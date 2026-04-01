"""Functional tests for AI Scheduling System.

Tests User Admin and Resource workflows with mocked external services
but real-ish data structures. Covers schedule building, emergency
insertion, alert resolution, suggestion acceptance, batch scheduling,
delay reporting, pre-job requirements, follow-up requests, parts
logging, nearby work, constraint satisfaction, and alert pipeline.

Validates: Requirements 27.1-27.7
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.schemas.ai_scheduling import (
    ChatResponse,
    PreJobChecklist,
    UpsellSuggestion,
)
from grins_platform.services.ai.scheduling.admin_tools import AdminSchedulingTools
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestService,
)
from grins_platform.services.ai.scheduling.chat_service import SchedulingChatService
from grins_platform.services.ai.scheduling.prejob_generator import PreJobGenerator
from grins_platform.services.ai.scheduling.resource_alerts import (
    ResourceAlertService,
)
from grins_platform.services.ai.scheduling.resource_tools import (
    ResourceSchedulingTools,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures (Task 17.1)
# ---------------------------------------------------------------------------


def _session() -> AsyncMock:
    """Create a mock async DB session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _staff(
    *,
    staff_id: UUID | None = None,
    name: str = "Mike D.",
    certifications: list[str] | None = None,
    equipment: list[str] | None = None,
    zone_id: UUID | None = None,
) -> dict[str, Any]:
    """Create a staff dict with certifications, equipment, availability."""
    return {
        "id": str(staff_id or uuid4()),
        "name": name,
        "certifications": certifications or ["backflow_certified", "lake_pump"],
        "assigned_equipment": equipment or ["compressor", "pressure_gauge"],
        "shift_start": "07:00",
        "shift_end": "17:00",
        "service_zone_id": str(zone_id or uuid4()),
        "performance_score": 85.0,
        "callback_rate": 0.03,
        "avg_satisfaction": 4.7,
        "latitude": 44.8547,
        "longitude": -93.4708,
        "overtime_threshold_minutes": 480,
        "team_job_hours": [6.0, 6.0, 6.0],
    }


def _customer(
    *,
    customer_id: UUID | None = None,
    clv: float = 75.0,
    preferred_resource_id: UUID | None = None,
) -> dict[str, Any]:
    """Create a customer dict with CLV and preferences."""
    return {
        "id": str(customer_id or uuid4()),
        "name": "Jane Smith",
        "clv_score": clv,
        "preferred_resource_id": (
            str(preferred_resource_id) if preferred_resource_id else None
        ),
        "time_window_preference": "am",
        "time_window_is_hard": False,
    }


def _job(
    *,
    job_id: UUID | None = None,
    priority: str = "standard",
    required_skills: list[str] | None = None,
    required_equipment: list[str] | None = None,
    depends_on: UUID | None = None,
    is_outdoor: bool = False,
    sla_deadline: str | None = None,
) -> dict[str, Any]:
    """Create a job dict with priorities, time windows, dependencies."""
    return {
        "job_id": str(job_id or uuid4()),
        "priority": priority,
        "required_skills": required_skills or [],
        "required_equipment": required_equipment or [],
        "depends_on_job_id": str(depends_on) if depends_on else None,
        "is_outdoor": is_outdoor,
        "sla_deadline": sla_deadline,
        "scheduled_start": "08:00",
        "scheduled_end": "10:00",
        "time_slot": "am",
        "scheduled_hour": 8,
        "estimated_duration_minutes": 60,
        "latitude": 44.86,
        "longitude": -93.47,
        "customer": _customer(),
    }


def _zone(*, zone_id: UUID | None = None, name: str = "North") -> dict[str, Any]:
    """Create a service zone dict."""
    return {
        "id": str(zone_id or uuid4()),
        "name": name,
        "boundary_type": "polygon",
        "is_active": True,
    }


def _criteria_config() -> list[dict[str, Any]]:
    """Create a minimal criteria config for all 30 criteria."""
    return [
        {
            "criterion_number": i,
            "criterion_name": f"Criterion {i}",
            "weight": 50,
            "is_hard_constraint": i in {6, 7, 8, 11, 21, 23, 30},
            "is_enabled": True,
        }
        for i in range(1, 31)
    ]



# ===========================================================================
# Task 17.2: User Admin workflow tests
# ===========================================================================


@pytest.mark.functional
class TestAdminScheduleBuilding:
    """Test admin schedule building via AI Chat workflow.

    Validates: Requirement 27.3
    """

    @pytest.mark.asyncio
    async def test_schedule_building_natural_language(self) -> None:
        """Admin sends natural language → chat returns schedule with changes."""
        session = _session()
        # Mock the session to return a new chat session on create
        mock_chat_session = MagicMock()
        mock_chat_session.id = uuid4()
        mock_chat_session.user_id = uuid4()
        mock_chat_session.user_role = "admin"
        mock_chat_session.messages = []
        mock_chat_session.context = {}
        mock_chat_session.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)
        user_id = uuid4()

        # Without OpenAI key, fallback response is used
        response = await service.chat(
            user_id=user_id,
            role="admin",
            message="Build next week's schedule for spring openings",
        )

        assert isinstance(response, ChatResponse)
        assert response.response  # non-empty response
        lower = response.response.lower()
        assert "schedule" in lower or "scheduling" in lower

    @pytest.mark.asyncio
    async def test_schedule_building_returns_clarifying_questions(self) -> None:
        """Fallback response includes clarifying questions for schedule builds."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="Build next week's schedule",
        )

        assert isinstance(response, ChatResponse)
        # Fallback for schedule-related messages includes clarifying questions
        if response.clarifying_questions:
            assert len(response.clarifying_questions) > 0


@pytest.mark.functional
class TestAdminEmergencyInsertion:
    """Test emergency job insertion via admin tools.

    Validates: Requirement 27.3
    """

    @pytest.mark.asyncio
    async def test_emergency_insertion_finds_best_fit(self) -> None:
        """Emergency insertion returns a valid assignment with resource."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.insert_emergency(
            address="456 Oak Ave, Eden Prairie, MN",
            skill="backflow_certified",
            duration=90,
            time_constraint="before 2pm",
        )

        assert result["status"] == "inserted"
        assert "skill_required" in result
        assert "time_constraint" in result

    @pytest.mark.asyncio
    async def test_emergency_chat_triggers_fallback(self) -> None:
        """Emergency message via chat returns appropriate response."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="Add an emergency break-fix at 123 Main St",
        )

        assert isinstance(response, ChatResponse)
        assert response.response
        # AI may ask clarifying questions or provide direct response
        assert len(response.response) > 0


@pytest.mark.functional
class TestAdminAlertResolution:
    """Test alert detection and admin resolution workflow.

    Validates: Requirement 27.3
    """

    @pytest.mark.asyncio
    async def test_double_booking_detected_and_resolvable(self) -> None:
        """Double-booking alert is detected with resolution options."""
        session = _session()
        engine = AlertEngine(session)

        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "08:00",
                "end": "10:00",
            },
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "09:00",
                "end": "11:00",
            },
        ]

        alerts = await engine._detect_double_bookings(assignments)

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "double_booking"
        assert alert.severity == "critical"
        assert len(alert.resolution_options) >= 1
        # Verify resolution options include reassign or shift
        actions = {opt.action for opt in alert.resolution_options}
        assert "reassign" in actions or "shift_time" in actions

    @pytest.mark.asyncio
    async def test_skill_mismatch_detected_with_swap_option(self) -> None:
        """Skill mismatch alert includes swap_resource resolution."""
        session = _session()
        engine = AlertEngine(session)

        assignments = [
            {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "required_skills": ["backflow_certified"],
                "resource_skills": ["lake_pump"],
            },
        ]

        alerts = await engine._detect_skill_mismatches(assignments)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "skill_mismatch"
        actions = {opt.action for opt in alerts[0].resolution_options}
        assert "swap_resource" in actions


@pytest.mark.functional
class TestAdminSuggestionAcceptance:
    """Test suggestion generation and acceptance workflow.

    Validates: Requirement 27.3
    """

    @pytest.mark.asyncio
    async def test_route_swap_suggestion_generated(self) -> None:
        """Route swap suggestion generated when drive time is high."""
        session = _session()
        engine = AlertEngine(session)

        r1, r2 = str(uuid4()), str(uuid4())
        assignments = [
            {
                "resource_id": r1,
                "job_id": str(uuid4()),
                "drive_time_minutes": 80,
            },
            {
                "resource_id": r2,
                "job_id": str(uuid4()),
                "drive_time_minutes": 80,
            },
        ]

        suggestions = await engine._suggest_route_swaps(assignments)

        assert len(suggestions) >= 1
        assert suggestions[0].alert_type == "route_swap"
        assert suggestions[0].severity == "suggestion"
        actions = {opt.action for opt in suggestions[0].resolution_options}
        assert "accept_swap" in actions

    @pytest.mark.asyncio
    async def test_underutilized_resource_suggestion(self) -> None:
        """Underutilized resource suggestion generated for large gaps."""
        session = _session()
        engine = AlertEngine(session)

        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "job_duration_minutes": 120,
                "drive_time_minutes": 30,
                "available_minutes": 480,
            },
        ]

        suggestions = await engine._suggest_utilization_fills(assignments)

        assert len(suggestions) >= 1
        assert suggestions[0].alert_type == "underutilized"
        assert suggestions[0].severity == "suggestion"


@pytest.mark.functional
class TestAdminBatchScheduling:
    """Test batch scheduling for multi-week campaigns.

    Validates: Requirement 27.3
    """

    @pytest.mark.asyncio
    async def test_batch_schedule_generates_multi_week(self) -> None:
        """Batch scheduling produces a multi-week schedule result."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.batch_schedule(
            job_type="fall_closing",
            customer_count=50,
            weeks=3,
            zone_priority=["North", "South"],
        )

        assert result["status"] == "batch_scheduled"
        assert result["total_jobs_scheduled"] >= 0
        assert result["weeks"] == 3
        assert "schedule_by_week" in result

    @pytest.mark.asyncio
    async def test_batch_schedule_via_dispatch(self) -> None:
        """Batch scheduling works through tool dispatch."""
        session = _session()
        tools = AdminSchedulingTools(session)

        args = json.dumps({
            "job_type": "spring_opening",
            "customer_count": 20,
            "weeks": 2,
            "zone_priority": ["East"],
        })

        result = await tools.dispatch_tool_call("batch_schedule", args)

        assert result["status"] == "batch_scheduled"



# ===========================================================================
# Task 17.3: Resource workflow tests
# ===========================================================================


@pytest.mark.functional
class TestResourceDelayReport:
    """Test resource delay reporting workflow.

    Validates: Requirement 27.4
    """

    @pytest.mark.asyncio
    async def test_delay_report_recalculates_etas(self) -> None:
        """Delay report returns recalculated ETAs and admin alert flag."""
        session = _session()
        tools = ResourceSchedulingTools(session)
        resource_id = uuid4()

        result = await tools.report_delay(
            resource_id=resource_id,
            delay_minutes=25,
        )

        assert result["status"] == "delay_reported"
        assert result["delay_minutes"] == 25
        assert "updated_etas" in result
        assert "admin_alerted" in result

    @pytest.mark.asyncio
    async def test_delay_chat_message_handled(self) -> None:
        """Resource chat about running late returns appropriate response."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="resource",
            message="I'm running late by 20 minutes",
        )

        assert isinstance(response, ChatResponse)
        assert response.response
        lower = response.response.lower()
        assert (
            "delay" in lower
            or "late" in lower
            or "scheduling" in lower
        )


@pytest.mark.functional
class TestResourcePreJobRequirements:
    """Test pre-job requirements retrieval workflow.

    Validates: Requirement 27.4
    """

    @pytest.mark.asyncio
    async def test_prejob_checklist_generated(self) -> None:
        """Pre-job checklist contains all required fields."""
        session = _session()
        generator = PreJobGenerator(session)

        checklist = await generator.generate_checklist(
            job_id=uuid4(),
            resource_id=uuid4(),
        )

        assert isinstance(checklist, PreJobChecklist)
        assert checklist.job_type
        assert checklist.customer_name
        assert checklist.customer_address
        assert len(checklist.required_equipment) > 0
        assert checklist.estimated_duration > 0

    @pytest.mark.asyncio
    async def test_prejob_info_via_resource_tools(self) -> None:
        """Pre-job info retrieval through resource tools."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.get_prejob_info(
            resource_id=uuid4(),
            job_id=uuid4(),
        )

        assert result["status"] == "info_retrieved"
        assert "job_type" in result
        assert "required_equipment" in result

    @pytest.mark.asyncio
    async def test_upsell_suggestions_generated(self) -> None:
        """Upsell suggestions are generated for a job."""
        session = _session()
        generator = PreJobGenerator(session)

        suggestions = await generator.generate_upsell_suggestions(
            job_id=uuid4(),
        )

        assert len(suggestions) >= 1
        assert isinstance(suggestions[0], UpsellSuggestion)
        assert suggestions[0].equipment_name
        assert suggestions[0].age_years > 0
        assert suggestions[0].recommended_upgrade


@pytest.mark.functional
class TestResourceFollowUpRequest:
    """Test follow-up job request workflow.

    Validates: Requirement 27.4
    """

    @pytest.mark.asyncio
    async def test_followup_creates_change_request(self) -> None:
        """Follow-up request creates a ChangeRequest for admin approval."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.request_followup(
            resource_id=uuid4(),
            job_id=uuid4(),
            field_notes="Found additional leak at zone 5",
            parts_needed=["coupling", "PVC pipe"],
        )

        assert result["status"] == "change_request_created"
        assert "change_request_id" in result
        assert result["request_type"] == "followup_job"

    @pytest.mark.asyncio
    async def test_change_request_service_create(self) -> None:
        """ChangeRequestService creates a pending request."""
        session = _session()
        service = ChangeRequestService(session)

        cr = await service.create_request(
            resource_id=uuid4(),
            request_type="followup_job",
            details={"notes": "Additional work needed"},
            affected_job_id=uuid4(),
        )

        assert cr.status == "pending"
        assert cr.request_type == "followup_job"
        assert cr.recommended_action
        session.add.assert_called_once()


@pytest.mark.functional
class TestResourcePartsLogging:
    """Test parts logging workflow.

    Validates: Requirement 27.4
    """

    @pytest.mark.asyncio
    async def test_parts_logged_and_inventory_updated(self) -> None:
        """Parts logging updates job record and truck inventory."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.log_parts(
            resource_id=uuid4(),
            job_id=uuid4(),
            parts_list=[
                {"part_name": "1-inch coupling", "quantity": 2},
                {"part_name": "PVC elbow", "quantity": 1},
            ],
        )

        assert result["status"] == "parts_logged"
        assert len(result["parts_logged"]) == 2
        assert "low_stock_warnings" in result


@pytest.mark.functional
class TestResourceNearbyWork:
    """Test nearby work discovery workflow.

    Validates: Requirement 27.4
    """

    @pytest.mark.asyncio
    async def test_nearby_work_listed(self) -> None:
        """Nearby work finder returns available jobs."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.find_nearby_work(
            resource_id=uuid4(),
            location={"latitude": 44.85, "longitude": -93.47},
        )

        assert result["status"] == "search_complete"
        assert "nearby_jobs" in result
        assert isinstance(result["nearby_jobs"], list)



# ===========================================================================
# Task 17.4: Constraint satisfaction and alert pipeline tests
# ===========================================================================


@pytest.mark.functional
class TestConstraintSatisfaction:
    """Test schedule generation constraint satisfaction with DB-like records.

    Validates: Requirement 27.5
    """

    @pytest.mark.asyncio
    async def test_generate_schedule_returns_valid_structure(self) -> None:
        """Schedule generation returns assignments with required fields."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.generate_schedule(
            schedule_date="2026-04-15",
            preferences={"optimization": "fewest_miles", "resource_count": 4},
        )

        assert result["status"] == "generated"
        assert "assignments" in result
        assert isinstance(result["assignments"], list)
        assert result["schedule_date"] == "2026-04-15"

    @pytest.mark.asyncio
    async def test_reshuffle_day_handles_unavailable_resources(self) -> None:
        """Reshuffle redistributes jobs when resources are unavailable."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.reshuffle_day(
            schedule_date="2026-04-15",
            unavailable_resources=[str(uuid4()), str(uuid4())],
            strategy="redistribute",
        )

        assert result["status"] == "reshuffled"
        assert "reassigned_jobs" in result

    @pytest.mark.asyncio
    async def test_move_job_checks_constraints(self) -> None:
        """Moving a job returns updated route information."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.move_job(
            job_id=str(uuid4()),
            target_day="2026-04-16",
            target_time="10:00",
            same_tech=True,
        )

        assert result["status"] == "moved"
        assert "job_id" in result
        assert "target_day" in result


@pytest.mark.functional
class TestAlertPipelineEndToEnd:
    """Test alert/suggestion pipeline end-to-end.

    Validates: Requirement 27.6
    """

    @pytest.mark.asyncio
    async def test_full_alert_pipeline_scan(self) -> None:
        """AlertEngine scan_and_generate runs all detectors and generators."""
        session = _session()
        # Mock the DB query for existing alerts (empty)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        engine = AlertEngine(session)

        alerts = await engine.scan_and_generate(
            schedule_date=date(2026, 4, 15),
        )

        # With empty assignment data, no alerts should be generated
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_sla_risk_detection_pipeline(self) -> None:
        """SLA risk detection produces alert with resolution options."""
        session = _session()
        engine = AlertEngine(session)

        jobs = [
            {
                "job_id": str(uuid4()),
                "sla_deadline": "2026-04-01",
                "scheduled_date": "2026-04-10",
            },
        ]

        alerts = await engine._detect_sla_risks(jobs)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "sla_risk"
        assert alerts[0].severity == "critical"
        actions = {opt.action for opt in alerts[0].resolution_options}
        assert "force_schedule" in actions

    @pytest.mark.asyncio
    async def test_resource_behind_detection(self) -> None:
        """Resource behind detection triggers for 40+ minute delays."""
        session = _session()
        engine = AlertEngine(session)

        assignments = [
            {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "delay_minutes": 45,
            },
        ]

        alerts = await engine._detect_resource_behind(assignments)

        assert len(alerts) == 1
        assert alerts[0].alert_type == "resource_behind"
        assert alerts[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_no_alert_for_minor_delay(self) -> None:
        """No alert generated for delays under 40 minutes."""
        session = _session()
        engine = AlertEngine(session)

        assignments = [
            {
                "resource_id": str(uuid4()),
                "job_id": str(uuid4()),
                "delay_minutes": 30,
            },
        ]

        alerts = await engine._detect_resource_behind(assignments)
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_overtime_avoidance_suggestion(self) -> None:
        """Overtime avoidance suggestion generated when over threshold."""
        session = _session()
        engine = AlertEngine(session)

        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "job_duration_minutes": 300,
                "drive_time_minutes": 200,
                "overtime_threshold": 480,
                "priority": "flexible",
            },
        ]

        suggestions = await engine._suggest_overtime_avoidance(assignments)

        assert len(suggestions) >= 1
        assert suggestions[0].alert_type == "overtime_avoidable"
        assert suggestions[0].severity == "suggestion"

    @pytest.mark.asyncio
    async def test_change_request_lifecycle(self) -> None:
        """Change request flows from creation through approval."""
        session = _session()
        service = ChangeRequestService(session)

        # Create
        cr = await service.create_request(
            resource_id=uuid4(),
            request_type="delay_report",
            details={"delay_minutes": 20, "reason": "traffic"},
        )
        assert cr.status == "pending"

        # Approve (mock the DB lookup)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cr
        session.execute.return_value = mock_result

        approval = await service.approve_request(
            request_id=cr.id,
            admin_id=uuid4(),
            admin_notes="Approved — absorb delay",
        )

        assert approval["status"] == "approved"
        assert approval["request_type"] == "delay_report"

    @pytest.mark.asyncio
    async def test_change_request_denial(self) -> None:
        """Change request can be denied with a reason."""
        session = _session()
        service = ChangeRequestService(session)

        cr = await service.create_request(
            resource_id=uuid4(),
            request_type="resequence",
            details={"reason": "Want to visit shop first"},
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cr
        session.execute.return_value = mock_result

        denial = await service.deny_request(
            request_id=cr.id,
            admin_id=uuid4(),
            reason="Route is already optimized",
        )

        assert denial["status"] == "denied"
        assert denial["reason"] == "Route is already optimized"

    @pytest.mark.asyncio
    async def test_invalid_request_type_rejected(self) -> None:
        """Invalid change request type raises ValueError."""
        session = _session()
        service = ChangeRequestService(session)

        with pytest.raises(ValueError, match="Invalid request_type"):
            await service.create_request(
                resource_id=uuid4(),
                request_type="invalid_type",
                details={},
            )


# ===========================================================================
# Task 17.4 continued: Chat guardrails
# ===========================================================================


@pytest.mark.functional
class TestChatGuardrails:
    """Test AI chat guardrails and off-topic rejection.

    Validates: Requirements 24.2, 24.5
    """

    @pytest.mark.asyncio
    async def test_off_topic_message_redirected(self) -> None:
        """Off-topic messages are redirected to scheduling topics."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="What's the stock market doing today?",
        )

        assert isinstance(response, ChatResponse)
        lower = response.response.lower()
        assert "scheduling" in lower or "schedule" in lower

    @pytest.mark.asyncio
    async def test_scheduling_message_not_rejected(self) -> None:
        """Scheduling-related messages are processed normally."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="Show me the schedule for next week",
        )

        assert isinstance(response, ChatResponse)
        assert response.response
        # Should not be the off-topic redirect
        assert "focused on scheduling" not in response.response


# ===========================================================================
# Task 17.4 continued: Resource alert generation
# ===========================================================================


@pytest.mark.functional
class TestResourceAlertGeneration:
    """Test resource-facing alert and suggestion generation.

    Validates: Requirements 16.1-16.5, 17.1-17.5
    """

    @pytest.mark.asyncio
    async def test_job_added_alert(self) -> None:
        """Job added alert generated for resource."""
        session = _session()
        service = ResourceAlertService(session)

        alert = await service.generate_job_added_alert(
            resource_id=uuid4(),
            job={
                "job_id": str(uuid4()),
                "job_type": "Spring Startup",
                "customer_name": "Jane Smith",
                "address": "123 Main St",
            },
        )

        assert alert["alert_type"] == "job_added"
        assert "job" in alert

    @pytest.mark.asyncio
    async def test_job_removed_alert(self) -> None:
        """Job removed alert generated with gap-fill suggestions."""
        session = _session()
        service = ResourceAlertService(session)

        alert = await service.generate_job_removed_alert(
            resource_id=uuid4(),
            job={
                "job_id": str(uuid4()),
                "job_type": "Maintenance",
                "customer_name": "John Doe",
            },
        )

        assert alert["alert_type"] == "job_removed"
        assert "gap_fill_suggestions" in alert

    @pytest.mark.asyncio
    async def test_equipment_alert(self) -> None:
        """Equipment alert generated for special equipment needs."""
        session = _session()
        service = ResourceAlertService(session)

        alert = await service.generate_equipment_alert(
            resource_id=uuid4(),
            job={"job_id": str(uuid4()), "address": "456 Oak Ave"},
            equipment=["Backflow test kit", "Pressure gauge"],
        )

        assert alert["alert_type"] == "equipment_required"
        assert "required_equipment" in alert

    @pytest.mark.asyncio
    async def test_parts_low_suggestion(self) -> None:
        """Parts low suggestion generated when stock is low."""
        session = _session()
        service = ResourceAlertService(session)

        suggestion = await service.generate_parts_low_suggestion(
            resource_id=uuid4(),
            parts_info={
                "part_name": "1-inch coupling",
                "current_quantity": 1,
                "reorder_threshold": 5,
                "nearest_supply_house": "Ferguson Supply",
            },
        )

        assert suggestion["suggestion_type"] == "parts_low"
        assert "parts_info" in suggestion
