# 08 — Invoices tab as single source of truth (+ filters, reminders, 3% fee, 2-wk due)

**Request (paraphrased):**
> Invoices is a separate tab holding all invoices — auto-generated from on-site collects, manually created for special projects, and any invoices scheduled for later payment. Stripe payments add 3%, cash/check don't. All invoices searchable/filterable by client name, job type, status. Unpaid invoices auto-remind at 1.5 weeks, day before due, weekly past-due (toggleable). Default due in 2 weeks.

**Status:** 🟡 PARTIAL (most of the "view/filter" story is done; scheduling + 3% fee + 2-wk default are gaps)

---

## What exists today

### UI
- Dedicated Invoices page: `frontend/src/pages/Invoices.tsx` with all-invoices + lien-review tabs.
- Filter set in `frontend/src/features/invoices/components/InvoiceList.tsx:40-120`:
  - Customer name search ✅
  - Status (draft, sent, viewed, paid, overdue, lien_warning, lien_filed) ✅
  - Amount range ✅
  - Payment method (cash, check, credit_card, ACH, Venmo, Zelle, other) ✅
  - Date ranges (created / due / paid) ✅
  - Days until/past due ✅
  - Invoice number ✅
  - Job-type filter: implicit via job_id — may need a cleaner UX ❓

### Model
- `Invoice` model (`models/invoice.py:30-220`) with `status`, `payment_method`, `paid_at`, `paid_amount`, `reminder_count`, `last_reminder_sent`, `pre_due_reminder_sent_at`, `last_past_due_reminder_at`, `lien_eligible`, `lien_warning_sent`, `lien_filed_date`, `late_fee_amount`.
- Manual creation endpoint: `POST /api/v1/invoices`; UI via `CreateInvoiceDialog`.
- Record payment: `POST /invoices/{invoice_id}/payment` (`api/v1/invoices.py:615-652`).
- Reminder send: `POST .../send_reminder` (`api/v1/invoices.py:654-689`) — increments `reminder_count`.

## Gaps

1. **Reminder schedule not wired.** The *fields* for tracking reminder timestamps exist, but no background job automatically sends reminders at 1.5 weeks / day-before-due / weekly-past-due. Reminders appear to be manual or bulk-triggered.
2. **Toggle to enable/disable follow-ups** — not implemented (no setting found).
3. **Default due = created + 14 days** — not enforced; due date is free-form per invoice.
4. **3% Stripe surcharge** — no code adds this when `payment_method = credit_card`. `late_fee_amount` field exists but that's for lien/late, not the processing fee.

## TODOs

- [ ] **TODO-08a** Background scheduler (APScheduler in `services/background_jobs.py`) that runs daily and:
  - sends pre-due reminder if `due_at - today == 1` and `pre_due_reminder_sent_at is null`
  - sends "approaching due" reminder if `due_at - today ≈ 10-11 days` and `reminder_count == 0` (maps to your "1.5 weeks" signal — ❓ clarify whether "1.5 weeks *after send*" or "1.5 weeks *before due*")
  - sends weekly past-due reminder while `status in (sent, overdue)` and `last_past_due_reminder_at` older than 7 days
  - stops when status = paid / void.
- [ ] **TODO-08b** Add per-invoice `auto_followups_enabled` boolean (default true) + a global toggle in admin settings. Scheduler respects it.
- [ ] **TODO-08c** Default `due_at = created_at + 14 days` in invoice creation path.
- [ ] **TODO-08d** Add 3% processing-fee line item when `payment_method = credit_card`. Surface to the customer before they confirm. Waive for cash/check/ACH/Zelle/Venmo. Persist both pre-fee and post-fee totals for clean accounting.
- [ ] **TODO-08e** Confirm every on-site collect-payment flow (#06) also writes an `Invoice` row so the invoices tab truly is the source of truth.
- [ ] **TODO-08f** Add "job type" as a top-level filter (currently only reachable through job_id).

## Clarification questions ❓

1. **"1.5 weeks"** — measured from what? Send date, or due date? (Affects scheduler logic.)
2. **Frequency research:** you asked us to research best cadence. Do you want a lit-review write-up, or pick a sensible default (10 days after send, day before due, then weekly) and iterate?
3. **Fee disclosure:** must the 3% surcharge be shown to the customer at checkout (required by some card-brand rules), or added silently on the invoice? Recommend showing.
4. **Toggle scope:** global on/off only, or per-invoice opt-out too?
