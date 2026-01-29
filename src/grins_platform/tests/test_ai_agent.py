"""Tests for AI Agent Service.

Validates: AI Assistant Requirements 1.1, 14.1-14.4
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.ai.agent import AIAgentService
from grins_platform.services.ai.rate_limiter import RateLimitError


def create_mock_session() -> MagicMock:
    """Create a properly mocked async session for testing."""
    mock_session = MagicMock()

    # Create mock result objects that behave correctly
    def create_mock_result(
        scalar_value: int | None = 0,
        all_value: list[MagicMock] | None = None,
    ) -> MagicMock:
        mock_result = MagicMock()
        mock_result.scalar.return_value = scalar_value
        mock_result.all.return_value = all_value or []
        return mock_result

    # Create an async function that returns the mock result
    async def mock_execute(*args, **kwargs):  # noqa: ARG001
        return create_mock_result(scalar_value=0, all_value=[])

    # Mock execute to return proper result objects
    mock_session.execute = mock_execute

    return mock_session


@pytest.mark.asyncio
class TestAIAgentService:
    """Tests for AIAgentService."""

    async def test_initialization(self) -> None:
        """Test agent initializes with correct model."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session, model="gpt-4o-mini")

        assert service.model == "gpt-4o-mini"
        assert service.system_prompt is not None

    async def test_chat_success(self) -> None:
        """Test successful chat interaction."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        # Mock rate limiter
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        # Mock the _generate_response method
        with patch.object(service, "_generate_response") as mock_generate:
            mock_generate.return_value = (
                "I can help you schedule appointments. What would you like to do?"
            )
            response = await service.chat(uuid4(), "Help me schedule appointments")

        assert response is not None
        assert len(response) > 0

    async def test_chat_rate_limit_exceeded(self) -> None:
        """Test chat fails when rate limit exceeded."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        # Mock rate limiter to raise error
        service.rate_limiter.check_limit = AsyncMock(
            side_effect=RateLimitError("Limit exceeded"),
        )

        with pytest.raises(RateLimitError):
            await service.chat(uuid4(), "Test message")

    async def test_chat_stream_success(self) -> None:
        """Test successful streaming chat."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        # Mock rate limiter
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        # Mock the streaming response by patching _generate_response
        # and the stream method
        async def mock_stream_gen():
            yield "I can help "
            yield "with estimates."

        with patch.object(service, "_generate_response") as mock_generate:
            mock_generate.return_value = "I can help with estimates."
            # For streaming, we need to collect chunks
            stream = service.chat_stream(uuid4(), "Help with estimates")
            chunks = [chunk async for chunk in stream]

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0

    async def test_chat_handles_categorization_query(self) -> None:
        """Test chat responds to categorization queries."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        with patch.object(service, "_generate_response") as mock_generate:
            mock_generate.return_value = (
                "I can help categorize jobs based on their type and requirements."
            )
            response = await service.chat(uuid4(), "Can you categorize this job?")

        assert "categorize" in response.lower()

    async def test_chat_handles_communication_query(self) -> None:
        """Test chat responds to communication queries."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        with patch.object(service, "_generate_response") as mock_generate:
            mock_generate.return_value = (
                "I can help draft a message for customer communication."
            )
            response = await service.chat(uuid4(), "Draft a message for the customer")

        assert "message" in response.lower() or "communication" in response.lower()

    async def test_chat_handles_generic_query(self) -> None:
        """Test chat responds to generic queries."""
        mock_session = create_mock_session()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        with patch.object(service, "_generate_response") as mock_generate:
            mock_generate.return_value = (
                "I can help with scheduling, estimates, and customer communication."
            )
            response = await service.chat(uuid4(), "Hello, what can you do?")

        assert "help" in response.lower()
        assert "scheduling" in response.lower()
