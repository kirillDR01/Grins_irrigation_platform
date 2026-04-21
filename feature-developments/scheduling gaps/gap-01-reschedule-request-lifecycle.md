# Gap 01 — Reschedule Request Lifecycle

**Severity:** 1 (high)
**Area:** Backend (service layer + schema)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/job_confirmation_service.py:238-273` — `_handle_reschedule`
- `src/grins_platform/services/job_confirmation_service.py:540-608` — `_handle_needs_review` (free-text append)
- `src/grins_platform/models/job_confirmation.py:103-172` — `RescheduleRequest` model
- `src/grins_platform/services/appointment_service.py:1086-1217` — `reschedule_for_request` (admin resolves)
- `src/grins_platform/migrations/versions/20260411_100400_crm2_confirmation_flow.py:85-142` — creation migration

---

## 1.A — Duplicate RescheduleRequest rows on repeat "R"

### Summary
If the same customer replies "R" twice to the same confirmation SMS (or if the provider redelivers the inbound once the Redis dedup window rolls off), `_handle_reschedule` creates a *second* `RescheduleRequest` row with `status='open'` for the same `appointment_id`. The admin queue then shows two identical rows.

### Reproduction
1. Appointment X is at status SCHEDULED after "Send Confirmation" is clicked.
2. Customer texts "R". First `RescheduleRequest(status='open')` is created and the follow-up SMS ("send us 2-3 dates") goes out.
3. Customer texts "R" again 10 minutes later (they forgot, or the provider ducktails).
4. Second `RescheduleRequest(status='open')` is created, joined to the same appointment, with a separate `original_reply_id`.
5. `RescheduleRequestsQueue.tsx` (`frontend/src/features/schedule/components/RescheduleRequestsQueue.tsx`) lists both rows.

### Current behavior (file:line)
`_handle_reschedule` (`job_confirmation_service.py:238-273`) has **no check** for an existing open request before inserting:

```python
reschedule = RescheduleRequest(
    job_id=job_id,
    appointment_id=appointment_id,
    customer_id=customer_id,
    original_reply_id=response.id,
    raw_alternatives_text=raw_body,
    status="open",
)
self.db.add(reschedule)
```

The `RescheduleRequest` table has **no partial unique index** on `(appointment_id) WHERE status='open'`. Schema confirmed in `models/job_confirmation.py:103-172`:

```python
__table_args__ = (
    Index("idx_reschedule_requests_appointment", "appointment_id"),
    Index("idx_reschedule_requests_status", "status"),
)
```

(Only plain indexes — no uniqueness.)

### Why it fails
- No application-level check before insert.
- No database-level constraint to catch a race or re-insertion.
- Redis webhook dedup at `api/v1/callrail_webhooks.py:30-80` only covers *same* `(conversation_id, created_at)` pair for 24h — a provider retry with a different `created_at` or a customer's genuine second reply lands as a new event.

### Downstream impact
- Admin sees N identical rows in `RescheduleRequestsQueue` — has to resolve each manually; resolving one doesn't close the others.
- If admin resolves #1 by rescheduling, the appointment moves to a new date. Row #2 still points to the (now-rescheduled) appointment_id and looks actionable.
- `requested_alternatives` written by `_handle_needs_review` (the free-text follow-up path, see 1.C) attaches to the *newest* open request — so alternatives collected after R#1 could end up attached to R#2's row, splitting the data.

### Proposed fix (not implemented)
Two-layer defense:

1. **Application-level idempotency:** In `_handle_reschedule`, before inserting, check for an existing `RescheduleRequest` where `appointment_id=appointment_id AND status='open'`. If one exists, reuse it (update `raw_alternatives_text` to append, log a duplicate-R event, still mark the new `JobConfirmationResponse` with `status='reschedule_requested'`, still send the follow-up SMS only if this is the first R in the last N minutes).
2. **DB constraint:** Add a partial unique index:

   ```sql
   CREATE UNIQUE INDEX uq_reschedule_requests_open_per_appointment
     ON reschedule_requests (appointment_id)
     WHERE status = 'open';
   ```

   This is a safety net — the app logic is the primary guard.

### Edge cases to verify
- Two R replies arrive within the same Redis window but are from different `conversation_id`s (shouldn't happen, but possible if CallRail reassigns). Dedup won't catch — app check must.
- Customer sends "R" then admin resolves (status='resolved'), then customer sends another "R" days later. Should create a NEW open request, not reuse the resolved one. The unique index is partial on `status='open'`, so this works.
- Race: two inbound webhooks arrive at the same millisecond and both pass the Redis dedup. With the DB unique index, one insert wins and the other raises `IntegrityError` — the handler needs to catch and treat that insert as a dedup hit.

### Tests needed
- Unit: two calls to `_handle_reschedule` for the same appointment → only one row, second call is idempotent.
- Integration: two webhook posts with different `provider_message_id` but same appointment/customer → only one queue entry.
- Migration test: verify the partial unique index rejects a second `status='open'` row for the same appointment.

---

## 1.B — "R" accepted during EN_ROUTE or IN_PROGRESS

### Summary
`_handle_reschedule` has **no guard** against the appointment being in a field-work state. It accepts R, creates a RescheduleRequest, and sends the "we'll get back to you" follow-up SMS. But the admin cannot resolve it: `reschedule_for_request` only accepts source states `{DRAFT, SCHEDULED, CONFIRMED}` (`appointment_service.py:1135-1149`). The request is stuck open forever.

### Reproduction
1. Appointment at CONFIRMED status. Tech clicks "On My Way" → appointment becomes EN_ROUTE.
2. Customer (stuck in traffic themselves) texts "R" to the original confirmation thread.
3. `_handle_reschedule` creates `RescheduleRequest(status='open')`, follow-up SMS goes out.
4. Admin opens `RescheduleRequestsQueue`, sees the row, clicks "Reschedule".
5. Backend endpoint `/api/v1/appointments/{id}/reschedule-from-request` (`api/v1/appointments.py:1049-1105`) checks:
   ```python
   allowed_statuses = {
       AppointmentStatus.DRAFT.value,
       AppointmentStatus.SCHEDULED.value,
       AppointmentStatus.CONFIRMED.value,
   }
   ```
   EN_ROUTE is not in the set → returns `422` with `InvalidStatusTransitionError`.
6. Admin UI shows error toast; the request row stays `status='open'`.

### Current behavior
- Backend accepts R unconditionally; appointment is not touched (stays EN_ROUTE).
- Follow-up SMS tells the customer to send alternatives — confusing, because the tech is literally on the way.
- Admin queue surfaces an unresolvable ticket.

### Why it fails
The state check exists at the *admin-action* layer but not at the *customer-reply* layer. The asymmetry creates dead queue items.

### Downstream impact
- Customer experience: they ask to reschedule, the system says "we got it", they expect a callback, but the tech arrives in 15 minutes — confusion at the door.
- Admin experience: click "Reschedule", get cryptic 422. No clear signal about what to do. The only path is to resolve the request manually and call the customer.
- On-site flow is disrupted: tech may not know the customer tried to reschedule at the last minute because the R reply doesn't surface on the appointment itself (see Gap 11 — appointment-detail is inbound-blind).

### Proposed fix
Three-part response:

1. **Pre-check in `_handle_reschedule`:** Reject R when appointment status is in `{EN_ROUTE, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW}`.
2. **Branch on state:**
   - `EN_ROUTE / IN_PROGRESS`: Send a different auto-reply, e.g. "Your technician is already on the way / on site. Please call us at [business_phone] if you need to make a change." Raise an Alert (`alert_type='late_reschedule_attempt'`) so admin sees it in context.
   - `COMPLETED`: "Your appointment was completed on [date]. To book a new service, call [business_phone] or reply with details."
   - `CANCELLED / NO_SHOW`: "This appointment is no longer active. Please call [business_phone]."
3. **Still record the response:** create a `JobConfirmationResponse` with `status='reschedule_rejected'` + `needs_review_reason='late_reschedule_attempt'` so the reply is visible in audit/queue.

### Edge cases
- If the tech marked "Job Started" but forgot to mark "Job Complete", the appointment sits in IN_PROGRESS overnight. A next-morning R should still not create a request on that stale appointment — handled by the pre-check.
- If admin just manually edited the appointment to a new date (bumping it back to SCHEDULED) right before the R lands, the normal path runs. Only EN_ROUTE+ blocks.

---

## 1.C — Free-text alternatives attachment is fragile

### Summary
After R, the system sends a follow-up asking for "2-3 dates that work." The customer's next message is free text ("Tuesday after 3" or "any day next week"). `_handle_needs_review` (`job_confirmation_service.py:540-608`) is responsible for attaching that text to the correct open `RescheduleRequest.requested_alternatives`. It works — but only for the *newest* open request, and only if the new inbound correlates to the *same* original confirmation SMS thread.

### Current behavior (file:line)
`_handle_needs_review` at line 546-558 runs this query:

```python
stmt = (
    select(RescheduleRequest)
    .where(
        RescheduleRequest.appointment_id == response.appointment_id,
        RescheduleRequest.status == "open",
    )
    .order_by(RescheduleRequest.created_at.desc())
    .limit(1)
)
```

It picks one open request, then appends `{"text": raw_reply_body, "at": iso_now}` to `requested_alternatives.entries`.

### Why it's fragile

1. **`appointment_id` comes from the correlated `SentMessage` (the original confirmation).** If the customer is replying to the *follow-up* SMS (which is `reschedule_followup` message_type, not `appointment_confirmation`), `find_confirmation_message` (`job_confirmation_service.py:614-638`) filters by `message_type=APPOINTMENT_CONFIRMATION` and won't match the follow-up thread.
   - **Outcome:** inbound falls through to the orphan/fallback path, a `communications` or `campaign_responses(status='orphan')` row is created, the RescheduleRequest never gets the alternatives attached.

2. **If there are multiple open requests** (Gap 1.A), the `order_by created_at DESC` picks the newest one — which may not be the one the customer is actually responding about.

3. **The free-text message doesn't preserve structure.** `"Tues 3pm or Wed 10am"` lands as one blob in `entries`. There's no parsing into candidate datetimes, so the admin has to read prose.

### Downstream impact
- Admin queue row shows `raw_alternatives_text` (from the initial R) but may or may not show the *follow-up* alternatives depending on correlation.
- If the customer replies to the follow-up SMS several times ("Tuesday at 3", then "or Wednesday morning works too"), each message needs to append to entries, which requires stable correlation every time.

### Proposed fix
1. **Treat follow-up replies as first-class.** When sending the "please send 2-3 dates" follow-up SMS, set `provider_thread_id` on that sent_message row too. Widen `find_confirmation_message` (or add a sibling `find_reschedule_thread`) to also match `message_type IN ('appointment_confirmation', 'reschedule_followup')` for thread resolution.
2. **Add an explicit capture window.** After a RescheduleRequest is opened, capture *any* inbound from that customer's phone for the next N hours as additional alternatives on that request, even if the thread_id correlation fails (this covers customers who reply from a different SMS thread).
3. **Optional: light parsing** — try `dateparser` on the raw body; store `{text, at, parsed_candidates: [datetime...]}`. Leaves the raw text as the source of truth but helps the UI.

### Tests
- Customer sends "R", then 3 follow-up messages. All 3 land in `requested_alternatives.entries` under the same request.
- Customer sends R for appointment A, then a few days later sends R for appointment B (different thread). Alternatives attach to the correct request.

---

## Cross-references
- **Gap 02** — idempotency for Y overlaps with 1.A but targets a different reply type.
- **Gap 03** — thread correlation underpins 1.C; stale/missing thread IDs make free-text capture fail silently.
- **Gap 11** — the appointment-detail UI does not surface any of this to the admin viewing the calendar.
