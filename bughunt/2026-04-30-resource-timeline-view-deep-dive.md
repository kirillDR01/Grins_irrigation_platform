# 2026-04-30 — Resource Timeline View deep-dive (post Phase 1–4)

## Context

Bughunt across the dev branch landed for `.agents/plans/schedule-resource-timeline-view.md`
(Phases 1–4, commits `3a6fceb…529d0f2`). The plan replaced the FullCalendar
week view with a hand-rolled resource grid in
`frontend/src/features/schedule/components/ResourceTimelineView/`. Verified
on dev tip `529d0f2`. FE typecheck (`tsc --noEmit`) and the 5 RTV vitest
files (69 tests) **pass**.

The bugs below survived because they are runtime / visual / contract issues
that the unit tests don't cover. They are catalogued by severity so the
schedule team can decide what to fix in this PR vs. follow-up.

---

## Severity legend

- **CRIT** — visible regression vs. legacy CalendarView, or feature
  promised by the plan that does not work in the implementation.
- **HIGH** — silent functional bug; user-impacting but not page-breaking.
- **MED** — visual / UX issue, or test mis-coverage.
- **LOW** — dead code, doc/code drift, residual cruft.

---

## CRIT-1 — Job-type colored left border never paints (every card looks the same)

### Symptom

Every `<AppointmentCard>` renders with a slate-300 (`#cbd5e1`) border on
**all four sides**, including the 4px left accent. The job-type color
promised by the plan ("Job-type colored left border (4px) using
`getJobTypeColor` — overrides the baseline border-left") does not appear.

### Root cause

`frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.tsx:167-174`

```tsx
const inlineStyle: CSSProperties = {
  opacity,
  borderWidth: 2,
  borderStyle,
  borderColor: '#cbd5e1', // slate-300 baseline border
  borderLeftWidth: 4,
  ...style,
};
```

The `palette.border` Tailwind class (e.g. `border-emerald-400`) is added
to `className` at line 182, but the inline `borderColor: '#cbd5e1'` wins
because inline `style` always beats class-based CSS regardless of
specificity. CSS shorthand `border-color` writes `border-left-color`
along with the other three sides.

### Effect

The Visual Parity Inventory in the plan called this out as the primary
job-type indicator: "card background tinted by `getJobTypeColor(job_type)`;
**status indicated by border style/opacity only**." The background tint
(`palette.bg`) does paint (Tailwind `bg-emerald-50` survives), but the
*accent border* — the high-contrast cue the plan was relying on — is
inert. Every Spring opening, Repair, Maintenance, etc. looks identical
on the left edge.

### Fix

Apply the colored left-border via inline style instead of relying on the
Tailwind class to win, e.g. derive a `fill` color from
`utils/jobTypeColors.ts` (the palette already exposes a `fill` hex for the
sparkline) and assign `borderLeftColor: palette.fill` in `inlineStyle`.

```tsx
const inlineStyle: CSSProperties = {
  opacity,
  borderWidth: 2,
  borderStyle,
  borderColor: '#cbd5e1',
  borderLeftWidth: 4,
  borderLeftColor: palette.fill,   // <-- NEW
  ...style,
};
```

Tests should also assert the inline `borderLeftColor` is set to a
non-grey value when `job_type` is non-null, otherwise this regression
will reappear silently.

---

## CRIT-2 — Non-tech staff are filtered out, hiding their appointments

### Symptom

Any appointment whose `staff_id` points to a Staff row with
`role !== 'tech'` (i.e. `'sales'` or `'admin'`) is **silently dropped**
from Week, Day, and Month modes. The legacy `CalendarView` rendered all
appointments regardless of assigned-staff role.

### Root cause

Three identical filter sites:

- `WeekMode.tsx:228-230`
  ```tsx
  const techs = (staffData?.items ?? []).filter(
    (s) => s.is_active && s.role === 'tech'
  );
  ```
- `DayMode.tsx:236-238` — same expression.
- `MonthMode.tsx:138-140` — same expression.

The bucket / lane logic only iterates `techs`, so an appointment whose
`staff_id` is admin/sales never gets a row to render in.

### Effect

If a sales rep is assigned to an estimate appointment (a real workflow
in this codebase — `StaffRole` enum at `models/enums.py:135-143` includes
`SALES`, `ADMIN`, and `TECH`), that estimate vanishes from the schedule
tab. Pre-feature, the FullCalendar single-resource view rendered the
appointment with the staff name in the title.

### Fix options

- **Cheap** — drop the `role === 'tech'` filter; render every active
  staff. The legacy view did this.
- **Cleaner** — add a config-driven role allowlist (e.g.
  `appointmentRenderRoles: ['tech', 'sales']`) so admins are excluded
  but sales reps stay visible.
- **Document** — if the v1 intent is "techs only," surface a banner
  ("N appointments hidden — assigned to non-tech staff") so the data
  doesn't disappear.

---

## CRIT-3 — Per-tech staff color is the same for every Grin's tech

### Symptom

The `getStaffColor(staff.name)` lookup that drives the `<TechHeader>`
left bar + avatar circle always returns `DEFAULT_COLOR` (emerald) for
every active tech in dev / prod. The visual differentiation the
target screenshot promises (Mike teal, Sarah violet, etc.) does not
exist in production data.

### Root cause

`frontend/src/features/schedule/utils/staffColors.ts:6-13`

```ts
export const STAFF_COLORS: Record<string, string> = {
  Viktor: '#14B8A6',
  Vas: '#8B5CF6',
  Dad: '#F59E0B',
  Gennadiy: '#F59E0B',
  Steven: '#F43F5E',
  Vitallik: '#3B82F6',
};
```

Lookup is exact-match by `staff.name`. The actual `staff.name` values in
the dev DB (and the seed used for QA, see
`scripts/seed_resource_timeline_test_data.py:80-99`) are full names:
`"Viktor Grin"`, `"Vasiliy Grin"`, `"Gennadiy Grin"`, `"Steve"`. None of
those strings is a key in the map, so every lookup falls through to
`DEFAULT_COLOR = '#10B981'` (emerald).

### Effect

Every `<TechHeader>` has the same emerald 4px left bar and avatar
background. At-a-glance row identification (the entire reason the plan
chose row-based per-tech layout) is broken.

### Fix

Either match on the first whitespace-separated token (mirrors the seed
script's `name.split()[0]` convention) or rekey the map by `staff_id` /
include nickname aliases:

```ts
export function getStaffColor(staffName: string): string {
  const first = staffName.trim().split(/\s+/)[0] ?? '';
  return STAFF_COLORS[staffName] ?? STAFF_COLORS[first] ?? DEFAULT_COLOR;
}
```

Pre-existing util (also used by `mapStyles.ts`), so the fix has
spillover benefit beyond the resource timeline.

---

## CRIT-4 — `MonthMode` `<TechHeader>` is permanently stuck on "Loading…"

### Symptom

Switching to Month mode shows every tech row with the secondary line
`"Loading…"` and never resolves. The previous fix
(`4997a61 fix(schedule): resource-timeline 0% capacity + permanent
Loading…`) addressed Week and Day mode but **not** Month mode.

### Root cause

`MonthMode.tsx:191-193`

```tsx
{techs.map((staff) => (
  <div key={`row-${staff.id}`} className="contents">
    <TechHeader staff={staff} utilizationPct={null} />
```

`utilizationPct={null}` is passed unconditionally. `<TechHeader>`
treats `null` as the "loading" sentinel
(`TechHeader.tsx:41-44`):

```tsx
{utilizationPct === null
  ? 'Loading…'
  : `${Math.round(utilizationPct)}% utilized`}
```

So Month mode permanently lies about the data state.

### Fix

Either compute a per-tech utilization for the visible month (sum of
`assigned_minutes` / `total_minutes` across the weekly fan-out the
component already has), or pass a sentinel that means "not applicable"
so `<TechHeader>` renders an em-dash instead of "Loading…":

```tsx
// Option A — month-utilization disabled for v1
<TechHeader staff={staff} utilizationPct={NaN} />
// + in TechHeader: Number.isNaN(utilizationPct) ? '—' : ...
```

Either way, the loading-vs-empty-vs-N/A distinction needs three states,
not two. This is the same defense-in-depth gap that motivated 4997a61
for Week/Day mode and the same FE-defense bullet in
`bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md` §3.

---

## HIGH-5 — `NowLine` renders once **per tech row** instead of one line spanning all rows

### Symptom

In Day mode on today's date, the rose vertical "now" indicator renders
**N times** (once inside each tech row strip) rather than as a single
floor-to-ceiling line. Each instance is contained inside its row's
`position: relative` strip, so:

1. Visually it's a stack of disconnected short rose segments.
2. `data-testid="now-line"` matches **N** elements — any E2E or
   component test that relies on a unique selector will break or
   silently match the first one.

### Evidence

`DayMode.tsx:367` mounts `<NowLine />` *inside the per-tech strip
`<div>`*:

```tsx
{positioned.map(...)}
{techAppts.length === 0 && (...)}
{isToday && <NowLine />}
```

The DayMode test acknowledges the duplication
(`DayMode.test.tsx:302-303`):

```tsx
// NowLine renders once per tech row (we have 2 active techs).
expect(screen.getAllByTestId('now-line').length).toBeGreaterThan(0);
```

The plan and visual-parity inventory promised "Vertical 'now' line
crossing all rows."

### Fix

Lift `<NowLine />` out of the row map and overlay it on the **time-axis
column** as a single absolute-positioned element:

```tsx
{/* tech rows */}
<div className="contents">{techs.map(...)}</div>

{/* single overlay spanning the time-axis column */}
{isToday && (
  <div className="col-start-2 row-start-2 row-end-[-1] relative pointer-events-none">
    <NowLine />
  </div>
)}
```

…or restructure the grid so the time-axis column is one cell with the
strips painted via background-grid + absolute children, then mount one
NowLine over that column.

Drop the now-stale `getAllByTestId('now-line').length > 0` assertion in
`DayMode.test.tsx:303` and replace with `getByTestId('now-line')`.

---

## HIGH-6 — Drag-drop in Day mode ignores grab offset → card jumps to cursor's drop position

### Symptom

In Day mode, dragging a card from its midpoint and dropping at any X
coordinate **anchors the card's NEW START at the cursor's X**, not at
the card's left edge. The classic HTML5 drag-drop "grab offset" issue.

A user grabbing a 9-10am card by the middle and dropping at the
3pm-axis position expects the card to slide to ~2:30pm (preserving the
grab-position relative to the card). Instead the card snaps to start at
3pm, which feels wrong if the user was visually aligning the LEFT edge.

### Evidence

`DayMode.tsx:151-157`

```tsx
const rect = e.currentTarget.getBoundingClientRect();
const xPct = rect.width > 0 ? (e.clientX - rect.left) / rect.width : 0;
const clampedXPct = Math.min(Math.max(xPct, 0), 1);
const rawMin = DAY_START_MIN + clampedXPct * DAY_SPAN_MIN;
const snappedStart = Math.round(rawMin / SNAP_MINUTES) * SNAP_MINUTES;
```

`e.clientX` is wherever the cursor lands at drop time. There's no
account for where on the card the user originally clicked.

### Workaround within HTML5 native DnD

In `AppointmentCard.handleDragStart`, capture the `offsetX` at the
moment of `dragstart` and serialize it into the `DragPayload`. In
`DayMode.handleRowDrop`, subtract that offset before computing
`xPct`:

```tsx
// AppointmentCard
const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
  const cardRect = e.currentTarget.getBoundingClientRect();
  const grabOffsetX = e.clientX - cardRect.left;
  const payload: DragPayload = { ...existingFields, grabOffsetX };
  ...
};

// DayMode
const xWithinStrip = (e.clientX - rect.left) - (payload.grabOffsetX ?? 0);
const xPct = rect.width > 0 ? xWithinStrip / rect.width : 0;
```

Both ends of the contract change; bump `DragPayload` in `types.ts`.

---

## HIGH-7 — E2E script's queue-presence assertions are silently wrong

### Symptom

`e2e/schedule-resource-timeline.sh:128-131` checks three queues:

```bash
ab is visible "[data-testid='reschedule-requests-queue']" || true
ab is visible "[data-testid='no-reply-review-queue']"   || true
ab is visible "[data-testid='inbox-queue']"             || true
```

The actual `data-testid` values on those components are:

| Component | Used in script | Actual rendered |
|---|---|---|
| `RescheduleRequestsQueue.tsx:112` | `reschedule-requests-queue` | `reschedule-queue` |
| `NoReplyReviewQueue.tsx:98`       | `no-reply-review-queue`   | `no-reply-queue` |
| `InboxQueue.tsx:124`              | `inbox-queue`             | `inbox-queue` ✓ |

Two of three assertions never match anything. They pass anyway because
of the trailing `|| true`, so the cross-feature integration check is
effectively a no-op.

### Fix

Update the selectors to the rendered values, and drop the `|| true` so
genuine regressions surface:

```bash
ab is visible "[data-testid='reschedule-queue']"
ab is visible "[data-testid='no-reply-queue']"
ab is visible "[data-testid='inbox-queue']"
```

If a queue is permitted to be hidden when empty, gate the assertion on
"renders OR is intentionally absent" via `--fn` instead of swallowing
all failures.

---

## MED-8 — `useReassignAppointment` is implemented but never imported

### Symptom

`frontend/src/features/schedule/hooks/useReassignAppointment.ts` (~67
LOC) is defined per Task 11 of the plan, but **no caller exists in
`src/`**. Both `WeekMode` and `DayMode` use `useUpdateAppointment`
directly with inline 409 detection.

### Effect

- Dead code in the bundle.
- The dedicated 409 toast string `"Scheduling conflict — that tech is
  already booked at that time"` defined in this hook is unused; the
  inline copy in WeekMode/DayMode uses `"that tech is already booked"`
  (slightly different wording).
- Cache invalidation strategies diverged: `useReassignAppointment`
  invalidates `appointmentKeys.detail(id) + lists() + daily + weekly +
  staffDaily`; `useUpdateAppointment` does the same set already
  (`useAppointmentMutations.ts:43-58`), so functionally a wash, but two
  copies of the same intent maintained separately.

### Fix

Either delete the unused hook (clean), or wire it up at the drop
handler in `WeekMode` / `DayMode` (matches the plan's intent and
consolidates the 409 toast text).

---

## MED-9 — `WeekMode` calls `useWeeklySchedule(start, end)` but BE only consumes `start_date`

### Symptom

`WeekMode.tsx:53-60` passes `endDateStr` (computed as
`format(addDays(weekStart, 7), 'yyyy-MM-dd')` — note the +7, an off-by-one
relative to the visible 7-day window) to `useWeeklySchedule`, but the
backend `/appointments/weekly` endpoint only reads
`start_date` (`src/grins_platform/api/v1/appointments.py:354-360`). The
`end_date` arg is silently dropped on the wire.

### Effects

1. The `endDateStr` value (`weekStart + 7 days`) is the **8th** day
   after `weekStart`, not the 7th — semantically misaligned with the
   7-cell visible window.
2. The React Query key
   (`appointmentKeys.weekly(startDate, endDate)`) includes the
   off-by-one end date, which means navigating to the next week creates
   a fresh cache entry rather than reusing the prior one. Harmless for
   correctness but wastes one cache slot per visited week.
3. The plan's `useWeeklySchedule` contract change ("end_date as a
   weekly window arg") was never implemented on the BE; FE is shipping
   a no-op param.

### Fix

Pass only `startDateStr`, and keep the FE/BE contract honest:

```tsx
const { data: weeklySchedule, ... } = useWeeklySchedule(startDateStr);
```

…or, if the intent is to support arbitrary windows, plumb `end_date`
through the BE handler. The FE call sites in
`SchedulePage.tsx:113` already call with both args, so a BE-side fix is
a non-trivial coordination change.

---

## MED-10 — `WeekMode` empty-cell click bypasses the bordered `+` button via background click

### Symptom

The cell-click handler at `WeekMode.tsx:301-305` triggers
`onEmptyCellClick` only when the click target is the cell `div` itself
(`e.target === e.currentTarget`). When the cell has appointments,
clicking the spacing between cards (which falls on the inner
`<div className="mt-1 flex flex-col gap-1">`) does **not** equal
`e.currentTarget`, so empty-region clicks inside non-empty cells are
swallowed.

### Effect

To create a new appointment in the same row+day as an existing one, the
admin must specifically aim at the cell's outer padding band (~4px
strip). Pre-feature CalendarView used FullCalendar's cell-click
semantics that fired regardless of internal child layout.

### Fix options

- Make the inner stack `pointer-events-none` for empty regions (only
  cards are interactive).
- Add a ghost "+" affordance below the last card that fires
  `onEmptyCellClick` regardless of card count, mirroring the existing
  empty-cell `+` button.
- Drop the `e.target === e.currentTarget` gate and instead check
  `(e.target as HTMLElement).closest('[data-testid^=appt-card-]')` to
  decide whether the click hit a card.

---

## MED-11 — Per-tech utilization in DayMode reads from a hook whose schema mismatch is documented

### Symptom

`DayMode.tsx:101-130` reads `utilization.resources[*].utilization_pct`
from `useUtilizationReport(dateStr)`. That endpoint was rewritten in
`4997a61` to compute from `staff_availability` + `appointments` — but
on dev, `staff_availability` is empty and only the fallback synthetic
480-min shift kicks in. On prod, only the techs with a real shift row
get a `ResourceUtilization` entry.

### Effect

Already partially mitigated by `utilizationByTech[staff.id] ?? null` →
`isLoadingUtilization ? null : 0`. So techs without a row see "0%
utilized" once data settles, which is at least honest. But:

1. Techs with NO availability row AND NO appointments report 0% (looks
   like they're idle when in reality their shift is unknown). May
   confuse admins.
2. Active techs with appointments but no `staff_availability` row will
   show a percentage off the synthetic 480-min divisor; the legacy
   `ScheduleGenerationService` may have other staff-included rules
   diverging from this.

### Fix

Pre-existing — this was raised in
`bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md`
and remediated for the loading-vs-empty distinction, but the underlying
data hole (no `staff_availability` rows) is acknowledged as a separate
backfill problem. Shouldn't block the resource-timeline ship; document
expected pct semantics in the FE.

---

## LOW-12 — `assignLanes` is documented as O(n log n) but is O(n·k)

`utils.ts:60-86` says "Greedy by start time with end-time tiebreak —
O(n log n)" but the inner `for (let i = 0; i < laneEnds.length; i++)`
loop makes per-item work proportional to the current number of lanes,
yielding O(n·k) where k = peak concurrency. For n ≤ ~50 (a tech's daily
load) this is irrelevant, but the docstring is wrong. Either tighten the
implementation (use a min-heap of lane-end-times for true O(n log n))
or update the comment.

---

## LOW-13 — `WeekMode.tsx:54` end-date computed by `addDays(weekStart, 7)` (off-by-one)

Already covered in MED-9; calling out as a tiny maintenance hazard
even if the BE drops the param. The visible 7-day window is days 0..6;
`addDays(weekStart, 7)` is day 7 (the next Monday). If a future
maintainer derives anything from this constant, the off-by-one will
bite.

---

## LOW-14 — `e2e/schedule-resource-timeline.sh` defaults to `:5174`, doc says `:5173`

```bash
BASE="${BASE:-http://localhost:5174}"
```

The doc comment two lines above says `(default http://localhost:5173)`.
Vite's default is 5173. If anyone copy-pastes the script unaware, they
hit the wrong port. Either fix the default or fix the doc.

---

## LOW-15 — Stale "CalendarView" doc references in component file headers

`AppointmentCard.tsx:8` and `index.tsx:35-37` both reference the
deleted `CalendarView` in comments. Cosmetic; will rot the next time
someone greps for `CalendarView`.

---

## Cross-cutting observations

- **All RTV vitest tests pass (5 files / 69 tests) and `tsc --noEmit`
  is clean** on dev tip `529d0f2`. The bugs above are runtime / visual
  contracts the unit tests do not assert on.
- The plan's "10/10 confidence" claim (line 1645 of the plan)
  underestimated three categories of risk that surfaced in this
  audit:
  1. Inline-style vs Tailwind-class precedence (CRIT-1).
  2. Pre-existing util coupling (CRIT-3 — `staffColors` was assumed to
     work; it never has for the active dev DB).
  3. The plan's "filter to active techs only" choice (CRIT-2)
     departed from the legacy view's "show all" semantics without
     calling it a behavior change.
- Phase 4's defense-in-depth fix in `4997a61` was correctly scoped to
  Week and Day mode but missed Month mode (CRIT-4); the same defense
  pattern (`utilizationPct === null` means loading) can lie in any
  mode that doesn't compute utilization at all.

---

## Suggested order of operations

1. **CRIT-1** (left-border color) and **CRIT-3** (staff color) — both
   are one-line fixes in shared util/style files; high visual ROI.
2. **CRIT-2** (non-tech filter) — needs a product call: keep the
   "techs only" semantic and add a banner, or revert to legacy "show
   all" semantics. Small code change either way.
3. **CRIT-4** (Month "Loading…") — extend the loading-vs-empty
   sentinel to a third "N/A" state, or compute utilization for Month
   mode.
4. **HIGH-5** (NowLine duplication) and **HIGH-6** (drag grab-offset)
   — both are real UX fixes but can ship as a follow-up if the team
   prefers a tight cut.
5. **HIGH-7** (E2E selectors) — fix the script in the same PR that
   addresses CRITs so the integration check actually validates the
   queues.
6. **MED-8 to LOW-15** — janitorial. Bundle with the next non-trivial
   schedule-feature PR.

---

## Files of interest

- `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.tsx:167-188` — CRIT-1
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx:228-230,53-60,301-305` — CRIT-2, MED-9, MED-10
- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx:236-238,151-157,367` — CRIT-2, HIGH-5, HIGH-6
- `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.tsx:138-140,191-193` — CRIT-2, CRIT-4
- `frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx:40-44` — CRIT-3, CRIT-4
- `frontend/src/features/schedule/components/ResourceTimelineView/NowLine.tsx:26-58` — HIGH-5
- `frontend/src/features/schedule/utils/staffColors.ts:6-24` — CRIT-3
- `frontend/src/features/schedule/hooks/useReassignAppointment.ts` — MED-8
- `e2e/schedule-resource-timeline.sh:26,128-131` — HIGH-7, LOW-14
- `src/grins_platform/api/v1/appointments.py:354-360` — MED-9
