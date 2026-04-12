# Implementation Plan: CRM Changes Update 2

## Overview

This plan implements all 39 requirements across 7 domains: Auth & Dashboard, Customers, Leads, Sales Pipeline, Jobs, Schedule & On-Site, and Invoice/Onboarding/Renewals. The architecture follows the existing Vertical Slice Architecture with Python/FastAPI backend and React/TypeScript frontend.

**Critical ordering:** Req 21 (missing job actions) blocks the Invoice tab and must be fixed first. Database migrations run before models/services. SignWell integration requires `SIGNWELL_API_KEY` provisioned.

**Implementation languages:** Python 3.11+ (backend), TypeScript 5.9 (frontend).

## Tasks

- [x] 1. Database Migrations — All 8 Alembic migrations in dependency order
  - [x] 1.1 Create migration `001_crm2_customer_extensions` — column additions to existing tables
    - Add `customers.merged_into_customer_id UUID REFERENCES customers(id)` with partial index
    - Add `properties.is_hoa BOOLEAN NOT NULL DEFAULT false`
    - Add `leads.moved_to VARCHAR(20)`, `leads.moved_at TIMESTAMPTZ`, `leads.last_contacted_at TIMESTAMPTZ`, `leads.job_requested VARCHAR(255)` with partial index on `moved_to`
    - Add `customer_photos.job_id UUID REFERENCES jobs(id)` with partial index
    - _Requirements: 5.8, 6.5, 8.2, 9.2, 10.3, 11.2, 26.3_

  - [x] 1.2 Create migration `002_crm2_customer_merge_candidates` — new table
    - Create `customer_merge_candidates` table with id, customer_a_id, customer_b_id, score, match_signals JSONB, status, created_at, resolved_at, resolution
    - Add UNIQUE constraint on (customer_a_id, customer_b_id), indexes on score DESC and status
    - _Requirements: 5.1, 5.6_

  - [x] 1.3 Create migration `003_crm2_customer_documents` — new table
    - Create `customer_documents` table with id, customer_id, file_key, file_name, document_type, mime_type, size_bytes, uploaded_at, uploaded_by
    - Add indexes on customer_id and document_type
    - _Requirements: 17.3_

  - [x] 1.4 Create migration `004_crm2_sales_pipeline` — new tables
    - Create `sales_entries` table with id, customer_id, property_id, lead_id, job_type, status, last_contact_date, notes, override_flag, closed_reason, signwell_document_id, created_at, updated_at
    - Create `sales_calendar_events` table with id, sales_entry_id, customer_id, title, scheduled_date, start_time, end_time, notes, created_at, updated_at
    - Add indexes on sales_entries(status, customer_id) and sales_calendar_events(scheduled_date)
    - _Requirements: 13.3, 14.1, 14.2, 15.1_

  - [x] 1.5 Create migration `005_crm2_confirmation_flow` — new tables
    - Create `job_confirmation_responses` table with id, job_id, appointment_id, sent_message_id, customer_id, from_phone, reply_keyword, raw_reply_body, provider_sid, status, received_at, processed_at
    - Create `reschedule_requests` table with id, job_id, appointment_id, customer_id, original_reply_id, requested_alternatives JSONB, raw_alternatives_text, status, created_at, resolved_at
    - Add indexes on appointment_id, status for both tables
    - _Requirements: 24.6, 25.1_

  - [x] 1.6 Create migration `006_crm2_contract_renewals` — new tables
    - Create `contract_renewal_proposals` table with id, service_agreement_id, customer_id, status, proposed_job_count, created_at, reviewed_at, reviewed_by
    - Create `contract_renewal_proposed_jobs` table with id, proposal_id (CASCADE), service_type, target_start_date, target_end_date, status, proposed_job_payload JSONB, admin_notes, created_job_id
    - Add indexes on proposal status and proposed_jobs(proposal_id)
    - _Requirements: 31.1, 31.5_

  - [x] 1.7 Create migration `007_crm2_service_week_preferences` — column addition
    - Add `service_agreements.service_week_preferences JSONB` column
    - _Requirements: 30.1_

  - [x] 1.8 Create migration `008_crm2_enums` — new enum values
    - Add MessageType values: APPOINTMENT_CONFIRMATION, GOOGLE_REVIEW_REQUEST, ON_MY_WAY
    - Add new enums: SalesEntryStatus, ConfirmationKeyword, DocumentType, ProposalStatus, ProposedJobStatus
    - _Requirements: 14.3, 24.1, 17.3, 31.1_

- [x] 2. Checkpoint — Migrations complete
  - Run `alembic upgrade head` and verify all 8 migrations apply cleanly. Ensure all tests pass, ask the user if questions arise.

- [x] 3. Backend Models and Schemas — SQLAlchemy models + Pydantic schemas for new tables
  - [x] 3.1 Create SQLAlchemy models for new tables
    - `CustomerMergeCandidate` model in `src/grins_platform/models/customer_merge_candidate.py`
    - `CustomerDocument` model in `src/grins_platform/models/customer_document.py`
    - `SalesEntry` and `SalesCalendarEvent` models in `src/grins_platform/models/sales.py` (new)
    - `JobConfirmationResponse` and `RescheduleRequest` models in `src/grins_platform/models/job_confirmation.py` (new)
    - `ContractRenewalProposal` and `ContractRenewalProposedJob` models in `src/grins_platform/models/contract_renewal.py` (new)
    - Update existing Customer, Property, Lead, CustomerPhoto, ServiceAgreement models with new columns
    - _Requirements: 5.1, 5.6, 6.5, 8.2, 9.2, 13.3, 14.2, 17.3, 24.6, 25.1, 30.1, 31.1_

  - [x] 3.2 Create Pydantic schemas for new models
    - Sales schemas: `SalesEntryCreate`, `SalesEntryResponse`, `SalesEntryStatusUpdate`, `SalesCalendarEventCreate/Response`
    - Customer schemas: `MergeCandidateResponse`, `MergeRequest`, `MergePreviewResponse`, `CustomerDocumentCreate/Response`, `ServicePreferenceCreate/Response`
    - Confirmation schemas: `ConfirmationResponseSchema`, `RescheduleRequestResponse`
    - Contract renewal schemas: `RenewalProposalResponse`, `ProposedJobResponse`, `ProposedJobModification`
    - _Requirements: 5.1, 6.2, 7.5, 14.2, 17.3, 24.6, 25.2, 31.5_

  - [x] 3.3 Add new enum classes to `src/grins_platform/models/enums.py`
    - Add `SalesEntryStatus`, `ConfirmationKeyword`, `DocumentType`, `ProposalStatus`, `ProposedJobStatus` enums
    - Extend `MessageType` with APPOINTMENT_CONFIRMATION, GOOGLE_REVIEW_REQUEST, ON_MY_WAY
    - _Requirements: 14.3, 24.1, 17.3, 31.1_

- [x] 4. BLOCKER FIX — Job-Level Actions (Invoicing and Completion) — Req 21
  - [x] 4.1 Investigate and document missing "Create Invoice" and "Mark Complete" bugs
    - Create `bughunt/job_actions_missing.md` documenting root cause for both bugs
    - _Requirements: 21.3_

  - [x] 4.2 Fix "Create Invoice" action on job detail view
    - Implement `POST /api/v1/jobs/{id}/invoice` endpoint that generates an invoice for the job
    - Wire to existing InvoiceService for template-based invoice generation
    - _Requirements: 21.1_

  - [x] 4.3 Fix "Mark Complete" action on job detail view
    - Implement `POST /api/v1/jobs/{id}/complete` endpoint that transitions job status to COMPLETED
    - _Requirements: 21.2_

  - [x] 4.4 Write unit tests for job invoice and complete actions
    - Test invoice creation from job, test status transition to COMPLETED
    - _Requirements: 21.1, 21.2_

- [x] 5. Checkpoint — Blocker fix verified
  - Ensure job invoice and complete actions work. Ensure all tests pass, ask the user if questions arise.

- [x] 5.1 E2E Visual Validation — Job Actions Blocker Fix
  - Start backend + frontend dev servers
  - Use agent-browser to navigate to a job detail page, verify "Create Invoice" and "Mark Complete" buttons are visible and functional
  - Click "Create Invoice" — verify invoice is created, screenshot the invoice detail
  - Navigate to /invoices — verify the new invoice appears in the list with correct customer/job data
  - Navigate back to job detail, click "Mark Complete" — verify job status transitions to COMPLETED
  - Navigate to /schedule — verify the completed job is archived out of the active schedule view
  - Navigate to /jobs — verify the completed job is still visible under a "Completed" status filter
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/blocker-fix/`
  - If any visual or functional issue is found, fix it and re-validate

- [x] 6. Auth & Dashboard Domain (Req 1–4, 38–39)
  - [x] 6.1 Implement password hardening migration script
    - Standalone script (not Alembic) that reads `NEW_ADMIN_PASSWORD` env var, validates 16+ chars/mixed case/digits/symbol, hashes with bcrypt cost 12, updates admin staff row
    - Abort with descriptive error if env var missing or password fails criteria
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 6.2 Investigate and document session timeout bug
    - Create `bughunt/session_timeout.md` documenting root cause of premature logout
    - Fix refresh token flow or cookie configuration if bug found
    - Maintain existing 60-min access / 30-day refresh unless investigation proves change needed
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 6.3 Implement dashboard alert-to-record navigation (backend)
    - Extend dashboard alert API responses to include `target_url` with `?highlight=<id>` query params
    - Single-record alerts link to detail page; multi-record alerts link to filtered list view
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 6.4 Implement dashboard alert-to-record navigation (frontend)
    - Add `HighlightRow.tsx` shared component with amber/yellow pulse animation fading over 3 seconds
    - Parse `?highlight=<id>` from URL, apply highlight + auto-scroll to first matching row
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 6.5 Remove Estimates and New Leads sections from Dashboard
    - Remove standalone Estimates card/section and New Leads section from Dashboard view
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 6.6 Write unit tests for password hardening and dashboard navigation
    - Test password validation criteria, bcrypt hashing, env var missing abort
    - Test highlight URL param parsing, alert target URL generation
    - _Requirements: 1.1, 1.2, 1.4, 3.1, 3.4_

- [x] 7. Customers Domain — Duplicate Detection, Merge, Preferences, Property Tags (Req 5–8)

- [x] 6.7 E2E Visual Validation — Auth & Dashboard Domain
  - Use agent-browser to navigate to /dashboard, verify Estimates section and New Leads section are removed
  - Verify the dashboard still renders all remaining sections correctly (no layout breakage)
  - Click a single-record dashboard alert — verify navigation goes directly to the record's detail page (not the list)
  - Click a multi-record dashboard alert — verify navigation to filtered list with `?highlight=<id>` in URL
  - Verify amber/yellow pulse animation on highlighted rows fades over ~3 seconds
  - Verify auto-scroll to first matching row on the filtered list
  - Refresh the page with the highlight URL — verify the highlight state survives the refresh
  - Test login/logout flow — verify no premature logout during normal navigation between tabs
  - Check `agent-browser console` and `agent-browser errors` for any JS errors
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/auth-dashboard/`
  - If any visual or functional issue is found, fix it and re-validate
  - [x] 7.1 Implement DuplicateDetectionService
    - Create `src/grins_platform/services/duplicate_detection_service.py`
    - `compute_score(customer_a, customer_b) -> int` with weighted signals: phone E.164 (+60), email lowercased (+50), Jaro-Winkler name ≥0.92 (+25), normalized address (+20), ZIP+last name (+10), capped at 100
    - `run_nightly_sweep(db) -> int` with pre-filtered candidate pairs (shared phone/email/ZIP/last name), upsert into customer_merge_candidates
    - `get_review_queue(db, skip, limit)` sorted by score descending
    - Register nightly sweep in background_jobs.py scheduler
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x] 7.2 Write property tests for duplicate score computation
    - **Property 1: Duplicate Score Commutativity** — score(A,B) == score(B,A)
    - **Validates: Requirements 32.1**
    - **Property 2: Duplicate Score Self-Identity** — score(A,A) == max_possible_score
    - **Validates: Requirements 32.2**
    - **Property 3: Duplicate Score Zero Floor** — no matching signals → score == 0
    - **Validates: Requirements 32.3**
    - **Property 4: Duplicate Score Bounded** — 0 <= score <= 100
    - **Validates: Requirements 32.4**

  - [x] 7.3 Implement CustomerMergeService
    - Create `src/grins_platform/services/customer_merge_service.py`
    - `check_merge_blockers(db, primary_id, duplicate_id)` — block if both have active Stripe subscriptions
    - `preview_merge(db, primary_id, duplicate_id, field_selections) -> MergePreview`
    - `execute_merge(db, primary_id, duplicate_id, field_selections, admin_id)` — reassign all related records (jobs, invoices, communications, agreements, properties), soft-delete duplicate via merged_into_customer_id, write audit log
    - Default non-empty field values when one record has empty, allow admin override via radio buttons
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10, 6.11, 6.12_

  - [x] 7.4 Write property test for customer merge data conservation
    - **Property 11: Customer Merge Data Conservation** — total jobs/invoices/communications before == total after on surviving record, duplicate.merged_into_customer_id == primary.id, audit log exists
    - **Validates: Requirements 35.1, 35.2, 35.3**

  - [x] 7.5 Implement customer duplicate check on create/convert
    - Synchronous Tier 1 check (exact phone or email) when customer is created or lead is converted
    - Display inline "Possible match found" warning with "Use existing customer" button
    - _Requirements: 6.13_

  - [x] 7.6 Implement customer service preferences CRUD
    - Add `service_preferences` JSON array field handling on customer model
    - CRUD endpoints for service preferences: Add, Edit, Delete
    - Modal with fields: service type dropdown, preferred week (week picker), preferred date, time window dropdown, notes
    - Auto-populate job Week_Of from matching preference on job creation
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 7.7 Implement property type tagging
    - Ensure `property_type` enum (residential/commercial) is required on Property model
    - Add `is_hoa` boolean field support
    - Derive `is_subscription_property` at query time from active service_agreement
    - Add filtering by property_type, is_hoa, is_subscription_property on Customers, Jobs, Sales list views
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.8 Implement customer duplicate/merge API endpoints
    - `GET /api/v1/customers/duplicates` — paginated review queue
    - `POST /api/v1/customers/{id}/merge` — execute merge with field_selections
    - _Requirements: 6.1, 6.3_

  - [x] 7.9 Implement customer documents API endpoints
    - `POST /api/v1/customers/{id}/documents` — upload (max 25MB, validated MIME types)
    - `GET /api/v1/customers/{id}/documents` — list documents
    - `GET /api/v1/customers/{id}/documents/{doc_id}/download` — presigned S3 URL
    - `DELETE /api/v1/customers/{id}/documents/{doc_id}` — delete
    - Use existing PhotoService S3 infrastructure
    - _Requirements: 17.2, 17.3_

  - [x] 7.10 Build customer duplicate review and merge frontend
    - `DuplicateReviewQueue.tsx` — review queue with count badge, sorted by score descending
    - `MergeComparisonModal.tsx` — side-by-side field comparison with radio buttons, preview, confirm
    - Stripe subscription blocker error display, ambiguity resolution modal
    - _Requirements: 6.1, 6.2, 6.3, 6.7, 6.12_

  - [x] 7.11 Build customer service preferences frontend
    - `ServicePreferencesSection.tsx` — list preferences with Add/Edit/Delete on customer detail
    - `ServicePreferenceModal.tsx` — form with service type, week picker, date picker, time window, notes
    - _Requirements: 7.5, 7.6_

  - [x] 7.12 Build PropertyTags shared component
    - `PropertyTags.tsx` in `frontend/src/shared/components/` — compact badges for Residential/Commercial, HOA, Subscription
    - Reusable across Jobs, Customers, Sales (3+ features)
    - _Requirements: 8.4_

  - [x] 7.13 Write unit tests for DuplicateDetectionService and CustomerMergeService
    - Test scoring algorithm with various signal combinations
    - Test merge blockers (dual Stripe subscriptions), reassignment logic, soft-delete
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 6.4, 6.5, 6.7_

- [x] 8. Checkpoint — Customers domain complete
  - Ensure duplicate detection, merge, preferences, and property tags all work. Ensure all tests pass, ask the user if questions arise.

- [x] 8.1 E2E Visual Validation — Customers Domain
  - Use agent-browser to navigate to /customers, verify "Review Duplicates" button with count badge is visible
  - Click "Review Duplicates" — verify the review queue loads with pairs sorted by score descending
  - Click a duplicate pair — verify side-by-side comparison modal opens with radio buttons for each conflicting field
  - Select a primary record, click "Confirm Merge" — verify the merge completes, duplicate disappears from customer list
  - Navigate to the surviving customer detail — verify all jobs/invoices/properties from the duplicate are now linked to the surviving record
  - Navigate to a customer detail page — verify "Service Preferences" section is visible with Add/Edit/Delete actions
  - Click "Add Preference" — verify modal opens with all fields: service type dropdown, week picker, date picker, time window dropdown, notes
  - Fill out and save a preference — verify it appears in the preferences list
  - Edit the preference — verify the edit modal pre-fills with existing values
  - Delete the preference — verify it disappears from the list
  - Verify PropertyTags badges (Residential/Commercial, HOA, Subscription) display on customer detail view
  - Navigate to /jobs — verify PropertyTags badges display on each job row
  - Test property type filtering on Customers list — filter by Residential, then Commercial, then HOA, then Subscription
  - Test creating a new customer — verify "Possible match found" inline warning appears if phone/email matches an existing customer
  - Test document upload on a customer — upload a PDF, verify it appears in the documents list, download it, delete it
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/customers/`
  - If any visual or functional issue is found, fix it and re-validate

- [x] 9. Leads Domain — Deletion, Column Reorder, Status, Move-Out (Req 9–12)
  - [x] 9.1 Implement lead deletion and move-out backend
    - `DELETE /api/v1/leads/{id}` — hard delete with confirmation
    - `POST /api/v1/leads/{id}/move-to-jobs` — auto-generate customer if needed, create Job with TO_BE_SCHEDULED, set lead.moved_to='jobs'
    - `POST /api/v1/leads/{id}/move-to-sales` — auto-generate customer if needed, create SalesEntry with 'schedule_estimate', set lead.moved_to='sales'
    - `PUT /api/v1/leads/{id}/contacted` — set status to "Contacted (Awaiting Response)", set last_contacted_at
    - Filter leads list query to exclude `moved_to IS NOT NULL`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 11.1, 11.2, 12.1, 12.2_

  - [x] 9.2 Implement auto-update of last_contacted_at from SMS/email
    - When outbound/inbound SMS/email tied to a lead is processed, auto-update lead's last_contacted_at
    - _Requirements: 11.3_

  - [x] 9.3 Update LeadsList frontend — column reorder and new columns
    - Remove color highlighting from lead source column
    - Move lead source column to far right
    - Add "Job Requested" column in source's old position
    - Add "City" column after Job Address (derived from address data)
    - Remove "Intake" column
    - Add "Last Contacted Date" column
    - Add "Move to Jobs" and "Move to Sales" action buttons per row
    - Add delete button with confirmation modal per row
    - Support exactly two statuses: "New" (default) and "Contacted (Awaiting Response)"
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.1, 11.4, 12.3_

  - [x] 9.4 Write unit tests for lead move-out and deletion
    - Test customer auto-generation on move, job/sales entry creation, lead filtering
    - Test hard delete, confirmation flow
    - _Requirements: 9.1, 9.2, 12.1, 12.2_

- [ ] 10. Sales Pipeline Domain — New Tab, Statuses, Calendar, SignWell, Documents (Req 13–18)

- [x] 9.5 E2E Visual Validation — Leads Domain
  - Use agent-browser to navigate to /leads, verify column order: Job Requested visible in source's old position, City column after address, lead source at far right, Intake column removed
  - Verify no color highlighting on lead source column
  - Verify "Last Contacted Date" column is visible
  - Verify exactly two status tags available: "New" and "Contacted (Awaiting Response)"
  - Click the "Contacted" button on a lead — verify status changes to "Contacted (Awaiting Response)" and Last Contacted Date updates
  - Verify "Move to Jobs" and "Move to Sales" action buttons on each lead row
  - Click "Move to Jobs" on a lead — verify lead disappears from Leads list
  - Navigate to /jobs — verify a new job with status TO_BE_SCHEDULED exists for that lead's customer
  - Navigate to /customers — verify a customer record was auto-generated for the lead
  - Navigate back to /leads, click "Move to Sales" on another lead — verify lead disappears
  - Navigate to /sales — verify a new sales entry with status "Schedule Estimate" exists
  - Navigate back to /leads, click the delete button on a lead — verify confirmation modal appears with permanent deletion warning
  - Confirm deletion — verify the lead is gone from the list
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/leads/`
  - If any visual or functional issue is found, fix it and re-validate
  - [x] 10.1 Implement SalesPipelineService
    - Create `src/grins_platform/services/sales_pipeline_service.py`
    - `create_from_lead(db, lead_id) -> SalesEntry` — create pipeline entry from lead move-out
    - `advance_status(db, entry_id, action) -> SalesEntry` — enforce VALID_TRANSITIONS, one step forward per action
    - `manual_override_status(db, entry_id, new_status)` — admin escape hatch with audit log
    - `convert_to_job(db, entry_id, force=False) -> Job` — create job from sales entry, signature gating, force override with audit log
    - _Requirements: 14.3, 14.4, 14.5, 14.7, 14.8, 14.9, 16.1, 16.2, 16.3, 16.4_

  - [x] 10.2 Write property tests for sales pipeline status transitions
    - **Property 5: Sales Pipeline Status Transition Validity** — advance_status result ∈ VALID_TRANSITIONS[current_status]
    - **Validates: Requirements 33.1**
    - **Property 6: Sales Pipeline Terminal State Immutability** — CLOSED_WON/CLOSED_LOST raise InvalidSalesTransitionError
    - **Validates: Requirements 33.2**
    - **Property 7: Sales Pipeline Idempotent Advance** — action advances exactly one step forward
    - **Validates: Requirements 33.3**

  - [x] 10.3 Implement SignWellClient service
    - Create `src/grins_platform/services/signwell/__init__.py`, `config.py`, `client.py`
    - `SignWellSettings` with SIGNWELL_API_KEY, SIGNWELL_WEBHOOK_SECRET env vars
    - `create_document_for_email(pdf_url, email, name)`, `create_document_for_embedded(pdf_url, signer_name)`, `get_embedded_url(document_id)`, `fetch_signed_pdf(document_id)`, `verify_webhook_signature(payload, signature)`
    - _Requirements: 18.1, 18.3, 18.5, 18.6_

  - [x] 10.4 Implement SignWell webhook endpoint
    - `POST /api/v1/webhooks/signwell` — verify HMAC-SHA256 signature, handle document_completed event
    - Fetch signed PDF, store as CustomerDocument with document_type "signed_contract"
    - Advance sales_entry status from pending_approval to send_contract
    - _Requirements: 14.6, 17.4, 18.4_

  - [x] 10.5 Implement Sales API endpoints
    - `GET /api/v1/sales` — list pipeline entries with summary boxes
    - `GET /api/v1/sales/{id}` — detail view
    - `POST /api/v1/sales/{id}/advance` — action-button status advance
    - `PUT /api/v1/sales/{id}/status` — manual status override
    - `POST /api/v1/sales/{id}/sign/email` — trigger email signing (disable if no customer email)
    - `POST /api/v1/sales/{id}/sign/embedded` — get embedded signing URL
    - `POST /api/v1/sales/{id}/convert` — convert to job (signature gated)
    - `POST /api/v1/sales/{id}/force-convert` — force convert with audit log
    - `DELETE /api/v1/sales/{id}` — mark lost
    - _Requirements: 14.1, 14.2, 14.4, 14.5, 14.8, 14.10, 16.1, 16.2, 16.3, 16.4, 18.1, 18.2, 18.3_

  - [x] 10.6 Implement Sales Calendar API endpoints
    - `GET /api/v1/sales/calendar/events` — list estimate appointments
    - `POST /api/v1/sales/calendar/events` — create estimate appointment
    - `PUT /api/v1/sales/calendar/events/{id}` — update
    - `DELETE /api/v1/sales/calendar/events/{id}` — delete
    - Keep separate from main Jobs schedule calendar
    - _Requirements: 15.1, 15.2, 15.3_

  - [x] 10.7 Implement Work Requests → Sales data migration script
    - One-time migration converting existing work request records to sales_entries
    - Map work request status to closest SalesEntryStatus, preserve customer_id, property_id, notes
    - _Requirements: 13.3_

  - [ ] 10.8 Build Sales Pipeline frontend — main list view
    - Create `frontend/src/features/sales/` feature slice
    - `SalesPipeline.tsx` — 4 summary boxes (migrated from Work Requests) + pipeline table with columns: Customer Name, Phone, Address, Job Type, Status, Last Contact Date
    - `StatusActionButton.tsx` — auto-advancing action buttons per status
    - Add Sales tab to navigation, remove Work Requests tab
    - _Requirements: 13.1, 13.2, 14.1, 14.2, 14.3, 14.4_

  - [ ] 10.9 Build Sales Detail view frontend
    - `SalesDetail.tsx` — expanded per-entry view with documents section, email signing action, embedded on-site signing action
    - `DocumentsSection.tsx` — upload/download/preview/delete documents (PDFs, images, docs up to 25MB)
    - `SignWellEmbeddedSigner.tsx` — iframe + postMessage listener for on-site signing (~50 lines)
    - _Requirements: 14.10, 17.1, 17.2, 18.1, 18.3_

  - [ ] 10.10 Build Sales Calendar frontend
    - `SalesCalendar.tsx` — dedicated estimate scheduling calendar, independent from main schedule
    - _Requirements: 15.1, 15.2, 15.3_

  - [ ] 10.11 Write unit tests for SalesPipelineService and SignWellClient
    - Test status transitions, terminal state enforcement, convert-to-job with/without signature
    - Test SignWell HTTP calls mocked via respx, webhook signature verification
    - _Requirements: 14.3, 14.6, 16.1, 16.2, 18.5_

- [ ] 11. Checkpoint — Sales pipeline complete
  - Ensure Sales tab, pipeline statuses, SignWell integration, documents, and calendar all work. Ensure all tests pass, ask the user if questions arise.

- [ ] 11.1 E2E Visual Validation — Sales Pipeline Domain
  - Use agent-browser to verify Work Requests tab is removed from navigation and Sales tab is present
  - Navigate to /sales, verify 4 summary boxes at top are unchanged from old Work Requests
  - Verify pipeline list view with columns: Customer Name, Phone, Address, Job Type, Status, Last Contact Date
  - Test the full status auto-advance flow: click each action button in sequence and verify status progresses exactly one step at a time (Schedule Estimate → Estimate Scheduled → Send Estimate → Pending Approval → Send Contract)
  - Verify clicking the same action button twice does NOT skip a step
  - Click a sales entry row — verify expanded detail view opens with documents section
  - Test document upload: upload a PDF, verify it appears in the documents list
  - Test document download: click download, verify presigned URL works
  - Test document delete: delete the document, verify it disappears
  - Verify "Convert to Job" button is disabled with tooltip "Waiting for customer signature" when no signature is on file
  - Test "Force Convert to Job" — verify confirmation modal appears with override warning
  - Confirm force convert — verify job is created in Jobs tab and sales entry moves to Closed-Won with override_flag
  - Verify "Mark Lost" button — click it, verify status changes to Closed-Lost
  - Verify terminal states (Closed-Won, Closed-Lost) have no further action buttons
  - Test manual status override dropdown — verify it allows jumping to any valid status
  - Test email signing button — verify it's disabled when customer has no email (check tooltip text)
  - Navigate to Sales Calendar — verify it renders independently from main schedule
  - Test creating an estimate appointment on the Sales Calendar — verify it saves and displays
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/sales-pipeline/`
  - If any visual or functional issue is found, fix it and re-validate

- [ ] 12. Jobs Domain — Property Tags, Week Of, On-Site Operations (Req 19–20, 26–27)
  - [ ] 12.1 Implement Week Of semantic rename and WeekPicker
    - Create `WeekPicker.tsx` shared component in `frontend/src/shared/components/` — calendar highlighting full weeks, selects Monday–Sunday range
    - Backend `align_to_week(date) -> (Monday, Sunday)` utility function
    - Rename UI column "Due By" to "Week Of" in Jobs list, replace date picker with week picker
    - Display as "Week of M/D/YYYY" (Monday date)
    - Auto-populate Week_Of from customer service preference on job creation
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5_

  - [ ] 12.2 Write property tests for Week Of date alignment
    - **Property 12: Week Of Date Alignment** — target_start_date is Monday, target_end_date is Sunday, end == start + 6 days
    - **Validates: Requirements 36.1, 36.2**
    - **Property 13: Week Of Round-Trip** — align_to_week(monday) == (monday, monday + 6 days)
    - **Validates: Requirements 36.3**

  - [ ] 12.3 Update Job detail view with property address and tags
    - Display full street address (street, city, state, ZIP) on job detail
    - Display PropertyTags badges (Residential/Commercial, HOA, Subscription)
    - Show same badges on Jobs list view per row
    - Support filtering Jobs list by property_type, is_hoa, is_subscription_property
    - _Requirements: 19.1, 19.2, 19.3, 19.4_

  - [ ] 12.4 Implement on-site operation endpoints
    - `POST /api/v1/jobs/{id}/on-my-way` — send SMS via SMSService (ON_MY_WAY), log timestamp
    - `POST /api/v1/jobs/{id}/started` — log timestamp
    - `POST /api/v1/jobs/{id}/notes` — add note, sync to customer record + link to job_id
    - `POST /api/v1/jobs/{id}/photos` — upload via PhotoService, link to job_id via customer_photos.job_id FK
    - `POST /api/v1/jobs/{id}/review-push` — send SMS (GOOGLE_REVIEW_REQUEST) with tracked deep link
    - _Requirements: 26.1, 26.2, 26.3, 26.4, 27.1, 27.2_

  - [ ] 12.5 Implement job complete with payment warning modal
    - Update `POST /api/v1/jobs/{id}/complete` to check for payment/invoice before completing
    - If no payment and no invoice: return warning requiring confirmation
    - "Complete Anyway" path writes audit log entry recording override
    - Auto-track time elapsed between On My Way → Started → Complete as structured metadata
    - Archive completed jobs out of active schedule view, keep in Jobs tab under "Completed" filter
    - _Requirements: 27.3, 27.4, 27.5, 27.6, 27.7_

  - [ ] 12.6 Build on-site operations frontend on job detail view
    - Add "On My Way", "Job Started", "Job Complete" status buttons
    - Payment warning modal with Cancel / "Complete Anyway" options
    - Notes and photos sections linked to job_id
    - Google review push button
    - _Requirements: 26.1, 26.2, 26.3, 26.4, 27.1, 27.2, 27.3, 27.4, 27.5_

  - [ ] 12.7 Write unit tests for on-site operations and week alignment
    - Test on-my-way SMS sending, timestamp logging, payment warning logic
    - Test align_to_week function, week picker date range
    - _Requirements: 20.2, 27.1, 27.3, 27.4_

- [ ] 13. Schedule & Confirmation Domain — Job Picker, Y/R/C Flow, Reschedule Queue (Req 22–25)
  - [ ] 13.1 Implement JobConfirmationService
    - Create `src/grins_platform/services/job_confirmation_service.py`
    - `parse_confirmation_reply(body) -> ConfirmationKeyword | None` — Y/R/C keyword parser (case-insensitive, whitespace-trimmed)
    - `handle_confirmation(db, thread_id, keyword, raw_body, from_phone)` — orchestrate appointment status transition + auto-reply
    - CONFIRM: SCHEDULED → CONFIRMED + auto-reply
    - RESCHEDULE: create reschedule_request + follow-up SMS + surface in admin queue
    - CANCEL: SCHEDULED → CANCELLED + auto-reply + admin notification
    - None: log with status "needs_review"
    - Correlate via provider_thread_id, use only abstract InboundSMS dataclass
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7, 24.8_

  - [ ] 13.2 Write property tests for Y/R/C keyword parser
    - **Property 8: Y/R/C Keyword Parser Completeness** — all known keywords map correctly, unknown inputs return None
    - **Validates: Requirements 34.1, 34.2, 34.3, 34.4**
    - **Property 9: Y/R/C Parser Idempotency** — parse(input) == parse(input)
    - **Validates: Requirements 34.5**
    - **Property 10: Y/R/C Parser Case Insensitivity** — parse(upper) == parse(lower)
    - **Validates: Requirements 34.1, 34.2, 34.3**

  - [ ] 13.3 Wire Y/R/C confirmation into existing SMS inbound webhook
    - Extend existing CallRail inbound webhook handler to detect APPOINTMENT_CONFIRMATION thread_id
    - Route to JobConfirmationService.handle_confirmation when matched
    - Send outbound confirmation SMS on appointment creation via SMSService
    - _Requirements: 24.1, 24.2, 24.3, 24.4_

  - [ ] 13.4 Implement reschedule requests API and admin queue
    - `GET /api/v1/schedule/reschedule-requests` — list open requests grouped by status
    - `PUT /api/v1/schedule/reschedule-requests/{id}/resolve` — mark resolved
    - _Requirements: 25.1, 25.2, 25.3, 25.4_

  - [ ] 13.5 Implement schedule visual distinction and job picker
    - CSS for confirmed (solid border, full color) vs unconfirmed (dashed border, muted) appointments
    - `JobPickerPopup.tsx` — popup mirroring Jobs tab columns/filters/search for manual schedule assignment
    - Bulk assignment: select multiple jobs → assign to date + staff member with global time allocation
    - Per-job time adjustments after bulk assignment
    - _Requirements: 22.1, 22.2, 22.3, 23.1, 23.2_

  - [ ] 13.6 Build reschedule requests queue frontend
    - `RescheduleRequestsQueue.tsx` — admin queue showing customer name, original appointment, requested alternatives, action buttons
    - "Reschedule to Alternative" opens appointment editor pre-filled
    - "Mark Resolved" closes the request
    - _Requirements: 25.1, 25.2, 25.3, 25.4_

  - [ ] 13.7 Write unit tests for JobConfirmationService
    - Test keyword parsing, confirmation handling, reschedule request creation, cancel flow
    - Test thread_id correlation, needs_review fallback
    - _Requirements: 24.2, 24.3, 24.4, 24.5_

- [ ] 14. Checkpoint — Jobs, Schedule, and Confirmation domains complete
  - Ensure Week Of, property tags, on-site ops, Y/R/C flow, reschedule queue, and job picker all work. Ensure all tests pass, ask the user if questions arise.

- [ ] 14.1 E2E Visual Validation — Jobs Domain
  - Use agent-browser to navigate to /jobs, verify "Week Of" column label (not "Due By"), verify week picker renders on click
  - Click the week picker — select a week, verify it writes "Week of M/D/YYYY" format with the Monday date
  - Verify the week picker selects the full Monday–Sunday range (not a single day)
  - Verify PropertyTags badges (Residential/Commercial, HOA, Subscription) on each job row
  - Test filtering Jobs list by Residential only, then Commercial only, then HOA, then Subscription — verify each filter works independently
  - Test combining multiple property filters — verify AND composition
  - Click into a job detail — verify full property address (street, city, state, ZIP) is displayed
  - Verify PropertyTags badges on the job detail view match the list view
  - Verify service preference notes appear as a read-only hint on job detail (if customer has matching preference)
  - Verify "On My Way", "Job Started", "Job Complete" status buttons are visible and in correct order
  - Click "On My Way" — verify timestamp is logged, navigate to communications log to verify SMS was sent
  - Click "Job Started" — verify timestamp is logged
  - Click "Job Complete" without payment/invoice — verify payment warning modal appears with "No Payment or Invoice on File" message
  - Click "Cancel" on the modal — verify job stays in current status
  - Click "Job Complete" again, then "Complete Anyway" — verify job transitions to COMPLETED with audit log
  - Test adding a note from job detail — verify it syncs to the customer record
  - Test uploading a photo from job detail — verify it appears in the photos section and is linked to the job
  - Test Google review push button — verify SMS is sent (check communications log)
  - Navigate to /jobs, apply "Completed" status filter — verify the completed job appears
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/jobs/`
  - If any visual or functional issue is found, fix it and re-validate

- [ ] 14.2 E2E Visual Validation — Schedule & Confirmation Domain
  - Use agent-browser to navigate to /schedule, verify confirmed appointments have solid border/full color and unconfirmed have dashed border/muted background
  - Take side-by-side screenshots of confirmed vs unconfirmed appointments for visual comparison
  - Open the job picker popup — verify it mirrors the Jobs tab columns/filters/search exactly
  - Test bulk assignment: select 2+ jobs from the picker, assign to a specific date + staff member with a global time allocation
  - Verify all selected jobs appear on the schedule for the chosen date
  - Test per-job time adjustment after bulk assignment — verify the time can be changed individually
  - Navigate to Reschedule Requests queue — verify it displays customer name, original appointment, requested alternatives, action buttons
  - Click "Reschedule to Alternative" — verify the appointment editor opens pre-filled with the selected alternative date/time
  - Click "Mark Resolved" on a request — verify the request disappears from the open queue
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/schedule/`
  - If any visual or functional issue is found, fix it and re-validate

- [ ] 15. Invoice Domain — Full Filtering, Status Colors, Mass Notifications (Req 28–29)
  - [ ] 15.1 Implement 9-axis invoice filtering backend
    - Extend `GET /api/v1/invoices` with composable AND-based query builder
    - 9 axes: date range (created/due/paid), status, customer, job, amount range, payment type, days until due, days past due, invoice number
    - All filters compose via AND (intersection)
    - _Requirements: 28.1_

  - [ ] 15.2 Write property tests for invoice filter composition
    - **Property 14: Invoice Filter Composition** — result(A ∪ B) == result(A) ∩ result(B)
    - **Validates: Requirements 37.1**
    - **Property 15: Invoice Filter URL Round-Trip** — deserialize(serialize(filter_state)) == filter_state
    - **Validates: Requirements 37.2**
    - **Property 16: Invoice Filter Clear-All Identity** — clear_all returns unfiltered result set
    - **Validates: Requirements 37.3**

  - [ ] 15.3 Implement mass notification endpoint
    - `POST /api/v1/invoices/mass-notify` — bulk SMS/email to past-due, due-soon, lien-eligible customers
    - Configurable templates per notification type
    - Lien eligibility: 60+ days past due AND over $500 (configurable)
    - _Requirements: 29.3, 29.4_

  - [ ] 15.4 Build FilterPanel shared component
    - `FilterPanel.tsx` in `frontend/src/shared/components/` — collapsible panel with all 9 filter axes
    - Chip badges for active filters, "Clear all filters" button
    - URL persistence via useSearchParams() for bookmarkable/shareable filtered views
    - Reusable across Invoices, Jobs, Customers, Sales (4+ features)
    - _Requirements: 28.2, 28.3, 28.4, 28.5_

  - [ ] 15.5 Update InvoiceList frontend
    - Columns: Invoice Number, Customer Name, Job (link), Cost, Status, Days Until Due, Days Past Due, Payment Type
    - Status colors: green (Complete), yellow (Pending), red (Past Due)
    - Mass notification action buttons
    - Real-time invoice state changes reflected in Customer detail view
    - _Requirements: 29.1, 29.2, 29.3, 29.5_

  - [ ] 15.6 Write unit tests for invoice filtering and mass notifications
    - Test each filter axis individually and in combination
    - Test URL serialization/deserialization round-trip
    - Test mass notification targeting logic
    - _Requirements: 28.1, 28.3, 29.3_

- [ ] 16. Onboarding & Contract Renewals Domain (Req 30–31)

- [ ] 15.7 E2E Visual Validation — Invoice Domain
  - Use agent-browser to navigate to /invoices, verify FilterPanel is visible (collapsible sidebar or drawer)
  - Test each of the 9 filter axes individually:
    - Date range: set a created date range, verify results narrow
    - Status: select "Past Due" only, verify only red-badged invoices show
    - Customer: search and select a customer, verify only their invoices show
    - Job: search and select a job, verify only that job's invoice shows
    - Amount: set min=500, verify only invoices ≥$500 show
    - Payment type: select "Cash", verify only cash invoices show
    - Days until due: set range 0-7, verify only soon-due invoices show
    - Days past due: set min=30, verify only 30+ day past-due invoices show
    - Invoice number: enter an exact invoice number, verify only that invoice shows
  - Test combining 3+ filters simultaneously — verify AND composition (results narrow with each added filter)
  - Verify active filters show as removable chip badges above the list
  - Click a chip badge "×" to remove a filter — verify the list updates
  - Click "Clear all filters" — verify the full unfiltered list returns
  - Copy the URL with filters applied, open in a new tab — verify the same filter state and results load
  - Test "Save this filter" option — save a filter combination, verify it can be recalled
  - Verify status colors: green (Complete), yellow (Pending), red (Past Due) on status badges
  - Verify invoice list columns: Invoice Number, Customer Name, Job (link), Cost, Status, Days Until Due, Days Past Due, Payment Type
  - Click the Job link in an invoice row — verify it navigates to the correct job detail
  - Test mass notification buttons — verify the targeting criteria UI works
  - Navigate to a customer detail page — verify invoice state changes are reflected in real-time
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/invoices/`
  - If any visual or functional issue is found, fix it and re-validate
  - [ ] 16.1 Implement week-based job auto-population in onboarding
    - Add `WeekPickerStep.tsx` to onboarding wizard — per-service week selection restricted to valid month ranges
    - Store selections as `service_week_preferences` JSON on ServiceAgreement
    - Extend job generator to read service_week_preferences and set target_start_date/target_end_date via align_to_week()
    - Fall back to existing calendar-month defaults if preferences are null
    - _Requirements: 30.1, 30.2, 30.3, 30.4, 30.5_

  - [ ] 16.2 Write property test for onboarding week preference round-trip
    - **Property 17: Onboarding Week Preference Round-Trip** — generate_jobs(preferences).week_of_display == preferences.values()
    - **Validates: Requirements 30.6**

  - [ ] 16.3 Implement ContractRenewalReviewService
    - Create `src/grins_platform/services/contract_renewal_service.py`
    - `generate_proposal(db, agreement_id)` — create proposal with proposed jobs, roll forward prior-year preferences by +1 year
    - `approve_all(db, proposal_id, admin_id)` — bulk approve, create real Job records
    - `reject_all(db, proposal_id, admin_id)` — bulk reject
    - `approve_job(db, proposed_job_id, admin_id, modifications=None)` — per-job approve with optional Week Of modification
    - `reject_job(db, proposed_job_id, admin_id)` — per-job reject
    - Fall back to hardcoded calendar-month defaults if no prior preferences
    - _Requirements: 31.1, 31.2, 31.3, 31.6, 31.7, 31.8, 31.10_

  - [ ] 16.4 Wire contract renewal into Stripe webhook
    - On `invoice.paid` for auto_renew=true agreements, call generate_proposal() instead of creating jobs directly
    - Fire dashboard alert: "1 contract renewal ready for review: {customer_name}"
    - _Requirements: 31.1, 31.4_

  - [ ] 16.5 Implement Contract Renewals API endpoints
    - `GET /api/v1/contract-renewals` — list pending proposals
    - `GET /api/v1/contract-renewals/{id}` — proposal detail with proposed jobs
    - `POST /api/v1/contract-renewals/{id}/approve-all` — bulk approve
    - `POST /api/v1/contract-renewals/{id}/reject-all` — bulk reject
    - `POST /api/v1/contract-renewals/{id}/jobs/{job_id}/approve` — per-job approve
    - `POST /api/v1/contract-renewals/{id}/jobs/{job_id}/reject` — per-job reject
    - `PUT /api/v1/contract-renewals/{id}/jobs/{job_id}` — modify proposed job (Week Of, admin_notes)
    - _Requirements: 31.5, 31.6, 31.7, 31.8, 31.9, 31.10, 31.11_

  - [ ] 16.6 Build Contract Renewals frontend
    - Create `frontend/src/features/contract-renewals/` feature slice
    - `RenewalReviewList.tsx` — pending proposals with columns: Customer, Agreement, Proposed job count, Created date, Actions
    - `RenewalProposalDetail.tsx` — per-job approve/reject/modify with admin_notes, "Approve All" and "Reject All" bulk actions
    - Add Contract Renewals navigation entry
    - _Requirements: 31.5, 31.6, 31.7, 31.8, 31.9, 31.10, 31.11_

  - [ ] 16.7 Write unit tests for ContractRenewalReviewService
    - Test proposal generation, date rolling (+1 year), approve/reject flows
    - Test fallback to calendar-month defaults
    - _Requirements: 31.1, 31.2, 31.3, 31.6, 31.10_

- [ ] 17. Checkpoint — Onboarding and renewals complete
  - Ensure week-based onboarding, contract renewal review queue, and all approval flows work. Ensure all tests pass, ask the user if questions arise.

- [ ] 17.1 E2E Visual Validation — Onboarding & Contract Renewals Domain
  - Use agent-browser to navigate to the onboarding wizard, verify the week picker step appears for each service in the package
  - Verify week pickers are restricted to valid month ranges per service type (e.g., Spring Startup only selectable in March–May)
  - Select weeks for each service — verify the selections are visually confirmed
  - Complete the onboarding flow through Stripe checkout
  - Navigate to /jobs — verify jobs were auto-generated with the correct "Week Of" dates matching the selected weeks
  - Verify the generated jobs are tagged as "Subscription" (from service agreement)
  - Navigate to Contract Renewal Reviews page — verify pending proposals list with columns: Customer, Agreement, Proposed job count, Created date, Actions
  - Click into a proposal — verify per-job detail view with Approve/Reject/Modify actions on each proposed job row
  - Verify admin_notes free-text field is present on each proposed job
  - Test modifying a proposed job's Week Of before approving — verify the modification is saved
  - Test "Approve All" — verify all proposed jobs become real Job records in the Jobs tab with correct Week Of dates
  - Test "Reject All" on a different proposal — verify no jobs are created and proposal status is "rejected"
  - Test partial approval: approve some jobs, reject others — verify proposal status becomes "partially_approved"
  - Check `agent-browser console` for any JS errors during the flow
  - Save all screenshots to `e2e-screenshots/crm-changes-update-2/onboarding-renewals/`
  - If any visual or functional issue is found, fix it and re-validate

- [ ] 18. Error Handling and Exception Classes
  - [ ] 18.1 Create domain-specific exception classes
    - `MergeBlockerError`, `InvalidSalesTransitionError`, `SignWellError`, `SignWellDocumentNotFoundError`, `SignWellWebhookVerificationError`, `ConfirmationCorrelationError`, `RenewalProposalNotFoundError`, `DocumentUploadError`
    - Register in global exception handler with correct HTTP status codes (409, 422, 502, 401, 404, 400)
    - _Requirements: 6.7, 14.3, 18.5_

- [ ] 19. Integration Wiring and Cross-Domain Connections
  - [ ] 19.1 Wire dashboard alerts to new domains
    - Sales pipeline alerts, contract renewal alerts, reschedule request alerts
    - Alert-to-record navigation for all new record types
    - _Requirements: 3.1, 3.2, 31.4_

  - [ ] 19.2 Wire service preferences into job creation flow
    - When creating a job for a customer with matching service_type preference, auto-populate Week_Of
    - Display preference notes as read-only hint on job detail
    - _Requirements: 7.2, 7.3_

  - [ ] 19.3 Ensure single-admin scope compliance
    - Verify no RBAC enforcement in new endpoints — all logged-in users have full admin privileges
    - Do not enforce "staff cannot delete jobs" restriction
    - Do not expose staff user management UI
    - _Requirements: 38.1, 38.2, 38.3, 38.4, 38.5_

  - [ ] 19.4 Verify out-of-scope items are not implemented
    - Confirm no Generate Routes, Marketing, Accounting, or removed Work Requests sub-features are included
    - Confirm Sales and Jobs calendars remain separate
    - _Requirements: 39.1, 39.2, 39.3, 39.4, 39.5, 39.6, 39.7, 39.8_

  - [ ] 19.5 Add CSP frame-src for SignWell embedded signing
    - Add `https://app.signwell.com` to Content-Security-Policy `frame-src` directive
    - _Requirements: 18.3_

- [ ] 20. Comprehensive Property-Based Tests
  - [ ] 20.1 Write PBT file `test_pbt_crm_changes_update_2.py` with all 17 correctness properties
    - **Property 1: Duplicate Score Commutativity** — Validates: Req 32.1
    - **Property 2: Duplicate Score Self-Identity** — Validates: Req 32.2
    - **Property 3: Duplicate Score Zero Floor** — Validates: Req 32.3
    - **Property 4: Duplicate Score Bounded** — Validates: Req 32.4
    - **Property 5: Sales Pipeline Status Transition Validity** — Validates: Req 33.1
    - **Property 6: Sales Pipeline Terminal State Immutability** — Validates: Req 33.2
    - **Property 7: Sales Pipeline Idempotent Advance** — Validates: Req 33.3
    - **Property 8: Y/R/C Keyword Parser Completeness** — Validates: Req 34.1, 34.2, 34.3, 34.4
    - **Property 9: Y/R/C Parser Idempotency** — Validates: Req 34.5
    - **Property 10: Y/R/C Parser Case Insensitivity** — Validates: Req 34.1, 34.2, 34.3
    - **Property 11: Customer Merge Data Conservation** — Validates: Req 35.1, 35.2, 35.3
    - **Property 12: Week Of Date Alignment** — Validates: Req 36.1, 36.2
    - **Property 13: Week Of Round-Trip** — Validates: Req 36.3
    - **Property 14: Invoice Filter Composition** — Validates: Req 37.1
    - **Property 15: Invoice Filter URL Round-Trip** — Validates: Req 37.2
    - **Property 16: Invoice Filter Clear-All Identity** — Validates: Req 37.3
    - **Property 17: Onboarding Week Preference Round-Trip** — Validates: Req 30.6

- [ ] 21. Functional Tests
  - [ ] 21.1 Write functional tests for sales pipeline flow
    - Full pipeline: create from lead → advance through all statuses → convert to job
    - Test with real DB
    - _Requirements: 14.3, 14.4, 14.5, 14.6, 16.2_

  - [ ] 21.2 Write functional tests for customer merge flow
    - Merge with real DB, verify data conservation across jobs/invoices/communications
    - Test Stripe subscription blocker
    - _Requirements: 6.4, 6.5, 6.7, 35.1_

  - [ ] 21.3 Write functional tests for invoice filtering
    - 9-axis filtering with real DB, test AND composition
    - _Requirements: 28.1, 37.1_

  - [ ] 21.4 Write functional tests for Y/R/C confirmation flow
    - Full flow with real DB + mocked SMS: send confirmation → receive Y/R/C → verify transitions
    - _Requirements: 24.2, 24.3, 24.4, 24.5_

  - [ ] 21.5 Write functional tests for contract renewal flow
    - Proposal generation → approve/reject with real DB
    - _Requirements: 31.1, 31.6, 31.7, 31.10_

- [ ] 22. Integration Tests
  - [ ] 22.1 Write integration test for SignWell webhook processing
    - End-to-end: webhook payload → signature verification → PDF storage → status advance
    - _Requirements: 14.6, 17.4, 18.4_

  - [ ] 22.2 Write integration test for Lead → Sales → Job pipeline
    - Full pipeline: lead creation → move to sales → advance through statuses → convert to job
    - _Requirements: 12.1, 12.2, 14.3, 16.2_

  - [ ] 22.3 Write integration test for onboarding week preferences → job generation
    - Onboarding with week selections → Stripe webhook → job generation with correct Week_Of dates
    - _Requirements: 30.3, 30.4, 30.6_

- [ ] 23. Final Checkpoint — All domains complete
  - Ensure all 39 requirements are covered, all tests pass, all property-based tests pass. Ask the user if questions arise.

- [ ] 24. Final Comprehensive E2E Visual Validation
  - [ ] 24.1 Full regression E2E pass across all features
    - Use agent-browser to perform a complete walkthrough of every feature implemented in this update
    - Navigate through: Dashboard → Customers → Leads → Sales → Jobs → Schedule → Invoices → Contract Renewals
    - Verify each page loads without errors, all new UI elements render correctly
    - Test the full Lead → Sales → Job pipeline end-to-end via the browser: create a lead, move to sales, advance through all statuses, force convert to job, schedule the job, complete the job, verify invoice
    - Test cross-domain data sync: create an invoice from a job, verify it appears on the customer detail page
    - Test dashboard alerts for new domains: verify sales pipeline alerts, contract renewal alerts, and reschedule request alerts all navigate correctly
    - Verify session persistence: navigate between 5+ tabs without being logged out prematurely
    - Test responsive layouts at desktop (1440x900) — screenshot every major page
    - Test responsive layouts at tablet (768x1024) — screenshot every major page, check for overflow/broken alignment
    - Test responsive layouts at mobile (375x812) — screenshot every major page, check touch target sizes
    - Check `agent-browser console` and `agent-browser errors` for any JS errors on every page at every viewport
    - Verify no console errors, no uncaught exceptions, no broken network requests across the entire walkthrough
    - Save all screenshots to `e2e-screenshots/crm-changes-update-2/final-regression/`
    - If any visual or functional issue is found, fix it and re-validate until clean

## Notes

- ALL tasks are REQUIRED — no optional tasks. Every test (unit, functional, integration, PBT, E2E) must pass.
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation after each domain
- Property tests validate all 17 correctness properties from the design document
- Req 21 (job actions blocker) is prioritized as Task 4 before all other domain work
- The 8 Alembic migrations must run in order (Task 1) before any model/service work
- SignWell integration (Task 10.3–10.4) requires `SIGNWELL_API_KEY` and `SIGNWELL_WEBHOOK_SECRET` environment variables provisioned
- Single-admin scope (Req 38) means no RBAC enforcement in any new endpoint
- E2E visual validation uses Vercel Agent Browser (agent-browser CLI) after each domain checkpoint
- All E2E screenshots are saved to `e2e-screenshots/crm-changes-update-2/{domain}/` for audit trail
- E2E validation is iterative: if issues are found, fix and re-validate until clean
- The final comprehensive E2E pass (Task 24) covers full regression across all features at multiple viewports
