# Design Document: AI-Powered Scheduling System

## Overview

The AI Scheduling System extends the existing Grin's Irrigation scheduling infrastructure with a 30-criteria evaluation engine, conversational co-piloting for two user roles (User Admin and Resource), a proactive alert/suggestion engine, and predictive intelligence. The system wraps the existing `ScheduleGenerationService` and `ScheduleSolverService` with a new `AISchedulingEngine` that layers 30 decision criteria on top of the current greedy + local search solver, adds an autonomous alert/suggestion pipeline, and provides role-aware AI Chat interactions with escalation workflows.

The design follows the project's vertical slice architecture. New scheduling AI logic lives in `services/ai/scheduling/` as an extension of the existing `services/ai/` structure. New API routes extend the existing `/api/v1/schedule` and `/api/v1/ai` routers. Frontend components extend the existing `features/schedule/` and `features/ai/` slices. The system integrates with OpenAI (chat, explanations, constraint parsing), Google Maps (travel time, traffic), and Redis (caching, rate limiting) via existing external service patterns.

Key architectural decisions:
- **Wrap, don't replace**: The existing `ScheduleSolverService` and `ConstraintChecker` remain the core solver. The new `CriteriaEvaluator` adds 30-criteria scoring as additional soft/hard constraints fed into the existing solver.
- **LLM as orchestrator**: The AI Chat uses OpenAI function calling to invoke scheduling tools. The LLM interprets user intent, asks clarifying questions, and calls structured tool functions — it does not directly manipulate schedules.
- **Event-driven alerts**: A background `AlertEngine` periodically scans schedule state and generates alerts/suggestions, stored in the database and pushed to the frontend via polling (WebSocket upgrade deferred).
- **Role-based chat routing**: A single `SchedulingChatService` routes messages based on user role, applying different system prompts, tool sets, and escalation rules for Admin vs. Resource.
- **Thin page composition**: All built components are composed into two page views (`AIScheduleView` for admins at `/schedule/generate`, `ResourceMobileView` for technicians at `/schedule/mobile`) following the project's thin page-wrapper pattern — pages import and render composed feature views, no business logic at the page level.

## Architecture

```mermaid
graph TB
    subgraph Frontend
        SO[Schedule Overview]
        AP[Alerts/Suggestions Panel]
        AC[AI Chat - Admin]
        RC[AI Chat - Resource Mobile]
    end

    subgraph API Layer
        SR[/api/v1/schedule/*]
        AR[/api/v1/ai-scheduling/*]
        ALR[/api/v1/scheduling-alerts/*]
    end

    subgraph AI Scheduling Engine
        SCH[SchedulingChatService]
        AE[AlertEngine]
        CE[CriteriaEvaluator]
        PJ[PreJobGenerator]
    end

    subgraph Existing Services
        SGS[ScheduleGenerationService]
        SSS[ScheduleSolverService]
        CC[ConstraintChecker]
        AIS[AIAgentService]
        CB[ContextBuilder]
        CP[ConstraintParserService]
    end

    subgraph External
        OAI[OpenAI API]
        GM[Google Maps API]
        WX[Weather API]
        RD[Redis Cache]
    end

    subgraph Data
        PG[(PostgreSQL)]
    end

    SO --> SR
    AP --> ALR
    AC --> AR
    RC --> AR

    SR --> SGS
    AR --> SCH
    ALR --> AE

    SCH --> AIS
    SCH --> CE
    SCH --> SGS
    AE --> CE
    AE --> PG
    CE --> CC
    CE --> SSS
    PJ --> PG

    AIS --> OAI
    CE --> GM
    CE --> WX
    CE --> RD
    SGS --> SSS
    SSS --> CC

    SGS --> PG
    AE --> PG
    SCH --> PG
```

### Request Flow: Admin Chat → Schedule Generation

1. Admin sends natural language command via AI Chat
2. `SchedulingChatService` receives message, identifies user role as Admin
3. LLM (via `AIAgentService`) interprets intent, asks clarifying questions if needed
4. LLM calls scheduling tool functions (e.g., `generate_schedule`, `insert_emergency`)
5. Tool functions invoke `CriteriaEvaluator` to score candidates against 30 criteria
6. `CriteriaEvaluator` feeds weighted scores into existing `ScheduleSolverService`
7. Solver produces `ScheduleSolution`, returned to LLM for natural language summary
8. Frontend receives structured schedule data + explanation, updates Schedule Overview

### Request Flow: Alert Generation Pipeline

1. `AlertEngine` runs on a configurable interval (default: every 5 minutes)
2. Scans current schedule state: overlaps, skill mismatches, SLA deadlines, weather, utilization
3. Each detector produces `AlertCandidate` objects with type, severity, affected entities, and resolution options
4. Candidates are deduplicated against existing active alerts
5. New alerts are persisted to `scheduling_alerts` table
6. Frontend polls `/api/v1/scheduling-alerts/` and renders in Alerts Panel

### Request Flow: Resource Chat → Change Request

1. Resource sends message via mobile AI Chat
2. `SchedulingChatService` identifies role as Resource, applies resource system prompt
3. LLM interprets intent (running late, needs help, parts logging, etc.)
4. For autonomous actions (ETA recalculation, pre-job info): executes directly, returns to Resource
5. For actions requiring approval (route change, follow-up job, crew assist): packages as `ChangeRequest`
6. `ChangeRequest` stored in DB, surfaces as alert in Admin's Alerts Panel
7. Admin approves/denies via one-click action, result pushed back to Resource

## Current Codebase Foundations

The following existing services, models, and components provide the foundation that this spec extends. All items listed here exist on the dev branch and should be wrapped/extended, not replaced.

### Backend Foundations

| Component | Path | What it provides |
|-----------|------|-----------------|
| `ScheduleGenerationService(LoggerMixin)` | `services/schedule_generation_service.py` | Core schedule generation using OR-Tools solver |
| `ScheduleSolverService(LoggerMixin)` | `services/schedule_solver_service.py` | Greedy + local search optimizer |
| `ConstraintChecker` | `services/schedule_constraints.py` | Hard/soft constraint definitions and validation |
| `AIAgentService(LoggerMixin)` | `services/ai/agent.py` | General AI agent with OpenAI integration |
| `ConstraintParserService(LoggerMixin)` | `services/ai/constraint_parser.py` | Natural language → structured constraint parsing |
| `ScheduleExplanationService(LoggerMixin)` | `services/ai/explanation_service.py` | AI-generated schedule explanations |
| `UnassignedJobAnalyzer(LoggerMixin)` | `services/ai/unassigned_analyzer.py` | AI analysis of why jobs remain unassigned |
| `TravelTimeService(LoggerMixin)` | `services/travel_time_service.py` | Google Maps travel time + haversine fallback |
| AI prompts | `services/ai/prompts/scheduling.py` | Scheduling-specific prompt templates |
| AI tools | `services/ai/tools/scheduling.py` | Scheduling tool definitions for function calling |
| AI context | `services/ai/context/builder.py` | Context assembly for AI prompts |
| Empty scaffolds | `services/ai/scheduling/`, `services/ai/scheduling/scorers/` | Empty directories (contain only `__pycache__` from prior branch work — clean up before implementing) |

### Existing Models

| Model | Path | Key columns for this spec |
|-------|------|--------------------------|
| `Job(Base)` | `models/job.py` | `weather_sensitive`, `priority_level`, `estimated_duration_minutes`, `equipment_required`, `job_type`, `category` |
| `Staff(Base)` | `models/staff.py` | `certifications`, `assigned_equipment`, `default_start_lat/lng`, `skill_level`, `role`, `is_available` |
| `Customer(Base)` | `models/customer.py` | `preferred_service_times`, `is_priority` |
| `Appointment(Base)` | `models/appointment.py` | `scheduled_date`, `time_window_start/end`, `route_order`, `estimated_arrival`, `staff_id`, `job_id` |

### Frontend Foundations

| Component/Hook | Path | What it provides |
|----------------|------|-----------------|
| `ScheduleGenerationPage` | `features/schedule/components/ScheduleGenerationPage.tsx` | Current schedule generation UI (date picker, job selector, constraints input, results) — will be replaced by `AIScheduleView` at the page composition phase |
| `SchedulePage` | `features/schedule/components/SchedulePage.tsx` | FullCalendar-based schedule view (remains for `/schedule` route) |
| `useGenerateSchedule`, `usePreviewSchedule`, `useScheduleCapacity` | `features/schedule/hooks/useScheduleGeneration.ts` | TanStack Query hooks for schedule generation API |
| `useWeeklySchedule`, `useDailySchedule` | `features/schedule/hooks/useAppointments.ts` | Existing schedule data fetching hooks |
| `AIQueryChat` | `features/ai/components/AIQueryChat.tsx` | General-purpose AI chat component |
| `AIScheduleGenerator` | `features/ai/components/AIScheduleGenerator.tsx` | AI schedule generation UI |
| `useAIChat` | `features/ai/hooks/useAIChat.ts` | General AI chat hook |
| `useAISchedule` | `features/ai/hooks/useAISchedule.ts` | AI schedule generation state hook |
| `ErrorBoundary` | `shared/components/ErrorBoundary.tsx` | Class-based error boundary with `fallback` prop and retry button |
| Feature barrel: `features/schedule/index.ts` | — | Exists, exports all schedule components/hooks/types |
| Feature barrel: `features/ai/components/index.ts` | — | Exists, exports 10 AI components |
| **No root barrel**: `features/ai/index.ts` | — | Does NOT exist — must be created to support `@/features/ai` imports |
| **Missing directories** | `features/scheduling-alerts/`, `features/resource-mobile/` | Do NOT exist — must be created from scratch |

## Components and Interfaces

### Backend Components

#### 1. CriteriaEvaluator (`services/ai/scheduling/criteria_evaluator.py`)

The core 30-criteria scoring engine. Wraps the existing `ConstraintChecker` and adds criteria 3–30 as additional scoring dimensions.

```python
class CriteriaEvaluator(LoggerMixin):
    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession, config: SchedulingConfig) -> None: ...

    async def evaluate_assignment(
        self, job: ScheduleJob, staff: ScheduleStaff, context: SchedulingContext
    ) -> CriteriaScore:
        """Score a single job-staff assignment against all 30 criteria.
        Returns weighted score with per-criterion breakdown."""

    async def evaluate_schedule(
        self, solution: ScheduleSolution, context: SchedulingContext
    ) -> ScheduleEvaluation:
        """Score an entire schedule against all 30 criteria.
        Returns aggregate score with alerts for violations."""

    async def rank_candidates(
        self, job: ScheduleJob, candidates: list[ScheduleStaff], context: SchedulingContext
    ) -> list[RankedCandidate]:
        """Rank staff candidates for a job by composite criteria score."""
```

Criteria are organized into 6 groups, each implemented as a scoring module:
- `GeographicScorer` (criteria 1–5): proximity, drive time, zones, traffic, access
- `ResourceScorer` (criteria 6–10): skills, equipment, availability, workload, performance
- `CustomerJobScorer` (criteria 11–15): time windows, duration, priority, CLV, relationship
- `CapacityDemandScorer` (criteria 16–20): utilization, forecast, seasonal, cancellation, backlog
- `BusinessRulesScorer` (criteria 21–25): compliance, revenue/hour, SLA, overtime, pricing
- `PredictiveScorer` (criteria 26–30): weather, complexity, lead conversion, start location, dependencies

Each scorer returns a `CriterionResult` with score (0–100), weight, hard/soft classification, and explanation text.

#### 2. SchedulingChatService (`services/ai/scheduling/chat_service.py`)

Role-aware chat service extending the existing `AIAgentService`.

```python
class SchedulingChatService(LoggerMixin):
    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None: ...

    async def chat(
        self, user_id: UUID, role: UserRole, message: str, session_id: UUID
    ) -> ChatResponse:
        """Process a scheduling chat message with role-based routing."""

    async def _handle_admin_message(self, message: str, context: AdminChatContext) -> ChatResponse: ...
    async def _handle_resource_message(self, message: str, context: ResourceChatContext) -> ChatResponse: ...
```

Uses OpenAI function calling with role-specific tool sets:
- **Admin tools**: `generate_schedule`, `reshuffle_day`, `insert_emergency`, `forecast_capacity`, `move_job`, `find_underutilized`, `batch_schedule`, `rank_profitable_jobs`, `weather_reschedule`, `create_recurring_route`
- **Resource tools**: `report_delay`, `get_prejob_info`, `request_followup`, `report_access_issue`, `find_nearby_work`, `request_resequence`, `request_assistance`, `log_parts`, `get_tomorrow_schedule`, `request_upgrade_quote`

#### 3. AlertEngine (`services/ai/scheduling/alert_engine.py`)

Autonomous alert and suggestion generator.

```python
class AlertEngine(LoggerMixin):
    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession, evaluator: CriteriaEvaluator) -> None: ...

    async def scan_and_generate(self, schedule_date: date) -> list[SchedulingAlert]:
        """Scan schedule state and generate alerts/suggestions."""

    async def _detect_double_bookings(self, assignments: list[ScheduleAssignment]) -> list[AlertCandidate]: ...
    async def _detect_skill_mismatches(self, assignments: list[ScheduleAssignment]) -> list[AlertCandidate]: ...
    async def _detect_sla_risks(self, jobs: list[Job]) -> list[AlertCandidate]: ...
    async def _detect_weather_impacts(self, schedule_date: date, jobs: list[Job]) -> list[AlertCandidate]: ...
    async def _suggest_route_swaps(self, assignments: list[ScheduleAssignment]) -> list[AlertCandidate]: ...
    async def _suggest_utilization_fills(self, assignments: list[ScheduleAssignment]) -> list[AlertCandidate]: ...
    async def _suggest_overtime_avoidance(self, assignments: list[ScheduleAssignment]) -> list[AlertCandidate]: ...
    async def _suggest_high_revenue_fills(self, open_slots: list[TimeSlot]) -> list[AlertCandidate]: ...
```

#### 4. PreJobGenerator (`services/ai/scheduling/prejob_generator.py`)

Generates pre-job requirement checklists for Resources.

```python
class PreJobGenerator(LoggerMixin):
    DOMAIN = "scheduling"

    async def generate_checklist(self, job_id: UUID, resource_id: UUID) -> PreJobChecklist:
        """Generate pre-job requirements based on job type, customer profile, equipment needs."""

    async def generate_upsell_suggestions(self, job_id: UUID) -> list[UpsellSuggestion]:
        """Identify upsell opportunities based on customer equipment age and service history."""
```

#### 5. ChangeRequestService (`services/ai/scheduling/change_request_service.py`)

Manages Resource-initiated change requests.

```python
class ChangeRequestService(LoggerMixin):
    DOMAIN = "scheduling"

    async def create_request(self, resource_id: UUID, request_type: str, details: dict) -> ChangeRequest: ...
    async def approve_request(self, request_id: UUID, admin_id: UUID) -> ChangeRequestResult: ...
    async def deny_request(self, request_id: UUID, admin_id: UUID, reason: str) -> ChangeRequestResult: ...
```

#### 6. New API Routes

**`/api/v1/ai-scheduling/`** — AI scheduling chat and operations:
- `POST /chat` — Role-aware AI chat endpoint
- `POST /evaluate` — Evaluate a schedule against 30 criteria
- `GET /criteria` — List all 30 criteria with current weights

**`/api/v1/scheduling-alerts/`** — Alert and suggestion management (renamed from `/api/v1/alerts/` on 2026-04-28; the original prefix is already taken by a generic Alert/SMS-cancellation router added 2026-04-16 for H-5 bughunt work):
- `GET /` — List active alerts/suggestions (filterable by type, severity)
- `POST /{id}/resolve` — Resolve an alert with a chosen action
- `POST /{id}/dismiss` — Dismiss a suggestion
- `GET /change-requests` — List pending change requests
- `POST /change-requests/{id}/approve` — Approve a change request
- `POST /change-requests/{id}/deny` — Deny a change request

**`/api/v1/schedule/`** — Extensions to existing schedule routes:
- `GET /capacity` — **Extends the existing `get_capacity` handler** (which already returns basic daily capacity) with 30-criteria analysis fields. Additive, non-breaking: existing response shape is preserved; new fields (per-criterion utilization, forecast confidence intervals, criteria-triggered alerts) are added to the response payload.
- `POST /batch-generate` — Batch schedule generation for multi-week campaigns (new endpoint)
- `GET /utilization` — Resource utilization report (new endpoint)

### Frontend Components

#### Schedule Overview Extensions (`features/schedule/`)
- `CapacityHeatMap.tsx` — Capacity row at the bottom of the schedule grid showing daily aggregate utilization percentages with color coding: >90% red (overbooking risk), 60–90% green (healthy), <60% yellow (underutilization opportunity)
- `ScheduleOverviewEnhanced.tsx` — Custom resource-row × day-column grid layout (replaces FullCalendar for the AI scheduling view). Each row = one resource (name, role, inline utilization %, e.g., "Mike D. — Senior Tech — 87% utilized"). Each column = one day (date + total job count in header, e.g., "Mon 2/16 — 18 jobs"). Cells contain job cards color-coded by job type (Spring Opening = green, Fall Closing = orange, Maintenance = blue, New Build = purple, Backflow Test = teal) with ⭐ VIP and ⚠️ conflict icons. Includes a job type color legend above the grid, a week title header with Day/Week/Month toggle and "+ New Job" button, and integrates CapacityHeatMap at the bottom.
- `BatchScheduleResults.tsx` — Multi-week campaign schedule display

#### Alerts/Suggestions Panel (`features/scheduling-alerts/`)
- `AlertsPanel.tsx` — Main panel rendering below Schedule Overview
- `AlertCard.tsx` — Individual alert (red) with one-click resolution actions
- `SuggestionCard.tsx` — Individual suggestion (green) with accept/dismiss
- `RouteSwapMap.tsx` — Map visualization for route swap suggestions
- `ChangeRequestCard.tsx` — Resource change request with approve/deny

#### AI Chat Extensions (`features/ai/`)
- `SchedulingChat.tsx` — Persistent right sidebar chat panel (not modal or collapsible) with scheduling-specific UI: inline schedule previews, clarifying question buttons, criteria tag badges (e.g., "Criteria #1 Proximity", "Criteria #26 Weather") in AI responses, and actionable "Publish Schedule" buttons when the AI generates/modifies schedules
- `ResourceMobileChat.tsx` — Mobile-optimized chat for Resource role
- `PreJobChecklist.tsx` — Pre-job requirements display for Resource mobile view

#### Resource Mobile View (`features/resource-mobile/`)
- `ResourceScheduleView.tsx` — Mobile schedule card with route order, ETAs, pre-job flags
- `ResourceAlertsList.tsx` — Mobile alerts (job added/removed, resequenced, equipment, access)
- `ResourceSuggestionsList.tsx` — Mobile suggestions (prep, upsell, departure, parts)

### Page Composition and Routing

All individual frontend components listed above are composed into two page views and registered with the router. No new business logic or API calls are introduced at the page level — this is purely composition, routing, and wiring.

#### AI Schedule Admin Page (`/schedule/generate`)

Replaces the current `ScheduleGeneratePage` wrapper. Composes `ScheduleOverviewEnhanced` (with integrated `CapacityHeatMap`), `AlertsPanel`, and `SchedulingChat` into a sidebar layout where the chat is a persistent right panel and the overview + alerts fill the main content area.

**Layout:**
- CSS Grid with `grid-template-columns: 1fr 380px` for main content + chat sidebar
- `<main>` landmark wraps ScheduleOverviewEnhanced and AlertsPanel
- `<aside>` landmark wraps SchedulingChat inside a React error boundary
- Visually hidden `<h1>` heading for screen reader navigation

```
┌─────────────────────────────────────────────────────────────┐
│ Layout (sidebar nav + header — already exists)              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ AIScheduleView  [data-testid="ai-schedule-page"]        │ │
│ │ CSS Grid: 1fr 380px                                     │ │
│ │ ┌───────────────────────────┐ ┌───────────────────────┐ │ │
│ │ │ <main>                    │ │ <aside>               │ │ │
│ │ │                           │ │                       │ │ │
│ │ │ ScheduleOverviewEnhanced  │ │ SchedulingChat        │ │ │
│ │ │ (with CapacityHeatMap)    │ │ (persistent sidebar)  │ │ │
│ │ │                           │ │                       │ │ │
│ │ │ ─────────────────────     │ │                       │ │ │
│ │ │                           │ │                       │ │ │
│ │ │ AlertsPanel               │ │                       │ │ │
│ │ │ (date-filtered)           │ │                       │ │ │
│ │ │                           │ │                       │ │ │
│ │ └───────────────────────────┘ └───────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:**
- `AIScheduleView` holds `scheduleDate` state (defaults to today's ISO date)
- `scheduleDate` is passed to `ScheduleOverviewEnhanced` (for grid data) and `AlertsPanel` (for date filtering)
- `onViewModeChange` from `ScheduleOverviewEnhanced` updates `scheduleDate`
- `onPublishSchedule` from `SchedulingChat` triggers `queryClient.invalidateQueries` to refresh both overview and alerts

**Error boundary:** `SchedulingChat` errors do not crash the overview/alerts. The existing `ErrorBoundary` class component from `@/shared/components/ErrorBoundary` wraps the chat sidebar with a custom fallback prop so the main content remains functional.

#### Resource Mobile Page (`/schedule/mobile`)

New route. Composes `ResourceScheduleView` and `ResourceMobileChat` in a mobile-first stacked layout for field technicians.

```
┌───────────────────────────┐
│ Layout (header)           │
│ ┌───────────────────────┐ │
│ │ ResourceMobileView    │ │
│ │                       │ │
│ │ ResourceScheduleView  │ │
│ │ (daily route cards)   │ │
│ │                       │ │
│ │ ─────────────────     │ │
│ │                       │ │
│ │ ResourceMobileChat    │ │
│ │ (field assistant)     │ │
│ │                       │ │
│ └───────────────────────┘ │
└───────────────────────────┘
```

Both components fetch their own data via internal TanStack Query hooks.

#### New/Modified Files for Page Composition

| File | Action | Purpose |
|------|--------|---------|
| `features/schedule/components/AIScheduleView.tsx` | New | Composed admin page view with shared `scheduleDate` state. Imports `ErrorBoundary` from `@/shared/components/ErrorBoundary` for chat isolation. |
| `features/resource-mobile/components/ResourceMobileView.tsx` | New | Composed mobile page view |
| `pages/ScheduleGenerate.tsx` | Modified | Replace `import { ScheduleGenerationPage } from '@/features/schedule'` with `import { AIScheduleView } from '@/features/schedule'` |
| `pages/ScheduleMobile.tsx` | New | Thin page wrapper for `ResourceMobileView` |
| `core/router/index.tsx` | Modified | Add lazy import for `ScheduleMobilePage` and `/schedule/mobile` route after line 204 (existing `schedule/generate` route) |
| `features/schedule/index.ts` | Modified | Add `AIScheduleView` to components export list (currently exports `ScheduleGenerationPage` + 22 other components) |
| `features/ai/index.ts` | New | Create root barrel export — currently only `features/ai/components/index.ts` exists. Must export `SchedulingChat` and `ResourceMobileChat` for page composition imports. |
| `features/resource-mobile/index.ts` | New | Create root barrel — directory does not exist yet, created in phase 12. Export `ResourceMobileView`. |
| `features/scheduling-alerts/index.ts` | New | Create root barrel — directory does not exist yet, created in phase 10. Export `AlertsPanel`. |

## Data Models

### New Database Tables

#### `scheduling_criteria_config`
Stores the 30 criteria weights and hard/soft classification. Enables runtime tuning without code changes.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| criterion_number | Integer | 1–30 |
| criterion_name | String(100) | Human-readable name |
| criterion_group | String(50) | geographic, resource, customer_job, capacity_demand, business_rules, predictive |
| weight | Integer | 0–100, relative importance |
| is_hard_constraint | Boolean | True = must satisfy, False = optimize |
| is_enabled | Boolean | Feature flag per criterion |
| config_json | JSONB | Criterion-specific configuration (thresholds, zone definitions, etc.) |
| created_at | DateTime | Record creation |
| updated_at | DateTime | Last update |

#### `scheduling_alerts`
Stores AI-generated alerts and suggestions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| alert_type | String(50) | double_booking, skill_mismatch, sla_risk, resource_behind, severe_weather, route_swap, underutilized, customer_preference, overtime_avoidable, high_revenue |
| severity | String(20) | critical (red alert), suggestion (green) |
| title | String(200) | Display title |
| description | Text | Detailed description |
| affected_job_ids | JSONB | List of affected job UUIDs |
| affected_staff_ids | JSONB | List of affected staff UUIDs |
| criteria_triggered | JSONB | List of criterion numbers that triggered this alert |
| resolution_options | JSONB | Available resolution actions with parameters |
| status | String(20) | active, resolved, dismissed, expired |
| resolved_by | UUID (FK → staff.id) | Admin who resolved |
| resolved_action | String(50) | Which resolution was chosen |
| resolved_at | DateTime | When resolved |
| schedule_date | Date | Which schedule date this alert pertains to |
| created_at | DateTime | Record creation |
| updated_at | DateTime | Last update |

#### `change_requests`
Stores Resource-initiated change requests routed to Admin.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| resource_id | UUID (FK → staff.id) | Resource who initiated |
| request_type | String(50) | delay_report, followup_job, access_issue, nearby_pickup, resequence, crew_assist, parts_log, upgrade_quote |
| details | JSONB | Request-specific details (field notes, parts list, etc.) |
| affected_job_id | UUID (FK → jobs.id) | Primary job affected |
| recommended_action | Text | AI's recommended resolution |
| status | String(20) | pending, approved, denied, expired |
| admin_id | UUID (FK → staff.id) | Admin who acted |
| admin_notes | Text | Admin's notes on decision |
| resolved_at | DateTime | When resolved |
| created_at | DateTime | Record creation |
| updated_at | DateTime | Last update |

#### `scheduling_chat_sessions`
Stores AI chat session context for multi-turn conversations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID (FK → staff.id) | User in the session |
| user_role | String(20) | admin, resource |
| messages | JSONB | Conversation history (role, content, tool_calls) |
| context | JSONB | Session context (current schedule date, active jobs, etc.) |
| is_active | Boolean | Whether session is still active |
| created_at | DateTime | Session start |
| updated_at | DateTime | Last message |

#### `resource_truck_inventory`
Tracks parts inventory per resource's truck for field consumption tracking.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| staff_id | UUID (FK → staff.id) | Resource whose truck |
| part_name | String(100) | Part name |
| quantity | Integer | Current stock |
| reorder_threshold | Integer | Minimum before alert |
| last_restocked | DateTime | Last restock date |
| created_at | DateTime | Record creation |
| updated_at | DateTime | Last update |

#### `service_zones`
Configurable geographic service zones for criterion #3.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | String(100) | Zone name (North, South, etc.) |
| boundary_type | String(20) | polygon, zip_group, radius |
| boundary_data | JSONB | Polygon coordinates, ZIP codes, or center+radius |
| assigned_staff_ids | JSONB | Default staff assigned to this zone |
| is_active | Boolean | Whether zone is active |
| created_at | DateTime | Record creation |
| updated_at | DateTime | Last update |

### Extended Existing Models

#### Job (additions)
- `weather_sensitive: bool` — Already exists. Used by criterion #26.
- `sla_deadline: DateTime | None` — New. Hard deadline for SLA compliance (criterion #23).
- `compliance_deadline: DateTime | None` — New. Regulatory deadline (criterion #21).
- `job_phase: int | None` — New. Phase number for multi-phase projects (criterion #30).
- `depends_on_job_id: UUID | None` — New. FK to prerequisite job (criterion #30).
- `is_outdoor: bool` — New. Whether job is outdoor (criterion #26 weather filtering).
- `predicted_complexity: float | None` — New. ML-predicted complexity score (criterion #27).
- `revenue_per_hour: Decimal | None` — New. Calculated revenue/hour including drive time (criterion #22).

#### Staff (additions)
- `performance_score: float | None` — New. Aggregate performance metric (criterion #10).
- `callback_rate: float | None` — New. Historical callback rate (criterion #10).
- `avg_satisfaction: float | None` — New. Average customer satisfaction score (criterion #10).
- `service_zone_id: UUID | None` — New. FK to assigned service zone (criterion #3).
- `overtime_threshold_minutes: int | None` — New. Per-resource overtime limit (criterion #24).

#### Customer (additions)
- `clv_score: Decimal | None` — New. Customer Lifetime Value score (criterion #14).
- `preferred_resource_id: UUID | None` — New. FK to preferred staff member (criterion #15).
- `time_window_preference: String | None` — New. AM/PM/specific preference (criterion #11).
- `time_window_is_hard: bool` — New. Whether time preference is a hard constraint (criterion #11).

#### Appointment (additions)
- `ai_explanation: Text | None` — New. AI-generated explanation for this assignment.
- `criteria_scores: JSONB | None` — New. Per-criterion scores for this assignment.

### Pydantic Schemas (Key Request/Response)

```python
# Criteria evaluation
class CriteriaScore(BaseModel):
    criterion_number: int
    criterion_name: str
    score: float  # 0-100
    weight: int
    is_hard: bool
    is_satisfied: bool  # For hard constraints
    explanation: str

class ScheduleEvaluation(BaseModel):
    schedule_date: date
    total_score: float
    hard_violations: int
    criteria_scores: list[CriteriaScore]
    alerts: list[AlertCandidate]

# Chat
class ChatRequest(BaseModel):
    message: str
    session_id: UUID | None = None

class ChatResponse(BaseModel):
    response: str
    schedule_changes: list[ScheduleChange] | None = None
    clarifying_questions: list[str] | None = None
    change_request_id: UUID | None = None  # For Resource escalations

# Alerts
class SchedulingAlertResponse(BaseModel):
    id: UUID
    alert_type: str
    severity: str
    title: str
    description: str
    resolution_options: list[ResolutionOption]
    created_at: datetime

class ResolutionOption(BaseModel):
    action: str
    label: str
    description: str
    parameters: dict[str, Any]

class ResolveAlertRequest(BaseModel):
    action: str
    parameters: dict[str, Any] | None = None
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Hard Constraint Invariant

*For any* generated schedule and *for any* job-to-resource assignment within that schedule, the following invariants SHALL all hold simultaneously:
- The assigned resource holds every skill tag and certification required by the job type
- The assigned resource's truck equipment includes every item in the job's required equipment checklist
- The job's time slot falls entirely within the resource's availability window (shift start/end, excluding PTO and training blocks)
- No two jobs assigned to the same resource have overlapping time windows
- The job's time slot falls within any hard customer time-window preference
- If the job has a compliance deadline, the scheduled date is on or before that deadline
- If the job has an SLA deadline, the scheduled date is on or before that SLA deadline
- If the job depends on another job (cross-job dependency), the dependent job is scheduled after the prerequisite job completes

**Validates: Requirements 4.1, 4.2, 4.3, 5.1, 7.1, 7.3, 8.5, 26.3**

### Property 2: Alert Detection Accuracy

*For any* schedule containing a constraint violation (time overlap, skill mismatch, SLA deadline past, or outdoor jobs on severe weather days), the `AlertEngine` SHALL detect and generate a corresponding alert. Conversely, *for any* alert generated by the `AlertEngine`, there SHALL exist a corresponding actual violation in the schedule data — no false positive alerts.

**Validates: Requirements 11.1, 11.2, 11.3, 11.5, 26.3**

### Property 3: Proximity Scoring Monotonicity

*For any* job and *for any* two resources A and B where resource A is closer to the job site than resource B (by haversine distance), the proximity criterion score for assigning the job to resource A SHALL be greater than or equal to the score for assigning it to resource B.

**Validates: Requirements 3.1**

### Property 4: Intra-Route Drive Time Minimization

*For any* resource's daily route with 3 or more jobs, the route sequence produced by the solver SHALL have a total cumulative drive time less than or equal to the worst-case (reverse-sorted) ordering of the same jobs.

**Validates: Requirements 3.2**

### Property 5: Zone Boundary Preference

*For any* job and *for any* two resources where one is assigned to the job's service zone and the other is not, the in-zone resource SHALL receive a higher zone criterion score, assuming equal distance.

**Validates: Requirements 3.3**

### Property 6: Workload Balance

*For any* generated schedule with 2 or more resources, the standard deviation of assigned job-hours across resources SHALL be less than or equal to the standard deviation that would result from assigning all jobs to a single resource. In other words, the solver should distribute work more evenly than the degenerate case.

**Validates: Requirements 4.4**

### Property 7: Priority and CLV Ordering

*For any* two jobs competing for the same time slot where one has a higher priority tier (emergency > VIP > standard > flexible), the higher-priority job SHALL be assigned to the slot. *For any* two jobs of equal priority competing for the same slot, the job with the higher customer CLV score SHALL be preferred.

**Validates: Requirements 5.3, 5.4**

### Property 8: Capacity Utilization Calculation

*For any* schedule and *for any* resource on that schedule, the computed capacity utilization percentage SHALL equal (total assigned job minutes + total drive minutes) / (total available minutes) × 100, within a 0.1% tolerance.

**Validates: Requirements 6.1**

### Property 9: Backlog Pressure Monotonicity

*For any* two backlog states A and B where A has more unscheduled jobs or older average job age than B, the backlog pressure score for state A SHALL be greater than or equal to the score for state B.

**Validates: Requirements 6.5**

### Property 10: Revenue Per Resource-Hour Calculation

*For any* job-resource assignment, the computed revenue per resource-hour SHALL equal `job_revenue / ((job_duration_minutes + drive_time_minutes) / 60)`, within a $0.01 tolerance.

**Validates: Requirements 7.2**

### Property 11: Overtime Cost-Benefit

*For any* resource whose schedule would extend into overtime, the overtime criterion scorer SHALL penalize the assignment UNLESS the job's revenue exceeds the overtime cost (overtime_hours × overtime_rate). The penalty/reward sign SHALL be correct for all generated inputs.

**Validates: Requirements 7.4**

### Property 12: Weather Impact on Outdoor Jobs

*For any* outdoor job (`is_outdoor=True`) scheduled on a day with severe weather forecast (rain, freeze), the weather criterion scorer SHALL assign a penalty score. *For any* indoor job on the same day, the weather scorer SHALL assign a neutral or positive score.

**Validates: Requirements 8.1, 23.7**

### Property 13: Dependency Chain Ordering

*For any* job B that depends on job A (`depends_on_job_id` is set), if both are scheduled, job B's start time SHALL be after job A's completion time. If job A is not yet scheduled, job B SHALL not be scheduled.

**Validates: Requirements 8.5**

### Property 14: Route Swap Improvement Guarantee

*For any* route swap suggestion generated by the `AlertEngine`, the proposed swap SHALL result in a strictly lower combined drive time for the two affected resources compared to the current assignment.

**Validates: Requirements 12.1**

### Property 15: Pre-Job Checklist Completeness

*For any* job and resource, the generated pre-job checklist SHALL contain all of the following fields: job type, customer name, customer address, required equipment list, known system issues (if any), gate code (if any), special instructions (if any), and estimated duration.

**Validates: Requirements 15.2**

### Property 16: Nearby Work Radius and Skill Filtering

*For any* resource location and *for any* job returned by the nearby work finder, the job SHALL be within a 15-minute drive radius of the resource's current location AND the resource SHALL hold all required skills AND the resource's truck SHALL carry all required equipment.

**Validates: Requirements 15.5**

### Property 17: Parts Low-Stock Threshold Alert

*For any* parts logging operation that decrements a resource's truck inventory below the reorder threshold, the system SHALL generate a low-stock suggestion. *For any* parts logging that keeps inventory at or above the threshold, no low-stock suggestion SHALL be generated.

**Validates: Requirements 15.8**

### Property 18: 30-Criteria Evaluation Completeness

*For any* schedule evaluation operation, the returned `ScheduleEvaluation` SHALL contain exactly 30 `CriteriaScore` entries, one for each criterion number 1 through 30, with no duplicates and no missing criteria.

**Validates: Requirements 23.1**

### Property 19: PII Protection in AI Outputs

*For any* AI prompt sent to the LLM and *for any* log entry produced by scheduling services, the output SHALL NOT contain raw customer phone numbers, email addresses, or full street addresses. Customer references SHALL use customer ID or anonymized identifiers.

**Validates: Requirements 24.1**

### Property 20: Audit Trail Completeness

*For any* AI chat interaction (admin or resource), the system SHALL create an audit log entry containing the user ID, user role, message timestamp, parsed intent, and response summary. The count of audit entries SHALL equal the count of processed chat messages.

**Validates: Requirements 24.3**

### Property 21: Resource Chat Routing Completeness

*For any* message from a Resource user, the `SchedulingChatService` SHALL produce exactly one of: (a) a direct response with no escalation, or (b) a `ChangeRequest` record persisted to the database for Admin approval. No message SHALL produce both or neither.

**Validates: Requirements 1.9**

### Property 22: Constraint Parsing Round-Trip

*For any* natural language scheduling constraint that is successfully parsed into structured parameters, converting those structured parameters back into a natural language description and re-parsing SHALL produce equivalent structured parameters.

**Validates: Requirements 26.3**

### Property 23: Admin Page Composition Structure

*For any* render of `AIScheduleView`, the resulting DOM SHALL contain:
- A root element with `data-testid="ai-schedule-page"`
- A `<main>` landmark element containing both `[data-testid="schedule-overview-enhanced"]` and `[data-testid="alerts-panel"]`, with the alerts panel appearing after the overview in document order
- An `<aside>` landmark element containing `[data-testid="scheduling-chat"]`
- A visually hidden `<h1>` heading element for screen reader navigation

**Validates: Requirements 36.1, 36.2, 36.3, 41.1, 41.3, 41.4**

### Property 24: Shared Schedule Date Propagation

*For any* ISO date string set as the `scheduleDate` state in `AIScheduleView`, both the `ScheduleOverviewEnhanced` component and the `AlertsPanel` component SHALL receive that same date value as a prop, ensuring date-synchronized display.

**Validates: Requirements 36.6, 40.2**

### Property 25: Date Context Update on View Change

*For any* view mode change triggered in `ScheduleOverviewEnhanced` (day, week, or month), the `AIScheduleView` SHALL update its `scheduleDate` state, and the updated date SHALL propagate to the `AlertsPanel` component.

**Validates: Requirements 40.3**

### Property 26: Mobile Page Composition Structure

*For any* render of `ResourceMobileView`, the resulting DOM SHALL contain:
- A root element with `data-testid="resource-mobile-page"`
- `[data-testid="resource-schedule-view"]` appearing before `[data-testid="resource-mobile-chat"]` in document order (vertically stacked)

**Validates: Requirements 38.1, 38.2, 41.2**

### Property 27: Chat Error Isolation

*For any* error thrown by the `SchedulingChat` component, the `AIScheduleView` SHALL continue rendering both `[data-testid="schedule-overview-enhanced"]` and `[data-testid="alerts-panel"]` without disruption. The error SHALL be contained within the `<aside>` boundary.

**Validates: Requirements 40.5**

## Error Handling

### External Service Failures

| Service | Failure Mode | Fallback Behavior |
|---------|-------------|-------------------|
| OpenAI API | Unavailable / timeout / rate limit | Fall back to existing `ScheduleSolverService` without AI-enhanced features. Chat returns "AI assistant temporarily unavailable, schedule generated using standard optimization." |
| Google Maps API | Unavailable / quota exceeded | Fall back to haversine distance with 1.4x road factor (existing `haversine_travel_minutes`). Log degradation. |
| Weather API | Unavailable / stale data | Skip weather criterion (#26). Log warning. Schedule without weather awareness. |
| Redis | Unavailable | Bypass cache, query database directly. Degraded performance but functional. |

### Data Quality Errors

| Scenario | Handling |
|----------|---------|
| Job missing geocoded address | Exclude from geographic criteria (1–5). Log warning. Still schedulable by other criteria. |
| Resource missing certifications data | Treat as having no certifications. Skill match criterion (#6) will prevent assignment to jobs requiring certs. |
| Customer missing CLV score | Default CLV to 0 (neutral). CLV criterion (#14) has no effect on tie-breaking. |
| Missing availability data for resource | Treat as unavailable. Resource excluded from scheduling for that date. |
| Incomplete criteria config | Use default weights. Log which criteria are using defaults. |

### Chat Error Handling

| Scenario | Handling |
|----------|---------|
| LLM returns unparseable response | Retry once with simplified prompt. If still fails, return "I couldn't process that request. Could you rephrase?" |
| Tool function raises exception | Log error with full context. Return user-friendly message: "I encountered an issue while [action]. Please try again or contact support." |
| Rate limit exceeded | Return "You've reached the chat limit. Please wait [N] minutes before trying again." |
| Off-topic message | Return guardrail response: "I can only help with scheduling, job management, and field operations. How can I help with your schedule?" |

### Alert Engine Error Handling

| Scenario | Handling |
|----------|---------|
| Alert scan fails mid-execution | Log error. Partial alerts already generated are kept. Next scan will re-detect. |
| Duplicate alert detected | Deduplicate by (alert_type, affected_job_ids, schedule_date). Skip creation if active duplicate exists. |
| Resolution action fails | Log error. Alert remains active. Admin can retry or choose different resolution. |

## Testing Strategy

### Property-Based Testing (PBT)

**Library**: Hypothesis (Python) — already in use in the project (`.hypothesis/` directory exists).

**Configuration**: Minimum 100 iterations per property test. Each test tagged with:
```python
# Feature: ai-scheduling-system, Property {N}: {property_text}
```

**Property tests** validate the 27 correctness properties defined above (Properties 1–22 are backend Hypothesis tests; Properties 23–27 are frontend fast-check tests covering page composition, date propagation, and chat error isolation). Each property maps to a single test that generates random inputs (jobs, staff, schedules, constraints, ISO dates, errors) and verifies the property holds for all generated cases.

Key generators needed:
- `st_schedule_job()` — random `ScheduleJob` with valid fields
- `st_schedule_staff()` — random `ScheduleStaff` with valid certifications, equipment, availability
- `st_schedule_solution()` — random valid schedule with assignments
- `st_criteria_config()` — random criteria weights and thresholds
- `st_weather_forecast()` — random weather data
- `st_customer_profile()` — random customer with CLV, preferences, relationship history

### Unit Tests

Located in `src/grins_platform/tests/unit/test_pbt_ai_scheduling.py` and `src/grins_platform/tests/unit/test_ai_scheduling.py`.

Unit tests cover:
- Each of the 30 criteria scorers individually with mocked data
- Alert detection logic for all 5 alert types and 5 suggestion types
- ChangeRequest packaging for all 10 Resource chat interaction types
- CriteriaEvaluator composite scoring
- PreJobGenerator checklist generation
- Revenue/hour calculation
- Capacity utilization calculation
- Backlog pressure scoring

All unit tests mock external dependencies (database, OpenAI, Google Maps, Redis).

### Functional Tests

Located in `src/grins_platform/tests/functional/test_ai_scheduling_functional.py`.

Functional tests use a real PostgreSQL test database and validate:
- Schedule building via AI Chat (command → clarifying questions → schedule generated)
- Emergency job insertion end-to-end
- Alert resolution workflows (detect → display → one-click resolve)
- Suggestion acceptance workflows
- Resource delay reporting → ETA recalculation → admin alert
- Pre-job requirements retrieval
- Follow-up job request → ChangeRequest → admin approval
- Parts logging → inventory decrement → low-stock alert
- Batch scheduling for multi-week campaigns

### Integration Tests

Located in `src/grins_platform/tests/integration/test_ai_scheduling_integration.py`.

Integration tests validate:
- Google Maps API integration with fallback
- OpenAI API integration with graceful degradation
- Cross-component data flows (Customer Intake → Scheduling, Scheduling → Billing, etc.)
- API endpoint behavior for all new routes
- Authentication and authorization (role-based access)
- Rate limiting on AI endpoints

### E2E Browser Tests

Located in `scripts/e2e/test-ai-scheduling.sh`.

E2E tests use `agent-browser` to validate:
- Schedule Overview displays correctly with capacity heat map
- Alerts Panel renders alerts (red) and suggestions (green) with correct actions
- AI Chat accepts commands and displays responses
- Resource mobile view displays schedule, alerts, and pre-job info
- Responsive behavior at mobile (375×812), tablet (768×1024), and desktop (1440×900)

### Dual Testing Approach

- **Unit tests** (with PBT): Verify correctness properties, individual criteria scorers, and business logic in isolation. PBT handles comprehensive input coverage; unit tests handle specific examples and edge cases.
- **Functional + Integration + E2E**: Verify complete workflows, cross-component interactions, and visual rendering.

Both approaches are complementary. Unit/PBT tests catch logic bugs early with fast feedback. Functional/integration/E2E tests catch wiring and rendering issues in realistic environments.
