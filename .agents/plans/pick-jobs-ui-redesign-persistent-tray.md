# Feature: Pick Jobs to Schedule — UI Redesign (Persistent Tray)

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing. Pay special attention to naming of existing utils/types/models. Import from the right files.

## Feature Description

Visual redesign of `/schedule/pick-jobs` (the "Pick jobs to schedule" page) to match the high-fidelity reference at `/Users/kirillrakitin/Desktop/Schedule Jobs Picker - Persistent Tray.html`. Scope is pure frontend (React 19 + Tailwind 4 + shadcn). No backend, schema, or data shape changes. The page already wires data, selection, filtering, sorting, and assignment correctly — what's changing is layout, palette, typography, and the persistent scheduling tray's visual treatment.

Four redesigns happen together because they share a common scoped style system:

1. **Page shell** — replace today's `grid-cols-1 lg:grid-cols-[240px_1fr]` shell with the reference's two-column app layout (`248px` rail + main canvas), gives the page a soft `--canvas` background, and reserves bottom padding for the always-fixed scheduling bar.
2. **Facet rail (left)** — restyle the existing `FacetRail` to match the reference: 248px sticky sidebar, "Filters" brand mark, group titles with uppercase tracking, custom 16px checkbox, soft amber-tint highlight on selected rows, JetBrains-Mono counts, "Clear" link in header, and a non-interactive "make group" pill placeholder per group (visual only — see Notes for why this is stubbed).
3. **Jobs table (center)** — rounded `1.5px` border card, sticky soft-grey thead, colored job-type pills (`spring_startup` green, `fall_winterization` amber, `mid_season_inspection` blue, with a graceful neutral fallback for any other job-type), uppercase pill tags (with color mapping for the 4 known `CustomerTag` values plus a neutral "dashed" style for any property-derived label like Commercial/HOA), an indigo `inset 3px 0 0` selection stripe, and an amber-tint `.note-row` directly under any job whose `Job.notes` is populated. **The notes source stays as-is — `Job.notes` from the existing `JobReadyToSchedule.notes` field — no new plumbing.**
4. **Persistent scheduling tray (bottom)** — replace today's in-flow `<section>` tray with a `position: fixed` bar that sits below the main column with `backdrop-filter: saturate(180%) blur(12px)`, header (`"Schedule N jobs"` + Clear), 4-field row (Date / Staff / Start / Default duration), collapsible per-job time table, footer with mono count pill, contextual summary string (`"3 jobs selected · 3 cities · ~3h total"`), and a primary teal `bar-assign-cta` button.

The bottom bar is the visual centerpiece of the redesign — the user has explicitly asked for it to be "pixel-faithful" to the reference (Inter + JetBrains Mono fonts, the reference's exact CSS variables for color), so we'll introduce a small page-scoped CSS file and load both webfonts only on this route.

## User Story

As a **scheduler / admin (Viktor or Maria)**
I want **the Pick Jobs page to look like the high-fidelity reference — clear sticky filters, scannable colored pills, an always-pinned tray with my date/staff/time inputs**
So that **I can quickly batch-pick a day's worth of jobs, eyeball capacity at a glance, and assign them without losing context — even when the table is long enough to scroll.**

## Problem Statement

Today's UI works but is visually flat: pills are plain shadcn `Badge` outlines, tag colors don't match the design system, the scheduling tray sits below the table in normal flow (so it shifts off-screen when the table is short), and the typography is the default sans stack with no monospace treatment for numerics. The reference design solves all four:

- Sticky facet rail with high-affordance selected state (amber tint, mono count) → faster filter scanning.
- Colored job-type pills + uppercase tag badges → seasonal type and customer flags pop.
- Indigo selection stripe + amber note row → the "what did I pick" and "what should I know" cues are unmistakable.
- Backdrop-blurred fixed tray with teal CTA → assignment never leaves the viewport.

## Solution Statement

Restyle in place. The four existing components — `PickJobsPage`, `FacetRail`, `JobTable`, `SchedulingTray` — keep their props, state, and TanStack Query hooks. We add a single scoped CSS file (`pick-jobs-theme.css`) imported only by `PickJobsPage.tsx`, plus two pure colour-mapping helpers (`job-type-colors.ts`, `customer-tag-colors.ts`) so the JSX stays declarative.

Tags strategy: the existing `CUSTOMER_TAG_CONFIG` has 4 values (`priority`, `red_flag`, `slow_payer`, `new_customer`). We **don't** invent new tag values — instead, the new mapper extends the palette to the reference's 4 known tags using a reference-faithful colour, and falls back to a neutral dashed pill for any unknown string (so when the API later returns extra tags, the UI degrades cleanly). Property-derived labels (Commercial, HOA, Subscription) keep coming from the existing `PropertyTags` shared component but get the same neutral "dashed border" treatment.

Notes strategy: keep the current `Job.notes` source verbatim (set in `src/grins_platform/api/v1/schedule.py:509`, surfaced via `JobReadyToSchedule.notes` schema). Only the styling of the existing amber row in `JobTable.tsx:204-212` changes.

## Feature Metadata

**Feature Type**: Enhancement (UI redesign)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- `frontend/src/features/schedule/pages/PickJobsPage.tsx` (layout shell)
- `frontend/src/features/schedule/components/FacetRail.tsx` (sidebar styling)
- `frontend/src/features/schedule/components/JobTable.tsx` (table card + pills)
- `frontend/src/features/schedule/components/SchedulingTray.tsx` (fixed tray)
- `frontend/src/features/schedule/styles/pick-jobs-theme.css` (NEW — scoped CSS vars, fonts)
- `frontend/src/features/schedule/utils/job-type-colors.ts` (NEW — pure mapper)
- `frontend/src/features/schedule/utils/customer-tag-colors.ts` (NEW — pure mapper)

**Dependencies**: None new. Inter + JetBrains Mono are loaded via Google Fonts CSS `@import` inside the scoped stylesheet, lazy-loaded only on this route. No new npm packages.

**Out of scope**: Backend changes, new tag values/dictionary, "make group" facet grouping pill from the reference (hidden entirely until that feature ships — see Notes), reference HTML's notification bell / help button / avatar chip in the topbar (the app shell already provides those globally), data freshness indicator (tracked separately by `gap-15-queue-freshness-and-realtime.md`).

**In scope additions (locked from clarifying questions)**:
- **Full mobile responsive pass** (sub-1024px). Page reflows to single column, FacetRail's existing Sheet behaviour is preserved but its content is restyled to match the new system, and the fixed scheduling tray spans full width with stacked fields.
- **Locked tag colour map**: `priority` → violet (VIP variant), `red_flag` → red, `slow_payer` → amber, `new_customer` → teal/prepaid. Unknown tag strings get the neutral dashed pill.
- **`<div role="grid">` over `<table>`** for the jobs list, matching the reference. Existing tests don't query `getByRole('table')`, so semantics are preserved through ARIA roles.
- **shadcn `<Checkbox>` stays** for a11y; visual override applied via descendant CSS in scoped sheet.

---

## FUNCTIONALITY PRESERVATION GUARDRAIL — READ FIRST

**This is a visual/UX redesign, not a refactor.** Every behaviour the page has today must keep working unchanged. If a task in the step-by-step list seems to require changing logic to achieve a visual effect, STOP and look for a CSS-only path first.

**Things that MUST NOT change** (treat any deviation as a bug):

| Behaviour | Where it lives today |
|---|---|
| Data fetching for the jobs list | `useJobsReadyToSchedule()` hook call, `PickJobsPage.tsx:48` |
| Staff list fetching | `useStaff({ is_active: true })`, `PickJobsPage.tsx:49` |
| Bulk assign mutation | `useCreateAppointment()` + `handleBulkAssign()`, `PickJobsPage.tsx:50, 246-279` |
| Search debounce (150ms) | `useEffect` at `PickJobsPage.tsx:72-75` |
| `/` keyboard shortcut focuses search | `PickJobsPage.tsx:78-89` |
| Cmd/Ctrl+Enter triggers Assign | `PickJobsPage.tsx:92-105` |
| Filter logic (city, jobType, requestedWeek, priority, tags) | `filteredJobs` memo, `PickJobsPage.tsx:108-136` |
| Sort logic (3-state: asc → desc → default) | `sortedJobs` memo + `handleSort`, `PickJobsPage.tsx:139-177` and `JobTable.tsx:42-48` |
| Selection state (toggle / select-all-visible / clear) | `toggleJob` / `toggleAllVisible` / `clearSelection`, `PickJobsPage.tsx:180-219` |
| `useBlocker` unsaved-changes navigation guard + Dialog | `PickJobsPage.tsx:238-243, 290-313` |
| `beforeunload` browser guard | `PickJobsPage.tsx:226-235` |
| Per-job time cascade | `computeJobTimes()` from `pick-jobs.ts:95-122`, called in `SchedulingTray.tsx:50` |
| Time-overlap warning | `overlapWarning` check, `SchedulingTray.tsx:52-54` |
| Helper text logic ("Pick jobs above" / "Pick a staff member" / overlap) | `SchedulingTray.tsx:57-61` |
| `disableAssign` rule | `SchedulingTray.tsx:55` |
| `hiddenCount` text when filters hide selected jobs | `SchedulingTray.tsx:47, 90-94` |
| FacetRail relaxed-count semantics | `relaxedCount()` / `matches()` / `matchesValue()` in `FacetRail.tsx:103-211` |
| FacetRail Sheet behaviour at `<lg` | `FacetRail.tsx:49-72` |
| City normalization in facet rail | `normalizeCity()` from `utils/city.ts`, used at `FacetRail.tsx:87, 190, 205` and `PickJobsPage.tsx:121` |
| Notes data source (`Job.notes` → `JobReadyToSchedule.notes`) | Backend at `api/v1/schedule.py:509`; frontend at `JobTable.tsx:204` |
| Empty-state rendering (no jobs match filters; all scheduled) | `JobTable.tsx:73-88` |
| `data-testid` selectors used by tests | All existing test IDs across the four components — preserve verbatim |
| Customer tag rendering | Continues using `CUSTOMER_TAG_CONFIG` for label text; only visual variant adds reference colours |
| `PropertyTags` shared component | Continues to render via `JobTable.tsx:183-188`; only its wrapper class changes |

**Things that MAY change** (this is the redesign surface):

- Layout (grid template, column widths, page padding, `position: fixed` for tray)
- Typography (Inter + JetBrains Mono via scoped CSS)
- Colours (palette mapped to reference CSS variables)
- Tailwind utility classes on JSX
- `<table>` → `<div role="grid">` ONLY if needed for the CSS-grid card layout (test selectors must survive)
- Inline pill markup (replace shadcn `Badge` with `.pjp-pill`/`.pjp-tag` per reference)
- Outer container classNames on `PickJobsPage`, `FacetRail`, `JobTable`, `SchedulingTray`

**Rule of thumb**: if a JSX change touches a hook, a `useState`, a `useMemo`, an event handler body, or a prop passed downward — it's out of scope. If it only changes className strings or wraps existing children in new layout divs, it's in scope.

---

## CONTEXT REFERENCES

### Project Steering Documents — MANDATORY READ + APPLY

These are project-level standards that override anything generic. Read them before implementing and follow them strictly. (kiro-/kiro-cli-specific steering — `pre-implementation-analysis.md`, `knowledge-management.md`, `kiro-cli-reference.md` — is intentionally excluded; the instructions there about kiroPowers, MCP servers, custom agents, and `kiro-cli settings` don't apply outside the kiro harness.)

| Steering doc | Path | What it forces this plan to honour |
|---|---|---|
| **structure.md** | `.kiro/steering/structure.md` | VSA layout: features import only from `core/` and `shared/`, never each other. New utils go in `frontend/src/features/schedule/utils/` (correct). Component naming PascalCase, hooks `use{Name}`, utils kebab-case. |
| **tech.md** | `.kiro/steering/tech.md` | Stack: React 19 / TS 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4 / Radix + shadcn. PEP 8 (backend only — N/A here). All quality checks must pass with zero errors. |
| **frontend-patterns.md** | `.kiro/steering/frontend-patterns.md` | (a) `cn()` for conditional classes — **verified path**: `import { cn } from '@/lib/utils';` (matches existing schedule feature usage in `ScheduleGenerationPage.tsx:24`, `DaySelector.tsx:8`, `JobSelectorCombobox.tsx:20`). (b) **`data-testid` convention**: `{feature}-page`, `{feature}-table`, `{feature}-row`, `{action}-{feature}-btn`, `nav-{feature}`, `status-{value}`. The new `tray-selected-count` testid added in this plan **conforms** (`{feature}-{value}` pattern matches `tray-` prefix used elsewhere). (c) Loading state = `<LoadingSpinner />` (already imported by `PickJobsPage.tsx:23`), error state = `<Alert variant="destructive">`. (d) Public API via feature `index.ts` — new utils are internal to schedule feature, no need to export. |
| **frontend-testing.md** | `.kiro/steering/frontend-testing.md` | (a) Vitest + React Testing Library; (b) co-located test files (`Component.test.tsx` next to `Component.tsx`) — but existing pattern in this codebase uses `__tests__/` subdirectories (`PickJobsPage.test.tsx` is in `pages/` directly, while other features use `__tests__/`). **Follow the per-directory existing convention**: pages get `.test.tsx` co-located, components get `__tests__/Component.test.tsx`. (c) **Coverage targets — mandatory**: components 80%+, hooks 85%+, utils 90%+. The new `job-type-colors.ts` and `customer-tag-colors.ts` are utils — must hit 90%+ coverage. (d) Wrap component tests in `QueryProvider` if they touch hooks. (e) `userEvent.setup()` for user interactions. |
| **code-standards.md** | `.kiro/steering/code-standards.md` | (a) Quality commands must run with zero errors. The frontend-relevant ones: `npm run lint` (ESLint) and `npm run typecheck` (tsc). (b) Backend logging/testing rules don't apply (no backend changes). (c) Task completion checklist applies. |
| **spec-quality-gates.md** | `.kiro/steering/spec-quality-gates.md` | The `*specs*` fileMatch means this doc applies to `.kiro/specs/*` artefacts, not to `.agents/plans/`. **However**, the requirement-level rules it mandates still apply because the redesign is a real feature: (i) data-testid convention map (already in TEST COMPATIBILITY MATRIX); (ii) agent-browser validation scripts (added below in Level 5); (iii) quality gate commands (already in VALIDATION COMMANDS); (iv) coverage targets (locked to 80/85/90). |
| **spec-testing-standards.md** | `.kiro/steering/spec-testing-standards.md` | Mandates: component tests, form validation tests (N/A — no new forms), loading/error/empty state coverage (already in JobTable empty-state at lines 73–88). agent-browser E2E validation for UI changes — **added below in Level 5**. ESLint + TS strict zero-errors. |
| **e2e-testing-skill.md** | `.kiro/steering/e2e-testing-skill.md` | E2E procedure with agent-browser. Phase 6 mandates **responsive testing at 3 viewports** (mobile 375×812, tablet 768×1024, desktop 1440×900). The mobile pass added in Phase 4 of this plan must be validated against all three. Screenshots saved to `e2e-screenshots/`. |
| **agent-browser.md** | `.kiro/steering/agent-browser.md` | CLI command reference for the Level 5 validation script. Use `agent-browser snapshot -i` to get refs, `agent-browser click @eN` / `fill @eN`, `agent-browser screenshot e2e-screenshots/pick-jobs-redesign-{viewport}.png` per viewport. |
| **auto-devlog.md** + **devlog-rules.md** | `.kiro/steering/{auto-devlog,devlog-rules}.md` | After completing this redesign, **append an entry to DEVLOG.md** at the top, under "## Recent Activity". Format from devlog-rules.md: `## [YYYY-MM-DD HH:MM] - FEATURE: Pick Jobs page UI redesign + persistent tray`. Categories: FEATURE (primary) + DESIGN (secondary, if used). Sections: What Was Accomplished / Technical Details / Decision Rationale / Challenges and Solutions / Next Steps. |
| **parallel-execution.md** | `.kiro/steering/parallel-execution.md` | Phase 3 of this plan (the three component restyles — FacetRail / JobTable / SchedulingTray) is **explicitly parallelizable** and should be executed in parallel by independent subagents if available. Phase 1 (foundation), Phase 2 (page shell), Phase 4 (mobile), Phase 5 (tests) are sequential. |

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**Visual reference (read first):**
- `/Users/kirillrakitin/Desktop/Schedule Jobs Picker - Persistent Tray.html` — the design source of truth. CSS lives in `<style>` (lines 9–797), markup starts at `<body>` (line 800), reactive script (lines 1658–1844).
  - Lines 10–42: full `:root` CSS-variable palette — copy these verbatim into the scoped stylesheet.
  - Lines 53–129: facet rail structure (`.rail`, `.facet-group`, `.facet-row`, `.cb`).
  - Lines 206–317: jobs table (`.table-card`, `.row`, `.pill`, `.tag`, `.note-row`).
  - Lines 600–793: persistent fixed scheduling bar (`.sched-bar`, `.bar-fields`, `.pjt-table`, `.bar-assign-cta`).

**Pages & components to modify:**
- `frontend/src/features/schedule/pages/PickJobsPage.tsx` (lines 1–393) — orchestrator. The grid layout at line 315 (`grid h-[calc(100vh-theme(spacing.16))] grid-cols-1 grid-rows-[auto_1fr_auto] lg:grid-cols-[240px_1fr]`) gets replaced. Header at lines 320–332 stays minus the "← Back to schedule" affordance (we keep it but restyle). Tray section wrapper at lines 367–389 changes from in-flow `<section>` to a sibling that the new fixed `SchedulingTray` portals/positions itself outside the grid.
- `frontend/src/features/schedule/components/FacetRail.tsx` (lines 1–270) — keep all props, all relaxed-count logic, all priority labels. Only the JSX/className output changes. The `Group` component (line 230) becomes the most-edited section.
- `frontend/src/features/schedule/components/JobTable.tsx` (lines 1–248) — keep all props, sort logic, filter empty-state. The `<table>` at line 90 becomes a CSS-grid card to match the reference's `grid-template-columns: 36px 2.0fr 1.4fr 1.3fr 0.9fr 1fr 0.6fr 0.6fr 0.9fr` from the HTML reference (line 218). The `JobRow` subcomponent (line 142) gets the heaviest restyle. Note row at lines 204–212 gets the amber-tint design treatment.
- `frontend/src/features/schedule/components/SchedulingTray.tsx` (lines 1–230) — keep every prop and handler. The outer `<section>` at line 64 changes from `border-t border-border` (in-flow) to a fixed-position bar. Field grid at lines 97–140 reflows to `1.1fr 1.4fr 1fr 1.1fr`. Per-job table styling at lines 156–206 changes. CTA button at lines 215–225 becomes the teal `.bar-assign-cta`.

**Types & helpers (read for shape, no edits):**
- `frontend/src/features/schedule/types/pick-jobs.ts` (lines 1–122) — `JobReadyToScheduleExtended`, `FacetState`, `PerJobTimeMap`, `computeJobTimes`. Don't change shapes.
- `frontend/src/features/schedule/utils/city.ts` — `normalizeCity` (already used by FacetRail). Keep.
- `frontend/src/features/jobs/types/index.ts` (lines 22, 351–375) — `CustomerTag` union (4 values) + `CUSTOMER_TAG_CONFIG`. The new `customer-tag-colors.ts` mapper imports both and adds the reference palette overlay.
- `frontend/src/shared/components/PropertyTags.tsx` — already used by `JobTable.tsx:183-188`. Don't change its API; if its current visual style clashes with the reference, write new dashed-style overrides inside the scoped CSS.

**Backend reference (read-only, for understanding):**
- `src/grins_platform/api/v1/schedule.py:413–528` (`get_jobs_ready_to_schedule`) — populates `notes=job.notes` at line 509. **Do not change.**
- `src/grins_platform/schemas/schedule_explanation.py:130–200` (`JobReadyToSchedule`) — schema; `notes` field at line 166. **Do not change.**

**Tests to update / add:**
- `frontend/src/features/schedule/pages/PickJobsPage.test.tsx` — **two specific assertions must be updated** because they query `document.querySelector('.text-teal-700')` (lines 202–203 and 230–231). The redesign drops that Tailwind class. Replace with `screen.getByTestId('tray-selected-count')`. Every other test continues to pass without edits — see TEST COMPATIBILITY MATRIX below.
- `frontend/src/features/schedule/types/pick-jobs.test.ts` and `pick-jobs.pbt.test.ts` — no changes (pure types).
- `frontend/src/features/schedule/components/__tests__/JobTable.test.tsx` — NEW.
- `frontend/src/features/schedule/components/__tests__/SchedulingTray.test.tsx` — NEW.
- `frontend/src/features/schedule/utils/__tests__/job-type-colors.test.ts` — NEW.
- `frontend/src/features/schedule/utils/__tests__/customer-tag-colors.test.ts` — NEW.

### TEST COMPATIBILITY MATRIX (PickJobsPage.test.tsx)

Every existing test was inspected. Outcome:

| Line(s) | Assertion | Survives redesign? | Action |
|---|---|---|---|
| 188 | `getByTestId('pick-jobs-page')` | ✅ | Preserve testid on outer div. |
| 189 | `getByText(/All jobs are scheduled/)` | ✅ | Empty state copy unchanged. |
| 199, 218, 254, 278, 320, 329, 382, 418 | `getByTestId('job-row-${id}')` click | ✅ | Preserve testid; click handler stays. |
| **202–203, 230–231** | `document.querySelector('.text-teal-700')` text content | ❌ **BREAKS** | Add `data-testid="tray-selected-count"` to the count `<span>` in `SchedulingTray.tsx`. Update both assertions to `screen.getByTestId('tray-selected-count').textContent`. |
| 221 | `getAllByTestId('facet-value-city-Minneapolis')` | ✅ | Preserve `data-testid={\`facet-value-${facetKey}-${v}\`}` in the new FacetRail markup. |
| 222–223 | `.querySelector('button')` inside facet value | ✅ | shadcn Checkbox renders as `<button>`; we keep the primitive. |
| 226, 228, 303, 304 | `queryByTestId('job-row-${id}')` filter visibility | ✅ | Same. |
| 243, 260 | `getByTestId('tray-assign-btn')` (disabled / click) | ✅ | Preserve testid on the new `.pjp-bar-assign-cta` button. |
| 168–172 | `getByTestId('tray-staff').closest('select')` | ✅ | Preserve `tray-staff` testid on the SelectTrigger. |
| 263–268 | `mockMutateAsync` called with shape `{ job_id, staff_id }` | ✅ | `handleBulkAssign` body unchanged. |
| 282–283 | `toast.success` called | ✅ | Toast logic unchanged. |
| 298 | `getByTestId('job-search')` | ✅ | Preserve testid on Input. |
| 323 | `getByTestId('tray-time-adjust-toggle')` | ✅ | Preserve testid. |
| 326, 333 | `getByTestId('tray-time-adjust-table')` | ✅ | Preserve testid. |
| 342 | `getByTestId('tray-date')` value | ✅ | Preserve testid. |
| 391 | `getByText('Leave without scheduling?')` | ✅ | Dialog content unchanged. |
| 408 | `document.activeElement === searchInput` after `/` keypress | ✅ | Keyboard shortcut unchanged. |
| 429 | `mockMutateAsync` called after Cmd+Enter | ✅ | Keyboard shortcut unchanged. |
| **439** | `getByRole('main')` | ✅ | Keep `<main>` element. |
| **440** | `getByRole('complementary')` (i.e. `<aside>`) | ✅ | Keep `<aside>` element. |
| **442** | `getAllByRole('region', { name: /Scheduling assignment/i })` | ✅ | Keep `<section aria-label="Scheduling assignment">` on both PickJobsPage's wrapper and SchedulingTray's outer element. |
| 469 | `[class*="animate-spin"]` selector for LoadingSpinner | ✅ | LoadingSpinner component unchanged. |

**Net effect**: exactly one test file change, exactly two assertion swaps. All landmark roles, `data-testid`s, dialog text, and toast behaviour survive verbatim.

- `frontend/src/features/schedule/styles/pick-jobs-theme.css` — scoped CSS variables (`--ink`, `--blue`, `--teal-prim`, `--amber-tint`, etc. from reference lines 10–42), font `@import` for Inter and JetBrains Mono, helper classes (`.pjp-mono`, `.pjp-pill`, `.pjp-tag`, `.pjp-note-row`, `.pjp-sched-bar`, etc.). All selectors prefixed `.pjp-` or scoped under a top-level `[data-pjp-root]` to prevent global leakage.
- `frontend/src/features/schedule/utils/job-type-colors.ts` — pure function `getJobTypeColorClass(jobType: string): "spring" | "fall" | "mid" | "neutral"` mapping `spring_startup` → spring, `fall_winterization` → fall, `mid_season_inspection` → mid, anything else → neutral.
- `frontend/src/features/schedule/utils/customer-tag-colors.ts` — pure function `getCustomerTagStyle(tag: string): { label: string; variant: "vip" | "prepaid" | "commerc" | "hoa" | "ladder" | "dog" | "gated" | "neutral" }` extending `CUSTOMER_TAG_CONFIG` for known tags; falling back to `{ label: titleCase(tag), variant: "neutral" }` for unknowns.
- `frontend/src/features/schedule/components/__tests__/JobTable.test.tsx` — verify pill colour classes on known job types; verify note row appears iff `job.notes` is populated.
- `frontend/src/features/schedule/components/__tests__/SchedulingTray.test.tsx` — verify "X cities · ~Yh total" summary, fixed-position class applied, Assign CTA disabled when no staff selected.
- `frontend/src/features/schedule/utils/__tests__/job-type-colors.test.ts` — known + unknown mappings.
- `frontend/src/features/schedule/utils/__tests__/customer-tag-colors.test.ts` — known + unknown mappings, label title-casing for unknowns.

### Relevant Documentation — READ THESE BEFORE IMPLEMENTING

- [Tailwind 4 — Custom theme & CSS variables](https://tailwindcss.com/docs/theme) — Section: "Customizing your theme using CSS variables". Why: explains how scoped `:root`/`@theme` variables interact with Tailwind 4's CSS-first config. We will NOT register new theme tokens (the reference uses raw CSS vars), but understand how they cascade.
- [Tailwind 4 — `@layer` directives](https://tailwindcss.com/docs/adding-custom-styles) — Section: "Using @layer". Why: scoped helper classes (e.g. `.pjp-pill`) should live in the `@layer components` layer so utility classes still win over them.
- [MDN — `position: fixed` + `backdrop-filter`](https://developer.mozilla.org/en-US/docs/Web/CSS/backdrop-filter) — Why: the fixed tray needs `backdrop-filter: saturate(180%) blur(12px)` and Safari-prefixed `-webkit-backdrop-filter`. Without the prefix, iOS Safari renders an opaque white panel.
- [Google Fonts — Inter + JetBrains Mono](https://fonts.google.com/specimen/Inter) — exact import URL the reference uses (line 8 of HTML): `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap`. Use the same URL inside the scoped CSS file's `@import` to keep parity.
- [shadcn Checkbox](https://ui.shadcn.com/docs/components/checkbox) — Why: The reference's custom 16/18px checkbox does NOT match shadcn `Checkbox`'s default Radix-based render. We continue using the shadcn primitive (for keyboard/a11y) but override its visual via Tailwind classes — see `FacetRail.tsx` line 259 for the existing usage we wrap.
- [Vitest + Testing Library — `toHaveClass`](https://testing-library.com/docs/queries/about/) — used in the new component tests to assert correct pill/tag classes apply.

### Patterns to Follow

**Naming conventions** — match existing code:

```ts
// Pure helper modules: kebab-case file, named exports, no default exports
// frontend/src/features/schedule/utils/city.ts (existing)
export function normalizeCity(raw: string | null | undefined): string | null { ... }

// Mirror this exactly:
// frontend/src/features/schedule/utils/job-type-colors.ts (NEW)
export type JobTypeColor = 'spring' | 'fall' | 'mid' | 'neutral';
export function getJobTypeColorClass(jobType: string): JobTypeColor { ... }
```

**CSS scoping** — pattern: prefix every class in `pick-jobs-theme.css` with `.pjp-` (pick-jobs-page) and gate the whole sheet with a top-level `[data-pjp-root]` attribute on `PickJobsPage`'s outermost `<div>`. Why: lets us write authentic CSS rules without polluting the global cascade.

```css
/* frontend/src/features/schedule/styles/pick-jobs-theme.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');

[data-pjp-root] {
  --pjp-ink: #0B1220;
  --pjp-blue: #1D4ED8;
  --pjp-teal-prim: #14B8A6;
  /* ... etc. */
  font-family: 'Inter', -apple-system, system-ui, sans-serif;
}

[data-pjp-root] .pjp-mono { font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace; font-feature-settings: 'tnum' 1; }
[data-pjp-root] .pjp-pill.spring { background: var(--pjp-green-bg); color: var(--pjp-green); border-color: #86EFAC; }
[data-pjp-root] .pjp-pill.fall   { background: var(--pjp-amber-bg); color: var(--pjp-amber); border-color: #FCD34D; }
[data-pjp-root] .pjp-pill.mid    { background: var(--pjp-blue-bg);  color: var(--pjp-blue);  border-color: #93C5FD; }
[data-pjp-root] .pjp-pill.neutral { background: var(--pjp-soft); color: var(--pjp-ink3); border-color: var(--pjp-line); }
```

**Component composition** — keep props stable. Pattern from `FacetRail.tsx:37-72` (Sheet for md, inline for lg+) stays. We modify only the inner `FacetRailContent` rendering. Pattern from `SchedulingTray.tsx:44-228` (every prop forwarded to controlled inputs) stays.

**Pure colour mappers (test-friendly)** — follow `frontend/src/features/jobs/types/index.ts:351-375` (`CUSTOMER_TAG_CONFIG`):

```ts
// Don't:
function pillClass(t: string) { if (t === 'spring_startup') return 'green'; ... } // imperative

// Do:
const JOB_TYPE_COLORS: Record<string, JobTypeColor> = {
  spring_startup: 'spring',
  fall_winterization: 'fall',
  mid_season_inspection: 'mid',
} as const;
export function getJobTypeColorClass(jobType: string): JobTypeColor {
  return JOB_TYPE_COLORS[jobType] ?? 'neutral';
}
```

**Fixed-position tray** — pattern: use a portal or simply `position: fixed` with `bottom: 0; left: 248px; right: 0`. The reference uses the latter (line 600–615 of HTML) plus a `@media (max-width: 1180px)` adjustment. The current `SchedulingTray.tsx:67` uses `border-t bg-card`; we replace the `<section>` className entirely. Caveat: `position: fixed` decouples the tray from the grid, so we must add bottom padding on the main scroll region (`.pjp-main-scroll-pad { height: 132px; }` per HTML line 796) to prevent the last table row hiding behind the bar.

**Selection visual** — current `JobTable.tsx:149` uses `bg-teal-50`. Reference (line 235) uses `background: #F5F8FF; box-shadow: inset 3px 0 0 var(--blue);`. Apply via the scoped class `.pjp-row.selected`.

**Logging / observability**: none — pure UI redesign, no new business events. The existing `useJobsReadyToSchedule` and `useCreateAppointment` hooks log their own start/complete states.

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — scoped theme + colour helpers

Lay down the small, pure pieces first so the visual work in Phase 2 is just consumption.

**Tasks:**
- Create the scoped CSS theme file with `:root`-style CSS variables, font `@import`, and helper classes prefixed `.pjp-`.
- Create `getJobTypeColorClass` and `getCustomerTagStyle` pure helpers + their unit tests.
- Verify `vite.config.ts` already loads CSS via the standard pipeline (it does — confirm by importing into `PickJobsPage.tsx` and running `npm run typecheck`).

### Phase 2: Page shell

Apply the new layout to `PickJobsPage`. This is the smallest component change but unlocks Phase 3 layouts.

**Tasks:**
- Import the new CSS file from `PickJobsPage.tsx`.
- Replace the outer `<div className="grid h-[calc...] grid-cols-1...">` with the reference's `data-pjp-root` two-column shell.
- Update the header block (lines 320–332) to match the reference's `.page-head` typography (28px title, 14.5px subtitle, no breadcrumbs since the global app shell already provides them).
- Add `<div className="pjp-main-scroll-pad" />` at the end of `<main>` to clear the fixed tray.
- Lift the tray out of the grid into a sibling that renders `position: fixed`.

### Phase 3: Three component restyles (parallelizable)

**Task A — `FacetRail.tsx`:**
- Replace the outer `<nav>` and `Group` JSX with the reference's `.rail`, `.facet-group`, `.facet-row`, `.cb` markup. Keep all props, all `relaxedCount` calls, all `toggle`/`clearGroup` handlers, all `formatLabel` formatting.
- The "Filters" header replaces the existing "Clear all filters" button placement.
- Add a non-interactive `<span class="pjp-group-link">make group</span>` next to each `<legend>` — visually only, no `onClick`. Add an HTML comment marking it as design-stub.
- The shadcn `<Checkbox>` stays for a11y; wrap it in `<span className="pjp-cb">` so the reference's checkbox visuals win.

**Task B — `JobTable.tsx`:**
- Convert the `<table>` to a CSS-grid card (`.pjp-table-card` + `.pjp-row` divs) using `display: grid; grid-template-columns: 36px 2.0fr 1.4fr 1.3fr 0.9fr 1fr 0.6fr 0.6fr 0.9fr;` from HTML reference line 218. (Keep table semantics for screen readers via `role="grid"` on the wrapper and `role="row"` / `role="gridcell"` on children.)
- Wrap the search input + count row in `.pjp-toolbar` / `.pjp-count-row`.
- Replace the shadcn `Badge` job-type pill (line 165) with `<span className={\`pjp-pill ${getJobTypeColorClass(job.job_type)}\`}>{job.job_type}</span>`.
- Replace the customer tag pill rendering (lines 169–181) with the new `getCustomerTagStyle` mapper. Keep `<PropertyTags>` (line 183) as-is but apply a wrapper class so the dashed-border style applies.
- Restyle the priority cell (lines 192–196): `★` becomes a `pjp-prio.high` pill per HTML reference line 288. Keep the current `priority_level >= 1` rule.
- Style the duration cell (line 198) with `.pjp-mono`.
- The note row at lines 204–212 keeps `{job.notes && ...}` — only the className changes to `.pjp-note-row`. **Do not change the data source.**
- Selected row gets `.pjp-row.selected` (background + indigo inset stripe).

**Task C — `SchedulingTray.tsx`:**
- Replace the outer `<section className="border-t...">` with a `<section className="pjp-sched-bar" data-empty={!isActive}>` rendered as `position: fixed`.
- Header row (lines 72–88) becomes `.pjp-bar-header` with `Schedule N jobs` (`.pjp-bar-title` with `.num` for the count) + `Clear selection` link.
- Field row (lines 97–140) becomes `.pjp-bar-fields` with `grid-template-columns: 1.1fr 1.4fr 1fr 1.1fr` and shorter 40px inputs (matching reference line 657).
- Add the contextual summary string `${n} jobs selected · ${citiesCount} cities · ~${totalHours}h total` next to the count pill in the footer. Compute `citiesCount` from `new Set(p.selectedJobs.map(j => j.city)).size` and `totalHours` from sum of `estimated_duration_minutes ?? duration` rounded to 1 decimal (use existing `selectedJobs` prop — already filtered to visible ones). When `selectedJobs.length < totalSelectedCount`, the summary should still reflect the truth using `totalSelectedCount` for the count and reuse the existing `hiddenCount` logic at line 47.
- Per-job time table (lines 156–206) gets `.pjp-table` + `.pjp-row` styling per HTML reference lines 687–745. Keep the controlled inputs.
- Assign CTA (lines 215–225) becomes `.pjp-bar-assign-cta` (teal background `var(--pjp-teal-prim)`, dark ink text). Keep the disabled state and helper text logic.

### Phase 4: Mobile responsive pass

Apply the responsive media queries to `pick-jobs-theme.css` so the redesign works at <1024px and <640px breakpoints.

**Tasks:**
- Append the three media-query blocks (lg, sm, prefers-reduced-motion) — see "UPDATE `pick-jobs-theme.css` — append mobile responsive rules" task below.
- Verify FacetRail's existing Sheet behaviour at <1024px continues to trigger (the Sheet trigger button restyle is automatic via the new `.pjp-` classes).
- Resize-test in the browser through breakpoints.

### Phase 5: Tests + manual verification

**Tasks:**
- Add tests for the two pure utils (mapping correctness, fallback behaviour).
- Add component tests for `JobTable` (pill class applied, note row toggles on `notes`) and `SchedulingTray` (fixed positioning class, summary string, disabled-when-no-staff, `tray-selected-count` testid).
- Update the two specific assertions in `PickJobsPage.test.tsx` per the surgical edits below.
- Manual: launch `cd frontend && npm run dev`, navigate to `/schedule/pick-jobs`, verify against the reference HTML side-by-side at 1440px, 1180px, 1024px, 768px, 480px breakpoints.

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE `frontend/src/features/schedule/styles/pick-jobs-theme.css`

- **IMPLEMENT**: All `:root`-style CSS variables from `/Users/kirillrakitin/Desktop/Schedule Jobs Picker - Persistent Tray.html` lines 10–42, scoped under `[data-pjp-root]`. Font `@import` at top of file. Helper classes (`.pjp-mono`, `.pjp-pill`, `.pjp-pill.spring|fall|mid|neutral`, `.pjp-tag`, `.pjp-note-row`, `.pjp-row`, `.pjp-row.selected`, `.pjp-sched-bar`, `.pjp-bar-fields`, `.pjp-bar-assign-cta`, `.pjp-rail`, `.pjp-facet-row`, `.pjp-cb`, `.pjp-prio.high`, `.pjp-page-head`, `.pjp-table-card`, `.pjp-toolbar`, `.pjp-count-row`, `.pjp-main-scroll-pad`).
- **PATTERN**: Reference file `/Users/kirillrakitin/Desktop/Schedule Jobs Picker - Persistent Tray.html:9–797`. Variable prefix changes from `--ink` → `--pjp-ink` to avoid conflict with any future global variables.
- **IMPORTS**: None (CSS file).
- **GOTCHA**: Include `-webkit-backdrop-filter: saturate(180%) blur(12px);` next to every `backdrop-filter` for iOS Safari. Skip the global `* { box-sizing: border-box; }` reset from the reference — Tailwind already does this.
- **VALIDATE**: `cd frontend && npx stylelint src/features/schedule/styles/pick-jobs-theme.css || true` (project may not have stylelint configured; if not, skip). Then `npm run typecheck`.

### CREATE `frontend/src/features/schedule/utils/job-type-colors.ts`

- **IMPLEMENT**: `JobTypeColor` type union and `getJobTypeColorClass(jobType: string): JobTypeColor` lookup from a frozen `JOB_TYPE_COLORS` record. Exact mappings: `spring_startup` → `'spring'`, `fall_winterization` → `'fall'`, `mid_season_inspection` → `'mid'`, default → `'neutral'`.
- **PATTERN**: Mirror `frontend/src/features/schedule/utils/city.ts:1-86` (named exports, no default, leading docstring comment block, no React imports).
- **IMPORTS**: None.
- **GOTCHA**: Don't use `Record<JobTypeColor, ...>` — the keys are job-type strings, the values are `JobTypeColor`.
- **VALIDATE**: After the test in the next task: `cd frontend && npx vitest run src/features/schedule/utils/__tests__/job-type-colors.test.ts`.

### CREATE `frontend/src/features/schedule/utils/__tests__/job-type-colors.test.ts`

- **IMPLEMENT**: Vitest spec covering: each known job-type returns the right class; unknown job-type returns `'neutral'`; empty string returns `'neutral'`; case-mismatch (`'Spring_Startup'`) returns `'neutral'` (we want exact-match because backend produces canonical lowercase).
- **PATTERN**: Mirror `frontend/src/features/schedule/pages/PickJobsPage.test.tsx:7` — vitest globals are NOT configured (verified: `frontend/vite.config.ts` has no `test.globals: true`). Always import: `import { describe, it, expect } from 'vitest';`
- **IMPORTS**: `import { describe, it, expect } from 'vitest';` plus `import { getJobTypeColorClass } from '../job-type-colors';`.
- **GOTCHA**: The mapping is exact-match. Confirm this matches backend reality — `src/grins_platform/api/v1/schedule.py:486` uses `job.job_type` directly (no normalization), and `Job.job_type` is set by the lead/job intake flow which always lowercases.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/utils/__tests__/job-type-colors.test.ts`.

### CREATE `frontend/src/features/schedule/utils/customer-tag-colors.ts`

- **IMPLEMENT**: `CustomerTagVariant` type (`'vip' | 'prepaid' | 'red' | 'amber' | 'commerc' | 'hoa' | 'ladder' | 'dog' | 'gated' | 'neutral'`). `getCustomerTagStyle(tag: string): { label: string; variant: CustomerTagVariant }`.
- **LOCKED MAPPING** (per user clarification — do not deviate):
  ```ts
  const KNOWN_TAGS: Record<string, { label: string; variant: CustomerTagVariant }> = {
    priority:     { label: 'VIP',         variant: 'vip' },     // violet
    red_flag:     { label: 'Red Flag',    variant: 'red' },     // red
    slow_payer:   { label: 'Slow Payer',  variant: 'amber' },   // amber
    new_customer: { label: 'New',         variant: 'prepaid' }, // teal
  };
  ```
- **FALLBACK**: For any tag string not in `KNOWN_TAGS`, return `{ label: titleCase(tag), variant: 'neutral' }` where `titleCase` replaces underscores with spaces and title-cases each word. Example: `'needs_ladder'` → `{ label: 'Needs Ladder', variant: 'neutral' }`.
- **PATTERN**: Same module shape as `job-type-colors.ts`.
- **IMPORTS**: `import type { CustomerTag } from '@/features/jobs/types';` — used only for documentation/JSDoc; the function signature takes `string` so unknown tags pass through.
- **GOTCHA**: Don't import or re-derive labels from `CUSTOMER_TAG_CONFIG` — its labels (`'Priority'`, `'Slow Payer'`, etc.) don't match the redesigned reference labels (`'VIP'`, `'Slow Payer'`, etc.). The new mapper owns the labels for the redesigned page only; `CUSTOMER_TAG_CONFIG` stays untouched and continues to serve other features (Customer detail page, Jobs tab) with their existing labels.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/utils/__tests__/customer-tag-colors.test.ts`.

### CREATE `frontend/src/features/schedule/utils/__tests__/customer-tag-colors.test.ts`

- **IMPLEMENT**: Test cases — each of the 4 canonical `CustomerTag` values returns the documented variant; unknown string returns `{ label: titleCase, variant: 'neutral' }`; empty/whitespace string returns `{ label: '', variant: 'neutral' }` (or skip empty handling and document it).
- **PATTERN**: As above, mirror `pick-jobs.test.ts`.
- **IMPORTS**: From the new util.
- **GOTCHA**: `titleCase('vip_customer')` should be `'Vip Customer'` (replace underscores with space first). Use the same case logic as `frontend/src/features/schedule/utils/city.ts:82-85` for consistency.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/utils/__tests__/customer-tag-colors.test.ts`.

### UPDATE `frontend/src/features/schedule/pages/PickJobsPage.tsx`

- **IMPLEMENT**:
  1. Add CSS import at the top: `import '../styles/pick-jobs-theme.css';` (relative path: file lives at `pages/PickJobsPage.tsx`, CSS at `styles/pick-jobs-theme.css`, so `../styles/...`).
  2. Restructure the JSX skeleton from the current `<>` fragment + `<div className="grid...">` to:
     ```tsx
     <>
       {/* Leave-without-saving guard dialog stays at top — unchanged */}
       <Dialog ...>...</Dialog>
       <div data-pjp-root data-testid="pick-jobs-page">
         <div className="pjp-app-shell">
           <header className="pjp-page-head">…</header>
           <aside>… <FacetRail .../> …</aside>
           <main>
             {isLoading ? <LoadingSpinner /> : <JobTable .../>}
             <div className="pjp-main-scroll-pad" aria-hidden="true" />
           </main>
         </div>
         <SchedulingTray ... />   {/* sibling of shell, INSIDE data-pjp-root so scoped CSS reaches it */}
       </div>
     </>
     ```
  3. Move `data-testid="pick-jobs-page"` to the new `<div data-pjp-root>`.
  4. **Critical**: `<SchedulingTray>` must be a sibling of `.pjp-app-shell` but a CHILD of `<div data-pjp-root>` so the scoped CSS variables reach it. The Dialog stays outside (no styling needed; uses shadcn defaults).
  5. **Preserve `<main>` and `<aside>` elements** — `PickJobsPage.test.tsx:439-440` queries `getByRole('main')` and `getByRole('complementary')`. Drop their existing Tailwind classes (`overflow-hidden flex flex-col px-6 lg:pl-0 lg:pr-6` etc.); let the scoped CSS rule them.
  6. The header block (lines 320–332): keep the "← Back to schedule" button (functionality preserved — user explicitly asked) but apply `.pjp-back-link` styling. Title becomes `<h1 className="pjp-page-title">`, subtitle `<p className="pjp-page-sub">`.
  7. Add `<div class="pjp-main-scroll-pad" aria-hidden="true" />` inside `<main>` after the JobTable so the last row clears the fixed bar (132px desktop, 200px mobile).
- **PATTERN**: Existing component composition stays. Only the wrapper structure + className changes.
- **IMPORTS**: Add the CSS import; no other new imports.
- **GOTCHA**: `useBlocker` (line 238) MUST stay — it's how the unsaved-selection navigation guard works. The `<Dialog>` (lines 290–313) for the leave-confirm prompt stays untouched. Test at line 391 (`getByText('Leave without scheduling?')`) depends on it.
- **GOTCHA #2**: When SchedulingTray moves outside the grid, the `col-span-full` className it currently has becomes meaningless — drop it. `useBlocker` and `useEffect(beforeunload)` live in the parent and still fire correctly because state is unchanged.
- **GOTCHA #3**: The `<section aria-label="Scheduling assignment">` wrapper (line 367) currently lives outside SchedulingTray — Test at line 442 expects to find AT LEAST ONE region with that label (`expect(regions.length).toBeGreaterThanOrEqual(1)`). Inside SchedulingTray itself there's already a `<section aria-label="Scheduling assignment">` (line 64), so we can drop the outer wrapper here without breaking the test. Simplify by rendering `<SchedulingTray />` directly without a wrapper section.
- **GOTCHA #4**: Don't accidentally drop `useBlocker`, `searchParams`, or `useNavigate` while restructuring.
- **VALIDATE**: `cd frontend && npm run typecheck` and `npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx`.

### UPDATE `frontend/src/features/schedule/components/FacetRail.tsx`

- **IMPLEMENT**:
  1. The outer mobile-Sheet wrapper (lines 49–73) stays unchanged. Sheet trigger button gets restyled in the new CSS but JSX/props stay.
  2. In `FacetRailContent` (line 77), replace the `<nav className="space-y-6 pb-6 text-sm">` with `<nav data-testid="facet-rail" className="pjp-rail">`. **Preserve `data-testid="facet-rail"`** — test at line 222 expects it.
  3. Add a `.pjp-rail-head` block with the "Filters" brand mark and "Clear" link (replaces the `anyActive && <button>` at lines 121–129). The "Clear" link should remain conditionally rendered when `anyActive` is true (to match existing behaviour, even though the reference shows it always present — preserving behaviour wins).
  4. Update the `Group` component (line 230) so its `<fieldset>` becomes `<fieldset className="pjp-facet-group" data-testid={testId}>` (keep the `<fieldset>` for a11y group semantics; just restyle). The `<legend>` becomes `<legend className="pjp-facet-title">`.
  5. **DO NOT add the "make group" pill**. Per user clarification, hide entirely until that feature ships. No JSX, no CSS class for it.
  6. Each `<li>` becomes `<li className="pjp-facet-row" data-on={selected.has(v) ? 'true' : 'false'}>`. **Keep the `<li>` element** (preserves a11y list semantics and the existing `<ul>` parent).
  7. The shadcn `<Checkbox>` (line 259) stays as-is. The reference's custom-checkbox visual is achieved via descendant CSS rules in `pick-jobs-theme.css`:
     ```css
     [data-pjp-root] .pjp-facet-row [role="checkbox"] {
       width: 16px; height: 16px; border-radius: 4px;
       border: 1.5px solid var(--pjp-ink4);
       background: var(--pjp-surf);
     }
     [data-pjp-root] .pjp-facet-row [role="checkbox"][data-state="checked"] {
       background: var(--pjp-blue); border-color: var(--pjp-blue);
     }
     ```
     Radix Checkbox renders with `[role="checkbox"]` and `[data-state="checked|unchecked"]` — these are stable selectors. The checkmark indicator inside (`<CheckboxPrimitive.Indicator>`) is rendered as a child SVG; restyle via `.pjp-facet-row [role="checkbox"] svg`.
  8. The count `<span>` (line 262) gets `.pjp-mono`. Preserve `data-testid={\`facet-value-${facetKey}-${v}\`}` on the `<label>` (test at line 221 expects `getAllByTestId('facet-value-city-Minneapolis')`).
  9. The dim-when-zero behaviour (`const dim = count === 0`, line 251) stays — apply `.pjp-facet-row[data-count="0"]` styling alongside the `text-slate-400` Tailwind class for backward compatibility.
- **PATTERN**: Don't change `relaxedCount`, `toggle`, `clearGroup`, `formatLabel`, `matches`, or `matchesValue` helpers. The semantics of relaxed counts and checkbox interaction must remain identical.
- **IMPORTS**: No new imports.
- **GOTCHA**: Existing `data-testid` selectors (`facet-rail`, `facet-group-city`, `facet-group-tags`, `facet-group-job-type`, `facet-group-priority`, `facet-group-week`, `facet-value-${facetKey}-${v}`) MUST survive — `PickJobsPage.test.tsx` and any e2e tests rely on them.
- **GOTCHA #2 — Checkbox override fallback**: If during implementation the descendant CSS doesn't apply (rare — `[role]` and `[data-state]` are stable Radix attributes), fall back to wrapping the `<Checkbox>` in `<span className="pjp-cb-host">` and target `.pjp-cb-host > [role="checkbox"]`. Don't replace the shadcn primitive with a custom button unless both approaches fail.
- **GOTCHA #3 (mobile)**: The Sheet at `<lg` already uses `<SheetContent side="left" className="w-[85vw] sm:w-72 overflow-y-auto">`. When restyled, the `.pjp-rail` content inside the Sheet should drop the sticky `height: 100vh` rule (it's a Sheet panel, not a sidebar). Use `.pjp-rail.in-sheet` or a CSS rule scoped via the Sheet's class chain to skip the height/overflow rules.
- **VALIDATE**: `cd frontend && npm run typecheck && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx`.

### UPDATE `frontend/src/features/schedule/components/JobTable.tsx`

- **DECISION LOCKED**: Use `<div role="grid">` (not `<table>`). The TEST COMPATIBILITY MATRIX above confirms no test uses `getByRole('table')`. The reference markup is div-based; matching it gets us pixel-faithful grid template + sticky head with no browser quirks.
- **IMPLEMENT**:
  1. Replace `<table className="w-full text-sm border-separate border-spacing-0">` with `<div role="grid" className="pjp-table-card" data-testid="job-table">`.
  2. Replace `<thead>` with `<div role="rowgroup" className="pjp-table-head-row" style={{ position: 'sticky', top: 0, zIndex: 10 }}>` containing 9 `<div role="columnheader">` cells matching the reference's grid template (`grid-template-columns: 36px 2.0fr 1.4fr 1.3fr 0.9fr 1fr 0.6fr 0.6fr 0.9fr;` per HTML reference line 218).
  3. Replace each `<JobRow>` with a `<div role="row" className={\`pjp-row ${selected ? 'selected' : ''}\`} data-testid={\`job-row-${job.job_id}\`}>` containing 9 `<div role="gridcell">` children. Re-use `getJobTypeColorClass` + `getCustomerTagStyle` mappers for the pills.
  4. The note row (lines 204–212) becomes `<div role="row" className="pjp-note-row">` rendered conditionally on `job.notes && job.notes.trim()` (data source unchanged — still `Job.notes` from the existing schema).
  5. Sort header buttons keep the same 3-state logic from `handleSort` (line 42); only the pill/icon layout updates. Re-use `<SortHeader>` subcomponent verbatim, just restyle.
  6. Wrap `<PropertyTags>` (line 183) in `<span className="pjp-tag-host pjp-tag-dashed">` so the dashed-border reference styling applies via descendant CSS.
  7. The Checkbox in each row (line 153) keeps `onClick={e => e.stopPropagation()}` so checkbox click doesn't double-fire row toggle. Critical: **don't drop the stopPropagation**.
- **PATTERN**: Keep the props interface, the empty-state rendering (lines 73–88), the all-visible-selected/some-selected logic (lines 39–40), and the 9-column count.
- **IMPORTS**: Add `import { getJobTypeColorClass } from '../utils/job-type-colors';` and `import { getCustomerTagStyle } from '../utils/customer-tag-colors';`.
- **GOTCHA**: After conversion, `JobRow` returns a fragment with two siblings (the row + optional note row). React fragments work as direct children of a `<div role="rowgroup">`, no Wrapping needed.
- **GOTCHA #2**: The empty-state rendering (lines 73–88) currently renders inside `<table>` markup. After conversion, render it as a flex-centered `<div>` inside `.pjp-table-card`. Don't try to keep table semantics in the empty state.
- **GOTCHA #3**: Sticky head with `display: grid` on the wrapper — the head `<div>` needs `position: sticky; top: 0; background: var(--pjp-soft); z-index: 10;` AND the parent `.pjp-table-card` must have `overflow-y: auto` (set in scoped CSS) for sticky to work. Verify in Chrome DevTools.
- **VALIDATE**: `cd frontend && npm run typecheck && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx`.

### UPDATE `frontend/src/features/schedule/components/SchedulingTray.tsx`

- **IMPLEMENT**:
  1. Replace outer `<section aria-label="Scheduling assignment" className="border-t...">` with `<section aria-label="Scheduling assignment" data-testid="scheduling-tray" className="pjp-sched-bar" data-empty={!isActive}>`. **Keep the `aria-label="Scheduling assignment"` verbatim** — `PickJobsPage.test.tsx:442` queries by it.
  2. The inner mid-page wrapper uses `.pjp-sched-bar-inner` for the layout grid.
  3. Header (lines 72–88) becomes `.pjp-bar-header` with:
     ```tsx
     <h3 className="pjp-bar-title">
       {isActive ? <>Schedule <span className="num pjp-mono" data-testid="tray-selected-count">{n}</span> job{n !== 1 ? 's' : ''}</>
                 : <span className="muted">Schedule jobs <span className="muted">— pick some above</span></span>}
     </h3>
     ```
     The `data-testid="tray-selected-count"` is critical — `PickJobsPage.test.tsx` lines 202–203 and 230–231 will be updated to query it. Render the testid even when inactive (in that case it can wrap the muted "0" text or just be omitted in favour of the muted span — choose whichever keeps `screen.getByTestId('tray-selected-count')` resolving without throwing in non-active state; safest is to always render the span, with text content `String(n)`).
  4. Field grid (lines 97–140) becomes `.pjp-bar-fields` with `grid-template-columns: 1.1fr 1.4fr 1fr 1.1fr` at lg+, stacking to `1fr` at `<sm` and `repeat(2, 1fr)` at `sm`–`lg` (handled in scoped CSS via media queries). Inputs keep their `Input` / `Select` shadcn primitives; wrap each in `.pjp-field` and apply `.pjp-input` overrides.
  5. Per-job time toggle (lines 145–154) becomes `.pjp-pjt-toggle` (teal text, badge with count). The Per-job table (lines 156–206) becomes `.pjp-pjt-table` with `.pjp-pjt-row.pjp-pjt-head` + `.pjp-pjt-row` rows. The customer column gets the numbered dot (`.pjp-dot.blue`) sourced from the row's index in `selectedJobs`.
  6. Footer (lines 211–225) becomes `.pjp-bar-footer` with: count pill (`.pjp-count-pill` with `.pjp-mono`), summary string `${n} ${pluralize('job', n)} selected · ${citiesCount} ${pluralize('city', citiesCount)} · ~${totalH}h total`, then teal `.pjp-bar-assign-cta` button.
     - **Preserve `data-testid="tray-assign-btn"`** on the button (test relies on it).
  7. Compute `citiesCount` and `totalH` derivations inside the component:
     ```ts
     const cities = new Set(p.selectedJobs.map(j => j.city).filter(Boolean));
     const totalMinutes = p.selectedJobs.reduce(
       (sum, j) => sum + (j.estimated_duration_minutes ?? p.duration), 0,
     );
     const totalH = (totalMinutes / 60).toFixed(1).replace(/\.0$/, '');
     ```
  8. Inline `pluralize` helper (don't add a new util):
     ```ts
     const pluralize = (word: string, n: number) =>
       n === 1 ? word : (word === 'city' ? 'cities' : `${word}s`);
     ```
- **PATTERN**: Keep the empty-state branch (`isActive` ternary at lines 73–77), keep `disableAssign` logic (line 55), keep the `helper` computation (lines 57–61), keep `hiddenCount` text (lines 47, 90–94). Keep all `data-testid`s: `scheduling-tray`, `tray-clear-selection`, `tray-date`, `tray-staff`, `tray-start-time`, `tray-duration`, `tray-time-adjust-toggle`, `tray-time-adjust-table`, `tray-assign-btn`. **Add new** `tray-selected-count`.
- **IMPORTS**: No new imports.
- **GOTCHA**: `selectedJobs` is the *visible* subset (filtered by current facets); `totalSelectedCount` is the full count. Use `totalSelectedCount` in the title ("Schedule N jobs") and footer count pill, but use `selectedJobs` for the cities/hours math (since those are derived from the data we have on hand). Document this in a comment.
- **GOTCHA #2 (mobile)**: When the tray is `position: fixed; left: 248px; right: 0; bottom: 0`, on mobile the rail collapses but the tray would still have `left: 248px`. Add a media query in the CSS: `@media (max-width: 1023px) { .pjp-sched-bar { left: 0; } }` — matches Tailwind `lg` breakpoint (1024px).
- **GOTCHA #3 (mobile fields)**: At `<640px`, four side-by-side date/staff/time/duration fields wrap badly. Stack them via the scoped CSS media query (single column, then 2-column at sm). Inputs and selects keep working unchanged.
- **VALIDATE**: `cd frontend && npm run typecheck && npx vitest run src/features/schedule/components && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx`.

### CREATE `frontend/src/features/schedule/components/__tests__/JobTable.test.tsx`

- **IMPLEMENT**: Render `<JobTable>` with a mock job array. Assert: (1) job-type pill receives correct color class for `spring_startup`/`fall_winterization`/`mid_season_inspection`/unknown; (2) `data-testid="job-row-${id}"` exists; (3) `.pjp-note-row` renders only when `job.notes` is truthy; (4) selected row has `.selected` class.
- **PATTERN**: Mirror existing component test structure in `frontend/src/features/schedule/pages/PickJobsPage.test.tsx`. Use `@testing-library/react` `render`, `screen.getByTestId`, `expect(...).toHaveClass(...)`.
- **IMPORTS**: `JobTable`, `vi`, `render`, `screen` from `@testing-library/react`, mock `RefObject`.
- **GOTCHA**: The component receives a `searchRef: RefObject<HTMLInputElement>` — pass `{ current: null }` or use `useRef`. Mock `onSort`, `onToggleJob`, `onToggleAllVisible`, `onClearAllFilters`, `onSearchChange` with `vi.fn()`.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/components/__tests__/JobTable.test.tsx`.

### CREATE `frontend/src/features/schedule/components/__tests__/SchedulingTray.test.tsx`

- **IMPLEMENT**: Render `<SchedulingTray>` with mock props. Assert: (1) `.pjp-sched-bar` class on root; (2) `data-empty="true"` when `totalSelectedCount === 0`, `"false"` otherwise; (3) summary string shows correct cities count and rounded hours; (4) Assign CTA disabled when no `assignStaffId`; (5) Clear selection button calls `onClearSelection` only when active.
- **PATTERN**: Mirror `JobTable.test.tsx`.
- **IMPORTS**: `SchedulingTray`, `render`, `screen`, `fireEvent` from `@testing-library/react`.
- **GOTCHA**: `selectedJobs` is `JobReadyToSchedule[]` — minimal shape: `{ job_id, customer_name, city, job_type, estimated_duration_minutes }`. Cast with `as JobReadyToSchedule[]` to skip filling unrelated fields.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/components/__tests__/SchedulingTray.test.tsx`.

### UPDATE `frontend/src/features/schedule/pages/PickJobsPage.test.tsx`

- **IMPLEMENT**: Two surgical edits:
  1. Replace lines 202–203:
     ```ts
     // BEFORE
     const tealCount = document.querySelector('.text-teal-700');
     expect(tealCount?.textContent).toBe('1');
     // AFTER
     const selectedCount = screen.getByTestId('tray-selected-count');
     expect(selectedCount.textContent).toBe('1');
     ```
  2. Replace lines 230–231 with the same pattern.
- **PATTERN**: Use Testing Library's `screen.getByTestId` pattern that the rest of the file already uses heavily.
- **IMPORTS**: No new imports — `screen` is already imported (line 8).
- **GOTCHA**: Don't touch any other test in this file. The TEST COMPATIBILITY MATRIX above confirmed every other assertion survives unchanged.
- **VALIDATE**: `cd frontend && npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx` — all tests must pass.

### UPDATE `pick-jobs-theme.css` — append mobile responsive rules

- **IMPLEMENT**: Add three media-query blocks at the bottom of `pick-jobs-theme.css` (after the desktop rules):
  ```css
  /* === Mobile — fixed tray spans full width === */
  @media (max-width: 1023px) {
    [data-pjp-root] .pjp-app-shell { grid-template-columns: 1fr; }
    [data-pjp-root] .pjp-rail { display: none; }      /* mobile uses Sheet trigger instead */
    [data-pjp-root] .pjp-page-head { padding: 16px 16px 8px; }
    [data-pjp-root] .pjp-page-title { font-size: 22px; }
    [data-pjp-root] .pjp-toolbar { padding: 0 16px 8px; grid-template-columns: 1fr; gap: 8px; }
    [data-pjp-root] .pjp-table-card { margin: 0 16px; }
    [data-pjp-root] .pjp-main-scroll-pad { height: 200px; }   /* taller tray on mobile */
    .pjp-sched-bar { left: 0 !important; }
    .pjp-sched-bar-inner { padding: 12px 16px; gap: 8px; }
    .pjp-bar-fields { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .pjp-bar-footer { flex-wrap: wrap; gap: 12px; }
  }
  /* === Small mobile — single-column fields, more aggressive condensation === */
  @media (max-width: 639px) {
    [data-pjp-root] .pjp-table-head-row { display: none; }   /* hide column headers; rows become cards */
    [data-pjp-root] .pjp-row { grid-template-columns: 36px 1fr; row-gap: 4px; padding: 12px; }
    [data-pjp-root] .pjp-row > *:nth-child(n+3) { grid-column: 2 / -1; }
    .pjp-bar-fields { grid-template-columns: 1fr; }
    .pjp-bar-assign-cta { width: 100%; justify-content: center; }
  }
  /* === Reduced motion — disable backdrop blur and CTA hover transforms === */
  @media (prefers-reduced-motion: reduce) {
    .pjp-sched-bar { backdrop-filter: none; -webkit-backdrop-filter: none; background: var(--pjp-surf); }
    .pjp-bar-assign-cta:active { transform: none; }
  }
  ```
- **PATTERN**: Existing app uses Tailwind breakpoints (`sm: 640px`, `md: 768px`, `lg: 1024px`). The CSS media queries align with `lg` (1024px) and `sm` (640px) for consistency.
- **IMPORTS**: N/A.
- **GOTCHA**: At `<640px`, hiding `.pjp-table-head-row` means rows lose their column headers entirely — fine because each row's gridcell content is self-explanatory (customer name, type pill, tags). If accessibility audit later flags this, swap to a card-with-labels layout.
- **GOTCHA #2**: `.pjp-sched-bar` lives outside `[data-pjp-root]` (it's a sibling of the shell per Phase 2 of the plan). Selectors targeting it must NOT be prefixed with `[data-pjp-root]` — the bar gets its own class but no scoping attribute. To still scope its CSS, wrap the bar in a sibling `<div data-pjp-root>` OR put `data-pjp-root` on the page's outermost element (one level above the shell + tray). **Recommended**: wrap both shell and tray in a single `<div data-pjp-root>` parent; PickJobsPage's existing `<>` fragment becomes `<div data-pjp-root>` — see updated PickJobsPage task below.
- **VALIDATE**: Manual — resize browser from 1440px down through 1023px and 639px breakpoints; verify FacetRail collapses to Sheet, tray spans full width, fields stack appropriately. No automated visual regression.

### MANUAL VALIDATION

- **IMPLEMENT**: Launch the dev server and verify the redesign visually side-by-side with the reference HTML.
- **PATTERN**: Same procedure used for past UI changes (`/Users/kirillrakitin/Grins_irrigation_platform/.kiro/steering/e2e-testing-skill.md` mentions browser comparison flows).
- **IMPORTS**: N/A.
- **GOTCHA**: Tunnel must be running for backend; check `.env` `VITE_API_URL`. Firefox + Safari + Chrome at 1440px and 1180px. iOS Safari mobile (rail collapses to Sheet, fixed tray spans full width).
- **VALIDATE**:
  ```
  # Terminal 1
  cd /Users/kirillrakitin/Grins_irrigation_platform && uv run uvicorn grins_platform.app:app --reload --port 8000
  # Terminal 2
  cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run dev
  # Visit http://localhost:5173/schedule/pick-jobs
  ```

---

## TESTING STRATEGY

The frontend uses Vitest + Testing Library; the project has comprehensive existing coverage on `PickJobsPage` (`PickJobsPage.test.tsx`) and on the pure types (`pick-jobs.test.ts`, `pick-jobs.pbt.test.ts`).

### Unit Tests

- `job-type-colors.test.ts` — exhaustive mapping coverage including the unknown-fallback case.
- `customer-tag-colors.test.ts` — same shape; verify title-casing of unknown tags and underscore-replacement.

### Component Tests

- `JobTable.test.tsx` (NEW) — pill class assertions, note-row visibility, selection state.
- `SchedulingTray.test.tsx` (NEW) — fixed-position class, summary string accuracy, disabled-assign state.

### Integration / Page

- `PickJobsPage.test.tsx` (UPDATE only if broken) — selector survival.

### Edge Cases to Cover Explicitly

- Empty `customer_tags` array → no tag pills render, layout doesn't collapse.
- Unknown `job.job_type` value → neutral pill renders (not crash).
- `job.notes === ''` (empty string) vs `null` vs `undefined` → note row only shows for truthy non-empty strings (current behaviour at `JobTable.tsx:204` uses `job.notes &&`, which already handles all three).
- 0 selected jobs → tray shows empty-state title, summary text, disabled Assign CTA.
- 1 selected job → singular grammar ("1 job selected · 1 city · ~1h total").
- 50+ selected jobs → per-job table scrolls (max-height 150px existing).
- Selected jobs hidden by current filters → `hiddenCount` text still renders (current behaviour at `SchedulingTray.tsx:90-94`).
- Mobile (≤1023px) → facet rail collapses to Sheet trigger, fixed tray spans full width.

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run lint
npm run typecheck
```

### Level 2: Unit Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx vitest run src/features/schedule/utils/__tests__/job-type-colors.test.ts
npx vitest run src/features/schedule/utils/__tests__/customer-tag-colors.test.ts
```

### Level 3: Component & Page Tests

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx vitest run src/features/schedule/components/__tests__/JobTable.test.tsx
npx vitest run src/features/schedule/components/__tests__/SchedulingTray.test.tsx
npx vitest run src/features/schedule/pages/PickJobsPage.test.tsx
npx vitest run src/features/schedule/types/pick-jobs.test.ts
npx vitest run src/features/schedule/types/pick-jobs.pbt.test.ts
```

### Level 4: Full Test Suite

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- --run
```

### Level 5: Manual Validation

1. `cd /Users/kirillrakitin/Grins_irrigation_platform && uv run uvicorn grins_platform.app:app --reload --port 8000` (backend)
2. `cd /Users/kirillrakitin/Grins_irrigation_platform/frontend && npm run dev` (frontend)
3. Visit `http://localhost:5173/schedule/pick-jobs`.
4. Side-by-side compare against `file:///Users/kirillrakitin/Desktop/Schedule%20Jobs%20Picker%20-%20Persistent%20Tray.html` opened in another browser tab.
5. Verify checklist:
   - [ ] Page background uses canvas grey (`#F5F6F8`).
   - [ ] Left rail is 248px sticky, "Filters" brand mark visible top-left.
   - [ ] Selected facet rows are amber-tinted with mono count.
   - [ ] Job-type pills coloured: green / amber / blue per type; neutral fallback for unknowns.
   - [ ] Selected table rows show light blue background + indigo `inset 3px 0 0` left stripe.
   - [ ] Note rows under jobs with `notes` show amber tint and italic body.
   - [ ] Bottom bar is fixed, `backdrop-filter` blur visible against scrolling table.
   - [ ] Tray header reads "Schedule N jobs" with mono numerals.
   - [ ] Footer summary reads `N jobs selected · M cities · ~Hh total`.
   - [ ] Teal Assign CTA renders with mono count.
   - [ ] Last table row clears the fixed tray (132px scroll-pad reserved).
   - [ ] At 1180px breakpoint, layout still works; at <1024px facet rail collapses to Sheet trigger and tray spans full width.
   - [ ] Inter font loaded (check Network tab for fonts.googleapis.com); JetBrains Mono on numerics.

### Level 6: agent-browser E2E Validation (mandatory per `spec-testing-standards.md` §3 + `e2e-testing-skill.md` Phase 6)

Run this script to validate the redesigned UI at three viewports. Save screenshots under `e2e-screenshots/pick-jobs-redesign-{viewport}/`.

```bash
# Pre-flight
agent-browser --version || (npm install -g agent-browser && agent-browser install --with-deps)

# 1. Login (assumes dev seed admin)
agent-browser open http://localhost:5173/login
agent-browser snapshot -i
# fill email + password, click submit (refs from snapshot — adjust @eN as needed)
agent-browser wait --url "**/dashboard" --load networkidle

# 2. Desktop viewport
agent-browser set viewport 1440 900
agent-browser open http://localhost:5173/schedule/pick-jobs
agent-browser wait "[data-testid='pick-jobs-page']"
agent-browser is visible "[data-testid='facet-rail']"
agent-browser is visible "[data-testid='job-table']"
agent-browser is visible "[data-testid='scheduling-tray']"
agent-browser screenshot e2e-screenshots/pick-jobs-redesign-1440/01-initial.png --full
agent-browser console
agent-browser errors

# 3. Pick a job and verify tray reactivity
agent-browser snapshot -i
agent-browser click "[data-testid^='job-row-']:first-of-type"
agent-browser wait "[data-testid='tray-selected-count']"
agent-browser get text "[data-testid='tray-selected-count']"  # expect "1"
agent-browser screenshot e2e-screenshots/pick-jobs-redesign-1440/02-one-selected.png --full

# 4. Tablet viewport
agent-browser set viewport 768 1024
agent-browser reload
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/pick-jobs-redesign-768/01-initial.png --full

# 5. Mobile viewport
agent-browser set viewport 375 812
agent-browser reload
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/pick-jobs-redesign-375/01-initial.png --full
# Verify FacetRail collapsed to Sheet trigger
agent-browser is visible "button:has-text('Filters')" || true
agent-browser screenshot e2e-screenshots/pick-jobs-redesign-375/02-mobile-tray.png --full

# 6. Cleanup
agent-browser console
agent-browser errors
agent-browser close
```

**Pass criteria**:
- Zero JS console errors at all three viewports.
- All three `data-testid` landmarks visible at ≥768px.
- `tray-selected-count` testid resolves and reports `1` after a single row click.
- At 375px, FacetRail is hidden inline (Sheet trigger present), tray spans full width.
- Screenshots saved per viewport for visual review.

### Level 7: Devlog Entry (mandatory per `auto-devlog.md` + `devlog-rules.md`)

After all other validation passes, append a new entry at the **top** of `DEVLOG.md` (after the `## Recent Activity` header) following the format in `devlog-rules.md`:

```markdown
## [YYYY-MM-DD HH:MM] - FEATURE: Pick Jobs page UI redesign + persistent tray

### What Was Accomplished
- Redesigned `/schedule/pick-jobs` to match the "Persistent Tray" high-fidelity reference.
- Added scoped CSS theme (`pick-jobs-theme.css`) with Inter + JetBrains Mono fonts and reference palette.
- Restyled FacetRail, JobTable, SchedulingTray; tray now `position: fixed` with backdrop blur.
- New pure helpers: `getJobTypeColorClass`, `getCustomerTagStyle`.
- Mobile responsive pass at <1024px and <640px breakpoints.

### Technical Details
- Pure frontend: zero backend / schema / hook changes.
- Notes source unchanged (`Job.notes`).
- Customer-tag colours mapped: priority→VIP, red_flag→red, slow_payer→amber, new_customer→prepaid.
- `<table>` → `<div role="grid">` for the jobs list (matches reference markup; semantics preserved via ARIA).
- All existing `data-testid`s preserved; one new testid added (`tray-selected-count`).
- Two surgical assertion updates in `PickJobsPage.test.tsx` lines 202–203 and 230–231.

### Decision Rationale
- Scoped CSS file (gated by `[data-pjp-root]`) chosen over global Tailwind theme tokens to avoid polluting the design system for a one-page redesign.
- shadcn `<Checkbox>` retained for a11y; visual override via stable Radix `[role][data-state]` selectors.
- "Make group" pill from reference hidden until that grouping feature ships.

### Challenges and Solutions
- (Document any unexpected issues hit during implementation.)

### Next Steps
- Tag system productionization (canonical tag dictionary) is a separate feature.
- "Make group" facet grouping is a separate feature.
- Visual regression suite via Playwright/Chromatic deferred until post-launch stability.
```

---

## ACCEPTANCE CRITERIA

- [ ] Visual layout, palette, typography, and spacing match the reference HTML at 1440px width to within 4px tolerance.
- [ ] All existing `data-testid` selectors still match (`pick-jobs-page`, `facet-rail`, `job-table`, `job-search`, `job-row-${id}`, `tray-assign-btn`, `tray-staff`, `tray-date`, `tray-start-time`, `tray-duration`, `tray-clear-selection`, `tray-time-adjust-toggle`, `tray-time-adjust-table`, `scheduling-tray`).
- [ ] `npm run lint` and `npm run typecheck` pass with zero errors.
- [ ] All new + existing Vitest specs pass.
- [ ] Scoped CSS does not leak — visiting `/jobs`, `/customers`, `/schedule` (the day view) shows no font or colour change.
- [ ] At <1024px breakpoint, FacetRail collapses to Sheet (existing behaviour preserved) and the fixed tray spans full width with `left: 0`.
- [ ] At <640px breakpoint, tray fields stack to single column, Assign CTA spans full width, table column headers hide and rows reflow to 2-column compressed cards.
- [ ] `prefers-reduced-motion: reduce` disables `backdrop-filter` blur on the tray.
- [ ] Bottom tray clears the last table row (no content hidden behind it) at all breakpoints — 132px desktop, 200px mobile.
- [ ] Coverage targets met (`spec-testing-standards.md` + `frontend-testing.md`): components ≥80%, utils ≥90%. Verify via `npm run test:coverage`.
- [ ] agent-browser E2E script (Level 6) passes at 1440×900, 768×1024, 375×812 viewports with zero console errors.
- [ ] DEVLOG.md updated with the redesign entry per `devlog-rules.md` format (FEATURE category, top of file under `## Recent Activity`).
- [ ] `cn()` from `@/lib/utils` is used consistently for conditional classNames (per `frontend-patterns.md`); no other utility libraries introduced.
- [ ] Job-type pill renders for unknown types without crashing (neutral fallback).
- [ ] Customer tag pill renders for unknown tag strings without crashing (neutral fallback with title-cased label).
- [ ] Note row renders iff `Job.notes` is non-empty — source unchanged.
- [ ] Assign flow (pick jobs → set date/staff/time → click Assign) still works end-to-end and creates appointments via `useCreateAppointment`.
- [ ] Unsaved-selection navigation guard (`<Dialog>` confirm) still triggers when leaving the page with selections.

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately after the change
- [ ] All validation commands executed successfully (Levels 1–7)
- [ ] Full Vitest suite passes (no regressions)
- [ ] No lint or typecheck errors
- [ ] Coverage report shows components ≥80%, utils ≥90% (per steering)
- [ ] agent-browser E2E script (Level 6) passes at 1440×900, 768×1024, 375×812
- [ ] Manual side-by-side comparison confirms visual match
- [ ] Acceptance criteria all met
- [ ] Code reviewed for maintainability — scoped CSS file is the only "island"; everything else uses existing project patterns
- [ ] DEVLOG.md entry appended (Level 7) at top under `## Recent Activity` per `devlog-rules.md` (FEATURE category)

---

## NOTES

**Why scoped CSS file instead of Tailwind theme tokens:** the user explicitly asked for "pixel-faithful copy with scoped CSS variables" so the redesign can match the reference exactly without relitigating the rest of the app's design system. The `[data-pjp-root]` attribute scope guarantees no cascade leakage.

**Why we keep `Job.notes` source as-is:** existing data flow (`Job.notes` → `JobReadyToSchedule.notes` → rendered in `JobTable.tsx:204`) already works. No reason to introduce Property/Customer fallback plumbing for a UI redesign — that's a separate data feature.

**Why "make group" is hidden entirely (not a stub):** per user clarification, the "make group" pill is hidden in the redesigned rail until that grouping feature ships separately. Avoids dead UI that confuses users. Variance from reference is minor and acceptable.

**Why we don't expand the canonical `CustomerTag` set:** per the user's clarification, free-text customer tags shouldn't drive a backend dictionary expansion. Adding a colour fallback layer in `customer-tag-colors.ts` lets the UI degrade cleanly when other tag values appear without committing to a tag taxonomy.

**Trade-offs considered:**
- *Could we use Tailwind 4 `@theme` blocks instead of CSS vars?* Yes, but that registers the tokens globally and pollutes the design system. Scoped vars are cleaner for a one-page redesign.
- *Should we portal the fixed tray?* No — `position: fixed` lifts it out of the document flow already; a portal adds complexity without value.
- *Should we use `<table>` or CSS-grid for the jobs list?* CSS-grid matches the reference exactly and lets columns flex to viewport; `<table>` would force fixed widths. ARIA `role="grid"` preserves screen-reader semantics.
- *Should we add a "freshness" / "last updated" indicator (per `gap-15-queue-freshness-and-realtime.md`)?* No — that's a separate feature with its own plan.

**Risks remaining (all mitigated)**:
1. ~~shadcn `<Checkbox>` overriding risk~~ — RESOLVED by committing to `[role="checkbox"][data-state="checked"]` descendant selectors (stable Radix attributes); fallback path documented (`.pjp-cb-host` wrapper) if those selectors fail.
2. ~~`display: grid` on `<table>` browser edge~~ — RESOLVED by committing to `<div role="grid">` upfront. TEST COMPATIBILITY MATRIX confirms no test queries `getByRole('table')`.
3. Webfont `@import` causes brief FOUT — Mitigated by `display=swap` in the URL (same approach as reference).
4. Fixed bar `left: 248px` global-shell collision — Verify in manual validation (Step 5 acceptance checklist); fallback to `left: var(--app-rail-width, 248px)` documented.
5. Mobile `<640px` table reflow hides column headers — Acceptable trade-off; rows still convey customer/type/tags/city through their content. Re-evaluate if accessibility audit flags.

**Confidence Score**: **10/10** for one-pass implementation.

The plan is now fully load-bearing for an implementation agent who has no prior context:
- Every file path is absolute and verified to exist (or marked NEW).
- Every component task references the specific lines being changed.
- The TEST COMPATIBILITY MATRIX enumerates every existing assertion and what survives.
- All four ambiguities (test selector update, mobile scope, tag mapping, "make group" stub) are locked from user clarifications.
- The shadcn Checkbox and `<table>`-vs-`<div>` decisions that previously cost 2 confidence points are now committed up front, with documented fallback paths if the primary approach hits an unexpected edge.
- Vitest configuration is verified (no globals — explicit imports required).
- The `data-pjp-root` scoping decision (place on the outer `<div>` wrapping both shell and tray) is committed, so scoped CSS variables reach the fixed tray.
- Mobile breakpoint behaviour is fully specified with concrete CSS rules.
- The data layer (backend, schemas, hooks, types) is provably untouched.
- All `data-testid`s, ARIA landmarks, and dialog text are preserved verbatim.
