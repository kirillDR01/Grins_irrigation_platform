"""AI-related Pydantic schemas and enums.

This module defines all schemas for AI Assistant Integration including
request/response models for chat, scheduling, categorization, communication,
and estimate generation.

Validates: AI Assistant Requirements 15.1-15.7
"""

from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# =============================================================================
# Enums (Task 2.1)
# =============================================================================


class AIActionType(str, Enum):
    """Types of AI actions that can be audited."""

    SCHEDULE_GENERATION = "schedule_generation"
    JOB_CATEGORIZATION = "job_categorization"
    COMMUNICATION_DRAFT = "communication_draft"
    ESTIMATE_GENERATION = "estimate_generation"
    BUSINESS_QUERY = "business_query"


class AIEntityType(str, Enum):
    """Types of entities that AI actions can affect."""

    JOB = "job"
    CUSTOMER = "customer"
    APPOINTMENT = "appointment"
    SCHEDULE = "schedule"
    COMMUNICATION = "communication"
    ESTIMATE = "estimate"


class UserDecision(str, Enum):
    """User decisions on AI recommendations."""

    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    PENDING = "pending"


class MessageType(str, Enum):
    """Types of SMS messages."""

    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    ON_THE_WAY = "on_the_way"
    ARRIVAL = "arrival"
    COMPLETION = "completion"
    INVOICE = "invoice"
    PAYMENT_REMINDER = "payment_reminder"
    CUSTOM = "custom"


class DeliveryStatus(str, Enum):
    """SMS delivery status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Chat Schemas (Task 2.2)
# =============================================================================


class AIChatRequest(BaseModel):
    """Request for AI chat interaction."""

    message: str = Field(..., min_length=1, max_length=2000)
    session_id: UUID | None = None


class AIChatResponse(BaseModel):
    """Response from AI chat interaction."""

    message: str
    session_id: UUID
    tokens_used: int
    is_streaming: bool = False


# =============================================================================
# Schedule Generation Schemas (Task 2.2)
# =============================================================================


class ScheduledJob(BaseModel):
    """A job scheduled in a time slot."""

    job_id: UUID
    customer_name: str
    address: str
    job_type: str
    estimated_duration_minutes: int
    time_window_start: time
    time_window_end: time
    notes: str | None = None


class StaffAssignment(BaseModel):
    """Staff assignment for a day."""

    staff_id: UUID
    staff_name: str
    jobs: list[ScheduledJob]
    total_jobs: int
    total_minutes: int


class ScheduleWarning(BaseModel):
    """Warning about a schedule issue."""

    warning_type: str
    message: str
    job_id: UUID | None = None
    staff_id: UUID | None = None


class ScheduleDay(BaseModel):
    """Schedule for a single day."""

    date: date
    staff_assignments: list[StaffAssignment]
    warnings: list[ScheduleWarning]


class ScheduleSummary(BaseModel):
    """Summary statistics for generated schedule."""

    total_jobs: int
    total_staff: int
    total_days: int
    jobs_per_day_avg: float
    warnings_count: int


class ScheduleGenerateRequest(BaseModel):
    """Request to generate a schedule."""

    start_date: date
    end_date: date
    staff_ids: list[UUID] | None = None
    include_pending_jobs: bool = True


class GeneratedSchedule(BaseModel):
    """A complete generated schedule."""

    schedule_id: UUID
    days: list[ScheduleDay]
    summary: ScheduleSummary
    ai_explanation: str
    confidence_score: float = Field(..., ge=0, le=1)


class ScheduleGenerateResponse(BaseModel):
    """Response from schedule generation."""

    schedule: GeneratedSchedule
    audit_log_id: UUID


# =============================================================================
# Job Categorization Schemas (Task 2.2)
# =============================================================================


class JobCategorization(BaseModel):
    """Categorization result for a single job."""

    job_id: UUID
    suggested_category: str
    suggested_job_type: str
    suggested_price: Decimal | None = None
    confidence_score: float = Field(..., ge=0, le=1)
    ai_notes: str | None = None
    requires_review: bool


class CategorizationSummary(BaseModel):
    """Summary of categorization results."""

    total_jobs: int
    ready_to_schedule: int
    requires_review: int
    avg_confidence: float


class JobCategorizationRequest(BaseModel):
    """Request to categorize jobs."""

    job_ids: list[UUID] | None = None
    include_uncategorized_only: bool = True


class JobCategorizationResponse(BaseModel):
    """Response from job categorization."""

    categorizations: list[JobCategorization]
    summary: CategorizationSummary
    audit_log_id: UUID


# =============================================================================
# Communication Draft Schemas (Task 2.2)
# =============================================================================


class CommunicationDraft(BaseModel):
    """A drafted communication message."""

    draft_id: UUID
    customer_id: UUID
    customer_name: str
    customer_phone: str
    message_type: MessageType
    message_content: str
    ai_notes: str | None = None
    is_slow_payer: bool = False


class CommunicationDraftRequest(BaseModel):
    """Request to draft communications."""

    customer_id: UUID | None = None
    job_id: UUID | None = None
    appointment_id: UUID | None = None
    message_type: MessageType


class CommunicationDraftResponse(BaseModel):
    """Response from communication drafting."""

    draft: CommunicationDraft
    audit_log_id: UUID


# =============================================================================
# Estimate Generation Schemas (Task 2.2)
# =============================================================================


class SimilarJob(BaseModel):
    """A similar completed job for reference."""

    job_id: UUID
    job_type: str
    zone_count: int
    final_amount: Decimal
    completed_at: datetime


class EstimateBreakdown(BaseModel):
    """Breakdown of estimate components."""

    materials: Decimal
    labor: Decimal
    equipment: Decimal
    margin: Decimal
    total: Decimal


class EstimateGenerateRequest(BaseModel):
    """Request to generate an estimate."""

    job_id: UUID
    zone_count: int | None = None
    include_similar_jobs: bool = True


class EstimateGenerateResponse(BaseModel):
    """Response from estimate generation."""

    job_id: UUID
    zone_count: int
    similar_jobs: list[SimilarJob]
    breakdown: EstimateBreakdown
    recommended_price: Decimal
    ai_recommendation: str
    requires_site_visit: bool
    confidence_score: float = Field(..., ge=0, le=1)
    audit_log_id: UUID


# =============================================================================
# AI Usage and Audit Schemas (Task 2.2)
# =============================================================================


class AIUsageResponse(BaseModel):
    """Response with AI usage statistics."""

    user_id: UUID
    usage_date: date
    request_count: int
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    daily_limit: int = 100
    remaining_requests: int


class AIAuditLogEntry(BaseModel):
    """A single audit log entry."""

    id: UUID
    action_type: AIActionType
    entity_type: AIEntityType
    entity_id: UUID | None
    ai_recommendation: dict[str, Any]
    confidence_score: float | None
    user_decision: UserDecision | None
    decision_at: datetime | None
    request_tokens: int | None
    response_tokens: int | None
    estimated_cost_usd: float | None
    created_at: datetime


class AIAuditLogResponse(BaseModel):
    """Response with audit log entries."""

    entries: list[AIAuditLogEntry]
    total: int
    page: int
    page_size: int


class AIDecisionRequest(BaseModel):
    """Request to record a user decision on AI recommendation."""

    decision: UserDecision
    modified_data: dict[str, Any] | None = None


# =============================================================================
# Additional API Schemas
# =============================================================================


class ScheduleGenerationRequest(BaseModel):
    """Request to generate a schedule."""

    target_date: date
    job_ids: list[UUID] | None = None


class ScheduleGenerationResponse(BaseModel):
    """Response from schedule generation."""

    audit_id: UUID
    schedule: dict[str, Any]
    confidence_score: float
    warnings: list[str]


class CategorizationRequest(BaseModel):
    """Request to categorize a job."""

    description: str
    customer_history: list[dict[str, Any]] | None = None


class CategorizationResponse(BaseModel):
    """Response from job categorization."""

    audit_id: UUID
    category: str
    confidence_score: float
    reasoning: str
    suggested_services: list[str]
    needs_review: bool


class CommunicationDraftAPIRequest(BaseModel):
    """Request to draft a communication (API version)."""

    customer_id: UUID | None = None
    job_id: UUID | None = None
    appointment_id: UUID | None = None
    message_type: MessageType
    context: dict[str, Any] | None = None


class CommunicationDraftAPIResponse(BaseModel):
    """Response from communication drafting (API version)."""

    audit_id: UUID
    message: str
    message_type: MessageType
    character_count: int
    sms_segments: int


class EstimateRequest(BaseModel):
    """Request to generate an estimate."""

    service_type: str
    zone_count: int | None = None
    additional_items: list[dict[str, Any]] | None = None


class EstimateResponse(BaseModel):
    """Response from estimate generation."""

    audit_id: UUID
    line_items: list[dict[str, Any]]
    subtotal: float
    tax: float
    total: float
    confidence_score: float
    needs_review: bool


class BusinessQueryRequest(BaseModel):
    """Request for business query."""

    query: str
    date_range: tuple[date, date] | None = None


class BusinessQueryResponse(BaseModel):
    """Response from business query."""

    query: str
    response: str
    data_sources: list[str]


class UsageResponse(BaseModel):
    """Response with usage statistics."""

    request_count: int
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost_usd: float
    daily_limit: int
    remaining_requests: int


class AuditLogResponse(BaseModel):
    """Response with audit log entry."""

    id: UUID
    action_type: AIActionType
    entity_type: AIEntityType
    entity_id: UUID | None
    ai_recommendation: dict[str, Any]
    user_decision: UserDecision | None
    confidence_score: float | None
    created_at: datetime
    decision_at: datetime | None


class AuditDecisionRequest(BaseModel):
    """Request to record a decision."""

    decision: UserDecision
