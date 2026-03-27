# Deployment Instructions: Service Package Purchases

## 1. Database Changes

### New Tables (11 migrations)

Execute in order — each depends on the previous:

| # | Migration File | Revision ID | Table/Change |
|---|---------------|-------------|--------------|
| 1 | `20250702_100000_create_service_agreement_tiers.py` | `20250702_100000` | Creates `service_agreement_tiers` + seeds 6 tier records |
| 2 | `20250702_100100_create_service_agreements.py` | `20250702_100100` | Creates `service_agreements` |
| 3 | `20250702_100200_create_agreement_status_logs.py` | `20250702_100200` | Creates `agreement_status_logs` |
| 4 | `20250702_100300_create_stripe_webhook_events.py` | `20250702_100300` | Creates `stripe_webhook_events` |
| 5 | `20250702_100400_create_disclosure_records.py` | `20250702_100400` | Creates `disclosure_records` (INSERT-ONLY) |
| 6 | `20250702_100500_create_sms_consent_records.py` | `20250702_100500` | Creates `sms_consent_records` (INSERT-ONLY) |
| 7 | `20250702_100600_create_email_suppression_list.py` | `20250702_100600` | Creates `email_suppression_list` |
| 8 | `20250702_100700_add_job_agreement_fields.py` | `20250702_100700` | Adds `service_agreement_id`, `target_start_date`, `target_end_date` to `jobs` |
| 9 | `20250702_100800_add_customer_agreement_fields.py` | `20250702_100800` | Adds Stripe, consent, email opt-in fields to `customers` |
| 10 | `20250702_100900_add_lead_extension_fields.py` | `20250702_100900` | Adds `lead_source`, `source_detail`, `intake_tag`, `sms_consent`, `terms_accepted` to `leads` |
| 11 | `20250702_101000_add_work_request_promotion_fields.py` | `20250702_101000` | Adds `promoted_to_lead_id`, `promoted_at` to `google_sheet_submissions` |

### Execution Command

```bash
uv run alembic upgrade head
```

Or to apply only these migrations:

```bash
uv run alembic upgrade 20250702_101000
```

### Seed Data

Migration `20250702_100000` seeds the initial 6 tiers, `20250710_100500` adds 2 winterization tiers, and `20260325_100000` updates all 8 tiers to current pricing with Stripe IDs.

After all migrations, the 8 tiers are:

| Tier | Package Type | Annual Price | Stripe Product (Test) | Stripe Price (Test) |
|------|-------------|-------------|----------------------|---------------------|
| Essential | Residential | $175.00 | `prod_U6ibkYyfakHQE3` | `price_1TF2nBQDNzCTp6j5u43DTExH` |
| Professional | Residential | $260.00 | `prod_U6icBhfGIvzqLx` | `price_1TF2nCQDNzCTp6j5sIB9OSH4` |
| Premium | Residential | $725.00 | `prod_U6icN6YaatjlVG` | `price_1TF2nCQDNzCTp6j5SC24GCKa` |
| Essential | Commercial | $235.00 | `prod_U6idaMQy8AHkat` | `price_1TF2nEQDNzCTp6j53W5uUqfi` |
| Professional | Commercial | $390.00 | `prod_U6ifaZT4doEALs` | `price_1TF2nFQDNzCTp6j5rhmqYTlJ` |
| Premium | Commercial | $880.00 | `prod_U6ihXIsrjf83X4` | `price_1TF2nGQDNzCTp6j5zWieKL0w` |
| Winterization Only | Residential | $85.00 | `prod_U8EJ1WraZBMrYV` | `price_1TF2nDQDNzCTp6j5KmY0goPa` |
| Winterization Only | Commercial | $105.00 | `prod_U8EJGKEoPiYUWN` | `price_1TF2nGQDNzCTp6j5Cieln9IO` |

**Note:** The test Stripe IDs above are populated by migration `20260325_100000`. For production, you must create new products/prices in the live Stripe account and update the database (see Section 4).

### Verify Seed Data

```bash
uv run python -c "
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ['DATABASE_URL'].replace('+asyncpg', ''))
with engine.connect() as conn:
    rows = conn.execute(text('SELECT name, slug, package_type, annual_price FROM service_agreement_tiers ORDER BY display_order'))
    for r in rows:
        print(f'{r.name} ({r.package_type}): \${r.annual_price}')
"
```

---

## 2. Environment Variables

### Backend (Railway)

#### Core (required for app to start)

| Variable | Description | Required | Example |
|----------|------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `JWT_SECRET_KEY` | JWT signing secret (min 32 chars in production) | Yes | `<random-64-char-string>` |
| `CORS_ORIGINS` | Comma-separated allowed origins | Yes | `https://frontend.vercel.app,https://admin.vercel.app` |

#### Stripe

| Variable | Description | Required | Example |
|----------|------------|----------|---------|
| `STRIPE_SECRET_KEY` | Stripe API secret key | Yes | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook endpoint signing secret | Yes | `whsec_...` |
| `STRIPE_CUSTOMER_PORTAL_URL` | Stripe Customer Portal URL | Yes | `https://billing.stripe.com/p/login/...` |
| `STRIPE_TAX_ENABLED` | Enable Stripe Tax automatic calculation | No (default: `true`) | `true` |

#### Email & Compliance

| Variable | Description | Required | Example |
|----------|------------|----------|---------|
| `EMAIL_API_KEY` | Email provider API key | Yes | `SG.xxx...` |
| `COMPANY_PHYSICAL_ADDRESS` | Physical address for CAN-SPAM compliance | Yes (for commercial emails) | `123 Main St, Minneapolis, MN 55401` |

**Behavior when missing:**
- `DATABASE_URL` / `JWT_SECRET_KEY` missing: app will not start
- `CORS_ORIGINS` missing: defaults to localhost only — frontend requests will be blocked
- `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` missing: logs warning, payment features disabled (app still starts)
- `EMAIL_API_KEY` missing: emails recorded as `sent_via="pending"` with `delivery_confirmed=false`
- `COMPANY_PHYSICAL_ADDRESS` missing: commercial emails refused (transactional emails still sent)

### Frontend (Vercel)

| Variable | Description | Required | Example |
|----------|------------|----------|---------|
| `VITE_API_BASE_URL` | Backend API base URL | Yes | `https://api.grinsirrigations.com` |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | Yes | `pk_live_...` |
| `VITE_STRIPE_CUSTOMER_PORTAL_URL` | Stripe Customer Portal link (per-environment) | Yes | `https://billing.stripe.com/p/login/...` |

**Per-environment portal URLs (set in Vercel):**
- **Preview (dev branch):** `https://billing.stripe.com/p/login/test_6oU8wR0zu8QUcQ4amueQM00`
- **Production:** `https://billing.stripe.com/p/login/00gaEXaaqack8zGa7N5Ne00`

---

## 3. New Dependencies

### Python Packages (pyproject.toml)

| Package | Version | Purpose |
|---------|---------|---------|
| `stripe` | `>=8.0.0` | Stripe payment integration |
| `apscheduler` | `>=3.10.0,<4.0.0` | Background job scheduling |
| `jinja2` | `>=3.1.0` | Email template rendering |

Install:

```bash
uv sync
```

### npm Packages (frontend/package.json)

| Package | Version | Purpose |
|---------|---------|---------|
| `recharts` | `^3.8.0` | MRR and tier distribution charts |

Install:

```bash
cd frontend && npm install
```

---

## 4. Stripe Configuration

### 4a. Test Environment (Already Configured)

The test/dev Stripe account already has all 8 products, prices, and webhook configured.
Migration `20260325_100000` populates the test Stripe IDs into the database automatically.

**Test webhook endpoint:** `https://grins-dev-dev.up.railway.app/api/v1/webhooks/stripe`

### 4b. Production Environment — Using the Stripe MCP Server

For production, use the Stripe MCP server in Claude Code to create products, prices, and verify configuration. Switch to the **live Stripe API key** before running these steps.

#### Step 1: Create Products (via MCP `create_product`)

Create 8 products in the live Stripe account:

| # | Product Name | Description |
|---|-------------|-------------|
| 1 | Residential Essential Package | Annual residential plan: Spring Start-Up, Fall Winterization, and Controller Programming. |
| 2 | Residential Professional Package | Annual residential plan: Everything in Essential plus 1 Mid-Season Inspection & Tune-Up, Priority Scheduling, and 10% Off Repairs. |
| 3 | Residential Premium Package | Annual residential plan: Everything in Professional plus 4 Monthly Monitoring Visits, 15% Off Repairs, Emergency Service, Free Consultations, and No Service Call Fees. |
| 4 | Commercial Essential Package | Annual commercial plan: Spring Start-Up, Fall Winterization, and Controller Programming. |
| 5 | Commercial Professional Package | Annual commercial plan: Everything in Essential plus 1 Mid-Season Inspection & Tune-Up, Priority Scheduling, and 10% Off Repairs. |
| 6 | Commercial Premium Package | Annual commercial plan: Everything in Professional plus 4 Monthly Monitoring Visits, 15% Off Repairs, Emergency Service, Free Consultations, and No Service Call Fees. |
| 7 | Winterization Only Residential | Single fall winterization for residential properties |
| 8 | Winterization Only Commercial | Single fall winterization for commercial properties |

#### Step 2: Create Prices (via MCP `create_price`)

Create a recurring annual price for each product:

| Product | Amount (cents) | Currency | Recurring Interval |
|---------|---------------|----------|-------------------|
| Residential Essential | 17500 | usd | year |
| Residential Professional | 26000 | usd | year |
| Residential Premium | 72500 | usd | year |
| Commercial Essential | 23500 | usd | year |
| Commercial Professional | 39000 | usd | year |
| Commercial Premium | 88000 | usd | year |
| Winterization Only Residential | 8500 | usd | year |
| Winterization Only Commercial | 10500 | usd | year |

#### Step 3: Verify Products & Prices (via MCP `list_products` / `list_prices`)

Run `list_products` and `list_prices` to confirm all 8 products and prices were created correctly.

#### Step 4: Update Database with Production Stripe IDs

After creating the live products and prices, update the `service_agreement_tiers` table with the production Stripe IDs:

```sql
-- Replace prod_xxx / price_xxx with actual live Stripe IDs from Step 3
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'essential-residential';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'professional-residential';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'premium-residential';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'essential-commercial';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'professional-commercial';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'premium-commercial';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'winterization-only-residential';
UPDATE service_agreement_tiers SET stripe_product_id = 'prod_xxx', stripe_price_id = 'price_xxx' WHERE slug = 'winterization-only-commercial';
```

**Important:** Tiers with `stripe_price_id = NULL` will return HTTP 503 on checkout session creation.

### 4c. Webhook Endpoint

| Setting | Value |
|---------|-------|
| URL | `https://<production-backend-domain>/api/v1/webhooks/stripe` |
| API Version | Match your `stripe` library version |

#### Required Webhook Events

Subscribe to these 6 events:

1. `checkout.session.completed`
2. `invoice.paid`
3. `invoice.payment_failed`
4. `invoice.upcoming`
5. `customer.subscription.updated`
6. `customer.subscription.deleted`

**Note:** The webhook endpoint must be configured manually in the Stripe Dashboard (Developers → Webhooks → Add endpoint). The MCP server does not currently support webhook management. Copy the signing secret to `STRIPE_WEBHOOK_SECRET` in Railway.

### 4d. Customer Portal

1. Enable the Stripe Customer Portal in Stripe Dashboard → Settings → Billing → Customer Portal
2. Configure allowed actions: update payment method, cancel subscription
3. Copy the portal link to `STRIPE_CUSTOMER_PORTAL_URL` (Railway) and `VITE_STRIPE_CUSTOMER_PORTAL_URL` (Vercel)
4. Set **different portal URLs per environment** in Vercel (see Section 2, Frontend table)

### 4e. Stripe Tax

If `STRIPE_TAX_ENABLED=true` (default), ensure Stripe Tax is configured:
1. Stripe Dashboard → Settings → Tax
2. Set tax registration for Minnesota
3. Enable automatic tax calculation

### 4f. Invoice Upcoming Timing

Stripe sends `invoice.upcoming` ~3 days before renewal by default. To adjust:
- Stripe Dashboard → Settings → Billing → Subscriptions → Days before renewal to send upcoming invoice event

### 4g. Price Reference — Test vs Production

| Tier | Test Price ID | Production Price ID |
|------|--------------|-------------------|
| Essential Residential ($175/yr) | `price_1TF2nBQDNzCTp6j5u43DTExH` | _TBD — set after Step 2_ |
| Professional Residential ($260/yr) | `price_1TF2nCQDNzCTp6j5sIB9OSH4` | _TBD_ |
| Premium Residential ($725/yr) | `price_1TF2nCQDNzCTp6j5SC24GCKa` | _TBD_ |
| Essential Commercial ($235/yr) | `price_1TF2nEQDNzCTp6j53W5uUqfi` | _TBD_ |
| Professional Commercial ($390/yr) | `price_1TF2nFQDNzCTp6j5rhmqYTlJ` | _TBD_ |
| Premium Commercial ($880/yr) | `price_1TF2nGQDNzCTp6j5zWieKL0w` | _TBD_ |
| Winterization Only Residential ($85/yr) | `price_1TF2nDQDNzCTp6j5KmY0goPa` | _TBD_ |
| Winterization Only Commercial ($105/yr) | `price_1TF2nGQDNzCTp6j5Cieln9IO` | _TBD_ |

---

## 5. Infrastructure Changes

### APScheduler (Background Jobs)

The application now starts an APScheduler `BackgroundScheduler` on FastAPI lifespan startup. Four jobs are registered:

| Job ID | Schedule | Description |
|--------|----------|-------------|
| `escalate_failed_payments` | Daily at 2:00 AM | Pauses agreements PAST_DUE ≥7 days, cancels PAUSED ≥14 days |
| `check_upcoming_renewals` | Daily at 9:00 AM | Alerts for approaching renewal dates |
| `send_annual_notices` | Daily at 10:00 AM | Sends MN auto-renewal annual notices (active in January) |
| `cleanup_orphaned_consent_records` | Weekly (Sunday 3:00 AM) | Marks consent records >30 days with no linked customer as abandoned |

**Note:** APScheduler uses in-memory job store (not PostgreSQL). Jobs are re-registered on each application restart. No additional infrastructure required.

### Email Service

- 6 Jinja2 email templates in `src/grins_platform/templates/emails/`:
  - `welcome.html`, `confirmation.html`, `renewal_notice.html`, `annual_notice.html`, `cancellation_conf.html`, `lead_confirmation.html`
- Transactional emails sent from `noreply@` sender
- Commercial emails sent from `info@` sender with physical address and unsubscribe link
- Public unsubscribe endpoint: `GET /api/v1/email/unsubscribe?token=<signed-token>`

### DNS Records (if using custom email domain)

Configure SPF, DKIM, and DMARC records for the email sending domain to ensure deliverability.

---

## 6. New API Endpoints

### Public (No Auth)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/onboarding/pre-checkout-consent` | Pre-checkout consent (rate-limited 5/IP/min) |
| POST | `/api/v1/checkout/create-session` | Create Stripe Checkout session (rate-limited 5/IP/min) |
| GET | `/api/v1/onboarding/verify-session` | Verify Stripe session |
| POST | `/api/v1/onboarding/complete` | Complete onboarding with property data |
| POST | `/api/v1/webhooks/stripe` | Stripe webhook receiver (signature-verified via `STRIPE_WEBHOOK_SECRET`) |
| GET | `/api/v1/email/unsubscribe` | Email unsubscribe |

### Authenticated (Admin)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/agreements` | List agreements (filterable) |
| GET | `/api/v1/agreements/{id}` | Agreement detail |
| PATCH | `/api/v1/agreements/{id}/status` | Update agreement status |
| PATCH | `/api/v1/agreements/{id}/notes` | Update agreement notes |
| POST | `/api/v1/agreements/{id}/approve-renewal` | Approve renewal |
| POST | `/api/v1/agreements/{id}/reject-renewal` | Reject renewal |
| GET | `/api/v1/agreements/metrics/summary` | Agreement metrics (MRR, ARPA, etc.) |
| GET | `/api/v1/agreements/metrics/mrr-history` | MRR history (trailing 12 months) |
| GET | `/api/v1/agreements/metrics/tier-distribution` | Agreements by tier |
| GET | `/api/v1/agreements/queues/renewal-pipeline` | Renewal pipeline queue |
| GET | `/api/v1/agreements/queues/failed-payments` | Failed payments queue |
| GET | `/api/v1/agreements/queues/annual-notice-due` | Annual notice due queue |
| GET | `/api/v1/agreement-tiers` | List active tiers |
| GET | `/api/v1/agreement-tiers/{id}` | Tier detail |
| GET | `/api/v1/agreements/{id}/compliance` | Agreement compliance records |
| GET | `/api/v1/compliance/customer/{customer_id}` | Customer compliance records |
| GET | `/api/v1/dashboard/summary` | Extended dashboard summary |
| POST | `/api/v1/leads/from-call` | Create lead from phone call |
| GET | `/api/v1/leads/follow-up-queue` | Follow-up queue |
| GET | `/api/v1/leads/metrics/by-source` | Lead metrics by source |

---

## 7. Deployment Order

1. **Set environment variables** on Railway and Vercel (Section 2), including `VITE_STRIPE_CUSTOMER_PORTAL_URL` per environment
2. **Install dependencies**: `uv sync` (backend), `npm install` (frontend)
3. **Run database migrations**: `uv run alembic upgrade head` (populates test Stripe IDs automatically)
4. **Verify seed data** — confirm all 8 tiers with prices (Section 1 verify command)
5. **Create production Stripe Products/Prices** using the Stripe MCP server (Section 4b, Steps 1–3)
6. **Update database** with production Stripe IDs (Section 4b, Step 4)
7. **Configure Stripe webhook** endpoint in Stripe Dashboard with the 6 required events (Section 4c)
8. **Configure Stripe Customer Portal** and set `STRIPE_CUSTOMER_PORTAL_URL` / `VITE_STRIPE_CUSTOMER_PORTAL_URL` (Section 4d)
9. **Configure Stripe Tax** for Minnesota (Section 4e)
10. **Deploy backend** (Railway)
11. **Deploy frontend** (Vercel)
12. **Run post-deployment verification** (Section 8)

---

## 8. Post-Deployment Verification

### Backend Health

```bash
curl -s https://<backend-domain>/health | python -m json.tool
```

### API Endpoint Smoke Tests

```bash
# List tiers (should return 8)
curl -s https://<backend-domain>/api/v1/agreement-tiers | python -m json.tool

# Dashboard summary (should include agreement + lead metrics)
curl -s -H "Authorization: Bearer <token>" https://<backend-domain>/api/v1/dashboard/summary | python -m json.tool

# Agreement metrics
curl -s -H "Authorization: Bearer <token>" https://<backend-domain>/api/v1/agreements/metrics/summary | python -m json.tool

# Follow-up queue
curl -s -H "Authorization: Bearer <token>" https://<backend-domain>/api/v1/leads/follow-up-queue | python -m json.tool

# Lead metrics by source
curl -s -H "Authorization: Bearer <token>" https://<backend-domain>/api/v1/leads/metrics/by-source | python -m json.tool
```

### Stripe Webhook Test

Use Stripe CLI to send a test event:

```bash
stripe trigger checkout.session.completed --webhook-endpoint https://<backend-domain>/api/v1/webhooks/stripe
```

### Agent-Browser UI Validation

Run the validation scripts from `scripts/agent-browser/`:

```bash
# Agreements tab
bash scripts/agent-browser/validate-agreements-tab.sh

# Agreement detail
bash scripts/agent-browser/validate-agreement-detail.sh

# Operational queues
bash scripts/agent-browser/validate-operational-queues.sh

# Dashboard modifications
bash scripts/agent-browser/validate-dashboard-modifications.sh

# Jobs tab modifications
bash scripts/agent-browser/validate-jobs-tab-modifications.sh

# Leads tab modifications
bash scripts/agent-browser/validate-leads-tab-modifications.sh
```

---

# DO NOT RUN BELOW STEPS THIS IS ONLY FOR MANUAL REFERENCE NOT FOR EXECUTION
<!-- ## 9. Rollback Instructions

### Step 1: Deactivate Stripe Webhook

Disable or delete the webhook endpoint in Stripe Dashboard to stop event delivery.

### Step 2: Stop Background Scheduler

The scheduler stops automatically on application shutdown. No separate action needed.

### Step 3: Rollback Database Migrations

Roll back all 11 migrations (back to the pre-feature state):

```bash
uv run alembic downgrade 20250701_100000
```

This will:
- Drop `service_agreement_tiers`, `service_agreements`, `agreement_status_logs`, `stripe_webhook_events`, `disclosure_records`, `sms_consent_records`, `email_suppression_list` tables
- Remove added columns from `jobs`, `customers`, `leads`, `google_sheet_submissions`

**Warning:** This is destructive — all agreement, compliance, and consent data will be lost. Back up the database first.

### Step 4: Remove Environment Variables

Remove from Railway:
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_CUSTOMER_PORTAL_URL`, `STRIPE_TAX_ENABLED`
- `EMAIL_API_KEY`, `COMPANY_PHYSICAL_ADDRESS`

Remove from Vercel:
- `VITE_STRIPE_PUBLISHABLE_KEY`

### Step 5: Redeploy

Deploy the previous backend and frontend versions without the service-package-purchases feature code. -->
