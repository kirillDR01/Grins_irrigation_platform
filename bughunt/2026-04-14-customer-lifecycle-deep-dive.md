# Customer Lifecycle Deep-Dive — 2026-04-14

**Date:** 2026-04-14
**Scope:** End-to-end audit of the customer lifecycle per `instructions/update2_instructions.md` §4, scoped by `.kiro/specs/smoothing-out-after-update2` and `.kiro/specs/crm-changes-update-2`.
**Method:**
1. Static code review of lifecycle code paths (leads → sales → jobs → schedule → on-site → invoices → SMS in/out → onboarding → renewals)
2. Live E2E walkthrough of the dev deployment via agent-browser (Vercel Preview `grins-irrigation-platform-git-dev` + Railway `grins-dev-dev`) with real SMS sent to +19527373312
3. Cross-check of findings against existing bughunt reports (esp. `2026-04-09-communications-deep-dive-round-2.md`) to flag survivors and regressions.

**Result:** 11 CRITICAL + 14 HIGH + 14 MEDIUM + 18 LOW/UX = **57 findings total**

Test records left in dev DB are listed at the bottom under **Cleanup**.

---

## Fix-status update — 2026-04-14 (evening, post-remediation sweep)

**Remediation scope:** this sweep addressed CRITICAL + HIGH priority findings only. Every MEDIUM, LOW/UX, and E-BUG-* item not listed as fixed below remains `[OPEN]`.

Verified against current `dev` branch after commits `dea1220`, `5fa5e74`, `ea81dc6`, `46a2bc0`, `04be13c`, `de8c28a`.

**Fixed (11):** CR-1, CR-2, CR-3, CR-4, CR-5, CR-6, CR-7, CR-10, H-2, H-9, E-BUG-B (observability portion)
**Partial (1):** CR-9 (still raises `ConsentRequiredError`, but API handler now catches it → 422 instead of 500; underlying legacy-flag consult unchanged)
**Still open (all remaining):** CR-8, H-1, H-3, H-4, H-5, H-6, H-7, H-8, H-10, X-1, E-BUG-C, E-BUG-D, E-BUG-G, plus every M-* and L-* and E-BUG-A/E/F/H/I/J finding.

Individual findings below are tagged `[FIXED]`, `[PARTIAL]`, or `[OPEN]` with the relevant commit / current file:line evidence.

---

## Environment

| Thing | URL / value |
|---|---|
| CRM frontend (dev) | https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app |
| Marketing frontend (dev) | https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app |
| Backend API (dev) | https://grins-dev-dev.up.railway.app |
| Admin creds | admin / admin123 |
| SMS test number (allowlisted) | +19527373312 |
| CallRail tracking number (from) | +19525293750 |

---

## Executive summary

The "smoothing-out-after-update2" spec largely ships — the UI wiring for the warning modal (Req 6), badges, Scheduled status, draft mode, appointment Edit button, estimate-calendar auto-advance, disabled signing buttons, and mobile `tel:` links all work in the live run. **But under the hood the SMS cancellation path, masked-phone resolution for auto-replies, and on-site appointment state machine all have bugs that break core promises of §4 of the diagram.** In particular:

- **BUG-CR-2** — `cancel_appointment` reads `pre_cancel_status` *after* the status has already been flipped to CANCELLED, so the cancellation-SMS branch is always skipped. Admin cancels and the customer is never told.
- **BUG-CR-3** — Y/R/C auto-replies (confirmation, reschedule ack, cancellation confirmation) are sent to the masked CallRail phone (`+3312`). The customer's confirmation reply works; they get *no* acknowledgment back.
- **BUG-CR-1** — The appointment service's internal `_STATUS_TRANSITIONS` map rejects DRAFT→SCHEDULED, SCHEDULED→CONFIRMED, SCHEDULED→EN_ROUTE, and every skip-to-complete combination. Every caller that goes through the service method hits `InvalidStatusTransitionError` — the ORM-level map is looser and is why the UI appears to work, but the service contract is broken.
- **BUG-CR-6** — `on_my_way` and `request_google_review` instantiate `SMSService(session)` with no provider; default is `NullProvider`, so no CallRail API call is made. E2E observed "SMS sent" toasts but this should be verified on the phone — if no SMS actually arrived for the On-My-Way and Google Review pushes, this is why.
- **BUG-B** (E2E) — The public "Get Your Free Quote" form on the marketing dev site silently fails: no success banner, no network error, no CRM record. That's the primary inbound-lead path.
- **BUG-CR-5** — `DELETE /api/v1/appointments/{id}` and `POST /api/v1/jobs/{id}/on-my-way` (and most other job-state endpoints) have **no auth guard**. Req 4 was applied to `POST /api/v1/jobs` only; the rest are wide open.

Full findings below, grouped by severity and prefixed `CR-*` for code-review-only, `E-*` for E2E-observed, and `X-*` for cross-confirmed.

---

## CRITICAL

### CR-1 — Appointment `transition_status` state machine blocks DRAFT→SCHEDULED, SCHEDULED→EN_ROUTE, every skip-to-complete  `[FIXED]`
**File:** `src/grins_platform/services/appointment_service.py:67-77, 1897-1912`
**Lifecycle segment:** on-site ops, draft mode (Req 3, Req 5, Req 8, Req 19.5)
`_STATUS_TRANSITIONS` contains only CONFIRMED→EN_ROUTE, EN_ROUTE→IN_PROGRESS, IN_PROGRESS→COMPLETED. Rejected: DRAFT→SCHEDULED (Send Confirmation), SCHEDULED→CONFIRMED (Y reply), SCHEDULED→EN_ROUTE (On My Way when unconfirmed — spec: "also works from SCHEDULED if unconfirmed"), CONFIRMED→IN_PROGRESS (Started when On My Way skipped), SCHEDULED/CONFIRMED→COMPLETED (Complete without Started). ORM-level `VALID_APPOINTMENT_TRANSITIONS` (`models/appointment.py:29`) is correct — hence UI appears functional — but the service helper is wrong. Latent trap as more callers migrate to the service method.
**Fix:** Import and reuse `VALID_APPOINTMENT_TRANSITIONS` instead of a second local copy.
**Resolution (commit `dea1220`):** Local `_STATUS_TRANSITIONS` dict removed; service now imports `VALID_APPOINTMENT_TRANSITIONS` from `models.appointment` (see `services/appointment_service.py:30`). All nine transitions defined in the ORM map are accepted.

### CR-2 — `cancel_appointment` never sends cancellation SMS (pre_cancel_status read after status flip)  `[FIXED]`
**File:** `src/grins_platform/services/appointment_service.py:487-516`
**Lifecycle segment:** SMS cancellation (Req 8.10-8.11, Req 15)
Sequence: `update_status(CANCELLED)` → `clear_on_site_data(appointment)` → `pre_cancel_status = appointment.status` (now `cancelled` via SQLAlchemy identity-map refresh) → `if pre_cancel_status in (SCHEDULED, CONFIRMED, EN_ROUTE, IN_PROGRESS)` is always false → no SMS. Customer is never told their appointment was cancelled by admin.
**Fix:** Capture `pre_cancel_status = appointment.status` at function entry, *before* the `update_status` call.
**Resolution (commit `ea81dc6`):** `pre_cancel_status` is now captured at function entry (`services/appointment_service.py:477`) before `update_status(CANCELLED)`. SMS branch at L493-498 gates on the pre-flip value. Admin opt-out dialog also added so admin can suppress the SMS deliberately.

### CR-3 — Y/R/C auto-replies are sent to masked CallRail phone (`+3312`) instead of real E.164  `[FIXED]`
**File:** `src/grins_platform/services/sms_service.py:746-759` (confirmation reply), `_handle_cancel` auto-reply, and all follow-up sends
**Lifecycle segment:** SMS inbound routing (spec §4 SMS #1a/#1b/#1c)
After `JobConfirmationService.handle_confirmation` returns, the service sends the auto-reply via `self.provider.send_text(self._format_phone(from_phone), ...)`. `from_phone` is the CallRail mask (e.g. `***3312`); `_format_phone` strips non-digits → `3312` → `+3312`. Provider either rejects or ships a malformed number. **Customer's Y reply confirms the appointment, but they get no "Your appointment has been confirmed" ack back. Same for R and C replies.**
**Fix:** Have `JobConfirmationService.handle_confirmation` return `original_sent_message.recipient_phone` (the real E.164 it already resolved). Use that phone for every follow-up send in `sms_service.py` and `_send_reschedule_followup`.
**Resolution (commit `5fa5e74`):** `handle_confirmation` now surfaces `recipient_phone`; sms_service uses `reply_phone = result.get("recipient_phone") or self._format_phone(from_phone)` (L752). Follow-up reschedule send uses the same resolved phone.

### CR-4 — STOP keyword correlation still broken for appointment threads (survived from BUG-C1, 2026-04-09)  `[FIXED]`
**File:** `src/grins_platform/services/campaign_response_service.py:151-153` and `services/sms_service.py:810-830`
**Lifecycle segment:** SMS opt-out / TCPA compliance
`correlate_reply(thread_id)` returns an empty `CorrelationResult` when `sent_msg.campaign_id is None` — but appointment-confirmation SMS always have `campaign_id = None`. So `_process_exact_opt_out` falls back to the masked phone again, writes a garbage E.164 like `+3312` into `SmsConsentRecord.phone_number`, and the customer's real number is never marked opted-out. BUG-C1 from the April-9 deep dive was only *partially* fixed.
**Fix:** Drop the `campaign_id` guard in `correlate_reply`, or add a dedicated `resolve_real_phone(thread_id)` helper used by the opt-out path.
**Resolution (commit `5fa5e74`):** Opt-out path now resolves the real phone via `correlate_reply` and uses `corr.sent_message.recipient_phone` (`services/sms_service.py:827-830`) before writing the `SmsConsentRecord`. Masked CallRail numbers no longer land in the consent table.

### CR-5 — Auth guard missing on every job-state and appointment-cancel endpoint except `POST /api/v1/jobs`  `[FIXED]`
**File:** `src/grins_platform/api/v1/appointments.py:624-659` (DELETE); `src/grins_platform/api/v1/jobs.py` (on-my-way, job_started, complete_job, update_status, create_job_invoice, add_job_note, request_google_review)
**Lifecycle segment:** cross-cutting (Req 4)
Req 4 (auth guard on `POST /api/v1/jobs`) was implemented but the sibling endpoints — which can trigger customer-facing SMS, flip job status, create invoices, cancel appointments — have no `_user: CurrentActiveUser` dependency. Any unauthenticated actor who discovers the URLs can drive the entire workflow.
**Fix:** Add `_user: CurrentActiveUser` to every state-mutating endpoint; harmonize with `POST /api/v1/jobs`.
**Resolution (commits `46a2bc0`, `04be13c`):** `CurrentActiveUser` guard added to DELETE `/api/v1/appointments/{id}` (appointments.py:638) plus on-my-way, job_started, complete_job, create_job_invoice, add_job_note, request_google_review in jobs.py. Unit tests recovered to account for new auth requirement.

### CR-6 — `on_my_way` and `request_google_review` instantiate `SMSService(session)` with default NullProvider — real SMS never dispatched  `[FIXED]`
**File:** `src/grins_platform/api/v1/jobs.py:1253`, `services/appointment_service.py:1631`
**Lifecycle segment:** SMS outbound (Req 1, Req 27)
`SMSService.__init__(provider=NullProvider())` is the default. These two call sites don't override it, unlike `_send_confirmation_sms` which passes `provider=get_sms_provider()`. Consequence: `SentMessage` rows are written ("audit says sent"), admin UI shows "SMS sent" toast, but no CallRail network call ever happens. This is the direct cause of Req 1 being silently broken even after the task checkbox was ticked.
**Fix:** Either default the constructor to `get_sms_provider()` or explicitly pass it in these two call sites.
**Resolution:** `SMSService.__init__` now defaults to `get_sms_provider()` when no provider is passed (`services/sms_service.py:128-135`). Both `on_my_way` (jobs.py:1260) and `request_google_review` (appointment_service.py:1671) construct `SMSService(session)` with no explicit provider, which now picks up the CallRail provider via the factory.

### CR-7 — `job_started` doesn't cover SCHEDULED→IN_PROGRESS on the appointment (skip path)  `[FIXED]`
**File:** `src/grins_platform/api/v1/jobs.py:1330-1336`
**Lifecycle segment:** on-site ops (Req 3.3, Req 19.5)
Guard: `if appointment.status in (EN_ROUTE, CONFIRMED)`. Misses SCHEDULED — the common case where customer didn't reply Y and tech went straight to site. Job flips to IN_PROGRESS; appointment is stranded at SCHEDULED.
**Fix:** Add `SCHEDULED` to the allowed pre-states.
**Resolution:** Guard now accepts `TO_BE_SCHEDULED` and `SCHEDULED` as valid pre-states (`api/v1/jobs.py:1328-1330`). Skip path from SCHEDULED→IN_PROGRESS works.

### CR-8 — `send_automated_message` bypasses audit log, dedup, consent, and last-contacted update  `[OPEN]`
**File:** `src/grins_platform/services/sms_service.py:404-451`
**Lifecycle segment:** SMS outbound (notifications, onboarding reminders, estimate nudges, lead follow-up)
Calls `self.provider.send_text` directly. No `SentMessage` row (no dedup, no 30-day Google-review block, no per-appointment dedup), no `_touch_lead_last_contacted` (Req 11.3 broken for these flows), no consent check via `check_sms_consent`. Past-due/upcoming-due mass notifications can re-spam.
**Fix:** Route through `send_message` with `MessageType.*` so everyone shares dedup/audit/lead-touch.
**Status:** Not yet addressed. `send_automated_message` (sms_service.py:407-453) still calls `provider.send_text` directly at L448.

### CR-9 — `request_google_review` raises `ConsentRequiredError` into the handler without a handler — 500 on opted-out customer  `[PARTIAL]`
**File:** `src/grins_platform/services/appointment_service.py:1585-1591` + `api/v1/jobs.py` request_google_review handler
**Lifecycle segment:** Google Review SMS (Req 1, Req 34)
Uses legacy `customer.sms_opt_in` instead of `check_sms_consent(..., 'transactional')`. Customers who opted in via the new `SmsConsentRecord` table but whose Customer row still has `sms_opt_in=False` are falsely denied. The error then propagates as HTTP 500 because the handler doesn't catch it.
**Fix:** Use `check_sms_consent`; return `ReviewRequestResult(sent=False, message='Customer opted out of SMS')` instead of raising.
**Status:** Service still raises `ConsentRequiredError` and still consults legacy `customer.sms_opt_in` (`services/appointment_service.py:1625-1631`). The API handler now catches the exception and returns HTTP 422 (appointments.py:1104-1109), so the 500 is gone — but the underlying consent-table mismatch still incorrectly denies customers whose `SmsConsentRecord` says opted-in.

### CR-10 / BUG-H-4 — Reschedule and cancellation SMS reuse `MessageType.APPOINTMENT_CONFIRMATION` — dedup eats them  `[FIXED]`
**File:** `src/grins_platform/services/appointment_service.py:1055-1062, 1098-1105`
**Lifecycle segment:** SMS outbound (Req 14, Req 15)
Both `_send_reschedule_sms` and `_send_cancellation_sms` call `send_message(..., message_type=APPOINTMENT_CONFIRMATION)`. The 24-hour per-appointment dedup in `sms_service.py:224-248` matches on `(appointment_id, message_type)`. So: send confirmation → within 24h cancel or reschedule → cancellation/reschedule SMS is silently deduped away.
**Fix:** Introduce (or use) `APPOINTMENT_RESCHEDULE` and `APPOINTMENT_CANCELLATION` types so dedup is per-type, and emit a clear log line when the dedup short-circuits a customer-critical notification.
**Resolution (commits `ea81dc6`, `de8c28a`):** `MessageType.APPOINTMENT_RESCHEDULE` and `APPOINTMENT_CANCELLATION` added in `models/enums.py:685-686`; `_send_reschedule_sms` uses `APPOINTMENT_RESCHEDULE` and `_send_cancellation_sms` uses `APPOINTMENT_CANCELLATION`. `sent_messages.message_type` CHECK constraint widened to accept the new values.

### E-BUG-B — Public "Get Your Free Quote" form silently fails  `[PARTIAL]`
**Marketing site lead form submission**
Filled the full form (phone, terms checkbox, service selection) on https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app and clicked submit. No success banner, no redirect, no toast, no CRM record. Primary inbound-lead path is broken on dev. Needs a network-tab inspection to know whether the request is failing, being issued against the wrong API base, or being blocked by CORS.
**Status (commit `46a2bc0`):** Backend observability hardened — structured exception + `source_site` logging added in `api/v1/leads.py:154-167`, so failures will now show up in Railway logs instead of failing silently server-side. Note: this makes the failure *diagnosable* but does not prove the original symptom is gone; an E2E retest on the marketing form is still required to confirm the full end-to-end path works.

---

## HIGH

### H-1 — `JobConfirmationService._handle_confirm` only accepts `y|yes|confirm|confirmed` — no "ok", "yeah", "yup", "1"  `[OPEN]`
**File:** `src/grins_platform/services/job_confirmation_service.py:38-47, 174-177`
Real SMS replies on mobile phones are `OK`, `Yep`, `1`, `yes please`. None parse. Customer thinks they confirmed; admin doesn't see a response; `_handle_needs_review` fires and it lands in the manual-follow-up queue.
**Fix:** Expand `_KEYWORD_MAP`: confirm = {y, yes, yeah, yep, yup, ok, okay, sure, 1, confirm, confirmed}; reschedule = {r, resched, reschedule, reschedule please, 2, change}; cancel = {c, cancel, cancelled, 3, no, stop… wait — STOP is opt-out, not cancel — explicit blocklist}.
**Status:** Keyword map unchanged (`job_confirmation_service.py:39-42`); synonyms still fall to needs-review.

### H-2 — Second "C" reply resends cancellation SMS (no idempotency guard)  `[FIXED]`
**File:** `src/grins_platform/services/job_confirmation_service.py:238-262`
If customer texts "C" twice, the second run still enters `_build_cancellation_message` and sends another cancellation SMS. `clear_on_site_data` also runs the second time, which is a no-op but logs noise.
**Fix:** Short-circuit when `appt.status == CANCELLED` with "Your appointment is already cancelled. Call [business] to reschedule."
**Resolution:** `_handle_cancel` now gates the transition on `appt.status in (SCHEDULED, CONFIRMED)` (`job_confirmation_service.py:245-248`), so a second "C" is a no-op and no additional SMS is sent.

### H-3 — Dates in outbound confirmation/reschedule SMS are raw ISO (`2026-04-21`), not "Monday, April 21"  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:972-992, 1032-1053`
`date_str = str(appointment.scheduled_date)`. Customer-facing format.
**Fix:** `scheduled_date.strftime("%A, %B %-d")`.
**Status:** Confirmation + reschedule SMS still use `str(appointment.scheduled_date)` (ISO). Cancellation SMS uses `%B %d, %Y` (`job_confirmation_service.py:289`) — better but missing weekday.

### H-4 — `create_appointment` silently allows DRAFT appointments for COMPLETED or CANCELLED jobs  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:315-323`
Only `TO_BE_SCHEDULED` is handled explicitly (transitioned to SCHEDULED). COMPLETED, CANCELLED, IN_PROGRESS jobs all accept new appointments with no error. Admin can accidentally schedule a finished job; draft-mode flow then proceeds.
**Fix:** Reject appointment creation when `job.status in {COMPLETED, CANCELLED}`.
**Status:** No status guard added to `create_appointment` (see `services/appointment_service.py:242-301`).

### H-5 — `move_to_jobs` drops `job_address` and any `requested_date` — Week Of and property info lost  `[OPEN]`
**File:** `src/grins_platform/services/lead_service.py:1001-1009`
`JobCreate(customer_id, job_type, description)` — no `property_id`, no `target_start_date/end_date`. Downstream Week Of auto-population uses generator defaults; Jobs-tab Address column is empty for manually-moved leads.
**Fix:** Create/ensure a Property from `lead.job_address`, link it, copy any lead preferences into JobCreate.
**Status:** `JobCreate` still built from `(customer_id, job_type, description)` only (`lead_service.py:1004-1008`).

### H-6 — `move_to_sales` ditto — `SalesEntry.property_id = None`, then `convert_to_job` propagates that null downstream  `[OPEN]`
**File:** `src/grins_platform/services/lead_service.py:1043-1054`; `services/sales_pipeline_service.py:277-283`
Address on resulting Job is blank; property tag filtering breaks.
**Fix:** Ensure a Property at `move_to_sales`; store `property_id` on `SalesEntry`.
**Status:** `SalesEntry` still created without `property_id` (`lead_service.py:1045-1051`).

### H-7 — Sales signing document lookup is by `customer_id`, not `sales_entry_id` — customers with 2 pipeline entries sign the wrong doc  `[OPEN]`
**File:** `src/grins_platform/api/v1/sales_pipeline.py:56-74, 264, 312`
`_get_signing_document(session, entry.customer_id)` returns the newest estimate/contract across *all* of a customer's pipeline entries.
**Fix:** Store `sales_entry_id` on `CustomerDocument`; filter on that.
**Status:** Query still filters by `customer_id` only; no `sales_entry_id` on CustomerDocument (`api/v1/sales_pipeline.py:64-72`).

### H-8 — Reactivating a CANCELLED appointment → new date doesn't emit a reschedule SMS  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:435-452`
Reactivation flips status CANCELLED→SCHEDULED; then the SMS branch checks `appointment.status in (SCHEDULED, CONFIRMED)` *before* the in-memory update persists, so it still reads `CANCELLED` and skips. Customer is never told the cancelled appointment is back on.
**Fix:** Include CANCELLED in the pre-state allowed to fire a reschedule SMS, or explicitly fire a fresh confirmation.
**Status:** Pre-state check unchanged (`services/appointment_service.py:407-410`).

### H-9 — `complete_job` builds response from stale `updated` object — may report pre-refresh timestamps  `[FIXED]`
**File:** `src/grins_platform/api/v1/jobs.py:1085-1158`
`updated = service.update_status(...)` → `await session.refresh(job)` (L1122) → time-tracking metadata set on `job` (L1123) → response built from `updated` (L1154). `updated` is pre-refresh. Minor, but `completed_at`, total-elapsed derivations may be stale/off.
**Fix:** Build response from `job`.
**Resolution:** Response is now built from the refreshed `updated` object after the `session.refresh(job)` call (see `api/v1/jobs.py:1141, 1159`).

### H-10 — `handle_webhook` fallback path marks inbound as opt-out without writing `SmsConsentRecord`  `[OPEN]`
**File:** `src/grins_platform/services/sms_service.py:1017-1023`
The EXACT_OPT_OUT early match path writes the consent record. The fallback `if body.lower() in {stop, unsubscribe, cancel}` path returns `{"action":"opt_out"}` without writing anything. Dead code in practice but a footgun.
**Fix:** Remove the fallback or route it through `_process_exact_opt_out`.
**Status:** Fallback block still returns opt-out action without writing consent (`sms_service.py:1025-1031`).

### E-BUG-C — Add Lead modal rejects E.164 phone format (`+19527373312` → "Invalid phone format")  `[OPEN]`
**File:** frontend Add Lead modal phone validator
Only bare-10-digit `9527373312` is accepted on the client. Backend normalizes both forms. User-hostile inconsistency.
**Fix:** Accept any form the backend accepts; normalize before submission.

### E-BUG-G — "Job Complete" on a TO_BE_SCHEDULED service-agreement job returns generic "Failed to complete job"  `[OPEN]`
**Route:** Jobs detail, no appointment yet
Req 19.5 says skip scenarios must be graceful. The UI either needs to disable Job Complete until an appointment exists, or surface a clearer "Schedule an appointment first" message. Backend-side, `job_service.VALID_TRANSITIONS` does not include TO_BE_SCHEDULED→COMPLETED (see M-1) — that's the root.

### E-BUG-D — Lead→Sales auto-merge into existing customer is silent  `[OPEN]`
**Route:** Move to Sales when `lead.phone` matches existing Customer
The Sales entry attaches to the existing customer; no toast or warning. Admin can't tell the lead name was discarded.
**Fix:** Toast: "Merged into existing customer: {customer.full_name}".

### X-1 — Default fallback for `GOOGLE_REVIEW_URL` is likely stale ("grins-irrigations" plural)  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:1618-1621`
The fallback `"https://g.page/r/grins-irrigations/review"` looks typoed (plural "irrigations") and probably 404s. When env var unset (as on this dev Railway), customers get a broken review link.
**Fix:** Fail-closed if env var unset; update to the real Google Business Profile short-link.
**Status:** Fallback URL unchanged (`services/appointment_service.py:1660`).

---

## MEDIUM

### M-1 — `JobService.VALID_TRANSITIONS` omits TO_BE_SCHEDULED→COMPLETED and SCHEDULED→COMPLETED  `[OPEN]`
**File:** `src/grins_platform/services/job_service.py:69-86`
`complete_job` endpoint calls `update_status(COMPLETED)` directly; if the job is still TO_BE_SCHEDULED/SCHEDULED, the transition is rejected. Matches E-BUG-G symptom.
**Fix:** Add both edges, or fast-forward via IN_PROGRESS in one transaction.
**Status:** Map still routes those states only through IN_PROGRESS (`services/job_service.py:69-86`).

### M-2 — `clear_on_site_data` resets `job.payment_collected_on_site = False` — destroys legitimate collected state  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:188-189`
A job with multiple appointments (one paid, one cancelled later) loses the `payment_collected_on_site` flag. Subsequent complete checks mis-fire the payment warning.
**Fix:** Only clear when no sibling invoice/payment evidence remains.
**Status:** Unconditional clear still present (`services/appointment_service.py:161`).

### M-3 — `_handle_needs_review` overwrites `requested_alternatives` on every inbound  `[OPEN]`
**File:** `src/grins_platform/services/job_confirmation_service.py:321-329`
Customer sends "Tue 2pm" then "or Wed morning" — second reply clobbers first.
**Fix:** Append to list: `{"messages":[...]}`.
**Status:** Still a direct assignment (`job_confirmation_service.py:329`).

### M-4 — `JobGenerator.generate_jobs` anchors on `now.year` — November onboards get April jobs scheduled in the past  `[OPEN]`
**File:** `src/grins_platform/services/job_generator.py:131-132`
If onboarded in Nov 2026, Spring Startup is scheduled for April 2026 (past).
**Fix:** If computed start month < current month and no explicit preference, advance to next year.
**Status:** No year-rollover logic added (`services/job_generator.py:131-132`).

### M-5 — `Lead.phone` stored in multiple formats; `SmsConsentRecord` is E.164 only; some Lead rows miss consent resolution  `[OPEN]`
**File:** `src/grins_platform/services/sms/consent.py:138-145`
`_phone_variants` handles E.164 and bare-10-digit. Hyphenated / parenthesized forms present in Lead rows fall through.
**Fix:** Normalize to E.164 on Lead write + migration.

### M-6 — `create_appointment` unconditionally overrides `status=DRAFT` even when caller sends a status  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:305-313`
Fine for the UX-driven path but blocks admin bulk-import paths that want to create already-confirmed appointments.
**Fix:** `status = data.status or AppointmentStatus.DRAFT`.
**Status:** Still hard-coded to DRAFT (`services/appointment_service.py:283`).

### M-7 — `_has_payment_or_invoice` returns True when `invoice_repository is None` — silent bypass if DI is misconfigured  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:1919-1924`
Most callers inject the repo; any future path without it silently disables the gate. Req 36 breach potential.
**Fix:** Raise `RuntimeError` instead.
**Status:** Guard still returns True when repo is None (`services/appointment_service.py:1950-1952`).

### M-8 — `bulk_send_confirmations` flips DRAFT→SCHEDULED even when SMS was deferred (rate-limited)  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:918-928`
Counter says "sent"; appointment says "customer notified"; in reality the SMS is still queued. If the queue later drops it, the appointment is stuck in SCHEDULED with nothing sent and no visible retry.
**Fix:** Only flip when success=True and deferred is False.
**Status:** Transition still unconditional inside the try block (`services/appointment_service.py:961`).

### M-9 — `_send_confirmation_sms` silently returns when customer has no phone; `send_confirmation` still transitions DRAFT→SCHEDULED  `[OPEN]`
**File:** `src/grins_platform/services/appointment_service.py:856-863, 944-967`
Appointment claims "customer notified" but nothing was sent — no admin signal.
**Fix:** Raise `CustomerHasNoPhoneError`; surface to UI; keep DRAFT.
**Status:** Silent return retained; caller still transitions (`services/appointment_service.py:1006-1007` and 961).

### M-10 — `advance_status` allows `send_estimate → pending_approval` without a SignWell document ID  `[OPEN]`
**File:** `src/grins_platform/services/sales_pipeline_service.py:114-147`
`/sign/email` endpoint gates on doc presence, but manual pipeline advance doesn't. Admin can skip the actual signing step.
**Fix:** Gate the service-level transition on `signwell_document_id is not None`.
**Status:** No document gate on service-level advance.

### M-11 — Cancellation message formatting may crash on Windows due to `%-I` strftime token  `[OPEN]`
**File:** `src/grins_platform/services/job_confirmation_service.py:281-284`
Posix-only format specifier. Backend likely runs on Linux so not an acute issue, but dev on Windows breaks.
**Fix:** `.strftime("%I:%M %p").lstrip("0")`.

### M-12 — Phone-fuzzy parsing missing synonyms (yeah/yup/ok/1/2/3)  `[OPEN]`
See H-1. Includes poll replies — instructions Section 9 allow numbered poll options.

### E-BUG-A — Public form gives no user feedback on submit (success or failure)  `[OPEN]`
Even when submission would succeed, the user sees no "Thanks, we'll be in touch" banner or redirect. Compounds BUG-B because the customer can't tell their lead was saved.

### E-BUG-E — Leads table "Job Requested" column is empty for manually-added leads  `[OPEN]`
Situation is captured in the Add Lead modal and persisted, but not surfaced in the list view. Admins must open the row to see the request type.

---

## LOW / UX

_All LOW/UX findings remain `[OPEN]` — current remediation scope was CRITICAL + HIGH only._

### L-1 — `job_type` slugs render poorly ("hoa_irrigation_audit" → "Hoa Irrigation Audit")  `[OPEN]`
`src/grins_platform/services/job_confirmation_service.py:253-262`. Maintain display-name map.

### L-2 — On-My-Way timestamp is persisted before SMS is attempted — stale timestamp survives SMS failure  `[OPEN]`
`src/grins_platform/api/v1/jobs.py:1245-1271`. Wrap in a try/except and rollback.

### L-3 — `cancel_appointment` returns 204 even if `clear_on_site_data`'s internal writes fail silently  `[OPEN]`
`src/grins_platform/services/appointment_service.py:192-208`. Log and surface.

### L-4 — Confirmation SMS lacks service type ("for your Spring Startup"); cancellation SMS includes it (Req 15). Asymmetric.  `[OPEN]`
`src/grins_platform/services/appointment_service.py:990-993`.

### L-5 — `GOOGLE_REVIEW_URL` fallback points at a plural-slug URL likely 404 (see X-1).  `[OPEN]`

### L-6 — `bulk_send_confirmations` conflates "sent" vs "deferred" (see M-8).  `[OPEN]`

### L-7 — `_touch_lead_last_contacted` returns early on masked phone — inbound Y/R/C never updates Last Contacted  `[OPEN]`
`src/grins_platform/services/sms_service.py:498-516, 556-557`. Resolve real phone first.

### L-8 — `SalesEntry.job_type` falls back to `lead.situation` slug — Pipeline list shows "new_system" not "System Installation"  `[OPEN]`
`src/grins_platform/services/lead_service.py:1048`.

### L-9 — `complete_job` force path audit-logs `job.complete_without_payment`; invoice-skip path does not  `[OPEN]`
`src/grins_platform/api/v1/jobs.py:1138-1152`. Flag for audit.

### L-10 — Sales→Job conversion doesn't write a `sales_entry_id` back-ref on the created Job  `[OPEN]`
`src/grins_platform/services/sales_pipeline_service.py:277-314`. Pipeline-to-job trace requires fuzzy matching today.

### L-11 — Inbound Y/R/C `_touch_lead_last_contacted` called with raw masked `from_phone` at top of `handle_inbound` — wrong phone.  `[OPEN]`
See L-7.

### L-12 — `clear_on_site_data` only handles SCHEDULED→TO_BE_SCHEDULED revert; IN_PROGRESS jobs whose last appointment is cancelled become orphaned without warning  `[OPEN]`
`src/grins_platform/services/appointment_service.py:202-208`.

### L-13 — Phone normalizer's 555-01XX check compares wrong digit slice  `[OPEN]`
`src/grins_platform/services/sms/phone_normalizer.py:67-70`. Low risk; minor correctness.

### L-14 — `_try_confirmation_reply` calls `svc._find_confirmation_message` (private) — encapsulation leak.  `[OPEN]`
`src/grins_platform/services/sms_service.py:733`.

### E-BUG-F — Google Review second-click error message is uselessly generic  `[OPEN]`
Frontend shows "Failed to send review request" on dedup block. Should say "Already sent within last 30 days".

### E-BUG-H — Add Lead modal Situation dropdown is missing job types (Winterization, Seasonal Maintenance)  `[OPEN]`
Only New System, Upgrade, Repair, Exploring. Prevents exercising the no-warning-modal path via the manual Add Lead form.

### E-BUG-I — Customer detail tab set diverges from spec  `[OPEN]`
Expected: Overview / Jobs / Invoices / Communications / Documents / Timeline. Actual: Overview / Photos / Invoice History / Payment Methods / Messages / Potential Duplicates / Internal Notes. Either spec or UI needs to catch up.

### E-BUG-J — Sidebar "Leads N" counter lags the table total after rapid add/delete until page refresh.  `[OPEN]`

---

## Pleasant surprises (verified working)

- `ck_jobs_status` and `ck_appointments_status` CHECK constraints are current (migrations `20260414_100000` and `20260414_100100`) — all nine appointment statuses including `draft` and the five job statuses including `scheduled` are allowed.
- **Req 6 warning modal** (requires_estimate → Move to Jobs): E2E confirmed — dialog shows "Cancel / Move to Sales / Move to Jobs" as three options. The chosen path is honored end-to-end (Sales entry created, or Job with amber "Estimate Needed" badge).
- **Req 9 signing gating**: E2E confirmed — both "Email for Signature" and "Sign On-Site" buttons are disabled on a Sales entry with no uploaded document.
- **Req 10 estimate calendar auto-advance**: E2E confirmed — `Schedule Estimate` click opens the calendar event dialog pre-filled; saving auto-advances Sales status to "Estimate Scheduled".
- **Req 18 appointment Edit wiring**: E2E confirmed — detail modal → Edit → form pre-populated with date/time/job/notes; save updates calendar.
- **Req 11 jobs-tab quick-action "Schedule" button**: E2E confirmed — opens appointment form pre-filled.
- **Req 7 Prepaid badge + hidden payment buttons for service-agreement jobs**: E2E confirmed — job detail renders "Covered by Premium — no payment needed" and hides Create Invoice / Collect Payment.
- **Draft mode visual state / Send-All badge**: E2E confirmed — newly created appointments surface the "Send All Confirmations 1" badge at the top of the Schedule view.
- **`clear_on_site_data`** correctly deletes `ON_MY_WAY` sent-message dedup rows and resets appointment timestamps (Req 2.1-2.5 implemented faithfully — it's only `cancel_appointment`'s *ordering* that's broken — see CR-2).
- **Tier → service count mapping** correct in `job_generator.py:24-43` (Essential=2, Professional=3, Premium=7).
- **Campaign-scoped dedup** for `APPOINTMENT_CONFIRMATION` is correctly per-appointment (bugfix #4 from April-7 holds).
- **Test-phone allowlist** (`SMS_TEST_PHONE_ALLOWLIST=+19527373312`) is enforced in `callrail_provider.send_text` before any network I/O (`base.py:65-93`), with production no-op when unset.
- `requires_estimate` warning modal at the service level returns `LeadMoveResponse(requires_estimate_warning=True)` when `force=False` (Req 6.1) and audit-logs the override when `force=True` (Req 6.2).
- `convert_to_job` gated on `signwell_document_id` unless forced (Req 16.1); `force_convert_to_job` writes audit.
- Alert deep-link highlight pattern is supported via `?highlight=<id>` in `AlertCard.tsx` and honored by the target pages.

---

## SMS sends triggered during the E2E run (verify on +19527373312)

All of these were triggered from the CRM during the walkthrough. Because CR-6 shows `on_my_way` and `request_google_review` use a NullProvider by default, the last two below are the acid test — if they did **not** arrive on the phone, CR-6 is confirmed live in prod-dev.

| # | Approx. time (CT) | Event | What customer should see |
|---|---|---|---|
| 1 | ~11:34 | Confirmation SMS for appointment `7e923ed8…` (Wed 4/15 10:00–12:00) | "Your appointment on 2026-04-15 has been scheduled between 10:00 AM and 12:00 PM. Reply Y to confirm, R to reschedule, or C to cancel." |
| 2 | ~11:37 | Reschedule SMS for same appointment (time shifted to 11:00–13:00 via Edit modal) | Should say rescheduled to new time. If it says "APPOINTMENT_CONFIRMATION"-looking text, confirms BUG-CR-10 dedup collision risk. |
| 3 | ~11:39 | On-My-Way SMS for job `0b37884e-…` | "We're on our way! Your technician is heading to your location now." |
| 4 | ~11:41 | Google Review SMS for job `0b37884e-…` | "Thanks for choosing Grins Irrigation! We'd appreciate a quick review: <URL>" |

**To fully validate Y/R/C routing** (per user ask), please reply to the confirmation SMS (#1) with:

- **`Y`** — expected: appointment → CONFIRMED + auto-reply "Your appointment has been confirmed. See you on [date] at [time]!" arrives back. **If no auto-reply arrives, BUG-CR-3 is confirmed live.**
- Then from a fresh confirmation SMS, reply **`R`** — expected: appointment → reschedule request created + "We've received your reschedule request..." ack arrives + follow-up "Please reply with 2-3 dates and times..." arrives. Same caveat re: CR-3.
- Then **`C`** — expected: appointment → CANCELLED + "Your [service] appointment on [date] at [time] has been cancelled. If you'd like to reschedule, please call us at [business phone]." arrives. Same caveat re: CR-3.
- Reply with a synonym like **`ok`** or **`yeah`** — expected to NOT parse (see H-1). Should hit the "needs review" queue.

After you reply, check the Schedule view on the dev CRM to verify the appointment's status flipped as expected.

---

## Cleanup

Test records created and left behind (attached to the pre-existing "Kirill Rakitin" customer — do NOT delete the customer):

- Jobs under Kirill Rakitin:
  - `0b37884e-4a27-485a-b79a-55589e664a21` — BH0414-C1 New System (Complete)
  - BH0414-B1 Small Repair (To Be Scheduled)
  - BH0414-A1 Upgrade (To Be Scheduled, Estimate Needed badge)
- Sales entry: `dd10f5cb-8707-4b38-851a-d687d196bcc4` — BH0414-A1 Upgrade, status "Send Estimate"
- Appointment `7e923ed8…` auto-completed with job; no longer on calendar.

No admin-visible "Delete Job" affordance exists today — recommend either (a) clearing via a backend script, or (b) marking the two open jobs Cancelled and the Sales entry Closed-Lost.

---

## Appendix — Spec coverage snapshot

Requirements from `smoothing-out-after-update2` validated in this run:

| Req | Status | Notes |
|---|---|---|
| 1 Google Review SMS | ✅ CR-6 fixed (SMSService default provider is now `get_sms_provider()`). Real CallRail network call now dispatched. |
| 2 Cancellation on-site cleanup | ✅ Helper works; CR-2 fixed — `cancel_appointment` now captures `pre_cancel_status` before flip, SMS branch fires, admin opt-out dialog added. |
| 3 On-site status progression | ✅ CR-1 + CR-7 fixed — service uses canonical `VALID_APPOINTMENT_TRANSITIONS`, `job_started` accepts SCHEDULED pre-state. |
| 4 Auth guard on mutating endpoints | ✅ CR-5 fixed — `CurrentActiveUser` guard now on DELETE appointment and all job-state endpoints (on-my-way, job_started, complete_job, create_job_invoice, add_job_note, request_google_review). |
| 5 Scheduled job status | ✅ DB constraint + UI filter + badge verified. |
| 6 Estimate warning modal | ✅ Verified E2E. |
| 7 Payment warning skip for service agreement | ✅ Verified E2E. |
| 8 Draft mode / Send Confirmation | ⚠️ UI works; M-8/M-9 still open (deferred-send + no-phone silent transitions). |
| 9 Signing uses real uploaded doc | ⚠️ Buttons disabled w/o doc; H-7 still open (wrong doc for customers with 2 pipeline entries). |
| 10 Estimate calendar ↔ Sales status | ✅ Verified E2E. |
| 11 Job selector combobox + Schedule button | ✅ Verified E2E. |
| 12 Mobile on-site view | ⚠️ `tel:` link confirmed; full-width button stack on actionable job not re-verified under mobile. |
| 13 Onboarding week picker consolidation | NOT re-tested in this run. |
| 14 Reschedule follow-up SMS | ⚠️ CR-3 fixed (now hits real phone); CR-10 fixed (dedup per-type); H-1 synonym parsing + H-3 date formatting still open. |
| 15 Detailed cancellation SMS | ✅ CR-2 + CR-10 both fixed — delivery path works; dedup now per-type. |
| 16 Stripe Tap-to-Pay | NOT tested (no live test card flow). |
| 17 Payment UI differentiation | ✅ Prepaid path verified. |
| 18 Appointment Edit wiring | ✅ Verified E2E. |
| 19 Combined status flow | ⚠️ Skip-to-complete on TB_SCHEDULED job still fails (E-BUG-G / M-1 open). |
| 20 Table horizontal scroll | ✅ Partial verify on mobile width Leads table. |
| 21 Out-of-scope items | Respected. |

---

## E2E discovery — 2026-04-14 (evening live run)

After Sprint 7 landed, a full Path A–J walkthrough was executed against the
`grins-dev-dev` Railway environment. The `Testing Procedure/` runbook
captures every step. This section records the bugs surfaced *by the E2E
itself* — tests that mock-based unit tests missed.

Convention: items that were fixed mid-run are marked `[FIXED IN E2E]` with
the commit hash; the rest are `[OPEN — E2E]`.

### E2E-1 — `ensure_property_for_lead` read the wrong Lead attribute (H-5 / H-6 regression)  `[FIXED IN E2E]` — `fc29282`

**File:** `src/grins_platform/services/property_service.py:471`-`513`

The Sprint 3 helper read `lead.job_address`, but the Lead model column is
just `address`. `getattr(lead, "job_address", None)` therefore returned
`None` for every real Lead, the helper logged `property.ensure.no_address`,
and every `move-to-sales` / `move-to-jobs` left `property_id` null — quietly
defeating the H-5 / H-6 closure.

Unit tests fed `SimpleNamespace(job_address=...)` so they happily passed
against a non-existent attribute.

**Live evidence:** B1 initially returned a sales entry with `property_id: null`;
after the fix, B1b's sales entry carried `property_id: c88841fe-…` and
`property_address: "8000 Test Property Rd, Edina, MN, 55439"`.

**Fix:** read `lead.address` throughout, rename local `job_address` →
`raw_address`, update the four test fixtures to match. 53 related unit
tests pass.

### E2E-2 — `job_confirmation_responses.status` VARCHAR(30) too narrow for `'reschedule_alternatives_received'` (35 chars)  `[FIXED IN E2E]` — `4e2708e`

**File:** `src/grins_platform/models/job_confirmation.py:64-68`

When a customer replied "Tue 2pm" (or any free-text follow-up) after R,
`_handle_needs_review` set `response.status = "reschedule_alternatives_received"`
and flushed. Postgres rejected the UPDATE with
`asyncpg.exceptions.StringDataRightTruncationError: value too long for type
character varying(30)`. The whole transaction rolled back, dropping both
the `JobConfirmationResponse` and the appended `RescheduleRequest.requested_alternatives`
entry. The CallRail webhook still returned 200 OK (our handler logs the
exception but doesn't propagate it), so the customer's reply was silently
lost.

**Why unit tests missed it:** `test_job_confirmation_service.py` uses
`AsyncMock` / `MagicMock` sessions that never validate column widths.

**Fix:** Alembic migration `20260414_100900` widens the column to VARCHAR(50).
Model column updated. Downgrade included but flagged unsafe once a
new-length value has been written.

### E2E-3 — H-2 idempotency is half-fixed: duplicate cancellation SMS on re-reply  `[OPEN — E2E]`

**File:** `src/grins_platform/services/job_confirmation_service.py:228-269`
(`_handle_cancel`)

When the customer replies `C` to an appointment that is **already
CANCELLED**, `_handle_cancel` correctly does not re-flip the status, but it
still **builds the cancellation auto-reply** and returns it, so
`sms_service._try_confirmation_reply` sends another cancellation text to
the customer. The stated Sprint 1 H-2 fix only handled the DB-transition
side.

**Live evidence:** Second `C` on the already-cancelled appt produced the
exact same "Your Monthly Visit appointment on May 11, 2026 at 9:00 AM has
been cancelled…" text again.

**Proposed fix:** short-circuit at the top of `_handle_cancel` when
`appt.status == AppointmentStatus.CANCELLED.value` — set
`response.status = "already_cancelled"` (new state to add), return an empty
`auto_reply` or a short "Your appointment is already cancelled." one-off,
and skip further DB writes. Add a unit test using a mocked session that
records the number of `provider.send_text` calls.

### E2E-4 — `customers.sms_opt_in` not flipped on STOP  `[OPEN — E2E]`

**File:** `src/grins_platform/services/sms_service.py:_process_exact_opt_out`
(around L922-L960)

After an inbound STOP (or CallRail's fallback opt-out path), a
`sms_consent_records` row is inserted with `consent_method='text_stop'`,
`consent_given=false`. That's the source of truth and correctly blocks
subsequent sends (probe returned HTTP 403 "Consent denied"). **But**
`customers.sms_opt_in` stays `true` — the denormalized mirror is stale.

This breaks any UI surface (or admin query) that trusts `customers.sms_opt_in`
at face value — the customer looks opted-in but sends silently fail.

**Proposed fix:** inside `_process_exact_opt_out`, after inserting the
consent record, `UPDATE customers SET sms_opt_in=false WHERE phone IN
(variants)`. Same treatment (true) for any opt-in path if/when the START
handler is added (see E2E-5).

### E2E-5 — No `START` / `UNSTOP` keyword handler — customers cannot self-re-subscribe  `[OPEN — E2E]`

**File:** `src/grins_platform/services/sms_service.py` (no matching handler)

STOP flow writes `consent_given=false`. There's no reverse path in code.
CallRail handles carrier-level re-opt-in when a customer replies START, but
our DB `sms_consent_records` keeps the STOP row, so our `check_sms_consent`
keeps rejecting sends even after the carrier has restored the number.

Live evidence: after the phone-holder replied `START`, our probe SMS still
returned HTTP 403 "Consent denied". Only a direct DB delete of the
text_stop row restored consent on our side.

**Proposed fix:** in `handle_inbound`, after the opt-out branch, match
start/unstop keywords case-insensitively. On match:
1. `INSERT INTO sms_consent_records (..., consent_method='text_start',
   consent_given=true, consent_type='transactional')`
2. `UPDATE customers SET sms_opt_in=true WHERE phone IN (variants)`
3. Send a short "You're re-subscribed to Grins Irrigation updates."
   acknowledgment (optional — CallRail usually handles the ack).

### E2E-6 — `job_started` endpoint does not transition appointment from SCHEDULED → IN_PROGRESS  `[OPEN — E2E]`

**File:** `src/grins_platform/api/v1/jobs.py:1379-1386`

Plan F2 ("Started from SCHEDULED, skipping On My Way") expects the linked
appointment to move from SCHEDULED → IN_PROGRESS alongside the job. Current
code only accepts `EN_ROUTE` or `CONFIRMED` as the pre-state:

```python
if appointment and appointment.status in (
    AppointmentStatus.EN_ROUTE.value,
    AppointmentStatus.CONFIRMED.value,
):
    appointment.status = AppointmentStatus.IN_PROGRESS.value
```

Result: job transitions to IN_PROGRESS, appointment stays SCHEDULED —
divergent state.

**Proposed fix:** add `AppointmentStatus.SCHEDULED.value` to the accepted
set. Confirm `VALID_APPOINTMENT_TRANSITIONS` in `models/appointment.py`
already allows SCHEDULED→IN_PROGRESS (it does, per Sprint 1 CR-1).

### E2E-7 — `ManualLeadCreate` endpoint does not E.164-normalize phones  `[OPEN — E2E]`

**File:** `src/grins_platform/schemas/lead.py::ManualLeadCreate`

Sprint 6 M-5 added phone normalization on the public `LeadSubmission`
write path but not on the admin `ManualLeadCreate` path. A2 (E.164 input
`+19525550202`) stored `9525550202`; A3 (messy `(952) 737-3312`) stored
`9527373312`. Digits-only, not E.164.

Not a correctness bug in consent matching (which uses `_phone_variants`)
but creates an analytics / reporting inconsistency where the same person
can show up with different phone-value spellings.

**Proposed fix:** extend the `@field_validator("phone", mode="before")`
normalizer from `LeadSubmission` into `ManualLeadCreate`.

### E2E-8 — Inbound Y/R/C auto-replies are not logged to `sent_messages`  `[OPEN — E2E]`

**File:** `src/grins_platform/services/sms_service.py:770-810`
(`_try_confirmation_reply`)

After `JobConfirmationService.handle_confirmation` returns with
`auto_reply`, the service sends it via `self.provider.send_text(...)`
directly — bypassing `SMSService.send_message()` which writes to
`sent_messages`. Observability gap: outbound confirmation SMS are in the
audit trail, but their customer-facing acks are not.

**Live evidence:** after Y reply, the appointment was `confirmed` and
the phone received "Your appointment has been confirmed. See you then!",
but no corresponding `sent_messages` row for the customer exists. Same
pattern for R / C acks.

**Proposed fix:** route auto-replies through `SMSService.send_message()`
with `message_type=AUTOMATED_NOTIFICATION` (Sprint 1 CR-8 enum) and a
`consent_type=transactional`. Skip the consent gate for this single path
since the inbound already confirmed consent implicitly. Include the
original appointment_id + thread_id so the record is correlatable.

### E2E-9 — Railway ignoreWatchPatterns redeploys may not apply migrations  `[OPEN — INFRA]`

**Observed:** the env-var-only redeploy (2ca4582c, patchId:
`fdab2acc-...`) stayed at status `DEPLOYING` indefinitely without a
visible `Running upgrade` line in alembic's output. A force-redeploy with
`skipBuildCache: true` (cc265696) was required to actually run the
migration and flip traffic.

**Implication:** after schema-changing commits, always force a fresh
source deploy with `railway redeploy --service Grins-dev --yes` to ensure
`alembic upgrade head` executes against a fresh container.

---

## Summary — Sprint 7 + E2E outcomes

Sprint 7 landed on `dev` and the E2E verified:
- ✅ **E-BUG-C** — phone regex accepts `+`.
- ✅ **E-BUG-D** — "Merged into existing customer: {name}" toast.
- ✅ **E-BUG-F** — 409 with structured `{code, message, last_sent_at}` body.
- ✅ **E-BUG-H** — Winterization + Seasonal Maintenance accepted on leads + in `SITUATION_JOB_MAP`.
- ✅ **E-BUG-J** — dashboard summary invalidates on lead mutations.
- ✅ **L-1 / L-8** — `JOB_TYPE_DISPLAY` drives cancellation SMS + Sales pipeline list.
- ✅ **L-2** — on_my_way_at rollback verified by the negative (CallRail block) path.
- ✅ **L-14** — public `find_confirmation_message` in use.
- ✅ **M-3** — reschedule alternatives append (`requested_alternatives.entries`) — verified live with two sequential replies.
- ✅ **M-4** — JobGenerator year rollover — four direct `_resolve_dates` assertions pass.
- ✅ **M-11** — time formatter portable across platforms.

Plus two **E2E-surfaced regression fixes** landed mid-run (E2E-1, E2E-2)
and seven **new OPEN findings** documented above.

Path D/E and Path J produced real SMS on +19527373312 — bulk-send fanned
out 28 Kirill appointments with 26 sent / 2 failed-on-dedup, all per-row
statuses correctly routed DRAFT → SCHEDULED or stayed DRAFT. User's
scheduling-priority concern is addressed end-to-end.

