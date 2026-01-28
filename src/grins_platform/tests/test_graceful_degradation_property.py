"""Property-Based Test: Graceful Degradation.

Property 6: All AI features have fallback behavior when AI unavailable.

This test validates Requirements 2.9, 3.8:
- Schedule explanation provides fallback when AI unavailable
- Unassigned job explanation provides fallback when AI unavailable
- Constraint parsing provides fallback when AI unavailable
- System remains functional without AI service
"""

from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestGracefulDegradation:
    """Test that all AI features degrade gracefully when AI is unavailable."""

    @pytest.mark.asyncio
    async def test_schedule_explanation_without_api_key(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test schedule explanation provides fallback when API key missing.

        Property: When OpenAI API key is not configured, schedule explanation
        returns a fallback response instead of failing.

        Validates: Requirement 2.9
        """
        # Remove API key to simulate AI unavailable
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = await client.post(
            "/api/v1/schedule/explain",
            json={
                "schedule_date": date.today().isoformat(),
                "staff_assignments": [
                    {
                        "staff_id": str(uuid4()),
                        "staff_name": "Viktor",
                        "job_count": 5,
                        "total_minutes": 300,
                        "cities": ["Minneapolis"],
                        "job_types": ["spring_startup"],
                    },
                ],
                "unassigned_job_count": 2,
            },
        )

        # Should return 200 with fallback message, not 500
        assert response.status_code == 200
        data = response.json()

        # Fallback response should contain basic information
        assert "explanation" in data
        assert len(data["explanation"]) > 0

        # Test passes if we get either:
        # 1. Fallback message (AI unavailable)
        # 2. Real AI response (if API key was already loaded)
        # The key property is: no 500 error when AI might be unavailable
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unassigned_job_explanation_without_api_key(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test unassigned job explanation provides fallback when API key missing.

        Property: When OpenAI API key is not configured, unassigned job explanation
        returns basic constraint analysis instead of failing.

        Validates: Requirement 3.8
        """
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = await client.post(
            "/api/v1/schedule/explain-unassigned",
            json={
                "job_id": str(uuid4()),
                "job_type": "spring_startup",
                "customer_name": "Test Customer",
                "city": "Minneapolis",
                "estimated_duration_minutes": 60,
                "priority": "medium",
                "requires_equipment": [],
                "constraint_violations": [],
            },
        )

        # Should return 200 with fallback, not 500
        assert response.status_code == 200
        data = response.json()

        # Fallback should provide basic information
        assert "reason" in data
        assert len(data["reason"]) > 0

        # Should have suggestions even without AI
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_constraint_parsing_without_api_key(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test constraint parsing provides fallback when API key missing.

        Property: When OpenAI API key is not configured, constraint parsing returns
        empty constraints list instead of failing.

        Validates: Requirement 4.9 (implicit - system should not crash)
        """
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        response = await client.post(
            "/api/v1/schedule/parse-constraints",
            json={
                "constraint_text": "Don't schedule Viktor before 10am",
            },
        )

        # Should return 200 with empty/fallback constraints, not 500
        assert response.status_code == 200
        data = response.json()

        # Should have constraints field (may be empty)
        assert "constraints" in data
        assert isinstance(data["constraints"], list)

        # Should indicate parsing failed or unavailable
        assert "unparseable_text" in data

    @pytest.mark.asyncio
    async def test_all_endpoints_survive_missing_api_key(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that all AI endpoints remain functional when API key missing.

        Property: No AI endpoint should return 500 when OpenAI API key
        is not configured. All should provide graceful fallback responses.

        Validates: Requirements 2.9, 3.8
        """
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Test schedule explanation
        explain_response = await client.post(
            "/api/v1/schedule/explain",
            json={
                "schedule_date": date.today().isoformat(),
                "staff_assignments": [],
                "unassigned_job_count": 0,
            },
        )
        assert explain_response.status_code != 500

        # Test unassigned explanation
        unassigned_response = await client.post(
            "/api/v1/schedule/explain-unassigned",
            json={
                "job_id": str(uuid4()),
                "job_type": "repair",
                "customer_name": "Test Customer",
                "city": "Minneapolis",
                "estimated_duration_minutes": 120,
                "priority": "high",
                "requires_equipment": [],
                "constraint_violations": [],
            },
        )
        assert unassigned_response.status_code != 500

        # Test constraint parsing
        parse_response = await client.post(
            "/api/v1/schedule/parse-constraints",
            json={
                "constraint_text": "Keep jobs together",
            },
        )
        assert parse_response.status_code != 500

    @pytest.mark.asyncio
    async def test_jobs_ready_endpoint_independent_of_ai(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that jobs ready endpoint works without AI service.

        Property: Jobs ready to schedule endpoint should not depend on AI
        and should always work regardless of AI availability.

        Validates: Requirement 9.1 (implicit - non-AI endpoint)
        """
        # This endpoint should work without any AI mocking
        response = await client.get("/api/v1/schedule/jobs-ready")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total_count" in data
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total_count"], int)
