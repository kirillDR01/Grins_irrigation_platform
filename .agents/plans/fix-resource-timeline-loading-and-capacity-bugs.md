# Feature: Fix Resource Timeline `Loading…` + 0% Capacity Bugs

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

The new `ResourceTimelineView` (Phases 1–4 landed in `3a6fceb…94630a2`) ships
two visible regressions on dev:

1. **Per-day capacity bar permanently renders 0%** — the orange/teal threshold
   logic in `<CapacityFooter>` never paints because `capacity.days[i].utilization_pct`
   is always `undefined` on the wire.
2. **Per-tech utilization line is permanently `Loading…`** — `utilizationByTech`
   ends up empty because `GET /schedule/utilization` always returns
   `resources: []`.

Both are FE/BE contract bugs at the same seam: the FE hooks are typed against
schemas (`CapacityForecastExtended`, `UtilizationReport.resources[]`) that the
BE endpoints don't actually populate. A third compounding factor — zero
`staff_availability` rows on dev — keeps the symptoms visible even after the
contract is fixed, so we patch BE-logic + dev-data + a defensive FE fallback in
one PR.

This plan implements all three legs of the fix described in
`bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md`.

## User Story

As a **scheduling-team admin** opening the Resource Timeline view on dev or
prod
I want to **see real per-day capacity utilization and per-tech utilization
percentages**
So that **I can spot over-booked techs and full-capacity days at a glance, and
trust the UI is accurately reporting the data state instead of hanging on a
silent "Loading…" forever.**

## Problem Statement

`ResourceTimelineView/WeekMode.tsx` consumes two query results that look
correct on the type level but are empty on the wire:

- `useWeeklyCapacity` types its result as `CapacityForecastExtended` (which
  has `utilization_pct?: number`), but `GET /schedule/capacity/{date}` actually
  returns `ScheduleCapacityResponse` (no `utilization_pct` field). Result:
  `?? 0` → 0% bar everywhere.
- `useWeeklyUtilization` calls `GET /schedule/utilization`, which iterates
  `getattr(capacity, "staff_capacities", [])` — but
  `ScheduleCapacityResponse` has no `staff_capacities` attribute. Result: HTTP
  200 with `resources: []` → no per-tech utilization → `null` → permanent
  `Loading…`.

`ScheduleGenerationService._load_available_staff` only returns staff that have
a `staff_availability` row for the date, and dev's `staff_availability` table
is empty (verified live: `count(*) = 0`). So even after the contract is
fixed, the values would be 0 / empty until availability rows exist.

## Solution Statement

A single PR with three coordinated fixes:

1. **BE — Bug A (capacity)**: extend `ScheduleCapacityResponse` with a
   computed `utilization_pct: float` field
   (`scheduled_minutes / total_capacity_minutes * 100`, `0.0` when
   denominator is 0). FE already reads this exact field name.
2. **BE — Bug B (utilization)**: rewrite `get_utilization_report` to compute
   per-staff `ResourceUtilization` entries directly from `staff_availability`
   + `appointments` instead of the non-existent
   `capacity.staff_capacities`. Falls back to a synthetic 480-min shift when
   no availability row exists, so dev is never stranded on an empty list.
3. **Dev data + FE defense**: extend the existing
   `scripts/seed_resource_timeline_test_data.py` to backfill
   `staff_availability` for the four active techs across the QA week
   (Mon–Fri 8:00–17:00, off Sat/Sun). FE follow-up: in `WeekMode.tsx`
   distinguish "queries settled but resources empty" from "still loading" so
   `<TechHeader>` renders `"—"` instead of `"Loading…"` when the BE
   genuinely returns empty.

## Feature Metadata

**Feature Type**: Bug Fix
**Estimated Complexity**: Medium
**Primary Systems Affected**: backend `schedule` API + `ScheduleGenerationService`,
frontend `ResourceTimelineView` (`WeekMode`, `TechHeader`), dev seed script
**Dependencies**: none (all changes use existing models, schemas, and
TanStack Query plumbing)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING!

**Backend — capacity / utilization endpoints**

- `src/grins_platform/api/v1/schedule.py:201-244` — `GET /capacity/{schedule_date}`
  endpoint. Returns `ScheduleCapacityResponse` plus 30-criteria overlay.
  **Why**: Bug A surface; the route's `response_model` is the schema we
  extend.
- `src/grins_platform/api/v1/schedule.py:892-954` — `GET /utilization`
  endpoint. Reads `capacity.staff_capacities` (which doesn't exist).
  **Why**: Bug B body; this is the loop we rewrite.
- `src/grins_platform/services/schedule_generation_service.py:139-175` —
  `get_capacity()`. Aggregates `total_capacity` and `scheduled_minutes`.
  **Why**: We mirror its `staff_with_availability` loop in the new
  `get_resource_utilization()` method.
- `src/grins_platform/services/schedule_generation_service.py:189-214` —
  `_load_available_staff()`. Returns `[(Staff, StaffAvailability)]`, only for
  staff that have a row. **Why**: Reuse for the new method; note the
  current behavior filters out staff with no availability row entirely.
- `src/grins_platform/services/schedule_generation_service.py:216-233` —
  `_get_scheduled_minutes()`. **Why**: Per-staff variant we'll add must
  group by `staff_id`.

**Backend — schemas**

- `src/grins_platform/schemas/schedule_generation.py:77-122` —
  `ScheduleCapacityResponse`. **Why**: Add `utilization_pct: float` field
  here (Bug A fix). Existing fields:
  `schedule_date, total_staff, available_staff, total_capacity_minutes,
  scheduled_minutes, remaining_capacity_minutes, can_accept_more`, plus
  optional overlay `criteria_*` / `forecast_*` / `per_criterion_utilization`.
- `src/grins_platform/schemas/ai_scheduling.py:658-700` —
  `ResourceUtilization` and `UtilizationReport`. **Why**: target schema
  shape for Bug B. Fields: `staff_id, name, total_minutes,
  assigned_minutes, drive_minutes, utilization_pct`.
- `src/grins_platform/schemas/ai_scheduling.py:703-732` — `CapacityForecast`
  (UNRELATED). **Why**: Reference only — this is the schema the FE *thinks*
  it gets but doesn't. Do **not** touch.

**Backend — models**

- `src/grins_platform/models/staff_availability.py` — `StaffAvailability`
  model. Fields: `staff_id, date, start_time, end_time, is_available,
  lunch_start, lunch_duration_minutes`. **Why**: dev seed inserts; backend
  fallback computation.
- `src/grins_platform/models/appointment.py` — `Appointment`. Fields used:
  `staff_id, scheduled_date, time_window_start, time_window_end`. **Why**:
  per-staff scheduled_minutes calculation.

**Backend — tests**

- `src/grins_platform/tests/integration/test_ai_scheduling_integration.py:403-450`
  — existing public-endpoint smoke tests for `/capacity/{date}` and
  `/utilization`. **Why**: pattern for ASGI-transport tests.
- `src/grins_platform/tests/integration/test_ai_scheduling_integration.py:943-1080`
  — `test_capacity_response_includes_overlay_fields_when_assignments_exist`.
  **Why**: pattern for `_make_session()` + dependency override + asserting
  on response body fields.
- `src/grins_platform/tests/integration/test_ai_scheduling_integration.py:1-55`
  — `_make_staff`, `_make_session` helpers. **Why**: reuse, do not redefine.

**Frontend — hooks (FE/BE seam)**

- `frontend/src/features/schedule/hooks/useWeeklyCapacity.ts:23-46` —
  `useWeeklyCapacity`. Returns `CapacityForecastExtended[]`. **Why**: types
  match Bug A surface. After BE fix this will continue to work because
  `CapacityForecastExtended.utilization_pct` is already `number | undefined`
  and the new BE field uses the same name.
- `frontend/src/features/schedule/hooks/useWeeklyUtilization.ts:22-46` —
  `useWeeklyUtilization`. Returns `UtilizationReport[]`. **Why**: types match
  Bug B surface. After BE fix `resources` is populated and this works as-is.
- `frontend/src/features/schedule/hooks/useAIScheduling.ts:29-91` — type
  definitions for `CapacityForecastExtended`, `UtilizationReport`,
  `aiSchedulingKeys`. **Why**: these stay unchanged; the BE schema now
  matches them.

**Frontend — components**

- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx:126-156`
  — `utilizationByTech` and `capacityByDate` memos. **Why**: Add the
  "queries settled but empty" guard so `<TechHeader>` doesn't get
  permanently stuck on `null`.
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx:279-285`
  — where `<TechHeader>` is rendered with
  `utilizationByTech[staff.id] ?? null`. **Why**: This is where the `null`
  vs `undefined` distinction matters.
- `frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx:40-44`
  — the `null → 'Loading…'` ternary. **Why**: defense-in-depth update so
  `'—'` shows when query settled with no data.
- `frontend/src/features/schedule/components/ResourceTimelineView/CapacityFooter.tsx:15-46`
  — already correctly distinguishes `null` (loading skeleton) from numeric
  pct. **Why**: reference; no change needed here.

**Frontend — tests**

- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx:80-180`
  — fixture builders + `mockUseWeeklyCapacity` / `mockUseWeeklyUtilization`
  patterns. **Why**: pattern for new tests.

**Dev seed**

- `scripts/seed_resource_timeline_test_data.py:53-99` — week constants
  (`MON…SAT` for week of 2026-05-04) and tech-id lookup
  (Viktor/Vasiliy/Gennadiy/Steve). **Why**: extend with availability seed.
- `scripts/seed_resource_timeline_test_data.py:111-146` — wipe-prior-rows
  block. **Why**: add availability wipe to keep re-runs clean.

### New Files to Create

- `src/grins_platform/tests/integration/test_resource_timeline_contract.py` —
  integration tests asserting `/capacity/{date}` returns numeric
  `utilization_pct`, and `/utilization` returns one `ResourceUtilization`
  per active staff (with a synthetic-shift fallback when
  `staff_availability` is empty).
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx`
  — *augment*, do not replace. New cases: "renders `—` when utilization
  query settles with empty resources" and "renders 0% capacity bar when
  `utilization_pct` is 0 (not skeleton)".

No new components, services, or models needed — all fixes are in-place edits.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Pydantic v2 — computed_field decorator](https://docs.pydantic.dev/latest/concepts/fields/#the-computed_field-decorator)
  - **Why**: `utilization_pct` on `ScheduleCapacityResponse` can be a
    `@computed_field` derived from `scheduled_minutes` /
    `total_capacity_minutes`, avoiding any caller-side bookkeeping. (You can
    also do it as a plain `Field()` populated by the service — both are
    fine; pick the one that mirrors the project's existing pattern. Search
    for `@computed_field` first; if absent, use a plain `float = 0.0`.)
- [Pydantic v2 — Field defaults](https://docs.pydantic.dev/latest/concepts/fields/#default-values)
  - **Why**: keeping the new field non-Optional with a sensible default
    (`0.0`) preserves backward compatibility for any test fixtures
    constructing `ScheduleCapacityResponse` directly.
- [TanStack Query v5 — Query state types](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys)
  - **Why**: confirms the `isLoading` + `data: undefined` vs `data: <empty
    list>` distinction the FE fix relies on.
- [SQLAlchemy 2.0 — `.query(...).filter(...).all()` legacy API in async
  context](https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html)
  - **Why**: `ScheduleGenerationService` uses the legacy `Session.query()`
    API (synchronous). Stick with it for the new
    `get_resource_utilization` method — do NOT introduce
    `select(...).execute(...)` / async patterns mid-service.

### Patterns to Follow

**LoggerMixin domain logging** (mandatory per `code-standards.md`):

```python
# Existing in ScheduleGenerationService — reuse the DOMAIN.
class ScheduleGenerationService(LoggerMixin):
    DOMAIN = "business"

    def get_resource_utilization(self, schedule_date: date) -> UtilizationReport:
        self.log_started("get_resource_utilization", schedule_date=str(schedule_date))
        try:
            ...
            self.log_completed(
                "get_resource_utilization",
                schedule_date=str(schedule_date),
                resource_count=len(resources),
            )
            return report
        except Exception as e:
            self.log_failed("get_resource_utilization", error=e)
            raise
```

**API endpoint pattern** (from `api-patterns.md` and existing
`schedule.py:201-244,897-954`):

```python
@router.get("/utilization", response_model=UtilizationReport, summary="...")
def get_utilization_report(
    schedule_date: date = Query(..., description="..."),
    service: ScheduleGenerationService = Depends(get_schedule_service),
) -> UtilizationReport:
    endpoints.log_started("get_utilization", schedule_date=str(schedule_date))
    try:
        report = service.get_resource_utilization(schedule_date)
    except Exception as exc:
        endpoints.log_failed("get_utilization", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Utilization report failed: {exc!s}",
        ) from exc
    else:
        endpoints.log_completed(
            "get_utilization",
            schedule_date=str(schedule_date),
            resource_count=len(report.resources),
        )
        return report
```

(Do NOT call `service.get_capacity` followed by reading
`staff_capacities` — that's the bug. The new service method owns the
per-staff math.)

**Per-staff scheduled-minutes aggregation** (mirror
`_get_scheduled_minutes` but group by staff_id):

```python
def _get_scheduled_minutes_per_staff(self, schedule_date: date) -> dict[UUID, int]:
    appointments = (
        self.db.query(Appointment)
        .filter(Appointment.scheduled_date == schedule_date)
        .all()
    )
    out: dict[UUID, int] = {}
    for apt in appointments:
        if not (apt.staff_id and apt.time_window_start and apt.time_window_end):
            continue
        start_mins = apt.time_window_start.hour * 60 + apt.time_window_start.minute
        end_mins = apt.time_window_end.hour * 60 + apt.time_window_end.minute
        out[apt.staff_id] = out.get(apt.staff_id, 0) + (end_mins - start_mins)
    return out
```

**Synthetic 8h-shift fallback** (when no `StaffAvailability` row exists
for a staff on a date — used by *both* the new utilization method and the
existing `get_capacity` totals; see Task 3):

```python
DEFAULT_SHIFT_MINUTES = 8 * 60  # 8:00–17:00 with 1h lunch == 480 min
```

**Frontend `null` vs `0` discipline** (`WeekMode.tsx:145-156` already
gets it right for capacity — mirror for utilization):

```tsx
// Distinguish "still loading" (null) from "settled but empty" (0 or undefined).
const utilizationByTech = useMemo(() => {
  const out: Record<string, number | null> = {};
  if (utilization.isLoading) return out; // empty map → all techs render Loading…
  // After settle: every staff.id maps to a number (defaults to 0 when
  // the BE returned no rows for them).
  ...
}, [utilization.days, utilization.isLoading]);

// At render site (line 279):
const utilPct = utilizationByTech[staff.id];
const value = utilization.isLoading ? null : (utilPct ?? 0);
return <TechHeader staff={staff} utilizationPct={value} />;
```

**Naming Conventions** (already enforced by Ruff/MyPy/Pyright):

- Python: `snake_case` everywhere; new method `get_resource_utilization`
  matches `get_capacity`/`generate_schedule` siblings.
- TS: `camelCase` for vars; component file already-`PascalCase`.

---

## IMPLEMENTATION PLAN

### Phase 1: Backend Schema + Service

Extend `ScheduleCapacityResponse` with `utilization_pct` and add a new
`get_resource_utilization` method to `ScheduleGenerationService` that
computes per-staff utilization without depending on the missing
`staff_capacities` attribute. Add a synthetic-shift fallback so dev (and
any environment with empty `staff_availability`) returns non-empty data.

**Tasks:**

- Add `utilization_pct: float = 0.0` to `ScheduleCapacityResponse` and
  populate it inside `ScheduleGenerationService.get_capacity()`.
- Add `_get_scheduled_minutes_per_staff` helper.
- Add `_load_all_active_staff_with_optional_availability` helper that
  returns `[(Staff, StaffAvailability | None)]` for *every* active +
  available staff member (so missing availability rows don't drop the
  staff from utilization output).
- Add `get_resource_utilization(date) -> UtilizationReport` that builds
  one `ResourceUtilization` per staff, using a 480-minute fallback when
  the availability row is missing.

### Phase 2: Backend Endpoint Rewrite

Rewrite `get_utilization_report` to delegate to the new service method.
Drop the `getattr(capacity, "staff_capacities", [])` dead code.

**Tasks:**

- Replace the body of the route with a call to
  `service.get_resource_utilization(schedule_date)`.
- Keep request/response models, status codes, and logging keys identical.

### Phase 3: Dev Data Backfill

Extend the existing seed script to insert `staff_availability` for the
four active techs across Mon–Fri of the QA week. Sat/Sun deliberately
omitted to keep the empty-Sun column meaningful.

**Tasks:**

- Add availability-insert helper inside
  `scripts/seed_resource_timeline_test_data.py`.
- Insert rows for Viktor, Vasiliy, Gennadiy, Steve for
  `2026-05-04 → 2026-05-08` (Mon–Fri, 08:00–17:00, 60-min lunch start
  12:00). Wipe prior `[TIMELINE-TEST]`-equivalent rows first to keep
  re-runs idempotent.

### Phase 4: Frontend Defensive Render

Update `WeekMode.tsx` so the `utilizationByTech` lookup distinguishes
"loading" from "settled-with-empty-data". Update `TechHeader` to render
`"—"` instead of `"Loading…"` when utilization is settled but absent.

**Tasks:**

- Tighten `utilizationByTech[staff.id] ?? null` to use `isLoading` as the
  loading source-of-truth.
- Update `TechHeader` (or the WeekMode render site) so a number-or-null
  distinction is preserved.
- Mirror in `DayMode.tsx` if the same idiom appears there.

### Phase 5: Testing & Validation

Add integration coverage that proves both endpoints return correctly
shaped, populated bodies even when `staff_availability` is empty (the
synthetic-shift fallback path). Add FE tests for the empty-data
defensive render.

**Tasks:**

- `test_capacity_response_includes_utilization_pct` (integration).
- `test_utilization_report_returns_one_resource_per_active_staff_with_no_availability_rows`
  (integration; exercises the fallback).
- `test_utilization_report_uses_real_availability_when_present` (integration).
- WeekMode test: "renders `—` when utilization query settled empty".
- Run full validation suite (Levels 1–4).

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic
and independently testable.

### Task 1: UPDATE `src/grins_platform/schemas/schedule_generation.py`

- **IMPLEMENT**: Add `utilization_pct: float = Field(default=0.0,
  description="(scheduled_minutes / total_capacity_minutes) * 100, or 0.0
  when total_capacity_minutes == 0")` to `ScheduleCapacityResponse`,
  positioned immediately after `can_accept_more` and before
  `criteria_triggered` so it's a non-Optional non-overlay field.
- **PATTERN**: Match existing field style at
  `schemas/schedule_generation.py:88-94`. Keep type annotation + `Field`
  with description.
- **IMPORTS**: none new — `Field` already imported.
- **GOTCHA**: Default to `0.0`, not `None`. The FE reads `?? 0`, so a
  `None` would silently keep the bug. Also keep it non-Optional (no
  `| None`) so existing test fixtures that omit it continue to construct
  validly.
- **VALIDATE**: `uv run pyright src/grins_platform/schemas/schedule_generation.py && uv run python -c "from grins_platform.schemas.schedule_generation import ScheduleCapacityResponse; r = ScheduleCapacityResponse(schedule_date=__import__('datetime').date.today(), total_staff=0, available_staff=0, total_capacity_minutes=0, scheduled_minutes=0, remaining_capacity_minutes=0, can_accept_more=False); print(r.utilization_pct)"`

### Task 2: UPDATE `src/grins_platform/services/schedule_generation_service.py` — populate `utilization_pct` in `get_capacity`

- **IMPLEMENT**: Inside `get_capacity()` (line 139), compute
  `utilization_pct` from `scheduled_minutes` and `total_capacity` and pass
  it into the `ScheduleCapacityResponse(...)` constructor:
  ```python
  utilization_pct = (
      (scheduled_minutes / total_capacity) * 100
      if total_capacity > 0 else 0.0
  )
  return ScheduleCapacityResponse(
      ...existing kwargs...,
      utilization_pct=round(utilization_pct, 1),
  )
  ```
- **PATTERN**: Compute inline before the return; mirror the `round(…, 1)`
  precision used for `utilization_pct` in `get_utilization_report` at
  `api/v1/schedule.py:934`.
- **IMPORTS**: none new.
- **GOTCHA**: `total_capacity` is `int` and `scheduled_minutes` is `int`
  in the existing code — guard against `ZeroDivisionError` explicitly.
  Don't reach for `Decimal`; FE rounds anyway.
- **VALIDATE**: `uv run mypy src/grins_platform/services/schedule_generation_service.py`

### Task 3: ADD per-staff helpers to `ScheduleGenerationService`

- **IMPLEMENT**: Two new private methods inside
  `ScheduleGenerationService`:

  ```python
  DEFAULT_SHIFT_MINUTES = 480  # 8 hours; mirrors a default 08:00–17:00 with 1h lunch.

  def _load_active_staff_with_optional_availability(
      self,
      schedule_date: date,
  ) -> list[tuple[Staff, StaffAvailability | None]]:
      """Like `_load_available_staff` but does NOT drop staff with no row."""
      staff_list = (
          self.db.query(Staff)
          .filter(Staff.is_active == True, Staff.is_available == True)  # noqa: E712
          .all()
      )
      out: list[tuple[Staff, StaffAvailability | None]] = []
      for staff in staff_list:
          availability = (
              self.db.query(StaffAvailability)
              .filter(
                  StaffAvailability.staff_id == staff.id,
                  StaffAvailability.date == schedule_date,
                  StaffAvailability.is_available == True,  # noqa: E712
              )
              .first()
          )
          out.append((staff, availability))
      return out

  def _get_scheduled_minutes_per_staff(
      self,
      schedule_date: date,
  ) -> dict[UUID, int]:
      """Sum appointment minutes grouped by staff_id."""
      appointments = (
          self.db.query(Appointment)
          .filter(Appointment.scheduled_date == schedule_date)
          .all()
      )
      out: dict[UUID, int] = {}
      for apt in appointments:
          if not (apt.staff_id and apt.time_window_start and apt.time_window_end):
              continue
          start_mins = (
              apt.time_window_start.hour * 60 + apt.time_window_start.minute
          )
          end_mins = apt.time_window_end.hour * 60 + apt.time_window_end.minute
          out[apt.staff_id] = out.get(apt.staff_id, 0) + (end_mins - start_mins)
      return out
  ```

- **PATTERN**: Mirror existing `_load_available_staff` (lines 189-214) and
  `_get_scheduled_minutes` (lines 216-233). Stay on the synchronous
  `self.db.query(...).filter(...).all()` API — do not switch to async.
- **IMPORTS**: `from uuid import UUID` is already imported (line 13).
  `Appointment` and `StaffAvailability` are already imported.
- **GOTCHA**: `_load_available_staff` returns ONLY staff with rows.
  Renaming/refactoring it would break `generate_schedule`. Add a *new*
  helper instead — same query shape, but appends `(staff, None)` when no
  row exists.
- **VALIDATE**: `uv run mypy src/grins_platform/services/schedule_generation_service.py`

### Task 4: ADD `get_resource_utilization` method to `ScheduleGenerationService`

- **IMPLEMENT**: Public method that returns `UtilizationReport`:

  ```python
  def get_resource_utilization(self, schedule_date: date) -> UtilizationReport:
      """Per-staff utilization for the schedule date.

      Falls back to a synthetic 480-min shift when no `staff_availability`
      row exists, so dev (where the table is empty) never produces an
      empty resources list.
      """
      self.log_started(
          "get_resource_utilization",
          schedule_date=str(schedule_date),
      )
      try:
          staff_with_avail = (
              self._load_active_staff_with_optional_availability(schedule_date)
          )
          assigned_by_staff = self._get_scheduled_minutes_per_staff(schedule_date)

          resources: list[ResourceUtilization] = []
          for staff, availability in staff_with_avail:
              if availability:
                  start_mins = (
                      availability.start_time.hour * 60
                      + availability.start_time.minute
                  )
                  end_mins = (
                      availability.end_time.hour * 60
                      + availability.end_time.minute
                  )
                  total_mins = end_mins - start_mins
                  if availability.lunch_duration_minutes:
                      total_mins -= availability.lunch_duration_minutes
              else:
                  total_mins = self.DEFAULT_SHIFT_MINUTES

              assigned = assigned_by_staff.get(staff.id, 0)
              # No drive-time signal here yet — leave 0 until route
              # optimization persists per-appointment drive minutes.
              drive = 0
              util_pct = (
                  (assigned + drive) / total_mins * 100
                  if total_mins > 0 else 0.0
              )
              resources.append(
                  ResourceUtilization(
                      staff_id=staff.id,
                      name=staff.name,
                      total_minutes=total_mins,
                      assigned_minutes=assigned,
                      drive_minutes=drive,
                      utilization_pct=round(util_pct, 1),
                  )
              )
          report = UtilizationReport(
              schedule_date=schedule_date,
              resources=resources,
          )
      except Exception as exc:
          self.log_failed("get_resource_utilization", error=exc)
          raise
      else:
          self.log_completed(
              "get_resource_utilization",
              schedule_date=str(schedule_date),
              resource_count=len(resources),
          )
          return report
  ```

- **PATTERN**: Mirror `get_capacity` (line 139) for the loop shape and
  `LoggerMixin` lifecycle from `code-standards.md` §1.
- **IMPORTS**: Add to top of file:
  ```python
  from grins_platform.schemas.ai_scheduling import (
      ResourceUtilization,
      UtilizationReport,
  )
  ```
- **GOTCHA**: `Staff.name` is the canonical display name in this codebase
  (used by the seed script at line 81). Don't try `staff.full_name` or
  similar.
- **VALIDATE**: `uv run pyright src/grins_platform/services/schedule_generation_service.py && uv run mypy src/grins_platform/services/schedule_generation_service.py`

### Task 5: REFACTOR `get_utilization_report` route to use the new service method

- **IMPLEMENT**: Replace the body of `get_utilization_report` (lines
  902-954) with a thin call to `service.get_resource_utilization`:

  ```python
  @router.get(
      "/utilization",
      response_model=UtilizationReport,
      summary="Resource utilization report for a schedule date",
  )
  def get_utilization_report(
      schedule_date: date = Query(..., description="Date to report utilization for"),
      service: ScheduleGenerationService = Depends(get_schedule_service),
  ) -> UtilizationReport:
      """Return per-resource utilization metrics for a schedule date.

      GET /api/v1/schedule/utilization

      Validates: Requirements 6.1, 9.4, 10.4, 23.5
      """
      endpoints.log_started("get_utilization", schedule_date=str(schedule_date))
      try:
          report = service.get_resource_utilization(schedule_date)
      except Exception as exc:
          endpoints.log_failed("get_utilization", error=exc)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=f"Utilization report failed: {exc!s}",
          ) from exc
      else:
          endpoints.log_completed(
              "get_utilization",
              schedule_date=str(schedule_date),
              resource_count=len(report.resources),
          )
          return report
  ```

- **PATTERN**: Identical to existing route shape (`api/v1/schedule.py:201-244`).
- **IMPORTS**: `ResourceUtilization` is no longer constructed in the
  route; remove from the imports block at the top of `schedule.py` only
  if it's not referenced elsewhere in the file (grep first; it likely is).
- **GOTCHA**: Keep the `schedule_date=` query param shape and the same
  `summary=` so the OpenAPI spec is byte-identical from the FE
  perspective. Keep log keys (`"get_utilization"`, `resource_count`).
- **VALIDATE**: `uv run ruff check --fix src/grins_platform/api/v1/schedule.py && uv run mypy src/grins_platform/api/v1/schedule.py`

### Task 6: ADD integration tests for the contract fixes

- **IMPLEMENT**: Create
  `src/grins_platform/tests/integration/test_resource_timeline_contract.py`
  with three tests:

  ```python
  """Bug fix: resource-timeline /capacity & /utilization contract.

  Validates: bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md
  """
  from __future__ import annotations
  import uuid
  from datetime import date, time
  from unittest.mock import MagicMock, patch
  import pytest
  from httpx import ASGITransport, AsyncClient

  from grins_platform.main import app


  def _staff(name: str = "Tech A") -> MagicMock:
      m = MagicMock()
      m.id = uuid.uuid4()
      m.name = name
      m.is_active = True
      m.is_available = True
      return m


  def _availability(staff_id, *, start=time(8, 0), end=time(17, 0), lunch=60):
      m = MagicMock()
      m.staff_id = staff_id
      m.date = date(2026, 5, 4)
      m.start_time = start
      m.end_time = end
      m.lunch_duration_minutes = lunch
      m.is_available = True
      return m


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_capacity_response_includes_numeric_utilization_pct() -> None:
      """`utilization_pct` must be numeric, not None — Bug A surface."""
      transport = ASGITransport(app=app)
      async with AsyncClient(transport=transport, base_url="http://test") as client:
          response = await client.get("/api/v1/schedule/capacity/2026-05-04")
      assert response.status_code == 200
      body = response.json()
      assert "utilization_pct" in body
      assert isinstance(body["utilization_pct"], (int, float))


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_utilization_report_falls_back_to_synthetic_shift_when_no_availability() -> None:
      """Empty `staff_availability` must NOT yield empty resources — dev parity."""
      from grins_platform.api.v1.schedule import get_schedule_service
      from grins_platform.services.schedule_generation_service import (
          ScheduleGenerationService,
      )

      tech = _staff()
      mock_session = MagicMock()
      # First call (`Staff` filter) returns one tech.
      # Second call inside helper (`StaffAvailability` filter) returns None.
      # Third call (`Appointment` filter) returns []
      mock_session.query.return_value.filter.return_value.all.side_effect = [
          [tech],  # active staff
          [],      # appointments for date
      ]
      mock_session.query.return_value.filter.return_value.first.return_value = None

      service = ScheduleGenerationService(db=mock_session)
      app.dependency_overrides[get_schedule_service] = lambda: service

      try:
          transport = ASGITransport(app=app)
          async with AsyncClient(transport=transport, base_url="http://test") as client:
              response = await client.get(
                  "/api/v1/schedule/utilization?schedule_date=2026-05-04"
              )
          assert response.status_code == 200
          body = response.json()
          assert len(body["resources"]) == 1
          r0 = body["resources"][0]
          assert r0["total_minutes"] == ScheduleGenerationService.DEFAULT_SHIFT_MINUTES
          assert r0["assigned_minutes"] == 0
          assert r0["utilization_pct"] == 0.0
      finally:
          app.dependency_overrides.clear()


  @pytest.mark.integration
  @pytest.mark.asyncio
  async def test_utilization_report_uses_real_availability_when_present() -> None:
      """When availability rows exist, total_minutes reflects them."""
      from grins_platform.api.v1.schedule import get_schedule_service
      from grins_platform.services.schedule_generation_service import (
          ScheduleGenerationService,
      )

      tech = _staff()
      avail = _availability(tech.id, start=time(8, 0), end=time(17, 0), lunch=60)
      mock_session = MagicMock()
      mock_session.query.return_value.filter.return_value.all.side_effect = [
          [tech],  # active staff
          [],      # appointments for date
      ]
      mock_session.query.return_value.filter.return_value.first.return_value = avail

      service = ScheduleGenerationService(db=mock_session)
      app.dependency_overrides[get_schedule_service] = lambda: service

      try:
          transport = ASGITransport(app=app)
          async with AsyncClient(transport=transport, base_url="http://test") as client:
              response = await client.get(
                  "/api/v1/schedule/utilization?schedule_date=2026-05-04"
              )
          assert response.status_code == 200
          body = response.json()
          assert len(body["resources"]) == 1
          # 9h shift minus 60-min lunch == 8 * 60.
          assert body["resources"][0]["total_minutes"] == 8 * 60
      finally:
          app.dependency_overrides.clear()
  ```

- **PATTERN**: Mirror existing tests in
  `tests/integration/test_ai_scheduling_integration.py:403-450`
  (smoke pattern) and `:943-1080` (dependency-override + body assertions).
- **IMPORTS**: All listed inline above.
- **GOTCHA**: The SQLAlchemy mocking via `side_effect` is order-sensitive
  — the helper calls `.query(Staff)…all()` then `.query(StaffAvailability)
  …first()` then `.query(Appointment)…all()`. Verify order by reading
  the new helpers in Task 3 again before locking in mocks.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/integration/test_resource_timeline_contract.py -v`

### Task 7: UPDATE `scripts/seed_resource_timeline_test_data.py` — backfill `staff_availability`

- **IMPLEMENT**: Add an availability-seed step before the existing wipe
  block, and an insertion step before the per-day appointment seeds:

  ```python
  # After the staff lookup at line 99, before the existing wipe:
  print(f"Cleaning prior availability rows for QA week ...")
  cur.execute(
      "DELETE FROM staff_availability WHERE staff_id IN (%s, %s, %s, %s) "
      "AND date BETWEEN %s AND %s",
      (str(viktor), str(vas), str(dad), str(steven),
       WEEK_START, WEEK_START + timedelta(days=6)),
  )

  print(f"Seeding staff_availability for Mon–Fri ...")
  for tech_id in (viktor, vas, dad, steven):
      for offset in range(5):  # Mon–Fri
          day = WEEK_START + timedelta(days=offset)
          cur.execute(
              """
              INSERT INTO staff_availability (
                  id, staff_id, date, start_time, end_time, is_available,
                  lunch_start, lunch_duration_minutes
              ) VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
              """,
              (
                  str(uuid.uuid4()), str(tech_id), day,
                  time(8, 0), time(17, 0),
                  time(12, 0), 60,
              ),
          )
  ```

- **PATTERN**: Existing `INSERT INTO …` blocks at
  `scripts/seed_resource_timeline_test_data.py:160-194`.
- **IMPORTS**: `time` and `timedelta` already imported (line 29).
- **GOTCHA**: `lunch_start` is a `time` *value*, not a string. The
  validator at `models/staff_availability.py:122-130` enforces
  `start_time < end_time`, so flipping defaults will raise.
- **VALIDATE**: `python scripts/seed_resource_timeline_test_data.py` (must
  exit 0 on the active dev DB; verify with
  `psql "$DATABASE_URL" -c "SELECT count(*) FROM staff_availability WHERE date BETWEEN '2026-05-04' AND '2026-05-10';"` returning `20`).

### Task 8: UPDATE `WeekMode.tsx` — distinguish loading from settled-empty

- **IMPLEMENT**: Tighten the `<TechHeader>` render site so `null` *only*
  flows when the upstream query is genuinely loading. After settle,
  default to `0` (or whatever `utilizationByTech[id]` is) so
  `<TechHeader>` renders a number, not `Loading…`.

  ```tsx
  // around line 279
  {techs.map((staff) => {
    const fromMap = utilizationByTech[staff.id];
    const utilPct =
      utilization.isLoading
        ? null
        : (fromMap ?? 0); // settled-but-missing → 0, not null
    return (
      <div key={`row-${staff.id}`} className="contents">
        <TechHeader staff={staff} utilizationPct={utilPct} />
        ...
  ```

- **PATTERN**: `WeekMode.tsx:145-156` already does the equivalent dance
  for capacity (`out[d] = capacity.isLoading ? null : 0`). Mirror.
- **IMPORTS**: none new.
- **GOTCHA**: Don't change `utilizationByTech` itself — that memo
  computes per-tech averages and is fine. Only change the read site so
  `null` is reserved for the loading state.
- **VALIDATE**: `cd frontend && npx tsc --noEmit`

### Task 9: UPDATE `TechHeader.tsx` — show `—` instead of `Loading…` on stuck-empty

- **IMPLEMENT**: Already partially handled by Task 8 (now passes `0`),
  but add a defensive 0-value affordance so the component never lies
  about state again. Conservative change: keep the existing copy, since
  Task 8 ensures `null` only shows during real loading. Optionally:

  ```tsx
  // TechHeader.tsx — leave the null branch as 'Loading…' (now correct);
  // no further change required if Task 8 is in place.
  ```

  If you want belt-and-suspenders defense (recommended per the bughunt
  doc): swap `'Loading…'` for `'—'` is **not** appropriate here — that
  branch is for the genuine loading state. Instead, do nothing in
  `TechHeader.tsx` and rely on Task 8 to upstream-fix the bug.

- **PATTERN**: n/a — the bug was upstream of this component.
- **IMPORTS**: none new.
- **GOTCHA**: This task is intentionally a no-op. It's listed only so a
  future reader sees that we considered changing `TechHeader` and
  rejected it, because the right fix is upstream (Task 8). Skip this
  task if you confirm Task 8 fixed it.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/`

### Task 10: ADD frontend test — settled-empty utilization renders 0%, not Loading

- **IMPLEMENT**: New `it()` block in
  `WeekMode.test.tsx`:

  ```tsx
  it('renders 0% utilized — not Loading… — when utilization settles empty', () => {
    mockUseWeeklyUtilization.mockReturnValue({
      days: Array.from({ length: 7 }, () => ({
        schedule_date: '2026-04-27',
        resources: [],
      })),
      isLoading: false,
      isError: false,
    });

    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );

    const header = screen.getByTestId('tech-header-staff-1');
    expect(header.textContent).toContain('0% utilized');
    expect(header.textContent).not.toContain('Loading');
  });

  it('renders Loading… while utilization is genuinely loading', () => {
    mockUseWeeklyUtilization.mockReturnValue({
      days: Array.from({ length: 7 }, () => undefined),
      isLoading: true,
      isError: false,
    });
    render(
      <WeekMode
        weekStart={new Date(2026, 3, 27)}
        selectedDate={null}
        onAppointmentClick={vi.fn()}
        onEmptyCellClick={vi.fn()}
        onDayHeaderClick={vi.fn()}
      />,
      { wrapper }
    );
    const header = screen.getByTestId('tech-header-staff-1');
    expect(header.textContent).toContain('Loading');
  });
  ```

- **PATTERN**: Mirror the existing `mockUseWeeklyUtilization.mockReturnValue`
  pattern at `WeekMode.test.tsx:153-169`.
- **IMPORTS**: none new.
- **GOTCHA**: `screen.getByTestId('tech-header-staff-1')` returns the
  outer `<div>`; `.textContent` includes initials and name. Use
  `.toContain` not `.toEqual`.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx`

### Task 11: VERIFY end-to-end manually on dev

- **IMPLEMENT**:
  1. Run `python scripts/seed_resource_timeline_test_data.py` against
     dev DB.
  2. Boot the dev backend (`./scripts/dev.sh`) and FE (`cd frontend &&
     npm run dev`).
  3. Open `/schedule` → switch to Resource Timeline view → navigate to
     week of 2026-05-04.
  4. Confirm: each tech shows a numeric `{n}% utilized`, capacity bar
     paints orange (Fri ≥85%) and teal (other days), Sat/Sun renders 0%
     teal cleanly (Sun has no appointments + no availability → 0%, but
     not stuck `Loading…`).
- **VALIDATE**:
  ```
  curl -s "$BACKEND_URL/api/v1/schedule/capacity/2026-05-04" | jq '.utilization_pct'   # numeric
  curl -s "$BACKEND_URL/api/v1/schedule/utilization?schedule_date=2026-05-04" | jq '.resources | length'  # >= 4
  ```

---

## TESTING STRATEGY

### Unit Tests

Per `code-standards.md` §2 the project enforces three tiers. The schema
default + service helpers are exercised by integration tests because
they're tightly coupled to the SQLAlchemy session lifecycle. If pure-unit
coverage is desired:

- `tests/unit/test_schedule_capacity_response_utilization_pct.py` —
  construct `ScheduleCapacityResponse(...)` with explicit `scheduled_minutes`
  / `total_capacity_minutes` and assert the value passed in.
- (Optional) `tests/unit/test_schedule_generation_service_utilization.py`
  — instantiate `ScheduleGenerationService` with a `MagicMock` session
  configured per Task 6's mocking pattern; assert per-staff math.

### Integration Tests

Authoritative coverage lives in
`tests/integration/test_resource_timeline_contract.py` (created in Task 6):

- Capacity response shape (Bug A).
- Utilization fallback when `staff_availability` is empty (Bug B + dev
  parity).
- Utilization with real availability rows.

### Edge Cases

- **`total_capacity_minutes == 0`**: `utilization_pct = 0.0`, no
  divide-by-zero. Tested in Task 6 fallback test.
- **Staff active but unavailable** (`is_available == False`): excluded
  by both `_load_available_staff` and the new
  `_load_active_staff_with_optional_availability`. Verify by hand-spot.
- **Appointment with `staff_id` set but missing time windows**:
  ignored in `_get_scheduled_minutes_per_staff` via the early-`continue`.
- **Multiple availability rows for the same `(staff_id, date)`**:
  `.first()` matches existing behavior of `_load_available_staff`. Don't
  change it here.
- **FE: utilization query returns `isError: true`**: existing render
  path doesn't crash; `<TechHeader>` shows `0% utilized` (acceptable —
  the error already surfaces to the user via toast/banner if upstream
  caller handles it).

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature
correctness.

### Level 1: Syntax & Style

```
uv run ruff check --fix src/grins_platform/api/v1/schedule.py src/grins_platform/services/schedule_generation_service.py src/grins_platform/schemas/schedule_generation.py
uv run ruff format src/grins_platform/api/v1/schedule.py src/grins_platform/services/schedule_generation_service.py src/grins_platform/schemas/schedule_generation.py
cd frontend && npx eslint src/features/schedule/components/ResourceTimelineView/
```

### Level 2: Unit Tests

```
uv run pytest -m unit -v src/grins_platform/tests/unit/ -k "schedule_generation or capacity or utilization"
cd frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/
```

### Level 3: Integration Tests

```
uv run pytest -m integration -v src/grins_platform/tests/integration/test_resource_timeline_contract.py
uv run pytest -m integration -v src/grins_platform/tests/integration/test_ai_scheduling_integration.py -k "capacity or utilization"
```

### Level 4: Type Checking

```
uv run mypy src/grins_platform/api/v1/schedule.py src/grins_platform/services/schedule_generation_service.py src/grins_platform/schemas/schedule_generation.py
uv run pyright src/
cd frontend && npx tsc --noEmit
```

### Level 5: Manual Validation

1. **Seed dev data**:
   `DATABASE_URL=$DEV_DATABASE_URL python scripts/seed_resource_timeline_test_data.py`
2. **API smoke** (against the running dev backend):
   ```
   curl -s "$BACKEND_URL/api/v1/schedule/capacity/2026-05-04" | jq '.utilization_pct, .scheduled_minutes, .total_capacity_minutes'
   curl -s "$BACKEND_URL/api/v1/schedule/utilization?schedule_date=2026-05-04" | jq '.resources | length, .resources[0]'
   ```
   Expected: numeric `utilization_pct` on `/capacity`; `resources.length
   >= 4` on `/utilization`; each resource has `total_minutes == 480`.
3. **UI smoke**:
   - Open `/schedule` → Resource Timeline view → week of 2026-05-04.
   - Each `<TechHeader>` shows `{n}% utilized` (no `Loading…`).
   - Friday (`Fri-overlap-…` seed → ≥85%) capacity bar orange.
   - Other weekdays teal.
   - Sun (no appts + no availability rows for that day) shows `0%`
     capacity bar — *not* a stuck skeleton.
4. **Network tab**: verify `/schedule/capacity/2026-05-04` response body
   carries `utilization_pct` (key present, numeric) and
   `/schedule/utilization?schedule_date=…` carries non-empty
   `resources[]`.

---

## ACCEPTANCE CRITERIA

- [ ] `GET /api/v1/schedule/capacity/{date}` response body includes a
      numeric `utilization_pct` (no longer absent).
- [ ] `GET /api/v1/schedule/utilization?schedule_date=…` response body
      includes one `ResourceUtilization` entry per active staff member,
      even when `staff_availability` has zero rows for the date.
- [ ] When `staff_availability` is empty, each resource's
      `total_minutes` equals `ScheduleGenerationService.DEFAULT_SHIFT_MINUTES`
      (480).
- [ ] Resource Timeline view week mode: `<TechHeader>` displays a
      numeric `{n}% utilized` after the queries settle (no permanent
      `Loading…`).
- [ ] Resource Timeline view week mode: `<CapacityFooter>` paints
      orange ≥85% / teal otherwise, with numeric labels.
- [ ] `scripts/seed_resource_timeline_test_data.py` re-run is idempotent
      and inserts 20 `staff_availability` rows (4 techs × Mon–Fri) for
      the QA week.
- [ ] All new and existing tests pass: `uv run pytest -v`,
      `cd frontend && npx vitest run`.
- [ ] Type checks pass: `uv run mypy src/`, `uv run pyright src/`,
      `cd frontend && npx tsc --noEmit`.
- [ ] Lint passes: `uv run ruff check src/`, `cd frontend && npx eslint
      src/features/schedule/`.
- [ ] No regressions in existing AI-scheduling integration tests.

---

## COMPLETION CHECKLIST

- [ ] Task 1: `ScheduleCapacityResponse.utilization_pct` field added.
- [ ] Task 2: `get_capacity` populates `utilization_pct`.
- [ ] Task 3: `_load_active_staff_with_optional_availability` +
      `_get_scheduled_minutes_per_staff` helpers added.
- [ ] Task 4: `get_resource_utilization` service method added.
- [ ] Task 5: `/utilization` route delegates to new service method.
- [ ] Task 6: New integration tests added and passing.
- [ ] Task 7: Seed script extended with `staff_availability` insertion.
- [ ] Task 8: `WeekMode.tsx` distinguishes `isLoading` from
      settled-empty.
- [ ] Task 9: `TechHeader.tsx` reviewed (no-op confirmed).
- [ ] Task 10: New FE tests added and passing.
- [ ] Task 11: Manual end-to-end smoke on dev passes.
- [ ] All validation commands (Levels 1–5) executed successfully.
- [ ] No new MyPy / Pyright / Ruff violations.

---

## NOTES

**Why one PR, not three**: BE schema + BE endpoint + dev seed + FE
defense are tightly coupled. Splitting risks a half-fix where the contract
is correct but dev data still hides the symptom (or vice versa). The
bughunt doc explicitly recommends bundling.

**Why a synthetic 480-min fallback (not just dev seed)**: even after the
seed runs, any new environment (a fresh Railway instance, a test DB, a
QA user creating data ad-hoc) will hit the same emptiness. Falling back
to a default shift is a sustainable invariant, not a dev-only band-aid.

**Why we extend `ScheduleCapacityResponse` instead of pointing the FE at
`/schedule/utilization`**: pointing FE at `/utilization` (the bughunt's
"Cleaner" option) introduces a circular dep — `/utilization` itself was
broken. Extending `ScheduleCapacityResponse` is one BE change and the FE
already reads the field name; the cleaner architectural option becomes
viable once `/utilization` is itself fixed (which we do here), so a
follow-up PR can dedupe if desired.

**Drive minutes** are intentionally hard-coded to `0` in the new method.
Drive-time only exists during solver runs (`ScheduleSolverService`) and
isn't persisted on `Appointment`. Plumbing it through is out of scope —
the field is preserved in the schema for future wiring.

**FE "Cosmetic follow-up" omitted**: the bughunt suggests rendering
`'—'` instead of `'Loading…'` when `resources` is empty. Task 8's fix
already prevents this state because the FE now passes `0` (not `null`)
when the query is settled. We don't need a UI-copy change.

**Confidence**: High. Surface area is small (4 backend files, 2 frontend
files, 1 seed script), tests cover the bug in both directions, and the
manual smoke step closes the loop.
