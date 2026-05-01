# 2026-04-30 — Resource Timeline view: stuck "Loading…" + empty capacity bars

## Context

While seeding visual-QA fixtures for the new `ResourceTimelineView` (Phases 1–4
landed in commits `3a6fceb…94630a2`), two visible regressions surfaced on the
dev preview:

1. **Capacity bar at the bottom of every day stays at 0%** — orange/teal
   thresholds never paint.
2. **`Loading…` stays under every technician's name forever** — the per-tech
   utilization line in `TechHeader` never resolves to `{n}% utilized`.

Both are deterministic on dev and reproduce regardless of how many appointments
exist on a day. Tracing through the FE → BE wiring shows they are **two
distinct bugs at the same FE/BE seam** plus one **dev-data prerequisite** that
hides the symptom even when the contract bug is fixed.

This doc captures the findings before triage so the schedule team can decide
whether to roll the fix into the resource-timeline branch or split into a
follow-up PR.

---

## Bug A — Capacity bar always renders 0%

### Symptom

`<CapacityFooter>` at the bottom of each weekday cell renders a teal 0% bar
(or the slate skeleton while loading). Never paints orange even when the day
is heavily booked.

### FE expectation

`frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx:144-156`

```tsx
const capacityByDate = useMemo(() => {
  const out: Record<string, number | null> = {};
  dates.forEach((d, i) => {
    const day = capacity.days[i];
    if (!day) {
      out[d] = capacity.isLoading ? null : 0;
      return;
    }
    out[d] = day.utilization_pct ?? 0;   // ← reads `utilization_pct`
  });
  return out;
}, [capacity.days, capacity.isLoading, dates]);
```

`capacity.days[i]` is typed as `CapacityForecastExtended` via
`useWeeklyCapacity` (`frontend/src/features/schedule/hooks/useWeeklyCapacity.ts:23-46`).

### What the BE actually returns

`useWeeklyCapacity` calls `GET /schedule/capacity/{date}`. That route's
`response_model` is **`ScheduleCapacityResponse`** (not
`CapacityForecastExtended`):

`src/grins_platform/api/v1/schedule.py:201-244`
`src/grins_platform/schemas/schedule_generation.py:77-122` — fields are
`schedule_date, total_staff, available_staff, total_capacity_minutes,
scheduled_minutes, remaining_capacity_minutes, can_accept_more,
criteria_triggered, forecast_confidence_low/high,
per_criterion_utilization`.

There is **no `utilization_pct` field on `ScheduleCapacityResponse`.** The
`utilization_pct` field exists only on the unrelated `CapacityForecast` schema
(`src/grins_platform/schemas/ai_scheduling.py:703-732`), which `/capacity/{date}`
does **not** return.

### Effect

`day.utilization_pct` is always `undefined` → `?? 0` → every cell renders 0%.

### Root cause

The frontend hook types its result as `CapacityForecastExtended`, but the
underlying endpoint serializes `ScheduleCapacityResponse`. Two unrelated
schemas with overlapping names. TypeScript silently accepts the cast because
nothing on the FE side verifies the runtime shape.

### Compounding factor — dev DB has zero `staff_availability` rows

Even if the contract is fixed so the FE reads
`scheduled_minutes / total_capacity_minutes`, the bar will still be 0% on
dev. `ScheduleGenerationService.get_capacity` only counts staff that have a
row in `staff_availability` for that date with `is_available=TRUE`
(`src/grins_platform/services/schedule_generation_service.py:139-175,189-214`).

Verified live against `Postgres-PH_d` (Railway dev):

```
SELECT count(*) FROM staff_availability;          -- 0
SELECT min(date), max(date) FROM staff_availability; -- (NULL, NULL)
```

So `total_capacity_minutes = 0` for every date in dev, regardless of how many
appointments exist. Dividing by zero or returning a meaningless ratio.

### Fix options

- **Cheapest** — extend `ScheduleCapacityResponse` with a derived
  `utilization_pct: float` field
  (`scheduled_minutes / total_capacity_minutes * 100` when denominator > 0,
  else `0.0`). One BE change + matching schema field. FE already reads it.
- **Cleaner** — point `useWeeklyCapacity` at `/schedule/utilization` and
  reduce `resources` to a per-day average. Reuses an endpoint that already has
  per-resource `utilization_pct`, no new schema field. But see Bug B below —
  that endpoint is broken too.
- **Independently required** — backfill `staff_availability` for the active
  techs on dev so `total_capacity_minutes > 0`. Either a one-off seed script
  (8:00–17:00 Mon–Fri, off Sat/Sun) or a default-shift fallback in
  `_load_available_staff` when no row exists for the date.

---

## Bug B — `Loading…` is stuck under every technician's name

### Symptom

`TechHeader` renders the staff name + a secondary line that toggles between
`"Loading…"` (while `utilizationPct === null`) and `"{n}% utilized"`. On dev
the secondary line is permanently `"Loading…"`, even after both per-day
queries have settled and appointments are visible in the cells.

### FE expectation

`frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx:40-44`

```tsx
{utilizationPct === null
  ? 'Loading…'
  : `${Math.round(utilizationPct)}% utilized`}
```

`WeekMode.tsx:126-142` builds `utilizationByTech` by averaging
`day.resources[*].utilization_pct` across the 7 days returned by
`useWeeklyUtilization`. The pct passed to `TechHeader` is
`utilizationByTech[staff.id] ?? null` (line 279).

### What the BE actually returns

`useWeeklyUtilization` calls `GET /schedule/utilization?schedule_date=…`,
which is `UtilizationReport { schedule_date, resources: ResourceUtilization[] }`
(`src/grins_platform/schemas/ai_scheduling.py:687-700`).

The endpoint implementation:

`src/grins_platform/api/v1/schedule.py:902-941`

```python
capacity = service.get_capacity(schedule_date)         # ScheduleCapacityResponse
resources: list[ResourceUtilization] = []
for staff_cap in getattr(capacity, "staff_capacities", []):
    ...
```

But **`ScheduleCapacityResponse` has no `staff_capacities` field** (see Bug A).
So `getattr(...,"staff_capacities", [])` always returns `[]`, the loop never
executes, and the route returns `{ schedule_date, resources: [] }`.

### Effect

- `utilization.days[*].resources` is `[]` for every day.
- `utilizationByTech` ends up an empty object — no key for any `staff.id`.
- `utilizationByTech[staff.id]` is `undefined` → `?? null` → `null` is passed
  to every `<TechHeader>`.
- `TechHeader` renders `"Loading…"` forever, even though the queries
  themselves are not loading (`utilization.isLoading === false`). The component
  has no way to distinguish "still loading" from "loaded but empty."

The FE flag that *would* hint at this — `utilization.isError` — is not set
either: HTTP 200 with an empty `resources` array is a successful response
shape, just an unusable one.

### Root cause

`get_utilization_report` was written against an interface
(`capacity.staff_capacities`) that `ScheduleGenerationService.get_capacity`
has never returned. The `getattr(..., default=[])` swallows the mismatch
silently, and there are no integration tests that assert
`resources` is populated when staff and appointments exist.

(There is a related fix in commit `49d12b2 fix(ai-scheduling): align
/schedule/utilization client with BE contract`, which adjusted FE field names
but did not address the empty-list root cause.)

### Compounding factor — same dev-DB hole as Bug A

Even if `get_utilization_report` is rewritten to compute per-staff utilization
directly (e.g., from `staff_availability` + `appointments`), it would still
return `resources: []` on dev because there are zero `staff_availability`
rows. So the `Loading…` symptom does not go away from a pure BE-logic fix —
data backfill is also required.

### Fix options

- **Cheapest** — rewrite `get_utilization_report` to query
  `staff_availability` + `appointments` directly (same data
  `get_capacity` aggregates) and emit one `ResourceUtilization` per active
  staff with availability that day. Falls back to a synthetic 480-min shift
  when `staff_availability` is empty so the UI is never stranded on dev.
- **Cosmetic FE follow-up** — when
  `utilization.isLoading === false && utilization.days[*].resources` is
  empty, render `"—"` instead of `"Loading…"` so the UI stops lying about
  the data state. Useful as a defense even after the BE fix.

---

## Suggested order of operations

1. **BE** — extend `ScheduleCapacityResponse` with `utilization_pct`
   (Bug A, cheapest) **and** rewrite `get_utilization_report` to compute
   per-staff utilization without relying on the missing
   `staff_capacities` attribute (Bug B). One PR; same surface area.
2. **Dev data** — backfill `staff_availability` for the four active techs
   (Viktor Grin, Vasiliy Grin, Gennadiy Grin, Steve) for the QA week
   (2026-05-04 → 2026-05-10) with default 8:00–17:00 shifts. Either as a
   step in `scripts/seed_resource_timeline_test_data.py` or a one-off SQL
   patch.
3. **FE follow-up** — replace `"Loading…"` with `"—"` (or hide the line)
   when the upstream query has settled but returned empty resources, so
   identical breakage in the future fails loudly instead of silently looking
   like a stuck spinner.

## Files of interest

- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx:126-156,279-285`
- `frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx:40-44`
- `frontend/src/features/schedule/components/ResourceTimelineView/CapacityFooter.tsx:15-46`
- `frontend/src/features/schedule/hooks/useWeeklyCapacity.ts:23-46`
- `frontend/src/features/schedule/hooks/useWeeklyUtilization.ts:22-46`
- `src/grins_platform/api/v1/schedule.py:201-244` — `/capacity/{date}`
- `src/grins_platform/api/v1/schedule.py:893-941` — `/utilization`
- `src/grins_platform/schemas/schedule_generation.py:77-122` — `ScheduleCapacityResponse`
- `src/grins_platform/schemas/ai_scheduling.py:658-732` — `ResourceUtilization`, `UtilizationReport`, `CapacityForecast`
- `src/grins_platform/services/schedule_generation_service.py:139-214` — `get_capacity`, `_load_available_staff`
