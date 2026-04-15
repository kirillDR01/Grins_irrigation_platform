# Requirements Document — E2E Bug Hunt Fixes

## Introduction

This spec addresses 7 bugs discovered during the 2026-04-13 E2E bug hunt of the CRM admin platform. The bugs span the full admin workflow: job search (Bug #1), lead conversion (Bug #2), appointment scheduling (Bug #3), SMS reliability (Bugs #4, #5), sales pipeline feedback (Bug #6), and on-site job completion (Bug #7). Bug #7 is the highest severity — it completely blocks the field workflow since no job can be marked as completed.

**Source:** `e2e-screenshots/bug-hunt/` (7 bug report files)

## Glossary

- **JobList**: React component in `frontend/src/features/jobs/components/JobList.tsx` that renders the Jobs tab with search, filters, and pagination
- **LeadService.move_to_jobs()**: Method in `src/grins_platform/services/lead_service.py` that converts a lead to a job
- **SITUATION_JOB_MAP**: Class variable mapping lead situations to `(job_category, description)` tuples
- **AppointmentForm**: React component in `frontend/src/features/schedule/components/AppointmentForm.tsx` with the job dropdown
- **SMSService.send_message()**: Method in `src/grins_platform/services/sms_service.py` that sends SMS with dedupe logic
- **send_sms**: FastAPI endpoint in `src/grins_platform/api/v1/sms.py` that wraps `SMSService.send_message()`
- **StatusActionButton**: React component in `frontend/src/features/sales/components/StatusActionButton.tsx` handling pipeline actions including Convert to Job
- **job_started**: FastAPI endpoint in `src/grins_platform/api/v1/jobs.py` that logs the started_at timestamp
- **complete_job**: FastAPI endpoint that transitions job status to completed via `JobService.update_status()`
- **VALID_TRANSITIONS**: Class variable in `JobService` defining allowed status transitions

## Requirements

### Requirement 1: Wire Jobs Tab Search to API (Bug #1)

**User Story:** As an admin searching for jobs, I want the Jobs tab search to actually filter results, so I can find specific jobs by customer name, job type, or description.

#### Acceptance Criteria

1. WHEN a user types a search query into the Jobs tab search input THEN the system SHALL include the `search` parameter in the API request params passed to `useJobs()`, filtering the job list
2. THE search SHALL be debounced (~300ms) to avoid excessive API calls
3. WHEN the search query changes, the page SHALL reset to page 1
4. WHEN the search input is cleared, the full unfiltered job list SHALL be displayed

#### Verification

- E2E: Type "E2E Confirm" in Jobs search → results filter to matching jobs
- Unit test: `JobList` includes `search` param when search input has value

---

### Requirement 2: Guard Move-to-Jobs for requires_estimate Leads (Bug #2)

**User Story:** As a system, I want to prevent leads that require an estimate from being placed directly in the Jobs tab, so that only approved/scheduled jobs appear there.

#### Acceptance Criteria

1. WHEN a lead with a situation that maps to `requires_estimate` (e.g., "Exploring", "New System", "Upgrade") is moved to Jobs THEN the system SHALL redirect the lead to the Sales pipeline instead via `move_to_sales()`
2. WHEN a lead with an unmapped situation value is moved to Jobs THEN the system SHALL treat it as requiring an estimate and redirect to Sales
3. WHEN a lead with situation "Repair" (maps to `ready_to_schedule`) is moved to Jobs THEN the system SHALL CONTINUE TO create a job in the Jobs tab as before

#### Verification

- Unit test: `move_to_jobs()` with "Exploring" lead → redirects to sales; with "Repair" lead → creates job
- Functional test: Create lead with "Exploring" situation, move to jobs → verify sales entry created

---

### Requirement 3: Show Customer Name in Job Selector Dropdown (Bug #3)

**User Story:** As an admin scheduling an appointment, I want to see the customer name in the job dropdown, so I can identify which customer each job belongs to.

#### Acceptance Criteria

1. WHEN a user opens the "New Appointment" form job dropdown THEN each job SHALL display as `{customer_name} — {job_type} - {description}` instead of just `{job_type} - {description}`
2. THE `customer_name` field SHALL be available on job objects returned by `useJobsReadyToSchedule()`

#### Verification

- E2E: Open appointment form → job dropdown shows customer names
- Unit test: AppointmentForm renders customer name in job dropdown options

---

### Requirement 4: Scope SMS Dedupe Per Appointment (Bug #4)

**User Story:** As a system, I want each appointment to receive its own confirmation SMS, even if the same customer has multiple appointments in one day.

#### Acceptance Criteria

1. WHEN a second appointment is created for the same customer within 24 hours THEN the system SHALL scope the legacy dedupe check to include `appointment_id`, allowing each distinct appointment to receive its own confirmation SMS
2. THE campaign-scoped dedupe (campaign_id + recipient) SHALL CONTINUE TO work as before
3. THE non-appointment SMS dedupe (customer_id + message_type for `custom`, `on_the_way`, etc.) SHALL CONTINUE TO work as before

#### Verification

- Unit test: Two `appointment_confirmation` sends for different appointment_ids to same customer → both succeed
- Functional test: Create two appointments for same customer, verify both get confirmation SMS

---

### Requirement 5: Fix SMS Send Endpoint 500 on Dedupe Block (Bug #5)

**User Story:** As an admin, I want the SMS send endpoint to return a proper error response when a message is blocked by dedupe, instead of crashing with a 500.

#### Acceptance Criteria

1. WHEN `POST /api/v1/sms/send` is called and the SMS service returns a dedupe-blocked result (`success: False`) THEN the endpoint SHALL return a proper JSON response with `success: false` instead of crashing with a 500 Internal Server Error
2. THE successful SMS sends SHALL CONTINUE TO return 200 with `message_id` and `status` as before
3. THE consent-denied SMS SHALL CONTINUE TO return 403 as before

#### Verification

- Unit test: Mock `send_message()` returning dedupe-blocked result → endpoint returns proper JSON, no 500
- Integration test: Trigger dedupe block via API → verify proper response

---

### Requirement 6: Show Force-Convert Dialog on Signature Error (Bug #6)

**User Story:** As an admin clicking "Convert to Job" on a sales entry, I want to see the force-convert dialog when the backend says a signature is required, instead of nothing happening.

#### Acceptance Criteria

1. WHEN a user clicks "Convert to Job" and the backend returns a 422 SignatureRequiredError THEN the frontend SHALL correctly extract the error detail and display the force-convert confirmation dialog
2. THE error extraction SHALL use `axios.isAxiosError()` for robust handling of the Axios error structure
3. THE sales pipeline stage advancement (non-convert actions) SHALL CONTINUE TO work with toasts as before
4. THE "Mark Lost" confirmation dialog SHALL CONTINUE TO work as before

#### Verification

- Unit test: Simulate 422 error with "signature" in detail → force-convert dialog appears
- E2E: Click "Convert to Job" on "Send Contract" entry → force-convert dialog shown

---

### Requirement 7: Make Job Started Transition Status to in_progress (Bug #7, HIGH)

**User Story:** As a field crew member, I want clicking "Job Started" to actually change the job status to in_progress, so that I can subsequently mark the job as completed.

#### Acceptance Criteria

1. WHEN the "Job Started" button is clicked on a job with status `to_be_scheduled` THEN the system SHALL transition the job status to `in_progress` in addition to logging the `started_at` timestamp
2. WHEN "Job Complete" is clicked after "Job Started" has set the status to `in_progress` THEN the system SHALL successfully transition the job from `in_progress` to `completed`
3. WHEN "Job Started" is clicked on a job already at `in_progress` THEN the system SHALL handle it gracefully (idempotent)
4. THE "On My Way" button SHALL CONTINUE TO send SMS and log `on_my_way_at` timestamp as before
5. Job cancellation from `to_be_scheduled` or `in_progress` SHALL CONTINUE TO work as before
6. `completed` and `cancelled` SHALL CONTINUE TO be terminal states

#### Verification

- Unit test: Job at `to_be_scheduled` → `job_started` → status is `in_progress` → `complete_job` → status is `completed`
- E2E: On My Way → Job Started → Job Complete → all succeed without errors
