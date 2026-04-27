# 01 — Current Responsive State (What Already Works)

A baseline. These are the responsive patterns the team has already shipped and that we should not regress.

---

## 1. Stack & Configuration

### Viewport meta tag — present and correct
```html
<!-- frontend/index.html:6 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
```
Standard, no `user-scalable=no` (good — that breaks accessibility), no `viewport-fit=cover` (we'll want this later for iPhone notches/safe-area).

### Tailwind CSS v4 with default breakpoints
- `sm:` 640 px
- `md:` 768 px
- `lg:` 1024 px
- `xl:` 1280 px
- `2xl:` 1536 px

No custom breakpoints defined. All responsive logic comes from default classes.

### Body min-width
```css
/* frontend/src/index.css:53 */
body { min-width: 320px; min-height: 100vh; }
```
The `min-width: 320px` floor is appropriate (covers iPhone SE 1st gen — the smallest iPhone Apple still supports).

---

## 2. Layout & Navigation — Working

The `Layout.tsx` component (`frontend/src/shared/components/Layout.tsx`) has a complete responsive sidebar pattern:

| Behavior | Breakpoint | Implementation |
|---|---|---|
| Sidebar visible by default | `lg:` (≥1024 px) | `lg:translate-x-0` (line 168) |
| Sidebar collapsed offscreen | `< lg` | `-translate-x-full` initial state |
| Hamburger button visible | `< lg` | `lg:hidden` on Menu/X button (line 243) |
| Backdrop overlay | `< lg` | `bg-black/50 lg:hidden` (line 159) |
| Main content padding | always | `p-4 lg:p-6` (line 331) |
| Global search | `≥ lg` only | `hidden lg:flex` (line 261) |
| User menu | `≥ sm` only | `hidden sm:block` (line 324) |
| Page title shown | `< lg` only | `text-lg font-semibold lg:hidden` (line 256) |

This is the *one* clean responsive surface in the app. **Don't change it** — only make sure new features stay aligned with this pattern.

**Caveat:** the sidebar lists 15 navigation items in a vertical column. Inside the mobile drawer this is fine (drawer is full-height, scrollable). But the order/grouping was not designed with technicians in mind — for them, "Schedule" is the only item that matters during the workday. Consider a **role-based reordering** so technicians see Schedule pinned to the top.

---

## 3. Dialog Primitive — Has Built-in Mobile Floor

```tsx
// frontend/src/components/ui/dialog.tsx:64
className={cn(
  "bg-white ... fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] rounded-2xl shadow-xl overflow-hidden duration-200 outline-none sm:max-w-lg",
  className
)}
```

The `max-w-[calc(100%-2rem)]` floor means even when a consumer passes `max-w-2xl` or `max-w-5xl`, the dialog will never be wider than `viewport - 32px` on small screens. This is the reason most dialogs in the app *don't actually overflow* on iPhone.

The `DialogFooter` also stacks correctly:
```tsx
// dialog.tsx:99
"flex flex-col-reverse gap-2 sm:flex-row sm:justify-end p-6 ..."
```
Footer buttons go full-width on mobile and into a row at `sm:` breakpoint.

**This is the strongest responsive primitive in the codebase.** Most dialog issues stem from the *content inside* the dialog (forms, tables) not from the dialog itself.

---

## 4. AppointmentModal v2 — Already Mobile-Aware

The combined appointment modal (`frontend/src/features/schedule/components/AppointmentModal/AppointmentModal.tsx`) is the strongest mobile-aware feature surface in the app:

```tsx
// AppointmentModal.tsx:289-296
className={[
  'fixed z-50 bg-white border border-[#E5E7EB] shadow-2xl overflow-hidden flex flex-col',
  // Desktop: fixed 560px centered
  'sm:rounded-[18px] sm:w-[560px] sm:max-h-[90vh]',
  'sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2',
  // Mobile: full-width bottom sheet
  'max-sm:rounded-t-[20px] max-sm:rounded-b-none max-sm:w-full max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:max-h-[92vh]',
].join(' ')}
```

Plus a grab handle for mobile:
```tsx
// line 302
<div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
  <div className="w-11 h-[5px] rounded-full bg-[#D1D5DB]" />
</div>
```

The body is scrollable (`overflow-y-auto flex-1`), header/footer are flex-shrink-0, and most sub-cards stack vertically with `px-5 pb-4` consistent spacing — works fine at any width.

Sub-component scorecard (deeper dive in `03_APPOINTMENT_MODAL_DEEP_DIVE.md`):

| Sub-component | Mobile-ready? |
|---|---|
| ModalHeader | ✅ Good — flex-wrap on badges, close button is 40 px |
| TimelineStrip | ✅ Good — has `overflow-x-auto`, scrolls if needed |
| ActionTrack | ⚠️ Marginal — three cards `flex-1` shrink to ~100 px each on iPhone SE |
| ModalFooter | ✅ Good — `flex-1` buttons with `min-h-[44px]` |
| SecondaryActionsStrip | ✅ Good — `flex-wrap` (line 37) |
| CustomerHero | ✅ Good — flexible, no fixed widths |
| PropertyDirectionsCard | ✅ Good |
| ScopeMaterialsCard | ✅ Good — `flex flex-wrap gap-2` |
| AssignedTechCard | ✅ Good |
| **PhotosPanel** | ⚠️ Needs polish — inline styles, fixed 180 px cards (scroll) |
| **NotesPanel** | ⚠️ Needs polish — fixed-width Save/Cancel may overflow < 320 px |
| **Nested sheets (Tags/Pay/Estimate)** | ⚠️ Stacking-context bug — `absolute inset-0` inside `fixed` parent |

---

## 5. Page-Level Patterns That Work

### `PageHeader` correctly stacks
```tsx
// frontend/src/shared/components/PageHeader.tsx:12
<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6">
```
Title goes on top, action goes below on mobile; row at `sm:`+. Clean.

### Dashboard cards use mobile-first grid
Most dashboards follow:
```tsx
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
```
This is the right pattern. **Where the pages break is usually inside the cards** (tables, charts) not in the grid itself.

### `InlineCustomerPanel` is a textbook responsive sheet
```tsx
// InlineCustomerPanel.tsx:67
<SheetContent
  className="w-full h-[90vh] rounded-t-2xl fixed bottom-0 left-0 right-0 overflow-y-auto md:w-[450px] md:h-full"
>
```
Bottom sheet on mobile, side sheet on desktop, both 90vh. **Good template for any future sheet.**

### `CancelAppointmentDialog` & `ClearDayDialog` — well-built
Both have `sm:max-w-lg`, footer with `flex-col gap-2 sm:flex-row`, no fixed-width inputs, and content that scales. **Use these as reference implementations** when reviewing other dialogs.

### Most cards have a `bg-white rounded-2xl border` shell
This visually communicates an information-block on every viewport size. The padding (`p-4`, `p-6`) is sufficient on mobile.

### Toast positioning via `sonner`
The Toaster from `@/components/ui/sonner` (line 4 of `App.tsx`) — `sonner` defaults to bottom-right but respects safe areas on iOS. Should test but expected to work.

---

## 6. Things That Will Hurt Less Than You Think

These look bad on first read but are non-issues in practice:

- **`max-w-2xl`, `max-w-3xl`, `max-w-5xl` on dialogs** — they're capped by the Dialog primitive's `max-w-[calc(100%-2rem)]` floor. Content inside the dialog is the actual concern, not the dialog width itself.
- **Tables wider than the viewport** — `Table` primitive (`table.tsx:8`) wraps in `overflow-x-auto`. They scroll horizontally. The UX issue isn't *broken*, it's *confusing* (no scroll affordance).
- **`min-h-screen` on the Layout root** — uses 100vh which on iOS Safari is wrong (includes the address bar even when scrolled), but in practice the user can scroll, so the visual artifact is minor. Worth eventually replacing with `100dvh` but not urgent.

---

## 7. Things That Look Risky and ARE Risky

These genuinely break on mobile and need fixing (full list in `07_FILE_INVENTORY.md`):

- FullCalendar `timeGridWeek` default view → broken < 900 px
- Schedule page action bar → broken < 1280 px
- JobTable / JobPickerPopup → broken < 1100 px
- Sales pipeline table → broken < 1100 px
- AppointmentList filter inputs → broken < 600 px
- Charts with fixed `h-80` → squishy on landscape phone
- Inline-styled NotesPanel buttons → broken < 320 px

---

**Next:** `02_SCHEDULE_TAB_DEEP_DIVE.md` for the priority area.
