# Path I — Dashboard counter invalidation (E-BUG-J)

Validates Sprint 7 E-BUG-J: creating or deleting a lead updates the
sidebar counter immediately.

## Backend signal

Without the browser, we verify the backend data changes. The frontend
invalidation is a direct code path in `useLeadMutations.ts`.

```bash
# Snapshot dashboard summary before
BEFORE=$(curl -s "https://grins-dev-dev.up.railway.app/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["new_leads_count"])')
echo "new_leads_count before: $BEFORE"

# I1 — Create lead
LID=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads/manual" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "name":"E2E-20260414-I1 Counter",
    "phone":"+19525550505",
    "address":"300 Counter Test St, Edina, MN 55410",
    "situation":"exploring"
  }' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

AFTER=$(curl -s "https://grins-dev-dev.up.railway.app/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["new_leads_count"])')
echo "new_leads_count after create: $AFTER"

# I2 — Delete lead
curl -s -X DELETE "https://grins-dev-dev.up.railway.app/api/v1/leads/$LID" -H "Authorization: Bearer $TOKEN"
AFTER2=$(curl -s "https://grins-dev-dev.up.railway.app/api/v1/dashboard/summary" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["new_leads_count"])')
echo "new_leads_count after delete: $AFTER2"
```

**Expect** `AFTER = BEFORE + 1` and `AFTER2 = BEFORE`.

## Frontend verification (manual)

In the CRM admin UI at the Vercel dev URL:
1. Watch the "New Leads" counter in the left sidebar.
2. Click "Add Lead" → submit any valid lead.
3. Counter should tick up **immediately** (no refresh needed).
4. Delete that lead.
5. Counter should tick back down immediately.

That's the `dashboardKeys.summary()` invalidation added in Sprint 7
(`frontend/src/features/leads/hooks/useLeadMutations.ts`).

## Acceptance

- [ ] Backend new_leads_count increments then decrements correctly.
- [ ] (If a browser is available) sidebar counter moves immediately
      without a page reload.
