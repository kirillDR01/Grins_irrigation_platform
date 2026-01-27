"""Property tests for schedule generation.

Property 6: Schedule Location Batching
Property 7: Schedule Job Type Batching

Validates: Requirements 4.2, 4.3
"""

from datetime import date, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.ai.tools.scheduling import SchedulingTools


@pytest.mark.asyncio
class TestSchedulingProperty:
    """Property-based tests for scheduling."""

    @given(
        cities=st.lists(
            st.sampled_from(["Eden Prairie", "Plymouth", "Maple Grove", "Rogers"]),
            min_size=2,
            max_size=10,
        ),
    )
    @settings(max_examples=20)
    async def test_jobs_batched_by_location(self, cities: list[str]) -> None:
        """Property: Jobs in same city are scheduled together."""
        mock_session = AsyncMock()
        tools = SchedulingTools(mock_session)

        # Create jobs with different cities
        jobs = [
            {
                "id": str(uuid4()),
                "city": city,
                "job_type": "startup",
                "estimated_duration": 30,
            }
            for city in cities
        ]

        staff = [{"id": str(uuid4()), "name": "Test Staff"}]

        schedule = tools._batch_and_assign(jobs, staff, date.today())

        # Verify jobs are grouped by city
        slots = schedule["slots"]
        if len(slots) > 1:
            # Check that consecutive slots tend to be in same city
            city_changes = 0
            for i in range(1, len(slots)):
                if slots[i]["city"] != slots[i - 1]["city"]:
                    city_changes += 1

            # Should have fewer city changes than random ordering
            max_changes = len(set(cities)) - 1
            assert city_changes <= max_changes

    @given(
        job_types=st.lists(
            st.sampled_from(["startup", "winterization", "repair", "installation"]),
            min_size=2,
            max_size=10,
        ),
    )
    @settings(max_examples=20)
    async def test_jobs_batched_by_type(self, job_types: list[str]) -> None:
        """Property: Jobs of same type are scheduled together within a city."""
        mock_session = AsyncMock()
        tools = SchedulingTools(mock_session)

        # Create jobs with same city but different types
        jobs = [
            {
                "id": str(uuid4()),
                "city": "Eden Prairie",
                "job_type": jt,
                "estimated_duration": 30,
            }
            for jt in job_types
        ]

        staff = [{"id": str(uuid4()), "name": "Test Staff"}]

        schedule = tools._batch_and_assign(jobs, staff, date.today())

        # Verify jobs are grouped by type within city
        slots = schedule["slots"]
        if len(slots) > 1:
            # Check that consecutive slots tend to be same type
            type_changes = 0
            for i in range(1, len(slots)):
                if slots[i]["job_type"] != slots[i - 1]["job_type"]:
                    type_changes += 1

            # Should have fewer type changes than random ordering
            max_changes = len(set(job_types)) - 1
            assert type_changes <= max_changes

    async def test_empty_jobs_returns_empty_schedule(self) -> None:
        """Test that empty job list returns empty schedule."""
        mock_session = AsyncMock()
        tools = SchedulingTools(mock_session)

        schedule = tools._batch_and_assign([], [], date.today())

        assert schedule["slots"] == []
        assert schedule["total_jobs"] == 0

    async def test_schedule_includes_travel_buffer(self) -> None:
        """Test that schedule includes travel time between jobs."""
        mock_session = AsyncMock()
        tools = SchedulingTools(mock_session)

        jobs = [
            {
                "id": str(uuid4()),
                "city": "Eden Prairie",
                "job_type": "startup",
                "estimated_duration": 30,
            },
            {
                "id": str(uuid4()),
                "city": "Plymouth",
                "job_type": "startup",
                "estimated_duration": 30,
            },
        ]
        staff = [{"id": str(uuid4()), "name": "Test Staff"}]

        schedule = tools._batch_and_assign(jobs, staff, date.today())

        slots = schedule["slots"]
        assert len(slots) == 2

        # Second job should start after first job + travel buffer
        first_end = datetime.fromisoformat(slots[0]["end_time"])
        second_start = datetime.fromisoformat(slots[1]["start_time"])

        # Should have at least 15 min buffer
        assert (second_start - first_end).total_seconds() >= 15 * 60
