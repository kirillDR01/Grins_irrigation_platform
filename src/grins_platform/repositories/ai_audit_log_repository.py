"""AI Audit Log Repository for tracking AI recommendations and decisions.

Validates: AI Assistant Requirements 3.1, 3.2, 3.7
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.ai_audit_log import AIAuditLog
from grins_platform.schemas.ai import AIActionType, AIEntityType, UserDecision


class AIAuditLogRepository(LoggerMixin):
    """Repository for AI audit log operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        action_type: AIActionType,
        entity_type: AIEntityType,
        ai_recommendation: dict[str, Any],
        entity_id: UUID | None = None,
        confidence_score: float | None = None,
        user_id: UUID | None = None,
        request_tokens: int | None = None,
        response_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
    ) -> AIAuditLog:
        """Create a new audit log entry.

        Args:
            action_type: Type of AI action
            entity_type: Type of entity affected
            ai_recommendation: The AI's recommendation data
            entity_id: ID of the affected entity
            confidence_score: AI confidence score (0-1)
            user_id: ID of the user who triggered the action
            request_tokens: Number of input tokens used
            response_tokens: Number of output tokens used
            estimated_cost_usd: Estimated cost in USD

        Returns:
            The created audit log entry
        """
        self.log_started(
            "create_audit_log",
            action_type=action_type.value,
            entity_type=entity_type.value,
        )

        audit_log = AIAuditLog(
            action_type=action_type.value,
            entity_type=entity_type.value,
            entity_id=entity_id,
            ai_recommendation=ai_recommendation,
            confidence_score=confidence_score,
            user_id=user_id,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
            estimated_cost_usd=estimated_cost_usd,
        )

        self.session.add(audit_log)
        await self.session.flush()
        await self.session.refresh(audit_log)

        self.log_completed("create_audit_log", audit_log_id=str(audit_log.id))
        return audit_log

    async def get_by_id(self, audit_log_id: UUID) -> AIAuditLog | None:
        """Get an audit log entry by ID.

        Args:
            audit_log_id: The audit log ID

        Returns:
            The audit log entry or None if not found
        """
        self.log_started("get_audit_log", audit_log_id=str(audit_log_id))

        result = await self.session.execute(
            select(AIAuditLog).where(AIAuditLog.id == audit_log_id),
        )
        audit_log: AIAuditLog | None = result.scalar_one_or_none()

        if audit_log:
            self.log_completed("get_audit_log", found=True)
        else:
            self.log_completed("get_audit_log", found=False)

        return audit_log

    async def update_decision(
        self,
        audit_log_id: UUID,
        decision: UserDecision,
        user_id: UUID | None = None,
    ) -> AIAuditLog | None:
        """Update the user decision on an audit log entry.

        Args:
            audit_log_id: The audit log ID
            decision: The user's decision
            user_id: ID of the user making the decision

        Returns:
            The updated audit log entry or None if not found
        """
        self.log_started(
            "update_decision",
            audit_log_id=str(audit_log_id),
            decision=decision.value,
        )

        audit_log = await self.get_by_id(audit_log_id)
        if not audit_log:
            self.log_rejected("update_decision", reason="audit_log_not_found")
            return None

        audit_log.user_decision = decision.value
        audit_log.decision_at = datetime.now()
        if user_id:
            audit_log.user_id = user_id

        await self.session.flush()
        await self.session.refresh(audit_log)

        self.log_completed("update_decision", audit_log_id=str(audit_log_id))
        return audit_log

    async def list_with_filters(
        self,
        action_type: AIActionType | None = None,
        entity_type: AIEntityType | None = None,
        user_decision: UserDecision | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AIAuditLog], int]:
        """List audit log entries with optional filters.

        Args:
            action_type: Filter by action type
            entity_type: Filter by entity type
            user_decision: Filter by user decision
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of audit logs, total count)
        """
        self.log_started(
            "list_audit_logs",
            action_type=action_type.value if action_type else None,
            entity_type=entity_type.value if entity_type else None,
            limit=limit,
            offset=offset,
        )

        query = select(AIAuditLog)

        if action_type:
            query = query.where(AIAuditLog.action_type == action_type.value)
        if entity_type:
            query = query.where(AIAuditLog.entity_type == entity_type.value)
        if user_decision:
            query = query.where(AIAuditLog.user_decision == user_decision.value)

        # Get total count
        count_query = select(AIAuditLog)
        if action_type:
            count_query = count_query.where(
                AIAuditLog.action_type == action_type.value,
            )
        if entity_type:
            count_query = count_query.where(
                AIAuditLog.entity_type == entity_type.value,
            )
        if user_decision:
            count_query = count_query.where(
                AIAuditLog.user_decision == user_decision.value,
            )

        count_result = await self.session.execute(count_query)
        total = len(count_result.scalars().all())

        # Get paginated results
        query = query.order_by(AIAuditLog.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        audit_logs = list(result.scalars().all())

        self.log_completed("list_audit_logs", count=len(audit_logs), total=total)
        return audit_logs, total
