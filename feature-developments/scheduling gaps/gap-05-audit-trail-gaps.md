# Gap 05 — Audit Trail Gaps

**Severity:** 3 (medium)
**Area:** Backend (observability + compliance)
**Status:** Investigated, not fixed
**Related files:**
- `src/grins_platform/services/job_confirmation_service.py:361-397` — `_record_customer_sms_cancel_audit` (the only customer-SMS audit site)
- `src/grins_platform/services/appointment_service.py:1219-1251` — `_record_reschedule_reconfirmation_audit` (admin-triggered reschedule audit)
- `src/grins_platform/services/appointment_service.py:754-823` — `_record_cancellation_audit` (admin cancel)
- `src/grins_platform/models/audit_log.py:21-70` — `AuditLog` model
- `src/grins_platform/services/sms_service.py:~700-900` — opt-out processing (not audited via AuditLog)

---

## Summary

Audit logging for customer-driven reply events is **asymmetric**. Cancellations (C replies) are audited. Reschedule requests (R replies), confirmations (Y replies), and opt-outs (STOP and informal) are not. This creates a partial picture in the audit log:

- You can answer: *"when did this appointment get cancelled by customer SMS?"* — yes.
- You cannot answer: *"when did this customer confirm? reschedule? opt out?"* — not from `AuditLog` alone. You have to join across `JobConfirmationResponse`, `RescheduleRequest`, `SmsConsentRecord`, each of which tells a slice.

For compliance (10DLC requires a reasoned record of consent and any reschedules that touched a customer's schedule commitment), and for operational debugging (*"what happened to this appointment last Tuesday?"*), the audit should be uniform.

---

## Current state — what IS audited

### 1. Customer SMS cancellation (C reply)
`_record_customer_sms_cancel_audit` at `job_confirmation_service.py:361-397`:

```python
await self._audit.record(
    action="appointment.cancel",
    resource_type="appointment",
    resource_id=appointment_id,
    actor_id=None,  # customer, not staff
    details={
        "source": "customer_sms",
        "pre_cancel_status": pre_status,
        "response_id": str(response_id),
        "from_phone": from_phone,
    },
)
```

Only fires when `transitioned=True` (status actually changed). Repeat C is already short-circuited in `_handle_cancel`, so no duplicate audit rows.

### 2. Admin resolving a reschedule request (`reschedule_for_request`)
`_record_reschedule_reconfirmation_audit` at `appointment_service.py:1219-1251`. Details include actor_id (admin staff), new_scheduled_at, and resource_id. Called on line 1205.

### 3. Admin direct cancellation
`_record_cancellation_audit` at `appointment_service.py:754-823`. Distinguishes `source='staff'` from the customer path via `actor_id`. Includes reason_code.

### 4. Job and service agreement lifecycle events
Out of scope for this gap doc, but exist.

---

## What IS NOT audited

### 5.A — Customer Y (confirm)

`_handle_confirm` transitions SCHEDULED → CONFIRMED and writes a `JobConfirmationResponse` row with `status='confirmed'`. No `AuditLog` entry.

The response row *is* the audit trail — it has `received_at`, `raw_reply_body`, `from_phone`, `sent_message_id`. But:
- It's not queryable alongside other audit events ("show me everything that happened to this appointment last week" requires joining multiple tables).
- There's no single audit timeline endpoint / no `audit.list?resource_id=X` call that surfaces confirmations.
- The AppointmentDetail UI (Gap 11) doesn't read `JobConfirmationResponse` today; an audit-driven timeline is a more natural render.

### 5.B — Customer R (reschedule request)

`_handle_reschedule` creates a `RescheduleRequest` row and sets `response.status='reschedule_requested'`. No `AuditLog` entry for the R reply itself. Audit only fires when/if the admin later resolves the request (`_record_reschedule_reconfirmation_audit`).

Gap:
- The *customer's* action isn't audited, only the admin's follow-up. So a request that sits open forever (or gets resolved by manual edit outside the standard flow) leaves no trace.
- Compliance: if the customer disputes a reschedule ("I never asked for that"), we'd want an audit row asserting the SMS body and phone number.

### 5.C — Opt-out (STOP)

Exact-keyword opt-out creates a new `SmsConsentRecord(consent_given=False, opt_out_method='text_stop')`. `SmsConsentRecord` is insert-only and serves as its own audit trail — but again:
- Not queryable from `AuditLog`.
- Informal opt-outs (*"please stop texting me"*) flag an Alert (`alert_type='INFORMAL_OPT_OUT'` per Gap 06) but don't write a consent record OR an audit log entry. See Gap 06 for the full story.

### 5.D — Confirmation reminder SMS sent (manual from NoReplyReviewQueue)

When admin clicks "Send Reminder SMS" in `NoReplyReviewQueue`, a fresh Y/R/C prompt is sent. Actor-attributed, customer-affecting — no audit log entry. (A `sent_messages` row is created which is the message log, but AuditLog is separate.)

### 5.E — Admin "Mark Contacted" in review queue

Clears `needs_review_reason`. No audit log — the flag change is silently overwritten.

### 5.F — Admin reschedules via drag-drop (without a customer R)

`update_appointment` sends a reschedule SMS and resets status. Audit log coverage here needs verification (grep `_record_*_audit` calls from `update_appointment`): if absent, this is a significant gap — drag-drop is the most common admin reschedule path.

---

## Why this matters

### Compliance / 10DLC / CTIA
- 10DLC carriers (and CTIA guidelines) expect records of consent and opt-out. `SmsConsentRecord` covers explicit consent but not the audit-history angle of *"this customer opted out, then later re-opted-in, then asked to reschedule an existing appt"*.
- Informal opt-outs that never produce a `SmsConsentRecord` or `AuditLog` row are invisible in compliance reporting.

### Operational debugging
- *"Why did this appointment get moved last Tuesday?"* currently requires checking 4+ sources: `AuditLog`, `JobConfirmationResponse`, `RescheduleRequest`, `SentMessage`, Alerts. A unified timeline view (see Gap 11) would read from a single authoritative log.

### Customer dispute resolution
- If a customer claims they never received X or never sent Y, we want a single query that shows every inbound+outbound+state-change event keyed to their customer_id or appointment_id.

---

## Proposed fix

### Near-term (non-breaking)

Add `AuditLog` entries at these sites:

| Event | Location | Action | Actor | Key details |
|---|---|---|---|---|
| Customer Y reply | `_handle_confirm` | `appointment.confirm` | None (customer) | `pre_status`, `response_id`, `from_phone`, `raw_body` |
| Customer R reply | `_handle_reschedule` | `appointment.reschedule_requested` | None | `response_id`, `from_phone`, `raw_body`, `reschedule_request_id` |
| STOP opt-out | opt-out handler in `sms_service` | `consent.opt_out_sms` | None | `phone`, `consent_record_id`, `method` |
| Informal opt-out | `_flag_informal_opt_out` | `consent.opt_out_informal_flag` | None | `phone`, `alert_id`, `raw_body` |
| Send Reminder SMS | Manual reminder endpoint | `appointment.reminder_sent` | staff_id | `appointment_id`, `message_id` |
| Mark Contacted | Mark-contacted endpoint | `appointment.mark_contacted` | staff_id | `appointment_id`, `prior_reason` |
| Admin drag-drop reschedule | `update_appointment` | `appointment.reschedule` | staff_id | `from_datetime`, `to_datetime`, `reason='admin_edit'` |

Each entry is small. The pattern already exists for `_record_customer_sms_cancel_audit` — it's just not replicated.

### Medium-term (consolidation)

Centralize status transitions through the `transition_to` method proposed in Gap 04, and hook an audit-log write into that method. Every state change becomes an audit event automatically — no per-caller remembering.

### Long-term (timeline UI)

Build a single `GET /api/v1/appointments/{id}/timeline` endpoint that reads:
- `AuditLog.filter(resource_id=appointment_id)`
- `JobConfirmationResponse.filter(appointment_id=appointment_id)`
- `RescheduleRequest.filter(appointment_id=appointment_id)`
- `SentMessage.filter(appointment_id=appointment_id)`
- `Alert.filter(entity_type='appointment', entity_id=appointment_id)`

Merge-sort by timestamp, return a typed event stream. This feeds the AppointmentDetail inbound-visibility gap (Gap 11) and the unified inbox (Gap 16).

---

## Edge cases

- **Do not audit every ORM update** — only customer-affecting status changes and cross-cut events. Administrative metadata changes (notes, staff reassignment) are not audit-worthy in this first pass.
- **Actor vs. system:** customer events have `actor_id=None` and rely on `source` in details. Maybe add a dedicated `actor_type` column (`staff | customer | system`) to disambiguate.
- **PII in details:** `raw_body` may contain PII. The `AuditLog.details` JSON is already trusted internal data, but we should be consistent — if `JobConfirmationResponse` is deemed safe, so is the audit row.

---

## Cross-references

- **Gap 04** — state machine centralization creates the natural hook for audit writes.
- **Gap 06** — informal opt-out triage UI depends on the event existing in a queryable place.
- **Gap 11** — AppointmentDetail timeline reads from audit + responses + reschedules + messages.
- **Gap 14** — many of these events deserve a dashboard alert type too (informal opt-out, stale-thread reply, late reschedule attempt).
