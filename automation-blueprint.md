# Grins Irrigation Platform — Automation Blueprint

> Brainstorming document for end-to-end automation: from customer acquisition through invoicing.
> Based on analysis of the current platform, the landing page, and industry best practices from Jobber, ServiceTitan, Housecall Pro, and Service Fusion.

---

## Table of Contents

1. [High-Level System Overview](#1-high-level-system-overview)
2. [Cross-Repo Architecture & Deployment](#2-cross-repo-architecture--deployment)
3. [Flow 1: Stripe Package Purchase → Dashboard](#3-flow-1-stripe-package-purchase--dashboard)
4. [Flow 2: Work Request / Lead → Job Pipeline](#4-flow-2-work-request--lead--job-pipeline)
5. [Lead Intake Enhancements & Architecture](#5-lead-intake-enhancements--architecture)
6. [New Entity: Service Agreement](#6-new-entity-service-agreement)
7. [New Entity: Estimate / Quote](#7-new-entity-estimate--quote)
8. [Automation Triggers](#8-automation-triggers)
9. [Dashboard Tab Structure](#9-dashboard-tab-structure)
10. [Recommended Status Machines](#10-recommended-status-machines)
11. [Stripe Webhook Integration](#11-stripe-webhook-integration)
12. [Seasonal Job Auto-Generation](#12-seasonal-job-auto-generation)
13. [Commercial vs. Residential Handling](#13-commercial-vs-residential-handling)
14. [Scheduling UX: "Ready to Schedule" View](#14-scheduling-ux-ready-to-schedule-view)
15. [Automated Communication Sequences](#15-automated-communication-sequences)
16. [Infrastructure Requirements](#16-infrastructure-requirements)
17. [Landing Page Fixes (Critical)](#17-landing-page-fixes-critical)
18. [Staff Mobile Experience](#18-staff-mobile-experience)
19. [Summary: What Needs to Be Built](#19-summary-what-needs-to-be-built)

---

## 1. High-Level System Overview

The platform consists of **two separate repositories** that work together, plus external services:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CUSTOMER-FACING                                   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │  Grins_irrigation (Landing Page)                          │           │
│  │  Repo: github.com/kirillDR01/Grins_irrigation             │           │
│  │  Deploy: Vercel (grins-irrigation.vercel.app)             │           │
│  │  Stack: React 19 + Vite + Tailwind                        │           │
│  │                                                            │           │
│  │  • Landing page with lead capture form                    │           │
│  │  • Service packages page with Stripe Payment Links        │           │
│  │  • Rule-based chatbot (to be upgraded to AI)              │           │
│  │  • Service pages, blog, gallery, contact                  │           │
│  └───────────────┬────────────────────────┬──────────────────┘           │
│                  │                        │                               │
│          POST /api/v1/leads        Stripe Payment Links                  │
│          (lead submission)         (redirect to Stripe Checkout)         │
│                  │                        │                               │
└──────────────────┼────────────────────────┼──────────────────────────────┘
                   │                        │
                   ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        BACKEND + ADMIN                                    │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────┐           │
│  │  Grins_irrigation_platform (Platform)                     │           │
│  │  Repo: github.com/kirillDR01/Grins_irrigation_platform    │           │
│  │  Deploy: Railway (grinsirrigationplatform-production)      │           │
│  │  Stack: FastAPI + PostgreSQL + React 19 admin dashboard   │           │
│  │                                                            │           │
│  │  Backend (FastAPI):                                        │           │
│  │  • 126 API endpoints across 16 routers                    │           │
│  │  • 14 DB models + 24 services + 15 repositories           │           │
│  │  • AI services (OpenAI), SMS (Twilio), Google Sheets sync │           │
│  │  • Timefold-based route optimization & scheduling         │           │
│  │                                                            │           │
│  │  Frontend (React admin dashboard):                        │           │
│  │  • Customers, Leads, Jobs, Schedule, Invoices, Staff tabs │           │
│  │  • AI chat, job categorization, estimate generation       │           │
│  │  • Schedule generation with map visualization             │           │
│  └───────────────┬──────────────────────────────────────────┘           │
│                  │                                                        │
└──────────────────┼────────────────────────────────────────────────────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
   ┌─────────────┐  ┌──────────────┐
   │   Stripe     │  │   Twilio      │
   │   Webhooks   │  │   SMS/Voice   │
   │   (MISSING)  │  │   (working)   │
   └─────────────┘  └──────────────┘
```

The platform handles two distinct customer acquisition paths that converge into a single job execution pipeline:

```
PATH A: PACKAGE PURCHASE (Stripe)              PATH B: WORK REQUEST / INQUIRY
─────────────────────────────────              ──────────────────────────────
Customer buys package on website               Customer fills out form
(Grins_irrigation landing page)                (landing page OR Google Form)
         │                                              │
         ▼                                              ▼
Stripe Checkout (external)                     POST /api/v1/leads
         │                                     (Grins_irrigation_platform backend)
         ▼                                              │
Webhook fires to backend ← MUST BUILD                  ▼
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

## 2. Cross-Repo Architecture & Deployment

### Why This Matters

This system spans **two separate git repositories** with **independent deployments**. Every feature must be evaluated for which repo(s) it touches. A change like "add SMS consent to the lead form" requires coordinated changes across both repos:

1. **Backend first**: Add `sms_consent` field to `LeadSubmission` schema and `Lead` model (platform repo)
2. **Deploy backend**: Push to Railway so the API accepts the new field
3. **Frontend second**: Wire up the checkbox in the lead form and include in payload (landing page repo)
4. **Deploy frontend**: Push to Vercel

### Repository Ownership Map

| Change Category | Landing Page Repo | Platform Backend | Platform Frontend |
|-----------------|:-:|:-:|:-:|
| Lead form fields (consent, referral, property type) | **X** | **X** | |
| Stripe webhook handling | | **X** | |
| Post-purchase onboarding form | **X** | **X** | |
| Admin dashboard features (tabs, widgets) | | | **X** |
| AI chatbot upgrade | **X** | **X** | |
| UTM/QR parameter tracking | **X** | **X** | |
| Background task scheduler | | **X** | |
| Email service integration | | **X** | |
| New models (Estimate, ServiceAgreement) | | **X** | **X** |
| Staff mobile experience | | **X** | **X** |
| Analytics (GTM/GA4) | **X** | | |

### Current Deployment Architecture

```
Landing Page (Grins_irrigation):
  Build:  Vite → static React SPA
  Host:   Vercel
  URL:    grins-irrigation.vercel.app
  Config: vercel.json with SPA rewrites
  Env:    VITE_API_URL → Railway backend URL

Platform Backend (Grins_irrigation_platform):
  Build:  Python → Uvicorn ASGI server
  Host:   Railway
  URL:    grinsirrigationplatform-production.up.railway.app
  DB:     PostgreSQL (Railway-managed)
  Env:    DATABASE_URL, TWILIO_*, OPENAI_API_KEY, GOOGLE_SHEETS_*, CORS_ORIGINS

Platform Frontend (Grins_irrigation_platform/frontend):
  Build:  Vite → static React SPA
  Host:   Vercel (separate project from landing page)
  Config: vercel.json in frontend/
  Env:    VITE_API_BASE_URL → Railway backend URL

CORS Configuration:
  Backend allows: grins-irrigation.vercel.app, platform frontend domain
  Both frontends use withCredentials: true for cookie-based auth refresh
```

### Cross-Repo API Contract

The landing page communicates with the platform backend through a single public endpoint:

```
POST /api/v1/leads (public, no auth required)

Current payload (what landing page sends today):
{
  "name": "John Smith",
  "phone": "6125551234",
  "zip_code": "55416",
  "situation": "new_system",       ← mapped from serviceInterest dropdown
  "email": "john@example.com",     ← optional
  "notes": "Need new sprinklers",  ← optional
  "source_site": "website",        ← hardcoded "website" or "chatbot"
  "website": ""                    ← honeypot (empty = real human)
}

PROBLEM: Landing page collects but DOES NOT SEND:
  - propertyType (residential/commercial/government)
  - referralSource (Google, Referral, Facebook, Instagram, Yard Sign, Nextdoor, Other)
  - smsConsent (checkbox rendered but not wired)
  - termsAccepted (checkbox does not exist)

Required payload (after fixes):
{
  "name": "John Smith",
  "phone": "6125551234",
  "zip_code": "55416",
  "situation": "new_system",
  "email": "john@example.com",
  "notes": "Need new sprinklers",
  "source_site": "website",
  "website": "",
  "property_type": "residential",   ← NEW: from radio buttons
  "referral_source": "google",      ← NEW: from dropdown
  "sms_consent": true,              ← NEW: from checkbox (CRITICAL for TCPA)
  "terms_accepted": true,           ← NEW: from checkbox
  "lead_source": "website",         ← NEW: derived from context + UTM params
  "source_detail": "utm_source=google&utm_medium=cpc&utm_campaign=spring2026"  ← NEW: from URL params
}
```

### Stripe Payment Link → Backend Connection

Currently **completely disconnected**. The landing page has 6 Stripe Payment Links (test mode) that redirect to `?payment=success` on the landing page. The backend has **no Stripe configuration, no webhook endpoint, and no Service Agreement model**.

```
TODAY (broken):
  Customer clicks "Subscribe" → Stripe Checkout (test mode)
  → Stripe processes payment → redirects to landing page ?payment=success
  → Landing page shows "Thanks!" banner
  → NOTHING happens in the backend. No record created. Viktor must check Stripe manually.

TARGET (automated):
  Customer clicks "Subscribe" → Stripe Checkout (live mode)
  → Stripe processes payment → fires webhook to platform backend
  → Backend: creates Customer + ServiceAgreement + seasonal Jobs
  → Stripe redirects to landing page ?session_id=xxx
  → Landing page shows post-purchase onboarding form (address, zones, etc.)
  → Form submits to backend → creates Property record
  → Viktor logs in → sees new jobs in "Ready to Schedule" queue
```

---

## 3. Flow 1: Stripe Package Purchase → Dashboard

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

## 4. Flow 2: Work Request / Lead → Job Pipeline

### Recommended Flow: Auto-Promote with Smart Defaults

```
ENTRY POINTS (All channels funnel into a single Lead pipeline)
──────────────────────────────────────────────────────────────
Website Lead Form ─────────────→ Lead (status: NEW, source: WEBSITE)
Google Form/Sheet ─────────────→ Work Request → auto-promote → Lead (status: NEW, source: GOOGLE_FORM)
Phone Call (AI Agent) ─────────→ Lead (status: NEW, source: PHONE_CALL)
SMS/Text (AI Agent) ───────────→ Lead (status: NEW, source: TEXT_MESSAGE)
Google Ads click-through ──────→ Lead (status: NEW, source: GOOGLE_AD)
Social Media Ads ──────────────→ Lead (status: NEW, source: SOCIAL_MEDIA)
QR Code (flyers/marketing) ───→ Lead (status: NEW, source: QR_CODE)
Email Campaign response ───────→ Lead (status: NEW, source: EMAIL_CAMPAIGN)
Text Campaign response ────────→ Lead (status: NEW, source: TEXT_CAMPAIGN)
Referral / Other ──────────────→ Lead (status: NEW, source: REFERRAL)

  The auto-promotion from Work Request to Lead should happen automatically.
  Spam/junk filtering is handled by:
    • Honeypot field (already on website form)
    • Zip code validation (already implemented)
    • Duplicate phone detection (flag, don't block)
    • Admin can still mark leads as SPAM from the Leads tab

INTAKE ROUTING (AI Agent or System determines path)
───────────────────────────────────────────────────
When AI agent or system can determine the service needed and price:
  → Tag as SCHEDULE
  → Lead enters normal qualification pipeline

When AI agent or system cannot determine scope (complex jobs, custom work):
  → Tag as FOLLOW_UP
  → Lead routed to admin-only Follow-Up Queue for human review

QUALIFICATION (Admin / AI Agent / Sales)
────────────────────────────────────────
Lead: NEW
  │
  ├──→ Auto-SMS sent: "Thanks for reaching out! We'll call within 2 hours."
  ├──→ Auto-email confirmation with what to expect
  │
  ▼
Lead: CONTACTED (admin or AI agent calls, gathers details)
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

FOLLOW-UP QUEUE (Admin-only, for FOLLOW_UP tagged leads)
────────────────────────────────────────────────────────
Lead tagged FOLLOW_UP:
  │
  ├── Admin reviews in dedicated Follow-Up Queue
  ├── Admin contacts client to determine needs
  │     │
  │     ├── Resolved → Move to schedule as confirmed job or estimate
  │     ├── Client declines → Mark as LOST (kept in DB for future reference)
  │     └── Need more info → Keep in queue, add notes
  │
  └── System tracks all follow-up interactions for audit

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

## 5. Lead Intake Enhancements & Architecture

This section covers the business logic and technical architecture for all lead intake enhancements identified from the system requirements. Each subsection includes business context, data model changes, API changes, frontend changes, and how it integrates with the existing codebase patterns.

---

### 5.1 Expanded Lead Source Tracking

#### Business Logic

The system requirements call for leads coming from many channels beyond the current website form and Google Forms: phone calls, texts, QR codes, Google Ads, social media ads, email campaigns, and text campaigns. Every lead must carry its source so the marketing dashboard can calculate customer acquisition cost per channel and determine which channels are worth investing in.

#### Data Model Changes

**Modify `Lead` model** (`src/grins_platform/models/lead.py`):

The existing `source_site` field (VARCHAR 100, defaults to `"residential"`) is repurposed and a new `lead_source` enum is added.

```
LeadSource enum (add to models/enums.py):
├── WEBSITE           — Landing page form submission (existing)
├── GOOGLE_FORM       — Auto-promoted from Google Sheets (existing)
├── PHONE_CALL        — Inbound call handled by AI agent or staff
├── TEXT_MESSAGE       — Inbound SMS handled by AI agent or staff
├── GOOGLE_AD         — Click-through from Google Ads campaign
├── SOCIAL_MEDIA      — Click-through from social media ads (FB, IG, etc.)
├── QR_CODE           — Scan from flyer, door hanger, or marketing material
├── EMAIL_CAMPAIGN    — Response from mass email campaign
├── TEXT_CAMPAIGN     — Response from mass text campaign
├── REFERRAL          — Referred by existing customer or partner
├── OTHER             — Catch-all for any other source
```

**Migration**: Add `lead_source` column (VARCHAR 50, NOT NULL, DEFAULT 'website') to `leads` table. The existing `source_site` field remains for sub-source detail (e.g., which specific landing page).

```
leads table additions:
├── lead_source: VARCHAR(50) NOT NULL DEFAULT 'website'  — which channel
├── source_detail: VARCHAR(255) NULL                      — UTM params, campaign name, QR code ID, etc.
├── intake_tag: VARCHAR(20) NULL                          — 'schedule' or 'follow_up' (see §5.3)
```

#### API Changes

**Modify `POST /api/v1/leads`** (`src/grins_platform/api/v1/leads.py`):
- Add optional `lead_source` field to `LeadSubmission` schema (defaults to `WEBSITE` for backward compatibility)
- Add optional `source_detail` field for UTM/campaign tracking
- The landing page form keeps working unchanged — it just gets the default `WEBSITE` source

**Modify `GET /api/v1/leads`**:
- Add `lead_source` filter parameter to `LeadListParams`
- Support multi-select filtering (e.g., show leads from GOOGLE_AD + SOCIAL_MEDIA)

**New endpoint** — `POST /api/v1/leads/from-call` (authenticated, for staff/AI):
- Creates a lead from a phone call or text interaction
- Accepts: name, phone, email, situation, notes, lead_source (PHONE_CALL or TEXT_MESSAGE)
- Used by the AI agent service or admin manually logging a call

#### Frontend Changes

**Modify `LeadsList.tsx`**:
- Add `LeadSourceBadge` component showing colored badges per source
- Add lead_source filter dropdown to `LeadFilters.tsx`

**Modify `LeadDetail.tsx`**:
- Show source + source_detail in lead detail view

**Modify Dashboard**:
- Add "Leads by Source" chart widget (pie or bar chart)

#### Architecture Fit

Follows the existing pattern exactly:
1. New enum in `models/enums.py` (like `LeadStatus`, `LeadSituation`)
2. New field in `Lead` model with Alembic migration
3. Schema update in `schemas/lead.py` (`LeadSubmission`, `LeadResponse`)
4. Filter logic in `LeadRepository.list_with_filters()`
5. Frontend badge component pattern matches `LeadStatusBadge`

---

### 5.2 AI Conversational Agent Architecture

#### Current State Assessment

**What exists today:**

- **Landing page chatbot** (`Grins_irrigation` repo): 100% rule-based conversation tree with 6 hardcoded flows and keyword-based FAQ search against 48 static Q&As. No OpenAI integration. A `chatbot.md` brainstorming doc proposes GPT-4o Nano for FAQ, but nothing is implemented.
- **Platform AI service** (`Grins_irrigation_platform` repo): Robust AI infrastructure in `services/ai/` with OpenAI integration, prompt management, tool execution framework, security guardrails, audit logging, token/cost tracking, usage limits, and streaming support. This is a **mature AI backend** that the chatbot doesn't use.
- **SMS service** (`Grins_irrigation_platform` repo): Twilio integration with send/receive, delivery tracking, and inbound webhook handler. Currently logs inbound SMS but does not route them through AI.

**Key insight**: The AI infrastructure already exists in the platform backend. The chatbot upgrade is primarily about **connecting the landing page chatbot to the existing platform AI service**, not building AI from scratch.

#### Business Logic

The system requirements emphasize that **all communications to customers should be handled by AI agents** to eliminate the need for a person to speak with them. The AI agent should:

1. **Answer inbound calls and texts** — greet the customer, understand their need
2. **Determine the service needed** — match to a service offering and provide pricing
3. **Guide the customer to the right path**:
   - If AI can determine service + price → tag as SCHEDULE, confirm with customer, create lead/work request
   - If AI cannot determine scope → tag as FOLLOW_UP, offer to connect to a real person or fill out a simplified work request form
4. **Handle common questions** — pricing, availability, service area, etc.
5. **Escalate gracefully** — always offer the option to speak to a real person

#### Technical Architecture

```
INBOUND CHANNELS
────────────────
Phone Call ──→ Twilio Voice ──→ AI Voice Agent (OpenAI Realtime API or similar)
SMS/Text   ──→ Twilio SMS   ──→ AI Text Agent (existing SMS webhook + OpenAI)
Website    ──→ Chat Widget   ──→ AI Chat Agent (WebSocket + OpenAI)

                    │
                    ▼
          ┌─────────────────┐
          │  AI Agent Core   │
          │  (AgentService)  │
          └────────┬────────┘
                   │
          ┌────────┴────────┐
          │  Context:        │
          │  • Service list  │
          │  • Price list    │
          │  • Service area  │
          │  • FAQ/scripts   │
          │  • Availability  │
          └────────┬────────┘
                   │
          ┌────────┴────────────────┐
          │  Decision:               │
          │  Can determine service?  │
          └──┬───────────────┬──────┘
             │               │
         YES (SCHEDULE)   NO (FOLLOW_UP)
             │               │
             ▼               ▼
     Create Lead         Create Lead
     tag: SCHEDULE       tag: FOLLOW_UP
     with service +      → Admin Follow-Up Queue
     price attached
```

#### Backend Components

**Extend existing AI service** at `src/grins_platform/services/ai/` — do NOT create a separate service. The existing AI module already has prompt management, tool execution, guardrails, and audit logging. Add conversational agent capabilities as a new module within it.

**New module**: `src/grins_platform/services/ai/conversational_agent.py`

```
ConversationalAgentModule (extends existing AI service architecture)
├── Dependencies:
│   ├── Existing AI service infrastructure (prompts, tools, guardrails, audit)
│   ├── ServiceOfferingRepository (for price/service lookup)
│   ├── LeadService (to create leads from conversations)
│   └── SMSService (for text-based interactions)
│
├── Methods:
│   ├── handle_inbound_sms(from_phone, message_body) → AgentResponse
│   │     — Process incoming text, maintain conversation state, create lead when ready
│   │
│   ├── handle_inbound_call(from_phone, call_data) → TwiML response
│   │     — Process voice call via Twilio + AI, return TwiML for voice response
│   │
│   ├── handle_chat_message(session_id, message) → AgentResponse
│   │     — Process website chat message, maintain session state
│   │
│   ├── determine_service(conversation_context) → ServiceMatch | None
│   │     — Analyze conversation to match to a ServiceOffering + price
│   │
│   └── create_lead_from_conversation(conversation) → Lead
│         — Extract customer info from conversation, create lead with appropriate tag
│
├── AI System Prompt includes:
│   ├── Company info (Grins Irrigation, service area, hours)
│   ├── Service catalog with prices (pulled from ServiceOffering table)
│   ├── Decision tree for routing (SCHEDULE vs FOLLOW_UP)
│   ├── Required info to collect (name, phone, address, service needed)
│   └── Escalation instructions (when to offer human handoff)
```

**Conversation state**: Store in Redis or in-memory cache (keyed by phone number or session ID) with 24-hour TTL. Alternatively, extend the existing `ai_audit_log` table to track multi-turn conversations.

**Modify existing SMS webhook** (`src/grins_platform/api/v1/sms.py`):
- Route inbound SMS through `AIAgentService.handle_inbound_sms()` before logging
- AI agent responds automatically; if it creates a lead, the normal lead pipeline takes over

**New endpoint**: `POST /api/v1/ai-agent/chat` (public, rate-limited)
- WebSocket or REST endpoint for the website chat widget
- Returns AI responses in real-time

#### Frontend Components (Landing Page Repo)

**Upgrade existing chatbot** (`Grins_irrigation/frontend/src/features/chatbot/`):

The landing page already has a floating chat widget with a conversation UI. The upgrade replaces the hardcoded conversation tree with calls to the platform backend's AI service:

```
CURRENT (rule-based, no backend):
  ChatWidget → ChatWindow → hardcoded conversation tree → keyword FAQ search

TARGET (AI-powered, backend-connected):
  ChatWidget → ChatWindow → POST /api/v1/ai/chat-public (new public endpoint)
  → Platform AI service processes message with service catalog context
  → Returns AI response + optional actions (show lead form, show pricing, etc.)
  → ChatWindow renders response + action buttons
  → When AI determines lead is ready → opens lead form modal with pre-filled data
```

**Keep the rule-based flows as fallback**: If the AI service is unavailable or over budget, the chatbot falls back to the existing conversation tree. This is a hybrid approach that the `chatbot.md` brainstorming doc already recommends.

**New backend endpoint** (in platform repo):
- `POST /api/v1/ai/chat-public` — public, rate-limited (no auth), for landing page chatbot
- Distinct from the existing `POST /api/v1/ai/chat` which requires admin auth
- Rate limit: 20 messages per session, 100 sessions per hour per IP
- Context: service catalog, pricing, service area, FAQs
- Returns: message text + optional structured actions (show_lead_form, show_pricing, redirect_to_page)

#### Integration with Existing Infrastructure

- **OpenAI**: Already integrated (`services/ai_*.py` files, `OPENAI_API_KEY` configured)
- **Twilio**: Already integrated (`services/sms_service.py`, inbound webhook exists)
- **Service Offerings**: Already in DB — AI agent queries these for pricing
- **Lead Creation**: Already has `LeadService.submit_lead()` — AI agent calls this

#### Implementation Phasing

This is the most complex feature. Recommended phases:
1. **Phase 1**: AI text agent (SMS) — extend existing Twilio webhook to route through AI
2. **Phase 2**: AI chat agent (website widget) — new frontend component + backend endpoint
3. **Phase 3**: AI voice agent (phone calls) — Twilio Voice + OpenAI Realtime API integration

---

### 5.3 SCHEDULE vs. FOLLOW UP Intake Tagging

#### Business Logic

When a lead comes in (whether through AI agent, form, or manual entry), it gets tagged based on whether the system/AI could determine what the customer needs:

- **SCHEDULE**: Service identified, price confirmed, customer agreed → ready for the normal scheduling pipeline
- **FOLLOW_UP**: Complex request, AI couldn't determine scope, or customer wants to talk to a human → routed to the admin-only Follow-Up Queue

This tagging reduces admin workload by separating "ready to go" leads from "needs human attention" leads.

#### Data Model Changes

**Modify `Lead` model**:

```
leads table addition:
├── intake_tag: VARCHAR(20) NULL  — 'schedule' or 'follow_up'
```

```
IntakeTag enum (add to models/enums.py):
├── SCHEDULE    — AI/system resolved, ready for pipeline
├── FOLLOW_UP   — Needs human review
```

Website form submissions default to `SCHEDULE` (the form itself determines the service via the `situation` field). AI agent interactions set the tag based on whether they could resolve the request.

#### API Changes

**Modify `LeadSubmission` schema**:
- Add optional `intake_tag` field (defaults to `SCHEDULE`)

**Modify `GET /api/v1/leads`**:
- Add `intake_tag` filter parameter
- The Follow-Up Queue view is just a filtered view: `intake_tag=follow_up&status=new,contacted`

**Modify `PATCH /api/v1/leads/{id}`**:
- Allow changing `intake_tag` (admin can re-tag a lead if they realize it's simpler/more complex than initially thought)

#### Frontend Changes

**Modify `LeadsList.tsx`**:
- Add `IntakeTagBadge` (green for SCHEDULE, orange for FOLLOW_UP)
- Add quick-filter tabs: "All" | "Schedule" | "Follow Up"

**New Dashboard widget**: "Follow-Up Queue" counter with link to filtered leads view

---

### 5.4 Admin Follow-Up Queue

#### Business Logic

The Follow-Up Queue is an **admin-only** section where leads tagged as `FOLLOW_UP` are centralized for human review. The admin can:

1. See all leads that need human attention, sorted by age (oldest first)
2. Click into a lead to see the AI conversation transcript (if applicable)
3. Contact the client directly (call or text from within the dashboard)
4. After follow-up, take one of three actions:
   - **Move to Schedule**: Re-tag as `SCHEDULE`, create job or estimate, proceed normally
   - **Mark as LOST**: Client doesn't want to proceed (kept in DB for future reference)
   - **Keep in Queue**: Need more info, add notes, try again later

#### Technical Architecture

The Follow-Up Queue is **not a separate entity** — it's a filtered view of the Leads table. This avoids data duplication and keeps the single-pipeline architecture intact.

```
Follow-Up Queue = Leads WHERE intake_tag = 'follow_up' AND status IN ('new', 'contacted', 'qualified')
```

#### API Changes

**New endpoint**: `GET /api/v1/leads/follow-up-queue`
- Returns leads filtered by `intake_tag=follow_up` with active statuses
- Sorted by `created_at ASC` (oldest first — longest waiting)
- Includes time-since-created for urgency display
- Admin-only (requires auth)

This is a convenience endpoint; the same data is available via `GET /api/v1/leads?intake_tag=follow_up` but the dedicated endpoint allows adding queue-specific metadata (e.g., average wait time, count by age bucket).

#### Frontend Changes

**Option A** — Dedicated section within existing Leads tab:
- Add a "Follow-Up Queue" tab/section at the top of the Leads page
- Collapsible panel showing follow-up leads with urgency indicators
- One-click actions: "Move to Schedule", "Mark Lost", "Add Notes"

**Option B** — Dashboard widget + filtered view:
- Dashboard shows "Follow-Up Queue (3)" widget with oldest-first preview
- Clicking through opens Leads tab pre-filtered to `intake_tag=follow_up`

**Recommendation**: Option A — keeps everything in the Leads tab, reduces navigation. The dashboard widget from Option B is also added as a shortcut.

#### Architecture Fit

- No new models or tables needed
- One new filter parameter on existing `LeadRepository.list_with_filters()`
- One optional convenience endpoint
- Frontend: new filter tab on existing `LeadsList.tsx`

---

### 5.5 Consent & Compliance Tracking

This is the most legally critical section of the blueprint. Non-compliance carries **severe financial penalties**: TCPA violations cost $500–$1,500 per text message, and Minnesota auto-renewal violations expose the business to AG enforcement and private lawsuits. The architecture must make compliance the default — impossible to accidentally bypass.

---

#### 5.5.1 TCPA Compliance for Automated SMS

The **Telephone Consumer Protection Act (TCPA)** governs all automated text messages sent to cell phones. Grins' automation relies heavily on SMS (lead follow-ups, appointment reminders, estimate reminders, review requests, subscription notifications), so TCPA compliance is foundational.

##### Two Consent Tiers

| Consent Type | Applies To | How Obtained | Example Messages |
|---|---|---|---|
| **Prior Express Consent (PEC)** | Transactional / informational messages | Customer provides phone number in context of service relationship (form submission, booking) | "Your spring startup is scheduled for Tuesday May 6 at 9am", "Your technician is on the way", "Your invoice for $345 is ready" |
| **Prior Express Written Consent (PEWC)** | Marketing / promotional messages | Signed written agreement (digital checkbox qualifies) with specific disclosures | "Renew your plan and save 10%!", "Spring specials — book your startup today!", "Check out our new fertilizer add-on" |

**Critical rule**: If ANY promotional content is mixed into an informational message, the entire message is treated as marketing and requires PEWC. "Your appointment is confirmed — and check out our new fertilizer add-on!" = marketing message.

##### Required Consent Language (for PEWC)

The consent disclosure must appear **immediately adjacent** to the opt-in checkbox and include ALL of the following:

```
COMPLIANT CONSENT LANGUAGE (use on lead form, service agreement form, and post-purchase onboarding):

"By providing your mobile number and checking this box, you consent to receive
automated text messages from Grin's Irrigation & Landscaping, LLC at the number
provided, including appointment reminders, service updates, and promotional
messages about our services. Message and data rates may apply. Message frequency
varies (approx. 2-8 messages/month during service season). Reply STOP to
unsubscribe at any time. Reply HELP for help. Consent is not a condition
of purchase."
```

**Key requirements**:
- Company name explicitly stated (not just "us" or "we")
- Specify that messages are **automated**
- State approximate frequency
- Include "message and data rates may apply"
- State how to opt out (STOP keyword)
- State that consent is NOT a condition of purchase
- Must be an **affirmative action** (no pre-checked boxes)

##### Opt-Out Processing (Updated April 2025 FCC Rules)

| Requirement | Detail |
|---|---|
| **Honor any reasonable method** | Consumers can revoke consent via text (STOP, QUIT, CANCEL, UNSUBSCRIBE, END, REVOKE), email, voicemail, informal text ("please stop texting me"), or any other reasonable means |
| **Processing deadline** | Must process opt-out within **10 business days** (ideally within 24 hours) |
| **One confirmation text allowed** | After receiving opt-out, send exactly ONE text confirming the revocation. No promotional content. |
| **Scope clarification** | Confirmation text may ask: "Do you want to stop all messages or just promotions?" |
| **Time restrictions** | No messages before 8:00 AM or after 9:00 PM recipient's local time (Central for MN) |

##### Record Retention (Minimum 7 Years Recommended)

> **Updated**: While the TCPA statute of limitations is 4 years, aligning with IRS/MN DOR record retention (7 years for financial/tax records) and contract statute of limitations (7 years after termination) provides comprehensive protection. All consent and communication records should be retained for 7 years after last customer interaction.

Store the following for every customer/lead who provides a phone number:

```
sms_consent_records (NEW TABLE — immutable audit log)
├── id: UUID PK
├── customer_id: UUID FK → customers.id NULL       — linked after lead conversion
├── lead_id: UUID FK → leads.id NULL               — set if consent came from lead form
├── phone_number: VARCHAR(20) NOT NULL
├── consent_type: enum (TRANSACTIONAL | MARKETING | BOTH)
├── consent_given: BOOLEAN NOT NULL
├── consent_timestamp: TIMESTAMP NOT NULL
├── consent_method: VARCHAR(50) NOT NULL            — "web_form", "stripe_checkout", "text_reply", "verbal", "paper"
├── consent_language_shown: TEXT NOT NULL            — EXACT text shown to consumer at time of consent
├── consent_form_version: VARCHAR(20) NULL          — version identifier for the form
├── consent_ip_address: VARCHAR(45) NULL            — if collected via web form (IPv4 or IPv6)
├── consent_user_agent: VARCHAR(500) NULL           — browser info for web form submissions
├── opt_out_timestamp: TIMESTAMP NULL               — when they opted out (NULL if still in)
├── opt_out_method: VARCHAR(50) NULL                — "text_stop", "email", "phone_call", "web_form"
├── opt_out_processed_at: TIMESTAMP NULL            — when the opt-out was processed
├── opt_out_confirmation_sent: BOOLEAN DEFAULT false
├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
│
├── INDEX on phone_number (lookup by phone for inbound SMS)
├── INDEX on customer_id (compliance audit per customer)
├── IMMUTABLE: Records are INSERT-ONLY. Never update or delete.
│   New opt-out = new row with consent_given=false + opt_out_timestamp set.
│
├── RETENTION: Minimum 7 years after last customer interaction.
│   Aligns with IRS/MN DOR financial record requirements and contract statute of limitations.
```

##### Penalties for Non-Compliance

| Violation Type | Penalty |
|---|---|
| Standard TCPA violation | **$500 per text message per recipient** |
| Willful/knowing violation | **Up to $1,500 per text message per recipient** |
| FCC civil penalty | **Up to $10,000 per text** |
| No aggregate cap | Class actions can reach millions — Dish Network paid $341M |

---

#### 5.5.2 Minnesota Auto-Renewal Law (MN Stat. 325G.56–325G.62)

Minnesota enacted one of the strictest auto-renewal laws in the country, effective **January 1, 2025**. Since Grins operates in Minnesota and offers auto-renewing annual service agreements, **every requirement below is mandatory**.

##### Required Pre-Sale Disclosures (at Point of Purchase)

Before the customer accepts the subscription, the following must be displayed **clearly and conspicuously** (bold text, larger font, contrasting color, or set off by symbols):

1. That the service **continues until the consumer terminates it**
2. The **cancellation policy** (how to cancel and when cancellation takes effect)
3. The **recurring charge amount** and billing frequency (e.g., "$250/year, billed annually")
4. The **length of the automatic renewal term** (e.g., "renews for successive 1-year terms")
5. Any **minimum purchase obligations**

**Implementation**: These disclosures must appear:
- On the **landing page** near the "Subscribe" button (before Stripe Checkout redirect)
- In the **Stripe Checkout** custom fields or metadata (if possible)
- In the **post-purchase onboarding form** as a confirmation

##### Confirmation Email (Immediately After Purchase)

After the customer accepts, send a **written confirmation** (email) that includes:
- All 5 offer terms listed above
- The cancellation procedure (link to Stripe Customer Portal + phone/email)
- Must be in a format the consumer can retain (email or downloadable PDF)

##### Pre-Renewal Notice (5–30 Days Before Renewal)

For auto-renewing agreements, the seller **must send written notice** of the upcoming renewal:

```
TIMING: No fewer than 5 days and no more than 30 days before the last date
on which the consumer can cancel before the new term begins.

CONTENT MUST INCLUDE:
  - Renewal date
  - Renewal price (and notice if price has changed)
  - How to cancel (link to Stripe Customer Portal + phone/email)
  - Summary of services provided during current term

DELIVERY: Email (primary) + SMS (supplementary, requires TCPA consent)

EXAMPLE EMAIL:
  Subject: Your Grin's Irrigation [tier] Plan Renews on [date]

  Hi [name],

  Your Grin's Irrigation [tier] plan is scheduled to renew on [date]
  for $[amount]/year.

  Here's what we did for you this season:
  ✓ Spring Startup (completed [date])
  ✓ Mid-Season Inspection (completed [date])
  ✓ Fall Winterization (completed [date])

  Your plan will automatically renew unless you cancel before [date].

  To manage or cancel your subscription:
  → Online: [Stripe Customer Portal link]
  → Phone: (952) 818-1020
  → Email: info@grinsirrigation.com

  Thank you for choosing Grin's Irrigation!
```

##### Annual Notice (At Least Once Per Calendar Year)

For continuous service agreements, the seller **must send written notice at least once per calendar year** containing:
- The current terms of the service
- How to terminate or manage the service

**If the seller fails to provide this annual notice**, the consumer may terminate by **any reasonable means at any time at no cost**.

##### Online Cancellation Requirement (Click-to-Cancel)

If the business has a website with subscription management capability, it **must provide a simple mechanism to cancel directly online** — regardless of how the customer signed up. This is satisfied by the **Stripe Customer Portal** with cancellations enabled.

**Cannot** require customers to:
- Call to cancel (if they signed up online)
- Visit an office in person
- Send a certified letter

##### Save Offer Restrictions (Minnesota-Specific)

Minnesota is uniquely strict on retention tactics during cancellation:

| Allowed | Prohibited |
|---|---|
| Ask why they're cancelling | Offer unsolicited discounts/benefits to stay |
| Explain consequences of cancellation | Delay or create confusion in the cancellation process |
| Suggest downgrading or pausing | Make save offers UNLESS customer has **affirmatively pre-consented** to receive them |
| Provide cancellation confirmation | Use "abusive delay tactics" |

If a customer declines a save offer (when pre-consented), **immediate cancellation is required**.

##### Compliance Data Model

```
disclosure_records (NEW TABLE — immutable compliance audit log)
├── id: UUID PK
├── agreement_id: UUID FK → service_agreements.id NULL
├── customer_id: UUID FK → customers.id NOT NULL
├── disclosure_type: enum
│   ├── PRE_SALE           — disclosures shown before purchase
│   ├── CONFIRMATION       — post-purchase confirmation email
│   ├── RENEWAL_NOTICE     — 5-30 day pre-renewal notice
│   ├── ANNUAL_NOTICE      — annual terms reminder (MN requirement)
│   ├── MATERIAL_CHANGE    — notice of price/terms change
│   ├── CANCELLATION_CONF  — cancellation confirmation sent
├── sent_at: TIMESTAMP NOT NULL
├── sent_via: VARCHAR(20) NOT NULL          — "email", "sms", "mail"
├── recipient_email: VARCHAR(255) NULL
├── recipient_phone: VARCHAR(20) NULL
├── content_hash: VARCHAR(64) NOT NULL      — SHA-256 hash of the disclosure content
├── content_snapshot: TEXT NULL              — full text of disclosure (or template version)
├── delivery_confirmed: BOOLEAN DEFAULT false — email open tracking / delivery receipt
├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
│
├── INDEX on agreement_id
├── INDEX on customer_id
├── INDEX on disclosure_type + sent_at (for compliance audits)
├── IMMUTABLE: Records are INSERT-ONLY. Never update or delete.
```

##### Compliance Automation Schedule

| Action | Timing | Trigger | Blueprint Section |
|---|---|---|---|
| Pre-sale disclosures shown | At purchase | Landing page renders disclosure block near Subscribe button | §17 |
| Confirmation email | Immediately after purchase | `checkout.session.completed` webhook handler | §11, §15 |
| Pre-renewal notice | 30 days before renewal | APScheduler daily job (`check_upcoming_renewals`) | §8, §16.1 |
| Annual notice | January of each year | APScheduler annual job (`send_annual_notices`) | §16.1 |
| Cancellation confirmation | On cancellation | `customer.subscription.deleted` webhook or Stripe Portal action | §11 |

##### FTC Click-to-Cancel Rule (Federal)

The FTC's Click-to-Cancel Rule was **vacated by the 8th Circuit** (Custom Communications, Inc. v. FTC, 2025). However, the FTC continues to enforce the underlying principles under existing authority (16 CFR 425, Telemarketing Sales Rule, Section 5 unfair practices). **Best practice: comply with the rule's principles regardless of its formal legal status.**

Enforceable requirements that remain:
- Disclose material terms **before** billing information is collected
- Do not misrepresent any material fact about the subscription
- Obtain express, informed consent to the auto-renewal feature **separately** from other consent
- Make cancellation **at least as easy as signup** — if signup was online, cancellation must be available online
- The Stripe Customer Portal with cancellations enabled satisfies both MN 325G.60 and these FTC principles

> **Note**: Minnesota's own auto-renewal law (above) is **stricter** than the vacated FTC rule in several areas (save offer restrictions, annual notice requirement). Complying with MN law provides full FTC compliance as well.

---

#### 5.5.3 Customer Model Consent Fields

**Modify `Customer` model** (`src/grins_platform/models/customer.py`):

The existing model already has `sms_opt_in` and `email_opt_in` (booleans). Extend with:

```
customers table additions:
├── sms_opt_in: BOOLEAN NOT NULL DEFAULT false          — (already exists) consent to receive texts
├── email_opt_in: BOOLEAN NOT NULL DEFAULT false         — (already exists) marketing emails
├── terms_accepted: BOOLEAN NOT NULL DEFAULT false       — agreed to terms & conditions
├── terms_accepted_at: TIMESTAMP NULL                    — when they agreed (audit trail)
├── terms_version: VARCHAR(20) NULL                      — which version of T&C they agreed to
├── sms_opt_in_at: TIMESTAMP NULL                        — when SMS consent was given
├── sms_opt_in_source: VARCHAR(50) NULL                  — how consent was given (form, text reply, verbal)
├── email_opt_in_at: TIMESTAMP NULL                      — when email consent was given
├── sms_consent_language_version: VARCHAR(20) NULL       — version of consent text shown (for TCPA audit)
```

**Modify `Lead` model**:

```
leads table additions:
├── sms_consent: BOOLEAN NOT NULL DEFAULT false           — did they consent during intake?
├── terms_accepted: BOOLEAN NOT NULL DEFAULT false        — did they accept T&C during intake?
```

When a lead converts to a customer, these consent fields carry over to the customer record AND a `sms_consent_records` entry is created for the immutable audit trail.

#### 5.5.4 API Changes

**Modify `POST /api/v1/leads`** (public form submission):
- Add `sms_consent` checkbox field (required for automated follow-ups)
- Add `terms_accepted` checkbox field
- On submission: create `sms_consent_records` entry with consent_language_shown, IP, user agent, timestamp

**Modify `POST /api/v1/leads/{id}/convert`**:
- Carry `sms_consent` and `terms_accepted` from lead to new customer record
- Set corresponding timestamps on customer

**Modify `POST /api/v1/sms/send`** (CRITICAL ENFORCEMENT POINT):
- **Gate ALL automated SMS on consent check**:
  - Transactional messages: check `sms_opt_in == true` (PEC)
  - Marketing messages: check `sms_consent_records` for valid PEWC entry
- If no consent: skip the SMS, log a warning, do NOT send
- Admin-initiated manual SMS: allowed regardless (operational communication)
- **Time window check**: block sending before 8 AM or after 9 PM Central time

**Modify inbound SMS webhook** (`POST /api/v1/sms/webhook`):
- Check for STOP/QUIT/CANCEL/UNSUBSCRIBE/END/REVOKE keywords → auto-opt-out
- Check for informal opt-out language ("stop texting me", "take me off the list") → flag for review
- On opt-out: insert new `sms_consent_records` row with `consent_given=false`, send ONE confirmation text
- Process within 10 business days (target: same-day automatic processing)

**New endpoint**: `POST /api/v1/customers/{id}/consent`
- Update consent fields (admin can toggle consent based on verbal confirmation or written request)
- Creates `sms_consent_records` entry for audit trail
- Audit trail: log who changed what and when

**New endpoint**: `GET /api/v1/compliance/consent-audit?customer_id=xxx`
- Returns all `sms_consent_records` and `disclosure_records` for a customer
- Used by admin to verify compliance history before sending campaigns

#### 5.5.5 Frontend Changes

**Modify landing page lead form**:
- Checkbox: "I agree to the [Terms & Conditions](/terms-of-service)" (required, with link to T&C page)
- Checkbox with TCPA-compliant disclosure language (see §5.5.1) — required for SMS follow-ups
- Optional checkbox: "I'd like to receive promotional offers via email/text" (separate from transactional consent)
- **No pre-checked boxes** — all must be affirmative actions

**Modify `CustomerDetail.tsx`** (admin dashboard):
- Consent status badges: SMS (opted in/out with date), Email (opted in/out), T&C (accepted version + date)
- "Consent History" expandable section showing all `sms_consent_records` entries
- Admin can toggle consent status with mandatory reason field (creates audit trail)
- Warning banner if customer has opted out: "This customer has opted out of SMS. Automated messages will not be sent."

**Modify customer creation forms**:
- Include consent checkboxes when creating customers manually (admin must confirm consent was obtained)

#### Architecture Fit

- Extends existing `Customer` model (which already has `sms_opt_in` and `email_opt_in`)
- Migration adds new columns with safe defaults (`false`)
- SMS sending gate added as a check in `SMSService.send_message()` — single enforcement point
- Two new tables (`sms_consent_records`, `disclosure_records`) are append-only audit logs
- Consent timestamps + content hashes provide defensible TCPA compliance record
- Disclosure records track Minnesota auto-renewal compliance obligations
- All compliance logic is centralized — no scattered consent checks throughout the codebase

---

#### 5.5.6 CAN-SPAM Email Compliance

The blueprint includes both transactional emails (confirmations, invoices) and marketing emails (seasonal reminders, review requests, promotional offers). **CAN-SPAM** (15 U.S.C. § 7701) applies to all commercial emails. Penalties: up to **$53,088 per violating email** (2025 inflation-adjusted). Unlike TCPA, CAN-SPAM is an **opt-out** regime — you can email without prior consent, but must follow strict rules and honor opt-outs.

##### Email Classification: Transactional vs Commercial

This matters because **transactional emails are exempt from most CAN-SPAM requirements** (no unsubscribe link needed, no physical address needed), while **commercial emails require full compliance**. If ANY promotional content is mixed into a transactional email, the entire email becomes commercial.

| Email Type | Classification | CAN-SPAM Requirements | Reasoning |
|---|---|---|---|
| Appointment confirmation ("Your visit is scheduled for Tuesday at 9am") | **Transactional** | Accurate headers only | Confirms an agreed-upon transaction |
| Invoice email (bill for completed work) | **Transactional** | Accurate headers only | Completes a transaction |
| Payment receipt | **Transactional** | Accurate headers only | Confirms payment |
| Subscription confirmation ("Your Professional plan is active") | **Transactional** | Accurate headers only | Confirms subscription transaction |
| Subscription renewal notice — pure info ("Your plan renews Apr 1 at $250") | **Transactional** (likely) | Accurate headers only | Account status notification |
| Renewal notice WITH upsell ("Renew now — consider upgrading to Premium!") | **Commercial** | Full compliance | Promotional content changes classification |
| Seasonal service reminder ("Time to schedule your spring startup") | **Commercial** | Full compliance | Generating new business, not confirming existing |
| Review request ("How was your experience? Leave us a Google review") | **Commercial** | Full compliance | Promotes business reputation — commonly misclassified |
| Promotional offer ("20% off drip system installation this month") | **Commercial** | Full compliance | Unambiguously commercial |
| Estimate delivery (sending a quote to customer) | **Transactional** | Accurate headers only | Facilitates requested transaction |
| Onboarding reminder ("Complete your property info form") | **Transactional** | Accurate headers only | Facilitates agreed-upon relationship |
| Failed payment notice ("Your card was declined — update here") | **Transactional** | Accurate headers only | Account status notification |

##### CAN-SPAM Requirements for Commercial Emails

Every commercial/marketing email must include ALL of the following:

```
REQUIRED IN EVERY COMMERCIAL EMAIL:
────────────────────────────────────
1. ACCURATE HEADER INFO
   - "From" name and email must correctly identify Grin's Irrigation
   - "Reply-To" must be a valid address that reaches the business
   - No misleading routing information

2. NON-DECEPTIVE SUBJECT LINE
   - Must accurately reflect the email content
   - "Your irrigation system needs attention" for a promo = deceptive
   - "Spring specials from Grin's Irrigation" = fine

3. IDENTIFICATION AS ADVERTISEMENT
   - Must identify the message as an ad/solicitation
   - Can be subtle: "This is a promotional email from Grin's Irrigation"
   - Typically placed in the email footer

4. PHYSICAL POSTAL ADDRESS (required in EVERY commercial email)
   - Street address, P.O. box, or registered private mailbox
   - Example footer:
     "Grin's Irrigation & Landscaping, LLC
      [street address], [city], MN [zip]"

5. WORKING UNSUBSCRIBE LINK
   - Clear and conspicuous opt-out mechanism
   - Must be a single click (no login required, no multi-step process)
   - Cannot require information beyond email address
   - Cannot charge a fee
   - Link must remain functional for at least 30 days after send

6. HONOR OPT-OUTS WITHIN 10 BUSINESS DAYS
   - Once someone unsubscribes, stop ALL commercial emails within 10 business days
   - Cannot sell/transfer the unsubscribed email address
   - Must maintain suppression list permanently (no expiration)
```

##### Email Opt-Out Architecture

```
EMAIL OPT-OUT FLOW:
────────────────────
Customer clicks "Unsubscribe" link in commercial email
       │
       ▼
Redirected to: GET /api/v1/email/unsubscribe?token=xxx
       │
       ▼
Backend:
  1. Decode token → get customer email + customer_id
  2. Set customer.email_opt_in = false
  3. Set customer.email_opt_out_at = NOW()
  4. Add email to permanent suppression list
  5. Show confirmation page: "You've been unsubscribed from marketing emails.
     You'll still receive transactional emails (invoices, appointment confirmations)."
       │
       ▼
Before every commercial email send:
  EmailService.send_commercial() checks:
    - Is recipient on suppression list? → SKIP
    - Is customer.email_opt_in == false? → SKIP
    - Log skip reason for audit

NOTE: Transactional emails (invoices, confirmations) are NOT affected by unsubscribe.
Customer can always receive transactional emails regardless of opt-out status.
```

##### Separate Email Streams

Set up **separate sending configurations** for transactional vs commercial emails:

```
TRANSACTIONAL EMAILS (from: noreply@grinsirrigation.com)
  - Appointment confirmations, invoices, receipts, payment notices
  - Subscription confirmations, renewal notices (pure informational)
  - Onboarding reminders, failed payment notices
  - Do NOT include promotional content in these
  - No unsubscribe link needed (but recommended for good practice)

COMMERCIAL/MARKETING EMAILS (from: info@grinsirrigation.com or marketing@grinsirrigation.com)
  - Seasonal reminders, promotional offers, newsletters
  - Review requests
  - Renewal notices with upsell content
  - MUST include: physical address, unsubscribe link, ad identification
  - Subject to suppression list checks
```

Separating streams prevents a situation where transactional emails get flagged as spam because of commercial opt-out issues, and protects transactional email deliverability.

##### Record Retention (7 Years Recommended — Aligned with Financial Records)

| Record | Retention Period | Why |
|---|---|---|
| Email suppression/opt-out list | **Permanent** (no expiration) | Must never re-email opted-out addresses |
| Email consent records (opt-in date, method, source) | **7 years** after last interaction | Aligned with IRS/MN DOR financial record retention + FTC investigation look-back |
| Campaign archives (copy of each email sent) | **5 years** | Evidence of compliance, matches TCPA communication log retention |
| Send logs (recipient, date, subject, email type) | **5 years** | Audit trail for dispute resolution |
| Financial/tax records (invoices, payment receipts) | **7 years** | IRS (3-year standard, 6-7 recommended), MN Department of Revenue |
| Subscription agreements | **7 years** after termination | General contract statute of limitations |
| Cancellation records | **7 years** | MN auto-renewal law + dispute resolution |

> **Soft-delete pattern**: Use `deleted_at` field for all customer-facing records. Never hard-delete financial, consent, or communication records within retention windows.

##### Implementation in EmailService

```
src/grins_platform/services/email_service.py

EmailService
├── send_transactional(to, template, context)
│   - No suppression check (always deliver)
│   - Uses transactional sender identity
│   - Templates: confirmation, invoice, receipt, renewal_notice, onboarding_reminder
│
├── send_commercial(to, template, context)
│   - CHECK suppression list first → skip if suppressed
│   - CHECK customer.email_opt_in → skip if false
│   - LOG skip with reason if suppressed
│   - Inject unsubscribe link + physical address + ad identification into template
│   - Uses commercial sender identity
│   - Templates: seasonal_reminder, review_request, promotional_offer, newsletter
│
├── process_unsubscribe(token)
│   - Decode token, update customer.email_opt_in = false
│   - Add to suppression list
│   - Log timestamp and method
│
├── generate_unsubscribe_token(customer_id, email)
│   - Create signed, time-limited token for unsubscribe links
│   - Token must remain valid for 30+ days (CAN-SPAM requirement)
│
└── check_suppression(email) → bool
    - Query suppression list before any commercial send

PHYSICAL ADDRESS CONSTANT:
  COMPANY_ADDRESS = "Grin's Irrigation & Landscaping, LLC\n[VIKTOR: PROVIDE ACTUAL BUSINESS ADDRESS BEFORE LAUNCH]"
  ⚠️  ACTION REQUIRED: Viktor must provide the real physical business address (street, city, state, zip)
  before ANY commercial/marketing emails are sent. CAN-SPAM requires a valid postal address in every
  commercial email. A P.O. Box or registered commercial mail receiving agency (CMRA) address is acceptable.
  (injected into footer of every commercial email template)
```

##### Email Footer Template (for all commercial emails)

```html
<!-- Base commercial email footer (Jinja2) -->
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0;
            font-size: 12px; color: #666;">
  <p>This is a promotional email from Grin's Irrigation & Landscaping, LLC.</p>
  <p>{{ company_address }}</p>
  <p>
    <a href="{{ unsubscribe_url }}">Unsubscribe from marketing emails</a>
    &nbsp;|&nbsp;
    <a href="{{ preferences_url }}">Email preferences</a>
  </p>
  <p>You'll continue to receive transactional emails (invoices, appointment confirmations)
     regardless of your marketing email preferences.</p>
</div>
```

---

#### 5.5.7 Minnesota Sales Tax on Irrigation Services

Lawn irrigation maintenance services are **taxable in Minnesota**. This applies to all services Grins provides under its subscription packages.

##### What Is Taxable

| Service | Taxable? | Authority |
|---|---|---|
| Spring startup / system activation | **YES** | MN Revenue — Landscape Maintenance Services |
| Mid-season inspection / check | **YES** | MN Revenue — Landscape Maintenance Services |
| Fall winterization / blowout | **YES** | MN Revenue — Landscape Maintenance Services |
| Monthly monitoring visits | **YES** | MN Revenue — Landscape Maintenance Services |
| Controller programming | **YES** | MN Revenue — Landscape Maintenance Services |
| Irrigation system repairs | **YES** | MN Revenue — Landscape Maintenance Services |
| Fertilizer / weed treatment | **YES** | MN Revenue — Landscape Maintenance Services |
| **Initial irrigation system installation** (first-time, new construction) | **NO** | Capital improvement — not maintenance |
| **Initial landscaping installation** (first-time) | **NO** | Capital improvement — not maintenance |

##### Tax Rate

- **State rate**: 6.875%
- **Local taxes**: 0–2% additional (varies by city/county jurisdiction)
- **Total**: 6.875%–8.875% depending on customer location
- Rate is based on **customer service address**, not business address

##### Business Registration Requirements

1. **Register for MN Tax ID** with the Minnesota Department of Revenue — **mandatory before collecting any sales tax**
2. Filing frequency assigned by DOR based on monthly average collections:
   - Under $100/month average → **annual** filing
   - $100–$500/month → **quarterly** filing
   - Over $500/month → **monthly** filing
3. Must file returns and remit tax on schedule even if no tax was collected in a period

##### Implementation: Stripe Tax (Recommended)

Use **Stripe Tax** to automate tax calculation and collection. This eliminates manual rate lookups and handles multi-jurisdiction complexity.

```
STRIPE TAX SETUP:
──────────────────
1. Enable Stripe Tax in Stripe Dashboard → Settings → Tax
2. Register your MN Tax ID with Stripe (Tax Settings → Registrations → Add → Minnesota)
3. Set your business origin address (for nexus determination)
4. When creating Checkout Sessions or Payment Links:
   - Set automatic_tax.enabled = True
   - Stripe calculates the correct rate based on customer's billing address
   - Tax appears as a separate line item on the receipt/invoice
5. Stripe Tax handles:
   - Rate calculation by jurisdiction (state + local)
   - Tax-inclusive vs tax-exclusive pricing (recommend tax-exclusive: "$250 + tax")
   - Filing-ready tax reports (Dashboard → Tax → Reporting)

CHECKOUT SESSION CONFIGURATION:
  stripe.checkout.Session.create(
      mode="subscription",
      line_items=[{"price": price_id, "quantity": 1}],
      automatic_tax={"enabled": True},
      ...
  )

PRICING PAGE DISPLAY:
  Show: "$250/year + applicable tax"
  Do NOT show: "$250/year" without mentioning tax — this misleads customers
```

##### Impact on Existing Pricing

| Tier | Listed Price | Approx. Tax (6.875%) | Customer Pays (approx.) |
|---|---|---|---|
| Essential (Residential) | $170/year | ~$11.69 | ~$181.69 |
| Professional (Residential) | $250/year | ~$17.19 | ~$267.19 |
| Premium (Residential) | $700/year | ~$48.13 | ~$748.13 |
| Essential (Commercial) | $225/year | ~$15.47 | ~$240.47 |
| Professional (Commercial) | $375/year | ~$25.78 | ~$400.78 |
| Premium (Commercial) | $850/year | ~$58.44 | ~$908.44 |

> **Note**: Actual tax amounts vary by customer jurisdiction. Local rates in the Minneapolis-St. Paul metro area range from 7.125% to 8.875%.

##### Landing Page Changes

- Update pricing cards to show "**+ applicable tax**" below each price
- The MN auto-renewal disclosure (Step 1 pre-checkout modal) already includes "recurring charge amount" — update to say "$[price]/year plus applicable sales tax"
- Confirmation email must include tax breakdown (Stripe receipts do this automatically)

##### ServiceAgreement Model Impact

The `annual_price` field on ServiceAgreement stores the **base price** (pre-tax). Tax is calculated and collected by Stripe — the backend does not need to store tax amounts unless generating its own invoices.

For invoice-based work (non-subscription jobs), the existing Invoice model's `tax_amount` field is not currently populated. When building invoices for ad-hoc work, calculate tax using Stripe Tax API or a simple rate lookup based on service address jurisdiction.

---

#### 5.5.8 ADA / Accessibility Compliance

Web accessibility lawsuits have surged — **68% of ADA web lawsuits in 2024 targeted e-commerce sites** with average settlements of $25,000–$75,000. Since Grins has an online purchase flow (pricing page → Stripe Checkout → success page), the customer-facing pages must meet **WCAG 2.2 Level AA** standards.

##### Scope of Responsibility

- **Stripe Checkout (hosted)**: Maintained by Stripe, generally WCAG compliant. Not our responsibility.
- **Landing page pricing/service packages section**: Our responsibility (Grins_irrigation repo)
- **Pre-checkout confirmation modal**: Our responsibility
- **Post-purchase success/onboarding page**: Our responsibility
- **Terms of Service / Privacy Policy pages**: Our responsibility
- **Admin dashboard**: Lower priority (internal tool, not customer-facing), but should follow best practices

##### Requirements for Purchase Flow Pages (WCAG 2.2 Level AA)

```
STRUCTURE & SEMANTICS:
  ✅ Proper heading hierarchy (h1 > h2 > h3, no skipped levels)
  ✅ Landmark roles (nav, main, aside, footer)
  ✅ Pricing tables use proper <table> markup with headers, or structured with ARIA
  ✅ All interactive elements have programmatic labels (<label> elements associated with inputs)
  ✅ Page structure uses semantic HTML (not just styled divs)

KEYBOARD NAVIGATION:
  ✅ Entire purchase flow navigable by keyboard only (Tab, Enter, Space)
  ✅ Visible focus indicators on all interactive elements (buttons, links, checkboxes, inputs)
  ✅ Focus order follows visual/logical order
  ✅ No keyboard traps (modal can be closed with Escape key)

VISUAL:
  ✅ Color contrast: 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold)
  ✅ Color is never the ONLY indicator of status/information (add icons/text alongside)
  ✅ Responsive at 200% zoom — no horizontal scrolling
  ✅ No content that flashes more than 3 times per second

IMAGES & MEDIA:
  ✅ All informational images have descriptive alt text
  ✅ Decorative images have alt="" (empty alt)
  ✅ Service package icons have appropriate alt text or are aria-hidden

FORMS & INPUTS:
  ✅ All form fields have visible labels (not just placeholder text)
  ✅ Error messages identify the problem and suggest fixes
  ✅ Form validation errors announced to screen readers (ARIA live regions)
  ✅ Required fields marked with aria-required="true" and visual indicator

MOBILE:
  ✅ Touch targets minimum 44x44px (buttons, checkboxes, links)
  ✅ Text readable without zooming (minimum 16px base font)
  ✅ No horizontal scrolling at standard viewport widths
  ✅ Pricing tiers usable on mobile (single-column layout or accessible horizontal scroll)

SUBSCRIBE BUTTONS:
  ✅ Use descriptive labels: "Subscribe to Essential Plan — $170/year"
  ✅ Not just "Subscribe" or "Buy" (ambiguous for screen readers)
  ✅ Include tier name and price in button text or aria-label
```

##### Implementation Notes

- The pre-checkout confirmation modal MUST be closable with Escape key
- The modal MUST trap focus within it while open (focus doesn't escape to background content)
- The "Continue to Checkout" button must announce its disabled state to screen readers
- The post-purchase onboarding form should use ARIA live regions for validation errors
- Test with: VoiceOver (macOS/iOS), keyboard-only navigation, WAVE browser extension

##### Phase 0 Checklist Item

Add to the landing page development process:
- [ ] Run WAVE accessibility checker on pricing page, modal, and success page
- [ ] Complete keyboard-only navigation test
- [ ] Test with VoiceOver (macOS) or NVDA (Windows)
- [ ] Verify all color contrast ratios meet WCAG AA

---

### 5.6 Customer Tags

#### Business Logic

The system requirements call for customer tags to categorize and segment customers. Tags are flexible labels applied by staff or the system to enable filtering, prioritization, and targeted marketing.

Example tags: `VIP`, `commercial`, `difficult-access`, `dogs-in-yard`, `gate-code-required`, `HOA`, `repeat-customer`, `premium-subscriber`, `past-due`, `do-not-text`, `referral-source`.

#### Data Model Changes

**New table**: `customer_tags`

```
customer_tags
├── id: UUID PK
├── customer_id: UUID FK → customers.id (indexed)
├── tag: VARCHAR(100) NOT NULL
├── created_by: UUID FK → staff.id NULL    — who added the tag
├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
│
├── UNIQUE constraint on (customer_id, tag)  — no duplicate tags per customer
├── INDEX on tag                              — for filtering customers by tag
```

This is a separate table (not JSONB) because:
- Enables efficient SQL filtering: "show me all customers tagged `VIP`"
- Supports audit trail (who tagged, when)
- Scales cleanly — no JSON manipulation needed

#### API Changes

**Modify `GET /api/v1/customers`**:
- Add `tags` filter parameter (comma-separated list, matches any)
- Include `tags[]` in `CustomerResponse`

**New endpoints**:
- `POST /api/v1/customers/{id}/tags` — add a tag (body: `{ "tag": "VIP" }`)
- `DELETE /api/v1/customers/{id}/tags/{tag}` — remove a tag
- `GET /api/v1/tags` — list all unique tags in use (for autocomplete/dropdown)

#### Frontend Changes

**Modify `CustomerDetail.tsx`**:
- Tag display as colored chips below customer name
- Add/remove tags with autocomplete input (suggests existing tags)

**Modify `CustomersList.tsx`**:
- Tag filter in sidebar (multi-select, shows tag counts)
- Tags column in list view

#### Architecture Fit

- New model: `CustomerTag` in `src/grins_platform/models/customer_tag.py`
- New repository: `CustomerTagRepository` (simple CRUD)
- Relationship: `Customer.tags` via SQLAlchemy `relationship()` with `selectinload`
- Migration: new `customer_tags` table
- Follows the same pattern as other relational models in the codebase

---

### 5.7 Customer Availability & Preferred Service Times

#### Business Logic

The system requirements specify collecting "customer general availability or requested service times" at intake. This information feeds directly into the scheduling system — when the admin schedules a job, the system should flag conflicts with customer preferences and optimize routes considering preferred time windows.

#### Data Model Changes

**Modify `Customer` model**:

```
customers table additions:
├── preferred_service_times: JSONB NULL
│   Example:
│   {
│     "preferred_days": ["monday", "wednesday", "friday"],
│     "preferred_time_window": "morning",          — morning (8-12), afternoon (12-5), any
│     "availability_notes": "Work from home Tuesdays, prefer mornings",
│     "blackout_dates": ["2026-07-04", "2026-09-01"]
│   }
```

Using JSONB (not separate columns) because:
- Preferences vary widely per customer
- Schema can evolve without migrations
- The scheduling engine (Timefold) already reads job-level constraints — this adds customer-level preferences

**Modify `Lead` model**:

```
leads table addition:
├── preferred_times: VARCHAR(500) NULL    — free-text from intake form
```

On lead conversion, `preferred_times` text is parsed/structured into the customer's `preferred_service_times` JSONB.

#### API Changes

**Modify `POST /api/v1/leads`**:
- Add optional `preferred_times` field (free text)

**Modify `CustomerCreate` / `CustomerUpdate` schemas**:
- Add `preferred_service_times` object field

**Modify schedule generation** (`ScheduleGenerationService`):
- When generating schedules, factor in `customer.preferred_service_times` as a soft constraint
- The Timefold solver already supports soft constraints — add customer time preference as a scoring factor

#### Frontend Changes

**Modify landing page form**:
- Add optional field: "When works best for you?" (dropdown: Morning / Afternoon / No preference)
- Add optional field: "Preferred days" (multi-select checkboxes)

**Modify `CustomerDetail.tsx`**:
- Show/edit preferred service times section
- Display as a readable summary: "Prefers mornings on Mon/Wed/Fri"

---

### 5.8 Work Request Submission Confirmation

#### Business Logic

The system requirements explicitly state: "Make sure there is a text or email confirmation that the work request has been filled out." Every customer who submits a work request (via any channel) should immediately receive confirmation that their request was received and what to expect next.

#### Technical Implementation

This is an automation trigger, not a model change. It hooks into the existing lead creation flow.

**Modify `LeadService.submit_lead()`** (`src/grins_platform/services/lead_service.py`):

After successfully creating a lead (line ~200), add:

```python
# After lead creation, trigger confirmation
if lead.phone and lead.sms_consent:
    await self.sms_service.send_message(
        to_phone=lead.phone,
        message=f"Hi {lead.name}! Your request has been received by Grins Irrigation. "
                f"We'll be in touch within 2 hours during business hours. "
                f"Questions? Call us at (952) 818-1020.",
        message_type=MessageType.LEAD_CONFIRMATION,
    )

if lead.email:
    await self.email_service.send_confirmation(
        to_email=lead.email,
        name=lead.name,
        situation=lead.situation,
    )
```

**For Google Form submissions** (auto-promoted work requests):
- The same confirmation fires when the work request is auto-promoted to a lead
- Add `MessageType.LEAD_CONFIRMATION` to the `MessageType` enum in `models/enums.py`
- The `SentMessage` table already tracks all outbound messages — this gets logged automatically

#### Architecture Fit

- No new models or endpoints needed
- Hooks into existing `LeadService.submit_lead()` and `SMSService`
- Gated on `sms_consent` (see §5.5) — won't send without consent
- Email service integration (see infrastructure requirements in §16)

---

### 5.9 Staff-Entered Client Data (Photos, Videos, Notes)

#### Business Logic

The system requirements call for the central database to store "clients special notes, photos, videos, data" entered by staff — not just what customers submit. This includes property photos, system diagrams, gate codes, pet warnings, access instructions, and any other field observations.

#### Data Model Changes

**New table**: `customer_attachments`

```
customer_attachments
├── id: UUID PK
├── customer_id: UUID FK → customers.id (indexed)
├── property_id: UUID FK → properties.id NULL    — optional, link to specific property
├── job_id: UUID FK → jobs.id NULL                — optional, link to specific job
├── uploaded_by: UUID FK → staff.id NOT NULL
├── file_type: VARCHAR(20) NOT NULL               — 'photo', 'video', 'document'
├── file_url: VARCHAR(500) NOT NULL               — S3/cloud storage URL
├── thumbnail_url: VARCHAR(500) NULL              — for photos/videos
├── caption: VARCHAR(500) NULL                     — description
├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
```

**Modify `Customer` model**:

```
customers table addition:
├── internal_notes: TEXT NULL    — staff-only notes (not visible to customer)
```

This is distinct from any customer-facing notes. Only staff/admin can see `internal_notes`.

#### API Changes

**New endpoints**:
- `POST /api/v1/customers/{id}/attachments` — upload file (multipart form)
- `GET /api/v1/customers/{id}/attachments` — list attachments
- `DELETE /api/v1/customers/{id}/attachments/{attachment_id}` — remove

**Modify `CustomerUpdate` schema**:
- Add `internal_notes` field

#### Infrastructure

- **File storage**: S3-compatible bucket (AWS S3, DigitalOcean Spaces, or Cloudflare R2)
- **Upload flow**: Frontend → presigned URL → direct upload to S3 → store URL in DB
- This avoids routing large files through the FastAPI backend

#### Architecture Fit

- New model: `CustomerAttachment` in `src/grins_platform/models/customer_attachment.py`
- New repository: `CustomerAttachmentRepository`
- New service: `AttachmentService` (handles presigned URLs, validation, cleanup)
- Frontend: file upload component in `CustomerDetail.tsx` (drag-and-drop zone)

---

## 6. New Entity: Service Agreement

This is the missing link between Stripe subscriptions and the job pipeline. The design is inspired by **ServiceTitan's template/instance pattern** (the most mature agreement system in field service CRMs), adapted for Grins' simpler tier structure and integrated with Stripe Billing for payment lifecycle management.

### Key Design Decisions (Confirmed by Viktor)

- **Billing model**: Auto-renewing annual subscription (Stripe handles recurring billing)
- **Tier changes**: NOT allowed mid-season — customer must wait until renewal to upgrade/downgrade
- **Customer portal**: Stripe Customer Portal only (payment method updates, invoice history) — no custom portal
- **Renewal jobs**: Viktor must be **notified and confirm** before next season's jobs are generated
- **Failed payment**: Pause agreement + manual outreach (no auto-retry beyond Stripe's built-in Smart Retries)
- **Zone surcharges**: Skip for now — flat pricing per tier

### Data Model

Following ServiceTitan's approach, we separate the **tier template** (what packages exist and what they include) from the **customer agreement instance** (a specific customer's subscription). This allows changing tier definitions without affecting existing agreements.

```
ServiceAgreementTier (Template — defines what each package includes)
├── id: UUID PK
├── name: VARCHAR(100) NOT NULL              — "Essential", "Professional", "Premium"
├── slug: VARCHAR(50) UNIQUE NOT NULL         — "essential", "professional", "premium"
├── description: TEXT
├── package_type: enum (RESIDENTIAL | COMMERCIAL)
├── annual_price: DECIMAL(10,2) NOT NULL      — $170, $250, $700 (res) / $225, $375, $850 (com)
├── billing_frequency: enum (ANNUAL)          — annual only for now (expandable later)
├── included_services: JSONB NOT NULL
│   Example:
│   [
│     { "service_type": "spring_startup", "frequency": 1, "description": "Spring system activation" },
│     { "service_type": "fall_winterization", "frequency": 1, "description": "Fall blowout & winterization" }
│   ]
├── perks: JSONB NULL
│   Example: ["priority_scheduling", "10_pct_repairs", "emergency_service"]
├── stripe_product_id: VARCHAR(255) NULL      — Stripe Product ID for this tier
├── stripe_price_id: VARCHAR(255) NULL        — Stripe Price ID (recurring annual)
├── is_active: BOOLEAN DEFAULT true
├── display_order: INTEGER DEFAULT 0          — for frontend sorting
├── created_at: TIMESTAMP
├── updated_at: TIMESTAMP

ServiceAgreement (Instance — a specific customer's subscription)
├── id: UUID PK
├── agreement_number: VARCHAR(50) UNIQUE      — "AGR-2026-001" (auto-generated)
├── customer_id: UUID FK → customers.id
├── tier_id: UUID FK → service_agreement_tiers.id
├── property_id: UUID FK → properties.id NULL — linked after onboarding form
│
├── Stripe Integration:
│   ├── stripe_subscription_id: VARCHAR(255) NULL  — Stripe Subscription object ID
│   ├── stripe_customer_id: VARCHAR(255) NULL       — Stripe Customer object ID
│
├── Status & Lifecycle:
│   ├── status: enum (see status flow below)
│   ├── start_date: DATE NOT NULL
│   ├── end_date: DATE NULL                    — start_date + 1 year (NULL for continuous)
│   ├── renewal_date: DATE NULL                — when Stripe will attempt next charge
│   ├── auto_renew: BOOLEAN DEFAULT true
│   ├── cancelled_at: TIMESTAMP NULL
│   ├── cancellation_reason: TEXT NULL
│   ├── pause_reason: TEXT NULL
│
├── Financials:
│   ├── annual_price: DECIMAL(10,2) NOT NULL   — locked at time of purchase (may differ from tier template if tier price changes)
│   ├── payment_status: enum (CURRENT | PAST_DUE | FAILED)
│   ├── last_payment_date: TIMESTAMP NULL
│   ├── last_payment_amount: DECIMAL(10,2) NULL
│
├── Compliance (Minnesota Auto-Renewal Law — MN Stat. 325G.56-325G.62):
│   ├── consent_recorded_at: TIMESTAMP NULL    — when auto-renewal consent was obtained
│   ├── consent_method: VARCHAR(50) NULL       — "web_form", "stripe_checkout", "in_person"
│   ├── disclosure_version: VARCHAR(20) NULL   — version of T&C/disclosures shown at signup
│   ├── last_annual_notice_sent: TIMESTAMP NULL — tracks annual notice (MN requires ≥1/year)
│   ├── last_renewal_notice_sent: TIMESTAMP NULL — tracks 5-30 day pre-renewal notice
│
├── Admin Workflow:
│   ├── renewal_approved_by: UUID FK → staff.id NULL — Viktor confirms before jobs are generated
│   ├── renewal_approved_at: TIMESTAMP NULL
│   ├── notes: TEXT NULL
│
├── Timestamps:
│   ├── created_at: TIMESTAMP
│   ├── updated_at: TIMESTAMP
│
├── Relationships:
│   ├── customer → Customer (many-to-one)
│   ├── tier → ServiceAgreementTier (many-to-one)
│   ├── property → Property (many-to-one, nullable)
│   ├── jobs[] → Job (one-to-many, all jobs spawned by this agreement)
│   └── status_log[] → AgreementStatusLog (one-to-many, audit trail)

AgreementStatusLog (Audit trail for compliance and troubleshooting)
├── id: UUID PK
├── agreement_id: UUID FK → service_agreements.id
├── old_status: VARCHAR(30) NOT NULL
├── new_status: VARCHAR(30) NOT NULL
├── changed_by: UUID FK → staff.id NULL       — NULL if system-triggered
├── reason: TEXT NULL
├── metadata: JSONB NULL                       — extra context (e.g., Stripe event ID)
├── created_at: TIMESTAMP NOT NULL DEFAULT NOW()
```

### Status Flow

```
PENDING (Stripe checkout completed, awaiting onboarding form)
  │
  ▼
ACTIVE (subscription current, jobs generated or ready to generate)
  │
  ├──→ PAST_DUE (Stripe invoice.payment_failed — Smart Retries in progress)
  │       │
  │       ├──→ ACTIVE (Stripe Smart Retries succeed — invoice.paid fires)
  │       │
  │       └──→ PAUSED (Day 7+: all retries failed, payment_collection paused)
  │               │
  │               ├──→ ACTIVE (customer updates card via Stripe Portal → payment succeeds)
  │               │
  │               └──→ CANCELLED (Day 21-30: no resolution after manual outreach)
  │
  ├──→ PENDING_RENEWAL (renewal approaching, awaiting Viktor's approval)
  │       │
  │       ├──→ ACTIVE (Viktor approves → Stripe charges → invoice.paid → next season's jobs generated)
  │       │
  │       └──→ EXPIRED (Viktor rejects or customer doesn't renew)
  │
  ├──→ CANCELLED (customer requests cancellation — cancel future unscheduled jobs)
  │       Cancellation effective at end of current term (customer keeps remaining visits)
  │
  └──→ EXPIRED (term ended, did not renew)
        └──→ ACTIVE (win-back: customer re-subscribes via new Stripe checkout)
```

### Renewal Lifecycle (Viktor's Approval Gate)

This is the critical workflow that ensures Viktor has control over when seasonal jobs are generated, while still using Stripe's automatic billing.

```
T-30 DAYS BEFORE RENEWAL:
──────────────────────────
1. Stripe fires `invoice.upcoming` webhook
2. Backend creates "Pending Renewal" record
3. Agreement status → PENDING_RENEWAL
4. Admin dashboard shows agreement in "Renewal Pipeline" queue
5. SMS/email sent to customer: "Your [tier] plan renews on [date] at $[amount]/yr.
   Manage your subscription: [Stripe Portal link]"
   (Minnesota law requires 5-30 days notice before renewal)

VIKTOR REVIEWS:
───────────────
6. Viktor logs into admin dashboard, sees renewal pipeline
7. Reviews customer account: any open issues? address changes? complaints?
8. Takes ONE of three actions:

   APPROVE RENEWAL:
   → Backend does nothing (lets Stripe auto-charge on renewal date)
   → When Stripe fires `invoice.paid`:
     → Agreement status → ACTIVE (new term)
     → System generates next season's jobs
     → Viktor sees new jobs in "Ready to Schedule" queue

   REJECT / DO NOT RENEW:
   → Backend calls Stripe API: subscription.cancel_at_period_end = true
   → Agreement status → EXPIRED (at end of current term)
   → Customer notified: "Your [tier] plan will not renew on [date]"
   → No new jobs generated

   NEEDS DISCUSSION:
   → Viktor contacts customer directly
   → Can still approve/reject later before renewal date

WHAT IF VIKTOR DOESN'T REVIEW?
──────────────────────────────
9. T-7 days: dashboard shows urgency alert "7 renewals need review"
10. T-1 day: final alert "These renewals auto-process tomorrow"
11. DEFAULT: If no action taken, Stripe auto-charges (safe default — don't lose revenue)
12. After `invoice.paid`, jobs are generated regardless (Viktor can review after)
```

### Failed Payment Workflow

```
DAY 0: Stripe fires `invoice.payment_failed`
──────────────────────────────────────────────
1. Agreement.payment_status → FAILED
2. Agreement.status → PAST_DUE
3. Log status change in AgreementStatusLog
4. Send customer SMS: "Your Grins Irrigation payment didn't go through.
   Update your card here: [Stripe Customer Portal link]"
5. Send customer email with same info + invoice details
6. Admin dashboard shows agreement in "Failed Payment" queue

DAYS 1-7: Stripe Smart Retries (automatic, configured in Stripe Dashboard)
──────────────────────────────────────────────────────────────────────────────
7. Stripe retries at ML-optimized intervals (typically Day 1, 3, 5, 7)
8. If retry succeeds: `invoice.paid` fires → status back to ACTIVE
9. No action needed from Grins — Stripe handles retry logic

DAY 7: If all retries fail — ESCALATE
──────────────────────────────────────
10. Backend calls Stripe API: pause_collection(behavior='keep_as_draft')
    (keeps subscription active but stops charging — invoices accumulate as drafts)
11. Agreement.status → PAUSED
12. Agreement.pause_reason = "Payment failed — all retries exhausted"
13. Admin dashboard moves agreement to "Paused — Needs Outreach" queue
14. Stop generating new jobs for this agreement

DAYS 7-21: Viktor's Manual Outreach
────────────────────────────────────
15. Viktor calls customer personally or sends direct text
16. Logs outreach attempts in agreement notes
17. If customer updates card via Stripe Portal:
    → Resume collection: stripe.subscriptions.update(pause_collection=None)
    → Status back to ACTIVE, resume job generation
18. If customer unreachable or refuses to pay:

DAY 21-30: Cancellation
────────────────────────
19. Backend calls: stripe.subscriptions.cancel(subscription_id)
20. Agreement.status → CANCELLED
21. Agreement.cancellation_reason = "Non-payment after manual outreach"
22. Cancel any future unscheduled jobs linked to this agreement
23. Send cancellation confirmation to customer (Minnesota law requires this)
```

### No Mid-Season Tier Changes

```
RULE: Customers CANNOT upgrade or downgrade mid-season.

WHY: Jobs are pre-generated at purchase. Upgrading mid-season would require:
  - Calculating prorated pricing for partial seasons
  - Generating additional jobs for the upgrade visits
  - Potentially rescheduling existing jobs
  This complexity isn't worth it for a seasonal irrigation business.

IMPLEMENTATION:
  - Stripe Customer Portal: Do NOT enable plan switching
    (Configure portal to hide the "Switch plan" option)
  - Admin dashboard: No "Change Tier" button on active agreements
  - At renewal time: Viktor can approve a tier change for the next season
    by creating a new agreement on the upgraded tier

CUSTOMER COMMUNICATION:
  If customer requests mid-season upgrade:
  "Your current plan runs through [end_date]. We can upgrade you to
   [tier] starting next season. Would you like us to set that up for renewal?"
```

### Stripe Customer Portal Configuration

Since Viktor confirmed **Stripe Customer Portal only** (no custom portal), configure it carefully:

```
ENABLE:
  ✅ Payment method management (critical for failed payment self-service)
  ✅ Invoice history & receipt downloads
  ✅ Billing address management

CONFIGURE WITH CARE:
  ⚠️ Cancellations: ENABLE with "collect cancellation reason" turned on
     Minnesota law REQUIRES online cancellation if you have a website
     with subscription management capability (MN Stat. 325G.60)
     → Cannot require phone call to cancel
     → Must provide click-to-cancel mechanism

DISABLE:
  ❌ Plan switching (no mid-season tier changes)
  ❌ Subscription pausing (admin-only action — Viktor controls this)
  ❌ Quantity changes (not applicable)

PORTAL URL STRATEGY:
  - Store STRIPE_CUSTOMER_PORTAL_URL in Railway env vars
  - Generate per-customer portal sessions via Stripe API (authenticated)
  - Link from: subscription welcome email, renewal notices, admin dashboard
  - NEVER expose portal session creation endpoint publicly
```

### Refund & Cancellation Policy

Both MN auto-renewal law and FTC guidance require that the refund/cancellation policy be disclosed **before purchase**. This policy must appear in the Terms of Service, on the pricing page, and in the pre-checkout confirmation modal.

```
GRINS IRRIGATION REFUND & CANCELLATION POLICY:
───────────────────────────────────────────────

CANCELLATION:
  • Cancel anytime via the Stripe Customer Portal, by calling (952) 818-1020,
    or by emailing info@grinsirrigation.com
  • Cancellation takes effect at the END of the current annual term
  • You retain all remaining service visits through the end of your paid period
  • No early termination fees

REFUNDS — SEASONAL PRORATED APPROACH:
  • Cancelled BEFORE first service visit of the season:
    → Full refund of the annual fee
  • Cancelled AFTER one or more service visits have been completed:
    → Prorated refund based on services NOT yet rendered
    → Formula: annual_price × (remaining_visits / total_visits) = refund amount
    → Example: Premium plan ($700/year, 7 visits), cancelled after 3 visits completed
      → $700 × (4/7) = $400 refund
  • Cancelled AFTER all seasonal services have been completed:
    → No refund (all services rendered)

REFUND PROCESSING:
  • Refunds processed to the original payment method
  • Allow 5-10 business days for refund to appear on statement
  • Refund initiated via Stripe Dashboard (admin action)

NO REFUNDS FOR:
  • Completed service visits
  • Subscription terms that have fully expired
  • Non-payment cancellations (Day 21+ failed payment workflow)

IMPLEMENTATION:
  • Store refund policy version in ServiceAgreement.disclosure_version
  • Track refund amount and reason when processing cancellation:
    → ServiceAgreement.cancellation_refund_amount (DECIMAL, nullable)
    → ServiceAgreement.cancellation_refund_processed_at (TIMESTAMP, nullable)
  • Create CANCELLATION_CONF disclosure_record with refund details
  • Stripe handles actual refund processing — backend calls:
    stripe.Refund.create(charge=original_charge_id, amount=refund_amount_cents)
```

> **ACTION REQUIRED**: This policy must be added to the Terms of Service page (`TermsOfServicePage.tsx`) in the landing page repo and referenced in the pre-checkout modal.

---

## 7. New Entity: Estimate / Quote

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

## 8. Automation Triggers

These are the automated actions the system should perform without admin intervention:

### On New Lead Created (from website form, auto-promoted work request, AI agent, or any channel)

| Trigger | Action | Timing |
|---------|--------|--------|
| Lead created (any source) | **Gate check**: Only send SMS if `sms_consent = true` | Immediate |
| Lead status = NEW + sms_consent | Send SMS: "Thanks for reaching out to Grins Irrigation! We'll call you within 2 hours during business hours." | Immediate |
| Lead status = NEW + has email | Send email confirmation with what to expect | Immediate |
| Lead tagged FOLLOW_UP | Add to Follow-Up Queue, notify admin | Immediate |
| Lead uncontacted for 2 hours | Notify admin (push notification / dashboard alert) | 2 hours |
| Lead uncontacted for 24 hours | Auto-send SMS follow-up: "Just following up on your irrigation request..." (if sms_consent) | 24 hours |
| Lead uncontacted for 72 hours | Auto-send second follow-up via SMS (if sms_consent) | 72 hours |

### On Work Request Submitted (Google Form / Google Sheet)

| Trigger | Action | Timing |
|---------|--------|--------|
| Work request auto-promoted to Lead | Send SMS confirmation: "Your request has been received!" (if phone + sms_consent) | Immediate |
| Work request auto-promoted to Lead | Send email confirmation (if email provided) | Immediate |

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
| `checkout.session.completed` | Create Customer + Service Agreement (status: PENDING) + log PRE_SALE disclosure | Immediate |
| `checkout.session.completed` | Send CONFIRMATION email with all MN-required terms + Stripe Portal link | Immediate |
| `checkout.session.completed` | Create `sms_consent_records` entry from checkout metadata | Immediate |
| Customer completes onboarding form | Create Property, link to agreement, generate seasonal jobs, status → ACTIVE | On form submit |
| `customer.subscription.updated` | Update Service Agreement record, log status change | Immediate |
| `customer.subscription.deleted` | Cancel Service Agreement, cancel future unscheduled jobs, send CANCELLATION_CONF disclosure | Immediate |
| `invoice.payment_failed` | Agreement → PAST_DUE, send customer SMS + email with Stripe Portal link | Immediate |
| `invoice.payment_failed` + Day 7 | If still failed: pause collection, agreement → PAUSED, add to "Failed Payment" queue | Day 7 |
| `invoice.payment_failed` + Day 21 | If still unresolved after manual outreach: cancel subscription | Day 21 |
| `invoice.upcoming` (renewal) | Agreement → PENDING_RENEWAL, send customer RENEWAL_NOTICE (MN law: 5-30 days), add to "Renewal Pipeline" queue for Viktor | 30 days before |
| `invoice.upcoming` + Day 23 | If Viktor hasn't reviewed: show urgency alert "7 renewals need review" | 7 days before |
| `invoice.paid` (renewal) | If Viktor approved (or default): agreement → ACTIVE (new term), generate next season's jobs | Immediate |
| January 1 each year | Send ANNUAL_NOTICE to all active agreement customers (MN law: ≥1/year) | Annually |

### Renewal Approval Workflow (Viktor's Gate)

This is the detailed workflow for the renewal pipeline. See §6 for the full lifecycle description.

```
T-30 days:  invoice.upcoming webhook fires
              │
              ▼
            Agreement status → PENDING_RENEWAL
            Send customer RENEWAL_NOTICE email (MN compliance)
            Add to admin "Renewal Pipeline" queue
              │
              ▼
            Viktor reviews in dashboard:
            ┌───────────────────────────────────────────────────┐
            │ Customer │ Tier │ Renews │ Price │ Visits Done    │
            │                                                    │
            │ [Approve ✓]  [Do Not Renew ✗]  [Needs Discussion]│
            └───────────────────────────────────────────────────┘
              │
    ┌─────────┼──────────────┐
    ▼         ▼              ▼
  Approve   Reject         No action
    │         │              │
    │         ▼              ▼
    │    Cancel at       Stripe auto-charges
    │    period end      on renewal date
    │    (no new jobs)   (safe default: revenue preserved)
    │                        │
    ▼                        ▼
  Stripe charges         invoice.paid fires
  on renewal date        → generate next season's jobs
    │
    ▼
  invoice.paid fires
  → generate next season's jobs
  → Viktor sees new jobs in "Ready to Schedule"
```

---

## 9. Dashboard Tab Structure

### Recommended Navigation

```
┌─────────────────────────────────────────────────────────────┐
│  Dashboard │ Leads │ Customers │ Agreements │ Estimates │   │
│  Jobs │ Schedule │ Invoices │ Work Requests │ Staff │       │
│  Settings                                                   │
└─────────────────────────────────────────────────────────────┘
```

### New Tabs

**Service Agreements** (new — modeled after Housecall Pro's Service Plans dashboard + ServiceTitan's KPIs)

This tab is Viktor's primary view for managing the subscription business. It has two modes: **Business Metrics** (high-level health) and **Operational Queue** (what needs action today). Viktor confirmed both are equally important.

**Business Metrics View (Top of Page)**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SERVICE AGREEMENTS                                                          │
│                                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Active   │  │ MRR      │  │ Renewal  │  │ Churn    │  │ Past Due │     │
│  │   24     │  │ $1,425   │  │ Rate     │  │ Rate     │  │ $425     │     │
│  │ ▲3 new   │  │ ▲$170    │  │  89%     │  │  4.2%    │  │ 2 accts  │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
│                                                                              │
│  ┌────────────────────────────────────┐  ┌────────────────────────────────┐ │
│  │  MRR Over Time (12-month trailing) │  │  Agreements by Tier            │ │
│  │  [═══════════════════════════▲]    │  │  ┌────┐ ┌────┐ ┌────┐        │ │
│  │  (line chart with monthly MRR)     │  │  │ 14 │ │  7 │ │  3 │        │ │
│  │                                     │  │  │Ess │ │Pro │ │Prem│        │ │
│  └────────────────────────────────────┘  │  └────┘ └────┘ └────┘        │ │
│                                           │  (donut or bar chart)         │ │
│                                           └────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**KPI Definitions**:

| KPI | Formula | Target |
|---|---|---|
| **Active Agreements** | Count where status = ACTIVE | Growth metric |
| **MRR (Monthly Recurring Revenue)** | Sum of all active agreement `annual_price` / 12 | Revenue forecasting |
| **Renewal Rate** | (Renewed / Up for Renewal) over trailing 90 days | >85% |
| **Churn Rate** | (Cancelled / Total Active at period start) × 100 over trailing 90 days | <10% annual |
| **Past-Due Amount** | Sum of `annual_price` for agreements with `payment_status = FAILED` | $0 target |
| **ARPA (Avg Revenue Per Agreement)** | MRR / Active Agreements | Upsell indicator |
| **Tier Distribution** | Count per tier (Essential / Professional / Premium) | Track upsell mix |

**Operational Queue View (Below Metrics)**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ACTION REQUIRED                                                             │
│                                                                              │
│  🔄 RENEWAL PIPELINE (5 agreements)                          [Review All →] │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ Johnson, Sarah │ Professional │ Renews Apr 1 │ $250/yr │        │       │
│  │ 3/3 visits completed this season                                 │       │
│  │                              [Approve ✓]  [Do Not Renew ✗]     │       │
│  ├──────────────────────────────────────────────────────────────────┤       │
│  │ Williams, Mike │ Essential │ Renews Apr 5 │ $170/yr │           │       │
│  │ 2/2 visits completed this season                                 │       │
│  │                              [Approve ✓]  [Do Not Renew ✗]     │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  ⚠️ FAILED PAYMENTS (2 agreements)                           [View All →]  │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ Smith, John │ Premium │ Failed Mar 3 │ $700/yr │ PAUSED        │       │
│  │ Last outreach: Mar 5 (called, left voicemail)                    │       │
│  │                         [Log Outreach]  [Resume]  [Cancel]      │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  📅 UNSCHEDULED VISITS (8 visits)                            [View All →]  │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ 4 Spring Startups due by Apr 30 │ 3 Mid-Season Checks due Jul 31│       │
│  │ 1 Monthly Visit due May 31                                       │       │
│  │                                               [Go to Schedule →]│       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                              │
│  ⏰ ONBOARDING INCOMPLETE (1 customer)                       [View All →]  │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ Davis, Emma │ Essential │ Purchased Mar 7 │ No property info    │       │
│  │ Reminder sent Mar 8                                               │       │
│  │                                              [Send Reminder]     │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Agreement Status Tabs** (inspired by Housecall Pro's 7-status model):

| Status Tab | What It Shows |
|---|---|
| **All** | Every agreement regardless of status |
| **Active** | Subscription current, billing up to date |
| **Pending** | Purchased but onboarding not complete (no property info yet) |
| **Pending Renewal** | Approaching renewal, awaiting Viktor's approval |
| **Past Due** | Payment failed, Stripe retrying or paused |
| **Expiring Soon** | Within 30 days of renewal date (before entering Pending Renewal) |
| **Expired** | Term ended, did not renew |
| **Cancelled** | Customer cancelled (with cancellation reason visible) |

**Agreement Detail View**:
- Full agreement info (tier, dates, price, status, property)
- **Linked jobs timeline**: visual timeline showing all seasonal jobs (completed ✓, scheduled 📅, upcoming ○)
- **Jobs remaining**: "2 of 3 visits completed" progress indicator
- **Payment history**: pulled from Stripe (invoices, charges, refunds)
- **Stripe subscription link**: "View in Stripe Dashboard →" (opens Stripe)
- **Compliance log**: all disclosure_records and sms_consent_records for this agreement
- **Notes**: admin notes field
- Actions: Pause, Resume, Cancel (with reason), View Stripe Portal

**Estimates** (new)
- List view: All estimates with status filters
- Kanban option: DRAFT → SENT → VIEWED → APPROVED/REJECTED (visual pipeline)
- Each row shows: Estimate #, customer, property, amount, status, days since sent
- Detail view: Full estimate with line items, customer communication history
- Actions: Send, mark approved/rejected, convert to job, duplicate as template

### Modified Tabs

**Dashboard** — Add widgets:
- "Pending Estimates" count (sent but not approved)
- "Active Agreements" count with trend arrow (vs. prior month)
- "MRR" current month with month-over-month change
- "Jobs Ready to Schedule" count (the key number for Viktor)
- "Revenue This Month" (from Stripe subscriptions + one-off invoices)
- "Leads Awaiting Contact" with time-since-created
- "Follow-Up Queue" count (leads tagged FOLLOW_UP needing admin attention) — admin-only
- "Renewal Pipeline" count — agreements needing Viktor's review before renewal
- "Failed Payments" count + dollar value at risk
- "Leads by Source" chart (pie/bar showing channel breakdown for marketing insights)

**Leads** — Now receives auto-promoted work requests and AI agent leads. Add:
- Source badge showing channel: "Website", "Google Form", "Phone", "Text", "Google Ad", "QR Code", etc.
- Intake tag badge: "Schedule" (green) vs "Follow Up" (orange)
- Time-since-created indicator (urgency signal)
- Quick-filter tabs: "All" | "Schedule" | "Follow Up"
- Consent indicators: SMS opt-in status, T&C accepted
- Follow-Up Queue view (filtered view showing only FOLLOW_UP tagged leads, admin-only)
- Customer tags display (carried over after conversion)

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

## 10. Recommended Status Machines

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
PENDING (checkout completed, awaiting onboarding form or first payment confirmation)
  │
  ▼
ACTIVE (subscription current, jobs generated)
  │
  ├──→ PAST_DUE (invoice.payment_failed — Stripe Smart Retries in progress)
  │       ├──→ ACTIVE (retry succeeds)
  │       └──→ PAUSED (Day 7+: retries exhausted, manual outreach needed)
  │               ├──→ ACTIVE (card updated, payment recovered)
  │               └──→ CANCELLED (Day 21-30: no resolution)
  │
  ├──→ PENDING_RENEWAL (invoice.upcoming — awaiting Viktor's approval)
  │       ├──→ ACTIVE (approved, renewed for next term)
  │       └──→ EXPIRED (rejected or customer didn't renew)
  │
  ├──→ CANCELLED (customer-initiated via Stripe Portal or admin action)
  │
  └──→ EXPIRED (term ended without renewal)
        └──→ ACTIVE (win-back: re-subscribes via new checkout)
```

> See §6 for the full status flow with detailed lifecycle workflows (renewal gate, failed payment escalation).

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

## 11. Stripe Webhook Integration

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

### Payment Links vs. API-Created Checkout Sessions (ARCHITECTURAL DECISION)

The landing page currently uses **Stripe Payment Links** (static URLs like `buy.stripe.com/test_...`). However, the 3-step purchase flow requires passing dynamic data (consent_token, UTM parameters) from Step 1 to Step 2. This is not possible with static Payment Links.

**Decision: Migrate to API-Created Checkout Sessions**

```
CURRENT (Payment Links):
  Landing page has hardcoded Stripe URLs → customer clicks → goes to Stripe
  LIMITATIONS:
    - Cannot pass dynamic metadata (consent_token) per session
    - Cannot set dynamic success_url parameters
    - Cannot programmatically enable automatic_tax
    - Metadata must be set at the Payment Link level (static, same for every customer)

TARGET (API-Created Checkout Sessions):
  Landing page calls backend → backend creates Checkout Session → returns URL → customer redirected
  BENEFITS:
    - Pass consent_token as session metadata (links consent to purchase)
    - Pass UTM params as session metadata (attribution tracking)
    - Enable automatic_tax dynamically
    - Set customer_email if known (prefill from consent form)
    - Full control over session configuration per customer
```

**New Architecture Flow**:

```
Step 1 (Pre-checkout modal) → customer fills consent + clicks "Continue to Checkout"
       │
       ▼
Landing page calls: POST /api/v1/checkout/create-session
  Request body: {
    package_tier: "professional",
    package_type: "residential",
    consent_token: "uuid-from-step-1",
    utm_params: { source: "google", medium: "cpc", campaign: "spring2026" }
  }
       │
       ▼
Backend creates Stripe Checkout Session:
  stripe.checkout.Session.create(
    mode="subscription",
    line_items=[{"price": tier.stripe_price_id, "quantity": 1}],
    success_url="https://grins-irrigation.vercel.app/service-packages?session_id={CHECKOUT_SESSION_ID}",
    cancel_url="https://grins-irrigation.vercel.app/service-packages",
    automatic_tax={"enabled": True},
    phone_number_collection={"enabled": True},
    billing_address_collection="required",
    consent_collection={"terms_of_service": "required"},
    custom_text={
      "terms_of_service_acceptance": {
        "message": "I acknowledge this is an annual auto-renewing subscription."
      }
    },
    subscription_data={
      "metadata": {
        "consent_token": consent_token,
        "package_tier": package_tier,
        "package_type": package_type,
      }
    },
    metadata={
      "consent_token": consent_token,
      "utm_source": utm_params.get("source"),
      "utm_medium": utm_params.get("medium"),
      "utm_campaign": utm_params.get("campaign"),
    }
  )
       │
       ▼
Backend returns: { checkout_url: "https://checkout.stripe.com/c/pay/cs_live_..." }
       │
       ▼
Landing page redirects customer to checkout_url
       │
       ▼
Step 2 (Stripe Checkout) → customer pays → webhook fires with consent_token in metadata
```

**New endpoint**: `POST /api/v1/checkout/create-session` (public, rate-limited)
- Validates package_tier and package_type
- Looks up `ServiceAgreementTier` to get `stripe_price_id`
- Validates consent_token exists in `disclosure_records`
- Creates Stripe Checkout Session with metadata
- Returns the session URL
- Rate limit: 5 requests per IP per minute

**Impact**: The landing page no longer needs hardcoded Stripe Payment Link URLs. Instead, the pricing data (`pricing.ts`) contains `package_tier` + `package_type` identifiers, and the frontend calls the create-session endpoint to get a dynamic checkout URL.

### Backend Implementation Requirements

1. **New endpoint**: `POST /api/v1/webhooks/stripe`
   - Verify Stripe webhook signature using **raw request body** (not parsed JSON — critical for signature verification)
   - Parse event type and route to handler
   - Must be **idempotent** (see Webhook Idempotency section below)
   - **CSRF exemption**: This endpoint must be excluded from any CSRF middleware. Stripe cannot send CSRF tokens. If using a global CSRF middleware in FastAPI, add an explicit exemption for this route.
   - Must return `200 OK` quickly (within 5 seconds). For long-running processing, acknowledge the event and process asynchronously.

2. **New endpoint**: `POST /api/v1/checkout/create-session` (public, rate-limited)
   - Creates a Stripe Checkout Session with consent_token + UTM metadata
   - Validates the consent_token matches a recent disclosure_record
   - Returns the Checkout Session URL for client-side redirect

3. **Stripe SDK**: Add `stripe>=7.0.0` Python package to backend dependencies

4. **Environment variables**:
   - `STRIPE_SECRET_KEY` — for API calls (starts with `sk_live_` in production)
   - `STRIPE_WEBHOOK_SECRET` — for signature verification (starts with `whsec_`)
   - `STRIPE_CUSTOMER_PORTAL_URL` — for linking customers to their portal

5. **Customer matching logic**:
   - On `checkout.session.completed`, extract customer email from Stripe session
   - Search existing customers by email → match if found
   - If no match, create new Customer record
   - Store `stripe_customer_id` on Customer record for future matching

6. **Metadata on Stripe Products** (set once in Stripe Dashboard):
   - Add metadata to each Stripe Product: `package_tier`, `package_type`
   - Also passed dynamically in Checkout Session subscription_data.metadata

### Webhook Idempotency Implementation

Stripe may deliver the same webhook event multiple times. The webhook handler **must** deduplicate to prevent creating duplicate customers, agreements, or jobs.

```
stripe_webhook_events (NEW TABLE — deduplication log)
├── id: UUID PK
├── stripe_event_id: VARCHAR(255) UNIQUE NOT NULL   — Stripe's event ID (evt_xxx)
├── event_type: VARCHAR(100) NOT NULL               — e.g., "checkout.session.completed"
├── processing_status: VARCHAR(20) NOT NULL          — "success", "failed", "skipped_duplicate"
├── error_message: TEXT NULL                         — if processing failed
├── event_data: JSONB NULL                           — full event payload (for debugging/replay)
├── processed_at: TIMESTAMP NOT NULL DEFAULT NOW()
│
├── UNIQUE INDEX on stripe_event_id (prevents duplicates)

IMPLEMENTATION:
──────────────
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    # 1. Get RAW body (must be bytes, not parsed JSON)
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # 2. Verify signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 3. Idempotency check — reject if already processed
    existing = await webhook_event_repo.get_by_stripe_id(event.id)
    if existing:
        return {"status": "already_processed"}

    # 4. Process event
    try:
        handler = EVENT_HANDLERS.get(event.type)
        if handler:
            await handler(event)
        status = "success"
        error = None
    except Exception as e:
        status = "failed"
        error = str(e)
        logger.error(f"Webhook processing failed: {event.type} {event.id}: {e}")

    # 5. Record event (even if processing failed — prevents infinite retries)
    await webhook_event_repo.create(
        stripe_event_id=event.id,
        event_type=event.type,
        processing_status=status,
        error_message=error,
        event_data=event.data.object if status == "failed" else None,
    )

    # 6. Return 200 even on processing failure (to prevent Stripe from retrying endlessly)
    # Failed events are logged and can be replayed manually
    return {"status": status}
```

### Consent Token → Stripe Session Linkage

The pre-checkout consent (Step 1) creates consent records **before** the customer's identity is known. Here's how the records get linked to the final ServiceAgreement:

```
LINKAGE FLOW:
─────────────
Step 1: Customer clicks "Continue to Checkout" on modal
  → POST /api/v1/onboarding/pre-checkout-consent
  → Creates sms_consent_records (customer_id=NULL, phone_number=NULL)
  → Creates disclosure_records (customer_id=NULL, agreement_id=NULL)
  → Returns consent_token (UUID) — stored in sessionStorage

Step 1→2: Landing page calls POST /api/v1/checkout/create-session
  → Passes consent_token in request body
  → Backend embeds consent_token in Checkout Session metadata AND subscription_data.metadata
  → Returns checkout URL → customer redirected

Step 2: Customer completes Stripe Checkout
  → Stripe fires checkout.session.completed webhook with metadata.consent_token
  → Backend webhook handler:
    1. Extract consent_token from event.data.object.metadata
    2. Create Customer record (from Stripe customer_details: email, name, phone, address)
    3. Create ServiceAgreement (linked to Customer)
    4. UPDATE sms_consent_records SET customer_id=customer.id, phone_number=customer.phone
       WHERE consent_token matches the records created in Step 1
    5. UPDATE disclosure_records SET customer_id=customer.id, agreement_id=agreement.id
       WHERE consent_token matches the records created in Step 1
    6. Now all consent/compliance records are fully linked

Step 3: Customer completes onboarding form (optional)
  → POST /api/v1/onboarding/complete with session_id
  → Backend verifies session, links Property to Agreement

EDGE CASE — Customer abandons checkout after Step 1:
  → Orphaned consent records remain (customer_id=NULL, consent_token set)
  → These are harmless — they prove consent was captured even if purchase wasn't completed
  → Cleanup: APScheduler job can mark records older than 30 days with no linked customer as "abandoned"
```

**Data model addition for consent_token linkage**:
```
sms_consent_records: add column consent_token: UUID NULL (indexed)
disclosure_records: add column consent_token: UUID NULL (indexed)
```

### Test-to-Live Migration Checklist

The landing page currently uses **test mode** Stripe Payment Links (`buy.stripe.com/test_...`). Before go-live:

1. **Create live Stripe Products** for all 6 packages (3 residential + 3 commercial)
2. **Add metadata** to each product: `package_tier` (essential/professional/premium), `package_type` (residential/commercial)
3. **Generate live Payment Links** and update the landing page's `ServicePackagesPage.tsx` pricing data
4. **Register webhook endpoint** in Stripe Dashboard → Developers → Webhooks → Add endpoint
   - URL: `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/stripe`
   - Events to listen for: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.paid`
5. **Set environment variables** on Railway:
   - `STRIPE_SECRET_KEY` (live key, starts with `sk_live_`)
   - `STRIPE_WEBHOOK_SECRET` (from webhook registration, starts with `whsec_`)
   - `STRIPE_CUSTOMER_PORTAL_URL` (Stripe Customer Portal URL)
6. **Update Stripe Checkout `success_url`** to include `{CHECKOUT_SESSION_ID}`:
   - `success_url: "https://grins-irrigation.vercel.app/service-packages?session_id={CHECKOUT_SESSION_ID}"`
   - This lets the post-purchase onboarding form verify the purchase
7. **Add `invoice.upcoming` event** to webhook listener (needed for renewal approval workflow)

### Stripe Dashboard Configuration Checklist

Before go-live, the following must be configured in the Stripe Dashboard (not via code):

```
ACCOUNT SETUP:
  [ ] Business verification completed (legal name, EIN, address, industry)
  [ ] Bank account connected for payouts
  [ ] Two-factor authentication enabled on Stripe account
  [ ] Statement descriptor set: "GRINS IRRIGATION" (appears on customer bank statements)

PRODUCTS & PRICES:
  [ ] 6 Products created (Essential/Professional/Premium × Residential/Commercial)
  [ ] Each Product has metadata: package_tier, package_type
  [ ] Each Product has 1 recurring Price (interval=year, currency=USD)
  [ ] Prices match landing page display prices ($170, $250, $700, $225, $375, $850)

TAX (Stripe Tax):
  [ ] Stripe Tax enabled (Settings → Tax)
  [ ] Minnesota tax registration added (MN Tax ID required — see §5.5.7)
  [ ] Business origin address set
  [ ] Tax behavior: "exclusive" (tax added on top of listed price)

CUSTOMER PORTAL:
  [ ] Portal enabled (Settings → Billing → Customer portal)
  [ ] Payment method management: ENABLED
  [ ] Invoice history / receipt downloads: ENABLED
  [ ] Billing address management: ENABLED
  [ ] Subscription cancellation: ENABLED with "collect cancellation reason"
  [ ] Plan switching: DISABLED (no mid-season tier changes — §6)
  [ ] Subscription pausing: DISABLED (admin-only action)
  [ ] Quantity changes: DISABLED
  [ ] Branding: Grin's colors/logo applied
  [ ] Return URL: set to landing page URL

BILLING:
  [ ] Smart Retries enabled (Settings → Billing → Revenue recovery)
  [ ] Retry schedule: default ML-optimized (up to 8 attempts over ~2 weeks)
  [ ] Failed payment emails: enabled via Stripe (supplements our custom emails)
  [ ] Invoice auto-advance: enabled
  [ ] Receipt emails: enabled (Stripe sends automatic receipts)

WEBHOOKS:
  [ ] Endpoint registered: https://[railway-url]/api/v1/webhooks/stripe
  [ ] Events selected: checkout.session.completed, customer.subscription.updated,
      customer.subscription.deleted, invoice.payment_failed, invoice.paid,
      invoice.upcoming
  [ ] Webhook signing secret saved to Railway env vars

BRANDING:
  [ ] Business name: "Grin's Irrigation & Landscaping, LLC"
  [ ] Logo uploaded
  [ ] Brand color set
  [ ] Support email: info@grinsirrigation.com
  [ ] Support phone: (952) 818-1020
```

### Purchase Flow: 3-Step Approach (Approved)

The current landing page shows a simple "Thanks!" banner after purchase. The target flow uses a **3-step approach** that handles compliance (MN auto-renewal disclosures + TCPA consent) before payment and collects property details after payment.

```
CURRENT FLOW (broken):
  Customer clicks Subscribe → Stripe Checkout (test mode)
  → Stripe processes payment → redirects to ?payment=success
  → Landing page shows "Thanks!" banner → DEAD END
  → Backend has NO idea a purchase happened

TARGET FLOW (3 steps):

STEP 1: PRE-CHECKOUT CONFIRMATION MODAL (on landing page)
─────────────────────────────────────────────────────────
  Customer clicks "Subscribe" on pricing card
       │
       ▼
  Landing page shows confirmation modal:
  ┌──────────────────────────────────────────────────────────┐
  │  Confirm Your Subscription                                │
  │                                                            │
  │  [tier] Plan — $[price]/year                              │
  │                                                            │
  │  SUBSCRIPTION TERMS:                                      │
  │  • Billed annually at $[price]/year                       │
  │  • Auto-renews each year until you cancel                 │
  │  • Cancel anytime via your account portal                 │
  │  • Cancellation effective at end of current term          │
  │  • No minimum commitment beyond current term              │
  │                                                            │
  │  [☐] I agree to the Terms & Conditions (required)        │
  │                                                            │
  │  [☐] I consent to receive automated text messages from    │
  │      Grin's Irrigation & Landscaping, LLC at the phone    │
  │      number provided during checkout, including           │
  │      appointment reminders, service updates, and          │
  │      promotional messages about our services. Message     │
  │      and data rates may apply. Approx. 2-8 msgs/month    │
  │      during service season. Reply STOP to unsubscribe     │
  │      at any time. Reply HELP for help. Consent is not     │
  │      a condition of purchase. (required)                  │
  │                                                            │
  │  [Continue to Checkout →]  (disabled until boxes checked) │
  └──────────────────────────────────────────────────────────┘

  WHY THIS STEP EXISTS:
  - MN Stat. 325G.57 requires all 5 auto-renewal disclosures BEFORE purchase
  - TCPA requires SMS consent BEFORE the first automated text (our welcome SMS)
  - Both are captured in one clean modal — not a separate page

  ON "Continue to Checkout" CLICK:
  - Store consent data immediately (timestamp, IP, user agent, consent language version)
  - Create sms_consent_records entry (even before payment — consent is for messaging, not purchase)
  - Create disclosure_records entry (PRE_SALE disclosure)
  - Store consent token in sessionStorage (for post-purchase form to reference)
  - Redirect to Stripe Checkout URL


STEP 2: STRIPE CHECKOUT (hosted by Stripe — we don't build this UI)
────────────────────────────────────────────────────────────────────
  Stripe Checkout natively collects (when configured on the Payment Link or Checkout Session):
  - Email (always required by Stripe)
  - Full name (configure as required)
  - Phone number (configure as required)
  - Billing address — street, city, state, zip (configure as required)

  All retrievable via:
  - checkout.session.completed webhook → session.customer_details (email, name, phone)
  - Stripe Customer object → customer.address (billing address)
  - Stripe Checkout Session → session.customer_details.address

  STRIPE CHECKOUT CONFIGURATION:
  - Configure Payment Links to collect: name, phone, billing address (all required)
  - Set success_url: "https://grins-irrigation.vercel.app/service-packages?session_id={CHECKOUT_SESSION_ID}"
  - Add metadata to each Payment Link: package_tier, package_type
  - This means Stripe handles address/phone validation — we don't need to build those fields

  WHY USE STRIPE'S NATIVE FIELDS:
  - Stripe already has validated address/phone collection built
  - Saves development time vs building our own form
  - PCI-compliant — card data never touches our servers
  - We get billing address which often IS the service address


STEP 3: POST-PURCHASE ONBOARDING FORM (on landing page, after redirect)
───────────────────────────────────────────────────────────────────────
  Stripe redirects to ?session_id=cs_xxx
       │
       ▼
  Landing page detects session_id in URL
       │
       ▼
  Calls backend: GET /api/v1/onboarding/verify-session?session_id=cs_xxx
  Backend verifies with Stripe API, returns: customer_name, package_tier, package_type, address
       │
       ▼
  Shows post-purchase onboarding form (SERVICE-SPECIFIC details only):
  ┌──────────────────────────────────────────────────────────┐
  │  Welcome to Grin's Irrigation [tier] Plan!                │
  │                                                            │
  │  Tell us about your property so we can schedule           │
  │  your first visit:                                         │
  │                                                            │
  │  Is the service address the same as your billing          │
  │  address ([billing address from Stripe])?                 │
  │  (●) Yes  ( ) No                                         │
  │                                                            │
  │  [If No — show service address fields:]                   │
  │  Street Address: [________________________]               │
  │  City:           [________________________]               │
  │  State:          [MN___]                                  │
  │  Zip Code:       [_____]                                  │
  │                                                            │
  │  Number of irrigation zones: [___] (if known, optional)   │
  │  Gate code: [___________] (optional)                      │
  │  Dogs on property? [ ] Yes                                │
  │  Special access instructions: [__________________]        │
  │  Preferred service times:                                  │
  │    ( ) Morning  ( ) Afternoon  ( ) No preference          │
  │                                                            │
  │  [Submit & Get Started →]                                 │
  └──────────────────────────────────────────────────────────┘
       │
       ▼
  Form submits to: POST /api/v1/onboarding/complete
  Backend creates/updates Property record, links to Customer + ServiceAgreement
       │
       ▼
  Landing page shows final confirmation:
  "You're all set! We'll schedule your first visit soon.
   Manage your subscription anytime: [Stripe Portal link]"

  NOTE: Consent checkboxes are NOT on this form — they were already captured
  in Step 1 (the pre-checkout modal). This form is purely for property details.
```

### Why 3 Steps Instead of 2

The previous blueprint version had consent checkboxes on the post-purchase form (Step 3). This is problematic because:

1. **TCPA violation**: The welcome SMS fires on `checkout.session.completed` (Step 2 completion). If consent isn't captured until Step 3, the welcome SMS is sent WITHOUT consent.
2. **MN law violation**: Auto-renewal disclosures must be shown BEFORE the customer accepts the subscription, not after payment.
3. **Customer may skip Step 3**: If they close the browser after payment, we'd have no consent on record at all.

The pre-checkout modal (Step 1) solves all three issues. Consent is captured before payment, so the welcome SMS is immediately legal.

### Backend Endpoints (in `Grins_irrigation_platform`)

1. `GET /api/v1/onboarding/verify-session?session_id=cs_xxx` (public)
   - Calls Stripe API to verify the checkout session
   - Returns: customer name, email, phone, billing address, package tier/type, payment status
   - Used by landing page to show personalized onboarding form with address pre-filled

2. `POST /api/v1/onboarding/complete` (public, rate-limited)
   - Accepts: session_id, service_address_same_as_billing (bool), service_address (optional), zone_count, gate_code, has_dogs, access_instructions, preferred_times
   - If service_address_same_as_billing: uses billing address from Stripe
   - Creates/updates Property record linked to the Customer created by the webhook
   - Returns: success confirmation + Stripe Customer Portal URL

3. `POST /api/v1/onboarding/pre-checkout-consent` (public, rate-limited)
   - Called from Step 1 modal when customer clicks "Continue to Checkout"
   - Accepts: package_tier, package_type, sms_consent (bool), terms_accepted (bool), consent_ip, consent_user_agent, consent_language_version
   - Creates `sms_consent_records` entry + `disclosure_records` entry (PRE_SALE)
   - Returns: consent_token (UUID) — stored in sessionStorage, sent to onboarding/complete for linking

### What if the Customer Doesn't Complete Step 3?

The automated communication sequence (§15, Sequence 4) handles this:
- T+24 hours: SMS reminder with link back to onboarding form (legal — consent captured in Step 1)
- T+72 hours: Second reminder
- T+7 days: Admin notification — "Customer purchased [tier] but hasn't provided property info"
- Viktor can manually reach out and enter the info

**Crucially**: Even without Step 3, we still have enough data from Stripe (name, email, phone, billing address) to:
- Create the Customer record
- Create the Service Agreement
- Generate seasonal jobs (address from Stripe billing info)
- Send all automated communications (consent from Step 1)

Step 3 is for service-specific details (zones, gate code, dogs) that improve job execution — not blockers.

### Landing Page Changes (in `Grins_irrigation` repo)

1. **New component**: `SubscriptionConfirmModal.tsx`
   - Shows MN auto-renewal disclosures (5 required items)
   - Shows TCPA consent checkbox with compliant language
   - Shows T&C checkbox
   - Disabled "Continue to Checkout" button until both checkboxes checked
   - On submit: calls `POST /api/v1/onboarding/pre-checkout-consent`, stores consent_token, redirects to Stripe

2. **Modify ServicePackagesPage**: Subscribe buttons open the modal instead of linking directly to Stripe

3. **New component**: `PostPurchaseOnboarding.tsx`
   - Detects `session_id` query param
   - Calls verify-session endpoint
   - Shows property details form (no consent checkboxes — already captured)
   - Submits to onboarding/complete endpoint
   - Shows final confirmation with Stripe Portal link

4. **Remove old success banner**: Replace `?payment=success` detection with `?session_id` detection

---

## 12. Seasonal Job Auto-Generation

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

## 13. Commercial vs. Residential Handling

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

## 14. Scheduling UX: "Ready to Schedule" View

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

## 15. Automated Communication Sequences

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

## 16. Infrastructure Requirements

This section consolidates all infrastructure dependencies that must be in place before the automation features can work. These are the foundational services and tools that multiple features depend on.

### 16.1 Background Task Scheduler (CRITICAL — Blocks All Timed Automation)

**Current state**: No background task scheduler exists. The only background process is the Google Sheets poller, which uses a simple `asyncio` loop inside the FastAPI process. This is not a general-purpose scheduler.

**Why it's critical**: Every time-delayed automation in §8 and §15 is blocked without this:
- Lead follow-up sequences (T+2h admin alert, T+24h SMS, T+72h re-engagement)
- Estimate reminders (T+48h, T+5d, T+25d)
- Invoice payment reminders (T+7d, T+14d, T+30d)
- Subscription renewal notifications (T-30d)
- Post-purchase onboarding reminders (T+24h)

**Recommended approach**: **APScheduler** (lightweight, runs in-process) for Phase 1, migrate to **Celery + Redis** if scale demands it.

```
APScheduler Architecture:
─────────────────────────
FastAPI startup hook:
  → Initialize AsyncIOScheduler
  → Register recurring jobs:
      • check_uncontacted_leads()    — every 30 min
      • check_estimate_followups()   — every 1 hour
      • check_invoice_reminders()    — every 1 hour
      • check_subscription_renewals() — daily at 9 AM
      • check_onboarding_incomplete() — every 6 hours

Each job queries the database for records matching timing criteria,
then dispatches SMS/email via existing SMSService + new EmailService.

Job store: PostgreSQL (apscheduler table) for persistence across restarts.
```

**Implementation in platform repo**:
- New file: `src/grins_platform/services/scheduler_service.py`
- New file: `src/grins_platform/services/automation_jobs.py` (individual job definitions)
- Modify `app.py` to start scheduler on FastAPI `startup` event
- Add `apscheduler` to `requirements.txt`

### 16.2 Email Service (CRITICAL — No Email Capability Exists)

**Current state**: Neither repo has any email sending capability. No SendGrid, no AWS SES, no SMTP. The only outbound communication channel is Twilio SMS.

**Why it's critical**: Multiple features require email:
- Lead submission confirmation email
- Estimate delivery (formatted quote with line items)
- Invoice sending (PDF or formatted email)
- Subscription welcome email with portal link
- MN auto-renewal confirmation email (legally required — §5.5.2)
- Pre-renewal notice (legally required — §5.5.2)
- Annual notice (legally required — §5.5.2)
- Cancellation confirmation (legally required — §5.5.2)
- Post-purchase onboarding form link
- Follow-up sequences use email as a secondary channel

**Chosen approach**: **Resend** — build our own compliance layer on top of Resend's delivery infrastructure.

**Why Resend (not a full-service platform like Brevo)**:
- **Free tier**: 100 emails/day, 3,000/month — more than enough for current scale
- **Simple Python SDK**: `resend` package, clean async-compatible API
- **Cost**: Free → $20/month (Pro) when volume increases
- **Developer-friendly**: No UI builder bloat — templates are code (Jinja2), automation is code (APScheduler)
- **We own the compliance logic**: Suppression list, unsubscribe handling, CAN-SPAM headers — all in our codebase
- **No vendor lock-in**: If we outgrow Resend, swap the delivery layer without changing templates or business logic

```
EmailService Architecture:
──────────────────────────
src/grins_platform/services/email_service.py

EmailService
├── Dependencies:
│   ├── resend (Python SDK — pip install resend)
│   └── Template renderer (Jinja2 — already available via FastAPI)
│
├── Core Methods (see §5.5.6 for transactional vs commercial separation):
│   ├── send_transactional(to, template, context)
│   │   - No suppression check (always deliver)
│   │   - Uses FROM: noreply@grinsirrigation.com
│   │   - Templates: confirmation, invoice, receipt, renewal_notice,
│   │     onboarding_reminder, failed_payment_notice, cancellation_conf
│   │
│   ├── send_commercial(to, template, context)
│   │   - CHECK suppression list → skip if suppressed
│   │   - CHECK customer.email_opt_in → skip if false
│   │   - Auto-inject: unsubscribe link, physical address, ad identification
│   │   - Uses FROM: info@grinsirrigation.com
│   │   - Templates: seasonal_reminder, review_request, promotional_offer
│   │
│   ├── process_unsubscribe(token) → see §5.5.6
│   ├── generate_unsubscribe_token(customer_id, email) → signed, 30+ day validity
│   └── check_suppression(email) → bool
│
├── Convenience Methods (call send_transactional or send_commercial internally):
│   ├── send_lead_confirmation(to, name, situation)             — transactional
│   ├── send_estimate(to, estimate: Estimate)                   — transactional
│   ├── send_invoice(to, invoice: Invoice)                      — transactional
│   ├── send_subscription_welcome(to, name, tier, portal_url)   — transactional
│   ├── send_subscription_confirmation(to, agreement)           — transactional (MN law §5.5.2)
│   ├── send_renewal_notice(to, agreement)                      — transactional (MN law §5.5.2)
│   ├── send_annual_notice(to, agreement)                       — transactional (MN law §5.5.2)
│   ├── send_cancellation_confirmation(to, agreement)           — transactional (MN law §5.5.2)
│   ├── send_failed_payment_notice(to, agreement)               — transactional
│   ├── send_onboarding_reminder(to, name, form_url)            — transactional
│   ├── send_payment_reminder(to, invoice, reminder_number)     — transactional
│   ├── send_review_request(to, name, review_url)               — COMMERCIAL
│   ├── send_seasonal_reminder(to, name, service_type)          — COMMERCIAL
│   └── send_custom(to, subject, template_name, context)        — caller specifies type
│
├── Templates (Jinja2 HTML):
│   └── src/grins_platform/templates/email/
│       ├── base.html                    — shared layout with Grin's branding
│       ├── base_commercial.html         — extends base, adds unsubscribe footer (§5.5.6)
│       ├── lead_confirmation.html
│       ├── estimate.html
│       ├── invoice.html
│       ├── subscription_welcome.html    — includes MN disclosure terms + portal link
│       ├── subscription_confirmation.html — MN law: all 5 offer terms + cancellation procedure
│       ├── renewal_notice.html          — MN law: renewal date, price, how to cancel
│       ├── annual_notice.html           — MN law: current terms + how to terminate
│       ├── cancellation_confirmation.html — refund details if applicable
│       ├── failed_payment.html
│       ├── payment_reminder.html
│       ├── review_request.html          — uses base_commercial (includes unsubscribe)
│       └── seasonal_reminder.html       — uses base_commercial (includes unsubscribe)
│
├── Configuration:
│   ├── RESEND_API_KEY (env var — add to Railway)
│   ├── TRANSACTIONAL_FROM = "noreply@grinsirrigation.com"
│   ├── COMMERCIAL_FROM = "info@grinsirrigation.com"
│   ├── FROM_NAME = "Grin's Irrigation & Landscaping"
│   └── COMPANY_ADDRESS = "[Viktor: provide before launch]"
│
├── DNS Setup (required for Resend):
│   └── Add DNS records to grinsirrigation.com:
│       ├── SPF record (TXT)
│       ├── DKIM record (TXT — Resend provides the key)
│       ├── DMARC record (TXT — recommended: v=DMARC1; p=quarantine)
│       └── Resend verifies domain ownership before sending
│
├── Tracking:
│   └── Log all sent emails in SentMessage table (reuse existing model)
│       Add email_id to SentMessage, extend MessageType enum with email types
│       Store: recipient, template_name, email_type (transactional/commercial),
│              resend_message_id, delivery_status
│
├── Resend SDK Usage:
│   import resend
│   resend.api_key = settings.RESEND_API_KEY
│
│   # Transactional email
│   resend.Emails.send({
│       "from": "noreply@grinsirrigation.com",
│       "to": customer_email,
│       "subject": subject,
│       "html": rendered_template,
│       "headers": {"X-Entity-Ref-ID": str(uuid4())},  # prevents Gmail threading
│   })
│
│   # Commercial email (with unsubscribe headers)
│   resend.Emails.send({
│       "from": "info@grinsirrigation.com",
│       "to": customer_email,
│       "subject": subject,
│       "html": rendered_template,  # already includes unsubscribe link via base_commercial.html
│       "headers": {
│           "List-Unsubscribe": f"<{unsubscribe_url}>",
│           "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
│       },
│   })
```

### 16.3 Stripe Python SDK

**Current state**: Not installed. The `PaymentMethod` enum includes `STRIPE` and the Invoice model has `payment_reference` but no actual Stripe integration code exists.

**Implementation**:
- Add `stripe>=7.0.0` to `requirements.txt`
- New config: `src/grins_platform/config/stripe_config.py`
- Environment variables (Railway):
  - `STRIPE_SECRET_KEY` (live key)
  - `STRIPE_WEBHOOK_SECRET` (from webhook registration)
  - `STRIPE_CUSTOMER_PORTAL_URL`
- See §11 for full webhook implementation details

### 16.4 Redis (Optional — For AI Conversation State)

**Current state**: No Redis. The Google Sheets poller uses in-memory state.

**When needed**: Phase 2, when the AI conversational agent handles multi-turn SMS conversations. Each phone number needs a conversation history stored temporarily (24-hour TTL).

**Alternative**: For Phase 1, use the existing `ai_audit_log` table or a new `conversation_sessions` table in PostgreSQL. Redis is only needed if conversation volume exceeds what Postgres can handle efficiently.

### 16.5 S3-Compatible File Storage (For Attachments)

**Current state**: No file storage. No upload endpoints.

**When needed**: Phase 3, for customer attachments (property photos, system diagrams, receipts).

**Options**: AWS S3, DigitalOcean Spaces, Cloudflare R2. Recommendation: Cloudflare R2 (no egress fees, S3-compatible API).

### 16.6 Google Analytics & Tag Manager (Landing Page)

**Current state**: GTM and GA4 script tags exist in the landing page's `index.html` but use **placeholder IDs** (`GTM-XXXXXXX`, `G-XXXXXXXXXX`). Analytics events are being fired to `window.dataLayer` (form submissions, phone clicks, chatbot interactions, scroll depth, CTA clicks) but no platform is receiving them.

**Fix**: Replace placeholder IDs with real GTM container ID and GA4 measurement ID. This enables:
- Conversion tracking for lead form submissions
- Campaign attribution via UTM parameters
- Chatbot engagement analytics
- Source/medium reporting for marketing dashboard

---

## 17. Landing Page Fixes (Critical)

These are issues in the **`Grins_irrigation` repo** (landing page) that must be fixed for the automation to work. They are ordered by severity.

### 17.1 Wire Up SMS Consent Checkbox (BLOCKER)

**File**: `Grins_irrigation/frontend/src/features/lead-form/components/LeadForm.tsx`

**Problem**: The SMS consent checkbox is rendered visually but has no `onChange` handler, no state variable, and is not included in the form payload. It's purely decorative.

**Fix**:
1. Add `smsConsent: boolean` to `LeadFormFields` type
2. Add `useState` for smsConsent (default: `false`)
3. Wire checkbox `onChange` to update state
4. Include `sms_consent: smsConsent` in the payload sent to `POST /api/v1/leads`
5. Make checkbox required (cannot submit without consenting to receive automated texts)

**Backend coordination**: Add `sms_consent: bool = False` to `LeadSubmission` schema in platform repo first, deploy, then update landing page.

### 17.2 Add Terms & Conditions Checkbox (BLOCKER)

**Problem**: No T&C acceptance checkbox exists on the lead form. The form footer links to the privacy policy page but doesn't require explicit agreement.

**Fix**:
1. Add checkbox: "I agree to the [Terms & Conditions](/terms-of-service)" (required)
2. Add `termsAccepted: boolean` to `LeadFormFields` type
3. Include `terms_accepted: termsAccepted` in payload
4. Block form submission if not checked

### 17.3 Send Property Type in Payload (HIGH)

**Problem**: The form collects `propertyType` (residential/commercial/government) via radio buttons but does not include it in the API payload.

**Fix**: Add `property_type: propertyType` to the payload object in the form submission handler.

**Backend coordination**: Add `property_type: str | None = None` to `LeadSubmission` schema.

### 17.4 Send Referral Source in Payload (HIGH)

**Problem**: The form collects "How did you hear about us?" (Google, Referral, Facebook, Instagram, Yard Sign, Nextdoor, Other) but does not include it in the API payload.

**Fix**: Add `referral_source: referralSource` to the payload.

**Backend coordination**: Add `referral_source: str | None = None` to `LeadSubmission` schema. This maps to the `lead_source` or `source_detail` field on the Lead model.

### 17.5 Add UTM Parameter Tracking (HIGH)

**Problem**: No URL parameter parsing. When customers arrive from Google Ads, social media ads, QR codes, or email campaigns with UTM parameters, those parameters are completely ignored.

**Fix**:
1. On page load, parse `window.location.search` for UTM params (`utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`)
2. Store in a React context or module-level variable (persist across page navigation within SPA)
3. Include as `source_detail` in the lead submission payload
4. Also derive `lead_source` from `utm_source` when available:
   - `utm_source=google` + `utm_medium=cpc` → `lead_source: "google_ad"`
   - `utm_source=facebook` → `lead_source: "social_media"`
   - `utm_source=qr` → `lead_source: "qr_code"`
   - No UTM params → `lead_source: "website"` (organic)

**Implementation**:
```typescript
// New utility: src/shared/utils/utmTracking.ts
export function captureUTMParams(): UTMParams {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get('utm_source'),
    utm_medium: params.get('utm_medium'),
    utm_campaign: params.get('utm_campaign'),
    utm_content: params.get('utm_content'),
    utm_term: params.get('utm_term'),
  };
}

export function deriveLeadSource(utm: UTMParams): string {
  if (utm.utm_source === 'google' && utm.utm_medium === 'cpc') return 'google_ad';
  if (utm.utm_source === 'facebook' || utm.utm_source === 'instagram') return 'social_media';
  if (utm.utm_source === 'qr') return 'qr_code';
  if (utm.utm_source === 'email') return 'email_campaign';
  if (utm.utm_source === 'sms') return 'text_campaign';
  return 'website';
}
```

Call `captureUTMParams()` in `App.tsx` on mount, store in context, inject into lead form submission.

### 17.6 Build Pre-Checkout Confirmation Modal (BLOCKER)

**Problem**: When a customer clicks "Subscribe", they are sent directly to Stripe Checkout with no opportunity to capture SMS consent or show MN auto-renewal disclosures. This means:
- The welcome SMS sent on `checkout.session.completed` is a TCPA violation (no consent captured yet)
- The MN auto-renewal disclosure requirement (MN Stat. 325G.57) is not met (disclosures must appear before purchase)

**Fix**: Build `SubscriptionConfirmModal.tsx` that intercepts the Subscribe button click and shows:
1. The 5 MN-required auto-renewal disclosures
2. T&C acceptance checkbox (required)
3. SMS consent checkbox with full TCPA-compliant language (required)
4. "Continue to Checkout →" button (disabled until checkboxes are checked)

On submit: call `POST /api/v1/onboarding/pre-checkout-consent` to record consent, then redirect to Stripe Checkout URL.

See §11 for the full 3-step purchase flow design.

### 17.7 Build Post-Purchase Onboarding Form (HIGH)

**Problem**: After Stripe checkout, the landing page shows a static "Thanks!" banner. No property info is collected. See §11 for the full onboarding flow design.

**Fix**: Build `PostPurchaseOnboarding.tsx` that detects `session_id` in the URL. Calls `GET /api/v1/onboarding/verify-session` to get customer/package data. Shows property details form (service address, zone count, gate code, dogs, access notes, preferred times). No consent checkboxes needed — those were captured in the pre-checkout modal (§17.6).

### 17.8 Replace Stripe Test Links with Live Links (BEFORE LAUNCH)

**Problem**: All 6 Stripe Payment Links use `buy.stripe.com/test_...` URLs.

**Fix**: Create live Stripe Products with proper metadata (package_tier, package_type), configure Payment Links to collect name + phone + billing address, generate live links, and update the `pricingData` array in `ServicePackagesPage.tsx`. See §11 test-to-live checklist.

### 17.9 Configure Real GTM/GA4 IDs (MEDIUM)

**Problem**: `GTM-XXXXXXX` and `G-XXXXXXXXXX` placeholders in `index.html`.

**Fix**: Create GTM container and GA4 property in Google Analytics, replace placeholder IDs.

### 17.10 Update Terms of Service Page (HIGH — Compliance)

**File**: `Grins_irrigation/frontend/src/features/legal/components/TermsOfServicePage.tsx`

**Problem**: The existing TOS page includes generic SMS terms but does NOT include the MN auto-renewal disclosures required by 325G.57 or the refund/cancellation policy. The pre-checkout modal references the TOS page — customers will click through to read it, and it must be complete.

**Required additions to TOS**:
1. **Auto-Renewal Terms section** — All 5 MN pre-sale disclosures (§5.5.2):
   - Service continues until consumer terminates
   - Cancellation policy and procedure (link to Stripe Portal + phone + email)
   - Recurring charge amount and billing frequency
   - Length of auto-renewal term (annual)
   - Minimum purchase obligations (none beyond current term)
2. **Refund & Cancellation Policy** — Full policy from §6:
   - Prorated refund before all services rendered
   - Full refund if cancelled before first visit
   - No refund after all services completed
   - No early termination fees
   - Processing timeframe (5-10 business days)
3. **Service Description** — What each tier includes (Essential, Professional, Premium)
4. **Billing Terms** — Annual recurring charge, payment method on file, Stripe Customer Portal
5. **Property Access** — Customer must provide access for service (gate codes, dog warnings)
6. **Service Area** — Geographic limitations (Minnesota, specific metro areas)
7. **Force Majeure** — Weather, acts of God (critical for seasonal outdoor service)
8. **Limitation of Liability** — Standard liability cap
9. **Modification Clause** — How material changes are communicated (must comply with MN 325G.57 Subd. 3)

**Must update before**: Pre-checkout modal goes live (§17.6), since the modal's T&C checkbox links to this page.

### 17.11 Audit & Update Privacy Policy Page (HIGH — Compliance)

**File**: `Grins_irrigation/frontend/src/features/legal/components/PrivacyPolicyPage.tsx`

**Problem**: The existing privacy policy may not disclose all current and planned data sharing and collection practices. Must be audited and updated.

**Required disclosures**:

| Category | What to Disclose |
|---|---|
| **Data collected** | Name, email, phone, service address, billing address, payment info (via Stripe), IP address, browser info, cookies, service history, property details (zone count, gate code, dogs) |
| **Payment processing** | Stripe processes all payments — Grins never sees or stores card numbers. Link to Stripe's privacy policy. |
| **SMS provider** | Twilio sends automated text messages on our behalf. Phone numbers shared with Twilio for delivery. |
| **Email provider** | Resend delivers emails on our behalf. Email addresses shared with Resend for delivery. |
| **Analytics** | Google Analytics (GA4) via Google Tag Manager — collects page views, click events, anonymized demographics |
| **AI services** | OpenAI processes certain service requests for AI-powered features. No customer PII is sent to OpenAI without anonymization. |
| **Data retention** | Financial records: 7 years. Consent records: 7 years. Communication logs: 5 years. Suppression list: permanent. |
| **Consumer rights** | Right to access, correct, and request deletion of personal data. Contact: info@grinsirrigation.com |
| **Security** | HTTPS encryption, PCI compliance via Stripe (SAQ A), database-level encryption at rest |
| **Cookies** | Session cookies for authentication, analytics cookies via GTM/GA4 |
| **Children's privacy** | Service not directed to children under 13 (COPPA statement) |
| **MN Consumer Data Privacy Act (MCDPA)** | Grins likely qualifies for the small business exemption under SBA size standards for NAICS 561730 (Landscaping Services — $9.5M annual revenue threshold). Regardless, Grins does not sell consumer personal data and obtains consent before collecting sensitive data. |

**Must update before**: Pre-checkout modal goes live, since it should reference the privacy policy.

### 17.12 Accessibility Audit of Purchase Flow (MEDIUM — Legal Risk)

**Problem**: No accessibility testing has been performed on the pricing page, pre-checkout modal, or success page. See §5.5.8 for full WCAG 2.2 Level AA requirements.

**Fix**:
1. Run WAVE accessibility checker on: pricing/service packages page, pre-checkout modal, post-purchase success page, TOS page, privacy policy page
2. Fix all critical issues (missing labels, keyboard traps, contrast failures)
3. Complete keyboard-only navigation test through full purchase flow
4. Test with VoiceOver (macOS) on pricing page and modal
5. Ensure all Subscribe buttons have descriptive labels (include tier name + price)
6. Ensure pre-checkout modal traps focus and closes with Escape

---

## 18. Staff Mobile Experience

### Business Context

The system requirements describe a field workflow where staff/crews:
- See only their own schedule (not other staff's)
- View appointment details (customer info, job type, location, materials, time allotted)
- Follow a step-by-step job completion process
- Collect payment on-site (card, cash, check, or invoice via portal)
- Build estimates and invoices in the field
- Request Google reviews
- Update job notes and mark appointments complete
- Receive real-time notifications about schedule changes

The current platform frontend is an **admin dashboard** designed for desktop use. There is no simplified technician-facing mobile interface.

### Recommended Architecture

**Option A: Progressive Web App (PWA)** — Add a `/tech` route group to the existing platform frontend with a mobile-optimized layout. Same React app, different views based on user role.

**Option B: Separate mobile app** — React Native or Flutter app that calls the same backend API.

**Recommendation: Option A (PWA)**. The existing platform frontend already has role-based auth (`UserRole: admin | manager | tech`). Add mobile-optimized views for the `tech` role that use the same API endpoints and React Query hooks.

### Staff Mobile Views

```
/tech/schedule          — Today's schedule (appointment list, sorted by route_order)
/tech/schedule/:date    — Schedule for specific date
/tech/appointment/:id   — Appointment detail with job completion workflow:
                           1. Navigate to location (Google Maps link)
                           2. Mark "Arrived" (updates arrived_at)
                           3. Review job details & customer notes
                           4. Complete job checklist
                           5. Add notes, photos
                           6. Upsell additional work (create estimate)
                           7. Collect payment or send invoice
                           8. Request Google review (if good candidate)
                           9. Mark "Complete" (updates completed_at)
                           → Auto-notifies next customer of ETA
/tech/estimate/new      — Quick estimate builder (service catalog + line items)
/tech/invoice/new       — Quick invoice builder
```

### GPS Tracking (Future Enhancement)

The system requirements call for admin visibility into staff location. This requires:

1. **Frontend**: Request `navigator.geolocation` permission, send location updates every 60 seconds
2. **Backend**: `POST /api/v1/staff/{id}/location` — stores lat/lng + timestamp
3. **New table**: `staff_locations` (staff_id, latitude, longitude, accuracy, timestamp) — rolling 24-hour window
4. **Admin dashboard**: Map widget showing staff pins with last-known location
5. **ETA calculation**: Use staff's current location + Google Distance Matrix API for real-time arrival estimates

**Privacy consideration**: GPS tracking should only be active during work hours (based on `StaffAvailability`), and staff should be clearly informed.

### Field Payment Collection (Future Enhancement)

For on-site card payments:

1. **Stripe Terminal** — Stripe's card-present payment SDK
   - Backend: Create `PaymentIntent` via Stripe API
   - Frontend: Stripe Terminal JS SDK connects to a card reader (Stripe Reader M2 or similar)
   - Reader communicates with Stripe directly, no card data touches our servers (PCI compliant)

2. **Alternative: Square Reader** — Square's card-present SDK
   - Similar flow, different vendor

3. **For MVP**: Skip card-present hardware. Staff selects payment method in the appointment view:
   - Cash/Check → record as `payment_collected_on_site: true`, `payment_method: cash/check`
   - Digital (Venmo/Zelle) → record manually
   - Invoice → generate and send invoice via email/SMS to customer's phone on the spot

---

## 19. Summary: What Needs to Be Built

### Critical Fixes (Must Be Done First — Blockers)

These items are **broken or missing today** and block core automation:

| # | Item | Repo | Description | Severity |
|---|------|------|-------------|----------|
| 1 | **Wire SMS consent checkbox** | Landing Page | Checkbox renders but has no handler, no state, not in payload. Every automated SMS is a **TCPA violation** ($500-$1,500 per message) without documented consent. | BLOCKER |
| 2 | **Add TCPA-compliant consent language** | Landing Page | The checkbox text must include: company name, "automated" messages, approximate frequency, "message and data rates may apply", opt-out instructions, "consent not a condition of purchase". | BLOCKER |
| 3 | **Add T&C checkbox** | Landing Page | No Terms & Conditions acceptance on lead form. | BLOCKER |
| 4 | **Build pre-checkout confirmation modal** | Landing Page | When customer clicks Subscribe, show modal with: MN auto-renewal disclosures (5 required by 325G.57), T&C checkbox, TCPA-compliant SMS consent checkbox. Must be completed before Stripe Checkout redirect. Captures consent BEFORE payment so welcome SMS is legal. | BLOCKER |
| 5 | **Send property_type in payload** | Landing Page | Collected via radio buttons but not sent to backend. | HIGH |
| 6 | **Send referral_source in payload** | Landing Page | Collected via dropdown but not sent to backend. Data lost at submission. | HIGH |
| 7 | **Unify lead source tracking** | Platform Backend | `source_site` (Lead model, freeform string) and `lead_source` (Customer model, enum) are separate fields with incompatible values. Must be unified into a single `lead_source` enum. | HIGH |
| 8 | **Add backend fields for consent** | Platform Backend | Add `sms_consent`, `terms_accepted`, `property_type`, `referral_source` to `LeadSubmission` schema and `Lead` model. Must deploy before landing page changes. | HIGH |
| 9 | **Create `sms_consent_records` table** | Platform Backend | Immutable audit log for TCPA compliance. Stores consent timestamp, method, exact language shown, IP, user agent. Retain for 7 years. | HIGH |
| 10 | **Replace Stripe test links** | Landing Page + Stripe | All 6 payment links are test mode. Migrate to API-created Checkout Sessions with consent_token metadata (§11). | HIGH (before launch) |
| 11 | **Enable Stripe Customer Portal cancellation** | Stripe Dashboard | Minnesota law requires click-to-cancel for online subscriptions. Stripe Portal must have cancellations enabled with "collect cancellation reason". | HIGH |
| 12 | **Register MN Tax ID + enable Stripe Tax** | Stripe Dashboard + MN DOR | Irrigation services taxable at 6.875% + local. Must register with MN DOR, enable Stripe Tax, add "+ applicable tax" to pricing. | HIGH |
| 13 | **Update Terms of Service page** | Landing Page | Add MN auto-renewal disclosures, refund/cancellation policy, service descriptions, billing terms. Must be complete before pre-checkout modal links to it. | HIGH |
| 14 | **Update Privacy Policy page** | Landing Page | Disclose Stripe, Twilio, Resend, Google Analytics data sharing. Add retention periods, MCDPA exemption note. | HIGH |
| 15 | **Build checkout session endpoint** | Platform Backend | `POST /api/v1/checkout/create-session` — creates Stripe Checkout Session with consent_token + UTM metadata. Replaces static Payment Links. | HIGH |
| 16 | **Create `stripe_webhook_events` table** | Platform Backend | Deduplication table for webhook idempotency. Stores stripe_event_id (unique), event_type, processing_status. | HIGH |
| 17 | **Provide physical business address** | Viktor (manual) | CAN-SPAM requires real postal address in every commercial email footer. Currently a placeholder. | HIGH (before any marketing emails) |

### New Backend Components (Platform Repo)

| Component | Description | Priority | Blueprint Section |
|-----------|-------------|----------|-------------------|
| **ServiceAgreementTier model** | Template table defining package tiers (Essential/Professional/Premium × Residential/Commercial) with included_services JSONB, Stripe product/price IDs | High | §6 |
| **ServiceAgreement model** | Instance table linking customer to tier with Stripe subscription ID, compliance fields (consent_recorded_at, disclosure_version, last_annual_notice_sent), admin workflow fields (renewal_approved_by/at) | High | §6 |
| **AgreementStatusLog model** | Immutable audit trail for all agreement status transitions | High | §6 |
| **sms_consent_records table** | TCPA compliance: consent timestamp, method, language shown, IP, opt-out tracking | High | §5.5 |
| **disclosure_records table** | MN auto-renewal compliance: tracks PRE_SALE, CONFIRMATION, RENEWAL_NOTICE, ANNUAL_NOTICE, CANCELLATION_CONF disclosures | High | §5.5 |
| **Estimate model** | New DB model + migration for quotes/estimates | High | §7 |
| **stripe_webhook_events table** | Webhook idempotency: stores stripe_event_id (unique), event_type, processing_status. Prevents duplicate processing. | High | §11 |
| **Stripe webhook endpoint** | `POST /api/v1/webhooks/stripe` with signature verification, idempotency check, CSRF exemption, raw body parsing | High | §11 |
| **Checkout session endpoint** | `POST /api/v1/checkout/create-session` — creates Stripe Checkout Session with consent_token metadata, automatic_tax, UTM params. Replaces static Payment Links. | High | §11 |
| **Stripe service** | Business logic: webhook events → agreement creation/update, job generation, compliance disclosures, consent token linkage | High | §11 |
| **Renewal approval service** | Viktor's gate: `invoice.upcoming` → PENDING_RENEWAL → admin reviews → approve/reject → job generation | High | §6, §8 |
| **Failed payment service** | Day 0: PAST_DUE + notify customer. Day 7: PAUSED + admin queue. Day 21: cancel if unresolved. | High | §6 |
| **Job generation service** | Generate seasonal jobs from Service Agreement (Essential: 2 jobs, Professional: 3, Premium: 7) | High | §12 |
| **Estimate service** | CRUD + status management + conversion to Job | High | §7 |
| **Background task scheduler** | APScheduler with PostgreSQL job store. Jobs: renewal checks (daily), annual notices (January), failed payment escalation, lead follow-ups. | High | §16.1 |
| **Email service** | Resend with Jinja2 templates. Separate transactional (noreply@) vs commercial (info@) streams. Commercial emails MUST include: physical address, unsubscribe link, ad identification (CAN-SPAM). DNS setup: SPF/DKIM/DMARC. Templates: subscription confirmation (MN law), renewal notice (MN law), annual notice (MN law), cancellation confirmation, plus all commercial templates. | High | §5.5.6, §16.2 |
| **Email unsubscribe endpoint** | `GET /api/v1/email/unsubscribe?token=xxx` — processes opt-out, adds to permanent suppression list, confirms to user. Token valid 30+ days (CAN-SPAM requirement). | High | §5.5.6 |
| **Email suppression list** | Permanent suppression table checked before every commercial email send. Never expires. Cannot sell/transfer opted-out addresses. | High | §5.5.6 |
| **Automation jobs** | Lead follow-ups, estimate reminders, invoice reminders, renewal pipeline, onboarding reminders, annual compliance notices. | High | §8, §15 |
| **Onboarding endpoints** | `POST /api/v1/onboarding/pre-checkout-consent` (Step 1 consent capture) + `GET /api/v1/onboarding/verify-session` (Step 3 session verification) + `POST /api/v1/onboarding/complete` (Step 3 property collection). See §11 for 3-step flow. | High | §11 |
| **Compliance audit endpoint** | `GET /api/v1/compliance/consent-audit?customer_id=xxx` — returns sms_consent_records + disclosure_records | High | §5.5 |
| **SMS opt-out handler** | Extend inbound SMS webhook: detect STOP/QUIT/CANCEL + informal opt-outs, auto-process within 10 business days (target: same-day) | High | §5.5 |
| **Public AI chat endpoint** | `POST /api/v1/ai/chat-public` — rate-limited, no auth, for landing page chatbot. Extends existing AI service architecture. | Medium | §5.2 |
| **Auto-promote service** | Auto-convert Google Sheet submissions to Leads | Medium | §4 |
| **Consent management endpoint** | `POST /api/v1/customers/{id}/consent` — update/audit consent status with mandatory reason | Medium | §5.5 |
| **Follow-Up Queue endpoint** | `GET /api/v1/leads/follow-up-queue` — filtered view for admin review | Medium | §5.4 |
| **AI conversational agent module** | Extend existing `services/ai/` with conversational_agent.py. SMS routing, multi-turn conversations, service matching. | Medium | §5.2 |
| **CustomerTag model** | New `customer_tags` table + repository for flexible customer tagging | Low | §5.6 |
| **CustomerAttachment model** | New `customer_attachments` table for staff-uploaded photos/videos/docs | Low | §5.9 |
| **Attachment service** | S3 presigned URL generation, file validation, cleanup | Low | §5.9 |

### New Frontend Components (Platform Admin Dashboard)

| Component | Description | Priority | Blueprint Section |
|-----------|-------------|----------|-------------------|
| **Service Agreements tab** | Business metrics (MRR, churn, renewal rate, tier distribution) + operational queues (renewal pipeline, failed payments, unscheduled visits, incomplete onboarding). 8 status tabs: All/Active/Pending/Pending Renewal/Past Due/Expiring Soon/Expired/Cancelled. | High | §6, §9 |
| **Agreement detail view** | Linked jobs timeline, visits progress (2/3 completed), payment history from Stripe, compliance log, admin notes, Stripe Portal/Dashboard links | High | §6, §9 |
| **Renewal pipeline queue** | Actionable list: customer/tier/price/visits completed + Approve/Reject/Needs Discussion buttons | High | §6, §8, §9 |
| **Failed payment queue** | Customer/tier/failed date/outreach log + Log Outreach/Resume/Cancel buttons | High | §6, §9 |
| **Estimates tab** | List + detail + kanban view for quotes | High | §7 |
| **Estimate builder** | Form for creating estimates with line items and options | High | §7 |
| **Ready to Schedule queue** | Dashboard widget or Jobs tab filtered view | High | §14 |
| **Dashboard widgets** | MRR with trend, active agreements with trend, pending estimates, ready-to-schedule count, renewal pipeline count, failed payments count + dollar value, follow-up queue count, leads by source chart | Medium | §9 |
| **Follow-Up Queue view** | Filtered leads view (admin-only) with urgency indicators and one-click actions | Medium | §5.4 |
| **Consent status badges** | SMS/email opt-in indicators on customer and lead detail views. Warning banner if opted out. | Medium | §5.5 |
| **Consent history view** | Expandable section on CustomerDetail showing all sms_consent_records entries | Medium | §5.5 |
| **Bulk scheduling UI** | Select multiple jobs → schedule together | Medium | §14 |
| **Customer Tags UI** | Tag chips + autocomplete input on customer detail, tag filter on customer list | Low | §5.6 |
| **Customer Attachments UI** | File upload (drag-and-drop) + gallery view on customer detail | Low | §5.9 |
| **Staff mobile views (PWA)** | `/tech/*` routes with mobile-optimized appointment detail, job completion, estimate builder | Low | §18 |

### New Frontend Components (Landing Page Repo)

| Component | Description | Priority | Blueprint Section |
|-----------|-------------|----------|-------------------|
| **SMS consent checkbox (wired)** | Fix existing checkbox — add state, handler, include in payload. Use TCPA-compliant disclosure language (§5.5.1). Must NOT be pre-checked. | CRITICAL | §5.5, §17.1 |
| **T&C checkbox** | New required checkbox with link to /terms-of-service | CRITICAL | §17.2 |
| **Pre-checkout confirmation modal** | `SubscriptionConfirmModal.tsx` — intercepts Subscribe button click. Shows MN auto-renewal disclosures (5 required), T&C checkbox, TCPA SMS consent checkbox. Calls pre-checkout-consent endpoint. Redirects to Stripe Checkout. | CRITICAL | §5.5.2, §11, §17.6 |
| **UTM parameter tracking** | Parse URL params on load, store in context, inject into lead submission | HIGH | §17.5 |
| **Post-purchase onboarding form** | Property info collection after Stripe checkout (Step 3), verifies session with backend. No consent checkboxes — consent captured in pre-checkout modal (Step 1). Collects: service address, zone count, gate code, dogs, access notes, preferred times. | HIGH | §11, §17.7 |
| **AI chatbot upgrade** | Replace rule-based conversation tree with calls to platform AI service. Keep rule-based as fallback. | Medium | §5.2 |

### Modifications to Existing Components

| Component | Change | Repo | Priority |
|-----------|--------|------|----------|
| **Lead model** | Add `lead_source` (enum), `source_detail`, `intake_tag`, `sms_consent`, `terms_accepted`, `property_type`, `referral_source`, `preferred_times` | Platform | HIGH |
| **LeadSubmission schema** | Add all new fields with backward-compatible defaults | Platform | HIGH |
| **Customer model** | Add `stripe_customer_id`, `terms_accepted`, `terms_accepted_at`, `terms_version`, `sms_opt_in_at`, `sms_opt_in_source`, `email_opt_in_at`, `sms_consent_language_version`, `preferred_service_times` (JSONB), `internal_notes` | Platform | HIGH |
| **Job model** | Add `service_agreement_id`, `estimate_id`, `target_start_date`, `target_end_date` | Platform | HIGH |
| **SMSService.send_message()** | Add `sms_opt_in` gate — block automated SMS if customer hasn't opted in. Add time window check (no sends before 8 AM or after 9 PM Central). Log warning for audit. | Platform | HIGH |
| **SMS webhook** (`api/v1/sms.py`) | Add STOP/QUIT/CANCEL keyword detection → auto-opt-out. Handle informal opt-outs ("stop texting me"). Create sms_consent_records entry. Send ONE confirmation text. | Platform | HIGH |
| **LeadService.submit_lead()** | Trigger SMS + email confirmation after lead creation (gated on sms_consent). Create sms_consent_records entry with full audit data. | Platform | HIGH |
| **LeadService.convert_lead()** | Carry consent fields from Lead to Customer record. Create corresponding sms_consent_records entry. | Platform | HIGH |
| **enums.py** | Add expanded `LeadSource` (11 values), `IntakeTag`, `LEAD_CONFIRMATION` to MessageType. Add `AgreementStatus`, `PackageTier`, `PackageType`, `PaymentStatus`, `DisclosureType`, `ConsentType` enums. | Platform | HIGH |
| **Landing page lead form** | Wire SMS consent with TCPA-compliant language, add T&C checkbox, send property_type + referral_source + consent_ip + consent_user_agent, add UTM tracking | Landing Page | HIGH |
| **Landing page ServicePackagesPage** | Replace test Stripe links, add MN auto-renewal disclosures near Subscribe buttons, add post-purchase onboarding flow | Landing Page | HIGH |
| **LeadRepository.list_with_filters()** | Add `lead_source`, `intake_tag` filter parameters | Platform | Medium |
| **Google Sheets poller** | Add auto-promote logic (create Lead automatically on new submission) | Platform | Medium |
| **Invoice model** | Add optional `po_number` field for commercial clients | Platform | Low |
| **LeadsList.tsx** | Add `LeadSourceBadge`, `IntakeTagBadge`, quick-filter tabs | Platform | Medium |
| **CustomerDetail.tsx** | Add consent badges + history, tags, attachments, preferred service times, internal notes, warning banner if opted out | Platform | Medium |
| **Dashboard page** | Add MRR widget, renewal pipeline count, failed payments count + dollar value, follow-up queue widget, leads by source chart, onboarding incomplete alerts | Platform | Medium |
| **Landing page index.html** | Replace GTM/GA4 placeholder IDs with real values | Landing Page | Medium |

### Infrastructure

| Item | Description | Priority | Blueprint Section |
|------|-------------|----------|-------------------|
| **APScheduler** | Add `apscheduler` to backend dependencies. Configure PostgreSQL job store. Start on FastAPI startup. Jobs: `check_upcoming_renewals` (daily 9 AM), `send_annual_notices` (January), `escalate_failed_payments` (daily), lead/estimate/invoice follow-ups. | HIGH | §16.1 |
| **Email service (Resend/SendGrid)** | Add SDK, configure API key, create HTML email templates. **Compliance-critical templates**: subscription_confirmation (MN law), renewal_notice (MN law), annual_notice (MN law), cancellation_confirmation. Plus: lead confirmation, estimate, invoice, payment reminder, review request. | HIGH | §16.2 |
| **Stripe Python SDK** | Add `stripe>=7.0.0` to backend dependencies | HIGH | §16.3 |
| **Stripe Dashboard config** | See Stripe Dashboard Configuration Checklist (§11). Includes: business verification, Stripe Tax + MN Tax ID, live products with metadata, webhook endpoint, Customer Portal (cancellations enabled, plan switching disabled), Smart Retries, branding, statement descriptor. | HIGH | §5.5.7, §6, §11 |
| **Railway env vars** | Add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_CUSTOMER_PORTAL_URL`, `RESEND_API_KEY` to Railway deployment | HIGH | §11, §16.2 |
| **Google Analytics** | Create GTM container + GA4 property, configure conversion goals | Medium | §16.6 |
| **Redis** (Phase 2) | For AI conversation state if needed. PostgreSQL alternative for Phase 1. | Medium | §16.4 |
| **S3-compatible storage** (Phase 3) | For customer attachments. Recommendation: Cloudflare R2. | Low | §16.5 |

### Implementation Phases (Updated)

**Phase 0 — Critical Fixes & Compliance Foundation (Before Any Other Work)**
1. Wire SMS consent checkbox on landing page with TCPA-compliant disclosure language (§5.5.1)
2. Add T&C checkbox on landing page
3. Build pre-checkout confirmation modal with MN disclosures + consent checkboxes (§5.5.2, §11, §17.6)
4. Send property_type + referral_source + consent metadata (IP, user agent) in lead payload
5. Add corresponding fields to backend LeadSubmission schema + Lead model
6. Create `sms_consent_records` table (immutable TCPA audit log, 7-year retention)
7. Create `disclosure_records` table (MN auto-renewal compliance log)
8. Create `stripe_webhook_events` table (webhook idempotency — §11)
9. Add SMS consent gating + time window check in SMSService
10. Add STOP keyword + informal opt-out detection in SMS webhook
11. Unify lead source enums (backend)
12. Configure real GTM/GA4 IDs on landing page
13. Enable Stripe Customer Portal cancellations (MN click-to-cancel requirement)
14. Register MN Tax ID with Department of Revenue + enable Stripe Tax (§5.5.7)
15. Update Terms of Service page with MN disclosures + refund policy (§17.10)
16. Update Privacy Policy page with data sharing disclosures (§17.11)
17. Run accessibility audit on purchase flow pages (§5.5.8, §17.12)
18. Viktor provides physical business address for CAN-SPAM email footer

**Phase 1 — Core Automation Pipeline + Subscription Tracking**
19. ServiceAgreementTier + ServiceAgreement + AgreementStatusLog models + migrations
20. Stripe Python SDK + webhook endpoint with signature verification + idempotency
21. Checkout session creation endpoint (replaces static Payment Links — §11)
22. Webhook handlers: checkout.session.completed, invoice.upcoming, invoice.paid, invoice.payment_failed, customer.subscription.deleted
23. Consent token → Stripe session linkage in webhook handler (§11)
24. Post-purchase onboarding flow (landing page form + backend endpoints)
25. Seasonal job auto-generation from Service Agreements
26. Renewal approval workflow (Viktor's gate: invoice.upcoming → admin review → job generation)
27. Failed payment workflow (PAST_DUE → PAUSED → manual outreach → cancel)
28. Service Agreements tab in admin dashboard (business metrics + operational queues)
29. Email service integration (Resend) — separate transactional/commercial streams, CAN-SPAM compliant templates (physical address, unsubscribe link, ad identification), MN-required compliance templates, DNS setup (SPF/DKIM/DMARC)
30. Email unsubscribe endpoint + permanent suppression list (CAN-SPAM §5.5.6)
31. Background task scheduler (APScheduler) — including renewal checks + annual notice jobs
32. Lead submission confirmation (SMS + email, gated on consent)
33. Subscription confirmation email (MN law: immediately after purchase)
34. Estimate entity + estimate builder + estimate-to-job conversion
35. Complete pre-launch testing checklist (§19)

**Phase 2 — Automated Communication & Intelligence**
36. Automated communication sequences (lead follow-ups, estimate reminders, job notifications, invoice reminders, renewal reminders)
37. Pre-renewal notice automation (30 days before, MN law compliant)
38. Annual notice automation (January each year, MN law compliant)
39. Follow-Up Queue view (admin dashboard)
40. AI conversational agent — SMS routing through existing AI service
41. AI chatbot upgrade on landing page (connect to platform AI backend)
42. UTM parameter tracking on landing page
43. Customer consent management endpoint + compliance audit endpoint

**Phase 3 — Enhanced Data & Field Operations**
44. Customer tags system
45. Customer attachments (photos/videos) + S3 storage
46. Customer preferred service times + scheduling integration
47. Staff mobile views (PWA)
48. Leads by source analytics dashboard
49. Bulk scheduling UI

**Phase 4 — Advanced (Future)**
50. AI voice agent (phone calls via Twilio Voice + OpenAI Realtime API)
51. GPS tracking for field staff
52. Card-present field payment (Stripe Terminal)
53. Advanced marketing dashboard with campaign ROI tracking

### Cross-Repo Deployment Order (Compliance-Critical)

Phase 0 and Phase 1 require **coordinated deployment** across both repos. The order matters because compliance items must be in place before any automated messaging begins.

```
STEP 1: Platform Backend (deploy to Railway first)
  → sms_consent_records + disclosure_records + stripe_webhook_events tables (migrations)
  → ServiceAgreement* models (migrations)
  → LeadSubmission schema extensions (backward-compatible)
  → SMSService consent gate + time window check
  → SMS webhook opt-out detection
  → Stripe webhook endpoint + idempotency (§11)
  → Checkout session creation endpoint (§11)
  → Onboarding endpoints (§11)

STEP 2: Stripe Dashboard (configure manually — see Stripe Dashboard Configuration Checklist in §11)
  → Complete business verification
  → Enable Stripe Tax + register MN Tax ID
  → Enable Customer Portal cancellations (disable plan switching)
  → Create live products with metadata (package_tier, package_type)
  → Create recurring Prices for each product
  → Register webhook endpoint with all required events
  → Configure Smart Retries + dunning
  → Set branding, support email, statement descriptor

STEP 3: Landing Page (deploy to Vercel)
  → Wire SMS consent checkbox with TCPA language
  → Add T&C checkbox
  → Update Terms of Service page with MN disclosures + refund policy (§17.10)
  → Update Privacy Policy page with data sharing disclosures (§17.11)
  → Build pre-checkout confirmation modal (calls create-session endpoint)
  → Build post-purchase onboarding form
  → Update pricing cards to show "+ applicable tax"
  → Add descriptive Subscribe button labels for accessibility (§5.5.8)
  → Run accessibility audit (§17.12)

STEP 4: Platform Backend (second deploy)
  → Email service (Resend) with DNS setup (SPF/DKIM/DMARC) + compliance templates
  → APScheduler with renewal + annual notice jobs
  → Subscription confirmation email on checkout.session.completed
  → Pre-renewal notice (30 days before)
  → Annual notice job (January each year)
```

### Pre-Launch Testing Checklist (Purchase Flow)

Before accepting real customer payments, complete this end-to-end testing checklist:

```
STRIPE TEST MODE (use test keys — do NOT test with live keys):
──────────────────────────────────────────────────────────────
  [ ] Purchase each of the 6 tiers (3 residential + 3 commercial) in test mode
  [ ] Verify checkout.session.completed webhook fires and is received by backend
  [ ] Verify Customer record created (or matched) on webhook receipt
  [ ] Verify ServiceAgreement record created with correct tier, price, status
  [ ] Verify seasonal jobs generated with correct target date ranges
  [ ] Verify consent_token linkage: sms_consent_records and disclosure_records
      are updated with customer_id after webhook processing
  [ ] Verify tax calculated correctly on test transactions (if Stripe Tax enabled in test)

WEBHOOK RELIABILITY:
────────────────────
  [ ] Idempotency: replay same webhook event via Stripe CLI, verify no duplicate records
  [ ] Signature verification: send request without valid signature, verify 400 response
  [ ] Out-of-order events: send invoice.paid before checkout.session.completed, verify graceful handling
  [ ] Failed processing: simulate handler error, verify event logged as "failed" and 200 returned

CONSENT & COMPLIANCE:
─────────────────────
  [ ] Pre-checkout modal displays all 5 MN auto-renewal disclosures
  [ ] T&C checkbox is NOT pre-checked, required to proceed
  [ ] SMS consent checkbox is NOT pre-checked, required to proceed
  [ ] Consent data stored in sms_consent_records (IP, user agent, timestamp, language version)
  [ ] Disclosure data stored in disclosure_records (PRE_SALE type)
  [ ] Terms of Service page includes all required sections (§17.10)
  [ ] Privacy Policy page discloses all data sharing (§17.11)

POST-PURCHASE FLOW:
───────────────────
  [ ] Success page loads with session_id parameter
  [ ] Verify-session endpoint returns correct customer/package data
  [ ] Onboarding form pre-fills billing address from Stripe
  [ ] "Same as billing" toggle works correctly
  [ ] Form submission creates/updates Property record
  [ ] Final confirmation shows Stripe Portal link
  [ ] If customer abandons Step 3: verify T+24h SMS reminder fires (in test mode)

FAILED PAYMENT:
───────────────
  [ ] Simulate card decline (Stripe test card 4000 0000 0000 0341)
  [ ] Verify invoice.payment_failed webhook received
  [ ] Verify agreement status → PAST_DUE
  [ ] Verify customer notification sent (SMS + email)
  [ ] Verify admin dashboard shows agreement in "Failed Payment" queue
  [ ] Simulate Day 7 escalation: agreement → PAUSED
  [ ] Simulate payment recovery: customer updates card → ACTIVE

CANCELLATION:
─────────────
  [ ] Cancel via Stripe Customer Portal
  [ ] Verify customer.subscription.deleted webhook received
  [ ] Verify agreement status → CANCELLED
  [ ] Verify cancellation_reason captured
  [ ] Verify cancellation confirmation sent to customer (MN law requirement)
  [ ] Verify future unscheduled jobs cancelled
  [ ] Verify completed jobs NOT affected

RENEWAL:
────────
  [ ] Simulate invoice.upcoming webhook (T-30 days)
  [ ] Verify agreement status → PENDING_RENEWAL
  [ ] Verify renewal notice email sent (MN law: 5-30 days before)
  [ ] Verify admin dashboard shows agreement in "Renewal Pipeline" queue
  [ ] Verify Approve action: jobs generated on invoice.paid
  [ ] Verify Reject action: subscription cancelled at period end

EMAIL:
──────
  [ ] Subscription confirmation email sent (check MN-required content)
  [ ] Unsubscribe link works in commercial emails
  [ ] Unsubscribe adds to suppression list
  [ ] Suppressed email skipped on next commercial send
  [ ] Transactional emails NOT affected by unsubscribe
  [ ] Physical address present in commercial email footer

MOBILE & ACCESSIBILITY:
───────────────────────
  [ ] Complete purchase flow on mobile (iPhone Safari + Android Chrome)
  [ ] Touch targets ≥ 44x44px on pricing page and modal
  [ ] Keyboard-only navigation through entire purchase flow (desktop)
  [ ] Screen reader test on pricing page (VoiceOver or NVDA)
  [ ] All color contrast ratios pass WCAG AA (4.5:1 normal text)
  [ ] Pre-checkout modal closes with Escape key, traps focus while open

STRIPE LIVE MODE (final check before launch):
──────────────────────────────────────────────
  [ ] Switch to live Stripe keys in Railway env vars
  [ ] Verify webhook endpoint receives events with live keys
  [ ] Make one real $1 test purchase (create a $1 test product)
  [ ] Verify full flow works with real payment
  [ ] Delete test purchase and refund
  [ ] Replace $1 test product with real products
```

---

> **Next step**: Begin with Phase 0 (critical fixes + compliance foundation) — these are the legal blockers that must be resolved before any automated messaging or subscription billing goes live. Then proceed to Phase 1 starting with the ServiceAgreement models, Stripe webhook integration, and email service with MN-required templates.
