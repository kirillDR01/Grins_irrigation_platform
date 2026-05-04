# Feature: E2E Sign-off Bug Resolution — F2, F3, F4, F5, F6 (run-20260504-185844-full)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

The 2026-05-04 master-plan E2E sign-off run (`run-20260504-185844-full`) surfaced six findings. F1 (tech role on admin routes) is **deliberately deferred** pending product decision. This plan resolves the remaining five (F2, F3, F4, F5, F6) so the dev environment, customer portal flow, and live release path become green.

| ID | Tier | One-liner |
|---|---|---|
| **F2** | MINOR | Pricelist editor "search" only filters the loaded page (20 of 73), not the full set. |
| **F3** | BLOCKER | `START` keyword does NOT re-opt-in customers (TCPA / 10DLC compliance gap). |
| **F4** | BLOCKER | Railway dev `PORTAL_BASE_URL` points to a 9-day-stale Vercel preview alias; estimate-email links 404. |
| **F5** | MAJOR | Customer portal "Approve Estimate" navigates to `/portal/estimates/:token/confirmed`, which is **not registered** in the router → "unexpected application error". |
| **F6** | BLOCKER | Sales-pipeline auto-nudge data + admin pause/unpause API exist, but no scheduled job ever runs — the nudge feature is dead UI. |

## User Story

As **the operations team and the customers we serve**
I want **the consent restore (START), customer portal approve, pricelist search, sales pipeline nudges, and estimate email links to actually work**
So that **the live release passes the verdict gate, customers don't see broken links or scary error pages, ops doesn't manually nag stale estimates, and the platform stays compliant with 10DLC/TCPA opt-in expectations.**

## Problem Statement

The five bugs above either (a) silently break a promised customer interaction (F3 START, F4 portal URL, F5 approve confirmation), (b) waste built infrastructure (F6 unregistered cron), or (c) erode trust in admin tooling (F2 misleading empty-state). Each is fully scoped and verified end-to-end; the fixes are small but each touches its own subsystem.

## Solution Statement

Land **five focused, independently shippable changes**, each behind its own test, all under the existing umbrella plan `master-plan-run-findings-bug-resolution-2026-05-04.md`:

1. **F2** — pass `search` from the pricelist editor input to a new `?search=` query param on the services list endpoint, with a server-side `ILIKE` against `name`, `slug`, `subcategory`. Reuse the existing `useDebounce` hook.
2. **F3** — add a `START` exact-match branch in `SMSService.handle_inbound` that creates a fresh `SmsConsentRecord(consent_given=True, consent_method="text_start")`, emits a `sms.consent.opt_in_sms_received` audit event, and sends a re-subscription confirmation SMS.
3. **F4** — operational env-var fix (Railway dashboard) + a deployment-time guard that warns on boot if `PORTAL_BASE_URL` matches the deprecated alias prefix.
4. **F5** — register `/portal/estimates/:token/confirmed` and `/portal/contracts/:token/confirmed` routes pointing at the existing `ApprovalConfirmation` component; capture and surface mutation errors instead of swallowing them.
5. **F6** — create a `SalesPipelineNudgeJob` that walks `sales_pipeline_entry` rows in `{send_estimate, pending_approval, send_contract}` whose `last_contact_date <= now - STALE_DAYS` and `nudges_paused_until` is null, sends an email nudge, bumps `last_contact_date`, and writes a `sales_pipeline.nudge.sent` audit row. Register it in `register_scheduled_jobs()`.

## Feature Metadata

**Feature Type**: Bug Fix (5 independent issues, one umbrella PR is acceptable; per memory `feedback_bug_reporting_workflow.md` and master-plan §"BUG-REPORTING WORKFLOW")
**Estimated Complexity**: **Medium** overall — F2/F4/F5 are small (≤ 60 LoC each); F3 and F6 are medium (~200 LoC each plus tests)
**Primary Systems Affected**:
- Backend: `services/sms_service.py`, `services/sms/audit.py`, `services/background_jobs.py`, **new** `services/sales_pipeline_nudge_job.py`, `services/service_offering_service.py`, `repositories/service_offering_repository.py`, `api/v1/services.py`, `services/email_service.py`
- Frontend: `features/pricelist/components/PriceListEditor.tsx`, `features/pricelist/api/serviceApi.ts`, `features/portal/api/portalApi.ts`, `features/portal/components/EstimateReview.tsx`, `features/portal/components/ContractSigning.tsx`, `core/router/index.tsx`, **new** `pages/portal/ApprovalConfirmation.tsx`
- Operational: Railway `PORTAL_BASE_URL` env var (dev + prod)

**Dependencies**: No new packages. APScheduler 3.x, Resend (email), SQLAlchemy 2 async, TanStack Query, axios — all already in use.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

#### F2 — Pricelist search

- `frontend/src/features/pricelist/components/PriceListEditor.tsx` (lines 56, 65–91, 150–151) — Why: search state is currently consumed only by an in-memory `.filter()` on the loaded page. The `useDebounce` wrap, the params shape, and the test selectors all live here.
- `frontend/src/features/pricelist/api/serviceApi.ts` (lines 14–24) — Why: line 18 explicitly strips `search` (`const { search, ...query } = params ?? {}; void search;`). This is the line to delete.
- `frontend/src/features/pricelist/types/index.ts` (line ~150) — Why: `ServiceOfferingListParams` already includes `search?: string`. No type change needed — only the dropping logic in the API client.
- `frontend/src/shared/hooks/useDebounce.ts` (lines 9–23) — Why: existing 300ms debounce hook used elsewhere; reuse don't re-implement.
- `src/grins_platform/api/v1/services.py` (lines 60–132) — Why: `list_services()` query-param block. Add `search: str | None = Query(default=None, description=...)` and pass through to the service.
- `src/grins_platform/services/service_offering_service.py` (~line 188) — Why: service-layer `list_services()` signature passes filters into the repo; mirror.
- `src/grins_platform/repositories/service_offering_repository.py` (lines 273–334) — Why: `list_with_filters()` is the SQL builder. Add an `or_()` ILIKE block on `name`, `slug`, `subcategory` before pagination.

#### F3 — START re-opt-in

- `src/grins_platform/services/sms_service.py` (lines 65–68, 82–85, 766–841, 1136–1244) — Why: `EXACT_OPT_OUT_KEYWORDS`, `OPT_OUT_CONFIRMATION_MSG`, `handle_inbound`, and `_process_exact_opt_out` are the canonical mirror surfaces. The new `_process_exact_opt_in` method must mirror `_process_exact_opt_out` line-for-line, swapping `consent_given=True`, `consent_method="text_start"`, no `opt_out_*` fields, and a different confirmation message.
- `src/grins_platform/services/job_confirmation_service.py` (lines 40–66) — Why: read the comment on line 43–45 explaining why `stop` is intentionally excluded. **Do NOT add START here.** START belongs in the consent layer (`sms_service.py`), not the confirmation router.
- `src/grins_platform/models/sms_consent_record.py` — Why: immutable INSERT-ONLY model. Confirm `consent_method` accepts the string `"text_start"` (it's a free-form string column — no enum constraint, but stay consistent with `"text_stop"` neighbour).
- `src/grins_platform/services/sms/consent.py` (lines 162–176) — Why: **VERIFIED** — `_has_hard_stop()` returns True on ANY `(consent_method='text_stop' AND consent_given=False)` row across the phone variants. There is **no latest-record-wins logic**. **The refactor in F3.3 is mandatory**, not conditional. The module docstring at lines 8–9 codifies the current "any historical STOP wins" rule, so the refactor is also a documented behaviour change — update that docstring too.
- `src/grins_platform/services/sms/audit.py` (lines 21, 126–137) — Why: module-level singleton `_audit = AuditService()` at line 21 is the established pattern; `log_consent_hard_stop()` at lines 126–137 is the exact mirror for the new `log_consent_opt_in_sms()`. Call shape: `await _audit.log_action(db, action="...", resource_type="sms_consent", details={"phone": phone_masked})` — `db` positional, rest kw-only.
- `src/grins_platform/repositories/sms_consent_repository.py` (lines 39, 91–123) — Why: `get_latest_for_customer` (lines 91–123) confirms the table is documented "INSERT-ONLY so the 'current' state for a customer is the row with the newest `created_at`". The new `_has_hard_stop` implementation must use **latest-by-`created_at`-DESC across all phone variants**, NOT keyed on `customer_id` (some inbound STOPs land before customer correlation).
- `src/grins_platform/services/sms_service.py` (lines 1388–1448) — Why: `_record_customer_sms_opt_out_audit` is the existing sister-method to mirror. **It writes via `AuditLogRepository(self.session).create(...)` directly** — NOT via `AuditService` — and includes the gap-05 discriminator `details={"actor_type": "customer", "source": "customer_sms", "phone_e164": …, "consent_record_id": …, "raw_body": …}`. The new `_record_customer_sms_opt_in_audit` must use the same direct-repo path with the same discriminator shape so the admin history view treats opt-in events identically to opt-out events.
- `src/grins_platform/services/audit_service.py` (lines 31–34) — Why: the canonical action-name list explicitly includes `consent.opt_out_sms`, `consent.opt_out_informal_flag`, `consent.opt_out_admin_confirmed`. The comment line 19 says "do NOT invent new ones — extend this list when adding a new flow". The new opt-in action **must be added to that docstring list** as `consent.opt_in_sms` (canonical, mirrors the opt-out twin) — and that's the action string passed to `_record_customer_sms_opt_in_audit`. The sub-domain audit twin `sms.consent.opt_in_sms_received` lives in `services/sms/audit.py` separately.
- `src/grins_platform/tests/unit/test_pbt_sms_consent_gating.py`, `src/grins_platform/tests/unit/test_sms_consent_repository.py`, `src/grins_platform/tests/test_sms_service.py` — Why: STOP test patterns to mirror for START.

#### F4 — PORTAL_BASE_URL stale

- `src/grins_platform/services/email_config.py` (line 24) — Why: `portal_base_url: str = "http://localhost:5173"` default. Add a startup-time warning (in `log_configuration_status`) if the value matches the deprecated `frontend-git-dev-kirilldr01s-projects.vercel.app` alias.
- `.env.example` (lines 152–153) — Why: comment + default. Update to point to the canonical `grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` so new dev clones get the right value.
- `src/grins_platform/services/estimate_service.py` (lines 306–308, 939–941, 1068–1070) — Why: three places that build `f"{self.portal_base_url}/portal/estimates/{estimate.customer_token}"`. No code change needed — just verify the construction is consistent and the env var is the single source of truth.
- `src/grins_platform/api/v1/portal.py` (line ~109) — Why: shows how `EmailSettings().portal_base_url` is wired into `EstimateService` constructor.

#### F5 — Portal Approve confirmation route

- `frontend/src/core/router/index.tsx` (lines 156–177) — Why: portal route block. Currently registers `estimates/:token`, `contracts/:token`, `invoices/:token`, `manage-subscription`. **Missing**: `estimates/:token/confirmed` and `contracts/:token/confirmed`. **This is the root cause of "unexpected application error"** — `navigate()` lands on an unregistered child path, React Router renders the parent's error boundary.
- `frontend/src/features/portal/components/EstimateReview.tsx` (lines 104–120) — Why: `handleApprove`/`handleReject` navigate to `/portal/estimates/:token/confirmed`. The empty `catch {}` blocks (lines 108–110, 117–119) silently swallow mutation errors — surface them via the existing `approve.error` mutation state once we register the route.
- `frontend/src/components/ui/alert.tsx` (lines 5–58) — Why: **existing shadcn-style `<Alert>` component** with `variant` prop (default | destructive). Exports `Alert`, `AlertTitle`, `AlertDescription`. **Use this** for the F5 error surface; do NOT inline a `<div role="alert">` or invent a new `ErrorBanner` component.
- `frontend/src/features/portal/components/ContractSigning.tsx` (line 94) — Why: same issue, `/portal/contracts/:token/confirmed` is also unregistered.
- `frontend/src/features/portal/components/ApprovalConfirmation.tsx` (lines 47–88) — Why: the destination component already exists and accepts `location.state.action`. Just register it under the missing routes.
- `frontend/src/features/portal/api/portalApi.ts` (lines 30–45) — Why: `approveEstimate`/`rejectEstimate`/`signContract` return `Promise<void>` even though the backend returns `PortalEstimateResponse`. **Optional improvement** (not strictly required for the bug fix): widen to `Promise<PortalEstimate>` so future UX (e.g., showing "your estimate has been approved at $X total") becomes easy.
- `frontend/src/features/portal/components/EstimateReview.test.tsx` (lines 56–66) — Why: existing test pattern that registers the `confirmed` route inline; mirror this in production router.
- `frontend/src/shared/components/ErrorBoundary.tsx` (lines 52–53) — Why: source of the "Something went wrong" fallback the user saw. After the route registration fix, this should never render in the approve flow.

#### F6 — Sales pipeline nudge cron

- `src/grins_platform/services/background_jobs.py` (lines 1389–1503) — Why: `register_scheduled_jobs()` is where the new job is registered. Mirror the `escalate_failed_payments_job` pattern (cron, fixed hour/minute, `replace_existing=True`, append the job ID to the `logger.info("scheduler.jobs.registered", jobs=[...])` list at line 1491).
- `src/grins_platform/services/onboarding_reminder_job.py` (full file, especially lines 29–63) — Why: **canonical sister job to mirror.** It uses `LoggerMixin`, opens a session via `db_manager.get_session()`, queries with `selectinload`, iterates and updates fields in-place, single `await session.commit()` at the end. Reuse this exact shape.
- `src/grins_platform/services/sales_pipeline_service.py` (lines 446–500) — Why: pause/unpause methods that the new job must respect. The new query filter must include `nudges_paused_until.is_(None) | nudges_paused_until <= now`.
- `src/grins_platform/models/sales.py` (lines 32–120) — Why: `SalesEntry` model **VERIFIED**. Fields used by the nudge query: `id`, `customer_id`, `status`, `last_contact_date`, `nudges_paused_until`, `dismissed_at`, `updated_at`. **`customer` relationship is already `lazy="selectin"` (line 102) — no explicit `selectinload(SalesEntry.customer)` needed in the query.** No `nudge_count` column exists; do not assume one.
- `src/grins_platform/models/enums.py` (lines 644–677) — Why: `SalesEntryStatus` — query target statuses are `SEND_ESTIMATE`, `PENDING_APPROVAL`, `SEND_CONTRACT`. Use the enum values, never literal strings.
- `src/grins_platform/services/email_service.py` (lines 154–265, 189–206) — Why: `EmailService.send_*()` pattern. Constructor takes `EmailSettings | None = None` and creates Jinja2 env via `_TEMPLATE_DIR` (verify at top of file). `_classify_email` (lines 184–209) holds a `transactional_types` set — **the new `"sales_pipeline_nudge"` email type MUST be added to that set** so it routes via the transactional sender. `_send_email` (lines 254+) is the private dispatch.
- `src/grins_platform/services/audit_service.py` (lines 19–35, 64–120) — Why: **VERIFIED signature** — `AuditService.log_action(db, *, actor_id=None, actor_role=None, action, resource_type, resource_id=None, details=None, ip_address=None, user_agent=None) -> AuditLog`. `db` is positional, rest keyword-only. The class is a `LoggerMixin` subclass with `DOMAIN = "audit"` — instantiate per-call via `AuditService()` (it's stateless beyond logger). For F6, also add `sales_pipeline.nudge.sent` to the canonical action-name docstring list at lines 21–35.
- `src/grins_platform/tests/unit/test_background_jobs.py` (lines 1–100) — Why: pattern for testing scheduled jobs with mocked `db_manager`.

### New Files to Create

- `src/grins_platform/services/sales_pipeline_nudge_job.py` — `SalesPipelineNudgeJob(LoggerMixin)` mirroring `OnboardingReminderJob`. Module-level singleton + async wrapper.
- `src/grins_platform/templates/emails/sales_pipeline_nudge.html` — **path is `templates/emails/` (plural), not `templates/email/`**, matching every existing template (`annual_notice.html`, `estimate_sent.html`, etc.). Resend-friendly transactional template. Variables: `customer_first_name`, `estimate_total`, `portal_url`, `company_name` (`pause_link` is v2 — do NOT add).
- `frontend/src/pages/portal/ApprovalConfirmation.tsx` — 3-line wrapper for the existing `<ApprovalConfirmation />` feature component (used by F5).
- `src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py` — unit tests mirroring `test_background_jobs.py`'s `TestFailedPaymentEscalator`.
- `src/grins_platform/tests/integration/test_sms_start_keyword.py` — integration test for STOP→START round-trip on a single phone.
- `frontend/src/features/portal/components/__tests__/EstimateReview.approval.test.tsx` — covers the navigate-to-confirmed flow without the in-test inline route override (i.e., uses production router).

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [APScheduler v3 cron trigger](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html#module-apscheduler.triggers.cron)
  - Specific section: "API"
  - Why: F6 job uses `"cron"` trigger with `hour=H, minute=M`. Confirm `replace_existing=True` semantics.
- [TanStack Query v5 — useMutation error states](https://tanstack.com/query/latest/docs/framework/react/reference/useMutation)
  - Specific section: "isError, error, reset"
  - Why: F5 surfaces `approve.error` instead of swallowing.
- [10DLC Best Practices for Opt-in Keywords](https://support.bandwidth.com/hc/en-us/articles/4407463451287-10DLC-Best-Practices-Opt-In-Opt-Out-and-Help)
  - Specific section: "Opt-in keywords (START, UNSTOP)"
  - Why: F3 must support at minimum `START`; common synonyms `UNSTOP`/`SUBSCRIBE` are nice-to-have.
- [SQLAlchemy 2.0 ILIKE on multiple columns](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html#filtering-on-multiple-criteria)
  - Specific section: "or_() and and_()"
  - Why: F2 search across `name`, `slug`, `subcategory`.
- [Resend transactional email — bounce/spam considerations](https://resend.com/docs/send-with-python)
  - Specific section: "Sending behaviour"
  - Why: F6 nudge mustn't trip spam thresholds; respect `email_test_inbox` allowlist on dev/staging.

### Patterns to Follow

**Naming Conventions** (observed in the codebase):
- Backend: snake_case modules, PascalCase classes, snake_case methods. Service singletons: `_service_name = ServiceName()` at module bottom.
- Frontend: kebab-case routes, PascalCase components, camelCase hooks/functions, hooks named `useThing()`.
- Audit event names: dotted lowercase (`sms.consent.hard_stop_received`, `sales_pipeline.nudge.sent`).
- Scheduler job IDs: snake_case, no prefix (`escalate_failed_payments`, `nudge_stale_sales`).

**Error Handling** (from `sms_service.py` and `portal.py`):
- Backend: typed domain exceptions (`EstimateNotFoundError`, `SMSConsentDeniedError`); routes catch and re-raise as `HTTPException` with explicit status. No bare `except`.
- Frontend: React Query mutations expose `error` and `isError`; surface them in the component, never silently `catch {}`.

**Logging Pattern** (from `LoggerMixin` users):
- `self.log_started("method_name", **context)` at entry
- `self.log_completed("method_name", **context)` at success
- `self.log_rejected("method_name", reason="…")` at deliberate denial
- `logger.warning("event.name", exc_info=True)` for non-fatal failures

**Audit Pattern** (from `services/sms/audit.py`):
- Each audit action gets a small async helper (`log_consent_hard_stop`, `log_consent_opt_in_sms`)
- Helpers call `audit_service.log_action(db, action, resource_type, details)` — never write to `audit_logs` directly from a service.

**Background-job Pattern** (from `OnboardingReminderJob`):
1. Class extends `LoggerMixin`, has `DOMAIN = "name"`.
2. `async def run(self)`: opens session via `db_manager.get_session()`, runs one query, iterates, mutates models in-place, single `await session.commit()`.
3. Module-level singleton `_job_instance = JobClass()`.
4. Module-level async wrapper `async def {name}_job(): await _job_instance.run()`.
5. Registered in `register_scheduled_jobs()` with `replace_existing=True`.

**Frontend route pattern** (from `core/router/index.tsx:155–177`):
- Lazy-load page components.
- Public portal routes nest under `/portal` with `<PortalWrapper />` (Suspense, no auth, no layout).
- Each route has a `path` and an `element`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Verify env / data prerequisites and read all files in the CONTEXT REFERENCES section. **No code change in this phase.**

**Tasks:**
- Read every file listed above; confirm line numbers haven't drifted.
- Run `git pull --rebase origin dev` to confirm the working copy is current.
- Confirm Railway dev access (you'll need `railway` CLI for the F4 verification step). Per memory `feedback_no_remote_alembic.md` — **never** run alembic against `*.railway.{app,internal}` from local; this plan adds no migrations, but if F6 needs one (it doesn't — uses existing columns), it must go through the deploy pipeline.
- Confirm the seed customer (`a44dc81f-…`, phone `9527373312`, email `kirillrakitinsecond@gmail.com`) exists per memory `project_e2e_seed_identities.md`.

### Phase 2: Core Implementation

Each bug is independent. Implementation order is **chosen for blast-radius minimization** (F2 first, F3 last):

1. **F2** (Phase 2.1) — pricelist search (smallest, lowest blast radius)
2. **F5** (Phase 2.2) — portal confirmed route (smallest FE)
3. **F4** (Phase 2.3) — env-var fix + boot-time warning
4. **F6** (Phase 2.4) — sales pipeline nudge job
5. **F3** (Phase 2.5) — START keyword (highest blast radius — touches consent layer)

### Phase 3: Integration

- Wire the new sales pipeline nudge job into `register_scheduled_jobs()`.
- Register the two new portal `confirmed` routes.
- Verify the email-config startup warning fires on boot.

### Phase 4: Testing & Validation

Run all five validation levels (see VALIDATION COMMANDS). Smoke each fix individually with the `e2e/master-plan/run-phase.sh` harness when applicable.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### F2 — Pricelist search wires `?search=` to the API

#### Task F2.1 — UPDATE `src/grins_platform/repositories/service_offering_repository.py`

- **IMPLEMENT**: In `list_with_filters()` (lines 273–334), accept a new `search: str | None = None` parameter. Before pagination, when `search` is non-empty, add `stmt = stmt.where(or_(ServiceOffering.name.ilike(f"%{search}%"), ServiceOffering.slug.ilike(f"%{search}%"), ServiceOffering.subcategory.ilike(f"%{search}%")))`.
- **PATTERN**: Existing filter blocks at lines 304–313 — add the search block right above pagination.
- **IMPORTS**: `from sqlalchemy import or_` (likely already present; check the existing imports).
- **GOTCHA**: `subcategory` is nullable — `ILIKE` on a NULL column returns NULL, which behaves correctly under `or_()`. Don't add `.isnot(None)` — that would wrongly exclude rows that have `name` matches but null subcategory.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_service_offering_repository.py -v`

#### Task F2.2 — UPDATE `src/grins_platform/services/service_offering_service.py`

- **IMPLEMENT**: Around line 188, add `search: str | None = None` to `list_services` signature; pass through to repo.
- **PATTERN**: Mirror existing param forwarding for `category`, `is_active`, `customer_type`.
- **GOTCHA**: Don't trim/lowercase here; let the repo decide. SQL `ILIKE` already case-insensitive.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_service_offering_service.py -v`

#### Task F2.3 — UPDATE `src/grins_platform/api/v1/services.py`

- **IMPLEMENT**: At line 66, add `search: Annotated[str | None, Query(description="Substring match against name, slug, or subcategory (case-insensitive)")] = None` to the `list_services` endpoint signature; pass through to the service call at line 124.
- **PATTERN**: Existing query params (`category`, `is_active`, `customer_type`) — same `Annotated` style.
- **GOTCHA**: FastAPI converts empty string `?search=` to `""`. Treat `""` as None — `if search:` is the right check (covers None and empty).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/test_services_api.py -v`

#### Task F2.4 — UPDATE `frontend/src/features/pricelist/api/serviceApi.ts`

- **IMPLEMENT**: Lines 14–24, replace the `list` method to **stop stripping** `search`. Pass the full `params` object straight through to `apiClient.get('/services', { params })`.
- **PATTERN**: Mirror other `apiClient.get` calls that take params.
- **GOTCHA**: axios serializes `undefined` values out by default — empty `search` will simply not be sent. No need to manually clean.
- **VALIDATE**: `cd frontend && npm run typecheck`

#### Task F2.5 — UPDATE `frontend/src/features/pricelist/components/PriceListEditor.tsx`

- **IMPLEMENT**:
  - Line 56: keep `search` state.
  - Add `const debouncedSearch = useDebounce(search, 300);` (import `useDebounce` from `@/shared/hooks/useDebounce`).
  - In the `params` object (lines 65–76), include `search: debouncedSearch || undefined`.
  - In the `filtered` `useMemo` (lines 81–91), **remove** the client-side substring filter — the server now does this. Keep the customer-type/category client filters if they exist as redundant guards (they're cheap), but the search is server-side only now.
  - Line 78 query key: ensure it depends on `params` so the query refetches when search changes.
- **PATTERN**: `frontend/src/features/customers/components/CustomerSearch.tsx` for an existing debounce-into-query pattern (verify file exists; otherwise grep `useDebounce` for callers).
- **GOTCHA**: The query key change means TanStack Query will create a new cache entry per debounced search term. That's correct. Don't `keepPreviousData` for now; the perceived UX is fine because debounce is 300 ms.
- **VALIDATE**: `cd frontend && npm run lint && npm run typecheck`

#### Task F2.6 — UPDATE `frontend/src/features/pricelist/components/PriceListEditor.test.tsx`

- **IMPLEMENT**: Add a test case `"sends ?search= to the API when the user types"` that:
  - Mocks `serviceApi.list` (already mocked).
  - Types "Spring" into the search input (`getByPlaceholderText("Search name, slug, subcategory…")`).
  - Waits 300 ms (use vitest fake timers or `await waitFor`).
  - Asserts the mock was called with `{ search: "Spring", … }`.
- **PATTERN**: Existing tests in this file for filter changes.
- **VALIDATE**: `cd frontend && npm test -- PriceListEditor.test.tsx`

---

### F5 — Portal `/confirmed` routes register

#### Task F5.1 — CREATE `frontend/src/pages/portal/ApprovalConfirmation.tsx`

- **IMPLEMENT**: Thin wrapper (mirroring `pages/portal/EstimateReview.tsx`):
  ```tsx
  import { ApprovalConfirmation } from '@/features/portal';
  export function ApprovalConfirmationPage() {
    return <ApprovalConfirmation />;
  }
  ```
- **PATTERN**: `pages/portal/EstimateReview.tsx` (3-line wrapper).
- **VALIDATE**: `cd frontend && npm run typecheck`

#### Task F5.2 — UPDATE `frontend/src/core/router/index.tsx`

- **IMPLEMENT**:
  - Add a lazy import (around line 90–108, in the portal-pages block):
    ```tsx
    const ApprovalConfirmationPage = lazy(() =>
      import('@/pages/portal/ApprovalConfirmation').then((m) => ({
        default: m.ApprovalConfirmationPage,
      }))
    );
    ```
  - In the `/portal` children block (lines 159–175), add **two new entries** before the existing `manage-subscription`:
    ```tsx
    { path: 'estimates/:token/confirmed', element: <ApprovalConfirmationPage /> },
    { path: 'contracts/:token/confirmed', element: <ApprovalConfirmationPage /> },
    ```
- **PATTERN**: Existing `estimates/:token` registration at line 161.
- **GOTCHA**: The order matters only when paths could shadow each other; React Router v7 prefers exact specificity, so `:token/confirmed` will win over `:token` for the `/confirmed` URL. Keep them in declared order — `:token` first, then `:token/confirmed` is fine because they're disjoint exact paths.
- **VALIDATE**: `cd frontend && npm run typecheck && npm run lint`

#### Task F5.3 — UPDATE `frontend/src/features/portal/components/EstimateReview.tsx`

- **IMPLEMENT**:
  1. Add the import at the top of the file: `import { Alert, AlertDescription } from '@/components/ui/alert';`.
  2. Replace empty `catch {}` blocks at lines 108–110 and 117–119 with `catch { /* surfaced via approve.error / reject.error below */ }` (drop the bound `err` — the mutation's `error` state is the source of truth).
  3. Above the Approve/Reject button row (find by `<Button` JSX further down — same component), insert:
     ```tsx
     {(approve.isError || reject.isError) && (
       <Alert variant="destructive" data-testid="estimate-action-error">
         <AlertDescription>
           {extractErrorMessage(approve.error ?? reject.error)
             ?? 'We couldn’t save that action. Please try again or call us at the number above.'}
         </AlertDescription>
       </Alert>
     )}
     ```
  4. Add a small helper at the top of the file (or in `frontend/src/shared/utils/error.ts` if a similar one already exists — grep first):
     ```ts
     import type { AxiosError } from 'axios';
     function extractErrorMessage(err: unknown): string | undefined {
       const axErr = err as AxiosError<{ detail?: string }> | undefined;
       return axErr?.response?.data?.detail ?? (err as Error | undefined)?.message;
     }
     ```
- **PATTERN**: Existing `<Alert>` component at `frontend/src/components/ui/alert.tsx` (lines 5–58); `variant="destructive"` is supported. Same shadcn pattern used elsewhere in the codebase.
- **GOTCHA**: The mutation `error` is typed as `Error | null`; cast safely, never `any`. Don't add the helper to `shared/components/` — it's a one-liner; keep colocated unless an exact duplicate already exists.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- EstimateReview.test.tsx`

#### Task F5.4 — UPDATE `frontend/src/features/portal/components/ContractSigning.tsx`

- **IMPLEMENT**: Same pattern as F5.3 — surface `signContract.error` instead of swallowing.
- **VALIDATE**: `cd frontend && npm test -- ContractSigning.test.tsx`

#### Task F5.5 — CREATE `frontend/src/features/portal/components/__tests__/EstimateReview.approval.test.tsx`

- **IMPLEMENT**: Test that:
  - Renders the actual production `<RouterProvider>` (or a `MemoryRouter` with **all** portal routes registered, including `:token/confirmed`).
  - Mocks `portalApi.approveEstimate` to resolve.
  - Clicks Approve.
  - Asserts the URL changed to `/portal/estimates/:token/confirmed` AND the confirmation page (`data-testid="approval-confirmation-page"`) renders.
- **PATTERN**: `EstimateReview.test.tsx` (lines 56–66) inline route registration. The new test must use the **production route table** — that's the regression guard.
- **VALIDATE**: `cd frontend && npm test -- EstimateReview.approval.test.tsx`

---

### F4 — `PORTAL_BASE_URL` env-var sanity

#### Task F4.1 — UPDATE Railway env var (operational, no code)

- **IMPLEMENT**: In Railway dashboard for service `Grins-dev`, environment `dev`:
  - Set `PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`
  - Save and let the service redeploy.
- **PATTERN**: N/A — operational.
- **GOTCHA**: Per memory `feedback_no_remote_alembic.md`, **do not** push from local. Use the dashboard. Do NOT attempt to run `railway run` for migrations as part of this fix.
- **VALIDATE**:
  ```
  curl -s "$RAILWAY_API/api/v1/healthz" | jq '.config.portal_base_url'
  # expected: "https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app"
  ```
  If `healthz` doesn't expose the var, run:
  ```
  curl -s -X POST $API/api/v1/estimates/<test_id>/send -H "Authorization: Bearer $TOKEN" \
    | jq '.portal_url' | grep grins-irrigation-platform-git-dev
  ```

#### Task F4.2 — UPDATE `src/grins_platform/services/email_config.py`

- **IMPLEMENT**: Add to `EmailSettings.log_configuration_status()` (after line 60):
  ```python
  _DEPRECATED_PORTAL_HOSTS = ("frontend-git-dev-kirilldr01s-projects.vercel.app",)
  if any(h in self.portal_base_url for h in _DEPRECATED_PORTAL_HOSTS):
      logger.error(
          "email.config.deprecated_portal_base_url",
          portal_base_url=self.portal_base_url,
          message=(
              "PORTAL_BASE_URL points to a deprecated Vercel preview alias. "
              "Estimate/portal links will 404. Update Railway env var to "
              "https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app "
              "(dev) or the equivalent canonical prod alias."
          ),
      )
  ```
- **PATTERN**: Existing `if not self.resend_api_key` block at line 43.
- **GOTCHA**: This is a structured-log warning, not a hard fail — service must still boot if the var is misconfigured (so you can self-heal on dev). On prod, the deploy logs review will surface it.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_config.py -v` (add a new test asserting the warning fires when `portal_base_url` contains the deprecated host).

#### Task F4.3 — UPDATE `.env.example`

- **IMPLEMENT**: Lines 152–153, change the example value from the deprecated alias to the canonical one. Update the comment to read:
  ```
  # PORTAL_BASE_URL must be the **canonical** Vercel domain for the environment:
  #   dev:  https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app
  #   prod: https://app.grinsirrigation.com  (or the live Vercel alias)
  # Pointing this at a stale preview alias breaks every customer portal link.
  PORTAL_BASE_URL=http://localhost:5173
  ```
- **VALIDATE**: `grep -n PORTAL_BASE_URL /Users/kirillrakitin/Grins_irrigation_platform/.env.example`

---

### F6 — Sales pipeline auto-nudge cron job

#### Task F6.1 — CREATE `src/grins_platform/templates/emails/sales_pipeline_nudge.html`

- **IMPLEMENT**: Plain transactional template with these merge fields:
  - `{{ customer_first_name }}` (template should render `{{ customer_first_name|default("there") }}`)
  - `{{ estimate_total }}` (currency-formatted, optional — only if linked estimate exists; render conditionally)
  - `{{ portal_url }}` (optional — only if linked estimate exists; render conditionally)
  - `{{ company_name }}` (default "Grins Irrigation")
  - Subject (set on the send call, NOT in the template): `"Just checking in on your estimate"`.
- **PATTERN**: **Path is `templates/emails/` (plural)**. Mirror `templates/emails/estimate_sent.html` for inline-CSS / table layout, header, and footer (unsubscribe link).
- **GOTCHA**: Per memory `feedback_email_test_inbox.md`, dev/staging must enforce code-level allowlist — only `kirillrakitinsecond@gmail.com` allowed. Verify the existing allowlist guard wraps `EmailService._send_email` (search the file for `EMAIL_TEST_ALLOWLIST` or `email_test_inbox`). If not centralized there, the nudge job MUST self-guard before calling `send_sales_pipeline_nudge`.
- **VALIDATE**: `ls src/grins_platform/templates/emails/sales_pipeline_nudge.html` exists; render once in a snapshot test or eyeball.

#### Task F6.2 — UPDATE `src/grins_platform/services/email_service.py`

- **IMPLEMENT**:
  1. Add `"sales_pipeline_nudge"` to the `transactional_types` set in `_classify_email` (lines 189–206) so it routes through the transactional sender, not commercial. **Required** — without this, the nudge gets classified as commercial and fails the `_can_send_commercial` guard if `COMPANY_PHYSICAL_ADDRESS` is unset on dev.
  2. Add the public method (place near other `send_*` helpers):
     ```python
     async def send_sales_pipeline_nudge(
         self,
         *,
         recipient_email: str,
         customer_first_name: str | None,
         portal_url: str | None,
         estimate_total: float | None,
         company_name: str = "Grins Irrigation",
     ) -> dict[str, Any]:
         """Send a sales-pipeline auto-nudge email (F6).

         Returns dict with keys ``sent``, ``sent_via``, ``recipient_email``,
         ``content`` matching the established send_* contract.
         """
         classification = self._classify_email("sales_pipeline_nudge")
         html_body = self._render_template(
             "sales_pipeline_nudge.html",
             {
                 "customer_first_name": customer_first_name or "there",
                 "estimate_total": estimate_total,
                 "portal_url": portal_url,
                 "company_name": company_name,
             },
         )
         sent = self._send_email(
             to_email=recipient_email,
             subject="Just checking in on your estimate",
             html_body=html_body,
             email_type="sales_pipeline_nudge",
             classification=classification,
         )
         return {
             "sent": sent,
             "sent_via": "resend" if sent else "pending",
             "recipient_email": recipient_email,
             "content": html_body,
         }
     ```
- **PATTERN**: Existing `send_estimate_sent` / `send_annual_notice` in the same file — same return-shape contract.
- **GOTCHA**: `_send_email` is **synchronous** in this codebase (line 254 — no `async def`); call it without `await`. Confirm by re-reading the existing `send_*` methods.
- **GOTCHA**: Subject must not include "Reminder" or "Follow-up" — those bump spam scores. "Just checking in" is the agreed copy.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_service.py -v -k nudge`

#### Task F6.3 — CREATE `src/grins_platform/services/sales_pipeline_nudge_job.py`

- **IMPLEMENT**: Mirror `OnboardingReminderJob` exactly:
  ```python
  """Background job for sales pipeline auto-nudges (F6).

  Walks SalesEntry rows in {SEND_ESTIMATE, PENDING_APPROVAL, SEND_CONTRACT}
  whose last_contact_date is older than STALE_DAYS and whose nudges are not
  paused. Sends a single nudge email per stale entry per nudge cadence,
  bumps last_contact_date, increments nudge_count if the column exists.

  Validates: F6 sign-off (run-20260504-185844-full).
  """

  from __future__ import annotations

  from datetime import datetime, timedelta, timezone
  from sqlalchemy import select

  from grins_platform.database import get_database_manager
  from grins_platform.log_config import LoggerMixin, get_logger
  from grins_platform.models.enums import SalesEntryStatus
  from grins_platform.models.sales import SalesEntry
  from grins_platform.services.audit_service import AuditService
  from grins_platform.services.email_config import EmailSettings
  from grins_platform.services.email_service import EmailService

  logger = get_logger(__name__)

  STALE_DAYS = 3
  NUDGE_TARGET_STATUSES = (
      SalesEntryStatus.SEND_ESTIMATE.value,
      SalesEntryStatus.PENDING_APPROVAL.value,
      SalesEntryStatus.SEND_CONTRACT.value,
  )


  class SalesPipelineNudgeJob(LoggerMixin):
      """Walks SalesEntry rows and sends auto-nudge emails for stale entries.

      Validates: F6 sign-off (run-20260504-185844-full).
      """

      DOMAIN = "sales_pipeline_nudge"

      async def run(self) -> None:
          self.log_started("run")
          db_manager = get_database_manager()
          now = datetime.now(timezone.utc)
          cutoff = now - timedelta(days=STALE_DAYS)
          email_service = EmailService(EmailSettings())
          audit = AuditService()
          sent_count = 0

          async for session in db_manager.get_session():
              # SalesEntry.customer is lazy="selectin" (models/sales.py:102)
              # so no explicit selectinload() needed.
              stmt = select(SalesEntry).where(
                  SalesEntry.status.in_(NUDGE_TARGET_STATUSES),
                  SalesEntry.last_contact_date.is_not(None),
                  SalesEntry.last_contact_date <= cutoff,
                  (SalesEntry.nudges_paused_until.is_(None))
                  | (SalesEntry.nudges_paused_until <= now),
                  SalesEntry.dismissed_at.is_(None),
              )
              entries = list((await session.execute(stmt)).scalars().all())

              for entry in entries:
                  if await self._process(entry, email_service, audit, session, now):
                      sent_count += 1

              await session.commit()

          self.log_completed("run", entries_nudged=sent_count)

      async def _process(
          self,
          entry: SalesEntry,
          email_service: EmailService,
          audit: AuditService,
          session: AsyncSession,
          now: datetime,
      ) -> bool:
          customer = entry.customer
          if customer is None or not customer.email:
              logger.info(
                  "sales_pipeline.nudge.skipped_no_email",
                  entry_id=str(entry.id),
              )
              return False

          # v1: don't deep-link estimates; nudge copy is generic.
          result = await email_service.send_sales_pipeline_nudge(
              recipient_email=customer.email,
              customer_first_name=customer.first_name,
              portal_url=None,
              estimate_total=None,
          )
          if not result.get("sent"):
              logger.warning(
                  "sales_pipeline.nudge.send_failed",
                  entry_id=str(entry.id),
                  sent_via=result.get("sent_via"),
              )
              return False

          entry.last_contact_date = now
          entry.updated_at = now

          # AuditService.log_action signature: (db, *, action, resource_type,
          # resource_id=None, details=None, ...) — db positional, rest kw-only.
          _ = await audit.log_action(
              session,
              action="sales_pipeline.nudge.sent",
              resource_type="sales_pipeline_entry",
              resource_id=entry.id,
              details={
                  "actor_type": "system",
                  "source": "nightly_job",
                  "recipient_email": customer.email,
                  "status": entry.status,
              },
          )

          logger.info(
              "sales_pipeline.nudge.sent",
              entry_id=str(entry.id),
              status=entry.status,
          )
          return True


  _sales_pipeline_nudge_job = SalesPipelineNudgeJob()


  async def nudge_stale_sales_entries_job() -> None:
      """Async wrapper for the scheduler."""
      await _sales_pipeline_nudge_job.run()
  ```
- **PATTERN**: Mirrors `services/onboarding_reminder_job.py` (singleton, async wrapper, single commit per run, LoggerMixin).
- **GOTCHA**: The explicit `last_contact_date.is_not(None)` filter is **required**. Without it, `last_contact_date <= cutoff` evaluates to NULL on NULL rows — Postgres treats NULL filter results as exclusion which works in practice, but being explicit prevents a future query optimizer surprise.
- **GOTCHA**: `details` includes the `actor_type=system, source=nightly_job` discriminator pair (per `audit_service.py:14–16`) so the admin history view classifies these correctly.
- **GOTCHA**: `entry.id` is a real `UUID` — pass it directly to `resource_id`; don't `str()`-wrap (the helper accepts `UUID | str | None`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py -v`

#### Task F6.4 — UPDATE `src/grins_platform/services/background_jobs.py`

- **IMPLEMENT**:
  - Import the wrapper at the top of the file (alongside other job imports):
    ```python
    from grins_platform.services.sales_pipeline_nudge_job import (
        nudge_stale_sales_entries_job,
    )
    ```
  - In `register_scheduled_jobs()` (after line 1487, before the final `logger.info`), add:
    ```python
    scheduler.add_job(
        nudge_stale_sales_entries_job,
        "cron",
        hour=8,
        minute=15,
        id="nudge_stale_sales_entries",
        replace_existing=True,
    )
    ```
  - Append `"nudge_stale_sales_entries"` to the `jobs=[…]` list in the `logger.info("scheduler.jobs.registered", …)` block.
- **PATTERN**: `escalate_failed_payments_job` registration at lines 1394–1401.
- **GOTCHA**: Cron hour is **UTC**. 8:15 UTC ≈ 3:15 AM Central — that's intentional (sends nudge emails before business hours, lands in inbox by morning). Confirm with the operator before changing.
- **VALIDATE**:
  ```
  uv run python -c "from grins_platform.services.background_jobs import register_scheduled_jobs; from apscheduler.schedulers.background import BackgroundScheduler; s = BackgroundScheduler(); register_scheduled_jobs(s); print([j.id for j in s.get_jobs()])"
  # expected to include 'nudge_stale_sales_entries'
  ```

#### Task F6.5 — CREATE `src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py`

- **IMPLEMENT**:
  - Mirror `tests/unit/test_background_jobs.py::TestFailedPaymentEscalator`.
  - Test cases:
    1. `test_nudge_sends_for_stale_send_estimate` — entry with `status=send_estimate`, `last_contact_date=now-4d`, `nudges_paused_until=None`, `customer.email` present → mocks `send_sales_pipeline_nudge`, asserts called once and `last_contact_date` bumped.
    2. `test_nudge_skips_paused` — same as above but `nudges_paused_until=now+1d` → asserts `send_sales_pipeline_nudge` NOT called.
    3. `test_nudge_skips_dismissed` — `dismissed_at=now-1h` → not called.
    4. `test_nudge_skips_fresh` — `last_contact_date=now-1h` (under cutoff) → not called.
    5. `test_nudge_skips_no_email` — customer with `email=None` → log warning, no exception.
    6. `test_nudge_skips_terminal_status` — `status=closed_won` → not called.
- **PATTERN**: `test_background_jobs.py` — patch `get_database_manager` to return a mock that yields the test session.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py -v`

---

### F3 — START keyword re-opt-in

> **Compliance invariant being upheld**: After a customer texts STOP, no marketing or transactional SMS is delivered to that phone until the customer explicitly opts back in via START. The only messages permitted post-STOP are (a) the one-time STOP confirmation reply, (b) informal-opt-out admin confirmations, and (c) the START opt-in confirmation. These three are required by 10DLC carrier rules and remain intentional bypasses. Every other send path is gated.
>
> The plan upgrades the gate in three layers (see F3.6, F3.7, F3.8 below) so the invariant is enforced even if a future engineer wires a new send path without thinking about consent.

#### Hard-STOP enforcement architecture (audit of every `provider.send_text` call site)

Pre-existing call sites in `src/grins_platform/services/sms_service.py`:

| Line | Call site | Status | Reason |
|---|---|---|---|
| **416** | `send_message` (happy path) | **GATED ✓** | Preceded by `check_sms_consent(...)` at line 286; raises `SMSConsentDeniedError` on hard-STOP. |
| **701** | `_send_via_provider` (private helper) | **UNGATED — needs defensive guard (F3.6)** | Only caller today is `send_automated_message(is_internal=True)` for staff phones. Latent risk if a future caller invokes it for a customer phone. |
| **957** | Poll-reply auto-confirmation | **UNGATED — must close (F3.7)** | After `STOP`, an inbound poll reply could trigger an auto-confirm SMS back to the opted-out phone. This is a real hole, not theoretical. |
| **1227** | STOP confirmation reply | **INTENTIONAL BYPASS** | 10DLC carriers REQUIRE the "you've been unsubscribed" reply. |
| **1608** | Informal-opt-out admin confirmation | **INTENTIONAL BYPASS** | Mirror of STOP confirmation, sent after admin confirms an informal opt-out alert. |
| **NEW (F3.2)** | START opt-in confirmation reply | **INTENTIONAL BYPASS** | 10DLC carriers REQUIRE the opt-in confirmation. |

Indirect call sites (caller of `send_message`, hence transitively gated):
- `services/background_jobs.py:560` — `CampaignWorker._send_one_recipient` calls `send_message(consent_type="marketing")`. Re-checks consent on every iteration of the 60-second batch loop, so a STOP that arrives mid-campaign blocks subsequent sends.
- All other `send_*` helpers in `sms_service.py` route through `send_message`.

#### Race-condition analysis

| Window | What happens | Mitigation |
|---|---|---|
| Inbound STOP webhook is processing in transaction A; outbound campaign send is processing in transaction B | Transaction B's `check_sms_consent` may not see the not-yet-committed STOP record from A | Bounded by request commit time (typically <100 ms). Each campaign batch re-checks consent per-recipient, so the next batch closes the gap. Industry-standard "best effort" — carriers accept this. |
| In-flight `provider.send_text(...)` HTTP call to CallRail/Twilio when STOP arrives | The carrier will deliver the message because it's already accepted | This is unavoidable at the application layer — carriers handle in-flight messages per their own rules. |
| Scheduled message (rate-limited at line 371) waiting in `delivery_status='scheduled'` | Could be picked up by a later worker after STOP | The worker that processes scheduled messages MUST re-check consent — verified above (campaign worker re-routes through `send_message`). Add explicit test (F3.8). |

#### Task F3.1 — UPDATE `src/grins_platform/services/sms/audit.py`

- **IMPLEMENT**: After the existing `log_consent_hard_stop` function (lines 126–137), add (use the module-level `_audit` singleton already at line 21 — do NOT instantiate a new one):
  ```python
  async def log_consent_opt_in_sms(
      db: AsyncSession,
      *,
      phone_masked: str,
      method: str = "text_start",
  ) -> None:
      """Emit ``sms.consent.opt_in_sms_received`` audit event."""
      _ = await _audit.log_action(
          db,
          action="sms.consent.opt_in_sms_received",
          resource_type="sms_consent",
          details={"phone": phone_masked, "method": method},
      )
  ```
- **PATTERN**: Verbatim mirror of `log_consent_hard_stop` (lines 126–137). Same `_audit.log_action(db, ...)` shape (`db` positional; `action`, `resource_type`, `details` keyword-only).
- **GOTCHA**: Use `_ = await ...` to satisfy ruff `RUF` rules about unused `await` results — the existing helpers all do this.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sms_audit.py -v`

#### Task F3.2 — UPDATE `src/grins_platform/services/sms_service.py`

- **IMPLEMENT**:
  - At the top, immediately after `EXACT_OPT_OUT_KEYWORDS` (lines 65–68) and `OPT_OUT_CONFIRMATION_MSG` (lines 82–85), add:
    ```python
    # Exact opt-in keywords (F3 — START re-subscribe)
    EXACT_OPT_IN_KEYWORDS: frozenset[str] = frozenset(
        {"start", "unstop", "subscribe"},
    )

    # Opt-in confirmation message (must include unsubscribe footer for 10DLC)
    OPT_IN_CONFIRMATION_MSG = (
        "You're re-subscribed to Grins Irrigation texts. Reply STOP to unsubscribe."
    )
    ```
  - In `handle_inbound` (line 798, BEFORE the existing STOP keyword check at line 799), insert:
    ```python
    # 10.0: Exact opt-in keyword match (F3) — must run BEFORE STOP check so a
    # phone that previously STOPped can re-subscribe without being denied.
    if body_lower in EXACT_OPT_IN_KEYWORDS:
        return await self._process_exact_opt_in(
            from_phone, body_lower, thread_id=thread_id,
        )
    ```
  - Below `_process_exact_opt_out` (after line 1244), add the new `_process_exact_opt_in` method as a **line-for-line mirror** of `_process_exact_opt_out` (lines 1136–1244) with these exact substitutions:
    1. Phone resolution block (lines 1157–1186): identical — copy verbatim.
    2. `SmsConsentRecord(...)` constructor (lines 1188–1199): change to:
       ```python
       record = SmsConsentRecord(
           phone_number=formatted_phone,
           consent_type="marketing",
           consent_given=True,
           consent_timestamp=now,
           consent_method="text_start",
           consent_language_shown=f"Keyword: {keyword}",
           # opt_out_* fields explicitly None: this is an opt-IN record
       )
       ```
    3. Replace `await log_consent_hard_stop(...)` (line 1204) with `await log_consent_opt_in_sms(self.session, phone_masked=_mask_phone(formatted_phone))` (import this from `grins_platform.services.sms.audit`).
    4. Replace `await self._record_customer_sms_opt_out_audit(action="consent.opt_out_sms", ...)` (lines 1210–1216) with `await self._record_customer_sms_opt_in_audit(action="consent.opt_in_sms", phone_e164=formatted_phone, consent_record_id=record.id, raw_body=keyword)` (new sister method — see F3.4).
    5. Drop the informal-alert auto-ack block (lines 1218–1224) — unnecessary on opt-in.
    6. Replace `await self.provider.send_text(formatted_phone, OPT_OUT_CONFIRMATION_MSG)` (line 1227) with `OPT_IN_CONFIRMATION_MSG`. **Critical ordering**: insert record → `await self.session.flush()` → THEN `provider.send_text` → THEN audit. The new record must exist BEFORE the send so `check_sms_consent()` (called inside the provider abstraction in some paths) doesn't deny the confirmation message itself.
    7. Touch lead `last_contacted` (line 1231): identical — copy verbatim.
    8. Return dict (lines 1239–1244): change `"action": "opt_out"` to `"action": "opt_in"` and use `OPT_IN_CONFIRMATION_MSG`.
- **PATTERN**: `_process_exact_opt_out` (lines 1136–1244) is the exact structural mirror.
- **GOTCHA — CRITICAL (resolved)**: `services/sms/consent.py::_has_hard_stop` (lines 162–176) currently returns True on ANY historical `(consent_method='text_stop', consent_given=False)` row. **F3.3 below refactors it to latest-record-wins — that refactor is mandatory, not optional.** Without it, `_process_exact_opt_in` writes a clean record but `check_sms_consent()` still returns False forever.
- **GOTCHA**: 10DLC requires the auto-reply confirmation to be sent on opt-in. The `provider.send_text` call inside `_process_exact_opt_in` must fire AFTER the new consent record is flushed but BEFORE return.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/test_sms_service.py -v -k "start or opt_in"
  ```

#### Task F3.3 — UPDATE `src/grins_platform/services/sms/consent.py` — **MANDATORY**

- **IMPLEMENT**: Refactor `_has_hard_stop` (lines 162–176) to latest-record-wins semantics, scoped over phone variants (NOT customer_id — some inbound STOPs land before customer correlation):
  ```python
  async def _has_hard_stop(session: AsyncSession, e164: str) -> bool:
      """Check if the *latest* consent record for the phone is a hard STOP.

      The SmsConsentRecord table is INSERT-ONLY, so the current state for a
      phone is whichever row has the newest ``created_at`` among all phone
      variants we accept. This means a later ``text_start`` opt-in row
      supersedes any earlier ``text_stop`` row, restoring sending eligibility.
      """
      stmt = (
          select(SmsConsentRecord)
          .where(SmsConsentRecord.phone_number.in_(_phone_variants(e164)))
          .order_by(SmsConsentRecord.created_at.desc())
          .limit(1)
      )
      result = await session.execute(stmt)
      latest = result.scalar_one_or_none()
      if latest is None:
          return False
      return (
          latest.consent_method == "text_stop"
          and latest.consent_given is False
      )
  ```
  Also update the module docstring (lines 8–9): replace "if **any** SmsConsentRecord row" with "if the **latest** SmsConsentRecord row (by `created_at`)" so the code matches the docstring.
- **PATTERN**: `repositories/sms_consent_repository.py::get_latest_for_customer` (lines 91–123) — same intent, customer-keyed; the new `_has_hard_stop` is the phone-keyed twin.
- **GOTCHA**: Order by `created_at` (server-set), not `consent_timestamp` — `consent_timestamp` is provided by the inserter and could collide for rapid back-to-back STOP/START in tests. `created_at` has `server_default=func.now()` and is monotonic.
- **GOTCHA**: This refactor changes the documented hard-STOP precedence rule. Re-read the existing `test_pbt_sms_consent_gating.py` properties — any property that asserts "any historical STOP wins" must be updated to "latest record wins". Expect ~1–2 test signature changes.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/unit/test_pbt_sms_consent_gating.py -v
  uv run pytest src/grins_platform/tests/unit/test_sms_consent_repository.py -v
  uv run pytest src/grins_platform/tests/test_sms_service.py -v -k "consent or opt_out"
  ```

#### Task F3.4 — UPDATE `src/grins_platform/services/sms_service.py` (audit twin) and `src/grins_platform/services/audit_service.py` (canonical action list)

- **IMPLEMENT**:
  1. Add a new `_record_customer_sms_opt_in_audit` method on `SMSService`, immediately after `_record_customer_sms_opt_out_audit` (lines 1388–1448), as a near-mirror:
     ```python
     async def _record_customer_sms_opt_in_audit(
         self,
         *,
         action: str,  # "consent.opt_in_sms"
         phone_e164: str,
         consent_record_id: UUID | None,
         raw_body: str,
         customer_id: UUID | None = None,
     ) -> None:
         """Audit a customer opt-IN event (F3 — gap-05 sister of opt-out)."""
         from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
             AuditLogRepository,
         )
         try:
             repo = AuditLogRepository(self.session)
             resource_id: UUID | str | None = (
                 customer_id if customer_id is not None else phone_e164
             )
             resource_type = "customer" if customer_id is not None else "phone"
             _ = await repo.create(
                 action=action,
                 resource_type=resource_type,
                 resource_id=resource_id,
                 actor_id=None,
                 details={
                     "actor_type": "customer",
                     "source": "customer_sms",
                     "phone_e164": phone_e164,
                     "consent_record_id": (
                         str(consent_record_id)
                         if consent_record_id is not None
                         else None
                     ),
                     "raw_body": raw_body,
                 },
             )
         except Exception:
             logger.warning(
                 "sms.opt_in.audit_write_failed",
                 action=action,
                 phone=_mask_phone(phone_e164),
                 exc_info=True,
             )
     ```
  2. Add `consent.opt_in_sms` to the canonical action-name docstring list in `services/audit_service.py` at lines 31–35, immediately after `consent.opt_out_sms`. New line:
     ```
     - ``consent.opt_in_sms``                         — START keyword opt-in (F3)
     ```
- **PATTERN**: `_record_customer_sms_opt_out_audit` (sms_service.py:1388–1448) — verbatim mirror minus the `alert_id` parameter (opt-in flow has no informal-alert correlation).
- **GOTCHA**: This method writes via `AuditLogRepository(self.session).create(...)` directly — NOT via `AuditService`. That's the established gap-05 path for customer-driven audits. Don't accidentally re-route through `AuditService.log_action`.
- **VALIDATE**: Same as F3.2 plus `uv run pytest src/grins_platform/tests/unit/test_audit_service.py -v -k consent` to confirm canonical-list expectations don't reject the new action name.

#### Task F3.6 — UPDATE `src/grins_platform/services/sms_service.py` — defensive consent guard inside `_send_via_provider`

- **IMPLEMENT**: Refactor `_send_via_provider` (lines 687–701) to require an explicit bypass-consent flag from callers:
  ```python
  async def _send_via_provider(
      self,
      phone: str,
      message: str,
      *,
      bypass_consent: bool = False,
      bypass_reason: str | None = None,
  ) -> ProviderSendResult:
      """Send message via the configured provider.

      Defense-in-depth consent guard: any caller that bypasses the
      ``send_message`` flow MUST pass ``bypass_consent=True`` with a
      ``bypass_reason`` documenting why. The three legitimate bypasses
      today are (a) STOP confirmation, (b) informal-opt-out admin
      confirmation, (c) START opt-in confirmation. Every other path
      should call ``send_message`` so the consent gate runs.
      """
      if not bypass_consent:
          # Defensive check — operational consent type still allows
          # so internal staff messages keep working; only customer-facing
          # ungated calls are blocked.
          has_consent = await check_sms_consent(
              self.session,
              phone,
              consent_type="transactional",
          )
          if not has_consent:
              masked = _mask_phone(phone)
              logger.warning(
                  "sms.provider.send_blocked_by_defensive_gate",
                  phone=masked,
                  bypass_reason=bypass_reason,
              )
              msg = (
                  f"Defensive consent gate blocked send to {masked}. "
                  f"Caller did not pass bypass_consent and the phone has hard-STOP."
              )
              raise SMSConsentDeniedError(msg)
      return await self.provider.send_text(phone, message)
  ```
  Then update the existing internal-staff caller at line 616 (`send_automated_message(is_internal=True)`) to pass `bypass_consent=True, bypass_reason="internal_staff_notification"` — staff phones never have customer consent records, so the defensive check would always block.
- **PATTERN**: This mirrors the explicit-bypass pattern used by `EmailService._can_send_commercial`-style guards.
- **GOTCHA**: The defensive check is a **belt-and-suspenders** — `send_message` already gates at line 286, so this is the SECOND layer that catches anyone who skips `send_message`. Without this, a future engineer who calls `_send_via_provider` directly inherits no protection.
- **GOTCHA — CRITICAL**: The three intentional-bypass call sites (lines 1227, 1608, F3.2's new opt-in confirm) currently call `self.provider.send_text(...)` directly, NOT `_send_via_provider`. They should be migrated in this task to call `_send_via_provider(phone, msg, bypass_consent=True, bypass_reason="stop_confirmation"|"informal_opt_out_confirmation"|"opt_in_confirmation")` so the bypass intent is explicit and auditable. This is a refactor of three line-level call sites — small, but required for the invariant to hold.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/test_sms_service.py -v -k "defensive or bypass"
  ```

#### Task F3.7 — UPDATE poll-reply auto-confirmation at `src/grins_platform/services/sms_service.py:957`

- **IMPLEMENT**: The poll-reply auto-confirm (lines 947–957) currently calls `self.provider.send_text(row.phone, confirmation_msg)` directly with no consent check. Replace with a consent-gated send. **Two options** — pick option A:
  - **Option A (recommended)**: Route through `send_message` with `consent_type="transactional"`:
    ```python
    from grins_platform.services.sms.recipient import Recipient  # noqa: PLC0415
    recipient = Recipient(
        phone=row.phone,
        source_type="customer",
        customer_id=row.customer_id,
    )
    try:
        _ = await self.send_message(
            recipient=recipient,
            message=confirmation_msg,
            message_type=MessageType.AUTOMATED_NOTIFICATION,  # or POLL_REPLY if enum exists
            consent_type="transactional",
            skip_formatting=True,
        )
    except SMSConsentDeniedError:
        logger.info(
            "sms.poll_reply.auto_reply_blocked_by_consent",
            phone=_mask_phone(row.phone),
        )
    ```
  - **Option B (only if AUTOMATED_NOTIFICATION enum doesn't fit)**: Call `_send_via_provider(row.phone, confirmation_msg, bypass_consent=False)` so the new defensive gate from F3.6 kicks in.
- **PATTERN**: Option A mirrors the appointment-confirmation auto-reply at lines 1085–1098 — same `send_message` shape with try/except `SMSConsentDeniedError`.
- **GOTCHA**: The original line 957 call had no consent check because pollreplies were assumed to be from already-engaged customers. Post-STOP customers can still receive polls in flight, then text back, and trigger this path. Closing this hole is required for the invariant.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/unit/test_sms_service_gaps.py -v -k "poll"
  uv run pytest src/grins_platform/tests/test_sms_service.py -v -k "poll_reply"
  ```

#### Task F3.8 — CREATE `src/grins_platform/tests/integration/test_hard_stop_invariant.py`

- **IMPLEMENT**: Property-based + scripted invariant test, asserting **no customer SMS is ever delivered after STOP** across every send path:
  1. **Property test (Hypothesis)**: For any random sequence of `(STOP | START | SEND_*)` events on a single phone, after the LAST STOP and before any subsequent START, NO call to `provider.send_text` happens for any non-bypass `consent_type`. Use `hypothesis.strategies.lists` of an enum of events; mock `provider.send_text` and assert the call count.
  2. **Scripted scenario tests** — cover every send path explicitly:
     - `test_stop_blocks_send_message_marketing` — `consent_type="marketing"` raises `SMSConsentDeniedError`.
     - `test_stop_blocks_send_message_transactional` — `consent_type="transactional"` raises `SMSConsentDeniedError`.
     - `test_stop_allows_operational` — `consent_type="operational"` succeeds (legal notices etc.).
     - `test_stop_blocks_send_automated_message` — `send_automated_message(is_internal=False)` returns `{"success": False, "reason": "opted_out"}`.
     - `test_stop_blocks_campaign_worker_iteration` — directly invokes `CampaignWorker._send_one_recipient` for an opted-out recipient; asserts the recipient transitions to `failed` with `error_message` mentioning consent.
     - `test_stop_blocks_poll_reply_auto_confirm` — sets up an opted-out customer with an inbound poll reply; asserts no `provider.send_text` call (proves F3.7 fix).
     - `test_stop_blocks_defensive_gate_in_send_via_provider` — calls `_send_via_provider(opted_out_phone, "msg")` without `bypass_consent`; asserts `SMSConsentDeniedError` (proves F3.6 fix).
     - `test_stop_confirmation_itself_is_delivered` — STOP arrives; assert exactly one `provider.send_text(phone, OPT_OUT_CONFIRMATION_MSG)` call (the carrier-required reply). This is the ONE intentional post-STOP send.
     - `test_start_after_stop_unblocks_subsequent_send` — STOP, then START, then `send_message(consent_type="transactional")`; assert send succeeds.
     - `test_start_then_stop_re_blocks` — STOP, START, STOP again; assert subsequent `send_message` is blocked (proves latest-wins).
     - `test_scheduled_message_picked_up_after_stop_is_blocked` — create a `delivery_status='scheduled'` SentMessage row; ingest STOP; have the scheduled-message worker process the row; assert no `provider.send_text` call.
- **PATTERN**: Existing property tests in `tests/unit/test_pbt_sms_consent_gating.py` show the Hypothesis strategy shape.
- **GOTCHA**: Use the `null` SMS provider (`SMS_PROVIDER=null`) to avoid hitting real providers; `provider.send_text` becomes a `MagicMock` you can assert on.
- **GOTCHA**: Reset `provider.send_text.mock_calls` between scripted scenarios so cross-test pollution doesn't fool a `assert_not_called`.
- **VALIDATE**:
  ```
  uv run pytest src/grins_platform/tests/integration/test_hard_stop_invariant.py -v
  ```

---

#### Task F3.5 — CREATE `src/grins_platform/tests/integration/test_sms_start_keyword.py`

- **IMPLEMENT**: End-to-end test with a real test session and test customer:
  1. Send a `STOP` inbound → verify `_has_hard_stop` is True, `check_sms_consent` returns False, attempting `send_message` returns/raises `SMSConsentDeniedError`.
  2. Send a `START` inbound on the same phone → verify a new `SmsConsentRecord(consent_method="text_start", consent_given=True)` exists, `_has_hard_stop` is False, `check_sms_consent` returns True, audit log has `sms.consent.opt_in_sms_received`, and outbound `OPT_IN_CONFIRMATION_MSG` was sent.
  3. Send another `STOP` after the START → verify `_has_hard_stop` is True again (latest record wins).
- **PATTERN**: `tests/test_sms_service.py` integration-style test pattern.
- **GOTCHA**: Use the seed customer phone `+19527373312` per memory `feedback_sms_test_number.md` only if the test actually hits the live provider. Tests using a Null provider can use any phone.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_sms_start_keyword.py -v`

---

## TESTING STRATEGY

Tests live under `src/grins_platform/tests/{unit,integration,functional}` for backend and `frontend/src/**/__tests__/*.test.tsx` for frontend, mirroring existing layout.

### Unit Tests

| Layer | New / Updated Tests |
|---|---|
| **F2** | `test_service_offering_repository.py` — add `test_search_by_name`, `test_search_by_slug`, `test_search_by_subcategory`, `test_search_combined`, `test_search_empty_string_means_no_filter`. |
| **F2** | `test_services_api.py` — add `test_search_query_param_propagated_to_service`. |
| **F2** | `PriceListEditor.test.tsx` — add `test_search_passes_to_api_after_debounce`, `test_clearing_search_removes_param`. |
| **F3** | `test_sms_service.py` — add `test_start_keyword_creates_opt_in_record`, `test_start_keyword_sends_confirmation`, `test_start_keyword_clears_hard_stop`, `test_unstop_synonym`. |
| **F3** | `test_sms_audit.py` — add `test_log_consent_opt_in_emits_correct_action`. |
| **F3** | `test_pbt_sms_consent_gating.py` — add property: `for_any_history_ending_in_text_start_consent_is_True`. |
| **F4** | `test_email_config.py` — add `test_log_warns_on_deprecated_portal_host`, `test_log_silent_on_canonical_host`. |
| **F5** | `EstimateReview.approval.test.tsx` (new) — production-router test that confirms approve → confirmed page. |
| **F6** | `test_sales_pipeline_nudge_job.py` — six cases listed in F6.5. |

### Integration Tests

| Test | Purpose |
|---|---|
| `test_sms_start_keyword.py` (new, F3) | Full STOP → START → STOP round-trip on a single phone. |
| `test_sales_pipeline_nudge_job.py::test_full_run_against_real_session` | Insert 3 SalesEntry rows (1 stale, 1 paused, 1 fresh) and assert exactly 1 nudge sent. |
| Existing `test_portal_api.py` | Already covers backend approve; ensure still green. |

### Edge Cases

- **F2**: Empty search input (`""`) should not send `?search=` (axios drops undefined; explicit empty string would make the backend treat empty as no-filter — already covered by `if search:` check).
- **F2**: Search by special characters (`%`, `_` — SQL ILIKE wildcards) — should be safe because parameterized queries escape them; **add a regression test**.
- **F3**: `START` followed immediately by another `START` (idempotent) — should create two records, latest still wins, no error.
- **F3**: `START` from a phone that never STOP'd — should still create a `text_start` record + send confirmation (defensive, harmless).
- **F3**: Mixed-case `Start`, `start`, `START` — `body_lower` handles this. **Add a test for each casing variant.**
- **F4**: Empty `PORTAL_BASE_URL` env var → should default to `http://localhost:5173` and the deprecated-host warning must NOT fire.
- **F5**: Double-clicking Approve while the mutation is pending — TanStack Query's default `useMutation` doesn't dedupe; either (a) disable the button on `approve.isPending`, or (b) add a guard. Add a test that asserts the button has `disabled` while pending.
- **F6**: A SalesEntry with `customer_id=None` (orphan) — should skip and log, not throw.
- **F6**: `nudges_paused_until` is in the past — should be treated as "no longer paused" and nudge eligible.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check src/grins_platform/services/sms_service.py \
                  src/grins_platform/services/sms/audit.py \
                  src/grins_platform/services/sms/consent.py \
                  src/grins_platform/services/sales_pipeline_nudge_job.py \
                  src/grins_platform/services/background_jobs.py \
                  src/grins_platform/services/email_config.py \
                  src/grins_platform/services/email_service.py \
                  src/grins_platform/api/v1/services.py \
                  src/grins_platform/services/service_offering_service.py \
                  src/grins_platform/repositories/service_offering_repository.py
uv run ruff format --check src/grins_platform/

# Frontend
cd frontend
npm run lint
npm run typecheck
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
# F2
uv run pytest src/grins_platform/tests/unit/test_service_offering_repository.py \
              src/grins_platform/tests/unit/test_service_offering_service.py \
              src/grins_platform/tests/test_services_api.py -v

# F3
uv run pytest src/grins_platform/tests/test_sms_service.py \
              src/grins_platform/tests/unit/test_sms_audit.py \
              src/grins_platform/tests/unit/test_pbt_sms_consent_gating.py \
              src/grins_platform/tests/unit/test_sms_consent_repository.py \
              src/grins_platform/tests/unit/test_sms_service_gaps.py -v -k "consent or stop or opt_in or poll or bypass or defensive"

# F3 — compliance invariant (THE proof that STOP blocks every send path)
uv run pytest src/grins_platform/tests/integration/test_hard_stop_invariant.py -v

# F4
uv run pytest src/grins_platform/tests/unit/test_email_config.py -v

# F6
uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py \
              src/grins_platform/tests/unit/test_email_service.py -v -k "nudge or sales"

# Frontend (F2 + F5)
cd frontend
npm test -- PriceListEditor.test.tsx
npm test -- EstimateReview.test.tsx EstimateReview.approval.test.tsx ContractSigning.test.tsx
```

### Level 3: Integration Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
# F3 — STOP → START → STOP round-trip
uv run pytest src/grins_platform/tests/integration/test_sms_start_keyword.py -v

# Full backend suite (regression sweep — must remain green)
uv run pytest src/grins_platform/tests -v --maxfail=5

# Single-head Alembic check (no migrations added by this plan, but verify)
bash scripts/check-alembic-heads.sh
```

### Level 4: Manual Validation

#### F2 — Pricelist search
1. `cd frontend && npm run dev` (separate terminal: `uv run uvicorn grins_platform.app:app --reload`)
2. Log in as admin, navigate to `/invoices?tab=pricelist`.
3. Type `"Spring"` in the search input. Wait 300ms.
4. **Expected**: 2 rows (`spring_startup_residential`, `spring_startup_commercial`) appear, regardless of pagination.
5. Clear the search → full 73-row paginated list returns.

#### F3 — START re-opt-in
**Test phone is `+19527373312` only (per `feedback_sms_test_number.md`).**
1. Trigger appointment confirmation SMS for the seed customer.
2. Reply `STOP` from the test phone.
3. Confirm `consent.opt_out_sms` audit + 403 on next `/sms/send`.
4. Reply `START` from the test phone.
5. **Expected**: receive opt-in confirmation SMS within ~30 sec; `/sms/send` no longer 403s.
6. `curl $API/api/v1/audit-log?action=sms.consent.opt_in_sms_received` returns the new row.

#### F4 — PORTAL_BASE_URL
1. After Railway env-var update + redeploy, send a real estimate to the seed customer.
2. Open the email at `kirillrakitinsecond@gmail.com`.
3. Click the portal link.
4. **Expected**: lands on a working portal page with the estimate (NOT a 404).
5. Repeat with the dev backend booted locally — confirm the structured-log warning DOES NOT fire (canonical host).
6. Temporarily set `PORTAL_BASE_URL=https://frontend-git-dev-kirilldr01s-projects.vercel.app` locally and reboot — confirm the warning DOES fire on boot.

#### F5 — Approve → Confirmed
1. With F4 fixed (portal link works), open a real estimate portal URL.
2. Click "Approve Estimate".
3. **Expected**: navigate to `/portal/estimates/:token/confirmed`; see "Estimate Approved!" with next-steps card. NO "unexpected application error".
4. Backend audit log shows `estimate.approved` (or equivalent) with `action_source=customer_portal`.

#### F6 — Sales pipeline nudge
1. Insert a SalesEntry with `status=send_estimate`, `last_contact_date=now-4d`, `nudges_paused_until=NULL` for the seed customer.
2. Manually trigger the job:
   ```
   uv run python -c "import asyncio; from grins_platform.services.sales_pipeline_nudge_job import _sales_pipeline_nudge_job; asyncio.run(_sales_pipeline_nudge_job.run())"
   ```
3. **Expected**: `kirillrakitinsecond@gmail.com` receives the nudge email; `last_contact_date` on the entry is bumped to ~now; audit log has `sales_pipeline.nudge.sent`.

### Level 5: Additional Validation

```bash
# Re-run the master-plan E2E phases that originally caught these
bash e2e/master-plan/run-phase.sh 09  # SMS (F3)
bash e2e/master-plan/run-phase.sh 4b  # Pricelist editor (F2)
bash e2e/master-plan/run-phase.sh 5   # Customer portal (F4, F5)
# F6 — no automated phase yet; add one to master-e2e-testing-plan.md as Phase 4f per the report
```

---

## ACCEPTANCE CRITERIA

- [ ] **F2**: `/api/v1/services?search=Spring` returns the 2 spring rows on dev. The pricelist editor search input finds rows on any page.
- [ ] **F3 (functional)**: After STOP, replying START on `+19527373312` (a) creates a new `sms_consent_records` row with `consent_method="text_start"` and `consent_given=True`, (b) the customer receives `OPT_IN_CONFIRMATION_MSG`, (c) `check_sms_consent` returns True, (d) `sms.consent.opt_in_sms_received` audit row exists.
- [ ] **F3 (compliance invariant)**: `tests/integration/test_hard_stop_invariant.py` passes for every scenario. After STOP, the ONLY successful `provider.send_text` call observed is `OPT_OUT_CONFIRMATION_MSG` (one-time carrier-required reply). Subsequent marketing, transactional, automated, campaign-worker, scheduled-replay, and poll-reply paths all block. After START on a previously-STOPped phone, sends resume.
- [ ] **F3 (defense-in-depth)**: `_send_via_provider` rejects unauthenticated calls (no `bypass_consent=True`) for opted-out phones with `SMSConsentDeniedError`. The three intentional bypass call sites all pass `bypass_consent=True` with a documented `bypass_reason`.
- [ ] **F4**: Railway dev `PORTAL_BASE_URL` is the canonical alias. Sending an estimate produces a clickable, non-404 portal link. Boot-time warning fires when env var matches the deprecated alias.
- [ ] **F5**: Clicking Approve in the portal navigates to `/portal/estimates/:token/confirmed` and renders the confirmation page. No "unexpected application error". Same for Reject and for Contract sign.
- [ ] **F6**: After deploy, `apscheduler` reports `nudge_stale_sales_entries` in its registered jobs. Stale `send_estimate`/`pending_approval`/`send_contract` entries with `last_contact_date <= now-3d` and unpaused get a single nudge email at the next 8:15 UTC fire; `last_contact_date` is bumped; audit log has `sales_pipeline.nudge.sent`.
- [ ] All Level 1, 2, 3 validation commands pass with zero errors.
- [ ] Manual validation Level 4 steps pass for each fix.
- [ ] No regressions in the full pytest suite or `pnpm test` / `npm test`.
- [ ] `scripts/check-alembic-heads.sh` clean (no migration drift).
- [ ] PR description references the candidate findings IDs F2, F3, F4, F5, F6 and links to the run directory `e2e-screenshots/master-plan/runs/run-20260504-185844-full/`.
- [ ] Master plan (`.agents/plans/master-e2e-testing-plan.md`) updated to add Phase 4f (sales-pipeline auto-nudge cron verification) per the original sign-off report's recommendation.

---

## COMPLETION CHECKLIST

- [ ] All tasks F2.1–F2.6, F3.1–F3.8, F4.1–F4.3, F5.1–F5.5, F6.1–F6.5 completed in order
- [ ] Each task validation passed immediately after the task
- [ ] All five Level-1/2/3/4 validation suites green
- [ ] Manual end-to-end on dev with the seed customer phone + email
- [ ] No linting or type-checking errors (ruff, mypy, pyright, eslint, tsc)
- [ ] Sign-off report updated: promote F3, F4, F5, F6 from "candidate" to "resolved", note F2 as resolved
- [ ] Memory updated if anything surprising emerges (per `feedback_bug_reporting_workflow.md` workflow — only stage in master plan first; only after 100% verification, promote)
- [ ] Single PR titled `fix(e2e-signoff): F2/F3/F4/F5/F6 from run-20260504-185844-full` co-authored with Claude
- [ ] Railway env-var change communicated to ops in the PR description (since it's not in code)

---

## NOTES

### Design decisions

- **One PR, five fixes.** Per memory `feedback_bug_reporting_workflow.md` and the umbrella pattern observed in commits `eba4162`, `dadbacc`, splitting these would create five tiny PRs that all share the same e2e-rerun cost. Keep them bundled.
- **F3 placement**: START handler goes in `sms_service.py` (consent layer), NOT in `job_confirmation_service.py` (appointment-reply parser). The existing comment at `job_confirmation_service.py:43–45` is explicit that compliance keywords don't belong in the keyword map. Respect that boundary.
- **F3 latest-record semantics — VERIFIED MANDATORY**: confirmed via direct read of `services/sms/consent.py:162–176` and module docstring `lines 8–9`. The current rule "ANY historical text_stop wins" is what's documented and what the SQL implements. The plan refactors **both** the docstring and `_has_hard_stop` to "latest-by-`created_at` wins". This is the only single change that actually unblocks START re-opt-in.
- **F3 audit twin uses direct `AuditLogRepository`**: confirmed via read of `sms_service.py:1388–1448`. Customer-driven audit events go through `AuditLogRepository(self.session).create(...)` directly with the gap-05 discriminator (`actor_type=customer, source=customer_sms`). Sister method must follow the same pattern, NOT route through `AuditService.log_action`.
- **F3 hard-STOP invariant — defense in depth**: the user explicitly asked for 100% confidence that STOP blocks every future send. Three layers of enforcement guarantee this:
  1. **Layer 1 — write-before-send ordering**: STOP handler (`_process_exact_opt_out`) writes the consent record and `await session.flush()`-es it BEFORE returning. Any subsequent `send_message` call within the same session sees it; the request commit makes it visible across the application.
  2. **Layer 2 — pre-send consent gate** (`send_message` line 286): every customer-facing send routes through `check_sms_consent` → `_has_hard_stop`. After F3.3's latest-wins refactor, the gate stays True forever after STOP unless a later START supersedes.
  3. **Layer 3 — defensive guard inside `_send_via_provider`** (F3.6, new): any code path that bypasses `send_message` and calls `_send_via_provider` must explicitly opt out with `bypass_consent=True` + a documented `bypass_reason`. Forgetting raises `SMSConsentDeniedError`. This catches future-engineer mistakes by construction.
- **F3 ungated hole at line 957 (poll-reply auto-confirm)**: F3.7 closes this by routing through `send_message` so the consent gate runs.
- **F3 in-flight race window**: bounded by request commit time (typically <100 ms) and explicitly accepted by 10DLC carrier rules. Each campaign batch re-checks per-recipient, so the next batch closes any gap.
- **F3 invariant test**: F3.8's property + scripted test exercises every send path AFTER STOP and asserts the ONLY observed `provider.send_text` is the one-time STOP confirmation reply. This is the falsifiable proof of the compliance invariant.
- **F4 boot-time guard**: Could have been a hard fail (raise on boot) but a structured warning is sufficient for dev — prod will catch it on deploy log review. Hard-failing on the deprecated host could brick a service if Railway has a momentary lookup glitch.
- **F5 confirmation route**: The component (`ApprovalConfirmation`) and the navigate target both exist. Only the route registration was missing. This is a pure infra-paperwork fix.
- **F5 error surface uses existing `<Alert>`**: confirmed at `frontend/src/components/ui/alert.tsx:5–58` — exports `Alert`, `AlertTitle`, `AlertDescription` with `variant="destructive"`. Don't invent a new shared component.
- **F6 cadence**: 3-day stale threshold + daily 8:15 UTC fire is a v1 default. Operations may want this tunable via `BusinessSetting` later — note for follow-up but **don't add the setting in this PR** (per "no half-finished implementations" rule).
- **F6 email content**: v1 nudge is generic ("just checking in"). Deep-linked estimate URLs (the portal_url merge field) are a v2 concern that should land alongside a SalesEntry → Estimate FK confirmation step.
- **F6 transactional classification**: confirmed at `email_service.py:189–206` — the `transactional_types` set must include `"sales_pipeline_nudge"` or the send is reclassified as commercial and fails on dev (no `COMPANY_PHYSICAL_ADDRESS`). This is in the task list.
- **F6 audit signature verified**: `AuditService.log_action(db, *, action, resource_type, resource_id=None, details=None, ...)` per direct read of `services/audit_service.py:77–120`. `db` positional, rest kw-only. Helper `details` includes the canonical `actor_type=system, source=nightly_job` discriminator.

### Trade-offs

- **F2 server-side search vs. preloading all 73 rows**: client-side filter on a 73-row dataset is fine ergonomically. But once the seed grows past a few hundred rows the bug recurs in prod, so server-side is the right call once and forever.
- **F3 `UNSTOP` and `SUBSCRIBE` synonyms**: included to match T-Mobile / Verizon best-practice docs. If the operator wants a stricter "START only" surface, drop the synonyms — but document why.
- **F5 surfacing mutation errors**: this is a small UX upgrade beyond the bug. It's tightly scoped (4 lines of JSX in 2 components) and prevents the next "silent error swallowed" report. Keep.
- **F6 first-pass simplicity**: the job is intentionally minimal — query, send, bump timestamp. No "max nudges per entry," no "per-status custom copy." Those are v2.

### Confidence assessment

**Confidence Score: 10/10** that an execution agent completes this in one pass.

Each previously open risk has been verified against the actual source and pinned in the task body:

| Prior risk | Resolution | Verified at |
|---|---|---|
| F3 — `_has_hard_stop` semantics unknown | Read directly: matches ANY historical opt-out. F3.3 refactor is mandatory and the exact replacement code is inlined in the task. | `services/sms/consent.py:162–176` |
| F3 — opt-in audit shape unknown | Read directly: customer-driven audits use `AuditLogRepository(...).create(...)` with `actor_type=customer, source=customer_sms` discriminator. F3.4 inlines the full mirror method. | `services/sms_service.py:1388–1448` |
| F3 — canonical action name | Action-name docstring list at `services/audit_service.py:31–34` lists `consent.opt_out_sms` etc. Plan adds `consent.opt_in_sms` to that list (F3.4 task). | `services/audit_service.py:19–35` |
| F6 — `AuditService.log_action` signature | Read directly: `(db, *, actor_id=None, actor_role=None, action, resource_type, resource_id=None, details=None, ip_address=None, user_agent=None)`. Plan now contains the verbatim call site. | `services/audit_service.py:77–120` |
| F6 — template directory path | Verified: `templates/emails/` (plural). Plan corrected throughout. | `templates/emails/*.html` listing |
| F6 — transactional classification | Verified: `_classify_email` set at lines 189–206; plan now requires adding `"sales_pipeline_nudge"` there. | `services/email_service.py:189–206` |
| F6 — `selectinload(SalesEntry.customer)` redundancy | Verified: `SalesEntry.customer` is `lazy="selectin"` already; explicit option dropped. | `models/sales.py:102` |
| F5 — error banner component | Verified: `<Alert variant="destructive">` exists. Plan now uses it directly with imports specified. | `frontend/src/components/ui/alert.tsx:5–58` |
| F4 — Railway env-var change is operational | Mitigation: code-level boot-time warning in `email_config.py` is the durable safeguard regardless of dashboard access. The dashboard step is documented but not a code blocker. | F4.2 task |
| F5 — `ApprovalConfirmation` route + component | Both verified — component at `frontend/src/features/portal/components/ApprovalConfirmation.tsx` (lines 47–88), route registration at `core/router/index.tsx:159–177` is the only missing piece. | grep results above |

All other tasks remain mechanical mirroring of existing patterns. The plan is now self-contained — an execution agent can implement top-to-bottom without external clarification.
