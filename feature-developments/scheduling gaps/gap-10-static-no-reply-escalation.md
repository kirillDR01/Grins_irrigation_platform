# Gap 10 — Static No-Reply Escalation

**Severity:** 3 (medium)
**Area:** Backend (nightly job) + UI (review queue)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/background_jobs.py:793-962` — `flag_no_reply_confirmations`
- `src/grins_platform/models/appointment.py:176-183` — `needs_review_reason` column
- `frontend/src/features/schedule/components/NoReplyReviewQueue.tsx:1-336`

---

## Summary

The no-reply escalation flow has exactly one automated step: a nightly cron (`flag_no_reply_confirmations`) that sets `needs_review_reason='no_confirmation_response'` on appointments that have been SCHEDULED for N days (default 3; configurable via `BusinessSetting`) without a Y/R/C reply. Appointments so flagged appear in `NoReplyReviewQueue`. Every subsequent action — sending a second reminder, calling the customer, deciding to cancel — is manual.

This is **a queue, not an escalation.** There's:
- No automatic second reminder SMS.
- No tiered reminder schedule (e.g., 1 day before → 2 days before → morning of).
- No auto-cancel or auto-no-show-flag for appointments the customer never acknowledges by the day of.
- No per-customer tailoring (loyal customers vs. new; high-value vs. routine).

For a business that sends dozens of confirmations a day, the manual-everything design scales poorly. Either the queue gets neglected (no-reply customers no-show without intervention) or the admin spends hours per week triaging.

---

## Current behavior

`flag_no_reply_confirmations` (nightly):

```python
# Pseudocode — actual code in background_jobs.py:793-962
threshold_days = business_setting("no_confirmation_days", default=3)
cutoff = now() - timedelta(days=threshold_days)
q = select(Appointment).where(
    Appointment.status == SCHEDULED,
    Appointment.confirmation_sent_at < cutoff,
    Appointment.needs_review_reason.is_(None),
)
for appt in q:
    appt.needs_review_reason = "no_confirmation_response"
    create_alert(type="CONFIRMATION_NO_REPLY", entity=appt)
```

UI: `NoReplyReviewQueue` lists flagged appointments. Actions per row:
- **Call Customer** — opens `tel:` URI.
- **Send Reminder SMS** — re-fires the Y/R/C prompt (reuses original confirmation template).
- **Mark Contacted** — clears `needs_review_reason`.

Only the first reminder is automated (the initial `send_confirmation` click). Second reminders are manual-only.

---

## Why this creates operational load

### At scale

- At 50 confirmations/day and a 20% no-reply-in-3-days rate, 10 appointments/day land in the queue.
- Assuming a 3-day appointment window, the queue carries ~30 rows at any time.
- Admin must triage daily or appointments go into the calendar un-confirmed, increasing no-show risk.

### Missing escalation stages

A production-ready escalation ladder might be:

1. **Initial confirmation** — 0-day send (already exists).
2. **Day-2 auto-reminder** — same Y/R/C, different wording ("Reminder: your appointment on [date] — please confirm").
3. **Day-before call** — automated voice or SMS: "Tomorrow at 2 PM, please reply Y to confirm or we may need to release this slot."
4. **Morning-of** — "Technician departs at [time]. Please reply Y to confirm."
5. **T-minus-2-hours** — if still no reply, auto-mark as TENTATIVE (new substatus) or trigger an Alert to admin for manual call.

Currently, **none of stages 2-5 is automated.** Admin can manually hit "Send Reminder SMS" at any time, but there's no scheduled cadence.

---

## Downstream impact

### No-show rate
- Unconfirmed appointments have materially higher no-show rates. Without escalation, more of them slip through.
- No-show = lost revenue (window of tech time with no job), customer dissatisfaction (tech arrived when customer wasn't ready), and scheduling chaos (other jobs bumped to fit the gap).

### Data quality
- `needs_review_reason` is a single-value field. Once set, it's set. If the appointment then receives a reply, the field is cleared (see `_handle_confirm` → it doesn't clear, actually — verify). Stale `needs_review_reason` values may pollute the queue.
- No history of "this customer was texted twice, then called twice, and still didn't respond" — impossible to mine for patterns (problem customers vs. problem reminder timing).

### Admin time
- Manual triage at scale ~= 1 hour/day per 50 daily confirmations. Time that could be spent on higher-value work.

---

## Proposed fix

### Phase 1 — automated second reminder (quick win)

Extend the nightly job or add a new hourly job:

```python
# Automated Day-2 reminder
def send_day_2_reminders():
    cutoff_min = now() - timedelta(days=2)
    cutoff_max = now() - timedelta(days=1, hours=20)  # 2-day window, avoid re-sending
    appointments = query_scheduled_no_reply(between=(cutoff_min, cutoff_max))
    for appt in appointments:
        if not already_sent_reminder(appt.id):
            send_reminder_sms(appt, template='day_2_gentle_reminder')
            log_reminder_sent(appt.id, stage='day_2')
```

Requires:
- A `sms_reminders_sent` log table or a structured field on `Appointment` listing reminder timestamps.
- A new `MessageType.APPOINTMENT_REMINDER_DAY_2` (the current `APPOINTMENT_REMINDER` can be reused or split).
- Business setting to enable/disable per-day reminders.

### Phase 2 — escalation config UI

Let admin configure:
- Days/hours between reminders.
- Template per stage (first reminder, second reminder, day-before, morning-of).
- Cutoff for auto-release (e.g., "if no reply by 24 hours before, mark as TENTATIVE").

Admin Settings page: `/settings/confirmation-escalation`.

### Phase 3 — per-customer tailoring

- New customers get more reminders (they're unfamiliar with the flow).
- Repeat customers with a strong "always confirms" history can skip intermediate reminders.
- Opted-out customers are excluded entirely from the escalation ladder.

---

## Edge cases

- **Customer confirms after the Day-2 reminder is queued but before it sends.** The queue should recheck before each send — if status is now CONFIRMED, skip.
- **Time window respect.** All reminders must respect CT 8 AM – 9 PM.
- **Opt-out mid-escalation.** If the customer replies STOP after the first reminder, all subsequent reminders must be canceled.
- **Appointment cancelled/rescheduled between reminders.** Cancel the pending reminder job.

---

## Alerts and dashboard integration

When escalation reaches stage 3+ (day-before call), create an Alert. Dashboard shows: *"5 customers not responding — final call needed today."* This is a different surface from the passive queue (see Gap 14).

---

## Cross-references

- **Gap 02** — repeat-Y handling must coexist with multi-stage reminders (customer replies Y to reminder 2 after ignoring reminder 1).
- **Gap 05** — each reminder should generate an audit log entry.
- **Gap 08** — reminder SMSes must respect the time window already enforced for outbound.
- **Gap 14** — escalation events deserve dashboard alert types.
