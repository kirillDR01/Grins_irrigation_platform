# Phase 14 Planning — Service Package Purchases & Admin Tracking

> End-to-end flow: Stripe package purchase → backend processing → admin dashboard tracking.
> Scoped to service packages only. References: `automation-blueprint.md` §3, §6, §9, §11, §12.

---

## Current State

**What exists today:**
- 6 Stripe Payment Links (test mode) on the landing page for 3 tiers × 2 types (residential/commercial)
- Landing page redirects to `?payment=success` after Stripe checkout → shows a "Thanks!" banner → dead end
- Backend has zero Stripe integration: no webhook endpoint, no `stripe` package, no Service Agreement model
- `Customer` model exists with `sms_opt_in`, `email_opt_in`, `lead_source`
- `Job` model exists with full status workflow (requested → approved → scheduled → in_progress → completed → closed)
- `ServiceOffering` model exists (service catalog with pricing)
- `Invoice` model exists with full status workflow
- `Property` model exists linked to customers
- Frontend admin dashboard has: Dashboard, Leads, Customers, Jobs, Schedule, Invoices, Work Requests, Staff tabs
- No `ServiceAgreementTier` or `ServiceAgreement` models
- No `service_agreement_id` on the Job model
- No `target_start_date` / `target_end_date` on the Job model

**What's broken:**
- Stripe purchases create zero records in the backend
- Viktor must manually check Stripe dashboard to know someone purchased
- No way to track which customers are subscribers vs one-off
- No seasonal job auto-generation from package purchases
- No renewal tracking, no failed payment handling

---

## Phase 14 Scope

This phase builds the **backend-to-frontend pipeline for service package purchases**. It does NOT include:
- Landing page changes (pre-checkout modal, post-purchase onboarding form) — separate phase, different repo
- Compliance tables (`sms_consent_records`, `disclosure_records`) — separate phase
- Automated communication sequences (SMS/email triggers) — separate phase
- Estimate entity — separate phase
- AI conversational agent — separate phase

### What Phase 14 Delivers

1. **Backend**: Stripe webhook endpoint that processes `checkout.session.completed` and creates Customer + ServiceAgreement + seasonal Jobs
2. **Backend**: ServiceAgreementTier and ServiceAgreement models with full status lifecycle
3. **Backend**: CRUD API for service agreements (list, detail, status transitions, renewal approval)
4. **Backend**: Seasonal job auto-generation logic based on package tier
5. **Backend**: Stripe subscription lifecycle webhooks (`invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`, `invoice.upcoming`)
6. **Frontend**: Service Agreements tab in admin dashboard with business metrics + operational queues
7. **Frontend**: Agreement detail view with linked jobs timeline, payment history, status actions
8. **Frontend**: Dashboard widgets for Active Agreements, MRR, Renewal Pipeline, Failed Payments
9. **Frontend**: Job model updates showing subscription source indicator + target date filtering

---

## Architecture Overview

```
Stripe Checkout (customer pays on landing page)
       │
       ▼
POST /api/v1/webhooks/stripe  ← NEW endpoint
       │
       ├── checkout.session.completed
       │     → Match/create Customer (by email)
       │     → Create ServiceAgreement (status: PENDING)
       │     → Generate seasonal Jobs (status: APPROVED)
       │
       ├── invoice.paid
       │     → Agreement → ACTIVE
       │     → On renewal: generate next season's jobs
       │
       ├── invoice.payment_failed
       │     → Agreement → PAST_DUE
       │     → After retries exhausted: → PAUSED
       │
       ├── invoice.upcoming
       │     → Agreement → PENDING_RENEWAL
       │     → Add to renewal pipeline queue
       │
       └── customer.subscription.deleted
             → Agreement → CANCELLED
             → Cancel future unscheduled jobs

Admin Dashboard (frontend)
       │
       ├── Service Agreements tab (NEW)
       │     → Business metrics (Active, MRR, Renewal Rate, Churn)
       │     → Operational queues (Renewal Pipeline, Failed Payments, Unscheduled Visits)
       │     → Agreement list with status tabs
       │     → Agreement detail with jobs timeline
       │
       ├── Dashboard tab (MODIFIED)
       │     → New widgets: Active Agreements, MRR, Renewal Pipeline count
       │
       └── Jobs tab (MODIFIED)
             → Source indicator: "Subscription" badge
             → Target date range filtering
```

---

## Data Model Changes

### New: `ServiceAgreementTier` (template table)

Defines what each package includes. Rarely changes. Seeded with the 6 current packages.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| name | VARCHAR(100) | "Essential", "Professional", "Premium" |
| slug | VARCHAR(50) UNIQUE | "essential", "professional", "premium" |
| description | TEXT | |
| package_type | ENUM | RESIDENTIAL / COMMERCIAL |
| annual_price | DECIMAL(10,2) | $170/$250/$700 (res) or $225/$375/$850 (com) |
| billing_frequency | ENUM | ANNUAL (only option for now) |
| included_services | JSONB | Array of `{ service_type, frequency, description }` |
| perks | JSONB | Array of perk strings |
| stripe_product_id | VARCHAR(255) | Stripe Product ID |
| stripe_price_id | VARCHAR(255) | Stripe Price ID (recurring annual) |
| is_active | BOOLEAN | Default true |
| display_order | INTEGER | Frontend sorting |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### New: `ServiceAgreement` (instance table)

A specific customer's subscription. One per customer per active subscription.

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| agreement_number | VARCHAR(50) UNIQUE | Auto-generated "AGR-YYYY-NNN" |
| customer_id | UUID FK → customers | |
| tier_id | UUID FK → service_agreement_tiers | |
| property_id | UUID FK → properties | Nullable, linked after onboarding |
| stripe_subscription_id | VARCHAR(255) | Stripe Subscription object ID |
| stripe_customer_id | VARCHAR(255) | Stripe Customer object ID |
| status | VARCHAR(30) | PENDING / ACTIVE / PAST_DUE / PAUSED / PENDING_RENEWAL / CANCELLED / EXPIRED |
| start_date | DATE | |
| end_date | DATE | start_date + 1 year |
| renewal_date | DATE | When Stripe attempts next charge |
| auto_renew | BOOLEAN | Default true |
| cancelled_at | TIMESTAMP | |
| cancellation_reason | TEXT | |
| pause_reason | TEXT | |
| annual_price | DECIMAL(10,2) | Locked at purchase time |
| payment_status | VARCHAR(20) | CURRENT / PAST_DUE / FAILED |
| last_payment_date | TIMESTAMP | |
| last_payment_amount | DECIMAL(10,2) | |
| renewal_approved_by | UUID FK → staff | Viktor's approval gate |
| renewal_approved_at | TIMESTAMP | |
| notes | TEXT | |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### New: `AgreementStatusLog` (audit trail)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID PK | |
| agreement_id | UUID FK → service_agreements | |
| old_status | VARCHAR(30) | |
| new_status | VARCHAR(30) | |
| changed_by | UUID FK → staff | Nullable (NULL = system-triggered) |
| reason | TEXT | |
| metadata | JSONB | Extra context (Stripe event ID, etc.) |
| created_at | TIMESTAMP | |

### Modified: `Job` model

| New Field | Type | Notes |
|-----------|------|-------|
| service_agreement_id | UUID FK → service_agreements | Nullable. Links subscription-generated jobs |
| target_start_date | DATE | Earliest scheduling date (e.g., Apr 1) |
| target_end_date | DATE | Latest scheduling date (e.g., Apr 30) |

### New Enums

```python
class AgreementStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    PENDING_RENEWAL = "pending_renewal"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PaymentStatus(str, Enum):
    CURRENT = "current"
    PAST_DUE = "past_due"
    FAILED = "failed"

class PackageType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"

class BillingFrequency(str, Enum):
    ANNUAL = "annual"
```

---

## Agreement Status Flow

```
PENDING (checkout completed, awaiting onboarding/activation)
  │
  ▼
ACTIVE (subscription current, jobs generated)
  │
  ├──→ PAST_DUE (invoice.payment_failed — Stripe retrying)
  │       ├──→ ACTIVE (retry succeeds)
  │       └──→ PAUSED (all retries failed, Day 7+)
  │               ├──→ ACTIVE (customer updates card, payment succeeds)
  │               └──→ CANCELLED (Day 21-30, no resolution)
  │
  ├──→ PENDING_RENEWAL (invoice.upcoming, awaiting Viktor's approval)
  │       ├──→ ACTIVE (approved + invoice.paid → new term + new jobs)
  │       └──→ EXPIRED (rejected or customer doesn't renew)
  │
  ├──→ CANCELLED (customer cancels — effective end of current term)
  │
  └──→ EXPIRED (term ended, did not renew)
        └──→ ACTIVE (win-back: customer re-subscribes)
```

---

## API Endpoints

### Stripe Webhook (public, signature-verified)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/webhooks/stripe` | Stripe signature | Process all Stripe events |

### Service Agreement Tiers (admin)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/agreement-tiers` | Admin | List all tiers |
| GET | `/api/v1/agreement-tiers/{id}` | Admin | Get tier detail |

### Service Agreements (admin)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/agreements` | Admin | List agreements (filterable by status, tier, customer) |
| GET | `/api/v1/agreements/{id}` | Admin | Agreement detail with linked jobs + payment history |
| PATCH | `/api/v1/agreements/{id}/status` | Admin | Status transitions (pause, resume, cancel) |
| POST | `/api/v1/agreements/{id}/approve-renewal` | Admin | Viktor approves renewal |
| POST | `/api/v1/agreements/{id}/reject-renewal` | Admin | Viktor rejects renewal |
| GET | `/api/v1/agreements/metrics` | Admin | Business KPIs (active count, MRR, renewal rate, churn) |
| GET | `/api/v1/agreements/renewal-pipeline` | Admin | Agreements pending renewal approval |
| GET | `/api/v1/agreements/failed-payments` | Admin | Agreements with failed payments |

### Dashboard (modified)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/v1/dashboard/summary` | Admin | Add agreement metrics to existing summary |

---

## Seasonal Job Generation Logic

When a `checkout.session.completed` webhook fires (or when agreement activates):

```
ESSENTIAL ($170 res / $225 com):
  → Job: "Spring Startup"         target: Apr 1 – Apr 30
  → Job: "Fall Winterization"     target: Oct 1 – Oct 31

PROFESSIONAL ($250 res / $375 com):
  → Job: "Spring Startup"         target: Apr 1 – Apr 30
  → Job: "Mid-Season Inspection"  target: Jul 1 – Jul 31
  → Job: "Fall Winterization"     target: Oct 1 – Oct 31

PREMIUM ($700 res / $850 com):
  → Job: "Spring Startup"         target: Apr 1 – Apr 30
  → Job: "Monthly Visit"          target: May 1 – May 31
  → Job: "Monthly Visit"          target: Jun 1 – Jun 30
  → Job: "Monthly Visit"          target: Jul 1 – Jul 31
  → Job: "Monthly Visit"          target: Aug 1 – Aug 31
  → Job: "Monthly Visit"          target: Sep 1 – Sep 30
  → Job: "Fall Winterization"     target: Oct 1 – Oct 31
```

All jobs created with:
- `status: APPROVED` (skip REQUESTED — pre-paid)
- `category: READY_TO_SCHEDULE`
- `service_agreement_id` linked
- `source: "subscription"`
- `customer_id` from the agreement
- `property_id` from the agreement (if available)

---

## Frontend: Service Agreements Tab

### Business Metrics (top of page)

KPI cards:
- Active Agreements (count + trend)
- MRR (Monthly Recurring Revenue = sum of annual_price / 12 for active agreements)
- Renewal Rate (trailing 90 days)
- Churn Rate (trailing 90 days)
- Past Due Amount (sum at risk)

Charts:
- MRR Over Time (12-month trailing line chart)
- Agreements by Tier (donut/bar chart)

### Operational Queues (below metrics)

1. **Renewal Pipeline** — agreements in PENDING_RENEWAL, sorted by renewal date
   - Each row: customer name, tier, renewal date, price, visits completed
   - Actions: [Approve ✓] [Do Not Renew ✗]

2. **Failed Payments** — agreements in PAST_DUE or PAUSED
   - Each row: customer name, tier, failed date, amount, current status
   - Actions: [Log Outreach] [Resume] [Cancel]

3. **Unscheduled Visits** — jobs linked to agreements that are APPROVED but not SCHEDULED
   - Grouped by month/type
   - Link to Schedule tab

4. **Onboarding Incomplete** — agreements in PENDING (no property info yet)
   - Actions: [Send Reminder]

### Agreement List (below queues)

Status filter tabs: All | Active | Pending | Pending Renewal | Past Due | Cancelled | Expired

Table columns: Agreement #, Customer, Tier, Package Type, Status, Price, Start Date, Renewal Date, Jobs Progress

### Agreement Detail View

- Agreement info (tier, dates, price, status, property)
- Jobs timeline: visual showing completed ✓, scheduled 📅, upcoming ○
- Jobs progress: "2 of 3 visits completed"
- Payment history (from Stripe via API or cached)
- Status log (from AgreementStatusLog)
- Admin notes
- Actions: Pause, Resume, Cancel (with reason), Approve/Reject Renewal

### Dashboard Tab Additions

New widgets on the main dashboard:
- Active Agreements count with trend arrow
- MRR with month-over-month change
- Renewal Pipeline count (needs Viktor's review)
- Failed Payments count + dollar amount at risk

### Jobs Tab Modifications

- New "Subscription" source badge on jobs linked to agreements
- Target date range column/filter
- "Ready to Schedule" quick-filter surfaces subscription jobs by urgency

---

## Implementation Phases (within Phase 14)

### Phase 14A — Backend Foundation
1. Add `stripe` package to dependencies
2. New enums: `AgreementStatus`, `PaymentStatus`, `PackageType`, `BillingFrequency`
3. New models: `ServiceAgreementTier`, `ServiceAgreement`, `AgreementStatusLog`
4. Modify `Job` model: add `service_agreement_id`, `target_start_date`, `target_end_date`
5. Alembic migrations
6. Seed `ServiceAgreementTier` with 6 packages (3 tiers × 2 types)
7. New repositories: `AgreementTierRepository`, `AgreementRepository`
8. New schemas: agreement tier + agreement request/response Pydantic models

### Phase 14B — Stripe Webhook + Service Logic
1. Stripe webhook endpoint with signature verification
2. `checkout.session.completed` handler: match/create customer, create agreement, generate jobs
3. `invoice.paid` handler: activate agreement, handle renewals
4. `invoice.payment_failed` handler: mark past due, escalation logic
5. `invoice.upcoming` handler: mark pending renewal
6. `customer.subscription.deleted` handler: cancel agreement + future jobs
7. Seasonal job generation service
8. Agreement service with status transitions, renewal approval/rejection
9. Agreement metrics service (active count, MRR, renewal rate, churn)

### Phase 14C — Admin API
1. Agreement tier endpoints (list, detail)
2. Agreement CRUD endpoints (list with filters, detail, status transitions)
3. Renewal pipeline + failed payments convenience endpoints
4. Agreement metrics endpoint
5. Modify dashboard summary to include agreement data
6. Modify jobs list to support `service_agreement_id` filter + target date filters

### Phase 14D — Frontend: Agreements Feature
1. New `features/agreements/` feature slice (types, API client, hooks, components)
2. Agreement list page with status tabs + table
3. Agreement detail page with jobs timeline + status actions
4. Renewal pipeline queue component
5. Failed payments queue component
6. Business metrics cards + charts
7. Register route + nav tab

### Phase 14E — Frontend: Dashboard + Jobs Updates
1. Dashboard widgets: Active Agreements, MRR, Renewal Pipeline, Failed Payments
2. Jobs table: subscription source badge, target date columns
3. Jobs filters: source type filter, target date range filter

### Phase 14F — Testing + Quality
1. Unit tests for all new services (agreement service, webhook handler, job generation)
2. Functional tests with real DB (agreement lifecycle, webhook processing)
3. Integration tests (Stripe webhook → agreement → jobs pipeline)
4. Property-based tests for job generation logic (correct job count per tier, valid date ranges)
5. Frontend component tests
6. Ruff + MyPy + Pyright zero errors

---

## Environment Variables (new)

| Variable | Purpose | Example |
|----------|---------|---------|
| `STRIPE_SECRET_KEY` | Stripe API calls | `sk_test_...` (test) / `sk_live_...` (prod) |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification | `whsec_...` |

---

## Dependencies (new)

| Package | Purpose |
|---------|---------|
| `stripe` (Python) | Stripe SDK for webhook verification + API calls |

---

## Key Design Decisions

1. **Tier templates vs instances**: Separate `ServiceAgreementTier` (what packages exist) from `ServiceAgreement` (a customer's subscription). Allows changing tier pricing without affecting existing agreements.

2. **Jobs generated at purchase**: All seasonal jobs for the year are created immediately with target date ranges. Viktor sees the full workload upfront and just needs to schedule them.

3. **Subscription jobs skip REQUESTED**: They enter at APPROVED status since they're pre-paid. No lead qualification needed.

4. **Viktor's renewal gate**: Renewals auto-charge by default (safe for revenue), but Viktor gets a 30-day window to review and reject if needed. Jobs only generate after `invoice.paid`.

5. **No mid-season tier changes**: Simplifies everything. Customer waits until renewal to upgrade/downgrade.

6. **Idempotent webhook handling**: Stripe can send duplicate webhooks. Every handler checks for existing records before creating new ones.

7. **Agreement status log**: Every status change is logged with timestamp, actor, and reason for audit trail.

---

## Open Questions

1. **Stripe Products**: Are the 6 Stripe Products already created with proper metadata (`package_tier`, `package_type`)? Or do we need to create them?
2. **Seed data**: Should tier seeding happen via migration or a management command?
3. **Payment history**: Pull from Stripe API on-demand, or cache/sync to local DB?
4. **MRR charts**: Use a charting library already in the frontend, or add one? (Recharts is common with React)
5. **Onboarding form**: Phase 14 creates the backend endpoints for it, but the landing page form itself is a separate repo/phase. Do we stub the onboarding endpoints now or defer entirely?
