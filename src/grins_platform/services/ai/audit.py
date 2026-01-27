"""Audit Service for AI actions.

Logs all AI recommendations and user decisions for compliance.

Validates: AI Assistant Requirements 2.7, 2.8, 7.8, 7.9, 7.10
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.models.ai_audit_log import AIAuditLog
from grins_platform.repositories.ai_audit_log_repository import AIAuditLogRepository
from grins_platform.schemas.ai import AIActionType, AIEntityType, UserDecision


class AuditService(LoggerMixin):
    """Service for auditing AI actions."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.audit_repo = AIAuditLogRepository(session)

    async def log_recommendation(
        self,
        action_type: AIActionType,
        entity_type: AIEntityType,
        ai_recommendation: dict[str, Any],
        entity_id: UUID | None = None,
        confidence_score: float | None = None,
        request_tokens: int | None = None,
        response_tokens: int | None = None,
    ) -> AIAuditLog:
        """Log an AI recommendation.

        Args:
            action_type: Type of AI action
            entity_type: Type of entity affected
            ai_recommendation: The AI's recommendation
            entity_id: ID of the affected entity
            confidence_score: AI confidence score
            request_tokens: Number of input tokens
            response_tokens: Number of output tokens

        Returns:
            Created audit log entry
        """
        self.log_started(
            "log_recommendation",
            action_type=action_type.value,
            entity_type=entity_type.value,
        )

        audit_log = await self.audit_repo.create(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            ai_recommendation=ai_recommendation,
            confidence_score=confidence_score,
            request_tokens=request_tokens,
            response_tokens=response_tokens,
        )

        self.log_completed("log_recommendation", audit_id=str(audit_log.id))
        return audit_log

    async def record_decision(
        self,
        audit_id: UUID,
        decision: UserDecision,
        user_id: UUID,
    ) -> AIAuditLog | None:
        """Record user decision on AI recommendation.

        Args:
            audit_id: ID of the audit log entry
            decision: User's decision
            user_id: ID of the user making decision

        Returns:
            Updated audit log entry or None if not found
        """
        self.log_started(
            "record_decision",
            audit_id=str(audit_id),
            decision=decision.value,
        )

        audit_log = await self.audit_repo.update_decision(
            audit_id,
            decision,
            user_id,
        )

        if audit_log:
            self.log_completed("record_decision", audit_id=str(audit_id))
        else:
            self.log_rejected(
                "record_decision",
                reason="audit_log_not_found",
                audit_id=str(audit_id),
            )

        return audit_log

    async def get_audit_log(self, audit_id: UUID) -> AIAuditLog | None:
        """Get an audit log entry by ID.

        Args:
            audit_id: ID of the audit log entry

        Returns:
            Audit log entry or None if not found
        """
        return await self.audit_repo.get_by_id(audit_id)

    async def list_audit_logs(
        self,
        action_type: AIActionType | None = None,
        entity_type: AIEntityType | None = None,
        user_decision: UserDecision | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AIAuditLog], int]:
        """List audit logs with filters.

        Args:
            action_type: Filter by action type
            entity_type: Filter by entity type
            user_decision: Filter by user decision
            limit: Maximum records to return
            offset: Number of records to skip

        Returns:
            Tuple of (audit logs, total count)
        """
        self.log_started("list_audit_logs", limit=limit, offset=offset)

        results, total = await self.audit_repo.list_with_filters(
            action_type=action_type,
            entity_type=entity_type,
            user_decision=user_decision,
            limit=limit,
            offset=offset,
        )

        self.log_completed("list_audit_logs", count=len(results), total=total)
        return results, total
