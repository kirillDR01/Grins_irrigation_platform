# Requirements Document — CRM Gap Closure

## Introduction

This spec addresses all 123 items identified in the gap analysis (`to_do/gap_analysis.md`), covering every NOT DONE, PARTIAL, and UNABLE TO VERIFY item across the CRM and System Requirements. Items already marked DONE are included as verification-only requirements to confirm they remain functional. The scope spans: CRM cleanup, Dashboard improvements, Customer enhancements, Leads pipeline overhaul, Work Requests consolidation, Jobs UI changes, Schedule creation and staff features, Invoice improvements, Lead Intake system, Scheduling system, Sales dashboard, Accounting dashboard, and Marketing dashboard.

Testing is the #1 priority. Every requirement group includes automated test requirements (unit/functional/integration) AND agent-browser E2E validation scripts. All features must be verifiable via autonomous overnight execution without human supervision.

Items already covered by existing specs (`service-package-purchases`, `backend-frontend-integration-gaps`) are cross-referenced but NOT duplicated. This spec covers only the remaining gaps.

**CRITICAL ENVIRONMENT CONSTRAINT:** ALL work in this spec MUST be performed exclusively on the `dev` branch and in the development environment. No changes shall be pushed to the `main` branch or deployed to production until the entire spec is implemented, all tests pass, and explicit approval is given by the Admin (Viktor) to merge to main. All migrations, code changes, dependency additions, infrastructure modifications, and test executions occur on `dev` only. The `main` branch remains untouched and production-safe throughout the entire implementation.

**CRITICAL PRESERVATION CONSTRAINT:** The service package agreement flow — including the `service_agreement_tiers` table, the Stripe checkout/webhook integration, the onboarding consent flow, the agreement-to-job generation pipeline, and all related models (`ServiceAgreement`, `ServiceAgreementTier`, `AgreementJob`), services, and frontend components — is fully functional and MUST NOT be modified, refactored, or disrupted by any work in this spec. Any new feature that touches adjacent systems (invoicing, jobs, customers, Stripe) MUST preserve the existing agreement flow behavior exactly as-is. Regression tests for the agreement flow are mandatory before and after any related changes.

## Glossary

- **Platform**: The Grins Irrigation Platform backend (FastAPI + PostgreSQL) and admin frontend (React 19)
- **Admin**: Viktor, the sole administrator who manages all operations via the admin dashboard
- **Staff**: Field technicians who perform on-site irrigation work
- **CRM**: The admin-facing Customer Relationship Management interface
- **Dashboard_Page**: The main CRM dashboard at `/dashboard` showing alerts, metrics, and status summaries
- **Customer_Service**: Backend service for customer CRUD, duplicate detection, merge, notes, and photo management
- **Customer_Detail_View**: Frontend page showing a single customer's full information, notes, photos, invoices, and service history
- **Lead_Service**: Backend service for lead creation, tagging, estimates, contracts, bulk outreach, and conversion
- **Leads_Page**: Frontend page at `/leads` showing the leads table with filters, tags, and actions
- **Job_Service**: Backend service for job CRUD, notes, status management, and filtering
- **Job_List_View**: Frontend page at `/jobs` showing the jobs table with columns and filters
- **Schedule_Page**: Frontend page at `/schedule` showing the calendar, appointment forms, and staff features
- **Appointment_Service**: Backend service for appointment CRUD, status transitions, and staff workflow
- **Invoice_Service**: Backend service for invoice CRUD, reminders, lien tracking, and bulk notifications
- **Invoice_Page**: Frontend page at `/invoices` showing the invoice list with filters and actions
- **Sales_Dashboard**: New frontend page at `/sales` for estimate management, approval tracking, and revenue pipeline
- **Estimate_Service**: Backend service for estimate creation, templates, pricing tiers, and customer approval workflow
- **Accounting_Dashboard**: New frontend page at `/accounting` for financial metrics, invoicing automation, expense tracking, and tax reporting
- **Accounting_Service**: Backend service for financial aggregation, expense tracking, margin calculation, and tax reporting
- **Marketing_Dashboard**: New frontend page at `/marketing` for lead source analytics, CAC calculation, campaign management, and budget tracking
- **Campaign_Service**: Backend service for email/SMS campaign creation, scheduling, automation rules, and performance tracking
- **Photo_Service**: Backend service for file upload, storage (S3-compatible), and retrieval of customer/job photos and receipts
- **Notification_Service**: Backend service for automated push notifications via SMS/email triggered by system events
- **Staff_Workflow**: The structured multi-step process staff follow during on-site appointments
- **E2E_Test**: An agent-browser validation script that verifies frontend functionality through browser automation
- **Data_Testid**: HTML `data-testid` attributes used for reliable E2E test element selection
- **Service_Agreement_Flow**: The existing, fully functional pipeline for service package purchases: Stripe checkout → webhook processing → agreement creation → automatic job generation. This flow is OFF-LIMITS for modification in this spec.

---

## Requirements

---

### Requirement 1: Remove Fake/Test Data

**User Story:** As an Admin, I want all demo seed data removed from the production database, so that the CRM contains only real customer, staff, and job records.

**Gap Refs:** CRM Overall #1, #2

#### Acceptance Criteria

1. THE Platform SHALL provide a reversible migration that removes all records created by `20250626_100000_seed_demo_data.py` and `20250627_100000_seed_staff_availability.py` seed migrations
2. THE Platform SHALL deactivate or delete the seed migration files so they cannot be re-run in production
3. WHEN the cleanup migration runs, THE Platform SHALL log each deleted record type and count using structured logging with event `data.cleanup.seed_removed`
4. THE Platform SHALL preserve all non-seed records created after the initial deployment

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying the cleanup migration removes exactly the expected seed record counts
6. THE Platform SHALL include a functional test confirming no seed customer, staff, or job records exist after migration
7. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/customers`, `/staff`, and `/jobs` and verifies no demo names (e.g., "Demo Customer", "Test Staff") appear in the lists

---

### Requirement 2: Fix Random Logout Issue

**User Story:** As an Admin, I want the system to maintain my authenticated session while I am actively using it, so that I am not randomly logged out during work.

**Gap Refs:** CRM Overall #3

#### Acceptance Criteria

1. THE Platform SHALL implement token refresh logic that extends the session when the Admin is actively making API requests within the token validity window
2. WHEN the frontend detects a 401 response, THE Platform SHALL attempt a silent token refresh before redirecting to the login page
3. IF the token refresh fails, THEN THE Platform SHALL redirect to the login page and display a message explaining the session expired
4. THE Platform SHALL log all authentication failures and token refresh attempts using structured logging with event `auth.session.refresh_attempted` and `auth.session.refresh_failed`

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying the token refresh endpoint extends session validity
6. THE Platform SHALL include a functional test simulating an expired token scenario and confirming silent refresh succeeds
7. THE Platform SHALL include an E2E_Test using agent-browser that logs in, waits for a configurable period, performs an action, and verifies the session remains active without redirect to login

---

### Requirement 3: Dashboard Alert Navigation with Highlighting

**User Story:** As an Admin, I want to click a dashboard alert and be taken directly to the relevant section with the specific item highlighted, so that I can act on alerts without manual searching.

**Gap Refs:** CRM Dashboard #1, #4, #6

#### Acceptance Criteria

1. WHEN the Admin clicks an alert on the Dashboard_Page, THE Platform SHALL navigate to the target page with query parameters specifying the filter criteria (e.g., `/jobs?status=requested&highlight=job-123`)
2. WHEN the Job_List_View receives URL query parameters for status, THE Job_List_View SHALL auto-apply those filters on page load
3. WHEN the Leads_Page receives URL query parameters for status, THE Leads_Page SHALL auto-apply those filters on page load
4. WHEN a `highlight` query parameter is present, THE target page SHALL visually highlight the specified item row with a temporary background color animation for 3 seconds
5. WHEN the Admin clicks a job status count on the Dashboard_Page, THE Platform SHALL navigate to `/jobs?status={clicked_status}` with the corresponding filter applied
6. WHEN the Admin clicks the "New Leads" card on the Dashboard_Page, THE Platform SHALL navigate to `/leads?status=new` with the filter applied and uncontacted leads highlighted

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying URL query parameter parsing and filter application for Job_List_View and Leads_Page
8. THE Platform SHALL include an E2E_Test using agent-browser that: opens `/dashboard`, clicks an alert card, verifies navigation to the correct page, verifies the filter is applied, and verifies the highlight animation is visible on the target row

---

### Requirement 4: Dashboard Messages Widget

**User Story:** As an Admin, I want the dashboard to show a count of messages needing to be addressed, so that I can see at a glance how many customer communications require my attention.

**Gap Refs:** CRM Dashboard #2

#### Acceptance Criteria

1. THE Dashboard_Page SHALL display a "Messages" widget showing the count of unaddressed customer communications
2. THE Platform SHALL expose a GET /api/v1/communications/unaddressed-count endpoint that returns the count of communications not yet marked as addressed
3. WHEN the Admin clicks the Messages widget, THE Platform SHALL navigate to a communications queue page showing all unaddressed messages
4. THE Platform SHALL store communication records with fields: id (UUID), customer_id (FK), channel (SMS, EMAIL, PHONE), direction (INBOUND, OUTBOUND), content (TEXT), addressed (BOOLEAN, default false), addressed_at (TIMESTAMP, nullable), addressed_by (FK to staff, nullable), created_at
5. WHEN an inbound SMS is received via the Twilio webhook, THE Platform SHALL create a communication record with addressed set to false

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying the unaddressed count endpoint returns correct counts
7. THE Platform SHALL include a functional test creating communication records and verifying the count updates
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/dashboard`, verifies the Messages widget displays a numeric count, clicks it, and verifies navigation to the communications queue

---

### Requirement 5: Dashboard Invoice Metrics Fix

**User Story:** As an Admin, I want the dashboard to show the count of pending invoices based on actual invoice data, so that the metric reflects real invoicing status rather than job status approximations.

**Gap Refs:** CRM Dashboard #3

#### Acceptance Criteria

1. THE Dashboard_Page SHALL display a "Pending Invoices" widget showing the count of invoices with status SENT or VIEWED (not yet paid)
2. THE Platform SHALL expose a GET /api/v1/invoices/metrics/pending endpoint that returns the count and total amount of pending invoices
3. THE Dashboard_Page SHALL NOT calculate invoice metrics from job statuses

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying the pending invoice metrics endpoint returns correct count and total from actual invoice records
5. THE Platform SHALL include an E2E_Test using agent-browser that opens `/dashboard` and verifies the Pending Invoices widget shows a numeric count derived from invoice data

---

### Requirement 6: Dashboard Job Status Alignment

**User Story:** As an Admin, I want the dashboard job status tracking to match the specific statuses I need: New Requests, Estimates, Pending Approval, To Be Scheduled, In Progress, and Complete.

**Gap Refs:** CRM Dashboard #5

#### Acceptance Criteria

1. THE Dashboard_Page SHALL display job counts for exactly these status categories: "New Requests" (status=requested), "Estimates" (category=requires_estimate), "Pending Approval" (jobs with estimates awaiting customer approval), "To Be Scheduled" (status=approved), "In Progress" (status=in_progress), "Complete" (status=completed)
2. THE Platform SHALL expose a GET /api/v1/jobs/metrics/by-status endpoint that returns counts for each of the six categories above
3. WHEN the "Estimates" or "Pending Approval" categories require new status or category values, THE Platform SHALL add them to the Job model enums via migration

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying the by-status metrics endpoint returns all six categories with correct counts
5. THE Platform SHALL include an E2E_Test using agent-browser that opens `/dashboard` and verifies all six job status categories are displayed with numeric counts

---


### Requirement 7: Customer Duplicate Review and Merge

**User Story:** As an Admin, I want an admin panel to review, compare, and merge duplicate customer records, so that I can maintain a clean customer database.

**Gap Refs:** CRM Customers #1

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/customers/duplicates endpoint that returns groups of potential duplicate customers identified by matching phone number, email, or similar name (Levenshtein distance ≤ 2)
2. THE Platform SHALL expose a POST /api/v1/customers/merge endpoint that accepts a primary_customer_id and a list of duplicate_customer_ids, merges all related records (jobs, invoices, leads, agreements, communications) to the primary customer, and soft-deletes the duplicate records
3. THE Customer_Detail_View SHALL display a "Potential Duplicates" section when duplicates are detected for the current customer
4. WHEN a merge is performed, THE Customer_Service SHALL log the merge action with structured logging including all merged customer IDs and the primary customer ID with event `customer.merge.completed`

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying duplicate detection logic identifies matches by phone, email, and similar name
6. THE Platform SHALL include a functional test verifying merge correctly reassigns all related records and soft-deletes duplicates
7. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/customers`, opens a customer with duplicates, verifies the "Potential Duplicates" section appears, and performs a merge action

---

### Requirement 8: Customer Internal Notes Exposure

**User Story:** As an Admin, I want to view and edit internal notes for each customer from the frontend, so that I can track important information about customer interactions.

**Gap Refs:** CRM Customers #2

#### Acceptance Criteria

1. THE Platform SHALL include the `internal_notes` field in the CustomerResponse API schema
2. THE Customer_Detail_View SHALL display the `internal_notes` field in an editable text area
3. THE CustomerForm SHALL include an `internal_notes` field that allows the Admin to create and update notes
4. WHEN the Admin saves internal notes, THE Customer_Service SHALL update the `internal_notes` field on the Customer record via PATCH /api/v1/customers/{id}

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying internal_notes is included in the CustomerResponse schema
6. THE Platform SHALL include an E2E_Test using agent-browser that navigates to a customer detail page, edits the internal notes field, saves, and verifies the updated notes persist on page reload

---

### Requirement 9: Customer Photos

**User Story:** As an Admin, I want to upload and view photos for each customer (property photos, job photos, etc.), so that I have visual documentation of customer properties and work performed.

**Gap Refs:** CRM Customers #3, Sys Req Lead Intake #13 (photos/videos)

#### Acceptance Criteria

1. THE Platform SHALL add a `customer_photos` table with fields: id (UUID), customer_id (FK), file_key (VARCHAR — S3 object key), file_name (VARCHAR), file_size (INTEGER), content_type (VARCHAR), caption (TEXT, nullable), uploaded_by (FK to staff, nullable), created_at
2. THE Platform SHALL expose a POST /api/v1/customers/{id}/photos endpoint that accepts multipart file uploads (JPEG, PNG, HEIC, max 10MB per file, max 5 files per request) and stores them in S3-compatible storage
3. THE Platform SHALL expose a GET /api/v1/customers/{id}/photos endpoint that returns a paginated list of photo metadata with pre-signed download URLs
4. THE Platform SHALL expose a DELETE /api/v1/customers/{id}/photos/{photo_id} endpoint that removes the photo record and the S3 object
5. THE Customer_Detail_View SHALL display a "Photos" tab showing a grid of customer photos with upload, caption editing, and delete functionality
6. THE Photo_Service SHALL log all upload and delete operations with structured logging including customer_id, file_key, and file_size with event `customer.photo.uploaded` and `customer.photo.deleted`

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying file type and size validation rejects invalid uploads
8. THE Platform SHALL include a functional test verifying upload, list, and delete operations against S3-compatible storage
9. THE Platform SHALL include an E2E_Test using agent-browser that navigates to a customer detail page, clicks the Photos tab, uploads a test image, verifies it appears in the grid, and deletes it

---

### Requirement 10: Customer Invoice History on Detail Page

**User Story:** As an Admin, I want to see a customer's complete invoice history directly on their detail page, so that I don't have to navigate away to the Invoices section.

**Gap Refs:** CRM Customers #4

#### Acceptance Criteria

1. THE Customer_Detail_View SHALL display an "Invoice History" tab showing all invoices linked to the customer, sorted by date descending
2. THE Invoice History tab SHALL display for each invoice: invoice_number, date, total_amount, status (with color-coded badge), days_until_due or days_past_due, and a link to the full invoice detail
3. THE Platform SHALL expose a GET /api/v1/customers/{id}/invoices endpoint that returns a paginated list of invoices for the customer

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying the customer invoices endpoint returns correctly filtered and sorted results
5. THE Platform SHALL include an E2E_Test using agent-browser that navigates to a customer detail page, clicks the Invoice History tab, and verifies invoice records are displayed with correct status badges

---

### Requirement 11: Customer Availability/Preferred Service Times Editing

**User Story:** As an Admin, I want to edit a customer's preferred service times from the frontend, so that scheduling can account for customer availability.

**Gap Refs:** CRM Customers #5

#### Acceptance Criteria

1. THE Customer_Detail_View SHALL display the "Service Preferences" section with an edit button
2. WHEN the Admin clicks edit on Service Preferences, THE Platform SHALL show a form with options: Morning, Afternoon, Evening, No Preference, and specific time windows
3. THE CustomerForm SHALL include a `preferred_service_times` field that saves the selection via PATCH /api/v1/customers/{id}
4. THE Platform SHALL include `preferred_service_times` in the CustomerResponse API schema as an editable field

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying preferred_service_times is accepted and returned in the API
6. THE Platform SHALL include an E2E_Test using agent-browser that navigates to a customer detail page, edits the preferred service times, saves, and verifies the updated preference persists

---

### Requirement 12: Lead City and Full Address Collection

**User Story:** As an Admin, I want leads to show city at the high level and collect full address on click-in, so that I can quickly see lead location without navigating into each record.

**Gap Refs:** CRM Leads #1

#### Acceptance Criteria

1. THE Platform SHALL add `city` (VARCHAR, nullable), `state` (VARCHAR, nullable), and `address` (VARCHAR, nullable) fields to the Lead model via migration
2. WHEN a lead creation request is received, THE Lead_Service SHALL accept optional `city`, `state`, and `address` fields
3. THE Leads_Page SHALL display the `city` field in the leads table list view instead of or alongside `zip_code`
4. WHEN the Admin clicks into a lead detail, THE Platform SHALL show the full address fields (address, city, state, zip_code) in an editable form
5. WHEN only `zip_code` is provided on lead creation, THE Lead_Service SHALL attempt to auto-populate `city` and `state` from the zip code using a lookup

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying city/state auto-population from zip code
7. THE Platform SHALL include a functional test verifying lead creation with full address fields
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/leads`, verifies city is displayed in the list, clicks a lead, and verifies full address fields are shown and editable

---

### Requirement 13: Lead Tags System (Contact, Estimate, Approval)

**User Story:** As an Admin, I want explicit tags on leads for "Need to be contacted", "Need estimate", and "Estimate status (Pending/Approved)", so that I can quickly see what action each lead requires.

**Gap Refs:** CRM Leads #2, #3, #4

#### Acceptance Criteria

1. THE Platform SHALL add an `action_tags` field (JSONB array) to the Lead model supporting values: NEEDS_CONTACT, NEEDS_ESTIMATE, ESTIMATE_PENDING, ESTIMATE_APPROVED, ESTIMATE_REJECTED
2. WHEN a lead is created with status `new`, THE Lead_Service SHALL auto-assign the NEEDS_CONTACT tag
3. WHEN a lead is marked as contacted, THE Lead_Service SHALL remove the NEEDS_CONTACT tag
4. WHEN an estimate is requested for a lead, THE Lead_Service SHALL add the NEEDS_ESTIMATE tag
5. WHEN an estimate is provided for a lead, THE Lead_Service SHALL replace NEEDS_ESTIMATE with ESTIMATE_PENDING
6. WHEN a customer approves an estimate, THE Lead_Service SHALL replace ESTIMATE_PENDING with ESTIMATE_APPROVED
7. THE Leads_Page SHALL display action tags as color-coded badges on each lead row
8. THE Leads_Page SHALL support filtering by action tag

#### Testing Requirements

9. THE Platform SHALL include a unit test verifying tag auto-assignment and transition logic for all tag states
10. THE Platform SHALL include a functional test verifying the full tag lifecycle: creation → contact → estimate → approval
11. THE Platform SHALL include an E2E_Test using agent-browser that opens `/leads`, verifies tag badges are visible, filters by a specific tag, and verifies the filtered results

---

### Requirement 14: Lead Bulk Outreach

**User Story:** As an Admin, I want to reach out to all pending leads in bulk to try to close them, so that I can efficiently follow up with multiple leads at once.

**Gap Refs:** CRM Leads #5

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/leads/bulk-outreach endpoint that accepts a list of lead_ids and a message template, and sends SMS/email to each lead based on their contact preferences and consent status
2. THE Leads_Page SHALL provide a "Select All" checkbox and a "Bulk Outreach" button that opens a message template selector
3. WHEN bulk outreach is initiated, THE Lead_Service SHALL skip leads without SMS consent for SMS messages and log each skipped lead
4. WHEN bulk outreach completes, THE Lead_Service SHALL return a summary: sent_count, skipped_count, failed_count
5. THE Lead_Service SHALL log each outreach attempt with structured logging including lead_id, channel, and outcome with event `lead.outreach.sent` or `lead.outreach.skipped`

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying consent-gated sending logic skips non-consented leads
7. THE Platform SHALL include a functional test verifying bulk outreach sends to multiple leads and returns correct summary counts
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/leads`, selects multiple leads, clicks "Bulk Outreach", selects a template, sends, and verifies the success summary

---

### Requirement 15: Lead Attachments (Estimates and Contracts)

**User Story:** As an Admin, I want to attach estimate documents and contracts to each lead, so that all sales materials are organized per lead.

**Gap Refs:** CRM Leads #6

#### Acceptance Criteria

1. THE Platform SHALL add a `lead_attachments` table with fields: id (UUID), lead_id (FK), file_key (VARCHAR), file_name (VARCHAR), file_size (INTEGER), content_type (VARCHAR), attachment_type (ESTIMATE, CONTRACT, OTHER), created_at
2. THE Platform SHALL expose a POST /api/v1/leads/{id}/attachments endpoint that accepts multipart file uploads (PDF, DOCX, JPEG, PNG, max 25MB per file)
3. THE Platform SHALL expose a GET /api/v1/leads/{id}/attachments endpoint that returns attachment metadata with pre-signed download URLs
4. THE Platform SHALL expose a DELETE /api/v1/leads/{id}/attachments/{attachment_id} endpoint
5. THE lead detail view SHALL display an "Attachments" section showing all attached files grouped by type (Estimates, Contracts, Other)

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying file type and size validation
7. THE Platform SHALL include a functional test verifying upload, list, and delete operations
8. THE Platform SHALL include an E2E_Test using agent-browser that opens a lead detail, uploads a test PDF as an estimate attachment, verifies it appears in the Attachments section, and deletes it

---

### Requirement 16: Customer Estimate Review and Contract Signing Portal

**User Story:** As a customer, I want to review estimates and sign contracts from a link sent to me, so that I can approve work without phone calls or in-person meetings.

**Gap Refs:** CRM Leads #7, #8 (templates), Sales #8

#### Acceptance Criteria

1. THE Platform SHALL expose a public GET /api/v1/portal/estimates/{token} endpoint that returns estimate details for customer review without requiring authentication
2. THE Platform SHALL expose a public POST /api/v1/portal/estimates/{token}/approve endpoint that records customer approval with timestamp, IP address, and user agent
3. THE Platform SHALL expose a public POST /api/v1/portal/estimates/{token}/reject endpoint that records customer rejection with optional reason
4. THE Platform SHALL expose a public POST /api/v1/portal/contracts/{token}/sign endpoint that records the customer's electronic signature with timestamp, IP address, and user agent
5. WHEN a customer approves an estimate, THE Estimate_Service SHALL update the lead's action tag to ESTIMATE_APPROVED and notify the Admin via the Dashboard_Page
6. WHEN a customer signs a contract, THE Estimate_Service SHALL create a signed contract record and update the lead status to reflect contract completion
7. THE customer-facing portal pages SHALL be mobile-responsive and accessible without CRM login

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying token-based estimate retrieval and approval/rejection logic
9. THE Platform SHALL include a functional test verifying the full flow: estimate creation → link generation → customer approval → lead tag update
10. THE Platform SHALL include an E2E_Test using agent-browser that opens a portal estimate link, reviews the estimate, clicks approve, and verifies the approval confirmation page

---

### Requirement 17: Estimate and Contract Templates

**User Story:** As an Admin, I want reusable estimate templates and contract templates accessible from the leads section, so that I can quickly generate professional estimates and contracts.

**Gap Refs:** CRM Leads #8, Sales #3

#### Acceptance Criteria

1. THE Platform SHALL add an `estimate_templates` table with fields: id (UUID), name (VARCHAR), description (TEXT), line_items (JSONB array of item, description, unit_price, quantity), terms (TEXT), is_active (BOOLEAN), created_at, updated_at
2. THE Platform SHALL add a `contract_templates` table with fields: id (UUID), name (VARCHAR), body (TEXT — supports template variables), terms_and_conditions (TEXT), is_active (BOOLEAN), created_at, updated_at
3. THE Platform SHALL expose CRUD endpoints for estimate templates at /api/v1/templates/estimates
4. THE Platform SHALL expose CRUD endpoints for contract templates at /api/v1/templates/contracts
5. WHEN creating an estimate for a lead, THE Admin SHALL be able to select a template and customize line items before sending
6. THE Leads_Page detail view SHALL include "Create Estimate" and "Create Contract" buttons that open template-based forms

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying template CRUD operations and variable substitution in contract templates
8. THE Platform SHALL include a functional test verifying estimate creation from template with customized line items
9. THE Platform SHALL include an E2E_Test using agent-browser that opens a lead detail, clicks "Create Estimate", selects a template, modifies a line item, saves, and verifies the estimate appears in the lead's attachments

---

### Requirement 18: Lead Estimate-to-Approval Reverse Flow

**User Story:** As an Admin, I want a customer who received an estimate needing approval to appear in the leads section until approved, so that unapproved estimates are tracked in the sales pipeline.

**Gap Refs:** CRM Leads #9

#### Acceptance Criteria

1. WHEN a staff member creates an estimate for an existing customer that requires approval, THE Estimate_Service SHALL create or reactivate a lead record linked to that customer with action tag ESTIMATE_PENDING
2. WHEN the customer approves the estimate, THE Lead_Service SHALL update the lead action tag to ESTIMATE_APPROVED and create a Job record from the approved estimate
3. THE Leads_Page SHALL display these estimate-pending leads alongside regular leads, filterable by the ESTIMATE_PENDING tag

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying lead creation from an estimate-needing-approval scenario
5. THE Platform SHALL include a functional test verifying the full reverse flow: estimate creation → lead appears → customer approves → job created
6. THE Platform SHALL include an E2E_Test using agent-browser that verifies an estimate-pending lead appears in the leads list with the correct tag

---


### Requirement 19: Consolidate Work Requests into Leads

**User Story:** As an Admin, I want the Work Requests section removed and its functionality consolidated into Leads with two lead types (needs estimate, or approved/becomes job), so that there is a single pipeline for all inbound requests.

**Gap Refs:** CRM Work Requests #1

#### Acceptance Criteria

1. THE Platform SHALL migrate all existing GoogleSheetSubmission records into Lead records, preserving all data fields and mapping submission fields to lead fields
2. THE Platform SHALL redirect the `/work-requests` route to `/leads` with a notification explaining the consolidation
3. THE Platform SHALL remove the WorkRequestsList and WorkRequestDetail frontend components after migration
4. THE Platform SHALL update the Google Sheets poller to create Lead records instead of GoogleSheetSubmission records
5. WHEN a new Google Sheets submission is received, THE Lead_Service SHALL create a Lead with intake_tag based on whether the request needs an estimate (FOLLOW_UP) or has a confirmed price (SCHEDULE)
6. THE Platform SHALL preserve the Google Sheets integration endpoint but route submissions through the Lead_Service

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying GoogleSheetSubmission to Lead field mapping
8. THE Platform SHALL include a functional test verifying the migration converts all existing work requests to leads
9. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/work-requests` and verifies redirect to `/leads`, then verifies former work request data appears in the leads list

---

### Requirement 20: Job Notes and Summary Field

**User Story:** As an Admin, I want persistent notes under each job and a summary field visible in the job list, so that I can quickly see what each job involves without clicking into it.

**Gap Refs:** CRM Jobs #1

#### Acceptance Criteria

1. THE Platform SHALL add a `notes` (TEXT, nullable) and `summary` (VARCHAR(255), nullable) field to the Job model via migration
2. THE Platform SHALL expose the `notes` and `summary` fields in the JobResponse API schema
3. THE Job_List_View SHALL display the `summary` field as a column in the jobs table
4. THE job detail view SHALL display the `notes` field in an editable text area
5. WHEN the Admin saves job notes, THE Job_Service SHALL update the `notes` field via PATCH /api/v1/jobs/{id}

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying notes and summary fields are accepted and returned in the API
7. THE Platform SHALL include an E2E_Test using agent-browser that opens `/jobs`, verifies the summary column is visible, clicks a job, edits the notes field, saves, and verifies persistence

---

### Requirement 21: Job Status Simplification

**User Story:** As an Admin, I want job statuses limited to the statuses I actually use: To Be Scheduled, In Progress, and Complete, with the existing statuses mapped accordingly.

**Gap Refs:** CRM Jobs #2

#### Acceptance Criteria

1. THE Platform SHALL map existing job statuses to the simplified set: `requested` and `approved` map to "To Be Scheduled", `scheduled` and `in_progress` map to "In Progress", `completed` and `closed` map to "Complete", `cancelled` remains as "Cancelled"
2. THE Job_List_View SHALL display the simplified status labels instead of the raw enum values
3. THE Platform SHALL maintain the underlying enum values for backward compatibility but present the simplified labels in all frontend views
4. THE Job_List_View status filter SHALL use the simplified status labels as filter options

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying status mapping logic correctly maps all existing statuses to simplified labels
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/jobs`, verifies the status filter shows only the simplified labels, and verifies job rows display simplified status badges

---

### Requirement 22: Job List Column Changes

**User Story:** As an Admin, I want the job list to show Customer Name and Customer Tag columns, remove the Category column, and replace "Created on" with "Days since added".

**Gap Refs:** CRM Jobs #4, #5, #6, #7

#### Acceptance Criteria

1. THE Job_List_View SHALL remove the "Category" column from the jobs table
2. THE Job_List_View SHALL add a "Customer" column displaying the customer's full name, linked to the customer detail page
3. THE Job_List_View SHALL add a "Tags" column displaying the customer's tags (priority, red_flag, slow_payer, new_customer) as color-coded badges
4. THE Job_List_View SHALL replace the "Created" date column with a "Days Waiting" column showing the number of days since the job was added to the list (calculated as current_date minus created_at)
5. THE Platform SHALL include customer name and tags in the JobResponse API schema via a nested customer summary object

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying the "Days Waiting" calculation logic
7. THE Platform SHALL include an E2E_Test using agent-browser that opens `/jobs` and verifies: Category column is absent, Customer column shows names, Tags column shows badges, and Days Waiting column shows numeric day counts

---

### Requirement 23: Job "Needs to be Completed By" Column

**User Story:** As an Admin, I want a clear "Needs to be completed by" column in the job list showing the target end date, so that I can see deadlines at a glance.

**Gap Refs:** CRM Jobs #8

#### Acceptance Criteria

1. THE Job_List_View SHALL display a "Due By" column showing the `target_end_date` field formatted as a human-readable date
2. WHEN a job's target_end_date is within 7 days, THE Job_List_View SHALL display the date in amber/warning color
3. WHEN a job's target_end_date has passed, THE Job_List_View SHALL display the date in red/danger color
4. WHEN a job has no target_end_date, THE Job_List_View SHALL display "No deadline" in muted text

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying date color logic for upcoming, overdue, and no-deadline scenarios
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/jobs` and verifies the "Due By" column displays dates with appropriate color coding

---

### Requirement 24: Schedule Drag and Drop

**User Story:** As an Admin, I want to drag and drop scheduled appointments on the calendar, so that I can quickly reschedule by moving appointments between time slots and days.

**Gap Refs:** CRM Schedule Creating #2

#### Acceptance Criteria

1. THE Schedule_Page calendar SHALL enable drag-and-drop by setting FullCalendar's `editable` property to `true`
2. WHEN the Admin drags an appointment to a new time slot or day, THE Platform SHALL call PATCH /api/v1/appointments/{id} with the updated date and time
3. WHEN a drag-and-drop reschedule succeeds, THE Schedule_Page SHALL display a brief success toast notification
4. IF a drag-and-drop reschedule fails (e.g., staff conflict), THEN THE Schedule_Page SHALL revert the appointment to its original position and display an error message
5. THE Appointment_Service SHALL validate that the new time slot does not conflict with existing appointments for the same staff member

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying conflict detection logic for overlapping appointments
7. THE Platform SHALL include a functional test verifying appointment time update via the PATCH endpoint
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule`, identifies an appointment on the calendar, drags it to a new time slot, and verifies the appointment appears at the new time

---

### Requirement 25: Schedule Lead Time Display

**User Story:** As an Admin, I want to see how far booked out the schedule is, so that I can give customers a rough estimate of wait time.

**Gap Refs:** CRM Schedule Creating #3, Sys Req Scheduling #2

#### Acceptance Criteria

1. THE Schedule_Page SHALL display a "Lead Time" indicator showing the number of days/weeks until the next available scheduling slot
2. THE Platform SHALL expose a GET /api/v1/schedule/lead-time endpoint that calculates the earliest available date based on current appointment density and staff availability
3. THE lead time calculation SHALL consider staff working hours, existing appointments, and configurable maximum appointments per day per staff member

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying lead time calculation with various appointment densities
5. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule` and verifies the Lead Time indicator displays a value (e.g., "Booked out 2 weeks")

---

### Requirement 26: Schedule Manual Job Addition with Filters

**User Story:** As an Admin, I want to manually add jobs to the schedule by selecting from a filtered list of all jobs (by location and job type, with multi-select), so that I can efficiently build the schedule.

**Gap Refs:** CRM Schedule Creating #4

#### Acceptance Criteria

1. THE Schedule_Page appointment creation form SHALL include a job selection interface that displays all unscheduled jobs
2. THE job selection interface SHALL support filtering by location (city/zip), job type, and customer name
3. THE job selection interface SHALL support multi-select to add multiple jobs at once
4. WHEN multiple jobs are selected, THE Platform SHALL create appointments for each selected job with the specified date, time, and staff assignment

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying job filtering by location and type
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule`, clicks "Add Appointment", uses the job filter to narrow results, selects multiple jobs, and verifies appointments are created for each

---

### Requirement 27: Schedule Inline Customer Info

**User Story:** As an Admin, I want to view customer and job information inline on the schedule page without navigating away, so that I can stay in context while managing the schedule.

**Gap Refs:** CRM Schedule Creating #5

#### Acceptance Criteria

1. WHEN the Admin clicks a customer name or job link in the Schedule_Page, THE Platform SHALL open a slide-over panel or modal showing the customer/job details instead of navigating to a different page
2. THE inline panel SHALL display: customer name, phone, email, address, preferred service times, internal notes, and job details (type, summary, notes)
3. THE inline panel SHALL include a "View Full Details" link that navigates to the full customer or job detail page

#### Testing Requirements

4. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule`, clicks a customer name on an appointment, verifies the inline panel opens with customer details, and verifies the URL has NOT changed (no navigation)

---

### Requirement 28: Schedule Calendar Display Format

**User Story:** As an Admin, I want calendar slots to display "Staff Name - Job Type" instead of "Staff Name - Status", so that I can see what work is being done at a glance.

**Gap Refs:** CRM Schedule Creating #6

#### Acceptance Criteria

1. THE Schedule_Page calendar event labels SHALL display in the format "{Staff Name} - {Job Type}" (e.g., "John Smith - Spring Startup")
2. THE calendar event SHALL use color coding based on appointment status (confirmed=blue, in_progress=orange, completed=green) as a background color rather than in the label text

#### Testing Requirements

3. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule` and verifies calendar event labels contain staff name and job type (not status text)

---

### Requirement 29: Schedule Property Address Auto-Populate

**User Story:** As an Admin, I want the property address to auto-populate from customer information when creating an appointment, so that I don't have to manually enter addresses.

**Gap Refs:** CRM Schedule Creating #7

#### Acceptance Criteria

1. WHEN the Admin selects a customer or job in the appointment creation form, THE Schedule_Page SHALL auto-populate the address field from the customer's primary property address
2. THE Admin SHALL be able to override the auto-populated address if needed
3. THE appointment creation form SHALL display the auto-populated address with a visual indicator that it was auto-filled

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying address auto-population from customer property data
5. THE Platform SHALL include an E2E_Test using agent-browser that opens the appointment creation form, selects a customer, and verifies the address field is auto-populated

---


### Requirement 30: On-Site Payment Collection

**User Story:** As a Staff member, I want to collect payment on-site during an appointment and have it automatically update the customer record and invoicing, so that payment is captured immediately without manual data entry later.

**Gap Refs:** CRM Schedule Staff #8, Sys Req Scheduling #16

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display a "Collect Payment" button when the appointment status is `in_progress` or `completed`
2. WHEN the Staff clicks "Collect Payment", THE Platform SHALL display a payment form with options: Credit Card (via Stripe Terminal or manual entry), Cash, Check, Venmo, Zelle, or "Send Invoice" (routes to portal)
3. WHEN a payment is collected, THE Appointment_Service SHALL create or update the linked Invoice record with the payment amount, method, and timestamp
4. WHEN a payment is collected, THE Platform SHALL update the Customer record's payment history and the Job's financial data
5. THE Platform SHALL expose a POST /api/v1/appointments/{id}/collect-payment endpoint that accepts payment_method, amount, and optional reference_number
6. THE Appointment_Service SHALL log each payment collection with structured logging including appointment_id, amount, method, and staff_id with event `appointment.payment.collected`

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying payment collection creates/updates invoice records correctly for each payment method
8. THE Platform SHALL include a functional test verifying the full flow: collect payment → invoice updated → customer payment history updated
9. THE Platform SHALL include an E2E_Test using agent-browser that opens an in-progress appointment, clicks "Collect Payment", selects a payment method, enters an amount, submits, and verifies the invoice status updates

---

### Requirement 31: On-Site Invoice Creation and Sending

**User Story:** As a Staff member, I want to create and send an invoice with a payment link directly from an appointment slot, so that customers can pay immediately or via a link.

**Gap Refs:** CRM Schedule Staff #9, Sys Req Scheduling #13

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display a "Create Invoice" button
2. WHEN the Staff clicks "Create Invoice", THE Platform SHALL pre-populate an invoice form with the job details, customer info, and quoted amount from the appointment
3. WHEN the invoice is created and sent, THE Invoice_Service SHALL generate a payment link (Stripe Payment Link or Checkout Session) and send it to the customer via SMS (if consented) and email
4. THE Platform SHALL expose a POST /api/v1/appointments/{id}/create-invoice endpoint that creates an invoice linked to the appointment's job and customer
5. THE Invoice_Service SHALL log invoice creation from appointment with event `invoice.from_appointment.created`

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying invoice pre-population from appointment data
7. THE Platform SHALL include a functional test verifying invoice creation, payment link generation, and customer notification
8. THE Platform SHALL include an E2E_Test using agent-browser that opens an appointment, clicks "Create Invoice", verifies pre-populated fields, submits, and verifies the invoice appears in the invoice list

---

### Requirement 32: On-Site Estimate Creation

**User Story:** As a Staff member, I want to create and send estimates on the spot from an appointment using templates and price lists, with auto-routing to leads if not approved within 4 hours.

**Gap Refs:** CRM Schedule Staff #10, Sys Req Scheduling #12, Sys Req Scheduling #18

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display a "Create Estimate" button
2. WHEN the Staff clicks "Create Estimate", THE Platform SHALL display an estimate form with template selection, line items, and a price list reference
3. WHEN an estimate is created, THE Estimate_Service SHALL send the estimate to the customer via the portal link (SMS if consented, email always)
4. WHEN an estimate has not been approved within 4 hours, THE Estimate_Service SHALL auto-create a lead with action tag ESTIMATE_PENDING and notify the Admin
5. WHEN a customer approves an estimate from the portal, THE Estimate_Service SHALL update the estimate status, create a Job if needed, and send a push notification to the Staff
6. THE Platform SHALL expose a POST /api/v1/appointments/{id}/create-estimate endpoint
7. THE Platform SHALL run a background job (`check_estimate_approvals`) every hour that queries unapproved estimates older than 4 hours and routes them to the leads pipeline

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying the 4-hour auto-routing logic
9. THE Platform SHALL include a functional test verifying estimate creation, customer notification, and approval flow
10. THE Platform SHALL include an E2E_Test using agent-browser that opens an appointment, clicks "Create Estimate", selects a template, submits, and verifies the estimate is created

---

### Requirement 33: Staff Notes and Photos from Appointments

**User Story:** As a Staff member, I want to add notes and photos during an appointment that automatically update the customer record, so that all field observations are captured.

**Gap Refs:** CRM Schedule Staff #11

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display a "Notes" text area and a "Photos" upload section
2. WHEN the Staff saves notes on an appointment, THE Appointment_Service SHALL store the notes on the appointment record AND append them to the customer's internal_notes with a timestamp prefix
3. WHEN the Staff uploads photos from an appointment, THE Photo_Service SHALL store them linked to both the appointment and the customer
4. THE Platform SHALL expose a POST /api/v1/appointments/{id}/photos endpoint for photo uploads from the appointment context
5. THE Platform SHALL accept photos from mobile devices (camera capture via `accept="image/*;capture=camera"` on the file input)

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying notes propagation from appointment to customer record
7. THE Platform SHALL include a functional test verifying photo upload from appointment context links to both appointment and customer
8. THE Platform SHALL include an E2E_Test using agent-browser that opens an appointment, adds notes text, saves, and verifies the notes appear on the customer detail page

---

### Requirement 34: Google Review Request via SMS

**User Story:** As a Staff member, I want to send a Google review request to the customer after completing a job, so that satisfied customers can easily leave reviews.

**Gap Refs:** CRM Schedule Staff #13

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display a "Request Google Review" button when the appointment status is `completed`
2. WHEN the Staff clicks "Request Google Review", THE Notification_Service SHALL send an SMS to the customer (gated on SMS consent) with a direct link to the Google Business review page
3. THE Platform SHALL expose a POST /api/v1/appointments/{id}/request-review endpoint
4. THE Platform SHALL store the Google Business review URL in application configuration (core/config.py)
5. THE Notification_Service SHALL log each review request with event `appointment.review_request.sent`
6. THE Platform SHALL track review requests per customer to avoid sending duplicate requests within 30 days

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying SMS consent gating and 30-day deduplication logic
8. THE Platform SHALL include an E2E_Test using agent-browser that opens a completed appointment and verifies the "Request Google Review" button is visible

---

### Requirement 35: Staff Workflow Buttons (On My Way, Job Started, Job Complete)

**User Story:** As a Staff member, I want three clear workflow buttons — "On My Way", "Job Started", and "Job Complete" — so that the system tracks my progress through each appointment.

**Gap Refs:** CRM Schedule Staff #14, Sys Req Scheduling #11

#### Acceptance Criteria

1. THE Schedule_Page appointment detail view SHALL display three sequential workflow buttons: "On My Way" (when status is confirmed), "Job Started" (when status is en_route), "Job Complete" (when status is in_progress)
2. THE Platform SHALL add an `en_route` status to the appointment status enum via migration, inserted between `confirmed` and `in_progress`
3. THE Platform SHALL add an `en_route_at` (TIMESTAMP, nullable) field to the Appointment model
4. WHEN the Staff clicks "On My Way", THE Appointment_Service SHALL transition the appointment to `en_route` status and record `en_route_at`
5. WHEN the Staff clicks "Job Started", THE Appointment_Service SHALL transition the appointment to `in_progress` status and record `arrived_at`
6. WHEN the Staff clicks "Job Complete", THE Appointment_Service SHALL transition the appointment to `completed` status and record `completed_at`
7. THE button labels SHALL match exactly: "On My Way", "Job Started", "Job Complete"

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying the full status transition chain: confirmed → en_route → in_progress → completed
9. THE Platform SHALL include a functional test verifying timestamp recording at each transition
10. THE Platform SHALL include an E2E_Test using agent-browser that opens a confirmed appointment, clicks "On My Way", verifies status changes, clicks "Job Started", verifies, clicks "Job Complete", and verifies final status

---

### Requirement 36: Payment Required Before Job Completion

**User Story:** As an Admin, I want staff to be unable to mark a job as complete until payment is collected or an invoice is sent, so that no job closes without financial resolution.

**Gap Refs:** CRM Schedule Staff #15

#### Acceptance Criteria

1. WHEN the Staff clicks "Job Complete" on an appointment, THE Appointment_Service SHALL check whether payment has been collected OR an invoice has been sent for the linked job
2. IF neither payment nor invoice exists, THEN THE Appointment_Service SHALL block the completion and display a message: "Please collect payment or send an invoice before completing this job"
3. THE "Job Complete" button SHALL be visually disabled (grayed out) with a tooltip explaining the requirement when payment/invoice is missing
4. THE Platform SHALL allow Admin to override this restriction via a configuration flag for exceptional cases

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying completion is blocked when no payment or invoice exists
6. THE Platform SHALL include a unit test verifying completion succeeds when payment or invoice exists
7. THE Platform SHALL include an E2E_Test using agent-browser that opens an in-progress appointment without payment, attempts to click "Job Complete", and verifies the blocking message appears

---

### Requirement 37: Staff Time Tracking and Analytics

**User Story:** As an Admin, I want the system to track time between each workflow button per job type and staff member, so that I can analyze efficiency and identify bottlenecks.

**Gap Refs:** CRM Schedule Staff #16, Sys Req Scheduling #17

#### Acceptance Criteria

1. THE Platform SHALL calculate and store duration metrics on each appointment: travel_time (en_route_at to arrived_at), job_duration (arrived_at to completed_at), total_time (en_route_at to completed_at)
2. THE Platform SHALL expose a GET /api/v1/analytics/staff-time endpoint that returns average travel_time, job_duration, and total_time grouped by staff_id and job_type
3. THE appointment detail view SHALL display the calculated durations after job completion
4. WHEN a staff member's job_duration exceeds 1.5x the average for that job type, THE Platform SHALL create a notification for the Admin with event `staff.time.exceeded_average`

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying duration calculations from timestamps
6. THE Platform SHALL include a unit test verifying the 1.5x threshold notification trigger
7. THE Platform SHALL include an E2E_Test using agent-browser that opens a completed appointment and verifies duration metrics are displayed

---

### Requirement 38: Invoice Bulk Notifications

**User Story:** As an Admin, I want to send bulk notifications to multiple customers at once for past-due invoices, upcoming due dates, and lien notices, so that I can efficiently manage collections.

**Gap Refs:** CRM Invoices #4

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/invoices/bulk-notify endpoint that accepts a list of invoice_ids and a notification_type (REMINDER, PAST_DUE, LIEN_WARNING, UPCOMING_DUE)
2. THE Invoice_Page SHALL provide a "Select All" checkbox and a "Bulk Notify" button with notification type selection
3. WHEN bulk notification is initiated, THE Invoice_Service SHALL send SMS (if consented) and email to each customer, skipping those without consent
4. THE Invoice_Service SHALL return a summary: sent_count, skipped_count, failed_count
5. THE Invoice_Service SHALL log each notification with event `invoice.bulk_notify.sent` or `invoice.bulk_notify.skipped`

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying consent-gated sending and notification type routing
7. THE Platform SHALL include a functional test verifying bulk notification sends to multiple invoices and returns correct summary
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/invoices`, selects multiple invoices, clicks "Bulk Notify", selects "Past Due", sends, and verifies the success summary

---


### Requirement 39: Customer Notifications (Day-Of, On My Way, Arrival, Delays, Completion)

**User Story:** As a customer, I want to receive automated notifications about my appointment — day-of reminder, when the technician is on the way with ETA, arrival, any delays, and job completion with receipt — so that I am informed throughout the service process.

**Gap Refs:** Sys Req Scheduling #7, #8, #9, #10, #14

#### Acceptance Criteria

1. THE Notification_Service SHALL send a day-of appointment reminder to the customer at 7:00 AM Central Time on the appointment date via SMS (if consented) and email, including the estimated arrival window
2. WHEN a Staff member clicks "On My Way", THE Notification_Service SHALL send an SMS/email to the customer with the staff name and estimated arrival time based on Google Maps travel time calculation
3. WHEN a Staff member clicks "Job Started" (arrival), THE Notification_Service SHALL send an SMS/email to the customer confirming the technician has arrived
4. WHEN an appointment is running behind schedule (current time exceeds the scheduled end time by more than 15 minutes and status is still in_progress), THE Notification_Service SHALL send a delay notification to the customer with an updated estimated completion time
5. WHEN a Staff member clicks "Job Complete", THE Notification_Service SHALL send a completion notification to the customer including a job summary, receipt/invoice link, and the Google review request link
6. THE Platform SHALL expose a POST /api/v1/notifications/appointment/{id}/day-of endpoint for the daily background job to trigger day-of reminders
7. THE Platform SHALL run a daily background job (`send_day_of_reminders`) at 7:00 AM Central Time that queries all appointments for the current day and sends reminders
8. ALL automated customer notifications SHALL be gated on SMS consent for SMS channel and SHALL always send via email as a fallback

#### Testing Requirements

9. THE Platform SHALL include a unit test verifying each notification type is triggered at the correct event
10. THE Platform SHALL include a unit test verifying SMS consent gating and email fallback
11. THE Platform SHALL include a functional test verifying the day-of reminder background job sends to all same-day appointments
12. THE Platform SHALL include an E2E_Test using agent-browser that opens a confirmed appointment, clicks "On My Way", and verifies the notification log shows an "on my way" notification was queued

---

### Requirement 40: Appointment Slot Enrichment

**User Story:** As a Staff member, I want appointment slots to show all key data — materials/equipment needed, time allocated, client history, and directions — so that I arrive prepared.

**Gap Refs:** Sys Req Scheduling #3

#### Acceptance Criteria

1. THE Platform SHALL add `materials_needed` (TEXT, nullable) and `estimated_duration_minutes` (INTEGER, nullable) fields to the Appointment model via migration
2. THE appointment detail view SHALL display: customer name, phone, email, job type, location with Google Maps link, materials/equipment needed, estimated duration, customer service history summary (total jobs, last service date), and special notes
3. THE Platform SHALL include a "Get Directions" button that opens Google Maps navigation to the appointment address
4. THE appointment creation form SHALL include fields for materials_needed and estimated_duration_minutes

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying the enriched appointment response includes all required fields
6. THE Platform SHALL include an E2E_Test using agent-browser that opens an appointment detail and verifies all enriched fields are displayed including the "Get Directions" button

---

### Requirement 41: Admin Real-Time Staff Tracking

**User Story:** As an Admin, I want to see staff GPS location, current job in progress, and estimated time remaining on the schedule dashboard, so that I can monitor field operations in real time.

**Gap Refs:** Sys Req Scheduling #6

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/staff/{id}/location endpoint that accepts latitude, longitude, and timestamp from the staff's mobile device
2. THE Platform SHALL store the latest staff location in Redis with a TTL of 5 minutes for real-time access
3. THE Schedule_Page SHALL display a map overlay showing staff locations as pins with their current appointment status
4. THE Schedule_Page staff panel SHALL show for each active staff member: current appointment (if any), time elapsed on current job, estimated time remaining (based on estimated_duration_minutes minus elapsed time)
5. THE Platform SHALL expose a GET /api/v1/staff/locations endpoint that returns the latest location for all active staff members

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying location storage and retrieval from Redis
7. THE Platform SHALL include a unit test verifying time remaining calculation
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule` and verifies the staff location map overlay is visible with staff pins

---

### Requirement 42: Staff Break/Pause Functionality

**User Story:** As a Staff member, I want to log breaks (gas station, lunch, etc.) so that customers see a 30-45 minute window and the system accounts for non-work time.

**Gap Refs:** Sys Req Scheduling #15

#### Acceptance Criteria

1. THE Schedule_Page SHALL display a "Take Break" button for active staff members
2. WHEN the Staff clicks "Take Break", THE Platform SHALL create a break record with start_time and an estimated duration (default 30 minutes, configurable up to 45 minutes)
3. THE Platform SHALL add a `staff_breaks` table with fields: id (UUID), staff_id (FK), appointment_id (FK, nullable — the appointment before the break), start_time (TIMESTAMP), end_time (TIMESTAMP, nullable), break_type (LUNCH, GAS, PERSONAL, OTHER), created_at
4. WHEN a break is active, THE Schedule_Page calendar SHALL show the break as a blocked time slot
5. WHEN a break is active and a customer has a next appointment with that staff member, THE Notification_Service SHALL adjust the customer's estimated arrival window by the break duration

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying break time adjusts subsequent appointment ETAs
7. THE Platform SHALL include an E2E_Test using agent-browser that opens `/schedule`, clicks "Take Break" for a staff member, and verifies the break appears as a blocked slot on the calendar

---

### Requirement 43: AI Chatbot for Public Website

**User Story:** As a customer visiting the website, I want to interact with an AI chatbot that can answer questions about services, pricing, and scheduling, with an option to speak to a real person.

**Gap Refs:** Sys Req Lead Intake #2, #11

#### Acceptance Criteria

1. THE Platform SHALL expose a public POST /api/v1/chat/public endpoint that accepts a message and session_id and returns an AI-generated response using GPT-4o-mini
2. THE public chat endpoint SHALL have context about Grins Irrigation services, pricing tiers, service areas, and FAQs
3. WHEN the customer requests to speak to a real person, THE chat system SHALL create a communication record flagged for Admin review and respond with "A team member will reach out to you shortly"
4. THE Platform SHALL rate-limit the public chat endpoint to 10 messages per minute per session to prevent abuse
5. THE chat system SHALL collect the customer's name and phone number before escalating to a human, creating a Lead record if one doesn't exist

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying rate limiting and human escalation trigger detection
7. THE Platform SHALL include a functional test verifying chat context includes service information and pricing
8. THE Platform SHALL include an E2E_Test using agent-browser that opens the public chat widget, sends a message, verifies an AI response is received, types "speak to a person", and verifies the escalation response

---

### Requirement 44: Voice Call AI Integration

**User Story:** As a customer calling the business, I want an AI agent to answer, collect my information, and route my request, so that I can get help even outside business hours.

**Gap Refs:** Sys Req Lead Intake #3 (voice calls)

#### Acceptance Criteria

1. THE Platform SHALL integrate with a voice AI provider (e.g., Vapi) to handle inbound phone calls
2. THE voice AI SHALL greet callers, collect name, phone, service needed, and preferred callback time
3. WHEN the voice AI collects customer information, THE Platform SHALL create a Lead record via the Lead_Service with lead_source set to PHONE_CALL
4. WHEN the caller requests a human, THE voice AI SHALL transfer the call to the Admin's phone number or take a message if unavailable
5. THE Platform SHALL expose a POST /api/v1/voice/webhook endpoint for the voice AI provider to send call transcripts and collected data
6. THE Platform SHALL log all voice interactions with event `voice.call.received` and `voice.call.lead_created`

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying lead creation from voice webhook data
8. THE Platform SHALL include a functional test verifying the webhook endpoint processes call data and creates leads correctly

---

### Requirement 45: Campaign Management System

**User Story:** As an Admin, I want to create, schedule, and send mass email and SMS campaigns for promotions and deals, so that I can market to my customer base efficiently.

**Gap Refs:** Sys Req Lead Intake #4, Sys Req Marketing #6, #7

#### Acceptance Criteria

1. THE Platform SHALL add a `campaigns` table with fields: id (UUID), name (VARCHAR), campaign_type (EMAIL, SMS, BOTH), status (DRAFT, SCHEDULED, SENDING, SENT, CANCELLED), subject (VARCHAR, nullable — for email), body (TEXT), template_id (FK, nullable), target_audience (JSONB — filter criteria for recipients), scheduled_at (TIMESTAMP, nullable), sent_at (TIMESTAMP, nullable), created_by (FK to staff), created_at, updated_at
2. THE Platform SHALL add a `campaign_recipients` table with fields: id (UUID), campaign_id (FK), customer_id (FK), channel (EMAIL, SMS), status (PENDING, SENT, DELIVERED, FAILED, BOUNCED, OPTED_OUT), sent_at (TIMESTAMP, nullable), error_message (TEXT, nullable)
3. THE Platform SHALL expose CRUD endpoints for campaigns at /api/v1/campaigns
4. THE Platform SHALL expose a POST /api/v1/campaigns/{id}/send endpoint that initiates campaign delivery
5. THE Platform SHALL expose a GET /api/v1/campaigns/{id}/stats endpoint returning delivery metrics: total_recipients, sent, delivered, failed, bounced, opted_out
6. WHEN a campaign is sent, THE Campaign_Service SHALL filter recipients based on target_audience criteria, skip customers without SMS consent (for SMS campaigns), and skip customers who have opted out of email marketing (for email campaigns)
7. THE Platform SHALL run campaign sends as a background job to avoid blocking the API
8. THE Campaign_Service SHALL enforce CAN-SPAM compliance for email campaigns: include physical business address and unsubscribe link
9. THE Platform SHALL support campaign scheduling: WHEN a campaign has scheduled_at set, THE background scheduler SHALL send it at the specified time
10. THE Campaign_Service SHALL support automation rules: recurring campaigns triggered by parameters (e.g., "send to all customers with no appointment in 90 days every Monday")

#### Testing Requirements

11. THE Platform SHALL include a unit test verifying recipient filtering by audience criteria and consent status
12. THE Platform SHALL include a functional test verifying campaign creation, scheduling, and delivery to multiple recipients
13. THE Platform SHALL include an E2E_Test using agent-browser that opens `/marketing/campaigns`, creates a new campaign, selects an audience, schedules it, and verifies it appears in the campaign list with SCHEDULED status

---

### Requirement 46: SMS Confirmation for Lead Submissions

**User Story:** As a customer, I want to receive an SMS confirmation after submitting a work request, so that I know my request was received.

**Gap Refs:** Sys Req Lead Intake #10

#### Acceptance Criteria

1. WHEN a lead is created and the lead has `sms_consent` set to true, THE Lead_Service SHALL send an SMS confirmation message to the lead's phone number: "Thanks for reaching out to Grins Irrigation! We received your request and will be in touch soon."
2. THE SMS confirmation SHALL be sent via the SMS_Service, which enforces time window restrictions (8 AM - 9 PM Central)
3. THE Lead_Service SHALL log the SMS confirmation attempt with event `lead.confirmation.sms_sent` or `lead.confirmation.sms_deferred`
4. THE Platform SHALL update the SentMessage model to accept a `lead_id` FK (nullable) in addition to `customer_id`, enabling SMS logging for leads that haven't converted to customers yet

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying SMS is sent only when sms_consent is true
6. THE Platform SHALL include a unit test verifying SMS is deferred when outside the time window
7. THE Platform SHALL include a functional test verifying lead creation triggers SMS confirmation end-to-end

---


### Requirement 47: Sales Dashboard

**User Story:** As an Admin, I want a dedicated Sales dashboard showing estimates needing write-up, pending approval, needing follow-up, and revenue to be gained, so that I can manage the sales pipeline effectively.

**Gap Refs:** Sys Req Sales #1, #2

#### Acceptance Criteria

1. THE Platform SHALL create a Sales_Dashboard page at `/sales` accessible from the main navigation
2. THE Sales_Dashboard SHALL display four pipeline sections: "Needs Estimate" (leads tagged NEEDS_ESTIMATE), "Pending Approval" (estimates with status ESTIMATE_PENDING), "Needs Follow-Up" (estimates older than 48 hours without customer response), "Revenue Pipeline" (total quoted amount of all pending estimates)
3. THE Platform SHALL expose a GET /api/v1/sales/metrics endpoint returning: estimates_needing_writeup_count, pending_approval_count, needs_followup_count, total_pipeline_revenue, conversion_rate (approved / total estimates over trailing 30 days)
4. THE Sales_Dashboard SHALL allow the Admin to click into each section to see the individual estimates/leads
5. THE Sales_Dashboard SHALL display a conversion funnel visualization: Leads → Estimates → Approved → Jobs

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying each metric calculation in the sales metrics endpoint
7. THE Platform SHALL include a functional test verifying pipeline counts match actual estimate/lead data
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/sales`, verifies all four pipeline sections display numeric counts, and clicks into the "Pending Approval" section to verify individual estimates are listed

---

### Requirement 48: Estimate Builder with Pricing Tiers

**User Story:** As an Admin or Staff, I want to build estimates with material-based pricing, good/better/best options, and promotional discounts, so that customers receive professional multi-option estimates.

**Gap Refs:** Sys Req Sales #3, #4, #7

#### Acceptance Criteria

1. THE Platform SHALL add an `estimates` table with fields: id (UUID), lead_id (FK, nullable), customer_id (FK, nullable), job_id (FK, nullable), template_id (FK, nullable), status (DRAFT, SENT, VIEWED, APPROVED, REJECTED, EXPIRED), line_items (JSONB array of item, description, quantity, unit_price, total), options (JSONB array of option tiers: good, better, best with different line items and totals), subtotal (DECIMAL), tax_amount (DECIMAL), discount_amount (DECIMAL, default 0), total (DECIMAL), promotion_code (VARCHAR, nullable), valid_until (DATE), customer_token (UUID — for portal access), notes (TEXT, nullable), created_by (FK to staff), created_at, updated_at
2. THE Platform SHALL expose CRUD endpoints for estimates at /api/v1/estimates
3. THE Platform SHALL expose a POST /api/v1/estimates/{id}/send endpoint that sends the estimate to the customer via email and SMS (if consented) with a portal link
4. THE estimate creation form SHALL support adding line items with material costs, labor costs, and markup
5. THE estimate creation form SHALL support creating up to 3 pricing tiers (Good, Better, Best) with different scope and pricing
6. THE estimate creation form SHALL support applying promotional discounts (percentage or fixed amount)
7. WHEN a promotion is applied, THE Estimate_Service SHALL validate the promotion code and calculate the discounted total

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying multi-tier estimate calculation with discounts
9. THE Platform SHALL include a functional test verifying estimate creation, sending, and customer portal access
10. THE Platform SHALL include an E2E_Test using agent-browser that opens the estimate builder, adds line items, creates Good/Better/Best options, applies a promotion, and verifies the totals calculate correctly

---

### Requirement 49: Media Library for Sales

**User Story:** As a Staff member, I want access to past photos, videos, and testimonials to show clients during estimates, so that I can demonstrate quality of work.

**Gap Refs:** Sys Req Sales #5

#### Acceptance Criteria

1. THE Platform SHALL add a `media_library` table with fields: id (UUID), file_key (VARCHAR), file_name (VARCHAR), file_size (INTEGER), content_type (VARCHAR), media_type (PHOTO, VIDEO, TESTIMONIAL), category (VARCHAR — e.g., "spring_startup", "installation", "repair"), caption (TEXT, nullable), is_public (BOOLEAN, default false), uploaded_by (FK to staff), created_at
2. THE Platform SHALL expose CRUD endpoints for media at /api/v1/media
3. THE Platform SHALL expose a GET /api/v1/media?category={category}&type={type} endpoint for filtered browsing
4. THE Sales_Dashboard and estimate builder SHALL include a "Media Library" panel for browsing and attaching media to estimates
5. THE media upload SHALL support JPEG, PNG, HEIC (photos), MP4, MOV (videos), max 50MB per file

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying file type validation and category filtering
7. THE Platform SHALL include an E2E_Test using agent-browser that opens the media library, uploads a test image, verifies it appears in the grid, and filters by category

---

### Requirement 50: Property Diagram/Vision Builder

**User Story:** As a Staff member, I want a basic property diagram tool to sketch irrigation system layouts during estimates, so that customers can visualize the proposed work.

**Gap Refs:** Sys Req Sales #6

#### Acceptance Criteria

1. THE Platform SHALL integrate a simple canvas-based drawing tool (e.g., Excalidraw embed or custom canvas) accessible from the estimate builder
2. THE drawing tool SHALL support: basic shapes (rectangles, circles, lines), text labels, drag-and-drop irrigation component icons (sprinkler heads, pipes, valves, controllers), and a property boundary outline
3. THE drawing tool SHALL support importing a satellite/aerial image as a background layer (via Google Maps Static API or uploaded photo)
4. WHEN a diagram is saved, THE Platform SHALL store it as an SVG or PNG file linked to the estimate via the media library
5. THE customer portal estimate view SHALL display attached diagrams

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying diagram save and retrieval
7. THE Platform SHALL include an E2E_Test using agent-browser that opens the estimate builder, opens the diagram tool, draws a basic shape, saves, and verifies the diagram appears in the estimate

---

### Requirement 51: Estimate Follow-Up Automation

**User Story:** As an Admin, I want automated follow-up notifications sent to customers at configurable intervals until they approve or reject an estimate, with promotional options for persuasion.

**Gap Refs:** Sys Req Sales #9, #10, #11

#### Acceptance Criteria

1. THE Platform SHALL add an `estimate_follow_ups` table with fields: id (UUID), estimate_id (FK), follow_up_number (INTEGER), scheduled_at (TIMESTAMP), sent_at (TIMESTAMP, nullable), channel (SMS, EMAIL), message (TEXT), promotion_code (VARCHAR, nullable), status (PENDING, SENT, CANCELLED)
2. WHEN an estimate is sent, THE Estimate_Service SHALL schedule follow-up notifications at configurable intervals (default: Day 3, Day 7, Day 14, Day 21)
3. WHEN a follow-up is due, THE background scheduler SHALL send the notification via SMS (if consented) and email
4. THE Admin SHALL be able to attach a promotional discount to a follow-up message (e.g., "10% off if you approve by Friday")
5. WHEN the customer approves or rejects the estimate, THE Estimate_Service SHALL cancel all remaining scheduled follow-ups
6. THE Sales_Dashboard SHALL display a "Follow-Up Queue" showing estimates with upcoming follow-ups

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying follow-up scheduling at correct intervals and cancellation on approval
8. THE Platform SHALL include a functional test verifying the full follow-up lifecycle: estimate sent → follow-ups scheduled → customer approves → remaining cancelled
9. THE Platform SHALL include an E2E_Test using agent-browser that opens `/sales`, views the Follow-Up Queue, and verifies estimates with scheduled follow-ups are listed

---

### Requirement 52: Accounting Dashboard — Revenue and Profit

**User Story:** As an Admin, I want an accounting dashboard showing YTD profit, YTD revenue, pending invoices, and past-due invoices with totals, so that I have a clear financial picture.

**Gap Refs:** Sys Req Accounting #1, #2, #3

#### Acceptance Criteria

1. THE Platform SHALL create an Accounting_Dashboard page at `/accounting` accessible from the main navigation
2. THE Accounting_Dashboard SHALL display: YTD Revenue (sum of all paid invoice amounts), YTD Expenses (sum of all tracked expenses), YTD Profit (revenue minus expenses), with options to view by month, quarter, or custom date range
3. THE Accounting_Dashboard SHALL display a "Pending Invoices" section showing invoices with status SENT or VIEWED, with total pending amount
4. THE Accounting_Dashboard SHALL display a "Past Due Invoices" section showing invoices with status OVERDUE, with total past-due amount and days past due for each
5. THE Platform SHALL expose a GET /api/v1/accounting/summary endpoint returning: ytd_revenue, ytd_expenses, ytd_profit, pending_invoice_count, pending_invoice_total, past_due_invoice_count, past_due_invoice_total
6. THE Accounting_Dashboard SHALL support date range filtering for all metrics

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying revenue, expense, and profit calculations
8. THE Platform SHALL include a functional test verifying the summary endpoint returns correct aggregations from real invoice and expense data
9. THE Platform SHALL include an E2E_Test using agent-browser that opens `/accounting`, verifies YTD Revenue, Pending Invoices, and Past Due Invoices sections display numeric values, and changes the date range filter to verify metrics update

---

### Requirement 53: Expense Tracking System

**User Story:** As an Admin, I want to track spending by category (materials, fuel, maintenance, staff costs, marketing, etc.), so that I can calculate profit margins and manage costs.

**Gap Refs:** Sys Req Accounting #4, #5, #10, #11, #14

#### Acceptance Criteria

1. THE Platform SHALL add an `expenses` table with fields: id (UUID), category (MATERIALS, FUEL, MAINTENANCE, LABOR, MARKETING, INSURANCE, EQUIPMENT, OFFICE, SUBCONTRACTING, OTHER), description (TEXT), amount (DECIMAL(10,2)), date (DATE), job_id (FK, nullable — links expense to specific job), staff_id (FK, nullable — links labor cost to staff), vendor (VARCHAR, nullable), receipt_file_key (VARCHAR, nullable — S3 key for receipt photo), notes (TEXT, nullable), created_by (FK to staff), created_at, updated_at
2. THE Platform SHALL expose CRUD endpoints for expenses at /api/v1/expenses
3. THE Platform SHALL expose a GET /api/v1/expenses/by-category endpoint returning total spending per category for a given date range
4. THE Accounting_Dashboard SHALL display a "Spending by Category" chart showing expense breakdown
5. THE Platform SHALL expose a GET /api/v1/jobs/{id}/costs endpoint returning all expenses linked to a specific job, enabling per-job cost analysis
6. THE Platform SHALL calculate average profit margin as: (total_revenue - total_expenses) / total_revenue × 100, exposed via the accounting summary endpoint
7. THE Platform SHALL support receipt photo upload on expense creation (JPEG, PNG, PDF, max 10MB) with storage in S3

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying expense categorization and per-job cost aggregation
9. THE Platform SHALL include a unit test verifying profit margin calculation
10. THE Platform SHALL include a functional test verifying expense CRUD with receipt upload
11. THE Platform SHALL include an E2E_Test using agent-browser that opens `/accounting`, navigates to expenses, creates a new expense with category and amount, and verifies it appears in the expense list and the spending chart updates

---

### Requirement 54: Automated Invoice Notifications

**User Story:** As an Admin, I want the system to automatically notify customers 3 days before invoice due date and weekly after past due, so that collections happen without manual tracking.

**Gap Refs:** Sys Req Accounting #6

#### Acceptance Criteria

1. THE Platform SHALL run a daily background job (`send_invoice_reminders`) that queries all invoices and sends notifications based on due date proximity
2. WHEN an invoice is 3 days before its due_date and no pre-due reminder has been sent, THE Invoice_Service SHALL send a reminder via SMS (if consented) and email: "Your invoice {invoice_number} for ${amount} is due on {due_date}"
3. WHEN an invoice is past due, THE Invoice_Service SHALL send a weekly reminder every 7 days via SMS (if consented) and email: "Your invoice {invoice_number} for ${amount} is past due. Please pay at your earliest convenience."
4. THE Platform SHALL add `pre_due_reminder_sent_at` (TIMESTAMP, nullable) and `last_past_due_reminder_at` (TIMESTAMP, nullable) fields to the Invoice model to track reminder state
5. THE Invoice_Service SHALL log each automated reminder with event `invoice.reminder.pre_due_sent` or `invoice.reminder.past_due_sent`

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying reminder scheduling logic for pre-due and past-due scenarios
7. THE Platform SHALL include a functional test verifying the background job sends reminders to the correct invoices
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/invoices` and verifies reminder status indicators are visible on invoices that have received automated reminders

---

### Requirement 55: Automated Lien Notifications

**User Story:** As an Admin, I want the system to automatically send formal lien notifications at 30 days past due for eligible services, so that lien rights are preserved without manual tracking.

**Gap Refs:** Sys Req Accounting #7

#### Acceptance Criteria

1. THE daily `send_invoice_reminders` background job SHALL also check for lien-eligible invoices that are 30+ days past due
2. WHEN a lien-eligible invoice reaches 30 days past due and no lien warning has been sent, THE Invoice_Service SHALL automatically send a formal lien notification via email (and SMS if consented)
3. THE lien notification SHALL reference the property address, invoice amount, and the statutory lien filing deadline
4. THE Invoice_Service SHALL update the invoice status to LIEN_WARNING and record the notification timestamp
5. THE Invoice_Service SHALL log the automated lien notification with event `invoice.lien.auto_warning_sent`

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying lien eligibility check and 30-day threshold
7. THE Platform SHALL include a functional test verifying automated lien notification for eligible invoices

---

### Requirement 56: Customer Credit on File

**User Story:** As an Admin, I want to store customer payment methods on file and charge them when needed, so that repeat billing is frictionless.

**Gap Refs:** Sys Req Accounting #9

#### Acceptance Criteria

1. THE Platform SHALL store Stripe customer IDs on Customer records (stripe_customer_id field, already exists from service-package-purchases spec)
2. THE Platform SHALL expose a POST /api/v1/customers/{id}/charge endpoint that creates a Stripe PaymentIntent using the customer's default payment method on file
3. THE Platform SHALL expose a GET /api/v1/customers/{id}/payment-methods endpoint that returns the customer's saved payment methods from Stripe
4. THE Customer_Detail_View SHALL display a "Payment Methods" section showing saved cards with a "Charge" button
5. WHEN charging a customer, THE Platform SHALL require the Admin to specify the amount and a description/invoice reference
6. THE Platform SHALL log all charge attempts with event `customer.charge.attempted` and `customer.charge.succeeded` or `customer.charge.failed`

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying charge endpoint validation (amount, description required)
8. THE Platform SHALL include a functional test verifying Stripe PaymentIntent creation with test mode
9. THE Platform SHALL include an E2E_Test using agent-browser that opens a customer detail page, views the Payment Methods section, and verifies saved payment methods are displayed

---

### Requirement 57: Per-Job Financial View

**User Story:** As an Admin, I want to see total money received, material costs, and staff costs per job, so that I can understand profitability at the job level.

**Gap Refs:** Sys Req Accounting #10, #11, #12

#### Acceptance Criteria

1. THE job detail view SHALL display a "Financials" section showing: quoted_amount, final_amount, total_paid (from linked invoices), material_costs (from linked expenses with category MATERIALS), labor_costs (from linked expenses with category LABOR), total_costs, profit (total_paid minus total_costs), and profit_margin percentage
2. THE Platform SHALL expose a GET /api/v1/jobs/{id}/financials endpoint returning all the above calculated fields
3. THE Job_List_View SHALL optionally display a "Profit" column showing per-job profit when the Admin enables it

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying per-job financial calculations
5. THE Platform SHALL include an E2E_Test using agent-browser that opens a job detail page and verifies the Financials section displays revenue, costs, and profit

---

### Requirement 58: Customer Acquisition Cost Tracking

**User Story:** As an Admin, I want to track customer acquisition cost by marketing channel, so that I can optimize marketing spend.

**Gap Refs:** Sys Req Accounting #13, Sys Req Marketing #2

#### Acceptance Criteria

1. THE Platform SHALL calculate CAC per lead source as: total_marketing_spend_for_source / number_of_converted_customers_from_source
2. THE Platform SHALL expose a GET /api/v1/marketing/cac endpoint returning CAC per lead source for a given date range
3. THE Marketing_Dashboard SHALL display CAC per channel in a comparison chart
4. THE expense tracking system SHALL support tagging marketing expenses with a lead_source to enable per-channel spend tracking

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying CAC calculation with various spend and conversion scenarios
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/marketing` and verifies CAC per channel is displayed

---


### Requirement 59: Tax and Write-Off Tracking

**User Story:** As an Admin, I want a tax section tracking material spending, insurance, equipment usage, office materials, CRM costs, subcontracting, and other write-offs, so that I can prepare for tax filing.

**Gap Refs:** Sys Req Accounting #16

#### Acceptance Criteria

1. THE Accounting_Dashboard SHALL display a "Tax Preparation" section showing expense totals by tax-relevant categories: Materials, Insurance, Equipment Purchase, Equipment Service/Maintenance, Office Supplies, CRM/Software, Marketing/Advertising, Subcontracting, Fuel/Vehicle, and Other Write-Offs
2. THE Platform SHALL expose a GET /api/v1/accounting/tax-summary endpoint returning totals per tax category for a given tax year
3. THE tax summary SHALL include total revenue per job type for income reporting
4. THE tax summary SHALL be exportable as a CSV file for accountant handoff

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying tax category aggregation
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/accounting`, navigates to the Tax Preparation section, and verifies category totals are displayed

---

### Requirement 60: Receipt Photo Storage with Amount Extraction

**User Story:** As an Admin, I want to upload receipt photos and have the system extract the amount and assign a category, so that expense entry is fast and accurate.

**Gap Refs:** Sys Req Accounting #17

#### Acceptance Criteria

1. THE expense creation form SHALL support receipt photo upload with automatic amount extraction using OCR (via OpenAI Vision API or similar)
2. WHEN a receipt photo is uploaded, THE Platform SHALL send the image to the OCR service and pre-populate the amount, vendor, and suggested category fields
3. THE Admin SHALL be able to review and correct the extracted values before saving
4. THE Platform SHALL store the receipt photo in S3 linked to the expense record via receipt_file_key
5. THE Platform SHALL expose a POST /api/v1/expenses/extract-receipt endpoint that accepts an image and returns extracted fields

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying OCR response parsing and field extraction
7. THE Platform SHALL include an E2E_Test using agent-browser that opens the expense creation form, uploads a receipt image, and verifies the amount field is pre-populated

---

### Requirement 61: Tax Estimation and Projections

**User Story:** As an Admin, I want to see estimated total tax due updated throughout the season and "what-if" spending projections, so that I can plan for tax obligations.

**Gap Refs:** Sys Req Accounting #18, #19

#### Acceptance Criteria

1. THE Accounting_Dashboard SHALL display an "Estimated Tax Due" widget showing the estimated tax liability based on current revenue minus deductible expenses, using a configurable effective tax rate
2. THE Platform SHALL expose a GET /api/v1/accounting/tax-estimate endpoint returning estimated_tax_due, effective_tax_rate, taxable_income, and total_deductions
3. THE Accounting_Dashboard SHALL include a "What-If Projections" tool where the Admin can input hypothetical expenses or revenue and see the impact on estimated tax due
4. THE Platform SHALL expose a POST /api/v1/accounting/tax-projection endpoint that accepts hypothetical_revenue and hypothetical_expenses and returns the projected tax impact

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying tax estimation calculation with various revenue and expense scenarios
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/accounting`, views the Estimated Tax Due widget, opens the What-If Projections tool, enters a hypothetical expense, and verifies the projected tax impact updates

---

### Requirement 62: Banking/Financial Account Integration

**User Story:** As an Admin, I want to connect credit cards and bank accounts for automatic spend tracking, so that expenses are captured without manual entry.

**Gap Refs:** Sys Req Accounting #15

#### Acceptance Criteria

1. THE Platform SHALL integrate with a financial data provider (e.g., Plaid) to connect bank accounts and credit cards
2. THE Platform SHALL expose a POST /api/v1/accounting/connect-account endpoint that initiates the Plaid Link flow and stores the access token
3. THE Platform SHALL run a daily background job (`sync_transactions`) that fetches new transactions from connected accounts
4. WHEN new transactions are fetched, THE Platform SHALL create expense records with auto-categorization based on merchant category codes
5. THE Admin SHALL be able to review, recategorize, and approve auto-imported transactions before they are finalized
6. THE Accounting_Dashboard SHALL display a "Connected Accounts" section showing linked accounts and sync status

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying transaction-to-expense mapping and auto-categorization
8. THE Platform SHALL include an E2E_Test using agent-browser that opens `/accounting`, navigates to Connected Accounts, and verifies the section is displayed (actual Plaid connection requires manual testing)

---

### Requirement 63: Marketing Dashboard — Lead Source Analytics

**User Story:** As an Admin, I want a marketing dashboard showing where leads come from, advertising channels, and key marketing metrics, so that I can optimize marketing strategy.

**Gap Refs:** Sys Req Marketing #1, #3, #5

#### Acceptance Criteria

1. THE Platform SHALL create a Marketing_Dashboard page at `/marketing` accessible from the main navigation
2. THE Marketing_Dashboard SHALL display a "Lead Sources" chart showing lead volume by source (website, google_ad, referral, social_media, qr_code, email_campaign, text_campaign, phone_call, etc.) for a configurable date range
3. THE Marketing_Dashboard SHALL display a "Conversion Funnel" showing: Total Leads → Contacted → Qualified → Converted, with conversion rates between each stage
4. THE Marketing_Dashboard SHALL display key metrics: total leads this period, conversion rate, average time to conversion, top performing lead source, and lead source trend over time
5. THE Platform SHALL expose a GET /api/v1/marketing/lead-analytics endpoint returning lead counts by source, conversion rates, and funnel metrics
6. THE Marketing_Dashboard SHALL display an "Advertising Channels" section listing active advertising placements with spend and lead count per channel

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying lead analytics calculations (conversion rates, funnel metrics)
8. THE Platform SHALL include a functional test verifying lead source aggregation from real lead data
9. THE Platform SHALL include an E2E_Test using agent-browser that opens `/marketing`, verifies the Lead Sources chart is displayed, verifies the Conversion Funnel shows stage counts, and changes the date range filter

---

### Requirement 64: Marketing Budget Tracking

**User Story:** As an Admin, I want to track marketing and advertising budget by channel, so that I can manage spend and measure ROI.

**Gap Refs:** Sys Req Marketing #4

#### Acceptance Criteria

1. THE Platform SHALL add a `marketing_budgets` table with fields: id (UUID), channel (VARCHAR — e.g., "Google Ads", "Facebook", "Flyers", "QR Codes"), budget_amount (DECIMAL(10,2)), period_start (DATE), period_end (DATE), actual_spend (DECIMAL(10,2), default 0), notes (TEXT, nullable), created_at, updated_at
2. THE Platform SHALL expose CRUD endpoints for marketing budgets at /api/v1/marketing/budgets
3. THE Marketing_Dashboard SHALL display a "Budget vs Actual" chart comparing budgeted amount to actual spend per channel
4. THE Platform SHALL link marketing expenses (from the expense tracking system with category MARKETING) to marketing budget channels for automatic actual_spend calculation

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying budget vs actual calculation
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/marketing`, views the Budget vs Actual chart, creates a new budget entry, and verifies it appears in the chart

---

### Requirement 65: QR Code Generation for Marketing

**User Story:** As an Admin, I want to generate QR codes that link to landing pages or lead forms with tracking parameters, so that I can use them on flyers and physical marketing materials.

**Gap Refs:** Sys Req Lead Intake #4 (QR codes)

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/marketing/qr-codes endpoint that accepts a target_url and campaign_name and returns a QR code image (PNG) with UTM parameters appended for tracking
2. THE Marketing_Dashboard SHALL include a "QR Codes" section where the Admin can generate, download, and manage QR codes
3. THE generated QR code URL SHALL include utm_source=qr_code, utm_campaign={campaign_name}, and utm_medium=print parameters
4. THE Platform SHALL track QR code scans by counting leads created with lead_source=QR_CODE and matching utm_campaign

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying QR code generation with correct UTM parameters
6. THE Platform SHALL include an E2E_Test using agent-browser that opens `/marketing`, navigates to QR Codes, generates a QR code, and verifies the download link is available

---

### Requirement 66: Navigation and Route Registration

**User Story:** As an Admin, I want all new dashboard pages (Sales, Accounting, Marketing) accessible from the main navigation, so that I can reach any section of the CRM quickly.

**Gap Refs:** Implicit — all new dashboards need navigation integration

#### Acceptance Criteria

1. THE Platform SHALL add navigation items for: Sales (`/sales`), Accounting (`/accounting`), Marketing (`/marketing`), and Communications (`/communications`) to the main sidebar navigation
2. THE Platform SHALL register all new frontend routes in the router configuration
3. THE Platform SHALL register all new backend routers in main.py with appropriate prefixes and tags
4. THE navigation items SHALL show active state highlighting when the user is on the corresponding page

#### Testing Requirements

5. THE Platform SHALL include an E2E_Test using agent-browser that opens the application, verifies all navigation items are visible in the sidebar, clicks each one, and verifies the correct page loads

---

### Requirement 67: Comprehensive E2E Test Suite

**User Story:** As a developer running an autonomous overnight test loop, I want a comprehensive agent-browser E2E test suite that validates all major user flows, so that regressions are caught without human supervision.

**Gap Refs:** Cross-cutting testing requirement

#### Acceptance Criteria

1. THE Platform SHALL include an E2E test runner script (`scripts/e2e-tests.sh`) that executes all agent-browser validation scripts sequentially and reports pass/fail for each
2. THE E2E test suite SHALL cover these critical flows:
   - Login and session persistence
   - Dashboard: all widgets display data, alert navigation works, job status counts are clickable
   - Customers: list, detail, edit notes, edit preferences, view photos, view invoice history, merge duplicates
   - Leads: list with city column, filter by tags, bulk outreach, create estimate, attach documents
   - Jobs: list with correct columns (Customer, Tags, Days Waiting, Due By), filter by simplified status
   - Schedule: calendar displays events with "Staff - Job Type" format, drag-and-drop, lead time indicator, inline customer info, manual job addition with filters
   - Staff Workflow: On My Way → Job Started → Job Complete with payment gate
   - Invoices: list, filter, bulk notify
   - Sales: dashboard metrics, estimate builder, follow-up queue
   - Accounting: dashboard metrics, expense creation, tax summary
   - Marketing: lead source chart, campaign creation, budget tracking
3. THE E2E test suite SHALL output a summary report with total tests, passed, failed, and screenshots of failures
4. THE E2E test suite SHALL be idempotent — running it multiple times SHALL produce the same results (tests clean up after themselves or use isolated test data)
5. EACH E2E test script SHALL include proper wait conditions (`wait --load networkidle`, `wait --text`, `wait <selector>`) to handle async loading

#### Testing Requirements

6. THE Platform SHALL include a meta-test that runs the E2E suite against a fresh test environment and verifies all tests pass
7. THE E2E test runner SHALL support a `--headed` flag for debugging individual test failures

---

### Requirement 68: Service Agreement Flow Preservation

**User Story:** As an Admin, I want the existing service package agreement flow — checkout, webhook processing, agreement creation, and automatic job generation — to remain completely untouched and fully functional throughout all CRM gap closure work, so that the revenue-critical agreement pipeline is never disrupted.

**Gap Refs:** Cross-cutting preservation constraint

#### Acceptance Criteria

1. THE Platform SHALL NOT modify any models, services, routes, schemas, or frontend components belonging to the service-package-purchases feature, including but not limited to: `ServiceAgreement`, `ServiceAgreementTier`, `AgreementJob`, the Stripe checkout session creation endpoint (`POST /checkout/create-session`), the Stripe webhook handler (`POST /webhooks/stripe`), the onboarding consent flow (`POST /onboarding/consent`), and the agreement-to-job generation pipeline
2. WHEN any migration in this spec adds or modifies columns on tables referenced by the agreement flow (e.g., `customers`, `jobs`, `invoices`), THE migration SHALL use nullable columns or defaults that do not break existing agreement-generated records
3. WHEN any service in this spec modifies Job creation, Invoice creation, or Customer update logic, THE service SHALL preserve the existing code paths used by the agreement flow without alteration
4. THE Platform SHALL NOT modify the Stripe webhook event handling for `checkout.session.completed` or any agreement-related webhook events
5. THE Platform SHALL NOT alter the surcharge calculator, zone/pump/backflow pricing logic, or tier configuration used by the agreement flow

#### Testing Requirements

6. THE Platform SHALL include a regression test suite (`test_agreement_flow_preservation.py`) that verifies the complete agreement flow end-to-end: tier retrieval → checkout session creation → webhook processing → agreement record creation → job generation → job-customer linkage
7. THE regression test suite SHALL be run BEFORE any migration or code change in this spec is applied, establishing a baseline
8. THE regression test suite SHALL be run AFTER every major feature implementation in this spec to confirm no regression
9. THE Platform SHALL include an E2E_Test using agent-browser that navigates to the service package purchase flow, verifies tier selection is functional, verifies the checkout redirect works, and verifies existing agreements display correctly on the customer detail page
10. THE Platform SHALL include a functional test verifying that agreement-generated jobs still appear correctly in the Job_List_View with all expected fields (target dates, customer linkage, subscription source)

---

### Requirement 69: Rate Limiting

**User Story:** As an Admin, I want all API endpoints protected by rate limiting, so that the system is resilient against brute-force attacks and abuse.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL implement rate limiting middleware using a Redis-backed rate limiter (e.g., slowapi or fastapi-limiter)
2. THE Platform SHALL enforce these rate limits:
   - Login endpoint (`POST /auth/login`): 5 requests per minute per IP
   - Public lead submission (`POST /api/v1/leads`): 10 requests per minute per IP
   - Public chat endpoint (`POST /api/v1/chat/public`): 10 requests per minute per session
   - Webhook endpoints (`/webhooks/*`): 100 requests per minute per IP
   - General authenticated API endpoints: 200 requests per minute per user
   - File upload endpoints: 20 requests per minute per user
3. WHEN a rate limit is exceeded, THE Platform SHALL return HTTP 429 Too Many Requests with a `Retry-After` header
4. THE Platform SHALL log rate limit violations with event `security.rate_limit.exceeded` including IP address, endpoint, and user_id (if authenticated)

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying rate limit enforcement returns 429 after threshold
6. THE Platform SHALL include an E2E_Test using agent-browser that rapidly submits a form and verifies a rate limit message appears

---

### Requirement 70: Security Headers Middleware

**User Story:** As an Admin, I want the application to send proper security headers on all responses, so that common web vulnerabilities (clickjacking, MIME sniffing, XSS) are mitigated.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL add a SecurityHeadersMiddleware that sets the following headers on all responses:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production only)
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 0` (disabled in favor of CSP)
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
2. THE Platform SHALL add a Content-Security-Policy header that restricts script sources to `'self'` and trusted CDN domains, restricts frame-ancestors to `'none'`, and restricts form-action to `'self'`
3. THE SecurityHeadersMiddleware SHALL be configurable via environment variables to allow CSP adjustments per deployment environment

#### Testing Requirements

4. THE Platform SHALL include a unit test verifying all security headers are present on API responses
5. THE Platform SHALL include an E2E_Test using agent-browser that loads the application and verifies no console security warnings related to missing headers

---

### Requirement 71: Secure Token Storage (Frontend)

**User Story:** As an Admin, I want my authentication tokens stored securely so that they are not vulnerable to XSS attacks.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL migrate JWT token storage from localStorage to httpOnly cookies set by the backend
2. THE backend auth endpoints SHALL set tokens via `Set-Cookie` with flags: `HttpOnly`, `Secure` (production), `SameSite=Lax`, `Path=/`, and a configurable `Max-Age`
3. THE frontend API client SHALL stop reading tokens from localStorage and instead rely on cookies being sent automatically with credentials
4. THE frontend SHALL remove any existing tokens from localStorage on first load after the migration
5. THE CSRF middleware SHALL continue to protect state-changing requests since cookies are now used for auth

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying the auth endpoint sets httpOnly cookies with correct flags
7. THE Platform SHALL include a functional test verifying the frontend can authenticate and make API calls using cookie-based auth
8. THE Platform SHALL include an E2E_Test using agent-browser that logs in, verifies no auth token is visible in localStorage (via `eval "localStorage.getItem('auth_token')"`), and verifies authenticated API calls succeed

---

### Requirement 72: JWT Secret Validation and Key Rotation

**User Story:** As an Admin, I want the system to reject insecure JWT secrets and support key rotation, so that authentication cannot be compromised by default or leaked keys.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL validate at startup that `JWT_SECRET_KEY` is not the default value `"dev-secret-key-change-in-production"` when `ENVIRONMENT` is set to `production` or `staging`
2. IF the JWT secret is the default value in production, THEN THE Platform SHALL refuse to start and log a CRITICAL error with event `security.jwt.insecure_secret`
3. THE Platform SHALL enforce a minimum JWT secret length of 32 characters in production
4. THE Platform SHALL support JWT key rotation by accepting a `JWT_PREVIOUS_SECRET_KEY` environment variable — tokens signed with the previous key SHALL be accepted for a configurable grace period (default 24 hours) but new tokens SHALL only be signed with the current key

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying startup fails with default secret in production mode
6. THE Platform SHALL include a unit test verifying key rotation accepts tokens signed with the previous key within the grace period

---

### Requirement 73: Request Size Limits

**User Story:** As an Admin, I want request body sizes limited to prevent denial-of-service attacks via oversized payloads.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL enforce a default maximum request body size of 10MB for all API endpoints
2. THE Platform SHALL allow file upload endpoints (photos, attachments, receipts, media) to accept up to 50MB per request
3. WHEN a request exceeds the size limit, THE Platform SHALL return HTTP 413 Payload Too Large
4. THE Platform SHALL log oversized request attempts with event `security.request.payload_too_large` including IP address and endpoint

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying oversized requests are rejected with 413
6. THE Platform SHALL include a unit test verifying file upload endpoints accept up to 50MB

---

### Requirement 74: Admin Audit Trail

**User Story:** As an Admin, I want all administrative actions logged in an audit trail, so that I can review who did what and when for accountability and compliance.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL add an `audit_log` table with fields: id (UUID), actor_id (FK to staff), actor_role (VARCHAR), action (VARCHAR — e.g., "customer.merge", "invoice.bulk_notify", "staff.create"), resource_type (VARCHAR), resource_id (UUID), details (JSONB — action-specific metadata), ip_address (VARCHAR), user_agent (TEXT), created_at (TIMESTAMP)
2. THE Platform SHALL log the following actions to the audit trail: customer merge, customer delete, bulk outreach, bulk invoice notification, staff creation/modification, campaign sends, payment collection, estimate approval/rejection, schedule modifications, and any data export
3. THE Platform SHALL expose a GET /api/v1/audit-log endpoint (Admin-only) that returns paginated audit entries with filtering by action, actor, resource_type, and date range
4. THE Accounting_Dashboard SHALL include an "Audit Log" section showing recent administrative actions

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying audit log entries are created for each auditable action
6. THE Platform SHALL include a functional test verifying the audit log endpoint returns correctly filtered results
7. THE Platform SHALL include an E2E_Test using agent-browser that performs an admin action (e.g., customer merge), navigates to the audit log, and verifies the action appears

---

### Requirement 75: Input Validation and Sanitization for All New Endpoints

**User Story:** As an Admin, I want all user inputs validated and sanitized across every new endpoint, so that injection attacks and malformed data are prevented.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. ALL new API endpoints SHALL use Pydantic schemas with strict validation for request bodies — no raw dict or untyped JSON accepted
2. ALL string fields in Pydantic schemas SHALL enforce maximum length constraints appropriate to the field (e.g., names ≤ 100 chars, notes ≤ 5000 chars, descriptions ≤ 2000 chars)
3. ALL file upload endpoints SHALL validate: file extension against an allowlist, MIME type matches extension, file size within limits, and file content (magic bytes) matches declared type
4. ALL endpoints accepting IDs SHALL validate UUID format before database queries
5. THE Platform SHALL sanitize all user-provided text that will be rendered in HTML (customer portal, email templates) to prevent XSS — using HTML escaping or a sanitization library
6. THE Platform SHALL validate and sanitize all query parameters used in database filtering to prevent SQL injection via raw query construction (even though SQLAlchemy ORM is used, any raw SQL must use parameterized queries)

#### Testing Requirements

7. THE Platform SHALL include unit tests verifying Pydantic schema validation rejects: oversized strings, invalid UUIDs, disallowed file types, and malformed input
8. THE Platform SHALL include a unit test verifying HTML sanitization strips script tags and event handlers from user-provided text

---

### Requirement 76: PII Protection in Logs

**User Story:** As an Admin, I want personally identifiable information (phone numbers, emails, addresses) masked in all log output, so that customer data is protected even if logs are exposed.

**Gap Refs:** Security hardening (cross-cutting)

#### Acceptance Criteria

1. THE Platform SHALL implement a structlog processor that automatically masks PII fields in log output: phone numbers (show last 4 digits only), email addresses (show first char + domain only), street addresses (show city/state only), and payment card numbers (never logged)
2. THE PII masking processor SHALL be applied globally to all structlog loggers
3. THE Platform SHALL never log: full phone numbers, full email addresses, full street addresses, payment card numbers, JWT tokens, API keys, passwords, or Stripe customer IDs
4. THE Platform SHALL log masked versions where context is needed: `phone=***1234`, `email=j***@example.com`

#### Testing Requirements

5. THE Platform SHALL include a unit test verifying the PII masking processor correctly masks phone, email, and address fields
6. THE Platform SHALL include a unit test verifying that logging a dict containing PII fields produces masked output

---

### Requirement 77: Secure File Upload and Storage

**User Story:** As an Admin, I want all file uploads (photos, receipts, attachments, media) handled securely with virus scanning considerations and access control, so that malicious files cannot compromise the system.

**Gap Refs:** Security hardening for Reqs 9, 15, 33, 49, 53, 60

#### Acceptance Criteria

1. ALL file upload endpoints SHALL validate file content by checking magic bytes (file signatures) against the declared content type — reject mismatches
2. ALL uploaded files SHALL be stored with randomized S3 keys (UUID-based) that do not expose original filenames in the URL
3. ALL file download URLs SHALL be pre-signed with a configurable expiration (default 1 hour) — no publicly accessible permanent URLs
4. THE Platform SHALL strip EXIF metadata from uploaded images before storage to prevent GPS location leakage
5. THE Platform SHALL enforce per-user upload quotas: maximum 500MB total storage per customer record, configurable via environment variable
6. THE Photo_Service SHALL log all upload and download operations with event `file.upload.completed` and `file.download.requested` including file_key, content_type, and file_size (but NOT the file content)

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying magic byte validation rejects a file with mismatched extension and content
8. THE Platform SHALL include a unit test verifying EXIF stripping removes GPS data from a test image
9. THE Platform SHALL include a unit test verifying pre-signed URLs expire after the configured duration

---

### Requirement 78: Portal Token Security

**User Story:** As a customer using the estimate review and contract signing portal, I want my portal access tokens to be secure and time-limited, so that unauthorized access to my estimates and contracts is prevented.

**Gap Refs:** Security hardening for Req 16

#### Acceptance Criteria

1. ALL customer portal tokens SHALL be cryptographically random UUIDs (v4) with at least 128 bits of entropy
2. ALL portal tokens SHALL have a configurable expiration (default 30 days) after which they return HTTP 410 Gone with a message explaining the link has expired
3. THE Platform SHALL rate-limit portal token access to 20 requests per minute per token to prevent enumeration attacks
4. WHEN a customer approves an estimate or signs a contract, THE Platform SHALL invalidate the token for further modifications (read-only access remains for 90 days)
5. THE Platform SHALL log all portal access attempts with event `portal.access.attempted` including token (last 8 chars only), IP address, and user agent
6. THE customer portal SHALL NOT expose any internal IDs (customer_id, lead_id, staff_id) in the response — only the estimate/contract content and approval actions

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying expired tokens return 410
8. THE Platform SHALL include a unit test verifying tokens are invalidated after approval/signing
9. THE Platform SHALL include an E2E_Test using agent-browser that opens a portal link, verifies estimate content is displayed, and verifies no internal IDs are visible in the page source

---

### Requirement 79: AppointmentStatus Enum Alignment (Live Bug Fix)

**User Story:** As a staff member, I want to mark an appointment as "No Show" when a customer misses their appointment, and as an Admin, I want the system to not crash when this action is taken, so that appointment tracking accurately reflects real-world outcomes.

**Gap Refs:** Data Model Gap Analysis — AppointmentStatus enum mismatch (live bug)

#### Acceptance Criteria

1. THE Platform SHALL add `PENDING = "pending"` to the `AppointmentStatus` Python enum in `enums.py` as the initial state before confirmation
2. THE Platform SHALL add `NO_SHOW = "no_show"` to the `AppointmentStatus` Python enum in `enums.py` as a terminal state for missed appointments
3. THE Platform SHALL create a migration that updates the CHECK constraint on `appointments.status` to accept all 8 values: `pending`, `scheduled`, `confirmed`, `en_route`, `in_progress`, `completed`, `cancelled`, `no_show`
4. THE frontend `markNoShow()` function (which sends `{ status: 'no_show' }` to `PATCH /appointments/{id}`) SHALL succeed without a database constraint violation after this migration is applied
5. THE `no_show` status SHALL be treated as a terminal state (no further transitions allowed, same as `completed` and `cancelled`)

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying that updating an appointment status to `no_show` succeeds and persists correctly
7. THE Platform SHALL include a unit test verifying that `pending` is accepted as a valid initial appointment status
8. THE Platform SHALL include a functional test that creates an appointment, transitions it through `scheduled` → `confirmed`, then marks it as `no_show`, and verifies the database record reflects the correct status

---

### Requirement 80: Invoice PDF Generation

**User Story:** As an Admin, I want to generate professional PDF documents for invoices that can be downloaded and emailed to customers, so that customers receive formal, printable invoices rather than just data on a screen.

**Gap Refs:** Data Model Gap Analysis — Invoice document_url, PDF generation

#### Acceptance Criteria

1. THE Platform SHALL add a `document_url` column (VARCHAR(500), nullable) to the `invoices` table to store the S3 key of the generated PDF
2. THE Platform SHALL expose a `POST /api/v1/invoices/{id}/generate-pdf` endpoint that generates a professional PDF using WeasyPrint (HTML→PDF), uploads it to S3 at `invoices/{invoice_id}.pdf`, updates the invoice's `document_url`, and returns the pre-signed download URL
3. THE Platform SHALL expose a `GET /api/v1/invoices/{id}/pdf` endpoint that returns a pre-signed S3 download URL (1-hour expiry) for an existing invoice PDF. If no PDF has been generated, it SHALL return HTTP 404 with a descriptive message
4. THE invoice PDF SHALL include: company branding (logo, address, phone), customer name and address, invoice number, invoice date, due date, line items table (description, quantity, unit price, total), subtotal, late fees (if any), total amount due, payment instructions, and payment status
5. THE Invoice_Detail_View SHALL display a "Download PDF" button that calls the generate-pdf endpoint (or retrieves existing) and triggers a browser download
6. WHEN an invoice is sent via the notification service (reminders, completion notifications), THE system SHALL auto-generate the PDF if not already generated and include the download link in the notification
7. THE Platform SHALL log PDF generation with event `invoice.pdf.generated` including invoice_id, file_size, and generation_time_ms

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying PDF generation produces a valid PDF file with correct invoice data
9. THE Platform SHALL include a functional test verifying the generate-pdf endpoint stores the file in S3 and updates document_url
10. THE Platform SHALL include an E2E_Test using agent-browser that navigates to an invoice detail page, clicks "Download PDF", and verifies a file download is initiated

---

### Requirement 81: SentMessage Constraint Fix for Lead Communication

**User Story:** As an Admin, I want the system to be able to send and track SMS messages to leads who haven't been converted to customers yet, so that lead confirmation messages and estimate notifications are properly recorded.

**Gap Refs:** Data Model Gap Analysis — SentMessage customer_id NOT NULL, message_type CHECK constraint

#### Acceptance Criteria

1. THE Platform SHALL create a migration that alters `sent_messages.customer_id` from NOT NULL to nullable, allowing records where the recipient is a lead (not yet a customer)
2. THE Platform SHALL add a `lead_id` column (UUID, nullable, FK→leads.id) to the `sent_messages` table for linking messages to unconverted leads
3. THE Platform SHALL add a CHECK constraint ensuring at least one of `customer_id` or `lead_id` is non-null: `CHECK (customer_id IS NOT NULL OR lead_id IS NOT NULL)`
4. THE Platform SHALL update the CHECK constraint on `sent_messages.message_type` to include the following new values in addition to existing ones: `lead_confirmation`, `estimate_sent`, `contract_sent`, `review_request`, `campaign`
5. THE lead confirmation SMS flow (Req 46) SHALL create `sent_messages` records with `customer_id = NULL` and `lead_id = {lead_uuid}` and `message_type = 'lead_confirmation'` without any constraint violations
6. THE Platform SHALL update all queries on `sent_messages` that filter by `customer_id` to handle nullable values correctly (e.g., using `COALESCE` or explicit null checks)

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying that a SentMessage record with `customer_id = NULL` and valid `lead_id` inserts successfully
8. THE Platform SHALL include a unit test verifying that a SentMessage record with both `customer_id = NULL` and `lead_id = NULL` fails the CHECK constraint
9. THE Platform SHALL include a unit test verifying that `message_type = 'lead_confirmation'` is accepted by the CHECK constraint
10. THE Platform SHALL include a functional test that creates a lead, triggers SMS confirmation, and verifies the `sent_messages` record is created with correct lead_id linkage

---

### Requirement 82: Outbound Notification History View

**User Story:** As an Admin, I want to see a log of all outbound notifications (SMS, email) sent to customers and leads, so that I can verify notifications were delivered and troubleshoot when customers say they didn't receive something.

**Gap Refs:** UI Gap Analysis — no admin visibility into outbound SMS/email history

#### Acceptance Criteria

1. THE Platform SHALL display a "Sent Messages" tab on the Communications page (`/communications`) alongside the existing "Needs Attention" (inbound) tab, showing all outbound messages from the `sent_messages` table
2. THE Sent Messages tab SHALL display a paginated DataTable with columns: recipient name, recipient phone, message type, content preview (first 80 chars), delivery status badge (pending/sent/delivered/failed), sent_at timestamp
3. THE Sent Messages tab SHALL support filtering by: message type (dropdown), delivery status (dropdown), date range (from/to), and search (recipient name or phone)
4. THE Customer_Detail_View SHALL include a "Messages" section (or tab) showing all outbound messages sent to that specific customer, sorted by date descending
5. THE Platform SHALL color-code delivery status badges: delivered=green, sent=blue, pending=yellow, failed=red
6. WHEN a message has `delivery_status = 'failed'`, THE Platform SHALL display the `error_message` in a tooltip on hover

#### Testing Requirements

7. THE Platform SHALL include a unit test verifying the sent messages list returns correctly filtered and paginated results
8. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/communications`, clicks the "Sent Messages" tab, verifies outbound messages are displayed with delivery status badges

---

### Requirement 83: Estimate Detail View (Admin-Side)

**User Story:** As a Sales staff or Admin, I want to click into an individual estimate and see its full details, history, follow-up log, and take actions (resend, edit, cancel), so that I can manage each estimate through the sales process.

**Gap Refs:** UI Gap Analysis — can create estimates but no admin-side detail/management page

#### Acceptance Criteria

1. THE Platform SHALL expose a route at `/estimates/{id}` that renders an EstimateDetail page
2. THE EstimateDetail page SHALL display: estimate number, customer name + contact info, creation date, status badge, valid_until date, line items table with quantities/prices/totals, tier options (if multi-tier), subtotal, discount, total amount
3. THE EstimateDetail page SHALL include an "Activity Timeline" section showing: when the estimate was created, sent, viewed, approved/rejected (with timestamps and actor info), and all follow-up notifications sent with their status
4. THE EstimateDetail page SHALL include action buttons based on current status: "Edit" (draft only), "Send/Resend" (draft or sent), "Cancel" (any non-terminal status), "Create Job" (approved only)
5. THE EstimateDetail page SHALL show linked documents: the estimate PDF (if generated), any attached contracts, and media library items attached during creation
6. THE Platform SHALL link to EstimateDetail from: the Sales Dashboard pipeline lists, the FollowUpQueue DataTable, the Lead detail AttachmentPanel, and the Appointment EstimateCreator confirmation
7. THE SalesDashboard pipeline cards ("Needs Estimate", "Pending Approval", etc.) SHALL navigate to a filtered estimate list when clicked, and each row in that list SHALL link to the EstimateDetail page

#### Testing Requirements

8. THE Platform SHALL include a unit test verifying the estimate detail endpoint returns all required fields including activity timeline
9. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/sales`, clicks a pipeline card, clicks an estimate row, and verifies the EstimateDetail page displays line items, status, and activity timeline

---

### Requirement 84: Customer Invoice Portal (Public)

**User Story:** As a customer, I want to view my invoice via a secure link from an SMS or email notification, see the amount due, and click a payment link, so that I can pay without needing to log into the CRM.

**Gap Refs:** UI Gap Analysis — no customer-facing invoice viewing page; notification links have no destination

#### Acceptance Criteria

1. THE Platform SHALL add an `invoice_token` column (UUID, nullable) and `invoice_token_expires_at` column (DateTime, nullable) to the `invoices` table for secure public access
2. THE Platform SHALL expose a public (no auth) endpoint at `GET /api/v1/portal/invoices/{token}` that returns invoice data (company name, customer name, invoice number, date, due date, line items, total, amount paid, balance due, payment status) without exposing internal IDs
3. THE Platform SHALL expose a route at `/portal/invoices/{token}` that renders an InvoicePortal page
4. THE InvoicePortal page SHALL display: company branding (logo, name, address, phone), invoice number, invoice date, due date, line items table, total amount, amount already paid, balance remaining, and payment status badge
5. THE InvoicePortal page SHALL include a "Pay Now" button that redirects to the Stripe payment link (if balance > 0) or displays "Paid in Full" confirmation (if balance = 0)
6. THE InvoicePortal page SHALL be mobile-responsive (single-column layout on screens < 768px) since customers will primarily access it from SMS links on their phones
7. WHEN the NotificationService sends invoice-related notifications (reminders, completion receipts), THE notification SHALL include a link to `/portal/invoices/{token}` instead of an internal CRM link
8. THE invoice_token SHALL expire after 90 days and return HTTP 410 Gone with a message to contact the business
9. THE portal response SHALL NOT expose any internal IDs (customer_id, job_id, staff_id)

#### Testing Requirements

10. THE Platform SHALL include a unit test verifying the portal invoice endpoint returns correct data without internal IDs
11. THE Platform SHALL include a unit test verifying expired invoice tokens return 410
12. THE Platform SHALL include an E2E_Test using agent-browser that opens a portal invoice link, verifies invoice content is displayed, verifies "Pay Now" button is present, and verifies no internal IDs are visible in page source

---

### Requirement 85: Rate Limit Error Handling in Frontend

**User Story:** As a user, I want to see a friendly error message when I've made too many requests, so that I understand why my action failed and know to wait before trying again.

**Gap Refs:** UI Gap Analysis — frontend has no 429 response handler; E2E test expects rate limit message

#### Acceptance Criteria

1. THE frontend API client (Axios interceptor) SHALL detect HTTP 429 (Too Many Requests) responses and display a user-friendly toast notification: "Too many requests. Please wait {retry_after} seconds and try again."
2. THE toast SHALL parse the `Retry-After` header from the 429 response to display the wait time; if the header is absent, default to "a moment"
3. THE 429 interceptor SHALL NOT retry the request automatically — it SHALL only show the toast and reject the promise so the calling component can handle it
4. THE toast SHALL use the existing toast/notification system (Radix Toast or equivalent) with a warning/amber style
5. THE 429 handler SHALL be registered alongside the existing 401 interceptor in the API client configuration

#### Testing Requirements

6. THE Platform SHALL include a unit test verifying the Axios interceptor catches 429 responses and triggers a toast with the correct message
7. THE Platform SHALL include an E2E_Test using agent-browser that rapidly submits a form, verifies a rate limit toast message appears with wait time

---

### Requirement 86: Mobile-Responsive Staff Field Views

**User Story:** As a Staff member using my phone in the field, I want all appointment and workflow features to be fully usable on a mobile screen, so that I can complete my work without needing a laptop.

**Gap Refs:** UI Gap Analysis — no explicit mobile design specifications for staff-facing schedule features

#### Acceptance Criteria

1. ALL staff-facing schedule components (StaffWorkflowButtons, PaymentCollector, InvoiceCreator, EstimateCreator, AppointmentNotes, ReviewRequest, AppointmentDetail, BreakButton) SHALL be fully functional and readable on mobile viewports (375px minimum width)
2. THE StaffWorkflowButtons SHALL render as full-width stacked buttons (min-height 48px, touch target ≥ 44px) on screens < 768px
3. THE PaymentCollector form SHALL use a single-column layout on mobile with large input fields (min-height 44px) and a full-width submit button
4. THE AppointmentNotes photo upload SHALL use `accept="image/*;capture=camera"` to open the device camera directly on mobile, with a full-width upload area
5. THE AppointmentDetail enriched view SHALL use a single-column stacked layout on mobile, with collapsible sections for customer info, job details, materials, and directions
6. THE InlineCustomerPanel (Radix Sheet) SHALL render as a full-screen bottom sheet on mobile (height: 90vh) instead of a side panel
7. ALL modal dialogs (JobSelector, PaymentCollector, InvoiceCreator, EstimateCreator) SHALL render as full-screen overlays on mobile with a sticky header containing a close button
8. THE "Get Directions" button on AppointmentDetail SHALL be prominently placed and use `tel:` and `maps:` URL schemes that open native phone/maps apps on mobile

#### Testing Requirements

9. THE Platform SHALL include a unit test verifying that staff workflow components render correctly at 375px viewport width (no horizontal overflow, all buttons visible)
10. THE Platform SHALL include an E2E_Test using agent-browser with a mobile viewport (375x812) that opens an appointment detail, clicks through the workflow buttons, and verifies all actions are accessible

---

### Requirement 87: Settings Page for Business Configuration

**User Story:** As an Admin, I want a Settings page where I can configure business information and system defaults used across the CRM, so that invoices, estimates, notifications, and compliance documents display correct company branding and settings.

**Gap Refs:** UI Gap Analysis — no settings updates for new features (company info, defaults, preferences)

#### Acceptance Criteria

1. THE Platform SHALL add a `business_settings` table with fields: id (UUID), setting_key (VARCHAR, UNIQUE), setting_value (JSONB), updated_by (FK to staff, nullable), updated_at (DateTime)
2. THE Platform SHALL expose CRUD endpoints at `GET /api/v1/settings` (list all) and `PATCH /api/v1/settings/{key}` (update one) for admin-only access
3. THE Settings page (`/settings`) SHALL include a "Business Information" section with editable fields for: company_name, company_address, company_phone, company_email, company_logo_url (with upload), company_website
4. THE Settings page SHALL include an "Invoice Defaults" section with: default_payment_terms_days (number input, default 30), late_fee_percentage (number input), lien_warning_days (number input, default 45), lien_filing_days (number input, default 120)
5. THE Settings page SHALL include a "Notification Preferences" section with: day_of_reminder_time (time picker, default 7:00 AM CT), sms_time_window_start (time picker, default 8:00 AM), sms_time_window_end (time picker, default 9:00 PM), enable_delay_notifications (toggle, default true)
6. THE Settings page SHALL include an "Estimate Defaults" section with: default_valid_days (number input, default 30), follow_up_intervals_days (comma-separated, default "3,7,14,21"), enable_auto_follow_ups (toggle, default true)
7. THE InvoicePDFService SHALL read company_name, company_address, company_phone, company_logo_url from business_settings when generating PDFs
8. THE NotificationService SHALL read sms_time_window_start, sms_time_window_end, day_of_reminder_time from business_settings
9. THE Platform SHALL seed default values for all settings on first deployment

#### Testing Requirements

10. THE Platform SHALL include a unit test verifying settings CRUD operations and default seeding
11. THE Platform SHALL include an E2E_Test using agent-browser that navigates to `/settings`, edits the company name, saves, and verifies the change persists on reload

---

## Cross-Reference: Gap Analysis Coverage Matrix

This section maps every gap analysis item to its requirement(s) in this document, ensuring 100% coverage.

### CRM Overall
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Remove fake/test data | Req 1 | Covered |
| 2 | Remove test/fake staff | Req 1 | Covered |
| 3 | Fix random logout | Req 2 | Covered |

### CRM Dashboard
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Alert navigation + highlighting | Req 3 | Covered |
| 2 | Messages widget | Req 4 | Covered |
| 3 | Pending invoices metric | Req 5 | Covered |
| 4 | New leads click → highlight | Req 3 | Covered |
| 5 | Job status alignment | Req 6 | Covered |
| 6 | Job status click → highlight | Req 3 | Covered |

### CRM Customers
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Duplicate review/merge | Req 7 | Covered |
| 2 | Internal notes exposure | Req 8 | Covered |
| 3 | Customer photos | Req 9 | Covered |
| 4 | Invoice history on detail | Req 10 | Covered |
| 5 | Preferred service times editing | Req 11 | Covered |

### CRM Leads
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | City/address collection | Req 12 | Covered |
| 2 | Tag: Need to be contacted | Req 13 | Covered |
| 3 | Tag: Need estimate | Req 13 | Covered |
| 4 | Tag: Estimate status | Req 13 | Covered |
| 5 | Bulk outreach | Req 14 | Covered |
| 6 | Attachments (estimates/contracts) | Req 15 | Covered |
| 7 | Customer estimate review/sign | Req 16 | Covered |
| 8 | Estimate/contract templates | Req 17 | Covered |
| 9 | Estimate → leads reverse flow | Req 18 | Covered |

### CRM Work Requests
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Consolidate into Leads | Req 19 | Covered |

### CRM Jobs
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Notes + summary field | Req 20 | Covered |
| 2 | Status simplification | Req 21 | Covered |
| 3 | Filters | Already DONE | Verified |
| 4 | Remove Category column | Req 22 | Covered |
| 5 | Add Customer name column | Req 22 | Covered |
| 6 | Add Customer tag column | Req 22 | Covered |
| 7 | Days since added | Req 22 | Covered |
| 8 | Completed by date column | Req 23 | Covered |

### CRM Schedule — Creating
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Undo/reverse | Already DONE | Verified |
| 2 | Drag and drop | Req 24 | Covered |
| 3 | Lead time display | Req 25 | Covered |
| 4 | Manual add with filters | Req 26 | Covered |
| 5 | Inline customer info | Req 27 | Covered |
| 6 | Calendar "Staff - Job Type" | Req 28 | Covered |
| 7 | Address auto-populate | Req 29 | Covered |

### CRM Schedule — Staff Features
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 8 | Collect payment on site | Req 30 | Covered |
| 9 | Invoice on the spot | Req 31 | Covered |
| 10 | Estimate on the spot | Req 32 | Covered |
| 11 | Staff notes and photos | Req 33 | Covered |
| 12 | Remove customer tags from schedule | Already DONE | Verified |
| 13 | Google review request | Req 34 | Covered |
| 14 | Staff workflow buttons | Req 35 | Covered |
| 15 | Payment required before complete | Req 36 | Covered |
| 16 | Time tracking between buttons | Req 37 | Covered |
| 17 | Remove "Mark as scheduled" | Already DONE | Verified |

### CRM Generate Routes
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Route generation in schedule | Already DONE | Verified |

### CRM Invoices
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Filter invoices | Already DONE | Verified |
| 2 | Track per invoice fields | Already DONE | Verified |
| 3 | Color coding | Already DONE | Verified |
| 4 | Mass notify | Req 38 | Covered |
| 5 | Invoice data in CRM | Already DONE | Verified |

### Sys Req: Lead Intake
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Website + AI text bot | Already DONE | Verified |
| 2 | AI chatbot on website | Req 43 | Covered |
| 3 | Calls/texts AI | Req 44 | Covered |
| 4 | Marketing (mass, QR codes) | Req 45, 65 | Covered |
| 5 | Service tier signup | Already DONE (service-package-purchases spec) | Verified |
| 6 | Work request form | Already DONE | Verified |
| 7 | SCHEDULE/FOLLOW_UP routing | Already DONE | Verified |
| 8 | Admin follow-up section | Already DONE | Verified |
| 9 | Customer info collection | Req 12 (city/address gaps) | Covered |
| 10 | Text/email confirmation | Req 46 | Covered |
| 11 | AI agents + human escalation | Req 43, 44 | Covered |
| 12 | Central database | Already DONE | Verified |
| 13 | Database stores photos/videos | Req 9 | Covered |

### Sys Req: Scheduling
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Scheduling dashboard | Already DONE | Verified |
| 2 | Lead time | Req 25 | Covered |
| 3 | Appointment slot enrichment | Req 40 | Covered |
| 4 | Staff sees own schedule | Already DONE | Verified |
| 5 | Route understanding | Already DONE | Verified |
| 6 | Admin GPS tracking | Req 41 | Covered |
| 7 | Day-of notification | Req 39 | Covered |
| 8 | On my way notification | Req 39 | Covered |
| 9 | Delay notification | Req 39 | Covered |
| 10 | Arrival notification | Req 39 | Covered |
| 11 | Staff workflow process | Req 35 | Covered |
| 12 | Staff estimates on spot | Req 32 | Covered |
| 13 | Staff invoices on spot | Req 31 | Covered |
| 14 | Completion notification | Req 39 | Covered |
| 15 | Staff breaks | Req 42 | Covered |
| 16 | Payment on-site | Req 30 | Covered |
| 17 | Time warnings | Req 37 | Covered |
| 18 | Additional estimate approval | Req 32 | Covered |

### Sys Req: Sales
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Sales dashboard | Req 47 | Covered |
| 2 | Sales staff access | Req 47 | Covered |
| 3 | Estimate templates | Req 17, 48 | Covered |
| 4 | Price adjustment options | Req 48 | Covered |
| 5 | Photos/videos/testimonials | Req 49 | Covered |
| 6 | Property diagram builder | Req 50 | Covered |
| 7 | Estimate promotions | Req 48 | Covered |
| 8 | Customer receives materials + sign | Req 16 | Covered |
| 9 | Sales staff estimate detail view | Req 47, 48 | Covered |
| 10 | Promotional follow-up options | Req 51 | Covered |
| 11 | Automated follow-up notifications | Req 51 | Covered |

### Sys Req: Accounting
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | General dashboard (YTD profit/revenue) | Req 52 | Covered |
| 2 | Pending invoices with total | Req 52 | Covered |
| 3 | Past due invoices with total | Req 52 | Covered |
| 4 | Spending by category | Req 53 | Covered |
| 5 | Average profit margin | Req 53 | Covered |
| 6 | Auto-notify 3 days before/weekly after | Req 54 | Covered |
| 7 | 30-day lien notification | Req 55 | Covered |
| 8 | Lien rules (service type) | Already DONE | Verified |
| 9 | Credit on file | Req 56 | Covered |
| 10 | Material cost per job | Req 53, 57 | Covered |
| 11 | Staff cost per job | Req 53, 57 | Covered |
| 12 | Total money received per job | Req 57 | Covered |
| 13 | Customer acquisition cost | Req 58 | Covered |
| 14 | Fuel and maintenance costs | Req 53 | Covered |
| 15 | Connect banking | Req 62 | Covered |
| 16 | Tax section | Req 59 | Covered |
| 17 | Receipt photo storage + extraction | Req 60 | Covered |
| 18 | Estimated tax due | Req 61 | Covered |
| 19 | What-if projections | Req 61 | Covered |

### Sys Req: Marketing
| Gap # | Description | Requirement(s) | Status |
|-------|------------|----------------|--------|
| 1 | Dashboard: lead sources | Req 63 | Covered |
| 2 | Average CAC | Req 58 | Covered |
| 3 | Advertising channels | Req 63 | Covered |
| 4 | Budget tracking | Req 64 | Covered |
| 5 | Key metrics | Req 63 | Covered |
| 6 | Mass email/text campaigns | Req 45 | Covered |
| 7 | Automated campaigns | Req 45 | Covered |

---

**Total Gap Items: 123**
**Covered by this spec: 106 (all NOT DONE and PARTIAL items)**
**Already DONE (verified): 17**
**Coverage: 100%**
**Additional Requirements:**
- Req 68 — Service Agreement Flow Preservation (cross-cutting regression protection)
- Req 69-78 — Security hardening (rate limiting, headers, tokens, PII, uploads, audit)
- Req 79 — AppointmentStatus Enum Alignment (live bug fix: no_show, pending)
- Req 80 — Invoice PDF Generation (document_url, WeasyPrint, S3 storage, download endpoint)
- Req 81 — SentMessage Constraint Fix (nullable customer_id, lead_id FK, message_type CHECK update)
- Req 82 — Outbound Notification History View (sent messages tab, customer message history)
- Req 83 — Estimate Detail View (admin-side estimate detail page with activity timeline)
- Req 84 — Customer Invoice Portal (public invoice view with payment link, invoice_token)
- Req 85 — Rate Limit Error Handling in Frontend (429 interceptor with toast notification)
- Req 86 — Mobile-Responsive Staff Field Views (mobile-first design for all staff workflow components)
- Req 87 — Settings Page for Business Configuration (company info, invoice/notification/estimate defaults)
**Additional: Reqs 69-78 — Security Hardening (rate limiting, security headers, secure token storage, JWT validation, request size limits, audit trail, input validation, PII protection, file upload security, portal token security)**
