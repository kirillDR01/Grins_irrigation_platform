"""AI Scheduling API endpoints.

Provides role-aware chat, schedule evaluation, and criteria configuration
endpoints for the 30-criteria AI scheduling engine.

Validates: Requirements 1.6, 1.7, 2.1-2.5, 9.1-9.10, 14.1-14.10,
           23.1, 32.7
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002 - runtime for FastAPI DI

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.scheduling_criteria_config import SchedulingCriteriaConfig
from grins_platform.schemas.ai_scheduling import (
    ChatRequest,
    ChatResponse,
    CriterionResult,
    ScheduleEvaluation,
    SchedulingConfig,
    SchedulingContext,
)
from grins_platform.services.ai.scheduling.chat_service import SchedulingChatService
from grins_platform.services.ai.scheduling.criteria_evaluator import CriteriaEvaluator
from grins_platform.services.schedule_domain import ScheduleSolution

router = APIRouter(prefix="/ai-scheduling", tags=["ai-scheduling"])


class AISchedulingEndpoints(LoggerMixin):
    """AI scheduling endpoint logger."""

    DOMAIN = "api"


_log = AISchedulingEndpoints()


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_chat_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchedulingChatService:
    """Provide a SchedulingChatService bound to the request session."""
    return SchedulingChatService(session)


async def get_criteria_evaluator(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CriteriaEvaluator:
    """Provide a CriteriaEvaluator bound to the request session."""
    return CriteriaEvaluator(session, config=SchedulingConfig())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(  # type: ignore[misc,untyped-decorator]
    "/chat",
    response_model=ChatResponse,
    summary="Role-aware AI scheduling chat",
)
async def chat(
    request: ChatRequest,
    current_user: CurrentActiveUser,
    service: Annotated[SchedulingChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Process a natural-language scheduling message.

    Routes to admin or resource handler based on the caller's role.
    Persists conversation history and writes an audit log entry.

    POST /api/v1/ai-scheduling/chat

    Validates: Requirements 1.6, 1.7, 1.8, 1.9, 2.1, 9.1-9.10, 14.1-14.10,
               32.7
    """
    _log.log_started(
        "chat",
        user_id=str(current_user.id),
        role=current_user.role,
        message_length=len(request.message),
    )

    try:
        response = await service.chat(
            user_id=current_user.id,
            role=current_user.role,
            message=request.message,
            session_id=request.session_id,
        )
    except Exception as exc:
        _log.log_failed("chat", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {exc!s}",
        ) from exc
    else:
        _log.log_completed(
            "chat",
            user_id=str(current_user.id),
            has_changes=bool(response.schedule_changes),
        )
        return response


@router.post(  # type: ignore[misc,untyped-decorator]
    "/evaluate",
    response_model=ScheduleEvaluation,
    summary="Evaluate a schedule against all 30 criteria",
)
async def evaluate_schedule(
    schedule_date: date = Query(..., description="Schedule date to evaluate"),
    current_user: CurrentActiveUser = None,  # type: ignore[assignment]  # noqa: ARG001
    evaluator: Annotated[CriteriaEvaluator, Depends(get_criteria_evaluator)] = None,  # type: ignore[assignment]
) -> ScheduleEvaluation:
    """Evaluate a schedule against all 30 criteria.

    Returns aggregate score, hard violations, per-criterion breakdown,
    and triggered alerts.

    POST /api/v1/ai-scheduling/evaluate

    Validates: Requirements 23.1, 23.2
    """
    _log.log_started("evaluate_schedule", schedule_date=str(schedule_date))

    try:
        context = SchedulingContext(schedule_date=schedule_date)
        # Build an empty solution for the given date; the evaluator will
        # load assignments from the DB via the session.
        solution = ScheduleSolution(schedule_date=schedule_date)
        result = await evaluator.evaluate_schedule(solution=solution, context=context)
    except Exception as exc:
        _log.log_failed("evaluate_schedule", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule evaluation failed: {exc!s}",
        ) from exc
    else:
        _log.log_completed(
            "evaluate_schedule",
            schedule_date=str(schedule_date),
            total_score=result.total_score,
            hard_violations=result.hard_violations,
        )
        return result


@router.get(  # type: ignore[misc,untyped-decorator]
    "/criteria",
    response_model=list[CriterionResult],
    summary="List all 30 criteria with current weights",
)
async def list_criteria(
    current_user: CurrentActiveUser,  # noqa: ARG001
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CriterionResult]:
    """Return all 30 scheduling criteria with current weights and config.

    GET /api/v1/ai-scheduling/criteria

    Validates: Requirements 23.1, 23.6
    """
    _log.log_started("list_criteria")

    try:
        stmt = select(SchedulingCriteriaConfig).order_by(
            SchedulingCriteriaConfig.criterion_number
        )
        result = await session.execute(stmt)
        configs = result.scalars().all()

        criteria: list[CriterionResult] = [
            CriterionResult(
                criterion_number=cfg.criterion_number,
                criterion_name=cfg.criterion_name,
                score=0.0,  # No assignment context — return config only
                weight=cfg.weight,
                is_hard=cfg.is_hard_constraint,
                is_satisfied=True,
                explanation=f"Group: {cfg.criterion_group}. Enabled: {cfg.is_enabled}.",
            )
            for cfg in configs
        ]
    except Exception as exc:
        _log.log_failed("list_criteria", error=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load criteria: {exc!s}",
        ) from exc
    else:
        _log.log_completed("list_criteria", count=len(criteria))
        return criteria
