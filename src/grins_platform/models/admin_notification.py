"""AdminNotification model for the in-app admin notifications inbox.

Backs the top-nav bell + dropdown surfaced to admin users so missed
estimate decisions, appointment cancellations, and late reschedule
attempts never get lost when an SMS is deleted or an email is missed.

Validates: Cluster H §5 (in-app notifications inbox).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class AdminNotification(Base):
    """Admin in-app notification row.

    Polymorphic `subject_resource_type` + `subject_resource_id` keeps the
    door open for future resource types (job, invoice, lead) without a
    schema change. No FK on `subject_resource_id` — mirrors
    :attr:`Alert.entity_id` and :attr:`AuditLog.resource_id`.

    Validates: Cluster H §5.
    """

    __tablename__ = "admin_notifications"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_resource_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(280), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    actor: Mapped[Staff | None] = relationship("Staff", lazy="selectin")

    __table_args__ = (
        Index("ix_admin_notifications_read_created", "read_at", "created_at"),
        Index("ix_admin_notifications_event_type", "event_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<AdminNotification(id={self.id}, event_type='{self.event_type}', "
            f"subject={self.subject_resource_type}:{self.subject_resource_id})>"
        )
