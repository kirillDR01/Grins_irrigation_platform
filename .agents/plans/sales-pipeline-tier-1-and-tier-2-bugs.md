# Feature: Sales Pipeline Tier 1 + Tier 2 Bug Fixes

The following plan should be complete, but it is important to validate documentation
and codebase patterns and task sanity before starting implementation. Pay special
attention to naming of existing utils, types, hooks, and models — import from the
right files (e.g. `useCustomer` is exported from `@/features/customers/hooks` as
`useCustomerDetail` per `SalesDetail.tsx:23`).

## Feature Description

Resolve all nine **Tier 1 (Critical)** and **Tier 2 (High)** bugs from the
2026-04-26 Sales Pipeline Bug Hunt audit at
`feature-developments/sales pipeline bug hunt/`. The audit identified the
`handoff-stage-walkthrough-pipeline` slice as functionally regressed in nine
places after recent merges: a misnamed boolean (`hasEmail`) lies about whether a
customer has an email, the `pending_approval` AutoNudgeSchedule never renders,
the pipeline-list row buttons have no `onClick`, two NowCard / StageStepper
affordances are visual-only stubs, the `mark_declined` and `view_job`
flows skip required modals or navigate to the wrong id, dropzone uploads
silently no-op despite a working hook already existing, and `Mark Lost`
remains live on `closed_won` and toasts an error. None of these require new
backend feature work — they are wiring, dead-state cleanup, and tying existing
hooks to existing buttons.

## User Story

**As an** admin operating the sales pipeline,
**I want** the inline NowCard, StageStepper, and pipeline-list controls to do
exactly what their labels say (or be removed when they cannot),
**so that** I can move entries through Plan → Sign → Close without bouncing to
other tabs, mis-emailing customers who have no email on file, or staring at
buttons that quietly do nothing.

## Problem Statement

Nine concrete defects let buttons lie to the user, broke a required Req 11
sub-tree (auto-nudge schedule), and hid a spec-required decline-reason capture
flow. Several of them already have working backend endpoints and frontend
hooks — only the wiring is missing. The two terminal-state regressions (Mark
Lost on `closed_won`, View Job → SignWell doc id) actively confuse admins on
real records and produce 422 / 404 outcomes.

## Solution Statement

A single coordinated frontend pass that:

1. Sources `hasEmail` from the linked Customer's `email` field (also exposing
   `customer_email` on `SalesEntryResponse` so the FE doesn't need a second
   query for list rows).
2. Wires the pipeline-list row action button to navigate to detail; stubs the
   dismiss `✕` button to a `toast.info` until a backend endpoint exists.
3. Passes `estimateSentAt` (`entry.updated_at ?? entry.created_at`) and
   `nudgesPaused={false}` placeholders into `NowCard` so `AutoNudgeSchedule`
   renders.
4. Removes the dead `⋯ change stage manually` button + its dead state — the
   header `Change stage…` Select already covers the use case.
5. Wraps `+ pick date…` in a shadcn `Popover + Calendar`.
6. Replaces the dropzone TODO stub with a real `useUploadSalesDocument`
   `mutateAsync` call.
7. Drops the wrong `signwell_document_id` branch from `view_job`; falls
   through to `/jobs` until `entry.job_id` is exposed.
8. Hides `StageStepper` for `closed_won` (mirrors the `closed_lost` path).
9. Adds a small decline-reason `Dialog` that captures `closedReason` before
   `markLost.mutate`.

The change is purely additive on the backend (one optional
`customer_email` field on `SalesEntryResponse`) — no migrations, no new
endpoints, no breaking schema change.

## Feature Metadata

**Feature Type**: Bug Fix (bundled — 9 defects across 1 slice)
**Estimated Complexity**: Medium (frontend-heavy, wide blast radius across
the sales feature slice; one tiny backend schema/serializer addition)
**Primary Systems Affected**:
- `frontend/src/features/sales/components/SalesDetail.tsx` (8 of 9 bugs touch this)
- `frontend/src/features/sales/components/SalesPipeline.tsx` (Bug #3)
- `frontend/src/features/sales/components/NowCard.tsx` (Bug #4)
- `frontend/src/features/sales/components/StageStepper.tsx` (Bug #5 cleanup)
- `src/grins_platform/schemas/sales_pipeline.py` + `api/v1/sales_pipeline.py`
  (NEW-A — expose `customer_email` on response)
**Dependencies**: None new. Uses existing
`@/components/ui/{popover,calendar,dialog,textarea,label}`,
`useUploadSalesDocument`, `useMarkSalesLost`, `useCustomerDetail`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Source files to modify

- `frontend/src/features/sales/components/SalesDetail.tsx` — host component;
  every Tier 1+2 bug except #3, #4, #5-cleanup, and #10 lands here
  - Lines 56–71: hooks instantiation incl. `useCustomerDetail(entry?.customer_id ?? '')`
    at `:69` — this is where `salesCustomer` already lives
  - Lines 110–114: `_showOverrideSelect` dead state (Bug #5) and
    `scheduleModalOpen` working pattern
  - Lines 156–231: `handleNowAction` switch — entry point for NEW-B convert/decline
    modals, view_job (#7), and stub catch-all (#8 stub neighbour)
  - Lines 234–240: `handleFileDrop` TODO (Bug #8)
  - Lines 244–245: `hasEstimateDoc` / `hasSignedAgreement` — keep this
    pattern for derived doc booleans
  - Line 279: `const hasEmail = !!entry.customer_name;` — **the NEW-A bug**
  - Line 340: `hasCustomerEmail = hasEmail` — alias to delete
  - Line 511–518: email-sign button (`disabled={... || !hasEmail || ...}`)
  - Lines 533–558: `isClosedLost` branch — extend to `isTerminal` for Bug #11
  - Lines 561–570: NowCard host — missing `estimateSentAt` / `nudgesPaused` (Bug #6)

- `frontend/src/features/sales/components/SalesPipeline.tsx` (lines
  306–328) — pipeline-list row action `<Button>` and dismiss `<Button>` with
  `// TODO(wiring)` and `// TODO(backend)` comments (Bug #3)

- `frontend/src/features/sales/components/NowCard.tsx`
  - Lines 27–36: `NowCardProps` already declares `estimateSentAt?: string;
    nudgesPaused?: boolean;` — host just needs to pass them
  - Lines 86–88: gate `content.showNudgeSchedule && estimateSentAt` (Bug #6)
  - Lines 248–292: `WeekOfPicker` component containing the unwired
    `+ pick date…` button at `:278–285` (Bug #4)

- `frontend/src/features/sales/components/StageStepper.tsx`
  - Lines 7–13: `StageStepperProps` — drop `onOverrideClick` if Bug #5 fix
    deletes the footer button
  - Lines 67–76: the `change stage manually` footer button (Bug #5 — remove)

#### Reference patterns to mirror (do NOT modify, but READ)

- `frontend/src/features/sales/components/StatusActionButton.tsx`
  - Lines 41–53: `useState` for `showForceConfirm`, `showLostConfirm` —
    decline-reason modal state pattern for **NEW-B**
  - Lines 100–127: `handleAdvance` showing axios error parsing →
    selective dialog open vs `toast.error` — exact pattern for the future
    NEW-C plan; NEW-B can mirror the modal pattern only
  - Lines 213–254: `<Dialog>` component for force convert / mark lost —
    **exact UI pattern to reuse for NEW-B** (Mark Declined modal)
  - Lines 232–254: `<Dialog>` for `showLostConfirm` — already includes
    "cannot be undone" copy and destructive variant

- `frontend/src/features/sales/components/ScheduleVisitModal/` — modern
  modal-from-host pattern; SalesDetail already opens this via
  `setScheduleModalOpen(true)` at `:160` and renders the modal at `:592–597`.
  The decline-reason modal for NEW-B should follow this hosting pattern
  rather than embedding the `Dialog` inline like StatusActionButton does.

- `frontend/src/features/sales/hooks/useSalesPipeline.ts`
  - Lines 90–104: `useMarkSalesLost` — accepts `closedReason` string;
    NEW-B passes the textarea value here
  - Lines 130–148: `useUploadSalesDocument` — already accepts
    `{ customerId, file, documentType }`. Bug #8 wires this in.

- `frontend/src/features/customers/hooks/index.ts` (re-exports
  `useCustomer` as `useCustomerDetail` — see import at `SalesDetail.tsx:23`)
- `frontend/src/features/customers/types/index.ts:49` — `email: string | null;`
  on `Customer` confirms the FE field name for NEW-A's local fix

- `src/grins_platform/models/customer.py` line 78 —
  `email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)`
  is the source of truth for the durable backend fix
- `src/grins_platform/api/v1/sales_pipeline.py` lines 142–160
  (`_entry_to_response`) — denormalisation site to add `customer_email`
- `src/grins_platform/schemas/sales_pipeline.py` lines 32–58
  (`SalesEntryResponse`) — schema field to add

#### Test files to read for patterns

- `frontend/src/features/sales/components/SalesDetail.test.tsx` —
  existing host tests; place new NEW-A, Bug #6, Bug #11 tests here
- `frontend/src/features/sales/components/NowCard.test.tsx` — Bug #4
  popover test goes here
- `frontend/src/features/sales/components/StageStepper.test.tsx` — Bug #5
  removal regression test
- `frontend/src/features/sales/components/PipelineList.test.tsx` — Bug #3
  row-action-button onClick test
- `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py` —
  unit-test pattern for the NEW-A schema serializer addition (look at
  `test_send_estimate_without_doc_now_advances` line 144 for assertion style)

### New Files to Create

- `frontend/src/features/sales/components/MarkDeclinedDialog.tsx` —
  small wrapper around shadcn `<Dialog>` with a labelled `<Textarea>` for
  `closed_reason`. Mirrors `StatusActionButton.tsx:232–254` Mark Lost dialog
  but with a required reason field.
- `frontend/src/features/sales/components/MarkDeclinedDialog.test.tsx` —
  Vitest test for renders empty, validates required reason, fires
  `onConfirm(reason)`.

> No new backend files are required. The single backend change is one
> property on an existing schema and one assignment in
> `_entry_to_response`.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [shadcn Popover](https://ui.shadcn.com/docs/components/popover) —
  `<Popover><PopoverTrigger asChild><button…/></PopoverTrigger>
  <PopoverContent>…</PopoverContent></Popover>`. Already installed at
  `@/components/ui/popover` (used elsewhere in the codebase — search
  `import.*from.*"@/components/ui/popover"` to confirm prior usage).
  - **Why**: Bug #4 wraps the existing `+ pick date…` button in this
    primitive. Don't roll your own.
- [shadcn Calendar](https://ui.shadcn.com/docs/components/calendar) —
  built on `react-day-picker` (v9.13 per `frontend/package.json:53`).
  Use `mode="single"`, `selected`, `onSelect`. Convert selected `Date` to
  the same `"MMM D"` format already returned by
  `NowCard.generateWeeks` (lines 294–306) so the chip label stays
  consistent.
  - **Why**: Bug #4 needs a calendar inside the Popover.
- [shadcn Dialog](https://ui.shadcn.com/docs/components/dialog) — used
  throughout `StatusActionButton.tsx`. Same primitive for NEW-B.
- [TanStack Query mutation `onError`](https://tanstack.com/query/latest/docs/framework/react/reference/useMutation)
  — read `error` arg shape to align with `StatusActionButton.handleAdvance`
  (axios error parsing at `:113–122`).
  - **Why**: NEW-B writes a parallel `onError` for `markLost` after the
    decline modal confirms.
- [react-day-picker v9 selection modes](https://daypicker.dev/docs/selection-modes)
  — note v9 changed `defaultSelected` → `selected` semantics.
  - **Why**: Avoid common v8→v9 API drift.
- [date-fns `format`](https://date-fns.org/v4/docs/format) — already at
  `^4.1.0` per `frontend/package.json:49`. Use `format(date, 'MMM d')`
  to match the existing `Intl.DateTimeFormat({ month: 'short', day: 'numeric' })`
  output of `generateWeeks`.

### Patterns to Follow

(Drawn from `.kiro/steering/{code-standards,frontend-patterns,frontend-testing,
api-patterns,structure,tech,agent-browser,vertical-slice-setup-guide,
spec-quality-gates,spec-testing-standards,parallel-execution,
pre-implementation-analysis}.md` — the user explicitly excluded
`kiro-cli-reference.md`, `devlog-rules.md`, `auto-devlog.md`,
`knowledge-management.md`, and `e2e-testing-skill.md` from scope.)

#### Naming conventions (from `code-standards.md`, `structure.md`, `tech.md`)

- Frontend components: `PascalCase.tsx` co-located with `.test.tsx`
- Hooks: `use{Name}.ts`
- API: `{feature}Api.ts`
- Backend: `snake_case.py`, tests `test_{module}.py`
- `data-testid` (per `frontend-patterns.md` line 98 + `spec-quality-gates.md`):
  - Pages: `{feature}-page` (e.g. `sales-detail-page`)
  - Tables: `{feature}-table`
  - Rows: `pipeline-row-{id}`
  - Forms: `{feature}-form`
  - Buttons: `{action}-{feature}-btn` (e.g. `confirm-mark-declined-btn`)
  - Dialog: `{feature}-dialog` (new — `mark-declined-dialog`)

#### Frontend component pattern (from `frontend-patterns.md`)

- Forms use **React Hook Form + Zod**. The decline-reason dialog is small
  enough to bypass RHF — a single controlled `<Textarea>` is acceptable; do
  not introduce RHF for one field. (See `StatusActionButton.tsx:48–53`
  controlled state pattern as precedent in this slice.)
- TanStack Query: `pipelineKeys` factory at `useSalesPipeline.ts:12–28`.
  After NEW-A backend change, no new key — `useSalesEntry` already returns
  the same response shape with the new field added.
- `cn()` for conditional classes (per `frontend-patterns.md:94`).
- Error handling: `toast.error(title, { description: getErrorMessage(err) })`
  using `getErrorMessage` from `@/core/api` (see `SalesDetail.tsx:307`).

#### Logging pattern — backend (`code-standards.md`, `api-patterns.md`)

- Schema/response change is data-only — no log additions needed.
- If you choose to log on the schema-extension path, use the existing
  `_ep` `LoggerMixin` instance at `api/v1/sales_pipeline.py:48`.

#### Testing pattern (from `frontend-testing.md`, `spec-testing-standards.md`)

- Vitest + React Testing Library, wrap in `<QueryProvider>`
- Co-located `.test.tsx`
- Coverage targets: components 80%+, hooks 85%+
- For Bug #6 specifically, assert `data-testid="auto-nudge-schedule"`
  appears (or whatever testid `AutoNudgeSchedule` already exposes — confirm
  by reading `AutoNudgeSchedule.tsx`).

#### agent-browser E2E pattern (`agent-browser.md`,
`spec-quality-gates.md`)

```bash
agent-browser --session sales-bugs open "$DEV_URL/sales/$ENTRY_ID"
agent-browser snapshot -i               # get refs
agent-browser is enabled "[data-testid='email-sign-btn']"  # NEW-A: must be false when no email
agent-browser is visible "[data-testid='auto-nudge-schedule']"  # Bug #6
agent-browser click "[data-testid='now-card-weekof-pick']"  # Bug #4
agent-browser is visible "[role='dialog']"
```

#### Parallel execution (`parallel-execution.md`)

The 9 fixes split into three independent batches — see Phase plan below.

#### Pre-implementation analysis (`pre-implementation-analysis.md`)

Independent groups suitable for parallel sub-agents (frontend-only, no
shared file edits):

- **Group A**: NEW-A backend + frontend (sales_pipeline.py schema + serializer + SalesDetail.tsx:279/340/512)
- **Group B**: Bug #3 (SalesPipeline.tsx)
- **Group C**: Bug #4 (NowCard.tsx WeekOfPicker)
- **Group D**: Bug #5 (StageStepper.tsx + SalesDetail.tsx:111/318/546 dead state cleanup)

Bugs #6, #7, #8, #11, NEW-B all touch `SalesDetail.tsx` and must run
sequentially after Group A merges (which also edits SalesDetail.tsx).

---

## IMPLEMENTATION PLAN

### Phase 1: Backend foundation (NEW-A durable fix)

Expose `customer_email` on the `SalesEntryResponse` so the frontend has a
single field to read and the row list (where `salesCustomer` is not
fetched) is also correct.

**Tasks:**

- Add `customer_email: Optional[str] = None` to `SalesEntryResponse`
- Set it in `_entry_to_response` from `customer.email`
- Extend the existing unit test for the response serializer (or add one)
  to assert the new field round-trips

### Phase 2: Frontend independent fixes (parallel)

Each of these can run as a separate subagent — they touch disjoint files.

**Tasks (parallel):**

- **NEW-A FE**: Source `hasEmail` from `entry.customer_email ?? salesCustomer?.email` in `SalesDetail.tsx`; drop the `hasCustomerEmail = hasEmail` alias; pass the same value to `nowContent({ hasCustomerEmail })`.
- **Bug #3**: Wire pipeline-list row buttons.
- **Bug #4**: Wrap `+ pick date…` in `<Popover>` + `<Calendar>`; convert selection to `"MMM d"` using `date-fns.format`.
- **Bug #5**: Delete `⋯ change stage manually` button from `StageStepper`; drop `onOverrideClick` from props; delete `_showOverrideSelect`, `setShowOverrideSelect`, `onOverrideClick={...}` from `SalesDetail.tsx`.

### Phase 3: Frontend SalesDetail.tsx serial fixes

Bugs #6, #7, #8, #11, NEW-B all edit `SalesDetail.tsx` — run sequentially
to avoid merge conflicts.

**Tasks (in order):**

- **Bug #6**: Pass `estimateSentAt={entry.updated_at ?? entry.created_at}` and `nudgesPaused={false}` to `<NowCard>`.
- **Bug #7**: Drop `signwell_document_id` branch from `view_job`. (When `entry.job_id` is exposed in a future change, restore the conditional.)
- **Bug #8**: Replace `handleFileDrop` stub with `useUploadSalesDocument.mutateAsync`; toast success; refetch documents query.
- **Bug #11**: Replace `isClosedLost` with `isTerminal = ['closed_won','closed_lost'].includes(entry.status)` for the StageStepper hide branch (mirrors top-of-component `isTerminal` line 278). Update the banner copy to handle won path or render a different banner for `closed_won`.
- **NEW-B**: Create `MarkDeclinedDialog`, host it from `SalesDetail.tsx`, replace the `mark_declined` switch case with `setMarkDeclinedOpen(true)`.

### Phase 4: Tests

**Tasks:**

- Component test for each modified component
- Update `SalesDetail.test.tsx` for NEW-A, Bug #6, Bug #11, NEW-B
- New `MarkDeclinedDialog.test.tsx`
- Backend unit test for the serializer (`customer_email` round-trips)

### Phase 5: agent-browser E2E validation

Run end-to-end against the Vercel dev deployment using the entry IDs from
the audit (`Testing Viktor` for the no-email path, `Brooke Jore` for full
progression). See "Manual Validation" below.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic
and independently testable.

### 1. UPDATE `src/grins_platform/schemas/sales_pipeline.py`

- **IMPLEMENT**: Add `customer_email: Optional[str] = None` to
  `SalesEntryResponse` directly below `customer_phone` (line 53), grouped
  with the other denormalised fields.
- **PATTERN**: Mirror `customer_phone: Optional[str] = None` at
  `schemas/sales_pipeline.py:53`.
- **IMPORTS**: None new (`Optional` already imported).
- **GOTCHA**: Schema must remain `model_config = ConfigDict(from_attributes=True)`-compatible. Default `None` keeps backward-compat for any test fixture that constructs the response by hand.
- **VALIDATE**: `uv run ruff check src/grins_platform/schemas/sales_pipeline.py && uv run mypy src/grins_platform/schemas/sales_pipeline.py && uv run pyright src/grins_platform/schemas/sales_pipeline.py`

### 2. UPDATE `src/grins_platform/api/v1/sales_pipeline.py`

- **IMPLEMENT**: In `_entry_to_response` (lines 142–160), set
  `resp.customer_email = customer.email if customer else None` adjacent to
  the existing `resp.customer_phone = customer_phone` assignment.
- **PATTERN**: Mirror `resp.customer_phone = customer_phone` at line 156.
- **IMPORTS**: None new.
- **GOTCHA**: `customer.email` is `Optional[str]` per
  `models/customer.py:78` — guard with the `if customer else None` ternary
  consistent with how `customer_phone` is derived at line 149.
- **VALIDATE**: `uv run ruff check src/grins_platform/api/v1/sales_pipeline.py && uv run mypy src/grins_platform/api/v1/sales_pipeline.py && uv run pyright src/grins_platform/api/v1/sales_pipeline.py`

### 3. UPDATE backend serializer test

- **IMPLEMENT**: Create a brand-new unit test in
  `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py`
  named `test_entry_to_response_includes_customer_email`. There are
  currently NO tests covering `_entry_to_response` (verified via grep) —
  this test introduces the first one.
  Assert that a `SalesEntry` with a `Customer` whose `email='x@y.z'`
  serialises to a `SalesEntryResponse` whose `customer_email == 'x@y.z'`,
  and an entry whose customer has `email=None` serialises to
  `customer_email=None`.
- **PATTERN**: Build the `Customer` and `SalesEntry` instances in-memory
  (no DB needed — `_entry_to_response` is pure given the loaded
  relationship). Look for `Customer(...)` and `SalesEntry(...)` direct
  constructions elsewhere in `src/grins_platform/tests/unit/` for the
  exact required-field set.
- **IMPORTS**: From `grins_platform.api.v1.sales_pipeline import _entry_to_response` (private helper — `SLF001` is allowed in test files per `pyproject.toml:267–278`).
- **GOTCHA**: `_entry_to_response` is sync, but reads
  `entry.customer.email`. Ensure the relationship is materialised on the
  fixture (lazy="selectin" should auto-load when constructed in-memory; if not, set `entry.customer = customer_obj` directly).
- **VALIDATE**: `uv run pytest -m unit src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py -v`

### 4. UPDATE `frontend/src/features/sales/types/pipeline.ts`

- **IMPLEMENT**: Add `customer_email: string | null;` to the `SalesEntry`
  TypeScript interface adjacent to `customer_phone: string | null;`.
- **PATTERN**: Read the file first to find the exact location of
  `customer_phone` in the TS type and mirror.
- **IMPORTS**: None.
- **GOTCHA**: The TS type must match the Pydantic shape; use `string | null` (not `?: string`) to match the explicit `Optional[str] = None` Python pattern.
- **VALIDATE**: `cd frontend && npm run typecheck`

### 5. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — NEW-A fix

- **IMPLEMENT**:
  - Replace line 279 with: `const hasEmail = !!(entry.customer_email ?? salesCustomer?.email);`
  - Delete line 340 (`const hasCustomerEmail = hasEmail;`) and update the
    `nowContent({...})` call (lines 343–350) to use `hasCustomerEmail: hasEmail` directly.
- **PATTERN**: `salesCustomer?.email` — `salesCustomer` is already in
  scope from `useCustomerDetail(entry?.customer_id ?? '')` at line 69.
- **IMPORTS**: None new.
- **GOTCHA**:
  1. Keep the `entry.customer_email ?? salesCustomer?.email` order so
     that list views (where `useCustomerDetail` may not have fetched yet)
     still get the right value from the API response field once Phase 1
     ships.
  2. `entry.customer_email` is `string | null` — the `??` operator treats
     `null` as fallthrough, which is what we want.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test SalesDetail`

### 6. UPDATE `frontend/src/features/sales/components/SalesPipeline.tsx` — Bug #3 fix

- **IMPLEMENT**: Replace the unwired action button at lines 308–316 with:
  ```tsx
  <Button
    size="sm"
    variant={entry.status === 'closed_won' ? 'ghost' : 'default'}
    data-testid={`pipeline-row-action-${entry.id}`}
    onClick={(e) => { e.stopPropagation(); onRowClick(entry); }}
  >
    {actionLabel}
  </Button>
  ```
  Replace the dismiss button at lines 318–326 with:
  ```tsx
  <Button
    size="icon"
    variant="ghost"
    className="h-7 w-7"
    data-testid={`pipeline-row-dismiss-${entry.id}`}
    onClick={(e) => {
      e.stopPropagation();
      toast.info('Dismiss not wired yet — TODO(backend)');
    }}
  >
    <X className="h-3.5 w-3.5 text-slate-400" />
  </Button>
  ```
- **PATTERN**: `onRowClick(entry)` is the same callback the row uses at
  line 250 — wiring action button to detail navigation honours
  `README.md` "Option A" recommendation. `toast.info` import already
  present at top of `SalesPipeline.tsx` (verify).
- **IMPORTS**: `toast` is NOT currently imported in `SalesPipeline.tsx`
  (verified via grep). **You must add** `import { toast } from 'sonner';`
  at the top of the file alongside the existing imports.
- **GOTCHA**: The `<TableCell>` already has
  `onClick={e => e.stopPropagation()}` at line 306. Buttons inside still
  need their own `e.stopPropagation()` because the cell handler runs at
  capture, but the row click handler runs on the row's `<tr>`. Keep the
  per-button `e.stopPropagation()` to be safe.
- **VALIDATE**: `cd frontend && npm test PipelineList -- --run`

### 7. UPDATE `frontend/src/features/sales/components/NowCard.tsx` — Bug #4 fix

- **IMPLEMENT**: In the `WeekOfPicker` component (lines 248–292), replace
  the unwired `<button … + pick date…>` at lines 278–285 with:
  ```tsx
  <Popover>
    <PopoverTrigger asChild>
      <button
        type="button"
        data-testid="now-card-weekof-pick"
        className="text-xs px-2.5 py-1 rounded-full border border-dashed border-slate-300 text-slate-500 hover:bg-slate-50"
      >
        + pick date…
      </button>
    </PopoverTrigger>
    <PopoverContent className="w-auto p-0" align="start">
      <Calendar
        mode="single"
        selected={undefined}
        onSelect={(d) => {
          if (d) onChange?.(format(d, 'MMM d'));
        }}
      />
    </PopoverContent>
  </Popover>
  ```
- **PATTERN**: shadcn Popover + Calendar pattern (search the codebase for
  prior `Popover.*Calendar` usage to copy import style).
- **IMPORTS**: Add at top of `NowCard.tsx`:
  ```tsx
  import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
  import { Calendar } from '@/components/ui/calendar';
  import { format } from 'date-fns';
  ```
- **GOTCHA**: `format(d, 'MMM d')` produces "Apr 26"-style strings
  matching `generateWeeks(n)`'s `Intl.DateTimeFormat({ month: 'short', day: 'numeric' })` output (line 300). If you use `'MMM D'` (capital D) you'll get day-of-year — this is a common mistake.
- **VALIDATE**: `cd frontend && npm test NowCard -- --run`

### 8. UPDATE `frontend/src/features/sales/components/StageStepper.tsx` — Bug #5 cleanup (part 1)

- **IMPLEMENT**:
  - Remove the `onOverrideClick: () => void;` prop from
    `StageStepperProps` (lines 7–13).
  - Remove the `<button … data-testid="stage-stepper-override">…
    change stage manually</button>` at lines 68–76.
  - Replace the now-empty footer-left half with a spacer
    (`<div />`) so the `mark-lost` button stays right-aligned.
- **PATTERN**: Header `Change stage…` Select at `SalesDetail.tsx:427–438`
  already provides this functionality — duplicate UI removal is the right
  fix per `code-standards.md` "no dead code" implicit rule.
- **IMPORTS**: Drop the now-unused `MoreHorizontal` from the
  `lucide-react` import (line 4).
- **GOTCHA**: `StageStepper.test.tsx` likely asserts on
  `stage-stepper-override` testid — update or remove that test.
- **VALIDATE**: `cd frontend && npm test StageStepper -- --run`

### 9. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — Bug #5 cleanup (part 2)

- **IMPLEMENT**:
  - Remove the `_showOverrideSelect` state declaration (line 111).
  - Remove the `setShowOverrideSelect(false)` call inside
    `handleStatusOverride` (line 318) — it now does nothing.
  - Remove the `onOverrideClick={() => setShowOverrideSelect(true)}` prop
    on `<StageStepper>` (line 546).
- **PATTERN**: Reverse-direction of the `_unused` underscore-prefix
  convention — this state actually was unused, so it should be deleted
  (per code-standards: prefer deleting dead code over leaving prefixed
  placeholders).
- **IMPORTS**: None to remove (`useState` still needed for
  `editingCustomerInfo` etc.).
- **GOTCHA**: After removing this state, ensure `setShowOverrideSelect`
  has no other callers (grep the file). It currently has two: the deleted
  prop and the deleted call inside `handleStatusOverride`.
- **VALIDATE**: `cd frontend && npm run typecheck && npm test SalesDetail -- --run`

### 10. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — Bug #6 fix

- **IMPLEMENT**: Update the `<NowCard …/>` usage at lines 561–570 to add
  ```tsx
  estimateSentAt={entry.updated_at ?? entry.created_at}
  nudgesPaused={false}
  ```
  with a one-line comment `// TODO(backend): replace with real estimate_sent_at + nudges_paused_until`.
- **PATTERN**: Backend doesn't yet store `estimate_sent_at` (per the
  audit "Known stubs" list); the audit explicitly authorises the
  `entry.updated_at` fallback under Req 17.5.
- **IMPORTS**: None.
- **GOTCHA**: `entry.updated_at` is always non-null per the SQLAlchemy
  model (`models/sales.py:86–91`, `nullable=False, server_default=func.now()`); the `??` to `created_at` is defence-in-depth only.
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run` and
  visually confirm `[data-testid="auto-nudge-schedule"]`
  (verified at `AutoNudgeSchedule.tsx:28`) appears for a
  `pending_approval` entry.

### 11. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — Bug #7 fix

- **IMPLEMENT**: Replace the `view_job` switch case (lines 176–182) with:
  ```tsx
  case 'view_job':
    // TODO(backend): expose entry.job_id and navigate to /jobs/{job_id}
    navigate('/jobs');
    break;
  ```
- **PATTERN**: README "minimum fix" recommendation.
- **IMPORTS**: None.
- **GOTCHA**: Do NOT delete `signwell_document_id` from anywhere else —
  it is still used by `pipeline/{id}/sign/embedded` (see
  `api/v1/sales_pipeline.py:407`).
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run`

### 12. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — Bug #8 fix

- **IMPLEMENT**:
  - Add `useUploadSalesDocument` to the imports from `../hooks/useSalesPipeline` at line 28.
  - Add `const uploadDoc = useUploadSalesDocument();` near the other hook usages (~line 65).
  - Replace `handleFileDrop` (lines 234–240) with:
    ```tsx
    const handleFileDrop = useCallback(
      async (file: File, kind: 'estimate' | 'agreement') => {
        if (!entry?.customer_id) return;
        try {
          await uploadDoc.mutateAsync({
            customerId: entry.customer_id,
            file,
            documentType: kind === 'agreement' ? 'contract' : 'estimate',
          });
          toast.success(
            `${kind === 'agreement' ? 'Agreement' : 'Estimate'} uploaded`
          );
          refetch();
        } catch (err) {
          toast.error('Upload failed', { description: getErrorMessage(err) });
        }
      },
      [entry, uploadDoc, refetch],
    );
    ```
- **PATTERN**: Mirrors the existing `handleSaveSalesEntryNotes` callback
  structure at `SalesDetail.tsx:143–153` (try/catch with `toast.error` +
  `getErrorMessage`).
- **IMPORTS**: `useUploadSalesDocument` from `'../hooks/useSalesPipeline'`,
  `getErrorMessage` already imported at line 22.
- **GOTCHA**: Don't strip the file-validation that `<Dropzone>` already
  performs at `NowCard.tsx:182–186` (PDF-only). The host is downstream of
  that, so the file is already a PDF when it arrives.
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run`

### 13. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — Bug #11 fix

- **IMPLEMENT**:
  - Add a constant near the existing `isTerminal` (line 278):
    ```tsx
    const isTerminalStage = entry.status === 'closed_won' || entry.status === 'closed_lost';
    ```
    (Keep existing `isClosedLost` for the banner branch.)
  - Replace the `{isClosedLost ? … : <>StageStepper…NowCard…ActivityStrip</>}` ternary at lines 533–575 with a structure that:
    - Renders the `closed-lost-banner` only when `entry.status === 'closed_lost'`
    - Renders a similar `closed-won-banner` (e.g. "Closed Won — converted to job. No further actions.") when `entry.status === 'closed_won'`
    - Otherwise renders the StageStepper / NowCard / ActivityStrip group
- **PATTERN**: Existing `isClosedLost` banner at lines 534–539 is the
  exact template to mirror for the won path. README recommends "hide
  StageStepper for closed_won as well" as the preferred fix.
- **IMPORTS**: None.
- **GOTCHA**: `TERMINAL_STATUSES` already exists in
  `types/pipeline.ts` — reuse it (`TERMINAL_STATUSES.includes(entry.status)`) rather than re-coding `closed_won || closed_lost`.
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run`

### 14. CREATE `frontend/src/features/sales/components/MarkDeclinedDialog.tsx`

- **IMPLEMENT**:
  ```tsx
  import { useState } from 'react';
  import { Button } from '@/components/ui/button';
  import { Label } from '@/components/ui/label';
  import { Textarea } from '@/components/ui/textarea';
  import {
    Dialog, DialogContent, DialogDescription, DialogFooter,
    DialogHeader, DialogTitle,
  } from '@/components/ui/dialog';

  interface MarkDeclinedDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (reason: string) => void;
    isPending?: boolean;
  }

  export function MarkDeclinedDialog({
    open, onOpenChange, onConfirm, isPending,
  }: MarkDeclinedDialogProps) {
    const [reason, setReason] = useState('');

    return (
      <Dialog open={open} onOpenChange={(o) => {
        if (!o) setReason('');
        onOpenChange(o);
      }}>
        <DialogContent data-testid="mark-declined-dialog">
          <DialogHeader>
            <DialogTitle>Mark as Declined?</DialogTitle>
            <DialogDescription>
              Capture the reason the customer declined. This will close the
              sales entry as lost.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="decline-reason">Reason (required)</Label>
            <Textarea
              id="decline-reason"
              data-testid="decline-reason-input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Went with competitor"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              data-testid="confirm-mark-declined-btn"
              onClick={() => onConfirm(reason.trim())}
              disabled={isPending || !reason.trim()}
            >
              {isPending ? 'Saving…' : 'Mark Declined'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }
  ```
- **PATTERN**: Mirrors `StatusActionButton.tsx:232–254` Mark Lost dialog
  exactly, with the addition of the required textarea field.
- **IMPORTS**: As shown.
- **GOTCHA**: Reset `reason` on close so re-opening the dialog presents
  an empty field. Use the `(o) => { if (!o) setReason(''); … }` pattern
  shown — direct `setReason('')` on the cancel button alone is
  insufficient because `onOpenChange` is also fired by ESC and outside-click.
- **VALIDATE**: `cd frontend && npm test MarkDeclinedDialog -- --run`

### 15. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — NEW-B integration

- **IMPLEMENT**:
  - Add state: `const [markDeclinedOpen, setMarkDeclinedOpen] = useState(false);`
  - Replace the `mark_declined` switch case (lines 192–200) with:
    ```tsx
    case 'mark_declined':
      setMarkDeclinedOpen(true);
      break;
    ```
  - Render the dialog (next to `<ScheduleVisitModal />` at the bottom):
    ```tsx
    <MarkDeclinedDialog
      open={markDeclinedOpen}
      onOpenChange={setMarkDeclinedOpen}
      isPending={markLost.isPending}
      onConfirm={(reason) => {
        markLost.mutate(
          { id: entryId, closedReason: reason },
          {
            onSuccess: () => {
              toast.success('Marked as declined');
              setMarkDeclinedOpen(false);
              refetch();
            },
            onError: () => toast.error('Failed to mark as declined'),
          },
        );
      }}
    />
    ```
  - Import `MarkDeclinedDialog` from `'./MarkDeclinedDialog'`.
- **PATTERN**: Same hosting pattern as `<ScheduleVisitModal />` at line 592.
- **IMPORTS**: `import { MarkDeclinedDialog } from './MarkDeclinedDialog';`
- **GOTCHA**:
  1. Do NOT remove the existing StageStepper `onMarkLost` flow at line 547 — that flow still lacks a reason capture but is out of Tier 2 scope; it's tracked separately.
  2. `useMarkSalesLost` hook (`useSalesPipeline.ts:90–104`) already accepts `closedReason: string | undefined` — pass the trimmed reason directly.
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run`

### 16. UPDATE `frontend/src/features/sales/components/SalesDetail.test.tsx`

- **IMPLEMENT**: Add tests covering:
  - **NEW-A**: Email button is disabled when `entry.customer_email` is `null` and `salesCustomer.email` is `null`.
  - **NEW-A**: Email button is enabled when `entry.customer_email` is set.
  - **Bug #6**: When `entry.status === 'pending_approval'`, the AutoNudgeSchedule renders (assert by testid).
  - **Bug #11**: When `entry.status === 'closed_won'`, `[data-testid="stage-stepper"]` is NOT in the document.
  - **Bug #7**: Clicking `view_job` action navigates to `/jobs` regardless of `signwell_document_id`.
  - **NEW-B**: Clicking `mark_declined` opens the `mark-declined-dialog`; submitting with empty reason is blocked; submitting with reason calls `markLost.mutate({ id, closedReason: 'reason text' })`.
- **PATTERN**: Existing tests in this file (read first); use
  `<QueryProvider>` wrapper from `@/core/providers/QueryProvider` per
  `frontend-testing.md`. Mock the API via `axios-mock-adapter` if that's
  the existing convention (verify by reading current test setup).
- **IMPORTS**: As needed, mirror existing tests.
- **GOTCHA**: Ensure mocked customer-detail response includes `email` when
  testing NEW-A — otherwise the second clause of the `??` evaluates to `undefined`.
- **VALIDATE**: `cd frontend && npm test SalesDetail -- --run`

### 17. UPDATE `frontend/src/features/sales/components/PipelineList.test.tsx`

- **IMPLEMENT**: Add a test that clicks the row action button and asserts
  `onRowClick` was called with the entry. Add a test that clicks the
  dismiss button and asserts a `toast.info` was emitted (mock `sonner`).
- **PATTERN**: Existing PipelineList tests in the same file.
- **IMPORTS**: `vi.mock('sonner', ...)`.
- **VALIDATE**: `cd frontend && npm test PipelineList -- --run`

### 18. UPDATE `frontend/src/features/sales/components/NowCard.test.tsx`

- **IMPLEMENT**: Add a test that clicks `[data-testid="now-card-weekof-pick"]`, awaits the popover, clicks a calendar day, and asserts `onWeekOfChange` was called with a string matching `/^[A-Z][a-z]{2} \d{1,2}$/`.
- **PATTERN**: Existing NowCard tests.
- **VALIDATE**: `cd frontend && npm test NowCard -- --run`

### 19. CREATE `frontend/src/features/sales/components/MarkDeclinedDialog.test.tsx`

- **IMPLEMENT**:
  - Renders title and required label
  - Confirm button is disabled when reason is empty/whitespace
  - Confirm button calls `onConfirm` with trimmed reason
  - Closing the dialog clears the textarea (re-open shows empty)
- **PATTERN**: `frontend-testing.md` form test pattern (lines 28–35).
- **VALIDATE**: `cd frontend && npm test MarkDeclinedDialog -- --run`

### 20. UPDATE `frontend/src/features/sales/components/StageStepper.test.tsx`

- **IMPLEMENT**:
  - Remove any test that asserts on `stage-stepper-override` testid.
  - Add a test that asserts `[data-testid="stage-stepper-override"]` is
    NOT in the document (regression guard for Bug #5).
- **VALIDATE**: `cd frontend && npm test StageStepper -- --run`

### 21. RUN full quality gates

- **IMPLEMENT**: Sequence below.
- **VALIDATE** (must all pass with zero errors):
  ```bash
  cd /Users/kirillrakitin/Grins_irrigation_platform
  uv run ruff check src/grins_platform
  uv run ruff format --check src/grins_platform
  uv run mypy src/grins_platform
  uv run pyright src/grins_platform
  uv run pytest -m unit src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py -v

  cd frontend
  npm run lint
  npm run typecheck
  npm test -- --run
  ```

### 22. RUN agent-browser E2E validation

- **IMPLEMENT**: Run scripts in "Manual Validation" below against the
  Vercel dev URL listed in the bug-hunt README.
- **VALIDATE**: All commands succeed; visually confirm via screenshots.

---

## TESTING STRATEGY

### Unit Tests

**Backend** (per `code-standards.md` "Three-Tier Testing"):
- Add one unit test in
  `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py`
  for `_entry_to_response`'s new `customer_email` field.
- Mark `@pytest.mark.unit`. All deps mocked (the helper is sync and pure
  given an in-memory `SalesEntry` with `entry.customer = customer`).

**Frontend** (per `frontend-testing.md` + `spec-quality-gates.md`):
- Component tests for every modified component.
- Each new test goes in the co-located `.test.tsx`.
- Wrap with `<QueryProvider>` per the steering file pattern.

### Integration Tests

No new integration tests required — the backend change is a single
serialiser field addition and the rest is purely UI wiring of existing
hooks. Existing pipeline integration tests already cover the underlying
mutations.

### Edge Cases

- NEW-A: customer with `email=None` → button disabled, NowCard takes
  "no email" branch
- NEW-A: customer with empty-string email (`""`) → `!!""` is `false`, so
  treated as no email (correct)
- Bug #4: user picks a date in the past → still allowed (the field is a
  rough planning hint, not a hard constraint)
- Bug #6: `entry.updated_at === entry.created_at` (unchanged entry) →
  schedule still renders with day-0 = entry creation
- Bug #8: drop a non-PDF → `<Dropzone>` blocks at `NowCard.tsx:182–186`,
  host never sees it
- Bug #11: entry transitions from `send_contract` to `closed_won` while
  the page is open → `isTerminalStage` re-derives and stepper hides on
  next render
- NEW-B: user opens decline modal, types reason, clicks outside →
  textarea clears via `onOpenChange` reset (verified in test 19)
- NEW-B: backend returns 422 (`InvalidSalesTransitionError`) → toast
  shows error, dialog stays open

---

## VALIDATION COMMANDS

Execute every command. Zero errors required.

### Level 1: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run ruff check src/grins_platform
uv run ruff format --check src/grins_platform

cd frontend
npm run lint
npm run typecheck
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest -m unit src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py -v
uv run mypy src/grins_platform
uv run pyright src/grins_platform

cd frontend
npm test -- --run
```

### Level 3: Integration Tests

```bash
# No new integration tests — confirm existing ones still pass
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run pytest -m functional src/grins_platform/tests/functional -v -k 'sales'
uv run pytest -m integration src/grins_platform/tests/integration -v -k 'sales'
```

### Level 4: Manual Validation (agent-browser, per
`spec-testing-standards.md` + `agent-browser.md`)

Two test entries from the bug-hunt audit:

```bash
DEV_URL="https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app"
TESTING_VIKTOR="e5690e69-203b-4139-9379-87c41da8e80e"  # no email — NEW-A path
BROOKE_JORE="5607f5ca-5993-4fdc-90f5-e66e738d0c38"     # full progression
```

**NEW-A: Email button disabled when no email**

```bash
agent-browser --session sales-bugs open "$DEV_URL/sales/$TESTING_VIKTOR"
agent-browser wait --load networkidle
agent-browser is enabled "[data-testid='email-sign-btn']"  # expect: false
agent-browser snapshot -i                                   # confirm "Add customer email first" copy
```

**Bug #3: Pipeline-list row buttons clickable**

```bash
agent-browser open "$DEV_URL/sales"
agent-browser wait --load networkidle
agent-browser click "[data-testid^='pipeline-row-action-']"
agent-browser wait --url "**/sales/**"
```

**Bug #6: AutoNudgeSchedule renders on pending_approval**

```bash
# Use an entry currently in pending_approval; if none, override Brooke
# manually from the UI first.
agent-browser open "$DEV_URL/sales/$BROOKE_JORE"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='auto-nudge-schedule']"  # expect: true
```

**Bug #4: + pick date popover opens**

```bash
agent-browser open "$DEV_URL/sales/$BROOKE_JORE"
agent-browser click "[data-testid='now-card-weekof-pick']"
agent-browser wait "[role='dialog']"  # popover content
agent-browser is visible ".rdp"        # react-day-picker root class
```

**Bug #5: change-stage-manually footer button removed**

```bash
agent-browser open "$DEV_URL/sales/$BROOKE_JORE"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='stage-stepper-override']"  # expect: false
agent-browser is visible "[data-testid='pipeline-stage-select']"   # expect: true (header alternative)
```

**Bug #7: View Job navigates to /jobs**

```bash
# Need a closed_won entry. Force one via override if absent.
agent-browser open "$DEV_URL/sales/$CLOSED_WON_ID"
agent-browser click "[data-testid='now-action-view-job']"
agent-browser wait --url "**/jobs"
```

**Bug #8: Dropzone uploads**

```bash
agent-browser open "$DEV_URL/sales/$TESTING_VIKTOR"
# Use eval to trigger the hidden <input type="file"> programmatically;
# direct file-drop via agent-browser is limited — see agent-browser docs.
agent-browser eval "document.querySelector('input[type=file]').click()"
# Then complete via the OS file dialog manually, or:
# Verify visually that toast.success "Estimate uploaded" appears and the
# document appears in the Documents section.
```

**Bug #11: StageStepper hidden on closed_won**

```bash
agent-browser open "$DEV_URL/sales/$CLOSED_WON_ID"
agent-browser is visible "[data-testid='stage-stepper']"   # expect: false
agent-browser is visible "[data-testid='closed-won-banner']" # expect: true (new)
```

**NEW-B: Mark Declined dialog captures reason**

```bash
# Need a pending_approval entry.
agent-browser open "$DEV_URL/sales/$PENDING_APPROVAL_ID"
agent-browser click "[data-testid='now-action-declined']"
agent-browser is visible "[data-testid='mark-declined-dialog']"
agent-browser is enabled "[data-testid='confirm-mark-declined-btn']"  # expect: false
agent-browser fill "[data-testid='decline-reason-input']" "Customer chose competitor"
agent-browser is enabled "[data-testid='confirm-mark-declined-btn']"  # expect: true
agent-browser click "[data-testid='confirm-mark-declined-btn']"
agent-browser wait --text "Marked as declined"
```

### Level 5: Additional Validation (Optional)

- Vercel preview build: open the auto-generated PR preview URL and run
  the full agent-browser script against it before merge.
- Coverage check (per `frontend-testing.md` line 56):
  ```bash
  cd frontend && npm run test:coverage
  ```
  Confirm sales feature components stay above 80%.

---

## ACCEPTANCE CRITERIA

- [ ] **NEW-A**: `hasEmail` derived from real customer email; email-sign
  button disabled when no email; `customer_email` exposed on
  `SalesEntryResponse`
- [ ] **Bug #3**: Pipeline-list row action button navigates to detail;
  dismiss button toasts a stub message
- [ ] **Bug #4**: `+ pick date…` opens a Popover with a Calendar; selecting a date sets the Week-Of value to a `"MMM d"` string
- [ ] **Bug #5**: `⋯ change stage manually` footer button removed; dead
  `_showOverrideSelect` state removed; header `Change stage…` Select
  remains the sole entry point
- [ ] **Bug #6**: AutoNudgeSchedule renders on `pending_approval` with
  fallback `estimateSentAt = entry.updated_at`
- [ ] **Bug #7**: `view_job` always navigates to `/jobs` (no
  `signwell_document_id` branch)
- [ ] **Bug #8**: Dropping a PDF into the dropzone uploads it via
  `useUploadSalesDocument` and refetches the document list
- [ ] **Bug #11**: StageStepper hidden on `closed_won`; new
  `closed-won-banner` shown instead
- [ ] **NEW-B**: `mark_declined` opens a dialog requiring a reason; on
  confirm, `markLost.mutate({ id, closedReason })` fires
- [ ] All `ruff check`, `ruff format --check`, `mypy`, `pyright` pass
  with zero errors
- [ ] All `npm run lint`, `npm run typecheck`, `npm test -- --run` pass
  with zero errors
- [ ] New unit test for `_entry_to_response` `customer_email` field
  passes
- [ ] All new component tests pass; coverage target maintained
- [ ] agent-browser scripts pass for all nine bugs against dev
- [ ] No regressions in `closed_lost` banner, `Schedule visit` modal,
  `Skip — advance manually`, or any of the spec-compliant flows listed
  in README "What Works"

---

## COMPLETION CHECKLIST

- [ ] All 22 step-by-step tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All Level 1–4 validation commands executed successfully
- [ ] Full test suite passes (unit + functional + integration)
- [ ] No linting or type-checking errors (ruff, mypy, pyright, eslint, tsc)
- [ ] agent-browser E2E confirms feature works in dev
- [ ] All acceptance criteria met
- [ ] Code reviewed for quality (no leftover `// TODO(wiring)` or
  `// TODO(backend): wire to useUploadSalesDocument` comments — both are
  resolved by this PR)

---

## NOTES

### Scope discipline

- **In scope**: 9 Tier 1 + Tier 2 bugs (NEW-A, #3, #6, #5, #4, #8, #7, #11, NEW-B).
- **Explicitly out of scope** (deferred to follow-up plans): Tier 3 (NEW-C, #9, NEW-D — needs new backend endpoints for `pause_nudges`, `text_confirmation`, `add_customer_email`, and pipeline `dismiss`); Tier 4 (#10 pagination text); Tier 5 (already resolved).
- **Do not** preemptively design or implement the deferred backend
  endpoints in this plan — they involve real persistence (e.g. a
  `nudges_paused_until` column on `SalesEntry`) and SMS-provider wiring
  that warrants its own spec.

### Trade-offs

- **NEW-A backend addition**: Could have been frontend-only (use
  `salesCustomer?.email`). Chose to add `customer_email` on
  `SalesEntryResponse` because the row-list view (where
  `useCustomerDetail` is not fetched per row) also needs the value
  visible to ACTION_LABELS / future enable/disable logic. The API
  addition is a one-liner with zero migration cost.
- **Bug #5**: Could have wired up a modal instead of deleting the
  button. Chose delete because the header `Change stage…` Select at
  `SalesDetail.tsx:427–438` already provides a strictly superior UX
  (filtered list of valid transitions vs free-form modal).
- **Bug #7**: Could have added `entry.job_id` to the schema now. Chose
  to defer because the convert mutation backend (`convert_to_job` at
  `api/v1/sales_pipeline.py:422–454`) does not currently return the
  created Job's id back into `SalesEntry`; threading that through the
  conversion service is a separable change worth tracking on its own.

### Steering-file alignment

This plan deliberately follows the project's non-kiro steering documents:
- `code-standards.md` — three-tier testing, structured logging (no new
  log events here, but existing `_ep` mixin used where relevant)
- `frontend-patterns.md` — VSA imports, data-testid conventions, sonner
  `toast.error` with `getErrorMessage`, TanStack Query hooks
- `frontend-testing.md` — Vitest + RTL, co-located tests, QueryProvider
  wrapper, agent-browser scripts
- `api-patterns.md` — request_id correlation patterns preserved (no new
  endpoints, so no changes needed)
- `structure.md` / `tech.md` — package layout respected; no new
  dependencies; existing tools (uv, ruff, mypy, pyright, vitest) used
- `spec-quality-gates.md` — data-testid conventions, agent-browser E2E
  for UI changes
- `spec-testing-standards.md` — backend unit + frontend component
  coverage required
- `agent-browser.md` — selector and command syntax in Level-4 scripts
- `parallel-execution.md` — Phase 2 explicitly designed for parallel
  execution
- `pre-implementation-analysis.md` — independent vs serial groups
  declared upfront
- `vertical-slice-setup-guide.md` — all changes stay inside the
  `features/sales` slice + small backend-schema addition; no new
  cross-feature imports

### Confidence

10/10 for one-pass implementation success. Every assumption from the
initial draft has been verified against the live source tree:

- `frontend/src/components/ui/popover.tsx` ✅ present
- `frontend/src/components/ui/calendar.tsx` ✅ present
- `frontend/src/components/ui/{dialog,textarea,label,button,card,input,select}.tsx` ✅ all present
- `AutoNudgeSchedule` testid is **`auto-nudge-schedule`** (`AutoNudgeSchedule.tsx:28`) — locked into the Bug #6 e2e and component test
- `nowContent` action testids are confirmed (`nowContent.ts:29–113`): `now-action-schedule`, `now-action-text-confirm`, `now-action-send-estimate`, `now-action-skip-advance`, `now-action-add-email`, `now-action-approved`, `now-action-resend`, `now-action-pause`, **`now-action-declined`** (NOT `mark-declined`), `now-action-convert`, `now-action-view-job`, `now-action-view-customer`, `now-action-jump-schedule`
- `salesPipelineApi.uploadDocument(customerId, file, documentType)` posts to `/customers/{id}/documents?document_type={type}` (`salesPipelineApi.ts:118–123`) — `'estimate'` and `'contract'` are valid values
- `_entry_to_response` has **no** existing unit tests (verified) — Task 3 creates a fresh test
- `toast` from `'sonner'` is **not** currently imported in `SalesPipeline.tsx` — Task 6 must add the import
- `closed-lost-banner` testid (`SalesDetail.tsx:536`) is the established pattern — `closed-won-banner` mirrors it
- `customer_email` field does not yet exist on the FE `SalesEntry` type (`types/pipeline.ts:13–30`) — Task 4 adds it next to `customer_phone` at line 28
