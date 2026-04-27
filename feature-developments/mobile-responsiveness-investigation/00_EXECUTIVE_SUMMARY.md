# 00 — Executive Summary

**Investigation:** Make the Grin's admin dashboard usable on iPhone and iPad, with priority emphasis on the Schedule tab and Appointment Modals (technicians' primary surfaces).

---

## The Question

> *"Investigate how to make this admin dashboard mobile-view friendly. It should be fully visible on a MacBook screen and also visible on iPhone or iPad. Emphasize the Scheduling tab and the appointment modals — that's what technicians use throughout the day."*

## The Short Answer

**MacBook ≥ 1024 px:** Already works. No changes needed.

**iPad portrait (768–1024 px):** Mostly works. The Schedule tab's calendar is cramped (FullCalendar `timeGridWeek` shows 7 columns on a 768 px screen — appointment text becomes illegible) but the page still functions. Forms and modals are fine. Tables wrap. Estimated **~80%** usability today.

**iPhone (375–430 px):** **Currently unusable for the Schedule tab.** Three concrete blockers:
1. The week-view calendar literally cannot fit on a phone (7 vertical columns, 28 half-hour rows, 6 am–8 pm).
2. The page action bar shows 7+ horizontal buttons (Lead-Time, Clear-Day, View Toggle, Add Jobs, Pick Jobs to Schedule, Send Confirmations, New Appointment) in a non-wrapping flex row — they overflow off the right edge.
3. The "Pick Jobs To Schedule" page (the single most important workflow for daily route building) uses a job-table with hard-coded ~1,100 px of column widths.

**The Appointment Modal v2 is in much better shape.** It already has a mobile bottom-sheet branch with a grab handle, full-width on small screens, scrollable body, and 92vh max height. The sub-issues there are smaller — a few inline-styled buttons that don't wrap, photo cards that are slightly cramped, and a stacking-context bug where nested sheets (Payment, Estimate, Tags) render with `absolute inset-0` instead of `fixed`.

---

## What's Driving the Gap

This is a **mobile-second** codebase, not a mobile-broken codebase. The team clearly knows responsive design — the Layout, Dialog primitive, AppointmentModal v2, PageHeader, and most card grids all have mobile branches. The gap is consistency, not knowledge.

Three patterns produce most of the issues:

| Pattern | Where it shows up | Why it breaks mobile |
|---|---|---|
| Fixed-width tables (`w-[180px]`, etc.) | JobTable, JobPickerPopup, SalesPipeline, AppointmentList filters | Won't shrink, won't wrap, won't scroll |
| Multi-button action bars without `flex-wrap` | SchedulePage header, several PageHeader actions | Buttons clip off the right edge |
| Skipping the `sm:` breakpoint | Forms with `grid-cols-2`, charts with fixed `h-80`, `md:` jumps | Wastes space on tablets, breaks on phones |

The good news: all three are mechanical fixes applied via Tailwind class adjustments. None requires architectural change.

---

## Recommended Path Forward

### Phase 1 — Schedule + Appointment Modal (1–2 weeks)
The two surfaces technicians touch every day. After this phase, a tech can run their full day from an iPhone.

1. **Switch FullCalendar to mobile-aware view config.** Default to `listWeek` view ≤ `md` breakpoint, `timeGridWeek` above. Hide unused toolbar buttons on mobile.
2. **Make the Schedule page action bar wrap and consolidate.** Move secondary buttons into an overflow menu on mobile; keep "+ New Appointment" as the primary action.
3. **Fix the JobTable / JobPickerPopup tables.** Either (a) replace with stacked cards on mobile, or (b) hide low-priority columns and add `overflow-x-auto`.
4. **Patch the AppointmentModal v2 polish items.** Move nested sheet panels from `absolute inset-0` → `fixed`; add `flex-wrap` to NotesPanel buttons; tighten PhotosPanel for narrow widths; standardize 44 px touch targets across `LinkButton`/`V2LinkBtn`.

### Phase 2 — Office tooling (1–2 weeks)
Customers, Sales pipeline, Invoices, Settings, Communications, etc. Office staff occasionally on iPad; nice-to-have on phone.

5. **Standardize tables.** Wrap every `<table>` in `overflow-x-auto`; replace `w-[NNNpx]` with `min-w-[NNN px]`; hide low-priority columns at `< md`.
6. **Standardize filter rows.** Stack filters vertically on mobile, horizontal at `sm:`+. Replace `w-48` → `flex-1 min-w-[140px]` pattern.
7. **Standardize charts.** Replace fixed `h-80` with `h-64 md:h-80` and ensure `ResponsiveContainer` is in use.

### Phase 3 — Polish (ongoing)
8. **Landscape-iPhone breakpoint.** Add a custom `xs-landscape` breakpoint or use `landscape:` variants for chart layouts.
9. **Accessibility audit.** Touch targets ≥ 44 px (Apple HIG), focus order, screen reader labels.
10. **Empty states & toast positioning.** Verify `sonner` toaster positioning works in safe-area on iPhone.

See **`05_RECOMMENDED_APPROACH.md`** for full plan with story-point estimates.

---

## What This Investigation Did *Not* Cover

- **No real-device testing.** All findings are based on code review. A round of testing on actual iPhone 13/14/SE and iPad Air/Mini is essential before signing off on Phase 1. Recommend Browserstack or a designated test device.
- **No PWA / offline considerations.** Technicians on poor cell signal would benefit from PWA install + offline cache, but that's a separate effort.
- **No Stripe Terminal / Tap-to-Pay flow review.** PaymentSheetWrapper opens the Terminal flow — that's its own SDK and may have its own mobile constraints (likely fine, Stripe Terminal Web supports mobile browsers).
- **No iOS Safari quirks deep-dive.** Things like 100vh ≠ visible viewport on Safari, the `position: fixed` keyboard behavior, and `:hover` state being sticky on touch — these need a dedicated pass during Phase 1 testing.
- **No native app investigation.** This audit assumes responsive web. If the goal shifts to native iOS, that's a different conversation (probably worth ~8 weeks of effort and an entirely separate codebase).

---

## Decision Points the Team Should Settle Before Phase 1

1. **Native vs. responsive web.** Recommend responsive web (cheaper, faster, no app-store overhead, technicians already have the dashboard URL). Confirm.
2. **Minimum supported viewport.** Recommend 375 px wide (iPhone SE 2nd/3rd gen, iPhone 13/14 mini). Anything narrower is rare.
3. **Calendar UX on mobile.** Recommend `listWeek` view by default — shows appointments as a vertical list grouped by day. Most field-service apps (ServiceTitan, Jobber, Housecall Pro) do exactly this. Confirm.
4. **Whether technicians need the full admin (drag-drop reschedule, generate routes, clear day) on phone — or just their own day.** This dramatically affects scope. Recommend that the **technician view on phone is read-only-plus-status-buttons**; full admin (route generation, clear day, etc.) stays desktop-only and can be hidden behind `lg:block`. Confirm.

---

## Estimated Effort

| Phase | Description | Estimate |
|---|---|---|
| Phase 1 | Schedule + Appointment Modal mobile | 1–2 weeks (one focused engineer) |
| Phase 2 | Other admin pages + tables + filters | 1–2 weeks |
| Phase 3 | Polish, landscape, a11y | 3–5 days, then ongoing |
| Real-device QA | iPhone, iPad, Browserstack pass | 1–2 days per phase |
| **Total** | | **3–4 weeks** to reach ~95% mobile usability |

---

## Risk Summary

| Risk | Likelihood | Mitigation |
|---|---|---|
| FullCalendar `listWeek` view doesn't satisfy technician workflow | Medium | Spike for 1 day on a real device with a real technician before committing |
| Drag-and-drop reschedule conflicts with mobile scroll on calendar | Medium | Disable drag-drop on `< md`; route through Edit dialog instead |
| iOS Safari viewport quirks (`100vh` ≠ visible height, soft-keyboard) | Medium-High | Use `100dvh` (already supported in modern Safari) and test on real keyboard-open scenarios |
| Hidden columns on mobile tables hide data tech *needs* | Medium | UX decision — show the truly essential columns only; add detail-on-tap |
| Photos panel inline styles drift from rest of design system | Low | Long-term refactor item; cosmetically OK as-is |

---

**Next:** read `02_SCHEDULE_TAB_DEEP_DIVE.md` for the priority area, then `05_RECOMMENDED_APPROACH.md` for the implementation plan.
