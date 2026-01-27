# Design Document: AI Assistant Integration (Phase 6)

## Overview

This document provides the technical design for the AI Assistant Integration feature of Grin's Irrigation Platform. It defines the database schema, API endpoints, service layer architecture, Pydantic AI agent configuration, and implementation patterns that will fulfill the requirements specified in requirements.md. This phase builds on the foundation established in Phases 1-5.

The AI Assistant follows a strict human-in-the-loop principle where AI analyzes data and generates recommendations, but all actions require explicit user approval before execution.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + TypeScript)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ AIQueryChat │ │AISchedule   │ │AICategorize │ │ AICommunicationDrafts   ││
│  │             │ │Generator    │ │             │ │ AIEstimateGenerator     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────────────────────┐ ┌─────────────────────────────────────────┐│
│  │ MorningBriefing             │ │ CommunicationsQueue                     ││
│  └─────────────────────────────┘ └─────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           API Layer (FastAPI)                                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ /ai/chat    │ │/ai/schedule │ │/ai/jobs     │ │ /ai/communication       ││
│  │ (streaming) │ │/generate    │ │/categorize  │ │ /ai/estimate            ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────────────┐│
│  │ /sms/send   │ │/sms/webhook │ │ /weather/forecast                       ││
│  └─────────────┘ └─────────────┘ └─────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           Service Layer                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        AIAgentService                                    ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐││
│  │  │ScheduleTool │ │Categorize   │ │Communication│ │ EstimateTool        │││
│  │  │             │ │Tool         │ │Tool         │ │ QueryTool           │││
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ SMSService  │ │WeatherSvc   │ │RateLimitSvc │ │ AuditService            ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           External Services                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────────────┐│
│  │ OpenAI API  │ │ Twilio SMS  │ │ OpenWeatherMap API                      ││
│  │ (GPT-5-nano)│ │             │ │                                         ││
│  └─────────────┘ └─────────────┘ └─────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│                           Data Layer (PostgreSQL)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ai_audit_log │ │ai_usage     │ │sent_messages│ │ weather_cache           ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Relationships

```mermaid
graph TD
    subgraph "Frontend Components"
        AIChat[AIQueryChat]
        AISchedule[AIScheduleGenerator]
        AICat[AICategorization]
        AIComm[AICommunicationDrafts]
        AIEst[AIEstimateGenerator]
        Brief[MorningBriefing]
        Queue[CommunicationsQueue]
    end

    subgraph "API Layer"
        ChatAPI[/ai/chat]
        ScheduleAPI[/ai/schedule/generate]
        CatAPI[/ai/jobs/categorize]
        CommAPI[/ai/communication/draft]
        EstAPI[/ai/estimate/generate]
        SMSAPI[/sms/send]
        WebhookAPI[/sms/webhook]
    end

    subgraph "Service Layer"
        AgentSvc[AIAgentService]
        SMSSvc[SMSService]
        WeatherSvc[WeatherService]
        RateSvc[RateLimitService]
        AuditSvc[AuditService]
    end

    subgraph "AI Tools"
        SchedTool[SchedulingTool]
        CatTool[CategorizationTool]
        CommTool[CommunicationTool]
        QueryTool[QueryTool]
        EstTool[EstimateTool]
    end

    subgraph "External"
        OpenAI[OpenAI GPT-5-nano]
        Twilio[Twilio SMS]
        Weather[OpenWeatherMap]
    end

    AIChat --> ChatAPI
    AISchedule --> ScheduleAPI
    AICat --> CatAPI
    AIComm --> CommAPI
    AIEst --> EstAPI
    Queue --> SMSAPI

    ChatAPI --> AgentSvc
    ScheduleAPI --> AgentSvc
    CatAPI --> AgentSvc
    CommAPI --> AgentSvc
    EstAPI --> AgentSvc
    SMSAPI --> SMSSvc
    WebhookAPI --> SMSSvc

    AgentSvc --> SchedTool
    AgentSvc --> CatTool
    AgentSvc --> CommTool
    AgentSvc --> QueryTool
    AgentSvc --> EstTool
    AgentSvc --> RateSvc
    AgentSvc --> AuditSvc

    SchedTool --> WeatherSvc
    AgentSvc --> OpenAI
    SMSSvc --> Twilio
    WeatherSvc --> Weather
```

## Components and Interfaces

### Backend Directory Structure

```
src/grins_platform/
├── services/
│   └── ai/
│       ├── __init__.py
│       ├── agent.py                 # Main Pydantic AI agent configuration
│       ├── dependencies.py          # AI service dependencies
│       ├── rate_limiter.py          # Rate limiting service
│       ├── audit.py                 # Audit logging service
│       │
│       ├── tools/                   # AI tool definitions
│       │   ├── __init__.py
│       │   ├── scheduling.py        # Schedule generation tools
│       │   ├── categorization.py    # Job categorization tools
│       │   ├── communication.py     # Message drafting tools
│       │   ├── queries.py           # Business query tools
│       │   └── estimates.py         # Estimate generation tools
│       │
│       ├── prompts/                 # System prompts and templates
│       │   ├── __init__.py
│       │   ├── system.py            # Base system prompts
│       │   ├── scheduling.py        # Scheduling-specific prompts
│       │   ├── categorization.py    # Categorization prompts
│       │   ├── communication.py     # Communication prompts
│       │   └── templates/           # Message templates
│       │       ├── confirmation.txt
│       │       ├── reminder.txt
│       │       └── follow_up.txt
│       │
│       └── context/                 # Context retrieval
│           ├── __init__.py
│           ├── builder.py           # Context builder with token management
│           ├── customers.py         # Customer context builder
│           ├── jobs.py              # Job context builder
│           └── business.py          # Business metrics context
│
├── services/
│   ├── sms_service.py               # Twilio SMS service
│   └── weather_service.py           # OpenWeatherMap service
│
├── api/v1/
│   ├── ai.py                        # AI API endpoints
│   ├── sms.py                       # SMS API endpoints
│   └── weather.py                   # Weather API endpoints
│
├── models/
│   ├── ai_audit_log.py              # Audit log model
│   ├── ai_usage.py                  # Usage tracking model
│   └── sent_message.py              # Sent message model
│
└── schemas/
    ├── ai.py                        # AI request/response schemas
    ├── sms.py                       # SMS schemas
    └── weather.py                   # Weather schemas
```

### Frontend Directory Structure

```
frontend/src/features/
├── ai/                              # AI feature module
│   ├── components/
│   │   ├── AIQueryChat.tsx          # Natural language query chat
│   │   ├── AIScheduleGenerator.tsx  # Schedule generation UI
│   │   ├── AICategorization.tsx     # Job categorization UI
│   │   ├── AICommunicationDrafts.tsx # Communication drafts
│   │   ├── AIEstimateGenerator.tsx  # Estimate generation UI
│   │   ├── MorningBriefing.tsx      # Daily briefing panel
│   │   ├── CommunicationsQueue.tsx  # Communications queue
│   │   ├── AILoadingState.tsx       # Shared loading component
│   │   ├── AIErrorState.tsx         # Shared error component
│   │   └── AIStreamingText.tsx      # Streaming text display
│   │
│   ├── hooks/
│   │   ├── useAIChat.ts             # Chat interaction hook
│   │   ├── useAISchedule.ts         # Schedule generation hook
│   │   ├── useAICategorize.ts       # Categorization hook
│   │   ├── useAICommunication.ts    # Communication draft hook
│   │   ├── useAIEstimate.ts         # Estimate generation hook
│   │   └── useAIStreaming.ts        # Streaming response hook
│   │
│   ├── api/
│   │   └── aiApi.ts                 # AI API client
│   │
│   └── types/
│       └── index.ts                 # AI-related types
│
└── communications/                  # Communications feature
    ├── components/
    │   └── CommunicationsQueuePage.tsx
    ├── hooks/
    │   └── useCommunications.ts
    └── api/
        └── communicationsApi.ts
```

## Database Schema

### ai_audit_log Table

```sql
CREATE TABLE ai_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Action Details
    action_type VARCHAR(50) NOT NULL,  -- 'categorization', 'estimate', 'schedule', 'communication', 'query'
    entity_type VARCHAR(50) NOT NULL,  -- 'job', 'customer', 'schedule', 'message'
    entity_id UUID,
    
    -- AI Recommendation (summary, not full prompt)
    ai_recommendation JSONB NOT NULL,
    confidence_score DECIMAL(5, 2),  -- 0.00 to 100.00
    
    -- User Decision
    user_decision VARCHAR(20),  -- 'approved', 'rejected', 'modified', NULL (pending)
    user_id VARCHAR(100),  -- Future: user identifier
    decision_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    request_tokens INTEGER,
    response_tokens INTEGER,
    estimated_cost_usd DECIMAL(10, 6),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_action_type CHECK (action_type IN ('categorization', 'estimate', 'schedule', 'communication', 'query')),
    CONSTRAINT valid_entity_type CHECK (entity_type IN ('job', 'customer', 'schedule', 'message', 'query')),
    CONSTRAINT valid_user_decision CHECK (user_decision IS NULL OR user_decision IN ('approved', 'rejected', 'modified'))
);

-- Indexes
CREATE INDEX idx_ai_audit_log_action_type ON ai_audit_log(action_type);
CREATE INDEX idx_ai_audit_log_entity_type ON ai_audit_log(entity_type);
CREATE INDEX idx_ai_audit_log_entity_id ON ai_audit_log(entity_id);
CREATE INDEX idx_ai_audit_log_created_at ON ai_audit_log(created_at);
CREATE INDEX idx_ai_audit_log_user_decision ON ai_audit_log(user_decision);
```

### ai_usage Table

```sql
CREATE TABLE ai_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User Tracking
    user_id VARCHAR(100) NOT NULL DEFAULT 'viktor',  -- Single user for v1
    usage_date DATE NOT NULL,
    
    -- Request Counts
    request_count INTEGER NOT NULL DEFAULT 0,
    
    -- Token Usage
    total_input_tokens INTEGER NOT NULL DEFAULT 0,
    total_output_tokens INTEGER NOT NULL DEFAULT 0,
    
    -- Cost Tracking
    estimated_cost_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint for user + date
    CONSTRAINT unique_user_date UNIQUE (user_id, usage_date)
);

-- Indexes
CREATE INDEX idx_ai_usage_user_date ON ai_usage(user_id, usage_date);
CREATE INDEX idx_ai_usage_date ON ai_usage(usage_date);
```

### sent_messages Table

```sql
CREATE TABLE sent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    customer_id UUID NOT NULL REFERENCES customers(id),
    job_id UUID REFERENCES jobs(id),
    appointment_id UUID REFERENCES appointments(id),
    
    -- Message Details
    message_type VARCHAR(50) NOT NULL,  -- 'confirmation', 'reminder', 'on_the_way', 'completion', 'payment_reminder', 'estimate_follow_up'
    message_content TEXT NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    
    -- Delivery Tracking
    delivery_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'sent', 'delivered', 'failed'
    twilio_sid VARCHAR(50),
    error_message TEXT,
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_by VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_message_type CHECK (message_type IN ('confirmation', 'reminder', 'on_the_way', 'completion', 'payment_reminder', 'estimate_follow_up')),
    CONSTRAINT valid_delivery_status CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'failed'))
);

-- Indexes
CREATE INDEX idx_sent_messages_customer ON sent_messages(customer_id);
CREATE INDEX idx_sent_messages_job ON sent_messages(job_id);
CREATE INDEX idx_sent_messages_type ON sent_messages(message_type);
CREATE INDEX idx_sent_messages_status ON sent_messages(delivery_status);
CREATE INDEX idx_sent_messages_scheduled ON sent_messages(scheduled_for);
CREATE INDEX idx_sent_messages_sent_at ON sent_messages(sent_at);
```

### weather_cache Table

```sql
CREATE TABLE weather_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Location
    latitude DECIMAL(9, 6) NOT NULL,
    longitude DECIMAL(9, 6) NOT NULL,
    
    -- Forecast Data
    forecast_date DATE NOT NULL,
    forecast_data JSONB NOT NULL,  -- Full forecast response
    
    -- Key Metrics (extracted for quick access)
    precipitation_probability INTEGER,  -- 0-100
    condition VARCHAR(50),  -- 'clear', 'cloudy', 'rain', 'snow'
    high_temp_f INTEGER,
    low_temp_f INTEGER,
    
    -- Cache Management
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Unique constraint for location + date
    CONSTRAINT unique_location_date UNIQUE (latitude, longitude, forecast_date)
);

-- Indexes
CREATE INDEX idx_weather_cache_date ON weather_cache(forecast_date);
CREATE INDEX idx_weather_cache_expires ON weather_cache(expires_at);
```

## Data Models

### Enum Types

```python
from enum import Enum

class AIActionType(str, Enum):
    """AI action type enumeration."""
    CATEGORIZATION = "categorization"
    ESTIMATE = "estimate"
    SCHEDULE = "schedule"
    COMMUNICATION = "communication"
    QUERY = "query"

class AIEntityType(str, Enum):
    """AI entity type enumeration."""
    JOB = "job"
    CUSTOMER = "customer"
    SCHEDULE = "schedule"
    MESSAGE = "message"
    QUERY = "query"

class UserDecision(str, Enum):
    """User decision on AI recommendation."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"

class MessageType(str, Enum):
    """Communication message type."""
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    ON_THE_WAY = "on_the_way"
    COMPLETION = "completion"
    PAYMENT_REMINDER = "payment_reminder"
    ESTIMATE_FOLLOW_UP = "estimate_follow_up"

class DeliveryStatus(str, Enum):
    """SMS delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"

class WeatherCondition(str, Enum):
    """Weather condition enumeration."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
```

### Pydantic Schemas

#### AI Request/Response Schemas

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

# Chat Schemas
class AIChatRequest(BaseModel):
    """Request for AI chat interaction."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class AIChatResponse(BaseModel):
    """Response from AI chat."""
    message: str
    suggestions: Optional[List[str]] = None
    actions: Optional[List[Dict[str, Any]]] = None
    session_id: str

# Schedule Generation Schemas
class ScheduleGenerateRequest(BaseModel):
    """Request for AI schedule generation."""
    date_range_start: date
    date_range_end: date
    staff_ids: Optional[List[UUID]] = None
    include_categories: List[str] = Field(default=["ready_to_schedule"])

class StaffAssignment(BaseModel):
    """Staff assignment in generated schedule."""
    staff_id: UUID
    staff_name: str
    jobs: List["ScheduledJob"]
    total_jobs: int
    total_hours: Decimal
    route_miles: Decimal

class ScheduledJob(BaseModel):
    """Job in generated schedule."""
    job_id: UUID
    customer_name: str  # Placeholder filled locally
    address: str  # City only for AI, full address filled locally
    job_type: str
    time_window_start: str
    time_window_end: str
    estimated_duration_minutes: int
    price: Optional[Decimal]

class ScheduleDay(BaseModel):
    """Single day in generated schedule."""
    date: date
    weather: Optional["WeatherInfo"]
    staff_assignments: List[StaffAssignment]

class ScheduleWarning(BaseModel):
    """Warning in generated schedule."""
    warning_type: str  # 'weather', 'equipment', 'conflict', 'availability'
    message: str
    affected_job_ids: List[UUID]

class ScheduleGenerateResponse(BaseModel):
    """Response from AI schedule generation."""
    success: bool
    schedule: Optional["GeneratedSchedule"]
    ai_explanation: str
    audit_id: UUID

class GeneratedSchedule(BaseModel):
    """Complete generated schedule."""
    days: List[ScheduleDay]
    warnings: List[ScheduleWarning]
    summary: "ScheduleSummary"

class ScheduleSummary(BaseModel):
    """Summary of generated schedule."""
    total_jobs: int
    total_revenue: Decimal
    jobs_needing_review: int

# Job Categorization Schemas
class JobCategorizationRequest(BaseModel):
    """Request for AI job categorization."""
    job_ids: List[UUID]

class JobCategorization(BaseModel):
    """Single job categorization result."""
    job_id: UUID
    suggested_category: str  # 'ready_to_schedule', 'needs_estimate', 'needs_review', 'red_flag'
    confidence: Decimal  # 0.00 to 1.00
    suggested_price: Optional[Decimal]
    price_breakdown: Optional[Dict[str, Any]]
    ai_notes: str

class JobCategorizationResponse(BaseModel):
    """Response from AI job categorization."""
    success: bool
    categorizations: List[JobCategorization]
    summary: "CategorizationSummary"
    audit_id: UUID

class CategorizationSummary(BaseModel):
    """Summary of categorization results."""
    ready_to_schedule: int
    needs_estimate: int
    needs_review: int
    red_flag: int

# Communication Draft Schemas
class CommunicationDraftRequest(BaseModel):
    """Request for AI communication draft."""
    customer_id: UUID
    job_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    message_type: MessageType
    context: Optional[Dict[str, Any]] = None

class CommunicationDraft(BaseModel):
    """Generated communication draft."""
    message_content: str
    recipient_name: str  # Placeholder
    recipient_phone: str  # Masked
    message_type: MessageType
    ai_notes: Optional[str]

class CommunicationDraftResponse(BaseModel):
    """Response from AI communication draft."""
    success: bool
    draft: CommunicationDraft
    audit_id: UUID

# Estimate Generation Schemas
class EstimateGenerateRequest(BaseModel):
    """Request for AI estimate generation."""
    job_id: UUID

class SimilarJob(BaseModel):
    """Similar completed job for reference."""
    job_id: UUID
    address_city: str  # City only
    zone_count: int
    final_price: Decimal
    completed_at: datetime

class EstimateBreakdown(BaseModel):
    """Estimate price breakdown."""
    materials: Decimal
    labor: Decimal
    equipment: Decimal
    margin: Decimal
    total: Decimal

class EstimateGenerateResponse(BaseModel):
    """Response from AI estimate generation."""
    success: bool
    job_id: UUID
    estimated_zones: int
    similar_jobs: List[SimilarJob]
    recommended_price: Decimal
    breakdown: EstimateBreakdown
    ai_recommendation: str
    requires_site_visit: bool
    audit_id: UUID

# Usage and Audit Schemas
class AIUsageResponse(BaseModel):
    """AI usage statistics."""
    user_id: str
    date: date
    request_count: int
    daily_limit: int
    total_tokens: int
    estimated_cost_usd: Decimal
    limit_reached: bool

class AIAuditLogEntry(BaseModel):
    """Single audit log entry."""
    id: UUID
    action_type: AIActionType
    entity_type: AIEntityType
    entity_id: Optional[UUID]
    ai_recommendation: Dict[str, Any]
    confidence_score: Optional[Decimal]
    user_decision: Optional[UserDecision]
    decision_at: Optional[datetime]
    created_at: datetime

class AIAuditLogResponse(BaseModel):
    """Response for audit log query."""
    items: List[AIAuditLogEntry]
    total: int
    page: int
    page_size: int
```

#### SMS Schemas

```python
class SMSSendRequest(BaseModel):
    """Request to send SMS."""
    customer_id: UUID
    message_type: MessageType
    message_content: str
    job_id: Optional[UUID] = None
    appointment_id: Optional[UUID] = None
    scheduled_for: Optional[datetime] = None

class SMSSendResponse(BaseModel):
    """Response from SMS send."""
    success: bool
    message_id: UUID
    twilio_sid: Optional[str]
    delivery_status: DeliveryStatus
    error_message: Optional[str]

class SMSWebhookPayload(BaseModel):
    """Incoming SMS webhook payload from Twilio."""
    From: str
    To: str
    Body: str
    MessageSid: str
    AccountSid: str

class CommunicationsQueueItem(BaseModel):
    """Item in communications queue."""
    id: UUID
    customer_id: UUID
    customer_name: str
    message_type: MessageType
    message_content: str
    delivery_status: DeliveryStatus
    scheduled_for: Optional[datetime]
    sent_at: Optional[datetime]
    error_message: Optional[str]

class CommunicationsQueueResponse(BaseModel):
    """Communications queue response."""
    pending: List[CommunicationsQueueItem]
    scheduled: List[CommunicationsQueueItem]
    sent_today: List[CommunicationsQueueItem]
    failed: List[CommunicationsQueueItem]
```

#### Weather Schemas

```python
class WeatherInfo(BaseModel):
    """Weather information for a day."""
    date: date
    condition: WeatherCondition
    precipitation_probability: int  # 0-100
    high_temp_f: int
    low_temp_f: int
    is_bad_weather: bool  # True if precipitation > 70%

class WeatherForecastResponse(BaseModel):
    """Weather forecast response."""
    location: str
    forecasts: List[WeatherInfo]
    fetched_at: datetime
    source: str  # 'openweathermap'
```

## API Endpoints

### AI Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/ai/chat` | Natural language chat (streaming) | AIChatRequest | AIChatResponse (SSE) |
| POST | `/api/v1/ai/schedule/generate` | Generate optimized schedule | ScheduleGenerateRequest | ScheduleGenerateResponse |
| POST | `/api/v1/ai/jobs/categorize` | Categorize job requests | JobCategorizationRequest | JobCategorizationResponse |
| POST | `/api/v1/ai/communication/draft` | Generate communication draft | CommunicationDraftRequest | CommunicationDraftResponse |
| POST | `/api/v1/ai/estimate/generate` | Generate job estimate | EstimateGenerateRequest | EstimateGenerateResponse |
| GET | `/api/v1/ai/usage` | Get current usage stats | - | AIUsageResponse |
| GET | `/api/v1/ai/audit` | Query audit logs | Query params | AIAuditLogResponse |
| POST | `/api/v1/ai/audit/{id}/decision` | Record user decision | UserDecision | AIAuditLogEntry |

### SMS Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/sms/send` | Send SMS message | SMSSendRequest | SMSSendResponse |
| POST | `/api/v1/sms/webhook` | Receive incoming SMS | SMSWebhookPayload | 200 OK |
| GET | `/api/v1/communications/queue` | Get communications queue | Query params | CommunicationsQueueResponse |
| POST | `/api/v1/communications/send-bulk` | Send multiple messages | List[UUID] | List[SMSSendResponse] |
| DELETE | `/api/v1/communications/{id}` | Cancel scheduled message | - | 204 No Content |

### Weather Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/api/v1/weather/forecast` | Get 5-day forecast | Query params | WeatherForecastResponse |
| POST | `/api/v1/weather/refresh` | Force refresh forecast | - | WeatherForecastResponse |



## Service Layer Design

### AIAgentService

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from grins_platform.logging import LoggerMixin

class AIAgentService(LoggerMixin):
    """Main AI agent service using Pydantic AI."""
    
    DOMAIN = "ai"
    
    # Token limits
    MAX_INPUT_TOKENS = 4000
    MAX_OUTPUT_TOKENS = 2000
    
    def __init__(
        self,
        rate_limiter: RateLimitService,
        audit_service: AuditService,
        context_builder: ContextBuilder,
    ):
        self.rate_limiter = rate_limiter
        self.audit_service = audit_service
        self.context_builder = context_builder
        
        # Initialize Pydantic AI agent with GPT-5-nano
        self.agent = Agent(
            model=OpenAIModel('gpt-5-nano'),
            system_prompt=SYSTEM_PROMPT,
            tools=[
                self.get_pending_jobs,
                self.get_customer_info,
                self.get_service_catalog,
                self.generate_schedule,
                self.draft_communication,
                self.calculate_estimate,
                self.query_database,
            ]
        )
    
    async def chat(self, request: AIChatRequest, user_id: str) -> AsyncGenerator[str, None]:
        """Process chat request with streaming response."""
        self.log_started("chat", user_id=user_id, message_length=len(request.message))
        
        # Check rate limit
        if not await self.rate_limiter.check_limit(user_id):
            self.log_rejected("chat", reason="rate_limit_exceeded")
            raise RateLimitExceededError("Daily AI request limit reached")
        
        try:
            # Build context (respecting token limits)
            context = await self.context_builder.build(
                request.context,
                max_tokens=self.MAX_INPUT_TOKENS
            )
            
            # Stream response
            async for chunk in self.agent.run_stream(
                request.message,
                context=context
            ):
                yield chunk
            
            # Record usage
            await self.rate_limiter.record_usage(user_id, tokens_used)
            
            self.log_completed("chat", user_id=user_id)
            
        except Exception as e:
            self.log_failed("chat", error=e, user_id=user_id)
            raise AIServiceError(f"Chat failed: {e}") from e
    
    async def generate_schedule(
        self, 
        request: ScheduleGenerateRequest,
        user_id: str
    ) -> ScheduleGenerateResponse:
        """Generate optimized schedule using AI."""
        self.log_started(
            "generate_schedule",
            user_id=user_id,
            date_range=f"{request.date_range_start} to {request.date_range_end}"
        )
        
        # Check rate limit
        if not await self.rate_limiter.check_limit(user_id):
            raise RateLimitExceededError("Daily AI request limit reached")
        
        try:
            # Get jobs ready to schedule
            jobs = await self.job_repository.get_ready_to_schedule(
                request.include_categories
            )
            
            # Get staff availability
            staff = await self.staff_repository.get_available(
                request.staff_ids,
                request.date_range_start,
                request.date_range_end
            )
            
            # Get weather forecast
            weather = await self.weather_service.get_forecast(
                request.date_range_start,
                request.date_range_end
            )
            
            # Build context with PII removed
            context = self._build_schedule_context(jobs, staff, weather)
            
            # Generate schedule via AI
            result = await self.agent.run(
                SCHEDULE_GENERATION_PROMPT,
                context=context
            )
            
            # Parse and validate result
            schedule = self._parse_schedule_result(result, jobs, staff)
            
            # Create audit log
            audit_id = await self.audit_service.log_recommendation(
                action_type=AIActionType.SCHEDULE,
                entity_type=AIEntityType.SCHEDULE,
                recommendation=schedule.model_dump(),
            )
            
            self.log_completed("generate_schedule", audit_id=str(audit_id))
            
            return ScheduleGenerateResponse(
                success=True,
                schedule=schedule,
                ai_explanation=result.explanation,
                audit_id=audit_id
            )
            
        except Exception as e:
            self.log_failed("generate_schedule", error=e)
            raise AIServiceError(f"Schedule generation failed: {e}") from e
```

### RateLimitService

```python
class RateLimitService(LoggerMixin):
    """Service for AI rate limiting and cost control."""
    
    DOMAIN = "ai"
    
    DAILY_REQUEST_LIMIT = 100
    MONTHLY_COST_ALERT = 50.00  # USD
    MONTHLY_COST_CAP = 100.00  # USD (optional)
    
    def __init__(self, usage_repository: AIUsageRepository):
        self.usage_repository = usage_repository
    
    async def check_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits."""
        self.log_started("check_limit", user_id=user_id)
        
        today = date.today()
        usage = await self.usage_repository.get_or_create(user_id, today)
        
        if usage.request_count >= self.DAILY_REQUEST_LIMIT:
            self.log_rejected("check_limit", reason="daily_limit_exceeded")
            return False
        
        self.log_completed("check_limit", current_count=usage.request_count)
        return True
    
    async def record_usage(
        self,
        user_id: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """Record AI usage for tracking."""
        self.log_started("record_usage", user_id=user_id, tokens=input_tokens + output_tokens)
        
        today = date.today()
        
        # Calculate estimated cost (GPT-5-nano pricing)
        cost = self._calculate_cost(input_tokens, output_tokens)
        
        await self.usage_repository.increment(
            user_id=user_id,
            usage_date=today,
            request_count=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        
        # Check monthly cost alert
        monthly_cost = await self.usage_repository.get_monthly_cost(user_id)
        if monthly_cost >= self.MONTHLY_COST_ALERT:
            self.log_warning("record_usage", reason="monthly_cost_alert", cost=monthly_cost)
            # TODO: Send email alert
        
        self.log_completed("record_usage", cost=cost)
    
    async def get_usage(self, user_id: str) -> AIUsageResponse:
        """Get current usage statistics."""
        today = date.today()
        usage = await self.usage_repository.get_or_create(user_id, today)
        
        return AIUsageResponse(
            user_id=user_id,
            date=today,
            request_count=usage.request_count,
            daily_limit=self.DAILY_REQUEST_LIMIT,
            total_tokens=usage.total_input_tokens + usage.total_output_tokens,
            estimated_cost_usd=usage.estimated_cost_usd,
            limit_reached=usage.request_count >= self.DAILY_REQUEST_LIMIT
        )
```

### AuditService

```python
class AuditService(LoggerMixin):
    """Service for AI audit logging."""
    
    DOMAIN = "ai"
    
    def __init__(self, audit_repository: AIAuditLogRepository):
        self.audit_repository = audit_repository
    
    async def log_recommendation(
        self,
        action_type: AIActionType,
        entity_type: AIEntityType,
        recommendation: Dict[str, Any],
        entity_id: Optional[UUID] = None,
        confidence_score: Optional[Decimal] = None,
        request_tokens: Optional[int] = None,
        response_tokens: Optional[int] = None,
    ) -> UUID:
        """Log an AI recommendation for audit."""
        self.log_started(
            "log_recommendation",
            action_type=action_type.value,
            entity_type=entity_type.value
        )
        
        # Calculate estimated cost
        cost = None
        if request_tokens and response_tokens:
            cost = self._calculate_cost(request_tokens, response_tokens)
        
        audit_entry = await self.audit_repository.create(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            ai_recommendation=recommendation,
            confidence_score=confidence_score,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            estimated_cost_usd=cost,
        )
        
        self.log_completed("log_recommendation", audit_id=str(audit_entry.id))
        return audit_entry.id
    
    async def record_decision(
        self,
        audit_id: UUID,
        decision: UserDecision,
        user_id: Optional[str] = None
    ) -> AIAuditLogEntry:
        """Record user decision on AI recommendation."""
        self.log_started("record_decision", audit_id=str(audit_id), decision=decision.value)
        
        entry = await self.audit_repository.update_decision(
            audit_id=audit_id,
            user_decision=decision,
            user_id=user_id,
            decision_at=datetime.utcnow()
        )
        
        self.log_completed("record_decision", audit_id=str(audit_id))
        return entry
```

### SMSService

```python
from twilio.rest import Client

class SMSService(LoggerMixin):
    """Service for SMS messaging via Twilio."""
    
    DOMAIN = "sms"
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        phone_number: str,
        message_repository: SentMessageRepository,
        customer_repository: CustomerRepository,
    ):
        self.client = Client(account_sid, auth_token)
        self.phone_number = phone_number
        self.message_repository = message_repository
        self.customer_repository = customer_repository
    
    async def send_message(self, request: SMSSendRequest) -> SMSSendResponse:
        """Send SMS message via Twilio."""
        self.log_started(
            "send_message",
            customer_id=str(request.customer_id),
            message_type=request.message_type.value
        )
        
        # Get customer and validate opt-in
        customer = await self.customer_repository.get_by_id(request.customer_id)
        if not customer:
            self.log_rejected("send_message", reason="customer_not_found")
            raise CustomerNotFoundError(request.customer_id)
        
        if not customer.sms_opt_in:
            self.log_rejected("send_message", reason="sms_not_opted_in")
            raise SMSOptInRequiredError(request.customer_id)
        
        # Format phone number to E.164
        phone = self._format_phone(customer.phone)
        
        # Create message record
        message_record = await self.message_repository.create(
            customer_id=request.customer_id,
            job_id=request.job_id,
            appointment_id=request.appointment_id,
            message_type=request.message_type,
            message_content=request.message_content,
            recipient_phone=phone,
            scheduled_for=request.scheduled_for,
        )
        
        # If scheduled for later, don't send now
        if request.scheduled_for and request.scheduled_for > datetime.utcnow():
            self.log_completed("send_message", status="scheduled")
            return SMSSendResponse(
                success=True,
                message_id=message_record.id,
                delivery_status=DeliveryStatus.PENDING
            )
        
        try:
            # Send via Twilio
            twilio_message = self.client.messages.create(
                body=request.message_content,
                from_=self.phone_number,
                to=phone
            )
            
            # Update record with Twilio SID
            await self.message_repository.update(
                message_record.id,
                twilio_sid=twilio_message.sid,
                delivery_status=DeliveryStatus.SENT,
                sent_at=datetime.utcnow()
            )
            
            self.log_completed(
                "send_message",
                twilio_sid=twilio_message.sid,
                status="sent"
            )
            
            return SMSSendResponse(
                success=True,
                message_id=message_record.id,
                twilio_sid=twilio_message.sid,
                delivery_status=DeliveryStatus.SENT
            )
            
        except Exception as e:
            # Update record with error
            await self.message_repository.update(
                message_record.id,
                delivery_status=DeliveryStatus.FAILED,
                error_message=str(e)
            )
            
            self.log_failed("send_message", error=e)
            
            return SMSSendResponse(
                success=False,
                message_id=message_record.id,
                delivery_status=DeliveryStatus.FAILED,
                error_message=str(e)
            )
    
    async def handle_webhook(self, payload: SMSWebhookPayload) -> None:
        """Handle incoming SMS webhook from Twilio."""
        self.log_started("handle_webhook", from_phone=payload.From)
        
        # Find customer by phone
        phone_digits = ''.join(filter(str.isdigit, payload.From))[-10:]
        customer = await self.customer_repository.find_by_phone(phone_digits)
        
        if not customer:
            self.log_warning("handle_webhook", reason="customer_not_found")
            return
        
        # Parse response
        response_text = payload.Body.strip().upper()
        
        if response_text == "YES":
            # Confirm pending appointment
            await self._confirm_appointment(customer.id)
            self.log_completed("handle_webhook", action="confirmed")
            
        elif response_text in ["NO", "CANCEL", "RESCHEDULE"]:
            # Flag for manual review
            await self._flag_for_review(customer.id, response_text)
            self.log_completed("handle_webhook", action="flagged_for_review")
            
        else:
            self.log_completed("handle_webhook", action="unrecognized_response")
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format."""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"+1{digits}"
        return f"+{digits}"
```

### WeatherService

```python
import httpx

class WeatherService(LoggerMixin):
    """Service for weather data via OpenWeatherMap."""
    
    DOMAIN = "weather"
    
    # Twin Cities coordinates
    DEFAULT_LAT = 44.98
    DEFAULT_LON = -93.27
    
    # Bad weather threshold
    PRECIPITATION_THRESHOLD = 70  # percent
    
    def __init__(
        self,
        api_key: str,
        cache_repository: WeatherCacheRepository
    ):
        self.api_key = api_key
        self.cache_repository = cache_repository
        self.base_url = "https://api.openweathermap.org/data/2.5/forecast"
    
    async def get_forecast(
        self,
        start_date: date,
        end_date: date,
        lat: float = DEFAULT_LAT,
        lon: float = DEFAULT_LON
    ) -> List[WeatherInfo]:
        """Get weather forecast for date range."""
        self.log_started("get_forecast", start=str(start_date), end=str(end_date))
        
        forecasts = []
        current_date = start_date
        
        while current_date <= end_date:
            # Check cache first
            cached = await self.cache_repository.get(lat, lon, current_date)
            
            if cached and cached.expires_at > datetime.utcnow():
                forecasts.append(self._cache_to_weather_info(cached))
            else:
                # Fetch from API
                try:
                    api_forecast = await self._fetch_from_api(lat, lon)
                    
                    # Cache results
                    for day_forecast in api_forecast:
                        await self.cache_repository.upsert(
                            lat, lon, day_forecast
                        )
                        if day_forecast.date == current_date:
                            forecasts.append(day_forecast)
                    
                except Exception as e:
                    self.log_warning("get_forecast", reason="api_error", error=str(e))
                    # Return None for this day if API fails
                    forecasts.append(None)
            
            current_date += timedelta(days=1)
        
        self.log_completed("get_forecast", days=len(forecasts))
        return forecasts
    
    async def _fetch_from_api(self, lat: float, lon: float) -> List[WeatherInfo]:
        """Fetch forecast from OpenWeatherMap API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": self.api_key,
                    "units": "imperial"
                }
            )
            response.raise_for_status()
            data = response.json()
        
        # Parse 3-hour intervals into daily forecasts
        daily_forecasts = self._aggregate_to_daily(data["list"])
        return daily_forecasts
    
    def _aggregate_to_daily(self, intervals: List[Dict]) -> List[WeatherInfo]:
        """Aggregate 3-hour intervals to daily forecasts."""
        daily = {}
        
        for interval in intervals:
            dt = datetime.fromtimestamp(interval["dt"])
            day = dt.date()
            
            if day not in daily:
                daily[day] = {
                    "temps": [],
                    "precip_probs": [],
                    "conditions": []
                }
            
            daily[day]["temps"].append(interval["main"]["temp"])
            daily[day]["precip_probs"].append(interval.get("pop", 0) * 100)
            daily[day]["conditions"].append(interval["weather"][0]["main"])
        
        forecasts = []
        for day, data in sorted(daily.items()):
            max_precip = max(data["precip_probs"])
            forecasts.append(WeatherInfo(
                date=day,
                condition=self._map_condition(data["conditions"]),
                precipitation_probability=int(max_precip),
                high_temp_f=int(max(data["temps"])),
                low_temp_f=int(min(data["temps"])),
                is_bad_weather=max_precip >= self.PRECIPITATION_THRESHOLD
            ))
        
        return forecasts
```



### ContextBuilder

```python
class ContextBuilder(LoggerMixin):
    """Builds AI context with token management and PII removal."""
    
    DOMAIN = "ai"
    
    # Token budgets by priority
    TOKEN_BUDGETS = {
        "current_request": 500,   # HIGHEST - never truncate
        "business_rules": 100,    # HIGHEST - never truncate
        "customer_info": 300,     # HIGH
        "recent_jobs": 500,       # MEDIUM
        "service_catalog": 400,   # MEDIUM
        "staff_availability": 200 # LOW
    }
    
    def __init__(
        self,
        customer_repository: CustomerRepository,
        job_repository: JobRepository,
        service_repository: ServiceOfferingRepository,
        staff_repository: StaffRepository,
    ):
        self.customer_repository = customer_repository
        self.job_repository = job_repository
        self.service_repository = service_repository
        self.staff_repository = staff_repository
    
    async def build(
        self,
        request_context: Optional[Dict[str, Any]],
        max_tokens: int = 4000
    ) -> str:
        """Build context string within token limits."""
        self.log_started("build", max_tokens=max_tokens)
        
        context_parts = []
        token_count = 0
        
        # Always include business rules (never truncate)
        business_rules = self._get_business_rules()
        context_parts.append(business_rules)
        token_count += self._estimate_tokens(business_rules)
        
        # Always include current request (never truncate)
        if request_context:
            request_str = self._format_request(request_context)
            context_parts.append(request_str)
            token_count += self._estimate_tokens(request_str)
        
        # Add customer info if space allows
        if request_context and "customer_id" in request_context:
            customer = await self.customer_repository.get_by_id(
                request_context["customer_id"]
            )
            if customer and token_count + self.TOKEN_BUDGETS["customer_info"] < max_tokens:
                customer_str = self._format_customer(customer)
                context_parts.append(customer_str)
                token_count += self._estimate_tokens(customer_str)
        
        # Add recent jobs if space allows
        if request_context and "customer_id" in request_context:
            jobs = await self.job_repository.get_recent_for_customer(
                request_context["customer_id"],
                limit=5
            )
            if jobs and token_count + self.TOKEN_BUDGETS["recent_jobs"] < max_tokens:
                jobs_str = self._format_jobs(jobs)
                context_parts.append(jobs_str)
                token_count += self._estimate_tokens(jobs_str)
        
        # Add service catalog if space allows
        if token_count + self.TOKEN_BUDGETS["service_catalog"] < max_tokens:
            services = await self.service_repository.get_active()
            services_str = self._format_services(services)
            context_parts.append(services_str)
            token_count += self._estimate_tokens(services_str)
        
        # Add staff availability if space allows
        if token_count + self.TOKEN_BUDGETS["staff_availability"] < max_tokens:
            staff = await self.staff_repository.get_available()
            staff_str = self._format_staff(staff)
            context_parts.append(staff_str)
            token_count += self._estimate_tokens(staff_str)
        
        self.log_completed("build", token_count=token_count)
        return "\n\n".join(context_parts)
    
    def _format_customer(self, customer: Customer) -> str:
        """Format customer info with PII removed."""
        # Use placeholder instead of actual name
        return f"""Customer Information:
- ID: {customer.id}
- Customer: Customer #{str(customer.id)[:8]}
- City: {customer.city or 'Unknown'}
- Customer Type: {'Commercial' if customer.is_commercial else 'Residential'}
- Priority: {'High' if customer.is_priority else 'Normal'}
- Red Flag: {'Yes' if customer.is_red_flag else 'No'}
- SMS Opt-in: {'Yes' if customer.sms_opt_in else 'No'}"""
    
    def _format_jobs(self, jobs: List[Job]) -> str:
        """Format job history with PII removed."""
        lines = ["Recent Job History:"]
        for job in jobs:
            lines.append(f"- Job #{str(job.id)[:8]}: {job.job_type}, Status: {job.status}, Amount: ${job.final_amount or job.quoted_amount or 'TBD'}")
        return "\n".join(lines)
    
    def _get_business_rules(self) -> str:
        """Get static business rules for context."""
        return """Business Rules for Grin's Irrigation:
- Seasonal services (startups, winterizations) are priced by zone count: $45-65 per zone
- Standard residential systems take ~30-45 minutes per zone
- Commercial and lake pump systems take longer (1.5x time estimate)
- Batch jobs by location (city) and job type for route efficiency
- First-come-first-serve with 2-4 day buffer for route optimization
- Staffing: 1 person for service calls, 2 for major repairs, 2-4 for installs
- Equipment: Compressor required for winterizations, pipe puller for installs
- Partner jobs (source='partner') use special pricing ($700/zone for installs)
- Red flag customers require manager approval before scheduling"""
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 4 chars per token)."""
        return len(text) // 4
```

## System Prompts

### Base System Prompt

```python
SYSTEM_PROMPT = """You are an AI assistant for Grin's Irrigation, a field service company 
serving the Twin Cities metro area (Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, 
Rogers, and surrounding cities).

Your role is to help Viktor manage scheduling, customer communication, and business 
operations. You analyze data and provide recommendations, but you NEVER execute actions 
directly - all actions require explicit user approval.

Key Responsibilities:
1. Generate optimized weekly schedules considering location, job type, staff skills, and weather
2. Categorize incoming job requests as "ready to schedule" or "requires estimate"
3. Draft customer communications (confirmations, reminders, follow-ups)
4. Answer business questions about customers, jobs, revenue, and operations
5. Generate estimates based on job details and similar completed work

Important Guidelines:
- Always explain your reasoning
- Flag any concerns or conflicts
- Provide confidence levels for categorizations
- Never include actual customer names, phones, or addresses in your responses
- Use placeholders like "Customer #1234" that will be filled in locally
- When uncertain, recommend human review

Business Context:
- Peak seasons: Spring (startups) and Fall (winterizations) with 150+ jobs/week
- Service types: Seasonal (startup, tuneup, winterization), Repairs, Installations, Diagnostics
- Pricing: Zone-based for seasonal ($45-65/zone), flat rate for repairs ($50/head, $100 diagnostic)
- Staff: Vas and Dad for service calls, Viktor for estimates and complex jobs
"""
```

### Schedule Generation Prompt

```python
SCHEDULE_GENERATION_PROMPT = """Generate an optimized weekly schedule for the provided jobs.

Consider these factors in order of priority:
1. Job type batching - Group seasonal services together, repairs together, installs together
2. Location clustering - Group jobs by city to minimize drive time
3. Time estimates - Calculate based on zone count and system type
4. Staff skills - Match job requirements to staff capabilities
5. Equipment needs - Flag jobs requiring compressor or pipe puller
6. Weather sensitivity - Flag outdoor jobs on days with >70% precipitation chance
7. First-come-first-serve - Respect request order with 2-4 day buffer for optimization

Staffing Rules:
- 1 person: Service calls, small repairs
- 2 people: Major repairs, diagnostics
- 2-4 people: Installations, landscaping

Output Format:
For each day, provide:
- Date
- Staff assignments with job list
- Time estimates per staff member
- Route miles estimate
- Any warnings (weather, equipment, conflicts)

End with a summary of total jobs, estimated revenue, and jobs needing review."""
```

### Categorization Prompt

```python
CATEGORIZATION_PROMPT = """Categorize the provided job requests into:
- ready_to_schedule: Can be scheduled immediately
- needs_estimate: Requires site visit or custom quote
- needs_review: Ambiguous, needs human decision
- red_flag: Customer on red flag list

Auto-categorize as "ready_to_schedule" when:
- Job type is seasonal (spring_startup, summer_tuneup, winterization)
- Job type is small_repair or head_replacement
- Job has an approved quote (quoted_amount is set)
- Source is "partner" (builder/partner pricing applies)

Auto-categorize as "needs_estimate" when:
- Job type is new_system or major_repair
- Description mentions "large", "complex", or "multiple"
- New customer with no property data on file

For each job, provide:
- Suggested category
- Confidence score (0-100%)
- Suggested price (if applicable)
- Price breakdown (base + per-zone calculation)
- Notes explaining the categorization

Flag for "needs_review" when confidence is below 85%."""
```



## Error Handling

### Error Types and Responses

| Error Type | HTTP Status | User Message | Recovery Action |
|------------|-------------|--------------|-----------------|
| RateLimitExceededError | 429 | "Daily limit reached, resets at midnight" | Enable manual workflows |
| AIServiceError | 503 | "AI temporarily unavailable" | Show manual fallback buttons |
| AIResponseInvalidError | 500 | "AI couldn't process this request" | Retry once, then manual fallback |
| SMSOptInRequiredError | 400 | "Customer has not opted in to SMS" | Show opt-in prompt |
| SMSDeliveryFailedError | 502 | "Message delivery failed" | Show retry button |
| WeatherAPIError | 503 | "Weather data unavailable" | Allow scheduling without weather |
| TokenLimitExceededError | 400 | "Request too large, please simplify" | Truncate context automatically |

### Graceful Degradation Strategy

```python
class AIErrorHandler:
    """Centralized error handling for AI features."""
    
    async def handle_error(self, error: Exception, context: Dict) -> AIErrorResponse:
        """Handle AI errors with graceful degradation."""
        
        if isinstance(error, RateLimitExceededError):
            return AIErrorResponse(
                error_type="rate_limit",
                message="You've used your 100 AI requests for today. AI features will be available again tomorrow.",
                show_manual_fallback=True,
                retry_after=self._seconds_until_midnight()
            )
        
        if isinstance(error, (httpx.TimeoutException, httpx.ConnectError)):
            # Retry with exponential backoff
            for attempt in range(3):
                await asyncio.sleep(2 ** attempt)
                try:
                    return await self._retry_request(context)
                except Exception:
                    continue
            
            return AIErrorResponse(
                error_type="service_unavailable",
                message="AI temporarily unavailable. You can continue manually.",
                show_manual_fallback=True
            )
        
        if isinstance(error, AIResponseInvalidError):
            return AIErrorResponse(
                error_type="invalid_response",
                message="AI couldn't process this request. Please try again or continue manually.",
                show_manual_fallback=True
            )
        
        # Unknown error - log and return generic message
        logger.error("ai.unknown_error", error=str(error), context=context)
        return AIErrorResponse(
            error_type="unknown",
            message="Something went wrong. Please try again.",
            show_manual_fallback=True
        )
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: PII Protection

*For any* customer data processed by the AI context builder, the resulting context string SHALL NOT contain actual customer names, phone numbers, email addresses, or street addresses. Instead, placeholders (e.g., "Customer #1234", "City: Eden Prairie") SHALL be used.

**Validates: Requirements 1.6, 1.7, 17.6**

### Property 2: Context Token Limit Enforcement

*For any* AI request, the context builder SHALL produce a context string that does not exceed 4000 tokens. When input data would exceed this limit, lower-priority context (staff availability, then service catalog, then job history) SHALL be truncated while preserving current request and business rules.

**Validates: Requirements 1.3, 13.5**

### Property 3: Rate Limit Enforcement

*For any* user making AI requests, after 100 requests in a single calendar day, all subsequent AI requests SHALL be rejected with a rate limit error until midnight UTC reset.

**Validates: Requirements 2.1, 2.2**

### Property 4: Audit Log Completeness for Recommendations

*For any* AI recommendation generated (categorization, estimate, schedule, communication), an audit log entry SHALL be created containing: action_type, entity_type, entity_id (if applicable), ai_recommendation summary, and created_at timestamp.

**Validates: Requirements 3.1**

### Property 5: Audit Log Completeness for Decisions

*For any* user decision (approved, rejected, modified) on an AI recommendation, the corresponding audit log entry SHALL be updated with: user_decision, decision_at timestamp, and user_id.

**Validates: Requirements 3.2, 3.3, 3.4**

### Property 6: Schedule Location Batching

*For any* generated schedule containing jobs in multiple cities, jobs in the same city SHALL be grouped together on the same day and assigned to the same staff member when possible, to minimize drive time.

**Validates: Requirements 4.2**

### Property 7: Schedule Job Type Batching

*For any* generated schedule, jobs of the same type (seasonal, repair, installation) SHALL be grouped together when possible, with seasonal services batched separately from repairs and installations.

**Validates: Requirements 4.3**

### Property 8: Weather Flagging Threshold

*For any* job scheduled on a day where the weather forecast shows precipitation probability ≥70%, the schedule SHALL include a weather warning flagging that job as weather-sensitive.

**Validates: Requirements 4.8, 11.3**

### Property 9: Confidence Threshold Routing

*For any* job categorization, if the AI confidence score is ≥85%, the job SHALL be routed to "ready_to_schedule" category. If confidence is <85%, the job SHALL be routed to "needs_review" category.

**Validates: Requirements 5.5, 5.6**

### Property 10: Human Approval Required for Actions

*For any* action that modifies system state (sending SMS, creating appointments, updating job status), the action SHALL NOT be executed without a corresponding user approval event being recorded in the audit log.

**Validates: Requirements 6.10**

### Property 11: Duplicate Message Prevention

*For any* customer and message type combination, if a message of that type was sent to that customer within the last 24 hours, a subsequent send attempt SHALL be rejected or flagged for review.

**Validates: Requirements 7.7**

### Property 12: Session History Limit

*For any* chat session, the session history SHALL contain at most 50 messages. When a new message would exceed this limit, the oldest message SHALL be removed before adding the new one.

**Validates: Requirements 8.9, 13.2**

### Property 13: SMS Opt-in Enforcement

*For any* SMS send request, if the target customer's sms_opt_in field is false, the send request SHALL be rejected with an SMSOptInRequiredError.

**Validates: Requirements 12.8, 12.9**

### Property 14: Input Sanitization

*For any* user input included in AI prompts, special characters and potential prompt injection patterns SHALL be escaped or removed before inclusion in the prompt.

**Validates: Requirements 17.2**

### Property 15: Data-testid Attribute Coverage

*For any* AI UI component (AIQueryChat, AIScheduleGenerator, AICategorization, AICommunicationDrafts, AIEstimateGenerator, MorningBriefing, CommunicationsQueue), the component SHALL include data-testid attributes on interactive elements for agent-browser targeting.

**Validates: Requirements 19.8**

## Testing Strategy

### Dual Testing Approach

The AI Assistant feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, error conditions, and mock LLM responses
- **Property tests**: Verify universal properties across all inputs using randomized testing

### Test Configuration

- **Property-based testing library**: Hypothesis (Python)
- **Minimum iterations**: 100 per property test
- **Tag format**: `Feature: ai-assistant, Property {number}: {property_text}`

### Unit Test Examples

```python
@pytest.mark.unit
class TestContextBuilder:
    """Unit tests for ContextBuilder."""
    
    def test_pii_removed_from_customer_context(self):
        """Test that customer PII is replaced with placeholders."""
        customer = Customer(
            id=uuid4(),
            first_name="John",
            last_name="Doe",
            phone="6125551234",
            email="john@example.com",
            city="Eden Prairie"
        )
        
        context = context_builder._format_customer(customer)
        
        assert "John" not in context
        assert "Doe" not in context
        assert "6125551234" not in context
        assert "john@example.com" not in context
        assert f"Customer #{str(customer.id)[:8]}" in context
        assert "Eden Prairie" in context  # City is allowed

@pytest.mark.unit
class TestRateLimiter:
    """Unit tests for RateLimitService."""
    
    async def test_limit_enforced_at_100_requests(self, mock_repository):
        """Test that 101st request is rejected."""
        mock_repository.get_or_create.return_value = AIUsage(request_count=100)
        
        result = await rate_limiter.check_limit("viktor")
        
        assert result is False
    
    async def test_under_limit_allowed(self, mock_repository):
        """Test that requests under limit are allowed."""
        mock_repository.get_or_create.return_value = AIUsage(request_count=50)
        
        result = await rate_limiter.check_limit("viktor")
        
        assert result is True
```

### Property Test Examples

```python
from hypothesis import given, strategies as st

@pytest.mark.property
class TestContextBuilderProperties:
    """Property-based tests for ContextBuilder."""
    
    @given(
        first_name=st.text(min_size=1, max_size=50),
        last_name=st.text(min_size=1, max_size=50),
        phone=st.from_regex(r'\d{10}', fullmatch=True),
        email=st.emails(),
        city=st.sampled_from(["Eden Prairie", "Plymouth", "Maple Grove"])
    )
    def test_pii_never_in_context(self, first_name, last_name, phone, email, city):
        """
        Feature: ai-assistant, Property 1: PII Protection
        For any customer data, context SHALL NOT contain PII.
        """
        customer = Customer(
            id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            city=city
        )
        
        context = context_builder._format_customer(customer)
        
        assert first_name not in context
        assert last_name not in context
        assert phone not in context
        assert email not in context

@pytest.mark.property
class TestRateLimiterProperties:
    """Property-based tests for RateLimitService."""
    
    @given(request_count=st.integers(min_value=100, max_value=1000))
    def test_over_limit_always_rejected(self, request_count):
        """
        Feature: ai-assistant, Property 3: Rate Limit Enforcement
        For any request count >= 100, check_limit SHALL return False.
        """
        usage = AIUsage(request_count=request_count)
        
        result = rate_limiter._check_against_limit(usage)
        
        assert result is False
    
    @given(request_count=st.integers(min_value=0, max_value=99))
    def test_under_limit_always_allowed(self, request_count):
        """
        Feature: ai-assistant, Property 3: Rate Limit Enforcement
        For any request count < 100, check_limit SHALL return True.
        """
        usage = AIUsage(request_count=request_count)
        
        result = rate_limiter._check_against_limit(usage)
        
        assert result is True

@pytest.mark.property
class TestSessionHistoryProperties:
    """Property-based tests for session history."""
    
    @given(messages=st.lists(st.text(min_size=1), min_size=51, max_size=100))
    def test_session_never_exceeds_50_messages(self, messages):
        """
        Feature: ai-assistant, Property 12: Session History Limit
        For any number of messages added, session SHALL contain at most 50.
        """
        session = ChatSession()
        
        for msg in messages:
            session.add_message(msg)
        
        assert len(session.messages) <= 50
        # Verify newest messages are kept
        assert session.messages[-1] == messages[-1]
```

### Integration Test Strategy

- Use GPT-3.5-turbo for integration tests (cheaper, faster than GPT-5-nano)
- Maintain golden dataset of 30 input/output pairs per AI capability
- Mock LLM for load testing infrastructure
- Use anonymized/fake customer data in all tests

### Agent-Browser Validation Scripts

Each AI component requires visual validation using agent-browser:

```bash
#!/bin/bash
# scripts/validate-ai-chat.sh

echo "🧪 AI Chat Component Validation"

agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Verify chat component renders
agent-browser is visible "[data-testid='ai-query-chat']" && echo "  ✓ Chat component visible"

# Test chat interaction
agent-browser fill "[data-testid='ai-chat-input']" "How many jobs are scheduled for tomorrow?"
agent-browser click "[data-testid='ai-chat-submit']"
agent-browser wait "[data-testid='ai-chat-response']"
echo "  ✓ Chat response received"

# Verify streaming display
agent-browser is visible "[data-testid='ai-streaming-text']" && echo "  ✓ Streaming text visible"

agent-browser close
echo "✅ AI Chat Validation PASSED!"
```

## Implementation Phases

### Phase 6.1: Foundation (Week 1)
- Set up Pydantic AI infrastructure with GPT-5-nano
- Create base agent with system prompts
- Implement database context retrieval tools
- Create basic chat API endpoint with streaming
- Build AI chat widget component
- Implement rate limiting service
- Implement audit logging service

### Phase 6.2: Natural Language Queries (Week 2)
- Implement query tools for customers, jobs, invoices
- Build query result formatting
- Add query suggestions and examples
- Integrate chat widget into dashboard
- Add session history management

### Phase 6.3: Job Categorization (Week 3)
- Implement categorization logic and tools
- Build categorization UI panel
- Add confidence scoring and threshold routing
- Integrate into job requests page
- Add bulk approval actions

### Phase 6.4: Communication Drafts (Week 4)
- Implement message template system
- Build communication draft tools
- Create Communications Queue UI
- Set up Twilio SMS integration
- Implement webhook for incoming SMS
- Add scheduling for automated messages

### Phase 6.5: Schedule Generation (Week 5-6)
- Implement scheduling algorithm tools
- Integrate weather service (OpenWeatherMap)
- Build schedule preview UI
- Add constraint handling (availability, equipment, weather)
- Integrate with existing schedule page

### Phase 6.6: Estimate Generation (Week 7)
- Implement estimate calculation tools
- Build estimate preview UI
- Add similar job reference lookup
- Generate PDF estimates (future)

### Phase 6.7: Polish & Testing (Week 8)
- End-to-end testing with property-based tests
- Agent-browser visual validation for all components
- Performance optimization
- Error handling improvements
- Documentation

## Notes

- All AI features follow human-in-the-loop principle - no auto-execution
- PII is never sent to LLM APIs - use placeholders filled locally
- Rate limiting prevents runaway costs (100 requests/day, $50 alert)
- Session history is browser-tab scoped, max 50 messages
- Weather flagging is advisory only - no auto-rescheduling
- SMS requires explicit opt-in from customers
