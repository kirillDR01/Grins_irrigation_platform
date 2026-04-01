"""
SchedulingChatSession model for AI chat session management.

This module defines the SchedulingChatSession SQLAlchemy model representing
AI chat session context for multi-turn scheduling conversations.

Validates: Requirements 1.6, 1.7, 21.1-21.4
"""

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
    """SchedulingChatSession model representing an AI chat session.

    Attributes:
        id: Unique identifier for the chat session
        user_id: User in the session
        user_role: Role of the user (admin, resource)
        messages: Conversation history (role, content, tool_calls)
        context: Session context (current schedule date, active jobs, etc.)
        is_active: Whether the session is still active
        created_at: Session start timestamp
        updated_at: Last message timestamp

    Validates: Requirements 1.6, 1.7, 21.1-21.4
    """

    __tablename__ = "scheduling_chat_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Session details
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_role: Mapped[str] = mapped_column(String(20), nullable=False)
    messages: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True,
    )
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["Staff"] = relationship(
        "Staff",
        foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        """Return string representation of the chat session."""
        return (
            f"<SchedulingChatSession(id={self.id}, user_id={self.user_id}, "
            f"role='{self.user_role}', active={self.is_active})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the chat session to a dictionary.

        Returns:
            Dictionary representation of the chat session.
        """
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
