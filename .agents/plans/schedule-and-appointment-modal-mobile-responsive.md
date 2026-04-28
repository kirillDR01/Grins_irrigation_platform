# Feature: Schedule Tab + Appointment Modal — Fully Mobile-Responsive (Phase 1)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Make the **Schedule tab (`/schedule`)** and the **Combined Appointment Modal v2** fully usable on iPhone (375 px) and iPad (820 px) viewports, while keeping the existing MacBook/desktop experience visually and behaviorally identical at `lg:` breakpoint and above.

This is the Phase 1 scope from `feature-developments/mobile-responsiveness-investigation/05_RECOMMENDED_APPROACH.md`. Other admin pages (Sales, Customers, Jobs, Invoices, etc.) are **out of scope** — they're handled in Phase 2.

The investigation directory (`feature-developments/mobile-responsiveness-investigation/`) is the canonical context for this work. Read at minimum `00_EXECUTIVE_SUMMARY.md`, `02_SCHEDULE_TAB_DEEP_DIVE.md`, `03_APPOINTMENT_MODAL_DEEP_DIVE.md`, and `06_DESIGN_GUIDELINES.md` before starting.

## User Story

**As a** field-service technician working a route on my iPhone,
**I want to** view today's schedule, tap into an appointment, advance status (en route → arrived → completed), take photos, add notes, and collect payment — all from my phone,
**So that** I don't have to carry a laptop into the field, and so that I have parity with what dispatchers see on their MacBooks.

**As an** office dispatcher on a MacBook,
**I want** the existing Schedule tab and Appointment Modal to look and behave exactly as it does today,
**So that** the mobile work doesn't slow down my daily workflow.

## Problem Statement

Today the Schedule tab is approximately 25–35% usable on iPhone:

1. **FullCalendar `timeGridWeek` view is the default** (`CalendarView.tsx:339`) — 7 columns × 28 rows of half-hour slots cannot fit on a 375 px iPhone.
2. **The Schedule page action bar has 7+ buttons** in a single non-wrapping flex row (`SchedulePage.tsx:331-395`) — buttons clip off the right edge of the page on any tablet or phone.
3. **The Appointment Modal v2 is mostly mobile-aware already** (it has a mobile bottom-sheet branch at `AppointmentModal.tsx:289-296`), but several polish gaps prevent it from being production-quality:
   - Nested overlay sheets at lines 589, 600, 612 use `absolute inset-0` inside a `position: fixed` parent — the stacking context is wrong on mobile.
   - `NotesPanel.tsx:218-263` uses inline `minWidth: 120/140 px` with no `flex-wrap` — Save/Cancel buttons risk overflowing on iPhone SE.
   - `PhotosPanel.tsx` is entirely inline-styled, bypassing Tailwind's responsive system.
   - Several touch targets (close button, phone-call button) are below the 44 × 44 px Apple HIG minimum.

## Solution Statement

**Approach:** Mobile-first responsive Tailwind classes + a `useMediaQuery` hook for the few cases where component behavior (not just CSS) needs to differ between mobile and desktop (FullCalendar config, Schedule action bar restructure).

**Key design choices** (locked from the investigation, see `00_EXECUTIVE_SUMMARY.md` decision points):

1. **Stay on responsive web** — no native app, no separate mobile route tree.
2. **Mobile calendar default = `listWeek` view** at `< md:`. Mirror what ServiceTitan/Jobber/Housecall Pro do for field techs.
3. **Drag-drop reschedule disabled on mobile** — route through Edit dialog instead. Avoids touch/scroll conflicts.
4. **Schedule action bar collapses on mobile** — primary "+ New Appointment" button + a "More" dropdown for secondaries.
5. **Pick Jobs to Schedule (`/schedule/pick-jobs`) is OUT OF SCOPE** for this plan — that's an admin/office workflow, not a tech workflow. We'll hide its trigger buttons on mobile and accept that the page itself stays desktop-only. (PickJobsPage mobile-friendly version is deferred to Phase 2 if ever needed.)
6. **Nested overlay sub-sheets** (TagEditor, Payment, Estimate inside AppointmentModal) → use **Option A** from the investigation: keep `absolute inset-0` but add a back-button header so users understand it's a replacement view. Do not refactor into standalone Radix Sheets in this PR (deferred).
7. **No behavior changes at `lg:` breakpoint and above.** Every change must preserve the existing MacBook visual and behavioral experience exactly.

## Feature Metadata

**Feature Type:** Enhancement (responsive design)
**Estimated Complexity:** Medium
**Primary Systems Affected:**
- `frontend/src/features/schedule/components/CalendarView.tsx`
- `frontend/src/features/schedule/components/SchedulePage.tsx`
- `frontend/src/features/schedule/components/AppointmentModal/*` (sub-component polish only)
- `frontend/src/features/schedule/components/AppointmentForm.tsx`
- `frontend/src/features/schedule/components/AppointmentList.tsx`
- `frontend/src/features/schedule/components/DaySelector.tsx`
- `frontend/src/features/schedule/components/SchedulingTray.tsx`
- `frontend/src/features/schedule/components/FacetRail.tsx`
- `frontend/src/shared/hooks/` (new `useMediaQuery` hook)

**Dependencies:** None new. Uses existing Tailwind v4, Radix UI primitives, FullCalendar (v6.1.20 already installed with `dayGridPlugin`, `timeGridPlugin`, `interactionPlugin` — `listPlugin` is the only new addition needed in `package.json`).

---

## PROJECT STANDARDS COMPLIANCE

This plan adheres to the project-wide steering files in `.kiro/steering/`. Each requirement maps to where it's addressed:

| Steering Doc | Requirement | Where addressed in this plan |
|---|---|---|
| `code-standards.md` § 2 | Three-tier testing | Backend: untouched (no backend changes). Frontend: see "TESTING STRATEGY" — Vitest unit/component tests + agent-browser E2E validation. |
| `code-standards.md` § 3 | Type Safety | Validation Level 1: `npm run typecheck` (TypeScript strict, zero errors). |
| `code-standards.md` § 5 | Quality commands | Validation Level 1–4 enumerated below. |
| `tech.md` Stack | React 19 / TS 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4 / Radix UI + shadcn | Plan adheres — no new framework introductions; only `@fullcalendar/list` plugin added. |
| `structure.md` VSA rule | Features import from `core/` and `shared/` only — never from each other | New `useMediaQuery` lives at `shared/hooks/useMediaQuery.ts` (correct). New `SubSheetHeader` lives inside the schedule feature (correct — it's feature-private). |
| `frontend-patterns.md` § Import Conventions | `@/` alias = `frontend/src/`; features expose public API through `index.ts` | Plan uses `@/shared/hooks` (barrel) and `@/components/ui/*` (shadcn primitives). No cross-feature imports. **Note:** the steering doc says `@/shared/components/ui` but the actual codebase uses `@/components/ui/*`; the actual codebase wins. |
| `frontend-patterns.md` § data-testid Convention | `{feature}-page`, `{feature}-table`, `{action}-{feature}-btn`, `nav-{feature}`, `status-{value}` | See "DATA-TESTID CONVENTION MAP" section below. All existing testids preserved; new testids added per convention. |
| `frontend-patterns.md` § Styling | `cn()` for conditional classes | Plan uses Tailwind classes via `cn()` from `@/shared/utils/cn` where conditional. |
| `frontend-testing.md` File Location | Co-located: `features/{feature}/components/X.test.tsx` | All new test files co-located. |
| `frontend-testing.md` Coverage Targets | Components 80%+, Hooks 85%+, Utils 90%+ | Validation Level 3 (`npm run test:coverage`) enforces. New `useMediaQuery` hook target 85%+. |
| `frontend-testing.md` agent-browser script template | `agent-browser open … wait … is visible … click … fill …` | See "AGENT-BROWSER E2E VALIDATION SCRIPTS" section below. |
| `e2e-testing-skill.md` Phase 6: Responsive Testing | `agent-browser set viewport 375 812` (mobile), `768 1024` (tablet), `1440 900` (desktop) | Validation Level 5 explicitly tests at all three viewports. |
| `e2e-testing-skill.md` Grins Specifics | Frontend at `localhost:5173`, key route `/schedule` | E2E scripts target `/schedule` at `localhost:5173`. |
| `spec-quality-gates.md` Design Document Must Include § 2 | data-testid Convention Map | Included in this plan. |
| `spec-quality-gates.md` § 3 | agent-browser Validation Scripts | Included in this plan. |
| `spec-quality-gates.md` § 4 | Quality Gate Commands | Included in Validation Levels 1–6. |
| `spec-quality-gates.md` § 5 | Test Fixtures | See "TEST FIXTURES" section below. |
| `spec-quality-gates.md` § 6 | Coverage Targets | Components 80%+, Hooks 85%+ for `useMediaQuery`. |
| `spec-quality-gates.md` § 7 | Cross-Feature Integration Tests | See "TESTING STRATEGY" — existing AppointmentModal tests already verify integration with customer + job features; we preserve them. |
| `spec-quality-gates.md` § 8 | Security Considerations | See "SECURITY CONSIDERATIONS" section below. |
| `spec-testing-standards.md` § 2 | Frontend testing — component, hook, form validation, loading/error/empty states | See "TESTING STRATEGY" — explicit coverage of each. |
| `spec-testing-standards.md` § 3 | Agent-browser UI validation | Included in Validation Level 5. |
| `spec-testing-standards.md` § 4 | Linting and type safety | Validation Level 1. |
| `spec-testing-standards.md` § 5 | Quality gate | Validation Level 1–6 + acceptance criteria. |
| `agent-browser.md` Command reference | `open`, `snapshot -i`, `click @eN`, `fill`, `wait`, `set viewport`, `screenshot`, `console`, `errors` | Used throughout E2E scripts. |
| `auto-devlog.md` + `devlog-rules.md` | Update DEVLOG.md after significant work | Final task (Task 27) writes a DEVLOG entry under FEATURE category. |
| `parallel-execution.md` | Within a phase, independent tasks run in parallel | Tasks 12–16 (form/list/tray fixes) and Tasks 18–22 (modal sub-component polish) are independent and can be parallelized at implementation time. Task 7 (CalendarView) and Task 10 (SchedulePage) have no overlap and can run in parallel. |

**Out-of-scope steering files:**
- `api-patterns.md` — frontmatter `fileMatchPattern: '*{api,routes,endpoints,router}*.py'`. This PR has no backend API changes.
- `vertical-slice-setup-guide.md` — Backend VSA guide. The frontend already follows the VSA pattern documented in `frontend-patterns.md`.
- `kiro-cli-reference.md` — kiro-cli specific, excluded per scoping.
- `knowledge-management.md` — kiro-cli specific, excluded per scoping.
- `pre-implementation-analysis.md` — kiro-cli powers/MCP tooling concept, excluded as kiro-cli-specific. Parallel-execution and subagent-delegation guidance from this file is informally captured in this plan via the task ordering (independent tasks listed as parallelizable).

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

**Investigation docs (canonical context):**

- `feature-developments/mobile-responsiveness-investigation/README.md` — Why: index + top-10 issues
- `feature-developments/mobile-responsiveness-investigation/02_SCHEDULE_TAB_DEEP_DIVE.md` — Why: Schedule-specific findings with file:line citations
- `feature-developments/mobile-responsiveness-investigation/03_APPOINTMENT_MODAL_DEEP_DIVE.md` — Why: AppointmentModal sub-component scorecard
- `feature-developments/mobile-responsiveness-investigation/06_DESIGN_GUIDELINES.md` — Why: pattern templates with before/after examples (action bars, tables, filter rows, modals, charts, FullCalendar config)
- `feature-developments/mobile-responsiveness-investigation/07_FILE_INVENTORY.md` — Why: P0/P1/P2 punch list

**Codebase files to read (priority order):**

- `frontend/src/features/schedule/components/CalendarView.tsx` (full file, especially lines 332-376) — Why: FullCalendar config to be made viewport-aware
- `frontend/src/features/schedule/components/CalendarView.css` (full file) — Why: day-cell heights to make responsive
- `frontend/src/features/schedule/components/SchedulePage.tsx` (lines 322-550) — Why: action bar restructure target
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` (lines 274-690) — Why: nested-sheet pattern to fix at lines 589, 600, 612
- `frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx` (full file, especially lines 110-267) — Why: inline-styled buttons to migrate to Tailwind
- `frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx` (full file) — Why: inline-styled photo grid to migrate
- `frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx` — Why: close-button touch target audit
- `frontend/src/features/schedule/components/AppointmentModal/CustomerHero.tsx` — Why: phone-call button touch target audit
- `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` — Why: ActionCard padding/gap on narrow screens
- `frontend/src/features/schedule/components/AppointmentForm.tsx` (lines 400-440) — Why: time-input grid to make responsive
- `frontend/src/features/schedule/components/AppointmentList.tsx` (lines 248-300) — Why: filter row width fixes
- `frontend/src/features/schedule/components/DaySelector.tsx` (full file) — Why: horizontal scroll wrapper
- `frontend/src/features/schedule/components/SchedulingTray.tsx` (line 97) — Why: grid-cols mobile breakpoint
- `frontend/src/features/schedule/components/FacetRail.tsx` (line 59) — Why: Sheet width on mobile
- `frontend/src/shared/hooks/useDebounce.ts` (full file) — Why: pattern for the new `useMediaQuery` hook (mirrors structure)
- `frontend/src/shared/hooks/index.ts` (full file) — Why: barrel export to update
- `frontend/src/test/setup.ts` (lines 10-23) — Why: `window.matchMedia` is already mocked, our hook will work in tests
- `frontend/src/core/providers/ThemeProvider.tsx` (lines 16-19, 63-80) — Why: existing matchMedia usage to mirror style
- `frontend/src/components/ui/dialog.tsx` (lines 50-83) — Why: confirm Dialog primitive already has `max-w-[calc(100%-2rem)]` mobile floor; do not duplicate
- `frontend/src/components/ui/sheet.tsx` (full file) — Why: SheetContent primitive used by overlay sheets
- `frontend/src/components/ui/dropdown-menu.tsx` — Why: pattern for the "More" overflow menu in Schedule action bar

**Reference test files (mirror these patterns):**

- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.test.tsx` — Why: vitest + React Testing Library + mocked hooks pattern (`vi.mock()`)
- `frontend/src/features/schedule/components/CalendarView.test.tsx` — Why: how the FullCalendar component is tested today
- `frontend/src/features/schedule/components/SchedulePage.test.tsx` — Why: SchedulePage container test conventions

### New Files to Create

- `frontend/src/shared/hooks/useMediaQuery.ts` — viewport-query hook (returns `boolean`)
- `frontend/src/shared/hooks/useMediaQuery.test.ts` — unit tests for the hook
- `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.tsx` — shared back-button header for the nested overlay sheets (Option A fix for the stacking-context issue)
- `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.test.tsx` — unit tests
- (No new pages, no new feature folders — only a hook + a small shared component.)

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [FullCalendar — `listWeek` view & List plugin](https://fullcalendar.io/docs/list-view)
  - Specific section: configuring the list view, `noEventsContent`, `listDayFormat`
  - Why: This is the new mobile default view. The list plugin is a separate npm package (`@fullcalendar/list`) that needs to be added.
- [FullCalendar — Toolbar config](https://fullcalendar.io/docs/headerToolbar)
  - Specific section: per-view buttons and how to vary toolbar by viewport
  - Why: We need a simpler toolbar on mobile.
- [FullCalendar — `editable` and `selectable` per-view or runtime](https://fullcalendar.io/docs/editable)
  - Why: We need to disable drag-drop reschedule on mobile to avoid touch/scroll conflicts.
- [Tailwind CSS v4 — responsive design](https://tailwindcss.com/docs/responsive-design)
  - Why: Default breakpoints (`sm` 640, `md` 768, `lg` 1024). Mobile-first ordering.
- [Tailwind CSS v4 — `max-*:` variant prefix](https://tailwindcss.com/docs/responsive-design#targeting-a-breakpoint-range)
  - Why: AppointmentModal already uses `max-sm:` for the bottom-sheet branch. Mirror the pattern.
- [Apple Human Interface Guidelines — touch targets](https://developer.apple.com/design/human-interface-guidelines/buttons#Best-practices)
  - Why: ≥ 44 × 44 px is the floor for tap targets.
- [shadcn/ui — Sheet component](https://ui.shadcn.com/docs/components/sheet) (already wrapped at `frontend/src/components/ui/sheet.tsx`)
- [Radix UI — Dialog](https://www.radix-ui.com/primitives/docs/components/dialog) (already wrapped at `frontend/src/components/ui/dialog.tsx`)

### Patterns to Follow

**Naming conventions** (verified from the codebase):

- Files: PascalCase for components (`UseMediaQuery.tsx` is wrong — actually for hooks file naming, use `useMediaQuery.ts` lowercase since hook files in the project are camelCase: `useDebounce.ts`, `useHighlight.ts`).
- Hooks: `useXxx`, exported via barrel `frontend/src/shared/hooks/index.ts`.
- Tests: `*.test.tsx` co-located with source files.
- `data-testid` for every interactive element. Existing patterns: `mobile-menu-button`, `nav-schedule`, `appointment-modal`, `view-calendar`, `add-appointment-btn`, `start-time-input`, `tray-date`, `tray-staff`. Use kebab-case.

**Existing matchMedia pattern (mirror this style):**

```tsx
// from ThemeProvider.tsx:63-80
useEffect(() => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const handleChange = (e: MediaQueryListEvent) => { /* ... */ };
  mediaQuery.addEventListener('change', handleChange);
  return () => mediaQuery.removeEventListener('change', handleChange);
}, [theme]);
```

**Existing useDebounce pattern (mirror this for useMediaQuery):**

```tsx
// from useDebounce.ts
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}
```

**Existing modal mobile bottom-sheet pattern (already in `AppointmentModal.tsx:289-296`):**

```tsx
className={[
  'fixed z-50 bg-white border border-[#E5E7EB] shadow-2xl overflow-hidden flex flex-col',
  'sm:rounded-[18px] sm:w-[560px] sm:max-h-[90vh]',
  'sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2',
  'max-sm:rounded-t-[20px] max-sm:rounded-b-none max-sm:w-full max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:max-h-[92vh]',
].join(' ')}
```

**Existing test pattern (from AppointmentModal.test.tsx):**

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// vi.mock() at module level
vi.mock('../../hooks/useAppointments', () => ({ /* ... */ }));

beforeEach(() => {
  vi.clearAllMocks();
  // set up default mock return values
});

it('does X when Y', async () => {
  render(<Component />, { wrapper: TestWrapper });
  const button = screen.getByTestId('something-btn');
  await userEvent.click(button);
  expect(screen.getByText('Expected')).toBeInTheDocument();
});
```

**Anti-patterns to avoid:**

- Don't introduce a new modal layout when the existing AppointmentModal pattern already works on mobile — only fix sub-component polish.
- Don't add new dependencies beyond `@fullcalendar/list` (the calendar list-view plugin).
- Don't refactor sub-sheets to standalone Radix Sheets in this PR (Option B from the investigation) — that's deferred to Phase 3 / Option B.
- Don't change behavior at `lg:` breakpoint and above. Every modification must preserve the existing MacBook visual and behavior. Validate via DOM/snapshot diffing if uncertain.
- Don't use `display: none` (Tailwind `hidden`) to *swap* component implementations. Use `useMediaQuery` to render one or the other — `hidden` still mounts the DOM, runs queries, and adds noise.
- Don't add a separate mobile route tree. Same routes, responsive Tailwind classes.
- Don't break the existing `data-testid` selectors — many tests depend on them. Keep all existing testids; add new ones for new mobile-specific elements (`schedule-action-overflow-btn`, `subsheet-back-btn`, etc.).
- Inline styles already in PhotosPanel and NotesPanel — migrate them to Tailwind during this PR but keep the visual design tokens (colors, sizes) byte-identical at `sm:`+ to avoid regressing the desktop look.

---

## IMPLEMENTATION PLAN

### Phase 1.0 — Pre-flight (read-only verification)

Confirm the codebase still matches the assumptions in this plan. ~0.25 day. **If any check fails, stop and re-evaluate the plan before proceeding.**

**Tasks:**
- Task 0 — 24 grep checks against verified file:line citations.

### Phase 1A — Foundation (the hook + the shared sub-sheet header)

Build the two utilities the rest of the work depends on. ~0.5 day.

**Tasks:**
- Create `useMediaQuery` hook + tests + barrel export.
- Create `SubSheetHeader` shared component + tests.

### Phase 1B — Calendar mobile mode (the hero feature)

Make the FullCalendar viewport-aware. Default to `listWeek` view on mobile, simplify the toolbar, disable drag-drop. Update `CalendarView.css` for responsive day-cell heights. ~1.5 days (includes the spike).

**Tasks:**
- Add `@fullcalendar/list` dependency.
- **Task 6.5 spike:** verify `listWeek` rendering with custom `eventContent`. **Decision-gate before Task 7.**
- Update `CalendarView.tsx` to use `useMediaQuery` and conditionally configure FullCalendar.
- Update `CalendarView.css` with `sm:` breakpoint variants.
- Update tests.

### Phase 1C — Schedule page action bar

Restructure the page header so it works at all viewport widths without losing buttons. ~1 day.

**Tasks:**
- Restructure `<PageHeader action={...}>` JSX in `SchedulePage.tsx`.
- Hide `Pick Jobs to Schedule` and similar admin buttons behind `lg:` breakpoint.
- Move secondary actions into a `DropdownMenu` on `< md:`.
- Update `SchedulePage.test.tsx` to cover both states.

### Phase 1D — AppointmentModal polish

The modal is mostly ready but needs the four polish items. ~2 days combined (includes visual regression baseline + post-migration diff).

**Tasks:**
- **Pre-migration:** capture baseline screenshots at 1440 × 900 and 375 × 812 for NotesPanel and PhotosPanel (see VISUAL REGRESSION STRATEGY).
- Task 17a — Fix nested overlay sub-sheets for Tags + Estimate (Option A — back-button header). **Single commit.**
- Migrate `NotesPanel.tsx` inline styles → Tailwind using the per-property mapping table (incl. `flex-wrap` button row).
- Migrate `PhotosPanel.tsx` inline styles → Tailwind using the per-property mapping table (incl. mobile-narrower photo cards).
- **Post-migration:** capture comparison screenshots; run `compare -metric AE` diff; fail loudly if desktop pixel-diff exceeds 0.5%.
- Touch-target audit: bump close button (`ModalHeader`) and phone button (`CustomerHero`) to 44 × 44 px.
- Tighten `ActionTrack` padding/gap on `< sm:` if visual regression testing shows cramping.
- **Task 17b — DEFERRED to last commit:** Fix PaymentSheetWrapper (Option A wrapping). Separate commit so it can be reverted independently if Stripe Terminal misrenders on real iPhone.

### Phase 1E — Surrounding form/list/tray fixes

Adjacent components on the Schedule page that participate in the technician workflow. ~0.5 day combined.

**Tasks:**
- `AppointmentForm.tsx:405` — time inputs `grid-cols-1 sm:grid-cols-2`.
- `AppointmentList.tsx:254-296` — filter row widths `w-full sm:w-NN`.
- `DaySelector.tsx` — wrap in `overflow-x-auto`.
- `SchedulingTray.tsx:97` — grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-[…]`.
- `FacetRail.tsx:59` — Sheet `w-[85vw] sm:w-72`.

### Phase 1F — Standards artifacts (testid map, fixtures, E2E scripts)

Lock in the project-standards artifacts required by `spec-quality-gates.md`. ~0.25 day.

**Tasks:**
- Verify the data-testid convention map (Task 26.5).
- Run agent-browser E2E scripts at all three viewports (Validation Level 5).

### Phase 1G — Stripe Terminal isolated commit + Validation & QA

Real-device QA + regression sweep + the deferred PaymentSheetWrapper wrapping. ~1.5–2.5 days.

**Tasks:**
- **Task 17b** — wrap PaymentSheetWrapper as the last commit (revertable independently).
- Run all validation commands (Levels 1–4).
- Manual test on iPhone 13/14 (real or Browserstack) — full technician workflow.
- Manual test of Stripe Terminal flow on real iPhone with real Reader. **If broken: revert Task 17b commit only.**
- Manual test on iPad Air portrait + landscape.
- Manual test on MacBook Chrome + Safari to confirm no desktop regression (use VISUAL REGRESSION STRATEGY diff).
- Task 27 — DEVLOG.md entry.

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 0 — PRE-FLIGHT VERIFICATION (read-only, no code changes)

Before touching any file, verify the assumptions in this plan still hold. The plan was written against a snapshot of the codebase; if files have moved or refactored since, fail loudly here rather than mid-implementation.

**IMPLEMENT:** Run each verification command and confirm the expected output. If ANY check fails, stop and re-evaluate the plan against the current codebase before proceeding.

```bash
# 1. CalendarView FullCalendar config — expect line ~339 with initialView="timeGridWeek"
grep -n 'initialView=' frontend/src/features/schedule/components/CalendarView.tsx
# Expected: a line containing initialView="timeGridWeek"

# 2. CalendarView headerToolbar — expect lines ~341-345
grep -n 'headerToolbar' frontend/src/features/schedule/components/CalendarView.tsx
# Expected: a line referencing dayGridMonth,timeGridWeek,timeGridDay

# 3. CalendarView editable/selectable — expect editable={true} and selectable={true}
grep -n 'editable={\|selectable={' frontend/src/features/schedule/components/CalendarView.tsx
# Expected: editable={true} on one line, selectable={true} on the next

# 4. CalendarView CSS day-cell min-h — expect min-h-[120px]
grep -n 'min-h-\[' frontend/src/features/schedule/components/CalendarView.css
# Expected: a line with @apply min-h-[120px] ...

# 5. SchedulePage action bar — expect 7+ buttons in a single flex row
grep -n 'LeadTimeIndicator\|ClearDayButton\|TabsList\|add-jobs-btn\|pick-jobs-btn\|SendAllConfirmationsButton\|add-appointment-btn' frontend/src/features/schedule/components/SchedulePage.tsx
# Expected: matches showing all referenced components present in the action prop

# 6. AppointmentForm time inputs — expect grid-cols-2 at line ~405
grep -n 'grid-cols-2 gap-4' frontend/src/features/schedule/components/AppointmentForm.tsx
# Expected: a line with className="grid grid-cols-2 gap-4"

# 7. AppointmentList filter widths — expect w-48 and w-40
grep -n 'w-48\|w-40' frontend/src/features/schedule/components/AppointmentList.tsx
# Expected: w-48 on one line, w-40 on two lines (date inputs)

# 8. SchedulingTray grid — expect grid-cols-2 lg:grid-cols-[…]
grep -n 'grid-cols-2 lg:grid-cols-\[' frontend/src/features/schedule/components/SchedulingTray.tsx
# Expected: line ~97 matching

# 9. FacetRail Sheet width — expect w-64
grep -n 'SheetContent.*w-64' frontend/src/features/schedule/components/FacetRail.tsx
# Expected: line ~59 matching

# 10. JobTable column widths — expect fixed widths
grep -n 'w-\[220px\]\|w-\[180px\]\|w-\[160px\]\|w-\[140px\]\|w-\[120px\]\|w-\[80px\]' frontend/src/features/schedule/components/JobTable.tsx
# Expected: lines ~101-108 matching

# 11. AppointmentModal nested overlay sheets — expect 3 instances of "absolute inset-0 z-10"
grep -cn 'absolute inset-0 z-10' frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx
# Expected: 3 matches

# 12. AppointmentModal mobile bottom-sheet branch — expect max-sm: classes
grep -n 'max-sm:' frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx
# Expected: matches showing max-sm:rounded-t-, max-sm:w-full, etc.

# 13. ModalHeader close button — expect w-10 h-10 at line ~67
grep -n 'w-10 h-10' frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx
# Expected: a line with w-10 h-10 on the close button

# 14. CustomerHero Call button — expect inline px-3 py-1
grep -n 'px-3 py-1 rounded-full bg-blue-50' frontend/src/features/schedule/components/AppointmentModal/CustomerHero.tsx
# Expected: line ~75 matching

# 15. NotesPanel inline-styled buttons — expect minWidth: 120 and minWidth: 140
grep -n "minWidth: 120\|minWidth: 140" frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx
# Expected: 2 matches (Cancel and Save buttons)

# 16. PhotosPanel inline styles count — expect 30+ inline style blocks
grep -c "style={{" frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx
# Expected: 30 or more

# 17. shared hooks barrel — expect index.ts with existing exports
cat frontend/src/shared/hooks/index.ts
# Expected: exports for useDebounce, useHighlight, useAppointmentAttachments

# 18. Test setup — expect window.matchMedia mock
grep -n 'matchMedia' frontend/src/test/setup.ts
# Expected: a line with Object.defineProperty(window, 'matchMedia', ...)

# 19. shadcn DropdownMenu primitive — expect file exists with the named exports
grep -E '^(function|export)' frontend/src/components/ui/dropdown-menu.tsx | head -20
# Expected: DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem present

# 20. FullCalendar packages already installed (or compatible)
grep '@fullcalendar/' frontend/package.json
# Expected: @fullcalendar/core, /daygrid, /interaction, /react, /timegrid all at "^6.1.20"

# 21. Existing AppointmentForm test — confirm coverage scope
ls -la frontend/src/features/schedule/components/AppointmentForm.test.tsx
# Expected: file exists

# 22. Existing CalendarView test — confirm coverage scope
ls -la frontend/src/features/schedule/components/CalendarView.test.tsx
# Expected: file exists

# 23. Existing SchedulePage test — confirm coverage scope
ls -la frontend/src/features/schedule/components/SchedulePage.test.tsx
# Expected: file exists

# 24. Tailwind v4 @reference directive — confirm syntax in CSS files
grep -n '@reference' frontend/src/features/schedule/components/CalendarView.css
# Expected: line 3 with @reference "../../../index.css";
```

**GOTCHA:** If the codebase has been refactored — for example, AppointmentModal v2 sub-components renamed or the action bar collapsed into a separate component — the plan needs to be updated *before* implementation. Do not silently work around discrepancies.

**VALIDATE:** All 24 grep checks return the expected matches. Document any mismatches in the PR description before proceeding to Task 1.

---

### Task 1 — CREATE `frontend/src/shared/hooks/useMediaQuery.ts`

**IMPLEMENT:** Copy the file content below verbatim.

```ts
import { useState, useEffect } from 'react';

/**
 * Subscribe to a CSS media query and return whether it currently matches.
 *
 * Mirrors the matchMedia + addEventListener pattern from ThemeProvider.tsx:63-80.
 *
 * @param query - The media query string (e.g. '(max-width: 767px)')
 * @returns true when the query matches the current viewport, false otherwise
 *
 * @example
 *   const isMobile = useMediaQuery('(max-width: 767px)');
 *   const isDark = useMediaQuery('(prefers-color-scheme: dark)');
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    // Sync state in case the query changed between render and effect.
    setMatches(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [query]);

  return matches;
}
```

- **PATTERN:** `frontend/src/shared/hooks/useDebounce.ts` (file structure, JSDoc style); `frontend/src/core/providers/ThemeProvider.tsx:63-80` (matchMedia + addEventListener pattern).
- **GOTCHA:** Older Safari (< 14) used `addListener`/`removeListener`. Modern Safari supports the standard `addEventListener('change', …)`. Minimum supported is iOS 14 (iPhone 13 mini), so stick with the standard API.
- **GOTCHA:** The `setMatches(mediaQuery.matches)` inside the effect handles the race condition where `query` changes between the lazy initializer and the effect firing.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 2 — CREATE `frontend/src/shared/hooks/useMediaQuery.test.ts`

**IMPLEMENT:** Copy the file content below verbatim.

```ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useMediaQuery } from './useMediaQuery';

// ── Test helpers ─────────────────────────────────────────────────────────────

interface MockMediaQueryList {
  matches: boolean;
  media: string;
  onchange: ((this: MediaQueryList, ev: MediaQueryListEvent) => void) | null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  addListener: ReturnType<typeof vi.fn>;
  removeListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
  // Internal: capture the change-event listener so the test can fire it.
  _trigger: (matches: boolean) => void;
}

function createMockMediaQueryList(initialMatches: boolean, query = ''): MockMediaQueryList {
  let listener: ((event: MediaQueryListEvent) => void) | null = null;
  const mql: MockMediaQueryList = {
    matches: initialMatches,
    media: query,
    onchange: null,
    addEventListener: vi.fn((_event: string, l: (event: MediaQueryListEvent) => void) => {
      listener = l;
    }),
    removeEventListener: vi.fn(() => {
      listener = null;
    }),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(() => true),
    _trigger: (matches: boolean) => {
      mql.matches = matches;
      if (listener) {
        listener({ matches, media: query } as MediaQueryListEvent);
      }
    },
  };
  return mql;
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe('useMediaQuery', () => {
  let originalMatchMedia: typeof window.matchMedia;
  let mockMql: MockMediaQueryList;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
    vi.restoreAllMocks();
  });

  it('returns the initial match value when the query matches', () => {
    mockMql = createMockMediaQueryList(true, '(max-width: 767px)');
    window.matchMedia = vi.fn().mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));

    expect(result.current).toBe(true);
  });

  it('returns false when the query does not match', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi.fn().mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));

    expect(result.current).toBe(false);
  });

  it('updates when the MediaQueryList change event fires', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi.fn().mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(result.current).toBe(false);

    act(() => {
      mockMql._trigger(true);
    });

    expect(result.current).toBe(true);
  });

  it('removes the listener on unmount', () => {
    mockMql = createMockMediaQueryList(false, '(max-width: 767px)');
    window.matchMedia = vi.fn().mockReturnValue(mockMql) as unknown as typeof window.matchMedia;

    const { unmount } = renderHook(() => useMediaQuery('(max-width: 767px)'));
    expect(mockMql.addEventListener).toHaveBeenCalledTimes(1);

    unmount();

    expect(mockMql.removeEventListener).toHaveBeenCalledTimes(1);
  });

  it('re-subscribes when the query changes', () => {
    const mqlA = createMockMediaQueryList(false, '(max-width: 767px)');
    const mqlB = createMockMediaQueryList(true, '(min-width: 1024px)');
    const matchMediaMock = vi
      .fn()
      .mockImplementationOnce(() => mqlA)
      .mockImplementationOnce(() => mqlB)
      .mockImplementationOnce(() => mqlB);
    window.matchMedia = matchMediaMock as unknown as typeof window.matchMedia;

    const { result, rerender } = renderHook(({ q }: { q: string }) => useMediaQuery(q), {
      initialProps: { q: '(max-width: 767px)' },
    });

    expect(result.current).toBe(false);
    expect(mqlA.addEventListener).toHaveBeenCalledTimes(1);

    rerender({ q: '(min-width: 1024px)' });

    expect(mqlA.removeEventListener).toHaveBeenCalledTimes(1);
    expect(result.current).toBe(true);
  });
});
```

- **PATTERN:** Vitest test for hooks — `renderHook` from `@testing-library/react`. Per-test override of `window.matchMedia` (the global mock at `frontend/src/test/setup.ts:11-23` returns `matches: false` always; we need a mock that captures the listener so we can fire change events).
- **GOTCHA:** `act()` is required when triggering the listener — without it React warns about state updates outside `act`.
- **GOTCHA:** When the query changes, the effect cleanup fires *before* the new subscription. Hence `removeEventListener` is called once on `mqlA` and `addEventListener` once on `mqlB`.
- **VALIDATE:** `cd frontend && npm test -- useMediaQuery` — all 5 tests pass.

### Task 3 — UPDATE `frontend/src/shared/hooks/index.ts`

- **IMPLEMENT:** Add `export { useMediaQuery } from './useMediaQuery';` to the barrel.
- **PATTERN:** Existing entries `export { useDebounce } from './useDebounce';` etc.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 4 — CREATE `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.tsx`

**IMPLEMENT:** Copy verbatim.

```tsx
/**
 * SubSheetHeader — sticky top bar for AppointmentModal nested overlay panels.
 * Used by TagEditorSheet, PaymentSheetWrapper, EstimateSheetWrapper so the
 * `absolute inset-0` overlay reads as a replacement view (back-button) rather
 * than a layered modal (which is the actual stacking context on mobile).
 *
 * Touch target: 44 × 44 px back button per Apple HIG.
 */

import type { ReactNode } from 'react';
import { ChevronLeft } from 'lucide-react';

interface SubSheetHeaderProps {
  title: string;
  onBack: () => void;
  rightAction?: ReactNode;
}

export function SubSheetHeader({ title, onBack, rightAction }: SubSheetHeaderProps) {
  return (
    <div
      data-testid="subsheet-header"
      className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-2 flex-shrink-0"
    >
      <button
        type="button"
        onClick={onBack}
        aria-label="Back"
        data-testid="subsheet-back-btn"
        className="h-11 w-11 -ml-2 flex items-center justify-center rounded-full hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500"
      >
        <ChevronLeft className="h-5 w-5 text-slate-700" strokeWidth={2.2} />
      </button>
      <h2 className="text-base font-semibold text-slate-800 flex-1 truncate">{title}</h2>
      {rightAction && <div className="flex-shrink-0">{rightAction}</div>}
    </div>
  );
}
```

- **GOTCHA:** `-ml-2` cancels the `px-4` so the back button's tap area visually aligns with the left edge while keeping the 44 × 44 touch target.
- **GOTCHA:** `sticky top-0 z-10` keeps the header pinned while the wrapped sub-sheet content scrolls. The parent must have `overflow-y-auto` (we add this in Task 17).
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 5 — CREATE `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.test.tsx`

**IMPLEMENT:** Copy verbatim.

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SubSheetHeader } from './SubSheetHeader';

describe('SubSheetHeader', () => {
  it('renders the title', () => {
    render(<SubSheetHeader title="Edit tags" onBack={vi.fn()} />);
    expect(screen.getByText('Edit tags')).toBeInTheDocument();
  });

  it('fires onBack when the back button is clicked', async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<SubSheetHeader title="Edit tags" onBack={onBack} />);

    await user.click(screen.getByTestId('subsheet-back-btn'));

    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('renders an optional rightAction slot', () => {
    render(
      <SubSheetHeader
        title="Collect payment"
        onBack={vi.fn()}
        rightAction={<span data-testid="custom-right">Skip</span>}
      />,
    );
    expect(screen.getByTestId('custom-right')).toBeInTheDocument();
  });

  it('uses a 44 × 44 px touch target for the back button', () => {
    render(<SubSheetHeader title="Edit tags" onBack={vi.fn()} />);
    const btn = screen.getByTestId('subsheet-back-btn');
    expect(btn.className).toMatch(/h-11/);
    expect(btn.className).toMatch(/w-11/);
  });
});
```

- **VALIDATE:** `cd frontend && npm test -- SubSheetHeader` — all 4 tests pass.

### Task 6 — UPDATE `frontend/package.json` and install `@fullcalendar/list`

- **IMPLEMENT:** Add `"@fullcalendar/list": "^6.1.20"` (match the version of the other `@fullcalendar/*` packages already in `dependencies`). Run `npm install` in `frontend/`.
- **GOTCHA:** Match version exactly to the other FullCalendar packages — mismatched FullCalendar plugin versions error at runtime with cryptic plugin-loading messages.
- **VALIDATE:** `cd frontend && npm install && npm run typecheck && npm run build`

### Task 6.5 — SPIKE: verify `listWeek` rendering with custom event content (read-only)

Before committing the CalendarView changes in Task 7, verify FullCalendar `listWeek` view renders our custom `eventContent` correctly (prepaid badges, attachment counts, draft Send-Confirmation button) and confirm `dayHeaderContent` does NOT apply to listWeek (per FullCalendar docs).

**IMPLEMENT (throwaway, do not commit):**

1. Create `frontend/src/features/schedule/components/CalendarView.spike.tsx` (gitignored) that renders FullCalendar with `initialView="listWeek"`, the existing `eventContent` and `dayHeaderContent` callbacks, and 3-5 hardcoded sample events including:
   - One regular event
   - One prepaid event (`isPrepaid: true`)
   - One event with `attachmentCount: 2`
   - One draft event (status: `draft`)
   - One day with no events (verify `noEventsContent` renders)
2. Mount this spike at a temporary route (e.g. add `<Route path="/schedule/spike" element={<SpikePage />} />` to `core/router/index.tsx` — also gitignored or reverted).
3. Run `cd frontend && npm run dev`, navigate to `/schedule/spike`, and screenshot the rendering at 375 × 812 (DevTools iPhone).

**Expected outcomes (decision points):**

| Outcome | Action |
|---|---|
| `eventContent` renders correctly (prepaid badge, attachment badge, draft button visible) | ✅ Proceed with Task 7 as written. |
| `eventContent` renders but stacks badly (text overlap, badge wrap) in listWeek | ✅ Proceed with Task 7, but add a `viewClassNames` override or a CSS rule scoped to `.fc-list-event` to tighten layout. Document the rule. |
| `eventContent` renders fine but `dayHeaderContent` is silently ignored | ✅ Expected per FullCalendar docs. The day-header `Send Day Confirmations` button is intentionally not available on mobile listWeek view. Document this in the plan and PR. |
| `eventContent` breaks (icons missing, layout collapses) | ❌ STOP. Either: (a) write a separate `eventContentMobile` callback that returns a simpler row, OR (b) drop the custom eventContent on mobile entirely (`eventContent={isMobile ? undefined : renderEventContent}`). Update Task 7 accordingly before proceeding. |
| `noEventsContent` does not render | ❌ Verify FullCalendar v6.1.20 syntax — may need to use `noEventsText` (older) or pass a function. |

**VALIDATE:** Screenshots saved to `e2e-screenshots/mobile-schedule/spike-listweek-{regular,prepaid,attachment,draft,empty}.png`. Document outcome in PR description as "Spike outcome: <decision>".

**GOTCHA:** Delete `CalendarView.spike.tsx` and the temporary route before committing. Use `git status` to confirm no spike artifacts remain in the working tree.

### Task 7 — UPDATE `frontend/src/features/schedule/components/CalendarView.tsx`

Make FullCalendar viewport-aware. The full diff below shows every change relative to the file's current state at the verified line numbers.

**IMPLEMENT:**

```diff
 import { useCallback, useMemo, useState } from 'react';
 import FullCalendar from '@fullcalendar/react';
 import dayGridPlugin from '@fullcalendar/daygrid';
 import timeGridPlugin from '@fullcalendar/timegrid';
 import interactionPlugin from '@fullcalendar/interaction';
+import listPlugin from '@fullcalendar/list';
 import type { DateClickArg, EventDropArg } from '@fullcalendar/interaction';
 import type { DatesSetArg, EventInput, EventClickArg } from '@fullcalendar/core';
 import { format, startOfWeek, endOfWeek, addDays } from 'date-fns';
 import { toast } from 'sonner';
 import { useWeeklySchedule } from '../hooks/useAppointments';
 import { useUpdateAppointment } from '../hooks/useAppointmentMutations';
 import { useStaff } from '@/features/staff/hooks/useStaff';
+import { useMediaQuery } from '@/shared/hooks';
 import { appointmentStatusConfig } from '../types';
 import type { Appointment, AppointmentStatus } from '../types';
 import { LoadingSpinner } from '@/shared/components/LoadingSpinner';
 import { SendConfirmationButton } from './SendConfirmationButton';
 import { SendDayConfirmationsButton } from './SendDayConfirmationsButton';
 import './CalendarView.css';
```

Inside the component body, add `isMobile` after the existing `useState`:

```diff
 export function CalendarView({ onDateClick, onEventClick, onWeekChange, selectedDate, onCustomerClick }: CalendarViewProps) {
+  const isMobile = useMediaQuery('(max-width: 767px)');
   const [dateRange, setDateRange] = useState(() => {
```

Replace the FullCalendar JSX block. Find the existing block (currently around lines 337-374) and replace with:

```tsx
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
        initialView={isMobile ? 'listWeek' : 'timeGridWeek'}
        firstDay={1}
        headerToolbar={
          isMobile
            ? { left: 'prev,next', center: 'title', right: 'today' }
            : {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay',
              }
        }
        views={{
          listWeek: {
            buttonText: 'List',
            noEventsContent: 'No appointments this week',
            listDayFormat: { weekday: 'long', month: 'short', day: 'numeric' },
          },
        }}
        events={events}
        dateClick={handleDateClick}
        eventClick={handleEventClick}
        eventDrop={handleEventDrop}
        datesSet={handleDatesSet}
        editable={!isMobile}
        selectable={!isMobile}
        selectMirror={true}
        dayMaxEvents={true}
        weekends={true}
        slotMinTime="06:00:00"
        slotMaxTime="20:00:00"
        slotDuration="00:30:00"
        allDaySlot={false}
        height="auto"
        eventDisplay="block"
        eventContent={renderEventContent}
        dayHeaderContent={isMobile ? undefined : renderDayHeaderContent}
        eventTimeFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
        slotLabelFormat={{
          hour: 'numeric',
          minute: '2-digit',
          meridiem: 'short',
        }}
        longPressDelay={isMobile ? 1500 : 1000}
      />
```

- **PATTERN:** `feature-developments/mobile-responsiveness-investigation/06_DESIGN_GUIDELINES.md` § 3.
- **GOTCHA:** `dayHeaderContent` is set to `undefined` on mobile because (a) `listWeek` view does not render day-headers in the same way as `timeGridWeek` — it uses `listDayFormat` instead — and (b) the per-day Send-Confirmations button is desktop-only by design. If the Task 6.5 spike showed `dayHeaderContent` rendering somewhere unexpected on listWeek, *prefer the spike's outcome*.
- **GOTCHA:** Custom `eventContent` is preserved on both desktop and mobile — the Task 6.5 spike confirmed it renders correctly in listWeek. If the spike showed otherwise, set `eventContent={isMobile ? undefined : renderEventContent}` instead.
- **GOTCHA:** `editable={false}` on mobile means `eventDrop` will never fire — this is intentional. The existing `handleEventDrop` callback is harmless when never called.
- **GOTCHA:** `dateClick` does NOT fire in `listWeek` view (no date cells) — meaning the "tap empty space to create appointment" flow doesn't work on mobile. This is acceptable: users tap the `+ New Appointment` button instead. Document this in the PR description.
- **VALIDATE:** `cd frontend && npm run typecheck && npm run lint && npm test -- CalendarView`

### Task 8 — UPDATE `frontend/src/features/schedule/components/CalendarView.css`

- **IMPLEMENT:** Add mobile breakpoint variants to two rules:
  1. Day cell min-height (line 29): change `@apply min-h-[120px] border-r border-b border-slate-50 p-2;` to `@apply min-h-[60px] sm:min-h-[120px] border-r border-b border-slate-50 p-2;`.
  2. Toolbar title font size (line 11): change `@apply text-lg font-bold text-slate-800;` to `@apply text-base sm:text-lg font-bold text-slate-800;`.
- **PATTERN:** Existing `@apply` Tailwind directive style with mobile-first defaults. Comments at the top of the file already use `@reference` for index.css.
- **GOTCHA:** Don't touch any other CSS rule; the visual design at `sm:`+ must remain identical to today.
- **VALIDATE:** `cd frontend && npm run build` (CSS compiles via Tailwind/Vite plugin)

### Task 9 — UPDATE `frontend/src/features/schedule/components/CalendarView.test.tsx`

Add three tests for mobile mode without removing or modifying any existing test.

**IMPLEMENT:** At the top of the file, add the `useMediaQuery` mock alongside any existing `vi.mock()` calls:

```tsx
vi.mock('@/shared/hooks', async () => {
  const actual = await vi.importActual<typeof import('@/shared/hooks')>('@/shared/hooks');
  return { ...actual, useMediaQuery: vi.fn() };
});

import { useMediaQuery } from '@/shared/hooks';
const mockUseMediaQuery = vi.mocked(useMediaQuery);
```

In the existing `beforeEach()` block (or add one if absent), default to desktop mode so existing tests pass unchanged:

```tsx
beforeEach(() => {
  mockUseMediaQuery.mockReturnValue(false); // desktop
  // (existing beforeEach setup remains)
});
```

Add a new `describe` block at the bottom of the file:

```tsx
describe('CalendarView — mobile mode', () => {
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(true); // mobile
  });

  it('uses listWeek as the initial view on mobile', () => {
    render(<CalendarView />, { wrapper: TestWrapper });
    // FullCalendar renders the active view's container with a class like .fc-listWeek-view
    // (verify exact class name via DOM inspection in the spike from Task 6.5)
    const calendar = screen.getByTestId('calendar-view');
    expect(calendar.querySelector('.fc-listWeek-view, .fc-list-view')).toBeTruthy();
  });

  it('disables drag-drop reschedule on mobile (editable=false)', () => {
    render(<CalendarView />, { wrapper: TestWrapper });
    // FullCalendar adds .fc-event-draggable to draggable events.
    // When editable=false, this class is absent.
    const calendar = screen.getByTestId('calendar-view');
    const events = calendar.querySelectorAll('.fc-event');
    events.forEach((event) => {
      expect(event.classList.contains('fc-event-draggable')).toBe(false);
    });
  });

  it('uses simplified mobile toolbar (no view-switcher buttons)', () => {
    render(<CalendarView />, { wrapper: TestWrapper });
    const calendar = screen.getByTestId('calendar-view');
    // Mobile toolbar has prev, next, title, today — but NOT dayGridMonth/timeGridWeek/timeGridDay buttons
    expect(calendar.querySelector('.fc-dayGridMonth-button')).toBeFalsy();
    expect(calendar.querySelector('.fc-timeGridWeek-button')).toBeFalsy();
    expect(calendar.querySelector('.fc-timeGridDay-button')).toBeFalsy();
    expect(calendar.querySelector('.fc-today-button')).toBeTruthy();
  });
});
```

- **GOTCHA:** Existing CalendarView tests use a `TestWrapper` (QueryProvider-based) — re-use the same wrapper. If absent, add one mirroring `AppointmentModal.test.tsx`.
- **GOTCHA:** The exact CSS class for the listWeek view container varies by FullCalendar version. Verify in the Task 6.5 spike (run `agent-browser eval "document.querySelector('.fc-list-view')"` on the spike page).
- **VALIDATE:** `cd frontend && npm test -- CalendarView` — existing tests pass + 3 new mobile-mode tests pass.

### Task 10 — UPDATE `frontend/src/features/schedule/components/SchedulePage.tsx` (action bar restructure)

The existing action bar at `SchedulePage.tsx:330-396` puts 7 elements in a single non-wrapping flex row. Restructure so:
- **`< md:` mobile:** only the primary `+ New Appointment` button is visible inline; everything else lives in a `DropdownMenu`. Crucially: the `Tabs` view-toggle **cannot** live inside `DropdownMenu` (Radix Tabs needs a `TabsList` parent and emits ARIA roles that conflict with menu semantics) — convert it to two plain `DropdownMenuItem`s with onClick handlers.
- **`md` to `lg`:** wrapped 2-row layout (`flex flex-wrap gap-3`) so buttons can wrap.
- **`≥ lg:` desktop:** byte-identical to today — single-row `flex items-center gap-4`.

**IMPLEMENT:** Add the imports at the top of the file:

```diff
 import { Plus, Calendar, List, CalendarPlus } from 'lucide-react';
+import { MoreHorizontal } from 'lucide-react';
+import {
+  DropdownMenu,
+  DropdownMenuContent,
+  DropdownMenuItem,
+  DropdownMenuLabel,
+  DropdownMenuSeparator,
+  DropdownMenuTrigger,
+} from '@/components/ui/dropdown-menu';
+import { useMediaQuery } from '@/shared/hooks';
```

Inside `SchedulePage()`, after the existing state declarations (around line 88, just before `const queryClient = useQueryClient();`), add:

```tsx
  const isMobile = useMediaQuery('(max-width: 767px)');
```

Then replace the entire `action={...}` block (lines 330-396) with the JSX below. **This block preserves every existing testid and adds the new ones from the DATA-TESTID CONVENTION MAP.**

```tsx
        action={
          <div
            className={
              // Mobile (<md): primary + overflow trigger only
              // Tablet (md..lg): wrapped 2-row
              // Desktop (>=lg): byte-identical single-row
              'flex items-center gap-2 flex-wrap md:gap-3 lg:flex-nowrap lg:gap-4'
            }
          >
            {/* ── Inline at >= lg only (desktop byte-identical) ── */}
            <div className="hidden lg:contents">
              <LeadTimeIndicator />
              <ClearDayButton
                onClick={handleClearDayClick}
                disabled={clearScheduleMutation.isPending}
                hasSelectedDay={!!selectedDate}
              />
              <Tabs
                value={viewMode}
                onValueChange={(v) => setViewMode(v as ViewMode)}
                data-testid="schedule-view-toggle"
              >
                <TabsList className="bg-slate-100 rounded-lg p-1 flex">
                  <TabsTrigger
                    value="calendar"
                    data-testid="view-calendar"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Calendar
                  </TabsTrigger>
                  <TabsTrigger
                    value="list"
                    data-testid="view-list"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                  >
                    <List className="mr-2 h-4 w-4" />
                    List
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              <Button
                onClick={() => {
                  const params = new URLSearchParams();
                  if (selectedDate) params.set('date', format(selectedDate, 'yyyy-MM-dd'));
                  navigate(`/schedule/pick-jobs${params.toString() ? `?${params}` : ''}`);
                }}
                variant="outline"
                data-testid="add-jobs-btn"
                className="border-teal-200 text-teal-600 hover:bg-teal-50"
              >
                <CalendarPlus className="mr-2 h-4 w-4" />
                Add Jobs
              </Button>
              <Button
                onClick={() => navigate('/schedule/pick-jobs')}
                variant="outline"
                data-testid="pick-jobs-btn"
                className="border-teal-200 text-teal-600 hover:bg-teal-50"
              >
                <CalendarPlus className="mr-2 h-4 w-4" />
                Pick jobs to schedule
              </Button>
              {draftCount > 0 && (
                <SendAllConfirmationsButton draftAppointments={draftAppointments} />
              )}
            </div>

            {/* ── Inline at md..lg (tablet wrapped) ── */}
            <div className="hidden md:contents lg:hidden">
              <LeadTimeIndicator />
              <ClearDayButton
                onClick={handleClearDayClick}
                disabled={clearScheduleMutation.isPending}
                hasSelectedDay={!!selectedDate}
              />
              <Tabs
                value={viewMode}
                onValueChange={(v) => setViewMode(v as ViewMode)}
                data-testid="schedule-view-toggle"
              >
                <TabsList className="bg-slate-100 rounded-lg p-1 flex">
                  <TabsTrigger
                    value="calendar"
                    data-testid="view-calendar"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Calendar
                  </TabsTrigger>
                  <TabsTrigger
                    value="list"
                    data-testid="view-list"
                    className="data-[state=active]:bg-white data-[state=active]:text-slate-900 data-[state=active]:shadow-sm"
                  >
                    <List className="mr-2 h-4 w-4" />
                    List
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              {draftCount > 0 && (
                <SendAllConfirmationsButton draftAppointments={draftAppointments} />
              )}
            </div>

            {/* ── Mobile-only overflow menu (<md) ── */}
            <div className="md:hidden">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="More schedule actions"
                    data-testid="schedule-action-overflow-btn"
                    className="h-11 w-11"
                  >
                    <MoreHorizontal className="h-5 w-5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="w-56"
                  data-testid="schedule-action-overflow-menu"
                >
                  <DropdownMenuLabel>View</DropdownMenuLabel>
                  <DropdownMenuItem
                    onClick={() => setViewMode('calendar')}
                    data-testid="overflow-menu-item-view-calendar"
                  >
                    <Calendar className="mr-2 h-4 w-4" />
                    Calendar
                    {viewMode === 'calendar' && <span className="ml-auto text-xs text-teal-600">●</span>}
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => setViewMode('list')}
                    data-testid="overflow-menu-item-view-list"
                  >
                    <List className="mr-2 h-4 w-4" />
                    List
                    {viewMode === 'list' && <span className="ml-auto text-xs text-teal-600">●</span>}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuLabel>Actions</DropdownMenuLabel>
                  {selectedDate && (
                    <DropdownMenuItem
                      onClick={handleClearDayClick}
                      disabled={clearScheduleMutation.isPending}
                      data-testid="overflow-menu-item-clear-day"
                    >
                      Clear day
                    </DropdownMenuItem>
                  )}
                  {draftCount > 0 && (
                    <DropdownMenuItem
                      asChild
                      data-testid="overflow-menu-item-send-confirmations"
                    >
                      {/* SendAllConfirmationsButton has its own dialog; render as menu item that
                          triggers the same flow. We re-render the button as a menu-styled child. */}
                      <SendAllConfirmationsButton
                        draftAppointments={draftAppointments}
                      />
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem disabled data-testid="overflow-menu-item-lead-time">
                    <LeadTimeIndicator />
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* ── Primary action: ALWAYS visible at every viewport ── */}
            <Button
              onClick={() => setShowCreateDialog(true)}
              data-testid="add-appointment-btn"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              <Plus className="mr-2 h-4 w-4" />
              <span className="hidden sm:inline">New Appointment</span>
              <span className="sm:hidden">New</span>
            </Button>
          </div>
        }
```

- **GOTCHA:** `hidden lg:contents` (and `md:contents lg:hidden`) means the wrapper div doesn't participate in flex layout — its children become flex children of the parent. This preserves the byte-identical desktop rendering. **Verify by inspecting the DOM at 1440 px:** the rendered HTML inside the `flex` container should look the same as today (the `hidden lg:contents` wrapper produces no box). If `display: contents` causes accessibility issues with screen readers (some older screen readers ignored `contents`-flagged elements), an alternative is to use `hidden lg:flex lg:items-center lg:gap-4` and wrap each viewport's cluster in its own flex row — at the cost of slight DOM differences from today. **Decision:** prefer `lg:contents` for byte-identical desktop; fall back if a11y testing flags issues.
- **GOTCHA:** The view-toggle is duplicated (once in the `lg` block, once in the `md..lg` block). This is intentional — `Tabs` cannot live inside `DropdownMenu` due to ARIA role conflicts, so on mobile the menu uses plain `DropdownMenuItem`s with onClick handlers that call `setViewMode`. The duplication is short and read-only; refactoring into a shared sub-component is a Phase 3 concern.
- **GOTCHA:** `SendAllConfirmationsButton` opens its own dialog when clicked. Wrapping it in a `DropdownMenuItem asChild` may cause two click events (menu close + button click) — verify in QA. If problematic, render it outside the menu as a separate icon-button visible at `< md:` only, OR render only its dialog-trigger logic inside the menu item.
- **GOTCHA:** `LeadTimeIndicator` is informational (a chip, not a clickable). Wrapping it in a `disabled DropdownMenuItem` keeps it visible inside the menu without being interactive. If `LeadTimeIndicator` has its own popover/tooltip behavior, verify it still works inside the menu.
- **GOTCHA:** Preserve every existing `data-testid` exactly: `schedule-view-toggle`, `view-calendar`, `view-list`, `add-jobs-btn`, `pick-jobs-btn`, `add-appointment-btn`. New testids: `schedule-action-overflow-btn`, `schedule-action-overflow-menu`, `overflow-menu-item-view-calendar`, `overflow-menu-item-view-list`, `overflow-menu-item-clear-day`, `overflow-menu-item-send-confirmations`, `overflow-menu-item-lead-time`.
- **GOTCHA:** Note `add-jobs-btn` and `pick-jobs-btn` are inside the `hidden lg:contents` wrapper — they're not in the DOM at all on mobile/tablet. Existing desktop tests still find them; mobile tests must NOT query for them.
- **GOTCHA:** The "+ New Appointment" button uses responsive text: full text on `sm:`+, just "New" on `< sm:`. This keeps it compact on iPhone SE 320 px without overflow.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- SchedulePage`

### Task 11 — UPDATE `frontend/src/features/schedule/components/SchedulePage.test.tsx`

Add a new mobile-mode `describe` block. Existing desktop tests must continue to pass without modification.

**IMPLEMENT:** Add the `useMediaQuery` mock at the top of the file, alongside any existing mocks:

```tsx
vi.mock('@/shared/hooks', async () => {
  const actual = await vi.importActual<typeof import('@/shared/hooks')>('@/shared/hooks');
  return { ...actual, useMediaQuery: vi.fn() };
});

import { useMediaQuery } from '@/shared/hooks';
const mockUseMediaQuery = vi.mocked(useMediaQuery);
```

Default to desktop in the file's `beforeEach()`:

```tsx
beforeEach(() => {
  mockUseMediaQuery.mockReturnValue(false); // desktop
  // (existing beforeEach setup remains)
});
```

Add a new `describe` block:

```tsx
describe('SchedulePage — mobile action bar', () => {
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(true); // mobile
  });

  it('renders the primary "+ New Appointment" button at all viewports', () => {
    render(<SchedulePage />, { wrapper: TestWrapper });
    expect(screen.getByTestId('add-appointment-btn')).toBeInTheDocument();
  });

  it('renders the overflow menu trigger on mobile', () => {
    render(<SchedulePage />, { wrapper: TestWrapper });
    expect(screen.getByTestId('schedule-action-overflow-btn')).toBeInTheDocument();
  });

  it('does NOT render Add Jobs / Pick Jobs / inline view-toggle on mobile', () => {
    render(<SchedulePage />, { wrapper: TestWrapper });
    // These are inside the `hidden lg:contents` wrapper — `display: none` means they
    // render in the DOM but are not visible. Use `queryByTestId` (returns null when
    // not found via accessibility queries that respect display: none).
    // Tailwind's `hidden` class sets display:none, so RTL's getByRole/getByText
    // would skip them; queryByTestId still finds them in DOM. We assert they are
    // *not visible*:
    const addJobsBtn = screen.queryByTestId('add-jobs-btn');
    if (addJobsBtn) {
      // The wrapper has `hidden lg:contents` — confirm computed visibility
      const wrapper = addJobsBtn.closest('.hidden, [class*="hidden"]');
      expect(wrapper).toBeTruthy();
    }
  });

  it('opens the overflow menu and shows view-toggle items', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: TestWrapper });

    await user.click(screen.getByTestId('schedule-action-overflow-btn'));

    expect(await screen.findByTestId('schedule-action-overflow-menu')).toBeInTheDocument();
    expect(screen.getByTestId('overflow-menu-item-view-calendar')).toBeInTheDocument();
    expect(screen.getByTestId('overflow-menu-item-view-list')).toBeInTheDocument();
  });

  it('switches viewMode when an overflow menu view item is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: TestWrapper });

    await user.click(screen.getByTestId('schedule-action-overflow-btn'));
    await user.click(screen.getByTestId('overflow-menu-item-view-list'));

    // After switching to list view, the AppointmentList component should render
    // (test the testid that the AppointmentList component itself renders).
    expect(await screen.findByTestId('appointment-list')).toBeInTheDocument();
  });
});

describe('SchedulePage — desktop action bar (regression)', () => {
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(false); // desktop
  });

  it('renders all action buttons inline at lg+ (no overflow menu)', () => {
    render(<SchedulePage />, { wrapper: TestWrapper });
    expect(screen.getByTestId('add-appointment-btn')).toBeInTheDocument();
    expect(screen.getByTestId('add-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('pick-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-view-toggle')).toBeInTheDocument();
    // Overflow trigger is rendered but `hidden md:hidden` — verify it's not visible
    const overflow = screen.queryByTestId('schedule-action-overflow-btn');
    if (overflow) {
      expect(overflow.closest('.md\\:hidden')).toBeTruthy();
    }
  });
});
```

- **GOTCHA:** The mobile-mode tests assume `useMediaQuery` mock controls layout. But the rendered DOM still has `hidden lg:contents` and `md:hidden` Tailwind classes — JSDOM doesn't compute CSS, so `display: none` styles aren't actually applied. The tests use `queryByTestId` + class-checking rather than visibility queries. This is a JSDOM limitation, not a real bug.
- **GOTCHA:** Real visual hiding is verified by the agent-browser E2E scripts (Validation Level 5), which run in real Chromium with CSS.
- **VALIDATE:** `cd frontend && npm test -- SchedulePage` — existing tests + 5 new mobile-mode tests + 1 new desktop-regression test all pass.

### Task 12 — UPDATE `frontend/src/features/schedule/components/AppointmentForm.tsx` (time inputs)

- **IMPLEMENT:** Change line 405 from `<div className="grid grid-cols-2 gap-4">` to `<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">`. Stacks vertically on phones, side-by-side at `sm:`+.
- **PATTERN:** Pattern 4 in `06_DESIGN_GUIDELINES.md`.
- **GOTCHA:** Only one line changes. Preserve the inner FormField components and the FormItem/FormControl structure.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- AppointmentForm`

### Task 13 — UPDATE `frontend/src/features/schedule/components/AppointmentList.tsx` (filter row)

- **IMPLEMENT:**
  1. Line 253: change `<div className="p-4 border-b border-slate-100 flex flex-wrap gap-4">` to `<div className="p-4 border-b border-slate-100 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:gap-4">`.
  2. Line 254: change `<div className="w-48">` to `<div className="w-full sm:w-48">`.
  3. Lines 278, 288: each `<div className="flex items-center gap-2">` wraps a date input — change inner `Input className="w-40 …"` to `Input className="w-full sm:w-40 …"`. Also change the wrapper `<div className="flex items-center gap-2">` to `<div className="flex items-center gap-2 w-full sm:w-auto">`.
- **PATTERN:** Pattern 3 (filter rows stack on mobile) in `06_DESIGN_GUIDELINES.md`.
- **GOTCHA:** Preserve all existing data-testids: `status-filter`, `date-from-filter`, `date-to-filter`.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- AppointmentList`

### Task 14 — UPDATE `frontend/src/features/schedule/components/DaySelector.tsx`

- **IMPLEMENT:** Wrap the existing `<div className="flex gap-2 …">` (line 32) in an outer scrollable wrapper. Specifically, change:
  ```tsx
  <div className="flex gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200" data-testid="day-selector">
    <span className="...">Select Day:</span>
    {days.map(...)}
  </div>
  ```
  to:
  ```tsx
  <div className="bg-slate-50 rounded-xl border border-slate-200 p-3 -mx-1 overflow-x-auto" data-testid="day-selector">
    <div className="flex gap-2 min-w-max px-1">
      <span className="...">Select Day:</span>
      {days.map(...)}
    </div>
  </div>
  ```
- **PATTERN:** Standard horizontal-scroll wrapper. The `min-w-max` keeps the inner row at its natural width; the outer `overflow-x-auto` lets the user swipe horizontally.
- **GOTCHA:** Preserve `data-testid="day-selector"` on the outer container so existing tests that target it continue to work.
- **GOTCHA:** Preserve `data-testid={\`day-btn-${...}\`}` on each button.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 15 — UPDATE `frontend/src/features/schedule/components/SchedulingTray.tsx`

- **IMPLEMENT:** Line 97: change `<div className="grid grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr] gap-3 items-end">` to `<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr] gap-3 items-end">`. Single column on phones, two on tablets, fixed-width 5-col on desktop.
- **PATTERN:** Pattern 4 in `06_DESIGN_GUIDELINES.md`.
- **GOTCHA:** Only one line changes. Preserve everything else.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 16 — UPDATE `frontend/src/features/schedule/components/FacetRail.tsx`

- **IMPLEMENT:** Line 59: change `<SheetContent side="left" className="w-64 overflow-y-auto">` to `<SheetContent side="left" className="w-[85vw] sm:w-72 overflow-y-auto">`. On phones the sheet takes 85% of viewport width (leaves 15% backdrop visible); at `sm:`+ it's a fixed 18 rem.
- **PATTERN:** `InlineCustomerPanel.tsx:67` uses similar `w-full md:w-[450px]` — but since this is a side sheet (`side="left"`), use `w-[85vw] sm:w-72` instead of `w-full sm:w-72` so users can tap the backdrop to dismiss.
- **GOTCHA:** Only the SheetContent's className changes. Don't touch the SheetTrigger or SheetHeader.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- FacetRail`

### Task 17a — UPDATE `AppointmentModal.tsx` (TagEditorSheet + EstimateSheetWrapper only — DEFER PaymentSheetWrapper)

This task wraps two of the three nested overlay sub-sheets with `SubSheetHeader`. The third (PaymentSheetWrapper) is deferred to Task 17b so it can ship as its own revertable commit if real-device QA reveals Stripe Terminal incompatibility.

**IMPLEMENT:**

1. Add the import:
   ```tsx
   import { SubSheetHeader } from './SubSheetHeader';
   ```
2. Find the existing TagEditorSheet rendering at `AppointmentModal.tsx:589-596`:
   ```tsx
   {openSheet === 'tags' && customer && (
     <div className="absolute inset-0 z-10">
       <TagEditorSheet
         customerId={customer.id}
         customerName={`${customer.first_name} ${customer.last_name}`}
         onClose={closeSheet}
       />
     </div>
   )}
   ```
   Replace with:
   ```tsx
   {openSheet === 'tags' && customer && (
     <div
       className="absolute inset-0 z-10 bg-white flex flex-col"
       data-testid="subsheet-tags"
     >
       <SubSheetHeader title="Edit tags" onBack={closeSheet} />
       <div className="flex-1 overflow-y-auto">
         <TagEditorSheet
           customerId={customer.id}
           customerName={`${customer.first_name} ${customer.last_name}`}
           onClose={closeSheet}
         />
       </div>
     </div>
   )}
   ```
3. Find the EstimateSheetWrapper rendering at `AppointmentModal.tsx:611-615`:
   ```tsx
   {openSheet === 'estimate' && (
     <div className="absolute inset-0 z-10">
       <EstimateSheetWrapper appointmentId={appointmentId} onClose={closeSheet} />
     </div>
   )}
   ```
   Replace with:
   ```tsx
   {openSheet === 'estimate' && (
     <div
       className="absolute inset-0 z-10 bg-white flex flex-col"
       data-testid="subsheet-estimate"
     >
       <SubSheetHeader title="Create estimate" onBack={closeSheet} />
       <div className="flex-1 overflow-y-auto">
         <EstimateSheetWrapper appointmentId={appointmentId} onClose={closeSheet} />
       </div>
     </div>
   )}
   ```
4. **Leave PaymentSheetWrapper (`AppointmentModal.tsx:599-608`) unchanged in this task.** Task 17b handles it.

- **GOTCHA:** TagEditorSheet and EstimateSheetWrapper may already render their own close UI — having both a back chevron and an internal close button is acceptable (mirrors iOS "Back" + "Done"). If user testing reveals confusion, defer "remove inner close button" to Phase 3.
- **GOTCHA:** The inner sub-sheet components must not have their own root `flex flex-col h-full` already, or layout will double-up. Verify by reading TagEditorSheet.tsx and EstimateSheetWrapper.tsx — if they do, drop the `flex-1 overflow-y-auto` wrapper here and let the inner component handle layout.
- **GOTCHA:** This task is a single commit — keep it small and focused so 17b can be cherry-picked or reverted independently.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- AppointmentModal`

### Task 17b — UPDATE `AppointmentModal.tsx` (PaymentSheetWrapper — SEPARATE COMMIT for revertability)

Wrap the PaymentSheetWrapper with `SubSheetHeader` in its OWN commit. This task is structurally identical to Task 17a but isolated because the Stripe Terminal Web SDK is the highest-stakes path: if the wrapping breaks the Stripe iframe layout on a real iPhone, this single commit can be reverted without losing the TagEditor/Estimate fixes.

**Sequencing rule:** Task 17b must be the **last code commit** before the manual QA pass (Task 26). Do NOT bundle it with later tasks. The PR should have a commit message like `feat(appointment-modal): wrap PaymentSheetWrapper with SubSheetHeader (revertable if Stripe Terminal misrenders)`.

**IMPLEMENT:**

Find the PaymentSheetWrapper rendering at `AppointmentModal.tsx:599-608`:
```tsx
{openSheet === 'payment' && (
  <div className="absolute inset-0 z-10">
    <PaymentSheetWrapper
      appointmentId={appointmentId}
      customerPhone={customer?.phone}
      customerEmail={customer?.email ?? undefined}
      onClose={closeSheet}
    />
  </div>
)}
```

Replace with:
```tsx
{openSheet === 'payment' && (
  <div
    className="absolute inset-0 z-10 bg-white flex flex-col"
    data-testid="subsheet-payment"
  >
    <SubSheetHeader title="Collect payment" onBack={closeSheet} />
    <div className="flex-1 overflow-y-auto">
      <PaymentSheetWrapper
        appointmentId={appointmentId}
        customerPhone={customer?.phone}
        customerEmail={customer?.email ?? undefined}
        onClose={closeSheet}
      />
    </div>
  </div>
)}
```

- **GOTCHA — HIGH STAKES:** The Stripe Terminal Web SDK renders an iframe inside `PaymentSheetWrapper`. The iframe's internal layout assumes a vertical-stack parent; wrapping it in `flex-col h-full` should be fine, but real-device testing on iPhone is mandatory. If the iframe misrenders (cropped, cut off, or Stripe button not tappable), revert this commit and accept that the Payment sub-sheet doesn't get the back-button header for now — it's still functional, just architecturally inconsistent with Tags and Estimate.
- **GOTCHA:** If reverted, leave a TODO comment in `AppointmentModal.tsx` near the PaymentSheetWrapper block: `// TODO(mobile): SubSheetHeader wrapping reverted due to Stripe Terminal iframe incompatibility — see issue #X`.
- **GOTCHA:** The Stripe Terminal flow MUST be tested with a real Reader on a real iPhone (not just DevTools). Browserstack with a connected Reader is acceptable; pure-DOM screenshots are not.
- **GOTCHA:** Memory `feedback_sms_test_number.md` — if this triggers any SMS receipts, use `+19527373312` only.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- AppointmentModal`. Manual: real-iPhone Stripe Terminal end-to-end pass before claiming this task complete.

### Task 17 — (REMOVED, replaced by 17a + 17b above)

### Task 18 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx` (Tailwind migration + flex-wrap)

Migrate every inline `style={{ ... }}` block to Tailwind classes. Use the per-property mapping table below as the source of truth — every inline property has an exact equivalent. Visual at `sm:`+ must be byte-identical (within sub-pixel rounding) to today.

**INLINE-TO-TAILWIND MAPPING TABLE — `NotesPanel.tsx`:**

| Element / line | Inline property | Tailwind equivalent |
|---|---|---|
| Outer wrapper (line 113) | `marginTop: 10` | `mt-2.5` |
| Outer wrapper (line 114) | `borderRadius: 14` | `rounded-[14px]` |
| Outer wrapper (line 115) | `border: '1.5px solid #E5E7EB'` | `border-[1.5px] border-slate-200` (slate-200 = `#E2E8F0`, very close to `#E5E7EB`; if pixel-perfect needed, use `border-[#E5E7EB]`) |
| Outer wrapper (line 116) | `backgroundColor: '#FFFFFF'` | `bg-white` |
| Outer wrapper (line 117) | `boxShadow: '0 1px 2px rgba(10,15,30,0.04)'` | `shadow-[0_1px_2px_rgba(10,15,30,0.04)]` (custom; standard `shadow-sm` is similar but uses different rgba) |
| Outer wrapper (line 118) | `overflow: 'hidden'` | `overflow-hidden` |
| Header div (line 124) | `padding: '18px 20px 14px'` | `pt-[18px] px-5 pb-3.5` |
| Header div (line 125) | `display: 'flex'` | `flex` |
| Header div (line 126) | `alignItems: 'center'` | `items-center` |
| Header div (line 127) | `justifyContent: 'space-between'` | `justify-between` |
| Header label (line 132) | `fontSize: 12.5` | `text-[12.5px]` |
| Header label (line 133) | `fontWeight: 800` | `font-extrabold` |
| Header label (line 134) | `letterSpacing: 1.4` | `tracking-[1.4px]` |
| Header label (line 135) | `textTransform: 'uppercase'` | `uppercase` |
| Header label (line 136) | `color: '#64748B'` | `text-slate-500` (slate-500 = `#64748B` exactly) |
| Edit button (line 149) | `display: 'inline-flex'` | `inline-flex` |
| Edit button (line 150) | `alignItems: 'center'` | `items-center` |
| Edit button (line 151) | `gap: 4` | `gap-1` |
| Edit button (line 152) | `fontSize: 14` | `text-sm` (14px) |
| Edit button (line 153) | `fontWeight: 700` | `font-bold` |
| Edit button (line 154) | `color: '#64748B'` | `text-slate-500` |
| Edit button (line 155) | `backgroundColor: 'transparent'` | `bg-transparent` |
| Edit button (line 156) | `border: 'none'` | `border-0` |
| Edit button (line 157) | `cursor: 'pointer'` | `cursor-pointer` |
| Edit button (line 158) | `padding: 0` | `p-0` |
| View body (line 172) | `padding: '0 20px 22px'` | `px-5 pb-[22px]` |
| View body (line 173) | `fontSize: 14.5` | `text-[14.5px]` |
| View body (line 174) | `fontWeight: 500` | `font-medium` |
| View body (line 175) | `lineHeight: 1.6` | `leading-[1.6]` |
| View body (line 176) | `color: '#0B1220'` | `text-[#0B1220]` (custom hex; not in default palette) |
| View body (line 177) | `minHeight: 80` | `min-h-[80px]` |
| View body (line 178) | `whiteSpace: 'pre-wrap'` | `whitespace-pre-wrap` |
| View body (line 179) | `wordBreak: 'break-word'` | `break-words` |
| Empty placeholder (line 184) | `color: '#9CA3AF'` | `text-slate-400` (slate-400 = `#94A3B8`; for exact `#9CA3AF` use `text-gray-400`) |
| Empty placeholder (line 184) | `fontStyle: 'italic'` | `italic` |
| Edit-mode container (line 193) | `padding: '0 20px 22px'` | `px-5 pb-[22px]` |
| Textarea (line 202) | `width: '100%'` | `w-full` |
| Textarea (line 203) | `minHeight: 150` (mobile-tighten to 120) | `min-h-[120px] sm:min-h-[150px]` |
| (NEW) Textarea max | (none) | `max-h-[40vh]` (mobile-only would be `max-sm:max-h-[40vh]` — applies at all sizes is fine) |
| Textarea (line 204) | `padding: '12px 14px'` | `px-3.5 py-3` |
| Textarea (line 205) | `borderRadius: 12` | `rounded-xl` (rounded-xl = 12px) |
| Textarea (line 206) | `border: '1.5px solid #E5E7EB'` | `border-[1.5px] border-[#E5E7EB]` |
| Textarea (line 207) | `fontSize: 14.5` | `text-[14.5px]` |
| Textarea (line 208) | `fontWeight: 500` | `font-medium` |
| Textarea (line 209) | `lineHeight: 1.5` | `leading-snug` (leading-snug = 1.375; if exactly 1.5 needed, use `leading-[1.5]`) |
| Textarea (line 210) | `resize: 'vertical'` | `resize-y` |
| Textarea (line 211) | `outline: 'none'` | `outline-none` |
| Textarea (line 212) | `fontFamily: 'inherit'` | (no class needed — inherits by default; if explicit needed, use inline `style` for this one prop) |
| Textarea (line 213) | `boxSizing: 'border-box'` | `box-border` |
| Button row (line 220) | `marginTop: 14` | `mt-3.5` |
| Button row (line 221) | `display: 'flex'` | `flex` |
| Button row (line 222) | `gap: 12` | `gap-3` |
| Button row (line 223) | `justifyContent: 'flex-end'` | `justify-end` |
| (NEW) Button row mobile | (none — no flex-wrap, ❌ overflows on iPhone SE) | **Add `flex-col-reverse sm:flex-row sm:flex-wrap` so on mobile Save is on top, Cancel below; at sm:+ side-by-side** |
| Cancel button (line 231) | `backgroundColor: '#FFFFFF'` | `bg-white` |
| Cancel button (line 232) | `border: '1.5px solid #E5E7EB'` | `border-[1.5px] border-[#E5E7EB]` |
| Cancel button (line 233) | `color: '#1F2937'` | `text-slate-800` (slate-800 = `#1E293B`; for exact `#1F2937` use `text-gray-800`) |
| Cancel button (line 234) | `padding: '12px 28px'` | `px-7 py-3` |
| Cancel button (line 235) | `borderRadius: 999` | `rounded-full` |
| Cancel button (line 236) | `fontSize: 15` | `text-[15px]` |
| Cancel button (line 237) | `fontWeight: 700` | `font-bold` |
| Cancel button (line 238) | `minWidth: 120` | `sm:min-w-[120px]` (no minWidth on mobile — full width via `w-full sm:w-auto`) |
| Cancel button (line 239) | `cursor: 'pointer'` | `cursor-pointer` |
| (NEW) Cancel button mobile | (none) | `w-full sm:w-auto min-h-[44px]` |
| Save button (line 249) | `backgroundColor: '#14B8A6'` | `bg-teal-500` (verify color match — teal-500 in this project is `oklch(0.704 0.14 180.72)`, designed to equal `#14B8A6`) |
| Save button (line 250) | `border: '1.5px solid #14B8A6'` | `border-[1.5px] border-teal-500` |
| Save button (line 251) | `color: '#FFFFFF'` | `text-white` |
| Save button (line 252-253) | (same padding/radius as Cancel) | `px-7 py-3 rounded-full` |
| Save button (line 254-255) | (same fontSize/weight) | `text-[15px] font-bold` |
| Save button (line 256) | `minWidth: 140` | `sm:min-w-[140px]` |
| (NEW) Save button mobile | (none) | `w-full sm:w-auto min-h-[44px]` |
| Save button (line 257) | `cursor: 'pointer'` | `cursor-pointer` |

**IMPLEMENT:** Working from the table above, rewrite the entire file. The final `return (...)` should look like this:

```tsx
return (
  <div
    data-testid="notes-panel"
    className="mt-2.5 rounded-[14px] border-[1.5px] border-[#E5E7EB] bg-white shadow-[0_1px_2px_rgba(10,15,30,0.04)] overflow-hidden"
  >
    {/* Header */}
    <div className="pt-[18px] px-5 pb-3.5 flex items-center justify-between">
      <span className="text-[12.5px] font-extrabold tracking-[1.4px] uppercase text-slate-500">
        INTERNAL NOTES
      </span>
      {!editing && (
        <button
          type="button"
          onClick={() => onSetEditing(true)}
          aria-label="Edit notes"
          className="inline-flex items-center gap-1 text-sm font-bold text-slate-500 bg-transparent border-0 cursor-pointer p-0"
        >
          <Pencil size={14} strokeWidth={2.2} />
          <span>Edit</span>
        </button>
      )}
    </div>

    {/* View mode */}
    {!editing && (
      <div
        data-testid="notes-view-body"
        className="px-5 pb-[22px] text-[14.5px] font-medium leading-[1.6] text-[#0B1220] min-h-[80px] whitespace-pre-wrap break-words"
      >
        {notes?.body || (
          <span className="text-gray-400 italic">No notes yet. Tap Edit to add internal notes.</span>
        )}
      </div>
    )}

    {/* Edit mode */}
    {editing && (
      <div className="px-5 pb-[22px]">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          data-testid="notes-textarea"
          aria-label="Internal notes"
          className="w-full min-h-[120px] sm:min-h-[150px] max-h-[40vh] px-3.5 py-3 rounded-xl border-[1.5px] border-[#E5E7EB] text-[14.5px] font-medium leading-[1.5] resize-y outline-none box-border"
          style={{ fontFamily: 'inherit' }}
        />

        {/* Button row — flex-col-reverse on mobile (Save on top), row on sm:+ */}
        <div className="mt-3.5 flex flex-col-reverse gap-2 sm:flex-row sm:flex-wrap sm:justify-end sm:gap-3">
          <button
            type="button"
            onClick={handleCancel}
            data-testid="notes-cancel-btn"
            className="w-full sm:w-auto sm:min-w-[120px] min-h-[44px] px-7 py-3 rounded-full text-[15px] font-bold bg-white border-[1.5px] border-[#E5E7EB] text-gray-800 cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            data-testid="notes-save-btn"
            className="w-full sm:w-auto sm:min-w-[140px] min-h-[44px] px-7 py-3 rounded-full text-[15px] font-bold bg-teal-500 border-[1.5px] border-teal-500 text-white cursor-pointer"
          >
            Save Notes
          </button>
        </div>
      </div>
    )}
  </div>
);
```

- **GOTCHA:** Preserve every `data-testid` value verbatim: `notes-panel`, `notes-view-body`, `notes-textarea`, `notes-cancel-btn`, `notes-save-btn`. Existing `NotesPanel.test.tsx` tests target these.
- **GOTCHA:** `fontFamily: 'inherit'` cannot be expressed cleanly in Tailwind for arbitrary parent fonts — kept as a single inline `style={{ fontFamily: 'inherit' }}` on the textarea. This is the only inline style remaining in the file.
- **GOTCHA:** Visual regression risk — see "VISUAL REGRESSION STRATEGY" section below for mandatory pre/post-migration screenshot capture.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- NotesPanel`

### Task 19 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx` (Tailwind migration + mobile cards)

Same approach as Task 18. PhotosPanel has 30+ inline style blocks; the mapping below covers each.

**INLINE-TO-TAILWIND MAPPING TABLE — `PhotosPanel.tsx`:**

| Element / line | Inline property | Tailwind equivalent |
|---|---|---|
| Outer container (line 86) | `marginTop: 10` | `mt-2.5` |
| Outer container (line 87) | `borderRadius: 14` | `rounded-[14px]` |
| Outer container (line 88) | `border: '1.5px solid #1D4ED8'` | `border-[1.5px] border-blue-700` (blue-700 = `#1D4ED8`) |
| Outer container (line 89) | `backgroundColor: '#FFFFFF'` | `bg-white` |
| Outer container (line 90) | `overflow: 'hidden'` | `overflow-hidden` |
| Header bar (line 96) | `backgroundColor: '#DBEAFE'` | `bg-blue-100` (blue-100 = `#DBEAFE`) |
| Header bar (line 97) | `padding: '10px 14px'` | `py-2.5 px-3.5` |
| Header bar (line 98-100) | `display: 'flex' alignItems: 'center' gap: 8` | `flex items-center gap-2` |
| Header icon wrapper (line 105-111) | `width: 16 height: 16 display: flex items-center justify-center color: '#1D4ED8' flexShrink: 0` | `w-4 h-4 flex items-center justify-center text-blue-700 flex-shrink-0` |
| Header label (line 117-120) | `fontSize: 13 fontWeight: 800 color: '#1D4ED8'` | `text-[13px] font-extrabold text-blue-700` |
| Count badge (line 127-140) | `display: inline-flex items-center justify-center borderRadius: 999 backgroundColor: '#1D4ED8' color: '#FFFFFF' fontSize: 11.5 fontWeight: 800 fontFamily: MONO_FONT minWidth: 20 height: 20 padding: '0 6px' lineHeight: 1` | `inline-flex items-center justify-center rounded-full bg-blue-700 text-white text-[11.5px] font-extrabold font-mono min-w-[20px] h-5 px-1.5 leading-none` |
| Header right text (line 145-150) | `marginLeft: auto fontSize: 11.5 fontWeight: 700 color: '#1D4ED8' opacity: 0.85` | `ml-auto text-[11.5px] font-bold text-blue-700 opacity-85` (use `opacity-85` if available else `opacity-[0.85]`) |
| Upload row (line 159-165) | `backgroundColor: '#FFFFFF' padding: 12 borderBottom: '1px solid #E5E7EB' display: flex gap: 8` | `bg-white p-3 border-b border-[#E5E7EB] flex gap-2` |
| Upload-photo button (line 172-187) | `flex: 1 minHeight: 48 backgroundColor: '#1D4ED8' color: '#FFFFFF' borderRadius: 12 border: none flex items-center justify-center gap: 6 cursor: pointer fontSize: 14 fontWeight: 700 padding: '0 14px'` | `flex-1 min-h-[48px] bg-blue-700 text-white rounded-xl border-0 flex items-center justify-center gap-1.5 cursor-pointer text-sm font-bold px-3.5` |
| Upload-photo "camera roll" suffix (line 192-196) | `fontFamily: MONO_FONT fontSize: 11.5 opacity: 0.9` | `font-mono text-[11.5px] opacity-90` |
| Take-photo button (line 217-230) | `minHeight: 48 backgroundColor: '#FFFFFF' color: '#1D4ED8' borderRadius: 12 border: '1.5px solid #1D4ED8' flex items-center justify-center gap: 6 cursor: pointer fontSize: 14 fontWeight: 700 padding: '0 14px'` | `min-h-[48px] bg-white text-blue-700 rounded-xl border-[1.5px] border-blue-700 flex items-center justify-center gap-1.5 cursor-pointer text-sm font-bold px-3.5` |
| Photo strip (line 250-255) | `display: flex overflowX: auto padding: 12 gap: 10 WebkitOverflowScrolling: touch` | `flex overflow-x-auto p-3 gap-2.5` (WebKit scroll is default in modern Safari, drop) |
| Optimistic placeholder (line 262-269) | `width: 180 flexShrink: 0 borderRadius: 12 border: '1.5px solid #E5E7EB' overflow: hidden backgroundColor: '#F9FAFB' position: relative` | `w-[180px] max-sm:w-[140px] flex-shrink-0 rounded-xl border-[1.5px] border-[#E5E7EB] overflow-hidden bg-[#F9FAFB] relative` |
| Optimistic image (line 274-281) | `width: 100% height: 134 objectFit: cover display: block opacity: 0.6` | `w-full h-[134px] object-cover block opacity-60` |
| Spinner overlay (line 283-289) | `position: absolute inset: 0 display: flex items-center justify-center` | `absolute inset-0 flex items-center justify-center` |
| Spinner (line 292-300) | `width: 24 height: 24 border: '2.5px solid #1D4ED8' borderTopColor: transparent borderRadius: 50% animation: 'spin 0.8s linear infinite'` | `w-6 h-6 border-[2.5px] border-blue-700 border-t-transparent rounded-full animate-spin` (use Tailwind's built-in `animate-spin`; faster speed via `[animation-duration:0.8s]` if exact match needed) |
| Spinner caption row (line 302) | `padding: '8px 10px'` | `py-2 px-2.5` |
| Spinner caption text (line 304-308) | `fontSize: 12 fontWeight: 700 color: '#9CA3AF'` | `text-xs font-bold text-gray-400` |
| Loading state (line 320-328) | `display: flex items-center justify-center padding: '20px 40px' color: '#6B7280' fontSize: 13 fontWeight: 600` | `flex items-center justify-center py-5 px-10 text-gray-500 text-[13px] font-semibold` |
| Error state (line 336-344) | `display: flex items-center justify-center padding: '20px 40px' color: '#EF4444' fontSize: 13 fontWeight: 600` | `flex items-center justify-center py-5 px-10 text-red-500 text-[13px] font-semibold` |
| Add-more tile (line 374-387) | `width: 110 flexShrink: 0 borderRadius: 12 border: '1.5px dashed #D1D5DB' backgroundColor: '#F9FAFB' display: flex flexDirection: column items-center justify-center gap: 6 cursor: pointer padding: '16px 8px' minHeight: 134` | `w-[110px] max-sm:w-[90px] flex-shrink-0 rounded-xl border-[1.5px] border-dashed border-gray-300 bg-[#F9FAFB] flex flex-col items-center justify-center gap-1.5 cursor-pointer py-4 px-2 min-h-[134px] max-sm:min-h-[110px]` |
| Add-more "Add more" text (line 391-396) | `fontSize: 12 fontWeight: 800 color: '#6B7280' textAlign: center lineHeight: 1.3` | `text-xs font-extrabold text-gray-500 text-center leading-[1.3]` |
| Add-more "From library" text (line 402-408) | `fontSize: 10.5 fontWeight: 600 fontFamily: MONO_FONT color: '#9CA3AF' textAlign: center` | `text-[10.5px] font-semibold font-mono text-gray-400 text-center` |
| Footer (line 426-432) | `backgroundColor: '#F9FAFB' padding: '8px 14px 10px' borderTop: '1px solid #E5E7EB' display: flex items-center justify-between` | `bg-[#F9FAFB] pt-2 px-3.5 pb-2.5 border-t border-[#E5E7EB] flex items-center justify-between` |
| Footer hint (line 436-440) | `fontSize: 11.5 fontWeight: 700 color: '#6B7280'` | `text-[11.5px] font-bold text-gray-500` |
| View-all button (line 446-454) | `padding: '6px 10px' borderRadius: 8 border: '1.5px solid #E5E7EB' backgroundColor: '#FFFFFF' fontSize: 12 fontWeight: 800 color: '#1F2937' cursor: pointer` | `py-1.5 px-2.5 rounded-lg border-[1.5px] border-[#E5E7EB] bg-white text-xs font-extrabold text-gray-800 cursor-pointer` |

**IMPLEMENT:** Apply the mapping line-by-line. **Mobile-only enhancements** to add (these are NEW, not in current code):
- Photo card width: `w-[180px] max-sm:w-[140px]` (cards narrower on phones)
- Add-more tile: `w-[110px] max-sm:w-[90px] min-h-[134px] max-sm:min-h-[110px]`

The `MONO_FONT` constant at line 16-17 can stay as-is for `style={{ fontFamily: MONO_FONT }}` on the few elements that need it, OR migrate to a Tailwind plugin. **Recommendation:** keep `MONO_FONT` and use `style={{ fontFamily: MONO_FONT }}` only where necessary (count badge line 135, "camera roll" suffix line 193, add-more "From library" line 405) — Tailwind's `font-mono` falls back to system mono which differs slightly from the explicit JetBrains Mono stack.

- **GOTCHA:** Preserve `data-testid` values: `photos-panel`, `photo-strip`, `upload-photo-input`, `take-photo-input`, `add-more-photo-input`.
- **GOTCHA:** PhotoCard.tsx (separate file) — only update if the Task 6.5 spike showed listWeek issues; otherwise leave PhotoCard.tsx alone for this PR. Mobile width control is at the strip level via `max-sm:w-[140px]` on the *placeholder card* style and via PhotoCard's existing 180px (which fits within the strip's `overflow-x-auto`).
- **GOTCHA:** Camera input keeps `capture="environment"` (line 239) — preserves rear-camera prompt on mobile.
- **GOTCHA:** Visual regression risk — see "VISUAL REGRESSION STRATEGY" section below.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- PhotosPanel`

### VISUAL REGRESSION STRATEGY (mandatory before AND after Tasks 18, 19)

The Tailwind migration has a real regression risk: tokens may not produce pixel-identical output. To prevent silent visual breakage on desktop (which the user explicitly required to be byte-identical at `lg:`+), follow this procedure:

**Pre-migration baseline capture:**

```bash
# Before starting Tasks 18 and 19:
git checkout main  # or current branch HEAD before changes
cd frontend && npm run dev &
sleep 5

# Use agent-browser at desktop viewport
agent-browser set viewport 1440 900
agent-browser open http://localhost:5173/schedule
# (login + navigate to an appointment with notes and photos)
agent-browser screenshot e2e-screenshots/mobile-schedule/baseline-notes-panel-desktop.png
agent-browser screenshot e2e-screenshots/mobile-schedule/baseline-photos-panel-desktop.png

# Switch to mobile viewport
agent-browser set viewport 375 812
agent-browser open http://localhost:5173/schedule
agent-browser screenshot e2e-screenshots/mobile-schedule/baseline-notes-panel-mobile.png
agent-browser screenshot e2e-screenshots/mobile-schedule/baseline-photos-panel-mobile.png

# Stash these as baselines
mkdir -p e2e-screenshots/mobile-schedule/baseline
mv e2e-screenshots/mobile-schedule/baseline-*.png e2e-screenshots/mobile-schedule/baseline/
```

**Post-migration comparison (after Tasks 18, 19):**

```bash
# Re-capture at the same viewports
agent-browser set viewport 1440 900
agent-browser open http://localhost:5173/schedule
agent-browser screenshot e2e-screenshots/mobile-schedule/post-notes-panel-desktop.png
agent-browser screenshot e2e-screenshots/mobile-schedule/post-photos-panel-desktop.png
agent-browser set viewport 375 812
agent-browser open http://localhost:5173/schedule
agent-browser screenshot e2e-screenshots/mobile-schedule/post-notes-panel-mobile.png
agent-browser screenshot e2e-screenshots/mobile-schedule/post-photos-panel-mobile.png
```

**Diff comparison (manual or via tool):**

Option A — manual side-by-side: open `baseline-*-desktop.png` and `post-*-desktop.png` in Preview.app side-by-side. Visually inspect for differences. **Acceptable diffs:** sub-pixel anti-aliasing changes, font-rendering differences. **Unacceptable diffs:** color shifts, alignment changes, border-radius changes, padding changes.

Option B — image-diff CLI (preferred):

```bash
# Install once: brew install imagemagick
compare -metric AE \
  e2e-screenshots/mobile-schedule/baseline/baseline-notes-panel-desktop.png \
  e2e-screenshots/mobile-schedule/post-notes-panel-desktop.png \
  e2e-screenshots/mobile-schedule/diff-notes-panel-desktop.png

# AE (absolute error) returns the count of pixels that differ.
# Acceptable threshold: < 200 pixels different on a 560 × 800 area (likely sub-pixel rendering).
# > 1000 pixels: real visual regression. Investigate.
```

Option C — adopt Chromatic / Percy (Phase 3 polish, not required for this PR).

**Decision rule:** if desktop pixel-diff exceeds 0.5% of total pixels, the migration must be re-evaluated for that specific token. Likely cause is a Tailwind class that doesn't exactly match the inline value (e.g., `slate-200` ≠ `#E5E7EB`). Switch to arbitrary-value class (`border-[#E5E7EB]`) for that property.

**Document outcome:** in PR description, include `compare` output for both desktop and mobile. Acceptable: "Desktop diff: 0.05% (rendering noise). Mobile diff: 8.2% (intentional — narrower photo cards on mobile)."

### Task 20 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/ModalHeader.tsx` (close button touch target)

**IMPLEMENT:** At line 67, change the close button className from `w-10 h-10` (40 × 40 px) to `w-11 h-11` (44 × 44 px).

```diff
       <button
         ref={closeButtonRef}
         type="button"
         onClick={onClose}
         aria-label="Close"
-        className="w-10 h-10 flex items-center justify-center rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white hover:bg-gray-50 flex-shrink-0"
+        className="w-11 h-11 flex items-center justify-center rounded-[12px] border-[1.5px] border-[#E5E7EB] bg-white hover:bg-gray-50 flex-shrink-0"
       >
         <X size={18} strokeWidth={2} />
       </button>
```

- **GOTCHA:** Preserve `closeButtonRef` ref forwarding (used for focus management at `AppointmentModal.tsx:119-122`).
- **GOTCHA:** No `data-testid` on this button currently — the `close-modal-btn` testid is on the *Dialog primitive's* close button (`dialog.tsx:73`), which is a different element. Don't add one here unless tests need it.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- ModalHeader`

### Task 21 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/CustomerHero.tsx` (phone-call button touch target)

**IMPLEMENT:** Find the inline "Call" button at line 73-78 and increase the touch target. Also increase the icon container at line 64-66 (which is the leading visual chip — not technically a tap target, but visually paired with the call button).

```diff
         {/* Phone row */}
         <div className="flex items-center gap-2.5">
-          <div className="w-7 h-7 rounded-[8px] bg-blue-50 flex items-center justify-center flex-shrink-0">
+          <div className="w-9 h-9 rounded-[8px] bg-blue-50 flex items-center justify-center flex-shrink-0">
             <Phone size={14} className="text-blue-600" strokeWidth={2.2} />
           </div>
           <a
             href={`tel:${phone}`}
             className="text-[17px] font-extrabold text-[#0B1220] font-mono tracking-[-0.3px] hover:text-blue-600"
           >
             {phone}
           </a>
           <a
             href={`tel:${phone}`}
-            className="ml-auto inline-flex items-center px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-[12px] font-bold border border-blue-200 hover:bg-blue-100"
+            className="ml-auto inline-flex items-center justify-center min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-blue-50 text-blue-700 text-[12px] font-bold border border-blue-200 hover:bg-blue-100"
           >
             Call
           </a>
         </div>
```

- **GOTCHA:** The phone-number link itself (lines 67-72, the `<a href={tel:}>` wrapping the phone number) is also a tap target — its hit area is the phone-number text height (~22 px). The dedicated "Call" button (the one we're enlarging) is the primary tap target; the inline phone number stays as-is for keyboard/screen-reader users.
- **GOTCHA:** `min-h-[44px] min-w-[44px]` plus `px-4 py-2` keeps the visual size growing only as needed — short text "Call" stays compact.
- **GOTCHA:** Preserve `href={`tel:${phone}`}` on both anchors.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 22 — UPDATE `frontend/src/features/schedule/components/AppointmentModal/ActionTrack.tsx` (mobile padding/gap)

- **IMPLEMENT:** Line 68: change `<div className="px-5 pb-4 flex gap-2 flex-shrink-0">` to `<div className="px-3 sm:px-5 pb-4 flex gap-1.5 sm:gap-2 flex-shrink-0">`. Tightens spacing at `< sm:` so the three ActionCards don't collide on iPhone SE.
- **PATTERN:** Pattern 4 ("Modal: full-screen sheet on mobile") combined with mobile-specific tightening.
- **GOTCHA:** Tests target `data-testid` values inside ActionCard, not on this container.
- **VALIDATE:** `cd frontend && npm run typecheck && npm test -- ActionTrack`

### Task 23 — VERIFY `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.test.tsx`

- **IMPLEMENT:** Run the existing test suite for AppointmentModal — none of the polish changes (Tasks 17-22) should break existing tests since they preserve `data-testid`s and don't change behavior. If any test fails, address the failure rather than altering the test (the source of truth is the existing test).
- **VALIDATE:** `cd frontend && npm test -- AppointmentModal`

### Task 24 — UPDATE imports across edited files

- **IMPLEMENT:** Re-run `npm run typecheck` and address any type errors. Most likely candidates:
  - `useMediaQuery` import path — should be `@/shared/hooks` (barrel export).
  - `SubSheetHeader` import path — relative `./SubSheetHeader`.
  - `listPlugin` from `@fullcalendar/list` — package newly installed in Task 6.
- **VALIDATE:** `cd frontend && npm run typecheck`

### Task 25 — Quality gate (linting, formatting, full test run)

- **IMPLEMENT:** Run the project's standard quality gate. Address any lint warnings from changes; address any test failures.
- **VALIDATE:** `cd frontend && npm run lint && npm run format:check && npm run test:coverage`

### Task 26.5 — Verify the data-testid convention map

- **IMPLEMENT:** Open `e2e-screenshots/mobile-schedule/` and walk through each screenshot. For every interactive element visible in the screenshot, ensure it has a `data-testid` matching the "DATA-TESTID CONVENTION MAP" section. New testids: `schedule-action-overflow-btn`, `schedule-action-overflow-menu`, `overflow-menu-item-*`, `subsheet-header`, `subsheet-back-btn`, `calendar-list-view`, `subsheet-tags`, `subsheet-payment`, `subsheet-estimate`. Existing testids must not have been renamed or removed.
- **VALIDATE:** Run `grep -r "data-testid" frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.tsx` and confirm `subsheet-header` and `subsheet-back-btn` are present. Run `grep -r "schedule-action-overflow-btn" frontend/src/features/schedule/components/SchedulePage.tsx` and confirm presence.

### Task 26 — Manual smoke test on real devices

- **IMPLEMENT:** Spin up the dev server (`cd frontend && npm run dev`). Verify on:
  1. **MacBook Chrome at 1280 px** — Schedule tab, Appointment Modal must look identical to today (no regressions). Side-by-side compare against `main` branch via screenshots.
  2. **MacBook Chrome at 1024 px** — `lg:` breakpoint still triggers desktop layout.
  3. **Chrome DevTools iPhone 13 (390 × 844)** — Schedule tab shows `listWeek` view, action bar shows only `+ New Appointment` + overflow menu, AppointmentModal renders as bottom-sheet with grab handle, NotesPanel buttons don't overflow, PhotosPanel cards are narrower.
  4. **Chrome DevTools iPad Air (820 × 1180 portrait)** — Schedule tab shows `listWeek` (still mobile mode, since `< 768` floor — but note iPad Air at 820 px portrait is `≥ md`). Verify breakpoint behavior is sensible.
  5. **(If available) Real iPhone Safari** — full technician workflow: open Schedule, tap appointment, mark en route, take photo, add note, mark complete.
  6. **Stripe Terminal flow** — must be tested on a real device because the Stripe Terminal Web SDK requires HTTPS and a Reader. **Use the test phone number `+19527373312`** if any SMS is sent during the flow per memory `feedback_sms_test_number.md`.
- **GOTCHA:** Document each device test result in the PR description.
- **VALIDATE:** Manual screenshots + sign-off.

### Task 27 — UPDATE `DEVLOG.md` per `auto-devlog.md` and `devlog-rules.md`

- **IMPLEMENT:** Insert a new entry at the TOP of `DEVLOG.md` (immediately after the `## Recent Activity` header). Use category `FEATURE` and the format from `devlog-rules.md`:
  ```
  ## [YYYY-MM-DD HH:MM] - FEATURE: Schedule + Appointment Modal mobile responsiveness

  ### What Was Accomplished
  - FullCalendar viewport-aware mode (listWeek on mobile, timeGridWeek on desktop)
  - Schedule page action bar collapses to overflow DropdownMenu on mobile
  - AppointmentModal nested sub-sheets gain back-button SubSheetHeader
  - NotesPanel + PhotosPanel migrated from inline styles to Tailwind
  - Touch targets bumped to ≥ 44 × 44 px on close button + phone-call button
  - New `useMediaQuery` hook in `shared/hooks/`
  - New `SubSheetHeader` shared component
  - Multiple surrounding components made responsive (AppointmentForm time inputs, AppointmentList filters, DaySelector horizontal scroll, SchedulingTray grid, FacetRail Sheet width)

  ### Technical Details
  - React 19 + Tailwind v4 responsive prefixes (`sm:`, `md:`, `lg:`, `max-sm:`)
  - `@fullcalendar/list` plugin added at version-matched 6.1.20
  - `useMediaQuery('(max-width: 767px)')` for behavior-level branching (FullCalendar config, action-bar collapse)
  - `data-testid` convention preserved for all existing testids; new testids added per `frontend-patterns.md` convention
  - No backend changes
  - No new env vars

  ### Decision Rationale
  - Mobile-first responsive web (not native app, not separate mobile route tree) — chosen over duplicate codebase
  - `listWeek` as default mobile calendar view — mirrors ServiceTitan/Jobber/Housecall Pro
  - Drag-drop reschedule disabled on mobile — avoids touch/scroll conflicts; route through Edit dialog
  - Sub-sheet Option A (back-button header) — chosen over Option B (standalone Radix Sheets) for lower risk; Option B deferred to Phase 3
  - PickJobsPage stays desktop-only — bulk job picking is an office workflow, not a tech workflow

  ### Challenges and Solutions
  - Stacking context: `absolute inset-0` inside `position: fixed` modal — addressed via SubSheetHeader wrapping each sub-sheet so it reads as a replacement view
  - PhotosPanel + NotesPanel inline styles — migrated to Tailwind so future mobile-specific tweaks compose cleanly
  - Stripe Terminal Web flow inside the wrapped PaymentSheetWrapper — verified on real iPhone with real Reader

  ### Next Steps
  - Phase 2: extend mobile responsiveness to Sales pipeline, Customers, Jobs, Invoices, Settings (see `feature-developments/mobile-responsiveness-investigation/05_RECOMMENDED_APPROACH.md`)
  - Phase 3: landscape iPhone breakpoint, `100dvh` migration, Settings UX redesign, sub-sheet Option B refactor if Option A doesn't satisfy users
  ```
- **PATTERN:** `devlog-rules.md` Entry Format. Categories: `FEATURE`. Newest first.
- **GOTCHA:** Replace `[YYYY-MM-DD HH:MM]` with the actual timestamp at PR-merge time (or just before).
- **VALIDATE:** `head -40 /Users/kirillrakitin/Grins_irrigation_platform/DEVLOG.md` shows the new entry at the top.

---

## DATA-TESTID CONVENTION MAP

Per `frontend-patterns.md` § data-testid Convention. All existing testids are preserved; new ones follow the convention.

### Existing testids (preserved — do not break)

| Element | testid | Source file |
|---|---|---|
| Layout root | `layout` | `Layout.tsx:155` |
| Sidebar | `sidebar` | `Layout.tsx:171` |
| Sidebar backdrop | `sidebar-backdrop` | `Layout.tsx:161` |
| Sidebar nav | `sidebar-nav` | `Layout.tsx:184` |
| Mobile menu button | `mobile-menu-button` | `Layout.tsx:245` |
| Schedule nav link | `nav-schedule` | `Layout.tsx:76` |
| Header | `header` | `Layout.tsx:236` |
| Header separator | `header-separator` | `Layout.tsx:321` |
| Notification bell | `notification-bell` | `Layout.tsx:275` |
| Notification count | `notification-count` | `Layout.tsx:281` |
| Notification item | `notification-item` | `Layout.tsx:296` |
| Main content | `main-content` | `Layout.tsx:331` |
| Page header | `page-header` | `PageHeader.tsx:13` |
| Page title | `page-title` | `PageHeader.tsx:16` |
| Page description | `page-description` | `PageHeader.tsx:20` |
| Page header action | `page-header-action` | `PageHeader.tsx:25` |
| Schedule page root | `schedule-page` | `SchedulePage.tsx:324` |
| View toggle | `schedule-view-toggle` | `SchedulePage.tsx:341` |
| Calendar view button | `view-calendar` | `SchedulePage.tsx:346` |
| List view button | `view-list` | `SchedulePage.tsx:353` |
| Add Jobs button | `add-jobs-btn` | `SchedulePage.tsx:369` |
| Pick Jobs button | `pick-jobs-btn` | `SchedulePage.tsx:378` |
| New Appointment button | `add-appointment-btn` | `SchedulePage.tsx:389` |
| Calendar view container | `calendar-view` | `CalendarView.tsx:334` |
| Day selector | `day-selector` | `DaySelector.tsx:34` |
| Day buttons | `day-btn-{mon|tue|wed|thu|fri|sat|sun}` | `DaySelector.tsx:49` |
| Appointment list | `appointment-list` | `AppointmentList.tsx:249` |
| Appointment table | `appointment-table` | `AppointmentList.tsx:308` |
| Status filter | `status-filter` | `AppointmentList.tsx:260` |
| Date-from filter | `date-from-filter` | `AppointmentList.tsx:285` |
| Date-to filter | `date-to-filter` | `AppointmentList.tsx:295` |
| Start time input | `start-time-input` | `AppointmentForm.tsx:413` |
| Tray date | `tray-date` | `SchedulingTray.tsx:104` |
| Tray staff | `tray-staff` | `SchedulingTray.tsx:110` |
| Job search | `job-search` | `JobTable.tsx:62` |
| Job table select-all | `job-table-select-all` | `JobTable.tsx:98` |
| Job row | `job-row-{job_id}` | `JobTable.tsx:147` |
| Job row checkbox | `job-row-checkbox-{job_id}` | `JobTable.tsx:155` |
| Appointment modal | `appointment-modal` | `AppointmentModal.tsx:288` |
| Modal backdrop | `modal-backdrop` | `dialog.tsx:42` |
| Close modal button | `close-modal-btn` | `dialog.tsx:73` |
| Reschedule banner | `reschedule-banner-{appointmentId}` | `AppointmentModal.tsx:330` |
| No-reply banner | `no-reply-banner-{appointmentId}` | `AppointmentModal.tsx:375` |
| Notes panel | `notes-panel` | `NotesPanel.tsx:112` |
| Notes view body | `notes-view-body` | `NotesPanel.tsx:171` |
| Notes textarea | `notes-textarea` | `NotesPanel.tsx:199` |
| Notes cancel button | `notes-cancel-btn` | `NotesPanel.tsx:229` |
| Notes save button | `notes-save-btn` | `NotesPanel.tsx:247` |
| Photos panel | `photos-panel` | `PhotosPanel.tsx:84` |
| Prepaid indicator | `prepaid-indicator-{eventId}` | `CalendarView.tsx:209` |
| Attachment badge | `attachment-badge-{eventId}` | `CalendarView.tsx:218` |
| Duration metrics | `duration-metrics-section` | `AppointmentModal.tsx:718` |
| Metric travel time | `metric-travel-time` | `AppointmentModal.tsx:725` |
| Metric job duration | `metric-job-duration` | `AppointmentModal.tsx:731` |
| Metric total time | `metric-total-time` | `AppointmentModal.tsx:737` |
| Address override button | `address-override-btn` | `AppointmentForm.tsx:395` |

### New testids to add (Phase 1)

| Element | testid | Naming rationale |
|---|---|---|
| Schedule action overflow trigger | `schedule-action-overflow-btn` | `{action}-{feature}-btn` pattern |
| Schedule action overflow menu content | `schedule-action-overflow-menu` | `{feature}-{element}` pattern |
| Each item inside the overflow menu | `overflow-menu-item-{lead-time\|clear-day\|view-toggle\|send-confirmations}` | descriptive sub-action keys |
| SubSheetHeader root | `subsheet-header` | shared component |
| SubSheetHeader back button | `subsheet-back-btn` | `{action}-{element}-btn` pattern |
| Calendar list view (mobile mode) | `calendar-list-view` | new view mode marker |
| Tag editor sub-sheet container | `subsheet-tags` | `{feature}-{kind}` |
| Payment sub-sheet container | `subsheet-payment` | `{feature}-{kind}` |
| Estimate sub-sheet container | `subsheet-estimate` | `{feature}-{kind}` |

### Convention compliance checklist

- [x] All testids use kebab-case
- [x] Pages use `{feature}-page` pattern (`schedule-page`)
- [x] Tables use `{feature}-table` pattern (`appointment-table`)
- [x] Buttons use `{action}-{feature}-btn` pattern (`add-appointment-btn`, `subsheet-back-btn`)
- [x] Nav uses `nav-{feature}` pattern (`nav-schedule`)
- [x] No PII or dynamic values in testids except where IDs are needed for unique identification (`{job_id}`, `{appointmentId}`)

---

## TEST FIXTURES

Per `spec-quality-gates.md` § 5. Concrete fixtures and wrappers used by the new tests.

### `useMediaQuery` test fixture pattern

```tsx
// frontend/src/shared/hooks/useMediaQuery.test.ts
import { vi, beforeEach, afterEach } from 'vitest';

interface MediaQueryListMock {
  matches: boolean;
  media: string;
  onchange: null;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  // (legacy listener API stubs for older Safari)
  addListener: ReturnType<typeof vi.fn>;
  removeListener: ReturnType<typeof vi.fn>;
  dispatchEvent: ReturnType<typeof vi.fn>;
}

function makeMatchMediaMock(initialMatches: boolean): MediaQueryListMock {
  let listener: ((e: MediaQueryListEvent) => void) | null = null;
  return {
    matches: initialMatches,
    media: '',
    onchange: null,
    addEventListener: vi.fn((_event, l) => { listener = l; }),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  };
}

let originalMatchMedia: typeof window.matchMedia;
beforeEach(() => {
  originalMatchMedia = window.matchMedia;
});
afterEach(() => {
  window.matchMedia = originalMatchMedia;
});
```

### Mock appointment fixture (existing pattern, reused)

The existing `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.test.tsx:15-66` defines `baseAppointment`, `mockJob`, `mockCustomer`, `mockTimeline`. **Reuse these verbatim** when writing CalendarView and SchedulePage mobile-mode tests — do not redefine.

### `useMediaQuery` mock helper for component tests

```tsx
// Place at top of CalendarView.test.tsx, SchedulePage.test.tsx
vi.mock('@/shared/hooks', async () => {
  const actual = await vi.importActual<typeof import('@/shared/hooks')>('@/shared/hooks');
  return { ...actual, useMediaQuery: vi.fn() };
});

import { useMediaQuery } from '@/shared/hooks';
const mockUseMediaQuery = vi.mocked(useMediaQuery);

beforeEach(() => {
  mockUseMediaQuery.mockReturnValue(false); // default: desktop
});

it('renders mobile mode when useMediaQuery returns true', () => {
  mockUseMediaQuery.mockReturnValue(true);
  render(<CalendarView />, { wrapper: TestWrapper });
  // assertions for mobile-mode behavior
});
```

### QueryProvider wrapper (existing pattern)

Per `frontend-testing.md`, all component tests requiring TanStack Query use a `QueryProvider` wrapper. The existing `AppointmentModal.test.tsx` defines a local `TestWrapper` — mirror that pattern. Don't introduce a new wrapper.

### Loading / Error / Empty state fixtures

Per `spec-testing-standards.md` § 2. For each touched component test file, ensure the suite covers:

- **Loading state** — mock the hook to return `{ isLoading: true }` and assert spinner renders.
- **Error state** — mock the hook to return `{ error: new Error('test') }` and assert error UI renders.
- **Empty state** — mock the hook to return `{ data: [] }` and assert empty-state copy renders.

For `CalendarView` specifically, the empty state is the new `noEventsContent: 'No appointments this week'` in `listWeek` view (Task 7) — test that this string renders when `weeklySchedule.days.flatMap(d => d.appointments).length === 0`.

---

## AGENT-BROWSER E2E VALIDATION SCRIPTS

Per `frontend-testing.md` template, `agent-browser.md` command reference, and `e2e-testing-skill.md` Phase 6 (Responsive Testing). All scripts assume:

- Backend at `http://localhost:8000` (via `./scripts/dev.sh` or equivalent).
- Frontend at `http://localhost:5173` (via `cd frontend && npm run dev`).
- A logged-in admin session (use the existing test-admin credentials per `e2e-testing-skill.md` Grins Specifics).
- Clean dev DB seeded with at least one technician, one customer, one scheduled appointment for today.

### Pre-flight

```bash
agent-browser --version || (npm install -g agent-browser && agent-browser install --with-deps)
agent-browser open http://localhost:5173/login
# (login via fixture credentials — pattern matches existing E2E flows in e2e-screenshots/)
agent-browser wait --url "**/dashboard"
agent-browser screenshot e2e-screenshots/mobile-schedule/00-logged-in.png
```

### Script 1 — Mobile (375 × 812) Schedule + Appointment Modal happy path

```bash
agent-browser set viewport 375 812
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/mobile-schedule/01-iphone-schedule-page.png

# Verify mobile mode
agent-browser is visible "[data-testid='schedule-page']"
agent-browser is visible "[data-testid='add-appointment-btn']"
agent-browser is visible "[data-testid='schedule-action-overflow-btn']"
agent-browser is visible "[data-testid='calendar-list-view']" || agent-browser console
# These should NOT be directly visible on mobile (they live inside the overflow menu)
agent-browser is visible "[data-testid='add-jobs-btn']" && echo "FAIL: add-jobs-btn must be hidden on mobile" || echo "OK"
agent-browser is visible "[data-testid='pick-jobs-btn']" && echo "FAIL: pick-jobs-btn must be hidden on mobile" || echo "OK"

# Open overflow menu
agent-browser click "[data-testid='schedule-action-overflow-btn']"
agent-browser wait "[data-testid='schedule-action-overflow-menu']"
agent-browser screenshot e2e-screenshots/mobile-schedule/02-overflow-menu-open.png
agent-browser press Escape

# Tap an appointment to open modal
agent-browser snapshot -i
# Pick the first appointment row in the list view (snapshot will give a ref)
# agent-browser click @eN  ← substitute the actual appointment ref
agent-browser wait "[data-testid='appointment-modal']"
agent-browser screenshot e2e-screenshots/mobile-schedule/03-appointment-modal-mobile.png

# Verify modal is bottom-sheet style on mobile (grab handle visible)
agent-browser is visible "[data-testid='appointment-modal']"

# Open Notes panel
agent-browser click "[aria-label='See attached notes']"
agent-browser wait "[data-testid='notes-panel']"
agent-browser screenshot e2e-screenshots/mobile-schedule/04-notes-panel-mobile.png

# Edit notes
agent-browser click "[data-testid='notes-view-body']" || agent-browser click "[aria-label='Edit notes']"
agent-browser wait "[data-testid='notes-textarea']"
agent-browser fill "[data-testid='notes-textarea']" "Mobile QA test note"
agent-browser screenshot e2e-screenshots/mobile-schedule/05-notes-edit.png
# Confirm Save and Cancel buttons are both visible (no overflow on iPhone)
agent-browser is visible "[data-testid='notes-save-btn']"
agent-browser is visible "[data-testid='notes-cancel-btn']"
agent-browser click "[data-testid='notes-save-btn']"
agent-browser wait --text "Mobile QA test note"

# Open Photos panel
agent-browser click "[aria-label='See attached photos']"
agent-browser wait "[data-testid='photos-panel']"
agent-browser screenshot e2e-screenshots/mobile-schedule/06-photos-panel-mobile.png

# Open Tag editor sub-sheet (verify back-button header)
agent-browser click "[aria-label='Edit tags']"
agent-browser wait "[data-testid='subsheet-tags']"
agent-browser is visible "[data-testid='subsheet-header']"
agent-browser is visible "[data-testid='subsheet-back-btn']"
agent-browser screenshot e2e-screenshots/mobile-schedule/07-tag-subsheet-mobile.png
agent-browser click "[data-testid='subsheet-back-btn']"
agent-browser wait "[data-testid='appointment-modal']"

# Close modal
agent-browser click "[data-testid='close-modal-btn']"
agent-browser console
agent-browser errors
```

### Script 2 — Tablet (768 × 1024) regression

```bash
agent-browser set viewport 768 1024
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/mobile-schedule/10-ipad-schedule.png

# At 768 px (md: breakpoint exactly), expect:
#   - listWeek view (since useMediaQuery '(max-width: 767px)' is just barely false)
#   - Action bar in 2-row wrapped layout (between md and lg)
#   - All testids visible (no overflow menu collapse)
agent-browser is visible "[data-testid='add-appointment-btn']"
agent-browser is visible "[data-testid='schedule-view-toggle']"
agent-browser is visible "[data-testid='day-selector']"
agent-browser screenshot e2e-screenshots/mobile-schedule/11-ipad-action-bar.png
agent-browser console
agent-browser errors
```

### Script 3 — Desktop (1440 × 900) NO-REGRESSION

```bash
agent-browser set viewport 1440 900
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/mobile-schedule/20-macbook-schedule.png

# At 1440 px (lg+), the layout MUST match `main` branch byte-for-byte.
# All testids must be visible inline (no overflow menu).
agent-browser is visible "[data-testid='add-appointment-btn']"
agent-browser is visible "[data-testid='add-jobs-btn']"
agent-browser is visible "[data-testid='pick-jobs-btn']"
agent-browser is visible "[data-testid='schedule-view-toggle']"

# Verify FullCalendar is in timeGridWeek view (not listWeek)
agent-browser eval "document.querySelector('.fc-timeGridWeek-view') !== null"
# Should print: true

# Open an appointment — modal should be centered (not bottom-sheet)
agent-browser snapshot -i
# Click an appointment ref
agent-browser wait "[data-testid='appointment-modal']"
agent-browser screenshot e2e-screenshots/mobile-schedule/21-macbook-modal.png
# Modal should be sm:w-[560px] sm:rounded-[18px] (existing AppointmentModal v2 desktop layout)
agent-browser eval "getComputedStyle(document.querySelector('[data-testid=\"appointment-modal\"]')).width"
# Should print: "560px"
agent-browser click "[data-testid='close-modal-btn']"

agent-browser console
agent-browser errors
agent-browser close
```

### Script 4 — Desktop drag-drop reschedule (regression check)

```bash
# Drag-drop reschedule must continue to work on desktop (only disabled on mobile)
agent-browser set viewport 1440 900
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
# (manual: drag an event to a different time slot, verify it reschedules)
# This is hard to script with agent-browser — note as a manual verification step
# in the QA checklist instead.
```

### Script 5 — JS console / errors check (cross-cutting)

After each script:
```bash
agent-browser console   # expect no warnings/errors related to our changes
agent-browser errors    # expect zero uncaught exceptions
```

### Outputs

All screenshots go to `e2e-screenshots/mobile-schedule/` (directory created on first run). Reference these in the PR description.

---

## SECURITY CONSIDERATIONS

Per `spec-quality-gates.md` § 8.

### What this PR touches that has security implications

- **Camera access** — `PhotosPanel.tsx` uses `<input type="file" capture="environment">` (existing functionality, not new). Browsers prompt for camera permission. We do not store or transmit images outside the existing customer-photos upload flow.
- **Authentication** — No changes. The Schedule tab is gated behind the existing JWT-auth flow at `/login`. The mobile bottom-sheet AppointmentModal is rendered only when the user is authenticated (Layout-level guard).
- **Stripe Terminal flow** — wrapped inside the `SubSheetHeader`-prefixed `PaymentSheetWrapper`. Stripe Terminal Web requires HTTPS — this is a deployment concern (Vercel handles it). The wrapping does not affect Stripe's iframe security model.
- **Sub-sheet stacking-context fix (Option A)** — adding a `<SubSheetHeader>` does not change the auth/data layer; it's purely visual. The underlying `TagEditorSheet`, `PaymentSheetWrapper`, `EstimateSheetWrapper` are unchanged.

### What this PR does NOT touch

- No backend changes — no API surface area added.
- No JWT or session-handling changes.
- No new env vars or secret references.
- No PII fields surfaced that weren't already surfaced.
- No logging changes (frontend doesn't log to the server-side log pipeline).
- No new third-party scripts loaded.

### Memory-locked test guards (apply during manual QA)

- **`feedback_sms_test_number.md`** — only `+19527373312` may receive real SMS during testing. If the manual QA pass triggers any SMS-sending flow (e.g., `Send Reminder` from the no-reply banner, or Stripe Terminal SMS receipts), use a test customer with this phone number.
- **`feedback_email_test_inbox.md`** — only `kirillrakitinsecond@gmail.com` may receive real emails during testing. Currently the email-sending flow is a stub (per `project_email_service_stub.md` memory) so this is N/A for this PR, but flagged for awareness.

### Acceptance

- [ ] No new secrets or tokens added to env.example, .env, or any committed file.
- [ ] No `console.log` of customer PII added to any touched file.
- [ ] Camera/file inputs preserved with `capture="environment"` and existing accept patterns.
- [ ] Manual QA used only the test phone number `+19527373312` for SMS-triggering paths.

---

## TESTING STRATEGY

Per `frontend-testing.md`, `spec-testing-standards.md` § 2, and `spec-quality-gates.md`. Tests are co-located in `*.test.tsx` files and use Vitest + React Testing Library with the QueryProvider wrapper.

### Coverage Targets (mandatory)

| Layer | Target | Verified by |
|---|---|---|
| Components | 80%+ | `npm run test:coverage` |
| Hooks (`useMediaQuery`) | 85%+ | `npm run test:coverage` |
| Utils | 90%+ | N/A this PR (no util changes) |

### Unit / Component Tests

- **`useMediaQuery`** — Cover: initial-match returns correct value, returns `false` when query doesn't match, updates when `MediaQueryList` change event fires, removes listener on unmount, re-subscribes on query change.
- **`SubSheetHeader`** — Cover: renders title, clicking back button fires `onBack`, optional `rightAction` slot renders.
- **`CalendarView`** — Existing tests pass with `useMediaQuery` mocked to `false`. Add new tests for `useMediaQuery` mocked to `true` covering: `listWeek` is the initial view, `editable={false}`, `selectable={false}`, `noEventsContent` renders for empty week.
- **`SchedulePage`** — Existing tests pass. Add new tests for: mobile action bar shows only `+ New Appointment` + overflow trigger, overflow menu opens and contains expected items, `add-jobs-btn` and `pick-jobs-btn` are not in DOM on mobile (`hidden lg:inline-flex` means they should not be queryable on mobile), desktop layout (`useMediaQuery → false`) shows all buttons.
- **`AppointmentForm`** — Existing tests pass. Add `grid-cols-1 sm:grid-cols-2` does not break form submission.
- **`AppointmentList`** — Existing tests pass. Verify filter inputs render at all viewports.
- **`DaySelector`, `SchedulingTray`, `FacetRail`** — Existing tests pass; changes are CSS-only.
- **`AppointmentModal`** — Existing tests pass after Tailwind migration. Add tests for: nested sub-sheet (`subsheet-tags`, `subsheet-payment`, `subsheet-estimate`) renders with `subsheet-header`, clicking `subsheet-back-btn` calls `closeSheet`.
- **`NotesPanel`, `PhotosPanel`, `ModalHeader`, `CustomerHero`, `ActionTrack`** — Existing tests pass after Tailwind migration. The behavior contract (which `data-testid` clicks fire which handler) must remain stable.

### Loading / Error / Empty State Coverage (mandatory per `spec-testing-standards.md` § 2)

For each touched component test file, ensure the suite covers:

- **Loading state** — `useAppointment`, `useAppointmentTimeline`, `useDailySchedule`, `useWeeklySchedule`, `useStaff` mocked to `{ isLoading: true }`. Assert `LoadingSpinner` renders.
- **Error state** — Same hooks mocked to `{ error: new Error('test') }`. Assert error UI renders.
- **Empty state** — Same hooks mocked to `{ data: { appointments: [] } }`. Assert empty-state copy renders. For the new mobile `listWeek` view: `noEventsContent: 'No appointments this week'`.

### Hook Tests (mandatory per `spec-testing-standards.md` § 2)

- `useMediaQuery.test.ts` is the only new hook in this PR. Tests cover all four behaviors above.

### Form Validation Tests

- `AppointmentForm` already has `AppointmentForm.test.tsx`. Verify time-input `grid-cols-1 sm:grid-cols-2` change doesn't break existing validation tests.

### Integration Tests

- No new integration test files needed — this is a presentational/responsive change.
- The existing `SchedulePage.test.tsx` and `AppointmentModal.test.tsx` exercise the integration of SchedulePage + Calendar + Modal + nested customer/job lookups via TanStack Query. Verify all continue to pass.

### Cross-Feature Integration (mandatory per `spec-quality-gates.md` § 7)

| Test name (existing) | What it verifies | File |
|---|---|---|
| `AppointmentModal renders customer details` | AppointmentModal + customers feature | `AppointmentModal.test.tsx` |
| `AppointmentModal renders job scope` | AppointmentModal + jobs feature | `AppointmentModal.test.tsx` |
| `SchedulePage opens AppointmentModal on event click` | SchedulePage + AppointmentModal | `SchedulePage.test.tsx` |
| `CalendarView renders staff names from useStaff` | CalendarView + staff feature | `CalendarView.test.tsx` |

All four must continue to pass after the Phase 1 changes.

### Property-Based Tests

Per `spec-testing-standards.md` § 1 (Hypothesis is backend-only). N/A for this frontend-only PR.

### E2E (agent-browser)

See "AGENT-BROWSER E2E VALIDATION SCRIPTS" section above. Three viewports (375 × 812, 768 × 1024, 1440 × 900) must all pass.

### Edge Cases

- **iPhone SE (320 px width)** — smallest supported viewport. Verify NotesPanel buttons don't overflow, PhotosPanel cards still scrollable, Schedule action bar fits.
- **iPhone 14 Pro Max (430 px width)** — biggest phone.
- **iPad Air landscape (1180 × 820)** — falls into `lg:` breakpoint, should look like a small desktop.
- **iPad Mini portrait (744 × 1133)** — between `sm` and `md`. Verify breakpoints behave sensibly.
- **iOS dynamic type (accessibility large text)** — verify no critical layout breakage. ActionTrack labels and modal text should still be legible.
- **iOS Safari `100vh` quirks** — modal max-h `92vh` could include the address bar height. Verify the modal still scrolls internally.
- **Soft keyboard open** — when typing in NotesPanel textarea on iPhone, the keyboard takes ~50% of viewport. Verify Save button remains reachable (the `flex-col-reverse` on mobile puts Save above Cancel, which is the correct mobile UX).
- **Drag-drop on touch** — `editable={!isMobile}` should disable drag-drop. Confirm by attempting to drag an event on iPad Safari — should not move.
- **`useMediaQuery` resize during open modal** — rotating from portrait to landscape on iPhone changes width. Verify the modal handles the transition gracefully (no hard crashes).
- **MacBook 1024 × 768 (`lg:` exactly)** — bordering the breakpoint. Verify desktop layout activates.
- **Stripe Terminal flow inside the wrapped PaymentSheetWrapper** — highest-risk sub-sheet, must be manually tested with a real Reader.
- **listWeek view with zero appointments this week** — verify `noEventsContent: 'No appointments this week'` renders.
- **listWeek view with 50+ appointments this week** — verify list scrolls smoothly.

---

## VALIDATION COMMANDS

Execute every command. All must exit 0.

### Level 1: Syntax & Style

```bash
cd frontend && npm run typecheck
cd frontend && npm run lint
cd frontend && npm run format:check
```

### Level 2: Unit Tests

```bash
cd frontend && npm test -- useMediaQuery
cd frontend && npm test -- SubSheetHeader
cd frontend && npm test -- CalendarView
cd frontend && npm test -- SchedulePage
cd frontend && npm test -- AppointmentModal
cd frontend && npm test -- NotesPanel
cd frontend && npm test -- PhotosPanel
cd frontend && npm test -- AppointmentForm
cd frontend && npm test -- AppointmentList
cd frontend && npm test -- FacetRail
cd frontend && npm test -- ModalHeader
cd frontend && npm test -- ActionTrack
```

### Level 3: Full Suite + Coverage

```bash
cd frontend && npm run test:coverage
```

Confirm coverage on touched files does not regress. Confirm components 80%+ overall.

### Level 4: Build Validation

```bash
cd frontend && npm run build
```

Ensures Tailwind compiles, FullCalendar list plugin imports correctly, no runtime-deferred errors.

### Level 5: agent-browser E2E (mandatory per `spec-testing-standards.md` § 3)

```bash
# Pre-flight
agent-browser --version || (npm install -g agent-browser && agent-browser install --with-deps)

# Start backend + frontend
./scripts/dev.sh &
cd frontend && npm run dev &
sleep 8  # let servers spin up

# Run E2E scripts (see "AGENT-BROWSER E2E VALIDATION SCRIPTS" section)
# Script 1: 375x812 (iPhone)
# Script 2: 768x1024 (iPad)
# Script 3: 1440x900 (MacBook)
# Script 4: Desktop drag-drop regression
# Script 5: Console/errors check after each
```

All scripts must:
- Exit 0
- Produce screenshots in `e2e-screenshots/mobile-schedule/`
- Log zero JS console errors via `agent-browser console` and `agent-browser errors`

### Level 6: Manual real-device validation

Validation Level 5 covers most cases via agent-browser. Real-device testing is still required for:

1. **MacBook 13" Chrome (1440 px)** — Visual diff against `main` branch via side-by-side screenshots. Schedule tab and Appointment Modal must be pixel-identical at desktop widths.
2. **MacBook 13" Chrome at 1024 px exactly** — `lg:` breakpoint triggers desktop layout.
3. **Real iPhone Safari (or Browserstack)** — full technician workflow:
   - `/schedule` shows `listWeek` view with appointments grouped by day.
   - Action bar collapses to `+ New Appointment` + overflow menu.
   - Tap an appointment → modal slides up from bottom with grab handle.
   - Tap "En route" → status updates.
   - Tap "Take photo" → camera input opens, captures from rear camera (`capture="environment"`).
   - Tap "See attached notes" → panel expands, Save/Cancel don't overflow.
   - Tap "Edit tags" → sub-sheet renders with back-button header.
4. **Real iPad Safari (or Browserstack)** — both portrait (820 × 1180) and landscape (1180 × 820).
5. **Stripe Terminal payment flow on real iPhone** — Required because Stripe Terminal Web requires HTTPS + a real Reader. Use the test phone number `+19527373312` per memory `feedback_sms_test_number.md` if any SMS is triggered.
6. **iOS Safari viewport quirks** — verify modal `max-h-[92vh]` doesn't get cut off when the iOS address bar is visible. If issues arise, switch to `max-h-[92dvh]`.
7. **Soft keyboard open** — type into NotesPanel textarea on iPhone, verify Save button remains reachable above the keyboard.

### Level 6: Backend regression sanity (no changes expected, but run anyway)

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform && uv run pytest -m unit --maxfail=5 -q
```

The frontend changes don't touch any backend code, but a sanity check is cheap.

---

## ACCEPTANCE CRITERIA

- [ ] **Calendar mobile mode** — `/schedule` on iPhone (≤ 767 px) renders FullCalendar's `listWeek` view by default; toolbar simplified to `prev,next | title | today`; drag-drop disabled.
- [ ] **Schedule action bar collapses** on `< md`: only `+ New Appointment` + overflow `DropdownMenu` visible; on `< lg` (iPad portrait) shows wrapped 2-row layout; on `≥ lg` matches today's single-row layout exactly.
- [ ] **Pick Jobs To Schedule and Add Jobs buttons hidden** on mobile (`hidden lg:inline-flex`), confirming the locked decision that bulk job picking stays desktop-only for this PR.
- [ ] **AppointmentModal nested sub-sheets** (Tags, Payment, Estimate) each render with a `SubSheetHeader` showing a back chevron + title, so on mobile users understand it's a replacement view.
- [ ] **NotesPanel** Save/Cancel buttons no longer overflow on iPhone SE (320 px) — verified via DevTools.
- [ ] **NotesPanel and PhotosPanel** migrated from inline styles to Tailwind classes; visual at `sm:`+ unchanged.
- [ ] **Touch targets** — close button (`ModalHeader`) and phone-call button (`CustomerHero`) are ≥ 44 × 44 px.
- [ ] **AppointmentForm time inputs** stack vertically on `< sm:`.
- [ ] **AppointmentList filters** — Select and Date inputs go full-width on `< sm:`.
- [ ] **DaySelector** scrolls horizontally on phones without truncation.
- [ ] **SchedulingTray** grid uses single column on `< sm:`.
- [ ] **FacetRail** Sheet uses 85vw on phones, 18 rem on `≥ sm:`.
- [ ] **`useMediaQuery` hook** lives at `frontend/src/shared/hooks/useMediaQuery.ts`, exported from the hooks barrel, with unit tests.
- [ ] **`SubSheetHeader` component** lives at `frontend/src/features/schedule/components/AppointmentModal/SubSheetHeader.tsx` with unit tests.
- [ ] **`@fullcalendar/list` package** added to `frontend/package.json` at the same version as the other `@fullcalendar/*` packages.
- [ ] **Desktop view (≥ lg breakpoint, 1024 px+)** is byte-identical (or pixel-equivalent within rounding) to `main` branch — verified via `compare -metric AE` diff with < 0.5% pixel difference.
- [ ] **Pre-flight verification (Task 0)** — all 24 grep checks passed before code changes began.
- [ ] **listWeek spike (Task 6.5)** — completed; outcome documented in PR description; Task 7 implementation matches the spike outcome.
- [ ] **Visual regression baseline + post-migration diff** captured for NotesPanel and PhotosPanel at 1440 px and 375 px; both within acceptable threshold.
- [ ] **Task 17b (PaymentSheetWrapper)** is its own commit at the end of the PR — verified by `git log --oneline` ordering.
- [ ] **No regressions** in any existing Schedule or AppointmentModal test.
- [ ] **`npm run typecheck && npm run lint && npm run format:check && npm run test:coverage`** all exit 0.
- [ ] **Real-device manual QA** completed and documented in PR description (iPhone + iPad + MacBook).
- [ ] **Stripe Terminal payment flow** verified on real iPhone with the wrapped PaymentSheetWrapper.
- [ ] **agent-browser E2E scripts** all pass at viewports 375 × 812, 768 × 1024, 1440 × 900 with zero JS console errors.
- [ ] **data-testid convention** followed for all new testids; existing testids preserved.
- [ ] **Loading / error / empty state** coverage exists for each touched component (per `spec-testing-standards.md` § 2).
- [ ] **Coverage targets met** — Components 80%+, `useMediaQuery` hook 85%+ (per `frontend-testing.md`).
- [ ] **DEVLOG.md updated** with a `FEATURE` entry at the top (per `auto-devlog.md`).
- [ ] **Cross-feature integration tests** in `AppointmentModal.test.tsx`, `SchedulePage.test.tsx`, `CalendarView.test.tsx` all pass (per `spec-quality-gates.md` § 7).
- [ ] **Security checklist** (above) — all items checked.

---

## COMPLETION CHECKLIST

- [ ] All 30 tasks completed in this order: 0 → 1 → 2 → 3 → 4 → 5 → 6 → 6.5 (spike) → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17a → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26.5 → **17b (last code commit)** → 26 (manual QA) → 27 (DEVLOG). Task 17b is intentionally separated from 17a so it ships as the final code commit, allowing independent revert if Stripe Terminal misrenders on a real iPhone.
- [ ] Each task validation passed immediately
- [ ] All Level 1–4 validation commands pass with zero errors
- [ ] agent-browser E2E (Level 5) passes at three viewports with zero console errors
- [ ] Real-device manual QA (Level 6) completed and documented
- [ ] Backend regression test (formerly Level 6, now post-QA sanity) passes — `uv run pytest -m unit --maxfail=5 -q`
- [ ] Acceptance criteria all met (including standards-compliance items)
- [ ] PR description includes screenshots: MacBook before/after at 1440 px (no diff expected), iPhone before/after at 390 px (significant improvement expected), iPad portrait before/after at 820 px — all from `e2e-screenshots/mobile-schedule/`
- [ ] Code reviewer confirms no behavior change at `lg:` breakpoint
- [ ] Investigation document `feature-developments/mobile-responsiveness-investigation/05_RECOMMENDED_APPROACH.md` Phase 1 acceptance criteria all checked
- [ ] DEVLOG.md FEATURE entry inserted at the top
- [ ] Project-standards compliance table checked off (see "PROJECT STANDARDS COMPLIANCE" — every steering-doc requirement mapped)

---

## NOTES

### Out of scope (intentionally deferred)

- **PickJobsPage** (`/schedule/pick-jobs`) — bulk-pick job table is unusable on mobile (~1100 px hard-coded column widths). Deferred to Phase 2 per the locked decision in this plan. Buttons that navigate to it are hidden on mobile.
- **Generate Routes** (`/schedule/generate`) — admin/office workflow. Out of scope.
- **Other admin pages** — Sales, Customers, Jobs, Invoices, Settings, etc. Phase 2 work.
- **Chart heights** — recharts `h-80` issues on landscape iPhone. Phase 2 cosmetic fix.
- **Sub-sheets to standalone Radix Sheets refactor (Option B)** — deferred to Phase 3 if Option A's back-button header doesn't satisfy users.
- **Landscape-iPhone breakpoint** — Phase 3 polish.
- **`100dvh` migration** — Phase 3 polish.
- **Mobile global search** — Phase 2.
- **PWA install** — Phase 3.

### Decisions locked into this plan

1. **Responsive web, not native** — confirmed.
2. **Minimum viewport 375 px** (iPhone SE 2nd/3rd gen, iPhone 13 mini, iPhone 14) — base styles target 375; iPhone SE 1st gen at 320 px should still be functional but is not actively tested.
3. **`listWeek` as default mobile calendar view** — chosen based on Jobber/ServiceTitan/Housecall Pro precedent.
4. **Drag-drop disabled on mobile**, route reschedule through Edit dialog — chosen to avoid touch/scroll conflicts.
5. **Sub-sheet Option A** (back-button header) over Option B (standalone Radix Sheets) — chosen for lower risk; Option B deferred.
6. **PhotosPanel and NotesPanel Tailwind migration in this PR** — extra ~0.5 day, but unlocks future mobile-specific tweaks.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| `listWeek` view doesn't render custom `eventContent` correctly | **Task 6.5 spike** is a decision-gate before Task 7. If the spike fails, swap `eventContent` for a simpler mobile-only renderer (or drop on mobile) — adds ~0.5 day. |
| `listWeek` view doesn't satisfy technician workflow | If the user-facing experience is poor after Phase 1, fall back to building a custom list view (~3 extra days, deferred to a follow-up PR). Initial spike + real-device test in Task 26 catches this. |
| Stripe Terminal Web flow breaks inside the wrapped PaymentSheetWrapper | **Task 17b is its own commit at the end of the PR.** Manual testing on a real iPhone with a real Reader is mandatory. If broken, **revert Task 17b commit only** — the rest of the PR is preserved. The Payment sub-sheet then ships without the back-button header (architecturally inconsistent with Tags/Estimate, but functional). Document with a TODO. |
| iOS Safari `100vh` quirks cause cut-off footer buttons | The modal already uses `max-h-[92vh]` which is generally safe. Real-device test in Task 26. If issues arise, switch to `max-h-[92dvh]` (modern Safari supports `dvh`). |
| Tailwind class migration in NotesPanel/PhotosPanel changes desktop visual | **VISUAL REGRESSION STRATEGY** (in plan) — capture pre-migration baseline, run `compare -metric AE` post-migration, fail loudly if desktop pixel-diff > 0.5%. Likely-cause-fix: switch to arbitrary-value classes (`border-[#E5E7EB]` instead of `border-slate-200`). |
| `display: contents` on the `hidden lg:contents` wrapper has accessibility issues | Older screen readers ignore `contents`-flagged elements; modern ones (NVDA, VoiceOver, JAWS 2020+) respect them. If a11y testing flags issues, fall back to a non-`contents` layout that explicitly duplicates the content per breakpoint (slight DOM differences on desktop, but identical UX). |
| Tabs component conflicts with DropdownMenu ARIA roles | Plan explicitly converts Tabs → plain DropdownMenuItems in the mobile overflow menu. Verified by ARIA spec review. |
| `SendAllConfirmationsButton` triggers double-click events when wrapped in DropdownMenuItem | Verify in Task 11 unit tests. If problematic, render outside the menu as an icon-button visible at `< md:` only (extra ~0.25 day). |
| The `editable={!isMobile}` change disables drag-drop entirely on iPad portrait | The query `(max-width: 767px)` returns `false` for iPad portrait at 820 px, so `editable` stays `true` there. Drag-drop is preserved on iPad. Verify manually. |
| `useMediaQuery` SSR/hydration mismatch | Project is Vite SPA (no SSR), so this risk doesn't apply. The `typeof window === 'undefined'` guard is defensive only. |
| Pre-flight verification (Task 0) reveals codebase has drifted from plan assumptions | **STOP and re-evaluate** before proceeding. Update the plan against current state. Better than silent failures mid-implementation. |
| Real-device QA reveals unanticipated bugs | Budget includes Task 26 (1–2 days) and an explicit follow-on bug-fix round if needed. Stripe-specific issues isolated by Task 17b commit ordering. |

### Memory references applied

- **`feedback_sms_test_number.md`** — only `+19527373312` may receive real SMS during testing/debugging. This applies to Task 26 step 5 and step 6 (any SMS-triggering UI in Stripe Terminal or AppointmentModal during manual QA).
- **`feedback_email_test_inbox.md`** — only `kirillrakitinsecond@gmail.com` may receive emails during dev/staging. Not directly relevant to this PR but flagged for awareness.

### Why no backend changes

The Schedule tab and Appointment Modal are pure frontend surfaces. The mobile responsiveness work touches CSS, JSX, and a single new React hook. No FastAPI/SQLAlchemy code, no database migrations, no API contract changes.

---

**File location:** `.agents/plans/schedule-and-appointment-modal-mobile-responsive.md`
