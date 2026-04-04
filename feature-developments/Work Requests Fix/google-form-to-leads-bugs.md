# Google Form to Leads — Bug Investigation Report

**Date:** 2026-03-31
**Branch:** feature-ai-scheduling
**Symptom:** Work requests from Google Form aren't routing correctly to leads; "unknown contact" appears in the system.

---

## Pipeline Overview

```
Google Form (external)
    |
    v
Google Sheet "1. Job Requests"
    |  (polled every 60s via service account JWT)
    v
GoogleSheetsPoller._execute_poll_cycle()
    |  (fetches rows A:T, detects header, finds new rows by max row_number)
    v
GoogleSheetsService.process_row()
    |  (remaps 20 cols -> 18, normalizes phone/name, checks for duplicate lead)
    v
Lead record created (or linked to existing lead by phone)
```

**Key files:**
- `src/grins_platform/services/google_sheets_poller.py` — polling loop, auth, row fetching
- `src/grins_platform/services/google_sheets_service.py` — row processing, lead creation
- `src/grins_platform/repositories/lead_repository.py` — duplicate detection queries
- `src/grins_platform/repositories/google_sheet_submission_repository.py` — submission storage
- `src/grins_platform/services/lead_service.py` — lead submission, conversion, migration

---

## Bug 1 — Phone Fallback Creates a "Black Hole" Lead (CRITICAL)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 324-335

**What happens:**
When a phone number is missing or can't be parsed to 10 digits, `safe_normalize_phone()` returns the fallback `"0000000000"`.

```python
@staticmethod
def safe_normalize_phone(raw_phone: str) -> str:
    if not raw_phone or not raw_phone.strip():
        return "0000000000"
    try:
        return normalize_phone(raw_phone)
    except ValueError:
        return "0000000000"
```

The duplicate detection (`get_by_phone_and_active_status`) then matches ALL bad-phone submissions to the SAME lead:

1. First submission with bad/missing phone -> creates lead with `phone="0000000000"` and `name="Unknown"`
2. Every subsequent submission with a bad phone -> links to that same lead (line 108)
3. Result: one "Unknown" lead accumulating unrelated work requests

**This is the most likely cause of the "unknown contact" issue.**

**Fix direction:** Reject or flag submissions with invalid phones instead of silently assigning a dummy value. Create separate leads for each rather than funneling into one.

---

## Bug 2 — Column Mapping May Be Stale (CRITICAL)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 338-351

The `remap_sheet_row()` function hardcodes a 20-column (A-T) layout and skips columns R (Score) and S (Email duplicate):

```python
def remap_sheet_row(raw_row: list[str]) -> list[str]:
    padded = raw_row + [""] * max(0, _SHEET_COLUMNS - len(raw_row))
    result = padded[:17]  # A-Q unchanged (indices 0-16)
    result.append(padded[19] if len(padded) > 19 else "")  # T -> internal 17
    return result
```

**Expected column layout:**
| Index | Column | Field |
|-------|--------|-------|
| 0 | A | Timestamp |
| 1 | B | Spring Startup |
| 2 | C | Fall Blowout |
| 3 | D | Summer Tuneup |
| 4 | E | Repair Existing |
| 5 | F | New System Install |
| 6 | G | Addition to System |
| 7 | H | Additional Services Info |
| 8 | I | Date Work Needed By |
| 9 | J | Name |
| 10 | K | Phone |
| 11 | L | Email |
| 12 | M | City |
| 13 | N | Address |
| 14 | O | Client Type |
| 15 | P | Property Type |
| 16 | Q | Referral Source |
| -- | R | Score (SKIPPED) |
| -- | S | Email duplicate (SKIPPED) |
| 17 | T | Landscape/Hardscape |

**Problem:** If ANY column has been added, removed, or reordered in the Google Form/Sheet since this mapping was written, all fields silently shift. Name (index 9) could receive a service checkbox value. Phone (index 10) could receive a city name. This would produce leads with wrong data, "Unknown" names, and "0000000000" phones.

**Verification needed:** Open the actual Google Sheet (ID: `1fXEy7rkSGDTXosvrDPCGUngttHHINPz859pEbN0pYN0`, tab "1. Job Requests") and compare columns A-T against the table above.

---

## Bug 3 — `process_row()` Drops City and Address (HIGH)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 117-128

The auto-promotion path does NOT pass `city`, `address`, or `property_type` to the Lead:

```python
lead = await lead_repo.create(
    name=self.normalize_name(padded[9]),
    phone=phone,
    email=padded[11].strip() or None,
    zip_code=None,
    situation=self.map_situation(padded).value,
    notes=self.aggregate_notes(padded) or None,
    source_site="google_sheets",
    lead_source=LeadSourceExtended.GOOGLE_FORM.value,
    source_detail=source_detail,
    intake_tag=IntakeTag.SCHEDULE.value,
    # MISSING: city=padded[12], address=padded[13], property_type=padded[15]
)
```

Compare with `migrate_work_requests()` (lead_service.py, line 1381) which DOES pass `city`, `address`, and `state`. This inconsistency means auto-created leads are missing location data.

**Fix direction:** Add `city`, `address`, and `property_type` to the `lead_repo.create()` call in `process_row()`.

---

## Bug 4 — Existing Clients Not Matched to Customer Records (HIGH)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 99-135

When someone selects "existing client" on the form, the code only sets `source_detail = "Existing client work request"`. It does NOT:

- Look up the customer by phone in the `customers` table
- Set `customer_id` on the Lead
- Match against existing service agreements or job history

Result: existing customer work requests appear as disconnected leads with no link to their customer profile. The admin sees a lead that should obviously map to a known customer but doesn't — contributing to the "unknown contact" perception.

**Fix direction:** After creating/finding the lead, query `CustomerRepository.find_by_phone()` and if found, set `lead.customer_id` to link them.

---

## Bug 5 — Service Account Permissions Fail Silently (MEDIUM)

**File:** `src/grins_platform/services/google_sheets_poller.py`, lines 330-340

If the service account (`grins-work-request-reader@grins-irrigation.iam.gserviceaccount.com`) loses access to the sheet:

```python
if resp.status_code == 403:
    msg = "Sheet not shared with service account..."
    logger.error("poller.fetch_forbidden", message=msg)
    self._last_error = msg
    return []  # <-- silently returns empty, poller keeps running
```

- A 403 is logged but the poller continues running every 60 seconds
- It silently fetches nothing — no leads are created
- No alerts, no emails, no escalation

**Verification:** Check `GET /api/v1/sheet-submissions/sync-status`. If `last_error` contains "Sheet not shared with service account", this is an active problem.

**Service account email:** `grins-work-request-reader@grins-irrigation.iam.gserviceaccount.com`
**Sheet must be shared with this email as Viewer.**

---

## Bug 6 — Row Number Tracking Is Fragile (MEDIUM)

**File:** `src/grins_platform/services/google_sheets_poller.py`, lines 257-295

The poller determines "new" rows by comparing `row_number > max_row` where `max_row` is the highest `sheet_row_number` stored in the DB. Row numbers are derived from array position, not a unique ID.

```python
max_row = await sub_repo.get_max_row_number()
for i, row_data in enumerate(rows[start_idx:], start=start_idx + 1):
    row_number = i + 1  # Note: +1 historical offset
    if row_number <= max_row:
        continue
```

**Problems:**
- If rows are **deleted** from the sheet: subsequent rows shift up, their new row numbers are <= max_row, so they are **permanently skipped**
- If rows are **inserted** above existing data: subsequent rows shift down, could cause reprocessing (caught by IntegrityError but wasteful)
- There's a consistent +1 offset noted as "historical" — row numbers in DB are 1 higher than actual sheet positions

**Fix direction:** Use a content-based dedup key (e.g., hash of timestamp + name + phone) rather than positional row numbers.

---

## Bug 7 — `client_type` Matching Is Overly Strict (MEDIUM)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 99-100

```python
client_type = (padded[14].strip().lower()) if padded[14] else ""
is_new = client_type == "new"
```

This only matches the exact string `"new"`. If the Google Form option is phrased differently:
- "New Client" -> NOT matched (treated as existing)
- "New Customer" -> NOT matched
- "I'm a new client" -> NOT matched

Any non-exact match defaults to `"Existing client work request"`, misclassifying new clients.

**Fix direction:** Use `"new" in client_type` or match against a list of known values.

---

## Bug 8 — Name Fallback "Unknown" Pollutes Lead Data (LOW)

**File:** `src/grins_platform/services/google_sheets_service.py`, lines 318-321

```python
@staticmethod
def normalize_name(raw_name: str) -> str:
    stripped = raw_name.strip() if raw_name else ""
    return stripped if stripped else "Unknown"
```

Empty names silently become `"Unknown"`. Combined with Bug 1 (phone fallback to "0000000000"), this creates leads that are literally `name="Unknown", phone="0000000000"` — and multiple unrelated submissions pile onto this one record.

**Fix direction:** Flag these as needing review rather than silently assigning placeholder values.

---

## Bug 9 — No Alerting for Persistent Poller Failures (LOW)

If the poller fails repeatedly (auth errors, network issues, sheet access revoked), `_last_error` is updated on the status endpoint but there's no active escalation:
- No email or SMS alert to the admin
- No Slack notification
- No automatic backoff beyond the fixed 60-second interval
- The admin would only notice if they manually check `/sync-status` or notice leads stopped appearing

---

## Verification Checklist

Before implementing fixes, verify these manually:

1. [ ] **Open the Google Sheet** (ID: `1fXEy7rkSGDTXosvrDPCGUngttHHINPz859pEbN0pYN0`, tab "1. Job Requests") and confirm columns A-T match the expected layout in Bug 2
2. [ ] **Check sync status** — Hit `GET /api/v1/sheet-submissions/sync-status` and look for errors
3. [ ] **Query the DB** — Look for leads with `phone = '0000000000'` or `name = 'Unknown'` to quantify impact
4. [ ] **Verify sheet sharing** — Confirm the sheet is shared with `grins-work-request-reader@grins-irrigation.iam.gserviceaccount.com` as Viewer
5. [ ] **Check the Google Form** — Verify what the `client_type` field options actually say (exact strings)
6. [ ] **Review recent submissions** — Compare a few recent Google Sheet rows against the corresponding `google_sheet_submissions` DB records to see if data is landing in the right fields

---

## Environment Details

- **Spreadsheet ID:** `1fXEy7rkSGDTXosvrDPCGUngttHHINPz859pEbN0pYN0`
- **Sheet Tab:** `1. Job Requests`
- **Service Account:** `grins-work-request-reader@grins-irrigation.iam.gserviceaccount.com`
- **Key File:** `./grins-irrigation-ec7fd07165a5.json`
- **Poll Interval:** 60 seconds
- **Service Account Project:** `grins-irrigation`
