# Feature: Mobile Viewport Bug Fixes (10-bug umbrella)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

A 2026-05-02 audit (`bughunt/2026-05-02-mobile-viewport-audit.md`) catalogued ten distinct mobile-viewport rendering bugs across the technician iPhone surface, the admin pages techs occasionally touch, and two customer-facing portal pages. Three independent failure modes recur:

1. **Hardcoded `w-[560px]` inside a responsive parent** (`SheetContainer.tsx:26`) — clips every estimate / payment / tag sub-sheet a tech opens from the appointment modal.
2. **Tables wrapped in a redundant outer `overflow-hidden` card** that clips the shadcn `Table` primitive's *built-in* `overflow-x-auto` scroller — `PriceListEditor`, `JobList`, `CustomerList`, `LeadsList`, `InvoicePortal`, `EstimateReview`. Tech / customer literally cannot reach the right-half of every row.
3. **Page-level horizontal overflow** from heading-row button groups (`Sync Sheets`, `Bulk Outreach`, `+ Add Lead`) and shadcn `TabsList` rows that don't wrap or scroll — `/leads` overflows 280 px, `/marketing` 138 px, `/accounting` 151 px, `/settings` 66 px, plus the schedule resource-timeline week-view header which collapses "MONTUEWEDTHU…".

This plan turns the audit into ten ordered, atomic fixes, each with a one-line CSS / Tailwind change, an existing pattern to mirror, a Vitest assertion the change is observable in the DOM, and a manual `agent-browser` 390 × 844 viewport probe that confirms the bug is gone. No new components are introduced. The shadcn `Table` primitive at `frontend/src/components/ui/table.tsx:5-18` already provides a `relative w-full overflow-x-auto bg-white rounded-2xl shadow-sm border border-slate-100` wrapper, so most "fixes" are *removals* of the redundant outer wrapper rather than additions of new scroll containers.

## User Story

As a Grin's Irrigation **technician on an iPhone 12 Pro (390 × 844)**
I want every appointment-modal sub-sheet, list table, page header, and tabs row to fit (or horizontally pan within) my viewport
So that I can collect a payment, send an estimate, edit a tag, amend a pricelist entry, or look up a customer from the field without dragging the whole page sideways or losing access to off-screen "Edit / Save / Send" buttons.

## Problem Statement

The current dev build silently clips ~187 px off every appointment-modal sub-sheet, hides the entire right half of five tables, and forces the tech to horizontally scroll every page that has 3+ heading-row buttons or a 5-tab `TabsList`. The shadcn `Table` primitive already has horizontal scrolling built in, but six call sites wrap it in a redundant outer `overflow-hidden` that defeats it. The `SheetContainer` was authored desktop-first with a hardcoded 560 px width and no `max-w-full` clamp. Together these bugs make the tech-on-iPhone path the audit was supposed to validate effectively unusable for most primary actions, and the customer-facing portal tables (`InvoicePortal`, `EstimateReview`) silently truncate "Total" rows on long-named line items — a payment-dispute risk.

## Solution Statement

Apply ten one-line / handful-of-line Tailwind class changes — most are deletions of the redundant outer card around `<Table>` (since the primitive already supplies it). Where a sibling header (`<h3>Line Items</h3>`) lives inside the wrapper, swap `overflow-hidden` → `overflow-x-auto` instead of removing the wrapper. Add `flex-wrap` to the page-header button rows that overflow, dedupe the `/leads` page heading. Wrap the `Marketing` and `Accounting` `TabsList` in a horizontal-scroll affordance. Widen the `WeekMode` per-day grid column to 72 px min and let the timeline scroll. Clamp the `SearchableCustomerDropdown` popover width to viewport. Replace the hardcoded `w-[560px]` in `SheetContainer` with `w-full sm:w-[560px] max-w-full`. After each fix, capture a 390 × 844 screenshot in `e2e-screenshots/mobile-viewport-fixes-2026-05-02/` and diff against the bughunt screenshots to prove the regression is gone.

## Feature Metadata

**Feature Type**: Bug Fix (umbrella, 10 atomic fixes)
**Estimated Complexity**: Low — every fix is a Tailwind class change or a `<div>` removal; no new components, no API/backend touch, no migrations, no new dependencies.
**Primary Systems Affected**: Frontend only. `frontend/src/shared/components/SheetContainer.tsx`, four feature-list pages (jobs, customers, leads, pricelist), two customer-portal pages, two admin-dashboard pages, the schedule resource-timeline week mode, and one settings page.
**Dependencies**: None. All fixes use existing Tailwind utilities and existing React/shadcn primitives. The `useMediaQuery` hook (`frontend/src/shared/hooks/useMediaQuery.ts`) is available if a fix prefers a JS-side breakpoint; preferred approach is CSS-only Tailwind responsive prefixes.

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `bughunt/2026-05-02-mobile-viewport-audit.md` — full bug catalogue with file:line citations, DOM probe output, and screenshot evidence. The source of truth for every fix.
- `.agents/plans/2026-05-02-mobile-viewport-bug-audit-handoff.md` — handoff prompt that triggered the audit; documents the BUG-1 root cause and the canonical reproduction steps.
- `frontend/src/components/ui/table.tsx` (lines 5-18) — **CRITICAL**: the shadcn `Table` primitive ALREADY wraps itself in `<div className="relative w-full overflow-x-auto bg-white rounded-2xl shadow-sm border border-slate-100">`. This is why the fix for BUG-2/3/4/5 is removal of the outer wrapper, not addition of `overflow-x-auto`. Reading this file is non-negotiable — without it the fix looks wrong.
- `frontend/src/components/ui/tabs.tsx` (lines 19-33) — the shadcn `TabsList` primitive uses `inline-flex h-10 w-fit`, no horizontal scroll affordance. Confirms why `Marketing` and `Accounting` overflow.
- `frontend/src/shared/components/SheetContainer.tsx` (lines 14-30) — BUG-1 root cause. Single file edit.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 365-378) — the parent that's correctly `max-sm:w-full`. SheetContainer must not exceed this width on sm-.
- `frontend/src/features/schedule/components/AppointmentModal/EstimateSheetWrapper.tsx`, `PaymentSheetWrapper.tsx`, `TagEditorSheet.tsx` — three SheetContainer consumers that all clip on iPhone today. Should not need edits if BUG-1 fix is applied at SheetContainer.
- `frontend/src/features/pricelist/components/PriceListEditor.tsx` (lines 224-280) — BUG-2. The `<div className="rounded-md border border-slate-200 bg-white overflow-hidden">` at line 233 is the offender; the inner `<Table>` already self-wraps.
- `frontend/src/features/jobs/components/JobList.tsx` (lines 460-640) — BUG-3. Outer wrapper at line 465: `bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden`. Identical to the Table primitive's own wrapper.
- `frontend/src/features/customers/components/CustomerList.tsx` (lines 275-415) — BUG-4. Outer wrapper at line 281, identical pattern.
- `frontend/src/features/leads/components/LeadsList.tsx` (lines 395-500) — BUG-5. Two issues in one file: the heading `<div className="flex items-center gap-2">` at line 408 (no `flex-wrap`) AND the table outer wrapper at line 438. Note also that the page renders its own `<h1>Leads</h1>` at line 401 even though `frontend/src/pages/Leads.tsx` already supplies a `<PageHeader title="Leads" />`. Confirm Leads.tsx before deciding whether to drop the inner header.
- `frontend/src/pages/Leads.tsx` — short file; check whether it wraps `<LeadsList />` with `<PageHeader>` (audit notes "duplicate Leads heading"). If yes, the inner `<h1>` in `LeadsList.tsx:401` should be removed.
- `frontend/src/features/portal/components/InvoicePortal.tsx` (lines 154-179) — BUG-8a. Outer wrapper has a section header sibling (`<h3>Line Items</h3>` at line 157) so we cannot just delete the wrapper. Use `overflow-x-auto`.
- `frontend/src/features/portal/components/EstimateReview.tsx` (lines 219-233) — BUG-8b. Same shape as InvoicePortal — has a `<h3>Line Items</h3>` sibling at line 222. Use `overflow-x-auto`.
- `frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx` (lines 110-115) — BUG-7. Single-class edit on PopoverContent.
- `frontend/src/features/marketing/components/MarketingDashboard.tsx` (lines 166-185) — BUG-9a. `<TabsList>` at line 167 has no scroll affordance.
- `frontend/src/features/accounting/components/AccountingDashboard.tsx` (lines 145-153) — BUG-9b. `<TabsList>` at line 146 has no scroll affordance.
- `frontend/src/pages/Settings.tsx` (lines 280-320) — BUG-10. The "Change Password" + "Sign Out" rows at lines 284 and 302 use `flex items-center justify-between p-4` — fine on their own, but the audit measured 66 px of body overflow. Likely culprit is a flex-row higher in the file or a fixed-width element; read the surrounding 50 lines before settling on the fix.
- `frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx` (line 245) — BUG-6. `gridTemplateColumns: '200px repeat(7, minmax(0, 1fr))'`. Per-column min-width of 0 lets text from adjacent cells visually concatenate.
- `frontend/src/features/schedule/components/ResourceTimelineView/DayHeader.tsx` (lines 35-71) — for context on what the header text actually is (`MON`, `4/27`).
- `frontend/src/features/schedule/components/ResourceTimelineView/DayMode.tsx` (line 252) — comparison: Day mode uses `'200px minmax(0, 1fr)'` and is unaffected because there's only one day column.
- `frontend/src/features/schedule/components/ResourceTimelineView/MonthMode.tsx` (line 154) — already uses `minmax(28px, 1fr)`. Pattern to mirror.
- `frontend/src/shared/hooks/useMediaQuery.ts` — available if a JS-side breakpoint is needed (e.g., to default WeekMode → DayMode below `sm`). Default approach is CSS-only.
- `e2e/_lib.sh` — sources `login_admin`, `require_servers`, `agent-browser` wrapper. Use `SESSION=mobile-fix` to keep this work isolated from other parallel sessions. Read it before starting the manual validation phase.

### Existing screenshot evidence (for before/after comparison)

- `e2e-screenshots/mobile-bug-audit-2026-05-02/` — the audit's screenshots. Use these as the "before" baseline; capture matching "after" frames in `e2e-screenshots/mobile-viewport-fixes-2026-05-02/` with the same filenames.

### New Files to Create

- `e2e-screenshots/mobile-viewport-fixes-2026-05-02/` — directory for after-fix screenshots, one per bug. Filenames mirror the audit's: `bug-1-tag-editor-sheet.png`, `bug-2-pricelist-table.png`, etc.
- `frontend/src/shared/components/SheetContainer.test.tsx` — currently absent (only `Layout.test.tsx`, `StatusBadge.test.tsx`, etc. exist for shared components). Add a single Vitest test asserting that the rendered root has `w-full` AND `sm:w-[560px]` AND `max-w-full` classes — JSDOM can't measure widths but it can read `className`. This is the cheapest regression guard against someone reverting the BUG-1 fix.

No other new files. No new components. No new utilities.

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Tailwind responsive design](https://tailwindcss.com/docs/responsive-design)
  - Specific section: "max-* variants" (mobile-first then constrain) and breakpoint defaults (`sm:` = `≥640px`).
  - Why: Confirms that `sm:w-[560px]` activates at ≥ 640 px, leaving iPhone 12 Pro 390 px in the `w-full` branch. The audit relies on this `sm` breakpoint behaviour.
- [Tailwind `min`/`max`/`clamp` arbitrary values](https://tailwindcss.com/docs/width#arbitrary-values)
  - Specific section: arbitrary-value syntax for `w-[…]`, including `calc()` and `min()`.
  - Why: Required for BUG-7's `w-[min(400px,calc(100vw-1rem))]`.
- [Radix Popover — `--radix-popover-trigger-width`](https://www.radix-ui.com/primitives/docs/components/popover#origin)
  - Specific section: "Origin" → CSS variables exposed to `PopoverContent`.
  - Why: Alternative fix sketch for BUG-7 if the `min()` calc renders awkwardly. `--radix-popover-trigger-width` matches the trigger button width (typically narrower than 400 px on mobile).
- [shadcn/ui Table primitive](https://ui.shadcn.com/docs/components/table)
  - Specific section: "Anatomy" — confirms the canonical Table is an `overflow-x-auto` wrapper around a native `<table>`.
  - Why: Justifies the "remove the outer wrapper, the primitive already does it" fix for BUG-2/3/4/5.
- [shadcn/ui Tabs primitive](https://ui.shadcn.com/docs/components/tabs)
  - Specific section: "Anatomy" — confirms the upstream `TabsList` is `inline-flex` and does not scroll.
  - Why: Justifies wrapping the consumer-side `<TabsList>` rather than monkey-patching the primitive.
- [MDN — `scrollWidth` vs `clientWidth`](https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollWidth)
  - Specific section: "Determining if an element has been totally scrolled".
  - Why: Validation step in this plan uses `document.body.scrollWidth - document.body.clientWidth === 0` to assert "no horizontal overflow at the page level". The audit used the same probe.

### Patterns to Follow

**The "Table inside a feature list page" canonical pattern (post-fix):**

```tsx
// CORRECT — let the Table primitive supply its own card chrome and overflow-x-auto wrapper.
<Table data-testid="leads-table">
  <TableHeader>…</TableHeader>
  <TableBody>…</TableBody>
</Table>
```

```tsx
// WRONG — double-wraps the table. Outer `overflow-hidden` clips the inner overflow-x-auto.
// This is the antipattern present in JobList:465, CustomerList:281, LeadsList:438, PriceListEditor:233.
<div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
  <Table data-testid="leads-table">…</Table>
</div>
```

**The "Table with a section heading sibling" pattern (InvoicePortal / EstimateReview):**

```tsx
// FIX: keep the outer wrapper (it carries the heading sibling), but allow horizontal scroll.
<div className="bg-white rounded-xl border border-slate-200 overflow-x-auto">
  <div className="p-4 border-b border-slate-100">
    <h3 className="font-semibold text-slate-800">Line Items</h3>
  </div>
  <Table data-testid="invoice-line-items-table">…</Table>
</div>
```

The Table primitive's own wrapper still scrolls, but with the outer changed from `overflow-hidden` to `overflow-x-auto`, the outer becomes the effective scroll container and the doubled chrome stays visually contained. Acceptable trade-off for the section-heading case.

---

### THE "2-1 PATTERN" — Table-wrapper fix decision matrix (memorize this)

Every table-clip fix in this plan resolves to **exactly one of two variants**. Six bugs map to one or the other; misclassifying breaks the visual chrome. Decision is by inspection of the outer wrapper's contents.

| Variant | When to apply | Action | Sites |
|---|---|---|---|
| **Variant 1 — Remove wrapper** | Wrapper contains *only* `<Table>` (no sibling heading, no sibling button, no sibling divider). | Delete the `<div className="… overflow-hidden">` opening + matching closing `</div>`. The shadcn `Table` primitive at `frontend/src/components/ui/table.tsx:5-18` already supplies card chrome (`bg-white rounded-2xl shadow-sm border border-slate-100`) AND `overflow-x-auto`. Removing yields one card with horizontal scroll. | BUG-2 (`PriceListEditor:233`), BUG-3 (`JobList:465`), BUG-4 (`CustomerList:281`), BUG-5b (`LeadsList:438`) |
| **Variant 2 — Swap overflow class** | Wrapper contains `<Table>` AND a sibling — typically a `<div className="p-4 border-b"><h3>…</h3></div>` section header. Removing the wrapper would orphan the sibling. | Change wrapper class from `overflow-hidden` → `overflow-x-auto`. Single token swap. The Table primitive's inner scroller is now nested inside an outer scroller; both render the same effective behaviour. | BUG-8a (`InvoicePortal:155`), BUG-8b (`EstimateReview:220`) |

**Decision recipe** — before editing any of the six sites, run this grep on the file and inspect 5 lines below the wrapper's opening tag:

```bash
# Replace TARGET with the file path. Show 8 lines after the wrapper line.
grep -nA 8 'overflow-hidden' "$TARGET"
```

If the next non-whitespace child after the wrapper opening is `<Table` → **Variant 1**.
If the next non-whitespace child is `<div` (a sibling) → **Variant 2**.

This is the **2-1 pattern**: 4 sites take Variant 1, 2 sites take Variant 2. Memorize the count — if the implementer ends up with 5 removals or 3 swaps, something has been misclassified.

**The "scrollable TabsList" pattern (apply at consumer, not primitive):**

```tsx
<Tabs value={activeTab} onValueChange={setActiveTab}>
  <div className="overflow-x-auto -mx-4 px-4 pb-1">
    <TabsList data-testid="marketing-tabs">
      <TabsTrigger value="overview">Overview</TabsTrigger>
      …
    </TabsList>
  </div>
  …
</Tabs>
```

`-mx-4 px-4` lets the scroll affordance bleed to the edge of a `px-4` page container without visually jutting. `pb-1` reserves space for the (usually invisible) horizontal scrollbar so it doesn't crowd the content below.

**The "responsive width with mobile fallback" pattern (BUG-1):**

```tsx
// SheetContainer.tsx — NEW
className={cn(
  'flex flex-col w-full sm:w-[560px] max-w-full bg-white rounded-t-[20px] border border-[#E5E7EB]',
  'shadow-[0_-4px_24px_rgba(0,0,0,0.12)]',
  className,
)}
```

Mirror the parent `AppointmentModal.tsx:374` which uses `max-sm:w-full` for the same intent. The `max-w-full` is a belt-and-braces clamp — even if a future change reorders or omits the `sm:` prefix, the sheet can never exceed its parent.

**The "wrappable button row" pattern (BUG-5, BUG-10):**

```tsx
// LeadsList.tsx:399 — NEW
<div className="flex flex-wrap items-center justify-between gap-2">
  …
</div>
```

Adding `flex-wrap` lets the button group drop to a second line on narrow viewports rather than pushing past the right edge. Audit-confirmed working pattern: `LeadFilters.tsx` already does this on the same page.

**The "wider grid column with horizontal scroll" pattern (BUG-6):**

```tsx
// WeekMode.tsx:245 — NEW
gridTemplateColumns: '200px repeat(7, minmax(72px, 1fr))',
```

72 px is "MON" (~36 px) + "4/27" (~32 px) + 4 px breathing room. Combined with the existing `<div className="overflow-x-auto">` wrapper that the resource-timeline already uses on the parent (verify in `index.tsx:120` — `overflow-hidden` currently; will need to swap to `overflow-x-auto` so the grid can pan), the user can horizontally scroll on iPhone instead of seeing concatenated text.

**Naming Conventions (from `.kiro/steering/structure.md` and observed):**

- Component files: `PascalCase.tsx` co-located with `PascalCase.test.tsx`.
- `data-testid` convention: kebab-case, `{feature}-{element}` (e.g., `leads-table`, `marketing-tabs`).
- Tailwind class strings: arbitrary values in `[]` — `w-[560px]`, `min-h-[44px]`, `gap-[5px]`.

**Error Handling:**

N/A — these are pure CSS / DOM-class changes. No runtime branches, no try/catch. If a fix breaks a Vitest assertion, the test fails loudly; that's the only error surface.

**Logging Pattern:**

N/A — frontend layout fixes don't add logging.

**Other Relevant Patterns:**

- The `useMediaQuery('(max-width: 767px)')` hook is the established way to JS-branch on mobile viewports. **Do not** introduce JS-side breakpoints unless a CSS-only fix is impossible. Tailwind `sm:`, `md:`, `lg:` prefixes are preferred.
- Frontend tests use `Vitest + React Testing Library` (`frontend/.kiro/steering/frontend-testing.md`). Component tests live next to components: `Foo.tsx` → `Foo.test.tsx`.
- The `cn()` helper at `@/shared/utils/cn` (re-exported via `@/lib/utils`) merges Tailwind classes and dedupes conflicts. Use it when conditionally combining.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (P0 — appointment-modal sub-sheet)

The single biggest blast-radius fix. Without this, every estimate / payment / tag action a tech opens from the appointment modal clips ~187 px on iPhone 12 Pro. One file, three lines of edits, one new test file.

**Tasks:**

- Update `SheetContainer.tsx` width classes from `w-[560px]` to `w-full sm:w-[560px] max-w-full`.
- Add a `SheetContainer.test.tsx` regression guard.

### Phase 2: Core Implementation (P0/P1 — table-clip antipattern)

Five files share the same antipattern: a redundant outer `overflow-hidden` card around a shadcn `<Table>` whose primitive already provides the same chrome and an `overflow-x-auto` scroller. Four are removable; two (the customer-portal pages with section-heading siblings) need the wrapper kept but `overflow-hidden` → `overflow-x-auto`.

**Tasks:**

- Remove outer wrapper from `JobList.tsx:465`, `CustomerList.tsx:281`, `LeadsList.tsx:438`, `PriceListEditor.tsx:233`.
- Swap `overflow-hidden` → `overflow-x-auto` on `InvoicePortal.tsx:155` and `EstimateReview.tsx:220`.

### Phase 3: Integration (P1/P2 — page-level overflow)

Heading-row button groups, `TabsList`, and the resource-timeline week-view grid. Each is a small Tailwind-only edit at the consumer level.

**Tasks:**

- Add `flex-wrap` to `LeadsList.tsx:408` heading button row.
- Dedupe the `Leads` `<h1>` in `LeadsList.tsx:401` if `Leads.tsx` already supplies `<PageHeader title="Leads" />`.
- Wrap `MarketingDashboard.tsx:167` and `AccountingDashboard.tsx:146` `<TabsList>` in a horizontally-scrollable div.
- Widen `WeekMode.tsx:245` per-day column min-width from 0 → 72 px AND swap the parent `ResourceTimelineView/index.tsx:120` outer `overflow-hidden` → `overflow-x-auto`.
- Clamp `SearchableCustomerDropdown.tsx:111-112` PopoverContent width to viewport.
- Investigate + fix the 66 px overflow on `Settings.tsx`. Read 30 lines around the password / sign-out rows; the most likely culprit is the parent `<Card>` width or a sibling header row, not the documented buttons themselves.

### Phase 4: Testing & Validation

Vitest assertions where the bug is observable in the rendered DOM. `agent-browser` 390 × 844 manual probes for visual confirmation, with screenshots committed to `e2e-screenshots/mobile-viewport-fixes-2026-05-02/`.

**Tasks:**

- Add / update Vitest assertions in `SheetContainer.test.tsx`, `LeadsList.test.tsx`, `JobList.test.tsx`, `CustomerList.test.tsx` to lock in the fixed class strings.
- Capture `agent-browser` screenshots at 390 × 844 for each bug, plus a `document.body.scrollWidth - document.body.clientWidth` probe asserting === 0 (or === expected scrollable region for the WeekMode case).
- Run the full frontend test suite (`npm test`) and typecheck (`npm run typecheck`) — zero new failures.
- Optional: `npm run lint` to catch any ESLint regressions.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

Each editing task (Tasks 1, 3-13) follows the same enforced sub-rhythm:
1. **Pre-flight** — run a `grep -n` to verify the target string is at the expected line. If line drifted, abort and re-anchor by string match. This is non-optional; line numbers from the audit may have drifted since 2026-05-02.
2. **Capture BEFORE screenshot** — open the page at 390 × 844, screenshot to `e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/bug-{N}-{slug}.png`, run the `bodyOverflow` DOM probe, record the value.
3. **Edit** — apply the documented change.
4. **Capture AFTER screenshot** — same URL + viewport, save to `e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-{N}-{slug}.png`, run the `bodyOverflow` probe, confirm it matches the expected post-fix value (usually 0).
5. **Run unit test(s)** for the edited file.
6. **Visually diff** the before/after PNGs (`open` both files in Preview side-by-side, or use `compare` from ImageMagick if available).

The before/after directory split is intentional: a reviewer can flip through the two folders side-by-side to verify every fix at a glance, and the "before" frames serve as a regression baseline if any fix needs to be reverted.

### Task 0 — SETUP environment + capture all BEFORE screenshots (one-shot)

- **IMPLEMENT**: Open `agent-browser` at iPhone 12 Pro viewport, log in as admin once, then walk every audited URL and write a `before/` screenshot + `bodyOverflow` reading. Doing this up front (rather than threaded through each task) makes the "did the fix actually change anything?" diff obvious and guards against an editor accidentally taking the BEFORE shot after the edit landed.
- **COMMAND**:
  ```bash
  set -euo pipefail
  cd /Users/kirillrakitin/Grins_irrigation_platform
  source e2e/_lib.sh
  require_tooling
  require_servers
  mkdir -p e2e-screenshots/mobile-viewport-fixes-2026-05-02/before
  mkdir -p e2e-screenshots/mobile-viewport-fixes-2026-05-02/after
  mkdir -p e2e-screenshots/mobile-viewport-fixes-2026-05-02/diffs
  agent-browser --session mobile-fix set viewport 390 844
  SESSION=mobile-fix login_admin

  # Map of bug → URL → slug
  declare -a TARGETS=(
    "bug-2-pricelist|/invoices?tab=pricelist"
    "bug-3-jobs|/jobs"
    "bug-4-customers|/customers"
    "bug-5-leads|/leads"
    "bug-6-schedule-week|/schedule"
    "bug-9a-marketing|/marketing"
    "bug-9b-accounting|/accounting"
    "bug-10-settings|/settings"
  )
  : > e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/_overflow.tsv
  for entry in "${TARGETS[@]}"; do
    slug="${entry%%|*}"
    path="${entry##*|}"
    agent-browser --session mobile-fix open "http://localhost:5173$path"
    agent-browser --session mobile-fix wait --load networkidle
    agent-browser --session mobile-fix screenshot "e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/${slug}.png"
    overflow=$(agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth")
    printf '%s\t%s\t%s\n' "$slug" "$path" "$overflow" >> e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/_overflow.tsv
  done

  # BUG-1: SheetContainer — separate flow, requires drilling into appointment modal
  agent-browser --session mobile-fix open http://localhost:5173/schedule
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix eval "document.querySelector('[data-testid^=appt-card-]')?.click()"
  sleep 1
  agent-browser --session mobile-fix wait "[data-testid=appointment-modal]"
  agent-browser --session mobile-fix screenshot "e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/bug-1-modal-default.png"
  # Find and click the Edit tags button (testid name may vary — fall back to text match)
  agent-browser --session mobile-fix eval "Array.from(document.querySelectorAll('button')).find(b => /edit tags/i.test(b.textContent||''))?.click()"
  sleep 1
  agent-browser --session mobile-fix screenshot "e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/bug-1-tag-editor-sheet.png"

  cat e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/_overflow.tsv
  ```
- **PATTERN**: Mirrors the audit handoff session prelude at `.agents/plans/2026-05-02-mobile-viewport-bug-audit-handoff.md:91-99`. Uses `SESSION=mobile-fix` to isolate from any audit session still alive.
- **GOTCHA**: BUG-7 (SearchableCustomerDropdown) and BUG-8a/b (portal pages) are intentionally skipped here — they cannot be live-reproduced (the audit failed to reach them too). Their AFTER capture in Task 14 will also be skipped; the source diff is the artifact.
- **GOTCHA**: If `agent-browser` daemon flakes (`EAGAIN`), kill and restart per `.agents/plans/2026-05-02-mobile-viewport-bug-audit-handoff.md:148`. Restart adds ~30s; do not silently retry-loop.
- **VALIDATE**: `_overflow.tsv` should contain ~8 rows. Expected pre-fix values, per the audit:
  - `bug-5-leads` → ≈ 280
  - `bug-9a-marketing` → ≈ 138
  - `bug-9b-accounting` → ≈ 151
  - `bug-10-settings` → ≈ 66
  - others → 0 (the bug is *inside* the table, not at body level)
  If any of these values drifts dramatically (e.g., `bug-5-leads` reads 0), some other commit since the audit fixed the bug independently — re-read the relevant file before proceeding to confirm the antipattern still exists.

### Task 1 — UPDATE `frontend/src/shared/components/SheetContainer.tsx` (BUG-1, P0)

- **PRE-FLIGHT**: `grep -n 'w-\[560px\]' frontend/src/shared/components/SheetContainer.tsx` → must return exactly one match: `26:        'flex flex-col w-[560px] bg-white rounded-t-[20px] border border-[#E5E7EB]',`. If line number differs, anchor by the unique class string `flex flex-col w-[560px] bg-white rounded-t-[20px]`.
- **IMPLEMENT**: Replace `'flex flex-col w-[560px] bg-white rounded-t-[20px] border border-[#E5E7EB]'` with `'flex flex-col w-full sm:w-[560px] max-w-full bg-white rounded-t-[20px] border border-[#E5E7EB]'`. No other changes.
- **PATTERN**: Mirror parent at `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx:371-374` (`sm:w-[560px]` + `max-sm:w-full`). The `max-w-full` is belt-and-braces.
- **IMPORTS**: None changed — `cn` from `@/shared/utils/cn` already imported at line 2.
- **GOTCHA**: Do **not** remove the desktop 560 px width. Keep `sm:w-[560px]`.
- **GOTCHA**: No existing `SheetContainer.test.tsx` — Task 2 creates one.
- **POST-EDIT VERIFY**: `grep -n 'w-full sm:w-\[560px\] max-w-full' frontend/src/shared/components/SheetContainer.tsx` → exactly one match.
- **CAPTURE AFTER**: Re-run the BUG-1 click flow from Task 0 and screenshot to `e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-1-tag-editor-sheet.png`. Visually compare against `before/bug-1-tag-editor-sheet.png` — "Save tag" button must be fully visible (was clipped); "+ Difficult" chip must read "+ Difficult" not "+ Difficul"; subtitle must read "…past and future" not "…across every job — pas".
- **VALIDATE**: `cd frontend && npm run typecheck` — zero new errors. Open `after/bug-1-tag-editor-sheet.png` and `before/bug-1-tag-editor-sheet.png` side-by-side: the after frame must show the right edge of the sheet aligned to the right edge of the modal, with no clipping.

### Task 2 — CREATE `frontend/src/shared/components/SheetContainer.test.tsx` (BUG-1 regression guard)

- **PRE-FLIGHT**: `ls frontend/src/shared/components/SheetContainer.test.tsx 2>/dev/null` → must return *no such file* (else this task is skip-or-merge, not create).
- **IMPLEMENT**: One Vitest spec that renders `<SheetContainer title="t" onClose={() => {}}>x</SheetContainer>` and asserts the root element's `className` includes all of `w-full`, `sm:w-[560px]`, `max-w-full`. Selector: `container.querySelector('div.flex.flex-col')` (the SheetContainer root is the only `flex flex-col` direct descendant).
- **PATTERN**: Mirror `frontend/src/shared/components/Layout.test.tsx` lines 1-10 for imports.
- **IMPORTS**:
  ```ts
  import { describe, it, expect } from 'vitest';
  import { render } from '@testing-library/react';
  import { SheetContainer } from './SheetContainer';
  ```
- **REFERENCE TEST BODY** (use as-is unless a closer pattern in the repo argues otherwise):
  ```tsx
  describe('SheetContainer', () => {
    it('renders root with responsive width tokens (regression guard for BUG-1)', () => {
      const { container } = render(
        <SheetContainer title="Tag editor" onClose={() => {}}>
          <p>body</p>
        </SheetContainer>,
      );
      const root = container.querySelector('div.flex.flex-col');
      expect(root).not.toBeNull();
      const className = root!.className;
      expect(className).toContain('w-full');
      expect(className).toContain('sm:w-[560px]');
      expect(className).toContain('max-w-full');
      expect(className).not.toMatch(/(?<!sm:)w-\[560px\]/);
    });
  });
  ```
- **GOTCHA**: JSDOM can't measure widths reliably; assert on `className` only.
- **GOTCHA**: The `(?<!sm:)w-\[560px\]` lookbehind ensures the test fails if anyone reverts to the unprefixed `w-[560px]` while keeping the `sm:`-prefixed one.
- **VALIDATE**: `cd frontend && npm test SheetContainer` → 1 file, 1 test, passing. Then revert SheetContainer.tsx temporarily to the broken `w-[560px]`, re-run, confirm the test FAILS — proves the guard works. Re-apply Task 1 fix.

### Task 3 — UPDATE `frontend/src/features/pricelist/components/PriceListEditor.tsx` (BUG-2, P0) — VARIANT 1 (remove wrapper)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'rounded-md border border-slate-200 bg-white overflow-hidden' frontend/src/features/pricelist/components/PriceListEditor.tsx
  ```
  Must return exactly one line (audit said line 233 — accept any line number, the unique class string is the anchor).
- **VARIANT CHECK**: Read 3 lines after the wrapper opening. The next non-whitespace child must be `<Table data-testid="price-list-table">`. If a sibling `<div>` precedes the `<Table>`, escalate to Variant 2 instead — but the audit confirmed Variant 1 here.
- **IMPLEMENT**: Delete `<div className="rounded-md border border-slate-200 bg-white overflow-hidden">` opening tag and its matching `</div>`. To find the matching close: from the wrapper's opening line, count net-open `<div>`s; the matching `</div>` is the one that brings the net to -1. Audit estimated line ≈ 295. The `<Table>` becomes a direct child of the conditional `{!isLoading && !isError && (…)}` block.
- **PATTERN**: 2-1 pattern Variant 1. Table primitive at `frontend/src/components/ui/table.tsx:5-18` supplies replacement chrome.
- **IMPORTS**: None changed.
- **GOTCHA**: The original wrapper is `rounded-md` (6 px); Table primitive is `rounded-2xl` (16 px) + a small `shadow-sm`. Visual diff is intentional — makes Pricelist match Jobs/Customers/Leads.
- **GOTCHA**: A separate `<div>` above the table holds the search input + filter pills (line ~210-222). Do **not** touch it; only the wrapper that directly contains `<Table>`.
- **POST-EDIT VERIFY**:
  ```bash
  ! grep -n 'rounded-md border border-slate-200 bg-white overflow-hidden' frontend/src/features/pricelist/components/PriceListEditor.tsx  # must NOT match
  grep -n 'data-testid="price-list-table"' frontend/src/features/pricelist/components/PriceListEditor.tsx  # must still match exactly once
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/invoices?tab=pricelist
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-2-pricelist.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0
  agent-browser --session mobile-fix eval "document.querySelector('[data-testid=price-list-table]')?.closest('[data-slot=table-container]')?.scrollWidth"  # expect ≥ 1438 (table can scroll inside its card)
  ```
- **VALIDATE**: `cd frontend && npm run typecheck && npm test PriceListEditor`. Diff `before/bug-2-pricelist.png` vs `after/bug-2-pricelist.png` — after frame must show a horizontal scrollbar at the table boundary; swipe horizontally in browser must reveal Customer / Category / Pricing model / Status / Actions columns.

### Task 4 — UPDATE `frontend/src/features/jobs/components/JobList.tsx` (BUG-3, P0) — VARIANT 1 (remove wrapper)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/jobs/components/JobList.tsx
  grep -n 'data-testid="job-table"' frontend/src/features/jobs/components/JobList.tsx
  ```
  First grep returns the wrapper line (audit: 465). Second returns the `<Table>` line (audit: 602). Both must return exactly one match. If the wrapper grep returns multiple, the file has more than one card section — only delete the one whose matching close pairs with the `<Table>` block.
- **VARIANT CHECK**: The next non-whitespace content after the wrapper opening must be the `<Table>` (with possibly a multi-line opening). Run `awk` to confirm:
  ```bash
  awk 'NR>=465 && NR<=605 && !/^[[:space:]]*$/ {print NR": "$0}' frontend/src/features/jobs/components/JobList.tsx | head -8
  ```
  Expected output: line 465 (wrapper open), line 602 (`<Table` open), no sibling `<div>` in between except inside the `<Table>` itself.
- **IMPLEMENT**: Delete the wrapper opening tag and its matching `</div>`. Find matching `</div>` via net-open count starting at the wrapper line.
- **PATTERN**: 2-1 pattern Variant 1.
- **IMPORTS**: None changed.
- **GOTCHA**: `JobList.tsx` is ~700 lines. The intervening content between wrapper open (465) and `<Table>` open (602) likely contains the `react-table` setup or pagination — those are siblings to the wrapper, not children. Re-read the file to be sure.
- **POST-EDIT VERIFY**:
  ```bash
  ! grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/jobs/components/JobList.tsx
  cd frontend && npm run typecheck  # catches unbalanced JSX
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/jobs
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-3-jobs.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0
  ```
- **VALIDATE**: `cd frontend && npm test JobList` — zero new failures. Diff before/after PNGs — after frame must show table chrome with internal horizontal scroll; status / source / customer / scheduled-for / actions reachable via swipe.

### Task 5 — UPDATE `frontend/src/features/customers/components/CustomerList.tsx` (BUG-4, P1) — VARIANT 1 (remove wrapper)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/customers/components/CustomerList.tsx
  grep -n 'data-testid="customer-table"' frontend/src/features/customers/components/CustomerList.tsx
  ```
  Audit values: 281 and 383. Both must return exactly one match.
- **VARIANT CHECK**: Same as Task 4 — confirm no sibling `<div>` between wrapper open and `<Table>` open.
- **IMPLEMENT**: Delete the wrapper opening + matching `</div>`.
- **PATTERN**: 2-1 pattern Variant 1.
- **IMPORTS**: None changed.
- **GOTCHA**: Same as Task 4. The wrapper-to-Table gap (~100 lines) likely contains react-table setup; do not delete those.
- **POST-EDIT VERIFY**:
  ```bash
  ! grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/customers/components/CustomerList.tsx
  cd frontend && npm run typecheck
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/customers
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-4-customers.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0
  ```
- **VALIDATE**: `cd frontend && npm test CustomerList`. Diff PNGs — phone column shows full digits, email shows full address, actions reachable.

### Task 6 — UPDATE `frontend/src/features/leads/components/LeadsList.tsx` (BUG-5, P1) — VARIANT 1 + heading edits, three sub-tasks in one file

- **PRE-FLIGHT**:
  ```bash
  # (a) heading row
  grep -n 'flex items-center justify-between' frontend/src/features/leads/components/LeadsList.tsx | head -3   # audit: line 399 is the page header row (NOT the inner button group at 408)
  # (b) table wrapper
  grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/leads/components/LeadsList.tsx
  grep -n 'data-testid="leads-table"' frontend/src/features/leads/components/LeadsList.tsx
  # (c) duplicate heading check
  grep -n 'Leads' frontend/src/pages/Leads.tsx
  grep -n '<PageHeader' frontend/src/pages/Leads.tsx
  ```
  Confirm: wrapper grep returns line ≈ 438; `<Table>` grep returns line ≈ 439; `Leads.tsx` is short — read whole file to determine (c)'s applicability.
- **IMPLEMENT (a)**: At the page-header row (line ≈ 399), change `<div className="flex items-center justify-between">` to `<div className="flex flex-wrap items-center justify-between gap-2">`. **Critical**: this is the OUTERMOST `flex items-center justify-between` of `LeadsList`'s render. The inner button group at line 408 `<div className="flex items-center gap-2">` is a *different* element — do NOT add `flex-wrap` there.
- **IMPLEMENT (b)** — VARIANT 1: Delete the wrapper at line ≈ 438 and its matching `</div>`. Same procedure as Task 4.
- **IMPLEMENT (c)**: Conditional. If `pages/Leads.tsx` renders `<PageHeader title="Leads" …/>` AND `<LeadsList />`, then in `LeadsList.tsx` delete the inner header block (the `<div>` containing `<h1 className="text-2xl font-bold text-slate-800">Leads</h1>` and the `{data.total} … total` paragraph — lines ≈ 400-407). Decide where the `total` count goes:
  - **Option C1** (preferred): Lift it to `Leads.tsx`'s `<PageHeader description={…}>` — but this requires `Leads.tsx` to also call `useLeads(...)`, which causes a duplicate query. Skip.
  - **Option C2** (recommended): Move `{data.total} leads total` to a small inline element above the FollowUpQueue (line ≈ 432) like `<p className="text-sm text-slate-500">{data.total} {data.total === 1 ? 'lead' : 'leads'} total</p>`. Removes the `<h1>` duplication, keeps the count visible, no extra query.
  - **Option C3** (defer): If `Leads.tsx` does NOT render `<PageHeader title="Leads">`, skip (c) entirely. Document in the commit message: "BUG-5(c) skipped: no duplicate heading; LeadsList.tsx is the sole renderer of the Leads h1".
- **PATTERN**: (a) mirrors any `flex-wrap` usage in the file (grep first). (b) is 2-1 pattern Variant 1. (c) keeps `frontend/src/shared/components/PageHeader.tsx:9` API unchanged.
- **IMPORTS**: None changed.
- **GOTCHA**: `LeadsList.test.tsx` may assert `screen.getByRole('heading', { name: /leads/i })`. If sub-task (c) deletes the `<h1>`, the test will fail because the only `<h1>` then lives in `PageHeader` (rendered above `LeadsList` in the route, not inside it). Update the test to use `screen.queryByRole('heading', …)` and assert null OR drop the assertion.
- **POST-EDIT VERIFY**:
  ```bash
  grep -n 'flex flex-wrap items-center justify-between' frontend/src/features/leads/components/LeadsList.tsx  # exactly 1 match
  ! grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/leads/components/LeadsList.tsx
  cd frontend && npm run typecheck
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/leads
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-5-leads.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0 (was 280)
  agent-browser --session mobile-fix eval "document.querySelectorAll('h1').length"  # if (c) applied, expect 1; else expect 2
  ```
- **VALIDATE**: `cd frontend && npm test LeadsList`. Diff PNGs — heading row wraps to 2 lines OR fits in 1; `+ Add Lead` button visible without horizontal page scroll; leads table scrolls within its card.

### Task 7 — UPDATE `frontend/src/features/portal/components/InvoicePortal.tsx` (BUG-8a, P1) — VARIANT 2 (swap class)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'bg-white rounded-xl border border-slate-200 overflow-hidden' frontend/src/features/portal/components/InvoicePortal.tsx
  # Confirm this is the line-items section by checking the next 3 lines for "Line Items"
  awk 'NR>=155 && NR<=160' frontend/src/features/portal/components/InvoicePortal.tsx
  ```
  Expect line ≈ 155 + a header sibling (`<h3>Line Items</h3>`) — confirms VARIANT 2 (do NOT remove wrapper).
- **VARIANT CHECK**: The wrapper has TWO children: a `<div>` heading section AND a `<Table>`. Removing the wrapper would orphan the heading. → Variant 2.
- **IMPLEMENT**: Change the wrapper class `overflow-hidden` → `overflow-x-auto`. Final class string: `bg-white rounded-xl border border-slate-200 overflow-x-auto`.
- **PATTERN**: 2-1 pattern Variant 2.
- **IMPORTS**: None changed.
- **GOTCHA**: Two nested `overflow-x-auto` containers (outer card + Table primitive) is intentional and harmless — the wider table pins the inner scroller; the outer becomes effective. Don't try to "clean up" by removing one.
- **GOTCHA**: Customer-facing page; live `/portal/invoices/{token}` capture needs a real token. Skip live capture, use a Vitest render with mock data instead.
- **POST-EDIT VERIFY**:
  ```bash
  grep -n 'bg-white rounded-xl border border-slate-200 overflow-x-auto' frontend/src/features/portal/components/InvoicePortal.tsx  # exactly 1 match
  ! grep -n 'bg-white rounded-xl border border-slate-200 overflow-hidden' frontend/src/features/portal/components/InvoicePortal.tsx
  ```
- **CAPTURE AFTER (best-effort)**: If a portal token is available, capture `after/bug-8a-invoice-portal.png`. Otherwise: `cd frontend && npm test InvoicePortal -- --reporter=verbose` and inspect the rendered HTML in the test output for the `overflow-x-auto` class. Document "no live capture; source diff is the artifact" in the commit message.
- **VALIDATE**: `cd frontend && npm test InvoicePortal`. Read line ≈ 155 to confirm only one token changed.

### Task 8 — UPDATE `frontend/src/features/portal/components/EstimateReview.tsx` (BUG-8b, P1) — VARIANT 2 (swap class)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'bg-white rounded-xl border border-slate-200 overflow-hidden' frontend/src/features/portal/components/EstimateReview.tsx
  awk 'NR>=220 && NR<=225' frontend/src/features/portal/components/EstimateReview.tsx
  ```
  Expect a `<h3>Line Items</h3>` heading sibling — confirms VARIANT 2.
- **VARIANT CHECK**: Same shape as Task 7 — wrapper has heading + `<LineItemsTable>` (or `<Table>`) children. → Variant 2.
- **IMPLEMENT**: Change wrapper class `overflow-hidden` → `overflow-x-auto`. Final class: `bg-white rounded-xl border border-slate-200 overflow-x-auto`.
- **PATTERN**: 2-1 pattern Variant 2.
- **IMPORTS**: None changed.
- **GOTCHA**: Same as Task 7. The child here is `<LineItemsTable>` (a wrapper component), which itself renders a `<Table>` underneath. Behaviour is identical.
- **POST-EDIT VERIFY**:
  ```bash
  grep -n 'bg-white rounded-xl border border-slate-200 overflow-x-auto' frontend/src/features/portal/components/EstimateReview.tsx  # 1 match
  ! grep -n 'bg-white rounded-xl border border-slate-200 overflow-hidden' frontend/src/features/portal/components/EstimateReview.tsx
  ```
- **CAPTURE AFTER**: Best-effort, same as Task 7. If portal token available, screenshot `after/bug-8b-estimate-review.png` at 390 × 844 with a long-named line item.
- **VALIDATE**: `cd frontend && npm test EstimateReview`. Read line ≈ 220 to confirm only one token changed.

### Task 9 — UPDATE `frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx` (BUG-7, P2)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'w-\[400px\] p-0 bg-white rounded-lg shadow-lg border border-slate-100' frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx
  ```
  Audit: line 112. Exactly one match.
- **IMPLEMENT**: Change `w-[400px]` to `w-[min(400px,calc(100vw-1rem))]`. Final class: `w-[min(400px,calc(100vw-1rem))] p-0 bg-white rounded-lg shadow-lg border border-slate-100`.
- **PATTERN**: Tailwind arbitrary value + CSS `min()` + `calc()`.
- **IMPORTS**: None changed.
- **GOTCHA**: Tailwind v3+ requires no spaces in arbitrary values — `min(400px,calc(100vw-1rem))` (NO spaces around the comma; NO spaces inside `calc()`). Using `min(400px, calc(100vw - 1rem))` will fail Tailwind's arbitrary-value parser and emit no CSS.
- **GOTCHA**: Alternative `w-[var(--radix-popover-trigger-width)]` may render too narrow. Stick with the `min()` clamp.
- **GOTCHA**: Could not live-reproduce in the audit (upstream HTTP 400). Skip live capture; rely on source diff + Vitest.
- **POST-EDIT VERIFY**:
  ```bash
  grep -n 'w-\[min(400px,calc(100vw-1rem))\]' frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx  # 1 match
  ! grep -n 'w-\[400px\] p-0' frontend/src/features/jobs/components/SearchableCustomerDropdown.tsx
  cd frontend && npm run typecheck
  ```
- **CAPTURE AFTER (best-effort)**: If any page that mounts `SearchableCustomerDropdown` renders cleanly (try `/jobs/new` or grep for `SearchableCustomerDropdown` consumers), open it at 390 × 844, click the dropdown trigger, screenshot `after/bug-7-customer-dropdown.png`. Otherwise document "no live capture".
- **VALIDATE**: `cd frontend && npm test SearchableCustomerDropdown`. Confirm no Tailwind build warning about an unrecognized arbitrary value — `npm run build` will catch this.

### Task 10 — UPDATE `frontend/src/features/marketing/components/MarketingDashboard.tsx` (BUG-9a, P2)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'TabsList data-testid="marketing-tabs"' frontend/src/features/marketing/components/MarketingDashboard.tsx
  grep -n '</TabsList>' frontend/src/features/marketing/components/MarketingDashboard.tsx
  # Check parent padding to decide whether to use -mx-4 px-4 or just overflow-x-auto pb-1
  awk 'NR>=160 && NR<=170' frontend/src/features/marketing/components/MarketingDashboard.tsx
  ```
  Audit: TabsList opens line 167, closes line 183. Read 7 lines above the open to determine parent padding.
- **PARENT PADDING DECISION**: If the immediate parent of the `<Tabs>` block uses `px-4` / `px-6` / similar, keep `-mx-4 px-4` (or matching value) so the scroll affordance bleeds to the page edge. If the parent has no `px-*`, drop `-mx-* px-*` and use just `overflow-x-auto pb-1`.
- **IMPLEMENT**: Wrap the `<TabsList>` (and ONLY the `<TabsList>`, not the surrounding `<TabsContent>`) in:
  ```tsx
  <div className="overflow-x-auto -mx-4 px-4 pb-1">
    <TabsList data-testid="marketing-tabs">
      …
    </TabsList>
  </div>
  ```
  Adjust `-mx-4 px-4` per parent-padding decision above.
- **PATTERN**: "Scrollable TabsList" — apply at consumer, never at primitive (`frontend/src/components/ui/tabs.tsx`).
- **IMPORTS**: None changed.
- **GOTCHA**: Wrapping the entire `<Tabs>` (including `<TabsContent>`) instead of just `<TabsList>` would scroll the entire tab content area, which is wrong. Only wrap `<TabsList>`.
- **GOTCHA**: `pb-1` reserves 4 px under the scrollbar to avoid crowding `TabsContent`'s `mt-4`.
- **POST-EDIT VERIFY**:
  ```bash
  grep -nB 1 'TabsList data-testid="marketing-tabs"' frontend/src/features/marketing/components/MarketingDashboard.tsx | grep 'overflow-x-auto'  # confirms wrap is present immediately above
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/marketing
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-9a-marketing.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0 (was 138)
  agent-browser --session mobile-fix eval "document.querySelector('[data-testid=marketing-tabs]')?.parentElement?.scrollWidth"  # expect ≥ TabsList natural width
  ```
- **VALIDATE**: `cd frontend && npm test MarketingDashboard`. Diff PNGs — TabsList horizontally scrollable; "CAC Analysis" reachable via swipe.

### Task 11 — UPDATE `frontend/src/features/accounting/components/AccountingDashboard.tsx` (BUG-9b, P2)

- **PRE-FLIGHT**:
  ```bash
  grep -n 'TabsList data-testid="accounting-tabs"' frontend/src/features/accounting/components/AccountingDashboard.tsx
  grep -n '</TabsList>' frontend/src/features/accounting/components/AccountingDashboard.tsx
  awk 'NR>=139 && NR<=149' frontend/src/features/accounting/components/AccountingDashboard.tsx
  ```
  Audit: TabsList opens line 146, closes line 152.
- **PARENT PADDING DECISION**: Same as Task 10.
- **IMPLEMENT**: Same wrapper pattern as Task 10. Wrap ONLY `<TabsList>`.
- **PATTERN**: Identical to Task 10.
- **IMPORTS**: None changed.
- **GOTCHA**: Same as Task 10.
- **POST-EDIT VERIFY**:
  ```bash
  grep -nB 1 'TabsList data-testid="accounting-tabs"' frontend/src/features/accounting/components/AccountingDashboard.tsx | grep 'overflow-x-auto'
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/accounting
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-9b-accounting.png
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0 (was 151)
  ```
- **VALIDATE**: `cd frontend && npm test AccountingDashboard`. Diff PNGs — "Audit Log" reachable via TabsList swipe.

### Task 12 — UPDATE `WeekMode.tsx` AND `ResourceTimelineView/index.tsx` (BUG-6, P2)

- **PRE-FLIGHT**:
  ```bash
  grep -n "gridTemplateColumns: '200px repeat(7, minmax(0, 1fr))'" frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx
  grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden' frontend/src/features/schedule/components/ResourceTimelineView/index.tsx
  ```
  Audit: WeekMode.tsx:245 + index.tsx:120. Each grep returns exactly one match.
- **IMPLEMENT (a)** — `WeekMode.tsx`: change `gridTemplateColumns: '200px repeat(7, minmax(0, 1fr))'` → `gridTemplateColumns: '200px repeat(7, minmax(72px, 1fr))'`. Single token in inline style object.
- **IMPLEMENT (b)** — `ResourceTimelineView/index.tsx`: change wrapper class `overflow-hidden` → `overflow-x-auto`. Final class: `bg-white rounded-2xl shadow-sm border border-slate-100 overflow-x-auto`.
- **PATTERN**: 72 px column = "MON" (~36 px) + "4/27" (~32 px) + 4 px padding. Mirrors `MonthMode.tsx:154` `minmax(28px, 1fr)` precedent.
- **IMPORTS**: None changed.
- **GOTCHA**: Reject the audit's alternative "default to Day view < sm" — JS-side breakpoint adds rotation desync risk and useEffect cascades. CSS fix is lower risk.
- **GOTCHA**: The parent `overflow-x-auto` change also affects Day mode and Month mode (same parent). Both already use `minmax(0, 1fr)` for their grid; Day is single-column (no overflow), Month is `minmax(28px, 1fr)` and will now scroll horizontally on iPhone (desirable).
- **GOTCHA**: `WeekMode.test.tsx` and `MonthMode.test.tsx` exist — `grep -l "minmax" frontend/src/features/schedule/components/ResourceTimelineView/*.test.tsx` to find any test asserting on the literal `'minmax(0, 1fr)'` string. Update if found.
- **POST-EDIT VERIFY**:
  ```bash
  grep -n "gridTemplateColumns: '200px repeat(7, minmax(72px, 1fr))'" frontend/src/features/schedule/components/ResourceTimelineView/WeekMode.tsx  # 1 match
  grep -n 'bg-white rounded-2xl shadow-sm border border-slate-100 overflow-x-auto' frontend/src/features/schedule/components/ResourceTimelineView/index.tsx  # 1 match
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix open http://localhost:5173/schedule
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-6-schedule-week.png
  # The page body itself should NOT overflow — only the timeline container
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"  # expect 0
  agent-browser --session mobile-fix eval "document.querySelector('[data-testid=schedule-resource-timeline]')?.scrollWidth"  # expect ≥ 704
  agent-browser --session mobile-fix eval "document.querySelector('[data-testid=day-header-2026-05-04]')?.textContent || ''"  # expect 'MON', not concatenated 'MONTUE'
  ```
- **VALIDATE**: `cd frontend && npm test WeekMode MonthMode DayMode`. Diff before/after PNGs — column headers legible (`MON` / `4/27` etc.); horizontal swipe within the timeline reveals later days.

### Task 13 — INVESTIGATE then UPDATE `frontend/src/pages/Settings.tsx` (BUG-10, P2)

This is the only fix that requires root-cause investigation. Use the **enumerate-then-fix** script below — do NOT guess.

- **PRE-FLIGHT (enumerate offenders)**:
  ```bash
  # Make sure dev servers are up; reuse mobile-fix session
  agent-browser --session mobile-fix open http://localhost:5173/settings
  agent-browser --session mobile-fix wait --load networkidle
  # Confirm overflow still ~66 px (sanity check vs Task 0 baseline)
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"
  # Enumerate every node that overflows the viewport, ordered by depth ascending
  # (shallowest = most likely root cause)
  agent-browser --session mobile-fix eval "
    Array.from(document.querySelectorAll('*'))
      .filter(el => el.getBoundingClientRect().right > window.innerWidth + 1)
      .map(el => ({
        tag: el.tagName,
        cls: (el.className || '').toString().slice(0, 100),
        right: Math.round(el.getBoundingClientRect().right),
        width: Math.round(el.getBoundingClientRect().width),
        depth: (function d(n){let i=0;while(n.parentElement){n=n.parentElement;i++}return i})(el)
      }))
      .sort((a,b) => a.depth - b.depth)
      .slice(0, 12)
  "
  ```
  Read the output. The shallowest overflowing node identifies the root container (typically a `<Card>` or a `flex items-center justify-between` row).
- **FIX DECISION TREE**:
  - **If shallowest is a `flex items-center justify-between` row**: add `flex-wrap gap-2` to its className. Mirrors BUG-5(a). Most likely outcome.
  - **If shallowest is a `<Card>` or `<CardHeader>` with a min-width**: change to `min-w-0 max-w-full`. Likely if a child relies on `min-width: auto` (default) which equals content width.
  - **If shallowest is a `<Dialog>` mounted in-flow (not portaled)**: it shouldn't be — but if so, ensure it uses `<DialogContent>` from `@/components/ui/dialog` which portals to body. Replace any direct DOM mount.
  - **If a `<Button>` row**: same fix as the `flex` case — `flex-wrap gap-2`.
- **IMPLEMENT**: Apply the matching fix to the offending element. Most likely: a single Tailwind class addition (`flex-wrap gap-2`) on one `<div>`.
- **PATTERN**: "Wrappable button row" / `min-w-0` clamp.
- **IMPORTS**: None expected.
- **TIME-BOX**: 30 minutes from PRE-FLIGHT to POST-EDIT VERIFY. If the enumerate-script didn't surface a single obvious culprit (e.g., 3 sibling overflows of equal depth), apply `flex-wrap gap-2` to the highest sibling that's a `flex` container AND record the partial fix in the commit message. Defer hunt to a follow-up issue, but DO ship the partial fix — even reducing overflow from 66 → 16 is a win.
- **POST-EDIT VERIFY**:
  ```bash
  cd frontend && npm run typecheck
  # Re-run the overflow probe — must read 0
  agent-browser --session mobile-fix open http://localhost:5173/settings
  agent-browser --session mobile-fix wait --load networkidle
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"
  ```
- **CAPTURE AFTER**:
  ```bash
  agent-browser --session mobile-fix screenshot e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/bug-10-settings.png
  ```
  Capture this screenshot regardless of whether the fix achieved 0 overflow — it's the artifact that proves the visible improvement.
- **VALIDATE**: `cd frontend && npm test Settings`. Diff before/after PNGs — page renders without horizontal scroll OR scrolls less than the 66 px baseline. Document the final overflow value in the commit message.

### Task 14 — CONSOLIDATE: write the validation matrix + summary report

By this point, every individual task has captured its own AFTER screenshot under `e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/`. This task does NOT re-capture — it produces the consolidated artifact a reviewer will look at.

- **IMPLEMENT**:
  1. Write `e2e-screenshots/mobile-viewport-fixes-2026-05-02/_after_overflow.tsv` by re-running the URL walk from Task 0 and recording the new `bodyOverflow` values. Filename mirrors the BEFORE TSV from Task 0.
     ```bash
     set -euo pipefail
     cd /Users/kirillrakitin/Grins_irrigation_platform
     declare -a TARGETS=(
       "bug-2-pricelist|/invoices?tab=pricelist"
       "bug-3-jobs|/jobs"
       "bug-4-customers|/customers"
       "bug-5-leads|/leads"
       "bug-6-schedule-week|/schedule"
       "bug-9a-marketing|/marketing"
       "bug-9b-accounting|/accounting"
       "bug-10-settings|/settings"
     )
     : > e2e-screenshots/mobile-viewport-fixes-2026-05-02/_after_overflow.tsv
     for entry in "${TARGETS[@]}"; do
       slug="${entry%%|*}"
       path="${entry##*|}"
       agent-browser --session mobile-fix open "http://localhost:5173$path"
       agent-browser --session mobile-fix wait --load networkidle
       overflow=$(agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth")
       printf '%s\t%s\t%s\n' "$slug" "$path" "$overflow" >> e2e-screenshots/mobile-viewport-fixes-2026-05-02/_after_overflow.tsv
     done
     paste e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/_overflow.tsv \
           e2e-screenshots/mobile-viewport-fixes-2026-05-02/_after_overflow.tsv \
       | awk -F'\t' 'BEGIN{print "slug\turl\tbefore\tafter\tdelta"} {print $1"\t"$2"\t"$3"\t"$6"\t"($3-$6)}' \
       > e2e-screenshots/mobile-viewport-fixes-2026-05-02/_overflow_diff.tsv
     cat e2e-screenshots/mobile-viewport-fixes-2026-05-02/_overflow_diff.tsv
     ```
  2. Write `e2e-screenshots/mobile-viewport-fixes-2026-05-02/README.md` with the table below filled in from `_overflow_diff.tsv` and a per-bug "before / after / source-diff" link list.
  3. Generate visual diff strips (optional, requires ImageMagick):
     ```bash
     for bug in bug-1-tag-editor-sheet bug-2-pricelist bug-3-jobs bug-4-customers bug-5-leads bug-6-schedule-week bug-9a-marketing bug-9b-accounting bug-10-settings; do
       before="e2e-screenshots/mobile-viewport-fixes-2026-05-02/before/${bug}.png"
       after="e2e-screenshots/mobile-viewport-fixes-2026-05-02/after/${bug}.png"
       diff="e2e-screenshots/mobile-viewport-fixes-2026-05-02/diffs/${bug}.png"
       if [[ -f "$before" && -f "$after" ]]; then
         convert "$before" "$after" +append "$diff" 2>/dev/null || echo "skip $bug (ImageMagick not installed)"
       fi
     done
     ```
- **VALIDATE**: 8-row `_overflow_diff.tsv` exists. Every row's `after` column is 0 (or for BUG-10, ≤ before). README.md committed alongside the screenshots.

### Required screenshot inventory (all referenced by other tasks; this is the catalog)

| Bug | URL | BEFORE path | AFTER path | Expected after-fix `bodyOverflow` |
|---|---|---|---|---|
| BUG-1 | /schedule → modal → Edit tags | `before/bug-1-tag-editor-sheet.png` | `after/bug-1-tag-editor-sheet.png` | 0 (modal-internal; "Save tag" visible) |
| BUG-2 | /invoices?tab=pricelist | `before/bug-2-pricelist.png` | `after/bug-2-pricelist.png` | 0 (table scrolls inside card) |
| BUG-3 | /jobs | `before/bug-3-jobs.png` | `after/bug-3-jobs.png` | 0 |
| BUG-4 | /customers | `before/bug-4-customers.png` | `after/bug-4-customers.png` | 0 |
| BUG-5 | /leads | `before/bug-5-leads.png` | `after/bug-5-leads.png` | 0 (was 280) |
| BUG-6 | /schedule (week) | `before/bug-6-schedule-week.png` | `after/bug-6-schedule-week.png` | 0 (timeline scrolls inside) |
| BUG-7 | (no live page) | — | — (source diff only) | n/a |
| BUG-8a | /portal/invoices/{token} | (skip if no token) | (skip if no token) | 0 |
| BUG-8b | /portal/estimates/{token} | (skip if no token) | (skip if no token) | 0 |
| BUG-9a | /marketing | `before/bug-9a-marketing.png` | `after/bug-9a-marketing.png` | 0 (was 138) |
| BUG-9b | /accounting | `before/bug-9b-accounting.png` | `after/bug-9b-accounting.png` | 0 (was 151) |
| BUG-10 | /settings | `before/bug-10-settings.png` | `after/bug-10-settings.png` | 0 (was 66; partial OK if root-cause defied 30-min time-box) |

This inventory is the single source of truth for what screenshots must exist before the umbrella is considered complete.

### Task 15 — RUN full quality checks

- **IMPLEMENT**: Top-to-bottom, all from the repo root:
  ```bash
  cd frontend && npm run typecheck
  cd frontend && npm test
  cd frontend && npm run lint
  cd frontend && npm run build
  ```
- **PATTERN**: This is the standard `package.json` script set; see `frontend/package.json:6-15`.
- **IMPORTS**: N/A.
- **GOTCHA**: `npm run build` runs `tsc -p tsconfig.app.json --noEmit && vite build` per `package.json:8`. If the build fails, do **not** rebase or amend earlier commits — fix the new error in a follow-up commit.
- **GOTCHA**: `npm run lint` is ESLint and may report pre-existing warnings unrelated to this work. Compare the count to baseline; only block on *new* errors.
- **VALIDATE**: All four commands exit `0`.

---

## TESTING STRATEGY

### Unit Tests

Vitest + React Testing Library. Co-located: `Foo.tsx` ↔ `Foo.test.tsx` (per `.kiro/steering/frontend-testing.md`).

For each fixed file with an existing test (`JobList.test.tsx`, `CustomerList.test.tsx`, `LeadsList.test.tsx`, etc.):
- Run the existing test first to capture the baseline.
- After the fix, the test should still pass — these tests assert presence of `data-testid="…-table"` and rendered rows, not the wrapper div.
- If a test asserts the old wrapper class string, update it to assert the post-fix class string.

For `SheetContainer.tsx`, add a new spec (Task 2) that asserts the rendered class string contains the responsive width tokens.

For `MarketingDashboard.tsx`, `AccountingDashboard.tsx` — there may not be a co-located test; if one exists, verify it still finds the `TabsList` via `data-testid="marketing-tabs"` / `accounting-tabs` (the wrapper does not occlude the testid).

For `WeekMode.tsx` — `WeekMode.test.tsx` exists. Verify the inline-style assertion (if any) is updated from `'minmax(0, 1fr)'` to `'minmax(72px, 1fr)'`.

### Integration Tests

No new integration tests. The closest equivalent is the manual `agent-browser` capture in Task 14 — a 390 × 844 visit to each page asserting (a) screenshot looks correct and (b) `document.body.scrollWidth - document.body.clientWidth === 0`.

### Edge Cases

- **iPhone SE (375 × 667)** — the `min()` clamp on BUG-7 should still hold (375 - 16 = 359 ≤ 400). `sm:` breakpoint (≥ 640 px) should still gate the `SheetContainer` 560 px branch correctly. No additional fix needed.
- **iPhone 14 Pro Max (430 × 932)** — borderline: 430 px is below `sm:` (640 px) so still uses the mobile branches. All fixes still apply.
- **iPad Mini portrait (768 × 1024)** — at `sm:` breakpoint exactly. `SheetContainer` activates 560 px branch (fits in 768 px). `TabsList` no longer needs to scroll. Verified by Tailwind defaults; no additional fix.
- **Landscape orientation (844 × 390)** — short height, wide width. Tables fit fine; `SheetContainer` activates desktop branch; no horizontal overflow. Verified mentally; capture an optional landscape screenshot for the appointment-modal flow if time permits.
- **Long line-item descriptions (BUG-8 a/b)** — generate a synthetic test estimate with a 60+ character item description. Verify the `overflow-x-auto` on the wrapper actually scrolls and the "Total" cell remains reachable.
- **Empty state on PriceListEditor / JobList / CustomerList / LeadsList** — when the table renders 0 rows, the empty-state row sits inside the (now-removed) outer wrapper. Verify the empty state still renders correctly with the right card chrome.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd frontend && npm run typecheck
cd frontend && npm run lint
```

Both should exit 0. New ESLint warnings vs. baseline may be acceptable; new errors are not.

### Level 2: Unit Tests

```bash
cd frontend && npm test SheetContainer
cd frontend && npm test JobList
cd frontend && npm test CustomerList
cd frontend && npm test LeadsList
cd frontend && npm test PriceListEditor
cd frontend && npm test InvoicePortal
cd frontend && npm test EstimateReview
cd frontend && npm test SearchableCustomerDropdown
cd frontend && npm test MarketingDashboard
cd frontend && npm test AccountingDashboard
cd frontend && npm test WeekMode
cd frontend && npm test Settings
cd frontend && npm test  # full suite
```

All exit 0.

### Level 3: Integration Tests

```bash
cd frontend && npm run build
```

`npm run build` runs `tsc + vite build` end-to-end and is the closest the frontend gets to an integration test. Exits 0 with the dist bundle written to `frontend/dist/`.

### Level 4: Manual Validation

```bash
# From repo root
source e2e/_lib.sh
require_tooling
require_servers
agent-browser --session mobile-fix set viewport 390 844
SESSION=mobile-fix login_admin

# For each bug, open the page, screenshot, probe
for url in /schedule /jobs /customers /leads /invoices?tab=pricelist /marketing /accounting /settings; do
  agent-browser --session mobile-fix open "http://localhost:5173$url"
  agent-browser --session mobile-fix wait --load networkidle
  slug=$(echo "$url" | tr '/?=' '-')
  agent-browser --session mobile-fix screenshot "e2e-screenshots/mobile-viewport-fixes-2026-05-02/page$slug.png"
  echo -n "$url bodyOverflow="
  agent-browser --session mobile-fix eval "document.body.scrollWidth - document.body.clientWidth"
done

# Then the SheetContainer flow specifically:
agent-browser --session mobile-fix open http://localhost:5173/schedule
agent-browser --session mobile-fix wait --load networkidle
agent-browser --session mobile-fix click "[data-testid^=appt-card-]"
agent-browser --session mobile-fix wait "[data-testid=appointment-modal]"
agent-browser --session mobile-fix click "button:has-text('Edit tags')"   # adjust selector to actual testid
agent-browser --session mobile-fix screenshot "e2e-screenshots/mobile-viewport-fixes-2026-05-02/bug-1-tag-editor-sheet.png"
```

Compare each capture to the audit's matching frame in `e2e-screenshots/mobile-bug-audit-2026-05-02/`.

### Level 5: Additional Validation (Optional)

If the agent-browser daemon flakes (audit handoff documents this at `.agents/plans/2026-05-02-mobile-viewport-bug-audit-handoff.md:117-148`), restart with:

```bash
pkill -f "agent-browser-darwin-arm64" ; pkill -f "node.*agent-browser.*daemon"
```

Then re-run from `agent-browser --session mobile-fix set viewport 390 844`.

---

## ACCEPTANCE CRITERIA

- [ ] BUG-1: `frontend/src/shared/components/SheetContainer.tsx:26` no longer contains the literal `w-[560px]` without a responsive prefix; rendered className includes `w-full`, `sm:w-[560px]`, `max-w-full`. New Vitest test enforces this.
- [ ] BUG-2: `/invoices?tab=pricelist` at 390 × 844 — Edit / Deactivate buttons reachable via horizontal scroll within the table card. `bodyOverflow === 0`.
- [ ] BUG-3: `/jobs` at 390 × 844 — status, source, customer, scheduled-for, actions columns reachable via horizontal scroll within the table card. `bodyOverflow === 0`.
- [ ] BUG-4: `/customers` at 390 × 844 — phone (full digits), email (full address), status, type, last-contact, actions columns reachable. `bodyOverflow === 0`.
- [ ] BUG-5: `/leads` at 390 × 844 — heading button row wraps to 2 lines or fits in 1; `bodyOverflow === 0` (was 280); leads table scrolls horizontally; no duplicate `<h1>Leads</h1>` (or duplicate confirmed acceptable if `Leads.tsx` doesn't supply `PageHeader`).
- [ ] BUG-6: `/schedule` Week view at 390 × 844 — column headers `MON / 4/27`, `TUE / 4/28` legible; horizontal swipe reveals later days.
- [ ] BUG-7: `SearchableCustomerDropdown` PopoverContent at 390 × 844 — width clamped to viewport-minus-margin; no horizontal page overflow.
- [ ] BUG-8a: `InvoicePortal` line-items table at 390 × 844 — long item descriptions cause the wrapper (not the page) to scroll; "Total" column reachable.
- [ ] BUG-8b: `EstimateReview` line-items table — same as 8a.
- [ ] BUG-9a: `/marketing` at 390 × 844 — TabsList scrolls horizontally; "CAC Analysis" tab reachable. `bodyOverflow === 0` (was 138).
- [ ] BUG-9b: `/accounting` at 390 × 844 — TabsList scrolls; "Audit Log" reachable. `bodyOverflow === 0` (was 151).
- [ ] BUG-10: `/settings` at 390 × 844 — `bodyOverflow === 0` (was 66).
- [ ] All Vitest specs pass (`cd frontend && npm test`).
- [ ] `cd frontend && npm run typecheck` exits 0.
- [ ] `cd frontend && npm run build` exits 0.
- [ ] `cd frontend && npm run lint` reports no NEW errors (warnings vs. baseline acceptable).
- [ ] No backend code touched. No migrations added. No new dependencies.
- [ ] Screenshots captured in `e2e-screenshots/mobile-viewport-fixes-2026-05-02/` for at least 8 of 10 bugs (BUG-7, BUG-8a/b may not have live captures).
- [ ] No regression on desktop ≥ 640 px — quick visual check that all fixed pages still render as before on a typical 1440 × 900 viewport.

---

## COMPLETION CHECKLIST

- [ ] Task 1: `SheetContainer.tsx` width updated.
- [ ] Task 2: `SheetContainer.test.tsx` created and passing.
- [ ] Task 3: `PriceListEditor.tsx` outer wrapper removed.
- [ ] Task 4: `JobList.tsx` outer wrapper removed.
- [ ] Task 5: `CustomerList.tsx` outer wrapper removed.
- [ ] Task 6: `LeadsList.tsx` heading wraps + table wrapper removed + dedupe heading (if applicable).
- [ ] Task 7: `InvoicePortal.tsx` `overflow-hidden` → `overflow-x-auto`.
- [ ] Task 8: `EstimateReview.tsx` `overflow-hidden` → `overflow-x-auto`.
- [ ] Task 9: `SearchableCustomerDropdown.tsx` width clamped.
- [ ] Task 10: `MarketingDashboard.tsx` TabsList wrapped.
- [ ] Task 11: `AccountingDashboard.tsx` TabsList wrapped.
- [ ] Task 12: `WeekMode.tsx` column min-width widened + parent overflow-x-auto.
- [ ] Task 13: `Settings.tsx` 66 px overflow root-caused and fixed (or deferred with reason).
- [ ] Task 14: After-fix screenshots captured.
- [ ] Task 15: Full typecheck + tests + build + lint pass.
- [ ] Each task validation passed immediately on completion.
- [ ] Acceptance criteria all met.
- [ ] Code reviewed for quality and maintainability — every fix is the *smallest* edit that addresses the bug.

---

## NOTES

- **Why removing the outer wrapper is preferred over swapping to `overflow-x-auto`** for BUG-2/3/4/5 (but not 8a/b): the shadcn `Table` primitive at `frontend/src/components/ui/table.tsx:5-18` already supplies the `bg-white rounded-2xl shadow-sm border border-slate-100 overflow-x-auto` chrome. Keeping a redundant outer wrapper means visually-doubled card borders (subtle but noticeable on retina displays) and two nested `overflow-x-auto` scrollers (only the inner one becomes effective; the outer becomes inert). Removing the outer wrapper is the correct DRY fix. For BUG-8a/b (`InvoicePortal`, `EstimateReview`) the outer wrapper carries a sibling `<h3>Line Items</h3>` header that's part of the visual section grouping, so we keep the wrapper and just fix the overflow class.
- **Why CSS-only fixes over JS breakpoints**: The codebase has `useMediaQuery('(max-width: 767px)')` as a working JS-side approach, but every fix in this plan can be expressed with Tailwind responsive prefixes alone. CSS-only fixes are SSR-safe, render correctly on first paint without a flash, and survive viewport rotation without state desync. Reserve `useMediaQuery` for behavior changes (e.g., switching component variants), not layout.
- **Why NOT to monkey-patch the shadcn `TabsList` primitive**: The primitive is intentionally width-agnostic so consumers can decide. Patching it would affect every `TabsList` consumer in the codebase, including ones that already work (e.g., `Sales.tsx`, `Communications.tsx`, `Customers.tsx`). The two-consumer wrap is targeted and reversible.
- **Why widen WeekMode columns instead of defaulting to Day mode**: The audit's alternative ("default to Day view < `sm`") requires JS-side breakpoints, mode-state desync risk on viewport rotation, and a `useEffect` cascade. The CSS-only widen+scroll fix is equivalent in user outcome (techs can see the week) and far lower risk. If the tech ever asks for "open in Day mode by default on phone", revisit then.
- **Risk: visual regression on desktop**: Removing the outer wrappers in BUG-2/3/4/5 changes the rendered card chrome from the wrapper's classes to the Table primitive's classes. They're nearly identical but not pixel-perfect (e.g., `rounded-md` vs `rounded-2xl` on PriceListEditor). Mitigation: capture a quick desktop (1440 × 900) screenshot of each affected page before and after, eyeball the diff. If unacceptable, fall back to the lower-risk `overflow-hidden` → `overflow-x-auto` swap (keeps the doubled chrome but unblocks horizontal scroll).
- **Risk: `bughunt/2026-05-02-mobile-viewport-audit.md` line numbers may drift**: The audit cites file:line precisely (e.g., `LeadsList.tsx:438`, `PriceListEditor.tsx:233`). If the file has been edited since the audit (today), those line numbers may be off. Always grep for the exact wrapper class string `"bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden"` rather than trusting the line number — it's a unique enough string to disambiguate.
- **Out of scope**: The cross-cutting refactor opportunity the audit mentions ("a `<TableScrollArea>` shared component") is intentionally not pursued. Removing the redundant outer wrappers achieves the same outcome with strictly less code. If a future requirement creates a NEW table that doesn't fit the shadcn primitive (e.g., a custom virtualized table), revisit.
- **Out of scope**: BUG follow-ups in `bughunt/2026-05-02-mobile-viewport-audit.md` "Out of scope" section — `/agreements` JS SyntaxError and `/invoices` HTTP 400 — are unrelated bugs that already have their own tracking.
- **Confidence (one-pass success): 10 / 10.** Rationale for the bump from the prior 8.5:
  - **2-1 pattern codified.** Every table-clip site is now classified Variant 1 (remove wrapper) or Variant 2 (swap class) with a deterministic decision recipe (`grep` + inspect next non-whitespace child). The implementer cannot misclassify because the classification is computed mechanically from the file, not inferred.
  - **Pre-flight `grep` per task.** Every editing task starts by re-anchoring against a unique class string instead of trusting the audit's line numbers. Line drift (the largest pre-bump risk) is eliminated.
  - **Post-edit verify per task.** Every editing task ends with a positive grep (the new string exists, exactly once) AND a negative grep (the old string is gone). JSX brace mismatches surface immediately via `npm run typecheck`.
  - **BEFORE screenshots all captured up front in Task 0.** The implementer cannot accidentally take a BEFORE shot after the edit landed (the previous biggest QA failure mode for this kind of work).
  - **AFTER screenshot + DOM-overflow probe enforced in every task.** Every fix has a numeric pass/fail signal (`bodyOverflow === 0`) plus a visual artifact, both auto-captured.
  - **Task 13 (Settings 66 px) de-risked from "investigate" to "run script, read top result, apply matching fix from a 4-branch decision tree".** The enumerate-overflowers JS snippet returns the offending node mechanically; the time-box now allows shipping a partial fix (overflow > 0 but < 66) rather than blocking the whole umbrella.
  - **Final consolidation Task 14 produces a `_overflow_diff.tsv` and a README** so a reviewer can verify the entire umbrella in one glance — no per-bug archaeology needed.
  - The remaining residual risk (Tailwind arbitrary-value parser quirks for the `min(400px,calc(100vw-1rem))` value in Task 9, possible `npm run lint` warnings on the wrapper-removal tasks) is explicitly called out per-task with concrete `npm run build` / `grep` checks. Nothing is hand-waved.
