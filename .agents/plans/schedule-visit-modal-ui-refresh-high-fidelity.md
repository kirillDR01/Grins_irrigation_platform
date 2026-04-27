# Feature: Schedule-Visit Modal UI Refresh (High-Fidelity Handoff)

> **Source of truth folder**: `feature-developments/schedule-estimate-visit-handoff_high_fidelity/`
> **Source of truth screenshot**: `/Users/kirillrakitin/Desktop/Screenshot 2026-04-25 at 6.54.34 PM.png`
> **Note**: The `feature-developments/schedule-estimate-visit-handoff 2/` folder is byte-identical (`diff -rq` returns no output). Either path is valid; this plan uses the `_high_fidelity` name per user preference.

The following plan is **complete and pre-validated for one-pass implementation**. Every decision is baked in. Every classname, command, and snippet has been verified against the live codebase (commit `bfb613e` on branch `dev`). Execute the diff in Task 1 verbatim, then run the validation block.

## Feature Description

The `ScheduleVisitModal` (booked from Sales pipeline → Stage 1 "Schedule estimate" → Now-card "Schedule visit" action) was first shipped in commit `dbed5f0`. The high-fidelity handoff redesigns the primary CTA in the modal footer.

This task is **a one-component UI refresh**:

- Replace the calendar-emoji prefix on the primary CTA with the high-fidelity treatment: `Confirm & advance to Send Estimate` followed by a trailing right-arrow icon, on a dark/slate-900 primary button (matches the screenshot).
- Refresh the reschedule-path CTA: `Update appointment` (no emoji, no arrow), same dark style.
- No backend / schema / hook / business-logic changes. The pick state, week calendar, conflict detection, and submit path are unchanged.

## User Story

As a sales operator scheduling an estimate visit from the Sales pipeline detail screen,
I want the modal's primary CTA to read **"Confirm & advance to Send Estimate →"** as a dark, prominent button matching the high-fidelity design,
So that the action of advancing the lead to the next pipeline stage is unmistakable, the calendar emoji is removed, and the trailing arrow signals stage progression.

## Problem Statement

The shipped modal uses `📅 Confirm & advance to Send Estimate` (calendar emoji prefix, default teal `<Button>` variant, no directional cue). The high-fidelity reference HTML at `feature-developments/schedule-estimate-visit-handoff_high_fidelity/reference/Schedule-Estimate-Visit-Reference.html:769–777` and the user's screenshot specify a cleaner CTA: dark/ink-colored primary button, no leading emoji, trailing right-arrow icon. The reschedule path's `📅 Update appointment` should drop its emoji for consistency.

## Solution Statement

Edit two files only:

1. `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx` — replace the `confirmLabel` string with inline JSX rendering text + `<ArrowRight />`, and add a `className` override on the `<Button>` for the dark slate-900 primary style.
2. `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.test.tsx` — append two new tests for the new label + arrow, and the reschedule label without arrow.

No new files. No new hooks. No new types. No package additions. No edits to the shared `<Button>` primitive.

## Feature Metadata

**Feature Type**: Enhancement (UI refresh)
**Estimated Complexity**: Low
**Primary Systems Affected**:
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.test.tsx`

**Dependencies (all verified present)**:
- `lucide-react@^0.562.0` — confirmed in `frontend/package.json` as a direct `dependencies` entry; `ArrowRight` already used in `frontend/src/features/sales/components/NowCard.tsx:10` and elsewhere.
- `tailwindcss@^4.1.18` — confirmed; standard `slate-*` palette is in scope.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx` (lines 1–179) — The file you edit. Specifically: import block at lines 1–23, `confirmLabel` const at lines 95–98, `<DialogFooter>` block at lines 160–175, Confirm `<Button>` at lines 168–174.
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.test.tsx` (lines 1–178) — Co-located tests. Existing tests don't assert button text content, so they continue to pass after the change. New tests append at the end of the `describe('ScheduleVisitModal', …)` block.
- `frontend/src/features/sales/components/NowCard.tsx` (line 10 import; usage at multiple `<ArrowRight />` calls) — Canonical example for importing and using `ArrowRight` in this feature.
- `frontend/src/components/ui/button.tsx` (entire 63-line file) — Shadcn Button. Critical lines:
  - Line 8: `[&_svg:not([class*='size-'])]:size-4` regex — any svg child with a `size-` class wins, so `size-3.5` overrides correctly.
  - Line 8: `disabled:pointer-events-none disabled:opacity-50` — base disabled style; we override `opacity-50` so the dark color isn't washed out.
  - Line 8: `whitespace-nowrap` — keeps the long label on one line.
- `frontend/src/components/ui/dialog.tsx` (DialogFooter) — Already in use; `flex flex-col-reverse gap-2 sm:flex-row sm:justify-end`. Cancel + Confirm buttons land justified-right with auto gap. No change.
- `frontend/src/features/sales/components/StageStepper.tsx:106` — Codebase pattern: `'bg-slate-900 text-white'` is the established dark-CTA treatment.
- `frontend/src/features/sales/components/NowCard.tsx:271` — Same pattern: `'bg-slate-900 text-white border-slate-900'`.
- `feature-developments/schedule-estimate-visit-handoff_high_fidelity/reference/Schedule-Estimate-Visit-Reference.html` (lines 549–558) — Source CSS for `.btn.primary`: `background: var(--ink); color: #fff; box-shadow: 0 1px 0 rgba(0,0,0,0.1), 0 4px 8px rgba(15,23,42,0.16)`.
- `feature-developments/schedule-estimate-visit-handoff_high_fidelity/reference/Schedule-Estimate-Visit-Reference.html` (lines 12–22) — `var(--ink) = #0B1220`. Tailwind `slate-900` = `#0f172a`. Visual delta is negligible (<5% luminance) and matches existing codebase usage. **Decision: use `bg-slate-900`** (codebase convention, not pixel-exact arbitrary value).
- `feature-developments/schedule-estimate-visit-handoff_high_fidelity/reference/Schedule-Estimate-Visit-Reference.html` (lines 769–777) — Footer markup. Confirm button has trailing inline SVG arrow: `width="14" height="14"` `stroke-width="2.5"`. Lucide `<ArrowRight className="size-3.5" strokeWidth={2.5} />` is a faithful translation.
- `feature-developments/schedule-estimate-visit-handoff_high_fidelity/SPEC.md` (§7 Copy table at lines 180–190) — SPEC §7 still lists `📅 Confirm & advance to Send Estimate` with the emoji. **The reference HTML and the user's screenshot drop the emoji and add the trailing arrow.** Per user instruction, screenshot wins.
- `feature-developments/schedule-estimate-visit-handoff_high_fidelity/CHECKLIST.md` — QA bar; nothing in this UI refresh regresses any item.
- `/Users/kirillrakitin/Desktop/Screenshot 2026-04-25 at 6.54.34 PM.png` — Visual ground truth. Cancel (ghost) + dark Confirm with trailing right arrow, no emoji.

### Files to Modify (exhaustive list — no others)

1. `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx`
2. `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.test.tsx`

### Files NOT to Touch

- `frontend/src/components/ui/button.tsx` — DO NOT add a new variant. Override at the call site.
- `WeekCalendar.tsx`, `ScheduleFields.tsx`, `PickSummary.tsx`, `PrefilledCustomerCard.tsx`, `useScheduleVisit.ts`, `scheduleVisitUtils.ts`, `ScheduleVisitModal.module.css` — out of scope for this UI refresh.

### Pre-Verified Repo Facts (no need to re-check)

| Item | Verified Value |
|---|---|
| Branch | `dev` (HEAD `bfb613e`) |
| Frontend test runner | `vitest run` (script: `npm test`) |
| Frontend lint | `eslint .` (script: `npm run lint`) |
| Frontend typecheck | `tsc -p tsconfig.app.json --noEmit` (script: `npm run typecheck`) |
| `lucide-react` direct dep | yes, `^0.562.0` |
| Tailwind | `^4.1.18`, CSS-based theme in `frontend/src/index.css`, default slate palette in scope |
| Baseline ESLint on touched dir | clean (no output) |
| Baseline `tsc` project-wide | **already has 16 pre-existing errors** in `src/shared/components/FilterPanel.tsx` and `src/shared/components/Layout.tsx` — these are NOT yours and must be ignored. Compare error counts before/after, do NOT expect zero. |

---

## STEP-BY-STEP TASKS

Execute every task in order. Each is atomic and independently testable.

---

### Task 1 — UPDATE `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx`

Apply this diff verbatim. The line numbers reference the current state of the file (commit `bfb613e`).

**Change 1 of 3** — add `ArrowRight` import. After line 11 (the `Button` import), add:

```tsx
import { ArrowRight } from 'lucide-react';
```

The final import block (lines 1–23 area) should contain `ArrowRight` once. If you add it next to `Button`, that is fine; if you put it on its own line after the `Button` line, that is also fine.

**Change 2 of 3** — delete the `confirmLabel` const at lines 95–98:

```tsx
// REMOVE these lines:
const confirmLabel = s.isReschedule
  ? '📅 Update appointment'
  : '📅 Confirm & advance to Send Estimate';
```

**Change 3 of 3** — replace the entire Confirm `<Button>` block (lines 168–174). Old:

```tsx
<Button
  onClick={handleConfirm}
  disabled={!s.pick || s.submitting}
  data-testid="schedule-visit-confirm-btn"
>
  {confirmLabel}
</Button>
```

New (paste exactly):

```tsx
<Button
  onClick={handleConfirm}
  disabled={!s.pick || s.submitting}
  data-testid="schedule-visit-confirm-btn"
  className="bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-100 disabled:bg-slate-300 disabled:text-white shadow-[0_1px_0_rgba(0,0,0,0.1),0_4px_8px_rgba(15,23,42,0.16)]"
>
  {s.isReschedule ? (
    'Update appointment'
  ) : (
    <>
      Confirm &amp; advance to Send Estimate
      <ArrowRight className="size-3.5" strokeWidth={2.5} aria-hidden="true" />
    </>
  )}
</Button>
```

**Why every detail of this snippet is the way it is** (no judgment calls left for the agent):

- `bg-slate-900 text-white hover:bg-slate-800` — codebase convention for dark CTA. Verified against `StageStepper.tsx:106`, `NowCard.tsx:271`, `CustomerList.tsx:460`, `LeadsList.tsx:546`. Visually equivalent to the reference's `var(--ink) = #0B1220`.
- `disabled:opacity-100` — the shadcn Button base sets `disabled:opacity-50` (button.tsx:8). Without this override, the disabled dark button becomes a 50%-opacity slate-900, looking washed out and ambiguous. Override to `opacity-100` so the explicit `disabled:bg-slate-300` color is what the user sees.
- `disabled:bg-slate-300 disabled:text-white` — clear "inactive" treatment. `text-white` on `slate-300` is below WCAG AA but matches the codebase's other inactive-CTA pattern; if you decide to change this, also touch the existing patterns for consistency (out of scope for this task — leave as written).
- `shadow-[0_1px_0_rgba(0,0,0,0.1),0_4px_8px_rgba(15,23,42,0.16)]` — direct port of the reference HTML's `.btn.primary` shadow. Tailwind 4 supports arbitrary shadow values. If for any reason Tailwind doesn't generate this class, drop the shadow utility entirely; the visual delta vs the screenshot will be negligible.
- `s.isReschedule ? 'Update appointment' : <>…</>` — string vs fragment branches. JSX accepts both as `ReactNode`.
- `Confirm &amp; advance to Send Estimate` — `&amp;` is the JSX-safe way to render the literal `&`. `toHaveTextContent` reads the rendered text, which is `Confirm & advance to Send Estimate`. Matches the existing convention used at line 109 of the same file (`start &amp; duration`).
- `<ArrowRight className="size-3.5" strokeWidth={2.5} aria-hidden="true" />`:
  - `size-3.5` (14px) matches the reference's `width="14" height="14"`. The shadcn Button regex `[&_svg:not([class*='size-'])]:size-4` excludes any svg whose class contains `size-`, so `size-3.5` overrides the default `size-4` correctly. Verified against `button.tsx:8`.
  - `strokeWidth={2.5}` matches reference HTML's `stroke-width="2.5"`.
  - `aria-hidden="true"` — the icon is decorative; the button label already conveys the action to assistive tech.
  - The Button's parent class sets `gap-2`, so spacing between text and icon is automatic.

**VALIDATE Task 1**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx
# Expected: no output (zero violations).
```

---

### Task 2 — UPDATE `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.test.tsx`

Append the two test cases below inside the existing `describe('ScheduleVisitModal', …)` block (after the existing test at lines 167–177, before the closing `});`).

Paste exactly:

```tsx
  it('renders the new CTA copy with a trailing arrow icon for new bookings', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    const btn = screen.getByTestId('schedule-visit-confirm-btn');
    expect(btn).toHaveTextContent('Confirm & advance to Send Estimate');
    expect(btn.querySelector('svg')).not.toBeNull();
    // Calendar-emoji prefix from v1 must be gone.
    expect(btn.textContent ?? '').not.toContain('📅');
  });

  it('renders "Update appointment" without an arrow on the reschedule path', () => {
    const event: SalesCalendarEvent = {
      id: 'e1',
      sales_entry_id: 'entry-1',
      customer_id: 'cust-1',
      title: 't',
      scheduled_date: '2026-04-23',
      start_time: '14:00:00',
      end_time: '15:00:00',
      notes: null,
      assigned_to_user_id: null,
      created_at: '',
      updated_at: '',
    };
    render(
      <ScheduleVisitModal
        entry={mkEntry({ status: 'estimate_scheduled' })}
        currentEvent={event}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    const btn = screen.getByTestId('schedule-visit-confirm-btn');
    expect(btn).toHaveTextContent('Update appointment');
    expect(btn.textContent ?? '').not.toContain('📅');
    // No advance-arrow on reschedule.
    expect(btn.querySelector('svg')).toBeNull();
  });
```

**Why every detail**:
- All imports needed (`render`, `screen`, `describe`, `it`, `expect`, `vi`, `SalesEntry`, `SalesCalendarEvent`) are already present at the top of the file (lines 1–6). No new imports.
- `mkEntry()` and `wrapper` are already defined at lines 43–68 of the same file.
- `toHaveTextContent('Confirm & advance to Send Estimate')` — uses literal `&` (rendered text), not `&amp;` (JSX source). RTL's `toHaveTextContent` reads `node.textContent`.
- `btn.querySelector('svg')` — pragmatic way to assert the lucide SVG presence/absence without coupling to its exact class names.
- The reschedule fixture object is duplicated from the existing test at lines 84–108 verbatim; do NOT extract a helper (only used twice; refactoring is out of scope).

**VALIDATE Task 2**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- ScheduleVisitModal
# Expected: 9 tests pass (7 existing + 2 new).
```

---

### Task 3 — Defensive sweep for stale emoji strings

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform
grep -rn '📅 Confirm & advance to Send Estimate' frontend/src/ || echo "OK: no stale 'Confirm' emoji string"
grep -rn '📅 Update appointment' frontend/src/ || echo "OK: no stale 'Update' emoji string"
```

**Expected**: both grep commands print "OK: …" and exit 0 (no matches found). If any match surfaces, update it the same way.

---

### Task 4 — Final validation gauntlet

Run the full block. **Compare the typecheck error count to the baseline of 16 pre-existing errors** in `FilterPanel.tsx` and `Layout.tsx` — those are NOT yours.

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend

# Level 1 — lint (must be clean on touched dir)
npx eslint src/features/sales/components/ScheduleVisitModal/

# Level 2 — typecheck (must NOT introduce new errors; pre-existing FilterPanel/Layout errors are tolerated)
npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -E '\.tsx?\(' | grep -v 'src/shared/components/FilterPanel\|src/shared/components/Layout' && echo "FAIL: new TS errors above" || echo "OK: no new TS errors"

# Level 3 — focused tests
npm test -- ScheduleVisitModal

# Level 4 — wider sales-feature regression check
npm test -- src/features/sales/
```

**Expected outputs**:
- ESLint: zero output.
- Typecheck: prints `OK: no new TS errors`.
- Focused: 9 passed.
- Wider: all sales-feature suites pass; no new failures vs baseline.

---

### Task 5 — Manual visual confirmation against the screenshot

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run dev
```

In a browser:
1. Log in.
2. Navigate to `/sales` → click an entry whose status is `schedule_estimate`.
3. On the detail page, click the "Schedule visit" Now-card primary action.
4. Confirm the footer matches `/Users/kirillrakitin/Desktop/Screenshot 2026-04-25 at 6.54.34 PM.png` exactly: dark slate button, white text `Confirm & advance to Send Estimate`, small trailing right-arrow icon, no calendar emoji, ghost `Cancel` to its left.
5. **(Optional)** If an `estimate_scheduled` entry with an existing event is available locally, open the modal in reschedule mode and confirm the button reads `Update appointment` (no arrow). The Task 2 unit test already covers this — manual check is a bonus.

---

## ACCEPTANCE CRITERIA

- [ ] Primary CTA reads `Confirm & advance to Send Estimate` (no `📅`) followed by a right-arrow icon, on a dark slate-900 button matching the screenshot.
- [ ] Reschedule CTA reads `Update appointment` (no `📅`, no arrow), same dark style.
- [ ] Cancel button is unchanged (ghost variant, "Cancel").
- [ ] All 7 existing tests in `ScheduleVisitModal.test.tsx` still pass.
- [ ] 2 new tests pass: one for new-booking copy + arrow; one for reschedule copy + no arrow.
- [ ] `npx eslint src/features/sales/components/ScheduleVisitModal/` exits with no output.
- [ ] `npm run typecheck` introduces zero new errors (compare against baseline of 16 pre-existing errors in `FilterPanel.tsx` + `Layout.tsx`).
- [ ] Manual side-by-side with the screenshot matches.
- [ ] No edits to any file outside the two listed in "Files to Modify".
- [ ] No edits to `frontend/src/components/ui/button.tsx`.

---

## NOTES

### Why screenshot wins over SPEC §7

User explicitly attached the screenshot and said "as found in the screenshot attached." SPEC §7 still lists `📅 Confirm & advance to Send Estimate` with the emoji prefix — but the reference HTML at lines 769–777 (the source the screenshot was rendered from) shows the emoji-free + trailing-arrow treatment. Treat reference HTML + screenshot as authoritative; treat SPEC §7 as out-of-date for this single string.

### Why `bg-slate-900` instead of an arbitrary `bg-[#0B1220]` for pixel-exact match

The reference HTML's `var(--ink)` is `#0B1220`, slightly darker than Tailwind's `slate-900` (`#0f172a`). Visual delta is <5% luminance and not perceptible at button scale. The codebase already uses `bg-slate-900` for every dark CTA (StageStepper, NowCard, CustomerList toast, LeadsList toast). Matching codebase convention beats matching mockup pixels.

### Why className override instead of a new Button variant

Adding a variant to `frontend/src/components/ui/button.tsx` expands a shared shadcn primitive's surface area for one consumer. The shadcn convention in this codebase (NowCard, DashboardPage) is to use `className` overrides at the call site for one-off color treatments.

### Why the reschedule path doesn't get an arrow

The arrow icon is a stage-progression cue ("advance to Send Estimate"). Reschedule does not advance the entry — it edits an existing appointment. Keeping the arrow off communicates "stay in place; just update."

### Out of scope (explicitly do NOT do these)

- Adding a "Send confirmation text" toggle to the footer (reference defines the CSS but does not render the toggle in the body).
- Adding the avatar circle / stage pills shown in the reference HTML's modal header — separate redesign, not requested.
- Backend changes to `/api/v1/sales/calendar/events` or to `useScheduleVisit`.
- Edits to `WeekCalendar.tsx`, `ScheduleFields.tsx`, `PickSummary.tsx`, `PrefilledCustomerCard.tsx`, the CSS module, or the shared shadcn `<Button>`.
- Fixing the pre-existing 16 TS errors in `FilterPanel.tsx` / `Layout.tsx`.

### Confidence Score

**10 / 10** for one-pass implementation success.

All previously-judgment-call items are now decided and verified:
- Color: `bg-slate-900` (codebase convention, verified against 4 existing call sites).
- Disabled state: `disabled:opacity-100 disabled:bg-slate-300 disabled:text-white` (overrides the shadcn base `disabled:opacity-50`).
- Arrow size: `size-3.5` + `strokeWidth={2.5}` (verified against the shadcn regex at button.tsx:8 — the override works).
- Icon import: `lucide-react@^0.562.0` confirmed direct dep.
- Validation commands: scripts confirmed in `frontend/package.json` (`vitest run`, `eslint .`, `tsc -p tsconfig.app.json --noEmit`).
- Typecheck baseline: 16 pre-existing errors in unrelated files documented; agent knows not to expect zero.
- Exact diff blocks provided — agent pastes verbatim.
- Defensive grep included to catch any accidental stale emoji strings elsewhere.
- Ref-folder ambiguity resolved: `_high_fidelity` and ` 2/` are byte-identical (`diff -rq` returned empty).
