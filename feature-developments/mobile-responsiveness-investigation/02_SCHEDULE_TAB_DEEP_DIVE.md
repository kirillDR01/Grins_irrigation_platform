# 02 — Schedule Tab Deep Dive (Priority Focus Area)

The user explicitly called this out as the highest-priority surface:

> *"Emphasize specifically on the scheduling tab because that's what technicians are actually going to use throughout the day the most. They're going to look at the schedule tab and they're going to press the appointment modals."*

This document goes deep on every component in the Schedule feature.

---

## 0. Audit Method

Files reviewed in `frontend/src/features/schedule/`:
- `pages/SchedulePage.tsx`
- `pages/PickJobsPage.tsx`
- `components/CalendarView.tsx` + `CalendarView.css`
- `components/DaySelector.tsx`
- `components/AppointmentList.tsx`
- `components/AppointmentForm.tsx`
- `components/JobSelector.tsx` + `JobSelectorCombobox.tsx`
- `components/JobPickerPopup.tsx`
- `components/InlineCustomerPanel.tsx`
- `components/FacetRail.tsx`
- `components/JobTable.tsx`
- `components/SchedulingTray.tsx`
- `components/RescheduleRequestsQueue.tsx`
- `components/NoReplyReviewQueue.tsx`
- `components/CancelAppointmentDialog.tsx`
- `components/ClearDayDialog.tsx`
- `components/RestoreScheduleDialog.tsx`

---

## 1. SchedulePage — Container

`frontend/src/features/schedule/components/SchedulePage.tsx`

### What it does
Top-level page: PageHeader + DaySelector + Calendar/List view toggle + several queues + dialogs.

### What's broken on mobile

#### Issue 1.1 — Action bar overflows
```tsx
// SchedulePage.tsx:331-395
action={
  <div className="flex items-center gap-4">
    <LeadTimeIndicator />
    <ClearDayButton />
    <Tabs value={viewMode}> ... </Tabs>     // 2 tab buttons
    <Button>Add Jobs</Button>
    <Button>Pick jobs to schedule</Button>
    {draftCount > 0 && <SendAllConfirmationsButton />}
    <Button>+ New Appointment</Button>
  </div>
}
```
**7 elements in a `flex items-center gap-4` row with no wrap, no breakpoint variants.** Total natural width ≈ 900–1,100 px depending on draft count. Overflows clip silently — buttons get pushed off the right edge of the page.

**On iPhone (375 px):** approximately the first 1.5 buttons are visible. Everything else is unreachable.

**Fix direction:**
- Below `md:`: collapse all secondary buttons into an overflow `DropdownMenu` triggered by a "More" button. Keep only `+ New Appointment` as a primary action.
- At `md:`+: drop into a 2-row layout (LeadTimeIndicator + tabs on row 1, action buttons on row 2).
- At `lg:`+: current single-row layout works.

#### Issue 1.2 — DialogContent for create/edit appointment
```tsx
// SchedulePage.tsx:441
<DialogContent className="max-w-lg" aria-describedby="...">
```
`max-w-lg` (32 rem = 512 px) is fine for most screens; the Dialog primitive has the `max-w-[calc(100%-2rem)]` floor so it won't overflow on iPhone. **Not actually broken**, but the AppointmentForm inside it (see issue 4 below) has its own mobile issues.

#### Issue 1.3 — Page wraps already use `space-y-6` correctly
```tsx
// SchedulePage.tsx:325
<div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
```
This is fine — vertical stacking works at any width. Good baseline.

---

## 2. CalendarView — The Big One

`frontend/src/features/schedule/components/CalendarView.tsx`

### What it does
FullCalendar wrapper showing weekly schedule with drag-drop, custom event content, and day-header send-confirmation buttons.

### What's broken on mobile

#### Issue 2.1 — `timeGridWeek` default view does not fit on a phone
```tsx
// CalendarView.tsx:339
initialView="timeGridWeek"
firstDay={1}
headerToolbar={{
  left: 'prev,next today',
  center: 'title',
  right: 'dayGridMonth,timeGridWeek,timeGridDay',
}}
slotMinTime="06:00:00"
slotMaxTime="20:00:00"
slotDuration="00:30:00"
```

**`timeGridWeek` renders 7 columns × 28 rows (06:00–20:00 in 30-min slots).** Even on a 768 px iPad portrait this is ~108 px per column — barely usable. On a 375 px iPhone, it's mathematically impossible — the time-axis label column alone consumes ~50 px, leaving 7 columns at ~46 px each, less than two letters of staff name.

Worse, the FullCalendar header toolbar has *three* button groups (`prev next today` | `title` | `dayGridMonth,timeGridWeek,timeGridDay`) which alone consume ~600 px before the calendar even renders.

**Fix direction:**
- Detect viewport width with a custom hook (`useMediaQuery('(min-width: 768px)')`).
- On mobile, set `initialView="listWeek"` — FullCalendar's built-in vertical-list view that groups appointments by day.
- Simplify `headerToolbar` on mobile: `{ left: 'prev,next', center: 'title', right: 'today' }` (or just `'prev,next today'` on left, `title` on right).
- Disable the view-switcher row on mobile entirely (3 view buttons unusable on small screens).
- Hide the existing `Tabs` view-toggle in `SchedulePage.tsx:343` on mobile (`hidden md:flex`) — it's redundant with FullCalendar's built-in switcher anyway.

This is the single biggest UX win for technicians. ServiceTitan, Jobber, and Housecall Pro all default to a list view on mobile for exactly this reason.

#### Issue 2.2 — Drag-drop reschedule conflicts with mobile scroll
```tsx
// CalendarView.tsx:351-352
editable={true}
selectable={true}
```
On a touch device, holding-and-dragging an event collides with vertical page scroll. FullCalendar handles this with a `longPressDelay` but the default is 1 second — accidentally trips during normal scrolling.

**Fix direction:**
- Disable `editable={isMobile ? false : true}` on mobile.
- Mobile reschedule path: tap → modal → Edit dialog (already works).
- Or: keep drag enabled but increase `longPressDelay` to 1500 ms to reduce accidental drags.

#### Issue 2.3 — Day cell `min-h-[120px]` on mobile is wasteful
```css
/* CalendarView.css:29 */
.fc .fc-daygrid-day {
  @apply min-h-[120px] border-r border-b border-slate-50 p-2;
}
```
On mobile in `dayGridMonth` view, 120 px × 6 weeks = 720 px just for the calendar grid, plus header. Reduce to `min-h-[60px]` on mobile.

**Fix direction:** add a mobile media query.
```css
.fc .fc-daygrid-day {
  @apply min-h-[60px] sm:min-h-[120px] ...;
}
```

#### Issue 2.4 — Custom event content has too much info for narrow events
```tsx
// CalendarView.tsx:202-225
<div className="flex items-center gap-1 w-full overflow-hidden">
  <div className="flex-1 truncate">
    <span className="text-[10px] text-slate-500">{eventInfo.timeText}</span>
    {isPrepaid && <span>... PREPAID ...</span>}
    {attachmentCount > 0 && <span>... 📎N ...</span>}
    <span className="ml-1 truncate">{eventInfo.event.title}</span>
  </div>
  {isDraft && appointment && <SendConfirmationButton appointment={appointment} compact />}
</div>
```
Even the "compact" SendConfirmationButton inside an event is ~24 px square — on a narrow column this swallows half the event width.

**Mobile-friendly approach:** in `listWeek` view, FullCalendar gives each event a full row, so this all works. The truncation issues are exclusive to grid views, which we'd hide on mobile anyway.

---

## 3. DaySelector — Working

`frontend/src/features/schedule/components/DaySelector.tsx`

7 day buttons in a `flex gap-2` row, each `min-w-[70px]`. Fits within `7 × 70 + 6 × 8 = 538 px`. **Will overflow iPhone (375 px) by ~160 px.**

**Fix direction:**
- Wrap the row in `overflow-x-auto`, the buttons keep their fixed width, user scrolls horizontally. Easy fix.
- Or: shrink to `min-w-[44px]` on mobile (`min-w-[44px] sm:min-w-[70px]`), shorten the day labels (M, T, W instead of Mon, Tue), keep date number prominent.

**Severity:** low — buttons are still tappable, day labels are still legible, just requires a horizontal swipe.

---

## 4. AppointmentForm — One small issue

`frontend/src/features/schedule/components/AppointmentForm.tsx`

```tsx
// AppointmentForm.tsx:405 (approximate, in the time-window inputs)
<div className="grid grid-cols-2 gap-4">
  <Input type="time" {...} />  {/* start */}
  <Input type="time" {...} />  {/* end */}
</div>
```
Two time inputs side-by-side on iPhone are ~155 px each (375 - 32 padding - 16 gap = 327, /2 = 163). The native `<input type="time">` chrome on iOS is about 110 px wide, so they technically fit, but barely.

Otherwise the form uses `grid grid-cols-1` with full-width fields. **Mostly fine.**

**Fix direction:** Optional — change time inputs to `grid-cols-1 sm:grid-cols-2` so they stack vertically on the smallest screens.

---

## 5. AppointmentList — Filter row breaks

`frontend/src/features/schedule/components/AppointmentList.tsx`

### Issue 5.1 — Fixed-width filter inputs

```tsx
// AppointmentList.tsx:254-296 (approximate)
<div className="flex flex-wrap gap-4 ...">
  <Select className="w-48"> {/* status */}
  <Input type="date" className="w-40" /> {/* from */}
  <Input type="date" className="w-40" /> {/* to */}
  ...
</div>
```
`w-48` (192 px) + `w-40` (160 px) + `w-40` = 512 px for filters alone, plus gaps. With `flex-wrap` they stack but the `w-40` date inputs are *narrower than iPhone safe-content width* and end up centered with empty space around them — cosmetically awkward.

**Fix direction:**
- Change to `w-full sm:w-48` and `w-full sm:w-40` — full-width on mobile, fixed at `sm:`+.
- Or: replace with `flex-1 min-w-[140px]` so they fill available space.

### Issue 5.2 — Underlying table has its own scroll
The list view itself has `overflow-x-auto` (line 307) wrapping the `<table>`. **This works** — table scrolls horizontally on mobile. UX could be better but it's not broken.

---

## 6. JobSelector + JobSelectorCombobox

`frontend/src/features/schedule/components/JobSelector.tsx` (legacy; mostly unused now)
`frontend/src/features/schedule/components/JobSelectorCombobox.tsx` (current)

### JobSelectorCombobox — works
Uses `PopoverContent className="w-[var(--radix-popover-trigger-width)]"` which mirrors the trigger width. `ScrollArea max-h-[300px]`. Good mobile UX.

### JobSelector — broken (legacy)
Lines 137 and 169:
```tsx
<DialogContent className="max-w-[100vw] h-full max-h-[100vh] flex flex-col rounded-none md:max-w-3xl">
  ...
  <SelectTrigger className="w-full min-h-[44px] text-sm md:w-[180px]" />
```
The dialog itself is full-screen on mobile (good), but the inner table has no defined columns and won't fit on iPhone.

**Severity:** Medium — but this is **deprecated** and replaced by `PickJobsPage` (the current path). Recommend keeping it functional on iPad but not optimizing for iPhone.

---

## 7. PickJobsPage + JobTable + FacetRail + SchedulingTray

This is the **single most important workflow** for daily route building. It's also the most broken on mobile.

### PickJobsPage layout
```tsx
// PickJobsPage.tsx:315
<div className="grid grid-cols-1 lg:grid-cols-[240px_1fr]">
  <FacetRail />          // hidden < lg, opens as Sheet
  <main>
    <JobTable />         // 6 hard-coded columns
    <SchedulingTray />   // sticky bottom, grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr]
  </main>
</div>
```

### Issue 7.1 — JobTable hard-coded column widths total ~1,100 px

```tsx
// JobTable.tsx:101-108
<TableHead className="w-[220px]">Customer</TableHead>
<TableHead className="w-[180px]">Job Type</TableHead>
<TableHead className="w-[160px]">Tags</TableHead>
<TableHead className="w-[120px]">City</TableHead>
<TableHead className="w-[120px]">Requested</TableHead>
<TableHead className="w-[80px]">Priority</TableHead>
<TableHead className="w-[80px]">Duration</TableHead>
<TableHead className="w-[140px]">Equipment</TableHead>
```
Total **= 1,100 px**. The table is wrapped in `overflow-y-auto` (line 72) but has no `overflow-x-auto`, so the table escapes the parent container and hides under other elements rather than scrolling.

**Fix direction (highest priority):**
- Wrap the `<Table>` in `<div className="overflow-x-auto">`.
- Replace hard-coded `w-[NNNpx]` with `min-w-[NNNpx]`.
- On mobile (`< md`), hide low-priority columns (Equipment, Duration, Priority) using `hidden md:table-cell`.
- Stretch goal: replace the table with stacked cards on `< sm`. Each card shows customer + job type + a tap-to-expand for the rest. This is the pattern industry-leaders use.

### Issue 7.2 — FacetRail too wide for iPhone Sheet

```tsx
// FacetRail.tsx:51-66 (approximate)
<Sheet>
  <SheetTrigger className="lg:hidden">Filters</SheetTrigger>
  <SheetContent className="w-64">  {/* 256 px */}
    <FacetRailContent />
  </SheetContent>
</Sheet>
```
On iPhone (375 px), `w-64` (256 px) leaves only ~100 px of overlay area visible behind the sheet. **Functional but tight.**

**Fix direction:** `className="w-[85vw] sm:w-72"`.

### Issue 7.3 — SchedulingTray bottom panel grid

```tsx
// SchedulingTray.tsx:97
<div className="grid grid-cols-2 lg:grid-cols-[200px_260px_160px_160px_1fr] gap-3">
```
On iPhone, two columns at ~160 px each — date pickers and staff selects squeeze.

**Fix direction:** `grid-cols-1 sm:grid-cols-2 lg:grid-cols-[...]`.

### Severity assessment for PickJobsPage as a whole
**Currently broken on iPhone.** The job table is the entire point of the page, and it overflows in a way that hides the scroll affordance. Estimate this page at <10% usability on iPhone today.

**However**, this is the *route-generation* workflow. It's used by office staff, not technicians in the field. Question for product: do field techs need to use Pick Jobs To Schedule on their phone, or only to *view* their assigned route?

If techs only need to *view* their day, this page can stay desktop-only (`<div className="hidden lg:block">`) and we save days of work.

---

## 8. JobPickerPopup — Legacy, deprecated

`frontend/src/features/schedule/components/JobPickerPopup.tsx`

Same issues as PickJobsPage: 7-column table, fixed-width filter row. Also `max-w-5xl` dialog (~1024 px).

**Recommendation:** if this is truly deprecated, mark it `lg:` only or delete it. Don't invest in mobile responsiveness here.

---

## 9. InlineCustomerPanel — Working

```tsx
// InlineCustomerPanel.tsx:67
<SheetContent
  side="right"
  className="w-full h-[90vh] rounded-t-2xl fixed bottom-0 left-0 right-0 overflow-y-auto md:w-[450px] md:h-full"
>
```
Bottom sheet on mobile, side sheet on desktop. **Reference implementation** for any future inline panel.

---

## 10. RescheduleRequestsQueue / NoReplyReviewQueue

Both render as cards in a list. Likely fine on mobile. Spot-check during Phase 1 testing but not flagged for changes.

---

## 11. CancelAppointmentDialog / ClearDayDialog / RestoreScheduleDialog

Reviewed — all three are properly responsive. `sm:max-w-lg`, footer stacks on mobile, no fixed-width inputs. **Don't touch.**

---

## 12. Summary Table — Schedule Components

| Component | iPhone status | iPad status | Action |
|---|---|---|---|
| SchedulePage container | ⚠️ Action bar overflows | ✅ Works | Add `flex-wrap` + overflow menu |
| **CalendarView (`timeGridWeek`)** | ❌ **Broken** | ⚠️ Cramped | **Switch to `listWeek` ≤ md** |
| DaySelector | ⚠️ Overflows by ~160 px | ✅ Works | Add `overflow-x-auto` |
| AppointmentForm | ⚠️ Time inputs tight | ✅ Works | `grid-cols-1 sm:grid-cols-2` for time |
| AppointmentList filters | ⚠️ Date inputs awkward | ✅ Works | `w-full sm:w-40` |
| AppointmentList table | ✅ Has overflow-x | ✅ Works | None |
| JobSelectorCombobox | ✅ Works | ✅ Works | None |
| JobSelector (legacy) | ❌ Broken | ⚠️ Tight | Mark `lg:` only or delete |
| **PickJobsPage container** | ❌ **Broken** | ⚠️ Tight | **Hide < lg, or major refactor** |
| **JobTable** | ❌ **Broken** | ⚠️ Tight | **Wrap overflow-x, hide cols < md** |
| FacetRail Sheet | ⚠️ Too wide | ✅ Works | `w-[85vw] sm:w-72` |
| SchedulingTray | ⚠️ 2-col tight | ✅ Works | `grid-cols-1 sm:grid-cols-2` |
| JobPickerPopup (legacy) | ❌ Broken | ⚠️ Tight | Delete or `lg:`-only |
| InlineCustomerPanel | ✅ Works | ✅ Works | Reference impl |
| RescheduleRequestsQueue | ✅ Likely OK | ✅ Works | Spot-check |
| NoReplyReviewQueue | ✅ Likely OK | ✅ Works | Spot-check |
| Cancel/Clear/Restore Dialogs | ✅ Work | ✅ Work | Reference impls |

---

## 13. The Recommended Mobile Calendar UX

When a technician opens `/schedule` on their iPhone, they should see:

1. **Compact header** — page title + a single "+ New Appt" button. Other actions in a "More" menu.
2. **Day picker** — horizontal swipe, today highlighted.
3. **Today's appointments as a vertical list** (FullCalendar `listWeek` view filtered to today, or our own list rendering):
   - Time
   - Customer name + address (tap → directions)
   - Job type
   - Status badge
   - Big touch target (whole card is tappable → opens AppointmentModal)
4. **Status buttons inline on each card** (En Route / Arrived / Complete) for fast workflow without opening the modal — though full modal is one tap away.
5. **Pull-to-refresh** (sonner provides this, or use a manual refresh button — already present in AppointmentModal).

This pattern matches what real field-service technicians expect from Jobber, ServiceTitan, Housecall Pro, Workiz, and similar tools. The week-grid stays available but only on desktop.

---

**Next:** `03_APPOINTMENT_MODAL_DEEP_DIVE.md` for the modal-side priority work.
