# Feature: Stripe Card Payments via Stripe Dashboard App + Webhook Reconciliation

**Status:** PLAN ONLY — no code changes. This is the executable, complete spec.

> The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

---

## Why this approach (the reframe)

A previous version of this plan was anchored on adding in-app Tap-to-Pay through the existing `PaymentCollector.tsx` flow. **That path does not work and never has** — Stripe's `@stripe/terminal-js` SDK does not support Tap to Pay at all (no `'tap_to_pay'` discovery method exists in the JS SDK; the `@ts-expect-error` in `PaymentCollector.tsx:114` is suppressing that fact). Triple-confirmed against Stripe's docs and JS SDK API reference. The Stripe Reader M2 hardware also can't be used from a browser — Bluetooth Stripe readers require the iOS, Android, or React Native native SDKs.

Rather than build a Capacitor/RN wrapper (~2 weeks once + perpetual app-store maintenance) or buy new hardware ($349 S700), we are deliberately choosing a **two-app workflow** as the *complete and final* shape of this feature:

- **Field staff use the official Stripe Dashboard mobile app** (Stripe's first-party app — already supports the M2 over Bluetooth on both iPhone and Android, and supports phone-NFC Tap to Pay natively) to actually charge the customer's card.
- **Grin's web app reconciles those charges back to invoices via webhook**, so the Invoices tab and the appointment modal stay the source of truth without ever touching a Stripe SDK in the browser.
- The M2 hardware the user already has remains useful, with zero additional dev effort beyond reconciliation.

This is not a stopgap. It is a coherent end state shipped by many production CRMs that integrate with Stripe.

---

## Feature Description

When the field tech / admin is at (or has just completed) an appointment, they collect payment using one of two paths from inside the Appointment Modal:

1. **"Take Card Payment via Stripe app"** — the appointment modal displays the invoice number and amount due; tech switches to the Stripe Dashboard app, charges the card on the M2 (or via the phone's NFC Tap to Pay — both supported by Stripe's app natively), and types `INV-YYYY-NNNN` in the description field. Within seconds, Grin's webhook handler matches the resulting `payment_intent.succeeded` event back to the invoice and marks it paid.
2. **"Record Other Payment"** — manual record of cash, check, Venmo, or Zelle (already working today; no change other than a small reference-prefix normalization).

Either path produces (or updates) an **Invoice** that lands in the **Invoices tab** with the correct status, payment method, amount, Stripe charge ID, and audit trail. Refunds and disputes initiated from the Stripe Dashboard also reconcile back into Grin's via the same webhook pipeline.

## User Story

As an **admin or field technician** using the Grin's Irrigation web app on my phone,
I want to **collect a card payment from a customer at the end of the visit using my phone's Stripe app (with the M2 reader or phone-NFC Tap to Pay)**,
so that **the payment is captured immediately, the corresponding invoice is automatically marked paid in the Invoices tab, the customer gets an automatic Stripe receipt, and I never have to do double-entry between two systems.**

## Problem Statement

Today the platform can record payments after the fact (cash, check, Venmo, Zelle, manually-entered card reference) but there is no automated reconciliation of card charges, no way to use the M2 hardware the user has, and the existing in-app Tap-to-Pay code is non-functional dead code that lies to anyone reading it. Field staff cannot collect a card payment in a way that updates Grin's automatically.

Concretely:

1. **Phone NFC Tap to Pay from a web app is not possible** — Stripe's JS SDK does not implement it; native runtime required.
2. **The Stripe Reader M2 is not usable from a web app** — Bluetooth readers require the iOS / Android / RN native SDKs.
3. **The existing `PaymentCollector.tsx` Tap-to-Pay flow is broken** — `discoverReaders({ method: 'tap_to_pay' })` is suppressed with `@ts-expect-error` because the SDK does not accept that parameter; at runtime this returns no readers (or errors).
4. **The webhook handler does not subscribe to `payment_intent.*` or `charge.*` events** — even if charges happened, Grin's wouldn't learn about them automatically.
5. **Stripe customers exist for some Grin's customers but not all** — `Customer.stripe_customer_id` field exists (`models/customer.py:111`) but is not consistently populated; reconciliation by customer is unreliable.

## Solution Statement

Five coordinated workstreams, in this order:

1. **Stripe account & ops setup** — enable Tap to Pay on the Stripe account, register the new webhook event subscriptions, ensure receipt/branding settings are right in the Stripe Dashboard, document the staff training (description format, customer selection in the Stripe app).
2. **Customer linkage hardening** — make sure every Grin's customer has a `stripe_customer_id`, idempotently. Backfill once + auto-create on customer create/update going forward.
3. **Webhook hardening (the spine)** — add `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created` to the handler with description-regex match → customer+amount fallback → `unmatched_stripe_charges` queue. Add full idempotency, refund/dispute lifecycle, audit logging.
4. **Frontend rewire** — *delete* the broken Tap-to-Pay button and state machine; replace with clear "Take Card Payment via Stripe app" instructions surfacing the invoice number prominently, plus copy-to-clipboard. Keep "Record Other Payment" path as today with a small reference-prefix normalization. Add a "Paid" pill to the Appointment Modal once the linked invoice is paid. Add Stripe-channel display to the Invoices tab.
5. **Admin reconciliation surface** — `unmatched_stripe_charges` table + simple admin page where unmatched charges can be linked to invoices manually. Required, not optional — this is the safety net for typo'd descriptions.

## Feature Metadata

- **Feature Type:** Enhancement / completion of a partial feature.
- **Estimated Complexity:** **Medium**.
- **Estimated Effort:** ~2 weeks of focused work for the full set; manual reconciliation tier (B1) is shippable today with zero code (just train staff to use Record Payment with the Stripe charge ID).
- **Primary Systems Affected:**
  - Backend: `api/v1/webhooks.py`, `services/customer_service.py`, `services/invoice_service.py`, `services/appointment_service.py`, `models/invoice.py` (new enum value), `models/stripe_webhook_event.py` (no change; just used), new `models/unmatched_stripe_charge.py`, new repository, new admin endpoints.
  - Frontend: `features/schedule/components/PaymentCollector.tsx` (major rewrite — delete broken paths), `features/schedule/components/AppointmentModal/AppointmentModal.tsx` (add paid-state pill), `features/invoices/components/PaymentDialog.tsx` (small reference-prefix tweak), new `features/invoices/pages/UnmatchedCharges.tsx`, plus mutation/key updates.
  - Database: 1 new table (`unmatched_stripe_charges`), 1 enum addition (`InvoiceStatus.REFUNDED`), possibly 1 backfill.
  - Ops: Stripe webhook subscription update, Stripe Dashboard app rollout to staff, training material.
- **Dependencies:** `stripe>=8.0.0` ✅ already installed. **No new packages required.** `@stripe/terminal-js` becomes unused — flag for removal.
- **External:** real Stripe account in good standing with Tap to Pay enabled, Stripe Dashboard mobile app installed on staff phones, M2 reader paired with the Stripe Dashboard app.

## Out of Scope (explicit non-goals)

These are intentionally not part of this feature so it stays shippable. Each is captured in the Future Considerations section at the end.

- **In-app Tap-to-Pay or in-app card charging from the Grin's web app.** (Would require Capacitor/RN wrapper. Not happening here.)
- **In-app pairing of the M2 reader from the Grin's web app.** (Same reason.)
- **Subscription/recurring billing and invoice generation from Stripe** — the existing `service_agreement_*` and `subscription` flows already exist and this feature does not touch them.
- **Sales tax handling.** This feature does not collect or remit sales tax. Invoice totals are charged as-is; if tax ever becomes in-scope it is a separate plan.
- **Tipping in the Stripe Dashboard app.** Tipping is disabled at the Stripe account level (Phase 0 task). Not a feature of this plan and not handled in code.
- **3% Stripe surcharge** (Obsidian Note 08 question) — explicit user decision needed; not part of this plan.
- **Custom Grin's-branded receipts** — Stripe sends receipts automatically; the plan deliberately does not double-send.
- **SMS receipts** — Stripe sends email receipts; SMS receipt would need a new send path. Not in this plan.
- **Removing the `services/stripe_terminal.py` and `api/v1/stripe_terminal.py` modules.** These become unused but are kept in place for a possible future Capacitor wrapper. Marked deprecated in code comments; full removal is a separate cleanup PR.

---

## CRITICAL GAPS TO ADDRESS BEFORE MERGE

The base plan above describes the happy-path architecture. The following gaps were surfaced during a red-team review and **must** be addressed before the plan is considered complete. They are listed as a single punch list here, then woven into specific tasks in the relevant phases below. **Any one of these, left unaddressed, is sufficient to ship a broken feature.**

### Open decisions that need user input (block Phase 2 merge)

- **CG-1: REMOVED — tipping is out of scope (see Out of Scope section). Tipping is disabled at the Stripe account level in Phase 0.**
- **CG-2: REMOVED — sales tax is out of scope (see Out of Scope section). Invoices are charged as-is; no tax line item is added in the Stripe app.**
- **CG-3: Lead support.** Today only `customers` have `stripe_customer_id`; `leads` do not. If a tech is at an estimate visit (Lead, not converted Customer yet) and takes a deposit, none of the matching strategies work. **Decide:**
  - **(a) Block card payments for Leads** — must convert Lead → Customer first. Frontend enforces. **Recommended for v1.**
  - (b) Add `stripe_customer_id` to leads + extend customer-fallback to also search Leads. More plumbing.
- **CG-4: Discount / on-the-fly price adjustment workflow.** Tech says "I'll knock $50 off." Invoice $350; charge $300. Amount mismatch → unmatched. **Decide:**
  - **(a) Tech must update the invoice amount in Grin's first**, then charge. Extra step but fully auditable. **Recommended.**
  - (b) Tolerate undercharge in matcher (link by description even if amount differs; mark invoice as PARTIAL with the charged amount). Permissive but loose.
  - (c) Always defer to admin reconciliation. Operationally costly.
- **CG-17: "Add new customer" in tech Stripe roles.** If a tech taps "Add new customer" inside the Stripe app instead of selecting an existing one, the resulting Stripe Customer has no `metadata.grins_customer_id` → customer-fallback fails permanently. **Decide:**
  - **(a) Disable customer-creation permission in tech Stripe roles** (verify in Settings → Team → Roles whether Stripe's permission grain supports this). **Recommended if available.**
  - (b) Pure training discipline. Document explicitly in tech 1-pager + admin spot-check weekly.

### Build-now items (folded into the phases below — see step-by-step tasks)

- **CG-5: Invoice must exist *before* charge.** Plan implicitly assumed it. **Make explicit:** "Take Card Payment" creates-or-fetches the invoice via the existing `POST /appointments/{id}/create-invoice` endpoint *before* showing the instructions card with the invoice number. → Tasks 3.0a, 3.1a.
- **CG-6: Pending-payment UI feedback.** Between "tech opens Stripe app" and "webhook arrives" there's no signal in Grin's. **Add:** when the modal is in awaiting-payment state, poll the appointment's invoice every 3–5 seconds and show a "Waiting for Stripe payment…" indicator that auto-collapses when the invoice flips to PAID. → Task 3.1b.
- **CG-7: Subscription / PaymentIntent overlap.** Both `invoice.paid` (existing handler, for service-agreement subscription renewals) and `payment_intent.succeeded` (new handler) fire for a single subscription renewal. The new handler must short-circuit when `event.data.object.invoice` is set — that means this PaymentIntent belongs to a Stripe Invoice already handled by `_handle_invoice_paid`. → Task 2.8a.
- **CG-8: Cancelled-while-pending race.** Admin cancels invoice while a charge is in flight. Webhook arrives for a CANCELLED invoice. **Behavior:** handler refuses to mark CANCELLED invoices paid; inserts into `unmatched_stripe_charges` with reason `invoice_cancelled`; raises a high-severity log/alert so admin can manually refund the customer in Stripe. → Task 2.8b.
- **CG-9: Multi-invoice charge split.** A $1000 charge covering 3 invoices lands in unmatched. The admin UI as designed only links to one. **Add:** "Split across invoices" admin action allocating a charge to multiple invoices (with sum-equals-amount validation). → Task 4.3a.
- **CG-10: Estimate/deposit two-payment flow.** Big installs take 50% upfront, 50% on completion. Confirm `Invoice.paid_amount` + `PARTIAL` status support incremental payments end-to-end (description matcher must handle "second charge against an already-PARTIAL invoice"). → Task 2.8c + edge cases.
- **CG-11: Cleanup policy for stale unmatched charges.** Rows in `unmatched_stripe_charges` don't auto-archive. **Add:** scheduled job archiving resolved rows >90 days old; alert when unresolved count grows beyond threshold (e.g., 10). → Task 4.6.
- **CG-12: Notifications when unmatched grows.** **Add:** structured log alert `unmatched_stripe_charges.threshold_exceeded` plus a daily 8am digest email to admins listing unresolved rows. → Task 4.5a.
- **CG-13: Search invoices by Stripe charge ID.** Admins will paste `pi_*` into Invoices search and expect a hit. **Verify** the existing 9-axis filter on `payment_reference` supports substring; if not, add it. → Task 3.7a.
- **CG-14: Tech audit trail.** Webhook handler doesn't capture *which* tech processed the charge. Stripe knows (charge.balance_transaction or staff who created the charge). **Add:** new optional `Invoice.collected_by_stripe_user_id` column populated from `event.data.object.metadata` when present (Stripe app may not expose this directly — verify via test event; if not available, defer to v2 with a note). → Task 2.8d (effort-gated).
- **CG-15: Legacy `PaymentMethod.STRIPE` rows.** Plan keeps the legacy enum value (per `features/invoices/types/index.ts:19–22`). **Add:** `InvoiceList` channel pill renderer handles `STRIPE` legacy as "Stripe (legacy)" pill; **no migration** of historical data. → Task 3.7b.
- **CG-16: Custom Stripe receipt sender domain.** Default receipts come from `noreply@stripe.com`. **Add:** Phase 0 task to configure sender domain in Stripe Dashboard → Settings → Emails (e.g., `payments@grins-irrigation.com`). Requires DKIM/SPF DNS records — coordinate with whoever owns the domain. → Task 0.4.
- **CG-18: `service_agreement.stripe_customer_id` ↔ `customer.stripe_customer_id` coordination.** Both columns exist on different tables. They must reference the same Stripe Customer for the same Grin's customer. **Add:** Alembic data audit + invariant check in `CustomerService` and `ServiceAgreementService`. → Task 1.5.
- **CG-19: Receipt-resend mechanism.** When a customer says they didn't get a receipt, office resends from Stripe Dashboard → charge detail → "Resend receipt." **No code needed.** Document in runbook. → Task 5.1 expansion.

### Cross-cutting note

The "Edge Cases & Defensive Behaviors" section enumerates 25 happy/sad-path scenarios; the 19 gaps above are *additional structural items*, not just edge cases. Edge cases section has been extended (#26–32) to cover the new scenarios introduced by these gaps.

---

## CONTEXT REFERENCES

### Backend files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Webhook layer (the spine of this feature):**
- `src/grins_platform/api/v1/webhooks.py` (entire file, 1000+ lines, especially lines 60–71 for `HANDLED_EVENT_TYPES` and lines 960–1020 for the Stripe handler) — `stripe.Webhook.construct_event(payload, sig_header, secret)` for signature verification, idempotency via `StripeWebhookEventRepository`. Currently handles: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `invoice.upcoming`, `customer.subscription.updated`, `customer.subscription.deleted`. **Must add:** `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
- `src/grins_platform/models/stripe_webhook_event.py` (71 lines) — `stripe_webhook_events` table. Fields: `stripe_event_id` (unique index), `event_type`, `processing_status`, `error_message`, `event_data` (JSONB), `processed_at`. **Already provides idempotency.** No change needed.
- `src/grins_platform/repositories/stripe_webhook_event_repository.py` — `get_by_stripe_event_id`, `create_event_record`, `mark_processed`. Use as-is.

**Stripe configuration:**
- `src/grins_platform/services/stripe_config.py` (lines 13–48) — `StripeSettings` Pydantic model with `stripe_secret_key`, `stripe_webhook_secret`, `stripe_publishable_key`, `stripe_customer_portal_url`, `stripe_tax_enabled`, `stripe_terminal_location_id`. `is_configured` property. **Add:** `stripe_api_version` for explicit pinning (current SDK default; we want to lock).

**Customer ↔ Stripe linkage:**
- `src/grins_platform/models/customer.py:111` — `stripe_customer_id: Mapped[Optional[str]]`. **Already exists** (Req 28.1, 28.3). No migration needed — just ensure consistent population.
- `src/grins_platform/services/customer_service.py` (lines ~1445–1610) — already has `get_payment_methods()` and `charge_customer()` referencing Stripe. **Mine this for the existing pattern of `stripe.Customer.list(...)`, `stripe.PaymentIntent.create(...)`, error handling with `stripe.StripeError`.** Add a new public method `get_or_create_stripe_customer(customer_id) -> str` (returns the Stripe customer ID, idempotent).

**Invoice domain (heavy reuse):**
- `src/grins_platform/models/invoice.py` (entire file, 221 lines) — `Invoice` model. Key fields: `payment_method`, `payment_reference`, `paid_at`, `paid_amount`, `status`, `total_amount` (Decimal), `invoice_number` (unique, `INV-YEAR-SEQ`), `job_id`, `customer_id`, `created_at`, `notes`. The webhook will write to all of these.
- `src/grins_platform/models/enums.py` (lines 200–236) — `InvoiceStatus` (DRAFT/SENT/VIEWED/PAID/PARTIAL/OVERDUE/LIEN_WARNING/LIEN_FILED/CANCELLED) and `PaymentMethod` (CASH/CHECK/VENMO/ZELLE/STRIPE [legacy]/CREDIT_CARD/ACH/OTHER). **Add:** `InvoiceStatus.REFUNDED` and `InvoiceStatus.DISPUTED` (for the new handlers).
- `src/grins_platform/services/invoice_service.py` (entire file, 500+ lines) — full CRUD + `record_payment(invoice_id, PaymentRecord)` + lien lifecycle + mass notify. Custom errors: `InvoiceNotFoundError`, `InvalidInvoiceOperationError`. **Use existing `record_payment` flow rather than writing directly to model from webhook.**
- `src/grins_platform/repositories/invoice_repository.py` — standard async-SQLAlchemy repo pattern. Use as-is. **Add:** `get_by_invoice_number(number: str)` if it doesn't exist; `find_unpaid_for_customer_with_amount(stripe_customer_id, amount_cents)` for fallback match.
- `src/grins_platform/api/v1/invoices.py` — Invoice REST endpoints. Routes use `CurrentActiveUser` / `ManagerOrAdminUser` / `AdminUser`. DI pattern in `get_invoice_service()`.

**Appointment / Job linkage:**
- `src/grins_platform/services/appointment_service.py` (line 1763 onward) — `AppointmentService.collect_payment(appointment_id, payment)` — manual payment recording. Used by the "Record Other Payment" UI; webhook does NOT call this (writes directly via invoice service, since webhook's source of truth is Stripe).
- `src/grins_platform/services/appointment_service.py` (lines 169–181) — `payment_collected_on_site` revert-on-cancel logic. **Important:** webhook handler must set `Job.payment_collected_on_site = True` when marking invoice paid.
- `src/grins_platform/models/job.py:152` — `payment_collected_on_site: bool` column.
- `src/grins_platform/api/v1/appointments.py` (lines 1271–1318) — `POST /appointments/{id}/collect-payment` (manual flow). No change.

**Service-agreement / "no payment needed" logic (must respect):**
- `src/grins_platform/services/contract_renewal_service.py` and related — service-agreement-covered jobs.
- `src/grins_platform/tests/unit/test_payment_warning_service_agreement.py` — confirms the existing rule: jobs with active `service_agreement_id` should not show "No Payment" warnings. By extension, the appointment modal should not show a "Take Card Payment" CTA for these. **Verify the modal already enforces this in `AppointmentModal.tsx`; if not, add it (see Phase 4).**

**Existing Stripe-Terminal code (to be deprecated, not removed in this PR):**
- `src/grins_platform/services/stripe_terminal.py` (131 lines) — `StripeTerminalService.create_connection_token`, `create_payment_intent`. **Mark deprecated with module-level docstring; do not delete.** Future Capacitor work could revive this.
- `src/grins_platform/api/v1/stripe_terminal.py` (177 lines) — `/stripe/terminal/connection-token`, `/stripe/terminal/create-payment-intent`. **Same: mark deprecated, leave wired** so we don't break any in-flight feature flag.

**Tests to read before touching code:**
- `src/grins_platform/tests/unit/test_stripe_webhook.py` — pattern for mocking `stripe.Webhook.construct_event`, asserting idempotency and event routing. **Mirror this exactly for the new event types.**
- `src/grins_platform/tests/unit/test_stripe_terminal.py` — pattern for mocking Stripe SDK calls.
- `src/grins_platform/tests/unit/test_invoice_service.py`, `tests/integration/test_invoice_integration.py`.
- `src/grins_platform/tests/unit/test_payment_warning_service_agreement.py` — service-agreement edge case.
- `src/grins_platform/tests/unit/test_subscription_management.py` — Stripe customer creation/lookup pattern.

### Frontend files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

- `frontend/src/features/schedule/components/PaymentCollector.tsx` (entire file, 447 lines) — **MAJOR REWRITE.** Delete the entire `tap_to_pay` `path` branch (lines ~71–360 of the file: `handleTapToPay`, the `tap_to_pay` view, the receipt sub-flow). Replace the "Pay with Card (Tap to Pay)" button with a "Take Card Payment via Stripe app" instructions card showing the invoice number prominently with a copy button. Keep the "Record Other Payment" manual path entirely intact.
- `frontend/src/features/schedule/api/stripeTerminalApi.ts` — keep file but mark deprecated with a header comment (matching the backend deprecation note). Stop importing it from `PaymentCollector.tsx`.
- `frontend/src/features/schedule/components/AppointmentModal/PaymentSheetWrapper.tsx` — no change to the wrapper itself; just hosts the simplified `PaymentCollector`.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 117–123, 515–533, 651–666) — the modal state and `openSheetExclusive('payment')` flow stays. Add a "Paid — $X via Stripe on {date}" read-only pill that displays *instead of* the Collect Payment CTA when the appointment's linked invoice is `PAID`. **Also verify** the modal already hides the Collect Payment CTA for service-agreement-covered jobs; if not, add that gate.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts` (lines 198–210) — `useCollectPayment` mutation. Add `invoiceKeys.all` and `customerInvoiceKeys.all` to the `onSuccess` invalidation list (cross-feature import, see "Patterns to follow" below).
- `frontend/src/features/invoices/components/PaymentDialog.tsx` (entire file, 289 lines) — manual payment recording. **Small change:** when user pastes a bare `pi_*` reference, auto-prepend `stripe_dashboard:`. Don't double-prepend.
- `frontend/src/features/invoices/components/InvoiceList.tsx` — add a "Channel" column or pill rendering based on `payment_reference` prefix (`stripe_dashboard:` → "Stripe (Dashboard app)", `stripe_terminal:` → "Stripe (Terminal)" — kept for forward compat — bare → manual). Existing 9-axis filter already supports payment-type filtering; no API change.
- `frontend/src/features/invoices/types/index.ts` (lines 8–17) — `InvoiceStatus` enum. **Add:** `'refunded'` and `'disputed'` (matching backend additions).
- `frontend/src/features/invoices/api/invoiceApi.ts` — add new methods: `listUnmatchedStripeCharges()`, `linkStripeCharge(stripe_event_id, invoice_id)`.
- `frontend/src/features/invoices/hooks/useInvoiceMutations.ts` — pattern for query-key invalidation; mirror for `useLinkStripeCharge`.
- `frontend/src/core/api/client.ts` (lines 8–119) — Axios instance. No change.

### Stripe documentation — READ THESE BEFORE IMPLEMENTING

> Validate every URL — Stripe revs docs frequently.

- **Webhooks intro & best practices:** https://docs.stripe.com/webhooks
  - Signature verification, idempotency by `event.id`, replay window, ordering.
- **Event types reference:** https://docs.stripe.com/api/events/types
  - `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
- **Idempotency:** https://docs.stripe.com/idempotency
- **Receipt configuration in Dashboard app:** https://docs.stripe.com/receipts
  - Stripe sends email receipts automatically when the Customer has `email`. Branding/sender are configured in Stripe Dashboard → Settings → Branding.
- **Stripe Dashboard mobile app overview:** https://stripe.com/dashboard
  - Reader pairing, customer search, charge with description, manual refunds.
- **Stripe Terminal M2 (for staff to set up reader pairing in the Stripe app):** https://docs.stripe.com/terminal/payments/setup-reader/stripe-m2
- **API versioning:** https://docs.stripe.com/api/versioning
  - Pinning `stripe.api_version` in code so events don't break under Stripe upgrades.
- **Disputes lifecycle:** https://docs.stripe.com/disputes/responding
- **Refunds API:** https://docs.stripe.com/refunds

### Patterns to follow (mirror these exactly)

**Backend service pattern (mirror `services/stripe_terminal.py` and `customer_service.py`):**

```python
from grins_platform.log_config import LoggerMixin, get_logger
logger = get_logger(__name__)

class FooError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

class FooService(LoggerMixin):
    DOMAIN = "payment"
    def __init__(self, deps...) -> None:
        super().__init__()
        ...
    def do_thing(self, ...) -> ...:
        self.log_started("do_thing", **safe_kwargs)
        try:
            ... stripe call ...
            self.log_completed("do_thing")
        except stripe.StripeError as e:
            self.log_failed("do_thing", error=e)
            raise FooError(str(e)) from e
```

**Webhook event handler pattern (mirror existing `_handle_invoice_paid` in `webhooks.py`):**

- Verify event type is in `HANDLED_EVENT_TYPES`.
- Check idempotency via `StripeWebhookEventRepository.get_by_stripe_event_id(event.id)` *before* doing any work.
- After processing, call `mark_processed(event.id)` to set `processing_status = "completed"`.
- On failure, set `processing_status = "failed"` with `error_message`, and **return 200 anyway** (Stripe should not retry our bugs forever — log and alert).
- Use `LoggerMixin.log_*` methods; do not `print` or `logger.info` directly.
- Defensive double-layer idempotency: even if the webhook event is "new," check the *invoice's* current state before mutating (e.g., do not mark already-paid invoice paid again).

**FastAPI endpoint pattern (mirror `api/v1/invoices.py`):**

```python
@router.post(
    "/path",
    response_model=Resp,
    status_code=status.HTTP_200_OK,
)
async def handler(
    data: Req,
    _current_user: AdminUser,  # auth dependency
    service: Annotated[Svc, Depends(get_svc)],
) -> Resp:
    try:
        return service.do_thing(...)
    except FooError as e:
        raise HTTPException(status_code=..., detail=...) from e
```

**Frontend mutation pattern (mirror `useInvoiceMutations.ts`):**

```ts
return useMutation({
  mutationFn: ({ id, data }) => api.doThing(id, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: invoiceKeys.all });
    queryClient.invalidateQueries({ queryKey: customerInvoiceKeys.all });
    queryClient.invalidateQueries({ queryKey: appointmentKeys.all });
  },
});
```

**Cross-feature query-key import:** before adding `invoiceKeys` import in `useAppointmentMutations.ts`, check repo lint config; if there's a feature-boundary rule, lift the keys to `shared/` first.

**Memory-aware safety guards (DO NOT bypass — mandatory):**
- Per memory `feedback_email_test_inbox.md`: any email send in dev/staging must enforce a code-level allowlist. Only `kirillrakitinsecond@gmail.com` may receive real email. **However, in this plan we do not add a Grin's-side receipt send — Stripe handles receipts.** If you ever break that rule and add a custom send, you must implement the allowlist.
- Per memory `feedback_sms_test_number.md`: same for SMS — only `+19527373312` in dev. Not relevant unless SMS receipts are added (out of scope).
- Per memory `project_dev_stripe_price_mismatch.md` (Apr 15 incident): when running the webhook flow against dev Stripe, double-check `STRIPE_SECRET_KEY` is the test key and the webhook signing secret matches the test endpoint, not live.
- Per memory `project_estimate_email_portal_wired.md`: the email service is no longer a stub (Resend is live). This means *if* a future iteration wants Grin's-side branded card-payment receipts, the channel exists — but we are deliberately NOT using it here to avoid double receipts.

---

## IMPLEMENTATION PLAN

### Phase 0 — Stripe account & ops setup (no code; ~1 day elapsed)

**Tasks:**

- **Confirm Stripe account state:**
  - Account in good standing, US-based merchant, MCC code accepted (irrigation/field services typically fine — verify in Settings → Business).
  - Tap to Pay (for the *Stripe app side*, so phone-NFC works there) is enabled in Settings → Terminal. Geographic eligibility: US ✅.
  - Test mode and live mode keys both configured. **Per memory, double-check dev `.env` has the test key.**

- **Stripe webhook subscription (the critical change):**
  - In Stripe Dashboard → Developers → Webhooks → the existing Grin's endpoint (`https://<env>/api/v1/webhooks/stripe`):
    - Add events: `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
    - Keep existing events: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `invoice.upcoming`, `customer.subscription.updated`, `customer.subscription.deleted`.
    - Confirm signing secret matches the value of `STRIPE_WEBHOOK_SECRET` in each env. If a new endpoint is registered, rotate the secret in env vars and restart.

- **Receipt configuration:**
  - Stripe Dashboard → Settings → Branding: confirm logo, primary color, business name, support email/phone are set. These appear on auto-sent receipts.
  - Stripe Dashboard → Settings → Customer emails: confirm "Successful payments" toggle is ON. This is what makes Stripe email a receipt automatically when `customer.email` is set.

- **Stripe Dashboard mobile app rollout:**
  - For each tech who will collect payments, create a Stripe team member account (Settings → Team) with the **"Reader" or "Mobile reader" role** (whichever Stripe currently calls the limited POS role) — *not* full admin access.
  - Each tech: install the Stripe Dashboard app on their phone, log in, accept any Tap-to-Pay terms-of-service prompts.
  - Each tech who will use the M2: pair the M2 inside the Stripe app (Bluetooth pairing wizard inside the app under Settings → Readers).

- **Staff training (short doc):**
  - Write a one-page tech-facing instruction sheet:
    1. Open Grin's web app, navigate to the appointment, note the invoice number (`INV-YYYY-NNNN`).
    2. Switch to Stripe Dashboard app → Payments → New charge.
    3. Search for the customer (by name or email; falls back to "Add new customer" — but explicitly: pick existing customer if present so reconciliation works).
    4. Enter amount.
    5. **In the description field, type the invoice number exactly as shown in Grin's** (e.g., `INV-2026-0042`). Optionally add a memo.
    6. Tap "Charge" → tap card on M2 (or on phone if using Tap to Pay).
    7. Done. Switch back to Grin's; the invoice will mark itself paid within seconds.

- **Validate end-to-end against test mode:**
  - Use Stripe's test cards in the Dashboard app (test mode toggle in app).
  - Confirm a test charge with `description: "INV-2026-0042"` triggers the webhook in dev → Grin's marks the invoice paid.

- **Disable tipping at the Stripe account level:**
  - Stripe Dashboard → Settings → Tipping. Confirm OFF.
  - Validate by attempting a test charge in the Stripe app and verifying no tip prompt appears. If a tip slips through, the resulting amount mismatch will land in the unmatched queue — operational alarm, not a feature gap.

- **CG-16 — Custom receipt sender domain:**
  - Stripe Dashboard → Settings → Emails → "Public details" or "Sending email." Set sender to `payments@grins-irrigation.com` (or the chosen domain).
  - Add DKIM/SPF DNS records (Stripe provides the values). Coordinate with whoever runs the Grin's DNS.
  - **Validate:** trigger a test charge; confirm receipt arrives from the new sender, not `noreply@stripe.com`.

- **CG-17 — Restrict Stripe team-member permissions for techs:**
  - Stripe Dashboard → Settings → Team → Roles. Verify whether the granular permission "Create customer" can be disabled for the limited POS role.
  - **If yes:** disable for tech role. Techs can still search and select existing Stripe customers, but cannot create new ones — closing the customer-fallback failure mode.
  - **If no:** rely on training. Add explicit instruction in the tech 1-pager: "NEVER tap 'Add new customer' inside the Stripe app — always select an existing one. If the customer doesn't exist in Stripe, stop and contact admin." Add a weekly admin spot-check (Stripe customers created in the last 7 days with no `metadata.grins_customer_id`).

### Phase 1 — Customer linkage hardening (~1 day)

**Tasks:**

- **Verify `Customer.stripe_customer_id` (already exists at `models/customer.py:111`).** No migration needed. Just confirm it's nullable, indexed for lookup.
- **Add a unique partial index on `stripe_customer_id`** (Alembic migration) so duplicate Stripe customer IDs can't accidentally bind to two Grin's customers. Partial index because the field is nullable.
- **Implement `CustomerService.get_or_create_stripe_customer(customer_id) -> str`** (new public method). Idempotent: if `customer.stripe_customer_id` is set, return it. Otherwise, call `stripe.Customer.create(name, email, phone, metadata={"grins_customer_id": str(customer_id)})`, persist the returned ID, and return it. On Stripe error, raise a typed exception.
- **Backfill script:** `scripts/backfill_stripe_customers.py` that paginates through all `customers` and calls the helper. Idempotent (skip those already linked). Logs results. Safe to run multiple times.
- **Auto-create on customer create/update:** add a post-write hook in `CustomerService.create_customer` and `update_customer` that calls `get_or_create_stripe_customer` *non-blockingly* (best-effort; if Stripe is down, log and continue — we'll catch up via backfill).

- **CG-3 — Lead-vs-Customer policy enforcement:**
  - **Recommended for v1: block card-payment UI for Lead-only appointments.** In `AppointmentModal.tsx`, if the appointment's job has `lead_id` set but no `customer_id`, replace the Collect Payment CTA with "Convert lead to customer first to take card payment." Existing convert-lead flow handles the conversion.
  - Backend safety net: in the webhook handler, if description-match resolves to an invoice whose `customer_id IS NULL` or matches a `Lead` only, defer to unmatched and log `payment_intent.lead_only_invoice`.

- **CG-18 — `service_agreement.stripe_customer_id` ↔ `customer.stripe_customer_id` coordination:**
  - **Audit query** (one-shot): `SELECT sa.id, sa.stripe_customer_id AS sa_stripe, c.stripe_customer_id AS c_stripe FROM service_agreements sa JOIN customers c ON sa.customer_id = c.id WHERE sa.stripe_customer_id IS NOT NULL AND c.stripe_customer_id IS NOT NULL AND sa.stripe_customer_id != c.stripe_customer_id;`
  - If any rows return: investigate (probably a backfill artifact). Reconcile to `customer.stripe_customer_id` as source of truth.
  - **Add invariant:** in `ServiceAgreementService.create_or_update`, if `customer.stripe_customer_id` is set, force `service_agreement.stripe_customer_id` to match. Add a test asserting this.
  - **Long-term cleanup (out of scope):** consider removing the redundant column on `service_agreements` and joining to `customers` for the Stripe ID.

### Phase 2 — Webhook hardening (the spine; ~3–4 days)

**Tasks:**

- **Pin Stripe API version** (currently unpinned in the codebase — confirmed by grep):
  - In `services/stripe_config.py` add `stripe_api_version: str = "2024-11-20.acacia"` (or current latest).
  - In every place that sets `stripe.api_key`, also set `stripe.api_version`.
  - Justification: we don't want unannounced event-shape changes to break our handlers.

- **Add InvoiceStatus enum values:**
  - `models/enums.py`: add `REFUNDED = "refunded"` and `DISPUTED = "disputed"` to `InvoiceStatus`.
  - Frontend `features/invoices/types/index.ts`: matching string literal additions.
  - Frontend `InvoiceList`: render the new statuses with appropriate colors.

- **Create `unmatched_stripe_charges` model + migration:**
  - Table fields: `id` (UUID PK), `stripe_event_id` (FK → `stripe_webhook_events.stripe_event_id`, unique), `payment_intent_id` (string, indexed), `stripe_customer_id` (string, nullable, indexed), `amount_cents` (int), `currency` (string), `description` (text, nullable), `created_at` (datetime UTC), `resolved_at` (datetime, nullable, indexed `WHERE resolved_at IS NULL`), `resolved_invoice_id` (UUID FK → invoices, nullable), `resolved_by_user_id` (UUID FK → staff, nullable).
  - Add `models/unmatched_stripe_charge.py`, `repositories/unmatched_stripe_charge_repository.py`, `schemas/unmatched_stripe_charge.py`.

- **Extend `HANDLED_EVENT_TYPES`** in `api/v1/webhooks.py`:
  ```python
  HANDLED_EVENT_TYPES = frozenset({
      # existing
      "checkout.session.completed",
      "invoice.paid",
      "invoice.payment_failed",
      "invoice.upcoming",
      "customer.subscription.updated",
      "customer.subscription.deleted",
      # NEW
      "payment_intent.succeeded",
      "payment_intent.payment_failed",
      "payment_intent.canceled",
      "charge.refunded",
      "charge.dispute.created",
  })
  ```

- **Implement `_handle_payment_intent_succeeded(event, session)`:**
  - Read `event.data.object`: `id`, `description`, `customer`, `amount`, `amount_received`, `currency`, `created`, `metadata`, **`invoice`** (for CG-7 short-circuit).
  - **CG-7 short-circuit (subscription overlap):** if `event.data.object.invoice` is non-null, this PaymentIntent belongs to a Stripe-side Invoice — already handled by `_handle_invoice_paid`. **Return immediately**, log structured info `payment_intent.subscription_intent_skipped` with the Stripe Invoice ID. Do NOT insert into `unmatched_stripe_charges` (would create duplicate work for admins).
  - **Match strategy 1 — explicit metadata** (forward compat with future Architecture A): if `metadata.invoice_id` is present, use that. Skip strategy 2 and 3.
  - **Match strategy 2 — description regex:** `re.search(r"\bINV-\d{4}-\d{4}\b", description or "")`. If match, look up `Invoice` by `invoice_number == match.group(0)`. Validate amount matches `total_amount` (cents-vs-cents) within tolerance of zero. **CG-10:** if invoice is already in `PARTIAL` state and the charged amount + existing `paid_amount` ≤ `total_amount`, treat this as a second deposit/installment — call `record_payment` with the new amount; service handles status transition.
  - **Match strategy 3 — customer + amount fallback:** if no description match and `customer` is present: find Grin's customer by `stripe_customer_id == event.customer`. Find unpaid AND `PARTIAL`-with-remaining-balance-equal-to-amount invoices for that customer with matching cents. If exactly one candidate → match. If zero or multiple → defer to unmatched.
  - **CG-3 safety net:** if matched invoice's `customer_id` resolves to a `Lead`-only record (no Customer), defer to unmatched with reason `lead_only_invoice` and log loudly.
  - **CG-8 cancelled-while-pending:** if matched invoice's `status == CANCELLED`, **do NOT mark paid.** Insert into `unmatched_stripe_charges` with reason `invoice_cancelled`, log at WARNING level (admin action required: refund the customer manually in Stripe Dashboard). The handler still returns 200 — Stripe must not retry our business-logic decision.
  - **On match (and not-cancelled):** mark invoice paid via `InvoiceService.record_payment(invoice_id, PaymentRecord(amount=Decimal(amount_received)/100, payment_method=PaymentMethod.CREDIT_CARD, payment_reference=f"stripe_dashboard:{intent.id}"))`. Set `Job.payment_collected_on_site = True`.
  - **CG-14 audit trail (effort-gated):** read `event.data.object.metadata.created_by_stripe_user_id` if present (Stripe app may expose it; verify with a real test charge); if non-null, persist on a new `Invoice.collected_by_stripe_user_id` column. **If Stripe app does not expose this field:** defer column add to v2; log the gap as `audit.stripe_user_id_unavailable` so we can bring it back if Stripe adds it.
  - **On no-match:** insert into `unmatched_stripe_charges` (linked to the `stripe_webhook_event_id`), log structured warning `payment_intent.unmatched` with reason. Do NOT raise — webhook still returns 200.
  - **Idempotency double-layer:** even if the webhook event is fresh, check `Invoice.status` — if already PAID, no-op (log `payment_intent.invoice_already_paid`).
  - **Currency check:** if `currency != "usd"`, log error and defer to unmatched (out of scope).

- **Implement `_handle_payment_intent_payment_failed(event, session)`:**
  - Log only. Do NOT mutate invoice status — Stripe will retry, and the staff member is in the field; they'll see the failure in the Stripe app and try again.
  - Optional: add a row to a new `payment_attempts` log table for ops visibility (defer; `event_data` JSONB on `stripe_webhook_events` already captures the payload).

- **Implement `_handle_payment_intent_canceled(event, session)`:**
  - If we previously linked this payment_intent to an invoice (via `payment_reference` lookup): only act if invoice is still PAID and the cancellation amount matches; in that rare case, revert to OVERDUE/SENT and log loudly. Otherwise no-op + log.

- **Implement `_handle_charge_refunded(event, session)`:**
  - Read `event.data.object`: `payment_intent`, `amount_refunded`, `amount`, `refunded` (bool).
  - Look up invoice by `payment_reference == f"stripe_dashboard:{payment_intent_id}"`.
  - **Full refund** (`amount_refunded == amount`): set `Invoice.status = REFUNDED`, persist refund metadata in `notes` or new fields. Set `Job.payment_collected_on_site = False` (so completion warnings re-fire).
  - **Partial refund** (`amount_refunded < amount`): set `Invoice.status = PARTIAL` (or new `PARTIALLY_REFUNDED` enum if you want it explicit; defer for now and use PARTIAL with notes annotation). Update `paid_amount` accordingly.
  - Idempotent: if invoice already in REFUNDED, no-op.

- **Implement `_handle_charge_dispute_created(event, session)`:**
  - Read `event.data.object`: `payment_intent`, `amount`, `reason`, `status`, `due_by` (timestamp).
  - Look up invoice by `payment_reference`. If found: set `Invoice.status = DISPUTED`, append a `notes` line with the reason and due-by date. Do NOT change `paid_amount` (the funds aren't reversed yet — that comes via `charge.dispute.funds_withdrawn` later, out of scope for v1).
  - **Critical:** also alert admin via the existing notification queue (or just log loudly with `WARNING` level — admin checks logs/Slack). A dispute is time-sensitive (Stripe deadline ~7 days) and silent failure is bad.

- **Audit trail:**
  - Every successful invoice-status mutation from a webhook should call into `InvoiceService.record_payment` (which already logs via `LoggerMixin`). For status changes that don't go through `record_payment` (refund, dispute), add structured logs `invoice.status.refunded` / `invoice.status.disputed` with `invoice_id`, `stripe_event_id`, `amount`.

- **Tests** (extend `tests/unit/test_stripe_webhook.py`):
  - `test_payment_intent_succeeded_with_description_match` — happy path.
  - `test_payment_intent_succeeded_with_metadata_match_takes_precedence` — forward compat.
  - `test_payment_intent_succeeded_with_customer_amount_fallback` — single-match success.
  - `test_payment_intent_succeeded_customer_fallback_multiple_candidates_defers` — defers to unmatched.
  - `test_payment_intent_succeeded_no_match_creates_unmatched_row`.
  - `test_payment_intent_succeeded_invoice_already_paid_is_noop`.
  - `test_payment_intent_succeeded_amount_mismatch_defers`.
  - `test_payment_intent_succeeded_currency_not_usd_defers`.
  - `test_payment_intent_succeeded_idempotent_replay` — same event id processed twice → second is no-op.
  - `test_payment_intent_payment_failed_logs_only`.
  - `test_payment_intent_canceled_logs_only_or_reverts_paid`.
  - `test_charge_refunded_full_marks_refunded`.
  - `test_charge_refunded_partial_updates_paid_amount`.
  - `test_charge_refunded_idempotent`.
  - `test_charge_dispute_created_marks_disputed_and_alerts`.

### Phase 3 — Frontend rewire (~2–3 days)

**Tasks:**

- **CG-5 — Ensure invoice exists before showing instructions:**
  - Before `PaymentCollector` renders the instructions card with the invoice number, the parent flow must guarantee an invoice exists for this appointment.
  - **Approach:** in `PaymentSheetWrapper.tsx` (or in `PaymentCollector`'s `useEffect` on mount), call `POST /appointments/{id}/create-invoice` (idempotent — the existing endpoint already creates-or-returns the invoice; verify in `services/appointment_service.py:1326+`). Show a loading skeleton until the invoice number is back. Only then render the instructions card.
  - **CG-3 gate:** if the appointment has no `customer_id` (Lead-only), do not call create-invoice — instead render "Convert lead to customer first to take card payment" with a link to the convert flow.
  - **GOTCHA:** if the existing endpoint is not idempotent (creates a duplicate invoice on every call), wrap the call in a getter pattern: `appointmentApi.getInvoice(id)` first, fall back to create. Verify behavior before merging.

- **CG-6 — Pending-payment polling UI:**
  - When `PaymentCollector` is showing the instructions card and the invoice is `SENT` (i.e., not yet paid), start a TanStack Query poll on the invoice every 4 seconds.
  - Show a small subtle indicator below the instructions: "Waiting for Stripe payment… (auto-refreshing)" with a spinner.
  - When the invoice flips to `PAID` / `REFUNDED` / `DISPUTED`, the polling auto-stops (TanStack Query's `refetchInterval` returns `false` based on status), the modal re-renders, and the `<PaidStatePill />` (Phase 3 step on AppointmentModal) replaces the instructions.
  - **Stop polling when:** modal closes, status terminal, user manually clicks "Cancel — record manually instead." Tear down on unmount.
  - **GOTCHA:** don't over-poll. 4–5s is a sweet spot; <2s wastes resources and triggers Stripe webhook delivery jitter; >10s feels broken.

- **`PaymentCollector.tsx` major rewrite:**
  - Delete `import { stripeTerminalApi } from '../api/stripeTerminalApi'`.
  - Delete the `path === 'tap_to_pay'` state, `handleTapToPay`, `handleSendReceipt`, all associated state (`tapStep`, `tapError`).
  - Replace the "Pay with Card (Tap to Pay)" button in the `path === 'choose'` view with a clear instructions card. Layout:
    ```
    ┌─ Take Card Payment ────────────────────────┐
    │ Charge this invoice in the Stripe app:     │
    │                                            │
    │ Invoice #: INV-2026-0042   [📋 Copy]       │
    │ Amount:    $350.00                         │
    │                                            │
    │ 1. Open Stripe Dashboard app               │
    │ 2. New charge → search customer            │
    │ 3. Enter $350.00                           │
    │ 4. Type INV-2026-0042 in description       │
    │ 5. Tap card on M2 or phone NFC             │
    │                                            │
    │ Invoice will mark paid within seconds.     │
    └────────────────────────────────────────────┘
    ```
  - Keep "Record Other Payment" button untouched.
  - Add a useState polling hook (or rely on existing TanStack Query refetch) so the modal reflects the paid state once the webhook fires. Existing refresh button should already work if invalidations are right (Phase 3 step on `useAppointmentMutations`).

- **`useAppointmentMutations.ts`:**
  - In `useCollectPayment.onSuccess`, add `queryClient.invalidateQueries({ queryKey: invoiceKeys.all })` and `customerInvoiceKeys.all`. (Even though webhook updates won't go through `useCollectPayment`, the manual "Record Other Payment" path does, and consistent invalidations matter.)
  - More importantly: TanStack Query's `staleTime` for invoices needs to be short enough that the modal re-fetches when user re-focuses the tab after using Stripe app. Verify and tune. Or wire an explicit polling on the appointment-detail query while a "pending payment" state is active.

- **`AppointmentModal.tsx`:**
  - Add a `<PaidStatePill />` that renders when the linked invoice is `PAID` (or `REFUNDED`/`DISPUTED` for those states).
  - Hide the "Take Card Payment" instructions when invoice is already paid.
  - **Service-agreement guard:** if `appointment.job.service_agreement_id` is non-null AND the agreement is active, hide the Collect Payment CTA entirely and show "Covered by service agreement — no payment needed" instead. (Verify if this guard is already in place via `test_payment_warning_service_agreement.py`-style logic; if not, add it. Cross-reference `feature-developments/smoothing-out-after-update2/smoothing-out-after-update2.md` Section 17 for the design intent.)

- **`PaymentDialog.tsx`:**
  - Reference field: on submit (or onChange), if value matches `^pi_[A-Za-z0-9]+$`, prepend `stripe_dashboard:`. Don't double-prepend an already-prefixed value.
  - Add helper text under the reference field: "Paste the Stripe charge ID (`pi_...`) — we'll auto-prefix it."

- **`InvoiceList.tsx`:**
  - Add a "Channel" pill column (or add to existing payment_method column) that derives from `payment_reference` prefix:
    - `stripe_dashboard:*` → "Stripe app" pill (purple, with Stripe icon)
    - `stripe_terminal:*` → "Stripe Terminal" pill (kept for forward compat)
    - **CG-15 legacy:** `payment_method == 'stripe'` (legacy enum) with bare reference → "Stripe (legacy)" pill, neutral grey. **No data migration** — historical rows render as-is.
    - bare → method label (Cash/Check/etc.)
  - 9-axis filter already supports payment-type filtering. No API change.

- **CG-13 — Verify and document Invoice search by `pi_*`:**
  - Verify the existing 9-axis filter on `payment_reference` supports substring/contains match. Look in `services/invoice_service.py:list_invoices` and `repositories/invoice_repository.py:list_invoices` for the `payment_reference` filter clause.
  - If only exact-match: add `ILIKE %{q}%` substring support so admins can paste `pi_3OXxxx` and find the invoice.
  - **Validate:** add a test asserting search by `pi_3OXxxx` finds an invoice with `payment_reference = "stripe_dashboard:pi_3OXxxx_..."`.

- **Channel-aware sorting/grouping:** optional, skip for v1.

- **Stripe app deep-link (optional, nice-to-have):** in the instructions card, add "Open Stripe app" button that uses `stripepayments://` URL scheme (works on iOS) or `intent://` (Android). Not all phones honor; defer if it adds risk.

### Phase 4 — Admin reconciliation surface (~3–4 days)

**Tasks:**

- **Backend endpoints:**
  - `GET /api/v1/invoices/unmatched-stripe-charges` (AdminUser) — paginated list, default sort by `created_at DESC`. Filters: `resolved` (boolean). Returns rows with derived `customer_name`, `customer_email` if `stripe_customer_id` resolves to a Grin's customer.
  - `POST /api/v1/invoices/unmatched-stripe-charges/{stripe_event_id}/link` (AdminUser). Body: `{invoice_id: UUID}`. Server-side flow:
    1. Verify the unmatched row exists and is unresolved.
    2. Verify the invoice exists and is unpaid (or matches the charge).
    3. Call `InvoiceService.record_payment(invoice_id, PaymentRecord(amount=..., payment_method=CREDIT_CARD, payment_reference=f"stripe_dashboard:{payment_intent_id}"))`.
    4. Update the unmatched row: `resolved_at = now`, `resolved_invoice_id`, `resolved_by_user_id`.
    5. Set `Job.payment_collected_on_site = True`.
  - `POST /api/v1/invoices/unmatched-stripe-charges/{stripe_event_id}/dismiss` (AdminUser). Body: `{reason: str}`. Marks unmatched row as `resolved_at = now` with `resolved_invoice_id = NULL` (not a match — admin discarded).

- **Frontend page `UnmatchedCharges.tsx` under route `/invoices/unmatched-stripe-charges`:**
  - Admin-only (use existing `AdminUser` route guard).
  - Table columns: created_at (relative), Stripe charge ID (link to Stripe Dashboard via `https://dashboard.stripe.com/test/payments/{pi_id}` for test, `/payments/{pi_id}` for live — use env to flip), customer name (resolved or "Unlinked"), amount, description (truncated), age, action button.
  - Action button → modal with searchable invoice picker (pre-filter to that customer's open invoices if customer matched). Submit → calls `/link` endpoint.
  - "Dismiss" secondary action with reason field.
  - Empty state: "No unmatched charges. 🎉"

- **Notification surface:**
  - When a new unmatched row is inserted (by webhook handler), enqueue a notification for admins. Reuse existing notification path if any; otherwise just rely on email/log + admins checking the page periodically. Defer to ops decision.

- **CG-9 — "Split charge across invoices" admin action:**
  - On the unmatched-charge detail modal, add a "Split across multiple invoices" mode in addition to the single-invoice link.
  - UI: list of invoice rows with editable amount fields per row. Sum-equals-charge-amount validation. Submit calls a new endpoint `POST /unmatched-stripe-charges/{stripe_event_id}/split` with body `{allocations: [{invoice_id, amount_cents}, ...]}`.
  - Server-side: validate sum, then call `InvoiceService.record_payment` per allocation with `payment_reference = f"stripe_dashboard:{pi_xxx}#alloc_{n}"` (suffix to disambiguate the same Stripe charge across multiple invoices in `payment_reference` searches). Update the unmatched row to `resolved_at = now` with `resolved_invoice_id = null` and a JSONB `allocations` array recorded.
  - **GOTCHA:** sum tolerance is zero — must match cents exactly.
  - **Defer to v2 if scope is tight:** v1 admins can split manually by creating multiple invoice records. Document the workaround in the runbook.

- **CG-12 — Notifications for growing unmatched queue:**
  - **Inline alert on insert:** in the webhook handler, after inserting a new unmatched row, count current unresolved rows. If count crosses thresholds (e.g., 5 → INFO log, 10 → WARNING log, 25 → ERROR log + structured alert event `unmatched_stripe_charges.threshold_exceeded`).
  - **Daily digest:** APScheduler job at 8am local time runs a query for unresolved unmatched rows and emails the result to admins. Reuse `_send_email` (Resend is now wired per memory). Apply the dev/staging email allowlist guard. Empty state: skip the email.
  - **Runbook:** describe what each threshold means and what action to take.

- **CG-11 — Cleanup policy for stale unmatched rows:**
  - APScheduler job runs nightly: archive (or hard-delete after audit period) `unmatched_stripe_charges` rows where `resolved_at IS NOT NULL AND resolved_at < now() - interval '90 days'`. Keep the underlying `stripe_webhook_events` row (that's our long-term audit trail).
  - Unresolved rows older than 30 days raise a separate ops alert — they shouldn't exist; either resolve or dismiss them.

### Phase 5 — Documentation, runbook, training (~1 day)

**Tasks:**

- Write an internal runbook (~1 page) at `docs/payments-runbook.md` covering:
  - How to add/remove a tech to the Stripe team account.
  - How to pair the M2 in the Stripe app.
  - What to do when a charge doesn't auto-match (admin reconciliation flow).
  - What to do for refunds (always initiate from Stripe Dashboard or app, NOT from Grin's UI).
  - What to do for disputes (Stripe deadline; respond from Stripe Dashboard).
  - Webhook-secret rotation procedure.
  - How to test new event types in dev (Stripe CLI `stripe trigger payment_intent.succeeded --add payment_intent:metadata.invoice_id=test`).
  - **CG-19 — Receipt resend:** when a customer says they didn't get a receipt, the office goes to Stripe Dashboard → Payments → click the charge → "Resend receipt" (with optional updated email). **No Grin's-side action.** No code involved. Document this so techs/office don't try to "fix it" in Grin's.
  - **Tipping/tax reminder:** tipping is disabled at the Stripe account level and sales tax is not handled by this feature. If a tech somehow adds either via the Stripe app, the charge will fail amount-match and land in the unmatched queue.
  - **CG-17 spot-check:** weekly admin task — run `stripe.Customer.list(limit=100, expand=['data.metadata'])` and verify every customer created in the last 7 days has `metadata.grins_customer_id`. Any without indicate a tech tapped "Add new customer" — investigate and reconcile.
  - **CG-11 monitoring threshold:** investigate when unresolved unmatched count > 10 or any row is > 7 days old.
- Write the tech-facing 1-pager from Phase 0 → bundle with the wider staff onboarding.
- Update `README.md` payments section: replace any in-app Tap-to-Pay references with the new two-app workflow.
- Mark `services/stripe_terminal.py` and `api/v1/stripe_terminal.py` deprecated with a module-level docstring pointing to this plan and the future Capacitor consideration.

### Phase 6 — Field validation & rollout (~1 week elapsed, mostly waiting)

- Test mode end-to-end with one tech and one test card on the M2.
- Deploy to staging, run live mode dry-run with a small real charge (refund immediately for cleanup).
- Roll out to production.
- Monitor `unmatched_stripe_charges` daily for the first 2 weeks; tune training if rate is high.

---

## STEP-BY-STEP TASKS

> Execute top to bottom. Each task is atomic and independently testable.

### Phase 0 ops

#### 0.1 Verify and update Stripe webhook subscription
- **IMPLEMENT:** add 5 new event types in Stripe Dashboard webhook settings.
- **VALIDATE:** in Stripe Dashboard, confirm "Events to send" lists all 11 events (6 existing + 5 new).

#### 0.2 Confirm receipt branding + auto-send toggle
- **IMPLEMENT:** Stripe Dashboard → Settings → Branding + Customer emails.
- **VALIDATE:** trigger a $0.50 test charge against a customer with email; confirm receipt email arrives.

#### 0.3 Create Stripe team accounts for staff who will collect
- **IMPLEMENT:** add team members with limited POS role.
- **VALIDATE:** each member can log in to Stripe Dashboard mobile app.

### Phase 1 — Customer linkage

#### 1.1 ADD partial unique index on `customers.stripe_customer_id`
- **IMPLEMENT:** Alembic migration creating `CREATE UNIQUE INDEX ix_customers_stripe_customer_id_unique ON customers(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL`.
- **PATTERN:** existing migrations under `src/grins_platform/migrations/versions/`.
- **GOTCHA:** if any duplicates exist, the migration will fail. Run a dedupe SELECT first.
- **VALIDATE:** `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.

#### 1.2 ADD `CustomerService.get_or_create_stripe_customer(customer_id) -> str`
- **IMPLEMENT:** check `customer.stripe_customer_id`; if null, call `stripe.Customer.create(name, email, phone, metadata={"grins_customer_id": str(customer_id)})`, persist, return.
- **PATTERN:** existing `customer_service.py` Stripe call style around lines 1445–1610.
- **IMPORTS:** `import stripe`.
- **GOTCHA:** Stripe customer fields max lengths — name 256, email 512, phone 50.
- **GOTCHA:** if `email` is null, Stripe doesn't auto-send receipts for charges against this customer. That's fine — just don't expect a receipt for those.
- **VALIDATE:** `uv run pytest src/grins_platform/tests/unit/test_customer_service.py -v -k stripe_customer`.

#### 1.3 CREATE `scripts/backfill_stripe_customers.py`
- **IMPLEMENT:** paginate `customers`, call `get_or_create_stripe_customer` for each, log progress, idempotent (skip already-linked).
- **PATTERN:** existing scripts under `scripts/`.
- **GOTCHA:** Stripe rate limit is 100 req/sec read, 100 req/sec write — sleep between batches. Use Stripe's idempotency key.
- **VALIDATE:** `uv run python scripts/backfill_stripe_customers.py --dry-run` then real run; confirm no duplicate Stripe customers created.

#### 1.4 ADD post-write hook in `CustomerService.create_customer` and `update_customer`
- **IMPLEMENT:** after the customer is persisted, call `get_or_create_stripe_customer` best-effort (catch + log Stripe errors, don't fail the user-facing operation).
- **PATTERN:** existing post-write hooks (search for `_after_create` style).
- **VALIDATE:** add `test_customer_create_links_stripe_customer` to existing customer-service tests.

### Phase 2 — Webhook hardening

#### 2.1 ADD Stripe API version pinning
- **IMPLEMENT:** in `services/stripe_config.py`, add `stripe_api_version: str = Field(default="2024-11-20.acacia")`. In every place that sets `stripe.api_key`, also set `stripe.api_version = settings.stripe_api_version`.
- **PATTERN:** existing `stripe.api_key = self.stripe_settings.stripe_secret_key` lines in `services/stripe_terminal.py` and `services/customer_service.py`.
- **GOTCHA:** verify the version string matches a real Stripe API version at the time of merge — pin to the latest stable.
- **VALIDATE:** new test asserts `stripe.api_version` is set after service init.

#### 2.2 ADD `InvoiceStatus.REFUNDED` and `DISPUTED`
- **IMPLEMENT:** `models/enums.py` — add the two values. Frontend `features/invoices/types/index.ts` — matching string literal additions.
- **PATTERN:** existing enum entries.
- **GOTCHA:** any switch/case on `InvoiceStatus` (in services, schemas, tests, frontend renderers) must be re-checked. Use `grep` first.
- **VALIDATE:** `uv run pytest src/grins_platform/tests -k invoice_status`; `cd frontend && npm run typecheck`.

#### 2.3 CREATE `models/unmatched_stripe_charge.py`
- **IMPLEMENT:** model class with fields per Phase 2 design (id, stripe_event_id FK, payment_intent_id, stripe_customer_id, amount_cents, currency, description, created_at, resolved_at, resolved_invoice_id FK, resolved_by_user_id FK).
- **PATTERN:** mirror `models/stripe_webhook_event.py`.
- **IMPORTS:** standard SQLAlchemy.
- **VALIDATE:** import the model in a Python shell without errors.

#### 2.4 CREATE Alembic migration for `unmatched_stripe_charges`
- **IMPLEMENT:** `uv run alembic revision --autogenerate -m "add_unmatched_stripe_charges_table"` and review the generated migration. Add `WHERE resolved_at IS NULL` partial index on `resolved_at`.
- **VALIDATE:** `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.

#### 2.5 CREATE `repositories/unmatched_stripe_charge_repository.py`
- **IMPLEMENT:** `create()`, `get_by_stripe_event_id()`, `list_unresolved(page, page_size)`, `mark_resolved(stripe_event_id, invoice_id, user_id)`, `mark_dismissed(stripe_event_id, user_id, reason)`.
- **PATTERN:** mirror `repositories/stripe_webhook_event_repository.py`.
- **VALIDATE:** unit tests for each method.

#### 2.6 CREATE `schemas/unmatched_stripe_charge.py`
- **IMPLEMENT:** `UnmatchedStripeChargeResponse`, `LinkChargeRequest`, `DismissChargeRequest`, `PaginatedUnmatchedStripeCharges`.
- **PATTERN:** mirror `schemas/invoice.py`.

#### 2.7 EXTEND `HANDLED_EVENT_TYPES` in `api/v1/webhooks.py`
- **IMPLEMENT:** add 5 new event-type strings to the frozenset.
- **VALIDATE:** `uv run pytest src/grins_platform/tests/unit/test_stripe_webhook.py::test_unhandled_event_returns_204` (or equivalent — confirm new types are now accepted).

#### 2.8 IMPLEMENT `_handle_payment_intent_succeeded(event, session)`
- **IMPLEMENT:** the three-strategy match (metadata → description regex → customer+amount). Use `InvoiceService.record_payment` for the actual write. Insert into `unmatched_stripe_charges` on no-match. Idempotent against already-paid invoices.
- **PATTERN:** mirror the existing `_handle_invoice_paid` style.
- **IMPORTS:** `import re`, `from datetime import datetime, UTC`, `InvoiceRepository`, `CustomerRepository`, `JobRepository`, `UnmatchedStripeChargeRepository`, `InvoiceService`, `PaymentRecord`, `PaymentMethod`.
- **GOTCHA:** anchor regex `\bINV-\d{4}-\d{4}\b`. Convert `event.data.object.amount_received` (int cents) to `Decimal` before comparing to `Invoice.total_amount`.
- **GOTCHA:** strict UTC: `datetime.fromtimestamp(event.created, tz=UTC)`.
- **GOTCHA:** when calling `InvoiceService.record_payment`, the existing service already updates `Invoice.status` (PAID or PARTIAL based on amount). Don't bypass it.
- **VALIDATE:** the unit tests listed in Phase 2 above.

#### 2.9 IMPLEMENT `_handle_payment_intent_payment_failed`
- **IMPLEMENT:** structured log only. No invoice mutation.
- **VALIDATE:** unit test.

#### 2.10 IMPLEMENT `_handle_payment_intent_canceled`
- **IMPLEMENT:** look up by `payment_reference`; if linked invoice is paid AND amount matches, revert to OVERDUE/SENT and log loudly. Otherwise no-op.
- **VALIDATE:** unit tests for both branches.

#### 2.11 IMPLEMENT `_handle_charge_refunded`
- **IMPLEMENT:** look up invoice by `payment_reference`; full refund → REFUNDED + `Job.payment_collected_on_site = False`; partial refund → adjust `paid_amount`, mark PARTIAL with notes annotation. Idempotent.
- **VALIDATE:** unit tests for full and partial.

#### 2.12 IMPLEMENT `_handle_charge_dispute_created`
- **IMPLEMENT:** mark invoice DISPUTED, append notes, log WARNING. (Future: enqueue admin notification.)
- **VALIDATE:** unit test.

#### 2.13 ROUTE new event types in the webhook handler
- **IMPLEMENT:** in `webhooks.py` after signature verification + idempotency check, add a dispatch dict mapping event type → handler. Avoid long if/elif chain.
- **VALIDATE:** integration test with a fixture for each event type.

### Phase 3 — Frontend rewire

#### 3.1 REWRITE `PaymentCollector.tsx`
- **IMPLEMENT:** delete `tap_to_pay` path, `handleTapToPay`, `handleSendReceipt`, `tapStep`, `tapError`. Replace top-of-component rendering for `path === 'choose'` with the instructions card. Add `[Copy]` button that calls `navigator.clipboard.writeText(invoiceNumber)` with toast confirmation.
- **PATTERN:** existing toast usage with `sonner`.
- **GOTCHA:** preserve all `data-testid` attributes that existing tests rely on. Update or replace tests as needed.
- **VALIDATE:** `cd frontend && npm test PaymentCollector`. Add test for clipboard-copy behavior with mocked `navigator.clipboard`.

#### 3.2 REMOVE import of `stripeTerminalApi` in `PaymentCollector.tsx`; mark `stripeTerminalApi.ts` deprecated
- **IMPLEMENT:** add header comment to `stripeTerminalApi.ts`: "DEPRECATED — see `.agents/plans/stripe-tap-to-pay-and-invoicing.md`. Kept for possible future Capacitor wrapper."
- **VALIDATE:** TypeScript still compiles.

#### 3.3 ADD `<PaidStatePill />` rendering in `AppointmentModal.tsx`
- **IMPLEMENT:** when the appointment's linked invoice is `PAID`, `REFUNDED`, or `DISPUTED`, render a pill instead of the Collect Payment CTA. Show: amount, channel ("Stripe app"), date.
- **PATTERN:** existing pill / badge components.
- **VALIDATE:** snapshot test.

#### 3.4 ADD service-agreement guard in `AppointmentModal.tsx`
- **IMPLEMENT:** when `appointment.job.service_agreement_id` is set AND active, hide the Collect Payment CTA, show "Covered by service agreement — no payment needed."
- **GOTCHA:** verify if this is already in code somewhere — search for `service_agreement_id` in frontend. If yes, no change needed. If no, add it here.
- **VALIDATE:** snapshot test for the covered case.

#### 3.5 UPDATE `useCollectPayment` invalidations in `useAppointmentMutations.ts`
- **IMPLEMENT:** add `invoiceKeys.all` and `customerInvoiceKeys.all` to `onSuccess` invalidation set.
- **GOTCHA:** cross-feature import; if lint forbids, lift keys to `shared/`.
- **VALIDATE:** existing mutation test asserts both new keys are invalidated.

#### 3.6 UPDATE `PaymentDialog.tsx` reference auto-prefix
- **IMPLEMENT:** if reference value matches `^pi_[A-Za-z0-9]+$`, prepend `stripe_dashboard:` on submit.
- **VALIDATE:** unit test.

#### 3.7 UPDATE `InvoiceList.tsx` channel pill
- **IMPLEMENT:** add a derived "channel" field from `payment_reference` prefix; render as colored pill in the row.
- **VALIDATE:** snapshot test for each channel value.

### Phase 4 — Admin reconciliation

#### 4.1 ADD `services/unmatched_stripe_charge_service.py`
- **IMPLEMENT:** `list_unresolved`, `link_to_invoice`, `dismiss`. Use `InvoiceService.record_payment` from inside `link_to_invoice`.
- **PATTERN:** mirror `services/invoice_service.py`.
- **VALIDATE:** unit tests.

#### 4.2 ADD endpoints in `api/v1/invoices.py` (or new `api/v1/unmatched_stripe_charges.py`)
- **IMPLEMENT:** `GET /unmatched-stripe-charges`, `POST .../{id}/link`, `POST .../{id}/dismiss`. AdminUser auth.
- **PATTERN:** existing invoice endpoints.
- **VALIDATE:** `uv run pytest -k unmatched_stripe`.

#### 4.3 CREATE `frontend/src/features/invoices/pages/UnmatchedCharges.tsx`
- **IMPLEMENT:** table, link modal, dismiss modal, search invoice picker, Stripe Dashboard deep link, empty state.
- **PATTERN:** existing list pages under `features/invoices/`.
- **VALIDATE:** vitest + manual.

#### 4.4 ADD route under `/invoices/unmatched-stripe-charges` (AdminUser guard)
- **IMPLEMENT:** add route in `core/router/`.
- **VALIDATE:** non-admin users get 403/redirect.

#### 4.5 ADD `useUnmatchedCharges`, `useLinkStripeCharge`, `useDismissStripeCharge` hooks
- **IMPLEMENT:** TanStack Query hooks with proper invalidation (invalidate unmatched list AND invoice detail/list on link).
- **VALIDATE:** vitest mutation tests.

### Phase 5 — Docs

#### 5.1 WRITE `docs/payments-runbook.md` (~200 lines)
#### 5.2 WRITE tech-facing 1-pager (Markdown or PDF)
#### 5.3 UPDATE `README.md` payments section
#### 5.4 ADD deprecation comments on `stripe_terminal.py` and `api/v1/stripe_terminal.py`

### Phase 6 — Validation

#### 6.1 STRIPE CLI dev test for each new event type
- `stripe trigger payment_intent.succeeded --override payment_intent:description="INV-2026-0001"`
- repeat for each event type with appropriate overrides.

#### 6.2 STAGING dry-run
- Real $0.50 charge against a test invoice; confirm reconciliation; refund.

#### 6.3 PRODUCTION soft launch
- 1-week monitoring of `unmatched_stripe_charges` rate and matching accuracy.

---

## EDGE CASES & DEFENSIVE BEHAVIORS

Comprehensive list. Each must be tested or explicitly accepted as "best-effort."

1. **Tech types invoice number with typo** (`INV-2026-004` instead of `INV-2026-0042`) → no description match → customer+amount fallback may save it → if not, lands in unmatched-charges queue.
2. **Tech types invoice number for a different customer's invoice** → description matches but amount/customer mismatch → flagged for review (don't auto-mark wrong customer's invoice paid). Add a strict mode: if description-matched invoice's `customer_id != stripe_customer_id`'s linked Grin's customer, defer to unmatched and log loudly.
3. **Tech doesn't enter description at all** → description-match fails → customer-fallback runs → if exactly one matching unpaid invoice for that Stripe customer with matching amount, link; else unmatched.
4. **Charge for amount that doesn't match any invoice** → customer-fallback finds zero candidates → unmatched.
5. **Multiple invoices for same customer + amount** → ambiguous → unmatched (not auto-linked).
6. **One charge intended to cover multiple invoices** ($1000 covering 3 invoices for $300/$400/$300) → unmatched (out of scope; admin manually links to one invoice and creates separate journal entries, OR splits the charge in Stripe).
7. **Webhook arrives for a charge that has no Stripe customer** (tech used "Quick charge" flow) → description-only match path; if no match, unmatched.
8. **Webhook arrives BEFORE the corresponding invoice exists in Grin's** (race: tech charges a customer for whom no invoice was generated yet) → no match → unmatched. Admin reconciles after creating the invoice.
9. **Same `pi_*` arrives twice via webhook replay** → idempotency table catches it; second is no-op.
10. **`payment_intent.succeeded` arrives, then later `charge.refunded` for the same intent** → invoice marked PAID then later REFUNDED. Both handlers idempotent.
11. **Invoice already manually marked paid via `PaymentDialog` (with the same `pi_*` reference)** → webhook arrives later → handler sees status PAID, no-ops. Logs `payment_intent.invoice_already_paid`. Good — this is the dual-write race protection.
12. **Service-agreement-covered job** → frontend doesn't show CTA → no charge happens → no edge case at backend level (but if a tech *does* charge anyway — maybe an extra service — the webhook just lands in unmatched since the job's invoice has `total_amount = 0`).
13. **Currency mismatch** (charge is EUR/CAD/etc.) → log + unmatched. Out of scope for v1.
14. **Stripe API outage during webhook processing** → handler should not retry inline; webhook signature is already verified. If Stripe is down, the invoice mutation still succeeds (we don't call Stripe again to mark paid). But `Customer.create` calls (in unrelated paths) would fail; covered by best-effort hook.
15. **Webhook secret rotation in mid-flight** → existing webhooks will fail signature verification. Documented in runbook: rotate, restart backend, then update Stripe Dashboard.
16. **Tech charges via Tap to Pay on iPhone** (in the Stripe app, no M2 needed) → reconciliation flow is identical. Stripe app abstracts away whether it was M2 or phone NFC.
17. **Customer requests refund before webhook arrives** → admin processes refund in Stripe Dashboard. `charge.refunded` arrives. If `payment_intent.succeeded` already arrived: invoice goes PAID → REFUNDED. If hasn't arrived: handler can't find invoice; logs and we defer until invoice exists. This is rare but log it.
18. **Tech charges, then realizes wrong customer, voids** → `payment_intent.canceled` arrives. Handler looks up invoice by `payment_reference`; usually no link exists yet (we haven't yet linked); no-op.
19. **Disputed charge** → `charge.dispute.created` arrives → invoice DISPUTED + admin alerted. Stripe handles the dispute response in Dashboard (out of scope to surface in Grin's UI; admin uses Stripe Dashboard directly).
20. **Late dispute won → funds restored to merchant** → `charge.dispute.closed` event (NOT in the initial `HANDLED_EVENT_TYPES`; out of scope for v1, captured as a future enhancement).
21. **Multiple admins try to link the same unmatched charge simultaneously** → DB unique constraint on `unmatched_stripe_charges.resolved_invoice_id` (or pessimistic lock in service). First commits; second sees `resolved_at IS NOT NULL` and shows error.
22. **`stripe_dashboard:` prefix collision with old data** → double-prefixing protection in `PaymentDialog.tsx`. Backwards-compat with old PARTIAL/PAID rows that have bare `pi_*` references — keep those readable; just don't auto-prefix re-entered values.
23. **Stripe rate limit during backfill** → script handles 429 with exponential backoff. Use Stripe's `Idempotency-Key` per customer to make retries safe.
24. **Stripe API version drift** — pinned via `stripe.api_version` in code. Migration of pinned version becomes a deliberate, tested upgrade.
25. **Webhook delivery delay** (rare but Stripe SLA is best-effort) → tech sees stale "unpaid" state in modal. Mitigation: short refetch interval on appointment-detail query when payment is pending; Refresh button is also wired.
26. **Subscription renewal fires both `invoice.paid` and `payment_intent.succeeded`** (CG-7). New handler short-circuits when `event.data.object.invoice` is set. Test: simulate a Stripe Customer subscription cycle in dev; assert only one handler mutates state, the other logs `subscription_intent_skipped`.
27. **Stray tip or tax added in the Stripe app** (out of scope but possible if a tech bypasses guidance). Charge amount > invoice amount → unmatched with reason `amount_mismatch`. Operational fix only — admin reconciles or refunds. No code path.
28. **Lead-only invoice** (CG-3). Description matches an invoice on a Lead-only job → defer to unmatched with reason `lead_only_invoice`. Test: simulated event against an invoice whose job has `lead_id` but no `customer_id`.
29. **Cancelled invoice mid-flight** (CG-8). Description matches a CANCELLED invoice → handler refuses, inserts into unmatched with reason `invoice_cancelled`, logs WARNING. Admin must refund manually in Stripe.
30. **Discount / undercharge** (CG-4). Tech charges $300 against a $350 invoice. Description matches but amount mismatches → unmatched. Recommended workflow: tech updates invoice in Grin's first. Test asserts undercharge is NOT auto-linked.
31. **Two-payment / installment invoice** (CG-10). First charge $175 against $350 invoice → invoice goes PARTIAL. Second charge $175 with same invoice number in description → matcher recognizes PARTIAL+balance match, calls `record_payment` again, invoice becomes PAID. Test both charges.
32. **Charge created via Stripe API or Payment Link, not the Stripe Dashboard app** → same `payment_intent.succeeded` event shape, same handler. Description match still applies if the link was generated with description set; otherwise customer-fallback. Documented in runbook.
33. **Stripe `customer.email` differs from Grin's `Customer.email`** → Stripe sends receipts to the email on the Stripe Customer record. If the office updates email in Grin's, the post-write hook (Phase 1) updates the Stripe customer. Verify this propagation in test.
34. **Customer with no email AND no phone** → Stripe doesn't auto-send receipt (no destination). Acceptable; tech can manually send a paper/SMS confirmation. Don't surface as an error.
36. **Refund of an unmatched charge** → `charge.refunded` event arrives for a `payment_intent` whose invoice was never linked. Handler tries `payment_reference` lookup → finds nothing. Should also check `unmatched_stripe_charges` table; if found, mark that row as `refunded_at` (new column? or use `dismissed_at` semantically) and log. Otherwise log and ignore.

---

## TESTING STRATEGY

### Backend unit tests (`uv run pytest src/grins_platform/tests/unit/`)
- All new webhook handlers: happy path, idempotency, no-match, multi-match, currency mismatch, amount mismatch, service-agreement guard interaction, refund full/partial, dispute.
- `CustomerService.get_or_create_stripe_customer`: idempotent, creates only when needed, persists ID, error path.
- `UnmatchedStripeChargeService` and repository methods.
- New endpoints: auth (AdminUser only), pagination, link/dismiss flows.
- `InvoiceStatus.REFUNDED` and `DISPUTED` rendering / persistence.

### Backend integration tests (`tests/integration/`)
- Full flow: simulate `payment_intent.succeeded` webhook → invoice goes PAID, `Job.payment_collected_on_site = True`, audit log entry created.
- Refund flow: paid invoice → `charge.refunded` → invoice REFUNDED + job flag flipped.
- Dispute flow.
- Race: webhook arrives twice (idempotency); webhook arrives before/after manual `record_payment`.
- Backfill script: integration test with seeded customers.

### Frontend unit tests (`cd frontend && npm test`)
- `PaymentCollector` new instructions card render, copy-button behavior, no remaining references to `stripeTerminalApi`.
- `AppointmentModal` paid-state pill rendering for PAID/REFUNDED/DISPUTED; service-agreement guard.
- `PaymentDialog` reference-prefix normalization.
- `InvoiceList` channel pill derivation.
- `UnmatchedCharges` page render, link modal flow, dismiss flow.
- Mutation hooks invalidate the correct query keys.

### End-to-end manual validation (Stripe test mode)
1. Create test invoice in Grin's: `INV-TEST-0001` for $1.00 against a customer whose Stripe customer is created.
2. Open Stripe Dashboard test mode → New charge → search customer → enter $1.00 → description: `INV-TEST-0001` → tap test card on M2 (or simulated reader).
3. Observe webhook fires → invoice marks PAID within 5 seconds → "Paid" pill appears in appointment modal → Stripe sends test-mode receipt email.
4. Refund the charge from Stripe Dashboard → invoice transitions to REFUNDED.
5. Repeat with no description → fallback path matches → invoice PAID.
6. Repeat with bad description → unmatched_stripe_charges row appears → admin links it via `/invoices/unmatched-stripe-charges` page.
7. Repeat with disputed test card → `charge.dispute.created` → invoice DISPUTED, admin alert logged.

### Stripe CLI test commands
- `stripe trigger payment_intent.succeeded`
- `stripe trigger charge.refunded`
- `stripe trigger charge.dispute.created`
- For description override: `stripe payment_intents create --amount=100 --currency=usd --confirm --payment-method=pm_card_visa --description="INV-2026-0042"` then trigger webhook from the resulting event.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
uv run ruff check src/grins_platform/api/v1/webhooks.py src/grins_platform/services/customer_service.py src/grins_platform/models/enums.py src/grins_platform/models/unmatched_stripe_charge.py
uv run ruff format src/grins_platform/api/v1/webhooks.py src/grins_platform/services/customer_service.py
uv run mypy src/grins_platform/
cd frontend && npm run lint && npm run typecheck
```

### Level 2: Unit tests
```bash
uv run pytest src/grins_platform/tests/unit/test_stripe_webhook.py src/grins_platform/tests/unit/test_customer_service.py src/grins_platform/tests/unit/test_invoice_service.py src/grins_platform/tests/unit/test_unmatched_stripe_charges.py -v
cd frontend && npm test PaymentCollector PaymentDialog AppointmentModal InvoiceList UnmatchedCharges useAppointmentMutations
```

### Level 3: Integration tests
```bash
uv run pytest src/grins_platform/tests/integration/test_invoice_integration.py src/grins_platform/tests/integration/test_combined_status_flow_integration.py src/grins_platform/tests/integration/test_stripe_dashboard_reconciliation_integration.py -v
```

### Level 4: Manual validation (Stripe CLI + dev server)
```bash
# In one terminal
uv run uvicorn grins_platform.app:app --reload --port 8000

# In another terminal — stripe-cli forwarding webhooks
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
# copy the whsec_... it prints into .env STRIPE_WEBHOOK_SECRET, restart backend

# In another terminal — Vite
cd frontend && npm run dev

# Trigger a test event
stripe trigger payment_intent.succeeded
# Observe backend logs + frontend
```

### Level 5: Stripe MCP spot checks
- `mcp__stripe__list_payment_intents` — confirm test-mode account state.
- `mcp__stripe__list_invoices` — N/A (we're using Stripe charges directly, not Stripe invoices).
- `mcp__stripe__list_refunds` — verify refund event triggers our handler.

---

## ACCEPTANCE CRITERIA

- [ ] Phase 0 ops complete: 5 new webhook events subscribed, receipt branding configured, Stripe team accounts provisioned, M2 paired with each tech's Stripe app.
- [ ] All Grin's customers (existing + future) have a `stripe_customer_id` populated.
- [ ] Stripe API version pinned in code; tested against the pinned version.
- [ ] `InvoiceStatus.REFUNDED` and `DISPUTED` shipped end-to-end (backend + frontend rendering).
- [ ] `unmatched_stripe_charges` table live; admin page reachable at `/invoices/unmatched-stripe-charges`.
- [ ] Webhook handler processes all 5 new event types idempotently.
- [ ] End-to-end flow demonstrated in test mode: charge in Stripe app w/ description → invoice PAID in Grin's within 5s; refund → REFUNDED; dispute → DISPUTED.
- [ ] No code in `PaymentCollector.tsx` references `stripeTerminalApi` or attempts `discoverReaders`. Old paths replaced with the instructions card.
- [ ] Service-agreement-covered jobs hide the Collect Payment CTA.
- [ ] `PaymentDialog.tsx` auto-prefixes bare `pi_*` references.
- [ ] `InvoiceList.tsx` shows channel pills.
- [ ] All listed validation commands pass green.
- [ ] No bypass of dev SMS/email allowlist guards.
- [ ] Runbook + tech-facing 1-pager merged and shared with staff.
- [ ] Soft launch: ≥7 days production observation with <10% unmatched rate.

### Critical-gap acceptance items (added from red-team review)

- [ ] Tipping disabled at the Stripe account level (verified by test charge with no tip prompt). Sales tax explicitly out of scope and not present in any Stripe app charge flow.
- [ ] **CG-3** Lead-only appointments do NOT show Collect Payment CTA; backend handler defers Lead-only invoice matches to unmatched.
- [ ] **CG-4** decision recorded; tech 1-pager addresses on-the-fly discount workflow.
- [ ] **CG-5** "Take Card Payment" creates-or-fetches invoice before showing the instructions card with the invoice number.
- [ ] **CG-6** Pending-payment polling indicator shipped; auto-collapses on PAID/REFUNDED/DISPUTED.
- [ ] **CG-7** `_handle_payment_intent_succeeded` short-circuits when `event.data.object.invoice` is set (subscription overlap protection); test asserts no duplicate processing.
- [ ] **CG-8** Cancelled-invoice race: handler refuses to mark CANCELLED invoices paid; inserts into unmatched with reason `invoice_cancelled`; alert raised.
- [ ] **CG-9** "Split charge across invoices" admin action working OR documented as v2 with manual workaround in runbook.
- [ ] **CG-10** Two-payment/installment flow tested: first deposit transitions invoice to PARTIAL; second charge against same invoice transitions to PAID.
- [ ] **CG-11** Cleanup job archives resolved unmatched rows >90 days; alert raised when unresolved >30 days old.
- [ ] **CG-12** Daily 8am unmatched digest email running; threshold log alerts firing at 5/10/25 unresolved.
- [ ] **CG-13** Searching by `pi_*` in Invoices tab returns the correct invoice.
- [ ] **CG-14** Tech audit trail: either `Invoice.collected_by_stripe_user_id` populated, OR a logged note that Stripe app does not expose this field (deferred to v2).
- [ ] **CG-15** `InvoiceList` renders legacy `PaymentMethod.STRIPE` rows as "Stripe (legacy)" pill; no historical migration.
- [ ] **CG-16** Receipt sender domain is the Grin's domain (verified by triggering a test charge and inspecting the From header).
- [ ] **CG-17** Stripe role for techs has customer-create disabled (or weekly admin spot-check process documented).
- [ ] **CG-18** Audit query confirms no divergence between `customer.stripe_customer_id` and `service_agreement.stripe_customer_id`; invariant added to `ServiceAgreementService`.
- [ ] **CG-19** Receipt-resend procedure documented in runbook; tech 1-pager redirects "didn't get receipt" requests to office.

---

## COMPLETION CHECKLIST

- [ ] Phase 0 ops complete and documented.
- [ ] Phase 1: customer-linkage migration + helper + backfill script run in dev/staging.
- [ ] Phase 2: all webhook handlers + tests merged with passing CI.
- [ ] Phase 3: `PaymentCollector` rewrite + AppointmentModal pill + PaymentDialog tweak + InvoiceList pill merged.
- [ ] Phase 4: admin reconciliation page live, end-to-end exercised.
- [ ] Phase 5: runbook + 1-pager + README updated; deprecation notes on `stripe_terminal.py`.
- [ ] Phase 6: staging dry-run + production soft launch with monitoring.
- [ ] No TypeScript or MyPy errors.
- [ ] Memory updated: replace prior in-app TTP memory (if any) with "Stripe payments live via Stripe Dashboard app + webhook reconciliation; M2 hardware paired in tech-side Stripe app, not in Grin's." Add a new project memory for this milestone.

---

## OPERATIONAL RUNBOOK (excerpt — full file at `docs/payments-runbook.md`)

### Monitoring
- **Daily**: review `/invoices/unmatched-stripe-charges` for new entries. Goal: ≤10% of charges land here. If >10%, refresh tech training on description format.
- **Weekly**: spot-check 5 random PAID invoices against Stripe Dashboard charges to confirm amount + customer alignment.
- **On-call alerts**: any `charge.dispute.created` should page admin (Stripe deadline ~7 days to respond).

### Rotating Stripe webhook secret
1. Stripe Dashboard → Developers → Webhooks → Endpoint → "Roll secret."
2. Copy new secret. Update `STRIPE_WEBHOOK_SECRET` in Railway env.
3. Restart backend service.
4. Test trigger an event from Stripe CLI; confirm 200 response.

### Adding a new tech
1. Stripe Dashboard → Settings → Team → Invite member → assign limited POS role.
2. Tech accepts invite, installs Stripe Dashboard app, logs in, accepts TTP terms.
3. Tech pairs the M2 (or company-issued M2) inside the Stripe app.
4. Onboard with the tech-facing 1-pager.

### Refunds and disputes
- **All refunds initiated from Stripe Dashboard** (admin or tech with appropriate role). Grin's webhook reconciles automatically.
- **Disputes**: respond inside Stripe Dashboard. Update Grin's invoice notes manually if needed. Stripe deadline is hard.

### Webhook secret + API version drift
- Pin Stripe API version explicitly in code via `stripe.api_version`. Bumping is a deliberate PR with regression tests.
- When Stripe deprecates a version, follow their migration guide; test against new version in staging before rolling to prod.

---

## NOTES

### Why this is the right shape (not a stopgap)

- **Zero new SDKs, zero new app stores, zero hardware purchases.** The user's existing M2 works; the existing webapp works; phone-NFC Tap to Pay works (via the Stripe app, not via our app).
- **Stripe is the source of truth for charges.** That's a healthy architectural property — we don't try to be a payments processor; we react to Stripe events.
- **Reconciliation is robust by design.** Three-strategy match + admin queue means typos are recoverable.
- **Forward-compat with future Architecture A.** If you ever build the Capacitor wrapper and want in-app charging, the same webhook handler accepts the new events with `metadata.invoice_id` set — no rewrite.

### Trade-offs we're accepting

- **Two-app workflow for techs.** ~30 seconds extra per payment. Mitigated by good tech training and the description-match auto-link.
- **Description format discipline** required from techs. Customer+amount fallback is the safety net; admin reconciliation is the second safety net.
- **No native receipt branding from Grin's.** Stripe receipts are good enough.
- **No in-app card capture flow.** Acknowledged out-of-scope. Future Capacitor wrapper revisits this.

### Future considerations (not in this PR)

- **Capacitor wrapper** — if the two-app dance becomes painful, a ~2-week investment would let us reuse the deprecated `stripe_terminal.py` service for in-app charges with both M2 and phone NFC. The webhook handler stays unchanged; it just starts seeing PaymentIntents created with `metadata.invoice_id` instead of relying on description match.
- **3% surcharge** (Obsidian Note 08) — surfaces in receipt and invoice.
- **`charge.dispute.closed` and `charge.dispute.funds_withdrawn`** events for full dispute lifecycle.
- **Multi-invoice charge splitting** — admin UI to split one Stripe charge across multiple Grin's invoices.
- **SMS receipts** (separate from Stripe's email receipts) — would use the existing CallRail SMS path with allowlist guard.
- **Custom receipt branding** via Resend — possible now that the email service is no longer a stub. Currently deliberately avoided to prevent double-receipts.
- **Removing `stripe_terminal.py` and `api/v1/stripe_terminal.py`** — separate cleanup PR; gated on confirmation that no Capacitor work is upcoming.

### Confidence

- **Plan accuracy:** **9.5/10** — verified against actual source for every file reference; Stripe behavior verified against official docs; existing patterns mirror exactly.
- **One-pass implementation success:** **8/10** — the only real unknowns are (a) exact line locations within the 1000-line `webhooks.py` for inserting new handlers (manageable — just read first), (b) cross-feature query-key import convention (resolvable in 5 min), (c) whether `Customer.update_customer` already has a post-write hook spot or needs one (minor).
- **Operational success after rollout:** **8/10** — depends on tech compliance with description-format. The customer+amount fallback and admin reconciliation queue make this recoverable, not catastrophic.
