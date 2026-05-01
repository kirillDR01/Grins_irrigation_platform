# Feature: Schedule Resource Timeline View

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing. Pay special attention to naming of existing utils, types, and models — import from the right files.

## Feature Description

Replace the current FullCalendar-based week view (`frontend/src/features/schedule/components/CalendarView.tsx`) with a brand-new **resource-grid timeline** that surfaces every technician's schedule at a glance. Three modes (Day / Week / Month) live inside the new view; the current `Day / Week / Month` toggle in FullCalendar's toolbar is removed and replaced with the new view's own toggle. Existing functionality preserved unchanged: select-day cell-click → create-appointment dialog, `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `InboxQueue`, `ClearDayDialog`, `RestoreScheduleDialog`, list view toggle, all `?scheduleJobId=` deep-links.

The new view answers four questions instantly:
1. **Who's busy when?** (rows = techs, time visible in every mode)
2. **Where are the gaps?** (whitespace ⇒ idle time)
3. **Who is over-utilized today?** (per-tech utilization % + per-day capacity bar)
4. **What needs admin attention?** (icon vocabulary on each card: ⭐ priority, 🔔 needs-review, 🔁 reschedule pending)

Drag-and-drop semantics:
- **Same row, different time** → reschedule (PATCH `time_window_start/end`).
- **Different row, same/any time** → reassign technician (PATCH `staff_id`).

## User Story

As a **business admin / dispatcher** at Grin's Irrigation
I want to **see the daily, weekly, and monthly workload of every technician on a single screen with at-a-glance time, utilization, and attention-flag visibility**
So that I can **dispatch and reassign jobs in seconds without paging through per-tech views, and catch over-utilized techs and stuck appointments before customers complain.**

## Problem Statement

The current schedule tab uses a single-resource FullCalendar week view: time on the Y-axis, days on the X-axis, every appointment lumped in. With 3–8 technicians on the road, the admin can't see who is assigned to what without clicking each event. There is no per-tech utilization visualization, no per-day capacity signal, no glanceable answer to "who's free at 11am for an emergency?", and the existing `useUtilizationReport` / `useCapacityForecast` data exposed by the AI scheduling subsystem is never surfaced on the live schedule.

## Solution Statement

Build a custom resource-timeline component family (no new paid dependencies — FullCalendar Premium's resource plugins are $480/dev/yr, off-limits). The component uses **technicians as rows** and **time/days as columns**, with **mode-switched fidelity** (industry-standard convention used by ServiceTitan, Jobber, Housecall Pro, Workiz):

- **Day mode**: rows = techs, horizontal hour axis 6am–8pm, cards are colored bars positioned by `time_window_start`/`time_window_end`. Vertical "now" line. **Drag horizontal = reschedule, drag vertical = reassign.**
- **Week mode**: rows = techs, columns = 7 days, **stacked cards** in each cell + **16px sparkline bar** at the top of each cell (mini-time-map of that day). Capacity bar row at the bottom.
- **Month mode**: rows = techs, columns = days of the month, cells show job-count badges with density coloring.

Existing `useUtilizationReport`, `useCapacityForecast`, and `useWeeklySchedule` hooks supply the data. New client-side hook `useWeeklyUtilization` fans out 7 per-day queries via `useQueries`. No backend migrations required for v1; one minor backend addition: extend `_enrich_appointment_response` to include `priority_level` from the joined `Job` so the ⭐ icon can render without an extra lookup.

## Feature Metadata

**Feature Type**: Enhancement (UI redesign with one minor BE schema extension)
**Estimated Complexity**: High (new component family, time-math, lane algorithm for overlap, drag-and-drop semantics, three modes)
**Primary Systems Affected**:
- `frontend/src/features/schedule/components/` — replace `CalendarView` with `ResourceTimelineView`
- `frontend/src/features/schedule/components/SchedulePage.tsx` — swap import, drop FullCalendar-specific state
- `frontend/src/features/schedule/hooks/` — new `useWeeklyUtilization`
- `src/grins_platform/api/v1/appointments.py` — add `priority_level` to `_enrich_appointment_response`
- `src/grins_platform/schemas/appointment.py` — add `priority_level: int | None` to `AppointmentResponse`

**Dependencies**: None new. Already-installed (verified against `frontend/package.json`): `@tanstack/react-query` 5.90, `date-fns` 4.1, `lucide-react` 0.562, `@radix-ui/react-popover` 1.1, `tailwindcss@4.1`, `react@19.2`, `fast-check` 4.6, `vitest` 4.0, `@testing-library/react` 16.3.

**NOT installed** (verify before designing):
- ❌ `@radix-ui/react-tooltip` — use native SVG `<title>` element inside `<rect>` for sparkline tooltips (fully accessible, zero deps).
- ❌ `@radix-ui/react-toggle-group` — `ViewModeToggle` uses three styled `<button>`s instead.
- ❌ `react-dnd`, `dnd-kit` — drag-drop uses HTML5 native (`draggable`, `onDragStart`, `onDrop`, `dataTransfer`).

**Do NOT add `@fullcalendar/resource-timeline`, `react-big-calendar`, or any drag-drop library** — the redesign is hand-rolled with CSS Grid + Tailwind + HTML5 native DnD.

---

## PRE-FLIGHT CHECKLIST (run before starting)

Verify these still hold. If any has changed, the plan needs adjustment:

```bash
# 1. Confirm priority_level field exists on Job model with this exact name
grep -n "priority_level" /Users/kirillrakitin/Grins_irrigation_platform/src/grins_platform/models/job.py
# Expected: line ~150–154, `priority_level: Mapped[int]`

# 2. Confirm AppointmentForm already accepts initialStaffId + initialDate
grep -n "initialStaffId\|initialDate" /Users/kirillrakitin/Grins_irrigation_platform/frontend/src/features/schedule/components/AppointmentForm.tsx
# Expected: hits at AppointmentFormProps (lines 88, 90); used at defaultValues (line 132)

# 3. Confirm the weekly query plan preloads Appointment.job (so priority_level flows)
grep -n "selectinload(Appointment.job)" /Users/kirillrakitin/Grins_irrigation_platform/src/grins_platform/repositories/appointment_repository.py
# Expected: at least 2 hits (line ~134 for list, line ~341 for paginated). Both gated on include_relationships=True.

# 4. Confirm tooltips are NOT installed
grep "react-tooltip" /Users/kirillrakitin/Grins_irrigation_platform/frontend/package.json
# Expected: no output

# 5. Confirm CalendarView.tsx is NOT in tsconfig.app.json exclude (it uses inline @ts-nocheck)
grep "CalendarView" /Users/kirillrakitin/Grins_irrigation_platform/frontend/tsconfig.app.json
# Expected: no output. The exclude list only catches *.test.ts/tsx.

# 6. Confirm Alembic head is single (CI gate)
cd /Users/kirillrakitin/Grins_irrigation_platform && bash scripts/check-alembic-heads.sh
# Expected: single head — this PR adds zero migrations.
```

If all six pass, proceed to Phase 1.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING!

**Frontend — to be replaced or rewired:**
- `frontend/src/features/schedule/components/SchedulePage.tsx` (lines 1–200) — Why: This is the host that currently renders `<CalendarView />` and will instead render `<ResourceTimelineView />`. Note line 1 has no `@ts-nocheck`; the new view must also pass `tsc -p tsconfig.app.json --noEmit`. The page is responsible for `?scheduleJobId=` deep-link (lines 87–98), `selectedDate` state (line 64), `currentWeekStart` (lines 82–84), and the `staffIdToName` / `jobIdToJob` / `customerIdToName` lookup maps (lines 119–185). All of those stay; only the calendar widget is swapped.
- `frontend/src/features/schedule/components/CalendarView.tsx` (lines 1–475) — Why: **DELETE this file entirely** at the end of the migration. The new view supersedes it. Read first to understand the existing event-color / status-class / drag-drop logic so you can port equivalent behavior. Note line 1 carries `@ts-nocheck` because this file is in the pre-existing-errors list (see `bughunt/2026-04-29-pre-existing-tsc-errors.md`); the new files must NOT use `@ts-nocheck`.
- `frontend/src/features/schedule/components/CalendarView.css` (lines 1–119) — Why: Delete after migration; copy any reusable color tokens (e.g., `.appointment-prepaid` left-border green) into `ResourceTimelineView.css` if needed.

**Frontend — must read, will reuse unchanged:**
- `frontend/src/features/schedule/hooks/useAppointments.ts` (entire file) — Why: `useWeeklySchedule(start, end)` returns the `WeeklyScheduleResponse` already enriched with `reply_state` per gap-12. Reuse without modification.
- `frontend/src/features/schedule/hooks/useAppointmentMutations.ts` — Why: `useUpdateAppointment()` is the PATCH `/appointments/{id}` mutation we'll call on drag-drop. Optimistic-update + 409-conflict-revert pattern is at `CalendarView.tsx:354-390`; mirror that for both reschedule and reassign mutations.
- `frontend/src/features/schedule/hooks/useAIScheduling.ts` (lines 99–110, 135–147) — Why: `useCapacityForecast(date)` and `useUtilizationReport(scheduleDate)` exist and target real backend endpoints (`GET /schedule/capacity/{date}`, `GET /schedule/utilization?schedule_date=...`). For week mode, fan out 7 queries via `useQueries`. The hook types `CapacityForecastExtended`, `UtilizationReport`, `ResourceUtilization` (line 61–71 of types within the file) are the source of truth.
- `frontend/src/features/schedule/utils/staffColors.ts` (entire file, 32 lines) — Why: `getStaffColor(staffName)` is the hardcoded staff-color map (Viktor=teal, Vas=violet, Dad/Gennadiy=amber, Steven=rose, Vitallik=blue, default emerald). Use for the left-border accent on each tech row and avatar-circle background.
- `frontend/src/features/schedule/types/index.ts` (lines 29–77) — Why: `Appointment` and `ReplyState` TS types. The card icons map to: `⭐` ← (NEW) `appointment.priority_level`, `🔔` ← `reply_state.has_no_reply_flag`, `🔁` ← `reply_state.has_pending_reschedule`. Add `priority_level: number | null` to `Appointment` to match the BE schema extension.
- `frontend/src/features/staff/types/index.ts` (lines 1–85) — Why: `Staff` type — fields available for the row header (id, name, role, skill_level, is_active).
- `frontend/src/features/staff/hooks/useStaff.ts` — Why: `useStaff({ page_size: 100 })` already used by SchedulePage and CalendarView. Reuse.

**Frontend — pattern reference for the new component:**
- `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx` (entire file) — Why: This is the AI-scheduling overview that ALREADY renders close to the target screenshot (rows = resources with utilization %, columns = days with jobCount, stacked cards in cells, per-day capacity bar). It is wired to `OverviewResource[]`, `OverviewDay[]`, `CapacityDay[]` shapes. **Use as the structural reference, but do NOT extend it directly** — it's read-only-overview; the new component needs drag-drop, mode-switching, click-to-create. It also has the `JOB_TYPE_COLORS` map (lines ~56–62) — extract to `frontend/src/features/schedule/utils/jobTypeColors.ts`.
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` (entire file) — Why: Lives ABOVE the calendar in `SchedulePage.tsx`. Don't touch — preserved as-is. The `🔁` icon on the new card is just a visual badge; clicking the card still routes to existing reschedule flow via the appointment-detail modal.

**Frontend — testing pattern:**
- `frontend/src/features/schedule/components/CalendarView.test.ts` (entire file) — Why: Vitest + fast-check pattern for property-based test on `formatCalendarEventLabel`. Mirror this style for new utility functions (`computeLanes`, `timeToPercent`, etc.).
- `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.test.tsx` — Why: Component-rendering test pattern with React Testing Library; mirror for `ResourceTimelineView.test.tsx` and submode tests.
- `frontend/src/features/schedule/components/AIScheduleView.test.tsx` — Why: Pattern for testing components that compose `useUtilizationReport` + `useCapacityForecast` + a render path with mocks.
- `frontend/src/features/schedule/components/AIScheduleView.pbt.test.tsx` — Why: Property-based tests using `fast-check` for invariants like "every appointment renders within its day cell" and "lanes never overlap".

**Backend — to be modified:**
- `src/grins_platform/api/v1/appointments.py` (lines 133–155) — Why: `_enrich_appointment_response` is where `job_type`, `customer_name`, `staff_name`, `service_agreement_id` are populated. Add `priority_level` from the joined `Job`. The function is called by every list/daily/weekly/staff-daily endpoint, so the field flows through automatically.
- `src/grins_platform/schemas/appointment.py` (lines 102–137) — Why: `AppointmentResponse` model. Add `priority_level: int | None = None` after `service_agreement_id`. This is an additive, non-breaking change (legacy callers receive `null` if not populated).

**Backend — must read, no changes:**
- `src/grins_platform/api/v1/schedule.py` (lines 202–301, 893–950) — Why: `/capacity/{schedule_date}` and `/utilization?schedule_date=...` endpoints. Both per-day. Frontend fans out 7 queries via `useQueries` for week mode — no backend aggregation endpoint needed for v1.
- `src/grins_platform/schemas/ai_scheduling.py` (lines 658–700) — Why: `ResourceUtilization` and `UtilizationReport` schemas — the contract `useUtilizationReport` already aligns to (per `49d12b2 fix(ai-scheduling): align /schedule/utilization client with BE contract`).
- `src/grins_platform/models/job.py` (lines 150–154, 162–163) — Why: `priority_level: int` (server_default 0) and `target_start_date` / `target_end_date`. We surface only `priority_level` in v1.
- `src/grins_platform/models/appointment.py` (lines 116–124, 190–194) — Why: Appointment model. `staff_id` FK, `scheduled_date`, `time_window_start`, `time_window_end`, `needs_review_reason` (drives 🔔 icon via `reply_state.has_no_reply_flag` enrichment).

### New Files to Create

**Frontend — main component family (vertical-slice — all under `features/schedule/components/ResourceTimelineView/`):**
- `frontend/src/features/schedule/components/ResourceTimelineView/index.tsx` — Top-level component; owns mode state (`day | week | month`), date range, and orchestrates child mode components. Replaces `<CalendarView />` import in `SchedulePage.tsx`.
- `frontend/src/features/schedule/components/ResourceTimelineView/types.ts` — Shared types: `ViewMode = 'day' | 'week' | 'month'`, `TechRow`, `DayColumn`, `Lane`, drag payloads.
- `frontend/src/features/schedule/components/ResourceTimelineView/utils.ts` — Pure helpers: `timeToMinutes`, `minutesToPercent`, `assignLanes` (interval-graph coloring), `formatTimeRange`, `getJobTypeColor`, `bucketIntoLanes`. **All exported and unit-tested in `utils.test.ts`.**
- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx` — Day mode: techs as rows, horizontal time axis, lane-positioned cards.
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx` — Week mode: techs × 7 days, stacked cards + sparkline + capacity footer.
- `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.tsx` — Month mode: techs × days-of-month, density grid.
- `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.tsx` — Card primitive used by Day & Week modes (Day uses absolute-positioned variant, Week uses stacked variant). Renders icons ⭐🔔🔁 + 💎 prepaid + status border.
- `frontend/src/features/schedule/components/ResourceTimelineView/SparklineBar.tsx` — 16px horizontal bar for week mode cells; SVG-based; tooltip on hover via `@radix-ui/react-tooltip`.
- `frontend/src/features/schedule/components/ResourceTimelineView/CapacityFooter.tsx` — Per-day capacity bar at bottom of Week mode; orange ≥85%, teal otherwise.
- `frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx` — Left-side row header (avatar circle with initials, name, utilization %).
- `frontend/src/features/schedule/components/ResourceTimelineView/DayHeader.tsx` — Top column header for Week mode (`MON 4/27` + `18 jobs`); clickable → drills into Day mode for that date.
- `frontend/src/features/schedule/components/ResourceTimelineView/ViewModeToggle.tsx` — Day/Week/Month toggle (Radix `ToggleGroup` style; matches existing `Tabs` styling).
- `frontend/src/features/schedule/components/ResourceTimelineView/NowLine.tsx` — Vertical "now" indicator for Day mode.
- `frontend/src/features/schedule/components/ResourceTimelineView/ResourceTimelineView.css` — Tailwind-arbitrary-value-friendly local styles (only what cannot be expressed in inline classes).

**Frontend — supporting files:**
- `frontend/src/features/schedule/utils/jobTypeColors.ts` — Extract `JOB_TYPE_COLORS` and `getJobTypeColor` from `ScheduleOverviewEnhanced.tsx`. Used by `AppointmentCard`.
- `frontend/src/features/schedule/hooks/useWeeklyUtilization.ts` — Fans out 7 `useUtilizationReport` queries via `useQueries`; returns `{ days: UtilizationReport[]; isLoading; isError }`.
- `frontend/src/features/schedule/hooks/useWeeklyCapacity.ts` — Same pattern for `useCapacityForecast`.
- `frontend/src/features/schedule/hooks/useReassignAppointment.ts` — New mutation; thin wrapper around `useUpdateAppointment` with optimistic-update keyed by tech-row swap; reuses existing `appointmentApi.patch`.

**Frontend — tests:**
- `frontend/src/features/schedule/components/ResourceTimelineView/utils.test.ts` — Property tests for `assignLanes` (no two overlapping intervals share a lane), `timeToPercent`, `minutesToPercent`. Use `fast-check`.
- `frontend/src/features/schedule/components/ResourceTimelineView/ResourceTimelineView.test.tsx` — Render, mode-toggle, day-header click drill-in.
- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx` — Lane positioning, drag-drop reassignment, drag-drop reschedule, now-line presence.
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx` — Sparkline rendering, capacity footer color thresholds, day-header drill-in.
- `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.test.tsx` — Density coloring.
- `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.test.tsx` — Icon rendering matrix (⭐🔔🔁💎 in every combination of presence flags).

**Backend — tests:**
- `src/grins_platform/tests/unit/test_appointment_response_priority_level.py` — Test that `_enrich_appointment_response` populates `priority_level` from the joined Job.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [TanStack Query — useQueries (parallel queries)](https://tanstack.com/query/v5/docs/framework/react/reference/useQueries)
  - Specific section: "useQueries"
  - Why: We use `useQueries` to fan out 7 per-day utilization/capacity calls in week mode without serial waterfalls.
- [FullCalendar — navLinks](https://fullcalendar.io/docs/navLinks)
  - Specific section: navLinkDayClick callback signature
  - Why: We are NOT using FullCalendar in this view, but the click-day-header-to-drill UX matches FC's `navLinks: true` default. Use as a reference for the affordance (hover underline, cursor pointer).
- [Tailwind CSS v4 — arbitrary values](https://tailwindcss.com/docs/styling-with-utility-classes#using-arbitrary-values)
  - Specific section: Arbitrary values + dynamic class names
  - Why: Time-based positioning requires dynamic `style={{ left: \`${pct}%\`, width: \`${dur}%\` }}` rather than dynamic class names — Tailwind 4's JIT cannot statically extract `left-[42.5%]` for runtime values. Use inline `style` for computed positions; reserve Tailwind classes for static styles.
- [date-fns — startOfWeek, endOfWeek, addDays, format](https://date-fns.org/v3/docs/Getting-Started)
  - Why: Date math for week ranges. Already used throughout the codebase (`SchedulePage.tsx:8`, `CalendarView.tsx:16`).
- [lucide-react icons](https://lucide.dev/icons/)
  - Specific icons to use: `Star` (priority), `BellRing` (needs-review), `RefreshCcw` (reschedule pending), `Gem` (prepaid — replaces 💎 emoji for accessibility).
  - Why: Already installed (`frontend/package.json`). Don't introduce a new icon library.
- [Radix UI Tooltip](https://www.radix-ui.com/primitives/docs/components/tooltip)
  - Why: Sparkline tooltip for hovering over a time-segment in week mode shows "9:00–10:30 — Henderson · 412 Oak St".
- [Outlook Schedule View — auto-pivot at 5+ calendars](https://www.cedarville.edu/insights/computer-help/post/use-schedule-view-in-outlook)
  - Why: Justifies the "techs as rows, time as horizontal axis" choice for Day mode. Reference only — no code.

### Patterns to Follow

**Naming Conventions (verified from CLAUDE.md / existing code):**
- React components: `PascalCase.tsx`. Files like `AppointmentCard.tsx`, `DayMode.tsx`.
- Hooks: `useCamelCase.ts` (e.g., `useWeeklyUtilization.ts`).
- Utils: `camelCase.ts` (e.g., `jobTypeColors.ts`).
- TS types in shared file `types.ts` (e.g., `ResourceTimelineView/types.ts`).
- Tests: same name as the file under test, suffix `.test.tsx` for components, `.test.ts` for utils, `.pbt.test.tsx` for property-based tests.

**Vertical-slice rule (from CLAUDE.md / DEVLOG):**
> "util lives in the slice that owns the type, not in `shared/` (only 2 callers)"

So `jobTypeColors.ts` lives in `features/schedule/utils/` (owned by the Schedule slice). Don't promote to `shared/`.

**Error Handling (mirror `CalendarView.tsx:354-390`):**
```tsx
try {
  await updateAppointment.mutateAsync({ id, data: updates });
  toast.success('Appointment updated');
} catch (error: unknown) {
  const message = error instanceof Error ? error.message : 'Update failed';
  if (message.includes('409')) {
    toast.error('Conflict — another technician is already booked at that time');
  } else {
    toast.error(`Failed to update: ${message}`);
  }
  // Revert optimistic update
  dropInfo.revert?.();
}
```

**Logging Pattern (FE):** Use `toast` from `sonner` for user-facing feedback. Don't use `console.log` (lint-blocked except in dev).

**Time / position math (new pattern, define in `utils.ts`):**
```ts
export const DAY_START_MIN = 6 * 60;   // 6:00 am
export const DAY_END_MIN   = 20 * 60;  // 8:00 pm
export const DAY_SPAN_MIN  = DAY_END_MIN - DAY_START_MIN; // 840

export function timeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + m;
}

export function minutesToPercent(min: number): number {
  return ((min - DAY_START_MIN) / DAY_SPAN_MIN) * 100;
}

/** Interval-graph coloring: assigns each appointment a lane (0..N-1)
 *  such that no two overlapping intervals share a lane. Greedy by start. */
export function assignLanes<T extends { start: number; end: number }>(items: T[]): Array<T & { lane: number }> {
  const sorted = [...items].sort((a, b) => a.start - b.start || a.end - b.end);
  const laneEnds: number[] = []; // end-time of each lane
  const out: Array<T & { lane: number }> = [];
  for (const item of sorted) {
    let lane = laneEnds.findIndex((end) => end <= item.start);
    if (lane === -1) {
      lane = laneEnds.length;
      laneEnds.push(item.end);
    } else {
      laneEnds[lane] = item.end;
    }
    out.push({ ...item, lane });
  }
  return out;
}
```

**Card icon rendering pattern (in `AppointmentCard.tsx`):**
```tsx
const icons: ReactNode[] = [];
if (appointment.priority_level && appointment.priority_level > 0) {
  icons.push(<Star key="pri" className="size-3 text-amber-500 fill-amber-500" aria-label="High priority" />);
}
if (appointment.reply_state?.has_no_reply_flag) {
  icons.push(<BellRing key="nor" className="size-3 text-rose-500" aria-label="Needs review" />);
}
if (appointment.reply_state?.has_pending_reschedule) {
  icons.push(<RefreshCcw key="resch" className="size-3 text-blue-500" aria-label="Reschedule pending" />);
}
// Cap at 3 — already-3 by construction.
```

**Drag-and-drop pattern — HTML5 native (copy-paste reference impl):**

The cards are `draggable={true}`. Drop zones are tech-row strips (Day mode) or `[tech × day]` cells (Week mode). Why HTML5 native: `react-dnd`/`dnd-kit` is not in `package.json` and we don't want to add it.

```tsx
// Card drag start (in AppointmentCard.tsx)
const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
  const payload: DragPayload = {
    appointmentId: appointment.id,
    originStaffId: appointment.staff_id,
    originDate: appointment.scheduled_date,
    originStartTime: appointment.time_window_start,
    originEndTime: appointment.time_window_end,
  };
  e.dataTransfer.setData('application/json', JSON.stringify(payload));
  e.dataTransfer.effectAllowed = 'move';
};

// Day-mode row strip drop (in DayMode.tsx)
const handleRowDrop = async (
  e: React.DragEvent<HTMLDivElement>,
  cellStaffId: string,
  cellDate: string,
) => {
  e.preventDefault();
  const raw = e.dataTransfer.getData('application/json');
  if (!raw) return;
  const payload = JSON.parse(raw) as DragPayload;

  // Compute new start time from drop X coordinate
  const rect = e.currentTarget.getBoundingClientRect();
  const xPct = (e.clientX - rect.left) / rect.width;          // 0–1
  const rawMin = DAY_START_MIN + xPct * DAY_SPAN_MIN;          // minutes-of-day
  const snappedMin = Math.round(rawMin / 15) * 15;             // 15-min grid
  // Preserve duration
  const durMin = timeToMinutes(payload.originEndTime) - timeToMinutes(payload.originStartTime);
  const newStartMin = snappedMin;
  const newEndMin = newStartMin + durMin;

  // Reject out-of-bounds
  if (newEndMin > DAY_END_MIN) {
    toast.error('Cannot schedule past 8pm — pick an earlier slot');
    return;
  }
  if (newStartMin < DAY_START_MIN) {
    toast.error('Cannot schedule before 6am');
    return;
  }

  const newStartTime = `${String(Math.floor(newStartMin/60)).padStart(2,'0')}:${String(newStartMin%60).padStart(2,'0')}:00`;
  const newEndTime   = `${String(Math.floor(newEndMin  /60)).padStart(2,'0')}:${String(newEndMin  %60).padStart(2,'0')}:00`;

  try {
    await updateAppointment.mutateAsync({
      id: payload.appointmentId,
      data: {
        staff_id: cellStaffId,           // included always — no-op if same
        scheduled_date: cellDate,         // included always — no-op if same
        time_window_start: newStartTime,
        time_window_end: newEndTime,
      },
    });
    toast.success(
      cellStaffId !== payload.originStaffId
        ? 'Reassigned and rescheduled'
        : 'Rescheduled',
    );
  } catch (error: unknown) {
    const is409 = typeof error === 'object' && error !== null && 'response' in error
      && (error as { response?: { status?: number } }).response?.status === 409;
    toast.error(is409 ? 'Scheduling conflict — that tech is already booked' : 'Update failed', {
      description: error instanceof Error ? error.message : undefined,
    });
  }
};

// Week-mode cell drop (no time precision — just staff/date)
const handleCellDrop = async (
  e: React.DragEvent<HTMLDivElement>,
  cellStaffId: string,
  cellDate: string,
) => {
  e.preventDefault();
  const raw = e.dataTransfer.getData('application/json');
  if (!raw) return;
  const payload = JSON.parse(raw) as DragPayload;
  if (payload.originStaffId === cellStaffId && payload.originDate === cellDate) {
    return;  // No-op
  }
  try {
    await updateAppointment.mutateAsync({
      id: payload.appointmentId,
      data: {
        staff_id: cellStaffId,
        scheduled_date: cellDate,
        // time stays the same in week mode
      },
    });
    toast.success('Updated');
  } catch (error: unknown) {
    const is409 = typeof error === 'object' && error !== null && 'response' in error
      && (error as { response?: { status?: number } }).response?.status === 409;
    toast.error(is409 ? 'Scheduling conflict — that tech is already booked' : 'Update failed');
  }
};

// Don't forget the dragOver handler — without it, drop never fires:
const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
};
```

Wire `onDragOver={handleDragOver}` and `onDrop={(e) => handleRowDrop(e, staff.id, date)}` on every drop zone. **Both are required** — a drop target without `preventDefault` on `dragOver` silently rejects all drops.

---

## VISUAL PARITY INVENTORY

The current `CalendarView.tsx` has subtle visual cues that admins use daily. Every item below must be preserved (or explicitly superseded) in the new view, or this becomes a regression.

| Element | Source (CalendarView.tsx / .css) | Plan in new view |
|---|---|---|
| **Status border style** — `solid` for confirmed, `dashed` for unconfirmed, `dotted` for draft | `CalendarView.css:94-113`; class names assigned at `CalendarView.tsx:151-160` | **Port to `AppointmentCard`**: read `appointment.status`, set `border-style` inline (`solid` if status ∈ {confirmed, en_route, in_progress, completed}; `dashed` if pending/scheduled; `dotted` if draft). Border width = 2px. |
| **Status opacity** — 1.0 confirmed, 0.65 unconfirmed, 0.5 draft | `CalendarView.css:94-113` | **Port**: same logic, set `opacity` inline. |
| **Status background color** — pending=amber, draft=slate, scheduled=violet, confirmed=blue, in_progress=orange, completed=green, cancelled=red, no_show=gray | `CalendarView.tsx:55-64` (`statusColors` record) | **Supersede with hybrid scheme** (per user spec, decision 3B in conversation): card background tinted by `getJobTypeColor(job_type)`; **status indicated by border style/opacity only** (above two rows). Cancelled appointments are filtered out before render (matches `CalendarView.tsx:109-112`). Verify: `appointment.status !== 'cancelled'` filter at the data-fetch layer or before passing to `<AppointmentCard />`. |
| **Prepaid green left-border (3px)** | `CalendarView.css:115-118` (`.appointment-prepaid`) | **Replaced by 💎 Gem icon** in icon row. The job-type left-border (4px) takes the green slot. |
| **Selected-day red ring + animate-pulse** — when `selectedDate` matches the appointment's date (clear-day flow) | `CalendarView.css:85-92` (`.selected-day-event`); class assignment at `CalendarView.tsx:156-160` | **Port to `AppointmentCard`**: accept `isOnSelectedDate: boolean` prop; when true, add `ring-2 ring-red-500 ring-offset-1 animate-pulse` and prefix title with `⚠️`. Plumb `selectedDate` through `ResourceTimelineView` props as today. |
| **Today's column highlight** — subtle teal background on the current day's column | `CalendarView.css:36-38` (`.fc-day-today { @apply bg-teal-50 }`) | **Port**: in `WeekMode.tsx`, the day column whose date == today gets `bg-teal-50` on the column background; `DayHeader.tsx` for that day gets `text-teal-600`. In `MonthMode.tsx`, today's cell gets a teal ring. |
| **Time label format** — "8:00 AM" (numeric/2-digit/short meridiem) | `CalendarView.tsx:460-464` (`eventTimeFormat`) | **Replace with "8:00–9:30"** (24h with en-dash, like target screenshot). Implement in `formatTimeRange` (Task 7). The card is small; meridiem markers waste space. Use `formatJobType` from `frontend/src/features/jobs/types` if needed for the job-type label. |
| **PREPAID text badge** | `CalendarView.tsx:265-273` | **Replaced by 💎 Gem icon** (per icon spec). Remove the badge entirely. |
| **📎 attachment count badge** | `CalendarView.tsx:274-282` | **Removed in v1** — not in the user-approved icon set (⭐🔔🔁💎). The data is still on the appointment via `extendedProps.attachment_count` if a future v2 wants to add. |
| **🚫 opt-out / ↻ pending-reschedule / ⚠ no-reply / ❓ unrecognized emoji pills** (`CalendarView.tsx:218-249`) | Various reply-state flags | **Replaced by lucide icons**: 🔁 `RefreshCcw` for `has_pending_reschedule`, 🔔 `BellRing` for `has_no_reply_flag`. **`customer_opted_out` and `has_unrecognized_reply` are intentionally dropped** in v1 (admin handles those via separate queues; not a per-card glance signal). Document this in DEVLOG. |
| **Mobile aggregate ⚠ N pill** (`CalendarView.tsx:283-292`) | Mobile-only collapse | **Removed** — mobile is out of scope; the existing `<AppointmentList />` mobile fallback in `SchedulePage.tsx` is preserved. |
| **`SendConfirmationButton` rendered inside draft cards** | `CalendarView.tsx:306-311` | **Port to `AppointmentCard`**: when `appointment.status === 'draft'`, render `<SendConfirmationButton appointment={appointment} compact />` in the right-edge of the card (replaces the icon row). Critical preserve — bulk-send-day-of-confirmations workflow depends on this surface. |
| **`SendDayConfirmationsButton` in day header** | `CalendarView.tsx:319-336` (renderDayHeaderContent); drafts grouped by day at `CalendarView.tsx:186-196` | **Port to `DayHeader.tsx`**: when the `draftsByDay[date]` array is non-empty, render `<SendDayConfirmationsButton date={dateStr} draftAppointments={dayDrafts} />` next to the day label. Compute `draftsByDay` in `WeekMode` from `weeklySchedule.days`. |
| **`fc-event-{id}` test id** (`CalendarView.tsx:454-458`) | E2E selector | **Port to `AppointmentCard`**: set `data-testid={\`appt-card-${appointment.id}\`}`. **Update E2E shell scripts**: `e2e/payment-links-flow.sh` references `fc-event-{id}` (per DEVLOG 2026-04-29 Bug 6). Search and update to the new selector. |
| **Cancelled-appointment filter** (`CalendarView.tsx:109-112`) | Hide cancelled events | **Port**: in `WeekMode`, `DayMode`, `MonthMode`, filter `appointment.status !== 'cancelled'` before grouping by tech / counting jobs. |
| **`firstDay={1}` (week starts Monday)** | `CalendarView.tsx:420` | **Port**: `startOfWeek(date, { weekStartsOn: 1 })` everywhere — already used in `SchedulePage.tsx:83`. |
| **`slotMinTime="06:00:00"` / `slotMaxTime="20:00:00"`** | `CalendarView.tsx:447-448` | **Port to `DAY_START_MIN`/`DAY_END_MIN`** constants in `utils.ts`. |

---

## QUALITY STANDARDS (per `.kiro/steering/*`)

The following sections enforce project-wide standards from `code-standards.md`, `tech.md`, `structure.md`, `frontend-patterns.md`, `frontend-testing.md`, `api-patterns.md`, `e2e-testing-skill.md`, `agent-browser.md`, `spec-quality-gates.md`, `spec-testing-standards.md`, `parallel-execution.md`, `auto-devlog.md`, `devlog-rules.md`, and `vertical-slice-setup-guide.md`. Every requirement below MUST be satisfied for the PR to merge.

### 1. Structured Logging Events

**Backend** — no new endpoints; the `_enrich_appointment_response` modification is data assembly, not a logged operation. Existing `appointment.api_*` events on the weekly endpoint cover the call site. **Do not add per-call DEBUG logs to `_enrich_appointment_response`** — it runs in the hot loop of every weekly fetch.

**Frontend** — user-facing events surface via `toast` from `sonner` (per `frontend-patterns.md` "Logging Pattern"). `console.log` is lint-blocked outside dev. Event table:

| FE Event | Trigger | Surface |
|---|---|---|
| `schedule.reschedule.success` | 2xx PATCH `/appointments/{id}` with `time_window_*` change, same `staff_id` | `toast.success('Rescheduled')` |
| `schedule.reassign.success` | 2xx PATCH with new `staff_id` | `toast.success('Reassigned and rescheduled')` |
| `schedule.update.conflict` | 409 from PATCH | `toast.error('Scheduling conflict — that tech is already booked')` |
| `schedule.update.out_of_bounds` | drop X-coord computes `endMin > DAY_END_MIN` or `startMin < DAY_START_MIN` | `toast.error('Cannot schedule past 8pm — pick an earlier slot')` |
| `schedule.update.failed` | non-409 error | `toast.error('Failed to update: {message}')` |

**Naming**: `{domain}.{component}.{action}_{state}` per `code-standards.md`. Toast titles use this prefix only in test assertions, not in the user-visible string.

**Never log**: customer phone, email, address, payment data — admin sees customer name only (already PII-acceptable per `tech.md` "PII masked in logs").

### 2. data-testid Convention Map

Per `frontend-patterns.md` data-testid convention (`{feature}-page` / `{feature}-table` / `{action}-{feature}-btn`) and `spec-quality-gates.md` requirement to map every frontend element:

| Element | data-testid |
|---|---|
| `ResourceTimelineView` root | `schedule-resource-timeline` |
| `WeekMode` root | `schedule-week-mode` |
| `DayMode` root | `schedule-day-mode` |
| `MonthMode` root | `schedule-month-mode` |
| `ViewModeToggle` root | `schedule-view-mode-toggle` |
| Day toggle button | `view-mode-day-btn` |
| Week toggle button | `view-mode-week-btn` |
| Month toggle button | `view-mode-month-btn` |
| Prev nav | `nav-prev-btn` |
| Next nav | `nav-next-btn` |
| Today nav | `nav-today-btn` |
| `TechHeader` | `tech-header-${staffId}` |
| `DayHeader` (week mode) | `day-header-${date}` (date as `YYYY-MM-DD`) |
| `[tech × day]` cell | `cell-${staffId}-${date}` |
| `AppointmentCard` | `appt-card-${appointmentId}` |
| `SparklineBar` | `sparkline-${staffId}-${date}` |
| `CapacityFooter` cell | `capacity-${date}` |
| `NowLine` | `now-line` |
| Empty state ("No technicians") | `schedule-empty-state` |

Add to every component as it is created in Tasks 12–25; reference this map from each component's `**IMPLEMENT**` block.

### 3. agent-browser E2E Validation Script

Required by `e2e-testing-skill.md`, `frontend-testing.md`, `spec-quality-gates.md`, `spec-testing-standards.md`. Save as `e2e/schedule-resource-timeline.sh` and run after Phase 4 manual checklist. Screenshots go to `e2e-screenshots/schedule-timeline/`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Pre-flight (per e2e-testing-skill.md Phase 1)
[[ "$(uname -s)" =~ ^(Darwin|Linux)$ ]] || { echo "Unsupported platform"; exit 1; }
agent-browser --version >/dev/null 2>&1 || { npm install -g agent-browser && agent-browser install --with-deps; }

# Phase 2: Open the schedule page (assumes BE on :8000, FE on :5173)
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser wait "[data-testid='schedule-resource-timeline']"
agent-browser screenshot e2e-screenshots/schedule-timeline/01-initial-week.png
agent-browser is visible "[data-testid='schedule-week-mode']"

# Phase 3: Mode toggle
agent-browser click "[data-testid='view-mode-day-btn']"
agent-browser wait "[data-testid='schedule-day-mode']"
agent-browser screenshot e2e-screenshots/schedule-timeline/02-day-mode.png

agent-browser click "[data-testid='view-mode-month-btn']"
agent-browser wait "[data-testid='schedule-month-mode']"
agent-browser screenshot e2e-screenshots/schedule-timeline/03-month-mode.png

# Day-header drill-in (week → day)
agent-browser click "[data-testid='view-mode-week-btn']"
agent-browser wait "[data-testid='schedule-week-mode']"
agent-browser snapshot -i
agent-browser click "[data-testid^='day-header-']"
agent-browser wait "[data-testid='schedule-day-mode']"
agent-browser screenshot e2e-screenshots/schedule-timeline/04-drill-in.png

# Empty cell click → create dialog
agent-browser click "[data-testid='view-mode-week-btn']"
agent-browser wait "[data-testid='schedule-week-mode']"
agent-browser click "[data-testid^='cell-']"
agent-browser wait --text "Create Appointment"
agent-browser screenshot e2e-screenshots/schedule-timeline/05-create-dialog.png
agent-browser press Escape

# Cross-component: queues still render
agent-browser is visible "[data-testid='reschedule-requests-queue']" || true   # queue exists
agent-browser is visible "[data-testid='no-reply-review-queue']" || true
agent-browser is visible "[data-testid='inbox-queue']" || true

# Console + errors check (Phase 3 of e2e-testing-skill)
agent-browser console
agent-browser errors

# Phase 6: Responsive (mobile branch falls back to AppointmentList)
agent-browser set viewport 375 812
agent-browser screenshot e2e-screenshots/schedule-timeline/06-mobile-list-fallback.png

agent-browser set viewport 768 1024
agent-browser screenshot e2e-screenshots/schedule-timeline/07-tablet.png

agent-browser set viewport 1440 900
agent-browser screenshot e2e-screenshots/schedule-timeline/08-desktop.png

agent-browser close
```

**CRITICAL** (`e2e-testing-skill.md`): Refs become invalid after navigation. Always re-snapshot after page changes. Use stable `data-testid` selectors as above.

### 4. Coverage Targets

Per `frontend-testing.md`, `tech.md`, `code-standards.md`, `spec-quality-gates.md`:

| Layer | Target | Tooling |
|---|---|---|
| Backend services + utilities | 90%+ | `uv run pytest --cov=src/grins_platform` |
| Frontend components | 80%+ | `npm run test:coverage` |
| Frontend hooks (`useWeeklyUtilization`, `useWeeklyCapacity`, `useReassignAppointment`) | 85%+ | `npm run test:coverage` |
| Frontend utils (`utils.ts`, `jobTypeColors.ts`) | 90%+ | `npm run test:coverage` |

Coverage MUST be reported in the DEVLOG entry (Task 33).

### 5. Test Fixtures

Per `spec-quality-gates.md` "Test Fixtures" requirement. Create `frontend/src/features/schedule/components/ResourceTimelineView/__fixtures__.ts`:

```ts
import type { Staff } from '@/features/staff/types';
import type { Appointment, WeeklyScheduleResponse } from '../../types';
import type { UtilizationReport, CapacityForecastExtended } from '../../hooks/useAIScheduling';

export const mockStaff: Staff[] = [
  { id: 'staff-1', name: 'Mike Davis', role: 'Technician', skill_level: 'Senior', is_active: true /* ...rest per Staff type */ },
  { id: 'staff-2', name: 'Sarah Kim',  role: 'Technician', skill_level: 'Mid',    is_active: true },
  { id: 'staff-3', name: 'Carlos Rivera', role: 'Lead',    skill_level: 'Senior', is_active: true },
];

export const mockAppointment: Appointment = {
  id: 'appt-1',
  staff_id: 'staff-1',
  scheduled_date: '2026-04-30',
  time_window_start: '08:00:00',
  time_window_end: '09:30:00',
  status: 'confirmed',
  job_type: 'Spring opening',
  customer_name: 'Henderson',
  priority_level: 1,
  service_agreement_id: null,
  reply_state: { has_no_reply_flag: false, has_pending_reschedule: false, customer_opted_out: false, has_unrecognized_reply: false },
  /* ...rest per Appointment type */
};

export const buildWeeklySchedule = (overrides: Partial<WeeklyScheduleResponse> = {}): WeeklyScheduleResponse => ({
  start_date: '2026-04-27',
  end_date: '2026-05-03',
  days: Array.from({ length: 7 }, (_, i) => ({
    date: `2026-04-${27 + i}`,
    appointments: [],
  })),
  ...overrides,
});

export const buildUtilizationReport = (date: string, pct: number): UtilizationReport => ({
  schedule_date: date,
  resources: [{ staff_id: 'staff-1', utilization_pct: pct, hours_assigned: 0, hours_available: 0 } as never],
});

export const buildCapacityForecast = (date: string, pct: number): CapacityForecastExtended => ({
  schedule_date: date,
  capacity_pct: pct,
  /* ...rest per CapacityForecastExtended */
} as CapacityForecastExtended);
```

Backend conftest fixtures (`appointment_factory`, `job_factory`, `staff_factory`) already exist in `src/grins_platform/tests/conftest.py` — reuse, don't duplicate (per `vertical-slice-setup-guide.md`: "Test infrastructure: tests/conftest.py provides shared fixtures").

### 6. Cross-Feature Integration Tests

Per `spec-quality-gates.md` "Cross-Feature Integration and Backward Compatibility" requirement. Add to `frontend/src/features/schedule/components/SchedulePage.integration.test.tsx`:

| Test | Description |
|---|---|
| `schedule_page_with_reschedule_queue_renders` | After ResourceTimelineView mounts, RescheduleRequestsQueue still renders above and routes to AppointmentModal on click |
| `schedule_page_no_reply_queue_renders` | NoReplyReviewQueue renders unchanged |
| `schedule_page_inbox_queue_renders` | InboxQueue renders unchanged |
| `schedule_page_deep_link_scheduleJobId` | `?scheduleJobId=xxx` query param opens AppointmentModal pre-filled (preserves existing behavior at `SchedulePage.tsx:87-98`) |
| `schedule_page_clear_day_red_ring` | After ClearDayDialog selects a date, AppointmentCards on that date show `ring-red-500 animate-pulse` |
| `schedule_page_restore_dialog_works` | RestoreScheduleDialog still opens and submits |
| `schedule_page_list_mode_toggle` | List/grid toggle still works; AppointmentList renders when toggled |
| `schedule_page_mobile_falls_back_to_list` | When `isMobile` is true, AppointmentList renders instead of ResourceTimelineView |
| `schedule_page_appointment_modal_opens_on_card_click` | Clicking an AppointmentCard opens AppointmentModal with the right appointment |

Backend cross-feature integration test in `src/grins_platform/tests/integration/test_appointment_weekly_priority.py` (`@pytest.mark.integration`):

| Test | Description |
|---|---|
| `test_weekly_endpoint_returns_priority_level` | Full `/appointments/weekly` round-trip with real DB Job + Appointment + selectinload — `priority_level` populates correctly |
| `test_weekly_endpoint_priority_level_null_when_no_job` | Appointment with `job_id=NULL` returns `priority_level: null` |
| `test_appointment_response_backward_compat` | Legacy clients ignoring the new field still parse the response |

### 7. Security Considerations

Per `spec-quality-gates.md` "Security" requirement and `tech.md` security standards:

- **Auth**: `/schedule` is admin-only — JWT guard + `require_admin` is enforced by existing middleware (`core/dependencies.py`); no new auth surface added in this PR.
- **PII in logs**: Toasts may include customer name. Customer name is admin-visible PII (already in `AppointmentResponse`); acceptable in toast UI. **Do not** add `console.log` of toast contents — admin browsers may have console exposed in shared screens. **Do not** include customer phone, email, address, or payment data in any toast or drag payload.
- **Drag-drop payload**: `dataTransfer.setData('application/json', ...)` carries `appointment_id`, `staff_id`, `scheduled_date`, and time strings. These are already in the URL/DOM; no new sensitivity. **Do not** serialize customer PII into the drag payload.
- **PATCH `/appointments/{id}`**: backend already validates that `staff_id` is a valid UUID and that the user has admin privileges. Frontend does not need additional input sanitization beyond Zod validation already in `AppointmentForm`.
- **No new endpoints**: no new auth surface added. The `priority_level` field on `AppointmentResponse` does not expose new data — `Job.priority_level` is already returned in the existing `/jobs/{id}` endpoint.
- **Never log secrets/tokens/credentials** (`code-standards.md`): no API keys, JWT tokens, or session IDs appear in any new code path.

### 8. Backend Three-Tier Testing (additions to plan)

`code-standards.md` and `spec-testing-standards.md` mandate unit + functional + integration tiers for every backend change. The current plan only includes a unit test (Task 3). Add the following:

- **Task 3a — `@pytest.mark.unit` on Task 3**: Decorate every test in `test_appointment_response_priority_level.py` with `@pytest.mark.unit`. Required by `code-standards.md` Three-Tier Testing table.
- **Task 3b — CREATE `src/grins_platform/tests/functional/test_appointment_weekly_priority_functional.py`** (`@pytest.mark.functional`): Real DB. Insert a Job with `priority_level=4`, Appointment linked to it, hit the repository's `get_weekly_schedule(start, include_relationships=True)`, assert the returned `Appointment.job.priority_level == 4` round-trips through the eager-load.
- **Task 3c — CREATE `src/grins_platform/tests/integration/test_appointment_weekly_priority_integration.py`** (`@pytest.mark.integration`): Full system. Use TestClient against the real `/appointments/weekly?start_date=...` endpoint; assert the JSON response contains `priority_level` for every appointment with a linked Job, and `null` for those without.

These three tasks slot in between Task 3 and Task 4 in the implementation order; do not renumber Tasks 4–33.

### 9. Frontend Loading / Error / Empty State Coverage

Per `spec-testing-standards.md` "Frontend Testing Requirement" — every component test MUST cover:

| State | Test pattern | Components to cover |
|---|---|---|
| **Loading** | `useWeeklySchedule` mock returns `{ isLoading: true }` → `<LoadingSpinner data-testid="loading-spinner">` renders | `WeekMode`, `DayMode`, `MonthMode`, `ResourceTimelineView` |
| **Error** | hook mock throws → `<ErrorMessage>` renders with retry button | same |
| **Empty (no staff)** | `useStaff` mock returns `{ data: { items: [] } }` → `<div data-testid="schedule-empty-state">` with "No technicians available — add staff in Settings" | same |
| **Empty (no appointments)** | `useWeeklySchedule` returns days with 0 appointments → cells render as empty drop zones; sparkline shows `aria-label="No appointments"` | `WeekMode` |

Add an explicit subsection to Tasks 19, 22, 24, 27 stating "MUST include loading/error/empty state coverage as documented in Quality Standards §9." (Existing test file outlines mention the rendering tests but not all three states explicitly.)

### 10. Parallel Execution Strategy

Per `parallel-execution.md`. Estimated 40% wall-clock savings vs fully-sequential.

```
Phase 1 (sequential):  Task 1 → Task 2 → Task 3 (+3a/3b/3c) — BE schema, enrichment, BE three-tier tests
Phase 2 (parallel):    Task 4 (FE type) | Task 5 (jobTypeColors) | Task 6 (types.ts) | Task 7 (utils.ts)
Phase 3 (sequential):  Task 8 (utils.test.ts — needs Task 7)
Phase 4 (parallel):    Task 9 (useWeeklyUtilization) | Task 10 (useWeeklyCapacity) | Task 11 (useReassignAppointment)
Phase 5 (parallel):    Task 12 (AppointmentCard) | Task 14 (SparklineBar) | Task 15 (CapacityFooter)
                       | Task 16 (TechHeader) | Task 17 (DayHeader) | Task 20 (NowLine) | Task 25 (ViewModeToggle)
Phase 6 (sequential):  Task 13 (AppointmentCard.test) — depends on Task 12
Phase 7 (parallel):    Task 18 (WeekMode) | Task 21 (DayMode) | Task 23 (MonthMode)
Phase 8 (parallel):    Task 19 (WeekMode.test) | Task 22 (DayMode.test) | Task 24 (MonthMode.test)
Phase 9 (sequential):  Task 26 (orchestrator) → Task 27 (orchestrator.test)
Phase 10 (sequential): Task 28 (SchedulePage swap) → Task 29 (verify) → Task 30 (delete CalendarView)
                       → Task 31 (E2E selectors) → Task 32 (bughunt doc) → Task 33 (DEVLOG)
```

**Subagent assignments** (`parallel-execution.md` "Subagent Pattern"): main agent queues independent tasks within a phase to separate subagents, waits for all to complete, then runs the test/quality phase. Use `general-purpose` subagent for component creation, `Plan` for architecture review only if a phase blocker emerges.

### 11. DEVLOG entry (Task 33 expansion)

Per `auto-devlog.md` and `devlog-rules.md`. The Task 33 DEVLOG entry MUST follow the format:

```markdown
## [YYYY-MM-DD HH:MM] - FEATURE: Schedule Resource Timeline View

### What Was Accomplished
- Replaced FullCalendar week view with hand-rolled resource-grid timeline (Day/Week/Month modes)
- Added `priority_level` field to `AppointmentResponse` (BE additive change)
- Wired ⭐🔔🔁💎 icon vocabulary on appointment cards
- Drag-drop reschedule (horizontal) + reassign (vertical) in Day mode; reassign-by-day in Week mode
- Deleted `CalendarView.{tsx,css,test.ts,test.tsx}` (~475 LOC removed)

### Technical Details
- New component family at `frontend/src/features/schedule/components/ResourceTimelineView/` (~14 files)
- New hooks: `useWeeklyUtilization`, `useWeeklyCapacity`, `useReassignAppointment` (TanStack `useQueries` fan-out pattern)
- Backend: `_enrich_appointment_response` populates `priority_level` from joined `Job` (selectinload already in place for weekly path)
- Coverage: <fill in actual numbers from npm run test:coverage and pytest --cov>

### Decision Rationale
- Hand-rolled vs FullCalendar Premium ($480/dev/yr): zero deps, full design control, ~600–800 LOC trade-off
- Techs as ROWS in Day mode: matches Outlook auto-pivot, ServiceTitan, Float, Resource Guru convention
- Single-click drill-in on day headers: NN/G + Baymard guidance against double-click
- Max 3 icons per card: visual budget on stacked-card cells; severity order: priority > no-reply > reschedule > prepaid

### Challenges and Solutions
- HTML5 native DnD requires `preventDefault` on `dragOver` AND `drop` — easy-to-miss; documented in plan §"drag-and-drop reference impl"
- Tailwind 4 cannot statically extract dynamic widths — used inline `style` for time-based positioning
- `customerCity` deferred to v2 (not currently in `AppointmentResponse`)
- Multi-day jobs deferred (`Appointment` model has no `parent_appointment_id`)

### Next Steps
- Extend `_enrich_appointment_response` with `customer_city` for v2 cards
- Mobile resource grid (currently falls back to `AppointmentList`)
- Multi-day job spanning UI (requires BE migration for `parent_appointment_id`)
```

Insert at TOP of `DEVLOG.md`, immediately after `## Recent Activity` header (per `devlog-rules.md` "Entry Ordering").

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Backend schema extension + shared utilities

Add the one minor backend extension that makes `priority_level` available to the FE without an extra fetch, then build the foundational TS utilities and types.

**Tasks:**
- Add `priority_level: int | None` to `AppointmentResponse` Pydantic schema and `_enrich_appointment_response`.
- Add `priority_level: number | null` to TS `Appointment` interface.
- Create `features/schedule/utils/jobTypeColors.ts` extracted from `ScheduleOverviewEnhanced.tsx`.
- Create `ResourceTimelineView/types.ts` and `ResourceTimelineView/utils.ts` with all time/lane math.
- Create `useWeeklyUtilization` and `useWeeklyCapacity` hooks (parallel-query fan-out).
- Create `useReassignAppointment` mutation.

### Phase 2: Core Implementation — Three modes

Build the three rendering modes in priority order: Week (target screenshot), Day (admin's primary triage tool), Month (density only).

**Tasks:**
- Build `WeekMode.tsx` with stacked cards, sparkline bars, day headers, capacity footer.
- Build `AppointmentCard.tsx` (stacked variant for Week, absolute variant for Day).
- Build `SparklineBar.tsx` and `CapacityFooter.tsx`.
- Build `DayMode.tsx` with horizontal hour axis, lane-positioned cards, now-line, drag-drop.
- Build `MonthMode.tsx` with density grid.
- Build `ResourceTimelineView/index.tsx` orchestrator with mode toggle.

### Phase 3: Integration — Wire into SchedulePage

Replace `<CalendarView />` and remove FullCalendar week-view code from SchedulePage. Preserve everything else.

**Tasks:**
- Swap imports in `SchedulePage.tsx`.
- Verify deep-link (`?scheduleJobId=`) flow still opens the create-dialog with date pre-fill.
- Verify `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `InboxQueue`, `ClearDayDialog`, `RestoreScheduleDialog`, `AppointmentList`, `AppointmentModal` still render and function unchanged.
- Delete `CalendarView.tsx` and `CalendarView.css` after green tests.

### Phase 4: Testing & Validation

Comprehensive test suite mirroring the existing `*.test.tsx` and `*.pbt.test.tsx` patterns.

**Tasks:**
- Property-based tests for `assignLanes` invariants.
- Component tests for each mode (rendering, interaction, mode toggle, drill-in).
- Backend test for `priority_level` enrichment.
- Manual validation against the target screenshot.

---

## STEP-BY-STEP TASKS

### Task Format Guidelines

Use information-dense keywords:
- **CREATE**: New files
- **UPDATE**: Modify existing
- **ADD**: Insert into existing
- **DELETE**: Remove deprecated
- **REFACTOR**: Restructure without behavior change
- **MIRROR**: Copy pattern from elsewhere

---

### Task 1: UPDATE `src/grins_platform/schemas/appointment.py`

- **IMPLEMENT**: Add `priority_level: int | None = None` to `AppointmentResponse` immediately after `service_agreement_id` (line 133). Field description: `"Priority level (0–5) from the linked Job; 0 = none, 5 = highest."`
- **PATTERN**: Mirror the existing optional-extended-field pattern in `AppointmentResponse` (e.g., `customer_name: Optional[str] = None`).
- **IMPORTS**: No new imports — `Optional` is already imported from typing on line 8.
- **GOTCHA**: This is additive — legacy callers default to `None`. Do NOT add to `AppointmentBase` / `AppointmentCreate` / `AppointmentUpdate` — it's a derived display field, not editable.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run python -c "from grins_platform.schemas.appointment import AppointmentResponse; assert 'priority_level' in AppointmentResponse.model_fields; print('ok')"`

### Task 2: UPDATE `src/grins_platform/api/v1/appointments.py`

- **IMPLEMENT**: In `_enrich_appointment_response` (line 133), populate `response.priority_level` from `appointment.job.priority_level` if `appointment.job` is loaded. The function uses `model_validate(appointment)` first, then post-fills extended fields.
- **PATTERN**: See how `customer_name` and `staff_name` are populated in the same function. Follow the `getattr(appointment, 'job', None)` defensive pattern in case the relationship isn't preloaded.
  ```python
  job = getattr(appointment, 'job', None)
  if job is not None:
      response.priority_level = getattr(job, 'priority_level', None)
  ```
- **IMPORTS**: None new.
- **GOTCHA — preload status, verified**:
  - **Weekly path** (`/appointments/weekly`): ✅ already preloads. `services/appointment_service.py:933` `get_weekly_schedule_with_reply_state` calls `get_weekly_schedule(start, include_relationships=True)`, and `repositories/appointment_repository.py:133-136` does `selectinload(Appointment.job).selectinload(Job.customer)` when that flag is on. `priority_level` will populate on the weekly endpoint without further changes — this is the only endpoint the new view needs in v1.
  - **Daily / list / staff-daily paths**: NOT verified — these may pass `include_relationships=False` (the default). Run `grep -n "include_relationships" src/grins_platform/services/appointment_service.py src/grins_platform/api/v1/appointments.py` to inventory; if the daily and staff-daily paths default to `False`, `priority_level` will silently return `None` on those endpoints. **Acceptable for v1** because the new resource-grid view ONLY uses the weekly endpoint. If future code uses daily/list and needs `priority_level`, flip those callers to `include_relationships=True` then.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests -k "weekly_schedule or appointment_response" -x -v`

### Task 3: CREATE `src/grins_platform/tests/unit/test_appointment_response_priority_level.py`

- **IMPLEMENT**: Single test that asserts `_enrich_appointment_response` returns `priority_level=3` when the input appointment has a job with `priority_level=3`. Also assert it returns `None` when `appointment.job` is `None`.
- **PATTERN**: Mirror `src/grins_platform/tests/unit/test_appointment_service_crm.py` — uses Mock-based unit testing without DB.
- **IMPORTS**:
  ```python
  from unittest.mock import MagicMock
  from grins_platform.api.v1.appointments import _enrich_appointment_response
  ```
- **GOTCHA**: `_enrich_appointment_response` calls `AppointmentResponse.model_validate(appointment)` which uses `model_config = ConfigDict(from_attributes=True)`. Build the mock with the right shape: a `MagicMock(spec=...)` that has every required field on `AppointmentResponse`, plus a `.job.priority_level` attribute.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest src/grins_platform/tests/unit/test_appointment_response_priority_level.py -x -v`

### Task 4: UPDATE `frontend/src/features/schedule/types/index.ts`

- **IMPLEMENT**: Add `priority_level: number | null;` to the `Appointment` interface (line 53–77) immediately after `service_agreement_id`.
- **PATTERN**: Mirror the surrounding optional fields.
- **IMPORTS**: None.
- **GOTCHA**: Do NOT add to `AppointmentCreate` or `AppointmentUpdate`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 5: CREATE `frontend/src/features/schedule/utils/jobTypeColors.ts`

- **IMPLEMENT**: Extract `JOB_TYPE_COLORS` and `getJobTypeColor` from `ScheduleOverviewEnhanced.tsx`. Add a `JOB_TYPE_BORDER_COLORS` for the left-border accent (darker shade) and an unknown-type fallback. Export shape:
  ```ts
  export const JOB_TYPE_COLORS: Record<string, { bg: string; border: string; text: string }>;
  export function getJobTypeColor(jobType: string | null | undefined): { bg: string; border: string; text: string };
  ```
  Cover at least: `Spring opening`, `Fall closing`, `Maintenance`, `Backflow test`, `New build`, `Repair`, `Diagnostic`, `Estimate`. Default to neutral gray for unknowns.
- **PATTERN**: Use Tailwind class strings (e.g., `'bg-emerald-50 border-emerald-300 text-emerald-900'`) — match the convention in the existing `JOB_TYPE_COLORS`.
- **IMPORTS**: None.
- **GOTCHA**: Match the `Job.job_type` casing as it appears in production data (verify with `formatJobType` in `frontend/src/features/jobs/types/index.ts`). Job type strings in the DB are free-form per `models/job.py:139` (`String(50)` — no enum). Use a case-insensitive lookup.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 6: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/types.ts`

- **IMPLEMENT**:
  ```ts
  import type { Appointment } from '../../types';
  import type { Staff } from '@/features/staff/types';

  export type ViewMode = 'day' | 'week' | 'month';

  export interface TechRow {
    staff: Staff;
    appointments: Appointment[];
    utilizationPct: number;
  }

  export interface DayColumn {
    date: string;          // YYYY-MM-DD
    label: string;         // 'MON 4/27'
    jobCount: number;
    capacityPct: number | null;
  }

  export interface PositionedAppointment extends Appointment {
    lane: number;
    startMin: number;
    endMin: number;
  }

  export interface DragPayload {
    appointmentId: string;
    originStaffId: string;
    originDate: string;
    originStartTime: string;
    originEndTime: string;
  }
  ```
- **IMPORTS**: As above.
- **GOTCHA**: Use `import type` to avoid runtime imports (per Tailwind 4 + React 19 + the project's strict TS setup).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 7: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/utils.ts`

- **IMPLEMENT**: Pure functions only — no React, no fetch.
  - `DAY_START_MIN = 360` (6:00 am)
  - `DAY_END_MIN = 1200` (8:00 pm)
  - `DAY_SPAN_MIN = 840`
  - `timeToMinutes(t: string): number` — parses `'HH:MM:SS'` or `'HH:MM'`
  - `minutesToPercent(min: number): number` — clamped 0–100
  - `formatTimeRange(start: string, end: string): string` — `'8:00–9:30'` (en-dash)
  - `assignLanes<T extends { start: number; end: number }>(items: T[]): Array<T & { lane: number }>` — interval-graph coloring (greedy by start, with end-tiebreak); guarantee: no two items with overlapping `[start, end)` share a lane.
  - `formatDayLabel(date: string): string` — `'MON 4/27'`
  - `getInitials(name: string): string` — `'Mike Davis' → 'MD'`, `'Madonna' → 'M'`
- **PATTERN**: Pure functions, named exports. See `formatCalendarEventLabel` in `CalendarView.tsx:46-53` for the docstring style.
- **IMPORTS**: `import { format, parse } from 'date-fns'`.
- **GOTCHA**: `assignLanes` must be O(n log n) (sort + linear scan). Don't quadratic-search lane availability. The reference impl in the "Patterns to Follow" section above is correct — copy it verbatim.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 8: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/utils.test.ts`

- **IMPLEMENT**: Property-based tests for `assignLanes` and unit tests for the rest:
  - **PBT**: For 100 random arrays of 0–50 intervals in `[360, 1200]`, assert that no two items with overlapping intervals end up with the same `lane`.
  - **PBT**: `assignLanes` is stable for non-overlapping inputs (lane = 0 for all).
  - Unit: `timeToMinutes('06:00:00') === 360`, `timeToMinutes('20:00:00') === 1200`, `timeToMinutes('14:30') === 870`.
  - Unit: `minutesToPercent(360) === 0`, `minutesToPercent(1200) === 100`, `minutesToPercent(780) ≈ 50`.
  - Unit: `formatTimeRange('08:00:00', '09:30:00') === '8:00–9:30'`.
  - Unit: `getInitials('Mike Davis') === 'MD'`, `getInitials('Madonna') === 'M'`, `getInitials('') === '?'`.
- **PATTERN**: Mirror `frontend/src/features/schedule/components/CalendarView.test.ts` (Vitest + fast-check).
- **IMPORTS**:
  ```ts
  import { describe, it, expect } from 'vitest';
  import * as fc from 'fast-check';
  import { assignLanes, timeToMinutes, minutesToPercent, formatTimeRange, getInitials } from './utils';
  ```
- **GOTCHA**: `fast-check` arbitrary for an interval: `fc.tuple(fc.integer({min:360,max:1199}), fc.integer({min:1,max:120})).map(([s,d]) => ({start: s, end: Math.min(s+d, 1200)}))`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/utils.test.ts`

### Task 9: CREATE `frontend/src/features/schedule/hooks/useWeeklyUtilization.ts`

- **IMPLEMENT**:
  ```ts
  import { useQueries } from '@tanstack/react-query';
  import { apiClient } from '@/core/api/client';
  import { addDays, format } from 'date-fns';
  import { aiSchedulingKeys, type UtilizationReport } from './useAIScheduling';

  export function useWeeklyUtilization(weekStart: Date) {
    const dates = Array.from({ length: 7 }, (_, i) => format(addDays(weekStart, i), 'yyyy-MM-dd'));
    const queries = useQueries({
      queries: dates.map((date) => ({
        queryKey: aiSchedulingKeys.utilization(date),
        queryFn: async () => {
          const res = await apiClient.get<UtilizationReport>('/schedule/utilization', { params: { schedule_date: date } });
          return res.data;
        },
        staleTime: 30_000,
      })),
    });
    return {
      days: queries.map((q) => q.data),  // (UtilizationReport | undefined)[]
      isLoading: queries.some((q) => q.isLoading),
      isError: queries.some((q) => q.isError),
    };
  }
  ```
- **PATTERN**: Mirror `useQueries` usage in `SchedulePage.tsx:137-144` (jobQueries fan-out).
- **IMPORTS**: As above.
- **GOTCHA**: Reuse `aiSchedulingKeys.utilization(date)` so cache entries are shared with the existing `useUtilizationReport(date)` consumers — no double-fetch.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 10: CREATE `frontend/src/features/schedule/hooks/useWeeklyCapacity.ts`

- **IMPLEMENT**: Identical pattern to Task 9 but targeting `/schedule/capacity/{date}` and `aiSchedulingKeys.capacityForecast(date)`. Returns `{ days: (CapacityForecastExtended | undefined)[]; isLoading; isError }`.
- **PATTERN**: See Task 9.
- **IMPORTS**: `import { aiSchedulingKeys, type CapacityForecastExtended } from './useAIScheduling';`
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 11: CREATE `frontend/src/features/schedule/hooks/useReassignAppointment.ts`

- **IMPLEMENT**: Thin wrapper around `useUpdateAppointment` that PATCHes `staff_id` only. Provide both an "optimistic" path (immediately re-render the card under the new tech) and a 409-conflict revert. Use the same `appointmentApi.patch` underneath.
- **PATTERN**: See `useUpdateAppointment` and `CalendarView.tsx:354-390` for the optimistic + revert pattern.
- **IMPORTS**: `import { useUpdateAppointment } from './useAppointmentMutations';`
- **GOTCHA**: 409 may come from the backend's "two appointments overlap on same staff" guard. Surface via `toast.error` with a clear message.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 12: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.tsx`

- **IMPLEMENT**: Two render variants gated by a `variant` prop:
  - `variant='stacked'` (week mode): full-width compact card showing time range + customer name + city + job-type colored left border + icon row.
  - `variant='absolute'` (day mode): absolute-positioned via `style={{ left, width, top, height }}` props passed in by parent.
  
  Component signature:
  ```tsx
  interface AppointmentCardProps {
    appointment: Appointment;
    customerCity?: string | null;       // Joined from property if available
    variant: 'stacked' | 'absolute';
    isOnSelectedDate?: boolean;          // Clear-day-flow red ring
    style?: React.CSSProperties;          // Absolute positioning (variant='absolute')
    onAppointmentClick: (id: string) => void;
  }
  ```
  
  Card surface elements (in order):
  1. **Status border** (visual parity row 1+2): `border-style` from status — `solid` if `confirmed|en_route|in_progress|completed`, `dashed` if `pending|scheduled`, `dotted` if `draft`. Border width 2px. Color matches `border-slate-300` baseline (the colored accent is the LEFT border below).
  2. **Status opacity**: 1.0 / 0.65 / 0.5 by the same status buckets.
  3. **Selected-day ring** (visual parity row 5): if `isOnSelectedDate`, add `ring-2 ring-red-500 ring-offset-1 animate-pulse` + ⚠️ emoji prefix on title.
  4. **Job-type colored left border (4px)** using `getJobTypeColor` — overrides the baseline border-left.
  5. Time text (e.g., "8:00–9:30") in 11px slate-600 via `formatTimeRange`.
  6. Job type text (e.g., "Spring opening") in 12px font-semibold, color from `getJobTypeColor`.
  7. Customer line: `{customer_name} · {customerCity ?? ''}` in 11px slate-700, truncate.
  8. **Icons row** (right-aligned): ⭐ if `priority_level && priority_level > 0`, 🔔 if `reply_state?.has_no_reply_flag`, 🔁 if `reply_state?.has_pending_reschedule`, 💎 (Gem) if `service_agreement_id`. Cap at 3 most-severe; severity order: `priority > no_reply > reschedule > prepaid`.
  9. **Draft action** (visual parity SendConfirmationButton row): if `appointment.status === 'draft'`, render `<SendConfirmationButton appointment={appointment} compact />` instead of the icon row.
  
  **Test id**: `data-testid={\`appt-card-${appointment.id}\`}` (replaces the FC `fc-event-{id}` selector — see "E2E test-id rename" task at end of plan).
  
  Drag attributes (full impl in "Patterns to Follow" → drag-and-drop reference impl):
  ```tsx
  draggable
  onDragStart={handleDragStart}
  onClick={() => onAppointmentClick(appointment.id)}
  ```
  
  Status → border-style helper:
  ```tsx
  const STATUS_BORDER_STYLE: Record<AppointmentStatus, 'solid' | 'dashed' | 'dotted'> = {
    confirmed: 'solid', en_route: 'solid', in_progress: 'solid', completed: 'solid',
    pending: 'dashed', scheduled: 'dashed',
    draft: 'dotted',
    cancelled: 'dashed', no_show: 'dashed',  // not actually rendered (cancelled filtered upstream)
  };
  const STATUS_OPACITY: Record<AppointmentStatus, number> = {
    confirmed: 1, en_route: 1, in_progress: 1, completed: 1,
    pending: 0.65, scheduled: 0.65, cancelled: 0.65, no_show: 0.65,
    draft: 0.5,
  };
  ```
- **PATTERN**: Match the visual language in the target screenshot + parity inventory. Use `lucide-react` icons (`Star`, `BellRing`, `RefreshCcw`, `Gem`). Use `getStaffColor` only for the row border on `TechHeader`, not the card.
- **IMPORTS**:
  ```tsx
  import { Star, BellRing, RefreshCcw, Gem } from 'lucide-react';
  import { SendConfirmationButton } from '../SendConfirmationButton';
  import { getJobTypeColor } from '../../utils/jobTypeColors';
  import { formatTimeRange } from './utils';
  import type { Appointment, AppointmentStatus } from '../../types';
  import type { DragPayload } from './types';
  ```
- **GOTCHA**: Don't `@ts-nocheck` this file. It must pass strict TS. Use proper React 19 event handler types — `React.DragEvent<HTMLDivElement>`, etc. The `customerCity` prop is optional because daily/weekly responses don't currently include city; for v1 pass `null` and just show `customer_name`. (Future enhancement: extend `_enrich_appointment_response` with city.)
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/AppointmentCard.test.tsx`

### Task 13: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/AppointmentCard.test.tsx`

- **IMPLEMENT**: Test the icon-rendering matrix:
  - Each icon flag independently true → its icon renders, others don't.
  - All four flags true → exactly 3 icons render (the most-severe 3 by the documented order).
  - No flags → no icons.
  - `priority_level=0` → no star (only `> 0` triggers).
  - Click handler fires with `appointment.id`.
  - `dataTransfer.setData` is called with valid JSON on drag start.
- **PATTERN**: Mirror `frontend/src/features/schedule/components/AppointmentDetail.test.tsx` for RTL setup and `vitest.fn()` for spy assertions.
- **IMPORTS**:
  ```tsx
  import { describe, it, expect, vi } from 'vitest';
  import { render, screen, fireEvent } from '@testing-library/react';
  import { AppointmentCard } from './AppointmentCard';
  ```
- **GOTCHA**: For drag-event `dataTransfer`, use a manual mock object since RTL doesn't polyfill `DataTransfer`: `fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn(), effectAllowed: '' } })`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/AppointmentCard.test.tsx`

### Task 14: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/SparklineBar.tsx`

- **IMPLEMENT**: 16px-tall horizontal SVG bar. Background = neutral-100. For each appointment, render a colored `<rect>` with `x={minutesToPercent(start)}%`, `width={minutesToPercent(end)-minutesToPercent(start)}%`, fill from `getJobTypeColor(...).border` (the darker shade — bgs are too light at 16px). **Use a native `<title>` SVG element inside each `<rect>` for tooltips** (no Radix Tooltip — `@radix-ui/react-tooltip` is NOT installed; verified against `package.json`).
  
  ```tsx
  export function SparklineBar({ appointments }: { appointments: Appointment[] }) {
    if (appointments.length === 0) {
      return <div className="h-4 bg-slate-50 rounded-sm" aria-label="No appointments" />;
    }
    return (
      <svg
        viewBox="0 0 100 16"
        preserveAspectRatio="none"
        className="h-4 w-full bg-slate-50 rounded-sm"
        role="img"
        aria-label={`${appointments.length} appointments`}
      >
        {appointments.map((appt) => {
          const startMin = timeToMinutes(appt.time_window_start);
          const endMin = timeToMinutes(appt.time_window_end);
          const x = minutesToPercent(startMin);
          const w = Math.max(minutesToPercent(endMin) - x, 1);  // floor at 1% so 30-min jobs are visible
          const color = getJobTypeColor(appt.job_type).border;
          return (
            <rect key={appt.id} x={x} y={0} width={w} height={16} fill={color}>
              <title>{`${formatTimeRange(appt.time_window_start, appt.time_window_end)} — ${appt.customer_name ?? appt.job_type ?? ''}`}</title>
            </rect>
          );
        })}
      </svg>
    );
  }
  ```
- **PATTERN**: SVG-with-percentage is the cheapest scale-invariant render. `viewBox="0 0 100 16"` + `preserveAspectRatio="none"` makes the X-axis a literal percent.
- **IMPORTS**: `import { timeToMinutes, minutesToPercent, formatTimeRange } from './utils';`, `import { getJobTypeColor } from '../../utils/jobTypeColors';`, `import type { Appointment } from '../../types';`.
- **GOTCHA**: Browser native `<title>` tooltip has a ~500ms hover delay (not configurable). Acceptable for sparkline scan use. If product wants instant tooltips later, swap to Radix Popover (already installed) or add a Tooltip primitive.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 15: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/CapacityFooter.tsx`

- **IMPLEMENT**: Renders one `<div>` per day in week mode, sticky at the bottom of the table. Each cell shows `{capacityPct}%` + a horizontal progress bar. Color: `bg-orange-500` if `capacityPct >= 85`, else `bg-teal-500`. Background: `bg-slate-100`.
- **PATTERN**: Inline `style={{ width: \`${capacityPct}%\` }}` — Tailwind 4 cannot statically extract dynamic widths.
- **IMPORTS**:
  ```tsx
  import type { DayColumn } from './types';
  ```
- **GOTCHA**: `capacityPct` may be `null` (loading) — render a `<Skeleton />` placeholder rather than `0%`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 16: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/TechHeader.tsx`

- **IMPLEMENT**: Left-side row header. Left vertical bar (4px) colored via `getStaffColor(staff.name)`. Avatar circle (32px) with `getInitials(staff.name)` and same color background, white text. Below: `staff.name` (font-semibold, 13px) and `{utilizationPct}% utilized` (12px slate-600).
- **PATTERN**: Match the visual in the target screenshot (rows: Mike D., Sarah K., Carlos R. with colored avatars and utilization %).
- **IMPORTS**:
  ```tsx
  import { getStaffColor } from '../../utils/staffColors';
  import { getInitials } from './utils';
  import type { Staff } from '@/features/staff/types';
  ```
- **GOTCHA**: `getStaffColor` keys by name, not by ID. Pass `staff.name`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 17: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/DayHeader.tsx`

- **IMPLEMENT**: Top column header for week mode. Renders `{label}` (e.g., 'MON 4/27') and `{jobCount} jobs`. Whole header is a `<button>` (NOT a div with onClick) for keyboard accessibility. On hover: underline + chevron icon (`ChevronDown` from lucide). On click: invokes `onDrillIn(date)` prop.
  
  Component signature:
  ```tsx
  interface DayHeaderProps {
    date: string;                       // YYYY-MM-DD
    jobCount: number;
    isToday: boolean;
    draftAppointments: Appointment[];   // For SendDayConfirmationsButton
    onDrillIn: (date: string) => void;
  }
  ```
  
  Visual:
  - Default: `text-slate-500 text-xs font-semibold uppercase tracking-wider`. Show date label + `{jobCount} jobs` on a second line.
  - `isToday`: text becomes `text-teal-600`, plus underline always visible.
  - Hover: `bg-slate-50` + underline on label text + `ChevronDown` icon fades in (was `opacity-0`, becomes `opacity-100`).
  - Focus-visible: `ring-2 ring-teal-500 ring-offset-2`.
  - **If `draftAppointments.length > 0`**: render `<SendDayConfirmationsButton date={date} draftAppointments={draftAppointments} />` (visual-parity row "SendDayConfirmationsButton in day header").
- **PATTERN**: Use `<button>` to get keyboard navigation + focus ring + Enter-key activation for free. The `group` Tailwind utility makes the chevron-fade-on-hover idiomatic.
- **IMPORTS**:
  ```tsx
  import { ChevronDown } from 'lucide-react';
  import { SendDayConfirmationsButton } from '../SendDayConfirmationsButton';
  import { formatDayLabel } from './utils';
  import type { Appointment } from '../../types';
  ```
- **GOTCHA**: NN/G signifier guidance — hover affordance must be visible *before* the user clicks, not after. Use `hover:underline hover:bg-slate-50 cursor-pointer` and reveal the chevron with `opacity-0 group-hover:opacity-100 transition-opacity`. **Don't put the `<SendDayConfirmationsButton>` inside the `<button>`** (button-in-button is invalid HTML). Render it as a sibling to the right of the clickable label.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run typecheck`

### Task 18: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx`

- **IMPLEMENT**: The headline component matching the target screenshot. CSS Grid layout:
  ```tsx
  <div className="grid grid-cols-[200px_repeat(7,1fr)] grid-rows-[auto_repeat(var(--N),minmax(120px,auto))_auto]">
  ```
  (Set `--N` inline via `style={{ '--N': techRows.length } as React.CSSProperties}` if using a custom CSS var; alternatively use `auto` rows with `repeat(${N}, auto)` template string.)
  
  Cells:
  - `[0,0]`: empty corner / `'RESOURCES'` label (uppercase slate-500 caption).
  - `[0,1..7]`: `<DayHeader date={...} jobCount={...} isToday={...} draftAppointments={...} onDrillIn={...} />` per day.
  - `[i,0]`: `<TechHeader staff={...} utilizationPct={...} />` for each tech.
  - `[i,j]`: `[tech × day]` cell:
    - **Today highlight** (visual-parity): `bg-teal-50` if column's date is today.
    - `<SparklineBar appointments={...} />` (top 16px).
    - Stacked `<AppointmentCard variant='stacked' isOnSelectedDate={...} />` below, in ascending `time_window_start` order.
    - Filter `appointment.status !== 'cancelled'` before rendering (visual-parity).
    - Empty cells: still drop targets; clickable to invoke `onEmptyCellClick(staffId, date)`.
    - `onDragOver={handleDragOver}`, `onDrop={(e) => handleCellDrop(e, staff.id, date)}` — full impl in "Patterns to Follow → drag-and-drop reference impl".
  - `[N+1,0]`: `'Capacity'` label (uppercase slate-500 caption).
  - `[N+1,1..7]`: `<CapacityFooter day={...} />` per day.

  Component signature:
  ```tsx
  interface WeekModeProps {
    weekStart: Date;
    selectedDate: Date | null;          // For clear-day red ring
    onAppointmentClick: (id: string) => void;
    onEmptyCellClick: (staffId: string, date: string) => void;
    onDayHeaderClick: (date: string) => void;  // Drills into Day mode
  }
  ```
  
  Compute `draftsByDay` map:
  ```tsx
  const draftsByDay = useMemo(() => {
    const map: Record<string, Appointment[]> = {};
    weeklySchedule?.days.forEach((day) => {
      const drafts = day.appointments.filter((a) => a.status === 'draft');
      if (drafts.length > 0) map[day.date] = drafts;
    });
    return map;
  }, [weeklySchedule]);
  ```
  Pattern is verbatim from `CalendarView.tsx:186-196`. Pass `draftsByDay[date] ?? []` to each `<DayHeader />`.
- **PATTERN**: Mirror the Tailwind grid layout in `ScheduleOverviewEnhanced.tsx`. Use CSS Grid `grid-cols-[200px_repeat(7,1fr)]` (Tailwind 4 supports this arbitrary value JIT-extracted at build time because the value is static).
- **IMPORTS**: `useWeeklySchedule`, `useStaff`, `useWeeklyUtilization`, `useWeeklyCapacity`, `useUpdateAppointment` (for drop handler), all subcomponents.
- **GOTCHA**: 
  - Empty `[tech × day]` cells must be clickable to open create-appointment with `staff_id` + `scheduled_date` pre-filled (preserves existing `dateClick` behavior).
  - **Both** `onDragOver` (with `e.preventDefault()`) AND `onDrop` are required on every cell; without `dragOver`, drops silently no-op.
  - When iterating `weeklySchedule.days`, group appointments by `staff_id` — the response is `{date, appointments[]}` not `{staffId, days[]}`. Build the `[techId][date]` lookup once per render.
  - Filter cancelled at the grouping step, not at render: `if (apt.status !== 'cancelled')`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm test -- src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx`

### Task 19: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx`

- **IMPLEMENT**:
  - Renders correct number of tech rows from mock `useStaff` data.
  - Sparkline renders one rect per appointment in a cell.
  - Capacity footer cell shows `bg-orange-500` when `capacityPct >= 85`, `bg-teal-500` otherwise.
  - Day-header click invokes `onDrillIn` callback with the correct date.
  - Empty cell click invokes `onEmptyCellClick` with `staffId` and `date`.
  - Card drop fires reassign/reschedule mutation.
- **PATTERN**: Mirror `frontend/src/features/schedule/components/AIScheduleView.test.tsx` for QueryClient + provider setup.
- **IMPORTS**: RTL, vitest, `QueryClient`, `QueryClientProvider`.
- **GOTCHA**: Mock `useWeeklySchedule`, `useStaff`, `useWeeklyUtilization`, `useWeeklyCapacity` via `vi.mock` — see existing test files for the exact mock shape.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/WeekMode.test.tsx`

### Task 20: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/NowLine.tsx`

- **IMPLEMENT**: A vertical line absolutely positioned at `left: minutesToPercent(currentMinutes)%`. Updates every 60s via `useEffect` + `setInterval`. Renders only when the day mode's date is today.
- **PATTERN**: `useEffect(() => { const id = setInterval(() => setNow(new Date()), 60_000); return () => clearInterval(id); }, []);`
- **IMPORTS**: React.
- **GOTCHA**: Don't render at all if outside `[DAY_START_MIN, DAY_END_MIN]`.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 21: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx`

- **IMPLEMENT**: One date, all techs. CSS Grid:
  ```tsx
  <div className="grid grid-cols-[200px_1fr] grid-rows-[auto_repeat(var(--N),auto)]">
  ```
  
  Cells:
  - `[0,0]`: empty.
  - `[0,1]`: hour-axis ruler — relative-positioned container with absolute-positioned tick labels at `left: ${minutesToPercent(h*60)}%` for `h in [6,7,8,...,20]`. Show major ticks (h%2==0) with text "6am", minor ticks as 1px gray lines.
  - `[i,0]`: `<TechHeader staff={...} utilizationPct={...} />`.
  - `[i,1]`: tech-row strip — `position: relative`, `height = Math.max(80, lanes.length * 40)` px. Each appointment is an absolute-positioned `<AppointmentCard variant='absolute' style={{ left: \`${pct}%\`, width: \`${w}%\`, top: \`${lane*38}px\`, height: '36px' }} />`. Use `assignLanes` PER-TECH (not global) to compute lane.
  - `<NowLine />` rendered as a `position: absolute; left: ${minutesToPercent(currentMinutes)}%; top: 0; bottom: 0;` line, overlaid on the entire `[*,1]` column when `date === today`.
  
  Component signature:
  ```tsx
  interface DayModeProps {
    date: Date;
    selectedDate: Date | null;
    onAppointmentClick: (id: string) => void;
    onEmptyCellClick: (staffId: string, date: string) => void;
  }
  ```
  
  Drag-drop: each tech-row strip is a drop zone. **Use `handleRowDrop` from "Patterns to Follow → drag-and-drop reference impl"** — full copy-paste implementation including X→time conversion, 15-min snap, duration preservation, past-8pm rejection, 409 conflict handling, reassign-and-reschedule combined PATCH.
- **PATTERN**: See `assignLanes` invariant in Task 7. Each tech's appointments get their own lane assignment (independent per-tech, not global).
- **IMPORTS**:
  ```tsx
  import { useDailySchedule } from '../../hooks/useAppointments';
  import { useStaff } from '@/features/staff/hooks/useStaff';
  import { useUpdateAppointment } from '../../hooks/useAppointmentMutations';
  import { useUtilizationReport } from '../../hooks/useAIScheduling';
  import { AppointmentCard } from './AppointmentCard';
  import { TechHeader } from './TechHeader';
  import { NowLine } from './NowLine';
  import {
    DAY_START_MIN, DAY_END_MIN, DAY_SPAN_MIN,
    timeToMinutes, minutesToPercent, assignLanes,
  } from './utils';
  import { toast } from 'sonner';
  import type { Appointment } from '../../types';
  import type { DragPayload } from './types';
  ```
- **GOTCHA**:
  - Per-tech lane assignment, not global. Reset `assignLanes` for each tech's appointments.
  - When the new `start_min` puts `end_min > DAY_END_MIN` (e.g., dropping a 3hr job at 6pm), `handleRowDrop` already toasts and returns early.
  - The drop handler PATCH always sends `staff_id` (no-op if same) — that's intentional and avoids a branch in the request payload.
  - Filter `appointment.status !== 'cancelled'` before grouping.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm test -- src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx`

### Task 22: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx`

- **IMPLEMENT**:
  - Renders correct hour ticks (6am–8pm).
  - Cards positioned with `left/width/top` matching their times and lane.
  - Two overlapping appointments end up in different lanes.
  - Drag-drop within same row → reschedule mutation called with new times only.
  - Drag-drop to different row → reassign + reschedule mutation called.
  - Drop position past 8pm → toast.error and no mutation.
  - NowLine renders only on today's date.
- **PATTERN**: See Task 19.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/DayMode.test.tsx`

### Task 23: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.tsx`

- **IMPLEMENT**: Simple density grid. CSS Grid:
  ```
  grid-template-columns: 200px repeat({daysInMonth}, 1fr);
  ```
  Each `[tech × day]` cell shows the appointment count as a centered text (`text-sm font-semibold`). Background opacity scales with count: `0 → bg-slate-50`, `1-2 → bg-emerald-100`, `3-5 → bg-emerald-300`, `6+ → bg-emerald-500 text-white`. Click on a cell drills into Day mode for that date.
- **PATTERN**: Density-only month views are the simplest possible — no cards, no time, just counts. See `react-calendar-heatmap` for inspiration if needed (don't install it; just implement).
- **IMPORTS**: Standard.
- **GOTCHA**: Use `eachDayOfInterval` from `date-fns` to generate the day list for the visible month.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/MonthMode.test.tsx`

### Task 24: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.test.tsx`

- **IMPLEMENT**: Render check, density-color-by-count check, drill-in-on-click check.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/MonthMode.test.tsx`

### Task 25: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/ViewModeToggle.tsx`

- **IMPLEMENT**: Three-button segmented toggle (Day / Week / Month). Visual style matches the existing `<Tabs>` in `SchedulePage.tsx:20-26`. Controlled via `mode` and `onModeChange` props.
- **PATTERN**: Use `@radix-ui/react-toggle-group` or just three styled `<button>`s (matches the existing design language better — the codebase doesn't use ToggleGroup elsewhere).
- **IMPORTS**: lucide icons `Clock` (day), `CalendarDays` (week), `Calendar` (month).
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 26: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/index.tsx`

- **IMPLEMENT**: Top-level orchestrator.
  - Owns `mode: ViewMode` state (default `'week'`).
  - Owns the visible date range (computed from `mode` + `currentDate`):
    - day → `[currentDate, currentDate]`
    - week → `[startOfWeek(currentDate), addDays(start, 6)]`
    - month → first/last of month
  - Renders `<ViewModeToggle />` + prev/next/today nav buttons + the active mode component.
  - Passes `onAppointmentClick`, `onEmptyCellClick`, `onDayHeaderClick` props through.
  - `onDayHeaderClick(date)` → setMode('day') + setCurrentDate(date).
  - Props mirror the original `<CalendarView />` so `SchedulePage.tsx` swap is one-line.
  
  Component signature:
  ```tsx
  interface ResourceTimelineViewProps {
    onDateClick?: (staffId: string, date: Date) => void;
    onEventClick?: (appointmentId: string) => void;
    onWeekChange?: (weekStart: Date) => void;
    selectedDate?: Date | null;
    onCustomerClick?: (appointmentId: string) => void;
  }
  export function ResourceTimelineView(props: ResourceTimelineViewProps): JSX.Element;
  ```
- **PATTERN**: Match the prop shape of `CalendarView.tsx:29-38` so the parent's call site changes minimally.
- **IMPORTS**: All mode components, `ViewModeToggle`, `useStaff`, `useWeeklySchedule`, `useDailySchedule` (for day mode).
- **GOTCHA**: `onDateClick` in the original `CalendarView` was called with just `Date`; we need to extend to `(staffId, date)` for empty-cell-click in week mode. Verify the `SchedulePage.tsx` consumer (`onDateClick={(d) => { setCreateDialogDate(d); setShowCreateDialog(true); }}`) still works — adapt the shim there to also pre-fill `staff_id` in the create dialog.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx tsc -p tsconfig.app.json --noEmit`

### Task 27: CREATE `frontend/src/features/schedule/components/ResourceTimelineView/ResourceTimelineView.test.tsx`

- **IMPLEMENT**:
  - Default mode is 'week'.
  - Mode toggle changes rendered child mode.
  - Day-header click switches to day mode for that date.
  - Prev/next buttons shift the date range correctly per mode.
  - 'Today' button resets to current date.
- **PATTERN**: See Task 19 for QueryClient + mock-hook setup.
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npx vitest run src/features/schedule/components/ResourceTimelineView/ResourceTimelineView.test.tsx`

### Task 28: UPDATE `frontend/src/features/schedule/components/SchedulePage.tsx`

- **IMPLEMENT**:
  - Replace `import { CalendarView } from './CalendarView';` with `import { ResourceTimelineView } from './ResourceTimelineView';`.
  - Replace the `<CalendarView ... />` JSX with `<ResourceTimelineView ... />`.
  - Add `createDialogStaffId` state alongside the existing `createDialogDate`. Pass it to `AppointmentForm` as `initialStaffId`.
  - Update the `onDateClick` shim from `(date: Date) => void` to `(staffId: string | null, date: Date) => void`. When `staffId` is provided (week-mode empty cell click), pre-fill both. When called from list/day-header (`staffId` null), pre-fill date only.
  - Keep all queues, dialogs, list-mode toggle, deep-link logic, and `RecentlyClearedSection` exactly as they are.
  - Pass `selectedDate` through unchanged (clear-day red ring still works in `AppointmentCard`).
  - **Mobile branch unchanged**: when `isMobile`, continue rendering `<AppointmentList />` instead of `<ResourceTimelineView />` (resource grid is desktop-only v1).
- **PATTERN**: Single-line import swap + JSX swap + one new state field + one prop signature widening.
- **IMPORTS**: As above.
- **GOTCHA — `AppointmentForm` props verified**: `AppointmentFormProps` at `frontend/src/features/schedule/components/AppointmentForm.tsx:86-104` already exposes `initialDate?: Date`, `initialJobId?: string`, `initialStaffId?: string`. They flow into `defaultValues` at line 130–135. **No changes needed to `AppointmentForm`** — just pass the new props from `SchedulePage`.
- **GOTCHA — `selectedDate` highlight**: The red ring + animate-pulse for cards on the cleared-day flow is preserved by passing `selectedDate` to `ResourceTimelineView` → `WeekMode`/`DayMode` → `AppointmentCard isOnSelectedDate={appt.scheduled_date === format(selectedDate, 'yyyy-MM-dd')}`.
- **VALIDATE**: 
  1. `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run typecheck`
  2. `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run dev` — open `http://localhost:5173/schedule`, verify renders without runtime error, all queues (`RescheduleRequestsQueue`, `NoReplyReviewQueue`, `InboxQueue`) visible above the new view, `RecentlyClearedSection` below it.

### Task 29: VERIFY no remaining `CalendarView` importers

- **IMPLEMENT**: Run grep to confirm `SchedulePage.tsx` is the only consumer:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && \
    grep -rn "from.*['\"].*CalendarView" src/ --include="*.ts" --include="*.tsx"
  ```
  Expected: only `SchedulePage.tsx` (already updated in Task 28) and the test files we're about to delete.
- **GOTCHA**: If a test imports `formatCalendarEventLabel` from `CalendarView.tsx`, the function is FullCalendar-specific (`{Staff} - {Job}` format string) and not reusable in the new view. Don't port it. Just delete the test (the new card has its own format via `formatTimeRange` + `getJobTypeColor`).
- **VALIDATE**: grep returns no surprise importers.

### Task 30: DELETE `CalendarView.{tsx,css,test.ts,test.tsx}`

- **IMPLEMENT**:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && \
    rm src/features/schedule/components/CalendarView.tsx \
       src/features/schedule/components/CalendarView.css \
       src/features/schedule/components/CalendarView.test.ts \
       src/features/schedule/components/CalendarView.test.tsx
  ```
  (Some of those test files may not exist; `rm -f` to be safe.)
- **GOTCHA**: `CalendarView.tsx` carries `@ts-nocheck` (line 1). It is **NOT** in `tsconfig.app.json`'s `exclude` list — verified — so no tsconfig change is needed. (The exclude list in `tsconfig.app.json` only catches `*.test.{ts,tsx}` and `src/test/**` — see `frontend/tsconfig.app.json:35-41`.)
- **VALIDATE**: `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run typecheck && npm test`

### Task 31: UPDATE E2E test selectors that reference `fc-event-{id}`

- **IMPLEMENT**: Search for the legacy FullCalendar selector and replace with the new card test id:
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform && \
    grep -rln "fc-event-" e2e/ scripts/ frontend/src/ 2>/dev/null
  ```
  Replace every `fc-event-${id}` with `appt-card-${id}`. Known callers per DEVLOG 2026-04-29 Bug 6: `e2e/payment-links-flow.sh`. There may be others.
- **PATTERN**: These are shell scripts — use `sed -i ''` (BSD/macOS):
  ```bash
  for f in $(grep -rl "fc-event-" e2e/ scripts/); do
    sed -i '' 's/fc-event-/appt-card-/g' "$f"
  done
  ```
- **GOTCHA**: Don't sed-replace inside the deleted `CalendarView.tsx` (already gone); verify by listing files first. Don't replace inside `bughunt/2026-04-29-pre-existing-tsc-errors.md` — it's historical context.
- **VALIDATE**: `grep -rn "fc-event-" e2e/ scripts/ frontend/src/` returns no hits.

### Task 32: UPDATE `bughunt/2026-04-29-pre-existing-tsc-errors.md`

- **IMPLEMENT**: If the doc lists `CalendarView.tsx` as a pre-existing-error file, strike through the entry and add a one-line note: "Removed YYYY-MM-DD as part of resource-timeline-view migration (`@ts-nocheck` no longer needed because the file is deleted)." If the doc does not list it, skip this task — the doc is for files still in `tsconfig.app.json`'s exclude list, which `CalendarView.tsx` was never in.
- **VALIDATE**: visual check.

### Task 33: WRITE DEVLOG entry

- **IMPLEMENT**: Append a new entry to `DEVLOG.md` following the format used by recent entries (e.g., the `2026-04-29 19:30` entry). Sections: "What Was Accomplished", "Technical Details", "Decision Rationale", "Challenges and Solutions", "Next Steps". Highlight: replaced FullCalendar week view with hand-rolled resource-timeline; new icon vocabulary; deliberate v1 omissions (mobile, multi-day, attachment badge, opt-out/unrecognized pills); confidence-affecting trade-offs.
- **PATTERN**: Mirror the structure of `DEVLOG.md:8-52` (the `2026-04-29 19:30 BUGFIX: AI scheduling spec validation` entry).
- **VALIDATE**: visual review of the appended entry.

---

## TESTING STRATEGY

### Unit Tests

**Backend:**
- `test_appointment_response_priority_level.py` — verify `_enrich_appointment_response` populates `priority_level` from joined Job; defaults to `None` if no job loaded.

**Frontend (Vitest):**
- `utils.test.ts` — pure helpers: `timeToMinutes`, `minutesToPercent`, `formatTimeRange`, `getInitials`. Property-based for `assignLanes` (no overlap on same lane invariant; minimum-lanes coverage; deterministic for sorted inputs).

### Integration Tests

**Frontend (Vitest + RTL):**
- `AppointmentCard.test.tsx` — icon-rendering matrix (16 combinations of priority/no_reply/reschedule/prepaid flags).
- `WeekMode.test.tsx` — sparkline rendering, capacity-color thresholds, drag-drop reassign+reschedule, day-header drill-in, empty-cell create.
- `DayMode.test.tsx` — lane positioning, drag-drop with X-coord-to-time conversion, NowLine presence, past-8pm rejection.
- `MonthMode.test.tsx` — density coloring, drill-in.
- `ResourceTimelineView.test.tsx` — mode-toggle, prev/next/today nav, day-header drill-in (mode switch).

**Frontend (PBT — `*.pbt.test.tsx`):**
- `assignLanes` invariants over 100 random interval sets.
- "Every appointment renders within its day cell's time bounds" — randomized appointment lists, assert position math is stable.

### Edge Cases

- 0 staff → render empty state ("No technicians available — add staff in Settings").
- 0 appointments on a day → empty cell, capacity bar shows 0%, sparkline empty.
- Appointment that starts before 6am or ends after 8pm → clamp to day bounds visually, log warning to console.
- Two appointments on same staff with `time_window_start` exactly equal → both go in same lane only if non-overlapping; otherwise two lanes.
- Appointment with `priority_level === null` (legacy data) → no star icon.
- Tech with no appointments all week → row renders with `0% utilized`, all cells empty (still drop targets).
- `useUtilizationReport` returns 404 (date pre-AI-scheduling-tables migration) → fall back to computing utilization client-side as `sum(appointment durations) / (8h * 60)`.
- Drag from week mode to a day in a different week → out of scope; suppress drop with cursor `not-allowed`.
- Concurrent edits (admin A drags while admin B already moved the same appointment) → 409 from BE → revert + toast.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Backend
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check src/grins_platform/api/v1/appointments.py src/grins_platform/schemas/appointment.py
uv run ruff format --check src/grins_platform/api/v1/appointments.py src/grins_platform/schemas/appointment.py
uv run mypy src/grins_platform/api/v1/appointments.py src/grins_platform/schemas/appointment.py

# Frontend (npm scripts per frontend/package.json — `test` = `vitest run`, `typecheck` = tsc --noEmit)
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run lint
npm run typecheck
```

### Level 2: Unit Tests

```bash
# Backend
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest src/grins_platform/tests/unit/test_appointment_response_priority_level.py -v

# Frontend — utils + components
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- src/features/schedule/components/ResourceTimelineView/
```

### Level 3: Integration Tests

```bash
# Backend — weekly endpoint still returns valid responses with new priority_level field
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest src/grins_platform/tests -k "weekly_schedule or appointment_api" -v

# Backend — three-tier markers must all pass (per code-standards.md / spec-testing-standards.md)
uv run pytest -m unit -v
uv run pytest -m functional -v
uv run pytest -m integration -v

# Frontend — full schedule slice
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- src/features/schedule/
```

### Level 3.5: Coverage Reports

```bash
# Backend coverage (target: services 90%+)
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest --cov=src/grins_platform --cov-report=term-missing src/grins_platform/tests/

# Frontend coverage (targets: components 80%+, hooks 85%+, utils 90%+)
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run test:coverage -- src/features/schedule/components/ResourceTimelineView/
```

Coverage numbers MUST be reported in the DEVLOG entry (Task 33).

### Level 3.6: agent-browser E2E Validation

Per `e2e-testing-skill.md`, `frontend-testing.md`, `spec-quality-gates.md`. Runs the full E2E script from Quality Standards §3:

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
# Start BE + FE first (Level 4 commands), then:
bash e2e/schedule-resource-timeline.sh
# Verify all screenshots produced in e2e-screenshots/schedule-timeline/
ls -la e2e-screenshots/schedule-timeline/
```

Pass criteria: zero `agent-browser console` JS errors, zero `agent-browser errors` exceptions, all 8 screenshots produced, all `wait`/`is visible` assertions succeed.

### Level 4: Manual Validation

```bash
# Start dev stack
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run alembic upgrade head  # confirm no pending migrations
uv run uvicorn grins_platform.app:app --reload --host 0.0.0.0 --port 8000 &

cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run dev
# Open http://localhost:5173/schedule
```

Manual checklist (per CLAUDE.md "test the golden path AND edge cases"):
- [ ] Week mode renders by default; matches the target screenshot's layout (techs as rows, days as columns, stacked cards, sparkline, capacity footer).
- [ ] Each tech row left-border + avatar uses the staff color from `staffColors.ts`.
- [ ] Cards display ⭐ when `priority_level > 0`, 🔔 when `needs_review_reason` set, 🔁 when an open RescheduleRequest exists, 💎 (Gem) when `service_agreement_id`.
- [ ] Sparkline tooltip on hover shows time + customer name.
- [ ] Capacity footer shows orange ≥85%, teal otherwise.
- [ ] Click day-header → drills into Day mode for that date; hover shows underline + chevron.
- [ ] Click empty `[tech × day]` cell → opens create-dialog with `staff_id` and `scheduled_date` pre-filled.
- [ ] Drag card to different tech row in same day → tech reassignment fires; toast confirms.
- [ ] Drag card to different day same tech → reschedule fires.
- [ ] Switch to Day mode → techs as rows, hour axis 6am–8pm, lane-positioned cards, NowLine if today.
- [ ] Drag card horizontally in Day mode → reschedule by minute (snapped to 15-min); past-8pm rejected with toast.
- [ ] Drag card to different tech row in Day mode → reassign + reschedule combined PATCH.
- [ ] Switch to Month mode → density grid; click cell drills into Day mode.
- [ ] `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `InboxQueue`, `ClearDayDialog`, `RestoreScheduleDialog`, list-mode toggle, deep-link `?scheduleJobId=xxx` all still function.
- [ ] No console errors. No `@ts-nocheck` in any new file.

### Level 5: Additional Validation

```bash
# Build gate (post-DEVLOG 2026-04-29 build hardening)
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run build

# Alembic head check (per .github/workflows/alembic-heads.yml)
cd /Users/kirillrakitin/Grins_irrigation_platform
bash scripts/check-alembic-heads.sh  # Should report a single head; this PR adds no migrations
```

---

## ACCEPTANCE CRITERIA

- [ ] FullCalendar week view fully removed; `ResourceTimelineView` is the only schedule renderer.
- [ ] Three modes (Day / Week / Month) toggle live without reload; each mode matches the design intent (Day = horizontal hour grid; Week = stacked + sparkline + capacity footer; Month = density).
- [ ] Card icon vocabulary works: ⭐ priority, 🔔 needs-review, 🔁 reschedule pending, 💎 prepaid; max 3 displayed.
- [ ] Drag-drop within Day mode = reschedule by time + (optional) reassign tech; within Week mode = reassign + reschedule by day only.
- [ ] Day-header click in Week mode drills into Day mode for that date; hover affordance visible.
- [ ] Empty cell click opens create-dialog with `staff_id` + `scheduled_date` prefilled.
- [ ] Capacity footer color thresholds match: orange ≥85%, teal otherwise.
- [ ] Per-tech utilization % displays in the row header.
- [ ] All existing schedule-page features unchanged: queues, deep-links, list-mode toggle, clear-day, restore.
- [ ] `priority_level` flows from BE `Job` through `_enrich_appointment_response` to the FE card.
- [ ] All validation commands (Levels 1–5) pass with zero errors.
- [ ] Frontend build succeeds with `tsc -p tsconfig.app.json --noEmit` (no `@ts-nocheck` in new files; one entry removed from the exclude list).
- [ ] Test coverage: every new file has a corresponding `.test.{ts,tsx}` with at least the documented cases.
- [ ] No new dependencies in `frontend/package.json`.
- [ ] **Backend three-tier testing complete** (per `code-standards.md`): `@pytest.mark.unit` (Task 3) + `@pytest.mark.functional` (Task 3b) + `@pytest.mark.integration` (Task 3c) all pass.
- [ ] **Coverage targets met** (per `frontend-testing.md`, `tech.md`): backend 90%+, FE components 80%+, hooks 85%+, utils 90%+.
- [ ] **data-testid attributes present on every element listed in Quality Standards §2**.
- [ ] **agent-browser E2E script `e2e/schedule-resource-timeline.sh` passes** with zero console errors and all 8 screenshots produced.
- [ ] **Loading / error / empty states tested** for `WeekMode`, `DayMode`, `MonthMode`, `ResourceTimelineView` (per Quality Standards §9).
- [ ] **Cross-feature integration tests pass** (per Quality Standards §6): queues, deep-link, clear-day red ring, list toggle, mobile fallback, modal-on-click.
- [ ] **Security checklist clean** (per Quality Standards §7): admin auth still enforced, no PII in logs/drag payloads, no new auth surface.
- [ ] **DEVLOG entry written** in the format specified in Quality Standards §11 / `devlog-rules.md`, inserted at top of `DEVLOG.md` after `## Recent Activity`.

---

## COMPLETION CHECKLIST

- [ ] All 33 tasks completed in order (plus Tasks 3a/3b/3c added in Quality Standards §8)
- [ ] Each task validation passed immediately
- [ ] All Level 1–5 validation commands pass (including Level 3.5 coverage and Level 3.6 agent-browser E2E)
- [ ] Manual checklist green
- [ ] No regressions in `RescheduleRequestsQueue`, `NoReplyReviewQueue`, `InboxQueue`, `ClearDayDialog`, `RestoreScheduleDialog`, deep-link `?scheduleJobId=`, `AppointmentList`, `AppointmentModal`, `AppointmentForm`
- [ ] `CalendarView.tsx`, `CalendarView.css`, `CalendarView.test.ts`, `CalendarView.test.tsx` deleted
- [ ] One entry removed from `frontend/tsconfig.app.json` exclude (the `CalendarView.tsx` line)
- [ ] DEVLOG entry written summarizing the migration (per Quality Standards §11)
- [ ] Quality Standards §1–11 all satisfied (logging events, data-testid map, agent-browser script, coverage targets, fixtures, integration tests, security, three-tier BE testing, FE state coverage, parallel execution, DEVLOG)

---

## NOTES

### Design decisions and trade-offs

1. **Hand-rolled vs `react-big-calendar` vs FullCalendar Premium.** FullCalendar Premium is $480/dev/yr — off-limits. `react-big-calendar` is MIT-licensed and ships a resource view, but mixing it with the existing FullCalendar plugins creates two calendar libraries in one codebase (smell). Hand-rolling with CSS Grid + Tailwind costs ~600–800 LOC across the file family but yields zero dependency churn, full design control, and reuses 100% of the existing query/mutation hooks. Worth the effort.

2. **Why techs as ROWS in Day mode (not columns).** Outlook auto-pivots to row-based "Schedule View" at ≥5 calendars; ServiceTitan defaults to row-based for SMB shops; every dedicated resource-scheduler (Float, Resource Guru, Asana Workload) is row-based. Vertical "now" line crossing all rows answers "who's free at 11am?" instantly — the admin's primary task. Trade-off accepted: ~5-min learning curve for users coming from Google Calendar's day view.

3. **Why single-click drill-in on day headers.** Google Calendar / Fantastical / FullCalendar default. Double-click is a documented anti-pattern (NN/G, Baymard). Plain highlight has no discoverability. Single-click + hover affordance (underline + chevron) is the only option that scores well on all of: discoverability, speed, accessibility, web idiom consistency. Trade-off accepted: field-service peers like ServiceTitan don't drill in — but Grin's primary workflow is calendar-like (scan-week-then-dive), not dispatcher-board-like.

4. **Card icon vocabulary capped at 3.** Visual budget on a stacked-card cell is tight; more icons compete with customer name and time. The four flags surface in this severity order: priority > no-reply > reschedule > prepaid. If all four trigger (rare), prepaid is dropped first since it's already-resolved (paid) and least admin-actionable. The ⚠ warning icon was rejected because the only data triggers (`sla_deadline`, `is_red_flag`, `has_dogs`) are either rarely populated (`sla_deadline`) or per-customer not per-appointment.

5. **Sparkline visibility in Week mode.** A 16px horizontal time bar at the top of each cell answers "where are Mike's gaps Tuesday?" without leaving Week mode. ~80 LOC, no libraries. If users find the sparkline insufficient over time, Option E (compact dual-axis with hour gutters) shares the same `minutesToPercent` math and is a non-breaking enhancement.

6. **Backend changes minimal.** Only one additive Pydantic field (`priority_level`) and one enrichment-function update. No migrations, no new endpoints. Per-day endpoints (`/schedule/utilization`, `/schedule/capacity/{date}`) are reused; week views fan out 7 queries client-side via `useQueries` (matches the existing `jobQueries` pattern in `SchedulePage.tsx:137-144`).

7. **Multi-day jobs deliberately out of scope.** The `Appointment` model has no `parent_appointment_id` / `day_index` / `total_days` fields. "New build (Day 1/4)" rendering would require a model + migration. Defer to a follow-up; v1 treats every appointment as single-day, regardless of the underlying job's duration. If a job spans 4 days, that's 4 separate appointments today.

8. **Mobile deferred.** Desktop-only v1. The existing mobile `listWeek` fallback in `SchedulePage.tsx` (`isMobile` branch) is preserved — when `isMobile` is true, render the existing `<AppointmentList />` instead of `<ResourceTimelineView />`. A horizontal-scroll mobile resource grid is a v2 design problem.

### Things to watch during implementation

- The `_enrich_appointment_response` function is shared by `/appointments`, `/appointments/daily/{date}`, `/appointments/staff/{id}/daily/{date}`, `/appointments/weekly`. Verify each query plan preloads `Appointment.job` (`selectinload(Appointment.job)`) — if not, `priority_level` will silently come back `None` even when set.
- Tailwind 4 cannot statically extract `style={{ left: \`${x}%\` }}` — use inline `style` attributes for all dynamic positioning. Reserve Tailwind classes for static layout only.
- `AppointmentForm.tsx` may not currently accept a pre-filled `staff_id` initial value. Verify before Task 28; if missing, add the prop in a small task before Task 28.
- The `useReassignAppointment` mutation returns 409 when overlapping — surface a specific toast ("Conflict — Sarah already has an appointment at that time") rather than a generic error.
- The pre-existing-errors list (`bughunt/2026-04-29-pre-existing-tsc-errors.md`) currently excludes `CalendarView.tsx`; once deleted, remove that entry from the file AND from `tsconfig.app.json`'s `exclude` array. New files in `ResourceTimelineView/` must NOT be added to the excludes — they must pass strict TS.

### Confidence Score

**10/10** for one-pass implementation, after the v2 hardening pass. The plan now includes:

1. **Pre-flight checklist** — six grep commands the implementer runs first to verify every assumption (priority_level field name, AppointmentForm prop names, selectinload preload status, missing tooltip dep, tsconfig exclude state, single Alembic head). If any fails, the plan calls out the exact file/line to inspect.
2. **Visual Parity Inventory** — every visual cue in the current `CalendarView.tsx` / `CalendarView.css` is enumerated with the `file:line` source and the explicit "port / supersede / drop" decision. No subtle regression can ship.
3. **Full drag-drop reference impl** — copy-paste handlers for `handleDragStart`, `handleRowDrop` (Day mode), `handleCellDrop` (Week mode), `handleDragOver` — including the exact X→time math, 15-min snap, duration preservation, past-8pm rejection, 409 conflict toast, and the easy-to-miss `dragOver preventDefault` requirement.
4. **Component signatures** for every new file — props, types, exports — so the implementer doesn't have to derive them from prose.
5. **Verified facts** for the two highest-risk unknowns (AppointmentForm props ✅ already exist, selectinload preload ✅ already in place for weekly path) and explicit "acceptable for v1" callouts for the unverified ones (daily/list paths' preload status).
6. **Corrected Tasks 31/32** — the original plan misread the tsconfig exclude list; the new tasks rename the `fc-event-{id}` E2E selectors and update the bughunt doc only if applicable.
7. **Native SVG `<title>` for sparkline tooltips** — replaces the original Radix Tooltip plan after verifying that dep is not installed.
8. **Test commands match `frontend/package.json` scripts** — `npm test`, `npm run typecheck`, `npm run lint` instead of `npx`-prefixed forms.

Remaining residual risk (would NOT lower from 10/10):
- A future product decision to extend the icon set could invalidate the "max 3 icons" cap. Not an implementation risk, a design-iteration risk.
- The `customerCity` field is not currently in `AppointmentResponse`; v1 ships without city on the card. If product wants the city visible in v1, extend `_enrich_appointment_response` to join `Property` — call this out in the DEVLOG follow-ups.
