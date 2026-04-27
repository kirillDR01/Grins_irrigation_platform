# 10 — Multi-staff calendar overlay toggles in Schedules tab

**Request (paraphrased):**
> In the main Schedules tab, admin should be able to toggle each staff member's calendar on/off, overlay them, and see how they stack. Pick one, several, or all (staff, crew, sales). This prevents double-booking when e.g. the salesperson needs to help staff-1 on Tuesday.

**Status:** 🟡 PARTIAL — toggle exists on the Map view; missing on the Calendar (week/month) view

---

## What exists today

- **Map view staff toggles:** `frontend/src/features/schedule/components/map/MapFilters.tsx:21-46`. Multiple staff selectable; their routes are visible/hidden on the map.
- **Calendar view:** `frontend/src/features/schedule/components/CalendarView.tsx` — appointments are color-coded by staff_id (line 115), so visually distinct, but there is **no filter / toggle UI** to hide a specific staff member's events. All data displays at once.
- Appointments carry `staff_id` so the data to filter by exists.

## TODOs

- [ ] **TODO-10a** Lift the staff-filter control out of `MapFilters.tsx` into a shared `ScheduleStaffFilter` component usable in both Map and Calendar views.
- [ ] **TODO-10b** Consume the filter in `CalendarView.tsx` to hide events whose `staff_id` is deselected.
- [ ] **TODO-10c** Persist the selected set per user (ties to **TODO-03e** user-preferences) so each user sees their default on login without cross-contamination between Kirill's phone and Voss's phone.
- [ ] **TODO-10d** Add a legend / color key that survives when overlaying many staff.

## Clarification questions ❓

1. **Scope of "staff":** include crews and sales alongside techs in the same filter? (Yes based on your description — confirm.)
2. **Default state on login:** admin sees everyone? A tech sees only themselves? (Ties to the RBAC doc in `feature-developments/multiple roles/`.)
3. **Grouping:** do you want roles grouped in the filter (Techs / Crews / Sales) or flat alphabetical?
