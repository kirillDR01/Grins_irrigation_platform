# 06 — On-site payment collection from appointment modal

**Request (paraphrased):**
> Staff at the job should collect payments via check, cash, or Stripe credit-card scanner. Cash/check payments should record the amount + method right on that customer/job. Credit card automatically records as Stripe-paid. Reduces the need for separate invoices — we'd only send an invoice in edge cases.

**Status:** 🟡 PARTIAL

---

## What exists today

- "Collect Payment" button in `AppointmentModal.tsx` (teal outline, approx lines 265-290).
- `PaymentCollector.tsx` (`frontend/src/features/schedule/components/PaymentCollector.tsx:1-80`) — frontend payment UI.
- Backend Stripe Terminal integration: `src/grins_platform/services/stripe_terminal.py` — `create_payment_intent()` and `create_connection_token()` methods.
- Supported recorded payment methods include: cash, check, credit card (Stripe), ACH, Venmo, Zelle (via invoice `payment_method` varchar).
- `Job.payment_collected_on_site` boolean flag (`models/job.py:152`) marks on-site-paid jobs.

## Gaps

1. **Amount + method note on the appointment/customer:** `Job.payment_collected_on_site` is just a bool. Actual amount + method + free-text note likely live on the `Invoice` record, not the appointment itself. Whether the customer timeline / appointment modal surfaces those details needs confirmation. ❓
2. **Stripe Terminal hardware readiness:** Code to create payment intents for Terminal exists; on-device reader provisioning, reader selection in UI, and receipt flow have not been verified end-to-end.

## TODOs

- [ ] **TODO-06a** Verify cash/check collection persists amount + note against the appointment or customer timeline — not only as an invoice.
- [ ] **TODO-06b** Surface the recorded on-site payment (method + amount + date) directly in the appointment modal so staff/admin can see "paid $X by check on-site" without drilling into invoices.
- [ ] **TODO-06c** Confirm Stripe Terminal reader is provisioned on-device and the tap-to-pay flow is end-to-end tested. (Out of scope for pure code audit — field test needed.)
- [ ] **TODO-06d** Decide whether every on-site payment still generates an `Invoice` row (so invoicing tab stays source-of-truth per #08) or only those paid later.

## Clarification questions ❓

1. **Invoice always?** If a tech collects $500 cash on site, do we still create an `Invoice` row marked paid, so it shows up in the invoices tab? (Recommended: yes — keeps #08 intact.)
2. **Receipt delivery:** on a cash/check/Stripe-terminal payment, should the customer automatically receive a receipt SMS/email?
3. **Reader model:** which Stripe Terminal reader(s) are you standardizing on (BBPOS WisePOS, Tap to Pay on iPhone, etc.)? This affects the client setup.
