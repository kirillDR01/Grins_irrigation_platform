# Gap 02 — Repeat Confirmation Idempotency

**Severity:** 3 (medium)
**Area:** Backend (reply handler + customer-facing SMS)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/job_confirmation_service.py:189-210` — `_handle_confirm`
- `src/grins_platform/services/job_confirmation_service.py:106-183` — `handle_confirmation` dispatch
- `src/grins_platform/models/job_confirmation.py:27-101` — `JobConfirmationResponse` model
- `src/grins_platform/services/job_confirmation_service.py:275-359` — `_handle_cancel` (for pattern reference: it DOES handle the repeat case)

---

## Summary

When a customer replies "Y" (or "yes"/"confirm") twice to the same confirmation SMS — whether because they forgot they already replied, because the provider duplicated the inbound, or because they want reassurance — the system:

- Creates a second `JobConfirmationResponse(status='confirmed')` row.
- Does **not** send an acknowledgment SMS back, because the appointment is already CONFIRMED and the state-change branch is skipped.
- Does not set any idempotency marker to prevent a third, fourth, Nth.

The customer is left in the dark — no "we got it, you're all set" reply to the second Y.

Compare to `_handle_cancel` at `job_confirmation_service.py:293-306`, which explicitly handles the repeat case:

```python
if appt and appt.status == AppointmentStatus.CANCELLED.value:
    response.status = "cancelled"
    response.processed_at = datetime.now(tz=timezone.utc)
    await self.db.flush()
    self.log_rejected("handle_cancel", reason="already_cancelled")
    return {
        "action": "cancelled",
        "auto_reply": "",   # empty → no second cancellation SMS
    }
```

`_handle_confirm` has no analogous block.

---

## Reproduction

1. Send confirmation for an appointment → customer gets "Reply Y/R/C" prompt.
2. Customer replies "Y". Appointment status: SCHEDULED → CONFIRMED. Customer receives "Thanks, you're confirmed!" auto-reply (via `MessageType.APPOINTMENT_CONFIRMATION_REPLY`).
3. 30 seconds later, the customer replies "yes" again (maybe their finger slipped, or the provider redelivered).
4. Webhook arrives, dedup misses (different `provider_message_id`), `handle_confirmation` runs.
5. `_handle_confirm` at line 199:
   ```python
   if appt and appt.status == AppointmentStatus.SCHEDULED.value:
       appt.status = AppointmentStatus.CONFIRMED.value
   ```
   The `if` fails because status is already CONFIRMED. The body is silently skipped.
6. `response.status = "confirmed"` still runs → a second `JobConfirmationResponse` row is persisted.
7. **No auto-reply SMS is sent.** The caller code only dispatches the acknowledgment if the state actually transitioned — check the SMS dispatch path in `sms_service.py` around `_try_confirmation_reply` (line ~770-879), which relies on the handler's returned `auto_reply` field.

---

## Current behavior details

- **DB state:** 2+ `JobConfirmationResponse` rows per appointment, all with `status='confirmed'` and `raw_reply_body='yes'`. No uniqueness, no dedup.
- **Customer-facing:** silence after the second Y. If the customer was uncertain whether their first Y landed, this silence reinforces the uncertainty.
- **Admin-facing:** nothing surfaces. `CustomerMessages` shows the first outbound ack only; no indication the customer sent a second Y.

---

## Why it fails

Two root causes:

1. **State-gated acknowledgment.** The "we got your confirmation" SMS is only sent on the transition edge (SCHEDULED → CONFIRMED). A no-op handler produces no reply.
2. **No idempotency key or response dedup.** Unlike `_handle_cancel`'s explicit `already_cancelled` short-circuit with a log line, `_handle_confirm` writes the response row without noting that it's a repeat.

The instructions doc (`instructions/update2_instructions.md:1070`) notes: *"A repeat 'C' from the same customer is a no-op (no second cancellation SMS)."* — this is captured as a spec requirement for C. The equivalent rule for Y is **not** articulated, and the code reflects that gap.

---

## Downstream impact

### Customer experience
- Silence after second Y → perceived unreliability. A small issue per event, but at scale (hundreds of confirmations a week) it generates occasional support calls: *"did you get my reply?"*
- Customer retries, possibly with slightly different wording ("confirm", "yes please"), and every variation either silently no-ops or falls into `_handle_needs_review` which flags it for manual admin review — polluting the queue.

### Data quality
- Duplicate `JobConfirmationResponse` rows inflate any analytic that counts "confirmations received" per appointment. Not a production issue yet, but the data is wrong.
- The `JobConfirmationResponse.sent_message_id` FK ties all duplicates to the same original SMS, which is correct — but makes it hard to distinguish "customer confirmed once" from "customer confirmed three times" without deduping in the query.

### Admin experience
- If the customer's second Y is actually mistyped (e.g., "yeah ok"), `_handle_needs_review` fires, which tries to attach to an open RescheduleRequest (there isn't one), falls through, and eventually marks the response `needs_review`. The admin then sees a mystery row: *"why is this appointment flagged needs-review when they already confirmed?"*

---

## Proposed fix

Mirror the `_handle_cancel` pattern. Add this block near the top of `_handle_confirm` after loading the appointment:

```python
if appt and appt.status == AppointmentStatus.CONFIRMED.value:
    # Repeat Y on already-confirmed appointment
    response.status = "confirmed"
    response.processed_at = datetime.now(tz=timezone.utc)
    await self.db.flush()
    self.log_rejected("handle_confirm", reason="already_confirmed")
    return {
        "action": "confirmed",
        "auto_reply": (
            "You're already confirmed for [date] at [time]. "
            "See you then! Reply R to reschedule or C to cancel."
        ),
        "dedup": True,
    }
```

Key design choices:

- **Send a brief reassurance SMS.** Unlike the repeat-C case (which suppresses), repeat-Y should *reassure* because confirmation is about trust. The message should be shorter than the first confirmation and not trigger another "state changed" noise.
- **Rate-limit the reassurance.** Check if we've already sent a `CONFIRMATION_REASSURANCE` (a new MessageType) to this customer for this appointment within the last N hours. If yes, silence it (otherwise a customer spamming "Y" could extract repeated SMS — minor cost and potential spam concern).
- **Record the repeat event.** Use `response.status = 'confirmed_repeat'` (new enum value — requires a status column widening migration if 30 chars isn't enough; after the `20260414_100900` widening it's VARCHAR(50) so we're fine) or keep `'confirmed'` and rely on the log line + counting.

---

## Edge cases to verify

1. **Customer replies "Y" → then "R" → then "Y" again.** What's the final state? With the proposed fix, the R flips to SCHEDULED + opens a RescheduleRequest, and the second Y should re-confirm. This means `_handle_confirm` needs to allow SCHEDULED → CONFIRMED even if a RescheduleRequest is open (and should probably *resolve* the open RescheduleRequest with status='cancelled_by_customer' because the customer changed their mind).
2. **Customer replies "Y" → EN_ROUTE → "Y" again.** Currently the field-work path ignores the reply entirely (status mismatch, no transition). The reassurance reply is still appropriate.
3. **Two Y webhooks arrive concurrently.** Without row-level lock, both could pass the `status == SCHEDULED` check and both try to transition. SQLAlchemy default behavior: last writer wins on the assignment. The double-response-row problem remains. Consider a `SELECT ... FOR UPDATE` or a unique constraint on `(appointment_id, reply_keyword, raw_reply_body)` — the latter is risky because legitimate retries would collide.
4. **Tests:** Y, Y → one transition, two response rows, second returns `dedup=True`, second auto-reply is the reassurance text (or empty if rate-limited).

---

## Cross-references

- **Gap 01.A** — same duplicate-row problem, on R replies. Fix pattern is parallel.
- **Gap 05** — audit asymmetry. Repeat Y isn't audited today; neither is the first Y explicitly.
- **Gap 04** — state machine enforcement. If we add `'confirmed_repeat'` or similar, we should be intentional about where state lives (Appointment vs. Response).
