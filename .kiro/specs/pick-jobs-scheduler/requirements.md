# Requirements Document

## Introduction

The Pick Jobs Scheduler is a full-page job picker at `/schedule/pick-jobs` that replaces the existing dialog-based `JobPickerPopup` in the Grin's Irrigation Platform. The current modal dialog presents schedule-assignment controls (date, staff, time, duration) only after a user selects at least one job, inverting the natural workflow. Users want to set the date and staff first, then pick jobs against that context.

This feature introduces three key changes:
1. A **full page** (not modal) with a larger table, clearer facets, and comfortable small-screen support
2. A **persistent scheduling tray** always pinned to the viewport bottom, always visible and visually foregrounded
3. A **facet rail** on the left for cascading filters (city, tags, job type, priority, requested week), replacing the cramped filter row in the existing popup

The page reuses existing data hooks (`useJobsReadyToSchedule`, `useStaff`, `useCreateAppointment`) and follows the platform's established React 19 + TypeScript + Tailwind v4 + shadcn/ui stack.

## Glossary

- **Pick_Jobs_Page**: The full-page React component at `/schedule/pick-jobs` that serves as the shell for the job picker, containing the page header, facet rail, job table, and scheduling tray in a CSS grid layout.
- **Facet_Rail**: The left-column navigation component that renders five facet filter groups (City, Tags, Job type, Priority, Requested week) with checkbox rows and relaxed-count logic.
- **Job_Table**: The main content area component that renders a sortable, selectable table of jobs ready to be scheduled, with inline search, tri-state select-all, inline notes rows, and empty states.
- **Scheduling_Tray**: The persistent bottom-pinned component that contains date, staff, start time, and duration fields, per-job time adjustments, and the assign action. It is always rendered regardless of selection state.
- **Relaxed_Count**: A facet counting strategy where the count for each facet value reflects the number of matches that would remain if that facet group's own filter were removed, while all other active filters and search remain applied. This is the standard e-commerce facet pattern.
- **Per_Job_Time_Override**: A user-edited start or end time for a specific selected job in the scheduling tray, which promotes that job out of the automatic cascade and causes subsequent auto-mode jobs to re-cascade from the override's end time.
- **Cascade_Logic**: The sequential time computation that walks forward from the global start time, assigning each selected job a start and end time based on its estimated duration (or the default duration), respecting any per-job overrides.
- **Tri_State_Checkbox**: A checkbox with three visual states — checked (all visible rows selected), indeterminate (some visible rows selected), and unchecked (no visible rows selected).
- **JobPickerPopup**: The existing deprecated modal dialog component (`JobPickerPopup.tsx`) that this feature replaces.
- **Assignment_Mutation**: The `useCreateAppointment()` TanStack Query mutation hook that creates a single appointment by calling the backend API with job_id, staff_id, scheduled_date, time_window_start, and time_window_end.

## Requirements

### Requirement 1: Page Routing and Access Control

**User Story:** As an Admin or Manager, I want to access the job picker at a dedicated route so that I have a full-page experience for selecting and scheduling jobs.

#### Acceptance Criteria

1. WHEN a user navigates to `/schedule/pick-jobs`, THE Pick_Jobs_Page SHALL render inside the existing application Layout (sidebar and header).
2. WHILE a user session has the Admin or Manager role, THE Pick_Jobs_Page SHALL be accessible at the `/schedule/pick-jobs` route.
3. IF a user without Admin or Manager role navigates to `/schedule/pick-jobs`, THEN THE Pick_Jobs_Page SHALL redirect the user away from the page following the existing route guard behavior.
4. WHEN the route includes a `date` query parameter in `YYYY-MM-DD` format, THE Scheduling_Tray SHALL prefill the date field with that value on initial mount.
5. WHEN the route includes a `staff` query parameter containing a staff UUID, THE Scheduling_Tray SHALL prefill the staff field with that value on initial mount.
6. WHEN neither `date` nor `staff` query parameters are present, THE Scheduling_Tray SHALL default the date field to today's date and leave the staff field empty.

### Requirement 2: Page Layout and Responsive Grid

**User Story:** As a user, I want the page to have a clear three-region layout so that I can see filters, jobs, and scheduling controls simultaneously without scrolling between them.

#### Acceptance Criteria

1. THE Pick_Jobs_Page SHALL render a CSS grid with three regions: a page header spanning the full width at the top, a facet rail (left) and job table (right) in the middle row, and a scheduling tray spanning the full width at the bottom.
2. WHILE the viewport width is at least 1024px (lg breakpoint), THE Facet_Rail SHALL render as a 240px-wide column to the left of the Job_Table.
3. WHILE the viewport width is between 768px and 1023px (md breakpoint), THE Facet_Rail SHALL collapse behind a "Filters" button that opens a Sheet (shadcn/ui) from the left, and the grid SHALL become a single column.
4. WHILE the viewport width is below 768px (sm breakpoint), THE Scheduling_Tray SHALL stack its fields in a 2×2 grid with a full-width Assign button.
5. THE Facet_Rail SHALL use sticky positioning at the top of its scroll container and scroll independently when its content exceeds the viewport height.
6. THE Job_Table header row SHALL use sticky positioning at the top of the table's scroll container so column headers remain visible while scrolling the table body.
7. THE Scheduling_Tray SHALL use sticky positioning at the bottom of the page grid and SHALL always be rendered regardless of selection state.

### Requirement 3: Facet Rail Filtering

**User Story:** As a scheduler, I want cascading facet filters on the left rail so that I can narrow down the job list by city, tags, job type, priority, and requested week without losing context.

#### Acceptance Criteria

1. THE Facet_Rail SHALL render five facet groups in order: City, Tags, Job type, Priority, and Requested week.
2. THE Facet_Rail SHALL render each facet group as a `fieldset` element with a `legend` element containing the group title, and each facet value as a `label` wrapping a checkbox input.
3. WHEN a facet checkbox is toggled, THE Facet_Rail SHALL update the corresponding facet Set in the filter state, and THE Job_Table SHALL re-filter to show only jobs matching all active facets.
4. THE Facet_Rail SHALL display a Relaxed_Count next to each facet value, reflecting the number of jobs that would match if that facet group's filter were removed while all other active filters and search remain applied.
5. WHEN a facet value has a Relaxed_Count of zero, THE Facet_Rail SHALL render that value with dimmed styling (`text-slate-400`) but SHALL keep the value clickable.
6. WHEN a facet group has at least one selected value, THE Facet_Rail SHALL display a "Clear" micro-link next to that group's title.
7. WHEN any facet group has at least one selected value, THE Facet_Rail SHALL display a "Clear all filters" link at the top of the rail.
8. THE Facet_Rail SHALL compose filters using AND logic between facet groups and OR logic within a single facet group.
9. WHEN the search query changes, THE Facet_Rail SHALL preserve all existing facet selections.
10. WHEN facet selections are cleared, THE Facet_Rail SHALL preserve the current job selection (selectedJobIds).

### Requirement 4: Job Table Display and Interaction

**User Story:** As a scheduler, I want a sortable, searchable table of jobs so that I can quickly find and select the jobs I need to schedule.

#### Acceptance Criteria

1. THE Job_Table SHALL render columns in order: Checkbox, Customer (with address sub-line), Job type, Tags, City, Requested week, Priority, Duration, and Equipment.
2. WHEN a user clicks anywhere on a job row (except nested interactive elements), THE Job_Table SHALL toggle that job's selection state in selectedJobIds.
3. THE Job_Table SHALL render selected rows with a `bg-teal-50` background.
4. THE Job_Table SHALL render a Tri_State_Checkbox in the header that reflects whether all visible rows are selected, some visible rows are selected, or no visible rows are selected.
5. WHEN the header Tri_State_Checkbox is toggled, THE Job_Table SHALL select all currently visible (filtered) rows if not all are selected, or deselect all visible rows if all are selected.
6. THE Job_Table SHALL support 3-state sorting on the Customer, City, Requested week, Priority, and Duration columns: first click sorts ascending, second click sorts descending, third click reverts to the default sort (priority descending, requested_week ascending).
7. WHEN a column is actively sorted, THE Job_Table SHALL render a sort direction glyph (▲ or ▼) next to the column header and set `aria-sort` to `ascending` or `descending` on the header button.
8. WHEN a job has a non-empty `notes` field, THE Job_Table SHALL render an inline notes row immediately below that job's main row, styled with an amber background band, italic text, and a sticky-note icon.
9. THE Job_Table SHALL render customer tag pills using the existing `CUSTOMER_TAG_CONFIG` from `features/jobs/types` (priority, red_flag, slow_payer, new_customer) and property tags using the existing `PropertyTags` component patterns (residential, commercial, HOA, subscription), with shadcn Badge variant="outline" and falling back to slate styling for unknown tags.
10. THE Job_Table SHALL render priority using the actual `priority_level` values from the job: `2` (urgent) and `1` (high) with a filled amber star icon, and `0` (normal) with an em-dash.

### Requirement 5: Job Table Search

**User Story:** As a scheduler, I want to search jobs by customer name, address, phone, or job type so that I can quickly locate specific jobs.

#### Acceptance Criteria

1. THE Job_Table SHALL render a search input with a Search (lucide) icon inset on the left and placeholder text "Search customer, address, phone, job type…".
2. WHEN a user types in the search input, THE Job_Table SHALL debounce the input for 150 milliseconds before applying the search filter.
3. THE Job_Table SHALL filter jobs by matching the search query (case-insensitive) against the customer name, address, city, job type, and job ID fields.
4. WHEN the user presses the `/` key while focus is not on an input, textarea, or contenteditable element, THE Pick_Jobs_Page SHALL move focus to the search input.
5. WHEN the user presses the `Escape` key while the search input is focused, THE Job_Table SHALL clear the search query.

### Requirement 6: Job Table Empty States

**User Story:** As a scheduler, I want clear feedback when no jobs are available so that I understand whether all jobs are scheduled or my filters are too restrictive.

#### Acceptance Criteria

1. WHEN the filtered job list is empty and no filters or search are active, THE Job_Table SHALL display the message "All jobs are scheduled. Nice work."
2. WHEN the filtered job list is empty and at least one filter or search is active, THE Job_Table SHALL display the message "No jobs match these filters." with a "Clear all filters" button.

### Requirement 7: Job Table Loading State

**User Story:** As a scheduler, I want visual feedback while jobs are loading so that I know the page is working.

#### Acceptance Criteria

1. WHILE the `useJobsReadyToSchedule` query is loading, THE Job_Table region SHALL display a centered LoadingSpinner component.
2. WHILE the job data is loading, THE Facet_Rail and Scheduling_Tray SHALL remain visible.

### Requirement 8: Persistent Scheduling Tray

**User Story:** As a scheduler, I want the scheduling tray to always be visible so that I can set the date and staff context before picking jobs, matching my natural workflow.

#### Acceptance Criteria

1. THE Scheduling_Tray SHALL always be rendered at the bottom of the page, in both idle (no selection) and active (one or more jobs selected) states.
2. WHILE no jobs are selected, THE Scheduling_Tray header SHALL display "No jobs selected yet — pick some above" in muted text styling.
3. WHILE one or more jobs are selected, THE Scheduling_Tray header SHALL display "Schedule N jobs" (where N is the count of selected jobs) with `aria-live="polite"` and a "Clear selection" link.
4. WHEN some selected jobs are hidden by the current filter or search, THE Scheduling_Tray SHALL display an inline note indicating how many selected jobs are hidden by current filters.
5. THE Scheduling_Tray SHALL render four fields in a single row at lg+ breakpoints: Date (date input), Staff member (Select dropdown populated from `useStaff({ is_active: true })`), Start time (time input, default 08:00), and Default duration in minutes (number stepper, default 60, min 15, step 15).
6. WHILE no jobs are selected, THE Scheduling_Tray date, staff, start time, and duration fields SHALL remain fully enabled so the user can set scheduling context before selecting jobs.

### Requirement 9: Per-Job Time Adjustments

**User Story:** As a scheduler, I want to adjust individual job start and end times so that I can fine-tune the schedule when the automatic cascade doesn't fit my needs.

#### Acceptance Criteria

1. WHILE one or more jobs are selected, THE Scheduling_Tray SHALL display a "Per-job time adjustments" toggle link with a clock icon and chevron.
2. WHILE no jobs are selected, THE Scheduling_Tray SHALL hide the per-job time adjustments toggle.
3. WHEN the per-job time adjustments toggle is opened, THE Scheduling_Tray SHALL render a scrollable table (max height 150px) with one row per selected job showing: Customer name, Job type, Start time input, and End time input.
4. THE Scheduling_Tray SHALL compute default per-job times using Cascade_Logic: walking forward sequentially from the global start time, using each job's `estimated_duration_minutes` (falling back to the default duration when unset).
5. WHEN a user edits the start or end time for a specific job, THE Scheduling_Tray SHALL promote that job to a Per_Job_Time_Override, and all subsequent auto-mode jobs SHALL re-cascade from the last override's end time.
6. WHEN a job is deselected, THE Scheduling_Tray SHALL remove that job's Per_Job_Time_Override from the perJobTimes state.

### Requirement 10: Assignment Mutation

**User Story:** As a scheduler, I want to assign selected jobs to a staff member on a specific date so that the jobs appear on the schedule calendar.

#### Acceptance Criteria

1. WHEN the user clicks the Assign button, THE Scheduling_Tray SHALL call `useCreateAppointment().mutateAsync` once per selected job sequentially (awaiting each call before the next), passing job_id, staff_id, scheduled_date, time_window_start, and time_window_end.
2. WHEN at least one assignment succeeds, THE Scheduling_Tray SHALL display a success toast with the message "Assigned N jobs to schedule" (where N is the success count).
3. WHEN at least one assignment fails, THE Scheduling_Tray SHALL display an error toast with the message "Failed to assign M jobs" (where M is the failure count).
4. WHEN at least one assignment succeeds, THE Pick_Jobs_Page SHALL navigate to `/schedule?date=<assignDate>` after the mutation loop completes.
5. WHEN the mutation loop completes, THE Scheduling_Tray SHALL clear the selectedJobIds and perJobTimes state.
6. WHILE the assignment mutation is in progress, THE Scheduling_Tray Assign button SHALL display the label "Assigning…" and SHALL be disabled.
7. THE Assignment_Mutation SHALL trigger TanStack Query invalidations for the query keys: `jobs ready-to-schedule`, `appointments daily`, `appointments weekly`, and `dashboard today-schedule`.

### Requirement 11: Assign Button Disabled States

**User Story:** As a scheduler, I want clear feedback about why I cannot assign jobs so that I know what action to take next.

#### Acceptance Criteria

1. WHILE selectedJobIds is empty, THE Scheduling_Tray Assign button SHALL be disabled.
2. WHILE no staff member is selected, THE Scheduling_Tray Assign button SHALL be disabled and a helper line SHALL display "Pick a staff member to continue".
3. WHILE the assignment mutation is pending, THE Scheduling_Tray Assign button SHALL be disabled.
4. WHILE any Per_Job_Time_Override has an end time less than or equal to its start time, THE Scheduling_Tray Assign button SHALL be disabled and a helper line SHALL display "Selected job times overlap — review per-job adjustments".
5. WHILE one or more jobs are selected and a staff member is chosen and no time overlaps exist, THE Scheduling_Tray Assign button SHALL be enabled with the label "Assign N Jobs" (where N is the selected count).

### Requirement 12: Selection Persistence Across Filters

**User Story:** As a scheduler, I want my job selections to persist when I change filters so that I don't lose my work when narrowing or broadening the job list.

#### Acceptance Criteria

1. WHEN a facet filter is applied that hides a previously selected job from the visible table, THE Pick_Jobs_Page SHALL retain that job in selectedJobIds.
2. WHEN a facet filter is removed that reveals a previously selected job, THE Job_Table SHALL render that job's row with its selected (checked) state intact.
3. WHEN the select-all header checkbox is toggled, THE Job_Table SHALL only affect the currently visible (filtered) rows, leaving hidden selected jobs unchanged.

### Requirement 13: Leave-Without-Saving Guard

**User Story:** As a scheduler, I want a confirmation dialog when I try to leave the page with unscheduled selections so that I don't accidentally lose my work.

#### Acceptance Criteria

1. WHEN the user attempts to navigate away (browser back, sidebar link, or other route change) while selectedJobIds contains one or more jobs, THE Pick_Jobs_Page SHALL display an AlertDialog with the message "You have N selected jobs that haven't been scheduled. Leave anyway?"
2. WHEN the user confirms the leave action in the AlertDialog, THE Pick_Jobs_Page SHALL allow the navigation to proceed.
3. WHEN the user cancels the leave action in the AlertDialog, THE Pick_Jobs_Page SHALL prevent the navigation and keep the user on the page.
4. WHEN the Assign action triggers navigation to `/schedule?date=<assignDate>`, THE Pick_Jobs_Page SHALL suppress the leave guard so the navigation proceeds without a confirmation dialog.

### Requirement 14: Entry Points and Navigation

**User Story:** As a scheduler, I want clear entry points to the job picker from the schedule page so that I can easily start the job selection workflow.

#### Acceptance Criteria

1. THE Schedule page (`/schedule`) SHALL render a "Pick jobs to schedule" button in the page header, top-right area, that navigates to `/schedule/pick-jobs`.
2. THE Pick_Jobs_Page SHALL render a "← Back to schedule" link in the page header that navigates back to the previous page.
3. WHEN a successful assignment completes, THE Pick_Jobs_Page SHALL navigate to `/schedule?date=<assignDate>` so the user lands on the day they just populated.

### Requirement 15: Accessibility

**User Story:** As a user relying on assistive technology, I want the page to use proper semantic markup and ARIA attributes so that I can navigate and operate the job picker effectively.

#### Acceptance Criteria

1. THE Pick_Jobs_Page SHALL use `<main>` for the table region, `<aside>` for the facet rail, and `<section>` or `<footer>` for the scheduling tray as landmark elements.
2. THE Facet_Rail SHALL render each facet group inside a `<fieldset>` element with a `<legend>` element, and each checkbox inside a `<label>` element.
3. THE Job_Table select-all checkbox SHALL have `aria-label="Select all visible jobs"`.
4. THE Job_Table sortable column headers SHALL be `<button>` elements with `aria-sort` set to `ascending`, `descending`, or `none`.
5. THE Scheduling_Tray SHALL be wrapped in a `<section aria-label="Scheduling assignment">` element.
6. THE Scheduling_Tray header text ("Schedule N jobs") SHALL have `aria-live="polite"` so screen readers announce selection count changes.
7. WHEN the user presses `Cmd/Ctrl+Enter` while any tray field has focus, THE Pick_Jobs_Page SHALL trigger the Assign action (if enabled).

### Requirement 16: Styling and Visual Consistency

**User Story:** As a user, I want the page to match the existing platform's visual language so that the experience feels cohesive.

#### Acceptance Criteria

1. THE Pick_Jobs_Page SHALL use CSS variable tokens (`--primary`, `--background`, `--border`, `--muted-foreground`, etc.) for all colors, with no hex literals.
2. THE Pick_Jobs_Page SHALL use `rounded-lg` for inputs and buttons, and `rounded-xl` for the tray container and facet rail card.
3. THE Scheduling_Tray SHALL use the shadow `shadow-[0_-4px_12px_rgba(0,0,0,0.04)]` and a top border (`border-t border-border`).
4. THE Job_Table SHALL render customer tag pills using the existing `CUSTOMER_TAG_CONFIG` (priority, red_flag, slow_payer, new_customer) and property tag styling (residential, commercial, HOA, subscription) with shadcn `<Badge variant="outline">`, falling back to slate styling for unknown tags.
5. THE Pick_Jobs_Page SHALL use `text-sm` as the default body text size, `text-xs` for column labels and tag pills, and `text-base font-semibold` for the tray header.

### Requirement 17: Deprecation of JobPickerPopup

**User Story:** As a developer, I want the old JobPickerPopup to be marked as deprecated so that the codebase clearly signals the migration path.

#### Acceptance Criteria

1. WHEN the Pick_Jobs_Page is shipped, THE JobPickerPopup component file SHALL be annotated with a `@deprecated Use /schedule/pick-jobs` JSDoc comment.
2. WHEN the Pick_Jobs_Page is shipped, all callsites that open JobPickerPopup SHALL be changed to navigate to `/schedule/pick-jobs` instead.
3. THE JobPickerPopup component file SHALL NOT be deleted in the same release; it SHALL remain for one release cycle to allow migration.

### Requirement 18: Test Coverage

**User Story:** As a developer, I want comprehensive test coverage for the job picker so that regressions are caught early.

#### Acceptance Criteria

1. THE Pick_Jobs_Page test suite SHALL verify that the empty state renders correctly with zero jobs.
2. THE Pick_Jobs_Page test suite SHALL verify that job rows render correctly with multiple jobs.
3. THE Pick_Jobs_Page test suite SHALL verify that clicking a row toggles its selection state.
4. THE Pick_Jobs_Page test suite SHALL verify that facet clicks filter the table rows while preserving existing selections.
5. THE Pick_Jobs_Page test suite SHALL verify that select-all respects only visible (filtered) rows.
6. THE Pick_Jobs_Page test suite SHALL verify that the Assign button is disabled when no staff member is selected.
7. THE Pick_Jobs_Page test suite SHALL verify that clicking Assign calls `createAppointment` once per selected job with the correct parameters.
8. THE Pick_Jobs_Page test suite SHALL verify that a success toast and navigation occur after a successful assignment.
9. THE Pick_Jobs_Page test suite SHALL verify that search input debounces and filters jobs correctly.
10. THE Pick_Jobs_Page test suite SHALL verify that per-job time overrides persist across unrelated selection toggles.
11. THE Pick_Jobs_Page test suite SHALL verify that URL query parameters `?date=...&staff=...` prefill the tray fields.
12. THE Pick_Jobs_Page test suite SHALL verify that the leave-without-saving guard triggers when navigating away with active selections.
