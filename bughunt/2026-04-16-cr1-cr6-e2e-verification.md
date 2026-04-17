# CR-1..CR-6 live-dev E2E verification — 2026-04-16

Deployments:
- **Backend:** Railway `Grins-dev` deployment `bc90a75f` (commit `5ecf3b7`, SUCCESS).
- **Frontend:** Vercel `grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` deployment `dpl_9nMBtAtWjyMktEnbV2Bgrbw4mn8W` (commit `5ecf3b7`, READY).

Base URLs:
- API: https://grins-dev-dev.up.railway.app
- FE:  https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app

Auth: admin / admin123. SMS safety: `SMS_TEST_PHONE_ALLOWLIST=+19527373312,+19528181020` is set on Grins-dev.

## Per-CR results

### CR-1 — `apply_schedule` creates DRAFT ✅ (BE live)

Created a test job for Kirill Rakitin + `POST /api/v1/schedule/apply` for `2027-01-15`.

```
created_appointment_ids: ["84b5db06-d76b-4e2c-a09f-a9f3c188ca50"]
appointment.status: draft
job.status:         to_be_scheduled
job.scheduled_at:   None
```

FE schedule page loaded (`cr1-schedule-page.png`). The `?date=YYYY-MM-DD` query param isn't honored by the current schedule page so the Jan 2027 DRAFT card wasn't visible in the default view; the BE invariant was the load-bearing assertion.

### CR-2 — `job_started` promotes SCHEDULED → IN_PROGRESS ✅ (BE live)

Created an appointment in DRAFT, transitioned to SCHEDULED via `PUT /api/v1/appointments/{id}`, then called `POST /api/v1/jobs/{id}/started`.

```
before: appt.status = scheduled,  job.status = to_be_scheduled
after:  appt.status = in_progress, job.status = in_progress
```

Before the fix the appointment would have stayed SCHEDULED while the job went IN_PROGRESS.

### CR-3 — Repeat C short-circuits ⚠ (partial — dev-env blocker)

`POST /api/v1/webhooks/callrail/inbound` accepted a signed (HMAC-SHA1 base64) payload with `content="C"` and returned `{"status":"processed"}` (200). Signature path and route entry verified.

Full end-to-end exercise of `_handle_cancel` requires correlating the inbound webhook to a `SentMessage` via `provider_thread_id`. On dev, `provider_thread_id` is null on every `sent_messages` row (0 / 20 recent `appointment_confirmation` rows have a thread_id populated). Without a correlating thread, the inbound webhook always falls into the `no_match` branch and never reaches `_handle_cancel`. This is a pre-existing dev-env issue unrelated to CR-3.

Unit + functional coverage (5 tests in `test_job_confirmation_service.py::TestRepeatCancelIsNoOp`, 1 in `test_yrc_confirmation_functional.py::test_two_consecutive_c_replies_send_exactly_one_sms`) covers the short-circuit behaviour directly.

### CR-4 — `invoice.paid` gated on `billing_reason` ⚠ (partial — side-effect safety)

`POST /api/v1/webhooks/stripe` accepted a signed (HMAC-SHA256, `t=…,v1=…`) `invoice.paid` payload with `billing_reason=subscription_update` and a bogus subscription ID, returning `{"status":"processed"}` (200). Signature path verified.

Exercising the three-branch logic against real Stripe subscription IDs would mutate real dev customer agreements (`last_payment_date`, `payment_status`, potentially `end_date`/`renewal_date`). Deferred. 14 unit tests in `test_webhook_handlers.py::TestInvoicePaid` cover all four `billing_reason` values plus the missing-reason backward-compat path.

### CR-5 — Lien Review Queue ✅ (full: BE + FE + SMS dispatch)

Seeded: test job + invoice (`amount=850.00`, `due_date=2025-12-01`, transitioned DRAFT → SENT). Then on the **live Vercel dev FE**:

1. Navigated to `/invoices?tab=lien-review`. Lien Review tab selected. Row rendered for Kirill Rakitin: `136 days past due`, `$850.00 owed`, `INV-2026-000002`. (`cr5-queue-with-row.png`)
2. Clicked **Send Notice**. Confirm dialog opened with "The recipient will receive an SMS at 9527373312 for invoice INV-2026-000002. This action is logged." (`cr5-confirm-dialog.png`)
3. Clicked **Confirm & send**. `POST /api/v1/invoices/lien-notices/{customer_id}/send` → 200. A `payment_reminder` SMS with `delivery_status=sent` landed in `sent_messages` at 20:50:48 to `+19527373312`. (`cr5-after-send.png`)
4. Clicked **Dismiss**. Row disappeared from the queue client-side (queue count → 0, empty state rendered).
5. `POST /api/v1/invoices/mass-notify {notification_type:"lien_eligible"}` → 400 with structured `detail.error="lien_eligible_deprecated"` + replacement-endpoint pointers.
6. Mass Notify dialog dropdown lists only "Past Due" and "Due Soon"; `lien_eligible` is absent. (`cr5-mass-notify-no-lien.png`, `cr5-lien-tab.png`)

### CR-6 — `convert_lead` Tier-1 dedup ✅ (full: BE + FE conflict modal)

Created test lead `CR6 BrowserE2E Lead` with phone `+19527373312` (duplicates the existing Kirill Rakitin customer). Transitioned `new → contacted → qualified`. Then on the **live Vercel dev FE**:

1. Navigated to `/leads/{id}`. "Convert to Customer" button visible (only shows on qualified leads).
2. Clicked Convert → `ConvertLeadDialog` opened with the pre-emptive "Possible match found" banner (from `useCheckDuplicate` hook). (`cr6-convert-dialog-warning.png`)
3. Clicked Convert in the dialog → API returned 409 → `<LeadConversionConflictModal>` opened with:
   - Title: "Possible duplicate customer"
   - Copy: "We already have a customer matching this lead's phone (9527373312) or email (cr6.browser.e2e@example.com). You can use the existing record or convert anyway."
   - Kirill Rakitin's record listed with "Use existing" button
   - Footer: **Cancel** + **Convert anyway** (`cr6-conflict-modal.png`)
4. Clicked Cancel. Dialog closed, no customer created.

Direct `POST /api/v1/leads/{id}/convert` without `force=true` returned 409 with structured detail `{error:"duplicate_found", lead_id, phone, email, duplicates:[Kirill Rakitin record]}`. `force=true` skipped on live dev because `customer_service.create_customer` has its own phone-uniqueness check that returns 400 before the dedup override lands — covered by unit + functional tests in `test_lead_api.py`, `test_lead_service.py`, `test_lead_operations_functional.py`.

## Real SMS dispatched during this pass

Two SMS, both to `+19527373312`:
1. `appointment_confirmation` at 20:47:22 (CR-3 setup; was intended to generate a `provider_thread_id` for inbound correlation, but dev doesn't persist them).
2. `payment_reminder` at 20:50:48 (CR-5 lien notice confirm+send).

No real emails were dispatched — `convert_lead` doesn't fire email on the paths exercised.

## Cleanup

All test resources deleted after verification:
- Lead `6c03bcce-e38c-41b4-add3-b2b658196878` (first CR-6 backend probe)
- Lead `44de4cba-69d5-4f48-ac48-a4dd90d87382` (CR-6 browser flow)
- Appointment `84b5db06-d76b-4e2c-a09f-a9f3c188ca50` (CR-1)
- Appointment `1d9306ba-230c-4d3c-a87b-80d584d74bb2`, Job `761066ba-…` (CR-2)
- Invoice `3ddc4dd8-ccd4-4d2e-9b4f-3a14072ce251`, Appointment `a3d7b406-…`, Job `a0703bbd-…` (CR-3/CR-5)

## Screenshots (e2e-screenshots/, gitignored)

- `cr1-schedule-page.png` — Schedule page rendering post-CR-1 merge.
- `cr5-lien-tab.png` — Lien Review tab (empty state, pre-seed).
- `cr5-queue-with-row.png` — Queue populated with Kirill Rakitin, 136 days, $850.
- `cr5-confirm-dialog.png` — Send lien notice confirmation dialog.
- `cr5-after-send.png` — Post-send state.
- `cr5-mass-notify-no-lien.png` — Mass Notify dropdown without `lien_eligible`.
- `cr6-convert-dialog-warning.png` — ConvertLeadDialog with pre-emptive duplicate warning.
- `cr6-conflict-modal.png` — LeadConversionConflictModal (the CR-6 409 path).
- `cr6-leads.png` — Leads list.
