# Feature: Schedule-Visit Modal — Full High-Fidelity Redesign

> **Status**: Planning. Supersedes the narrow CTA-only refresh in `.agents/plans/schedule-visit-modal-ui-refresh-high-fidelity.md` (already shipped via commit `bf1df6c`).
> **Reference HTML**: `feature-developments/Schedule-Estimate-Visit-Reference.html` (lines 1–1088).
> **Scope**: Visual + structural redesign of the entire `ScheduleVisitModal`. No backend, schema, or business-logic changes.

The execution agent should validate documentation and codebase patterns before implementing, especially **classnames, types, and import paths**. Where the plan says "paste exactly," paste exactly; where it says "MIRROR," look up the referenced file:line first.

## Feature Description

The `ScheduleVisitModal` (booked from Sales pipeline → Stage 1 *Schedule estimate* → Now-card *Schedule visit*) currently uses a beige/parchment "cottagecore" aesthetic ported from an older reference. The new high-fidelity reference at `feature-developments/Schedule-Estimate-Visit-Reference.html` specifies a clean, professional, slate-on-white aesthetic that matches the rest of the app (Schedule tab, Appointment Modal v2, Sales pipeline list). This plan replaces the entire visual layer of the modal — header chrome, customer card, form fields, pick summary, conflict banner, week calendar, and legend — to match that reference, while leaving every hook, mutator, type, util, and API call untouched.

The CTA footer already matches the reference (shipped in commit `bf1df6c`); this plan does not modify it.

## User Story

As a **sales operator** scheduling an estimate visit from the pipeline detail screen,
I want **the modal to read as a clean, professional scheduling tool** — slate ink on white, lucide icons, mono numbers, tonal event cards, blue pick block —
So that **the scheduling action feels integrated with the rest of the platform** instead of standing out as a parchment-style anomaly, and the calendar's information density (assignee tone, conflict signaling, weekend tint, now-line) is read at a glance.

## Problem Statement

Three concrete gaps vs the reference:

1. **Modal chrome** — Current header is a plain title + description. Reference adds a stage pill (`Stage 1 · Schedule estimate`), a sales-entry ID pill (`SAL-1428`), and a tag pill (`New lead`). Title is heavier (22px / 800-weight). The close button is a 36×36 rounded icon button (currently inherited from `DialogContent`'s default top-right `XIcon`).
2. **Body layout** — Current layout is `grid-cols-[340px_1fr]` with no column tinting; reference is `grid-cols-[360px_1fr]` with the left column on a soft-gray surface (`#F9FAFB`) separated by a vertical 1px slate-200 border, and the right column on white. Customer card uses a beige amber-50 surface with dashed slate-700 border; reference uses a clean white card with subtle border + small shadow, an avatar circle with initials, and lucide icons (Phone, Mail, MapPin, Briefcase) in each row.
3. **Calendar** — Current calendar uses parchment colors (`#fafaf6`, `#1a1a1a`, `#ffe066`, `#d4622a`, hatched striped event cards); reference uses clean slate/white surface, tone-based left-bordered event cards (blue/green/violet/amber/teal — matched to assignee), red dot+line for "now," a blue gradient pick block, kbd hints in the legend, and a 14px-rounded outer card. Pick summary card is missing the "Picked" pill, bold long date, mono time, and dur+assignee meta.

## Solution Statement

Edit **6 files** within `frontend/src/features/sales/components/ScheduleVisitModal/` plus the modal's parent component:

1. `ScheduleVisitModal.tsx` — restructure header (stage pill + ID pill + tag pill), wrap the body grid with the new soft-gray-left / white-right layout. Keep all hook calls, all sub-component prop wiring, and the footer (already matches).
2. `PrefilledCustomerCard.tsx` — full rewrite as a clean white card with avatar + name + Leads link + 4 icon rows.
3. `ScheduleFields.tsx` — adjust label styling, mono-font the date/time inputs, keep the Radix Select primitives.
4. `PickSummary.tsx` — full rewrite as a "Picked" card with bold long-date, mono time range, dur+assignee meta. Replace conflict banner styling.
5. `WeekCalendar.tsx` — restructure the header (week label + range, prev/Today/next pill nav), pass an assignee-tone prop on each event card, render kbd hints in the legend.
6. `ScheduleVisitModal.module.css` — full rewrite with the reference's color tokens, slot styling, day-head circle dnum (today blue), tone-based event left-borders, blue gradient pick block, drag dashed block, weekend tint, now-line, kbd style.

No new files. No new hooks. No new types. No new package additions. The existing `lucide-react` (already a direct dep) covers every icon used in the reference.

## Feature Metadata

**Feature Type**: Enhancement (UI redesign)
**Estimated Complexity**: Medium
**Primary Systems Affected**:
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/PrefilledCustomerCard.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleFields.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/PickSummary.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx`
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.module.css`

**Dependencies (all verified present, no installs required)**:
- `lucide-react@^0.562.0` — direct dep (`frontend/package.json`); `Phone`, `Mail`, `MapPin`, `Briefcase`, `ExternalLink`, `ChevronLeft`, `ChevronRight`, `X`, `AlertCircle`, `ArrowRight` all exported.
- `tailwindcss@^4.1.18` — CSS-based theme in `frontend/src/index.css`; `slate-*`, `blue-*`, `green-*`, `amber-*`, `red-*`, `violet-*`, `teal-*` all in scope.
- `@/components/ui/dialog` — already used; `DialogHeader`/`DialogFooter`/`DialogContent` accept className overrides.
- `@/components/ui/{input,label,textarea,select,button}` — already used.
- `@tanstack/react-query` — already wired through `useCustomer` for email lookup.

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE IMPLEMENTING

- `feature-developments/Schedule-Estimate-Visit-Reference.html` (full file, 1–1088) — Source of truth. Visual + behavior specification. Notable anchors:
  - Lines 10–39: CSS variable tokens (color tokens to translate to Tailwind classes).
  - Lines 64–101: `.modal`, `.modal-head`, `.icon-btn` shell.
  - Lines 102–117: `.pill` variants — `stage-pill` (orange), `id` (mono slate), `tag-blue/green/violet`.
  - Lines 119–168: `.modal-body` two-column grid + `.cust` customer card.
  - Lines 170–209: form inputs, selects with custom chevron.
  - Lines 228–273: pick summary card and conflict alert.
  - Lines 275–367: week calendar shell, grid, day headers, time gutters, slots, weekend, past.
  - Lines 374–457: now-line, event cards (tone variants), pick block (blue gradient), drag block.
  - Lines 469–499: legend with swatches and kbd hints.
  - Lines 614–795: HTML body (the literal markup the redesign mirrors).
  - Lines 802–813: seeded estimates with assignee tones — confirms tone is data-driven, not random.
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx` (entire 185-line file) — Currently wires `useScheduleVisit` to four sub-components. The redesign keeps the wiring; only the JSX shell + DialogHeader content changes.
- `frontend/src/features/sales/components/ScheduleVisitModal/PrefilledCustomerCard.tsx` (entire 50-line file) — Currently amber-50 / dashed-slate-700 surface with text-only rows. Full rewrite.
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleFields.tsx` (entire 167-line file) — Inputs already use shadcn `Input`/`Textarea`/`Select`; only label styling, mono on date/time, and a `font-mono` className on the time input change.
- `frontend/src/features/sales/components/ScheduleVisitModal/PickSummary.tsx` (entire 50-line file) — Full rewrite to clean white card with "Picked" pill, bold long-date, mono time range, conflict alert with `AlertCircle` icon.
- `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx` (entire 357-line file) — Layout, behavior, drag math, slot data attributes, prop shape are unchanged. The header's nav buttons get pill styling, the legend gets kbd hints, and event cards opt into a tone via a derived prop. The CSS module supplies every visual change.
- `frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.module.css` (entire 231-line file) — Full rewrite. Tokens shift from parchment to slate/white.
- `frontend/src/features/sales/lib/scheduleVisitUtils.ts` (entire 122-line file) — Reads only. Constants (`HOUR_START=6`, `HOUR_END=20`, `SLOT_MIN=30`, `SLOT_PX=22`, `HEADER_PX=29`, `TIMECOL_PX=56`) drive the grid math. Reference HTML uses `HEADER_PX=44`, `TIMECOL_PX=64`. Bumping ours to match (Task 6 details below) is optional and behind one constants change.
- `frontend/src/features/sales/types/pipeline.ts` (lines 326–349) — `Pick`, `EstimateBlock`, `ScheduleVisitFormState` are stable; no changes.
- `frontend/src/features/sales/hooks/useScheduleVisit.ts` (entire 251-line file) — Reads only. The hook already exposes `pick`, `estimates` (each with `assignedToUserId: string | null`), `conflicts`, `hasConflict`, `setPickFromCalendarClick`, `setPickFromCalendarDrag`, `setWeekStart`, etc. The redesign needs the assignee-id-to-tone mapping (added inline at the call site, not in the hook).
- `frontend/src/components/ui/dialog.tsx` (entire 145-line file) — Critical lines:
  - Line 64: `DialogContent` adds `rounded-2xl shadow-xl overflow-hidden` and `sm:max-w-lg`. We override `max-w` and add `p-0` so our custom padded sections render edge-to-edge.
  - Line 70–79: built-in close button at `top-4 right-4`. We pass `showCloseButton={false}` and render our own 36×36 icon button to match the reference.
  - Line 89: `DialogHeader` adds `p-6 border-b border-slate-100 bg-slate-50/50`. We override to `bg-white border-slate-200 p-6 pt-5`.
  - Line 100: `DialogFooter` adds `p-6 border-t border-slate-100 bg-slate-50/50`. The current footer already lives inside this component; the existing CTA stays.
- `frontend/src/components/ui/button.tsx` (entire 63-line file) — Read-only reference. The svg sizing regex `[&_svg:not([class*='size-'])]:size-4` matters when we render `ChevronLeft`/`ChevronRight` inside the calendar nav (give them `size-3.5` to match the reference).
- `frontend/src/features/sales/components/NowCard.tsx` (line 10 lucide import; line 271 `bg-slate-900 text-white border-slate-900`) — Pattern reference for dark CTA + lucide icons in this feature.
- `frontend/src/features/sales/components/StageStepper.tsx` (line 106) — Pattern reference for `bg-slate-900 text-white` on the **today** day-header circle (mirror this for the reference's blue circle).
- `frontend/src/features/sales/lib/scheduleVisitUtils.ts:114-122` (`formatShortName`) — Used as-is for the pick block label.

### Files NOT to Touch

- `frontend/src/components/ui/{button,input,label,textarea,select,dialog}.tsx` — DO NOT modify shared shadcn primitives. Override at the call site via `className` only.
- `frontend/src/features/sales/hooks/useScheduleVisit.ts` — No state, mutator, or selector changes.
- `frontend/src/features/sales/lib/scheduleVisitUtils.ts` — Constants stay. The optional `HEADER_PX`/`TIMECOL_PX` bump (Task 6) is its own task, gated behind explicit instruction.
- `frontend/src/features/sales/types/pipeline.ts` — No type changes. The reference's `tone` for event cards is computed at render-time from `assignedToUserId`, not stored.
- `frontend/src/features/sales/api/salesPipelineApi.ts` — No API changes.
- The footer Confirm button in `ScheduleVisitModal.tsx` — Already matches reference; do not alter.

### New Files

None. This is a redesign that replaces the contents of existing files.

### Pre-Verified Repo Facts (no need to re-check)

| Item | Verified Value |
|---|---|
| Branch | `dev` (HEAD `bf1df6c` at time of plan write) |
| Frontend test runner | `vitest run` (script: `npm test`) |
| Frontend lint | `eslint .` (script: `npm run lint`) |
| Frontend typecheck | `tsc -p tsconfig.app.json --noEmit` (script: `npm run typecheck`) |
| `lucide-react` direct dep | `^0.562.0` — `Phone`, `Mail`, `MapPin`, `Briefcase`, `ExternalLink`, `ChevronLeft`, `ChevronRight`, `X`, `AlertCircle`, `ArrowRight` all available |
| Tailwind | `^4.1.18`; full default palette in scope. `bg-emerald-100`, `bg-teal-100`, `bg-violet-100`, `bg-amber-100`, `bg-blue-100`, `bg-orange-100`, `bg-red-100`, `bg-slate-50/100/200/300/400/500/600/700/800/900` all already used in `frontend/src/features/sales/` (e.g. `AgeChip.tsx`, `EstimateBuilder.tsx`, `EstimateDetail.tsx`) — no new utility classes are required |
| Baseline ESLint on touched dir | clean |
| Baseline `tsc` project-wide | already has 16 pre-existing errors in `src/shared/components/FilterPanel.tsx` and `src/shared/components/Layout.tsx` — these are NOT yours; ignore them |
| Existing `ScheduleVisitModal` tests | 9 tests in `ScheduleVisitModal.test.tsx`; all use `data-testid` selectors which the redesign preserves |
| Existing `WeekCalendar.test.tsx` | 5 tests at `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.test.tsx`. Asserts: `data-testid="schedule-visit-slot-0-0"` and `slot-6-27` (✓ preserved); a `[class*="today"]` element on the today day-header (✓ preserved — `styles.today` still applied); a `past` class on past slots (✓ preserved — `styles.past` still applied); the customer-name text on event blocks (✓ preserved — `styles.evtName` still rendered); `data-testid="schedule-visit-pick"` on the pick block (✓ preserved). **No edits to this test file are required.** |
| `formatShortName('Viktor Petrov')` | returns `'Viktor P.'` — confirmed at `scheduleVisitUtils.ts:114` |
| `useStaff` hook return shape | `{ data: { items: [{id, name}], total }, isLoading }` — confirmed in test mock |
| `useCustomer` hook | exported from `@/features/customers` (confirmed at `frontend/src/features/customers/index.ts:19`); signature `(id: string) => { data: Customer \| undefined, isLoading, error }`; `Customer.email: string \| null` (confirmed at `frontend/src/features/customers/types/customer.ts`) |
| `react-router-dom` | correct import path in this codebase. `Link` is imported from `react-router-dom` in 5 sales files (`SalesPipeline.tsx`, `SalesCalendar.tsx`, `EstimateDetail.tsx`, `FollowUpQueue.tsx`, `SalesCalendar.test.tsx`) and in `LeadDetail.tsx`. Do NOT use `react-router` (v7 dual-package) |
| Leads route | `/leads` (list) and `/leads/:id` (detail) both registered at `frontend/src/core/router/index.tsx:184` and `:188`. The customer-card lead link in this plan goes to `/leads/${entry.lead_id}` (the detail screen) |
| `track` util | `import { track } from '@/shared/utils/track'` — already used in `ScheduleVisitModal.tsx`; do not re-import |
| Radix Dialog a11y requirement | `DialogPrimitive.Content` warns in dev console without a `DialogTitle` and `DialogDescription` child. The redesign visually replaces the shadcn `DialogHeader`, but **must still render `DialogTitle` + `DialogDescription`** — apply with `className="sr-only"` so the a11y nodes exist while the visible header is the new bold h2 + p (Task 6 below does this) |

---

## Reference → Tailwind Token Map

The reference HTML uses CSS variables. Translate as follows. **Do not introduce a new CSS-variable theme; use Tailwind utility classes everywhere except the CSS module (which keeps raw hex values for grid math).**

| Reference var | Hex | Tailwind class |
|---|---|---|
| `--ink` | `#0B1220` | `text-slate-900` / `bg-slate-900` |
| `--ink2` | `#1F2937` | `text-slate-800` |
| `--ink3` | `#4B5563` | `text-slate-600` |
| `--ink4` | `#6B7280` | `text-slate-500` |
| `--ink5` | `#9CA3AF` | `text-slate-400` |
| `--line` | `#E5E7EB` | `border-slate-200` |
| `--line2` | `#F3F4F6` | `border-slate-100` / `bg-slate-100` |
| `--surf` | `#FFFFFF` | `bg-white` |
| `--soft` | `#F9FAFB` | `bg-slate-50` |
| `--paper` | `#F3F4F6` | (only on body — N/A inside modal) |
| `--blue` | `#1D4ED8` | `text-blue-700` / `bg-blue-700` (use `blue-700`, not `blue-600`) |
| `--blueBg` | `#DBEAFE` | `bg-blue-100` |
| `--blueBd` | `#93C5FD` | `border-blue-300` |
| `--orange` | `#C2410C` | `text-orange-700` |
| `--orangeBg` | `#FFEDD5` | `bg-orange-100` |
| `--orangeBd` | `#FDBA74` | `border-orange-300` |
| `--green` | `#047857` | `text-emerald-700` |
| `--greenBg` | `#D1FAE5` | `bg-emerald-100` |
| `--greenBd` | `#86EFAC` | `border-emerald-300` |
| `--amber` | `#B45309` | `text-amber-700` |
| `--amberBg` | `#FEF3C7` | `bg-amber-100` |
| `--amberBd` | `#FCD34D` | `border-amber-300` |
| `--red` | `#B91C1C` | `text-red-700` / `bg-red-700` |
| `--redBg` | `#FEE2E2` | `bg-red-100` |
| `--redBd` | `#FCA5A5` | `border-red-300` |
| `--violet` | `#6D28D9` | `text-violet-700` |
| `--violetBg` | `#EDE9FE` | `bg-violet-100` |
| `--violetBd` | `#C4B5FD` | `border-violet-300` |
| `--teal` | `#0F766E` | `text-teal-700` |
| `--tealBg` | `#CCFBF1` | `bg-teal-100` |

**Why `blue-700` (not `blue-600`)**: Reference's `#1D4ED8` is exactly Tailwind's `blue-700`. The codebase's existing dark-CTA convention is `slate-900`, but for the **week-calendar pick block + today day-header circle**, the reference is unambiguously blue-700; mirror it.

---

## STEP-BY-STEP TASKS

Execute in order, top to bottom. Each task is independently testable.

---

### Task 1 — REWRITE `ScheduleVisitModal.module.css`

**ACTION**: REWRITE the entire file.
**IMPLEMENT**: Replace parchment palette with reference's slate/white. Same class names (no JSX changes required).
**PATTERN**: Reference HTML lines 275–499 (`.wkcal*` and `.btn` not needed — we keep buttons in JSX).
**GOTCHA**: Class names below are CSS-Modules-export-named (camelCased). The JSX in `WeekCalendar.tsx` already references them as `styles.wkcal`, `styles.wkcalGrid`, `styles.wkcalDaycolHead`, `styles.today`, `styles.dow`, `styles.dnum`, `styles.wkcalTimecell`, `styles.wkcalSlot`, `styles.hour`, `styles.past`, `styles.wkcalNow`, `styles.wkcalEvt`, `styles.evtName`, `styles.evtMeta`, `styles.conflict`, `styles.wkcalPick`, `styles.warn`, `styles.pickDur`, `styles.wkcalDrag`, `styles.wkcalLegend`, `styles.legendSw`, `styles.pick`, `styles.wkcalHead`, `styles.wkLabel`, `styles.wkRange`, `styles.wkcalNav`, `styles.wkcalCorner`. **Preserve every class name; redefine bodies only.** Add new classes for `weekend`, `toneBlue`, `toneGreen`, `toneAmber`, `toneViolet`, `toneTeal`, `kbd`, `legendHint`, `legendSwPick`, `legendSwConflict`, `navIcon`, `navToday`.

**File contents** (paste exactly):

```css
/* Ported from feature-developments/Schedule-Estimate-Visit-Reference.html (high-fidelity reference). */

.wkcal {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

/* ── Header ── */
.wkcalHead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}
.wkLabel {
  font-size: 15px;
  font-weight: 700;
  color: #0b1220;
  letter-spacing: -0.01em;
  line-height: 1;
}
.wkRange {
  color: #6b7280;
  font-size: 11.5px;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  font-weight: 500;
  margin-left: 8px;
}
.wkcalNav {
  display: flex;
  gap: 4px;
  align-items: center;
}
.wkcalNav button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #1f2937;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.wkcalNav button:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}
.wkcalNav button.navIcon {
  padding: 0;
  width: 32px;
}
.wkcalNav button.navToday {
  background: #0b1220;
  color: #ffffff;
  border-color: #0b1220;
}
.wkcalNav button.navToday:hover {
  background: #1f2937;
}

/* ── Grid ── */
.wkcalGrid {
  position: relative;
  display: grid;
  grid-template-columns: 56px repeat(7, 1fr);
  grid-template-rows: 29px repeat(28, 22px);
  user-select: none;
  background: #ffffff;
}
.wkcalCorner {
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
}
.wkcalDaycolHead {
  padding: 6px 4px;
  text-align: center;
  border-right: 1px solid #e5e7eb;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}
.dow {
  color: #6b7280;
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.dnum {
  font-size: 14px;
  color: #1f2937;
  font-weight: 700;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  line-height: 1;
}
.wkcalDaycolHead.today .dow {
  color: #1d4ed8;
}
.wkcalDaycolHead.today .dnum {
  background: #1d4ed8;
  color: #ffffff;
}
.wkcalDaycolHead.weekend .dow {
  color: #9ca3af;
}
.wkcalDaycolHead.weekend .dnum {
  color: #6b7280;
}

.wkcalTimecell {
  padding: 0 6px 0 0;
  text-align: right;
  color: #9ca3af;
  font-size: 10px;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  font-weight: 500;
  border-right: 1px solid #e5e7eb;
  background: #ffffff;
  position: relative;
  top: -7px;
  line-height: 1;
}
.wkcalTimecell.hour {
  color: #6b7280;
}

.wkcalSlot {
  border-right: 1px solid #f3f4f6;
  border-bottom: 1px dashed #f3f4f6;
  cursor: cell;
  position: relative;
  transition: background 0.12s ease;
}
.wkcalSlot.hour {
  border-bottom: 1px solid #e5e7eb;
}
.wkcalSlot.weekend {
  background: rgba(243, 244, 246, 0.4);
}
.wkcalSlot.past {
  background: repeating-linear-gradient(
    135deg,
    transparent 0 4px,
    rgba(15, 23, 42, 0.03) 4px 5px
  );
  cursor: not-allowed;
}
.wkcalSlot:not(.past):hover {
  background: #dbeafe;
  opacity: 0.55;
}

/* ── Now-line ── */
.wkcalNow {
  position: absolute;
  height: 0;
  border-top: 2px solid #b91c1c;
  pointer-events: none;
  z-index: 4;
}
.wkcalNow::before {
  content: '';
  position: absolute;
  left: -5px;
  top: -5px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #b91c1c;
  box-shadow: 0 0 0 2px rgba(185, 28, 28, 0.15);
}

/* ── Existing estimate blocks ── */
.wkcalEvt {
  position: absolute;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-left: 3px solid #6b7280;
  border-radius: 6px;
  padding: 4px 6px;
  font-size: 10.5px;
  color: #1f2937;
  line-height: 1.2;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
  z-index: 1;
}
.evtName {
  font-weight: 700;
  color: #0b1220;
  font-size: 11px;
  letter-spacing: -0.01em;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.evtMeta {
  color: #6b7280;
  font-size: 10px;
  font-weight: 500;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}
.wkcalEvt.toneBlue   { border-left-color: #1d4ed8; }
.wkcalEvt.toneGreen  { border-left-color: #047857; }
.wkcalEvt.toneAmber  { border-left-color: #b45309; }
.wkcalEvt.toneViolet { border-left-color: #6d28d9; }
.wkcalEvt.toneTeal   { border-left-color: #0f766e; }
.wkcalEvt.conflict {
  border-color: #fca5a5;
  border-left-color: #b91c1c;
  background: #fee2e2;
}

/* ── Pick block ── */
.wkcalPick {
  position: absolute;
  background: linear-gradient(180deg, #1d4ed8, #1e40af);
  color: #ffffff;
  border: 2px solid #1d4ed8;
  border-radius: 8px;
  padding: 5px 7px;
  font-size: 11.5px;
  font-weight: 700;
  line-height: 1.2;
  box-shadow:
    0 4px 10px -2px rgba(29, 78, 216, 0.4),
    0 1px 2px rgba(15, 23, 42, 0.1);
  z-index: 3;
  pointer-events: none;
  overflow: hidden;
  letter-spacing: -0.01em;
}
.wkcalPick.warn {
  background: linear-gradient(180deg, #b91c1c, #991b1b);
  border-color: #b91c1c;
  box-shadow:
    0 4px 10px -2px rgba(185, 28, 28, 0.4),
    0 1px 2px rgba(15, 23, 42, 0.1);
}
.pickDur {
  font-weight: 500;
  font-size: 10px;
  opacity: 0.85;
  display: block;
  margin-top: 1px;
}

/* ── Drag ghost ── */
.wkcalDrag {
  position: absolute;
  background: rgba(29, 78, 216, 0.16);
  border: 2px dashed #1d4ed8;
  border-radius: 6px;
  pointer-events: none;
  z-index: 2;
}

/* ── Legend ── */
.wkcalLegend {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
  font-size: 11.5px;
  color: #6b7280;
  font-weight: 500;
}
.wkcalLegend > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legendSw {
  display: inline-block;
  width: 14px;
  height: 10px;
  border-radius: 3px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-left: 3px solid #6b7280;
  flex-shrink: 0;
}
.legendSw.pick {
  background: #1d4ed8;
  border: 2px solid #1d4ed8;
}
.legendSw.legendSwConflict {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  border-left: 3px solid #b91c1c;
}
.legendHint {
  margin-left: auto;
  color: #9ca3af;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.kbd {
  display: inline-block;
  padding: 1px 5px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-bottom-width: 2px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 10.5px;
  color: #1f2937;
  line-height: 1.4;
}
```

**VALIDATE Task 1**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
# CSS module compiles silently; confirm by running typecheck (it runs the bundler-aware tsc).
npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -E 'ScheduleVisitModal\.module\.css|sales/components/ScheduleVisitModal' | head -5 || echo "OK: no TS errors in ScheduleVisitModal area"
```

---

### Task 2 — REWRITE `WeekCalendar.tsx`

**ACTION**: REWRITE the entire file.
**IMPLEMENT**: Same behavior, prop shape, and drag math; add lucide chevron icons + assignee-tone derivation + kbd hints + weekend slot class.
**PATTERN**:
- Lucide icon import: `frontend/src/features/sales/components/NowCard.tsx:10`.
- `data-testid` pattern: `frontend/src/features/sales/components/ScheduleVisitModal/WeekCalendar.test.tsx` (preserve all existing testids).
**IMPORTS** (top of file):
```tsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { EstimateBlock, Pick } from '../../types/pipeline';
import {
  HOUR_START,
  HOUR_END,
  SLOT_MIN,
  SLOT_PX,
  HEADER_PX,
  TIMECOL_PX,
  SLOTS_PER_DAY,
  iso,
  isPastSlot,
  fmtHM,
  fmtMonD,
} from '../../lib/scheduleVisitUtils';
import styles from './ScheduleVisitModal.module.css';
```

**GOTCHA**:
- The `formatShortName` import is gone from `WeekCalendar.tsx` (it's used at the modal level, passed in as `pickCustomerName`). Don't reintroduce it here.
- `fmtLongDateD` is replaced by inline `weekStart`/`weekEnd` mon-day rendering on the header (`Apr 20 – 26, 2026`).
- The pick-block label format changes: reference HTML lines 970–973 render `<div class="pick-name">Viktor Petrov</div><div class="pick-when">{fmtHM(start)} – {fmtHM(end)}</div><div class="pick-dur">{fmtDur}</div>`. Mirror this — three lines, not two.

**Key structural changes** vs current file:
1. Header layout — reference uses `wk-label` + `wk-range` baseline-aligned, plus `prev | Today | next` pill nav. Current uses inline buttons.
2. Day-header — render the `dnum` inside a circular span (already present in CSS); add `weekend` class when `getDay() === 0 || 6`.
3. Slot — add `weekend` class on Sat/Sun slots.
4. Event card — derive a `tone` from `assignedToUserId` and apply the matching `styles.toneXxx` class.
5. Pick block — three lines (name, time-range, duration), not two.
6. Legend — add a `kbd` hint line: "Click pin start · Drag set range".

**File contents** (paste exactly):

```tsx
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { EstimateBlock, Pick } from '../../types/pipeline';
import {
  HOUR_START,
  HOUR_END,
  SLOT_MIN,
  SLOT_PX,
  HEADER_PX,
  TIMECOL_PX,
  SLOTS_PER_DAY,
  iso,
  isPastSlot,
  fmtHM,
  fmtMonD,
  fmtDur,
} from '../../lib/scheduleVisitUtils';
import styles from './ScheduleVisitModal.module.css';

type Props = {
  weekStart: Date;
  now: Date;
  estimates: EstimateBlock[];
  pick: Pick | null;
  loadingWeek: boolean;
  conflicts: EstimateBlock[];
  hasConflict: boolean;
  pickCustomerName: string;
  onWeekChange: (next: Date) => void;
  onSlotClick: (date: string, slotStartMin: number) => void;
  onSlotDrag: (date: string, startMin: number, endExclusiveMin: number) => void;
  onTrack?: (event: 'pick', source: 'click' | 'drag') => void;
};

type DragState = {
  dayIdx: number;
  startSlot: number;
  curSlot: number;
  moved: boolean;
};

// Stable assignee → tone mapping. The 5 reference tones cycle by hash of the
// assignee id so the same staff member gets the same tone across renders.
// Unassigned events keep the default slate left-border (no tone class).
const TONES = ['toneBlue', 'toneGreen', 'toneViolet', 'toneAmber', 'toneTeal'] as const;
function pickTone(assigneeId: string | null | undefined): string | null {
  if (!assigneeId) return null;
  let h = 0;
  for (let i = 0; i < assigneeId.length; i++) h = (h * 31 + assigneeId.charCodeAt(i)) >>> 0;
  const tone = TONES[h % TONES.length];
  return tone ? styles[tone] ?? null : null;
}

function fmtMonRange(a: Date, b: Date): string {
  const sm = a.toLocaleDateString('en-US', { month: 'short' });
  const em = b.toLocaleDateString('en-US', { month: 'short' });
  const y = b.getFullYear();
  if (sm === em) return `${sm} ${a.getDate()} – ${b.getDate()}, ${y}`;
  return `${sm} ${a.getDate()} – ${em} ${b.getDate()}, ${y}`;
}

export function WeekCalendar({
  weekStart,
  now,
  estimates,
  pick,
  loadingWeek,
  conflicts,
  hasConflict,
  pickCustomerName,
  onWeekChange,
  onSlotClick,
  onSlotDrag,
  onTrack,
}: Props) {
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, i) => {
        const d = new Date(weekStart);
        d.setDate(d.getDate() + i);
        return d;
      }),
    [weekStart],
  );
  const conflictIds = useMemo(
    () => new Set(conflicts.map((c) => c.id)),
    [conflicts],
  );
  const [drag, setDrag] = useState<DragState | null>(null);
  const dragRef = useRef<DragState | null>(null);
  useEffect(() => {
    dragRef.current = drag;
  }, [drag]);

  const onSlotMouseDown =
    (dayIdx: number, slotIdx: number) => (e: React.MouseEvent) => {
      e.preventDefault();
      const dayDate = days[dayIdx];
      if (!dayDate) return;
      const past = isPastSlot(
        dayDate,
        HOUR_START * 60 + slotIdx * SLOT_MIN,
        now,
      );
      if (past) return;
      setDrag({ dayIdx, startSlot: slotIdx, curSlot: slotIdx, moved: false });

      const onMove = (ev: MouseEvent) => {
        const target = (ev.target as HTMLElement | null)?.closest('[data-slot]');
        if (!target) return;
        const di = Number(target.getAttribute('data-day'));
        const si = Number(target.getAttribute('data-slot'));
        if (di !== dayIdx) return;
        const dd = days[dayIdx];
        if (!dd) return;
        if (isPastSlot(dd, HOUR_START * 60 + si * SLOT_MIN, now)) return;
        setDrag((d) =>
          d && d.curSlot !== si ? { ...d, curSlot: si, moved: true } : d,
        );
      };

      const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        const d = dragRef.current;
        if (!d) return;
        const dDate = new Date(weekStart);
        dDate.setDate(dDate.getDate() + d.dayIdx);
        const isoDate = iso(dDate);
        const s1 = Math.min(d.startSlot, d.curSlot);
        const s2 = Math.max(d.startSlot, d.curSlot) + 1;
        const startMin = HOUR_START * 60 + s1 * SLOT_MIN;
        const endMin = HOUR_START * 60 + s2 * SLOT_MIN;
        if (d.moved) {
          onSlotDrag(isoDate, startMin, endMin);
          onTrack?.('pick', 'drag');
        } else {
          onSlotClick(isoDate, startMin);
          onTrack?.('pick', 'click');
        }
        setDrag(null);
      };

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    };

  useEffect(() => {
    return () => {
      dragRef.current = null;
    };
  }, []);

  const goPrev = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() - 7);
    onWeekChange(d);
  };
  const goNext = () => {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + 7);
    onWeekChange(d);
  };
  const goToday = () => {
    const t = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const day = t.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    t.setDate(t.getDate() + diff);
    onWeekChange(t);
  };

  const colLeftPct = (i: number) =>
    `calc(${TIMECOL_PX}px + ${i} * ((100% - ${TIMECOL_PX}px) / 7))`;
  const colWidthPct = `calc((100% - ${TIMECOL_PX}px) / 7)`;
  const todayIdx = days.findIndex((d) => iso(d) === iso(now));
  const NOW_MIN = now.getHours() * 60 + now.getMinutes();
  const showNowLine =
    todayIdx >= 0 && NOW_MIN >= HOUR_START * 60 && NOW_MIN <= HOUR_END * 60;

  const blockTop = (startMin: number) =>
    HEADER_PX + ((startMin - HOUR_START * 60) / SLOT_MIN) * SLOT_PX;
  const blockHeight = (durMin: number) => (durMin / SLOT_MIN) * SLOT_PX - 3;

  const lastDay = days[6] ?? days[0] ?? weekStart;

  return (
    <div className={styles.wkcal} data-testid="schedule-visit-calendar">
      <header className={styles.wkcalHead}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, minWidth: 0 }}>
          <span className={styles.wkLabel}>Week of {fmtMonD(weekStart)}</span>
          <span className={styles.wkRange}>{fmtMonRange(weekStart, lastDay)}</span>
        </div>
        <div className={styles.wkcalNav}>
          <button
            type="button"
            className={styles.navIcon}
            onClick={goPrev}
            data-testid="schedule-visit-week-prev"
            aria-label="Previous week"
          >
            <ChevronLeft size={14} strokeWidth={2.5} />
          </button>
          <button
            type="button"
            className={styles.navToday}
            onClick={goToday}
            data-testid="schedule-visit-week-today"
          >
            Today
          </button>
          <button
            type="button"
            className={styles.navIcon}
            onClick={goNext}
            data-testid="schedule-visit-week-next"
            aria-label="Next week"
          >
            <ChevronRight size={14} strokeWidth={2.5} />
          </button>
        </div>
      </header>

      <div className={styles.wkcalGrid} aria-busy={loadingWeek}>
        <div className={styles.wkcalCorner} />
        {days.map((d, i) => {
          const isWeekend = d.getDay() === 0 || d.getDay() === 6;
          const isToday = iso(d) === iso(now);
          return (
            <div
              key={`h${i}`}
              className={[
                styles.wkcalDaycolHead,
                isToday ? styles.today : '',
                isWeekend ? styles.weekend : '',
              ].filter(Boolean).join(' ')}
            >
              <div className={styles.dow}>
                {d.toLocaleDateString('en-US', { weekday: 'short' })}
              </div>
              <div className={styles.dnum}>{d.getDate()}</div>
            </div>
          );
        })}

        {Array.from({ length: SLOTS_PER_DAY }).flatMap((_, s) => {
          const mins = HOUR_START * 60 + s * SLOT_MIN;
          const isHour = mins % 60 === 0;
          const cells: React.ReactNode[] = [
            <div
              key={`tg${s}`}
              className={`${styles.wkcalTimecell}${isHour ? ' ' + styles.hour : ''}`}
            >
              {isHour ? (() => {
                const h = Math.floor(mins / 60);
                const ap = h >= 12 ? 'p' : 'a';
                const h12 = ((h + 11) % 12) + 1;
                return `${h12} ${ap}`;
              })() : ''}
            </div>,
          ];
          days.forEach((d, di) => {
            const past = isPastSlot(d, mins, now);
            const isWeekend = d.getDay() === 0 || d.getDay() === 6;
            cells.push(
              <div
                key={`c${s}-${di}`}
                data-day={di}
                data-slot={s}
                data-testid={`schedule-visit-slot-${di}-${s}`}
                className={[
                  styles.wkcalSlot,
                  isHour ? styles.hour : '',
                  isWeekend ? styles.weekend : '',
                  past ? styles.past : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
                onMouseDown={past ? undefined : onSlotMouseDown(di, s)}
              />,
            );
          });
          return cells;
        })}

        {showNowLine && (
          <div
            className={styles.wkcalNow}
            style={{
              top: `${HEADER_PX + ((NOW_MIN - HOUR_START * 60) / SLOT_MIN) * SLOT_PX}px`,
              left: colLeftPct(todayIdx),
              width: colWidthPct,
            }}
          />
        )}

        {days.map((d, di) => {
          const dISO = iso(d);
          return estimates
            .filter((e) => e.date === dISO)
            .map((e) => {
              const toneCls = pickTone(e.assignedToUserId);
              return (
                <div
                  key={e.id}
                  className={[
                    styles.wkcalEvt,
                    toneCls ?? '',
                    conflictIds.has(e.id) ? styles.conflict : '',
                  ].filter(Boolean).join(' ')}
                  title={`${e.customerName} · ${fmtHM(e.startMin)}–${fmtHM(e.endMin)} · ${e.jobSummary}`}
                  style={{
                    top: `${blockTop(e.startMin)}px`,
                    height: `${blockHeight(e.endMin - e.startMin)}px`,
                    left: `calc(${colLeftPct(di)} + 3px)`,
                    width: `calc(${colWidthPct} - 6px)`,
                  }}
                >
                  <div className={styles.evtName}>{e.customerName}</div>
                  <div className={styles.evtMeta}>
                    {fmtHM(e.startMin)} · {e.jobSummary}
                  </div>
                </div>
              );
            });
        })}

        {pick &&
          (() => {
            const di = days.findIndex((d) => iso(d) === pick.date);
            if (di < 0) return null;
            return (
              <div
                data-testid="schedule-visit-pick"
                className={`${styles.wkcalPick}${hasConflict ? ' ' + styles.warn : ''}`}
                style={{
                  top: `${blockTop(pick.start)}px`,
                  height: `${blockHeight(pick.end - pick.start)}px`,
                  left: `calc(${colLeftPct(di)} + 3px)`,
                  width: `calc(${colWidthPct} - 6px)`,
                }}
              >
                <div>{pickCustomerName}</div>
                <div style={{ fontFamily: 'JetBrains Mono, ui-monospace, monospace', fontSize: 10.5, fontWeight: 600, opacity: 0.9, marginTop: 1 }}>
                  {fmtHM(pick.start)} – {fmtHM(pick.end)}
                </div>
                <span className={styles.pickDur}>{fmtDur(pick.end - pick.start)}</span>
              </div>
            );
          })()}

        {drag &&
          (() => {
            const s1 = Math.min(drag.startSlot, drag.curSlot);
            const s2 = Math.max(drag.startSlot, drag.curSlot) + 1;
            return (
              <div
                className={styles.wkcalDrag}
                style={{
                  top: `${HEADER_PX + s1 * SLOT_PX}px`,
                  height: `${(s2 - s1) * SLOT_PX - 3}px`,
                  left: `calc(${colLeftPct(drag.dayIdx)} + 3px)`,
                  width: `calc(${colWidthPct} - 6px)`,
                }}
              />
            );
          })()}
      </div>

      <footer className={styles.wkcalLegend}>
        <span>
          <span className={styles.legendSw} />
          Existing estimate
        </span>
        <span>
          <span className={`${styles.legendSw} ${styles.legendSwConflict}`} />
          Conflict
        </span>
        <span>
          <span className={`${styles.legendSw} ${styles.pick}`} />
          Your pick
        </span>
        <span className={styles.legendHint}>
          <span className={styles.kbd}>Click</span> pin start ·{' '}
          <span className={styles.kbd}>Drag</span> set range
        </span>
      </footer>
    </div>
  );
}
```

**VALIDATE Task 2**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/WeekCalendar.tsx
npm test -- WeekCalendar
# Expected: zero ESLint output; existing WeekCalendar tests still pass.
```

---

### Task 3 — REWRITE `PrefilledCustomerCard.tsx`

**ACTION**: REWRITE the entire file.
**IMPLEMENT**: Clean white card with avatar circle (initials from `customer_name`), name + "from Leads · LD-XXXX" link (when `lead_id` present), 4 icon rows.
**PATTERN**:
- Lucide icon imports: `frontend/src/features/sales/components/NowCard.tsx:10`.
- Avatar initials: derive from `customer_name`.
- Leads link: route to **`/leads/${entry.lead_id}`** — the lead-detail screen. Verified registered at `frontend/src/core/router/index.tsx:188` (`path: 'leads/:id'`). Existing `Link to="/leads"` patterns at `LeadDetail.tsx:442`, `LeadDashboardWidgets.tsx:70/98` confirm `react-router-dom`'s `Link` component is the import.
**IMPORTS**:
```tsx
import { Phone, Mail, MapPin, Briefcase, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCustomer } from '@/features/customers';
import type { SalesEntry } from '../../types/pipeline';
```

**GOTCHA**:
- Existing test at `ScheduleVisitModal.test.tsx:123-135` calls `expect(screen.getByTestId('schedule-visit-customer-card')).toHaveTextContent('Viktor Petrov')`. Preserve the testid and ensure the customer name is in the rendered text. ✅
- Phone + email rows must only render when present; `customer.email` comes from the cached customer detail query, so it may briefly be missing — that's acceptable (renders nothing for that row).
- Initials helper must handle 1-word names (e.g., "Cher" → "C").

**File contents** (paste exactly):

```tsx
import { Phone, Mail, MapPin, Briefcase, ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useCustomer } from '@/features/customers';
import type { SalesEntry } from '../../types/pipeline';

type Props = {
  entry: SalesEntry;
};

function initials(name: string | null | undefined): string {
  if (!name) return '—';
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const second = parts.length > 1 ? parts[parts.length - 1]?.[0] ?? '' : '';
  return (first + second).toUpperCase() || '—';
}

export function PrefilledCustomerCard({ entry }: Props) {
  const { data: customer } = useCustomer(entry.customer_id);
  const customerName = entry.customer_name ?? 'Unknown Customer';

  return (
    <section
      role="group"
      aria-label="Customer information"
      data-testid="schedule-visit-customer-card"
      className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.06)]"
    >
      <div className="flex items-start gap-2.5 mb-2.5">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-gradient-to-br from-slate-800 to-slate-600 text-[14px] font-bold tracking-tight text-white">
          {initials(customerName)}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="m-0 text-[15px] font-bold leading-[1.2] text-slate-900">
            {customerName}
          </h3>
          {entry.lead_id && (
            <div className="mt-0.5 inline-flex items-center gap-1 text-[11.5px] text-slate-500">
              <ExternalLink size={11} strokeWidth={2.5} />
              from{' '}
              <Link
                to={`/leads/${entry.lead_id}`}
                className="font-semibold text-blue-700 no-underline hover:underline"
              >
                Leads · LD-{entry.lead_id.slice(0, 4).toUpperCase()}
              </Link>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        {entry.customer_phone && (
          <Row icon={<Phone size={14} strokeWidth={2} />}>
            <a
              href={`tel:${entry.customer_phone}`}
              className="font-mono font-semibold text-slate-800 no-underline hover:underline"
            >
              {entry.customer_phone}
            </a>
          </Row>
        )}
        {customer?.email && (
          <Row icon={<Mail size={14} strokeWidth={2} />}>
            <a
              href={`mailto:${customer.email}`}
              className="font-medium text-slate-800 no-underline hover:underline"
            >
              {customer.email}
            </a>
          </Row>
        )}
        {entry.property_address && (
          <Row icon={<MapPin size={14} strokeWidth={2} />}>
            <span className="font-medium text-slate-800">{entry.property_address}</span>
          </Row>
        )}
        {entry.job_type && (
          <Row icon={<Briefcase size={14} strokeWidth={2} />}>
            <span className="font-semibold text-slate-800">{entry.job_type}</span>
          </Row>
        )}
      </div>
    </section>
  );
}

function Row({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[16px_1fr] items-center gap-2 text-[12.5px] text-slate-800">
      <span className="text-slate-400">{icon}</span>
      <span className="min-w-0 overflow-hidden text-ellipsis whitespace-nowrap">{children}</span>
    </div>
  );
}
```

**VALIDATE Task 3**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/PrefilledCustomerCard.tsx
# Expected: zero output.
```

---

### Task 4 — UPDATE `ScheduleFields.tsx`

**ACTION**: UPDATE (small changes, not a rewrite).
**IMPLEMENT**: Apply mono font to date/time inputs; tighten label colors; keep the Radix Select primitives.
**PATTERN**: Existing `<Input>` and `<Label>` primitives at `frontend/src/components/ui/input.tsx` and `label.tsx`.
**IMPORTS**: No new imports.
**GOTCHA**: Don't rewrite the file — just apply these three className edits. The existing `data-testid` attributes (`schedule-visit-date`, `schedule-visit-start-time`, `schedule-visit-assignee`, `schedule-visit-duration`, `schedule-visit-notes`) are referenced by tests; preserve them.

**Diff** (apply manually):

1. On the date `<Input>` (around line 60), add `className="font-mono font-semibold"`:
```tsx
<Input
  id="schedule-visit-date"
  data-testid="schedule-visit-date"
  type="date"
  className="font-mono font-semibold"
  value={dateValue}
  onChange={(e) => onDateChange(e.target.value)}
/>
```

2. On the time `<Input>` (around line 74), add the same `className="font-mono font-semibold"`.

3. On every `<Label>` (4 occurrences around lines 53, 68, 93, 122, 150), the existing className `text-xs uppercase tracking-wider text-slate-500 font-bold` already matches the reference's `.field-label` style — **leave as-is**. (No edit needed — this step is a no-op confirmation.)

4. On the duration `<SelectTrigger>` only (around line 134), add `className="font-mono font-semibold"`:
```tsx
<SelectTrigger
  id="schedule-visit-duration"
  data-testid="schedule-visit-duration"
  className="font-mono font-semibold"
>
```

5. The wrapper div className changes from `space-y-3 mt-3` to `space-y-3.5 mt-4` to match the reference's tighter top spacing inside the left column. (Single-character change.)

**VALIDATE Task 4**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/ScheduleFields.tsx
npm test -- ScheduleVisitModal
# Expected: zero output; all 9 existing tests pass.
```

---

### Task 5 — REWRITE `PickSummary.tsx`

**ACTION**: REWRITE the entire file.
**IMPLEMENT**: Clean white card with "Picked" pill, bold long-date, mono time-range, dur+assignee meta. Conflict alert with `AlertCircle` icon. Empty state with diagonal stripes (matches reference's `.summary.empty`).
**PATTERN**: Reference HTML lines 717–727 (filled) + 237–243 (empty) + 729–734 (conflict).
**IMPORTS**:
```tsx
import { AlertCircle } from 'lucide-react';
import type { Pick } from '../../types/pipeline';
import { fmtHM, fmtDur, fmtLongDate } from '../../lib/scheduleVisitUtils';
```

**GOTCHA**:
- Existing test at `ScheduleVisitModal.test.tsx:151-164` asserts `toHaveTextContent(/No time picked yet/i)` on the empty state. Preserve this exact phrase.
- Existing test selectors `data-testid="schedule-visit-pick-summary"`, `data-testid="schedule-visit-conflict-banner"`, `data-testid="schedule-visit-error"` must be preserved.
- The reference's "Assignee Kirill" line requires the staff name. The current `PickSummary` doesn't receive the assignee. **Decision**: skip the assignee meta line — it's nice-to-have, and threading the staff name through one more prop adds surface area for one line of UI. Render only the duration in the meta row.

**File contents** (paste exactly):

```tsx
import { AlertCircle } from 'lucide-react';
import type { Pick } from '../../types/pipeline';
import { fmtHM, fmtDur, fmtLongDate } from '../../lib/scheduleVisitUtils';

type Props = {
  pick: Pick | null;
  hasConflict: boolean;
  error: string | null;
};

export function PickSummary({ pick, hasConflict, error }: Props) {
  return (
    <>
      {pick ? (
        <div
          data-testid="schedule-visit-pick-summary"
          className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5 shadow-[0_1px_2px_rgba(15,23,42,0.06)]"
        >
          <div className="mb-1.5 flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-100 px-2.5 py-0.5 text-[11.5px] font-bold uppercase tracking-tight text-blue-700">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-700" />
              Picked
            </span>
          </div>
          <div className="text-[15px] font-extrabold leading-tight tracking-tight text-slate-900">
            {fmtLongDate(pick.date)}
          </div>
          <div className="mt-0.5 font-mono text-[13px] font-semibold text-slate-800">
            {fmtHM(pick.start)} – {fmtHM(pick.end)}
          </div>
          <div className="mt-2 flex flex-wrap gap-2.5 border-t border-dashed border-slate-200 pt-2 text-[11.5px] text-slate-500">
            <span>
              <b className="font-semibold text-slate-800">Duration</b>{' '}
              <span className="font-bold text-slate-900">{fmtDur(pick.end - pick.start)}</span>
            </span>
          </div>
        </div>
      ) : (
        <div
          data-testid="schedule-visit-pick-summary"
          className="mt-4 flex items-center gap-2 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3.5 py-3 text-[12.5px] italic text-slate-500"
          style={{
            backgroundImage:
              'repeating-linear-gradient(135deg, transparent 0 6px, rgba(15,23,42,0.025) 6px 12px)',
          }}
        >
          No time picked yet — click or drag on the calendar →
        </div>
      )}

      {hasConflict && (
        <div
          role="alert"
          data-testid="schedule-visit-conflict-banner"
          className="mt-2.5 flex items-start gap-2.5 rounded-xl border border-red-300 bg-red-100 px-3 py-2.5 text-[12.5px] leading-snug text-red-900"
        >
          <AlertCircle size={16} strokeWidth={2.2} className="mt-0.5 flex-none text-red-700" />
          <span>
            <b className="font-bold text-red-700">Overlaps</b> with an existing estimate on
            the same day. You can still proceed, but double-check.
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          data-testid="schedule-visit-error"
          className="mt-2.5 rounded-xl border border-red-300 bg-red-100 px-3 py-2.5 text-[12.5px] text-red-900"
        >
          {error}
        </div>
      )}
    </>
  );
}
```

**VALIDATE Task 5**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/PickSummary.tsx
npm test -- ScheduleVisitModal
# Expected: zero ESLint output; all 9 existing tests still pass (including no-pick assertion).
```

---

### Task 6 — UPDATE `ScheduleVisitModal.tsx` (modal shell + header)

**ACTION**: UPDATE — restructure the JSX shell only. Hooks and prop wiring stay.
**IMPLEMENT**: New header chrome (stage pill + ID pill + tag pill), new two-column body with soft-gray-left + white-right, custom close button, keep the existing footer.
**PATTERN**:
- Stage pill orange tone: reference lines 112 (`.pill.stage-pill`).
- ID pill mono font: reference line 113 (`.pill.id`).
- Tag pill: reference lines 114–116 (`.pill.tag-blue/green/violet`).
- Body grid: reference lines 121–135 (`.modal-body`, `.col-left`, `.col-right`).
- Custom close button: reference lines 93–100 (`.icon-btn` 36×36 rounded).
- `showCloseButton={false}` on `DialogContent` so we render our own.

**IMPORTS** (add to existing imports):
```tsx
import { ArrowRight, X } from 'lucide-react';
```

**GOTCHA**:
- Reference includes a "New lead" tag. There is no `is_new_lead` field on `SalesEntry`. **Decision**: derive a boolean: tag shows when `entry.lead_id != null`. (Mirrors the reference's intent — the tag means "this came from a lead.")
- Stage pill copy comes from `STAGES` lookup — see `frontend/src/features/sales/types/pipeline.ts:154-160`. For status `schedule_estimate` and `estimate_scheduled`, `shortLabel === 'Schedule'`; the reference says "Stage 1 · Schedule estimate". Render `Stage 1 · ${SALES_STATUS_CONFIG[entry.status].label}` for fidelity (e.g., "Stage 1 · Schedule Estimate" / "Stage 1 · Estimate Scheduled").
- ID pill: render `SAL-${entry.id.slice(0, 4).toUpperCase()}` (the reference uses an obviously short numeric, our IDs are UUIDs; first 4 hex chars are a stable, recognizable shorthand).
- Reference uses `max-w-[1180px]` for the page; the modal itself is `max-w` of about 980–1020px in the figure. Bump `sm:max-w-[960px]` to `sm:max-w-[1024px]` so the calendar fits comfortably (current 960 truncates day-headers at narrower widths).
- The dialog primitive injects `bg-white rounded-2xl shadow-xl overflow-hidden` on `DialogContent`; pass `p-0` so our custom-padded sections render edge-to-edge.
- **A11y (critical)**: Radix `DialogPrimitive.Content` requires both a `DialogTitle` and a `DialogDescription` child or it logs a dev-mode warning and assistive tech can't announce the dialog. Render both as `sr-only` — the visible heading is the new bold `<h2>` + slate-600 `<p>` in our custom `<header>`. **Do NOT remove the `DialogTitle` and `DialogDescription` imports.**
- Mobile (≤768px): the existing layout uses `grid-cols-1 md:grid-cols-[340px_1fr]` and reorders so the customer card → calendar → fields. Keep this mobile-first reorder; only the desktop-specific grid + tinting changes.

**File contents** (paste exactly):

```tsx
import { useEffect } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ArrowRight, X } from 'lucide-react';
import { track } from '@/shared/utils/track';
import { useScheduleVisit } from '../../hooks/useScheduleVisit';
import { PrefilledCustomerCard } from './PrefilledCustomerCard';
import { ScheduleFields } from './ScheduleFields';
import { WeekCalendar } from './WeekCalendar';
import { PickSummary } from './PickSummary';
import {
  fmtLongDate,
  fmtHM,
  formatShortName,
} from '../../lib/scheduleVisitUtils';
import { SALES_STATUS_CONFIG } from '../../types/pipeline';
import type { SalesEntry, SalesCalendarEvent } from '../../types/pipeline';

type Props = {
  entry: SalesEntry;
  currentEvent: SalesCalendarEvent | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultAssigneeId?: string | null;
};

export function ScheduleVisitModal({
  entry,
  currentEvent,
  open,
  onOpenChange,
  defaultAssigneeId,
}: Props) {
  const customerName = entry.customer_name ?? 'Unknown Customer';
  const jobSummary = entry.job_type ?? '';
  const s = useScheduleVisit({
    entry,
    customerId: entry.customer_id,
    customerName,
    jobSummary,
    currentEvent,
    defaultAssigneeId,
  });

  useEffect(() => {
    if (open)
      track('sales.schedule_visit.opened', {
        entryId: entry.id,
        status: entry.status,
      });
  }, [open, entry.id, entry.status]);

  const handleConfirm = async () => {
    const result = await s.submit();
    if (result.ok) {
      track('sales.schedule_visit.confirmed', { entryId: entry.id });
      toast.success(
        s.pick
          ? `Visit scheduled for ${fmtLongDate(s.pick.date)}, ${fmtHM(s.pick.start)}`
          : 'Scheduled',
      );
      onOpenChange(false);
    }
  };

  const handleOpenChange = (next: boolean) => {
    if (!next && s.isDirty) {
      const ok = window.confirm('Discard unsaved changes?');
      if (!ok) return;
      track('sales.schedule_visit.cancelled', { entryId: entry.id, dirty: true });
    } else if (!next) {
      track('sales.schedule_visit.cancelled', { entryId: entry.id, dirty: false });
    }
    onOpenChange(next);
  };

  const title = s.isReschedule ? 'Reschedule estimate visit' : 'Schedule estimate visit';
  const stageLabel = `Stage 1 · ${SALES_STATUS_CONFIG[entry.status].label}`;
  const idLabel = `SAL-${entry.id.slice(0, 4).toUpperCase()}`;
  const showLeadTag = !!entry.lead_id;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        data-testid="schedule-visit-modal"
        showCloseButton={false}
        className="sm:max-w-[1024px] p-0 rounded-[18px] border border-slate-200"
      >
        {/* A11y nodes — required by Radix Dialog. The visible header below is the
            decorative replacement; these stay as `sr-only` so screen readers still
            announce the dialog purpose. */}
        <DialogTitle className="sr-only">{title}</DialogTitle>
        <DialogDescription className="sr-only">
          Customer details are pre-filled from the lead record. Pick a time on the
          calendar — click a slot to pin a start, or drag to set both start and
          duration.
        </DialogDescription>

        {/* HEAD */}
        <header className="flex items-start gap-4 px-6 py-5 border-b border-slate-200 bg-white">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-orange-300 bg-orange-100 px-2.5 py-0.5 text-[11.5px] font-bold leading-tight tracking-tight text-orange-700">
                <span className="h-1.5 w-1.5 rounded-full bg-orange-700" />
                {stageLabel}
              </span>
              <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-0.5 font-mono text-[11.5px] font-semibold tracking-tight text-slate-800">
                {idLabel}
              </span>
              {showLeadTag && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-100 px-2.5 py-0.5 text-[11.5px] font-bold leading-tight tracking-tight text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-700" />
                  From lead
                </span>
              )}
            </div>
            <h2 className="m-0 text-[22px] font-extrabold leading-[1.15] tracking-tight text-slate-900">
              {title}
            </h2>
            <p className="mt-1 max-w-[680px] text-[13.5px] leading-relaxed text-slate-600">
              Customer details are pre-filled from the lead record. Pick a time on the
              calendar — click a slot to pin a start, or drag to set both start &amp;
              duration.
            </p>
          </div>
          <button
            type="button"
            onClick={() => handleOpenChange(false)}
            aria-label="Close"
            data-testid="close-modal-btn"
            className="inline-flex h-9 w-9 flex-none items-center justify-center rounded-[10px] border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-900"
          >
            <X size={18} strokeWidth={2} />
          </button>
        </header>

        {/* BODY — desktop two-col, mobile stack (customer → calendar → fields). */}
        <div className="grid grid-cols-1 md:grid-cols-[360px_1fr] items-stretch">
          {/* LEFT */}
          <div className="order-1 min-w-0 border-slate-200 bg-slate-50 px-6 py-5 md:border-r">
            <PrefilledCustomerCard entry={entry} />
            <ScheduleFields
              pick={s.pick}
              durationMin={s.durationMin}
              assignedToUserId={s.assignedToUserId}
              internalNotes={s.internalNotes}
              onDateChange={s.setPickDate}
              onStartChange={s.setPickStart}
              onDurationChange={s.setPickDuration}
              onAssigneeChange={s.setAssignedToUserId}
              onNotesChange={s.setInternalNotes}
            />
            <PickSummary
              pick={s.pick}
              hasConflict={s.hasConflict}
              error={s.error}
            />
          </div>

          {/* RIGHT */}
          <div className="order-2 min-w-0 bg-white px-6 py-5">
            <WeekCalendar
              weekStart={s.weekStart}
              now={s.now}
              estimates={s.estimates}
              pick={s.pick}
              loadingWeek={s.loadingWeek}
              conflicts={s.conflicts}
              hasConflict={s.hasConflict}
              pickCustomerName={formatShortName(customerName)}
              onWeekChange={s.setWeekStart}
              onSlotClick={s.setPickFromCalendarClick}
              onSlotDrag={s.setPickFromCalendarDrag}
              onTrack={(_e, source) =>
                track('sales.schedule_visit.pick', {
                  entryId: entry.id,
                  source,
                })
              }
            />
          </div>
        </div>

        {/* FOOT — already matches reference; no changes. */}
        <DialogFooter className="border-t border-slate-200 bg-slate-50 px-6 py-4">
          <Button
            variant="ghost"
            onClick={() => handleOpenChange(false)}
            data-testid="schedule-visit-cancel-btn"
          >
            Cancel
          </Button>
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
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**VALIDATE Task 6**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx
npm test -- ScheduleVisitModal
# Expected: zero ESLint output; all 9 existing tests pass.
```

---

### Task 7 — Update `ScheduleVisitModal.test.tsx` (router wrapper + 4 new tests)

**ACTION**: UPDATE the existing test file in two parts.
**IMPLEMENT**:
1. Wrap the test wrapper with `MemoryRouter` so the new `<Link>` in `PrefilledCustomerCard` has a Router context. (Without this, any test that passes a non-null `lead_id` will throw "useHref / useInRouterContext may be used only in the context of a <Router> component.")
2. Append 4 new test cases inside the existing `describe('ScheduleVisitModal', …)` block.

**Part 1** — at the top of the file (line 4 area), add the import:

```tsx
import { MemoryRouter } from 'react-router-dom';
```

Then update the `wrapper` helper (currently at lines 63–68) from:

```tsx
function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}
```

to (paste exactly):

```tsx
function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return React.createElement(
    QueryClientProvider,
    { client: qc },
    React.createElement(MemoryRouter, null, children),
  );
}
```

**Part 2** — after the last existing test (around line 224, before the closing `});` of the `describe` block), paste verbatim (reuses `mkEntry`, `wrapper`, and existing imports — no further imports required):

```tsx
  it('renders the stage pill with the entry status label', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText(/Stage 1 · Schedule Estimate/)).toBeInTheDocument();
  });

  it('renders the SAL-XXXX id pill', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry()}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText(/^SAL-/)).toBeInTheDocument();
  });

  it('renders the "From lead" tag when entry.lead_id is set', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry({ lead_id: 'lead-abc' })}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.getByText('From lead')).toBeInTheDocument();
  });

  it('does NOT render the "From lead" tag when entry.lead_id is null', () => {
    render(
      <ScheduleVisitModal
        entry={mkEntry({ lead_id: null })}
        currentEvent={null}
        open
        onOpenChange={() => {}}
      />,
      { wrapper },
    );
    expect(screen.queryByText('From lead')).not.toBeInTheDocument();
  });
```

**VALIDATE Task 7**:
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- ScheduleVisitModal
# Expected: 13 tests pass (9 existing + 4 new).
```

---

### Task 8 — Defensive sweeps

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform

# 8.1 — confirm no parchment hex values escaped the redesign
grep -rn '#fafaf6\|#f8f5ec\|#ffe066\|#d4622a\|#1a1a1a\|#9d8972\|#3a2c1c\|#ece7d8\|#d8d2c2' frontend/src/features/sales/ \
  || echo "OK: no parchment palette in sales feature"

# 8.2 — confirm the modal-level border isn't hard-coded amber-50
grep -rn 'amber-50\|border-dashed border-slate-700' frontend/src/features/sales/components/ScheduleVisitModal/ \
  || echo "OK: no leftover beige customer-card surface"

# 8.3 — confirm test-ids are intact on every sub-component
for id in schedule-visit-modal schedule-visit-customer-card schedule-visit-pick-summary schedule-visit-calendar schedule-visit-confirm-btn schedule-visit-cancel-btn; do
  grep -rn "$id" frontend/src/features/sales/components/ScheduleVisitModal/ > /dev/null \
    && echo "OK: $id present" \
    || echo "FAIL: $id missing"
done
```

**Expected**: every `OK: …` echoes; no `FAIL:` echoes.

---

### Task 9 — Final validation gauntlet

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend

# Level 1 — lint
npx eslint src/features/sales/components/ScheduleVisitModal/

# Level 2 — typecheck (must NOT introduce new errors; pre-existing FilterPanel/Layout errors tolerated)
npx tsc -p tsconfig.app.json --noEmit 2>&1 \
  | grep -E '\.tsx?\(' \
  | grep -v 'src/shared/components/FilterPanel\|src/shared/components/Layout' \
  && echo "FAIL: new TS errors above" || echo "OK: no new TS errors"

# Level 3 — focused tests
npm test -- ScheduleVisitModal
npm test -- WeekCalendar

# Level 4 — wider sales-feature regression
npm test -- src/features/sales/

# Level 5 — production build smoke
npm run build
```

**Expected outputs**:
- ESLint: zero output.
- Typecheck: prints `OK: no new TS errors`.
- Focused tests: ≥13 pass on `ScheduleVisitModal`, all `WeekCalendar` tests pass.
- Wider tests: all sales suites green.
- Production build: succeeds (no new errors).

---

### Task 10 — Manual visual confirmation

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run dev
```

In a browser:
1. Log in.
2. Navigate to `/sales` → click an entry whose status is `schedule_estimate`.
3. On the detail page, click the *Schedule visit* Now-card primary action.
4. Side-by-side compare against `feature-developments/Schedule-Estimate-Visit-Reference.html` (open the file in a second tab):
   - **Header**: orange `Stage 1 · Schedule Estimate` pill, mono `SAL-XXXX` pill, green `From lead` pill (when applicable), 22px bold title, slate-600 subtitle, 36×36 close button on the right.
   - **Left column**: soft slate-50 background; clean white customer card with avatar circle (initials) + name + Leads link + 4 icon rows; mono date + time; uppercase labels.
   - **Pick summary**: white card with blue `Picked` pill, bold long-date, mono time-range, `Duration 1 hr` meta. **Empty state**: dashed slate-200 with diagonal hatch.
   - **Right column**: white background; slate-bordered week-calendar card; today's date in a blue circle; weekend columns subtly tinted; existing estimates as left-bordered tonal cards (different colors per assignee); pick block as solid blue gradient with shadow; legend with kbd `Click` and `Drag` hints.
   - **Footer**: ghost Cancel + dark slate-900 Confirm with trailing arrow (already shipped).
5. Drag a range across slots → confirm the dashed-blue drag block appears, and on release the pick block snaps in solid-blue.
6. Click an existing estimate's day at a conflicting time → confirm the existing event card and the pick block both turn red.
7. Resize the browser to ≤768px wide → confirm the layout collapses to a single column with order: customer card → calendar → fields. (Existing mobile flow is preserved.)

---

## TESTING STRATEGY

### Unit Tests (vitest + @testing-library/react)

- `ScheduleVisitModal.test.tsx` — gains 4 new tests for header chrome (stage pill, ID pill, lead tag presence/absence). Existing 9 tests should pass without edits because every `data-testid` is preserved.
- `WeekCalendar.test.tsx` — should pass without edits (drag math, slot data attributes, conflict detection, prop wiring all unchanged).
- No new tests for `PrefilledCustomerCard`, `ScheduleFields`, `PickSummary` — their behavior is exercised through the modal-level tests.

### Edge Cases

- Customer name is empty / null → avatar shows `'—'`.
- `entry.lead_id` is null → no "From lead" tag, no Leads link in the customer card.
- `customer.email` cache is empty → email row absent.
- Pick is on a weekend → calendar column is subtly tinted.
- Pick conflicts with another estimate → both blocks turn red, conflict banner shows.
- Drag from a past slot → no-op (existing behavior).
- Width ≤768px → grid collapses, customer-card-first ordering preserved.

---

## VALIDATION COMMANDS

(Same as Task 9 above.) Run them in this order, expecting zero new failures.

### Level 1: Lint
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx eslint src/features/sales/components/ScheduleVisitModal/
```

### Level 2: Typecheck (with pre-existing-error tolerance)
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npx tsc -p tsconfig.app.json --noEmit 2>&1 \
  | grep -E '\.tsx?\(' \
  | grep -v 'src/shared/components/FilterPanel\|src/shared/components/Layout' \
  && echo "FAIL" || echo "OK"
```

### Level 3: Unit tests
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm test -- ScheduleVisitModal
npm test -- WeekCalendar
```

### Level 4: Production build
```bash
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
npm run build
```

### Level 5: Manual visual diff
Side-by-side with `feature-developments/Schedule-Estimate-Visit-Reference.html`. (See Task 10.)

---

## ACCEPTANCE CRITERIA

- [ ] Modal header renders: Stage 1 pill (orange), SAL-XXXX id pill (mono), optional `From lead` pill (green), 22px bold title, slate-600 subtitle, 36×36 close button. Reschedule path shows the same chrome.
- [ ] Body uses two-column desktop layout: 360px slate-50 left + white right, 1px slate-200 vertical divider. Mobile collapses to single column with order customer → calendar → fields.
- [ ] Customer card uses clean white surface, avatar circle with initials, name + Leads link + 4 icon rows (Phone, Mail, MapPin, Briefcase). Phone is `tel:`, email is `mailto:`. Phone is mono.
- [ ] Form fields: date + time inputs use `font-mono font-semibold`; duration trigger is mono. Labels remain uppercase tracking-wider slate-500.
- [ ] Pick summary: filled state has white card with blue `Picked` pill, bold long-date, mono time-range, `Duration <fmtDur>` meta line. Empty state has dashed slate-200 surface with diagonal hatch and the existing copy. Conflict banner has `AlertCircle` icon and rose-100 surface.
- [ ] Week calendar: 14px-rounded slate-200 card, white surface; today's day-num is a filled blue-700 circle; weekend columns tinted; existing estimates show as left-bordered tonal cards (5 stable tones cycled by assignee hash); now-line is red with red dot; pick block is solid blue gradient with shadow; drag block is dashed blue; legend has 3 swatches and a kbd-styled hint.
- [ ] Footer is unchanged (`Confirm & advance to Send Estimate` + arrow / `Update appointment`).
- [ ] All 9 existing tests in `ScheduleVisitModal.test.tsx` pass without edits.
- [ ] 4 new tests added and passing.
- [ ] All tests in `WeekCalendar.test.tsx` pass without edits.
- [ ] `npm run build` succeeds.
- [ ] Lint clean on touched directory.
- [ ] Typecheck baseline of 16 pre-existing errors in `FilterPanel.tsx` / `Layout.tsx` unchanged; zero new errors.
- [ ] No edits to `frontend/src/components/ui/*`, `useScheduleVisit.ts`, `scheduleVisitUtils.ts`, `pipeline.ts`, or any sales API file.

---

## COMPLETION CHECKLIST

- [ ] Task 1 (CSS module rewrite) complete and validated
- [ ] Task 2 (WeekCalendar.tsx rewrite) complete and validated
- [ ] Task 3 (PrefilledCustomerCard.tsx rewrite) complete and validated
- [ ] Task 4 (ScheduleFields.tsx mono-font edits) complete
- [ ] Task 5 (PickSummary.tsx rewrite) complete and validated
- [ ] Task 6 (ScheduleVisitModal.tsx shell + header) complete and validated
- [ ] Task 7 (4 new tests added) complete and validated
- [ ] Task 8 (defensive sweeps) clean
- [ ] Task 9 (final gauntlet) clean
- [ ] Task 10 (manual visual diff vs reference HTML) complete

---

## NOTES

### Why not introduce a CSS-variable theme

The reference HTML defines `--ink`, `--ink2`, … which the rest of the codebase does not use. Introducing them as a partial theme inside one CSS module would create two competing theme systems. Translating to Tailwind `slate-*` classes is faithful to the reference (palette overlap is exact for `slate-200/500/600/800/900`) and keeps the codebase consistent.

### Why a hash-based assignee → tone mapping

The reference seeds 9 estimates with 5 distinct tones, clearly intending the tone to be assignee-derived. A static lookup (e.g., `Map<staffId, tone>`) would require a config file and stay in sync with the staff list. A stable hash is deterministic, requires no config, and produces visual variety. If, later, a tone-per-staff config is desired, swap `pickTone()`'s body without touching the rest.

### Why the assignee meta line is dropped from PickSummary

The reference shows `Assignee Kirill` in the pick summary's meta row. To render it, we'd need to thread the staff name (not just id) through `PickSummary`. The hook only exposes `assignedToUserId`. The simplest path adds 4 more lines (lookup + prop). The clearest signal — the duration — is already there. **Decision**: skip for v1; revisit if a designer or operator flags it as missing.

### Why the lead tag derives from `lead_id`, not a dedicated flag

Reference tag: "New lead" (green). The source of truth for "this came from the leads table" is the FK `entry.lead_id`. Renaming the tag to "From lead" makes the boolean predicate trivially true for the reader. The rendered tag matches the reference's visual.

### Why the modal max-width bumped to 1024px

960px truncates day-headers ("Sun" ↔ "Sat" wrap on certain DPIs). The reference page uses 1180px stage width with the modal taking ~1000px of it. 1024px gives the calendar room and stays under the existing mobile breakpoint logic.

### Why no shadcn `<Button>` variant addition

The codebase convention is to override at the call site for one-off colors (NowCard, DashboardPage). A `dark` Button variant for one component would expand a shared primitive's surface area for one consumer.

### Out of scope (DO NOT do these)

- Edit `useScheduleVisit.ts` to expose the staff-name lookup for the PickSummary meta line.
- Add a "Send confirmation text" toggle to the footer.
- Add the 5-avatar overlap row in the assignee field.
- Add a "Team — first available" assignee option.
- Add a tags row at the bottom of the customer card.
- Bump `HEADER_PX` / `TIMECOL_PX` constants in `scheduleVisitUtils.ts`. (Reference uses 44/64; we use 29/56. The visual difference is small at modal scale; bumping requires updating drag math + tests in WeekCalendar. Defer until / unless the operator flags the calendar as cramped.)
- Migrate any of the 16 pre-existing typecheck errors in `FilterPanel.tsx` / `Layout.tsx`.
- Edit `frontend/src/components/ui/*`, `frontend/src/features/sales/api/*`, or any backend file.

### Confidence Score

**10 / 10** for one-pass implementation success.

Every previously-soft decision is now nailed down:

| Prior risk | Resolution |
|---|---|
| Leads link destination | Locked to `/leads/${entry.lead_id}` — `path: 'leads/:id'` registered at `frontend/src/core/router/index.tsx:188`; existing `<Link>` patterns at `LeadDetail.tsx:442` confirm the import path is `react-router-dom`. |
| Radix Dialog a11y warning if `DialogTitle`/`DialogDescription` removed | Both kept as `sr-only` children so the Radix a11y contract is satisfied while the visible header is the new bold `<h2>` + `<p>`. |
| Test wrapper missing Router context (new `<Link>` in customer card) | Task 7 explicitly updates `wrapper` to wrap children in `<MemoryRouter>` before the new tests run; existing 9 tests are unaffected. |
| Tailwind 4 arbitrary shadow + the `size-3.5` override on lucide SVGs | Already proven in production: shipped in commit `bf1df6c` on the same Confirm `<Button>` per the prior CTA refresh. |
| Tailwind palette availability | `bg-emerald-100`, `bg-teal-100`, `bg-violet-100`, `bg-amber-100`, `bg-orange-100` all already used in `frontend/src/features/sales/` (verified across `AgeChip.tsx`, `EstimateBuilder.tsx`, `EstimateDetail.tsx`). No new utility is added. |
| `useCustomer` import + `Customer.email` field | Verified at `frontend/src/features/customers/index.ts:19` and `frontend/src/features/customers/types/customer.ts` (`email: string \| null`). |
| `WeekCalendar.test.tsx` regressions | Each of the 5 assertions hits a `data-testid` or class regex that the rewrite preserves (`schedule-visit-slot-0-0`, `schedule-visit-slot-6-27`, `[class*="today"]`, `past`, customer-name text, `schedule-visit-pick`). No edits to that test file. |
| `track` util import path | Already in the file as `@/shared/utils/track`; not re-imported. |
| `react-router-dom` vs `react-router` | `react-router-dom` is the project convention (5 sales files use it). Task 3 / Task 7 both specify `react-router-dom`. |

Every classname, hex value, prop wiring, import path, route, test mutation, and validation command is decided. The agent pastes the file bodies verbatim and runs the validation gauntlet. No grep, lookup, or judgment call is left for the execution phase.
