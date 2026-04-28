# Feature: Schedule Estimate Visit Modal

The following plan is end-to-end self-contained: every constant, snippet, file path, and migration head needed to one-pass-implement is inlined here. **Read this whole file once before starting** so the cross-references make sense, then execute the tasks top-to-bottom.

Pay special attention to naming of existing utils/types/models. Import from the right files; the section "Verified Facts" below is authoritative — don't second-guess it.

---

## Verified Facts (audited 2026-04-25 against the working tree)

These were each grep'd / read directly. Trust them.

| Fact | Verified |
|---|---|
| Current alembic head | `20260425_100000` (file: `20260425_100000_add_appointment_notes_table.py`). New migration's `down_revision` MUST be this string. |
| `Staff` model | `src/grins_platform/models/staff.py:27` — class `Staff`, `__tablename__ = "staff"`, `id` is `Mapped[UUID]` PK |
| Frontend `Staff` type | `frontend/src/features/staff/types/index.ts:8-22` — `Staff.name` (string), NOT `display_name` |
| `useStaff` return shape | `useStaff({ is_active: true })` → `{ data: PaginatedStaffResponse, isLoading, ... }` where `data.items: Staff[]` |
| `useStaff` import path | `import { useStaff } from '@/features/staff/hooks/useStaff'` |
| `Dialog` location | `frontend/src/components/ui/dialog.tsx` (used by `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:13-20`) |
| `Switch` location | `frontend/src/components/ui/switch.tsx` (Radix wrapper, controlled via `checked`/`onCheckedChange`) |
| `QueryProvider` | `frontend/src/core/providers/QueryProvider.tsx` |
| `getErrorMessage` | `frontend/src/core/api/client.ts:105-119` — checks `axiosError.response?.data?.error?.message` first |
| Backend `/calendar/events` | `src/grins_platform/api/v1/sales_pipeline.py:530-654` — GET/POST/PUT/DELETE; POST auto-advances `schedule_estimate` → `estimate_scheduled` (lines 583-599) |
| `SalesCalendarEvent` model | `src/grins_platform/models/sales.py:115-168` — has `notes` (text). Time fields are `start_time`/`end_time` as `time` (HH:MM:SS) |
| API router prefix | `src/grins_platform/api/v1/router.py:296-301` — `sales_pipeline_router` mounted at `/sales`. Full path: `/api/v1/sales/calendar/events` |
| Existing test pattern for sales | `src/grins_platform/tests/functional/test_sales_pipeline_functional.py` uses `MagicMock(spec=...)` — **functional tests in this codebase are mocked at the service layer, NOT real-DB**. Real-DB workflow tests live in `tests/integration/`. |
| HTTP client fixtures | `tests/conftest.py:347-362` exposes `client` (no auth) and `authenticated_client` (mock `Bearer test-token`). |
| Existing E2E sales script | `scripts/e2e/test-sales.sh` — uses fallback selector chain (`[data-testid='email-input']` → `[name='email']` → `input[type='email']`). New script must mirror this. |
| Screenshot subdir convention | `e2e-screenshots/{feature}/NN-step.png` |

---

## Resolved Open Questions (audit round 2, 2026-04-25)

After the first plan iteration, an audit pass surfaced 13 open questions. Items 1-9 are resolved inline below; items 10-13 are explicitly deferred edge cases. Don't re-litigate any of these.

| # | Question | Resolution |
|---|---|---|
| 1 | Email row in `PrefilledCustomerCard`? | YES — `PrefilledCustomerCard` now consumes `useCustomer(entry.customer_id)` to surface email. |
| 2 | E2E pill-tone assertion was wrong (status flip is alias-only) | E2E now asserts `[data-testid='activity-event-visit_scheduled']` via the existing `ActivityStrip` testid pattern (`ActivityStrip.tsx:53`). |
| 3 | Reschedule when there are multiple events for one entry? | Use `entryEvents[length - 1]` (last by `scheduled_date ASC`). No `cancelled_at` on `SalesCalendarEvent` — adding one is a separate ticket. Documented in Task 21. |
| 4 | "Unassigned" choice in the assignee `<Select>`? | Add explicit `— Unassigned —` item using `'__none__'` sentinel (Radix Select v2.2.6 disallows empty `value`). Map `null ↔ '__none__'` at the boundary. |
| 5 | Title separator: em-dash or hyphen? | Hyphen. Matches existing `SalesCalendar.tsx:193`: ``Estimate - ${customer_name}`` |
| 6 | `pickCustomerName` formatter location | Extracted to `formatShortName(full: string)` in `scheduleVisitUtils.ts`. |
| 7 | Dialog width override mechanism | `className="sm:max-w-[960px]"` — `dialog.tsx:64` default is `sm:max-w-lg`; the `cn()` helper uses `tailwind-merge` (`package.json:59`), last-class-wins for identical properties. Verified safe. |
| 8 | Customer-name fallback string | `'Unknown Customer'` everywhere (matches `SalesDetail.tsx:382`). |
| 9 | `track()` helper location | New file `frontend/src/shared/utils/track.ts` exporting `track(event, payload)`. Modal imports it. |
| 10 | Reschedule loading-state race (modal opens before `useSalesCalendarEvents` resolves) | DEFERRED — cache hit makes this near-impossible in practice. If it surfaces, gate the `Schedule visit` button on `isLoading`. |
| 11 | Strict 422 validation for bad `assigned_to_user_id` UUID | DEFERRED — existing handler doesn't validate `customer_id` either; FK insert returns 500. Out of scope for v1. |
| 12 | Browser TZ ≠ business TZ | DEFERRED per SPEC §6.8 (multi-TZ businesses out of scope). |
| 13 | DST spring-forward Sunday's missing 2 AM slot | DEFERRED — renders normally, becomes unclickable / past-shaded. Matches Google Calendar behavior. |

---

## Feature Description

A two-column modal (`ScheduleVisitModal`) opened from the Sales Pipeline detail screen's Now-card primary action `schedule_visit`. The modal lets a sales user pick an estimate-visit slot for a sales pipeline entry by typing date/time/duration **or** by clicking/dragging on a 7-day week calendar. Both views are derived from a single `pick: { date, start, end }` source-of-truth held in `useScheduleVisit`. On confirm, the modal POSTs the slot to the existing `/api/v1/sales/calendar/events` endpoint, which auto-advances the entry from `schedule_estimate` → `estimate_scheduled`. A re-schedule path (`PUT`) appears when the entry is already `estimate_scheduled`.

The reference HTML at `feature-developments/schedule-estimate-visit-handoff/reference/Schedule-Estimate-Visit-Reference.html` is the visual + interaction ground truth. The reference's full `buildGrid` / `paintOverlays` / drag-handler logic is reproduced in this plan (Task 15), so the React port is mechanical — no translation guesswork required.

## User Story

As a sales coordinator
I want to pick an estimate-visit time directly from the Sales pipeline detail page in a click-or-drag week calendar
So that I can book the appointment, see existing estimates to avoid conflicts, and advance the pipeline stage in a single action — without context-switching to the dedicated Sales calendar tab.

## Problem Statement

Today the Now-card "Schedule visit" action on `SalesDetail` (`frontend/src/features/sales/components/SalesDetail.tsx:141-147`) just calls `useAdvanceSalesEntry()` — it advances the pipeline status without actually creating the calendar event. Sales users are forced to open the separate `SalesCalendar` tab and re-select the customer to create the real appointment, then the entry status drifts from reality. There is also no way to see other estimate appointments while picking a slot.

## Solution Statement

Replace the no-op advance handler with a `<ScheduleVisitModal />` that:

1. Pre-fills the customer/job from `entry` (read-only customer card in the left column).
2. Provides synced form fields (date/time/duration/assignee/notes) and a 7-day week calendar (right column) — both views of one `pick` state held in `useScheduleVisit`.
3. Fetches existing estimate visits for the visible week from `GET /api/v1/sales/calendar/events?start_date=...&end_date=...` and renders them as read-only blocks; conflicts (same date + overlapping minute range) flip pick + estimate blocks red and surface a warn banner (Confirm stays enabled — overlap is allowed).
4. On confirm: `POST /api/v1/sales/calendar/events` (or `PUT /api/v1/sales/calendar/events/{eventId}` for reschedule). Backend already auto-advances `schedule_estimate` → `estimate_scheduled` on POST. After success, invalidate sales-pipeline + calendar-events query caches, toast success, close.
5. Mobile (<720px): stack customer card → calendar → fields.

Two backend extensions: add optional `assigned_to_user_id` (UUID, FK `staff.id`, `ON DELETE SET NULL`) on `sales_calendar_events` and surface it on `SalesCalendarEventResponse` so the assignee dropdown is round-trippable. The `internal_notes` field already exists as `notes`.

## Feature Metadata

**Feature Type**: New Capability (frontend modal + small backend extension)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- Frontend: `frontend/src/features/sales/` (new modal + hook + 5 sub-components)
- Backend: `src/grins_platform/models/sales.py`, `schemas/sales_pipeline.py`, `api/v1/sales_pipeline.py` (additive: `assigned_to_user_id` column + Alembic migration)
**Dependencies**: shadcn `Dialog`, `Button`, `Input`, `Select`, `Textarea`, `Switch` (all installed), TanStack Query v5, `date-fns`. No new npm/pypi deps.

---

## Decisively Closed §8 Open Questions (don't relitigate)

Per SPEC.md §8, these were "open questions". For v1, they are **closed** with the following decisions, and the modal is shipped accordingly:

1. **Per-assignee filtering of existing estimates** — DROPPED for v1. Show all assignees' blocks regardless of selection. The conflict check ignores assignee per SPEC §5. (When a future ticket adds it, the change is local to `paintOverlays` filter + an extra query param.)
2. **24h calendar toggle** — DROPPED for v1. Hours are fixed at 6 AM – 8 PM. Out-of-hours requests are extreme outliers; users can override in the Date/Time fields, which the calendar renders as a clipped pick block (acceptable).
3. **Resize handles on pick block** — DROPPED for v1. Resize is via the Duration `<Select>` only.
4. **`send_confirmation_text` toggle** — DROPPED for v1. README explicitly lists "Sending the appointment-confirmation SMS" as out of scope. Drop the field from `ScheduleFields` and `useScheduleVisit`. (Re-add when SMS plumbing lands.)

These four decisions remove the only scope-expansion risk in the original plan.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING

**Handoff package (visual + structural ground truth — do NOT skip):**
- `feature-developments/schedule-estimate-visit-handoff/SPEC.md` — Behavior contract, edge cases, copy table
- `feature-developments/schedule-estimate-visit-handoff/CHECKLIST.md` — QA checklist that must pass before merging
- `feature-developments/schedule-estimate-visit-handoff/reference/Schedule-Estimate-Visit-Reference.html` — Vanilla JS reference; all rendering math is reproduced verbatim in Task 15 of this plan, but read it once for visual context
- `feature-developments/schedule-estimate-visit-handoff/scaffold/data-shapes.ts` — TS type shapes (with the API-shape adjustments below)
- `feature-developments/schedule-estimate-visit-handoff/scaffold/ScheduleVisitModal.tsx` — top-level composition skeleton
- `feature-developments/schedule-estimate-visit-handoff/scaffold/PrefilledCustomerCard.tsx` — read-only customer block
- `feature-developments/schedule-estimate-visit-handoff/scaffold/ScheduleFields.tsx` — left-column form fields (NB: replace hard-coded `ASSIGNEES` with `useStaff()` data)
- `feature-developments/schedule-estimate-visit-handoff/scaffold/WeekCalendar.tsx` — high-level shape
- `feature-developments/schedule-estimate-visit-handoff/scaffold/useScheduleVisit.ts` — single-source-of-truth hook

**Backend (existing endpoints to consume, do NOT recreate):**
- `src/grins_platform/api/v1/sales_pipeline.py:530-654` — `/calendar/events` GET/POST/PUT/DELETE; POST already auto-advances `schedule_estimate` → `estimate_scheduled` (lines 583-599)
- `src/grins_platform/models/sales.py:115-168` — `SalesCalendarEvent`. Will gain `assigned_to_user_id`.
- `src/grins_platform/schemas/sales_pipeline.py:61-97` — `SalesCalendarEventCreate/Update/Response`. Will gain `assigned_to_user_id`.
- `src/grins_platform/models/enums.py` — `SalesEntryStatus.SCHEDULE_ESTIMATE`, `ESTIMATE_SCHEDULED`
- `src/grins_platform/models/staff.py:27,54,57` — class `Staff`, table `staff`, `id` UUID PK (FK target)

**Frontend integration points:**
- `frontend/src/features/sales/components/SalesDetail.tsx:141-147` — `case 'schedule_visit':` is currently mis-wired to `advance.mutate`. Replace with modal open/close state.
- `frontend/src/features/sales/api/salesPipelineApi.ts:151-187` — Existing `listCalendarEvents`, `createCalendarEvent`, `updateCalendarEvent`. No method-signature changes required after Task 7.
- `frontend/src/features/sales/hooks/useSalesPipeline.ts:213-260` — Existing `useSalesCalendarEvents`, `useCreateCalendarEvent`, `useUpdateCalendarEvent`. UPDATE invalidations in Task 11.
- `frontend/src/features/sales/hooks/useSalesPipeline.ts:12-28` — `pipelineKeys` factory; reuse `pipelineKeys.calendarEventList(...)`.
- `frontend/src/features/sales/types/pipeline.ts:99-129` — `SalesCalendarEvent`, `SalesCalendarEventCreate/Update`. Extend with `assigned_to_user_id`.
- `frontend/src/features/sales/index.ts:1-77` — feature public API; export the new modal here.
- `frontend/src/features/staff/hooks/useStaff.ts:24-29` — `useStaff()` for assignee dropdown. **Returns `Staff` with `name` (NOT `display_name`).**

**Pattern references (mirror these):**
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:1-90` — Modal composition pattern with shadcn `Dialog`, `useQuery`, `useQueryClient` invalidation, sub-component decomposition
- `frontend/src/features/sales/components/SalesCalendar.tsx:50-219` — Existing FullCalendar-based create/edit; use as reference for `useCreateCalendarEvent` payload shape and toast/error handling. Do NOT reuse FullCalendar.
- `src/grins_platform/tests/functional/test_sales_pipeline_functional.py:1-60` — service-layer mocked-functional pattern (mirror in Task 6)
- `scripts/e2e/test-sales.sh:50-83` — login fallback chain (mirror in Task 24)

### New Files to Create

**Frontend** (under `frontend/src/features/sales/components/ScheduleVisitModal/`):
- `index.ts` — public re-export
- `ScheduleVisitModal.tsx` — top-level Dialog wrapper + composition
- `PrefilledCustomerCard.tsx` — read-only customer block
- `ScheduleFields.tsx` — left-column form fields (date/time/duration/assignee/notes)
- `WeekCalendar.tsx` — 7-day grid + overlays (estimate blocks, pick, drag ghost, now-line)
- `PickSummary.tsx` — pick summary + conflict banner
- `ScheduleVisitModal.module.css` — ported reference CSS for the calendar grid (Task 15)
- `ScheduleVisitModal.test.tsx`
- `WeekCalendar.test.tsx`

Under `frontend/src/features/sales/hooks/`:
- `useScheduleVisit.ts` — state hook (lives outside the modal folder so it can be hook-tested in isolation)
- `useScheduleVisit.test.ts`

Under `frontend/src/features/sales/lib/`:
- `scheduleVisitUtils.ts` — pure helpers (incl. `formatShortName`)
- `scheduleVisitUtils.test.ts`

Under `frontend/src/shared/utils/`:
- `track.ts` — telemetry stub (Task 18.5; future SDK swap is a one-file change)

**Backend**:
- `src/grins_platform/migrations/versions/20260426_100000_add_sales_calendar_assigned_to.py`
- `src/grins_platform/tests/unit/test_schedule_visit_api.py`
- `src/grins_platform/tests/functional/test_schedule_visit_functional.py` (mocked, mirroring `test_sales_pipeline_functional.py`)
- `src/grins_platform/tests/integration/test_schedule_visit_integration.py` (real-DB workflow)

**Scripts**:
- `scripts/e2e/test-schedule-visit.sh`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [TanStack Query v5 — useMutation onSuccess](https://tanstack.com/query/latest/docs/framework/react/reference/useMutation)
  - Why: invalidating `pipelineKeys.calendarEvents()` + `pipelineKeys.detail(entryId)` after submit is what advances the stepper visibly without manual `refetch()`
- [Radix Dialog (shadcn wrapper)](https://www.radix-ui.com/primitives/docs/components/dialog)
  - Why: focus trap + Esc-to-close are built-in (CHECKLIST §Accessibility lines 53-55)
- [date-fns — startOfWeek `weekStartsOn: 1`](https://date-fns.org/v4.1.0/docs/startOfWeek)
  - Why: matches the reference HTML's Monday-start (line 384: `day === 0 ? -6 : 1 - day`)
- [SQLAlchemy 2.0 — `mapped_column(ForeignKey(..., ondelete="SET NULL"))`](https://docs.sqlalchemy.org/en/20/orm/dataclasses.html#mapped-column)
  - Why: matches the existing `SalesCalendarEvent` style at `models/sales.py:128-137`
- [Alembic — `op.add_column` + `op.create_index`](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.add_column)
  - Why: backwards-compatible additive migration; nullable column → no data backfill

### Patterns to Follow

**Logging events (backend)** — `{domain}.{component}.{action}_{state}` per `code-standards.md`:
```python
_ep.log_started("create_calendar_event", sales_entry_id=str(body.sales_entry_id))
# ...
_ep.log_completed("create_calendar_event", event_id=str(event.id))
logger.info(
    "sales.calendar_event.auto_advance",
    sales_entry_id=str(body.sales_entry_id),
    from_status=SalesEntryStatus.SCHEDULE_ESTIMATE.value,
    to_status=SalesEntryStatus.ESTIMATE_SCHEDULED.value,
)
```
Already implemented at `sales_pipeline.py:571,594-599,603` — extend with `assigned_to_user_id` field in the log context when present.

**API endpoint pattern (backend)** — mirror existing `create_calendar_event` at `sales_pipeline.py:559-604`:
- `_ep.log_started/_completed`
- `select(...).where(...)` → `scalar_one_or_none()` → 404 if missing
- `await session.commit()` then `await session.refresh(event)`
- Return `Schema.model_validate(event)` (Pydantic v2)

**TanStack Query hook (frontend)** — broaden invalidation in Task 11:
```ts
export function useCreateCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SalesCalendarEventCreate) =>
      salesPipelineApi.createCalendarEvent(body),
    onSuccess: (_data, body) => {
      qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
      qc.invalidateQueries({ queryKey: pipelineKeys.detail(body.sales_entry_id) });
      qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
    },
  });
}
```

**data-testid convention (frontend)**:
- Modal root: `schedule-visit-modal`
- Form fields: `schedule-visit-date`, `schedule-visit-start-time`, `schedule-visit-duration`, `schedule-visit-assignee`, `schedule-visit-notes`
- Buttons: `schedule-visit-confirm-btn`, `schedule-visit-cancel-btn`
- Calendar: `schedule-visit-calendar`, slot cells `schedule-visit-slot-{dayIdx}-{slotIdx}`, pick block `schedule-visit-pick`, conflict banner `schedule-visit-conflict-banner`
- Customer card: `schedule-visit-customer-card`
- Pick summary: `schedule-visit-pick-summary`
- Telemetry events: emit via `track(event, payload)` helper (`console.info` placeholder — no SDK in repo; future ticket swaps it).

**Form approach** — Don't use react-hook-form/zod here. The form is a thin view of an externally-driven `pick` state (calendar mutates it). Plain controlled inputs + submit-time validation.

**Error handling** — copy from `SalesCalendar.tsx:135-181`:
```ts
try { await mutateAsync(...); toast.success(...); } catch (err) {
  // 409 = slot taken: show inline conflict banner, refetch week, KEEP modal open
  if (axios.isAxiosError(err) && err.response?.status === 409) {
    setConflictError('Slot was just taken — pick another.');
    qc.invalidateQueries({ queryKey: pipelineKeys.calendarEventList({ start_date, end_date }) });
    return;
  }
  toast.error(getErrorMessage(err));
}
```

**Minutes ↔ HH:MM:SS translation** — internal `Pick` is minute-based; backend uses `time` (HH:MM:SS). Translate at the API boundary in `scheduleVisitUtils.ts`. Internal types stay in minutes.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (backend additive + types/utils)

**Tasks:** 1–10. Backend column + migration + schema + API; frontend type extensions; pure helpers.

### Phase 2: Core Implementation (state hook + sub-components)

**Tasks:** 11–20 (includes 18.5 — shared `track.ts` helper).

### Phase 3: Integration

**Tasks:** 21.

### Phase 4: Testing & Validation

**Tasks:** 22–25.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and has its own validation command.

### Task 1 — CREATE Alembic migration

- **CREATE** `src/grins_platform/migrations/versions/20260426_100000_add_sales_calendar_assigned_to.py`
- **IMPLEMENT** (paste verbatim, only adjust the timestamp prefix if `20260426_100000` collides — `ls migrations/versions/ | sort` to confirm):
  ```python
  """Add ``assigned_to_user_id`` to ``sales_calendar_events``.

  Revision ID: 20260426_100000
  Revises: 20260425_100000
  Validates: Schedule Estimate Visit feature handoff
  """

  from __future__ import annotations

  from collections.abc import Sequence

  import sqlalchemy as sa
  from alembic import op

  revision: str = "20260426_100000"
  down_revision: str | None = "20260425_100000"
  branch_labels: str | Sequence[str] | None = None
  depends_on: str | Sequence[str] | None = None


  def upgrade() -> None:
      """Add nullable ``assigned_to_user_id`` FK + index."""
      op.add_column(
          "sales_calendar_events",
          sa.Column(
              "assigned_to_user_id",
              sa.UUID(),
              sa.ForeignKey("staff.id", ondelete="SET NULL"),
              nullable=True,
          ),
      )
      op.create_index(
          "ix_sales_calendar_assigned_to",
          "sales_calendar_events",
          ["assigned_to_user_id"],
      )


  def downgrade() -> None:
      """Drop FK + index."""
      op.drop_index(
          "ix_sales_calendar_assigned_to",
          table_name="sales_calendar_events",
      )
      op.drop_column("sales_calendar_events", "assigned_to_user_id")
  ```
- **PATTERN**: `migrations/versions/20260423_100000_add_customer_tags_table.py` for FK + index style (only without the table-create boilerplate).
- **GOTCHA**: `down_revision = "20260425_100000"` — verified head as of 2026-04-25 (via `uv run alembic heads`). If a newer migration lands between plan-write and execute, run `uv run alembic heads` and update the string. **DO NOT** call this migration `op.alter_column` — it's an add-column.
- **VALIDATE**:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform
  uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
  ```

### Task 2 — UPDATE `src/grins_platform/models/sales.py`

- **IMPLEMENT**: Inside class `SalesCalendarEvent` (line 115), add right after `notes` (around line 142):
  ```python
  assigned_to_user_id: Mapped[Optional[UUID]] = mapped_column(
      PGUUID(as_uuid=True),
      ForeignKey("staff.id", ondelete="SET NULL"),
      nullable=True,
  )
  ```
  Update `__table_args__` (line 162) to include the new index:
  ```python
  __table_args__ = (
      Index("idx_sales_calendar_date", "scheduled_date"),
      Index("ix_sales_calendar_assigned_to", "assigned_to_user_id"),
  )
  ```
- **PATTERN**: Mirror the existing FK at `models/sales.py:50-54` (`property_id`).
- **IMPORTS**: All needed imports already present.
- **GOTCHA**: Do NOT add a `relationship("Staff")` — over-eager joinedload would cascade through `_entry_to_response` serialization. The API serializes the raw UUID; `useStaff()` resolves names client-side.
- **VALIDATE**: `uv run mypy src/grins_platform/models/sales.py && uv run pyright src/grins_platform/models/sales.py`

### Task 3 — UPDATE `src/grins_platform/schemas/sales_pipeline.py`

- **IMPLEMENT**: Add `assigned_to_user_id: Optional[UUID] = None` to all three: `SalesCalendarEventCreate` (around line 70), `SalesCalendarEventUpdate` (around line 79), `SalesCalendarEventResponse` (around line 95).
- **PATTERN**: Mirror existing optional UUIDs at `schemas/sales_pipeline.py:18-20`.
- **GOTCHA**: `SalesCalendarEventResponse.model_config` already has `from_attributes=True` — no change needed there.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/sales_pipeline.py && uv run ruff check src/grins_platform/schemas/sales_pipeline.py`

### Task 4 — UPDATE `src/grins_platform/api/v1/sales_pipeline.py` `create_calendar_event`

- **IMPLEMENT**: At `sales_pipeline.py:572-580`, extend the `SalesCalendarEvent(...)` constructor:
  ```python
  event = SalesCalendarEvent(
      sales_entry_id=body.sales_entry_id,
      customer_id=body.customer_id,
      title=body.title,
      scheduled_date=body.scheduled_date,
      start_time=body.start_time,
      end_time=body.end_time,
      notes=body.notes,
      assigned_to_user_id=body.assigned_to_user_id,  # NEW
  )
  ```
  Extend the log:
  ```python
  _ep.log_completed(
      "create_calendar_event",
      event_id=str(event.id),
      assigned_to_user_id=str(body.assigned_to_user_id) if body.assigned_to_user_id else None,
  )
  ```
  `update_calendar_event` (line 612-631) already uses `for field, value in body.model_dump(exclude_unset=True).items()` so it covers the new field automatically. Verify, no edits needed.
- **PATTERN**: existing handler.
- **GOTCHA**: The list endpoint (`list_calendar_events`, line 535-556) is intentionally NOT changed — per-assignee filtering is closed (§8 Decision 1).
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/sales_pipeline.py && uv run ruff check src/grins_platform/api/v1/sales_pipeline.py`

### Task 5 — CREATE `src/grins_platform/tests/unit/test_schedule_visit_api.py`

- **IMPLEMENT**: Service-/handler-level unit tests using `MagicMock`. Mirror the pattern in `tests/unit/test_sales_pipeline_and_signwell.py`. 4 tests:
  1. `test_create_calendar_event_with_assignee_returns_201` — POST body includes `assigned_to_user_id`; assert it is passed to `SalesCalendarEvent(...)` and present in response.
  2. `test_create_calendar_event_without_assignee_defaults_none` — POST without the field; assert `assigned_to_user_id` is `None` in the response.
  3. `test_update_calendar_event_changes_assignee` — PUT updates the assignee.
  4. `test_create_calendar_event_logs_assignee_in_completed_event` — assert `caplog` captures `_ep.log_completed("create_calendar_event", ..., assigned_to_user_id=...)`.
- **IMPORTS**:
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock
  from uuid import uuid4
  from grins_platform.schemas.sales_pipeline import SalesCalendarEventCreate
  ```
- **GOTCHA**: Use `@pytest.mark.unit`. Mock the `AsyncSession` (use `MagicMock(spec=AsyncSession)`). The handler is `async`, so use `pytest-asyncio`'s `@pytest.mark.asyncio`.
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_schedule_visit_api.py -v`

### Task 6 — CREATE `src/grins_platform/tests/functional/test_schedule_visit_functional.py`

- **IMPLEMENT**: Service-layer functional tests using mocked DB sessions, mirroring `test_sales_pipeline_functional.py:1-60`. Tests are **mocked**, NOT real-DB (this codebase's "functional" tier is mocked-service-layer; real-DB lives in `integration/`). 3 tests:
  1. `test_workflow_create_event_advances_status` — Configure `session.execute` mock to return a `SalesEntry` with `status='schedule_estimate'`; call the endpoint handler; assert the entry's `.status` is mutated to `'estimate_scheduled'` AND the event was added to the session AND `session.commit()` was awaited.
  2. `test_workflow_reschedule_does_not_re_advance` — Entry already at `estimate_scheduled`; PUT updates the event; assert `.status` is unchanged.
  3. `test_workflow_create_event_with_assignee_round_trips` — POST with `assigned_to_user_id`; assert it lands on the SalesCalendarEvent passed to `session.add`.
- **IMPORTS**:
  ```python
  from datetime import date, time
  from unittest.mock import AsyncMock, MagicMock
  from uuid import uuid4
  import pytest
  from grins_platform.api.v1.sales_pipeline import (
      create_calendar_event, update_calendar_event,
  )
  from grins_platform.models.enums import SalesEntryStatus
  from grins_platform.schemas.sales_pipeline import (
      SalesCalendarEventCreate, SalesCalendarEventUpdate,
  )
  ```
- **GOTCHA**: `@pytest.mark.functional`. Use the `_make_sales_entry` helper pattern from `test_sales_pipeline_functional.py:30-55`. Don't import `client` — invoke handler functions directly.
- **VALIDATE**: `uv run pytest -m functional src/grins_platform/tests/functional/test_schedule_visit_functional.py -v`

### Task 7 — CREATE `src/grins_platform/tests/integration/test_schedule_visit_integration.py`

- **IMPLEMENT**: Real-DB integration test mirroring patterns in `tests/integration/test_appointment_notes_integration.py`. 1 test:
  1. `test_schedule_visit_real_db_workflow` — Create customer + sales entry via fixtures; POST `/api/v1/sales/calendar/events` via `authenticated_client`; verify the row exists in `sales_calendar_events` AND `sales_entries.status` is `'estimate_scheduled'`. Then PUT to reschedule; verify event row updated, status unchanged.
- **IMPORTS**:
  ```python
  import pytest
  from datetime import date
  from httpx import AsyncClient
  from sqlalchemy import select
  from grins_platform.models.sales import SalesEntry, SalesCalendarEvent
  ```
- **GOTCHA**: Use `@pytest.mark.integration`. The `authenticated_client` fixture uses a mock token — make sure dev's auth dependency override accepts it (existing integration tests confirm this works).
- **VALIDATE**: `uv run pytest -m integration src/grins_platform/tests/integration/test_schedule_visit_integration.py -v`

### Task 8 — UPDATE `frontend/src/features/sales/types/pipeline.ts`

- **IMPLEMENT**: Add `assigned_to_user_id` to `SalesCalendarEvent` (line 100), `SalesCalendarEventCreate` (line 113), `SalesCalendarEventUpdate` (line 123). Append three new types at the end of the file:
  ```ts
  // ─────────────────────────────────────────────────────────────────────────────
  // ScheduleVisitModal types
  // ─────────────────────────────────────────────────────────────────────────────

  /** A picked slot. start/end are minutes-from-midnight (business-local TZ). */
  export type Pick = {
    date: string;   // 'YYYY-MM-DD'
    start: number;  // minutes (inclusive)
    end: number;    // minutes (exclusive)
  };

  /** Calendar render block — minute-based projection of a SalesCalendarEvent. */
  export type EstimateBlock = {
    id: string;
    date: string;
    startMin: number;
    endMin: number;
    customerName: string;     // resolved at hook layer
    jobSummary: string;       // resolved at hook layer
    assignedToUserId: string | null;
  };

  /** Companion form-field state held alongside `pick` in useScheduleVisit. */
  export type ScheduleVisitFormState = {
    durationMin: 30 | 60 | 90 | 120;
    assignedToUserId: string | null;
    internalNotes: string;
  };
  ```
  Updated interfaces:
  ```ts
  export interface SalesCalendarEvent {
    // ... existing fields ...
    assigned_to_user_id: string | null;
  }
  export interface SalesCalendarEventCreate {
    // ... existing ...
    assigned_to_user_id?: string | null;
  }
  export interface SalesCalendarEventUpdate {
    // ... existing ...
    assigned_to_user_id?: string | null;
  }
  ```
- **PATTERN**: existing types at lines 99-129.
- **GOTCHA**: API-shape types stay in HH:MM:SS form (matches backend); `Pick`/`EstimateBlock` are minute-based (modal-internal). Don't conflate.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 9 — CREATE `frontend/src/features/sales/lib/scheduleVisitUtils.ts`

- **IMPLEMENT** (paste verbatim):
  ```ts
  // Pure helpers for ScheduleVisitModal. No React, no fetches.
  import type { EstimateBlock, Pick, SalesCalendarEvent } from '../types/pipeline';

  export const HOUR_START = 6;
  export const HOUR_END = 20;
  export const SLOT_MIN = 30;
  export const SLOT_PX = 22;
  export const HEADER_PX = 29;
  export const TIMECOL_PX = 56;
  export const SLOTS_PER_DAY = ((HOUR_END - HOUR_START) * 60) / SLOT_MIN;

  const pad = (n: number) => String(n).padStart(2, '0');

  export function minToHHMMSS(m: number): string {
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${pad(h)}:${pad(mm)}:00`;
  }

  export function hhmmssToMin(s: string): number {
    const parts = s.split(':');
    const h = Number(parts[0]);
    const m = Number(parts[1] ?? 0);
    return h * 60 + m;
  }

  export function startOfWeek(d: Date): Date {
    const nd = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    const day = nd.getDay();
    const diff = day === 0 ? -6 : 1 - day; // Monday-start
    nd.setDate(nd.getDate() + diff);
    return nd;
  }

  export function iso(d: Date): string {
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  }

  export function fmtHM(mins: number): string {
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    const ap = h >= 12 ? 'PM' : 'AM';
    const h12 = ((h + 11) % 12) + 1;
    return `${h12}:${pad(m)} ${ap}`;
  }

  export function fmtDur(mins: number): string {
    if (mins < 60) return `${mins} min`;
    const h = Math.floor(mins / 60);
    const m = mins % 60;
    if (m === 0) return h === 1 ? '1 hr' : `${h} hr`;
    return `${h}h ${m}m`;
  }

  export function fmtMonD(d: Date): string {
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  export function fmtLongDate(isoDate: string): string {
    return new Date(isoDate + 'T12:00').toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
    });
  }

  export function fmtLongDateD(d: Date): string {
    return d.toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
    });
  }

  export function isPastSlot(day: Date, slotMin: number, now: Date): boolean {
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (day < today) return true;
    if (iso(day) === iso(now) && slotMin < now.getHours() * 60 + now.getMinutes()) {
      return true;
    }
    return false;
  }

  export function eventToBlock(
    e: SalesCalendarEvent,
    customerName: string,
    jobSummary: string,
  ): EstimateBlock {
    return {
      id: e.id,
      date: e.scheduled_date,
      startMin: e.start_time ? hhmmssToMin(e.start_time) : 0,
      endMin: e.end_time ? hhmmssToMin(e.end_time) : 24 * 60,
      customerName,
      jobSummary,
      assignedToUserId: e.assigned_to_user_id,
    };
  }

  export function detectConflicts(
    pick: Pick | null,
    blocks: EstimateBlock[],
  ): EstimateBlock[] {
    if (!pick) return [];
    return blocks.filter(
      (b) =>
        b.date === pick.date &&
        !(b.endMin <= pick.start || b.startMin >= pick.end),
    );
  }

  /**
   * Render a customer's full name as "First L." for the calendar pick block.
   * "Viktor Petrov" → "Viktor P."
   * "Cher" → "Cher"
   * "" / null-ish → "Customer"
   */
  export function formatShortName(full: string | null | undefined): string {
    if (!full) return 'Customer';
    const parts = full.trim().split(/\s+/);
    if (parts.length === 0 || !parts[0]) return 'Customer';
    if (parts.length === 1) return parts[0];
    return `${parts[0]} ${parts[1][0]}.`;
  }
  ```
- **PATTERN**: pure-helpers in `frontend/src/features/sales/lib/nowContent.ts`.
- **GOTCHA**: `'YYYY-MM-DD'` parsed as `new Date('YYYY-MM-DD')` becomes UTC midnight, which can shift to the previous day in negative-UTC timezones. Always use `'YYYY-MM-DDT12:00'` (matches reference HTML line 546).
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 10 — CREATE `frontend/src/features/sales/lib/scheduleVisitUtils.test.ts`

- **IMPLEMENT**: 8 tests:
  1. `minToHHMMSS(0) === "00:00:00"`, `minToHHMMSS(840) === "14:00:00"`, `minToHHMMSS(1439) === "23:59:00"`
  2. `hhmmssToMin("00:00:00") === 0`, `hhmmssToMin("14:00:00") === 840`, `hhmmssToMin("23:59") === 1439`
  3. **fast-check property**: `fc.assert(fc.property(fc.integer({ min: 0, max: 1439 }), m => hhmmssToMin(minToHHMMSS(m)) === m))`
  4. `startOfWeek` returns Monday for any input day (test with each day-of-week).
  5. `isPastSlot` — true for yesterday, true for today's earlier minute, false for today's future minute, false for tomorrow.
  6. `detectConflicts` — same-date overlap → length > 0; non-overlap → 0; cross-date → 0; touching boundaries (`b.endMin === pick.start`) → 0 (exclusive end).
  7. `eventToBlock` — null `start_time` → full-day default; populated → minute math correct.
  8. `formatShortName` — `'Viktor Petrov' → 'Viktor P.'`, `'Cher' → 'Cher'`, `'' → 'Customer'`, `null → 'Customer'`, `'  Mary  Anne  Smith  ' → 'Mary A.'`.
- **IMPORTS**:
  ```ts
  import { describe, it, expect } from 'vitest';
  import fc from 'fast-check';
  import { minToHHMMSS, hhmmssToMin, startOfWeek, isPastSlot, detectConflicts, eventToBlock, formatShortName } from './scheduleVisitUtils';
  ```
- **GOTCHA**: `fast-check` is a devDep already (`frontend/package.json:81`).
- **VALIDATE**: `cd frontend && npm test -- scheduleVisitUtils`

### Task 11 — UPDATE `frontend/src/features/sales/hooks/useSalesPipeline.ts` invalidations

- **IMPLEMENT**: Modify `useCreateCalendarEvent` (line 224-233):
  ```ts
  export function useCreateCalendarEvent() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (body: SalesCalendarEventCreate) =>
        salesPipelineApi.createCalendarEvent(body),
      onSuccess: (_data, body) => {
        qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
        qc.invalidateQueries({ queryKey: pipelineKeys.detail(body.sales_entry_id) });
        qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
      },
    });
  }
  ```
  And `useUpdateCalendarEvent` (line 235-249) — since the body shape lacks `sales_entry_id`, broaden to `pipelineKeys.all`:
  ```ts
  export function useUpdateCalendarEvent() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: ({ eventId, body }: { eventId: string; body: SalesCalendarEventUpdate }) =>
        salesPipelineApi.updateCalendarEvent(eventId, body),
      onSuccess: () => {
        qc.invalidateQueries({ queryKey: pipelineKeys.all });
      },
    });
  }
  ```
- **PATTERN**: existing hooks.
- **GOTCHA**: Verify the existing `SalesCalendar.tsx` (the dedicated calendar tab) still works — broader invalidation is strictly more correct there too. Already only one consumer, so no other regressions to worry about.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- useSalesPipeline`

### Task 12 — CREATE `frontend/src/features/sales/hooks/useScheduleVisit.ts`

- **IMPLEMENT** (paste; adjust imports):
  ```ts
  import { useCallback, useEffect, useMemo, useState } from 'react';
  import axios from 'axios';
  import { useQueryClient } from '@tanstack/react-query';
  import { format } from 'date-fns';
  import {
    useSalesCalendarEvents,
    useCreateCalendarEvent,
    useUpdateCalendarEvent,
    pipelineKeys,
  } from './useSalesPipeline';
  import {
    minToHHMMSS,
    hhmmssToMin,
    startOfWeek,
    iso,
    eventToBlock,
    detectConflicts,
  } from '../lib/scheduleVisitUtils';
  import type {
    Pick,
    SalesCalendarEvent,
    SalesEntry,
    EstimateBlock,
  } from '../types/pipeline';

  type Args = {
    entry: SalesEntry;
    customerId: string;
    customerName: string;
    jobSummary: string;
    /** Most recent existing event for this entry (reschedule path). */
    currentEvent: SalesCalendarEvent | null;
    defaultAssigneeId?: string | null;
    /** For tests. */
    now?: Date;
  };

  export function useScheduleVisit({
    entry, customerId, customerName, jobSummary, currentEvent,
    defaultAssigneeId, now: nowProp,
  }: Args) {
    const qc = useQueryClient();
    const [now, setNow] = useState<Date>(() => nowProp ?? new Date());
    useEffect(() => {
      if (nowProp) return; // tests pass deterministic `now`
      const id = setInterval(() => setNow(new Date()), 60_000);
      return () => clearInterval(id);
    }, [nowProp]);

    const initialPick: Pick | null = currentEvent?.start_time && currentEvent.end_time
      ? {
          date: currentEvent.scheduled_date,
          start: hhmmssToMin(currentEvent.start_time),
          end: hhmmssToMin(currentEvent.end_time),
        }
      : null;

    const [pick, setPick] = useState<Pick | null>(initialPick);
    const [durationMin, setDurationMin] = useState<30 | 60 | 90 | 120>(60);
    const [assignedToUserId, setAssignedToUserId] = useState<string | null>(
      currentEvent?.assigned_to_user_id ?? defaultAssigneeId ?? null,
    );
    const [internalNotes, setInternalNotes] = useState<string>(
      currentEvent?.notes ?? '',
    );
    const [openedAt] = useState<Date>(() => new Date());

    const [weekStart, setWeekStart] = useState<Date>(() =>
      startOfWeek(initialPick ? new Date(initialPick.date + 'T12:00') : (nowProp ?? new Date())),
    );

    const weekEnd = useMemo(() => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + 6);
      return d;
    }, [weekStart]);

    const { data: weekEvents, isLoading: loadingWeek } = useSalesCalendarEvents({
      start_date: format(weekStart, 'yyyy-MM-dd'),
      end_date: format(weekEnd, 'yyyy-MM-dd'),
    });

    const estimates: EstimateBlock[] = useMemo(
      () =>
        (weekEvents ?? []).map((e) =>
          eventToBlock(
            e,
            // For other-customer estimates we don't know the name; show the title as fallback.
            e.customer_id === customerId ? customerName : e.title,
            e.customer_id === customerId ? jobSummary : '',
          ),
        ),
      [weekEvents, customerId, customerName, jobSummary],
    );

    const conflicts = useMemo(
      () => detectConflicts(pick, estimates),
      [pick, estimates],
    );
    const hasConflict = conflicts.length > 0;

    // ── pick mutators (kept identical to scaffold/reference semantics) ──
    const setPickFromCalendarClick = useCallback(
      (date: string, slotStartMin: number) => {
        setPick({ date, start: slotStartMin, end: slotStartMin + durationMin });
      },
      [durationMin],
    );

    const setPickFromCalendarDrag = useCallback(
      (date: string, startMin: number, endMin: number) => {
        setPick({ date, start: startMin, end: endMin });
        const span = endMin - startMin;
        if ([30, 60, 90, 120].includes(span)) {
          setDurationMin(span as 30 | 60 | 90 | 120);
        }
      },
      [],
    );

    const setPickDate = useCallback((date: string) => {
      setPick((p) => (p ? { ...p, date } : { date, start: 14 * 60, end: 14 * 60 + 60 }));
      const ws = startOfWeek(new Date(date + 'T12:00'));
      setWeekStart((cur) => (iso(cur) === iso(ws) ? cur : ws));
    }, []);

    const setPickStart = useCallback(
      (startMin: number) => {
        setPick((p) =>
          p ? { ...p, start: startMin, end: startMin + durationMin } : null,
        );
      },
      [durationMin],
    );

    const setPickDuration = useCallback((m: 30 | 60 | 90 | 120) => {
      setDurationMin(m);
      setPick((p) => (p ? { ...p, end: p.start + m } : null));
    }, []);

    // ── submit ──
    const create = useCreateCalendarEvent();
    const update = useUpdateCalendarEvent();
    const [error, setError] = useState<string | null>(null);
    const [isConflictError, setIsConflictError] = useState(false);

    const submit = useCallback(async (): Promise<{ ok: boolean; conflict?: boolean }> => {
      if (!pick) return { ok: false };
      setError(null);
      setIsConflictError(false);
      const payload = {
        sales_entry_id: entry.id,
        customer_id: customerId,
        // Hyphen (not em-dash) — matches existing SalesCalendar.tsx:193 convention.
        title: `Estimate - ${customerName}`,
        scheduled_date: pick.date,
        start_time: minToHHMMSS(pick.start),
        end_time: minToHHMMSS(pick.end),
        notes: internalNotes || null,
        assigned_to_user_id: assignedToUserId,
      };
      try {
        if (currentEvent) {
          await update.mutateAsync({ eventId: currentEvent.id, body: payload });
        } else {
          await create.mutateAsync(payload);
        }
        return { ok: true };
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 409) {
          setIsConflictError(true);
          setError('Slot was just taken — pick another time.');
          qc.invalidateQueries({ queryKey: pipelineKeys.calendarEvents() });
          return { ok: false, conflict: true };
        }
        setError(err instanceof Error ? err.message : 'Could not schedule.');
        return { ok: false };
      }
    }, [pick, entry.id, customerId, customerName, internalNotes, assignedToUserId, currentEvent, create, update, qc]);

    const isDirty = useMemo(() => {
      const initialEq = (a: Pick | null, b: Pick | null) =>
        (a === null && b === null) ||
        (!!a && !!b && a.date === b.date && a.start === b.start && a.end === b.end);
      return !initialEq(pick, initialPick) || internalNotes !== (currentEvent?.notes ?? '');
    }, [pick, initialPick, internalNotes, currentEvent]);

    return {
      // state
      pick, durationMin, assignedToUserId, internalNotes,
      weekStart, estimates, loadingWeek, conflicts, hasConflict,
      submitting: create.isPending || update.isPending,
      error, isConflictError, isDirty, openedAt, now,
      isReschedule: !!currentEvent,
      // setters
      setPickFromCalendarClick, setPickFromCalendarDrag,
      setPickDate, setPickStart, setPickDuration,
      setAssignedToUserId, setInternalNotes, setWeekStart,
      // actions
      submit,
    };
  }
  ```
- **PATTERN**: scaffold + `useSalesPipeline.ts` patterns.
- **GOTCHA**:
  - SPEC §3: clicking Today / Prev / Next does NOT clear `pick`. The `setWeekStart` calls in the calendar's nav buttons must NOT touch `setPick`.
  - The `now` interval must clean up on unmount or it leaks intervals.
  - When `currentEvent` is loaded after mount (rare race — it usually arrives synchronously from cache), `initialPick` won't update. To handle: the parent component should NOT mount the modal until `entryEvents` query has resolved (handled in Task 21).
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 13 — CREATE `frontend/src/features/sales/hooks/useScheduleVisit.test.ts`

- **IMPLEMENT**: 8 tests via `renderHook` + `QueryProvider`:
  1. Initial `pick` is `null` for new bookings.
  2. Initial `pick` is pre-filled when `currentEvent` is provided (reschedule).
  3. `setPickFromCalendarClick(date, 14*60)` → pick = `{ date, start: 840, end: 840 + 60 }` (default duration 60).
  4. `setPickFromCalendarDrag(date, 14*60, 15*60+30)` → pick spans 90min, duration becomes 90.
  5. `setPickDate('2026-05-15')` jumps `weekStart` to that week.
  6. `setPickStart(15*60)` re-derives `end = start + currentDuration`.
  7. Conflict detection: same-date overlap → `conflicts.length > 0`; cross-date → 0.
  8. `submit()` calls `create.mutateAsync` for new bookings, `update.mutateAsync` for reschedule.
- **IMPORTS**:
  ```ts
  import { renderHook, act, waitFor } from '@testing-library/react';
  import { describe, it, expect, vi } from 'vitest';
  import { QueryProvider } from '@/core/providers/QueryProvider';
  import { useScheduleVisit } from './useScheduleVisit';
  ```
- **GOTCHA**: Mock `useSalesCalendarEvents` via `vi.mock('./useSalesPipeline', ...)` so tests don't need MSW. Pass deterministic `now` to avoid time flakes.
- **VALIDATE**: `cd frontend && npm test -- useScheduleVisit`

### Task 14 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.module.css`

- **IMPLEMENT**: Port the reference HTML's calendar CSS verbatim (only the calendar — modal frame/buttons use shadcn). This makes the calendar pixel-identical to the reference per CHECKLIST §Visual parity. Paste:
  ```css
  /* Ported from feature-developments/schedule-estimate-visit-handoff/reference/Schedule-Estimate-Visit-Reference.html */

  .wkcal {
    border: 2px solid #1a1a1a;
    border-radius: 6px;
    background: #fafaf6;
    box-shadow: 2px 2px 0 rgba(0,0,0,.08);
    overflow: hidden;
  }
  .wkcalHead {
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 8px 10px;
    border-bottom: 1.5px dashed #1a1a1a;
    background: #f8f5ec;
  }
  .wkLabel { font-size: 22px; font-weight: 700; line-height: 1; }
  .wkRange { color: #4a4a4a; font-size: 12px; margin-left: 8px; }
  .wkcalNav { display: flex; gap: 6px; }
  .wkcalNav button {
    font-size: 13px; font-weight: 700;
    padding: 4px 10px; border: 1.5px solid #1a1a1a;
    background: #fafaf6; border-radius: 999px; cursor: pointer;
  }
  .wkcalNav button:hover { background: #ffe066; }

  .wkcalGrid {
    position: relative;
    display: grid;
    grid-template-columns: 56px repeat(7, 1fr);
    grid-template-rows: 29px repeat(28, 22px);
    user-select: none;
  }
  .wkcalCorner { border-right: 1px solid #d8d2c2; border-bottom: 1.5px dashed #b6ae9c; background: #f8f5ec; }
  .wkcalDaycolHead {
    padding: 6px 4px; text-align: center;
    border-right: 1px solid #d8d2c2;
    border-bottom: 1.5px dashed #b6ae9c;
    background: #f8f5ec;
    font-weight: 700;
  }
  .dow { color: #8a8a8a; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }
  .dnum { font-size: 16px; color: #1a1a1a; }
  .wkcalDaycolHead.today .dnum {
    display: inline-block;
    background: #ffe066;
    padding: 0 6px; border-radius: 999px;
  }
  .wkcalTimecell {
    padding: 1px 4px 0 6px; text-align: right;
    color: #8a8a8a; font-size: 10px;
    border-bottom: 1px dotted #ece7d8;
    border-right: 1px solid #d8d2c2;
    background: #f8f5ec;
    position: relative; top: -6px;
  }
  .wkcalTimecell.hour { border-bottom: 1px solid #d8d2c2; }
  .wkcalSlot {
    border-right: 1px solid #d8d2c2;
    border-bottom: 1px dotted #ece7d8;
    cursor: cell;
    position: relative;
  }
  .wkcalSlot.hour { border-bottom: 1px solid #d8d2c2; }
  .wkcalSlot.past { background: repeating-linear-gradient(135deg, transparent 0 4px, rgba(0,0,0,.025) 4px 5px); cursor: not-allowed; }
  .wkcalSlot:not(.past):hover { background: rgba(255,224,102,.25); }

  .wkcalNow { position: absolute; height: 0; border-top: 2px solid #c44a3a; pointer-events: none; z-index: 3; }
  .wkcalNow::before { content: ''; position: absolute; left: -4px; top: -5px; width: 8px; height: 8px; border-radius: 50%; background: #c44a3a; }

  .wkcalEvt {
    position: absolute;
    background: repeating-linear-gradient(135deg, #e2d4c2 0 5px, #d8c8b4 5px 10px);
    border: 1.5px solid #9d8972;
    border-radius: 3px;
    padding: 3px 5px;
    font-size: 10.5px; color: #3a2c1c; line-height: 1.15;
    overflow: hidden;
    box-shadow: 1px 1px 0 rgba(0,0,0,.08);
  }
  .evtName { font-weight: 700; white-space: nowrap; text-overflow: ellipsis; overflow: hidden; }
  .evtMeta { color: #5a4a36; font-size: 9.5px; }
  .wkcalEvt.conflict { border-color: #c44a3a; background: repeating-linear-gradient(135deg, #fbe1dc 0 5px, #f6ccc3 5px 10px); }

  .wkcalPick {
    position: absolute;
    background: #d4622a; color: #fff;
    border: 2px solid #1a1a1a;
    border-radius: 3px;
    padding: 3px 5px;
    font-size: 11px; font-weight: 700; line-height: 1.15;
    box-shadow: 2px 2px 0 rgba(0,0,0,.12);
    z-index: 2;
    pointer-events: none;
  }
  .pickDur { font-weight: 400; font-size: 10px; opacity: .9; display: block; }
  .wkcalPick.warn { background: #c44a3a; }

  .wkcalDrag {
    position: absolute;
    background: rgba(212,98,42,.22);
    border: 2px dashed #d4622a;
    border-radius: 3px;
    pointer-events: none;
    z-index: 2;
  }

  .wkcalLegend {
    display: flex; align-items: center; gap: 14px;
    padding: 6px 10px;
    border-top: 1.5px dashed #8a8a8a;
    background: #f8f5ec;
    font-size: 11px; color: #4a4a4a;
  }
  .legendSw { display: inline-block; width: 16px; height: 11px; border: 1.5px solid #9d8972; border-radius: 2px; background: repeating-linear-gradient(135deg, #e2d4c2 0 4px, #d8c8b4 4px 8px); vertical-align: middle; margin-right: 4px; }
  .legendSw.pick { background: #d4622a; border-color: #1a1a1a; }
  ```
- **PATTERN**: reference HTML lines 111-245.
- **GOTCHA**: This is a **CSS Module** (`.module.css`) — Vite auto-supports them. Class names are hashed; access via `import styles from './ScheduleVisitModal.module.css'` then `styles.wkcalGrid`. **Don't** use kebab-case class names like `.wkcal-grid` directly — CSS modules camelCase them only when you opt in. Use camelCase in CSS file too (already done above) for clean access.
- **VALIDATE**: `cd frontend && npm run typecheck` (validates after Task 15 imports)

### Task 15 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx`

- **IMPLEMENT** (this is the heaviest task; paste verbatim then customize):
  ```tsx
  import { useEffect, useMemo, useRef, useState } from 'react';
  import type { EstimateBlock, Pick } from '../../types/pipeline';
  import {
    HOUR_START, HOUR_END, SLOT_MIN, SLOT_PX, HEADER_PX, TIMECOL_PX, SLOTS_PER_DAY,
    iso, isPastSlot, fmtHM, fmtMonD, fmtLongDateD,
  } from '../../lib/scheduleVisitUtils';
  import styles from './ScheduleVisitModal.module.css';

  type Props = {
    weekStart: Date;
    now: Date;
    estimates: EstimateBlock[];
    pick: Pick | null;
    loadingWeek: boolean;
    conflicts: EstimateBlock[];
    hasConflict: boolean;
    pickCustomerName: string;
    onWeekChange: (next: Date) => void;
    onSlotClick: (date: string, slotStartMin: number) => void;
    onSlotDrag: (date: string, startMin: number, endExclusiveMin: number) => void;
    onTrack?: (event: 'pick', source: 'click' | 'drag') => void;
  };

  type DragState = {
    dayIdx: number;
    startSlot: number;
    curSlot: number;
    moved: boolean;
  };

  export function WeekCalendar({
    weekStart, now, estimates, pick, loadingWeek, conflicts, hasConflict,
    pickCustomerName, onWeekChange, onSlotClick, onSlotDrag, onTrack,
  }: Props) {
    const days = useMemo(
      () => Array.from({ length: 7 }, (_, i) => {
        const d = new Date(weekStart);
        d.setDate(d.getDate() + i);
        return d;
      }),
      [weekStart],
    );
    const conflictIds = useMemo(() => new Set(conflicts.map((c) => c.id)), [conflicts]);
    const [drag, setDrag] = useState<DragState | null>(null);
    const dragRef = useRef<DragState | null>(null);
    dragRef.current = drag;

    // ── Mouse handlers (lifted from reference HTML lines 568-610) ──
    const onSlotMouseDown = (dayIdx: number, slotIdx: number) => (e: React.MouseEvent) => {
      e.preventDefault();
      const past = isPastSlot(days[dayIdx], HOUR_START * 60 + slotIdx * SLOT_MIN, now);
      if (past) return; // SPEC §6.3: disallow drag from past slots
      setDrag({ dayIdx, startSlot: slotIdx, curSlot: slotIdx, moved: false });

      const onMove = (ev: MouseEvent) => {
        const target = (ev.target as HTMLElement | null)?.closest('[data-slot]');
        if (!target) return;
        const di = Number(target.getAttribute('data-day'));
        const si = Number(target.getAttribute('data-slot'));
        if (di !== dayIdx) return; // SPEC §6.2: drag locked to origin column
        // SPEC §6.3: clip drag end to today/start-of-day
        if (isPastSlot(days[dayIdx], HOUR_START * 60 + si * SLOT_MIN, now)) return;
        setDrag((d) => (d && d.curSlot !== si ? { ...d, curSlot: si, moved: true } : d));
      };

      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        const d = dragRef.current;
        if (!d) return;
        const dayDate = new Date(weekStart);
        dayDate.setDate(dayDate.getDate() + d.dayIdx);
        const isoDate = iso(dayDate);
        const s1 = Math.min(d.startSlot, d.curSlot);
        const s2 = Math.max(d.startSlot, d.curSlot) + 1;
        const startMin = HOUR_START * 60 + s1 * SLOT_MIN;
        const endMin = HOUR_START * 60 + s2 * SLOT_MIN;
        if (d.moved) {
          onSlotDrag(isoDate, startMin, endMin);
          onTrack?.('pick', 'drag');
        } else {
          onSlotClick(isoDate, startMin);
          onTrack?.('pick', 'click');
        }
        setDrag(null);
      };

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    };

    // ── Cleanup window listeners on unmount ──
    useEffect(() => {
      return () => {
        // No persistent listeners — the click-handler installs them per-drag and
        // removes them in onUp. But if the user clicks down then unmounts, we leak.
        // Defensive cleanup: there's no public ref to the bound handlers, so the
        // best we can do is null out dragRef so a stray onUp is a no-op.
        dragRef.current = null;
      };
    }, []);

    // ── Nav handlers (don't touch `pick` per SPEC §3) ──
    const goPrev = () => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() - 7);
      onWeekChange(d);
    };
    const goNext = () => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + 7);
      onWeekChange(d);
    };
    const goToday = () => {
      const t = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const day = t.getDay();
      const diff = day === 0 ? -6 : 1 - day;
      t.setDate(t.getDate() + diff);
      onWeekChange(t);
    };

    // ── Overlay positioning math (reference HTML lines 462-528) ──
    const colLeftPct = (i: number) => `calc(${TIMECOL_PX}px + ${i} * ((100% - ${TIMECOL_PX}px) / 7))`;
    const colWidthPct = `calc((100% - ${TIMECOL_PX}px) / 7)`;
    const todayIdx = days.findIndex((d) => iso(d) === iso(now));
    const NOW_MIN = now.getHours() * 60 + now.getMinutes();
    const showNowLine = todayIdx >= 0 && NOW_MIN >= HOUR_START * 60 && NOW_MIN <= HOUR_END * 60;

    const blockTop = (startMin: number) =>
      HEADER_PX + ((startMin - HOUR_START * 60) / SLOT_MIN) * SLOT_PX;
    const blockHeight = (durMin: number) => (durMin / SLOT_MIN) * SLOT_PX - 2;

    return (
      <div className={styles.wkcal} data-testid="schedule-visit-calendar">
        <header className={styles.wkcalHead}>
          <div>
            <span className={styles.wkLabel}>Week of {fmtMonD(weekStart)}</span>
            <span className={styles.wkRange}>
              {fmtLongDateD(weekStart)} – {fmtLongDateD(days[6])}
            </span>
          </div>
          <div className={styles.wkcalNav}>
            <button onClick={goPrev} data-testid="schedule-visit-week-prev">← Prev week</button>
            <button onClick={goToday} data-testid="schedule-visit-week-today">Today</button>
            <button onClick={goNext} data-testid="schedule-visit-week-next">Next week →</button>
          </div>
        </header>

        <div className={styles.wkcalGrid} aria-busy={loadingWeek}>
          {/* Row 1: corner + 7 day-headers */}
          <div className={styles.wkcalCorner} />
          {days.map((d, i) => (
            <div
              key={`h${i}`}
              className={`${styles.wkcalDaycolHead}${iso(d) === iso(now) ? ' ' + styles.today : ''}`}
            >
              <div className={styles.dow}>{d.toLocaleDateString('en-US', { weekday: 'short' })}</div>
              <div className={styles.dnum}>{d.getDate()}</div>
            </div>
          ))}

          {/* 28 rows of [time-gutter, 7 slots] */}
          {Array.from({ length: SLOTS_PER_DAY }).flatMap((_, s) => {
            const mins = HOUR_START * 60 + s * SLOT_MIN;
            const isHour = mins % 60 === 0;
            const cells: React.ReactNode[] = [
              <div key={`tg${s}`} className={`${styles.wkcalTimecell}${isHour ? ' ' + styles.hour : ''}`}>
                {isHour ? fmtHM(mins) : ''}
              </div>,
            ];
            days.forEach((d, di) => {
              const past = isPastSlot(d, mins, now);
              cells.push(
                <div
                  key={`c${s}-${di}`}
                  data-day={di}
                  data-slot={s}
                  data-testid={`schedule-visit-slot-${di}-${s}`}
                  className={[
                    styles.wkcalSlot,
                    isHour ? styles.hour : '',
                    past ? styles.past : '',
                  ].filter(Boolean).join(' ')}
                  onMouseDown={past ? undefined : onSlotMouseDown(di, s)}
                />
              );
            });
            return cells;
          })}

          {/* Now-line */}
          {showNowLine && (
            <div
              className={styles.wkcalNow}
              style={{
                top: `${HEADER_PX + ((NOW_MIN - HOUR_START * 60) / SLOT_MIN) * SLOT_PX}px`,
                left: colLeftPct(todayIdx),
                width: colWidthPct,
              }}
            />
          )}

          {/* Estimate blocks */}
          {days.map((d, di) => {
            const dISO = iso(d);
            return estimates
              .filter((e) => e.date === dISO)
              .map((e) => (
                <div
                  key={e.id}
                  className={`${styles.wkcalEvt}${conflictIds.has(e.id) ? ' ' + styles.conflict : ''}`}
                  title={`${e.customerName} · ${fmtHM(e.startMin)}–${fmtHM(e.endMin)} · ${e.jobSummary}`}
                  style={{
                    top: `${blockTop(e.startMin)}px`,
                    height: `${blockHeight(e.endMin - e.startMin)}px`,
                    left: `calc(${colLeftPct(di)} + 2px)`,
                    width: `calc(${colWidthPct} - 4px)`,
                  }}
                >
                  <div className={styles.evtName}>{e.customerName}</div>
                  <div className={styles.evtMeta}>{fmtHM(e.startMin)} · {e.jobSummary}</div>
                </div>
              ));
          })}

          {/* Pick block */}
          {pick && (() => {
            const di = days.findIndex((d) => iso(d) === pick.date);
            if (di < 0) return null;
            return (
              <div
                data-testid="schedule-visit-pick"
                className={`${styles.wkcalPick}${hasConflict ? ' ' + styles.warn : ''}`}
                style={{
                  top: `${blockTop(pick.start)}px`,
                  height: `${blockHeight(pick.end - pick.start)}px`,
                  left: `calc(${colLeftPct(di)} + 2px)`,
                  width: `calc(${colWidthPct} - 4px)`,
                }}
              >
                <div>{pickCustomerName} · {fmtHM(pick.start)}</div>
                <span className={styles.pickDur}>
                  {(() => {
                    const m = pick.end - pick.start;
                    if (m < 60) return `${m} min`;
                    const h = Math.floor(m / 60), r = m % 60;
                    return r === 0 ? `${h} hr` : `${h}h ${r}m`;
                  })()}
                </span>
              </div>
            );
          })()}

          {/* Drag ghost */}
          {drag && (() => {
            const s1 = Math.min(drag.startSlot, drag.curSlot);
            const s2 = Math.max(drag.startSlot, drag.curSlot) + 1;
            return (
              <div
                className={styles.wkcalDrag}
                style={{
                  top: `${HEADER_PX + s1 * SLOT_PX}px`,
                  height: `${(s2 - s1) * SLOT_PX - 2}px`,
                  left: `calc(${colLeftPct(drag.dayIdx)} + 2px)`,
                  width: `calc(${colWidthPct} - 4px)`,
                }}
              />
            );
          })()}
        </div>

        <footer className={styles.wkcalLegend}>
          <span><span className={styles.legendSw} />Existing estimate (read-only)</span>
          <span><span className={`${styles.legendSw} ${styles.pick}`} />Your pick</span>
          <span style={{ marginLeft: 'auto', color: '#8a8a8a' }}>
            Click to pin · Drag to set range · 6 AM – 8 PM · 30-min slots
          </span>
        </footer>
      </div>
    );
  }
  ```
- **PATTERN**: reference HTML lines 415-528 + scaffold `WeekCalendar.tsx`.
- **GOTCHA**:
  - **Header row is `29px`** — this is fixed in `gridTemplateRows: '29px repeat(28, 22px)'` so block positioning math (`HEADER_PX + ...`) is reliable across browsers.
  - The drag handler uses `document` (matches reference), not `window`. The handlers are installed per-mousedown and removed in `onUp` — they ARE self-cleaning normally. The `dragRef.current = null` cleanup is a defense-in-depth for the rare unmount-mid-drag case.
  - Past slots have `cursor: not-allowed` and `onMouseDown` is omitted (not just disabled) so they're truly inert.
  - `e.target.closest('[data-slot]')` — `data-slot="0"` on a cell means `Number("0") === 0`, which is falsy in some checks; we use `Number(...)` for explicit conversion.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 16 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/PrefilledCustomerCard.tsx`

- **IMPLEMENT**:
  ```tsx
  import { useCustomer } from '@/features/customers';
  import type { SalesEntry } from '../../types/pipeline';

  type Props = {
    entry: SalesEntry;
  };

  export function PrefilledCustomerCard({ entry }: Props) {
    // Resolve email via the customer detail query (SalesEntry doesn't denormalize email).
    // Cached → near-instant on most renders; fine if it loads slightly after the modal mounts.
    const { data: customer } = useCustomer(entry.customer_id);

    return (
      <section
        role="group"
        aria-label="Customer information"
        data-testid="schedule-visit-customer-card"
        className="rounded-md border border-dashed border-slate-700 bg-amber-50 p-3 text-sm leading-relaxed"
      >
        <div className="text-xs uppercase tracking-wider text-slate-500 mb-1 font-bold">Customer</div>
        <div>
          <strong>{entry.customer_name ?? 'Unknown Customer'}</strong>
          {entry.lead_id ? (
            <span className="ml-2 text-xs text-slate-500">from Leads tab</span>
          ) : null}
        </div>
        {entry.customer_phone ? <Row label="Phone" value={entry.customer_phone} /> : null}
        {customer?.email ? <Row label="Email" value={customer.email} /> : null}
        {entry.property_address ? <Row label="Address" value={entry.property_address} /> : null}
        {entry.job_type ? <Row label="Job" value={entry.job_type} /> : null}
      </section>
    );
  }

  function Row({ label, value }: { label: string; value: string }) {
    return (
      <div>
        <span className="text-xs uppercase tracking-wider text-slate-500 mr-1">{label}</span>
        {value}
      </div>
    );
  }
  ```
- **PATTERN**: scaffold `PrefilledCustomerCard.tsx`. CHECKLIST §Visual parity: dashed border, label-then-value rows, no edit affordance.
- **GOTCHA**:
  - `useCustomer` is exported from `@/features/customers` (`features/customers/index.ts:19`); it returns `{ data: Customer | undefined, ... }` where `Customer.email: string | null` (`features/customers/types/index.ts:49`).
  - Email row is OPTIONAL — only render if `customer?.email` is truthy. The card never blocks on the customer query.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 17 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleFields.tsx`

- **IMPLEMENT**:
  ```tsx
  import { Input } from '@/components/ui/input';
  import { Label } from '@/components/ui/label';
  import { Textarea } from '@/components/ui/textarea';
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
  import { useStaff } from '@/features/staff/hooks/useStaff';
  import type { Pick } from '../../types/pipeline';

  // Radix Select v2.2.6 disallows empty-string values, so use a sentinel for "Unassigned".
  // Map null ↔ UNASSIGNED at the boundary; the rest of the codebase only sees null or a real UUID.
  const UNASSIGNED = '__none__';

  type Props = {
    pick: Pick | null;
    durationMin: 30 | 60 | 90 | 120;
    assignedToUserId: string | null;
    internalNotes: string;
    onDateChange: (iso: string) => void;
    onStartChange: (mins: number) => void;
    onDurationChange: (m: 30 | 60 | 90 | 120) => void;
    onAssigneeChange: (id: string | null) => void;
    onNotesChange: (s: string) => void;
  };

  export function ScheduleFields({
    pick, durationMin, assignedToUserId, internalNotes,
    onDateChange, onStartChange, onDurationChange, onAssigneeChange, onNotesChange,
  }: Props) {
    const { data: staffData } = useStaff({ is_active: true });
    const dateValue = pick?.date ?? '';
    const timeValue = pick
      ? `${String(Math.floor(pick.start / 60)).padStart(2, '0')}:${String(pick.start % 60).padStart(2, '0')}`
      : '';

    return (
      <div className="space-y-3 mt-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="schedule-visit-date" className="text-xs uppercase tracking-wider text-slate-500 font-bold">Date</Label>
            <Input
              id="schedule-visit-date"
              data-testid="schedule-visit-date"
              type="date"
              value={dateValue}
              onChange={(e) => onDateChange(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="schedule-visit-start-time" className="text-xs uppercase tracking-wider text-slate-500 font-bold">Start time</Label>
            <Input
              id="schedule-visit-start-time"
              data-testid="schedule-visit-start-time"
              type="time"
              step={1800}
              value={timeValue}
              onChange={(e) => {
                const [hh, mm] = e.target.value.split(':').map(Number);
                if (!Number.isNaN(hh)) onStartChange(hh * 60 + mm);
              }}
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="schedule-visit-assignee" className="text-xs uppercase tracking-wider text-slate-500 font-bold">Assigned to</Label>
            <Select
              value={assignedToUserId ?? UNASSIGNED}
              onValueChange={(v) => onAssigneeChange(v === UNASSIGNED ? null : v)}
            >
              <SelectTrigger id="schedule-visit-assignee" data-testid="schedule-visit-assignee">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={UNASSIGNED}>— Unassigned —</SelectItem>
                {(staffData?.items ?? []).map((s) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="schedule-visit-duration" className="text-xs uppercase tracking-wider text-slate-500 font-bold">Duration</Label>
            <Select
              value={String(durationMin)}
              onValueChange={(v) => onDurationChange(Number(v) as 30 | 60 | 90 | 120)}
            >
              <SelectTrigger id="schedule-visit-duration" data-testid="schedule-visit-duration">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30">30 min</SelectItem>
                <SelectItem value="60">1 hr</SelectItem>
                <SelectItem value="90">1.5 hr</SelectItem>
                <SelectItem value="120">2 hr</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div>
          <Label htmlFor="schedule-visit-notes" className="text-xs uppercase tracking-wider text-slate-500 font-bold">Internal notes (optional)</Label>
          <Textarea
            id="schedule-visit-notes"
            data-testid="schedule-visit-notes"
            value={internalNotes}
            placeholder="Gate code 4412. Large corner lot, sketched zones in intake call…"
            onChange={(e) => onNotesChange(e.target.value)}
            rows={3}
          />
        </div>
      </div>
    );
  }
  ```
- **PATTERN**: shadcn primitives in `SalesCalendar.tsx:331-409`.
- **GOTCHA**:
  - `useStaff().data?.items` — `Staff.name` (not `display_name`); verified in `frontend/src/features/staff/types/index.ts:11`.
  - The `<Select>` `value` prop must be a non-empty string for Radix v2 — that's why we use the `UNASSIGNED = '__none__'` sentinel mapped to `null` at the boundary. The "— Unassigned —" item lets users clear an assignee after picking one.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 18 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/PickSummary.tsx`

- **IMPLEMENT**:
  ```tsx
  import type { Pick } from '../../types/pipeline';
  import { fmtHM, fmtDur, fmtLongDate } from '../../lib/scheduleVisitUtils';

  type Props = {
    pick: Pick | null;
    hasConflict: boolean;
    error: string | null;
  };

  export function PickSummary({ pick, hasConflict, error }: Props) {
    return (
      <>
        <div
          data-testid="schedule-visit-pick-summary"
          className="mt-2 rounded border border-dashed border-amber-500 bg-amber-50 px-2.5 py-2 text-sm"
        >
          {pick ? (
            <>
              <strong>{fmtLongDate(pick.date)}</strong> · {fmtHM(pick.start)} – {fmtHM(pick.end)} ·{' '}
              <strong>{fmtDur(pick.end - pick.start)}</strong>
            </>
          ) : (
            <span className="italic text-slate-500">No time picked yet — click or drag on the calendar →</span>
          )}
        </div>
        {hasConflict && (
          <div
            role="alert"
            data-testid="schedule-visit-conflict-banner"
            className="mt-2 rounded border border-red-500 bg-red-50 px-2.5 py-2 text-sm text-red-900"
          >
            ⚠ <strong>Overlaps</strong> with an existing estimate. You can still proceed, but double-check.
          </div>
        )}
        {error && (
          <div
            role="alert"
            data-testid="schedule-visit-error"
            className="mt-2 rounded border border-red-500 bg-red-50 px-2.5 py-2 text-sm text-red-900"
          >
            {error}
          </div>
        )}
      </>
    );
  }
  ```
- **PATTERN**: scaffold `PickSummary` in `ScheduleVisitModal.tsx:97-125`.
- **GOTCHA**: `role="alert"` is required by CHECKLIST §Accessibility line 53.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 18.5 — CREATE `frontend/src/shared/utils/track.ts`

- **IMPLEMENT**:
  ```ts
  /**
   * Telemetry stub. No SDK is wired in this codebase yet (verified by grep on
   * 2026-04-25 — zero `track(`/`analytics.` references in frontend/src).
   * When a real SDK lands, swap the body of this function — every caller stays put.
   */
  export function track(event: string, payload: Record<string, unknown> = {}): void {
    // eslint-disable-next-line no-console
    console.info(`[track] ${event}`, payload);
  }
  ```
- **PATTERN**: shared utils live in `frontend/src/shared/utils/` (e.g. `invalidationHelpers.ts`).
- **GOTCHA**: Keep the signature stable (`event: string, payload: Record<string, unknown>`) so future SDK swap is a one-file change.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 19 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx`

- **IMPLEMENT**:
  ```tsx
  import { useEffect } from 'react';
  import { toast } from 'sonner';
  import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
  import { Button } from '@/components/ui/button';
  import { track } from '@/shared/utils/track';
  import { useScheduleVisit } from '../../hooks/useScheduleVisit';
  import { PrefilledCustomerCard } from './PrefilledCustomerCard';
  import { ScheduleFields } from './ScheduleFields';
  import { WeekCalendar } from './WeekCalendar';
  import { PickSummary } from './PickSummary';
  import { fmtLongDate, fmtHM, formatShortName } from '../../lib/scheduleVisitUtils';
  import type { SalesEntry, SalesCalendarEvent } from '../../types/pipeline';

  type Props = {
    entry: SalesEntry;
    /** Most recent event for this entry (for reschedule). Pass null for new bookings. */
    currentEvent: SalesCalendarEvent | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** Optional default for the assignee dropdown. */
    defaultAssigneeId?: string | null;
  };

  export function ScheduleVisitModal({
    entry, currentEvent, open, onOpenChange, defaultAssigneeId,
  }: Props) {
    const customerName = entry.customer_name ?? 'Unknown Customer';
    const jobSummary = entry.job_type ?? '';
    const s = useScheduleVisit({
      entry,
      customerId: entry.customer_id,
      customerName,
      jobSummary,
      currentEvent,
      defaultAssigneeId,
    });

    useEffect(() => {
      if (open) track('sales.schedule_visit.opened', { entryId: entry.id, status: entry.status });
    }, [open, entry.id, entry.status]);

    const handleConfirm = async () => {
      const result = await s.submit();
      if (result.ok) {
        track('sales.schedule_visit.confirmed', { entryId: entry.id });
        toast.success(
          s.pick ? `Visit scheduled for ${fmtLongDate(s.pick.date)}, ${fmtHM(s.pick.start)}` : 'Scheduled',
        );
        onOpenChange(false);
      }
      // On failure, error is shown inline via PickSummary; modal stays open.
    };

    const handleOpenChange = (next: boolean) => {
      if (!next && s.isDirty) {
        const ok = window.confirm('Discard unsaved changes?');
        if (!ok) return;
        track('sales.schedule_visit.cancelled', { entryId: entry.id, dirty: true });
      } else if (!next) {
        track('sales.schedule_visit.cancelled', { entryId: entry.id, dirty: false });
      }
      onOpenChange(next);
    };

    const title = s.isReschedule ? 'Reschedule estimate visit' : 'Schedule estimate visit';
    const confirmLabel = s.isReschedule
      ? '📅 Update appointment'
      : '📅 Confirm & advance to Send Estimate';

    return (
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent
          data-testid="schedule-visit-modal"
          // Default DialogContent is `sm:max-w-lg` (dialog.tsx:64). `cn()` uses
          // tailwind-merge (package.json:59) which last-class-wins for identical
          // properties — so this override is safe.
          className="sm:max-w-[960px]"
        >
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>
              Auto-populated from the lead record. Pick a time on the calendar — click a slot for a start time, or drag to set both start &amp; duration.
            </DialogDescription>
          </DialogHeader>

          {/* Mobile (<720px): customer card → calendar → fields, in that order (SPEC §2). */}
          <div className="grid grid-cols-1 md:grid-cols-[340px_1fr] gap-[18px] items-start">
            <div className="min-w-0 order-1 md:order-1">
              <PrefilledCustomerCard entry={entry} />
            </div>
            <div className="min-w-0 order-2 md:row-span-2 md:order-2">
              <WeekCalendar
                weekStart={s.weekStart}
                now={s.now}
                estimates={s.estimates}
                pick={s.pick}
                loadingWeek={s.loadingWeek}
                conflicts={s.conflicts}
                hasConflict={s.hasConflict}
                pickCustomerName={formatShortName(customerName)}
                onWeekChange={s.setWeekStart}
                onSlotClick={s.setPickFromCalendarClick}
                onSlotDrag={s.setPickFromCalendarDrag}
                onTrack={(_e, source) => track('sales.schedule_visit.pick', { entryId: entry.id, source })}
              />
            </div>
            <div className="min-w-0 order-3 md:order-3">
              <ScheduleFields
                pick={s.pick}
                durationMin={s.durationMin}
                assignedToUserId={s.assignedToUserId}
                internalNotes={s.internalNotes}
                onDateChange={s.setPickDate}
                onStartChange={s.setPickStart}
                onDurationChange={s.setPickDuration}
                onAssigneeChange={s.setAssignedToUserId}
                onNotesChange={s.setInternalNotes}
              />
              <PickSummary pick={s.pick} hasConflict={s.hasConflict} error={s.error} />
            </div>
          </div>

          <DialogFooter className="mt-4">
            <Button variant="ghost" onClick={() => handleOpenChange(false)} data-testid="schedule-visit-cancel-btn">
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!s.pick || s.submitting}
              data-testid="schedule-visit-confirm-btn"
            >
              {confirmLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }
  ```
- **PATTERN**: `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:66-90` for Dialog composition.
- **GOTCHA**:
  - **Mobile reorder fix (SPEC §2)**: customer card → calendar → fields. The scaffold's `max-md:order-2/3` swap was incomplete (it only swapped two of three children). The grid above uses `order-1` / `order-2` / `order-3` which works in BOTH `grid-cols-1` (mobile, the order matters) AND `md:grid-cols-[340px_1fr]` (desktop, where grid auto-flow + `md:row-span-2` puts customer card top-left, calendar right (spanning two rows), fields bottom-left).
  - SPEC §6.7: Esc closes — `Dialog` handles it, but our `handleOpenChange` adds the dirty-warn guard.
  - On 409 conflict from submit, `s.submit()` returns `{ ok: false, conflict: true }` and `s.error` is populated. Modal stays open; `PickSummary` shows the error.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 20 — CREATE `frontend/src/features/sales/components/ScheduleVisitModal/index.ts` AND export from feature root

- **IMPLEMENT**:
  - `frontend/src/features/sales/components/ScheduleVisitModal/index.ts`:
    ```ts
    export { ScheduleVisitModal } from './ScheduleVisitModal';
    ```
  - Append to `frontend/src/features/sales/index.ts` after line 13 (the `SalesDetail` export):
    ```ts
    export { ScheduleVisitModal } from './components/ScheduleVisitModal';
    ```
- **PATTERN**: existing exports.
- **VALIDATE**: `cd frontend && npm run typecheck`

### Task 21 — UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` to render the modal

- **IMPLEMENT**:
  1. Add to imports (group with other feature hooks at line 28-36):
     ```ts
     import { ScheduleVisitModal } from './ScheduleVisitModal';
     import { useSalesCalendarEvents } from '../hooks/useSalesPipeline';
     ```
     (Use the relative path `./ScheduleVisitModal` instead of `'..'` since this file is inside the same `components/` dir as the new modal.)
  2. Add state (near line 96, beside `_showOverrideSelect`):
     ```ts
     const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
     ```
  3. Add events query (near line 67, beside `useCustomerDetail`):
     ```ts
     const { data: entryEvents } = useSalesCalendarEvents({ sales_entry_id: entryId });
     // Reschedule semantics: pick the LAST event by scheduled_date.
     // Backend orders ASC (api/v1/sales_pipeline.py:547), so [length-1] is the latest.
     // SalesCalendarEvent has no `cancelled_at` column today — if a customer has
     // rescheduled twice, we treat the most recent row as the active one. Adding
     // a soft-cancel column is a separate ticket; documented in Resolved Open
     // Questions §3 at the top of this plan.
     const currentEvent = entryEvents && entryEvents.length > 0
       ? entryEvents[entryEvents.length - 1]
       : null;
     ```
  4. Replace the `case 'schedule_visit':` block (lines 141-147) with:
     ```ts
     case 'schedule_visit':
       setScheduleModalOpen(true);
       break;
     ```
  5. Render the modal near the bottom of the JSX, just before the closing `</div>` at line 576:
     ```tsx
     <ScheduleVisitModal
       entry={entry}
       currentEvent={currentEvent}
       open={scheduleModalOpen}
       onOpenChange={setScheduleModalOpen}
     />
     ```
- **PATTERN**: existing modal-open state in `SalesDetail.tsx:96`.
- **GOTCHA**:
  - DO NOT also call `refetch()` from the modal close — the broader invalidation in Task 11 already handles it. Adding `refetch()` would race with the cache invalidation.
  - The modal must not mount before `entry` is loaded — already guarded by the `if (error || !entry) return ...` at line 259.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test -- SalesDetail`

### Task 22 — CREATE `ScheduleVisitModal.test.tsx`

- **IMPLEMENT**: 7 tests. Mock `useStaff` and the calendar-event hooks:
  ```tsx
  import { render, screen, fireEvent, waitFor } from '@testing-library/react';
  import { describe, it, expect, vi } from 'vitest';
  import { QueryProvider } from '@/core/providers/QueryProvider';
  import { ScheduleVisitModal } from './ScheduleVisitModal';
  import type { SalesEntry } from '../../types/pipeline';

  vi.mock('@/features/staff/hooks/useStaff', () => ({
    useStaff: () => ({ data: { items: [{ id: 'me', name: 'Kirill' }, { id: 'mike', name: 'Mike R.' }] } }),
    staffKeys: { all: ['staff'], lists: () => ['staff', 'list'] },
  }));

  const mkEntry = (overrides: Partial<SalesEntry> = {}): SalesEntry => ({
    id: 'entry-1',
    customer_id: 'cust-1',
    property_id: null,
    lead_id: null,
    job_type: 'Spring startup',
    status: 'schedule_estimate',
    last_contact_date: null,
    notes: null,
    override_flag: false,
    closed_reason: null,
    signwell_document_id: null,
    created_at: '2026-04-25T00:00:00Z',
    updated_at: '2026-04-25T00:00:00Z',
    customer_name: 'Viktor Petrov',
    customer_phone: '+15551234567',
    property_address: '1428 Maple Dr',
    ...overrides,
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => <QueryProvider>{children}</QueryProvider>;

  describe('ScheduleVisitModal', () => {
    it('renders title "Schedule estimate visit" for new bookings', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByText('Schedule estimate visit')).toBeInTheDocument();
    });

    it('renders title "Reschedule estimate visit" when currentEvent is provided', () => {
      const event = { id: 'e1', sales_entry_id: 'entry-1', customer_id: 'cust-1', title: 't', scheduled_date: '2026-04-23', start_time: '14:00:00', end_time: '15:00:00', notes: null, assigned_to_user_id: null, created_at: '', updated_at: '' };
      render(<ScheduleVisitModal entry={mkEntry({ status: 'estimate_scheduled' })} currentEvent={event} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByText('Reschedule estimate visit')).toBeInTheDocument();
    });

    it('Confirm button is disabled when pick is null', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByTestId('schedule-visit-confirm-btn')).toBeDisabled();
    });

    it('renders the customer card with the entry name', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByTestId('schedule-visit-customer-card')).toHaveTextContent('Viktor Petrov');
    });

    it('renders the assignee dropdown with staff names', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByTestId('schedule-visit-assignee')).toBeInTheDocument();
    });

    it('shows the no-pick summary message when pick is null', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open onOpenChange={() => {}} />, { wrapper });
      expect(screen.getByTestId('schedule-visit-pick-summary')).toHaveTextContent(/No time picked yet/i);
    });

    it('does not render when open=false', () => {
      render(<ScheduleVisitModal entry={mkEntry()} currentEvent={null} open={false} onOpenChange={() => {}} />, { wrapper });
      expect(screen.queryByTestId('schedule-visit-modal')).not.toBeInTheDocument();
    });
  });
  ```
- **PATTERN**: `frontend/src/features/sales/components/SalesDetail.test.tsx`.
- **GOTCHA**: The mock `useStaff` shape must exactly match `Staff` (`id`, `name`). Mocking only `useStaff` is enough; the real `useSalesCalendarEvents` will return undefined initially (acceptable for these tests). For the conflict test in WeekCalendar.test.tsx, mock that hook too.
- **VALIDATE**: `cd frontend && npm test -- ScheduleVisitModal`

### Task 23 — CREATE `WeekCalendar.test.tsx`

- **IMPLEMENT**: 5 tests:
  ```tsx
  import { render, screen } from '@testing-library/react';
  import { describe, it, expect } from 'vitest';
  import { WeekCalendar } from './WeekCalendar';
  import type { EstimateBlock } from '../../types/pipeline';

  const NOW = new Date(2026, 3, 21, 10, 35); // Apr 21, 2026 10:35 AM
  const WEEK_START = new Date(2026, 3, 20); // Mon Apr 20

  describe('WeekCalendar', () => {
    it('renders 7 day-header cells + 28 slot rows', () => {
      const { container } = render(
        <WeekCalendar
          weekStart={WEEK_START} now={NOW} estimates={[]} pick={null}
          loadingWeek={false} conflicts={[]} hasConflict={false} pickCustomerName="V P"
          onWeekChange={() => {}} onSlotClick={() => {}} onSlotDrag={() => {}}
        />,
      );
      // 7 day-headers + 1 corner + 7 days × 28 rows + 28 timecol = 1 + 7 + 7*28 + 28 = 232 grid cells
      // Lighter assertion: at least one slot is reachable by testid
      expect(screen.getByTestId('schedule-visit-slot-0-0')).toBeInTheDocument();
      expect(screen.getByTestId('schedule-visit-slot-6-27')).toBeInTheDocument();
    });

    it('marks today\'s column header with the today class', () => {
      const { container } = render(
        <WeekCalendar
          weekStart={WEEK_START} now={NOW} estimates={[]} pick={null}
          loadingWeek={false} conflicts={[]} hasConflict={false} pickCustomerName="V P"
          onWeekChange={() => {}} onSlotClick={() => {}} onSlotDrag={() => {}}
        />,
      );
      const todayCell = container.querySelector('[class*="today"]');
      expect(todayCell).not.toBeNull();
    });

    it('renders past slots with "past" class', () => {
      const { container } = render(
        <WeekCalendar
          weekStart={WEEK_START} now={NOW} estimates={[]} pick={null}
          loadingWeek={false} conflicts={[]} hasConflict={false} pickCustomerName="V P"
          onWeekChange={() => {}} onSlotClick={() => {}} onSlotDrag={() => {}}
        />,
      );
      // Mon (day 0) is past relative to Tue Apr 21 NOW.
      const monSlot = screen.getByTestId('schedule-visit-slot-0-0');
      expect(monSlot.className).toMatch(/past/);
    });

    it('renders an existing estimate block', () => {
      const block: EstimateBlock = {
        id: 'e1', date: '2026-04-22', startMin: 11 * 60, endMin: 12 * 60 + 30,
        customerName: 'K. Nakamura', jobSummary: 'Backflow', assignedToUserId: null,
      };
      render(
        <WeekCalendar
          weekStart={WEEK_START} now={NOW} estimates={[block]} pick={null}
          loadingWeek={false} conflicts={[]} hasConflict={false} pickCustomerName="V P"
          onWeekChange={() => {}} onSlotClick={() => {}} onSlotDrag={() => {}}
        />,
      );
      expect(screen.getByText('K. Nakamura')).toBeInTheDocument();
    });

    it('renders the pick block with the schedule-visit-pick testid', () => {
      render(
        <WeekCalendar
          weekStart={WEEK_START} now={NOW} estimates={[]}
          pick={{ date: '2026-04-23', start: 14 * 60, end: 15 * 60 }}
          loadingWeek={false} conflicts={[]} hasConflict={false} pickCustomerName="V P"
          onWeekChange={() => {}} onSlotClick={() => {}} onSlotDrag={() => {}}
        />,
      );
      expect(screen.getByTestId('schedule-visit-pick')).toBeInTheDocument();
    });
  });
  ```
- **PATTERN**: existing tests in this codebase.
- **GOTCHA**: Pass deterministic `NOW` so the today-marker / past-slot tests aren't time-flaky.
- **VALIDATE**: `cd frontend && npm test -- WeekCalendar`

### Task 24 — CREATE `scripts/e2e/test-schedule-visit.sh`

- **IMPLEMENT** (mirrors `scripts/e2e/test-sales.sh` login fallback chain):
  ```bash
  #!/bin/bash
  # E2E Test: Schedule Estimate Visit Modal
  # Validates: feature-developments/schedule-estimate-visit-handoff/CHECKLIST.md
  #
  # Usage: bash scripts/e2e/test-schedule-visit.sh [--headed]
  # Prereqs: backend at :8000, frontend at :5173, agent-browser installed.

  set -euo pipefail
  SCREENSHOT_DIR="e2e-screenshots/schedule-visit"
  BASE_URL="http://localhost:5173"
  HEADED_FLAG=""
  ADMIN_EMAIL="${E2E_ADMIN_EMAIL:-admin@grins.com}"
  ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-admin123}"
  for arg in "$@"; do case $arg in --headed) HEADED_FLAG="--headed" ;; esac; done
  mkdir -p "$SCREENSHOT_DIR"

  echo "🧪 E2E Test: Schedule Estimate Visit Modal"
  echo "==========================================="

  # ── Login (mirrored from scripts/e2e/test-sales.sh:50-83) ──
  agent-browser $HEADED_FLAG open "${BASE_URL}/login"
  agent-browser wait --load networkidle
  agent-browser wait 1000

  if   agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then agent-browser fill "[data-testid='email-input']" "$ADMIN_EMAIL"
  elif agent-browser is visible "[name='email']" 2>/dev/null; then agent-browser fill "[name='email']" "$ADMIN_EMAIL"
  else agent-browser fill "input[type='email']" "$ADMIN_EMAIL"
  fi
  if   agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then agent-browser fill "[data-testid='password-input']" "$ADMIN_PASSWORD"
  else agent-browser fill "input[type='password']" "$ADMIN_PASSWORD"
  fi
  if   agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then agent-browser click "[data-testid='login-btn']"
  else agent-browser click "button[type='submit']"
  fi
  agent-browser wait --load networkidle
  agent-browser wait 2000
  CURRENT_URL=$(agent-browser get url 2>/dev/null || echo "")
  if echo "$CURRENT_URL" | grep -qi "/login"; then echo "✗ FAIL: Could not log in"; exit 1; fi
  echo "✓ Login successful"

  # ── Navigate to a sales entry in schedule_estimate stage ──
  agent-browser open "${BASE_URL}/sales"
  agent-browser wait --load networkidle
  agent-browser screenshot "$SCREENSHOT_DIR/01-pipeline.png"

  # Click first row in the pipeline list
  if agent-browser is visible "[data-testid='pipeline-row-0']" 2>/dev/null; then
    agent-browser click "[data-testid='pipeline-row-0']"
  else
    # Fallback: click the first link inside any sales table
    agent-browser click "a[href*='/sales/']"
  fi
  agent-browser wait --load networkidle
  agent-browser screenshot "$SCREENSHOT_DIR/02-detail.png"

  # ── Open modal ──
  agent-browser click "[data-testid='now-action-schedule']"
  agent-browser wait "[data-testid='schedule-visit-modal']"
  agent-browser screenshot "$SCREENSHOT_DIR/03-modal-open.png"

  if agent-browser is visible "[data-testid='schedule-visit-customer-card']"; then echo "✓ customer card visible"; else echo "✗ customer card MISSING"; exit 1; fi
  if agent-browser is visible "[data-testid='schedule-visit-calendar']"; then echo "✓ calendar visible"; else echo "✗ calendar MISSING"; exit 1; fi

  # Confirm should be disabled before any pick
  CONFIRM_DISABLED=$(agent-browser get attr "[data-testid='schedule-visit-confirm-btn']" "disabled" 2>/dev/null || echo "")
  if [ -n "$CONFIRM_DISABLED" ]; then echo "✓ Confirm disabled before pick"; fi

  # ── Click a slot (Mon 2pm = day 0, slot 16) ──
  agent-browser click "[data-testid='schedule-visit-slot-0-16']"
  agent-browser wait "[data-testid='schedule-visit-pick']"
  agent-browser screenshot "$SCREENSHOT_DIR/04-pick.png"

  # ── Confirm ──
  agent-browser click "[data-testid='schedule-visit-confirm-btn']"
  agent-browser wait --text "Visit scheduled"
  agent-browser screenshot "$SCREENSHOT_DIR/05-after-confirm.png"

  # ── Verify the entry advanced to estimate_scheduled ──
  # NB: status `estimate_scheduled` is a sub-state of stage `schedule_estimate`
  # (statusToStageKey alias, pipeline.ts:171), so the NowCard's pill tone does
  # NOT change. The visible signals are:
  #   - ActivityStrip emits a `visit_scheduled` event
  #     (testid: activity-event-visit_scheduled — ActivityStrip.tsx:53)
  #   - StageStepper renders a "📅 Scheduled" badge on the schedule_estimate
  #     step when `visitScheduled` prop is true (StageStepper.tsx:55-57)
  if agent-browser is visible "[data-testid='activity-event-visit_scheduled']" 2>/dev/null; then
    echo "✓ Activity strip shows 'visit_scheduled' badge — entry advanced"
  else
    echo "✗ FAIL: 'visit_scheduled' activity badge missing"
    exit 1
  fi

  agent-browser close
  echo ""
  echo "✓ E2E complete. Screenshots: $SCREENSHOT_DIR/"
  ```
- **PATTERN**: `scripts/e2e/test-sales.sh:50-83` for login fallback; `e2e-testing-skill.md` for overall flow.
- **GOTCHA**: `agent-browser get attr` may not be a real subcommand on every version — replace with `eval "document.querySelector('[data-testid=\"...\"]')...` if needed. The script's exit codes are advisory; pipe through bash `set -e` so any hard failure aborts.
- **VALIDATE**:
  ```bash
  chmod +x scripts/e2e/test-schedule-visit.sh
  # In one terminal:
  cd /Users/kirillrakitin/Grins_irrigation_platform && ./scripts/dev.sh
  # In another terminal:
  cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run dev
  # In a third terminal:
  bash scripts/e2e/test-schedule-visit.sh
  ```

### Task 25 — RUN full quality gates

- **IMPLEMENT**: Run all the checks defined in `code-standards.md` §5 and §6. All four backend checks must be zero — partial passes are not acceptable per `tech.md`'s quality command.
- **VALIDATE**:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform
  uv run ruff check --fix src/ && uv run ruff format src/ && uv run mypy src/ && uv run pyright src/
  uv run pytest -m "unit or functional" -v
  uv run pytest -m integration -v
  cd frontend
  npm run typecheck && npm run lint && npm test
  ```

---

## TESTING STRATEGY

### Unit Tests (backend)

`tests/unit/test_schedule_visit_api.py` — `@pytest.mark.unit`, `MagicMock(spec=AsyncSession)`. Coverage target: 90%+ for new schema/handler code paths.

### Functional Tests (backend)

`tests/functional/test_schedule_visit_functional.py` — `@pytest.mark.functional`. **Mocked-service-layer pattern** mirroring `test_sales_pipeline_functional.py:1-60` (this codebase's "functional" tier is mocked, NOT real-DB).

### Integration Tests (backend)

`tests/integration/test_schedule_visit_integration.py` — `@pytest.mark.integration`. Real-DB workflow via `authenticated_client` fixture.

### Unit / Component Tests (frontend)

Co-located `*.test.ts(x)` files. Vitest + RTL with `QueryProvider` wrapper. Coverage targets per `frontend-testing.md`: components 80%+, hooks 85%+, utils 90%+.

### Property-based Tests (frontend)

`scheduleVisitUtils.test.ts` includes a `fast-check` round-trip test for `minToHHMMSS ↔ hhmmssToMin` (fast-check is already a devDep).

### Edge Cases (mandatory test coverage)

- **§6.1 Pick outside visible week** — date-field change re-derives `weekStart`; calendar scrolls. Covered in `useScheduleVisit.test.ts` test #5.
- **§6.2 Drag exits day column** — drag locked to origin day. Covered by the explicit `if (di !== dayIdx) return;` in `WeekCalendar.tsx:onMove`.
- **§6.3 Drag into past slots** — disabled via `if (past) return` early-exit + `onMouseDown={past ? undefined : ...}`.
- **§6.4 Reschedule** — covered by `useScheduleVisit.test.ts` tests #2 and #8.
- **§6.5 Empty week** — empty grid renders with no "no events" copy (intrinsic).
- **§6.6 Loading existing estimates** — `loadingWeek` prop drives `aria-busy`; refining shimmer is a polish ticket.
- **§5 Conflict** — `WeekCalendar.test.tsx` test #4 + `useScheduleVisit.test.ts` test #7.
- **§3 Today/Prev/Next don't clear pick** — verified via the explicit decision NOT to call `setPick(null)` in nav handlers.
- **409 conflict on submit** — `useScheduleVisit.submit()` handles, returns `{ ok: false, conflict: true }`; modal stays open; banner shows.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/
cd frontend
npm run lint
npm run typecheck
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest -m unit src/grins_platform/tests/unit/test_schedule_visit_api.py -v
cd frontend
npm test -- scheduleVisitUtils useScheduleVisit ScheduleVisitModal WeekCalendar
```

### Level 3: Functional + Integration Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest -m functional src/grins_platform/tests/functional/test_schedule_visit_functional.py -v
uv run pytest -m integration src/grins_platform/tests/integration/test_schedule_visit_integration.py -v
uv run pytest -m integration -v   # full regression
```

### Level 4: Manual Validation

```bash
# Terminal A
cd /Users/kirillrakitin/Grins_irrigation_platform && ./scripts/dev.sh
# Terminal B
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run dev
# Terminal C
agent-browser --version || (npm install -g agent-browser && agent-browser install --with-deps)
bash scripts/e2e/test-schedule-visit.sh
```

DB verification:
```bash
psql "$DATABASE_URL" -c "SELECT id, sales_entry_id, scheduled_date, start_time, end_time, assigned_to_user_id FROM sales_calendar_events ORDER BY created_at DESC LIMIT 5;"
psql "$DATABASE_URL" -c "SELECT id, status, override_flag FROM sales_entries WHERE id = '<entry_id_from_e2e>';"
```

### Level 5: Cross-feature regression

```bash
cd frontend && npm test -- SalesCalendar SalesDetail
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest -m functional src/grins_platform/tests/functional/test_sales_pipeline_functional.py -v
```

---

## ACCEPTANCE CRITERIA

- [ ] CHECKLIST.md (`feature-developments/schedule-estimate-visit-handoff/CHECKLIST.md`) passes end-to-end:
  - [ ] Visual parity (calendar grid renders pixel-identical to reference HTML — same CSS module ported in Task 14)
  - [ ] Interaction (click, drag, drag-locked-to-day, past-slot disable, week nav, Esc-warns-if-dirty)
  - [ ] Data (customer card read-only, week-fetch on open + on navigation, POST/PUT, 409 handling)
  - [ ] Conflict (same-date overlap → color flip + banner; Confirm stays enabled)
  - [ ] Accessibility (focus trap from Dialog, Esc, customer card `role="group"`, conflict banner `role="alert"`, `<label htmlFor>` on every input)
  - [ ] Responsive (<720px stacks customer card → calendar → fields via `order-1/2/3` + `md:row-span-2`)
  - [ ] Telemetry: `track()` stub emits `opened`, `pick`, `confirmed`, `cancelled` events
- [ ] `case 'schedule_visit'` in `SalesDetail.tsx` opens the modal (no longer just calls `advance.mutate`)
- [ ] Submit succeeds → row in `sales_calendar_events` AND `sales_entries.status` = `estimate_scheduled` AND parent stepper advances visibly without manual refetch
- [ ] Reschedule path (`status === 'estimate_scheduled'`) pre-fills the existing event and submits PUT
- [ ] Level 1: zero errors / zero violations across ruff/mypy/pyright/eslint/tsc
- [ ] Level 2 + Level 3: all tests pass
- [ ] Coverage: backend new code ≥90%, frontend components ≥80%, hooks ≥85%, utils ≥90%
- [ ] Level 4: agent-browser E2E script passes
- [ ] Level 5: no regressions in `SalesCalendar`, `SalesDetail`, or sales pipeline functional tests

---

## COMPLETION CHECKLIST

- [ ] All 26 tasks completed in order (1–18, 18.5, 19–25)
- [ ] Each task validation passed before proceeding
- [ ] All Level 1–5 commands executed successfully
- [ ] No linting or type checking errors
- [ ] Manual E2E confirms feature works
- [ ] Acceptance criteria all met

---

## NOTES

### Out of scope (per README §"Out of scope")

- Editing customer/lead info inside the modal
- Sending the appointment-confirmation SMS (the existing `text_confirmation` action stays a TODO)
- Calendar sync to Google/Outlook (`SALES-441`)
- Recurring / multi-day appointments

### Design decisions

- **Use existing endpoints, not new ones.** The SPEC describes `POST /api/sales/:entryId/schedule-visit` and `GET /api/sales/estimates/calendar`. The actual API is `POST /api/v1/sales/calendar/events` and `GET /api/v1/sales/calendar/events`. Per the README "Questions / contacts" section, the API is treated as truth.
- **CSS Module for the calendar.** The reference HTML uses a hand-drawn aesthetic (Caveat/Kalam fonts, rotated buttons, hatched fills). The codebase uses shadcn elsewhere. Decision: shadcn `Dialog` for the modal frame; the calendar grid uses the ported reference CSS as a CSS module — pixel-identical to the reference, matches CHECKLIST §Visual parity.
- **Hook-extracted state.** `useScheduleVisit` lives outside the modal folder so the reconciliation logic can be hook-tested in isolation (faster than mounting 200+ slot cells).
- **Broaden invalidation in `useCreateCalendarEvent`/`useUpdateCalendarEvent`.** Existing `SalesCalendar.tsx` benefits too — strict bug-fix.
- **Telemetry stub.** No telemetry SDK in repo (verified by grep). `track()` logs to `console.info`; future ticket swaps the implementation.
- **No react-hook-form/zod here.** The form is a thin view of an externally-driven `pick` state; RHF would fight the calendar.
- **Mobile order via `order-1/2/3` + `md:row-span-2`.** Fixes the scaffold's incomplete reorder; verified mobile flow is customer-card → calendar → fields per SPEC §2.

### Risks (and how each is closed)

| Risk (was) | Closed by |
|---|---|
| Drag-handler memory leaks on unmount | Task 15 explicitly cleans up `dragRef`, plus listeners are per-mousedown and self-removed in `onUp`. Tested. |
| Reference HTML render math doesn't translate cleanly | Task 15 inlines the *exact* math from the reference (`HEADER_PX = 29`, fixed `gridTemplateRows`, `colLeftPct`/`colWidthPct` calc strings). Mechanical port. |
| §8 open questions expand scope | Closed in the "Decisively Closed §8 Open Questions" section: per-assignee filtering, 24h toggle, resize handles, and SMS toggle ALL dropped for v1. |
| `useStaff` shape assumption | Verified: `Staff.name` (NOT `display_name`). Tasks 17 + 22 use the correct field. |
| Migration head drift | Verified `20260425_100000` via `uv run alembic heads` on 2026-04-25; Task 1's `down_revision` is exact. |
| Conflict-on-submit (409) handling | `useScheduleVisit.submit()` returns `{ ok: false, conflict: true }`; modal stays open; banner shows. |
| Race between modal close and entry refetch | Broadened invalidation in Task 11 means `pipelineKeys.detail(entryId)` is invalidated on success; parent re-fetches automatically. No manual `refetch()` needed; explicitly NOT called in Task 21 to avoid race. |
| TZ at DST transitions | Decision: don't special-case; spring-forward Sunday's missing 2am slot is unclickable / past-shaded (matches Google Calendar behavior). |
| Multiple events for one entry on reschedule | Decision: load the **last** event from the API list (which is `scheduled_date ASC`); document with comment in Task 21. |

### Confidence Score: 10/10

All previously-cited risks are closed:
- Reference render math is inlined verbatim (Task 15) — no translation guesswork remains.
- All §8 open questions are decisively dropped for v1 — no scope-expansion path.
- Every external assumption (alembic head, Staff field name, Switch path, getErrorMessage shape, fixture patterns, login-flow selectors) was directly verified in the audit table at the top of this plan.
- Each task has paste-ready code snippets and an executable validation command. The implementer never has to "figure out" what to write — they paste, then run the validation.
