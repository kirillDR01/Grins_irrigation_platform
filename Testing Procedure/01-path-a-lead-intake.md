# Path A — Lead intake

Validates the three lead-create paths and E-BUG-C/H (Sprint 7 fixes).

## A1 — Public quote form submission

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "E2E-20260414-A1 Quote",
    "phone": "+19525550101",
    "address": "7400 Metro Blvd, Edina, MN 55439",
    "zip_code": "55439",
    "situation": "repair",
    "email": "e2e-a1@example.com",
    "source_site": "website",
    "page_url": "https://grins.com/quote",
    "sms_consent": true,
    "terms_accepted": true,
    "email_marketing_consent": false
  }'
```

**Expect** `HTTP 201` and:

```json
{"success":true,"message":"Thank you! We'll reach out within 1-2 business days.","lead_id":"<uuid>"}
```

## A2 — Manual Add Lead (E.164 phone + Winterization)

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name": "E2E-20260414-A2 Winter",
    "phone": "+19525550202",
    "address": "7700 Cahill Rd, Edina, MN 55439",
    "situation": "winterization",
    "notes": "E2E A2 — Winterization via E.164"
  }'
```

**Expect** `HTTP 201` with `situation: "winterization"` accepted.

- ✅ **E-BUG-H** — backend accepts `winterization` + `seasonal_maintenance` enum values (Sprint 7).

## A3 — Manual Add Lead (messy phone format)

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name": "E2E-20260414-A3 Messy",
    "phone": "(952) 737-3312",
    "address": "100 Example St, Minneapolis, MN 55401",
    "situation": "seasonal_maintenance",
    "notes": "E2E A3 — messy phone format"
  }'
```

**Expect** `HTTP 201`. Stored phone becomes `9527373312` (bare 10-digit; the
non-digit characters get stripped).

📋 **Known gap** — `ManualLeadCreate` does not E.164-normalize phones the way
`LeadSubmission` does (Sprint 6 M-5 only widened the public-form path). Not
blocking; consent matching uses `_phone_variants` that accepts both forms.

## Verify

```bash
# Save the IDs above into shell vars (replace with the actual uuids from the responses):
A1_LID=<id-from-A1>
A2_LID=<id-from-A2>
A3_LID=<id-from-A3>

for L in $A1_LID $A2_LID $A3_LID; do
  curl -s "https://grins-dev-dev.up.railway.app/api/v1/leads/$L" \
    -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
l = json.load(sys.stdin)
for k in ['name','phone','situation','source_site','lead_source','status']:
    print(f'  {k:15} {l.get(k)}')
"
done
```

**Expect** each lead `status=new`, correct `situation`, and `source_site`
of either `website` (A1) or `admin` (A2/A3).

## Acceptance

- [ ] A1 returns 201 + success banner text.
- [ ] A2 returns 201 with `situation: winterization` accepted.
- [ ] A3 returns 201 with `situation: seasonal_maintenance` accepted.
- [ ] `sms_consent` recorded as `true` for A1 and `false` for A2/A3.
