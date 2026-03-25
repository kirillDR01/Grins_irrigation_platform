"""AuditService for tracking administrative actions.

Provides log_action() to create audit log entries and get_audit_log()
for paginated, filterable retrieval.

Validates: CRM Gap Closure Req 74.1, 74.2, 74.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.audit_log_repository import AuditLogRepository
from grins_platform.schemas.audit import AuditLogFilters, AuditLogResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.audit_log import AuditLog


class AuditService(LoggerMixin):
    """Service for audit log management.

    Called by other services at the point of auditable actions.
    A FastAPI dependency extracts ip_address and user_agent from
    the request and passes them through.

    Validates: CRM Gap Closure Req 74.1, 74.2, 74.3
    """

    DOMAIN = "audit"

    async def log_action(
        self,
        db: AsyncSession,
        *,
        actor_id: UUID | None = None,
        actor_role: str | None = None,
        action: str,
        resource_type: str,
        resource_id: UUID | str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry for an administrative action.

        Args:
            db: Database session.
            actor_id: Staff UUID who performed the action.
            actor_role: Role of the actor (e.g. "admin", "staff").
            action: Action performed (e.g. "customer.merge").
            resource_type: Resource type affected (e.g. "customer").
            resource_id: Resource UUID.
            details: Additional event details (JSONB).
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            Created AuditLog instance.

        Validates: Req 74.1, 74.2
        """
        self.log_started(
            "log_action",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )

        repo = AuditLogRepository(db)
        entry = await repo.create(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            actor_id=actor_id,
            actor_role=actor_role,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.log_completed(
            "log_action",
            audit_log_id=str(entry.id),
            action=action,
        )
        return entry

    async def get_audit_log(
        self,
        db: AsyncSession,
        filters: AuditLogFilters,
    ) -> dict[str, Any]:
        """Retrieve paginated, filterable audit log entries.

        Args:
            db: Database session.
            filters: AuditLogFilters with page, page_size, and optional filters.

        Returns:
            Dict with items (list of AuditLogResponse), total, page, page_size.

        Validates: Req 74.3
        """
        self.log_started(
            "get_audit_log",
            page=filters.page,
            page_size=filters.page_size,
        )

        repo = AuditLogRepository(db)
        entries, total = await repo.list_with_filters(filters)

        items = [AuditLogResponse.model_validate(e) for e in entries]

        self.log_completed(
            "get_audit_log",
            count=len(items),
            total=total,
        )
        return {
            "items": items,
            "total": total,
            "page": filters.page,
            "page_size": filters.page_size,
        }
