# Phase 1.5 Planning — Backend Gaps for Frontend Integration

This document captures backend changes required in the `Grins_irrigation_platform` repo to support the Phase One Frontend spec in the `Grins_irrigation` repo. These gaps were identified by cross-referencing the `service-package-purchases` spec (Requirements 1–70) against the `phase-one-frontend` spec (Requirements 1–22).

---

## Gap 1: BLOCKER — Fix SMS Consent Validation (TCPA Conflict)

**Current state (Req 30 AC5):** The `pre-checkout-consent` endpoint validates that **both** `sms_consent` and `terms_accepted` are `true` before proceeding, returning HTTP 422 if either is `false`.

**Problem:** TCPA explicitly prohibits making SMS consent a condition of purchase. The frontend spec correctly treats SMS consent as optional in the SubscriptionConfirmModal. Requiring `sms_consent=true` before checkout violates federal law.

**Required change:**
- Modify Req 30 AC5 to: "THE pre-checkout-consent endpoint SHALL validate that `terms_accepted` is `true` before proceeding, and return HTTP 422 if `terms_accepted` is `false`. The `sms_consent` field SHALL be accepted as `true` or `false` without blocking the checkout flow."
- The endpoint still creates an `sms_consent_record` regardless — if `sms_consent=false`, the record documents the customer declined, which is still useful for compliance audit.

**Files affected:** `pre-checkout-consent` endpoint handler, request schema validation.

---

## Gap 2: HIGH — Add `email_marketing_consent` to Lead Model & Pre-Checkout Endpoint

**Current state:**
- Req 56 adds `sms_consent` and `terms_accepted` to the Lead model but **not** `email_marketing_consent`.
- Req 30 (pre-checkout-consent endpoint) accepts `sms_consent` and `terms_accepted` but **not** `email_marketing_consent`.
- Req 68 adds `email_opt_in` to the Customer model, but there's no corresponding Lead field.

**Problem:** The frontend captures `email_marketing_consent` in both the Lead_Form (Req 2B) and the SubscriptionConfirmModal (Req 3). The backend has no field to receive or store it on leads, and doesn't accept it during pre-checkout consent.

**Required changes:**

### Lead Model
- Add `email_marketing_consent` (BOOLEAN, default `false`) to the Lead model.
- Add database migration setting `email_marketing_consent` to `false` for all existing leads.

### Lead API
- Accept optional `email_marketing_consent` on `POST /api/v1/leads`.
- When a Lead with `email_marketing_consent=true` converts to a Customer, carry the value to the Customer's `email_opt_in` field with `email_opt_in_at` and `email_opt_in_source="lead_form"`.

### Pre-Checkout Consent Endpoint
- Add `email_marketing_consent` (boolean, optional, default `false`) to the `POST /api/v1/onboarding/pre-checkout-consent` request schema.
- Store the value and carry it through to the Customer record upon `checkout.session.completed` via the consent_token linkage.

**Files affected:** Lead model, Lead schema, Lead service, pre-checkout-consent endpoint schema/handler, lead-to-customer conversion logic, Alembic migration.

---

## Gap 3: HIGH — Add Zone Count & Lake Pump Surcharges to Checkout Session

**Current state:**
- Req 1 defines `ServiceAgreementTier` with a fixed `annual_price` ($170, $250, $700, etc.).
- Req 31 (`create-session` endpoint) accepts `package_tier`, `package_type`, `consent_token`, and `utm_params` — no `zone_count` or `has_lake_pump`.

**Problem:** The frontend SubscriptionConfirmModal (Req 3) collects zone count and lake pump selection, calculates surcharges in real time, and passes them to `create-session`. But the backend has no way to receive these values or adjust the Stripe Checkout Session price accordingly.

**Required changes:**

### Create-Session Endpoint (Req 31)
- Add `zone_count` (integer, required, minimum 1) and `has_lake_pump` (boolean, default `false`) to the request schema.
- Calculate the final price server-side using the surcharge rules:
  - **Residential zone surcharge:** If `zone_count >= 10`: base + ($7.50 x (zone_count - 9))
  - **Commercial zone surcharge:** If `zone_count >= 10`: base + ($10 x (zone_count - 9))
  - **Residential lake pump:** +$175
  - **Commercial lake pump:** +$200
  - **Winterization-Only residential zone surcharge:** If `zone_count >= 10`: base + ($5 x (zone_count - 9))
  - **Winterization-Only residential lake pump:** +$75
  - **Winterization-Only commercial zone surcharge:** If `zone_count >= 10`: base + ($10 x (zone_count - 9))
  - **Winterization-Only commercial lake pump:** +$100
- Create the Stripe Checkout Session with the calculated total. Options:
  - **Option A (recommended):** Use Stripe line items with a base price + additional surcharge line items (zone surcharge, lake pump surcharge) for transparent receipt.
  - **Option B:** Create a dynamic Stripe Price on the fly with the total amount.
- Store `zone_count` and `has_lake_pump` in the Stripe session metadata and subscription metadata so the webhook handler can record them on the ServiceAgreement.

### ServiceAgreement Model (Req 2)
- Add `zone_count` (INTEGER, nullable) and `has_lake_pump` (BOOLEAN, default `false`) to the ServiceAgreement model.
- The webhook handler (`checkout.session.completed`) should populate these from the session metadata.
- Add `base_price` (DECIMAL, nullable) to differentiate from `annual_price` (which includes surcharges).

**Files affected:** Checkout service, create-session endpoint schema/handler, ServiceAgreement model, webhook handler, Alembic migration, surcharge calculation utility (new).

---

## Gap 4: HIGH — Add Winterization-Only Tier to Backend

**Current state:** Req 1 AC3 seeds 6 tiers: Essential/Professional/Premium x Residential/Commercial. No Winterization-Only tier exists.

**Problem:** The frontend (Req 7 AC4, Req 11 AC5-7) supports a Winterization-Only tier for both residential and commercial with distinct pricing. The backend has no corresponding tier records or job generation logic.

**Required changes:**

### Tier Seed Data
- Add 2 new `ServiceAgreementTier` records:
  - **Winterization Only Residential:** slug `winterization-only-residential`, package_type `RESIDENTIAL`, annual_price $80, included_services: [{ service_type: "Fall Winterization", frequency: 1 }]
  - **Winterization Only Commercial:** slug `winterization-only-commercial`, package_type `COMMERCIAL`, annual_price $100, included_services: [{ service_type: "Fall Winterization", frequency: 1 }]
- Create Stripe Products and Prices for both Winterization-Only tiers.

### Job Generator (Req 9)
- Add Winterization-Only job generation logic: Create **1 job** — "Fall Winterization" with target_start_date October 1 and target_end_date October 31.

### PackageType or Tier Level Enum
- If the tier level enum is used (Essential/Professional/Premium), add `WINTERIZATION_ONLY` as a valid level, or handle Winterization-Only as a special package_tier slug.

**Files affected:** Tier seed migration, Job Generator service, ServiceAgreementTier model (if enum changes needed), Stripe product/price setup documentation.

---

## Gap 5: MEDIUM — Add `page_url` Field to Lead Model

**Current state:** The frontend (Req 17 AC1) sends `page_url` (the URL the lead submitted from) in the Lead_Payload. The backend Lead model does not have a `page_url` field.

**Required changes:**
- Add `page_url` (VARCHAR(2048), nullable) to the Lead model.
- Accept `page_url` on `POST /api/v1/leads`.
- Database migration setting `page_url` to `NULL` for existing records.

**Files affected:** Lead model, Lead schema, Alembic migration.

---

## Gap 6: MEDIUM — Define Duplicate Lead Detection Logic

**Current state:** The frontend (Req 17 AC2) expects the backend to return a specific "duplicate lead" rejection response. The backend spec has no duplicate detection requirement.

**Required changes:**
- Define duplicate detection criteria. Recommended: same `phone` or same `email` submitted within 24 hours.
- When a duplicate is detected on `POST /api/v1/leads`, return HTTP 409 (Conflict) with a response body: `{ "detail": "duplicate_lead", "message": "A lead with this contact information was recently submitted." }`
- The frontend will display a friendly message based on the `duplicate_lead` detail code.
- Do NOT block the request entirely — still return a success-like response that the frontend can handle gracefully, or return 409 with enough info for the frontend to show a friendly message.

**Files affected:** Lead service (create logic), Lead API endpoint, Lead schema (error response).

---

## Gap 7: LOW — AI Chat Endpoint

**Current state:** The frontend (Req 13) references `POST /api/v1/ai/chat-public` for the chatbot AI mode. This endpoint does not appear in the `service-package-purchases` spec.

**Required change:** Confirm whether this endpoint is defined in a separate spec or needs to be added. If it doesn't exist anywhere:
- Add a `POST /api/v1/ai/chat-public` endpoint (public, rate-limited) that accepts a `message` string and returns an AI-generated response.
- This may already be planned or implemented separately — verify before adding.

**Files affected:** TBD pending investigation.

---

## Gap 8: HIGH — Create sms_consent_record at Lead Form Submission Time (Not Just Conversion)

**Current state (Backend Req 57 AC2):** "WHEN a Lead with sms_consent=true converts to a Customer, THE Lead_Service SHALL carry the sms_consent value to the Customer record and create an sms_consent_record entry."

**Automation Blueprint (§5.5.4):** "On submission: create `sms_consent_records` entry with consent_language_shown, IP, user agent, timestamp."

**Problem:** The backend spec only creates the `sms_consent_record` when a lead converts to a customer. But for TCPA defensibility, consent must be documented **at the moment it's given**, not when a business event (conversion) happens later. If a lead never converts, there's no audit record of the consent/refusal. The frontend already sends `consent_ip`, `consent_user_agent`, and `consent_language_version` in the Lead_Payload (Frontend Req 1 AC6).

**Required change:**
- On `POST /api/v1/leads`, immediately create an `sms_consent_record` entry with:
  - `consent_given`: from the lead's `sms_consent` value
  - `consent_method`: `"lead_form"`
  - `consent_language_shown`: the exact TCPA disclosure text version
  - `consent_ip_address`: from the payload's `consent_ip`
  - `consent_user_agent`: from the payload's `consent_user_agent`
  - `customer_id`: NULL (not yet known)
  - `lead_id`: set to the newly created lead's ID (NOTE: the blueprint defines a `lead_id` FK on `sms_consent_records` that is NOT in Backend Req 29 — add this field)
- When the lead later converts to a customer, link the existing record by updating `customer_id`.

**Files affected:** Lead service (submit_lead logic), sms_consent_records model (add `lead_id` FK), Alembic migration.

---

## Gap 9: HIGH — STOP Keyword Processing in Inbound SMS Webhook

**Current state:** The backend `service-package-purchases` spec (Req 29) defines the `sms_consent_record` model with `opt_out_method` and `opt_out_timestamp` fields, but **no requirement exists for actually processing opt-out requests from inbound SMS**.

**Automation Blueprint (§5.5.1):** Extensive STOP keyword processing requirements:
- Honor STOP, QUIT, CANCEL, UNSUBSCRIBE, END, REVOKE keywords
- Detect informal opt-outs ("stop texting me", "take me off the list") — flag for review
- Process within 10 business days (target: same-day automatic)
- Send exactly ONE confirmation text after opt-out
- Scope clarification: "Do you want to stop all messages or just promotions?"

**Problem:** Without STOP keyword processing, there's no way for customers to revoke SMS consent via text, which is a TCPA requirement (must honor any reasonable opt-out method). This is compliance-critical — penalties are $500–$1,500 per message sent after opt-out.

**Required change:**
- Modify the existing inbound SMS webhook (`POST /api/v1/sms/webhook` or equivalent) to:
  1. Check incoming messages for STOP/QUIT/CANCEL/UNSUBSCRIBE/END/REVOKE keywords
  2. On match: create new `sms_consent_record` with `consent_given=false`, `opt_out_timestamp=NOW()`, `opt_out_method="text_stop"`
  3. Send ONE confirmation text: "You've been unsubscribed from Grins Irrigation texts. Reply START to re-subscribe."
  4. Set `opt_out_confirmation_sent=true`
  5. For informal opt-outs (fuzzy match): flag for admin review rather than auto-processing

**Files affected:** SMS webhook handler, SMS service (add consent check before all sends).

---

## Gap 10: HIGH — SMS Time Window Check (8 AM – 9 PM Central)

**Current state:** No time window restriction exists in the backend spec for automated SMS sending.

**Automation Blueprint (§5.5.1, line 795):** "No messages before 8:00 AM or after 9:00 PM recipient's local time (Central for MN)."

**Problem:** TCPA restricts automated messages to 8 AM – 9 PM in the recipient's local time zone. Sending outside this window is a per-message violation.

**Required change:**
- Add a time window check in `SMSService.send_message()` that:
  1. Checks the current time in Central Time (all MN customers)
  2. If outside 8:00 AM – 9:00 PM CT: queue the message for delivery at 8:00 AM CT the next day
  3. Log the deferral with structured logging
- This applies to all automated SMS (lead confirmations, appointment reminders, subscription notifications) — NOT to admin-initiated manual messages.

**Files affected:** SMS service (send_message method), potentially a message queue/scheduler.

---

## Gap 11: MEDIUM — Onboarding Incomplete Automated Reminders

**Current state:** Backend Req 23 AC4 has an "Onboarding Incomplete" queue in the admin dashboard. But there are **no automated reminders** to customers who haven't completed Step 3 (property details).

**Automation Blueprint (§11, line 2926–2930):**
- T+24 hours: SMS reminder with link to onboarding form
- T+72 hours: Second reminder
- T+7 days: Admin notification — "Customer purchased [tier] but hasn't provided property info"

**Problem:** If a customer closes their browser after Stripe checkout without completing the onboarding form, there's no automated follow-up. Viktor would need to manually check the Onboarding Incomplete queue and reach out.

**Required change:**
- Add a scheduled background job (`remind_incomplete_onboarding`, runs daily) that:
  1. Queries ServiceAgreements with status ACTIVE/PENDING and `property_id IS NULL`
  2. At T+24h: send SMS reminder (gated on sms_consent) with link to `/onboarding?session_id=xxx`
  3. At T+72h: send second SMS reminder
  4. At T+7d: create admin notification/alert
- SMS reminders are transactional (not marketing) since they facilitate completing an agreed-upon transaction.

**Files affected:** New background job, SMS service, notification system.

---

## Gap 12: MEDIUM — Verify Company Legal Entity Name

**Current state:** The automation blueprint consistently uses **"Grin's Irrigation & Landscaping, LLC"** (with apostrophe, with "& Landscaping"). The frontend spec uses **"Grins Irrigation LLC"** (no apostrophe, no "& Landscaping").

**Problem:** For TCPA compliance, the exact legal entity name must appear in the SMS consent disclosure text. Using the wrong name could undermine the enforceability of consent records.

**Required action:**
- Viktor must confirm the exact legal entity name as registered with the Minnesota Secretary of State.
- Once confirmed, update all consent language references across both repos.
- This is a manual verification — not a code change — but it blocks the correct TCPA consent language.

---

## Gap 13: LOW — Physical Business Address for CAN-SPAM

**Current state:** The automation blueprint (line 1246) has a placeholder: `"Grin's Irrigation & Landscaping, LLC\n[VIKTOR: PROVIDE ACTUAL BUSINESS ADDRESS BEFORE LAUNCH]"`.

**Problem:** CAN-SPAM requires a valid physical postal address in every commercial email. No code change needed — Viktor must provide the real street address (or PO Box / registered CMRA address) and it must be set in the `COMPANY_PHYSICAL_ADDRESS` environment variable before ANY marketing/commercial emails are sent.

**Required action:** Viktor provides physical business address → set in Railway environment variables → backend email templates will inject it into commercial email footers.

**This is a BLOCKER for commercial emails (not transactional).**

---

## Gap 14: HIGH — Consent Language Version Registry on Backend

**Current state:** The frontend sends `consent_language_version` (e.g., "v1.0") in consent metadata payloads. The backend `sms_consent_records` table has a `consent_language_shown` TEXT field and `consent_form_version` VARCHAR field, but there is no formal registry or validation of consent versions.

**Problem:** For TCPA defensibility, the backend should be able to map a consent version identifier to the exact text that was shown. If a version string changes on the frontend without the backend knowing what text it corresponds to, the audit trail is incomplete.

**Required changes:**
- Create a `consent_language_versions` reference table (or a simple config/enum) mapping version identifiers to the exact consent text:
  ```
  consent_language_versions
  ├── version: VARCHAR(20) PK (e.g., "v1.0")
  ├── consent_text: TEXT NOT NULL (exact TCPA disclosure text)
  ├── effective_date: DATE NOT NULL (when this version started being used)
  ├── deprecated_date: DATE NULL (when this version stopped being used)
  ├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
  ```
- Seed the initial version "v1.0" with the current TCPA-compliant PEWC disclosure text.
- When recording `sms_consent_records`, cross-reference the `consent_form_version` against this table.
- This is append-only — old versions are never deleted, only deprecated.

**Files affected:** New model/migration, seed data, sms_consent_records service (optional validation).

---

## Summary

| # | Gap | Priority | Type |
|---|-----|----------|------|
| 1 | SMS consent cannot be required for checkout (TCPA) | **BLOCKER** | Fix existing Req 30 |
| 2 | `email_marketing_consent` on Lead + pre-checkout | **HIGH** | New field + schema changes |
| 3 | Zone count & lake pump surcharges in checkout | **HIGH** | New endpoint params + pricing logic |
| 4 | Winterization-Only tier seed + job generation | **HIGH** | New tier records + generator logic |
| 5 | `page_url` field on Lead model | **MEDIUM** | New field |
| 6 | Duplicate lead detection | **MEDIUM** | New service logic + error response |
| 7 | AI chat endpoint | **LOW** | Possibly separate spec |
| 8 | sms_consent_record at lead submission (not just conversion) | **HIGH** | TCPA compliance fix |
| 9 | STOP keyword processing in SMS webhook | **HIGH** | TCPA opt-out compliance |
| 10 | SMS time window check (8 AM – 9 PM CT) | **HIGH** | TCPA time restriction |
| 11 | Onboarding incomplete automated reminders | **MEDIUM** | Business process automation |
| 12 | Verify company legal entity name | **MEDIUM** | Manual verification (blocks consent language) |
| 13 | Physical business address for CAN-SPAM | **LOW** | Manual action (blocks commercial emails only) |
| 14 | Consent language version registry | **HIGH** | New reference table + seed data |

### Implementation Order

1. **Gap 1** (BLOCKER) — Fix before any checkout testing
2. **Gap 3** (surcharges) + **Gap 4** (winterization tier) — Define Stripe product/price structure
3. **Gap 8** (sms_consent_record at submission) + **Gap 9** (STOP processing) + **Gap 10** (time window) — TCPA compliance foundation, must be in place before any automated SMS
4. **Gap 2** (`email_marketing_consent`) — Needed for lead form and pre-checkout consent
5. **Gap 12** (legal entity name) — Manual verification, unblocks correct consent language
6. **Gap 5** (`page_url`) + **Gap 6** (duplicate detection) — Lead form integration
7. **Gap 14** (consent language version registry) — TCPA audit trail completeness
8. **Gap 11** (onboarding reminders) — Business process improvement
9. **Gap 13** (physical address) — Manual action, blocks only commercial emails
10. **Gap 7** (AI chat) — Independent, can be done anytime
