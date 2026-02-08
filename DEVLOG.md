# Development Log

## Project Overview
Grin's Irrigation Platform — field service automation for residential/commercial irrigation.

## Recent Activity

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
