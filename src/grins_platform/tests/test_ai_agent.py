"""Tests for AI Agent Service.

Validates: AI Assistant Requirements 1.1, 14.1-14.4
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from grins_platform.services.ai.agent import AIAgentService
from grins_platform.services.ai.rate_limiter import RateLimitError


@pytest.mark.asyncio
class TestAIAgentService:
    """Tests for AIAgentService."""

    async def test_initialization(self) -> None:
        """Test agent initializes with correct model."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session, model="gpt-4o-mini")

        assert service.model == "gpt-4o-mini"
        assert service.system_prompt is not None

    async def test_chat_success(self) -> None:
        """Test successful chat interaction."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        # Mock rate limiter
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        response = await service.chat(uuid4(), "Help me schedule appointments")

        assert response is not None
        assert len(response) > 0
        assert "schedule" in response.lower()

    async def test_chat_rate_limit_exceeded(self) -> None:
        """Test chat fails when rate limit exceeded."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        # Mock rate limiter to raise error
        service.rate_limiter.check_limit = AsyncMock(
            side_effect=RateLimitError("Limit exceeded"),
        )

        with pytest.raises(RateLimitError):
            await service.chat(uuid4(), "Test message")

    async def test_chat_stream_success(self) -> None:
        """Test successful streaming chat."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        # Mock rate limiter
        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        chunks = [
            chunk async for chunk in service.chat_stream(uuid4(), "Help with estimates")
        ]

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert "estimate" in full_response.lower()

    async def test_chat_handles_categorization_query(self) -> None:
        """Test chat responds to categorization queries."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        response = await service.chat(uuid4(), "Can you categorize this job?")

        assert "categorize" in response.lower()

    async def test_chat_handles_communication_query(self) -> None:
        """Test chat responds to communication queries."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        response = await service.chat(uuid4(), "Draft a message for the customer")

        assert "communication" in response.lower() or "message" in response.lower()

    async def test_chat_handles_generic_query(self) -> None:
        """Test chat responds to generic queries."""
        mock_session = AsyncMock()
        service = AIAgentService(mock_session)

        service.rate_limiter.check_limit = AsyncMock(return_value=True)
        service.rate_limiter.record_usage = AsyncMock(return_value=1)

        response = await service.chat(uuid4(), "Hello, what can you do?")

        assert "help" in response.lower()
        assert "scheduling" in response.lower()
