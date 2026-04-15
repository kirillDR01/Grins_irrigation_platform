# 00 — Pre-flight

Everything you must verify or set up **before** running any Path.

## Environment

| Thing | Value |
|---|---|
| Railway project | `zealous-heart` |
| Railway environment | `dev` |
| Railway service | `Grins-dev` |
| API base URL | `https://grins-dev-dev.up.railway.app` |
| Admin login | `admin` / `admin123` |
| CRM frontend (dev) | `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` |
| Marketing frontend (dev) | `https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app` |
| SMS test allowlist | `+19527373312` (ONLY number that can receive SMS in dev) |

## One-time verification

```bash
# 1. Railway CLI linked to the right thing
cd "/Users/kirillrakitin/Grins_irrigation_platform"
railway status
# Expect: Project: zealous-heart, Environment: dev, Service: Grins-dev

# 2. Dev API is up
curl -s https://grins-dev-dev.up.railway.app/health
# Expect: {"status":"healthy","version":"1.0.0","database":{"status":"healthy","database":"connected"}}

# 3. Required env vars present on dev
railway variables --service Grins-dev --environment dev --kv | grep -E '^(SMS_TEST_PHONE_ALLOWLIST|GOOGLE_REVIEW_URL|SMS_PROVIDER|CALLRAIL_TRACKING_NUMBER)='
# Expect:
#   SMS_PROVIDER=callrail
#   SMS_TEST_PHONE_ALLOWLIST=+19527373312
#   CALLRAIL_TRACKING_NUMBER=+19525293750
#   GOOGLE_REVIEW_URL=<any non-empty URL>   # required since Sprint 2 fail-closed
```

If `GOOGLE_REVIEW_URL` is missing, Path F5/F6 will fail. Set it:

```bash
railway variables --set 'GOOGLE_REVIEW_URL=https://www.google.com/search?q=Grins+Irrigation+and+Landscape+Reviews' --service Grins-dev --environment dev
```

(Any valid URL is fine; the app only validates it's set.)

## Get an auth token

JWT tokens expire after ~1 hour. Re-run this between paths if you see 401s.

```bash
TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
export TOKEN
echo "Token length: ${#TOKEN}"   # ~239
```

## Confirm seed customer

```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers?search=Kirill&page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
items = json.load(sys.stdin).get('items', [])
for c in items:
    if c['first_name']=='Kirill' and c.get('phone','').endswith('7373312'):
        print(f\"ID:       {c['id']}\")
        print(f\"Phone:    {c['phone']}\")
        print(f\"Opt-in:   {c['sms_opt_in']}\")
        break
else:
    print('SEED CUSTOMER MISSING — create via Add Customer UI first')
"
# Expect:
#   ID:     e7ba9b51-580e-407d-86a4-06fd4e059380
#   Phone:  9527373312
#   Opt-in: True
```

## Clear any leftover STOP from prior test runs

CallRail's carrier-level opt-out AND our `sms_consent_records` table both need
to be clean before testing. Our DB side:

```bash
# Copy the helper script to /tmp and run it via railway ssh
cp "Testing Procedure/scripts/clear_consent.py" /tmp/clear_consent.py
B64=$(base64 < /tmp/clear_consent.py | tr -d '\n')
railway ssh --service Grins-dev --environment dev \
  "python3 -c 'import base64,os; exec(base64.b64decode(\"$B64\"))'"
```

If `customers.sms_opt_in` is already `true` and there is no `text_stop` row,
this is a no-op. If you see "Deleted: DELETE 1" it cleared a prior opt-out.

**CallRail side**: if prior sessions sent STOP and CallRail's provider
started blocking sends, you may need to wait (sometimes it clears within
~30 min after START) or contact CallRail support. The probe below tells you
whether it's clear:

```bash
# Probe: send a custom SMS with unique text
TS=$(date +%s)
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/sms/send" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{
    \"customer_id\":\"e7ba9b51-580e-407d-86a4-06fd4e059380\",
    \"phone\":\"+19527373312\",
    \"message\":\"E2E preflight probe $TS\",
    \"message_type\":\"custom\",
    \"sms_opt_in\":true
  }"
# GOOD: {"success":true,"message_id":"...","provider_message_id":"...","status":"sent"}
# CALLRAIL BLOCK: success=false with 400 error about "recipient has opted out"
# DEDUP:   success=false, reason="Duplicate message prevented" (benign — try another body)
```

**Confirm on the phone**: the allowlisted phone should ping with
"E2E preflight probe {timestamp}. Reply STOP to opt out." That proves the
entire pipeline works for the paths that follow.

## Inventory jobs

Handy for Path J sizing:

```bash
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs?page=1&page_size=100" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
from collections import Counter
d = json.load(sys.stdin)
by_status = Counter(j['status'] for j in d['items'])
print('By status:', dict(by_status))
"
```

When the pre-flight probes pass, move on to `01-path-a-lead-intake.md`.
