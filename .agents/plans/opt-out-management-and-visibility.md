# Feature: Opt-Out Management & Visibility (Gap 06)

The following plan is derived from `feature-developments/scheduling gaps/gap-06-opt-out-management.md`. It is complete, but you MUST validate documentation and codebase patterns and task sanity before starting implementation.

Pay special attention to naming of existing utils, types, and models. Import from the right files:
- `AlertType` / `AlertSeverity` live in `grins_platform.models.enums`
- `AlertRepository` lives in `grins_platform.repositories.alert_repository`
- `check_sms_consent` lives in `grins_platform.services.sms.consent`
- `SmsConsentRecord` lives in `grins_platform.models.sms_consent_record`
- `LoggerMixin` / `get_logger` live in `grins_platform.log_config`
- `ManagerOrAdminUser` auth dep lives in `grins_platform.api.v1.auth_dependencies`

## Feature Description

Harden the SMS opt-out pipeline so informal "please stop texting me" signals are (a) surfaced to admins for triage and (b) visible in every UI where an admin could accidentally send SMS to someone who has asked to be left alone. Covers two coordinated gaps:

- **6.A — Informal opt-out triage.** Today `_flag_informal_opt_out` only emits a structured-log line. It does NOT write an `Alert` row, does NOT suppress subsequent marketing/reminder sends, and is invisible to admins. This task wires the missing Alert creation, adds a dedicated dashboard widget + review queue, adds an auto-suppression window for marketing/reminder tiers between flagging and admin action, and emits `AuditLog` entries for every transition.
- **6.B — Opt-out visibility.** Today customer opt-out state (`SmsConsentRecord(consent_given=False)`) is only exposed as a buried boolean on `CustomerDetail`'s comm-prefs form. This task introduces a shared `<OptOutBadge />` component, renders it across seven UI surfaces (calendar cards, appointment detail, no-reply queue, reschedule queue, customer detail, customer messages, appointment form), disables outbound-SMS action buttons for opted-out recipients with an override confirm dialog for transactional messages, and adds a consent-history timeline panel on `CustomerDetail`.

## User Story

As an admin operating the Grins dispatch board
I want informal opt-out signals to be surfaced and actionable, and opt-out state to be visible everywhere I could accidentally send SMS
So that I never text a customer who has explicitly asked not to be contacted, and I can confirm/dismiss the ambiguous "please stop" signals our system currently silently logs.

## Problem Statement

Opt-out compliance leaks in two places:

1. **Informal opt-outs are functionally invisible.** The `_flag_informal_opt_out` handler only logs a warning — no `Alert` row is written, so even the existing `GET /api/v1/alerts?acknowledged=false` endpoint cannot surface them. Meanwhile, the system continues to send marketing and reminder SMS to customers who have written "stop texting me" (a CTIA grey-area violation).
2. **Opt-out status is invisible in operational UI.** Seven admin surfaces show actionable SMS buttons ("Send Confirmation", "Send Reminder", "Google Review") to customers whose `SmsConsentRecord` has `consent_given=False`. The backend consent check blocks the send and returns a generic error toast — the admin learns about the opt-out only *after* attempting to send, and may retry thinking the error is transient.

## Solution Statement

Two-layer fix with a shared middle:

- **Backend (6.A)**:
  - Extend `AlertType` enum with `INFORMAL_OPT_OUT` and add an `AlertSeverity` mapping.
  - Patch `SMSService._flag_informal_opt_out` to (a) create an `Alert(type=INFORMAL_OPT_OUT, severity=WARNING, entity_type='customer', entity_id=<resolved customer id>)`, (b) emit an `sms.informal_opt_out.flagged` audit event, and (c) attempt customer resolution from the phone number so the alert is actionable.
  - Extend `check_sms_consent` to accept a `respect_pending_opt_out` mode that treats an open `INFORMAL_OPT_OUT` alert as a hard block for `marketing` and widened block for `transactional-non-urgent` types (reminders, review requests), while leaving urgent transactional (confirmations within 48h, en-route / completion) sends through.
  - Add admin endpoints:
    - `POST /api/v1/alerts/{id}/confirm-opt-out` — writes `SmsConsentRecord(consent_given=False, opt_out_method='admin_confirmed_informal')`, acknowledges the alert, sends a one-time `OPT_OUT_CONFIRMATION_MSG`, emits `sms.informal_opt_out.confirmed` audit.
    - `POST /api/v1/alerts/{id}/dismiss` — acknowledges the alert without writing consent; emits `sms.informal_opt_out.dismissed` audit.
    - `GET /api/v1/alerts` — extend with `type` filter param for dashboard widget.
    - `GET /api/v1/customers/{id}/consent-history` — paginated timeline of `SmsConsentRecord` rows for the consent-history panel.
- **Frontend (6.A)**: Dashboard `AlertCard` variant with count of open `INFORMAL_OPT_OUT` alerts that navigates to `/alerts/informal-opt-out`; new `InformalOptOutQueue.tsx` page listing each alert with Confirm/Dismiss/Call actions.
- **Frontend (6.B)**: New shared `<OptOutBadge />` component driven by a `useCustomerConsentStatus(customerId)` hook that fetches from a new `GET /api/v1/customers/{id}/consent-status` endpoint (derived fields: `is_opted_out`, `opt_out_method`, `opt_out_timestamp`, `pending_informal_opt_out_alert_id`). Render the badge across seven surfaces. Disable all SMS-action buttons when `is_opted_out=true` with a tooltip; for transactional buttons, allow an override with an acknowledgment checkbox dialog. Add a `<ConsentHistoryPanel />` to `CustomerDetail` consuming the new consent-history endpoint.
- **Audit (Gap 05 prerequisite)**: Write `AuditLog` entries for every consent state change (flag, confirm, dismiss, admin-manual opt-out/in).

## Feature Metadata

**Feature Type**: Enhancement (compliance-adjacent hardening) + Bug Fix (missing Alert creation)
**Estimated Complexity**: High — spans backend service logic, new endpoints, seven frontend surfaces, a new shared component, and a new queue page.
**Primary Systems Affected**:
- Backend services: `SMSService` (`_flag_informal_opt_out`), `services/sms/consent.py`, `AuditService`
- Backend API: new endpoints on `alerts.py`, `customers.py`
- Backend schemas: new `consent_status`, `consent_history` response schemas; extended `AlertListResponse` filter
- Backend models / enums: `AlertType.INFORMAL_OPT_OUT` addition
- Frontend shared: new `OptOutBadge.tsx`, new `useCustomerConsentStatus` hook
- Frontend dashboard: new `InformalOptOutAlertCard`
- Frontend new page: `InformalOptOutQueue.tsx` at `/alerts/informal-opt-out`
- Frontend existing surfaces (badge + disabled action buttons): `CalendarView.tsx`, `AppointmentDetail.tsx`, `NoReplyReviewQueue.tsx`, `RescheduleRequestsQueue.tsx`, `CustomerDetail.tsx`, `CustomerMessages.tsx`, `AppointmentForm.tsx`
- Tests: unit + functional + integration + component + agent-browser

**Dependencies**: No new external libraries. Uses existing SQLAlchemy 2.x async, Alembic, pytest, pytest-asyncio, hypothesis, Vitest, React Testing Library, react-router-dom v7, TanStack Query v5.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

**Backend — opt-out pipeline:**
- `src/grins_platform/services/sms_service.py` (lines 1035–1070) — `_flag_informal_opt_out` — currently only logs a warning. Primary insertion point for Alert creation + customer resolution.
- `src/grins_platform/services/sms_service.py` (lines 930–1021) — `_process_exact_opt_out` — mirror this structure for the admin-confirmed informal path (writes `SmsConsentRecord`, sends confirmation SMS, calls `log_consent_hard_stop`). Reuse `OPT_OUT_CONFIRMATION_MSG` constant at line 62.
- `src/grins_platform/services/sms_service.py` (lines 621–696) — `handle_inbound` — shows the branch ordering; informal-opt-out edge case ("Customer sends informal, then STOP minutes later") must auto-acknowledge the alert; keep that logic inside `_process_exact_opt_out` or add a helper.
- `src/grins_platform/services/sms/consent.py` (lines 37–67) — `check_sms_consent` — extend with a `require_no_pending_informal=False` kwarg that additionally checks for an open `INFORMAL_OPT_OUT` alert for the customer_id tied to the phone.
- `src/grins_platform/services/sms/audit.py` (lines 126–138) — `log_consent_hard_stop` — pattern to mirror for new audit helpers `log_informal_opt_out_flagged`, `log_informal_opt_out_confirmed`, `log_informal_opt_out_dismissed`.

**Backend — Alert plumbing:**
- `src/grins_platform/models/alert.py` (lines 28–121) — `Alert` model. No model change required; uses existing `type` / `severity` string columns.
- `src/grins_platform/models/enums.py` (lines 590–600) — `AlertType` enum — add `INFORMAL_OPT_OUT = "informal_opt_out"`.
- `src/grins_platform/repositories/alert_repository.py` (lines 45–92) — `AlertRepository.create()` + `list_unacknowledged()`. Extend with `list_unacknowledged_by_type(alert_type, limit)`, `get(alert_id)`, and `acknowledge(alert_id, actor_id=None)` (new).
- `src/grins_platform/api/v1/alerts.py` (lines 38–89) — current list endpoint. Add `type` filter (`Query(None, description="...")`) and two new routes: `POST /{id}/confirm-opt-out` and `POST /{id}/dismiss`. Guard with `ManagerOrAdminUser` (line 19).
- `src/grins_platform/services/background_jobs.py` (lines 885–910) — existing pattern for writing an `Alert` via the repository. Copy this structure into the new informal-opt-out handler.

**Backend — SmsConsentRecord + history:**
- `src/grins_platform/models/sms_consent_record.py` (lines 31–132) — `SmsConsentRecord` fields. `opt_out_method` string supports `'text_stop'` today; add `'admin_confirmed_informal'` as a new value (no DB schema change — column already `String(50)`).
- `src/grins_platform/repositories/sms_consent_repository.py` — extend with `list_by_customer(customer_id, limit)` returning chronologically-ordered rows for the history timeline.
- `src/grins_platform/services/audit_service.py` (lines 30, 46–80) — `AuditService.log_action` — pattern for new audit events.

**Backend — phone → customer resolution:**
- `src/grins_platform/services/sms_service.py` (lines 577–619) — `_touch_lead_last_contacted` — demonstrates lead-lookup-by-phone. Mirror its normalization logic for customer resolution in the informal-opt-out path.
- `src/grins_platform/services/sms/phone_normalizer.py` — `normalize_to_e164()` for consistent phone storage.

**Backend — router registration:**
- `src/grins_platform/api/v1/router.py` (line 51–170) — shows `api_router.include_router(...)` pattern. No NEW router file is needed (existing `alerts.py` and `customers.py` are being extended).

**Frontend — existing badge / alert / queue patterns:**
- `frontend/src/features/dashboard/components/AlertCard.tsx` (lines 1–125) — `AlertCard` is the single source of truth for dashboard alert cards. Use variant `amber` (matches existing warning-level UX) for the informal-opt-out widget; the `targetPath='/alerts/informal-opt-out'` wires navigation.
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (lines 1–337) — closest pattern for the new queue page. Mirror: section header with icon + count badge, skeleton loading state, error state, per-row action buttons, confirm dialog (Send Reminder uses one), data-testid conventions.
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (lines 35–290) — second reference for queue layout + resolve mutation + row rendering.
- `frontend/src/features/schedule/hooks/useNoReplyReview.ts` (lines 1–70) — hook pattern (list + two mutations that invalidate on success). Mirror exactly for `useInformalOptOutQueue.ts`.

**Frontend — seven surfaces needing OptOutBadge + disabled action buttons (6.B):**
- `frontend/src/features/schedule/components/CalendarView.tsx` (lines 52–61 — `statusColors` map; add a second indicator slot that renders a small colored dot when opted out — mirror the existing status-border approach).
- `frontend/src/features/schedule/components/AppointmentDetail.tsx` (lines 213–219 — customer-info section; render badge inline with customer name; lines 151–167 — action handlers `handleConfirm` / `handleCancelConfirmed` — thread through the opt-out override dialog).
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (lines 281–322 — `NoReplyRow` action buttons; disable the Send Reminder button when `is_opted_out=true` with a tooltip).
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (lines 235–290 — `RescheduleRequestItem` — render badge next to customer name; no action button to disable here).
- `frontend/src/features/customers/components/CustomerDetail.tsx` (lines 107–114 — existing `sms_opt_in` form field — leave the form editable but add a read-only badge + consent-history panel above it; line 95 area — add `<ConsentHistoryPanel customerId={id} />` under the comm-prefs accordion).
- `frontend/src/features/customers/components/CustomerMessages.tsx` — render badge at page header; disable the composer "Send" button when opted out with override.
- `frontend/src/features/schedule/components/AppointmentForm.tsx` — show a banner at the top of the form when the selected customer is opted out.

**Frontend — shared UI primitives:**
- `frontend/src/shared/components/ui/` — Radix-based primitives live here. Put new `OptOutBadge.tsx` in `frontend/src/shared/components/` (one directory up from `ui/` because it's domain-aware, not a primitive).

**Tests — reference fixtures and patterns:**
- `src/grins_platform/tests/unit/test_sms_service_gaps.py` (lines 1–100) — unit test setup with `_make_service()` factory, `pytest.mark.asyncio`, parametrized cases. Mirror exactly for new `TestInformalOptOutCreatesAlert` suite.
- `src/grins_platform/tests/functional/test_no_reply_review_functional.py` — functional test example for a workflow that creates an `Alert` row and resolves it via the API. Mirror for informal-opt-out confirm/dismiss.
- `src/grins_platform/tests/unit/test_alert_repository.py` (line 53+) — repository unit test pattern.
- `src/grins_platform/tests/unit/test_pbt_sms_service_gaps.py` (lines 28, 91+) — property-based test for `INFORMAL_OPT_OUT_PHRASES`. Add a new PBT that asserts every phrase triggers Alert creation.
- `frontend/src/features/schedule/components/NoReplyReviewQueue.test.tsx` — component test for a queue page with a confirm dialog. Mirror for `InformalOptOutQueue.test.tsx`.

### New Files to Create

**Backend:**
- `src/grins_platform/migrations/versions/20260422_100000_add_admin_confirmed_informal_opt_out_method.py` — no-op migration reserving the new `opt_out_method` string; include a data-integrity check (ensure all existing rows still validate). Column is `String(50)` so no schema change; this migration is documentation-only but keeps the alembic chain honest.
- `src/grins_platform/schemas/consent.py` — new `ConsentStatusResponse`, `ConsentHistoryResponse`, `ConsentHistoryEntry`.

**Frontend:**
- `frontend/src/shared/components/OptOutBadge.tsx` — the shared badge component.
- `frontend/src/shared/components/OptOutBadge.test.tsx` — component tests (renders, tooltip content, correct color for `text_stop` vs `admin_confirmed_informal`).
- `frontend/src/features/customers/hooks/useConsentStatus.ts` — TanStack Query hook + key factory for `GET /api/v1/customers/{id}/consent-status`.
- `frontend/src/features/customers/hooks/useConsentHistory.ts` — hook for `GET /api/v1/customers/{id}/consent-history`.
- `frontend/src/features/customers/components/ConsentHistoryPanel.tsx` — chronological list of consent state changes for `CustomerDetail`.
- `frontend/src/features/customers/components/ConsentHistoryPanel.test.tsx` — component tests.
- `frontend/src/features/dashboard/hooks/useInformalOptOutCount.ts` — hook for dashboard widget count (derived via `GET /api/v1/alerts?type=informal_opt_out`).
- `frontend/src/features/dashboard/components/InformalOptOutAlertCard.tsx` — the AlertCard variant wired with the count + navigation to the queue page.
- `frontend/src/features/communications/components/InformalOptOutQueue.tsx` — the new review queue page at `/alerts/informal-opt-out`. Put it under `communications/` (confirmed: `frontend/src/features/communications/` already has `api/`, `components/`, `hooks/`, `index.ts`, `types/`, `utils/`) since it is cross-cutting messaging-compliance UI, not schedule-specific.
- `frontend/src/features/communications/hooks/useInformalOptOutQueue.ts` — list + confirm + dismiss mutations.
- `frontend/src/features/communications/api/alertsApi.ts` — new API client for `GET /api/v1/alerts?type=...`, `POST /api/v1/alerts/{id}/confirm-opt-out`, `POST /api/v1/alerts/{id}/dismiss`.
- `frontend/src/features/communications/components/InformalOptOutQueue.test.tsx` — component tests covering confirm + dismiss + empty state.
- Extend existing `frontend/src/features/communications/index.ts` (confirmed: already re-exports components, hooks, types, API) to add: `InformalOptOutQueue` component, `useInformalOptOutQueue` hook, `alertsApi`.
- `frontend/src/pages/InformalOptOutQueue.tsx` — thin page wrapper (pattern: every page in `frontend/src/pages/` is a feature re-export, e.g. `Dashboard.tsx`, `Communications.tsx`). Named export `InformalOptOutQueuePage`.

**Tests (backend):**
- `src/grins_platform/tests/unit/test_informal_opt_out_alert.py` — unit tests for `_flag_informal_opt_out` Alert creation + customer resolution.
- `src/grins_platform/tests/unit/test_check_sms_consent_pending_informal.py` — unit tests for the new `require_no_pending_informal` mode.
- `src/grins_platform/tests/functional/test_informal_opt_out_admin_flow.py` — functional test: inbound SMS → alert created → admin confirms via API → consent record written → future sends blocked.
- `src/grins_platform/tests/integration/test_alert_informal_opt_out_endpoints.py` — integration test hitting the FastAPI app with TestClient.

### Relevant Documentation — READ BEFORE IMPLEMENTING

- [CTIA Short Code Monitoring Handbook v1.7](https://api.ctia.org/wp-content/uploads/2019/07/190719-CTIA-Messaging-Principles-and-Best-Practices-FINAL.pdf)
  - Section 5.2 "Consumer Opt-Out" — requires honoring "reasonable variations" of STOP; defines what qualifies as an opt-out signal.
  - Why: Establishes that treating "stop texting me" identically to STOP is compliance-mandated, not optional.
- [10DLC Campaign Requirements (TCR)](https://www.campaignregistry.com/resources/)
  - Section on consent management — informal opt-out handling expectations for registered 10DLC campaigns.
  - Why: Our CallRail/10DLC registration is documented as complete in the CallRail-integration memory; losing compliance-adjacent handling risks deregistration.
- [TCPA Consent Best Practices — FCC](https://www.fcc.gov/consumers/guides/stop-unwanted-robocalls-and-texts)
  - Section: prior express written consent and revocation.
  - Why: Revocation can be made "in any reasonable manner" per FCC 2015 order — reinforces the legal floor for our informal-opt-out handling.
- [SQLAlchemy 2.x Async ORM — Session usage](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#asynchronous-orm-queries)
  - Why: patterns used throughout this repo for `select()`, `session.flush()`, etc.
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/)
  - Why: adding `type` filter to the alerts list endpoint needs correct optional-with-validation setup.
- [TanStack Query v5 mutations + invalidateQueries](https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations)
  - Why: Informal-opt-out confirm/dismiss mutations need to invalidate alert counts, consent status, and the list.
- **Native `title=` attribute for tooltips** — `frontend/src/components/ui/tooltip.tsx` does **NOT** exist in this repo. Existing pattern for hover-tooltips is the native HTML `title=` attribute (see `SendConfirmationButton.tsx` line 52). Use the same pattern for `OptOutBadge`. Do NOT introduce a Radix Tooltip dependency.

### Patterns to Follow

**Naming Conventions:**
- Backend: `snake_case.py`, services end with `_service.py`, repositories end with `_repository.py`, schemas end with plain domain name (`consent.py`).
- Frontend: Components `PascalCase.tsx`, hooks `use{PascalCase}.ts`, API clients `{feature}Api.ts`, tests co-located `{Component}.test.tsx`.
- Enum values: `lower_snake_case` strings; `AlertType.INFORMAL_OPT_OUT = "informal_opt_out"`.
- data-testid: `{feature}-page`, `{action}-{feature}-btn`, `opt-out-badge`, `informal-opt-out-queue`.

**Error Handling (backend services):**
```python
try:
    result = await self._do(param)
except ValidationError:
    self.log_rejected("op", reason=str(e))
    raise
except Exception as e:
    self.log_failed("op", error=e)
    raise
```
Follow `_flag_informal_opt_out`'s existing `self.log_started` / `self.log_completed` calls; add `self.log_failed` if the Alert insert raises.

**Logging pattern (mandatory per `.kiro/steering/code-standards.md`):**
```python
logger.info(
    "sms.informal_opt_out.flagged",
    phone=_mask_phone(phone),
    customer_id=str(customer_id) if customer_id else None,
    alert_id=str(alert.id),
)
```
- Never log raw phone — use `_mask_phone` from `sms_service.py`.
- Never log message body at WARN+ level.
- Use structured keys: `sms.{component}.{action}_{state}`.

**API endpoint template (per `.kiro/steering/api-patterns.md`):**
- `ManagerOrAdminUser` for admin actions
- `set_request_id()` at entry, `clear_request_id()` in `finally`
- `DomainLogger.api_event` for started/completed/failed
- 400 / 404 / 500 handled explicitly
- Pydantic request/response models

**Frontend hook pattern (per `.kiro/steering/frontend-patterns.md`):**
```ts
export const consentStatusKeys = {
  all: ['consent-status'] as const,
  byCustomer: (id: string) => [...consentStatusKeys.all, id] as const,
};
export function useCustomerConsentStatus(customerId: string) {
  return useQuery({
    queryKey: consentStatusKeys.byCustomer(customerId),
    queryFn: () => customerApi.getConsentStatus(customerId),
    enabled: !!customerId,
    staleTime: 30_000,  // 30s cache per gap's "cache 30s" requirement
  });
}
```

**OptOutBadge UX pattern:**
- Red fill when `opt_out_method === 'text_stop'` (hard STOP).
- Amber fill when `opt_out_method === 'admin_confirmed_informal'` (softer path).
- Amber outline (not filled) when `pending_informal_opt_out_alert_id` is set but no consent record yet.
- Tooltip text: `"Opted out via {method_label} on {date}. {raw_body_snippet?}"`.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (backend enums + schemas + repository surface)

Groundwork that later tasks depend on. No behavior change yet.

**Tasks:**
- Add `AlertType.INFORMAL_OPT_OUT` enum value.
- Create `schemas/consent.py` with `ConsentStatusResponse`, `ConsentHistoryResponse`, `ConsentHistoryEntry`, and an extended `AlertListResponse` (via `alert.py`) that optionally echoes the customer snapshot for queue rendering.
- Extend `AlertRepository` with `list_unacknowledged_by_type`, `get`, `acknowledge`.
- Extend `SmsConsentRepository` with `list_by_customer`.
- Add SMS audit helpers: `log_informal_opt_out_flagged`, `log_informal_opt_out_confirmed`, `log_informal_opt_out_dismissed`, `log_informal_opt_out_auto_acknowledged`.
- Alembic no-op migration for documentation (`20260422_100000_add_admin_confirmed_informal_opt_out_method.py`).

### Phase 2: Core Implementation — Backend (6.A flagging + consent gating + endpoints)

**Tasks:**
- Patch `SMSService._flag_informal_opt_out` to resolve the customer via phone, write the `Alert` row via `AlertRepository`, and call `log_informal_opt_out_flagged`. On customer-resolution failure, still create the Alert with `entity_type='phone'` and `entity_id=uuid4()` fallback — but prefer customer attachment.
- Auto-ack edge case: inside `_process_exact_opt_out`, after writing the `SmsConsentRecord`, look up any open `INFORMAL_OPT_OUT` alert for this customer_id / phone and `acknowledge()` it; emit `log_informal_opt_out_auto_acknowledged`.
- Extend `check_sms_consent()` with `require_no_pending_informal: bool = False` and a private `_has_open_informal_opt_out_alert(session, customer_id)` helper. When `True` and an open alert exists, return `False` regardless of `consent_type`.
- Update outbound-SMS call sites that should respect the pending window:
  - Marketing sends: always pass `require_no_pending_informal=True`.
  - Reminder sends (`MessageType.APPOINTMENT_REMINDER`, `REVIEW_REQUEST`, `CAMPAIGN`, `GOOGLE_REVIEW_REQUEST`): pass `require_no_pending_informal=True`.
  - Urgent transactional (`APPOINTMENT_CONFIRMATION`, `APPOINTMENT_CONFIRMATION_REPLY`, `ON_THE_WAY`, `ARRIVAL`, `COMPLETION`): pass `require_no_pending_informal=False` (allowed through).
- Add endpoints:
  - `GET /api/v1/alerts?type=informal_opt_out` — extend existing list.
  - `POST /api/v1/alerts/{id}/confirm-opt-out` — writes `SmsConsentRecord(consent_given=False, consent_method='admin_confirmed_informal', opt_out_method='admin_confirmed_informal', consent_language_shown=<alert.message>, created_by_staff_id=<actor>)`, acknowledges the Alert, sends `OPT_OUT_CONFIRMATION_MSG` via `provider.send_text`, emits `log_informal_opt_out_confirmed` + `log_consent_hard_stop`.
  - `POST /api/v1/alerts/{id}/dismiss` — acknowledges the Alert; emits `log_informal_opt_out_dismissed`. No consent change.
  - `GET /api/v1/customers/{id}/consent-status` — returns `ConsentStatusResponse` with `is_opted_out`, `opt_out_method`, `opt_out_timestamp`, `pending_informal_opt_out_alert_id`.
  - `GET /api/v1/customers/{id}/consent-history` — returns `ConsentHistoryResponse` (chronological `SmsConsentRecord` list).

### Phase 3: Core Implementation — Frontend (6.A dashboard widget + queue page)

**Tasks:**
- Create `alertsApi.ts` in `features/communications/api/` with `list({type})`, `confirmOptOut(alertId)`, `dismiss(alertId)`.
- Create `useInformalOptOutQueue.ts` hook (list + two mutations). On success, invalidate: the alert list, `consentStatusKeys.all`, and `informalOptOutCountKeys.all`.
- Create `useInformalOptOutCount.ts` (select `.length` from the list query so a single cached fetch serves both widget and queue).
- Create `InformalOptOutAlertCard.tsx` — wires `AlertCard` with `count={data?.length ?? 0}`, `variant='amber'`, `targetPath='/alerts/informal-opt-out'`. Render under the metrics grid in `DashboardPage.tsx` (between `JobStatusGrid` and `today-schedule-card`).
- Create `InformalOptOutQueue.tsx` page mirroring `NoReplyReviewQueue.tsx` layout:
  - Columns: customer name (clickable to `/customers/{id}`), phone, raw message body (truncated, expand-on-click), timestamp (`formatDistanceToNow`), alert age.
  - Row actions: **Confirm Opt-Out** (red), **Dismiss** (ghost), **Call Customer** (`tel:` link).
  - Confirm dialog for the Confirm Opt-Out action surfacing the recipient phone (dev safety pattern from `NoReplyReviewQueue.tsx` lines 170–238).
  - Loading / error / empty states (mirror NoReplyReviewQueue lines 84–119, 146–152).
- Register route `/alerts/informal-opt-out` in the app router (find the router file via `Grep pattern="createBrowserRouter|<Routes>"` in `frontend/src/core/router/`).

### Phase 4: Core Implementation — Frontend (6.B badge + disabled buttons + history panel)

**Tasks:**
- Create `OptOutBadge.tsx` in `frontend/src/shared/components/` with props `{ customerId: string, compact?: boolean }`. Internally calls `useCustomerConsentStatus(customerId)` and renders nothing when loading or when not opted out / no pending alert. Tooltip via existing Radix wrapper.
- Create `useCustomerConsentStatus.ts` + `useConsentHistory.ts` hooks with key factories.
- Create `ConsentHistoryPanel.tsx` in `features/customers/components/` — chronological list of consent events with method, timestamp, staff-id.
- **Render the badge** in each of the seven surfaces identified in CONTEXT REFERENCES. For each, use `compact` variant on tight layouts (calendar cards) and full variant elsewhere.
- **Disable action buttons** when `is_opted_out=true`:
  - `AppointmentDetail.tsx` → `SendConfirmationButton` (pass `disabled` prop if component supports it; otherwise wrap in a parent disabled pattern), cancel-with-notify checkbox (warn copy).
  - `NoReplyReviewQueue.tsx` → Send Reminder button.
  - `CustomerMessages.tsx` → composer Send button.
- **Override dialog** for urgent transactional: a shared `<ConfirmSendToOptedOutDialog />` (create in `frontend/src/features/communications/components/`) that requires ticking "I understand this customer has opted out. This is an urgent transactional notification only" before firing the mutation. Only wire into `AppointmentDetail.tsx`'s on-my-way / completion actions — NOT reminder / marketing.
- Integrate `ConsentHistoryPanel` into `CustomerDetail.tsx` under the comm-prefs accordion.
- Add calendar indicator: in `CalendarView.tsx`'s `statusColors` mapping + event content renderer, add a small red dot when the appointment's customer is opted out. Requires the weekly-schedule query to include opt-out status per appointment — if it doesn't, either (a) augment backend `GET /api/v1/schedule/weekly` response, or (b) use per-appointment `useCustomerConsentStatus` (acceptable because TanStack de-dupes in-flight queries; but add a batch `POST /api/v1/customers/consent-status/batch` if the schedule has more than 20 events on screen — measure first).

### Phase 5: Testing & Validation

**Backend tasks:**
- Unit tests for `_flag_informal_opt_out` Alert creation (mocked session): assert `Alert(type='informal_opt_out', severity='warning', entity_type='customer', ...)` added and audit emitted.
- Unit tests for `check_sms_consent(..., require_no_pending_informal=True)`.
- Unit tests for `AlertRepository.acknowledge`.
- Property-based test (hypothesis) — extend `test_pbt_sms_service_gaps.py`: every phrase in `INFORMAL_OPT_OUT_PHRASES` triggers Alert creation.
- Functional test covering full flow: seed customer → inbound SMS "stop texting me" → assert Alert row created + suppression active → admin POSTs confirm-opt-out → assert consent record written + alert acknowledged + suppression now hard-stop-based.
- Functional test: inbound "stop texting me" → admin POSTs dismiss → assert no consent record, alert acknowledged, marketing send still blocked until pending cleared? (Reread: dismiss clears the pending, so marketing should be allowed again. Verify this in the test.)
- Integration test hitting FastAPI with `TestClient` to confirm auth gate (non-admin → 403).

**Frontend tasks:**
- Component tests for `OptOutBadge` (three variants: hard stop, informal confirmed, pending).
- Component tests for `InformalOptOutQueue` (empty state, rows render, confirm dialog submits, dismiss works).
- Component tests for `ConsentHistoryPanel` (chronological order, empty state).
- Component tests for `InformalOptOutAlertCard` (renders count, navigates on click).
- Hook tests for `useCustomerConsentStatus` / `useInformalOptOutQueue` using `QueryProvider` wrapper.
- Update tests for `AppointmentDetail.test.tsx`, `NoReplyReviewQueue.test.tsx`, `CustomerDetail.test.tsx` to assert disabled-when-opted-out behavior.
- agent-browser end-to-end validation script.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines
Use information-dense keywords:
- **CREATE**: New files/components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **MIRROR**: Copy pattern from elsewhere in codebase

### 1. UPDATE `src/grins_platform/models/enums.py`

- **IMPLEMENT**: Add `INFORMAL_OPT_OUT = "informal_opt_out"` to `AlertType` (lines 590–600).
- **PATTERN**: Existing enum members, e.g. `CONFIRMATION_NO_REPLY = "confirmation_no_reply"`.
- **IMPORTS**: none.
- **GOTCHA**: Value must be lowercase snake_case; Alert.type is stored as the enum value string.
- **VALIDATE**: `uv run python -c "from grins_platform.models.enums import AlertType; print(AlertType.INFORMAL_OPT_OUT.value)"`

### 2. CREATE `src/grins_platform/schemas/consent.py`

- **IMPLEMENT**:
  - `ConsentStatusResponse` with fields: `customer_id: UUID`, `phone: str`, `is_opted_out: bool`, `opt_out_method: str | None`, `opt_out_timestamp: datetime | None`, `pending_informal_opt_out_alert_id: UUID | None`.
  - `ConsentHistoryEntry` with `id`, `consent_given`, `consent_method`, `consent_timestamp`, `opt_out_method`, `opt_out_timestamp`, `created_by_staff_id`, `consent_language_shown`.
  - `ConsentHistoryResponse` with `items: list[ConsentHistoryEntry]`, `total: int`.
- **PATTERN**: `src/grins_platform/schemas/alert.py` lines 14–60.
- **IMPORTS**: `from pydantic import BaseModel, ConfigDict, Field`, `from datetime import datetime`, `from uuid import UUID`.
- **GOTCHA**: Use `model_config = ConfigDict(from_attributes=True)` so `SmsConsentRecord` rows validate directly.
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.consent import ConsentStatusResponse"`

### 3. UPDATE `src/grins_platform/repositories/alert_repository.py`

- **ADD**:
  - `async def get(self, alert_id: UUID) -> Alert | None` — single-row fetch by id.
  - `async def list_unacknowledged_by_type(self, alert_type: str, limit: int = 100) -> list[Alert]` — filter on `Alert.type == alert_type AND acknowledged_at IS NULL`.
  - `async def acknowledge(self, alert_id: UUID) -> Alert | None` — set `acknowledged_at = datetime.now(tz=timezone.utc)`, flush, return refreshed row.
- **PATTERN**: existing `create()` (lines 45–67) + `list_unacknowledged()` (lines 69–91).
- **IMPORTS**: `from datetime import datetime, timezone`.
- **GOTCHA**: `acknowledge` must be idempotent — if already acknowledged, do not overwrite `acknowledged_at`; return existing row.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_alert_repository.py -v`

### 4. UPDATE `src/grins_platform/repositories/sms_consent_repository.py`

- **ADD**: `async def list_by_customer(self, customer_id: UUID, limit: int = 50) -> list[SmsConsentRecord]` ordered by `consent_timestamp DESC`.
- **PATTERN**: existing `get_opted_out_customer_ids` at line 39.
- **GOTCHA**: INSERT-ONLY table — newest rows first so the UI can show the "current state" banner at top.
- **VALIDATE**: `uv run mypy src/grins_platform/repositories/sms_consent_repository.py`

### 5. UPDATE `src/grins_platform/services/sms/audit.py`

- **ADD** helpers mirroring `log_consent_hard_stop` (lines 126–138):
  - `log_informal_opt_out_flagged(db, *, phone_masked, customer_id=None, alert_id)`
  - `log_informal_opt_out_confirmed(db, *, alert_id, customer_id, actor_id)`
  - `log_informal_opt_out_dismissed(db, *, alert_id, actor_id)`
  - `log_informal_opt_out_auto_acknowledged(db, *, alert_id, customer_id)`
- **IMPORTS**: inherit from file.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/sms/audit.py`

### 6. UPDATE `src/grins_platform/services/sms/consent.py`

- **ADD** `require_no_pending_informal: bool = False` kwarg to `check_sms_consent` at line 37.
- **ADD** private `_has_open_informal_opt_out_alert(session, customer_id)` helper that queries `alerts` where `type='informal_opt_out'`, `entity_type='customer'`, `entity_id=customer_id`, `acknowledged_at IS NULL`. Mirror the SQLAlchemy pattern from `_has_hard_stop` (lines 112–126).
- **ADD** lookup helper `_resolve_customer_id_by_phone(session, e164_phone) -> UUID | None` using the existing `_phone_variants(e164)` helper (already in this file at line 70) and `select(Customer.id).where(Customer.phone.in_(variants)).limit(1)`. The project already uses this exact query shape — see `_has_marketing_opt_in` at line 155. Do NOT add a new phone-normalization path.
- **UPDATE** logic: after the `hard_stop` check at line 58 but before the `consent_type == "transactional"` branch at line 62, insert:
  ```python
  if require_no_pending_informal:
      customer_id = await _resolve_customer_id_by_phone(session, e164)
      if customer_id is not None and await _has_open_informal_opt_out_alert(session, customer_id):
          return False
  ```
- **PATTERN**: existing `_has_hard_stop` at lines 112–126 + `_has_marketing_opt_in` at lines 129–173.
- **GOTCHA**: `customer_id` resolution may return None (lead-only phone); treat None as "no alert exists" — informal-opt-out alerts are scoped to customer entities only in this plan (lead-only flagging falls back to `entity_type='phone'` which cannot be auto-blocked).
- **GOTCHA**: `Alert.entity_id` is typed as `PGUUID`; comparison `entity_id == customer_id` is safe when customer_id is a UUID.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_check_sms_consent_pending_informal.py -v` (after creating test file in step 15).

### 7. UPDATE `src/grins_platform/services/sms_service.py` — patch `_flag_informal_opt_out`

- **IMPLEMENT**:
  1. Resolve customer_id from `phone` (mirror `_touch_lead_last_contacted` but looking up `Customer.phone`).
  2. Normalize phone to E.164 via `normalize_to_e164`.
  3. Build `Alert(type=AlertType.INFORMAL_OPT_OUT.value, severity=AlertSeverity.WARNING.value, entity_type='customer' if customer_id else 'phone', entity_id=customer_id or uuid4(), message=f"Possible opt-out from {phone_masked}: '{body[:200]}'")`.
  4. Persist via `AlertRepository(self.session).create(alert)`.
  5. Call `log_informal_opt_out_flagged(self.session, phone_masked=_mask_phone(phone), customer_id=customer_id, alert_id=alert.id)`.
  6. Keep the existing `logger.warning` / `log_completed` calls.
- **PATTERN**: `background_jobs.py` lines 890–910 for Alert creation with fallback-safe error handling.
- **IMPORTS**: add `from grins_platform.models.alert import Alert`, `from grins_platform.models.enums import AlertSeverity, AlertType`, `from grins_platform.repositories.alert_repository import AlertRepository`, `from grins_platform.services.sms.audit import log_informal_opt_out_flagged`, `from uuid import uuid4`.
- **GOTCHA**: The gap spec says `entity_type='customer', entity_id=customer_id`. If the phone does not resolve to a customer, fall back to `entity_type='phone'` with a generated id — but prefer customer attachment. Frontend must handle both.
- **GOTCHA**: Alert creation failure must NOT swallow the inbound — wrap in try/except and let the inbound still return the flag response.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_informal_opt_out_alert.py -v` (created in step 14).

### 8. UPDATE `src/grins_platform/services/sms_service.py` — auto-ack on subsequent exact STOP

- **ADD** inside `_process_exact_opt_out` after the `self.session.add(record)` block: look up open `INFORMAL_OPT_OUT` alerts for the resolved customer_id (if any); acknowledge each via `AlertRepository.acknowledge`; emit `log_informal_opt_out_auto_acknowledged` per alert.
- **PATTERN**: see `_flag_informal_opt_out` for customer resolution; `AlertRepository.acknowledge` from step 3.
- **GOTCHA**: do not fail the opt-out if the acknowledge raises — log and continue.
- **VALIDATE**: functional test in step 17 covers this sequence.

### 9. UPDATE `send_message` to pass `require_no_pending_informal` derived from `message_type`

- **IMPLEMENT**: At `src/grins_platform/services/sms_service.py` line 169 (`send_message` signature), do NOT add a new kwarg — instead derive the flag internally from `message_type`. At module scope near line 75 (`_SUPERSEDABLE_MESSAGE_TYPES`), add:
  ```python
  # Message types that should be suppressed while an INFORMAL_OPT_OUT alert is
  # unacknowledged. Urgent transactional (CONFIRMATION, ON_THE_WAY, ARRIVAL,
  # COMPLETION) are excluded — they are allowed through until the admin decides.
  _RESPECTS_PENDING_INFORMAL_OPT_OUT: frozenset[MessageType] = frozenset({
      MessageType.APPOINTMENT_REMINDER,
      MessageType.REVIEW_REQUEST,
      MessageType.GOOGLE_REVIEW_REQUEST,
      MessageType.CAMPAIGN,
      MessageType.PAYMENT_REMINDER,
  })
  ```
  At line 221, where `check_sms_consent` is called, change to:
  ```python
  respects_pending = message_type in _RESPECTS_PENDING_INFORMAL_OPT_OUT
  has_consent = await check_sms_consent(
      self.session,
      recipient.phone,
      consent_type,
      require_no_pending_informal=respects_pending,
  )
  ```
- **PATTERN**: existing `_SUPERSEDABLE_MESSAGE_TYPES` frozenset at line 75.
- **GOTCHA**: Do NOT extend this to `APPOINTMENT_CONFIRMATION` / `APPOINTMENT_CONFIRMATION_REPLY` / `RESCHEDULE_FOLLOWUP` / `ON_THE_WAY` / `ARRIVAL` / `COMPLETION` — all urgent transactional and customer-initiated.
- **GOTCHA**: `send_message` raises `SMSConsentDeniedError` when the check fails (line 234); the exception message is consumed by upstream toasts. The "pending informal opt-out" case may need a distinct error or message prefix so the frontend can show a targeted toast ("Send blocked — customer has a pending opt-out alert. Resolve it first in /alerts/informal-opt-out."). Extend `SMSConsentDeniedError` or pass a `reason_code` if helpful.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_sms_service_gaps.py -v`

### 10. UPDATE `src/grins_platform/api/v1/alerts.py`

- **ADD** `type: str | None = Query(None, description="Optional alert type filter")` to `list_alerts`. When provided, route to `AlertRepository.list_unacknowledged_by_type`.
- **CREATE** new route `POST /{id}/confirm-opt-out`:
  - Guard: `ManagerOrAdminUser`.
  - Look up alert, reject 404 if not found, 400 if already acknowledged, 422 if `type != 'informal_opt_out'`.
  - Look up customer via `entity_id`; if `entity_type == 'phone'` reject with 422 ("cannot confirm opt-out for un-resolved phone; admin must attach customer manually").
  - Instantiate `SMSService(session)` and call a new helper `await sms_service.confirm_informal_opt_out(alert_id, actor_id=current_user.id)` that: writes `SmsConsentRecord`, acknowledges alert, sends `OPT_OUT_CONFIRMATION_MSG`, emits audit events.
  - Return 200 with the updated `AlertResponse`.
- **CREATE** new route `POST /{id}/dismiss`:
  - Guard: `ManagerOrAdminUser`.
  - `AlertRepository.acknowledge(alert_id)` + emit `log_informal_opt_out_dismissed`.
  - Return 200 with the acknowledged `AlertResponse`.
- **PATTERN**: `src/grins_platform/api/v1/reschedule_requests.py` for endpoint structure with `LoggerMixin`.
- **IMPORTS**: add `from grins_platform.services.sms_service import SMSService`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_alert_informal_opt_out_endpoints.py -v`.

### 11. UPDATE `src/grins_platform/services/sms_service.py` — add `confirm_informal_opt_out` helper

- **IMPLEMENT**: mirror `_process_exact_opt_out` but:
  - `consent_method='admin_confirmed_informal'`, `opt_out_method='admin_confirmed_informal'`.
  - `consent_language_shown=alert.message` (the raw flagged body).
  - `created_by_staff_id=actor_id`.
  - Acknowledge the alert via `AlertRepository.acknowledge`.
  - Send `OPT_OUT_CONFIRMATION_MSG` via `self.provider.send_text` to the resolved E.164 phone.
  - Emit `log_informal_opt_out_confirmed` + `log_consent_hard_stop`.
- **GOTCHA**: If SMS send fails, still commit consent + acknowledge — write failure is worse than missed confirmation SMS.

### 12. UPDATE `src/grins_platform/api/v1/customers.py`

- **ADD** `GET /{customer_id}/consent-status` returning `ConsentStatusResponse`.
  - Resolve customer; look up most recent `SmsConsentRecord` for customer_id OR phone; check for open `INFORMAL_OPT_OUT` alert.
- **ADD** `GET /{customer_id}/consent-history` returning paginated `ConsentHistoryResponse`.
- **PATTERN**: existing customer endpoints at the top of this file.
- **GUARD**: `CurrentActiveUser` (all roles need read access for the badge).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/ -k consent_status -v`.

### 13. CREATE `src/grins_platform/migrations/versions/20260422_100000_add_admin_confirmed_informal_opt_out_method.py`

- **IMPLEMENT**: No-op migration (the `opt_out_method` column is already `String(50)`). Set:
  ```python
  revision: str = "20260422_100000"
  down_revision: str | None = "20260421_100100"  # confirmed: currently HEAD
  branch_labels: str | Sequence[str] | None = None
  depends_on: str | Sequence[str] | None = None
  ```
  Keep `upgrade()` and `downgrade()` as `pass` with a module docstring explaining this reserves the new `opt_out_method='admin_confirmed_informal'` value.
- **PATTERN**: `20260416_100100_create_alerts_table.py` (revision ID format + branch_labels pattern).
- **GOTCHA**: The current HEAD is confirmed as `20260421_100100_add_sent_messages_superseded_at.py` — use it as `down_revision`.
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`.

### 14. CREATE `src/grins_platform/tests/unit/test_informal_opt_out_alert.py`

- **IMPLEMENT**: Test cases:
  - `test_informal_phrase_creates_alert_for_resolved_customer`
  - `test_informal_phrase_creates_alert_with_phone_entity_when_unresolved`
  - `test_alert_creation_failure_does_not_break_inbound`
  - `test_subsequent_exact_stop_auto_acknowledges_pending_alert`
- **PATTERN**: `test_sms_service_gaps.py::TestInformalOptOut` for `_make_service` factory.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_informal_opt_out_alert.py -v`

### 15. CREATE `src/grins_platform/tests/unit/test_check_sms_consent_pending_informal.py`

- **IMPLEMENT**:
  - `test_pending_alert_blocks_marketing`
  - `test_pending_alert_blocks_reminder`
  - `test_pending_alert_does_not_block_urgent_transactional`
  - `test_no_pending_alert_returns_base_consent`
- **PATTERN**: existing `check_sms_consent` unit tests (grep for `test_check_sms_consent`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_check_sms_consent_pending_informal.py -v`

### 16. UPDATE `src/grins_platform/tests/unit/test_pbt_sms_service_gaps.py`

- **ADD** hypothesis test asserting every phrase in `INFORMAL_OPT_OUT_PHRASES` triggers Alert creation — extend the existing `@given(phrase=st.sampled_from(list(INFORMAL_OPT_OUT_PHRASES)))` case.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_pbt_sms_service_gaps.py -v`

### 17. CREATE `src/grins_platform/tests/functional/test_informal_opt_out_admin_flow.py`

- **IMPLEMENT**: full workflow using real DB fixtures. Steps:
  1. Seed a customer with opted-in SMS.
  2. Drive `SMSService.handle_inbound` with `"stop texting me"`.
  3. Assert an `Alert(type='informal_opt_out')` row exists unacknowledged.
  4. Assert `check_sms_consent(..., require_no_pending_informal=True)` returns False for marketing.
  5. Assert urgent transactional still returns True.
  6. POST `/api/v1/alerts/{id}/confirm-opt-out` (with admin auth fixture).
  7. Assert `SmsConsentRecord` row written with `consent_given=False, opt_out_method='admin_confirmed_informal'`.
  8. Assert `check_sms_consent(..., consent_type='transactional')` now returns False (hard-stop precedence).
  9. Assert alert acknowledged.
  10. Parallel test: dismiss path — POST dismiss, assert no consent record, assert marketing now allowed again (pending cleared).
- **PATTERN**: `test_no_reply_review_functional.py`.
- **VALIDATE**: `uv run pytest -m functional src/grins_platform/tests/functional/test_informal_opt_out_admin_flow.py -v`

### 18. CREATE `src/grins_platform/tests/integration/test_alert_informal_opt_out_endpoints.py`

- **IMPLEMENT**: TestClient-driven tests for 401/403 auth gates, 404 missing alert, 422 wrong-type alert, 400 already-acknowledged.
- **PATTERN**: other integration tests under `tests/integration/`.
- **VALIDATE**: `uv run pytest -m integration src/grins_platform/tests/integration/test_alert_informal_opt_out_endpoints.py -v`

### 19. CREATE `frontend/src/shared/components/OptOutBadge.tsx`

- **IMPLEMENT**:
  ```tsx
  interface OptOutBadgeProps { customerId: string; compact?: boolean }
  ```
  Hook: `useCustomerConsentStatus(customerId)`. Render nothing if loading, no customer, or neither `is_opted_out` nor `pending_informal_opt_out_alert_id`.
  Color: red for `text_stop`, amber for `admin_confirmed_informal`, amber-outline for pending.
  Hover-tooltip: use native `title=` attribute (example: `title={`Opted out via ${methodLabel} on ${format(date, 'MMM d, yyyy')}. ${rawBodySnippet ?? ''}`}`). NO Radix Tooltip — it is not installed in this repo.
- **PATTERN**: existing `Badge` wrapper at `frontend/src/components/ui/badge.tsx` (used by `NoReplyReviewQueue.tsx` line 25); native `title=` pattern at `SendConfirmationButton.tsx` line 52.
- **EXPORT**: add to `frontend/src/shared/components/index.ts` alongside other shared components (e.g. `StatusBadge`).
- **VALIDATE**: `npm run typecheck && npm test OptOutBadge`.

### 20. CREATE `frontend/src/features/customers/hooks/useConsentStatus.ts` and `useConsentHistory.ts`

- **IMPLEMENT**: TanStack Query hooks with 30s staleTime for consent-status (per gap spec "cache 30s"), 60s for history.
- **PATTERN**: `useNoReplyReview.ts` for hook + key factory structure.
- **VALIDATE**: `npm run typecheck`.

### 21. CREATE `frontend/src/features/customers/components/ConsentHistoryPanel.tsx`

- **IMPLEMENT**: chronological list (newest first) of consent events; each row shows method badge, timestamp, staff attribution, language snippet.
- **PATTERN**: mirror the existing activity-timeline layout in `RecentActivity.tsx`.
- **VALIDATE**: `npm test ConsentHistoryPanel`.

### 22. UPDATE `frontend/src/features/customers/components/CustomerDetail.tsx`

- **ADD** `<OptOutBadge customerId={customer.id} />` inline with the customer name at the page header.
- **ADD** `<ConsentHistoryPanel customerId={customer.id} />` under the comm-prefs accordion (near lines 107–114 region).
- **UPDATE** the `sms_opt_in` form field to show a disabled banner when `is_opted_out=true` explaining the customer must first confirm re-opt-in via START keyword.
- **VALIDATE**: `npm test CustomerDetail`.

### 23. UPDATE `frontend/src/features/schedule/components/AppointmentDetail.tsx` + `SendConfirmationButton.tsx`

- **UPDATE** `SendConfirmationButton.tsx` — add an optional `customerId?: string` prop. When provided, call `useCustomerConsentStatus(customerId)` inside and extend the internal `disabled` computation to include `consentStatus?.is_opted_out === true`. Update the `tooltip` string to reflect the opt-out reason when applicable ("Customer has opted out of SMS").
- **PATTERN**: the existing internal `disabled = sendMutation.isPending || !isDraft` at `SendConfirmationButton.tsx` line 34.
- **UPDATE** `AppointmentDetail.tsx` — pass `customerId={customer.id}` to every `<SendConfirmationButton />` rendering site. Add `<OptOutBadge customerId={customer.id} compact />` inline with the customer name at the customer-info section (near line 218).
- **GOTCHA**: `SendConfirmationButton` is also rendered from `CalendarView.tsx` — update that call site too to thread `customerId`.
- **VALIDATE**: `npm test AppointmentDetail && npm test SendConfirmationButton && npm test CalendarView`.

### 24. UPDATE `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx`

- **ADD** `<OptOutBadge customerId={row.customer_id} compact />` beside customer name in `NoReplyRow`.
- **UPDATE** Send Reminder button: disable + tooltip when opted out. Show an amber warning in the confirm dialog if the customer has an open informal-opt-out alert.
- **VALIDATE**: `npm test NoReplyReviewQueue`.

### 25. UPDATE `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx`

- **ADD** `<OptOutBadge customerId={request.customer_id} compact />` beside customer name.
- **VALIDATE**: `npm test RescheduleRequestsQueue`.

### 26. UPDATE `frontend/src/features/schedule/components/CalendarView.tsx`

- **ADD** a small red/amber dot on the event card when the customer is opted out. Either (a) enrich the weekly-schedule response to include an `opted_out: bool` flag per appointment, or (b) use per-event `useCustomerConsentStatus` (TanStack de-dupes by key).
- **GOTCHA**: prefer option (a) for calendars with >20 events; add a batch endpoint if needed. Measure first.
- **VALIDATE**: `npm test CalendarView && agent-browser open http://localhost:5173/schedule`.

### 27. UPDATE `frontend/src/features/customers/components/CustomerMessages.tsx`

- **ADD** `<OptOutBadge customerId={customerId} />` at the top of the component's render (before the loading skeleton check at line 29).
- **DO NOT** add a composer/Send button. `CustomerMessages` is read-only — it displays message history (`useCustomerSentMessages`) and has no Send affordance. The original plan's "disable composer Send" task was based on an incorrect assumption; there is no ad-hoc per-customer SMS composer in the app today.
- **VALIDATE**: `npm test CustomerMessages`.

### 28. UPDATE `frontend/src/features/schedule/components/AppointmentForm.tsx`

- **ADD** an amber banner at the top of the form when the selected customer is opted out: "This customer has opted out of SMS. SMS confirmations will not be sent."
- **VALIDATE**: `npm test AppointmentForm`.

### 29. CREATE `frontend/src/features/communications/api/alertsApi.ts`

- **IMPLEMENT**: API client with `list({type?})`, `confirmOptOut(alertId)`, `dismiss(alertId)`.
- **PATTERN**: existing feature API files (`appointmentApi.ts`).
- **VALIDATE**: `npm run typecheck`.

### 30. CREATE `frontend/src/features/communications/hooks/useInformalOptOutQueue.ts`

- **IMPLEMENT**: list query + confirmOptOut mutation + dismiss mutation. On success, invalidate the queue query, `consentStatusKeys.all`, and any alert-count queries.
- **PATTERN**: `useNoReplyReview.ts`.
- **VALIDATE**: `npm run typecheck`.

### 31. CREATE `frontend/src/features/dashboard/hooks/useInformalOptOutCount.ts`

- **IMPLEMENT**: Wraps the list query with a `select: (data) => data.length` transform so the dashboard widget only rerenders when the count changes.
- **VALIDATE**: `npm run typecheck`.

### 32. CREATE `frontend/src/features/dashboard/components/InformalOptOutAlertCard.tsx`

- **IMPLEMENT**: Wrap `AlertCard` from step 32's parent; `count={useInformalOptOutCount()}`, `targetPath='/alerts/informal-opt-out'`, `variant='amber'`, `icon={AlertOctagon}` (lucide-react).
- **VALIDATE**: `npm test InformalOptOutAlertCard`.

### 33. UPDATE `frontend/src/features/dashboard/components/DashboardPage.tsx`

- **ADD** `<InformalOptOutAlertCard />` between `<JobStatusGrid />` (line 101) and `{/* Today's Schedule Summary */}` (line 104). Wrap in a `<div className="grid grid-cols-1 md:grid-cols-2 gap-4">` if there will be other AlertCards; else render standalone.
- **VALIDATE**: `npm test DashboardPage`.

### 34. CREATE `frontend/src/features/communications/components/InformalOptOutQueue.tsx`

- **IMPLEMENT**: Mirror `NoReplyReviewQueue.tsx` layout. Columns: customer name, phone, raw body, alert age. Row actions: Confirm Opt-Out (red, opens confirm dialog surfacing phone), Dismiss (ghost), Call (`tel:`).
- **PATTERN**: `NoReplyReviewQueue.tsx` lines 123–241 for section + confirm dialog.
- **VALIDATE**: `npm test InformalOptOutQueue`.

### 35. UPDATE router + create page wrapper

- **CREATE** `frontend/src/pages/InformalOptOutQueue.tsx` — thin page wrapper that imports and renders `InformalOptOutQueue` from `@/features/communications`. Also add a named export `InformalOptOutQueuePage` that the router can lazy-load.
- **PATTERN**: every page in `frontend/src/pages/` is a thin wrapper that imports its feature component (see `Dashboard.tsx`, `Communications.tsx`).
- **UPDATE** `frontend/src/pages/index.ts` — re-export `InformalOptOutQueuePage` if that's the pattern (grep to verify).
- **UPDATE** `frontend/src/core/router/index.tsx` — add a new lazy import beside the others (around line 70):
  ```tsx
  const InformalOptOutQueuePage = lazy(() =>
    import('@/pages/InformalOptOutQueue').then((m) => ({
      default: m.InformalOptOutQueuePage,
    }))
  );
  ```
  Then add a new route inside the `/` protected children (after `path: 'communications'` around line 248):
  ```tsx
  {
    path: 'alerts/informal-opt-out',
    element: <InformalOptOutQueuePage />,
  },
  ```
- **GOTCHA**: All protected routes automatically go through `<ProtectedLayoutWrapper />` (line 153–155) → `<ProtectedRoute>` (line 107) → `<LayoutWrapper />`. No extra admin-only wrapper exists in router — the backend `ManagerOrAdminUser` gate is the security boundary. If you want a UI-level gate, add a `useAuth()` role check inside the `InformalOptOutQueue` component itself; otherwise non-admins just see an empty list (backend 403s on the list endpoint).
- **VALIDATE**: `npm run build && npm run dev` then navigate to `http://localhost:5173/alerts/informal-opt-out`.

### 36. Run full quality gate

- **VALIDATE** (in order):
  ```bash
  uv run ruff check --fix src/
  uv run ruff format src/
  uv run mypy src/
  uv run pyright src/
  uv run pytest -v
  cd frontend && npm run lint && npm run typecheck && npm test && npm run build
  ```

---

## TESTING STRATEGY

### Unit Tests

Backend (`@pytest.mark.unit`, mocked `AsyncSession`):
- `_flag_informal_opt_out` Alert creation paths (customer resolved / phone-only).
- `confirm_informal_opt_out` writes correct consent row, acknowledges alert, sends confirmation SMS, emits audit events.
- `check_sms_consent(..., require_no_pending_informal=True)` with open / acknowledged / no alert.
- `AlertRepository.acknowledge` idempotency.
- `SmsConsentRepository.list_by_customer` ordering.
- Property-based: every `INFORMAL_OPT_OUT_PHRASES` entry creates an alert.

Frontend (Vitest + RTL):
- `OptOutBadge` — three variants (hard stop, informal confirmed, pending).
- `ConsentHistoryPanel` — empty, populated, newest-first.
- `InformalOptOutQueue` — empty, rows render, confirm dialog, dismiss.
- `InformalOptOutAlertCard` — count shown, navigates on click.
- Hook tests for `useCustomerConsentStatus`, `useInformalOptOutQueue`.

### Functional Tests (real DB)

- Full informal-opt-out flow: inbound SMS → alert → admin confirm → consent row → suppression.
- Dismiss path: alert → admin dismiss → suppression cleared.
- Exact STOP after informal flag auto-acknowledges pending alert.
- Disabled action button on opted-out customer in `AppointmentDetail` (component functional).

### Integration Tests

- `POST /api/v1/alerts/{id}/confirm-opt-out` auth gates (401/403/404/400/422).
- `GET /api/v1/customers/{id}/consent-status` returns correct fields.
- `GET /api/v1/alerts?type=informal_opt_out` filters correctly.

### Edge Cases (per gap spec)

- Customer sends informal, then Y to appt confirmation — Y still processes; alert stays open.
- Customer sends informal, then STOP — alert auto-acknowledges, hard-stop takes over.
- Customer has previous opt-out then texts START — history shows both; current state derived from most recent.
- Lead (not yet customer) sends informal — `entity_type='phone'` fallback; admin cannot confirm until the phone is linked to a customer.
- Customer with two phones, one opted out — consent check per phone; UI shows which phone is blocked.
- Alert creation failure does not swallow inbound response.
- TanStack cache: badge updates within 30s of the consent mutation via `invalidateQueries({ queryKey: consentStatusKeys.all })`.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style
```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint && npm run format:check
```

### Level 2: Unit Tests
```bash
uv run pytest -m unit -v
cd frontend && npm test
```

### Level 3: Functional + Integration
```bash
uv run pytest -m functional -v
uv run pytest -m integration -v
```

### Level 4: Type Safety
```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck
```

### Level 5: Manual / agent-browser Validation
```bash
# Backend dev server
./scripts/dev.sh

# Drive an inbound informal opt-out via SMS webhook.
# Confirmed endpoint: POST /api/v1/sms/webhook (Twilio-signed, form-encoded).
# For local dev without Twilio signing, call SMSService.handle_inbound directly in a
# REPL, or use the CallRail test endpoint if available.
curl -X POST http://localhost:8000/api/v1/sms/webhook \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'From=%2B19527373312&Body=stop+texting+me&MessageSid=SM_TEST_001'

# Verify Alert was created
curl -s "http://localhost:8000/api/v1/alerts?type=informal_opt_out" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Frontend
cd frontend && npm run dev
agent-browser open http://localhost:5173/alerts/informal-opt-out
agent-browser is visible "[data-testid='informal-opt-out-queue']"
agent-browser click "[data-testid='confirm-opt-out-btn']"
agent-browser wait --text "Customer opted out"

# Verify badge on appointment detail
agent-browser open http://localhost:5173/schedule
agent-browser click "[data-testid*='calendar-event']"
agent-browser is visible "[data-testid='opt-out-badge']"
agent-browser is disabled "[data-testid='send-confirmation-btn']"
```

### Level 6: End-to-End Compliance Sanity Check

Confirm no regressions to existing opt-out pipeline:
```bash
uv run pytest -m unit src/grins_platform/tests/unit/test_sms_service_gaps.py::TestExactOptOutKeywords -v
uv run pytest -m unit src/grins_platform/tests/unit/test_sms_service_gaps.py::TestInformalOptOut -v
```

---

## ACCEPTANCE CRITERIA

- [ ] Inbound "stop texting me" creates an `Alert(type='informal_opt_out', severity='warning', entity_type='customer')` row (or `entity_type='phone'` fallback) and emits `sms.informal_opt_out.flagged` audit event.
- [ ] Open `INFORMAL_OPT_OUT` alerts suppress marketing + reminder + review-request SMS to the same customer; urgent transactional (confirmation, en-route, completion) still go through.
- [ ] Dashboard shows an amber `AlertCard` with count of open informal opt-outs.
- [ ] `/alerts/informal-opt-out` route renders a queue with Confirm / Dismiss / Call actions.
- [ ] Confirm Opt-Out writes `SmsConsentRecord(consent_given=False, opt_out_method='admin_confirmed_informal')`, acknowledges the alert, sends `OPT_OUT_CONFIRMATION_MSG`, and emits both `sms.informal_opt_out.confirmed` and `sms.consent.hard_stop_received` audit events.
- [ ] Dismiss acknowledges the alert without writing consent and emits `sms.informal_opt_out.dismissed`.
- [ ] Subsequent exact STOP from the same customer auto-acknowledges the pending informal-opt-out alert.
- [ ] `<OptOutBadge />` renders on all seven identified surfaces when the customer is opted out or has a pending informal alert.
- [ ] Send Confirmation / Send Reminder / composer Send / Google Review buttons are disabled with tooltip when customer is opted out; transactional buttons allow override via acknowledgment dialog.
- [ ] `CustomerDetail` shows a `ConsentHistoryPanel` with chronological consent events.
- [ ] `GET /api/v1/customers/{id}/consent-status` returns correct `is_opted_out`, `opt_out_method`, `opt_out_timestamp`, `pending_informal_opt_out_alert_id`.
- [ ] All validation commands pass with zero errors.
- [ ] Unit test coverage ≥ 90% for new services/repositories; component coverage ≥ 80%; hook coverage ≥ 85%.
- [ ] No regressions in exact-STOP opt-out pipeline tests.
- [ ] No real customer SMS is sent during testing (only `+19527373312` may receive real SMS per dev rule — use mock provider or the null provider in tests).

---

## COMPLETION CHECKLIST

- [ ] All 36 tasks executed in order
- [ ] Per-task `VALIDATE` commands passed immediately
- [ ] `uv run ruff check src/` — zero violations
- [ ] `uv run mypy src/` — zero errors
- [ ] `uv run pyright src/` — zero errors
- [ ] `uv run pytest -v` — all unit + functional + integration pass
- [ ] `cd frontend && npm run typecheck && npm run lint && npm test && npm run build` — all pass
- [ ] Agent-browser validation script completes end-to-end
- [ ] Manual sanity: inbound informal opt-out → dashboard shows count → queue resolves correctly → badge appears on calendar card and appointment detail → Send Confirmation is disabled
- [ ] All acceptance criteria met
- [ ] Alembic upgrade/downgrade round-trips cleanly (`alembic upgrade head && alembic downgrade -1 && alembic upgrade head`)

---

## NOTES

**Design decisions / tradeoffs:**

1. **`entity_type='customer'` vs `entity_type='phone'` for unresolved phones.** Preference is customer attachment so the frontend can render a clickable link and the backend can check consent by `customer_id`. Fallback to `phone` when the inbound arrives from a lead-only phone — the admin will then need to manually attach the phone to a customer before confirming the opt-out. This matches how `NotificationService.send_admin_cancellation_alert` already behaves.

2. **Why a no-op migration?** `opt_out_method` is `String(50)` already — no schema change required. The migration file reserves the revision number in the alembic chain and documents the new enum value for future readers. Omitting it leaves the chain clean but introduces ambiguity about whether the schema was reviewed.

3. **Auto-suppression granularity.** The gap spec asks for "middle ground that protects the customer without auto-deciding compliance." The chosen design splits non-urgent (reminders, marketing, reviews — suppress during pending) from urgent (confirmations, en-route, completion — pass through). This preserves the operator's ability to honor the day-of appointment for customers who sent "stop texting me" the same morning.

4. **Frontend OptOutBadge implementation — single query vs batch.** For calendar views with many events, per-event `useCustomerConsentStatus` will fire N queries; TanStack de-dupes by key but N still grows linearly. If load-time issues appear, add `POST /api/v1/customers/consent-status/batch` and drive it from `weeklySchedule` response enrichment. Defer until measured.

5. **Audit attribution on `SmsConsentRecord`.** When admin confirms an informal opt-out, `created_by_staff_id` captures the actor. The existing `text_stop` path leaves this null — keep that behavior unchanged to preserve the "customer-initiated" distinction.

6. **CTIA compliance stance.** We are deliberately treating informal opt-out as a soft block + triage, not a hard auto-block. Rationale: false-positive phrase matching ("I want you to stop by Thursday to take me off the list of people waiting") would incorrectly opt the customer out. The admin-confirm step is the compliance insurance against phrase-match overfit. Document this choice in the PR description.

7. **Why `/alerts/informal-opt-out` (not `/compliance/opt-outs`)?** The existing dashboard alert surfacing pattern is `/alerts/<type-slug>`. Stay with the house style unless the user asks otherwise.

8. **Memory-persistent dev rules honored:** per the SMS test number rule, any test that triggers a real send must target `+19527373312`. Functional tests will use the null provider or a mocked provider so no real sends leave the dev environment.

---

## APPENDIX — PRE-IMPLEMENTATION VERIFICATIONS

These facts were verified by reading the codebase on 2026-04-21. Trust them unless the code has diverged.

| Claim | Verified by reading | Status |
|---|---|---|
| `AlertType` enum lives at `models/enums.py` lines 590–600 and does NOT yet include `INFORMAL_OPT_OUT` | Full file read | ✅ |
| `_flag_informal_opt_out` at `sms_service.py` lines 1035–1070 only logs a warning — no `Alert` row created today | Lines 1035–1070 read | ✅ |
| `_process_exact_opt_out` at lines 930–1021 is the structural template for admin-confirmed-informal flow | Lines 930–1021 read | ✅ |
| `check_sms_consent` signature at `services/sms/consent.py` line 37 — extend with kwarg | Full file read | ✅ |
| `check_sms_consent` is called from `send_message` at `sms_service.py` line 221 | Lines 215–235 read | ✅ |
| `send_message` signature at `sms_service.py` line 169 already has `consent_type: ConsentType = "transactional"` | Lines 169–210 read | ✅ |
| `_SUPERSEDABLE_MESSAGE_TYPES` frozenset at line 75 is the pattern for the new `_RESPECTS_PENDING_INFORMAL_OPT_OUT` set | Lines 72–82 read | ✅ |
| `ManagerOrAdminUser` type alias exists at `auth_dependencies.py` line 303 (maps to `require_manager_or_admin`) | Full file read | ✅ |
| `AlertRepository` at `alert_repository.py` has `create()` and `list_unacknowledged()`; need to add `get`, `list_unacknowledged_by_type`, `acknowledge` | Full file read | ✅ |
| `SmsConsentRecord.opt_out_method` is `String(50)` — no schema change needed for `'admin_confirmed_informal'` | `models/sms_consent_record.py` line 94–97 | ✅ |
| Latest migration HEAD is `20260421_100100_add_sent_messages_superseded_at.py` — use as `down_revision` | `ls migrations/versions/` | ✅ |
| Inbound SMS webhook route is `POST /api/v1/sms/webhook` (form-encoded, Twilio-signed) | `api/v1/sms.py` line 101 | ✅ |
| `AlertCard` at `frontend/src/features/dashboard/components/AlertCard.tsx` has variant `amber` and `targetPath` nav prop | Full file read | ✅ |
| `NoReplyReviewQueue.tsx` is the closest pattern for the new queue page (section header + count badge + confirm dialog + skeleton/error states) | Full file read | ✅ |
| `SendConfirmationButton.tsx` takes `appointment` prop; its internal `disabled = sendMutation.isPending \|\| !isDraft` — must extend to accept `customerId` and call `useCustomerConsentStatus` | Full file read | ✅ |
| No `tooltip.tsx` exists under `frontend/src/components/ui/` — use native `title=` attribute (pattern at `SendConfirmationButton.tsx` line 52) | `ls components/ui/` | ✅ |
| `CustomerMessages.tsx` is read-only (uses `useCustomerSentMessages`, renders message history) — has NO Send button to disable | Lines 1–80 read | ✅ |
| No ad-hoc per-customer SMS composer exists in the app; `MessageComposer.tsx` is the campaign-wizard Step 2, not per-customer | Lines 1–60 read | ✅ |
| Router lives at single file `frontend/src/core/router/index.tsx`; pages are lazy-loaded from `@/pages/{Name}`; no per-role UI route guard exists | Full file read | ✅ |
| `features/communications/` already has `api/`, `components/`, `hooks/`, `index.ts`, `types/`, `utils/` with public-API index | Directory listing + `index.ts` read | ✅ |
| `Customer.phone` lookup pattern is `select(Customer.id).where(Customer.phone.in_(_phone_variants(e164)))` — already used at `consent.py` line 155 | `Grep Customer.phone` | ✅ |
| `OPT_OUT_CONFIRMATION_MSG` constant at `sms_service.py` line 62 is reusable for the admin-confirmed path | Lines 61–64 read | ✅ |
| `log_consent_hard_stop` at `services/sms/audit.py` lines 126–138 is the mirror template for new audit helpers | Full file read | ✅ |
| Functional test fixture pattern exists at `tests/functional/test_no_reply_review_functional.py` | Located via grep | ✅ |
| `AlertResponse` Pydantic schema at `schemas/alert.py` already has `model_config = ConfigDict(from_attributes=True)` — reusable for the confirm/dismiss response | Full file read | ✅ |

### Remaining low-risk unknowns (won't block implementation)

- The exact body of `CustomerDetail.tsx` below line 139 (only read lines 90–139). Mitigation: the badge + ConsentHistoryPanel slot is described by anchor region; the implementer can pick the exact insertion line at implementation time.
- The body of `AppointmentForm.tsx` — only existence verified. Mitigation: the plan prescribes adding an amber banner at the top of the form; exact JSX insertion is mechanical once the file is opened.
- Whether `SMSConsentDeniedError` should carry a `reason_code` to let the frontend show a distinct toast for pending-informal vs hard-STOP denials. Mitigation: start without the distinction; add only if UX testing shows ambiguity.
