# Deployment Instructions: dev → main (April 9, 2026)

**Date:** April 9, 2026 (updated April 13, 2026)
**Source branch:** `dev`
**Target branch:** `main`
**Commits:** 44 commits (f308749..7b882a3)

---

## Summary

This deployment brings seven major feature areas from dev to production:

1. **CallRail SMS Integration** — New SMS provider replacing Twilio, with provider abstraction layer
2. **Scheduling Poll & Response Collection** — Send date-range polls via SMS, collect and export responses
3. **Communications Dashboard Overhaul** — Campaign creation wizard, CSV audience upload, draft editing, campaign lifecycle management
4. **Google Sheets Pipeline Fix** — Header-based column mapping for the restructured form
5. **CRM Changes Update 2** — Sales pipeline, contract renewals, customer merge detection, document management, property type tagging, job confirmation flow
6. **SignWell E-Signature Integration** — Email and embedded document signing for sales pipeline contracts
7. **Dashboard & Onboarding Enhancements** — Removed Estimates/New Leads sections, added services_with_types to onboarding verify-session

---

## Pre-Deployment Checklist

- [ ] Back up the production database
- [ ] Verify CallRail account credentials are ready (API key, account ID, company ID)
- [ ] Generate CallRail webhook secret: `openssl rand -hex 32`
- [ ] Obtain SignWell API key and webhook secret (if enabling e-signatures)
- [ ] Generate SignWell webhook secret: `openssl rand -hex 32`
- [ ] Confirm Redis is available (or provision one on Railway)
- [ ] Verify S3 bucket (`grins-platform-files`) is accessible — customer document uploads use it (no new config, reuses existing PhotoService)
- [ ] Coordinate with team — campaign worker will start processing pending recipients within 60s of deploy
- [ ] Coordinate with team — nightly duplicate detection sweep runs at 1:30 AM CT

---

## 1. Database Migrations (20 new migrations)

### Migration Chain

The production DB head is currently at `20260328_110000`. This deploy adds 20 sequential migrations:

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

### Running Migrations

Migrations run automatically on app startup via Alembic. To run manually:

```bash
# On Railway
railway run uv run alembic upgrade head

# Verify head
railway run uv run alembic current
# Expected: 20260412_100100 (head)
```

### Rollback

If something goes wrong, each migration has a `downgrade()` function:

```bash
# Roll back to the pre-deploy state
railway run uv run alembic downgrade 20260328_110000
```

**Warning:** Rolling back migration #4 (`rename_twilio_sid_to_provider_message_id`) is NOT idempotent — only roll back once.

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

### Vercel Configuration

No changes to `vercel.json` are required. The existing SPA rewrite rule handles all new routes:

```json
{ "source": "/((?!assets/).*)", "destination": "/index.html" }
```

### Vercel Environment Variables

Verify these are set (likely already configured):

| Variable | Value |
|----------|-------|
| `VITE_API_BASE_URL` | `https://grinsirrigationplatform-production.up.railway.app` |

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

## 12. No Dependency Changes

- **Python:** No new packages in `pyproject.toml` dependencies (only linting config changes)
- **Frontend:** No changes to `package.json` — no new npm packages

---

## Deployment Steps (Ordered)

### Step 1: Set Environment Variables on Railway

Set all required CallRail variables, SignWell variables, and REDIS_URL **before** deploying code.

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
INFO  [alembic.runtime.migration] Running upgrade ... -> 20260412_100100
```

Or verify manually:
```bash
railway run uv run alembic current
# Should show: 20260412_100100 (head)
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

### Step 9: Verify Vercel Frontend

Vercel should auto-deploy from main. Verify:
- Communications dashboard loads at `/communications`
- Campaign creation wizard works (draft mode)
- Subscription management page loads at `/portal/manage-subscription`
- Contract renewals page loads at `/contract-renewals`
- Sales pipeline page loads at `/sales`
- Dashboard no longer shows Estimates or New Leads sections

### Step 10: Post-Deploy Smoke Tests

1. **Campaign worker running:** Hit `GET /api/v1/campaigns/worker-health` — status should be `"healthy"`
2. **Inbound webhook working:** Send a test SMS to `+19525293750` — check logs for `sms.webhook.inbound`
3. **Google Sheets sync:** Click "Sync Sheets" on the Leads page — verify new submissions appear
4. **Campaign create/send flow:** Create a draft campaign, add audience, review, and send (use test phone only)
5. **Sales pipeline:** Create a test sales entry from a lead, verify it appears in the pipeline
6. **Contract renewals:** Verify the renewal proposals page loads and shows data (if any exist)
7. **Duplicate detection:** Check logs after 1:30 AM for `duplicate_detection` sweep results

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
