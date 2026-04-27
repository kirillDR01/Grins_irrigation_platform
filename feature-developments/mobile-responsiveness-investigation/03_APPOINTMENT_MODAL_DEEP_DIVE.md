# 03 — Appointment Modal Deep Dive (Priority Focus Area)

The user's second emphasis area. Technicians "press the appointment modals" throughout the day — this is the *primary* tap target on the Schedule tab.

**Headline finding:** **The combined AppointmentModal v2 is mostly mobile-ready already.** The team did the responsive work when shipping v2. The remaining work is polish — call out 4 specific issues to fix in Phase 1, plus a sub-component touch-target audit.

---

## 0. Audit Method

Files reviewed in `frontend/src/features/schedule/components/AppointmentModal/`:

```
ActionCard.tsx               LinkButton.tsx
ActionTrack.tsx              MapsPickerPopover.tsx
AppointmentModal.tsx         ModalFooter.tsx
AssignedTechCard.tsx         ModalHeader.tsx
CustomerHero.tsx             NotesPanel.tsx
EstimateSheetWrapper.tsx     PaymentSheetWrapper.tsx
PhotoCard.tsx                PhotosPanel.tsx
PropertyDirectionsCard.tsx   ScopeMaterialsCard.tsx
SecondaryActionsStrip.tsx    TagEditorSheet.tsx
TimelineStrip.tsx            V2LinkBtn.tsx
```

Plus the appointment-form path used by the create/edit dialogs:
- `components/AppointmentForm.tsx`
- `components/AppointmentDetail.tsx` (legacy)
- `shared/components/AppointmentAttachments.tsx`

---

## 1. Container Layout — ✅ Already Mobile-Ready

`AppointmentModal.tsx:289-296`
```tsx
className={[
  'fixed z-50 bg-white border border-[#E5E7EB] shadow-2xl overflow-hidden flex flex-col',
  // Desktop: 560 px centered, max 90vh
  'sm:rounded-[18px] sm:w-[560px] sm:max-h-[90vh]',
  'sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2',
  // Mobile: full-width bottom sheet, 92vh
  'max-sm:rounded-t-[20px] max-sm:rounded-b-none max-sm:w-full max-sm:bottom-0 max-sm:left-0 max-sm:right-0 max-sm:max-h-[92vh]',
].join(' ')}
```

Plus the grab handle at line 302:
```tsx
<div className="sm:hidden flex justify-center pt-3 pb-1 flex-shrink-0">
  <div className="w-11 h-[5px] rounded-full bg-[#D1D5DB]" />
</div>
```

This is correct. Body has `overflow-y-auto flex-1` so content scrolls. **No changes needed here.**

---

## 2. ModalHeader — ✅ Good

`ModalHeader.tsx:37-82`

Title (26 px font), status pill, schedule line, close button (40 × 40 px). Flex with `flex-wrap` on the badge row (line 40). Close button meets the recommended 44 px touch-target minimum (40 px × 40 px is technically a hair under, but Apple HIG calls for 44 × 44 — flag for polish).

**Minor polish:** bump close button to `w-11 h-11` (44 × 44) to align strictly with HIG.

---

## 3. TimelineStrip — ✅ Good (with caveat)

`TimelineStrip.tsx:30-33`

```tsx
<div className="overflow-x-auto" style={{ minWidth: 0 }}>
  <div style={{ minWidth: 240 }}>
    {/* steps */}
  </div>
</div>
```

`minWidth: 240` ensures the steps stay legible; `overflow-x-auto` lets users scroll if the container is narrower. Step labels at 11 px and timestamps at 10 px are at the edge of legibility on mobile but workable.

**Polish:** consider bumping `fontSize: 12` for the step labels on mobile. Optional.

---

## 4. ActionTrack — ⚠️ Marginal (Phase 1)

`ActionTrack.tsx:67-96`

```tsx
<div className="px-5 pb-4 flex gap-2 flex-shrink-0">
  <ActionCard label="En route" ... />
  <ActionCard label="On site" ... />
  <ActionCard label="Complete" ... />
</div>
```

Each `ActionCard` is `flex-1 min-h-[104px]`. On iPhone SE (375 px) with `px-5` (40 px total) and `gap-2` (16 px total), each card is `(375 - 40 - 16) / 3 ≈ 106 px wide`. Tight but workable.

The 12-px label text + 10-px mono timestamp can collide on very narrow viewports if iOS dynamic type is enlarged.

**Fix direction:**
- Reduce padding to `px-4` and gap to `gap-1.5` on mobile.
- Or: stack the 3 cards vertically on `< sm:` (`flex-col sm:flex-row`).
- Or: reduce icon size and tighten label/timestamp spacing on mobile.

**Severity:** Low-Medium. Functional today but fragile.

---

## 5. ModalFooter — ✅ Good

`ModalFooter.tsx:23-39`

Three `LinkButton`s, each `flex-1 min-h-[44px]`. `flex-wrap` on the row. Touch targets meet HIG. **No changes.**

---

## 6. SecondaryActionsStrip — ✅ Good

`SecondaryActionsStrip.tsx:37`
```tsx
<div className="px-5 pb-4 flex gap-2 flex-wrap flex-shrink-0">
```
`flex-wrap` is the key — buttons wrap to row 2 on narrow widths. **Working as designed.**

---

## 7. PhotosPanel — ⚠️ Phase 1 polish

`PhotosPanel.tsx`

This one is the most stylistically off-pattern in the modal — it uses **inline styles instead of Tailwind classes**, which means it bypasses the entire responsive system.

### Issue 7.1 — Fixed photo card widths
`PhotoCard.tsx`: 180 px wide × 134 px tall photo cards. Strip is `overflow-x: auto` so the user can scroll horizontally — works on mobile. UX is cramped (only ~2 cards visible at a time on 375 px).

### Issue 7.2 — Upload buttons fine, but inline-styled
Upload and "Take photo" buttons are `minHeight: 48 px` (good), inline styled. Need to be reviewed for color contrast and consistency with the rest of the design system.

### Issue 7.3 — Add-more tile is fixed 110 px
`PhotosPanel.tsx:374, 386` — `width: 110px, minHeight: 134px`. Also fine, also inline-styled.

**Severity:** Low. Photos work on mobile. Polish item: consider migrating to Tailwind classes during Phase 1 so we can apply `max-sm:w-32` style mobile reductions.

---

## 8. NotesPanel — ⚠️ Phase 1 polish

`NotesPanel.tsx`

### Issue 8.1 — Save / Cancel buttons may overflow on iPhone SE 1st gen (320 px)

`NotesPanel.tsx:218-263`
```tsx
<div style={{ marginTop: 14, display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
  <button style={{ ..., minWidth: 120, padding: '12px 28px' }}>Cancel</button>
  <button style={{ ..., minWidth: 140, padding: '12px 28px' }}>Save Notes</button>
</div>
```

`120 + 140 + 12 (gap) + 40 (panel padding * 2) = 312 px`. Above 320 px iPhone SE 1st gen viewport, but with iOS auto-zoom on `<input>` focus the visual viewport can shrink. **Fragile.**

**Fix direction:**
- Add `flex-wrap` to the button container.
- Or: reduce minWidth to `min-w-[100px]` on mobile.
- Or: Cancel goes full-width above Save on mobile, side-by-side on `sm:`+.

### Issue 8.2 — Textarea `minHeight: 150` in landscape iPhone

In landscape iPhone (e.g., 14 Pro Max: 926 × 430), 150 px textarea + buttons + header = ~270 px, plus the modal header above. Modal `max-h: 92vh` of 430 = 396 px usable. Fits, but tight.

**Fix direction:** consider `max-h: 30vh` on the textarea so it doesn't dominate the viewport.

### Issue 8.3 — Inline styles, like PhotosPanel
Same migration recommendation.

**Severity:** Medium. The 320 px button-overflow issue could trigger on the smallest devices.

---

## 9. CustomerHero — ✅ Good

`CustomerHero.tsx:32-98`

11 × 11 avatar, large name, contact row with phone link (32 px button — barely under HIG, polish to 44 px), tag row uses `flex flex-wrap gap-2`. **Fine.**

---

## 10. PropertyDirectionsCard — ✅ Good

`PropertyDirectionsCard.tsx:30-60`

Full-width "Get directions" button (`w-full py-2.5`) that opens MapsPickerPopover with three options (Apple Maps / Google Maps / Waze). **Works on mobile.**

---

## 11. MapsPickerPopover — ⚠️ Marginal

`MapsPickerPopover.tsx:56-105`

Renders as `absolute left-0 right-0 bottom-full mb-2`. Inside the modal's bottom-sheet on mobile, "bottom-full" means it pops *upward* from its trigger — generally fine. But if the trigger is near the modal's top, the popover may clip outside the modal.

**Severity:** Low. Works in 95% of cases. Edge case if modal is scrolled to a position where the directions button is near the top.

**Fix direction (optional):** convert to a Radix Popover or DropdownMenu so it gets portal-based positioning.

---

## 12. ScopeMaterialsCard / AssignedTechCard — ✅ Good

Both use `flex flex-wrap gap-2`. No fixed widths. **No changes.**

---

## 13. TagEditorSheet — ⚠️ Stacking-context bug

`AppointmentModal.tsx:589`
```tsx
{openSheet === 'tags' && customer && (
  <div className="absolute inset-0 z-10">
    <TagEditorSheet ... />
  </div>
)}
```

### The problem
On mobile, the AppointmentModal itself is `position: fixed` (the bottom-sheet). When a child uses `absolute inset-0`, it's positioned relative to the nearest positioned ancestor — which is the `fixed` modal, not the viewport.

So the TagEditorSheet *fills the modal*, not the viewport. That actually works visually, but:
- It overlays the modal's grab handle (UX confusion)
- It doesn't have its own backdrop
- Z-index `z-10` is local to the modal's stacking context, not global — fine here, but a footgun

### Fix direction
Two options:
- **Option A (minimal change):** keep `absolute inset-0`, but document that these sub-sheets are *replacing* the modal content, not overlaying it. Add a header with a back button so users can return to the main modal.
- **Option B (cleaner):** lift these sub-sheets out as their own Radix Sheet / Dialog at the `<RootProvider>` level. Trade-off: more code but proper stacking, backdrops, animation.

**Severity:** Low cosmetic, Medium UX. Sub-sheets are functional but feel like overlays when they're actually replacements.

---

## 14. PaymentSheetWrapper / EstimateSheetWrapper — Same as TagEditorSheet

Same `absolute inset-0` pattern at `AppointmentModal.tsx:600` and `:612`. Same issue.

These are higher-stakes than the tag editor — payment is a critical flow. On a real iPhone, when you tap "Collect Payment" inside the modal:
1. The PaymentSheetWrapper renders inside the modal
2. The Stripe Terminal SDK takes over the inside of that sheet
3. If the user dismisses, they're back in the modal

**This actually works** — it's just architecturally a smell, not a bug. But during Phase 1 testing, *do* verify on a real iPhone with a real Stripe Terminal flow that:
- The Stripe iframe / web view doesn't get clipped by the `overflow-hidden` parent
- The modal scroll position is preserved
- Dismissing the payment sheet returns to the right modal state

---

## 15. AppointmentForm (used in create/edit dialogs)

`AppointmentForm.tsx`

This is *not* in the AppointmentModal/v2 folder; it's the form used by the "+ New Appointment" and "Edit Appointment" dialogs from `SchedulePage`.

Looks responsive overall — single-column form with full-width inputs. Two issues:

### Issue 15.1 — Time inputs side-by-side (line ~405)
```tsx
<div className="grid grid-cols-2 gap-4">
  <Input type="time" ... />
  <Input type="time" ... />
</div>
```
Tight on iPhone SE (~155 px each). Native iOS time picker is ~110 px wide so it fits, but the label + input combo gets cramped.

**Fix direction:** `grid-cols-1 sm:grid-cols-2`.

### Issue 15.2 — Otherwise OK
The dialog containing this form is `max-w-lg` with the Dialog primitive's mobile floor. Form layout is already mostly stacked-vertical. **Mostly fine.**

---

## 16. AppointmentDetail (legacy)

`AppointmentDetail.tsx` (35 KB, legacy detail view that AppointmentModal v2 replaced)

If this is truly deprecated and not used anywhere, **delete it** — no point investing in mobile responsiveness for code about to go away.

If still in use as a fallback, audit carefully. Without doing the full review I'd estimate: same issues as the rest of the legacy code (fixed widths, dense filter rows).

**Recommend confirming deprecation status before Phase 1.**

---

## 17. AppointmentAttachments

`shared/components/AppointmentAttachments.tsx`

Used by AppointmentModal for file uploads (separate from the customer-photo PhotosPanel). Spot check:
- Renders a list of attached files
- Has upload button
- No fixed-width grid issues observed

**Likely fine on mobile.** Verify in Phase 1 testing.

---

## 18. PaymentCollector (legacy)

`PaymentCollector.tsx` (15 KB)

Field tooling for collecting payment manually (cash/check) before the Stripe Terminal flow. Form-heavy. Likely has some grid issues. Worth a Phase 1 review since this is a technician-facing flow.

---

## 19. StaffWorkflowButtons / BreakButton

Technician-facing inline buttons. Brief review:
- `StaffWorkflowButtons.tsx`: 4.6 KB, simple button row. Probably wraps fine.
- `BreakButton.tsx`: 4.8 KB, single button + dialog. Probably fine.

**No flags. Verify in Phase 1 testing.**

---

## 20. Touch-Target Audit Summary

Apple HIG: 44 × 44 px minimum tap target. Current state:

| Component | Touch target | HIG-compliant? |
|---|---|---|
| ModalHeader close button | 40 × 40 | ⚠️ 4 px under |
| CustomerHero phone-call button | 32 × 32 | ❌ 12 px under |
| ActionCard | 104 × ~106 | ✅ |
| ModalFooter LinkButtons | min-h-[44px] | ✅ |
| SecondaryActionsStrip V2LinkBtn | minHeight: 44 | ✅ |
| PhotosPanel upload buttons | 48+ | ✅ |
| NotesPanel Save/Cancel | min-w-[120px], h ~44 | ✅ |
| Calendar event tap target | varies | ⚠️ events sometimes < 30 px tall |
| FullCalendar nav buttons | varies | ❓ FullCalendar default |

**Phase 1 quick wins:** bump close button to 44 × 44, phone-call button to 44 × 44.

---

## 21. Summary Table — Appointment Modal Components

| Component | Phone | Tablet | Phase 1 action |
|---|---|---|---|
| Container layout | ✅ | ✅ | None |
| ModalHeader | ⚠️ Close 40px | ✅ | Bump to 44 |
| TimelineStrip | ✅ | ✅ | None |
| ActionTrack | ⚠️ Marginal | ✅ | Reduce padding/gap on mobile |
| ModalFooter | ✅ | ✅ | None |
| SecondaryActionsStrip | ✅ | ✅ | None |
| **PhotosPanel** | ⚠️ Cramped | ✅ | Migrate inline styles → Tailwind, smaller cards mobile |
| PhotoCard | ✅ Scrolls | ✅ | None (or tighten in Phase 2) |
| **NotesPanel** | ⚠️ Buttons risk overflow | ✅ | Add flex-wrap, migrate inline styles |
| ActionCard | ✅ | ✅ | None |
| CustomerHero | ⚠️ Phone btn 32px | ✅ | Bump phone btn to 44 |
| PropertyDirectionsCard | ✅ | ✅ | None |
| MapsPickerPopover | ⚠️ Edge clipping | ✅ | Convert to Radix Popover (Phase 2) |
| ScopeMaterialsCard | ✅ | ✅ | None |
| AssignedTechCard | ✅ | ✅ | None |
| **TagEditorSheet (overlay)** | ⚠️ Stacking | ⚠️ Stacking | Lift to Radix Sheet OR add back-button header |
| **PaymentSheetWrapper** | ⚠️ Stacking | ⚠️ Stacking | Same |
| **EstimateSheetWrapper** | ⚠️ Stacking | ⚠️ Stacking | Same |
| AppointmentForm (dialog form) | ⚠️ Time inputs | ✅ | `grid-cols-1 sm:grid-cols-2` |
| AppointmentDetail (legacy) | ❓ | ❓ | Confirm deprecation, delete if unused |
| AppointmentAttachments | ✅ likely | ✅ | Spot-check in QA |
| PaymentCollector (legacy) | ❓ | ❓ | Phase 1 spot-check |

---

## 22. The Phase 1 Punch List for Appointment Modal

In priority order:

1. **Fix nested overlay sheets** (`AppointmentModal.tsx:589, 600, 612`) — either lift into proper Radix Sheets or add back-button headers so users understand they're replacement views, not overlays.
2. **NotesPanel button overflow** (`NotesPanel.tsx:218-263`) — add `flex-wrap` or reduce min-width.
3. **Touch-target audit** — close button, phone-call button to 44×44.
4. **Time input grid** in AppointmentForm (`AppointmentForm.tsx:~405`) — `grid-cols-1 sm:grid-cols-2`.
5. **PhotosPanel polish** — migrate inline styles to Tailwind so we can apply mobile-specific reductions.
6. **ActionTrack tightness** — reduce padding/gap on mobile if testing reveals issues.

Confirm deprecation status of `AppointmentDetail.tsx` and `PaymentCollector.tsx` before sinking time into them.

---

**Net estimate:** ~3 days of focused engineering for the entire AppointmentModal mobile polish, including a real-iPhone QA pass.

**Next:** `04_OTHER_PAGES_AUDIT.md` for the rest of the dashboard.
