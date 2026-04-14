# Path C — Sales pipeline

Validates M-10 (missing-doc block) and the force-convert path that carries
`property_id` into the created Job.

Use the B1 sales_entry_id from Path B. Replace `<B1_SID>` below.

## C1 / C2 — Advance through the pipeline without a doc

The sales pipeline status chain is:
```
schedule_estimate → estimate_scheduled → send_estimate → pending_approval → ...
```

`send_estimate → pending_approval` is the gate that requires
`signwell_document_id`. Advance twice:

```bash
# 1st advance: schedule_estimate → estimate_scheduled
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/sales/pipeline/<B1_SID>/advance" \
  -H "Authorization: Bearer $TOKEN"

# 2nd advance: estimate_scheduled → send_estimate  (should SUCCEED)
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/sales/pipeline/<B1_SID>/advance" \
  -H "Authorization: Bearer $TOKEN"

# 3rd advance: send_estimate → pending_approval   (MUST BLOCK — M-10)
curl -s -w '\nHTTP %{http_code}\n' \
  -X POST "https://grins-dev-dev.up.railway.app/api/v1/sales/pipeline/<B1_SID>/advance" \
  -H "Authorization: Bearer $TOKEN"
```

**Expect** on the 3rd call:
```
{"detail":"Upload an estimate before advancing to pending approval"}
HTTP 422
```

## C4 — Force-convert to Job

Same sales entry, now force-convert without a signed doc:

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/sales/pipeline/<B1_SID>/force-convert" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}'
```

**Expect**:
```json
{"job_id":"<uuid>","status":"closed_won","forced":true}
```

Grab `job_id` and verify `property_id` carried through (Sprint 3 H-5/H-6):

```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs/<job_id-from-above>" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
j = json.load(sys.stdin)
for k in ['status','property_id','job_type','description']:
    print(f'  {k:15} {j.get(k)}')
"
```

**Expect** `property_id` is non-null and matches the SalesEntry's
`property_id`.

## Skipped / out-of-scope

- **C1 (Email for Signature / C3 Sign On-Site)** — requires a real SignWell
  document + webhook. Exercised in `test_sales_pipeline_functional.py`;
  live E2E not possible without SignWell sandbox credentials.
- **C5 (multi-entry signing correctness — H-7)** — ditto.

## Acceptance

- [ ] 2nd advance returns 200, status advances to `send_estimate`.
- [ ] 3rd advance returns 422 with detail `"Upload an estimate before
      advancing to pending approval"`.
- [ ] Force-convert returns `{job_id, status: "closed_won", forced: true}`.
- [ ] Job from force-convert has non-null `property_id`.
