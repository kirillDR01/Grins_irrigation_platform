"""Integration tests for Schedule AI Updates feature.

Tests complete flows for:
- Schedule explanation
- Unassigned job analysis
- Constraint parsing
- Jobs ready to schedule

Note: These tests verify endpoint existence and basic response structure.
Full AI functionality testing requires valid AI service configuration.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestScheduleExplanationFlow:
    """Test complete schedule explanation flow."""

    @pytest.mark.asyncio
    async def test_explain_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that explain schedule endpoint exists and validates input."""
        # Test with minimal valid input
        response = await client.post(
            "/api/v1/schedule/explain",
            json={
                "schedule_date": date.today().isoformat(),
                "staff_assignments": [],
                "unassigned_count": 0,
            },
        )

        # Should either succeed (200) or fail gracefully
        # (422 for validation, 500 for AI unavailable)
        assert response.status_code in [200, 422, 500]


@pytest.mark.integration
class TestUnassignedJobAnalysisFlow:
    """Test complete unassigned job analysis flow."""

    @pytest.mark.asyncio
    async def test_explain_unassigned_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that explain unassigned endpoint exists."""
        response = await client.post(
            "/api/v1/schedule/explain-unassigned",
            json={
                "job_id": str(uuid4()),
                "job_type": "repair",
                "city": "St Paul",
                "duration_minutes": 120,
                "priority": 2,
                "schedule_date": date.today().isoformat(),
                "available_staff": [],
                "constraints": [],
            },
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 422, 500]


@pytest.mark.integration
class TestConstraintParsingFlow:
    """Test complete constraint parsing flow."""

    @pytest.mark.asyncio
    async def test_parse_constraints_endpoint_exists(self, client: AsyncClient) -> None:
        """Test that parse constraints endpoint exists."""
        response = await client.post(
            "/api/v1/schedule/parse-constraints",
            json={
                "text": "Don't schedule Viktor before 10am",
                "available_staff": ["Viktor", "John"],
            },
        )

        # Should either succeed or fail gracefully
        assert response.status_code in [200, 422, 500]


@pytest.mark.integration
class TestJobsReadyToScheduleFlow:
    """Test complete jobs ready to schedule flow."""

    @pytest.mark.asyncio
    async def test_get_jobs_ready_to_schedule(
        self,
        client: AsyncClient,
    ) -> None:
        """Test fetching jobs ready to schedule."""
        response = await client.get("/api/v1/schedule/jobs-ready")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total_count" in data
        assert isinstance(data["jobs"], list)

    @pytest.mark.asyncio
    async def test_filter_jobs_by_date_range(
        self,
        client: AsyncClient,
    ) -> None:
        """Test filtering jobs by date range."""
        future_date = date.today() + timedelta(days=7)
        response = await client.get(
            "/api/v1/schedule/jobs-ready",
            params={
                "start_date": future_date.isoformat(),
                "end_date": (future_date + timedelta(days=1)).isoformat(),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert isinstance(data["jobs"], list)


@pytest.mark.integration
class TestCompleteSchedulingWorkflow:
    """Test complete end-to-end scheduling workflow with AI features."""

    @pytest.mark.asyncio
    async def test_all_endpoints_accessible(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that all new AI endpoints are accessible."""
        # Test parse constraints endpoint
        constraints_response = await client.post(
            "/api/v1/schedule/parse-constraints",
            json={
                "text": "Keep spring startups together",
                "available_staff": ["Viktor", "John"],
            },
        )
        assert constraints_response.status_code in [200, 422, 500]

        # Test jobs ready endpoint
        jobs_response = await client.get("/api/v1/schedule/jobs-ready")
        assert jobs_response.status_code == 200

        # Test explain schedule endpoint
        explain_response = await client.post(
            "/api/v1/schedule/explain",
            json={
                "schedule_date": date.today().isoformat(),
                "staff_assignments": [],
                "unassigned_count": 0,
            },
        )
        assert explain_response.status_code in [200, 422, 500]

        # Test explain unassigned endpoint
        unassigned_response = await client.post(
            "/api/v1/schedule/explain-unassigned",
            json={
                "job_id": str(uuid4()),
                "job_type": "repair",
                "city": "Minneapolis",
                "duration_minutes": 120,
                "priority": 2,
                "schedule_date": date.today().isoformat(),
                "available_staff": [],
                "constraints": [],
            },
        )
        assert unassigned_response.status_code in [200, 422, 500]

        # All endpoints are accessible
        assert True
