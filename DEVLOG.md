# Development Log

## Project Overview
Grin's Irrigation Platform — field service automation for residential/commercial irrigation.

## Recent Activity

## [2026-04-16 20:30] - BUGFIX: 17 MEDIUM Customer Lifecycle Fixes (M-1..M-17)

### What Was Accomplished
Closed all 17 MEDIUM findings from the 2026-04-16 customer-lifecycle bug hunt, on top of the already-merged CR-1..CR-6 + H-1..H-14 fixes. Work ran in seven phases (1: SMS templates → 2: audits → 3: send_message routing → 4: schedule UX → 5: invoices → 6: sales → 7: renewals/uploads/docs), each commit gated through ruff/mypy/pyright/unit tests before merge.

### Technical Details
- **SMS template alignment (M-3/M-4/M-5/M-6):** `_KEYWORD_MAP` extended with `ok/okay/yup/yeah/1` (CONFIRM) and `different time/change time/2` (RESCHEDULE) — `stop` and `3` intentionally excluded. CONFIRM auto-reply now includes appointment date + time via new `_build_confirm_message` helper. Reschedule ack uses spec-exact wording. Google Review SMS uses spec verbiage (no `Grin's Irrigations`, no first-name prefix).
- **Audit coverage (M-7/M-8):** New `_record_update_audit` and `_record_reactivate_audit` on `AppointmentService` capture pre/post field snapshots, `notify_customer`, and `actor_id`. Customer-SMS cancel writes audit with `source="customer_sms"` and gates on `transitioned` to skip CR-3 short-circuit cases.
- **Audit trail completeness (M-9):** Y/R/C auto-reply and reschedule follow-up SMS now route through `SMSService.send_message` with new `APPOINTMENT_CONFIRMATION_REPLY` and `RESCHEDULE_FOLLOWUP` MessageType values. Migration `20260416_100000` widens the `ck_sent_messages_message_type` CHECK constraint.
- **Schedule UX (M-1/M-2):** `AppointmentDetail` now renders the canonical `SendConfirmationButton` for drafts (was a hand-rolled inline button). `CancelAppointmentDialog` keeps both action buttons visible for DRAFT and adds a `title` tooltip on the disabled "Cancel & text" variant.
- **Invoices (M-12/M-14/M-15):** `days_until_due` / `days_past_due` are now Pydantic `computed_field`s on `InvoiceResponse` (UTC, mutually exclusive). Frontend reads them directly. New `render_invoice_template()` + `validate_invoice_template()` helpers introduce canonical merge keys (`{customer_name}/{invoice_number}/{amount}/{due_date}`) and accept the spec's bracket form. Invalid templates → 400 with named missing keys. Stripe webhook returns 503 (was 400) on missing secret so Stripe retries.
- **Sales (M-10/M-11):** Regression test locks `StatusActionButton` calling convertToJob first on `SEND_CONTRACT` (no code change — the bughunt's "advance-first" claim was stale). `_get_signing_document` defaults to strict `sales_entry_id` scope; legacy customer-scope fallback gated behind `include_legacy=True` (reporting reads only).
- **Renewals/uploads/docs (M-13/M-16/M-17):** `PARTIALLY_APPROVED` fires on first approval (was waiting for zero PENDING). `PhotoService.validate_file` raises `TypeError` for MIME (→ 415) vs. `ValueError` for size (→ 413); all upload endpoints differentiate. New `useDocumentPresign` hook resolves presigned URL at render so signing buttons disable when the file is missing or expired.

### Files Created
- `src/grins_platform/migrations/versions/20260416_100000_widen_sent_messages_for_confirmation_reply_and_followup.py`
- `frontend/src/features/sales/components/StatusActionButton.test.tsx` (M-10 regression)
- `frontend/src/features/sales/components/SalesDetail.test.tsx` (M-17 signing gate)

### Files Modified
- `src/grins_platform/services/job_confirmation_service.py` (M-3/M-4/M-5/M-8)
- `src/grins_platform/services/appointment_service.py` (M-7)
- `src/grins_platform/services/sms_service.py` (M-9)
- `src/grins_platform/services/invoice_service.py` (M-14)
- `src/grins_platform/services/contract_renewal_service.py` (M-13)
- `src/grins_platform/services/photo_service.py` (M-16)
- `src/grins_platform/api/v1/jobs.py` (M-6, M-16)
- `src/grins_platform/api/v1/customers.py` (M-16)
- `src/grins_platform/api/v1/leads.py` (M-16)
- `src/grins_platform/api/v1/appointments.py` (M-7, M-16)
- `src/grins_platform/api/v1/invoices.py` (M-14)
- `src/grins_platform/api/v1/sales_pipeline.py` (M-11)
- `src/grins_platform/api/v1/webhooks.py` (M-15)
- `src/grins_platform/schemas/invoice.py`, `schemas/ai.py` (M-12, M-9)
- `src/grins_platform/models/enums.py`, `models/sent_message.py` (M-9)
- `frontend/src/features/schedule/components/AppointmentDetail.tsx` + test (M-1)
- `frontend/src/features/schedule/components/CancelAppointmentDialog.tsx` + test (M-2)
- `frontend/src/features/invoices/components/InvoiceList.tsx`, `types/index.ts` (M-12)
- `frontend/src/features/sales/components/SalesDetail.tsx`, `hooks/useSalesPipeline.ts` (M-17)

### Quality Check Results
- Backend `ruff check src/`: 179 errors baseline = 179 mine (no regression).
- Backend `mypy src/`: 230 errors baseline = 230 mine.
- Backend `pyright` on touched files: 10 errors / 102 warnings baseline = 10 / 102 mine after cleanup commit.
- Backend `pytest -m unit`: 49 fail / 3066 pass baseline = same on this branch (all 49 failures pre-existing).
- Frontend `tsc --noEmit`: clean.
- Frontend `eslint`: 4 errors baseline = 4 mine.
- Frontend `vitest`: 3 fail / 1379 pass baseline = same on this branch.

### Decisions
- **M-3:** `stop` and `3` are NOT cancel synonyms (`stop` is reserved compliance keyword; `3` would be ambiguous numeric mapping).
- **M-9:** Two new MessageType values (`appointment_confirmation_reply`, `reschedule_followup`) over reusing `appointment_confirmation` so per-type dedup and audit reporting stay accurate.
- **M-11:** Default behavior change — multi-entry customers with legacy unscoped docs now get a 422 prompting upload rather than silently signing the wrong entry's doc. Reporting reads opt back in with `include_legacy=True`.
- **M-15:** Behavioral change — Stripe missing-secret returns 503 (Stripe retries with backoff + on-call paged) rather than 400 (terminal, silent drop).

### Next Steps
- Manual E2E verification on dev for SMS #1 happy path with each new keyword (`ok`, `yup`, `1`, `R`, `different time`, repeat `C`) against `+19527373312`.
- Manual E2E for Job Complete → Google Review SMS (verify spec wording on owner's phone).
- LOW/UX findings L-1..L-11 remain open from the same hunt.

## [2026-04-16 17:50] - BUGFIX: 14 HIGH Customer Lifecycle Fixes (H-1..H-14)

### What Was Accomplished
Closed all 14 HIGH findings from the 2026-04-16 customer-lifecycle bug hunt, on top of the already-merged CR-1..CR-6 CRITICAL fixes. Work ran in four waves of parallel subagents (H-10/H-13/H-14 → H-2/H-3/H-4/H-8/H-9 → H-5/H-6/H-11 → H-1/H-7/H-12), each branch gated through ruff / mypy / pyright / unit tests before merging to dev.

### Technical Details
- **New surfaces:** `Alert` model + `AlertRepository` + `/api/v1/alerts` endpoint; `NoReplyReviewQueue` (`/schedule` tab); `BusinessSettingsPanel` (`/settings`); `reschedule-from-request` + `send-reminder-sms` endpoints; `useLeadRoutingActions` shared hook.
- **Nightly cron:** `flag_no_reply_confirmations` (6 AM local) flags SCHEDULED appointments with no Y/R/C reply after N days (BusinessSetting, default 3).
- **Consent hygiene:** `mass_notify` now batch-filters opt-outs via `SmsConsentRepository.get_opted_out_customer_ids`; response carries `skipped_count` + `skipped_reasons`.
- **Auth:** `bulk_notify_invoices` now genuinely `ManagerOrAdmin`-gated (was effectively open with `type: ignore` suppressions).
- **Calendar correctness:** `weekStartsOn: 1` + `firstDay={1}` unified across the schedule feature so admins and the backend `align_to_week()` agree.
- **PaymentMethod:** `credit_card` / `ach` / `other` added to the enum + CHECK constraint; `stripe` retained for legacy rows per owner decision — no data migration.
- **Renewal math:** `+52 weeks` → `replace(year=year+1)` + align-to-Monday with leap-day fallback; five-year roll test confirms weekday stability.

### Files Created
- `src/grins_platform/models/alert.py`, `src/grins_platform/repositories/alert_repository.py`, `src/grins_platform/schemas/alert.py`, `src/grins_platform/api/v1/alerts.py`
- `src/grins_platform/services/admin_config.py`, `src/grins_platform/services/business_setting_service.py`
- Alembic migrations: `20260416_100000` (H-4 payment-method CHECK), `20260416_100100` (H-5 alerts table), `20260416_100200` (H-7 needs_review_reason), `20260416_100300` (H-12 business-settings seeds)
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` + test
- `frontend/src/features/settings/components/BusinessSettingsPanel.tsx` + test, `useBusinessSettings.ts`, `businessSettingsApi.ts`
- `frontend/src/features/leads/hooks/useLeadRoutingActions.ts` + test
- `frontend/src/features/schedule/hooks/useNoReplyReview.ts`
- Multiple new backend + frontend test files

### Quality Check Results
- Backend unit + functional tests on all affected modules: green (144+ tests across H-5/H-7/H-11/H-12 alone).
- Frontend tests for affected features: green across customers, invoices, schedule, leads, settings (193 tests).
- Migrations: round-trip `alembic upgrade head` + `downgrade -1` verified for the 20260416 chain.
- Frontend typecheck baseline: 69 pre-existing errors; 0 new from Waves 1–4.

### Decisions (user-confirmed)
- **D-1 (H-1):** Full parity with `LeadsList` including requires-estimate + CR-6 conflict modal; shared `useLeadRoutingActions` hook.
- **D-3 (H-4):** Add `credit_card` / `ach` / `other`; keep `stripe` rows untouched; FE dropdown omits `stripe` going forward. No data migration.
- **D-5 (H-7):** 3-day no-reply default, overridable via `BusinessSetting.confirmation_no_reply_days`.
- **D-6 (H-12):** BusinessSettings panel placed as a new `Card` on the existing `/settings` page (the page uses stacked cards, not tabs).

### Follow-ups
- The two RescheduleRequestsQueue FE integration tests were re-enabled by mocking `AppointmentForm` (tests now verify the queue's own wiring rather than driving the full form + Radix Dialog chain in jsdom). Real form behavior still covered by its own component tests.
- The two long-form plan / finding documents that were lost mid-session (`customer-lifecycle-bughunt.md` and `critical-fixes-plan.md`) were reconstructed verbatim from the conversation's session-start Read captures.
- Agent-browser E2E validation for H-1 / H-3 / H-7 / H-12 not yet run in this session.

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

### Quality Check Results
- Each CR's new and modified tests pass locally. Pre-existing dev-branch failures were documented as drift notes per fix.
- Ruff / MyPy / Pyright surfaces match baseline — fix branches add zero new errors.
- FE typecheck + vitest pass on the new components and hooks.

### Decisions
- CR-1: Job status stays `to_be_scheduled` during DRAFT creation (admin promotes explicitly via Send Confirmation).
- CR-2: DRAFT cannot skip to IN_PROGRESS; only SCHEDULED / CONFIRMED / EN_ROUTE can.
- CR-5: Lien Review Queue is a tab on `/invoices`; client-side dismiss only for MVP.
- CR-6: 409 detail uses structured `{error:"duplicate_found", duplicates:[...]}`.

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
