"""
Scheduling chat session model.

Stores AI chat session context for multi-turn scheduling conversations
between users (Admin or Resource) and the AI scheduling engine.

Validates: Requirements 9.1-9.10, 14.1-14.10
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.staff import Staff


class SchedulingChatSession(Base):
    """AI scheduling chat session.

    Stores conversation history and context for multi-turn interactions
    between a user and the AI scheduling engine. Sessions are role-aware,
    routing Admin and Resource messages through different tool sets.

    Attributes:
        id: Unique identifier (UUID).
        user_id: User (staff member) in the session.
        user_role: Role of the user (admin, resource).
        messages: Conversation history (role, content, tool_calls).
        context: Session context (current schedule date, active jobs, etc.).
        is_active: Whether the session is still active.
        created_at: Session start timestamp.
        updated_at: Last message timestamp.
    """

    __tablename__ = "scheduling_chat_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Session owner
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id"),
        nullable=False,
    )
    user_role: Mapped[str] = mapped_column(String(20), nullable=False)

    # Conversation data
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )

    # Session state
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped[Staff] = relationship(
        "Staff",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<SchedulingChatSession("
            f"id={self.id}, "
            f"user_role='{self.user_role}', "
            f"is_active={self.is_active})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "user_role": self.user_role,
            "messages": self.messages,
            "context": self.context,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
