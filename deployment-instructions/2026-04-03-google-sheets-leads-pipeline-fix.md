# Deployment Instructions: Google Sheets → Leads Pipeline Fix

**Date:** April 3, 2026
**Branch:** `ASAP_changes` (merged to `dev`)
**Commit:** `1ff6e2f` — fix: Google Sheets → Leads pipeline with header-based column mapping

---

## Summary

Fixes the broken Google Sheets → Leads pipeline that was creating "Unknown" contacts with phone "0000000000". Replaces hardcoded positional column mapping with dynamic header-based mapping that adapts to the restructured Google Form (29 columns, new data in columns T-AC).

---

## 1. Database Migration (Required)

### What Changed

Adds 3 new nullable columns to the `google_sheet_submissions` table for the new Google Form fields:

| Column | Type | Description |
|--------|------|-------------|
| `zip_code` | `VARCHAR(20)` | Zip code from column W |
| `work_requested` | `VARCHAR(255)` | Service type selection from column Z |
| `agreed_to_terms` | `VARCHAR(10)` | "Yes"/"No" terms agreement from column AC |

### Migration Command

```bash
uv run alembic upgrade head
```

This runs migration `20260403_100000_add_submission_new_form_fields` which:
1. Adds `zip_code` (VARCHAR(20), nullable) to `google_sheet_submissions`
2. Adds `work_requested` (VARCHAR(255), nullable) to `google_sheet_submissions`
3. Adds `agreed_to_terms` (VARCHAR(10), nullable) to `google_sheet_submissions`

**Safe for zero-downtime deployment — all columns are nullable with no default, no data migration needed.**

### Verification

After migration, verify the columns exist:

```bash
uv run python -c "
from sqlalchemy import create_engine, text, inspect
import os
engine = create_engine(os.environ['DATABASE_URL'].replace('+asyncpg', ''))
inspector = inspect(engine)
cols = [c['name'] for c in inspector.get_columns('google_sheet_submissions')]
for expected in ('zip_code', 'work_requested', 'agreed_to_terms'):
    status = 'FOUND' if expected in cols else 'MISSING'
    print(f'{expected}: {status}')
"
```

---

## 2. Code Changes (Auto-deployed with branch merge)

### Files Modified

| File | Change |
|------|--------|
| `services/google_sheets_service.py` | Header-based dynamic column mapping (last-match-wins), extras extraction, full lead field population (address, city, zip_code, terms_accepted, property_type, customer_type) |
| `services/google_sheets_poller.py` | Builds column map from header row, passes to service, fetches all sheet columns (removed A:T limit), diagnostic logging, headers in sync status |
| `models/google_sheet_submission.py` | Added `zip_code`, `work_requested`, `agreed_to_terms` model columns |
| `schemas/google_sheet_submission.py` | Added 3 new fields to API response + `detected_headers`/`column_map` in sync status |
| `tests/conftest.py` | Added new fields to sample submission fixture |
| `tests/unit/test_google_sheets_property.py` | Updated mock signatures for `col_map` param + new fields |

### Files Added

| File | Purpose |
|------|---------|
| `migrations/versions/20260403_100000_add_submission_new_form_fields.py` | DB migration for 3 new columns |
| `scripts/diagnose_google_sheet.py` | Diagnostic tool — connects to sheet, prints headers and column mapping |
| `to_do/ASAP.md` | ASAP fixes tracking checklist |

---

## 3. No Environment Variable Changes

No new environment variables are required. The existing Google Sheets configuration continues to work:
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_SHEET_NAME` (should be `1. Job Requests`)
- `GOOGLE_SHEETS_POLL_INTERVAL_SECONDS`
- `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` or `GOOGLE_SERVICE_ACCOUNT_KEY_JSON`

---

## 4. Post-Deployment Verification

### Step 1: Verify migration ran

Check Railway deploy logs for:
```
Running upgrade 20260328_110000 -> 20260403_100000, Add zip_code, work_requested, agreed_to_terms
```

### Step 2: Verify poller detects headers

Check deploy logs for:
```
header_count=29 mapped_fields=[...] event="poller.headers_detected"
```

Confirm `mapped_fields` includes: `name`, `phone`, `email`, `address`, `city`, `zip_code`, `work_requested`, `agreed_to_terms`, `date_work_needed_by`, `additional_services_info`

### Step 3: Verify sync status endpoint

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  https://<API_URL>/api/v1/sheet-submissions/sync-status
```

Response should include `detected_headers` (29 items) and `column_map` with all critical fields mapped to the new columns (T-AC):
- `name` → index 19 (column T)
- `phone` → index 23 (column X)
- `email` → index 24 (column Y)
- `address` → index 20 (column U)
- `city` → index 21 (column V)
- `zip_code` → index 22 (column W)

### Step 4: Submit a test form

1. Submit the Google Form with test data
2. Wait 60 seconds (one poll cycle)
3. Check the Leads tab — the new lead should have:
   - Correct name, phone, email, address, city, zip code
   - Situation mapped from "Work Requested" selection
   - Notes containing work requested type, zip code, and terms agreement
   - `source_site` = "google_sheets"
   - `lead_source` = "google_form"

### Step 5: Run diagnostic script (optional)

```bash
python scripts/diagnose_google_sheet.py
```

Prints the full header mapping and a sample data row (with PII redacted).

---

## 5. Rollback Plan

If issues arise:

1. **Code rollback**: Revert to previous deployment in Railway
2. **Migration rollback**: `uv run alembic downgrade 20260328_110000` (drops the 3 new columns)
3. The old positional mapping (`remap_sheet_row`) is still in the code as fallback when no header row is detected

---

## 6. Key Technical Details

### Why the old mapping was broken

The Google Sheet has **29 columns** (A-AC), but the old code:
- Fetched only columns A-T (20 columns), missing 9 columns entirely
- Used hardcoded positional indices (name=9, phone=10, etc.)
- The Google Form was restructured — new submissions put data in columns T-AC, not B-Q
- Result: name field read from empty old column → "Unknown", phone → "0000000000"

### How the new mapping works

1. **Header-based**: Reads the header row and matches column names to fields using keyword patterns
2. **Last-match-wins**: When duplicate columns exist (old B-Q + new T-AC), the newer columns take priority
3. **All columns fetched**: No column range limit — discovers fields regardless of sheet size
4. **Extra fields**: `zip_code`, `work_requested`, `agreed_to_terms` extracted from raw row and stored in both submissions table and lead notes
5. **Full lead population**: Now passes `address`, `city`, `zip_code`, `terms_accepted`, `property_type`, `customer_type` to lead creation (previously only name, phone, email, situation, notes)
