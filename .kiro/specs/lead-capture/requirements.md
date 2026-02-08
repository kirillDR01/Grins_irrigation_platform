# Requirements Document: Lead Capture (Website Form Submission)

## Introduction

The Lead Capture feature enables the Grin's Irrigation Platform to receive and manage leads from the public-facing landing page (grins-irrigation.vercel.app). When a visitor fills out the "Get Your Free Design" form, the submission hits a public API endpoint, stores the lead in a dedicated `leads` table, and surfaces it in the admin dashboard. This replaces the current manual process where Viktor receives form submissions via email/text and manually tracks them in spreadsheets.

The feature spans three areas: a public API endpoint for form intake, backend lead management (CRUD, status workflow, conversion to customer), and a new Leads tab in the admin dashboard frontend.

## Glossary

- **Lead**: A prospect who has submitted the website form but is not yet a confirmed customer
- **Customer**: A confirmed client in the existing `customers` table with contact info and service history
- **Conversion**: The process of turning a lead into a customer record (and optionally a job)
- **Situation**: The lead's self-described need from the form dropdown (new system, upgrade, repair, exploring)
- **Honeypot**: A hidden form field used for bot detection — real users never see or fill it
- **Source_Site**: A free-text identifier for which website/landing page the lead came from
- **Lead_Status**: The lifecycle stage of a lead (new, contacted, qualified, converted, lost, spam)

## Requirements

### Requirement 1: Lead Submission (Public API)

**User Story:** As a website visitor, I want to submit my contact information and service needs through the landing page form, so that Grin's Irrigation can follow up with me about a free design consultation.

#### Acceptance Criteria

1. WHEN a visitor submits the form with valid data (name, phone, zip_code, situation), THE System SHALL create a new lead record and return HTTP 201 with a success message
2. WHEN a visitor submits a phone number in any format (parentheses, dashes, spaces), THE System SHALL normalize it to 10 digits before storage
3. WHEN a visitor submits a phone number that does not resolve to exactly 10 digits, THE System SHALL reject the request with a validation error
4. WHEN a visitor submits a zip code that is not exactly 5 digits, THE System SHALL reject the request with a validation error
5. WHEN a visitor submits a situation value not in the allowed enum (new_system, upgrade, repair, exploring), THE System SHALL reject the request with a validation error
6. WHEN a visitor optionally provides an email, THE System SHALL validate it against standard email format
7. WHEN a visitor optionally provides notes, THE System SHALL accept up to 1000 characters
8. WHEN a visitor does not provide source_site, THE System SHALL default it to "residential"
9. THE System SHALL store the lead with status "new" and created_at/updated_at timestamps
10. THE `POST /api/v1/leads` endpoint SHALL NOT require authentication (public endpoint)
11. THE System SHALL strip HTML tags from name and notes fields to prevent stored XSS
12. THE System SHALL NOT log PII (phone, email, name) — only lead_id in log events

### Requirement 2: Honeypot Bot Detection

**User Story:** As a system administrator, I want basic bot protection on the public form endpoint, so that spam submissions don't pollute the leads database.

#### Acceptance Criteria

1. WHEN a submission includes a non-empty honeypot field (named "website"), THE System SHALL silently reject it by returning HTTP 201 (fake success) without storing the lead
2. WHEN a submission includes an empty or missing honeypot field, THE System SHALL process the lead normally
3. WHEN a bot submission is detected, THE System SHALL log the event as "lead.spam_detected" with the lead's source_site (no PII)
4. THE System SHALL NOT reveal to the submitter that the honeypot was triggered (always return success)

### Requirement 3: Duplicate Lead Detection

**User Story:** As a business owner, I want the system to handle duplicate form submissions intelligently, so that the same person submitting twice doesn't create clutter but returning prospects get a fresh opportunity.

#### Acceptance Criteria

1. WHEN a lead is submitted with a phone number matching an existing lead with status "new" or "contacted", THE System SHALL update the existing lead (refresh updated_at, merge email/notes if provided) instead of creating a duplicate
2. WHEN a lead is submitted with a phone number matching an existing lead with status "qualified", THE System SHALL update the existing lead
3. WHEN a lead is submitted with a phone number matching an existing lead with status "converted" or "lost", THE System SHALL create a new lead record (fresh opportunity)
4. WHEN a lead is submitted with a phone number matching an existing lead with status "spam", THE System SHALL create a new lead record (second chance)
5. WHEN an existing lead is updated via duplicate detection, THE System SHALL merge non-null optional fields (email, notes) without overwriting existing values with empty ones

### Requirement 4: Lead Data Model

**User Story:** As a system administrator, I want a dedicated leads table separate from customers, so that prospects are tracked independently until they convert.

#### Acceptance Criteria

1. THE System SHALL store leads in a separate `leads` table with UUID primary keys
2. THE System SHALL store: name (VARCHAR 200), phone (VARCHAR 20), email (VARCHAR 255 nullable), zip_code (VARCHAR 10), situation (enum), notes (TEXT nullable), source_site (VARCHAR 100), status (enum), assigned_to (FK to staff, nullable), customer_id (FK to customers, nullable), contacted_at (nullable), converted_at (nullable), created_at, updated_at
3. THE System SHALL create database indexes on phone, status, created_at, and zip_code columns
4. THE System SHALL support the LeadStatus enum: new, contacted, qualified, converted, lost, spam
5. THE System SHALL support the LeadSituation enum: new_system, upgrade, repair, exploring
6. THE System SHALL store source_site as a free string (not an enum) to support future sites without code changes
7. THE System SHALL enforce foreign key relationships to staff (assigned_to) and customers (customer_id)

### Requirement 5: Lead Management (Admin CRUD)

**User Story:** As a business owner, I want to view, filter, update, and manage leads from the admin dashboard, so that I can track follow-ups and move leads through the sales pipeline.

#### Acceptance Criteria

1. WHEN an admin requests the lead list, THE System SHALL return paginated results sorted by created_at descending (newest first)
2. WHEN an admin filters by status, THE System SHALL return only leads matching that status
3. WHEN an admin filters by situation, THE System SHALL return only leads matching that situation
4. WHEN an admin filters by date range, THE System SHALL return only leads created within that range
5. WHEN an admin searches by name or phone, THE System SHALL return matching leads (case-insensitive for name)
6. WHEN an admin updates a lead's status to "contacted", THE System SHALL automatically set contacted_at to the current timestamp
7. WHEN an admin assigns a lead to a staff member, THE System SHALL validate the staff member exists
8. WHEN an admin retrieves a single lead by ID, THE System SHALL return the complete lead record including staff assignment and linked customer (if converted)
9. WHEN an admin deletes a lead, THE System SHALL remove the record
10. ALL lead management endpoints (GET, PATCH, DELETE) SHALL require admin authentication

### Requirement 6: Lead Status Workflow

**User Story:** As a business owner, I want leads to follow a clear status workflow, so that I can track where each lead is in the pipeline and ensure timely follow-up.

#### Acceptance Criteria

1. WHEN a lead is created via form submission, THE System SHALL set status to "new"
2. THE System SHALL support the following status transitions:
   - new → contacted, qualified, lost, spam
   - contacted → qualified, lost, spam
   - qualified → converted, lost
   - converted → (terminal state, no further transitions)
   - lost → new (re-engagement)
   - spam → (terminal state, no further transitions)
3. WHEN an admin attempts an invalid status transition, THE System SHALL reject the request with a descriptive error
4. WHEN a lead status changes to "converted", THE System SHALL set converted_at to the current timestamp
5. WHEN a lead status changes to "contacted" and contacted_at is null, THE System SHALL set contacted_at to the current timestamp

### Requirement 7: Lead Conversion to Customer

**User Story:** As a business owner, I want to convert a qualified lead into a customer (and optionally a job), so that the lead's information flows into the existing customer management system without re-entry.

#### Acceptance Criteria

1. WHEN an admin converts a lead, THE System SHALL auto-split the lead's name into first_name and last_name by splitting on the first space
2. WHEN the lead's name contains no space, THE System SHALL set first_name to the full name and last_name to empty string
3. WHEN the admin provides first_name/last_name overrides in the conversion request, THE System SHALL use those instead of auto-split
4. WHEN a lead is converted, THE System SHALL create a new customer record via the existing CustomerService with source set to "website"
5. WHEN the conversion request includes job details, THE System SHALL create a job linked to the new customer with the appropriate category based on situation:
   - new_system → requires_estimate (Installation Estimate)
   - upgrade → requires_estimate (System Upgrade Estimate)
   - repair → ready_to_schedule (Repair Request)
   - exploring → requires_estimate (Consultation)
6. WHEN a lead is successfully converted, THE System SHALL update the lead's status to "converted", set converted_at, and link customer_id
7. WHEN an admin attempts to convert a lead that is already converted, THE System SHALL reject the request with a LeadAlreadyConvertedError
8. WHEN customer creation fails (e.g., duplicate phone in customers table), THE System SHALL return the error without changing the lead's status
9. THE conversion endpoint SHALL require admin authentication

### Requirement 8: Dashboard Integration

**User Story:** As a business owner, I want to see new lead activity on my dashboard at a glance, so that I can respond quickly to incoming prospects and not miss opportunities.

#### Acceptance Criteria

1. THE System SHALL add `new_leads_today` (leads submitted today with status "new") to the DashboardMetrics response
2. THE System SHALL add `uncontacted_leads` (all leads with status "new") to the DashboardMetrics response
3. THE System SHALL include "lead_submitted" as a valid activity_type in the RecentActivity feed
4. WHEN a new lead is submitted, THE System SHALL create a recent activity entry with description "New lead from {name} ({situation})"
5. THE dashboard metrics endpoint SHALL return lead counts alongside existing customer/job/appointment metrics

### Requirement 9: Frontend — Leads Management Tab

**User Story:** As a business owner, I want a dedicated Leads tab in the admin dashboard, so that I can view, filter, and manage all incoming leads in one place.

#### Acceptance Criteria

1. THE admin dashboard SHALL include a "Leads" navigation tab with a funnel/inbox icon
2. THE Leads tab SHALL display a badge showing the count of leads with status "new" (disappears when count is 0)
3. THE Leads list page SHALL display a data table with columns: Name, Phone, Situation, Status, Zip Code, Submitted (relative time), Assigned To
4. THE Leads list page SHALL support filtering by status, situation, date range, and search by name/phone
5. THE Status column SHALL display color-coded badges: new=blue, contacted=yellow, qualified=purple, converted=green, lost=gray, spam=red
6. THE table SHALL default sort by submitted date descending (newest first)
7. WHEN a user clicks a lead row, THE System SHALL navigate to the lead detail view

### Requirement 10: Frontend — Lead Detail View

**User Story:** As a business owner, I want to see full lead details and take actions (contact, convert, mark as lost), so that I can manage each lead through the pipeline efficiently.

#### Acceptance Criteria

1. THE lead detail view SHALL display: name, phone, email, zip code, situation (with description), notes, source site, submitted date/time
2. THE lead detail view SHALL display current status with a dropdown to change it
3. THE lead detail view SHALL display assigned staff with a selector to reassign
4. THE lead detail view SHALL show a "Mark as Contacted" button when status is "new"
5. THE lead detail view SHALL show a "Convert to Customer" button that opens a conversion dialog
6. THE conversion dialog SHALL pre-fill first_name/last_name from auto-split of the lead's name, with editable fields
7. THE conversion dialog SHALL offer an option to create a job during conversion with auto-suggested job type based on situation
8. WHEN conversion succeeds, THE System SHALL navigate to the new customer's detail page
9. THE lead detail view SHALL show a "Mark as Lost" button and a "Mark as Spam" button
10. WHEN a lead has been converted, THE detail view SHALL display links to the created customer and job

### Requirement 11: Frontend — Dashboard Lead Widget

**User Story:** As a business owner, I want a "New Leads" card on the main dashboard, so that I immediately see when new leads need attention.

#### Acceptance Criteria

1. THE dashboard SHALL display a "New Leads" card showing new_leads_today and uncontacted_leads counts
2. THE card SHALL be color-coded: green (0 uncontacted), yellow (1-5 uncontacted), red (6+ uncontacted)
3. WHEN a user clicks the card, THE System SHALL navigate to the Leads list page filtered by status=new
4. THE Recent Activity feed SHALL display "lead_submitted" events with lead name and situation
5. WHEN a user clicks a lead activity item, THE System SHALL navigate to that lead's detail page

### Requirement 12: CORS and Security

**User Story:** As a system administrator, I want the public lead endpoint to be secure and accessible from the landing page domain, so that form submissions work correctly without exposing the system to abuse.

#### Acceptance Criteria

1. THE System SHALL accept requests from the landing page domain (grins-irrigation.vercel.app) via existing CORS configuration
2. THE System SHALL NOT require any code changes for CORS — the landing page domain must be in the CORS_ORIGINS environment variable
3. THE public POST endpoint SHALL validate all input fields strictly (phone format, zip format, enum values, string lengths)
4. THE System SHALL sanitize text inputs (name, notes) by stripping HTML tags
5. THE System SHALL NOT implement rate limiting in v1 (deferred to future iteration)

### Requirement 13: Exception Handling

**User Story:** As an API consumer, I want clear error responses when something goes wrong, so that I can handle errors gracefully in the frontend.

#### Acceptance Criteria

1. WHEN a lead is not found by ID, THE System SHALL return HTTP 404 with a LeadNotFoundError
2. WHEN an admin attempts to convert an already-converted lead, THE System SHALL return HTTP 400 with a LeadAlreadyConvertedError
3. WHEN an admin attempts an invalid status transition, THE System SHALL return HTTP 400 with an InvalidLeadStatusTransitionError
4. WHEN validation fails on the public endpoint, THE System SHALL return HTTP 422 with detailed field-level errors
5. ALL lead-related exceptions SHALL be registered as global exception handlers in app.py following existing patterns

### Requirement 14: Comprehensive Testing and Validation

**User Story:** As a developer, I want thorough test coverage across all tiers and end-to-end UI validation, so that every component of the lead capture feature is proven correct before deployment.

#### Acceptance Criteria

1. ALL backend services (LeadService, LeadRepository) SHALL have unit tests with mocked dependencies covering happy paths, validation failures, and edge cases
2. ALL backend API endpoints SHALL have functional tests using a real test database verifying request/response contracts, status codes, and data persistence
3. ALL backend cross-component flows (lead submission → duplicate detection → dashboard metrics) SHALL have integration tests verifying the full pipeline
4. ALL property-based tests SHALL validate core invariants: phone normalization idempotency, status transition validity, duplicate detection correctness, and input sanitization completeness
5. ALL frontend components (LeadsList, LeadDetail, ConversionDialog, LeadWidget) SHALL have Vitest unit tests covering rendering, user interactions, and state management
6. ALL frontend API hooks (useLeads, useCreateLead, useConvertLead) SHALL have tests verifying query/mutation behavior and cache invalidation
7. THE lead submission flow SHALL be validated end-to-end using agent-browser: navigate to the landing page form, submit a lead, verify it appears in the admin dashboard Leads tab
8. THE lead detail and conversion flow SHALL be validated end-to-end using agent-browser: open a lead, change status, convert to customer, verify navigation to customer detail
9. THE dashboard lead widget SHALL be validated using agent-browser: verify new leads card renders, color-coding works, and click-through navigates to filtered leads list
10. ALL existing tests across the platform SHALL continue to pass after lead capture implementation (no regressions)
11. Backend test coverage for lead-related code SHALL meet or exceed 85% for services, 80% for API endpoints, and 80% for repositories
12. Frontend test coverage for lead-related components SHALL meet or exceed 80%

### Requirement 15: Logging and Observability

**User Story:** As a system administrator, I want structured logging for all lead operations, so that I can monitor lead flow, debug issues, and track conversion metrics.

#### Acceptance Criteria

1. WHEN a lead is submitted, THE System SHALL log "lead.submitted" at INFO level with lead_id and source_site
2. WHEN a lead status changes, THE System SHALL log "lead.status_changed" at INFO level with lead_id, old_status, new_status
3. WHEN a lead is converted, THE System SHALL log "lead.converted" at INFO level with lead_id, customer_id, job_id (if created)
4. WHEN a honeypot bot is detected, THE System SHALL log "lead.spam_detected" at WARNING level with source_site
5. WHEN a lead operation fails, THE System SHALL log at ERROR level with lead_id and error details
6. THE System SHALL use the "lead" domain namespace following existing structured logging patterns
7. THE System SHALL NOT include PII (name, phone, email) in any log entries
