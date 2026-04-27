# 05 — Recommended Approach

A phased plan for going from today's ~25–35% iPhone usability to ~95%, with a focused effort and a clear delineation between technician-critical vs. office-nice-to-have work.

---

## 1. Strategic Choice: Responsive Web (Recommended)

**Recommendation:** Stay with responsive web. Don't build a native iOS app or a separate mobile route tree.

### Why
- The dashboard already has working responsive primitives (Layout sidebar, Dialog, AppointmentModal v2, PageHeader). The team's pattern instincts are right.
- Native iOS/Android = 8–12 weeks + ongoing app-store maintenance + duplicated business logic. Wrong trade for a 1-engineer team shipping a CRM.
- Two separate UI bundles (mobile route tree + desktop route tree) means double the surface area for bugs. **Same codebase, different breakpoints** is the modern default.
- Tailwind v4 is already installed and the project uses default breakpoints. Adding `sm:` / `md:` / `lg:` variants is the cheapest path.

### What "responsive" means in this codebase
1. **Mobile-first** — base classes target the smallest viewport, breakpoint variants add desktop behavior. Most existing code is desktop-first; we should flip this on touched files.
2. **Three layout intents** — phone (< sm, ~320–640 px), tablet (sm–lg, 640–1024 px), desktop (≥ lg, ≥ 1024 px). Existing breakpoints map naturally.
3. **Touch targets ≥ 44 × 44 px** on every interactive element. Apple HIG floor.
4. **No horizontal scroll for primary content** — tables can scroll, but the page itself shouldn't. Body width should be content-driven, not table-driven.

---

## 2. Phase 1 — Schedule + Appointment Modal (target: 1–2 weeks)

**Goal:** A technician can run their full day from an iPhone — view today's schedule, tap into an appointment, mark en-route → arrived → completed, take photos, add notes.

### 1.1 — FullCalendar mobile mode (P0)
**File:** `frontend/src/features/schedule/components/CalendarView.tsx`

```tsx
import { useMediaQuery } from '@/shared/hooks/useMediaQuery'; // create if missing

const isMobile = useMediaQuery('(max-width: 768px)');

<FullCalendar
  initialView={isMobile ? 'listWeek' : 'timeGridWeek'}
  headerToolbar={
    isMobile
      ? { left: 'prev,next', center: 'title', right: 'today' }
      : { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }
  }
  editable={!isMobile}                  // disable drag-drop on touch
  selectable={!isMobile}
  views={{
    listWeek: {
      buttonText: 'List',
      noEventsContent: 'No appointments this week',
    },
  }}
  ...
/>
```

Hide the in-app `Tabs` view-toggle on mobile (`SchedulePage.tsx:343`) since FullCalendar's own switcher disappears in mobile mode anyway.

**Effort:** 0.5–1 day including testing list view event rendering.

### 1.2 — Schedule page action bar (P0)
**File:** `frontend/src/features/schedule/components/SchedulePage.tsx:330-396`

Restructure the `<PageHeader action={...}>`:
- Mobile (< md): only `+ New Appointment` button + a "More" `DropdownMenu` containing all secondary actions.
- Desktop (≥ lg): current full row.
- In-between (md–lg): two-row layout with primary actions on row 1, secondary on row 2.

**Effort:** ~1 day.

### 1.3 — Hide Pick Jobs To Schedule on mobile (P0 if scope-decision allows)
**Files:** `SchedulePage.tsx:373-383` (the "Pick jobs to schedule" buttons), `pages/PickJobsPage.tsx`.

Recommend wrapping the page route in a desktop-only check or showing a "Use desktop for route generation" message on mobile. **This avoids ~5 days of work building a mobile-friendly bulk job picker** — a workflow that genuinely doesn't fit a phone use case.

**Decision needed:** product owner sign-off that techs don't need to bulk-pick jobs from their phone.

**Effort if approved:** 0.5 day. **Effort if mobile-friendly version required:** ~5 days.

### 1.4 — DaySelector horizontal scroll (P1)
**File:** `frontend/src/features/schedule/components/DaySelector.tsx`

Wrap the row in `overflow-x-auto`, snap-scroll to today on mount.

**Effort:** 0.25 day.

### 1.5 — AppointmentList mobile filter row (P1)
**File:** `AppointmentList.tsx:254-296`

`w-48` → `w-full sm:w-48`, `w-40` → `w-full sm:w-40`. Or: replace with a Sheet trigger like the JobList plan in Phase 2.

**Effort:** 0.25–0.5 day.

### 1.6 — AppointmentForm time inputs (P1)
**File:** `AppointmentForm.tsx:~405`

`grid grid-cols-2` → `grid grid-cols-1 sm:grid-cols-2`.

**Effort:** 0.1 day.

### 1.7 — Appointment Modal nested overlays (P0)
**File:** `AppointmentModal.tsx:589, 600, 612`

Pick one approach:
- **A (cheaper):** add a header to each sub-sheet (TagEditorSheet, PaymentSheetWrapper, EstimateSheetWrapper) with a back button so users understand it's a replacement view of the modal content. Keep `absolute inset-0`. ~0.5 day.
- **B (cleaner):** lift sub-sheets to standalone Radix Sheets at the same level as the modal. Better UX, but more code change. ~1.5 days.

**Recommended:** Option A for Phase 1 (low-risk), refactor to B in Phase 3 if usage feedback warrants.

### 1.8 — NotesPanel button overflow (P0)
**File:** `NotesPanel.tsx:218-263`

Add `flexWrap: 'wrap'` to button container. Or migrate inline styles to Tailwind: `className="mt-3 flex flex-wrap gap-3 justify-end"` and convert button styles. **Migration to Tailwind also brings PhotosPanel and NotesPanel into design-system consistency.**

**Effort:** 0.5 day for both panels.

### 1.9 — Touch target audit (P1)
**Files:** `ModalHeader.tsx`, `CustomerHero.tsx`, any `h-8`/`w-8` button across modal subcomponents.

Bump close button and phone-call button to `h-11 w-11`.

**Effort:** 0.25 day.

### 1.10 — Schedule page header polish (P2)
- Page title responsive: smaller on mobile.
- LeadTimeIndicator: hide or condense on mobile.
- ClearDayButton: hide on mobile (route-generation-flavored, desktop only).

**Effort:** 0.25 day.

### Phase 1 totals

| Item | Effort |
|---|---|
| 1.1 FullCalendar mobile mode | 1.0 day |
| 1.2 Schedule action bar | 1.0 day |
| 1.3 Hide Pick Jobs (if approved) | 0.5 day |
| 1.4 DaySelector | 0.25 day |
| 1.5 AppointmentList filters | 0.5 day |
| 1.6 AppointmentForm time inputs | 0.1 day |
| 1.7 Modal nested overlays (A) | 0.5 day |
| 1.8 NotesPanel + PhotosPanel migration | 0.5 day |
| 1.9 Touch targets | 0.25 day |
| 1.10 Header polish | 0.25 day |
| **Subtotal engineering** | **~5 days** |
| Real-device QA (iPhone, iPad) | 1–2 days |
| **Phase 1 total** | **~6–7 days = 1–1.5 weeks** |

### Phase 1 acceptance criteria
- Technician on iPhone 13 mini (375 × 812):
  - Can open `/schedule` and see today's appointments as a vertical list.
  - Can tap an appointment to open the modal.
  - Can advance status (en route → arrived → completed).
  - Can take/upload a photo.
  - Can add internal notes.
  - Can call/text customer from the modal.
  - Can collect payment via Stripe Terminal (verify the SDK flow on real device).
- Office user on iPad (768 × 1024 portrait):
  - Calendar view shows day/list view by default but can switch to week.
  - All admin pages render without horizontal scroll on the page itself (tables can scroll).

---

## 3. Phase 2 — Office Pages (target: 1–2 weeks)

**Goal:** All admin pages usable on iPad and iPhone, with awareness that office staff are the primary users.

### 2.1 — Standardize tables (P0)
- Audit every `<TableHead className="w-[NNNpx]">` and replace with `min-w-[NNNpx]`.
- Add `hidden md:table-cell` to low-priority columns:
  - Jobs: `created_at`, `equipment_required`, `notes_summary`
  - Sales: `Tags`, `Updated`
  - Customers: `Created`, `Tags`
  - Invoices: `Issued`, `Notes`
- Verify every `<table>` is wrapped in the `Table` primitive (which has `overflow-x-auto`) or in a custom `overflow-x-auto` div.

**Effort:** ~2 days across all list pages.

### 2.2 — Filter Sheet on mobile (P1)
Build a shared `MobileFilterSheet` component that wraps existing filter controls in a `<Sheet side="bottom">`. Use across:
- AppointmentList
- JobList
- SalesPipeline
- Invoices
- Customers (currently uses FilterPanel)

**Effort:** ~2 days.

### 2.3 — Charts (P2)
Find/replace `h-80` → `h-64 md:h-80`. Verify pie charts have label collision logic.

**Effort:** ~0.5 day.

### 2.4 — Bulk action bar (P2)
**File:** `CustomerList.tsx:~459` and similar.

On mobile, change `fixed bottom-6 left-1/2 -translate-x-1/2` to `fixed bottom-0 inset-x-0` so it spans the full width without obscuring content. Add safe-area-bottom padding.

**Effort:** ~0.25 day.

### 2.5 — Mobile search affordance (P2)
Add a search icon to the mobile header (currently search is hidden via `hidden lg:flex` in `Layout.tsx:261`). Tapping opens a fullscreen search panel.

**Effort:** ~1 day.

### 2.6 — EstimateBuilder line-item layout (P1)
**File:** `EstimateBuilder.tsx`

Replace `grid-cols-12` line items with stacked cards on mobile (`grid-cols-1 md:grid-cols-12`).

**Effort:** ~1 day.

### Phase 2 totals
~7 engineering days + 2 days QA = **~2 weeks**.

---

## 4. Phase 3 — Polish (ongoing)

### 3.1 — Landscape iPhone (P2)
Current breakpoints: phones in landscape (e.g., 14 Pro Max landscape = 932 × 430) trigger the `sm:` and possibly `md:` styles, which assume portrait tablet aspect ratios. Add a custom breakpoint:

```js
// tailwind via CSS variables in index.css
// Add in the @theme inline block or in a CSS file:
@variant phone-landscape (@media (max-width: 1024px) and (orientation: landscape));
```

Use sparingly: charts (height-constrained), modals (use `100dvh`), and timeline strips that don't need to be tall.

**Effort:** ~1 day to introduce, then per-component fixes as needed.

### 3.2 — `100dvh` instead of `100vh` (P2)
Find/replace `min-h-screen` and `h-[NNvh]` patterns with `dvh` units (modern Safari supports this). Eliminates the "100vh extends under the address bar" issue.

**Effort:** ~0.5 day.

### 3.3 — Settings tabbed redesign (P2-P3)
Convert `Settings.tsx` to a tabbed layout to reduce vertical scroll. Could be done as a separate UX initiative.

**Effort:** 2–3 days.

### 3.4 — Sub-sheet refactor (P3)
The cleaner architectural approach to Appointment Modal nested overlays — lift to standalone Radix Sheets. Only do this if Phase 1 Option A (back-button headers) doesn't satisfy users.

**Effort:** ~1.5 days.

### 3.5 — Accessibility full audit (ongoing)
- Tap targets ≥ 44 × 44 (mostly done in Phase 1).
- Focus order in modals.
- Screen-reader labels on icon-only buttons.
- Color contrast (in particular, the `text-slate-400` on `bg-white` for inactive nav links — check WCAG AA).
- Reduced-motion respect (already partly in via `tw-animate-css`, but verify).

**Effort:** 1–2 days per audit pass, ongoing.

### 3.6 — PWA install (P3)
Add manifest, service worker, install prompt. Lets technicians "install" the dashboard to their home screen and get an app-like experience without the app store.

**Effort:** 1–2 days.

---

## 5. Total Budget

| Phase | Effort | Calendar |
|---|---|---|
| Phase 1 (Schedule + Modal) | ~5–7 dev days + 2 QA | 1.5 weeks |
| Phase 2 (Other pages) | ~7 dev days + 2 QA | 2 weeks |
| Phase 3 (Polish) | ~5 dev days, ongoing | 2 weeks elapsed for initial pass |
| **Cumulative to ~95% mobile** | **~22 days** | **~5 weeks** |

These estimates assume one focused engineer, with product/UX sign-off on the open decisions before kick-off.

---

## 6. Open Decisions Required Before Phase 1

1. **Native vs. responsive web.** Recommend responsive. Confirm.
2. **Minimum supported viewport width.** Recommend 375 px. Confirm.
3. **Default mobile calendar view.** Recommend `listWeek`. Confirm.
4. **Pick Jobs To Schedule on mobile.** Recommend desktop-only — *can techs bulk-pick from their phone, or only office staff?* Confirm.
5. **Drag-drop reschedule on mobile.** Recommend disabling on touch and routing through Edit dialog. Confirm.
6. **Photos panel approach.** Recommend migrating inline styles → Tailwind during Phase 1 (~0.5 day extra). Confirm.

---

## 7. What Could Go Wrong

| Risk | Mitigation |
|---|---|
| FullCalendar `listWeek` view doesn't satisfy tech workflow | Spike day 1 of Phase 1; if it doesn't work, build a custom list view (an extra ~3 days) |
| Stripe Terminal Web flow breaks inside the modal on iPhone | Test early; PaymentSheetWrapper is one of the highest-stakes paths |
| iOS Safari `100vh` quirks cause cut-off footer buttons | Use `100dvh`; test with keyboard open |
| Hidden columns on mobile hide data techs need | Treat column-hide list as a UX decision; keep "expand row" affordance |
| `useMediaQuery` SSR/hydration mismatch | Project is Vite SPA, no SSR — won't apply |
| Sub-sheet stacking-context fix breaks payment flow | Test deeply with real Stripe Terminal device; have fallback for Option A vs Option B |
| Real-device QA reveals issues outside this audit | Budget includes 2 QA days/phase; expect a follow-on bug round |

---

## 8. Definition of Done

A feature is "mobile responsive" when:

- [ ] Renders correctly on iPhone 13 mini (375 × 812 px) and iPad Air (820 × 1180 px) without horizontal page scroll.
- [ ] All interactive elements have ≥ 44 × 44 px tap target.
- [ ] No content is cut off below the fold for the same data shown on desktop (tables can scroll, but content is reachable).
- [ ] Forms can be submitted (no buttons hidden by soft keyboard).
- [ ] Touch interactions don't conflict with native scroll (no accidental drags).
- [ ] iOS dynamic type (large text setting) doesn't break layout.
- [ ] Tested on a real iPhone or Browserstack — not just dev tools.

---

**Next:** `06_DESIGN_GUIDELINES.md` for the patterns to apply, then `07_FILE_INVENTORY.md` for the exhaustive file:line list.
