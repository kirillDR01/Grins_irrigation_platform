# 11 — Auto-notify next customer of rough expected ETA

**Request (paraphrased):**
> While we're working on a customer, the next customer in the route should automatically get a rough expected arrival time — so if we run late, they're not in the dark. Wants automation: either a button tech taps, or something that auto-fires when tech updates the previous customer.

**Status:** ❌ NOT IMPLEMENTED (parts exist — no auto-trigger)

---

## What exists today

- Message templates include `ON_THE_WAY` and `ARRIVAL` types (`models/enums.py:726-727`).
- `NotificationService.send_arrival_notification()` (`services/notification_service.py:504`) — existing building block.
- Staff can mark appointment status `en_route` via `StaffWorkflowButtons.tsx:32-39`.

## Gaps

- No code fetches the *next* scheduled appointment for the same staff on the same day and sends it an ETA.
- No "delay detected — notify next" automation exists.

## TODOs

- [ ] **TODO-11a** On tech tapping "En route to next job" (or "Complete + next"):
  - Query next appointment for `staff_id = me`, same day, `start_at > now`.
  - Compute rough arrival = `now + default_drive_minutes + buffer` (or configurable per-job travel time).
  - Send `ON_THE_WAY` SMS to the next customer.
- [ ] **TODO-11b** Add a manual "Send ETA to next customer" button in the appointment modal for cases where the automatic trigger didn't fire or the tech wants to customize the time.
- [ ] **TODO-11c** Respect customer's `sms_consent` and quiet hours.
- [ ] **TODO-11d** Cap frequency: don't send two ETAs within X minutes even if status flips multiple times.

## Clarification questions ❓

1. **Trigger style:** you said "not sure what would be best" — recommend option (a) **manual button**: tech taps once when leaving current job, then the system auto-picks the next customer and sends. Lowest risk, no mis-fires. Confirm?
2. **ETA accuracy:** do you want us to call Google Maps for real drive time, or ship a simple `+30 min` rough estimate first and add drive-time lookup later?
3. **Message copy:** you mentioned "rough expected time." Something like: *"Hi {name} — Grins Irrigation here. We're wrapping up a prior job and expect to arrive around {time_rough}. We'll text again when en route."* — OK to start with this?
