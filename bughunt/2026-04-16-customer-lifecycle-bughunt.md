# Customer Lifecycle Bug Hunt — 2026-04-16

**Date:** 2026-04-16
**Scope:** End-to-end static code review of the customer lifecycle per `instructions/update2_instructions.md` §1–16 and the `instructions/customer_lifecycle.png` diagram. Covers **both backend and frontend**, with attention to button wiring, modal flows, SMS triggers, state machine transitions, and data-flow consistency.
**Method:**
1. Map each segment of the diagram to backend services/endpoints and frontend features/pages.
2. Delegate phase-by-phase review to ten parallel `Explore` agents covering: Lead intake, Sales pipeline, Jobs tab + Week Of, Schedule + Draft mode, SMS Y/R/C + reschedule, Day-of-Job ops + payment check, Cancellation side-effects, Invoices + mass notifications, Onboarding + renewals, Dedup + admin edits.
3. Manually verify the highest-stakes findings (4 spot-checks) before writing them up.
4. Cross-reference against prior bughunt reports — especially `2026-04-14-customer-lifecycle-deep-dive.md` — to flag survivors, regressions, and new findings.

**Result:** **6 CRITICAL + 14 HIGH + 17 MEDIUM + 11 LOW/UX = 48 findings**
Plus **3 confirmed survivors** from the 2026-04-14 hunt that remain OPEN (H-2/E2E-3, E2E-6, "No reply needs-review path").

Note on false positives: the Explore agents produced a handful of claims that I invalidated on re-read. Those are listed under **Invalidated** at the bottom so the next reviewer doesn't chase them again.

---

## Executive summary

The lifecycle largely works end-to-end, but several promises in the diagram are not honored by the code:

1. **`apply_schedule` (bulk schedule push from the schedule generator) creates appointments with `status="scheduled"` instead of `"draft"`** — bypassing Draft Mode and the "no SMS until admin clicks Send Confirmation" contract (CR-1 below).
2. **`job_started` still does not transition an appointment from `SCHEDULED` → `IN_PROGRESS`** — only from `EN_ROUTE` or `CONFIRMED`. This is the same E2E-6 that was marked OPEN on 2026-04-14 and has not been fixed (CR-2).
3. **Repeat `C` reply still produces a duplicate cancellation SMS** — `_handle_cancel` unconditionally builds the auto-reply even when the appointment is already `CANCELLED`. Same H-2/E2E-3 survivor (CR-3).
4. **`invoice.paid` webhook creates a renewal proposal for any non-first invoice**, not just true renewals — the condition is `agreement.last_payment_date is None`, which misclassifies every mid-cycle charge (prorated additions, manual top-ups) as a renewal (CR-4).
5. **Lien-eligibility flag (SMS #6) is sent immediately by `mass_notify`** instead of being surfaced as a review queue for admin approval. The spec is explicit that the SMS is sent *manually after admin decides to proceed* (CR-5).
6. **`convert_lead` endpoint performs no real-time Tier-1 duplicate check** before creating a customer — so the "Possible match found — Use existing customer" warning promised in §4 and §14 only fires on the create-customer path, not the convert-lead path (CR-6).

Frontend connectivity gaps deserve their own spotlight:
- The **Lead detail page has no Move-to-Jobs, Move-to-Sales, or requires-estimate override buttons** — that flow is only reachable from the Leads list (H-1).
- **Bulk "Send All Confirmations" and "Send Confirmations for [Day]" accept all appointments**, not just drafts, and render misleading counts (H-2).
- **`AppointmentDetail` modal never shows a Send Confirmation button** even when the appointment is DRAFT — admins must return to the calendar card (M-1).
- **Schedule & Calendar use `weekStartsOn: 0` (Sunday)** while Jobs' Week Picker uses `weekStartsOn: 1` (Monday). Scheduling near week boundaries can land jobs in the wrong week (H-3).
- **Invoice list payment-type filter is missing `Credit Card` and `ACH`** — the exact values the spec calls out in §11 (H-4).

---

## CRITICAL

### CR-1 — `apply_schedule` creates appointments in SCHEDULED (not DRAFT) state
**File:** `src/grins_platform/api/v1/schedule.py:559`
**Lifecycle segment:** Draft Mode (§4 diagram; §9)
**Evidence:** Verified. `apply_schedule` writes:
```python
appointment = Appointment(
    ...
    status="scheduled",
    ...
)
```
No `send_confirmation_sms` is invoked either. Net effect: the bulk-scheduling path produces appointments that are *already* past DRAFT but have **no outbound SMS**, so the calendar shows them as Scheduled (dashed) while the customer was never actually notified — the worst of both worlds.
**Expected:** All newly-assigned appointments start in `DRAFT` (dotted, silent). Admin chooses when to Send Confirmation.
**Fix:** Default to `AppointmentStatus.DRAFT.value`. Remove the immediate `job_record.status = "scheduled"` on line 574 unless the generator is explicitly post-confirmation.

---

### CR-2 — `job_started` endpoint does not promote a SCHEDULED appointment to IN_PROGRESS (E2E-6 survivor)
**File:** `src/grins_platform/api/v1/jobs.py:1379-1386`
**Lifecycle segment:** Day of Job → Job Started (§10, Req 3.3)
**Evidence:** Verified. The appointment-side transition only fires when the appointment is already `EN_ROUTE` or `CONFIRMED`:
```python
if appointment and appointment.status in (
    AppointmentStatus.EN_ROUTE.value,
    AppointmentStatus.CONFIRMED.value,
):
    appointment.status = AppointmentStatus.IN_PROGRESS.value
```
If the customer never replied to the confirmation (appointment is still `SCHEDULED`) and the tech skips On My Way, clicking Job Started promotes the *Job* to IN_PROGRESS but leaves the *Appointment* at SCHEDULED. Diagram explicitly says "Steps can be skipped — clicking 'Job Complete' without 'Job Started' still completes both."
**Expected:** `SCHEDULED → IN_PROGRESS` must be an allowed transition here (and `DRAFT → IN_PROGRESS` if we consider an even more aggressive skip).
**Fix:** Add `AppointmentStatus.SCHEDULED.value` to the pre-state set.
**Status:** OPEN since 2026-04-14 (tracked as E2E-6).

---

### CR-3 — Repeat `C` reply still sends a duplicate cancellation SMS (H-2 / E2E-3 survivor)
**File:** `src/grins_platform/services/job_confirmation_service.py:244-269`
**Lifecycle segment:** SMS #1c cancellation reply (§4, §15 — "repeat C is a no-op")
**Evidence:** Verified. The `appt.status in (SCHEDULED, CONFIRMED)` guard gates the *state transition* correctly, but `auto_reply = self._build_cancellation_message(appt, job)` on line 259 runs unconditionally and is then sent by `sms_service.py`. On a second `C`, the appointment is already `CANCELLED`, the branch at 245-254 is skipped, but 259 still builds and returns the cancellation text, which `sms_service._try_confirmation_reply` dispatches to the provider.
**Expected:** Per spec line 1070: "A repeat C from the same customer is a no-op." No SMS, no DB writes on the second C.
**Fix:** Short-circuit at the top of `_handle_cancel` when `appt.status == CANCELLED.value` — return `{"action": "cancelled", "appointment_id": ..., "auto_reply": ""}`.
**Status:** OPEN since 2026-04-14 (tracked as H-2 / E2E-3).

---

### CR-4 — `invoice.paid` webhook misclassifies every non-first invoice as a renewal
**File:** `src/grins_platform/api/v1/webhooks.py:532-566`
**Lifecycle segment:** Contract Renewals (§13)
**Evidence:** Verified. Renewal proposal generation is gated on:
```python
is_first_invoice = agreement.last_payment_date is None
...
if is_first_invoice: ...
else:
    ...
    if agreement.auto_renew:
        renewal_svc = ContractRenewalReviewService(self.session)
        _ = await renewal_svc.generate_proposal(agreement.id)
```
A second, third, or Nth payment within the same contract year (prorated mid-year add-ons, manual top-ups, out-of-cycle charges) all have `last_payment_date != None` → every one of them spawns a spurious renewal proposal on the dashboard.
**Expected:** Only generate a proposal when the invoice is an actual subscription cycle rollover.
**Fix:** Inspect the Stripe invoice `billing_reason` — treat as renewal only when `billing_reason == "subscription_cycle"`. `subscription_create`, `subscription_update`, and `manual` should be skipped.

---

### CR-5 — Lien-eligibility flag (SMS #6) sent immediately instead of surfacing a review queue
**File:** `src/grins_platform/services/invoice_service.py:810-929` (and `frontend/src/features/invoices/components/MassNotifyPanel.tsx`)
**Lifecycle segment:** SMS #6 — Lien Notice Eligibility Flag (§4, §11, §15)
**Evidence:** The `mass_notify(notification_type="lien_eligible")` path loads flagged customers and immediately sends SMS (lines 889-898), identical to past-due/upcoming-due handling. The spec is explicit (§4 lines 362-368 and §15): "the SMS itself is sent manually after admin decides to proceed. This is a flag for admin review."
**Expected:** Flag the customer, surface in a review queue, let admin approve each entry before SMS is sent.
**Fix:** Split the operation: `compute_lien_candidates()` returns a reviewable list; a separate `send_lien_notice(customer_id)` endpoint sends after admin approval. Store approval in an audit log.

---

### CR-6 — `convert_lead` skips the real-time Tier-1 duplicate check
**File:** `src/grins_platform/services/lead_service.py:909-962` ; `src/grins_platform/api/v1/leads.py:490-509`
**Lifecycle segment:** Lead routing → customer creation (§4, §5, §14)
**Evidence:** Lead-list `Move to Jobs` / `Move to Sales` → `POST /leads/{id}/convert` → `service.convert_lead()` → `customer_service.create_customer()` directly. No `check_tier1_duplicates(phone, email)` call on this path. The standalone create-customer endpoint does perform the check, so the warning is only shown when the admin is creating a customer manually — not when converting a lead.
**Expected:** "Possible match found — Use existing customer" warning before auto-creating on conversion (per §4 closing paragraph of §5, and §14 "Real-Time Duplicate Warning").
**Fix:** In `convert_lead`, call `dup_detection_service.check_tier1_duplicates(phone=lead.phone, email=lead.email)` before `create_customer`. If non-empty, return 409 or a structured response the frontend can render as the inline warning. Add a `force=true` override that bypasses the check (audit-logged).

---

## HIGH

### H-1 — Lead detail page has no routing buttons (Move to Jobs / Move to Sales / requires-estimate modal)
**File:** `frontend/src/features/leads/components/LeadDetail.tsx`
**Lifecycle segment:** Lead routing (§4, §5)
**Evidence:** `LeadsList.tsx` contains the 3-option requires-estimate modal and Move-to-Jobs / Move-to-Sales buttons. `LeadDetail.tsx` is missing them entirely. An admin drilling into a lead to review details is a dead-end for routing — they must back out to the list.
**Expected:** The same button set (Mark Contacted, Move to Jobs, Move to Sales, Delete) plus the 3-option override modal should be available from the detail view.
**Fix:** Import `useMoveToJobs` / `useMoveToSales` / the requires-estimate modal helper from the shared hooks and render them in the detail panel.

### H-2 — Bulk "Send Confirmations" buttons don't pre-filter by DRAFT status
**File:** `frontend/src/features/schedule/components/SendDayConfirmationsButton.tsx:31`, `SendAllConfirmationsButton.tsx:36`
**Lifecycle segment:** Draft Mode → Send Confirmation (§9)
**Evidence:** Both components forward the full `appointments` prop to the bulk endpoint. The backend `bulk_send_confirmations` silently drops non-DRAFT rows, but the summary modal count is computed from the unfiltered list, so admins see "12 confirmations will be sent" and only 4 go out.
**Expected:** Frontend should filter to `status === 'draft'` before counting and submitting; the modal should name customers accurately.
**Fix:** Filter `draftAppointments.filter(a => a.status === 'draft')` at component boundary.

### H-3 — Schedule and Calendar use Sunday-based weeks, Jobs tab uses Monday
**Files:**
- `frontend/src/features/schedule/components/SchedulePage.tsx:70`
- `frontend/src/features/schedule/components/CalendarView.tsx:66-67, 308`
- `frontend/src/features/jobs/components/JobWeekEditor.tsx:106-111` (correct Monday)
**Lifecycle segment:** Week Of (§4, §8)
**Evidence:** Schedule / Calendar: `startOfWeek(new Date(), { weekStartsOn: 0 })`. Jobs Week Picker: `weekStartsOn: 1`. Backend `align_to_week()` is Monday-based. Selecting a date near the boundary from the Schedule calendar can land a job in the previous Monday-week on the Jobs side.
**Expected:** Single source of truth: Monday-based weeks everywhere.
**Fix:** Change all `weekStartsOn: 0` → `weekStartsOn: 1` in schedule components.

### H-4 — Invoice payment-type filter is missing Credit Card and ACH
**File:** `frontend/src/features/invoices/components/InvoiceList.tsx:86-93`
**Lifecycle segment:** Invoices filter axis 6 (§11)
**Evidence:** Options are `cash | check | venmo | zelle | stripe`. The spec lists `Credit Card, Cash, Check, ACH, Other`. Venmo/Zelle don't appear in the spec; Credit Card and ACH do.
**Expected:** Options match spec (with backend enum as single source of truth).
**Fix:** Align the `PaymentMethod` enum in the backend with the spec list, update this array accordingly, and either rename `stripe` → `Credit Card` or add both.

### H-5 — `_handle_cancel` has no admin-notification path on customer `C` reply
**File:** `src/grins_platform/services/job_confirmation_service.py:232-269`
**Lifecycle segment:** SMS #1c (§4: "Admin is notified"; §15)
**Evidence:** Docstring on line 237 says "admin notification" is the purpose, but no notification service is called. The return dict is consumed only by `sms_service._try_confirmation_reply`, which ships the customer auto-reply and nothing else.
**Expected:** When a customer cancels by SMS, the admin must be notified (email or in-app alert).
**Fix:** After flushing the CANCELLED transition, dispatch via `notification_service` (email to admin + an Alert record that the dashboard picks up).

### H-6 — Customer reschedule (R) response doesn't push a NEW confirmation SMS after admin resolves
**Files:**
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx:55-61` (queue UI)
- `src/grins_platform/services/appointment_service.py` (reschedule path)
**Lifecycle segment:** SMS #1b reschedule follow-up (§4 lines 270-272: "when rescheduled, a NEW confirmation SMS (#1) is sent and the cycle repeats")
**Evidence:** The queue's "Reschedule to Alternative" flow opens the appointment editor; `update_appointment` only emits a *reschedule* SMS. The diagram promises the full confirmation-request cycle restart after an R reply. Right now the customer receives "Your appointment has been rescheduled to …" but no Y/R/C prompt.
**Expected:** When admin picks a new date for an R-request, send SMS #1 again (Reply Y to confirm / R to reschedule / C to cancel).
**Fix:** In the reschedule-from-R path, call `send_confirmation_sms(appointment_id)` after status is reset to SCHEDULED.

### H-7 — No-reply / timeout "needs review" path is unimplemented
**File:** `src/grins_platform/services/job_confirmation_service.py` (absent) ; `src/grins_platform/services/background_jobs.py` (no matching job)
**Lifecycle segment:** SMS #1 no-reply branch (§4 lines 200-208)
**Evidence:** No cron job, no repository query, no UI surface for appointments that received a confirmation SMS N days ago and never heard back.
**Expected:** Timed-out confirmations land in an admin "needs review" queue for manual follow-up.
**Fix:** Add a nightly job that finds SCHEDULED appointments with confirmation sent >N days ago and no response, and creates a review flag / dashboard alert.

### H-8 — `send_confirmation` button on the calendar card has no non-DRAFT guard
**File:** `frontend/src/features/schedule/components/SendConfirmationButton.tsx`
**Lifecycle segment:** Draft Mode (§9)
**Evidence:** The button renders whenever the parent passes it. The backend returns 422 on a non-draft, so the user gets a toast error rather than a disabled button.
**Expected:** Disable when `status !== 'draft'`, with a tooltip explaining why.
**Fix:** `disabled={sendMutation.isPending || appointment.status !== 'draft'}`.

### H-9 — "Real-time" invoice updates on the customer detail page aren't real-time
**File:** `frontend/src/features/customers/components/InvoiceHistory.tsx:26`
**Lifecycle segment:** Customer detail → Invoices subsection (§7: "updates in real-time when invoice status changes")
**Evidence:** Plain `useCustomerInvoices(customerId, {...})` — no `refetchInterval`, no WS/SSE, no cross-query invalidation when invoice mutations fire elsewhere. Marking an invoice paid from the Invoices tab doesn't propagate to the open customer detail view without a manual refresh.
**Expected:** Sub-second propagation of invoice status changes into the customer detail view.
**Fix:** At minimum, add `refetchInterval: 30_000` on the hook; better, invalidate `['customer-invoices', customerId]` from invoice mutation hooks.

### H-10 — SignWell webhook auto-advance silently no-ops if the sales entry isn't in PENDING_APPROVAL
**File:** `src/grins_platform/api/v1/signwell_webhooks.py:180-191`
**Lifecycle segment:** Sales pipeline → Pending Approval → Send Contract (§6)
**Evidence:** Advance is gated on `if entry.status == SalesEntryStatus.PENDING_APPROVAL.value:`. If the entry has been manually overridden to another status between sending and the webhook firing, the signed document is stored but the entry never advances — and the webhook returns 200 OK, so the problem is invisible.
**Expected:** Warn (or raise) when the webhook lands on an unexpected status, and at minimum log it at ERROR level so ops sees it.
**Fix:** Emit a log warning when the pre-state isn't PENDING_APPROVAL; optionally record an `audit_log` entry so the advance is manually recoverable.

### H-11 — `MassNotifyPanel` does not check SMS consent before enqueueing mass sends
**File:** `src/grins_platform/services/invoice_service.py:889-898`
**Lifecycle segment:** SMS #4, #5 (§11, §15)
**Evidence:** The loop calls `sms_service.send_message(consent_type="transactional")`. If a customer has opted out via STOP, the send throws and the `except Exception` at line 907 only increments `failed`. Nothing proactively skips opted-out customers.
**Expected:** Pre-filter by SMS consent before the send loop, so opt-outs are a `skipped` event, not a silent `failed`.
**Fix:** Query `SmsConsentRecord` for each customer before attempting a send; skip with a reason code.

### H-12 — Mass-notify lien thresholds are defaulted in the backend but exposed as in-UI sliders (spec says "configurable")
**File:** `src/grins_platform/services/invoice_service.py:810-816`, `frontend/src/features/invoices/components/MassNotifyPanel.tsx:28-29`
**Lifecycle segment:** SMS #6 threshold (§15: "thresholds configurable")
**Evidence:** Per-request defaults (60 days, $500) are editable in the panel but there's no system-wide persisted configuration. Admins who want a different firm-wide threshold have to re-enter it every time.
**Expected:** Thresholds belong in business settings (or env), not as per-invocation inputs.
**Fix:** Add `LIEN_DAYS_PAST_DUE` / `LIEN_MIN_AMOUNT` to `business_setting` with admin UI; the panel reads (and may override per send).

### H-13 — Renewal proposal date roll uses `+52 weeks` instead of "closest Monday one year later"
**File:** `src/grins_platform/services/contract_renewal_service.py:73-94`
**Lifecycle segment:** Renewal date rolling (§13)
**Evidence:** Verified.
```python
d = date.fromisoformat(val)
new_d = d + timedelta(weeks=52)
rolled[key] = new_d.isoformat()
```
52 weeks = 364 days. Over a non-leap year the roll lands one calendar day earlier; over a leap year two. For any customer whose renewal date drifts by a day per year, in 5–10 years it will no longer be on the same Monday of the same calendar week.
**Expected:** Spec §13: `"Week of April 20, 2026" → "Week of April 21, 2027" (the closest Monday one year later)`.
**Fix:** Roll by calendar year, then align to Monday:
```python
candidate = d.replace(year=d.year + 1)
monday = candidate - timedelta(days=candidate.weekday())
rolled[key] = monday.isoformat()
```

### H-14 — `bulk_notify_invoices` endpoint has `_current_user = None` with `# type: ignore` — effectively unauthenticated
**File:** `src/grins_platform/api/v1/invoices.py:677-680`
**Lifecycle segment:** Mass notifications (§11)
**Evidence:**
```python
_current_user: ManagerOrAdminUser = None,  # type: ignore[assignment]
service: Annotated[...] = None,  # type: ignore[assignment]
```
Missing `Depends(...)`. If FastAPI resolves the default (`None`), the endpoint proceeds without authentication.
**Expected:** Both dependencies wired through `Depends(...)`.
**Fix:** Replace defaults with the proper dependency call.

---

## MEDIUM

### M-1 — `AppointmentDetail` modal never renders a "Send Confirmation" button for drafts
**File:** `frontend/src/features/schedule/components/AppointmentDetail.tsx`
**Lifecycle segment:** Draft Mode (§9)
**Evidence:** Send-Confirmation is only in the calendar card. If an admin drills into a draft from the details modal, there's no send action.
**Fix:** Conditionally render `SendConfirmationButton` when `status === 'draft'`.

### M-2 — Cancel dialog omits the "Cancel & text customer" button when status is DRAFT rather than disabling it
**File:** `frontend/src/features/schedule/components/CancelAppointmentDialog.tsx:159`
**Lifecycle segment:** Admin cancel (§9)
**Evidence:** Layout collapses to a single button. The spec expects a consistent two-button layout with the inapplicable one disabled + tooltip "Draft was never sent, no text needed."
**Fix:** Keep both buttons, disable "Cancel & text" for DRAFT with tooltip.

### M-3 — Y/R/C keyword map is missing `ok`, `okay`, `yup`, `yeah`, `1`, `different time`, `change time`
**File:** `src/grins_platform/services/job_confirmation_service.py:38-47`
**Lifecycle segment:** SMS #1 parse (§15)
**Evidence:** Map only covers `y/yes/confirm/confirmed/r/reschedule/c/cancel`. Everything else lands in "needs review," which is wasteful for common synonyms the spec explicitly mentions in §9 (lines 776-780: "Y (or yes, confirm, ok, okay)").
**Fix:** Extend the keyword set. This was M-12/H-1 on 2026-04-14 marked OPEN-out-of-scope; worth revisiting.

### M-4 — Confirmation auto-reply doesn't include date/time
**File:** `src/grins_platform/services/job_confirmation_service.py:51`
**Lifecycle segment:** SMS #1a (§4 lines 219-222)
**Evidence:** Template is `"Your appointment has been confirmed. See you then!"`. Spec: `"Your appointment has been confirmed. See you on [date] at [time]!"`.
**Fix:** Parameterize the template with appointment date/time.

### M-5 — Reschedule acknowledgment text diverges from spec
**File:** `src/grins_platform/services/job_confirmation_service.py:52-55`
**Lifecycle segment:** SMS #1b (§4 lines 251-254)
**Evidence:** Current: `"We received your reschedule request. Our team will reach out with alternative times shortly."` Spec: `"We've received your reschedule request. We'll be in touch with a new time."`
**Fix:** Match the spec wording exactly.

### M-6 — Google Review SMS wording diverges from spec
**File:** `src/grins_platform/api/v1/jobs.py:1582-1587`
**Lifecycle segment:** SMS #3 (§4, §10)
**Evidence:** Current: `"Hi {first_name}! Thank you for choosing Grin's Irrigations. We'd love your feedback — please leave us a Google review: {review_url}"`. Spec: `"Thanks for choosing Grins Irrigation! We'd appreciate a quick review: [GOOGLE_REVIEW_URL]"`. Also contains the stray apostrophe + plural "Grin's Irrigations".
**Fix:** Match spec text verbatim.

### M-7 — Admin edit of appointment (drag-drop / Edit modal) does not produce an audit log entry
**File:** `src/grins_platform/services/appointment_service.py:382-482`
**Lifecycle segment:** Admin-initiated edits (§4 "ADMIN-INITIATED APPOINTMENT CHANGES")
**Evidence:** Cancellation has `_record_cancellation_audit`; edit/reactivation have nothing equivalent.
**Fix:** Log `appointment.update` and `appointment.reactivate` with pre/post values and `notify_customer` flag.

### M-8 — Customer-initiated cancel (C reply) doesn't produce an audit log entry
**File:** `src/grins_platform/services/job_confirmation_service.py:232-269`
**Lifecycle segment:** SMS #1c (§4)
**Evidence:** Admin cancel path is audited; customer C path isn't, so the history view doesn't show why an appointment was cancelled when an admin opens it later.
**Fix:** Log `appointment.cancel` with `source="customer_sms"`.

### M-9 — Auto-replies and reschedule follow-up SMS bypass the `sent_messages` table (E2E-8 survivor)
**File:** `src/grins_platform/services/sms_service.py:810-837`
**Lifecycle segment:** SMS audit trail (§15)
**Evidence:** These sends go to `provider.send_text()` directly, not through `SMSService.send_message()`, so they don't create `SentMessage` rows. The compliance audit trail misses an entire class of messages.
**Fix:** Route via `send_message` (which creates the row) or mirror its side effects inside `_try_confirmation_reply`.
**Status:** OPEN since 2026-04-14 (tracked as E2E-8).

### M-10 — Convert-to-Job button fires `/advance` first, then `/convert` only on error
**File:** `frontend/src/features/sales/components/StatusActionButton.tsx:37-144`
**Lifecycle segment:** Sales "Send Contract" → "Closed-Won" (§6)
**Evidence:** On the `SEND_CONTRACT` status, clicking the action calls `advance.mutate()` (line 126). The convert path (109-124) is only reached when advance throws a "signature" error. That means every happy-path conversion takes two round-trips.
**Fix:** When `isSendContract`, always call `convertToJob.mutate()` first; fall back to `advance` only if the entry is in an unexpected state.

### M-11 — Document scope fallback in `_get_signing_document` allows a pre-migration customer-level doc to sign a different entry
**File:** `src/grins_platform/api/v1/sales_pipeline.py:57-115`
**Lifecycle segment:** SignWell (§6)
**Evidence:** The in-code comment acknowledges bughunt H-7 and adds an entry-scoped branch, but the fallback to customer-scope (`sales_entry_id IS NULL`) remains. A customer with two open sales entries where only one uploaded a doc can end up signing the wrong entry's legacy doc.
**Fix:** Remove the customer-scope fallback for active pipeline operations. Only fall back for legacy-read scenarios.

### M-12 — Invoice API `days_until_due` / `days_past_due` are computed client-side instead of server-side
**File:** `frontend/src/features/invoices/components/InvoiceList.tsx:128-146`
**Lifecycle segment:** Invoices list (§11)
**Evidence:** Client computes via `daysDiff(due_date)`, but the backend filter accepts these as numeric ranges — the filter path and the display path aren't reading the same value. Two sources of truth drift on timezone.
**Fix:** Return these fields from `InvoiceResponse`; display and filter from one source.

### M-13 — `PARTIALLY_APPROVED` renewal-proposal status only sets when there are zero PENDING jobs
**File:** `src/grins_platform/services/contract_renewal_service.py:391-411`
**Lifecycle segment:** Contract Renewals (§13)
**Evidence:** Condition is `elif ProposedJobStatus.PENDING.value not in statuses:` — so if admin approves 2 of 7 and walks away, the proposal stays `PENDING` on the dashboard even though it visibly has approvals. The status only flips when all are processed.
**Fix:** Set `PARTIALLY_APPROVED` whenever both APPROVED and REJECTED (or APPROVED + PENDING) are present.

### M-14 — Mass-notify template field names don't match spec merge-field names
**File:** `src/grins_platform/services/invoice_service.py:794-876`
**Lifecycle segment:** SMS #4 / #5 (§11)
**Evidence:** Spec lists `[Customer name]`, `[number]`, `[amount]`, `[date]`. Code uses `{first_name}`, `{invoice_number}`, `{amount}`, `{due_date}`. Neither the spec's bracket names nor a validation step for custom admin templates exists.
**Fix:** Document canonical merge keys in code + admin UI; validate custom templates contain at least the required ones.

### M-15 — Stripe webhook returns 400 on missing secret — Stripe will retry forever
**File:** `src/grins_platform/api/v1/webhooks.py:950-956`
**Lifecycle segment:** Onboarding / renewal webhooks (§12, §13)
**Evidence:** Missing-secret is returned as `400 Bad Request`. Stripe interprets 4xx as terminal and stops retrying — the correct behavior, but for an *infrastructure* misconfiguration we'd rather Stripe back off with a 5xx and page on-call.
**Fix:** Return `503 Service Unavailable` for missing-secret (infra) and keep `400` only for signature mismatches (request).

### M-16 — File-upload size/MIME validation is frontend-only
**File:** `src/grins_platform/services/photo_service.py:278`
**Lifecycle segment:** Sales → Documents (§6)
**Evidence:** Frontend rejects files >25 MB; backend trusts whatever the multipart part contains. A direct API call can push a 2 GB file.
**Fix:** Enforce the 25 MB cap and MIME allow-list server-side.

### M-17 — `DocumentsSection` doesn't validate that the stored `file_key` resolves to a real presigned URL
**File:** `frontend/src/features/sales/components/DocumentsSection.tsx:34-59`
**Lifecycle segment:** Sales → Send for Signature (§6)
**Evidence:** Signing buttons unlock as soon as `documents.length > 0`. If the underlying `file_key` is null or the presign fails, the signing iframe opens with a broken URL.
**Fix:** Resolve the presign at render and hide the buttons if it's null/expired.

---

## LOW / UX

### L-1 — Schedule calendar renders both `💎 ` emoji prefix *and* a PREPAID badge on service-agreement appointments
**File:** `frontend/src/features/schedule/components/CalendarView.tsx:133, 203-210`
**Lifecycle segment:** Calendar visual state (§9)
**Fix:** Remove the emoji prefix; the badge + green left border already convey it.

### L-2 — `apply_schedule` also flips `job_record.status = "scheduled"` (paired with CR-1)
**File:** `src/grins_platform/api/v1/schedule.py:574`
**Fix:** Keep job status in sync with the appointment creation decision made in CR-1.

### L-3 — Lead `Mark Contacted` button hidden once status is `contacted` (can't re-stamp on a second reach-out)
**File:** `frontend/src/features/leads/components/LeadsList.tsx:375`, `LeadDetail.tsx:238`
**Fix:** Show when status is `new | contacted | qualified`.

### L-4 — `LeadDetail.handleMarkContacted` bypasses `useMarkContacted` hook and the NEEDS_CONTACT tag cleanup
**File:** `frontend/src/features/leads/components/LeadDetail.tsx:173-181`
**Fix:** Call the dedicated hook.

### L-5 — `Lead.to_dict` missing `last_contacted_at`, `moved_to`, `moved_at`
**File:** `src/grins_platform/models/lead.py:273-312`
**Fix:** Include the fields for parity with `LeadResponse`.

### L-6 — Email-signing button has no tooltip when disabled due to missing email
**File:** `frontend/src/features/sales/components/SalesDetail.tsx:181-187`
**Fix:** Add "Customer has no email address on file" tooltip branch.

### L-7 — Happy-path sales conversion has no audit log (only Force Convert is logged)
**File:** `src/grins_platform/services/sales_pipeline_service.py:259-331`
**Fix:** Log every `convert_to_job` with a `forced` boolean in details.

### L-8 — Reschedule Requests queue doesn't invalidate its own query on `Mark Resolved`
**File:** `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx:55-61`
**Fix:** `queryClient.invalidateQueries({queryKey: ['reschedule-requests']})` in the hook's `onSuccess`.

### L-9 — Invoice pagination uses `window.history.pushState` instead of React Router
**File:** `frontend/src/features/invoices/components/InvoiceList.tsx:495-521`
**Fix:** Use `useNavigate`/`useSearchParams` so the router state stays consistent.

### L-10 — Bulk "Send All" summary modal shows aggregate numbers but not per-appointment reasons
**File:** `frontend/src/features/schedule/components/SendAllConfirmationsButton.tsx:38-44`
**Fix:** Expose the backend `results[]` in a collapsible details panel.

### L-11 — Frontend job-link in invoice list has no test coverage
**File:** `frontend/src/features/invoices/components/InvoiceList.tsx:287-299`
**Fix:** Add a RTL test that asserts navigation on click.

---

## Carried-over from prior hunts (verified still open)

| Prior ID | New ID | Status | Notes |
|---|---|---|---|
| H-2 / E2E-3 | CR-3 | OPEN | Duplicate cancellation SMS on repeat `C` |
| E2E-6 | CR-2 | OPEN | `job_started` doesn't transition SCHEDULED → IN_PROGRESS |
| E2E-8 | M-9 | OPEN | Auto-replies bypass `sent_messages` |
| H-1 / M-12 (old) | M-3 | Deferred | Y/R/C synonyms — worth revisiting |

The following from 2026-04-14 remain OPEN but were not re-examined in this pass:
- E2E-4: `customers.sms_opt_in` not flipped on STOP.
- E2E-5: No START / UNSTOP handler.
- E2E-7: `ManualLeadCreate` skips E.164 normalization.
- E2E-9: Railway env-var redeploys can stall without running alembic (infra).
- E-BUG-A / E-BUG-B / E-BUG-E / E-BUG-I / L-10: product/infra decisions pending.

---

## Invalidated during review

These items were reported by the Explore agents but failed verification on re-read:

1. **"Agreement missing `service_week_preferences` on webhook creation"** — webhook only creates the skeleton; `complete_onboarding` later writes preferences via `agreement_repo.update` (see `onboarding_service.py:404-408`). Design is correct so long as `complete_onboarding` always runs post-checkout, which it does for the standard funnel.
2. **"Score threshold includes or excludes exactly 50"** — `if score < 50: continue` keeps score=50 as flagged, which is the spec's `>= 50`. Not a bug.
3. **"DRAFT drag-drop sends SMS"** — `_send_reschedule_sms` is guarded by `if appointment.status in (SCHEDULED, CONFIRMED)`; DRAFT is correctly excluded.
4. **"Nightly dedup job doesn't run at 1:30 AM"** — `hour=1, minute=30` is 01:30 local time. Correct.
5. **"Admin edit of SCHEDULED/CONFIRMED doesn't send reschedule SMS"** — verified correct at `appointment_service.py:461-479`.

---

## Summary table

| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 14 |
| MEDIUM | 17 |
| LOW / UX | 11 |
| **Total** | **48** |

### Top-5 recommended fixes (highest spec-divergence, easiest to unblock)

1. **CR-1** — default new appointments to DRAFT in `apply_schedule`.
2. **CR-2** — allow `SCHEDULED → IN_PROGRESS` in `job_started`.
3. **CR-3** — short-circuit `_handle_cancel` when already CANCELLED.
4. **CR-6** — add Tier-1 dedup check to `convert_lead`.
5. **H-3** — unify week start to Monday across Schedule and Calendar.

### Frontend connectivity gaps (rolling up the button-wiring findings)

| Where | What's broken |
|---|---|
| `LeadDetail.tsx` | No Move-to-Jobs / Move-to-Sales / requires-estimate modal (H-1) |
| `LeadDetail.tsx` | Mark Contacted bypasses hook (L-4) |
| `SendDayConfirmationsButton.tsx` / `SendAllConfirmationsButton.tsx` | Don't filter for DRAFT (H-2) |
| `AppointmentDetail.tsx` | No Send Confirmation button for drafts (M-1) |
| `CancelAppointmentDialog.tsx` | Collapses to one button for DRAFT (M-2) |
| `SchedulePage.tsx` / `CalendarView.tsx` | Sunday-based weeks (H-3) |
| `InvoiceList.tsx` | Payment-type filter missing Credit Card / ACH (H-4) |
| `InvoiceHistory.tsx` | "Real-time" invoice updates are static fetch-once (H-9) |
| `StatusActionButton.tsx` (sales) | Convert path only reached on error (M-10) |
| `RescheduleRequestsQueue.tsx` | Mark Resolved doesn't invalidate query (L-8) |
| `SalesDetail.tsx` | Missing tooltip on email-signing disabled state (L-6) |
| `MassNotifyPanel.tsx` | Thresholds not persisted anywhere (H-12) |
| `LeadsList.tsx` / `LeadDetail.tsx` | Mark Contacted hidden after first contact (L-3) |

---

*Hunt performed 2026-04-16 against the `dev` branch HEAD (b60f740).*

---

## History — Resolved

| Finding | Resolution Date | Commit SHA | Branch | Notes |
|---|---|---|---|---|
| CR-1 — `apply_schedule` creates SCHEDULED not DRAFT | 2026-04-15 | `2f7caaf` | `fix/cr-1-apply-schedule-draft` | Default to `AppointmentStatus.DRAFT.value`; `Job.status` stays `to_be_scheduled`. |
| CR-2 — `job_started` doesn't promote SCHEDULED → IN_PROGRESS | 2026-04-15 | `c65283e` | `fix/cr-2-job-started-scheduled` | Added `SCHEDULED` to pre-state set; transitions table now allows `SCHEDULED → IN_PROGRESS`. |
| CR-3 — Repeat `C` sends duplicate cancellation SMS | 2026-04-15 | `9a30fac` | `fix/cr-3-repeat-cancel-sms` | `_handle_cancel` short-circuits when already CANCELLED; empty `auto_reply` suppresses SMS. |
| CR-4 — `invoice.paid` misclassifies non-first invoices as renewals | 2026-04-15 | `6d99587` | `fix/cr-4-invoice-billing-reason` | Renewal branch now gated on Stripe `billing_reason == "subscription_cycle"`. |
| CR-5 — Lien SMS sent immediately instead of queued | 2026-04-15 | `d679c25` | `fix/cr-5-lien-review-queue` | Split into `compute_lien_candidates` + `send_lien_notice` with SMS-consent pre-filter and audit log; new `/invoices?tab=lien-review` queue UI. |
| CR-6 — `convert_lead` skips Tier-1 dedup | 2026-04-15 | `7007002` | `fix/cr-6-convert-lead-dedup` | Added `force` flag; raises `LeadDuplicateFoundError` → 409 with structured detail; FE surfaces conflict modal with "Use existing" + "Convert anyway". |
| H-1 — LeadDetail missing routing buttons | 2026-04-16 | `6c098a5` | `fix/h-1-lead-detail-routing` | Full parity with LeadsList (Mark Contacted, Move to Jobs, Move to Sales, Delete + requires-estimate override + CR-6 conflict modal) via shared `useLeadRoutingActions` hook. Also folds L-4. |
| H-2 — Bulk confirmation filters don't re-filter DRAFT | 2026-04-16 | `a389f8c` | `fix/h-2-bulk-confirmation-filter` | Defensive `useMemo` filter in `SendAllConfirmationsButton` + `SendDayConfirmationsButton`. `SendDayConfirmationsButton` now takes `Appointment[]` instead of id-array so count + submit stay in sync. |
| H-3 — Schedule week starts Sunday | 2026-04-16 | `ab67840` | `fix/h-3-week-starts-monday` | All `weekStartsOn: 0` → `1` in schedule feature plus `firstDay={1}` on FullCalendar so the rendered grid matches the state logic. |
| H-4 — Payment-type filter missing Credit Card / ACH | 2026-04-16 | `d4f738c` | `fix/h-4-payment-method-enum` | Added `credit_card`/`ach`/`other` to `PaymentMethod` enum + Alembic CHECK-constraint widen (kept `stripe` for legacy rows — no data migration). FE filter + record-payment picker omit `stripe` going forward. |
| H-5 — No admin notification on customer `C` reply | 2026-04-16 | `6a31863` | `fix/h-5-admin-cancel-alert` | New `Alert` model + `AlertRepository` + `GET /api/v1/alerts` endpoint + migration `20260416_100100`. `NotificationService.send_admin_cancellation_alert` wired into `_handle_cancel` after CR-3 short-circuit; email failures logged, don't block customer reply. |
| H-6 — R reply doesn't send new confirmation SMS cycle | 2026-04-16 | `ccde877` | `fix/h-6-reschedule-reconfirm` | New `POST /api/v1/appointments/{id}/reschedule-from-request` resets appointment to SCHEDULED and re-sends SMS #1 (Y/R/C). RescheduleRequestsQueue UI routes through the new endpoint. FE tests mocked AppointmentForm to stay deterministic. |
| H-7 — No-reply review queue missing | 2026-04-16 | `3642069` | `fix/h-7-no-reply-review-queue` | Nightly `flag_no_reply_confirmations` APScheduler job + `needs_review_reason` appointment column (migration `20260416_100200`) + `NoReplyReviewQueue` component on `/schedule` with Call / Send Reminder / Mark-Contacted actions. Default 3-day threshold, BusinessSetting-tunable. |
| H-8 — `SendConfirmationButton` not disabled for non-DRAFT | 2026-04-16 | `e52ed2b` | `fix/h-8-send-confirmation-disable` | `appointment: Appointment` prop added; `disabled={... || status !== 'draft'}` with "Confirmation already sent" tooltip. Tested across all 8 non-DRAFT statuses. |
| H-9 — Invoice history not real-time | 2026-04-16 | `4925941` | `fix/h-9-invoice-history-realtime` | `refetchInterval: 30_000` on `useCustomerInvoices` + `customerInvoiceKeys.all` invalidation from 11 invoice mutation hooks. Query key refactored (commit `8d9df12`) so prefix invalidation actually matches. |
| H-10 — SignWell advance fails silently on unexpected pre-state | 2026-04-16 | `c51f7cc` | `fix/h-10-signwell-advance-log` | `document_signed` webhook now emits a structured WARN when the SalesEntry isn't in `PENDING_APPROVAL`; still returns 200 so SignWell doesn't retry. |
| H-11 — `mass_notify` doesn't skip opted-out customers | 2026-04-16 | `ee4eb82` | `fix/h-11-mass-notify-consent-prefilter` | Batched `SmsConsentRepository.get_opted_out_customer_ids` pre-filter in mass_notify; response carries `skipped_count` + `skipped_reasons`. Lien branch untouched (CR-5 already handles it per-customer). |
| H-12 — Lien thresholds not persisted | 2026-04-16 | `94efcbf` | `fix/h-12-lien-thresholds-settings` | New `BusinessSettingService` + `GET/PATCH /api/v1/settings/business` endpoints + `BusinessSettingsPanel` card on `/settings` seeding `lien_days_past_due`/`lien_min_amount`/`upcoming_due_days`/`confirmation_no_reply_days`. `compute_lien_candidates` reads defaults from `BusinessSetting`. Migration `20260416_100300`. |
| H-13 — Renewal roll uses 52 weeks | 2026-04-16 | `99db54d` | `fix/h-13-renewal-date-roll` | `d.replace(year=d.year + 1)` + align-to-Monday with Feb 29 → Feb 28 fallback. Five-year roll test confirms weekday stability. |
| H-14 — `bulk_notify_invoices` effectively unauthenticated | 2026-04-16 | `c607c96` | `fix/h-14-bulk-notify-auth` | Replaced `_current_user: ManagerOrAdminUser = None  # type: ignore[assignment]` with `_current_user: ManagerOrAdminUser` (Depends-annotated alias). New 401/403/200 tests cover the three auth tiers. |

### Follow-up commits (not their own bug IDs)

| Context | Commit SHA | Notes |
|---|---|---|
| Correct H-9 queryKey for prefix invalidation | `8d9df12` | `useCustomerInvoices` queryKey structure was broken — invalidation-by-prefix didn't match. Simplified to `customerInvoiceKeys.byCustomer(customerId)` prefix. |
| Resolve H-7 + H-12 migration revision clash | `ffa068e` | Both migrations were authored as `20260416_100200`. Renamed H-12's to `20260416_100300` and unified the `confirmation_no_reply_days` seed shape on `{"value": N}`. |
