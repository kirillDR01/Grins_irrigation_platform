# Implementation Plan: AI-Powered Scheduling System

## Overview

This plan implements the full AI scheduling system in 7 phases following the project's dependency pattern: database foundations → core scoring services → AI services → API routes → frontend components → comprehensive testing → quality checks. The backend uses Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / PostgreSQL. The frontend uses React 19 / TypeScript 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4. All 35 requirements, 22 correctness properties, 6 backend services, 6 database tables, 4 model extensions, all API routes, and all frontend components are covered.

## Tasks

- [x] 1. Database migrations, models, and schemas
  - [x] 1.1 Create Alembic migration for 6 new tables and 4 model extensions
    - Create migration file `migrations/versions/XXX_ai_scheduling_tables.py`
    - New tables: `scheduling_criteria_config` (30 criteria weights, hard/soft, enabled, config_json), `scheduling_alerts` (type, severity, title, description, affected_job_ids, affected_staff_ids, criteria_triggered, resolution_options, status, resolved_by, resolved_action, resolved_at, schedule_date), `change_requests` (resource_id, request_type, details, affected_job_id, recommended_action, status, admin_id, admin_notes, resolved_at), `scheduling_chat_sessions` (user_id, user_role, messages JSONB, context JSONB, is_active), `resource_truck_inventory` (staff_id, part_name, quantity, reorder_threshold, last_restocked), `service_zones` (name, boundary_type, boundary_data JSONB, assigned_staff_ids JSONB, is_active)
    - Extend `jobs` table: add `sla_deadline`, `compliance_deadline`, `job_phase`, `depends_on_job_id` (FK → jobs.id), `is_outdoor`, `predicted_complexity`, `revenue_per_hour`
    - Extend `staff` table: add `performance_score`, `callback_rate`, `avg_satisfaction`, `service_zone_id` (FK → service_zones.id), `overtime_threshold_minutes`
    - Extend `customers` table: add `clv_score`, `preferred_resource_id` (FK → staff.id), `time_window_preference`, `time_window_is_hard`
    - Extend `appointments` table: add `ai_explanation`, `criteria_scores` (JSONB)
    - Seed `scheduling_criteria_config` with all 30 criteria (numbers 1–30, names, groups, default weights, hard/soft classification, enabled=True)
    - _Requirements: 3.1–3.5, 4.1–4.5, 5.1–5.5, 6.1–6.5, 7.1–7.5, 8.1–8.5, 19.1–19.2, 20.1–20.2, 21.1–21.4, 35.1_

  - [x] 1.2 Create SQLAlchemy models for new tables
    - Create `src/grins_platform/models/scheduling_criteria_config.py` — `SchedulingCriteriaConfig` model with all columns from design
    - Create `src/grins_platform/models/scheduling_alert.py` — `SchedulingAlert` model with all columns from design
    - Create `src/grins_platform/models/change_request.py` — `ChangeRequest` model with all columns from design
    - Create `src/grins_platform/models/scheduling_chat_session.py` — `SchedulingChatSession` model with all columns from design
    - Create `src/grins_platform/models/resource_truck_inventory.py` — `ResourceTruckInventory` model with all columns from design
    - Create `src/grins_platform/models/service_zone.py` — `ServiceZone` model with all columns from design
    - Add all models to `models/__init__.py` for Alembic discovery
    - Use `LoggerMixin` pattern where applicable
    - _Requirements: 19.1, 19.2, 20.1, 20.2, 21.1–21.4_

  - [x] 1.3 Extend existing models with new columns
    - Add to `Job` model: `sla_deadline` (DateTime, nullable), `compliance_deadline` (DateTime, nullable), `job_phase` (Integer, nullable), `depends_on_job_id` (UUID FK → jobs.id, nullable), `is_outdoor` (Boolean, default False), `predicted_complexity` (Float, nullable), `revenue_per_hour` (Numeric(10,2), nullable)
    - Add to `Staff` model: `performance_score` (Float, nullable), `callback_rate` (Float, nullable), `avg_satisfaction` (Float, nullable), `service_zone_id` (UUID FK → service_zones.id, nullable), `overtime_threshold_minutes` (Integer, nullable)
    - Add to `Customer` model: `clv_score` (Numeric(10,2), nullable), `preferred_resource_id` (UUID FK → staff.id, nullable), `time_window_preference` (String(50), nullable), `time_window_is_hard` (Boolean, default False)
    - Add to `Appointment` model: `ai_explanation` (Text, nullable), `criteria_scores` (JSONB, nullable)
    - _Requirements: 3.3, 4.3, 5.1–5.5, 7.1, 7.3, 8.5, 19.1, 19.2, 20.1, 20.2_

  - [x] 1.4 Create Pydantic schemas for all new endpoints
    - Create `src/grins_platform/schemas/ai_scheduling.py` with:
      - `CriterionResult` (criterion_number, criterion_name, score, weight, is_hard, is_satisfied, explanation)
      - `CriteriaScore` / `ScheduleEvaluation` (schedule_date, total_score, hard_violations, criteria_scores list, alerts list)
      - `RankedCandidate` (staff_id, name, composite_score, criterion_breakdown)
      - `ChatRequest` (message, session_id optional), `ChatResponse` (response, schedule_changes, clarifying_questions, change_request_id)
      - `SchedulingAlertResponse` (id, alert_type, severity, title, description, resolution_options, created_at)
      - `ResolutionOption` (action, label, description, parameters)
      - `ResolveAlertRequest` (action, parameters), `DismissAlertRequest`
      - `ChangeRequestResponse` (id, resource_id, request_type, details, affected_job_id, recommended_action, status, created_at)
      - `ApproveChangeRequest` (admin_notes optional), `DenyChangeRequest` (reason)
      - `AlertCandidate` (alert_type, severity, title, description, affected_job_ids, affected_staff_ids, criteria_triggered, resolution_options)
      - `PreJobChecklist` (job_type, customer_name, customer_address, required_equipment, known_issues, gate_code, special_instructions, estimated_duration)
      - `UpsellSuggestion` (equipment_name, age_years, repair_count, recommended_upgrade, estimated_savings)
      - `ScheduleChange` (change_type, job_id, staff_id, old_slot, new_slot, explanation)
      - `BatchScheduleRequest` / `BatchScheduleResponse`, `UtilizationReport`, `CapacityForecast`
      - `SchedulingConfig` (criteria weights, thresholds), `SchedulingContext` (schedule_date, weather, traffic, backlog)
    - _Requirements: 1.1–1.9, 2.1–2.5, 9.1–9.10, 10.1–10.10, 11.1–11.5, 12.1–12.5, 14.1–14.10, 15.1–15.10, 23.1_

- [x] 2. Checkpoint — Database and schema foundation
  - Run migration: `uv run alembic upgrade head`. Verify all 6 new tables and 4 model extensions exist. Run `uv run ruff check src/grins_platform/models/ src/grins_platform/schemas/ai_scheduling.py` and `uv run mypy src/grins_platform/models/ src/grins_platform/schemas/ai_scheduling.py`. Ensure all tests pass, ask the user if questions arise.


- [x] 3. Core services — CriteriaEvaluator and 6 scorer modules
  - [x] 3.1 Create CriteriaEvaluator service
    - Create `src/grins_platform/services/ai/scheduling/criteria_evaluator.py`
    - Implement `CriteriaEvaluator(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Constructor takes `AsyncSession` and `SchedulingConfig` (loaded from `scheduling_criteria_config` table)
    - Implement `evaluate_assignment(job, staff, context) → CriteriaScore` — scores a single job-staff assignment against all 30 criteria by delegating to 6 scorer modules and aggregating weighted scores
    - Implement `evaluate_schedule(solution, context) → ScheduleEvaluation` — scores entire schedule, returns aggregate with per-criterion breakdown and alerts for violations
    - Implement `rank_candidates(job, candidates, context) → list[RankedCandidate]` — ranks staff candidates by composite criteria score
    - Load criteria config from DB (weights, hard/soft, enabled flags) with caching via Redis
    - Wrap existing `ConstraintChecker` — criteria 1–2 delegate to existing travel/equipment checks
    - _Requirements: 3.1–3.5, 4.1–4.5, 5.1–5.5, 6.1–6.5, 7.1–7.5, 8.1–8.5, 23.1, 23.2, 32.1, 32.2_

  - [x] 3.2 Implement GeographicScorer (criteria 1–5)
    - Create `src/grins_platform/services/ai/scheduling/scorers/geographic.py`
    - Implement `GeographicScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 1: Resource-to-job proximity — score based on haversine distance (existing `haversine_travel_minutes`), fallback from Google Maps drive-time when available
    - Criterion 2: Intra-route drive time — total cumulative drive time across all jobs in resource's daily route, penalize high totals
    - Criterion 3: Service zone boundaries — check job location against `service_zones` table, prefer in-zone resources, allow cross-zone if more efficient
    - Criterion 4: Real-time traffic — overlay Google Maps traffic data on route calculations, adjust ETAs (fallback: skip criterion if API unavailable)
    - Criterion 5: Job site access constraints — check gate codes, HOA entry requirements, construction access windows from customer/job data, treat as hard constraint windows
    - Each criterion returns `CriterionResult` with score 0–100, weight, hard/soft, explanation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 31.2, 31.3_

  - [x] 3.3 Implement ResourceScorer (criteria 6–10)
    - Create `src/grins_platform/services/ai/scheduling/scorers/resource.py`
    - Implement `ResourceScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 6: Skill/certification match — verify job's required skill tags against resource's certifications (hard constraint)
    - Criterion 7: Equipment on truck — verify resource's truck carries required equipment from `resource_truck_inventory` and `Staff.assigned_equipment` (hard constraint)
    - Criterion 8: Resource availability windows — check shift start/end, PTO, training blocks from `StaffAvailability` (hard constraint)
    - Criterion 9: Workload balance — calculate standard deviation of job-hours across resources, penalize imbalance
    - Criterion 10: Performance history — score based on `Staff.performance_score`, `callback_rate`, `avg_satisfaction`, match high-complexity jobs to top performers
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.4 Implement CustomerJobScorer (criteria 11–15)
    - Create `src/grins_platform/services/ai/scheduling/scorers/customer_job.py`
    - Implement `CustomerJobScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 11: Customer time-window preferences — check `Customer.time_window_preference` and `time_window_is_hard`, hard constraint if hard, soft optimization if soft
    - Criterion 12: Job type duration estimates — use template default adjusted by `Job.predicted_complexity` from ML model
    - Criterion 13: Job priority level — emergency > VIP > standard > flexible ordering, schedule emergencies first
    - Criterion 14: Customer lifetime value (CLV) — use `Customer.clv_score` for tie-breaking during high-demand periods
    - Criterion 15: Customer-resource relationship history — prefer pairings where customer rated resource 5 stars or requested by name via `Customer.preferred_resource_id`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 3.5 Implement CapacityDemandScorer (criteria 16–20)
    - Create `src/grins_platform/services/ai/scheduling/scorers/capacity_demand.py`
    - Implement `CapacityDemandScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 16: Daily capacity utilization — calculate (assigned job minutes + drive minutes) / available minutes × 100, flag >90% overbooking and <60% underutilization
    - Criterion 17: Weekly demand forecast — predict job volume for 2–8 weeks based on historical patterns, seasonal trends, weather
    - Criterion 18: Seasonal peak windows — detect spring opening / fall closing rush periods, recommend overtime or temp staffing
    - Criterion 19: Cancellation/no-show probability — ML model prediction based on customer history, weather, day-of-week
    - Criterion 20: Pipeline/backlog pressure — track unscheduled jobs count and aging, escalate aging jobs
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 3.6 Implement BusinessRulesScorer (criteria 21–25)
    - Create `src/grins_platform/services/ai/scheduling/scorers/business_rules.py`
    - Implement `BusinessRulesScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 21: Compliance deadlines — check `Job.compliance_deadline`, schedule before deadline (hard constraint)
    - Criterion 22: Revenue per resource-hour — calculate `job_revenue / ((job_duration + drive_time) / 60)`, optimize for max daily revenue
    - Criterion 23: Contract/SLA commitments — check `Job.sla_deadline`, treat as hard constraint
    - Criterion 24: Overtime cost threshold — check `Staff.overtime_threshold_minutes`, penalize overtime unless job revenue justifies it
    - Criterion 25: Seasonal pricing signals — steer flexible jobs to off-peak slots, reserve peak for full-price work
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 3.7 Implement PredictiveScorer (criteria 26–30)
    - Create `src/grins_platform/services/ai/scheduling/scorers/predictive.py`
    - Implement `PredictiveScorer(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Criterion 26: Weather forecast impact — check 7-day forecast, penalize outdoor jobs on rain/freeze days, prefer indoor-safe backfill
    - Criterion 27: Predicted job complexity — use `Job.predicted_complexity` from ML model, assign longer time slots to complex jobs
    - Criterion 28: Lead-to-job conversion timing — identify hot leads from pipeline, reserve tentative capacity
    - Criterion 29: Resource location at shift start — determine home/shop/job-site origin for first-job routing
    - Criterion 30: Cross-job dependency chains — check `Job.depends_on_job_id` and `job_phase`, enforce phase sequencing (hard constraint)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 4. Checkpoint — Core scoring engine
  - Run `uv run ruff check src/grins_platform/services/ai/scheduling/` and `uv run mypy src/grins_platform/services/ai/scheduling/` and `uv run pyright src/grins_platform/services/ai/scheduling/`. Verify all 6 scorer modules and CriteriaEvaluator import cleanly. Ensure all tests pass, ask the user if questions arise.


- [x] 5. AI services — SchedulingChatService, AlertEngine, PreJobGenerator, ChangeRequestService
  - [x] 5.1 Implement SchedulingChatService
    - Create `src/grins_platform/services/ai/scheduling/chat_service.py`
    - Implement `SchedulingChatService(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Constructor takes `AsyncSession`, initializes `AIAgentService`, `CriteriaEvaluator`, `ScheduleGenerationService`
    - Implement `chat(user_id, role, message, session_id) → ChatResponse` — routes messages based on `UserRole` (admin vs resource)
    - Implement `_handle_admin_message()` — uses OpenAI function calling with admin tool set: `generate_schedule`, `reshuffle_day`, `insert_emergency`, `forecast_capacity`, `move_job`, `find_underutilized`, `batch_schedule`, `rank_profitable_jobs`, `weather_reschedule`, `create_recurring_route`
    - Implement `_handle_resource_message()` — uses OpenAI function calling with resource tool set: `report_delay`, `get_prejob_info`, `request_followup`, `report_access_issue`, `find_nearby_work`, `request_resequence`, `request_assistance`, `log_parts`, `get_tomorrow_schedule`, `request_upgrade_quote`
    - Apply role-specific system prompts with scheduling context
    - Ask clarifying questions before executing admin commands (Req 1.8)
    - For resource requests: handle autonomously OR package as ChangeRequest (Req 1.9)
    - Persist conversation history to `scheduling_chat_sessions` table
    - Enforce guardrails: reject off-topic questions (Req 24.2, 24.5)
    - Log all interactions with user role, parsed intent, response time (Req 32.3)
    - Implement audit trail for every chat interaction (Req 24.3)
    - _Requirements: 1.6, 1.7, 1.8, 1.9, 2.1, 2.2, 2.3, 2.4, 2.5, 9.1–9.10, 14.1–14.10, 24.2, 24.3, 24.5, 32.3, 34.1_

  - [x] 5.2 Implement admin scheduling tool functions
    - Create `src/grins_platform/services/ai/scheduling/admin_tools.py`
    - Implement all 10 admin tool functions as async methods callable by OpenAI function calling:
      - `generate_schedule(date, preferences)` — build weekly schedule using criteria 1–5, 6–8, 11–13, 16–18, 26 (Req 9.1)
      - `reshuffle_day(date, unavailable_resources, strategy)` — redistribute using criteria 8–9, 1–2, 11 (Req 9.2)
      - `insert_emergency(address, skill, duration, time_constraint)` — find best-fit using criteria 6, 7, 1, 13 (Req 9.3)
      - `forecast_capacity(job_type, weeks, zones)` — pull criteria 16–18, 20 (Req 9.4)
      - `move_job(job_id, target_day, target_time, same_tech)` — check criteria 15, 11, 1–2 (Req 9.5)
      - `find_underutilized(week)` — evaluate criteria 9, 16, 20, 17 (Req 9.6)
      - `batch_schedule(job_type, customer_count, weeks, zone_priority)` — use criteria 3, 11, 18, 26, 6–7 (Req 9.7)
      - `rank_profitable_jobs(day, open_slots)` — evaluate criteria 22, 13, 14, 25, 20 (Req 9.8)
      - `weather_reschedule(day)` — apply criterion 26, rebuild with criteria 1–2 (Req 9.9)
      - `create_recurring_route(accounts, cadence, preferences)` — use criteria 23, 14, 15, 3, 1–2 (Req 9.10)
    - Each tool returns structured data for Schedule Overview updates (Req 10.1–10.10)
    - _Requirements: 9.1–9.10, 10.1–10.10, 23.3_

  - [x] 5.3 Implement resource scheduling tool functions
    - Create `src/grins_platform/services/ai/scheduling/resource_tools.py`
    - Implement all 10 resource tool functions:
      - `report_delay(resource_id, delay_minutes)` — recalculate ETAs, alert admin if windows at risk (Req 14.1)
      - `get_prejob_info(resource_id, job_id)` — pull job template, customer profile, equipment checklist (Req 14.2)
      - `request_followup(resource_id, job_id, field_notes, parts_needed)` — create ChangeRequest (Req 14.3)
      - `report_access_issue(resource_id, job_id, issue_type)` — check customer profile, create ChangeRequest if needed (Req 14.4)
      - `find_nearby_work(resource_id, location)` — find jobs within 15-min radius matching skills/equipment (Req 14.5)
      - `request_resequence(resource_id, reason, shop_stop)` — check feasibility, create ChangeRequest (Req 14.6)
      - `request_assistance(resource_id, job_id, skill_needed)` — find nearby qualified resources, create ChangeRequest (Req 14.7)
      - `log_parts(resource_id, job_id, parts_list)` — update job record, decrement truck inventory, flag low stock (Req 14.8)
      - `get_tomorrow_schedule(resource_id)` — pull tomorrow's schedule with details (Req 14.9)
      - `request_upgrade_quote(resource_id, job_id, upgrade_type)` — pull pricing, create quote draft, create ChangeRequest (Req 14.10)
    - Each tool produces outputs for Resource mobile view and/or Alerts Panel (Req 15.1–15.10)
    - _Requirements: 14.1–14.10, 15.1–15.10_

  - [x] 5.4 Implement AlertEngine service
    - Create `src/grins_platform/services/ai/scheduling/alert_engine.py`
    - Implement `AlertEngine(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Constructor takes `AsyncSession` and `CriteriaEvaluator`
    - Implement `scan_and_generate(schedule_date) → list[SchedulingAlert]` — main scan method
    - Implement 5 alert detectors (red/critical):
      - `_detect_double_bookings(assignments)` — find overlapping time windows on same resource (Req 11.1)
      - `_detect_skill_mismatches(assignments)` — find jobs assigned to uncertified resources (Req 11.2)
      - `_detect_sla_risks(jobs)` — find SLA deadlines expiring before scheduled date (Req 11.3)
      - `_detect_resource_behind(assignments)` — find resources 40+ min behind via tracking (Req 11.4)
      - `_detect_weather_impacts(schedule_date, jobs)` — find outdoor jobs on severe weather days (Req 11.5)
    - Implement 5 suggestion generators (green):
      - `_suggest_route_swaps(assignments)` — find job swaps that reduce combined drive time (Req 12.1)
      - `_suggest_utilization_fills(assignments)` — find resources with 2+ hour gaps and matching backlog (Req 12.2)
      - `_suggest_customer_preference(assignments)` — find dissatisfaction feedback, recommend alternatives (Req 12.3)
      - `_suggest_overtime_avoidance(assignments)` — find low-priority jobs shiftable to avoid overtime (Req 12.4)
      - `_suggest_high_revenue_fills(open_slots)` — find high-revenue jobs matching open slots (Req 12.5)
    - Deduplicate against existing active alerts by (alert_type, affected_job_ids, schedule_date)
    - Persist new alerts to `scheduling_alerts` table
    - Log every alert/suggestion created with type, severity, criteria triggered (Req 32.4)
    - _Requirements: 11.1–11.5, 12.1–12.5, 23.4, 32.4_

  - [x] 5.5 Implement PreJobGenerator service
    - Create `src/grins_platform/services/ai/scheduling/prejob_generator.py`
    - Implement `PreJobGenerator(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Implement `generate_checklist(job_id, resource_id) → PreJobChecklist` — generates pre-job requirements based on job type, customer profile, equipment needs
    - Checklist must include: job type, customer name, customer address, required equipment list, known system issues, gate code, special instructions, estimated duration (Property 15)
    - Implement `generate_upsell_suggestions(job_id) → list[UpsellSuggestion]` — identify upsell opportunities based on customer equipment age and service history
    - _Requirements: 2.3, 14.2, 15.2, 15.9, 16.4, 16.5, 17.1, 17.2_

  - [x] 5.6 Implement ChangeRequestService
    - Create `src/grins_platform/services/ai/scheduling/change_request_service.py`
    - Implement `ChangeRequestService(LoggerMixin)` with `DOMAIN = "scheduling"`
    - Implement `create_request(resource_id, request_type, details) → ChangeRequest` — persist to `change_requests` table with AI-recommended action
    - Implement `approve_request(request_id, admin_id) → ChangeRequestResult` — execute the approved action (route change, job add, etc.)
    - Implement `deny_request(request_id, admin_id, reason) → ChangeRequestResult` — mark denied with reason, notify resource
    - Support all 8 request types: delay_report, followup_job, access_issue, nearby_pickup, resequence, crew_assist, parts_log, upgrade_quote
    - _Requirements: 2.4, 14.3, 14.4, 14.6, 14.7, 14.10, 15.3, 15.4, 15.6, 15.7, 15.10_

  - [x] 5.7 Implement resource alert generation for mobile view
    - Create `src/grins_platform/services/ai/scheduling/resource_alerts.py`
    - Implement resource-facing alert types:
      - Schedule Change – Job Added (Req 16.1)
      - Schedule Change – Job Removed with gap-fill suggestions (Req 16.2)
      - Route Resequenced with reason and updated navigation (Req 16.3)
      - Pre-Job Requirement – Special Equipment with confirmation prompt (Req 16.4)
      - Pre-Job Requirement – Customer Access with gate code, instructions, pet warnings (Req 16.5)
    - Implement resource-facing suggestion types:
      - Pre-Job Prep with customer history and spare parts recommendation (Req 17.1)
      - Upsell Opportunity with equipment age and upgrade recommendation (Req 17.2)
      - Optimized Departure Time with traffic avoidance (Req 17.3)
      - Parts Running Low with stock prediction and nearest supply house (Req 17.4)
      - Pending Approval status for submitted ChangeRequests (Req 17.5)
    - _Requirements: 16.1–16.5, 17.1–17.5_

  - [x] 5.8 Implement external service integrations and fallbacks
    - Create `src/grins_platform/services/ai/scheduling/external_services.py`
    - Implement Google Maps integration for travel time and traffic (Req 31.1) with fallback to `haversine_travel_minutes` with 1.4x factor (Req 31.3)
    - Implement Weather API integration for 7-day forecast (Req 8.1) with fallback: skip weather criterion (Req 31.3)
    - Implement Redis caching for AI query results and criteria config (Req 34.3) with fallback: direct DB queries (Req 31.3)
    - Validate API keys at startup, log clear error messages for missing keys (Req 31.2)
    - Log all external API calls with request initiation, response status, latency, errors (Req 32.5)
    - _Requirements: 31.1, 31.2, 31.3, 31.4, 32.5, 34.3, 34.4_

  - [x] 5.9 Implement data migration and onboarding utilities
    - Create `src/grins_platform/services/ai/scheduling/data_migration.py`
    - Implement data import tools for customer, job, resource, and schedule data from external systems (Req 25.1)
    - Implement data cleaning functions: geocode addresses, standardize job types, map skill tags (Req 25.2)
    - Define minimum data requirements per AI capability tier (Req 25.3)
    - Implement data quality flagging and guided remediation (Req 25.4)
    - Support incremental data enrichment for ML model accuracy improvement (Req 25.5)
    - _Requirements: 25.1, 25.2, 25.3, 25.4, 25.5_

  - [x] 5.10 Implement security, guardrails, and audit trail
    - Enforce PII protection: never include raw phone numbers, emails, or full addresses in AI prompts or logs (Req 24.1, Property 19)
    - Implement AI chat guardrails: reject off-topic questions, redirect to scheduling topics (Req 24.2, 24.5)
    - Implement audit trail logging for all AI interactions: user ID, role, timestamp, parsed intent, response summary (Req 24.3, Property 20)
    - Support configurable minimum data requirements for graceful degradation (Req 24.4)
    - Protect proprietary scheduling logic and AI prompts (Req 34.5)
    - _Requirements: 24.1, 24.2, 24.3, 24.4, 24.5, 34.5_

  - [x] 5.11 Implement LLM configuration and AI cost tracking
    - Support configurable LLM selection per function: chat, explanations, constraint parsing, predictions (Req 34.1)
    - Implement AI usage cost tracking per function for pricing and optimization (Req 34.2)
    - Implement caching for repeated AI queries (similar explanations, common constraint patterns) (Req 34.3)
    - _Requirements: 34.1, 34.2, 34.3_

  - [x] 5.12 Implement storage limits and scalability
    - Define and enforce per-user storage limits for schedule history, AI logs, ML training data (Req 35.1)
    - Implement historical data archival beyond configurable retention period (Req 35.2)
    - Ensure schedule generation scales linearly, sub-30s for up to 50 jobs (Req 35.3)
    - Implement batch generation partitioning by zone/resource group for large job counts (Req 35.4)
    - _Requirements: 35.1, 35.2, 35.3, 35.4_

- [x] 6. Checkpoint — AI services complete
  - Run `uv run ruff check src/grins_platform/services/ai/scheduling/` and `uv run mypy src/grins_platform/services/ai/scheduling/` and `uv run pyright src/grins_platform/services/ai/scheduling/`. Verify all services import cleanly and type-check. Ensure all tests pass, ask the user if questions arise.


- [x] 7. API routes — AI scheduling, alerts, and schedule extensions
  - [x] 7.1 Create AI scheduling API router
    - Create `src/grins_platform/api/v1/ai_scheduling.py`
    - Implement `router = APIRouter(prefix="/ai-scheduling", tags=["ai-scheduling"])`
    - `POST /chat` — role-aware AI chat endpoint, accepts `ChatRequest`, returns `ChatResponse`, routes to `SchedulingChatService.chat()` with user role from JWT
    - `POST /evaluate` — evaluate a schedule against 30 criteria, accepts schedule_date, returns `ScheduleEvaluation`
    - `GET /criteria` — list all 30 criteria with current weights, returns list of criteria config from DB
    - Add FastAPI dependencies for auth (`CurrentActiveUser`), session management
    - Add rate limiting on chat endpoint (Req 28.7)
    - Log all API requests with correlation IDs (Req 32.7)
    - _Requirements: 1.6, 1.7, 2.1–2.5, 9.1–9.10, 14.1–14.10, 23.1, 32.7_

  - [x] 7.2 Create alerts API router
    - Create `src/grins_platform/api/v1/alerts.py`
    - Implement `router = APIRouter(prefix="/alerts", tags=["scheduling-alerts"])`
    - `GET /` — list active alerts/suggestions, filterable by type (alert/suggestion), severity (critical/suggestion), schedule_date, status
    - `POST /{id}/resolve` — resolve an alert with chosen action, accepts `ResolveAlertRequest`, executes resolution via AlertEngine
    - `POST /{id}/dismiss` — dismiss a suggestion, accepts `DismissAlertRequest`
    - `GET /change-requests` — list pending change requests for admin review
    - `POST /change-requests/{id}/approve` — approve a change request, accepts `ApproveChangeRequest`
    - `POST /change-requests/{id}/deny` — deny a change request, accepts `DenyChangeRequest`
    - Role-based access: resolve/approve/deny require admin role
    - _Requirements: 11.1–11.5, 12.1–12.5, 13.1–13.10, 15.1–15.10_

  - [x] 7.3 Extend existing schedule API router
    - Modify `src/grins_platform/api/v1/schedule.py`
    - Add `GET /capacity` — extended capacity forecast with 30-criteria analysis, returns `CapacityForecast`
    - Add `POST /batch-generate` — batch schedule generation for multi-week campaigns, accepts `BatchScheduleRequest`, returns `BatchScheduleResponse`
    - Add `GET /utilization` — resource utilization report, returns `UtilizationReport`
    - _Requirements: 9.4, 9.7, 10.4, 10.7, 23.5_

  - [x] 7.4 Register new routers in main API router
    - Update `src/grins_platform/api/v1/router.py`
    - Import and include `ai_scheduling_router` with `prefix="/ai-scheduling"`, `tags=["ai-scheduling"]`
    - Import and include `alerts_router` with `prefix="/alerts"`, `tags=["scheduling-alerts"]`
    - _Requirements: 1.2, 1.5_

  - [x] 7.5 Update `.env.example` with new environment variables
    - Add `GOOGLE_MAPS_API_KEY` with description and example
    - Add `WEATHER_API_KEY` with description and example (if separate from existing)
    - Document all scheduling-specific env vars with descriptions
    - _Requirements: 31.1, 31.5_

- [x] 8. Checkpoint — API layer complete
  - Run `uv run ruff check src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/alerts.py` and type checks. Verify all endpoints are reachable. Ensure all tests pass, ask the user if questions arise.


- [x] 9. Frontend — Schedule Overview extensions
  - [x] 9.1 Create CapacityHeatMap component
    - Create `frontend/src/features/schedule/components/CapacityHeatMap.tsx`
    - Capacity row rendered at the bottom of the schedule grid showing daily aggregate utilization percentages
    - Color indicators: >90% red (overbooking risk), 60–90% green (healthy), <60% yellow (underutilization opportunity)
    - Accept schedule data as props, render a single row of day cells with percentage values and color-coded backgrounds
    - Use `data-testid="capacity-heat-map"` and per-cell `data-testid="capacity-cell-{day}"`
    - _Requirements: 1.3, 6.1, 10.1, 10.4_

  - [x] 9.2 Create ScheduleOverviewEnhanced component
    - Create `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.tsx`
    - Custom resource-row × day-column grid layout (NOT FullCalendar — this is a purpose-built grid matching the mockup)
    - Each row = one resource showing: name, role/title, inline utilization percentage (e.g., "Mike D. — Senior Tech — 87% utilized")
    - Each column = one day showing: date and total job count in header (e.g., "Mon 2/16 — 18 jobs")
    - Each cell contains job cards with: job type name, time window (e.g., "8:00 – 9:30 AM"), customer last name + address, indicator icons (⭐ for VIP customers, ⚠️ for conflicts)
    - Job cards color-coded by job type: Spring Opening = green, Fall Closing = orange, Maintenance = blue, New Build = purple, Backflow Test = teal (configurable color map)
    - Job type color legend bar above the grid with colored dots and labels
    - Week title header: "Schedule Overview — Week of {date}" with Day/Week/Month toggle buttons and "+ New Job" button
    - Add/remove resource controls on the schedule (Req 1.4)
    - Integrate CapacityHeatMap as the bottom row of the grid
    - Status indicators: confirmed, in-progress, completed, flagged
    - Route sequences per resource with ETAs
    - AI-generated annotations (explanations) per assignment from `criteria_scores` JSONB
    - Use `data-testid="schedule-overview-enhanced"`, per-resource-row `data-testid="resource-row-{id}"`, per-job-card `data-testid="job-card-{id}"`
    - _Requirements: 1.3, 1.4, 10.1, 10.2, 10.3, 10.5, 10.6, 10.9, 10.10_

  - [x] 9.3 Create BatchScheduleResults component
    - Create `frontend/src/features/schedule/components/BatchScheduleResults.tsx`
    - Multi-week campaign schedule display: jobs assigned by week, zone, and resource
    - Capacity utilization by week
    - Customer appointment notifications ready for batch send
    - Ranked list of best-fit jobs with projected revenue impact and one-click assignment (Req 10.8)
    - Use `data-testid="batch-schedule-results"`
    - _Requirements: 10.7, 10.8_

  - [x] 9.4 Create TanStack Query hooks for schedule extensions
    - Create `frontend/src/features/schedule/hooks/useAIScheduling.ts`
    - `useCapacityForecast(params)` — query `GET /api/v1/schedule/capacity`
    - `useBatchGenerate()` — mutation `POST /api/v1/schedule/batch-generate`
    - `useUtilizationReport(params)` — query `GET /api/v1/schedule/utilization`
    - `useEvaluateSchedule()` — mutation `POST /api/v1/ai-scheduling/evaluate`
    - `useCriteriaConfig()` — query `GET /api/v1/ai-scheduling/criteria`
    - Define query key factory: `aiSchedulingKeys`
    - _Requirements: 10.1–10.10_

- [x] 10. Frontend — Alerts/Suggestions Panel
  - [x] 10.1 Create AlertsPanel component
    - Create `frontend/src/features/scheduling-alerts/components/AlertsPanel.tsx`
    - Main panel rendering below the Schedule Overview grid
    - Header: "Alerts & Suggestions" with badge showing total alert count (e.g., "3 alerts")
    - Fetch alerts via `GET /api/v1/alerts/` with polling (configurable interval, default 30s)
    - Render alerts (red/⚠) and suggestions (green/💡) in a single scrollable list, alerts first then suggestions
    - Each item is an AlertCard or SuggestionCard component
    - Use `data-testid="alerts-panel"`, `data-testid="alerts-count-badge"`
    - _Requirements: 1.5, 11.1–11.5, 12.1–12.5_

  - [x] 10.2 Create AlertCard component
    - Create `frontend/src/features/scheduling-alerts/components/AlertCard.tsx`
    - Individual alert card with red/critical styling: red left border or background accent, ⚠ icon prefix in title
    - Header row: "⚠ ALERT — {alert_type}" with timestamp (e.g., "2 min ago")
    - Brief summary line (e.g., "Backflow test on Tue assigned to Carlos R. — not backflow-certified")
    - Detailed description paragraph with context and impact
    - One-click resolution action buttons as a row of styled buttons (e.g., "Reassign to Mike D.", "See alternatives", "Dismiss")
    - Resolution actions call `POST /api/v1/alerts/{id}/resolve`
    - Use `data-testid="alert-card-{id}"`
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [x] 10.3 Create SuggestionCard component
    - Create `frontend/src/features/scheduling-alerts/components/SuggestionCard.tsx`
    - Individual suggestion card with green styling: green left border or background accent, 💡 icon prefix in title
    - Header row: "💡 SUGGESTION — {suggestion_type}" with timestamp (e.g., "8 min ago")
    - Brief summary line (e.g., "Swap 2 jobs between Sarah K. and Carlos R. on Monday — saves 28 min drive time")
    - Detailed description paragraph with metrics (drive time saved, revenue impact, cost savings)
    - Accept/dismiss buttons as a row: primary "Accept" action, secondary actions (e.g., "See on map", "Review jobs"), and "Keep current"/"Leave as-is" dismiss option
    - Accept calls `POST /api/v1/alerts/{id}/resolve`, dismiss calls `POST /api/v1/alerts/{id}/dismiss`
    - Use `data-testid="suggestion-card-{id}"`
    - _Requirements: 13.6, 13.7, 13.8, 13.9, 13.10_

  - [x] 10.4 Create RouteSwapMap component
    - Create `frontend/src/features/scheduling-alerts/components/RouteSwapMap.tsx`
    - Map visualization for route swap suggestions showing before/after drive times
    - Display two resource routes with proposed swap highlighted
    - Accept/dismiss controls
    - Use `data-testid="route-swap-map"`
    - _Requirements: 12.1, 13.6_

  - [x] 10.5 Create ChangeRequestCard component
    - Create `frontend/src/features/scheduling-alerts/components/ChangeRequestCard.tsx`
    - Resource change request display with approve/deny buttons
    - Show resource name, request type, field notes, AI-recommended action
    - Approve calls `POST /api/v1/alerts/change-requests/{id}/approve`
    - Deny calls `POST /api/v1/alerts/change-requests/{id}/deny` with reason input
    - Use `data-testid="change-request-card-{id}"`
    - _Requirements: 15.3, 15.6, 15.7, 15.10_

  - [x] 10.6 Create TanStack Query hooks for alerts
    - Create `frontend/src/features/scheduling-alerts/hooks/useAlerts.ts`
    - `useAlerts(params)` — query `GET /api/v1/alerts/` with polling refetchInterval
    - `useResolveAlert()` — mutation `POST /api/v1/alerts/{id}/resolve`
    - `useDismissAlert()` — mutation `POST /api/v1/alerts/{id}/dismiss`
    - `useChangeRequests()` — query `GET /api/v1/alerts/change-requests`
    - `useApproveChangeRequest()` — mutation `POST /api/v1/alerts/change-requests/{id}/approve`
    - `useDenyChangeRequest()` — mutation `POST /api/v1/alerts/change-requests/{id}/deny`
    - Define query key factory: `alertKeys`
    - _Requirements: 11.1–11.5, 12.1–12.5, 13.1–13.10_

  - [x] 10.7 Create alert types and API client
    - Create `frontend/src/features/scheduling-alerts/types/index.ts` — TypeScript types for `SchedulingAlert`, `ResolutionOption`, `ChangeRequest`, `AlertType`, `Severity`
    - Create `frontend/src/features/scheduling-alerts/api/alertsApi.ts` — API client functions for all alert endpoints
    - Create `frontend/src/features/scheduling-alerts/index.ts` — public API exports
    - _Requirements: 11.1–11.5, 12.1–12.5_

- [x] 11. Frontend — AI Chat extensions
  - [x] 11.1 Create SchedulingChat component
    - Create `frontend/src/features/ai/components/SchedulingChat.tsx`
    - Persistent right sidebar panel layout (not modal or collapsible) — renders alongside the Schedule Overview in a two-column layout (schedule grid on left, chat on right)
    - Header showing "AI Scheduling Assistant" with model name badge (e.g., "Opus 4.6")
    - Chat messages with role labels: "AI ASSISTANT" (left-aligned, light background) and user name + role (right-aligned, colored background)
    - AI responses include inline criteria tag badges (e.g., "Criteria #1 Proximity", "Criteria #3 Zones", "Criteria #26 Weather") as small clickable pills showing which of the 30 criteria were used for that response
    - When AI generates or modifies a schedule, include an actionable "Publish Schedule →" button in the chat response that applies changes to the Schedule Overview
    - Clarifying question display with numbered list format and quick-response buttons
    - Schedule summary display inline (e.g., "Mon: 10 jobs, Tue: 10 jobs..." with metrics like total drive time and avg jobs/tech/day)
    - Send messages via `POST /api/v1/ai-scheduling/chat` with session management
    - Display schedule changes inline with accept/reject controls
    - Use `data-testid="scheduling-chat"`, `data-testid="chat-message-{role}"`, `data-testid="criteria-tag-{number}"`, `data-testid="publish-schedule-btn"`
    - _Requirements: 1.6, 1.8, 2.1, 2.2, 9.1–9.10_

  - [x] 11.2 Create ResourceMobileChat component
    - Create `frontend/src/features/ai/components/ResourceMobileChat.tsx`
    - Mobile-optimized chat for Resource role
    - Quick-action buttons for common operations: "Running late", "Pre-job info", "Log parts", "Tomorrow's schedule"
    - Display pre-job checklists inline
    - Display change request status updates
    - Use `data-testid="resource-mobile-chat"`
    - _Requirements: 1.7, 1.9, 2.3, 2.4, 14.1–14.10_

  - [x] 11.3 Create PreJobChecklist component
    - Create `frontend/src/features/ai/components/PreJobChecklist.tsx`
    - Pre-job requirements display for Resource mobile view
    - Show: job type, customer name/address, required equipment, known issues, gate code, special instructions, estimated duration
    - Confirmation checkboxes for equipment verification
    - Use `data-testid="prejob-checklist"`
    - _Requirements: 15.2, 15.9, 16.4, 16.5_

  - [x] 11.4 Create TanStack Query hooks for AI chat
    - Create `frontend/src/features/ai/hooks/useSchedulingChat.ts`
    - `useSchedulingChat()` — mutation `POST /api/v1/ai-scheduling/chat` with session_id management
    - `useChatHistory(sessionId)` — query chat session history
    - Define query key factory: `schedulingChatKeys`
    - _Requirements: 9.1–9.10, 14.1–14.10_

- [x] 12. Frontend — Resource Mobile View
  - [x] 12.1 Create ResourceScheduleView component
    - Create `frontend/src/features/resource-mobile/components/ResourceScheduleView.tsx`
    - Mobile schedule card with route order, ETAs, pre-job flags
    - Job cards showing: address, job type, estimated duration, customer notes, status
    - Total estimated drive time for the day
    - Pre-job requirements flagged for special prep
    - Use `data-testid="resource-schedule-view"`
    - _Requirements: 14.9, 15.9, 16.1_

  - [x] 12.2 Create ResourceAlertsList component
    - Create `frontend/src/features/resource-mobile/components/ResourceAlertsList.tsx`
    - Mobile alerts: job added/removed, route resequenced, special equipment, customer access
    - Tap interactions: view job details, request backlog fill, confirm equipment, launch navigation
    - Use `data-testid="resource-alerts-list"`
    - _Requirements: 16.1–16.5, 18.1–18.5_

  - [x] 12.3 Create ResourceSuggestionsList component
    - Create `frontend/src/features/resource-mobile/components/ResourceSuggestionsList.tsx`
    - Mobile suggestions: pre-job prep, upsell opportunity, departure timing, parts low, pending approval
    - Tap interactions: view history, initiate quote, update departure, navigate to supply house, view request status
    - Use `data-testid="resource-suggestions-list"`
    - _Requirements: 17.1–17.5, 18.6–18.10_

  - [x] 12.4 Create resource mobile types, API client, and hooks
    - Create `frontend/src/features/resource-mobile/types/index.ts` — TypeScript types for resource schedule, alerts, suggestions
    - Create `frontend/src/features/resource-mobile/api/resourceApi.ts` — API client for resource-specific endpoints
    - Create `frontend/src/features/resource-mobile/hooks/useResourceSchedule.ts` — TanStack Query hooks for resource data
    - Create `frontend/src/features/resource-mobile/index.ts` — public API exports
    - _Requirements: 14.1–14.10, 15.1–15.10, 16.1–16.5, 17.1–17.5_

- [x] 13. Checkpoint — Frontend components complete
  - Run `cd frontend && npm run build` to verify all components compile. Run `npm test` to verify existing tests still pass. Ensure all tests pass, ask the user if questions arise.


- [x] 14. Unit tests with Property-Based Testing (PBT) — Hypothesis strategies and properties 1–11
  - [x] 14.1 Create Hypothesis strategies and test infrastructure
    - Create `src/grins_platform/tests/unit/test_pbt_ai_scheduling.py`
    - Define Hypothesis strategies:
      - `st_schedule_job()` — random `ScheduleJob` with valid fields (location, duration, equipment, priority, time windows)
      - `st_schedule_staff()` — random `ScheduleStaff` with valid certifications, equipment, availability windows
      - `st_schedule_solution()` — random valid schedule with assignments
      - `st_criteria_config()` — random criteria weights (0–100) and hard/soft thresholds
      - `st_weather_forecast()` — random weather data (temperature, precipitation, freeze warnings)
      - `st_customer_profile()` — random customer with CLV, preferences, relationship history
      - `st_alert_candidate()` — random alert with type, severity, affected entities
    - Create mock helpers for `AsyncSession`, `CriteriaEvaluator`, `AlertEngine`, external services
    - All tests marked `@pytest.mark.unit`, minimum 100 examples per property via `@settings(max_examples=100)`
    - _Requirements: 26.1, 26.2, 26.3_

  - [x] 14.2 Write PBT for Property 1: Hard Constraint Invariant
    - **Property 1: Hard Constraint Invariant**
    - **Validates: Requirements 4.1, 4.2, 4.3, 5.1, 7.1, 7.3, 8.5, 26.3**
    - `@given` with random schedule solution
    - For every job-to-resource assignment: verify skill match, equipment match, availability window, no time overlap, hard customer time window, compliance deadline, SLA deadline, dependency ordering
    - All hard constraints must hold simultaneously

  - [x] 14.3 Write PBT for Property 2: Alert Detection Accuracy
    - **Property 2: Alert Detection Accuracy**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.5, 26.3**
    - `@given` with random schedule containing injected violations (overlaps, skill mismatches, SLA past, outdoor+weather)
    - Verify AlertEngine detects all injected violations (no false negatives)
    - Verify no alerts generated for violation-free schedules (no false positives)

  - [x] 14.4 Write PBT for Property 3: Proximity Scoring Monotonicity
    - **Property 3: Proximity Scoring Monotonicity**
    - **Validates: Requirements 3.1**
    - `@given` with random job and two resources at different distances
    - Verify closer resource gets higher or equal proximity score

  - [x] 14.5 Write PBT for Property 4: Intra-Route Drive Time Minimization
    - **Property 4: Intra-Route Drive Time Minimization**
    - **Validates: Requirements 3.2**
    - `@given` with random resource route of 3+ jobs
    - Verify solver's route has total drive time ≤ worst-case (reverse-sorted) ordering

  - [x] 14.6 Write PBT for Property 5: Zone Boundary Preference
    - **Property 5: Zone Boundary Preference**
    - **Validates: Requirements 3.3**
    - `@given` with random job and two resources (one in-zone, one out-of-zone) at equal distance
    - Verify in-zone resource gets higher zone criterion score

  - [x] 14.7 Write PBT for Property 6: Workload Balance
    - **Property 6: Workload Balance**
    - **Validates: Requirements 4.4**
    - `@given` with random schedule with 2+ resources
    - Verify std dev of assigned job-hours across resources ≤ std dev of all-to-one assignment

  - [x] 14.8 Write PBT for Property 7: Priority and CLV Ordering
    - **Property 7: Priority and CLV Ordering**
    - **Validates: Requirements 5.3, 5.4**
    - `@given` with two jobs competing for same slot with different priorities
    - Verify higher-priority job gets the slot; for equal priority, higher CLV wins

  - [x] 14.9 Write PBT for Property 8: Capacity Utilization Calculation
    - **Property 8: Capacity Utilization Calculation**
    - **Validates: Requirements 6.1**
    - `@given` with random schedule and resource
    - Verify utilization = (assigned job minutes + drive minutes) / available minutes × 100, within 0.1% tolerance

  - [x] 14.10 Write PBT for Property 9: Backlog Pressure Monotonicity
    - **Property 9: Backlog Pressure Monotonicity**
    - **Validates: Requirements 6.5**
    - `@given` with two backlog states (different job counts and ages)
    - Verify state with more/older jobs gets higher or equal backlog pressure score

  - [x] 14.11 Write PBT for Property 10: Revenue Per Resource-Hour Calculation
    - **Property 10: Revenue Per Resource-Hour Calculation**
    - **Validates: Requirements 7.2**
    - `@given` with random job-resource assignment
    - Verify revenue/hour = job_revenue / ((job_duration + drive_time) / 60), within $0.01 tolerance

  - [x] 14.12 Write PBT for Property 11: Overtime Cost-Benefit
    - **Property 11: Overtime Cost-Benefit**
    - **Validates: Requirements 7.4**
    - `@given` with random resource schedule extending into overtime
    - Verify overtime scorer penalizes UNLESS job revenue exceeds overtime cost

- [x] 15. Unit tests with PBT — Properties 12–22 and criteria unit tests
  - [x] 15.1 Write PBT for Property 12: Weather Impact on Outdoor Jobs
    - **Property 12: Weather Impact on Outdoor Jobs**
    - **Validates: Requirements 8.1, 23.7**
    - `@given` with random outdoor/indoor jobs and weather forecasts
    - Verify outdoor jobs on severe weather days get penalty; indoor jobs get neutral/positive

  - [x] 15.2 Write PBT for Property 13: Dependency Chain Ordering
    - **Property 13: Dependency Chain Ordering**
    - **Validates: Requirements 8.5**
    - `@given` with random jobs with dependency chains
    - Verify dependent job B starts after prerequisite job A completes; unscheduled A prevents B scheduling

  - [x] 15.3 Write PBT for Property 14: Route Swap Improvement Guarantee
    - **Property 14: Route Swap Improvement Guarantee**
    - **Validates: Requirements 12.1**
    - `@given` with random route swap suggestions from AlertEngine
    - Verify proposed swap results in strictly lower combined drive time

  - [x] 15.4 Write PBT for Property 15: Pre-Job Checklist Completeness
    - **Property 15: Pre-Job Checklist Completeness**
    - **Validates: Requirements 15.2**
    - `@given` with random job and resource
    - Verify checklist contains all required fields: job type, customer name, address, equipment list, known issues, gate code, special instructions, estimated duration

  - [x] 15.5 Write PBT for Property 16: Nearby Work Radius and Skill Filtering
    - **Property 16: Nearby Work Radius and Skill Filtering**
    - **Validates: Requirements 15.5**
    - `@given` with random resource location and nearby jobs
    - Verify all returned jobs are within 15-min drive, resource has required skills, truck has required equipment

  - [x] 15.6 Write PBT for Property 17: Parts Low-Stock Threshold Alert
    - **Property 17: Parts Low-Stock Threshold Alert**
    - **Validates: Requirements 15.8**
    - `@given` with random parts logging operations
    - Verify low-stock suggestion generated when inventory drops below threshold; no suggestion when at/above threshold

  - [x] 15.7 Write PBT for Property 18: 30-Criteria Evaluation Completeness
    - **Property 18: 30-Criteria Evaluation Completeness**
    - **Validates: Requirements 23.1**
    - `@given` with random schedule evaluation
    - Verify returned ScheduleEvaluation contains exactly 30 CriteriaScore entries, numbers 1–30, no duplicates, no missing

  - [x] 15.8 Write PBT for Property 19: PII Protection in AI Outputs
    - **Property 19: PII Protection in AI Outputs**
    - **Validates: Requirements 24.1**
    - `@given` with random customer data containing phone numbers, emails, addresses
    - Verify AI prompts and log entries do not contain raw PII; customer references use IDs or anonymized identifiers

  - [x] 15.9 Write PBT for Property 20: Audit Trail Completeness
    - **Property 20: Audit Trail Completeness**
    - **Validates: Requirements 24.3**
    - `@given` with random sequence of chat interactions
    - Verify audit log entry count equals processed chat message count; each entry contains user ID, role, timestamp, intent, summary

  - [x] 15.10 Write PBT for Property 21: Resource Chat Routing Completeness
    - **Property 21: Resource Chat Routing Completeness**
    - **Validates: Requirements 1.9**
    - `@given` with random resource messages
    - Verify each message produces exactly one of: direct response (no escalation) OR ChangeRequest record (not both, not neither)

  - [x] 15.11 Write PBT for Property 22: Constraint Parsing Round-Trip
    - **Property 22: Constraint Parsing Round-Trip**
    - **Validates: Requirements 26.3**
    - `@given` with random natural language scheduling constraints
    - Verify parse → describe → re-parse produces equivalent structured parameters

  - [x] 15.12 Write unit tests for all 30 criteria scorers individually
    - Create `src/grins_platform/tests/unit/test_ai_scheduling.py`
    - Test each of the 30 criteria scorers with mocked data inputs:
      - GeographicScorer: criteria 1–5 (proximity, drive time, zones, traffic, access)
      - ResourceScorer: criteria 6–10 (skills, equipment, availability, workload, performance)
      - CustomerJobScorer: criteria 11–15 (time windows, duration, priority, CLV, relationship)
      - CapacityDemandScorer: criteria 16–20 (utilization, forecast, seasonal, cancellation, backlog)
      - BusinessRulesScorer: criteria 21–25 (compliance, revenue/hour, SLA, overtime, pricing)
      - PredictiveScorer: criteria 26–30 (weather, complexity, lead conversion, start location, dependencies)
    - _Requirements: 26.4_

  - [x] 15.13 Write unit tests for alert and suggestion generation logic
    - Test all 5 alert types: double-booking, skill mismatch, SLA risk, resource behind, severe weather
    - Test all 5 suggestion types: route swap, underutilized resource, customer preference, overtime avoidable, high-revenue job
    - Mock schedule data, verify correct alert/suggestion generation with expected types and severities
    - _Requirements: 26.5_

  - [x] 15.14 Write unit tests for ChangeRequest packaging logic
    - Test all 10 Resource AI Chat interaction types produce correct ChangeRequest records:
      - delay_report, followup_job, access_issue, nearby_pickup, resequence, crew_assist, parts_log, upgrade_quote, and autonomous responses (prejob_info, tomorrow_schedule)
    - Verify correct request_type, details, affected_job_id, recommended_action
    - _Requirements: 26.6_

  - [x] 15.15 Write unit tests for PreJobGenerator, revenue/hour, capacity utilization, backlog pressure
    - Test PreJobGenerator checklist generation with various job types and customer profiles
    - Test revenue per resource-hour calculation with edge cases (zero drive time, zero duration)
    - Test capacity utilization calculation with various schedule densities
    - Test backlog pressure scoring with various queue sizes and ages
    - _Requirements: 26.4, 26.7_

- [x] 16. Checkpoint — Unit tests and PBT complete
  - Run `uv run pytest -m unit -v src/grins_platform/tests/unit/test_pbt_ai_scheduling.py src/grins_platform/tests/unit/test_ai_scheduling.py`. Verify all 22 property tests and all unit tests pass with zero failures. Check coverage: `uv run pytest --cov=src/grins_platform/services/ai/scheduling -m unit`. Ensure minimum 85% coverage on scheduling service modules (Req 26.7). Ensure all tests pass, ask the user if questions arise.


- [x] 17. Functional testing — User Admin and Resource workflows
  - [x] 17.1 Create functional test infrastructure
    - Create `src/grins_platform/tests/functional/test_ai_scheduling_functional.py`
    - Set up test fixtures with real PostgreSQL test database
    - Create seed data: staff with certifications/equipment/availability, customers with CLV/preferences, jobs with priorities/time windows/dependencies, service zones, criteria config
    - All tests marked `@pytest.mark.functional`
    - _Requirements: 27.1, 27.2_

  - [x] 17.2 Write functional tests for User Admin workflows
    - Test schedule building via AI Chat: natural language command → clarifying questions → schedule generated → Schedule Overview data updated (Req 27.3)
    - Test emergency job insertion: chat command → AI finds best-fit resource → job inserted → downstream ETAs recalculated (Req 27.3)
    - Test alert resolution: double-booking detected → admin resolves → one-click reassignment → routes recalculated (Req 27.3)
    - Test suggestion acceptance: route swap suggested → admin accepts → both routes updated → drive time reduced (Req 27.3)
    - Test batch scheduling: multiple jobs → zone prioritization → multi-week schedule generated (Req 27.3)
    - _Requirements: 27.3_

  - [x] 17.3 Write functional tests for Resource workflows
    - Test running late report: resource reports delay → ETAs recalculated → admin alerted if windows at risk (Req 27.4)
    - Test pre-job requirements retrieval: resource asks → checklist generated with equipment, access, customer history (Req 27.4)
    - Test follow-up job request: resource reports additional work → ChangeRequest packaged → admin alert created (Req 27.4)
    - Test parts logging: resource logs parts → job record updated → truck inventory decremented → low-stock flagged (Req 27.4)
    - Test nearby pickup work: resource finishes early → nearby jobs listed → admin approval → job added to route (Req 27.4)
    - _Requirements: 27.4_

  - [x] 17.4 Write functional tests for constraint satisfaction and alert pipeline
    - Test schedule generation constraint satisfaction with real DB records for staff availability, equipment, job priorities, customer time windows (Req 27.5)
    - Test alert/suggestion generation pipeline end-to-end: data input → criteria evaluation → alert created → admin interaction → resolution applied (Req 27.6)
    - _Requirements: 27.5, 27.6_

  - [x] 17.5 Verify all functional tests pass
    - Run `uv run pytest -m functional -v src/grins_platform/tests/functional/test_ai_scheduling_functional.py`
    - All tests must pass with zero failures (Req 27.7)
    - _Requirements: 27.7_

- [x] 18. Integration testing — Cross-component and external service validation
  - [x] 18.1 Create integration test infrastructure
    - Create `src/grins_platform/tests/integration/test_ai_scheduling_integration.py`
    - Set up full system stack: database, Redis, API layer
    - Create mock/stub implementations for external services (Google Maps, OpenAI, Weather API) with option for real APIs via env flags
    - All tests marked `@pytest.mark.integration`
    - _Requirements: 28.1, 28.2, 31.4_

  - [x] 18.2 Write integration tests for external service integrations
    - Test Google Maps API integration for travel time with fallback to haversine (Req 28.3)
    - Test OpenAI API integration for chat, explanations, constraint parsing with graceful degradation (Req 28.3)
    - Test Weather API integration with fallback (skip weather criterion) (Req 28.3)
    - Test Redis caching with fallback to direct DB queries (Req 28.3)
    - _Requirements: 28.3_

  - [x] 18.3 Write integration tests for cross-component data flows
    - Test Customer Intake → Scheduling: new job request flows with correct priority, time windows, customer data (Req 28.4)
    - Test Sales/Quoting → Scheduling: approved quote creates schedulable job with correct duration, phases (Req 28.4)
    - Test Scheduling → Customer Communication: schedule changes trigger notification events (delivery deferred) (Req 28.4)
    - Test Scheduling → Financial/Billing: job completion triggers invoicing with correct amounts (Req 28.4)
    - Test Scheduling → Inventory: parts logging decrements truck inventory, triggers low-stock alerts (Req 28.4)
    - Test Scheduling → Reporting: schedule adherence data written correctly (Req 28.4)
    - Test CRM → Scheduling: customer profile changes reflected in scheduling decisions (Req 28.4)
    - Test Compliance → Scheduling: approaching deadlines generate proactive jobs (Req 28.4)
    - _Requirements: 22.1–22.10, 28.4_

  - [x] 18.4 Write integration tests for API endpoints
    - Test all AI scheduling API routes: `POST /chat`, `POST /evaluate`, `GET /criteria` (Req 28.5)
    - Test all alert API routes: `GET /`, `POST /{id}/resolve`, `POST /{id}/dismiss` (Req 28.5)
    - Test all change request API routes: `GET /change-requests`, `POST /{id}/approve`, `POST /{id}/deny` (Req 28.5)
    - Test extended schedule routes: `GET /capacity`, `POST /batch-generate`, `GET /utilization` (Req 28.5)
    - _Requirements: 28.5_

  - [x] 18.5 Write integration tests for auth, rate limiting, and role-based access
    - Test User_Admin endpoints reject Resource-role tokens where role restrictions apply (Req 28.6)
    - Test Resource endpoints reject Admin-role tokens where applicable (Req 28.6)
    - Test rate limiting on AI-powered endpoints (Req 28.7)
    - _Requirements: 28.6, 28.7_

  - [x] 18.6 Verify all integration tests pass
    - Run `uv run pytest -m integration -v src/grins_platform/tests/integration/test_ai_scheduling_integration.py`
    - All tests must pass with zero failures (Req 28.8)
    - _Requirements: 28.8_

- [x] 19. Checkpoint — Backend testing complete
  - Run full backend test suite: `uv run pytest -m "unit or functional or integration" -v`. Verify zero failures across all tiers. Ensure all tests pass, ask the user if questions arise.


- [x] 20. Frontend component tests
  - [x] 20.1 Write tests for Schedule Overview extension components
    - Create `frontend/src/features/schedule/components/CapacityHeatMap.test.tsx` — test rendering, color indicators for >90%/<60%, data-testid attributes
    - Create `frontend/src/features/schedule/components/ScheduleOverviewEnhanced.test.tsx` — test job display, status indicators, add/remove resource controls
    - Create `frontend/src/features/schedule/components/BatchScheduleResults.test.tsx` — test multi-week display, revenue ranking
    - _Requirements: 30.6, 30.7, 30.8_

  - [x] 20.2 Write tests for Alerts/Suggestions Panel components
    - Create `frontend/src/features/scheduling-alerts/components/AlertsPanel.test.tsx` — test alert/suggestion rendering, polling, count display
    - Create `frontend/src/features/scheduling-alerts/components/AlertCard.test.tsx` — test red styling, resolution actions, one-click buttons
    - Create `frontend/src/features/scheduling-alerts/components/SuggestionCard.test.tsx` — test green styling, accept/dismiss actions
    - Create `frontend/src/features/scheduling-alerts/components/ChangeRequestCard.test.tsx` — test approve/deny buttons, field notes display
    - _Requirements: 30.6, 30.7, 30.8_

  - [x] 20.3 Write tests for AI Chat extension components
    - Create `frontend/src/features/ai/components/SchedulingChat.test.tsx` — test message send, response display, clarifying questions, inline schedule previews
    - Create `frontend/src/features/ai/components/ResourceMobileChat.test.tsx` — test quick-action buttons, mobile layout, change request status
    - Create `frontend/src/features/ai/components/PreJobChecklist.test.tsx` — test checklist fields, confirmation checkboxes
    - _Requirements: 30.6, 30.7, 30.8_

  - [x] 20.4 Write tests for Resource Mobile View components
    - Create `frontend/src/features/resource-mobile/components/ResourceScheduleView.test.tsx` — test route order, ETAs, job cards
    - Create `frontend/src/features/resource-mobile/components/ResourceAlertsList.test.tsx` — test alert types, tap interactions
    - Create `frontend/src/features/resource-mobile/components/ResourceSuggestionsList.test.tsx` — test suggestion types, tap interactions
    - _Requirements: 30.6, 30.7, 30.8_

  - [x] 20.5 Verify all frontend tests pass with coverage
    - Run `cd frontend && npm test -- --run` to verify all component tests pass
    - Run `cd frontend && npm run test:coverage` to verify coverage targets: components 80%+, hooks 85%+, utils 90%+
    - _Requirements: 30.6, 30.7_

- [x] 21. End-to-End browser testing with agent-browser
  - [x] 21.1 Create E2E test script for Schedule Overview
    - Create `scripts/e2e/test-ai-scheduling-overview.sh`
    - Validate schedule displays all assigned jobs across technicians by day/week with status indicators
    - Validate capacity utilization percentages display and update after schedule generation
    - Validate add/remove resource controls function correctly
    - Validate capacity heat map renders with overbooking/underutilization indicators
    - Capture screenshots to `e2e-screenshots/ai-scheduling/`
    - Use `agent-browser snapshot -i` for element refs, verify `data-testid` attributes
    - _Requirements: 29.1, 29.2, 29.3_

  - [x] 21.2 Create E2E test script for Alerts/Suggestions Panel
    - Create `scripts/e2e/test-ai-scheduling-alerts.sh`
    - Validate alerts (red) and suggestions (green) render below Schedule Overview with correct color coding
    - Validate one-click resolution actions on alerts execute correctly
    - Validate suggestion accept/dismiss actions execute and update schedule
    - Validate alert/suggestion counts update as AI generates new items
    - Verify database state after UI interactions using `psql` queries
    - _Requirements: 29.1, 29.2, 29.4, 29.9_

  - [x] 21.3 Create E2E test script for AI Chat (Admin)
    - Create `scripts/e2e/test-ai-scheduling-chat.sh`
    - Validate chat input accepts natural language commands and displays AI responses
    - Validate clarifying questions from AI are displayed and user responses processed
    - Validate schedule changes from chat commands reflected in Schedule Overview
    - _Requirements: 29.1, 29.2, 29.5_

  - [x] 21.4 Create E2E test script for Resource Mobile Chat
    - Create `scripts/e2e/test-ai-scheduling-resource.sh`
    - Set mobile viewport: `agent-browser set viewport 375 812`
    - Validate pre-job requirements display correctly on Resource mobile view
    - Validate schedule change alerts display on Resource mobile view
    - Validate resource chat interactions produce correct responses
    - _Requirements: 29.1, 29.2, 29.6_

  - [x] 21.5 Create E2E test script for responsive behavior
    - Create `scripts/e2e/test-ai-scheduling-responsive.sh`
    - Test at mobile (375×812), tablet (768×1024), desktop (1440×900) viewports
    - Capture screenshots at each viewport for all major pages
    - Verify no layout issues, overflow, or broken alignment
    - _Requirements: 29.7, 29.8_

  - [x] 21.6 Register E2E tests in test runner and add pre-flight checks
    - Update `scripts/e2e-tests.sh` to include all 5 new test scripts
    - Add pre-flight checks for frontend (http://localhost:5173), backend (http://localhost:8000), and agent-browser installation
    - Support `--headed` mode for debugging and `--test NAME` for individual tests
    - _Requirements: 29.10, 29.11, 29.12_

- [x] 22. Checkpoint — All testing complete
  - Run full test suite in order:
    1. `uv run pytest -m unit -v` (unit + PBT, no infrastructure)
    2. `uv run pytest -m functional -v` (functional, requires PostgreSQL)
    3. `uv run pytest -m integration -v` (integration, requires full stack)
    4. `cd frontend && npm test -- --run` (frontend component tests)
  - Verify zero failures across all tiers. Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 26.8, 27.7, 28.8, 33.6, 33.7_


- [x] 23. Code quality, linting, type safety, and simulation testing
  - [x] 23.1 Run and fix Ruff linting on all scheduling code
    - Run `uv run ruff check --fix src/grins_platform/services/ai/scheduling/ src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/alerts.py src/grins_platform/models/scheduling_*.py src/grins_platform/models/change_request.py src/grins_platform/models/service_zone.py src/grins_platform/models/resource_truck_inventory.py src/grins_platform/schemas/ai_scheduling.py`
    - Run `uv run ruff format src/` to ensure 88-char line formatting
    - Zero violations required
    - _Requirements: 30.1, 30.2_

  - [x] 23.2 Run and fix MyPy type checking on all scheduling code
    - Run `uv run mypy src/grins_platform/services/ai/scheduling/ src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/alerts.py src/grins_platform/models/ src/grins_platform/schemas/ai_scheduling.py`
    - Ensure all functions have complete type hints on all parameters and return types, no implicit `Any`
    - Zero errors required
    - _Requirements: 30.3, 30.5_

  - [x] 23.3 Run and fix Pyright type checking on all scheduling code
    - Run `uv run pyright src/grins_platform/services/ai/scheduling/ src/grins_platform/api/v1/ai_scheduling.py src/grins_platform/api/v1/alerts.py`
    - Zero errors required
    - _Requirements: 30.4_

  - [x] 23.4 Implement simulation testing infrastructure
    - Create test scenarios for realistic scheduling situations: seasonal peaks, emergency insertions, weather events, resource unavailability (Req 33.2)
    - Implement schedule quality metrics: total drive time, capacity utilization, SLA compliance rate, revenue per resource-hour (Req 33.3)
    - Support A/B testing of scheduling algorithms with metric comparison (Req 33.4)
    - Support incremental feature release flags per criterion (Req 33.5)
    - _Requirements: 33.1, 33.2, 33.3, 33.4, 33.5_

  - [x] 23.5 Verify interacting business component data sourcing
    - Verify all 10 business component integrations from Req 22 are wired:
      - Customer Intake (Req 22.1), Sales/Quoting (Req 22.2), Marketing/Lead Management (Req 22.3), Customer Communication triggers (Req 22.4), Workforce/HR (Req 22.5), Inventory/Equipment (Req 22.6), Financial/Billing (Req 22.7), Reporting/Analytics read+write (Req 22.8), Compliance/Regulatory (Req 22.9), CRM (Req 22.10)
    - Verify competitive differentiation: 30-constraint simultaneous evaluation (Req 23.1), predictive signals (Req 23.2), autonomous schedule building (Req 23.3), proactive predictions (Req 23.4), revenue optimization (Req 23.5), vertical configurability (Req 23.6), weather-aware scheduling (Req 23.7)
    - _Requirements: 22.1–22.10, 23.1–23.7_

- [x] 24. Final checkpoint — Full quality gate
  - Run complete quality gate: `uv run ruff check --fix src/ && uv run ruff format --check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v`
  - Verify zero errors across all quality checks (Req 33.7)
  - Verify all 35 requirements are covered by implementation and tests
  - Verify all 22 correctness properties have passing PBT tests
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 30.1–30.8, 33.6, 33.7_

## Notes

- All tasks are REQUIRED — none are optional. Every task must be implemented.
- Tasks follow the project's phased dependency pattern: database → services → API → frontend → testing → quality.
- Each task references specific requirements for traceability across all 35 requirements.
- All 22 correctness properties from the design document have dedicated PBT tasks.
- Checkpoints ensure incremental validation at each phase boundary.
- Property tests validate universal correctness properties; unit tests validate specific examples and edge cases.
- Twilio notification delivery is deferred — tests validate notification event creation only.
- External service integrations use mock/stub by default with real API option via env flags.
- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / PostgreSQL / Redis.
- Frontend: React 19 / TypeScript 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4.
- Logging: All services use `LoggerMixin` with `DOMAIN = "scheduling"`.
- Test markers: `@pytest.mark.unit`, `@pytest.mark.functional`, `@pytest.mark.integration`.
