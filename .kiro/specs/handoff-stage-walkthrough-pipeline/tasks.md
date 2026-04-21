# Implementation Plan: Handoff Stage Walkthrough and Pipeline

## Overview

This plan implements the redesigned sales pipeline across two views — the **Pipeline List** (`/sales`) with age-in-stage health signals, and the **Stage Walkthrough** (`/sales/:id`) with a StageStepper → NowCard → ActivityStrip guided experience. All work is frontend-only (React 19, TypeScript, Tailwind 4, shadcn/Radix, Vitest, fast-check). Scaffold files from `feature-developments/handoff-stage-walkthrough-and-pipeline/scaffold/` provide the implementation source to copy and adapt.

## Tasks

- [x] 1. Extend type system and update status config
  - [x] 1.1 Merge `data-shapes.ts` into `frontend/src/features/sales/types/pipeline.ts`
    - Add `StageKey`, `StageDef`, `StagePhase`, `STAGES`, `STAGE_INDEX`, `statusToStageKey` types and constants
    - Add `AgeBucket`, `AgeThresholds`, `AGE_THRESHOLDS`, `StageAge` types and constants with per-stage thresholds: `schedule_estimate` (3/7), `send_estimate` (3/7), `pending_approval` (4/10), `send_contract` (3/7), `closed_won` (999/999)
    - Add `ActivityEventKind`, `ActivityEvent`, `NowPill`, `NowCardInputs`, `NowCardContent`, `NowAction`, `NowActionId`, `LucideIconName` types
    - Add `NudgeStep`, `NUDGE_CADENCE_DAYS` types and constants
    - Preserve ALL existing exports without modification
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 1.2 Update `SALES_STATUS_CONFIG` for `send_contract`
    - Change `send_contract.label` to `"Convert to Job"`
    - Change `send_contract.action` to `"Convert to Job"`
    - _Requirements: 1.7_

- [x] 2. Create `useStageAge` hook and `AgeChip` component
  - [x] 2.1 Create `frontend/src/features/sales/hooks/useStageAge.ts`
    - Copy and adapt from `scaffold/useStageAge.ts`
    - Export `useStageAge(entry: SalesEntry): StageAge` hook
    - Export `countStuck(rows: SalesEntry[]): number` utility
    - Use `updated_at` fallback with `TODO(backend)` comment for `stage_entered_at`
    - Map `estimate_scheduled` → `schedule_estimate` thresholds
    - Return `{ days: 0, bucket: 'fresh', needsFollowup: false }` for terminal statuses
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 2.2 Create `frontend/src/features/sales/components/AgeChip.tsx`
    - Copy and adapt from `scaffold/AgeChip.tsx`
    - Render rounded-full pill with 1.5px border, leading glyph (`●` fresh, `⚡` stale/stuck), `{n}d` label
    - Apply correct color tokens per bucket (emerald/amber/red)
    - Include `aria-label` in format `"{BUCKET} — {n} days in {stage name}"`
    - Display `1d` minimum when age < 1 day
    - Include `data-testid` and `data-bucket` attributes
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 2.3 Write unit tests for `useStageAge` hook — `frontend/src/features/sales/hooks/useStageAge.test.ts`
    - Test threshold boundaries for every stage (fresh/stale/stuck transitions)
    - Test terminal status returns `{ days: 0, bucket: 'fresh', needsFollowup: false }`
    - Test `estimate_scheduled` maps to `schedule_estimate` thresholds
    - Test `countStuck` with mixed arrays of entries
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 2.4 Write property-based test for age bucket classification — `frontend/src/features/sales/hooks/useStageAge.test.ts`
    - **Property 2: Age Bucket Classification**
    - Use fast-check to generate random `SalesEntry` objects with non-terminal statuses and random timestamps 0–30 days ago
    - Verify: (a) `days` equals `floor((now - ref) / 86_400_000)`, (b) `bucket` matches threshold rules, (c) `needsFollowup === (bucket === 'stuck')`
    - Verify terminal statuses always return `{ days: 0, bucket: 'fresh', needsFollowup: false }`
    - Minimum 100 iterations
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

  - [x] 2.5 Write property-based test for countStuck — `frontend/src/features/sales/hooks/useStageAge.test.ts`
    - **Property 4: countStuck Correctness**
    - Use fast-check to generate arrays of 0–20 `SalesEntry` objects with random statuses and timestamps
    - Verify count matches manual threshold computation
    - Minimum 100 iterations
    - **Validates: Requirements 4.4**

- [x] 3. Replace Pipeline List with scaffold implementation
  - [x] 3.1 Replace `frontend/src/features/sales/components/SalesPipeline.tsx` with scaffold PipelineList
    - Copy and adapt from `scaffold/PipelineList.tsx`
    - Render 4 summary cards: Needs Estimate, Pending Approval, Needs Follow-Up (with `bg-amber-50` and WoW delta), Revenue Pipeline
    - Needs Follow-Up count uses `countStuck(rows)` computed client-side
    - Revenue Pipeline card is not clickable
    - Import and use `AgeChip` and `useStageAge` from new files
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 3.2 Implement table redesign with 6 columns
    - Customer (bold name, address tooltip on hover), Phone, Job Type, Status (pill + AgeChip + override ⚠), Last Contact, Actions
    - Remove Address column; add shadcn Tooltip on customer name showing `property_address`
    - AgeChip renders on every non-terminal row
    - Override flag shows ⚠ icon after status pill
    - Row click navigates to `/sales/{entry.id}`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7_

  - [x] 3.3 Implement compact action buttons per stage
    - Stage-specific labels: Schedule, Send, Nudge, Convert, View job (ghost), no button for closed_lost
    - Secondary ghost `✕` dismiss button next to primary action
    - _Requirements: 5.5, 5.6, 5.8_

  - [x] 3.4 Implement status and stuck filtering
    - Summary card click toggles `statusFilter` and resets pagination to page 0
    - Needs Follow-Up click toggles client-side `stuckFilter` showing only `bucket === 'stuck'` entries
    - Filter chips display when active: status label chip + "⚡ Stuck entries only" chip
    - Both filters can be active simultaneously
    - Clear button removes all filters and resets pagination
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 3.5 Add all Pipeline List `data-testid` attributes
    - Root: `pipeline-list-page`
    - Summary cards: `pipeline-summary-needs-estimate`, `pipeline-summary-pending-approval`, `pipeline-summary-needs-followup`, `pipeline-summary-revenue`
    - Delta: `pipeline-summary-followup-delta`
    - Stuck filter chip: `pipeline-filter-age-stuck`
    - Rows: `pipeline-row-{id}`, age chips: `pipeline-row-age-{id}`, actions: `pipeline-row-action-{id}`, dismiss: `pipeline-row-dismiss-{id}`
    - _Requirements: 16.1_

- [x] 4. Create `nowContent` pure function
  - [x] 4.1 Create `frontend/src/features/sales/lib/nowContent.ts`
    - Copy and adapt from `scaffold/nowContent.ts`
    - Implement pure function: `(NowCardInputs & { firstName, jobId?, sentDate?, docName? }) → NowCardContent | null`
    - Implement all 7 variations: schedule_estimate, send_estimate (empty), send_estimate (ready), pending_approval, send_contract (no agreement), send_contract (agreement uploaded), closed_won
    - Return `null` for `closed_lost` (caller handles with banner)
    - Include `sanitizeCopy` helper that strips all HTML tags except `<em>` and `<b>`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [x] 4.2 Write unit tests for `nowContent` — `frontend/src/features/sales/lib/nowContent.test.ts`
    - Snapshot test for each of the 7 NowCard variations
    - Test `statusToStageKey` mapping: `estimate_scheduled` → `schedule_estimate`, `closed_lost` → `null`
    - Test `sanitizeCopy` strips disallowed tags, preserves `<em>` and `<b>`
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 1.5, 1.6_

  - [x] 4.3 Write property-based test for statusToStageKey — `frontend/src/features/sales/lib/nowContent.test.ts`
    - **Property 1: statusToStageKey Mapping Correctness**
    - Use fast-check to generate from `SalesEntryStatus` union (7 values)
    - Verify: `estimate_scheduled` → `schedule_estimate`, `closed_lost` → `null`, all others map to themselves
    - Minimum 100 iterations
    - **Validates: Requirements 1.5, 1.6**

  - [x] 4.4 Write property-based test for sanitizeCopy — `frontend/src/features/sales/lib/nowContent.test.ts`
    - **Property 6: sanitizeCopy HTML Allowlist**
    - Use fast-check to generate random HTML strings with mixed valid/invalid tags
    - Verify output contains no HTML tags other than `<em>`, `</em>`, `<b>`, `</b>`
    - Minimum 100 iterations
    - **Validates: Requirements 8.4**

  - [x] 4.5 Write property-based test for nowContent output structure — `frontend/src/features/sales/lib/nowContent.test.ts`
    - **Property 7: nowContent Output Structure**
    - Use fast-check to generate all combinations of `{ stage, hasEstimateDoc, hasSignedAgreement, hasCustomerEmail }` × random `firstName` strings
    - Verify: (a) pill tone matches expected for stage, (b) title contains firstName, (c) actions is non-empty, (d) send_estimate without doc has lockBanner and unfilled dropzone, (e) send_contract without agreement has locked convert action, (f) determinism — identical inputs produce deeply equal results
    - Minimum 100 iterations
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10**

- [x] 5. Checkpoint — Ensure all tests pass
  - Run `cd frontend && npx vitest --run` and verify zero failures
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create StageStepper component
  - [x] 6.1 Create `frontend/src/features/sales/components/StageStepper.tsx`
    - Copy and adapt from `scaffold/StageStepper.tsx`
    - Render 5-step horizontal stepper from `STAGES` constant
    - Three phase labels: Plan (step 1), Sign (steps 2–3), Close (steps 4–5)
    - Step states: `done` (emerald ✓), `active` (slate-900), `waiting` (dashed amber pulse for `pending_approval` only), `future` (outlined slate-300)
    - Footer: "⋯ change stage manually" → `onOverrideClick`, "✕ Mark Lost" → `onMarkLost`
    - Calendar badge when `visitScheduled` is true and stage is `schedule_estimate`
    - `waiting` pulse animation respects `prefers-reduced-motion`
    - All `data-testid` attributes: `stage-stepper`, `stage-step-{key}` with `data-state`, `stage-stepper-override`, `stage-stepper-mark-lost`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 16.2, 16.8_

  - [x] 6.2 Write unit tests for StageStepper — `frontend/src/features/sales/components/StageStepper.test.tsx`
    - Test renders each stage with correct step states (done/active/waiting/future)
    - Test `pending_approval` shows waiting state on step 3
    - Test override button calls `onOverrideClick`
    - Test Mark Lost button calls `onMarkLost`
    - Test calendar badge renders when `visitScheduled` is true
    - Test 5 steps and 3 phase labels render
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [x] 6.3 Write property-based test for step state computation — `frontend/src/features/sales/components/StageStepper.test.tsx`
    - **Property 5: StageStepper Step State Computation**
    - Use fast-check to generate random `StageKey` values
    - Verify: (a) all steps with `index < currentStageIndex` have state `done`, (b) step at `index === currentStageIndex` has state `active` (or `waiting` for `pending_approval`), (c) all steps with `index > currentStageIndex` have state `future`
    - Minimum 100 iterations
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**

- [x] 7. Create NowCard component with Dropzone and WeekOfPicker
  - [x] 7.1 Create `frontend/src/features/sales/components/NowCard.tsx`
    - Copy and adapt from `scaffold/NowCard.tsx`
    - Render card with left border accent colored by pill tone (sky/amber/emerald)
    - Render pill, title (`text-wrap: pretty`), body copy (sanitized HTML via `dangerouslySetInnerHTML`)
    - Render action buttons mapped to shadcn variants: primary → default, outline → outline, ghost → ghost, danger → outline+red, locked → disabled+tooltip
    - Delegate all actions to host via `onAction(id: NowActionId)` — never call mutations directly
    - Render lock banner when `content.lockBanner` is set
    - Include Dropzone sub-component: empty (dashed border, drag-over state) and filled (filename, size, replace/remove links)
    - Dropzone accepts `application/pdf` only; rejects non-PDF with sonner toast "PDF only."
    - Include WeekOfPicker sub-component: 5 week chips (Monday anchor) + "+ pick date…" chip
    - WeekOfPicker persists to `localStorage` keyed by entry ID with `TODO(backend)` comment
    - All `data-testid` attributes: `now-card` with `data-stage`, `now-card-pill` with `data-tone`, `now-card-title`, action testIds from content, `now-card-lock-banner`, `now-card-dropzone-empty`, `now-card-dropzone-filled`, `now-card-weekof-{value}`, `now-card-weekof-pick`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 14.1, 14.2, 14.3, 14.4, 14.5, 16.3, 16.7_

  - [x] 7.2 Write unit tests for NowCard — `frontend/src/features/sales/components/NowCard.test.tsx`
    - Test pill renders with correct tone and label for each variation
    - Test lock banner renders when set
    - Test dropzone empty and filled states
    - Test dropzone rejects non-PDF files
    - Test action buttons call `onAction` with correct NowActionId
    - Test locked action shows tooltip with reason
    - Test WeekOfPicker renders 5 week chips + pick date chip
    - _Requirements: 8.1, 8.2, 8.5, 8.6, 8.7, 10.1, 10.4, 14.1_

  - [x] 7.3 Write property-based test for AgeChip rendering — `frontend/src/features/sales/components/NowCard.test.tsx`
    - **Property 3: AgeChip Rendering Correctness**
    - Use fast-check to generate `StageAge` with random `days` (0–100), random `bucket`, random `stageKey` strings
    - Verify: (a) correct glyph per bucket, (b) `Math.max(1, days)` followed by `d`, (c) correct color tokens, (d) `aria-label` matches expected pattern
    - Minimum 100 iterations
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [x] 7.4 Write property-based test for generateWeeks — `frontend/src/features/sales/components/NowCard.test.tsx`
    - **Property 9: generateWeeks Produces Consecutive Monday-Anchored Weeks**
    - Use fast-check to generate random starting dates across different months/years
    - Verify: exactly 5 labels, each successive label 7 days apart, first label is Monday of the week containing the start date
    - Minimum 100 iterations
    - **Validates: Requirements 14.1**

- [x] 8. Create AutoNudgeSchedule component
  - [x] 8.1 Create `frontend/src/features/sales/components/AutoNudgeSchedule.tsx`
    - Copy and adapt from `scaffold/AutoNudgeSchedule.tsx`
    - Render rows for day 0, 2, 5, 8 (from `NUDGE_CADENCE_DAYS`) plus weekly loop sentinel
    - Row states computed from `estimateSentAt`: `done` (past), `next` (first upcoming), `future`, `loop`
    - Exactly one row is `next` at a time
    - When `paused`: strike through future/loop rows, show "Paused. Resume to continue auto-follow-up." banner
    - All `data-testid` attributes: `auto-nudge-schedule`, `auto-nudge-row-{dayOffset}` with `data-state`, `auto-nudge-paused-banner`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 16.4_

  - [x] 8.2 Write unit tests for AutoNudgeSchedule — `frontend/src/features/sales/components/AutoNudgeSchedule.test.tsx`
    - Test 5 rows render (4 cadence + 1 loop)
    - Test exactly one row has `next` state given a mock `estimateSentAt`
    - Test all rows before `next` have `done` state
    - Test paused state shows banner and strikes through future/loop rows
    - Test loop row always has `loop` state
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [x] 8.3 Write property-based test for computeSteps — `frontend/src/features/sales/components/AutoNudgeSchedule.test.tsx`
    - **Property 8: computeSteps Nudge State Assignment**
    - Use fast-check to generate random `estimateSentAt` timestamps 0–30 days ago
    - Verify: (a) at most one step has `state === 'next'`, (b) all steps with `dayOffset < daysSinceEstimateSent` have `state === 'done'`, (c) steps after `next` have `state === 'future'`, (d) last step always has `state === 'loop'` and `dayOffset === -1`, (e) states form valid sequence: done* → next? → future* → loop
    - Minimum 100 iterations
    - **Validates: Requirements 11.2, 11.3, 11.4, 11.5**

- [x] 9. Create ActivityStrip component
  - [x] 9.1 Create `frontend/src/features/sales/components/ActivityStrip.tsx`
    - Copy and adapt from `scaffold/ActivityStrip.tsx`
    - Render horizontal flex-wrap row of event chips with glyphs and `·` separators
    - Tone classes: `done` → `text-slate-600`, `wait` → `text-amber-700 font-medium`, `neutral` → `text-slate-500`
    - Leading glyph per event kind from GLYPH mapping
    - Return `null` when events array is empty
    - All `data-testid` attributes: `activity-strip`, `activity-event-{kind}`
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 16.5_

  - [x] 9.2 Write unit tests for ActivityStrip — `frontend/src/features/sales/components/ActivityStrip.test.tsx`
    - Test returns null for empty events
    - Test renders correct glyphs per event kind
    - Test tone classes applied correctly (done/wait/neutral)
    - Test `·` separators between events
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 10. Checkpoint — Ensure all tests pass
  - Run `cd frontend && npx vitest --run` and verify zero failures
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Integrate walkthrough into SalesDetail
  - [x] 11.1 Wire StageStepper + NowCard + ActivityStrip into `SalesDetail.tsx`
    - Insert StageStepper between header card and NowCard
    - Insert NowCard between StageStepper and ActivityStrip
    - Insert ActivityStrip between NowCard and DocumentsSection
    - Remove `StatusActionButton` from the header card actions row — primary action lives only inside NowCard
    - Compute `nowContent(inputs)` from entry state and pass to NowCard
    - Build `ActivityEvent[]` from entry fields for ActivityStrip
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [x] 11.2 Implement `closed_lost` banner
    - When `status === 'closed_lost'`: hide StageStepper, NowCard, and ActivityStrip entirely
    - Show slate banner: "Closed Lost — {closed_reason}. No further actions." above DocumentsSection
    - _Requirements: 13.5_

  - [x] 11.3 Wire click-handler `handleNowAction` for all `NowActionId` values
    - `schedule_visit` → open schedule modal
    - `send_estimate_email` → call send estimate mutation
    - `convert_to_job` → open convert-to-job modal
    - `view_job` → navigate to `/jobs/{entry.job_id}`
    - `view_customer` → navigate to `/customers/{entry.customer_id}`
    - `jump_to_schedule` → navigate to `/schedule`
    - `mark_declined` → open decline confirmation modal
    - `skip_advance` → advance entry to `pending_approval`
    - `mark_approved_manual` → advance entry to `send_contract`
    - `text_confirmation`, `resend_estimate`, `pause_nudges` → sonner toast "Not wired yet — TODO" with `TODO(backend)` comment
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9, 15.10_

  - [x] 11.4 Wire dropzone file handling and Week-Of picker state
    - `onFileDrop` handles estimate and agreement PDF uploads
    - `weekOfValue` / `onWeekOfChange` persists to `localStorage` keyed by entry ID
    - Pass `estimateSentAt` and `nudgesPaused` to NowCard for AutoNudgeSchedule
    - _Requirements: 10.3, 14.4, 17.6_

  - [x] 11.5 Write integration tests for SalesDetail walkthrough layout — `frontend/src/features/sales/components/SalesDetail.test.tsx`
    - Test StageStepper + NowCard + ActivityStrip render between header and documents
    - Test `closed_lost` shows banner, hides walkthrough components
    - Test StatusActionButton is NOT in the header card
    - Test each NowActionId triggers correct mutation or navigation
    - Test stubbed actions show "Not wired yet — TODO" toast
    - Test all 7 NowCard variations render correctly in context
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 15.9, 15.10_

- [x] 12. Update export barrels
  - [x] 12.1 Update `frontend/src/features/sales/components/index.ts`
    - Add exports for `AgeChip`, `StageStepper`, `NowCard`, `AutoNudgeSchedule`, `ActivityStrip`
    - Preserve all existing exports
    - _Requirements: 1.4_

  - [x] 12.2 Update `frontend/src/features/sales/hooks/index.ts` if needed
    - Ensure `useStageAge` and `countStuck` are accessible
    - Preserve all existing exports
    - _Requirements: 1.4_

- [x] 13. Checkpoint — Ensure all tests pass
  - Run `cd frontend && npx vitest --run` and verify zero failures
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Write Pipeline List tests
  - [x] 14.1 Write unit tests for PipelineList — `frontend/src/features/sales/components/PipelineList.test.tsx`
    - Test 4 summary cards render with correct values
    - Test clicking Needs Follow-Up toggles stuck filter
    - Test both statusFilter and stuckFilter active simultaneously
    - Test Clear removes all filters
    - Test row click navigates to `/sales/{id}`
    - Test no action button for `closed_lost` entries
    - Test address tooltip on customer name (no Address column)
    - Test age chips show correct bucket per row
    - Test compact action button labels match stage
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.5, 5.8, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 15. Verify no new dependencies and no backend changes
  - Confirm no new entries in `frontend/package.json` dependencies
  - Confirm `useSalesPipeline` hook and `salesPipelineApi` module are unchanged
  - Confirm no database migrations or API schema changes
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [x] 16. TypeScript type checking pass
  - Run `cd frontend && npm run typecheck` and ensure zero errors
  - Fix any type errors introduced by the new components
  - _Requirements: 17.1_

- [x] 17. Lint pass
  - Run `cd frontend && npm run lint` and ensure zero violations
  - Fix any lint issues in new and modified files
  - _Requirements: 17.1_

- [x] 18. Full test suite pass
  - Run `cd frontend && npm test` and ensure zero failures across all test files
  - Verify all 9 property-based tests pass with 100+ iterations each
  - Verify all unit tests and integration tests pass
  - _Requirements: All_

- [x] 19. Final checkpoint — Ensure all tests pass
  - Run `cd frontend && npm test`, `cd frontend && npm run typecheck`, and `cd frontend && npm run lint`
  - All three commands must exit with zero errors
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are REQUIRED — none are optional
- Each task references specific requirements for traceability
- Scaffold files in `feature-developments/handoff-stage-walkthrough-and-pipeline/scaffold/` provide the implementation source
- Property-based tests use `fast-check` with minimum 100 iterations per property
- Checkpoints ensure incremental validation at key milestones
- Stubbed backend endpoints use sonner toast "Not wired yet — TODO" with `TODO(backend)` comments
- `localStorage` is used for Week-Of persistence and follow-up delta (v1); `TODO(backend)` comments document future column additions
