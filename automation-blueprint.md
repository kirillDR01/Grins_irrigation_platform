# Grins Irrigation Platform — Automation Blueprint

> Brainstorming document for end-to-end automation: from customer acquisition through invoicing.
> Based on analysis of the current platform, the landing page, and industry best practices from Jobber, ServiceTitan, Housecall Pro, and Service Fusion.

---

## Table of Contents

1. [High-Level System Overview](#1-high-level-system-overview)
2. [Flow 1: Stripe Package Purchase → Dashboard](#2-flow-1-stripe-package-purchase--dashboard)
3. [Flow 2: Work Request / Lead → Job Pipeline](#3-flow-2-work-request--lead--job-pipeline)
4. [New Entity: Service Agreement](#4-new-entity-service-agreement)
5. [New Entity: Estimate / Quote](#5-new-entity-estimate--quote)
6. [Automation Triggers](#6-automation-triggers)
7. [Dashboard Tab Structure](#7-dashboard-tab-structure)
8. [Recommended Status Machines](#8-recommended-status-machines)
9. [Stripe Webhook Integration](#9-stripe-webhook-integration)
10. [Seasonal Job Auto-Generation](#10-seasonal-job-auto-generation)
11. [Commercial vs. Residential Handling](#11-commercial-vs-residential-handling)
12. [Scheduling UX: "Ready to Schedule" View](#12-scheduling-ux-ready-to-schedule-view)
13. [Automated Communication Sequences](#13-automated-communication-sequences)
14. [Summary: What Needs to Be Built](#14-summary-what-needs-to-be-built)

---

## 1. High-Level System Overview

The platform handles two distinct customer acquisition paths that converge into a single job execution pipeline:

```
PATH A: PACKAGE PURCHASE (Stripe)              PATH B: WORK REQUEST / INQUIRY
─────────────────────────────────              ──────────────────────────────
Customer buys package on website               Customer fills out form
         │                                     (website lead form OR Google Form)
         ▼                                              │
Stripe processes payment                                ▼
         │                                     Work Request (if Google Form)
         ▼                                              │
Webhook fires to backend                                ▼ (auto-promote)
         │                                          Lead (NEW)
         ▼                                              │
Auto-create:                                            ▼
  • Customer record                            Lead qualification
  • Service Agreement                          (CONTACTED → QUALIFIED)
  • Seasonal jobs                                       │
         │                                              ▼
         │                                     Needs estimate? ──YES──→ Estimate
         │                                              │                  │
         │                                              NO            Approved?
         │                                              │                  │
         │                                              ▼                  ▼
         └──────────────────────────────────→  Job (APPROVED)  ◄──────────┘
                                                        │
                                                        ▼
                                               Schedule & Dispatch
                                                        │
                                                        ▼
                                                  Job Completed
                                                        │
                                                        ▼
                                                Auto-generate Invoice
                                                        │
                                                        ▼
                                                  Payment collected
```

---

## 2. Flow 1: Stripe Package Purchase → Dashboard

### Recommended Approach: Hybrid (Option C)

A **Service Agreements tab** shows subscription-level data (who's subscribed, what tier, payment status, renewal dates). The **jobs generated from those agreements flow into the normal Jobs and Schedule tabs**. This is how Jobber and ServiceTitan handle it — the agreement is the parent record that spawns child jobs.

### The Automated Flow

```
1. Customer clicks "Subscribe" on landing page
2. Stripe Payment Link → Stripe Checkout
3. Customer completes payment
4. Stripe fires `checkout.session.completed` webhook to backend
5. Backend receives webhook and:
   a. Looks up customer by email → match existing OR create new Customer record
   b. Creates a Property record if address info is available (prompt during checkout)
   c. Creates a Service Agreement record linked to the Customer
   d. Auto-generates seasonal Jobs based on package tier:

      ESSENTIAL ($170 res / $225 com):
        → Job 1: Spring Startup (target: April)
        → Job 2: Fall Winterization/Blowout (target: October)

      PROFESSIONAL ($250 res / $375 com):
        → Job 1: Spring Startup (target: April)
        → Job 2: Mid-Season Inspection (target: July)
        → Job 3: Fall Winterization/Blowout (target: October)

      PREMIUM ($700 res / $850 com):
        → Job 1: Spring Startup (target: April)
        → Job 2: Monthly Visit (target: May)
        → Job 3: Monthly Visit (target: June)
        → Job 4: Monthly Visit (target: July)
        → Job 5: Monthly Visit (target: August)
        → Job 6: Monthly Visit (target: September)
        → Job 7: Fall Winterization/Blowout (target: October)

   e. All jobs created with status: APPROVED (skip REQUESTED since pre-paid)
   f. Jobs linked to Service Agreement via `service_agreement_id`
   g. Customer tagged as subscription customer

6. Admin (Victor) logs in → sees new jobs in "Ready to Schedule" queue
7. Admin drags/assigns jobs to schedule — no lead qualification needed
```

### Why This Works

- **Zero admin intervention** from purchase to "ready to schedule"
- **Victor sees the jobs immediately** — just needs to schedule them
- **Service Agreement tab** gives the subscription bird's-eye view (who's active, upcoming renewals, churn risk)
- **Jobs tab** stays the single source of truth for all work, regardless of origin

---

## 3. Flow 2: Work Request / Lead → Job Pipeline

### Recommended Flow: Auto-Promote with Smart Defaults

```
ENTRY POINTS
─────────────
Website Lead Form ──────→ Lead (status: NEW)
Google Form/Sheet ──────→ Work Request → auto-promote → Lead (status: NEW)

  The auto-promotion from Work Request to Lead should happen automatically.
  Spam/junk filtering is handled by:
    • Honeypot field (already on website form)
    • Zip code validation (already implemented)
    • Duplicate phone detection (flag, don't block)
    • Admin can still mark leads as SPAM from the Leads tab

QUALIFICATION (Admin / Sales)
─────────────────────────────
Lead: NEW
  │
  ├──→ Auto-SMS sent: "Thanks for reaching out! We'll call within 2 hours."
  │
  ▼
Lead: CONTACTED (admin calls, gathers details)
  │
  ▼
Lead: QUALIFIED (confirmed viable, scope understood)
  │
  ├── Does this need an on-site estimate?
  │     │
  │     YES → Create Estimate (auto-converts lead to Customer)
  │     │     Schedule estimate visit
  │     │     Perform on-site assessment
  │     │     Send quote to customer
  │     │     Customer approves → Estimate becomes Job (status: APPROVED)
  │     │
  │     NO → Convert Lead to Customer
  │           Create Job directly (status: APPROVED, category: READY_TO_SCHEDULE)
  │
  ▼
Lead: CONVERTED (customer_id linked, lead closed)

EXECUTION
─────────
Job: APPROVED → SCHEDULED → IN_PROGRESS → COMPLETED

INVOICING
─────────
Job: COMPLETED → Invoice auto-generated (DRAFT)
  → Admin reviews/sends → SENT
  → Customer pays → PAID
```

### Why Auto-Promote Work Requests

- **Manual review adds friction** with minimal value — the admin still reviews everything in the Leads tab
- **Spam is rare** on Google Forms (requires more effort than web bots)
- **Faster response time** — the sooner a lead enters the pipeline, the sooner the auto-acknowledgment goes out
- **Single pipeline** — everything flows through Leads, whether it came from the website or Google Forms
- The Work Requests tab remains as a **sync log / audit trail** showing what came in from Google Sheets

---

## 4. New Entity: Service Agreement

This is the missing link between Stripe subscriptions and the job pipeline.

### Data Model

```
ServiceAgreement
├── id: UUID
├── customer_id: FK → Customer
├── stripe_subscription_id: string (links to Stripe)
├── stripe_customer_id: string
├── package_tier: enum (ESSENTIAL | PROFESSIONAL | PREMIUM)
├── package_type: enum (RESIDENTIAL | COMMERCIAL)
├── status: enum (ACTIVE | PAUSED | CANCELLED | EXPIRED)
├── start_date: date
├── end_date: date (start_date + 1 year)
├── renewal_date: date
├── auto_renew: boolean (default true)
├── amount: decimal (annual price)
├── payment_status: enum (CURRENT | PAST_DUE | CANCELLED)
├── notes: text
├── created_at: datetime
├── updated_at: datetime
│
├── Relationships:
│   ├── customer → Customer
│   ├── jobs[] → Job (all jobs spawned by this agreement)
│   └── properties[] → Property (covered properties)
```

### Status Flow

```
ACTIVE (subscription current, jobs being generated)
  │
  ├──→ PAUSED (payment failed, on hold — stop generating new jobs)
  │       └──→ ACTIVE (payment resolved)
  │
  ├──→ CANCELLED (customer cancelled — cancel future unscheduled jobs)
  │
  └──→ EXPIRED (term ended, did not renew)
        └──→ ACTIVE (renewed for another year)
```

---

## 5. New Entity: Estimate / Quote

Currently, jobs have a `REQUIRES_ESTIMATE` category but no formal estimate workflow. For maximum automation and professionalism, a proper Estimate entity is recommended.

### Why Add Estimates

- **Customer-facing document** — send a professional quote with line items and options
- **Approval tracking** — know exactly when and how a customer approved
- **Conversion metrics** — track estimate-to-job conversion rate
- **Multiple options** — present good/better/best options (industry standard)
- **This is how every major CRM does it** — Jobber, ServiceTitan, and Housecall Pro all treat estimates as first-class entities

### Data Model

```
Estimate
├── id: UUID
├── estimate_number: string (unique, e.g., "EST-2026-001")
├── customer_id: FK → Customer
├── property_id: FK → Property
├── lead_id: FK → Lead (nullable, if originated from lead)
├── assigned_to: FK → Staff (who created/owns the estimate)
├── status: enum (DRAFT | SENT | VIEWED | APPROVED | REJECTED | EXPIRED)
├── title: string (e.g., "Irrigation System Repair — 123 Main St")
├── description: text
├── line_items: JSONB
│   [
│     { service: "Valve replacement", qty: 2, unit_price: 85.00, total: 170.00 },
│     { service: "Head adjustment", qty: 4, unit_price: 25.00, total: 100.00 },
│     { service: "System diagnostic", qty: 1, unit_price: 75.00, total: 75.00 }
│   ]
├── options: JSONB (nullable — for good/better/best quoting)
│   [
│     { name: "Basic Repair", line_items: [...], total: 345.00 },
│     { name: "Full System Tune-Up", line_items: [...], total: 595.00, recommended: true }
│   ]
├── subtotal: decimal
├── discount_amount: decimal
├── tax_amount: decimal
├── total_amount: decimal
├── valid_until: date (default: 30 days from creation)
├── customer_message: text (personalized note)
├── internal_notes: text (admin-only)
├── sent_at: datetime
├── viewed_at: datetime
├── approved_at: datetime
├── approved_option: string (nullable — which option the customer chose)
├── rejection_reason: text (nullable)
├── job_id: FK → Job (nullable — linked after approval converts to job)
├── created_at: datetime
├── updated_at: datetime
```

### Status Flow

```
DRAFT (being prepared)
  │
  ▼
SENT (delivered to customer via email/SMS)
  │
  ▼
VIEWED (customer opened the estimate — tracked via unique link)
  │
  ├──→ APPROVED (customer accepted — auto-create Job)
  │       └── Job created with status APPROVED, linked back to estimate
  │
  ├──→ REJECTED (customer declined — log reason, keep for follow-up)
  │
  └──→ EXPIRED (past valid_until date with no response)
        └── Trigger follow-up sequence before expiring
```

### Estimate → Job Conversion

When an estimate is approved:
1. Auto-create a Job with `category: READY_TO_SCHEDULE`, `status: APPROVED`
2. Copy line items to job's `quoted_amount`
3. Link `estimate.job_id` and `job.estimate_id`
4. If the Lead isn't already converted, auto-convert Lead → Customer
5. Notify the admin that a new job is ready to schedule

---

## 6. Automation Triggers

These are the automated actions the system should perform without admin intervention:

### On New Lead Created (from website form OR auto-promoted work request)

| Trigger | Action | Timing |
|---------|--------|--------|
| Lead status = NEW | Send SMS: "Thanks for reaching out to Grins Irrigation! We'll call you within 2 hours during business hours." | Immediate |
| Lead status = NEW | Send email confirmation with what to expect | Immediate |
| Lead uncontacted for 2 hours | Notify admin (push notification / dashboard alert) | 2 hours |
| Lead uncontacted for 24 hours | Auto-send SMS follow-up: "Just following up on your irrigation request..." | 24 hours |
| Lead uncontacted for 72 hours | Auto-send second follow-up via SMS | 72 hours |

### On Estimate Sent

| Trigger | Action | Timing |
|---------|--------|--------|
| Estimate status = SENT | Track email open / link click → set status to VIEWED | On event |
| Estimate not viewed after 48 hours | Auto-send reminder: "We sent you a quote — take a look!" | 48 hours |
| Estimate viewed but not approved after 5 days | Auto-send follow-up: "Any questions about the quote?" | 5 days |
| Estimate approaching expiration (3 days before) | Auto-send urgency reminder | 3 days before valid_until |

### On Job Status Change

| Trigger | Action | Timing |
|---------|--------|--------|
| Job status → SCHEDULED | Send customer SMS: "Your appointment is confirmed for [date]." | Immediate |
| Appointment is tomorrow | Send reminder SMS: "Reminder: Grins Irrigation visit tomorrow [time window]." | Day before, 6 PM |
| Job status → IN_PROGRESS | Send customer SMS: "Your technician is on the way!" | Immediate |
| Job status → COMPLETED | Auto-generate Invoice (status: DRAFT) | Immediate |
| Job status → COMPLETED | Send customer summary: "Work completed at [address]. Here's what we did: [description]" | Immediate |
| Job completed + 48 hours | Send review request (Google review link) | 48 hours |

### On Invoice

| Trigger | Action | Timing |
|---------|--------|--------|
| Invoice status → SENT | Start payment tracking timer | Immediate |
| Invoice unpaid after 7 days | Auto-send payment reminder #1 | 7 days |
| Invoice unpaid after 14 days | Auto-send payment reminder #2 | 14 days |
| Invoice unpaid after 30 days | Flag as OVERDUE, notify admin | 30 days |
| Invoice unpaid after 45 days | Lien warning (already implemented) | 45 days |

### On Stripe Subscription Event

| Trigger | Action | Timing |
|---------|--------|--------|
| `checkout.session.completed` | Create Customer + Service Agreement + Seasonal Jobs | Immediate |
| `customer.subscription.updated` | Update Service Agreement record | Immediate |
| `customer.subscription.deleted` | Cancel Service Agreement, cancel future unscheduled jobs | Immediate |
| `invoice.payment_failed` | Pause Service Agreement, notify admin, send customer payment update request | Immediate |
| `invoice.paid` (renewal) | Reactivate agreement, generate next year's seasonal jobs | Immediate |
| Subscription renewal in 30 days | Send customer renewal reminder with summary of services provided | 30 days before |

---

## 7. Dashboard Tab Structure

### Recommended Navigation

```
┌─────────────────────────────────────────────────────────────┐
│  Dashboard │ Leads │ Customers │ Agreements │ Estimates │   │
│  Jobs │ Schedule │ Invoices │ Work Requests │ Staff │       │
│  Settings                                                   │
└─────────────────────────────────────────────────────────────┘
```

### New Tabs

**Service Agreements** (new)
- List view: All active/paused/cancelled agreements
- Filters: status, package tier, package type, renewal date range
- Each row shows: Customer name, package, status, start/end date, # jobs remaining, payment status
- Detail view: Full agreement info, linked jobs timeline, Stripe subscription link, renewal history
- Actions: Pause, cancel, view in Stripe

**Estimates** (new)
- List view: All estimates with status filters
- Kanban option: DRAFT → SENT → VIEWED → APPROVED/REJECTED (visual pipeline)
- Each row shows: Estimate #, customer, property, amount, status, days since sent
- Detail view: Full estimate with line items, customer communication history
- Actions: Send, mark approved/rejected, convert to job, duplicate as template

### Modified Tabs

**Dashboard** — Add widgets:
- "Pending Estimates" count (sent but not approved)
- "Active Agreements" count
- "Jobs Ready to Schedule" count (the key number for Victor)
- "Revenue This Month" (from Stripe + invoices)
- "Leads Awaiting Contact" with time-since-created

**Leads** — Now receives auto-promoted work requests. Add:
- Source badge: "Website" vs "Google Form" to distinguish origin
- Time-since-created indicator (urgency signal)

**Work Requests** — Stays as-is, but now functions as:
- Sync log / audit trail for Google Sheets
- Shows which submissions were auto-promoted to leads
- Still allows manual review if needed

**Jobs** — Add:
- `service_agreement_id` link (for subscription-generated jobs)
- `estimate_id` link (for estimate-originated jobs)
- "Ready to Schedule" filter/view as a prominent quick-filter
- Source indicator: "Subscription", "Estimate", "Direct"

---

## 8. Recommended Status Machines

### Lead Status

```
NEW ──→ CONTACTED ──→ QUALIFIED ──→ CONVERTED
 │          │             │              │
 │          │             │              └──→ (Customer + Job or Estimate created)
 │          │             │
 └──→ SPAM  └──→ LOST     └──→ LOST
```

No changes needed — the current lead status flow is solid.

### Estimate Status (new)

```
DRAFT ──→ SENT ──→ VIEWED ──→ APPROVED ──→ (auto-creates Job)
                      │
                      ├──→ REJECTED
                      │
                      └──→ EXPIRED
```

### Job Status

```
REQUESTED ──→ APPROVED ──→ SCHEDULED ──→ IN_PROGRESS ──→ COMPLETED ──→ CLOSED
                                                              │
                                                              └──→ (auto-creates Invoice)

  At any point: ──→ CANCELLED
```

Minor recommendation: For subscription-generated jobs, they should skip `REQUESTED` and enter directly at `APPROVED` since they're pre-paid.

### Service Agreement Status (new)

```
ACTIVE ──→ PAUSED ──→ ACTIVE (reactivated)
   │
   ├──→ CANCELLED
   │
   └──→ EXPIRED ──→ ACTIVE (renewed)
```

### Invoice Status

```
DRAFT ──→ SENT ──→ VIEWED ──→ PAID
                      │
                      ├──→ PARTIAL ──→ PAID
                      │
                      └──→ OVERDUE ──→ LIEN_WARNING ──→ LIEN_FILED
```

No changes needed — the current invoice flow is solid.

---

## 9. Stripe Webhook Integration

### Architecture

```
Stripe ──webhook──→ POST /api/v1/webhooks/stripe
                           │
                           ▼
                    Verify signature (stripe-python SDK)
                           │
                           ▼
                    Route by event type
                           │
              ┌────────────┼────────────────┐
              ▼            ▼                ▼
    checkout.session   invoice.*    customer.subscription.*
      .completed           │                │
          │                ▼                ▼
          ▼          Update Invoice    Update Service
   Create Customer    payment status    Agreement status
   Create Agreement
   Generate Jobs
```

### Backend Implementation Requirements

1. **New endpoint**: `POST /api/v1/webhooks/stripe`
   - Verify Stripe webhook signature
   - Parse event type and route to handler
   - Idempotent (handle duplicate webhook deliveries)

2. **Stripe SDK**: Add `stripe` Python package to backend dependencies

3. **Environment variables**:
   - `STRIPE_SECRET_KEY` — for API calls
   - `STRIPE_WEBHOOK_SECRET` — for signature verification
   - `STRIPE_CUSTOMER_PORTAL_URL` — for linking customers to their portal

4. **Customer matching logic**:
   - On `checkout.session.completed`, extract customer email from Stripe
   - Search existing customers by email → match if found
   - If no match, create new Customer record
   - Store `stripe_customer_id` on Customer record for future matching

5. **Metadata on Stripe Payment Links**:
   - Add metadata to each Stripe Product: `package_tier`, `package_type`
   - This tells the webhook handler which jobs to generate

### Stripe Checkout Session: Collecting Property Info

To auto-create Property records, the Stripe Checkout should collect:
- **Address fields** (Stripe Checkout supports `shipping_address_collection`)
- Or: redirect to a post-purchase onboarding form that collects property details

Recommendation: **Post-purchase onboarding form**. After Stripe redirects back to the success page, show a short form: "Tell us about your property so we can schedule your first visit" — address, number of zones (if known), gate code, dogs, etc. This is better UX than cramming it into Stripe Checkout.

---

## 10. Seasonal Job Auto-Generation

### Timing Strategy: Generate All Jobs at Purchase, with Target Date Ranges

When a subscription is created, generate **all seasonal jobs for the year** immediately, each with a `target_date_range` (not a fixed date). This gives Victor full visibility into the year's workload.

```
Package purchased in March 2026:

ESSENTIAL:
  Job 1: Spring Startup      → target: Apr 1 – Apr 30
  Job 2: Fall Blowout         → target: Oct 1 – Oct 31

PROFESSIONAL:
  Job 1: Spring Startup      → target: Apr 1 – Apr 30
  Job 2: Mid-Season Check    → target: Jul 1 – Jul 31
  Job 3: Fall Blowout         → target: Oct 1 – Oct 31

PREMIUM:
  Job 1: Spring Startup      → target: Apr 1 – Apr 30
  Job 2: Monthly Visit       → target: May 1 – May 31
  Job 3: Monthly Visit       → target: Jun 1 – Jun 30
  Job 4: Monthly Visit       → target: Jul 1 – Jul 31
  Job 5: Monthly Visit       → target: Aug 1 – Aug 31
  Job 6: Monthly Visit       → target: Sep 1 – Sep 30
  Job 7: Fall Blowout         → target: Oct 1 – Oct 31
```

### Job Model Addition

```
target_start_date: date (nullable) — earliest this job should be scheduled
target_end_date: date (nullable) — latest this job should be scheduled
```

These fields allow:
- Filtering "jobs due this month" for scheduling
- Dashboard alerts: "12 Spring Startups need to be scheduled by April 30"
- Route optimization: batch similar jobs in the same time window

### On Subscription Renewal

When Stripe fires `invoice.paid` for a renewal:
1. Check if the Service Agreement is up for renewal
2. Generate next year's seasonal jobs with updated target dates
3. Update agreement `end_date` and `renewal_date`

---

## 11. Commercial vs. Residential Handling

### Recommendation: Same Pipeline, Different Tagging

Don't create separate flows. Instead, use the existing `property_type` field (RESIDENTIAL | COMMERCIAL) and `package_type` on Service Agreement to differentiate. The pipeline stages are identical — the differences are in **pricing, job scope, and scheduling priority**.

### Where Commercial Differs

| Aspect | Residential | Commercial |
|--------|-------------|------------|
| Property count | Usually 1 | Often multiple (HOA, complex) |
| Decision maker | Homeowner | Property manager, board |
| Estimate approval | Quick (days) | Slower (weeks, may need board vote) |
| Scheduling | Flexible | May require off-hours or specific windows |
| Invoicing | Per-job or subscription | Monthly/quarterly billing, PO numbers |
| Contract value | $170–$700/yr | $225–$850/yr (packages), $10K–$200K (custom) |

### Implementation

- **Customer record**: Already has properties[] — commercial clients just have more
- **Lead form**: Already captures `property_type` (Residential, Commercial, Government)
- **Service Agreement**: `package_type` field distinguishes RESIDENTIAL vs COMMERCIAL
- **Jobs**: Inherit property_type from the property they're attached to
- **Estimates**: For large commercial projects ($10K+), use the multi-option quoting (good/better/best)
- **Invoices**: Add optional `po_number` field for commercial clients that require it

No separate tabs or flows needed. Filters on each tab handle the distinction.

---

## 12. Scheduling UX: "Ready to Schedule" View

### What Victor Needs When He Logs In

The #1 priority for the admin is: **"What needs to be scheduled, and how do I get it on the calendar fast?"**

### Recommended: "Ready to Schedule" Queue

Add a prominent section (either on Dashboard home or as a filtered view on the Jobs tab) that shows:

```
┌─────────────────────────────────────────────────────────────────┐
│  READY TO SCHEDULE (14 jobs)                    [Schedule All ▼]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⏰ OVERDUE (target date passed)                                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Spring Startup — Johnson, 456 Oak Ave, Plymouth      │       │
│  │ Premium subscriber · Due by Apr 30 · 4 days overdue  │       │
│  │                                    [Schedule →]       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
│  📅 DUE THIS WEEK                                               │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Valve Repair — Smith, 123 Main St, Minnetonka        │       │
│  │ From estimate EST-2026-042 · Quoted $345              │       │
│  │                                    [Schedule →]       │       │
│  └──────────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ Spring Startup — Williams, 789 Elm Dr, Eden Prairie  │       │
│  │ Essential subscriber · Due by Apr 30                  │       │
│  │                                    [Schedule →]       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
│  📋 UPCOMING (due within 30 days)                               │
│  ... more jobs ...                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

- **Sorted by urgency**: Overdue → due this week → upcoming → no target date
- **Grouped by service type** option: Batch all Spring Startups together for efficient route planning
- **One-click schedule**: Opens scheduling modal with date picker + staff assignment
- **Bulk schedule**: Select multiple jobs → "Schedule All" → picks optimal date using AI route generation (already built)
- **Source indicator**: Shows whether the job came from a subscription, estimate, or direct request
- **Priority badges**: Premium subscribers, commercial clients, and flagged customers surface first

---

## 13. Automated Communication Sequences

### Sequence 1: New Lead Welcome

```
Trigger: Lead created (any source)
─────────────────────────────────
T+0 min     SMS: "Hi [name]! Thanks for reaching out to Grins Irrigation.
                   We'll give you a call within 2 hours during business hours.
                   Questions? Call us at (952) 818-1020."

T+0 min     Email: Welcome email with company info, services overview,
                    and what to expect next.

T+2 hours   If status still NEW:
              Internal alert to admin: "Lead [name] hasn't been contacted yet"

T+24 hours  If status still NEW:
              SMS: "Hi [name], just following up on your irrigation request.
                    We'd love to help — expect a call from us today!"

T+72 hours  If status still NEW or CONTACTED (no qualifier):
              SMS: "Hi [name], we want to make sure we don't miss you.
                    Reply YES if you're still interested and we'll get
                    right back to you."

T+7 days    If still not QUALIFIED:
              Admin notification: "Lead [name] going cold — last chance follow-up"
```

### Sequence 2: Estimate Follow-Up

```
Trigger: Estimate status = SENT
──────────────────────────────
T+0         SMS: "Hi [name]! We just sent over your estimate for [property].
                   Check your email or view it here: [link]"

T+48 hours  If not VIEWED:
              SMS: "Just a reminder — your irrigation estimate is waiting
                    for you. View it here: [link]"

T+5 days    If VIEWED but not APPROVED:
              SMS: "Hi [name], any questions about the estimate we sent?
                    Happy to walk through it — call us at (952) 818-1020."

T+25 days   If still SENT or VIEWED (5 days before expiration):
              SMS: "Your estimate for [property] expires in 5 days.
                    Want to lock in the price? Reply YES or call us."

T+30 days   If not APPROVED:
              Status → EXPIRED
              Admin notification for final outreach decision
```

### Sequence 3: Job Lifecycle Notifications

```
Trigger: Job status changes
───────────────────────────
SCHEDULED   SMS: "Your Grins Irrigation appointment is confirmed
                   for [date] between [time window]. We'll send a
                   reminder the day before."

Day before  SMS: "Reminder: Grins Irrigation visit tomorrow,
                   [date] between [time window]. Reply RESCHEDULE
                   if you need to change."

IN_PROGRESS SMS: "Your Grins Irrigation technician is on the way
                   to [address]! Estimated arrival: [time]."

COMPLETED   SMS: "All done at [address]! Here's a summary of today's work:
                   [service description]. Your invoice will follow shortly."

T+48 hours  SMS: "How was your experience with Grins Irrigation?
                   We'd love your feedback: [Google review link]"
```

### Sequence 4: Subscription Welcome

```
Trigger: Service Agreement created (Stripe purchase)
─────────────────────────────────────────────────────
T+0         SMS: "Welcome to Grins Irrigation [tier] plan!
                   Your [package_type] subscription is active.
                   We'll be scheduling your first visit soon."

T+0         Email: Full welcome email with:
                    - Subscription details & what's included
                    - Link to Stripe customer portal (manage billing)
                    - Link to post-purchase property info form
                    - Seasonal schedule overview
                    - Contact info

T+24 hours  If property info form not completed:
              SMS: "One more step — tell us about your property so
                    we can schedule your first visit: [form link]"
```

---

## 14. Summary: What Needs to Be Built

### New Backend Components

| Component | Description | Priority |
|-----------|-------------|----------|
| **ServiceAgreement model** | New DB model + migration for subscription tracking | High |
| **Estimate model** | New DB model + migration for quotes/estimates | High |
| **Stripe webhook endpoint** | `POST /api/v1/webhooks/stripe` with event routing | High |
| **Stripe service** | Business logic for handling webhook events, creating agreements/jobs | High |
| **Auto-promote service** | Auto-convert Google Sheet submissions to Leads | Medium |
| **Job generation service** | Generate seasonal jobs from Service Agreement | High |
| **Notification automation service** | Scheduled task runner for timed follow-ups and reminders | Medium |
| **Estimate service** | CRUD + status management + conversion to Job | High |
| **Post-purchase onboarding endpoint** | Collect property details after Stripe checkout | Medium |

### New Frontend Components

| Component | Description | Priority |
|-----------|-------------|----------|
| **Service Agreements tab** | List + detail view for subscriptions | High |
| **Estimates tab** | List + detail + kanban view for quotes | High |
| **Estimate builder** | Form for creating estimates with line items and options | High |
| **Ready to Schedule queue** | Dashboard widget or Jobs tab filtered view | High |
| **Post-purchase onboarding form** | Property info collection after Stripe checkout | Medium |
| **Dashboard widgets** | Pending estimates, active agreements, ready-to-schedule count | Medium |
| **Bulk scheduling UI** | Select multiple jobs → schedule together | Medium |

### Modifications to Existing Components

| Component | Change | Priority |
|-----------|--------|----------|
| **Customer model** | Add `stripe_customer_id` field | High |
| **Job model** | Add `service_agreement_id`, `estimate_id`, `target_start_date`, `target_end_date` fields | High |
| **Invoice model** | Add optional `po_number` field for commercial clients | Low |
| **Lead model** | Add source tracking for auto-promoted work requests | Medium |
| **Google Sheets poller** | Add auto-promote logic (create Lead automatically on new submission) | Medium |
| **Work Requests tab** | Show promotion status ("Auto-promoted to Lead #X") | Medium |
| **Dashboard page** | Add new metric widgets | Medium |
| **Jobs tab** | Add "Ready to Schedule" filter, source indicators | Medium |

### Infrastructure

| Item | Description | Priority |
|------|-------------|----------|
| **Stripe Python SDK** | Add `stripe` to backend dependencies | High |
| **Background task scheduler** | For timed automations (follow-ups, reminders). Options: Celery, APScheduler, or simple cron-based approach | Medium |
| **Email service** | For estimate delivery, welcome emails, follow-ups. Options: SendGrid, AWS SES, or Resend | Medium |

---

> **Next step**: Once we align on this blueprint, we can break it into implementation phases — likely starting with Stripe webhook integration + Service Agreements, then Estimates, then the automation sequences.
