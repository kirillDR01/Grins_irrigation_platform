# Gap 03 — Thread Correlation Bugs

**Severity:** 2 (high)
**Area:** Backend (SMS dispatch + inbound correlation)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/job_confirmation_service.py:614-638` — `find_confirmation_message`
- `src/grins_platform/services/appointment_service.py:1545-1599` — `_send_reschedule_sms`
- `src/grins_platform/services/appointment_service.py:1601-1644` — `_send_cancellation_sms`
- `src/grins_platform/services/sms_service.py` — `send_message`, thread_id assignment
- `src/grins_platform/models/sent_message.py:21-158` — `SentMessage` model, `provider_thread_id` column
- `src/grins_platform/models/enums.py` — `MessageType` values

---

## Summary

The system correlates inbound Y/R/C replies to their original outbound SMS via `provider_thread_id` on `sent_messages`. That correlation has two latent bugs:

- **3.A:** Outbound SMSes of type `APPOINTMENT_RESCHEDULE` and `APPOINTMENT_CANCELLATION` do not carry a `provider_thread_id`. Replies to them cannot be correlated → fall through to orphan/needs-review.
- **3.B:** Old confirmation SMSes remain matchable after the appointment has been rescheduled. A stale reply ("Y" sent to last week's thread) routes to the old appointment's sent_message and triggers handler logic against a state that has moved on.

These are independent but combine to produce surprising routing when a customer is inattentive about *which* SMS they reply to.

---

## 3.A — Reschedule & Cancellation notification SMSes lack `provider_thread_id`

### Reproduction

1. Admin drags appointment X from Monday to Wednesday on the calendar.
2. `AppointmentService.update_appointment` → `_send_reschedule_sms` runs (`appointment_service.py:1545-1599`).
3. Customer receives: *"Your appointment has been rescheduled to [Wed date]. Reply Y to confirm, R to reschedule, or C to cancel."*
4. `message_type` on the outbound `sent_messages` row is `APPOINTMENT_RESCHEDULE`.
5. Customer replies "Y".
6. Inbound webhook hits `sms_service.handle_inbound`. The dispatch chain tries `_try_confirmation_reply`, which calls `find_confirmation_message(thread_id)`:

```python
stmt = (
    select(SentMessage)
    .where(
        SentMessage.provider_thread_id == thread_id,
        SentMessage.message_type == MessageType.APPOINTMENT_CONFIRMATION.value,
    )
    .order_by(SentMessage.created_at.desc())
    .limit(1)
)
```

Two filters. Both fail:
- `provider_thread_id` — the reschedule SMS didn't set one (the `send_message` call path in `sms_service.py` only captures the thread_id into `SentMessage` for message types that are explicitly handled; `APPOINTMENT_RESCHEDULE` isn't in that set — verify with `grep provider_thread_id src/grins_platform/services/sms_service.py`).
- `message_type` — hard-coded to `APPOINTMENT_CONFIRMATION`. Even if thread_id were set, the query wouldn't match.

7. `_try_confirmation_reply` returns no match → falls through to the generic fallback (`communications` table insert or `campaign_responses(status='orphan')`).
8. **The customer's Y is lost for confirmation purposes.** The appointment stays in SCHEDULED state. No auto-reply. No CONFIRMED status. The Y is buried in the orphan pile.

### Why it fails

Two separate bugs composing:

1. The outbound dispatch path for `APPOINTMENT_RESCHEDULE` and `APPOINTMENT_CANCELLATION` does not persist the provider's thread identifier on the `sent_messages` row. (The provider API returns a conversation/thread id on send; it's just not captured for those message types.)

2. `find_confirmation_message` hard-filters `message_type == APPOINTMENT_CONFIRMATION`. That was safe when confirmations were the only outbound that expected a reply. Now that reschedule and cancellation notifications *also* solicit Y/R/C, the filter is too narrow.

### Downstream impact

- **Customer re-confirmation lost.** The instructions doc (`update2_instructions.md:1071`) mandates: *"Reschedule notification sent when a SCHEDULED, CONFIRMED, or (reactivated) CANCELLED appointment's date/time changes. ... The customer re-confirms with Y/R/C."* — the re-confirmation actually goes nowhere.
- **Appointment stays SCHEDULED forever** unless the admin notices and manually updates. Calendar visual stays dashed (unconfirmed) even though the customer did confirm.
- **Cancellation flip-flop case lost:** if admin cancels, customer replies R within minutes ("wait, no, I still want it"), that reschedule request can't be correlated. Customer thinks they un-cancelled; system disagrees.

### Proposed fix

1. **Set `provider_thread_id` on all outbound SMSes that solicit a reply.** In the `send_message` path, unconditionally capture `provider_thread_id` from the provider response for every outbound with `message_type IN (APPOINTMENT_CONFIRMATION, APPOINTMENT_RESCHEDULE, APPOINTMENT_CANCELLATION, APPOINTMENT_REMINDER)`.

2. **Widen `find_confirmation_message` filter:**
   ```python
   CONFIRMATION_LIKE = {
       MessageType.APPOINTMENT_CONFIRMATION.value,
       MessageType.APPOINTMENT_RESCHEDULE.value,
       MessageType.APPOINTMENT_REMINDER.value,
   }
   ```
   Exclude `APPOINTMENT_CANCELLATION` — a reply to a cancellation SMS should route to a separate "reconsideration" handler, because a Y on a cancellation notice means something specific ("actually yes put me back on") that needs different handling.

3. **Consider a new handler path for post-cancellation replies** — `_handle_post_cancellation_reply` that recognizes R or Y on a cancelled appointment and either opens a new RescheduleRequest (for R) or creates an Alert for admin review (for Y → "customer wants to un-cancel").

### Edge cases

- Reschedule SMS's thread_id is the *same* as the original confirmation's in some providers (both replies are on the same phone conversation). In that case, thread-id lookup needs to pick the most recent one (already implemented — `ORDER BY created_at DESC LIMIT 1`).
- If admin reschedules twice in an hour, two reschedule SMSes exist with different thread_ids. The "most recent" tie-break should point to the latest — which it does.

---

## 3.B — Stale confirmation threads remain matchable

### Reproduction

1. Monday: appointment A is at status CONFIRMED. Original confirmation SMS sent_messages row has `provider_thread_id='abc123'`.
2. Tuesday: admin reschedules via drag-drop. `update_appointment` resets status to SCHEDULED, sends reschedule notification SMS (which per 3.A doesn't get a thread_id set, bug #1 in isolation). **The original row with `thread_id='abc123'` is untouched** — there is no `superseded_at`, no `archived_at`, no `is_active` flag on SentMessage.
3. Wednesday: customer (ignoring the reschedule SMS) replies Y to the original Monday thread ('abc123').
4. `find_confirmation_message('abc123')` returns the original row → routes to the same `appointment_id`.
5. `_handle_confirm` checks `appt.status == SCHEDULED`. Status *is* SCHEDULED (because admin's reschedule reset it). Transition to CONFIRMED proceeds.
6. **Customer just confirmed the new date without knowing it.** They thought they were confirming the original Monday slot that no longer exists.

Alternatively:
- If the admin also sent a new confirmation SMS after the reschedule (thread_id 'def456'), now both threads are matchable. A Y to 'abc123' and a Y to 'def456' both land on the same appointment. The second Y is a no-op under current `_handle_confirm` (Gap 02), but the customer's confusion is real.

### Why it fails

`find_confirmation_message` has no concept of "this thread is no longer authoritative." The `ORDER BY created_at DESC LIMIT 1` plus filter on `message_type='appointment_confirmation'` picks the newest confirmation SMS *for the thread_id*, not the newest *for the appointment*. Two different problems:

- Two confirmations sent for the same appointment at different thread_ids → each thread_id lookup returns itself, no cross-referencing.
- A single confirmation sent, appointment rescheduled, old thread still matches → replies route to an appointment whose date doesn't match what the customer saw.

### Downstream impact

- **Silent state drift:** customer thinks they confirmed X, system records Y.
- **Hard to debug:** logs show "confirmed successfully" because from the system's perspective nothing is wrong.
- **Audit trail is misleading:** `JobConfirmationResponse.raw_reply_body='Y'` on a new date the customer never actually saw.

### Proposed fix

Introduce a concept of "active thread" for an appointment:

1. **Add `superseded_at TIMESTAMPTZ NULL` to `sent_messages`.** When a new confirmation-like SMS is sent for the same `appointment_id`, update all prior `sent_messages(appointment_id=X, message_type IN confirmation-like) SET superseded_at = NOW()` except the newest.

2. **Update `find_confirmation_message` to filter out superseded rows:**
   ```python
   .where(
       SentMessage.provider_thread_id == thread_id,
       SentMessage.message_type.in_(CONFIRMATION_LIKE),
       SentMessage.superseded_at.is_(None),
   )
   ```

3. **Fallback handling for stale thread hits:** if the lookup finds a superseded row, don't ignore — create a `JobConfirmationResponse(status='stale_thread_reply')` and send a courteous auto-reply: *"Your appointment was updated. Please reply to the most recent message from us, or call [business_phone]."* This both captures the customer's intent and tells them what to do.

### Alternative — appointment-scoped lookup

Instead of thread_id lookup, do this:
- Inbound SMS has `from_phone` and `thread_id`.
- Lookup the most recent CONFIRMATION-like outbound for that `from_phone` where the appointment status is in an "awaiting reply" set (SCHEDULED, CANCELLED-but-reactivatable).
- This is more forgiving to stale thread IDs and more intuitive, but harder if one customer has multiple active appointments.

Both approaches have tradeoffs; the `superseded_at` flag is the simpler start.

### Edge cases

- Admin sends multiple confirmation SMSes by accident (double-click on "Send Confirmation"). First wins, later get superseded. Customer replies to whichever they see. Handling: accept the newest thread (current behavior), but also mark all earlier threads superseded at send time so their thread IDs don't accidentally win a future tie.
- Customer replies to an old-old thread (4+ weeks out, across multiple reschedules). They'll hit the `stale_thread_reply` handler. Still better than silently mapping to a date the customer didn't see.

---

## Cross-references

- **Gap 01** — free-text alternatives attachment is downstream of correct thread correlation.
- **Gap 02** — repeat-Y handling gets safer once stale threads can't double-confirm.
- **Gap 16 (unified inbox)** — if inbound replies are hard to correlate, they end up in the orphan pile, which has no UI (see gap 16).
- **Gap 14** (dashboard alerts) — stale-thread replies deserve an alert type so admin can investigate patterns.
