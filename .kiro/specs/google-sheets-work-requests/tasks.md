# Implementation Plan: Google Sheets Work Requests

## Overview

This plan implements the Google Sheets Work Requests feature in phases: database foundation first, then backend services and poller, API layer, frontend components, and finally integration wiring. Each phase builds on the previous one. Backend is Python/FastAPI/SQLAlchemy, frontend is React/TypeScript/TanStack Query.

## Tasks

- [x] 1. Database foundation and models
  - [x] 1.1 Create Alembic migration to make `leads.zip_code` nullable
    - Add migration with `op.alter_column("leads", "zip_code", nullable=True)`
    - Downgrade must backfill NULLs with `'00000'` then restore NOT NULL
    - _Requirements: 4.1, 4.3, 15.3_

  - [x] 1.2 Update `LeadResponse` schema to allow nullable `zip_code`
    - Change `zip_code: str` to `zip_code: str | None` in `schemas/lead.py`
    - Audit `LeadDetail.tsx` frontend component to handle null zip_code (display "N/A")
    - Verify `LeadSubmission` still requires 5-digit zip_code for public form
    - _Requirements: 4.2, 4.4, 4.5_

  - [x] 1.3 Create `GoogleSheetSubmission` SQLAlchemy model
    - Create `src/grins_platform/models/google_sheet_submission.py`
    - Define all 19 sheet columns as nullable strings, processing metadata fields, lead relationship
    - Add indexes on `client_type`, `processing_status`, `imported_at`
    - Register model in `models/__init__.py`
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [x] 1.4 Create Alembic migration for `google_sheet_submissions` table
    - Generate migration from the new model
    - Include UNIQUE constraint on `sheet_row_number`, indexes, foreign key to `leads`
    - _Requirements: 2.2_

  - [x] 1.5 Create Pydantic schemas for Google Sheet submissions
    - Create `src/grins_platform/schemas/google_sheet_submission.py`
    - Define `GoogleSheetSubmissionResponse`, `SubmissionListParams`, `PaginatedSubmissionResponse`, `SyncStatusResponse`, `TriggerSyncResponse`
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 2. Checkpoint - Verify database foundation
  - Ensure migrations run cleanly, models import without errors, schemas validate correctly. Ask the user if questions arise.

- [x] 3. Backend repository and service layer
  - [x] 3.1 Add test fixtures to conftest
    - Add `sample_sheet_row`, `sample_sheet_row_factory`, `mock_sheets_service`, `mock_sheets_repository`, `sample_submission_model` fixtures to `tests/conftest.py`
    - These fixtures are used by unit, functional, and integration tests in subsequent tasks
    - _Requirements: 12.8_

  - [x] 3.2 Create `GoogleSheetSubmissionRepository`
    - Create `src/grins_platform/repositories/google_sheet_submission_repository.py`
    - Implement `create`, `get_by_id`, `get_max_row_number`, `list_with_filters`, `update`
    - Extend `LoggerMixin` with `DOMAIN = "database"`
    - Emit structured log events for all CRUD operations
    - _Requirements: 2.1, 2.2, 5.1, 11.2_

  - [x] 3.3 Write unit tests for `GoogleSheetSubmissionRepository`
    - Test all CRUD methods with mocked session
    - Test `list_with_filters` with various filter combinations
    - Test `get_max_row_number` returns 0 when no rows exist
    - _Requirements: 12.1, 12.4_

  - [x] 3.4 Create `GoogleSheetsService` with business logic
    - Create `src/grins_platform/services/google_sheets_service.py`
    - Implement `process_row`, `create_lead_from_submission`, `list_submissions`, `get_submission`
    - Implement static helpers: `map_situation`, `aggregate_notes`, `normalize_name`, `safe_normalize_phone`
    - `safe_normalize_phone` wraps existing `normalize_phone()` from `schemas/customer.py`
    - Extend `LoggerMixin` with `DOMAIN = "sheets"`
    - Emit structured log events for all public methods
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 11.1, 17.2, 17.3, 17.4_

  - [x] 3.5 Write property test: Row padding produces exactly 19 columns
    - **Property 1: Row padding produces exactly 19 columns**
    - **Validates: Requirements 2.3**

  - [x] 3.6 Write property test: Situation mapping priority
    - **Property 4: Situation mapping priority**
    - **Validates: Requirements 3.3**

  - [x] 3.7 Write property test: Notes aggregation contains all non-empty fields
    - **Property 5: Notes aggregation contains all non-empty fields**
    - **Validates: Requirements 3.4**

  - [x] 3.8 Write property test: Field fallbacks for missing data
    - **Property 6: Field fallbacks for missing data**
    - **Validates: Requirements 3.9, 3.10_

  - [x] 3.9 Write property test: safe_normalize_phone wraps normalize_phone
    - **Property 17: safe_normalize_phone wraps normalize_phone**
    - **Validates: Requirements 3.10, 17.3**

  - [x] 3.10 Write property test: Client type determines lead creation
    - **Property 3: Client type determines lead creation**
    - **Validates: Requirements 3.1, 3.2, 3.8**

  - [x] 3.11 Write unit tests for `GoogleSheetsService`
    - Test `process_row` for new client (lead created), existing client (skipped), error case
    - Test `create_lead_from_submission` including 409 conflict guard
    - Test duplicate phone deduplication
    - Test name/phone fallbacks
    - _Requirements: 12.1, 12.4_

  - [x] 3.12 Write unit tests for Pydantic schemas
    - Create `tests/unit/test_google_sheet_submission_schemas.py`
    - Test `GoogleSheetSubmissionResponse` serialization from ORM model, all fields present, null handling
    - Test `SubmissionListParams` default values, filter validation, pagination bounds
    - Test `SyncStatusResponse` running/stopped states, with/without error
    - Test `TriggerSyncResponse` serialization
    - _Requirements: 12.1, 12.4_

- [x] 4. Checkpoint - Verify service layer
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Google Sheets Poller (background task)
  - [x] 5.1 Add Google Sheets configuration settings
    - Add `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_SHEET_NAME`, `GOOGLE_SHEETS_POLL_INTERVAL_SECONDS`, `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` to settings class
    - Add placeholder environment variables to `.env` file:
      ```
      # Google Sheets Integration
      GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here
      GOOGLE_SHEETS_SHEET_NAME=Form Responses 1
      GOOGLE_SHEETS_POLL_INTERVAL_SECONDS=60
      GOOGLE_SERVICE_ACCOUNT_KEY_PATH=./service-account-key.json
      ```
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 5.2 Create `GoogleSheetsPoller` background task
    - Create `src/grins_platform/services/google_sheets_poller.py`
    - Implement JWT auth with RS256 (`_build_jwt_assertion`, `_request_token`, `_ensure_token` with 100s expiry buffer)
    - Implement `_poll_loop` with configurable interval, `_fetch_sheet_data`, `_execute_poll_cycle`
    - Implement `asyncio.Lock` for concurrent poll serialization
    - Implement header row detection (dynamic, checks for "Timestamp" in first cell)
    - Implement `start`/`stop` lifecycle with graceful shutdown
    - Implement `sync_status` property returning `SyncStatusResponse`
    - Implement `trigger_sync` method for manual sync
    - Use `get_logger(__name__)` for structured logging
    - Handle 403, 429, 5xx, timeout, token refresh errors per design
    - Per-row transaction commits for error isolation
    - Never log key contents, JWT assertions, or access tokens
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 5.8, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.3, 11.6, 16.1, 16.2, 16.4_

  - [x] 5.3 Integrate poller into FastAPI lifespan
    - Add poller startup/shutdown to the existing lifespan function in `main.py`
    - Store poller on `app.state.sheets_poller` for API access
    - Skip startup gracefully if config is missing
    - _Requirements: 1.1, 1.2, 1.6_

  - [x] 5.4 Write property test: Header row detection
    - **Property 13: Header row detection**
    - **Validates: Requirements 1.8**

  - [x] 5.5 Write property test: Token refresh triggers within expiry buffer
    - **Property 12: Token refresh triggers within expiry buffer**
    - **Validates: Requirements 1.5**

  - [x] 5.6 Write unit tests for `GoogleSheetsPoller`
    - Test start/stop lifecycle
    - Test JWT assertion building
    - Test token refresh with expiry buffer
    - Test poll loop with mocked HTTP responses (429, 5xx, timeout)
    - Test header row detection and skipping
    - Test graceful handling of missing config
    - _Requirements: 12.1, 12.4_

- [x] 6. Checkpoint - Verify poller
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Admin API endpoints
  - [x] 7.1 Add dependency injection for sheet submissions
    - Add `get_google_sheet_submission_repository` dependency to `api/v1/dependencies.py`
    - Add `get_sheets_service` dependency that retrieves the service from `request.app.state`
    - _Requirements: 5.1_

  - [x] 7.2 Create sheet submissions API router
    - Create `src/grins_platform/api/v1/sheet_submissions.py`
    - Implement GET `/sheet-submissions` (paginated list with filters)
    - Implement GET `/sheet-submissions/sync-status` (poller status)
    - Implement GET `/sheet-submissions/{id}` (single submission detail)
    - Implement POST `/sheet-submissions/{id}/create-lead` (manual lead creation, 409 on duplicate)
    - Implement POST `/sheet-submissions/trigger-sync` (immediate poll cycle)
    - Register `/sync-status` and `/trigger-sync` before `/{id}` to avoid path conflicts
    - All endpoints require `require_admin` dependency
    - Use `DomainLogger.api_event()` with request ID correlation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 11.4, 16.3_

  - [x] 7.3 Register sheet submissions router in `main.py`
    - Add `app.include_router(sheet_submissions_router, prefix="/api/v1/sheet-submissions", tags=["sheet-submissions"])`
    - _Requirements: 5.1_

  - [x] 7.4 Write unit tests for sheet submissions API
    - Test all 5 endpoints with mocked service
    - Test 401 for unauthenticated requests
    - Test 404 for missing submission
    - Test 409 for create-lead on already-linked submission
    - Test query parameter validation (422)
    - _Requirements: 5.7, 12.1, 12.4_

- [x] 8. Checkpoint - Verify backend API
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Frontend: types, API client, and hooks
  - [x] 9.1 Create Work Requests feature types
    - Create `frontend/src/features/work-requests/types/index.ts`
    - Define `ProcessingStatus`, `SheetClientType`, `WorkRequest`, `SyncStatus`, `WorkRequestListParams`, `PaginatedWorkRequestResponse`
    - _Requirements: 6.2, 6.3_

  - [x] 9.2 Create Work Requests API client
    - Create `frontend/src/features/work-requests/api/workRequestApi.ts`
    - Implement `list`, `getById`, `getSyncStatus`, `createLead`, `triggerSync` methods
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [x] 9.3 Create TanStack Query hooks
    - Create `frontend/src/features/work-requests/hooks/useWorkRequests.ts`
    - Implement `useWorkRequests`, `useWorkRequest`, `useSyncStatus`, `useCreateLeadFromSubmission`, `useTriggerSync`
    - Use query key factory pattern
    - Invalidate queries on mutations
    - _Requirements: 6.2, 6.3, 6.8_

- [x] 10. Frontend: components
  - [x] 10.1 Create `ProcessingStatusBadge` component
    - Create `frontend/src/features/work-requests/components/ProcessingStatusBadge.tsx`
    - Display colored badge for each processing status (imported, lead_created, skipped, error)
    - Use `data-testid="status-{value}"`
    - _Requirements: 6.2, 13.1_

  - [x] 10.2 Create `SyncStatusBar` component
    - Create `frontend/src/features/work-requests/components/SyncStatusBar.tsx`
    - Display last sync timestamp and poller running state
    - Use `data-testid="sync-status-bar"`
    - _Requirements: 6.9, 13.1_

  - [x] 10.3 Create `WorkRequestFilters` component
    - Create `frontend/src/features/work-requests/components/WorkRequestFilters.tsx`
    - Include Processing Status dropdown, Client Type dropdown, text search input
    - Use `data-testid` attributes: `filter-processing-status`, `filter-client-type`, `search-input`
    - _Requirements: 6.4, 6.10, 13.1_

  - [x] 10.4 Create `WorkRequestsList` component
    - Create `frontend/src/features/work-requests/components/WorkRequestsList.tsx`
    - Display paginated table with key columns: name, phone, email, client_type, property_type, processing_status, date_work_needed_by, imported_at
    - Include SyncStatusBar, WorkRequestFilters, Trigger Sync button, submission count
    - Handle loading, error, and empty states
    - Follow Leads tab visual patterns (table styling, pagination, empty state)
    - Use `data-testid` attributes: `work-requests-page`, `work-requests-table`, `work-request-row`, `trigger-sync-btn`, `submission-count`, `loading-spinner`, `error-message`, `empty-state`, `pagination-controls`
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 13.1_

  - [x] 10.5 Create `WorkRequestDetail` component
    - Create `frontend/src/features/work-requests/components/WorkRequestDetail.tsx`
    - Display all 19 sheet columns plus processing metadata
    - Show "Create Lead" button when no linked lead (`data-testid="create-lead-btn"`)
    - Show lead link when lead exists (`data-testid="lead-link"`)
    - Handle create lead success/error with toast notifications
    - Use `data-testid="work-request-detail"`
    - _Requirements: 6.3, 7.1, 7.2, 7.3, 7.4, 7.5, 13.1_

  - [x] 10.6 Create feature index and add route
    - Create `frontend/src/features/work-requests/index.ts` exporting public API
    - Add `/work-requests` and `/work-requests/:id` routes in `App.tsx`
    - _Requirements: 6.1_

  - [x] 10.7 Add Work Requests to sidebar navigation
    - Insert "Work Requests" nav item at index 3 in `Layout.tsx` navItems array (after Leads)
    - Use `ClipboardList` icon from lucide-react
    - Use `data-testid="nav-work-requests"`
    - _Requirements: 6.1, 6.11, 13.1_

- [x] 11. Checkpoint - Verify frontend components
  - Ensure all frontend tests pass, ask the user if questions arise.

- [x] 12. Backend functional and integration tests
  - [x] 12.1 Write functional tests for Google Sheets workflow
    - Test full polling cycle with mocked Sheets API → submissions stored, leads created
    - Test manual lead creation workflow → submission updated, lead linked
    - Test duplicate phone deduplication → existing lead linked
    - Test error isolation → failed row doesn't block others
    - Test unique constraint prevents duplicate row imports
    - _Requirements: 12.2, 12.5_

  - [x] 12.2 Write integration tests for cross-feature compatibility
    - Test sheet-created lead appears in GET /api/v1/leads
    - Test sheet-created lead included in dashboard metrics
    - Test null zip_code leads coexist with normal leads
    - Test existing leads unaffected by migration
    - Test public form still requires zip_code
    - Test migration downgrade backfills zip_code
    - Test all API endpoints require authentication
    - _Requirements: 12.3, 12.6, 15.1, 15.2, 15.3, 15.4, 15.5_

  - [x] 12.3 Write property test: Duplicate phone deduplication
    - **Property 9: Duplicate phone deduplication**
    - **Validates: Requirements 3.6**

  - [x] 12.4 Write property test: Row processing error isolation
    - **Property 10: Row processing error isolation**
    - **Validates: Requirements 3.7, 8.6**

  - [x] 12.5 Write property test: Only new rows are processed
    - **Property 11: Only new rows are processed**
    - **Validates: Requirements 1.4**

  - [x] 12.6 Write property test: Manual lead creation idempotency guard
    - **Property 15: Manual lead creation idempotency guard**
    - **Validates: Requirements 5.5**

  - [x] 12.7 Write property test: New submission invariants
    - **Property 2: New submission invariants**
    - **Validates: Requirements 2.1, 2.4**

  - [x] 12.8 Write property test: Sheet-created leads have null zip_code
    - **Property 7: Sheet-created leads have null zip_code**
    - **Validates: Requirements 3.5, 4.3, 4.4**

  - [x] 12.9 Write property test: Public form submission still requires zip_code
    - **Property 8: Public form submission still requires zip_code**
    - **Validates: Requirements 4.2**

  - [x] 12.10 Write property test: Submission list filtering
    - **Property 14: Submission list filtering**
    - **Validates: Requirements 5.1, 6.10**

  - [x] 12.11 Write property test: Concurrent poll cycles are serialized
    - **Property 16: Concurrent poll cycles are serialized**
    - **Validates: Requirements 5.8**

- [x] 13. Frontend tests
  - [x] 13.1 Write tests for `WorkRequestsList` component
    - Test table rendering with data, pagination, filters, empty state, loading state, error state
    - Test sync status display and trigger sync button
    - Co-locate as `WorkRequestsList.test.tsx`
    - _Requirements: 13.2, 13.4, 13.5_

  - [x] 13.2 Write tests for `WorkRequestDetail` component
    - Test all 19 fields displayed, create lead button visibility, lead link display
    - Test create lead success/error flows
    - Co-locate as `WorkRequestDetail.test.tsx`
    - _Requirements: 13.2, 13.4, 13.5_

  - [x] 13.3 Write tests for `ProcessingStatusBadge` and `SyncStatusBar`
    - Test badge colors for each status value
    - Test running/stopped states and last sync time display
    - _Requirements: 13.2, 13.4_

  - [x] 13.4 Write tests for Work Requests API client and hooks
    - Test all API client methods
    - Test hook query/mutation behavior
    - _Requirements: 13.3_

- [x] 14. Final checkpoint - Quality gates and validation
  - Run `uv run ruff check --fix src/` and `uv run ruff format src/` (zero violations)
  - Run `uv run mypy src/` and `uv run pyright src/` (zero type errors)
  - Run `uv run pytest -v` (all tiers pass)
  - Run `cd frontend && npm test` (all frontend tests pass)
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation between phases
- Property tests validate universal correctness properties from the design document
- All 17 design properties are covered: Properties 1, 3-6, 17 in phase 3; Properties 12-13 in phase 5; Properties 2, 7-11, 14-16 in phase 12
- The backend uses Python 3.11+ / FastAPI / SQLAlchemy 2.0 async; frontend uses React 19 / TypeScript 5.9 / TanStack Query v5
- Agent-browser E2E validation scripts (Requirements 14.1–14.6) are documented in the design and can be run manually after deployment
