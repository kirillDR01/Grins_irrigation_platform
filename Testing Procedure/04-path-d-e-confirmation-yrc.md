# Path D/E — Appointment confirmation + Y/R/C/STOP/START

Most interactive path. **Requires the phone-holder to actively reply.** Tell
them the expected text, wait for confirmation, then verify before moving on.

## Helper — pick a fresh Kirill TB_SCHEDULED job

Every sub-step of D/E wants a fresh appointment on an unused job, so you get
a new thread_id from CallRail each time.

```bash
pick_kirill_tbs_job() {
  curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs?page=1&page_size=100" \
    -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for j in json.load(sys.stdin)['items']:
    if j['customer_id']=='e7ba9b51-580e-407d-86a4-06fd4e059380' \
       and j['status']=='to_be_scheduled':
        print(j['id']); break
"
}
KIRILL=e7ba9b51-580e-407d-86a4-06fd4e059380
STAFF=0bb0466d-ce5e-477a-9292-7d4b9673a7f6
```

## D1 / E1 — Reply Y

```bash
JOB=$(pick_kirill_tbs_job)
APT=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"job_id\":\"$JOB\",\"staff_id\":\"$STAFF\",
    \"scheduled_date\":\"2026-04-21\",
    \"time_window_start\":\"10:00:00\",\"time_window_end\":\"12:00:00\",
    \"notes\":\"E2E-20260414-D1 confirmation\"
  }" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/$APT/send-confirmation" \
  -H "Authorization: Bearer $TOKEN"
```

**Tell phone-holder**: you should receive a text like:
> "Your appointment on Tuesday, April 21 between 10:00 AM and 12:00 PM for your [Service Type] has been scheduled. Reply Y to confirm, R to reschedule, or C to cancel. Reply STOP to opt out."

**Reply `Y`**. Phone receives back: *"Your appointment has been confirmed. See you then!"*

**Verify**:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/appointments/$APT" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])'
# Expect: confirmed

curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers/$KIRILL/sent-messages?limit=3" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for m in json.load(sys.stdin)['items'][:3]:
    print(f\"{m['message_type']:28} to={m['recipient_phone']}\")"
# Expect: recipient_phone is +19527373312 (E.164, NOT the +3312 mask — CR-3 fix)
```

## E3 — Reply R (creates reschedule_request)

Fresh appointment:
```bash
JOB=$(pick_kirill_tbs_job)
APT=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"job_id\":\"$JOB\",\"staff_id\":\"$STAFF\",
    \"scheduled_date\":\"2026-10-15\",
    \"time_window_start\":\"13:00:00\",\"time_window_end\":\"15:00:00\",
    \"notes\":\"E2E-20260414-E3 reschedule\"
  }" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/$APT/send-confirmation" \
  -H "Authorization: Bearer $TOKEN"
```

**Tell phone-holder**: reply `R`.

Phone should receive **TWO** auto-replies:
1. *"We received your reschedule request. Our team will reach out with alternative times shortly."*
2. *"We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up."*

**Verify**:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/schedule/reschedule-requests?status=open&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for r in json.load(sys.stdin)['items'][:5]:
    if r['appointment_id']=='$APT':
        print(f\"status={r['status']} raw={r['raw_alternatives_text']!r}\")"
# Expect: status=open raw='R'
```

## E4 / E5 — Append alternatives (M-3)

Same thread. Tell phone-holder to reply `Tue 2pm`.

```bash
# Verify after E4 reply:
curl -s "https://grins-dev-dev.up.railway.app/api/v1/schedule/reschedule-requests?status=open&limit=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
for r in json.load(sys.stdin)['items'][:5]:
    if r['appointment_id']=='$APT':
        ra = r['requested_alternatives'] or {}
        print(f\"entries: {len(ra.get('entries', []))}\"); print(ra)"
```

**Expect** 1 entry: `{"text":"Tue 2pm","at":"..."}`.

Then tell phone-holder to reply `or Wed morning`. Re-run the verify query.

**Expect** 2 entries, in order, both preserved (Sprint 7 M-3 append).

## E6 / E7 — Reply C, then C again

Fresh appointment. Same pattern as E3.

```bash
# (create DRAFT appt as above)
# Send confirmation
```

**Tell phone-holder**: reply `C`.

**Verify**:
- Appointment status → `cancelled`
- You receive: *"Your [Service] appointment on [Date] at [Time] has been cancelled. Please contact us..."* (Sprint 2 L-1 + M-11)

**Then** ask them to reply `C` again (**E7 idempotency check — H-2**).

📋 **Known gap**: the customer will receive a duplicate cancellation SMS
— H-2 is only half-fixed. DB stays `cancelled` (correct), but
`_handle_cancel` unconditionally sends the reply. File this as a follow-up.

## E8 — Reply STOP

Fresh appointment + send-confirmation. Tell phone-holder to reply `STOP`.

CallRail's provider-level handler returns:
> "You have successfully been unsubscribed. You will not receive any more messages from this number. Reply START to resubscribe."

**Verify**:
```bash
# Probe SMS send — expect consent denial
curl -s -w '\nHTTP %{http_code}\n' -X POST "https://grins-dev-dev.up.railway.app/api/v1/sms/send" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"customer_id\":\"$KIRILL\",\"phone\":\"+19527373312\",
    \"message\":\"probe after STOP\",
    \"message_type\":\"custom\",\"sms_opt_in\":false
  }"
# Expect: {"detail":"Consent denied for ..."} HTTP 403
```

📋 **Known gap**: `customers.sms_opt_in` flag stays `true` (denormalized
mirror not flipped). Source of truth is the consent_records table, which
is correctly populated.

## E9 — Restore consent for the next test

There is **no START handler** in the backend. To re-enable, run:

```bash
cp "Testing Procedure/scripts/clear_consent.py" /tmp/clear_consent.py
B64=$(base64 < /tmp/clear_consent.py | tr -d '\n')
railway ssh --service Grins-dev --environment dev \
  "python3 -c 'import base64,os; exec(base64.b64decode(\"$B64\"))'"
```

Also ask phone-holder to reply `START` to a thread — CallRail may keep them
blocked on their end until the carrier ack. If CallRail still returns
"recipient has opted out" errors after ~10 minutes, the next E2E session
may need to wait or contact CallRail.

## Acceptance

- [ ] Y → appointment CONFIRMED; `recipient_phone` is +19527373312 (E.164).
- [ ] R → reschedule_request `status=open`, 2 auto-replies received.
- [ ] E4 → `requested_alternatives.entries` has 1 entry.
- [ ] E5 → `requested_alternatives.entries` has 2 entries, ordered.
- [ ] C → appointment CANCELLED; cancellation SMS with service type + time.
- [ ] STOP → `/api/v1/sms/send` returns 403 "Consent denied".
- [ ] `clear_consent.py` removes the `text_stop` row, sends work again.
