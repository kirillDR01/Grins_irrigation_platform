# Implementation Plan: Smoothing Out After Update 2

## Overview

This plan implements all 21 requirements across 4 domains: Bugs & Data Integrity, Workflow & Logic Gaps, UX Improvements, and Payment Feature. The architecture follows the existing Vertical Slice Architecture with Python/FastAPI backend and React/TypeScript frontend.

**Critical ordering:**
- Req 4 (auth guard) is a one-line security fix — do first
- Req 1 (Google Review SMS) and Req 2 (cancellation cleanup) are standalone bug fixes — next
- Req 3 (on-site status wiring) modifies transition tables — before Req 5 (Scheduled status)
- Req 5 (Scheduled status) and Req 8 (draft mode) change the appointment creation flow together — implement as a pair
- Req 7 (payment warning fix) is a quick win — do early in the workflow gaps phase

**Implementation languages:** Python 3.11+ (backend), TypeScript 5.9 (frontend).

**E2E validation:** Uses Vercel Agent Browser (agent-browser CLI) after each domain checkpoint. All screenshots saved to `e2e-screenshots/smoothing-out-after-update2/{domain}/`. E2E validation is iterative — if issues are found, fix and re-validate until clean.

## Tasks

### Phase 1: Bugs & Data Integrity (Req 1–4)

- [x] 1. Security Fix — Auth Guard on Job Creation Endpoint (Req 4)
  - [x] 1.1 Add `CurrentActiveUser` dependency to `POST /api/v1/jobs` endpoint
    - In `src/grins_platform/api/v1/jobs.py` (lines 515-571), add `_user: CurrentActiveUser` parameter to the `create_job` function signature
    - Verify unauthenticated requests now return HTTP 401
    - Verify authenticated requests continue to work identically
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 1.2 Write unit test for auth guard
    - Test: unauthenticated `POST /api/v1/jobs` returns 401
    - Test: authenticated `POST /api/v1/jobs` creates job normally
    - _Requirements: 4.1, 4.2_

- [x] 2. Bug Fix — Google Review SMS Actually Sends (Req 1)
  - [x] 2.1 Add `sms_service.send_message()` call to `request_google_review()`
    - In `src/grins_platform/services/appointment_service.py` (lines 1050-1134), after consent check and dedup validation, call `sms_service.send_message()` with `MessageType.GOOGLE_REVIEW_REQUEST`
    - Load the review URL from `GOOGLE_REVIEW_URL` environment variable with fallback to existing hardcoded URL `"https://g.page/r/grins-irrigations/review"`
    - Log the sent SMS in `sent_messages` table
    - Return `sent=True` with provider SID on success, `sent=False` with error on failure
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [x] 2.2 Verify existing consent and dedup guards remain intact
    - Confirm 30-day deduplication window still blocks duplicate sends
    - Confirm `sms_opt_in` consent check still prevents sends to non-consented customers
    - _Requirements: 1.3_

  - [x] 2.3 Write unit tests for Google Review SMS
    - Test: click review push → `sms_service.send_message()` is called with correct message type and review URL
    - Test: 30-day dedup blocks second send within window
    - Test: SMS consent check blocks send when `sms_opt_in = False`
    - Test: SMS send failure returns `sent=False` without crashing
    - _Requirements: 1.1, 1.3, 1.4_

- [x] 3. Bug Fix — Cancellation Clears On-Site Operations Data (Req 2)
  - [x] 3.1 Implement `clear_on_site_data()` helper function
    - Create helper in `src/grins_platform/services/appointment_service.py` that nullifies `on_my_way_at`, `started_at`, `completed_at` on appointment record
    - Delete related "On My Way" SMS send records (`sent_messages` where `appointment_id` matches and `message_type = ON_MY_WAY`) so replacement appointments can send fresh SMS
    - Clear payment/invoice warning override flags
    - If no other active appointments exist for the parent job, also nullify the same fields on the job record
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.2 Wire cleanup into appointment cancellation paths
    - Admin cancellation endpoint in `src/grins_platform/api/v1/appointments.py` — call `clear_on_site_data()` when appointment is cancelled
    - SMS "C" reply handler in `src/grins_platform/services/job_confirmation_service.py` `_handle_cancel()` (lines 217-241) — call `clear_on_site_data()` after transitioning to CANCELLED
    - Job cancellation endpoint in `src/grins_platform/api/v1/jobs.py` — clear timestamps on the job record when job is cancelled
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Write unit tests for cancellation cleanup
    - Test: cancel appointment with `on_my_way_at` set → all three timestamps are null after cancel
    - Test: cancel appointment → On My Way SMS record deleted, new appointment can send fresh On My Way
    - Test: cancel only appointment for a job → job timestamps also cleared
    - Test: cancel one of two appointments for a job → job timestamps NOT cleared (other appointment still active)
    - Test: create new appointment after cancellation → starts with all fields null, no inherited data
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [x] 4. On-Site Status Progression — Wire Buttons to Transitions (Req 3)
  - [x] 4.1 Create `get_active_appointment_for_job()` helper function
    - In `src/grins_platform/api/v1/jobs.py`, add helper that queries for the most recent non-terminal appointment for a given job (exclude COMPLETED, CANCELLED, NO_SHOW)
    - Return `None` if no active appointment exists
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 4.2 Wire "On My Way" to appointment EN_ROUTE transition
    - In `POST /api/v1/jobs/{job_id}/on-my-way` (lines 1092-1152), after existing timestamp logging and SMS send, transition the active appointment from CONFIRMED or SCHEDULED to EN_ROUTE
    - _Requirements: 3.1, 3.2_

  - [x] 4.3 Wire "Job Started" to job IN_PROGRESS and appointment IN_PROGRESS transitions
    - In `POST /api/v1/jobs/{job_id}/started` (lines 1155-1186), after logging timestamp, transition job to IN_PROGRESS and appointment from EN_ROUTE (or CONFIRMED if On My Way was skipped) to IN_PROGRESS
    - **Note:** Job → IN_PROGRESS transition was already implemented in the E2E bug fixes (Bug #7, commit cf2cee9). This task only needs to add the appointment → IN_PROGRESS transition.
    - _Requirements: 3.3_

  - [x] 4.4 Wire "Job Complete" to also complete the appointment
    - In `POST /api/v1/jobs/{job_id}/complete` (lines 912-1036), after existing job → COMPLETED transition, also transition the active appointment to COMPLETED
    - Handle skip scenario: if On My Way / Job Started were skipped, appointment goes directly to COMPLETED from whatever state it's in
    - _Requirements: 3.4, 3.7_

  - [x] 4.5 Update `VALID_APPOINTMENT_TRANSITIONS` to allow new paths
    - In `src/grins_platform/api/v1/appointments.py` (lines 29-56): add `SCHEDULED → EN_ROUTE` (for On My Way on unconfirmed appointment)
    - Verify existing paths are preserved: CONFIRMED → EN_ROUTE, EN_ROUTE → IN_PROGRESS, IN_PROGRESS → COMPLETED
    - _Requirements: 3.2, 3.5_

  - [x] 4.6 Write unit tests for on-site status progression
    - Test full happy path: On My Way → Started → Complete — verify job and appointment statuses at each step
    - Test skip scenarios: Complete without Started, Complete without On My Way, Started without On My Way
    - Test On My Way on SCHEDULED (unconfirmed) appointment → EN_ROUTE
    - Test On My Way on CONFIRMED appointment → EN_ROUTE
    - Test existing behavior preserved: timestamps still logged, SMS still sent, payment warning still works
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

- [x] 5. Bug Fix — Appointment Edit Button Not Wired Up (Req 18)
  - [x] 5.1 Add edit state management to SchedulePage.tsx
    - Add `editingAppointment: Appointment | null` state to `SchedulePage.tsx`
    - Add a handler function that receives the appointment from `AppointmentDetail`, closes the detail dialog, and opens the edit dialog with the appointment data
    - Pass this handler down to `AppointmentDetail` as an `onEdit` prop
    - _Requirements: 18.4_

  - [x] 5.2 Wire onClick handler to Edit button in AppointmentDetail.tsx
    - In `AppointmentDetail.tsx` (lines 432-440), add `onClick={() => onEdit(appointment)}` to the Edit button
    - The `onEdit` prop comes from `SchedulePage.tsx` and triggers the edit flow
    - _Requirements: 18.1_

  - [x] 5.3 Add edit dialog to SchedulePage.tsx
    - Render `AppointmentForm` in a dialog/modal when `editingAppointment` is set
    - Pass the appointment data to `AppointmentForm` via the `appointment` prop (it already supports edit mode with `isEditing = !!appointment`)
    - On form submit, call the existing `useUpdateAppointment()` mutation (`PUT /api/v1/appointments/{id}`)
    - On successful save, clear `editingAppointment`, invalidate calendar queries to refresh the view
    - On cancel, clear `editingAppointment` and re-open the detail modal
    - _Requirements: 18.1, 18.2, 18.3_

  - [x] 5.4 Write unit tests for appointment edit wiring
    - Test: clicking Edit button calls `onEdit` with the correct appointment data
    - Test: edit form opens pre-populated with appointment date, time, job, staff, notes
    - Test: saving edit calls `useUpdateAppointment()` mutation and refreshes calendar
    - Test: cancelling edit returns to detail modal without changes
    - _Requirements: 18.1, 18.2, 18.3_

- [-] 6. Checkpoint — Bugs & Data Integrity complete
  - Run all unit tests, verify they pass. Ask the user if questions arise.

- [ ] 6.1 E2E Visual Validation — Bugs & Data Integrity
  - Start backend + frontend dev servers
  - **Auth guard test (Req 4):**
    - Use agent-browser to open a private/incognito window (no auth cookie)
    - Attempt to POST to `/api/v1/jobs` via the browser console or a curl-equivalent — verify 401 response
    - Log in, then create a job normally — verify it still works for authenticated users
  - **Google Review SMS test (Req 1):**
    - Navigate to a completed job detail page
    - Click the "Google Review" button — verify the action completes (no error toast)
    - Check the communications log / sent_messages for that customer — verify an SMS with `message_type = google_review_request` was recorded
    - Click "Google Review" again within 30 days — verify dedup blocks with appropriate message
  - **Cancellation cleanup test (Req 2):**
    - Navigate to a job with a scheduled appointment
    - Click "On My Way" — verify `on_my_way_at` timestamp appears
    - Cancel the appointment — verify the timestamp disappears from the job detail view
    - Create a new appointment for the same job — verify it starts clean with no inherited timestamps
    - Click "On My Way" on the new appointment — verify it works (no dedup blocking from the old cancelled appointment's SMS)
  - **On-site status progression test (Req 3):**
    - Navigate to a job with a confirmed appointment
    - Click "On My Way" — verify appointment status changes to "En Route" on the schedule view
    - Click "Job Started" — verify job status shows "In Progress" on the jobs list, appointment shows "In Progress"
    - Click "Job Complete" — verify both job and appointment show "Completed"
    - Test skip scenario: on a different job, click "Job Complete" directly without On My Way or Started — verify it still completes
  - **Appointment edit button test (Req 18):**
    - Navigate to /schedule, click on an existing appointment to open the Appointment Details modal
    - Verify the Edit button is visible at the bottom of the modal (as shown in the screenshot)
    - Click "Edit" — verify the detail modal closes and an edit form opens, pre-populated with the appointment's current date, time, job, and staff
    - Change the appointment time (e.g., shift by 1 hour) — click Save
    - Verify the calendar updates to show the new time
    - Re-open the appointment details — verify the updated time is reflected
    - Test cancel: click Edit on another appointment, then Cancel — verify no changes were made and the detail modal re-opens
  - Check `agent-browser console` for any JS errors during all flows
  - Save all screenshots to `e2e-screenshots/smoothing-out-after-update2/bugs-data-integrity/`
  - If any visual or functional issue is found, fix it and re-validate

### Phase 2: Workflow & Logic Gaps (Req 5–10)

- [x] 7. Database Migration — Add SCHEDULED and DRAFT Enum Values (Req 5, 8)
  - [x] 7.1 Create Alembic migration `add_scheduled_and_draft_statuses`
    - Add `SCHEDULED` to `JobStatus` PostgreSQL enum (after `to_be_scheduled`)
    - Add `DRAFT` to `AppointmentStatus` PostgreSQL enum (after `pending`)
    - _Requirements: 5.8, 8.1_

  - [x] 7.2 Update Python enums in `src/grins_platform/models/enums.py`
    - Add `SCHEDULED = "scheduled"` to `JobStatus` enum between TO_BE_SCHEDULED and IN_PROGRESS
    - Add `DRAFT = "draft"` to `AppointmentStatus` enum between PENDING and SCHEDULED
    - _Requirements: 5.1, 8.1_

  - [x] 7.3 Run migration and verify
    - Run `alembic upgrade head` and verify migration applies cleanly
    - Ensure all existing tests still pass with the new enum values
    - _Requirements: 5.8, 8.1_

- [x] 8. Add "Scheduled" Job Status (Req 5)
  - [x] 8.1 Update `VALID_STATUS_TRANSITIONS` in jobs.py
    - In `src/grins_platform/api/v1/jobs.py` (lines 45-57), add:
      - `to_be_scheduled → [scheduled, in_progress, cancelled]`
      - `scheduled → [in_progress, to_be_scheduled, cancelled]` (new entry)
    - Remove `to_be_scheduled` from `in_progress` targets (use `cancelled` for that direction instead)
    - _Requirements: 5.2_

  - [x] 8.2 Auto-transition job to SCHEDULED on appointment creation
    - In the appointment creation flow (`src/grins_platform/services/appointment_service.py`), after creating the appointment, check if the linked job is in TO_BE_SCHEDULED status and transition it to SCHEDULED
    - _Requirements: 5.3_

  - [x] 8.3 Revert job to TO_BE_SCHEDULED on last appointment cancellation
    - In the cancellation cleanup logic (from task 3.2), after cancelling an appointment: if the job is in SCHEDULED status and no other active appointments exist, revert job to TO_BE_SCHEDULED
    - If other active appointments still exist, keep job as SCHEDULED
    - _Requirements: 5.4, 5.5_

  - [x] 8.4 Update Jobs tab frontend — status filter and badge
    - Add "Scheduled" to the status filter dropdown in `JobList.tsx`
    - Render "Scheduled" status badge with a distinct color (blue) in both the Jobs tab list and job detail view
    - _Requirements: 5.6, 5.7_

  - [x] 8.5 Write unit tests for Scheduled status
    - Test: create appointment → job transitions from TO_BE_SCHEDULED to SCHEDULED
    - Test: cancel only appointment → job reverts to TO_BE_SCHEDULED
    - Test: cancel one of two appointments → job stays SCHEDULED
    - Test: SCHEDULED job can transition to IN_PROGRESS (Job Started) and CANCELLED
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 9. No-Estimate-Jobs Enforcement (Req 6)
  - [x] 9.1 Add estimate warning to "Move to Jobs" backend
    - In `POST /api/v1/leads/{id}/move-to-jobs`, when the lead's situation maps to `requires_estimate`, return a `requires_estimate_warning: true` flag in the response instead of silently creating the job
    - Log the override for audit purposes if the frontend confirms "Move to Jobs" anyway
    - **Note:** The E2E bug fixes (Bug #2, commit cf2cee9) currently auto-redirect requires_estimate leads to Sales without asking. This task changes that behavior to show a warning modal with three options instead of silently redirecting. The backend `move_to_jobs()` guard in `lead_service.py` will need to be updated to return a warning flag rather than calling `move_to_sales()` directly.
    - _Requirements: 6.1, 6.2_

  - [x] 9.2 Build confirmation modal in Leads tab frontend
    - When `requires_estimate_warning` is true in the move-to-jobs response, show a confirmation modal: "This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?"
    - Three buttons: "Move to Jobs" (proceed), "Move to Sales" (redirect), "Cancel"
    - _Requirements: 6.1, 6.3_

  - [x] 9.3 Add "Estimate Needed" visual badge to Jobs tab
    - In `JobList.tsx`, add an amber/yellow "Estimate Needed" badge on jobs where `category === "requires_estimate"`
    - Also show the badge on the job detail view header in `JobDetail.tsx`
    - Add a filter option for `REQUIRES_ESTIMATE` category in the Jobs tab filter panel
    - _Requirements: 6.5, 6.6, 6.7_

  - [x] 9.4 Write unit tests for no-estimate enforcement
    - Test: lead with `requires_estimate` situation → move-to-jobs returns warning flag
    - Test: lead with normal situation → move-to-jobs proceeds without warning
    - Test: confirmed override logs audit entry
    - _Requirements: 6.1, 6.2, 6.4_

- [x] 10. Payment Warning — Skip for Service Agreement Jobs (Req 7)
  - [x] 10.1 Add service agreement check to job completion logic
    - In `POST /api/v1/jobs/{job_id}/complete` (lines 947-972), before the existing payment/invoice check, add: if `job.service_agreement_id` exists and the linked agreement is active (not expired, not cancelled), skip the warning entirely and proceed to completion
    - Updated check order: (1) active service agreement → skip, (2) payment_collected_on_site → skip, (3) any invoice exists → skip, (4) show warning
    - _Requirements: 7.1, 7.2, 7.6_

  - [x] 10.2 Add "Covered by Service Agreement" display to job detail frontend
    - When `job.service_agreement_id` is present and agreement is active, show "Covered by Service Agreement — [Agreement Name]" with a green indicator on the job detail / on-site view
    - Hide or disable "Create Invoice" and "Collect Payment" buttons for agreement-linked jobs
    - _Requirements: 7.3, 7.4_

  - [x] 10.3 Add "Prepaid" badge to Jobs tab and Schedule calendar
    - In `JobList.tsx`, add a "Prepaid" or "Agreement" green badge on service-agreement-linked jobs
    - In the Schedule tab calendar view, add a visual indicator on pre-paid appointment cards
    - _Requirements: 7.5_

  - [x] 10.4 Write unit tests for payment warning enhancement
    - Test: job with active service agreement → complete without warning (force=false succeeds)
    - Test: job with expired service agreement → payment warning still shown
    - Test: job with no service agreement, no payment, no invoice → warning shown
    - Test: job with no service agreement but invoice exists → no warning
    - Test: job with no service agreement but payment collected → no warning
    - _Requirements: 7.1, 7.2, 7.6_

- [x] 11. Schedule Draft Mode — Decouple SMS from Appointment Creation (Req 8)
  - [x] 11.1 Update `VALID_APPOINTMENT_TRANSITIONS` for DRAFT status
    - In `src/grins_platform/api/v1/appointments.py` (lines 29-56), add:
      - `pending → [draft, scheduled, cancelled]` (add draft as target)
      - `draft → [scheduled, cancelled]` (new entry entirely)
    - _Requirements: 8.14_

  - [x] 11.2 Change appointment creation to set DRAFT status
    - In `src/grins_platform/services/appointment_service.py` `create_appointment()` (line 170), change initial status from `AppointmentStatus.SCHEDULED` to `AppointmentStatus.DRAFT`
    - Remove any SMS send that currently happens during appointment creation (if any)
    - _Requirements: 8.2_

  - [x] 11.3 Implement `POST /api/v1/appointments/{id}/send-confirmation` endpoint
    - New endpoint that sends Y/R/C confirmation SMS via SMSService and transitions appointment from DRAFT to SCHEDULED
    - Reject with 422 if appointment is not in DRAFT status
    - _Requirements: 8.4, 8.12_

  - [x] 11.4 Implement `POST /api/v1/appointments/send-confirmations` bulk endpoint
    - Accepts a list of appointment IDs or a date range filter
    - Sends confirmation SMS for all DRAFT appointments in the set
    - Returns count of sent confirmations
    - _Requirements: 8.6, 8.13_

  - [x] 11.5 Implement post-send reschedule detection
    - When a SCHEDULED or CONFIRMED appointment's date/time is changed via the update endpoint, automatically send a reschedule notification SMS and reset status to SCHEDULED
    - When a DRAFT appointment is moved, do nothing (silent)
    - _Requirements: 8.8, 8.9_

  - [x] 11.6 Implement cancellation SMS logic based on appointment state
    - When a DRAFT appointment is deleted → no SMS (customer was never notified)
    - When a SCHEDULED or CONFIRMED appointment is deleted → send cancellation SMS
    - _Requirements: 8.10, 8.11_

  - [x] 11.7 Build draft mode frontend on Schedule tab
    - Add dotted border + grayed-out styling for DRAFT appointments on the calendar
    - Add "Send Confirmation" button/icon on each draft appointment card
    - Add "Send Confirmations for [Day]" button on each day column header
    - Add "Send All Confirmations" button at top of Schedule tab with count badge showing number of unsent DRAFT appointments
    - Build summary modal for "Send All Confirmations": list customer names, appointment dates, Send All / Cancel buttons
    - _Requirements: 8.3, 8.4, 8.5, 8.6, 8.7_

  - [x] 11.8 Write unit tests for draft mode
    - Test: creating appointment does NOT send SMS (status = DRAFT)
    - Test: send-confirmation sends SMS and transitions DRAFT → SCHEDULED
    - Test: bulk send sends SMS for all DRAFT appointments in range
    - Test: moving a DRAFT appointment does not send SMS
    - Test: moving a SCHEDULED appointment sends reschedule notification and resets to SCHEDULED
    - Test: deleting a DRAFT appointment does not send SMS
    - Test: deleting a SCHEDULED appointment sends cancellation SMS
    - Test: send-confirmation on non-DRAFT appointment returns 422
    - _Requirements: 8.2, 8.4, 8.6, 8.8, 8.9, 8.10, 8.11, 8.12_

- [ ] 12. Sales Pipeline — Wire Signing to Uploaded Documents (Req 9)
  - [ ] 12.1 Replace hardcoded PDF URL with real document lookup
    - In `src/grins_platform/api/v1/sales_pipeline.py` (lines 241 and 282), replace hardcoded `f"/api/v1/sales/{entry_id}/contract.pdf"` with a query to `customer_documents` for the most recent document with `document_type` in ('estimate', 'contract')
    - Generate S3 presigned URL for the found document and pass to SignWell
    - Return 422 "Upload an estimate document first" if no qualifying document exists
    - _Requirements: 9.1, 9.2, 9.4_

  - [ ] 12.2 Update signing button state in frontend
    - Disable "Send Estimate for Signature (Email)" and "Sign On-Site" buttons with tooltip "Upload an estimate document first" when no estimate/contract document exists for the entry
    - If multiple qualifying documents exist, show a dropdown to select which one to sign
    - _Requirements: 9.3, 9.5_

  - [ ] 12.3 Write unit tests for signing document wiring
    - Test: signing with uploaded document → presigned URL passed to SignWell, not placeholder
    - Test: signing without uploaded document → 422 error
    - Test: multiple documents → most recent one selected by default
    - _Requirements: 9.1, 9.2, 9.3_

- [ ] 13. Sales Pipeline — Connect Estimate Calendar to Pipeline Status (Req 10)
  - [ ] 13.1 Auto-advance sales entry on calendar event creation
    - In the sales calendar event creation endpoint, after creating the event, check if the linked `sales_entry` is at `schedule_estimate` status. If so, auto-advance to `estimate_scheduled`.
    - Do NOT advance if already at `estimate_scheduled` or later (prevent double-advance)
    - _Requirements: 10.1, 10.4_

  - [ ] 13.2 Change "Schedule Estimate" action button to open calendar form
    - In `StatusActionButton.tsx`, when current status is `schedule_estimate`, instead of calling `advance()` directly, open the calendar event creation dialog pre-filled with the sales entry's customer and property details
    - On successful event save, the backend handles the status advance
    - _Requirements: 10.2, 10.3_

  - [ ] 13.3 Write unit tests for estimate calendar sync
    - Test: create calendar event for `schedule_estimate` entry → status auto-advances to `estimate_scheduled`
    - Test: create calendar event for `estimate_scheduled` entry → no status change
    - Test: action button opens calendar form instead of just advancing
    - _Requirements: 10.1, 10.4, 10.5_

- [ ] 14. Checkpoint — Workflow & Logic Gaps complete
  - Run all unit tests, verify they pass. Ask the user if questions arise.

- [ ] 14.1 E2E Visual Validation — Workflow & Logic Gaps
  - **Scheduled job status test (Req 5):**
    - Navigate to /jobs — verify "Scheduled" appears in the status filter dropdown
    - Navigate to /schedule, create an appointment for a TO_BE_SCHEDULED job → navigate back to /jobs, verify the job now shows "Scheduled" status with blue badge
    - Cancel that appointment on the schedule → navigate back to /jobs, verify the job reverts to "To Be Scheduled"
    - Create two appointments for the same job, cancel one → verify job stays "Scheduled"
  - **No-estimate enforcement test (Req 6):**
    - Navigate to /leads, find a lead with a situation that maps to `requires_estimate` (e.g., "New System Install")
    - Click "Move to Jobs" — verify the confirmation modal appears with three options: Move to Jobs, Move to Sales, Cancel
    - Click "Move to Sales" — verify the lead moves to the Sales pipeline instead
    - On another similar lead, click "Move to Jobs" → confirm "Move to Jobs" from the modal → navigate to /jobs, verify the job has an amber "Estimate Needed" badge
    - Test the "Estimate Needed" filter in the Jobs tab — verify it shows only requires_estimate jobs
  - **Payment warning skip test (Req 7):**
    - Navigate to a job that is linked to an active service agreement (e.g., a subscription customer's Spring Startup)
    - Verify the job detail view shows "Covered by Service Agreement — [name]" with green indicator
    - Verify "Create Invoice" and "Collect Payment" buttons are hidden/disabled
    - Click "Job Complete" — verify completion proceeds immediately with NO payment warning modal
    - Navigate to a one-off job (no agreement), click "Job Complete" — verify the payment warning modal still appears
    - Navigate to /jobs — verify "Prepaid" badge is visible on agreement-linked jobs
  - **Schedule draft mode test (Req 8):**
    - Navigate to /schedule, create a new appointment — verify it appears with dotted border / grayed-out styling (DRAFT state)
    - Verify NO SMS was sent (check communications log for the customer)
    - Move the draft appointment to a different day — verify still no SMS sent
    - Click "Send Confirmation" on the draft appointment — verify SMS is sent, appointment visual changes to dashed border (SCHEDULED/unconfirmed)
    - Create 3 more draft appointments on the same day — click "Send Confirmations for [Day]" button — verify all 3 get SMS sent and change to dashed border
    - Create 5 draft appointments across multiple days — click "Send All Confirmations" — verify summary modal shows customer count, click "Send All", verify all transition to SCHEDULED
    - Move a SCHEDULED (already sent) appointment to a new day — verify a reschedule SMS is sent to the customer
    - Delete a DRAFT appointment — verify no SMS sent
    - Delete a SCHEDULED appointment — verify cancellation SMS sent
  - **Signing wiring test (Req 9):**
    - Navigate to /sales, open a sales entry detail
    - Without any documents uploaded, verify "Send for Signature" buttons are disabled with "Upload an estimate document first" tooltip
    - Upload an estimate PDF to the documents section
    - Verify "Send for Signature" buttons become enabled
    - (If SignWell keys are configured) Click "Send for Signature (Email)" — verify the real document is referenced, not a placeholder URL
  - **Estimate calendar sync test (Req 10):**
    - Navigate to /sales, find an entry at "Schedule Estimate" status
    - Click the "Schedule Estimate" action button — verify a calendar event creation dialog opens (pre-filled with customer info) instead of just flipping the status
    - Save the calendar event — verify the sales entry auto-advances to "Estimate Scheduled"
    - Navigate to the Sales Calendar — verify the event appears
  - Check `agent-browser console` for any JS errors during all flows
  - Save all screenshots to `e2e-screenshots/smoothing-out-after-update2/workflow-logic-gaps/`
  - If any visual or functional issue is found, fix it and re-validate

### Phase 3: UX Improvements (Req 11–15)

- [ ] 15. Schedule Tab — Improve Job Selector (Req 11)
  - [ ] 15.1 Verify backend returns customer data for job selector
    - Check that the jobs list endpoint used by the appointment creation form returns `customer_name`, `customer_address`, `property_tags`, and `service_preference_notes` alongside job data
    - If any fields are missing, extend the serializer/response to include them
    - **Note:** `customer_name` is already included in the dropdown display (Bug #3 fix, commit cf2cee9). This task extends it with address, tags, and preference notes.
    - _Requirements: 11.1, 11.3, 11.4, 11.5_

  - [ ] 15.2 Replace job selector dropdown with searchable combobox
    - In `AppointmentForm.tsx`, replace the plain `<select>` dropdown with a searchable combobox component
    - Format each option as: "Customer Name — Job Type (Week of M/D)"
    - Include customer address as secondary text, property tags as small badges, service preference notes as a hint line
    - Default sort by Week Of date (soonest first), with options to sort by customer name or area
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ] 15.3 Add "Schedule" quick-action button to Jobs tab
    - In `JobList.tsx`, add a "Schedule" button on each job row that is in TO_BE_SCHEDULED or SCHEDULED status
    - Clicking it opens the appointment creation form pre-filled with the job's customer, job type, and address
    - _Requirements: 11.7_

  - [ ] 15.4 Write unit tests for job selector
    - Test: job selector options include customer name as primary text
    - Test: search/filter narrows results by customer name, job type, and address
    - Test: quick-schedule from Jobs tab opens pre-filled appointment form
    - _Requirements: 11.1, 11.2, 11.7_

- [ ] 16. Mobile-Friendly On-Site Job View (Req 12)
  - [ ] 16.1 Add responsive CSS to OnSiteOperations.tsx
    - Add media queries for mobile viewport (< 768px): stack status buttons vertically, full-width, minimum 48px height
    - Position status buttons at top of page above job details on mobile (use CSS `order: -1`)
    - Ensure adequate spacing between buttons to prevent accidental taps
    - _Requirements: 12.1, 12.2_

  - [ ] 16.2 Add mobile-friendly enhancements to JobDetail.tsx
    - Add `capture="environment"` to photo upload file input for camera access on mobile
    - Render customer phone number as a `tel:` link for tap-to-call
    - Ensure payment warning modal is properly sized and dismissable on mobile viewports
    - Display customer name, address, property tags, and job type above the fold on mobile
    - Use `font-size: 16px` on inputs to prevent iOS auto-zoom
    - _Requirements: 12.3, 12.4, 12.5, 12.6, 12.7_

- [ ] 17. Onboarding — Consolidate Week Selection (Req 13)
  - [ ] 17.1 Wire WeekPickerStep to tier-correct service lists
    - Ensure `WeekPickerStep.tsx` (in `frontend/src/features/portal/components/`) receives the correct service list from `services_with_types` based on the customer's selected tier
    - Essential = 2 pickers (Spring Startup, Fall Winterization), Professional = 3, Premium = 7
    - Verify each picker is restricted to valid month ranges via existing `SERVICE_MONTH_RANGES`
    - _Requirements: 13.2, 13.3, 13.4_

  - [ ] 17.2 Add "No preference" option and remove duplicate preference UI
    - Add a "No preference" / "Assign for me" option per week picker that leaves `service_week_preferences` as null for that service
    - Remove or demote the general `preferred_schedule` (ASAP / 1-2 Weeks / 3-4 Weeks) selector if it exists in the onboarding flow
    - Verify only one week picker component is used (no duplicate `ServiceWeekPreferences.tsx` in platform frontend)
    - _Requirements: 13.1, 13.5, 13.6_

  - [ ] 17.3 Write unit tests for tier mapping
    - Test: Essential tier shows exactly 2 pickers (spring startup, fall winterization)
    - Test: Professional tier shows exactly 3 pickers (+ mid-season)
    - Test: Premium tier shows exactly 7 pickers (+ monthly visits May-Sep)
    - Test: no service appears twice, no extra pickers for lower tiers
    - _Requirements: 13.2, 13.7_

- [ ] 18. Reschedule Follow-Up SMS (Req 14)
  - [ ] 18.1 Add follow-up SMS to `_handle_reschedule()` in JobConfirmationService
    - In `src/grins_platform/services/job_confirmation_service.py` `_handle_reschedule()` (lines 187-215), after creating the reschedule request and sending the initial acknowledgment, send a second follow-up SMS: "We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up."
    - _Requirements: 14.1, 14.2_

  - [ ] 18.2 Capture customer reply in `requested_alternatives` field
    - When the customer replies to the follow-up SMS with alternative times, capture the raw reply text in the `requested_alternatives` JSONB field on the reschedule request record
    - Display the customer's suggestions in the Reschedule Requests admin queue
    - _Requirements: 14.3, 14.4_

  - [ ] 18.3 Write unit tests for reschedule follow-up
    - Test: "R" reply → acknowledgment sent + follow-up SMS sent (two SMS total)
    - Test: customer follow-up reply → captured in `requested_alternatives` field
    - _Requirements: 14.1, 14.3_

- [ ] 19. Cancellation Confirmation SMS — Include Details (Req 15)
  - [ ] 19.1 Update cancellation auto-reply in `_handle_cancel()`
    - In `src/grins_platform/services/job_confirmation_service.py` `_handle_cancel()` (lines 217-241), replace the generic "Your appointment has been cancelled. Please contact us if you'd like to reschedule." with detailed message including service type, original date/time, and business phone from `BUSINESS_PHONE_NUMBER` env var
    - Format: "Your [service type] appointment on [date] at [time] has been cancelled. If you'd like to reschedule, please call us at [business phone]."
    - _Requirements: 15.1, 15.2, 15.3_

  - [ ] 19.2 Write unit test for cancellation SMS details
    - Test: "C" reply → cancellation SMS includes service type, date, time, and business phone
    - _Requirements: 15.1, 15.2_

- [ ] 20. Table Horizontal Scroll Fix (Req 20)
  - [ ] 20.1 Fix shared table container overflow
    - In `frontend/src/components/ui/table.tsx`, change the table container wrapper class from `overflow-hidden` to `overflow-x-auto`
    - Verify rounded corners, shadow, and border styling are preserved after the change
    - _Requirements: 20.1, 20.4_

  - [ ] 20.2 Verify fix across all table views
    - Test on the Leads tab (12 columns) — verify horizontal scroll works and action buttons on the far right are reachable
    - Test on the Jobs tab — verify scroll appears only when needed
    - Test on the Invoices tab — verify same behavior
    - Test on wide viewport — verify no horizontal scrollbar appears when all columns fit
    - _Requirements: 20.2, 20.3, 20.5_

- [ ] 21. Checkpoint — UX Improvements complete
  - Run all unit tests, verify they pass. Ask the user if questions arise.

- [ ] 21.1 E2E Visual Validation — UX Improvements
  - **Job selector test (Req 11):**
    - Navigate to /schedule, click to create a new appointment
    - Verify the job selector is a searchable combobox (not a plain dropdown)
    - Type a customer name — verify the list filters to show only matching jobs
    - Verify each option shows: "Customer Name — Job Type (Week of M/D)" with address and property tags
    - Select a job — verify the form is populated with the correct data
    - Navigate to /jobs, find a TO_BE_SCHEDULED job — verify a "Schedule" quick-action button is present
    - Click "Schedule" — verify the appointment creation form opens pre-filled with that job's customer, type, and address
  - **Mobile view test (Req 12):**
    - Use agent-browser to set viewport to mobile (375x812)
    - Navigate to a job detail page — verify status buttons (On My Way, Job Started, Job Complete) are stacked vertically, full-width, at the TOP of the page above job details
    - Verify each button is at least 48px tall with adequate spacing
    - Verify customer phone number is a clickable `tel:` link
    - Verify the "Add Photo" button triggers correctly (input has camera capture attribute)
    - Verify the payment warning modal fits within the mobile viewport and is dismissable without horizontal scrolling
    - Verify customer name, address, property tags, job type are all visible without scrolling past the action buttons
    - Take screenshots at 375x812 (iPhone), 390x844 (iPhone 14), and 768x1024 (tablet) for comparison
  - **Onboarding week picker test (Req 13):**
    - Navigate to the onboarding flow (if accessible in dev) or portal page
    - Select the Essential tier — verify exactly 2 week pickers appear (Spring Startup, Fall Winterization)
    - Switch to Professional tier — verify exactly 3 pickers appear (+ Mid-Season Inspection)
    - Switch to Premium tier — verify exactly 7 pickers appear (+ monthly visits May-Sep)
    - Verify each picker is restricted to valid month ranges (can't select June for Spring Startup)
    - Verify "No preference" option is available on each picker
    - Verify no duplicate preference UI (no general ASAP / 1-2 Weeks selector competing)
  - **Reschedule follow-up SMS test (Req 14):**
    - If testable: simulate a customer "R" reply to a confirmation SMS
    - Verify TWO SMS messages are sent: the initial acknowledgment AND the follow-up asking for alternative times
    - Check the reschedule requests queue — verify the request appears with any customer alternatives populated
  - **Cancellation SMS details test (Req 15):**
    - If testable: simulate a customer "C" reply to a confirmation SMS
    - Check the sent_messages log — verify the cancellation SMS includes service type, date, time, and business phone number (not just the generic "Your appointment has been cancelled")
  - **Table horizontal scroll test (Req 20):**
    - Resize the browser window to a narrow width (e.g., 1024px or less) where the Leads tab columns would overflow
    - Navigate to /leads — verify a horizontal scrollbar appears on the table
    - Scroll right — verify the Source column and action buttons (Move to Jobs, Move to Sales, Delete) are reachable
    - Click an action button on the far right — verify it works normally
    - Resize back to full width — verify the horizontal scrollbar disappears (no scrollbar when all columns fit)
    - Navigate to /jobs — verify the same scroll behavior works on the Jobs table
    - Navigate to /invoices — verify the same scroll behavior
    - Verify the table container still has rounded corners, shadow, and border styling (no visual regression)
  - Check `agent-browser console` for any JS errors during all flows
  - Save all screenshots to `e2e-screenshots/smoothing-out-after-update2/ux-improvements/`
  - If any visual or functional issue is found, fix it and re-validate

### Phase 4: Payment Feature (Req 16–17)

- [ ] 22. Stripe Tap-to-Pay Integration (Req 16)
  - [ ] 22.1 Create StripeTerminalService backend
    - Create `src/grins_platform/services/stripe_terminal.py`
    - `create_connection_token() -> str` — Stripe Terminal connection token for frontend SDK
    - `create_payment_intent(amount_cents, currency, description) -> PaymentIntent` — create PaymentIntent with `card_present` payment method type
    - _Requirements: 16.6, 16.7_

  - [ ] 22.2 Create Stripe Terminal API endpoints
    - `POST /api/v1/stripe/terminal/connection-token` — returns connection token (requires auth)
    - `POST /api/v1/stripe/terminal/create-payment-intent` — creates PaymentIntent with amount, currency, and capture_method
    - Both endpoints require `CurrentActiveUser`
    - _Requirements: 16.2, 16.6, 16.7_

  - [ ] 22.3 Integrate Stripe Terminal SDK in PaymentCollector.tsx
    - Add Stripe Terminal JavaScript SDK to the frontend
    - Split "Collect Payment" into two paths: "Pay with Card (Tap to Pay)" and "Record Other Payment"
    - "Pay with Card" flow: create PaymentIntent → discover reader (tap_to_pay method) → collect payment → confirm → record on invoice as PAID with `payment_method: stripe_terminal`
    - "Record Other Payment" retains existing manual form for cash, check, venmo, zelle
    - _Requirements: 16.1, 16.3, 16.4, 16.5_

  - [ ] 22.4 Add Stripe Terminal configuration
    - Read `STRIPE_TERMINAL_LOCATION_ID` from environment variable
    - Configure terminal location for reader discovery
    - _Requirements: 16.8_

  - [ ] 22.5 Add receipt offering after successful payment
    - After a successful tap-to-pay charge, show option to send SMS or email receipt
    - _Requirements: 16.9_

  - [ ] 22.6 Write unit tests for Stripe Terminal
    - Test: connection token endpoint returns valid token
    - Test: PaymentIntent creation with correct amount and payment_method_types
    - Test: successful payment recorded on invoice as PAID with stripe_terminal method
    - _Requirements: 16.2, 16.4, 16.6, 16.7_

- [ ] 23. Payment UI Differentiation (Req 17)
  - [ ] 23.1 Implement conditional payment section on job detail view
    - Service agreement job: show "Covered by [Agreement Name] — no payment needed" with green checkmark, hide invoice/payment buttons
    - One-off job, no invoice: show both "Create Invoice" and "Collect Payment" buttons
    - One-off job, invoice sent: show "Invoice #[number] — Sent on [date], $[amount]" with status badge, keep "Collect Payment" available
    - One-off job, paid on-site: show "Payment collected — $[amount] via [method]" with green checkmark
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

  - [ ] 23.2 Add pre-paid indicator to Schedule tab calendar view
    - On the Schedule tab calendar, add a visual indicator (badge or icon) on pre-paid appointment cards so the admin can see which appointments need payment collection during the day's route
    - _Requirements: 17.5_

  - [ ] 23.3 Write unit tests for payment UI differentiation
    - Test: job with active agreement → "Covered" display, no payment buttons
    - Test: job with no agreement, no invoice → both buttons shown
    - Test: job with invoice sent → invoice details shown with badge
    - Test: job with on-site payment → payment confirmation shown
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.6_

- [ ] 24. Checkpoint — Payment Feature complete
  - Run all unit tests, verify they pass. Ask the user if questions arise.

- [ ] 24.1 E2E Visual Validation — Payment Feature
  - **Stripe Tap-to-Pay test (Req 16):**
    - Navigate to a job's on-site view that has an invoice
    - Verify the "Collect Payment" section now shows two options: "Pay with Card (Tap to Pay)" and "Record Other Payment"
    - Click "Record Other Payment" — verify the existing manual form (cash, check, venmo, zelle) still works as before
    - Click "Pay with Card (Tap to Pay)" — verify the Stripe Terminal SDK initializes (connection token requested from backend)
    - In Stripe test mode, verify the PaymentIntent is created with the correct amount
    - (If simulated reader available) Complete a test tap-to-pay — verify the invoice updates to PAID with `stripe_terminal` payment method
    - Verify receipt offering appears after successful payment
  - **Payment UI differentiation test (Req 17):**
    - Navigate to a job linked to a service agreement — verify "Covered by [Agreement Name] — no payment needed" with green checkmark
    - Verify "Create Invoice" and "Collect Payment" buttons are NOT shown for this job
    - Navigate to a one-off job (no agreement) with no invoice — verify both "Create Invoice" and "Collect Payment" buttons are visible
    - Create an invoice on that job — verify the payment section changes to show "Invoice #[number] — Sent on [date], $[amount]" with status badge
    - Verify "Collect Payment" is still available alongside the invoice info
    - Record a payment on a different one-off job — verify "Payment collected — $[amount] via [method]" with green checkmark
    - Navigate to /schedule — verify pre-paid jobs have a visible indicator (badge) on their calendar card, distinguishing them from jobs that need payment collection
    - Navigate to /jobs — verify the "Prepaid" badge is visible on agreement-linked jobs in the list
  - Check `agent-browser console` for any JS errors during all flows
  - Save all screenshots to `e2e-screenshots/smoothing-out-after-update2/payment-feature/`
  - If any visual or functional issue is found, fix it and re-validate

### Phase 5: Cross-Cutting, Property Tests, and Final Validation (Req 18–19)

- [ ] 25. Combined Status Flow Validation (Req 19)
  - [ ] 25.1 Write integration test for complete job + appointment lifecycle
    - Test the full combined flow: create appointment (DRAFT) → send confirmation (SCHEDULED) → customer confirms (CONFIRMED) → On My Way (EN_ROUTE) → Job Started (IN_PROGRESS) → Job Complete (COMPLETED)
    - Verify both job and appointment statuses at every step
    - Verify transitions happen atomically in the same database transaction
    - _Requirements: 18.1, 18.2, 18.3_

  - [ ] 25.2 Write integration test for cancellation revert scenarios
    - Test: cancel the only appointment → job reverts to TO_BE_SCHEDULED, verify no other active appointments
    - Test: cancel one of two appointments → job stays SCHEDULED
    - _Requirements: 18.4_

  - [ ] 25.3 Write integration test for skip scenarios
    - Test: Job Complete clicked directly (skipped On My Way and Job Started) → both job and appointment go to COMPLETED
    - Test: Job Started clicked (skipped On My Way) → job goes to IN_PROGRESS, appointment goes to IN_PROGRESS from CONFIRMED
    - _Requirements: 18.5_

- [ ] 26. Property-Based Tests
  - [ ] 26.1 Write PBT file `test_pbt_smoothing_out.py` with all 8 correctness properties
    - **Property 1: Job Status Transition Validity** — on-site button transitions always produce a valid next status per VALID_STATUS_TRANSITIONS
    - **Property 2: Appointment Status Transition Validity** — all transitions produce valid next status per VALID_APPOINTMENT_TRANSITIONS
    - **Property 3: Job-Appointment Status Consistency** — both transition in same transaction; if job transitions, appointment also transitions
    - **Property 4: Cancellation Cleanup Completeness** — cancelled appointments have all timestamps null; if no other active appointments, job timestamps also null
    - **Property 5: Draft Appointment SMS Silence** — creating/moving/deleting DRAFT appointments sends 0 SMS
    - **Property 6: Payment Warning Skip for Agreements** — jobs with active service_agreement_id skip payment warning on completion
    - **Property 7: Scheduled Status Revert** — cancelling last appointment reverts job to TO_BE_SCHEDULED; cancelling non-last keeps SCHEDULED
    - **Property 8: Auth Guard Enforcement** — unauthenticated POST /api/v1/jobs returns 401
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, and cross-cutting properties from Req 1-8_

- [ ] 27. Out-of-Scope Verification (Req 21)
  - [ ] 27.1 Verify excluded items are not implemented
    - Confirm no email provider integration code added (placeholder remains)
    - Confirm no SignWell API key provisioning steps in code
    - Confirm no S3 configuration steps in code
    - Confirm no Twilio implementation changes
    - Confirm no RBAC enforcement added
    - Confirm no AI routing / Generate Routes code
    - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.6_

- [ ] 28. Final Checkpoint — All domains complete
  - Ensure all 21 requirements are covered (Req 1-21), all unit tests pass, all property-based tests pass, all integration tests pass. Ask the user if questions arise.

- [ ] 29. Final Comprehensive E2E Visual Validation
  - [ ] 29.1 Run E2E Testing Playbook as regression baseline
    - Execute the full `e2e-screenshots/E2E-TESTING-PLAYBOOK.md` playbook (all 16 phases) to verify the existing customer lifecycle still works after all smoothing-out changes
    - **CRITICAL:** Use phone 952-737-3312 for ALL test leads
    - Phases that must pass without regression:
      - Phase 2: Lead → Mark Contacted → Move to Jobs (Repair) — job type should be "Small Repair"
      - Phase 3: Lead → Move to Jobs Guard (Exploring → redirects to Sales)
      - Phase 4: Lead → Move to Sales (direct)
      - Phase 5: Sales Pipeline full stage progression + Force Convert dialog
      - Phase 7: Jobs search with debounce
      - Phase 8: Job selector shows customer names in dropdown
      - Phase 9: SMS Y/R/C reply flow (requires human tester to reply at 952-737-3312)
      - Phase 10: On-site workflow — On My Way → Job Started (→ In Progress) → Job Complete (→ Completed)
      - Phase 11: Google Review SMS delivery
      - Phase 15: Dashboard alerts navigation
    - Any regression found must be fixed before proceeding
    - Save screenshots to `e2e-screenshots/smoothing-out-after-update2/playbook-regression/`

  - [ ] 29.2 Full regression E2E pass across all NEW features
    - Use agent-browser to perform a complete walkthrough of every feature implemented in this spec
    - **Full lifecycle walkthrough (with new smoothing-out features):**
      - Create a new lead → verify "Move to Jobs" shows estimate warning for appropriate lead types
      - Move a lead to Jobs → verify job created with correct status and badges
      - Navigate to /schedule → create a DRAFT appointment for the job → verify draft visual styling (dotted border, grayed out)
      - Send confirmation → verify SMS sent, appointment changes to dashed border (SCHEDULED)
      - Verify job status is now "Scheduled" on /jobs
      - Click "On My Way" → verify appointment shows "En Route" on schedule, SMS sent
      - Click "Job Started" → verify job shows "In Progress", appointment shows "In Progress"
      - Click "Job Complete" on a subscription job → verify NO payment warning (pre-paid via agreement)
      - Click "Job Complete" on a one-off job without payment → verify payment warning modal appears
      - Click "Complete Anyway" → verify completion with audit log
      - Click "Google Review" on a completed job → verify SMS sent
    - **Cancellation and rescheduling walkthrough:**
      - Create an appointment, click "On My Way" (timestamps set)
      - Cancel the appointment → verify all timestamps cleared
      - Create a new appointment for the same job → verify clean state, no inherited data
      - Send confirmation on the new appointment → verify SMS goes through (no dedup blocking from cancelled appointment)
    - **Sales pipeline walkthrough:**
      - Open a sales entry, upload an estimate document
      - Click "Send for Signature" → verify real document is used (not placeholder)
      - Click "Schedule Estimate" action → verify calendar form opens pre-filled, saving auto-advances status
    - **Payment paths walkthrough:**
      - Navigate to a service agreement job → verify "Covered by Agreement" display, no payment buttons
      - Navigate to a one-off job → verify payment buttons shown
      - Record a payment → verify "Payment collected" display
      - Verify Stripe Tap-to-Pay flow initializes (connection token, PaymentIntent creation)
    - **Cross-feature data sync:**
      - Verify job status changes reflect on both /jobs list and /schedule calendar
      - Verify appointment status changes reflect on both /schedule and job detail view
      - Verify "Prepaid" badges appear consistently across Jobs tab, Schedule tab, and job detail view
    - **Responsive layouts:**
      - Test at desktop (1440x900) — screenshot every major page modified in this spec
      - Test at tablet (768x1024) — verify no overflow or broken alignment
      - Test at mobile (375x812) — verify on-site buttons are stacked, full-width, at top; phone is tap-to-call; photo input triggers camera; payment modal fits viewport
    - **Error and console verification:**
      - Check `agent-browser console` and `agent-browser errors` on every page at every viewport
      - Verify no console errors, no uncaught exceptions, no broken network requests
    - Save all screenshots to `e2e-screenshots/smoothing-out-after-update2/final-regression/`
    - If any visual or functional issue is found, fix it and re-validate until clean

## Notes

- ALL tasks are REQUIRED — no optional tasks. Every test (unit, functional, integration, PBT, E2E) must pass.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation after each domain phase.
- Property tests validate all 8 correctness properties from the design document.
- Req 4 (auth guard) is a security fix prioritized as Task 1 before all other work.
- The Alembic migration (Task 7) must run before any status model changes.
- Req 5 (Scheduled status) and Req 8 (Draft mode) are implemented together in Phase 2 since both change the appointment creation flow.
- E2E visual validation uses Vercel Agent Browser (agent-browser CLI) after each domain checkpoint.
- All E2E screenshots are saved to `e2e-screenshots/smoothing-out-after-update2/{domain}/` for audit trail.
- E2E validation is iterative: if issues are found, fix and re-validate until clean.
- The final comprehensive E2E pass (Task 29) covers full regression across all features at multiple viewports (desktop, tablet, mobile).
- Stripe Tap-to-Pay (Req 16) requires `STRIPE_TERMINAL_LOCATION_ID` environment variable and a Stripe account with Terminal enabled.
- SMS-dependent E2E tests should verify via sent_messages log rather than actual delivery (only +19527373312 may receive real SMS during testing).
- **E2E Testing Playbook:** The full customer lifecycle regression playbook is at `e2e-screenshots/E2E-TESTING-PLAYBOOK.md`. Task 29.1 runs this playbook as a regression baseline after all smoothing-out changes. The playbook covers 16 phases including real SMS Y/R/C testing with 952-737-3312.
- **update2_instructions.md:** After all changes, verify the customer lifecycle diagram in `instructions/update2_instructions.md` Section 4 is still accurate. Update it if any status transitions, SMS flows, or routing logic changed.
