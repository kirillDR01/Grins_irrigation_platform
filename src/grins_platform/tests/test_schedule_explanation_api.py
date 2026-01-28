"""Tests for schedule explanation API endpoint.

Validates: Requirement 6.1, 6.2, 6.3
"""

from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from grins_platform.schemas.schedule_explanation import (
    ParseConstraintsRequest,
    ScheduleExplanationRequest,
    StaffAssignmentSummary,
    UnassignedJobExplanationRequest,
)


@pytest.mark.asyncio
@patch("grins_platform.services.ai.explanation_service.AIAgentService")
async def test_explain_schedule_success(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test successful schedule explanation.

    Validates: Requirement 6.1
    """
    # Arrange - Mock AI service
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        return_value="Viktor was assigned 8 jobs in Eden Prairie and Plymouth, "
        "focusing on Spring Startups and Repairs. Vas handled 6 Spring Startups "
        "in Maple Grove. Geographic grouping optimized travel time.",
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = ScheduleExplanationRequest(
        schedule_date=date(2025, 6, 15),
        staff_assignments=[
            StaffAssignmentSummary(
                staff_id=uuid4(),
                staff_name="Viktor",
                job_count=8,
                total_minutes=480,
                cities=["Eden Prairie", "Plymouth"],
                job_types=["Spring Startup", "Repair"],
            ),
            StaffAssignmentSummary(
                staff_id=uuid4(),
                staff_name="Vas",
                job_count=6,
                total_minutes=360,
                cities=["Maple Grove"],
                job_types=["Spring Startup"],
            ),
        ],
        unassigned_job_count=2,
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/explain",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert "highlights" in data
    assert isinstance(data["explanation"], str)
    assert len(data["explanation"]) > 0
    assert isinstance(data["highlights"], list)


@pytest.mark.asyncio
@patch("grins_platform.services.ai.explanation_service.AIAgentService")
async def test_explain_schedule_with_no_unassigned(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test schedule explanation with no unassigned jobs."""
    # Arrange - Mock AI service
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        return_value="Viktor was assigned 10 Spring Startups in Eden Prairie. "
        "All jobs were successfully scheduled with optimal routing.",
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = ScheduleExplanationRequest(
        schedule_date=date(2025, 6, 15),
        staff_assignments=[
            StaffAssignmentSummary(
                staff_id=uuid4(),
                staff_name="Viktor",
                job_count=10,
                total_minutes=600,
                cities=["Eden Prairie"],
                job_types=["Spring Startup"],
            ),
        ],
        unassigned_job_count=0,
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/explain",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 0


@pytest.mark.asyncio
@patch("grins_platform.services.ai.explanation_service.AIAgentService")
async def test_explain_schedule_handles_ai_error(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test that endpoint handles AI service errors gracefully.

    Validates: Requirement 6.1 (error handling)
    """
    # Arrange - Mock AI service to raise error
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        side_effect=RuntimeError("AI service unavailable"),
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = ScheduleExplanationRequest(
        schedule_date=date(2025, 6, 15),
        staff_assignments=[
            StaffAssignmentSummary(
                staff_id=uuid4(),
                staff_name="Viktor",
                job_count=5,
                total_minutes=300,
                cities=["Eden Prairie"],
                job_types=["Repair"],
            ),
        ],
        unassigned_job_count=0,
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/explain",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 500
    assert "Schedule explanation failed" in response.json()["detail"]


@pytest.mark.asyncio
@patch("grins_platform.services.ai.unassigned_analyzer.AIAgentService")
async def test_explain_unassigned_job_success(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test successful unassigned job explanation.

    Validates: Requirement 6.2
    """
    # Arrange - Mock AI service
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        return_value="This job couldn't be scheduled because all available staff "
        "are already at capacity for this date. The job requires 90 minutes but "
        "the maximum available slot is 60 minutes.\n\n"
        "1. Move a lower priority job to another day\n"
        "2. Schedule this job on a different date\n"
        "3. Add additional staff capacity",
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = UnassignedJobExplanationRequest(
        job_id=uuid4(),
        job_type="Spring Startup",
        customer_name="John Doe",
        city="Eden Prairie",
        estimated_duration_minutes=90,
        priority="high",
        requires_equipment=["compressor"],
        constraint_violations=["Staff capacity exceeded", "No available time slots"],
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/explain-unassigned",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "reason" in data
    assert "suggestions" in data
    assert "alternative_dates" in data
    assert isinstance(data["reason"], str)
    assert len(data["reason"]) > 0
    assert isinstance(data["suggestions"], list)
    assert len(data["suggestions"]) > 0
    assert isinstance(data["alternative_dates"], list)


@pytest.mark.asyncio
@patch("grins_platform.services.ai.unassigned_analyzer.AIAgentService")
async def test_explain_unassigned_job_with_fallback(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test unassigned job explanation with AI fallback.

    Validates: Requirement 3.8 (graceful degradation)
    """
    # Arrange - Mock AI service to raise error
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        side_effect=RuntimeError("AI service unavailable"),
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = UnassignedJobExplanationRequest(
        job_id=uuid4(),
        job_type="Repair",
        customer_name="Jane Smith",
        city="Plymouth",
        estimated_duration_minutes=60,
        priority="medium",
        requires_equipment=[],
        constraint_violations=["No available staff"],
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/explain-unassigned",
        json=request_data.model_dump(mode="json"),
    )

    # Assert - Should return 200 with fallback response (graceful degradation)
    assert response.status_code == 200
    data = response.json()
    assert "reason" in data
    assert "suggestions" in data
    assert "alternative_dates" in data
    # Fallback should use constraint violations
    assert "No available staff" in data["reason"]
    assert len(data["alternative_dates"]) > 0


@pytest.mark.asyncio
@patch("grins_platform.services.ai.constraint_parser.AIAgentService")
async def test_parse_constraints_success(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test successful constraint parsing.

    Validates: Requirement 6.3
    """
    # Arrange - Mock AI service
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        return_value='[{"constraint_type": "staff_time", '
        '"description": "Don\'t schedule Viktor before 10am", '
        '"parameters": {"staff_name": "Viktor", "earliest_start": "10:00"}}]',
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = ParseConstraintsRequest(
        constraint_text="Don't schedule Viktor before 10am",
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/parse-constraints",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "constraints" in data
    assert "unparseable_text" in data
    assert isinstance(data["constraints"], list)
    assert len(data["constraints"]) > 0
    constraint = data["constraints"][0]
    assert constraint["constraint_type"] == "staff_time"
    assert "Viktor" in constraint["description"]
    assert "parameters" in constraint
    assert "validation_errors" in constraint


@pytest.mark.asyncio
@patch("grins_platform.services.ai.constraint_parser.AIAgentService")
async def test_parse_constraints_handles_ai_error(
    mock_ai_service_class: AsyncMock,
    client: AsyncClient,
) -> None:
    """Test that endpoint handles AI service errors gracefully.

    Validates: Requirement 6.3 (error handling)
    """
    # Arrange - Mock AI service to raise error
    mock_ai_instance = AsyncMock()
    mock_ai_instance.chat = AsyncMock(
        side_effect=RuntimeError("AI service unavailable"),
    )
    mock_ai_service_class.return_value = mock_ai_instance

    request_data = ParseConstraintsRequest(
        constraint_text="Don't schedule Viktor before 10am",
    )

    # Act
    response = await client.post(
        "/api/v1/schedule/parse-constraints",
        json=request_data.model_dump(mode="json"),
    )

    # Assert
    assert response.status_code == 500
    assert "Constraint parsing failed" in response.json()["detail"]
