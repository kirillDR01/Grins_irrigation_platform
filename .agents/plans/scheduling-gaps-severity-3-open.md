# Feature: Close All Open Severity-3 Scheduling Gaps (05, 10, 12, 13, 14, 16)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models (`Alert`, `AlertType`, `AlertSeverity`, `AuditService`, `JobConfirmationResponse`, `RescheduleRequest`, `SmsConsentRecord`, `SentMessage`, `Communication`, `customerKeys`, `appointmentKeys`, `useWeeklySchedule`). Import from the right files — the project enforces vertical-slice boundaries (features import only from `core/` and `shared/`, never from each other).

## Feature Description

Close the **six remaining severity-3 gaps** from the inbound-SMS / confirmation-flow audit (`feature-developments/scheduling gaps/`). The severity-1 and severity-2 work (gaps 01, 03, 04, 06, 07, 11) is shipped to `dev`; this plan completes the remaining medium-severity items so admins can see and act on every customer reply event from the dashboard, the calendar, and the per-customer messages tab without cross-referencing four separate tables.

**The six gaps** (grouped by tier per the README's revised priority on 2026-04-26):

| Tier | Gap | Title | Area |
|---|---|---|---|
| A | **05** | Audit trail asymmetry — Y/R/opt-out not audited | Backend |
| A | **12** | Calendar cards lack reply-state badges | Frontend |
| A | **14** | Dashboard alert coverage (only 2 alert types defined) | Backend + Frontend |
| B | **13** | CustomerMessages tab is outbound-only | Frontend (+ small BE) |
| B | **16** | No unified SMS inbox — surfaced as a fourth queue card on `/schedule` | Backend + Frontend |
| C | **10** | Static no-reply escalation (no automated 2nd reminder) | Backend (+ UI config) |

Tier order matters: **A blocks B blocks C**. Gap 05 must land first (audit data), then Gap 14 alert types (these surface the new audit-driven events), then Gap 12 (which reuses Gap 14 alert counts in calendar badges). Gap 13 then 16 ride on the audit infrastructure and a clean inbound-event stream. Gap 10 is the most contained and lands last because Phase 2 (config UI) wants the alert coverage from Gap 14 to already exist.

## User Story

As an **admin / dispatcher operating Grin's Irrigation**,
I want to **see every customer reply, opt-out, reschedule request, and no-reply escalation surfaced on the dashboard, the calendar, the customer's Messages tab, and a unified SMS inbox — with a complete audit trail behind every event**,
so that **I can triage the morning's exceptions in one place, never miss a customer reply, and be able to answer "what happened to this appointment last Tuesday?" from a single source**.

## Problem Statement

Today, customer-driven SMS events (Y, R, opt-outs, free-text) are **structurally invisible** in the admin UI:

1. **Audit asymmetry (Gap 05)** — only customer `C` (cancel) is logged to `AuditLog`. `Y` (confirm), `R` (reschedule), STOP/informal opt-outs, manual reminders, "Mark Contacted", and admin drag-drop reschedules never write audit rows. "Who confirmed when?" requires joining 4+ tables.
2. **Dashboard blind spots (Gap 14)** — `AlertType` defines only 2 values (`CUSTOMER_CANCELLED_APPOINTMENT`, `CONFIRMATION_NO_REPLY`); 4 more were added by gaps 01/06/07 but aren't surfaced. Pending reschedules, unrecognized replies, orphan inbounds, late reschedule attempts, webhook health all flow into queues nobody routinely checks.
3. **Calendar visual deficit (Gap 12)** — appointment cards encode only status; an open `RescheduleRequest`, `needs_review_reason`, opted-out customer, or unrecognized reply is invisible at the calendar glance.
4. **Customer-level inbound invisibility (Gap 13)** — the per-customer Messages tab queries only `sent_messages`. Admins cannot see what the customer texted back without leaving the page.
5. **No unified inbox (Gap 16)** — inbound replies land in 4 different tables (`job_confirmation_response`, `reschedule_requests`, `campaign_responses`, `communications`); orphans and unrecognized replies have **no UI at all** and silently rot.
6. **Manual-only no-reply (Gap 10)** — the nightly flagger creates a queue but never sends a 2nd reminder. At 50 confirmations/day with 20% no-reply, ~30 rows pile up and get neglected.

## Solution Statement

Land six tightly-scoped, dependency-ordered work packages:

1. **WP-05 — uniform audit coverage** for `Y/R/STOP/informal-STOP`, manual reminder send, "Mark Contacted", and admin drag-drop reschedule, via `AuditService.log_action`. Add helper `_record_customer_sms_audit` mirroring `_record_customer_sms_cancel_audit`. Add `actor_type` discriminator into `details` (so existing `actor_id IS NULL` rows become disambiguatable). No schema migration — `AuditLog.details` is JSONB.
2. **WP-14 — alert coverage** by adding 3 new `AlertType` values (`PENDING_RESCHEDULE_REQUEST`, `UNRECOGNIZED_CONFIRMATION_REPLY`, `ORPHAN_INBOUND`), wiring creation hooks into the relevant services, adding `GET /api/v1/alerts/counts`, extending `GET /api/v1/alerts` with `alert_type[]`/`severity[]`/`offset`/`sort` query params, implementing `acknowledged=true`, and shipping dashboard `AlertCard` instances + per-type queue routes.
3. **WP-12 — calendar badges** by extending `AppointmentResponse._enrich_appointment_response` (or the weekly-schedule serializer) with a `reply_state` block, then rendering pills inside the existing `renderEventContent` callback in `CalendarView.tsx`. Reuses the `OptOutBadge` from `shared/components`.
4. **WP-13 — conversation view** by adding `GET /api/v1/customers/{id}/conversation` (server-side UNION of the four inbound/outbound sources) and refactoring `CustomerMessages.tsx` to a paired in/out chronological list. Read-only in this phase.
5. **WP-16 — unified inbox v0 as a fourth Schedule-tab queue card** by adding `GET /api/v1/inbox` (read-only, filterable, paginated, UNION across four tables) and a new `InboxQueue.tsx` component placed in `SchedulePage.tsx` immediately after `RecentlyClearedSection` (line 517). **No new route, no new top-nav entry, no new VSA slice.** Same card chrome as the existing `RescheduleRequestsQueue` / `NoReplyReviewQueue` siblings. Triage actions (link to appointment, archive, reply) deferred to v1/v2.
6. **WP-10 — automated 2nd reminder** by adding `send_day_2_reminders` to `background_jobs.py` with a small append-only `appointment_reminder_log` table, gated by a new `BusinessSetting` flag. Phase 1 only — config UI and per-customer tailoring deferred.

Each WP is independently shippable. Tiers A → B → C strictly serialize; within Tier A, **WP-05 → WP-14 → WP-12** is the recommended order.

## Feature Metadata

**Feature Type**: Enhancement (closes outstanding gaps in shipped feature)
**Estimated Complexity**: **High** (six work packages, ~6–8 weeks total; each WP individually Low-to-Medium)
**Primary Systems Affected**:
- Backend: `services/audit_service.py`, `services/job_confirmation_service.py`, `services/sms_service.py`, `services/appointment_service.py`, `services/background_jobs.py`, `services/campaign_response_service.py`, `services/communication_service.py` (new), `repositories/alert_repository.py`, `api/v1/alerts.py`, `api/v1/customers.py`, `api/v1/appointments.py`, `api/v1/inbox.py` (new)
- Models: `models/enums.py` (AlertType extension), new `models/appointment_reminder_log.py`
- Frontend: `features/schedule/components/CalendarView.tsx`, `features/schedule/components/SchedulePage.tsx` (slot a new InboxQueue card), new `features/schedule/components/InboxQueue.tsx`, `features/customers/components/CustomerMessages.tsx`, `features/dashboard/components/DashboardPage.tsx`, new `features/dashboard/components/*AlertCard.tsx` instances
- Migrations: 1–2 new alembic revisions (alert-counts index; reminder_log table)

**Dependencies**: SQLAlchemy 2.0 async, Pydantic 2, FastAPI, TanStack Query v5, React Hook Form (already in project). No new external libraries.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING!

#### Cross-cutting (read first)

- `feature-developments/scheduling gaps/README.md` — full status matrix and tier reordering as of 2026-04-26.
- `feature-developments/scheduling gaps/gap-05-audit-trail-gaps.md` — full WP-05 spec with the missing-audit table (5.A–5.F) and proposed `actor_type` discriminator.
- `feature-developments/scheduling gaps/gap-10-static-no-reply-escalation.md` — escalation ladder (stages 1–5), Phase 1/2/3 split.
- `feature-developments/scheduling gaps/gap-12-calendar-card-reply-state.md` — Tier-1/2/3 badge priority list, visual-density mitigation, `reply_state` JSON shape.
- `feature-developments/scheduling gaps/gap-13-customer-messages-outbound-only.md` — four-source UNION, conversation JSON shape, customer-level vs. appointment-level linkage.
- `feature-developments/scheduling gaps/gap-14-dashboard-alert-coverage.md` — 8 missing alert types (AT-1..AT-8), API extension shape, dedup considerations.
- `feature-developments/scheduling gaps/gap-16-unified-sms-inbox.md` — original three-pane layout proposal and four-table UNION/phasing (v0..v3). **Note: this plan deliberately deviates from the gap doc's three-pane layout** — see "Notes" section for rationale. The backend UNION and phasing are unchanged.
- `instructions/update2_instructions.md` — original product instructions; useful for "what does the customer flow look like" but secondary to the gap docs.

#### Steering / standards (loaded automatically by Kiro for matching files; treat as MUST-FOLLOW)

- `.kiro/steering/code-standards.md` — structured logging via `LoggerMixin`, three-tier testing (unit / functional / integration), Ruff + MyPy + Pyright zero-error gate.
- `.kiro/steering/api-patterns.md` — endpoint template (`set_request_id` → `DomainLogger.api_event` started/completed/failed → `clear_request_id` finally; 201/200/204 success + 400/404/500 errors).
- `.kiro/steering/frontend-patterns.md` — VSA imports (`@/core`, `@/shared`, `@/features/X`), TanStack Query key factory pattern, RHF + Zod form pattern, `cn()` for classes, `data-testid` conventions.
- `.kiro/steering/frontend-testing.md` — Vitest + RTL with `QueryProvider` wrapper, agent-browser CLI for E2E, coverage targets (Components 80% / Hooks 85% / Utils 90%).
- `.kiro/steering/spec-quality-gates.md` and `spec-testing-standards.md` — every spec MUST include three-tier testing, agent-browser validation, structured logging, type safety, and security sections.
- `.kiro/steering/structure.md` and `tech.md` — directory layout, naming, performance targets (<200 ms p95 API).
- `.kiro/steering/devlog-rules.md` and `auto-devlog.md` — DEVLOG.md update cadence (insert at top under "## Recent Activity", category prefix, what/why/how).
- `.kiro/steering/agent-browser.md` and `e2e-testing-skill.md` — agent-browser command reference; use for end-to-end UI validation.
- **EXCLUDE** from this work: `.kiro/steering/kiro-cli-reference.md`, `.kiro/steering/knowledge-management.md`, and the `pre-implementation-analysis.md` "kiroPowers" section — they describe Kiro CLI tools we don't use here.

#### WP-05 — Audit Coverage

- `src/grins_platform/services/audit_service.py:46-101` — `AuditService.log_action(db, *, actor_id, actor_role, action, resource_type, resource_id, details, ip_address, user_agent)`. **Reuse this** rather than calling `AuditLogRepository.create` directly.
- `src/grins_platform/services/job_confirmation_service.py:233-302` — `_handle_confirm`. Add audit write at the SCHEDULED→CONFIRMED transition (line 290) AND at the `confirmed_repeat` short-circuit (line 274).
- `src/grins_platform/services/job_confirmation_service.py:357-510` — `_handle_reschedule`. Add audit write where the new `RescheduleRequest` is inserted; also at the late-reschedule rejection branch (line 392).
- `src/grins_platform/services/job_confirmation_service.py:618-702` — `_handle_cancel`. Already audited at `_record_customer_sms_cancel_audit` (700-740) — **mirror this pattern**.
- `src/grins_platform/services/sms_service.py:1040-1140` — `_process_exact_opt_out` (STOP). Add audit write here.
- `src/grins_platform/services/sms_service.py:1153-1216` — `_flag_informal_opt_out`. Add audit write here.
- `src/grins_platform/services/sms_service.py:1300-1380` — `confirm_informal_opt_out`. Already emits structured log events; add `AuditLog` row.
- `src/grins_platform/services/appointment_service.py:1219-1280` — `_record_reschedule_reconfirmation_audit` (admin resolves a reschedule request). **Pattern to mirror.**
- `src/grins_platform/services/appointment_service.py:754-823` — `_record_cancellation_audit` (admin direct cancel). **Pattern to mirror.**
- `src/grins_platform/services/appointment_service.py:386-542` — `update_appointment` (admin drag-drop reschedule path). **VERIFIED 2026-04-26: this path IS already audited** via `_record_update_audit` (`appointment_service.py:570-616`, action `appointment.update`) and `_record_reactivate_audit` (`appointment_service.py:618-660`, action `appointment.reactivate`). Gap 05.F is therefore **partially satisfied** — the row exists with `pre`/`post` field snapshots and `changed_fields` list. **Remaining work**: enrich the existing `details` dict with `actor_type='staff'`, `source='admin_ui'`, and a derived `is_reschedule: bool` flag (computed from `is_rescheduling` at line 429). Do NOT add a new audit row.
- `src/grins_platform/api/v1/appointments.py:681-727` — `mark_appointment_contacted` route handler. **Audit site**: the route handler already holds `_current_user: ManagerOrAdminUser` and the session — capture `prior_reason = appt.needs_review_reason` BEFORE line 717 (`appt.needs_review_reason = None`) and write the audit row right after the flush. Action `appointment.mark_contacted`, `actor_type='staff'`, `actor_id=_current_user.id`, `details={"prior_reason": prior_reason}`.
- `src/grins_platform/api/v1/appointments.py:736-781` — `send_reminder_sms` route handler. **Audit site**: after `service.send_confirmation_sms(appointment_id)` succeeds at line 763 and before the response build at line 777. Action `appointment.reminder_sent`, `actor_type='staff'`, `actor_id=_current_user.id`, `details={"sent_message_id": result.get("sent_message_id"), "stage": "manual", "sms_sent": sms_sent}`. Pull `sent_message_id` from the `result` dict returned by `send_confirmation_sms` (verify the key shape — likely contains `message_id` or `sent_message_id`).
- `src/grins_platform/models/audit_log.py:21-68` — `AuditLog` model. `details` is JSONB (extend with `actor_type` and `source` keys).
- `src/grins_platform/repositories/audit_log_repository.py` — already exists; do not refactor.

#### WP-14 — Dashboard Alert Coverage

- `src/grins_platform/models/enums.py:580-604` — `AlertSeverity` (info/warning/error) + current `AlertType` enum (8 values today; need to ADD `PENDING_RESCHEDULE_REQUEST`, `UNRECOGNIZED_CONFIRMATION_REPLY`, `ORPHAN_INBOUND`). `MMS_RECEIVED`, `STALE_THREAD_REPLY`, `WEBHOOK_FAILURE` are deferred (covered by gaps 09, 03.B, 07 respectively).
- `src/grins_platform/models/alert.py:21-120` — `Alert` model. **No schema change needed**; existing `idx_alerts_type_acknowledged_at` composite index supports the counts query.
- `src/grins_platform/repositories/alert_repository.py:1-180` — extend with `count_unacknowledged_by_type`, `list_unacknowledged_filtered(types: list[str], severities: list[str], offset, limit, sort)`, and `list_acknowledged(limit, offset, since: datetime | None)` methods.
- `src/grins_platform/api/v1/alerts.py:1-245` — already has `confirm-opt-out` and `dismiss` POST routes from Gap 06. **Extend** the existing `list_alerts` GET (line 50–110) with the new query params; **add** `GET /alerts/counts` and `POST /alerts/{id}/acknowledge`.
- `src/grins_platform/services/job_confirmation_service.py:_handle_reschedule` insertion site — emit `PENDING_RESCHEDULE_REQUEST` alert at the new-RescheduleRequest path (only if not duplicate).
- `src/grins_platform/services/job_confirmation_service.py:883` — `_handle_needs_review`. The first branch (lines ~905–960) attaches the reply to an existing open `RescheduleRequest`; the **else** branch (where `reschedule_req is None`) sets `response.status='needs_review'` — that is the emit site for `UNRECOGNIZED_CONFIRMATION_REPLY` alert.
- `src/grins_platform/services/sms_service.py` — webhook fallthrough path (search `_record_orphan` / `direction='inbound'` write into `communications`) — emit `ORPHAN_INBOUND` alert.
- `frontend/src/features/dashboard/components/AlertCard.tsx:1-126` — generic component. **Reuse**, do not modify the public API.
- `frontend/src/features/dashboard/components/InformalOptOutAlertCard.tsx:1-29` — concrete-AlertCard pattern that mirrors what each new alert card should look like (count from a hook → AlertCard with target path + variant + icon + testId).
- `frontend/src/features/dashboard/hooks/useInformalOptOutCount.ts` — pattern for the per-type count hook.
- `frontend/src/features/dashboard/components/DashboardPage.tsx:104-105` — current `<InformalOptOutAlertCard />` placement. New cards (PendingReschedule, UnrecognizedReply, NoReplyConfirmation, OrphanInbound) drop in here.

#### WP-12 — Calendar Reply-State Badges

- `frontend/src/features/schedule/components/CalendarView.tsx:54-63` — `statusColors` map. Existing visual vocabulary.
- `frontend/src/features/schedule/components/CalendarView.tsx:100-181` — `events` `useMemo` that builds FullCalendar event inputs. **Read `appointment.reply_state` here**; emit class names / extendedProps for each badge.
- `frontend/src/features/schedule/components/CalendarView.tsx:199-239` — `renderEventContent` callback. **Render badges here** alongside the existing `prepaid-indicator-${id}` and `attachment-badge-${id}` patterns. Right-aligned pill stack, 2–3 max, priority-ordered.
- `frontend/src/features/schedule/components/CalendarView.css` — add badge color classes (amber/orange/red/purple) consistent with existing.
- `frontend/src/features/schedule/types.ts` (search) — extend the `Appointment` type with optional `reply_state`.
- `src/grins_platform/api/v1/appointments.py:336-385` — `get_weekly_schedule`. The serializer (`_enrich_appointment_response` near top of file) is where the `reply_state` block must be populated.
- `src/grins_platform/services/appointment_service.py:895-913` — `get_weekly_schedule` service. Either eagerly join `RescheduleRequest`/`SmsConsentRecord`/`JobConfirmationResponse` OR have `_enrich_appointment_response` call a small `_compute_reply_state(appointment_id, customer_id)` helper. Bias toward a single eager query.
- `frontend/src/shared/components/OptOutBadge.tsx` (Gap 06) — **REUSE** for the opt-out indicator.

#### WP-13 — CustomerMessages Conversation View

- `frontend/src/features/customers/components/CustomerMessages.tsx:1-139` — current outbound-only flat list. **Replace render** with a paired in/out chronological view; keep the existing `OptOutBadge` header and 60 s polling.
- `frontend/src/features/customers/hooks/useCustomers.ts:120-131` — `useCustomerSentMessages` (60 s `refetchInterval`). **Add** parallel `useCustomerConversation(customerId)` hook that hits the new endpoint.
- `frontend/src/features/customers/api/customerApi.ts` (search `listSentMessages`) — pattern for the new `getConversation(customerId, params?)` API call.
- `src/grins_platform/api/v1/customers.py` — add `GET /customers/{id}/conversation` that delegates to a new `CustomerConversationService` (or a method on `CustomerService`).
- `src/grins_platform/models/sent_message.py` — outbound source. Has `customer_id` (verified).
- `src/grins_platform/models/job_confirmation.py:55` — `JobConfirmationResponse.customer_id` is **NOT NULL FK to customers.id** (verified 2026-04-26). No JOIN needed. `RescheduleRequest.customer_id` at `job_confirmation.py:126` is also **NOT NULL FK**. Both already indexed via the appointment FK.
- `src/grins_platform/models/campaign_response.py:47` — `customer_id` is `UUID | None` (nullable — orphans permitted). Filter must `OR(customer_id == X, AND(customer_id IS NULL, from_phone == customer.phone))` for orphan correlation.
- `src/grins_platform/models/communication.py:35` — `customer_id` is **NOT NULL FK**. Already indexed by `idx_communications_customer_id`.
- `src/grins_platform/models/sms_consent_record.py` — INSERT-ONLY; `customer_id` is `UUID | None` (line 55), `phone_number` indexed (line 43). Latest-per-customer query: `ORDER BY consent_timestamp DESC LIMIT 1`.

#### WP-16 — Unified SMS Inbox (as fourth Schedule-tab queue card)

- All four data sources from WP-13 — same UNION shape, but customer-agnostic (cross-customer). **Reuse the same merge helper.**
- Backend (unchanged from original plan): `src/grins_platform/api/v1/inbox.py` (route), `src/grins_platform/services/inbox_service.py` (UNION + filter), `src/grins_platform/schemas/inbox.py` (response models).
- Router registration site: `src/grins_platform/api/v1/router.py:19` (alerts row pattern). Add `from grins_platform.api.v1.inbox import router as inbox_router` and include in the api_router list (insert alphabetically near `invoices_router`).
- Frontend (revised — single component, no new slice/route):
  - `frontend/src/features/schedule/components/InboxQueue.tsx` — mirrors `RescheduleRequestsQueue.tsx` and `NoReplyReviewQueue.tsx` chrome.
  - `frontend/src/features/schedule/hooks/useInbox.ts` — TanStack Query with 60 s `refetchInterval` parity.
  - `frontend/src/features/schedule/api/inboxApi.ts` (or extend `appointmentApi.ts` if pattern fits).
  - **Mounted in** `frontend/src/features/schedule/components/SchedulePage.tsx` after `<RecentlyClearedSection />` (line 517). Use anchor `id="inbox-queue"` so dashboard alert cards can deep-link via `/schedule#inbox-queue`.
- **No** new top-level route, **no** new top-nav entry, **no** new VSA slice.

#### WP-10 — No-Reply Escalation

- `src/grins_platform/services/background_jobs.py:710-905` — `NoReplyConfirmationFlagger`. **Add new** `Day2ReminderJob` class (mirror pattern). New module-level singleton + `send_day_2_reminders_job()` entry point at line ~963.
- `src/grins_platform/services/business_setting_service.py` — pattern to add `confirmation_day_2_reminder_enabled` boolean setting and `confirmation_day_2_reminder_offset_hours` integer (default 48).
- `src/grins_platform/services/sms_service.py` (search `send_appointment_confirmation` / `send_confirmation_sms`) — outbound prompt builder. Reuse for the day-2 send (same Y/R/C prompt; different copy).
- `src/grins_platform/models/sent_message.py` — `MessageType` enum lives in `models/enums.py`. **Add** `APPOINTMENT_REMINDER_DAY_2` value (or reuse `APPOINTMENT_REMINDER` with a `metadata.stage='day_2'` discriminator — recommend the latter to avoid an enum migration).
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx:1-336` — read-only lookup of how the queue currently works (already exists, do not modify in this WP).
- `src/grins_platform/scheduler.py` — register the new APScheduler job.

### New Files to Create

#### WP-05 — Audit
- _No new files._ Add helper methods (`_record_customer_sms_confirm_audit`, `_record_customer_sms_reschedule_audit`, `_record_customer_sms_opt_out_audit`, `_record_admin_drag_drop_audit`, `_record_manual_reminder_audit`, `_record_mark_contacted_audit`) inside the existing services.

#### WP-14 — Alerts

- `frontend/src/features/dashboard/hooks/usePendingRescheduleCount.ts`
- `frontend/src/features/dashboard/hooks/useUnrecognizedReplyCount.ts`
- `frontend/src/features/dashboard/hooks/useNoReplyCount.ts` (driven off `confirmation_no_reply` count)
- `frontend/src/features/dashboard/hooks/useOrphanInboundCount.ts`
- `frontend/src/features/dashboard/hooks/useAlertCounts.ts` (single-call alternative; PREFERRED — one query feeds all per-type cards)
- `frontend/src/features/dashboard/components/PendingRescheduleAlertCard.tsx`
- `frontend/src/features/dashboard/components/UnrecognizedReplyAlertCard.tsx`
- `frontend/src/features/dashboard/components/NoReplyConfirmationAlertCard.tsx`
- `frontend/src/features/dashboard/components/OrphanInboundAlertCard.tsx`
- (Optional, defer if scope tight) `frontend/src/features/alerts/` — generic `/alerts` index page with type/severity filters.

#### WP-12 — Calendar
- _No new files._ Extend existing `CalendarView.tsx` and the appointment serializer.

#### WP-13 — Conversation
- `src/grins_platform/services/customer_conversation_service.py` (or method on `CustomerService`) — UNION across the four tables.
- `src/grins_platform/schemas/customer_conversation.py` — `ConversationItem`, `ConversationResponse`, pagination cursor schema.
- `frontend/src/features/customers/hooks/useCustomerConversation.ts`

#### WP-16 — Inbox (single component inside the existing schedule slice)
- `src/grins_platform/api/v1/inbox.py`
- `src/grins_platform/services/inbox_service.py`
- `src/grins_platform/schemas/inbox.py`
- `frontend/src/features/schedule/components/InboxQueue.tsx`
- `frontend/src/features/schedule/hooks/useInbox.ts`
- `frontend/src/features/schedule/api/inboxApi.ts` (optional — may extend existing `appointmentApi.ts`).
- **NOT** creating: `features/inbox/` slice, three-pane layout components, new route, or top-nav entry.

#### WP-10 — Reminders
- `src/grins_platform/migrations/versions/{YYYYMMDD}_create_appointment_reminder_log.py`
- `src/grins_platform/models/appointment_reminder_log.py` — `id`, `appointment_id` FK, `stage` (day_2 | day_before | morning_of), `sent_at`, `sent_message_id` FK, `cancelled_at`. Append-only.
- `src/grins_platform/repositories/appointment_reminder_log_repository.py`
- New `Day2ReminderJob` class inside `services/background_jobs.py`.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [SQLAlchemy 2.0 — UNION ALL across heterogeneous tables](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.union_all)
  - Section: "Composing UNION queries with explicit casting"
  - Why: WP-13 and WP-16 must UNION across `sent_messages`, `job_confirmation_response`, `campaign_responses`, `communications` with column shapes that differ. Use `select(literal_column(...).label(...))` to align column names; or do per-source `select` and merge in Python (simpler, OK at <500 inbound/day volume).
- [SQLAlchemy 2.0 — async patterns + `selectinload`](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#selectin-eager-loading)
  - Section: "selectin loading"
  - Why: WP-12 reply_state computation needs to avoid N+1 queries when serializing 50–100 weekly appointments. Eager-load `RescheduleRequest`, `SmsConsentRecord` per-customer in one query.
- [TanStack Query v5 — Cursor pagination](https://tanstack.com/query/latest/docs/framework/react/guides/infinite-queries)
  - Section: "useInfiniteQuery"
  - Why: WP-13 customer conversation and WP-16 inbox both want cursor-based "load more" (newest-first).
- [FullCalendar — eventContent custom rendering](https://fullcalendar.io/docs/event-render-hooks)
  - Section: "eventContent"
  - Why: WP-12 badges land inside the existing `renderEventContent` callback.
- [Pydantic 2 — `model_validate` from ORM with computed fields](https://docs.pydantic.dev/2.0/usage/computed_fields/)
  - Why: WP-12 `reply_state` computed field on the `AppointmentResponse` schema.
- [Alembic — non-data-loss migrations](https://alembic.sqlalchemy.org/en/latest/cookbook.html#conditional-migration-elements)
  - Why: WP-10 needs a new `appointment_reminder_log` table; WP-14 may need a partial index for `count(*)` performance.
- [APScheduler — `AsyncIOScheduler`](https://apscheduler.readthedocs.io/en/3.x/userguide.html#choosing-the-right-scheduler-job-store-s-executor-s-and-trigger-s)
  - Section: "Adding jobs"
  - Why: WP-10 register the day-2 reminder job at hourly cadence.

### Patterns to Follow

**Naming Conventions:**
```python
# Backend services
class FooService(LoggerMixin):
    DOMAIN = "foo"  # business | sms | scheduler | webhook | api | audit

    async def operation_verb_noun(self, ...) -> ReturnType:
        self.log_started("operation", key=value)  # OR log_event with kwargs
        try:
            ...
            self.log_completed("operation", result=...)
        except ValidationError as e:
            self.log_rejected("operation", reason=str(e))
            raise
```
- Method names use **verb_noun_qualifier** snake_case: `record_customer_sms_confirm_audit`, `count_unacknowledged_by_type`, `list_pending_rescheduled`.
- Frontend hooks follow `use{Noun}{Action?}` PascalCase: `useAlertCounts`, `useCustomerConversation`, `useInbox`.
- Alert types are `UPPER_SNAKE_CASE` enum keys with lowercase string values: `PENDING_RESCHEDULE_REQUEST = "pending_reschedule_request"`.

**AuditLog details JSONB shape** (reused across WP-05):
```python
details = {
    "actor_type": "customer" | "staff" | "system",  # NEW discriminator
    "source": "customer_sms" | "admin_ui" | "nightly_job",
    "raw_body": "Y",  # nullable; only on inbound
    "from_phone": "+1952...",  # nullable; only on inbound; already-PII-OK in details
    "response_id": "<uuid>",  # FK back to JobConfirmationResponse if applicable
    "pre_status": "scheduled",
    "post_status": "confirmed",
}
# action keys (enumerated, do NOT make up new ones):
#   appointment.confirm
#   appointment.reschedule_requested
#   appointment.cancel                         (already exists)
#   appointment.reschedule.reconfirmation_sent (already exists, admin)
#   appointment.reschedule.admin_drag_drop     (NEW)
#   appointment.reminder_sent                  (NEW; manual reminder)
#   appointment.mark_contacted                 (NEW)
#   consent.opt_out_sms                        (NEW; STOP keyword)
#   consent.opt_out_informal_flag              (NEW; informal STOP)
#   consent.opt_out_admin_confirmed            (already partially via SMSService)
```

**API endpoint template** (verbatim from `.kiro/steering/api-patterns.md`):
```python
router = APIRouter(prefix="/inbox", tags=["inbox"])

class _InboxEndpoints(LoggerMixin):
    DOMAIN = "api"

_endpoints = _InboxEndpoints()

@router.get(
    "",
    response_model=InboxListResponse,
    summary="List unified inbox events",
)
async def list_inbox(
    _user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    triage: str | None = Query(default=None, description="pending|handled|dismissed"),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> InboxListResponse:
    _endpoints.log_started("list_inbox", triage=triage, limit=limit)
    service = InboxService(session)
    result = await service.list_events(triage=triage, cursor=cursor, limit=limit)
    _endpoints.log_completed("list_inbox", count=len(result.items))
    return result
```

**TanStack Query key factory** (mirror `customerKeys` and `appointmentKeys`):
```ts
export const alertKeys = {
  all: ['alerts'] as const,
  lists: () => [...alertKeys.all, 'list'] as const,
  list: (params: AlertListParams) => [...alertKeys.lists(), params] as const,
  counts: () => [...alertKeys.all, 'counts'] as const,
};

// Inbox lives inside the schedule feature slice; key namespaces under 'schedule'.
export const inboxKeys = {
  all: ['schedule', 'inbox'] as const,
  list: (filters: InboxFilters) => [...inboxKeys.all, 'list', filters] as const,
};

export const customerKeys = {
  // ...existing keys...
  conversation: (id: string, params?: ConversationParams) =>
    [...customerKeys.all, id, 'conversation', params] as const,
};
```

**`AlertCard` instance pattern** (mirror `InformalOptOutAlertCard.tsx`):
```tsx
import { CalendarClock } from 'lucide-react';
import { AlertCard } from './AlertCard';
import { useAlertCounts } from '../hooks/useAlertCounts';

export function PendingRescheduleAlertCard() {
  const { data } = useAlertCounts();
  const count = data?.pending_reschedule_request ?? 0;
  if (count <= 0) return null;
  return (
    <AlertCard
      title="Pending reschedule requests"
      description="Customers asked to move their appointment — admin action required."
      count={count}
      icon={CalendarClock}
      targetPath="/schedule"
      queryParams={{ tab: 'reschedule-queue' }}
      variant="amber"
      testId="pending-reschedule-alert-card"
    />
  );
}
```

**Calendar badge slot pattern** (in `renderEventContent`):
```tsx
{appointment.reply_state?.has_pending_reschedule && (
  <span
    className="ml-1 inline-flex items-center rounded px-1 py-0.5 text-[9px] font-bold leading-none bg-amber-100 text-amber-700 border border-amber-200"
    data-testid={`pending-reschedule-badge-${event.id}`}
    title={`Reschedule requested ${formatDistanceToNow(...)}`}
  >
    ↻
  </span>
)}
```

**Logging Pattern (project convention `{domain}.{component}.{action}_{state}`):**
- `audit.customer_sms.confirm_recorded` / `..._failed`
- `alerts.counts.queried`
- `appointments.reply_state.computed`
- `inbox.union.queried`
- `customer_conversation.merged`
- `scheduler.day_2_reminder.sent` / `..._skipped` / `..._failed`

---

## IMPLEMENTATION PLAN

### Phase 0: Foundation (cross-WP)

**Tasks:**
- Verify the `AuditService.log_action` signature handles all the new `details` shapes (it does — `details: dict[str, Any] | None` is JSONB).
- Confirm `actor_type` can live in `details` (no schema migration). Document the discriminator in `services/audit_service.py` module docstring.
- Confirm there is no automatic `MessageType.APPOINTMENT_REMINDER_DAY_2` already; recommendation is to put `stage` into `SentMessage.metadata` JSONB instead of expanding the enum (low-risk, no migration).

### Phase 1 — Tier A: Audit + Alerts + Calendar Badges

#### WP-05 — Audit Coverage

**Tasks:**
1. Add `_record_customer_sms_confirm_audit` to `JobConfirmationService` mirroring `_record_customer_sms_cancel_audit`.
2. Wire it from both branches of `_handle_confirm` (first-Y transition AND `confirmed_repeat` short-circuit, with distinct `action` values: `appointment.confirm` vs `appointment.confirm_repeat`).
3. Add `_record_customer_sms_reschedule_audit`. Wire from `_handle_reschedule` at the new-RescheduleRequest insert (line ~440) AND at the late-reschedule rejection (line 392).
4. Add `_record_customer_sms_opt_out_audit` to `SMSService` (action `consent.opt_out_sms` for STOP, `consent.opt_out_informal_flag` for informal). Wire from `_process_exact_opt_out` and `_flag_informal_opt_out`.
5. Audit `confirm_informal_opt_out` (admin admin-confirmed informal opt-out) — verify if not already via existing `log_informal_opt_out_confirmed` and add `AuditLog` row if missing.
6. Audit admin "Send Reminder SMS" — find the manual reminder endpoint in `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` → trace to backend → add audit at the send site.
7. Audit "Mark Contacted" — find the endpoint that clears `needs_review_reason` → add audit.
8. Audit admin drag-drop reschedule — `appointment_service.py:update_appointment` → if no audit, add `appointment.reschedule.admin_drag_drop` audit row.
9. Standardize `details.actor_type` across the existing `_record_customer_sms_cancel_audit`, `_record_cancellation_audit`, `_record_reschedule_reconfirmation_audit` so all three rows are queryable on the same shape.

#### WP-14 — Dashboard Alert Coverage

**Tasks:**
10. Add 3 new `AlertType` values to `models/enums.py`: `PENDING_RESCHEDULE_REQUEST`, `UNRECOGNIZED_CONFIRMATION_REPLY`, `ORPHAN_INBOUND`. (Defer `MMS_RECEIVED`, `STALE_THREAD_REPLY`, `WEBHOOK_FAILURE` to gaps 09/03.B/07.)
11. Wire `PENDING_RESCHEDULE_REQUEST` alert creation in `_handle_reschedule` at the new-RescheduleRequest insert (only when no duplicate). Severity = `WARNING`. `entity_type='appointment'`, `entity_id=appointment_id`.
12. Wire `UNRECOGNIZED_CONFIRMATION_REPLY` alert in `_handle_needs_review` (when `JobConfirmationResponse.status='needs_review'` and no open `RescheduleRequest`). Severity = `INFO` first occurrence, `WARNING` if 2+ for same appointment within 24 h.
13. Wire `ORPHAN_INBOUND` alert in `SMSService` where inbound falls through to `communications` with `direction='inbound'` and no customer correlation. Severity = `INFO`.
14. Auto-acknowledge `PENDING_RESCHEDULE_REQUEST` alert when `RescheduleRequest.status='resolved'` (hook in `appointment_service.reschedule_for_request`).
15. Extend `AlertRepository` with `count_unacknowledged_by_type()` returning `dict[str, int]`, `list_unacknowledged_filtered()`, and `list_acknowledged()`.
16. Extend `GET /api/v1/alerts` with new query params `alert_type: list[str] | None`, `severity: list[str] | None`, `offset: int`, `sort: 'created_at_asc' | 'created_at_desc'`. Implement the `acknowledged=True` path (currently returns `[]`).
17. Add `GET /api/v1/alerts/counts` returning per-type counts dict. Cache via dashboard's existing 60 s `refetchInterval` — no server-side caching needed at our volume.
18. Add `POST /api/v1/alerts/{id}/acknowledge` (manual ack from a generic `/alerts` page); reuse `AlertRepository.acknowledge`.
19. Frontend: add `useAlertCounts` hook (single query feeds all dashboard cards).
20. Add `PendingRescheduleAlertCard`, `UnrecognizedReplyAlertCard`, `NoReplyConfirmationAlertCard`, `OrphanInboundAlertCard` (mirror `InformalOptOutAlertCard.tsx`).
21. Place all four new cards in `DashboardPage.tsx` next to the existing `<InformalOptOutAlertCard />` (line 105).
22. Defer the generic `/alerts` index page (Tier-A is dashboard-cards-only; index page is a Phase-2 nice-to-have).

#### WP-12 — Calendar Reply-State Badges

**Tasks:**
23. Add a `ReplyState` Pydantic model to `schemas/appointment.py` with: `has_pending_reschedule: bool`, `has_no_reply_flag: bool`, `customer_opted_out: bool`, `has_unrecognized_reply: bool`, `last_reminder_sent_at: datetime | None`.
24. Extend `AppointmentResponse` (or the weekly-schedule-specific subclass) with `reply_state: ReplyState | None`.
25. Add `_compute_reply_state(appointment, customer_id)` helper to `AppointmentService` OR a new `appointment_reply_state_service.py`. Single-query approach: in `get_weekly_schedule`, eagerly fetch `RescheduleRequest` rows (joined on `appointment_id`), latest `SmsConsentRecord` per customer, latest `JobConfirmationResponse` with `status='needs_review'`. **Aim <50 ms p95 added latency at 100 appointments.**
26. Update `_enrich_appointment_response` in `api/v1/appointments.py` to populate `reply_state` from the precomputed dict.
27. Frontend: extend `Appointment` type in `features/schedule/types.ts` with the optional `reply_state` block.
28. In `CalendarView.tsx:renderEventContent` add 4 conditional pills (priority-ordered, max 3 visible at once):
    - `customer_opted_out` (priority 1, red, 🚫) — reuse the visual style from `OptOutBadge.tsx` if it exists in `shared/components`.
    - `has_pending_reschedule` (priority 2, amber, ↻).
    - `has_no_reply_flag` (priority 3, orange, ⚠).
    - `has_unrecognized_reply` (priority 4, purple, ❓).
29. Add CSS for the 4 new badge variants in `CalendarView.css` (consistent with existing `appointment-prepaid` / `appointment-confirmed`).
30. Mobile aggregation: on `useMediaQuery('(max-width: 767px)')` (already in scope) collapse 2+ badges into a single `⚠ N` aggregate badge with title text listing the issues.
31. Accessibility: every badge has `title` and (for screen-readers) `aria-label`.

### Phase 2 — Tier B: Conversation View + Unified Inbox

#### WP-13 — CustomerMessages Conversation View

**Tasks:**
32. Add `customer_id` (or verify) to `JobConfirmationResponse` rows. If missing, add via JOIN (`appointment.job.customer_id`) in the new query rather than schema migration — the model already has `appointment_id`.
33. Create `CustomerConversationService.list_conversation(customer_id, cursor=None, limit=50)`:
    - Query each of 4 sources for the customer (or phone match for orphans).
    - Build typed `ConversationItem` with `direction`, `timestamp`, `body`, `channel`, `parsed_keyword?`, `appointment_id?`, `status?`, `source_table`, `source_id`.
    - Sort by `timestamp` desc.
    - Cursor pagination on composite (`timestamp`, `id`).
34. Add `GET /api/v1/customers/{id}/conversation` route in `api/v1/customers.py`.
35. Frontend: add `useCustomerConversation(customerId)` hook (TanStack Query, 60 s `refetchInterval` parity with `useCustomerSentMessages`). Use `useInfiniteQuery` for cursor pagination.
36. Refactor `CustomerMessages.tsx`:
    - Switch data source to `useCustomerConversation`.
    - Render in/out as paired chronological items (right-aligned for outbound, left-aligned for inbound — mirror chat-app convention).
    - Each item: direction icon (📤/📥), timestamp, body, channel-icon, status badge for outbound, parsed-keyword badge for inbound.
    - Keep `OptOutBadge` header.
37. Add filters (Phase 1 minimal): channel toggle (SMS/email/all), date range. Free-text search and per-appointment filter deferred.
38. Pagination: "Load more" button at bottom (or auto-load on scroll-bottom). Initial 50 items.

#### WP-16 — Unified SMS Inbox v0 (as a Schedule-tab queue card)

**Tasks:**
39. Create `InboxService.list_events(triage, cursor, limit)` — UNION across the 4 sources (cross-customer). Reuse the merge helper pattern from WP-13.
40. Add `triage_status` derivation (computed, not stored): `pending` if `status in ('needs_review', 'orphan')` and not yet handled; `handled` if linked to a resolved appointment / acked alert; `dismissed` reserved for v1.
41. Schemas: `InboxItem`, `InboxListResponse`, `InboxFilters`.
42. `GET /api/v1/inbox` route — `ManagerOrAdminUser` guarded, cursor paginated.
43. Frontend: build `frontend/src/features/schedule/components/InboxQueue.tsx`:
    - Mirror the chrome of `RescheduleRequestsQueue.tsx` and `NoReplyReviewQueue.tsx`: card container, title with icon, "Updated <relative time>" + refresh button, table/list body, empty state, error state.
    - Filter pills row at the top of the card body: `All` · `Needs triage` · `Orphans` · `Unrecognized` · `Opt-outs` · `Archived`. Counts in pill labels driven by the same `useInbox` query response.
    - List rows: sender name + phone (or "Unknown number" for orphans), snippet (first 80 chars of body), timestamp, status pill, source-table icon (small).
    - Click a row → expands inline (accordion-style) to show full body + action buttons:
      - "Open appointment" (visible only if `correlated_appointment_id` is set) → routes to `/schedule` calendar with `AppointmentDetail` opened (reuse existing onEventClick pattern).
      - "Open customer" (visible only if `customer_id` is set) → routes to `/customers/{id}` Messages tab.
      - "Archive" (button rendered but disabled in v0 with tooltip "v1 feature").
    - "Load more" button at the bottom — same pattern as `NoReplyReviewQueue`.
    - Wrap the card in `<section id="inbox-queue">` so dashboard alert cards can deep-link via `/schedule#inbox-queue`.
44. Mount `<InboxQueue />` in `SchedulePage.tsx` immediately after `<RecentlyClearedSection />` at line 517. No other layout changes.
45. Update WP-14 alert cards' `targetPath` to `/schedule` and add `queryParams={{ section: 'inbox-queue' }}` (or use the URL-fragment form `targetPath="/schedule#inbox-queue"`) for the `OrphanInbound` and `UnrecognizedReply` cards.
46. **v0 is read-only.** Triage actions (link, archive, reply) deferred to v1.

### Phase 3 — Tier C: Automated Reminders

#### WP-10 — Day-2 No-Reply Reminder

**Tasks:**
47. Migration: create `appointment_reminder_log` table (`id`, `appointment_id` FK, `stage` String enum, `sent_at`, `sent_message_id` FK nullable, `cancelled_at` nullable, indexes on `appointment_id`, `stage + appointment_id`).
48. Model + repository following project patterns.
49. Add `BusinessSetting` rows: `confirmation_day_2_reminder_enabled` (bool, default `false` to opt-in safely on prod), `confirmation_day_2_reminder_offset_hours` (int, default 48).
50. New `Day2ReminderJob(LoggerMixin)` in `services/background_jobs.py`:
    - Hourly tick (configurable).
    - Query: SCHEDULED appointments whose latest `APPOINTMENT_CONFIRMATION` `SentMessage.sent_at` is between `now - 52h` and `now - 48h`, with no `JobConfirmationResponse` after that, and no `appointment_reminder_log(stage='day_2')` row yet.
    - For each: send the same Y/R/C prompt with day-2 copy ("Reminder: please reply Y to confirm…"), respect outbound time window (CT 8 AM–9 PM — already enforced upstream), respect opt-out (skip if customer's latest `SmsConsentRecord.consent_given=False`).
    - Insert `appointment_reminder_log(stage='day_2', sent_at=..., sent_message_id=...)` to dedup.
    - Audit `appointment.reminder_sent` (Gap 05 hook).
51. Register the job in `scheduler.py` (interval trigger every 1 h).
52. Edge cases:
    - Customer confirms BETWEEN reminder queue and send → re-check status before send; skip if not SCHEDULED.
    - Customer opts out mid-cycle → set `cancelled_at` on any pending reminder log row (none exist in v1 since we send synchronously, but reserve the column for future scheduled-send pattern).
    - Appointment cancelled/rescheduled → no action; the SCHEDULED status filter handles it.

### Phase 4 — Testing & Validation (across all WPs)

**Tasks:**
- Unit tests per service method (all WPs). `@pytest.mark.unit`, mocked DB.
- Functional tests for each new API endpoint (`/alerts/counts`, `/customers/{id}/conversation`, `/inbox`, `/alerts/{id}/acknowledge`). `@pytest.mark.functional`, real DB.
- Integration tests for end-to-end flows:
  - Customer Y → audit row exists with `actor_type='customer'` (WP-05).
  - Customer R → `RescheduleRequest` + `Alert(type=PENDING_RESCHEDULE_REQUEST)` + audit row + calendar `reply_state.has_pending_reschedule=true` (WP-05/12/14 cross-cut).
  - Day-2 reminder → second confirmation SMS sent + reminder log row + audit row (WP-05/10).
- Property-based tests (Hypothesis) for:
  - Reply-state computation: any combination of (open RescheduleRequest, no-reply flag, opt-out, unrecognized reply) yields a deterministic `ReplyState`.
  - Inbox merge invariant: items are strictly ordered by timestamp regardless of source-table order.
- Frontend component tests for each new card and the conversation view.
- agent-browser E2E: walk dashboard → click each new alert card → land on `/schedule` (with `#inbox-queue` anchor for the inbox-related cards); open a customer with conversation history → verify in/out pairing renders; scroll `/schedule` to bottom → verify `InboxQueue` card renders alongside the other three queues; calendar viewport mobile vs desktop badge rendering.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Tier A · WP-05 (Audit)

#### TASK-05.1 ADD module helper `_actor_type_discriminator` doc to `audit_service.py`

- **IMPLEMENT**: At the top of `services/audit_service.py`, add a module docstring section describing the `details.actor_type` discriminator (`customer | staff | system`) and the canonical `action` strings used by the customer-SMS path.
- **PATTERN**: existing module docstring (lines 1–9).
- **VALIDATE**: `uv run ruff format src/grins_platform/services/audit_service.py && uv run mypy src/grins_platform/services/audit_service.py`

#### TASK-05.2 ADD `_record_customer_sms_confirm_audit` to JobConfirmationService

- **IMPLEMENT**: Mirror `_record_customer_sms_cancel_audit` (line 704–740). Distinct `action='appointment.confirm'` (or `'appointment.confirm_repeat'`). Include `details={"actor_type": "customer", "source": "customer_sms", "pre_status": ..., "response_id": ..., "from_phone": ..., "raw_body": ...}`.
- **PATTERN**: `services/job_confirmation_service.py:704`.
- **IMPORTS**: `from grins_platform.repositories.audit_log_repository import AuditLogRepository` (lazy in-method, mirroring existing).
- **GOTCHA**: never let an audit failure propagate — wrap in `try / except Exception` and log via `self.log_failed`. The customer-facing reply must always succeed.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/services/test_job_confirmation_service.py -v -k confirm_audit`

#### TASK-05.3 WIRE confirm-audit from both branches of `_handle_confirm`

- **IMPLEMENT**: Call the helper at line 274 (`confirmed_repeat` branch) with `action='appointment.confirm_repeat'` and after line 297 (first-Y SCHEDULED→CONFIRMED transition) with `action='appointment.confirm'`.
- **PATTERN**: existing `_dispatch_admin_cancellation_alert` invocation in `_handle_cancel`.
- **GOTCHA**: pull `pre_status` BEFORE flushing the status update.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_confirmation_flow.py -v`

#### TASK-05.4 ADD `_record_customer_sms_reschedule_audit` and wire it

- **IMPLEMENT**: Helper mirrors confirm-audit; `action='appointment.reschedule_requested'` (or `'appointment.reschedule_rejected'` at the late-reschedule branch). Include `reschedule_request_id` in details.
- **PATTERN**: same as TASK-05.2.
- **WIRE FROM**: line ~440 (RescheduleRequest insert) and line 392 (late-reschedule rejection).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_reschedule_flow.py -v`

#### TASK-05.5 ADD `_record_customer_sms_opt_out_audit` to SMSService

- **IMPLEMENT**: Two helpers — one for STOP (`consent.opt_out_sms`) and one for informal (`consent.opt_out_informal_flag`). `details` includes `phone_number` (E.164), `consent_record_id` if exact, `alert_id` if informal, `raw_body`.
- **PATTERN**: `services/sms_service.py:1153–1216` already emits structured log events; add `AuditLogRepository.create` calls beside them.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/services/test_sms_service.py -v -k opt_out`

#### TASK-05.6 AUDIT manual "Send Reminder SMS" endpoint

- **IMPLEMENT**: Endpoint located at `src/grins_platform/api/v1/appointments.py:736-781` (`POST /appointments/{appointment_id}/send-reminder-sms`). Inject `AuditLogRepository` after `result = await service.send_confirmation_sms(appointment_id)` at line 763. Action `appointment.reminder_sent`, `resource_type='appointment'`, `resource_id=appointment_id`, `actor_id=_current_user.id`, `details={"actor_type": "staff", "source": "admin_ui", "stage": "manual", "sms_sent": sms_sent, "sent_message_id": result.get("sent_message_id") or result.get("message_id")}`. Wrap in `try/except Exception` and `_endpoints.log_failed` so audit failure never blocks the SMS reply path.
- **GOTCHA**: the route holds a session via `get_full_appointment_service` dependency — pull the session from `service.appointment_repository.session` to instantiate the audit repo (mirrors `appointment_service._record_update_audit:587-589` pattern).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_no_reply_review_functional.py -v -k reminder` (existing file at `tests/functional/test_no_reply_review_functional.py:172` already exercises this endpoint — extend with audit-row assertion).

#### TASK-05.7 AUDIT "Mark Contacted"

- **IMPLEMENT**: Endpoint located at `src/grins_platform/api/v1/appointments.py:681-727` (`POST /appointments/{appointment_id}/mark-contacted`). The handler reads/writes the Appointment directly. **Capture `prior_reason = appt.needs_review_reason` BEFORE line 717** (`appt.needs_review_reason = None`). After `await session.flush()` at line 718, write the audit row inline (no service refactor needed). Action `appointment.mark_contacted`, `resource_id=appointment_id`, `actor_id=_current_user.id`, `details={"actor_type": "staff", "source": "admin_ui", "prior_reason": prior_reason}`.
- **GOTCHA**: the existing handler uses `session: Annotated[AsyncSession, Depends(get_db_session)]` — instantiate `AuditLogRepository(session)` directly. Wrap in `try/except` so the user's "Mark Contacted" click never fails because of an audit-write hiccup.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_no_reply_review_functional.py -v -k mark_contacted` (existing test at line 250 — extend with `SELECT COUNT(*) FROM audit_log WHERE action='appointment.mark_contacted' AND resource_id=$1` assertion).

#### TASK-05.8 ENRICH existing admin drag-drop audit (Gap 05.F is partially satisfied)

- **STATUS**: **VERIFIED 2026-04-26** — `appointment_service.update_appointment` (lines 386–542) **already audits** via `_record_update_audit` (action `appointment.update`, line 600) and `_record_reactivate_audit` (action `appointment.reactivate`, line 642). Gap 05.F's "audit log coverage here needs verification" concern is resolved: rows DO exist with `pre`/`post` field snapshots and `changed_fields` list.
- **IMPLEMENT**: enrich the existing `details` dicts at `appointment_service.py:604-610` (`_record_update_audit`) and `:646-651` (`_record_reactivate_audit`) by adding:
  - `"actor_type": "staff" if actor_id is not None else "system"`
  - `"source": "admin_ui"`
  - `"is_reschedule": is_rescheduling` (the boolean computed at line 429–433; needs to be threaded as a new keyword argument into both `_record_*_audit` methods).
- **DO NOT** add a new audit row or change the `action` strings — that would break existing dashboards and queries.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_appointment_update_audit.py -v` (existing or to be created in same module as the bughunt M-7 tests).

#### TASK-05.9 RETROFIT `actor_type` into existing audit details

- **IMPLEMENT**: Add `"actor_type": "staff"` (or `"customer"`) to the existing details dicts in `_record_cancellation_audit`, `_record_reschedule_reconfirmation_audit`, and `_record_customer_sms_cancel_audit`. Backwards compatible — older rows simply lack the key.
- **VALIDATE**: `uv run pytest -v -k audit`

### Tier A · WP-14 (Alerts)

#### TASK-14.1 EXTEND `AlertType` enum

- **IMPLEMENT**: Add `PENDING_RESCHEDULE_REQUEST`, `UNRECOGNIZED_CONFIRMATION_REPLY`, `ORPHAN_INBOUND` to `models/enums.py:590-604`.
- **GOTCHA**: enum string values are stored as plain strings in the DB (no enum-type column); no migration required.
- **VALIDATE**: `uv run mypy src/ && uv run pyright src/`

#### TASK-14.2 EMIT `PENDING_RESCHEDULE_REQUEST` alert in `_handle_reschedule`

- **IMPLEMENT**: After successful new-RescheduleRequest insert (NOT on duplicate), `await alert_repo.create(Alert(type=AlertType.PENDING_RESCHEDULE_REQUEST.value, severity=AlertSeverity.WARNING.value, entity_type='appointment', entity_id=appointment_id, message=f"Reschedule requested by {customer_name}"))`.
- **PATTERN**: `services/background_jobs.py:885-893` — `Alert(...) → alert_repo.create(...)`.
- **VALIDATE**: `uv run pytest -v -k pending_reschedule_alert`

#### TASK-14.3 EMIT `UNRECOGNIZED_CONFIRMATION_REPLY` alert in `_handle_needs_review`

- **IMPLEMENT**: At the end of `_handle_needs_review`, create alert with severity `INFO`. Bump to `WARNING` if a similar alert already exists for this `appointment_id` in the last 24 h (cheap query).
- **VALIDATE**: `uv run pytest -v -k unrecognized_alert`

#### TASK-14.4 EMIT `ORPHAN_INBOUND` alert in inbound fallthrough

- **IMPLEMENT**: In `SMSService` where inbound writes to `communications` with `direction='inbound'` and no customer correlation. Severity `INFO`, `entity_type='communication'`, `entity_id=communication.id`, `message="Orphan inbound from <masked phone>"`.
- **VALIDATE**: `uv run pytest -v -k orphan_inbound_alert`

#### TASK-14.5 AUTO-ACKNOWLEDGE `PENDING_RESCHEDULE_REQUEST` on resolve

- **IMPLEMENT**: In `appointment_service.reschedule_for_request`, after the resolve transaction succeeds, find the matching open alert and `await alert_repo.acknowledge(alert.id)`.
- **GOTCHA**: lookup by `(type=PENDING_RESCHEDULE_REQUEST, entity_id=appointment_id, acknowledged_at IS NULL)`. Multiple opens not possible because of Gap 01.A unique index.
- **VALIDATE**: `uv run pytest -v -k auto_acknowledge_reschedule_alert`

#### TASK-14.6 EXTEND `AlertRepository`

- **IMPLEMENT**:
  - `count_unacknowledged_by_type() -> dict[str, int]` — `SELECT type, COUNT(*) FROM alerts WHERE acknowledged_at IS NULL GROUP BY type`.
  - `list_unacknowledged_filtered(types, severities, offset, limit, sort)` — composable `WHERE` clauses.
  - `list_acknowledged(limit, offset, since)` — implements the deferred path in the API.
- **PATTERN**: `repositories/alert_repository.py:111-146`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/repositories/test_alert_repository.py -v`

#### TASK-14.7 EXTEND `GET /api/v1/alerts`

- **IMPLEMENT**: Add `alert_type: list[str] | None`, `severity: list[str] | None`, `offset: int = 0`, `sort: Literal['created_at_asc', 'created_at_desc'] = 'created_at_desc'`. Implement `acknowledged=True` path via `repo.list_acknowledged`.
- **PATTERN**: existing `list_alerts` at `api/v1/alerts.py:50-110`.
- **GOTCHA**: keep backwards-compat — existing single-`type` query param remains valid.
- **VALIDATE**: `curl 'http://localhost:8000/api/v1/alerts?alert_type=pending_reschedule_request&alert_type=informal_opt_out&limit=10' -H 'Authorization: Bearer ...'`

#### TASK-14.8 ADD `GET /api/v1/alerts/counts`

- **IMPLEMENT**: New endpoint returning `dict[str, int]` keyed by `AlertType.value`. Logged via `_endpoints.log_started/completed("counts")`.
- **VALIDATE**: `curl http://localhost:8000/api/v1/alerts/counts` returns JSON of all 11 types.

#### TASK-14.9 ADD `POST /api/v1/alerts/{id}/acknowledge`

- **IMPLEMENT**: Generic ack endpoint that calls `repo.acknowledge`. Idempotent.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_alerts_api.py -v -k acknowledge`

#### TASK-14.10 FRONTEND `useAlertCounts` hook

- **IMPLEMENT**: New hook `frontend/src/features/dashboard/hooks/useAlertCounts.ts` with 60 s `refetchInterval`, query key `alertKeys.counts()`. Returns `Record<AlertType, number>`.
- **PATTERN**: `hooks/useInformalOptOutCount.ts`.
- **VALIDATE**: `npm test -- useAlertCounts` (write tests in same file).

#### TASK-14.11 CREATE four new `AlertCard` instances

- **IMPLEMENT**: `PendingRescheduleAlertCard.tsx`, `UnrecognizedReplyAlertCard.tsx`, `NoReplyConfirmationAlertCard.tsx`, `OrphanInboundAlertCard.tsx`. Each mirrors `InformalOptOutAlertCard.tsx`, reads from `useAlertCounts`, returns `null` if count<=0.
- **PATTERN**: `frontend/src/features/dashboard/components/InformalOptOutAlertCard.tsx`.
- **VALIDATE**: `npm test -- AlertCard`

#### TASK-14.12 PLACE new cards in `DashboardPage.tsx`

- **IMPLEMENT**: Insert after `<InformalOptOutAlertCard />` (line 105). Order by typical urgency: `<PendingRescheduleAlertCard />`, `<NoReplyConfirmationAlertCard />`, `<UnrecognizedReplyAlertCard />`, `<OrphanInboundAlertCard />`.
- **VALIDATE**: `npm test -- DashboardPage`

### Tier A · WP-12 (Calendar Badges)

#### TASK-12.1 ADD `ReplyState` schema

- **IMPLEMENT**: `class ReplyState(BaseModel)` in `schemas/appointment.py` — fields per Phase-1 above.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/schemas/test_appointment.py -v`

#### TASK-12.2 ADD `_compute_reply_state_map` to `AppointmentService`

- **IMPLEMENT**: New method `_compute_reply_state_map(appointment_ids: list[UUID], customer_ids: list[UUID]) -> dict[UUID, ReplyState]` issuing exactly **3 indexed queries** in parallel (`asyncio.gather`):
  1. `select(RescheduleRequest.appointment_id).where(RescheduleRequest.appointment_id.in_(appointment_ids), RescheduleRequest.status == "open")` → set of appointment_ids with pending reschedules.
  2. `select(SmsConsentRecord).where(SmsConsentRecord.customer_id.in_(customer_ids)).order_by(SmsConsentRecord.consent_timestamp.desc())` then DISTINCT-ON in Python by customer_id, taking the latest. Map customer→`consent_given`. (Postgres `DISTINCT ON (customer_id) ... ORDER BY customer_id, consent_timestamp DESC` is more efficient — use that if available.)
  3. `select(JobConfirmationResponse.appointment_id).where(JobConfirmationResponse.appointment_id.in_(appointment_ids), JobConfirmationResponse.status == "needs_review")` → set of appointment_ids with unrecognized replies.
  - The `needs_review_reason` and `last_reminder_sent_at` are already on the Appointment row (no extra query).
- **PATTERN**: mirrors the bulk-load pattern in `services/dashboard_service.py` (search for any `.in_(ids)` query as exemplar).
- **CALL FROM**: `AppointmentService.get_weekly_schedule` at `appointment_service.py:895-913`. After `appointments = await self.appointment_repository.get_weekly_schedule(...)`, build `appointment_ids = [a.id for a in flat_list]` and `customer_ids = [a.job.customer_id for a in flat_list]` (job already lazy-loaded by `selectin`), then call `reply_state_map = await self._compute_reply_state_map(appointment_ids, customer_ids)`. Return tuple `(schedule, total, reply_state_map)`.
- **GOTCHA**: budget **<50 ms p95** additional latency at 100 appointments. Verify by running `psql "$DATABASE_URL" -c "EXPLAIN ANALYZE SELECT ..."` against a seeded test DB. The `idx_alerts_type_acknowledged_at`-equivalent indexes already exist (`ix_sms_consent_records_customer_id`, `idx_confirmation_responses_appointment`, `idx_confirmation_responses_status`, `uq_reschedule_requests_open_per_appointment`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_weekly_schedule.py -v -k reply_state`

#### TASK-12.3 EXTEND `_enrich_appointment_response` to accept the map

- **IMPLEMENT**: Change signature at `api/v1/appointments.py:132` from `_enrich_appointment_response(appointment: object) -> AppointmentResponse` to `_enrich_appointment_response(appointment: object, reply_state: ReplyState | None = None) -> AppointmentResponse`. After `_populate_appointment_extended_fields` at line 135, set `response.reply_state = reply_state`.
- **CALL SITES TO UPDATE**: 3 existing call sites at `appointments.py:270`, `:325`, `:369` (the latter is the weekly-schedule renderer at line 367–372 — the one that matters for badges). Pass `reply_state=reply_state_map.get(a.id)` from the precomputed dict at the weekly-schedule call site only; the other two pass `None` (acceptable — list-view doesn't need badges in v0).
- **VALIDATE**: hit `GET /api/v1/appointments/weekly?start_date=2026-04-26` → response items each carry a `reply_state` block (or `null`). `uv run pytest src/grins_platform/tests/unit/api/test_appointments_api.py -v`.

#### TASK-12.4 EXTEND frontend `Appointment` type

- **IMPLEMENT**: Add `reply_state?: { has_pending_reschedule: boolean; has_no_reply_flag: boolean; customer_opted_out: boolean; has_unrecognized_reply: boolean; last_reminder_sent_at: string | null }` to `frontend/src/features/schedule/types.ts`.
- **VALIDATE**: `npm run typecheck`

#### TASK-12.5 RENDER badges in `renderEventContent`

- **IMPLEMENT**: 4 conditional pills inside the existing `<div className="flex items-center gap-1">` block at line 206. Reuse `OptOutBadge` from `shared/components` if it offers the visual; otherwise use the inline-pill pattern.
- **PATTERN**: `attachment-badge-${event.id}` block at line 218.
- **GOTCHA**: data-testids must follow `{action}-{feature}-${id}` convention: `pending-reschedule-badge-${id}`, `no-reply-badge-${id}`, `opt-out-badge-${id}`, `unrecognized-reply-badge-${id}`.
- **VALIDATE**: `npm test -- CalendarView`

#### TASK-12.6 ADD CSS variants and mobile aggregation

- **IMPLEMENT**: New classes `appointment-reply-amber`, `appointment-reply-orange`, `appointment-reply-red`, `appointment-reply-purple` in `CalendarView.css`. Mobile (sm breakpoint): if 2+ pills active, render single aggregate `⚠ N` pill with `title` listing the issues.
- **VALIDATE**: agent-browser viewport check — `agent-browser set viewport 375 812 && agent-browser screenshot mobile-calendar.png`.

### Tier B · WP-13 (Conversation View)

#### TASK-13.1 ADD conversation schemas

- **IMPLEMENT**: `schemas/customer_conversation.py` with `ConversationItem` (typed by `direction`, `channel`, `source_table`, `parsed_keyword`, etc.), `ConversationResponse(items, next_cursor, has_more)`.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/customer_conversation.py`

#### TASK-13.2 IMPLEMENT `CustomerConversationService.list_conversation`

- **IMPLEMENT**: New service file `services/customer_conversation_service.py`. **4 separate `select` queries** issued in parallel via `asyncio.gather` (NOT a SQL UNION — column shapes diverge across the 4 tables and casting is fragile). Per-table queries:
  1. `SentMessage.customer_id == X` ORDER BY `sent_at DESC NULLS LAST, created_at DESC` LIMIT `limit + 1`.
  2. `JobConfirmationResponse.customer_id == X` (NOT NULL FK per `models/job_confirmation.py:55`) ORDER BY `received_at DESC` LIMIT `limit + 1`.
  3. `CampaignResponse.customer_id == X OR (customer_id IS NULL AND from_phone == customer.phone)` (orphan fallback) ORDER BY `received_at DESC` LIMIT `limit + 1`.
  4. `Communication.customer_id == X` ORDER BY `created_at DESC` LIMIT `limit + 1`.
- After gather, **Python merge-sort** by timestamp (heap-merge from `heapq.merge` is the idiomatic Python tool for ordered streams). Yield up to `limit` items.
- Cursor pagination on composite `(timestamp, source_table, source_id)`; encode/decode as base64-JSON.
- **PERFORMANCE CONTRACT**: each per-table query is indexed (`SentMessage.customer_id` indexed by FK, `idx_confirmation_responses_appointment` covers the customer indirectly via JOIN — but `customer_id` itself is FK so PG creates an implicit index; verify with `EXPLAIN`. Same for `idx_communications_customer_id` and `campaign_responses.customer_id`). Target: **<150 ms p95** at 500 cumulative items per customer.
- **GOTCHA**: phone-number history — `customer.phone` may have changed; if so, the orphan fallback misses old inbound. Acceptable in v0; flag in code comment for v1.
- **GOTCHA**: ambiguous customer↔phone (two customers share a phone) — show the customer's own row matches first; do not include cross-customer rows.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/services/test_customer_conversation_service.py -v` and a Hypothesis property test on the merge invariant (timestamps strictly descending regardless of source-table order).

#### TASK-13.3 ADD `GET /api/v1/customers/{id}/conversation`

- **IMPLEMENT**: New route in `api/v1/customers.py`. Manager-or-Admin guard. Cursor + `limit` query params.
- **VALIDATE**: `curl http://localhost:8000/api/v1/customers/<uuid>/conversation`

#### TASK-13.4 FRONTEND `useCustomerConversation` (infinite query)

- **IMPLEMENT**: `useInfiniteQuery` with cursor pagination. Key: `customerKeys.conversation(id, params)`. 60 s `refetchInterval` parity.
- **VALIDATE**: `npm test -- useCustomerConversation`

#### TASK-13.5 REFACTOR `CustomerMessages.tsx` to paired view

- **IMPLEMENT**: Replace flat-list render with paired in/out chronological list. Outbound right-aligned, inbound left-aligned. Keep `OptOutBadge` header. Add channel filter (sms/email/all).
- **GOTCHA**: keep existing `data-testid="customer-messages"` and per-message `data-testid={\`message-${msg.id}\`}` for backward-compat with existing tests.
- **VALIDATE**: `npm test -- CustomerMessages` and agent-browser walkthrough on a customer with R-then-free-text history.

### Tier B · WP-16 (Unified Inbox v0)

#### TASK-16.1 ADD inbox schemas

- **IMPLEMENT**: `schemas/inbox.py` with `InboxItem`, `InboxFilters`, `InboxListResponse(items, next_cursor)`.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/inbox.py`

#### TASK-16.2 IMPLEMENT `InboxService.list_events`

- **IMPLEMENT**: Same parallel-`gather` + `heapq.merge` pattern as WP-13, but **without** the `customer_id == X` filter — cross-customer. Apply the `triage` filter inside each per-table query (push down `WHERE status IN ('needs_review', 'orphan')` so we don't pull a million rows then filter in Python). Compute `triage_status` server-side:
  - `pending` if source row's `status in ('needs_review', 'orphan')` OR linked to an unacknowledged `Alert(type IN ('PENDING_RESCHEDULE_REQUEST', 'INFORMAL_OPT_OUT', 'UNRECOGNIZED_CONFIRMATION_REPLY', 'ORPHAN_INBOUND'))`.
  - `handled` if source row links to a resolved `RescheduleRequest` or to an acknowledged `Alert`.
  - `dismissed` reserved for v1 (manual archive).
- **PERFORMANCE CONTRACT**: at 30-day window with ~1k inbound rows total, target <250 ms p95. Add a composite index `(status, received_at DESC)` on `job_confirmation_response` and `campaign_responses` if `EXPLAIN ANALYZE` shows seq-scans. Defer the index to a follow-up migration if not needed.
- **VALIDATE**: `uv run pytest -v -k InboxService` and load-test with `locust` or a simple `for _ in range(100): curl ... ; done` timing check.

#### TASK-16.3 ADD `GET /api/v1/inbox`

- **IMPLEMENT**: New `api/v1/inbox.py` mirroring the `_endpoints` pattern from `api/v1/alerts.py:32-38`. Register the router in **`src/grins_platform/api/v1/router.py`** (NOT `__init__.py` — that file only contains a docstring): add `from grins_platform.api.v1.inbox import router as inbox_router` near line 19 (alphabetically next to `invoices_router` at line 42), and `api_router.include_router(inbox_router)` in the same place the other routers are included (search for `api_router.include_router(alerts_router)` to confirm the exact pattern).
- **VALIDATE**: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/inbox?triage=pending`

#### TASK-16.4 BUILD `useInbox` hook

- **IMPLEMENT**: New `frontend/src/features/schedule/hooks/useInbox.ts`. TanStack Query with key `['schedule', 'inbox', filters]`, 60 s `refetchInterval` parity, `useInfiniteQuery` for cursor pagination.
- **PATTERN**: existing `useNoReplyReview` / `useRescheduleRequests` hooks in the same `features/schedule/hooks/` directory.
- **VALIDATE**: `npm test -- useInbox`

#### TASK-16.5 BUILD `InboxQueue.tsx` component

- **IMPLEMENT**: Mirror the chrome of `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` (1–336) and `RescheduleRequestsQueue.tsx`:
  - Card container, title (e.g. "Inbound Triage" with `Inbox` icon from lucide-react), last-updated text + refresh button (reuse the same `dataUpdatedAt` / `RefreshCw` pattern visible at `CustomerMessages.tsx:42-66`).
  - Filter pills bar: 6 pills (All / Needs triage / Orphans / Unrecognized / Opt-outs / Archived), active state via `cn()` Tailwind classes. Counts in the labels.
  - Row list: each row shows sender + phone, 80-char snippet, status pill, source-table icon, timestamp. Clicking expands inline (`<details>` or controlled-expand state).
  - Expanded view: full body, action buttons ("Open appointment" if linked, "Open customer" if linked, "Archive" disabled).
  - Empty state: same pattern as `messages-empty` in `CustomerMessages.tsx:84-89` ("No inbound messages awaiting review").
  - Error state: red text, mirrors `messages-error` pattern.
  - data-testids: `inbox-queue`, `inbox-queue-empty`, `inbox-queue-error`, `inbox-row-${id}`, `inbox-row-expand-${id}`, `open-appointment-btn-${id}`, `open-customer-btn-${id}`, `inbox-filter-${name}`, `refresh-inbox-btn`, `load-more-inbox-btn`.
  - Wrap card in `<section id="inbox-queue">` for anchor deep-link.
- **GOTCHA**: do NOT create a new VSA slice. The component lives inside the existing `features/schedule/` slice.
- **VALIDATE**: `npm test -- InboxQueue` and agent-browser walkthrough on `/schedule`.

#### TASK-16.6 MOUNT in `SchedulePage.tsx`

- **IMPLEMENT**: In `frontend/src/features/schedule/components/SchedulePage.tsx`, add `import { InboxQueue } from './InboxQueue';` near the existing imports at lines 37–40, then render `<InboxQueue />` immediately after `<RecentlyClearedSection ... />` at line 517.
- **GOTCHA**: no other layout, route, or nav changes — confirm via `git diff` that the change is additive.
- **VALIDATE**: `agent-browser open http://localhost:5173/schedule && agent-browser scroll down 2000 && agent-browser is visible "[data-testid='inbox-queue']"`

### Tier C · WP-10 (Day-2 Reminder)

#### TASK-10.1 MIGRATION `appointment_reminder_log`

- **IMPLEMENT**: New alembic revision `{YYYYMMDD}_create_appointment_reminder_log.py` mirroring `20260416_100100_create_alerts_table.py` structure. Columns + indexes per Phase 3.
- **GOTCHA**: down-revision must be the latest existing migration (currently `20260428_100000_add_customer_email_bounced_at`).
- **VALIDATE**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`

#### TASK-10.2 ADD model + repository

- **IMPLEMENT**: `models/appointment_reminder_log.py`, `repositories/appointment_reminder_log_repository.py` with `create`, `get_latest_for(appointment_id, stage)`, `count_for_appointment(appointment_id)`.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/repositories/test_appointment_reminder_log_repository.py -v`

#### TASK-10.3 SEED `BusinessSetting` rows

- **IMPLEMENT**: Either via a migration data step (mirroring `20260416_100300_seed_business_settings_h12.py`) or via `BusinessSettingService` defaults. Recommend migration for prod safety.
- **VALIDATE**: `uv run alembic upgrade head` then verify rows exist.

#### TASK-10.4 IMPLEMENT `Day2ReminderJob`

- **IMPLEMENT**: New `Day2ReminderJob(LoggerMixin)` class in `services/background_jobs.py` mirroring `NoReplyConfirmationFlagger`. Hourly tick. Eligible-set query as in Phase 3 task 50. Skip on opt-out. Insert reminder-log row + audit row + emit alert if desired.
- **GOTCHA**: time-window respect — outbound SMS is already gated by quiet-hours upstream; do NOT re-implement, but do guard against sending at, e.g., 7:55 AM if the next-tick send would land at 8:00.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_day_2_reminder.py -v`

#### TASK-10.5 REGISTER scheduler tick

- **IMPLEMENT**: In `scheduler.py`, register `send_day_2_reminders_job` at 1 h interval.
- **GOTCHA**: gate on `confirmation_day_2_reminder_enabled=true` so prod can opt-in deliberately.
- **VALIDATE**: start the app locally and watch logs for `scheduler.day_2_reminder.tick_started`.

---

## TESTING STRATEGY

### Unit Tests

Per `code-standards.md` §2 — `tests/unit/`, `@pytest.mark.unit`, all dependencies mocked. Mirror existing test naming `test_{method}_with_{condition}_returns_{expected}`.

Required new unit-test files:
- `tests/unit/services/test_audit_service.py` — extend with new audit-action assertions.
- `tests/unit/services/test_job_confirmation_service_audit.py` — exercise the new audit helpers.
- `tests/unit/services/test_customer_conversation_service.py` — UNION + sort invariants.
- `tests/unit/services/test_inbox_service.py` — cross-customer UNION + triage classification.
- `tests/unit/services/test_day_2_reminder_job.py` — eligibility filter + dedup.
- `tests/unit/repositories/test_alert_repository.py` — extend for new methods.
- `tests/unit/api/test_alerts_api.py` — new query params, counts endpoint, ack endpoint.

### Functional Tests

`tests/functional/`, `@pytest.mark.functional`, real DB. Naming: `test_{workflow}_as_user_would_experience`.

Required:
- `test_customer_y_reply_creates_audit_row`
- `test_customer_r_reply_creates_alert_and_audit`
- `test_admin_drag_drop_creates_audit_row`
- `test_alerts_counts_returns_per_type_dict`
- `test_acknowledged_alerts_filterable_by_date`
- `test_weekly_schedule_includes_reply_state`
- `test_customer_conversation_returns_paired_history`
- `test_inbox_unifies_four_inbound_sources`
- `test_day_2_reminder_sends_once_per_appointment`

### Integration Tests

`tests/integration/`, `@pytest.mark.integration`, full system.

Required cross-component flows:
- `test_y_then_r_full_lifecycle_with_audit_and_alerts` — confirm, then reschedule, verify audit rows, alerts created and auto-acked when admin resolves.
- `test_calendar_badge_reflects_reply_state` — POST a reschedule, then GET /weekly and assert `reply_state.has_pending_reschedule=true`.
- `test_inbox_orphan_appears_after_unknown_inbound` — fire a webhook from an unknown number, verify orphan row + alert + inbox visibility.
- `test_day_2_reminder_skipped_for_opted_out_customer`.

### Property-Based Tests (Hypothesis)

- `test_reply_state_deterministic_under_combinations` — given a tuple of (open_reschedule, no_reply_flag, opted_out, unrecognized) booleans, the computed `ReplyState` is deterministic and matches expected pill-priority order.
- `test_inbox_merge_strictly_ordered_by_timestamp` — generate random timestamps across the 4 source tables, assert the merged stream is monotonically descending.

### Edge Cases

- Repeat Y after C (already-cancelled) → no audit, no alert (silent).
- Repeat R after R → 1 audit row for the second event, 0 new alerts (deduped by Gap 01.A).
- Admin clicks "Mark Contacted" then customer replies Y → both audit rows, no alert state inconsistency.
- Customer phone changes mid-conversation → conversation view falls back to `customer_id` linkage.
- Day-2 reminder fires the second the customer replies → race: re-check status before send.
- Calendar with 200 appointments in a month view (mobile) → badges aggregate to single `⚠ N` pill.
- Inbox query with no triage filter — full unioned dataset paginates correctly.

### Coverage Targets

Per `frontend-testing.md` and `spec-quality-gates.md`:

| Layer | Target |
|---|---|
| Backend services (new) | 90% |
| Backend repositories (extended) | 90% |
| Backend API routes | 85% |
| Frontend components | 80% |
| Frontend hooks | 85% |
| Frontend utils | 90% |

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend
uv run ruff check --fix src/grins_platform/
uv run ruff format src/grins_platform/

# Frontend
cd frontend && npm run lint && npm run format:check
```

### Level 2: Type Safety

```bash
# Backend (BOTH must pass with zero errors per .kiro/steering/code-standards.md)
uv run mypy src/grins_platform/
uv run pyright src/grins_platform/

# Frontend
cd frontend && npm run typecheck
```

### Level 3: Unit Tests

```bash
uv run pytest -m unit -v
cd frontend && npm test
```

### Level 4: Functional + Integration Tests

```bash
uv run pytest -m functional -v
uv run pytest -m integration -v
uv run pytest --cov=src/grins_platform --cov-report=term-missing
cd frontend && npm run test:coverage
```

### Level 5: Manual Validation (per WP)

#### WP-05 Audit
```bash
# Send a confirmation, then reply Y, R, STOP, free-text, and 'please stop'.
# Verify each emits an audit row with correct actor_type:
psql "$DATABASE_URL" -c "SELECT action, details->>'actor_type' AS at, created_at FROM audit_log ORDER BY created_at DESC LIMIT 20;"
```

#### WP-14 Alerts
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/alerts/counts
curl -H "Authorization: Bearer $TOKEN" 'http://localhost:8000/api/v1/alerts?alert_type=pending_reschedule_request&alert_type=informal_opt_out'
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/alerts/$ALERT_ID/acknowledge
```

agent-browser dashboard walkthrough:
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='pending-reschedule-alert-card']"
agent-browser click "[data-testid='pending-reschedule-alert-card']"
agent-browser wait --url "**/schedule**"
agent-browser screenshot dashboard-alert-flow.png
```

#### WP-12 Calendar badges
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait "[data-testid='calendar-view']"
agent-browser is visible "[data-testid^='pending-reschedule-badge-']"
agent-browser screenshot calendar-badges.png
agent-browser set viewport 375 812
agent-browser screenshot calendar-badges-mobile.png
```

#### WP-13 Conversation
```bash
agent-browser open "http://localhost:5173/customers/$CUSTOMER_ID"
agent-browser click "[role='tab'][value='messages']"
agent-browser wait "[data-testid='customer-messages']"
agent-browser screenshot customer-conversation.png
```

#### WP-16 Inbox (Schedule-tab queue card)
```bash
agent-browser open http://localhost:5173/schedule#inbox-queue
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='inbox-queue']"
agent-browser screenshot inbox-queue-card.png
# Click filter pill
agent-browser click "[data-testid='inbox-filter-orphans']"
agent-browser wait --load networkidle
# Expand a row
agent-browser click "[data-testid^='inbox-row-']"
agent-browser is visible "[data-testid^='open-customer-btn-']"
```

#### WP-10 Reminder
```bash
# Run the job manually for a test appointment >48h old with no reply:
uv run python -c "import asyncio; from grins_platform.services.background_jobs import _day_2_reminder_job; asyncio.run(_day_2_reminder_job.run())"
psql "$DATABASE_URL" -c "SELECT * FROM appointment_reminder_log ORDER BY sent_at DESC LIMIT 5;"
```

---

## ACCEPTANCE CRITERIA

- [ ] **WP-05**: All Y/R/C/STOP/informal-STOP customer events, manual reminder sends, "Mark Contacted", and admin drag-drop reschedules produce an `AuditLog` row with `details.actor_type ∈ {'customer','staff','system'}`.
- [ ] **WP-14**: `GET /api/v1/alerts/counts` returns counts for ≥9 alert types; dashboard surfaces 5 distinct AlertCards (informal opt-out + 4 new); each new alert auto-acknowledges when underlying state resolves.
- [ ] **WP-12**: Weekly-schedule API returns `reply_state` block; calendar cards visibly badge each of (pending-reschedule, no-reply, opted-out, unrecognized-reply); badge data-testids follow project convention; mobile aggregates to single `⚠ N` pill.
- [ ] **WP-13**: `GET /api/v1/customers/{id}/conversation` returns paired in/out chronological items across 4 sources; `CustomerMessages.tsx` renders chat-app-style paired view; existing tests still pass.
- [ ] **WP-16**: `InboxQueue` card renders at the bottom of `/schedule` immediately after `RecentlyClearedSection`; orphan and unrecognized-reply rows are visible (previously invisible); filter pills work; row expansion shows full body and Open-appointment / Open-customer actions; cursor pagination works at >100 items; `/schedule#inbox-queue` deep-link from dashboard alert cards scrolls to the section.
- [ ] **WP-10**: Day-2 reminder fires exactly once per eligible appointment when feature flag enabled; respects opt-out; respects quiet-hours; produces an `appointment_reminder_log` row + audit row.
- [ ] All validation commands pass with **zero errors / zero violations**.
- [ ] Coverage targets met (90% backend services, 80% FE components, 85% FE hooks).
- [ ] DEVLOG.md updated per WP per `auto-devlog.md` rules.
- [ ] No regressions in existing severity-1/2 work (gaps 01, 03, 04, 06, 07, 11, 15).
- [ ] No new high-severity findings from `/security-review` skill.

---

## COMPLETION CHECKLIST

- [ ] Tier A WPs shipped to `dev` branch in order WP-05 → WP-14 → WP-12.
- [ ] Tier B WPs shipped after Tier A passes E2E validation: WP-13 → WP-16.
- [ ] Tier C (WP-10) shipped after Tier A+B; feature flag default `false` on prod.
- [ ] Each WP closes with a single PR + DEVLOG entry referencing the relevant gap doc(s).
- [ ] All validation commands executed successfully on each WP merge.
- [ ] Manual testing confirms each WP via agent-browser walkthroughs above.
- [ ] Acceptance criteria all met.
- [ ] `.kiro/specs/scheduling-gaps-severity-3/tasks.md` (if Kiro spec is desired) reflects per-WP completion — OPTIONAL; the existing gap docs remain authoritative.
- [ ] README at `feature-developments/scheduling gaps/README.md` updated to mark gaps 05, 10, 12, 13, 14, 16 as ✅ DONE with the corresponding plan/commit references.

---

## NOTES

### Why this ordering vs. shipping all six in parallel

The README's Tier A ordering (12 → 14 → 05) is optimized for **fastest user-visible value**. This plan **inverts to 05 → 14 → 12** because:
- Gap 14 alert-creation hooks live inside the same services that need new audit rows (Gap 05). Doing 05 first lets us land both behavioral changes per service in one PR (cheaper review, fewer rebases).
- Gap 12 reads from data Gap 14 already exposes. Building the badges before the alert types exist would mean computing reply_state from raw tables — duplicate logic.
- The user-visible payoff after WP-05 is small, but the WP-14 dashboard cards land in a single PR and immediately deliver the dispatcher-facing value the README promises for Tier A.

### Why we extend `details` JSONB instead of adding `actor_type` column to `audit_log`

- Backwards compatibility with existing rows.
- Avoids a migration on a hot table.
- `details` is already JSONB and indexed via GIN-able expressions if we ever need fast `actor_type` filtering.
- Project precedent: `_record_customer_sms_cancel_audit` already stores `source` in `details`. We extend the same shape.

### Why WP-10 is Phase 3

The README explicitly says "defer until manual surfaces (12/13/14) prove the policy." Sending a second automated SMS to every silent customer changes the system's voice; we want WP-12/14 dashboards in admins' hands first so they can sanity-check who's actually being escalated against. Phase-1 ships the engine; Phase-2 (config UI) and Phase-3 (per-customer tailoring) wait until we observe day-2-reminder outcomes for ~2 weeks.

### Why WP-16 deviates from gap-16's three-pane Gmail layout

Gap-16's spec proposes a dedicated `/inbox` route with a three-pane Gmail-like layout. After product review (2026-04-26), this plan deliberately deviates:

- **Volume doesn't justify a new screen.** Twin Cities, dozens of confirmations/day, single-digit orphans/day. A three-pane layout assumes inbox-as-primary-workflow; here it's inbox-as-exception-triage.
- **Operational co-location.** Admins already triage `RescheduleRequestsQueue` and `NoReplyReviewQueue` at the bottom of `/schedule`. Orphan/unrecognized inbounds are the same mental bucket — "things customers said that need my attention." Stacking a fourth queue card matches the existing workflow.
- **Lower scope risk.** No new route, no new top-nav entry, no new VSA slice, no three-pane responsive design. Cuts WP-16 frontend scope by ~50%.
- **Reversible.** If volume grows past the queue card's ergonomics, graduating to a dedicated `/inbox` route is a future migration that can reuse this plan's backend service unchanged.

The backend (`GET /api/v1/inbox`, `InboxService.list_events`, schemas) is unchanged from the gap-16 spec.

### Out of scope (deferred to other gaps)

- `MMS_RECEIVED` alert (Gap 09).
- `STALE_THREAD_REPLY` alert (Gap 03.B follow-on).
- `WEBHOOK_FAILURE` alert (Gap 07 follow-on; some signals already added by Gap 07).
- Inbox v1+ (triage actions, reply composer, threading, realtime).
- Graduating the inbox queue card to a dedicated `/inbox` route (deferred to a future scope if volume warrants).
- Conversation Phase 2 (reply composer, template picker).
- Day-3+ reminder cadence, voice escalation, day-before / morning-of templates (Gap 10 Phase 2).
- Generic `/alerts` index page with type/severity filters (Gap 14 Phase 2).
- Per-customer reminder tailoring (Gap 10 Phase 3).

### Confidence Score

**10/10** for one-pass implementation success.

All previously-flagged blockers are resolved (verified 2026-04-26):

1. **Send Reminder SMS endpoint** — `POST /api/v1/appointments/{id}/send-reminder-sms` at `api/v1/appointments.py:736-781`. Audit hook site identified (after line 763, before line 777). Existing functional test at `tests/functional/test_no_reply_review_functional.py:172` extends naturally.
2. **Mark Contacted endpoint** — `POST /api/v1/appointments/{id}/mark-contacted` at `api/v1/appointments.py:681-727`. Audit hook site identified (capture `prior_reason` before line 717, write audit row after line 718 flush). Existing functional test at `tests/functional/test_no_reply_review_functional.py:250` extends naturally.
3. **Admin drag-drop reschedule (Gap 05.F)** — VERIFIED already audited via `_record_update_audit` (`appointment_service.py:570-616`, action `appointment.update`) and `_record_reactivate_audit` (`appointment_service.py:618-660`, action `appointment.reactivate`). Remaining work narrowed to enriching the existing `details` dicts with `actor_type`/`source`/`is_reschedule` — no new audit row, no risk of duplicates.
4. **UNION approach for WP-13/16** — explicit decision: 4 parallel per-table `select` queries via `asyncio.gather` + Python `heapq.merge` (NOT SQL UNION ALL). Rationale: column shapes diverge across the 4 tables; SQL casting fragile; per-table queries hit existing FK indexes. Performance contracts written: <150 ms p95 for WP-13 customer view at 500 items, <250 ms p95 for WP-16 cross-customer at 1k inbound/30-day window.
5. **Customer ID linkage** — VERIFIED `JobConfirmationResponse.customer_id` (NOT NULL FK), `RescheduleRequest.customer_id` (NOT NULL FK), `Communication.customer_id` (NOT NULL FK), `CampaignResponse.customer_id` (nullable; orphan fallback via `from_phone == customer.phone`). No new schema migrations required for WP-13/16.
6. **Reply-state injection point for WP-12** — VERIFIED `_enrich_appointment_response(appointment: object)` at `api/v1/appointments.py:132-136` is the single injection point used by all three relevant endpoints. New signature `(appointment, reply_state=None)` is backwards-compatible at the 3 call sites (`:270`, `:325`, `:369`).
7. **Router registration** — VERIFIED location at `api/v1/router.py:19-77` (NOT `api/v1/__init__.py`). The new inbox router slots in alphabetically next to `invoices_router` at line 42.
8. **OptOutBadge** — VERIFIED at `frontend/src/shared/components/OptOutBadge.tsx`, exported from `shared/components/index.ts`. Reusable in WP-12 calendar badges and WP-13 conversation header.
9. **`AppointmentResponse` schema extension** — VERIFIED at `schemas/appointment.py:66-97`. Add `reply_state: ReplyState | None = None` field; Pydantic 2 `from_attributes=True` auto-populates it (or pass via the enricher when not derivable from the ORM).
10. **`_handle_needs_review` emit site for `UNRECOGNIZED_CONFIRMATION_REPLY`** — VERIFIED at `services/job_confirmation_service.py:883`; the else-branch (no open RescheduleRequest) is the precise emit site.

Every task carries: file path, line number, executable validation command, and a clearly-named pattern reference. The plan can be executed top-to-bottom by an implementation agent with no additional research required.
