# Master E2E Plan Run — 2026-05-04 Sign-off Findings

**Run ID**: `2026-05-04T15:00Z` (dev Vercel + dev Railway)
**Operator**: human at +19527373312, inbox kirillrakitinsecond@gmail.com
**Scope**: estimate portal + email delivery + SMS confirm/reschedule + Stripe Payment Link + Apple Pay checkout
**Seed customer**: `a44dc81f-ce81-4a6f-81f5-4676886cef1a` (Test User, +19527373312, kirillrakitinsecond@gmail.com, both opt-ins true)

---

## Run Summary

| Surface | Result |
|---|---|
| Dev API + frontend health | ✅ healthy |
| Admin login + seed customer fetch | ✅ |
| Estimate create | ✅ (`bdbcfc63-8e3b-471a-9516-e5ea2d580c27`) |
| `POST /estimates/{id}/send` (customer email + customer SMS) | ❌ 500 — Bug #1 |
| Portal link `/portal/estimates/<token>` render | ✅ (with cosmetic gaps — Bug #2) |
| Portal Approve button → fires customer email + internal email + signed PDF | ✅ emails arrived |
| Portal Approve → DB persists `status=approved`, `approved_at`, `job_id` | ❌ rolled back — Bug #1 |
| Job + appointment create (direct API) | ✅ |
| `POST /appointments/{id}/send-confirmation` (Y/R/C SMS to phone) | ✅ delivered |
| Human Y reply → CallRail webhook → appointment CONFIRMED | ❌ 400 rejection — Bug #3 |
| Simulator Y reply (HMAC-signed) → appointment CONFIRMED | ❌ 500 unique violation — Bug #4 |
| Invoice create + Stripe Payment Link generation | ✅ |
| `POST /invoices/{id}/send-link` (SMS preferred, email fallback) | ⚠️ SMS dedup-soft-failed mislabeled `provider_error`; email ✅ — Bug #2b |
| Stripe checkout page render + Apple Pay accepted | ✅ — Stripe sent customer receipt |
| `payment_intent.succeeded` → invoice PAID | ❌ unmatched_metadata — Bug #5 |
| `checkout.session.completed` → fallback path | ❌ 500 phone validation — Bug #6 |
| Receipt SMS after payment | ❌ never fired (blocked by #5) |

**Emails delivered to kirillrakitinsecond@gmail.com (Resend logs):**
- `f2504760-563b-4da2-8d19-69872ad38e54` — *"Your signed estimate from Grin's Irrigation"* (PDF, 13152 bytes)
- `2e53a65d-084b-44dc-a671-4608aa71a47a` — *"Estimate APPROVED for Test User"* (internal staff)
- `6edb5a4f-a191-49e3-9a0b-b3948c2ea7ad` — *"Your invoice from Grin's Irrigation — $50.00"* (payment link)

**SMS delivered to +19527373312 (CallRail):**
- conv `k8mc8`, thread `SMT019de95f6f0e78d1ad1a7bb4fd59fc49`, 598ms — appointment confirmation (Y/R/C prompt)

---

## Bug 1 — `send_estimate` + estimate-approval rolls back on `ck_sent_messages_recipient` 🔴 P0

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 3 of umbrella). `send_automated_message` now accepts `customer_id` / `lead_id` / `is_internal` keyword args; estimate / lead / notification / resend-webhook call sites thread the right FK so `SentMessage` rows satisfy the CHECK constraint without poisoning the transaction.

**File:line**: `src/grins_platform/services/estimate_service.py:322, 363, 629, 1083` + `src/grins_platform/services/sms_service.py:532-610` + `src/grins_platform/services/sms/recipient.py:62-80`
**Constraint**: `ck_sent_messages_recipient` requires `customer_id IS NOT NULL OR lead_id IS NOT NULL` (`models/sent_message.py:128`).

**Repro** (against dev):
```bash
TOKEN=$(curl -s -X POST $API/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 1. Create estimate
EST=$(curl -s -X POST $API/api/v1/estimates -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{
    "customer_id":"a44dc81f-ce81-4a6f-81f5-4676886cef1a",
    "line_items":[{"description":"x","quantity":1,"unit_price":100,"amount":100}],
    "subtotal":100,"total":100
  }' | jq -r .id)

# 2. Send → 500
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -X POST $API/api/v1/estimates/$EST/send -H "Authorization: Bearer $TOKEN"
# → HTTP 500
```

**Root cause**: `EstimateService.send_estimate` (and `_notify_internal_decision`) call `sms_service.send_automated_message(phone, message, message_type)`. That shim builds a `Recipient.from_adhoc(phone=phone)` which leaves `customer_id` and `lead_id` `None`. The downstream `send_message` writes a `SentMessage` row with both FKs null, which violates `ck_sent_messages_recipient`. The IntegrityError poisons the SQLAlchemy session; subsequent attribute access on `estimate.customer` (lazy load) raises `PendingRollbackError`, rolling back the entire `/send` (or `/approve`) transaction including the `status=sent`/`status=approved` update and the auto-job creation.

**Verification**:
- `grep -n "send_automated_message" src/grins_platform/services/estimate_service.py` → 4 hits at 322, 363, 629, 1083 (all phone-only).
- `grep -n "ck_sent_messages_recipient" src/grins_platform/models/sent_message.py` → constraint definition at line 128–129.
- Railway logs around 14:56:58 + 14:59:52 show two distinct rollback traces with the exact failing INSERT.
- Compare to `services/appointment_service.py:1769` which uses `Recipient.from_customer(customer)` correctly + threads `job_id`/`appointment_id` — that path is unaffected.

**Symptom-vs-independent filter**: Independent. Affects estimate-portal flow exclusively; does NOT depend on any other listed bug.

**If not resolved**: every estimate sent through the standard `/send` endpoint and every portal-side approval/rejection rolls back its DB state. Operators see "estimate stuck in draft" while customers are receiving email confirmations and signed-PDF copies of their *"approved"* estimate. Two visible consequences:
- Sales pipeline can't move estimates → jobs without manual SQL or a separate API path.
- Customer trust hit: their inbox confirms approval, our admin says "still draft." Disputes will look like fraud accusations.

**If resolved**: estimate send + portal approve flow works end-to-end without leaked emails. Estimate transitions persist; auto-job creation persists; standard reporting (dashboard "approved this week") starts being accurate.

**Suggested fix** (smallest blast radius):
1. Extend `Recipient.from_adhoc` to accept optional `customer_id: UUID | None = None`.
2. Add optional `customer_id` / `lead_id` kwargs to `send_automated_message` and thread them into `Recipient.from_adhoc`.
3. Update the 4 call sites in `estimate_service.py` to pass `customer_id=estimate.customer.id` (customer branch) / `lead_id=estimate.lead.id` (lead branch).
4. Backfill the same fix to `lead_service.py:126,359,1733` and `notification_service.py:1142` (lead branches), `resend_webhooks.py:153` (internal SMS notification).

---

## Bug 2 — Portal estimate page: empty "Prepared for:" + "Invalid Date" 🟢 P3 (cosmetic)

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 5 of umbrella). `PortalEstimateResponse` now exposes `customer_first_name`, `customer_last_name`, `customer_email`, `created_at`, `sent_at`. Frontend renders them with fallback to legacy `customer_name`.

**File:line**: `src/grins_platform/schemas/portal.py PortalEstimateResponse` + portal frontend (un-traced).
**API endpoint**: `GET /api/v1/portal/estimates/<token>`

**Repro**:
```bash
curl -s $API/api/v1/portal/estimates/41df0929-2870-46bc-a227-39575019fff6 | jq 'keys'
# Returns: company_address, company_logo_url, company_name, company_phone,
# discount_amount, estimate_number, line_items, notes, options, promotion_code,
# readonly, status, subtotal, tax_amount, total, valid_until
# NO customer_first_name, customer_last_name, customer_email, created_at, sent_at.
```

**Root cause**: `PortalEstimateResponse` deliberately does not include customer name fields nor a date the portal can use as the "Date:" label. The portal frontend reads a property (likely `created_at` from the underlying estimate) which is undefined and renders `new Date(undefined)` → "Invalid Date". The "Prepared for:" label has no source to render.

**Verification**: see `keys` output above. Also visually verified — screenshot at `e2e-screenshots/master-plan/phase-portal/02-full.png`.

**Symptom-vs-independent filter**: Independent. Two related cosmetic regressions; could be combined into one fix.

**If not resolved**: customers see a blank "Prepared for:" label (looks unprofessional) and a broken "Date: Invalid Date" string. They may misinterpret the estimate as malformed and not approve.

**If resolved**: portal estimate page is fully populated; "Prepared for: First Last" + "Date: 5/4/2026" render correctly; reduces "is this a real estimate?" customer support load.

### Bug 2b (related, P3) — `provider_error` mislabel on payment-link SMS soft-fail

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 5 of umbrella). New sibling `sms_failure_detail: str | None` field on `SendLinkResponse` carries the raw upstream reject reason (e.g. `duplicate_message_within_24_hours`) without widening the strict categorical literal.

`services/invoice_service.py` returns `sms_failure_reason: "provider_error"` when the actual reason in logs is `duplicate_message_within_24_hours` (dedup gate). The label dilutes the signal — operators reading the response can't tell if it was rate-limit / dedup / network / 5xx.

**Suggested**: thread the actual reject reason from `business.smsservice.send_message_rejected.reason` field through to `attempted_channels` reporting.

---

## Bug 3 — Real CallRail inbound webhooks rejected with 400 `replay_or_stale_timestamp` 🔴 P0

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 2 of umbrella). New `_extract_created_at` helper falls back `payload.created_at` → `payload.sent_at` → receipt time and emits a `sms.webhook.timestamp_source` log line per request. Resource-id dedup remains the primary replay barrier.

**File:line**: `src/grins_platform/api/v1/callrail_webhooks.py:296` + `src/grins_platform/services/sms/webhook_security.py:99-108`

**Repro**: Trigger any outbound SMS to +19527373312 from dev, have human reply Y/R/C/STOP, watch Railway logs.

```
[INFO]  request_id="041f4dd2-..." event="api.request.webhook_inbound_started"
[WARN]  created_at="" skew_seconds=0 event="sms.webhook.replay_rejected"
[INFO]  reason="replay_or_stale_timestamp" event="validation.schema.webhook_payload_rejected"
INFO:   POST /api/v1/webhooks/callrail/inbound HTTP/1.1 400 Bad Request
```

**Root cause**: `callrail_webhooks.py:296` does `payload.get("created_at", "")`. The actual CallRail inbound payload either:
1. uses a different field name (`timestamp`? `created`? nested under `resource.created_at`?), OR
2. CallRail just doesn't include a `created_at` for inbound text-message webhooks.

`check_freshness("")` returns `(False, 0)` (line 99) → 400 rejection. The HMAC signature was valid (passed line 243); only the freshness gate failed.

**Verification**:
- Run #1 at 15:04:38 with real human Y reply → 400 rejection (logs).
- Test fixtures at `tests/integration/test_callrail_webhook_endpoint.py:64-72` use `created_at` at the top level — that matches the validator but does NOT match what CallRail actually sends (proven by today's run).
- Simulator at `e2e/master-plan/sim/callrail_inbound.sh:67` puts `created_at` at top level → freshness check passes (Bug #4 then fires next).

**Symptom-vs-independent filter**: Independent. Hard prerequisite to ANY human SMS reply working — Y, R, C, STOP, ad-hoc, all blocked.

**If not resolved**: every customer SMS reply on dev (and presumably any environment using current CallRail provider config) is silently dropped. Y replies don't confirm appointments; R replies don't open reschedule requests; STOP replies don't honor opt-out (compliance issue!). Customer thinks they confirmed; admin sees "no reply"; appointment may auto-cancel; tech shows up at unconfirmed slot.

**If resolved**: all human SMS reply paths work. Phase 9 (confirmation Y/R/C) runs human-in-the-loop without simulator. Phase 14 (payment-link reply correlation) works. STOP/HELP compliance honored.

**Suggested fix path**:
1. Add a temporary debug-log dump of the raw payload to confirm what fields CallRail actually sends, OR check CallRail's webhook docs at `https://docs.callrail.com/` (text-messages section).
2. Either: (a) update `payload.get("created_at", "")` to read from CallRail's actual field path, or (b) fall back to `Date.now()` receipt-time when `created_at` is empty (relies on resource_id dedup which is already in place via `_REDIS_MSGID_KEY_PREFIX` for replay protection — defense-in-depth not weakened).

---

## Bug 4 — `_try_poll_reply` orphan-inserts into `campaign_responses` with empty `provider_message_id`, blocking all confirmation Y replies 🟠 P1 (gated by Bug #3)

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 4 of umbrella). Application coerces empty `provider_sid` to `None` before insert; new alembic migration `20260507_120000_harden_provider_message_id_partial_index` backfills existing empty rows to NULL and recreates the partial unique index with `provider_message_id IS NOT NULL AND provider_message_id <> ''`.

**File:line**: `src/grins_platform/services/campaign_response_service.py:266` + `src/grins_platform/api/v1/callrail_webhooks.py:381`

**Repro** (after Bug #3 fixed, or via simulator):
```bash
export CALLRAIL_WEBHOOK_SECRET=$(railway variables --service Grins-dev --environment dev --kv \
  | grep ^CALLRAIL_WEBHOOK_SECRET= | cut -d= -f2-)
export API_BASE=https://grins-dev-dev.up.railway.app
THREAD="SMT019de95f6f0e78d1ad1a7bb4fd59fc49"  # from outbound send
e2e/master-plan/sim/callrail_inbound.sh "$THREAD" "Y"
# → HTTP 200 {"status":"error_logged"}, but appointment never CONFIRMED
```

Logs:
```
campaign_response.campaignresponseservice.correlate_reply_completed matched=true campaign_id=null
campaign.response.orphan
asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint
  "ix_campaign_responses_provider_message_id"
DETAIL:  Key (provider_message_id)=() already exists.
```

**Root cause**: `handle_inbound` calls `_try_poll_reply` first. That correlates by `thread_resource_id`, returns `matched=true campaign_id=null` (no matching campaign), but still INSERTs an orphan row to `campaign_responses` with `provider_message_id=''` (empty string from the simulator payload's missing `id` field). A previous run's row with `provider_message_id=''` already exists (the unique index treats empty string as a value, not null) → duplicate key. The IntegrityError poisons the session and the appointment-confirmation handler never runs.

**Verification**:
- Railway logs at 15:07:35 show the full traceback.
- `grep -n "provider_message_id" src/grins_platform/services/campaign_response_service.py` and `grep -n "ix_campaign_responses_provider_message_id" src/grins_platform/migrations/`.

**Symptom-vs-independent filter**: Independent of Bug #3 (each is its own gate). With #3 unfixed, real replies don't even reach this code; with #3 fixed, this still blocks Y replies for appointment confirmation. Therefore separately promotable.

**If not resolved**: even after fixing CallRail-side `created_at` (Bug #3), Y replies for appointment confirmation 500 the inbound webhook. Same operational impact as #3 (replies dropped) but now with corrupted DB state from the unique-violation rollback chain.

**If resolved**: Y/R/C confirmation replies route correctly to the appointment-confirmation handler; appointments transition draft → scheduled → confirmed without operator intervention.

**Suggested fix**:
- Either skip orphan-row insert entirely when `campaign_id is None` (handle_inbound dispatcher should fall through to the next correlator).
- Or coerce `provider_message_id=""` to `None` before INSERT so unique index doesn't collide on multiple empties.
- Or change the unique index to `WHERE provider_message_id IS NOT NULL` (partial index).

---

## Bug 5 — Stripe Payment Link metadata not propagated to PaymentIntent → invoice never PAID 🔴 P0 BLOCKER

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 1 of umbrella). `StripePaymentLinkService.create_for_invoice` now sets `payment_intent_data.metadata` mirroring the top-level metadata so the PI handler reads `invoice_id` deterministically. Defensive `_handle_checkout_completed_invoice_payment` correlator backfills any in-flight PaymentLinks created before this fix.

**File:line**: `src/grins_platform/services/stripe_payment_link_service.py:100-110` (link create) + `src/grins_platform/api/v1/webhooks.py:1048-1054` (PI handler unmatched-metadata branch)

**Repro**: Pay any dev invoice via its Stripe Payment Link (Apple Pay, card, anything). Watch Railway logs for `unmatched_metadata` and verify invoice stays `draft`.

```
[WARN]  payment_intent="pi_3TT***CAe0" event="stripe.webhook.payment_intent.unmatched_metadata"
```

```bash
curl -s $API/api/v1/invoices/$INV -H "Authorization: Bearer $TOKEN" | jq '.status, .paid_at'
# → "draft" null   (despite Stripe-side payment success)
```

**Root cause**: `StripePaymentLinkService.create_for_invoice` builds the Payment Link with:
```python
params = {
    "line_items": ...,
    "metadata": {"invoice_id": ..., "customer_id": ...},  # ← only on PaymentLink object
    ...
}
```
Stripe propagates `metadata` from PaymentLink → CheckoutSession but does NOT auto-propagate to the resulting PaymentIntent. To get `metadata` on the PI, you must set `payment_intent_data.metadata` explicitly on Payment Link create. The Architecture-C reconciliation handler `_handle_payment_intent_succeeded` reads `metadata.get("invoice_id")` from the PI — which is empty — and returns early.

**Verification**:
- `grep -n 'payment_intent_data\|metadata' src/grins_platform/services/stripe_payment_link_service.py` → only top-level `metadata`, no `payment_intent_data`.
- Stripe API docs: PaymentLink → `payment_intent_data.metadata` is the canonical way to thread metadata to the PI.
- Logged event `evt_3TTOFjQDNzCTp6j508laZsaU` (today's Apple Pay) has `metadata={}` on the PI.

**Symptom-vs-independent filter**: Independent. Top-cause of "Apple Pay went through but invoice still draft."

**If not resolved**: every Stripe Payment Link payment fails to reconcile. Invoices stuck in `draft`/`sent` forever; receipt SMS never fires; `Job.payment_collected_on_site` never set; revenue reporting wildly inaccurate; manual SQL reconciliation required for every payment. The previously-shelved "Architecture C reconciliation deterministic via metadata.invoice_id" promise (per project memory) is **not actually delivered**.

**If resolved**: Architecture-C works as designed. PI carries `invoice_id`, handler matches, invoice → PAID, `paid_at` set, `paid_amount` set, `payment_method='credit_card'` (or method-specific), receipt SMS dispatched, job marker set, dashboard accurate.

**Suggested fix** (one-line):
```python
params: dict[str, Any] = {
    "line_items": line_items,
    "metadata": {"invoice_id": str(invoice.id), "customer_id": str(invoice.customer_id)},
    "payment_intent_data": {  # ← ADD
        "metadata": {"invoice_id": str(invoice.id), "customer_id": str(invoice.customer_id)},
    },
    "restrictions": {"completed_sessions": {"limit": 1}},
    ...
}
```
Backfill: any in-flight Payment Links created before this fix will still have empty PI metadata; either deactivate + recreate or add a `checkout.session.completed` correlator that reads metadata from the session and updates the invoice (defense in depth).

---

## Bug 6 — `checkout.session.completed` handler 500s on Apple Pay due to non-numeric synthetic phone fallback 🔴 P0

**Status**: ✅ RESOLVED 2026-05-04 by branch `feature/master-plan-2026-05-04-umbrella` (Phase 1 of umbrella). New `_synthetic_phone_for_event` derives a deterministic 10-digit phone via `sha256(event_id) % 10^10` so retries find the same customer and the synthetic always passes `normalize_phone`.

**File:line**: `src/grins_platform/api/v1/webhooks.py:340`

**Repro**: Pay any subscription/Stripe checkout via Apple Pay where `customer_details.phone` is empty (Apple Pay often omits phone). Watch logs.

```
ValidationError: 1 validation error for CustomerCreate
phone
  Value error, Phone must be 10 digits (North American format)
  [type=value_error, input_value='000SoDqVvS', input_type=str]
```

**Root cause**: line 340 fallback:
```python
phone=normalized_phone or phone_raw or f"000{event['id'][-7:]}",
```
Stripe event IDs like `evt_1TTOFlQDNzCTp6j5nSoDqVvS` have alphanumeric suffixes. `event['id'][-7:]` = `SoDqVvS`. With `000` prefix = `000SoDqVvS` — non-numeric, fails `CustomerCreate.phone` validator (`schemas/customer.py` requires 10 digits).

**Verification**:
- `grep -n "000.*event\['id'\]" src/grins_platform/api/v1/webhooks.py` → confirms line 340.
- Today's run: `evt_1TTOFlQDNzCTp6j5nSoDqVvS` → fallback emitted `000SoDqVvS` → ValidationError.

**Symptom-vs-independent filter**: Independent. Can fire for any agreement-signup checkout where phone is missing — not specific to invoice flow.

**If not resolved**: any agreement signup via Apple Pay (or other Stripe surfaces that omit phone) crashes the webhook handler. New customer / new agreement isn't created; seasonal jobs aren't generated; welcome email isn't sent; consent records aren't linked. Stripe will retry (idempotency-keyed), but every retry produces the same crash. The customer paid but is invisible to our system until manually onboarded.

**If resolved**: agreement signups via Apple Pay (and any other phone-less checkout method) complete the post-payment flow as designed: customer created, agreement PENDING, jobs generated, consent linked, welcome+confirmation emails sent.

**Suggested fix**: replace the fallback with either
- a real digit-only synthetic: `f"5550000000"` (sentinel) or `f"{abs(hash(event['id'])) % 10**10:010d}"` (deterministic from event ID, all digits), or
- skip phone entirely when missing — make `CustomerCreate.phone` allow `None` and gate phone-keyed lookup on its presence rather than requiring a synthetic.

The hash-to-digits approach is simplest and preserves the "match-by-phone if Stripe ever does send one for this event" idempotency property — but the cleaner architectural answer is to treat phone as optional everywhere downstream.

---

## Retracted candidates / notes (none this run)

All six bugs above passed the Step 2 / Step 2a / Step 2b verification. No symptoms-of-parent and no fabricated citations.

---

## Suggested priority order for fixing

1. **Bug #5** (P0 BLOCKER) — payment reconciliation broken; one-line fix; unblocks revenue reporting + receipt SMS path.
2. **Bug #3** (P0) — real human SMS replies dropped; needs CallRail payload investigation + small validator change.
3. **Bug #6** (P0) — agreement signup crashes on Apple Pay; one-line fix.
4. **Bug #1** (P1) — estimate flow rolls back; small refactor (~5 file edits) but well-scoped.
5. **Bug #4** (P1) — Y reply orphan-insert; partial-index migration or `_try_poll_reply` early-skip.
6. **Bug #2 / 2b** (P3) — portal cosmetic + soft-fail-reason mislabel; bundle into one PR.

---

## Reproducibility / artifacts

- Screenshots: `e2e-screenshots/master-plan/phase-portal/{01-08}*.png`
- Estimate ID: `bdbcfc63-8e3b-471a-9516-e5ea2d580c27` (token `41df0929-2870-46bc-a227-39575019fff6`)
- Job ID: `43caa0c3-8d05-4cdf-85e2-e619acd7c3e7`
- Appointment ID: `a6927c81-c38c-4670-acdd-cad2c18759c6` (status stuck at `scheduled`)
- Invoice ID: `51c68abb-c84d-42c4-a783-edb51b2f82d6` (status stuck at `draft` despite Apple Pay success)
- Stripe Payment Link: `plink_1TTO7fQDNzCTp6j5nDSKtyhr` / `https://buy.stripe.com/test_5kQ9AV6XSc366rGeCKeQM0q`
- Stripe events: `evt_3TTOFjQDNzCTp6j508laZsaU` (PI succeeded, unmatched), `evt_1TTOFlQDNzCTp6j5nSoDqVvS` (checkout completed, handler crashed)

---

## What's NOT covered by this run (out of scope today)

- Phase 10 reschedule R-reply path (gated by Bug #3 + #4)
- Phase 11 tech-mobile on-my-way SMS / on-site payment collection
- Phase 16 contract renewals (`invoice.paid` Stripe event — separate from payment_intent.succeeded)
- Phase 18 resource-timeline / capacity bars
- Phase 21 dispute / refund webhooks (`charge.dispute.created`, `charge.refunded`)
- Phase 22 mobile viewport regression sweep

These are independent and unblocked by today's findings; will need their own runs.
