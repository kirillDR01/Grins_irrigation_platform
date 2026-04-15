# Path F — On-site workflow

Validates L-2 (on_my_way rollback), M-1 (complete from TB_SCHEDULED),
E-BUG-F (structured 409 on review dedup).

## F1 — On My Way from SCHEDULED

```bash
JOB=$(pick_kirill_tbs_job)
APT=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"job_id\":\"$JOB\",\"staff_id\":\"$STAFF\",
    \"scheduled_date\":\"2026-04-20\",
    \"time_window_start\":\"08:00:00\",\"time_window_end\":\"10:00:00\",
    \"status\":\"scheduled\",
    \"notes\":\"E2E-20260414-F1 On My Way\"
  }" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB/on-my-way" \
  -H "Authorization: Bearer $TOKEN"
```

**Expect** appointment → `en_route`, `job.on_my_way_at` populated, SMS sent
(phone receives "We're on our way!").

**Sprint 7 L-2 negative-test**: if CallRail rejects the send, our handler
*rolls back* `job.on_my_way_at` to the prior value (the send didn't succeed
so the admin audit shouldn't claim it did). Confirm by:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print("on_my_way_at:", json.load(sys.stdin).get("on_my_way_at"))'
```

## F2 — Started from SCHEDULED (skip On My Way)

```bash
JOB=$(pick_kirill_tbs_job)
APT=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"job_id\":\"$JOB\",\"staff_id\":\"$STAFF\",
    \"scheduled_date\":\"2026-05-18\",
    \"time_window_start\":\"11:00:00\",\"time_window_end\":\"13:00:00\",
    \"status\":\"scheduled\",
    \"notes\":\"E2E-20260414-F2 Started skip\"
  }" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB/started" \
  -H "Authorization: Bearer $TOKEN"
```

**Expect** job → `in_progress`, `started_at` populated.

📋 **Known gap**: the appointment stays `scheduled` — the `started` endpoint
only transitions from EN_ROUTE or CONFIRMED. File as a follow-up.

## F3 — Complete from TB_SCHEDULED (M-1)

Pick a TB_SCHEDULED job with a `service_agreement_id` (service-agreement
path). **Do not** create an appointment first — this tests the skip path.

```bash
JOB=<some-kirill-tbs-job-with-service-agreement>
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB/complete" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"skip_invoice": true, "skip_payment": true}'
```

**Expect** response `{"status":"completed","completed_at":"..."}` or similar.

**Verify**:
```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs/$JOB" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;j=json.load(sys.stdin);print("status:",j["status"],"completed_at:",j["completed_at"])'
```
**Expect**: `status: completed`.

## F4 — Complete from IN_PROGRESS

Use the job from F2 (already `in_progress`):
```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/jobs/<F2_JOB_ID>/complete" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"skip_invoice": true, "skip_payment": true}'
```

## F5 — Request Google Review

Pick an appointment attached to a completed job (or from F2 set to `completed`).
Mark the appointment completed first if needed.

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/<APPT>/request-review" \
  -H "Authorization: Bearer $TOKEN"
```

On first call: SMS goes out with the Google review link, response 200 with
`{sent: true, reason: null}`.

## F6 — Review dedup (Sprint 7 E-BUG-F)

Re-call the same endpoint immediately:
```bash
curl -s -w '\nHTTP %{http_code}\n' \
  -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/<APPT>/request-review" \
  -H "Authorization: Bearer $TOKEN"
```

**Expect**:
```json
{"detail":{"code":"REVIEW_ALREADY_SENT","message":"...","last_sent_at":"2026-..."}}
HTTP 409
```

This is exactly the shape the frontend `ReviewRequest.tsx` consumes.

## F7 — Opted-out customer review request

Skipped in standard runs — requires flipping a customer to `sms_opt_in=false`
AND having a `text_stop` record. The CR-9 remainder fix (clean 422, not 500)
is unit-test covered.

## Acceptance

- [ ] F1: appointment EN_ROUTE. `job.on_my_way_at` populated IF SMS
      succeeded; null IF CallRail blocked (L-2 rollback verified).
- [ ] F3: job directly TB_SCHEDULED → COMPLETED with skip flags.
- [ ] F4: job IN_PROGRESS → COMPLETED.
- [ ] F5: first call returns 200.
- [ ] F6: second call returns 409 with structured `{code, message,
      last_sent_at}` detail.
