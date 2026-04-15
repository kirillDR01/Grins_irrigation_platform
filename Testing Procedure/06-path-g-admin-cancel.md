# Path G — Admin cancel / reschedule

Validates CR-2 (cancel SMS fires), H-8 (reactivate CANCELLED → SCHEDULED
sends reschedule SMS).

## G1 — Admin cancels a CONFIRMED appointment (notify=true)

Use the D1/E1 appointment (should be `confirmed` by this point).

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/<D1_APT>/cancel" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"notify_customer": true, "reason": "E2E G1 admin cancel"}'
```

**Expect** `HTTP 200` with body like:
```json
{"appointment_id":"<id>","cancelled_at":"...","reason":"...","message":"Appointment cancelled successfully"}
```

**Phone** receives the cancellation SMS (service type + date + time).

**Verify**:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers/$KIRILL/sent-messages?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for m in json.load(sys.stdin)['items'][:5]:
    if m['message_type']=='appointment_cancellation':
        print(f\"{m['created_at'][:19]} to={m['recipient_phone']}\"); break
"
```

## G2 — Admin cancel with notify=false

Same as G1 but with `notify_customer: false`. No SMS, appointment still
CANCELLED. Unit-test covered; skip in live runs unless regressing.

## G3 — Reactivate a CANCELLED appointment (H-8)

```bash
curl -s -X PUT "https://grins-dev-dev.up.railway.app/api/v1/appointments/<G1_APT>" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "status": "scheduled",
    "scheduled_date": "2026-04-22",
    "time_window_start": "11:00:00",
    "time_window_end": "13:00:00"
  }'
```

**Expect** `HTTP 200`, appointment returns to `scheduled` with new date.

**Critical H-8 verify**:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers/$KIRILL/sent-messages?limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for m in json.load(sys.stdin)['items'][:5]:
    if m['message_type']=='appointment_reschedule':
        print('✅ H-8 verified — appointment_reschedule SMS row found'); break
"
```

**Phone** receives: "Your [Service] appointment has been rescheduled to
Tuesday, April 22 between 11:00 AM and 1:00 PM..."

## G4 — Cancel last IN_PROGRESS appointment

Covered by Sprint 4 M-2 / L-12 unit tests. Skipped in standard live run.

## Acceptance

- [ ] G1: appointment CANCELLED; `appointment_cancellation` sent_message
      row created with phone +19527373312.
- [ ] G3: appointment returns to SCHEDULED; `appointment_reschedule`
      sent_message row created (Sprint 2 H-8 fix).
