# Bugfix Requirements Document

## Introduction

Seven bugs were identified during comprehensive E2E testing of the Grins Irrigation CRM platform. These bugs span the full customer lifecycle — from lead conversion, through scheduling and SMS confirmation, to on-site job completion. The highest-severity issue (Bug #7) completely blocks the field workflow: no job can be marked as completed. Other bugs affect SMS reliability, search functionality, data display, and user feedback on errors. This document captures the defective behavior, expected corrections, and regression-prevention constraints for all seven bugs.

---

## Bug Analysis

### Current Behavior (Defect)

**Bug #1 — Jobs tab search doesn't filter results**

1.1 WHEN a user types a search query into the Jobs tab search input THEN the system captures the query in `searchQuery` state but never passes it to the API params, so the job list remains unfiltered regardless of input.

**Bug #2 — Move to Jobs creates requires_estimate job without warning**

1.2 WHEN a lead with situation "Exploring", "New System", or "Upgrade" is moved to Jobs via `move_to_jobs()` THEN the system creates a job with category `requires_estimate` directly in the Jobs tab without warning the user or redirecting to the Sales pipeline.

1.3 WHEN a lead with an unmapped situation value is moved to Jobs THEN the system defaults to `requires_estimate` category without any guard or user notification.

**Bug #3 — Job selector doesn't show customer name**

1.4 WHEN a user opens the "New Appointment" form job dropdown THEN the system displays jobs as only "{job_type} - {description}" (e.g., "spring_startup - Spring system activation and inspection") with no customer name, making it impossible to identify which customer a job belongs to.

**Bug #4 — SMS dedupe blocks second appointment confirmation**

1.5 WHEN a second appointment is created for the same customer within 24 hours THEN the system's legacy dedupe check (customer_id + message_type within 24h) blocks the confirmation SMS for the new appointment, even though it is a different appointment requiring its own confirmation.

**Bug #5 — SMS send endpoint 500s for appointment_confirmation type**

1.6 WHEN `POST /api/v1/sms/send` is called with `message_type: "appointment_confirmation"` and the dedupe check blocks the send (returning `success: False` with `recent_message_id` instead of `message_id`) THEN the endpoint crashes with a 500 Internal Server Error because it attempts `UUID(send_result["message_id"])` on a dict that lacks the `message_id` key.

**Bug #6 — Convert to Job has no visible effect**

1.7 WHEN a user clicks "Convert to Job" on a sales entry at "Send Contract" stage and the backend returns a 422 SignatureRequiredError THEN the frontend `onError` handler checks if the error message includes "signature" but the Axios error structure `err.response?.data?.detail` does not resolve correctly, so neither the force-convert dialog nor an error toast is shown — the click produces no visible feedback.

**Bug #7 — Job Complete fails due to invalid status transition**

1.8 WHEN the "Job Started" button is clicked on a job detail page THEN the system only logs a `started_at` timestamp without changing the job status from `to_be_scheduled` to `in_progress`.

1.9 WHEN "Job Complete" is clicked after "On My Way" and "Job Started" THEN the system attempts a `to_be_scheduled → completed` transition which is rejected by `VALID_TRANSITIONS`, causing a "Failed to force-complete job" error and leaving the job stuck at `to_be_scheduled`.

---

### Expected Behavior (Correct)

**Bug #1 — Jobs tab search**

2.1 WHEN a user types a search query into the Jobs tab search input THEN the system SHALL include the `search` parameter in the API request params passed to `useJobs()`, filtering the job list by customer name, job type, address, or description.

**Bug #2 — Move to Jobs guard**

2.2 WHEN a lead with a situation that maps to `requires_estimate` is moved to Jobs THEN the system SHALL redirect the lead to the Sales pipeline instead (via `move_to_sales()`), or at minimum block the move and display a warning that the lead requires an estimate first.

2.3 WHEN a lead with an unmapped situation value is moved to Jobs THEN the system SHALL treat it as requiring an estimate and redirect to Sales pipeline rather than creating a `requires_estimate` job in the Jobs tab.

**Bug #3 — Job selector customer name**

2.4 WHEN a user opens the "New Appointment" form job dropdown THEN the system SHALL display each job as "{customer_name} — {job_type} - {description}" so the user can identify which customer each job belongs to.

**Bug #4 — SMS dedupe scoping**

2.5 WHEN a second appointment is created for the same customer within 24 hours THEN the system SHALL scope the legacy dedupe check to include `appointment_id`, allowing each distinct appointment to receive its own confirmation SMS.

**Bug #5 — SMS send endpoint error handling**

2.6 WHEN `POST /api/v1/sms/send` is called and the SMS service returns a dedupe-blocked result (`success: False`) THEN the endpoint SHALL handle the non-success response gracefully, returning a proper JSON response (e.g., 200 with `success: false` or 409 Conflict) instead of crashing with a 500.

**Bug #6 — Convert to Job error feedback**

2.7 WHEN a user clicks "Convert to Job" and the backend returns a 422 SignatureRequiredError THEN the frontend SHALL correctly extract the error detail from the Axios error response and display the force-convert confirmation dialog prompting the user to force-convert or cancel.

**Bug #7 — On-site status progression**

2.8 WHEN the "Job Started" button is clicked THEN the system SHALL transition the job status from `to_be_scheduled` to `in_progress` (in addition to logging the `started_at` timestamp), enabling the subsequent `in_progress → completed` transition.

2.9 WHEN "Job Complete" is clicked after "Job Started" has set the status to `in_progress` THEN the system SHALL successfully transition the job from `in_progress` to `completed`.

---

### Unchanged Behavior (Regression Prevention)

**Bug #1 — Jobs tab**

3.1 WHEN the Jobs tab search input is empty THEN the system SHALL CONTINUE TO display the full unfiltered job list with pagination and status filtering working as before.

3.2 WHEN the Jobs tab status filter is changed THEN the system SHALL CONTINUE TO filter jobs by status correctly.

**Bug #2 — Move to Jobs**

3.3 WHEN a lead with situation "Repair" (which maps to `ready_to_schedule`) is moved to Jobs THEN the system SHALL CONTINUE TO create a `ready_to_schedule` job in the Jobs tab as before.

3.4 WHEN `move_to_sales()` is called THEN the system SHALL CONTINUE TO create a sales pipeline entry at "Schedule Estimate" status as before.

**Bug #3 — Job selector**

3.5 WHEN the JobSelector table view is used (not the dropdown) THEN the system SHALL CONTINUE TO display customer_name, job_type, city, and other columns as before.

3.6 WHEN filtering jobs by city, job type, or customer name in the JobSelector THEN the system SHALL CONTINUE TO filter correctly as before.

**Bug #4 — SMS dedupe**

3.7 WHEN a campaign-scoped SMS is sent to the same recipient within 24 hours THEN the system SHALL CONTINUE TO dedupe by campaign_id + recipient as before.

3.8 WHEN a non-appointment SMS (e.g., `custom`, `on_the_way`) is sent to the same customer with the same message_type within 24 hours THEN the system SHALL CONTINUE TO dedupe by customer_id + message_type as before.

**Bug #5 — SMS send endpoint**

3.9 WHEN `POST /api/v1/sms/send` is called with `message_type: "custom"` and the message sends successfully THEN the system SHALL CONTINUE TO return a 200 response with `success: true`, `message_id`, and `status` as before.

3.10 WHEN `POST /api/v1/sms/send` is called and consent is denied THEN the system SHALL CONTINUE TO return a 403 Forbidden error as before.

**Bug #6 — Sales pipeline**

3.11 WHEN a user advances a sales entry through stages other than "Send Contract" (e.g., Schedule Estimate → Estimate Scheduled) THEN the system SHALL CONTINUE TO advance the status and show a "Status advanced" toast as before.

3.12 WHEN a user clicks "Mark Lost" on a sales entry THEN the system SHALL CONTINUE TO show the confirmation dialog and mark the entry as lost as before.

**Bug #7 — Job status transitions**

3.13 WHEN "On My Way" is clicked THEN the system SHALL CONTINUE TO send the "We're on our way!" SMS and log the `on_my_way_at` timestamp as before.

3.14 WHEN a job is cancelled from `to_be_scheduled` or `in_progress` THEN the system SHALL CONTINUE TO allow the `→ cancelled` transition as before.

3.15 WHEN a job is at `completed` or `cancelled` status THEN the system SHALL CONTINUE TO treat these as terminal states with no further transitions allowed.
