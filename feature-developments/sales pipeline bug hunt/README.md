# Sales Pipeline Bug Hunt — 2026-04-23 (re-audited 2026-04-26, shipped 2026-04-26)

End-to-end audit of the `handoff-stage-walkthrough-pipeline` feature against the spec at
`.kiro/specs/handoff-stage-walkthrough-pipeline/`. Tested live against the Vercel dev
deployment:

> https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/

Login: admin / admin123 (session already held).

Primary entries used for E2E walkthrough:

| Entry | ID | Role |
|---|---|---|
| Testing Viktor | `e5690e69-203b-4139-9379-87c41da8e80e` | Send Estimate → reproduce Skip bug, then Mark Lost |
| Brooke Jore | `5607f5ca-5993-4fdc-90f5-e66e738d0c38` | Full progression Plan → Sign → Approve → Close |

## TL;DR

Original audit (2026-04-23) filed 11 bugs against commit `8693b6d`.

**Re-audit (2026-04-26, against `dev` HEAD `db7befa`):** Bugs #1 and #2 (the two
Critical user-reported bugs) were already resolved by recent commits — the Q-B gate drop
in `db7befa` unblocked Bug #1 (`Skip — advance manually`), and the
`feat(schedule-visit)` series (`dbed5f0` → `1c4772d`) shipped a real
`ScheduleVisitModal` for Bug #2. Re-audit also discovered 4 new bugs (NEW-A through
NEW-D), the most severe being NEW-A: `hasEmail` was reading `customer_name` instead of
the email field.

**Bundled fix shipped (2026-04-26, commit `09dc082`):** the plan
`.agents/plans/sales-pipeline-tier-1-and-tier-2-bugs.md` was executed and pushed to
`dev`. **8 of the 9 still-open bugs were closed** in a single PR. **Bug #5 was
deliberately skipped** — the user opted to keep the `⋯ change stage manually` button and
asked for a wiring design instead; the addendum at the bottom of the plan file describes
turning that button into a `<DropdownMenu>` of the 5 canonical stages.

**Second bundled fix shipped (2026-04-26 PM, "Tier 3 + 4 + Bug #5 wire-up"):**
the plan `.agents/plans/sales-pipeline-remaining-open-bugs.md` was executed.
**All remaining 5 open bugs are now closed**: NEW-C (force-convert dialog),
Bug #9 (`sales_entry_id`-scoped `hasSignedAgreement`), NEW-D (×4 sub-actions
+ dismiss with new persistence columns + endpoints), Bug #10 (pagination
text under filters), and Bug #5 (DropdownMenu of canonical stages).

Files: [bugs.md](./bugs.md) · [test-matrix.md](./test-matrix.md) · [screenshots/](./screenshots/)

---

## Bug Status Summary (current)

### Tier 1 — Critical

| # | Status | Title |
|---|---|---|
| 1 | ✅ Fixed (`db7befa`, 2026-04-26) | `Skip — advance manually` always fails |
| 2 | ✅ Fixed (`dbed5f0` → `1c4772d`, 2026-04-26) | `Schedule visit` doesn't open a schedule modal |
| **NEW-A** | ✅ Fixed (`09dc082`, 2026-04-26) | `hasEmail` checks `customer_name`, not email |
| 3 | ✅ Fixed (`09dc082`, 2026-04-26) | Pipeline-list row action buttons have no `onClick` |
| 6 | ✅ Fixed (`09dc082`, 2026-04-26) | `AutoNudgeSchedule` never renders |

### Tier 2 — High

| # | Status | Title |
|---|---|---|
| 5 | ✅ Fixed (Tier 3+4+#5 wire-up, 2026-04-26 PM) | `⋯ change stage manually` now wraps a `<StageOverrideMenu>` (DropdownMenu of 5 canonical stages) → `useOverrideSalesStatus` |
| 4 | ✅ Fixed (`09dc082`) | `+ pick date…` chip is a no-op |
| 8 | ✅ Fixed (`09dc082`) | Dropzone file upload is TODO stub |
| 7 | ✅ Fixed (`09dc082`) | `View Job` navigates to wrong field (`signwell_document_id`) |
| 11 | ✅ Fixed (`09dc082`) | `Mark Lost` button stays live on `closed_won` |
| **NEW-B** | ✅ Fixed (`09dc082`) | `mark_declined` skips the decline-reason modal (Req 15.7) |

### Tier 3 — Medium (closed)

| # | Status | Title |
|---|---|---|
| **NEW-C** | ✅ Fixed (Tier 3+4+#5 wire-up, 2026-04-26 PM) | `convert_to_job` now opens `<ForceConvertDialog>` on `SignatureRequiredError` (Req 15.3) |
| 9 | ✅ Fixed (Tier 3+4+#5 wire-up, 2026-04-26 PM) | `hasSignedAgreement` scoped to `entry.id` via newly-exposed `sales_entry_id` field on `CustomerDocumentResponse` |
| **NEW-D** | ✅ Fixed (Tier 3+4+#5 wire-up, 2026-04-26 PM) | All 4 stubs wired: `pause_nudges`/`unpause`, `text_confirmation` (SMS), `add_customer_email` (reuses `PUT /customers/{id}`), pipeline `dismiss` (new column + endpoint) |

### Tier 4 — Low (closed)

| # | Status | Title |
|---|---|---|
| 10 | ✅ Fixed (Tier 3+4+#5 wire-up, 2026-04-26 PM) | Pagination footer now uses `displayTotal = stuckFilter ? visibleRows.length : data.total` and hides on zero rows |

---

## What Was Shipped in `09dc082`

A single bundled PR executed the plan at
`.agents/plans/sales-pipeline-tier-1-and-tier-2-bugs.md`:

| Bug | Change |
|---|---|
| **NEW-A** | Backend: added `customer_email: Optional[str]` to `SalesEntryResponse` (`schemas/sales_pipeline.py`) and assigned it in `_entry_to_response` (`api/v1/sales_pipeline.py`). Frontend: `hasEmail = !!(entry.customer_email ?? salesCustomer?.email)` (`SalesDetail.tsx:288`); dropped the `hasCustomerEmail = hasEmail` alias |
| **#3** | `SalesPipeline.tsx`: action button → `e.stopPropagation(); onRowClick(entry)` (navigates to detail). Dismiss `✕` → `toast.info('Dismiss not wired yet — TODO(backend)')`. Added `import { toast } from 'sonner'` |
| **#4** | `NowCard.tsx`: wrapped `+ pick date…` in shadcn `<Popover>` + `<Calendar mode="single">`; `onSelect → format(d, 'MMM d') → onChange`. Aliased `Calendar` from `@/components/ui/calendar` to `CalendarPicker` to avoid colliding with the existing `lucide-react` `Calendar` icon import |
| **#6** | `SalesDetail.tsx:586–587`: passed `estimateSentAt={entry.updated_at ?? entry.created_at}` and `nudgesPaused={false}` to `<NowCard>` (with `TODO(backend)` for the eventual `estimate_sent_at` + `nudges_paused_until` columns) |
| **#7** | `SalesDetail.tsx:182–184`: dropped the `signwell_document_id` branch from `view_job`; always `navigate('/jobs')` (TODO marker for `entry.job_id` once it's exposed) |
| **#8** | `SalesDetail.tsx`: `useUploadSalesDocument` imported and instantiated; `handleFileDrop` now calls `uploadDoc.mutateAsync({ customerId, file, documentType })` with `documentType = kind === 'agreement' ? 'contract' : 'estimate'`; success toast + `refetch`; errors via `getErrorMessage` |
| **#11** | `SalesDetail.tsx`: added `isClosedWon` check; renders new `closed-won-banner` (emerald palette mirroring closed-lost) when `entry.status === 'closed_won'`; StageStepper / NowCard / ActivityStrip hidden |
| **NEW-B** | New `MarkDeclinedDialog.tsx` component (mirrors `StatusActionButton`'s Mark Lost dialog with a required `<Textarea>` reason). `mark_declined` switch case → `setMarkDeclinedOpen(true)`; on confirm, `markLost.mutate({ id, closedReason: reason.trim() })`. 5 dedicated component tests |

**Tests added:**
- 3 backend serializer unit tests (`TestEntryToResponseCustomerEmail` in
  `tests/unit/test_sales_pipeline_and_signwell.py`)
- 5 `MarkDeclinedDialog` tests
- New SalesDetail / PipelineList / NowCard cases covering NEW-A enable/disable, NEW-B
  dialog open, Bug #11 banner replaces walkthrough, Bug #3 row + dismiss, Bug #4 popover
  open / day-select format

**Validation:** all 111 sales-component tests + 27 backend unit tests pass. No new
type-check errors in modified files.

---

## What Was Shipped in the Tier 3 + 4 + Bug #5 wire-up (2026-04-26 PM)

A second bundled PR executed the plan at
`.agents/plans/sales-pipeline-remaining-open-bugs.md` — closing every
remaining open bug in this audit:

| Bug | Change |
|---|---|
| **NEW-C** | New `ForceConvertDialog.tsx` component. `SalesDetail.handleNowAction` parses `axios.isAxiosError(err) ? err.response?.data?.detail` for the `convert_to_job` case; on signature-related detail strings the dialog opens, and confirming runs the existing `useForceConvertToJob` mutation → `Converted to job (forced)` toast |
| **#9** | Backend: added `sales_entry_id: Optional[UUID]` to `CustomerDocumentResponse` (`schemas/customer_document.py`) — the column already existed (added in bughunt H-7). Frontend: extended `SalesDocument` interface with `sales_entry_id`; narrowed `SalesDetail.hasSignedAgreement` to `d.document_type === 'contract' && (d.sales_entry_id === entry.id \|\| d.sales_entry_id == null)` (legacy `null` fallback preserved) |
| **NEW-D pause/unpause** | Alembic migration `20260430_120000` adds nullable `nudges_paused_until` (timestamptz) to `sales_entries`. New service methods + endpoints `POST /sales/pipeline/{id}/{pause-nudges,unpause-nudges}` returning `SalesEntryResponse`. New hooks `usePauseNudges` / `useUnpauseNudges`. `SalesDetail.handleNowAction` `pause_nudges` case now toggles based on `entry.nudges_paused_until`. `<NowCard>` `nudgesPaused` reads the real value |
| **NEW-D text** | New `POST /sales/pipeline/{id}/send-text-confirmation` delegates to `SMSService.send_message` with `MessageType.APPOINTMENT_CONFIRMATION`. `Recipient` built via `Recipient.from_customer`. Returns `{ message_id, status }`. New `useSendTextConfirmation` hook. `SalesDetail.handleNowAction` `text_confirmation` → `sendTextConfirm.mutate` |
| **NEW-D add-email** | New `AddCustomerEmailDialog.tsx` with RFC-email-regex validation, wired to existing `useUpdateCustomer` (no new backend). `SalesDetail.handleNowAction` `add_customer_email` → `setAddEmailOpen(true)`. `onSaved` callback refetches the entry so `customer_email` re-populates and dependent buttons unlock |
| **NEW-D dismiss** | Same migration adds nullable `dismissed_at` (timestamptz) to `sales_entries`. New service `dismiss_entry` (idempotent — second call leaves timestamp untouched). New `POST /sales/pipeline/{id}/dismiss`. New `useDismissSalesEntry` hook. `SalesPipeline.PipelineRow` `pipeline-row-dismiss-{id}` → `dismiss.mutate` → `Dismissed` toast |
| **NEW-D resend (bonus)** | `SalesDetail.handleNowAction` `resend_estimate` case wired to `emailSign.mutateAsync(entryId)` (the existing email-signature endpoint shipped in `db7befa`) — no backend work needed |
| **#10** | `SalesPipeline.tsx` pagination: `displayTotal = stuckFilter ? visibleRows.length : (data?.total ?? 0)`; footer renders only when `displayTotal > 0`. Footer text and button-disabled conditions both use `displayTotal` |
| **#5** | New `StageOverrideMenu.tsx` (`<DropdownMenu>` of all 5 entries from `STAGES`). `StageStepper` prop renamed `onOverrideClick → onStageOverride: (stage: StageKey) => void`; the existing footer `stage-stepper-override` button is now wrapped by `StageOverrideMenu` (render-prop child). `SalesDetail.handleStageOverride` calls `useOverrideSalesStatus.mutateAsync` and toasts `Moved to <Label>`. The current stage is rendered as `aria-disabled` to prevent override-to-current no-ops |

**Tests added:**
- 5 new backend unit-test classes in `tests/unit/test_sales_pipeline_and_signwell.py`:
  `TestPauseUnpauseNudges`, `TestSendTextConfirmation`, `TestDismissSalesEntry`,
  `TestEntryToResponseExposesNewFields`, `TestCustomerDocumentResponseExposesSalesEntryId`
  (14 tests total)
- 5 `ForceConvertDialog` component tests
- 6 `AddCustomerEmailDialog` component tests
- 3 `StageOverrideMenu` component tests
- Updated `StageStepper.test.tsx` (renamed prop + new dropdown-flow assertions)
- Updated `SalesDetail.test.tsx` mock (added new hooks + new entry fields)
- Updated `PipelineList.test.tsx`: dismiss now asserts `useDismissSalesEntry.mutate` fires;
  added 2 Bug #10 tests covering footer-hides-on-zero and `visibleRows`-driven count

**Validation:** all 188 sales-component tests + 41 sales-pipeline backend
unit tests pass. ruff + pyright clean on every modified backend file.
TypeScript clean on every modified frontend file (project-wide pre-existing
errors in `FilterPanel.tsx`/`SalesCalendar.tsx`/etc. are untouched).

---

## What Works (spec-compliant, post-shipment)

- Type system, `STAGES`, `AGE_THRESHOLDS`, `NUDGE_CADENCE_DAYS` constants in place
- `StageStepper` renders all 5 step states (done ✓, active, waiting w/ dashed amber for
  `pending_approval`, future); phase labels Plan / Sign / Close; calendar badge under
  Schedule when `estimate_scheduled`
- `NowCard` renders all 7 variations with correct pill tone, sanitised copy, locked +
  tooltip action variants
- `ActivityStrip` shows correct event glyphs per kind
- `AgeChip` renders correct colour + glyph per bucket; suppressed on `closed_won` /
  `closed_lost`
- `closed_lost` banner replaces walkthrough correctly
- **`closed_won` banner replaces walkthrough correctly** (new in `09dc082`)
- Client approved (manual) → `send_contract` via override mutation
- Jump to Schedule → `/schedule`
- View Customer profile → `/customers/{id}`
- Week-Of picker chip selection + localStorage persistence
- **`+ pick date…` chip opens shadcn Popover + Calendar** (new in `09dc082`)
- Summary cards (Needs Estimate / Pending Approval / Needs Follow-Up / Revenue Pipeline)
- Row click + **row action button click** both navigate to `/sales/{id}` (new in `09dc082`)
- **`Skip — advance manually`** — works after Q-B gate drop (was Bug #1)
- **`Schedule visit`** — opens full modal with calendar, fields, conflicts (was Bug #2)
- **Email-for-Signature button correctly disabled when customer has no email** (new in
  `09dc082`; was NEW-A)
- **Estimate / signed-agreement dropzone uploads via `useUploadSalesDocument`** (new in
  `09dc082`; was Bug #8)
- **`AutoNudgeSchedule` renders on `pending_approval`** (new in `09dc082`; was Bug #6)
- **`mark_declined` opens `MarkDeclinedDialog` and captures `closed_reason`** (new in
  `09dc082`; was NEW-B)

## Known stubs (spec-allowed; not bugs in this PR's scope)

- ~~`text_confirmation`, `pause_nudges`, `add_customer_email`, pipeline `dismiss`~~ —
  ✅ all wired in the Tier 3+4+#5 wire-up (NEW-D resolved)
- ~~`resend_estimate`~~ — ✅ wired to `emailSign.mutateAsync(entryId)` in the
  Tier 3+4+#5 wire-up
- Week-Of backend column (uses `localStorage` per design decision)
- `estimate_sent_at` / `stage_entered_at` backend columns (fall back to
  `updated_at` per Req 17.5). `nudges_paused_until` is now a real column
  (NEW-D); `dismissed_at` is also live (NEW-D dismiss)
- `entry.job_id` not yet on `SalesEntryResponse` (Bug #7's TODO)
- The `GET /sales/pipeline` list endpoint still returns dismissed rows.
  Whether to hide them by default is **out of scope** — tracked as a
  follow-up; current behavior preserves Bug #3's row-action navigation
  for accidental dismisses

---

## Newly-Found Bugs (detail) — original audit findings preserved

### NEW-A — `hasEmail` derives from `customer_name`, not from an email field 🟢 Fixed

**Status:** ✅ FIXED in commit `09dc082`. See "What Was Shipped" table for details.

### NEW-B — `mark_declined` skips the decline modal 🟢 Fixed

**Status:** ✅ FIXED in commit `09dc082`. New `MarkDeclinedDialog.tsx` component.

### NEW-C — `convert_to_job` skips the convert modal & has no force-convert UI 🟢 Fixed

**Status:** ✅ FIXED in the Tier 3+4+#5 wire-up. New `ForceConvertDialog`;
`SalesDetail.handleNowAction` parses the axios error and opens the
dialog on signature-related details.

### NEW-D — Three NowCard actions are permanent stubs (no backend) 🟢 Fixed

**Status:** ✅ FIXED in the Tier 3+4+#5 wire-up. New Alembic migration
adds `nudges_paused_until` and `dismissed_at` columns; 4 new endpoints
ship pause/unpause/text-confirmation/dismiss. `add_customer_email`
reuses the existing `PUT /customers/{id}` route via
`<AddCustomerEmailDialog>`. `resend_estimate` was wired as a bonus to
the existing `emailSign.mutateAsync`.

---

## Recommended fix order

**Sprint 1 — Tier 1** — ✅ shipped (`09dc082`)
1. ✅ NEW-A — `hasEmail` derives from real email + new `customer_email` schema field
2. ✅ Bug #3 — row action wired; dismiss toasts a stub
3. ✅ Bug #6 — `estimateSentAt` + `nudgesPaused` passed

**Sprint 2 — Tier 2** — 5 of 6 shipped (`09dc082`)
4. ⚠️ Bug #5 — *deferred*. User opted to keep the `⋯ change stage manually` button. Design
   addendum (DropdownMenu of 5 canonical stages) drafted in
   `.agents/plans/sales-pipeline-tier-1-and-tier-2-bugs.md`; implementation pending
5. ✅ Bug #4 — Popover + Calendar wired
6. ✅ Bug #8 — `useUploadSalesDocument.mutateAsync` wired
7. ✅ Bug #7 — `view_job` always goes to `/jobs`
8. ✅ Bug #11 — `closed_won` renders a `closed-won-banner`; StageStepper hidden
9. ✅ NEW-B — `MarkDeclinedDialog` captures reason before `markLost.mutate`

**Sprint 3 — Tier 3** — ✅ shipped (Tier 3+4+#5 wire-up, 2026-04-26 PM)
10. ✅ NEW-C — `ForceConvertDialog` + axios-error parsing in
    `SalesDetail.handleNowAction`
11. ✅ Bug #9 — `CustomerDocumentResponse.sales_entry_id` exposed; FE
    narrows `hasSignedAgreement` to `entry.id` (legacy `null` fallback
    preserved)
12. ✅ NEW-D — Alembic migration + 4 new endpoints
    (`pause-nudges`, `unpause-nudges`, `send-text-confirmation`,
    `dismiss`) + `<AddCustomerEmailDialog>` reusing
    `PUT /customers/{id}`

**Sprint 4 — Tier 4** — ✅ shipped (Tier 3+4+#5 wire-up, 2026-04-26 PM)
13. ✅ Bug #10 — `displayTotal = stuckFilter ? visibleRows.length : data.total`
    + footer hidden when zero rows visible

**Sprint 5 — Bug #5 wire-up** — ✅ shipped (Tier 3+4+#5 wire-up, 2026-04-26 PM)
14. ✅ Bug #5 — `<StageOverrideMenu>` (`<DropdownMenu>` of 5 canonical
    stages) wraps the existing footer button; selecting a stage calls
    `useOverrideSalesStatus` → toast `Moved to <Label>`
