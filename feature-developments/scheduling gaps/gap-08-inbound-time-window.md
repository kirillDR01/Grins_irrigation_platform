# Gap 08 — Inbound Reply Processing Outside Business Hours

**Severity:** 4 (low)
**Area:** Backend (inbound dispatch + auto-reply policy)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/sms_service.py:58-59, 1041-1090` — outbound time window (`enforce_time_window`)
- `src/grins_platform/services/sms_service.py:~587-887` — `handle_inbound` (no time window logic)
- `src/grins_platform/services/job_confirmation_service.py` — auto-reply dispatch

---

## Summary

Outbound SMS respects a **Central Time 8 AM – 9 PM** quiet-hours window. Messages sent outside this window are deferred until the next 8 AM CT (`enforce_time_window` returns a `scheduled_for` datetime rather than `None`).

**Inbound processing has no equivalent.** An inbound Y/R/C at 2 AM triggers:
- Immediate DB writes (`JobConfirmationResponse`, state transition, `RescheduleRequest`).
- Immediate outbound auto-reply SMS ("Thanks, you're confirmed!" or "We've received your reschedule request...").

Since the auto-reply *is* an outbound SMS, it *does* hit `enforce_time_window`, so the auto-reply itself is deferred until 8 AM. But other side effects (Alert creation, state transition, audit events) happen in real time.

---

## Why this is minor (and why it's still worth noting)

### It's minor because:
- The outbound time window already covers the customer-facing SMS side. The customer won't get a 2 AM text back — the auto-reply queues.
- State transitions happening at 2 AM (customer's Y processed, appointment moves to CONFIRMED) are invisible to the customer and correct.
- Most admin alerts can wait until morning.

### It's worth noting because:
- **Noisy events for on-call.** If an Alert is created at 3 AM (e.g., customer cancellation), any PagerDuty/paging hooked to alerts wakes someone up. The alert is real, but the *response* can wait until morning — there's nothing to do at 3 AM.
- **Admin sees a stale picture.** An admin opening the dashboard at 8:30 AM sees Alerts created overnight with odd timestamps — possibly confusing without context ("why did this cancellation at 3 AM not page me?").
- **Late-night opt-outs.** An informal opt-out at midnight creates an Alert. If the triage UI (Gap 06) existed, it would queue correctly. But sending even a one-time "you're unsubscribed" confirmation SMS at midnight is awkward — the outbound window delays it, so this is already handled correctly.
- **Inbound processing could respect "do not wake me" policy.** For low-priority inbound (orphan messages, unrecognized replies), defer audit/alert generation until morning so ops isn't drowning in off-hours noise.

---

## Current behavior (file:line)

`sms_service.py:1041-1090`:

```python
def enforce_time_window(
    self,
    phone: str,
    message: str,
    message_type: str = "automated",
) -> datetime | None:
    if message_type == "manual":
        return None
    now_ct = datetime.now(CT_TZ)
    window_start = time(8, 0)
    window_end = time(21, 0)
    if window_start <= now_ct.time() < window_end:
        return None
    # Outside window → schedule for next 8:00 AM CT
    if now_ct.time() >= window_end:
        next_day = now_ct.date() + timedelta(days=1)
    else:
        next_day = now_ct.date()
    return datetime.combine(next_day, window_start, tzinfo=CT_TZ)
```

This is invoked on the *outbound* send path. Nothing equivalent on the inbound path.

Inbound `handle_inbound` flow (approx):
1. Webhook receives.
2. Parse → route to keyword-specific handler.
3. Handler performs DB state changes, enqueues auto-reply.
4. Auto-reply enters outbound path → `enforce_time_window` defers if needed.

Steps 1-3 run in real time regardless of hour.

---

## Proposed fix (small)

This gap is low-severity; pragmatic options in order of simplicity:

1. **Do nothing; document the current behavior.** Make it explicit that inbound processes in real time and outbound auto-replies are deferred. This is defensible and possibly correct.

2. **Defer Alert creation for specific alert types.** Only `CUSTOMER_CANCELLED_APPOINTMENT` is remotely paging-worthy. For the rest, wrap Alert creation in `enforce_time_window` semantics — if now is outside business hours, set the Alert's `created_at` to now (real timestamp for audit) but also set a new `surface_at` column to the next 8 AM; dashboards filter on `surface_at <= now()`. Admins don't see off-hours alerts until morning.

3. **Defer auto-replies that are "reassurance" (not urgent).** The repeat-Y reassurance SMS proposed in Gap 02, the informal-opt-out courtesy confirmation from Gap 06 — any non-transactional reply should respect the time window.

4. **Defer RescheduleRequest follow-up SMS by default.** If a customer replies R at 10 PM, they're not going to type alternatives until morning anyway. Send the initial acknowledgment immediately (it's transactional); send the "please reply with 2-3 dates" follow-up at 8 AM. This is pragmatic and customer-friendly.

### Implementation sketch for option 2

Add to `Alert`:

```python
surface_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    index=True,
    comment="If set, alert is hidden from admin UI until this time. Used for quiet-hours deferral."
)
```

Update `AlertRepository.list_unacknowledged`:

```python
query = (
    select(Alert)
    .where(
        Alert.acknowledged_at.is_(None),
        or_(
            Alert.surface_at.is_(None),
            Alert.surface_at <= func.now(),
        ),
    )
    .order_by(Alert.created_at.desc())
    .limit(limit)
)
```

At Alert creation, compute `surface_at` based on the alert type and current time.

---

## Edge cases

- **Time zone**: the business is in CT. Customers are assumed CT. If the business expands, per-customer time zones need to be considered — `phone_number_to_timezone` lookup or a customer-level field.
- **Urgency override**: some alerts are urgent (e.g., customer cancellation on a same-day appointment where the tech is scheduled in 2 hours). These should *not* be deferred. Encode urgency in the alert creation code.
- **Holiday schedule**: CT 8 AM on a holiday isn't a real workday. Consider honoring the business-calendar concept used elsewhere.

---

## Cross-references

- **Gap 06** — the informal-opt-out confirmation SMS should respect the window.
- **Gap 10** (static no-reply escalation) — the escalation job runs nightly; it already batches by design.
- **Gap 14** (dashboard alerts) — surfacing/deferral logic lives here.
