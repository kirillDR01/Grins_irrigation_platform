# Path B — Lead → Sales

Validates E-BUG-D (merge toast), H-5/H-6 (property carry-through), L-8
(`job_type_display`), and the requires-estimate warning.

## Setup

Create fresh B1/B2/B3 leads. B2 must share a phone with the seed Kirill
customer so the merge path triggers.

```bash
B1_LID=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name":"E2E-20260414-B1 Winter",
    "phone":"+19525550404",
    "address":"8000 Test Property Rd, Edina, MN 55439",
    "situation":"winterization",
    "notes":"E2E B1 — net-new customer"
  }' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

B2_LID=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name":"E2E-20260414-B2 Merge",
    "phone":"(952) 737-3312",
    "address":"200 Merge Test Ln, Minneapolis, MN 55402",
    "situation":"seasonal_maintenance",
    "notes":"E2E B2 — should merge into Kirill"
  }' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

B3_LID=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name":"E2E-20260414-B3 NewSys",
    "phone":"+19525550303",
    "address":"500 Example Ln, Edina, MN 55424",
    "situation":"new_system",
    "notes":"E2E B3 — requires_estimate warning"
  }' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

echo "B1=$B1_LID B2=$B2_LID B3=$B3_LID"
```

## B1 — Move to Sales (net-new customer)

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/$B1_LID/move-to-sales" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expect**:
```json
{
  "success": true,
  "customer_id": "<fresh-uuid>",
  "sales_entry_id": "<uuid>",
  "message": "Lead moved to Sales",
  "requires_estimate_warning": false,
  "merged_into_customer": null
}
```

## B2 — Move to Sales (auto-merge into Kirill)

```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/$B2_LID/move-to-sales" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Expect** (E-BUG-D):
```json
{
  "customer_id": "e7ba9b51-580e-407d-86a4-06fd4e059380",
  "message": "Merged into existing customer: Kirill Rakitin",
  "merged_into_customer": {"id":"e7ba9b51-...","name":"Kirill Rakitin"}
}
```

## B3 — Move to Jobs with requires-estimate warning

**First pass** (no `force`):
```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/$B3_LID/move-to-jobs" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}' \
  | python3 -m json.tool
```

**Expect** `requires_estimate_warning: true`, `job_id: null`, and the
advisory message.

**Second pass** (`force=true`):
```bash
curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/$B3_LID/move-to-jobs?force=true" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{}' \
  | python3 -m json.tool
```

**Expect** `job_id` populated, `requires_estimate_warning: false`.

## Verify — property carry-through + job_type_display

Grab the sales_entry IDs from B1 and B2 responses above and:

```bash
for SID in <B1-sales-entry-id> <B2-sales-entry-id>; do
  curl -s "https://grins-dev-dev.up.railway.app/api/v1/sales/pipeline/$SID" \
    -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
e = json.load(sys.stdin)
for k in ['property_id','property_address','job_type','job_type_display','status','customer_name']:
    print(f'  {k:20} {e.get(k)}')
"
done
```

**Expect** (H-5/H-6 + L-8):
- `property_id` is a UUID (not `null`)
- `property_address` parsed from the lead address
- `job_type_display` reads `Winterization` / `Seasonal Maintenance` (not
  the raw slug)

## Acceptance

- [ ] B1 creates fresh customer (`merged_into_customer: null`).
- [ ] B2 response has `merged_into_customer: {id, name: "Kirill Rakitin"}`
      and message `"Merged into existing customer: Kirill Rakitin"`.
- [ ] B3 first call returns `requires_estimate_warning: true`.
- [ ] B3 `force=true` call creates a job (id in response).
- [ ] Sales entries have non-null `property_id` and `job_type_display`
      reads as a human name.
