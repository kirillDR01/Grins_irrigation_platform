 Phase 13: Google Sheets Retrieval Integration                                                                                                          │
│                                                                                                                                                        │
│ Overview                                                                                                                                               │
│                                                                                                                                                        │
│ Phase 13 implements an automated Google Sheets polling system that monitors a Google Form-linked spreadsheet for new service request submissions. The  │
│ system stores all submissions in a dedicated database table and auto-creates Lead records for new client submissions only.                             │
│                                                                                                                                                        │
│ Delivery: This plan will be saved as Markdown/PHASE-13-PLANNING.md and a companion docs/google_sheets_retrieval.md research doc.                       │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Context & Problem Statement                                                                                                                            │
│                                                                                                                                                        │
│ The Grins Irrigation Platform currently collects leads via a public web form (POST /api/v1/leads). However, the business also receives service         │
│ requests through a Google Form that populates a Google Sheet. Today this sheet is checked manually — there is no automated pipeline to bring these     │
│ submissions into the platform.                                                                                                                         │
│                                                                                                                                                        │
│ Goal: Automatically poll the Google Sheet, store all submissions, and create Lead records for new clients so they enter the existing lead management   │
│ pipeline (new → contacted → qualified → converted).                                                                                                    │
│                                                                                                                                                        │
│ Approach: Background asyncio polling task inside the FastAPI lifespan, using httpx to call Google Sheets API v4 directly (matching the existing        │
│ TravelTimeService pattern for Google Maps API). Service account JWT authentication. No new infrastructure required — runs inside the existing FastAPI  │
│ process.                                                                                                                                               │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Google Sheet Column Structure (19 Columns)                                                                                                             │
│                                                                                                                                                        │
│ The Google Form populates a sheet with the following columns:                                                                                          │
│                                                                                                                                                        │
│ ┌─────┬───────────────────────┬──────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────┐     │
│ │  #  │ Sheet Column (Letter) │        Field Name        │                              Data Type / Possible Values                              │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 1   │ A                     │ timestamp                │ Date string, e.g. "3/4/2026 12:01:41"                                                 │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 2   │ B                     │ spring_startup           │ "requesting once" / "requesting yearly service" / empty                               │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 3   │ C                     │ fall_blowout             │ same as above                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 4   │ D                     │ summer_tuneup            │ same as above                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 5   │ E                     │ repair_existing          │ same as above                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 6   │ F                     │ new_system_install       │ same as above                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 7   │ G                     │ addition_to_system       │ same as above                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 8   │ H                     │ additional_services_info │ Free text (1-2 sentences) — "If requesting services not listed above, please specify" │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 9   │ I                     │ date_work_needed_by      │ Date string, e.g. "5/1/2026"                                                          │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 10  │ J                     │ name                     │ First and last name, e.g. "John Doe"                                                  │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 11  │ K                     │ phone                    │ Phone number                                                                          │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 12  │ L                     │ email                    │ Email address                                                                         │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 13  │ M                     │ city                     │ City name                                                                             │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 14  │ N                     │ address                  │ Street address                                                                        │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 15  │ O                     │ additional_info          │ Free text — additional info between address and client type                           │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 16  │ P                     │ client_type              │ "new" or "existing"                                                                   │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 17  │ Q                     │ property_type            │ "residential" / "commercial" / "other"                                                │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 18  │ R                     │ referral_source          │ Free text — "How did you hear about us?"                                              │     │
│ ├─────┼───────────────────────┼──────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────┤     │
│ │ 19  │ S                     │ landscape_hardscape      │ Free text — landscape/hardscape work if requested                                     │     │
│ └─────┴───────────────────────┴──────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                                                                                        │
│ Service Columns (2-7) Detail                                                                                                                           │
│                                                                                                                                                        │
│ Columns 2-7 represent specific irrigation services. Each can be:                                                                                       │
│ - Empty — not requesting this service                                                                                                                  │
│ - "requesting once" — one-time service request                                                                                                         │
│ - "requesting yearly service" — recurring annual service                                                                                               │
│                                                                                                                                                        │
│ ┌────────┬─────────────────────────────────────┬───────────────────────┐                                                                               │
│ │ Column │               Service               │ Maps to LeadSituation │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ B      │ Spring System Start Up & Adjustment │ exploring (seasonal)  │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ C      │ Fall System Blow Out/Winterization  │ exploring (seasonal)  │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ D      │ Summer System Tune Up & Adjustment  │ exploring (seasonal)  │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ E      │ Repair to Existing System           │ repair                │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ F      │ New System Installation             │ new_system            │                                                                               │
│ ├────────┼─────────────────────────────────────┼───────────────────────┤                                                                               │
│ │ G      │ Addition to Existing System         │ upgrade               │                                                                               │
│ └────────┴─────────────────────────────────────┴───────────────────────┘                                                                               │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Architecture                                                                                                                                           │
│                                                                                                                                                        │
│ ┌─────────────────────────────────────────────────────────────────────┐                                                                                │
│ │                     GOOGLE SHEETS POLLING FLOW                       │                                                                               │
│ │                                                                      │                                                                               │
│ │  Google Form → Google Sheet (19 columns)                             │                                                                               │
│ │                     │                                                │                                                                               │
│ │                     │ (polled every 60s)                              │                                                                              │
│ │                     ▼                                                │                                                                               │
│ │  ┌──────────────────────────────────────────────────┐                │                                                                               │
│ │  │  GoogleSheetsService.poll_loop()                  │                │                                                                              │
│ │  │  (asyncio background task in FastAPI lifespan)    │                │                                                                              │
│ │  │                                                    │                │                                                                             │
│ │  │  1. Authenticate (service account JWT → token)    │                │                                                                              │
│ │  │  2. GET Sheets API v4 /values/A:S                 │                │                                                                              │
│ │  │  3. Compare row count with last imported row      │                │                                                                              │
│ │  │  4. For each new row:                             │                │                                                                              │
│ │  │     a. Store in google_sheet_submissions table    │                │                                                                              │
│ │  │     b. If client_type == "new":                   │                │                                                                              │
│ │  │        → Create Lead (status: "new")              │                │                                                                              │
│ │  │        → Link lead_id to submission               │                │                                                                              │
│ │  │     c. If client_type == "existing":              │                │                                                                              │
│ │  │        → Mark as "skipped" (no lead created)      │                │                                                                              │
│ │  └──────────────────────────────────────────────────┘                │                                                                               │
│ │                     │                                                │                                                                               │
│ │                     ▼                                                │                                                                               │
│ │  ┌──────────────────────────────────────────────────┐                │                                                                               │
│ │  │  Database Tables                                   │                │                                                                             │
│ │  │                                                    │                │                                                                             │
│ │  │  google_sheet_submissions (new)                   │                │                                                                              │
│ │  │  ├── All 19 columns stored as raw strings         │                │                                                                              │
│ │  │  ├── sheet_row_number (unique, dedup key)         │                │                                                                              │
│ │  │  ├── processing_status (imported/lead_created/    │                │                                                                              │
│ │  │  │                      skipped/error)            │                │                                                                              │
│ │  │  └── lead_id (FK → leads, if created)             │                │                                                                              │
│ │  │                                                    │                │                                                                             │
│ │  │  leads (existing)                                  │                │                                                                             │
│ │  │  └── New leads with source_site="google_sheets"   │                │                                                                              │
│ │  └──────────────────────────────────────────────────┘                │                                                                               │
│ │                                                                      │                                                                               │
│ │  ┌──────────────────────────────────────────────────┐                │                                                                               │
│ │  │  Admin API Endpoints                               │                │                                                                             │
│ │  │                                                    │                │                                                                             │
│ │  │  GET  /api/v1/sheet-submissions         (list)    │                │                                                                              │
│ │  │  GET  /api/v1/sheet-submissions/{id}    (detail)  │                │                                                                              │
│ │  │  GET  /api/v1/sheet-submissions/sync-status       │                │                                                                              │
│ │  │  POST /api/v1/sheet-submissions/{id}/create-lead  │                │                                                                              │
│ │  │  POST /api/v1/sheet-submissions/trigger-sync      │                │                                                                              │
│ │  └──────────────────────────────────────────────────┘                │                                                                               │
│ └─────────────────────────────────────────────────────────────────────┘                                                                                │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Google Sheets API v4 — Technical Details                                                                                                               │
│                                                                                                                                                        │
│ Authentication: Service Account JWT Flow                                                                                                               │
│                                                                                                                                                        │
│ The platform uses a Google Cloud service account for server-to-server authentication. No user interaction required.                                    │
│                                                                                                                                                        │
│ ┌─────────────────────────────────────────────────────┐                                                                                                │
│ │  SERVICE ACCOUNT AUTHENTICATION FLOW                 │                                                                                               │
│ │                                                      │                                                                                               │
│ │  1. Load service-account-key.json                    │                                                                                               │
│ │     (contains client_email, private_key, token_uri)  │                                                                                               │
│ │                                                      │                                                                                               │
│ │  2. Create JWT (signed with RS256):                  │                                                                                               │
│ │     {                                                │                                                                                               │
│ │       "iss": "sa@project.iam.gserviceaccount.com",   │                                                                                               │
│ │       "scope": "spreadsheets.readonly",              │                                                                                               │
│ │       "aud": "https://oauth2.googleapis.com/token",  │                                                                                               │
│ │       "iat": now,                                    │                                                                                               │
│ │       "exp": now + 3600                              │                                                                                               │
│ │     }                                                │                                                                                               │
│ │                                                      │                                                                                               │
│ │  3. POST https://oauth2.googleapis.com/token         │                                                                                               │
│ │     grant_type=jwt-bearer, assertion=<signed_jwt>    │                                                                                               │
│ │                                                      │                                                                                               │
│ │  4. Receive access_token (valid ~3600s)              │                                                                                               │
│ │     Cache until near expiry (refresh at 3500s)       │                                                                                               │
│ │                                                      │                                                                                               │
│ │  5. Use token in API calls:                          │                                                                                               │
│ │     Authorization: Bearer <access_token>             │                                                                                               │
│ └─────────────────────────────────────────────────────┘                                                                                                │
│                                                                                                                                                        │
│ Dependency note: python-jose[cryptography] is already installed (used for auth JWTs). It supports RS256, so no new dependency needed for JWT signing.  │
│                                                                                                                                                        │
│ API Endpoint Used                                                                                                                                      │
│                                                                                                                                                        │
│ GET https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}                                                                       │
│                                                                                                                                                        │
│ Headers:                                                                                                                                               │
│   Authorization: Bearer {access_token}                                                                                                                 │
│                                                                                                                                                        │
│ Response (ValueRange):                                                                                                                                 │
│ {                                                                                                                                                      │
│   "range": "Form Responses 1!A1:S100",                                                                                                                 │
│   "majorDimension": "ROWS",                                                                                                                            │
│   "values": [                                                                                                                                          │
│     ["Timestamp", "Spring...", ...],           // Row 1: headers                                                                                       │
│     ["3/4/2026 12:01:41", "requesting once", ...],  // Row 2: first submission                                                                         │
│     ["3/4/2026 14:30:00", "", ...],            // Row 3: second submission                                                                             │
│     ...                                                                                                                                                │
│   ]                                                                                                                                                    │
│ }                                                                                                                                                      │
│                                                                                                                                                        │
│ Key behaviors:                                                                                                                                         │
│ - The API omits trailing empty cells in each row (rows may have different lengths)                                                                     │
│ - Empty rows at the end are omitted entirely                                                                                                           │
│ - The values array length = total populated rows (including header)                                                                                    │
│                                                                                                                                                        │
│ Rate Limits                                                                                                                                            │
│                                                                                                                                                        │
│ ┌──────────────────────────────────────┬─────────────┐                                                                                                 │
│ │                Limit                 │    Value    │                                                                                                 │
│ ├──────────────────────────────────────┼─────────────┤                                                                                                 │
│ │ Read requests per minute per project │ 300         │                                                                                                 │
│ ├──────────────────────────────────────┼─────────────┤                                                                                                 │
│ │ Read requests per minute per user    │ 60          │                                                                                                 │
│ ├──────────────────────────────────────┼─────────────┤                                                                                                 │
│ │ Request timeout                      │ 180 seconds │                                                                                                 │
│ ├──────────────────────────────────────┼─────────────┤                                                                                                 │
│ │ Cost                                 │ Free        │                                                                                                 │
│ └──────────────────────────────────────┴─────────────┘                                                                                                 │
│                                                                                                                                                        │
│ At 60-second poll intervals = 1 request/minute = well within limits.                                                                                   │
│                                                                                                                                                        │
│ Google Cloud Setup (Manual, One-Time)                                                                                                                  │
│                                                                                                                                                        │
│ 1. Go to Google Cloud Console                                                                                                                          │
│ 2. Create a project (or use existing)                                                                                                                  │
│ 3. Enable Google Sheets API (APIs & Services → Library)                                                                                                │
│ 4. Create a Service Account (IAM & Admin → Service Accounts)                                                                                           │
│ 5. Create a key for the service account (JSON format) → downloads service-account-key.json                                                             │
│ 6. Share the Google Sheet with the service account email (e.g., grins-sheets@my-project.iam.gserviceaccount.com) as Viewer                             │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Database Design                                                                                                                                        │
│                                                                                                                                                        │
│ New Table: google_sheet_submissions                                                                                                                    │
│                                                                                                                                                        │
│ CREATE TABLE google_sheet_submissions (                                                                                                                │
│     -- Primary Key & Metadata                                                                                                                          │
│     id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),                                                                                │
│     sheet_row_number        INTEGER NOT NULL UNIQUE,     -- Dedup key (row 2 = first data row)                                                         │
│     imported_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),                                                                                        │
│                                                                                                                                                        │
│     -- Raw Sheet Data (19 columns, all nullable strings)                                                                                               │
│     submission_timestamp    VARCHAR(50),                  -- Col A                                                                                     │
│     spring_startup          VARCHAR(50),                  -- Col B                                                                                     │
│     fall_blowout            VARCHAR(50),                  -- Col C                                                                                     │
│     summer_tuneup           VARCHAR(50),                  -- Col D                                                                                     │
│     repair_existing         VARCHAR(50),                  -- Col E                                                                                     │
│     new_system_install      VARCHAR(50),                  -- Col F                                                                                     │
│     addition_to_system      VARCHAR(50),                  -- Col G                                                                                     │
│     additional_services_info TEXT,                        -- Col H                                                                                     │
│     date_work_needed_by     VARCHAR(50),                  -- Col I                                                                                     │
│     name                    VARCHAR(200),                 -- Col J                                                                                     │
│     phone                   VARCHAR(20),                  -- Col K                                                                                     │
│     email                   VARCHAR(255),                 -- Col L                                                                                     │
│     city                    VARCHAR(100),                 -- Col M                                                                                     │
│     address                 VARCHAR(255),                 -- Col N                                                                                     │
│     additional_info         TEXT,                         -- Col O                                                                                     │
│     client_type             VARCHAR(20),                  -- Col P: "new" / "existing"                                                                 │
│     property_type           VARCHAR(20),                  -- Col Q: "residential" / "commercial" / "other"                                             │
│     referral_source         VARCHAR(255),                 -- Col R                                                                                     │
│     landscape_hardscape     TEXT,                         -- Col S                                                                                     │
│                                                                                                                                                        │
│     -- Processing Tracking                                                                                                                             │
│     lead_id                 UUID REFERENCES leads(id),    -- FK if lead was created                                                                    │
│     processing_status       VARCHAR(20) NOT NULL DEFAULT 'imported',                                                                                   │
│                             -- Values: imported, lead_created, skipped, error                                                                          │
│     processing_error        TEXT,                         -- Error message if processing failed                                                        │
│     created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()                                                                                         │
│ );                                                                                                                                                     │
│                                                                                                                                                        │
│ -- Indexes                                                                                                                                             │
│ CREATE INDEX idx_gsheet_sub_client_type ON google_sheet_submissions (client_type);                                                                     │
│ CREATE INDEX idx_gsheet_sub_status ON google_sheet_submissions (processing_status);                                                                    │
│ CREATE INDEX idx_gsheet_sub_imported_at ON google_sheet_submissions (imported_at);                                                                     │
│                                                                                                                                                        │
│ Design decisions:                                                                                                                                      │
│ - sheet_row_number with UNIQUE constraint prevents re-importing the same row                                                                           │
│ - All 19 sheet columns stored as raw strings (no data transformation at storage layer)                                                                 │
│ - processing_status tracks the outcome: imported (initial), lead_created, skipped (existing client), error                                             │
│ - lead_id FK links back to the auto-created lead (null if existing client or error)                                                                    │
│                                                                                                                                                        │
│ Schema Change: Make leads.zip_code Nullable                                                                                                            │
│                                                                                                                                                        │
│ The Google Sheet has city + address but no zip code. The current Lead model requires zip_code NOT NULL. This needs to change:                          │
│                                                                                                                                                        │
│ ALTER TABLE leads ALTER COLUMN zip_code DROP NOT NULL;                                                                                                 │
│                                                                                                                                                        │
│ Impact: The public form submission (POST /api/v1/leads) still validates zip_code via the LeadSubmission Pydantic schema. Only the internal lead        │
│ creation path from sheets will set zip_code=NULL.                                                                                                      │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Business Logic                                                                                                                                         │
│                                                                                                                                                        │
│ Lead Creation Rules                                                                                                                                    │
│                                                                                                                                                        │
│ For each new sheet row:                                                                                                                                │
│   1. Store raw data in google_sheet_submissions (always)                                                                                               │
│   2. Check client_type column:                                                                                                                         │
│      - If "new" (case-insensitive, trimmed):                                                                                                           │
│        a. Normalize phone number (reuse existing normalize_phone())                                                                                    │
│        b. Check for duplicate lead by phone + active status                                                                                            │
│           - If duplicate exists: link submission to existing lead, mark "lead_created"                                                                 │
│           - If no duplicate: create new Lead, link submission, mark "lead_created"                                                                     │
│      - If "existing" or anything else:                                                                                                                 │
│        → Mark as "skipped" (existing clients are already in the system)                                                                                │
│   3. If any error during lead creation:                                                                                                                │
│      → Mark as "error", store error message, continue to next row                                                                                      │
│                                                                                                                                                        │
│ Situation Mapping (Service Columns → LeadSituation Enum)                                                                                               │
│                                                                                                                                                        │
│ Priority order (first match wins):                                                                                                                     │
│                                                                                                                                                        │
│ ┌──────────┬──────────────────────────────┬───────────────┬──────────────────────────────────┐                                                         │
│ │ Priority │        Service Column        │ LeadSituation │            Rationale             │                                                         │
│ ├──────────┼──────────────────────────────┼───────────────┼──────────────────────────────────┤                                                         │
│ │ 1        │ new_system_install (Col F)   │ new_system    │ Direct match                     │                                                         │
│ ├──────────┼──────────────────────────────┼───────────────┼──────────────────────────────────┤                                                         │
│ │ 2        │ addition_to_system (Col G)   │ upgrade       │ Adding to existing = upgrade     │                                                         │
│ ├──────────┼──────────────────────────────┼───────────────┼──────────────────────────────────┤                                                         │
│ │ 3        │ repair_existing (Col E)      │ repair        │ Direct match                     │                                                         │
│ ├──────────┼──────────────────────────────┼───────────────┼──────────────────────────────────┤                                                         │
│ │ 4        │ Any seasonal service (B/C/D) │ exploring     │ Seasonal maintenance = exploring │                                                         │
│ ├──────────┼──────────────────────────────┼───────────────┼──────────────────────────────────┤                                                         │
│ │ 5        │ None selected                │ exploring     │ Default fallback                 │                                                         │
│ └──────────┴──────────────────────────────┴───────────────┴──────────────────────────────────┘                                                         │
│                                                                                                                                                        │
│ Notes Aggregation                                                                                                                                      │
│                                                                                                                                                        │
│ All relevant sheet data is combined into the Lead's notes field:                                                                                       │
│                                                                                                                                                        │
│ Spring Start Up: requesting yearly service                                                                                                             │
│ Fall Blow Out: requesting once                                                                                                                         │
│ Needed by: 5/1/2026                                                                                                                                    │
│ Additional: Customer wants backflow preventer checked                                                                                                  │
│ City: Minneapolis                                                                                                                                      │
│ Address: 123 Oak Street                                                                                                                                │
│ Landscape/Hardscape: Paver patio installation                                                                                                          │
│ Referral: Google search                                                                                                                                │
│                                                                                                                                                        │
│ Lead Field Mapping                                                                                                                                     │
│                                                                                                                                                        │
│ ┌─────────────┬────────────────────┬──────────────────────────────────────┐                                                                            │
│ │ Lead Field  │       Source       │                Notes                 │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ name        │ Col J (name)       │ Used as-is                           │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ phone       │ Col K (phone)      │ Normalized via normalize_phone()     │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ email       │ Col L (email)      │ Used as-is, null if empty            │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ zip_code    │ —                  │ Set to NULL (not available in sheet) │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ situation   │ Cols B-G           │ Mapped via priority table above      │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ notes       │ Cols B-I, M-O, R-S │ Aggregated text (see above)          │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ source_site │ Hardcoded          │ "google_sheets"                      │                                                                            │
│ ├─────────────┼────────────────────┼──────────────────────────────────────┤                                                                            │
│ │ status      │ Hardcoded          │ "new"                                │                                                                            │
│ └─────────────┴────────────────────┴──────────────────────────────────────┘                                                                            │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Files to Create                                                                                                                                        │
│                                                                                                                                                        │
│ ┌─────┬───────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────────┐            │
│ │  #  │                                           File                                            │                Purpose                │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 1   │ src/grins_platform/migrations/versions/20260304_100000_create_google_sheet_submissions.py │ Migration: new table                  │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 2   │ src/grins_platform/migrations/versions/20260304_100100_make_lead_zip_code_nullable.py     │ Migration: zip_code nullable          │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 3   │ src/grins_platform/models/google_sheet_submission.py                                      │ SQLAlchemy model                      │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 4   │ src/grins_platform/schemas/google_sheet_submission.py                                     │ Pydantic schemas                      │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 5   │ src/grins_platform/repositories/google_sheet_submission_repository.py                     │ Data access layer                     │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 6   │ src/grins_platform/services/google_sheets_service.py                                      │ API client + polling + lead creation  │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 7   │ src/grins_platform/api/v1/google_sheet_submissions.py                                     │ Admin API endpoints                   │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 8   │ src/grins_platform/tests/unit/test_google_sheets_service.py                               │ Service unit tests                    │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 9   │ src/grins_platform/tests/unit/test_google_sheet_submission_schemas.py                     │ Schema tests                          │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 10  │ src/grins_platform/tests/unit/test_google_sheet_submission_api.py                         │ API endpoint tests                    │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 11  │ src/grins_platform/tests/integration/test_google_sheets_integration.py                    │ Integration tests                     │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 12  │ Markdown/PHASE-13-PLANNING.md                                                             │ This planning document                │            │
│ ├─────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────┤            │
│ │ 13  │ docs/google_sheets_retrieval.md                                                           │ Research & architecture reference doc │            │
│ └─────┴───────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────────┘            │
│                                                                                                                                                        │
│ Files to Modify                                                                                                                                        │
│                                                                                                                                                        │
│ ┌─────┬───────────────────────────────────────────┬─────────────────────────────────────────────────┐                                                  │
│ │  #  │                   File                    │                     Change                      │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 1   │ src/grins_platform/app.py                 │ Add polling task to lifespan (startup/shutdown) │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 2   │ src/grins_platform/api/v1/router.py       │ Include new sheet-submissions router            │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 3   │ src/grins_platform/api/v1/dependencies.py │ Add DI for new repository                       │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 4   │ src/grins_platform/models/lead.py         │ Make zip_code nullable                          │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 5   │ src/grins_platform/schemas/lead.py        │ Allow zip_code=None in LeadResponse             │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 6   │ .env                                      │ Add Google Sheets config variables              │                                                  │
│ ├─────┼───────────────────────────────────────────┼─────────────────────────────────────────────────┤                                                  │
│ │ 7   │ pyproject.toml                            │ No changes needed (all deps already present)    │                                                  │
│ └─────┴───────────────────────────────────────────┴─────────────────────────────────────────────────┘                                                  │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Implementation Steps (Detailed)                                                                                                                        │
│                                                                                                                                                        │
│ Step 1: Environment Variables                                                                                                                          │
│                                                                                                                                                        │
│ Add to .env:                                                                                                                                           │
│ # Google Sheets Integration                                                                                                                            │
│ GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here                                                                                                  │
│ GOOGLE_SHEETS_SHEET_NAME=Form Responses 1                                                                                                              │
│ GOOGLE_SHEETS_POLL_INTERVAL_SECONDS=60                                                                                                                 │
│ GOOGLE_SERVICE_ACCOUNT_KEY_PATH=./service-account-key.json                                                                                             │
│                                                                                                                                                        │
│ Step 2: Database Migration — google_sheet_submissions Table                                                                                            │
│                                                                                                                                                        │
│ File: src/grins_platform/migrations/versions/20260304_100000_create_google_sheet_submissions.py                                                        │
│                                                                                                                                                        │
│ Follow migration pattern from 20250628_100000_create_leads_table.py:                                                                                   │
│ - Manual revision ID                                                                                                                                   │
│ - Full upgrade() with op.create_table(), indexes                                                                                                       │
│ - Full downgrade() with op.drop_index(), op.drop_table()                                                                                               │
│                                                                                                                                                        │
│ Step 3: Database Migration — Make leads.zip_code Nullable                                                                                              │
│                                                                                                                                                        │
│ File: src/grins_platform/migrations/versions/20260304_100100_make_lead_zip_code_nullable.py                                                            │
│                                                                                                                                                        │
│ def upgrade() -> None:                                                                                                                                 │
│     op.alter_column("leads", "zip_code",                                                                                                               │
│                      existing_type=sa.String(10), nullable=True)                                                                                       │
│                                                                                                                                                        │
│ def downgrade() -> None:                                                                                                                               │
│     # Set any NULL zip_codes to "00000" before making non-nullable                                                                                     │
│     op.execute("UPDATE leads SET zip_code = '00000' WHERE zip_code IS NULL")                                                                           │
│     op.alter_column("leads", "zip_code",                                                                                                               │
│                      existing_type=sa.String(10), nullable=False)                                                                                      │
│                                                                                                                                                        │
│ Step 4: SQLAlchemy Model — GoogleSheetSubmission                                                                                                       │
│                                                                                                                                                        │
│ File: src/grins_platform/models/google_sheet_submission.py                                                                                             │
│                                                                                                                                                        │
│ Pattern: Follow models/lead.py exactly:                                                                                                                │
│ - Import from sqlalchemy, sqlalchemy.orm                                                                                                               │
│ - Inherit from Base                                                                                                                                    │
│ - UUID PK with server_default=text("gen_random_uuid()")                                                                                                │
│ - All 19 sheet columns as mapped_column(String(...), nullable=True)                                                                                    │
│ - Tracking columns: sheet_row_number, lead_id (FK), processing_status, processing_error                                                                │
│ - Timestamps: imported_at, created_at                                                                                                                  │
│ - __table_args__ with UniqueConstraint and Index definitions                                                                                           │
│ - to_dict() method                                                                                                                                     │
│                                                                                                                                                        │
│ Step 5: Update Lead Model                                                                                                                              │
│                                                                                                                                                        │
│ File: src/grins_platform/models/lead.py                                                                                                                │
│                                                                                                                                                        │
│ Change zip_code column from nullable=False to nullable=True.                                                                                           │
│                                                                                                                                                        │
│ Step 6: Pydantic Schemas                                                                                                                               │
│                                                                                                                                                        │
│ File: src/grins_platform/schemas/google_sheet_submission.py                                                                                            │
│                                                                                                                                                        │
│ Schemas to create:                                                                                                                                     │
│ - GoogleSheetSubmissionResponse — full response with all fields, ConfigDict(from_attributes=True)                                                      │
│ - GoogleSheetSubmissionListParams — pagination + filters (client_type, processing_status, search)                                                      │
│ - PaginatedGoogleSheetSubmissionResponse — paginated list                                                                                              │
│ - SyncStatusResponse — poller status (is_running, last_sync_at, total_imported, last_error)                                                            │
│                                                                                                                                                        │
│ Pattern: Follow schemas/lead.py.                                                                                                                       │
│                                                                                                                                                        │
│ Step 7: Repository                                                                                                                                     │
│                                                                                                                                                        │
│ File: src/grins_platform/repositories/google_sheet_submission_repository.py                                                                            │
│                                                                                                                                                        │
│ Pattern: Follow repositories/lead_repository.py:                                                                                                       │
│ - Inherit LoggerMixin, DOMAIN = "database"                                                                                                             │
│ - Constructor takes AsyncSession                                                                                                                       │
│                                                                                                                                                        │
│ Methods:                                                                                                                                               │
│ async def create(**kwargs) -> GoogleSheetSubmission                                                                                                    │
│ async def get_by_id(id: UUID) -> GoogleSheetSubmission | None                                                                                          │
│ async def get_by_row_number(row_number: int) -> GoogleSheetSubmission | None                                                                           │
│ async def get_max_row_number() -> int  # SELECT MAX(sheet_row_number) — for detecting new rows                                                         │
│ async def list_with_filters(params) -> tuple[list[GoogleSheetSubmission], int]                                                                         │
│ async def update_processing_status(id, status, lead_id=None, error=None)                                                                               │
│ async def count_by_status() -> dict[str, int]  # For sync status endpoint                                                                              │
│                                                                                                                                                        │
│ Step 8: Google Sheets Service                                                                                                                          │
│                                                                                                                                                        │
│ File: src/grins_platform/services/google_sheets_service.py                                                                                             │
│                                                                                                                                                        │
│ This is the core service. Pattern: Follow services/travel_time_service.py for the HTTP client pattern and services/sms_service.py for the external API │
│  integration pattern.                                                                                                                                  │
│                                                                                                                                                        │
│ class GoogleSheetsService(LoggerMixin):                                                                                                                │
│     DOMAIN = "integration"                                                                                                                             │
│                                                                                                                                                        │
│     def __init__(self, db_manager: DatabaseManager) -> None:                                                                                           │
│         super().__init__()                                                                                                                             │
│         self._client: httpx.AsyncClient | None = None                                                                                                  │
│         self._access_token: str | None = None                                                                                                          │
│         self._token_expires_at: float = 0                                                                                                              │
│         self._running: bool = False                                                                                                                    │
│         self._last_sync_at: datetime | None = None                                                                                                     │
│         self._last_error: str | None = None                                                                                                            │
│         self._db_manager = db_manager                                                                                                                  │
│                                                                                                                                                        │
│         # Config from env                                                                                                                              │
│         self.spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")                                                                            │
│         self.sheet_name = os.getenv("GOOGLE_SHEETS_SHEET_NAME", "Form Responses 1")                                                                    │
│         self.poll_interval = int(os.getenv("GOOGLE_SHEETS_POLL_INTERVAL_SECONDS", "60"))                                                               │
│         self.key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "")                                                                               │
│                                                                                                                                                        │
│     @property                                                                                                                                          │
│     def is_configured(self) -> bool:                                                                                                                   │
│         """Check if all required config is present."""                                                                                                 │
│         return bool(self.spreadsheet_id and self.key_path and Path(self.key_path).exists())                                                            │
│                                                                                                                                                        │
│ Key methods:                                                                                                                                           │
│                                                                                                                                                        │
│ ┌────────────────────────────────────┬───────────────────────────────────────────────────────────┐                                                     │
│ │               Method               │                          Purpose                          │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _get_access_token()                │ JWT auth flow (RS256 via python-jose), token caching      │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _get_client()                      │ Lazy httpx.AsyncClient creation (30s timeout)             │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ fetch_sheet_data()                 │ GET /spreadsheets/{id}/values/{range} → list of rows      │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ poll_loop()                        │ Main background loop: poll every N seconds                │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _poll_once()                       │ Single poll: fetch data, detect new rows, process them    │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _process_row(row_number, row_data) │ Store submission + conditionally create lead              │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _create_lead_from_submission(data) │ Map sheet data → Lead fields, create via LeadRepository   │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _determine_situation(data)         │ Map service columns → LeadSituation enum                  │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ _build_notes(data)                 │ Aggregate all relevant fields into notes text             │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ stop()                             │ Graceful shutdown: set _running=False, close httpx client │                                                     │
│ ├────────────────────────────────────┼───────────────────────────────────────────────────────────┤                                                     │
│ │ get_sync_status()                  │ Return current status for the API endpoint                │                                                     │
│ └────────────────────────────────────┴───────────────────────────────────────────────────────────┘                                                     │
│                                                                                                                                                        │
│ Background task lifecycle:                                                                                                                             │
│                                                                                                                                                        │
│ # In poll_loop():                                                                                                                                      │
│ self._running = True                                                                                                                                   │
│ while self._running:                                                                                                                                   │
│     try:                                                                                                                                               │
│         await self._poll_once()                                                                                                                        │
│         self._last_sync_at = datetime.now(UTC)                                                                                                         │
│         self._last_error = None                                                                                                                        │
│     except Exception as e:                                                                                                                             │
│         self.log_failed("poll_once", error=e)                                                                                                          │
│         self._last_error = str(e)                                                                                                                      │
│     await asyncio.sleep(self.poll_interval)                                                                                                            │
│                                                                                                                                                        │
│ # In stop():                                                                                                                                           │
│ self._running = False                                                                                                                                  │
│ if self._client:                                                                                                                                       │
│     await self._client.aclose()                                                                                                                        │
│                                                                                                                                                        │
│ Database session management in background task:                                                                                                        │
│                                                                                                                                                        │
│ The polling loop runs outside the request/response cycle, so it can't use FastAPI's Depends. Instead, it creates its own sessions via the              │
│ DatabaseManager:                                                                                                                                       │
│                                                                                                                                                        │
│ async def _poll_once(self) -> None:                                                                                                                    │
│     async for session in self._db_manager.get_session():                                                                                               │
│         submission_repo = GoogleSheetSubmissionRepository(session)                                                                                     │
│         lead_repo = LeadRepository(session)                                                                                                            │
│         # ... process rows within this session/transaction                                                                                             │
│                                                                                                                                                        │
│ Step 9: API Endpoints                                                                                                                                  │
│                                                                                                                                                        │
│ File: src/grins_platform/api/v1/google_sheet_submissions.py                                                                                            │
│                                                                                                                                                        │
│ All endpoints require authentication (same as leads endpoints).                                                                                        │
│                                                                                                                                                        │
│ ┌────────┬────────────────────────────────────────────┬──────────┬─────────────────────────────────────────────────────────┐                           │
│ │ Method │                  Endpoint                  │   Auth   │                         Purpose                         │                           │
│ ├────────┼────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤                           │
│ │ GET    │ /api/v1/sheet-submissions                  │ Required │ List submissions with pagination & filters              │                           │
│ ├────────┼────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤                           │
│ │ GET    │ /api/v1/sheet-submissions/sync-status      │ Required │ Get polling status                                      │                           │
│ ├────────┼────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤                           │
│ │ GET    │ /api/v1/sheet-submissions/{id}             │ Required │ Get single submission detail                            │                           │
│ ├────────┼────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤                           │
│ │ POST   │ /api/v1/sheet-submissions/{id}/create-lead │ Required │ Manually create lead from an existing-client submission │                           │
│ ├────────┼────────────────────────────────────────────┼──────────┼─────────────────────────────────────────────────────────┤                           │
│ │ POST   │ /api/v1/sheet-submissions/trigger-sync     │ Required │ Manually trigger a poll cycle                           │                           │
│ └────────┴────────────────────────────────────────────┴──────────┴─────────────────────────────────────────────────────────┘                           │
│                                                                                                                                                        │
│ Manual lead creation (POST /sheet-submissions/{id}/create-lead):                                                                                       │
│ - Allows admins to create a lead from a submission that was originally skipped (existing client) or errored                                            │
│ - Reuses the same _create_lead_from_submission() logic                                                                                                 │
│ - Updates the submission's processing_status and lead_id                                                                                               │
│                                                                                                                                                        │
│ Trigger sync (POST /sheet-submissions/trigger-sync):                                                                                                   │
│ - Immediately runs _poll_once() outside the normal interval                                                                                            │
│ - Returns the number of new rows imported                                                                                                              │
│                                                                                                                                                        │
│ Step 10: Dependency Injection                                                                                                                          │
│                                                                                                                                                        │
│ File: src/grins_platform/api/v1/dependencies.py                                                                                                        │
│                                                                                                                                                        │
│ Add:                                                                                                                                                   │
│ async def get_google_sheet_submission_repository(                                                                                                      │
│     session: Annotated[AsyncSession, Depends(get_db_session)],                                                                                         │
│ ) -> GoogleSheetSubmissionRepository:                                                                                                                  │
│     return GoogleSheetSubmissionRepository(session=session)                                                                                            │
│                                                                                                                                                        │
│ The GoogleSheetsService is a singleton stored in app.state (not per-request), since it manages the background polling task and httpx client lifecycle. │
│                                                                                                                                                        │
│ Step 11: App Lifespan Integration                                                                                                                      │
│                                                                                                                                                        │
│ File: src/grins_platform/app.py                                                                                                                        │
│                                                                                                                                                        │
│ Modify the lifespan() function:                                                                                                                        │
│                                                                                                                                                        │
│ @asynccontextmanager                                                                                                                                   │
│ async def lifespan(app: FastAPI) -> AsyncIterator[None]:                                                                                               │
│     # Startup                                                                                                                                          │
│     logger.info("app.startup_started", version="1.0.0")                                                                                                │
│     db_manager = get_database_manager()                                                                                                                │
│     health = await db_manager.health_check()                                                                                                           │
│     logger.info("app.startup_database_check", **health)                                                                                                │
│                                                                                                                                                        │
│     # Start Google Sheets poller (if configured)                                                                                                       │
│     sheets_service = GoogleSheetsService(db_manager)                                                                                                   │
│     polling_task = None                                                                                                                                │
│     if sheets_service.is_configured:                                                                                                                   │
│         polling_task = asyncio.create_task(sheets_service.poll_loop())                                                                                 │
│         app.state.sheets_service = sheets_service                                                                                                      │
│         logger.info("app.google_sheets_poller_started",                                                                                                │
│                      spreadsheet_id=sheets_service.spreadsheet_id,                                                                                     │
│                      interval=sheets_service.poll_interval)                                                                                            │
│     else:                                                                                                                                              │
│         logger.warning("app.google_sheets_not_configured")                                                                                             │
│                                                                                                                                                        │
│     logger.info("app.startup_completed")                                                                                                               │
│                                                                                                                                                        │
│     yield                                                                                                                                              │
│                                                                                                                                                        │
│     # Shutdown                                                                                                                                         │
│     logger.info("app.shutdown_started")                                                                                                                │
│     if sheets_service.is_configured:                                                                                                                   │
│         await sheets_service.stop()                                                                                                                    │
│         if polling_task:                                                                                                                               │
│             polling_task.cancel()                                                                                                                      │
│         logger.info("app.google_sheets_poller_stopped")                                                                                                │
│     await db_manager.close()                                                                                                                           │
│     logger.info("app.shutdown_completed")                                                                                                              │
│                                                                                                                                                        │
│ Step 12: Router Registration                                                                                                                           │
│                                                                                                                                                        │
│ File: src/grins_platform/api/v1/router.py                                                                                                              │
│                                                                                                                                                        │
│ Add:                                                                                                                                                   │
│ from grins_platform.api.v1.google_sheet_submissions import router as sheet_submissions_router                                                          │
│                                                                                                                                                        │
│ api_router.include_router(                                                                                                                             │
│     sheet_submissions_router,                                                                                                                          │
│     prefix="/sheet-submissions",                                                                                                                       │
│     tags=["google-sheets"],                                                                                                                            │
│ )                                                                                                                                                      │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Error Handling                                                                                                                                         │
│                                                                                                                                                        │
│ ┌──────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────┐      │
│ │                   Scenario                   │                                            Handling                                            │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Google API 429 (rate limited)                │ Log warning, retry on next poll cycle (60s natural backoff)                                    │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Google API 5xx (server error)                │ Log error, retry on next poll cycle                                                            │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Network timeout                              │ httpx timeout (30s), log error, retry next cycle                                               │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Service account key missing/invalid          │ is_configured returns False, poller doesn't start, log warning at startup                      │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Sheet not shared with service account        │ API returns 403, log error with clear message                                                  │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Invalid/missing data in row                  │ Store submission with processing_status="error", log error, continue to next row               │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Phone normalization fails                    │ Best-effort: strip non-digits, take last 10 chars. If still invalid, store lead with raw phone │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Duplicate row number                         │ Caught by UNIQUE constraint on sheet_row_number, skip silently (already imported)              │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Sheet structure changed (fewer/more columns) │ Rows are padded to 19 columns; extra columns ignored; missing columns filled with empty string │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Token refresh failure                        │ Log error, clear cached token, retry on next poll cycle                                        │      │
│ ├──────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────┤      │
│ │ Database connection failure                  │ Exception propagates, logged by poll_loop catch-all, retry next cycle                          │      │
│ └──────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Testing Plan                                                                                                                                           │
│                                                                                                                                                        │
│ Unit Tests                                                                                                                                             │
│                                                                                                                                                        │
│ File: src/grins_platform/tests/unit/test_google_sheets_service.py                                                                                      │
│                                                                                                                                                        │
│ ┌────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐ │
│ │       Test Class       │                                                           Tests                                                           │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestDetermineSituation │ new_system_install → new_system; repair_existing → repair; addition_to_system → upgrade; seasonal only → exploring; none  │ │
│ │                        │ selected → exploring; multiple selected → highest priority wins                                                           │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestBuildNotes         │ All services selected; only one service; with date needed; with additional info; with address/city; empty row             │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestProcessRow         │ New client → lead created + submission stored; existing client → submission stored + skipped; error during lead creation  │ │
│ │                        │ → submission stored + error status; short row (fewer than 19 cols) → padded correctly                                     │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestPhoneNormalization │ Valid phone → normalized; invalid phone → best effort; empty phone → handled                                              │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestDuplicateDetection │ Existing active lead with same phone → returns existing lead, no duplicate                                                │ │
│ ├────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤ │
│ │ TestIsConfigured       │ All env vars present + file exists → True; missing spreadsheet ID → False; missing key file → False                       │ │
│ └────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                                                                        │
│ File: src/grins_platform/tests/unit/test_google_sheet_submission_schemas.py                                                                            │
│                                                                                                                                                        │
│ ┌───────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────┐                                 │
│ │            Test Class             │                                     Tests                                      │                                 │
│ ├───────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤                                 │
│ │ TestGoogleSheetSubmissionResponse │ Serialization from ORM model; all fields present; null handling                │                                 │
│ ├───────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤                                 │
│ │ TestListParams                    │ Default values; filter by client_type; filter by processing_status; pagination │                                 │
│ ├───────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┤                                 │
│ │ TestSyncStatusResponse            │ Running status; stopped status; with error                                     │                                 │
│ └───────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────┘                                 │
│                                                                                                                                                        │
│ File: src/grins_platform/tests/unit/test_google_sheet_submission_api.py                                                                                │
│                                                                                                                                                        │
│ ┌─────────────────────┬───────────────────────────────────────────────────────────────────────┐                                                        │
│ │     Test Class      │                                 Tests                                 │                                                        │
│ ├─────────────────────┼───────────────────────────────────────────────────────────────────────┤                                                        │
│ │ TestListSubmissions │ Success with pagination; filter by client_type; unauthenticated → 401 │                                                        │
│ ├─────────────────────┼───────────────────────────────────────────────────────────────────────┤                                                        │
│ │ TestGetSubmission   │ Found; not found → 404                                                │                                                        │
│ ├─────────────────────┼───────────────────────────────────────────────────────────────────────┤                                                        │
│ │ TestSyncStatus      │ Returns current status                                                │                                                        │
│ ├─────────────────────┼───────────────────────────────────────────────────────────────────────┤                                                        │
│ │ TestCreateLead      │ Success → lead created; already has lead → error                      │                                                        │
│ ├─────────────────────┼───────────────────────────────────────────────────────────────────────┤                                                        │
│ │ TestTriggerSync     │ Success → returns count                                               │                                                        │
│ └─────────────────────┴───────────────────────────────────────────────────────────────────────┘                                                        │
│                                                                                                                                                        │
│ Integration Tests                                                                                                                                      │
│                                                                                                                                                        │
│ File: src/grins_platform/tests/integration/test_google_sheets_integration.py                                                                           │
│                                                                                                                                                        │
│ ┌─────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────┐                        │
│ │              Test               │                                        Description                                        │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_new_client_creates_lead    │ Process row with client_type="new" → submission stored + lead created with correct fields │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_existing_client_no_lead    │ Process row with client_type="existing" → submission stored + status="skipped" + no lead  │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_duplicate_row_prevention   │ Import same row_number twice → only one submission (UNIQUE constraint)                    │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_duplicate_phone_detection  │ Two rows with same phone → only one lead, both submissions linked                         │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_situation_mapping_priority │ Row with new_system_install + repair → situation="new_system" (priority)                  │                        │
│ ├─────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┤                        │
│ │ test_notes_aggregation          │ Row with multiple services + info → notes contains all data                               │                        │
│ └─────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────┘                        │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Verification Plan                                                                                                                                      │
│                                                                                                                                                        │
│ 1. Lint: ruff check src/grins_platform/services/google_sheets_service.py src/grins_platform/models/google_sheet_submission.py                          │
│ 2. Unit tests: pytest src/grins_platform/tests/unit/test_google_sheets*.py -v                                                                          │
│ 3. Integration tests: pytest src/grins_platform/tests/integration/test_google_sheets*.py -v                                                            │
│ 4. Manual end-to-end test:                                                                                                                             │
│   - Set up a test Google Sheet with sample rows (both new and existing clients)                                                                        │
│   - Create a service account and share the sheet                                                                                                       │
│   - Configure .env with spreadsheet ID and key path                                                                                                    │
│   - Run alembic upgrade head to apply migrations                                                                                                       │
│   - Start the app → verify "google_sheets_poller_started" log                                                                                          │
│   - Add a new row with client_type="new" → verify lead appears in GET /api/v1/leads                                                                    │
│   - Add a row with client_type="existing" → verify no lead, submission stored                                                                          │
│   - Hit GET /api/v1/sheet-submissions → verify all imported rows                                                                                       │
│   - Hit GET /api/v1/sheet-submissions/sync-status → verify poller running                                                                              │
│   - Hit POST /api/v1/sheet-submissions/{id}/create-lead on a skipped row → verify lead created                                                         │
│                                                                                                                                                        │
│ ---                                                                                                                                                    │
│ Implementation Order                                                                                                                                   │
│                                                                                                                                                        │
│ ┌─────┬──────────────────────────────────────────────────┬──────────────────────────────────────┐                                                      │
│ │  #  │                       Task                       │             Dependencies             │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 1   │ Add env vars to .env                             │ —                                    │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 2   │ Create migration: google_sheet_submissions table │ —                                    │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 3   │ Create migration: make leads.zip_code nullable   │ —                                    │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 4   │ Create SQLAlchemy model: GoogleSheetSubmission   │ Migration #2                         │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 5   │ Update Lead model: zip_code nullable             │ Migration #3                         │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 6   │ Create Pydantic schemas                          │ Model #4                             │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 7   │ Create repository                                │ Model #4                             │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 8   │ Create Google Sheets service                     │ Repository #7                        │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 9   │ Create API endpoints                             │ Service #8, Schemas #6               │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 10  │ Update dependencies.py                           │ Repository #7                        │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 11  │ Update router.py                                 │ Endpoints #9                         │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 12  │ Update app.py lifespan                           │ Service #8                           │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 13  │ Create Markdown/PHASE-13-PLANNING.md             │ —                                    │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 14  │ Create docs/google_sheets_retrieval.md           │ —                                    │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 15  │ Write unit tests                                 │ Service #8, Schemas #6, Endpoints #9 │                                                      │
│ ├─────┼──────────────────────────────────────────────────┼──────────────────────────────────────┤                                                      │
│ │ 16  │ Write integration tests                          │ All above                            │                                                      │
│ └─────┴──────────────────────────────────────────────────┴──────────────────────────────────────┘         