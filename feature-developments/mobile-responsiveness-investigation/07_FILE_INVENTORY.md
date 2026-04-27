# 07 — File Inventory (Exhaustive List)

Every file:line that needs to change to reach Phase 1+2 mobile usability, grouped by severity. Use this as the engineering punch list.

**Severity:**
- **P0** = Blocks technician workflow on iPhone today.
- **P1** = Significant UX problem; technician *can* work around but shouldn't have to.
- **P2** = Polish; cosmetic or edge case.

---

## P0 — Phase 1 Critical (Schedule + Modal)

### S-01 — FullCalendar mobile mode
- **File:** `frontend/src/features/schedule/components/CalendarView.tsx`
- **Lines:** 339–344, 351–352
- **Problem:** `initialView="timeGridWeek"` and full toolbar both unusable on phone.
- **Fix:** Add `useMediaQuery`, switch to `listWeek` and simplified toolbar on mobile. Disable `editable`/`selectable` on mobile.
- **Effort:** 1 day
- **See:** `02_SCHEDULE_TAB_DEEP_DIVE.md` § 2.1, `06_DESIGN_GUIDELINES.md` § 3

### S-02 — Schedule page action bar overflow
- **File:** `frontend/src/features/schedule/components/SchedulePage.tsx`
- **Lines:** 331–395
- **Problem:** 7 buttons in `flex items-center gap-4` with no wrap.
- **Fix:** Add `flex-wrap`, hide secondary buttons in DropdownMenu on mobile. Pattern 1 in `06_DESIGN_GUIDELINES.md`.
- **Effort:** 1 day

### S-03 — JobTable hardcoded column widths
- **File:** `frontend/src/features/schedule/components/JobTable.tsx`
- **Lines:** 101–108
- **Problem:** `w-[220px] w-[180px] w-[160px] w-[120px] w-[120px] w-[80px] w-[80px] w-[140px]` totaling ~1100 px.
- **Fix:** Replace `w-[NNNpx]` → `min-w-[NNNpx]`. Wrap table in `overflow-x-auto`. Hide low-priority columns at `< md:`. (Or scope-decision: hide entire PickJobsPage on `< lg:`.)
- **Effort:** 1 day if mobile-friendly, 0.5 day if scope-limited to desktop

### S-04 — JobPickerPopup (legacy)
- **File:** `frontend/src/features/schedule/components/JobPickerPopup.tsx`
- **Lines:** 220–270
- **Problem:** 7-column table + fixed-width filters in `max-w-5xl` dialog.
- **Fix:** If deprecated, delete or `lg:`-only. If still used, same as JobTable.
- **Effort:** 0.5 day to verify deprecation

### M-01 — AppointmentModal nested overlay sheets
- **File:** `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx`
- **Lines:** 589 (TagEditorSheet), 600 (PaymentSheetWrapper), 612 (EstimateSheetWrapper)
- **Problem:** `<div className="absolute inset-0 z-10">` inside `position: fixed` modal — stacking context wrong on mobile.
- **Fix Option A:** Add header with back button to each sub-sheet so it reads as a replacement view (cheaper).
- **Fix Option B:** Lift sub-sheets to standalone Radix Sheets at the modal level.
- **Effort:** 0.5 day (A), 1.5 day (B)
- **See:** `03_APPOINTMENT_MODAL_DEEP_DIVE.md` §13–14

### M-02 — NotesPanel button overflow
- **File:** `frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx`
- **Lines:** 218–263
- **Problem:** Save / Cancel buttons with fixed `minWidth: 120/140 px` and no `flex-wrap`. Overflows on iPhone SE (320 px).
- **Fix:** Migrate inline styles → Tailwind classes; add `flex-wrap`.
- **Effort:** 0.5 day (combined with M-03)

### M-03 — PhotosPanel inline-styled, can't apply mobile breakpoints
- **File:** `frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx`
- **Problem:** All styling inline; bypasses Tailwind breakpoint system.
- **Fix:** Migrate inline styles → Tailwind. Apply `max-sm:w-32` to photo cards, `max-sm:p-3` to upload buttons.
- **Effort:** combined with M-02

---

## P1 — Phase 1 Important (Polish)

### S-05 — DaySelector overflow
- **File:** `frontend/src/features/schedule/components/DaySelector.tsx`
- **Problem:** 7 buttons × `min-w-[70px]` + gaps = ~538 px, overflows iPhone.
- **Fix:** Wrap in `overflow-x-auto`, snap-scroll to today on mount.
- **Effort:** 0.25 day

### S-06 — AppointmentList filters
- **File:** `frontend/src/features/schedule/components/AppointmentList.tsx`
- **Lines:** 254–296
- **Problem:** `w-48` Select and `w-40` Date inputs cramped on phone.
- **Fix:** `w-full sm:w-48`, `w-full sm:w-40`. (Or bigger: replace with Sheet-based filters.)
- **Effort:** 0.5 day

### S-07 — AppointmentForm time inputs
- **File:** `frontend/src/features/schedule/components/AppointmentForm.tsx`
- **Lines:** ~405
- **Problem:** `grid-cols-2` on time inputs, tight on iPhone SE.
- **Fix:** `grid-cols-1 sm:grid-cols-2`.
- **Effort:** 0.1 day

### S-08 — FacetRail Sheet width
- **File:** `frontend/src/features/schedule/components/FacetRail.tsx`
- **Lines:** ~59
- **Problem:** `w-64` (256 px) on iPhone (375 px) leaves only ~100 px of overlay.
- **Fix:** `w-[85vw] sm:w-72` for the SheetContent.
- **Effort:** 0.1 day

### S-09 — SchedulingTray bottom panel
- **File:** `frontend/src/features/schedule/components/SchedulingTray.tsx`
- **Lines:** ~97
- **Problem:** `grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr]` — 2 cols cramped on iPhone.
- **Fix:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-[...]`.
- **Effort:** 0.1 day

### M-04 — Touch target audit
- **Files:**
  - `AppointmentModal/ModalHeader.tsx` close button (40×40 → 44×44)
  - `AppointmentModal/CustomerHero.tsx` phone-call button (32×32 → 44×44)
  - Audit any `h-8`/`w-8` on clickable elements globally
- **Effort:** 0.25 day

### M-05 — ActionTrack tightness on narrow phones
- **File:** `AppointmentModal/ActionTrack.tsx:68`
- **Problem:** Three `flex-1` cards with `gap-2` and `px-5` → ~106 px each on iPhone SE.
- **Fix:** Reduce `px-4` and `gap-1.5` on mobile, OR stack vertically.
- **Effort:** 0.25 day

### M-06 — RestoreScheduleDialog summary cards
- **File:** `frontend/src/features/schedule/components/RestoreScheduleDialog.tsx`
- **Lines:** ~205
- **Problem:** `grid grid-cols-2` for summary cards; ~165 px each on iPhone.
- **Fix:** `grid-cols-1 sm:grid-cols-2`.
- **Effort:** 0.1 day

---

## P2 — Phase 2 (Office Pages)

### O-01 — Sales pipeline table
- **File:** `frontend/src/features/sales/components/SalesPipeline.tsx`
- **Lines:** 179–184
- **Problem:** 6 fixed-width columns ~840 px.
- **Fix:** `min-w-[]`, hide cols < md.
- **Effort:** 0.5 day

### O-02 — Jobs page filters & table
- **File:** `frontend/src/features/jobs/components/JobList.tsx`
- **Lines:** 467–598 (filters), table headers
- **Problem:** 7 filter dropdowns, 12-column table.
- **Fix:** Sheet-based filters on mobile, hide cols < md.
- **Effort:** 1 day

### O-03 — Customers page bulk action bar
- **File:** `frontend/src/features/customers/components/CustomerList.tsx`
- **Lines:** ~459
- **Problem:** `fixed bottom-6 left-1/2 -translate-x-1/2` overlay obscures rows on phone.
- **Fix:** Mobile: full-width pinned bottom with safe-area padding.
- **Effort:** 0.25 day

### O-04 — Charts fixed height
- **Files:** `frontend/src/features/accounting/components/SpendingChart.tsx:70`, plus marketing charts.
- **Problem:** `h-80` fixed.
- **Fix:** `h-64 md:h-80`.
- **Effort:** 0.5 day across all charts

### O-05 — Settings page UX
- **File:** `frontend/src/pages/Settings.tsx`
- **Problem:** 18.7 KB single-page form with heavy vertical scroll on mobile.
- **Fix:** Convert to tabs (General / Integrations / Team / Billing / Branding).
- **Effort:** 2–3 days

### O-06 — EstimateBuilder line items
- **File:** likely `frontend/src/features/sales/components/EstimateBuilder.tsx`
- **Problem:** `grid-cols-12` line items unusable on mobile.
- **Fix:** Stacked card on mobile, grid on desktop.
- **Effort:** 1 day

### O-07 — Mobile global search
- **File:** `frontend/src/shared/components/Layout.tsx:261`
- **Problem:** Search hidden behind `hidden lg:flex`.
- **Fix:** Add a search icon to the mobile header that opens fullscreen search.
- **Effort:** 1 day

### O-08 — Reusable MobileFilterSheet shared component
- **New file:** `frontend/src/shared/components/MobileFilterSheet.tsx`
- **Purpose:** Shared sheet wrapper for filter UIs across pages.
- **Effort:** 1 day to build, 0.25 day per page to integrate

---

## P3 — Phase 3 (Polish, Optional)

### P-01 — `100dvh` instead of `100vh`
- Find all `100vh`, `min-h-screen`, `h-screen`. Replace with `100dvh`/`min-h-dvh`/`h-dvh`. iOS Safari supports dvh in 16+.
- **Effort:** 0.5 day

### P-02 — Landscape phone breakpoint
- Add custom `phone-landscape` variant to Tailwind/CSS.
- Apply to chart heights, modals, timeline strips.
- **Effort:** 1 day

### P-03 — MapsPickerPopover edge clipping
- **File:** `AppointmentModal/MapsPickerPopover.tsx:56-105`
- Fix: convert to Radix Popover/DropdownMenu for portal-based positioning.
- **Effort:** 0.5 day

### P-04 — AppointmentDetail (legacy) deprecation
- **File:** `frontend/src/features/schedule/components/AppointmentDetail.tsx` (35 KB)
- Verify deprecation, delete if unused. Otherwise audit.
- **Effort:** 0.5–2 day depending on outcome

### P-05 — PaymentCollector (legacy) review
- **File:** `frontend/src/features/schedule/components/PaymentCollector.tsx` (15 KB)
- Verify still used. If yes, mobile audit. If no, delete.
- **Effort:** 0.5 day to verify

### P-06 — JobSelector (legacy) cleanup
- **File:** `frontend/src/features/schedule/components/JobSelector.tsx`
- Mark `lg:`-only or delete.
- **Effort:** 0.25 day

### P-07 — A11y full audit
- Touch targets, focus order, screen-reader labels, color contrast, motion respect.
- **Effort:** 1–2 days per pass, ongoing

### P-08 — PWA install
- Manifest, service worker, install prompt.
- **Effort:** 1–2 days

### P-09 — Sub-sheet refactor (Option B)
- If Phase 1 Option A doesn't satisfy users.
- **Effort:** 1.5 days

---

## Summary Counts

| Severity | Count | Engineering days |
|---|---|---|
| P0 | 7 items | ~5–6 days |
| P1 | 6 items | ~1.5 days |
| **Phase 1 total** | **13 items** | **~7 days** |
| P2 | 8 items | ~7–9 days |
| **Phase 2 total** | **8 items** | **~7–9 days** |
| P3 | 9 items | ~5–7 days |
| **Phase 3 total** | **9 items** | **~5–7 days** |
| **Grand total** | **30 items** | **~19–23 days** |

---

## Files NOT Touched (intentionally)

These are mobile-ready already; do not modify.

- `frontend/src/shared/components/Layout.tsx` — sidebar pattern works.
- `frontend/src/components/ui/dialog.tsx` — primitive has mobile floor.
- `frontend/src/shared/components/PageHeader.tsx` — already responsive.
- `frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx` — container layout works (only sub-component issues to fix).
- `frontend/src/features/schedule/components/InlineCustomerPanel.tsx` — reference impl.
- `frontend/src/features/schedule/components/CancelAppointmentDialog.tsx` — reference impl.
- `frontend/src/features/schedule/components/ClearDayDialog.tsx` — reference impl.
- `frontend/src/components/ui/sheet.tsx` — primitive works as-is.
- `frontend/src/features/schedule/components/JobSelectorCombobox.tsx` — already responsive.
- `frontend/src/features/schedule/components/AppointmentModal/{TimelineStrip,ModalFooter,SecondaryActionsStrip,CustomerHero,PropertyDirectionsCard,ScopeMaterialsCard,AssignedTechCard}.tsx` — reviewed and clean.

---

## Files Where Deeper Investigation Is Needed Before Phase 2

These were sampled lightly but warrant a closer look during Phase 2 planning:

- `frontend/src/features/communications/` — SMS/email logs.
- `frontend/src/features/agreements/` — agreement detail/list.
- `frontend/src/features/contract-renewals/` — likely fine but unverified.
- `frontend/src/features/marketing/` — chart-heavy.
- `frontend/src/features/staff/` — staff list, schedule blocks.
- `frontend/src/features/dashboard/` — metric cards, recent activity.
- `frontend/src/features/customers/components/CustomerForm.tsx` (716 lines).
- `frontend/src/features/jobs/components/JobForm.tsx` (409 lines).
- Map components: `StaffLocationMap.tsx`, any Google Maps usage.

---

## Implementation Order (Suggested)

If a single engineer is doing this, suggested order to minimize rework and maximize early visible progress:

1. **Day 1:** Build `useMediaQuery` hook, add to `shared/hooks/`. Pick one P0 item to validate the testing setup (recommend S-05 DaySelector — quick visible win).
2. **Day 2:** S-01 FullCalendar mobile mode. Real-device test. **This is the hero feature.**
3. **Day 3:** S-02 Schedule action bar. Combine with S-08, S-09.
4. **Day 4:** M-01 (Option A), M-02, M-03 — Appointment Modal polish.
5. **Day 5:** S-03 JobTable (or scope-out if approved). M-04, M-05, S-06, S-07.
6. **Day 6–7:** Real-device QA, bug fixes, second pass on calendar UX.
7. **Phase 1 ship.**

Then Phase 2 can run in parallel with normal feature work.
