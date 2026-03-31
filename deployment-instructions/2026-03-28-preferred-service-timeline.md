# Deployment Instructions: Preferred Service Timeline

**Date:** 2026-03-28
**Feature:** Preferred Service Timeline (Onboarding) + Move to Agreements
**Commits:**
- `496afda` — feat: add preferred service timeline to onboarding
- `346aec6` — fix: include preferred_schedule in customer detail API response
- `fb95ea7` — refactor: move preferred_schedule from Customer to ServiceAgreement

**Repos affected:** `Grins_irrigation_platform` (backend + admin dashboard), `Grins_irrigation` (public frontend — unchanged by refactor)

---

## Overview

Adds a "Preferred Service Timeline" dropdown to the post-purchase onboarding form so customers can indicate when they'd like their service done (ASAP, 1-2 Weeks, 3-4 Weeks, or Other with free-text details).

The schedule preference is stored **on the service agreement** (not the customer), because it represents urgency for a specific purchase — not a lasting customer trait. This preserves per-purchase timeline history if a customer buys again.

The admin team sees the timeline on the **Agreement Detail** page and as a badge in the **Onboarding Incomplete** queue.

---

## Pre-Deployment Checklist

- [ ] Verify dev E2E tests passed (see `e2e-screenshots/schedule-testing/`)
- [ ] All 4 schedule options tested: ASAP, ONE_TWO_WEEKS, THREE_FOUR_WEEKS, OTHER + details
- [ ] Agreement Detail shows "Preferred Timeline" field after deploy
- [ ] Customer Detail no longer shows "Timeline" field after deploy
- [ ] Merge `dev` → `main` on `Grins_irrigation_platform` repo
- [ ] No new environment variables required
- [ ] No Stripe configuration changes required
- [ ] No CORS changes required
- [ ] Public frontend (`Grins_irrigation`) does NOT need redeployment for the refactor — it sends the same payload to the same endpoint

---

## 1. Database Changes

Two migrations run in sequence. Both run automatically via `alembic upgrade head` in the Dockerfile CMD.

### Migration 1: `20260328_100000_customer_add_preferred_schedule`

Adds two nullable columns to the `customers` table:

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| `preferred_schedule` | `VARCHAR(30)` | Yes | `NULL` |
| `preferred_schedule_details` | `TEXT` | Yes | `NULL` |

### Migration 2: `20260328_110000_move_preferred_schedule_to_agreements`

Moves the columns from `customers` to `service_agreements`:

1. Adds `preferred_schedule` (VARCHAR(30)) and `preferred_schedule_details` (TEXT) to `service_agreements`
2. Copies data from each customer to their **most recent** agreement (by `created_at`)
3. Drops both columns from `customers`

**Valid values for `preferred_schedule`:** `ASAP`, `ONE_TWO_WEEKS`, `THREE_FOUR_WEEKS`, `OTHER`

### Verification

After deployment, verify the columns are on `service_agreements` and gone from `customers`:

```bash
# Get auth token
TOKEN=$(curl -s "https://grinsirrigationplatform-production.up.railway.app/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<PROD_PASSWORD>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Verify agreements have preferred_schedule
curl -s "https://grinsirrigationplatform-production.up.railway.app/api/v1/agreements?sort_by=created_at&sort_order=desc&page_size=3" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
data = json.load(sys.stdin)
for a in data.get('items', []):
    print(a['agreement_number'], '|', 'sched:', a.get('preferred_schedule'), '|', 'details:', a.get('preferred_schedule_details'))
"

# Verify customers no longer have preferred_schedule
curl -s "https://grinsirrigationplatform-production.up.railway.app/api/v1/customers?page=1&page_size=1" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
data = json.load(sys.stdin)
if data.get('items'):
    c = data['items'][0]
    has_field = 'preferred_schedule' in c
    print('preferred_schedule on customer:', has_field, '(should be False)')
"
```

### Rollback

To fully roll back both migrations:

```bash
uv run alembic downgrade 20260326_120000
```

This reverses both migrations in order:
1. `20260328_110000` → restores columns to `customers` (copies from most recent agreement back)
2. `20260328_100000` → drops columns from `customers`

Net result: database returns to pre-feature state. No data loss for existing records.

---

## 2. Environment Variables

**No new environment variables are required.** The feature uses only existing database columns and API endpoints.

---

## 3. API Changes

### Modified Endpoints

| Endpoint | Change |
|----------|--------|
| `POST /api/v1/onboarding/complete` | New optional fields: `preferred_schedule` (default "ASAP"), `preferred_schedule_details` |
| `GET /api/v1/agreements` | Response now includes `preferred_schedule` and `preferred_schedule_details` |
| `GET /api/v1/agreements/{id}` | Response now includes `preferred_schedule` and `preferred_schedule_details` |
| `GET /api/v1/customers/{id}` | **Removed** `preferred_schedule` and `preferred_schedule_details` from response |
| `PUT /api/v1/customers/{id}` | **Removed** `preferred_schedule` and `preferred_schedule_details` from accepted fields |

### Request Schema: `POST /api/v1/onboarding/complete`

New fields (both optional, backwards-compatible):

```json
{
  "preferred_schedule": "ASAP",
  "preferred_schedule_details": null
}
```

**Validation rules:**
- `preferred_schedule` must be one of: `ASAP`, `ONE_TWO_WEEKS`, `THREE_FOUR_WEEKS`, `OTHER`
- When `preferred_schedule` is `OTHER`, `preferred_schedule_details` is required (non-empty)
- Defaults to `ASAP` if not provided (backwards-compatible with existing clients)

### Backwards Compatibility

- Existing onboarding submissions that don't include `preferred_schedule` will default to `ASAP`
- The public frontend (`Grins_irrigation`) sends the same `preferred_schedule` payload to the same endpoint — no changes needed there
- The `preferred_service_times` field (Morning/Afternoon preference) remains on the Customer model — only `preferred_schedule` moved

---

## 4. Deployment Steps

### Step 1: Merge to main (platform repo only)

The public frontend (`Grins_irrigation`) does not need redeployment for the refactor commit. It sends the same payload to the same API endpoint.

```bash
# Platform repo
cd /Users/kirillrakitin/Grins_irrigation_platform
git checkout main
git merge dev
git push origin main
```

### Step 2: Verify Railway deployment (backend)

Railway auto-deploys on push to `main`. The Dockerfile runs `alembic upgrade head` before starting uvicorn.

```bash
# Check deployment status via MCP
# mcp__railway__list-deployments (service: Grins_irrigation_platform, environment: production)
```

Wait for deployment status: **SUCCESS**

### Step 3: Verify both migrations ran

Check Railway deploy logs for both lines:

```
INFO  [alembic.runtime.migration] Running upgrade 20260326_120000 -> 20260328_100000, Add preferred_schedule columns to customers table.
INFO  [alembic.runtime.migration] Running upgrade 20260328_100000 -> 20260328_110000, Move preferred_schedule columns from customers to service_agreements.
```

If production already ran migration `20260328_100000` from an earlier deploy, only the second line will appear — that's fine.

### Step 4: Verify Vercel deployment (admin dashboard)

The admin dashboard Vercel project auto-deploys on push to `main`:
- `grins-irrigation-platform` — check target: `production`

Wait for state: **READY**

### Step 5: Smoke test

1. **API health check:**
   ```bash
   curl -s "https://grinsirrigationplatform-production.up.railway.app/health"
   # Should return {"status": "healthy"}
   ```

2. **Agreement API:** Fetch recent agreements and confirm `preferred_schedule` field is present:
   ```bash
   curl -s "https://grinsirrigationplatform-production.up.railway.app/api/v1/agreements?sort_by=created_at&sort_order=desc&page_size=3" \
     -H "Authorization: Bearer $TOKEN"
   # Each agreement should have "preferred_schedule" and "preferred_schedule_details" fields
   ```

3. **Customer API:** Fetch a customer and confirm `preferred_schedule` is absent:
   ```bash
   curl -s "https://grinsirrigationplatform-production.up.railway.app/api/v1/customers/{id}" \
     -H "Authorization: Bearer $TOKEN"
   # Should NOT contain "preferred_schedule" key
   # Should still contain "preferred_service_times" (Morning/Afternoon)
   ```

4. **Admin dashboard — Agreement Detail:** Navigate to an agreement that had a schedule set. Verify "Preferred Timeline" appears in the info section (after Payment Status).

5. **Admin dashboard — Customer Detail:** Navigate to the same customer. Verify the "Timeline" field is gone from Service Preferences. Only "Preferred Time" (Morning/Afternoon) should remain.

6. **Onboarding form:** Complete a test checkout and onboarding with a schedule selection. Verify the new agreement has the correct `preferred_schedule` value via the API.

---

## 5. Files Changed

### Platform Repo (`Grins_irrigation_platform`) — 27 files across 3 commits

#### Commit 1: `496afda` — feat: add preferred service timeline to onboarding (12 files)

| File | Change |
|------|--------|
| `migrations/versions/20260328_100000_customer_add_preferred_schedule.py` | **NEW** — migration adding columns to customers |
| `models/customer.py` | Add 2 columns (preferred_schedule, preferred_schedule_details) |
| `api/v1/onboarding.py` | Add fields to request schema + validator |
| `services/onboarding_service.py` | Add params + persist to customer |
| `services/customer_service.py` | Add fields to detail response dict |
| `schemas/customer.py` | Add fields to response + update schemas |
| `frontend/.../customers/types/index.ts` | Add fields to Customer + CustomerUpdate types |
| `frontend/.../customers/components/CustomerDetail.tsx` | Display preferred schedule in Service Preferences |
| `tests/unit/test_onboarding_preferred_schedule.py` | **NEW** — 8 unit tests |
| `tests/functional/test_onboarding_preferred_schedule.py` | **NEW** — 3 functional tests |
| `tests/integration/test_onboarding_preferred_schedule.py` | **NEW** — 2 integration tests |

#### Commit 2: `346aec6` — fix: include preferred_schedule in customer detail API response (1 file)

| File | Change |
|------|--------|
| `services/customer_service.py` | Add missing fields to response_data dict |

#### Commit 3: `fb95ea7` — refactor: move preferred_schedule from Customer to ServiceAgreement (15 files)

| File | Change |
|------|--------|
| `migrations/versions/20260328_110000_move_preferred_schedule_to_agreements.py` | **NEW** — migration moving columns from customers to service_agreements |
| `models/service_agreement.py` | Add 2 columns (preferred_schedule, preferred_schedule_details) |
| `models/customer.py` | Remove 2 columns |
| `services/onboarding_service.py` | Save schedule to agreement instead of customer |
| `schemas/agreement.py` | Add 2 fields to AgreementResponse |
| `api/v1/agreements.py` | Add to `_agreement_to_response()` serializer |
| `schemas/customer.py` | Remove 2 fields from CustomerResponse + CustomerUpdate |
| `services/customer_service.py` | Remove from response_data dict |
| `frontend/.../agreements/types/index.ts` | Add to Agreement interface |
| `frontend/.../agreements/components/AgreementDetail.tsx` | Add SCHEDULE_LABELS + display in InfoSection |
| `frontend/.../agreements/components/OnboardingIncompleteQueue.tsx` | Add schedule badge per row |
| `frontend/.../customers/types/index.ts` | Remove from Customer + CustomerUpdate |
| `frontend/.../customers/components/CustomerDetail.tsx` | Remove SCHEDULE_LABELS + schedule display |
| `tests/functional/test_onboarding_preferred_schedule.py` | Assert on agreement instead of customer |
| `tests/integration/test_onboarding_preferred_schedule.py` | Assert on agreement instead of customer |

### Public Frontend Repo (`Grins_irrigation`) — 4 files (unchanged by refactor)

| File | Change |
|------|--------|
| `frontend/src/features/onboarding/types/index.ts` | Add fields to form + request types |
| `frontend/src/features/onboarding/components/OnboardingPage.tsx` | Add dropdown, conditional input, disclaimer, validation |
| `frontend/src/features/onboarding/__tests__/onboarding-page.test.tsx` | Update + 7 new tests |
| `frontend/src/features/onboarding/__tests__/form-submission-payload.property.test.ts` | Add preferred_schedule to property tests |

---

## 6. What Does NOT Change

- **Public frontend** (`Grins_irrigation`) — sends same `preferred_schedule` in same API payload to same endpoint
- **Onboarding API request schema** — same fields, same validation, same endpoint
- **`preferred_service_times`** (Morning/Afternoon) — stays on Customer (lasting preference)
- **Unit tests** — validate `CompleteOnboardingRequest` schema, which is unchanged

---

## 7. Rollback Plan

If issues arise after production deployment:

### Option A: Full revert (recommended if caught early)

1. **Revert backend:**
   ```bash
   git revert HEAD~3..HEAD   # Reverts all 3 commits
   git push origin main
   ```
2. **Downgrade migrations:**
   ```bash
   uv run alembic downgrade 20260326_120000
   ```
   This rolls back both migrations safely — `20260328_110000` copies schedule data back from agreements to customers, then `20260328_100000` drops the columns from customers.

### Option B: Revert only the refactor (keep schedule on Customer)

If the feature itself is fine but the move to Agreement causes issues:

1. **Revert only the refactor commit:**
   ```bash
   git revert fb95ea7
   git push origin main
   ```
2. **Downgrade only the second migration:**
   ```bash
   uv run alembic downgrade 20260328_100000
   ```
   This moves schedule data back to customers and restores the original behavior.

### Option C: Emergency SQL rollback (if Alembic not available)

```sql
-- Reverse migration 20260328_110000 manually
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_schedule VARCHAR(30);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_schedule_details TEXT;

UPDATE customers c
SET preferred_schedule = sa.preferred_schedule,
    preferred_schedule_details = sa.preferred_schedule_details
FROM service_agreements sa
WHERE sa.customer_id = c.id
  AND sa.preferred_schedule IS NOT NULL
  AND sa.id = (
      SELECT sa2.id FROM service_agreements sa2
      WHERE sa2.customer_id = c.id
      ORDER BY sa2.created_at DESC LIMIT 1
  );

ALTER TABLE service_agreements DROP COLUMN IF EXISTS preferred_schedule;
ALTER TABLE service_agreements DROP COLUMN IF EXISTS preferred_schedule_details;

UPDATE alembic_version SET version_num = '20260328_100000';
```

To also reverse the first migration:

```sql
ALTER TABLE customers DROP COLUMN IF EXISTS preferred_schedule;
ALTER TABLE customers DROP COLUMN IF EXISTS preferred_schedule_details;

UPDATE alembic_version SET version_num = '20260326_120000';
```

All columns are nullable with no constraints, so rollback is safe and non-destructive.

---

## 8. Dev E2E Test Results (2026-03-28)

All schedule options tested end-to-end on the dev environment after deployment:

| Agreement | Package | Schedule | API Verified | Admin UI Verified |
|-----------|---------|----------|-------------|-------------------|
| AGR-2026-047 | Essential Residential $175 | ASAP | `preferred_schedule=ASAP` on agreement | "As Soon As Possible" on Agreement Detail |
| AGR-2026-048 | Professional Residential $260 | ONE_TWO_WEEKS | `preferred_schedule=ONE_TWO_WEEKS` on agreement | "Within 1-2 Weeks" on Agreement Detail |
| AGR-2026-049 | Essential Commercial $235 | OTHER + details | `preferred_schedule=OTHER` + details text on agreement | "Other" + detail text on Agreement Detail |
| AGR-2026-050 | Premium Residential $725 | THREE_FOUR_WEEKS | `preferred_schedule=THREE_FOUR_WEEKS` on agreement | "Within 3-4 Weeks" on Agreement Detail |

Additional verifications:
- Customer Detail page no longer shows "Timeline" field — only "Preferred Time" (Morning/Afternoon) remains
- Migration correctly copied existing schedule data from customers to their most recent agreements
- All 8 package checkout modals verified with correct pricing and surcharge calculations
- Screenshots: `e2e-screenshots/schedule-testing/` (50 screenshots)
