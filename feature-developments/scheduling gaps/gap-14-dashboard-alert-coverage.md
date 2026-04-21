# Gap 14 — Dashboard Alert Coverage

**Severity:** 3 (medium — UX)
**Area:** Frontend (dashboard) + Backend (Alert model + creation sites)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/models/alert.py:28-121` — `Alert` model
- `src/grins_platform/models/enums.py` — `AlertType` enum (only 2 values)
- `src/grins_platform/api/v1/alerts.py:38-88` — `GET /api/v1/alerts`
- `frontend/src/features/dashboard/components/AlertCard.tsx:1-125` — generic card component

---

## Summary

The Alert infrastructure exists — model, enum, repository, list endpoint, and a reusable `AlertCard` dashboard component. It's used sparingly:

- Only **2 alert types** are defined: `CUSTOMER_CANCELLED_APPOINTMENT`, `CONFIRMATION_NO_REPLY`.
- The dashboard surfaces alerts per-type via dedicated `AlertCard` instances; no generic "all unacknowledged alerts" widget.
- Many events that *should* be alert-worthy are logged to other places (`communications`, `campaign_responses`, `JobConfirmationResponse` with status='needs_review') without creating an Alert.

Consequence: admins rely on manual queue-checking (NoReplyReviewQueue, RescheduleRequestsQueue, informal-opt-out review which doesn't exist yet per Gap 06) instead of being pulled to things on the dashboard. The dashboard *could* be the single pane of glass for "things that need attention this morning."

---

## Current state

### Alert types defined

`enums.py`:

```python
class AlertType(str, Enum):
    CUSTOMER_CANCELLED_APPOINTMENT = "customer_cancelled_appointment"  # H-5
    CONFIRMATION_NO_REPLY = "confirmation_no_reply"                    # H-7
```

Only two. Both created by specific code paths:
- `CUSTOMER_CANCELLED_APPOINTMENT` — created by `_handle_cancel` in `JobConfirmationService`.
- `CONFIRMATION_NO_REPLY` — created by the nightly `flag_no_reply_confirmations` job.

### Alert list endpoint

`api/v1/alerts.py:38-88`:

```python
@router.get("", response_model=AlertListResponse)
async def list_alerts(
    _current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    acknowledged: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
) -> AlertListResponse:
    repo = AlertRepository(session=session)
    if acknowledged:
        alerts = []  # NOT IMPLEMENTED
        total = 0
    else:
        rows = await repo.list_unacknowledged(limit=limit)
        alerts = [AlertResponse.model_validate(row) for row in rows]
        total = len(alerts)
    return AlertListResponse(items=alerts, total=total)
```

- No filter by type or severity (query params missing).
- Acknowledged-alerts path is a stub (`alerts = []`).
- Single "return all unacked" mode.

### Dashboard rendering

`AlertCard.tsx` is generic — takes props `title`, `description`, `count`, `variant`, `targetPath`. Used for:
- Leads Awaiting Contact
- Overdue Invoices
- Lien Deadlines
- etc. (not all of these are Alert-backed — some are derived from other metrics)

There's **no** AlertCard instance for:
- `CUSTOMER_CANCELLED_APPOINTMENT` — which means the Alert is created in the DB but never seen on the dashboard.
- `CONFIRMATION_NO_REPLY` — same.

Admins may see the effects in the NoReplyReviewQueue, but not a dashboard summary.

---

## Missing alert types

### AT-1 — `PENDING_RESCHEDULE_REQUEST`

**Trigger:** On `RescheduleRequest(status='open')` creation.
**Severity:** WARNING.
**Dashboard widget:** "N reschedule requests awaiting action."
**Target:** `/schedule` → RescheduleRequestsQueue.

### AT-2 — `INFORMAL_OPT_OUT`

**Trigger:** `_flag_informal_opt_out` in sms_service.
**Severity:** WARNING.
**Dashboard widget:** "N customers may have requested opt-out — review."
**Target:** New `/alerts/informal-opt-out` queue (Gap 06).

### AT-3 — `UNRECOGNIZED_CONFIRMATION_REPLY`

**Trigger:** `_handle_needs_review` when no open RescheduleRequest exists to attach to.
**Severity:** INFO (unless repeated for same appointment, then WARNING).
**Dashboard widget:** "N unrecognized replies."
**Target:** A new `/alerts/unrecognized-replies` triage page.

### AT-4 — `LATE_RESCHEDULE_ATTEMPT`

**Trigger:** Customer replies R when appointment is EN_ROUTE/IN_PROGRESS (Gap 01.B fix).
**Severity:** ERROR.
**Dashboard widget:** "Last-minute reschedule attempt — call customer now."
**Target:** AppointmentDetail for the specific appointment.

### AT-5 — `ORPHAN_INBOUND`

**Trigger:** Inbound SMS that correlates to no outbound (wrong thread, random text from a number we've messaged before).
**Severity:** INFO.
**Dashboard widget:** "N orphan messages — review."
**Target:** A new `/alerts/orphans` triage page.

### AT-6 — `MMS_RECEIVED`

**Trigger:** Inbound with media_urls (Gap 09).
**Severity:** INFO.
**Dashboard widget:** "N photos received — review."

### AT-7 — `STALE_THREAD_REPLY`

**Trigger:** Inbound with a superseded thread_id (Gap 03.B fix).
**Severity:** WARNING.
**Dashboard widget:** "N customers replied to outdated messages."
**Target:** triage page with context of the stale thread vs. current appointment.

### AT-8 — `WEBHOOK_FAILURE`

**Trigger:** Signature verification failures in the last hour exceeding threshold, or Redis unavailability prolonged (Gap 07).
**Severity:** ERROR.
**Dashboard widget:** "SMS webhook health issue — check ops runbook."
**Target:** Ops/admin settings page.

---

## Proposed API changes

Extend `GET /api/v1/alerts`:

```python
@router.get("")
async def list_alerts(
    acknowledged: bool = Query(default=False),
    alert_type: list[str] = Query(default=None),   # NEW
    severity: list[str] = Query(default=None),     # NEW
    entity_type: str = Query(default=None),        # NEW
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),          # NEW, for pagination
    sort: str = Query(default='created_at_desc'),  # NEW
):
```

Implement the `acknowledged=True` path (return historical alerts).

Add `GET /api/v1/alerts/counts` for per-type unacked counts used by dashboard widgets:

```json
{
  "pending_reschedule": 3,
  "informal_opt_out": 1,
  "unrecognized_confirmation_reply": 7,
  "confirmation_no_reply": 12,
  "customer_cancelled_appointment": 0,
  "orphan_inbound": 4
}
```

Dashboard loads this with its existing 60s `refetchInterval`.

---

## Proposed frontend changes

1. **Dashboard widgets for the top 4-5 alert types.** Initially: pending_reschedule, informal_opt_out, unrecognized_confirmation_reply, confirmation_no_reply. Each uses `AlertCard` with its own target path.

2. **Generic "All Alerts" view.** New route `/alerts` lists everything unacked, filterable by type and severity. Bulk ack actions ("acknowledge all of type X older than Y days").

3. **Alert detail modal.** Clicking an alert row shows the entity details + actions specific to the alert type (e.g., "Send Reminder" for a no-reply alert, "Reschedule" for a pending-reschedule).

---

## Edge cases

- **Alert deduplication.** If `PENDING_RESCHEDULE_REQUEST` already exists for an appointment and a second R comes in (Gap 01.A), don't create a duplicate Alert — increment an internal `occurrence_count` or note the second event in metadata.
- **Surface-at / quiet-hours:** per Gap 08, some alert types deserve deferral to business hours.
- **Auto-acknowledgment:** When the underlying state resolves (e.g., `RescheduleRequest.status='resolved'` by admin), the corresponding Alert should auto-ack. Add a hook in the resolve path.

---

## Cross-references

- **Gap 05** — audit coverage should drive or mirror alert creation sites.
- **Gap 06** — informal opt-out triage UI is blocked on the informal-opt-out alert type.
- **Gap 07** — webhook health alert.
- **Gap 10** — no-reply escalation alerts.
- **Gap 11** — AppointmentDetail should show active alerts for the appointment.
