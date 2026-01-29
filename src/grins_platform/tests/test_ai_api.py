"""Tests for AI API endpoints."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAIChatEndpoint:
    """Tests for /api/v1/ai/chat endpoint."""

    @patch("grins_platform.api.v1.ai.AIAgentService")
    async def test_chat_returns_streaming_response(
        self,
        mock_agent_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that chat endpoint returns streaming response."""

        # Mock the chat_stream method to return an async generator
        async def mock_stream() -> AsyncGenerator[str, None]:
            yield "Hello"
            yield " World"

        mock_agent = mock_agent_cls.return_value
        mock_agent.chat_stream = Mock(return_value=mock_stream())

        response = await client.post(
            "/api/v1/ai/chat",
            json={"message": "How many jobs today?"},
            params={"stream": "true"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    async def test_chat_requires_message(self, client: AsyncClient) -> None:
        """Test that chat endpoint requires message in request body."""
        response = await client.post("/api/v1/ai/chat", json={})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestScheduleGenerateEndpoint:
    """Tests for /api/v1/ai/schedule/generate endpoint."""

    @patch("grins_platform.api.v1.ai.SchedulingTools")
    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_schedule_generate_creates_audit_log(
        self,
        mock_audit_cls: Mock,
        mock_tools_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that schedule generation creates audit log."""
        mock_tools = mock_tools_cls.return_value
        mock_tools.generate_schedule = AsyncMock(
            return_value={
                "days": [],
                "warnings": [],
                "summary": {"total_jobs": 0, "total_staff": 0},
            },
        )

        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = uuid4()
        mock_audit.log_recommendation = AsyncMock(return_value=mock_log)

        response = await client.post(
            "/api/v1/ai/schedule/generate",
            json={"target_date": "2025-01-27", "job_ids": []},
        )
        assert response.status_code == 200
        mock_audit.log_recommendation.assert_called_once()

    async def test_schedule_generate_requires_target_date(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that schedule generate requires target_date."""
        response = await client.post(
            "/api/v1/ai/schedule/generate",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestJobCategorizeEndpoint:
    """Tests for /api/v1/ai/jobs/categorize endpoint."""

    @patch("grins_platform.api.v1.ai.CategorizationTools")
    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_categorize_returns_results(
        self,
        mock_audit_cls: Mock,
        mock_tools_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that categorize returns categorization results."""
        mock_tools = mock_tools_cls.return_value
        mock_tools.categorize_job = AsyncMock(
            return_value={
                "category": "repair",
                "confidence": 85,
                "reasoning": "Test reasoning",
                "suggested_services": ["sprinkler_repair"],
                "needs_review": False,
            },
        )

        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = uuid4()
        mock_audit.log_recommendation = AsyncMock(return_value=mock_log)

        response = await client.post(
            "/api/v1/ai/jobs/categorize",
            json={"description": "Broken sprinkler head in front yard"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "category" in data
        assert data["category"] == "repair"

    async def test_categorize_requires_description(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that categorize requires description."""
        response = await client.post(
            "/api/v1/ai/jobs/categorize",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestCommunicationDraftEndpoint:
    """Tests for /api/v1/ai/communication/draft endpoint."""

    @patch("grins_platform.api.v1.ai.CommunicationTools")
    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_draft_returns_message(
        self,
        mock_audit_cls: Mock,
        mock_tools_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that draft returns message draft."""
        mock_tools = mock_tools_cls.return_value
        mock_tools.draft_message = AsyncMock(
            return_value={
                "success": True,
                "message": "Test message",
                "character_count": 12,
                "sms_segments": 1,
            },
        )

        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = uuid4()
        mock_audit.log_recommendation = AsyncMock(return_value=mock_log)

        response = await client.post(
            "/api/v1/ai/communication/draft",
            json={
                "message_type": "appointment_confirmation",
                "context": {"appointment_date": "2025-01-27"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Test message"


@pytest.mark.asyncio
class TestEstimateGenerateEndpoint:
    """Tests for /api/v1/ai/estimate/generate endpoint."""

    @patch("grins_platform.api.v1.ai.EstimateTools")
    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_estimate_returns_breakdown(
        self,
        mock_audit_cls: Mock,
        mock_tools_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that estimate returns price breakdown."""
        mock_tools = mock_tools_cls.return_value
        mock_tools.calculate_estimate = AsyncMock(
            return_value={
                "line_items": [{"description": "Labor", "amount": 200.0}],
                "subtotal": 200.0,
                "tax": 16.0,
                "total": 216.0,
                "confidence": 90,
                "needs_review": False,
            },
        )

        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = uuid4()
        mock_audit.log_recommendation = AsyncMock(return_value=mock_log)

        response = await client.post(
            "/api/v1/ai/estimate/generate",
            json={"service_type": "spring_startup", "zone_count": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] == 216.0


@pytest.mark.asyncio
class TestAIUsageEndpoint:
    """Tests for /api/v1/ai/usage endpoint."""

    @patch("grins_platform.api.v1.ai.RateLimitService")
    async def test_usage_returns_statistics(
        self,
        mock_rate_limit_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that usage returns usage statistics."""
        mock_rate_limit = mock_rate_limit_cls.return_value
        mock_rate_limit.get_usage = AsyncMock(
            return_value={
                "request_count": 10,
                "total_input_tokens": 100,
                "total_output_tokens": 200,
                "estimated_cost_usd": 0.05,
                "daily_limit": 100,
                "remaining_requests": 90,
            },
        )

        response = await client.get("/api/v1/ai/usage")
        assert response.status_code == 200
        data = response.json()
        assert "request_count" in data
        assert data["request_count"] == 10


@pytest.mark.asyncio
class TestAIAuditEndpoint:
    """Tests for /api/v1/ai/audit endpoint."""

    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_audit_returns_logs(
        self,
        mock_audit_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that audit returns audit logs."""
        mock_audit = mock_audit_cls.return_value
        mock_audit.list_audit_logs = AsyncMock(return_value=([], 0))

        response = await client.get("/api/v1/ai/audit")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_audit_filters_by_action_type(
        self,
        mock_audit_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that audit filters by action type."""
        mock_audit = mock_audit_cls.return_value
        mock_audit.list_audit_logs = AsyncMock(return_value=([], 0))

        response = await client.get(
            "/api/v1/ai/audit",
            params={"action_type": "schedule_generation"},
        )
        assert response.status_code == 200
        mock_audit.list_audit_logs.assert_called_once()


@pytest.mark.asyncio
class TestAIAuditDecisionEndpoint:
    """Tests for /api/v1/ai/audit/{audit_id}/decision endpoint."""

    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_decision_records_approval(
        self,
        mock_audit_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that decision records approval."""
        audit_id = uuid4()
        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = audit_id
        mock_log.action_type = "schedule_generation"
        mock_log.entity_type = "schedule"
        mock_log.entity_id = None
        mock_log.ai_recommendation = {}
        mock_log.user_decision = "approved"
        mock_log.confidence_score = 0.85
        mock_log.created_at = "2025-01-27T00:00:00"
        mock_log.decision_at = "2025-01-27T00:01:00"
        mock_audit.record_decision = AsyncMock(return_value=mock_log)

        response = await client.post(
            f"/api/v1/ai/audit/{audit_id}/decision",
            json={"decision": "approved"},
        )
        assert response.status_code == 200

    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_decision_returns_404_for_missing_log(
        self,
        mock_audit_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that decision returns 404 for missing audit log."""
        audit_id = uuid4()
        mock_audit = mock_audit_cls.return_value
        mock_audit.record_decision = AsyncMock(return_value=None)

        response = await client.post(
            f"/api/v1/ai/audit/{audit_id}/decision",
            json={"decision": "approved"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestHumanApprovalProperty:
    """Property-based tests for human approval requirement."""

    @patch("grins_platform.api.v1.ai.SchedulingTools")
    @patch("grins_platform.api.v1.ai.AuditService")
    async def test_schedule_generation_creates_audit_for_review(
        self,
        mock_audit_cls: Mock,
        mock_tools_cls: Mock,
        client: AsyncClient,
    ) -> None:
        """Test that schedule generation always creates audit log for review."""
        mock_tools = mock_tools_cls.return_value
        mock_tools.generate_schedule = AsyncMock(
            return_value={
                "days": [],
                "warnings": [],
                "summary": {"total_jobs": 0, "total_staff": 0},
            },
        )

        mock_audit = mock_audit_cls.return_value
        mock_log = Mock()
        mock_log.id = uuid4()
        mock_audit.log_recommendation = AsyncMock(return_value=mock_log)

        response = await client.post(
            "/api/v1/ai/schedule/generate",
            json={"target_date": "2025-01-27", "job_ids": []},
        )
        assert response.status_code == 200
        # Verify audit log was created (human-in-the-loop)
        mock_audit.log_recommendation.assert_called_once()
        data = response.json()
        assert "audit_id" in data
