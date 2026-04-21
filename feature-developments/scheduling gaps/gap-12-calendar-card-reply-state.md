# Gap 12 — Calendar Cards Lack Reply-State Badges

**Severity:** 3 (medium — UX)
**Area:** Frontend (`features/schedule/components/CalendarView.tsx`)
**Status:** Investigated, not fixed
**Related files:**
- `frontend/src/features/schedule/components/CalendarView.tsx:1-350+` — calendar rendering
- `frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx` — separate queue
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx` — separate queue

---

## Summary

Calendar appointment cards encode appointment **status** (DRAFT / SCHEDULED / CONFIRMED / EN_ROUTE / IN_PROGRESS / COMPLETED / CANCELLED) via border style and color:

- **Dotted border, grayed-out** — DRAFT.
- **Dashed border, muted color** — SCHEDULED (confirmation sent, awaiting reply).
- **Solid border, full color** — CONFIRMED and downstream states.

Cards also show:
- A **PREPAID** badge + emerald left-border for service-agreement appointments.
- An **attachments** count badge (📎 + N) if the job has uploaded files.

They do **not** encode reply-lifecycle state. An appointment can be in SCHEDULED status but have:
- An open `RescheduleRequest` from the customer's R reply (pending admin action).
- A `needs_review_reason='no_confirmation_response'` (3+ days silent).
- An opted-out customer who can't receive further SMS.
- An orphan/unrecognized inbound that's attached to this appointment but needs triage.
- An informal opt-out alert on the customer (not this appointment, but relevant).

None of this shows on the card. Admin must click in (AppointmentDetail, Gap 11 — also blind) or cross-reference a separate queue page.

---

## Reproduction — the "I opened the schedule and nothing looks wrong" problem

1. Admin at 8 AM scanning today's schedule.
2. Customer Jane Doe has an appointment at 2 PM today, status SCHEDULED (dashed, muted).
3. Jane texted "R — need to move, can we do tomorrow?" at midnight (Gap 01's normal flow).
4. Calendar card still shows dashed/muted, identical to every other SCHEDULED card.
5. Admin moves on, assumes nothing's urgent.
6. 2 PM arrives; tech heads to Jane's — who is away because she thinks she rescheduled.
7. Admin learns of the RescheduleRequest only when the tech calls frustrated.

The information *exists* in the system. The UI just doesn't surface it where the admin looks.

---

## Current visual vocabulary

From `CalendarView.tsx` (lines 120-230 approximately):

| Element | Meaning |
|---|---|
| Dotted border, gray | DRAFT appointment |
| Dashed border, muted | SCHEDULED, awaiting reply |
| Solid border, full color | CONFIRMED |
| Darker color | EN_ROUTE / IN_PROGRESS |
| Faded gray-through | COMPLETED / CANCELLED |
| 💎 emerald badge | Prepaid (service agreement) |
| 📎 blue badge + count | Has attachments |
| Red background (selected day) | Highlighted/selected |

That's the complete set of visual signals. Zero signals for reply-lifecycle anomalies.

---

## Missing badges — priority list

### Tier 1 (must-have)

**B1 — Pending reschedule request.**
- Icon: ↻ or ⏱ in amber/yellow.
- Fires when: `RescheduleRequest(appointment_id=X, status='open')` exists.
- Click: opens AppointmentDetail with the reschedule banner expanded.

**B2 — No-reply flagged.**
- Icon: ⚠ in orange.
- Fires when: `appointment.needs_review_reason == 'no_confirmation_response'`.
- Click: opens AppointmentDetail with reminder-action banner.

### Tier 2 (high value)

**B3 — Customer opted out.**
- Icon: 🚫 or small red badge.
- Fires when: customer's most recent `SmsConsentRecord.consent_given == False`.
- Tooltip shows opt-out date/method.

**B4 — Unrecognized reply pending review.**
- Icon: ❓ in purple.
- Fires when: `JobConfirmationResponse(appointment_id=X, status='needs_review')` exists AND not yet triaged.
- Click: opens AppointmentDetail with raw body visible.

### Tier 3 (optional)

**B5 — Reminder recently sent.**
- Small dot or count badge.
- Fires when: a manual "Send Reminder SMS" or auto-reminder was sent within last 24h.
- Tooltip: "Day-2 reminder sent 4h ago."

**B6 — Recent edit / move.**
- Small indicator that the appointment was drag-drop-moved recently (e.g., last 24h).
- Fires when: `updated_at` > `created_at` + 1 day, and change included a scheduled_date/time update.
- Tooltip: "Rescheduled from Apr 18 → Apr 21."

---

## Visual density concern

Adding 4-6 possible badges to every card risks visual noise. Mitigate by:

1. **Stacking right-aligned pills.** Each card has ~2-3 pill slots max. Priority: B3 (opted-out) > B1 (pending reschedule) > B2 (no-reply flagged) > B4 (unrecognized) > others. Only show top N for any given card.
2. **Color coding.** Amber/orange for action-needed; red for blocking; gray for informational. Consistent with existing error/warning conventions in the design system.
3. **Compact mobile view.** On small calendars (dense weekly view), show a single "⚠ N issues" aggregate badge that expands on hover/click.

---

## Data flow

Calendar render currently hits `GET /api/v1/appointments?start=X&end=Y`. Extend response to include reply-state hints:

```json
{
  "id": "...",
  "status": "scheduled",
  // ... existing fields ...
  "reply_state": {
    "has_pending_reschedule": true,
    "has_no_reply_flag": false,
    "customer_opted_out": false,
    "has_unrecognized_reply": false,
    "last_reminder_sent_at": "2026-04-18T14:00:00Z",
    "recently_edited": false
  }
}
```

Server-side: a single JOIN to RescheduleRequest / needs_review_reason / SmsConsentRecord, indexed, should add <20ms to the query.

Alternative: separate `/api/v1/appointments/{id}/reply-state` endpoint called per visible card. More network but more cacheable.

---

## Edge cases

- **Legacy appointments:** appointments created before the reschedule-request system existed have no rows; reply_state is all-null/false. No impact.
- **Mobile view:** limited horizontal real estate. Consider a dot-color indicator (single dot, color carries meaning) rather than full pills.
- **Accessibility:** icons alone are not accessible. Every badge needs a `title` / `aria-label` with full text.

---

## Cross-references

- **Gap 11 (AppointmentDetail inbound-blind)** — same data, different surface. The badge on the card is the "at-a-glance" view; the detail modal is the "click-through" view.
- **Gap 06 (opt-out visibility)** — the opt-out badge is mandated here too.
- **Gap 14 (dashboard alerts)** — aggregate counts roll up to dashboard ("4 appointments with pending reschedules").
