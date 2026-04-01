"""
AI scheduling API endpoints.

Provides role-aware AI chat, 30-criteria schedule evaluation,
and criteria configuration listing.

Validates: Requirements 1.6, 1.7, 2.1-2.5, 9.1-9.10, 14.1-14.10, 23.1, 32.7
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_criteria_config import SchedulingCriteriaConfig
from grins_platform.schemas.ai_scheduling import (
    ChatRequest,
    ChatResponse,
    ScheduleEvaluation,
)
from grins_platform.services.ai.scheduling.chat_service import (
    SchedulingChatService,
)
from grins_platform.services.ai.scheduling.criteria_evaluator import (
    CriteriaEvaluator,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/ai-scheduling", tags=["ai-scheduling"])


class AISchedulingEndpoints(LoggerMixin):
    """AI scheduling endpoints."""

    DOMAIN = "api"


endpoints = AISchedulingEndpoints()


@router.post(  # type: ignore[misc,untyped-decorator]
    "/chat",
    response_model=ChatResponse,
)
async def ai_scheduling_chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    role: str = Query(
        default="admin",
        description="User role: 'admin' or 'resource'",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> ChatResponse:
    """Role-aware AI scheduling chat.

    Accepts a natural-language message and routes it through the
    SchedulingChatService based on the caller's role (admin or resource).

    POST /api/v1/ai-scheduling/chat

    Validates: Requirements 1.6, 1.7, 2.1-2.5, 9.1-9.10, 14.1-14.10
    """
    endpoints.log_started(
        "ai_scheduling_chat",
        user_id=str(current_user.id),
        role=role,
    )

    try:
        service = SchedulingChatService(session)
        response = await service.chat(
            user_id=current_user.id,
            role=role,
            message=request.message,
            session_id=(
                request.session_id
                or UUID("00000000-0000-0000-0000-000000000000")
            ),
        )
    except Exception as e:
        endpoints.log_failed("ai_scheduling_chat", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI scheduling chat failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed("ai_scheduling_chat", user_id=str(current_user.id))
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/evaluate",
    response_model=ScheduleEvaluation,
)
async def evaluate_schedule(
    current_user: CurrentActiveUser,
    schedule_date: date = Query(..., description="Date of the schedule to evaluate"),
    session: AsyncSession = Depends(get_db_session),
) -> ScheduleEvaluation:
    """Evaluate a schedule against all 30 criteria.

    Returns a full ScheduleEvaluation with per-criterion scores,
    aggregate totals, hard-constraint violations, and generated alerts.

    POST /api/v1/ai-scheduling/evaluate

    Validates: Requirements 23.1, 23.2
    """
    endpoints.log_started(
        "evaluate_schedule",
        schedule_date=str(schedule_date),
        user_id=str(current_user.id),
    )

    try:
        evaluator = CriteriaEvaluator(session=session, config=None)
        evaluation = await evaluator.evaluate_schedule(
            solution=None,
            context=None,
            schedule_date=schedule_date,
        )
    except Exception as e:
        endpoints.log_failed("evaluate_schedule", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule evaluation failed: {e!s}",
        ) from e
    else:
        endpoints.log_completed(
            "evaluate_schedule",
            total_score=evaluation.total_score,
            hard_violations=evaluation.hard_violations,
        )
        return evaluation


@router.get(  # type: ignore[misc,untyped-decorator]
    "/criteria",
    response_model=list[dict[str, Any]],
)
async def list_criteria(
    current_user: CurrentActiveUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, Any]]:
    """List all 30 scheduling criteria with current weights.

    Returns the full criteria configuration from the database including
    criterion number, name, group, weight, hard/soft classification,
    and enabled status.

    GET /api/v1/ai-scheduling/criteria

    Validates: Requirement 23.1
    """
    endpoints.log_started("list_criteria", user_id=str(current_user.id))

    try:
        stmt = (
            select(SchedulingCriteriaConfig)
            .order_by(SchedulingCriteriaConfig.criterion_number)
        )
        result = await session.execute(stmt)
        criteria = result.scalars().all()
        criteria_list = [c.to_dict() for c in criteria]
    except Exception as e:
        endpoints.log_failed("list_criteria", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list criteria: {e!s}",
        ) from e
    else:
        endpoints.log_completed("list_criteria", count=len(criteria_list))
        return criteria_list
