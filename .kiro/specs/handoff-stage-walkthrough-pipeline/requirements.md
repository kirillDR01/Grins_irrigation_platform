# Requirements Document

## Introduction

This feature redesigns the Grins Irrigation Platform's sales pipeline experience across two interconnected views. The **Pipeline List** (at `/sales`) adds age-in-stage health signals to every row so stuck entries surface inline, with per-stage thresholds driving summary counts and filters. The **Stage Walkthrough** (at `/sales/:id`) replaces the current flat action-button layout with a stepper → NowCard → activity strip stack that makes the current stage and next action obvious at a glance. Both views are frontend-only for v1 — no backend or API changes are required.

## Glossary

- **Pipeline_List**: The redesigned table view at `/sales` that replaces the existing `SalesPipeline.tsx`, showing all sales entries with age-in-stage chips, summary cards, and compact action buttons.
- **Stage_Walkthrough**: The redesigned detail view at `/sales/:id` that extends `SalesDetail.tsx` with a StageStepper, NowCard, and ActivityStrip.
- **StageStepper**: A 5-step horizontal stepper component displaying the sales pipeline stages grouped into three phases (Plan, Sign, Close), with visual states for done, active, waiting, and future steps.
- **NowCard**: A stage-driven card component that displays the current "what to do next" guidance, including a pill indicator, title, body copy, optional dropzone/nudge schedule/week picker, action buttons, and lock banners.
- **ActivityStrip**: A one-line horizontal event feed component showing the 2–4 most recent events for the current stage.
- **AutoNudgeSchedule**: A component rendered inside NowCard for the `pending_approval` stage, displaying the fixed follow-up cadence (day 0, 2, 5, 8 + weekly loop).
- **AgeChip**: A small colored pill rendered next to the status badge on each pipeline row, indicating whether the entry is fresh, stale, or stuck based on per-stage thresholds.
- **StageKey**: One of the five stepper stages: `schedule_estimate`, `send_estimate`, `pending_approval`, `send_contract`, `closed_won`. The DB enum `estimate_scheduled` collapses into `schedule_estimate`; `closed_lost` hides the stepper entirely.
- **AgeBucket**: A derived classification (`fresh`, `stale`, or `stuck`) computed from the number of calendar days an entry has spent in its current stage, compared against per-stage thresholds.
- **NowActionId**: A string identifier for click handlers (e.g. `schedule_visit`, `convert_to_job`) that the NowCard passes to its host via `onAction`, keeping the component pure and testable.
- **WeekOf_Picker**: A chip-based date selector rendered in the `send_contract` NowCard variation, allowing the user to pick a rough target week for the job. Persisted to localStorage in v1.
- **Dropzone**: A drag-and-drop file upload area rendered inside NowCard for estimate PDF and signed agreement PDF uploads. Accepts `application/pdf` only.
- **Stage_Name_Reconciliation**: The display-layer alias where the DB enum `send_contract` is shown as "Convert to Job" in the UI. No migration or API change is involved.

## Requirements

### Requirement 1: Type System Extension

**User Story:** As a developer, I want the sales pipeline type system extended with stage definitions, age thresholds, activity event types, and NowCard content contracts, so that all new components have a single source of truth for data shapes.

#### Acceptance Criteria

1. THE Type_System SHALL export `StageKey`, `StageDef`, `STAGES`, `STAGE_INDEX`, and `statusToStageKey` types and constants as defined in the handoff `data-shapes.ts`.
2. THE Type_System SHALL export `AgeBucket`, `AgeThresholds`, `AGE_THRESHOLDS`, and `StageAge` types and constants with per-stage threshold values: `schedule_estimate` (3/7), `send_estimate` (3/7), `pending_approval` (4/10), `send_contract` (3/7), `closed_won` (999/999).
3. THE Type_System SHALL export `ActivityEventKind`, `ActivityEvent`, `NowCardContent`, `NowAction`, `NowActionId`, `NowCardInputs`, `NudgeStep`, and `NUDGE_CADENCE_DAYS` types and constants.
4. THE Type_System SHALL preserve all existing exports from `pipeline.ts` without modification.
5. WHEN `statusToStageKey` is called with `'estimate_scheduled'`, THE function SHALL return `'schedule_estimate'`.
6. WHEN `statusToStageKey` is called with `'closed_lost'`, THE function SHALL return `null`.
7. THE `SALES_STATUS_CONFIG` entry for `send_contract` SHALL use the display label "Convert to Job" for both `label` and `action` fields.

### Requirement 2: Age-in-Stage Computation

**User Story:** As a sales manager, I want each pipeline entry to show how long it has been in its current stage, so that I can identify entries that need attention.

#### Acceptance Criteria

1. THE `useStageAge` hook SHALL compute the number of calendar days since the entry entered its current stage, using `updated_at` as a fallback timestamp for v1.
2. WHEN the computed days are less than or equal to the stage's `freshMax` threshold, THE hook SHALL return `bucket: 'fresh'`.
3. WHEN the computed days are greater than `freshMax` but less than or equal to `staleMax`, THE hook SHALL return `bucket: 'stale'`.
4. WHEN the computed days are greater than `staleMax`, THE hook SHALL return `bucket: 'stuck'` and `needsFollowup: true`.
5. WHEN the entry status is `closed_won` or `closed_lost`, THE hook SHALL return `{ days: 0, bucket: 'fresh', needsFollowup: false }`.
6. WHEN the entry status is `estimate_scheduled`, THE hook SHALL use the `schedule_estimate` thresholds.
7. THE hook SHALL include a `TODO(backend)` comment noting that the proper source is a `stage_entered_at` column.

### Requirement 3: AgeChip Component

**User Story:** As a sales manager, I want a colored chip next to each entry's status pill showing its age bucket, so that I can visually scan for entries that need attention.

#### Acceptance Criteria

1. THE AgeChip SHALL render a rounded-full pill with a 1.5px border, displaying a leading glyph (`●` for fresh, `⚡` for stale and stuck) followed by the age in days formatted as `{n}d`.
2. WHEN the bucket is `fresh`, THE AgeChip SHALL use emerald color tokens (text-emerald-700, bg-emerald-50, border-emerald-500).
3. WHEN the bucket is `stale`, THE AgeChip SHALL use amber color tokens (text-amber-700, bg-amber-50, border-amber-500).
4. WHEN the bucket is `stuck`, THE AgeChip SHALL use red color tokens (text-red-700, bg-red-50, border-red-500).
5. THE AgeChip SHALL include an `aria-label` in the format `"{BUCKET} — {n} days in {stage name}"` where the stage name has underscores replaced with spaces.
6. WHEN the age is less than 1 day, THE AgeChip SHALL display `1d`.
7. THE AgeChip SHALL NOT render for entries with status `closed_won` or `closed_lost`.

### Requirement 4: Pipeline List Summary Cards

**User Story:** As a sales manager, I want four summary cards at the top of the pipeline list showing key metrics, so that I can quickly assess the health of my pipeline.

#### Acceptance Criteria

1. THE Pipeline_List SHALL render four summary cards: Needs Estimate, Pending Approval, Needs Follow-Up, and Revenue Pipeline.
2. THE Needs_Estimate card SHALL display the count from `summary.schedule_estimate` and toggle `statusFilter = 'schedule_estimate'` on click.
3. THE Pending_Approval card SHALL display the count from `summary.pending_approval` and toggle `statusFilter = 'pending_approval'` on click.
4. THE Needs_Follow-Up card SHALL display the count of entries where `age.bucket === 'stuck'`, computed client-side over the loaded page rows.
5. WHEN the Needs_Follow-Up card is clicked, THE Pipeline_List SHALL toggle a client-side stuck-only filter.
6. THE Needs_Follow-Up card SHALL display a week-over-week delta below the count, using localStorage to persist the previous week's count keyed on ISO week number.
7. THE Revenue_Pipeline card SHALL display `metrics.total_pipeline_revenue` formatted with locale separators and SHALL NOT be clickable.
8. THE Needs_Follow-Up card SHALL have a `bg-amber-50` background to visually distinguish it from the other cards.

### Requirement 5: Pipeline List Table Redesign

**User Story:** As a sales manager, I want a streamlined pipeline table with age chips, address tooltips, and compact action buttons, so that I can efficiently manage my sales entries.

#### Acceptance Criteria

1. THE Pipeline_List table SHALL display six columns: Customer, Phone, Job Type, Status (with AgeChip), Last Contact, and Actions.
2. THE Pipeline_List SHALL NOT display a separate Address column; instead, WHEN a customer has a `property_address`, THE customer name cell SHALL render a shadcn Tooltip showing the address on hover.
3. THE Status column SHALL render the existing status pill followed by an AgeChip for all non-terminal statuses.
4. WHEN `override_flag` is true on an entry, THE Status column SHALL display a ⚠ icon after the status pill.
5. THE Actions column SHALL render a compact primary button with a stage-specific label: Schedule (schedule_estimate), Send (estimate_scheduled, send_estimate), Nudge (pending_approval), Convert (send_contract), View job (closed_won as ghost variant).
6. THE Actions column SHALL render a secondary ghost `✕` dismiss button next to the primary action button.
7. WHEN a row is clicked, THE Pipeline_List SHALL navigate to `/sales/{entry.id}`.
8. THE Pipeline_List SHALL NOT render an action button for `closed_lost` entries.

### Requirement 6: Pipeline List Filtering

**User Story:** As a sales manager, I want to filter the pipeline by status and by stuck entries, so that I can focus on entries that need immediate attention.

#### Acceptance Criteria

1. WHEN a summary card is clicked, THE Pipeline_List SHALL toggle the corresponding status filter and reset pagination to page 0.
2. WHEN the Needs_Follow-Up card is clicked, THE Pipeline_List SHALL toggle a client-side `stuckFilter` that shows only entries where `age.bucket === 'stuck'`.
3. WHILE a status filter is active, THE Pipeline_List SHALL display a filter chip showing the status label with a Clear button.
4. WHILE the stuck filter is active, THE Pipeline_List SHALL display a filter chip reading "⚡ Stuck entries only" with a Clear button.
5. THE Pipeline_List SHALL support both `statusFilter` and `stuckFilter` being active simultaneously.
6. WHEN the Clear button is clicked, THE Pipeline_List SHALL remove all active filters and reset pagination to page 0.

### Requirement 7: StageStepper Component

**User Story:** As a sales user, I want a visual stepper showing where an entry is in the pipeline, so that I can understand the overall progress at a glance.

#### Acceptance Criteria

1. THE StageStepper SHALL render a 5-step horizontal stepper from the `STAGES` constant, with three phase labels above: Plan (step 1), Sign (steps 2–3), Close (steps 4–5).
2. WHEN a step's index is less than the current stage index, THE StageStepper SHALL render that step in the `done` state with a filled emerald circle showing `✓` and an emerald connector line.
3. WHEN a step's index equals the current stage index, THE StageStepper SHALL render that step in the `active` state with a filled slate-900 circle showing the step number.
4. WHEN the current stage is `pending_approval`, THE StageStepper SHALL render step 3 in the `waiting` state with a dashed amber border, slow 2.5s pulse animation, and amber text.
5. WHEN a step's index is greater than the current stage index, THE StageStepper SHALL render that step in the `future` state with an outlined slate-300 circle and a dashed slate-200 connector line.
6. THE StageStepper SHALL render a "⋯ change stage manually" button that triggers the `onOverrideClick` callback.
7. THE StageStepper SHALL render a "✕ Mark Lost" button that triggers the `onMarkLost` callback.
8. WHEN `visitScheduled` is true and the current stage is `schedule_estimate`, THE StageStepper SHALL render a calendar badge below step 1's label.
9. THE `waiting` pulse animation SHALL be disabled when the user has `prefers-reduced-motion` enabled.

### Requirement 8: NowCard Component

**User Story:** As a sales user, I want a card that tells me exactly what to do next for each pipeline entry, so that I never have to guess the next step.

#### Acceptance Criteria

1. THE NowCard SHALL render a card with a left border accent colored by the pill tone: sky for `you`, amber for `cust`, emerald for `done`.
2. THE NowCard SHALL render a pill at the top-left showing "Your move" (tone: you), "Waiting on customer" (tone: cust), or "Complete" (tone: done).
3. THE NowCard SHALL render the title with `text-wrap: pretty` styling.
4. THE NowCard SHALL render body copy using `dangerouslySetInnerHTML` with a sanitizer that allows only `<em>` and `<b>` tags.
5. THE NowCard SHALL render action buttons mapped to shadcn variants: `primary` → default, `outline` → outline, `ghost` → ghost, `danger` → outline with red styling, `locked` → disabled outline with lock icon and tooltip showing the reason.
6. THE NowCard SHALL delegate all click actions to the host via `onAction(id: NowActionId)` and SHALL NOT call any mutations directly.
7. WHEN `content.lockBanner` is set, THE NowCard SHALL render a red-toned banner below the action row with a lock icon and the banner text.

### Requirement 9: NowCard Content — Pure Function

**User Story:** As a developer, I want the NowCard content to be a pure function of stage and flags, so that all 7 variations are fully testable without mocking.

#### Acceptance Criteria

1. THE `nowContent` function SHALL accept `NowCardInputs` plus `firstName`, `jobId`, `sentDate`, and `docName` parameters and return a `NowCardContent` object.
2. WHEN the stage is `schedule_estimate`, THE function SHALL return pill "Your move", title referencing the customer's first name, and actions: Schedule visit (primary) and Text appointment confirmation (outline).
3. WHEN the stage is `send_estimate` and `hasEstimateDoc` is false, THE function SHALL return a dropzone with `filled: false`, a locked "Upload & send estimate" action, a "Skip — advance manually" ghost action, and a lock banner stating "No estimate PDF yet."
4. WHEN the stage is `send_estimate` and `hasEstimateDoc` is true and `hasCustomerEmail` is true, THE function SHALL return a dropzone with `filled: true` and a primary "Upload & send estimate" action.
5. WHEN the stage is `send_estimate` and `hasEstimateDoc` is true and `hasCustomerEmail` is false, THE function SHALL return a locked "Upload & send estimate" action with reason "no email on file" and a primary "Add customer email" action.
6. WHEN the stage is `pending_approval`, THE function SHALL return pill "Waiting on customer", `showNudgeSchedule: true`, and actions: Client approved manual (primary), Resend estimate (outline), Pause auto-follow-up (outline), Client declined (danger).
7. WHEN the stage is `send_contract` and `hasSignedAgreement` is false, THE function SHALL return a dropzone for agreement with `filled: false`, `showWeekOfPicker: true`, and a locked "Convert to Job" action with reason "upload signed agreement first".
8. WHEN the stage is `send_contract` and `hasSignedAgreement` is true, THE function SHALL return a dropzone for agreement with `filled: true` and a primary "Convert to Job" action.
9. WHEN the stage is `closed_won`, THE function SHALL return pill "Complete", title referencing the job ID and week-of target, and actions: View Job (primary), View Customer profile (outline), Jump to Schedule (outline).
10. FOR ALL valid `NowCardInputs` combinations, parsing the output of `nowContent` and then re-serializing it SHALL produce an equivalent object (round-trip property for the pure content function).

### Requirement 10: NowCard Dropzone

**User Story:** As a sales user, I want to drag-and-drop PDF files into the NowCard, so that I can quickly upload estimates and agreements without navigating away.

#### Acceptance Criteria

1. WHEN the dropzone is in the empty state, THE Dropzone SHALL render a dashed-border area with instructions to drag a PDF or click to browse.
2. WHEN a file is dragged over the empty dropzone, THE Dropzone SHALL change its border to sky-500 and background to sky-100.
3. WHEN a PDF file is dropped, THE Dropzone SHALL call `onFileDrop` with the file and the dropzone kind (`estimate` or `agreement`).
4. IF a non-PDF file is dropped, THEN THE Dropzone SHALL reject it and display a sonner toast reading "PDF only."
5. WHEN the dropzone is in the filled state, THE Dropzone SHALL render the filename, file size, and links for preview, replace, and remove.
6. THE Dropzone SHALL accept files via both drag-and-drop and a hidden file input triggered by click, with `accept="application/pdf"`.

### Requirement 11: AutoNudgeSchedule Component

**User Story:** As a sales user, I want to see the automated follow-up schedule for pending approvals, so that I know when the system will nudge the customer and what message will be sent.

#### Acceptance Criteria

1. THE AutoNudgeSchedule SHALL render a schedule with rows for day 0, 2, 5, 8 (from `NUDGE_CADENCE_DAYS`) plus a weekly loop sentinel row.
2. WHEN a nudge day offset is less than the current day number (days since `estimateSentAt`), THE row SHALL render in the `done` state with a `✓` leading glyph and emerald text.
3. THE AutoNudgeSchedule SHALL render exactly one row in the `next` state (the first offset greater than the current day number) with a `⏰` leading glyph, amber highlight, and bold text.
4. WHEN a nudge day offset is greater than the next-upcoming offset, THE row SHALL render in the `future` state with a `·` leading glyph and slate text.
5. THE weekly loop row SHALL always render in the `loop` state with a `🔁` leading glyph, italic text, and a top border separator.
6. WHEN `paused` is true, THE AutoNudgeSchedule SHALL strike through all future and loop rows and display a banner reading "Paused. Resume to continue auto-follow-up."

### Requirement 12: ActivityStrip Component

**User Story:** As a sales user, I want a compact activity feed showing recent events for the current stage, so that I have context about what has happened without scrolling through a full history.

#### Acceptance Criteria

1. THE ActivityStrip SHALL render a horizontal flex-wrap row of event chips separated by `·` dividers.
2. WHEN an event has `tone: 'done'`, THE chip SHALL render in `text-slate-600`.
3. WHEN an event has `tone: 'wait'`, THE chip SHALL render in `text-amber-700` with `font-medium`.
4. WHEN an event has `tone: 'neutral'`, THE chip SHALL render in `text-slate-500`.
5. THE ActivityStrip SHALL render a leading glyph per event kind as defined in the GLYPH mapping (e.g. 🆕 for `moved_from_leads`, 📅 for `visit_scheduled`, ✉ for `estimate_sent`).
6. IF the events array is empty, THEN THE ActivityStrip SHALL render nothing (return null).

### Requirement 13: Stage Walkthrough Layout Integration

**User Story:** As a sales user, I want the detail page to show a stepper, NowCard, and activity strip between the header and documents section, so that the current stage and next action are always visible.

#### Acceptance Criteria

1. THE SalesDetail page SHALL render the StageStepper between the header card and the NowCard.
2. THE SalesDetail page SHALL render the NowCard between the StageStepper and the ActivityStrip.
3. THE SalesDetail page SHALL render the ActivityStrip between the NowCard and the existing DocumentsSection.
4. THE SalesDetail page SHALL remove the StatusActionButton from the header card actions row; the primary action SHALL live only inside the NowCard.
5. WHEN the entry status is `closed_lost`, THE SalesDetail page SHALL hide the StageStepper, NowCard, and ActivityStrip entirely and SHALL display a slate banner reading "Closed Lost — {closed_reason}. No further actions." above the DocumentsSection.

### Requirement 14: Week-Of Picker

**User Story:** As a sales user, I want to pick a rough target week for a job during the Convert to Job stage, so that the scheduling team has a starting point.

#### Acceptance Criteria

1. THE WeekOf_Picker SHALL render 5 chip buttons representing the current week and the next 4 weeks, using Monday as the week anchor.
2. THE WeekOf_Picker SHALL render an additional "+ pick date…" chip that opens a shadcn Popover with a Calendar for custom date selection.
3. WHEN a chip is selected, THE WeekOf_Picker SHALL style it with `bg-slate-900 text-white`; unselected chips SHALL use `bg-white border-slate-200 text-slate-700`.
4. THE WeekOf_Picker SHALL persist the selected week to `localStorage` keyed by the entry ID.
5. THE WeekOf_Picker SHALL include a helper note: "Used only as a target — pin the exact day + crew later in the Jobs tab."

### Requirement 15: Click-Handler Wiring

**User Story:** As a developer, I want all NowCard actions wired to the correct mutations or navigation, so that the walkthrough is functional end-to-end.

#### Acceptance Criteria

1. WHEN the `schedule_visit` action is triggered, THE SalesDetail host SHALL open the schedule modal.
2. WHEN the `send_estimate_email` action is triggered, THE SalesDetail host SHALL call the send estimate mutation.
3. WHEN the `convert_to_job` action is triggered, THE SalesDetail host SHALL open the convert-to-job modal.
4. WHEN the `view_job` action is triggered, THE SalesDetail host SHALL navigate to `/jobs/{entry.job_id}`.
5. WHEN the `view_customer` action is triggered, THE SalesDetail host SHALL navigate to `/customers/{entry.customer_id}`.
6. WHEN the `jump_to_schedule` action is triggered, THE SalesDetail host SHALL navigate to `/schedule`.
7. WHEN the `mark_declined` action is triggered, THE SalesDetail host SHALL open a decline confirmation modal.
8. WHEN the `skip_advance` action is triggered, THE SalesDetail host SHALL advance the entry status to `pending_approval`.
9. WHEN the `mark_approved_manual` action is triggered, THE SalesDetail host SHALL advance the entry status to `send_contract`.
10. IF the `text_confirmation`, `resend_estimate`, or `pause_nudges` action is triggered, THEN THE SalesDetail host SHALL display a sonner toast reading "Not wired yet — TODO" because the backend endpoint does not exist yet.

### Requirement 16: Test IDs and Accessibility

**User Story:** As a QA engineer, I want all interactive elements to have `data-testid` attributes and proper accessibility labels, so that automated tests and screen readers can interact with the UI.

#### Acceptance Criteria

1. THE Pipeline_List root SHALL have `data-testid="pipeline-list-page"`.
2. THE StageStepper root SHALL have `data-testid="stage-stepper"` and each step SHALL have `data-testid="stage-step-{key}"` with a `data-state` attribute.
3. THE NowCard root SHALL have `data-testid="now-card"` with a `data-stage` attribute, and the pill SHALL have `data-testid="now-card-pill"` with a `data-tone` attribute.
4. THE AutoNudgeSchedule root SHALL have `data-testid="auto-nudge-schedule"` and each row SHALL have `data-testid="auto-nudge-row-{dayOffset}"` with a `data-state` attribute.
5. THE ActivityStrip root SHALL have `data-testid="activity-strip"` and each event SHALL have `data-testid="activity-event-{kind}"`.
6. THE AgeChip SHALL include an `aria-label` describing the bucket, days, and stage name.
7. THE NowCard title SHALL use `text-wrap: pretty` for improved readability.
8. THE StageStepper `waiting` animation SHALL respect `prefers-reduced-motion` by disabling the pulse.

### Requirement 17: No New Dependencies or Backend Changes

**User Story:** As a developer, I want this feature to ship with zero new runtime dependencies and zero backend changes, so that the deployment risk is minimal.

#### Acceptance Criteria

1. THE feature SHALL NOT add any new npm dependencies beyond what is already in `package.json`.
2. THE feature SHALL NOT require any database migrations, API schema changes, or backend code modifications.
3. THE feature SHALL NOT modify the existing `useSalesPipeline` hook or `salesPipelineApi` module.
4. WHEN a backend endpoint is needed but does not exist (e.g. `sendConfirmationSMS`, `resendEstimate`, `pauseNudges`), THE feature SHALL stub the action with a sonner toast and a `TODO(backend)` code comment.
5. THE feature SHALL use `updated_at` as the age computation fallback and SHALL include a `TODO(backend)` comment for the future `stage_entered_at` column.
6. THE feature SHALL use `localStorage` for Week-Of persistence and SHALL include a `TODO(backend)` comment for the future `target_week_of` column.
