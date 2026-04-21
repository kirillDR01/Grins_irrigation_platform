# Gap 11 — AppointmentDetail is Inbound-Blind

**Severity:** 2 (high — UX)
**Area:** Frontend (`features/schedule/components/AppointmentDetail.tsx`)
**Status:** Investigated, not fixed
**Related files:**
- `frontend/src/features/schedule/components/AppointmentDetail.tsx:1-586` — modal/panel
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` — separate queue that holds reschedule state
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` — separate queue for no-reply
- `src/grins_platform/models/job_confirmation.py` — backing data `JobConfirmationResponse`, `RescheduleRequest`

---

## Summary

`AppointmentDetail.tsx` is the modal/side-panel admins open when clicking an appointment on the calendar. It shows: status badge, scheduled date/time, customer name, staff, job type, notes, and a timeline of field-work timestamps (en_route_at, started_at, completed_at).

It does **not** show:
- Customer's Y/R/C replies or their timestamps.
- Any reply history at all — neither outbound confirmations sent nor inbound responses received.
- Open `RescheduleRequest` on this appointment (even though one may exist).
- `needs_review_reason` flag indicating no-reply escalation.
- `SmsConsentRecord` / opt-out status for the customer.
- Any free-text alternatives the customer supplied after R.

For the admin, the detail modal is a field-work view. For customer-facing events (Y, R, C, no reply, opt-out, informal opt-out), they must navigate elsewhere — or blind-check the reschedule/no-reply queues on a different page — to know what's happening.

---

## Reproduction — concrete admin blind spot

Customer replies R, then follows up with "Tuesday at 3 or Wednesday morning works."

1. Admin opens the calendar, sees the appointment still visible (status SCHEDULED, dashed border).
2. Clicks the appointment → AppointmentDetail modal opens.
3. Modal shows: "Scheduled, Tuesday 10:00-12:00, customer Jane Doe" and the field-work timeline (empty, since it hasn't happened yet).
4. **No indication a RescheduleRequest is open.**
5. **No indication customer sent free-text alternatives.**
6. Admin closes modal, goes back to queue-level thinking, navigates to RescheduleRequestsQueue, finds the row there — 3 extra clicks and a mental context-switch.

For the admin to get a complete picture of an appointment, they must stitch together:
- Calendar card visual (dashed/solid/dotted)
- AppointmentDetail modal (this blind view)
- RescheduleRequestsQueue (separate page)
- NoReplyReviewQueue (separate page)
- CustomerDetail → Messages tab (outbound-only, see Gap 13)
- Direct DB queries or logs for anything else

---

## Current AppointmentDetail content (file:line)

From `AppointmentDetail.tsx`:

- Line 200-210: Status badge with color mapping for each appointment status.
- Line 353-361: Notes section (`appointment.notes` — free-text admin-entered).
- Line 364-385: Timeline: en_route_at, started_at (arrived_at), completed_at.
- Lines elsewhere: customer name/phone, staff, job type, address, scheduled date/time, action buttons (Edit, Cancel, Send Confirmation if DRAFT).

No reference to `JobConfirmationResponse`, `RescheduleRequest`, `sms_consent`, or `alerts` API endpoints.

---

## Missing elements — detailed list

### M1 — Confirmation reply history

- Customer's Y/R/C reply timestamp, raw body, parsed keyword.
- Any auto-reply SMS we sent back.
- If multiple Y replies (Gap 02 scenario), all of them.

### M2 — Pending RescheduleRequest indicator

If `RescheduleRequest(appointment_id=X, status='open')` exists:
- Badge or banner at the top of the modal: *"Customer requested reschedule — [time since]"*.
- Inline display of `raw_alternatives_text` and any `requested_alternatives.entries` captured from follow-up.
- Quick-action button: "Reschedule to Alternative" that opens the reschedule form pre-filled.

### M3 — No-reply flag

If `appointment.needs_review_reason == 'no_confirmation_response'`:
- Banner at top: *"No reply received after [N days]. [Send reminder] [Call customer] [Mark contacted]"*.
- Same actions as `NoReplyReviewQueue` but in context.

### M4 — Opt-out indicator

If the customer's phone has `SmsConsentRecord(consent_given=False)`:
- Red badge: *"Customer opted out of SMS on [date] via [method]"*.
- Send-SMS action buttons disabled (Gap 06).

### M5 — Outbound SMS log

List of `SentMessage` rows for this appointment:
- Timestamp, recipient, message content, delivery status.
- Icon for message type (confirmation, reminder, reschedule notice, cancellation).

### M6 — Inbound correlated to appointment

All `JobConfirmationResponse` rows for this appointment, plus any inbound `communications` rows that correlated via thread_id:
- Raw body, received_at, parsed keyword.
- Link to the corresponding `SentMessage` (the outbound they were replying to).

### M7 — Audit timeline (once Gap 05 is closed)

Unified event stream:
- Outbound sent
- Inbound received (Y/R/C/free-text/opt-out)
- Status transition (with actor)
- Admin edit
- Reminder sent

Sorted chronologically, one line each, click-to-expand for details.

---

## Proposed UI structure

Add a new "Communication" section to `AppointmentDetail.tsx` between the status/metadata block and the Notes section. Collapsed by default; expands to show:

```
[Communication ▼] — Last reply 2 days ago

  📤 Confirmation sent              Apr 14, 10:00 AM
  📥 Customer replied "Y"           Apr 14, 10:05 AM → Confirmed
  📤 Reminder sent (day 2)          Apr 16, 8:00 AM
  📥 Customer replied "R" + "Tuesday at 3 or Wed morning"
                                    Apr 16, 2:17 PM → RescheduleRequest opened

  [⚠ Open reschedule request]      [Resolve & reschedule]

  📛 Customer opted out via STOP on Mar 15 (transactional-only allowed)
```

Driven by a new `GET /api/v1/appointments/{id}/timeline` endpoint (proposed in Gap 05) that returns all event types in one response, sorted.

---

## Existing API gaps to fill

`AppointmentDetail` currently hits `GET /api/v1/appointments/{id}` only. To populate the new section it would need:

1. `GET /appointments/{id}/confirmation-responses` — all JobConfirmationResponse rows.
2. `GET /appointments/{id}/reschedule-requests` — filtered by appointment_id.
3. `GET /appointments/{id}/sent-messages` — outbound SMS history.
4. `GET /customers/{id}/consent` — current consent state + history.

Or consolidate all of these into a single `GET /appointments/{id}/timeline` endpoint for bandwidth efficiency.

---

## Edge cases

- **Rescheduled appointment:** `AppointmentDetail` for appointment B should still show the *original* reschedule request that caused B to exist (link via `rescheduled_from_id`). Gives history context.
- **Very long history:** 6 reminders, 4 no-replies, 2 reschedule requests — the timeline gets long. Consider a "show all" / "show last 10" pagination.
- **Customer with opt-out that's pending admin action (informal opt-out, Gap 06):** show the Alert ID and the raw informal-opt-out body inline.

---

## Cross-references

- **Gap 05** — the `/timeline` endpoint depends on having comprehensive audit coverage.
- **Gap 06** — opt-out badge is rendered here too.
- **Gap 12** — calendar card hints and AppointmentDetail banner are two surfaces of the same state.
- **Gap 13** — CustomerMessages tab has adjacent but broader data (all customer SMS, not just this appointment's).
- **Gap 16** — unified inbox intersects with this timeline concept.
