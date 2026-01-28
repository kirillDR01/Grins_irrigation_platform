"""Tests for jobs ready to schedule endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.integration
class TestJobsReadyToScheduleEndpoint:
    """Test GET /api/v1/schedule/jobs-ready endpoint."""

    @pytest.mark.asyncio
    async def test_get_jobs_ready_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that endpoint exists and returns valid response."""
        # Call endpoint
        response = await client.get("/api/v1/schedule/jobs-ready")

        # Verify response structure
        assert response.status_code == 200
        data = response.json()

        # Verify response has required fields
        assert "jobs" in data
        assert "total_count" in data
        assert "by_city" in data
        assert "by_job_type" in data

        # Verify types
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["by_city"], dict)
        assert isinstance(data["by_job_type"], dict)

    @pytest.mark.asyncio
    async def test_get_jobs_ready_accepts_date_filters(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that endpoint accepts date filter parameters."""
        # Call endpoint with date filters
        response = await client.get(
            "/api/v1/schedule/jobs-ready",
            params={
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "jobs" in data
        assert "total_count" in data
