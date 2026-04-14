# Path J — Schedule every TB_SCHEDULED job + bulk confirmation

The big integration test. Fans out appointment creation for every Kirill
TB_SCHEDULED job, then bulk-sends confirmations. Validates Sprint 5 M-8/M-9.

## Goal

Prove that:
1. The appointment-create endpoint handles a batch of ~28+ rows.
2. `POST /api/v1/appointments/send-confirmations` returns a `results: []`
   list with per-row `status` (`sent` / `deferred` / `skipped` / `failed`)
   and `reason` strings.
3. Only rows with `status=sent` transition DRAFT → SCHEDULED.
4. Failed rows stay DRAFT so admins can retry.

## Setup — inventory Kirill's jobs

```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs?page=1&page_size=100" \
  -H "Authorization: Bearer $TOKEN" > /tmp/jobs.json
python3 <<'PY'
import json
from collections import Counter
d = json.load(open('/tmp/jobs.json'))
kirill_tbs = [j for j in d['items'] if j['customer_id']=='e7ba9b51-580e-407d-86a4-06fd4e059380' and j['status']=='to_be_scheduled']
print(f'Kirill TB_SCHEDULED: {len(kirill_tbs)}')
json.dump([(j['id'], j['job_type']) for j in kirill_tbs], open('/tmp/kirill_tbs.json','w'))
PY
```

## Step 1 — create DRAFT appointments for all

```bash
python3 <<'PY'
import json, subprocess
token = open('/tmp/grins_token.txt').read().strip() if False else __import__('os').environ['TOKEN']
jobs = json.load(open('/tmp/kirill_tbs.json'))
staff = '0bb0466d-ce5e-477a-9292-7d4b9673a7f6'
from datetime import date, timedelta
base = date(2026, 5, 4)
created = []
for i, (jid, jtype) in enumerate(jobs):
    payload = json.dumps({
        "job_id": jid, "staff_id": staff,
        "scheduled_date": (base + timedelta(days=i*2)).isoformat(),
        "time_window_start":"09:00:00","time_window_end":"11:00:00",
        "notes":f"E2E-20260414-J {jtype}"
    })
    r = subprocess.run(
        ['curl','-s','-X','POST',
         'https://grins-dev-dev.up.railway.app/api/v1/appointments',
         '-H',f'Authorization: Bearer {token}',
         '-H','Content-Type: application/json',
         '-d',payload],
        capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        if 'id' in j: created.append(j['id'])
    except Exception:
        pass
print(f'Created: {len(created)}')
json.dump(created, open('/tmp/j_appts.json','w'))
PY
```

**Expect** `Created: N` where N == Kirill TB_SCHEDULED count.

## Step 2 — bulk-send confirmations

```bash
APPTS=$(python3 -c "import json;print(json.dumps(json.load(open('/tmp/j_appts.json'))))")
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/appointments/send-confirmations" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"appointment_ids\":$APPTS}" > /tmp/bulk_resp.json

python3 <<'PY'
import json
d = json.loads(open('/tmp/bulk_resp.json').read().split('\n')[0])
print(f"sent_count={d['sent_count']} deferred={d['deferred_count']} skipped={d['skipped_count']} failed={d['failed_count']} total={d['total_draft']}")
from collections import Counter
print('by_status:', dict(Counter(r['status'] for r in d['results'])))
PY
```

**Expect**:
- Every row has a `status` entry in the results list.
- `sent_count + deferred_count + skipped_count + failed_count == total_draft`.
- Real SMS arrive on +19527373312 for every `sent` row (allowlist of one).

⚠️ **Warn phone-holder** that they'll get a batch of texts — one per
successful send.

## Step 3 — verify status transitions

```bash
python3 <<'PY'
import json, subprocess, os
token = os.environ['TOKEN']
d = json.loads(open('/tmp/bulk_resp.json').read().split('\n')[0])
results = d['results']
sent_ids = [r['appointment_id'] for r in results if r['status']=='sent']
failed_ids = [r['appointment_id'] for r in results if r['status']=='failed']

# Sample check: 10 sent rows should all be SCHEDULED
bad_sent = 0
for aid in sent_ids[:10]:
    r = subprocess.run(['curl','-s',f'https://grins-dev-dev.up.railway.app/api/v1/appointments/{aid}',
                        '-H',f'Authorization: Bearer {token}'], capture_output=True, text=True)
    st = json.loads(r.stdout)['status']
    if st != 'scheduled': bad_sent += 1; print(f'  !! sent {aid[:8]}: status={st}')
print(f'sent sample clean: {10-bad_sent}/10')

# Every failed row should stay DRAFT
bad_failed = 0
for aid in failed_ids:
    r = subprocess.run(['curl','-s',f'https://grins-dev-dev.up.railway.app/api/v1/appointments/{aid}',
                        '-H',f'Authorization: Bearer {token}'], capture_output=True, text=True)
    st = json.loads(r.stdout)['status']
    if st != 'draft': bad_failed += 1; print(f'  !! failed {aid[:8]}: status={st} (should be draft)')
print(f'failed rows clean: {len(failed_ids)-bad_failed}/{len(failed_ids)}')
PY
```

**Expect** all checks clean.

## Acceptance (Sprint 5 M-8 / M-9)

- [ ] Bulk response totals match (`sent+deferred+skipped+failed==total_draft`).
- [ ] Every row has a `status` + optional `reason` string (no silent skips).
- [ ] All `status=sent` rows transitioned to `scheduled`.
- [ ] All `status=failed` rows stayed `draft` — retry path preserved.
- [ ] Only +19527373312 received real SMS (allowlist enforced).
