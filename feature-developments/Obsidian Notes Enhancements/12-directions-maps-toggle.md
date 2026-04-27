# 12 — Get Directions toggles Google Maps or Apple Maps

**Request (paraphrased):**
> When we click Get Directions, it should toggle either Google Maps or Apple Maps.

**Status:** ✅ IMPLEMENTED

---

## What exists today

- "Get directions" button: `frontend/src/features/schedule/components/AppointmentModal/PropertyDirectionsCard.tsx:42-48`. Tapping opens a popover.
- Maps picker: `frontend/src/features/schedule/components/AppointmentModal/MapsPickerPopover.tsx:24-102`. User selects Apple Maps (lines 65-85) or Google Maps (lines 86-103). Uses either address or coordinates.
- Apple Maps URL uses the `maps://` scheme with a web fallback for non-iOS (line 73).
- Both buttons have distinct branding (Apple teal, Google blue). No hard-coded default — always user's choice.

## TODOs

- [ ] **TODO-12a** *(optional)* Remember the user's last choice per device so the preferred provider is pre-selected on the next tap.
- [ ] **TODO-12b** *(optional, verify only)* Confirm the Apple link gracefully falls back on Android browsers and that the Google link still works on iOS. Should already be true — worth a quick field test.

## Clarification questions ❓

1. Should we auto-default by device (iOS → Apple Maps, others → Google Maps) instead of always showing the picker? Saves one tap on mobile. Or keep the picker for explicit choice?
