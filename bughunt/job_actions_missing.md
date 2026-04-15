# Bug Hunt: Missing Job-Level Actions (Create Invoice & Mark Complete)

## Date: 2026-04-11

## Summary

Both "Create Invoice" and "Mark Complete" actions are effectively broken on the job detail view due to a frontend status mismatch and missing convenience endpoints.

## Root Cause Analysis

### Bug 1: "Mark Complete" — Status Mismatch in Frontend

**Root Cause:** The `JobDetail.tsx` component checks for statuses that do not exist in the backend `JobStatus` enum.

**Backend `JobStatus` enum** (`src/grins_platform/models/enums.py`):
- `to_be_scheduled`
- `in_progress`
- `completed`
- `cancelled`

**Frontend `JobDetail.tsx` status checks** (dead code):
- `requested` — does not exist in backend
- `approved` — does not exist in backend
- `scheduled` — does not exist in backend
- `closed` — does not exist in backend

**Impact:** The "Start Job" button renders only when `job.status === 'scheduled'`, but no job ever has that status. This means jobs in `to_be_scheduled` status have no button to transition to `in_progress`. Since jobs can never reach `in_progress`, the "Mark Complete" button (which checks `job.status === 'in_progress'`) also never renders.

**Valid transition chain:** `to_be_scheduled` → `in_progress` → `completed`

**Broken chain in UI:** No button exists for `to_be_scheduled` → `in_progress` because the frontend checks for `scheduled` instead of `to_be_scheduled`.

### Bug 2: "Create Invoice" — Blocked by Bug 1

**Root Cause:** The `GenerateInvoiceButton` component only renders when `['completed', 'closed'].includes(job.status)`. Since Bug 1 prevents jobs from ever reaching `completed` status through the UI, the invoice button never appears.

**Secondary issue:** There is no `POST /api/v1/jobs/{id}/invoice` convenience endpoint. The existing endpoint is `POST /api/v1/invoices/generate-from-job/{job_id}` which works but is on the invoices router, not the jobs router.

## Fix Plan

1. **Fix frontend status buttons** in `JobDetail.tsx`:
   - Replace `job.status === 'scheduled'` with `job.status === 'to_be_scheduled'` for the "Start Job" button
   - Remove dead code for non-existent statuses (`requested`, `approved`, `closed`)

2. **Add `POST /api/v1/jobs/{id}/complete` endpoint** — convenience endpoint that transitions job to COMPLETED status

3. **Add `POST /api/v1/jobs/{id}/invoice` endpoint** — convenience endpoint that generates an invoice for the job, delegating to InvoiceService

## Files Affected

- `frontend/src/features/jobs/components/JobDetail.tsx` — status button conditions
- `src/grins_platform/api/v1/jobs.py` — new convenience endpoints
