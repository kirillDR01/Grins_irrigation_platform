# Bug Fix Tasks — E2E Bug Hunt (2026-04-13)

## Overview

Fix 7 bugs discovered during E2E bug hunt testing of the CRM admin platform. Bugs span frontend (React/TypeScript) and backend (FastAPI/Python) across the Jobs, Schedule, SMS, Sales, and Lead-to-Jobs workflows.

**Source:** `e2e-screenshots/bug-hunt/` (7 bug reports)

## Phase 1: Frontend Fixes

- [x] 1. Wire Jobs tab search to API params (Bug #1 — LOW-MEDIUM)
  - [x] 1.1 In `frontend/src/features/jobs/components/JobList.tsx`, add `searchQuery` to the `params` object passed to `useJobs()` with ~300ms debounce
  - [x] 1.2 Reset `params.page` to 1 when search query changes
  - [x] 1.3 When search is cleared, remove `search` from params so full list returns
  - _Files: JobList.tsx_

- [x] 2. Prepend customer name in job selector dropdown (Bug #3 — MEDIUM-HIGH)
  - [x] 2.1 In `frontend/src/features/schedule/components/AppointmentForm.tsx`, change the job `SelectItem` display from `{job.job_type} - {job.description}` to `{job.customer_name} — {job.job_type} - {job.description}`
  - [x] 2.2 Verify `customer_name` is available on the job objects returned by `useJobsReadyToSchedule()`; if not, update the hook/API to include it
  - _Files: AppointmentForm.tsx, possibly jobs hooks/API_

- [x] 3. Fix Convert to Job error extraction (Bug #6 — LOW)
  - [x] 3.1 In `frontend/src/features/sales/components/StatusActionButton.tsx`, use `axios.isAxiosError(err)` for robust error extraction in the `onError` handler for `convertToJob.mutate`
  - [x] 3.2 Ensure the "signature" string check works with the actual 422 error message "Waiting for customer signature" so the force-convert dialog appears
  - _Files: StatusActionButton.tsx_

## Phase 2: Backend Fixes

- [x] 4. Guard move_to_jobs for requires_estimate leads (Bug #2 — MEDIUM)
  - [x] 4.1 In `src/grins_platform/services/lead_service.py` `move_to_jobs()`, after resolving `_category` from `SITUATION_JOB_MAP`, check if `_category == "requires_estimate"`
  - [x] 4.2 If category is `requires_estimate`, call `self.move_to_sales(lead_id)` instead of creating a job, and return a response indicating the lead was redirected to Sales pipeline
  - [x] 4.3 Add unit test: lead with situation "Exploring" → `move_to_jobs()` redirects to sales; lead with "Repair" → creates job normally
  - _Files: lead_service.py, test files_

- [x] 5. Scope SMS dedupe per appointment_id (Bug #4 — MEDIUM-HIGH)
  - [x] 5.1 In `src/grins_platform/services/sms_service.py` `send_message()`, in the legacy dedupe branch (customer_id + message_type), when `appointment_id` is provided and `message_type` is `appointment_confirmation`, add `appointment_id` to the dedupe query
  - [x] 5.2 Update `get_by_customer_and_type()` in the message repository to accept an optional `appointment_id` filter, or write an inline query that includes the filter
  - [x] 5.3 Add unit test: two `appointment_confirmation` sends for different `appointment_id`s to the same customer within 24h → both succeed
  - _Files: sms_service.py, sent_message_repository.py, test files_

- [x] 6. Fix SMS send endpoint 500 on dedupe block (Bug #5 — MEDIUM)
  - [x] 6.1 In `src/grins_platform/api/v1/sms.py` `send_sms()`, check `send_result["success"]` before accessing `send_result["message_id"]`
  - [x] 6.2 When `success` is `False`, return an `SMSSendResponse` with `success=False`, `message_id=None` (or the `recent_message_id`), and appropriate status instead of crashing with KeyError
  - [x] 6.3 Update `SMSSendResponse` schema if needed to allow `message_id` to be optional
  - [x] 6.4 Add unit test: mock `send_message()` returning dedupe-blocked result → endpoint returns proper JSON, no 500
  - _Files: sms.py, sms schemas, test files_

- [x] 7. Make job_started transition status to in_progress (Bug #7 — HIGH)
  - [x] 7.1 In `src/grins_platform/api/v1/jobs.py` `job_started()`, after logging `started_at`, call `JobService.update_status()` to transition the job from `to_be_scheduled` to `in_progress`
  - [x] 7.2 Handle the case where the job is already `in_progress` (idempotent — skip the status update gracefully)
  - [x] 7.3 Add `JobService` as a dependency to the `job_started` endpoint if not already injected
  - [x] 7.4 Add unit test: job at `to_be_scheduled` → `job_started` → status is `in_progress`; then `complete_job` → status is `completed`
  - _Files: jobs.py, job_service.py, test files_

## Execution Order

```
Phase 1 (tasks 1-3) ← Frontend fixes, can be done in parallel
Phase 2 (tasks 4-7) ← Backend fixes
  Task 7 is highest priority (blocks entire field workflow)
  Tasks 5+6 are related (SMS) and should be done together
  Task 4 is independent
```

## Estimated Scope

- **Phase 1:** ~3 frontend files modified
- **Phase 2:** ~5-6 backend files modified + tests
- **Total:** ~9 file changes + test files
