"""Chat session management for AI assistant."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from grins_platform.log_config import LoggerMixin  # type: ignore[import-untyped]


class ChatMessage:
    """Represents a single message in a chat session."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime | None = None,
    ) -> None:
        """Initialize a chat message.

        Args:
            role: Message role (user or assistant)
            content: Message content
            timestamp: Message timestamp (defaults to now)
        """
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


class ChatSession(LoggerMixin):  # type: ignore[misc]
    """Manages chat session history with message limit enforcement."""

    DOMAIN = "ai"
    MAX_MESSAGES = 50

    def __init__(self, session_id: UUID | None = None) -> None:
        """Initialize a chat session.

        Args:
            session_id: Optional session ID (generates new if not provided)
        """
        super().__init__()
        self.session_id = session_id or uuid4()
        self.messages: list[ChatMessage] = []
        self.created_at = datetime.now(UTC)
        self.log_started("session_created", session_id=str(self.session_id))  # type: ignore[attr-defined]

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session.

        Enforces 50 message limit by removing oldest messages.

        Args:
            role: Message role (user or assistant)
            content: Message content
        """
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)

        # Enforce message limit
        if len(self.messages) > self.MAX_MESSAGES:
            removed = self.messages.pop(0)
            self.log_validated(  # type: ignore[attr-defined]
                "message_limit_enforced",
                session_id=str(self.session_id),
                removed_timestamp=removed.timestamp.isoformat(),
                current_count=len(self.messages),
            )

        self.log_completed(  # type: ignore[attr-defined]
            "message_added",
            session_id=str(self.session_id),
            role=role,
            message_count=len(self.messages),
        )

    def clear(self) -> None:
        """Clear all messages from the session."""
        message_count = len(self.messages)
        self.messages.clear()
        self.log_completed(  # type: ignore[attr-defined]
            "session_cleared",
            session_id=str(self.session_id),
            cleared_count=message_count,
        )

    def get_message_count(self) -> int:
        """Get the current number of messages in the session.

        Returns:
            Number of messages
        """
        return len(self.messages)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages as dictionaries.

        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self.messages]

    def get_context_messages(self) -> list[dict[str, str]]:
        """Get messages formatted for AI context.

        Returns:
            List of messages with role and content
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
