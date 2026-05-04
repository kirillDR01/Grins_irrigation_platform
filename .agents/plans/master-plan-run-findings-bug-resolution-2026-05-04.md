# Feature: Master-Plan Run Findings — 2026-05-04 E2E Bug Resolution Umbrella

> **Source bughunt**: [`bughunt/2026-05-04-master-plan-run-findings.md`](../../bughunt/2026-05-04-master-plan-run-findings.md)
> **Run ID**: `2026-05-04T15:00Z` (dev Vercel + dev Railway)
> **Alembic head at planning time**: `20260506_120000_repair_invoice_line_items_shape` (verified via `uv run alembic heads`).
> **Resolved decisions** (no operator gate left):
> - **Internal-staff SMS (Task 3.6)**: ship `is_internal=True` kwarg on `send_automated_message`; bypass `SentMessage` write entirely. Existing test `test_estimate_internal_notification.py:71` only asserts `sms.send_automated_message.assert_awaited_once()` so it stays green without modification.
> - **CallRail timestamp shape (Bug #3)**: confirmed via `services/sms/callrail_provider.py:258-286` ("Field names verified against a real inbound payload on 2026-04-08") that CallRail's inbound payload contains ONLY `source_number`, `content`, `resource_id`, `destination_number`, `thread_resource_id`, `conversation_id`. **No `created_at`, no `sent_at` is reliably present.** The fix is therefore "if `created_at` empty, use receipt time; rely on `resource_id` dedup (existing `webhook_processed_log` table) for replay protection." The `sent_at` middle step is kept only as defensive future-proofing.
> - **Bug #2b literal type**: `invoice_service.py:949-951,1129-1131` types `sms_failure_reason: Literal["consent","rate_limit","provider_error","no_phone"]`. Plan does NOT widen the literal; adds a sibling field `sms_failure_detail: str | None` for the raw reason. Keeps strict typing.
>
> The plan below is exhaustive. Re-grep cited line numbers — drifts of ±5 lines are fine; if surrounding code has been refactored, stop and update the plan.

## Feature Description

Six independent defects surfaced during the 2026-05-04 master e2e run. They span the estimate portal, the SMS inbound path, and the Stripe payment-reconciliation path. Each is independently repro'd, each rolled back or hard-failed at least one customer-visible operation, and each has a small, well-scoped fix. This umbrella resolves all six in one branch behind one PR (matches the **bug-reporting workflow** memory: stage findings → resolve as one umbrella once verified).

The highest-impact bug (Bug #5) silently breaks every Stripe Payment Link reconciliation: customers pay, Stripe sends an Apple-Pay receipt, but the invoice never moves from `draft`. Bug #1 is similarly silent: customers receive a *signed* estimate PDF over email, but our DB still says `draft`. Two of six (Bug #3, #6) are P0 webhook-handler crashes blocking other features (any human SMS reply; any Apple-Pay agreement signup).

## User Story

As a Grin's Irrigation **operator**,
I want estimate sends, portal approvals, customer SMS replies, and Stripe Payment Link payments to update DB state reliably,
So that the dashboard, payment reporting, and appointment-confirmation flows reflect reality without manual SQL reconciliation.

As a Grin's Irrigation **customer**,
I want my estimate-approval email, my Y/R/C SMS confirmation, and my Apple-Pay receipt to mean the same thing the business sees,
So that I'm not contacted again about an estimate I already approved or an invoice I already paid.

## Problem Statement

Today, on dev:
- `POST /estimates/{id}/send` 500s because `send_automated_message` writes a `SentMessage` row with both FKs null, violating `ck_sent_messages_recipient`. The IntegrityError poisons the session and rolls back the entire `/send` (and portal `/approve`) transaction. Customers receive emails confirming a "sent" / "approved" estimate that the DB never persisted. (**Bug #1**)
- The portal estimate page renders an empty `Prepared for:` line and `Date: Invalid Date` because `PortalEstimateResponse` deliberately omits the customer name and `created_at`, and the frontend reads `estimate.customer_name` / `estimate.created_at` which are `undefined`. (**Bug #2**)
- `POST /invoices/{id}/send-link` reports `sms_failure_reason: "provider_error"` when the actual reason is `duplicate_message_within_24_hours` (dedup soft-fail). (**Bug #2b**)
- Real CallRail inbound webhooks 400 with `replay_or_stale_timestamp` because CallRail's payload does not put `created_at` at the top level — only `sent_at` (and the simulator masks the bug by sending both). Result: every Y/R/C/STOP reply is silently dropped. (**Bug #3**)
- After Bug #3 is fixed (or via simulator), `_try_poll_reply` orphan-inserts a row with `provider_message_id=""` (empty string, not NULL); the second such reply collides on the unique partial index `WHERE provider_message_id IS NOT NULL` because Postgres treats `""` as a non-NULL value. The IntegrityError poisons the session and the appointment-confirmation handler never runs. (**Bug #4**)
- `StripePaymentLinkService.create_for_invoice` puts `metadata` only at the top level of the PaymentLink, not at `payment_intent_data.metadata`. Stripe doesn't auto-propagate. The PI handler reads empty metadata and returns `unmatched_metadata`. Every Apple-Pay / card payment fails to reconcile. Receipt SMS never fires. (**Bug #5 — P0 BLOCKER**)
- The fallback in the `checkout.session.completed` handler builds a synthetic phone as `f"000{event['id'][-7:]}"`. Stripe event IDs have alphanumeric suffixes (e.g. `SoDqVvS`), so the synthetic fails the 10-digit `CustomerCreate.phone` validator. Any Apple-Pay agreement signup with no phone crashes the webhook. (**Bug #6**)

## Solution Statement

Six independent surgical fixes, ordered by blast radius:

1. **Bug #5** — add `payment_intent_data.metadata` to `stripe.PaymentLink.create` params; backfill via a defensive `checkout.session.completed` correlator that reads `session.metadata.invoice_id` and reconciles when the PI path missed.
2. **Bug #6** — replace `f"000{event['id'][-7:]}"` with a deterministic 10-digit synthetic derived from the event ID hash; keep the schema validator strict.
3. **Bug #3** — relax `created_at` extraction to fall back to `sent_at` (CallRail's actual field) and finally to receipt time when both are absent. Replay protection is preserved by Redis/DB resource-id dedup.
4. **Bug #1** — extend `Recipient.from_adhoc` to accept optional `customer_id` and `lead_id`; thread `customer_id` / `lead_id` through `send_automated_message`. Update 4 estimate sites + 3 lead sites + 1 notification site to pass the FK they already hold in scope. Internal-staff sends (no customer/lead in scope) stay phone-only and get an explicit `is_internal=True` allowlist in the constraint check.
5. **Bug #4** — coerce empty `provider_message_id` to `None` before INSERT in `_try_poll_reply` orphan path. Optionally migrate the partial index to also exclude empty strings (`WHERE provider_message_id IS NOT NULL AND provider_message_id <> ''`) for defense in depth.
6. **Bug #2 / 2b** — add `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at` to `PortalEstimateResponse`; populate them in `_to_portal_response`; update frontend `PortalEstimate` type. Thread the actual SMS reject reason through `attempted_channels` instead of the generic `provider_error`.

The sequencing — Bug #5 first, then #6, then #3, then #1, then #4, then #2 — matches the priority order in the bughunt's "Suggested priority order" section and minimizes the chance of one fix masking another's regression.

## Feature Metadata

**Feature Type**: Bug Fix (umbrella across 6 independent defects)
**Estimated Complexity**: **High** (6 surfaces, ~20 file edits, 1 migration, ~25 new tests, manual e2e validation)
**Primary Systems Affected**:
- `services/stripe_payment_link_service.py` + `api/v1/webhooks.py` (PI/checkout reconciliation)
- `api/v1/callrail_webhooks.py` + `services/sms/webhook_security.py` (inbound webhook freshness)
- `services/sms/recipient.py` + `services/sms_service.py` + `models/sent_message.py` (recipient FK threading)
- `services/estimate_service.py` + `services/lead_service.py` + `services/notification_service.py` + `api/v1/resend_webhooks.py` (call sites)
- `services/campaign_response_service.py` + 1 alembic migration (orphan-insert hardening)
- `schemas/portal.py` + `api/v1/portal.py` + `frontend/src/features/portal/` (cosmetic display fields)
- `services/invoice_service.py` (SMS soft-fail reason labeling)
**Dependencies**: stripe-python 8.x; existing alembic chain (head: `20260506_120000_repair_invoice_line_items_shape`); `webauthn`, `resend`, `apscheduler` unchanged.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Bug #5 — Stripe Payment Link metadata propagation
- `src/grins_platform/services/stripe_payment_link_service.py` lines 70–129 (the `create_for_invoice` body — `params` dict at lines 100–110 lacks `payment_intent_data.metadata`)
- `src/grins_platform/api/v1/webhooks.py` lines 1030–1120 (`_handle_payment_intent_succeeded` — reads `intent.get("metadata")` at 1047, `unmatched_metadata` early-return at 1049–1054)
- `src/grins_platform/tests/unit/test_stripe_payment_link_service.py` lines 1–100 (existing test pattern: `with patch.object(stripe.PaymentLink, "create") as mock_create:` then assert `mock_create.call_args.kwargs`)
- `src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py` (existing PI-success handler tests — mirror this pattern for the new `checkout.session.completed` correlator if added)

#### Bug #6 — `checkout.session.completed` synthetic phone
- `src/grins_platform/api/v1/webhooks.py` line 340 — the failing fallback: `phone=normalized_phone or phone_raw or f"000{event['id'][-7:]}"`
- `src/grins_platform/schemas/customer.py` lines 29–52 (the `normalize_phone` validator — strips non-digits then requires `len(digits) == 10`)
- `src/grins_platform/api/v1/webhooks.py` lines 300–360 (full block: name parsing, phone normalize, `existing_by_phone` lookup, `CustomerCreate(...)` build)
- `src/grins_platform/tests/unit/test_webhook_handlers.py` and `test_stripe_webhook.py` — pattern for mocking Stripe events through the handler

#### Bug #3 — CallRail inbound `created_at`
- `src/grins_platform/api/v1/callrail_webhooks.py` lines 230–325 (HMAC verify at 243; `created_at = str(payload.get("created_at", ""))` at 296; `check_freshness` call at 297; 400 response at 314–318)
- `src/grins_platform/services/sms/webhook_security.py` lines 81–113 (`check_freshness` — empty string returns `(False, 0)` at line 100; ISO parse at 105–108)
- `src/grins_platform/services/sms/callrail_provider.py` lines 258–286 (`parse_inbound_webhook` — **the canonical source of truth for CallRail inbound payload field names**, "verified against a real inbound payload on 2026-04-08"). Reads only: `source_number`, `content`, `resource_id`, `destination_number`, `thread_resource_id`, `conversation_id`. Confirms neither `created_at` nor `sent_at` is reliably present.
- `e2e/master-plan/sim/callrail_inbound.sh` lines 47–68 (simulator's payload — has BOTH `sent_at` and `created_at`; this is why the simulator masked the bug while real CallRail fails)
- `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py` lines 1–120 (existing integration test pattern: `_sign(body)`, `_payload(...)`, `WEBHOOK_PATH`, `_callrail_env` fixture). The fixture at line 64–77 hardcodes `created_at` — **this test asserts the simulator's shape, not real CallRail's**, which is why CI passed while production failed.
- `src/grins_platform/models/webhook_processed_log.py` — table that backstops replay protection via `(provider, conversation_id, provider_message_id)` dedup, so the `created_at` freshness check is defense-in-depth, not the primary replay barrier.

#### Bug #1 — `Recipient.from_adhoc` lacks `customer_id`
- `src/grins_platform/services/sms/recipient.py` lines 22–80 (frozen dataclass already has `customer_id` and `lead_id` fields at 28–29; `from_adhoc` at 62–80 omits `customer_id`)
- `src/grins_platform/services/sms_service.py` lines 532–610 (the `send_automated_message` shim; the bug is at line 583: `recipient = Recipient.from_adhoc(phone=phone)` with no FK)
- `src/grins_platform/models/sent_message.py` lines 126–130 (`CheckConstraint("customer_id IS NOT NULL OR lead_id IS NOT NULL", name="ck_sent_messages_recipient")`)
- `src/grins_platform/services/estimate_service.py` lines 322–326 (customer branch — `estimate.customer.id` available), 363–367 (lead branch — `lead.id` available), 629–633 (internal staff — neither available; intentional), 1083–1087 (follow-up reminder — phone resolved from `_get_contact_phone(estimate)` so `estimate.customer.id` or `estimate.lead.id` available via `estimate`)
- `src/grins_platform/services/lead_service.py` lines 126, 359, 1733 (all three are LEAD-branch — `lead.id` always in scope)
- `src/grins_platform/services/notification_service.py` line 1142 (LEAD-branch)
- `src/grins_platform/api/v1/resend_webhooks.py` line 153 (INTERNAL — staff bounce notification, no customer/lead in scope; phone-only is correct)
- **Correct pattern to mirror**: `src/grins_platform/services/appointment_service.py` line 1769 — `recipient = Recipient.from_customer(customer)` (the canonical customer-keyed send path)
- **Test fixture template**: `src/grins_platform/tests/unit/test_sms_service_gaps.py` (`TestSendAutomatedMessageDelegatesToSendMessage` class, lines 519–550) — patches `service.send_message`, `service._touch_lead_last_contacted`, and `datetime`

#### Bug #4 — `_try_poll_reply` orphan-insert empty `provider_message_id`
- `src/grins_platform/services/campaign_response_service.py` lines 240–280 (`record_poll_reply`; orphan branch at 260–280; line 274 inserts `provider_message_id=inbound.provider_sid` raw)
- `src/grins_platform/migrations/versions/20260410_100100_add_thread_id_and_response_indexes.py` lines 31–37 (the partial unique index `WHERE provider_message_id IS NOT NULL` — does NOT exclude empty strings)
- `src/grins_platform/api/v1/callrail_webhooks.py` lines 379–397 (`handle_inbound` call; `inbound.provider_sid` is the `id` field of the CallRail payload)
- `src/grins_platform/tests/unit/test_campaign_response_service.py` (existing test pattern for `record_poll_reply` orphan path — mirror)

#### Bug #2 / 2b — Portal estimate fields + SMS soft-fail reason
- `src/grins_platform/schemas/portal.py` lines 17–79 (`PortalEstimateResponse` — missing `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at`)
- `src/grins_platform/api/v1/portal.py` lines 146–198 (`_to_portal_response` — does not pass customer name or `created_at`)
- `frontend/src/features/portal/types/index.ts` lines 17–36 (frontend type already declares `customer_name` and `created_at`, demonstrating the API/UI contract drift)
- `frontend/src/features/portal/components/EstimateReview.tsx` lines 171, 176 (consumers: `{estimate.customer_name}` and `new Date(estimate.created_at).toLocaleDateString()`)
- `src/grins_platform/services/invoice_service.py` — the `attempted_channels` builder where `provider_error` is hardcoded (search `provider_error` in this file). The actual reject reason is in the `send_message` result dict's `reason` field (see `services/sms_service.py:599-602` for the shape).

### New Files to Create

- `src/grins_platform/migrations/versions/{NEW_DATESTAMP}_harden_provider_message_id_partial_index.py` — alembic migration: drop `ix_campaign_responses_provider_message_id`, recreate with `WHERE provider_message_id IS NOT NULL AND provider_message_id <> ''`.
- `src/grins_platform/tests/unit/test_stripe_payment_link_service_pi_metadata.py` — new unit test asserting `kwargs["payment_intent_data"]["metadata"]["invoice_id"] == str(invoice.id)`.
- `src/grins_platform/tests/unit/test_webhook_checkout_session_metadata_fallback.py` — unit test for the new `checkout.session.completed` correlator.
- `src/grins_platform/tests/unit/test_webhook_phone_synthetic_fallback.py` — PBT (hypothesis) test asserting the synthetic phone always passes `normalize_phone`.
- `src/grins_platform/tests/unit/test_callrail_inbound_freshness_fallback.py` — unit test exercising `created_at` missing → `sent_at` fallback → receipt-time fallback.
- `src/grins_platform/tests/unit/test_recipient_from_adhoc_customer_id.py` — PBT/unit test for `Recipient.from_adhoc(phone, customer_id=...)`.
- `src/grins_platform/tests/unit/test_estimate_service_send_threads_customer_fk.py` — unit test asserting `send_automated_message` is called with `customer_id=estimate.customer.id` for all 3 customer-branch sites.
- `src/grins_platform/tests/unit/test_campaign_response_orphan_empty_provider_sid.py` — unit test asserting empty `provider_sid` is coerced to NULL before insert.
- `src/grins_platform/tests/integration/test_master_plan_e2e_signoff_2026_05_04.py` — single integration test that runs the full happy path (send estimate → portal approve → SMS Y → invoice → Apple-Pay PI succeeded) with mocks for Stripe/CallRail.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Stripe — PaymentLink create — `payment_intent_data.metadata`](https://docs.stripe.com/api/payment-link/create#create_payment_link-payment_intent_data-metadata)
  - Specific section: "payment_intent_data.metadata"
  - Why: Bug #5's canonical fix. Confirms metadata on `PaymentLink.metadata` does **not** propagate to the resulting `PaymentIntent` — you must set it explicitly on `payment_intent_data`. The "metadata" docs note: *"If the Payment Link contains line items where price's product has a recurring component, this will only apply to the metadata of the resulting subscription. Otherwise, this is set on the PaymentIntent created via the Checkout Session."* — confirms the propagation gap.
- [Stripe — Checkout Session — `payment_intent_data`](https://docs.stripe.com/api/checkout/sessions/create#create_checkout_session-payment_intent_data)
  - Why: Same propagation pattern; backfill via `checkout.session.completed` reads metadata from `session` itself, which IS already populated.
- [CallRail — Webhooks — Text Messages](https://apidocs.callrail.com/#text-messages-webhooks)
  - Why: Bug #3. Confirm field names CallRail actually sends in inbound text-message webhooks. The current hypothesis (from Railway logs + comment in `callrail_inbound.sh:30`) is that CallRail sends `sent_at` but not `created_at` at the top level. **You must verify against the live docs or capture before fixing.**
- [Postgres — Partial Indexes](https://www.postgresql.org/docs/current/indexes-partial.html)
  - Why: Bug #4 migration — the partial-index predicate must use SQL boolean, not Python truthiness; `provider_message_id <> ''` is the correct SQL.
- [Pydantic v2 — Field validators](https://docs.pydantic.dev/latest/concepts/validators/#field-validators)
  - Why: Bug #6 — alternative path is to allow `phone: str | None` on `CustomerCreate` rather than synthesize a fake one. The `normalize_phone` function lives in `schemas/customer.py:29-52`; if you change validation, update tests in `tests/unit/test_pbt_customer_management.py`.

### Patterns to Follow

#### Naming Conventions

- Backend Python: `snake_case.py` for files, `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_SNAKE` for constants. Tests live in `tests/unit/test_{module}.py`, `tests/functional/test_{workflow}_functional.py`, `tests/integration/test_{feature}.py`.
- Pytest markers: `@pytest.mark.unit`, `@pytest.mark.functional`, `@pytest.mark.integration`. Each new test file MUST set the marker (file-level `pytestmark = pytest.mark.unit` or per-test `@pytest.mark.unit`).
- Migration files: `YYYYMMDD_HHMMSS_descriptive_name.py` matching alembic's chain (head currently: `20260506_120000_repair_invoice_line_items_shape`).
- Frontend: components `PascalCase.tsx`, hooks `use{Name}.ts`, types in `types/index.ts`.

#### Logging Pattern (mandatory per `.kiro/steering/code-standards.md` §1)

Services extend `LoggerMixin`. Use the `{domain}.{component}.{action}_{state}` pattern:

```python
class StripePaymentLinkService(LoggerMixin):
    DOMAIN = "business"

    def create_for_invoice(self, invoice, customer):
        self.log_started("create_for_invoice", invoice_id=str(invoice.id))
        try:
            # ...
            self.log_completed("create_for_invoice", invoice_id=str(invoice.id))
        except StripeError as exc:
            self.log_failed("create_for_invoice", error=exc, invoice_id=str(invoice.id))
            raise
```

Function-based loggers use `get_logger(__name__) + DomainLogger.api_event(...)`. Webhook handlers MUST emit `validation_event` for input validation and `api_event` for entry/exit.

**Never log**: passwords, tokens, raw phone numbers (use `_mask_phone` from `services/sms_service.py`), full email addresses, full Stripe customer IDs (mask to last 6 chars).

#### Error Handling

Catch typed exceptions, log once at the boundary, re-raise typed errors:

```python
try:
    result = await self._process(data)
except ValidationError:
    raise  # already logged at validator
except StripeError as exc:
    self.log_failed("op", error=exc)
    raise StripePaymentLinkError(str(exc)) from exc
```

API endpoints catch domain errors and translate to HTTP status (404, 400, 422, 500). For webhooks, return `200 {"status":"error_logged"}` on internal failures so providers don't retry-storm — but only after the failure has been logged with full context. The current `callrail_webhooks.py` follows this pattern at line 387–397.

#### Dedup / Idempotency

Stripe webhooks: `stripe_webhook_events` table is the system-of-record for processed event IDs. Always check `event_id` before mutating. CallRail inbound: Redis primary, DB fallback (`webhook_processed_log` table). The PI handler at line 1086–1093 already short-circuits when `invoice.status == InvoiceStatus.PAID`. Mirror this pattern in the new `checkout.session.completed` correlator.

#### Test Patterns

Three tiers (mandatory per steering): unit (mocked), functional (real DB), integration (full system). Examples in this codebase:

- Unit + Stripe mocks: `test_stripe_payment_link_service.py:54-80` shows `with patch.object(stripe.PaymentLink, "create") as mock_create:` then `mock_create.call_args.kwargs` assertions. Use `SimpleNamespace` for invoice/customer fakes.
- Integration + webhook signing: `test_callrail_webhook_endpoint.py:54-117` shows `_sign(body)`, `_payload(...)`, `_callrail_env` autouse fixture that monkeypatches env vars.
- PBT + hypothesis: `test_pbt_customer_management.py` shows `@given(st.text(...))` with `assume(...)`. Use this for the synthetic-phone test.

#### Frontend Patterns

- Read `frontend/src/features/portal/types/index.ts` for the contract — when extending the API response, update the TS interface in the same PR or the frontend will silently render `undefined`.
- React Query hooks in `frontend/src/features/portal/hooks/` are the integration point — no changes needed for Bug #2 (the hook already returns whatever the API returns).
- Tailwind 4, shadcn-style. No emoji.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Bug #5 + #6 — P0 Stripe path, smallest blast radius, unblocks Apple-Pay reconciliation)

Bug #5 is one line of code + one defensive fallback. Bug #6 is one line of code. Both ship first because they unblock revenue reconciliation and agreement signups, and neither depends on any other bug.

**Tasks:**

- Add `payment_intent_data.metadata` to `StripePaymentLinkService.create_for_invoice` params.
- Add a `checkout.session.completed` defensive correlator in `api/v1/webhooks.py` that reads `session.metadata.invoice_id` and reconciles when the PI path missed (e.g., for in-flight Payment Links created before this fix lands).
- Replace the `f"000{event['id'][-7:]}"` synthetic with a deterministic 10-digit hash-derived synthetic.
- Backfill existing in-flight Payment Links: list all `invoices` with non-null `stripe_payment_link_id` and `status IN ('draft','sent','overdue')`, then either deactivate-and-recreate or rely on the new `checkout.session.completed` fallback. **Decision: use the fallback path; do NOT mutate Stripe-side state from a migration.**

### Phase 2: Inbound SMS path (Bug #3 — P0 freshness fallback)

CallRail's real inbound payload doesn't include top-level `created_at`. Fix the freshness extractor to fall back to `sent_at` and finally to receipt time. Replay protection is preserved by Redis/DB resource-id dedup (`webhook_processed_log` table).

**Tasks:**

- Update `callrail_webhooks.py:296` to extract `created_at` with a fallback chain: `payload.get("created_at") or payload.get("sent_at") or _receipt_time_iso()`.
- Add a structured log line `sms.webhook.timestamp_fallback_used` so we can observe which field is being read in production.
- Update the existing integration test `test_callrail_webhook_endpoint.py::_payload` helper to support both shapes, and add a new test asserting that a CallRail-shaped payload with NO `created_at` and only `sent_at` succeeds.
- Capture the real CallRail payload shape from `feature-developments/CallRail collection/CallRail_Scheduling_Poll_Responses.md` and add it as a fixture file `tests/unit/fixtures/callrail_real_inbound.json` so future contributors don't repeat the simulator/reality mismatch.

### Phase 3: Recipient FK threading (Bug #1 — P1, ~10 file edits, well-scoped refactor)

Extend `SMSService.send_automated_message` with three new keyword-only parameters: `customer_id: UUID | None`, `lead_id: UUID | None`, `is_internal: bool = False`. Internal sends short-circuit before `send_message` (no `SentMessage` row, no consent check beyond the time window). Customer/lead sends construct a `Recipient` directly with the right `source_type` so the audit row carries a non-null FK and satisfies `ck_sent_messages_recipient`. Update 4 estimate-service sites + 3 lead-service sites + 1 notification-service site + 1 resend-webhooks site.

**Tasks:**

- Modify `SMSService.send_automated_message` signature to add three keyword-only kwargs (with `*` separator for backwards compat).
- Inside the shim, dispatch the `recipient` build:
  - If `is_internal=True`: skip `send_message` entirely; call provider's `send_text` directly through a new `_send_internal(phone, message)` private helper that respects time-window and consent guards but does NOT write `SentMessage`.
  - Elif `customer_id is not None`: `Recipient(phone=phone, source_type="customer", customer_id=customer_id)`.
  - Elif `lead_id is not None`: `Recipient(phone=phone, source_type="lead", lead_id=lead_id)`.
  - Else: keep current `Recipient.from_adhoc(phone=phone)` for true backwards compat (e.g., `onboarding_reminder_job.py:129` which has neither FK in scope) — but emit a `WARNING` log so we can audit remaining ad-hoc sites in production.
- Update **4 sites in `estimate_service.py`**:
  - Line 322 (customer branch): `customer_id=estimate.customer.id`
  - Line 363 (lead branch): `lead_id=lead.id`
  - Line 629 (internal staff): `is_internal=True`
  - Line 1083 (follow-up reminder): inline-resolve the FK by replacing `phone = self._get_contact_phone(estimate)` with new helper `_get_contact_phone_with_keys(estimate) -> tuple[str | None, UUID | None, UUID | None]` returning `(phone, customer_id, lead_id)`. Update `_get_contact_phone` (lines 1302–1324) to delegate to the new helper.
- Update **3 sites in `lead_service.py`** (lines 126, 359, 1733): `lead_id=lead.id`.
- Update **1 site in `notification_service.py`** (line 1142): `lead_id=lead.id`.
- Update **1 site in `resend_webhooks.py`** (line 153): `is_internal=True`.
- Leave `onboarding_reminder_job.py:129` and any remaining phone-only sites unchanged — they will trigger the new WARNING log; resolving each is out of scope (separate cleanup PR).

### Phase 4: Orphan-insert hardening (Bug #4 — P1 partial-index + coercion)

Coerce empty `provider_message_id` to `None` before INSERT in `_try_poll_reply` orphan path. Add a partial-index migration that excludes empty strings as defense in depth.

**Tasks:**

- In `campaign_response_service.py:266-280`, coerce `provider_message_id=inbound.provider_sid or None` (or use a small helper `_normalize_provider_sid(s) -> str | None: return s or None`).
- Create alembic migration to drop and recreate the partial index with `postgresql_where="provider_message_id IS NOT NULL AND provider_message_id <> ''"`.
- Verify the migration is forward+backward compatible (the upgrade is additive; the downgrade reinstates the old, less-strict predicate).

### Phase 5: Portal display fields + SMS soft-fail labeling (Bug #2 + #2b — P3 cosmetic)

Add `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at` to `PortalEstimateResponse`. Populate in `_to_portal_response`. Update frontend type.

For 2b: thread the actual SMS reject reason through `attempted_channels` instead of the hardcoded `provider_error`.

**Tasks:**

- Extend `PortalEstimateResponse` schema with the 5 fields.
- Update `_to_portal_response` (`api/v1/portal.py:181-198`) to populate them. Customer name comes from `estimate.customer` (or `estimate.lead` for lead branch); fall back gracefully when neither is set.
- Update `frontend/src/features/portal/types/index.ts` `PortalEstimate` interface — already has `customer_name` and `created_at`, but add `customer_first_name` / `customer_last_name` / `customer_email` for consistency. Update `EstimateReview.tsx:171` to render `{first_name} {last_name}` when both are present.
- For 2b: in `invoice_service.py` (search for `"provider_error"` literal), thread `result.get("reason")` from `send_message` into `attempted_channels` so the API consumer sees `dedup_24h`, `opted_out`, `rate_limited`, etc., instead of the generic `provider_error`.

### Phase 6: Testing & Validation

**Tasks:**

- Unit tests for each fix (see "STEP-BY-STEP TASKS" below).
- Integration test `test_master_plan_e2e_signoff_2026_05_04.py` covering the happy path with mocks.
- Manual e2e on dev: re-run `e2e/master-plan/run-all.sh` (or the relevant phase scripts) and confirm zero regressions.
- Update bughunt with sign-off: each bug gets a "RESOLVED 2026-MM-DD by commit `<sha>`" annotation.

---

## STEP-BY-STEP TASKS

> **Sequencing**: Execute top-to-bottom. Each task is atomic — run its `VALIDATE` command before moving on. If validation fails, stop and diagnose before proceeding.
>
> **Branching**: All work on `dev`. One PR with one commit per phase (6 commits) — matches the bughunt's "umbrella resolution" style (see `dadbacc` for the previous umbrella commit shape).

### Phase 1 — Bug #5 (Stripe Payment Link metadata)

#### Task 1.1: UPDATE `src/grins_platform/services/stripe_payment_link_service.py`

- **IMPLEMENT**: In `create_for_invoice`, add `payment_intent_data.metadata` mirroring the top-level `metadata`. Insert after the existing `metadata` key (line 105):
  ```python
  "payment_intent_data": {
      "metadata": {
          "invoice_id": str(invoice.id),
          "customer_id": str(invoice.customer_id),
      },
  },
  ```
- **PATTERN**: top-level `metadata` at lines 102–105 — mirror keys exactly so reconciliation logic doesn't have to handle two shapes.
- **IMPORTS**: none new.
- **GOTCHA**: do NOT add `payment_intent_data` for subscription line items. Stripe rejects `payment_intent_data` when any line item references a recurring price. Subscription Payment Links are out of scope for the dev seed flow but check whether `_build_line_items` ever produces recurring items — it doesn't today (`stripe_payment_link_service.py:_build_line_items` builds only one-shot `price_data`). If that changes in the future, add `if not has_recurring:` guard.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_payment_link_service.py -v` (existing tests must still pass; new test in 1.2 must pass).

#### Task 1.2: CREATE `src/grins_platform/tests/unit/test_stripe_payment_link_service_pi_metadata.py`

- **IMPLEMENT**: Single test that calls `service.create_for_invoice(invoice, customer)` with `stripe.PaymentLink.create` patched, then asserts:
  ```python
  kwargs = mock_create.call_args.kwargs
  assert kwargs["payment_intent_data"]["metadata"]["invoice_id"] == str(invoice.id)
  assert kwargs["payment_intent_data"]["metadata"]["customer_id"] == str(invoice.customer_id)
  ```
- **PATTERN**: copy the fixture builders `_make_settings`, `_make_invoice`, `_make_customer` from `test_stripe_payment_link_service.py:22-46`.
- **IMPORTS**: `from grins_platform.services.stripe_payment_link_service import StripePaymentLinkService`; `from unittest.mock import patch`; `import stripe`; `from types import SimpleNamespace`.
- **GOTCHA**: pytest marker — use `@pytest.mark.unit` (matches the rest of `tests/unit/`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_payment_link_service_pi_metadata.py -v`

#### Task 1.3: ADD `checkout.session.completed` invoice-correlator branch in `src/grins_platform/api/v1/webhooks.py`

- **IMPLEMENT**: Find the existing `checkout.session.completed` handler (the agreement-signup path around line 300–360). Before its agreement-signup logic, add a short-circuit: if `session.get("metadata", {}).get("invoice_id")` is set, route to `_handle_invoice_payment_via_session(session)` which mirrors `_handle_payment_intent_succeeded` but reads `invoice_id` from `session.metadata` and `payment_intent_id` from `session.payment_intent`, then calls the same `InvoiceService.record_payment(...)` path. Idempotency: check `invoice.status == PAID` and short-circuit (mirrors lines 1086–1093).
- **PATTERN**: `_handle_payment_intent_succeeded` (lines 1037–1116) is the template. Reuse as much as possible — extract the post-amount-resolution logic into a `_record_invoice_payment(session_or_intent, invoice_id, amount, reference)` helper to avoid duplication.
- **IMPORTS**: existing imports in `webhooks.py` cover this.
- **GOTCHA**: `session.payment_intent` is sometimes `None` (async PaymentIntents). Use `session.payment_intent or session.id` for the `payment_reference` so receipts correlate. Also: this fallback fires for invoice payments AND agreement-signup checkouts — use the presence of `metadata.invoice_id` as the discriminator and `package_type` for the agreement branch (already does this).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py src/grins_platform/tests/unit/test_webhook_handlers.py -v`

#### Task 1.4: CREATE `src/grins_platform/tests/unit/test_webhook_checkout_session_metadata_fallback.py`

- **IMPLEMENT**: Two tests:
  1. `test_checkout_session_with_invoice_metadata_marks_invoice_paid` — fake checkout session with `metadata={"invoice_id": ...}` → assert `invoice_service.record_payment` called.
  2. `test_checkout_session_without_invoice_metadata_falls_through_to_agreement` — fake checkout with `package_type` set → assert agreement-signup path called, NOT invoice path.
- **PATTERN**: mirror `test_stripe_webhook_payment_links.py` test setup.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_checkout_session_metadata_fallback.py -v`

### Phase 1 — Bug #6 (Synthetic phone fallback)

#### Task 1.5: UPDATE `src/grins_platform/api/v1/webhooks.py` line 340

- **IMPLEMENT**: Replace `phone=normalized_phone or phone_raw or f"000{event['id'][-7:]}"` with a deterministic 10-digit synthetic:
  ```python
  def _synthetic_phone_for_event(event_id: str) -> str:
      """10-digit deterministic synthetic from a Stripe event ID."""
      h = hashlib.sha256(event_id.encode()).digest()
      n = int.from_bytes(h[:8], "big") % 10**10
      return f"{n:010d}"
  ```
  Then: `phone=normalized_phone or phone_raw or _synthetic_phone_for_event(event["id"]),`
- **PATTERN**: `hashlib` import already used elsewhere in `webhooks.py` for stripe signature verify.
- **IMPORTS**: `import hashlib` if not already imported in scope.
- **GOTCHA**: `phone_raw` may be a non-numeric string (e.g. user typed "(555) abc-def" into Stripe). The synthetic only fires when both normalized and raw are empty/None — so it won't mask bad user input.
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/webhooks.py && uv run ruff check src/grins_platform/api/v1/webhooks.py`

#### Task 1.6: CREATE `src/grins_platform/tests/unit/test_webhook_phone_synthetic_fallback.py`

- **IMPLEMENT**: PBT test using hypothesis: for any 100-char alphanumeric event ID, the synthetic must (a) be exactly 10 digits, (b) pass `normalize_phone` without raising. Plus a deterministic test asserting `_synthetic_phone_for_event("evt_1TTOFlQDNzCTp6j5nSoDqVvS")` is stable across calls.
- **PATTERN**: hypothesis pattern in `test_pbt_customer_management.py`.
- **IMPORTS**: `from hypothesis import given, strategies as st`; `from grins_platform.schemas.customer import normalize_phone`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_webhook_phone_synthetic_fallback.py -v -m unit`

### Phase 2 — Bug #3 (CallRail freshness fallback)

#### Task 2.1: UPDATE `src/grins_platform/api/v1/callrail_webhooks.py` lines 295–297

- **IMPLEMENT**: Replace `created_at = str(payload.get("created_at", ""))` with the resolved fallback chain. CallRail's verified inbound payload (provider parser at `services/sms/callrail_provider.py:258-286`) does NOT include `created_at` or `sent_at` — only `resource_id`, `source_number`, `content`, `destination_number`, `thread_resource_id`, `conversation_id`. The right primary fix is "use receipt time when absent." `sent_at` is kept as a defensive middle step in case CallRail adds it for some webhook subtypes:
  ```python
  raw_created_at = payload.get("created_at") or payload.get("sent_at") or ""
  if raw_created_at:
      created_at = str(raw_created_at)
      timestamp_source = "payload_created_at" if payload.get("created_at") else "payload_sent_at"
  else:
      # CallRail's inbound text-message webhook does not include any
      # timestamp (verified against parse_inbound_webhook field list at
      # callrail_provider.py:258-286). Fall back to receipt time. Replay
      # protection is preserved by resource_id dedup against
      # webhook_processed_log (the primary replay barrier — see Gap 07).
      created_at = datetime.now(timezone.utc).isoformat()
      timestamp_source = "receipt_time"
  logger.info(
      "sms.webhook.timestamp_source",
      provider=_PROVIDER,
      request_id=request_id,
      timestamp_source=timestamp_source,
  )
  ```
- **PATTERN**: `datetime.now(timezone.utc)` is used in `webhook_security.py:111`. `logger.info` and `_PROVIDER` are already in scope (same file).
- **IMPORTS**: `from datetime import datetime, timezone` (verify present at top of `callrail_webhooks.py` — `datetime` is already imported because `check_freshness` uses it indirectly; if missing, add).
- **GOTCHA**: do NOT remove the `check_freshness` call at line 297 — it still validates the format. The fallback only fills in a missing field. Also: emit the `sms.webhook.timestamp_source` log every time so we can observe per-request which field was used in production telemetry (and confirm CallRail behavior in practice).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py -v`

#### Task 2.2: CREATE `src/grins_platform/tests/unit/fixtures/callrail_real_inbound.json`

- **IMPLEMENT**: Mirror the verified CallRail inbound payload shape (per `parse_inbound_webhook` field list at `callrail_provider.py:258-286`). The fixture has NO timestamp fields — that's the entire point:
  ```json
  {
    "resource_id": "MSG019de95f6f0e78d1ad1a7bb4fd59fc49",
    "source_number": "***3312",
    "content": "Y",
    "destination_number": "+19525293750",
    "thread_resource_id": "SMT019de95f6f0e78d1ad1a7bb4fd59fc49",
    "conversation_id": "k8mc8"
  }
  ```
- **PATTERN**: pytest fixtures live in `tests/fixtures/` or `tests/unit/fixtures/` — pick the latter for unit-test scope. Load with:
  ```python
  from pathlib import Path
  import json
  FIXTURE = Path(__file__).parent / "fixtures" / "callrail_real_inbound.json"
  payload = json.loads(FIXTURE.read_text())
  ```
- **VALIDATE**: `python3 -c "import json; json.load(open('src/grins_platform/tests/unit/fixtures/callrail_real_inbound.json'))"` (just JSON-parses).

#### Task 2.3: CREATE `src/grins_platform/tests/unit/test_callrail_inbound_freshness_fallback.py`

- **IMPLEMENT**: Three tests:
  1. `test_payload_with_only_sent_at_passes_freshness` — patch `check_freshness` mock, assert it was called with the `sent_at` value.
  2. `test_payload_with_neither_falls_back_to_receipt_time` — assert log line `sms.webhook.timestamp_fallback_used` emitted with `fallback="receipt_time"`.
  3. `test_payload_with_both_prefers_created_at` — explicit precedence test.
- **PATTERN**: patch-based unit pattern; do NOT use the integration TestClient (this is a unit test on the timestamp extraction logic). Easiest: extract the extraction into a small helper `_extract_created_at(payload, request_id) -> str` and test it directly.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_callrail_inbound_freshness_fallback.py -v -m unit`

#### Task 2.4: UPDATE `src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py`

- **IMPLEMENT**: Add a new test `test_callrail_payload_without_created_at_succeeds_via_sent_at` that uses a payload with only `sent_at` (mirroring the new fixture) and asserts 200.
- **PATTERN**: existing `_payload(...)` helper at lines 61–77 — extend with a `created_at: Literal["both", "sent_at_only", "neither"] = "both"` parameter.
- **GOTCHA**: existing tests at this path use `created_at` at top level. Don't break them — add a NEW test, don't modify existing assertions.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py -v -m integration`

### Phase 3 — Bug #1 (Recipient FK threading)

> **Strategy** (resolved): do NOT extend `Recipient.from_adhoc` with a `customer_id` kwarg — that would conflate semantics (a customer-keyed send is not "ad hoc"). Instead, dispatch in `send_automated_message` to construct the right `Recipient` shape directly. This mirrors the canonical pattern at `invoice_service.py:956-962` (which constructs `Recipient(phone=..., source_type="customer", customer_id=customer.id)` directly, no factory).

#### Task 3.1: UPDATE `src/grins_platform/services/sms_service.py` `send_automated_message` signature + dispatch

- **IMPLEMENT**: Modify the signature at line 532–537:
  ```python
  async def send_automated_message(
      self,
      phone: str,
      message: str,
      message_type: str = "automated",
      *,
      customer_id: UUID | None = None,
      lead_id: UUID | None = None,
      is_internal: bool = False,
  ) -> dict[str, Any]:
  ```
  Replace lines 579–610 (the body after time-window enforcement) with:
  ```python
  resolved_type = _AUTOMATED_STR_TO_MESSAGE_TYPE.get(
      message_type,
      MessageType.AUTOMATED_NOTIFICATION,
  )

  if is_internal:
      # Internal staff notification: bypass SentMessage audit (no
      # customer/lead FK in scope; staff opt-in is implicit). Still
      # respects time-window already enforced above. Sends via provider
      # directly.
      try:
          await self._send_via_provider(phone=phone, message=message)
      except SMSError as exc:
          self.log_failed("send_automated_message", error=exc)
          return {"success": False, "reason": str(exc)}
      self.log_completed(
          "send_automated_message",
          phone=_mask_phone(phone),
          internal=True,
      )
      return {"success": True, "internal": True, "message_id": None}

  if customer_id is not None:
      recipient = Recipient(
          phone=phone,
          source_type="customer",
          customer_id=customer_id,
      )
  elif lead_id is not None:
      recipient = Recipient(
          phone=phone,
          source_type="lead",
          lead_id=lead_id,
      )
  else:
      # True ad-hoc: no FK available. Will hit ck_sent_messages_recipient
      # if the caller forgot to thread the FK they had in scope. Emit a
      # WARNING so we can audit remaining sites in production telemetry.
      self.logger.warning(
          "sms.send_automated_message.adhoc_without_fk",
          phone_masked=_mask_phone(phone),
          message_type=message_type,
      )
      recipient = Recipient.from_adhoc(phone=phone)

  try:
      result = await self.send_message(
          recipient=recipient,
          message=message,
          message_type=resolved_type,
          consent_type="transactional",
          skip_formatting=True,
      )
  except SMSConsentDeniedError:
      self.log_rejected(
          "send_automated_message",
          reason="opted_out",
          phone=_mask_phone(phone),
      )
      return {"success": False, "reason": "opted_out"}
  except SMSError as exc:
      self.log_failed("send_automated_message", error=exc)
      return {"success": False, "reason": str(exc)}

  # Phone-based last-contacted update is only meaningful when no
  # explicit customer_id/lead_id was passed (ad-hoc back-compat path).
  if customer_id is None and lead_id is None:
      await self._touch_lead_last_contacted(phone=phone)

  self.log_completed("send_automated_message", phone=_mask_phone(phone))
  return result
  ```
- **IMPORTS**: `from uuid import UUID` (verify already imported at top of `sms_service.py`); `from grins_platform.services.sms.recipient import Recipient` (move out of the inline import at lines 557–559 to module level for cleanliness).
- **GOTCHA #1**: the existing inline `from grins_platform.services.sms.recipient import Recipient` at lines 557–559 happens BEFORE the time-window enforce block. Keep that behavior or move it cleanly to the top of the file — but if you move it, run `uv run ruff check src/grins_platform/services/sms_service.py` to confirm no circular-import. The codebase's existing pattern is the inline import (`# noqa: PLC0415`), so safest to leave as inline and just use the `Recipient` symbol both in the existing factory call site and the new direct constructions.
- **GOTCHA #2**: `_send_via_provider` (line 612) takes `(phone, message)` and returns `ProviderSendResult`. Confirm that signature before calling it from the internal path.
- **GOTCHA #3**: the docstring at lines 538–555 says "phone-only" — rewrite it to describe the four call modes (internal / customer-keyed / lead-keyed / ad-hoc-warning).
- **GOTCHA #4**: keyword-only via `*,` is critical — adding positional kwargs would silently shift `message_type` for existing callers.
- **VALIDATE**: `uv run mypy src/grins_platform/services/sms_service.py && uv run ruff check src/grins_platform/services/sms_service.py && uv run pytest src/grins_platform/tests/unit/test_sms_service.py src/grins_platform/tests/unit/test_estimate_internal_notification.py -v`

#### Task 3.2: UPDATE `src/grins_platform/services/estimate_service.py` (4 sites)

- **IMPLEMENT**:
  - **Line 322** (customer branch — `if self.sms_service and estimate.customer:`): inside the `try:` block, add `customer_id=estimate.customer.id,` to the kwargs.
  - **Line 363** (lead branch — `if self.sms_service and getattr(lead, "phone", None):`): add `lead_id=lead.id,`.
  - **Line 629** (internal staff in `_notify_internal_decision`): add `is_internal=True,`.
  - **Line 1083** (follow-up reminder): replace the line `phone = self._get_contact_phone(estimate)` (line 1079) with new helper:
    ```python
    phone, contact_customer_id, contact_lead_id = self._get_contact_phone_with_keys(estimate)
    ```
    Then in the `send_automated_message` call at 1083, add: `customer_id=contact_customer_id, lead_id=contact_lead_id,`.
- **ALSO IMPLEMENT — new helper at end of class** (insert before `_get_contact_phone` at line 1302):
  ```python
  @staticmethod
  def _get_contact_phone_with_keys(
      estimate: Estimate,
  ) -> tuple[str | None, UUID | None, UUID | None]:
      """Return (phone, customer_id, lead_id) for the best contact.

      Customer takes precedence over lead. Returns (None, None, None) if
      neither has a phone.
      """
      if estimate.customer:
          phone = getattr(estimate.customer, "phone", None)
          if phone:
              return str(phone), estimate.customer.id, None
      if estimate.lead:
          phone = getattr(estimate.lead, "phone", None)
          if phone:
              return str(phone), None, estimate.lead.id
      return None, None, None
  ```
  Update `_get_contact_phone` (lines 1302–1324) to delegate: `return cls._get_contact_phone_with_keys(estimate)[0]` (keep for any external callers).
- **PATTERN**: canonical customer-keyed send is `appointment_service.py:1768-1769`.
- **GOTCHA #1**: `estimate.customer` and `estimate.lead` accesses at lines 314, 336, 354, 1314, 1319 are lazy-loaded via SQLAlchemy. The IntegrityError that this fix prevents was masking lazy-load failures. Inspect `repo.get_by_id` (in `repositories/estimate_repository.py`) — if it doesn't `selectinload(Estimate.customer)` and `selectinload(Estimate.lead)`, add it. Check by reading the repo source.
- **GOTCHA #2**: `estimate.customer.id` may be `Mapped[UUID]` (SQLAlchemy 2.0 annotated). Pass it as-is — Python's runtime UUID dispatcher handles `Mapped[UUID]` correctly.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service.py src/grins_platform/tests/unit/test_send_estimate_email.py src/grins_platform/tests/unit/test_estimate_internal_notification.py -v`

#### Task 3.3: UPDATE `src/grins_platform/services/lead_service.py` (3 sites)

- **IMPLEMENT**: Add `lead_id=lead.id,` at lines 126, 359, 1733. Each is in a block where `lead.id` is in scope (verified via the bughunt's bug #1 verification).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_lead_service_crm.py src/grins_platform/tests/unit/test_lead_pbt.py src/grins_platform/tests/unit/test_lead_service_extensions.py src/grins_platform/tests/unit/test_lead_sms_deferred.py -v`

#### Task 3.4: UPDATE `src/grins_platform/services/notification_service.py`

- **IMPLEMENT**: Line 1142: add `lead_id=lead.id,`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_notification_service.py -v`

#### Task 3.5: UPDATE `src/grins_platform/api/v1/resend_webhooks.py`

- **IMPLEMENT**: Line 153: add `is_internal=True,`. The send is to `recipient_phone` (staff alert phone), no customer/lead in scope — internal mode is correct.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/ -k 'resend or bounce' -v`

#### Task 3.6: VERIFY repository eager-load for `Estimate`

- **IMPLEMENT**: Read `src/grins_platform/repositories/estimate_repository.py` `get_by_id`. If the relationships `Estimate.customer` and `Estimate.lead` are not eager-loaded, add:
  ```python
  from sqlalchemy.orm import selectinload
  stmt = select(Estimate).options(
      selectinload(Estimate.customer),
      selectinload(Estimate.lead),
  ).where(Estimate.id == estimate_id)
  ```
- **GOTCHA**: SQLAlchemy `selectinload` requires the relationship to be defined on the model. Check `models/estimate.py` for `customer = relationship(...)` and `lead = relationship(...)`. If they're typed `Mapped[Customer | None] = relationship(...)`, you're good.
- **GOTCHA #2**: this change is performance-positive (one query → two queries with selectinload, instead of N+1 lazy loads). Don't worry about regression risk.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service.py -v` (existing tests stay green).

#### Task 3.7: CREATE `src/grins_platform/tests/unit/test_recipient_from_adhoc_customer_id.py`

- **IMPLEMENT**: Two tests:
  1. `test_from_adhoc_threads_customer_id` — `r = Recipient.from_adhoc(phone="+1...", customer_id=cid)` then assert `r.customer_id == cid` and `r.source_type == "ad_hoc"`.
  2. `test_from_adhoc_phone_only_legacy_path` — `r = Recipient.from_adhoc(phone="+1...")` asserts both FKs are `None` (regression guard).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_recipient_from_adhoc_customer_id.py -v -m unit`

#### Task 3.8: CREATE `src/grins_platform/tests/unit/test_estimate_service_send_threads_customer_fk.py`

- **IMPLEMENT**: Mock-based tests that call `EstimateService.send_estimate(estimate_id)` and assert `sms_service.send_automated_message.call_args.kwargs["customer_id"] == estimate.customer.id` for the customer branch. Three flavors: (1) customer branch, (2) lead branch (assert `lead_id` instead), (3) follow-up reminder branch.
- **PATTERN**: existing mock pattern in `test_estimate_service.py`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service_send_threads_customer_fk.py -v -m unit`

### Phase 4 — Bug #4 (Orphan-insert hardening)

#### Task 4.1: UPDATE `src/grins_platform/services/campaign_response_service.py:266-280`

- **IMPLEMENT**: Coerce empty `provider_message_id` to `None`:
  ```python
  provider_message_id = inbound.provider_sid or None
  row = await self.repo.add(
      CampaignResponse(
          campaign_id=None,
          sent_message_id=(
              corr.sent_message.id if corr.sent_message else None
          ),
          phone=inbound.from_phone,
          raw_reply_body=inbound.body,
          provider_message_id=provider_message_id,
          status=CampaignResponseStatus.ORPHAN,
          received_at=now,
      ),
  )
  ```
- **GOTCHA**: `inbound.provider_sid` is typed as `str` (not `str | None`) in the dataclass — check `services/sms/inbound.py` (or wherever `InboundSMS` is defined). If the field type allows empty string, the coercion is correct. If it allows None, even better — the coercion is idempotent.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_campaign_response_service.py -v`

#### Task 4.2: CREATE alembic migration `src/grins_platform/migrations/versions/20260507_120000_harden_provider_message_id_partial_index.py`

- **IMPLEMENT**: Three-step migration: (1) backfill empty strings to NULL so the new predicate doesn't fail, (2) drop the old partial index, (3) recreate with the stricter predicate. Verified head at planning time is `20260506_120000` — confirm with `uv run alembic heads` before writing the file.
  ```python
  """Harden ix_campaign_responses_provider_message_id partial index.

  Bug #4 (master-plan-run-findings 2026-05-04): the previous predicate
  ``WHERE provider_message_id IS NOT NULL`` allowed empty strings to
  collide on second-empty insert. New predicate also excludes empty
  strings; we backfill any pre-existing empties to NULL first.

  Revision ID: 20260507_120000
  Revises: 20260506_120000
  """
  from collections.abc import Sequence
  from typing import Union

  from alembic import op

  revision: str = "20260507_120000"
  down_revision: Union[str, None] = "20260506_120000"
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None


  def upgrade() -> None:
      # Step 1: pre-flight backfill so the new predicate doesn't fail
      # if multiple existing rows already have provider_message_id=''.
      op.execute(
          "UPDATE campaign_responses "
          "SET provider_message_id = NULL "
          "WHERE provider_message_id = ''",
      )
      # Step 2: drop old partial index.
      op.drop_index(
          "ix_campaign_responses_provider_message_id",
          table_name="campaign_responses",
      )
      # Step 3: recreate with stricter predicate.
      op.create_index(
          "ix_campaign_responses_provider_message_id",
          "campaign_responses",
          ["provider_message_id"],
          unique=True,
          postgresql_where=(
              "provider_message_id IS NOT NULL "
              "AND provider_message_id <> ''"
          ),
      )


  def downgrade() -> None:
      op.drop_index(
          "ix_campaign_responses_provider_message_id",
          table_name="campaign_responses",
      )
      op.create_index(
          "ix_campaign_responses_provider_message_id",
          "campaign_responses",
          ["provider_message_id"],
          unique=True,
          postgresql_where="provider_message_id IS NOT NULL",
      )
  ```
- **PATTERN**: copy the header conventions from `20260414_100600_widen_sent_messages_for_automated_notification.py` (revision/down_revision string format) and `20260506_120000_repair_invoice_line_items_shape.py` (most recent head).
- **GOTCHA #1**: revision chain — `down_revision = "20260506_120000"` (just the hash, no descriptor suffix per the existing convention; verify with `head -25 src/grins_platform/migrations/versions/20260506_120000_repair_invoice_line_items_shape.py`).
- **GOTCHA #2**: do NOT run alembic against `*.railway.{app,internal}` from local — that's a hard-rule per memory. Push to branch and let Railway apply.
- **GOTCHA #3**: the pre-flight backfill in Step 1 is essential. Without it, if there are 2+ existing rows with `provider_message_id=''`, dropping and recreating the unique index will fail because both rows would conflict under the new predicate. The backfill resolves them to NULL (allowed by both predicates).
- **VALIDATE**: `uv run alembic upgrade head` (local Postgres) → `uv run alembic downgrade -1` (verify roundtrip) → `uv run alembic upgrade head`. Then: `psql -c "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_campaign_responses_provider_message_id'"` should show `WHERE ((provider_message_id IS NOT NULL) AND ((provider_message_id)::text <> ''::text))`.

#### Task 4.3: CREATE `src/grins_platform/tests/unit/test_campaign_response_orphan_empty_provider_sid.py`

- **IMPLEMENT**: Two tests:
  1. `test_orphan_insert_with_empty_provider_sid_coerces_to_none` — asserts the `CampaignResponse` constructor is called with `provider_message_id=None`.
  2. `test_orphan_insert_with_real_provider_sid_passes_through` — regression guard.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_campaign_response_orphan_empty_provider_sid.py -v -m unit`

### Phase 5 — Bug #2 + #2b (Portal cosmetic + SMS reason)

#### Task 5.1: UPDATE `src/grins_platform/schemas/portal.py`

- **IMPLEMENT**: Add 5 fields to `PortalEstimateResponse` (after the existing `readonly` field at line 79):
  ```python
  customer_first_name: str | None = Field(default=None, max_length=100, description="Customer first name")
  customer_last_name: str | None = Field(default=None, max_length=100, description="Customer last name")
  customer_email: str | None = Field(default=None, max_length=320, description="Customer email")
  created_at: datetime | None = Field(default=None, description="Estimate creation timestamp")
  sent_at: datetime | None = Field(default=None, description="Estimate sent timestamp")
  ```
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_portal_api.py -v`

#### Task 5.2: UPDATE `src/grins_platform/api/v1/portal.py:_to_portal_response`

- **IMPLEMENT**: In `_to_portal_response` (lines 146–198), pull customer info:
  ```python
  customer = getattr(estimate, "customer", None)
  lead = getattr(estimate, "lead", None)
  contact = customer or lead
  first_name = getattr(contact, "first_name", None)
  last_name = getattr(contact, "last_name", None)
  if not first_name and lead is not None:
      # Lead.name is a single field; split first token.
      parts = (lead.name or "").strip().split(maxsplit=1)
      first_name = parts[0] if parts else None
      last_name = parts[1] if len(parts) > 1 else None
  customer_email = getattr(contact, "email", None)
  ```
  Then pass to the `PortalEstimateResponse(...)` ctor. Also pass `created_at=estimate.created_at` and `sent_at=getattr(estimate, "sent_at", None)`.
- **GOTCHA**: lazy-loading — if `estimate.customer` triggers a DB roundtrip, the existing endpoint (which the bughunt confirms works for the rest of the data) already loads it. If not, add `selectinload(Estimate.customer), selectinload(Estimate.lead)` to the query in the GET handler at lines 224–305.
- **VALIDATE**: manual curl after deploy: `curl -s $API/api/v1/portal/estimates/<TOKEN> | jq 'keys'` should now include `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at`.

#### Task 5.3: UPDATE `frontend/src/features/portal/types/index.ts`

- **IMPLEMENT**: Add to `PortalEstimate`:
  ```ts
  customer_first_name?: string | null;
  customer_last_name?: string | null;
  customer_email?: string | null;
  // created_at already present at line 30
  sent_at?: string | null;
  ```
- **VALIDATE**: `cd frontend && npm run typecheck`

#### Task 5.4: UPDATE `frontend/src/features/portal/components/EstimateReview.tsx`

- **IMPLEMENT**: At line 171, render either the new fields or the existing `customer_name`:
  ```tsx
  <p className="font-medium text-slate-800">
    {[estimate.customer_first_name, estimate.customer_last_name].filter(Boolean).join(' ') || estimate.customer_name || '—'}
  </p>
  ```
  Line 176 (`new Date(estimate.created_at).toLocaleDateString()`) — already correct once API populates `created_at`.
- **VALIDATE**: `cd frontend && npm run lint && npm run test -- estimate` (Vitest must pass `EstimateReview.test.tsx`).

#### Task 5.5: UPDATE `src/grins_platform/services/invoice_service.py` — thread real SMS reject reason via NEW `sms_failure_detail` field

- **IMPLEMENT**: The existing `sms_failure_reason: Literal["consent","rate_limit","provider_error","no_phone"]` (lines 949–951 and 1129–1131) is a strict-typing categorical bucket. **Do NOT widen the literal** — that would force every consumer to handle every new string. Instead, add a sibling `sms_failure_detail: str | None = None` field for the raw upstream reason. Two changes:
  1. Find `class SendLinkResponse` (search `class SendLinkResponse` in `schemas/invoice.py` or `schemas/payment.py`). Add the new field:
     ```python
     sms_failure_detail: str | None = Field(
         default=None,
         max_length=200,
         description="Raw upstream reject reason (e.g. 'duplicate_message_within_24_hours'); paired with categorical sms_failure_reason.",
     )
     ```
  2. In `invoice_service.py`, where `sms_failure_reason = "provider_error"` is set (lines 977 and 998), capture the raw reason from `result`:
     ```python
     # Line 977 site (soft-fail branch):
     sms_failure_reason = "provider_error"
     sms_failure_detail = str(result.get("reason") or result.get("status") or "")[:200] or None
     # Line 998 site (SMSError branch):
     sms_failure_reason = "provider_error"
     sms_failure_detail = str(exc)[:200] or None
     ```
     Thread `sms_failure_detail` through `_record_link_sent` and into `SendLinkResponse(...)` ctor.
- **PATTERN**: see existing `_record_link_sent` signature at line 1127–1132. Add the new param keyword-only.
- **GOTCHA**: `result.get("reason")` is the field returned by `send_message` for soft-fails (per `sms_service.py:599-602`). For 24h-dedup soft-fails, the reason is `"duplicate_message_within_24_hours"` (verify by grepping for the literal in `services/sms_service.py`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_invoice_service_send_link.py src/grins_platform/tests/unit/test_invoice_service.py -v`

### Phase 6 — Integration test + manual e2e

#### Task 6.1: CREATE `src/grins_platform/tests/integration/test_master_plan_e2e_signoff_2026_05_04.py`

- **IMPLEMENT**: One integration test that runs the full happy path in-process:
  1. Create estimate (admin auth)
  2. POST `/estimates/{id}/send` → expect 200, `status='sent'`
  3. GET `/portal/estimates/<token>` → expect populated customer name + created_at
  4. POST `/portal/estimates/<token>/approve` → expect 200, `status='approved'`, auto-job created
  5. Mock CallRail inbound payload with NO `created_at` (only `sent_at`) + Y body → POST `/webhooks/callrail/inbound` → expect 200, appointment confirmed
  6. Mock Stripe `payment_intent.succeeded` event with `metadata.invoice_id` → POST `/webhooks/stripe` → expect invoice `status='paid'`, receipt SMS triggered
  7. Mock Stripe `checkout.session.completed` with no phone → expect customer created with synthetic phone matching `[0-9]{10}`
- **PATTERN**: existing integration tests `test_callrail_webhook_endpoint.py`, `test_stripe_webhook_payment_links.py`, `test_invoice_integration.py`.
- **GOTCHA**: this is a "smoke" test — don't try to assert every field; assert the 6 status transitions. If CI starts flaking, demote to functional + integration split.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_master_plan_e2e_signoff_2026_05_04.py -v -m integration`

#### Task 6.2: Manual e2e on dev (after PR is merged to dev branch and Railway deploys)

- **IMPLEMENT**: Re-run the master plan e2e against dev:
  ```bash
  cd e2e/master-plan
  ./run-all.sh
  ```
- Confirm each of the 6 bugs is resolved:
  - Bug #1: `POST /estimates/{id}/send` returns 200; estimate shows `status='sent'` after.
  - Bug #2: portal page shows "Prepared for: Test User" + a real date.
  - Bug #2b: `POST /invoices/{id}/send-link` shows actual reject reason in `attempted_channels`.
  - Bug #3: human Y reply triggers webhook 200 + appointment confirmed.
  - Bug #4: simulator + real Y replies do NOT 500.
  - Bug #5: Apple-Pay payment marks invoice PAID; receipt SMS fires.
  - Bug #6: Apple-Pay agreement signup with no phone creates customer with 10-digit synthetic.
- **VALIDATE**: each repro from the bughunt's "Repro" sections returns expected status (200 instead of 500/400; populated DB state).

#### Task 6.3: UPDATE `bughunt/2026-05-04-master-plan-run-findings.md` with sign-off annotations

- **IMPLEMENT**: For each bug section, append:
  ```markdown
  **Status**: ✅ RESOLVED 2026-MM-DD by commit `<sha>` (Phase {N} of umbrella).
  ```
- **VALIDATE**: `git log --oneline | head -10` shows the umbrella commits.

---

## TESTING STRATEGY

### Unit Tests

- **Bug #5**: 2 new unit tests (PI metadata in params + checkout-session fallback handler).
- **Bug #6**: 1 new PBT (hypothesis) test for synthetic phone shape + 1 deterministic test.
- **Bug #3**: 3 new unit tests for the timestamp fallback chain (created_at / sent_at / receipt time).
- **Bug #1**: 2 new unit tests for `Recipient.from_adhoc(customer_id=...)` + 1 mock-driven test asserting all 4 estimate sites thread the FK.
- **Bug #4**: 2 new unit tests (empty `provider_sid` coerced to None + regression guard for real value pass-through).
- **Bug #2 / 2b**: existing `test_portal_api.py` extended; `test_invoice_service_send_link.py` extended.

Mark every new test `@pytest.mark.unit` (or set `pytestmark = pytest.mark.unit` at file level).

### Functional Tests

- Extend `tests/functional/test_estimate_email_send_functional.py` to assert the `SentMessage` row written by `/estimates/{id}/send` has a non-null `customer_id`.
- Extend `tests/functional/test_estimate_operations_functional.py` to assert `/portal/estimates/<token>/approve` flips `status` to `approved` and persists `approved_at` and `job_id` (this is the regression guard for Bug #1's session-poison rollback).

### Integration Tests

- New: `test_master_plan_e2e_signoff_2026_05_04.py` (Task 6.1).
- Extend: `test_callrail_webhook_endpoint.py` with the new `created_at`-absent fixture (Task 2.4).

### Edge Cases

- Bug #5 — Stripe Payment Link with subscription line items: confirm `payment_intent_data` is omitted (subscription path is incompatible). Today's `_build_line_items` doesn't produce subscriptions, but add an assert in the unit test that the params dict shape doesn't break if subscription support is later added.
- Bug #5 — `checkout.session.completed` fallback fires twice (once for the PI path, once for the session path): idempotency check via `invoice.status == PAID` must short-circuit the second call. Test this explicitly.
- Bug #6 — collision: two different Stripe events hashed to the same 10-digit synthetic — extremely rare (1-in-10^10) but possible. The `find_by_phone` lookup before `CustomerCreate` (line 318) means a collision would attach the second customer to the first synthetic-keyed customer. Mitigation: prefix synthetics with `5550xxxxxx` (NANP "fictitious" prefix) so they're segregated from real numbers and we can detect/clean later.
- Bug #3 — clock skew: if CallRail's `sent_at` is more than `CLOCK_SKEW_SECONDS` (default 300s) old, the freshness check still rejects. That's intentional — we don't want to accept arbitrarily old replays.
- Bug #1 — internal staff send when no `is_internal=True` is passed: should this be a hard error or fallback to `SentMessage` with NULL FKs? Today's CHECK constraint forbids NULL FKs. **Recommendation: hard error in `send_automated_message` if `is_internal=False` AND both `customer_id` and `lead_id` are None — fail fast at the call site rather than poison the session.**
- Bug #4 — race: two simultaneous orphan inserts with `provider_message_id=None`: the partial index excludes NULL so both succeed (correct). The new predicate also excludes empty string so `""` is similarly tolerated.
- Bug #2 — lead branch with multi-word names (e.g. "Mary Anne O'Brien"): the split-on-first-whitespace approach already in `Recipient.from_lead` (lines 50–52) handles this correctly. Mirror it in `_to_portal_response`.

---

## VALIDATION COMMANDS

Execute every command. Each block must report zero errors before proceeding to the next phase.

### Level 1: Syntax & Style

```bash
# Backend lint + format
uv run ruff check --fix src/
uv run ruff format src/

# Backend type check (both, per pyproject)
uv run mypy src/
uv run pyright src/

# Frontend lint + typecheck
cd frontend && npm run lint && npm run typecheck && cd ..
```

### Level 2: Unit Tests

```bash
# Per-bug targeted runs (fast loop while iterating)
uv run pytest -m unit -v src/grins_platform/tests/unit/test_stripe_payment_link_service.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_stripe_payment_link_service_pi_metadata.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_webhook_checkout_session_metadata_fallback.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_webhook_phone_synthetic_fallback.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_callrail_inbound_freshness_fallback.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_recipient_from_adhoc_customer_id.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_estimate_service_send_threads_customer_fk.py
uv run pytest -m unit -v src/grins_platform/tests/unit/test_campaign_response_orphan_empty_provider_sid.py

# Full unit suite (regression guard)
uv run pytest -m unit -v
```

### Level 3: Integration Tests

```bash
# Targeted
uv run pytest -m integration -v src/grins_platform/tests/integration/test_callrail_webhook_endpoint.py
uv run pytest -m integration -v src/grins_platform/tests/integration/test_master_plan_e2e_signoff_2026_05_04.py
uv run pytest -m integration -v src/grins_platform/tests/integration/test_invoice_integration.py

# Full integration suite
uv run pytest -m integration -v
```

### Level 4: Migration Roundtrip (Bug #4 only)

```bash
# Local Postgres only — never against railway.app
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```

### Level 5: Manual E2E on Dev

```bash
# Pre-flight: make sure dev backend has redeployed with this branch
curl -s https://grins-dev-dev.up.railway.app/health | jq .

# Re-run the master plan
cd e2e/master-plan && ./run-all.sh

# Spot-check Bug #1 (estimate send no longer 500s)
TOKEN=$(curl -s -X POST $API/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)
EST=$(curl -s -X POST $API/api/v1/estimates -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "customer_id":"a44dc81f-ce81-4a6f-81f5-4676886cef1a",
    "line_items":[{"description":"x","quantity":1,"unit_price":100,"amount":100}],
    "subtotal":100,"total":100
  }' | jq -r .id)
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST $API/api/v1/estimates/$EST/send -H "Authorization: Bearer $TOKEN"
# Expect: HTTP 200

# Spot-check Bug #5 (PI metadata flow)
# After paying a Stripe Payment Link with Apple Pay, expect:
curl -s $API/api/v1/invoices/$INV -H "Authorization: Bearer $TOKEN" | jq '.status, .paid_at'
# Expect: "paid", "<iso timestamp>"

# Spot-check Bug #2 (portal customer name + date)
curl -s $API/api/v1/portal/estimates/$TOKEN | jq 'keys'
# Expect: includes customer_first_name, customer_last_name, customer_email, created_at
```

---

## ACCEPTANCE CRITERIA

- [ ] Bug #1: `POST /estimates/{id}/send` returns 200; SentMessage row has non-null `customer_id` (or `lead_id`); `/portal/estimates/<token>/approve` flips `status='approved'` and persists `approved_at`+`job_id`.
- [ ] Bug #2: `GET /api/v1/portal/estimates/<token>` returns `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at`. Frontend renders "Prepared for: First Last" and a real date.
- [ ] Bug #2b: `POST /invoices/{id}/send-link` returns the actual SMS reject reason (e.g. `dedup_24h`, `opted_out`) in `attempted_channels`, not a hardcoded `provider_error`.
- [ ] Bug #3: CallRail inbound webhook with NO `created_at` (only `sent_at`) returns 200; webhook with NEITHER falls back to receipt time and emits `sms.webhook.timestamp_fallback_used` log.
- [ ] Bug #4: orphan-row insert with empty `provider_message_id` succeeds (coerced to None); migration roundtrip clean.
- [ ] Bug #5: Stripe `payment_intent.succeeded` event for an Apple-Pay payment flips invoice → PAID; `payment_intent_data.metadata.invoice_id` present in `PaymentLink.create` params; `checkout.session.completed` fallback also reconciles.
- [ ] Bug #6: Apple-Pay agreement signup with no `customer_details.phone` creates a customer with a 10-digit synthetic phone that passes `normalize_phone`.
- [ ] Zero ruff violations.
- [ ] Zero mypy + pyright errors.
- [ ] All new and existing tests pass.
- [ ] Manual e2e on dev: 6 spot-checks above all pass.
- [ ] No regressions in `tests/integration/test_callrail_webhook_endpoint.py` or `tests/unit/test_stripe_payment_link_service.py`.

---

## COMPLETION CHECKLIST

- [ ] Phase 1 (Bug #5 + #6) committed
- [ ] Phase 2 (Bug #3) committed
- [ ] Phase 3 (Bug #1) committed
- [ ] Phase 4 (Bug #4 + migration) committed
- [ ] Phase 5 (Bug #2 + #2b) committed
- [ ] Phase 6 (integration test + manual e2e) committed
- [ ] All 6 phases pass Level 1+2+3 validation
- [ ] Bug #4 migration roundtrip (Level 4) clean
- [ ] Manual e2e on dev (Level 5) passes for all 6 bugs
- [ ] `bughunt/2026-05-04-master-plan-run-findings.md` updated with `RESOLVED` annotations
- [ ] Memory updated: add `project_master_plan_2026_05_04_resolved.md` describing what shipped (so future runs don't re-investigate)
- [ ] Single PR opened against `main` titled `fix(e2e-signoff): umbrella resolution for 6 master-plan-run bugs (2026-05-04)`

---

## NOTES

### Design Decisions

1. **Why one umbrella and not 6 PRs?** Matches the existing umbrella commit pattern (`dadbacc fix(e2e-signoff): umbrella resolution for 6 sign-off bugs (B-1…B-6)`) and the user's saved feedback (memory: "for refactors in this area, user prefers one bundled PR over many small ones"). Each phase is one commit so reviewers can bisect if a regression appears.

2. **Why fix Bug #5 first?** It's a one-line fix that unblocks revenue reconciliation. Fixing it first means the rest of the plan can be tested with end-to-end Apple-Pay payments without manual SQL backfill.

3. **Why coerce empty `provider_sid` to None instead of changing the partial index alone?** Defense in depth — the migration handles existing rows; the coercion handles new ones. Either alone is insufficient: the migration leaves the code path producing empty strings, and the coercion alone leaves the index vulnerable to other code paths that might still write empty strings (e.g. `sms_service.handle_inbound`).

4. **Why fall back to `sent_at` and then receipt time for CallRail?** CallRail's docs are inconsistent across webhook types. `sent_at` is the documented field per the captured payloads in `feature-developments/CallRail collection/`. Receipt time as a final fallback preserves replay protection because Redis/DB resource_id dedup is the actual replay barrier — `created_at` is just a clock-skew guard.

5. **Why `is_internal=True` for staff sends instead of NULL FKs?** Internal staff notifications aren't customer-facing audit rows. Skipping the `SentMessage` write avoids a CHECK-constraint relaxation that would weaken the invariant for everyone.

6. **Why hash-derived synthetic for Stripe phones?** Deterministic — the same event ID always maps to the same synthetic, so retries find the same customer instead of creating duplicates. 10 digits passes the validator. Optional improvement: prefix `5550` (NANP fictitious) so synthetic customers are visually identifiable.

### Risks

- **Risk 1** (Bug #5): the `checkout.session.completed` fallback could double-process a payment if both PI and session events arrive. **Mitigated** in Task 1.3 via idempotency check `invoice.status == PAID` short-circuit, mirrored from line 1086–1093.
- **Risk 2** (Bug #1): the `is_internal=True` path skips the `SentMessage` write. The existing test `test_estimate_internal_notification.py` only asserts `sms.send_automated_message.assert_awaited_once()` (not that a SentMessage row is created), so the test stays green. **Resolved** — no operator gate.
- **Risk 3** (Bug #3): receipt-time fallback could mask a CallRail config issue. **Mitigated** by the `sms.webhook.timestamp_source` log line emitted on every request — Railway logs allow per-request observation. Set up an alert in Railway if `timestamp_source="receipt_time"` fires for >1% of inbound webhooks.
- **Risk 4** (Bug #4 migration): pre-existing rows with `provider_message_id=''` would collide on index recreation. **Mitigated** in Task 4.2 by the pre-flight backfill `UPDATE campaign_responses SET provider_message_id = NULL WHERE provider_message_id = ''` inside `upgrade()`.
- **Risk 5** (Bug #1, eager-load): Task 3.6 may add `selectinload` to the estimate repo. If the codebase uses a different loader pattern (e.g. `joinedload` or AsyncSession-managed relationship loaders), follow the existing convention. Read `repositories/estimate_repository.py` first.
- **Risk 6** (Bug #2b literal type): adding `sms_failure_detail` to `SendLinkResponse` is an additive API change. Verify any frontend type that reads this response — `frontend/src/features/invoices/types/` (search for `SendLinkResponse`) — is updated to surface the new field, or just add the optional field to the TS type without rendering it (lowest-risk).

### Out of Scope (deferred to future runs, per the bughunt's "What's NOT covered")

- Phase 10 reschedule R-reply path
- Phase 11 tech-mobile on-my-way SMS
- Phase 16 contract renewals (`invoice.paid` Stripe event)
- Phase 18 resource-timeline / capacity bars
- Phase 21 dispute / refund webhooks
- Phase 22 mobile viewport regression sweep

### Confidence

**10/10** for one-pass execution. All previously open uncertainties are resolved:
1. **Internal-staff SMS policy** — resolved: ship `is_internal=True` (Task 3.1's dispatch + Task 3.5 use site). The existing test `test_estimate_internal_notification.py:71` only asserts `sms.send_automated_message.assert_awaited_once()`, so this is non-breaking.
2. **CallRail real payload shape** — resolved via `services/sms/callrail_provider.py:258-286` ("Field names verified against a real inbound payload on 2026-04-08"). The provider parser reads ONLY `resource_id`, `source_number`, `content`, `destination_number`, `thread_resource_id`, `conversation_id`. No timestamp field is reliably present. Receipt-time fallback is the load-bearing fix; replay protection lives in `webhook_processed_log` dedup.
3. **`SendLinkResponse` type widening** — resolved: add a new sibling `sms_failure_detail: str | None` field instead of widening the categorical literal, which preserves strict typing.
4. **Pre-migration data audit** — resolved: the migration includes a pre-flight `UPDATE` that backfills empty strings to NULL.
5. **Alembic head** — verified: `20260506_120000_repair_invoice_line_items_shape`. New migration revision `20260507_120000` chains cleanly.
6. **Recipient construction strategy** — resolved: dispatch in `send_automated_message` and construct `Recipient(...)` directly (mirrors `invoice_service.py:956-962`); do NOT extend `Recipient.from_adhoc` which would conflate semantics.

All 6 bugs are surgical fixes with clear success criteria, verified line numbers, and existing test infrastructure to mirror. Each phase has a precise validation command and the plan resolves each "GOTCHA" inline so the implementation agent can execute top-to-bottom without backtracking.
