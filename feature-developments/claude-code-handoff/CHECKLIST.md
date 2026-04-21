# CHECKLIST — Pick Jobs to Schedule

Walk this top to bottom as you build. Tick each box when done.

## Routing
- [ ] Route `/schedule/pick-jobs` added to router config
- [ ] Route is guarded to Admin | Manager (matches existing `/schedule` guards)
- [ ] "Pick jobs to schedule" button added to `/schedule` page header, top-right
- [ ] Empty-state CTA on day cells links to `/schedule/pick-jobs?date=YYYY-MM-DD`
- [ ] `?date` and `?staff` query params prefill the tray (read once on mount)

## Layout
- [ ] Page lives inside the existing `<Layout>` (sidebar + header)
- [ ] Grid: `grid-cols-[240px_1fr] grid-rows-[auto_1fr_auto]` with `col-span-2` header + tray
- [ ] Facet rail: `sticky top-0`, independent scroll
- [ ] Table header: `sticky top-0` inside scroll container
- [ ] Tray: `sticky bottom-0`, always rendered, never conditionally hidden
- [ ] `md`: facet rail collapses to a Sheet triggered by a "Filters" button
- [ ] `sm`: tray fields stack 2×2, Assign goes full width

## Facet rail
- [ ] Groups rendered: City, Tags, Job type, Priority, Requested week
- [ ] Each group: fieldset + legend + labeled checkbox rows
- [ ] Counts use the **relaxed-count** rule (count of matches if *this* facet were removed)
- [ ] Per-group "Clear" micro-link appears only when that group has selections
- [ ] Top-level "Clear all filters" link appears only when any facet is active
- [ ] Values with 0 matches are dimmed (`text-slate-400`) but still clickable
- [ ] Facet state does NOT clear on search change
- [ ] Clearing facets does NOT clear selection

## Search
- [ ] Input with `Search` lucide icon, left-inset
- [ ] Placeholder matches spec: "Search customer, address, phone, job type…"
- [ ] 150ms debounce before applying
- [ ] `/` from page focuses search (if target isn't already an input)
- [ ] `Esc` while focused clears the query

## Table
- [ ] Columns in order: checkbox, Customer (+ address sub-line), Job type, Tags, City, Requested, Priority, Duration, Equipment
- [ ] Header checkbox is tri-state (all / some / none of visible rows)
- [ ] Clicking a row anywhere (except nested interactives) toggles selection
- [ ] Selected row uses `bg-teal-50`
- [ ] Sort: Customer, City, Requested, Priority, Duration (3-state: asc → desc → clear)
- [ ] Default sort: `priority desc, requested_week asc`
- [ ] Sort glyph (▲ / ▼) rendered on active column
- [ ] `aria-sort` on header buttons
- [ ] Inline notes row rendered for jobs with non-empty `notes` (amber band, italic, sticky-note icon)
- [ ] Empty state: "All jobs are scheduled" (no filters) vs "No jobs match these filters" (filters active) + Clear button
- [ ] Loading: `LoadingSpinner` centered in table region; facets + tray visible but disabled

## Scheduling tray
- [ ] Always rendered (idle + active states), never conditionally hidden
- [ ] Idle header: "No jobs selected yet — pick some above" in `text-slate-500`
- [ ] Active header: "Schedule **N** jobs" with `aria-live="polite"` + "Clear selection" link
- [ ] "Hidden selections" note inline when some selected jobs are not in the current filtered view
- [ ] Date field uses popover + `react-day-picker` (match existing `AppointmentForm`)
- [ ] Staff field: shadcn `<Select>` populated from `useStaff({ is_active: true })`
- [ ] Start time: `<Input type="time">`, default `08:00`
- [ ] Duration: number stepper, default `60`, `min={15} step={15}`
- [ ] Fields row at `lg`+; 2×2 at `md` and below
- [ ] Per-job time adjustments toggle hidden when selection is empty
- [ ] Per-job table, scrollable, `max-h-[150px]`
- [ ] Edited per-job time promotes to override; other jobs re-cascade from last override's end
- [ ] Deselecting a job deletes its override
- [ ] Assign disabled when: no selection / no staff / mutation pending / any override has end ≤ start
- [ ] Helper text under Assign explains what's missing (one line max)
- [ ] Assign label: "Assign N Job${plural}"; "Assigning…" while pending

## Mutation flow
- [ ] Uses `useCreateAppointment()` from existing hooks
- [ ] Calls one `mutateAsync` per selected job, **sequentially** (await inside loop)
- [ ] Tracks success / failure counts
- [ ] On ≥1 success: `toast.success('Assigned N jobs to schedule')`
- [ ] On ≥1 failure: `toast.error('Failed to assign M jobs')`
- [ ] On ≥1 success: navigate to `/schedule?date=<assignDate>`
- [ ] Clears `selectedJobIds` and `perJobTimes` on completion
- [ ] Verifies TanStack Query invalidations cover: `jobs ready-to-schedule`, `appointments daily`, `appointments weekly`, `dashboard today-schedule` (add missing ones)

## Leave-without-saving guard
- [ ] Browser back / sidebar nav with `selectedJobIds.size > 0` triggers `<AlertDialog>`
- [ ] Dialog text: "You have N selected jobs that haven't been scheduled. Leave anyway?"
- [ ] Guard is suppressed during internal `handleBulkAssign` navigation (ref flag)

## Styling
- [ ] All colors via CSS variables (`--primary`, `--background`, etc.) — no hex literals
- [ ] Radius: `rounded-lg` controls, `rounded-xl` containers
- [ ] Tray shadow: `shadow-[0_-4px_12px_rgba(0,0,0,0.04)]`
- [ ] Tag pills use the `TAG_COLORS` map (see SPEC §7.3), shadcn `<Badge variant="outline">`
- [ ] Priority: filled amber star for High, em-dash for Normal
- [ ] Typography: `text-sm` default, `text-xs` pills/labels, `text-base font-semibold` tray header
- [ ] No gradients, no custom font stack (use the `--font-sans` Inter token)

## Accessibility
- [ ] Landmarks: `<main>`, `<aside>`, `<footer>` (or `<section>`) used correctly
- [ ] `<fieldset>` + `<legend>` in facet groups
- [ ] `<label>` wraps each checkbox
- [ ] Select-all has `aria-label="Select all visible jobs"`
- [ ] Sort headers: `<button>` + `aria-sort`
- [ ] Tray: `<section aria-label="Scheduling assignment">` + live region on header
- [ ] Keyboard: `/` focuses search, `Esc` clears, `Cmd/Ctrl+Enter` submits Assign
- [ ] Tab order matches SPEC §9

## Test IDs
- [ ] All IDs listed in SPEC §10 are present on their intended elements
- [ ] Existing `data-testid` conventions preserved (kebab-case, scoped)

## Tests (target coverage)
- [ ] Renders empty state with zero jobs
- [ ] Renders rows with many jobs
- [ ] Row click toggles selection
- [ ] Facet click filters rows, preserves selection
- [ ] Select-all respects visible rows only
- [ ] Assign disabled without staff
- [ ] Assign calls `createAppointment` once per selected job with correct params
- [ ] Success toast + navigation on Assign
- [ ] Search debounce + filter
- [ ] Per-job override persists across unrelated toggles
- [ ] URL `?date=...&staff=...` prefill
- [ ] Unsaved-changes guard on navigate-away

## Deprecation
- [ ] `JobPickerPopup.tsx` annotated with `@deprecated Use /schedule/pick-jobs`
- [ ] All `<JobPickerPopup>` callsites changed to `navigate('/schedule/pick-jobs')`
- [ ] Follow-up ticket filed to delete `JobPickerPopup.tsx` next release

## Deviations log
- [ ] Any deviation from SPEC is marked with `// DEVIATION: <reason>` at the call site
- [ ] `DEVIATIONS.md` in this folder lists every deviation with a one-liner reason
