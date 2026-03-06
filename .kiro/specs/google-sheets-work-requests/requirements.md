# Requirements Document

## Introduction

The Grins Irrigation Platform receives service requests through a Google Form that populates a Google Sheet with 19 columns of data. Today this sheet is checked manually. This feature automates the retrieval of Google Sheet submissions, stores all rows in a dedicated database table, auto-creates Lead records for new client submissions, and provides an admin "Work Requests" tab to view and manage all submissions. Admins can also manually create leads from any work request entry regardless of client type.

## Glossary

- **Poller**: Background asyncio task running inside the FastAPI lifespan that periodically fetches new rows from the Google Sheet via the Sheets API v4
- **Submission**: A single row from the Google Sheet representing one service request form response, stored in the `google_sheet_submissions` database table
- **Work_Requests_Tab**: A new navigation tab in the admin dashboard that displays all Google Sheet submissions with all 19 columns
- **Processing_Status**: The outcome state of a submission: `imported` (stored but not yet processed), `lead_created` (Lead record created), `skipped` (existing client, no auto-lead), or `error` (processing failed)
- **Client_Type**: A column value from the Google Sheet indicating whether the submitter is a "new" or "existing" client
- **Situation_Mapper**: Logic that maps service request columns (B through G) to a LeadSituation enum value using a priority-based algorithm
- **Sync_Status**: Runtime information about the Poller including last sync time, running state, and last error
- **Sheet_Row_Number**: The 1-based row index from the Google Sheet used as a unique deduplication key
- **Service_Account**: A Google Cloud service account used for server-to-server JWT authentication with the Google Sheets API
- **Manual_Lead_Creation**: The admin action of creating a Lead record from any submission, regardless of client type or processing status
- **Notes_Aggregator**: Logic that combines multiple sheet columns (services requested, dates, addresses, additional info) into a single Lead notes field
- **Key_Columns**: The subset of submission fields displayed in the Work Requests list view: name, phone, email, client_type, property_type, processing_status, date_work_needed_by, and imported_at. All 19 sheet columns plus metadata are shown in the detail view

## Requirements

### Requirement 1: Google Sheets Polling and Data Retrieval

**User Story:** As a platform operator, I want the system to automatically poll a Google Form-linked Google Sheet for new submissions, so that service requests are captured without manual effort.

#### Acceptance Criteria

1. WHEN the application starts and the Service_Account key path and spreadsheet ID are configured, THE Poller SHALL authenticate using a Service_Account JWT signed with RS256 and begin polling the Google Sheet at a configurable interval (default 60 seconds)
2. WHEN the application starts and the Service_Account key path or spreadsheet ID is missing, THE Poller SHALL log a warning and skip polling startup without causing application failure
3. WHEN the Poller executes a poll cycle, THE Poller SHALL fetch all rows from columns A through S of the configured sheet using the Google Sheets API v4 GET /values endpoint
4. WHEN the Poller detects rows with Sheet_Row_Number values not yet stored in the database, THE Poller SHALL process only those new rows and skip previously imported rows
5. WHEN the Poller receives a valid access token that is within 100 seconds of expiry, THE Poller SHALL request a new access token before the next API call
6. WHEN the application shuts down, THE Poller SHALL set its running flag to false, cancel the polling task, and close the HTTP client gracefully
7. WHILE the Poller is running, THE Poller SHALL track and expose the last successful sync timestamp, running state, and last error message for the Sync_Status endpoint
8. WHEN the Poller fetches sheet data, THE Poller SHALL dynamically detect and skip the header row by checking if the first row's values match expected column header names (e.g., "Timestamp" in column A), rather than hardcoding row 1 as the header

### Requirement 2: Submission Storage

**User Story:** As a platform operator, I want all Google Sheet submissions stored in a dedicated database table, so that the platform has a complete record of every service request regardless of client type.

#### Acceptance Criteria

1. WHEN the Poller processes a new sheet row, THE Poller SHALL store all 19 column values as raw strings in the `google_sheet_submissions` table along with the Sheet_Row_Number and an `imported_at` timestamp
2. THE `google_sheet_submissions` table SHALL enforce a UNIQUE constraint on Sheet_Row_Number to prevent duplicate row imports
3. WHEN a row has fewer than 19 values (due to trailing empty cells omitted by the Google Sheets API), THE Poller SHALL treat missing trailing columns as empty strings
4. THE `google_sheet_submissions` table SHALL store a Processing_Status field with an initial value of `imported` for each new row
5. THE `google_sheet_submissions` table SHALL store an optional `lead_id` foreign key referencing the `leads` table, populated when a Lead is created from the submission
6. THE `google_sheet_submissions` table SHALL store an optional `processing_error` text field to capture error details when processing fails

### Requirement 3: Automatic Lead Creation for New Clients

**User Story:** As a platform operator, I want the system to automatically create Lead records for new client submissions, so that new prospects enter the lead management pipeline without manual data entry.

#### Acceptance Criteria

1. WHEN a submission has Client_Type equal to "new" (case-insensitive, trimmed), THE Poller SHALL create a new Lead record with status "new" and source_site "google_sheets"
2. WHEN a submission has Client_Type equal to "existing" or any value other than "new", THE Poller SHALL set the Processing_Status to `skipped` and not create a Lead record
3. WHEN creating a Lead from a submission, THE Situation_Mapper SHALL determine the LeadSituation using the following priority order: new_system_install maps to `new_system`, addition_to_system maps to `upgrade`, repair_existing maps to `repair`, any seasonal service (spring_startup, fall_blowout, summer_tuneup) maps to `exploring`, and no service selected defaults to `exploring`
4. WHEN creating a Lead from a submission, THE Notes_Aggregator SHALL combine the following fields into the Lead notes: requested services with their frequency, date_work_needed_by, additional_services_info, city, address, additional_info, landscape_hardscape, and referral_source
5. WHEN creating a Lead from a submission, THE Poller SHALL normalize the phone number using the existing `normalize_phone()` function and set zip_code to NULL
6. WHEN creating a Lead from a submission, THE Poller SHALL check for an existing active Lead with the same normalized phone number; if a duplicate exists, THE Poller SHALL link the submission to the existing Lead instead of creating a new one
7. IF an error occurs during Lead creation for a submission, THEN THE Poller SHALL set the Processing_Status to `error`, store the error message in `processing_error`, and continue processing the next row
8. WHEN a Lead is successfully created or linked, THE Poller SHALL update the submission's Processing_Status to `lead_created` and set the `lead_id` foreign key
9. WHEN creating a Lead from a submission where the name field (Col J) is empty or blank, THE Poller SHALL use "Unknown" as the fallback name value
10. WHEN creating a Lead from a submission where the phone field (Col K) is empty, invalid, or cannot be normalized, THE Poller SHALL use "0000000000" as the fallback phone value

### Requirement 4: Schema Migration for Nullable Zip Code

**User Story:** As a developer, I want the `leads.zip_code` column to accept NULL values, so that leads created from Google Sheet submissions (which lack zip codes) can be stored without validation errors.

#### Acceptance Criteria

1. THE database migration SHALL alter the `leads.zip_code` column from NOT NULL to nullable
2. WHEN a Lead is created via the public form submission endpoint (POST /api/v1/leads), THE LeadSubmission schema SHALL continue to require and validate a 5-digit zip_code
3. WHEN a Lead is created from a Google Sheet submission, THE Poller SHALL set zip_code to NULL
4. THE LeadResponse Pydantic schema SHALL be updated to allow zip_code to be `str | None` so the API can return null zip codes for leads created from Google Sheet submissions without serialization errors

### Requirement 5: Admin API Endpoints for Sheet Submissions

**User Story:** As an admin user, I want API endpoints to list, view, and manage Google Sheet submissions, so that the frontend Work Requests tab can display and interact with submission data.

#### Acceptance Criteria

1. WHEN an authenticated admin requests GET /api/v1/sheet-submissions, THE API SHALL return a paginated list of submissions with support for filtering by Processing_Status and Client_Type, text search across name, phone, email, and address fields, and sorting by imported_at
2. WHEN an authenticated admin requests GET /api/v1/sheet-submissions/{id}, THE API SHALL return the full submission record including all 19 sheet columns, Processing_Status, lead_id, and processing_error
3. WHEN an authenticated admin requests GET /api/v1/sheet-submissions/sync-status, THE API SHALL return the current Sync_Status including last sync timestamp, running state, and last error
4. WHEN an authenticated admin requests POST /api/v1/sheet-submissions/{id}/create-lead for a submission that does not already have a linked Lead, THE API SHALL create a Lead record using the same mapping logic as automatic creation and update the submission's Processing_Status and lead_id
5. IF an authenticated admin requests POST /api/v1/sheet-submissions/{id}/create-lead for a submission that already has a linked Lead, THEN THE API SHALL return a 409 Conflict error with a descriptive message
6. WHEN an authenticated admin requests POST /api/v1/sheet-submissions/trigger-sync, THE API SHALL immediately execute one poll cycle and return the count of new rows imported
7. IF an unauthenticated request is made to any sheet-submissions endpoint, THEN THE API SHALL return a 401 Unauthorized error

### Requirement 6: Work Requests Tab (Frontend)

**User Story:** As an admin user, I want a "Work Requests" tab in the admin dashboard that displays all Google Sheet submissions, so that I can view and manage service requests from the Google Form.

#### Acceptance Criteria

1. THE Work_Requests_Tab SHALL appear as a navigation item labeled "Work Requests" in the admin sidebar, positioned after the "Leads" tab
2. WHEN the Work_Requests_Tab is active, THE Work_Requests_Tab SHALL display a paginated table showing key columns: name, phone, email, client_type, property_type, processing_status, date_work_needed_by, and imported_at. All remaining columns SHALL be visible in the detail view
3. WHEN the admin clicks a row in the Work Requests table, THE Work_Requests_Tab SHALL navigate to a detail view showing all submission fields and the linked Lead (if one exists)
4. THE Work_Requests_Tab SHALL provide filter controls for Processing_Status, Client_Type, and text search
5. THE Work_Requests_Tab SHALL display a total count of submissions above the table
6. WHEN data is loading, THE Work_Requests_Tab SHALL display a loading indicator; WHEN an error occurs, THE Work_Requests_Tab SHALL display an error message with a retry option
7. THE Work_Requests_Tab SHALL follow the same visual design patterns as the existing Leads tab including table styling, pagination controls, and empty state messaging
8. THE Work_Requests_Tab SHALL display a "Trigger Sync" button in the page header that calls POST /api/v1/sheet-submissions/trigger-sync and displays a notification with the count of new rows imported
9. THE Work_Requests_Tab SHALL display the current sync status (last sync timestamp and poller running state) in the page header area
10. THE Work_Requests_Tab SHALL provide a text search input that filters submissions by name, phone, email, or address

### Requirement 7: Manual Lead Creation from Work Requests

**User Story:** As an admin user, I want to manually create a lead from any work request entry, so that I can convert existing-client submissions or errored submissions into leads when appropriate.

#### Acceptance Criteria

1. WHEN viewing a submission that does not have a linked Lead, THE Work_Requests_Tab SHALL display a "Create Lead" button
2. WHEN the admin clicks the "Create Lead" button, THE Work_Requests_Tab SHALL call POST /api/v1/sheet-submissions/{id}/create-lead and display a success notification upon completion
3. WHEN a Lead is successfully created from a submission, THE Work_Requests_Tab SHALL update the submission row to reflect the new Processing_Status and display a link to the created Lead
4. IF the Lead creation fails, THEN THE Work_Requests_Tab SHALL display an error notification with the failure reason
5. WHEN viewing a submission that already has a linked Lead, THE Work_Requests_Tab SHALL display the linked Lead's status and a link to navigate to the Lead detail view instead of a "Create Lead" button

### Requirement 8: Error Handling and Resilience

**User Story:** As a platform operator, I want the Google Sheets polling system to handle errors gracefully, so that transient failures do not disrupt the platform or lose data.

#### Acceptance Criteria

1. WHEN the Google Sheets API returns a 429 (rate limited) response, THE Poller SHALL log a warning and retry on the next scheduled poll cycle
2. WHEN the Google Sheets API returns a 5xx (server error) response, THE Poller SHALL log an error and retry on the next scheduled poll cycle
3. WHEN a network timeout occurs during a Google Sheets API call, THE Poller SHALL log an error and retry on the next scheduled poll cycle (HTTP client timeout is 30 seconds)
4. IF the Service_Account key file is missing or contains invalid credentials, THEN THE Poller SHALL log an error with a descriptive message and not start the polling loop
5. WHEN the access token refresh fails, THE Poller SHALL log an error and retry token acquisition on the next poll cycle
6. WHEN processing an individual row fails, THE Poller SHALL mark that submission as `error`, log the failure with row context, and continue processing remaining rows

### Requirement 9: Configuration

**User Story:** As a platform operator, I want the Google Sheets integration to be configurable via environment variables, so that I can set up the integration without code changes.

#### Acceptance Criteria

1. THE Poller SHALL read the spreadsheet identifier from the `GOOGLE_SHEETS_SPREADSHEET_ID` environment variable
2. THE Poller SHALL read the sheet tab name from the `GOOGLE_SHEETS_SHEET_NAME` environment variable with a default value of "Form Responses 1"
3. THE Poller SHALL read the poll interval from the `GOOGLE_SHEETS_POLL_INTERVAL_SECONDS` environment variable with a default value of 60 seconds
4. THE Poller SHALL read the service account key file path from the `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` environment variable
