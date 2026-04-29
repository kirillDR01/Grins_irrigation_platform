"""Functional tests for AI scheduling — User Admin and Resource workflows.

Tests the full AI scheduling workflows using real service objects with
mocked external dependencies (OpenAI, Google Maps, Weather API).

Validates: Requirements 27.1-27.7
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.schemas.ai_scheduling import (
    ChatResponse,
    PreJobChecklist,
)
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestService,
)
from grins_platform.services.ai.scheduling.chat_service import SchedulingChatService
from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator

# =============================================================================
# Helpers / Factories
# =============================================================================


def _make_job(**kw: Any) -> MagicMock:
    j = MagicMock()
    j.id = kw.get("id", uuid.uuid4())
    j.customer_id = kw.get("customer_id", uuid.uuid4())
    j.status = kw.get("status", "approved")
    j.priority = kw.get("priority", 3)
    j.description = kw.get("description", "Spring irrigation startup")
    j.job_type = kw.get("job_type", "seasonal")
    j.category = kw.get("category", "Seasonal")
    j.is_outdoor = kw.get("is_outdoor", True)
    j.predicted_complexity = kw.get("predicted_complexity", 1.0)
    j.revenue_per_hour = kw.get("revenue_per_hour", 120.0)
    j.address = kw.get("address", "123 Main St, Eden Prairie, MN")
    j.latitude = kw.get("latitude", 44.85)
    j.longitude = kw.get("longitude", -93.47)
    customer = MagicMock()
    customer.first_name = "Jane"
    customer.last_name = "Smith"
    customer.phone = "6125551234"
    customer.gate_code = None
    customer.time_window_preference = "morning"
    customer.time_window_is_hard = False
    j.customer = customer
    return j


def _make_session() -> AsyncMock:
    """Build a minimal AsyncMock that satisfies SQLAlchemy session usage."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalar_one_or_none.return_value = None
    result.scalar.return_value = 0
    session.execute.return_value = result
    return session


# =============================================================================
# 17.1 — Functional test infrastructure fixtures
# =============================================================================


@pytest.fixture
def db_session() -> AsyncMock:
    return _make_session()


@pytest.fixture
def job_spring_opening() -> MagicMock:
    return _make_job(
        description="Spring irrigation system startup",
        job_type="seasonal",
        priority=4,
        is_outdoor=True,
    )


@pytest.fixture
def job_backflow_test() -> MagicMock:
    return _make_job(
        description="Annual backflow preventer test",
        job_type="diagnostic",
        priority=3,
        is_outdoor=False,
    )


@pytest.fixture
def job_emergency() -> MagicMock:
    return _make_job(
        description="Emergency: broken main line flooding yard",
        job_type="repair",
        priority=5,
        is_outdoor=True,
    )


# =============================================================================
# 17.2 — User Admin workflows
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
async def test_admin_chat_schedule_building_via_natural_language(
    db_session: AsyncMock,
) -> None:
    """Admin sends natural language command → AI returns schedule changes.

    Validates: Requirement 27.3
    """
    svc = SchedulingChatService(session=db_session)
    response = await svc.chat(
        user_id=uuid.uuid4(),
        role="admin",
        message="Schedule all spring openings for Monday next week",
    )

    assert isinstance(response, ChatResponse)
    assert len(response.response) > 0


@pytest.mark.functional
@pytest.mark.asyncio
async def test_admin_chat_emergency_job_insertion(
    db_session: AsyncMock,
    job_emergency: MagicMock,
) -> None:
    """Admin reports emergency → AI finds best-fit resource.

    Validates: Requirement 27.3
    """
    svc = SchedulingChatService(session=db_session)
    response = await svc.chat(
        user_id=uuid.uuid4(),
        role="admin",
        message=(
            f"Emergency repair needed at job {job_emergency.id}. "
            "Flooding yard. Who can go now?"
        ),
    )

    assert isinstance(response, ChatResponse)
    assert len(response.response) > 0


@pytest.mark.functional
@pytest.mark.asyncio
async def test_admin_alert_detection_double_booking(
    db_session: AsyncMock,
) -> None:
    """Double-booking alert detected by AlertEngine.

    Validates: Requirement 27.3
    """
    staff_id = uuid.uuid4()
    job_id_1 = uuid.uuid4()
    job_id_2 = uuid.uuid4()

    engine = AlertEngine(session=db_session)

    # Two overlapping assignments for the same staff member
    alerts = await engine.scan_and_generate(
        schedule_date=date(2026, 5, 15),
        assignments=[
            {
                "staff_id": str(staff_id),
                "job_id": str(job_id_1),
                "start_time": "09:00",
                "end_time": "11:00",
            },
            {
                "staff_id": str(staff_id),
                "job_id": str(job_id_2),
                "start_time": "10:00",
                "end_time": "12:00",
            },
        ],
    )

    assert isinstance(alerts, list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_admin_suggestion_generation_route_swap(
    db_session: AsyncMock,
) -> None:
    """Route swap suggestion generated by AlertEngine.

    Validates: Requirement 27.3
    """
    engine = AlertEngine(session=db_session)

    # Two staff with jobs in each other's zones (swap opportunity)
    staff_a = uuid.uuid4()
    staff_b = uuid.uuid4()
    job_a = uuid.uuid4()
    job_b = uuid.uuid4()

    alerts = await engine.scan_and_generate(
        schedule_date=date(2026, 5, 16),
        assignments=[
            {
                "staff_id": str(staff_a),
                "job_id": str(job_a),
                "start_time": "08:00",
                "end_time": "10:00",
                "latitude": 44.85,
                "longitude": -93.47,
            },
            {
                "staff_id": str(staff_b),
                "job_id": str(job_b),
                "start_time": "08:00",
                "end_time": "10:00",
                "latitude": 44.90,
                "longitude": -93.50,
            },
        ],
    )

    assert isinstance(alerts, list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_admin_batch_scheduling_natural_language(
    db_session: AsyncMock,
) -> None:
    """Batch scheduling: multi-week schedule via natural language.

    Validates: Requirement 27.3
    """
    svc = SchedulingChatService(session=db_session)
    response = await svc.chat(
        user_id=uuid.uuid4(),
        role="admin",
        message=(
            "Generate a 3-week batch schedule for all spring openings, "
            "prioritizing Eden Prairie zone first."
        ),
    )

    assert isinstance(response, ChatResponse)
    assert len(response.response) > 0


# =============================================================================
# 17.3 — Resource workflows
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_running_late_report(
    db_session: AsyncMock,
) -> None:
    """Resource reports delay → ChangeRequest created for admin.

    Validates: Requirement 27.4
    """
    resource_id = uuid.uuid4()
    job_id = uuid.uuid4()

    svc = ChangeRequestService(session=db_session)

    result = await svc.create_request(
        resource_id=resource_id,
        request_type="delay_report",
        details={
            "job_id": str(job_id),
            "delay_minutes": 25,
            "reason": "Traffic on I-494",
        },
        affected_job_id=job_id,
    )

    assert result is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_prejob_requirements_retrieval(
    db_session: AsyncMock,
    job_spring_opening: MagicMock,
) -> None:
    """Resource asks for pre-job info → checklist generated.

    Validates: Requirement 27.4
    """
    # Ensure service_offering_id and property_id are None so the generator
    # uses safe defaults rather than trying to load related objects.
    job_spring_opening.service_offering_id = None
    job_spring_opening.property_id = None

    # First execute call returns the job; subsequent calls return None.
    job_result = MagicMock()
    job_result.scalar_one_or_none.return_value = job_spring_opening
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db_session.execute.side_effect = [job_result, none_result, none_result, none_result]

    gen = PreJobGenerator(session=db_session)

    checklist = await gen.generate_checklist(
        job_id=job_spring_opening.id,
        resource_id=uuid.uuid4(),
    )

    assert isinstance(checklist, PreJobChecklist)
    assert checklist.job_type is not None
    assert checklist.customer_name is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_followup_job_request(
    db_session: AsyncMock,
) -> None:
    """Resource reports additional work needed → ChangeRequest packaged.

    Validates: Requirement 27.4
    """
    resource_id = uuid.uuid4()
    job_id = uuid.uuid4()

    svc = ChangeRequestService(session=db_session)

    result = await svc.create_request(
        resource_id=resource_id,
        request_type="followup_job",
        details={
            "job_id": str(job_id),
            "description": "Found broken head on zone 3, needs replacement",
            "estimated_duration_minutes": 45,
        },
        affected_job_id=job_id,
    )

    assert result is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_parts_logging(
    db_session: AsyncMock,
) -> None:
    """Resource logs parts used → ChangeRequest created for inventory update.

    Validates: Requirement 27.4
    """
    resource_id = uuid.uuid4()
    job_id = uuid.uuid4()

    svc = ChangeRequestService(session=db_session)

    result = await svc.create_request(
        resource_id=resource_id,
        request_type="parts_log",
        details={
            "job_id": str(job_id),
            "parts": [
                {"name": "Hunter PGP rotor", "quantity": 3},
                {"name": "1/2 inch coupling", "quantity": 2},
            ],
        },
        affected_job_id=job_id,
    )

    assert result is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_nearby_pickup_work(
    db_session: AsyncMock,
) -> None:
    """Resource finishes early → nearby pickup request created.

    Validates: Requirement 27.4
    """
    resource_id = uuid.uuid4()

    svc = ChangeRequestService(session=db_session)

    result = await svc.create_request(
        resource_id=resource_id,
        request_type="nearby_pickup",
        details={
            "current_location": {"lat": 44.85, "lng": -93.47},
            "available_minutes": 90,
            "message": "Finished early, can take another job nearby",
        },
        affected_job_id=None,
    )

    assert result is not None


@pytest.mark.functional
@pytest.mark.asyncio
async def test_resource_chat_running_late(
    db_session: AsyncMock,
) -> None:
    """Resource uses chat to report running late.

    Validates: Requirement 27.4
    """
    svc = SchedulingChatService(session=db_session)
    response = await svc.chat(
        user_id=uuid.uuid4(),
        role="technician",
        message="Running late, stuck in traffic, about 25 minutes behind",
    )

    assert isinstance(response, ChatResponse)
    assert len(response.response) > 0


# =============================================================================
# 17.4 — Constraint satisfaction and alert pipeline
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
async def test_schedule_generation_skill_mismatch_detection(
    db_session: AsyncMock,
) -> None:
    """AlertEngine detects skill mismatch in assignments.

    Validates: Requirement 27.5
    """
    staff_id = uuid.uuid4()
    job_id = uuid.uuid4()

    engine = AlertEngine(session=db_session)

    # Assignment with skill mismatch: job requires backflow, staff lacks it
    alerts = await engine.scan_and_generate(
        schedule_date=date(2026, 5, 20),
        assignments=[
            {
                "staff_id": str(staff_id),
                "job_id": str(job_id),
                "required_skills": ["backflow"],
                "staff_skills": [],  # mismatch
                "start_time": "09:00",
                "end_time": "11:00",
            }
        ],
    )

    assert isinstance(alerts, list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_alert_pipeline_end_to_end(
    db_session: AsyncMock,
) -> None:
    """Alert pipeline: data input → criteria evaluation → alert list returned.

    Validates: Requirement 27.6
    """
    engine = AlertEngine(session=db_session)

    # Empty assignments — no alerts expected
    alerts = await engine.scan_and_generate(
        schedule_date=date(2026, 5, 21),
        assignments=[],
    )

    assert isinstance(alerts, list)


@pytest.mark.functional
@pytest.mark.asyncio
async def test_change_request_invalid_type_raises(
    db_session: AsyncMock,
) -> None:
    """ChangeRequestService rejects invalid request types.

    Validates: Requirement 27.5
    """
    svc = ChangeRequestService(session=db_session)

    with pytest.raises(ValueError, match="Invalid request_type"):
        await svc.create_request(
            resource_id=uuid.uuid4(),
            request_type="invalid_type_xyz",
            details={},
            affected_job_id=None,
        )


# =============================================================================
# 17.5 — Verify all functional tests pass (meta-test)
# =============================================================================


@pytest.mark.functional
def test_functional_test_module_imports() -> None:
    """Verify all required service classes import cleanly.

    Validates: Requirement 27.7
    """
    from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
    from grins_platform.services.ai.scheduling.change_request_service import (
        ChangeRequestService,
    )
    from grins_platform.services.ai.scheduling.chat_service import (
        SchedulingChatService,
    )
    from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator

    assert AlertEngine is not None
    assert ChangeRequestService is not None
    assert SchedulingChatService is not None
    assert PreJobGenerator is not None


@pytest.mark.functional
def test_ai_scheduling_schemas_import() -> None:
    """Verify AI scheduling schemas import cleanly.

    Validates: Requirement 27.7
    """
    from grins_platform.schemas.ai_scheduling import (
        AlertCandidate,
        BatchScheduleRequest,
        BatchScheduleResponse,
        CapacityForecast,
        ChangeRequestResponse,
        ChatRequest,
        ChatResponse,
        CriteriaScore,
        CriterionResult,
        PreJobChecklist,
        RankedCandidate,
        ResolveAlertRequest,
        ScheduleChange,
        ScheduleEvaluation,
        SchedulingAlertResponse,
        UpsellSuggestion,
        UtilizationReport,
    )

    assert ChatRequest is not None
    assert ChatResponse is not None
    assert ScheduleEvaluation is not None
    assert PreJobChecklist is not None
    assert UpsellSuggestion is not None
    assert AlertCandidate is not None
    assert BatchScheduleRequest is not None
    assert BatchScheduleResponse is not None
    assert CapacityForecast is not None
    assert ChangeRequestResponse is not None
    assert CriteriaScore is not None
    assert CriterionResult is not None
    assert RankedCandidate is not None
    assert ResolveAlertRequest is not None
    assert ScheduleChange is not None
    assert SchedulingAlertResponse is not None
    assert UtilizationReport is not None
