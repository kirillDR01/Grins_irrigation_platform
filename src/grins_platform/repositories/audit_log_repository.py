"""Audit log repository for database operations.

Create entry + paginated filtered query.

Validates: CRM Gap Closure Req 74.3
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.audit_log import AuditLog

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.schemas.audit import AuditLogFilters


class AuditLogRepository(LoggerMixin):
    """Repository for audit log database operations.

    Validates: CRM Gap Closure Req 74.3
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: UUID | None = None,
        actor_role: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create a new audit log entry.

        Args:
            action: Action performed (e.g. "customer.merge")
            resource_type: Resource type affected (e.g. "customer")
            resource_id: Resource UUID as string
            actor_id: Staff UUID who performed the action
            actor_role: Role of the actor
            details: Additional event details (JSONB)
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog instance

        Validates: CRM Gap Closure Req 74.3
        """
        self.log_started("create", action=action, resource_type=resource_type)

        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_id=actor_id,
            actor_role=actor_role,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)

        self.log_completed("create", audit_log_id=str(entry.id))
        return entry

    async def get_by_id(self, entry_id: UUID) -> AuditLog | None:
        """Get an audit log entry by ID.

        Args:
            entry_id: AuditLog UUID

        Returns:
            AuditLog instance or None if not found
        """
        self.log_started("get_by_id", entry_id=str(entry_id))

        stmt = select(AuditLog).where(AuditLog.id == entry_id)
        result = await self.session.execute(stmt)
        entry: AuditLog | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=entry is not None)
        return entry

    async def list_with_filters(
        self,
        filters: AuditLogFilters,
    ) -> tuple[list[AuditLog], int]:
        """List audit log entries with filtering and pagination.

        Args:
            filters: AuditLogFilters with page, page_size, and optional filters

        Returns:
            Tuple of (list of audit log entries, total count)

        Validates: CRM Gap Closure Req 74.3
        """
        self.log_started(
            "list_with_filters",
            page=filters.page,
            page_size=filters.page_size,
        )

        base_query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if filters.actor_id is not None:
            base_query = base_query.where(AuditLog.actor_id == filters.actor_id)
            count_query = count_query.where(AuditLog.actor_id == filters.actor_id)

        if filters.action is not None:
            base_query = base_query.where(AuditLog.action == filters.action)
            count_query = count_query.where(AuditLog.action == filters.action)

        if filters.resource_type is not None:
            base_query = base_query.where(
                AuditLog.resource_type == filters.resource_type,
            )
            count_query = count_query.where(
                AuditLog.resource_type == filters.resource_type,
            )

        if filters.date_from is not None:
            base_query = base_query.where(AuditLog.created_at >= filters.date_from)
            count_query = count_query.where(AuditLog.created_at >= filters.date_from)

        if filters.date_to is not None:
            base_query = base_query.where(AuditLog.created_at <= filters.date_to)
            count_query = count_query.where(AuditLog.created_at <= filters.date_to)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (filters.page - 1) * filters.page_size
        stmt = (
            base_query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(filters.page_size)
        )

        result = await self.session.execute(stmt)
        entries = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(entries), total=total)
        return entries, total
