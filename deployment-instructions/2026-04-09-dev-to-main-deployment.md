# Deployment Instructions: dev → main (April 9, 2026)

**Date:** April 9, 2026
**Source branch:** `dev`
**Target branch:** `main`
**Commits:** 27 commits (f308749..1c67bb3)

---

## Summary

This deployment brings four major feature areas from dev to production:

1. **CallRail SMS Integration** — New SMS provider replacing Twilio, with provider abstraction layer
2. **Scheduling Poll & Response Collection** — Send date-range polls via SMS, collect and export responses
3. **Communications Dashboard Overhaul** — Campaign creation wizard, CSV audience upload, draft editing, campaign lifecycle management
4. **Google Sheets Pipeline Fix** — Header-based column mapping for the restructured form

---

## Pre-Deployment Checklist

- [ ] Back up the production database
- [ ] Verify CallRail account credentials are ready (API key, account ID, company ID, tracker ID)
- [ ] Generate webhook secret: `openssl rand -hex 32`
- [ ] Confirm Redis is available (or provision one on Railway)
- [ ] Coordinate with team — campaign worker will start processing pending recipients within 60s of deploy

---

## 1. Database Migrations (10 new migrations)

### Migration Chain

The production DB head is currently at `20260328_110000`. This deploy adds 10 sequential migrations:

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

> **Note:** Migration #10 (`20260410_100100`) is currently untracked locally. It must be committed to dev before merging to main.

### New Table: `campaign_responses`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | No | PK, gen_random_uuid() |
| `campaign_id` | UUID | Yes | FK → campaigns.id (SET NULL) |
| `sent_message_id` | UUID | Yes | FK → sent_messages.id (SET NULL) |
| `customer_id` | UUID | Yes | FK → customers.id (SET NULL) |
| `lead_id` | UUID | Yes | FK → leads.id (SET NULL) |
| `phone` | String(32) | No | |
| `recipient_name` | String(200) | Yes | |
| `recipient_address` | Text | Yes | |
| `selected_option_key` | String(8) | Yes | |
| `selected_option_label` | Text | Yes | |
| `raw_reply_body` | Text | No | |
| `provider_message_id` | String(100) | Yes | Unique partial index (WHERE NOT NULL) |
| `status` | String(20) | No | CHECK: 'parsed', 'needs_review', 'opted_out', 'orphan' |
| `received_at` | DateTime(tz) | No | |
| `created_at` | DateTime(tz) | No | server_default: now() |

### Column Renames (Breaking for raw SQL queries)

| Table | Old Column | New Column |
|-------|-----------|------------|
| `sent_messages` | `twilio_sid` | `provider_message_id` |
| `campaign_recipients` | `status` | `delivery_status` |
| `campaign_recipients` | `delivered_at` | `sent_at` |

### Running Migrations

Migrations run automatically on app startup via Alembic. To run manually:

```bash
# On Railway
railway run uv run alembic upgrade head

# Verify head
railway run uv run alembic current
# Expected: 20260410_100100 (head)
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
| `CALLRAIL_TRACKER_ID` | `<from CallRail dashboard>` | Tracker identifier |
| `CALLRAIL_WEBHOOK_SECRET` | `<openssl rand -hex 32>` | HMAC signing secret for inbound webhooks |

### New Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMS_PROVIDER` | `callrail` | Provider selection: `callrail`, `twilio`, or `null` |
| `SMS_SENDER_PREFIX` | `Grins Irrigation: ` | Prefix prepended to all outbound SMS |
| `SMS_TEST_PHONE_ALLOWLIST` | *(unset)* | Comma-separated phone numbers allowed to receive SMS. **Leave unset in production** to allow all recipients. Set in staging to restrict sends. |
| `REDIS_URL` | *(unset)* | Redis connection URL for rate-limit tracking, webhook dedup, and worker health. **Strongly recommended** — system degrades gracefully without it but loses dedup and rate-limit caching. |
| `ENVIRONMENT` | `development` | Set to `production` for secure cookies, proper CORS, etc. (likely already set) |

### Setting Variables on Railway

```bash
railway variables set \
  CALLRAIL_API_KEY=<key> \
  CALLRAIL_ACCOUNT_ID=<id> \
  CALLRAIL_COMPANY_ID=<id> \
  CALLRAIL_TRACKING_NUMBER=+19525293750 \
  CALLRAIL_TRACKER_ID=<tracker-id> \
  CALLRAIL_WEBHOOK_SECRET=<generated-secret> \
  SMS_PROVIDER=callrail \
  REDIS_URL=<redis-url>
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

## 5. New API Endpoints

### Public (No Auth)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/webhooks/callrail/inbound` | CallRail inbound SMS webhook (HMAC-verified) |
| POST | `/api/v1/checkout/create-session` | Create Stripe checkout session (rate-limited) |
| POST | `/api/v1/checkout/manage-subscription` | Send subscription management email (rate-limited) |

### Authenticated (Manager or Admin)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/campaigns/worker-health` | Campaign worker health status |
| POST | `/api/v1/campaigns/audience/preview` | Preview matched recipients |
| PATCH | `/api/v1/campaigns/{id}` | Update draft campaign |
| POST | `/api/v1/campaigns/{id}/cancel` | Cancel a campaign |
| POST | `/api/v1/campaigns/{id}/retry-failed` | Retry failed recipients |
| GET | `/api/v1/campaigns/{id}/recipients` | List campaign recipients |
| GET | `/api/v1/campaigns/{id}/responses/summary` | Poll response summary (bucket counts) |
| GET | `/api/v1/campaigns/{id}/responses` | List poll responses (paginated) |
| GET | `/api/v1/campaigns/{id}/responses/export.csv` | Export responses as CSV |

### Authenticated (Admin Only)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/campaigns/audience/csv` | Upload CSV audience file |

### Authorization Changes

- Campaign creation: elevated from `CurrentActiveUser` → `ManagerOrAdminUser`
- Campaign send: now requires `require_campaign_send_authority` (managers ≤ 50 recipients, admins unlimited)
- Campaign delete: elevated to `AdminUser` only; restricted to draft/cancelled campaigns

---

## 6. Frontend Changes (Vercel)

### New Pages/Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/portal/manage-subscription` | `SubscriptionManagementPage` | Customer self-service subscription management |

### Updated Components

- **CommunicationsDashboard** — Complete overhaul with campaign list, creation wizard, poll options editor
- **AudienceBuilder** — New component for selecting recipients (customer/lead filters + CSV upload)
- **CampaignReview** — Pre-send review screen with segment counter and recipient preview
- **CampaignResponsesView** — View/filter/export poll responses
- **FailedRecipientsDetail** — View and retry failed campaign recipients
- **LeadsList** — Added Google Sheets sync button and auto-refresh
- **CustomerList** — Updated with new filter capabilities

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

## 7. Background Jobs / Campaign Worker

A new background job runs **every 60 seconds** inside the FastAPI process:

| Job | Schedule | Description |
|-----|----------|-------------|
| `process_pending_campaign_recipients` | Every 60s | Picks up pending campaign recipients and sends SMS via CallRail |

### Behavior

- **Time window:** Only sends during 8 AM – 9 PM CT (hardcoded)
- **Batch size:** Max 2 recipients per tick (stays under 140 SMS/hour rate limit)
- **Rate-limit aware:** Reads `x-rate-limit-*` headers from CallRail responses
- **Health endpoint:** `GET /api/v1/campaigns/worker-health` shows last tick, pending count, rate-limit state

### No Separate Worker Needed

The scheduler runs in-process via APScheduler in the FastAPI lifespan. No additional Procfile, Railway service, or worker dyno is required.

### Monitoring

```bash
# Watch campaign worker ticks
railway logs --filter "campaign.worker"

# Check worker health via API
curl -H "Cookie: ..." https://<domain>/api/v1/campaigns/worker-health
```

---

## 8. SMS Provider Switchover

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

## 9. No Dependency Changes

- **Python:** No changes to `pyproject.toml` — no new packages to install
- **Frontend:** No changes to `package.json` — no new npm packages

---

## Deployment Steps (Ordered)

### Step 1: Set Environment Variables on Railway

Set all required CallRail variables and REDIS_URL **before** deploying code.

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
INFO  [alembic.runtime.migration] Running upgrade ... -> 20260410_100100
```

Or verify manually:
```bash
railway run uv run alembic current
# Should show: 20260410_100100 (head)
```

### Step 5: Verify App Startup

Check logs for:
```
app.sms_provider_resolved provider=callrail
app.startup_completed
```

### Step 6: Configure CallRail Webhook

Follow [callrail-webhook-setup.md](./callrail-webhook-setup.md) — point the webhook URL to the production Railway domain.

### Step 7: Verify Vercel Frontend

Vercel should auto-deploy from main. Verify:
- Communications dashboard loads at `/communications`
- Campaign creation wizard works (draft mode)
- Subscription management page loads at `/portal/manage-subscription`

### Step 8: Post-Deploy Smoke Tests

1. **Campaign worker running:** Hit `GET /api/v1/campaigns/worker-health` — status should be `"healthy"`
2. **Inbound webhook working:** Send a test SMS to `+19525293750` — check logs for `sms.webhook.inbound`
3. **Google Sheets sync:** Click "Sync Sheets" on the Leads page — verify new submissions appear
4. **Campaign create/send flow:** Create a draft campaign, add audience, review, and send (use test phone only)

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

**Warning:** This drops the `campaign_responses` table and renames columns back. Any data in the new table will be lost.

### Environment Variables

Remove CallRail variables only if fully reverting to Twilio:
```bash
railway variables set SMS_PROVIDER=twilio
railway variables unset CALLRAIL_API_KEY CALLRAIL_ACCOUNT_ID CALLRAIL_COMPANY_ID CALLRAIL_TRACKING_NUMBER CALLRAIL_TRACKER_ID CALLRAIL_WEBHOOK_SECRET
```
