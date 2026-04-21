# Implementation Plan: Pick Jobs Scheduler

## Overview

This plan implements the full-page job picker at `/schedule/pick-jobs`, replacing the existing `JobPickerPopup` modal. The implementation is frontend-only — no backend changes needed. We copy scaffold files from `feature-developments/claude-code-handoff/src-scaffold/`, complete all TODOs, wire routing, deprecate the old popup, and validate with comprehensive tests and E2E verification.

**Language:** TypeScript (React 19 + Vite + Tailwind v4 + shadcn/ui)

## Tasks

- [x] 1. Types and data layer
  - [x] 1.1 Create `features/schedule/types/pick-jobs.ts` with all new types
    - Define `FacetState` interface with five `Set<string>` fields (city, tags, jobType, priority, requestedWeek)
    - Define `initialFacets` constant with all empty Sets
    - Define `PerJobTime` interface (`{ start: string; end: string }`)
    - Define `PerJobTimeMap` as `Record<string, PerJobTime>`
    - Define `SortKey` type (`'customer' | 'city' | 'requested_week' | 'priority' | 'duration'`)
    - Define `SortDir` type (`'asc' | 'desc'`)
    - Define `PriorityLevel` type (`'0' | '1' | '2'`) matching real numeric priority levels
    - Export `computeJobTimes` function (cascade logic: walk forward from startTime, respect per-job overrides as anchors)
    - Export `timeToMinutes` and `minutesToTime` helper functions
    - _Requirements: 4.10, 9.4, 9.5_

  - [x] 1.2 Extend `JobReadyToSchedule` type with missing fields
    - Add `address?: string`, `customer_tags?: CustomerTag[]`, `property_type?: 'residential' | 'commercial' | null`
    - Add `property_is_hoa?: boolean`, `property_is_subscription?: boolean`
    - Add `requested_week?: string`, `notes?: string`, `priority_level?: number`
    - Ensure the type is exported from `features/schedule/types/index.ts`
    - _Requirements: 4.1, 4.8, 4.9, 4.10_

- [x] 2. FacetRail component
  - [x] 2.1 Implement `features/schedule/components/FacetRail.tsx`
    - Copy scaffold from `feature-developments/claude-code-handoff/src-scaffold/components/FacetRail.tsx`
    - Implement relaxed-count computation that incorporates debounced search (the `jobs` prop is unfiltered; search must be factored into relaxed counts)
    - Render five facet groups in order: City, Tags, Job type, Priority, Requested week
    - Each group is a `<fieldset>` with `<legend>`, each value is a `<label>` wrapping a `<Checkbox>`
    - Show per-group "Clear" micro-link when group has selections
    - Show "Clear all filters" link at top when any facet is active
    - Dim values with 0 relaxed count (`text-slate-400`) but keep clickable
    - Use real customer tags (`priority`, `red_flag`, `slow_payer`, `new_customer`) for the Tags facet group
    - Use real priority levels (`'0'`, `'1'`, `'2'`) for the Priority facet group with human-readable labels (Normal, High, Urgent)
    - Add all `data-testid` attributes: `facet-rail`, `facet-group-city`, `facet-group-tags`, `facet-group-job-type`, `facet-group-priority`, `facet-group-week`, `facet-value-<facet>-<value>`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 15.2_

  - [x] 2.2 Implement responsive Sheet behavior for md breakpoint
    - At `md` (768–1023px), facet rail collapses behind a "Filters" button
    - Button opens a shadcn `<Sheet>` from the left containing the FacetRail
    - At `lg`+ (≥1024px), facet rail renders inline as a 240px column
    - _Requirements: 2.3_

- [x] 3. JobTable component
  - [x] 3.1 Implement `features/schedule/components/JobTable.tsx`
    - Copy scaffold from `feature-developments/claude-code-handoff/src-scaffold/components/JobTable.tsx`
    - Render columns in order: Checkbox, Customer (+address sub-line), Job type, Tags, City, Requested week, Priority, Duration, Equipment
    - Implement tri-state header checkbox (all visible / some / none) with `aria-label="Select all visible jobs"`
    - Implement row click toggles selection (except nested interactives)
    - Selected rows use `bg-teal-50`
    - Render inline notes row for jobs with non-empty `notes` (amber band, italic, `StickyNote` icon)
    - Use `CUSTOMER_TAG_CONFIG` and `PropertyTags` styling for tag pills (not the placeholder `TAG_COLORS`)
    - Priority column: filled amber star for `priority_level` 1 (high) and 2 (urgent), em-dash for 0 (normal)
    - Add all `data-testid` attributes: `job-table`, `job-search`, `job-table-select-all`, `job-row-<job_id>`, `job-row-checkbox-<job_id>`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.8, 4.9, 4.10, 15.3, 15.4_

  - [x] 3.2 Implement 3-state column sorting
    - Sortable columns: Customer, City, Requested week, Priority, Duration
    - First click: ascending; second click: descending; third click: revert to default sort (`priority desc, requested_week asc`)
    - Render sort glyph (▲/▼) next to active column header
    - Set `aria-sort` on header `<button>` elements (`ascending`, `descending`, `none`)
    - Implement the sort comparator in `PickJobsPage` (the `sortedJobs` useMemo)
    - _Requirements: 4.6, 4.7, 15.4_

  - [x] 3.3 Implement search toolbar
    - Search input with `Search` lucide icon inset left, placeholder "Search customer, address, phone, job type…"
    - 150ms debounce before applying filter
    - Case-insensitive match against customer_name, address, city, job_type, job_id
    - `Esc` while focused clears the query
    - Results count displayed next to search
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [x] 3.4 Implement empty states
    - No filters active + empty: "All jobs are scheduled. Nice work." with link back to `/schedule`
    - Filters active + empty: "No jobs match these filters." with "Clear all filters" button
    - _Requirements: 6.1, 6.2_

- [x] 4. SchedulingTray component
  - [x] 4.1 Implement `features/schedule/components/SchedulingTray.tsx`
    - Copy scaffold from `feature-developments/claude-code-handoff/src-scaffold/components/SchedulingTray.tsx`
    - Always rendered — never conditionally hidden
    - Idle state: "No jobs selected yet — pick some above" in muted text
    - Active state: "Schedule N jobs" with `aria-live="polite"` + "Clear selection" link
    - Show "hidden selections" note when some selected jobs are filtered out of view
    - Wrap in `<section aria-label="Scheduling assignment">`
    - Add all `data-testid` attributes: `scheduling-tray`, `tray-date`, `tray-staff`, `tray-start-time`, `tray-duration`, `tray-time-adjust-toggle`, `tray-time-adjust-table`, `tray-assign-btn`, `tray-clear-selection`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6, 15.5, 15.6_

  - [x] 4.2 Implement tray fields row
    - Four fields: Date (date input), Staff (shadcn Select from `useStaff({ is_active: true })`), Start time (time input, default 08:00), Duration (number stepper, default 60, min 15, step 15)
    - Single row at `lg`+; 2×2 grid at `md` and below; full-width Assign at `sm`
    - Fields always enabled regardless of selection state
    - _Requirements: 8.5, 8.6, 2.4_

  - [x] 4.3 Implement per-job time adjustments
    - Toggle link with clock icon and chevron, hidden when no selection
    - Scrollable table (max-h 150px) with rows per selected job: Customer, Job type, Start, End
    - Implement `computeJobTimes` cascade logic (port from `JobPickerPopup.computeJobTimes`)
    - Editing start/end promotes to override; subsequent auto-mode jobs re-cascade from last override's end
    - Deselecting a job removes its override from `perJobTimes`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 4.4 Implement assign action and disabled states
    - Assign disabled when: no selection, no staff, mutation pending, or any override has end ≤ start
    - Helper text: "Pick jobs above to continue" / "Pick a staff member to continue" / "Selected job times overlap — review per-job adjustments"
    - Assign label: "Assign N Jobs" (active) / "Assigning…" (pending) / "Assign" (idle)
    - Implement `handleBulkAssign`: sequential `mutateAsync` per job, track success/failure counts
    - On success: `toast.success`, navigate to `/schedule?date=<assignDate>`
    - On failure: `toast.error`
    - Clear `selectedJobIds` and `perJobTimes` after loop
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 5. PickJobsPage shell — wire everything together
  - [x] 5.1 Implement `features/schedule/pages/PickJobsPage.tsx`
    - Copy scaffold from `feature-developments/claude-code-handoff/src-scaffold/pages/PickJobsPage.tsx`
    - Wire FacetRail, JobTable, SchedulingTray into the 3-region CSS grid
    - Implement the filtering pipeline: search (debounced) → facets (AND between groups, OR within) → sort
    - Implement `toggleJob`, `toggleAllVisible`, `clearSelection`, `clearAllFilters`
    - Read `?date` and `?staff` query params on mount to prefill tray
    - Implement `/` keyboard shortcut to focus search (skip if target is already an input)
    - Implement `Cmd/Ctrl+Enter` keyboard shortcut to trigger Assign (if enabled)
    - Implement loading state: `LoadingSpinner` centered in table region while `useJobsReadyToSchedule` loads
    - Add `data-testid="pick-jobs-page"` on root element
    - Use proper landmark elements: `<header>`, `<aside>`, `<main>`, `<footer>`/`<section>`
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 2.1, 2.2, 5.4, 7.1, 7.2, 12.1, 12.2, 12.3, 15.1, 15.7_

  - [x] 5.2 Implement leave-without-saving guard
    - Use `useBlocker` (react-router) to intercept in-app navigation when `selectedJobIds.size > 0`
    - Show shadcn `<AlertDialog>` with message "You have N selected jobs that haven't been scheduled. Leave anyway?"
    - Confirm → allow navigation; Cancel → stay on page
    - Suppress guard during `handleBulkAssign` navigation via `suppressGuardRef`
    - Also handle `beforeunload` for browser-level navigation
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [x] 5.3 Apply styling and visual consistency
    - All colors via CSS variable tokens (`--primary`, `--background`, `--border`, `--muted-foreground`) — no hex literals
    - `rounded-lg` for inputs/buttons, `rounded-xl` for tray container and facet rail card
    - Tray shadow: `shadow-[0_-4px_12px_rgba(0,0,0,0.04)]` + `border-t border-border`
    - Typography: `text-sm` default, `text-xs` for pills/labels, `text-base font-semibold` for tray header
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [x] 6. Checkpoint — Verify components render and compile
  - Ensure TypeScript compiles with zero errors (`npx tsc --noEmit`)
  - Ensure all imports resolve correctly
  - Ensure the page renders in the dev server without runtime errors
  - Ask the user if questions arise.

- [x] 7. Routing and entry points
  - [x] 7.1 Add route `/schedule/pick-jobs` to router config
    - Add route in `core/router/` (or wherever `/schedule` routes are declared)
    - Apply existing Admin | Manager role guard (match existing `/schedule` route guards)
    - Lazy-load `PickJobsPage` component
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 7.2 Add "Pick jobs to schedule" button on `/schedule` page
    - Place button in the schedule page header, top-right area
    - Button navigates to `/schedule/pick-jobs`
    - _Requirements: 14.1_

  - [x] 7.3 Add "← Back to schedule" link in PickJobsPage header
    - Navigates back to previous page via `navigate(-1)`
    - _Requirements: 14.2_

  - [x] 7.4 Verify TanStack Query invalidations in `useCreateAppointment`
    - Confirm `onSuccess` invalidates: `['jobs-ready-to-schedule']`, `appointmentKeys.all` (daily, weekly), `['dashboard', 'today-schedule']`
    - Add any missing invalidation keys
    - _Requirements: 10.7_

- [x] 8. Deprecate JobPickerPopup
  - [x] 8.1 Annotate `JobPickerPopup.tsx` with `@deprecated` JSDoc
    - Add `@deprecated Use /schedule/pick-jobs` comment at the top of the component
    - Do NOT delete the file — leave for one release cycle
    - _Requirements: 17.1, 17.3_

  - [x] 8.2 Update all JobPickerPopup callsites
    - Search project-wide for `JobPickerPopup` references
    - Change all callsites to `navigate('/schedule/pick-jobs')` instead
    - Pass `?date=` and `?staff=` query params where the old popup received `defaultDate` / `defaultStaffId` props
    - _Requirements: 17.2_

- [x] 9. Checkpoint — Verify routing and deprecation
  - Ensure `/schedule/pick-jobs` route loads correctly
  - Ensure the "Pick jobs to schedule" button on `/schedule` navigates correctly
  - Ensure no remaining direct usages of `JobPickerPopup` (except the deprecated file itself)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Unit and component tests (Vitest + React Testing Library)
  - [x] 10.1 Write unit tests for pure logic functions in `pick-jobs.ts`
    - Test `computeJobTimes` with various job lists, start times, and overrides
    - Test `timeToMinutes` and `minutesToTime` round-trip
    - Test overlap detection logic
    - _Requirements: 18.10_

  - [x] 10.2 Write component tests for FacetRail
    - Test facet groups render with correct values
    - Test toggling a facet checkbox updates filter state
    - Test "Clear" micro-link appears when group has selections
    - Test "Clear all filters" link appears when any facet is active
    - Test dimmed styling for zero-count values
    - Test relaxed count computation accuracy
    - _Requirements: 18.4_

  - [x] 10.3 Write component tests for JobTable
    - Test renders rows with multiple jobs (columns in correct order)
    - Test row click toggles selection
    - Test tri-state header checkbox (all/some/none)
    - Test select-all respects only visible (filtered) rows
    - Test inline notes row renders for jobs with notes
    - Test tag pills use correct styling (CUSTOMER_TAG_CONFIG)
    - Test priority star (levels 1,2) vs em-dash (level 0)
    - Test sort headers cycle through 3 states
    - Test `aria-sort` attribute on sort headers
    - Test empty states (no filters vs filters active)
    - _Requirements: 18.1, 18.2, 18.3, 18.5_

  - [x] 10.4 Write component tests for SchedulingTray
    - Test tray always renders (idle and active states)
    - Test idle header text and active header text with count
    - Test hidden selections note displays correctly
    - Test assign button disabled states (no selection, no staff, pending, time overlap)
    - Test helper text for each disabled reason
    - Test per-job time adjustments toggle visibility
    - Test `aria-live="polite"` on header
    - _Requirements: 18.6_

  - [x] 10.5 Write integration tests for PickJobsPage
    - Test renders empty state with zero jobs
    - Test clicking a row toggles selection and updates tray header count
    - Test facet click filters table rows while preserving existing selections
    - Test assign button disabled without staff selected
    - Test clicking Assign calls `createAppointment` once per selected job with correct params
    - Test success toast and navigation after successful assignment
    - Test search input debounces and filters jobs correctly
    - Test per-job time overrides persist across unrelated selection toggles
    - Test URL `?date=...&staff=...` prefill tray fields
    - Test leave-without-saving guard triggers when navigating away with active selections
    - Test `/` keyboard shortcut focuses search
    - Test `Cmd/Ctrl+Enter` triggers assign
    - Test landmark elements present (`<main>`, `<aside>`, `<section>`)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10, 18.11, 18.12_

- [x] 11. Checkpoint — Verify all unit and component tests pass
  - Run `npm test` in the frontend directory
  - Ensure all new tests pass with zero failures
  - Ask the user if questions arise.

- [x] 12. Property-based tests (fast-check)
  - [x] 12.1 Write property test for facet filter contract (AND between groups, OR within group)
    - **Property 1: Facet filter contract**
    - Use `arbJob` and `arbFacetState` generators from the design
    - Assert: filtered output contains exactly jobs satisfying OR within each non-empty group AND across all groups
    - Assert: excluded jobs fail at least one non-empty facet group
    - Minimum 100 iterations
    - **Validates: Requirements 3.3, 3.8**

  - [x] 12.2 Write property test for relaxed count correctness
    - **Property 2: Relaxed count correctness**
    - For any jobs, FacetState, group G, value V: relaxed count equals jobs matching all filters except G AND matching V
    - Assert: sum of relaxed counts across all values in G ≥ total filtered count
    - Minimum 100 iterations
    - **Validates: Requirements 3.4**

  - [x] 12.3 Write property test for search filter correctness
    - **Property 3: Search filter correctness**
    - For any jobs and non-empty search query: filtered output contains exactly jobs where at least one searchable field contains the query (case-insensitive)
    - Assert: every excluded job has no matching field
    - Minimum 100 iterations
    - **Validates: Requirements 5.3**

  - [x] 12.4 Write property test for selection persistence across filter changes
    - **Property 4: Selection persistence across filter changes**
    - For any selectedJobIds and any FacetState change: selectedJobIds remains identical before and after
    - Assert: no facet operation adds to or removes from the selection set
    - Minimum 100 iterations
    - **Validates: Requirements 3.10, 12.1**

  - [x] 12.5 Write property test for select-all only affects visible rows
    - **Property 5: Select-all only affects visible rows**
    - For any visible IDs and existing selectedJobIds: toggle select-all adds/removes only visible IDs
    - Assert: IDs not in visible set remain unchanged in selectedJobIds
    - Minimum 100 iterations
    - **Validates: Requirements 4.5, 12.3**

  - [x] 12.6 Write property test for sort ordering correctness
    - **Property 6: Sort ordering correctness**
    - For any jobs, sortable column, and direction: every adjacent pair respects the sort direction
    - Assert: default sort orders by priority descending then requested_week ascending
    - Minimum 100 iterations
    - **Validates: Requirements 4.6**

  - [x] 12.7 Write property test for cascade time computation
    - **Property 7: Cascade time computation**
    - For any ordered selected jobs with positive durations, valid start time, positive default duration, and valid overrides: auto-mode jobs cascade sequentially; overridden jobs match override values; no overlapping windows; all end > start
    - Minimum 100 iterations
    - **Validates: Requirements 9.4, 9.5**

  - [x] 12.8 Write property test for override cleanup on deselect
    - **Property 8: Override cleanup on deselect**
    - For any PerJobTimeMap and deselected job ID: after deselect, the map has no entry for that ID; all other entries unchanged
    - Minimum 100 iterations
    - **Validates: Requirements 9.6**

  - [x] 12.9 Write property test for overlap detection correctness
    - **Property 9: Overlap detection correctness**
    - For any PerJobTimeMap: overlap detection returns true iff at least one entry has end ≤ start; returns false when all entries have end > start or map is empty
    - Minimum 100 iterations
    - **Validates: Requirements 11.4**

- [x] 13. Checkpoint — Verify all property-based tests pass
  - Run `npm test` in the frontend directory targeting the PBT test files
  - Ensure all 9 property tests pass with zero failures across 100+ iterations each
  - Ask the user if questions arise.

- [x] 14. Full quality gate — zero regressions
  - [x] 14.1 Run frontend tests — all must pass
    - Run `npm test` in the `frontend/` directory
    - All existing tests plus all new tests must pass with zero failures
    - _Requirements: 18.1–18.12_

  - [x] 14.2 Run frontend linting — zero violations
    - Run `npm run lint` (or equivalent ESLint/Biome command) in the `frontend/` directory
    - Zero lint violations allowed

  - [x] 14.3 Run TypeScript type checking — zero errors
    - Run `npx tsc --noEmit` in the `frontend/` directory
    - Zero type errors allowed

  - [x] 14.4 Run backend tests — all must pass (no regressions)
    - Run `uv run pytest -v` from the project root
    - All existing backend tests must pass — this is a frontend-only feature, so zero backend regressions expected

  - [x] 14.5 Run backend linting — zero violations
    - Run `uv run ruff check src/` from the project root
    - Zero violations allowed

  - [x] 14.6 Run backend type checking — zero errors
    - Run `uv run mypy src/` from the project root — zero errors
    - Run `uv run pyright src/` from the project root — zero errors

- [x] 15. Checkpoint — Full quality gate passed
  - Confirm all 6 quality checks (14.1–14.6) passed with zero errors
  - Ask the user if questions arise before proceeding to deployment.

- [x] 16. Deploy to dev environment
  - [x] 16.1 Deploy frontend to Vercel
    - Use `mcp_vercel_deploy_to_vercel` to deploy the frontend
    - Verify the deployment succeeds (check build logs if needed)
    - Confirm the deployment URL is accessible
    - Navigate to `/schedule/pick-jobs` on the deployed URL and verify it loads

- [x] 17. End-to-end testing with Vercel Agent Browser
  - [x] 17.1 Navigate to `/schedule/pick-jobs` and verify page layout
    - Open the deployed Vercel URL at `/schedule/pick-jobs`
    - Verify the 3-region layout renders: facet rail (left), job table (center), scheduling tray (bottom)
    - Verify page header with title "Pick jobs to schedule" and "← Back to schedule" link
    - Screenshot: `e2e-screenshots/pick-jobs/01-page-layout.png`
    - _Requirements: 2.1, 14.2_

  - [x] 17.2 Test facet filtering
    - Click a City facet checkbox and verify the table filters
    - Verify relaxed counts update on other facet groups
    - Click a Tags facet checkbox and verify AND composition between groups
    - Verify "Clear" micro-link appears on groups with selections
    - Verify "Clear all filters" link appears at top of rail
    - Screenshot: `e2e-screenshots/pick-jobs/02-facet-filtering.png`
    - _Requirements: 3.1, 3.3, 3.6, 3.7, 3.8_

  - [x] 17.3 Test job selection and tray updates
    - Click a job row and verify it becomes selected (teal background)
    - Verify tray header updates to "Schedule 1 job"
    - Select additional jobs and verify count updates
    - Verify "Clear selection" link appears in tray
    - Screenshot: `e2e-screenshots/pick-jobs/03-job-selection.png`
    - _Requirements: 4.2, 8.3_

  - [x] 17.4 Test search functionality
    - Type a customer name in the search input
    - Verify table filters after 150ms debounce
    - Verify results count updates
    - Press Escape and verify search clears
    - Screenshot: `e2e-screenshots/pick-jobs/04-search.png`
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [x] 17.5 Test sorting
    - Click the "Customer" column header and verify ascending sort
    - Click again and verify descending sort
    - Click a third time and verify revert to default sort
    - Verify sort glyph (▲/▼) renders on active column
    - Screenshot: `e2e-screenshots/pick-jobs/05-sorting.png`
    - _Requirements: 4.6, 4.7_

  - [x] 17.6 Test assign flow (select jobs, pick staff, assign)
    - Select 2–3 jobs by clicking rows
    - Select a staff member from the dropdown
    - Verify Assign button becomes enabled with label "Assign N Jobs"
    - Click Assign and verify success toast appears
    - Verify navigation to `/schedule?date=<assignDate>`
    - Screenshot before assign: `e2e-screenshots/pick-jobs/06-pre-assign.png`
    - Screenshot after assign: `e2e-screenshots/pick-jobs/07-post-assign.png`
    - _Requirements: 10.1, 10.2, 10.4, 11.5_

  - [x] 17.7 Test responsive behavior at different viewports
    - Set viewport to 768×1024 (tablet) — verify facet rail collapses to Sheet, "Filters" button appears
    - Open the Filters Sheet and verify facet groups render inside it
    - Set viewport to 375×812 (mobile) — verify tray fields stack 2×2, Assign is full-width
    - Set viewport back to 1440×900 (desktop) — verify full layout restores
    - Screenshot tablet: `e2e-screenshots/pick-jobs/08-responsive-tablet.png`
    - Screenshot mobile: `e2e-screenshots/pick-jobs/09-responsive-mobile.png`
    - _Requirements: 2.2, 2.3, 2.4_

  - [x] 17.8 Capture final state screenshots
    - Screenshot empty state (all jobs scheduled): `e2e-screenshots/pick-jobs/10-empty-state.png`
    - Screenshot per-job time adjustments open: `e2e-screenshots/pick-jobs/11-time-adjustments.png`
    - Screenshot with inline notes row visible: `e2e-screenshots/pick-jobs/12-inline-notes.png`
    - _Requirements: 6.1, 9.3, 4.8_

- [x] 18. Final checkpoint — Feature complete
  - Ensure all tests pass, all quality checks pass, deployment is live, and E2E tests confirm correct behavior.
  - Ask the user if questions arise.

## Notes

- This is a frontend-only feature — no backend changes required. All data comes from existing hooks (`useJobsReadyToSchedule`, `useStaff`, `useCreateAppointment`).
- Scaffold files in `feature-developments/claude-code-handoff/src-scaffold/` provide the starting point — copy and complete all TODOs.
- Real customer tags are `priority`, `red_flag`, `slow_payer`, `new_customer` (from `CUSTOMER_TAG_CONFIG`), not the placeholder `TAG_COLORS` in the scaffold.
- Real priority levels are numeric: `0` (normal), `1` (high), `2` (urgent) — not `'high'`/`'normal'`.
- The `JobPickerPopup.tsx` file is deprecated but NOT deleted — leave for one release cycle.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation at key milestones.
- Property tests validate the 9 universal correctness properties from the design document.
- E2E testing (Phase 9) uses Vercel Agent Browser and runs only after successful deployment.
