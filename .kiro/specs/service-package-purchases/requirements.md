# Requirements Document — Service Package Purchases

## Introduction

This feature builds the end-to-end pipeline for service package purchases in the Grins Irrigation Platform. Starting from the pre-checkout consent modal on the landing page, through Stripe Checkout Session creation, webhook processing, customer/agreement/job creation, and post-purchase property onboarding. The admin dashboard gains a Service Agreements tab with business metrics, operational queues, and agreement lifecycle management. The existing Jobs and Dashboard tabs are extended with subscription-aware data. TCPA SMS consent and MN auto-renewal compliance are enforced throughout the purchase flow.

Additionally, this feature enhances the Leads and Work Requests pipeline with expanded lead source tracking, intake tagging (SCHEDULE vs FOLLOW_UP), a follow-up queue for leads requiring human review, work request auto-promotion for all client types, SMS/email submission confirmations, dashboard widgets for lead metrics, and consent field tracking on leads. These enhancements close the gap between inbound lead capture and the service agreement purchase funnel.

The platform currently has zero Stripe integration, no service agreement tracking, no seasonal job auto-generation, and no compliance audit trail. The existing Leads tab has basic status tracking but lacks source attribution, intake routing, and confirmation messaging. This feature closes those gaps.

## Glossary

- **Platform**: The Grins Irrigation Platform backend (FastAPI + PostgreSQL) and admin frontend (React 19)
- **Admin**: Viktor, the sole administrator who manages all operations via the admin dashboard
- **Webhook_Handler**: The backend component that receives and processes Stripe webhook events
- **Agreement_Service**: The backend service responsible for ServiceAgreement lifecycle management, status transitions, and business logic
- **Job_Generator**: The backend component that creates seasonal Job records based on a ServiceAgreementTier's included_services definition
- **Agreement_Repository**: The data access layer for ServiceAgreement and related records
- **Tier_Repository**: The data access layer for ServiceAgreementTier template records
- **Metrics_Service**: The backend component that computes business KPIs (MRR, renewal rate, churn rate) from agreement data
- **Agreements_Dashboard**: The frontend Service Agreements tab in the admin dashboard
- **Agreement_Detail_View**: The frontend page showing a single agreement's full information, linked jobs, payment history, and status actions
- **ServiceAgreementTier**: A template record defining a package (name, price, included services, perks, Stripe IDs). 6 tiers exist: 3 levels (Essential, Professional, Premium) × 2 types (Residential, Commercial)
- **ServiceAgreement**: An instance record representing a specific customer's active subscription, linked to a tier, customer, and property
- **AgreementStatusLog**: An audit trail record capturing every status change on a ServiceAgreement with timestamp, actor, and reason
- **Stripe_Webhook_Event**: A deduplication record storing processed Stripe event IDs to ensure idempotent webhook handling
- **Seasonal_Job**: A Job record auto-generated from a ServiceAgreement with a target date range, entering at APPROVED status
- **Agreement_Status**: One of PENDING, ACTIVE, PAST_DUE, PAUSED, PENDING_RENEWAL, CANCELLED, EXPIRED
- **Payment_Status**: One of CURRENT, PAST_DUE, FAILED
- **MRR**: Monthly Recurring Revenue, calculated as the sum of annual_price / 12 for all ACTIVE agreements
- **Renewal_Pipeline**: The set of agreements in PENDING_RENEWAL status awaiting Admin approval or rejection
- **Target_Date_Range**: A pair of target_start_date and target_end_date on a Job indicating the scheduling window
- **Disclosure_Record**: An immutable audit log entry tracking a compliance disclosure sent to a customer (pre-sale, confirmation, renewal notice, annual notice, cancellation confirmation) per MN Stat. 325G.56–325G.62
- **Disclosure_Type**: One of PRE_SALE, CONFIRMATION, RENEWAL_NOTICE, ANNUAL_NOTICE, MATERIAL_CHANGE, CANCELLATION_CONF
- **MN_Auto_Renewal_Law**: Minnesota Statute 325G.56–325G.62, effective January 1, 2025, governing auto-renewing service agreements. Requires pre-sale disclosures, post-purchase confirmation, pre-renewal notices (5–30 days before renewal), annual notices, and click-to-cancel capability
- **Compliance_Service**: The backend component responsible for creating and querying Disclosure_Records and enforcing compliance automation schedules
- **Checkout_Service**: The backend component responsible for creating Stripe Checkout Sessions with consent_token and UTM metadata, replacing static Payment Links
- **Onboarding_Service**: The backend component responsible for verifying Stripe sessions and collecting post-purchase property details from customers
- **SMS_Consent_Record**: An immutable audit log entry tracking SMS consent given or revoked by a customer, per TCPA requirements. Records are INSERT-ONLY; opt-outs create new rows
- **Consent_Token**: A UUID generated during the pre-checkout consent flow (Step 1) that links orphaned consent and disclosure records to the Customer and ServiceAgreement created after Stripe payment (Step 2)
- **Three_Step_Purchase_Flow**: The purchase sequence: Step 1 (pre-checkout consent modal captures T&C + SMS consent), Step 2 (Stripe Checkout processes payment), Step 3 (post-purchase onboarding collects property details)
- **LeadSource**: Enum identifying the channel through which a lead was acquired. Values: WEBSITE, GOOGLE_FORM, PHONE_CALL, TEXT_MESSAGE, GOOGLE_AD, SOCIAL_MEDIA, QR_CODE, EMAIL_CAMPAIGN, TEXT_CAMPAIGN, REFERRAL, OTHER
- **IntakeTag**: Enum classifying a lead's routing disposition: SCHEDULE (ready for the scheduling pipeline) or FOLLOW_UP (needs human review before scheduling)
- **Follow_Up_Queue**: A filtered view of leads tagged FOLLOW_UP with active statuses (NEW, CONTACTED, QUALIFIED), displayed as a dedicated section in the Leads tab and as a dashboard widget
- **Lead_Confirmation**: An automated SMS and/or email message sent immediately after a lead is created, confirming receipt of the customer's request. SMS is gated on sms_consent per TCPA requirements
- **Lead_Service**: The backend service responsible for lead creation, source tracking, intake tagging, follow-up queue queries, and lead-to-customer conversion
- **Leads_Dashboard**: The frontend Leads tab in the admin dashboard, including the leads table, source filters, intake tag filters, and the Follow-Up Queue section
- **Email_Service**: The backend component responsible for sending transactional and commercial emails via a third-party provider (e.g., Resend, SendGrid). Transactional emails (confirmations, compliance notices) are sent from a noreply@ address; commercial emails require CAN-SPAM compliance (physical address, unsubscribe link)
- **MN_Sales_Tax**: Minnesota state sales tax (6.875% base rate plus applicable local taxes) that applies to irrigation services. Collected via Stripe Tax at checkout

## Requirements

### Requirement 1: ServiceAgreementTier Model

**User Story:** As an Admin, I want a template table defining what each service package includes, so that the system can reference standardized tier definitions when creating agreements and generating jobs.

#### Acceptance Criteria

1. THE Platform SHALL store ServiceAgreementTier records with the fields: id (UUID), name, slug (unique), description, package_type (RESIDENTIAL or COMMERCIAL), annual_price (DECIMAL), billing_frequency (ANNUAL), included_services (JSONB array of service_type, frequency, and description objects), perks (JSONB array), stripe_product_id, stripe_price_id, is_active (boolean), display_order (integer), created_at, and updated_at
2. THE Platform SHALL enforce a unique constraint on the slug field of ServiceAgreementTier
3. THE Platform SHALL seed 6 ServiceAgreementTier records via migration: Essential Residential ($170), Essential Commercial ($225), Professional Residential ($250), Professional Commercial ($375), Premium Residential ($700), Premium Commercial ($850). The stripe_product_id and stripe_price_id fields MAY be NULL in seed data and populated later via environment-specific configuration or admin action, since Stripe product IDs differ between test and live environments
4. WHEN a ServiceAgreementTier has is_active set to false, THE Platform SHALL exclude that tier from new agreement creation

### Requirement 2: ServiceAgreement Model

**User Story:** As an Admin, I want a record for each customer's subscription instance, so that I can track agreement status, payment state, renewal dates, and linked jobs.

#### Acceptance Criteria

1. THE Platform SHALL store ServiceAgreement records with the fields: id (UUID), agreement_number (unique, auto-generated as "AGR-YYYY-NNN"), customer_id (FK to customers), tier_id (FK to service_agreement_tiers), property_id (FK to properties, nullable), stripe_subscription_id, stripe_customer_id, status (Agreement_Status), start_date, end_date, renewal_date, auto_renew (boolean, default true), cancelled_at, cancellation_reason, pause_reason, annual_price (DECIMAL locked at purchase time), payment_status (Payment_Status), last_payment_date, last_payment_amount, renewal_approved_by (FK to staff, nullable), renewal_approved_at, consent_recorded_at (TIMESTAMP, nullable), consent_method (VARCHAR, nullable — "web_form", "stripe_checkout", "in_person"), disclosure_version (VARCHAR, nullable — version of T&C/disclosures shown at signup), last_annual_notice_sent (TIMESTAMP, nullable — tracks MN annual notice requirement), last_renewal_notice_sent (TIMESTAMP, nullable — tracks 5-30 day pre-renewal notice), notes, created_at, and updated_at
2. THE Platform SHALL enforce a unique constraint on the agreement_number field
3. THE Platform SHALL auto-generate agreement_number in the format "AGR-YYYY-NNN" where YYYY is the current year and NNN is a zero-padded sequential number within that year
4. THE Platform SHALL store the annual_price on the ServiceAgreement at the time of purchase, independent of subsequent changes to the ServiceAgreementTier price
5. THE Platform SHALL store nullable cancellation_refund_amount (DECIMAL(10,2)) and cancellation_refund_processed_at (TIMESTAMP) fields on the ServiceAgreement for tracking prorated refund amounts when a subscription is cancelled after partial service delivery

### Requirement 3: AgreementStatusLog Model

**User Story:** As an Admin, I want an audit trail of every status change on a service agreement, so that I can review the history of an agreement for troubleshooting and compliance.

#### Acceptance Criteria

1. THE Platform SHALL store AgreementStatusLog records with the fields: id (UUID), agreement_id (FK to service_agreements), old_status, new_status, changed_by (FK to staff, nullable for system-triggered changes), reason (text, nullable), metadata (JSONB, nullable), and created_at
2. WHEN a ServiceAgreement status changes, THE Agreement_Service SHALL create an AgreementStatusLog record capturing the old status, new status, actor, reason, and any relevant metadata including the Stripe event ID when applicable

### Requirement 4: Job Model Extensions

**User Story:** As an Admin, I want jobs linked to service agreements with target scheduling windows, so that I can see which jobs come from subscriptions and when they should be scheduled.

#### Acceptance Criteria

1. THE Platform SHALL add a nullable service_agreement_id (FK to service_agreements) field to the Job model
2. THE Platform SHALL add nullable target_start_date (DATE) and target_end_date (DATE) fields to the Job model
3. WHEN a Job has a non-null service_agreement_id, THE Platform SHALL treat that Job as a Seasonal_Job originating from a subscription

### Requirement 5: Agreement Status Lifecycle

**User Story:** As an Admin, I want agreements to follow a defined status flow with valid transitions, so that agreement state is always consistent and auditable.

#### Acceptance Criteria

1. THE Agreement_Service SHALL enforce the following valid status transitions: PENDING to ACTIVE; ACTIVE to PAST_DUE, PENDING_RENEWAL, CANCELLED, or EXPIRED; PAST_DUE to ACTIVE or PAUSED; PAUSED to ACTIVE or CANCELLED; PENDING_RENEWAL to ACTIVE or EXPIRED; EXPIRED to ACTIVE (win-back re-subscription)
2. IF an invalid status transition is requested, THEN THE Agreement_Service SHALL reject the transition and return a descriptive error identifying the current status and the attempted target status
3. WHEN a status transition occurs, THE Agreement_Service SHALL log the transition in the AgreementStatusLog with the actor and reason

### Requirement 6: Stripe Webhook Endpoint

**User Story:** As an Admin, I want the platform to automatically process Stripe webhook events, so that purchases, payments, and subscription changes are reflected in the system without manual intervention.

#### Acceptance Criteria

1. THE Webhook_Handler SHALL expose a POST endpoint at /api/v1/webhooks/stripe that accepts Stripe webhook events
2. THE Webhook_Handler SHALL verify the Stripe webhook signature using the raw request body and the STRIPE_WEBHOOK_SECRET environment variable
3. IF the Stripe webhook signature verification fails, THEN THE Webhook_Handler SHALL return HTTP 400 and reject the event
4. THE Webhook_Handler SHALL route verified events to the appropriate handler based on event type: checkout.session.completed, invoice.paid, invoice.payment_failed, invoice.upcoming, customer.subscription.updated, and customer.subscription.deleted
5. THE Webhook_Handler SHALL log every received event using structured logging with the Stripe event ID, event type, and processing outcome following the `{domain}.{component}.{action}_{state}` pattern (e.g., `stripe.webhook.checkout_completed`)
6. THE Webhook_Handler SHALL return HTTP 200 within 5 seconds for all received events, regardless of processing outcome
7. THE Webhook_Handler SHALL be excluded from CSRF middleware protection

### Requirement 7: Webhook Idempotency

**User Story:** As an Admin, I want webhook processing to be idempotent, so that duplicate Stripe events do not create duplicate records.

#### Acceptance Criteria

1. THE Platform SHALL store Stripe_Webhook_Event records with the fields: id (UUID), stripe_event_id (unique), event_type, processing_status (success, failed, or skipped_duplicate), error_message (nullable), event_data (JSONB, nullable), and processed_at
2. WHEN the Webhook_Handler receives an event with a stripe_event_id that already exists in the Stripe_Webhook_Event table, THE Webhook_Handler SHALL skip processing and return HTTP 200 with status "already_processed"
3. WHEN the Webhook_Handler processes an event, THE Webhook_Handler SHALL record the stripe_event_id, event_type, and processing_status in the Stripe_Webhook_Event table regardless of whether processing succeeded or failed

### Requirement 8: Checkout Session Completed Handler

**User Story:** As an Admin, I want the system to automatically create a customer, agreement, and seasonal jobs when a Stripe checkout completes, so that new subscribers are immediately tracked and their work is queued.

#### Acceptance Criteria

1. WHEN a checkout.session.completed event is received, THE Webhook_Handler SHALL extract the customer email from the Stripe session and search for an existing Customer record by email
2. WHEN no existing Customer matches the email from a checkout.session.completed event, THE Webhook_Handler SHALL create a new Customer record using the name, email, phone, and address from the Stripe session customer_details
3. WHEN an existing Customer matches the email from a checkout.session.completed event, THE Webhook_Handler SHALL use the existing Customer record and update the stripe_customer_id
4. WHEN a checkout.session.completed event is received, THE Agreement_Service SHALL create a ServiceAgreement with status PENDING, linked to the matched or created Customer and the appropriate ServiceAgreementTier identified by the subscription metadata (package_tier and package_type)
5. WHEN a ServiceAgreement is created from a checkout.session.completed event, THE Job_Generator SHALL create Seasonal_Jobs for the agreement based on the tier's included_services definition
6. WHEN a ServiceAgreement is created, THE Agreement_Service SHALL lock the annual_price from the ServiceAgreementTier at the time of creation
7. WHEN a checkout.session.completed event includes a `consent_token` in the Stripe session metadata, THE Webhook_Handler SHALL use the consent_token to link pre-existing orphaned Disclosure_Records and sms_consent_records (where customer_id IS NULL and consent_token matches) to the newly created Customer and ServiceAgreement, bridging the 3-step purchase flow (pre-checkout consent → Stripe payment → record linkage)

### Requirement 9: Seasonal Job Generation

**User Story:** As an Admin, I want seasonal jobs auto-generated with correct visit types and target date ranges per tier, so that the full year's workload is visible immediately after purchase.

#### Acceptance Criteria

1. WHEN generating jobs for an Essential tier agreement, THE Job_Generator SHALL create 2 jobs: one "Spring Startup" with target_start_date April 1 and target_end_date April 30, and one "Fall Winterization" with target_start_date October 1 and target_end_date October 31
2. WHEN generating jobs for a Professional tier agreement, THE Job_Generator SHALL create 3 jobs: one "Spring Startup" (April 1-30), one "Mid-Season Inspection" (July 1-31), and one "Fall Winterization" (October 1-31)
3. WHEN generating jobs for a Premium tier agreement, THE Job_Generator SHALL create 7 jobs: one "Spring Startup" (April 1-30), five "Monthly Visit" jobs for May through September (each with the 1st through last day of the respective month), and one "Fall Winterization" (October 1-31)
4. THE Job_Generator SHALL create all Seasonal_Jobs with status APPROVED, skipping the REQUESTED status
5. THE Job_Generator SHALL create all Seasonal_Jobs with category READY_TO_SCHEDULE
6. THE Job_Generator SHALL link all Seasonal_Jobs to the ServiceAgreement via service_agreement_id and to the Customer via customer_id
7. THE Job_Generator SHALL set the property_id on Seasonal_Jobs from the ServiceAgreement's property_id when available

### Requirement 10: Invoice Paid Handler

**User Story:** As an Admin, I want the system to activate agreements and handle renewals when Stripe confirms payment, so that agreement status stays in sync with billing.

#### Acceptance Criteria

1. WHEN an invoice.paid event is received for a subscription's first invoice, THE Agreement_Service SHALL transition the ServiceAgreement status from PENDING to ACTIVE
2. WHEN an invoice.paid event is received for a renewal invoice, THE Agreement_Service SHALL transition the ServiceAgreement status to ACTIVE, update the end_date and renewal_date for the new term, and trigger the Job_Generator to create the next season's Seasonal_Jobs
3. WHEN an invoice.paid event is received, THE Agreement_Service SHALL update the ServiceAgreement's last_payment_date, last_payment_amount, and set payment_status to CURRENT

### Requirement 11: Invoice Payment Failed Handler

**User Story:** As an Admin, I want the system to flag agreements with failed payments, so that I can see which customers need outreach.

#### Acceptance Criteria

1. WHEN an invoice.payment_failed event is received, THE Agreement_Service SHALL transition the ServiceAgreement status to PAST_DUE and set payment_status to PAST_DUE
2. WHEN an invoice.payment_failed event is received and the ServiceAgreement is already PAST_DUE with all Stripe retries exhausted, THE Agreement_Service SHALL transition the status to PAUSED and set payment_status to FAILED

### Requirement 12: Subscription Updated Handler

**User Story:** As an Admin, I want the system to reflect subscription changes made directly in Stripe (such as payment method updates or metadata changes), so that the local agreement record stays in sync with Stripe's state.

#### Acceptance Criteria

1. WHEN a customer.subscription.updated event is received, THE Agreement_Service SHALL update the ServiceAgreement's stripe_subscription_id and any changed subscription metadata fields
2. WHEN a customer.subscription.updated event indicates the subscription status has changed (e.g., from past_due to active after a successful retry), THE Agreement_Service SHALL transition the ServiceAgreement status accordingly and log the change in AgreementStatusLog with the Stripe event ID in metadata
3. WHEN a customer.subscription.updated event indicates the customer updated their payment method via the Stripe Customer Portal and a previously failed payment succeeds, THE Agreement_Service SHALL transition the ServiceAgreement from PAUSED to ACTIVE, set payment_status to CURRENT, clear pause_reason, and resume normal job generation
4. WHEN a customer.subscription.updated event indicates the subscription's cancel_at_period_end flag has changed, THE Agreement_Service SHALL update the ServiceAgreement's auto_renew field accordingly (cancel_at_period_end=true maps to auto_renew=false, and vice versa)
5. THE Webhook_Handler SHALL treat customer.subscription.updated as idempotent — if the local ServiceAgreement already reflects the updated state, no changes SHALL be made

### Requirement 13: Invoice Upcoming Handler

**User Story:** As an Admin, I want to be notified when a subscription renewal is approaching, so that I can review and approve or reject the renewal.

#### Acceptance Criteria

1. WHEN an invoice.upcoming event is received, THE Agreement_Service SHALL transition the ServiceAgreement status to PENDING_RENEWAL
2. WHEN an invoice.upcoming event is received, THE Agreement_Service SHALL add the agreement to the Renewal_Pipeline visible in the Agreements_Dashboard
3. THE Platform SHALL document that the Stripe `invoice.upcoming` webhook must be configured to fire at least 30 days before the renewal date (Stripe's default is 3 days) to satisfy MN Stat. 325G.59's requirement of 5–30 days pre-renewal notice and to provide adequate time for Admin review

### Requirement 14: Subscription Deleted Handler

**User Story:** As an Admin, I want the system to cancel agreements and future jobs when a Stripe subscription is deleted, so that the system reflects the actual subscription state.

#### Acceptance Criteria

1. WHEN a customer.subscription.deleted event is received, THE Agreement_Service SHALL transition the ServiceAgreement status to CANCELLED
2. WHEN a ServiceAgreement is cancelled, THE Agreement_Service SHALL cancel all linked Seasonal_Jobs that have status APPROVED (not yet scheduled or in progress)
3. WHEN a ServiceAgreement is cancelled, THE Agreement_Service SHALL preserve all linked Seasonal_Jobs that have status SCHEDULED, IN_PROGRESS, or COMPLETED
4. WHEN a ServiceAgreement is cancelled, THE Agreement_Service SHALL compute the prorated refund amount using the formula `annual_price × (remaining_visits / total_visits)` where remaining_visits is the count of linked Seasonal_Jobs NOT in COMPLETED status and total_visits is the total job count for the tier, and store the result in cancellation_refund_amount. The actual Stripe refund is triggered manually by Admin via the Stripe Dashboard — the platform computes and displays the amount but does not initiate the refund API call

### Requirement 15: Failed Payment Escalation Background Job

**User Story:** As an Admin, I want the system to automatically escalate failed payments on a schedule (Day 7 → PAUSED, Day 21 → CANCELLED), so that unresolved payment failures are handled consistently without manual tracking.

#### Acceptance Criteria

1. THE Platform SHALL run a daily background job (`escalate_failed_payments`) that queries all ServiceAgreements with payment_status PAST_DUE or FAILED
2. WHEN a ServiceAgreement has been in PAST_DUE status for 7 or more days with all Stripe retries exhausted, THE background job SHALL call the Stripe API to pause payment collection (`pause_collection` with behavior `keep_as_draft`), transition the agreement status to PAUSED, set pause_reason to "Payment failed — all retries exhausted", and stop generating new jobs for the agreement
3. WHEN a ServiceAgreement has been in PAUSED status for 14 or more days (Day 21+ from initial failure) with no resolution, THE background job SHALL call the Stripe API to cancel the subscription and transition the agreement status to CANCELLED
4. THE background job SHALL log each escalation action using structured logging with the agreement_id, escalation step (day_7_pause or day_21_cancel), and Stripe API response

### Requirement 16: Background Task Scheduler Infrastructure (APScheduler)

**User Story:** As a Developer, I want a persistent background task scheduler integrated with the FastAPI application, so that time-based automation (renewal checks, annual notices, failed payment escalation) runs reliably without manual intervention.

#### Acceptance Criteria

1. THE Platform SHALL include `apscheduler` as a backend dependency and configure it with a PostgreSQL job store for persistence across application restarts
2. THE Platform SHALL start the APScheduler instance on FastAPI application startup and shut it down gracefully on application shutdown
3. THE Platform SHALL register the following scheduled jobs at startup: `escalate_failed_payments` (daily), `check_upcoming_renewals` (daily at 9 AM — queries agreements approaching renewal_date and triggers urgency alerts), `send_annual_notices` (daily in January — queries ACTIVE agreements needing annual notices per MN Stat. 325G.59), and `cleanup_orphaned_consent_records` (weekly — marks consent records older than 30 days with no linked customer as abandoned)
4. THE Platform SHALL log each scheduled job execution start and completion using structured logging with the job name, execution time, and outcome

### Requirement 17: Renewal Approval Gate

**User Story:** As an Admin, I want a 30-day window to review upcoming renewals before Stripe auto-charges, so that I can reject renewals for problematic accounts.

#### Acceptance Criteria

1. THE Agreements_Dashboard SHALL display a Renewal_Pipeline queue showing all agreements in PENDING_RENEWAL status, sorted by renewal_date ascending
2. WHEN the Admin approves a renewal, THE Agreement_Service SHALL record the renewal_approved_by and renewal_approved_at fields and allow Stripe to proceed with the auto-charge
3. WHEN the Admin rejects a renewal, THE Agreement_Service SHALL call the Stripe API to set cancel_at_period_end on the subscription and transition the agreement status to EXPIRED at the end of the current term
4. WHEN the Admin takes no action on a renewal before the renewal_date, THE Platform SHALL allow Stripe to auto-charge (safe default to preserve revenue), and the agreement SHALL be updated upon receiving the invoice.paid event
5. WHEN a renewal is 7 days away and the Admin has not yet reviewed it, THE Agreements_Dashboard SHALL display an urgency alert on the Renewal Pipeline queue indicating "7 renewals need review"
6. WHEN a renewal is 1 day away and the Admin has not yet reviewed it, THE Agreements_Dashboard SHALL display a final alert on the Renewal Pipeline queue indicating these renewals auto-process tomorrow

### Requirement 18: No Mid-Season Tier Changes

**User Story:** As an Admin, I want to prevent tier changes during an active season, so that job generation and pricing remain consistent for the current term.

#### Acceptance Criteria

1. WHILE a ServiceAgreement has status ACTIVE, THE Agreement_Service SHALL reject any request to change the tier_id and return a descriptive error explaining that tier changes are only permitted at renewal

### Requirement 19: Agreement CRUD API

**User Story:** As an Admin, I want API endpoints to list, view, and manage service agreements, so that the frontend can display and interact with agreement data.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/agreements endpoint that returns a paginated list of ServiceAgreements filterable by status, tier_id, customer_id, payment_status, and expiring_soon (boolean — when true, returns agreements within 30 days of renewal_date that have not yet entered PENDING_RENEWAL status)
2. THE Platform SHALL expose a GET /api/v1/agreements/{id} endpoint that returns a single ServiceAgreement with its linked Customer, ServiceAgreementTier, Seasonal_Jobs, and AgreementStatusLog entries
3. THE Platform SHALL expose a PATCH /api/v1/agreements/{id}/status endpoint that accepts a target status and reason, validates the transition, and updates the agreement status
4. THE Platform SHALL expose a POST /api/v1/agreements/{id}/approve-renewal endpoint that records the Admin's approval
5. THE Platform SHALL expose a POST /api/v1/agreements/{id}/reject-renewal endpoint that records the Admin's rejection and triggers Stripe cancellation at period end
6. THE Platform SHALL expose a GET /api/v1/agreement-tiers endpoint that returns all active ServiceAgreementTier records
7. THE Platform SHALL expose a GET /api/v1/agreement-tiers/{id} endpoint that returns a single ServiceAgreementTier record

### Requirement 20: Agreement Metrics API

**User Story:** As an Admin, I want business KPIs computed from agreement data, so that I can monitor the health of the subscription business.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/agreements/metrics endpoint that returns: active agreement count, MRR (sum of annual_price / 12 for ACTIVE agreements), ARPA (Average Revenue Per Agreement, calculated as MRR / active agreement count), renewal rate (renewed / up-for-renewal over trailing 90 days), churn rate (cancelled / total active at period start over trailing 90 days), and past-due amount (sum of annual_price for agreements with payment_status PAST_DUE or FAILED)
2. THE Platform SHALL expose a GET /api/v1/agreements/renewal-pipeline endpoint that returns agreements in PENDING_RENEWAL status sorted by renewal_date ascending
3. THE Platform SHALL expose a GET /api/v1/agreements/failed-payments endpoint that returns agreements with payment_status PAST_DUE or FAILED

### Requirement 21: Dashboard Summary Extension

**User Story:** As an Admin, I want the main dashboard to include subscription metrics, so that I see the subscription business health at a glance alongside existing KPIs.

#### Acceptance Criteria

1. THE Platform SHALL extend the GET /api/v1/dashboard/summary response to include: active agreement count, MRR, renewal pipeline count (agreements in PENDING_RENEWAL), and failed payment count with total dollar amount at risk

### Requirement 22: Frontend — Service Agreements Tab

**User Story:** As an Admin, I want a Service Agreements tab in the admin dashboard, so that I can view and manage all subscription agreements in one place.

#### Acceptance Criteria

1. THE Agreements_Dashboard SHALL display as a new tab labeled "Agreements" in the admin dashboard navigation
2. THE Agreements_Dashboard SHALL display KPI cards at the top showing: Active Agreements count, MRR, Renewal Rate, Churn Rate, and Past Due Amount
3. THE Agreements_Dashboard SHALL display an MRR Over Time line chart showing trailing 12-month MRR data
4. THE Agreements_Dashboard SHALL display an Agreements by Tier chart showing the count of active agreements per tier
5. THE Agreements_Dashboard SHALL display status filter tabs: All, Active, Pending, Pending Renewal, Past Due, Expiring Soon (agreements within 30 days of renewal_date that have not yet entered PENDING_RENEWAL), Cancelled, and Expired
6. THE Agreements_Dashboard SHALL display a table of agreements with columns: Agreement Number, Customer Name, Tier, Package Type, Status, Annual Price, Start Date, Renewal Date, and Jobs Progress (e.g., "2 of 3 visits completed")

### Requirement 23: Frontend — Operational Queues

**User Story:** As an Admin, I want operational queues on the Agreements tab showing items that need my attention, so that I can quickly act on renewals, failed payments, and unscheduled visits.

#### Acceptance Criteria

1. THE Agreements_Dashboard SHALL display a Renewal Pipeline queue showing agreements in PENDING_RENEWAL status with customer name, tier, renewal date, price, visits completed, and Approve/Reject action buttons
2. THE Agreements_Dashboard SHALL display a Failed Payments queue showing agreements in PAST_DUE or PAUSED status with customer name, tier, failed date, amount, current status, and Resume/Cancel action buttons
3. THE Agreements_Dashboard SHALL display an Unscheduled Visits queue showing Seasonal_Jobs in APPROVED status (not yet SCHEDULED) grouped by month and service type, with a link to the Schedule tab
4. THE Agreements_Dashboard SHALL display an Onboarding Incomplete queue showing agreements in PENDING status with no linked property_id

### Requirement 24: Frontend — Agreement Detail View

**User Story:** As an Admin, I want a detail view for each agreement showing its full information, linked jobs, and available actions, so that I can manage individual subscriptions effectively.

#### Acceptance Criteria

1. THE Agreement_Detail_View SHALL display agreement information: tier name, package type, status, annual price, start date, end date, renewal date, auto_renew flag, property address, and customer name with link to customer detail
2. THE Agreement_Detail_View SHALL display a jobs timeline showing all linked Seasonal_Jobs with visual indicators for completed, scheduled, and upcoming jobs
3. THE Agreement_Detail_View SHALL display a jobs progress summary (e.g., "2 of 3 visits completed")
4. THE Agreement_Detail_View SHALL display the AgreementStatusLog as a chronological history of status changes with timestamps, actors, and reasons
5. THE Agreement_Detail_View SHALL display admin notes with the ability to edit
6. WHEN the agreement status is ACTIVE, THE Agreement_Detail_View SHALL display Pause and Cancel action buttons
7. WHEN the agreement status is PAUSED, THE Agreement_Detail_View SHALL display Resume and Cancel action buttons
8. WHEN the agreement status is PENDING_RENEWAL, THE Agreement_Detail_View SHALL display Approve Renewal and Reject Renewal action buttons
9. WHEN the Admin clicks Cancel, THE Agreement_Detail_View SHALL require a cancellation reason before submitting
10. THE Agreement_Detail_View SHALL display a "View in Stripe Dashboard" link that opens the Stripe subscription in the Stripe Dashboard
11. THE Agreement_Detail_View SHALL display a "Customer Portal" link that opens the Stripe Customer Portal for the agreement's customer, using the STRIPE_CUSTOMER_PORTAL_URL configuration

### Requirement 25: Frontend — Dashboard Widgets

**User Story:** As an Admin, I want subscription-related widgets on the main Dashboard tab, so that I see subscription health alongside existing operational metrics.

#### Acceptance Criteria

1. THE Platform SHALL add an Active Agreements widget to the Dashboard tab showing the count of ACTIVE agreements with a trend indicator compared to the prior month
2. THE Platform SHALL add an MRR widget to the Dashboard tab showing the current MRR value with month-over-month change
3. THE Platform SHALL add a Renewal Pipeline widget to the Dashboard tab showing the count of agreements in PENDING_RENEWAL status
4. THE Platform SHALL add a Failed Payments widget to the Dashboard tab showing the count and total dollar amount of agreements with payment_status PAST_DUE or FAILED

### Requirement 26: Frontend — Jobs Tab Subscription Enhancements

**User Story:** As an Admin, I want to see which jobs come from subscriptions and filter by target dates, so that I can prioritize scheduling subscription work.

#### Acceptance Criteria

1. WHEN a Job has a non-null service_agreement_id, THE Platform SHALL display a "Subscription" source badge on that job in the Jobs tab
2. THE Platform SHALL add target date range columns (target_start_date and target_end_date) to the Jobs tab table
3. THE Platform SHALL add a target date range filter to the Jobs tab allowing the Admin to filter jobs by their target scheduling window
4. THE Platform SHALL add a "Subscription" source type filter to the Jobs tab allowing the Admin to show only subscription-originated jobs

### Requirement 27: Stripe Configuration

**User Story:** As an Admin, I want the platform to integrate with Stripe using secure configuration, so that webhook processing and API calls work correctly.

#### Acceptance Criteria

1. THE Platform SHALL read the STRIPE_SECRET_KEY environment variable for Stripe API authentication
2. THE Platform SHALL read the STRIPE_WEBHOOK_SECRET environment variable for webhook signature verification
3. THE Platform SHALL include the stripe Python package as a backend dependency
4. THE Platform SHALL read the STRIPE_CUSTOMER_PORTAL_URL environment variable for generating customer-facing Stripe portal links in renewal notices, cancellation confirmations, and the agreement detail view
5. IF the STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET environment variable is missing at startup, THEN THE Platform SHALL log a warning indicating that Stripe integration is not configured
6. THE Platform SHALL document that the Stripe Customer Portal must be configured with cancellation enabled and "collect cancellation reason" turned on, to satisfy MN Stat. 325G.59's click-to-cancel requirement for online auto-renewing subscriptions

### Requirement 28: Customer Model Extensions for Package Purchases

**User Story:** As an Admin, I want customer records to track Stripe identity, consent status, and service preferences, so that the system maintains a complete customer profile from the moment of purchase.

#### Acceptance Criteria

1. THE Platform SHALL add the following fields to the Customer model: stripe_customer_id (VARCHAR(255), nullable, indexed), terms_accepted (BOOLEAN, default false), terms_accepted_at (TIMESTAMP, nullable), terms_version (VARCHAR(20), nullable — version of T&C agreed to), sms_opt_in_at (TIMESTAMP, nullable), sms_opt_in_source (VARCHAR(50), nullable — "web_form", "stripe_checkout", "text_reply", "verbal"), sms_consent_language_version (VARCHAR(20), nullable — version of TCPA consent text shown), preferred_service_times (JSONB, nullable), and internal_notes (TEXT, nullable — staff-only notes not visible to customer)
2. WHEN a Customer record is created from a checkout.session.completed webhook, THE Webhook_Handler SHALL populate stripe_customer_id from the Stripe session, and set terms_accepted, terms_accepted_at, terms_version, sms_opt_in_at, and sms_opt_in_source from the linked consent_token records if available
3. THE Platform SHALL enforce a unique constraint on stripe_customer_id (when not null) to prevent duplicate Stripe customer linkages

### Requirement 29: SMS Consent Records Model (TCPA Compliance)

**User Story:** As an Admin, I want an immutable audit log of every SMS consent interaction, so that the business has defensible proof of TCPA compliance for all automated text messages sent to customers.

#### Acceptance Criteria

1. THE Platform SHALL store sms_consent_record entries with the fields: id (UUID), customer_id (FK to customers, nullable — linked after purchase), phone_number (VARCHAR(20), NOT NULL), consent_type (enum: TRANSACTIONAL, MARKETING, or BOTH), consent_given (BOOLEAN, NOT NULL), consent_timestamp (TIMESTAMP, NOT NULL), consent_method (VARCHAR(50), NOT NULL — "web_form", "stripe_checkout", "text_reply", "verbal", "paper"), consent_language_shown (TEXT, NOT NULL — exact text shown to consumer at time of consent), consent_form_version (VARCHAR(20), nullable), consent_ip_address (VARCHAR(45), nullable), consent_user_agent (VARCHAR(500), nullable), consent_token (UUID, nullable, indexed — links to pre-checkout consent flow), opt_out_timestamp (TIMESTAMP, nullable), opt_out_method (VARCHAR(50), nullable — "text_stop", "email", "phone_call", "web_form"), opt_out_processed_at (TIMESTAMP, nullable), opt_out_confirmation_sent (BOOLEAN, default false), and created_at (TIMESTAMP)
2. THE Platform SHALL enforce that sms_consent_record entries are INSERT-ONLY and never updated or deleted. A new opt-out is recorded as a new row with consent_given=false and opt_out_timestamp set
3. THE Platform SHALL create indexes on phone_number and customer_id for compliance audit queries
4. THE Platform SHALL retain all sms_consent_record entries for a minimum of 7 years after the last customer interaction, aligned with TCPA statute of limitations (4 years) plus IRS/MN DOR financial record retention (7 years)

### Requirement 30: Pre-Checkout Consent Endpoint

**User Story:** As an Admin, I want the system to capture SMS consent and MN auto-renewal disclosures before the customer enters Stripe Checkout, so that the welcome SMS is legally compliant and the pre-sale disclosure requirement is met before payment.

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/onboarding/pre-checkout-consent endpoint (public, rate-limited to 5 requests per IP per minute) that accepts: package_tier, package_type, sms_consent (boolean), terms_accepted (boolean), consent_ip (VARCHAR), consent_user_agent (VARCHAR), and consent_language_version (VARCHAR)
2. WHEN the pre-checkout-consent endpoint is called, THE Platform SHALL create an sms_consent_record entry with consent_given=sms_consent, consent_method="web_form", and the exact TCPA-compliant consent language shown in the pre-checkout modal
3. WHEN the pre-checkout-consent endpoint is called, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type PRE_SALE, customer_id=NULL (not yet known), and the content_hash of the MN auto-renewal disclosure text shown in the modal
4. THE pre-checkout-consent endpoint SHALL return a consent_token (UUID) that links the sms_consent_record and Disclosure_Record, enabling the checkout webhook handler to associate these records with the Customer and ServiceAgreement after purchase
5. THE pre-checkout-consent endpoint SHALL validate that both sms_consent and terms_accepted are true before proceeding, and return HTTP 422 if either is false

### Requirement 31: Checkout Session Creation Endpoint

**User Story:** As an Admin, I want the platform to create dynamic Stripe Checkout Sessions instead of using static Payment Links, so that consent tokens, UTM parameters, and package metadata can be passed through the checkout flow.

#### Acceptance Criteria

1. THE Platform SHALL expose a POST /api/v1/checkout/create-session endpoint (public, rate-limited to 5 requests per IP per minute) that accepts: package_tier, package_type, consent_token (UUID), and utm_params (optional object with source, medium, campaign)
2. THE create-session endpoint SHALL look up the ServiceAgreementTier by package_tier and package_type, validate it exists and is_active, and use its stripe_price_id to create the Stripe Checkout Session
3. THE create-session endpoint SHALL validate that the consent_token matches a recent Disclosure_Record (created within the last 2 hours) before creating the Checkout Session
4. THE create-session endpoint SHALL create a Stripe Checkout Session in subscription mode with: the tier's stripe_price_id, phone_number_collection enabled, billing_address_collection required, consent_collection with terms_of_service required, automatic_tax enabled (to collect MN state and local sales tax via Stripe Tax), and custom_text acknowledging the auto-renewing subscription
5. THE create-session endpoint SHALL embed the consent_token, package_tier, and package_type in both the session metadata and subscription_data.metadata, and embed utm_source, utm_medium, and utm_campaign in the session metadata
6. THE create-session endpoint SHALL set the success_url to the landing page with a session_id parameter (`?session_id={CHECKOUT_SESSION_ID}`) and the cancel_url to the service packages page
7. THE create-session endpoint SHALL return the Stripe Checkout Session URL for client-side redirect
8. IF the ServiceAgreementTier's stripe_price_id is NULL, THE create-session endpoint SHALL return HTTP 503 with a descriptive error indicating that Stripe is not yet configured for this tier

### Requirement 32: Post-Purchase Onboarding Endpoints

**User Story:** As an Admin, I want the system to collect property details from customers after purchase, so that seasonal jobs can be linked to the correct service address and technicians have the information they need.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/onboarding/verify-session endpoint (public) that accepts a session_id query parameter, verifies the Stripe Checkout Session via the Stripe API, and returns: customer_name, email, phone, billing_address, package_tier, package_type, and payment_status
2. THE Platform SHALL expose a POST /api/v1/onboarding/complete endpoint (public, rate-limited) that accepts: session_id, service_address_same_as_billing (boolean), service_address (optional — street, city, state, zip), zone_count (integer, optional), gate_code (VARCHAR, optional), has_dogs (boolean, optional), access_instructions (TEXT, optional), and preferred_times (enum: MORNING, AFTERNOON, NO_PREFERENCE)
3. WHEN service_address_same_as_billing is true, THE onboarding/complete endpoint SHALL use the billing address from the Stripe session to create or update the Property record
4. WHEN service_address_same_as_billing is false, THE onboarding/complete endpoint SHALL use the provided service_address to create or update the Property record
5. THE onboarding/complete endpoint SHALL link the Property record to the Customer and update the ServiceAgreement's property_id, and update all linked Seasonal_Jobs with the property_id
6. THE onboarding/complete endpoint SHALL update the Customer's preferred_service_times from the submitted preferred_times value
7. IF the onboarding/complete endpoint is called with a session_id that does not match any ServiceAgreement, THE endpoint SHALL return HTTP 404 with a descriptive error

### Requirement 33: Disclosure Records Model (MN Auto-Renewal Compliance)

**User Story:** As an Admin, I want an immutable audit log of every compliance disclosure sent to customers, so that the business has defensible proof of compliance with Minnesota's auto-renewal law (MN Stat. 325G.56–325G.62).

#### Acceptance Criteria

1. THE Platform SHALL store Disclosure_Record entries with the fields: id (UUID), agreement_id (FK to service_agreements, nullable), customer_id (FK to customers, nullable — NULL for pre-checkout records created before customer identity is known), disclosure_type (Disclosure_Type enum), sent_at (TIMESTAMP, NOT NULL), sent_via (VARCHAR — "email", "sms", "mail", "web_form"), recipient_email (VARCHAR, nullable), recipient_phone (VARCHAR, nullable), content_hash (VARCHAR(64), NOT NULL — SHA-256 hash of the disclosure content), content_snapshot (TEXT, nullable — full text or template version of the disclosure), consent_token (UUID, nullable, indexed — links pre-checkout disclosures to the purchase flow), delivery_confirmed (BOOLEAN, default false), and created_at (TIMESTAMP)
2. THE Platform SHALL enforce that Disclosure_Record entries are INSERT-ONLY and never updated or deleted
3. THE Platform SHALL create indexes on agreement_id, customer_id, and the combination of disclosure_type and sent_at for compliance audit queries
4. THE Platform SHALL retain all Disclosure_Record entries for a minimum of 7 years after the last customer interaction, aligned with IRS/MN DOR financial record retention and contract statute of limitations

### Requirement 34: Checkout Compliance — PRE_SALE Disclosure Logging

**User Story:** As an Admin, I want the system to automatically log that pre-sale disclosures were presented when a customer completes a Stripe checkout, so that the business has proof the MN-required disclosures were shown before purchase.

#### Acceptance Criteria

1. WHEN a checkout.session.completed event is processed, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type PRE_SALE, linked to the newly created ServiceAgreement and Customer
2. THE PRE_SALE Disclosure_Record SHALL capture the content_hash of the disclosure text that was shown on the landing page pre-checkout modal, and the sent_via field SHALL be set to "web_form"
3. WHEN a checkout.session.completed event is processed, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type CONFIRMATION, representing the post-purchase confirmation that includes all 5 MN-required auto-renewal terms (service continues until terminated, cancellation policy, recurring charge amount and frequency, renewal term length, minimum purchase obligations)

### Requirement 35: Renewal Notice Compliance Logging

**User Story:** As an Admin, I want the system to log pre-renewal notices when a subscription renewal is approaching, so that the business complies with MN's 5–30 day pre-renewal notice requirement.

#### Acceptance Criteria

1. WHEN an invoice.upcoming event is processed and the Agreement_Service transitions the agreement to PENDING_RENEWAL, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type RENEWAL_NOTICE
2. THE RENEWAL_NOTICE Disclosure_Record SHALL include the renewal date, renewal price, cancellation instructions (Stripe Customer Portal link, phone, email), and a summary of services provided during the current term
3. WHEN a RENEWAL_NOTICE Disclosure_Record is created, THE Agreement_Service SHALL update the ServiceAgreement's last_renewal_notice_sent timestamp

### Requirement 36: Cancellation Compliance Logging

**User Story:** As an Admin, I want the system to log cancellation confirmations when a subscription is cancelled, so that the business has proof the customer was notified per MN requirements.

#### Acceptance Criteria

1. WHEN a customer.subscription.deleted event is processed, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type CANCELLATION_CONF linked to the ServiceAgreement and Customer
2. THE CANCELLATION_CONF Disclosure_Record SHALL capture the cancellation effective date, the reason (if provided), and confirmation that remaining scheduled visits will be honored

### Requirement 37: Annual Notice Tracking

**User Story:** As an Admin, I want the system to track when annual notices are due and sent, so that the business complies with MN's requirement to send at least one written notice per calendar year to active subscribers.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/agreements/annual-notice-due endpoint that returns all ACTIVE agreements where last_annual_notice_sent is NULL or the year of last_annual_notice_sent is before the current calendar year
2. WHEN an annual notice is sent for a ServiceAgreement, THE Compliance_Service SHALL create a Disclosure_Record with disclosure_type ANNUAL_NOTICE and update the ServiceAgreement's last_annual_notice_sent timestamp
3. THE ANNUAL_NOTICE Disclosure_Record SHALL include the current terms of the service and instructions on how to terminate or manage the subscription

### Requirement 38: Compliance Audit API

**User Story:** As an Admin, I want to view the full compliance history for any agreement or customer, so that I can verify disclosure obligations have been met before audits or disputes.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/agreements/{id}/compliance endpoint that returns all Disclosure_Records linked to that agreement, sorted by sent_at descending
2. THE Platform SHALL expose a GET /api/v1/compliance/customer/{customer_id} endpoint that returns all Disclosure_Records for a customer across all their agreements, sorted by sent_at descending
3. EACH Disclosure_Record in the API response SHALL include the disclosure_type, sent_at, sent_via, content_snapshot (or content_hash if snapshot is unavailable), and delivery_confirmed status

### Requirement 39: Frontend — Agreement Detail Compliance Section

**User Story:** As an Admin, I want to see the compliance disclosure history on the agreement detail view, so that I can verify at a glance whether all required notices have been sent.

#### Acceptance Criteria

1. THE Agreement_Detail_View SHALL display a "Compliance Log" section showing all Disclosure_Records for the agreement in chronological order
2. EACH entry in the Compliance Log SHALL display the disclosure_type as a labeled badge (e.g., "Pre-Sale", "Confirmation", "Renewal Notice", "Annual Notice", "Cancellation"), the sent_at date, sent_via method, and delivery_confirmed status
3. THE Agreement_Detail_View SHALL display a compliance status summary indicating whether all required disclosures are up to date: PRE_SALE recorded (yes/no), CONFIRMATION sent (yes/no), last RENEWAL_NOTICE date, last ANNUAL_NOTICE date
4. WHEN a required disclosure is missing or overdue (e.g., no ANNUAL_NOTICE in the current calendar year for an ACTIVE agreement), THE Agreement_Detail_View SHALL display a warning indicator on the compliance status summary

### Requirement 39A: Stripe Tax and MN Sales Tax Configuration

**User Story:** As an Admin, I want the platform to collect Minnesota state and local sales tax on service package purchases via Stripe Tax, so that the business complies with MN tax obligations on taxable irrigation services.

#### Acceptance Criteria

1. THE Platform SHALL document that Stripe Tax must be enabled in the Stripe Dashboard (Settings → Tax) with the business origin address set to the company's physical address in Minnesota
2. THE Platform SHALL document that a Minnesota tax registration must be added to the Stripe Tax configuration with the business's MN Tax ID (obtained from the Minnesota Department of Revenue)
3. THE Platform SHALL document that the tax behavior on all Stripe Prices must be set to "exclusive" (tax added on top of the listed price), so that the displayed tier prices ($170, $250, $700, $225, $375, $850) remain the base price and tax is calculated and added at checkout
4. THE Platform SHALL configure the Checkout Session creation (Requirement 31) with `automatic_tax: { enabled: true }` so that Stripe Tax calculates and collects the applicable MN state tax (6.875%) plus any local taxes based on the customer's billing address
5. THE Platform SHALL document that the landing page pricing cards should display "+ applicable tax" alongside the annual price to set customer expectations before checkout
6. THE Platform SHALL read an optional STRIPE_TAX_ENABLED environment variable (boolean, default true) to allow disabling automatic tax collection in test environments where Stripe Tax is not configured

### Requirement 39B: Email Service for Compliance Notification Delivery

**User Story:** As an Admin, I want the platform to send compliance-required emails to customers at key lifecycle events (purchase confirmation, renewal notice, annual notice, cancellation confirmation), so that the business actually delivers the notifications that MN Stat. 325G.56–325G.62 requires and the disclosure records accurately reflect sent communications.

#### Acceptance Criteria

1. THE Platform SHALL integrate an email sending service (e.g., Resend, SendGrid) as a backend dependency, configured via an EMAIL_API_KEY environment variable
2. THE Platform SHALL configure a transactional email sender address (e.g., noreply@grinsirrigation.com) for compliance and operational emails, and document that SPF, DKIM, and DMARC DNS records must be configured for the sending domain
3. THE Email_Service SHALL send a CONFIRMATION email immediately after a checkout.session.completed event is processed, containing all 5 MN-required auto-renewal terms: (a) the service continues until the consumer terminates it, (b) the cancellation policy with Stripe Customer Portal link, phone number (952) 818-1020, and email info@grinsirrigation.com, (c) the recurring charge amount and billing frequency, (d) the renewal term length, and (e) any minimum purchase obligations
4. THE Email_Service SHALL send a RENEWAL_NOTICE email when an invoice.upcoming event transitions an agreement to PENDING_RENEWAL, containing: the renewal date, renewal price, cancellation instructions (Stripe Customer Portal link, phone, email), and a summary of services provided during the current term (completed job names and dates)
5. THE Email_Service SHALL send an ANNUAL_NOTICE email when the send_annual_notices background job identifies ACTIVE agreements needing annual notices, containing: the current terms of the service and instructions on how to terminate or manage the subscription via the Stripe Customer Portal
6. THE Email_Service SHALL send a CANCELLATION_CONF email when a customer.subscription.deleted event is processed, containing: the cancellation effective date, the reason (if provided), confirmation that remaining scheduled visits will be honored, and the prorated refund amount (if applicable)
7. WHEN the Email_Service sends a compliance email, THE Compliance_Service SHALL create the corresponding Disclosure_Record with sent_via set to "email", recipient_email set to the customer's email, and delivery_confirmed updated based on the email provider's delivery status callback
8. IF the EMAIL_API_KEY environment variable is missing at startup, THEN THE Platform SHALL log a warning indicating that email delivery is not configured, and compliance disclosure records SHALL still be created with sent_via set to "pending" and delivery_confirmed set to false
9. THE Email_Service SHALL use Jinja2 HTML email templates stored in the backend codebase, with each compliance email template including the Grins Irrigation business name, contact information, and Stripe Customer Portal link
10. THE Email_Service SHALL log every email send attempt using structured logging with the recipient email (masked), email type, disclosure_type, and delivery status following the `{domain}.{component}.{action}_{state}` pattern (e.g., `email.compliance.renewal_notice_sent`)

### Requirement 39C: Welcome Email on Purchase

**User Story:** As an Admin, I want the system to send a welcome email immediately after a customer purchases a service package, so that the customer receives a written confirmation of their subscription with all relevant details and next steps.

#### Acceptance Criteria

1. WHEN a checkout.session.completed event is processed and a ServiceAgreement is created, THE Email_Service SHALL send a welcome email to the customer's email address with subject line "Welcome to Grins Irrigation [tier_name] Plan!"
2. THE welcome email SHALL include: the subscription tier name and package type, the annual price, the start date, a list of included services from the tier's included_services definition, a link to the Stripe Customer Portal for managing billing, a link to the post-purchase onboarding form (with session_id) for providing property details, and contact information (phone and email)
3. THE welcome email SHALL be distinct from the MN compliance CONFIRMATION email (Requirement 39B AC3) — the welcome email is a customer-friendly overview while the CONFIRMATION email contains the legally required auto-renewal terms. Both SHALL be sent, either as two separate emails or as a single combined email that includes all MN-required terms alongside the welcome content
4. IF the customer's email address is not available from the Stripe session, THE Email_Service SHALL skip the welcome email and log a warning using structured logging


### Requirement 40: Backend Testing

**User Story:** As a Developer, I want comprehensive backend test coverage for all service package functionality, so that business logic, data access, and webhook processing are verified to work correctly in isolation and together.

#### Acceptance Criteria

1. THE Platform SHALL include unit tests (`@pytest.mark.unit`) with mocked dependencies for: Agreement_Service (all status transitions, renewal approval/rejection, tier change rejection), Webhook_Handler (all 6 event types, signature verification, idempotency), Job_Generator (correct job counts and date ranges per tier), Metrics_Service (MRR, ARPA, renewal rate, churn rate calculations), Compliance_Service (disclosure record creation for each disclosure type), Checkout_Service (session creation, consent_token validation, tier lookup, automatic_tax configuration), Onboarding_Service (session verification, property creation, consent_token linkage), and Email_Service (correct email sent for each compliance event, template rendering, delivery status handling, skip behavior when email is unavailable)
2. THE Platform SHALL include functional tests (`@pytest.mark.functional`) with a real database for: full agreement lifecycle (PENDING → ACTIVE → PENDING_RENEWAL → ACTIVE), checkout webhook → customer + agreement + jobs creation pipeline, failed payment escalation (ACTIVE → PAST_DUE → PAUSED → CANCELLED), renewal approval and rejection workflows, seasonal job generation with correct linking, Portal payment recovery (PAUSED → ACTIVE via subscription.updated), and compliance email dispatch pipeline (checkout → welcome email + confirmation email, renewal → renewal notice email, cancellation → cancellation confirmation email)
3. THE Platform SHALL include integration tests (`@pytest.mark.integration`) for: Stripe webhook endpoint receiving simulated Stripe payloads with signature verification, agreement CRUD API endpoints with filtering and pagination, metrics API returning correct computed values, and dashboard summary extension including agreement data
4. THE Platform SHALL include property-based tests (Hypothesis) for: job generation logic (given any valid tier, the correct number of jobs with valid non-overlapping date ranges are produced), agreement number generation (format AGR-YYYY-NNN is always valid and sequential), status transition validation (only valid transitions succeed, all invalid transitions are rejected), and MRR calculation (sum of annual_price / 12 for any set of active agreements equals the reported MRR)
5. ALL backend tests SHALL pass with zero failures before the feature is considered complete
6. Backend test coverage SHALL meet or exceed 90% line coverage for all new service, repository, and webhook handler modules

### Requirement 41: Frontend Component Testing

**User Story:** As a Developer, I want comprehensive frontend test coverage for all new and modified UI components, so that the admin dashboard renders correctly and interactive elements function as expected.

#### Acceptance Criteria

1. THE Platform SHALL include Vitest + React Testing Library component tests for: AgreementsList (status tab filtering, table rendering, pagination), AgreementDetail (info display, jobs timeline, status action buttons per status, compliance log), RenewalPipelineQueue (approve/reject actions, urgency alerts), FailedPaymentsQueue (resume/cancel actions), UnscheduledVisitsQueue (grouping by month, link to schedule), OnboardingIncompleteQueue (send reminder action), BusinessMetricsCards (KPI values, trend indicators), and DashboardWidgets (active agreements, MRR, renewal pipeline, failed payments)
2. THE Platform SHALL include hook tests for all new TanStack Query hooks: useAgreements, useAgreement, useAgreementMetrics, useRenewalPipeline, useFailedPayments, useCreateAgreement, useUpdateAgreementStatus, useApproveRenewal, and useRejectRenewal
3. THE Platform SHALL include form validation tests for any agreement-related forms including cancellation reason input and admin notes editing
4. ALL frontend component tests SHALL verify loading states, error states, and empty states for data-fetching components
5. ALL frontend tests SHALL pass with zero failures before the feature is considered complete
6. Frontend component test coverage SHALL meet or exceed 80% for components and 85% for hooks

### Requirement 42: Agent-Browser UI Validation

**User Story:** As a Developer, I want end-to-end UI validation using Vercel Agent Browser for all new and modified admin dashboard pages, so that the user interface is verified to work correctly in a real browser environment.

#### Acceptance Criteria

1. THE Platform SHALL include agent-browser validation scripts that verify the Service Agreements tab: page loads without errors, KPI cards render with data, MRR Over Time chart renders, Agreements by Tier chart renders, status filter tabs are clickable and filter the table, agreement table renders with correct columns, and clicking an agreement row navigates to the detail view
2. THE Platform SHALL include agent-browser validation scripts that verify the Agreement Detail view: agreement info section renders with all fields, jobs timeline renders with visual indicators, compliance log section renders with disclosure entries, status action buttons are visible and appropriate for the current agreement status, and clicking action buttons triggers the expected modals or state changes
3. THE Platform SHALL include agent-browser validation scripts that verify the Operational Queues: Renewal Pipeline queue renders with approve/reject buttons, Failed Payments queue renders with resume/cancel buttons, Unscheduled Visits queue renders grouped by month, Onboarding Incomplete queue renders with send reminder button, and urgency alerts display when renewals are within 7 days
4. THE Platform SHALL include agent-browser validation scripts that verify the Dashboard tab modifications: Active Agreements widget renders with count and trend, MRR widget renders with value and month-over-month change, Renewal Pipeline widget renders with count, and Failed Payments widget renders with count and dollar amount
5. THE Platform SHALL include agent-browser validation scripts that verify the Jobs tab modifications: Subscription source badge displays on subscription-originated jobs, target date columns render, target date range filter functions correctly, and Subscription source filter functions correctly
6. ALL agent-browser validation scripts SHALL pass without errors before the feature is considered complete

### Requirement 43: Code Quality Gate

**User Story:** As a Developer, I want all new code to pass linting, formatting, and type checking with zero errors, so that the codebase maintains consistent quality standards.

#### Acceptance Criteria

1. ALL new backend Python code SHALL pass `ruff check` with zero violations
2. ALL new backend Python code SHALL pass `ruff format` verification (88 character line limit)
3. ALL new backend Python code SHALL pass `mypy` strict mode with zero type errors
4. ALL new backend Python code SHALL pass `pyright` with zero type errors
5. ALL new frontend TypeScript code SHALL pass ESLint with zero errors
6. ALL new frontend TypeScript code SHALL pass TypeScript strict mode compilation with zero errors
7. ALL new backend services SHALL use structured logging via LoggerMixin or get_logger following the `{domain}.{component}.{action}_{state}` pattern
8. THE Platform SHALL run the full quality check suite (`ruff check`, `ruff format`, `mypy`, `pyright`, `pytest`, `eslint`, `tsc`) with zero errors before the feature is considered complete

### Requirement 44: Lead Source Tracking — Model Extensions

**User Story:** As an Admin, I want each lead to record which channel it came from and optional source details, so that I can measure marketing effectiveness and prioritize high-converting channels.

#### Acceptance Criteria

1. THE Platform SHALL add a lead_source field (VARCHAR(50), NOT NULL, DEFAULT 'website') to the Lead model, constrained to the LeadSource enum values: WEBSITE, GOOGLE_FORM, PHONE_CALL, TEXT_MESSAGE, GOOGLE_AD, SOCIAL_MEDIA, QR_CODE, EMAIL_CAMPAIGN, TEXT_CAMPAIGN, REFERRAL, OTHER
2. THE Platform SHALL add a source_detail field (VARCHAR(255), nullable) to the Lead model for storing UTM parameters, campaign names, QR code identifiers, or referral source names
3. THE Platform SHALL create an index on the lead_source field for efficient filtering and aggregation queries
4. THE Platform SHALL apply a database migration that sets lead_source to 'website' for all existing Lead records

### Requirement 45: Lead Source Tracking — API Extensions

**User Story:** As an Admin, I want to create leads with source information and filter leads by source, so that I can track where leads originate and analyze channel performance.

#### Acceptance Criteria

1. WHEN a POST /api/v1/leads request includes optional lead_source and source_detail fields, THE Lead_Service SHALL store the provided values on the new Lead record
2. WHEN a POST /api/v1/leads request omits the lead_source field, THE Lead_Service SHALL default lead_source to WEBSITE
3. THE Platform SHALL modify the GET /api/v1/leads endpoint to accept a lead_source query parameter supporting multi-select (comma-separated values) for filtering leads by one or more source channels
4. THE Platform SHALL expose a POST /api/v1/leads/from-call endpoint (authenticated, admin-only) that accepts name, phone, email (optional), zip_code (optional), situation, notes, and lead_source (defaulting to PHONE_CALL) for staff or AI agents to create leads from phone and text interactions
5. THE /api/v1/leads/from-call endpoint SHALL set source_detail to include the caller context (e.g., "Inbound call" or "AI agent interaction") when not explicitly provided

### Requirement 46: Lead Source Tracking — Frontend

**User Story:** As an Admin, I want to see lead sources visually in the Leads tab and filter by source, so that I can quickly identify where leads are coming from.

#### Acceptance Criteria

1. THE Leads_Dashboard SHALL display a LeadSourceBadge component on each lead row showing the lead_source value with a distinct color per source channel
2. THE Leads_Dashboard SHALL display a lead_source filter dropdown (multi-select) allowing the Admin to filter the leads table by one or more source channels
3. THE Leads_Dashboard SHALL display the source_detail value on the Lead Detail view when present
4. THE LeadSourceBadge component SHALL use the data-testid convention: `lead-source-{value}` (e.g., `lead-source-phone_call`)

### Requirement 47: Intake Tagging — Model Extensions

**User Story:** As an Admin, I want each lead tagged as either SCHEDULE or FOLLOW_UP, so that the system can route leads to the appropriate workflow.

#### Acceptance Criteria

1. THE Platform SHALL add an intake_tag field (VARCHAR(20), nullable) to the Lead model, constrained to the IntakeTag enum values: SCHEDULE, FOLLOW_UP
2. THE Platform SHALL create an index on the intake_tag field for efficient filtering
3. THE Platform SHALL apply a database migration that leaves intake_tag as NULL for all existing Lead records

### Requirement 48: Intake Tagging — API Extensions

**User Story:** As an Admin, I want to set and change intake tags on leads and filter by tag, so that I can manage the routing of leads between scheduling and follow-up workflows.

#### Acceptance Criteria

1. WHEN a POST /api/v1/leads request includes an optional intake_tag field, THE Lead_Service SHALL store the provided value on the new Lead record
2. WHEN a lead is created from a website form submission and no intake_tag is provided, THE Lead_Service SHALL default intake_tag to SCHEDULE
3. WHEN a lead is created via the /api/v1/leads/from-call endpoint and no intake_tag is provided, THE Lead_Service SHALL leave intake_tag as NULL for the staff or AI agent to set explicitly
4. THE Platform SHALL modify the GET /api/v1/leads endpoint to accept an intake_tag query parameter for filtering leads by SCHEDULE, FOLLOW_UP, or NULL (untagged)
5. THE Platform SHALL modify the PATCH /api/v1/leads/{id} endpoint to accept an intake_tag field, allowing the Admin to change a lead's intake tag

### Requirement 49: Intake Tagging — Frontend

**User Story:** As an Admin, I want to see intake tags visually and filter by tag in the Leads tab, so that I can quickly distinguish between leads ready for scheduling and those needing follow-up.

#### Acceptance Criteria

1. THE Leads_Dashboard SHALL display an IntakeTagBadge component on each lead row: green for SCHEDULE, orange for FOLLOW_UP, and gray for untagged
2. THE Leads_Dashboard SHALL display quick-filter tabs above the leads table: All, Schedule, Follow Up
3. WHEN the Admin clicks a quick-filter tab, THE Leads_Dashboard SHALL filter the leads table to show only leads matching the selected intake_tag
4. THE IntakeTagBadge component SHALL use the data-testid convention: `intake-tag-{value}` (e.g., `intake-tag-schedule`, `intake-tag-follow_up`)

### Requirement 50: Follow-Up Queue — Backend

**User Story:** As an Admin, I want a dedicated endpoint for the follow-up queue, so that the frontend can efficiently display leads that need human review.

#### Acceptance Criteria

1. THE Platform SHALL expose a GET /api/v1/leads/follow-up-queue endpoint (authenticated, admin-only) that returns leads WHERE intake_tag equals FOLLOW_UP AND status is one of NEW, CONTACTED, or QUALIFIED
2. THE /api/v1/leads/follow-up-queue endpoint SHALL sort results by created_at ascending (oldest first) to prioritize leads waiting the longest
3. THE /api/v1/leads/follow-up-queue endpoint SHALL include a computed time_since_created field (in hours) on each lead in the response for urgency display
4. THE /api/v1/leads/follow-up-queue endpoint SHALL support pagination with page and page_size query parameters

### Requirement 51: Follow-Up Queue — Frontend

**User Story:** As an Admin, I want a Follow-Up Queue section in the Leads tab with one-click actions, so that I can efficiently process leads that need human attention.

#### Acceptance Criteria

1. THE Leads_Dashboard SHALL display a Follow-Up Queue section as a collapsible panel above the main leads table
2. THE Follow-Up Queue section SHALL display each lead with: name, phone, situation, time since created (formatted as hours or days), and urgency indicator (yellow for 2-12 hours, red for 12+ hours)
3. THE Follow-Up Queue section SHALL display one-click action buttons on each lead: "Move to Schedule" (re-tags intake_tag to SCHEDULE), "Mark Lost" (sets status to LOST), and "Add Notes" (opens notes editor)
4. WHEN the Admin clicks "Move to Schedule", THE Leads_Dashboard SHALL call PATCH /api/v1/leads/{id} with intake_tag=SCHEDULE and refresh the Follow-Up Queue
5. THE Follow-Up Queue section SHALL use the data-testid convention: `follow-up-queue` for the container, `follow-up-lead-{id}` for each lead row

### Requirement 52: Work Request Auto-Promotion Enhancement

**User Story:** As an Admin, I want all work request submissions auto-promoted to leads regardless of client type, so that every inbound service request enters the lead tracking pipeline for consistent follow-up.

#### Acceptance Criteria

1. WHEN a work request is synced from Google Sheets, THE Lead_Service SHALL create a Lead record for the submission regardless of whether the client_type is "new" or "existing"
2. WHEN a work request from an existing client is auto-promoted to a lead, THE Lead_Service SHALL set lead_source to GOOGLE_FORM and source_detail to "Existing client work request"
3. THE Platform SHALL add a promoted_to_lead_id field (FK to leads, nullable) to the WorkRequest model to track which submissions were auto-promoted
4. THE Platform SHALL add a promoted_at field (TIMESTAMP, nullable) to the WorkRequest model to record when the promotion occurred
5. WHEN a work request is auto-promoted, THE Lead_Service SHALL set the promoted_to_lead_id and promoted_at fields on the WorkRequest record

### Requirement 53: Work Request Audit Trail — Frontend

**User Story:** As an Admin, I want the Work Requests tab to show which submissions were auto-promoted to leads, so that I can use it as a sync log and audit trail.

#### Acceptance Criteria

1. THE Platform SHALL display a "Promoted to Lead" badge on work request rows that have a non-null promoted_to_lead_id
2. THE Platform SHALL display the promoted_to_lead_id as a clickable link navigating to the corresponding lead detail view
3. THE Platform SHALL display the promoted_at timestamp on work request rows that were auto-promoted

### Requirement 54: Lead Submission Confirmation — SMS

**User Story:** As an Admin, I want the system to send an SMS confirmation after a lead is created from any source, so that customers know their request was received and can expect a response.

#### Acceptance Criteria

1. WHEN a Lead is created and the lead has a phone number and sms_consent is true, THE Lead_Service SHALL send an SMS confirmation via the SMS service (Twilio) with the message: "Hi {name}! Your request has been received by Grins Irrigation. We'll be in touch within 2 hours during business hours."
2. THE Platform SHALL add a LEAD_CONFIRMATION value to the MessageType enum for tracking lead confirmation messages
3. WHEN sending an SMS lead confirmation, THE Lead_Service SHALL verify sms_consent is true before sending, per TCPA compliance requirements
4. IF sms_consent is false or the lead has no phone number, THEN THE Lead_Service SHALL skip SMS confirmation and log the skip reason using structured logging

### Requirement 55: Lead Submission Confirmation — Email

**User Story:** As an Admin, I want the system to send an email confirmation after a lead is created when an email is provided, so that customers receive written acknowledgment of their request.

#### Acceptance Criteria

1. WHEN a Lead is created and the lead has an email address, THE Lead_Service SHALL send an email confirmation with subject "Your request has been received — Grins Irrigation" and body confirming receipt and expected response time
2. THE Lead_Service SHALL use the LEAD_CONFIRMATION MessageType when recording the email confirmation
3. IF the lead has no email address, THEN THE Lead_Service SHALL skip email confirmation and log the skip reason using structured logging

### Requirement 56: Lead Consent Fields — Model Extensions

**User Story:** As an Admin, I want each lead to track SMS consent and terms acceptance, so that consent status is visible from the moment of lead creation and carries over when a lead converts to a customer.

#### Acceptance Criteria

1. THE Platform SHALL add an sms_consent field (BOOLEAN, default false) to the Lead model
2. THE Platform SHALL add a terms_accepted field (BOOLEAN, default false) to the Lead model
3. THE Platform SHALL apply a database migration that sets sms_consent and terms_accepted to false for all existing Lead records

### Requirement 57: Lead Consent Fields — API Extensions

**User Story:** As an Admin, I want to capture and view consent status on leads, so that the system respects consent preferences from the earliest point of contact.

#### Acceptance Criteria

1. WHEN a POST /api/v1/leads request includes optional sms_consent and terms_accepted fields, THE Lead_Service SHALL store the provided values on the new Lead record
2. WHEN a Lead with sms_consent=true converts to a Customer, THE Lead_Service SHALL carry the sms_consent value to the Customer record and create an sms_consent_record entry with consent_method="lead_form" and the lead's phone number
3. WHEN a Lead with terms_accepted=true converts to a Customer, THE Lead_Service SHALL carry the terms_accepted value and set terms_accepted_at on the Customer record

### Requirement 58: Lead Consent Fields — Frontend

**User Story:** As an Admin, I want to see consent indicators on the Leads tab, so that I can quickly identify which leads have opted in to SMS and accepted terms.

#### Acceptance Criteria

1. THE Leads_Dashboard SHALL display consent indicators on each lead row: an SMS icon (green checkmark for sms_consent=true, gray dash for false) and a Terms icon (green checkmark for terms_accepted=true, gray dash for false)
2. THE Lead Detail view SHALL display the full consent status: sms_consent value and terms_accepted value
3. THE consent indicators SHALL use the data-testid convention: `sms-consent-{id}` and `terms-accepted-{id}`

### Requirement 59: Dashboard Widgets — Leads Awaiting Contact

**User Story:** As an Admin, I want a dashboard widget showing leads awaiting first contact with urgency indicators, so that I can prioritize outreach to new leads.

#### Acceptance Criteria

1. THE Platform SHALL add a "Leads Awaiting Contact" widget to the Dashboard tab showing the count of leads with status NEW
2. THE "Leads Awaiting Contact" widget SHALL display the time since the oldest NEW lead was created as an urgency indicator
3. THE "Leads Awaiting Contact" widget SHALL link to the Leads tab filtered by status=NEW when clicked
4. THE widget SHALL use the data-testid: `widget-leads-awaiting-contact`

### Requirement 60: Dashboard Widgets — Follow-Up Queue

**User Story:** As an Admin, I want a dashboard widget showing the follow-up queue count, so that I can see at a glance how many leads need human review.

#### Acceptance Criteria

1. THE Platform SHALL add a "Follow-Up Queue" widget to the Dashboard tab showing the count of leads WHERE intake_tag equals FOLLOW_UP AND status is one of NEW, CONTACTED, or QUALIFIED
2. THE "Follow-Up Queue" widget SHALL link to the Leads tab Follow-Up Queue section when clicked
3. THE widget SHALL use the data-testid: `widget-follow-up-queue`

### Requirement 61: Dashboard Widgets — Leads by Source

**User Story:** As an Admin, I want a dashboard chart showing lead distribution by source channel, so that I can evaluate which marketing channels are generating the most leads.

#### Acceptance Criteria

1. THE Platform SHALL add a "Leads by Source" chart widget to the Dashboard tab displaying a pie or bar chart of lead counts grouped by lead_source
2. THE "Leads by Source" chart SHALL include all leads created within the trailing 30 days
3. THE Platform SHALL expose a GET /api/v1/leads/metrics/by-source endpoint that returns lead counts grouped by lead_source for a configurable date range (default trailing 30 days)
4. THE widget SHALL use the data-testid: `widget-leads-by-source`

### Requirement 62: Dashboard Summary Extension — Lead Metrics

**User Story:** As an Admin, I want the main dashboard summary to include lead metrics alongside existing KPIs, so that I see the full pipeline health at a glance.

#### Acceptance Criteria

1. THE Platform SHALL extend the GET /api/v1/dashboard/summary response to include: new leads count (status NEW), follow-up queue count (intake_tag FOLLOW_UP with active statuses), and leads awaiting contact oldest age (hours since the oldest NEW lead was created)

### Requirement 63: Leads and Work Requests — Backend Testing

**User Story:** As a Developer, I want comprehensive backend test coverage for all leads and work requests enhancements, so that source tracking, intake tagging, follow-up queue, auto-promotion, confirmations, and consent fields are verified to work correctly.

#### Acceptance Criteria

1. THE Platform SHALL include unit tests (`@pytest.mark.unit`) with mocked dependencies for: Lead_Service lead creation with all LeadSource values, Lead_Service intake tag defaulting logic (SCHEDULE for website, NULL for from-call), Lead_Service follow-up queue filtering and sorting, Lead_Service work request auto-promotion for both new and existing clients, Lead_Service SMS confirmation with sms_consent gating, Lead_Service email confirmation with email presence check, and Lead_Service consent field carry-over during lead-to-customer conversion
2. THE Platform SHALL include functional tests (`@pytest.mark.functional`) with a real database for: lead creation with source and intake tag persisted correctly, follow-up queue endpoint returning correct filtered and sorted results, work request auto-promotion creating linked lead records, PATCH lead intake_tag changing tag and updating follow-up queue membership, and lead consent fields carrying over to customer on conversion
3. THE Platform SHALL include integration tests (`@pytest.mark.integration`) for: GET /api/v1/leads with lead_source multi-select filter, GET /api/v1/leads with intake_tag filter, POST /api/v1/leads/from-call endpoint with authentication, GET /api/v1/leads/follow-up-queue endpoint with pagination, GET /api/v1/leads/metrics/by-source endpoint with date range, and GET /api/v1/dashboard/summary including lead metrics
4. ALL leads and work requests backend tests SHALL pass with zero failures before the feature is considered complete

### Requirement 64: Leads and Work Requests — Frontend Testing

**User Story:** As a Developer, I want comprehensive frontend test coverage for all new and modified leads UI components, so that the Leads tab enhancements render correctly and interactive elements function as expected.

#### Acceptance Criteria

1. THE Platform SHALL include Vitest + React Testing Library component tests for: LeadSourceBadge (renders correct color per source), IntakeTagBadge (renders green for SCHEDULE, orange for FOLLOW_UP, gray for untagged), Follow-Up Queue section (renders leads sorted by age, urgency indicators, one-click actions), Leads table with source filter dropdown and intake tag quick-filter tabs, Work Requests tab with promoted-to-lead badges and links, Lead Detail view with source_detail and consent indicators, and Dashboard widgets (Leads Awaiting Contact, Follow-Up Queue, Leads by Source chart)
2. ALL leads and work requests frontend tests SHALL pass with zero failures before the feature is considered complete

### Requirement 65: Deployment Verification — Railway, Vercel, and End-to-End Validation

**User Story:** As an Admin, I want automated deployment verification for both the Railway backend and Vercel frontend, so that the feature is confirmed fully operational in production before it is considered complete.

#### Acceptance Criteria

1. WHEN the backend is deployed to Railway, THE Platform SHALL verify via CLI that all Alembic migrations have run successfully and the database schema matches the expected state (all new tables: service_agreement_tiers, service_agreements, agreement_status_logs, stripe_webhook_events, disclosure_records, sms_consent_records exist with correct columns)
2. WHEN the backend is deployed to Railway, THE Platform SHALL verify via CLI that the 6 ServiceAgreementTier seed records are present in the database with correct names, prices, and included_services definitions
3. WHEN the backend is deployed to Railway, THE Platform SHALL verify via CLI that all required environment variables are configured: DATABASE_URL, REDIS_URL, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PUBLISHABLE_KEY, EMAIL_API_KEY, and any feature-specific variables (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN where applicable)
4. WHEN the backend is deployed to Railway, THE Platform SHALL verify via CLI that the /api/v1/health endpoint returns HTTP 200 with database and Redis connectivity confirmed
5. WHEN the frontend is deployed to Vercel, THE Platform SHALL verify via CLI that the deployment status is "Ready" and the production URL is accessible
6. WHEN the frontend is deployed to Vercel, THE Platform SHALL verify via CLI that all required environment variables are configured: VITE_API_BASE_URL (pointing to the Railway backend URL), VITE_STRIPE_PUBLISHABLE_KEY, and any feature-specific frontend variables
7. WHEN the frontend is deployed to Vercel, THE Platform SHALL use agent-browser to open the production Vercel URL and confirm the application loads without errors (no blank page, no console errors, navigation renders)
8. WHEN the frontend is deployed, THE Platform SHALL use agent-browser to navigate to the Service Agreements tab and confirm the agreements table renders with data sourced from the Railway-hosted database
9. WHEN the frontend is deployed, THE Platform SHALL use agent-browser to navigate to the Leads tab and confirm the leads table, source filters, intake tag filters, and Follow-Up Queue section render correctly
10. WHEN the frontend is deployed, THE Platform SHALL use agent-browser to navigate to the Dashboard tab and confirm that subscription metrics (MRR, active agreements, renewal pipeline count) and lead metrics (follow-up queue count, leads by source) display with data from the backend
11. IF any deployment verification check fails, THEN THE Platform SHALL report the specific failure (missing table, missing seed data, missing environment variable, unreachable endpoint, or UI rendering error) with actionable remediation steps
12. ALL deployment verification checks for Railway and Vercel SHALL pass with zero failures before the service-package-purchases feature is considered complete

### Requirement 66: Deployment Instructions Document

**User Story:** As a Developer, I want a comprehensive deployment instructions document auto-generated from the implemented code, so that I have a single reference for deploying the service-package-purchases feature with all actual migration names, environment variables, table names, and configuration steps.

#### Acceptance Criteria

1. WHEN all implementation tasks for the service-package-purchases feature are complete, THE Platform SHALL generate a deployment instructions document at `deployment-instructions/service-package-purchases.md` in the repository root
2. THE deployment instructions document SHALL include a "Database Changes" section listing every new SQLAlchemy model table name, every Alembic migration file name (extracted from `src/grins_platform/migrations/versions/`), the execution order of migrations, and any seed data commands required (including the 6 ServiceAgreementTier seed records)
3. THE deployment instructions document SHALL include an "Environment Variables" section listing every new environment variable required on Railway (backend) and Vercel (frontend), with the variable name, description, example value, and whether the variable is required or optional
4. THE deployment instructions document SHALL include a "New Dependencies" section listing every Python package added to `pyproject.toml` and every npm package added to `frontend/package.json` during this feature, with version constraints
5. THE deployment instructions document SHALL include a "Stripe Configuration" section documenting: webhook endpoint URL and events to subscribe to, Stripe product and price creation steps for the 6 ServiceAgreementTier records, customer portal configuration for click-to-cancel compliance, the `invoice.upcoming` webhook timing configuration (30 days before renewal), and Stripe Tax configuration (enable Stripe Tax, add MN tax registration with MN Tax ID, set tax behavior to "exclusive" on all Prices)
6. THE deployment instructions document SHALL include an "Infrastructure Changes" section documenting APScheduler setup with PostgreSQL job store, all registered background jobs (escalate_failed_payments, check_upcoming_renewals, send_annual_notices, cleanup_orphaned_consent_records) with their schedules, email service configuration (API key, sending domain, SPF/DKIM/DMARC DNS records), and any Redis configuration changes
7. THE deployment instructions document SHALL include a "Deployment Order" section specifying the required sequence of deployment steps (backend migrations first, seed data, backend deploy, frontend deploy) with explicit instructions for each step
8. THE deployment instructions document SHALL include a "Post-Deployment Verification" section referencing Requirement 65's acceptance criteria and providing the specific CLI commands and agent-browser scripts to execute each verification check
9. THE deployment instructions document SHALL include a "Rollback Instructions" section documenting how to revert each deployment step: Alembic downgrade commands for each migration in reverse order, environment variable removal list, Stripe webhook deactivation steps, APScheduler job removal, and frontend redeployment to the previous version
10. THE deployment instructions document SHALL extract all table names, migration file names, environment variable names, dependency versions, and Stripe event types from the actual implemented source code rather than using placeholder values
11. IF the deployment instructions document references a migration, table, environment variable, or dependency that does not exist in the implemented code, THEN THE document generation process SHALL flag the discrepancy as a warning in the document

### Requirement 67: CAN-SPAM Email Compliance Infrastructure

**User Story:** As an Admin, I want the email service to enforce CAN-SPAM compliance for any commercial or marketing emails, so that the business avoids penalties (up to $53,088 per violating email) and maintains customer trust when sending promotional content alongside transactional compliance emails.

#### Acceptance Criteria

1. THE Email_Service SHALL classify every outbound email as either TRANSACTIONAL (appointment confirmations, invoices, receipts, subscription confirmations, renewal notices without promotional content, onboarding reminders, failed payment notices) or COMMERCIAL (seasonal reminders, promotional offers, review requests, renewal notices with upsell content, newsletters), and apply CAN-SPAM requirements only to COMMERCIAL emails
2. THE Email_Service SHALL use separate sender identities for transactional emails (noreply@grinsirrigation.com) and commercial emails (info@grinsirrigation.com or marketing@grinsirrigation.com) to protect transactional email deliverability from commercial opt-out issues
3. THE Email_Service SHALL inject the following into every COMMERCIAL email template: the company physical postal address (configurable via COMPANY_PHYSICAL_ADDRESS environment variable), a working unsubscribe link (single-click, no login required, functional for at least 30 days after send), identification as an advertisement/promotional email, and accurate "From" header identifying Grin's Irrigation
4. THE Platform SHALL expose a GET /api/v1/email/unsubscribe endpoint (public, no auth) that accepts a signed token parameter, decodes it to identify the customer, sets customer.email_opt_in to false, records email_opt_out_at timestamp, adds the email to a permanent suppression list, and renders a confirmation page stating "You've been unsubscribed from marketing emails. You'll still receive transactional emails (invoices, appointment confirmations)."
5. THE Email_Service SHALL check the suppression list and customer.email_opt_in status before sending any COMMERCIAL email, and skip sending with a structured log entry if the recipient is suppressed or opted out
6. THE Email_Service SHALL generate signed, time-limited unsubscribe tokens via a generate_unsubscribe_token(customer_id, email) method, with tokens remaining valid for at least 30 days per CAN-SPAM requirements
7. THE Platform SHALL store email suppression list entries permanently (no expiration) — once a customer unsubscribes from commercial emails, their email address SHALL never receive commercial emails again unless they explicitly re-subscribe
8. THE Platform SHALL honor email opt-out requests within 10 business days of receipt, with a target of same-day automatic processing
9. THE Platform SHALL retain email consent records (opt-in date, method, source), campaign archives (copy of each email sent), and send logs (recipient, date, subject, email type) for a minimum of 5 years, and email suppression/opt-out lists permanently
10. IF the COMPANY_PHYSICAL_ADDRESS environment variable is not configured, THEN THE Email_Service SHALL refuse to send COMMERCIAL emails and log a critical warning indicating that CAN-SPAM compliance cannot be met without a physical address

### Requirement 68: Customer Email Consent Tracking — Model Extensions

**User Story:** As an Admin, I want customer records to track email marketing consent status with timestamps and audit trail, so that the system can enforce CAN-SPAM opt-out requirements and provide defensible proof of consent status.

#### Acceptance Criteria

1. THE Platform SHALL add the following fields to the Customer model: email_opt_in_at (TIMESTAMP, nullable — when email marketing consent was given), email_opt_out_at (TIMESTAMP, nullable — when the customer unsubscribed from marketing emails), and email_opt_in_source (VARCHAR(50), nullable — "web_form", "lead_form", "stripe_checkout", "verbal", "import")
2. WHEN a Customer record is created from a checkout.session.completed webhook, THE Webhook_Handler SHALL set email_opt_in to true, email_opt_in_at to the current timestamp, and email_opt_in_source to "stripe_checkout" (since completing a purchase implies a service relationship)
3. WHEN a Lead with an email address converts to a Customer, THE Lead_Service SHALL carry the email consent status to the Customer record and set email_opt_in_at and email_opt_in_source accordingly
4. THE Platform SHALL apply a database migration that sets email_opt_in_at to NULL and email_opt_out_at to NULL for all existing Customer records (preserving the existing email_opt_in boolean value)

### Requirement 69: ADA / Accessibility Compliance for Purchase Flow

**User Story:** As an Admin, I want all customer-facing pages in the purchase flow (pre-checkout modal, post-purchase onboarding form) to meet WCAG 2.2 Level AA accessibility standards, so that the business minimizes legal risk from ADA web accessibility lawsuits and ensures all customers can complete the purchase process.

#### Acceptance Criteria

1. THE Platform SHALL ensure that the pre-checkout consent modal uses proper semantic HTML: heading hierarchy (h1 > h2 > h3 with no skipped levels), landmark roles (dialog role on the modal), all form inputs associated with visible labels (not placeholder-only), required fields marked with aria-required="true" and a visual indicator, and form validation errors announced via ARIA live regions
2. THE Platform SHALL ensure that the pre-checkout consent modal is fully keyboard navigable: focus is trapped within the modal while open, the modal can be closed with the Escape key, Tab order follows the visual/logical order, and all interactive elements (checkboxes, buttons, links) have visible focus indicators
3. THE Platform SHALL ensure that the post-purchase onboarding form meets the same semantic HTML and keyboard navigation standards as the pre-checkout modal (AC1 and AC2)
4. THE Platform SHALL ensure that all customer-facing pages in the purchase flow meet WCAG 2.2 Level AA color contrast requirements: 4.5:1 minimum contrast ratio for normal text, 3:1 for large text (18px+ or 14px+ bold), and color is never the sole indicator of status or information (icons or text labels accompany color indicators)
5. THE Platform SHALL ensure that all interactive elements in the purchase flow have minimum touch targets of 44x44 pixels for mobile accessibility
6. THE Platform SHALL ensure that the "Continue to Checkout" button in the pre-checkout modal uses a descriptive accessible label (e.g., "Continue to Checkout — [tier_name] Plan, $[price]/year") rather than a generic label, and announces its disabled state to screen readers when consent checkboxes are not checked
7. THE Platform SHALL ensure that the Stripe Customer Portal link included in compliance emails and the agreement detail view opens in a way that is announced to screen readers (e.g., via aria-label indicating "Opens in new tab" or equivalent)
8. THE Platform SHALL document that before launch, the following accessibility validation steps must be completed: run WAVE accessibility checker on the pre-checkout modal and post-purchase onboarding form, complete a keyboard-only navigation test of the full purchase flow, and test with VoiceOver (macOS) or a comparable screen reader
9. THE Platform SHALL include agent-browser validation scripts that verify accessibility basics: all form inputs have associated labels (no orphaned inputs), all images have alt attributes, focus is visible on interactive elements, and the modal traps focus correctly

### Requirement 70: Compliance Email Content — No Promotional Mixing

**User Story:** As an Admin, I want the system to enforce strict separation between transactional/compliance emails and promotional content, so that compliance emails (MN auto-renewal notices, TCPA-related confirmations) are never reclassified as commercial emails due to mixed promotional content, which would trigger additional CAN-SPAM requirements and risk deliverability issues.

#### Acceptance Criteria

1. THE Email_Service SHALL enforce that compliance email templates (CONFIRMATION, RENEWAL_NOTICE, ANNUAL_NOTICE, CANCELLATION_CONF) contain zero promotional content — no upsell offers, no discount codes, no "upgrade your plan" calls to action, and no links to promotional landing pages
2. THE Email_Service SHALL use the transactional sender identity (noreply@grinsirrigation.com) for all compliance emails, never the commercial sender identity
3. THE Email_Service SHALL NOT include an unsubscribe link in compliance/transactional emails, since these are legally required communications that customers cannot opt out of receiving (though a "Manage your subscription" link to the Stripe Customer Portal is permitted as it facilitates the service relationship)
4. IF a future requirement requests adding promotional content to a compliance email template, THE Platform SHALL instead send the promotional content as a separate COMMERCIAL email with full CAN-SPAM compliance (unsubscribe link, physical address, ad identification), preserving the transactional classification of the compliance email
