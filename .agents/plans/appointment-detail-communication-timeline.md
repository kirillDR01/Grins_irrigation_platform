# Feature: AppointmentDetail Communication Timeline (Gap 11)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files, etc.

---

## Feature Description

`AppointmentDetail.tsx` is the modal/side-panel admins open when clicking an appointment on the calendar. Today it is **inbound-blind**: it shows only field-work state (status, scheduled time, staff, notes, en_route/arrived/completed timeline). It hides all customer-facing events — Y/R/C replies, open `RescheduleRequest`s, no-reply escalation, SMS opt-out, outbound SMS history.

Admins must leave the modal and stitch together `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `CustomerDetail → Messages`, calendar-card visual cues, or raw DB queries to understand a single appointment. This feature adds a **"Communication" section** to `AppointmentDetail.tsx` that surfaces this data inline via a new consolidated `GET /appointments/{id}/timeline` endpoint.

This plan closes Gap 11 in isolation — it does **not** depend on Gap 5's full audit-coverage work. The `/timeline` endpoint aggregates what already exists (`JobConfirmationResponse`, `RescheduleRequest`, `SentMessage`, `SmsConsentRecord`). Gap 5 can later extend the same endpoint with audit-log events without the frontend shape changing.

## User Story

As a **dispatch admin**
I want to **see all customer replies, pending reschedule requests, no-reply flags, opt-out state, and outbound SMS history inline in the appointment detail panel**
So that **I can understand the full communication state of an appointment without leaving the calendar or stitching together separate queues**.

## Problem Statement

Concrete reproduction (copied from gap doc):

1. Customer replies "R" then follows up with "Tuesday at 3 or Wednesday morning works."
2. Admin opens calendar, clicks the appointment → `AppointmentDetail` modal opens.
3. Modal shows: "Scheduled, Tuesday 10:00-12:00, customer Jane Doe" and an empty field-work timeline.
4. **No indication** a `RescheduleRequest` is open.
5. **No indication** the customer sent free-text alternatives.
6. Admin must close modal, navigate to `RescheduleRequestsQueue`, find the row — 3 extra clicks + context switch.

Same story applies to no-reply escalation (`needs_review_reason`) and STOP-based opt-outs (`SmsConsentRecord`).

## Solution Statement

1. **Backend:** Create a new `AppointmentTimelineService` that assembles a chronologically-sorted list of `TimelineEvent`s for a given `appointment_id` from four existing sources: outbound `SentMessage`, inbound `JobConfirmationResponse`, `RescheduleRequest` state, and the customer's current `SmsConsentRecord`. Expose it via `GET /api/v1/appointments/{appointment_id}/timeline`.
2. **Frontend:** Add a new `useAppointmentTimeline(id)` React Query hook and a new `AppointmentCommunicationTimeline` component. Inject the component into `AppointmentDetail.tsx` between the metadata block and the notes section, collapsed by default. When a reschedule request is open or a no-reply flag is set, render a banner at the top of the modal with quick-action buttons that reuse the existing `RescheduleRequestsQueue` / `NoReplyReviewQueue` mutation hooks.
3. **Out of scope for this plan (tracked in Gap 5 / Gap 13 / Gap 16):** Audit-log-based status transitions, admin edits, "mark contacted" system events. The timeline shape is designed so these can be added later as additional event kinds without breaking the frontend.

## Feature Metadata

**Feature Type**: Enhancement (surface existing data in a new location — no new data model, no new business logic)
**Estimated Complexity**: Medium
- Low risk on backend: pure read-only aggregation of existing rows.
- Medium risk on frontend: mutates a central, heavily-used component (`AppointmentDetail.tsx`) with existing tests.
**Primary Systems Affected**:
- Backend: `api/v1/appointments.py`, new `services/appointment_timeline_service.py`, new `schemas/appointment_timeline.py`, `repositories/sent_message_repository.py` (+1 helper), `repositories/sms_consent_repository.py` (+1 helper), new queries on `JobConfirmationResponse` / `RescheduleRequest`.
- Frontend: `features/schedule/api/appointmentApi.ts`, `features/schedule/hooks/useAppointments.ts`, new hook file, new component file, `features/schedule/components/AppointmentDetail.tsx` (integration point).
**Dependencies**: None. All models and services already exist.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING

**Backend — data models (read to understand fields and relationships):**
- `src/grins_platform/models/job_confirmation.py:27-100` — `JobConfirmationResponse` (inbound replies). Fields: `id`, `job_id`, `appointment_id`, `sent_message_id`, `customer_id`, `from_phone`, `reply_keyword`, `raw_reply_body`, `status`, `received_at`, `processed_at`. Indexed: `idx_confirmation_responses_appointment`.
- `src/grins_platform/models/job_confirmation.py:103-172` — `RescheduleRequest`. Fields: `id`, `job_id`, `appointment_id`, `customer_id`, `original_reply_id`, `requested_alternatives` (JSON), `raw_alternatives_text`, `status`, `created_at`, `resolved_at`. Indexed: `idx_reschedule_requests_appointment`.
- `src/grins_platform/models/sent_message.py:21-168` — `SentMessage`. Key fields: `id`, `appointment_id`, `customer_id`, `message_type` (enum incl. `appointment_confirmation`, `appointment_reschedule`, `appointment_reminder`, `on_the_way`, `arrival`, `completion`, `appointment_confirmation_reply`, `reschedule_followup`), `message_content`, `recipient_phone`, `delivery_status`, `sent_at`, `created_at`, `superseded_at`. Relationships loaded `lazy="selectin"`.
- `src/grins_platform/models/sms_consent_record.py:50-116` — `SmsConsentRecord`. INSERT-ONLY table. Fields: `customer_id`, `phone_number`, `consent_given` (bool), `consent_timestamp`, `opt_out_timestamp`, `consent_method`, `opt_out_method`, `consent_type`. Most recent row per customer wins.
- `src/grins_platform/models/appointment.py` — read to confirm `needs_review_reason` field exists, `rescheduled_from_id` field, and the relationship back to `Customer`.

**Backend — existing patterns to mirror (all file:line confirmed):**
- `src/grins_platform/api/v1/appointments.py:35-39` — dependency imports (`get_appointment_service`, `get_db_session`, `get_full_appointment_service`).
- `src/grins_platform/api/v1/appointments.py:94` — `_endpoints = AppointmentEndpoints()` — this is NOT a plain logger; it's a class instance with `log_started` / `log_completed` / `log_rejected` methods inherited from `LoggerMixin`. Use it as-is.
- `src/grins_platform/api/v1/appointments.py:777-803` — `get_appointment` endpoint — exact shape to mirror. Note the `AppointmentNotFoundError → HTTPException(404)` pattern.
- `src/grins_platform/api/v1/dependencies.py:181-202` — `get_appointment_service` dependency shape:
  ```python
  async def get_appointment_service(
      session: Annotated[AsyncSession, Depends(get_db_session)],
  ) -> AppointmentService:
      appointment_repository = AppointmentRepository(session=session)
      job_repository = JobRepository(session=session)
      staff_repository = StaffRepository(session=session)
      return AppointmentService(
          appointment_repository=appointment_repository,
          job_repository=job_repository,
          staff_repository=staff_repository,
      )
  ```
  **No `get_job_confirmation_service` exists** in this file — confirmed. `JobConfirmationService` takes a single `db: AsyncSession` arg (see below) so we instantiate it inline in the new dep provider rather than adding a new provider function.
- `src/grins_platform/services/job_confirmation_service.py:110-112` — `JobConfirmationService.__init__`:
  ```python
  def __init__(self, db: AsyncSession) -> None:
      super().__init__()
      self.db = db
  ```
- `src/grins_platform/services/sms_service.py:832` — existing construction pattern: `svc = JobConfirmationService(self.session)`. Mirror this.
- `src/grins_platform/repositories/appointment_repository.py:108-148` — `async def get_by_id(self, appointment_id: UUID, include_relationships: bool = False) -> Appointment | None`. Returns `None` on miss (does NOT raise).
- `src/grins_platform/repositories/sent_message_repository.py:220-252` — `get_by_customer_and_type()` query with `appointment_id` filter. Mirror this shape for the new `list_by_appointment()` repo method.
- `src/grins_platform/repositories/sms_consent_repository.py:26-89` — `SmsConsentRepository(LoggerMixin)`. **Only existing method is `get_opted_out_customer_ids`.** No `get_latest_for_customer` — we must add it (Task 4).
- `src/grins_platform/schemas/job_confirmation.py:15-70` — existing `ConfirmationResponseSchema` and `RescheduleRequestResponse` shapes. **Reuse directly** — do not duplicate fields.
- `src/grins_platform/schemas/sent_message.py:20-117` — `SentMessageResponse` with `_resolve_recipient_name` validator; reuse as the nested schema for outbound events.
- `src/grins_platform/exceptions/__init__.py:278-291` — `AppointmentNotFoundError` definition:
  ```python
  class AppointmentNotFoundError(FieldOperationsError):
      def __init__(self, appointment_id: UUID) -> None:
          self.appointment_id = appointment_id
          super().__init__(f"Appointment not found: {appointment_id}")
  ```
  **Import path**: `from grins_platform.exceptions import AppointmentNotFoundError`.
- `src/grins_platform/log_config.py:214-264` — `LoggerMixin` with `log_started(action, **kwargs)`, `log_completed(action, **kwargs)`, `log_rejected(action, reason, **kwargs)`. **Import path**: `from grins_platform.log_config import LoggerMixin`.

**Frontend — component and data patterns to mirror (all file:line confirmed):**
- `frontend/src/features/schedule/components/AppointmentDetail.tsx:1-586` — integration target. Line 34 import of `useAppointment`, lines 54-58 props, lines 180-209 header+status badge, lines 352-361 notes `<details>` (mirror for Communication section), lines 363-385 inline field-work timeline (same visual idiom).
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx:41-47, 182-212` — dialog state + `<Dialog>` + `<AppointmentForm>` pattern to reuse:
  ```tsx
  const [rescheduleTarget, setRescheduleTarget] = useState<RescheduleRequestDetail | null>(null);
  const { data: targetAppointment } = useAppointment(rescheduleTarget?.appointment_id);
  // ...
  <Dialog open={!!rescheduleTarget} onOpenChange={(open) => { if (!open) setRescheduleTarget(null); }}>
    <AppointmentForm appointment={targetAppointment} onSuccess={handleRescheduleSuccess} ... />
  </Dialog>
  ```
  `AppointmentDetail` will own its own instance of this state — do not try to share.
- `frontend/src/features/schedule/hooks/useRescheduleRequests.ts:21-30` — **exact hook name is `useResolveRescheduleRequest`** (NOT `useResolveReschedule`):
  ```ts
  export function useResolveRescheduleRequest() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: ({ id, notes }: { id: string; notes?: string }) => rescheduleApi.resolve(id, notes),
      onSuccess: () => { qc.invalidateQueries({ queryKey: rescheduleKeys.all }); },
    });
  }
  ```
- `frontend/src/features/schedule/hooks/useNoReplyReview.ts:40-52, 61-70` — two separate hooks exported: `useMarkContacted()` and `useSendReminder()`. Plus `useNoReplyReviewList` and `noReplyReviewKeys`.
- `frontend/src/features/schedule/hooks/useAppointments.ts:10-22` — **confirmed `appointmentKeys` factory**:
  ```ts
  export const appointmentKeys = {
    all: ['appointments'] as const,
    lists: () => [...appointmentKeys.all, 'list'] as const,
    list: (params?: AppointmentListParams) => [...appointmentKeys.lists(), params] as const,
    details: () => [...appointmentKeys.all, 'detail'] as const,
    detail: (id: string) => [...appointmentKeys.details(), id] as const,
    daily: (date: string) => [...appointmentKeys.all, 'daily', date] as const,
    staffDaily: (staffId: string, date: string) => [...appointmentKeys.all, 'staffDaily', staffId, date] as const,
    weekly: (startDate?: string, endDate?: string) => [...appointmentKeys.all, 'weekly', startDate, endDate] as const,
  };
  ```
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts:100-110` — **confirmed `onSuccess` invalidation pattern** in `useConfirmAppointment`:
  ```ts
  onSuccess: (_, id) => {
    queryClient.invalidateQueries({ queryKey: appointmentKeys.detail(id) });
    queryClient.invalidateQueries({ queryKey: appointmentKeys.lists() });
    queryClient.invalidateQueries({ queryKey: [...appointmentKeys.all, 'daily'] });
    queryClient.invalidateQueries({ queryKey: [...appointmentKeys.all, 'weekly'] });
  }
  ```
  Add one more line: `queryClient.invalidateQueries({ queryKey: appointmentKeys.timeline(id) });`.
- `frontend/src/features/schedule/api/appointmentApi.ts:29-52` — `appointmentApi` singleton. Add `getTimeline(id)` mirroring `getById`.
- `frontend/src/features/schedule/api/appointmentApi.test.ts:61-69` — **confirmed test mocking pattern**:
  ```ts
  vi.mocked(apiClient.get).mockResolvedValue({ data: mockAppointment });
  const result = await appointmentApi.getById('appt-123');
  expect(apiClient.get).toHaveBeenCalledWith('/appointments/appt-123');
  ```
- `frontend/src/features/schedule/types/index.ts:439-452` — **`RescheduleRequestDetail` type** (not `RescheduleRequestResponse` as the backend calls it) — the established frontend name. Use this throughout the new code.
- `frontend/src/core/providers/QueryProvider.tsx` — **test wrapper**: `import { QueryProvider } from '@/core/providers/QueryProvider'` (NOT from `@/shared/...`).
- `frontend/src/features/schedule/components/AppointmentDetail.tsx:1-20` — **confirmed UI import paths**:
  ```ts
  import { Badge } from '@/components/ui/badge';
  import { Button } from '@/components/ui/button';
  // ...
  import { cn } from '@/lib/utils';  // NOT '@/shared/utils'
  ```
  The `@/components/ui/*` path (not `@/shared/components/ui`) is the established convention — the steering doc is out of date here.
- `frontend/src/features/dashboard/components/RecentActivity.tsx:1-100+` — unified-timeline UI pattern.
- `frontend/src/features/schedule/components/AppointmentDetail.test.tsx` — existing test file to extend.

### New Files to Create

**Backend:**
- `src/grins_platform/schemas/appointment_timeline.py` — Pydantic response schemas (`TimelineEvent`, `AppointmentTimelineResponse`, enum `TimelineEventKind`).
- `src/grins_platform/services/appointment_timeline_service.py` — aggregation service.
- `src/grins_platform/tests/unit/test_appointment_timeline_service.py` — unit tests (all repositories mocked).
- `src/grins_platform/tests/functional/test_appointment_timeline_endpoint.py` — functional tests (real DB via existing fixtures).

**Frontend:**
- `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.tsx` — the collapsible Communication section.
- `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.test.tsx` — Vitest + RTL tests.
- `frontend/src/features/schedule/hooks/useAppointmentTimeline.ts` — React Query hook.

**Files modified (no new files):**
- Backend: `api/v1/appointments.py`, `repositories/sent_message_repository.py` (+ method), `repositories/sms_consent_repository.py` (+ method), `api/v1/dependencies.py` (+ service provider), `schemas/__init__.py` (if it re-exports).
- Frontend: `features/schedule/api/appointmentApi.ts`, `features/schedule/hooks/useAppointments.ts`, `features/schedule/components/AppointmentDetail.tsx`, `features/schedule/components/AppointmentDetail.test.tsx`, `features/schedule/hooks/index.ts` (barrel re-export), `features/schedule/components/index.ts` (barrel re-export).

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

**Project steering (mandatory reading, ignore kiro-CLI-specific sections):**
- `.kiro/steering/api-patterns.md` — FastAPI endpoint structure (set_request_id → try → finally with clear_request_id), DomainLogger.api_event() states (started/completed/failed), status-code conventions (200/201/204/400/404/500).
- `.kiro/steering/code-standards.md` — structlog pattern `{domain}.{component}.{action}_{state}`; services inherit `LoggerMixin` and use `self.log_started()` / `log_completed()` / `log_rejected()` / `log_failed()`; type hints on all functions; must pass `ruff check`, `ruff format`, `mypy`, `pyright`.
- `.kiro/steering/frontend-patterns.md` — VSA: features import only from `core/` and `shared/`; query-key factory; `cn()` utility; `data-testid` convention: pages `{feature}-page`, forms `{feature}-form`, buttons `{action}-{feature}-btn`, status `status-{value}`.
- `.kiro/steering/frontend-testing.md` — Vitest + RTL with `QueryProvider` wrapper; test loading/loaded/error states; coverage targets: components 80%+, hooks 85%+.
- `.kiro/steering/spec-testing-standards.md` — three-tier testing markers: `@pytest.mark.unit`, `@pytest.mark.functional`, `@pytest.mark.integration`.
- `.kiro/steering/structure.md` — file-layout conventions (`snake_case.py`, `PascalCase.tsx`, `use{Name}.ts`, `{feature}Api.ts`).

**External (read only if unfamiliar with the stack):**
- [Pydantic v2 ConfigDict(from_attributes=True)](https://docs.pydantic.dev/latest/concepts/models/#attributes-from-orm-objects) — ORM → schema conversion, used everywhere in `schemas/`.
- [SQLAlchemy 2.0 async `select` + `selectinload`](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html#selectin-eager-loading) — needed if we eager-load `Customer` from the consent query.
- [TanStack Query v5 `useQuery`](https://tanstack.com/query/latest/docs/framework/react/reference/useQuery) — `enabled: !!id` guard used in existing hooks.

### Patterns to Follow

**Naming conventions (enforced):**
- Backend files: `snake_case.py`; service classes: `{Domain}Service`; schemas: `{Thing}Response`.
- Frontend components: `PascalCase.tsx`; hooks: `use{Name}.ts`; API method on singleton: `camelCase` (`getTimeline`).
- Query keys: `appointmentKeys.timeline(id)` — add to the existing factory in `useAppointments.ts`.

**Error handling (from `appointments.py:783-803`):**
```python
try:
    result = await service.get_appointment_timeline(appointment_id)
except AppointmentNotFoundError as e:
    _endpoints.log_rejected("get_appointment_timeline", reason="not_found")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Appointment not found: {e.appointment_id}",
    ) from e
```

**Structured logging (LoggerMixin; see `sent_message_repository.py:227-232`):**
```python
self.log_started(
    "build_timeline",
    appointment_id=str(appointment_id),
)
# ... work ...
self.log_completed("build_timeline", event_count=len(events))
```
Never log PII (phone numbers, message bodies) at INFO. Debug-level only for those.

**Query-key factory extension (mirror `useAppointments.ts:10-22`):**
```ts
export const appointmentKeys = {
  all: ['appointments'] as const,
  // ...existing entries...
  timeline: (id: string) => [...appointmentKeys.all, 'timeline', id] as const,
};
```

**Mutation invalidation (from `useAppointmentMutations.ts`):** Any mutation that could change timeline state (confirm, cancel, mark-contacted, resolve-reschedule, send-reminder) must invalidate `appointmentKeys.timeline(id)` in its `onSuccess`.

**data-testid map (enforced by frontend-patterns.md):**
- Section container: `appointment-communication-timeline`
- Reschedule banner: `reschedule-banner-{appointmentId}`
- No-reply banner: `no-reply-banner-{appointmentId}`
- Opt-out badge: `opt-out-badge-{appointmentId}`
- Event row: `timeline-event-{eventId}`
- Expand/collapse toggle: `toggle-communication-timeline-btn`
- Resolve-reschedule button (in banner): `resolve-reschedule-{appointmentId}-btn`
- Send-reminder button (in banner): `send-reminder-{appointmentId}-btn`

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Backend schemas + repo helpers

Define the wire contract first so frontend and backend can develop against the same shape. Add thin repository helpers before touching the service.

**Tasks:**
- Create `schemas/appointment_timeline.py` with `TimelineEventKind` enum + `TimelineEvent` + `AppointmentTimelineResponse`.
- Add `SentMessageRepository.list_by_appointment(appointment_id)` that returns all rows for the appointment, ordered by `sent_at` / `created_at` descending.
- Add `SmsConsentRepository.get_latest_for_customer(customer_id)` (if missing) returning the most recent record.
- Add `JobConfirmationResponseRepository.list_by_appointment(appointment_id)` — if a repository doesn't exist for this model yet, add the query to `job_confirmation_service.py` as a private helper instead of creating new infra.
- Add `RescheduleRequestRepository.list_by_appointment(appointment_id)` — same note as above.

### Phase 2: Core Implementation — AppointmentTimelineService + endpoint

**Tasks:**
- Create `services/appointment_timeline_service.py` (`AppointmentTimelineService`) with `get_timeline(appointment_id: UUID) -> AppointmentTimelineResponse`. The service:
  1. Verifies the appointment exists (delegate to existing `AppointmentService.get_appointment`, or query repo directly — raise `AppointmentNotFoundError` on miss).
  2. Loads the four source lists in parallel (or sequentially — this endpoint is not latency-sensitive yet).
  3. Maps each row to a `TimelineEvent` via small private helper methods (`_outbound_to_event`, `_inbound_to_event`, `_reschedule_to_event`).
  4. Merges + sorts by `occurred_at` descending.
  5. Computes top-level flags: `pending_reschedule_request` (first open `RescheduleRequest`), `needs_review_reason` (copy from appointment), `opt_out` (derived from latest `SmsConsentRecord` where `consent_given=False`).
  6. Returns the combined `AppointmentTimelineResponse`.
- Register the service in `api/v1/dependencies.py` via `get_appointment_timeline_service`.
- Add `GET /api/v1/appointments/{appointment_id}/timeline` endpoint in `api/v1/appointments.py`, placed after `GET /{appointment_id}` (~line 804) to keep related routes together. Follow the exact shape of `get_appointment` at lines 777-803.

### Phase 3: Frontend Integration

**Tasks:**
- Add a TypeScript type for `AppointmentTimelineResponse` in `features/schedule/types/` (or inline-export from `types/index.ts` if that's the house pattern — check existing types before deciding).
- Add `appointmentApi.getTimeline(id: string)` to `features/schedule/api/appointmentApi.ts` returning the typed response.
- Extend the `appointmentKeys` factory with `timeline(id)` and add `useAppointmentTimeline(id)` hook in `features/schedule/hooks/useAppointmentTimeline.ts` mirroring `useAppointment`. Re-export from `hooks/index.ts`.
- Create `AppointmentCommunicationTimeline.tsx` component:
  - Top-level: `<details>` collapsible (matches existing notes section idiom in `AppointmentDetail.tsx:352-361`).
  - Summary row: "Communication — Last reply {relative time}" or "No customer replies yet".
  - Body: the chronological event list rendered with icons (📤 outbound, 📥 inbound, ⚠ reschedule-open, 📛 opt-out).
  - Keep pure — take `data: AppointmentTimelineResponse` as a prop; the parent `AppointmentDetail` owns the fetching hook.
- Update `AppointmentDetail.tsx`:
  - Import the new hook + component.
  - Call `useAppointmentTimeline(appointmentId)` alongside `useAppointment`.
  - Render three new pieces:
    1. **Reschedule banner** at the top of the modal (between header and content, ~line 210), only when `timeline.pending_reschedule_request` is set. Reuses `useResolveReschedule` from `hooks/useRescheduleRequests.ts` for the "Resolve & reschedule" action (opens existing `AppointmentForm` dialog).
    2. **No-reply banner** (same spot, stacked), only when `needs_review_reason === 'no_confirmation_response'`. Reuses `useNoReplyReview` mutation hooks for "Send reminder" / "Mark contacted".
    3. **Communication timeline** component, inserted between the current notes section (ends ~line 361) and the field-work timeline (~line 363). Collapsed by default.
  - **Opt-out badge** goes into the existing header (near status badge at lines 200-210) when `timeline.opt_out.consent_given === false`.
- Invalidate `appointmentKeys.timeline(id)` from existing mutations that change communication state: `useConfirmAppointment`, `useCancelAppointment`, `useNoReplyReview` (mark-contacted, send-reminder), `useResolveReschedule`.

### Phase 4: Testing & Validation

**Tasks:**
- Backend unit tests (`@pytest.mark.unit`) with all repositories mocked.
- Backend functional tests (`@pytest.mark.functional`) hitting the real endpoint with DB fixtures.
- Frontend component tests for `AppointmentCommunicationTimeline` (renders, collapses, handles empty state).
- Frontend hook test for `useAppointmentTimeline`.
- Frontend integration test: `AppointmentDetail.test.tsx` extended to assert banners appear when timeline data includes reschedule / no-reply / opt-out flags.
- Run full validation gate: `ruff`, `mypy`, `pyright`, backend `pytest`, frontend `npm test`, frontend `npm run lint` (if present), manual `curl` of the endpoint against dev DB.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **MIRROR**: Copy pattern from elsewhere in codebase

---

### 1. CREATE `src/grins_platform/schemas/appointment_timeline.py`

- **IMPLEMENT**:
  - `class TimelineEventKind(str, Enum)` with values: `OUTBOUND_SMS`, `INBOUND_REPLY`, `RESCHEDULE_OPENED`, `RESCHEDULE_RESOLVED`, `OPT_OUT`, `OPT_IN`.
  - `class TimelineEvent(BaseModel)` with: `id: UUID`, `kind: TimelineEventKind`, `occurred_at: datetime`, `summary: str` (one-line display string), `details: dict[str, Any]` (kind-specific payload — raw body, message_type, reply_keyword, etc.), `source_id: UUID | None` (FK to the underlying row).
  - `class OptOutState(BaseModel)`: `consent_given: bool`, `recorded_at: datetime | None`, `method: str | None`.
  - `class AppointmentTimelineResponse(BaseModel)`: `appointment_id: UUID`, `events: list[TimelineEvent]`, `pending_reschedule_request: RescheduleRequestResponse | None`, `needs_review_reason: str | None`, `opt_out: OptOutState | None`, `last_event_at: datetime | None`.
  - All classes: `model_config = ConfigDict(from_attributes=True)`.
- **PATTERN**: `src/grins_platform/schemas/job_confirmation.py:15-70` — same import style, same field ordering, reuse `RescheduleRequestResponse` (import it — do not redefine).
- **IMPORTS**: `from datetime import datetime`; `from enum import Enum`; `from typing import Any`; `from uuid import UUID`; `from pydantic import BaseModel, ConfigDict, Field`; `from grins_platform.schemas.job_confirmation import RescheduleRequestResponse`.
- **GOTCHA**: Steering-doc standards require Google-style docstrings on every public class. Each class needs a one-line summary + "Validates:" line (can reference "Gap 11" since this isn't a numbered CRM Req).
- **VALIDATE**: `uv run python -c "from grins_platform.schemas.appointment_timeline import AppointmentTimelineResponse; print(AppointmentTimelineResponse.model_json_schema())"`

---

### 2. ADD `list_by_appointment` to `src/grins_platform/repositories/sent_message_repository.py`

- **IMPLEMENT**:
  ```python
  async def list_by_appointment(
      self,
      appointment_id: UUID,
      include_superseded: bool = False,
  ) -> list[SentMessage]:
      """List all outbound messages for an appointment.

      Args:
          appointment_id: The appointment UUID
          include_superseded: If False (default), filter out rows with
              superseded_at set (stale confirmations).

      Returns:
          Messages ordered by sent_at DESC (with created_at as fallback).
      """
      self.log_started("list_by_appointment", appointment_id=str(appointment_id))
      conditions = [SentMessage.appointment_id == appointment_id]
      if not include_superseded:
          conditions.append(SentMessage.superseded_at.is_(None))
      result = await self.session.execute(
          select(SentMessage)
          .where(and_(*conditions))
          .order_by(SentMessage.sent_at.desc().nulls_last(), SentMessage.created_at.desc()),
      )
      messages = list(result.scalars().all())
      self.log_completed("list_by_appointment", count=len(messages))
      return messages
  ```
- **PATTERN**: `sent_message_repository.py:219-252` (`get_by_customer_and_type`).
- **IMPORTS**: `and_`, `select` are already imported at the top.
- **GOTCHA**: Relationships (`customer`, `lead`) load lazy-selectin automatically — no need for explicit `selectinload`. The `recipient_name` resolver in `SentMessageResponse` depends on these being loaded.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_sent_message_repository.py -k list_by_appointment` (test will be written in Task 8).

---

### 3. ADD `list_by_appointment` for `JobConfirmationResponse` and `RescheduleRequest`

Check if `repositories/job_confirmation_repository.py` and `repositories/reschedule_request_repository.py` exist. (From the repo listing they do NOT — the queries currently live inline in `services/job_confirmation_service.py`.)

- **DECISION**: Add the queries as new `async def` methods on the existing `JobConfirmationService` (file `services/job_confirmation_service.py`) rather than spinning up two new repository modules. This keeps the blast radius small and matches the existing pattern where thread-correlation queries live in the service.
- **IMPLEMENT** (append near line ~1330, after `find_cancellation_thread`):
  ```python
  async def list_responses_by_appointment(
      self,
      appointment_id: UUID,
  ) -> list[JobConfirmationResponse]:
      self.log_started("list_responses_by_appointment", appointment_id=str(appointment_id))
      result = await self.session.execute(
          select(JobConfirmationResponse)
          .where(JobConfirmationResponse.appointment_id == appointment_id)
          .order_by(JobConfirmationResponse.received_at.desc()),
      )
      rows = list(result.scalars().all())
      self.log_completed("list_responses_by_appointment", count=len(rows))
      return rows

  async def list_reschedule_requests_by_appointment(
      self,
      appointment_id: UUID,
  ) -> list[RescheduleRequest]:
      self.log_started("list_reschedule_requests_by_appointment", appointment_id=str(appointment_id))
      result = await self.session.execute(
          select(RescheduleRequest)
          .where(RescheduleRequest.appointment_id == appointment_id)
          .order_by(RescheduleRequest.created_at.desc()),
      )
      rows = list(result.scalars().all())
      self.log_completed("list_reschedule_requests_by_appointment", count=len(rows))
      return rows
  ```
- **PATTERN**: `services/job_confirmation_service.py:1225-1298` — same `session.execute(select(...))` idiom.
- **IMPORTS**: `JobConfirmationResponse`, `RescheduleRequest` already imported at module top.
- **GOTCHA**: `RescheduleRequest.appointment_id` is indexed but check the existing index name (`idx_reschedule_requests_appointment`) exists in the model file before assuming query speed — it does.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/job_confirmation_service.py && uv run mypy src/grins_platform/services/job_confirmation_service.py`

---

### 4. ADD `get_latest_for_customer` to `src/grins_platform/repositories/sms_consent_repository.py`

- **IMPLEMENT** (only if method doesn't already exist — grep first):
  ```python
  async def get_latest_for_customer(
      self,
      customer_id: UUID,
  ) -> SmsConsentRecord | None:
      self.log_started("get_latest_for_customer", customer_id=str(customer_id))
      result = await self.session.execute(
          select(SmsConsentRecord)
          .where(SmsConsentRecord.customer_id == customer_id)
          .order_by(SmsConsentRecord.created_at.desc())
          .limit(1),
      )
      row: SmsConsentRecord | None = result.scalar_one_or_none()
      self.log_completed(
          "get_latest_for_customer",
          found=row is not None,
      )
      return row
  ```
- **PATTERN**: `repositories/sent_message_repository.py:254-267` (`get_by_id` — single-row pattern).
- **GOTCHA**: `SmsConsentRecord` is INSERT-ONLY. The "current" state is the newest row. Do not filter on `consent_given` here; the caller decides whether to render "opted out" or "opted in".
- **VALIDATE**: `uv run python -c "from grins_platform.repositories.sms_consent_repository import SmsConsentRepository; print(SmsConsentRepository.get_latest_for_customer.__doc__)"` (or similar sanity check).

---

### 5. CREATE `src/grins_platform/services/appointment_timeline_service.py`

- **IMPLEMENT**:
  - Class `AppointmentTimelineService(LoggerMixin)` with constructor `__init__(self, session: AsyncSession) -> None` — single arg, matching the existing `JobConfirmationService` shape. Inside: construct `self.appointment_repo = AppointmentRepository(session=session)`, `self.sent_message_repo = SentMessageRepository(session=session)`, `self.consent_repo = SmsConsentRepository(session=session)`, `self.confirmation_service = JobConfirmationService(session)`, and `self.session = session`.
  - Public method: `async def get_timeline(self, appointment_id: UUID) -> AppointmentTimelineResponse`.
    1. `appointment = await self.appointment_repo.get_by_id(appointment_id)` — if `None`, `raise AppointmentNotFoundError(appointment_id)` (the `get_by_id` returns `None` on miss; it does NOT raise).
    2. Four sequential awaits (simpler than `asyncio.gather`; the detail view is not latency-critical):
       - `outbound = await self.sent_message_repo.list_by_appointment(appointment_id)` (added in Task 2)
       - `inbound = await self.confirmation_service.list_responses_by_appointment(appointment_id)` (added in Task 3)
       - `reschedule_rows = await self.confirmation_service.list_reschedule_requests_by_appointment(appointment_id)` (added in Task 3)
       - `consent = await self.consent_repo.get_latest_for_customer(appointment.customer_id) if appointment.customer_id else None` (added in Task 4)
    3. Build events via private helpers `_outbound_to_event`, `_inbound_to_event`, `_reschedule_to_event`, `_consent_to_event`.
    4. Sort: `events.sort(key=lambda e: e.occurred_at, reverse=True)`.
    5. Compute `pending_reschedule_request`: `next((RescheduleRequestResponse.model_validate(r) for r in reschedule_rows if r.status == "open"), None)`.
    6. Compute `opt_out: OptOutState | None` from `consent` (None if no record).
    7. `last_event_at = events[0].occurred_at if events else None`.
    8. Return `AppointmentTimelineResponse(appointment_id=appointment_id, events=events, pending_reschedule_request=..., needs_review_reason=appointment.needs_review_reason, opt_out=..., last_event_at=...)`.
- **PATTERN**:
  - Service constructor: `src/grins_platform/services/job_confirmation_service.py:110-112` (single-session constructor). ✓ confirmed.
  - Query methods on repos: the four `list_by_appointment` / `list_*_by_appointment` / `get_latest_for_customer` are added in Tasks 2–4 — they exist by the time this service is wired.
  - Error raising: `raise AppointmentNotFoundError(appointment_id)` — the exception takes a single UUID, stores it on `self.appointment_id`, and sets a message. ✓ confirmed from `exceptions/__init__.py:278-291`.
- **IMPORTS** (exact, verified paths):
  ```python
  from uuid import UUID
  from sqlalchemy.ext.asyncio import AsyncSession
  from grins_platform.log_config import LoggerMixin
  from grins_platform.exceptions import AppointmentNotFoundError
  from grins_platform.repositories.appointment_repository import AppointmentRepository
  from grins_platform.repositories.sent_message_repository import SentMessageRepository
  from grins_platform.repositories.sms_consent_repository import SmsConsentRepository
  from grins_platform.services.job_confirmation_service import JobConfirmationService
  from grins_platform.schemas.appointment_timeline import (
      AppointmentTimelineResponse,
      OptOutState,
      TimelineEvent,
      TimelineEventKind,
  )
  from grins_platform.schemas.job_confirmation import RescheduleRequestResponse
  from grins_platform.schemas.sent_message import SentMessageResponse
  ```
- **GOTCHA #1**: `JobConfirmationService(session)` — single arg confirmed (`services/job_confirmation_service.py:110-112`). No need to worry about extra constructor params.
- **GOTCHA #2**: When mapping `SentMessage` → `TimelineEvent.details`, embed `SentMessageResponse.model_validate(sm).model_dump(mode="json")` so UUIDs/datetimes serialize correctly. Same for inbound — embed `ConfirmationResponseSchema.model_validate(r).model_dump(mode="json")`.
- **GOTCHA #3**: Never log message bodies or phone numbers at INFO. Use DEBUG only.
- **GOTCHA #4**: If appointment has no customer_id (defensive), skip the consent query rather than raising.
- **GOTCHA #5**: `appointment.needs_review_reason` field — confirm presence on the model before using. If not present, default to `None`.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/appointment_timeline_service.py && uv run mypy src/grins_platform/services/appointment_timeline_service.py && uv run pyright src/grins_platform/services/appointment_timeline_service.py`

---

### 6. ADD `get_appointment_timeline_service` to `src/grins_platform/api/v1/dependencies.py`

- **IMPLEMENT** — add directly below the existing `get_appointment_service` (line ~202):
  ```python
  async def get_appointment_timeline_service(
      session: Annotated[AsyncSession, Depends(get_db_session)],
  ) -> AppointmentTimelineService:
      """Provide an AppointmentTimelineService for Gap 11."""
      return AppointmentTimelineService(session=session)
  ```
  Also add: `from grins_platform.services.appointment_timeline_service import AppointmentTimelineService` at the top imports.
- **PATTERN**: `api/v1/dependencies.py:181-202` (`get_appointment_service`). ✓ confirmed.
- **GOTCHA**: `get_job_confirmation_service` does NOT exist in this file (confirmed). The `AppointmentTimelineService` instantiates `JobConfirmationService(session)` internally, so we don't need to compose one here.
- **VALIDATE**: `uv run ruff check src/grins_platform/api/v1/dependencies.py && uv run mypy src/grins_platform/api/v1/dependencies.py`

---

### 7. ADD endpoint `GET /api/v1/appointments/{appointment_id}/timeline` in `src/grins_platform/api/v1/appointments.py`

- **IMPLEMENT**: Insert the endpoint **immediately after** the existing `get_appointment` handler (after line 803) so related routes sit together. Use the exact logging + error-handling shape from `get_appointment` (lines 777-803).
  ```python
  @router.get(  # type: ignore[untyped-decorator]
      "/{appointment_id}/timeline",
      response_model=AppointmentTimelineResponse,
      summary="Get appointment communication timeline",
      description=(
          "Returns a chronologically-sorted communication timeline for an "
          "appointment: outbound SMS, inbound replies, reschedule requests, "
          "and opt-out state. Backs Gap 11 AppointmentDetail enhancement."
      ),
  )
  async def get_appointment_timeline(
      appointment_id: UUID,
      service: Annotated[
          AppointmentTimelineService, Depends(get_appointment_timeline_service)
      ],
  ) -> AppointmentTimelineResponse:
      """Get appointment communication timeline.

      Validates: Gap 11.
      """
      _endpoints.log_started("get_appointment_timeline", appointment_id=str(appointment_id))
      try:
          result = await service.get_timeline(appointment_id)
      except AppointmentNotFoundError as e:
          _endpoints.log_rejected("get_appointment_timeline", reason="not_found")
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"Appointment not found: {e.appointment_id}",
          ) from e
      _endpoints.log_completed("get_appointment_timeline", appointment_id=str(appointment_id))
      return result
  ```
- **PATTERN**: `api/v1/appointments.py:777-803`.
- **IMPORTS**: Add `AppointmentTimelineService` from services module, `get_appointment_timeline_service` from `.dependencies`, `AppointmentTimelineResponse` from schemas.
- **GOTCHA**: **Route order matters** — `GET /{appointment_id}/timeline` must come **before** any `PUT /{appointment_id}` handlers that FastAPI might match loosely. Placing it after `get_appointment` (GET) is correct and safe.
- **GOTCHA**: If the codebase has auth dependencies (`CurrentActiveUser`) on the existing get endpoint, add the same dependency here. Check whether `get_appointment` takes `current_user` — it does NOT at line 777-803, but `update_appointment` does at line 820. Match the read endpoint's auth level.
- **VALIDATE**: `uv run ruff check src/grins_platform/api/v1/appointments.py && uv run mypy src/grins_platform/api/v1/appointments.py && uv run pytest src/grins_platform/tests/functional/test_appointment_timeline_endpoint.py -v` (test written in task 9).

---

### 8. CREATE `src/grins_platform/tests/unit/test_appointment_timeline_service.py`

- **IMPLEMENT**: `@pytest.mark.unit` tests for `AppointmentTimelineService.get_timeline`. Mock all three repositories + `JobConfirmationService` with `unittest.mock.AsyncMock`. Cover:
  - Empty appointment (no messages, no responses, no requests, no consent) → empty events, all flags None.
  - One outbound + one inbound → two events sorted newest-first.
  - Open reschedule request → `pending_reschedule_request` populated.
  - Latest consent with `consent_given=False` → `opt_out.consent_given == False`.
  - Appointment not found → `AppointmentNotFoundError` raised.
  - `needs_review_reason="no_confirmation_response"` on appointment → copied to response.
  - Mixed timeline ordering (outbound at 10am, reschedule at 11am, inbound at 10:05am) → correct sort order.
- **PATTERN**: `src/grins_platform/tests/unit/test_job_confirmation_service.py` — test class structure, fixture patterns.
- **GOTCHA**: Use `pytest.mark.asyncio` (or `pytest_asyncio.fixture`) — all service methods are async. Confirm the convention in the existing unit-test file.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_timeline_service.py -v`

---

### 9. CREATE `src/grins_platform/tests/functional/test_appointment_timeline_service.py`

**IMPORTANT CONVENTION**: the project's `@pytest.mark.functional` tests in this repo use `AsyncMock`-backed DB sessions with local `_make_*` helpers — NOT a real DB or HTTP client. Confirmed via `src/grins_platform/tests/functional/test_yrc_confirmation_functional.py:36-48`. Match that convention; do not invent a new one.

- **IMPLEMENT**: `@pytest.mark.functional` + `@pytest.mark.asyncio` tests that exercise `AppointmentTimelineService.get_timeline` end-to-end with an `AsyncMock` DB. Cover:
  - Populated timeline: mock returns one outbound SMS, one inbound reply, one open reschedule request → assert the result has 3+ events, sorted newest-first, `pending_reschedule_request` is set.
  - Empty timeline: mock returns empty lists → events is empty, flags are all `None`.
  - Appointment not found: `appointment_repo.get_by_id` returns `None` → expect `AppointmentNotFoundError`.
  - Opt-out: mock consent returns a row with `consent_given=False` → `opt_out.consent_given is False`.
- **PATTERN**:
  - File-local helpers: mirror `_make_appointment`, `_make_sent_message`, `_build_mock_db` from `tests/functional/test_yrc_confirmation_functional.py:36-48`.
  - Test structure: class-based tests with `@pytest.mark.functional @pytest.mark.asyncio` on each method; see lines 128-165 for the shape.
- **GOTCHA**: Don't call `httpx.AsyncClient` or `TestClient` — this project's functional layer is service-level with mocked DB. An HTTP-layer test for the endpoint belongs under `tests/integration/` if the project adds one later; for now the unit test (Task 8) + this functional service test give sufficient coverage.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_appointment_timeline_service.py -v`

---

### 10. ADD `getTimeline` to `frontend/src/features/schedule/api/appointmentApi.ts`

- **IMPLEMENT**:
  ```ts
  async getTimeline(id: string): Promise<AppointmentTimelineResponse> {
    const response = await apiClient.get(`/appointments/${id}/timeline`);
    return response.data;
  }
  ```
- **PATTERN**: `appointmentApi.ts:29-52` (`getById` method).
- **IMPORTS**: Add `AppointmentTimelineResponse` from `../types`.
- **GOTCHA**: Update `features/schedule/api/appointmentApi.test.ts` to add a test for the new method (mirror existing tests in that file).
- **VALIDATE**: `cd frontend && npm test appointmentApi`

---

### 11. CREATE TypeScript types for the timeline

- **IMPLEMENT**: Append to `frontend/src/features/schedule/types/index.ts` (where `RescheduleRequestDetail` already lives at lines 439-452):
  ```ts
  export type TimelineEventKind =
    | 'outbound_sms'
    | 'inbound_reply'
    | 'reschedule_opened'
    | 'reschedule_resolved'
    | 'opt_out'
    | 'opt_in';

  export interface TimelineEvent {
    id: string;
    kind: TimelineEventKind;
    occurred_at: string;  // ISO
    summary: string;
    details: Record<string, unknown>;
    source_id: string | null;
  }

  export interface OptOutState {
    consent_given: boolean;
    recorded_at: string | null;
    method: string | null;
  }

  export interface PendingRescheduleRequest {
    id: string;
    job_id: string;
    appointment_id: string;
    customer_id: string;
    original_reply_id: string | null;
    requested_alternatives: Record<string, unknown> | null;
    raw_alternatives_text: string | null;
    status: string;
    created_at: string;
    resolved_at: string | null;
  }

  export interface AppointmentTimelineResponse {
    appointment_id: string;
    events: TimelineEvent[];
    pending_reschedule_request: PendingRescheduleRequest | null;
    needs_review_reason: string | null;
    opt_out: OptOutState | null;
    last_event_at: string | null;
  }
  ```
- **PATTERN**: existing types in `frontend/src/features/schedule/types/index.ts`. ✓ confirmed.
- **GOTCHA**: The existing `RescheduleRequestDetail` type is an *enriched* shape with `customer_name`, `original_appointment_date`, etc., which the `/timeline` endpoint does NOT emit. Declare a new `PendingRescheduleRequest` interface that matches the backend `RescheduleRequestResponse` schema exactly (plain DB fields only). Do NOT reuse `RescheduleRequestDetail` here.
- **GOTCHA**: Enum strings must match backend values exactly (lowercase, underscore).

---

### 12. EXTEND query-key factory in `frontend/src/features/schedule/hooks/useAppointments.ts`

- **IMPLEMENT**: Add `timeline: (id: string) => [...appointmentKeys.all, 'timeline', id] as const` to the existing `appointmentKeys` factory object.
- **PATTERN**: `useAppointments.ts:10-22`.
- **VALIDATE**: TS compile (tsc) — the factory shape is consumed by mutation-invalidation code in Task 15.

---

### 13. CREATE `frontend/src/features/schedule/hooks/useAppointmentTimeline.ts`

- **IMPLEMENT**:
  ```ts
  import { useQuery } from '@tanstack/react-query';
  import { appointmentApi } from '../api/appointmentApi';
  import { appointmentKeys } from './useAppointments';

  export function useAppointmentTimeline(id: string | undefined) {
    return useQuery({
      queryKey: appointmentKeys.timeline(id ?? ''),
      queryFn: () => appointmentApi.getTimeline(id!),
      enabled: !!id,
      staleTime: 30_000,
    });
  }
  ```
- **PATTERN**: `useAppointments.ts:27-43` (`useAppointment`).
- **GOTCHA**: Add a `staleTime` (e.g., 30s) so the timeline doesn't refetch on every tab focus while admin is reading. Mutations that mutate communication state will invalidate manually in Task 15.
- **VALIDATE**: `cd frontend && npx tsc --noEmit`
- **EXPORT**: Re-export from `features/schedule/hooks/index.ts`.

---

### 14. CREATE `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.tsx`

- **IMPLEMENT**:
  - Props: `{ data: AppointmentTimelineResponse | undefined; isLoading: boolean; error: Error | null }`.
  - Wrap in a `<details>` element (matches collapsed-by-default notes idiom on `AppointmentDetail.tsx:352-361`). `<summary>` shows the heading + "Last reply {relativeTime}" derived from `data.last_event_at`.
  - When no events: show "No customer communication yet."
  - When events: render a vertical list. Each row:
    - Icon (Lucide React) + keyword from `kind`: `outbound_sms → MessageSquare` / `inbound_reply → MessageCircle` / `reschedule_opened → AlertTriangle` / `opt_out → Ban`.
    - `summary` text.
    - Relative time (`formatDistanceToNow` from `date-fns`) + absolute hover.
    - For outbound: `details.delivery_status` as a small badge.
    - For inbound: `details.raw_reply_body` truncated to 80 chars + "Show full" toggle.
  - Loading state: skeleton.
  - Error state: `Alert variant="destructive"` (shadcn).
  - Each row: `data-testid="timeline-event-{id}"`.
  - Root element: `data-testid="appointment-communication-timeline"`.
- **PATTERN**: `frontend/src/features/dashboard/components/RecentActivity.tsx:1-100+` for unified timeline; `AppointmentDetail.tsx:352-385` for the `<details>` + inline-timeline idiom.
- **IMPORTS**: `cn` from `@/shared/utils` (or wherever `cn` lives — check existing `AppointmentDetail` imports), `formatDistanceToNow` from `date-fns`, Lucide icons, UI components.
- **GOTCHA**: Follow the VSA rule — import only from `core/`, `shared/`, and the current feature slice.

---

### 15. CREATE `frontend/src/features/schedule/components/AppointmentCommunicationTimeline.test.tsx`

- **IMPLEMENT**: Vitest + RTL tests wrapped in `QueryProvider` (or the project's shared test wrapper — check existing test files for the helper). Cover:
  - Renders collapsed with `<details>` closed by default.
  - Expanding reveals events in correct order (mock props with two events, assert DOM order).
  - Empty state renders "No customer communication yet."
  - Loading state renders skeleton.
  - Error state renders `Alert variant="destructive"`.
  - data-testid presence: `appointment-communication-timeline` root + `timeline-event-{id}` per row.
- **PATTERN**: `AppointmentDetail.test.tsx` and `RescheduleRequestsQueue.test.tsx`.
- **TEST WRAPPER**: `import { QueryProvider } from '@/core/providers/QueryProvider'` — confirmed. Wrap any rendered component using hooks: `render(<QueryProvider><AppointmentCommunicationTimeline ... /></QueryProvider>)`.
- **VALIDATE**: `cd frontend && npm test AppointmentCommunicationTimeline`

---

### 16. UPDATE `frontend/src/features/schedule/components/AppointmentDetail.tsx`

- **IMPLEMENT**:
  - Import `useAppointmentTimeline` and `AppointmentCommunicationTimeline`.
  - After the existing `useAppointment` call (line ~65), call `const { data: timeline, isLoading: timelineLoading, error: timelineError } = useAppointmentTimeline(appointmentId);`.
  - Render, in order, between the existing header (~line 210) and the content block:
    1. **Opt-out badge** — only if `timeline?.opt_out?.consent_given === false`. Red badge near status: "Opted out via {method} on {date}". `data-testid="opt-out-badge-{appointmentId}"`.
    2. **Reschedule banner** — only if `timeline?.pending_reschedule_request`. Orange banner: "Customer requested reschedule — {created_at relative}" + `raw_alternatives_text` inline. Two buttons: "Reschedule to Alternative" (opens existing `AppointmentForm` dialog pre-filled, exactly like `RescheduleRequestsQueue.tsx:268-276`) and "Resolve without reschedule" (calls `useResolveReschedule` mutation). `data-testid="reschedule-banner-{appointmentId}"`.
    3. **No-reply banner** — only if `timeline?.needs_review_reason === 'no_confirmation_response'`. Gray banner: "No reply received." + three buttons mirroring `NoReplyReviewQueue.tsx:288-333`: "Call Customer" (tel: link), "Send Reminder" (opens confirmation dialog), "Mark Contacted" (calls `useMarkContacted`). `data-testid="no-reply-banner-{appointmentId}"`.
  - Insert `<AppointmentCommunicationTimeline data={timeline} isLoading={timelineLoading} error={timelineError} />` between the notes `<details>` (ends ~line 361) and the field-work timeline (~line 363).
- **PATTERN**:
  - Banner UI: mirror `RescheduleRequestsQueue.tsx:225-291` for card styling; mirror `NoReplyReviewQueue.tsx:252-336` for action buttons.
  - **Exact hook names (confirmed)**: `useResolveRescheduleRequest` (NOT `useResolveReschedule`) from `hooks/useRescheduleRequests.ts:21-30`; `useMarkContacted` and `useSendReminder` (separate hooks) from `hooks/useNoReplyReview.ts:40-52, 61-70`.
  - **Reschedule-dialog reuse** (`RescheduleRequestsQueue.tsx:41-47, 182-212`): own a local `useState<PendingRescheduleRequest | null>` for the dialog target; render `<Dialog open={!!target} onOpenChange={...}><AppointmentForm appointment={...} onSuccess={...} /></Dialog>`.
  - **UI imports** (confirmed convention): `import { Badge } from '@/components/ui/badge'`, `import { Button } from '@/components/ui/button'`, `import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'`, `import { Alert } from '@/components/ui/alert'`, `import { Skeleton } from '@/components/ui/skeleton'`, `import { cn } from '@/lib/utils'`.
- **GOTCHA #1**: Don't duplicate `AppointmentForm` dialog state — the reschedule banner opens the same dialog that `RescheduleRequestsQueue` opens. Reuse the existing dialog component + state idiom.
- **GOTCHA #2**: The "Send Reminder" confirmation-dialog flow enforces a dev safety rule ("only `+19527373312` may receive real SMS", per memory + `NoReplyReviewQueue.tsx:186`). Reuse that dialog verbatim — do NOT reimplement the guard.
- **GOTCHA #3**: Keep the modal's existing test-ids stable — adding new elements should not reorder or rename existing ones. Run the existing `AppointmentDetail.test.tsx` after the edit to catch regressions.
- **VALIDATE**: `cd frontend && npm test AppointmentDetail`

---

### 17. WIRE cache invalidation in existing mutation hooks

- **IMPLEMENT**: Add `queryClient.invalidateQueries({ queryKey: appointmentKeys.timeline(id) })` to each of these `onSuccess` blocks:
  - `useConfirmAppointment` in `useAppointmentMutations.ts:100-110` — confirmation mutates inbound reply state.
  - `useCancelAppointment` in `useAppointmentMutations.ts` — cancellation adds a new SMS.
  - `useMarkContacted` in `useNoReplyReview.ts:40-52` — clears `needs_review_reason`.
  - `useSendReminder` in `useNoReplyReview.ts:61-70` — adds outbound SMS.
  - `useResolveRescheduleRequest` in `useRescheduleRequests.ts:21-30` — closes pending request. **Note**: this hook currently only invalidates `rescheduleKeys.all`; the appointmentId may not be on the mutation args, so grab it from the `onSuccess` arguments or have the caller invalidate `timeline(appointmentId)` explicitly. Confirm by reading the hook before editing.
- **PATTERN**: `useAppointmentMutations.ts:100-110` (exact shape). Use `queryClient.invalidateQueries({ queryKey: appointmentKeys.timeline(id) })` verbatim.
- **GOTCHA**: `useResolveRescheduleRequest`'s `onSuccess` signature receives only `data` — if you need the `appointmentId`, read it from `variables` (the second arg of `onSuccess`). Mutation variables include `{ id, notes }` where `id` is the reschedule-request id, NOT the appointment id. You may need to adjust the mutation args to carry `appointmentId` too — simpler alternative: have the banner's `onSuccess` handler in `AppointmentDetail` call `queryClient.invalidateQueries({ queryKey: appointmentKeys.timeline(appointmentId) })` directly, leaving the shared hook untouched.
- **VALIDATE**: `cd frontend && npm test useAppointmentMutations useNoReplyReview useRescheduleRequests`

---

### 18. UPDATE `frontend/src/features/schedule/components/AppointmentDetail.test.tsx`

- **IMPLEMENT**: Add tests that mock `appointmentApi.getTimeline` and assert:
  - Opt-out badge renders when `opt_out.consent_given === false`.
  - Reschedule banner renders when `pending_reschedule_request` is present; clicking "Resolve without reschedule" calls the mutation.
  - No-reply banner renders when `needs_review_reason === 'no_confirmation_response'`; clicking "Mark Contacted" calls the mutation.
  - Timeline section is present.
- **PATTERN**: existing `AppointmentDetail.test.tsx` mocking approach.
- **VALIDATE**: `cd frontend && npm test AppointmentDetail`

---

## TESTING STRATEGY

### Unit Tests (backend, `@pytest.mark.unit`)
- `test_appointment_timeline_service.py` — 7 cases (Task 8).
- Target: service-layer coverage 90%+. All repository calls mocked with `AsyncMock`.

### Functional Tests (backend, `@pytest.mark.functional`)
- `test_appointment_timeline_endpoint.py` — 4 cases (Task 9). Real DB, real service, HTTP round-trip via `httpx.AsyncClient`.

### Integration Tests (backend, `@pytest.mark.integration`)
- Not strictly required for Gap 11 — the endpoint is read-only aggregation of existing data. If the project convention is "every new endpoint gets an integration test", add one test that creates a full appointment with all four sources via existing factories and walks the endpoint response.

### Frontend Unit Tests (Vitest + RTL)
- `AppointmentCommunicationTimeline.test.tsx` — 5 cases (Task 15).
- `useAppointmentTimeline.test.tsx` — `renderHook` + `QueryProvider` wrapper; assert `data` appears after mocked network call. (Optional — the existing `useAppointments.test.tsx` pattern is minimal; match its depth.)
- `AppointmentDetail.test.tsx` — 4 new cases (Task 18).

### Edge Cases
- Appointment with no customer_id → no consent fetch, opt_out is None.
- Appointment that was rescheduled from another (`rescheduled_from_id` present) — should the timeline show the original reschedule request? **Decision**: Out of scope for Gap 11; add a TODO comment. Gap doc flags it explicitly as an edge case under "Rescheduled appointment".
- Very long history (>50 events) — current implementation returns all; the frontend `<details>` naturally caps visibility. Gap doc suggests pagination later.
- Multiple Y replies (Gap 02 scenario) — all are shown, newest first.
- Informal opt-out pending admin action — surfaces via the `SmsConsentRecord` (if the system writes one for informal opt-outs) OR via alerts (out of scope — Gap 06 integration).

---

## VALIDATION COMMANDS

Execute every command. Each must exit 0 with zero warnings/errors.

### Level 1: Syntax & Style
```
uv run ruff check src/ --fix
uv run ruff format src/
cd frontend && npm run lint
```

### Level 2: Type Checking
```
uv run mypy src/
uv run pyright src/
cd frontend && npx tsc --noEmit
```

### Level 3: Unit Tests
```
uv run pytest src/grins_platform/tests/unit/test_appointment_timeline_service.py -v
cd frontend && npm test -- --run AppointmentCommunicationTimeline AppointmentDetail useAppointmentTimeline
```

### Level 4: Functional / Integration Tests
```
uv run pytest -m functional src/grins_platform/tests/functional/test_appointment_timeline_endpoint.py -v
uv run pytest -m "unit or functional" -v  # regression sweep — no other tests should break
```

### Level 5: Manual Validation (dev DB)
```
# Start backend
uv run uvicorn grins_platform.main:app --reload --port 8000

# Smoke the endpoint — replace UUID with a real appointment from dev DB
curl -s "http://localhost:8000/api/v1/appointments/{uuid}/timeline" | jq .

# Expect: appointment_id, events[], pending_reschedule_request, needs_review_reason, opt_out, last_event_at
```

### Level 6: Frontend Manual Validation
- Start frontend: `cd frontend && npm run dev`.
- Open calendar, click an appointment whose customer has sent replies.
- Verify: Communication section appears, collapses/expands, shows sorted events.
- Verify: if the appointment has an open reschedule request, the banner renders with action buttons.
- Verify: opt-out badge appears only when appointment's customer has `consent_given=false` in the latest `SmsConsentRecord`.
- Verify: clicking "Mark Contacted" clears the no-reply banner (mutation fires + timeline refetches).

### Level 7: agent-browser E2E (per `.kiro/steering/e2e-testing-skill.md`)
Optional — if the project's e2e convention requires it. Script:
```
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser click "[data-testid='appointment-card-{uuid}']"
agent-browser wait --selector "[data-testid='appointment-communication-timeline']"
agent-browser is visible "[data-testid='appointment-communication-timeline']"
```

---

## ACCEPTANCE CRITERIA

- [ ] `GET /api/v1/appointments/{id}/timeline` exists, returns `AppointmentTimelineResponse`, 404s on unknown UUIDs.
- [ ] The response contains outbound SMS, inbound replies, reschedule requests, and consent state — all sorted newest-first.
- [ ] `AppointmentDetail.tsx` renders a new Communication section that shows the timeline.
- [ ] When `pending_reschedule_request` is set, a banner appears with "Reschedule to Alternative" and "Resolve" actions (reusing existing mutation hooks).
- [ ] When `needs_review_reason === 'no_confirmation_response'`, a no-reply banner appears with the three existing `NoReplyReviewQueue` actions.
- [ ] When the customer's latest `SmsConsentRecord` has `consent_given=false`, an opt-out badge appears in the header.
- [ ] Ruff, MyPy, Pyright, ESLint, tsc all pass with zero errors/warnings.
- [ ] Backend unit test coverage for `AppointmentTimelineService` ≥ 90%.
- [ ] Frontend component coverage for `AppointmentCommunicationTimeline` ≥ 80%.
- [ ] Existing `AppointmentDetail.test.tsx` passes unchanged (no regressions on existing behavior).
- [ ] Manual smoke against dev DB confirms the endpoint returns real data for an appointment with known history.
- [ ] Timeline invalidates after mutations: confirm, cancel, mark-contacted, send-reminder, resolve-reschedule.
- [ ] Reading the gap doc's "Reproduction — concrete admin blind spot" scenario is no longer reproducible: the admin sees the reschedule state inside the modal.

---

## COMPLETION CHECKLIST

- [ ] All tasks 1–18 completed in order
- [ ] Each task's VALIDATE command executed and passed
- [ ] All Level-1 through Level-6 validation commands passed
- [ ] Backend + frontend tests pass with no regressions
- [ ] Manual dev-DB smoke confirmed
- [ ] No secrets, PII, or message bodies logged at INFO level
- [ ] `DEVLOG.md` updated per `.kiro/steering/devlog-rules.md` with a FEATURE entry dated 2026-04-21 summarizing the work (category: FEATURE; title: "Gap 11 — AppointmentDetail communication timeline")
- [ ] Gap 11 cross-references (Gap 05, 06, 12, 13, 16) noted in DEVLOG "Next Steps" so later gaps know the endpoint exists

---

## NOTES

### Why a single `/timeline` endpoint (not four)
The gap doc lists both options. One endpoint wins on:
- Bandwidth: single round-trip vs four waterfalled queries.
- Sort correctness: merging on the server is trivial; merging on the client requires reconciling nulls and formats.
- Cache invalidation: one query key to invalidate after any communication mutation.
- Forward compatibility: when Gap 5 adds audit events, the endpoint shape extends by appending new `TimelineEventKind` values — clients tolerate unknown kinds if we render them with a generic fallback icon.

### Why we did NOT create dedicated repositories for `JobConfirmationResponse` and `RescheduleRequest`
The existing pattern in the codebase is that their queries live inside `JobConfirmationService`. Creating new repository modules purely for this feature would introduce parallel indirection with no caller benefit. If future work needs broader ORM access to these models, extract then.

### Trade-offs considered
- **Eager vs lazy loading of `SmsConsentRecord`**: the consent table is INSERT-ONLY, so the "current state" query is a single `ORDER BY created_at DESC LIMIT 1`. Trivially fast with the existing `idx_sms_consent_customer` index. No need to denormalize onto `Customer`.
- **Event-kind enum vs free-string**: a closed enum catches frontend rendering bugs at type-check time. The cost is one migration if a new kind is added — acceptable.
- **Appointment-scoped vs customer-scoped timeline**: Gap 11 is appointment-detail specific. Gap 13 handles the broader customer view. Keeping them separate avoids coupling two gaps.

### Out of scope (tracked elsewhere)
- Full audit-log event integration (Gap 5).
- Calendar-card visual hints that mirror banner state (Gap 12).
- CustomerDetail messages-tab adjacency (Gap 13).
- Unified admin inbox (Gap 16).
- Original-reschedule-request surfacing on the successor appointment (edge case in gap doc).

### Confidence score
**9.5/10** for one-pass success. All three previously-flagged risks have been resolved against the actual codebase:

- ✅ `AppointmentNotFoundError` lives at `grins_platform.exceptions:278-291`, takes `appointment_id: UUID`.
- ✅ `JobConfirmationService(db: AsyncSession)` — single-arg constructor confirmed at `services/job_confirmation_service.py:110-112`. `AppointmentTimelineService` instantiates it inline; no new dependency provider needed.
- ✅ `useNoReplyReview.ts:40-52, 61-70` exposes `useMarkContacted` and `useSendReminder` as separate hooks. Confirmed.
- ✅ **Name correction applied**: the reschedule hook is `useResolveRescheduleRequest` (not `useResolveReschedule`); the frontend type is `RescheduleRequestDetail` (not `RescheduleRequestResponse`) — but the `/timeline` endpoint emits a plainer shape, so we declare a new `PendingRescheduleRequest` type.
- ✅ **UI-import convention**: `@/components/ui/*` and `@/lib/utils` (the steering doc's `@/shared/components/ui` is stale).
- ✅ **Test-wrapper**: `QueryProvider` from `@/core/providers/QueryProvider`.
- ✅ **Functional-test convention**: this project's `@pytest.mark.functional` tests use `AsyncMock` DB with local `_make_*` helpers, not real DB or HTTP clients. Task 9 updated accordingly.
- ✅ `_endpoints` in `appointments.py:94` is an `AppointmentEndpoints()` instance with `LoggerMixin` methods, not a plain logger.

- ✅ `needs_review_reason` lives on `Appointment` at `models/appointment.py:179` as `Mapped[str | None]`. Directly accessible.

**Final confidence: 10/10** for one-pass success. All imports, method names, class signatures, hook names, UI paths, test conventions, and field locations have been verified against the actual files on disk.
