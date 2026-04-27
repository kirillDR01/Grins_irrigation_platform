# Mobile Responsiveness Investigation — Grin's Admin Dashboard

**Investigation date:** 2026-04-25
**Audit scope:** Full admin dashboard (frontend/), with priority emphasis on Schedule tab and Appointment Modals
**Stack reviewed:** React 19 + Vite + TailwindCSS v4 + Radix UI + FullCalendar
**Code touched:** Investigation only — **no code changes made**

---

## Quick Verdict

| Device class                     | Today's usability | After Phase 1 fixes | After full rollout |
|----------------------------------|-------------------|---------------------|--------------------|
| **MacBook / desktop (≥1024 px)** | 100% — works as designed | 100% | 100% |
| **iPad portrait (768 – 1024 px)** | ~75–85% usable, calendar cramped | ~95% | 100% |
| **iPad landscape (1024 px+)**    | ~95% — already triggers desktop layout | 100% | 100% |
| **iPhone (375 – 430 px)**        | **~25–35%** usable; Schedule tab essentially broken | ~75% | ~95% |
| **iPhone landscape (~750–900 px)** | ~50% — falls in `sm:` gap, wastes space | ~90% | ~98% |

The single biggest blocker for technicians on iPhone today is the **Schedule tab's calendar view** (FullCalendar `timeGridWeek` displays a 7-column × 28-row grid that cannot fit a 375 px screen). The **Appointment Modal v2 is largely already mobile-aware** (bottom-sheet layout exists), so the gap there is smaller — mostly polish.

---

## Document Index

| File | Purpose |
|------|---------|
| [`00_EXECUTIVE_SUMMARY.md`](00_EXECUTIVE_SUMMARY.md) | One-pager for stakeholders. Read this first. |
| [`01_CURRENT_RESPONSIVE_STATE.md`](01_CURRENT_RESPONSIVE_STATE.md) | What already works on small screens — credit where it's due, and a baseline so we don't regress. |
| [`02_SCHEDULE_TAB_DEEP_DIVE.md`](02_SCHEDULE_TAB_DEEP_DIVE.md) | **Priority focus area.** Calendar, day selector, list view, picker pages, drag-drop on touch. |
| [`03_APPOINTMENT_MODAL_DEEP_DIVE.md`](03_APPOINTMENT_MODAL_DEEP_DIVE.md) | **Priority focus area.** Combined modal v2, photos, notes, secondary actions, nested sheets. |
| [`04_OTHER_PAGES_AUDIT.md`](04_OTHER_PAGES_AUDIT.md) | Survey of Sales / Customers / Jobs / Invoices / Settings / Dashboards / etc. |
| [`05_RECOMMENDED_APPROACH.md`](05_RECOMMENDED_APPROACH.md) | Phased plan. What to ship in Phase 1, 2, 3. Effort estimates. |
| [`06_DESIGN_GUIDELINES.md`](06_DESIGN_GUIDELINES.md) | Mobile-first patterns, breakpoint strategy, touch-target rules, FullCalendar mobile config. |
| [`07_FILE_INVENTORY.md`](07_FILE_INVENTORY.md) | Exhaustive `file:line` list of every change needed, grouped by severity. |

---

## Top 10 Issues (TL;DR)

1. **FullCalendar `timeGridWeek` is the default view** — unusable below ~900 px (`CalendarView.tsx:339`). Need `listWeek` on mobile.
2. **Schedule page action bar has 7+ buttons** in a single non-wrapping flex row (`SchedulePage.tsx:331-395`). Will overflow horizontally on any tablet or phone.
3. **`JobTable` has hard-coded column widths totaling ~1,100 px** (`JobTable.tsx:101-108`). The Pick-Jobs-To-Schedule flow breaks completely on iPhone.
4. **`JobPickerPopup` has 7-column table + fixed-width filter row** (`JobPickerPopup.tsx:220-270`). Same problem as JobTable.
5. **`AppointmentList` filter inputs are `w-48`/`w-40`** (`AppointmentList.tsx:254-296`) — date filters cannot fit side-by-side on iPhone.
6. **Nested overlay sheets inside the AppointmentModal use `absolute inset-0`** (`AppointmentModal.tsx:589, 600, 612`) — works on desktop, but inside the mobile bottom-sheet (which is `position: fixed`) the stacking context is wrong; payment & estimate sub-sheets may render incorrectly on iPhone.
7. **`NotesPanel` Save/Cancel buttons** use fixed `minWidth: 120/140 px` with no `flex-wrap` (`NotesPanel.tsx:218-263`). Overflows on screens narrower than ~320 px.
8. **`PhotosPanel` uses inline styles with fixed 180 px card widths** (`PhotosPanel.tsx`) — works because of horizontal scroll, but cramped on phones, and inline styles bypass Tailwind's responsive system entirely.
9. **`SalesPipeline` table has 6 fixed-width columns** (`SalesPipeline.tsx:179-184`) — no horizontal scroll affordance, content cut off below ~1,100 px.
10. **No viewport-height management on charts** (recharts `h-80`, etc.) — charts squish unreadable on landscape iPhone.

---

## Key Things Already Working

Don't redo these — they're solid:

- **Layout sidebar** has working hamburger collapse at `lg:` breakpoint with backdrop overlay (`Layout.tsx:155-336`).
- **Viewport meta tag** is present (`index.html:6`) — `<meta name="viewport" content="width=device-width, initial-scale=1.0" />`.
- **Dialog primitive has a built-in mobile floor** of `max-w-[calc(100%-2rem)]` (`dialog.tsx:64`) — most dialogs won't overflow even when sized `max-w-2xl`.
- **AppointmentModal v2 already has mobile bottom-sheet layout** with grab handle (`AppointmentModal.tsx:289-304`).
- **PageHeader correctly stacks on mobile** (`PageHeader.tsx:12`) — `flex-col gap-4 sm:flex-row`.
- **Dashboard/Customers/Invoices use responsive grids** (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`).
- **InlineCustomerPanel is correctly built as a responsive sheet** (`InlineCustomerPanel.tsx:67`).
- **CancelAppointmentDialog and ClearDayDialog stack their footer buttons** on mobile (`CancelAppointmentDialog.tsx:137-179`).

---

## Strategy Summary

**Recommended approach:** Mobile-first responsive (not separate mobile app, not separate routes). Reasons:

1. The dashboard is already partway there — Layout, Dialog, PageHeader, AppointmentModal v2 all have mobile branches.
2. Tailwind v4's breakpoint system is already in place; this is mostly a question of *applying it consistently*.
3. Maintenance: a separate mobile bundle would double the surface area for bugs and double the time required to ship features like the appointment modal v2 you just shipped.
4. Technicians need the same data and the same workflow as the office — building two divergent UIs leads to drift.

**Three phases recommended:**

- **Phase 1 (1-2 weeks)** — Fix the Schedule tab and Appointment Modal so technicians can actually do their job on iPhone. This is the urgent path.
- **Phase 2 (1-2 weeks)** — Tables, filter panels, and the rest of the admin pages. Office staff occasionally on iPad.
- **Phase 3 (ongoing)** — Polish: landscape iPhone, accessibility, touch-target audit, charts.

See `05_RECOMMENDED_APPROACH.md` for full breakdown.
