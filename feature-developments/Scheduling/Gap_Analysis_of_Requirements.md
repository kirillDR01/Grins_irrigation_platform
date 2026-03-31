# Gap Analysis: AI Scheduling System Requirements vs. Current Codebase

**Date:** March 31, 2026 | **Repos Analyzed:** `Grins_irrigation_platform` (backend + admin dashboard) and `Grins_irrigation` (customer-facing frontend)

**Purpose:** Identify what the AI Scheduling System Requirements document covers, what it doesn't cover, and what currently exists in the codebase that can be leveraged.

---

## Table of Contents

1. [Current Codebase Foundation](#1-current-codebase-foundation)
2. [Gaps Addressed in Requirements](#2-gaps-addressed-in-requirementsmd)
3. [Gaps NOT Addressed in Requirements](#3-gaps-not-addressed-in-requirementsmd)
4. [Constraint Solver Coverage](#4-constraint-solver-coverage-8-of-30-implemented)
5. [Component Integration Readiness](#5-component-integration-readiness)
6. [Summary Scorecard](#6-summary-scorecard)
7. [Recommended Build Order](#7-recommended-build-order)

---

## 1. Current Codebase Foundation

### 1.1 What Already Exists (Backend — `Grins_irrigation_platform`)

#### Database Models (41 total)

| Model | Key Scheduling-Relevant Fields | Coverage |
|---|---|---|
| **Customer** | id, name, phone, email, status, priority/red_flag/slow_payer flags, preferred_service_times (JSON), communication preferences, stripe_customer_id | ~70% of what requirements need |
| **Lead** | name, phone, email, address, city, state, situation, status, assigned_to, customer_id | Feeds into job creation pipeline |
| **Job** | job_type, category, status (to_be_scheduled/in_progress/completed/cancelled), estimated_duration_minutes, priority_level (0-2), weather_sensitive, target_start_date, target_end_date, staffing_required, equipment_required (JSON), materials_required (JSON), timestamps (requested_at, approved_at, scheduled_at, started_at, completed_at) | ~75% of what requirements need |
| **Appointment** | job_id, staff_id, scheduled_date, time_window_start/end, status (pending/scheduled/confirmed/en_route/in_progress/completed/cancelled/no_show), arrived_at, completed_at, en_route_at, route_order, estimated_arrival, materials_needed (JSONB), estimated_duration_minutes | ~65% of what requirements need |
| **Property** | address, city, state, zip_code, latitude, longitude, zone_count, system_type (standard/lake_pump), property_type (residential/commercial), access_instructions, gate_code, has_dogs, special_notes | ~80% of what requirements need |
| **Staff** | name, phone, email, role (tech/sales/admin), skill_level (junior/senior/lead), certifications (JSON), assigned_equipment (JSON), default_start_address, default_start_lat/lng, is_available, availability_notes, hourly_rate | ~60% of what requirements need |
| **StaffAvailability** | date, start_time, end_time, is_available, lunch_start, lunch_duration_minutes | Basic daily availability |
| **ServiceAgreement** | customer_id, tier_id, property_id, stripe_subscription_id, status, start_date, end_date, annual_price, zone_count, has_lake_pump, has_rpz_backflow, preferred_schedule, preferred_schedule_details | Subscription management |
| **ServiceOffering** | name, category, base_price, price_per_zone, pricing_model, estimated_duration_minutes, duration_per_zone_minutes, staffing_required, equipment_required, buffer_minutes | Job type templates |
| **ScheduleWaitlist** | job_id, preferred_date, preferred_time_start/end, priority, notes | Basic waitlist |
| **ScheduleReassignment** | original_staff_id, new_staff_id, reassignment_date, reason, jobs_reassigned | Reassignment tracking |
| **StaffBreak** | staff_id, appointment_id, start_time, end_time, break_type | Break tracking |

#### Services (Business Logic)

| Service | What It Does | Relevance |
|---|---|---|
| **ScheduleGenerationService** | `generate_schedule(date, timeout)` — builds schedule for a given day | Core scheduler entry point |
| **ScheduleSolverService** | Constraint-based greedy algorithm with local search, 30-second timeout | The optimization engine — currently uses ~8 constraints |
| **ConstraintChecker** | Hard constraints (availability, equipment, overlap, lunch) + soft constraints (travel time weight 80, city batching weight 70, priority weight 90) | Extensible constraint framework |
| **TravelTimeService** | Google Maps Distance Matrix API with Haversine fallback (40 km/h avg, 1.4x road factor) | Route optimization foundation |
| **StaffLocationService** | Redis-based GPS tracking with 5-minute TTL | Real-time location tracking |
| **ConflictResolutionService** | Cancel with waitlist, reschedule, fill gaps | Conflict handling foundation |
| **JobGenerator** | Generates seasonal jobs from service agreements by tier | Automated job creation |
| **ScheduleExplanationService** | AI-powered explanation of schedule decisions | Explainability |
| **ConstraintParserService** | Parses natural language constraints | NL understanding |
| **UnassignedJobAnalyzer** | Analyzes why jobs weren't scheduled | Debugging |

#### API Endpoints

| Endpoint Group | Endpoints Available |
|---|---|
| **Schedule Generation** | POST /generate, GET /capacity/{date}, POST /apply, POST /emergency-insert, POST /reoptimize, GET /jobs-ready-to-schedule, POST /explain, POST /analyze-unassigned, POST /parse-constraints |
| **Appointments** | Full CRUD, daily/weekly views, staff daily views, reschedule, status transitions (mark-in-progress, complete), payment collection |
| **Jobs** | Full CRUD, status transitions, filtering |
| **Staff** | Management, availability, equipment/certifications |
| **Conflict Resolution** | Conflict resolution, waitlist management |

#### Frontend Dashboard (Platform Repo)

| Component Area | What Exists |
|---|---|
| **Schedule Page** | SchedulePage, CalendarView, AppointmentList, AppointmentForm, AppointmentDetail |
| **Schedule Generation** | JobsReadyToSchedulePreview, DaySelector, ScheduleResults, useScheduleGeneration hook |
| **Map Features** | MapProvider, MapFilters, MapLegend, RoutePolyline, MobileJobSheet |
| **Operations** | ClearDayDialog, RestoreScheduleDialog, BreakButton, PaymentCollector, InvoiceCreator |
| **AI Assistance** | SchedulingHelpAssistant, NaturalLanguageConstraintsInput |

#### External Integrations

| Integration | Status |
|---|---|
| **Stripe** | Full integration — subscriptions, checkout, webhooks, customer portal |
| **Google Maps** | Distance Matrix API for travel time calculation |
| **Email** | Email service configured |
| **SMS** | SMS service configured |
| **Google Sheets** | Lead import polling |
| **Redis** | Staff GPS location caching |

### 1.2 What Already Exists (Frontend — `Grins_irrigation`)

| Area | What Exists |
|---|---|
| **Lead Capture** | Full lead form with customer type, name, phone, email, address, service interest, property type, referral source |
| **Chatbot** | Customer-facing chatbot with rule-based conversation tree (6 flows), FAQ search, lead form prefilling, AI fallback to `/api/v1/ai/chat-public` |
| **Onboarding** | Post-purchase form capturing service_address, gate_code, has_dogs, access_instructions, preferred_times (MORNING/AFTERNOON/NO_PREFERENCE), preferred_schedule (ASAP/1-2 weeks/3-4 weeks/Other) |
| **Service Packages** | Tiered pricing display, Stripe checkout integration |
| **Service Area** | City data with phase info and available services |

**What does NOT exist in the customer-facing frontend:**
- No calendar/date picker for appointment booking
- No appointment self-service (view, reschedule, cancel)
- No ETA tracking portal
- No satisfaction rating submission
- No admin or resource interfaces (all customer-facing)

---

## 2. Gaps Addressed in Requirements.md

These are capabilities missing from the codebase that the requirements document explicitly specifies.

### 2.1 ML/AI Models — 0% Built, Fully Specified in Requirements

| Model | Requirements Coverage | Criteria Referenced | Inputs Defined | Output Defined |
|---|---|---|---|---|
| **Cancellation/No-Show Prediction** | Criterion #19 | Yes — customer history, weather forecast, day-of-week patterns | Yes | Yes — probability per scheduled job; enables over-scheduling low-risk slots |
| **Job Complexity/Duration Prediction** | Criteria #12, #27 | Yes — customer system age, zone count, last service date, historical repair frequency, resource speed | Yes | Yes — predicted actual duration; allocate longer time slots |
| **Weekly Demand Forecasting** | Criterion #17 | Yes — historical patterns, seasonal trends, weather, customer base size | Yes | Yes — predicted job volume for 2-8 weeks; pre-position capacity |
| **Lead Conversion Probability** | Criterion #28 | Yes — sales pipeline data | Partial | Yes — reserve tentative capacity for hot leads |
| **Customer Preference Learning** | Criterion #15 | Yes — past ratings, resource requests | Partial | Yes — preferred technician pairing |

**What's NOT specified for ML models:**
- Training data volume requirements (how much history is needed)
- Model accuracy thresholds (what's "good enough" to deploy)
- Cold-start strategy (how to bootstrap with no historical data)
- Retraining cadence (how often models are updated)
- Model versioning and rollback

### 2.2 Admin Conversational AI Chat — 0% Built, Thoroughly Specified

The requirements define 10 specific admin chat interactions in Section 3, each with:
- The exact user prompt
- The AI's clarifying questions
- Which of the 30 criteria are used behind the scenes
- The output rendered to the Schedule Overview

| # | Prompt | Criteria Used | Output |
|---|---|---|---|
| 1 | "Build next week's schedule for spring openings" | 1-5, 6-8, 11-13, 16-18, 26 | Auto-generated weekly schedule with capacity heat map and flagged conflicts |
| 2 | "Reshuffle Thursday — two resources called out sick" | 8-9, 1-2, 11 | Revised Thursday with reassigned jobs, updated ETAs, overflow list |
| 3 | "Add an emergency break-fix at 456 Oak Street, needs lake pump specialist" | 6, 7, 1, 13 | Emergency inserted into nearest qualified resource's route |
| 4 | "What does next month's capacity look like for new build installs?" | 16-18, 20 | Capacity forecast with available project slots by week |
| 5 | "Move Mrs. Rodriguez to Tuesday morning, same tech as last time" | 15, 11, 1-2 | Job moved, routes recalculated, confirmation drafted |
| 6 | "Show me which resources are underutilized this week" | 9, 16, 20, 17 | Utilization report with pull-forward/backlog suggestions |
| 7 | "Schedule all 350 fall closing customers across next 5 weeks" | 3, 11, 18, 26, 6-7 | Complete 5-week campaign with batch notifications ready |
| 8 | "What's the most profitable way to fill Friday — 3 open slots" | 22, 13, 14, 25, 20 | Ranked jobs by profitability with one-click assignment |
| 9 | "Rain forecast all day Wednesday. Reschedule outdoor jobs" | 26, 1-2 | Outdoor jobs pushed, indoor backfill assigned, customers notified |
| 10 | "Set up recurring bi-weekly maintenance for top 20 commercial accounts" | 23, 14, 15, 3, 1-2 | Recurring route template auto-populating future schedules |

**What's NOT specified:**
- Error handling for ambiguous prompts
- Conversation memory (multi-turn context window)
- Confirmation workflow before executing destructive changes
- Rate limiting on AI interactions
- Fallback when LLM is unavailable

### 2.3 Resource Conversational AI Chat — 0% Built, Thoroughly Specified

The requirements define 10 specific resource chat interactions in Section 5, each with:
- The resource's prompt
- The AI's response or escalation path
- Output visible to the resource and/or admin

| # | Prompt | AI Response | Escalation |
|---|---|---|---|
| 1 | "I'm running about 30 minutes behind" | Recalculates ETAs; if window violated, drafts delay notification | Alert to admin if customer window at risk |
| 2 | "What do I need for my next job?" | Pre-job checklist: type, customer, equipment, issues, gate code, instructions, duration | None — self-contained |
| 3 | "Customer needs additional work — 3 broken heads + leaking valve" | Creates follow-up job request with field notes and parts estimate | Change request to admin's Alerts panel |
| 4 | "Customer isn't home and gate is locked" | Checks profile for alternate access/secondary contact | Alert to admin: reschedule or contact customer |
| 5 | "I finished early. Anything nearby?" | Lists 2-3 nearby jobs matching skills/equipment within 15-min radius | Requests admin approval before adding |
| 6 | "Don't have the right nozzle kit. Can I swap with afternoon job?" | Checks if resequencing to shop stop is feasible | Route change request to admin |
| 7 | "System is way more complex than expected — 16-zone lake pump. Need help" | Identifies nearby qualified resources with capacity | Crew assistance request to admin |
| 8 | "Log that I replaced 4 spray heads and 2 rotors" | Updates job record, decrements truck inventory | Low-stock suggestion to admin if threshold breached |
| 9 | "What's my schedule look like tomorrow?" | Tomorrow's schedule card with 6 jobs in route order, ETAs, pre-job requirements | None — self-contained |
| 10 | "Customer wants to upgrade to smart controller. Quote and schedule?" | Pulls upgrade pricing, creates quote draft, finds install slots | Quote + scheduling request to admin |

**What's NOT specified:**
- Authentication/authorization for resource chat (how does AI verify the resource's identity)
- Offline behavior when resource is in poor coverage area
- Voice input support (hands-free while working)
- Photo/media attachment support in chat

### 2.4 Alert/Suggestion Engine — 0% Built, Thoroughly Specified

#### Admin Alerts (5 defined)

| # | Alert | Trigger Criteria | Resolution Actions |
|---|---|---|---|
| 1 | Double-Booking Conflict | Criteria 8, 12 — two jobs overlap on same resource | Reassign, shift by 30 min, or extend gap |
| 2 | Skill Mismatch Detected | Criterion 6 — resource lacks required certification | Swap resource with certified alternative (one-click) |
| 3 | SLA Deadline at Risk | Criteria 23, 20 — commercial deadline approaching | Force-schedule today/tomorrow or accept SLA miss |
| 4 | Resource Running 40+ Min Behind | Criteria 12, 27, 4 — job significantly over estimate | Absorb delay, move last job, or reschedule (auto-drafted customer notifications) |
| 5 | Severe Weather Incoming | Criterion 26 — freeze/rain warning for scheduled outdoor jobs | Batch-reschedule outdoor jobs, backfill with indoor work |

#### Admin Suggestions (5 defined)

| # | Suggestion | Trigger Criteria | Resolution Actions |
|---|---|---|---|
| 6 | Route Swap Saves X Minutes | Criteria 1-2, 9 — swap between two resources reduces drive time | Accept to execute (map visualization with before/after) |
| 7 | Underutilized Resource — Fill Gap | Criteria 9, 16, 20 — resource has 2.5+ hours unused with matching backlog | Accept one or all candidate jobs |
| 8 | Customer Prefers Different Resource | Criteria 15, 10 — customer dissatisfaction from last visit | Accept to reassign for all future jobs |
| 9 | Overtime Avoidable by Shifting 1 Job | Criteria 24, 13 — moving one low-priority job eliminates overtime | Accept to move (shows cost saved) |
| 10 | High-Revenue Job Available for Open Slot | Criteria 22, 14 — new request matches open slot with 2x avg revenue | Accept to auto-schedule |

#### Resource Alerts (5 defined)

| # | Alert | Trigger | Resource Interaction |
|---|---|---|---|
| 1 | Schedule Change — Job Added | Admin/AI inserted new job | See new job with updated sequence and ETA |
| 2 | Schedule Change — Job Removed | Cancellation removed a job | See updated route; AI suggests nearby backlog |
| 3 | Route Resequenced | Traffic/swap/weather caused reorder | See new job list with reason and updated navigation |
| 4 | Pre-Job Requirement — Special Equipment | 30 min before job needing atypical equipment | Tap "Confirmed" or "Need Shop Stop" |
| 5 | Pre-Job Requirement — Customer Access | 15 min before arrival | Gate code, entry instructions, pet warnings, text-before-arrival |

#### Resource Suggestions (5 defined)

| # | Suggestion | Trigger | Resource Interaction |
|---|---|---|---|
| 6 | Pre-Job Prep — Review Customer History | Recurring issue detected (e.g., Zone 3 valve replaced twice in 18 months) | Carry recommended spare parts |
| 7 | Upsell Opportunity | Old controller (12+ years) with frequent service calls | Suggest smart controller upgrade to customer |
| 8 | Optimized Departure Time | Traffic spike in 8 minutes; delaying 10 min yields same ETA | "Depart at 1:25 instead of 1:15" |
| 9 | Parts Running Low | Predicted consumption exceeds truck stock for remaining jobs | Pick up parts at supply house near Job #4 |
| 10 | Admin Decision Required — Pending Approval | Resource's change request unanswered for 25+ min | Nudge notification |

**What's NOT specified:**
- Alert priority ranking when multiple alerts fire simultaneously
- Alert dismissal tracking (was it addressed or ignored?)
- Alert escalation (what if admin doesn't respond to a critical alert?)
- Suggestion acceptance rate tracking (for improving AI recommendations)
- Notification channels per alert type (in-app only? push? SMS?)

### 2.5 Weather Integration — 0% Built, Specified in Requirements

- **Criterion #26:** Check 7-day weather forecast; proactively reschedule outdoor jobs before rain/freeze events; backfill gap with indoor-safe jobs
- **Admin Chat #9:** "Rain is forecast all day Wednesday. Reschedule outdoor jobs and backfill with indoor work"
- **Admin Alert #5:** Severe weather incoming — freeze warning for Thursday, 12 outdoor jobs scheduled
- **Data Section:** 7-day weather forecast (temperature, precipitation, freeze warnings)

**What's NOT specified:**
- Which weather API to use
- Update frequency (hourly? daily?)
- Definition of "severe" vs. "moderate" weather thresholds
- How far in advance to trigger proactive rescheduling
- Indoor vs. outdoor job classification rules beyond the `weather_sensitive` flag

### 2.6 Revenue Optimization — 0% Built, Specified in Requirements

- **Criterion #22:** Revenue per resource-hour — calculate effective revenue/hour including drive time; optimize for total daily revenue, not job count
- **Criterion #24:** Overtime cost threshold — avoid overtime unless job revenue justifies the added labor cost
- **Criterion #25:** Seasonal pricing signals — premium for Saturday, discount for Wednesday PM; steer flexible jobs to off-peak; reserve peak for full-price
- **Admin Chat #8:** "What's the most profitable way to fill Friday — 3 open slots" — ranked by profitability
- **Data Section:** Revenue per job, cost per resource-hour (fully loaded), overtime rates, dynamic pricing rules, parts/material costs

**What's NOT specified:**
- Exact formula for revenue-per-resource-hour calculation
- How "fully loaded cost" is defined (wages + benefits + truck + fuel — but what percentages?)
- Dynamic pricing rule configuration interface
- How revenue optimization interacts with customer fairness (does a low-value customer always get deprioritized?)

### 2.7 Inventory/Equipment Tracking — 10% Built, Moderately Specified

**What exists:** `assigned_equipment` (JSON) on Staff, `equipment_required` (JSON) on Job, `materials_needed` (JSONB) on Appointment

**What requirements specify:**
- Criterion #7: Verify truck carries required equipment; prevent "wrong truck" dispatches
- Resource Chat #8: "Log that I replaced 4 spray heads and 2 rotors" — update job record, decrement truck inventory
- Resource Alert #9: Parts running low — predict consumption will exceed stock for remaining jobs
- Data Section: Stock levels of common parts, reorder thresholds, supply house locations

**What's NOT specified:**
- Inventory item master list (what parts are tracked)
- Initial truck stocking workflow
- Reorder automation (just alert, or auto-order?)
- Integration with parts suppliers
- Barcode/QR scanning for inventory management

### 2.8 Customer Satisfaction & Relationship Data — 5% Built, Specified in Requirements

**What exists:** No satisfaction tracking, no relationship ratings, no preferred technician field

**What requirements specify:**
- Criterion #14: Customer lifetime value (CLV) score — scheduling preference during high-demand
- Criterion #15: Customer-resource relationship history — prefer 5-star rated pairings, honor name requests
- Criterion #10: Resource performance history — match complex jobs to top performers
- Admin Alert #8: Customer prefers different resource — dissatisfaction from last visit
- Data Section: CLV scores, per-visit satisfaction, aggregate NPS, customer-resource ratings

**What's NOT specified:**
- How satisfaction scores are collected (post-visit survey? in-app rating? manual entry?)
- CLV calculation formula
- NPS collection mechanism and cadence
- How "preferred technician" requests are captured
- Privacy implications of tracking customer-resource relationship data

### 2.9 Multi-Phase Project Support — 0% Built, Briefly Specified

**What requirements specify:**
- Criterion #30: Cross-job dependency chains — "Job B cannot start until Job A is complete (e.g., rough-in before head installation)"; enforce phase sequencing; alert if upstream delays threaten downstream
- Job Data: job_phase, phase_sequence, phase_dependencies

**What's NOT specified:**
- Maximum dependency chain depth
- How phases are defined (per job type template? per project?)
- Gantt-style visualization for multi-phase projects
- What happens when a phase is delayed (auto-cascade all downstream? notify and hold?)
- Resource continuity across phases (same tech for all phases?)

### 2.10 Compliance/Regulatory Module — 0% Built, Moderately Specified

**What requirements specify:**
- Criterion #21: Compliance deadlines — backflow test certification expiration, municipal inspection windows, warranty service windows; schedule before deadline (hard constraint)
- Component Map: Compliance/Regulatory — backflow test expiry dates, municipal inspection requirements, watering restriction schedules, permit deadlines; proactive job generation when deadlines approach
- Data Section: Municipal compliance calendars

**What's NOT specified:**
- Which specific regulations apply (Minnesota-specific? varies by municipality?)
- How compliance calendars are maintained (manual entry? API? data subscription?)
- Notification cadence before deadline (30 days? 14 days? 7 days?)
- What happens when a deadline is missed (escalation, penalty tracking)
- Reporting requirements for regulatory bodies

---

## 3. Gaps NOT Addressed in Requirements.md

These are gaps identified in the analysis that the requirements document does not cover at all.

### 3.1 Data Migration & Bootstrapping

**The problem:** A new business adopting this system has years of scheduling history in spreadsheets, ServiceTitan, Jobber, or paper records. The ML models need this historical data to function.

**What's missing from requirements:**
- No data import strategy for existing businesses
- No data cleaning/normalization workflow
- No mapping from competitor system schemas to ours
- No minimum data quality thresholds
- No "getting started" flow that works with zero historical data
- The doc lists "Difficulty for someone to start using from the start" as an open question but provides no answer

### 3.2 Offline/Degraded Mode

**The problem:** The system depends on 4+ external APIs (weather, Google Maps, LLM, GPS). Any of them can fail.

**What's missing from requirements:**
- No fallback behavior when weather API is unavailable
- No fallback when Google Maps is unreachable (Haversine exists in code but isn't referenced in requirements)
- No fallback when LLM API is down (chat becomes unusable)
- No offline mode for resource mobile app (technicians work in basements, rural areas)
- No graceful degradation strategy (which features work without which dependencies)
- No SLA expectations for external API uptime

### 3.3 Multi-Tenant Architecture

**The problem:** The requirements mention "vertical configurability" and "irrigation is a configuration pack, not custom code" — implying this could become a product serving multiple businesses.

**What's missing from requirements:**
- No multi-tenancy data model (shared database vs. isolated per tenant)
- No tenant provisioning workflow
- No per-tenant configuration (business hours, zones, pricing rules)
- No data isolation guarantees between tenants
- No per-tenant billing model
- No tenant-scoped AI model training (one business's data shouldn't influence another's predictions)

### 3.4 Granular Permission Model

**The problem:** The requirements define two roles (User Admin, Resource) but real businesses have more nuanced permission needs.

**What's missing from requirements:**
- No sub-permissions within Admin role (dispatcher vs. owner vs. office manager)
- No definition of who can override AI decisions
- No approval hierarchy (can a junior admin clear a full day's schedule? approve overtime?)
- No read-only vs. read-write distinction for schedule views
- No audit of who approved what
- No role for "owner" who sees financial data that dispatchers shouldn't

### 3.5 AI Decision Audit Trail

**The problem:** The AI makes "autonomous decisions" per the requirements. Businesses need to understand and audit what the AI did and why.

**What's missing from requirements:**
- No logging specification for autonomous AI actions
- No explainability requirement for alerts/suggestions (why was this flagged?)
- No "show me what the AI changed today" summary view
- No regulatory compliance for AI decision-making (depending on jurisdiction)
- No customer-facing explanation when their appointment is moved by AI

**Note:** The codebase already has `AIAuditLog` and `AIUsage` models, but the requirements don't reference or build on them.

### 3.6 LLM Cost Controls

**The problem:** Every chat interaction, every alert explanation, and every schedule generation calls an LLM. At scale, this is expensive.

**What's missing from requirements:**
- No cost model (cost per interaction, cost per schedule generation)
- No rate limiting strategy (max interactions per user per hour)
- No caching strategy (repeated similar queries)
- No tiered AI quality (use cheaper model for simple queries, expensive for complex)
- No cost visibility for admin ("your AI usage this month: $X")
- The doc lists "What will be the costs for using this service?" as an open question but provides no answer

### 3.7 Notification Delivery Logic

**The problem:** The requirements mention SMS, email, phone, and app push as notification channels but don't specify the operational details.

**What's missing from requirements:**
- No channel priority/fallback order (if SMS fails, try email?)
- No quiet hours (don't text customers at 11pm about a Tuesday reschedule)
- No delivery confirmation tracking (was the notification read?)
- No retry logic for failed deliveries
- No escalation when critical notifications go unread
- No opt-out management per notification type (I want appointment reminders but not marketing)
- No localization/language considerations

### 3.8 Conflicting AI Suggestions

**The problem:** The AI generates multiple suggestions simultaneously. Some may contradict each other.

**What's missing from requirements:**
- No priority ranking system when suggestions conflict
- No mutual exclusion rules (if you accept suggestion A, suggestion B auto-dismisses)
- No "package" suggestions (these 3 suggestions work best together)
- No impact calculation showing combined effect of multiple accepted suggestions
- No undo for a suggestion that made things worse

### 3.9 Rollback/Undo for AI Actions

**The problem:** The AI can autonomously reschedule dozens of jobs (e.g., weather event). The admin needs to be able to undo this.

**What's missing from requirements:**
- No schedule versioning (snapshot before/after AI action)
- No "undo last AI action" capability
- No batch rollback for weather-driven rescheduling
- No confirmation step before AI executes large-scale changes
- No impact preview showing what will change before execution

**Note:** The codebase has `ScheduleClearAudit` for tracking cleared schedules, which is a partial foundation.

### 3.10 ML Training Data Requirements

**The problem:** Every ML model needs historical data to train. The requirements don't specify how much or what quality.

**What's missing from requirements:**
- No minimum dataset size per model (how many past jobs for duration prediction?)
- No data quality requirements (what if historical durations are inaccurate?)
- No cold-start strategy (what do the models do on day 1 with no data?)
- No model accuracy thresholds (when is a prediction "good enough" to use?)
- No retraining cadence (weekly? monthly? continuous?)
- No A/B testing framework (is the new model better than the old one?)
- No model monitoring (detecting when model accuracy degrades)

### 3.11 Resource Onboarding

**The problem:** When a new technician joins, they need to be set up in the system before the AI can schedule them.

**What's missing from requirements:**
- No new resource onboarding workflow
- No skill/certification assessment process
- No truck inventory initialization
- No home base geocoding step
- No ramp-up period (new techs shouldn't get complex jobs immediately)
- No training mode (shadow experienced tech before solo scheduling)

### 3.12 Customer-Facing Visibility

**The problem:** The requirements are entirely admin/resource focused. Customers are passive recipients.

**What's missing from requirements:**
- No customer appointment confirmation interface
- No self-service rescheduling portal
- No real-time ETA tracking for customers
- No post-visit satisfaction rating submission
- No customer communication preference management
- No "preferred technician" request mechanism
- Customer satisfaction is a core criterion (#14, #15) but there's no defined way for customers to provide it

### 3.13 Testing/Validation Framework

**The problem:** "How will we test functionality prior to sending it to market?" is listed as an open question.

**What's missing from requirements:**
- No simulation framework for testing schedule quality on historical data
- No benchmark metrics (what is a "good" schedule?)
- No A/B testing strategy (AI-generated vs. manual schedule comparison)
- No load testing requirements (100 jobs/day vs. 1000)
- No regression testing for AI behavior (does a model update break existing flows?)
- No user acceptance testing plan

### 3.14 Performance & Scale Requirements

**The problem:** The system needs to generate schedules, run ML models, and serve real-time chat. No performance targets are defined.

**What's missing from requirements:**
- No maximum response time for schedule generation (current: 30-second timeout)
- No maximum response time for chat interactions
- No concurrent user targets (5 admins? 50 resources?)
- No maximum jobs-per-day capacity
- No data retention policy (how long to keep historical schedules?)
- No geographic scale (one metro? statewide? multi-state?)

### 3.15 Integration Specifications

**The problem:** Section 8 lists 10 component integrations at a conceptual level only.

**What's missing from requirements:**
- No API contracts between scheduler and other components
- No data format specifications (JSON schemas, field mappings)
- No sync frequency (real-time push? polling every 5 min? daily batch?)
- No error handling for integration failures
- No data ownership rules (which component is source of truth for each field?)
- No versioning strategy for integration APIs

### 3.16 Mobile-Specific UX

**The problem:** Resource features are described functionally but the mobile context imposes unique constraints.

**What's missing from requirements:**
- No offline mode specification (technicians lose connectivity frequently)
- No touch-interaction patterns (fat fingers, gloves, sun glare)
- No push notification behavior (frequency, grouping, snooze)
- No battery/data usage considerations
- No GPS tracking privacy controls (when does tracking start/stop?)
- No voice input for hands-free operation while working
- No photo/media capture for job documentation

---

## 4. Constraint Solver Coverage (8 of 30 Implemented)

The current `ScheduleSolverService` and `ConstraintChecker` implement approximately 8 of the 30 required criteria:

| # | Criterion | Status | Notes |
|---|---|---|---|
| 1 | Resource-to-Job Proximity | **Implemented** | Haversine + Google Maps travel time |
| 2 | Intra-Route Drive Time | **Implemented** | Soft constraint, weight 80 |
| 3 | Service Zone Boundaries | **Partial** | City batching exists (weight 70), but no polygon zones |
| 4 | Real-Time Traffic | **Not implemented** | Google Maps API exists but not used in real-time during scheduling |
| 5 | Job Site Access Constraints | **Not implemented** | `gate_code` and `access_instructions` exist on Property but not in solver |
| 6 | Skill/Certification Match | **Not implemented** | Data exists (`certifications` on Staff, `equipment_required` on Job) but not enforced in solver |
| 7 | Equipment on Truck | **Partial** | Hard constraint checks equipment matching but limited |
| 8 | Resource Availability Windows | **Implemented** | Hard constraint — respects shift times and availability |
| 9 | Resource Workload Balance | **Not implemented** | No even-distribution logic |
| 10 | Resource Performance History | **Not implemented** | No performance metrics used in scheduling |
| 11 | Customer Time-Window Preference | **Not implemented** | `time_window_start/end` exists on Appointment but not as solver constraint |
| 12 | Job Type Duration Estimate | **Partial** | `estimated_duration_minutes` used but not AI-adjusted |
| 13 | Job Priority Level | **Implemented** | Soft constraint, weight 90 |
| 14 | Customer Lifetime Value | **Not implemented** | No CLV data exists |
| 15 | Customer-Resource Relationship | **Not implemented** | No relationship tracking |
| 16 | Daily Capacity Utilization | **Not implemented** | No utilization monitoring |
| 17 | Weekly Demand Forecast | **Not implemented** | No forecasting model |
| 18 | Seasonal Peak Windows | **Not implemented** | `JobGenerator` knows seasons but solver doesn't |
| 19 | Cancellation/No-Show Probability | **Not implemented** | No prediction model |
| 20 | Pipeline/Backlog Pressure | **Not implemented** | No backlog aging tracking |
| 21 | Compliance Deadlines | **Not implemented** | No compliance tracking |
| 22 | Revenue Per Resource-Hour | **Not implemented** | No revenue optimization |
| 23 | Contract/SLA Commitments | **Not implemented** | No SLA tracking |
| 24 | Overtime Cost Threshold | **Not implemented** | `hourly_rate` exists but no overtime logic |
| 25 | Seasonal Pricing Signals | **Not implemented** | No dynamic pricing |
| 26 | Weather Forecast Impact | **Not implemented** | `weather_sensitive` flag exists but no weather API |
| 27 | Predicted Job Complexity | **Not implemented** | No complexity model |
| 28 | Lead-to-Job Conversion Timing | **Not implemented** | No conversion prediction |
| 29 | Resource Location at Shift Start | **Partial** | `default_start_lat/lng` exists on Staff |
| 30 | Cross-Job Dependency Chains | **Not implemented** | No phase/dependency tracking |

**Summary:** 4 fully implemented, 4 partially implemented, 22 not implemented.

---

## 5. Component Integration Readiness

| Component | Requirements Say | What Exists | Gap |
|---|---|---|---|
| **Customer Intake / CRM** | Reads new job requests, customer details, urgency, time windows | Lead + Customer + Job models exist; lead-to-customer conversion exists | Need: automated job creation from lead conversion, urgency extraction |
| **Sales / Quoting** | Reads approved quotes, scope/duration, project phases | Estimate model exists | Need: estimate-to-job conversion, multi-phase project creation |
| **Marketing / Lead Mgmt** | Reads campaign calendars, conversion probabilities, outreach schedules | Lead model with sources exists | Need: campaign calendar integration, conversion scoring |
| **Customer Communication** | Triggers confirmations, ETA updates, delay notifications, reminders | Email + SMS services exist | Need: scheduling-triggered notifications, template system, delivery tracking |
| **Workforce / HR** | Reads roster, certifications, PTO, onboarding status | Staff + StaffAvailability models exist | Need: PTO calendar, certification expiry tracking, onboarding workflow |
| **Inventory / Equipment** | Reads truck equipment, stock levels, reorder thresholds | JSON fields on Staff/Job | Need: proper inventory model, stock tracking, reorder automation |
| **Financial / Billing** | Reads job pricing, resource costs, overtime rules, payment status | Stripe + Invoice models exist; hourly_rate on Staff | Need: cost-per-resource-hour calculation, overtime rules, payment status in scheduling |
| **Reporting / Analytics** | Reads historical performance for ML training | Job/Appointment history exists | Need: ML training pipeline, performance dashboards, data export |
| **Compliance / Regulatory** | Reads certification expiry, inspection requirements, permit deadlines | Backflow data on Property (partially) | Need: compliance calendar, deadline tracking, proactive job generation |
| **CRM (Master Record)** | Single source of truth for all customer data | Customer model is the master record | Need: CLV calculation, satisfaction tracking, preference management |

---

## 6. Summary Scorecard

### Requirements Coverage

| Category | Covered in Requirements | Not Covered |
|---|---|---|
| 30 Decision Criteria | **30/30** | 0 |
| ML Models | **5/6** | 1 (resource performance prediction as explicit model) |
| Chat Interactions | **20/20** | 0 |
| Alerts/Suggestions | **20/20** | 0 |
| Data Entities | **8/8 domains** | 0 |
| Component Integrations | **10/10 listed** | 0 (but all conceptual, no API specs) |
| Operational Concerns | **0/16** | **16** (offline, permissions, audit, rollback, scale, testing, costs, migration, mobile UX, notifications, conflicts, onboarding, customer-facing, integration specs, multi-tenant, training data) |

### Codebase Readiness

| Area | Readiness | What's Needed |
|---|---|---|
| Data Models | **~65%** | Add CLV, NPS, relationship tracking, compliance dates, inventory model, job dependencies |
| Constraint Solver | **~27%** (8/30) | Add remaining 22 criteria |
| AI/ML Models | **0%** | Build all 5-6 prediction models |
| Admin Chat | **0%** | Build conversational scheduler |
| Resource Chat | **0%** | Build field technician AI assistant |
| Alert/Suggestion Engine | **0%** | Build autonomous monitoring + alert system |
| Weather Integration | **0%** | Add weather API |
| Revenue Optimization | **0%** | Build cost/revenue calculation engine |
| Mobile Resource App | **0%** | Build entire mobile experience |
| Customer Self-Service | **0%** (not in requirements) | Not specified but needed |

---

## 7. Recommended Build Order

Based on the gap analysis, maximizing value while building on existing infrastructure:

### Phase 1: Deepen the Solver (Leverage Existing Foundation)
- Add criteria 6, 9, 11, 12, 16, 20 to the existing `ConstraintChecker`
- Add weather API integration (criterion 26) using the existing `weather_sensitive` flag
- Build the alert/suggestion engine on top of existing conflict detection
- **Why first:** Biggest ROI on existing code; makes the current scheduler significantly smarter

### Phase 2: Admin AI Chat + Alert Panel
- Build conversational schedule builder using existing `/api/v1/ai/` pattern
- Build the Alerts/Suggestions panel as a new dashboard section
- Add one-click resolution workflows
- **Why second:** This is the primary user interaction paradigm

### Phase 3: ML Models
- Duration prediction model (criteria 12, 27) using existing job completion history
- Demand forecasting (criterion 17) from seasonal job patterns
- Cancellation prediction (criterion 19)
- **Why third:** Needs historical data from Phase 1-2 usage

### Phase 4: Resource Mobile Experience
- Mobile schedule view with route sequence
- Pre-job checklists from existing Property data (gate_code, access_instructions, has_dogs)
- Resource chat with escalation workflow
- **Why fourth:** Highest complexity; builds on admin features

### Phase 5: Revenue Optimization + Advanced
- Revenue per resource-hour calculation
- Dynamic pricing signals
- Customer satisfaction/relationship tracking (criteria 14, 15)
- Multi-phase project support (criterion 30)
- Compliance module (criterion 21)
- **Why last:** Advanced differentiation; requires mature data foundation
