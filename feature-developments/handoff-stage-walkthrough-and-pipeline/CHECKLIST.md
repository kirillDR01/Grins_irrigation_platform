# Pull-Request Checklist — Stage Walkthrough + Pipeline List

Every box below must be checked before merge. Copy this into the PR description and tick as you go.

## Types & data

- [ ] `frontend/src/features/sales/types/pipeline.ts` merged with additions from `data-shapes.ts` — existing exports unchanged.
- [ ] `SALES_STATUS_CONFIG.send_contract.label` changed to `"Convert to Job"`.
- [ ] `SALES_STATUS_CONFIG.send_contract.action` changed to `"Convert to Job"`.
- [ ] `AGE_THRESHOLDS`, `STAGES`, `STAGE_INDEX`, `statusToStageKey`, `NUDGE_CADENCE_DAYS` exported.
- [ ] No DB migrations required; no API schema changes.

## Pipeline List

- [ ] `SalesPipeline.tsx` replaced with scaffold; renders under `/sales`.
- [ ] `AgeChip` component added; renders on every row except `closed_*`.
- [ ] `useStageAge` hook added.
- [ ] `pending_approval` rows use 4/10 thresholds (not 3/7).
- [ ] Clicking "Needs Follow-Up" card toggles stuck-only filter; indicator pill renders.
- [ ] Clicking a status summary card preserves the stuck filter (and vice versa).
- [ ] Address column removed; tooltip on customer name shows address.
- [ ] Row action label matches stage per the table in SPEC §7.
- [ ] Every element in SPEC §9 has its `data-testid`.
- [ ] Existing pagination works unchanged.
- [ ] Visual parity with `reference/screenshots/02-pipeline-list.png` (≈95%).

## Stage Walkthrough

- [ ] `StageStepper`, `NowCard`, `ActivityStrip`, `AutoNudgeSchedule` components added.
- [ ] `nowContent()` pure function added with a unit-test snapshot for each of the 7 variations.
- [ ] `StatusActionButton` removed from the `SalesDetail` header card; primary action lives inside `NowCard`.
- [ ] `pending_approval` step shows dashed amber waiting state; no other stage does.
- [ ] `waiting` animation disabled under `prefers-reduced-motion`.
- [ ] Stepper "⋯ change stage manually" opens dropdown with all statuses.
- [ ] Stepper "✕ Mark Lost" opens a modal that requires `closed_reason` (required textarea).
- [ ] `closed_lost`: stepper + Now card + activity are hidden; slate banner is shown instead.
- [ ] Dropzone accepts only `application/pdf`; non-PDF drop shows sonner toast.
- [ ] Dropzone drag-over state changes border colour.
- [ ] `AutoNudgeSchedule` renders exactly one `next` row given a mock `estimateSentAt`.
- [ ] `paused` state strikes through future rows + shows banner.
- [ ] Week-Of picker renders 5 default chips starting from current week (Monday anchor) + "+ pick date…" chip.
- [ ] Selected Week-Of persists to `localStorage` keyed by `entryId` (v1) — TODO(backend) for `target_week_of` column.
- [ ] Click-handlers wired per SPEC §8. Missing endpoints stubbed with sonner toast + TODO(backend).
- [ ] All test IDs from SPEC §3–§6 present.
- [ ] Visual parity with `reference/screenshots/03-walk-*.png` for all 7 variations (≈95%).

## Tests

- [ ] `PipelineList.test.tsx` — renders with fixtures, age chips show correct bucket, stuck filter toggles.
- [ ] `StageStepper.test.tsx` — renders each stage, step states are correct.
- [ ] `NowCard.test.tsx` — snapshot for each `nowContent()` variation.
- [ ] `AutoNudgeSchedule.test.tsx` — computes row states correctly from mock `estimateSentAt`.
- [ ] `useStageAge.test.ts` — threshold boundaries tested for every stage.
- [ ] `npm test` passes locally.
- [ ] `npm run typecheck` passes.
- [ ] `npm run lint` passes.

## Accessibility & polish

- [ ] `AgeChip` has `aria-label` including bucket + days + stage.
- [ ] All buttons have visible text or `aria-label`.
- [ ] `NowCard` title uses `text-wrap: pretty`.
- [ ] Tooltips respect keyboard focus (shadcn default).
- [ ] No new deps added.

## Docs

- [ ] Screenshots of the new Pipeline List and the 7 walkthrough variations attached to PR.
- [ ] Any deferred backend tickets filed with links in the PR description (`stage_entered_at`, `target_week_of`, nudge-pause endpoint, etc.).
