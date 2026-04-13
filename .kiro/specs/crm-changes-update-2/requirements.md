# Requirements Document

## Introduction

CRM Changes Update 2 is a comprehensive platform update for the Grins Irrigation CRM covering authentication hardening, dashboard cleanup, customer duplicate detection and merge, leads workflow overhaul, a new Sales pipeline tab replacing Work Requests, job management improvements (Week Of semantic rename, missing actions fix), full scheduling confirmation flow (Y/R/C via SMS), invoice filtering on all axes, package onboarding week-based job population, and service contract auto-renewal review queues. All work operates under a single-admin login scope with no staff/admin role split. External integrations include SignWell (e-signature PAYG) and the existing CallRail SMS provider abstraction.

## Glossary

- **Platform**: The Grins Irrigation CRM web application (FastAPI backend + React frontend)
- **Admin**: The single logged-in user operating the CRM (no role distinction in this update)
- **Lead**: An inbound customer request that has not yet been contacted or sorted
- **Sales_Entry**: A pipeline record in the Sales tab representing a customer who needs an estimate before job scheduling
- **Job**: An approved work item that needs to be scheduled and performed
- **Appointment**: A scheduled time slot for a job, with its own status lifecycle (PENDING → SCHEDULED → CONFIRMED → EN_ROUTE → IN_PROGRESS → COMPLETED → CANCELLED → NO_SHOW)
- **Customer**: A person or entity who has or will receive services
- **Property**: A physical location associated with a customer where work is performed
- **Invoice**: A billing record for completed or in-progress work
- **Service_Agreement**: A subscription contract linking a customer to a service package with auto-renewal
- **Service_Preference**: A structured date/time/service-type preference stored per customer
- **Week_Of**: A week-level scheduling target represented by the Monday–Sunday date range of a calendar week
- **SignWell_Client**: The backend httpx wrapper for the SignWell e-signature REST API
- **Embedded_Signer**: The frontend React component that mounts a SignWell iframe for on-site signing
- **SMS_Service**: The existing messaging service using the BaseSMSProvider protocol (currently CallRail)
- **Job_Confirmation_Service**: The new service orchestrating Y/R/C appointment confirmation via SMS
- **Duplicate_Score**: A weighted 0–100 confidence score computed from phone, email, name, address, and ZIP matching signals
- **Merge_Candidate**: A pair of customer records flagged as potential duplicates above the 50-point threshold
- **Renewal_Proposal**: A batch of proposed jobs generated when a service contract auto-renews, pending admin review
- **Customer_Document**: A file (PDF, image, or doc) stored in S3 and associated with a customer record
- **Filter_Panel**: A collapsible UI component providing multi-axis filtering with chip badges and URL persistence

## Requirements

### Requirement 1: Password Hardening via Environment Variable Migration

**User Story:** As an admin, I want the default seeded password replaced with a strong passphrase loaded from an environment variable, so that the platform is not vulnerable to default credential attacks.

#### Acceptance Criteria

1. WHEN the password migration runs, THE Platform SHALL read the new admin password from the `NEW_ADMIN_PASSWORD` environment variable, hash it with bcrypt at cost factor 12, and update the existing admin staff row's `password_hash` column
2. IF the `NEW_ADMIN_PASSWORD` environment variable is not set, THEN THE Platform SHALL abort the migration with a descriptive error message
3. THE Platform SHALL retain the username `admin` unchanged during the password migration
4. THE Platform SHALL ensure the new password meets minimum criteria: 16 characters, mixed case, digits, and at least one common symbol
5. THE Platform SHALL never commit the plaintext password to any repository file, migration script, commit message, or PR description

### Requirement 2: Session Timeout Bug Investigation

**User Story:** As an admin, I want premature logout bugs investigated and fixed, so that I am not randomly logged out while using the platform.

#### Acceptance Criteria

1. WHEN the premature-logout bug is investigated, THE Platform SHALL document the root cause in a bug-hunt note under `bughunt/`
2. IF a bug is found in the refresh token flow or cookie configuration, THEN THE Platform SHALL fix the underlying issue rather than extending timeout values
3. THE Platform SHALL maintain the existing access token expiry of 60 minutes and refresh token expiry of 30 days unless the investigation proves a change is necessary

### Requirement 3: Dashboard Alert-to-Record Navigation

**User Story:** As an admin, I want clicking a dashboard alert to take me directly to the referenced record with visual confirmation, so that I can act on alerts without searching.

#### Acceptance Criteria

1. WHEN a single-record dashboard alert is clicked, THE Platform SHALL navigate directly to the record's detail page
2. WHEN a multi-record dashboard alert is clicked, THE Platform SHALL navigate to the corresponding list tab with a pre-applied filter showing only the matching records
3. WHEN navigating to a filtered list from a multi-record alert, THE Platform SHALL apply a soft amber/yellow background pulse animation that fades over 3 seconds on matched rows
4. THE Platform SHALL encode the highlight state in URL query parameters using `?highlight=<id>` so the highlight survives page refresh and is shareable
5. WHEN navigating to a filtered list from a multi-record alert, THE Platform SHALL auto-scroll to the first matching row

### Requirement 4: Dashboard Section Removal

**User Story:** As an admin, I want the Estimates and New Leads sections removed from the Dashboard, so that the dashboard is not cluttered with information available in dedicated tabs.

#### Acceptance Criteria

1. THE Platform SHALL remove the standalone Estimates card/section from the Dashboard view
2. THE Platform SHALL remove the New Leads section from the Dashboard view
3. WHEN the Dashboard loads, THE Platform SHALL render without the Estimates or New Leads sections
4. WHEN the admin needs to find an estimate after the Dashboard section is removed, THE Platform SHALL make estimates accessible through the Sales tab pipeline list view (Requirement 14), where each estimate is tied to a named Sales_Entry
5. WHEN the admin needs to find leads awaiting contact after the Dashboard section is removed, THE Platform SHALL make them accessible through the Leads tab (Requirements 9–12), which is the single source of truth for not-yet-contacted inbound requests

### Requirement 5: Customer Duplicate Detection and Scoring

**User Story:** As an admin, I want the system to detect potential duplicate customer records using weighted scoring, so that I can review and merge them before they cause operational problems.

#### Acceptance Criteria

1. THE Platform SHALL compute a Duplicate_Score (0–100) for each customer pair using the following weighted signals: normalized phone exact match (E.164) = +60, normalized email exact match (lowercased) = +50, Jaro-Winkler name similarity ≥ 0.92 = +25, same normalized street address = +20, same ZIP plus same last name = +10
2. WHEN a Duplicate_Score is ≥ 80, THE Platform SHALL classify the pair as "High confidence duplicate" and place it at the top of the review queue with pre-selected merge fields
3. WHEN a Duplicate_Score is between 50 and 79 inclusive, THE Platform SHALL classify the pair as "Possible duplicate" and include it in the review queue
4. WHEN a Duplicate_Score is below 50, THE Platform SHALL not flag the pair as a duplicate
5. THE Platform SHALL NEVER auto-merge customer records regardless of confidence score, including scores of 100/100
6. THE Platform SHALL run a nightly background job that sweeps all active customers, computes Duplicate_Scores in batch, and upserts results into the `customer_merge_candidates` table
7. THE Platform SHALL treat all duplicate detection output as recommendations only — the background job SHALL NOT modify any customer record, delete any customer record, or trigger any downstream merge action
8. THE Platform SHALL never hard-delete a customer record as part of the duplicate detection or merge flow; the only deletion semantics supported are soft-delete via `merged_into_customer_id` (see Requirement 6)


### Requirement 6: Customer Duplicate Review and Merge Flow

**User Story:** As an admin, I want a side-by-side comparison and merge interface for duplicate customers, so that I can consolidate records while preserving all related data.

#### Acceptance Criteria

1. WHEN the admin clicks "Review Duplicates" on the Customers tab, THE Platform SHALL display a review queue listing suggested duplicate pairs sorted by Duplicate_Score descending
2. WHEN the admin clicks a duplicate pair, THE Platform SHALL open a side-by-side comparison modal showing all fields from both records with radio buttons for each conflicting field (primary record's value selected by default)
3. THE Platform SHALL require explicit manual admin confirmation for every merge operation, with no exception for high-confidence pairs, and SHALL present a preview of the merged record before the admin clicks "Confirm Merge"
4. WHEN the admin confirms a merge, THE Platform SHALL reassign all related jobs, notes, invoices, communications, agreements, and properties from the duplicate to the surviving record
5. WHEN the admin confirms a merge, THE Platform SHALL soft-delete the duplicate record by setting `merged_into_customer_id` to the surviving record's ID (no hard-delete)
6. WHEN the admin confirms a merge, THE Platform SHALL write an audit log entry recording the admin identity, timestamp, and which field values survived
7. IF both customer records have active Stripe subscriptions, THEN THE Platform SHALL block the merge with the error message "Both customers have active Stripe subscriptions ({sub_a_id}, {sub_b_id}). Cancel one subscription before merging." and SHALL never silently cancel or combine Stripe subscriptions
8. IF both customer records have active service agreements, THEN THE Platform SHALL reassign all agreements from the duplicate to the surviving record so both end up linked to the surviving customer
9. IF both customer records have pending appointments or scheduled jobs, THEN THE Platform SHALL reassign both sets to the surviving record and surface the combined schedule to the admin for conflict review
10. IF both customer records have different `stripe_customer_id` values, THEN THE Platform SHALL preserve the surviving record's `stripe_customer_id` and record the duplicate's `stripe_customer_id` in the audit log entry for reference
11. IF one record has an empty value for a field (phone, email, name) and the other has a non-empty value, THEN THE Platform SHALL default the surviving record to keep the non-empty value, allowing the admin to override via the side-by-side radio buttons
12. IF any merge rule is ambiguous during execution, THEN THE Platform SHALL prompt the admin with a modal to resolve the ambiguity rather than silently picking a side
13. WHEN a customer is created or a lead is converted, THE Platform SHALL synchronously check for Tier 1 matches (exact phone or email) and display an inline "Possible match found" warning with a "Use existing customer" button

### Requirement 7: Customer Service Preferences — Multi Date and Time

**User Story:** As an admin, I want to configure multiple date, time, and service-type preferences per customer, so that scheduling hints auto-populate when creating jobs.

#### Acceptance Criteria

1. THE Platform SHALL store service preferences as a JSON array on the customer record, where each entry contains: id (UUID), service_type, preferred_week, preferred_date (optional, overrides week), preferred_time_window, and notes
2. WHEN a job is created for a customer and a matching service preference exists (same service_type), THE Platform SHALL auto-populate the job's Week_Of field from the preference's preferred_week value
3. THE Platform SHALL display the preference's notes as a read-only hint on the job detail view
4. THE Platform SHALL never auto-create jobs from service preferences; job creation requires explicit user action
5. WHEN the admin views a customer detail page, THE Platform SHALL display a "Service Preferences" section listing all existing preferences with Add, Edit, and Delete actions
6. WHEN the admin adds a service preference, THE Platform SHALL present a modal with fields: service type dropdown (Spring Startup, Mid-Season Inspection, Fall Winterization, Monthly Visit, Custom), preferred week (week picker), preferred specific date (date picker), time window dropdown (Morning, Afternoon, Evening, Any), and notes (free text)

### Requirement 8: Property Type Tagging

**User Story:** As an admin, I want properties tagged with type (residential/commercial), HOA status, and subscription status, so that I can filter and identify properties at a glance.

#### Acceptance Criteria

1. THE Platform SHALL maintain the existing `property_type` enum field (residential, commercial) on the Property model as a required attribute
2. THE Platform SHALL add a new `is_hoa` boolean field on the Property model, defaulting to false
3. THE Platform SHALL derive `is_subscription_property` at query time by checking for an active service_agreement linked to the property, without storing it as a column
4. WHEN displaying property information on the property list, customer detail, or job detail views, THE Platform SHALL show visual tags for Residential or Commercial, HOA (if true), and Subscription (if true) — the Subscription tag MAY be labeled as either "Subscription" or "Subbed to us" per the source doc terminology
5. THE Platform SHALL support filtering by any combination of property_type, is_hoa, and is_subscription_property on the Customers, Jobs, and Sales list views

### Requirement 9: Lead Deletion and Auto-Removal on Move

**User Story:** As an admin, I want to delete leads manually and have them automatically disappear when moved to Jobs or Sales, so that the Leads tab only shows actionable inbound requests.

#### Acceptance Criteria

1. WHEN the admin clicks the delete icon on a lead row and confirms the deletion modal, THE Platform SHALL hard-delete the lead record from the database
2. WHEN a lead is moved to the Jobs tab or Sales tab via action buttons, THE Platform SHALL set the lead's `moved_to` column to the destination (jobs or sales) with a timestamp, causing the lead to disappear from the Leads list view
3. THE Platform SHALL filter the Leads list query to exclude any lead where `moved_to IS NOT NULL`
4. WHEN the admin clicks delete, THE Platform SHALL display a confirmation modal stating the deletion is permanent and cannot be undone

### Requirement 10: Leads Column Reorder and New Columns

**User Story:** As an admin, I want the Leads table reorganized with Job Requested and City columns added and Intake removed, so that I can scan and prioritize leads without clicking into each one.

#### Acceptance Criteria

1. THE Platform SHALL remove all color highlighting from the lead source column
2. THE Platform SHALL move the lead source column to the far right of the Leads table
3. THE Platform SHALL add a "Job Requested" column in the position previously occupied by lead source
4. THE Platform SHALL add a "City" column immediately after the Job Address column, derived from the existing address data
5. THE Platform SHALL remove the "Intake" column from the Leads table

### Requirement 11: Lead Status Tags and Last Contacted Date

**User Story:** As an admin, I want lead statuses limited to New and Contacted (Awaiting Response) with a Last Contacted Date column, so that lead tracking is simple and actionable.

#### Acceptance Criteria

1. THE Platform SHALL support exactly two lead status values: "New" (default on creation) and "Contacted (Awaiting Response)"
2. WHEN the admin clicks the "Contacted" action button on a lead row, THE Platform SHALL update the lead's status to "Contacted (Awaiting Response)" and set `last_contacted_at` to the current timestamp
3. WHEN an outbound or inbound SMS/email tied to a lead is processed by the SMS_Service, THE Platform SHALL auto-update the lead's `last_contacted_at` timestamp
4. THE Platform SHALL display a "Last Contacted Date" column in the Leads table showing the `last_contacted_at` value

### Requirement 12: Lead Move-Out Action Buttons

**User Story:** As an admin, I want "Move to Jobs" and "Move to Sales" buttons on each lead row, so that I can route leads to the correct workflow in one action.

#### Acceptance Criteria

1. WHEN the admin clicks "Move to Jobs" on a lead, THE Platform SHALL auto-generate a customer record if one does not already exist for the lead, create a job with status TO_BE_SCHEDULED, and remove the lead from the Leads list
2. WHEN the admin clicks "Move to Sales" on a lead, THE Platform SHALL auto-generate a customer record if one does not already exist for the lead, create a Sales_Entry with status "Schedule Estimate", and remove the lead from the Leads list
3. THE Platform SHALL display both "Move to Jobs" and "Move to Sales" action buttons on each lead row

### Requirement 13: Work Requests Tab Removal and Sales Tab Replacement

**User Story:** As an admin, I want the Work Requests tab deleted and replaced by a new Sales tab, so that the estimate-to-job pipeline has a dedicated, purpose-built interface.

#### Acceptance Criteria

1. THE Platform SHALL remove the Work Requests tab entirely from the navigation
2. THE Platform SHALL add a new Sales tab to the navigation
3. WHEN existing work requests data exists, THE Platform SHALL migrate it to the Sales tab as pipeline entries
4. THE Platform SHALL remove the following sub-features from the old Work Requests page without replacement: Estimate Builder, Media Library, Diagrams, Follow-Up Queue, and Estimates sub-tab

### Requirement 14: Sales Pipeline List View with Auto-Advancing Statuses

**User Story:** As an admin, I want a pipeline list view in the Sales tab with statuses that auto-advance when I click action buttons, so that I can move deals through the funnel without manual dropdown changes.

#### Acceptance Criteria

1. THE Platform SHALL preserve the existing 4 summary boxes at the top of the Sales tab unchanged from the current Work Requests implementation — the boxes migrate visually to the Sales tab without modification to their content, layout, or data sources
2. THE Platform SHALL display a Sales pipeline list view (below the summary boxes) with columns: Customer Name, Customer Phone Number (interpreting the source doc "Customer Number" as phone, following small-business CRM convention), Customer Address, Job Type, Status, and Last Contact Date
3. THE Platform SHALL support the following ordered pipeline statuses: Schedule Estimate, Estimate Scheduled, Send Estimate, Pending Approval, Send Contract, Closed-Won, and Closed-Lost
4. WHEN the admin clicks the "Schedule Estimate" action button on a Sales_Entry with status "Schedule Estimate", THE Platform SHALL advance the status to "Estimate Scheduled"
5. WHEN the admin clicks the "Send Estimate" action button, THE Platform SHALL advance the status to "Pending Approval" and trigger the email or embedded signing flow
6. WHEN the SignWell webhook fires confirming customer approval, THE Platform SHALL advance the Sales_Entry status from "Pending Approval" to "Send Contract"
7. WHEN the admin clicks "Mark Lost" on any Sales_Entry, THE Platform SHALL set the status to "Closed-Lost" as a terminal state
8. THE Platform SHALL allow the admin to manually override the status via a dropdown for exceptional cases
9. WHEN a customer in Pending Approval status declines, THE Platform SHALL transition the Sales_Entry to Closed-Lost with an optional reason field
10. THE Platform SHALL offer an expanded per-lead detail view when the admin clicks a Sales pipeline row, showing the Documents section (Requirement 17), the email signing action, and the embedded on-site signing action (Requirement 18)

### Requirement 15: Sales Scheduling Calendar

**User Story:** As an admin, I want a dedicated scheduling calendar inside the Sales tab for estimate appointments, so that estimate scheduling does not pollute the main job calendar.

#### Acceptance Criteria

1. THE Platform SHALL provide a separate calendar view within the Sales tab for scheduling estimate appointments
2. THE Platform SHALL support manual entry of estimate appointments on the Sales calendar
3. THE Platform SHALL keep the Sales calendar independent from the main Jobs schedule calendar

### Requirement 16: Convert to Job with Signature Gating and Force Override

**User Story:** As an admin, I want the Convert to Job button gated on customer signature confirmation with a force override option, so that jobs are only created after proper authorization while retaining flexibility for edge cases.

#### Acceptance Criteria

1. WHILE the SignWell webhook has not fired confirming customer signature, THE Platform SHALL disable the "Convert to Job" button with the tooltip "Waiting for customer signature"
2. WHEN the admin clicks "Convert to Job" after signature confirmation, THE Platform SHALL create a new job with status TO_BE_SCHEDULED pre-filled with data from the Sales_Entry, and set the Sales_Entry status to Closed-Won
3. WHEN the admin clicks "Force Convert to Job", THE Platform SHALL display a confirmation modal warning that no signature is on file and asking for confirmation
4. WHEN the admin confirms the force override, THE Platform SHALL create the job, write an audit log entry recording the override with admin identity and timestamp, and set `override_flag = true` on the Sales_Entry

### Requirement 17: Sales Per-Lead Documents Section

**User Story:** As an admin, I want a documents section in each Sales pipeline entry's expanded view, so that I can upload, download, preview, and manage all customer-facing documents in one place.

#### Acceptance Criteria

1. WHEN the admin clicks a Sales pipeline row, THE Platform SHALL display an expanded detail view with a documents section
2. THE Platform SHALL support upload, download, delete, and preview of documents (PDFs, images, and common doc types) up to 25 MB per file
3. THE Platform SHALL store documents using the existing S3/PhotoService infrastructure with a new Customer_Document model containing fields: id, customer_id, file_key, file_name, document_type (estimate, contract, photo, diagram, reference, signed_contract), mime_type, size_bytes, uploaded_at, uploaded_by
4. WHEN a signed contract is returned from SignWell, THE Platform SHALL store it as a Customer_Document with document_type "signed_contract"

### Requirement 18: E-Signature Dual Path — Email and Embedded On-Site

**User Story:** As an admin, I want to send estimates for signature via email or have customers sign on-site via an embedded iframe, so that I can handle both remote and in-person signing scenarios.

#### Acceptance Criteria

1. WHEN the admin clicks "Send Estimate for Signature (Email)", THE Platform SHALL call the SignWell_Client to create a document with the uploaded PDF and customer email, advance the Sales_Entry status to Pending Approval, and log the action in communications history
2. IF the customer record has no email on file, THEN THE Platform SHALL disable the email signing button with the tooltip "Customer email required — add one on the customer record or use the on-site embedded signing path instead"
3. WHEN the admin clicks "Sign on-site", THE Platform SHALL call the SignWell_Client embedded signing API, return a signing URL, and mount the Embedded_Signer iframe overlay for the customer to sign
4. WHEN the Embedded_Signer detects signature completion via postMessage events, THE Platform SHALL fetch the signed PDF via webhook, store it as a Customer_Document with document_type "signed_contract", and advance the Sales_Entry status
5. THE Platform SHALL implement the SignWell_Client as a thin httpx wrapper in `src/grins_platform/services/signwell/` with methods: create_document_for_email, create_document_for_embedded, get_embedded_url, fetch_signed_pdf, and verify_webhook_signature
6. THE Platform SHALL store the SignWell API key as the `SIGNWELL_API_KEY` environment variable

### Requirement 19: Job Detail View with Address and Property Tags

**User Story:** As an admin, I want the job detail view to show the full property address and property tags, so that I can see location and property context without navigating away.

#### Acceptance Criteria

1. WHEN the admin views a job detail page, THE Platform SHALL display the full street address (street, city, state, ZIP) of the property where the job will be performed
2. WHEN the admin views a job detail page, THE Platform SHALL display property tags: Residential or Commercial, HOA (if is_hoa is true), and Subscription (if is_subscription_property is true)
3. THE Platform SHALL display the same property tags as compact badges on the Jobs list view next to each row
4. THE Platform SHALL support filtering the Jobs list by any combination of Residential/Commercial, HOA yes/no, and Subscription yes/no

### Requirement 20: Replace Due By with Week Of Semantic Rename

**User Story:** As an admin, I want the "Due By" column renamed to "Week Of" with a week picker, so that I can assign jobs to target weeks rather than specific due dates.

#### Acceptance Criteria

1. THE Platform SHALL rename the UI column label from "Due By" to "Week Of" in the Jobs list view
2. THE Platform SHALL replace the date picker with a week picker that writes target_start_date as Monday and target_end_date as Sunday of the selected week
3. THE Platform SHALL display the Week_Of value as "Week of M/D/YYYY" where the date shown is the Monday of the selected week
4. WHEN a job is created for a customer with a matching service preference, THE Platform SHALL auto-populate the Week_Of from the preference's preferred_week value
5. WHEN the week before the Week_Of target arrives, THE Platform SHALL allow the admin to promote the job from a week-level assignment to a specific date and time, surfacing any customer date/time constraints from Service_Preferences as hints

### Requirement 21: Fix Missing Job-Level Actions (Invoicing and Completion)

**User Story:** As an admin, I want the ability to invoice customers and mark jobs as complete from the job detail view, so that the invoicing and job completion workflows are unblocked.

#### Acceptance Criteria

1. WHEN the admin views a job detail page, THE Platform SHALL provide a working "Create Invoice" action that generates an invoice for the job
2. WHEN the admin views a job detail page, THE Platform SHALL provide a working "Mark Complete" action that transitions the job status to COMPLETED
3. THE Platform SHALL investigate and document both bugs ("cannot invoice" and "cannot mark complete") in a bug-hunt document before fixing

### Requirement 22: Schedule — Job Picker Popup and Bulk Assignment

**User Story:** As an admin, I want a job picker popup that mirrors the Jobs tab and supports bulk assignment, so that I can efficiently schedule multiple jobs at once.

#### Acceptance Criteria

1. WHEN the admin adds jobs to the schedule manually, THE Platform SHALL open a popup that displays the same columns, filter controls, and search as the Jobs tab list
2. WHEN the admin selects multiple jobs from the picker, THE Platform SHALL allow assigning all selected jobs to a specific date and staff member in one action with a global time allocation per job
3. WHEN bulk assignment is complete, THE Platform SHALL support per-job time adjustments after the initial bulk assignment

### Requirement 23: Schedule — Unconfirmed vs Confirmed Visual Distinction

**User Story:** As an admin, I want a clear visual distinction between unconfirmed and confirmed scheduled jobs, so that I can see at a glance which appointments still need customer confirmation.

#### Acceptance Criteria

1. WHILE an Appointment has status SCHEDULED (unconfirmed), THE Platform SHALL display it with a dashed border and muted background
2. WHILE an Appointment has status CONFIRMED, THE Platform SHALL display it with a solid border and full color background

### Requirement 24: Y/R/C Scheduling Confirmation Flow via SMS

**User Story:** As an admin, I want the system to send appointment confirmation SMS messages and automatically process Y/R/C replies, so that customers can confirm, reschedule, or cancel via text.

#### Acceptance Criteria

1. WHEN an Appointment is created for a job, THE Platform SHALL send an outbound SMS via SMS_Service with message_type APPOINTMENT_CONFIRMATION containing the customer name, service type, scheduled date, time window, and Y/R/C reply instructions
2. WHEN an inbound SMS reply correlates to an APPOINTMENT_CONFIRMATION message via thread_id and the reply body matches a CONFIRM keyword (y, yes, confirm, confirmed, ok, okay), THE Job_Confirmation_Service SHALL transition the Appointment status from SCHEDULED to CONFIRMED and send a confirmation auto-reply
3. WHEN an inbound SMS reply matches a RESCHEDULE keyword (r, reschedule, different time, change time), THE Job_Confirmation_Service SHALL create a reschedule_request record, send a follow-up SMS asking for 2–5 alternative date/time options, and surface the request in the admin Reschedule Requests queue
4. WHEN an inbound SMS reply matches a CANCEL keyword (c, cancel, cancelled), THE Job_Confirmation_Service SHALL transition the Appointment status to CANCELLED, send a cancellation auto-reply, and notify the admin
5. IF an inbound reply does not match any known keyword, THEN THE Job_Confirmation_Service SHALL log the reply with status "needs_review" for manual processing
6. THE Platform SHALL persist all confirmation replies in the `job_confirmation_responses` table with fields: job_id, appointment_id, sent_message_id, customer_id, from_phone, reply_keyword, raw_reply_body, provider_sid, status, received_at, processed_at
7. THE Platform SHALL use only the abstract InboundSMS dataclass from the BaseSMSProvider Protocol for Y/R/C handling, with no CallRail-specific code in the confirmation handler
8. THE Platform SHALL correlate inbound replies to outbound messages via provider_thread_id, not phone number

### Requirement 25: Reschedule Requests Admin Queue

**User Story:** As an admin, I want a queue showing all customer reschedule requests with their proposed alternatives, so that I can efficiently handle rescheduling.

#### Acceptance Criteria

1. THE Platform SHALL provide a "Reschedule Requests" view accessible from the Schedule tab showing all open reschedule_requests grouped by status
2. WHEN the admin views a reschedule request, THE Platform SHALL display: customer name, original appointment details, requested alternatives (parsed or raw text), received timestamp, and action buttons
3. WHEN the admin clicks "Reschedule to Alternative", THE Platform SHALL open the appointment editor pre-filled with the selected alternative date/time
4. WHEN the admin clicks "Mark Resolved", THE Platform SHALL close the reschedule request and update its status to resolved

### Requirement 26: Schedule — Auto-Complete, Payment, Invoice, Notes, Photos, and Review Push

**User Story:** As an admin, I want on-site capabilities for payment collection, invoice creation, customer notes/photos, and Google review requests from the job detail view, so that field operations are handled in one place.

#### Acceptance Criteria

1. WHEN the admin records a payment on-site via the job detail view, THE Platform SHALL update the appointment with payment details (amount, method, timestamp), auto-update the customer record, and mark the linked invoice as paid
2. WHEN the admin creates an invoice on-site, THE Platform SHALL generate a template-based invoice pre-filled with customer and job data, send it to the customer email with a payment link, and update the Invoice tab
3. WHEN the admin adds notes or photos from the job detail view, THE Platform SHALL sync both to the customer record and link them to the job_id for contextual retrieval
4. WHEN the admin triggers a Google review push, THE Platform SHALL send an SMS to the customer via SMS_Service with message_type GOOGLE_REVIEW_REQUEST containing a tracked review deep link

### Requirement 27: Job Status Buttons with Payment Warning Override

**User Story:** As an admin, I want On My Way, Job Started, and Job Complete status buttons with a payment warning before completion, so that I can track job progress and ensure billing is not missed.

#### Acceptance Criteria

1. WHEN the admin clicks "On My Way", THE Platform SHALL send an SMS notification to the customer via SMS_Service and log the timestamp
2. WHEN the admin clicks "Job Started", THE Platform SHALL log the timestamp
3. WHEN the admin clicks "Job Complete" and payment has been collected or an invoice has been sent, THE Platform SHALL transition the Job status to COMPLETED and log the timestamp
4. IF the admin clicks "Job Complete" and no payment has been collected and no invoice has been sent, THEN THE Platform SHALL display a warning modal stating "No Payment or Invoice on File" with Cancel and "Complete Anyway" options
5. WHEN the admin clicks "Complete Anyway", THE Platform SHALL complete the job and write an audit log entry recording the override
6. THE Platform SHALL automatically track time elapsed between On My Way, Job Started, and Job Complete as structured metadata per job type and staff member for future scheduling optimization
7. WHEN a Job status transitions to COMPLETED, THE Platform SHALL archive it out of the active schedule view while keeping it discoverable in the Jobs tab under a "Completed" status filter

### Requirement 28: Invoice Full Filtering on All Axes

**User Story:** As an admin, I want to filter invoices on every attribute including date range, status, customer, job, amount, payment type, days until due, days past due, and invoice number, so that I can find any invoice instantly.

#### Acceptance Criteria

1. THE Platform SHALL support filtering invoices on all 9 axes: date range (created/due/paid), status (Complete/Pending/Past Due), customer (searchable dropdown), job (searchable dropdown), amount range (min/max), payment type (multi-select: Credit Card/Cash/Check/ACH/Other), days until due (numeric range), days past due (numeric range), and invoice number (exact match)
2. THE Platform SHALL display active filters as removable chip badges above the invoice list
3. THE Platform SHALL persist filter state in URL query parameters so filtered views are bookmarkable and shareable
4. THE Platform SHALL provide a "Clear all filters" button and a "Save this filter" option for commonly used filter combinations
5. THE Platform SHALL use a collapsible Filter_Panel pattern (sidebar or drawer) to present all 9 filters simultaneously without overwhelming the toolbar

### Requirement 29: Invoice List View with Status Colors and Mass Notifications

**User Story:** As an admin, I want the invoice list to show status-colored badges and support bulk notification actions, so that I can visually scan invoice health and batch-notify customers.

#### Acceptance Criteria

1. THE Platform SHALL display invoice list columns: Invoice Number, Customer Name, Job (link), Cost, Status, Days Until Due, Days Past Due, and Payment Type
2. THE Platform SHALL apply visual status colors: green for Complete, yellow for Pending, and red for Past Due
3. WHEN the admin triggers a mass notification, THE Platform SHALL support bulk SMS/email to: all customers with past-due invoices, all customers with invoices due within a configurable window, and all customers meeting lien notice eligibility criteria (60+ days past due AND over $500, configurable)
4. THE Platform SHALL use configurable templates for each mass notification type
5. WHEN invoice state changes (created, paid, past-due, void), THE Platform SHALL reflect the change in the Customer detail view in real-time

### Requirement 30: Package Onboarding Week-Based Job Auto-Population

**User Story:** As a customer going through onboarding, I want to pick specific weeks for each service in my package, so that my jobs are pre-scheduled to my preferred timing.

#### Acceptance Criteria

1. THE Platform SHALL add a `service_week_preferences` JSON field to the ServiceAgreement model storing per-service week selections as ISO Monday dates
2. WHEN the onboarding wizard reaches the service week selection step, THE Platform SHALL display a week picker for each service in the customer's package, restricted to the valid month range for that service type
3. WHEN the onboarding completes and the Stripe checkout webhook fires, THE Platform SHALL pass the service_week_preferences to the job generator
4. WHEN the job generator creates jobs for an agreement with service_week_preferences, THE Platform SHALL set target_start_date to the Monday and target_end_date to the Sunday of the customer-selected week for each matching service
5. IF the agreement has no service_week_preferences (null), THEN THE Platform SHALL fall back to the existing calendar-month defaults for job date ranges
6. FOR ALL valid service_week_preferences, generating jobs then reading their Week_Of display values SHALL produce dates matching the originally selected weeks (round-trip property)

### Requirement 31: Service Contract Auto-Renewal Review Queue

**User Story:** As an admin, I want auto-renewed contracts to generate proposed jobs in a review queue rather than creating jobs directly, so that I can verify and adjust the batch before it hits the live schedule.

#### Acceptance Criteria

1. WHEN a ServiceAgreement with auto_renew=true reaches its renewal date and the Stripe invoice.paid webhook fires, THE Platform SHALL generate a Renewal_Proposal containing proposed jobs for the new contract year instead of creating jobs directly
2. THE Platform SHALL roll forward prior-year service_week_preferences by one year for each proposed job's target dates
3. IF the agreement has no prior-year service_week_preferences, THEN THE Platform SHALL use the hardcoded calendar-month defaults for proposed job dates
4. WHEN a Renewal_Proposal is created, THE Platform SHALL fire a dashboard alert: "1 contract renewal ready for review: {customer_name}"
5. WHEN the admin views the Contract Renewal Reviews page, THE Platform SHALL display pending proposals with columns: Customer, Agreement name, Proposed job count, Created date, and Action buttons
6. WHEN the admin clicks "Approve All" on a proposal, THE Platform SHALL create real Job records using the proposed dates and mark the proposal as approved
7. WHEN the admin rejects individual proposed jobs, THE Platform SHALL mark those as rejected and set the proposal status to partially_approved if some were approved
8. THE Platform SHALL allow the admin to modify the Week_Of on individual proposed jobs before approving them
9. THE Platform SHALL provide an `admin_notes` free-text field on each proposed job allowing the admin to annotate the proposal before approving, rejecting, or modifying it
10. WHEN the admin clicks "Reject All" on a proposal, THE Platform SHALL mark every proposed job in the batch as rejected, set the proposal status to rejected, and create no Job records — useful when the renewal webhook fires in error or the customer is not actually renewing
11. THE Platform SHALL support three per-job actions in the proposal detail view: Approve, Reject, and Modify, displayed as toggles or buttons on each proposed job row

### Requirement 32: Duplicate Score Computation Correctness

**User Story:** As a developer, I want the duplicate scoring algorithm to be verifiable through property-based testing, so that scoring is deterministic and consistent.

#### Acceptance Criteria

1. FOR ALL pairs of customer records, computing the Duplicate_Score SHALL be commutative: score(A, B) equals score(B, A)
2. FOR ALL customer records, computing the Duplicate_Score of a record against itself SHALL produce the maximum possible score
3. FOR ALL customer records with no matching signals, computing the Duplicate_Score SHALL produce zero
4. FOR ALL customer records, the Duplicate_Score SHALL be bounded between 0 and 100 inclusive

### Requirement 33: Sales Pipeline Status Transition Correctness

**User Story:** As a developer, I want the sales pipeline status transitions to be verifiable, so that statuses only advance through valid paths.

#### Acceptance Criteria

1. FOR ALL Sales_Entry records, the status SHALL only transition through the defined pipeline order: Schedule Estimate → Estimate Scheduled → Send Estimate → Pending Approval → Send Contract → Closed-Won, with Closed-Lost reachable from any active status
2. FOR ALL Sales_Entry records, once a terminal status (Closed-Won or Closed-Lost) is reached, THE Platform SHALL not allow further status transitions
3. FOR ALL valid status transitions triggered by action buttons, the post-status SHALL be exactly one step forward in the pipeline (idempotence: clicking the same action button twice on the same status SHALL not skip a step)

### Requirement 34: Y/R/C Keyword Parser Correctness

**User Story:** As a developer, I want the Y/R/C keyword parser to be verifiable through property-based testing, so that customer replies are correctly classified.

#### Acceptance Criteria

1. FOR ALL inputs matching CONFIRM keywords (y, yes, confirm, confirmed, ok, okay — case-insensitive, whitespace-trimmed), the parser SHALL return CONFIRM
2. FOR ALL inputs matching RESCHEDULE keywords (r, reschedule, different time, change time — case-insensitive, whitespace-trimmed), the parser SHALL return RESCHEDULE
3. FOR ALL inputs matching CANCEL keywords (c, cancel, cancelled — case-insensitive, whitespace-trimmed), the parser SHALL return CANCEL
4. FOR ALL inputs not matching any known keyword, the parser SHALL return None
5. FOR ALL inputs, the parser SHALL be idempotent: parsing the same input twice SHALL produce the same result

### Requirement 35: Customer Merge Data Integrity

**User Story:** As a developer, I want customer merges to preserve all related data without loss, so that no jobs, invoices, or communications are orphaned.

#### Acceptance Criteria

1. FOR ALL customer merges, the total count of jobs, invoices, communications, agreements, and properties across both records before the merge SHALL equal the count associated with the surviving record after the merge
2. FOR ALL customer merges, the duplicate record's `merged_into_customer_id` SHALL reference the surviving record's ID
3. FOR ALL customer merges, an audit log entry SHALL exist recording the merge details

### Requirement 36: Week Of Date Alignment Correctness

**User Story:** As a developer, I want Week_Of values to always represent valid Monday–Sunday ranges, so that scheduling logic is consistent.

#### Acceptance Criteria

1. FOR ALL jobs with a Week_Of value set, target_start_date SHALL be a Monday and target_end_date SHALL be the following Sunday (6 days later)
2. FOR ALL jobs, target_start_date SHALL be less than or equal to target_end_date
3. FOR ALL week picker selections, writing then reading the Week_Of value SHALL produce the same Monday date (round-trip property)

### Requirement 37: Invoice Filter Composition Correctness

**User Story:** As a developer, I want invoice filters to compose correctly when multiple axes are applied simultaneously, so that results are the intersection of all active filters.

#### Acceptance Criteria

1. FOR ALL combinations of active filters, the result set SHALL be the intersection (AND) of each individual filter's result set
2. FOR ALL filter states persisted in URL query parameters, loading the URL SHALL reproduce the same filter configuration and result set
3. FOR ALL filter states, clearing all filters SHALL return the complete unfiltered invoice list

### Requirement 38: Single Admin Scope (Staff/Admin Role Split Deferred)

**User Story:** As a developer, I want the single-admin scope explicitly documented as a formal requirement, so that I do not mistakenly implement role-based restrictions described in the source doc that are deferred to a future update.

#### Acceptance Criteria

1. THE Platform SHALL treat all logged-in users as having full admin privileges for this update, regardless of the `admin`, `sales`, or `tech` role values present in the database's `staff` table
2. THE Platform SHALL NOT enforce the "staff cannot delete jobs" restriction from the source doc (`CRM_Changes_Update_2.md` line 73) — job deletion is available to any logged-in user in this update
3. THE Platform SHALL NOT expose a staff user management UI (create/edit/delete staff accounts) as part of this update
4. THE Platform SHALL defer role-based access control (RBAC) UI, enforcement, and any staff-vs-admin capability distinctions to a future update
5. WHEN the source doc uses "staff" or "admin" to describe specific capabilities (e.g., in the Schedule section), THE Platform SHALL treat those as equivalent to "any logged-in user" for this update

### Requirement 39: Explicit Out-of-Scope Items

**User Story:** As a developer, I want an explicit list of items that are NOT in scope for this update, so that I do not accidentally implement deferred or cancelled work.

#### Acceptance Criteria

1. THE Platform SHALL NOT implement Generate Routes (AI routing) changes as part of this update — this feature is being built by an upstream team and is waiting for test coverage independent of CRM Changes Update 2
2. THE Platform SHALL NOT implement new Marketing features as part of this update — Marketing is flagged lower-priority and explicitly out of scope
3. THE Platform SHALL NOT implement new Accounting features as part of this update — Accounting is flagged lower-priority and explicitly out of scope
4. THE Platform SHALL NOT restore the removed Work Requests sub-features (Estimate Builder, Media Library, Diagrams, Follow-Up Queue, Estimates sub-tab) as part of this update — they are removed without replacement
5. THE Platform SHALL NOT merge the Sales scheduling calendar with the main Jobs calendar as part of this update — they remain separate calendars
6. THE Platform SHALL NOT implement the staff/admin role split UI or RBAC enforcement as part of this update (see Requirement 38)
7. THE Platform SHALL NOT integrate DocuSign, HelloSign, or Dropbox Sign for e-signature — SignWell PAYG replaces them (see Requirement 18)
8. THE Platform SHALL NOT consult or incorporate the "PLEASE LOOK AT SCHEDULING TASK IN ASANA" reference from the source doc — per Kirill's direction, the Schedule requirements (Requirements 22–27) are locked based only on the content of `CRM_Changes_Update_2.md`; any additional scheduling requirements from Asana will be handled as a separate follow-up outside this update
