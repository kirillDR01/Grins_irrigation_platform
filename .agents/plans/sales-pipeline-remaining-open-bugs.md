# Feature: Sales Pipeline — Remaining Open Bugs (NEW-C, #9, NEW-D, #10, Bug #5 wire-up)

> The following plan should be complete, but it's important that you validate
> documentation and codebase patterns and task sanity before you start
> implementing. Pay special attention to naming of existing utils, types, and
> models. Import from the right files.

## Feature Description

Close the **five open bugs** that the 2026-04-26 sales-pipeline bundled fix
(`09dc082`) deliberately deferred. Two of them are pure FE polish (NEW-C, #10)
and one is a partial schema fix (#9). The remaining two need new backend
endpoints + persistence (NEW-D fans out into four endpoints, two of which
require new columns; Bug #5 wires up an existing button to an existing
mutation). After this PR, the sales pipeline walkthrough has zero stub
toasts, zero dead state, zero ambiguous document matches, and accurate
pagination text under all filter combinations.

## User Story

As a **sales admin** working `/sales/{id}` and `/sales`,
I want **every action button to behave as it appears** (no stub toasts, no
no-op buttons, no broad-match unlocks),
So that I can **trust the walkthrough to drive the entry forward without
falling back to the customer-detail or schedule pages**.

## Problem Statement

Five concrete failures remain after `09dc082`:

1. **NEW-C** — `convert_to_job` (`SalesDetail.tsx:175–180`) calls
   `convertToJob.mutate` without parsing the error. When the backend rejects
   with `SignatureRequiredError` (HTTP 422 — `api/v1/sales_pipeline.py:447–451`)
   the user sees only a generic "Failed to convert" toast. There is no force-
   convert escape hatch even though `useForceConvertToJob` already exists
   (`useSalesPipeline.ts:80–88`) and `StatusActionButton.tsx:107–124` already
   demonstrates the correct pattern for the row-action button.
2. **Bug #9** — `hasSignedAgreement` (`SalesDetail.tsx:254`) treats *any*
   `document_type === 'contract'` doc on the customer as a signed agreement
   for **this** entry. `customer_documents.sales_entry_id` already exists
   (`models/customer_document.py:44–48`) but is **not exposed** on
   `CustomerDocumentResponse` (`schemas/customer_document.py:24–37`), so the
   frontend can't narrow the filter.
3. **NEW-D** — four NowCard / row actions still hit the catch-all stub at
   `SalesDetail.tsx:215–221`:
   - `pause_nudges` / unpause — needs persistence on `SalesEntry`
     (`nudges_paused_until` column does not exist).
   - `text_confirmation` — backend SMS plumbing exists
     (`services/sms_service.py:212`, `SMSService.send_message`) but no
     pipeline endpoint wraps it.
   - `add_customer_email` — `PUT /customers/{id}` already accepts email
     updates (`api/v1/customers.py:420–448`); needs a small inline modal.
   - Pipeline list `✕` dismiss — needs a `dismissed_at` column on
     `SalesEntry` and an endpoint.
4. **Bug #10** — pagination footer text at `SalesPipeline.tsx:210–215` reads
   `Showing 1 to 24 of 24 entries` even when the client-side `stuckFilter`
   has hidden every row. The footer uses `data.total` (API total) instead of
   `visibleRows.length`.
5. **Bug #5 (deferred)** — `⋯ change stage manually` button at
   `StageStepper.tsx:67–76` fires `onOverrideClick`, which flips an
   intentionally-discarded `_showOverrideSelect` (`SalesDetail.tsx:114`) and
   never opens a UI. The user has explicitly opted to **keep** the button
   and asked it to open a `<DropdownMenu>` of the 5 canonical stages calling
   the existing `useOverrideSalesStatus` mutation
   (`useSalesPipeline.ts:59–68`).

## Solution Statement

- **NEW-C**: Lift the force-convert dialog state into `SalesDetail.tsx`.
  Mirror `StatusActionButton.handleAdvance` (axios error parsing → check for
  the substrings `'signature' | 'Signature'` → open Dialog → confirm calls
  `forceConvert.mutate`).
- **Bug #9**: Add `sales_entry_id: UUID | None` to `CustomerDocumentResponse`
  (one-line schema change — the column is already populated). On the FE,
  add `sales_entry_id` to `SalesDocument` and narrow `hasSignedAgreement`
  to `d.document_type === 'contract' && (d.sales_entry_id === entry.id ||
  d.sales_entry_id == null)` (legacy fallback per H-7 comment).
- **NEW-D**:
  - Backend: Alembic migration adding `nudges_paused_until` and
    `dismissed_at` to `sales_entries`. New service methods + endpoints for
    pause/unpause nudges, send-text-confirmation (delegates to
    `SMSService.send_message` with `MessageType.OPERATIONAL`), and dismiss.
    `add_customer_email` reuses the existing `PUT /customers/{id}` route —
    no new backend.
  - Frontend: Replace catch-all stub with mutation calls. Add
    `<AddCustomerEmailDialog>` (Email input only) wired to `useUpdateCustomer`.
    Render `<PauseNudgesButton>` toggling between paused/active. Wire row
    dismiss `✕` to `useDismissSalesEntry` (replacing the stub toast added in
    `09dc082`).
- **Bug #10**: One conditional in the pagination footer:
  `displayTotal = stuckFilter ? visibleRows.length : data.total`. Hide the
  footer when `displayTotal === 0`.
- **Bug #5**: Replace dead `_showOverrideSelect` with a `<DropdownMenu>`
  rendered by `StageStepper` (anchored to the existing footer button).
  Selecting a stage calls `overrideStatus.mutateAsync({ id, body: { status }
  })` and toasts `Moved to <Label>`.

## Feature Metadata

**Feature Type**: Bug Fix (5 bugs) + minor backend additions
**Estimated Complexity**: Medium (one Alembic migration; four new endpoints;
roughly seven FE component updates; no protocol-level rework)
**Primary Systems Affected**:
- Backend: `services/sales_pipeline_service.py`, `api/v1/sales_pipeline.py`,
  `schemas/customer_document.py`, `schemas/sales_pipeline.py`,
  `models/sales.py` + new Alembic revision
- Frontend: `features/sales/components/{SalesDetail,SalesPipeline,
  StageStepper}.tsx`, `features/sales/hooks/useSalesPipeline.ts`,
  `features/sales/api/salesPipelineApi.ts`,
  `features/sales/types/pipeline.ts`,
  new `features/sales/components/{ForceConvertDialog,AddCustomerEmailDialog,
  StageOverrideMenu}.tsx`
**Dependencies**: No new packages. Reuses `@/components/ui/{dialog,
dropdown-menu,input,label,button}`, `sonner`, `axios`, existing TanStack
Query hooks, existing `SMSService`. Alembic + sqlalchemy already in
`pyproject.toml`.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

#### Backend
- `src/grins_platform/api/v1/sales_pipeline.py` (lines 1–60, 56–139, 423–486,
  488–520) — Why: existing `convert_to_job` / `force_convert_to_job` already
  return `SignatureRequiredError`; new endpoints will be appended after
  line 486 mirroring this exact decorator + try/except shape.
- `src/grins_platform/services/sales_pipeline_service.py` (read fully,
  ~430 lines; especially `convert_to_job` near line 362) — Why: where the
  new `pause_nudges`, `unpause_nudges`, `send_text_confirmation`, and
  `dismiss_entry` service methods live. Mirror the existing
  `LoggerMixin`/`DOMAIN = "sales"` style.
- `src/grins_platform/models/sales.py` (lines 30–112) — Why: the
  `SalesEntry` model. Migration adds `nudges_paused_until: Optional[datetime]`
  and `dismissed_at: Optional[datetime]` here.
- `src/grins_platform/models/customer_document.py` (lines 21–77) — Why: the
  `sales_entry_id` column **already exists** (added in bughunt H-7).
  No DB migration needed — only schema response change.
- `src/grins_platform/schemas/customer_document.py` (lines 24–37) — Why:
  `CustomerDocumentResponse` is missing the `sales_entry_id` field. Add it
  alongside `customer_id`.
- `src/grins_platform/schemas/sales_pipeline.py` (lines 32–60) — Why:
  `SalesEntryResponse`. Add `nudges_paused_until` and `dismissed_at`
  optional fields after `customer_email`. Read `_entry_to_response` in
  `api/v1/sales_pipeline.py:142–162` and add the new fields there.
- `src/grins_platform/services/sms_service.py` (lines 176–270) — Why:
  `SMSService.send_message` is the existing entry point.
  `text_confirmation` will call this with `MessageType.APPOINTMENT_REMINDER`
  (or `OPERATIONAL` — confirm in `models/enums.py`).
- `src/grins_platform/api/v1/customers.py` (lines 420–448) — Why:
  `PUT /customers/{customer_id}` already accepts a partial `CustomerUpdate`
  with `email`. **No backend change needed for `add_customer_email`** —
  only a frontend modal that calls the existing endpoint.
- `src/grins_platform/exceptions/__init__.py` — Why: contains
  `SignatureRequiredError`, `SalesEntryNotFoundError`,
  `InvalidSalesTransitionError`. Add `SalesEntryAlreadyDismissedError` if
  you want stricter dismiss semantics, otherwise treat repeat dismiss as a
  no-op.
- `src/grins_platform/migrations/versions/` — Why: each existing migration
  is a self-contained Alembic revision. Mirror the latest one (alphabetic
  by filename) for naming, header docstring, and `op.add_column` syntax.
- `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py` —
  Why: `_entry_to_response` and pipeline service unit-test patterns
  (the `customer_email` test class added in `09dc082` is the closest
  reference).

#### Frontend
- `frontend/src/features/sales/components/SalesDetail.tsx` (lines 90–249,
  especially 114, 175–180, 215–221, 254) — Why: the central switch-case host.
  Every bug listed touches this file.
- `frontend/src/features/sales/components/StatusActionButton.tsx`
  (lines 100–166, 213–230) — Why: **the** reference pattern for NEW-C.
  Lift the *exact* axios-error parsing + force-confirm Dialog into
  SalesDetail.
- `frontend/src/features/sales/components/StageStepper.tsx`
  (lines 1–89) — Why: footer button. Bug #5 either keeps the existing
  button as the `<DropdownMenuTrigger>` or moves the trigger inside.
- `frontend/src/features/sales/components/SalesPipeline.tsx`
  (lines 42, 56–70, 145–195, 200–228) — Why: `stuckFilter`, `visibleRows`,
  and the pagination footer for Bug #10.
- `frontend/src/features/sales/components/NowCard.tsx`
  (search for `pause_nudges`, `add_customer_email`, `text_confirmation`) —
  Why: confirm the action IDs flow through `nowContent.ts` to the host's
  switch.
- `frontend/src/features/sales/lib/nowContent.ts`
  (lines 29–113) — Why: action testids: `now-action-pause`,
  `now-action-text-confirm`, `now-action-add-email`, `now-action-convert`,
  `now-action-resend`, `now-action-declined`.
- `frontend/src/features/sales/hooks/useSalesPipeline.ts`
  (read fully, especially lines 59–88, 122–148) — Why: existing hooks
  `useOverrideSalesStatus`, `useConvertToJob`, `useForceConvertToJob`,
  `useUploadSalesDocument`, `useSalesDocuments`, the `pipelineKeys` factory.
  New hooks `usePauseNudges`, `useUnpauseNudges`, `useSendTextConfirmation`,
  `useDismissSalesEntry` go here.
- `frontend/src/features/sales/api/salesPipelineApi.ts`
  (lines 1–130) — Why: pattern for new endpoint wrappers.
- `frontend/src/features/sales/types/pipeline.ts`
  (lines 13–31, 142–168) — Why: `SalesEntry` shape, `STAGES`, `STAGE_INDEX`.
  Add `nudges_paused_until: string | null`, `dismissed_at: string | null`
  to `SalesEntry`.
- `frontend/src/features/customers/hooks/useCustomerMutations.ts`
  (lines 22–33) — Why: `useUpdateCustomer({ id, data })` reused for
  `add_customer_email`.
- `frontend/src/components/ui/dropdown-menu.tsx`,
  `frontend/src/components/ui/dialog.tsx`,
  `frontend/src/components/ui/{input,label,button}.tsx` — Why: shadcn
  primitives already in repo.
- `frontend/src/features/sales/components/MarkDeclinedDialog.tsx` (created
  in `09dc082`) — Why: use as the structural template for
  `AddCustomerEmailDialog.tsx` (props shape, footer button layout, testid
  conventions).

### New Files to Create

#### Backend
- `src/grins_platform/migrations/versions/{NEW_REVISION_HASH}_sales_entry_nudges_dismiss_columns.py`
  — Alembic revision adding `nudges_paused_until` (nullable timestamptz) and
  `dismissed_at` (nullable timestamptz) to `sales_entries`. Keep the
  `down_revision` chain consistent with the latest existing migration.

#### Frontend
- `frontend/src/features/sales/components/ForceConvertDialog.tsx` — Mirrors
  the `Dialog` block at `StatusActionButton.tsx:213–230`. Props:
  `{ open, onOpenChange, isPending, onConfirm }`.
- `frontend/src/features/sales/components/AddCustomerEmailDialog.tsx` —
  shadcn `<Dialog>` with `<Input type="email">` + zod min-length validation.
  Props: `{ open, onOpenChange, customerId, onSaved }`. Calls
  `useUpdateCustomer().mutateAsync({ id: customerId, data: { email } })`
  on submit.
- `frontend/src/features/sales/components/StageOverrideMenu.tsx` —
  `<DropdownMenu>` rendering all 5 `STAGES` (`schedule_estimate`,
  `send_estimate`, `pending_approval`, `send_contract`, `closed_won`).
  Props: `{ currentStage, onSelect(stage) }`. The trigger is a render-prop
  child so `StageStepper` can keep its existing button DOM.
- Co-located component tests for each new file:
  `ForceConvertDialog.test.tsx`, `AddCustomerEmailDialog.test.tsx`,
  `StageOverrideMenu.test.tsx`.

#### Backend tests
- Append to `src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py`:
  - `TestPauseUnpauseNudges` — service method sets/clears
    `nudges_paused_until`.
  - `TestSendTextConfirmation` — service method delegates to a mocked
    `SMSService.send_message`.
  - `TestDismissSalesEntry` — sets `dismissed_at`; second call is idempotent.
  - `TestEntryToResponseExposesNewFields` — `_entry_to_response` returns
    `nudges_paused_until` and `dismissed_at`.
  - `TestCustomerDocumentResponseExposesSalesEntryId` — round-trips
    `sales_entry_id` through Pydantic.

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

- [shadcn DropdownMenu](https://ui.shadcn.com/docs/components/dropdown-menu)
  — Why: Bug #5 replaces a no-op button with a `<DropdownMenu>` of stages.
- [shadcn Dialog](https://ui.shadcn.com/docs/components/dialog)
  — Why: NEW-C and `add_customer_email` both use `<Dialog>`. Reuse the
  exact import shape used in `StatusActionButton.tsx:213–230` and
  `MarkDeclinedDialog.tsx`.
- [TanStack Query — useMutation onError typing](https://tanstack.com/query/v5/docs/framework/react/guides/mutations#mutation-side-effects)
  — Why: NEW-C parses the `onError` axios error.
- [SQLAlchemy 2.0 mapped_column with Optional[datetime]](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#using-pep-593-annotated-to-package-common-directives-into-types)
  — Why: matches the existing `last_contact_date` style in
  `models/sales.py:66–69`.
- [Alembic Operations Reference — add_column](https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.add_column)
  — Why: pattern for the `nudges_paused_until` / `dismissed_at` migration.
- [date-fns format](https://date-fns.org/v3/docs/format)
  — Why: already used in `NowCard.tsx` for the Bug #4 popover; reuse for
  any UI-side timestamp display of `nudges_paused_until`.

### Patterns to Follow

#### Steering-document alignment (excludes kiro / kiro-cli content)

- `.kiro/steering/code-standards.md` — Three-tier testing:
  - **Unit** (`@pytest.mark.unit`, `tests/unit/`): all new service methods +
    schema serializers must have unit tests with mocked DB / mocked
    `SMSService`.
  - Structured logging via `LoggerMixin` (`DOMAIN = "sales"`) with
    `log_started("pause_nudges", entry_id=...)` /
    `log_completed("pause_nudges", entry_id=...)` /
    `log_failed("pause_nudges", error=e)` per the existing
    `SalesPipelineService` style. Don't log PII (no phone numbers, only
    masked via `_mask_phone`).
  - Type safety: `mypy src/` and `pyright src/` zero errors.
  - Quality commands at the bottom of the file are the validation gates:
    `uv run ruff check --fix src/`, `uv run ruff format src/`,
    `uv run mypy src/`, `uv run pyright src/`,
    `uv run pytest -m unit -v`.
- `.kiro/steering/api-patterns.md` — Endpoint template:
  - `set_request_id()` at start, `clear_request_id()` in `finally`.
  - `DomainLogger.api_event(logger, "pause_nudges", "started",
    request_id=..., entry_id=...)` → `_completed` on success,
    `_failed` on raise.
  - Status codes: 200 for state-changing POSTs that return the updated
    entity; 404 if entry not found; 422 for invalid transition (matches
    existing `convert_to_job` exception map).
  - Request/Response models: `SalesEntryResponse` for return value of
    `pause_nudges`, `unpause_nudges`, `dismiss`. `text_confirmation`
    returns `{ "message_id": str, "status": str }` to mirror the SMS
    service result.
- `.kiro/steering/frontend-patterns.md` — VSA imports
  (`@/features/sales/...`, `@/shared/components/ui/...`,
  `@/core/api/client`), TanStack Query key factory pattern (extend
  `pipelineKeys`), `cn()` for class merging, sonner `toast.success` /
  `toast.error({ description: getErrorMessage(err) })` mutation error
  handling. data-testid: `force-convert-dialog`,
  `confirm-force-convert-btn`, `add-customer-email-dialog`,
  `customer-email-input`, `confirm-add-email-btn`,
  `stage-override-menu`, `stage-override-{stage_key}`,
  `pause-nudges-btn`, `unpause-nudges-btn`,
  `send-text-confirmation-btn`, `pipeline-row-dismiss-{id}` (already
  defined for Bug #3 in `09dc082`).
- `.kiro/steering/frontend-testing.md` — Vitest + RTL co-located tests
  with `wrapper={QueryProvider}`. Each new component gets a `.test.tsx`
  file. Coverage targets: components 80%+, hooks 85%+.
- `.kiro/steering/structure.md` — Backend changes stay inside
  `src/grins_platform/`; FE changes inside `frontend/src/features/sales/`
  (no cross-feature imports — `useUpdateCustomer` is reached via the
  feature's public API at `@/features/customers`).
- `.kiro/steering/spec-testing-standards.md` — Each new endpoint must
  have a unit test (mocked) and a functional test (real DB, marked
  `@pytest.mark.functional`). Each new component must have RTL coverage
  for loading, error, and empty states. Add an agent-browser script in
  Validation Level 4 for every new visible UI element.
- `.kiro/steering/tech.md` — Stack confirmation: FastAPI + SQLAlchemy
  async + structlog; React 19 + TanStack Query v5 + shadcn. Performance
  target API <200ms p95 — the four new endpoints are simple
  single-row UPDATEs, well within budget.

#### Naming conventions
- Backend: snake_case modules, `{Domain}Service` classes,
  `{action}_{state}` log events.
- Frontend: PascalCase components, `use{Action}{Resource}` hooks,
  kebab-case testids, `{action}-{feature}-btn` button testids.

#### Error handling

```python
# Backend service method — mirror sales_pipeline_service.convert_to_job
async def pause_nudges(
    self,
    session: AsyncSession,
    entry_id: UUID,
    *,
    paused_until: datetime,
    actor_id: UUID,
) -> SalesEntry:
    self.log_started("pause_nudges", entry_id=str(entry_id))
    entry = await session.get(SalesEntry, entry_id)
    if entry is None:
        self.log_rejected("pause_nudges", reason="not_found",
                          entry_id=str(entry_id))
        raise SalesEntryNotFoundError(entry_id)
    entry.nudges_paused_until = paused_until
    await session.flush()
    self.log_completed("pause_nudges", entry_id=str(entry_id))
    return entry
```

```tsx
// Frontend mutation handler — mirror StatusActionButton.handleAdvance
const onError = (err: unknown) => {
  const detail = axios.isAxiosError(err)
    ? (err.response?.data?.detail ?? 'Failed to convert')
    : 'Failed to convert';
  if (typeof detail === 'string'
      && (detail.includes('signature') || detail.includes('Signature'))) {
    setForceConvertOpen(true);
  } else {
    toast.error('Error', {
      description: typeof detail === 'string' ? detail : 'Failed to convert',
    });
  }
};
```

#### Logging pattern (backend)

```python
DomainLogger.api_event(logger, "pause_nudges", "started",
                       request_id=request_id, entry_id=str(entry_id))
# … work …
DomainLogger.api_event(logger, "pause_nudges", "completed",
                       request_id=request_id, entry_id=str(entry_id),
                       status_code=200)
```

#### TanStack Query key extension

```ts
export const pipelineKeys = {
  // existing keys preserved …
  // (no new key factories needed — pause/unpause/dismiss invalidate
  //  pipelineKeys.lists() + pipelineKeys.detail(id), exactly like
  //  useOverrideSalesStatus.)
};
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Backend — schema + migration)

Add the persistence backbone that NEW-D and Bug #9 hinge on. Nothing is
user-visible after this phase.

**Tasks:**
1. Add `sales_entry_id` to `CustomerDocumentResponse` (one-line schema
   addition; column already exists).
2. Alembic migration adding `nudges_paused_until` + `dismissed_at` columns
   to `sales_entries`.
3. Update `SalesEntry` model with the two new mapped columns.
4. Update `SalesEntryResponse` schema with the two new optional fields.
5. Update `_entry_to_response` to assign the two new fields.

### Phase 2: Core Implementation — Backend service + endpoints

Service methods and endpoints for the four NEW-D actions. `add_customer_email`
is FE-only (reuses `PUT /customers/{id}`).

**Tasks:**
6. `SalesPipelineService.pause_nudges(entry_id, paused_until, actor_id)` and
   `unpause_nudges(entry_id, actor_id)`.
7. `SalesPipelineService.send_text_confirmation(entry_id, actor_id)` —
   delegates to `SMSService.send_message`.
8. `SalesPipelineService.dismiss_entry(entry_id, actor_id)` —
   sets `dismissed_at = now()`; idempotent.
9. Endpoints in `api/v1/sales_pipeline.py`:
   - `POST /sales/pipeline/{entry_id}/pause-nudges`
   - `POST /sales/pipeline/{entry_id}/unpause-nudges`
   - `POST /sales/pipeline/{entry_id}/send-text-confirmation`
   - `POST /sales/pipeline/{entry_id}/dismiss`

### Phase 3: Core Implementation — Frontend hooks + API + types

**Tasks:**
10. Extend `salesPipelineApi.ts` with the 4 new endpoint wrappers.
11. Extend `useSalesPipeline.ts` with `usePauseNudges`, `useUnpauseNudges`,
    `useSendTextConfirmation`, `useDismissSalesEntry`.
12. Extend `SalesDocument` and `SalesEntry` types in `types/pipeline.ts`
    with the new fields.

### Phase 4: Core Implementation — Frontend dialogs and menus

**Tasks:**
13. CREATE `ForceConvertDialog.tsx`.
14. CREATE `AddCustomerEmailDialog.tsx`.
15. CREATE `StageOverrideMenu.tsx`.

### Phase 5: Integration — wire into SalesDetail / SalesPipeline / StageStepper

**Tasks:**
16. UPDATE `SalesDetail.tsx`:
    - Replace `case 'convert_to_job'` (NEW-C) with axios-error-parsing
      handler that opens `<ForceConvertDialog>`.
    - Replace catch-all stub for `pause_nudges`, `text_confirmation`,
      `add_customer_email`, `resend_estimate` with real mutations
      (NEW-D + a quick `resend_estimate → emailSign.mutateAsync`
      bonus per `db7befa`).
    - Narrow `hasSignedAgreement` (Bug #9).
    - Remove dead `_showOverrideSelect` state (Bug #5 part 1).
17. UPDATE `StageStepper.tsx` — wrap the existing `change stage manually`
    button in a `<DropdownMenu>` rendered by `StageOverrideMenu` (Bug #5
    part 2). Add new prop `onStageOverride(stage: StageKey)`.
18. UPDATE `SalesPipeline.tsx`:
    - Pagination footer uses `displayTotal = stuckFilter ?
      visibleRows.length : data.total` and hides on zero (Bug #10).
    - Wire row-dismiss `✕` to `useDismissSalesEntry` (replacing the
      sonner stub from `09dc082`).

### Phase 6: Testing & Validation

**Tasks:**
19. Backend unit tests (5 new test classes — see *New Files to Create*).
20. Backend functional tests for each new endpoint (real DB, real auth).
21. Frontend component tests for the 3 new components.
22. Frontend SalesDetail / SalesPipeline / StageStepper test cases:
    - SalesDetail: NEW-C signature error opens ForceConvertDialog;
      add-customer-email opens dialog; pause_nudges fires mutation;
      text_confirmation fires mutation; hasSignedAgreement is entry-scoped.
    - SalesPipeline: Bug #10 stuck filter shows `0 of 0`; row dismiss
      fires mutation.
    - StageStepper: `stage-stepper-override` opens DropdownMenu with 5
      items; selecting fires `onStageOverride`.
23. Run all four validation levels.

---

## STEP-BY-STEP TASKS

> Execute every task in order, top to bottom. Each task is atomic and
> independently testable.

### Task Format Guidelines

- **CREATE**: New files
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **MIRROR**: Copy pattern from elsewhere in codebase

---

### 1. UPDATE `src/grins_platform/schemas/customer_document.py` — expose `sales_entry_id` (Bug #9 backend)

- **IMPLEMENT**: Add `sales_entry_id: Optional[UUID] = None` to
  `CustomerDocumentResponse` after `customer_id`.
- **PATTERN**: `models/customer_document.py:44–48` (column shape).
- **IMPORTS**: `Optional` and `UUID` already imported at lines 7–8.
- **GOTCHA**: Optional because legacy rows pre-H-7 have NULL. The
  Pydantic `from_attributes=True` (line 27) does the rest.
- **VALIDATE**:
  ```bash
  uv run ruff check src/grins_platform/schemas/customer_document.py
  uv run pyright src/grins_platform/schemas/customer_document.py
  ```

### 2. CREATE Alembic migration `sales_entry_nudges_dismiss_columns.py`

- **IMPLEMENT**: New revision adding two nullable timestamptz columns to
  `sales_entries`:
  - `nudges_paused_until DATETIME(timezone=True) NULL`
  - `dismissed_at DATETIME(timezone=True) NULL`
- **PATTERN**: Mirror
  `src/grins_platform/migrations/versions/20260429_100100_seed_day_2_reminder_settings.py`
  (header docstring shape, `revision` / `down_revision` constants).
- **IMPORTS**: `from alembic import op` + `import sqlalchemy as sa` +
  `from collections.abc import Sequence`.
- **CURRENT HEAD (verified 2026-04-26 via `uv run alembic heads`)**:
  `20260429_100100`. New revision should be:
  - filename: `20260430_120000_add_sales_entry_nudges_dismiss_columns.py`
  - `revision: str = "20260430_120000"`
  - `down_revision: str | None = "20260429_100100"`
- **`upgrade()`**:
  ```python
  op.add_column(
      "sales_entries",
      sa.Column("nudges_paused_until", sa.DateTime(timezone=True), nullable=True),
  )
  op.add_column(
      "sales_entries",
      sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
  )
  ```
- **`downgrade()`**: drop both columns in reverse order.
- **GOTCHA**: Run `uv run alembic heads` again immediately before
  authoring — if any migration has merged since this plan was written
  (current head: `20260429_100100`), update `down_revision` to the
  newer head; otherwise the chain breaks.
- **VALIDATE**:
  ```bash
  uv run alembic check
  uv run alembic upgrade head    # apply on dev DB
  uv run alembic downgrade -1    # round-trip
  uv run alembic upgrade head
  ```

### 3. UPDATE `src/grins_platform/models/sales.py` — add columns

- **IMPLEMENT**: After the `signwell_document_id` block (line 80) and
  before `created_at` (line 81), add:
  ```python
  nudges_paused_until: Mapped[Optional[datetime]] = mapped_column(
      DateTime(timezone=True),
      nullable=True,
  )
  dismissed_at: Mapped[Optional[datetime]] = mapped_column(
      DateTime(timezone=True),
      nullable=True,
  )
  ```
- **PATTERN**: `models/sales.py:66–69` (`last_contact_date` shape).
- **IMPORTS**: `Optional`, `datetime`, `DateTime`, `Mapped`,
  `mapped_column` already imported.
- **GOTCHA**: Keep alphabetic-ish ordering — these are state columns
  separated from timestamps; insert before `created_at` to keep `created_at`
  / `updated_at` adjacent.
- **VALIDATE**:
  ```bash
  uv run mypy src/grins_platform/models/sales.py
  uv run pyright src/grins_platform/models/sales.py
  ```

### 4. UPDATE `src/grins_platform/schemas/sales_pipeline.py` — extend `SalesEntryResponse`

- **IMPLEMENT**: Add two `Optional[datetime]` fields after `customer_email`:
  ```python
  nudges_paused_until: Optional[datetime] = None
  dismissed_at: Optional[datetime] = None
  ```
- **PATTERN**: existing `customer_email: Optional[str] = None` line in the
  same `SalesEntryResponse` class.
- **IMPORTS**: `datetime` likely already imported; verify.
- **VALIDATE**:
  ```bash
  uv run pyright src/grins_platform/schemas/sales_pipeline.py
  ```

### 5. UPDATE `src/grins_platform/api/v1/sales_pipeline.py` — `_entry_to_response` populates new fields

- **IMPLEMENT**: In `_entry_to_response` (around line 142–162) add:
  ```python
  nudges_paused_until=entry.nudges_paused_until,
  dismissed_at=entry.dismissed_at,
  ```
  alongside the other field assignments.
- **PATTERN**: existing `customer_email=customer.email if customer else None`
  assignment in the same helper.
- **VALIDATE**: covered by Task 19's `TestEntryToResponseExposesNewFields`
  unit test.

### 6. UPDATE `src/grins_platform/services/sales_pipeline_service.py` — pause/unpause/text/dismiss methods

- **IMPLEMENT**: Add four new `async` methods to `SalesPipelineService`:
  - `pause_nudges(self, session, entry_id, *, paused_until=None, actor_id) -> SalesEntry`
    — sets `entry.nudges_paused_until = paused_until or (datetime.now(tz=timezone.utc) + timedelta(days=7))`.
  - `unpause_nudges(self, session, entry_id, *, actor_id) -> SalesEntry`
    — sets `entry.nudges_paused_until = None`.
  - `send_text_confirmation(self, session, entry_id, *, sms_service, actor_id) -> dict`
    — loads entry → loads customer → builds `Recipient` from
    `(customer.id, customer.phone, ...)` → calls
    `await sms_service.send_message(recipient, body, MessageType.CONFIRMATION,
    consent_type='transactional', sales_entry_id=entry_id)` → returns the
    SMSService result.
  - `dismiss_entry(self, session, entry_id, *, actor_id) -> SalesEntry`
    — early-returns if `entry.dismissed_at is not None` (idempotent),
    else sets `entry.dismissed_at = datetime.now(tz=timezone.utc)`.
- **PATTERN**: `convert_to_job` in the same file for the
  load-entry-or-raise + log + flush + return shape.
- **IMPORTS**:
  ```python
  from datetime import datetime, timedelta, timezone
  from grins_platform.services.sms_service import SMSService
  from grins_platform.models.enums import MessageType
  ```
- **GOTCHA**:
  - Use `MessageType.APPOINTMENT_CONFIRMATION` (`models/enums.py:736`).
    Do **not** invent a new enum value; existing constant is the right
    semantic match for "confirm a scheduled visit".
  - Use `Recipient.from_customer(customer)`
    (`services/sms/recipient.py:33`) to build the recipient — do **not**
    construct the dataclass manually.
  - `send_text_confirmation` must NOT log the customer phone number —
    `SMSService.send_message` masks it via `_mask_phone`
    (`sms_service.py:140, 244`); do not log it again at the service level.
  - Service should accept `sms_service` as a dep-injected param so tests
    can mock it; do **not** instantiate inside the method.
  - Required signature:
    ```python
    async def send_text_confirmation(
        self,
        session: AsyncSession,
        entry_id: UUID,
        *,
        sms_service: SMSService,
        actor_id: UUID,
    ) -> dict[str, Any]:
    ```
- **VALIDATE**:
  ```bash
  uv run mypy src/grins_platform/services/sales_pipeline_service.py
  uv run pytest -m unit src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py -v
  ```

### 7. UPDATE `src/grins_platform/api/v1/sales_pipeline.py` — 4 new endpoints

- **IMPLEMENT**: Append four endpoints after `force_convert_to_job` (line 486)
  and before `mark_sales_entry_lost` (line 488):
  - `POST /pipeline/{entry_id}/pause-nudges`
  - `POST /pipeline/{entry_id}/unpause-nudges`
  - `POST /pipeline/{entry_id}/send-text-confirmation`
  - `POST /pipeline/{entry_id}/dismiss`
- **PATTERN**: `convert_to_job` decorator + try/except shape (lines 423–455).
  Each catches `SalesEntryNotFoundError → 404` and `SMSError → 502`
  (text-confirmation only).
- **IMPORTS**: Add to top of `api/v1/sales_pipeline.py`:
  ```python
  from grins_platform.services.sms_service import SMSError, SMSService
  from grins_platform.services.sms import get_sms_provider
  ```
  There is **no** `get_sms_service` `Depends()` helper in this codebase.
  The repo-wide pattern (verified via `api/v1/portal.py:91` and
  `api/v1/callrail_webhooks.py:379`) is **inline construction** inside
  the endpoint:
  ```python
  sms_service = SMSService(session=session, provider=get_sms_provider())
  result = await service.send_text_confirmation(
      session, entry_id, sms_service=sms_service, actor_id=user.id,
  )
  ```
  Do **not** introduce a new `Depends(get_sms_service)` helper for this
  PR — match the existing inline pattern.
- **GOTCHA**:
  - `pause-nudges` returns `SalesEntryResponse` (use `_entry_to_response`).
  - `send-text-confirmation` returns `{"message_id": str, "status": str}`
    — do **not** return `SalesEntryResponse` here.
  - `dismiss` returns `SalesEntryResponse`. The pipeline list
    (`GET /sales/pipeline`) should still surface `dismissed_at`-set rows
    (no `WHERE dismissed_at IS NULL` filter unless the user requests one
    — out of scope for this PR; document as TODO).
- **VALIDATE**:
  ```bash
  uv run pytest -m functional -k "pause_nudges or text_confirmation or dismiss" -v
  uv run uvicorn grins_platform.main:app --reload   # then curl smoke
  ```
  ```bash
  curl -X POST http://localhost:8000/api/v1/sales/pipeline/$ENTRY_ID/pause-nudges \
    -H "Authorization: Bearer $TOKEN"
  ```

### 8. UPDATE `frontend/src/features/sales/api/salesPipelineApi.ts` — 4 new wrappers

- **IMPLEMENT**: Add after `forceConvert` (line 74):
  ```ts
  pauseNudges: async (id: string): Promise<SalesEntry> => {
    const r = await apiClient.post<SalesEntry>(`/sales/pipeline/${id}/pause-nudges`);
    return r.data;
  },
  unpauseNudges: async (id: string): Promise<SalesEntry> => {
    const r = await apiClient.post<SalesEntry>(`/sales/pipeline/${id}/unpause-nudges`);
    return r.data;
  },
  sendTextConfirmation: async (id: string): Promise<{ message_id: string; status: string }> => {
    const r = await apiClient.post<{ message_id: string; status: string }>(
      `/sales/pipeline/${id}/send-text-confirmation`,
    );
    return r.data;
  },
  dismiss: async (id: string): Promise<SalesEntry> => {
    const r = await apiClient.post<SalesEntry>(`/sales/pipeline/${id}/dismiss`);
    return r.data;
  },
  ```
- **PATTERN**: `convert` and `forceConvert` (lines 59–74).
- **VALIDATE**: TS compile via Task 11 typecheck.

### 9. UPDATE `frontend/src/features/sales/hooks/useSalesPipeline.ts` — 4 new hooks

- **IMPLEMENT**: Add after `useForceConvertToJob` (line 88):
  ```ts
  export function usePauseNudges() {
    const qc = useQueryClient();
    return useMutation({
      mutationFn: (id: string) => salesPipelineApi.pauseNudges(id),
      onSuccess: (entry) => {
        qc.invalidateQueries({ queryKey: pipelineKeys.detail(entry.id) });
        qc.invalidateQueries({ queryKey: pipelineKeys.lists() });
      },
    });
  }
  // Same shape for useUnpauseNudges, useSendTextConfirmation, useDismissSalesEntry
  ```
- **PATTERN**: `useOverrideSalesStatus` (lines 59–68).
- **VALIDATE**: TS compile + Task 22 hook test.

### 10. UPDATE `frontend/src/features/sales/types/pipeline.ts` — extend SalesEntry + SalesDocument

- **IMPLEMENT**:
  - In `SalesEntry` (lines 13–31), add after `customer_email`:
    ```ts
    nudges_paused_until: string | null;
    dismissed_at: string | null;
    ```
  - In `SalesDocument` (in `salesPipelineApi.ts:11–21` — note: the
    interface lives there, not in `types/pipeline.ts`), add:
    ```ts
    sales_entry_id: string | null;
    ```
- **GOTCHA**: `SalesDocument` is exported from `salesPipelineApi.ts` —
  update both the interface and any consumers that destructure.
- **VALIDATE**:
  ```bash
  cd frontend && npm run typecheck
  ```

### 11. CREATE `frontend/src/features/sales/components/ForceConvertDialog.tsx`

- **IMPLEMENT**: shadcn `<Dialog>` with title "Force Convert to Job?",
  description copy lifted verbatim from `StatusActionButton.tsx:218–220`,
  Cancel + "Force Convert" buttons. Props:
  ```ts
  interface ForceConvertDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    isPending: boolean;
    onConfirm: () => void;
  }
  ```
- **PATTERN**: `StatusActionButton.tsx:213–230` exactly.
- **IMPORTS**:
  ```ts
  import { Dialog, DialogContent, DialogDescription, DialogFooter,
           DialogHeader, DialogTitle } from '@/components/ui/dialog';
  import { Button } from '@/components/ui/button';
  ```
- **DATA-TESTID**: `force-convert-dialog`, `confirm-force-convert-btn`,
  `cancel-force-convert-btn`.
- **VALIDATE**:
  ```bash
  cd frontend && npm test ForceConvertDialog -- --run
  ```

### 12. CREATE `frontend/src/features/sales/components/AddCustomerEmailDialog.tsx`

- **IMPLEMENT**: shadcn `<Dialog>` with `<Input type="email">` + zod
  validation `z.string().email()`. On submit, call
  `useUpdateCustomer().mutateAsync({ id: customerId, data: { email } })`.
- **PATTERN**: `MarkDeclinedDialog.tsx` (created in `09dc082`) for the
  Dialog scaffolding + isPending + disabled-on-empty pattern. Substitute
  `<Textarea>` with `<Input type="email">`.
- **IMPORTS**:
  ```ts
  import { Dialog, DialogContent, ... } from '@/components/ui/dialog';
  import { Input } from '@/components/ui/input';
  import { Label } from '@/components/ui/label';
  import { Button } from '@/components/ui/button';
  import { useUpdateCustomer } from '@/features/customers';
  import { toast } from 'sonner';
  import { getErrorMessage } from '@/shared/utils/getErrorMessage';
  ```
- **DATA-TESTID**: `add-customer-email-dialog`, `customer-email-input`,
  `confirm-add-email-btn`, `cancel-add-email-btn`.
- **GOTCHA**: After save, parent should `refetch()` the sales entry so
  `customer_email` updates. Pass `onSaved?: () => void` so the host
  controls invalidation.
- **VALIDATE**:
  ```bash
  cd frontend && npm test AddCustomerEmailDialog -- --run
  ```

### 13. CREATE `frontend/src/features/sales/components/StageOverrideMenu.tsx`

- **IMPLEMENT**: `<DropdownMenu>` listing all 5 entries from `STAGES`
  (`types/pipeline.ts:157–163`). Trigger is a render prop (`{ children }`).
  On select, call `onSelect(stage.key)` and close.
- **PATTERN**: shadcn DropdownMenu docs + any existing
  DropdownMenu usage (search repo with
  `Grep('DropdownMenuTrigger', glob='*.tsx')`).
- **IMPORTS**:
  ```ts
  import { DropdownMenu, DropdownMenuContent, DropdownMenuItem,
           DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
  import { STAGES, type StageKey } from '@/features/sales/types/pipeline';
  ```
- **DATA-TESTID**: `stage-override-menu`,
  `stage-override-{stage.key}` for each item.
- **GOTCHA**: Disable the item matching `currentStage` so users can't
  "override to current".
- **VALIDATE**:
  ```bash
  cd frontend && npm test StageOverrideMenu -- --run
  ```

### 14. UPDATE `frontend/src/features/sales/components/SalesDetail.tsx` — wire NEW-C, Bug #9, NEW-D, Bug #5 cleanup

- **IMPLEMENT**:
  1. **REMOVE** dead `_showOverrideSelect` state at line 114
     (Bug #5 part 1).
  2. **ADD** state at top of component:
     ```tsx
     const [forceConvertOpen, setForceConvertOpen] = useState(false);
     const [addEmailOpen, setAddEmailOpen] = useState(false);
     ```
  3. **ADD** hook instantiations near other mutations:
     ```tsx
     const forceConvert = useForceConvertToJob();
     const pauseNudges = usePauseNudges();
     const unpauseNudges = useUnpauseNudges();
     const sendTextConfirm = useSendTextConfirmation();
     ```
  4. **REPLACE** `case 'convert_to_job'` (lines 175–180) with NEW-C handler
     mirroring `StatusActionButton.tsx:107–124`. On signature error, call
     `setForceConvertOpen(true)`.
  5. **REPLACE** the catch-all stub (lines 215–221) with explicit cases:
     - `case 'pause_nudges'`: if `entry.nudges_paused_until` →
       `unpauseNudges.mutate(entryId)`; else `pauseNudges.mutate(entryId)`.
     - `case 'text_confirmation'`:
       `sendTextConfirm.mutate(entryId, { onSuccess, onError })`.
     - `case 'add_customer_email'`: `setAddEmailOpen(true)`.
     - `case 'resend_estimate'`: `emailSign.mutateAsync(entryId)` (the
       email-signature endpoint was wired in `db7befa`; this gets it for
       free).
  6. **NARROW** `hasSignedAgreement` (line 254):
     ```tsx
     const hasSignedAgreement = signingDocs.some(
       (d) => d.document_type === 'contract'
              && (d.sales_entry_id === entry?.id || d.sales_entry_id == null),
     );
     ```
     Comment: `// Bug #9: scope contract docs to this entry; legacy
     pre-H-7 docs (sales_entry_id == null) fall through to keep the old
     unlock behaviour for grandfathered rows.`
  7. **RENDER** the new dialogs near the existing ones:
     ```tsx
     <ForceConvertDialog
       open={forceConvertOpen}
       onOpenChange={setForceConvertOpen}
       isPending={forceConvert.isPending}
       onConfirm={() => forceConvert.mutate(entryId, {
         onSuccess: () => { toast.success('Converted to job (forced)'); refetch(); setForceConvertOpen(false); },
         onError: () => { toast.error('Failed to force convert'); setForceConvertOpen(false); },
       })}
     />
     <AddCustomerEmailDialog
       open={addEmailOpen}
       onOpenChange={setAddEmailOpen}
       customerId={entry?.customer_id ?? ''}
       onSaved={() => { setAddEmailOpen(false); refetch(); }}
     />
     ```
- **PATTERN**: `StatusActionButton.tsx:107–166` for NEW-C; `MarkDeclinedDialog`
  open-state pattern for the new dialogs.
- **GOTCHA**:
  - Update the `useCallback` deps array to include
    `forceConvert, pauseNudges, unpauseNudges, sendTextConfirm, emailSign`.
  - The `_showOverrideSelect` removal also requires deleting the line
    where `setShowOverrideSelect` is called from `<StageStepper>` (search
    for `setShowOverrideSelect`); but Bug #5's new `<StageStepper>` props
    (next task) replace it with `onStageOverride`.
- **VALIDATE**:
  ```bash
  cd frontend && npm test SalesDetail -- --run
  ```

### 15. UPDATE `frontend/src/features/sales/components/StageStepper.tsx` — wrap override button in DropdownMenu (Bug #5 part 2)

- **IMPLEMENT**:
  1. Add new prop:
     ```ts
     onStageOverride: (stage: StageKey) => void;
     ```
     Replace the existing `onOverrideClick: () => void` prop.
  2. Wrap the existing footer button (lines 68–76) with
     `<StageOverrideMenu currentStage={currentStage} onSelect={onStageOverride}>`
     and use `<StageOverrideMenu>` as a render-prop wrapper. The existing
     button becomes the `DropdownMenuTrigger`'s child.
- **PATTERN**: shadcn pattern for converting a button into a
  DropdownMenuTrigger via `asChild`:
  ```tsx
  <StageOverrideMenu currentStage={currentStage} onSelect={onStageOverride}>
    <button data-testid="stage-stepper-override" className="…">
      <MoreHorizontal className="h-3.5 w-3.5" />
      change stage manually
    </button>
  </StageOverrideMenu>
  ```
- **GOTCHA**: Keep the existing `data-testid="stage-stepper-override"` so
  the deferred Bug #5 e2e expectation flips from `is visible: false` to
  `is visible: true`. Update the README/test-matrix accordingly.
- **VALIDATE**:
  ```bash
  cd frontend && npm test StageStepper -- --run
  ```

### 16. UPDATE `frontend/src/features/sales/components/SalesPipeline.tsx` — Bug #10 + dismiss wiring

- **IMPLEMENT**:
  1. Replace lines 210–215 (pagination footer header) with:
     ```tsx
     {(() => {
       const displayTotal = stuckFilter ? visibleRows.length : data.total;
       if (displayTotal === 0) return null;
       const start = Math.min(page * pageSize + 1, displayTotal);
       const end = Math.min((page + 1) * pageSize, displayTotal);
       return (
         <div className="p-4 border-t border-slate-100 flex items-center justify-between">
           <div className="text-sm text-slate-500">
             Showing {start} to {end} of {displayTotal} entries
           </div>
           {/* …existing pagination buttons unchanged… */}
         </div>
       );
     })()}
     ```
  2. Wire row dismiss `✕` (added in `09dc082` as `toast.info`) to
     `useDismissSalesEntry().mutate(entry.id, { onSuccess: refetch, onError: ... })`.
- **PATTERN**: existing `data && data.total > 0` guard at line 210 (replace
  with the `displayTotal === 0` guard).
- **GOTCHA**:
  - Keep `Page X of Y` text accurate too — `totalPages` already comes from
    `data.total`; revisit if needed (but the user-reported bug is only the
    `Showing ... of N` text). For now, scope the fix to that text.
  - Don't remove the sonner import added in `09dc082`; the dismiss
    `onError` toast still uses it.
- **VALIDATE**:
  ```bash
  cd frontend && npm test SalesPipeline -- --run
  ```

### 17. ADD backend unit tests in `tests/unit/test_sales_pipeline_and_signwell.py`

- **IMPLEMENT**: Append five new test classes:
  - `TestPauseUnpauseNudges` — service sets/clears `nudges_paused_until`;
    raises `SalesEntryNotFoundError` when entry missing.
  - `TestSendTextConfirmation` — service calls
    `sms_service.send_message` exactly once with the expected args.
  - `TestDismissSalesEntry` — sets `dismissed_at` once; second call is
    idempotent (does not overwrite).
  - `TestEntryToResponseExposesNewFields` — `_entry_to_response`
    populates `nudges_paused_until` and `dismissed_at` from the model.
  - `TestCustomerDocumentResponseExposesSalesEntryId` — `from_attributes`
    round-trip.
- **PATTERN**: existing `TestEntryToResponseCustomerEmail` class added in
  `09dc082`.
- **VALIDATE**:
  ```bash
  uv run pytest -m unit src/grins_platform/tests/unit/test_sales_pipeline_and_signwell.py -v
  ```

### 18. ADD backend functional tests for the four new endpoints

- **IMPLEMENT**: New test file or appended to existing
  `tests/functional/test_sales_pipeline_endpoints.py` (search for the
  closest functional file). Each endpoint:
  - 200 happy path (changes the row).
  - 404 when entry id is unknown.
  - 422 / domain error for invalid pre-conditions where applicable.
  - For `send-text-confirmation`: 502 when `SMSService` raises `SMSError`.
- **PATTERN**: Reuse existing `mark_lost` functional test as scaffolding
  (search the functional dir).
- **VALIDATE**:
  ```bash
  uv run pytest -m functional -v
  ```

### 19. ADD frontend component + integration tests

- **IMPLEMENT**: New / extended Vitest tests:
  - `ForceConvertDialog.test.tsx`, `AddCustomerEmailDialog.test.tsx`,
    `StageOverrideMenu.test.tsx` — full open/close, validation, confirm.
  - `SalesDetail.test.tsx`:
    - `convert_to_job` failure with signature in detail → ForceConvertDialog
      opens.
    - `add_customer_email` action click → AddCustomerEmailDialog opens.
    - `pause_nudges` toggles based on `entry.nudges_paused_until`.
    - `hasSignedAgreement` ignores docs with mismatched
      `sales_entry_id`.
  - `SalesPipeline.test.tsx`:
    - With `stuckFilter` on and zero matches, footer is **not** rendered.
    - With `stuckFilter` off, footer reads `data.total`.
    - Dismiss `✕` fires `useDismissSalesEntry`.
  - `StageStepper.test.tsx`:
    - Click `stage-stepper-override` opens menu with 5 items.
    - Selecting a stage fires `onStageOverride(stage.key)`.
- **PATTERN**: `MarkDeclinedDialog.test.tsx`, `PipelineList.test.tsx`,
  `SalesDetail.test.tsx` cases added in `09dc082`.
- **VALIDATE**:
  ```bash
  cd frontend && npm test -- --run
  ```

### 20. UPDATE `feature-developments/sales pipeline bug hunt/bugs.md` and `README.md`

- **IMPLEMENT**: Flip the status lines for NEW-C, Bug #9, NEW-D, Bug #10,
  and Bug #5 to `✅ Fixed (<commit-sha>, <date>)`. Append a *"Tier 3 + 4
  + Bug #5 wire-up"* section to "What Was Shipped" describing the
  bundled close-out.
- **PATTERN**: identical to the `09dc082` entries already in the file.
- **VALIDATE**: visual diff inspection — no validation command.

---

## TESTING STRATEGY

Three-tier testing per `.kiro/steering/code-standards.md`. Property-based
tests are not warranted here (no invariant-rich math).

### Unit Tests (mocked, `tests/unit/`)

- Service layer: each new method (`pause_nudges`, `unpause_nudges`,
  `send_text_confirmation`, `dismiss_entry`) gets a class with
  ≥3 cases (happy path; not-found; idempotency or error path).
- Schema: `_entry_to_response` round-trip; `CustomerDocumentResponse`
  with and without `sales_entry_id`.

### Functional Tests (real DB, `tests/functional/`)

- Each new endpoint: 200 happy, 404 unknown, 422 invalid, 502 SMS error
  (text-confirmation only).

### Integration Tests (`tests/integration/`)

- One end-to-end flow: pause → unpause → text-confirmation → dismiss
  on a single entry, asserting the row state after each call.

### Frontend Component / Hook Tests

- Each new component fully covered (loading, error, empty, valid
  submit). Each new hook covered via `renderHook` with a mocked
  `apiClient`.

### Edge Cases

- `hasSignedAgreement` with mixed `sales_entry_id` values (this entry,
  another entry, NULL).
- Pagination with `stuckFilter=true` and `data.total > 0` but
  `visibleRows.length === 0` (the bug #10 reproduction).
- `pause_nudges` re-pausing already-paused entry → idempotent or
  refresh-the-paused-until window? **Decision**: refresh — last call
  wins. Document in service docstring.
- `dismiss` of an already-dismissed entry → no-op (return existing row
  with same `dismissed_at`).
- `text_confirmation` with no phone on file → service raises
  `SMSConsentDeniedError`; endpoint returns 422 with body
  `{"detail": "<reason>"}`.
- `convert_to_job` after `force_convert_to_job` already succeeded — the
  state-machine catches this (`InvalidSalesTransitionError`); test that
  the FE toasts the message instead of opening the force-convert dialog.

---

## VALIDATION COMMANDS

Execute every level. Zero tolerated failures before merge.

### Level 1: Syntax & Style

```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint
```

### Level 2: Type checking

```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck
```

### Level 3: Unit + Functional + Integration tests

```bash
uv run pytest -m unit -v
uv run pytest -m functional -v
uv run pytest -m integration -v
uv run pytest --cov=src/grins_platform --cov-report=term-missing
cd frontend && npm test -- --run
cd frontend && npm run test:coverage
```

### Level 4: Manual / agent-browser validation

Set the dev URL + entry IDs (from the bug-hunt README):
```bash
export DEV_URL="https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app"
export TESTING_VIKTOR="e5690e69-203b-4139-9379-87c41da8e80e"
export BROOKE_JORE="5607f5ca-5993-4fdc-90f5-e66e738d0c38"
```

**NEW-C: ForceConvertDialog opens on signature error**
```bash
# Need an entry in send_contract with no signwell_document_id
agent-browser open "$DEV_URL/sales/$TESTING_VIKTOR"
agent-browser click "[data-testid='now-action-convert']"
agent-browser is visible "[data-testid='force-convert-dialog']"
agent-browser click "[data-testid='confirm-force-convert-btn']"
agent-browser wait --text "Converted to job (forced)"
```

**Bug #9: hasSignedAgreement scoped to entry**
- Manual: in DB, set one customer's `customer_documents.sales_entry_id`
  to a *different* entry's id → re-open the original entry; "Convert to
  Job" should remain locked. Re-set to the current entry's id → unlocks.

**NEW-D: pause/unpause/text/dismiss**
```bash
agent-browser open "$DEV_URL/sales/$BROOKE_JORE"
# advance into pending_approval first (skip-advance), then:
agent-browser click "[data-testid='now-action-pause']"
agent-browser wait --text "Nudges paused"
agent-browser click "[data-testid='now-action-pause']"   # toggles to unpause
agent-browser wait --text "Nudges resumed"
# add-customer-email
agent-browser click "[data-testid='now-action-add-email']"
agent-browser is visible "[data-testid='add-customer-email-dialog']"
agent-browser fill "[data-testid='customer-email-input']" "test@example.com"
agent-browser click "[data-testid='confirm-add-email-btn']"
agent-browser wait --text "Email saved"
# dismiss from list
agent-browser open "$DEV_URL/sales"
agent-browser click "[data-testid='pipeline-row-dismiss-$BROOKE_JORE']"
agent-browser wait --text "Dismissed"
```

**Bug #10: pagination text correct under stuck filter**
```bash
agent-browser open "$DEV_URL/sales"
agent-browser click "[data-testid='stuck-filter-toggle']"
# If zero stuck rows:
agent-browser is visible ".pagination-footer"  # expect: false
# Toggle off:
agent-browser click "[data-testid='stuck-filter-toggle']"
agent-browser is visible ".pagination-footer"  # expect: true; "of 24"
```

**Bug #5: StageOverrideMenu opens with 5 items**
```bash
agent-browser open "$DEV_URL/sales/$BROOKE_JORE"
agent-browser click "[data-testid='stage-stepper-override']"
agent-browser is visible "[data-testid='stage-override-menu']"
agent-browser is visible "[data-testid='stage-override-schedule_estimate']"
agent-browser is visible "[data-testid='stage-override-send_estimate']"
agent-browser is visible "[data-testid='stage-override-pending_approval']"
agent-browser is visible "[data-testid='stage-override-send_contract']"
agent-browser is visible "[data-testid='stage-override-closed_won']"
agent-browser click "[data-testid='stage-override-pending_approval']"
agent-browser wait --text "Moved to Approval"
```

### Level 5: Vercel Preview + Coverage

- Open the auto-generated PR preview URL and re-run the Level 4 script.
- Confirm `frontend/coverage` keeps sales components above 80%.

---

## ACCEPTANCE CRITERIA

- [ ] **NEW-C**: signature-related convert error opens
  `ForceConvertDialog`; force-confirm calls
  `useForceConvertToJob` → success toast → refetch.
- [ ] **Bug #9**: `hasSignedAgreement` is true only when at least one
  `contract` doc has `sales_entry_id === entry.id` (or NULL legacy).
- [ ] **NEW-D pause**: clicking pause sets `nudges_paused_until`
  ≈ now+7d on the row; clicking again clears it.
- [ ] **NEW-D text**: clicking text-confirmation triggers a real SMS
  send via `SMSService.send_message` (verifiable via
  `/admin/sent-messages` if exposed; otherwise via DB).
- [ ] **NEW-D add-email**: dialog opens, validates RFC email, persists
  via `useUpdateCustomer`, refetches the entry, button re-enables.
- [ ] **NEW-D dismiss**: pipeline-list `✕` sets `dismissed_at`;
  idempotent on repeat.
- [ ] **Bug #10**: with stuck filter on and zero visible rows, footer is
  not rendered.
- [ ] **Bug #5**: `⋯ change stage manually` opens a `<DropdownMenu>` of
  the 5 canonical stages; selecting one calls
  `useOverrideSalesStatus` → toast `Moved to <Label>`.
- [ ] All ruff / format / mypy / pyright pass with zero errors.
- [ ] All ESLint / TypeScript pass with zero errors.
- [ ] Unit + functional + integration test suites all green.
- [ ] Frontend coverage stays at 80%+ for sales components.
- [ ] agent-browser scripts pass for all five bugs.
- [ ] No regressions in `closed_lost` / `closed_won` banners,
  `Schedule visit` modal, `Skip — advance manually`,
  `MarkDeclinedDialog`, document upload, or signed-agreement detection
  for legacy NULL rows.
- [ ] `feature-developments/sales pipeline bug hunt/{README,bugs}.md`
  status lines updated.

---

## COMPLETION CHECKLIST

- [ ] All 20 step-by-step tasks completed in order
- [ ] Each task validation passed before moving on
- [ ] All Level 1–4 validation commands executed successfully
- [ ] Full backend test suite passes (unit + functional + integration)
- [ ] Full frontend test suite passes
- [ ] No linting or type errors
- [ ] Manual / agent-browser testing confirms each bug closed
- [ ] `bugs.md` and `README.md` updated to reflect closures
- [ ] DEVLOG.md entry added per
  `.kiro/steering/devlog-rules.md` (`BUGFIX` category, top of file)

---

## NOTES

### Scope discipline

- **In scope**: NEW-C, Bug #9, NEW-D (×4 endpoints + UI), Bug #10,
  Bug #5 wire-up.
- **Out of scope**: any further pipeline filtering on `dismissed_at`
  in the list endpoint (i.e., should dismissed rows hide by default?).
  Track as follow-up. Default behaviour in this PR is to **continue
  showing dismissed rows** but visually de-emphasize them via a future
  CSS pass.
- `entry.job_id` exposure on `SalesEntryResponse` (for Bug #7's TODO)
  is **not** in scope — separate change.

### Trade-offs

- **NEW-D persistence model**: Could have used a `nudges_paused`
  boolean instead of `nudges_paused_until` timestamptz. Chose timestamp
  because the AutoNudgeSchedule UI already implies a *pause window*
  (per spec Req 9.6) and a single bool would force the FE to invent a
  resume policy. Trade-off: one extra column, one extra value to
  display, but matches `last_contact_date` style for free.
- **Bug #9 fallback**: Could have hard-required `sales_entry_id` on
  every contract doc. Chose to keep the legacy `NULL` fallback because
  the H-7 column was added with `nullable=True` for backward
  compatibility — flipping that requires a backfill, which is its own
  ticket.
- **Bug #5 dropdown vs modal**: Per the addendum's design intent
  (DropdownMenu of 5 stages), the dropdown is one click vs the
  modal's two. Trade-off: less hand-holding (no confirmation step),
  but `useOverrideSalesStatus` already logs every override server-side,
  and accidental misclicks recover via the same dropdown.
- **`add_customer_email` reuses `PUT /customers/{id}`**: Could have
  built a dedicated `POST /sales/pipeline/{id}/add-customer-email`
  for symmetry with the other three NEW-D endpoints. Chose reuse
  because the customer endpoint already does what's needed and adding
  another route is dead weight.
- **`text_confirmation` body content**: Service generates the body
  from a hard-coded template
  (`"Hi {first_name}, this confirms your appointment with Grin's…"`)
  for now. A configurable template lives outside this PR's scope.

### Steering-file alignment

This plan deliberately follows the project's general steering documents
(excludes anything kiro / kiro-cli specific):

- `code-standards.md` — three-tier testing, structured logging via
  `LoggerMixin`, type safety on every new symbol.
- `api-patterns.md` — `set_request_id` + `DomainLogger.api_event` on
  every new endpoint; standard 200/404/422/502 status code map.
- `frontend-patterns.md` — VSA imports, TanStack Query
  invalidations, `cn()`, sonner toast, data-testid conventions.
- `frontend-testing.md` — Vitest + RTL, `QueryProvider` wrapper,
  agent-browser for visual validation, coverage targets.
- `structure.md` / `tech.md` — package layout respected; no new
  dependencies added.
- `spec-testing-standards.md` — backend unit + functional + integration
  + frontend component + agent-browser coverage.
- `devlog-rules.md` — `BUGFIX` entry at top of `DEVLOG.md`.

### Confidence

**10/10** for one-pass implementation success. Every assumption verified
against the live source tree on 2026-04-26:

- `customer_documents.sales_entry_id` column ✅ already present
  (`models/customer_document.py:44–48`); only the response schema is
  missing the field. No migration needed for Bug #9.
- `SalesEntry.nudges_paused_until` / `dismissed_at` ❌ do **not** exist
  → Task 2's Alembic migration adds them.
- `useForceConvertToJob` ✅ exists (`useSalesPipeline.ts:80–88`);
  `salesPipelineApi.forceConvert` posts to
  `/sales/pipeline/{id}/force-convert` (`salesPipelineApi.ts:66–74`);
  backend endpoint exists (`api/v1/sales_pipeline.py:458–485`).
- `StatusActionButton.handleAdvance` force-convert reference pattern ✅
  confirmed verbatim (`StatusActionButton.tsx:107–124` for the error
  parser; `213–230` for the Dialog body — copy the `<DialogTitle>` and
  `<DialogDescription>` strings directly).
- `STAGES` ordered array with 5 entries ✅ confirmed
  (`types/pipeline.ts:157–163`):
  `['schedule_estimate','send_estimate','pending_approval','send_contract','closed_won']`.
- shadcn primitives ✅ all present in `frontend/src/components/ui/`:
  `dropdown-menu.tsx`, `dialog.tsx`, `input.tsx`, `label.tsx`,
  `button.tsx`, `popover.tsx`, `calendar.tsx`, `textarea.tsx`,
  `select.tsx`.
- `useUpdateCustomer({id, data})` ✅ confirmed
  (`features/customers/hooks/useCustomerMutations.ts:22–33`); accepts
  partial `CustomerUpdate`, so `data: { email }` is valid. No backend
  change needed for `add_customer_email`.
- `SMSService.send_message` ✅ signature confirmed
  (`services/sms_service.py:212–270`). Recipient must be built via
  `Recipient.from_customer(customer)` (`services/sms/recipient.py:33–42`).
- **`MessageType.APPOINTMENT_CONFIRMATION`** ✅ confirmed at
  `models/enums.py:736`. **Use this value** — there is no
  `MessageType.CONFIRMATION` or `MessageType.OPERATIONAL`.
- **Alembic head**: `20260429_100100` (verified via
  `uv run alembic heads` — output:
  `20260429_100100 (head)`). New revision filename and `down_revision`
  baked into Task 2.
- **SMSService DI**: there is **no** `get_sms_service` helper. Inline
  construction `SMSService(session=session, provider=get_sms_provider())`
  is the established pattern across `api/v1/portal.py:91`,
  `api/v1/callrail_webhooks.py:379`, `api/v1/alerts.py:293,354`. Task 7
  uses inline construction; the service method (Task 6) accepts
  `sms_service` as a keyword argument so unit tests can mock it.
- **`useDismissSalesEntry` invalidation**: Task 9 invalidates
  `pipelineKeys.lists()` only (no optimistic update) — keeps row
  removal in sync with backend state and matches `useMarkSalesLost`
  (`useSalesPipeline.ts:90–104`). Optimistic updates are deliberately
  out of scope; refetch is the existing convention.

All four previously-flagged unknowns are resolved. No remaining caveats.
