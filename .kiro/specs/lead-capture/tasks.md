# Tasks: Lead Capture (Website Form Submission)

## Task 1: Database Setup — Enums and Migration

- [x] 1.1 Add LeadStatus and LeadSituation enums to `models/enums.py`
  - Add LeadStatus enum: new, contacted, qualified, converted, lost, spam
  - Add LeadSituation enum: new_system, upgrade, repair, exploring
  - Add VALID_LEAD_STATUS_TRANSITIONS dict
  - **Validates: Requirement 4.4, 4.5, 6.2**

- [x] 1.2 Create leads table Alembic migration
  - Define leads table with all columns from design (id, name, phone, email, zip_code, situation, notes, source_site, status, assigned_to, customer_id, contacted_at, converted_at, created_at, updated_at)
  - Add foreign keys to staff(id) and customers(id) with ON DELETE SET NULL
  - Add indexes on phone, status, created_at, zip_code
  - **Validates: Requirement 4.1, 4.2, 4.3, 4.7**

- [x] 1.3 Create Lead SQLAlchemy model (`models/lead.py`)
  - Define Lead class with all columns matching migration
  - Add relationships to Staff and Customer (lazy="selectin")
  - Add __table_args__ with index definitions
  - **Validates: Requirement 4.1, 4.2**

- [x] 1.4 Test migration runs successfully
  - Run `alembic upgrade head` against test database
  - Verify leads table and indexes created
  - Verify foreign key constraints work
  - **Validates: Requirement 4.3, 4.7**

## Task 2: Pydantic Schemas

- [x] 2.1 Create lead schemas (`schemas/lead.py`)
  - Implement strip_html_tags utility function
  - Implement LeadSubmission schema with validators (phone normalization, zip validation, HTML sanitization, honeypot field)
  - Implement LeadSubmissionResponse schema
  - Implement LeadUpdate schema
  - Implement LeadResponse schema with enum converters
  - Implement LeadListParams schema
  - Implement PaginatedLeadResponse schema
  - Implement LeadConversionRequest schema
  - Implement LeadConversionResponse schema
  - **Validates: Requirement 1.1-1.11, 5.1-5.5, 7.1-7.6**

- [x] 2.2 Write schema validation unit tests
  - Test phone normalization (various formats → 10 digits)
  - Test phone rejection (invalid formats)
  - Test zip code validation (5 digits only)
  - Test situation enum validation
  - Test email validation (optional, valid format)
  - Test HTML tag stripping from name and notes
  - Test honeypot field acceptance (empty string)
  - Test max length constraints
  - **Validates: Requirement 1.2-1.7, 1.11**

## Task 3: Custom Exceptions

- [x] 3.1 Add lead exceptions to `exceptions/__init__.py`
  - Add LeadError base class
  - Add LeadNotFoundError (with lead_id attribute)
  - Add LeadAlreadyConvertedError (with lead_id attribute)
  - Add InvalidLeadStatusTransitionError (with current_status, requested_status attributes)
  - **Validates: Requirement 13.1-13.3**

- [x] 3.2 Register exception handlers in `app.py`
  - Add handler for LeadNotFoundError → 404
  - Add handler for LeadAlreadyConvertedError → 400
  - Add handler for InvalidLeadStatusTransitionError → 400
  - Follow existing exception handler patterns
  - **Validates: Requirement 13.5**

## Task 4: Repository Layer

- [x] 4.1 Create LeadRepository (`repositories/lead_repository.py`)
  - Implement __init__ with AsyncSession and LoggerMixin (DOMAIN="database")
  - Implement create(**kwargs) → Lead
  - Implement get_by_id(lead_id) → Lead | None
  - Implement get_by_phone_and_active_status(phone) → Lead | None (status in new, contacted, qualified)
  - Implement list_with_filters(params) → tuple[list[Lead], int] with filtering, search, pagination, sorting
  - Implement update(lead_id, update_data) → Lead
  - Implement delete(lead_id) → None
  - Implement count_new_today() → int
  - Implement count_uncontacted() → int
  - **Validates: Requirement 4, 5, 8**

- [x] 4.2 Write repository unit tests
  - Test create method
  - Test get_by_id (found and not found)
  - Test get_by_phone_and_active_status (matching and non-matching statuses)
  - Test list_with_filters (status filter, situation filter, date range, search, pagination)
  - Test update method
  - Test delete method
  - Test count_new_today and count_uncontacted
  - **Validates: Requirement 4, 5**

## Task 5: Service Layer

- [x] 5.1 Create LeadService (`services/lead_service.py`)
  - Implement __init__ with LeadRepository, CustomerService, JobService, StaffRepository dependencies and LoggerMixin (DOMAIN="lead")
  - Implement split_name(full_name) → (first_name, last_name) static method
  - **Validates: Requirement 7.1-7.2**

- [x] 5.2 Implement submit_lead method
  - Check honeypot field — if non-empty, log "lead.spam_detected" and return fake 201
  - Check for duplicate by phone + active status
  - If duplicate found: update existing lead (merge email/notes without overwriting with empty)
  - If no duplicate or existing is terminal: create new lead with status "new"
  - Log "lead.submitted" with lead_id and source_site only (no PII)
  - Return LeadSubmissionResponse
  - **Validates: Requirement 1, 2, 3, 15.1, 15.4**

- [x] 5.3 Implement get_lead and list_leads methods
  - get_lead: fetch by ID, raise LeadNotFoundError if not found
  - list_leads: delegate to repository with params, return PaginatedLeadResponse
  - **Validates: Requirement 5.1-5.5, 5.8**

- [x] 5.4 Implement update_lead method
  - Validate status transition against VALID_LEAD_STATUS_TRANSITIONS
  - If new status is "contacted" and contacted_at is null: set contacted_at
  - If new status is "converted": set converted_at
  - If assigning to staff: validate staff exists via staff_repository
  - Log "lead.status_changed" with lead_id, old_status, new_status
  - **Validates: Requirement 5.6-5.7, 6, 15.2**

- [x] 5.5 Implement convert_lead method
  - Fetch lead, verify not already converted (raise LeadAlreadyConvertedError)
  - Split name or use overrides from request
  - Create customer via CustomerService with source="website"
  - If create_job=True: create job via JobService with category/description mapped from situation
  - Update lead: status=converted, converted_at=now(), customer_id=new customer ID
  - Log "lead.converted" with lead_id, customer_id, job_id
  - Return LeadConversionResponse
  - **Validates: Requirement 7, 15.3**

- [x] 5.6 Implement delete_lead and get_dashboard_metrics methods
  - delete_lead: fetch lead, raise LeadNotFoundError if not found, delete
  - get_dashboard_metrics: return {"new_leads_today": int, "uncontacted_leads": int}
  - **Validates: Requirement 5.9, 8.1-8.2**

- [x] 5.7 Write service unit tests (mocked repository)
  - Test submit_lead: happy path, honeypot rejection, duplicate detection (update vs create)
  - Test get_lead: found and not found
  - Test list_leads: pagination
  - Test update_lead: valid transitions, invalid transitions, contacted_at auto-set, staff validation
  - Test convert_lead: happy path, already converted, name splitting, job creation toggle
  - Test delete_lead: found and not found
  - Test split_name: single word, two words, three+ words
  - Target 85%+ coverage
  - **Validates: Requirement 1-8, 13, 15**

## Task 6: API Layer

- [x] 6.1 Create lead API endpoints (`api/v1/leads.py`)
  - Implement POST "" (public, no auth) — submit_lead
  - Implement GET "" (admin auth) — list_leads with LeadListParams
  - Implement GET "/{lead_id}" (admin auth) — get_lead
  - Implement PATCH "/{lead_id}" (admin auth) — update_lead
  - Implement POST "/{lead_id}/convert" (admin auth) — convert_lead
  - Implement DELETE "/{lead_id}" (admin auth) — delete_lead
  - Create _get_lead_service helper for dependency injection
  - **Validates: Requirement 1.10, 5.10, 7.9, 12.3**

- [x] 6.2 Register leads router in `api/v1/router.py`
  - Import leads router
  - Include with prefix="/leads" and tags=["leads"]
  - **Validates: Design — Router Registration**

- [x] 6.3 Write API endpoint tests
  - Test POST /api/v1/leads (public, no auth): valid submission, validation errors, honeypot
  - Test GET /api/v1/leads (admin): pagination, filters, search
  - Test GET /api/v1/leads/{id} (admin): found, not found
  - Test PATCH /api/v1/leads/{id} (admin): status change, invalid transition
  - Test POST /api/v1/leads/{id}/convert (admin): success, already converted
  - Test DELETE /api/v1/leads/{id} (admin): success, not found
  - Test auth enforcement: admin endpoints reject unauthenticated requests
  - Target 80%+ coverage
  - **Validates: Requirement 1, 5, 7, 13**

## Task 7: Dashboard Integration

- [x] 7.1 Update DashboardMetrics schema (`schemas/dashboard.py`)
  - Add new_leads_today: int field with default 0
  - Add uncontacted_leads: int field with default 0
  - **Validates: Requirement 8.1-8.2**

- [x] 7.2 Update DashboardService (`services/dashboard_service.py`)
  - Add lead_repository parameter to __init__
  - Query lead counts in get_overview_metrics()
  - Include new_leads_today and uncontacted_leads in DashboardMetrics response
  - **Validates: Requirement 8.5**

- [x] 7.3 Update dashboard dependency injection
  - Ensure DashboardService receives LeadRepository in the API dependency
  - **Validates: Requirement 8.5**

- [x] 7.4 Write dashboard integration tests
  - Test that dashboard metrics include lead counts
  - Test count_new_today returns correct count
  - Test count_uncontacted returns correct count
  - **Validates: Requirement 8.1-8.2**

## Task 8: Backend Integration Tests

- [x] 8.1 Write lead submission → dashboard metrics integration test
  - Submit a lead via POST /api/v1/leads
  - Verify dashboard metrics reflect the new lead
  - **Validates: Requirement 8, 14.3**

- [x] 8.2 Write lead lifecycle integration test
  - Submit lead → list leads → update status → convert to customer
  - Verify customer created with correct data
  - Verify lead status is "converted" with customer_id linked
  - **Validates: Requirement 1, 5, 6, 7, 14.3**

- [x] 8.3 Write duplicate detection integration test
  - Submit lead with phone X → submit again with same phone X
  - Verify only one lead exists (updated, not duplicated)
  - Submit again after converting first lead → verify new lead created
  - **Validates: Requirement 3, 14.3**

## Task 9: Property-Based Tests

- [x] 9.1 Write phone normalization idempotency PBT
  - Generate phone strings with digits, parens, dashes, spaces, dots
  - Filter to valid 10-digit results
  - Assert normalize(normalize(p)) == normalize(p)
  - **PBT: Property 1 — Validates: Requirement 1.2**

- [x] 9.2 Write status transition validity PBT
  - Generate all (LeadStatus, LeadStatus) pairs
  - Assert valid transitions succeed and invalid transitions raise InvalidLeadStatusTransitionError
  - Assert terminal states (converted, spam) have empty transition sets
  - **PBT: Property 2 — Validates: Requirement 6.2-6.3**

- [x] 9.3 Write duplicate detection correctness PBT
  - Generate sequences of (phone, existing_status) pairs
  - Assert lead count invariants: no increase for active duplicates, increase for terminal/new
  - **PBT: Property 3 — Validates: Requirement 3.1-3.5**

- [x] 9.4 Write input sanitization completeness PBT
  - Generate arbitrary strings including HTML-like patterns
  - Assert strip_html_tags is idempotent
  - Assert output contains no substrings matching <[^>]+>
  - **PBT: Property 4 — Validates: Requirement 1.11, 12.4**

- [x] 9.5 Write name splitting consistency PBT
  - Generate name strings with 1-4 space-separated words
  - Assert first_name is non-empty
  - Assert re-splitting produces same result
  - Assert single-word names produce (word, "")
  - **PBT: Property 5 — Validates: Requirement 7.1-7.2**

- [x] 9.6 Write honeypot transparency PBT
  - Generate valid submission payloads
  - Submit with empty and non-empty honeypot values
  - Assert response shape is identical (no information leakage)
  - Assert storage behavior differs (created vs not created)
  - **PBT: Property 6 — Validates: Requirement 2.1, 2.4**

## Task 10: Checkpoint — Backend Complete

- [x] 10.1 Run all backend quality checks
  - `uv run ruff check src/` — zero violations
  - `uv run mypy src/` — zero errors
  - `uv run pyright src/` — zero errors
  - `uv run pytest -v` — all tests passing
  - Verify 85%+ coverage on LeadService, 80%+ on API endpoints, 80%+ on LeadRepository
  - Verify all existing tests still pass (no regressions)
  - **Validates: Requirement 14.10, 14.11**

## Task 11: Frontend — Types, API Client, and Hooks

- [x] 11.1 Create lead TypeScript types (`features/leads/types/index.ts`)
  - Define LeadStatus, LeadSituation types
  - Define Lead, LeadListParams, PaginatedLeadResponse interfaces
  - Define LeadConversionRequest, LeadConversionResponse interfaces
  - **Validates: Design — Frontend Types**

- [x] 11.2 Create lead API client (`features/leads/api/leadApi.ts`)
  - Implement list, getById, update, convert, delete methods
  - Use existing apiClient from core
  - **Validates: Design — API Client**

- [x] 11.3 Create lead query key factory and hooks
  - Create leadKeys factory (all, lists, list, details, detail)
  - Create useLeads hook (list with params)
  - Create useLead hook (single lead by ID)
  - Create useUpdateLead mutation hook with cache invalidation
  - Create useConvertLead mutation hook with cache invalidation
  - Create useDeleteLead mutation hook with cache invalidation
  - **Validates: Design — Query Keys and Hooks**

## Task 12: Frontend — Lead Components

- [x] 12.1 Create LeadStatusBadge and LeadSituationBadge components
  - LeadStatusBadge: color-coded badge for all 6 statuses (new=blue, contacted=yellow, qualified=purple, converted=green, lost=gray, spam=red)
  - LeadSituationBadge: label badge for all 4 situations
  - Add data-testid attributes
  - **Validates: Requirement 9.5**

- [x] 12.2 Create LeadFilters component
  - Status filter dropdown
  - Situation filter dropdown
  - Date range picker
  - Search input (name/phone)
  - Add data-testid attributes
  - **Validates: Requirement 9.4**

- [x] 12.3 Create LeadsList page component
  - Data table with columns: Name, Phone, Situation, Status, Zip Code, Submitted (relative time), Assigned To
  - Integrate LeadFilters
  - Pagination controls
  - Row click navigates to lead detail
  - Default sort by submitted date descending
  - Add data-testid attributes (leads-page, leads-table, lead-row)
  - **Validates: Requirement 9.3, 9.6, 9.7**

- [x] 12.4 Create ConvertLeadDialog component
  - Pre-fill first_name/last_name from auto-split of lead name
  - Editable name fields
  - Toggle for "Create job during conversion" with auto-suggested job type
  - Submit button triggers useConvertLead mutation
  - On success: navigate to new customer detail page
  - Add data-testid attributes
  - **Validates: Requirement 10.5-10.8**

- [x] 12.5 Create LeadDetail page component
  - Display all lead fields: name, phone, email, zip, situation, notes, source_site, timestamps
  - Status dropdown to change status
  - Staff assignment selector
  - "Mark as Contacted" button (when status is "new")
  - "Convert to Customer" button (opens ConvertLeadDialog)
  - "Mark as Lost" and "Mark as Spam" buttons
  - When converted: show links to customer and job
  - Add data-testid attributes
  - **Validates: Requirement 10.1-10.10**

## Task 13: Frontend — Navigation, Routing, and Dashboard Widget

- [x] 13.1 Add Leads navigation tab to Layout.tsx
  - Add "Leads" item to sidebar with funnel icon (Funnel from lucide-react)
  - Add badge showing count of "new" leads (from dashboard metrics uncontacted_leads)
  - Badge disappears when count is 0
  - Add data-testid="nav-leads"
  - **Validates: Requirement 9.1, 9.2**

- [x] 13.2 Add lead routes to router
  - Add /leads route → LeadsList component
  - Add /leads/:id route → LeadDetail component
  - **Validates: Design — Router Integration**

- [x] 13.3 Add "New Leads" card to DashboardPage
  - Display new_leads_today and uncontacted_leads counts
  - Color-coding: green (0 uncontacted), yellow (1-5), red (6+)
  - Click navigates to /leads?status=new
  - Add data-testid="leads-metric"
  - **Validates: Requirement 11.1-11.3**

- [x] 13.4 Add lead activity to Recent Activity feed
  - Display "lead_submitted" events with lead name and situation
  - Click navigates to lead detail page
  - **Validates: Requirement 11.4-11.5**

- [x] 13.5 Create public exports (`features/leads/index.ts`)
  - Export all components, hooks, types, and API client
  - **Validates: Design — Feature Slice Structure**

## Task 14: Frontend Tests

- [x] 14.1 Write LeadStatusBadge and LeadSituationBadge tests
  - Test all 6 status colors render correctly
  - Test all 4 situation labels render correctly
  - **Validates: Requirement 14.5**

- [x] 14.2 Write LeadsList component tests
  - Test table renders with mock data
  - Test loading state
  - Test empty state
  - Test row click navigation
  - Test filter interactions
  - **Validates: Requirement 14.5**

- [x] 14.3 Write LeadDetail component tests
  - Test all fields render
  - Test status change dropdown
  - Test action buttons visibility based on status
  - Test converted lead shows customer/job links
  - **Validates: Requirement 14.5**

- [x] 14.4 Write ConvertLeadDialog tests
  - Test name pre-fill from auto-split
  - Test form submission
  - Test job creation toggle
  - **Validates: Requirement 14.5**

- [x] 14.5 Write hook tests (useLeads, useLead, useConvertLead)
  - Test query behavior
  - Test mutation behavior
  - Test cache invalidation
  - **Validates: Requirement 14.6**

## Task 15: Checkpoint — Frontend Complete

- [x] 15.1 Run all frontend quality checks
  - `cd frontend && npm run lint` — zero violations
  - `cd frontend && npm run typecheck` — zero errors
  - `cd frontend && npm test` — all tests passing
  - Verify 80%+ coverage on lead-related components
  - Verify all existing frontend tests still pass (no regressions)
  - **Validates: Requirement 14.10, 14.12**

## Task 16: Agent-Browser E2E Validation — Public Form Submission

- [x] 16.1 Validate public form submission on live site
  - `agent-browser open https://grins-irrigation.vercel.app/`
  - Scroll to "Get Your Free Design" form
  - Fill name, phone, zip code, select situation from dropdown
  - Submit the form
  - Verify success message appears on the page
  - **Validates: Requirement 14.7**

- [x] 16.2 Validate submitted lead appears in admin dashboard
  - `agent-browser open http://localhost:5173/leads`
  - Verify the lead just submitted from the live form appears in the leads table
  - Verify status is "new" and data matches what was submitted
  - **Validates: Requirement 14.7**

- [x] 16.3 Validate dashboard widget reflects new lead
  - `agent-browser open http://localhost:5173/`
  - Verify "New Leads" card shows updated count
  - Click the card
  - Verify navigation to leads list filtered by status=new
  - **Validates: Requirement 14.9**

## Task 17: Agent-Browser E2E Validation — Lead Management

- [x] 17.1 Validate lead detail view
  - Navigate to a lead's detail page
  - Verify all fields render (name, phone, email, zip, situation, notes, status, timestamps)
  - Verify action buttons are present (Mark as Contacted, Convert, Mark as Lost, Mark as Spam)
  - **Validates: Requirement 14.8**

- [x] 17.2 Validate lead status change
  - Open a lead with status "new"
  - Click "Mark as Contacted"
  - Verify status badge updates to "contacted"
  - Verify contacted_at timestamp appears
  - **Validates: Requirement 14.8**

- [x] 17.3 Validate lead conversion flow
  - Open a lead (set to "qualified" status first if needed)
  - Click "Convert to Customer"
  - Verify dialog pre-fills first/last name from auto-split
  - Toggle job creation on
  - Submit conversion
  - Verify navigation to new customer detail page
  - **Validates: Requirement 14.8**

- [x] 17.4 Validate converted lead shows links
  - Navigate back to the converted lead's detail page
  - Verify status shows "converted"
  - Verify links to created customer and job are visible and clickable
  - **Validates: Requirement 14.8**

## Task 18: Agent-Browser E2E Validation — Filtering and Cleanup

- [x] 18.1 Validate lead filtering and search
  - On leads list page, filter by status → verify table updates
  - Search by name → verify results
  - Filter by situation → verify results
  - Clear filters → verify all leads shown
  - **Validates: Requirement 14.8**

- [x] 18.2 Validate lead deletion
  - Open a spam/test lead
  - Delete it
  - Verify it disappears from the list
  - **Validates: Requirement 14.8**

## Task 19: Final Quality Check and Documentation

- [x] 19.1 Run full backend quality suite
  - `uv run ruff check src/` — zero violations
  - `uv run mypy src/` — zero errors
  - `uv run pyright src/` — zero errors
  - `uv run pytest -v` — all tests passing (including all PBT)
  - **Validates: Requirement 14.10**

- [x] 19.2 Run full frontend quality suite
  - `cd frontend && npm run lint` — zero violations
  - `cd frontend && npm run typecheck` — zero errors
  - `cd frontend && npm test` — all tests passing
  - **Validates: Requirement 14.10**

- [x] 19.3 Update DEVLOG.md
  - Document lead capture implementation
  - Document decisions made and any deviations from design
  - Document test results and coverage
