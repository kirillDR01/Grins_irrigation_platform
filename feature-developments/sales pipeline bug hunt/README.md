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

Tier 3 + Tier 4 bugs (NEW-C, #9, NEW-D, #10) are **still open** — they need new backend
endpoints (`pause_nudges`, `text_confirmation`, `add_customer_email`, pipeline
`dismiss`), a force-convert dialog, or doc-scoping logic.

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
| 5 | ⚠️ Deferred (kept) | `⋯ change stage manually` button is a no-op — user opted to keep the button. Wiring design drafted in `.agents/plans/sales-pipeline-tier-1-and-tier-2-bugs.md` addendum |
| 4 | ✅ Fixed (`09dc082`) | `+ pick date…` chip is a no-op |
| 8 | ✅ Fixed (`09dc082`) | Dropzone file upload is TODO stub |
| 7 | ✅ Fixed (`09dc082`) | `View Job` navigates to wrong field (`signwell_document_id`) |
| 11 | ✅ Fixed (`09dc082`) | `Mark Lost` button stays live on `closed_won` |
| **NEW-B** | ✅ Fixed (`09dc082`) | `mark_declined` skips the decline-reason modal (Req 15.7) |

### Tier 3 — Medium (still open)

| # | Status | Title |
|---|---|---|
| **NEW-C** | 🔴 Open | `convert_to_job` skips the convert modal (Req 15.3); no force-convert UI on signature failure |
| 9 | 🔴 Open | `hasSignedAgreement` matches any `contract` doc on the customer — Convert can unlock prematurely |
| **NEW-D** | 🔴 Open | `pause_nudges`, `text_confirmation`, `add_customer_email`, pipeline `dismiss` — permanent stub toasts (no backend endpoints) |

### Tier 4 — Low (still open)

| # | Status | Title |
|---|---|---|
| 10 | 🔴 Open | Pagination text shows unfiltered total when stuck filter hides rows |

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

- `text_confirmation`, `pause_nudges`, `add_customer_email`, pipeline `dismiss` — stub
  toasts (tracked as NEW-D, awaiting backend endpoints)
- `resend_estimate` — could now be wired to `emailSign.mutateAsync(entryId)` (the
  estimate-email backend was wired in `db7befa`); currently still a stub toast
- Week-Of backend column (uses `localStorage` per design decision)
- `estimate_sent_at` / `stage_entered_at` / `nudges_paused_until` backend columns
  (fall back to `updated_at` per Req 17.5)
- `entry.job_id` not yet on `SalesEntryResponse` (Bug #7's TODO)

---

## Newly-Found Bugs (detail) — original audit findings preserved

### NEW-A — `hasEmail` derives from `customer_name`, not from an email field 🟢 Fixed

**Status:** ✅ FIXED in commit `09dc082`. See "What Was Shipped" table for details.

### NEW-B — `mark_declined` skips the decline modal 🟢 Fixed

**Status:** ✅ FIXED in commit `09dc082`. New `MarkDeclinedDialog.tsx` component.

### NEW-C — `convert_to_job` skips the convert modal & has no force-convert UI 🔴 Open

**Symptom.** "Convert to Job" in the `send_contract` NowCard fires `convertToJob.mutate(entryId)`
directly. If the backend rejects with `SignatureRequiredError`, the user just sees a generic
"Failed to convert" toast — there is no force-convert escape hatch, even though
`useForceConvertToJob` exists (`useSalesPipeline.ts:80–88`) and `StatusActionButton.tsx:117–120`
already implements the pattern.

**Fix.** Mirror `StatusActionButton.handleAdvance` (`StatusActionButton.tsx:108–127`): on a
signature-related error, open a confirm dialog → on confirm, call `forceConvert.mutate`.

### NEW-D — Three NowCard actions are permanent stubs (no backend) 🔴 Open

`pause_nudges`, `text_confirmation`, and `add_customer_email` all fall into the catch-all stub
at `SalesDetail.tsx`. Backend grep confirms no endpoints exist for any of them.

These compound NEW-A (which is now fixed but `add_customer_email` is the natural in-app
fix-it path), Bug #6 (now fixed but `pause_nudges` would let admins quiet nudges they
don't want), and the post-Bug-#2 Schedule visit flow (`text_confirmation` is the natural
follow-up). Each needs a backend endpoint, then a few lines of FE wiring.

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

**Sprint 3 — Tier 3 (still open)**
10. NEW-C — surface `SignatureRequiredError` and add a force-convert dialog mirroring
    `StatusActionButton`
11. Bug #9 — narrow `hasSignedAgreement` (filter docs to those created after entry entered
    `send_contract`, or require a naming convention)
12. NEW-D — design + ship the missing endpoints (`pause_nudges`, `text_confirmation`,
    `add_customer_email`, pipeline `dismiss`)

**Sprint 4 — Tier 4 (still open)**
13. Bug #10 — when `stuckFilter` is true, render `visibleRows.length` instead of the API
    total (or hide pagination on zero rows)

**Sprint 5 — Bug #5 wire-up (design ready, implementation pending)**
14. Bug #5 (revised) — implement the addendum: dropdown of 5 stepper stages →
    `useOverrideSalesStatus` → success toast `Moved to <Label>`. See addendum at the
    bottom of `.agents/plans/sales-pipeline-tier-1-and-tier-2-bugs.md`
