# Requirements Document — Backend-Frontend Integration Gaps

## Introduction

This spec addresses 11 gaps identified between the existing `service-package-purchases` backend spec and the Phase One Frontend spec. These gaps span TCPA/compliance fixes, missing model fields, pricing surcharge logic, new tiers, duplicate detection, SMS opt-out processing, time-window enforcement, onboarding reminders, and a consent language version registry. Gaps 7 (AI chat — separate spec), 12 (legal entity name — manual verification), and 13 (physical address — manual action) are excluded.

The existing backend has partial implementations for Gaps 1, 3, and 4. The remaining 8 gaps are completely unimplemented. All changes target the FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL backend in the `grins_platform` package.

## Glossary

- **Platform**: The Grins Irrigation Platform backend (FastAPI + PostgreSQL)
- **Compliance_Service**: The backend service responsible for pre-checkout consent processing, disclosure records, and SMS consent records
- **Checkout_Service**: The backend service responsible for creating Stripe Checkout Sessions with consent tokens, tier validation, and pricing
- **Lead_Service**: The backend service responsible for lead creation, validation, source tracking, and lead-to-customer conversion
- **SMS_Service**: The backend service responsible for sending SMS messages, checking consent status, and enforcing time-window restrictions
- **Job_Generator**: The backend component that creates seasonal Job records based on a ServiceAgreementTier's included_services definition
- **Webhook_Handler**: The backend component that receives and processes Stripe webhook events
- **Onboarding_Reminder_Job**: A daily background job that queries incomplete onboarding records and sends automated reminders
- **Surcharge_Calculator**: A utility component that computes zone count and lake pump surcharges based on tier type and package type
- **ServiceAgreement**: An instance record representing a specific customer's active subscription, linked to a tier, customer, and property
- **ServiceAgreementTier**: A template record defining a package (name, price, included services, perks, Stripe IDs)
- **SmsConsentRecord**: An immutable audit log entry tracking SMS consent given or revoked, per TCPA requirements
- **ConsentLanguageVersion**: A reference record mapping a version identifier to the exact TCPA disclosure text shown to the customer
- **Lead**: A prospect record from a website form submission, tracked independently until conversion to a Customer
- **Consent_Token**: A UUID generated during pre-checkout consent that links orphaned consent and disclosure records to the Customer created after Stripe payment
- **TCPA**: Telephone Consumer Protection Act — federal law governing SMS consent, opt-out processing, and time-window restrictions
- **Central_Time**: US Central Time zone (America/Chicago), used for SMS time-window enforcement since all customers are in Minnesota

## Requirements

### Requirement 1: Fix SMS Consent Validation in Pre-Checkout Flow (TCPA Compliance)

**User Story:** As a customer, I want to complete a service package purchase without being forced to consent to SMS messages, so that my purchase is not conditioned on SMS consent as required by TCPA.

#### Acceptance Criteria

1. WHEN a pre-checkout consent request is received, THE Compliance_Service SHALL validate that `terms_accepted` is `true` before proceeding, and return HTTP 422 if `terms_accepted` is `false`
2. WHEN a pre-checkout consent request is received with `sms_consent` set to `false`, THE Compliance_Service SHALL accept the request without returning an error and proceed with checkout flow
3. WHEN a pre-checkout consent request is received with `sms_consent` set to `false`, THE Compliance_Service SHALL create an SmsConsentRecord with `consent_given` set to `false` to document the customer's declination for compliance audit
4. WHEN a pre-checkout consent request is received with `sms_consent` set to `true`, THE Compliance_Service SHALL create an SmsConsentRecord with `consent_given` set to `true` as in the current behavior

### Requirement 2: Add email_marketing_consent to Lead Model and Pre-Checkout Endpoint

**User Story:** As a customer, I want to opt in or out of email marketing when submitting a lead form or purchasing a service package, so that my email preferences are respected from first contact.

#### Acceptance Criteria

1. THE Platform SHALL add an `email_marketing_consent` field (BOOLEAN, default `false`) to the Lead model via database migration, setting `false` for all existing lead records
2. WHEN a lead creation request is received on `POST /api/v1/leads`, THE Lead_Service SHALL accept an optional `email_marketing_consent` field and store the value on the Lead record
3. WHEN a Lead with `email_marketing_consent` set to `true` converts to a Customer, THE Lead_Service SHALL set the Customer's `email_opt_in` field to `true`, `email_opt_in_at` to the conversion timestamp, and `email_opt_in_source` to `"lead_form"`
4. THE Platform SHALL add an optional `email_marketing_consent` field (boolean, default `false`) to the `POST /api/v1/onboarding/pre-checkout-consent` request schema
5. WHEN a `checkout.session.completed` event is received with `email_marketing_consent` stored in the Stripe session metadata via the consent_token linkage, THE Webhook_Handler SHALL carry the value to the Customer's `email_opt_in` field

### Requirement 3: Zone Count and Lake Pump Surcharges in Checkout Session

**User Story:** As a customer, I want my zone count and lake pump selection reflected in my checkout total, so that I pay the correct price for my property's irrigation system configuration.

#### Acceptance Criteria

1. THE Checkout_Service SHALL accept `zone_count` (integer, required, minimum 1) and `has_lake_pump` (boolean, default `false`) on the create-session endpoint request schema
2. WHEN `zone_count` is 10 or greater for a Residential tier, THE Surcharge_Calculator SHALL compute a zone surcharge of $7.50 multiplied by (`zone_count` minus 9) and add the surcharge to the base tier price
3. WHEN `zone_count` is 10 or greater for a Commercial tier, THE Surcharge_Calculator SHALL compute a zone surcharge of $10.00 multiplied by (`zone_count` minus 9) and add the surcharge to the base tier price
4. WHEN `has_lake_pump` is `true` for a Residential tier, THE Surcharge_Calculator SHALL add a lake pump surcharge of $175.00 to the price
5. WHEN `has_lake_pump` is `true` for a Commercial tier, THE Surcharge_Calculator SHALL add a lake pump surcharge of $200.00 to the price
6. WHEN `zone_count` is 10 or greater for a Winterization-Only Residential tier, THE Surcharge_Calculator SHALL compute a zone surcharge of $5.00 multiplied by (`zone_count` minus 9)
7. WHEN `zone_count` is 10 or greater for a Winterization-Only Commercial tier, THE Surcharge_Calculator SHALL compute a zone surcharge of $10.00 multiplied by (`zone_count` minus 9)
8. WHEN `has_lake_pump` is `true` for a Winterization-Only Residential tier, THE Surcharge_Calculator SHALL add a lake pump surcharge of $75.00
9. WHEN `has_lake_pump` is `true` for a Winterization-Only Commercial tier, THE Surcharge_Calculator SHALL add a lake pump surcharge of $100.00
10. WHEN `zone_count` is less than 10, THE Surcharge_Calculator SHALL apply zero zone surcharge regardless of tier type
11. THE Checkout_Service SHALL create the Stripe Checkout Session with separate line items for the base tier price and each applicable surcharge (zone surcharge, lake pump surcharge) so that the customer receipt is transparent
12. THE Checkout_Service SHALL store `zone_count` and `has_lake_pump` in the Stripe session metadata and subscription metadata
13. THE Platform SHALL add `zone_count` (INTEGER, nullable), `has_lake_pump` (BOOLEAN, default `false`), and `base_price` (DECIMAL(10,2), nullable) fields to the ServiceAgreement model via database migration
14. WHEN a `checkout.session.completed` event is received, THE Webhook_Handler SHALL populate `zone_count`, `has_lake_pump`, and `base_price` on the ServiceAgreement from the Stripe session metadata, where `base_price` is the tier's base price before surcharges and `annual_price` is the total including surcharges

### Requirement 4: Winterization-Only Tier

**User Story:** As a customer, I want to purchase a winterization-only service package, so that I can get my irrigation system winterized without committing to a full-season plan.

#### Acceptance Criteria

1. THE Platform SHALL seed 2 new ServiceAgreementTier records via database migration: "Winterization Only Residential" (slug `winterization-only-residential`, package_type `RESIDENTIAL`, annual_price $80.00, included_services containing one "Fall Winterization" entry with frequency 1) and "Winterization Only Commercial" (slug `winterization-only-commercial`, package_type `COMMERCIAL`, annual_price $100.00, included_services containing one "Fall Winterization" entry with frequency 1)
2. WHEN generating jobs for a Winterization-Only tier agreement, THE Job_Generator SHALL create 1 job: "Fall Winterization" with target_start_date October 1 and target_end_date October 31
3. THE Platform SHALL create Stripe Products and Prices for both Winterization-Only tiers, with `stripe_product_id` and `stripe_price_id` fields populated via environment-specific configuration
4. THE Checkout_Service SHALL recognize Winterization-Only tier slugs and apply the Winterization-Only surcharge rates when calculating zone count and lake pump surcharges

### Requirement 5: Add page_url Field to Lead Model

**User Story:** As an admin, I want to know which page a lead submitted from, so that I can track which landing pages generate the most leads.

#### Acceptance Criteria

1. THE Platform SHALL add a `page_url` field (VARCHAR(2048), nullable) to the Lead model via database migration, setting `NULL` for all existing lead records
2. WHEN a lead creation request is received on `POST /api/v1/leads`, THE Lead_Service SHALL accept an optional `page_url` field and store the value on the Lead record

### Requirement 6: Duplicate Lead Detection

**User Story:** As a customer, I want to receive a friendly message if I accidentally submit the lead form twice, so that I know my original request was already received.

#### Acceptance Criteria

1. WHEN a lead creation request is received with a `phone` number that matches an existing Lead record created within the previous 24 hours, THE Lead_Service SHALL detect the submission as a duplicate
2. WHEN a lead creation request is received with an `email` address that matches an existing Lead record created within the previous 24 hours, THE Lead_Service SHALL detect the submission as a duplicate
3. WHEN a duplicate lead is detected, THE Lead_Service SHALL return HTTP 409 with a response body containing `"detail": "duplicate_lead"` and a `"message"` field with a human-readable explanation
4. WHEN a duplicate lead is detected, THE Lead_Service SHALL not create a new Lead record

### Requirement 7: Create SmsConsentRecord at Lead Form Submission

**User Story:** As a platform operator, I want SMS consent documented at the moment it is given on the lead form, so that the consent audit trail exists even if the lead never converts to a customer.

#### Acceptance Criteria

1. WHEN a lead is created on `POST /api/v1/leads`, THE Lead_Service SHALL immediately create an SmsConsentRecord with `consent_given` set to the lead's `sms_consent` value, `consent_method` set to `"lead_form"`, and `customer_id` set to NULL
2. THE Platform SHALL add a `lead_id` foreign key (UUID, nullable, references leads.id) to the SmsConsentRecord model via database migration
3. WHEN an SmsConsentRecord is created at lead submission, THE Lead_Service SHALL set the `lead_id` field to the newly created Lead's ID
4. WHEN a lead creation request includes `consent_ip`, `consent_user_agent`, and `consent_language_version` fields, THE Lead_Service SHALL store these values on the SmsConsentRecord as `consent_ip_address`, `consent_user_agent`, and `consent_form_version` respectively
5. WHEN a Lead with an associated SmsConsentRecord converts to a Customer, THE Lead_Service SHALL update the existing SmsConsentRecord's `customer_id` to the new Customer's ID rather than creating a duplicate record

### Requirement 8: STOP Keyword Processing in Inbound SMS

**User Story:** As a customer, I want to text STOP to opt out of SMS messages, so that I can revoke my consent at any time as guaranteed by TCPA.

#### Acceptance Criteria

1. WHEN an inbound SMS message contains one of the keywords STOP, QUIT, CANCEL, UNSUBSCRIBE, END, or REVOKE (case-insensitive, as the entire message body or as a standalone word), THE SMS_Service SHALL process the message as an opt-out request
2. WHEN an opt-out request is processed, THE SMS_Service SHALL create a new SmsConsentRecord with `consent_given` set to `false`, `opt_out_timestamp` set to the current timestamp, `opt_out_method` set to `"text_stop"`, and the customer's phone number
3. WHEN an opt-out request is processed, THE SMS_Service SHALL send exactly one confirmation SMS to the customer: "You've been unsubscribed from Grins Irrigation texts. Reply START to re-subscribe."
4. WHEN an opt-out confirmation is sent, THE SMS_Service SHALL set `opt_out_confirmation_sent` to `true` on the SmsConsentRecord
5. WHEN an inbound SMS message contains informal opt-out language (phrases such as "stop texting me", "take me off the list", "no more texts") but does not contain an exact keyword match, THE SMS_Service SHALL flag the message for admin review rather than auto-processing the opt-out
6. WHEN the SMS_Service is about to send any automated SMS message, THE SMS_Service SHALL check the most recent SmsConsentRecord for the recipient's phone number and skip sending if `consent_given` is `false`

### Requirement 9: SMS Time Window Enforcement

**User Story:** As a customer, I want to receive automated SMS messages only during reasonable hours, so that I am not disturbed outside of 8 AM to 9 PM as required by TCPA.

#### Acceptance Criteria

1. WHEN the SMS_Service is about to send an automated SMS message, THE SMS_Service SHALL check the current time in Central Time (America/Chicago timezone)
2. WHEN the current Central Time is before 8:00 AM or after 9:00 PM, THE SMS_Service SHALL queue the message for delivery at 8:00 AM Central Time the next day instead of sending immediately
3. WHEN a message is deferred due to the time window restriction, THE SMS_Service SHALL log the deferral with structured logging including the original send time, the scheduled delivery time, and the recipient phone number
4. THE SMS_Service SHALL apply the time window restriction to all automated SMS messages including lead confirmations, appointment reminders, onboarding reminders, and subscription notifications
5. THE SMS_Service SHALL not apply the time window restriction to admin-initiated manual messages

### Requirement 10: Onboarding Incomplete Automated Reminders

**User Story:** As an admin, I want customers who purchased a service package but did not complete property onboarding to receive automated reminders, so that onboarding completion rates improve without manual follow-up.

#### Acceptance Criteria

1. THE Platform SHALL run a daily background job (`remind_incomplete_onboarding`) that queries ServiceAgreements with status ACTIVE or PENDING and `property_id` set to NULL
2. WHEN a ServiceAgreement has been without a `property_id` for 24 hours or more after creation and no reminder has been sent, THE Onboarding_Reminder_Job SHALL send an SMS reminder to the customer with a link to the onboarding form, gated on the customer's SMS consent status
3. WHEN a ServiceAgreement has been without a `property_id` for 72 hours or more after creation and only one reminder has been sent, THE Onboarding_Reminder_Job SHALL send a second SMS reminder to the customer
4. WHEN a ServiceAgreement has been without a `property_id` for 7 days or more after creation, THE Onboarding_Reminder_Job SHALL create an admin notification indicating the customer purchased a service package but has not provided property information
5. THE Onboarding_Reminder_Job SHALL log each reminder action using structured logging with the agreement_id, reminder step (24h_sms, 72h_sms, or 7d_admin_alert), and delivery outcome
6. THE Platform SHALL add `onboarding_reminder_sent_at` (TIMESTAMP, nullable) and `onboarding_reminder_count` (INTEGER, default 0) fields to the ServiceAgreement model to track reminder state

### Requirement 11: Consent Language Version Registry

**User Story:** As a platform operator, I want a versioned registry of TCPA consent disclosure text, so that every SMS consent record can be traced back to the exact language the customer was shown.

#### Acceptance Criteria

1. THE Platform SHALL create a `consent_language_versions` table with the fields: `id` (UUID, primary key), `version` (VARCHAR(20), unique), `consent_text` (TEXT, not null), `effective_date` (DATE, not null), `deprecated_date` (DATE, nullable), and `created_at` (TIMESTAMP, not null, default NOW())
2. THE Platform SHALL seed an initial record with version `"v1.0"`, the current TCPA-compliant disclosure text, and the effective_date set to the migration date
3. THE Platform SHALL treat the `consent_language_versions` table as append-only: old versions are never deleted, only deprecated by setting `deprecated_date`
4. WHEN an SmsConsentRecord is created with a `consent_form_version` value, THE Compliance_Service SHALL validate that the version exists in the `consent_language_versions` table and is not deprecated
5. IF an SmsConsentRecord references a `consent_form_version` that does not exist in the `consent_language_versions` table, THEN THE Compliance_Service SHALL log a warning and proceed with record creation without blocking the consent flow
