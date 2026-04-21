# Gap 13 — CustomerMessages is Outbound-Only

**Severity:** 3 (medium — UX)
**Area:** Frontend (`features/customers/components/CustomerMessages.tsx`)
**Status:** Investigated, not fixed
**Related files:**
- `frontend/src/features/customers/components/CustomerMessages.tsx:1-98` — tab component
- `frontend/src/features/customers/hooks/useCustomerSentMessages.ts` — data hook
- `src/grins_platform/models/sent_message.py` — outbound
- `src/grins_platform/models/job_confirmation.py` — inbound confirmation responses
- `src/grins_platform/models/campaign_response.py` — inbound campaign replies
- `src/grins_platform/models/communication.py` — generic inbound log

---

## Summary

CustomerDetail → "Messages" tab renders `CustomerMessages.tsx`, a flat chronological list of **outbound** messages to this customer. It's hooked to `useCustomerSentMessages(customerId)` which queries `sent_messages` filtered by customer_id.

It doesn't show inbound replies. It doesn't thread conversations. There's no way to reply from the UI. There's no pagination or search.

For the admin, this tab is a useful-but-incomplete outbound log. To see what a customer said back — Y, R, C, free text, opt-out, or anything else — they'd need to cross-reference four separate tables (`job_confirmation_response`, `reschedule_request`, `campaign_responses`, `communications`) from four separate UIs, none of which show a single customer's full SMS history.

---

## Current behavior

`CustomerMessages.tsx:1-98`:

- Hook: `useCustomerSentMessages(customerId)` — returns array of `SentMessage` rows.
- Render: chronological (newest first), each row shows:
  - Channel icon (sms/email/phone)
  - Status badge (sent/delivered/failed/pending)
  - Timestamp (sent_at or created_at)
  - Message body (whitespace-preserved)
  - Recipient (phone or email)
- No pagination — all messages.
- No threading — flat list.
- No filtering or search — everything.
- No compose / reply UI.

Read-only.

---

## What admins actually need

When an admin opens a customer's Messages tab, the usual questions are:

- *"What did we tell this customer recently?"* — partially answered today.
- *"What did this customer say back?"* — not answerable at all.
- *"Did they confirm their appointment?"* — have to navigate to calendar, find appointment, open detail modal (which is also blind per Gap 11), or check the no-reply queue.
- *"Have they complained or asked to reschedule?"* — have to check reschedule queue.
- *"Did they opt out?"* — check the consent preferences section on the same page (different section), or nothing shows up at all if informal.

Each question requires different navigation. The Messages tab could be the answer to all of them.

---

## Proposed redesign — conversation view

Replace the outbound-only list with a threaded conversation view. Every SMS sent or received for this customer, in chronological order, visually paired like a chat app:

```
── Apr 12, 10:00 AM ─────────────────────────
📤 "Grins Irrigation: Your appointment on Apr 15 at 2 PM has
    been scheduled. Reply Y to confirm, R to reschedule, or C to cancel."
                                          (appointment confirmation)

── Apr 12, 10:08 AM ─────────────────────────
                                          📥 "Y"
                                          (parsed: confirm — appointment moved to CONFIRMED)

📤 "Thanks! You're all set for Apr 15 at 2 PM. See you then!"
    (auto-reply, confirmation acknowledgment)

── Apr 14, 8:00 AM ──────────────────────────
📤 "Reminder: your appointment is tomorrow at 2 PM. Please reply Y
    if still good."
                                          (day-2 reminder)

── Apr 14, 8:12 AM ──────────────────────────
                                          📥 "actually can we move to Thursday?"
                                          (parsed: unrecognized → needs_review,
                                           or attached to new RescheduleRequest)
```

Each message row has:
- Direction (📤 / 📥).
- Timestamp.
- Message body.
- Metadata (outbound message type, inbound parsed keyword, linked appointment ID, linked RescheduleRequest ID).
- Status for outbound (sent / delivered / failed).
- Click-through to the linked appointment.

---

## Data sources to merge

The view needs to union four data sources:

1. **`sent_messages`** filtered by customer_id → outbound.
2. **`job_confirmation_response`** filtered by customer_id (via appointment → job → customer, or a direct customer_id column if added) → inbound confirmation replies.
3. **`campaign_responses`** filtered by customer_id → inbound campaign replies.
4. **`communications`** filtered by customer_id → generic inbound/outbound log.

Sort by timestamp, merge into a typed event list. Backend endpoint: `GET /api/v1/customers/{id}/conversation` returning:

```json
{
  "items": [
    {
      "id": "...",
      "timestamp": "2026-04-12T10:00:00Z",
      "direction": "outbound",
      "channel": "sms",
      "body": "...",
      "message_type": "appointment_confirmation",
      "appointment_id": "...",
      "status": "delivered"
    },
    {
      "id": "...",
      "timestamp": "2026-04-12T10:08:00Z",
      "direction": "inbound",
      "channel": "sms",
      "body": "Y",
      "parsed_keyword": "confirm",
      "appointment_id": "...",
      "response_id": "..."
    },
    ...
  ],
  "pagination": {...}
}
```

---

## Reply-from-UI capability

Once inbound is visible, the natural next step is: let admin reply directly.

- Compose box at the bottom of the conversation.
- Optional template picker (reminder, reschedule-followup, etc.).
- Respects consent (disabled if opted out — see Gap 06).
- Respects time window (defer if outside 8 AM – 9 PM CT).

This is a significant scope expansion. Might be a Phase 2.

---

## Search / filter

Flat chronological gets unwieldy for long-term customers. Add:

- Filter by channel (SMS only / email only / all).
- Filter by appointment (all messages linked to a specific appointment).
- Free-text search across bodies.
- Date range picker.

Pagination: infinite-scroll or "load more" to avoid loading hundreds of rows.

---

## Edge cases

- **Cross-appointment customer** — a customer with 20 appointments over 3 years has a long conversation. Lazy-load from newest.
- **Missing linkage** — an orphan inbound (can't be correlated to an appointment) still belongs in this view by `from_phone == customer.phone`. The linkage is customer-level, not appointment-level.
- **Phone-number changes** — if a customer updates their phone, historical messages on the old number should still appear (via customer_id linkage in sent_messages; inbound may be harder if old phone has been reused). Use customer_id where available; fall back to phone_number match cautiously.
- **Multiple customers sharing a household phone** — if two CustomerDetail records both point to `555-123-4567`, whose conversation is it? Should display per customer based on the explicit customer_id linkage, and flag ambiguity.

---

## Cross-references

- **Gap 11 (AppointmentDetail timeline)** — per-appointment version of the same data.
- **Gap 16 (unified inbox)** — cross-customer view of inbound pile.
- **Gap 06 (opt-out visibility)** — the conversation header should show the consent state.
- **Gap 05 (audit coverage)** — structured inbound data is a prerequisite for rendering replies as first-class events.
