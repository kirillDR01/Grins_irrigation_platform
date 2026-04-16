# Development Log

## Project Overview
Grin's Irrigation Platform — field service automation for residential/commercial irrigation.

## Recent Activity

## [2026-04-16 14:00] - BUGFIX: 6 Critical Customer Lifecycle Fixes (CR-1..CR-6)

### What Was Accomplished
Closed all 6 CRITICAL findings from the 2026-04-16 customer-lifecycle bug hunt (`bughunt/2026-04-16-customer-lifecycle-bughunt.md`). Six fix branches merged to `dev` across three waves.

### Technical Details
- **CR-1** (`fix/cr-1-apply-schedule-draft`, 2f7caaf): `apply_schedule` now writes `AppointmentStatus.DRAFT.value` and leaves `Job.status`/`Job.scheduled_at` untouched. Draft Mode silence restored.
- **CR-2** (`fix/cr-2-job-started-scheduled`, c65283e): `SCHEDULED → IN_PROGRESS` added to the transitions table; `job_started` pre-state tuple includes SCHEDULED. DRAFT stays blocked per decision.
- **CR-3** (`fix/cr-3-repeat-cancel-sms`, 9a30fac): `_handle_cancel` short-circuits when appointment already CANCELLED, returning empty `auto_reply` so the SMS guard suppresses the send.
- **CR-4** (`fix/cr-4-invoice-billing-reason`, 6d99587): renewal branch gated on Stripe `billing_reason == "subscription_cycle"`. Three-branch dispatch: first_invoice / renewal_cycle / other.
- **CR-5** (`fix/cr-5-lien-review-queue`, d679c25): `mass_notify("lien_eligible")` raises deprecation → 400; new `compute_lien_candidates` + `send_lien_notice` service methods; two new endpoints + `LienReviewQueue` component as tab on `/invoices`.
- **CR-6** (`fix/cr-6-convert-lead-dedup`, 7007002): `convert_lead` runs `check_tier1_duplicates`; raises `LeadDuplicateFoundError` → 409 with structured detail; FE `LeadConversionConflictModal` surfaces "Use existing" / "Convert anyway" (force=true).

### Files Created
- `src/grins_platform/schemas/invoice.py` (LienCandidateResponse, LienNoticeResult)
- `frontend/src/features/invoices/components/LienReviewQueue.tsx` + test
- `frontend/src/features/invoices/hooks/useLienReview.ts` + test
- `frontend/src/features/invoices/components/MassNotifyPanel.test.tsx`
- `frontend/src/features/leads/components/LeadConversionConflictModal.tsx` + test
- `frontend/src/features/leads/utils/isDuplicateConflict.ts`
- `bughunt/2026-04-16-critical-fixes-plan.md`

### Files Modified
- `src/grins_platform/api/v1/schedule.py` (CR-1)
- `src/grins_platform/api/v1/jobs.py`, `src/grins_platform/models/appointment.py` (CR-2)
- `src/grins_platform/services/job_confirmation_service.py` (CR-3)
- `src/grins_platform/api/v1/webhooks.py` (CR-4)
- `src/grins_platform/services/invoice_service.py`, `api/v1/invoices.py`, `repositories/invoice_repository.py` (CR-5)
- `src/grins_platform/services/lead_service.py`, `api/v1/leads.py`, `schemas/lead.py` (CR-6)
- `frontend/src/features/invoices/{types,api,hooks}/*`, `pages/Invoices.tsx`, `components/MassNotifyPanel.tsx` (CR-5)
- `frontend/src/features/leads/{types,components}/*`, plus ConvertLeadDialog wired to the conflict modal (CR-6)
- `bughunt/2026-04-16-customer-lifecycle-bughunt.md` (History — Resolved table appended)

### Quality Check Results
- Each CR's new and modified tests pass locally. Pre-existing dev-branch failures were documented as drift notes per fix.
- Ruff / MyPy / Pyright surfaces match baseline — fix branches add zero new errors.
- FE typecheck + vitest pass on the new components and hooks; matched adjustments to existing `ConvertLeadDialog.test.tsx`.

### Decisions
- CR-1: Job status stays `to_be_scheduled` during DRAFT creation (admin promotes explicitly via Send Confirmation).
- CR-2: DRAFT cannot skip to IN_PROGRESS; only SCHEDULED / CONFIRMED / EN_ROUTE can.
- CR-5: Lien Review Queue is a tab on `/invoices`; client-side dismiss only for MVP.
- CR-6: 409 detail uses structured `{error:"duplicate_found", duplicates:[...]}`; FE conflict handling lives in `ConvertLeadDialog` (where `useConvertLead` is actually called), not `LeadsList` as the plan originally described.

### Next Steps
- Address HIGH findings H-1..H-14 from the same hunt.
- Persist lien-candidate dismissals server-side (CR-5 follow-up).
- Run agent-browser E2E flows for CR-1, CR-5, CR-6 against the dev stack under the `+19527373312`-only SMS safety constraint.

## [2026-02-07 21:30] - BUGFIX: Lead Form CORS Error Diagnosis & Documentation

### What Was Accomplished
Diagnosed and documented the CORS error blocking lead form submissions from the Vercel landing page (`grins-irrigation.vercel.app`) to the Railway backend (`grins-platform-production.up.railway.app`). Created solution documentation for the deployment fix.

### Technical Details
- The browser's preflight `OPTIONS` request to `POST /api/v1/leads` was rejected because the backend's `CORS_ORIGINS` env var on Railway did not include `https://grins-irrigation.vercel.app`
- Confirmed no code changes needed — `src/grins_platform/app.py` already reads `CORS_ORIGINS` as a comma-separated env var and merges with localhost defaults
- Fix is purely a Railway environment variable update: add `https://grins-irrigation.vercel.app` to `CORS_ORIGINS`

### Files Created
- `LeadErrorSolution.md` — concise problem/solution/verification reference at workspace root
- `docs/lead-form-cors-fix.md` — detailed guide with step-by-step Railway instructions, curl verification commands, environment variable reference, and troubleshooting section (created in prior session)

### Decision Rationale
Documented the fix as a standalone markdown file rather than a code change because the issue is a deployment configuration gap, not a code bug. The CORS middleware is already correctly implemented — it just needs the right origins configured in production.

### Next Steps
- Apply the fix: add `https://grins-irrigation.vercel.app` to `CORS_ORIGINS` on Railway
- Verify with the curl commands in `LeadErrorSolution.md`
- Consider adding rate limiting to the public `/api/v1/leads` endpoint

## [2026-02-07 20:10] - FEATURE: Lead Capture (Website Form Submission)

### What Was Accomplished
Complete lead capture feature implemented end-to-end across backend and frontend, covering the full lifecycle from public form submission through admin management to customer conversion.

### Technical Details

**Backend (Python/FastAPI):**
- Lead SQLAlchemy model with Alembic migration, indexes on phone/status/created_at/zip_code
- Pydantic schemas with phone normalization, zip validation, HTML sanitization, honeypot bot detection
- Repository layer with filtered listing, search, pagination, and dashboard metric queries
- Service layer with duplicate detection (merges active duplicates), status transition validation, lead-to-customer conversion with optional job creation
- 6 API endpoints: public POST (no auth), admin GET list/detail, PATCH update, POST convert, DELETE
- Custom exceptions: LeadNotFoundError, LeadAlreadyConvertedError, InvalidLeadStatusTransitionError
- Dashboard integration: new_leads_today and uncontacted_leads metrics

**Frontend (React/TypeScript):**
- Full feature slice: types, API client, TanStack Query hooks, 5 components
- LeadsList with filtering (status, situation, date range, search), pagination, sorting
- LeadDetail with status management, staff assignment, action buttons
- ConvertLeadDialog with auto name-splitting, optional job creation toggle
- Status/Situation badge components with color coding
- Dashboard "New Leads" widget with color-coded urgency, sidebar nav with uncontacted count badge

**Testing:**
- 168 backend tests (unit, functional, integration, PBT) — all passing
- 6 property-based tests: phone normalization idempotency, status transition validity, duplicate detection, input sanitization, name splitting, honeypot transparency
- 793 frontend tests across 67 files — all passing
- Agent-browser E2E validation: form submission, lead management, filtering, status changes, conversion flow, deletion

### Quality Check Results
- Ruff: 0 lead-related violations (pre-existing seed migration issues only)
- MyPy: 0 errors
- Pyright: 0 errors
- Backend tests: 1870 passed (6 pre-existing failures in auth_service)
- Frontend lint: 0 errors
- Frontend typecheck: 0 errors
- Frontend tests: 793/793 passing

### Decisions and Deviations
- Public form submission endpoint has no auth (by design) for website integration
- Honeypot field returns identical 201 response shape to avoid bot detection leakage
- Duplicate detection merges data into existing active leads rather than rejecting
- CORS issue discovered during E2E testing — production backend needs landing page domain added to CORS_ORIGINS env var (documented in docs/lead-form-cors-fix.md)

### Next Steps
- Add landing page domain to Railway CORS_ORIGINS environment variable
- Consider adding rate limiting to public lead submission endpoint
- Future: automated SMS/email notifications on lead submission
