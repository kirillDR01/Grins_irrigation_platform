# Feature: Cluster D — Scheduling & Confirmations

The following plan is complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils, types, and models. Import from the right files etc.

## Feature Description

Cluster D groups five scheduling/confirmation papercuts into one coordinated frontend-led release. The throughline: **drag-drop must never silently text the customer**, **buttons that depend on customer confirmation must explain themselves**, and **the daily schedule should pick slots the same way the sales pipeline already does**. Two of the items are pure copy/UX (status labels, banners), two are interaction polish (drag-drop demote, daily slot-pick), and one is a small refactor (single canonical on-the-way hook).

The five items in this cluster (per `docs/2026-05-12-verification-and-clarifications.md:1491–1503`):

1. **Drag-drop demote without auto-SMS.** Dragging a CONFIRMED appointment to a new slot must (a) revert its status to SCHEDULED — keeps it visually on the calendar but un-confirmed, and (b) NOT call any send-confirmation endpoint nor fire the reschedule SMS. Admin must explicitly click Send for a fresh confirmation; customer must reply Y again to return to CONFIRMED.
2. **Status label "Awaiting confirmation" vs "Scheduled".** Apply consistently to both appointments and sales entries. Pure frontend, no schema change.
3. **Banner placeholder for tech-mobile actions.** Render a visible info banner above the On-My-Way / Job-Start / Job-Complete buttons when the appointment is not yet CONFIRMED, explaining that these actions unlock once the customer replies Y. Buttons themselves are hidden, not disabled.
4. **Port the WeekCalendar slot-pick UX onto DayMode.** Lift the click-to-pick + drag-across-slots interaction from `WeekCalendar.tsx` (sales pipeline) onto the daily admin schedule `DayMode.tsx` so admins can slide/drop to define an appointment block. Visual consistency win; existing data model + mutations stay.
5. **Canonical on-the-way hook = `useOnMyWay` (job-side).** Deprecate `useMarkAppointmentEnRoute` (appointment-side). Job-side already has audit logging on `job.on_my_way_at` (`api/v1/jobs.py:1272–1359`) and bughunt L-2 ensures the timestamp is only logged after SMS dispatch succeeds (`api/v1/jobs.py:1303–1343`).

## User Story

As an **admin** scheduling and dispatching irrigation work,
I want **the daily schedule to behave predictably — labels that mean what they say, drag-drops that don't accidentally text the customer, banners that explain why workflow buttons are hidden, and one canonical "On My Way" path that audits correctly**,
So that I can **drag jobs around the calendar without spamming customers, see at a glance which appointments are still awaiting Y reply, and dispatch techs through the right code path every time**.

## Problem Statement

Today the schedule surface lies in five small ways:

- **Drag-drop silently sends SMS.** `AppointmentService.update_appointment` already fires `_send_reschedule_sms` (`services/appointment_service.py:495–508`) on any date/time change. Drag-drop has no way to suppress this. The user's directive is explicit: drag-drop must never auto-send.
- **"Scheduled" is the wrong word for un-confirmed appointments.** `appointmentStatusConfig.scheduled.label` (`frontend/src/features/schedule/types/index.ts:192–195`) and `AppointmentList.getStatusLabel` (`AppointmentList.tsx:73–92`) both render "Scheduled" while the customer has not yet replied Y. The user wants "Awaiting confirmation" pre-Y, "Scheduled" post-Y.
- **Tech-mobile workflow buttons silently disappear** when an appointment is not CONFIRMED (`ActionTrack.tsx:40–47` returns `'disabled'` when `deriveStep` is null). Admins see greyed/missing buttons with no explanation.
- **Daily schedule has no slot-pick UX** for creating new appointments. The sales pipeline already has a polished click-to-pick + drag-across-slots experience in `WeekCalendar.tsx`. Visual divergence between the two surfaces.
- **Two hooks for on-the-way.** `useOnMyWay` (jobs side, audited, SMS-aware) and `useMarkAppointmentEnRoute` (appointments side, no SMS, no `on_my_way_at` write). Same action, two paths → drift risk.

## Solution Statement

Land the five fixes as **one coordinated PR**, each gated behind its own task block so they can be reverted individually:

1. **Add `suppress_notifications: bool = False` to `AppointmentUpdate`**, plumb it into `AppointmentService.update_appointment` (the service already takes `notify_customer: bool = True`). Frontend drag-drop handlers in `DayMode.handleRowDrop` and `WeekMode.handleCellDrop` set the flag to `True`. The existing demote-CONFIRMED→SCHEDULED logic (`services/appointment_service.py:509–526`) stays untouched — it already does the right thing.
2. **Relabel** `appointmentStatusConfig.scheduled.label` to "Awaiting confirmation" and `appointmentStatusConfig.confirmed.label` to "Scheduled". For sales entries, extract a `getSalesStatusLabel(entry)` helper that returns "Awaiting confirmation" when `entry.status === 'estimate_scheduled'` and the latest `SalesCalendarEvent.confirmation_status !== 'confirmed'`. Wire it into the two render sites (`SalesPipeline.tsx`, `SalesDetail.tsx`).
3. **In `ActionTrack.tsx`**: extend the early-return guard to also short-circuit on `status === 'scheduled'`, returning an `<Alert variant="info">` (`frontend/src/shared/components/ui/alert.tsx:63–73`) with copy explaining the gate.
4. **In `DayMode.tsx`**: add an empty-strip mousedown→mousemove→mouseup state machine mirroring `WeekCalendar.tsx:92–143` that drags a range, computes `(startMin, endMin)`, and opens the existing create-appointment dialog with the range pre-filled. Keep DayMode's 15-min `SNAP_MINUTES` precision; do not lower to 30-min.
5. **Migrate the two appointment-side callsites** (`StaffWorkflowButtons.tsx:28`, `ActionTrack.tsx:36`) from `useMarkAppointmentEnRoute` to `useOnMyWay(appointment.job_id)`. The `Appointment` response already exposes `job_id` (`frontend/src/features/schedule/types/index.ts:66–80`, `src/grins_platform/schemas/appointment.py` AppointmentResponse). Remove the hook from `frontend/src/features/schedule/hooks/index.ts:24` and `frontend/src/features/schedule/index.ts:50` exports. Keep `appointmentApi.markEnRoute` defined for now (used only by the deprecated hook); flag for removal in a follow-up.

## Feature Metadata

**Feature Type**: Enhancement (UX + small backend schema add) + Refactor (canonical hook)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Backend: `AppointmentUpdate` schema, `AppointmentService.update_appointment` (passthrough flag only — no new branching), `PUT /appointments/{id}` endpoint, `SalesEntryResponse` schema + sales pipeline list service (one denormalized field added)
- Frontend: `appointmentStatusConfig`, `AppointmentList`, `ActionTrack`, `StaffWorkflowButtons`, `DayMode`, `WeekMode`, `ResourceTimelineView`, `SchedulePage` (new prop), sales pipeline label helper, `SalesEntry` TS type
- Tests: appointment-service unit tests, appointment-API integration tests, ActionTrack render tests, DayMode interaction tests, hook-callsite migration tests
**Dependencies**: None new. All work uses existing libraries (Tailwind, lucide-react, sonner, shared `<Alert>` primitive).

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Backend (appointment update path)**

- `src/grins_platform/schemas/appointment.py` (lines 51–64) — Current `AppointmentUpdate` schema. Add `suppress_notifications` here.
- `src/grins_platform/services/appointment_service.py` (lines 400–558) — `update_appointment` method. Already has `notify_customer: bool = True` parameter at line 406; already demotes CONFIRMED→SCHEDULED at lines 509–526; already fires `_send_reschedule_sms` at lines 495–508 gated on `notify_customer`. **Critical**: the existing logic already does the demote you want. Only the SMS-suppression path is new.
- `src/grins_platform/api/v1/appointments.py` (lines 1085–1131) — `PUT /appointments/{id}` endpoint. Pass `notify_customer=not data.suppress_notifications` (or equivalent) through `service.update_appointment`.
- `src/grins_platform/models/enums.py` (lines 188–203) — `AppointmentStatus` enum. Confirms values used in label logic: `pending`, `draft`, `scheduled`, `confirmed`, `en_route`, `in_progress`, `completed`, `cancelled`, `no_show`.

**Backend (canonical on-the-way endpoint)**

- `src/grins_platform/api/v1/jobs.py` (lines 1272–1359) — `POST /jobs/{job_id}/on-my-way`. Audited; sends SMS; rolls back `on_my_way_at` on SMS failure (bughunt L-2 fix at lines 1303–1343); auto-transitions associated appointment to EN_ROUTE if it was CONFIRMED or SCHEDULED (lines 1348–1356). **Do not modify.** This is the canonical path the migrated callsites will use.
- `src/grins_platform/services/appointment_service.py` (lines 1980–1981 per Explore agent) — Sets `en_route_at` when a generic status update transitions to EN_ROUTE. Leave in place for backward compat; nothing calls into it after the migration except scripts/tests.

**Frontend (status labels)**

- `frontend/src/features/schedule/types/index.ts` (lines 177–227) — `appointmentStatusConfig`. Source of truth for the appointment badge label. Lines 192–195: `scheduled` → relabel to "Awaiting confirmation". Lines 197–201: `confirmed` → relabel to "Scheduled".
- `frontend/src/features/schedule/components/AppointmentList.tsx` (lines 73–92) — `getStatusLabel` switch. Line 79–80: `case 'confirmed': return 'Scheduled';` — currently lacks a `case 'scheduled'` branch. Add one that returns "Awaiting confirmation". Update the existing `confirmed` case to keep returning "Scheduled" (already does).
- `frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx` (lines 1–85, specifically 41–51) — Renders `appointmentStatusConfig[status].label`. Picks up label change automatically; no edit needed. Verify with a render test.
- `frontend/src/features/sales/types/pipeline.ts` (lines 50–91) — `SALES_STATUS_CONFIG`. Static label per status. `estimate_scheduled` currently labels "Estimate Scheduled". You will NOT mutate this map; instead, add a helper `getSalesStatusLabel(entry, latestEvent?)` next to it.
- `frontend/src/features/sales/types/pipeline.ts` (lines 116–136) — `SalesCalendarEvent` type. Confirms `confirmation_status: SalesCalendarEventConfirmationStatus` and the four values: `'pending' | 'confirmed' | 'reschedule_requested' | 'cancelled'`.
- `frontend/src/features/sales/components/SalesPipeline.tsx` (lines 273–327, specifically 311–316) — `PipelineRow` label render.
- `frontend/src/features/sales/components/SalesDetail.tsx` (lines 356–357 and 523–525 per Explore agent) — sales detail label render. Uses `SALES_STATUS_CONFIG[entry.status].label` today.

**Frontend (tech-mobile banner)**

- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` (lines 1–98) — 3-card workflow row. **The component to modify.** Line 26: `TERMINAL_STATUSES` array. Line 40: terminal early-return. Line 42–47: `cardState` derivation. The new "awaiting confirmation" branch lives at line 40–41 (insert *before* the terminal check, since `'scheduled'` is non-terminal).
- `frontend/src/features/schedule/components/AppointmentModal/ActionCard.tsx` (lines 1–83) — Individual button. No edit; just confirms how state is rendered.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 512–518) — Renders `<ActionTrack appointmentId={…} status={appointment.status} … />`. No edit; confirms ActionTrack's status input.
- `frontend/src/shared/components/ui/alert.tsx` (lines 1–130) — Shared `Alert`, `AlertIcon`, `AlertTitle`, `AlertDescription` primitives. **Use these for the new banner.** Variants: `info` (lines 80–88 + variant tokens) is the right choice.
- `frontend/src/features/schedule/hooks/useModalState.ts` (lines 17–31) — `deriveStep` helper. Confirms `scheduled` and `confirmed` both map to step 0 today — that is why ActionTrack renders disabled cards at `'scheduled'`. After our change, ActionTrack will short-circuit before reaching `deriveStep` for `'scheduled'`.

**Frontend (canonical on-the-way migration)**

- `frontend/src/features/jobs/hooks/useJobMutations.ts` (lines 137–146) — `useOnMyWay()` hook. Takes a `jobId: string`, returns a `Job` mutation. Re-exported from `frontend/src/features/jobs/hooks/index.ts:22` and `frontend/src/features/jobs/index.ts:65`.
- `frontend/src/features/jobs/api/jobApi.ts` (lines 145–147) — `jobApi.onMyWay(id)` API client. POST to `${BASE_PATH}/${id}/on-my-way`.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts` (lines 180–193) — `useMarkAppointmentEnRoute`. **To deprecate.** Stop exporting; leave file behavior for one release if you must, but the cleanest move is delete.
- `frontend/src/features/schedule/hooks/index.ts:24` — re-export line for the deprecated hook. Remove.
- `frontend/src/features/schedule/index.ts:50` — feature-level re-export. Remove.
- `frontend/src/features/schedule/components/StaffWorkflowButtons.tsx` (lines 1–126) — **Callsite #1.** Line 28: `const enRouteMutation = useMarkAppointmentEnRoute();`. Line 32–39: handler. Migrate to `useOnMyWay`, pass `job.id` instead of `appointmentId`. Component currently does not receive `jobId` as a prop; add one and have the parent pass it down (AppointmentModal already has `job.id` via appointment.job_id, which is on the appointment response — see `Appointment` type at `frontend/src/features/schedule/types/index.ts:66–97`).
- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` — **Callsite #2.** Line 36 currently uses `useMarkAppointmentEnRoute`. Migrate to `useOnMyWay`. Component currently takes `appointmentId`; add a `jobId` prop and have `AppointmentModal.tsx` pass `appointment.job_id`.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 512–518) — pass `jobId={appointment.job_id}` to `<ActionTrack>`.
- `frontend/src/features/schedule/components/StaffWorkflowButtons.test.tsx` (line 14) and `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.test.tsx` (line 21) — mock the deprecated hook. Update mocks to mock `useOnMyWay` from the jobs feature instead.
- `frontend/src/features/jobs/components/OnSiteOperations.tsx` (lines 22, 37) — Already uses `useOnMyWay` correctly; no edit. Reference for the prop-passing pattern.

**Frontend (DayMode slot-pick port)**

- `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx` (lines 1–387) — **Source of the interaction pattern.** Critical sections:
  - Props (lines 20–33).
  - Slot-grid layout (lines 73–80) using constants from `lib/scheduleVisitUtils`.
  - Mouse handlers (lines 92–143): `onSlotMouseDown`, `onMove`, `onUp`. State shape lines 35–40.
  - Drag-vs-click branching (lines 119–139): `moved === false` → `onSlotClick`; `moved === true` → `onSlotDrag`.
  - End time is exclusive: `s2 = max(startSlot, curSlot) + 1` (line 127).
- `frontend/src/features/sales/lib/scheduleVisitUtils.ts` (lines 1–123) — Exports: `HOUR_START=6`, `HOUR_END=20`, `SLOT_MIN=30`, `SLOT_PX=22`, `HEADER_PX=29`, `TIMECOL_PX=56`, `SLOTS_PER_DAY=28`; helpers `minToHHMMSS`, `hhmmssToMin`, `iso`, `fmtHM`, `fmtDur`, `isPastSlot`, `eventToBlock`, `detectConflicts`, `formatShortName`.
- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx` (lines 1–375) — **The target.** Already has:
  - `LANE_HEIGHT_PX=38`, `CARD_HEIGHT_PX=36`, `SNAP_MINUTES=15`, `DAY_START_MIN=360 (6am)`, `DAY_END_MIN=1200 (8pm)`, `HOUR_TICKS` (lines 52–69).
  - `handleRowDrop` for moving existing appointments (lines 137–212) — **leave this alone**.
  - `handleDragOver` (lines 132–135) — leave alone.
  - Existing `onEmptyCellClick(staffId, dateStr)` wired to a create flow (per Explore agent).
  - 15-min snap precision (line 156–157) — keep.
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx` (lines 163–204) — Same drag-drop pattern; also needs `suppress_notifications: true` in its `handleCellDrop` mutation payload. **Same change as DayMode for Item 1.**
- `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.tsx` (lines 140–150) — Drag-start handler; sets `DragPayload`. Read for context.
- `frontend/src/features/schedule/components/ResourceTimelineView/types.ts` (lines 40–49) — `DragPayload` interface. No edit.
- `frontend/src/features/schedule/components/ResourceTimelineView/utils.ts` — `timeToMinutes`, `minutesToTimeString`, `assignLanes`, `minutesToPercent`. Reuse for the new mouse-drag conversion math.
- `frontend/src/features/schedule/components/ResourceTimelineView/index.tsx` (verified lines 1–183) — orchestrator. Today: `handleEmptyCellClick` (lines 92–97) just forwards `(staffId, date)` to the parent's `onDateClick` prop (lines 28–31). **It does NOT accept a time range.** To wire Item 4, add a NEW prop `onSlotRangePick?: (staffId: string, date: Date, startMin: number, endMin: number) => void` to `ResourceTimelineViewProps`, plumb it down as a new prop to `<DayMode>` at line 167–172, and let the parent (`SchedulePage.tsx`) decide how to open the create-appointment dialog with the pre-filled range.
- `frontend/src/features/schedule/components/SchedulePage.tsx` (line 31 import; line 496 render) — sole parent of `<ResourceTimelineView>`. Add an `onSlotRangePick` callback here that opens the existing create-appointment dialog with `defaultStartTime`/`defaultEndTime`/`defaultStaffId` pre-filled. Read the existing dialog's prop signature before wiring; if it doesn't accept time defaults, extend it.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts` (lines 18–35 for create, 37–61 for update) — `useCreateAppointment` will be called by the new drag-create flow (existing pattern; nothing new needed).

**Backend (sales pipeline list response)**

- `src/grins_platform/schemas/sales_pipeline.py` (lines 34–65) — `SalesEntryResponse` already has denormalized fields (`customer_name`, `customer_phone`, `customer_tags`, `property_address`, `job_type_display`). **Add one more**: `latest_event_confirmation_status: Optional[str] = None`. This is a response-schema change only — not a DB schema migration — consistent with the user's "pure frontend — no schema change" intent (no Alembic migration involved).
- `src/grins_platform/services/sales_pipeline_service.py` — Grep for the list-entries method (likely `list_entries`, `get_pipeline`, or similar). Populate `latest_event_confirmation_status` by joining on the latest `SalesCalendarEvent` for each entry (ordered by `scheduled_date DESC` + `created_at DESC`, LIMIT 1). Use a correlated subquery or selectinload + Python-side last-event picker — pick whichever matches the existing patterns in that service.

**Backend tests to update**

- `src/grins_platform/tests/unit/test_appointment_service.py` (or equivalent file path under `tests/unit/`; grep before editing) — add tests for `suppress_notifications=True` path: assert SMS dispatch is skipped AND status still demotes CONFIRMED→SCHEDULED.
- `src/grins_platform/tests/integration/test_appointment_routes.py` (or equivalent; grep) — PUT `/appointments/{id}` with `suppress_notifications=true` returns 200 and no SMS attempted.
- `src/grins_platform/tests/functional/test_sales_pipeline_functional.py` (or unit equivalent — grep) — assert list response includes `latest_event_confirmation_status` populated from the latest `SalesCalendarEvent` (or `None` when none exists).

**Frontend tests to update**

- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx` — assert the existing drag-drop mutation payload now includes `suppress_notifications: true`.
- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.test.tsx` — add a test for the new "Awaiting confirmation" banner render path (status='scheduled'); ensure no buttons rendered.
- `frontend/src/features/schedule/components/StaffWorkflowButtons.test.tsx` — update the hook mock from `useMarkAppointmentEnRoute` → `useOnMyWay`; ensure clicking calls the new hook with `jobId`.

### New Files to Create

- **None** for items 1–3, 5. All edits are in place.
- **Optional (Item 4)**: `frontend/src/features/schedule/components/ResourceTimelineView/EmptyCellDragLayer.tsx` — a new local component that wraps the empty-strip mouse handlers, returns the drag preview rectangle, and emits `onSlotPick({ staffId, date, startMin, endMin })`. Keeps `DayMode.tsx` from ballooning. If lift cost is high, inline in DayMode instead — judgment call at implementation time.
- `e2e-screenshots/cluster-d-scheduling-confirmations/` — output directory for E2E screenshots (auto-created by `/e2e-test` skill; listed here for completeness).

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [TanStack Query — Mutations](https://tanstack.com/query/v5/docs/framework/react/guides/mutations)
  - Section: `useMutation` `onSuccess` invalidation patterns.
  - Why: All callsite migrations rely on understanding existing TanStack invalidation; do NOT remove `appointmentKeys` invalidations when switching to job-side hook unless you also need a job-keys invalidation in their place.
- [FastAPI — Request Body](https://fastapi.tiangolo.com/tutorial/body/)
  - Section: optional fields, default values.
  - Why: Adding `suppress_notifications: bool = False` to a Pydantic schema must keep all existing clients (which don't send the field) working unchanged.
- [Pydantic v2 — `model_dump(exclude_unset=True)`](https://docs.pydantic.dev/latest/concepts/serialization/#modeldumpexclude-unset)
  - Section: exclude-unset semantics.
  - Why: `appointment_service.py:435` uses `data.model_dump(exclude_unset=True)`. The new flag must NOT be passed into the repository update (it isn't an Appointment column). Extract it from `data` before the dump, or drop it from the dumped dict before passing to repository.
- [WebAuthn / WebAuthn-like? — N/A] — no third-party feature spec relevant for this cluster.
- Project memory: `feedback_no_remote_alembic.md` — no schema changes in this cluster, so no migration concern; just be aware if you ever pivot to add a real DB field.
- Project memory: `feedback_test_recipients_prod_safety.md` — E2E must use `email=kirillrakitinsecond@gmail.com` and `phone=+19527373312` only.

### Patterns to Follow

**Naming Conventions (Python backend)**

```python
# src/grins_platform/services/appointment_service.py:400-407
async def update_appointment(
    self,
    appointment_id: UUID,
    data: AppointmentUpdate,
    *,
    actor_id: UUID | None = None,
    notify_customer: bool = True,  # <-- existing flag; reuse this
) -> Appointment:
```

`notify_customer` is the existing convention. The new schema field should map onto it semantically (`suppress_notifications=True` ↔ `notify_customer=False`).

**Pydantic schema additions (backwards-compatible)**

```python
# src/grins_platform/schemas/appointment.py:51-64
class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment.

    Validates: Admin Dashboard Requirement 1.2
    """
    staff_id: Optional[UUID] = Field(None, description="Assigned staff member ID")
    scheduled_date: Optional[date] = Field(None, description="Appointment date")
    # ...
    # NEW (additive, defaults False, existing clients unaffected):
    suppress_notifications: bool = Field(
        default=False,
        description=(
            "When True, skip the reschedule SMS that would otherwise fire on "
            "date/time change. Used by drag-drop on the schedule board where "
            "the admin will explicitly click Send afterwards."
        ),
    )
```

**Endpoint passthrough**

```python
# src/grins_platform/api/v1/appointments.py:1106-1110
result = await service.update_appointment(
    appointment_id,
    data,
    actor_id=current_user.id,
    notify_customer=not data.suppress_notifications,  # <-- new line
)
```

**Service extracts the non-column flag before model_dump (defensive)**

```python
# src/grins_platform/services/appointment_service.py:435 (modify)
update_data = data.model_dump(exclude_unset=True, exclude={"suppress_notifications"})
```

Use `exclude={"suppress_notifications"}` so the flag doesn't leak into the `update_data` dict passed to the repository (which writes Appointment columns).

**Frontend status-label config (single source of truth)**

```ts
// frontend/src/features/schedule/types/index.ts:182-201
export const appointmentStatusConfig: Record<...> = {
  // ...
  scheduled: {
    label: 'Awaiting confirmation',  // <-- was 'Scheduled'
    color: 'text-amber-800',         // <-- bump to a "waiting" tone; amber is the project's wait color (verify against tailwind.config.js + alert.tsx info variant)
    bgColor: 'bg-amber-100',
  },
  confirmed: {
    label: 'Scheduled',              // <-- was 'Confirmed'
    color: 'text-blue-800',
    bgColor: 'bg-blue-100',
  },
  // ...
};
```

Note: `AppointmentList.getStatusLabel` (`AppointmentList.tsx:73–92`) has its own switch and currently returns 'Scheduled' for `'confirmed'`. Either route it through `appointmentStatusConfig[status].label` (cleaner) or update both `scheduled` and `confirmed` arms in the switch.

**Sales status label helper (handle confirmation_status branching)**

The helper accepts a plain string for the latest event's confirmation status — that way the same function works for the list view (using the new denormalized `entry.latest_event_confirmation_status` field) and for the detail view (using `currentEvent.confirmation_status`):

```ts
// frontend/src/features/sales/types/pipeline.ts (add helper next to SALES_STATUS_CONFIG)
export function getSalesStatusLabel(
  entry: { status: SalesEntryStatus },
  latestEventConfirmationStatus?: SalesCalendarEventConfirmationStatus | string | null,
): string {
  if (entry.status === 'estimate_scheduled') {
    return latestEventConfirmationStatus === 'confirmed' ? 'Scheduled' : 'Awaiting confirmation';
  }
  return SALES_STATUS_CONFIG[entry.status]?.label ?? entry.status;
}
```

Wire into the two render sites:
- `SalesPipeline.tsx:311–316` (list view): pass `entry.latest_event_confirmation_status` — the new denormalized field added to `SalesEntryResponse` (see Backend block above). Also add the field to the frontend `SalesEntry` TS type at `frontend/src/features/sales/types/pipeline.ts:13–36`.
- `SalesDetail.tsx:523–525` (detail view): pass `currentEvent?.confirmation_status` — `currentEvent` is already in scope (per Explore agent finding lines 523–525) and is typed as `SalesCalendarEvent | null` with `confirmation_status: SalesCalendarEventConfirmationStatus` at `pipeline.ts:132`.

**Banner pattern (ActionTrack)**

```tsx
// frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx:67-97 (replace return)
import { Alert, AlertIcon, AlertTitle, AlertDescription } from '@/shared/components/ui/alert';
import { Info } from 'lucide-react';

// ...inside ActionTrack, before TERMINAL_STATUSES check:
const AWAITING_STATUSES: AppointmentStatus[] = ['scheduled', 'pending', 'draft'];
if (status === 'scheduled') {
  return (
    <div className="px-3 sm:px-5 pb-4">
      <Alert variant="info" data-testid="awaiting-confirmation-banner">
        <AlertIcon><Info /></AlertIcon>
        <AlertTitle>Waiting for customer confirmation</AlertTitle>
        <AlertDescription>
          On My Way, Job Started, and Job Complete unlock once the customer replies <strong>Y</strong> to the confirmation text.
        </AlertDescription>
      </Alert>
    </div>
  );
}
if (TERMINAL_STATUSES.includes(status)) return null;
// ...existing 3-card render
```

Verify the actual `Alert` API by reading `frontend/src/shared/components/ui/alert.tsx:1–130` first — variants are `default`, `warning`, `error`, `success`, `info` per Explore findings.

**StaffWorkflowButtons — same pattern at the parent level**

`StaffWorkflowButtons.tsx:23–27` accepts `appointmentId, status, hasPaymentOrInvoice`. Add `jobId: string` to props and switch `useMarkAppointmentEnRoute → useOnMyWay`. `handleOnMyWay` (lines 32–39) calls `enRouteMutation.mutateAsync(appointmentId)` today → switch to `onMyWayMutation.mutateAsync(jobId)`. There is exactly **one** render site: `frontend/src/features/schedule/components/AppointmentDetail.tsx:690–694`. The `appointment` object is already in scope at that callsite (verified — `appointment.status` is passed today), so add `jobId={appointment.job_id}` to the props.

**Daily slot-pick state shape (port from WeekCalendar)**

```ts
type EmptyDragState = {
  staffId: string;
  startMin: number;
  curMin: number;
  moved: boolean;
};
```

Snap `curMin` to `SNAP_MINUTES` (15) on every move; on `mouseup`, compute `(startMin = min(start, cur), endMin = max(start, cur) + SNAP_MINUTES)` to preserve the "exclusive end" semantics from WeekCalendar:127. Click (no move) yields `endMin = startMin + DEFAULT_NEW_APPT_MINUTES` (pick 60 to match WeekCalendar's `useScheduleVisit` default; verify by reading `useScheduleVisit.ts`).

**Drag preview overlay**

```tsx
{dragState && dragState.moved && (
  <div
    className="absolute bg-blue-200/60 border border-dashed border-blue-500 rounded-md pointer-events-none"
    style={{
      left: `${minutesToPercent(Math.min(dragState.startMin, dragState.curMin), DAY_START_MIN, DAY_SPAN_MIN)}%`,
      width: `${minutesToPercent(Math.abs(dragState.curMin - dragState.startMin) + SNAP_MINUTES, 0, DAY_SPAN_MIN)}%`,
      top: 2,
      height: CARD_HEIGHT_PX,
    }}
  />
)}
```

Drawn at the same z-layer as appointment cards; non-interactive (`pointer-events-none`).

---

## IMPLEMENTATION PLAN

### Phase 1: Backend — Add `suppress_notifications` passthrough

Foundation for Item 1. Pure additive change; no migration; no behavior change for existing callers.

**Tasks:**

- Extend `AppointmentUpdate` schema with optional `suppress_notifications: bool = False`.
- Modify `update_appointment` service to skip `_send_reschedule_sms` when `notify_customer=False`. (Already gated; just confirm the gate handles the new path correctly.)
- Pass `notify_customer=not data.suppress_notifications` through the PUT endpoint.
- Extract `suppress_notifications` from the dumped update_data before repository write.
- Add a unit test that asserts SMS dispatch is skipped and audit log still records the change.

### Phase 2: Frontend — Status labels (Item 2)

Pure cosmetic. Two label edits in `appointmentStatusConfig`; one helper for sales pipeline; switch in `AppointmentList`.

**Tasks:**

- Update `appointmentStatusConfig.scheduled.label` to "Awaiting confirmation"; bump color tokens if needed.
- Update `appointmentStatusConfig.confirmed.label` to "Scheduled".
- Update `AppointmentList.getStatusLabel` to add a `case 'scheduled': return 'Awaiting confirmation';` branch (or route through the config map).
- Add `getSalesStatusLabel` helper to `frontend/src/features/sales/types/pipeline.ts`.
- Wire helper into `SalesPipeline.tsx` row render and `SalesDetail.tsx` header render.
- Verify all tests in `frontend/src/features/schedule/` that snapshot or assert "Scheduled" / "Confirmed" strings still pass; update fixtures where needed.

### Phase 3: Frontend — Tech-mobile banner (Item 3)

Wire the shared `<Alert>` component into ActionTrack's pre-confirmed branch.

**Tasks:**

- Import `Alert`, `AlertIcon`, `AlertTitle`, `AlertDescription` from `@/shared/components/ui/alert`.
- Add an early return in `ActionTrack` before the `TERMINAL_STATUSES` check: when `status === 'scheduled'`, render the banner; do not render the 3 cards.
- Optionally apply the same gate to `StaffWorkflowButtons.tsx` if it renders pre-confirmed (today the buttons only render at `confirmed`/`en_route`/`in_progress`; the banner is more critical in ActionTrack). Decision: skip StaffWorkflowButtons for this item — its current behavior already hides pre-confirmed.
- Add a render test for the banner case.

### Phase 4: Frontend — Canonical on-the-way hook (Item 5)

Migrate two callsites. Remove the deprecated hook from exports.

**Tasks:**

- In `StaffWorkflowButtons.tsx`, add `jobId: string` to props; replace `useMarkAppointmentEnRoute` with `useOnMyWay`; pass `jobId` to `mutateAsync`. Find every render site of `<StaffWorkflowButtons>` and add `jobId={appointment.job_id}` (or `job.id` in job contexts). Grep for `<StaffWorkflowButtons` to enumerate.
- In `ActionTrack.tsx`, add `jobId: string` to props; replace `useMarkAppointmentEnRoute` with `useOnMyWay`; pass `jobId`. In `AppointmentModal.tsx:512–518`, add `jobId={appointment.job_id}` to the `<ActionTrack>` element.
- Remove the `useMarkAppointmentEnRoute` export line from `frontend/src/features/schedule/hooks/index.ts` (line 24).
- Remove the `useMarkAppointmentEnRoute` export line from `frontend/src/features/schedule/index.ts` (line 50).
- Update test mocks in `StaffWorkflowButtons.test.tsx:14` and `ActionTrack.test.tsx:21` to mock `useOnMyWay` from the jobs feature path.
- Leave `appointmentApi.markEnRoute` defined for now — flag for follow-up cleanup. Add a `// @deprecated — replaced by job-side on-my-way; remove after one release` comment above the function in `appointmentApi.ts:205–207`.

### Phase 5: Frontend + Backend — Drag-drop suppress SMS (Item 1)

Smallest mechanical change with the biggest behavior delta. Wire the new `suppress_notifications` flag through.

**Tasks:**

- In `frontend/src/features/schedule/types/index.ts:108–117` (`AppointmentUpdate` TS interface), add `suppress_notifications?: boolean;`.
- In `DayMode.tsx:186-194`, add `suppress_notifications: true` to the `data` object passed to `updateAppointment.mutateAsync`.
- In `WeekMode.tsx:184–190`, add `suppress_notifications: true` to its mutation payload.
- Confirm via test: drop-on-DayMode mutation payload now carries the flag.
- Add an integration test that hits PUT `/appointments/{id}` with `suppress_notifications=true` from a CONFIRMED state, asserts: (a) status becomes SCHEDULED, (b) NO `_send_reschedule_sms` log line emitted, (c) audit log row written.

### Phase 6: Frontend — Daily slot-pick UX port (Item 4)

The biggest single piece. Adds a brand-new interaction to `DayMode`. Self-contained; doesn't depend on phases 1–5.

**Tasks:**

- Read `WeekCalendar.tsx:92–143` and `scheduleVisitUtils.ts` end-to-end. Trace one click and one drag through the parent `useScheduleVisit` hook to understand the `(date, startMin, endMin)` payload contract.
- In `DayMode.tsx`, add a `dragState: EmptyDragState | null` useState and a `dragRef` mirror (the stale-closure pattern from WeekCalendar lines 91 + 119–139 is required).
- Wire `onMouseDown` on each tech strip's empty area (in the existing `.relative` drop zone container at `DayMode.tsx:313–368`). Guard: skip if the click target is an existing `<AppointmentCard>` (event bubbling).
- Wire global `mousemove` and `mouseup` listeners that update `dragState.curMin` snapped to `SNAP_MINUTES` and finalize on release.
- On finalize: if `dragState.moved`, call `onSlotPick({ staffId, date: dateStr, startMin, endMin })`; if not moved, call `onSlotPick({ staffId, date: dateStr, startMin, endMin: startMin + 60 })`.
- The parent `ResourceTimelineView/index.tsx` orchestrator routes `onSlotPick` into the existing create-appointment dialog (it already does this for `onEmptyCellClick`; extend to accept range).
- Render the dashed drag preview rectangle while `dragState.moved && dragState !== null`.
- Guard: drop into the past should be rejected, matching WeekCalendar's `isPastSlot` behavior. Reuse `isPastSlot` from `scheduleVisitUtils` OR write a local equivalent (avoid the import cross-feature; copy is fine — it's 5 lines).
- Add unit tests for the drag math (start>cur and start<cur both produce a valid range; click without movement defaults to 60 min).
- Add a render test asserting the preview rectangle appears during drag.

### Phase 7: Testing & Validation

Run the full unit + integration + frontend test suites. Fix any snapshot drift from the label change.

**Tasks:**

- `uv run pytest src/grins_platform/tests/unit/test_appointment_service.py -v` — new `suppress_notifications` tests green.
- `uv run pytest src/grins_platform/tests/integration/ -v -k appointment` — PUT endpoint integration test green.
- `cd frontend && npm test -- --run` — full Vitest pass.
- `cd frontend && npm run lint && npm run typecheck` — green.
- `uv run ruff check src/grins_platform && uv run mypy src/grins_platform` — green.

### Phase 8 (MANDATORY): E2E Validation Against Dev Vercel + Dev Railway

After implementation is complete, the executing agent MUST invoke the `e2e-test` skill (`.claude/skills/e2e-test/SKILL.md`) targeting:

- Dev Vercel admin dashboard URL: `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`
- Dev Railway API/backend URL: `https://grins-dev-dev.up.railway.app`
- Dev Railway Postgres: read `DATABASE_URL` from Railway dev env via `mcp__railway__list-variables` (or `railway variables --service <backend>`). Never read from local `.env`. Never apply alembic from local — there are no migrations in this cluster, but the rule stands for any incidental schema work.

(The marketing/landing site is NOT touched by this cluster — skip the `Grins_irrigation` Vercel URL.)

**Tasks:**

- Run `/e2e-test` and let it spawn its three research sub-agents (structure, schema, bugs).
- Exercise every user journey this cluster affects (enumerated in VALIDATION COMMANDS Level 5 below).
- Query the dev Railway database with the validation SQL listed in VALIDATION COMMANDS Level 5 to confirm record state.
- Capture screenshots to `e2e-screenshots/cluster-d-scheduling-confirmations/` at desktop, tablet, and mobile viewports.
- Use ONLY the hardcoded safe recipients: `kirillrakitinsecond@gmail.com` / `+19527373312`.
- Stop the dev server and close the browser session afterward.
- Block PR/merge until every E2E journey passes green.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **REFACTOR**: Restructure without changing behavior
- **MIRROR**: Copy pattern from elsewhere in codebase

---

### Task 1: UPDATE `src/grins_platform/schemas/appointment.py`

- **IMPLEMENT**: Add `suppress_notifications: bool = Field(default=False, description="…")` to `AppointmentUpdate` (after `estimated_arrival`, line 64).
- **PATTERN**: Mirror the existing optional-field shape at `schemas/appointment.py:51–64`. Use `Field(default=False, …)` (not `Optional[bool] = None`) so the flag is always present with a safe default.
- **IMPORTS**: No new imports — `BaseModel`, `Field`, `Optional`, `UUID`, `date`, `time`, `AppointmentStatus` all already imported.
- **GOTCHA**: This is NOT an Appointment-column field — it must be excluded from the dumped dict before reaching the repository (Task 3).
- **VALIDATE**: `uv run ruff check src/grins_platform/schemas/appointment.py && uv run python -c "from src.grins_platform.schemas.appointment import AppointmentUpdate; m = AppointmentUpdate(suppress_notifications=True); assert m.suppress_notifications is True; m2 = AppointmentUpdate(); assert m2.suppress_notifications is False; print('ok')"`

### Task 2: UPDATE `src/grins_platform/services/appointment_service.py` (extract flag from dump)

- **IMPLEMENT**: On line 435, change `update_data = data.model_dump(exclude_unset=True)` to `update_data = data.model_dump(exclude_unset=True, exclude={"suppress_notifications"})`. This keeps `suppress_notifications` out of the repository-bound dict.
- **PATTERN**: Pydantic's `exclude={…}` argument on `model_dump`. See docs link above.
- **IMPORTS**: None new.
- **GOTCHA**: Be careful — `exclude_unset=True` + `exclude={"suppress_notifications"}` compose correctly (both filters apply). Verify with a quick REPL run.
- **VALIDATE**: `uv run python -c "from src.grins_platform.schemas.appointment import AppointmentUpdate; m = AppointmentUpdate(suppress_notifications=True, notes='x'); d = m.model_dump(exclude_unset=True, exclude={'suppress_notifications'}); assert 'suppress_notifications' not in d; assert d == {'notes': 'x'}; print('ok')"`

### Task 3: UPDATE `src/grins_platform/api/v1/appointments.py` (passthrough)

- **IMPLEMENT**: Modify `update_appointment` route (lines 1091–1110) to pass `notify_customer=not data.suppress_notifications` into `service.update_appointment(...)`.
- **PATTERN**: Existing call at `appointments.py:1106-1110` already passes `actor_id`. Add `notify_customer` as a third keyword arg.
- **IMPORTS**: None new.
- **GOTCHA**: Keep the existing exception handling unchanged.
- **VALIDATE**: `uv run ruff check src/grins_platform/api/v1/appointments.py && uv run mypy src/grins_platform/api/v1/appointments.py`

### Task 4: UPDATE `src/grins_platform/tests/unit/test_appointment_service.py` (add test)

- **IMPLEMENT**: Add a new test `test_update_appointment_suppress_notifications_skips_sms` that:
  - Creates a CONFIRMED appointment fixture.
  - Calls `service.update_appointment(appt.id, AppointmentUpdate(scheduled_date=new_date, suppress_notifications=True), notify_customer=False)`.
  - Asserts: (a) the result's `status == "scheduled"` (demote still happens), (b) the `_send_reschedule_sms` mock was NOT called, (c) the audit log row is still written with `sms_sent=False`.
  - Also add a positive test `test_update_appointment_default_sends_sms` asserting that default `suppress_notifications=False` still fires `_send_reschedule_sms` exactly once for a CONFIRMED→reschedule path.
- **PATTERN**: Grep `tests/unit/test_appointment_service.py` for existing `test_update_appointment_*` tests; mirror their fixture setup (likely use `appointment_factory`, `mock_sms_service`, etc.). If the file doesn't exist, grep for `update_appointment` in `tests/` to find where it's currently exercised.
- **IMPORTS**: From existing test utilities — `pytest`, `pytest-asyncio`, `AppointmentUpdate`, `AppointmentStatus`.
- **GOTCHA**: The service's `_send_reschedule_sms` is on `self`, not a global — patch via `mocker.patch.object(service, "_send_reschedule_sms", new_callable=AsyncMock)` or similar. Verify by reading existing patches in nearby tests.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_appointment_service.py -v -k "suppress_notifications or default_sends_sms"`

### Task 5: UPDATE `src/grins_platform/tests/integration/test_appointment_integration.py`

- **IMPLEMENT**: Add an integration test that posts PUT `/api/v1/appointments/{id}` with `{"scheduled_date": ..., "suppress_notifications": true}` against a confirmed appointment, asserts 200, asserts no SMS log line (by mocking the SMS service or asserting on the SMS outbox table).
- **PATTERN**: Grep `tests/integration/` for `def test_update_appointment` and mirror the test setup (TestClient or httpx AsyncClient, db_session fixture).
- **IMPORTS**: Use existing test fixtures.
- **GOTCHA**: The dev DB must NOT be hit; this is a local SQLite-or-test-Postgres test. Use `--db postgres` or whatever the project's standard pytest config dictates (check `pyproject.toml` or `tests/conftest.py`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration -v -k "suppress_notifications or appointment_update"`

### Task 6: UPDATE `frontend/src/features/schedule/types/index.ts` (TS interface + label config)

- **IMPLEMENT**:
  - (a) In the `AppointmentUpdate` interface (lines 108–117), add `suppress_notifications?: boolean;`.
  - (b) Change `appointmentStatusConfig.scheduled.label` (line 193) from `'Scheduled'` to `'Awaiting confirmation'`. Optionally swap `color`/`bgColor` to amber tones (`text-amber-800` / `bg-amber-100`) to match the new "waiting" semantics. Verify Tailwind utility classes are present in the project's CSS purge config; if `text-amber-*`/`bg-amber-*` aren't already used elsewhere, fall back to the existing `text-purple-800`/`bg-purple-100` to avoid purge issues.
  - (c) Change `appointmentStatusConfig.confirmed.label` (line 198) from `'Confirmed'` to `'Scheduled'`.
- **PATTERN**: Mirror the existing record entries; do not add new keys to the `Record` shape.
- **IMPORTS**: None new.
- **GOTCHA**: Tailwind purge — if amber utilities aren't already used elsewhere, they'll be purged in prod. Grep `frontend/src/` for `text-amber-` and `bg-amber-` to confirm. Fallback: stick with purple (which is already used here).
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 7: UPDATE `frontend/src/features/schedule/components/AppointmentList.tsx` (label switch)

- **IMPLEMENT**: In `getStatusLabel` (lines 73–92), add `case 'scheduled': return 'Awaiting confirmation';` directly above the `case 'confirmed'` line. The existing `case 'confirmed': return 'Scheduled';` line stays — it already returns the right label. (Or refactor the whole function to read `appointmentStatusConfig[status]?.label ?? status` for single source of truth — cleaner but slightly higher blast radius; pick based on existing test coverage on this file.)
- **PATTERN**: Same switch shape as existing arms.
- **IMPORTS**: None new (or import `appointmentStatusConfig` if you refactor).
- **GOTCHA**: If you refactor to use the config map, check that the call site at lines 170–178 doesn't depend on any unique behavior of the switch (it doesn't appear to).
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run AppointmentList`

### Task 7b: ADD `latest_event_confirmation_status` to `SalesEntryResponse` (backend)

- **IMPLEMENT**: In `src/grins_platform/schemas/sales_pipeline.py:34–65`, after the existing denormalized fields (e.g., after `job_type_display`), add `latest_event_confirmation_status: Optional[str] = None`. In the sales-pipeline list service (grep `services/sales_pipeline_service.py` for the list-entries method), populate this from the latest `SalesCalendarEvent` per entry (ordered by `scheduled_date DESC, created_at DESC`, LIMIT 1). Use a correlated subquery via SQLAlchemy or selectinload + Python-side picker — pick whatever matches the existing patterns in that service.
- **PATTERN**: Mirror the existing denormalization of `customer_tags` and `property_address` already populated at the service layer.
- **IMPORTS**: `from grins_platform.models.sales_calendar_event import SalesCalendarEvent` (or wherever the model lives — grep to confirm).
- **GOTCHA**: Not every sales entry has a calendar event — return `None` in that case. The frontend helper handles `null` by returning the appropriate label.
- **VALIDATE**: `uv run pytest src/grins_platform/tests -v -k "sales_pipeline or sales_entries" && uv run mypy src/grins_platform/schemas/sales_pipeline.py`

### Task 7c: ADD field to frontend `SalesEntry` TS type

- **IMPLEMENT**: In `frontend/src/features/sales/types/pipeline.ts:13–36` (`SalesEntry` interface), add `latest_event_confirmation_status: string | null;`. Type as `SalesCalendarEventConfirmationStatus | null` if you want stricter typing — but the backend returns a bare string, and the helper accepts string-or-typed.
- **PATTERN**: Mirror the existing optional/nullable fields in the interface.
- **IMPORTS**: None new.
- **GOTCHA**: TypeScript's strict mode may complain if you mark this required but the backend hasn't been deployed yet during integration testing — mark as `string | null` (not optional with `?:`) since the backend will always populate the field (even as `null`).
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 8: ADD `frontend/src/features/sales/types/pipeline.ts` (sales label helper)

- **IMPLEMENT**: Add an exported function `getSalesStatusLabel(entry, latestEvent?)` after `SALES_STATUS_CONFIG` (lines 50–91). Logic per the "Patterns to Follow" snippet above. Return type `string`.
- **PATTERN**: Pure helper, no state, lives next to the config map.
- **IMPORTS**: Use the existing `SalesEntryStatus`, `SalesCalendarEventConfirmationStatus` types from the same file.
- **GOTCHA**: The helper signature accepts a plain string for the confirmation status — that way list view (using denormalized `entry.latest_event_confirmation_status` from Task 7b/7c) and detail view (using `currentEvent.confirmation_status`) share one helper.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run pipeline`

### Task 9: UPDATE `frontend/src/features/sales/components/SalesPipeline.tsx` (wire helper)

- **IMPLEMENT**: At line 311–316 (`{statusConfig?.label ?? entry.status}`), replace with `{getSalesStatusLabel(entry, entry.latest_event_confirmation_status)}`. The accessor is the new field added in Task 7b/7c.
- **PATTERN**: Import `getSalesStatusLabel` from `../types/pipeline`.
- **IMPORTS**: `import { getSalesStatusLabel } from '../types/pipeline';`
- **GOTCHA**: Don't lose the `className` style application — the label change only swaps the text, not the badge color. If you want amber styling for "Awaiting confirmation" rows, branch `statusConfig.className` similarly via a sibling helper.
- **VALIDATE**: `cd frontend && npm run typecheck && npx eslint --fix src/features/sales/components/SalesPipeline.tsx`

### Task 10: UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` (wire helper)

- **IMPLEMENT**: At lines 523–525 (`{statusConfig?.label ?? entry.status}`), replace with `{getSalesStatusLabel(entry, currentEvent?.confirmation_status)}`. `currentEvent` (`SalesCalendarEvent | null`) is already in scope per Explore findings; its `confirmation_status` is typed at `pipeline.ts:132`.
- **PATTERN**: Same as Task 9.
- **IMPORTS**: `import { getSalesStatusLabel } from '../types/pipeline';`
- **GOTCHA**: Same styling caveat as Task 9.
- **VALIDATE**: `cd frontend && npm run typecheck && npx eslint --fix src/features/sales/components/SalesDetail.tsx`

### Task 11: UPDATE `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` (banner branch)

- **IMPLEMENT**:
  - (a) Import the `Alert*` family from `@/shared/components/ui/alert` (verify the alias path from `tsconfig.json` — the actual import may be `../../../shared/components/ui/alert` if `@/` isn't aliased; Grep an existing import to confirm).
  - (b) Import `Info` from `lucide-react` (lucide is already used at line 7).
  - (c) Add `jobId: string` to `ActionTrackProps` (line 18–24).
  - (d) Replace `useMarkAppointmentEnRoute` with `useOnMyWay` (import from `@/features/jobs/hooks` or relative path). Adjust `handleEnRoute` to call `enRouteMutation.mutate(jobId, …)` (was `appointmentId`). **Note**: keep `useMarkAppointmentArrived` and `useMarkAppointmentCompleted` as-is for this cluster — the user only specified canonicalizing the on-my-way path.
  - (e) Before the `TERMINAL_STATUSES` early return (line 40), add: `if (status === 'scheduled') return <BannerComponent />;` where `BannerComponent` renders the `<Alert variant="info">` per the snippet in "Patterns to Follow".
- **PATTERN**: Banner pattern from snippet above. Mirror existing Tailwind container `px-3 sm:px-5 pb-4` for vertical rhythm.
- **IMPORTS**:
  - `import { Alert, AlertIcon, AlertTitle, AlertDescription } from '<resolved path>/shared/components/ui/alert';`
  - `import { Info } from 'lucide-react';`
  - `import { useOnMyWay } from '<resolved path>/features/jobs/hooks';`
- **GOTCHA**: `AppointmentModal.tsx:512–518` does NOT currently pass `jobId`. You must also update that callsite in Task 13. If you ship ActionTrack with a required `jobId` prop and forget to update the caller, the build breaks.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run ActionTrack`

### Task 12: UPDATE `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.test.tsx` (test mocks + new banner test)

- **IMPLEMENT**:
  - (a) Update the hook mock at line 21: replace `useMarkAppointmentEnRoute` mock with `useOnMyWay` mock (import path will move from `useAppointmentMutations` to `useJobMutations`).
  - (b) Add a new test `renders banner when status is scheduled`: render `<ActionTrack status="scheduled" appointmentId="..." jobId="..." />`, assert `screen.getByTestId('awaiting-confirmation-banner')` exists AND assert no `<ActionCard>` rendered (e.g., `queryByLabelText('Mark as on my way')` is null).
- **PATTERN**: Existing test structure in the file.
- **IMPORTS**: Match new hook path.
- **GOTCHA**: vi.mock is module-scoped — make sure you mock the right module path.
- **VALIDATE**: `cd frontend && npm test -- --run ActionTrack`

### Task 13: UPDATE `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (pass jobId)

- **IMPLEMENT**: At lines 512–518, add `jobId={appointment.job_id}` to the `<ActionTrack ...>` props.
- **PATTERN**: The `appointment` object is already in scope; it includes `job_id` per `frontend/src/features/schedule/types/index.ts:66–97`.
- **IMPORTS**: None new.
- **GOTCHA**: If `appointment.job_id` could ever be null/undefined, narrow the type or use a fallback. Read the type def to confirm it's non-nullable (it is `string`, not `string | null`, per type definition).
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 13b: UPDATE `frontend/src/features/schedule/components/AppointmentDetail.tsx` (pass jobId to StaffWorkflowButtons)

- **IMPLEMENT**: At lines 690–694, add `jobId={appointment.job_id}` to the `<StaffWorkflowButtons>` props. The `appointment` object is already in scope (its `.status` is passed today at line 692).
- **PATTERN**: Same prop-plumbing as Task 13.
- **IMPORTS**: None new.
- **GOTCHA**: This is the ONLY render site for `<StaffWorkflowButtons>` (verified via Grep). If you miss this single edit, the build fails after Task 14 makes `jobId` a required prop.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 14: UPDATE `frontend/src/features/schedule/components/StaffWorkflowButtons.tsx` (canonical hook)

- **IMPLEMENT**:
  - (a) Add `jobId: string` to `StaffWorkflowButtonsProps` (lines 17–21).
  - (b) Replace `import { useMarkAppointmentEnRoute, useMarkAppointmentArrived, useMarkAppointmentCompleted } from '../hooks/useAppointmentMutations';` with — keeping the latter two, but importing `useOnMyWay` from the jobs feature: `import { useMarkAppointmentArrived, useMarkAppointmentCompleted } from '../hooks/useAppointmentMutations';` AND `import { useOnMyWay } from '<resolved path>/features/jobs/hooks';`.
  - (c) Change `const enRouteMutation = useMarkAppointmentEnRoute();` (line 28) to `const onMyWayMutation = useOnMyWay();`.
  - (d) In `handleOnMyWay` (lines 32–39), change `await enRouteMutation.mutateAsync(appointmentId);` to `await onMyWayMutation.mutateAsync(jobId);`.
- **PATTERN**: Same pattern as ActionTrack.
- **IMPORTS**: As above.
- **GOTCHA**: The job-side `on-my-way` endpoint auto-transitions the appointment to EN_ROUTE if currently CONFIRMED or SCHEDULED (`api/v1/jobs.py:1348–1356`). So the visible status change still happens — but it now also writes `job.on_my_way_at` and fires the customer SMS. Make sure the success toast wording still makes sense ("You are now en route.").
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run StaffWorkflowButtons`

### Task 15: UPDATE `frontend/src/features/schedule/components/StaffWorkflowButtons.test.tsx` (mock update)

- **IMPLEMENT**: Update the mock at line 14: replace `useMarkAppointmentEnRoute: ...` with `useOnMyWay: () => ({ mutateAsync: mockOnMyWayMutate, isPending: false })`. Update import path.
- **PATTERN**: Mirror existing mock shape.
- **IMPORTS**: Match new hook path.
- **GOTCHA**: Same as Task 12.
- **VALIDATE**: `cd frontend && npm test -- --run StaffWorkflowButtons`

### Task 16: REMOVE deprecated hook exports

- **IMPLEMENT**:
  - (a) In `frontend/src/features/schedule/hooks/index.ts`, delete the line at index 24 that re-exports `useMarkAppointmentEnRoute`.
  - (b) In `frontend/src/features/schedule/index.ts`, delete the line at index 50 that re-exports it.
  - (c) In `frontend/src/features/schedule/hooks/useAppointmentMutations.ts:180–193`, add `// @deprecated — use useOnMyWay (job-side). Scheduled for removal after one release.` above the hook. Do NOT delete the implementation yet — leave it for one release in case any out-of-tree consumer (mobile app prototype?) imports it.
  - (d) In `frontend/src/features/schedule/api/appointmentApi.ts:205–207`, add `// @deprecated — see useOnMyWay migration` comment above `markEnRoute`.
- **PATTERN**: Standard deprecation comment.
- **IMPORTS**: N/A (removals).
- **GOTCHA**: Make sure no other file imports `useMarkAppointmentEnRoute` from the deleted re-export path. Grep first: `grep -r "useMarkAppointmentEnRoute" frontend/src/` — should only find the hook definition and the two test files (already updated).
- **VALIDATE**: `cd frontend && npm run typecheck && npm run build`

### Task 17: UPDATE `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx` (suppress SMS)

- **IMPLEMENT**: At lines 186–194, add `suppress_notifications: true` to the `data:` object passed to `updateAppointment.mutateAsync`.
- **PATTERN**: TypeScript object spread; preserves existing fields.
- **IMPORTS**: None new (the TS interface change in Task 6 makes the field accepted).
- **GOTCHA**: `WeekMode.tsx` needs the same edit (Task 18). If you change only DayMode, week-view drags still text customers.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run DayMode`

### Task 18: UPDATE `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx` (suppress SMS)

- **IMPLEMENT**: At lines 184–190, add `suppress_notifications: true` to the `data:` object.
- **PATTERN**: Same as Task 17.
- **IMPORTS**: None new.
- **GOTCHA**: Same as Task 17.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run WeekMode`

### Task 19: UPDATE `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx` (assertion)

- **IMPLEMENT**: Add an assertion to the existing drag-drop test (or create one if missing): after a drag-drop, the mocked `updateAppointment` mutation was called with an object whose `data.suppress_notifications === true`.
- **PATTERN**: Use the existing mutation mock fixture; inspect call args with `expect(updateAppointment).toHaveBeenCalledWith(expect.objectContaining({ data: expect.objectContaining({ suppress_notifications: true }) }))`.
- **IMPORTS**: As in existing tests.
- **GOTCHA**: If the existing test doesn't drive a full drag-drop (just renders), you'll need to fire `dragStart`/`drop` events via `@testing-library/user-event`'s `dataTransfer` mock — read `AppointmentCard.tsx:140–150` to construct the right payload.
- **VALIDATE**: `cd frontend && npm test -- --run DayMode`

### Task 20: UPDATE `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx` (slot-pick UX port)

- **IMPLEMENT**: Add empty-strip mouse handlers per Phase 6 "Tasks" + the snippets in "Patterns to Follow":
  - `useState<EmptyDragState | null>(null)` + `useRef` mirror.
  - `onMouseDown` on each tech-row drop zone (`<div className="relative …">` at lines 313–368). Skip if `e.target.closest('[data-appointment-card]')` returns truthy (so dragging a card doesn't trigger a new-block drag — verify the card root has a stable `data-` attribute by reading `AppointmentCard.tsx`).
  - Global `mousemove` + `mouseup` listeners attached via `useEffect` while `dragState !== null`.
  - On `mouseup` with `dragState.moved === false`, call `onSlotPick({ staffId, date, startMin: dragState.startMin, endMin: dragState.startMin + 60 })`.
  - On `mouseup` with `dragState.moved === true`, call `onSlotPick({ staffId, date, startMin: min(start, cur), endMin: max(start, cur) + SNAP_MINUTES })`.
  - Render the dashed preview rectangle while `dragState !== null && dragState.moved`.
  - `onSlotPick` is a new prop on `DayMode`; parent orchestrator wires it to the existing create-appointment dialog.
- **PATTERN**: `WeekCalendar.tsx:92–143`, but adapted for percentage-based positioning instead of slot-grid.
- **IMPORTS**: `useEffect`, `useRef` from React (likely already imported).
- **GOTCHA**:
  - Use `dragRef.current` in the `mousemove`/`mouseup` handlers, NOT the stale `dragState` closure. Same trick WeekCalendar uses at line 119.
  - Past-time guard: reject drags whose start is before `Date.now()` for today's date.
  - Don't break the existing `handleRowDrop` for existing-card drag-and-drop — different code path; ensure HTML5 drag events (`dragstart`, `drop`) and mouse events (`mousedown`, `mousemove`, `mouseup`) don't collide.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run DayMode`

### Task 21: UPDATE `ResourceTimelineView/index.tsx` + `SchedulePage.tsx` (wire onSlotRangePick)

- **IMPLEMENT**:
  - (a) In `frontend/src/features/schedule/components/ResourceTimelineView/index.tsx` (verified lines 27–39 + 166–172), add a new optional prop to `ResourceTimelineViewProps`: `onSlotRangePick?: (staffId: string, date: Date, startMin: number, endMin: number) => void`. Plumb it down to `<DayMode>` at line 167 as `onSlotRangePick={onSlotRangePick}`.
  - (b) In `DayMode.tsx` (the Task 20 changes), accept `onSlotRangePick` as a new prop and call it from the mouse-up handler with the resolved `(staffId, parseISO(dateStr), startMin, endMin)` payload.
  - (c) In `frontend/src/features/schedule/components/SchedulePage.tsx` (line 31 import; line 496 render), add an `onSlotRangePick` callback handler that opens the existing create-appointment dialog with `defaultStartTime`/`defaultEndTime`/`defaultStaffId`/`defaultScheduledDate` pre-filled. Read the dialog's actual prop signature first; if it doesn't accept defaults, extend it (separate component edit, mirrored on whatever the existing `onDateClick` flow already supports).
- **PATTERN**: Mirror the existing `onEmptyCellClick`/`onDateClick` wiring at `ResourceTimelineView/index.tsx:92–97` and `SchedulePage.tsx:496`.
- **IMPORTS**: None new in `ResourceTimelineView/index.tsx`; in `SchedulePage.tsx`, whatever dialog component is already imported.
- **GOTCHA**: `onDateClick` today takes `(staffId: string | null, date: Date)` — do NOT widen its signature; add a SEPARATE callback so existing tests don't churn. Verify the SchedulePage test mock at `SchedulePage.test.tsx:19` still passes.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- --run SchedulePage`

### Task 22: ADD unit tests for DayMode slot-pick drag math

- **IMPLEMENT**: In `DayMode.test.tsx`, add tests for:
  - Click without movement → onSlotPick called with `(startMin, startMin + 60)`.
  - Drag forward (start < cur) → onSlotPick called with `(startMin, curMin + SNAP_MINUTES)`.
  - Drag backward (start > cur) → onSlotPick called with `(curMin, startMin + SNAP_MINUTES)`.
  - Past-time drag → no onSlotPick call; toast.error or silent rejection.
- **PATTERN**: Mirror existing DayMode tests; use `fireEvent.mouseDown/mouseMove/mouseUp` from `@testing-library/react`.
- **IMPORTS**: Use existing test helpers.
- **GOTCHA**: `clientX`/`clientY` math depends on the strip's `getBoundingClientRect()`. Stub `HTMLDivElement.prototype.getBoundingClientRect` in the test setup (or use `jest-dom` 's relevant mock).
- **VALIDATE**: `cd frontend && npm test -- --run DayMode`

### Task 23: VERIFY all linting and type checking pass

- **IMPLEMENT**: No code change; run validators.
- **PATTERN**: N/A.
- **IMPORTS**: N/A.
- **GOTCHA**: If `ruff`/`mypy` warns about an unused import or a generic missing in the new helper, fix at source.
- **VALIDATE**: `uv run ruff check src/grins_platform && uv run mypy src/grins_platform && cd frontend && npm run lint && npm run typecheck`

### Task 24: VERIFY full test suites pass

- **IMPLEMENT**: No code change; run validators.
- **PATTERN**: N/A.
- **IMPORTS**: N/A.
- **GOTCHA**: A handful of older Vitest tests may snapshot "Confirmed" / "Scheduled" strings. Update fixtures in those tests rather than reverting the label change.
- **VALIDATE**: `uv run pytest src/grins_platform/tests -v && cd frontend && npm test -- --run`

### Task 25: RUN `/e2e-test` against dev Vercel + dev Railway (MANDATORY)

- **IMPLEMENT**: Invoke the `e2e-test` skill. See Phase 8 above and Level 5 below.
- **PATTERN**: Follow `.claude/skills/e2e-test/SKILL.md` directly. Capture screenshots to `e2e-screenshots/cluster-d-scheduling-confirmations/`.
- **IMPORTS**: N/A.
- **GOTCHA**: Use ONLY `email=kirillrakitinsecond@gmail.com` and `phone=+19527373312`. Never any synthetic values. (Memory rule: `feedback_test_recipients_prod_safety.md`.)
- **VALIDATE**: All journeys listed in Level 5 below pass green; screenshots captured; DB validation SQL returns expected rows.

---

## TESTING STRATEGY

### Unit Tests

- **Backend**: Add `test_update_appointment_suppress_notifications_skips_sms` and a positive counterpart (`test_update_appointment_default_sends_sms`) in `src/grins_platform/tests/unit/test_appointment_service.py`. Both must assert post-update status AND SMS dispatch count.
- **Frontend**:
  - `ActionTrack.test.tsx` — new banner-render test for `status='scheduled'`; assert no buttons rendered; assert `data-testid="awaiting-confirmation-banner"` present.
  - `StaffWorkflowButtons.test.tsx` — assert `useOnMyWay.mutateAsync` called with `jobId` (not `appointmentId`).
  - `AppointmentList.test.tsx` (if exists) — assert getStatusLabel('scheduled') returns 'Awaiting confirmation'.
  - `DayMode.test.tsx` — drag-drop adds `suppress_notifications: true` to mutation payload; mouse-drag math (4 cases: click, drag-forward, drag-backward, past-time).
  - `pipeline.test.ts` (if exists for the sales types file) — `getSalesStatusLabel` returns the right label across the 4 confirmation_status values × estimate_scheduled vs other statuses.

### Integration Tests

- **Backend**: PUT `/api/v1/appointments/{id}` with `{"scheduled_date": ..., "suppress_notifications": true}` against a confirmed appointment:
  - Returns 200.
  - Returns response body with `status="scheduled"`.
  - Audit log row written with `sms_sent=False`.
  - No SMS dispatch logged (mock the SMS service in test setup).

### Edge Cases

- Confirmed appointment dragged within the same staff/same date/same time → no mutation fired (existing no-op guard at `DayMode.tsx:178–180`). Verify the `suppress_notifications` flag is also not sent in that case.
- Past-time drag in DayMode → toast.error (existing) AND no mutation; verify the new slot-pick handler also rejects past times.
- Drag-drop on a CANCELLED appointment → reactivates (per `appointment_service.py:448–458`); ensure `suppress_notifications=true` from drag-drop suppresses the reschedule SMS the reactivation would otherwise fire.
- Dragging from a tech-row whose appointment has `job_id` deleted/null → mutation still works (only updates appointment); banner copy in ActionTrack still renders correctly when `appointment.status === 'scheduled'`.
- Tech-mobile user opens AppointmentModal at `status='scheduled'` → sees ONLY the banner (no buttons); after admin sends confirmation SMS and customer replies Y → status flips to 'confirmed' → ModalHeader label flips to 'Scheduled' AND ActionTrack renders the 3 cards.
- `useOnMyWay` SMS failure path → `on_my_way_at` rolled back per bughunt L-2 fix (`jobs.py:1339`). Verify the migrated callsite's error toast still surfaces.
- Sales pipeline entry at `estimate_scheduled` with no `SalesCalendarEvent` yet → `getSalesStatusLabel` returns "Awaiting confirmation" (latestEvent is undefined → branch fall-through to the awaiting label).

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform
uv run mypy src/grins_platform
cd frontend && npm run lint && npm run typecheck
```

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit -v -k "appointment_service or appointment_routes"
cd frontend && npm test -- --run -- ActionTrack StaffWorkflowButtons AppointmentList DayMode WeekMode
```

### Level 3: Integration Tests

```bash
uv run pytest src/grins_platform/tests/integration -v -k "appointment"
```

### Level 4: Manual Validation

Local dev (do NOT run alembic against Railway from local — there are no migrations in this cluster, but the rule stands):

```bash
# Backend
uv run uvicorn grins_platform.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

Manual checks:
1. Open the dev frontend at `http://localhost:5173`.
2. Schedule tab → Day view → drag a CONFIRMED appointment to a different time. Confirm: (a) status badge flips to "Awaiting confirmation" (was: "Scheduled"), (b) no SMS arrives in the test inbox/phone (`kirillrakitinsecond@gmail.com` / `+19527373312`), (c) network tab shows PUT `/api/v1/appointments/{id}` with `suppress_notifications: true` in body.
3. Open the appointment in the modal → confirm the banner appears above where the 3 action cards would be → confirm the 3 cards do NOT render.
4. From a separate device or test SMS tool, reply Y to a fresh confirmation SMS → status flips → modal now shows the 3 action cards AND the badge says "Scheduled".
5. Click On My Way in the modal → confirm: (a) one SMS sent to test phone, (b) network tab shows POST `/api/v1/jobs/{job_id}/on-my-way` (NOT `/appointments/{id}` PUT), (c) `job.on_my_way_at` set in DB.
6. Schedule tab → Day view → on an empty area of a tech strip, click-without-dragging → confirm the create-appointment dialog opens with a 60-min default range.
7. Schedule tab → Day view → on an empty area, mousedown + drag horizontally → confirm dashed preview rectangle appears → release → dialog opens with the dragged range pre-filled.
8. Sales tab → an entry at `estimate_scheduled` with no Y reply yet → confirm pipeline row badge says "Awaiting confirmation".
9. Same entry after replying Y → badge flips to "Scheduled".

### Level 5: MANDATORY E2E Against Dev Vercel + Dev Railway

Invoke the `e2e-test` skill (`.claude/skills/e2e-test/SKILL.md`) — DO NOT skip, DO NOT mark complete until this passes.

- **Dev Vercel admin dashboard URL**: `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`
- **(Skip)** Dev Vercel marketing/landing — Cluster D does NOT touch the public/landing flow.
- **Dev Railway API URL**: `https://grins-dev-dev.up.railway.app`
- **Dev Railway DB connection**: read `DATABASE_URL` from the dev Railway environment via `mcp__railway__list-variables` (or `railway variables --service <backend-service>`). Use the public Postgres URL for `psql` queries from the executing agent. **Never run alembic against this URL from local** — there are no migrations in this cluster; rule stands generally (memory `feedback_no_remote_alembic.md`).
- **Test recipient email** (HARDCODED, do not change): `kirillrakitinsecond@gmail.com`
- **Test recipient phone** (HARDCODED, do not change): `+19527373312`

**User journeys to exercise:**

1. **Drag-drop demote without SMS (DayMode)** — Schedule tab → Day view → drag a CONFIRMED appointment to a new time slot on the same tech row. Assert: badge flips to "Awaiting confirmation", no SMS at test phone, network log shows `suppress_notifications: true`.
2. **Drag-drop demote without SMS (WeekMode)** — Schedule tab → Week view → drag a CONFIRMED appointment to a different staff column / different day. Same assertions as #1 plus staff/date update.
3. **Status label appointments — pre-confirmed** — Create a fresh appointment via Schedule tab → status='scheduled' → assert ModalHeader badge reads "Awaiting confirmation" AND AppointmentList row reads "Awaiting confirmation".
4. **Status label appointments — post-confirmed** — Send a confirmation SMS to the test phone, reply Y → assert badge flips to "Scheduled" in both ModalHeader and AppointmentList.
5. **Status label sales entries — pre-Y** — Open a sales pipeline entry at status='estimate_scheduled' with no SalesCalendarEvent confirmation → assert pipeline row + detail header both read "Awaiting confirmation".
6. **Status label sales entries — post-Y** — Customer (test phone) replies Y → reload entry → assert label flips to "Scheduled".
7. **Tech-mobile banner — pre-confirmed** — Open AppointmentModal at status='scheduled' on mobile viewport → assert banner visible with copy "Waiting for customer confirmation" AND 3 action cards NOT rendered.
8. **Tech-mobile banner — post-confirmed** — After Y reply → reopen modal → assert banner gone AND 3 action cards rendered (On My Way active, Job Started disabled, Job Complete disabled).
9. **Canonical on-the-way flow (modal)** — Status='confirmed' → click "On my way" card → assert: SMS sent to test phone, network shows POST `/jobs/{job_id}/on-my-way`, modal status flips to "En Route".
10. **Canonical on-the-way flow (StaffWorkflowButtons)** — Find a render site of StaffWorkflowButtons (likely tech-mobile job detail) → click On My Way → same assertions as #9.
11. **Daily slot-pick — click to create** — DayMode, empty tech row, click without drag → assert create-appointment dialog opens with the clicked time as default-start and +60min default-end.
12. **Daily slot-pick — drag to create** — DayMode, empty tech row, mousedown + drag horizontally → assert dashed preview rect → release → assert dialog opens with dragged time range pre-filled.
13. **Mobile/tablet viewports** — Repeat journeys 3, 7, 8, 11 at viewport widths 375px (iPhone) and 768px (tablet).

**DB validation queries** (run via `psql $DATABASE_URL`):

```sql
-- Journey 1 & 2: drag-drop must demote status, MUST NOT log SMS
-- Replace <appt_id> with the appointment manipulated during the test.
SELECT id, status, scheduled_date, time_window_start, time_window_end
  FROM appointments WHERE id = '<appt_id>';
-- expect: status='scheduled', new date/time applied

SELECT COUNT(*) FROM sent_messages
  WHERE customer_id = (SELECT customer_id FROM jobs WHERE id = (SELECT job_id FROM appointments WHERE id = '<appt_id>'))
    AND created_at > now() - interval '5 minutes'
    AND message_type ILIKE '%reschedule%';
-- expect: 0 (no reschedule SMS fired)

-- Journey 4: post-Y reply, status flips to confirmed
SELECT id, status FROM appointments WHERE id = '<appt_id>';
-- expect: status='confirmed'

-- Journey 9 & 10: canonical on-my-way sets job.on_my_way_at AND fires SMS
SELECT id, on_my_way_at FROM jobs WHERE id = '<job_id>';
-- expect: on_my_way_at IS NOT NULL, set within last minute

SELECT COUNT(*) FROM sent_messages
  WHERE customer_id = (SELECT customer_id FROM jobs WHERE id = '<job_id>')
    AND created_at > now() - interval '2 minutes'
    AND body ILIKE '%on our way%';
-- expect: 1

-- Journey 11 & 12: new appointment created via slot-pick
SELECT id, scheduled_date, time_window_start, time_window_end, staff_id, status
  FROM appointments WHERE id = '<new_appt_id>' ORDER BY created_at DESC LIMIT 1;
-- expect: matches the picked range; status='draft' or 'scheduled' depending on dialog flow
```

- **Screenshot directory**: `e2e-screenshots/cluster-d-scheduling-confirmations/`
- **Completion criterion**: every journey green, every DB validation query returns expected rows, no console/JS errors, mobile/tablet/desktop screenshots all captured.

> The executing agent must run `/e2e-test` (the skill) after implementation, point it at the dev Vercel URL above, and validate writes against the dev Railway DB. Skipping this is a protocol violation.

### Level 6: Additional Validation (Optional)

- **Railway MCP**: `mcp__railway__get-logs --service <backend>` immediately after journey 1 — confirm no reschedule SMS log line.
- **Storybook** (if the project has one for `Alert` or `ActionTrack`): verify visual regression at the new states.

---

## ACCEPTANCE CRITERIA

- [ ] `suppress_notifications` accepted on `PUT /api/v1/appointments/{id}`; when true, no reschedule SMS fires; status still demotes CONFIRMED→SCHEDULED.
- [ ] `appointmentStatusConfig` labels: `scheduled='Awaiting confirmation'`, `confirmed='Scheduled'`.
- [ ] `AppointmentList.getStatusLabel('scheduled') === 'Awaiting confirmation'`; `getStatusLabel('confirmed') === 'Scheduled'`.
- [ ] `getSalesStatusLabel` returns "Awaiting confirmation" for `estimate_scheduled` + non-confirmed event; "Scheduled" for `estimate_scheduled` + confirmed event; existing labels for all other statuses.
- [ ] `SalesEntryResponse.latest_event_confirmation_status` populated from the latest `SalesCalendarEvent`; `null` when none exists. Frontend `SalesEntry` TS type carries the field.
- [ ] `ActionTrack` renders the info banner (and no action cards) when `status === 'scheduled'`.
- [ ] `StaffWorkflowButtons` and `ActionTrack` both call `useOnMyWay(jobId)` for the on-my-way action.
- [ ] `useMarkAppointmentEnRoute` removed from `frontend/src/features/schedule/hooks/index.ts` and `frontend/src/features/schedule/index.ts` exports; hook definition still present with `@deprecated` comment.
- [ ] DayMode + WeekMode drag-drop mutations include `suppress_notifications: true`.
- [ ] DayMode supports click-to-pick and drag-across-slots to create a new appointment; existing card-drag-to-reschedule still works.
- [ ] All validation commands pass with zero errors.
- [ ] Unit + integration tests for the new paths green.
- [ ] **`/e2e-test` skill executed against dev Vercel + dev Railway — all 13 journeys green, all DB validations pass, screenshots captured under `e2e-screenshots/cluster-d-scheduling-confirmations/`.**
- [ ] Code follows project conventions and patterns.
- [ ] No regressions in existing functionality (existing tests pass).

---

## COMPLETION CHECKLIST

- [ ] All 25 tasks completed in order.
- [ ] Each task's validation command passed immediately.
- [ ] All validation commands executed successfully.
- [ ] Full test suite passes (unit + integration + frontend Vitest).
- [ ] No linting or type checking errors.
- [ ] Manual testing confirms each of the 5 items works end-to-end locally.
- [ ] **`/e2e-test` skill RUN against dev Vercel + dev Railway — ALL 13 journeys green, ALL DB validations pass, screenshots captured. Plan is NOT complete without this.**
- [ ] Acceptance criteria all met.
- [ ] Code reviewed for quality and maintainability (consider `/simplify` after implementation).

---

## NOTES

### Critical pre-existing logic to be aware of

`AppointmentService.update_appointment` ALREADY demotes CONFIRMED → SCHEDULED on reschedule (`services/appointment_service.py:509–526`) AND already fires a reschedule SMS gated on `notify_customer=True` (`services/appointment_service.py:495–508`). The only new wiring is exposing a `suppress_notifications` flag through the schema/endpoint to flip `notify_customer` to False for the drag-drop path.

This means:
- **Do NOT add new branching to the service.** Reuse the existing `notify_customer` parameter.
- **Do NOT add a `confirmation_status` field to the Appointment model.** The existing `status` column already encodes the pre/post-confirmation distinction (SCHEDULED = pre, CONFIRMED = post). Adding a parallel field would create two sources of truth and force the SalesCalendarEvent-style flag onto a table that doesn't need it. The user's "clear `confirmation_status`" wording in the verification doc is best interpreted as "ensure the appointment is back in the un-confirmed state" — which the existing demote logic accomplishes. Surface this design choice explicitly in PR description so the user can confirm or push back.

### Sales entries DO have `confirmation_status`

`SalesCalendarEvent.confirmation_status` (`schemas/sales_pipeline.py:111–112`, `frontend/src/features/sales/types/pipeline.ts:132–133`) already exists with values `'pending' | 'confirmed' | 'reschedule_requested' | 'cancelled'`. The `getSalesStatusLabel` helper reads this field directly. No schema change for sales side either.

### Why a brand-new endpoint isn't needed for Item 1

A dedicated `POST /appointments/{id}/reschedule-quietly` endpoint would more cleanly express intent than a request-body flag. We chose the flag approach because:
1. Existing frontend already uses `useUpdateAppointment` with PUT — no new hook needed.
2. The mutation already optimistically updates and invalidates the right cache keys.
3. The flag is additive and backwards-compatible — no client breakage.
4. The audit log already captures the flag's effect via `sms_sent=False`.

If future requirements add more drag-drop-specific behaviors (e.g., a separate "drag-drop demote" audit action label), a dedicated endpoint becomes worthwhile.

### Future cleanup (out of scope, capture for follow-up)

- Delete `appointmentApi.markEnRoute` and `useMarkAppointmentEnRoute` entirely after one release.
- Delete the unused `en_route_at`-write branch in `appointment_service.py:1980–1981` if no other path hits it.
- Extract a shared `<SlotGridInteractive>` primitive consumed by both `WeekCalendar` and `DayMode` (see Explore-agent recommendation in research). The current plan duplicates the mouse-state machine in DayMode rather than extracting; that's a deliberate trade-off — the extraction is a separate-PR concern after the cluster D port lands and proves out.

## Iteration Log

- **Iter 1**: 6/10 — gaps: hadn't verified existing demote logic (turns out it exists at `appointment_service.py:509–526`); hadn't confirmed `confirmation_status` does NOT exist on Appointment model; hadn't located `useOnMyWay` callers; hadn't verified `WeekCalendar` ↔ `DayMode` shape.
- **Iter 2**: 9/10 — spawned 4 parallel Explore agents, closed most gaps. Remaining: hadn't read the actual demote-logic file or banner-component source to confirm semantics.
- **Iter 3**: 8.5/10 (claimed 10/10 prematurely — corrected after user challenge). Genuine remaining gaps: SalesEntry response had no embedded calendar event, so list-view label needed a backend denormalization; package manager was `npm` not `pnpm`; `<StaffWorkflowButtons>` render sites + `<ResourceTimelineView>` parent wiring not enumerated; `onEmptyCellClick` dialog flow not opened.
- **Iter 4**: 10/10 — closed all Iter 3 gaps with direct reads. Verified: `npm` lock file at repo root; `ResourceTimelineView/index.tsx:27–183` shows `onDateClick` does NOT accept time range (added `onSlotRangePick` prop + Task 21); `SchedulePage.tsx:31, 496` is sole parent; `<StaffWorkflowButtons>` has exactly ONE render site at `AppointmentDetail.tsx:690–694` with `appointment` already in scope (Task 13b added); `SalesEntryResponse` lacks the field but already has denormalized siblings (`customer_tags`, etc.) so Task 7b/7c add `latest_event_confirmation_status` consistently; `WeekCalendar.tsx:92–143` mouse handler exact match; `Alert` variants `default/warning/error/success/info` confirmed (`shared/components/ui/alert.tsx:5–20`); `useOnMyWay` at `useJobMutations.ts:137–146` exact match; `appointmentApi.markEnRoute` at `:205–207` exact match; `jobs.py:1272–1359` on-my-way endpoint with bughunt L-2 at `:1303–1339` exact match; `text-amber`/`bg-amber` confirmed in 5 existing files (purge safe). All gaps closed. Min dimension score: 10. Plan ready.
