# Requirements Document

## Introduction

Smoothing Out After Update 2 addresses remaining bugs, workflow gaps, status model issues, and UX friction points discovered after the CRM Changes Update 2 implementation. This spec covers bug fixes and feature improvements only — external integration provisioning (email provider, SignWell API keys, S3 configuration, Twilio provider) is explicitly out of scope.

The work spans four areas:
1. **Bugs & Data Integrity** — Google Review SMS not sending, stale on-site data after cancellation, on-site buttons not changing statuses, unauthenticated job creation endpoint, appointment edit button not wired up
2. **Workflow & Logic Gaps** — Missing "Scheduled" job status, unestimated jobs leaking into Jobs tab, false payment warnings on subscription jobs, SMS sending coupled to appointment creation, signing using hardcoded placeholder URL, disconnected estimate calendar and sales pipeline
3. **UX Improvements** — Job selector missing customer names, mobile-unfriendly on-site view, duplicate/disconnected onboarding week pickers, missing reschedule follow-up SMS, generic cancellation confirmation SMS, table horizontal scroll clipping on small screens
4. **New Feature** — Payment flow differentiation for pre-paid, invoiced, and on-site Stripe payments (including Stripe Tap-to-Pay)

All work operates under the same single-admin login scope established in CRM Changes Update 2 (Requirement 38 of that spec).

## Glossary

- **Platform**: The Grins Irrigation CRM web application (FastAPI backend + React frontend)
- **Admin**: The single logged-in user operating the CRM
- **Job**: An approved work item that needs to be scheduled and performed
- **Appointment**: A scheduled time slot for a job, with its own status lifecycle
- **Service_Agreement**: A subscription contract linking a customer to a service package with auto-renewal
- **On-Site Operations**: The field workflow progression: On My Way -> Job Started -> Job Complete
- **Draft Appointment**: An appointment placed on the calendar but not yet communicated to the customer via SMS
- **Week_Of**: A week-level scheduling target represented by the Monday-Sunday date range of a calendar week
- **Sales_Entry**: A pipeline record in the Sales tab representing a customer who needs an estimate before job scheduling
- **Estimate Calendar**: The separate scheduling calendar within the Sales tab for estimate appointments
- **REQUIRES_ESTIMATE**: A job category indicating the job type typically needs an estimate before scheduling
- **Stripe Terminal**: Stripe's SDK for in-person card payments (tap-to-pay via phone NFC or dedicated reader)
- **PaymentIntent**: A Stripe object representing an intent to collect a specific payment amount
- **SMS_Service**: The existing messaging service using the BaseSMSProvider protocol (currently CallRail)
- **Job_Confirmation_Service**: The service orchestrating Y/R/C appointment confirmation via SMS

## Requirements

### Requirement 1: Google Review SMS — Fix Missing Send Call

**User Story:** As an admin, I want the Google Review button to actually send an SMS to the customer, so that I can request reviews after completing a job.

#### Acceptance Criteria

1. WHEN the admin clicks the "Google Review" button on the job detail view, THE Platform SHALL call `sms_service.send_message()` with message_type `GOOGLE_REVIEW_REQUEST` inside the `appointment_service.request_google_review()` function
2. THE Platform SHALL include the Google Business Profile review deep link URL in the SMS message body, loaded from the `GOOGLE_REVIEW_URL` environment variable
3. THE Platform SHALL retain the existing consent check and 30-day deduplication window — a customer SHALL NOT receive more than one Google Review SMS per 30-day period
4. WHEN the SMS is successfully sent, THE Platform SHALL return `sent=True` with the provider message SID; WHEN the SMS fails to send, THE Platform SHALL return `sent=False` with an error description
5. THE Platform SHALL log the sent review SMS in the `sent_messages` table with message_type `GOOGLE_REVIEW_REQUEST` for audit trail

### Requirement 2: Job Cancellation — Clear On-Site Operations Data

**User Story:** As an admin, I want on-site operations data (timestamps, flags) to be cleared when a job or appointment is cancelled, so that rescheduled work starts with a clean slate.

#### Acceptance Criteria

1. WHEN a job is cancelled, THE Platform SHALL reset the following fields to null on the job record: `on_my_way_at`, `started_at`, `completed_at`
2. WHEN an appointment is cancelled (via admin action or customer SMS "C" reply), THE Platform SHALL reset the following fields to null on that appointment record: `on_my_way_at`, `started_at`, `completed_at`
3. WHEN an appointment is cancelled and it was the source of the parent job's on-site timestamps, THE Platform SHALL also reset the parent job's `on_my_way_at`, `started_at`, `completed_at` to null
4. WHEN an appointment is cancelled, THE Platform SHALL clear any "On My Way" SMS send records for that appointment so that a replacement appointment can trigger a new "On My Way" SMS without deduplication blocking
5. WHEN an appointment is cancelled, THE Platform SHALL clear any payment/invoice warning override flags set during a previous completion attempt so that the new appointment's completion flow starts fresh
6. WHEN a new appointment is created for a job that had a previous cancelled appointment, THE Platform SHALL start with all on-site operation fields as null — no timestamps, flags, or SMS records SHALL carry over from the cancelled appointment

### Requirement 3: On-Site Status Progression — Wire Buttons to Status Transitions

**User Story:** As an admin, I want the "On My Way," "Job Started," and "Job Complete" buttons to actually progress both job and appointment statuses through their lifecycle, so that the system accurately reflects real-time field activity.

#### Acceptance Criteria

1. WHEN the admin clicks "On My Way", THE Platform SHALL transition the associated appointment status from CONFIRMED to EN_ROUTE (in addition to logging the `on_my_way_at` timestamp and sending the customer SMS)
2. WHEN the admin clicks "On My Way" and the appointment is in SCHEDULED status (not yet confirmed), THE Platform SHALL still allow the transition to EN_ROUTE — the transition SHALL be valid from both CONFIRMED and SCHEDULED
3. WHEN the admin clicks "Job Started", THE Platform SHALL transition the job status to IN_PROGRESS and the appointment status to IN_PROGRESS (in addition to logging the `started_at` timestamp)
4. WHEN the admin clicks "Job Complete", THE Platform SHALL transition the job status to COMPLETED and the appointment status to COMPLETED (in addition to existing payment/invoice checks and time tracking)
5. THE Platform SHALL update `VALID_APPOINTMENT_TRANSITIONS` to allow: CONFIRMED -> EN_ROUTE, SCHEDULED -> EN_ROUTE, EN_ROUTE -> IN_PROGRESS, IN_PROGRESS -> COMPLETED
6. THE Platform SHALL update `VALID_JOB_TRANSITIONS` to include: TO_BE_SCHEDULED -> IN_PROGRESS (for "Job Started" when no "Scheduled" status exists yet), and IN_PROGRESS -> COMPLETED
7. WHEN "Job Complete" is clicked without first clicking "Job Started" (skipping steps), THE Platform SHALL still allow the transition: the job goes directly from its current status to COMPLETED and the appointment goes directly to COMPLETED
8. THE Platform SHALL preserve all existing "Job Complete" behavior: payment/invoice warning check, time tracking calculation, and audit logging

### Requirement 4: Unauthenticated Job Creation Endpoint — Add Auth Guard

**User Story:** As an admin, I want the job creation endpoint to require authentication, so that unauthorized users cannot create job records.

#### Acceptance Criteria

1. THE Platform SHALL add the `CurrentActiveUser` dependency to the `POST /api/v1/jobs` endpoint, matching the authentication pattern used by all other protected endpoints
2. WHEN an unauthenticated request is made to `POST /api/v1/jobs`, THE Platform SHALL return HTTP 401 Unauthorized
3. THE Platform SHALL NOT change the behavior of the endpoint for authenticated users — all existing job creation functionality SHALL remain intact

### Requirement 5: Add "Scheduled" Job Status

**User Story:** As an admin, I want a "Scheduled" job status that indicates a job has been placed on the calendar, so that I can distinguish between jobs awaiting scheduling and jobs already assigned to a date.

#### Acceptance Criteria

1. THE Platform SHALL add a `SCHEDULED` value to the `JobStatus` enum, positioned between `TO_BE_SCHEDULED` and `IN_PROGRESS`
2. THE Platform SHALL update `VALID_JOB_TRANSITIONS` to: TO_BE_SCHEDULED -> {SCHEDULED, CANCELLED}, SCHEDULED -> {IN_PROGRESS, TO_BE_SCHEDULED, CANCELLED}, IN_PROGRESS -> {COMPLETED, CANCELLED}
3. WHEN an appointment is created on the Schedule tab for a job in TO_BE_SCHEDULED status, THE Platform SHALL automatically transition the job status to SCHEDULED
4. WHEN an appointment is cancelled and it was the job's only active appointment, THE Platform SHALL revert the job status from SCHEDULED back to TO_BE_SCHEDULED
5. WHEN an appointment is cancelled but other active appointments still exist for the same job, THE Platform SHALL keep the job status as SCHEDULED
6. THE Platform SHALL add "Scheduled" to the Jobs tab status filter options
7. THE Platform SHALL render the "Scheduled" status badge with a distinct color (suggested: blue) in both the Jobs tab and job detail view
8. THE Platform SHALL create an Alembic migration to add the SCHEDULED value to the JobStatus database enum

### Requirement 6: Enforce No-Estimate Jobs Rule in Jobs Tab

**User Story:** As an admin, I want the system to prevent unestimated jobs from entering the Jobs tab, so that only approved, ready-to-schedule work appears there.

#### Acceptance Criteria

1. WHEN a lead's situation maps to `requires_estimate` and the admin clicks "Move to Jobs", THE Platform SHALL display a confirmation modal: "This job type typically requires an estimate. Move to Jobs anyway, or move to Sales for the estimate workflow?" with "Move to Jobs", "Move to Sales", and "Cancel" buttons
2. WHEN the admin confirms "Move to Jobs" from the modal, THE Platform SHALL proceed with job creation and log the override for audit purposes
3. WHEN the admin clicks "Move to Sales" from the modal, THE Platform SHALL redirect the lead to the Sales pipeline instead
4. WHEN a job is created via `POST /api/v1/jobs` and the auto-categorization result is `REQUIRES_ESTIMATE` and no `quoted_amount` is provided, THE Platform SHALL return a warning flag in the response indicating the job may need an estimate
5. THE Platform SHALL display an "Estimate Needed" badge on jobs in the Jobs tab where `category = REQUIRES_ESTIMATE`, using an amber/yellow color to visually distinguish them from approved jobs
6. THE Platform SHALL add a filter option to the Jobs tab allowing the admin to filter by `REQUIRES_ESTIMATE` category so unestimated jobs can be identified and cleaned up
7. THE Platform SHALL add the "Estimate Needed" badge to both the Jobs list view rows and the job detail view header

### Requirement 7: Payment Warning — Skip for Service Agreement Jobs

**User Story:** As an admin, I want the "No Payment or Invoice on File" warning to not appear for jobs covered by a service agreement, so that I don't have to click "Complete Anyway" on every subscription customer's job.

#### Acceptance Criteria

1. WHEN the admin clicks "Job Complete" on a job that has an active `service_agreement_id`, THE Platform SHALL skip the "No Payment or Invoice on File" warning entirely and proceed directly to completion
2. THE Platform SHALL determine "active" service agreement by checking that the linked agreement exists, is not expired, and is not cancelled
3. WHEN a job is linked to an active service agreement, THE Platform SHALL display "Covered by Service Agreement - [Agreement Name]" on the job detail view with a green visual indicator
4. WHEN a job is linked to an active service agreement, THE Platform SHALL hide or disable the "Create Invoice" and "Collect Payment" buttons on the job detail and on-site views — there is nothing to bill
5. THE Platform SHALL display a "Prepaid" or "Agreement" badge on service-agreement-linked jobs in the Jobs tab list view and Schedule tab calendar view so the admin can see at a glance which jobs need payment handling
6. THE Platform SHALL update the job completion check logic to follow this order: (1) check service_agreement_id -> skip warning if active, (2) check payment_collected_on_site -> skip warning if true, (3) check invoice exists -> skip warning if any invoice exists (regardless of invoice status), (4) show warning only if none of the above conditions are met

### Requirement 8: Schedule Draft Mode — Decouple SMS from Appointment Creation

**User Story:** As an admin, I want to build out a schedule without triggering SMS notifications, and then send confirmations when I'm ready, so that customers only receive one accurate text about their appointment.

#### Acceptance Criteria

1. THE Platform SHALL add a `DRAFT` value to the appointment status enum, positioned before SCHEDULED
2. WHEN an appointment is created on the Schedule tab, THE Platform SHALL set its initial status to DRAFT and SHALL NOT send any SMS notification
3. THE Platform SHALL display draft appointments on the calendar with a dotted border and grayed-out styling, visually distinct from unconfirmed (dashed border, muted color) and confirmed (solid border, full color) appointments
4. WHEN the admin clicks "Send Confirmation" on a draft appointment, THE Platform SHALL send the Y/R/C confirmation SMS and transition the appointment status from DRAFT to SCHEDULED
5. THE Platform SHALL provide a "Send Confirmations for [Day]" button on each day column header that sends confirmation SMS for all DRAFT appointments on that day
6. THE Platform SHALL provide a "Send All Confirmations" button at the top of the Schedule tab that sends confirmation SMS for all DRAFT appointments in the current calendar view
7. WHEN the admin clicks "Send All Confirmations", THE Platform SHALL display a summary modal listing: the count of appointments to be notified, the customer names and appointment dates, with "Send All" and "Cancel" buttons
8. WHEN a DRAFT appointment is moved to a different day/time on the calendar, THE Platform SHALL NOT send any SMS — draft changes are silent
9. WHEN a SCHEDULED or CONFIRMED appointment's date or time is changed, THE Platform SHALL automatically send a reschedule notification SMS to the customer and reset the appointment status to SCHEDULED (unconfirmed)
10. WHEN a DRAFT appointment is deleted from the calendar, THE Platform SHALL NOT send any SMS — the customer was never notified
11. WHEN a SCHEDULED or CONFIRMED appointment is deleted from the calendar, THE Platform SHALL send a cancellation SMS to the customer
12. THE Platform SHALL create a new endpoint `POST /api/v1/appointments/{id}/send-confirmation` that sends the SMS and transitions DRAFT to SCHEDULED
13. THE Platform SHALL create a new bulk endpoint `POST /api/v1/appointments/send-confirmations` that accepts a list of appointment IDs or a date range and sends confirmations for all DRAFT appointments in the set
14. THE Platform SHALL update `VALID_APPOINTMENT_TRANSITIONS` to include: DRAFT -> SCHEDULED (on send confirmation), DRAFT -> CANCELLED (on delete)

### Requirement 9: Sales Pipeline — Wire Signing to Uploaded Documents

**User Story:** As an admin, I want the "Send for Signature" action to use the actual uploaded estimate document, so that the e-signature flow sends real documents instead of a placeholder URL.

#### Acceptance Criteria

1. WHEN the admin clicks "Send Estimate for Signature (Email)" or "Sign On-Site", THE Platform SHALL use the actual uploaded document from the Documents section instead of the hardcoded placeholder URL (`/api/v1/sales/{entry_id}/contract.pdf`)
2. THE Platform SHALL identify the document to sign by selecting the most recently uploaded document with `document_type` of `estimate` or `contract` for the given Sales_Entry
3. IF no estimate or contract document has been uploaded for the Sales_Entry, THEN THE Platform SHALL disable the "Send Estimate for Signature (Email)" and "Sign On-Site" buttons with a tooltip: "Upload an estimate document first"
4. THE Platform SHALL pass the real document content (S3 presigned URL or file bytes) to the SignWell API instead of the hardcoded placeholder path in `src/grins_platform/api/v1/sales_pipeline.py`
5. WHEN the admin has uploaded multiple estimate/contract documents, THE Platform SHALL use the most recently uploaded one by default, with an option to select a different document via a dropdown if multiple exist

### Requirement 10: Sales Pipeline — Connect Estimate Calendar to Pipeline Status

**User Story:** As an admin, I want the estimate calendar and the pipeline status to stay in sync, so that scheduling an estimate automatically advances the pipeline and vice versa.

#### Acceptance Criteria

1. WHEN a calendar event is created on the Estimate Calendar for a Sales_Entry that is in "Schedule Estimate" status, THE Platform SHALL automatically advance the Sales_Entry status to "Estimate Scheduled"
2. WHEN the admin clicks the "Schedule Estimate" action button on a Sales_Entry, THE Platform SHALL open the calendar event creation dialog pre-filled with the Sales_Entry's customer and property details, instead of just flipping the status text
3. WHEN the calendar event is saved from the pre-filled dialog, THE Platform SHALL advance the Sales_Entry status to "Estimate Scheduled" as part of the same action
4. WHEN a calendar event is created for a Sales_Entry already at "Estimate Scheduled" or later, THE Platform SHALL NOT change the status — no double-advance
5. THE Platform SHALL NOT auto-advance from "Estimate Scheduled" to "Send Estimate" based on the appointment date passing — this transition SHALL remain a manual admin action because the estimate document needs to be prepared first

### Requirement 11: Schedule Tab — Improve Job Selector for Appointment Creation

**User Story:** As an admin, I want the job selector when scheduling appointments to show customer names and be searchable, so that I can quickly find and schedule the right job.

#### Acceptance Criteria

1. THE Platform SHALL display the customer name as the primary text in each job selector option, followed by job type and Week Of date, formatted as: "John Smith - Spring Startup (Week of 4/6)"
2. THE Platform SHALL replace the plain dropdown with a searchable combobox that filters as the admin types by customer name, job type, or address
3. THE Platform SHALL include the customer's address (or at least city) in each selector option for route-based scheduling context
4. THE Platform SHALL include property tags (Residential/Commercial, HOA, Subscription) as small badges in each selector option
5. THE Platform SHALL include service preference notes (e.g., "AM only", "call before arriving") as a secondary line in each selector option when present
6. THE Platform SHALL sort jobs in the selector by Week Of date (soonest first) by default, with options to sort by customer name or area/zip code
7. THE Platform SHALL add a "Schedule" quick-action button on each job row in the Jobs tab (for jobs in TO_BE_SCHEDULED or SCHEDULED status) that opens the appointment creation form pre-filled with that job's customer, job type, and address

### Requirement 12: Mobile-Friendly On-Site Job View

**User Story:** As an admin in the field, I want the on-site job view to work well on my phone, so that I can efficiently tap through the job workflow at the customer's property.

#### Acceptance Criteria

1. WHEN the job detail / on-site view is accessed on a mobile viewport (< 768px), THE Platform SHALL stack the status progression buttons (On My Way, Job Started, Job Complete) vertically at full width and position them at the top of the page above job details
2. THE Platform SHALL make each status button a minimum of 48px tall with adequate spacing to prevent accidental taps on adjacent buttons
3. THE Platform SHALL render the "Add Photo" button with `capture="environment"` on the file input so that tapping it opens the phone's camera directly for photo capture
4. THE Platform SHALL render the customer phone number as a `tel:` link so the admin can tap to call
5. THE Platform SHALL ensure the payment warning modal ("No Payment or Invoice on File") is properly sized and dismissable on mobile viewports without requiring horizontal scrolling
6. THE Platform SHALL display customer name, address, property tags, service preference notes, and job type/Week Of above the fold on mobile (visible without scrolling past the action buttons)
7. THE Platform SHALL apply responsive CSS media queries to the existing `JobDetail.tsx` and `OnSiteOperations.tsx` components rather than creating a separate mobile view

### Requirement 13: Onboarding — Consolidate Week Selection and Fix Tier Mapping

**User Story:** As a customer going through onboarding, I want a single, clear step to pick my preferred weeks for each service, so that I don't encounter duplicate or confusing timing preference options.

#### Acceptance Criteria

1. THE Platform SHALL present a single per-service week selection step in the onboarding flow, removing any duplicate or competing timing preference UI (the general `preferred_schedule` ASAP/1-2 Weeks/3-4 Weeks selector SHALL be removed or demoted to a fallback only shown if the customer skips the week selection step)
2. THE Platform SHALL dynamically show week pickers only for the services included in the customer's selected tier: Essential = 2 pickers (Spring Startup, Fall Winterization), Professional = 3 pickers (+ Mid-Season Inspection), Premium = 7 pickers (+ Monthly Visits May-Sep)
3. THE Platform SHALL restrict each week picker to the valid month range for that service type: Spring Startup = March-May, Mid-Season Inspection = June-August, Fall Winterization = September-November, Monthly Visits = their specific month
4. THE Platform SHALL use the `services_with_types` data from the `verify-session` endpoint to drive which pickers appear, ensuring the frontend matches the backend's tier-to-service mapping
5. THE Platform SHALL consolidate to a single week picker component — either `WeekPickerStep.tsx` (platform frontend) or `ServiceWeekPreferences.tsx` (landing page) — and remove the unused duplicate
6. THE Platform SHALL provide a "No preference" or "Assign for me" option for customers who don't want to pick specific weeks, leaving `service_week_preferences` as null so the job generator falls back to default calendar-month ranges
7. THE Platform SHALL ensure no service appears twice in the week selection step and no extra pickers appear for a lower tier

### Requirement 14: Reschedule Follow-Up SMS

**User Story:** As a customer, I want to be asked for my preferred alternative times after requesting a reschedule, so that I can provide options and get rescheduled efficiently.

#### Acceptance Criteria

1. WHEN a customer replies "R" (reschedule) to a confirmation SMS, THE Platform SHALL send a follow-up SMS after the reschedule request is created, asking: "We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up."
2. THE Platform SHALL add the follow-up SMS send call in `JobConfirmationService._handle_reschedule()` after the reschedule request record is created and the initial acknowledgment reply is sent
3. WHEN the customer replies to the follow-up SMS with alternative times, THE Platform SHALL capture the reply text in the `requested_alternatives` field (JSONB) on the reschedule request record, storing the raw text for admin review
4. THE Platform SHALL display the customer's alternative time suggestions in the Reschedule Requests admin queue alongside the original appointment details

### Requirement 15: Cancellation Confirmation SMS — Include Appointment Details

**User Story:** As a customer, I want the cancellation confirmation SMS to include my appointment details and a callback number, so that I know exactly what was cancelled and how to get back in touch.

#### Acceptance Criteria

1. WHEN a customer replies "C" (cancel) and the appointment is cancelled, THE Platform SHALL send a cancellation confirmation SMS that includes: the service type, the original appointment date and time, and the business phone number for rescheduling
2. THE Platform SHALL format the cancellation SMS as: "Your [service type] appointment on [date] at [time] has been cancelled. If you'd like to reschedule, please call us at [business phone]."
3. THE Platform SHALL load the business phone number from the `BUSINESS_PHONE_NUMBER` environment variable (or existing configuration)

### Requirement 16: Payment Flow — Stripe Tap-to-Pay Integration

**User Story:** As an admin in the field, I want to collect card payments on-site via tap-to-pay on my phone, so that I can process real card charges instead of manually recording payment details.

#### Acceptance Criteria

1. THE Platform SHALL integrate the Stripe Terminal JavaScript SDK into the frontend for in-person card payment processing
2. WHEN the admin clicks "Pay with Card (Tap to Pay)" on the on-site payment view, THE Platform SHALL create a Stripe PaymentIntent via a backend endpoint for the invoice amount
3. THE Platform SHALL discover and connect to a Stripe Terminal reader using `tap_to_pay` as the discovery method (using the phone's NFC chip) or a paired Bluetooth reader
4. WHEN the customer taps their card and the charge is confirmed by Stripe Terminal, THE Platform SHALL record the payment on the invoice as PAID with `payment_method: stripe_terminal` and the Stripe PaymentIntent ID as the reference
5. THE Platform SHALL split the "Collect Payment" UI into two paths: "Pay with Card (Tap to Pay)" triggering the Stripe Terminal flow, and "Record Other Payment" retaining the existing manual form for cash, check, Venmo, and Zelle
6. THE Platform SHALL create a backend endpoint `POST /api/v1/stripe/terminal/connection-token` that returns a Stripe Terminal connection token for the frontend SDK
7. THE Platform SHALL create a backend endpoint `POST /api/v1/stripe/terminal/create-payment-intent` that creates a PaymentIntent with the specified amount, currency, and capture_method
8. THE Platform SHALL configure the Stripe Terminal Location (business address) via the `STRIPE_TERMINAL_LOCATION_ID` environment variable
9. AFTER a successful tap-to-pay charge, THE Platform SHALL offer to send an SMS or email receipt to the customer

### Requirement 17: Payment Flow — UI Differentiation Across Three Payment Paths

**User Story:** As an admin, I want the job detail and on-site views to clearly show whether a job is pre-paid, needs invoicing, or needs on-site collection, so that I immediately know the payment situation for each job.

#### Acceptance Criteria

1. WHEN a job is linked to an active service agreement, THE Platform SHALL display: "Covered by [Agreement Name] - no payment needed" with a green checkmark, and SHALL hide the "Create Invoice" and "Collect Payment" buttons
2. WHEN a job is a one-off (no service agreement) and no invoice has been created, THE Platform SHALL display both "Create Invoice" and "Collect Payment" buttons as available actions
3. WHEN a job has an invoice in sent or viewed status, THE Platform SHALL display: "Invoice #[number] - Sent on [date], $[amount]" with a status badge, and SHALL still show "Collect Payment" as available (customer may want to pay on-site instead of via the invoice link)
4. WHEN a job has payment collected on-site, THE Platform SHALL display: "Payment collected - $[amount] via [method]" with a green checkmark
5. THE Platform SHALL display a visual indicator (badge or icon) on pre-paid jobs in the Schedule tab calendar view so the admin can see which appointments need payment collection during the day's route
6. THE Platform SHALL render the payment section on the job detail / on-site view conditionally based on the job's payment path, showing only the relevant information and actions for that path

### Requirement 18: Appointment Edit Button — Wire to Edit Form

**User Story:** As an admin, I want the Edit button on the Appointment Details modal to open the appointment edit form, so that I can modify appointment date, time, and staff assignment without having to cancel and recreate.

#### Acceptance Criteria

1. WHEN the admin clicks the "Edit" button on the Appointment Details modal, THE Platform SHALL open the AppointmentForm component in edit mode, pre-populated with the current appointment's data (date, time range, job, staff member, notes)
2. THE Platform SHALL use the existing `useUpdateAppointment()` mutation hook to submit changes via `PUT /api/v1/appointments/{id}`
3. WHEN the admin saves the edited appointment, THE Platform SHALL close the edit form, refresh the calendar view to reflect changes, and re-open the Appointment Details modal showing the updated data
4. THE Platform SHALL add the necessary state management (`editingAppointmentId`, `showEditDialog`) to `SchedulePage.tsx` to support transitioning from the detail modal to the edit form and back
5. IF the appointment is in SCHEDULED or CONFIRMED status and the date or time has changed, THE Platform SHALL trigger a reschedule notification SMS (per Requirement 8, draft mode rules — only post-send appointments trigger customer notification on edit)

### Requirement 19: On-Site Status Progression — Combined Flow with Scheduled Status

**User Story:** As a developer, I want the complete job and appointment status flow documented as a single requirement, so that the combined lifecycle from Items 1, 2, and 5 (status progression, scheduled status, and draft mode) is clear and testable.

#### Acceptance Criteria

1. THE Platform SHALL support the following complete job status flow: TO_BE_SCHEDULED -> SCHEDULED (appointment created) -> IN_PROGRESS (Job Started clicked) -> COMPLETED (Job Complete clicked), with CANCELLED reachable from any non-terminal status
2. THE Platform SHALL support the following complete appointment status flow: DRAFT (created on calendar) -> SCHEDULED (confirmation SMS sent) -> CONFIRMED (customer replies Y) -> EN_ROUTE (On My Way clicked) -> IN_PROGRESS (Job Started clicked) -> COMPLETED (Job Complete clicked), with CANCELLED reachable from any non-terminal status
3. FOR ALL job status transitions triggered by on-site buttons, THE Platform SHALL transition both the job and the associated appointment in the same database transaction
4. FOR ALL appointment cancellations that revert a job to TO_BE_SCHEDULED, THE Platform SHALL verify no other active appointments exist for that job before reverting
5. THE Platform SHALL handle skip scenarios gracefully: clicking "Job Complete" without first clicking "Job Started" or "On My Way" SHALL still complete both the job and appointment, transitioning them directly to COMPLETED from whatever their current status is

### Requirement 20: Table Horizontal Scroll — Fix Clipped Columns on Small Screens

**User Story:** As an admin using a smaller screen or browser window, I want to scroll horizontally through wide tables so that I can reach all columns including actions on the far right.

#### Acceptance Criteria

1. THE Platform SHALL change the shared table container in `frontend/src/components/ui/table.tsx` from `overflow-hidden` to `overflow-x: auto`, enabling horizontal scrolling when table content exceeds the viewport width
2. WHEN the Leads tab table is wider than the viewport, THE Platform SHALL allow the admin to scroll horizontally to reach the Source column and the action buttons (Move to Jobs, Move to Sales, Delete) on the far right
3. THE Platform SHALL apply the same horizontal scroll fix to all tables that use the shared `table.tsx` component, including but not limited to: Leads, Jobs, Invoices, Customers, and Sales pipeline list views
4. THE Platform SHALL NOT break the existing rounded corners, shadow, or border styling on the table container when changing the overflow behavior
5. THE Platform SHALL ensure that on viewports wide enough to display all columns, no horizontal scrollbar appears — the scrollbar SHALL only appear when content overflows

### Requirement 21: Explicit Out-of-Scope Items

**User Story:** As a developer, I want an explicit list of items that are NOT in scope for this spec, so that I do not accidentally implement deferred or unrelated work.

#### Acceptance Criteria

1. THE Platform SHALL NOT implement email provider integration (AWS SES, SendGrid, Postmark) as part of this spec — the `_send_email()` placeholder in `email_service.py` remains as-is until a separate email integration spec is created
2. THE Platform SHALL NOT provision or configure SignWell API keys as part of this spec — the code integration is already complete, and API key provisioning is an operational task
3. THE Platform SHALL NOT provision or configure S3 buckets, credentials, or CORS as part of this spec — S3 configuration is an operational task
4. THE Platform SHALL NOT implement the Twilio SMS provider as part of this spec — CallRail is the active provider and the Twilio stub remains as-is unless a business decision is made to switch
5. THE Platform SHALL NOT implement staff/admin role-based access control as part of this spec — the single-admin scope from CRM Changes Update 2 (Requirement 38) remains in effect
6. THE Platform SHALL NOT implement AI routing / Generate Routes as part of this spec — this is being handled by a separate team
