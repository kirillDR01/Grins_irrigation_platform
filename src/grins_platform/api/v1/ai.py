"""AI API endpoints.

Validates: AI Assistant Requirements 15.1-15.7
"""

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.database import get_db_session as get_db
from grins_platform.schemas.ai import (
    AIActionType,
    AIChatRequest,
    AIChatResponse,
    AIEntityType,
    AuditDecisionRequest,
    AuditLogResponse,
    BusinessQueryRequest,
    BusinessQueryResponse,
    CategorizationRequest,
    CategorizationResponse,
    CommunicationDraftAPIRequest,
    CommunicationDraftAPIResponse,
    EstimateRequest,
    EstimateResponse,
    ScheduleGenerationRequest,
    ScheduleGenerationResponse,
    UsageResponse,
    UserDecision,
)
from grins_platform.services.ai.agent import AIAgentService
from grins_platform.services.ai.audit import AuditService
from grins_platform.services.ai.context.builder import ContextBuilder
from grins_platform.services.ai.rate_limiter import RateLimitError, RateLimitService
from grins_platform.services.ai.tools.categorization import CategorizationTools
from grins_platform.services.ai.tools.communication import CommunicationTools
from grins_platform.services.ai.tools.estimates import EstimateTools
from grins_platform.services.ai.tools.scheduling import SchedulingTools

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


# Placeholder user ID for demo (would come from auth in production)
DEMO_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@router.post("/chat", response_model=None)
async def chat(
    request: AIChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    stream: bool = False,
) -> StreamingResponse | AIChatResponse:
    """Chat with AI assistant.

    Args:
        request: Chat request with message and optional session_id
        db: Database session
        stream: If True, return streaming response; otherwise return JSON

    Returns:
        Streaming response or JSON response with AI reply
    """
    agent = AIAgentService(db)
    message = request.message

    if stream:
        async def generate() -> AsyncGenerator[str, None]:
            try:
                async for chunk in agent.chat_stream(DEMO_USER_ID, message):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except RateLimitError as e:
                yield f"data: ERROR: {e}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")
    # Non-streaming response
    try:
        response_text = await agent.chat(DEMO_USER_ID, message)
        return AIChatResponse(
            message=response_text,
            session_id=request.session_id or DEMO_USER_ID,
            tokens_used=len(message) // 4 + len(response_text) // 4,
            is_streaming=False,
        )
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        ) from e


@router.post("/schedule/generate", response_model=ScheduleGenerationResponse)
async def generate_schedule(
    request: ScheduleGenerationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleGenerationResponse:
    """Generate optimized schedule for a date.

    Args:
        request: Schedule generation request
        db: Database session

    Returns:
        Generated schedule for review
    """
    tools = SchedulingTools(db)
    audit = AuditService(db)

    schedule = await tools.generate_schedule(request.target_date, request.job_ids)

    # Log recommendation for audit
    audit_log = await audit.log_recommendation(
        action_type=AIActionType.SCHEDULE_GENERATION,
        entity_type=AIEntityType.SCHEDULE,
        ai_recommendation=schedule,
        confidence_score=0.85,
    )

    return ScheduleGenerationResponse(
        audit_id=audit_log.id,
        schedule=schedule,
        confidence_score=0.85,
        warnings=[],
    )


@router.post("/jobs/categorize", response_model=CategorizationResponse)
async def categorize_job(
    request: CategorizationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CategorizationResponse:
    """Categorize a job request.

    Args:
        request: Categorization request
        db: Database session

    Returns:
        Categorization result
    """
    tools = CategorizationTools(db)
    audit = AuditService(db)

    result = await tools.categorize_job(request.description)

    # Log recommendation for audit
    audit_log = await audit.log_recommendation(
        action_type=AIActionType.JOB_CATEGORIZATION,
        entity_type=AIEntityType.JOB,
        ai_recommendation=result,
        confidence_score=result["confidence"] / 100,
    )

    return CategorizationResponse(
        audit_id=audit_log.id,
        category=result["category"],
        confidence_score=result["confidence"],
        reasoning=result["reasoning"],
        suggested_services=result["suggested_services"],
        needs_review=result["needs_review"],
    )


@router.post("/communication/draft", response_model=CommunicationDraftAPIResponse)
async def draft_communication(
    request: CommunicationDraftAPIRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CommunicationDraftAPIResponse:
    """Draft a customer communication.

    Args:
        request: Communication draft request
        db: Database session

    Returns:
        Drafted message for review
    """
    tools = CommunicationTools(db)
    audit = AuditService(db)

    result = await tools.draft_message(
        message_type=request.message_type.value,
        customer_data={"first_name": "Customer"},  # Would fetch from DB
        appointment_data=request.context,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to draft message"),
        )

    # Log recommendation for audit
    audit_log = await audit.log_recommendation(
        action_type=AIActionType.COMMUNICATION_DRAFT,
        entity_type=AIEntityType.COMMUNICATION,
        ai_recommendation=result,
        confidence_score=0.9,
    )

    return CommunicationDraftAPIResponse(
        audit_id=audit_log.id,
        message=result["message"],
        message_type=request.message_type,
        character_count=result["character_count"],
        sms_segments=result["sms_segments"],
    )


@router.post("/estimate/generate", response_model=EstimateResponse)
async def generate_estimate(
    request: EstimateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EstimateResponse:
    """Generate an estimate for services.

    Args:
        request: Estimate request
        db: Database session

    Returns:
        Generated estimate for review
    """
    tools = EstimateTools(db)
    audit = AuditService(db)

    result = await tools.calculate_estimate(
        service_type=request.service_type,
        zone_count=request.zone_count or 0,
        additional_items=request.additional_items,
    )

    # Log recommendation for audit
    audit_log = await audit.log_recommendation(
        action_type=AIActionType.ESTIMATE_GENERATION,
        entity_type=AIEntityType.ESTIMATE,
        ai_recommendation=result,
        confidence_score=result["confidence"] / 100,
    )

    return EstimateResponse(
        audit_id=audit_log.id,
        line_items=result["line_items"],
        subtotal=result["subtotal"],
        tax=result["tax"],
        total=result["total"],
        confidence_score=result["confidence"],
        needs_review=result["needs_review"],
    )


@router.post("/query", response_model=BusinessQueryResponse)
async def business_query(
    request: BusinessQueryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BusinessQueryResponse:
    """Answer a business query.

    Args:
        request: Business query request
        db: Database session

    Returns:
        Query response
    """
    agent = AIAgentService(db)
    context_builder = ContextBuilder(db)

    # Build context
    context = await context_builder.build_query_context(request.query)

    # Get response
    response = await agent.chat(DEMO_USER_ID, request.query, context)

    return BusinessQueryResponse(
        query=request.query,
        response=response,
        data_sources=["customers", "jobs", "appointments"],
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UsageResponse:
    """Get AI usage statistics.

    Args:
        db: Database session

    Returns:
        Usage statistics
    """
    rate_limiter = RateLimitService(db)
    usage = await rate_limiter.get_usage(DEMO_USER_ID)

    return UsageResponse(
        request_count=int(usage["request_count"]),
        total_input_tokens=int(usage["total_input_tokens"]),
        total_output_tokens=int(usage["total_output_tokens"]),
        estimated_cost_usd=usage["estimated_cost_usd"],
        daily_limit=int(usage["daily_limit"]),
        remaining_requests=int(usage["remaining_requests"]),
    )


@router.get("/audit", response_model=list[AuditLogResponse])
async def list_audit_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    action_type: AIActionType | None = None,
    entity_type: AIEntityType | None = None,
    user_decision: UserDecision | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLogResponse]:
    """List AI audit logs.

    Args:
        db: Database session
        action_type: Filter by action type
        entity_type: Filter by entity type
        user_decision: Filter by user decision
        limit: Maximum results
        offset: Results to skip

    Returns:
        List of audit logs
    """
    audit = AuditService(db)
    logs, _total = await audit.list_audit_logs(
        action_type=action_type,
        entity_type=entity_type,
        user_decision=user_decision,
        limit=limit,
        offset=offset,
    )

    return [
        AuditLogResponse(
            id=log.id,
            action_type=AIActionType(log.action_type),
            entity_type=AIEntityType(log.entity_type),
            entity_id=log.entity_id,
            ai_recommendation=log.ai_recommendation,
            user_decision=(
                UserDecision(log.user_decision) if log.user_decision else None
            ),
            confidence_score=log.confidence_score,
            created_at=log.created_at,
            decision_at=log.decision_at,
        )
        for log in logs
    ]


@router.post("/audit/{audit_id}/decision", response_model=AuditLogResponse)
async def record_decision(
    audit_id: UUID,
    request: AuditDecisionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditLogResponse:
    """Record user decision on AI recommendation.

    Args:
        audit_id: Audit log ID
        request: Decision request
        db: Database session

    Returns:
        Updated audit log
    """
    audit = AuditService(db)
    log = await audit.record_decision(audit_id, request.decision, DEMO_USER_ID)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )

    return AuditLogResponse(
        id=log.id,
        action_type=AIActionType(log.action_type),
        entity_type=AIEntityType(log.entity_type),
        entity_id=log.entity_id,
        ai_recommendation=log.ai_recommendation,
        user_decision=UserDecision(log.user_decision) if log.user_decision else None,
        confidence_score=log.confidence_score,
        created_at=log.created_at,
        decision_at=log.decision_at,
    )
