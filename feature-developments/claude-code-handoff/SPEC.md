# SPEC — `/schedule/pick-jobs`

**Feature:** Pick Jobs to Schedule (persistent tray variant, a.k.a. Combo 3)
**Replaces:** `features/schedule/components/JobPickerPopup.tsx`
**Target path:** `frontend/src/features/schedule/pages/PickJobsPage.tsx`
**Route:** `/schedule/pick-jobs`
**Access:** Admin, Manager (same as existing schedule feature)

---

## 1. Goal & Rationale

The existing `JobPickerPopup` is a modal dialog that presents the schedule-assignment controls (date / staff / time / duration) **only after** a user has ticked at least one job. Users consistently want to **set the date and staff first**, then pick jobs against that context. Hiding the tray until selection inverts the natural flow.

This page fixes that by:

1. Promoting the picker to a **full page** (not a modal) — larger table, clearer facets, comfortable on small screens.
2. Making the scheduling tray **persistent** — always pinned to the viewport bottom, always visible, visually foregrounded.
3. Adding a **facet rail** on the left for cascading filters (city, tags, job type, priority, requested week). Replaces the cramped filter row at the top of the existing popup.

Everything else (data source, mutation, bulk-assign logic, per-job time overrides) is carried over from `JobPickerPopup`.

---

## 2. Routing

Add to the schedule feature's routes (in `core/router/` or wherever `/schedule` routes are declared today):

```tsx
// core/router/routes.tsx (or similar)
{
  path: '/schedule/pick-jobs',
  element: <PickJobsPage />,
  // role guard: Admin | Manager (follow existing /schedule route guards)
}
```

### Entry points

- **Primary:** add a "Pick jobs to schedule" button on `/schedule` that calls `navigate('/schedule/pick-jobs')`. Placement: top-right of the schedule header, next to the existing "Generate schedule" button.
- **Secondary:** from the empty state of a day on the calendar ("No jobs scheduled — [Pick jobs]").
- **Deep-link params** (optional but recommended):
  - `?date=YYYY-MM-DD` — prefill the tray's date field
  - `?staff=<uuid>` — prefill the tray's staff field
  - These map to the same `defaultDate` / `defaultStaffId` props `JobPickerPopup` accepts today.

### Back-navigation

- After a successful assignment, toast + `navigate('/schedule?date=<assignedDate>')` — drop the user on the day they just populated.
- "Cancel" button in the tray → `navigate(-1)`.
- Browser back is always safe; no unsaved-changes blocker unless there are pending per-job time overrides AND selection is non-empty (see §6.6).

---

## 3. Layout

### 3.1 Page shell

The page lives inside the app's existing `<Layout>` (sidebar + header). Within the content area, the page itself is a **3-region CSS grid**:

```
┌──────────────────────────────────────────────────────────────┐
│ Page header (title + subtitle + "← Back to schedule")        │ auto
├─────────────┬────────────────────────────────────────────────┤
│             │                                                │
│  Facet      │                   Job table                    │
│  rail       │                                                │
│             │                                                │
│             │                                                │
│  (sticky)   │                   (scrolls)                    │ 1fr
│             │                                                │
├─────────────┴────────────────────────────────────────────────┤
│                 Scheduling tray (sticky bottom)              │ auto
└──────────────────────────────────────────────────────────────┘
```

**Grid definition** (Tailwind v4):

```tsx
<div className="grid h-[calc(100vh-theme(spacing.16))] grid-cols-[240px_1fr] grid-rows-[auto_1fr_auto] gap-x-6">
  {/* header spans both columns */}
  <header className="col-span-2 ..."> ... </header>
  {/* facet rail */}
  <aside className="row-start-2 overflow-y-auto ..."> ... </aside>
  {/* table */}
  <main  className="row-start-2 overflow-y-auto ..."> ... </main>
  {/* tray spans both columns */}
  <footer className="col-span-2 row-start-3 ..."> ... </footer>
</div>
```

### 3.2 Responsive rules

| Breakpoint | Behavior |
|---|---|
| ≥ 1024px (`lg`) | Grid as above. Facet rail 240px wide. |
| 768–1023px (`md`) | Facet rail collapses behind a "Filters" button that opens a `<Sheet>` (shadcn/ui) from the left. Grid becomes `grid-cols-1`. |
| < 768px | As above + tray becomes a stacked card (Date / Staff / Time / Duration as 2×2 grid) with full-width Assign button. Tray still persistent (not modal). |

### 3.3 Sticky behavior

- **Facet rail:** `sticky top-0` inside the scrolling region, independent scroll if content exceeds viewport height.
- **Table header row:** `sticky top-0` inside the table's scroll container — always visible while scrolling the body.
- **Tray:** `sticky bottom-0` **of the page grid region**. Uses `bg-background` + `border-t` + `shadow-[0_-4px_12px_rgba(0,0,0,0.04)]` so it reads as a pinned surface. **Always rendered** — never conditionally hidden.

---

## 4. Component Tree

```
PickJobsPage
├── PageHeader                 (title, subtitle, back link)
├── FacetRail                  (left column)
│   ├── FacetGroup  "City"
│   ├── FacetGroup  "Tags"
│   ├── FacetGroup  "Job type"
│   ├── FacetGroup  "Priority"
│   └── FacetGroup  "Requested week"
├── JobTable                   (right column)
│   ├── JobTableToolbar        (search input, clear-filters pill-row, results count)
│   ├── JobTableHead           (sticky checkbox + column headers, sortable)
│   ├── JobTableBody           (rows, optional expanded notes row per job)
│   └── JobTableEmpty          (empty state)
└── SchedulingTray             (pinned bottom)
    ├── TrayHeader             ("Schedule N jobs" live count + "Clear selection" link)
    ├── TrayFields             (Date / Staff / Start time / Default duration)
    ├── PerJobTimeAdjustments  (collapsible accordion, rendered only when N ≥ 1)
    └── TrayActions            (assigned-to summary + Assign CTA)
```

Keep everything in `features/schedule/`:

```
features/schedule/
├── pages/
│   └── PickJobsPage.tsx         NEW
├── components/
│   ├── FacetRail.tsx            NEW
│   ├── JobTable.tsx             NEW
│   ├── SchedulingTray.tsx       NEW
│   ├── PerJobTimeAdjustments.tsx  NEW (extracted; shared with JobPickerPopup migration)
│   └── JobPickerPopup.tsx       EXISTING — mark deprecated
└── hooks/
    └── (reuse existing; no new hooks required)
```

---

## 5. State Model

All state is page-local (`useState`) unless called out. **Do not** push filters to URL params in v1 — deep linking is out of scope; `date` / `staff` query params are read once on mount only.

```ts
// inside PickJobsPage
const [search,          setSearch]          = useState('');
const [facetState,      setFacetState]      = useState<FacetState>(initialFacets);
const [selectedJobIds,  setSelectedJobIds]  = useState<Set<string>>(new Set());
const [perJobTimes,     setPerJobTimes]     = useState<Record<string, {start: string; end: string}>>({});
const [showTimeAdjust,  setShowTimeAdjust]  = useState(false);

// Tray fields
const [assignDate,      setAssignDate]      = useState<string>(defaultDateFromQuery ?? todayIso());
const [assignStaffId,   setAssignStaffId]   = useState<string>(defaultStaffFromQuery ?? '');
const [startTime,       setStartTime]       = useState<string>('08:00');
const [duration,        setDuration]        = useState<number>(60);

// Sorting
const [sortKey,  setSortKey]  = useState<'customer'|'city'|'requested_week'|'priority'|'duration'>('priority');
const [sortDir,  setSortDir]  = useState<'asc'|'desc'>('desc');
```

### 5.1 `FacetState` shape

```ts
type FacetState = {
  city:          Set<string>;    // values like "Minnetonka", "Plymouth"
  tags:          Set<string>;    // "vip", "commercial", "prepaid", "hoa", ...
  jobType:       Set<string>;    // "fall_winterization", "spring_startup", ...
  priority:      Set<'high'|'normal'>;
  requestedWeek: Set<string>;    // ISO date of Monday, e.g. "2026-04-27"
};
```

A facet is "active" when its Set is non-empty. An empty Set means **no filter on that facet** (pass-through), **not** "match nothing".

### 5.2 Selection invariants

- Selection survives facet changes — if a selected job is filtered out of view, it stays in `selectedJobIds`. A visually muted "N hidden selections" affordance in the tray header reminds the user.
- Toggling off the last facet that hid a row reveals it with its selected checkbox intact.
- `perJobTimes[jobId]` is pruned when a job is deselected (`toggleJob` deletes the key). Carry this over exactly from `JobPickerPopup.toggleJob`.

---

## 6. Interactions

### 6.1 Facet rail

- Each facet is a titled group; values are checkbox rows with live counts.
- Counts reflect **remaining matches when this facet's own filter is removed** (relaxed count). This is the standard e-commerce pattern — if the city filter has "Plymouth (3)" the 3 is the number of jobs that would match if the user toggled Plymouth on, given all other active filters. Rationale: if you show the raw filtered count, every unchecked facet would read "0" once a single filter is applied, which is useless.
- Clicking a row toggles it in the corresponding Set.
- When a facet Set has ≥ 1 value, show a "Clear" micro-link next to the group title.
- Top of the rail: a global "Clear all filters" link, visible only when any Set is non-empty. Does not clear `search`.
- Search + facets compose with AND. Values within a single facet compose with OR. Example: `city ∈ {Plymouth, Minnetonka} AND tags ⊇ {VIP} AND search matches "baxter"`.
- **No min-count rule** — show every facet value even if count = 0, but dim it (`text-slate-400`) and keep clickable (toggling just won't change the row count, and is the right escape hatch when the user wants to *see* unmatched options).

### 6.2 Table

**Columns (left → right):**

| # | Column | Width | Source | Notes |
|---|---|---|---|---|
| 1 | Checkbox | `w-10` | `selectedJobIds.has(job.id)` | Header checkbox is tri-state: all visible selected / some / none |
| 2 | Customer | `w-[220px]` | `job.customer_name` + sub-line `job.address` | Address dimmed (`text-slate-500 text-xs`) |
| 3 | Job type | `w-[180px]` | `job.job_type` | Pill-style badge; monospace-ish tag |
| 4 | Tags | `w-[160px]` | `job.tags` | Stacked pills; see §7.3 for colors |
| 5 | City | `w-[120px]` | `job.city` | |
| 6 | Requested | `w-[120px]` | "Wk of MMM D" format | Click opens a mini popover explaining request age |
| 7 | Priority | `w-[80px]` | ★ for High, — for Normal | Right-aligned |
| 8 | Duration | `w-[80px]` | `${job.estimated_duration_minutes}m` or `—` | Right-aligned |
| 9 | Equipment | `w-[140px]` | `job.requires_equipment.join(', ')` or `—` | Dimmed when empty |

**Row states:**

| State | Classes |
|---|---|
| default | `hover:bg-slate-50 cursor-pointer` |
| selected | `bg-teal-50 hover:bg-teal-50` |
| has notes (§6.2.1) | Render second row below the main row with a soft amber band |

**Click anywhere in a row (except on the equipment column or a nested interactive) toggles selection.** Checkbox also works. Keyboard: the checkbox is the focusable element; `Space` toggles. Rows themselves are not focusable to keep tab order quiet.

#### 6.2.1 Inline job notes row

If a job has `job.notes` (non-empty string), render a second `<tr>` immediately below it spanning all non-checkbox columns:

```tsx
<tr className="bg-amber-50/40 border-t border-amber-100">
  <td></td>
  <td colSpan={8} className="p-2 text-xs text-amber-900 italic">
    <StickyNote className="inline h-3 w-3 mr-1" /> {job.notes}
  </td>
</tr>
```

Rationale: gate codes, access instructions, dog-on-site warnings — the person scheduling needs to see them without clicking. Same pattern lives in the current platform in a few places.

#### 6.2.2 Sorting

- Click a column header to sort ascending; click again for descending; click a third time to clear (reverts to default `priority desc, requested_week asc`).
- Only these columns are sortable: Customer, City, Requested, Priority, Duration. Job type and Tags are not (they're categorical and already facet-filterable).
- Render a sort glyph (▲ / ▼) next to the sorted header.

#### 6.2.3 Empty state

If `filteredJobs.length === 0`:

- If **no filters active and no search**: "All jobs are scheduled. Nice work." with a `Link` back to `/schedule`.
- If **any filter active**: "No jobs match these filters." with a "Clear all filters" button.

### 6.3 Persistent scheduling tray

**Always rendered.** It has two visual states — "idle" (no selection) and "active" (≥1 selected):

| Element | Idle state | Active state |
|---|---|---|
| Tray header | "No jobs selected yet — pick some above" (muted `text-slate-500`) | "Schedule **N** jobs" (bold, teal-700) + "Clear selection" link |
| Date / Staff / Start / Duration fields | Fully enabled. User can set context first. | Same values persist. |
| "Per-job time adjustments" toggle | Hidden | Visible |
| Assign button | Disabled, label: "Assign" | Enabled (if staff is set), label: `Assign N Job${plural}` |
| Hidden-selections note | Hidden | Shown inline when `selectedJobIds.size` > visible-selected count |

#### 6.3.1 Fields (left → right, in a flex row)

| Field | Control | Default | Notes |
|---|---|---|---|
| Date | `<Input type="date">` inside a `<Popover>` with `react-day-picker` (already installed) for a richer picker | today | Matches existing `AppointmentForm` pattern |
| Staff member | shadcn `<Select>` | empty | Options from `useStaff({ is_active: true })`. Required before Assign is enabled. |
| Start time | `<Input type="time">` | `08:00` | |
| Default duration (min) | number stepper | `60` | `min={15} step={15}` — same as existing popup |

All four fields sit on one line at `lg`+; wrap to 2×2 at `md` and below.

#### 6.3.2 Per-job time adjustments

- Toggle link: "Per-job time adjustments" with a clock icon and chevron. Closed by default.
- When open, render a scrollable table (max height `150px`) with rows per selected job: Customer · Job type · Start (time input) · End (time input).
- Default times are computed sequentially from `startTime`, walking forward by each job's `estimated_duration_minutes` (falling back to `duration` if unset). Port `computeJobTimes` from `JobPickerPopup` verbatim — it's already correct.
- Editing either Start or End for a job promotes that job to an override in `perJobTimes`. Remaining jobs (still in auto-mode) re-cascade from the last override's end time.
- Deselecting a job removes its override.

#### 6.3.3 Assign action

Carry over `handleBulkAssign` from `JobPickerPopup`. Key points:

- Loop through `selectedJobIds`, call `createAppointment.mutateAsync` for each with `{ job_id, staff_id, scheduled_date, time_window_start, time_window_end }`.
- Aggregate success / failure counts.
- On any success: `toast.success('Assigned N jobs to schedule')`; on any failure: `toast.error('Failed to assign M jobs')`.
- After the loop, clear `selectedJobIds` + `perJobTimes`.
- `navigate('/schedule?date=<assignDate>')` on any success (don't navigate if 0 succeed).
- Show the button in a loading state (`createAppointment.isPending`) with label "Assigning…".

#### 6.3.4 Disabled / blocked states

Assign is disabled when ANY of:
- `selectedJobIds.size === 0`
- `assignStaffId === ''`
- `createAppointment.isPending === true`
- Any per-job time override has `end ≤ start`

Show a small helper line under the Assign button ("Pick a staff member to continue", "Selected job times overlap" — compute this defensively from `perJobTimes`). Keep the helper to one line max.

### 6.4 Search input

- Placeholder: "Search customer, address, phone, job type…"
- Debounce 150ms before applying.
- Icon: `Search` lucide, left-inset.
- Keyboard: `/` from anywhere on the page focuses search (skip if target is already an input — match GitHub's `/` shortcut). `Esc` while focused clears the query.

### 6.5 Loading state

- Initial load (`useJobsReadyToSchedule().isLoading`): show `LoadingSpinner` centered in the table region. Keep facet rail and tray visible (all disabled).
- Mutation in flight: the Assign button shows `"Assigning…"`; everything else stays interactive.

### 6.6 Leave-without-saving guard

If the user navigates away (browser back, sidebar link, etc.) while `selectedJobIds.size > 0`, show a confirm dialog: "You have N selected jobs that haven't been scheduled. Leave anyway?". Use a standard shadcn `<AlertDialog>`. This does **not** block router navigation on success (Assign → navigate is internal and intentional; suppress the guard via a ref flag during `handleBulkAssign`).

---

## 7. Styling

Follow the tokens already defined in `frontend/src/index.css`. Concrete mappings below; reference them rather than hex literals.

### 7.1 Color roles

| Role | Token | Tailwind |
|---|---|---|
| Background | `--background` (slate-50) | `bg-background` |
| Card surface | `--card` (white) | `bg-card` |
| Primary | `--primary` (teal-500) | `bg-primary text-primary-foreground` |
| Border | `--border` (slate-100) | `border-border` |
| Muted text | `--muted-foreground` | `text-muted-foreground` |

### 7.2 Component styling rules

- **Radius:** `rounded-lg` for inputs and buttons; `rounded-xl` for the tray container and facet rail card; `rounded-2xl` is reserved for big cards (not used here).
- **Borders:** `border border-border` on the tray and facet rail. On the table, use `border-separate border-spacing-0` and apply borders to the header row only; rows use top borders for inter-row separation.
- **Shadow:** tray gets `shadow-[0_-4px_12px_rgba(0,0,0,0.04)]`; nothing else on this page needs a shadow.
- **Typography:** `text-sm` is default body; `text-xs` for column labels and tag pills; `text-base font-semibold` for the tray header "Schedule N jobs"; no display fonts.
- **Padding:** table cells `p-2`; tray fields `space-y-1.5` inside each `<div>` wrapper (Label above control); tray container `px-6 py-4`.

### 7.3 Tag pill styling

Tags are the semantic labels like "VIP", "Commercial", "HOA", "Prepaid", "Needs ladder", "Dog on site", "Gated". Each gets its own color role — do **not** gradient or shadow these.

```tsx
const TAG_COLORS: Record<string, string> = {
  vip:          'bg-amber-50  text-amber-700   border-amber-200',
  commercial:   'bg-blue-50   text-blue-700    border-blue-200',
  hoa:          'bg-purple-50 text-purple-700  border-purple-200',
  prepaid:      'bg-teal-50   text-teal-700    border-teal-200',
  'needs-ladder':'bg-slate-100 text-slate-700  border-slate-300',
  'dog-on-site': 'bg-red-50   text-red-700     border-red-200',
  gated:        'bg-orange-50 text-orange-700  border-orange-200',
};
```

Usage: shadcn `<Badge variant="outline">` with the color class appended. Unknown tags fall back to slate.

### 7.4 Priority indicator

- High → filled star `<Star className="h-4 w-4 fill-amber-400 text-amber-400" />`
- Normal → em-dash `—` in `text-slate-300`

### 7.5 Tray visual spec

```
┌─ SchedulingTray ──────────────────────────────────────────────────────────┐
│                                                                           │
│  Schedule 3 jobs                                       [Clear selection]  │  ← header
│                                                                           │
│  ┌─ Date ─────┐ ┌─ Staff ──────────┐ ┌─ Start ─┐ ┌─ Duration ──┐          │  ← fields
│  │ 04/27/2026 │ │ Select staff…  ▼ │ │ 08:00 AM│ │  60  ▲▼     │          │
│  └────────────┘ └──────────────────┘ └─────────┘ └─────────────┘          │
│                                                                           │
│  ⏱ Per-job time adjustments  ▼                                           │  ← toggle
│                                                                           │
│  3 jobs selected                                    [  Assign 3 Jobs  ]  │  ← action
└───────────────────────────────────────────────────────────────────────────┘
```

Height when collapsed (`<PerJobTimeAdjustments>` closed): ~164px. When expanded: up to 164 + 180 = 344px. The page grid reserves the "auto" row — the tray can grow without pushing table content off-screen because the table's row is `1fr` and scrolls internally.

---

## 8. Data Flow

### 8.1 Sources

- **Jobs:** `useJobsReadyToSchedule()` — returns `{ data: { jobs: JobReadyToSchedule[] }, isLoading, error }`. No new query needed.
- **Staff:** `useStaff({ is_active: true })` — returns `{ data: { items: Staff[] }, isLoading }`. Filter to active only.

### 8.2 Mutation

`useCreateAppointment()` — already wraps `appointmentApi.create`. Call per-job in a sequential loop (preserves the order of times, matches current behavior). Do **not** parallelize — the backend's schedule-conflict check benefits from sequential ordering.

On success, TanStack Query invalidates the following queries (the mutation hook should already be doing this — verify):

- `['jobs', 'ready-to-schedule']`
- `['appointments', 'daily', assignDate]`
- `['appointments', 'weekly', ...]`
- `['dashboard', 'today-schedule']` (if `assignDate === today`)

If any of these aren't invalidated today, add them. The schedule calendar must refresh to show the new appointments without a manual reload.

### 8.3 URL query params

Read once on mount:

```ts
const [searchParams] = useSearchParams();
const defaultDate     = searchParams.get('date')  ?? todayIso();
const defaultStaffId  = searchParams.get('staff') ?? '';
```

Do **not** write back to the URL as the user changes filters — we don't want filter-state pollution in the URL in v1.

---

## 9. Accessibility

- The page uses `<main>`, `<aside>`, `<footer>` landmarks as shown in §3.1.
- Facet rail: each group is a `<fieldset>` with a `<legend>`; each row is a `<label>` wrapping a real `<input type="checkbox">`.
- Table: single `<table>` with `<thead>` / `<tbody>`. The select-all checkbox in the header has `aria-label="Select all visible jobs"`. Sort headers are `<button>` elements with `aria-sort="ascending" | "descending" | "none"`.
- Tray: contained in a `<section aria-label="Scheduling assignment">`. Live region: the "Schedule N jobs" text has `aria-live="polite"` so screen readers hear "Schedule 3 jobs" updating.
- Keyboard:
  - `/` focuses search (unless already in an input)
  - `Esc` in search clears
  - `Cmd/Ctrl+Enter` while any tray field has focus submits Assign (if enabled)
  - Standard Tab order: skip-to-table link → facets → search → table → tray fields → Assign

- Color contrast: verify teal-500 on white meets 4.5:1 for large text (it does at the current token). Tag pills use 200-weight borders with 700-weight text on 50-weight backgrounds — all pass.

---

## 10. Testing

Mirror the patterns in `features/schedule/components/__tests__/JobPickerPopup.test.tsx`. At minimum:

### Unit / component

1. Renders with zero jobs → shows "All jobs are scheduled" empty state.
2. Renders with jobs → shows one row per job.
3. Clicking a row toggles `selectedJobIds` and updates the tray header count.
4. Facet click filters the table; row counts update; selected rows stay selected (even if hidden).
5. Checking "Select all" with 5 visible + 2 active filters selects only the 5 visible.
6. Assign button disabled without staff selected.
7. Clicking Assign calls `createAppointment` once per selected job with correct params.
8. On successful Assign: toast fires, navigation happens to `/schedule?date=<assignDate>`.
9. Search input debounces and filters by customer name.
10. Per-job time adjustment override persists across selection toggles of *other* jobs.
11. URL `?date=2026-05-01&staff=<uuid>` prefills the tray.
12. Navigating away with unassigned selections shows the confirm dialog.

### Test IDs (add these — match existing popup conventions)

```
pick-jobs-page
facet-rail
facet-group-city | facet-group-tags | facet-group-job-type | facet-group-priority | facet-group-week
facet-value-<facet>-<value>
job-table
job-search
job-table-select-all
job-row-<job_id>
job-row-checkbox-<job_id>
scheduling-tray
tray-date | tray-staff | tray-start-time | tray-duration
tray-time-adjust-toggle
tray-time-adjust-table
tray-assign-btn
tray-clear-selection
```

---

## 11. Out of scope (v1)

These are deliberately excluded to keep the scope tight:

- Saving filter state to URL or localStorage
- Multi-day assignment (e.g. "spread across Mon–Wed")
- Conflict detection against existing staff schedules (backend does this on create; surface errors via the existing toast path)
- Route optimization / map preview in the tray (that's the AI generate flow)
- Drag-to-reorder jobs inside the per-job time adjustments table
- Keyboard shortcut overlay

Log these in the `DEVLOG.md` so the next iteration has a clear follow-up list.
