# Deployment Instructions: dev → main (April 9, 2026)

**Date:** April 9, 2026 (updated April 14, 2026 — 8:30 PM CT)
**Source branch:** `dev`
**Target branch:** `main`
**Commits:** 92 commits (f308749..edf04f3)
**Companion repo:** `Grins_irrigation` (customer site) — 9 commits dev→main, see Section 16
**Rehearsal:** Full migration chain replayed against a copy of prod 19:50 data on dev — see Section 17.

---

## Summary

This deployment brings eight major feature areas plus critical bug fixes from dev to production:

1. **CallRail SMS Integration** — New SMS provider replacing Twilio, with provider abstraction layer
2. **Scheduling Poll & Response Collection** — Send date-range polls via SMS, collect and export responses
3. **Communications Dashboard Overhaul** — Campaign creation wizard, CSV audience upload, draft editing, campaign lifecycle management
4. **Google Sheets Pipeline Fix** — Header-based column mapping for the restructured form
5. **CRM Changes Update 2** — Sales pipeline, contract renewals, customer merge detection, document management, property type tagging, job confirmation flow
6. **SignWell E-Signature Integration** — Email and embedded document signing for sales pipeline contracts
7. **Dashboard & Onboarding Enhancements** — Removed Estimates/New Leads sections, added services_with_types to onboarding verify-session, per-service week preferences picker
8. **Stripe Terminal (tap-to-pay)** — Connection-token + PaymentIntent endpoints for in-person card collection (NEW frontend dep `@stripe/terminal-js`)
9. **Smoothing-out-after-update2 (Phase 2-5)** — Job/Appointment status check fixes, agreement snapshot fields, target-week inline editing
10. **Sprint 1-7 post-bughunt remediation (Apr 14)** — TCPA/compliance, customer silent-failure paths, CRM data integrity, workflow guards, bulk-send reliability, phone normalization, UX polish & observability
11. **E2E Bug Fixes (post-April 9)** — 7 E2E bug hunt fixes, SITUATION_JOB_MAP job_type correction, SMS 12-hour AM/PM time formatting

---

## Pre-Flight Requirements (MUST complete before merging)

These items will cause the app to **crash or be insecure** if not done before the merge deploys to production. Do not merge until all four are confirmed.

### 1. Provision Redis and set `REDIS_URL`

Redis is required for webhook deduplication, rate-limit caching, and campaign worker health. Without it, duplicate inbound SMS webhooks can create duplicate `campaign_response` rows and the worker health endpoint returns `"status": "unknown"`.

```bash
# Option A: Add Railway Redis plugin (auto-injects REDIS_URL)
# Option B: External provider (Upstash, etc.)
railway variables set REDIS_URL=redis://user:pass@host:port/db
```

### 2. Set `JWT_SECRET_KEY`

The app uses a default dev key (`dev-secret-key-change-in-production`) that is **rejected at startup** when `ENVIRONMENT=production`. Must be a cryptographically strong value, minimum 32 characters.

```bash
# Generate a strong key
openssl rand -base64 48

# Set it on Railway
railway variables set JWT_SECRET_KEY=<generated-key>
```

### 3. Set `ENVIRONMENT=production`

Controls secure cookies, JWT validation strictness, HSTS headers, and CORS enforcement. Currently set to `development` on Railway.

```bash
railway variables set ENVIRONMENT=production
```

### 4. Update `CORS_ORIGINS` for production

Currently contains only dev/preview origins. Must include the production frontend domain or the browser will block all API requests.

```bash
railway variables set CORS_ORIGINS="https://your-production-domain.com,https://grins-irrigation-*-kirilldr01s-projects.vercel.app"
```

---

## Pre-Deployment Checklist

- [ ] **Pre-flight complete:** Redis provisioned, JWT_SECRET_KEY set, ENVIRONMENT=production, CORS_ORIGINS updated
- [ ] Back up the production database (mandatory — migrations #22/#23/#27/#28 alter CHECK constraints; #30 backfills `leads.phone` lossily)
- [ ] Verify CallRail account credentials are ready (API key, account ID, company ID)
- [ ] Generate CallRail webhook secret: `openssl rand -hex 32`
- [ ] Obtain SignWell API key and webhook secret (if enabling e-signatures)
- [ ] Generate SignWell webhook secret: `openssl rand -hex 32`
- [ ] Confirm Redis is available (or provision one on Railway)
- [ ] Verify S3 bucket (`grins-platform-files`) is accessible — customer document uploads use it (no new config, reuses existing PhotoService)
- [ ] Decide whether tap-to-pay launches with this deploy. If yes, obtain `STRIPE_TERMINAL_LOCATION_ID` from the Stripe dashboard (Terminal → Locations) and queue it for Step 1.
- [ ] Coordinate with team — campaign worker will start processing pending recipients within 60s of deploy
- [ ] Coordinate with team — nightly duplicate detection sweep runs at 1:30 AM CT
- [ ] Coordinate `Grins_irrigation` (customer site) merge — should follow this platform deploy (Section 16). Confirm whoever owns that repo is ready.

---

## 1. Database Migrations (31 new migrations)

### Migration Chain

The production DB head is currently at `20260328_110000`. This deploy adds 31 sequential migrations:

| # | Migration | Description |
|---|-----------|-------------|
| 1 | `20260403_100000_add_submission_new_form_fields` | Adds `zip_code`, `work_requested`, `agreed_to_terms` to `google_sheet_submissions` |
| 2 | `20260404_100000_add_content_hash_to_submissions` | Adds `content_hash` column + unique index; drops old `sheet_row_number` unique constraint |
| 3 | `20260407_100000_callrail_phase1_columns` | Adds `channel`, `sending_started_at` to `campaign_recipients`; `created_by_staff_id` to `sms_consent_records`; `campaign_id`, `provider_conversation_id`, `provider_thread_id` to `sent_messages`; renames `status` → `delivery_status` on `campaign_recipients` |
| 4 | `20260408_100000_rename_twilio_sid_to_provider_message_id` | Renames `sent_messages.twilio_sid` → `provider_message_id` |
| 5 | `20260408_100100_fix_sent_messages_message_type_check` | Expands `ck_sent_messages_message_type` constraint from 8 to 16 allowed values |
| 6 | `20260408_100200_align_campaign_recipients_sent_at` | Renames `campaign_recipients.delivered_at` → `sent_at` (idempotent) |
| 7 | `20260408_100300_add_campaigns_automation_rule` | Adds `automation_rule` (JSONB) to `campaigns` |
| 8 | `20260409_100000_add_poll_options_and_campaign_responses` | Adds `poll_options` (JSONB) to `campaigns`; creates new `campaign_responses` table with 4 FKs and 3 indexes |
| 9 | `20260410_100000_add_campaign_responses_dedup_index` | Composite index on `campaign_responses(campaign_id, phone, received_at DESC)` |
| 10 | `20260410_100100_add_thread_id_and_response_indexes` | Index on `sent_messages.provider_thread_id`; unique partial index on `campaign_responses.provider_message_id` |
| 11 | `20260411_100000_crm2_customer_extensions` | Adds `merged_into_customer_id` (FK) to `customers`; `is_hoa` to `properties`; `moved_to`, `moved_at`, `last_contacted_at`, `job_requested` to `leads`; `job_id` (FK) to `customer_photos` |
| 12 | `20260411_100100_crm2_customer_merge_candidates` | Creates `customer_merge_candidates` table (score-based duplicate detection queue) |
| 13 | `20260411_100200_crm2_customer_documents` | Creates `customer_documents` table (S3-linked file metadata) |
| 14 | `20260411_100300_crm2_sales_pipeline` | Creates `sales_entries` and `sales_calendar_events` tables |
| 15 | `20260411_100400_crm2_confirmation_flow` | Creates `job_confirmation_responses` and `reschedule_requests` tables |
| 16 | `20260411_100500_crm2_contract_renewals` | Creates `contract_renewal_proposals` and `contract_renewal_proposed_jobs` tables |
| 17 | `20260411_100600_crm2_service_week_preferences` | Adds `service_week_preferences` (JSON) to `service_agreements` |
| 18 | `20260411_100700_crm2_enums` | Updates `ck_sent_messages_message_type` to include `google_review_request`, `on_my_way`; adds CHECK constraints on `sales_entries`, `job_confirmation_responses`, `customer_documents`, `contract_renewal_proposals`, `contract_renewal_proposed_jobs` |
| 19 | `20260412_100000_add_on_my_way_at_to_jobs` | Adds `on_my_way_at` (DateTime) to `jobs` |
| 20 | `20260412_100100_add_time_tracking_metadata_to_jobs` | Adds `time_tracking_metadata` (JSON) to `jobs` |
| 21 | `20260412_100200_add_scheduled_and_draft_statuses` | **No-op** — Job/Appointment status are VARCHAR not PG enums; new values enforced in Python only. Required as a placeholder so #22-#23 can chain. |
| 22 | `20260414_100000_fix_appointment_status_check_add_draft` | Drops + recreates `ck_appointments_status` to add `'draft'` (was blocking INSERT of draft appointments). |
| 23 | `20260414_100100_fix_job_status_check_add_scheduled` | Drops + recreates `ck_jobs_status` AND `ck_job_status_history_{previous,new}_status` to re-add `'scheduled'` (had been removed by `20260326_120000_simplify_job_statuses`). |
| 24 | `20260414_100200_add_agreement_snapshot_fields` | Adds 7 nullable snapshot columns to `service_agreements` (`tier_slug_snapshot`, `tier_name_snapshot`, `preferred_service_time`, `access_instructions`, `gate_code`, `dogs_on_property`, `no_preference_flags`). **Note: dropped again in #26 — see warning below.** |
| 25 | `20260414_100300_update_tier_descriptions_to_marketing_labels` | Data-only UPDATE to `service_agreements.included_services` (JSON) — aligns service descriptions with marketing copy ("Spring Start-Up", "Mid-Season Inspection & Tune Up", "Fall Winterization", "Monthly Monitoring Visits & Tune Ups (May-Sep)"). |
| 26 | `20260414_100400_drop_redundant_agreement_snapshot_fields` | Drops the 7 columns added in #24 — they duplicated data already canonical in `tiers`, `customers.preferred_service_times`, `properties.{access_instructions,gate_code,has_dogs}`, and `service_agreements.service_week_preferences`. |
| 27 | `20260414_100500_widen_sent_messages_for_reschedule_cancellation` | Drops + recreates `ck_sent_messages_message_type` to add `'appointment_reschedule'` and `'appointment_cancellation'` (without this, every reschedule/cancel SMS rolls back the surrounding txn). |
| 28 | `20260414_100600_widen_sent_messages_for_automated_notification` | Drops + recreates `ck_sent_messages_message_type` to add `'automated_notification'` (Sprint 1 / CR-8 routes legacy `send_automated_message` through the canonical pipeline). |
| 29 | `20260414_100700_add_customer_documents_sales_entry_id` | Adds nullable `sales_entry_id` UUID FK + index to `customer_documents`. Backfills single-entry customers; multi-entry customers stay NULL and signing lookup falls back with a warn log. (H-7) |
| 30 | `20260414_100800_normalize_lead_phones` | Backfills `leads.phone` to bare 10-digit format (strips punctuation + leading `1`). Idempotent; rows that can't normalize are left in place and logged. **Lossy — downgrade is a no-op.** |
| 31 | `20260414_100900_widen_confirmation_response_status` | Widens `job_confirmation_responses.status` from VARCHAR(30) → VARCHAR(50) so the service can write the 35-char value `'reschedule_alternatives_received'` (without it, every free-text reschedule reply silently rolls back the surrounding txn). Existing data fits — no backfill. **Downgrade fails if any post-deploy row exceeds 30 chars.** |

### New Tables (8 total)

| Table | Purpose |
|-------|---------|
| `campaign_responses` | Inbound SMS poll replies linked to campaigns |
| `customer_merge_candidates` | Duplicate detection queue with confidence scoring |
| `customer_documents` | S3-linked file metadata for customer documents |
| `sales_entries` | Estimate-to-job pipeline tracking |
| `sales_calendar_events` | Estimate appointment scheduling |
| `job_confirmation_responses` | Y/R/C keyword appointment confirmation replies |
| `reschedule_requests` | Admin queue for reschedule requests |
| `contract_renewal_proposals` | Service agreement renewal workflow |
| `contract_renewal_proposed_jobs` | Individual proposed jobs within a renewal |

### Column Renames (Breaking for raw SQL queries)

| Table | Old Column | New Column |
|-------|-----------|------------|
| `sent_messages` | `twilio_sid` | `provider_message_id` |
| `campaign_recipients` | `status` | `delivery_status` |
| `campaign_recipients` | `delivered_at` | `sent_at` |

### Columns Added to Existing Tables

| Table | New Columns |
|-------|-------------|
| `customers` | `merged_into_customer_id` (UUID FK) |
| `properties` | `is_hoa` (Boolean) |
| `leads` | `moved_to`, `moved_at`, `last_contacted_at`, `job_requested` |
| `customer_photos` | `job_id` (UUID FK) |
| `service_agreements` | `service_week_preferences` (JSON) |
| `jobs` | `on_my_way_at` (DateTime), `time_tracking_metadata` (JSON) |
| `campaigns` | `poll_options` (JSONB), `automation_rule` (JSONB) |
| `campaign_recipients` | `channel`, `sending_started_at` |
| `sent_messages` | `campaign_id`, `provider_conversation_id`, `provider_thread_id` |
| `sms_consent_records` | `created_by_staff_id` |
| `customer_documents` | `sales_entry_id` (UUID FK, nullable, indexed) — added in migration #29 |

### CHECK Constraints Modified (Critical)

Migrations #22, #23, #27, #28 drop and recreate CHECK constraints. These are not idempotent at the SQL level but are wrapped in `DROP CONSTRAINT IF EXISTS` where appropriate — review individual migrations before partial reruns.

| Constraint | Migration | Adds Value(s) |
|------------|-----------|---------------|
| `ck_appointments_status` | #22 | `'draft'` |
| `ck_jobs_status` | #23 | `'scheduled'` |
| `ck_job_status_history_previous_status` | #23 | `'scheduled'` |
| `ck_job_status_history_new_status` | #23 | `'scheduled'` |
| `ck_sent_messages_message_type` | #27 | `'appointment_reschedule'`, `'appointment_cancellation'` |
| `ck_sent_messages_message_type` | #28 | `'automated_notification'` |

### Running Migrations

Migrations run automatically on app startup via Alembic. To run manually:

```bash
# On Railway
railway run uv run alembic upgrade head

# Verify head
railway run uv run alembic current
# Expected: 20260414_100900 (head)
```

### Rollback

If something goes wrong, each migration has a `downgrade()` function:

```bash
# Roll back to the pre-deploy state
railway run uv run alembic downgrade 20260328_110000
```

**Warnings:**
- Migration #4 (`rename_twilio_sid_to_provider_message_id`) is NOT idempotent — only roll back once.
- Migration #30 (`normalize_lead_phones`) downgrade is a no-op — original phone formatting is lost. Restore from DB backup if a regression is detected.
- Migrations #22/#23/#27/#28 (CHECK constraints): downgrade restores the *previous* allowed-values list. Any data inserted under the new values will violate the recreated constraint and the downgrade will fail mid-statement. Confirm there are no rows with `'draft'` / `'scheduled'` / `'appointment_reschedule'` / `'appointment_cancellation'` / `'automated_notification'` before downgrading.
- Migration #29 (`add_customer_documents_sales_entry_id`): downgrade drops the FK + index + column. Any signing-document linkage created while the column existed will be lost.

---

## 2. Environment Variables (Railway Backend)

### New Required Variables

These must be set **before deploying** or the app will fail to send SMS:

| Variable | Value | Description |
|----------|-------|-------------|
| `CALLRAIL_API_KEY` | `<from CallRail dashboard>` | API authentication key |
| `CALLRAIL_ACCOUNT_ID` | `<from CallRail dashboard>` | Account identifier |
| `CALLRAIL_COMPANY_ID` | `<from CallRail dashboard>` | Company identifier |
| `CALLRAIL_TRACKING_NUMBER` | `+19525293750` | 10DLC registered sending number |
| `CALLRAIL_WEBHOOK_SECRET` | `<openssl rand -hex 32>` | HMAC signing secret for inbound webhooks |

> **Note:** `CALLRAIL_TRACKER_ID` appears in `.env.example` but is **not read by the code** — the app discovers trackers dynamically via the CallRail API. You do not need to set it.

### New Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMS_PROVIDER` | `callrail` | Provider selection: `callrail`, `twilio`, or `null` |
| `SMS_SENDER_PREFIX` | `Grins Irrigation: ` | Prefix prepended to all outbound SMS |
| `SMS_TEST_PHONE_ALLOWLIST` | *(unset)* | Comma-separated phone numbers allowed to receive SMS. **Leave unset in production** to allow all recipients. Set in staging to restrict sends. |
| `SIGNWELL_API_KEY` | *(empty)* | SignWell e-signature API key. Required for email/embedded contract signing in the sales pipeline. App logs a warning if unset but does not crash. |
| `SIGNWELL_WEBHOOK_SECRET` | *(empty)* | SignWell webhook HMAC secret. Required to verify inbound signature-completion webhooks. |
| `STRIPE_TERMINAL_LOCATION_ID` | *(empty)* | **NEW** — Stripe Terminal location ID (e.g. `tml_...`). Required only if you intend to use the in-person tap-to-pay flow on the Schedule page. App will accept payments without it but the Stripe SDK won't pre-bind a location. |
| `GOOGLE_REVIEW_URL` | *(unset)* | Optional deep link to the Google review page included in `review_request` SMS. Falls back to a hard-coded constant when unset. |
| `REDIS_URL` | *(unset)* | Redis connection URL for rate-limit tracking, webhook dedup, and worker health. **Strongly recommended** — system degrades gracefully without it but loses dedup and rate-limit caching. |
| `ENVIRONMENT` | `development` | Set to `production` for secure cookies, proper CORS, etc. (likely already set) |

### Setting Variables on Railway

```bash
railway variables set \
  CALLRAIL_API_KEY=<key> \
  CALLRAIL_ACCOUNT_ID=<id> \
  CALLRAIL_COMPANY_ID=<id> \
  CALLRAIL_TRACKING_NUMBER=+19525293750 \
  CALLRAIL_WEBHOOK_SECRET=<generated-secret> \
  SMS_PROVIDER=callrail \
  REDIS_URL=<redis-url> \
  SIGNWELL_API_KEY=<signwell-key> \
  SIGNWELL_WEBHOOK_SECRET=<signwell-secret>
```

### Variables to Remove (Optional Cleanup)

If fully switching from Twilio to CallRail, these Twilio variables are no longer required but won't cause harm if left:

- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

---

## 3. Redis (New Dependency)

Redis is used for three purposes:

1. **Webhook deduplication** — Prevents processing the same CallRail inbound SMS twice (24h TTL keys)
2. **Rate-limit caching** — Caches CallRail API rate-limit state (120s TTL)
3. **Worker health tracking** — Records last campaign worker tick for the `/campaigns/worker-health` endpoint

### Provisioning Options

**Option A: Railway Redis Plugin**
- Add a Redis service in the Railway dashboard
- Railway auto-injects `REDIS_URL`

**Option B: External Redis (Upstash, etc.)**
- Set `REDIS_URL` manually (format: `redis://user:pass@host:port/db` or `rediss://` for TLS)

### Without Redis

The system functions without Redis but with degraded behavior:
- Webhook dedup is lost → occasional duplicate `campaign_response` rows (harmless, covered by unique index)
- Rate-limit state is not cached → extra DB reads
- Worker health endpoint returns `"status": "unknown"`

---

## 4. CallRail Webhook Configuration (External)

The inbound SMS webhook must be registered in the CallRail dashboard. See [callrail-webhook-setup.md](./callrail-webhook-setup.md) for the full runbook.

### Quick Steps

1. Log in to [CallRail](https://app.callrail.com)
2. Navigate to **Account Settings → Integrations → Webhooks**
3. Add webhook:
   - **URL:** `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/callrail/inbound`
   - **Events:** Inbound SMS
   - **Signing Secret:** Same value as `CALLRAIL_WEBHOOK_SECRET` env var
4. Save

### Verification

After deploying, send a test SMS to the tracking number (`+19525293750`):

```bash
# Check Railway logs
railway logs --filter "sms.webhook"
```

Expected log: `sms.webhook.inbound` with status 200.

---

## 5. SignWell Webhook Configuration (External)

If using e-signatures in the sales pipeline, configure the SignWell webhook:

1. Log in to [SignWell](https://www.signwell.com)
2. Navigate to **Settings → API → Webhooks**
3. Add webhook:
   - **URL:** `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/signwell`
   - **Events:** `document_completed`
   - **Signing Secret:** Same value as `SIGNWELL_WEBHOOK_SECRET` env var
4. Save

The webhook processes `document_completed` events to auto-advance sales pipeline entries from `send_contract` → `closed_won`.

---

## 6. Security Header Changes (CSP)

The `Content-Security-Policy` `frame-src` directive was updated to include `https://app.signwell.com` for embedded e-signature iframes. This is baked into the code — no deployment action needed, but be aware if you have a separate WAF or CDN CSP override.

**Before:** `frame-src https://js.stripe.com https://maps.google.com`
**After:** `frame-src https://js.stripe.com https://maps.google.com https://app.signwell.com`

---

## 7. New API Endpoints

### Public (No Auth)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/webhooks/callrail/inbound` | CallRail inbound SMS webhook (HMAC-verified) |
| POST | `/api/v1/webhooks/signwell` | SignWell document completion webhook (HMAC-verified) |
| POST | `/api/v1/checkout/create-session` | Create Stripe checkout session (rate-limited) |
| POST | `/api/v1/checkout/manage-subscription` | Send subscription management email (rate-limited) |

### Authenticated — Campaigns & Communications

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/campaigns/worker-health` | Campaign worker health status |
| POST | `/api/v1/campaigns/audience/preview` | Preview matched recipients |
| POST | `/api/v1/campaigns/audience/csv` | Upload CSV audience file (Admin only) |
| PATCH | `/api/v1/campaigns/{id}` | Update draft campaign |
| POST | `/api/v1/campaigns/{id}/cancel` | Cancel a campaign |
| POST | `/api/v1/campaigns/{id}/retry-failed` | Retry failed recipients |
| GET | `/api/v1/campaigns/{id}/recipients` | List campaign recipients |
| GET | `/api/v1/campaigns/{id}/responses/summary` | Poll response summary (bucket counts) |
| GET | `/api/v1/campaigns/{id}/responses` | List poll responses (paginated) |
| GET | `/api/v1/campaigns/{id}/responses/export.csv` | Export responses as CSV |

### Authenticated — Sales Pipeline (NEW — CRM2)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/sales/pipeline` | List sales entries with status summary counts |
| GET | `/api/v1/sales/pipeline/{id}` | Get sales entry detail |
| POST | `/api/v1/sales/pipeline/{id}/advance` | Advance entry one step in pipeline |
| PUT | `/api/v1/sales/pipeline/{id}/status` | Manual status override |
| POST | `/api/v1/sales/pipeline/{id}/sign/email` | Trigger email signing via SignWell |
| POST | `/api/v1/sales/pipeline/{id}/sign/embedded` | Get embedded signing URL |
| POST | `/api/v1/sales/pipeline/{id}/convert` | Convert to job (signature gated) |
| POST | `/api/v1/sales/pipeline/{id}/force-convert` | Force convert to job without signature |
| DELETE | `/api/v1/sales/pipeline/{id}` | Mark entry as lost |
| GET | `/api/v1/sales/calendar/events` | List estimate appointments |
| POST | `/api/v1/sales/calendar/events` | Create estimate appointment |
| PUT | `/api/v1/sales/calendar/events/{id}` | Update estimate appointment |
| DELETE | `/api/v1/sales/calendar/events/{id}` | Delete estimate appointment |

### Authenticated — Stripe Terminal (NEW — Tap-to-Pay)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/stripe/terminal/connection-token` | Create connection token for the Stripe Terminal SDK |
| POST | `/api/v1/stripe/terminal/payment-intent` | Create a `card_present` PaymentIntent for in-person collection |

Both require an authenticated active user. They short-circuit with `stripe_not_configured` if `STRIPE_SECRET_KEY` is missing.

### Authenticated — Contract Renewals (NEW — CRM2)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/contract-renewals` | List renewal proposals |
| GET | `/api/v1/contract-renewals/{id}` | Get proposal detail with proposed jobs |
| POST | `/api/v1/contract-renewals/{id}/approve-all` | Bulk approve all proposed jobs |
| POST | `/api/v1/contract-renewals/{id}/reject-all` | Bulk reject all proposed jobs |
| POST | `/api/v1/contract-renewals/{id}/jobs/{job_id}/approve` | Approve single proposed job |
| POST | `/api/v1/contract-renewals/{id}/jobs/{job_id}/reject` | Reject single proposed job |
| PUT | `/api/v1/contract-renewals/{id}/jobs/{job_id}` | Modify proposed job |

### Authenticated — Reschedule Requests (NEW — CRM2)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/schedule/reschedule-requests` | List reschedule request queue |
| PUT | `/api/v1/schedule/reschedule-requests/{id}/resolve` | Resolve a reschedule request |

### Authenticated — Enhanced Existing Endpoints (NEW — CRM2)

**Jobs (`/api/v1/jobs/{id}/...`)**:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/{id}/complete` | Mark job as complete |
| POST | `/{id}/invoice` | Create invoice from job |
| POST | `/{id}/on-my-way` | Send "On My Way" SMS + log timestamp |
| POST | `/{id}/started` | Log job started timestamp |
| POST | `/{id}/notes` | Add note to job |
| POST | `/{id}/photos` | Upload photo linked to job |
| POST | `/{id}/review-push` | Send Google review request SMS |

**Leads (`/api/v1/leads/{id}/...`)**:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/{id}/move-to-jobs` | Move lead to Jobs (auto-create customer) |
| POST | `/{id}/move-to-sales` | Move lead to Sales pipeline |
| PUT | `/{id}/contacted` | Mark lead as contacted |

**Customers (`/api/v1/customers/...`)**:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/duplicates` | Get duplicate review queue |
| POST | `/{id}/merge/preview` | Preview merge result |
| GET | `/check-duplicate` | Tier 1 duplicate check by phone/email |
| GET/POST/PUT/DELETE | `/{id}/service-preferences[/{pref_id}]` | CRUD service preferences |
| POST/GET | `/{id}/documents[/{doc_id}]` | Upload/list/download/delete documents |

**Invoices (`/api/v1/invoices/...`)**:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/mass-notify` | Mass notify by invoice criteria |

**Onboarding:**
- `POST /onboarding/verify-session` now includes `services_with_types` in the response
- `POST /onboarding/complete-onboarding` now accepts `service_week_preferences`

### Authorization Changes

- Campaign creation: elevated from `CurrentActiveUser` → `ManagerOrAdminUser`
- Campaign send: now requires `require_campaign_send_authority` (managers ≤ 50 recipients, admins unlimited)
- Campaign delete: elevated to `AdminUser` only; restricted to draft/cancelled campaigns

---

## 8. Frontend Changes (Vercel)

### New Pages/Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/portal/manage-subscription` | `SubscriptionManagementPage` | Customer self-service subscription management |
| `/contract-renewals` | `ContractRenewalsPage` | List contract renewal proposals |
| `/contract-renewals/:id` | `ContractRenewalsPage` | View renewal proposal detail |
| `/sales/:id` | `SalesPage` | Sales entry detail view (new sub-route) |

### Updated Components

- **CommunicationsDashboard** — Complete overhaul with campaign list, creation wizard, poll options editor
- **AudienceBuilder** — New component for selecting recipients (customer/lead filters + CSV upload)
- **CampaignReview** — Pre-send review screen with segment counter and recipient preview
- **CampaignResponsesView** — View/filter/export poll responses
- **FailedRecipientsDetail** — View and retry failed campaign recipients
- **LeadsList** — Added Google Sheets sync button, auto-refresh, move-to-jobs/sales actions, contacted status
- **CustomerList** — Updated with duplicate detection, document management, service preferences, merge preview
- **Dashboard** — Removed Estimates and New Leads sections
- **SalesPage** — Full sales pipeline list view with status columns, advance/close actions, calendar events
- **ContractRenewalsPage** — New page for reviewing and approving/rejecting renewal proposals
- **JobDetail** — Added "On My Way", started, complete, invoice, notes, photos, review-push actions
- **JobList** — Inline week-picker (`JobWeekEditor`) on every `to_be_scheduled` row for editing target_start_date/target_end_date (Sprint feat 1a74b2b)
- **OnSiteOperations** — New on-site action surface (Stripe Terminal payment collection, on-my-way trigger, photo upload, etc.)
- **PaymentCollector / PaymentSection** — Stripe Terminal in-person tap-to-pay flow on the Schedule and Job Detail pages
- **WeekPickerStep** (NEW) — Customer portal onboarding picker for explicit per-service week preferences (depends on `services_with_types` from `/api/v1/onboarding/verify-session`)
- **SignWellEmbeddedSigner** — Embedded SignWell iframe for Sales pipeline contracts

### Vercel Configuration

No changes to `vercel.json` are required for the platform admin frontend. The existing SPA rewrite rule handles all new routes:

```json
{ "source": "/((?!assets/).*)", "destination": "/index.html" }
```

> **Note:** the *customer-site* repo (`Grins_irrigation`) **does** require a `vercel.json` change to add CSP headers — see Section 16 below.

### Vercel Build — New Dependency

`frontend/package.json` adds **`@stripe/terminal-js@^0.26.0`**. Vercel will install it automatically on the next build (no manual step). Verify by:
1. Watching the Vercel build log for the install line.
2. After deploy, opening DevTools → Network and confirming the Stripe Terminal SDK is loaded only on Schedule and Job Detail pages (lazy import, not in the global bundle).

### Vercel Environment Variables

Verify these are set (likely already configured):

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://grinsirrigationplatform-production.up.railway.app` |

No new VITE_* variables are required by this deploy. (Stripe Terminal connection-token + PaymentIntent are minted server-side by the platform — the frontend only consumes them.)

---

## 9. Background Jobs / Scheduled Tasks

### Existing Campaign Worker (unchanged)

Runs **every 60 seconds** inside the FastAPI process:

| Job | Schedule | Description |
|-----|----------|-------------|
| `process_pending_campaign_recipients` | Every 60s | Picks up pending campaign recipients and sends SMS via CallRail |

- **Time window:** Only sends during 8 AM – 9 PM CT (hardcoded)
- **Batch size:** Max 2 recipients per tick (stays under 140 SMS/hour rate limit)
- **Rate-limit aware:** Reads `x-rate-limit-*` headers from CallRail responses
- **Health endpoint:** `GET /api/v1/campaigns/worker-health` shows last tick, pending count, rate-limit state

### New: Duplicate Detection Sweep (CRM2)

| Job | Schedule | Description |
|-----|----------|-------------|
| `duplicate_detection_sweep` | Daily at 1:30 AM CT | Scans customers for duplicate phone/email matches, creates `customer_merge_candidates` records with confidence scores |

### No Separate Worker Needed

Both jobs run in-process via APScheduler in the FastAPI lifespan. No additional Procfile, Railway service, or worker dyno is required.

### Monitoring

```bash
# Watch campaign worker ticks
railway logs --filter "campaign.worker"

# Watch duplicate detection sweep
railway logs --filter "duplicate_detection"

# Check worker health via API
curl -H "Cookie: ..." https://<domain>/api/v1/campaigns/worker-health
```

---

## 10. SMS Provider Switchover

### What Changed

- New provider abstraction layer (`src/grins_platform/services/sms/`)
- CallRail is now the default provider (was Twilio)
- Factory pattern selects provider based on `SMS_PROVIDER` env var
- All providers enforce `SMS_TEST_PHONE_ALLOWLIST` guard

### Provider Boot Audit

On startup, the app logs which SMS provider was selected and writes an audit record:

```
app.sms_provider_resolved provider=callrail
```

### Rollback to Twilio

If CallRail has issues, switch back instantly:

```bash
railway variables set SMS_PROVIDER=twilio
# Restart the service
```

Requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` to still be set.

---

## 11. Data Migration Script (Manual, One-Time)

### Work Requests → Sales Entries Migration

**Script:** `scripts/migrate_work_requests_to_sales.py`

This one-time script converts existing `google_sheet_submissions` (work requests) into `sales_entries` for the new sales pipeline. It must be run **after** Alembic migrations complete (the `sales_entries` table must exist).

**What it does:**
- Maps `processing_status` to `SalesEntryStatus`
- Resolves `customer_id` via lead linkage, phone, or email matching
- Extracts `property_id` from customer's primary property
- Determines `job_type` from service request fields
- Builds notes from service/repair information

**How to run:**

```bash
# On Railway (after migrations have run)
railway run python scripts/migrate_work_requests_to_sales.py
```

**This is optional** — only needed if you want historical work requests to appear in the sales pipeline. New leads entering via Google Sheets will flow into sales entries automatically.

---

## 12. Dependency Changes

- **Python:** No new runtime packages in `pyproject.toml` (only ruff lint-config additions: `COM812` ignore, expanded test/migration override rule sets).
- **Frontend (admin platform — `frontend/package.json`):** **One new dependency** — `@stripe/terminal-js@^0.26.0` for tap-to-pay. Vercel build will fetch this on the next deploy. Verify after Vercel completes the build that the bundle includes the new chunk and the Schedule page tap-to-pay button mounts without runtime errors.

---

## 13. Post-April 9 Bug Fixes (commits 7b882a3..93886b8)

These 7 additional commits landed on dev after the original 44-commit cutoff. They contain critical bug fixes found during E2E testing and do **not** introduce new migrations, environment variables, or dependencies.

### E2E Bug Hunt Fixes (cf2cee9)

| Bug | Fix | Files Changed |
|-----|-----|---------------|
| Bug #2 | Leads with `requires_estimate` category now redirect from Jobs → Sales pipeline automatically when `move_to_jobs` is called | `services/lead_service.py` |
| Bug #4 | Appointment confirmation SMS deduplication is now scoped per `appointment_id` — sending confirmations for two different appointments for the same customer no longer blocks the second send | `services/sms_service.py`, `repositories/sent_message_repository.py` |
| Bug #5 | Dedupe-blocked SMS sends now return proper JSON (`{success: false, reason: ...}`) instead of crashing with a 500 error | `api/v1/sms.py`, `schemas/sms.py` |
| Bug #7 | `POST /jobs/{id}/started` now transitions job status from `to_be_scheduled` → `in_progress` | `api/v1/jobs.py` |
| Frontend | StatusActionButton improvements, AppointmentForm time field fix, JobList column additions | `StatusActionButton.tsx`, `AppointmentForm.tsx`, `JobList.tsx` |

### SITUATION_JOB_MAP Fix (2d9a236)

The lead-to-job mapping was using the job *category* (e.g., `requires_estimate`) as the `job_type` field. Now correctly maps to actual job types: `new_system`, `upgrade`, `small_repair`, `consultation`.

### SMS Time Formatting (5dd51f0)

Appointment confirmation SMS messages now display times in 12-hour AM/PM format (e.g., "between 9:00 AM and 11:00 AM") instead of raw 24-hour time strings.

### API Schema Change (Non-Breaking)

`SMSSendResponse.message_id` changed from required `UUID` to optional `UUID | None`. A new `reason` field was added. Both changes are additive — existing consumers that check `success: true` before reading `message_id` are unaffected.

---

## 14. Railway Environment Audit (as of April 13, 2026)

Current Railway dev environment variable status for production readiness:

| Variable | Status | Notes |
|----------|--------|-------|
| CALLRAIL_API_KEY | **Set** | |
| CALLRAIL_ACCOUNT_ID | **Set** | |
| CALLRAIL_COMPANY_ID | **Set** | |
| CALLRAIL_TRACKING_NUMBER | **Set** | +19525293750 |
| CALLRAIL_WEBHOOK_SECRET | **Set** | |
| SMS_PROVIDER | **Set** | callrail |
| SMS_TEST_PHONE_ALLOWLIST | **Set** | +19527373312 — **remove or update for production** |
| STRIPE_SECRET_KEY | **Set** | Test mode (sk_test_*) — **switch to live key for production** |
| STRIPE_WEBHOOK_SECRET | **Set** | Test mode — **switch to live key for production** |
| STRIPE_CUSTOMER_PORTAL_URL | **Set** | Test mode — **switch to live URL for production** |
| DATABASE_URL | **Set** | |
| GOOGLE_SHEETS_* | **Set** | All 3 vars configured |
| GOOGLE_SERVICE_ACCOUNT_KEY_JSON | **Set** | |
| CORS_ORIGINS | **Set** | Dev origins — **update for production domain** |
| REDIS_URL | **NOT SET** | Must provision Redis before deploy (webhook dedup, rate-limit caching, worker health) |
| SIGNWELL_API_KEY | **NOT SET** | Required for Sales pipeline e-signature flow |
| SIGNWELL_WEBHOOK_SECRET | **NOT SET** | Required for signature completion webhooks |
| JWT_SECRET_KEY | **NOT SET** | Using default "dev-secret-key..." — **must set a strong 32+ char secret for production** |
| OPENAI_API_KEY | **NOT SET** | Required for AI scheduling/categorization features |
| GOOGLE_MAPS_API_KEY | **NOT SET** | Required for route optimization (falls back to haversine without it) |
| AWS_ACCESS_KEY_ID | **NOT SET** | Required for S3 file storage (photos, documents, invoice PDFs) |
| AWS_SECRET_ACCESS_KEY | **NOT SET** | Required for S3 file storage |
| S3_BUCKET_NAME | **NOT SET** | Defaults to `grins-platform-files` if unset |
| EMAIL_API_KEY | **NOT SET** | Email sending is currently a placeholder — not blocking |
| STRIPE_TERMINAL_LOCATION_ID | **NOT SET** | **NEW** — Required only if tap-to-pay on Schedule page is in-scope for v1 launch. Skip if Stripe Terminal is post-launch. |
| GOOGLE_REVIEW_URL | **NOT SET** | Optional — falls back to hard-coded URL in `review_request` SMS |
| ENVIRONMENT | **Set** | `development` — **change to `production` for main** |

### Action Required Before Production Deploy

1. **Provision Redis** on Railway (or external provider) and set `REDIS_URL`
2. **Set JWT_SECRET_KEY** to a cryptographically strong value (min 32 chars)
3. **Set SIGNWELL_API_KEY + SIGNWELL_WEBHOOK_SECRET** if enabling e-signatures
4. **Set OPENAI_API_KEY** if AI features are needed
5. **Set GOOGLE_MAPS_API_KEY** if route optimization is needed
6. **Set AWS credentials + S3_BUCKET_NAME** if file uploads are needed
7. **Update CORS_ORIGINS** to include the production frontend domain
8. **Update ENVIRONMENT** to `production`
9. **Remove or expand SMS_TEST_PHONE_ALLOWLIST** for production (leave unset to allow all recipients)
10. **Switch Stripe keys** from test to live mode (see [productiongolive.md](./productiongolive.md))
11. **Set STRIPE_TERMINAL_LOCATION_ID** if tap-to-pay is in scope for launch (otherwise skip — endpoint will reject with `stripe_not_configured`)

---

## Deployment Steps (Ordered)

### Step 1: Set Environment Variables on Railway

Set all required CallRail variables, SignWell variables, and REDIS_URL **before** deploying code. Optionally set Stripe Terminal location ID if tap-to-pay is in scope for v1 launch.

```bash
railway variables set \
  CALLRAIL_API_KEY=<key> \
  CALLRAIL_ACCOUNT_ID=<id> \
  CALLRAIL_COMPANY_ID=<id> \
  CALLRAIL_TRACKING_NUMBER=+19525293750 \
  CALLRAIL_WEBHOOK_SECRET=<generated-secret> \
  SMS_PROVIDER=callrail \
  REDIS_URL=<redis-url> \
  SIGNWELL_API_KEY=<signwell-key> \
  SIGNWELL_WEBHOOK_SECRET=<signwell-secret> \
  JWT_SECRET_KEY=<openssl-rand-base64-48> \
  ENVIRONMENT=production \
  CORS_ORIGINS="https://<production-frontend-domain>,https://grins-irrigation-*-kirilldr01s-projects.vercel.app"

# Optional — only if tap-to-pay launches with this deploy:
railway variables set STRIPE_TERMINAL_LOCATION_ID=tml_<id>
```

### Step 2: Provision Redis (if not already available)

Add a Redis plugin on Railway or set `REDIS_URL` to an external instance.

### Step 3: Merge dev → main

```bash
git checkout main
git merge dev
git push origin main
```

### Step 4: Verify Migrations Ran

Check Railway logs for:
```
INFO  [alembic.runtime.migration] Running upgrade ... -> 20260414_100900
```

Look for the print line from migration #30:
```
normalize_lead_phones: updated=<N> already_normalized=<N> unparseable=<N>
```
Any non-zero `unparseable` count is data that operators should triage manually (see logged rows; the migration left them untouched).

Or verify manually:
```bash
railway run uv run alembic current
# Should show: 20260414_100900 (head)
```

### Step 5: Verify App Startup

Check logs for:
```
app.sms_provider_resolved provider=callrail
scheduler.jobs.registered [..., "duplicate_detection_sweep"]
app.startup_completed
```

### Step 6: Configure CallRail Webhook

Follow [callrail-webhook-setup.md](./callrail-webhook-setup.md) — point the webhook URL to the production Railway domain.

### Step 7: Configure SignWell Webhook (if using e-signatures)

1. In SignWell dashboard → Settings → API → Webhooks
2. **URL:** `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/signwell`
3. **Events:** `document_completed`
4. **Secret:** Same as `SIGNWELL_WEBHOOK_SECRET`

### Step 8: Run Data Migration Script (Optional)

If you want historical work requests in the sales pipeline:

```bash
railway run python scripts/migrate_work_requests_to_sales.py
```

### Step 9: Verify Vercel Frontend (Admin Platform)

Vercel should auto-deploy from main. **Confirm the build log includes `@stripe/terminal-js` install** (new dependency). Then verify:
- Communications dashboard loads at `/communications`
- Campaign creation wizard works (draft mode)
- Subscription management page loads at `/portal/manage-subscription`
- Contract renewals page loads at `/contract-renewals`
- Sales pipeline page loads at `/sales`
- Dashboard no longer shows Estimates or New Leads sections
- Jobs tab renders the inline week-picker on `to_be_scheduled` rows
- Schedule page renders the tap-to-pay button (if `STRIPE_TERMINAL_LOCATION_ID` is set; otherwise it falls back to the older Stripe Checkout link)

### Step 9b: Merge & Verify Customer Site (`Grins_irrigation` repo)

Once the platform is healthy, merge the customer-site dev → main and let Vercel redeploy. See **Section 16** for full details. After deploy:
- Open the homepage; DevTools → Network response headers should include the new `Content-Security-Policy` header.
- `/sitemap.xml` should serve a real XML sitemap (built by `vite-plugin-sitemap`).
- Submit a test lead through the contact form; verify it lands in the platform's Leads page (uses `address`, not `zipCode`).
- Walk through the customer onboarding flow end-to-end; verify the `WeekPickerStep` renders and the `services_with_types` payload is correctly consumed.

### Step 10: Post-Deploy Smoke Tests

1. **Campaign worker running:** Hit `GET /api/v1/campaigns/worker-health` — status should be `"healthy"`
2. **Inbound webhook working:** Send a test SMS to `+19525293750` — check logs for `sms.webhook.inbound`
3. **Google Sheets sync:** Click "Sync Sheets" on the Leads page — verify new submissions appear
4. **Campaign create/send flow:** Create a draft campaign, add audience, review, and send (use test phone only — `+19527373312` per the SMS test number restriction)
5. **Sales pipeline:** Create a test sales entry from a lead, verify it appears in the pipeline
6. **Contract renewals:** Verify the renewal proposals page loads and shows data (if any exist)
7. **Duplicate detection:** Check logs after 1:30 AM for `duplicate_detection` sweep results
8. **Reschedule SMS:** Cancel a confirmed appointment from the Schedule page; verify the cancellation SMS reaches the test phone AND the appointment status update *commits* (without migration #27 the SMS write would roll back the txn)
9. **Lead phone backfill:** Spot-check a few `leads.phone` values in the DB — should be bare 10-digit format
10. **Stripe Terminal connection token (only if STRIPE_TERMINAL_LOCATION_ID set):** `POST /api/v1/stripe/terminal/connection-token` should return `{secret: "..."}`. Test the in-person tap-to-pay end-to-end on a real Stripe Terminal reader if available.
11. **Sales pipeline signing per-entry (H-7 fix):** Customer with two active sales entries — open both detail pages and verify each renders the correct estimate/contract document (not the most-recent across all entries)
12. **Onboarding week-pref flow:** Run a fresh customer onboarding through the customer site — verify `service_week_preferences` lands on the new `service_agreements` row and propagates to the generated jobs

---

## 15. Sprint 1-7 Post-Bughunt Remediation (Apr 14 commits e554ba7..f32bbf3)

These 7 sequential sprints landed *after* the original April 13 doc revision (commit `48b9eb2`) and before the Apr 14 property-column fix (`fc29282`). They close ~30 critical/high/medium bughunt findings and rewrite several SMS-path code paths. **Each sprint is independently mergeable, but all sprints depend on migrations #27-#30 above.**

| Sprint | Commit | Scope | Notes |
|--------|--------|-------|-------|
| 1 | `e554ba7` | TCPA/compliance — `send_automated_message` rewritten as a shim onto `send_message` (audit + dedup + consent + lead-touch); `request_google_review` switched off the legacy `customer.sms_opt_in` flag onto `SmsConsentRecord`; consent denial returns structured `ReviewRequestResult(sent=False)` with HTTP 2xx instead of HTTP 500. | Requires migration #28 (`automated_notification` enum). |
| 2 | `51149d5` | Customer silent-failure remediation — surfaces unrecoverable customer-side failures that previously absorbed and 2xx-returned. | No migration. |
| 3 | `604494c` | CRM data integrity — property + document scoping; ensures `customer_documents.sales_entry_id` is set on new uploads. | Requires migration #29 (`customer_documents.sales_entry_id`). |
| 4 | `330446a` | Workflow guards & cleanup — additional state-transition guards; removes a few dead code paths. | No migration. |
| 5 | `dc83470` | Appointments bulk-send reliability — fixes idempotency and rate-limit handling for SendAllConfirmations / SendDayConfirmations. | No migration. |
| 6 | `c3c9e98` | Phone normalization & consent lookup — widens `_phone_variants` to match every plausible historical phone formatting, then backfills `leads.phone` to the bare 10-digit canonical form. | Requires migration #30 (`normalize_lead_phones`). |
| 7 | `f32bbf3` | UX polish & observability — phone regex accepts leading `+`; Lead→Sales/Jobs toast surfaces "Merged into existing customer"; ReviewRequest renders structured 409; Winterization + Seasonal Maintenance added to LeadSituation enum + label/badge maps; dashboardKeys.summary() invalidations on lead mutations. | No migration. |

Plus one small follow-up in `fc29282` (`property_service.ensure_property_for_lead` was reading the wrong column name — `lead.job_address` instead of `lead.address`, silently returning None for every move-to-sales/move-to-jobs).

### Schemas / Behavior Changes Worth Calling Out

- `SMSService.send_automated_message` is now a back-compat shim. Any external caller still using it works, but messages flow through `send_message` (consent + dedup + audit). The new `MessageType.AUTOMATED_NOTIFICATION` is the catch-all enum value when the legacy string doesn't map to a known type.
- `request_google_review` now returns 2xx with a structured payload `{code, message, last_sent_at}` for the dedupe / consent-denied paths; previously raised. Frontend updated to render the structured 409 body.
- `LeadSituation` enum gained `WINTERIZATION` + `SEASONAL_MAINTENANCE`; SITUATION_JOB_MAP routes them to ready-to-schedule job types (no estimate gate).
- `JobUpdate` schema accepts `target_start_date` + `target_end_date`; admin Jobs tab renders an inline week-picker on every `to_be_scheduled` row.
- Stripe webhook renewal handler: when `agreement.auto_renew=true`, now creates a `contract_renewal_proposal` for admin review instead of auto-generating jobs (CRM2 Req 31.1).

---

## 16. Companion Repo: Grins_irrigation (Customer Website)

The customer-facing marketing site is a separate repo (`Grins_irrigation`) that auto-deploys to Vercel. It has 9 commits on `dev` not yet merged to `main`. **It must be merged in coordination with this platform deploy** because the lead form schema (`address` instead of `zipCode`) and the onboarding `services_with_types` flow depend on the platform changes landing first.

### Commits Pending dev → main on Grins_irrigation

```
b94fd42 feat(onboarding): require explicit week choice for every tier-included service
39f164e feat(onboarding): add per-service week preference selection to onboarding form
3bf0fb8 chore: add firecrawl research data, competitor analysis, SEO docs, and scheduled tasks
05b70cf chore: add research data, e2e screenshots, competitor analysis, and SEO assets
ea77560 feat: add free-use hero images for 4 blog posts missing images
59d7527 fix: prevent mid-word break on hero headlines and reset scroll on navigation
0b0b556 fix: allow clearing zone count input in subscription modal
c3063ee feat: Website_Changes_Update_2 — lead form compliance, photos, pricing single-source
cd67559 feat: 12k-website visual upgrades, SEO, content, and city/nav fixes
```

### Required Configuration Changes

#### 1. `vercel.json` — CSP Headers (NEW)

The customer site adds a Content-Security-Policy via Vercel headers (previously had none). The new policy:

```jsonc
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com https://js.stripe.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: blob:; connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com https://*.up.railway.app https://api.stripe.com https://api.ipify.org; frame-src 'self' https://www.google.com https://www.googletagmanager.com https://js.stripe.com https://hooks.stripe.com https://www.youtube.com;"
        }
      ]
    }
  ],
  "rewrites": [
    { "source": "/sitemap.xml", "destination": "/sitemap.xml" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**Verify after Vercel deploy:** open the production site, confirm DevTools → Network → response headers include `Content-Security-Policy`, and confirm the `/sitemap.xml` rewrite serves the generated XML (the `vite-plugin-sitemap` plugin emits it at build time).

#### 2. Vercel Environment Variables (Customer Site)

| Variable | Purpose |
|----------|---------|
| `VITE_API_URL` | Should already be set to `https://grinsirrigationplatform-production.up.railway.app` |
| `VITE_GA4_MEASUREMENT_ID` | Google Analytics 4 measurement ID — verify present |
| `VITE_GTM_CONTAINER_ID` | Google Tag Manager container ID — verify present |

These already exist on Vercel — verify the values and that no new env var was required (confirmed: only `vercel.json` + `vite.config.ts` + content/components changed).

#### 3. Lead Form API Contract (Coordination Point)

The customer-site `frontend/api/leads.ts` proxy and `frontend/api/mcp.ts` MCP definition were updated to accept `address` instead of `zipCode`. They post `address` to the platform's `/api/v1/leads` endpoint. **The platform side already accepts `address` (migration #1, commit `4c6f2de` on the customer-site). Merging the customer site dev → main without the platform side already on production would still work** because the platform also keeps `zip_code` accepted for back-compat — but verify by running the public smoke test:

```bash
./scripts/smoke/test_public_lead.sh https://grinsirrigationplatform-production.up.railway.app
```

#### 4. New Onboarding Flow Coordination

The customer site's new `ServiceWeekPreferences` component (`frontend/src/features/onboarding/components/ServiceWeekPreferences.tsx`) reads `services_with_types` from `POST /api/v1/onboarding/verify-session` (added in commit `c1388e7`) and posts back `service_week_preferences` to `POST /api/v1/onboarding/complete-onboarding`. **Both the customer-site and platform sides must be in sync — merge platform first, verify the API responses include `services_with_types`, then merge the customer site.**

### Deploy Order

1. Merge `Grins_irrigation_platform` dev → main (this doc).
2. Verify the platform `/api/v1/onboarding/verify-session` and `/api/v1/leads` endpoints respond with the new shape (smoke tests in Step 10).
3. Merge `Grins_irrigation` (customer site) dev → main.
4. Wait for Vercel auto-deploy to complete.
5. Verify the customer site loads, lead form posts succeed, and onboarding completes end-to-end with the new ServiceWeekPreferences step.

---

## 17. Migration Rehearsal — 2026-04-14 8:30 PM CT

The full 31-migration chain was rehearsed against a copy of production data on dev's identically-configured Postgres before this revision was finalized. **Result: all 31 migrations applied cleanly, zero errors, all data preserved.**

### Setup

1. Snapshot of dev → `backups/dev-environment/dev_backup_20260414_201922.{dump,sql}` (rollback insurance, unused).
2. `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` on dev.
3. `pg_restore` of `backups/production_backup_20260414_195000.dump` into dev.
4. Confirmed dev = byte-mirror of prod 19:50: alembic head `20260328_110000`, 41 tables, 106 customers, 232 jobs, 105 service_agreements, 32 leads, 212 agreement_status_logs, 169 sms_consent_records, 213 stripe_webhook_events.
5. `DATABASE_URL=<dev-public> uv run alembic upgrade head` → applied all 31 migrations.

### Verification

| Check | Result |
|---|---|
| Final alembic head | `20260414_100900` ✅ |
| Migration #30 phone backfill | `updated=0 already_normalized=32 unparseable=0` ✅ |
| Total tables (41 prod + 9 new) | 50 ✅ |
| Customer / Job / Service-agreement counts preserved | 106 / 232 / 105 ✅ |
| All schema additions present (`jobs.on_my_way_at`, `time_tracking_metadata`, `service_agreements.service_week_preferences`, `customer_documents.sales_entry_id`, `sent_messages.provider_message_id`) | All confirmed via `information_schema` ✅ |
| Snapshot cols added by #24 then dropped by #26 | Only `service_week_preferences` remains on `service_agreements` ✅ |
| `job_confirmation_responses.status` widened to VARCHAR(50) (#31) | Confirmed ✅ |
| All 5 CHECK constraints contain new values (`'draft'`, `'scheduled'`, `'appointment_reschedule'`, `'appointment_cancellation'`, `'automated_notification'`) | Confirmed via `pg_get_constraintdef` ✅ |
| Tier descriptions updated to marketing copy (#25) | Confirmed in `service_agreement_tiers.included_services` ✅ |
| `UPDATE jobs SET status='scheduled'` accepts | Pass ✅ |
| `INSERT INTO appointments (..., status='draft')` accepts | Pass ✅ |
| `INSERT INTO sent_messages` with `'appointment_reschedule'`, `'appointment_cancellation'`, `'automated_notification'` accepts | Pass ✅ |
| `INSERT INTO job_confirmation_responses` with `status='reschedule_alternatives_received'` (35 chars) accepts | Pass ✅ |
| Dev backend `/health` after migration | 200, `database: connected` ✅ |
| Dev backend `/api/v1/auth/login` after migration | 200, valid JWT issued ✅ |

### Artefacts retained

- `backups/production_backup_20260414_195000.{dump,sql,xlsx}` — the pre-migration snapshot from prod.
- `backups/dev-environment/dev_backup_20260414_201922.{dump,sql}` — dev snapshot taken immediately before the rehearsal (proves what dev looked like before the test, restorable in one command).

### How to re-run before the actual prod deploy

If commits land between this rehearsal and the prod deploy, re-run the rehearsal — it's a ~3-minute procedure documented in `backups/BACKUP-INSTRUCTIONS.md` plus the steps above.

---

## 18. Late-Breaking Commits (post-rehearsal addendum)

Five commits landed on `dev` between the original commit `fc29282` and the rehearsal cutoff `edf04f3`. All are accounted for in this doc revision and the rehearsal:

| # | Commit | What it does | Migration / schema impact | In rehearsal? |
|---|--------|--------------|---------------------------|---------------|
| 1 | `4e2708e` | Migration #31 — widens `job_confirmation_responses.status` to VARCHAR(50) so the 35-char value `'reschedule_alternatives_received'` fits | Yes — added as migration #31 above | ✅ Applied + verified |
| 2 | `7d35162` | Docs only — E2E Testing Procedure runbook + bughunt findings | None | n/a (docs) |
| 3 | `e99454d` | Docs only — bughunt status updates after Sprint 1-7 + E2E | None | n/a (docs) |
| 4 | `88e471f` | **BUG-001 fix** — lead-form POST was returning 201 with a valid `lead_id` while the row silently rolled back. Fix: `submit_lead` now schedules SMS / email confirmations to a fresh-session `BackgroundTask` after commit, instead of inline inside the request transaction. Code-only — no schema change. | None | ✅ Code rides along with the merge; dev backend confirmed healthy after the rehearsal. **Recommended smoke test on prod after deploy:** `POST /api/v1/leads` with `sms_consent=true` and verify the row persists. |
| 5 | `edf04f3` | Docs only — marks BUG-001 fixed | None | n/a (docs) |

---

## Rollback Plan

### Quick Rollback (Code Only)

```bash
git checkout main
git revert --no-commit dev..HEAD
git commit -m "revert: roll back dev merge"
git push origin main
```

### Database Rollback

```bash
railway run uv run alembic downgrade 20260328_110000
```

**Warning:** This drops 8 new tables and renames columns back. All data in new tables will be lost.

### Environment Variables

Remove CallRail and SignWell variables only if fully reverting:
```bash
railway variables set SMS_PROVIDER=twilio
railway variables unset CALLRAIL_API_KEY CALLRAIL_ACCOUNT_ID CALLRAIL_COMPANY_ID CALLRAIL_TRACKING_NUMBER CALLRAIL_TRACKER_ID CALLRAIL_WEBHOOK_SECRET SIGNWELL_API_KEY SIGNWELL_WEBHOOK_SECRET
```
