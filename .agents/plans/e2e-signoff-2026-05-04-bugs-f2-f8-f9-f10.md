# Feature: E2E Sign-off Bug Resolution — Run `2026-05-04-full-real-emails` (F2, F8, F9, F10)

The following plan should be complete, but it is important to validate documentation, codebase patterns, and task sanity before implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files. The four promoted-MAJOR findings come from a real E2E run against dev — every fix has a verified reproduction path and a tightly bounded surface area.

## Feature Description

Resolve the four PROMOTED MAJOR bugs filed in `e2e-screenshots/master-plan/runs/2026-05-04-full-real-emails/E2E-SIGNOFF-REPORT.md` plus close one informational documentation drift item:

- **F2** — `EstimateResponse.rejection_reason` is silently always `None` in API responses because the ORM column is named `rejected_reason` and the Pydantic schema field is named `rejection_reason` with no alias bridge. Customer rejection reasons therefore never surface to admins.
- **F8** — Stripe Payment Link customers receive no SMS/email receipt after paying because `_handle_checkout_invoice_payment` does not call `_send_payment_receipts` (the sibling `_handle_payment_intent_succeeded` does, but it short-circuits on `invoice.status == PAID` after checkout already reconciled).
- **F9** — `GET /api/v1/appointments?customer_id=<uuid>` silently ignores the `customer_id` filter (FastAPI drops unknown query params with no 422). UI/scripts get back the global appointment list.
- **F10** — `POST /appointments/{id}/collect-payment` for cash/check/Venmo/Zelle never sets `Job.payment_collected_on_site=True`. The duplicate-invoice guard at `invoice_service.generate_from_job` relies on this flag; cash-paid jobs allow generating a second invoice for the same job.
- **F7 (informational)** — Master plan E11 acceptance text is stale; the code correctly logs `appointment.reschedule_rejected` (Gap 1.B) instead of the plan-described `stale_thread_reply`. Update the plan, not the code.

The other findings (F1 portal column-clipping at 1280px, F5 24h dedup blocks cancellation acknowledgment) require multi-viewport visual diff and a product-spec decision respectively, and are deliberately **out of scope** for this plan.

## User Story

As an **admin user** of the Grin's Irrigation Platform,
I want to **see the customer's rejection reason on rejected estimates, receive parity SMS receipts on every payment method (cash/check/Venmo/Zelle/Stripe), filter appointments by customer correctly, and trust that an on-site cash collection blocks a duplicate invoice from being generated**,
So that **rejected-estimate follow-ups are informed, customers always get a payment confirmation regardless of channel, the customer-detail UI shows only that customer's appointments, and the books don't accumulate phantom duplicate invoices for already-paid work**.

## Problem Statement

Four bugs surfaced in the 2026-05-04 master-plan E2E run that compromise customer-facing trust and admin/billing data integrity:

1. **F2 — silent data loss in API response.** A Pydantic field-name mismatch causes the API to drop the rejection reason on every rejected estimate. The DB has the data; clients can't see it.
2. **F8 — Stripe-vs-other payment-method asymmetry.** Stripe Payment Link payments reconcile correctly server-side but skip the customer receipt SMS/email. Cash/check/Venmo/Zelle all fire the receipt. Customers who pay by card receive only Stripe's hosted-page confirmation and have no SMS proof their payment landed against the right invoice — driving support inquiries and "did it work?" ambiguity.
3. **F9 — silently ignored query param.** Calling `GET /api/v1/appointments?customer_id=<id>` returns appointments for OTHER customers (the underlying repository has no such filter). The UI/scripts get wrong data with no error signal.
4. **F10 — duplicate-invoice guard bypassed for non-Stripe payments.** Cash collected on-site doesn't set `Job.payment_collected_on_site=True`, so the duplicate-invoice guard at `invoice_service.py:1369` cannot fire. A subsequent `POST /invoices/generate-from-job/{job_id}` succeeds and produces a second invoice for the same job. Audit/billing/lien-eligibility paths don't know which invoice is "real". Reproduced in this run as `INV-2026-000049` (duplicate of `INV-2026-0045`).

Each bug has a precise file:line root cause and a known reproduction path documented in the sign-off report.

## Solution Statement

Apply the four targeted fixes — each is bounded, has an obvious reference pattern in the codebase, and has at least one existing test that needs extension or mirroring:

1. **F2** — Add `validation_alias=AliasChoices("rejection_reason", "rejected_reason")` on `EstimateResponse.rejection_reason` and set `populate_by_name=True` on the schema's `model_config`. Mirrors the `sent_message.py:39-44` pattern. ~3 lines of change.
2. **F8** — Inside `_handle_checkout_invoice_payment`, after `await self.session.flush()`, add the same try/except receipt-dispatch block that already exists in `_handle_payment_intent_succeeded:1293-1336`. Best-effort, never raises. Mirror exactly so the two handlers stay symmetric. ~25 lines.
3. **F9** — Three-layer thread-through: add `customer_id: UUID | None = Query(default=None, ...)` to the endpoint signature, plumb into the service, then into `AppointmentRepository.list_with_filters`, where it joins `Job` on `Appointment.job_id == Job.id` and filters by `Job.customer_id`. Mirror `jobs.py:298-301` for the endpoint. ~15 lines + a JOIN.
4. **F10** — In the non-Stripe branch of `collect_payment`, after `result_invoice` is settled and BEFORE `_send_payment_receipts`, set the in-memory `job.payment_collected_on_site = True` and persist via `job_repository.update(job.id, payment_collected_on_site=True)`. Mirror webhook lines 1138-1140 and 1288-1291. ~3 lines.

Plus a plan-doc update (F7) noting the audit-discriminator drift.

Every fix includes either a new unit test or extends an existing one. No DB migrations required (column names stay; F2 is schema-layer only). No frontend change required.

## Feature Metadata

**Feature Type**: Bug Fix (4 PROMOTED MAJOR + 1 doc-drift cleanup)
**Estimated Complexity**: Low–Medium (each fix is bounded; F8 has the largest surface but mirrors an existing block verbatim)
**Primary Systems Affected**:
- `schemas/estimate.py` (F2)
- `api/v1/webhooks.py` Stripe handler parity (F8)
- `api/v1/appointments.py` + `services/appointment_service.py` + `repositories/appointment_repository.py` (F9)
- `services/appointment_service.py` `collect_payment` non-Stripe branch (F10)
- `.agents/plans/master-e2e-testing-plan.md` (F7 doc cleanup)

**Dependencies**: None new. All changes use already-imported types (`UUID`, `Query`, `AliasChoices`, `Job`, `AppointmentService`, `AppointmentRepository`, `JobRepository`).

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**F2 — Estimate rejection_reason mismatch:**
- `src/grins_platform/models/estimate.py:129` — ORM column `rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)` (DO NOT rename — used by migration)
- `src/grins_platform/migrations/versions/20260324_100100_crm_create_new_tables.py:297` — DB column literally named `rejected_reason`. Do not write a rename migration.
- `src/grins_platform/schemas/estimate.py:270` — `model_config = ConfigDict(from_attributes=True)` — needs `populate_by_name=True` added
- `src/grins_platform/schemas/estimate.py:319-322` — the field that needs the alias added
- `src/grins_platform/services/estimate_service.py:539-579` — service writes `rejected_reason=reason` to DB (line ~543) and calls `EstimateResponse.model_validate(updated)` (line ~578). Service is correct; do not change.
- `src/grins_platform/schemas/sent_message.py:26` — pattern: `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`
- `src/grins_platform/schemas/sent_message.py:39-44` — pattern: `validation_alias=AliasChoices("content", "message_content")`
- `src/grins_platform/schemas/sms.py:43-50` — alternative `Field(..., alias="…")` pattern + `model_config = {"populate_by_name": True}`
- `src/grins_platform/tests/unit/test_estimate_service.py:459-485` — existing reject-flow unit test — **extend or mirror this**, do not delete
- `src/grins_platform/tests/unit/test_estimate_service.py:62-130` — the `_make_estimate_mock` helper that sets `est.rejected_reason = rejected_reason` on line ~124

**F8 — Stripe checkout missing receipt dispatch:**
- `src/grins_platform/api/v1/webhooks.py:1022-1147` — full `_handle_checkout_invoice_payment` (you will inject the receipt block at the very end, after `await self.session.flush()` on line ~1141)
- `src/grins_platform/api/v1/webhooks.py:1252-1259` — PI-handler idempotency short-circuit (`if invoice.status == InvoiceStatus.PAID.value: return`) — explains why the existing PI dispatch is unreachable after a checkout reconciliation
- `src/grins_platform/api/v1/webhooks.py:1293-1336` — **the EXACT receipt-dispatch block to mirror.** Copy literally; same `noqa: PLC0415`/`SLF001` comments, same `try`/`except Exception as exc:`, same logger key.
- `src/grins_platform/services/appointment_service.py:2150-2159` — `_send_payment_receipts(self, job: Job, invoice: Invoice, amount: Decimal) -> None` — note the signature; pass `paid_invoice` (the freshly re-fetched row), not the stale pre-payment `invoice`.
- `src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py:242-280+` — `test_payment_intent_succeeded_fires_customer_receipt` — **mirror this for a new `test_checkout_session_completed_fires_customer_receipt` test**

**F9 — GET /appointments customer_id ignored:**
- `src/grins_platform/api/v1/appointments.py:166-257` — `list_appointments` endpoint — add `customer_id: UUID | None = Query(default=None, ...)` and plumb through
- `src/grins_platform/services/appointment_service.py:831-864` — `list_appointments` service method — add `customer_id` parameter, forward
- `src/grins_platform/repositories/appointment_repository.py:270-349` — `list_with_filters` — accept `customer_id`, JOIN on `Job` when present
- `src/grins_platform/api/v1/jobs.py:298-301` — pattern: `customer_id: UUID | None = Query(default=None, description="Filter by customer ID")`
- `src/grins_platform/api/v1/estimates.py:106-133` — pattern: full thread-through of `customer_id` from endpoint → service → repository
- `src/grins_platform/tests/integration/test_appointment_integration.py:126-150` — fixture/test pattern for appointment integration tests
- `src/grins_platform/models/job.py` — confirm `Job.customer_id` column name (it is `customer_id` per repo conventions)
- `src/grins_platform/models/appointment.py` — confirm `Appointment.job_id` FK (already used by repo selectinload at line ~340)

**F10 — collect_payment doesn't set payment_collected_on_site:**
- `src/grins_platform/services/appointment_service.py:1990-2148` — full `collect_payment`. Inject the flag-set inside the `if not defer_to_webhook:` branch (i.e., NOT for Stripe-deferred methods, since the webhook already handles those).
- `src/grins_platform/services/invoice_service.py:1369-1376` — duplicate-invoice guard `if job.payment_collected_on_site: raise InvalidInvoiceOperationError(...)` — this is the consumer of the flag.
- `src/grins_platform/api/v1/webhooks.py:1134-1140` — Stripe checkout handler reference pattern: `if job is not None: job.payment_collected_on_site = True; await self.session.flush()`
- `src/grins_platform/api/v1/webhooks.py:1284-1291` — Stripe PI handler reference pattern (identical structure)
- `src/grins_platform/tests/unit/test_appointment_service_crm.py:703-766` — `test_collect_payment_with_no_existing_invoice_creates_new` — **extend to assert the flag is set after collect_payment for cash/check/Venmo/Zelle**
- The service has `self.job_repository: JobRepository` — use `await self.job_repository.update(job_id=job.id, data={"payment_collected_on_site": True})`. **The signature is `update(self, job_id: UUID, data: dict[str, Any]) -> Job | None`** (verified at `repositories/job_repository.py:179-221`). Do NOT pass field names as kwargs — that would be a runtime error. Reference call sites: `services/schedule_clear_service.py:134` (`await self.job_repository.update(job_id=job_id, data={"status": JobStatus.TO_BE_SCHEDULED.value})`) and `services/schedule_clear_service.py:333`.

**F7 — plan doc update:**
- `.agents/plans/master-e2e-testing-plan.md` — find the E11 acceptance line that says "logged as `stale_thread_reply`" (per F7 in the report). Update inline to read "logged as `appointment.reschedule_rejected` (Gap 1.B state guard)" with a one-line note pointing at `services/job_confirmation_service.py:461-490`.
- `src/grins_platform/services/job_confirmation_service.py:461-490` — Gap 1.B state guard that emits `appointment.reschedule_rejected` (already correct; do not modify).
- `src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py` — existing functional coverage; do not modify.

### New Files to Create

- **None.** All four fixes are edits to existing files. The doc cleanup (F7) edits a plan file. New tests should live alongside their existing siblings:
  - `src/grins_platform/tests/unit/test_estimate_service.py` — add `test_reject_via_portal_response_surfaces_rejection_reason` (F2)
  - `src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py` — add `test_checkout_session_completed_fires_customer_receipt` (F8)
  - `src/grins_platform/tests/integration/test_appointment_integration.py` — add a test method asserting `customer_id` filter narrows results to the requested customer (F9)
  - `src/grins_platform/tests/unit/test_appointment_service_crm.py` — extend the existing parametrized cash/check/Venmo/Zelle test to assert `payment_collected_on_site` is set (F10)

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [Pydantic v2 — `validation_alias` and `AliasChoices`](https://docs.pydantic.dev/latest/concepts/alias/#aliaspath-and-aliaschoices)
  - Specific section: "AliasChoices" — accepts multiple input names for one field
  - Why: F2 needs to accept either the new `rejection_reason` (forward-compatible JSON in) or the ORM-derived `rejected_reason` (when `model_validate(orm)` is called). `populate_by_name=True` in `model_config` is mandatory for both ingress paths to work.
- [Pydantic v2 — `model_config` `populate_by_name`](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.populate_by_name)
  - Specific section: `populate_by_name`
  - Why: Without this flag, Pydantic only honors the alias and rejects the canonical field name. We want both to work.
- [FastAPI — Query parameters](https://fastapi.tiangolo.com/tutorial/query-params/)
  - Specific section: "Query parameter values"
  - Why: F9 — confirm that adding a typed `Query(default=None)` parameter is the correct way to introduce optional filters; FastAPI silently drops unknown params (which is exactly the F9 root cause).
- [SQLAlchemy 2.0 — `select(...).join(...)`](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html#joining-related-entities)
  - Specific section: ORM-Style Joins
  - Why: F9 — the repository must `.join(Job, Appointment.job_id == Job.id)` when `customer_id` is provided, then `.where(Job.customer_id == customer_id)`.
- [Stripe — `checkout.session.completed` event](https://stripe.com/docs/api/checkout/sessions/object) and [Stripe — Payment Link metadata](https://stripe.com/docs/payment-links/customer-tracking)
  - Why: F8 — confirms the canonical Stripe event order for Payment Links is `checkout.session.completed` → `payment_intent.succeeded`, validating that the receipt dispatch must be wired into the checkout handler (the PI handler short-circuits on already-PAID invoices).

### Patterns to Follow

#### Naming conventions

- Pydantic field names: `snake_case`. Aliases for backward-compat use `validation_alias=AliasChoices(...)` (Pydantic v2 idiom in this repo).
- Endpoint query params: `customer_id: UUID | None = Query(default=None, description="…")` — see `jobs.py:298-301`.
- Service method signature changes: keyword-only kwargs added at the end with `None` defaults to preserve callers (Python's `*` separator is not used in these particular service methods, but mirror the existing argument order).

#### Pydantic v2 alias bridge — F2 reference

From `src/grins_platform/schemas/sent_message.py:26, 39-44`:

```python
model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ... other fields ...

content: str | None = Field(
    default=None,
    max_length=5000,
    description="Message content",
    validation_alias=AliasChoices("content", "message_content"),
)
```

Apply identically to `EstimateResponse.rejection_reason` with `AliasChoices("rejection_reason", "rejected_reason")`. Imports needed: `from pydantic import AliasChoices, ConfigDict, Field` (verify what's already imported at top of `schemas/estimate.py` first).

#### Stripe webhook receipt-dispatch block — F8 reference

From `src/grins_platform/api/v1/webhooks.py:1293-1336`. **Copy literally — same comment, same try/except, same logger key, same noqa pragmas.** The only change is that in the checkout handler we already have `job` in scope (set at line ~1138) and have just called `record_payment` + `update(stripe_payment_link_active=False)`, so we should re-fetch `paid_invoice = await invoice_repo.get_by_id(invoice_id)` to get the post-payment row.

```python
# At the END of _handle_checkout_invoice_payment, AFTER `await self.session.flush()`:

# Architecture C parity: cash/check/etc. fire a customer receipt
# SMS+email from AppointmentService._send_payment_receipts. Stripe
# Payment Link payments arrive here via checkout.session.completed
# (the PaymentIntent succeeded handler short-circuits once invoice
# is PAID), so receipts must fire here for parity. Best-effort —
# a failure logs and returns.
try:
    from grins_platform.repositories.appointment_repository import (  # noqa: PLC0415
        AppointmentRepository,
    )
    from grins_platform.services.appointment_service import (  # noqa: PLC0415
        AppointmentService,
    )

    paid_invoice = await invoice_repo.get_by_id(invoice_id)
    if paid_invoice is not None and job is not None:
        appt_service = AppointmentService(
            appointment_repository=AppointmentRepository(session=self.session),
            job_repository=JobRepository(session=self.session),
            invoice_repository=invoice_repo,
        )
        await appt_service._send_payment_receipts(  # noqa: SLF001
            job,
            paid_invoice,
            amount,
        )
except Exception as exc:
    self.logger.warning(
        "stripe.webhook.receipt_dispatch_failed",
        payment_intent=masked,
        invoice_id=str(invoice_id),
        error=str(exc),
    )
```

#### Three-layer query-param thread-through — F9 reference

Endpoint (mirror `api/v1/jobs.py:298-301`):

```python
customer_id: UUID | None = Query(
    default=None,
    description="Filter by customer ID (joins via job.customer_id)",
),
```

Service: forward `customer_id` to repository.

Repository: when `customer_id is not None`, JOIN `Job` and filter:

```python
if customer_id is not None:
    base_query = base_query.join(Job, Appointment.job_id == Job.id).where(
        Job.customer_id == customer_id,
    )
```

`Job` is already imported in the repository (used by `selectinload(Appointment.job).selectinload(Job.customer)`).

#### Setting Job.payment_collected_on_site from a service — F10 reference

The service layer does NOT have direct `self.session` access (the webhooks do). Use the repository:

```python
await self.job_repository.update(job.id, payment_collected_on_site=True)
```

Place it inside `if not defer_to_webhook:` (i.e., AFTER `result_invoice` is finalized and BEFORE the `_send_payment_receipts` try block). This guarantees the flag is set even if SMS/email dispatch later fails (the `_send_payment_receipts` block is `try/except`).

#### Error handling

- Webhook receipt dispatch is best-effort: `try: ... except Exception as exc: self.logger.warning(...)`. Do NOT re-raise — a downstream SMS hiccup must never undo the recorded payment.
- Service-layer flag set is NOT in a try/except: a `JobRepository.update` failure should bubble up and roll back the transaction. The flag and the invoice-update should land or fail together.

#### Logging pattern

- Webhook handlers use `self.log_started(...)`, `self.log_completed(...)`, `self.logger.warning(...)` with structured kwargs. Mirror the existing keys (`stripe_event_id`, `payment_intent`, `invoice_id`).
- Services use `self.log_started(...)`, `self.log_completed(...)`, `self.log_rejected(...)`. F10 already logs `collect_payment`; do not add a new log line for the flag set — it's part of the same logical operation.

#### Testing patterns

- Unit tests use `pytest.mark.unit` + `pytest.mark.asyncio`, `AsyncMock` for repositories, `SimpleNamespace` or `_make_*_mock` helpers for ORM stand-ins.
- The existing test file `test_appointment_service_crm.py:703-766` is parametrized over `(amount, method)` for cash/check/Venmo/Zelle — extend this same parametrization to assert `job_repo.update` was awaited with `payment_collected_on_site=True`.
- `test_stripe_webhook_payment_links.py:242` is the verbatim mirror target for F8's new test.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — verify-before-edit

**Tasks:**

- Read each "Relevant Codebase Files" entry above and confirm line numbers still match (the report was written at SHA `7495d88`; verify nothing has shifted).
- Confirm `from pydantic import AliasChoices` is or is not already imported in `schemas/estimate.py` — adjust the import line accordingly.
- Confirm `Job` is already imported in `repositories/appointment_repository.py` (used by `selectinload(Appointment.job).selectinload(Job.customer)` at ~line 340 — should be importable).
- Confirm `JobRepository.update(...)` signature accepts arbitrary kwargs (it does — used widely in the codebase, but spot-check before the F10 fix).

### Phase 2: Core Implementation

**F2 — Schema alias bridge (~3 lines)**

- `UPDATE` `schemas/estimate.py:270` — change `model_config = ConfigDict(from_attributes=True)` to `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`.
- `UPDATE` `schemas/estimate.py:319-322` — replace with:
  ```python
  rejection_reason: str | None = Field(
      default=None,
      description="Rejection reason",
      validation_alias=AliasChoices("rejection_reason", "rejected_reason"),
  )
  ```
- `UPDATE` `schemas/estimate.py` import block — ensure `AliasChoices` is imported from `pydantic`.

**F8 — Stripe checkout handler receipt dispatch (~25 lines)**

- `UPDATE` `api/v1/webhooks.py` `_handle_checkout_invoice_payment` (around line 1141, immediately AFTER `await self.session.flush()` and BEFORE the trailing `self.log_completed(...)`) — insert the verbatim receipt-dispatch try/except block from the "Patterns to Follow" section above.
- Cross-check: ensure the imports inside the `try:` block use `noqa: PLC0415` exactly as in the PI handler. Cross-check the `noqa: SLF001` on `_send_payment_receipts`.
- Ensure `paid_invoice = await invoice_repo.get_by_id(invoice_id)` is fetched fresh inside the try block (not reusing the stale pre-payment `invoice` object).

**F9 — Three-layer customer_id thread-through (~15 lines + JOIN)**

- `UPDATE` `api/v1/appointments.py:166-238` (`list_appointments`) — add `customer_id: UUID | None = Query(default=None, description="Filter by customer ID")` to the signature (alphabetically near the other ID filters). Pass `customer_id=customer_id` into `service.list_appointments(...)`. Add `"customer_id": str(customer_id) if customer_id else None` into the `filters` dict on the `_endpoints.log_started` call.
- `UPDATE` `services/appointment_service.py:831-864` (`list_appointments`) — add `customer_id: UUID | None = None` parameter (place near `staff_id`/`job_id`); forward `customer_id=customer_id` into `self.appointment_repository.list_with_filters(...)`.
- `UPDATE` `repositories/appointment_repository.py:270-349` (`list_with_filters`) — add `customer_id: UUID | None = None` parameter; in the filter section (after `if job_id is not None:`), add:
  ```python
  if customer_id is not None:
      base_query = base_query.join(Job, Appointment.job_id == Job.id).where(
          Job.customer_id == customer_id,
      )
  ```
- Verify `Job` import at top of repository file.

**F10 — Set Job.payment_collected_on_site in collect_payment (~3 lines)**

- `UPDATE` `services/appointment_service.py` `collect_payment` — inside the `if not defer_to_webhook:` block (around the location where the post-existing-invoice update or new-invoice creation completes), AFTER `result_invoice` is finalized and BEFORE the `try: await self._send_payment_receipts(...)`, add:
  ```python
  await self.job_repository.update(
      job_id=job.id,
      data={"payment_collected_on_site": True},
  )
  ```
- Confirm position — the flag must land before the receipt-dispatch try block so a receipt-send failure does not leave the flag unset.

**F7 — Plan doc cleanup (1 line + 1 sentence)**

- `UPDATE` `.agents/plans/master-e2e-testing-plan.md` — find the P9/E11 acceptance phrasing referencing `stale_thread_reply` and rewrite to: "logged as `appointment.reschedule_rejected` via Gap 1.B state guard at `services/job_confirmation_service.py:461-490`. (Plan was previously phrased as `stale_thread_reply`; code is correct, plan was stale.)"

### Phase 3: Integration

**Tasks:**

- F8 only: confirm the new `appt_service` instance constructed inside the checkout handler does not conflict with any `appt_service` constructed earlier in the same handler. The checkout handler currently does NOT construct one, so this is a new local. It's deliberately scoped inside the try block and has no lingering effect.
- F9: no router/registration change required — endpoint signature update only.
- F2: no migration required — DB column unchanged.
- F10: no migration; `JobRepository.update` already exists and is widely used.

### Phase 4: Testing & Validation (unit + integration)

**Tasks:**

- **F2 unit test (new)**: in `tests/unit/test_estimate_service.py`, add `test_reject_via_portal_response_surfaces_rejection_reason`. Mirror the structure of `test_reject_via_portal_also_sets_token_readonly` (lines 459-485). Build `updated` via `_make_estimate_mock` with `rejected_reason="Too expensive"` (the helper at line 124 already supports this kwarg). Call `await svc.reject_via_portal(token, reason="Too expensive")`. Assert the returned `EstimateResponse.rejection_reason == "Too expensive"`.
- **F8 unit test (new)**: in `tests/unit/test_stripe_webhook_payment_links.py`, add `test_checkout_session_completed_fires_customer_receipt`. Mirror `test_payment_intent_succeeded_fires_customer_receipt` at line 242. Build a `checkout.session.completed` event with `metadata.invoice_id` set, `amount_total=25000`, `payment_intent="pi_test_checkout_receipt"`. Mock `invoice_repo.get_by_id` to return an unpaid invoice on first call and a paid invoice on the second call (the post-`record_payment` re-fetch). Mock `session.execute` to return a job. Patch `AppointmentService._send_payment_receipts` and assert it is awaited once with `(job, paid_invoice, Decimal("250"))`.
- **F8 idempotency test (extend existing)**: ensure replaying `checkout.session.completed` after invoice is already PAID does NOT double-fire receipts. The existing short-circuit at line 1102-1109 returns before reaching the new code; verify by adding an assertion.
- **F9 integration test (new)**: in `tests/integration/test_appointment_integration.py`, add a test that creates 2 customers + 2 jobs + 2 appointments (one per customer), then asserts `service.list_appointments(customer_id=customer1.id)` returns ONLY `appointment1`. Without the fix, this returns both appointments.
- **F10 unit test (extend existing)**: in `tests/unit/test_appointment_service_crm.py`, extend `test_collect_payment_with_no_existing_invoice_creates_new` (or add a sibling test) to assert `job_repo.update.assert_awaited_with(job.id, payment_collected_on_site=True)` for cash/check/Venmo/Zelle. Add an explicit negative case for Stripe-deferred methods (`PaymentMethod.CREDIT_CARD`) confirming `job_repo.update` is NOT called with that flag from `collect_payment` (the webhook handles it).
- **Cross-bug regression**: run the full unit + integration sweep to confirm no other tests assert the buggy behavior (e.g., a test that depended on `customer_id` being silently ignored, or one asserting `EstimateResponse.rejection_reason is None` even when the DB has a value — those would need updating).

### Phase 5: Real-SMS / Real-Email E2E Recreation (HUMAN-mode)

This phase recreates the live end-to-end exercises that originally surfaced F2, F8, F9, and F10. It uses **real SMS** to `+19527373312` and **real email** to `kirillrakitinsecond@gmail.com` against the dev environment — no simulator short-cuts. The aim is to ship reusable, idempotent shell scripts that an operator can run after deploying the fixes to confirm each bug stays fixed under real carrier + Stripe + Resend conditions, and to commit them as regression coverage.

**Why HUMAN-mode (not simulator)**: per `e2e/master-plan/sim/_README.md`, simulators are for CI iteration and bypass the real CallRail/Stripe/Resend integration. The four bugs in scope all involve customer-facing notifications or external-service reconciliation. Simulators would mask the very behavior we need to confirm.

**Shared rules** (HARD):
- SMS only to `+19527373312`. Email only to `kirillrakitinsecond@gmail.com`. Operator must be present at both.
- Dev-only execution. URLs must resolve to `*-dev-*.vercel.app` or `grins-dev-*.up.railway.app`. No local-only mocks.
- 24 h SMS dedup at `services/sms_service.py:344-361` is the most common false-failure source. Sequence the runs so receipt-firing scripts use a fresh seed customer, OR space runs ≥ 24 h apart, OR temporarily duplicate the seed customer for the run.
- The agent driving the script MUST pause at every HUMAN checkpoint and wait for the operator to reply / confirm. No auto-skip on timeout — silence is "stop and wait."
- No commits, pushes, or merges to `main`. Per ENVIRONMENT SAFETY rules in `master-e2e-testing-plan.md`.

**Artifact location**: `e2e/master-plan/bug-resolution-2026-05-04/` — a new directory containing one shell script per bug, a shared helper, and a README. This keeps the bug-resolution scripts physically separate from the master-plan phase scripts (which serve a different purpose: full-system sign-off across 25 phases) but reuses `_dev_lib.sh`.

**Tasks:**

- Create the new directory `e2e/master-plan/bug-resolution-2026-05-04/` with a README that lists the four scripts, their purpose, expected operator interactions (Y/R/C/STOP/payment), expected real-SMS / real-email arrivals, and post-run cleanup notes.
- Author a shared helper `_bug_lib.sh` (sources `_dev_lib.sh`) that adds:
  - A `pause_for_operator "<prompt>"` function that prints the prompt, beeps, and blocks on stdin.
  - A `assert_recent_sms <customer_id> <message_type> <max_age_seconds>` helper that polls `/api/v1/customers/{id}/sent-messages?message_type=...` and confirms a row exists newer than `now - max_age`.
  - A `assert_no_recent_sms <customer_id> <message_type> <max_age_seconds>` inverse for negative assertions.
  - A `assert_recent_email <customer_id> <subject_substring>` that polls Resend via `sim/resend_email_check.sh poll` (verification only — does NOT remove the operator-confirms-inbox checkpoint).
  - A pre-flight that verifies the seed customer's email is `kirillrakitinsecond@gmail.com` and phone is `+19527373312`; PATCH the customer record if not.
- Author per-bug scripts (next four tasks).
- Author a top-level `run-all.sh` for the directory that runs F9 → F2 → F10 → F8 in that order to maximize the dedup-window budget (F9 has no SMS; F2 sends real email but no real SMS; F10 fires `payment_receipt`; F8 needs a fresh `payment_receipt` slot, so it MUST go last or use a different customer).

**Per-script step shapes** (full step lists are in the STEP-BY-STEP section below):

- **F2 — `f2-estimate-rejection-reason-roundtrip.sh`** — drives a real lead → estimate → email-to-customer (real Resend send to allowlisted inbox) → operator clicks portal Reject → enters reason "F2 Live Verify {timestamp}" → script polls `/api/v1/estimates/{id}` and asserts `rejection_reason == "F2 Live Verify {timestamp}"`. Operator visually confirms the rejection email arrived. No SMS.
- **F8 — `f8-stripe-payment-link-receipt.sh`** — drives a fresh test customer (so seed customer's 24 h `payment_receipt` slot stays available for other tests) → creates a $1.00 invoice → `POST /invoices/{id}/send-link` → operator receives SMS at `+19527373312` with the link → operator pays via test card 4242 4242 4242 4242 (any future expiry, any CVC) → script polls `/api/v1/customers/{id}/sent-messages?message_type=payment_receipt` for ≤ 60 s and asserts a row appears with `sent_at` after the Stripe pay → operator visually confirms the receipt SMS landed on the phone. **Pre-fix: this assertion fails (no receipt SMS arrives). Post-fix: assertion passes within ~30 s.** Also asserts `payment_receipt` email arrives at allowlisted inbox.
- **F9 — `f9-appointments-customer-id-filter.sh`** — pure API exercise (no SMS). Creates 2 customers, 2 jobs, 2 appointments. Calls `GET /api/v1/appointments?customer_id={c1}&page_size=20` and asserts every returned item's `job.customer_id == c1`. Calls again with `customer_id={c2}` and asserts the same. Calls without `customer_id` and asserts both appointments appear. **Pre-fix: filtered call returns both customers' rows. Post-fix: filtered call returns only the targeted customer's row.** Cleanup leaves the two customers in dev as fixture data.
- **F10 — `f10-collect-payment-flag-and-duplicate-guard.sh`** — driven against the seed customer. Creates an appointment + job (no invoice yet). `POST /appointments/{apt}/collect-payment {payment_method:"cash", amount:50}` → operator receives the cash `payment_receipt` SMS at `+19527373312` and visually confirms → script asserts `GET /api/v1/jobs/{job}` returns `payment_collected_on_site: true` → script attempts `POST /api/v1/invoices/generate-from-job/{job}` and asserts a 4xx response with the `InvalidInvoiceOperationError` message. **Pre-fix: flag is `false`, duplicate-invoice creation succeeds with HTTP 201. Post-fix: flag is `true`, duplicate creation rejected.** Repeat once each for `check`, `venmo`, `zelle` on a different fresh job (to dodge the 24 h `payment_receipt` dedup, the script either spaces these runs or uses 4 different customers; default behavior is to use the seed customer for `cash` only and stub the other 3 methods as API-only assertions on the flag without expecting the receipt SMS).

**Risk: 24 h dedup management**: F10's full 4-method test cannot cleanly fire 4 real `payment_receipt` SMS to the same phone in a single run. Acceptable strategies:
1. Run only `cash` with a real-SMS check; assert the flag set + duplicate-guard rejection for all 4 methods via API-only checks.
2. Stand up 4 throwaway test customers, all with phone `+19527373312` (allowlisted) and email `kirillrakitinsecond+tag-NN@gmail.com` (NOTE: per Bug F2 sister observation in the report — `email_service.py:135` rejects plus-aliases on the email allowlist). So plus-aliases will NOT work for email. Phone allowlist may be more permissive — verify before scripting.
3. Space runs ≥ 24 h apart.

The plan defaults to strategy (1) — real SMS only on `cash`, API-only assertions on the other 3 methods — to keep a single-run script practical. Document the strategy in the script's header comment so operators know why they only receive 1 SMS during a 4-method run.



IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: VERIFY current line numbers + imports

- **IMPLEMENT**: Open each file in "Relevant Codebase Files" and confirm the line numbers still match (drift since SHA `7495d88` is possible). Check imports at the top of `schemas/estimate.py`, `repositories/appointment_repository.py`, and `api/v1/webhooks.py`.
- **PATTERN**: N/A — verification step
- **IMPORTS**: Confirm `AliasChoices` is or is not present in `pydantic` import in `schemas/estimate.py`. Confirm `Job` is imported in `repositories/appointment_repository.py`.
- **GOTCHA**: If line numbers drifted, update the plan's task references mentally before applying edits — don't blindly apply by line number.
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.estimate import EstimateResponse; print(EstimateResponse.model_fields['rejection_reason'])"`

### Task 2: UPDATE `schemas/estimate.py` — F2 schema alias

- **IMPLEMENT**: Change `model_config` to `ConfigDict(from_attributes=True, populate_by_name=True)`. Add `validation_alias=AliasChoices("rejection_reason", "rejected_reason")` to the `rejection_reason` field. Add `AliasChoices` to the `pydantic` import line.
- **PATTERN**: `src/grins_platform/schemas/sent_message.py:26, 39-44`
- **IMPORTS**: `from pydantic import AliasChoices, ConfigDict, Field` (extend existing import)
- **GOTCHA**: Do NOT rename the ORM column (`models/estimate.py:129`) and do NOT write a migration. The schema is the only mismatch; the DB has the correct data already. Order of `AliasChoices` matters: put the canonical name first (`"rejection_reason"`) so JSON inputs using the new name still validate; the second choice (`"rejected_reason"`) is what Pydantic uses when `from_attributes=True` walks the ORM and finds `rejected_reason` (the column name). `populate_by_name=True` is REQUIRED in `model_config` for this dual-key behavior — without it, Pydantic only honors the alias path. **Verified working pattern: `schemas/sent_message.py:26` (`model_config = ConfigDict(from_attributes=True, populate_by_name=True)`) + `:39-44` (`validation_alias=AliasChoices("content", "message_content")`).** This is the only existing usage of `validation_alias`/`AliasChoices` in `schemas/`; mirror it byte-for-byte.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service.py -v -k reject`

### Task 3: ADD F2 unit test — `test_reject_via_portal_response_surfaces_rejection_reason`

- **IMPLEMENT**: In `tests/unit/test_estimate_service.py`, mirror the structure of the existing reject-flow test at line 459-485. Build `updated = _make_estimate_mock(estimate_id=estimate.id, status=EstimateStatus.REJECTED.value, rejected_at=now, rejected_reason="Too expensive", token_readonly=True)`. After calling `await svc.reject_via_portal(token, reason="Too expensive")`, assert the returned response object's `rejection_reason == "Too expensive"`. (Note: depending on how the existing test asserts on the return value, you may need to capture it: `result = await svc.reject_via_portal(...)`.)
- **PATTERN**: `src/grins_platform/tests/unit/test_estimate_service.py:459-485`; `_make_estimate_mock` helper at lines 62-130 (already supports `rejected_reason` kwarg).
- **IMPORTS**: Reuse existing imports from the test file.
- **GOTCHA**: The helper sets `est.rejected_reason = rejected_reason` — confirm `EstimateResponse.model_validate(est)` now picks this up via the new alias and sets `rejection_reason` on the schema. Without `populate_by_name=True`, this would still fail.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_service.py::TestEstimateService::test_reject_via_portal_response_surfaces_rejection_reason -v`

### Task 4: UPDATE `api/v1/webhooks.py` — F8 checkout handler receipt dispatch

- **IMPLEMENT**: Locate `_handle_checkout_invoice_payment` (line ~1022). At the END of the method, AFTER `await self.session.flush()` (line ~1141) and BEFORE the closing `self.log_completed("webhook_checkout_invoice_payment", ...)` call (line ~1143), insert the receipt-dispatch try/except block from the "Patterns to Follow" section above. Use logger key `stripe.webhook.receipt_dispatch_failed` (same as PI handler).
- **PATTERN**: Verbatim mirror of `api/v1/webhooks.py:1293-1336`. Same `noqa: PLC0415` on inline imports, same `noqa: SLF001` on `_send_payment_receipts`.
- **IMPORTS**: Inline (inside the `try` block) — `AppointmentRepository`, `AppointmentService`. `JobRepository` is already imported at the top of `_handle_checkout_invoice_payment`. `invoice_repo` is already in scope.
- **GOTCHA**: Re-fetch `paid_invoice = await invoice_repo.get_by_id(invoice_id)` inside the try. Freshness is guaranteed: `invoice_repository.get_by_id` issues a fresh `select(Invoice).where(...)` (verified at `invoice_repository.py:94-122`), and the prior `invoice_repository.update(stripe_payment_link_active=False)` calls `session.flush()` + `session.refresh(invoice)` (verified at `invoice_repository.py:185-186`). The re-fetch will return the post-payment row with `status=PAID`. Replays of `checkout.session.completed` after the invoice is already PAID hit the short-circuit at line ~1102-1109 BEFORE the dispatch — verify with the idempotency test in Task 5.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py -v`

### Task 5: ADD F8 unit test — `test_checkout_session_completed_fires_customer_receipt`

- **IMPLEMENT**: Mirror `test_payment_intent_succeeded_fires_customer_receipt` (line 242). Build a `checkout.session.completed` event with `metadata.invoice_id` set, `amount_total=25000`, `payment_intent="pi_test_checkout_receipt"`. Mock `invoice_repo.get_by_id` to return (1) the pre-payment unpaid invoice, then (2) a paid invoice on re-fetch. Mock `session.execute` to return a job with `payment_collected_on_site=False`. Patch `AppointmentService._send_payment_receipts` (use `patch.object(AppointmentService, "_send_payment_receipts", new_callable=AsyncMock)`) and assert it is awaited once with `(job, paid_invoice, Decimal("250"))`. Add a parallel `test_checkout_session_completed_does_not_fire_receipt_when_already_paid` that asserts the dispatch is NOT awaited when the invoice is already PAID at handler entry (idempotency).
- **PATTERN**: `src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py:242-280+`
- **IMPORTS**: Reuse the file's existing `_make_event`, `_build_handler`, `SimpleNamespace`, `AsyncMock`, `MagicMock`.
- **GOTCHA / EXACT PATCH PATTERN**: The handler imports `AppointmentService` inline via `noqa: PLC0415`. Use the SAME triple-patch context-manager pattern as the existing test at `test_stripe_webhook_payment_links.py:274-283` (verified verbatim):

  ```python
  send_receipts_mock = AsyncMock()
  with (
      patch(
          "grins_platform.repositories.invoice_repository.InvoiceRepository",
      ) as mock_repo_cls,
      patch(
          "grins_platform.services.invoice_service.InvoiceService",
      ) as mock_svc_cls,
      patch(
          "grins_platform.services.appointment_service.AppointmentService",
      ) as mock_appt_svc_cls,
  ):
      mock_repo_cls.return_value.get_by_id = AsyncMock(side_effect=[invoice_unpaid, invoice_paid])
      mock_repo_cls.return_value.update = AsyncMock()
      mock_svc_cls.return_value.record_payment = AsyncMock()
      mock_appt_svc_cls.return_value._send_payment_receipts = send_receipts_mock

      await handler._handle_checkout_invoice_payment(event, session_obj, str(invoice_id))

  send_receipts_mock.assert_awaited_once()
  args = send_receipts_mock.await_args
  assert args.args[0] is job_obj
  assert args.args[1] is invoice_paid  # the post-payment re-fetch result
  assert args.args[2] == Decimal("250.00")
  ```

  The patch targets the **module path where the inline import resolves** (`grins_platform.services.appointment_service`), not where it's used. This is identical to the proven PI-handler pattern.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py::test_checkout_session_completed_fires_customer_receipt -v`

### Task 6: UPDATE `api/v1/appointments.py` — F9 endpoint param

- **IMPLEMENT**: Add `customer_id: UUID | None = Query(default=None, description="Filter by customer ID (joins via job.customer_id)")` to the `list_appointments` signature (place between `staff_id` and `job_id` to keep ID-style filters grouped). Pass `customer_id=customer_id` into the `service.list_appointments(...)` call. Add `"customer_id": str(customer_id) if customer_id else None` into the `filters` dict on `_endpoints.log_started`.
- **PATTERN**: `src/grins_platform/api/v1/jobs.py:298-301`
- **IMPORTS**: `UUID` and `Query` are already imported.
- **GOTCHA**: Don't shadow the existing `staff_id`/`job_id` shape — use the same `UUID | None = Query(default=None, ...)` form.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py -v` (will fail until Tasks 7-8 are also done)

### Task 7: UPDATE `services/appointment_service.py` — F9 service param

- **IMPLEMENT**: Add `customer_id: UUID | None = None` to `list_appointments` signature (place between `staff_id` and `job_id`). Forward `customer_id=customer_id` into `self.appointment_repository.list_with_filters(...)`.
- **PATTERN**: `src/grins_platform/services/appointment_service.py:831-864`
- **IMPORTS**: `UUID` is already imported at the top of the file.
- **GOTCHA**: Keep the parameter ordering consistent with the repository signature (Task 8) — endpoint, service, repository should all accept the same set of filter kwargs in the same order so the call site reads cleanly.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit -v -k list_appointments`

### Task 8: UPDATE `repositories/appointment_repository.py` — F9 query JOIN

- **IMPLEMENT**: Add `customer_id: UUID | None = None` parameter to `list_with_filters`. After the existing `if job_id is not None:` block (around line 308), add:
  ```python
  if customer_id is not None:
      base_query = base_query.join(Job, Appointment.job_id == Job.id).where(
          Job.customer_id == customer_id,
      )
  ```
- **PATTERN**: `src/grins_platform/repositories/appointment_repository.py:270-349`. `Job` is already imported (used by `selectinload(Appointment.job).selectinload(Job.customer)` at line ~340).
- **IMPORTS**: Verify `Job` is already imported at module top; if not, add `from grins_platform.models.job import Job`.
- **GOTCHA**: Place the JOIN clause BEFORE the count-query subquery construction (line ~317) so the count reflects the filter. The count derives from `base_query.subquery()`, so anything appended to `base_query` before that line is captured. Order of filter `.where()` calls does not matter, but the JOIN must precede the count subquery.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py -v`

### Task 9: ADD F9 integration test — `customer_id` filter narrows results

- **IMPLEMENT**: In `tests/integration/test_appointment_integration.py`, add a test that creates 2 customers, 2 jobs (one per customer), 2 appointments (one per job), then asserts `service.list_appointments(customer_id=customer1.id)` returns only `appointment1` (length 1, ID matches). Use the existing `mock_appointment_repo` / `mock_job_repo` / `mock_staff_repo` fixtures or, if this is a true integration test with a DB, use the integration test database fixtures already in the test file.
- **PATTERN**: `src/grins_platform/tests/integration/test_appointment_integration.py:126-150` for fixture conventions.
- **IMPORTS**: Reuse existing.
- **GOTCHA**: If the existing test infrastructure mocks the repository (rather than running real SQL), the test should mock `list_with_filters` to verify the parameter is plumbed through (i.e., assert `mock_appointment_repo.list_with_filters.assert_awaited_with(customer_id=customer1.id, ...)`). For end-to-end JOIN behavior, prefer a true integration test with a temp DB if such fixtures exist in the repo; otherwise the unit-level plumbing assertion is acceptable.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py -v`

### Task 10: UPDATE `services/appointment_service.py` `collect_payment` — F10 flag set

- **IMPLEMENT**: Inside the `if not defer_to_webhook:` block of `collect_payment` (around lines ~2040–2120), AFTER `result_invoice` is finalized (after the existing-invoice update or new-invoice creation paths converge) and BEFORE the `try: await self._send_payment_receipts(...)` block, add:
  ```python
  await self.job_repository.update(
      job_id=job.id,
      data={"payment_collected_on_site": True},
  )
  ```
- **PATTERN**: Webhook reference at `api/v1/webhooks.py:1138-1140` and `:1288-1291` (different layer — service uses repository, webhooks use direct ORM + session.flush). For the repository call shape, mirror `services/schedule_clear_service.py:134` exactly.
- **IMPORTS**: `JobRepository` already accessed via `self.job_repository`. **Signature is `update(self, job_id: UUID, data: dict[str, Any])`** — pass `job_id=` and `data=` as kwargs; do NOT pass `payment_collected_on_site=True` as a kwarg directly.
- **GOTCHA**: Place outside the receipt try/except — if the receipt SMS fails, the flag must STILL be set (the duplicate-invoice guard depends on it). If the `job_repository.update` itself fails, that is a real DB error and should bubble up to roll back the transaction. Do NOT add a try/except around the flag set.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py -v -k collect_payment`

### Task 11: EXTEND F10 unit test — assert flag set for cash/check/Venmo/Zelle, NOT for Stripe-deferred

- **IMPLEMENT**: Extend `test_collect_payment_with_no_existing_invoice_creates_new` (line 703) — after the existing assertions, add `job_repo.update.assert_awaited_with(job_id, payment_collected_on_site=True)`. Add a sibling test `test_collect_payment_does_not_set_flag_for_stripe_deferred_methods` parametrized over `STRIPE_DEFERRED_METHODS` (likely `[PaymentMethod.CREDIT_CARD]`) that asserts `job_repo.update` was NOT called with `payment_collected_on_site=True` (the webhook owns this flag set for Stripe).
- **PATTERN**: `src/grins_platform/tests/unit/test_appointment_service_crm.py:703-766` — already parametrized over cash/check/Venmo/Zelle.
- **IMPORTS**: Reuse.
- **GOTCHA**: `job_repo.update` is an `AsyncMock`; use `.assert_awaited_with(...)` not `.assert_called_with(...)`. **Exact assertion**: `job_repo.update.assert_awaited_with(job_id=job.id, data={"payment_collected_on_site": True})` — both kwargs. The repository signature is `update(self, job_id: UUID, data: dict[str, Any])` per `repositories/job_repository.py:179-221`; existing call site reference: `services/schedule_clear_service.py:134`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py -v -k collect_payment`

### Task 12: UPDATE `.agents/plans/master-e2e-testing-plan.md` — F7 doc cleanup

- **IMPLEMENT**: Replace the four `stale_thread_reply` references with the actual audit discriminator emitted by `services/job_confirmation_service.py:461-490` (Gap 1.B state guard) — `appointment.reschedule_rejected` — and add a one-line note that the plan previously phrased this as `stale_thread_reply` but the code-side guard is the authoritative behavior. Specific edits:
  - **Line 211** (bug-pattern table row): change `Post-cancel "R" → \`stale_thread_reply\` (no reactivation)` to `Post-cancel "R" → \`appointment.reschedule_rejected\` (Gap 1.B; no reactivation)`.
  - **Line 1725** (VERIFY command): change the grep target so it surfaces the actual code idiom, e.g., `grep -n "appointment.reschedule_rejected\|late_reschedule_attempt\|post_cancel" src/grins_platform/services/job_confirmation_service.py src/grins_platform/services/sms_service.py`.
  - **Line 1729** (assertion description): change `marking the reply as \`stale_thread_reply\` (or equivalent enum)` to `marking the reply as \`appointment.reschedule_rejected\` and emitting a \`late_reschedule_attempt\` alert`.
  - **Line 1741** (acceptance checkbox): change `logged as \`stale_thread_reply\`` to `logged as \`appointment.reschedule_rejected\` (Gap 1.B state guard at \`services/job_confirmation_service.py:461-490\`)`.
- **PATTERN**: N/A — narrative doc edit. Cross-reference the run's verbatim audit example in the report (run 2026-05-04-full-real-emails session 3): `appointment.reschedule_rejected` row at 22:05:29Z with `pre_status=cancelled`, `raw_body=R`, `reschedule_request_id=null`, plus `late_reschedule_attempt` alert.
- **IMPORTS**: N/A
- **GOTCHA**: Do NOT touch any other phases (P9 covers other E* edge cases unrelated to E11 — leave those alone). Do NOT modify `services/job_confirmation_service.py` itself; the F7 finding is INFORMATIONAL — the code is correct, the plan was stale. Existing functional coverage at `tests/functional/test_post_cancellation_reply_functional.py` already validates the correct behavior; no test changes either.
- **VALIDATE**: `grep -n stale_thread_reply .agents/plans/master-e2e-testing-plan.md` returns zero matches outside any historical/changelog block. Cross-check: `grep -n "appointment.reschedule_rejected" .agents/plans/master-e2e-testing-plan.md` returns four matches (one per replacement).

### Task 12.5: CREATE `e2e/master-plan/bug-resolution-2026-05-04/` directory + README + shared helper

- **IMPLEMENT**: Create the new directory. Write `README.md` listing the four scripts, the operator interactions required, the dedup-management strategy, the post-run cleanup notes, and a "how to run on dev" section. Author `_bug_lib.sh` that `source`s `e2e/master-plan/_dev_lib.sh` and adds the helpers described in Phase 5: `pause_for_operator`, `assert_recent_sms`, `assert_no_recent_sms`, `assert_recent_email`, plus a `ensure_seed_recipients` pre-flight that PATCHes the seed customer's email to `kirillrakitinsecond@gmail.com` and phone to `+19527373312` if they have drifted.
- **PATTERN**: Mirror `e2e/master-plan/_dev_lib.sh` shape: helper functions named in lower_snake_case, exit on first failure, `set -euo pipefail` at the top of every script.
- **IMPORTS**: Bash sourcing only. No new external deps; uses `curl`, `jq`, `psql` already required by the master-plan harness.
- **GOTCHA**: `assert_recent_sms` must poll for at least 60 s before declaring failure (Stripe webhooks + receipt dispatch can take 10–30 s on a real provider). The poll loop should sleep 3 s between attempts. Print every API response on failure so the operator can debug.
- **VALIDATE**: `bash -n e2e/master-plan/bug-resolution-2026-05-04/_bug_lib.sh` (syntax check). Run `e2e/master-plan/bug-resolution-2026-05-04/_bug_lib.sh` directly with `--self-test` if you implement that flag, or just source it and call `ensure_seed_recipients` to confirm the helper writes the expected PATCH.

### Task 12.6: AUTHOR `f9-appointments-customer-id-filter.sh` (no SMS, runs first)

- **IMPLEMENT**: Script logs in as admin via `login_admin`, creates customer A and customer B (uses the lead → move-to-sales → move-to-jobs flow OR the direct customer-create endpoint depending on what the dev test allowance allows), creates one job per customer, schedules one appointment per job. Then issues:
  - `api GET /api/v1/appointments?customer_id=$CID_A&page_size=20` → assert every `.items[].job.customer_id == $CID_A`.
  - `api GET /api/v1/appointments?customer_id=$CID_B&page_size=20` → assert every `.items[].job.customer_id == $CID_B`.
  - `api GET /api/v1/appointments?page_size=20` → assert both `$CID_A` and `$CID_B` appear in the union.
  - Combined-filter case: `?customer_id=$CID_A&staff_id=$STAFF&date_from=YYYY-MM-DD` → assert AND-semantics (intersection).
- **PATTERN**: `e2e/master-plan/phase-*` scripts; `api`/`api_q` helpers from `_dev_lib.sh`; `jq` for assertions.
- **IMPORTS**: source `_bug_lib.sh`.
- **GOTCHA**: When unspecified, FastAPI ignores unknown params (this is the F9 bug). The pre-fix assertion will fail because the response will contain other customers' rows. Post-fix it passes. Make the failure message actionable: "Customer-id filter returned N rows for OTHER customers — F9 fix likely missing on this build."
- **VALIDATE**: `e2e/master-plan/bug-resolution-2026-05-04/f9-appointments-customer-id-filter.sh` returns exit code 0 against a build that has Task 6–8 applied; non-zero against a build without.

### Task 12.7: AUTHOR `f2-estimate-rejection-reason-roundtrip.sh` (real email, no real SMS)

- **IMPLEMENT**: Script:
  1. Login admin; ensure_seed_recipients.
  2. POST a new lead (real email allowlisted) using a unique tag (e.g., `f2-livecheck-{epoch}`). Move to sales pipeline.
  3. Build estimate with one line item ($350) → Send to customer → operator visually confirms the estimate email arrived at `kirillrakitinsecond@gmail.com`. Pause for confirmation.
  4. Operator clicks the portal token URL printed by the script (or the script extracts it from `/api/v1/estimates/{id}.customer_token`).
  5. Operator clicks Reject in the portal; types reason `"F2 Live Verify {timestamp}"`. Pause for confirmation.
  6. Script polls `GET /api/v1/estimates/{id}` for ≤ 30 s and asserts `.rejection_reason == "F2 Live Verify {timestamp}"`. Pre-fix: it stays null. Post-fix: appears immediately.
  7. Script polls Resend (`assert_recent_email <customer_id> "rejected"`) and operator visually confirms the rejection-notification email at the allowlisted inbox.
- **PATTERN**: `e2e/master-plan/phase-04-*` (sales-pipeline / estimate flow) — reuse the lead-create / pipeline-move idioms.
- **IMPORTS**: source `_bug_lib.sh`.
- **GOTCHA**: `email_service.py:135` rejects plus-aliases on the allowlist (per the report's "Operational outcomes"). Use `kirillrakitinsecond@gmail.com` (no `+tag`) and rely on the unique reason string for distinguishing test runs in the inbox.
- **VALIDATE**: Real estimate rejection email lands in inbox; API response surfaces the reason post-fix.

### Task 12.8: AUTHOR `f10-collect-payment-flag-and-duplicate-guard.sh` (real SMS for cash; API-only for check/Venmo/Zelle)

- **IMPLEMENT**: Script:
  1. Login admin; ensure_seed_recipients.
  2. Create a fresh job for the seed customer (no invoice yet). Schedule a tech appointment for that job (today's date).
  3. Move appointment to `arrived` then `in_progress` (so `collect_payment` is contextually valid; verify the appt-status state machine accepts this in the current code).
  4. `POST /api/v1/appointments/{apt}/collect-payment {"payment_method":"cash","amount":50.00}`.
  5. `assert_recent_sms <seed_customer_id> payment_receipt 60` — fails fast if receipt SMS missing.
  6. Pause for operator to visually confirm receipt SMS at `+19527373312`.
  7. `GET /api/v1/jobs/{job}` → assert `.payment_collected_on_site == true` (this is the F10 bug under test).
  8. `POST /api/v1/invoices/generate-from-job/{job}` → assert HTTP 4xx with body containing `"payment was collected on site"`.
  9. **Repeat steps 2–4, 7, 8 for `check` ($40 ref=`CHK-1234`), `venmo` ($30 ref=`VENMO-abc`), `zelle` ($25 ref=`ZELLE-zzz`)** — each on a NEW job to avoid invoice cross-contamination, but expecting the receipt SMS to be dedup-blocked (so `assert_no_recent_sms` is the right call for steps 5–6 on these methods, with a comment explaining why). Steps 7–8 (flag + duplicate-guard) MUST pass regardless.
- **PATTERN**: `e2e/master-plan/phase-12-*` (payment matrix). Reuse PaymentCollectionRequest schema shape from earlier scripts.
- **IMPORTS**: source `_bug_lib.sh`.
- **GOTCHA**: Step 3 may require an admin override depending on whether the appt-state machine demands a `staff arrived at site` action or accepts a direct PATCH. Verify against the current state-machine implementation before authoring; the master-plan run-3 walked job 77d78d08 through `scheduled → on-my-way → in_progress → completed` — mirror that sequence. Step 8's exact 4xx code can be 409 or 422 depending on `InvalidInvoiceOperationError` mapping; assert on the message substring, not the status code.
- **VALIDATE**: All 4 method runs produce flag-set + duplicate-guard pass. Real SMS for cash arrives within 30 s. The other 3 methods are deliberately silent at SMS layer (dedup) and that's expected.

### Task 12.9: AUTHOR `f8-stripe-payment-link-receipt.sh` (real SMS, real Stripe pay)

- **IMPLEMENT**: Script:
  1. Login admin; ensure_seed_recipients.
  2. Create a FRESH test customer (`F8 Live Verify {timestamp}`) with phone `+19527373312` and email `kirillrakitinsecond@gmail.com`. **Why fresh**: the seed customer's 24 h `payment_receipt` dedup window is likely already used by F10's run earlier in the sequence; a fresh customer has an open dedup slot.
  3. Create a job for the new customer; create an invoice for $1.00 (small, low-risk).
  4. `POST /api/v1/invoices/{inv}/send-link` → assert `sms_sent == true` in response.
  5. `assert_recent_sms <new_customer_id> payment_link_sent 60` (or whatever the message_type for the link is — confirm against `sms_service.py` constants).
  6. Pause for operator: "Open the SMS at +19527373312, click the Stripe Payment Link, pay with test card `4242 4242 4242 4242` exp `12/30` CVC `123`. Reply Y here when payment succeeded."
  7. Poll `GET /api/v1/invoices/{inv}` for ≤ 90 s; assert `.status == "paid"`, `.payment_method == "credit_card"`, `.payment_reference` startswith `"stripe:pi_"`.
  8. **THE F8 ASSERTION**: poll `GET /api/v1/customers/{new_customer_id}/sent-messages?message_type=payment_receipt` for ≤ 60 s and assert at least one row exists with `sent_at` AFTER step 7's invoice-paid timestamp. Pre-fix: this assertion fails (no receipt fires after Stripe pay). Post-fix: passes within ~30 s.
  9. Pause for operator to visually confirm the receipt SMS arrived at `+19527373312`.
  10. `assert_recent_email <new_customer_id> "receipt"` → operator confirms the receipt email arrived at the allowlisted inbox.
- **PATTERN**: `e2e/payment-links-flow.sh` (existing) is a closely related shape — reuse its Stripe-link send + poll-for-paid idiom. The new piece is the receipt-SMS assertion AFTER paid.
- **IMPORTS**: source `_bug_lib.sh`.
- **GOTCHA**: Stripe's typical event order is `checkout.session.completed` → `payment_intent.succeeded`; the post-fix dispatch is wired into the checkout handler (Task 4). Verify the `_send_payment_receipts` call path actually fires for checkout-driven invoices, not only PI-driven ones, by reading the post-deploy server logs for `stripe.webhook.receipt_dispatch_failed` warnings (none expected). Also: the test card `4242 4242 4242 4242` should ALWAYS succeed on Stripe test mode; if it declines, dev's Stripe key may not be in test mode — abort and ask the user.
- **VALIDATE**: Receipt SMS arrives at `+19527373312` within ~30 s of payment; matching email arrives at allowlisted inbox; invoice flips to PAID with correct payment_reference.

### Task 12.10: AUTHOR top-level `run-all.sh` for the bug-resolution dir

- **IMPLEMENT**: Sequence: F9 first (no SMS, no email — fastest), then F2 (real email), then F10 (real `payment_receipt` SMS for cash), then F8 (real `payment_link_sent` + real `payment_receipt` SMS — uses fresh customer to dodge dedup). Print phase-by-phase timing. On any single-script failure, abort the whole run and print which fix is missing from the build.
- **PATTERN**: `e2e/master-plan/run-all.sh` shape.
- **IMPORTS**: source `_bug_lib.sh` for shared logging.
- **GOTCHA**: If F8 runs before F10, F10's `cash` receipt may dedup-collide if the operator pays the F8 Stripe link with the seed customer instead of a fresh one. The defined order (F9 → F2 → F10 → F8) avoids this. Document that ordering explicitly in the script.
- **VALIDATE**: `e2e/master-plan/bug-resolution-2026-05-04/run-all.sh` end-to-end on dev returns exit 0 against a build with all four fixes; non-zero with clear "F<n> fix missing" output otherwise.

### Task 13: RUN full lint + type-check + targeted test suite

- **IMPLEMENT**: Execute the validation commands in the next section in order. Stop at the first failure and fix before continuing.
- **PATTERN**: Standard repo workflow.
- **IMPORTS**: N/A
- **GOTCHA**: Pyright sometimes flags the `validation_alias=AliasChoices(...)` form if the import is missing — re-confirm the pydantic import.
- **VALIDATE**: All Level 1–3 commands below should pass with zero errors.

### Task 14: MANUAL E2E re-verification on dev (optional but recommended pre-commit)

- **IMPLEMENT**: Reproduce each bug's pre-fix path on dev and confirm the fix-side behavior. F2: reject an estimate via `/portal/estimates/{token}` and `GET /api/v1/estimates/{id}` confirms `rejection_reason` is populated. F8: send a $1 Stripe Payment Link to allowlisted phone, pay, confirm a `payment_receipt` SMS lands within seconds (not 24 h dedup-blocked — use a NEW seed customer for this). F9: `GET /api/v1/appointments?customer_id=<seed_id>&page_size=20` returns only seed-customer appointments. F10: `POST /appointments/{id}/collect-payment {payment_method:cash}` then `POST /invoices/generate-from-job/{job_id}` returns 422/409 with the duplicate-invoice error.
- **PATTERN**: ENVIRONMENT SAFETY rules from `master-e2e-testing-plan.md` apply: dev only, allowlisted phone/email only, no main pushes.
- **GOTCHA**: F8 verification will appear to fail if the seed customer has had a `payment_receipt` SMS in the last 24 h (24 h customer+type dedup at `sms_service.py:344-361`). Use a fresh test customer or wait out the dedup window. Per `feedback_test_email_only_allowlist.md`, set the test customer's email to `kirillrakitinsecond@gmail.com` first.
- **VALIDATE**: All four paths produce the expected post-fix behavior.

---

## TESTING STRATEGY

### Unit Tests

- **F2**: `test_reject_via_portal_response_surfaces_rejection_reason` (new). Asserts that calling `reject_via_portal(token, reason)` returns an `EstimateResponse` whose `.rejection_reason` equals the input reason. Without the fix, `.rejection_reason is None`.
- **F8**: `test_checkout_session_completed_fires_customer_receipt` + `test_checkout_session_completed_does_not_fire_receipt_when_already_paid` (both new). Mock `_send_payment_receipts` and assert it is awaited once on the success path and zero times on the idempotency-replay path.
- **F10**: extend `test_collect_payment_with_no_existing_invoice_creates_new` to assert `job_repository.update(job.id, payment_collected_on_site=True)` was awaited for cash/check/Venmo/Zelle. Add `test_collect_payment_does_not_set_flag_for_stripe_deferred_methods` (negative case for `CREDIT_CARD`).

### Integration Tests

- **F9**: in `tests/integration/test_appointment_integration.py`, a test that asserts `list_appointments(customer_id=X)` narrows the result set to appointments whose linked job belongs to customer X. Verify both via service-layer (mocked repo plumbing) and, if integration DB fixtures exist, via real-SQL JOIN behavior.

### Edge Cases

- **F2**: `rejection_reason` empty string vs `None` — schema allows `None`, service writes whatever is passed (could be empty string). Confirm `EstimateResponse.model_validate(orm_with_empty_str)` yields empty string, not `None`.
- **F8**: PI replay AFTER checkout reconciliation must not double-fire receipts. The `invoice.status == PAID` short-circuit at `webhooks.py:1252-1259` already handles this in the PI handler; the new checkout-handler dispatch happens BEFORE the invoice is in any state where the PI handler would re-fire, so symmetry is preserved.
- **F8**: the 24 h SMS dedup at `sms_service.py:344-361` is a downstream defense; even if a logic bug accidentally double-called `_send_payment_receipts` for the same invoice, the SMS layer would dedup. The unit test asserts the call count, not the SMS-layer outcome.
- **F9**: `customer_id` set + `staff_id` set + `job_id` set simultaneously — all filters AND together. Verify the query produces the intersection, not the union.
- **F9**: `customer_id` matches no appointments — empty list, not error. Existing pagination handles this.
- **F10**: collecting a $0 payment — should still set the flag (any successful collect-payment call indicates the job is "settled on site"). Verify the existing `if not defer_to_webhook:` branch handles $0 correctly.
- **F10**: collect_payment called twice on the same appointment for the same method (operator double-clicks). Per session-3 observations in the report, multi-tender accumulates `paid_amount` additively; the flag set is idempotent (setting `True` twice is fine).
- **F10**: collecting payment for `PaymentMethod.CREDIT_CARD` (Stripe-deferred). The flag must NOT be set here — the webhook handles it on actual Stripe payment. Confirm via the negative test case.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/schemas/estimate.py
uv run ruff check src/grins_platform/api/v1/webhooks.py
uv run ruff check src/grins_platform/api/v1/appointments.py
uv run ruff check src/grins_platform/services/appointment_service.py
uv run ruff check src/grins_platform/repositories/appointment_repository.py
uv run ruff format --check src/grins_platform/
uv run mypy src/grins_platform/schemas/estimate.py src/grins_platform/api/v1/webhooks.py src/grins_platform/api/v1/appointments.py src/grins_platform/services/appointment_service.py src/grins_platform/repositories/appointment_repository.py
uv run pyright src/grins_platform/
```

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_estimate_service.py -v
uv run pytest src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py -v
uv run pytest src/grins_platform/tests/unit/test_appointment_service_crm.py -v
uv run pytest src/grins_platform/tests/unit -v -k "list_appointments or collect_payment or reject or checkout"
```

### Level 3: Integration Tests

```bash
uv run pytest src/grins_platform/tests/integration/test_appointment_integration.py -v
uv run pytest src/grins_platform/tests/functional/test_post_cancellation_reply_functional.py -v  # confirm F7-related path still passes
uv run pytest src/grins_platform/tests -v  # full sweep
```

### Level 4: Manual Validation (dev environment, allowlisted recipients only)

> ENVIRONMENT SAFETY: dev only. SMS only to `+19527373312`, email only to `kirillrakitinsecond@gmail.com`. No `main` pushes.

```bash
# F2 — reject an estimate, then GET it back and confirm rejection_reason populated
TOKEN=<seed_estimate_token>
curl -X POST "https://grins-dev-dev.up.railway.app/portal/estimates/$TOKEN/reject" \
  -H "Content-Type: application/json" \
  -d '{"reason":"Manual F2 verification"}'
ESTIMATE_ID=<lookup>
curl -s "https://grins-dev-dev.up.railway.app/api/v1/estimates/$ESTIMATE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.rejection_reason'
# Expect: "Manual F2 verification"

# F8 — Stripe Payment Link end-to-end (use a FRESH customer to avoid 24h dedup)
INVOICE_ID=<freshly_created_invoice>
curl -X POST "https://grins-dev-dev.up.railway.app/api/v1/invoices/$INVOICE_ID/send-link" \
  -H "Authorization: Bearer $TOKEN"
# Operator: receive SMS at +19527373312, click link, pay with test card 4242 4242 4242 4242
# Then poll:
curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers/<customer_id>/sent-messages?message_type=payment_receipt" \
  -H "Authorization: Bearer $TOKEN" | jq
# Expect: a row with sent_at within ~30s of payment

# F9 — customer_id filter
SEED_CUSTOMER=a44dc81f-ce81-4a6f-81f5-4676886cef1a
curl -s "https://grins-dev-dev.up.railway.app/api/v1/appointments?customer_id=$SEED_CUSTOMER&page_size=20" \
  -H "Authorization: Bearer $TOKEN" | jq '.items | map(.job.customer_id) | unique'
# Expect: ["a44dc81f-ce81-4a6f-81f5-4676886cef1a"]

# F10 — duplicate-invoice guard fires after cash collection
APT_ID=<appointment_with_job_no_invoice_yet>
JOB_ID=<that_job>
curl -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/$APT_ID/collect-payment" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payment_method":"cash","amount":50}'
# Then verify flag and try duplicate:
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.payment_collected_on_site'
# Expect: true
curl -X POST "https://grins-dev-dev.up.railway.app/api/v1/invoices/generate-from-job/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN" -i
# Expect: HTTP 4xx with InvalidInvoiceOperationError "payment was collected on site"
```

### Level 5: Real-SMS / Real-Email E2E Recreation (Phase 5 scripts)

Run the new bug-resolution E2E scripts authored in Tasks 12.5–12.10. Operator must be present at `+19527373312` and at the `kirillrakitinsecond@gmail.com` inbox throughout.

```bash
# Source dev env vars first (reads from Railway):
source e2e/master-plan/_dev_lib.sh   # exports BASE / API_BASE / SHOTS_ROOT for dev
export E2E_USER=admin@grinsirrigation.com
export E2E_PASS=<dev_admin_password>

# Single-script runs (use during iteration):
e2e/master-plan/bug-resolution-2026-05-04/f9-appointments-customer-id-filter.sh
e2e/master-plan/bug-resolution-2026-05-04/f2-estimate-rejection-reason-roundtrip.sh
e2e/master-plan/bug-resolution-2026-05-04/f10-collect-payment-flag-and-duplicate-guard.sh
e2e/master-plan/bug-resolution-2026-05-04/f8-stripe-payment-link-receipt.sh

# Or one-shot ordered run (preferred for sign-off):
e2e/master-plan/bug-resolution-2026-05-04/run-all.sh
```

Each script exits 0 on full PASS, non-zero with a structured failure diagnostic on the first assertion that doesn't match. Real SMS / real email checkpoints are HUMAN-mode — do not auto-skip.

### Level 6: Additional Validation (optional)

- Run `e2e/master-plan/sim/callrail_inbound.sh` and `sim/resend_email_check.sh poll` per master-plan if you want non-human-loop coverage of receipt SMS arrival.
- After all four fixes land, run a partial re-execution of the master-plan phases that exercised these bugs (P4d for F2, P14 for F8, P12 for F10, anywhere a `customer_id` filter is naturally used for F9) and confirm no new findings.

---

## ACCEPTANCE CRITERIA

- [ ] **F2**: `EstimateResponse.rejection_reason` is populated whenever the underlying ORM `Estimate.rejected_reason` is non-null. New unit test passes.
- [ ] **F8**: A `checkout.session.completed` event for an Architecture-C invoice with `metadata.invoice_id` triggers `AppointmentService._send_payment_receipts(job, paid_invoice, amount)` exactly once. Replays of the same event do not double-fire.
- [ ] **F9**: `GET /api/v1/appointments?customer_id=<uuid>` returns only appointments whose linked Job has the matching `customer_id`. Combining with other filters AND-s correctly.
- [ ] **F10**: After `POST /appointments/{id}/collect-payment` with `payment_method` in `{cash, check, venmo, zelle}`, `Job.payment_collected_on_site` is `True`. A subsequent `POST /invoices/generate-from-job/{job_id}` raises `InvalidInvoiceOperationError`. For `payment_method=credit_card`, the flag is NOT set by `collect_payment` (the webhook handles it).
- [ ] All Level 1–3 validation commands pass with zero errors.
- [ ] `master-e2e-testing-plan.md` no longer references `stale_thread_reply` in P9/E11 acceptance.
- [ ] No regressions in existing unit/integration/functional tests (full `pytest` sweep green).
- [ ] No new ruff/mypy/pyright errors.
- [ ] Manual dev-environment Level 4 validation confirms all four post-fix behaviors.
- [ ] Real-SMS / real-email E2E scripts authored under `e2e/master-plan/bug-resolution-2026-05-04/`.
- [ ] `run-all.sh` returns exit 0 against the post-fix dev deploy with the operator present at `+19527373312` and `kirillrakitinsecond@gmail.com`.
- [ ] Real `payment_receipt` SMS arrives at `+19527373312` within ~30 s of a Stripe Payment Link pay (F8) and within ~30 s of a cash collect-payment (F10).
- [ ] Real estimate-rejected email arrives at `kirillrakitinsecond@gmail.com` (F2) and the API surfaces `rejection_reason` immediately after.

---

## COMPLETION CHECKLIST

- [ ] Tasks 1–14 completed in order
- [ ] Each task's validation command passed immediately after the change
- [ ] Level 1 (syntax/style/type) passes
- [ ] Level 2 (unit) passes
- [ ] Level 3 (integration + functional sweep) passes
- [ ] Level 4 (manual dev verification) confirms each fix
- [ ] No linting or type errors introduced
- [ ] Master plan doc no longer drifts from code (F7)
- [ ] Acceptance criteria all checked
- [ ] Code reviewed for adherence to project patterns (mirror webhook receipt block, mirror `customer_id` thread-through from `jobs.py`/`estimates.py`, mirror Pydantic alias from `sent_message.py`)
- [ ] Sign-off report at `e2e-screenshots/master-plan/runs/2026-05-04-full-real-emails/E2E-SIGNOFF-REPORT.md` is updated (separate task — append a "Resolutions" section noting which findings have shipping fixes)
- [ ] Phase 5 real-SMS/real-email scripts authored, lint-clean (`bash -n`), and run-all.sh PASSes against post-fix dev with operator-confirmed SMS at +19527373312 and email at kirillrakitinsecond@gmail.com

---

## NOTES

### Out of scope (deliberately deferred)

- **F1 — Portal Line Items column-clipping at ~1280px**: needs multi-viewport visual diff; not promoted; defer to a separate UI pass.
- **F5 — `appointment_confirmation_reply` 24h dedup blocks cancellation acknowledgment after Y reply**: requires a product-spec decision (is this intentional anti-storm behavior, or should the dedup key become `(customer_id, message_type, appointment_id)` for `APPOINTMENT_CONFIRMATION_REPLY` like Bug #4 fixed for `APPOINTMENT_CONFIRMATION`?). Not safe to fix unilaterally — defer until spec call.
- **F3, F4, F6**: retracted by source-VERIFY in the report (operator error / field-filter trap / source-verified registration). No action.

### Design decisions / trade-offs

- **F8 receipt dispatch placement**: Chose to wire the receipt block into `_handle_checkout_invoice_payment` rather than refactor into a shared helper. Rationale: the existing PI-handler block is ~25 lines with cross-cutting `noqa` pragmas; a helper extraction would touch the PI handler too, broadening the diff and the test surface. Refactor-into-helper is noted as a follow-up in the existing inline comment (`A future refactor should extract this into a standalone payment_receipt_dispatcher module`). This plan honors that intent — keep the symmetric duplication today, refactor as a separate PR.
- **F9 query JOIN**: `base_query.join(Job, Appointment.job_id == Job.id).where(Job.customer_id == customer_id)` versus a `Job.customer_id` subquery. JOIN is preferred — the `selectinload(Appointment.job)` pattern is already present in the same method, so the JOIN doesn't introduce a new model dependency. Subquery would force a second round-trip pattern that doesn't match the rest of the file.
- **F2 alias direction**: `AliasChoices("rejection_reason", "rejected_reason")` accepts both names on input. For `model_validate(orm_obj)` (where the ORM attribute is `rejected_reason`), the alias path resolves correctly. For JSON-input requests using the canonical `rejection_reason` name, `populate_by_name=True` lets the canonical name still validate. Trade-off considered: rename the ORM column to `rejection_reason` (one-shot migration). Rejected because (a) DB is the source of truth and renaming columns mid-stream invites integration breakage in any consumer hitting the DB directly (analytics, BI, replicas), and (b) the schema is the right place to bridge the gap — schemas are a translation layer.
- **F10 flag-set placement**: Chose to set the flag via `self.job_repository.update(...)` rather than by mutating the in-memory `job` and relying on session flush. Rationale: the AppointmentService's session lifecycle is repository-mediated, not direct (`self.session` is not held by the service). Calling `job_repository.update(...)` mirrors how the rest of the service modifies entities and avoids a flush-ordering surprise.
- **F10 idempotency**: setting `payment_collected_on_site=True` twice (e.g., operator double-clicks) is a no-op at the DB level. The duplicate-invoice guard at `invoice_service.py:1369` only reads the flag; it doesn't care about transitions. So no idempotency wrapper is needed.

### Confidence assessment

**One-pass implementation confidence**: **10/10**.

Every soft spot from the prior 9/10 assessment has been resolved by reading the actual current source:

- **F2 alias semantics** — verified by quoting `schemas/sent_message.py:26, 39-44`: `populate_by_name=True` + `validation_alias=AliasChoices(...)` is a known-working idiom in this codebase. The plan mirrors it byte-for-byte. `EstimateResponse` currently has `model_config = ConfigDict(from_attributes=True)` at line 270 (no other alias usage in the file), so the change is additive and bounded.
- **F8 test patching** — the existing `test_payment_intent_succeeded_fires_customer_receipt` at `test_stripe_webhook_payment_links.py:242-298` uses a triple-`patch()` context-manager pattern targeting `grins_platform.services.appointment_service.AppointmentService` (the resolution module of the inline `noqa: PLC0415` import). The plan now embeds the exact pattern verbatim. No ambiguity.
- **F8 paid_invoice freshness** — verified `invoice_repository.get_by_id` issues `select(Invoice).where(...)` (fresh query, line 110), and `invoice_repository.update` calls `session.flush()` + `session.refresh(invoice)` (lines 185-186) before returning. The re-fetch inside the new try-block is guaranteed to see the post-payment row.
- **F9 Job import** — verified already imported at `repositories/appointment_repository.py:25`. JOIN clause requires no new imports.
- **F10 repository call shape** — verified `JobRepository.update(self, job_id: UUID, data: dict[str, Any])` at `repositories/job_repository.py:179-221`. Plan now uses the correct `update(job_id=..., data={"payment_collected_on_site": True})` form (was incorrectly written as `update(job.id, payment_collected_on_site=True)` in the v1 draft — corrected). Existing call site reference at `services/schedule_clear_service.py:134` mirrors the exact shape.

### Risks (residual, all out-of-band of the implementation)

- **F2 visibility change**: if any other consumer reads `EstimateResponse.rejection_reason` and relies on its value being `None` for rejected estimates, the fix will start surfacing real data. This is the intended behavior; flagged as a known visibility change, not a bug.
- **F9 JOIN performance**: for very large appointment tables, the JOIN-on-customer_id without an index on `Job.customer_id` could degrade. `Job.customer_id` is a FK and is almost certainly indexed by Alembic conventions; spot-check the migration and add an index migration as a separate PR if missing.
- **F10 backfill question**: existing cash-paid jobs (pre-fix) have `payment_collected_on_site=False` and their duplicate-invoice guard is currently bypassable. Decision: do NOT write a one-time backfill in this plan — that's a separate data-cleanup task with its own risk surface. Document the gap in the resolution PR; a backfill SQL is straightforward (`UPDATE jobs SET payment_collected_on_site=true WHERE id IN (SELECT job_id FROM invoices WHERE status='paid' AND payment_method IN ('cash','check','venmo','zelle'))`) and can be run manually post-deploy.
- **Phase 5 (real-SMS) operator availability**: the four E2E scripts require a human at `+19527373312` and the allowlisted inbox throughout. Schedule the run window with the operator before kicking off `run-all.sh`.

---

## APPENDIX A — Source-of-truth verification (read before editing)

Before applying any task, run these commands and confirm each line still matches. The plan was hardened against the SHA below; if any line has drifted, update the plan reference before applying the edit.

```bash
# F2 — schema currently has from_attributes only
grep -n "model_config = ConfigDict" src/grins_platform/schemas/estimate.py
# Expected: model_config = ConfigDict(from_attributes=True)   (around line 270)

# F2 — proven alias pattern to mirror
grep -n -A 1 "validation_alias=AliasChoices" src/grins_platform/schemas/sent_message.py
# Expected: line 43 — validation_alias=AliasChoices("content", "message_content")

# F2 — confirm AliasChoices is NOT yet imported in estimate.py (you will add it)
grep -n "from pydantic import" src/grins_platform/schemas/estimate.py
# Expected: from pydantic import BaseModel, ConfigDict, Field

# F8 — confirm checkout handler does not yet call _send_payment_receipts
grep -n "_send_payment_receipts" src/grins_platform/api/v1/webhooks.py
# Expected: a single match in _handle_payment_intent_succeeded (around line ~1318);
# zero matches in _handle_checkout_invoice_payment (your fix adds the second match)

# F8 — confirm the proven test patch targets
grep -n "grins_platform.services.appointment_service.AppointmentService" \
  src/grins_platform/tests/unit/test_stripe_webhook_payment_links.py
# Expected: at least one match — this is the patch path your new test will reuse

# F9 — confirm endpoint signature is missing customer_id
grep -n "customer_id" src/grins_platform/api/v1/appointments.py
# Expected: zero matches (or only inside docstrings/comments). Your fix adds it.

# F9 — confirm Job is already imported in the repository
grep -n "from grins_platform.models.job import Job" \
  src/grins_platform/repositories/appointment_repository.py
# Expected: line 25 — `from grins_platform.models.job import Job`

# F10 — confirm JobRepository.update signature
grep -n -A 4 "async def update" src/grins_platform/repositories/job_repository.py
# Expected: `async def update(self, job_id: UUID, data: dict[str, Any]) -> Job | None:`

# F10 — confirm an existing call-site shape to mirror
grep -n -A 3 "self.job_repository.update" src/grins_platform/services/schedule_clear_service.py
# Expected: `await self.job_repository.update(job_id=job_id, data={"status": ...})`

# F10 — confirm collect_payment does not yet set the flag
grep -n "payment_collected_on_site" src/grins_platform/services/appointment_service.py
# Expected: zero matches in this file currently. Your fix adds one inside the
# `if not defer_to_webhook:` branch.

# F10 — confirm duplicate-invoice guard reads the flag
grep -n "payment_collected_on_site" src/grins_platform/services/invoice_service.py
# Expected: a guard around line 1369 reading `if job.payment_collected_on_site:`

# F7 — find the stale plan phrasing
grep -n "stale_thread_reply" .agents/plans/master-e2e-testing-plan.md
# Expected: at least one match (the line your edit replaces). Post-fix: zero matches
# outside of any historical/changelog block.
```

If any of the "expected" outcomes don't match (e.g., a file shifted, an import was already added by a parallel branch), STOP and reconcile against the current source before applying the edit. The plan's line numbers are accurate to commit `7495d88` (the SHA recorded in the E2E sign-off report); recent commits may have shifted them.

---

## APPENDIX B — Verified call signatures (paste-ready)

These are the EXACT shapes for the three highest-risk call sites. Copy them when implementing — do not reconstruct from memory.

```python
# F2 — schema field replacement (schemas/estimate.py:319-322)
rejection_reason: str | None = Field(
    default=None,
    description="Rejection reason",
    validation_alias=AliasChoices("rejection_reason", "rejected_reason"),
)

# F2 — model_config update (schemas/estimate.py:270)
model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# F2 — pydantic import (top of schemas/estimate.py)
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# F9 — repository JOIN (insert in appointment_repository.py after the `if job_id is not None:` block)
if customer_id is not None:
    base_query = base_query.join(Job, Appointment.job_id == Job.id).where(
        Job.customer_id == customer_id,
    )

# F10 — flag-set call (insert in appointment_service.collect_payment, inside `if not defer_to_webhook:`,
#                       AFTER `result_invoice` is settled and BEFORE the `try: await self._send_payment_receipts(...)`)
await self.job_repository.update(
    job_id=job.id,
    data={"payment_collected_on_site": True},
)

# F10 — unit-test assertion (extend test_collect_payment_with_no_existing_invoice_creates_new)
job_repo.update.assert_awaited_with(
    job_id=job_id,
    data={"payment_collected_on_site": True},
)
```
