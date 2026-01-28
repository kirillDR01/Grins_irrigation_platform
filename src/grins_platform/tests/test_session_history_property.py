"""Property test for session history limit enforcement.

Property 12: Session History Limit
- Sessions must enforce a 50 message limit
- When limit is exceeded, oldest messages are removed
- Message count never exceeds 50

Validates: Requirements 8.9, 13.2
"""

import pytest
from hypothesis import (
    given,
    strategies as st,
)

from grins_platform.services.ai.session import ChatSession


@pytest.mark.unit
class TestSessionHistoryLimitProperty:
    """Property tests for session history limit enforcement."""

    @given(
        message_count=st.integers(min_value=1, max_value=100),
    )
    def test_session_never_exceeds_limit(self, message_count: int) -> None:
        """Property: Session message count never exceeds 50.

        Args:
            message_count: Number of messages to add
        """
        session = ChatSession()

        # Add messages
        for i in range(message_count):
            role = "user" if i % 2 == 0 else "assistant"
            session.add_message(role=role, content=f"Message {i}")

        # Verify limit enforced
        assert session.get_message_count() <= ChatSession.MAX_MESSAGES
        assert len(session.messages) <= ChatSession.MAX_MESSAGES

    @given(
        message_count=st.integers(min_value=51, max_value=100),
    )
    def test_oldest_messages_removed_when_limit_exceeded(
        self,
        message_count: int,
    ) -> None:
        """Property: Oldest messages are removed when limit exceeded.

        Args:
            message_count: Number of messages to add (> 50)
        """
        session = ChatSession()

        # Add messages with unique content
        for i in range(message_count):
            role = "user" if i % 2 == 0 else "assistant"
            session.add_message(role=role, content=f"Message {i}")

        # Verify only most recent 50 messages remain
        messages = session.get_messages()
        assert len(messages) == ChatSession.MAX_MESSAGES

        # Verify oldest messages were removed
        first_message_content = messages[0]["content"]
        expected_first_index = message_count - ChatSession.MAX_MESSAGES
        assert first_message_content == f"Message {expected_first_index}"

        # Verify newest message is last
        last_message_content = messages[-1]["content"]
        assert last_message_content == f"Message {message_count - 1}"

    def test_clear_removes_all_messages(self) -> None:
        """Property: Clear removes all messages."""
        session = ChatSession()

        # Add messages
        for i in range(30):
            session.add_message(role="user", content=f"Message {i}")

        assert session.get_message_count() == 30

        # Clear session
        session.clear()

        # Verify all messages removed
        assert session.get_message_count() == 0
        assert len(session.messages) == 0
        assert len(session.get_messages()) == 0

    @given(
        message_count=st.integers(min_value=1, max_value=50),
    )
    def test_message_count_accurate_below_limit(self, message_count: int) -> None:
        """Property: Message count is accurate when below limit.

        Args:
            message_count: Number of messages to add (<= 50)
        """
        session = ChatSession()

        # Add messages
        for i in range(message_count):
            session.add_message(role="user", content=f"Message {i}")

        # Verify count matches
        assert session.get_message_count() == message_count
        assert len(session.messages) == message_count
        assert len(session.get_messages()) == message_count
