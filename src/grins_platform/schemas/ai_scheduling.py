"""AI Scheduling Pydantic schemas for request/response validation.

This module defines all Pydantic schemas for the AI-powered scheduling system,
including criteria evaluation, chat, alerts, change requests, pre-job checklists,
batch scheduling, utilization reports, and configuration.

Note: General AI schemas (AIChatRequest, ScheduleGenerateRequest, etc.) live in
``schemas/ai.py``. This file is specifically for the 30-criteria AI scheduling
engine endpoints.

Validates: Requirements 1.1-1.9, 2.1-2.5, 9.1-9.10, 10.1-10.10, 11.1-11.5,
           12.1-12.5, 14.1-14.10, 15.1-15.10, 23.1
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# =============================================================================
# Criteria and Evaluation
# =============================================================================


class CriterionResult(BaseModel):
    """Result of evaluating a single scheduling criterion.

    Each of the 30 criteria produces one of these, containing the raw score,
    weight, hard/soft classification, satisfaction flag, and a human-readable
    explanation of how the score was derived.
    """

    criterion_number: int = Field(
        ...,
        description="Criterion number (1-30)",
    )
    criterion_name: str = Field(
        ...,
        description="Human-readable criterion name",
    )
    score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Criterion score (0-100)",
    )
    weight: int = Field(
        ...,
        description="Relative weight of this criterion (0-100)",
    )
    is_hard: bool = Field(
        ...,
        description="True if this is a hard constraint that must be satisfied",
    )
    is_satisfied: bool = Field(
        ...,
        description=(
            "Whether the criterion is satisfied (relevant for hard constraints)"
        ),
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the score",
    )


class CriteriaScore(BaseModel):
    """Aggregate score from evaluating all criteria for a single assignment.

    Returned by ``CriteriaEvaluator.evaluate_assignment`` to summarise the
    weighted composite score and any hard-constraint violations.
    """

    total_score: float = Field(
        ...,
        description="Weighted composite score across all evaluated criteria",
    )
    hard_violations: int = Field(
        ...,
        description="Number of hard constraints violated",
    )
    criteria_scores: list[CriterionResult] = Field(
        default_factory=list,
        description="Per-criterion breakdown",
    )


class ScheduleEvaluation(BaseModel):
    """Evaluation of an entire schedule against all 30 criteria.

    Returned by ``CriteriaEvaluator.evaluate_schedule`` with aggregate metrics
    and any alerts triggered by violations or optimization opportunities.
    """

    schedule_date: date = Field(
        ...,
        description="Date of the evaluated schedule",
    )
    total_score: float = Field(
        ...,
        description="Aggregate weighted score for the full schedule",
    )
    hard_violations: int = Field(
        ...,
        description="Total hard-constraint violations across all assignments",
    )
    criteria_scores: list[CriterionResult] = Field(
        default_factory=list,
        description="Per-criterion breakdown aggregated across assignments",
    )
    alerts: list[str] = Field(
        default_factory=list,
        description=(
            "Alert messages triggered by violations or optimization opportunities"
        ),
    )


class RankedCandidate(BaseModel):
    """A staff candidate ranked by composite criteria score for a job.

    Returned by ``CriteriaEvaluator.rank_candidates`` to show the best-fit
    resources for a given job with per-criterion breakdown.
    """

    staff_id: UUID = Field(
        ...,
        description="Staff member UUID",
    )
    name: str = Field(
        ...,
        description="Staff member display name",
    )
    composite_score: float = Field(
        ...,
        description="Weighted composite score across all criteria",
    )
    criterion_breakdown: list[CriterionResult] = Field(
        default_factory=list,
        description="Per-criterion score breakdown for this candidate",
    )


# =============================================================================
# Chat
# =============================================================================


class ScheduleChange(BaseModel):
    """A single schedule modification proposed or executed by the AI chat.

    Embedded in ``ChatResponse`` to describe what changed (or would change)
    in the schedule as a result of the user's chat command.
    """

    change_type: str = Field(
        ...,
        description="Type of change (e.g. 'move', 'add', 'remove', 'swap')",
    )
    job_id: UUID | None = Field(
        default=None,
        description="Affected job UUID",
    )
    staff_id: UUID | None = Field(
        default=None,
        description="Affected staff UUID",
    )
    old_slot: str | None = Field(
        default=None,
        description="Previous time slot or assignment description",
    )
    new_slot: str | None = Field(
        default=None,
        description="New time slot or assignment description",
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of the change",
    )


class ChatRequest(BaseModel):
    """Request payload for the AI scheduling chat endpoint.

    Validates: Requirements 1.6, 1.7, 1.8, 2.1
    """

    message: str = Field(
        ...,
        min_length=1,
        description="User's natural-language message",
    )
    session_id: UUID | None = Field(
        default=None,
        description="Existing chat session ID for multi-turn conversations",
    )


class CriterionUsage(BaseModel):
    """A single criterion that influenced an AI chat response.

    Used by ``ChatResponse.criteria_used`` to surface which of the 30 scheduling
    criteria drove the AI's reasoning, so the UI can render badges that link the
    response back to the rules in play.
    """

    number: int = Field(
        ...,
        ge=1,
        le=30,
        description="Criterion number (1-30)",
    )
    name: str = Field(
        ...,
        description="Human-readable criterion name",
    )


class ChatResponse(BaseModel):
    """Response from the AI scheduling chat endpoint.

    Contains the AI's text response plus optional structured data: schedule
    changes, clarifying questions, or a change-request ID for resource
    escalation workflows.

    Validates: Requirements 1.8, 1.9, 2.2
    """

    response: str = Field(
        ...,
        description="AI-generated text response",
    )
    schedule_changes: list[ScheduleChange] | None = Field(
        default=None,
        description="Schedule modifications proposed or executed",
    )
    clarifying_questions: list[str] | None = Field(
        default=None,
        description="Follow-up questions the AI needs answered",
    )
    change_request_id: UUID | None = Field(
        default=None,
        description="Change request ID if escalated for admin approval",
    )
    session_id: UUID | None = Field(
        default=None,
        description=(
            "Persistent session id for multi-turn conversations; clients should "
            "echo this back on the next ``ChatRequest`` to continue the same thread"
        ),
    )
    criteria_used: list[CriterionUsage] | None = Field(
        default=None,
        description=(
            "Subset of the 30 scheduling criteria that drove this response "
            "(emitted only when the response is grounded in evaluator output)"
        ),
    )
    schedule_summary: str | None = Field(
        default=None,
        description=(
            "Inline schedule summary string, e.g. 'Mon: 10 jobs, Tue: 8 jobs'; "
            "populated when a tool call returned a ``ScheduleSolution``"
        ),
    )


# =============================================================================
# Alerts
# =============================================================================


class ResolutionOption(BaseModel):
    """A single resolution action available for an alert.

    Each alert may offer one or more resolution options that the admin can
    execute with a single click from the Alerts Panel.
    """

    action: str = Field(
        ...,
        description=(
            "Machine-readable action identifier (e.g. 'swap_resources', 'reschedule')"
        ),
    )
    label: str = Field(
        ...,
        description="Human-readable button label",
    )
    description: str = Field(
        ...,
        description="Detailed description of what this action will do",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Action-specific parameters",
    )


class SchedulingAlertResponse(BaseModel):
    """Response schema for a scheduling alert or suggestion.

    Validates: Requirements 11.1-11.5, 12.1-12.5
    """

    id: UUID = Field(
        ...,
        description="Alert UUID",
    )
    alert_type: str = Field(
        ...,
        description=(
            "Alert type (e.g. 'double_booking', 'skill_mismatch', 'route_swap')"
        ),
    )
    severity: str = Field(
        ...,
        description=(
            "Severity level ('critical' for red alerts, 'suggestion' for green)"
        ),
    )
    title: str = Field(
        ...,
        description="Short display title",
    )
    description: str | None = Field(
        default=None,
        description="Detailed description of the alert",
    )
    affected_job_ids: list[UUID] | None = Field(
        default=None,
        description="UUIDs of affected jobs",
    )
    affected_staff_ids: list[UUID] | None = Field(
        default=None,
        description="UUIDs of affected staff members",
    )
    criteria_triggered: list[int] | None = Field(
        default=None,
        description="Criterion numbers (1-30) that triggered this alert",
    )
    resolution_options: list[ResolutionOption] | None = Field(
        default=None,
        description="Available one-click resolution actions",
    )
    status: str = Field(
        ...,
        description="Alert status ('active', 'resolved', 'dismissed', 'expired')",
    )
    schedule_date: date | None = Field(
        default=None,
        description="Schedule date this alert pertains to",
    )
    created_at: datetime = Field(
        ...,
        description="When the alert was created",
    )


class ResolveAlertRequest(BaseModel):
    """Request to resolve a scheduling alert with a chosen action.

    Validates: Requirement 11.1
    """

    action: str = Field(
        ...,
        description=(
            "Resolution action identifier (must match a ResolutionOption.action)"
        ),
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Action-specific parameters",
    )


class DismissAlertRequest(BaseModel):
    """Request to dismiss a scheduling suggestion.

    Validates: Requirement 12.1
    """

    reason: str | None = Field(
        default=None,
        description="Optional reason for dismissing the suggestion",
    )


class AlertCandidate(BaseModel):
    """Internal schema for an alert candidate before persistence.

    Used by ``AlertEngine`` detectors and suggestion generators to produce
    candidate alerts that are then deduplicated and persisted.
    """

    alert_type: str = Field(
        ...,
        description="Alert type identifier",
    )
    severity: str = Field(
        ...,
        description="Severity level ('critical' or 'suggestion')",
    )
    title: str = Field(
        ...,
        description="Short display title",
    )
    description: str = Field(
        ...,
        description="Detailed description",
    )
    affected_job_ids: list[UUID] | None = Field(
        default=None,
        description="UUIDs of affected jobs",
    )
    affected_staff_ids: list[UUID] | None = Field(
        default=None,
        description="UUIDs of affected staff members",
    )
    criteria_triggered: list[int] | None = Field(
        default=None,
        description="Criterion numbers that triggered this alert",
    )
    resolution_options: list[ResolutionOption] | None = Field(
        default=None,
        description="Available resolution actions",
    )


# =============================================================================
# Change Requests
# =============================================================================


class ChangeRequestResponse(BaseModel):
    """Response schema for a resource-initiated change request.

    Validates: Requirements 14.3, 14.4, 14.6, 14.7, 14.10
    """

    id: UUID = Field(
        ...,
        description="Change request UUID",
    )
    resource_id: UUID = Field(
        ...,
        description="Resource (staff) who initiated the request",
    )
    request_type: str = Field(
        ...,
        description=(
            "Request type (e.g. 'delay_report', 'followup_job', 'resequence')"
        ),
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Request-specific details (field notes, parts list, etc.)",
    )
    affected_job_id: UUID | None = Field(
        default=None,
        description="Primary job affected by this request",
    )
    recommended_action: str | None = Field(
        default=None,
        description="AI's recommended resolution for this request",
    )
    status: str = Field(
        ...,
        description="Request status ('pending', 'approved', 'denied', 'expired')",
    )
    created_at: datetime = Field(
        ...,
        description="When the request was created",
    )


class ApproveChangeRequest(BaseModel):
    """Request to approve a resource change request.

    Validates: Requirement 2.4
    """

    admin_notes: str | None = Field(
        default=None,
        description="Optional admin notes on the approval decision",
    )


class DenyChangeRequest(BaseModel):
    """Request to deny a resource change request with a reason.

    Validates: Requirement 2.4
    """

    reason: str = Field(
        ...,
        description="Reason for denying the change request",
    )


# =============================================================================
# Pre-Job and Upsell
# =============================================================================


class PreJobChecklist(BaseModel):
    """Pre-job requirements checklist generated for a resource.

    Contains everything the resource needs to know before arriving at the
    job site: job type, customer info, equipment, known issues, access
    details, and estimated duration.

    Validates: Requirements 2.3, 14.2, 15.2
    """

    job_type: str = Field(
        ...,
        description="Type of job (e.g. 'Spring Opening', 'Maintenance')",
    )
    customer_name: str = Field(
        ...,
        description="Customer display name",
    )
    customer_address: str = Field(
        ...,
        description="Job site address",
    )
    required_equipment: list[str] = Field(
        default_factory=list,
        description="Equipment the resource must have on truck",
    )
    known_issues: list[str] = Field(
        default_factory=list,
        description="Known system issues or customer concerns",
    )
    gate_code: str | None = Field(
        default=None,
        description="Gate or access code for the property",
    )
    special_instructions: str | None = Field(
        default=None,
        description="Special instructions (e.g. pet warnings, HOA rules)",
    )
    estimated_duration: int = Field(
        ...,
        description="Estimated job duration in minutes",
    )


class UpsellSuggestion(BaseModel):
    """AI-generated upsell opportunity for a resource at a job site.

    Based on customer equipment age and service history, suggests upgrades
    the resource can propose on-site.

    Validates: Requirements 17.1, 17.2
    """

    equipment_name: str = Field(
        ...,
        description="Name of the equipment to consider upgrading",
    )
    age_years: float = Field(
        ...,
        description="Age of the equipment in years",
    )
    repair_count: int = Field(
        ...,
        description="Number of repairs on this equipment",
    )
    recommended_upgrade: str = Field(
        ...,
        description="Recommended upgrade or replacement",
    )
    estimated_savings: float = Field(
        ...,
        description="Estimated annual savings from the upgrade",
    )


# =============================================================================
# Batch and Reports
# =============================================================================


class BatchScheduleRequest(BaseModel):
    """Request for batch schedule generation across multiple weeks.

    Validates: Requirement 9.7
    """

    job_type: str | None = Field(
        default=None,
        description="Filter by job type (e.g. 'Spring Opening')",
    )
    customer_count: int | None = Field(
        default=None,
        description="Target number of customers to schedule",
    )
    weeks: int = Field(
        default=1,
        description="Number of weeks to schedule",
    )
    zone_priority: list[str] | None = Field(
        default=None,
        description="Ordered list of zone names to prioritise",
    )
    preferences: dict[str, Any] | None = Field(
        default=None,
        description="Additional scheduling preferences",
    )


class BatchScheduleResponse(BaseModel):
    """Response from batch schedule generation.

    Validates: Requirement 10.7
    """

    schedule_id: UUID | None = Field(
        default=None,
        description="Generated schedule UUID",
    )
    weeks_scheduled: int = Field(
        ...,
        description="Number of weeks actually scheduled",
    )
    total_jobs: int = Field(
        ...,
        description="Total jobs scheduled across all weeks",
    )
    jobs_by_week: dict[str, int] = Field(
        default_factory=dict,
        description="Job count per week (ISO week string to count)",
    )
    capacity_utilization: dict[str, float] = Field(
        default_factory=dict,
        description="Utilization pct per week (ISO week string to pct)",
    )


class ResourceUtilization(BaseModel):
    """Utilization metrics for a single resource on a given day."""

    staff_id: UUID = Field(
        ...,
        description="Staff member UUID",
    )
    name: str = Field(
        ...,
        description="Staff member display name",
    )
    total_minutes: int = Field(
        ...,
        description="Total available minutes in the shift",
    )
    assigned_minutes: int = Field(
        ...,
        description="Minutes assigned to jobs",
    )
    drive_minutes: int = Field(
        ...,
        description="Minutes spent driving between jobs",
    )
    utilization_pct: float = Field(
        ...,
        description="Utilization pct ((assigned + drive) / total * 100)",
    )


class UtilizationReport(BaseModel):
    """Resource utilization report for a schedule date.

    Validates: Requirement 6.1
    """

    schedule_date: date = Field(
        ...,
        description="Date of the utilization report",
    )
    resources: list[ResourceUtilization] = Field(
        default_factory=list,
        description="Per-resource utilization breakdown",
    )


class CapacityForecast(BaseModel):
    """Capacity forecast for a schedule date.

    Validates: Requirements 6.2, 9.4
    """

    schedule_date: date = Field(
        ...,
        description="Forecast date",
    )
    total_capacity_minutes: int = Field(
        ...,
        description="Total available capacity in minutes across all resources",
    )
    assigned_minutes: int = Field(
        ...,
        description="Minutes already assigned to jobs",
    )
    utilization_pct: float = Field(
        ...,
        description="Current utilization percentage",
    )
    criteria_analysis: dict[str, Any] | None = Field(
        default=None,
        description="30-criteria analysis overlay (per-criterion data)",
    )
    forecast_confidence: float | None = Field(
        default=None,
        description="Confidence score for the forecast (0.0-1.0)",
    )


# =============================================================================
# Configuration and Context
# =============================================================================


class SchedulingConfig(BaseModel):
    """Runtime configuration for the AI scheduling engine.

    Allows overriding criteria weights and thresholds without code changes.
    Loaded from the ``scheduling_criteria_config`` table.
    """

    criteria_weights: dict[int, int] | None = Field(
        default=None,
        description="Override weights by criterion number (1-30 to 0-100)",
    )
    thresholds: dict[str, Any] | None = Field(
        default=None,
        description="Threshold overrides (e.g. overbooking_pct)",
    )


class SchedulingContext(BaseModel):
    """Contextual data passed to the criteria evaluator for a scheduling run.

    Bundles the schedule date with external signals (weather, traffic, backlog)
    so scorers can incorporate real-time conditions.
    """

    schedule_date: date = Field(
        ...,
        description="Target schedule date",
    )
    weather: dict[str, Any] | None = Field(
        default=None,
        description="Weather forecast data for the schedule date",
    )
    traffic: dict[str, Any] | None = Field(
        default=None,
        description="Real-time traffic conditions",
    )
    backlog: dict[str, Any] | None = Field(
        default=None,
        description="Current job backlog and pipeline pressure data",
    )
