# Design Document: Schedule AI Updates (Phase 7)

## Overview

This document provides the technical design for the Schedule AI Updates feature of Grin's Irrigation Platform. The feature removes the broken AI Generation tab, keeps the working OR-Tools optimization, and adds practical AI features that enhance the scheduling workflow with explanations, suggestions, and natural language interaction.

**Key Principle:** Use AI for what it's good at (explaining decisions, understanding context, parsing natural language) while keeping algorithms for what they're good at (route optimization, constraint satisfaction, travel time calculation).

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + TypeScript)                      │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────┐│
│  │ScheduleGeneration   │ │ScheduleExplanation │ │ NaturalLanguage         ││
│  │Page (simplified)    │ │Modal               │ │ ConstraintsInput        ││
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────┘│
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────┐│
│  │UnassignedJob        │ │SchedulingHelp      │ │ JobsReadyToSchedule     ││
│  │ExplanationCard      │ │Assistant           │ │ Preview                 ││
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ JobForm (with SearchableCustomerDropdown)                               ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           API Layer (FastAPI)                                │
│  ┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────────┐│
│  │/schedule/explain    │ │/schedule/explain-   │ │/schedule/parse-         ││
│  │                     │ │unassigned           │ │constraints              ││
│  └─────────────────────┘ └─────────────────────┘ └─────────────────────────┘│
│  ┌─────────────────────┐ ┌─────────────────────────────────────────────────┐│
│  │/ai/chat (existing)  │ │/jobs/ready-to-schedule                          ││
│  └─────────────────────┘ └─────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           Service Layer                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    ScheduleExplanationService                            ││
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐││
│  │  │ScheduleAnalyzer │ │UnassignedJob    │ │ ConstraintParser            │││
│  │  │                 │ │Analyzer         │ │                             │││
│  │  └─────────────────┘ └─────────────────┘ └─────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ScheduleGenerationService (EXISTING - OR-Tools, NO CHANGES)             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           External Services                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ Claude API (via existing AIAgentService)                                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           Data Layer (PostgreSQL)                            │
│  ┌─────────────────────┐ ┌─────────────────────────────────────────────────┐│
│  │ai_audit_log         │ │ saved_constraints (optional future)             ││
│  │(existing)           │ │                                                 ││
│  └─────────────────────┘ └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Relationships

```mermaid
graph TD
    subgraph "Frontend Components"
        SchedulePage[ScheduleGenerationPage]
        ExplainModal[ScheduleExplanationModal]
        UnassignedCard[UnassignedJobExplanationCard]
        ConstraintsInput[NaturalLanguageConstraintsInput]
        HelpAssistant[SchedulingHelpAssistant]
        JobsPreview[JobsReadyToSchedulePreview]
        JobForm[JobForm]
        CustomerDropdown[SearchableCustomerDropdown]
    end

    subgraph "API Layer"
        ExplainAPI[/schedule/explain]
        UnassignedAPI[/schedule/explain-unassigned]
        ParseAPI[/schedule/parse-constraints]
        ChatAPI[/ai/chat - existing]
        ReadyJobsAPI[/jobs/ready-to-schedule]
        CustomersAPI[/customers - existing]
    end

    subgraph "Service Layer"
        ExplainSvc[ScheduleExplanationService]
        ConstraintSvc[ConstraintParserService]
        AgentSvc[AIAgentService - existing]
        ScheduleSvc[ScheduleGenerationService - existing]
    end

    subgraph "External"
        Claude[Claude API]
    end

    SchedulePage --> ExplainModal
    SchedulePage --> UnassignedCard
    SchedulePage --> ConstraintsInput
    SchedulePage --> HelpAssistant
    SchedulePage --> JobsPreview
    JobForm --> CustomerDropdown

    ExplainModal --> ExplainAPI
    UnassignedCard --> UnassignedAPI
    ConstraintsInput --> ParseAPI
    HelpAssistant --> ChatAPI
    JobsPreview --> ReadyJobsAPI
    CustomerDropdown --> CustomersAPI

    ExplainAPI --> ExplainSvc
    UnassignedAPI --> ExplainSvc
    ParseAPI --> ConstraintSvc
    ChatAPI --> AgentSvc

    ExplainSvc --> AgentSvc
    ConstraintSvc --> AgentSvc
    AgentSvc --> Claude
```

## Components and Interfaces

### Backend Directory Structure

```
src/grins_platform/
├── services/
│   └── ai/
│       ├── __init__.py                    # EXISTING
│       ├── agent.py                       # EXISTING - no changes
│       │
│       └── schedule_explanation/          # NEW DIRECTORY
│           ├── __init__.py
│           ├── explanation_service.py     # Schedule explanation service
│           ├── unassigned_analyzer.py     # Unassigned job analysis
│           └── constraint_parser.py       # Natural language constraint parsing
│
├── api/v1/
│   ├── schedule.py                        # MODIFY - add explanation endpoints
│   └── jobs.py                            # MODIFY - add ready-to-schedule endpoint
│
└── schemas/
    └── schedule_explanation.py            # NEW - explanation schemas
```

### Frontend Directory Structure

```
frontend/src/features/
├── schedule/
│   ├── components/
│   │   ├── ScheduleGenerationPage.tsx     # MODIFY - remove AI tab, add new features
│   │   ├── ScheduleResults.tsx            # EXISTING - add explain button
│   │   │
│   │   └── ai/                            # NEW DIRECTORY
│   │       ├── index.ts                   # Barrel exports
│   │       ├── ScheduleExplanationModal.tsx
│   │       ├── UnassignedJobExplanationCard.tsx
│   │       ├── NaturalLanguageConstraintsInput.tsx
│   │       ├── SchedulingHelpAssistant.tsx
│   │       └── JobsReadyToSchedulePreview.tsx
│   │
│   ├── hooks/
│   │   ├── useScheduleGeneration.ts       # EXISTING
│   │   ├── useScheduleExplanation.ts      # NEW
│   │   ├── useConstraintParser.ts         # NEW
│   │   └── useJobsReadyToSchedule.ts      # NEW
│   │
│   └── types/
│       └── explanation.ts                 # NEW - explanation types
│
└── jobs/
    └── components/
        ├── JobForm.tsx                    # MODIFY - add customer dropdown
        └── SearchableCustomerDropdown.tsx # NEW
```

## Pydantic Schemas

### Schedule Explanation Schemas

**File: `src/grins_platform/schemas/schedule_explanation.py`** (NEW)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date

# Schedule Explanation
class ScheduleExplanationRequest(BaseModel):
    """Request for schedule explanation."""
    schedule_date: date
    staff_assignments: List["StaffAssignmentSummary"]
    unassigned_job_ids: List[UUID] = Field(default_factory=list)

class StaffAssignmentSummary(BaseModel):
    """Summary of staff assignment for explanation."""
    staff_id: UUID
    staff_name: str
    job_count: int
    cities: List[str]
    job_types: List[str]
    has_compressor_jobs: bool = False
    total_travel_minutes: int

class ScheduleExplanationResponse(BaseModel):
    """Response with schedule explanation."""
    success: bool
    explanation: str
    highlights: List[str] = Field(default_factory=list)
    audit_id: Optional[UUID] = None
    error_message: Optional[str] = None

# Unassigned Job Explanation
class UnassignedJobExplanationRequest(BaseModel):
    """Request for unassigned job explanation."""
    job_id: UUID
    job_type: str
    customer_city: str
    requires_equipment: List[str] = Field(default_factory=list)
    schedule_date: date
    constraint_violations: List[str] = Field(default_factory=list)

class UnassignedJobExplanationResponse(BaseModel):
    """Response with unassigned job explanation."""
    success: bool
    job_id: UUID
    reason: str
    suggestions: List[str] = Field(default_factory=list)
    alternative_dates: List[date] = Field(default_factory=list)
    audit_id: Optional[UUID] = None
    error_message: Optional[str] = None

# Natural Language Constraints
class ParseConstraintsRequest(BaseModel):
    """Request to parse natural language constraints."""
    constraints_text: str = Field(..., min_length=1, max_length=1000)

class ParsedConstraint(BaseModel):
    """A single parsed constraint."""
    original_text: str
    constraint_type: str  # 'staff_time', 'job_grouping', 'staff_restriction', 'geographic'
    parameters: dict
    confidence: float = Field(ge=0.0, le=1.0)
    is_valid: bool = True
    error_message: Optional[str] = None

class ParseConstraintsResponse(BaseModel):
    """Response with parsed constraints."""
    success: bool
    constraints: List[ParsedConstraint] = Field(default_factory=list)
    unparseable_text: Optional[str] = None
    audit_id: Optional[UUID] = None

# Jobs Ready to Schedule
class JobReadyToSchedule(BaseModel):
    """A job ready to be scheduled."""
    job_id: UUID
    customer_name: str
    customer_city: str
    job_type: str
    priority_level: int = 0
    estimated_duration_minutes: int
    requires_equipment: List[str] = Field(default_factory=list)
    created_at: str

class JobsReadyToScheduleResponse(BaseModel):
    """Response with jobs ready to schedule."""
    jobs: List[JobReadyToSchedule] = Field(default_factory=list)
    total: int = 0
    by_city: dict = Field(default_factory=dict)
    by_job_type: dict = Field(default_factory=dict)
```

## API Endpoints

### New Schedule Explanation Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/schedule/explain` | Get AI explanation of schedule | ScheduleExplanationRequest | ScheduleExplanationResponse |
| POST | `/api/v1/schedule/explain-unassigned` | Get explanation for unassigned job | UnassignedJobExplanationRequest | UnassignedJobExplanationResponse |
| POST | `/api/v1/schedule/parse-constraints` | Parse natural language constraints | ParseConstraintsRequest | ParseConstraintsResponse |
| GET | `/api/v1/jobs/ready-to-schedule` | Get jobs ready to schedule | Query params (date, status) | JobsReadyToScheduleResponse |

### Existing Endpoints (No Changes)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/chat` | AI chat for scheduling help |
| GET | `/api/v1/customers` | Customer list for dropdown |
| POST | `/api/v1/schedule/generate` | Generate schedule (OR-Tools) |

## Service Layer Design

### ScheduleExplanationService

**File: `src/grins_platform/services/ai/schedule_explanation/explanation_service.py`**

```python
from grins_platform.logging import LoggerMixin
from grins_platform.services.ai.agent import AIAgentService

class ScheduleExplanationService(LoggerMixin):
    """Service for generating AI explanations of schedules."""
    
    DOMAIN = "ai"
    
    def __init__(self, ai_agent: AIAgentService):
        self.ai_agent = ai_agent
    
    async def explain_schedule(
        self, 
        request: ScheduleExplanationRequest
    ) -> ScheduleExplanationResponse:
        """Generate natural language explanation of schedule decisions."""
        self.log_started("explain_schedule", date=str(request.schedule_date))
        
        try:
            # Build context without PII (no full addresses, no phone numbers)
            context = self._build_explanation_context(request)
            
            # Generate explanation via AI
            explanation = await self.ai_agent.generate_explanation(
                prompt=SCHEDULE_EXPLANATION_PROMPT,
                context=context
            )
            
            # Extract highlights
            highlights = self._extract_highlights(explanation)
            
            # Log to audit
            audit_id = await self._log_audit(request, explanation)
            
            self.log_completed("explain_schedule")
            
            return ScheduleExplanationResponse(
                success=True,
                explanation=explanation,
                highlights=highlights,
                audit_id=audit_id
            )
            
        except Exception as e:
            self.log_failed("explain_schedule", error=e)
            return ScheduleExplanationResponse(
                success=False,
                explanation="",
                error_message="Unable to generate explanation. Please try again."
            )
    
    def _build_explanation_context(self, request: ScheduleExplanationRequest) -> dict:
        """Build context for AI without PII."""
        return {
            "date": str(request.schedule_date),
            "staff_assignments": [
                {
                    "staff_name": a.staff_name,
                    "job_count": a.job_count,
                    "cities": a.cities,
                    "job_types": a.job_types,
                    "has_compressor": a.has_compressor_jobs,
                    "travel_minutes": a.total_travel_minutes
                }
                for a in request.staff_assignments
            ],
            "unassigned_count": len(request.unassigned_job_ids)
        }
```

### ConstraintParserService

**File: `src/grins_platform/services/ai/schedule_explanation/constraint_parser.py`**

```python
class ConstraintParserService(LoggerMixin):
    """Service for parsing natural language scheduling constraints."""
    
    DOMAIN = "ai"
    
    SUPPORTED_CONSTRAINT_TYPES = [
        "staff_time",        # "Don't schedule Viktor before 10am"
        "job_grouping",      # "Keep Johnson and Smith jobs together"
        "staff_restriction", # "Vas shouldn't do lake pump jobs"
        "geographic",        # "Finish Eden Prairie by noon"
    ]
    
    async def parse_constraints(
        self, 
        request: ParseConstraintsRequest
    ) -> ParseConstraintsResponse:
        """Parse natural language constraints into structured format."""
        self.log_started("parse_constraints", text_length=len(request.constraints_text))
        
        try:
            # Use AI to parse constraints
            parsed = await self.ai_agent.parse_constraints(
                text=request.constraints_text,
                supported_types=self.SUPPORTED_CONSTRAINT_TYPES
            )
            
            # Validate parsed constraints
            validated = self._validate_constraints(parsed)
            
            self.log_completed("parse_constraints", count=len(validated))
            
            return ParseConstraintsResponse(
                success=True,
                constraints=validated
            )
            
        except Exception as e:
            self.log_failed("parse_constraints", error=e)
            return ParseConstraintsResponse(
                success=False,
                constraints=[],
                unparseable_text=request.constraints_text
            )
```

## Frontend Types

**File: `frontend/src/features/schedule/types/explanation.ts`** (NEW)

```typescript
// Schedule Explanation
export interface ScheduleExplanationRequest {
  schedule_date: string;
  staff_assignments: StaffAssignmentSummary[];
  unassigned_job_ids: string[];
}

export interface StaffAssignmentSummary {
  staff_id: string;
  staff_name: string;
  job_count: number;
  cities: string[];
  job_types: string[];
  has_compressor_jobs: boolean;
  total_travel_minutes: number;
}

export interface ScheduleExplanationResponse {
  success: boolean;
  explanation: string;
  highlights: string[];
  audit_id?: string;
  error_message?: string;
}

// Unassigned Job Explanation
export interface UnassignedJobExplanationRequest {
  job_id: string;
  job_type: string;
  customer_city: string;
  requires_equipment: string[];
  schedule_date: string;
  constraint_violations: string[];
}

export interface UnassignedJobExplanationResponse {
  success: boolean;
  job_id: string;
  reason: string;
  suggestions: string[];
  alternative_dates: string[];
  audit_id?: string;
  error_message?: string;
}

// Natural Language Constraints
export interface ParseConstraintsRequest {
  constraints_text: string;
}

export interface ParsedConstraint {
  original_text: string;
  constraint_type: 'staff_time' | 'job_grouping' | 'staff_restriction' | 'geographic';
  parameters: Record<string, unknown>;
  confidence: number;
  is_valid: boolean;
  error_message?: string;
}

export interface ParseConstraintsResponse {
  success: boolean;
  constraints: ParsedConstraint[];
  unparseable_text?: string;
  audit_id?: string;
}

// Jobs Ready to Schedule
export interface JobReadyToSchedule {
  job_id: string;
  customer_name: string;
  customer_city: string;
  job_type: string;
  priority_level: number;
  estimated_duration_minutes: number;
  requires_equipment: string[];
  created_at: string;
}

export interface JobsReadyToScheduleResponse {
  jobs: JobReadyToSchedule[];
  total: number;
  by_city: Record<string, number>;
  by_job_type: Record<string, number>;
}

// Customer Search (for dropdown)
export interface CustomerSearchResult {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  display_name: string; // "John Doe (612-555-1234)"
}
```

## Data-TestId Conventions

| Component | TestId Pattern |
|-----------|----------------|
| Schedule generation page | `schedule-generation-page` |
| Generate schedule button | `generate-schedule-btn` |
| Explain schedule button | `explain-schedule-btn` |
| Schedule explanation modal | `schedule-explanation-modal` |
| Explanation text | `explanation-text` |
| Explanation highlights | `explanation-highlights` |
| Unassigned jobs section | `unassigned-jobs-section` |
| Unassigned job card | `unassigned-job-{job_id}` |
| Why link | `why-link-{job_id}` |
| Job explanation card | `job-explanation-{job_id}` |
| Suggestion item | `suggestion-{index}` |
| Constraints input | `constraints-input` |
| Parse constraints button | `parse-constraints-btn` |
| Parsed constraint item | `parsed-constraint-{index}` |
| Remove constraint button | `remove-constraint-{index}` |
| Scheduling help panel | `scheduling-help-panel` |
| Help toggle button | `help-toggle-btn` |
| Sample question button | `sample-question-{index}` |
| Help chat input | `help-chat-input` |
| Help chat submit | `help-chat-submit` |
| Jobs preview section | `jobs-preview-section` |
| Job preview item | `job-preview-{job_id}` |
| Exclude job checkbox | `exclude-job-{job_id}` |
| Jobs summary | `jobs-summary` |
| Customer dropdown | `customer-dropdown` |
| Customer search input | `customer-search-input` |
| Customer option | `customer-option-{id}` |
| Loading state | `loading-state` |
| Error state | `error-state` |
| Retry button | `retry-btn` |

## Component Specifications

### ScheduleExplanationModal

Modal that displays AI-generated explanation of the schedule.

```typescript
interface ScheduleExplanationModalProps {
  isOpen: boolean;
  onClose: () => void;
  scheduleDate: string;
  staffAssignments: StaffAssignmentSummary[];
  unassignedJobIds: string[];
}
```

### UnassignedJobExplanationCard

Expandable card showing why a job couldn't be scheduled.

```typescript
interface UnassignedJobExplanationCardProps {
  job: UnassignedJob;
  scheduleDate: string;
  onExplanationLoaded?: (explanation: UnassignedJobExplanationResponse) => void;
}
```

### NaturalLanguageConstraintsInput

Text area for entering scheduling constraints in plain English.

```typescript
interface NaturalLanguageConstraintsInputProps {
  onConstraintsParsed: (constraints: ParsedConstraint[]) => void;
  initialConstraints?: ParsedConstraint[];
}
```

### SchedulingHelpAssistant

Collapsible AI help panel for scheduling questions.

```typescript
interface SchedulingHelpAssistantProps {
  isCollapsed: boolean;
  onToggle: () => void;
}
```

### JobsReadyToSchedulePreview

Preview section showing jobs that will be included in schedule generation.

```typescript
interface JobsReadyToSchedulePreviewProps {
  date: string;
  onExcludedJobsChange: (excludedJobIds: string[]) => void;
}
```

### SearchableCustomerDropdown

Searchable dropdown for selecting customers in JobForm.

```typescript
interface SearchableCustomerDropdownProps {
  value: string | null;
  onChange: (customerId: string | null) => void;
  error?: string;
  disabled?: boolean;
}
```

## AI Prompts

### Schedule Explanation Prompt

```
You are explaining a schedule generated for an irrigation service business.

Given the following schedule summary:
{context}

Explain why jobs were assigned this way. Focus on:
1. Geographic grouping (which cities are grouped together)
2. Equipment requirements (compressor jobs assigned to staff with compressors)
3. Travel time optimization
4. Staff workload balance

Keep the explanation concise (2-3 paragraphs). Use plain language.
Do NOT include any customer names, addresses, or phone numbers.
```

### Unassigned Job Explanation Prompt

```
A job could not be scheduled. Explain why and suggest solutions.

Job details:
- Type: {job_type}
- City: {customer_city}
- Equipment needed: {requires_equipment}
- Date: {schedule_date}
- Constraint violations: {constraint_violations}

Provide:
1. A clear explanation of why this job couldn't be scheduled
2. 2-3 specific, actionable suggestions to resolve the conflict
3. Alternative dates if applicable

Keep the response concise and helpful.
```

### Constraint Parser Prompt

```
Parse the following scheduling constraints into structured format.

Supported constraint types:
- staff_time: Time restrictions for staff (e.g., "Don't schedule Viktor before 10am")
- job_grouping: Keep certain jobs together (e.g., "Keep Johnson and Smith jobs together")
- staff_restriction: Staff-job restrictions (e.g., "Vas shouldn't do lake pump jobs")
- geographic: Location-based constraints (e.g., "Finish Eden Prairie by noon")

User input:
{constraints_text}

For each constraint, extract:
- constraint_type: one of the supported types
- parameters: relevant details (staff_name, time, location, etc.)
- confidence: 0.0-1.0 how confident you are in the parsing

If a constraint cannot be parsed, set is_valid to false with an error_message.
```

## Error Handling

### AI Service Unavailable
- Show graceful error message
- Display retry button
- For unassigned jobs, show basic constraint violation from solver

### Constraint Parsing Failure
- Show which text couldn't be parsed
- Provide examples of valid constraints
- Allow user to edit and retry

### Customer Search Failure
- Show "Unable to load customers" message
- Allow manual UUID entry as fallback

## Correctness Properties

### P1: PII Protection
AI prompts must never contain customer full addresses, phone numbers, or email addresses.

### P2: Explanation Consistency
Schedule explanations must accurately reflect the actual staff assignments and job groupings.

### P3: Constraint Validation
Parsed constraints must be validated against known staff names and job types before being applied.

### P4: Customer Dropdown Accuracy
Selected customer ID must match the displayed customer name in the dropdown.

### P5: Job Preview Accuracy
Jobs shown in preview must match jobs that will be passed to schedule generation.

### P6: Graceful Degradation
All AI features must have fallback behavior when AI service is unavailable.
