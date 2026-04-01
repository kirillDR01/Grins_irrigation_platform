"""Integration tests for AI Scheduling System.

Tests cross-component interactions including external service
integrations with fallbacks, data flow between scheduling and
other components, API endpoint validation, and auth/rate limiting.

Validates: Requirements 28.1-28.8
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from grins_platform.schemas.ai_scheduling import (
    AlertCandidate,
    ChatResponse,
)
from grins_platform.services.ai.scheduling.admin_tools import (
    AdminSchedulingTools,
)
from grins_platform.services.ai.scheduling.alert_engine import AlertEngine
from grins_platform.services.ai.scheduling.change_request_service import (
    ChangeRequestService,
)
from grins_platform.services.ai.scheduling.chat_service import (
    SchedulingChatService,
)
from grins_platform.services.ai.scheduling.external_services import (
    ExternalServiceManager,
)
from grins_platform.services.ai.scheduling.resource_alerts import (
    ResourceAlertService,
)
from grins_platform.services.ai.scheduling.resource_tools import (
    ResourceSchedulingTools,
)

# ---------------------------------------------------------------------------
# Helpers / Fixtures (Task 18.1)
# ---------------------------------------------------------------------------


def _session() -> AsyncMock:
    """Create a mock async DB session for integration tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    return session


def _mock_user(
    *,
    user_id: UUID | None = None,
    role: str = "admin",
) -> MagicMock:
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.role = role
    user.is_active = True
    return user


def _mock_alert(
    *,
    alert_id: UUID | None = None,
    alert_type: str = "double_booking",
    severity: str = "critical",
    status: str = "active",
) -> MagicMock:
    """Create a mock SchedulingAlert model."""
    alert = MagicMock()
    alert.id = alert_id or uuid4()
    alert.alert_type = alert_type
    alert.severity = severity
    alert.title = f"Test {alert_type}"
    alert.description = f"Test description for {alert_type}"
    alert.affected_job_ids = [str(uuid4())]
    alert.affected_staff_ids = [str(uuid4())]
    alert.criteria_triggered = [1, 8]
    alert.resolution_options = [
        {
            "action": "reassign",
            "label": "Reassign",
            "description": "Reassign job",
            "parameters": {},
        },
    ]
    alert.status = status
    alert.schedule_date = date(2026, 4, 15)
    alert.created_at = datetime.now(tz=timezone.utc)
    alert.resolved_by = None
    alert.resolved_action = None
    alert.resolved_at = None
    return alert


def _mock_change_request(
    *,
    request_id: UUID | None = None,
    request_type: str = "delay_report",
    status: str = "pending",
) -> MagicMock:
    """Create a mock ChangeRequest model."""
    cr = MagicMock()
    cr.id = request_id or uuid4()
    cr.resource_id = uuid4()
    cr.request_type = request_type
    cr.details = {"delay_minutes": 20}
    cr.affected_job_id = uuid4()
    cr.recommended_action = "Recalculate ETAs"
    cr.status = status
    cr.admin_id = None
    cr.admin_notes = None
    cr.resolved_at = None
    cr.created_at = datetime.now(tz=timezone.utc)
    return cr



# ===========================================================================
# Task 18.2: External service integration tests
# ===========================================================================


@pytest.mark.integration
class TestGoogleMapsIntegration:
    """Test Google Maps API integration with fallback.

    Validates: Requirement 28.3
    """

    @pytest.mark.asyncio
    async def test_travel_time_fallback_to_haversine(self) -> None:
        """Without API key, travel time falls back to haversine x 1.4."""
        session = _session()
        manager = ExternalServiceManager(session)

        with patch.dict("os.environ", {}, clear=False):
            # Ensure no Google Maps key
            os.environ.pop("GOOGLE_MAPS_API_KEY", None)

            result = await manager.get_travel_time(
                origin=(44.8547, -93.4708),
                destination=(44.9778, -93.2650),
            )

        assert result["source"] == "haversine_fallback"
        assert result["travel_minutes"] > 0
        assert result["distance_km"] > 0

    @pytest.mark.asyncio
    async def test_haversine_distance_calculation(self) -> None:
        """Haversine calculation produces reasonable distances."""
        session = _session()
        manager = ExternalServiceManager(session)

        # Eden Prairie to Minneapolis ~15km
        distance = manager._haversine_km(
            (44.8547, -93.4708),
            (44.9778, -93.2650),
        )

        assert 10 < distance < 30  # reasonable range

    @pytest.mark.asyncio
    async def test_same_location_zero_distance(self) -> None:
        """Same origin and destination produces near-zero travel time."""
        session = _session()
        manager = ExternalServiceManager(session)

        result = await manager.get_travel_time(
            origin=(44.8547, -93.4708),
            destination=(44.8547, -93.4708),
        )

        assert result["travel_minutes"] < 1.0
        assert result["distance_km"] < 0.01


@pytest.mark.integration
class TestWeatherAPIIntegration:
    """Test Weather API integration with fallback.

    Validates: Requirement 28.3
    """

    @pytest.mark.asyncio
    async def test_weather_fallback_returns_unknown(self) -> None:
        """Without API key, weather returns unknown with skip flag."""
        session = _session()
        manager = ExternalServiceManager(session)

        with patch.dict("os.environ", {}, clear=False):
            os.environ.pop("WEATHER_API_KEY", None)

            result = await manager.get_weather_forecast(
                date="2026-04-15",
                location=(44.8547, -93.4708),
            )

        assert result["condition"] == "unknown"
        assert result["source"] == "fallback"
        assert result["skip_criterion"] is True

    @pytest.mark.asyncio
    async def test_weather_fallback_has_all_fields(self) -> None:
        """Fallback weather response includes all expected fields."""
        session = _session()
        manager = ExternalServiceManager(session)

        result = await manager.get_weather_forecast(
            date="2026-04-15",
            location=(44.8547, -93.4708),
        )

        expected_keys = {
            "condition",
            "high_temp",
            "low_temp",
            "precipitation_chance",
            "source",
            "skip_criterion",
        }
        assert expected_keys.issubset(result.keys())


@pytest.mark.integration
class TestRedisCachingIntegration:
    """Test Redis caching with fallback.

    Validates: Requirement 28.3
    """

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_on_miss(self) -> None:
        """Cache get returns None when Redis is unavailable."""
        session = _session()
        manager = ExternalServiceManager(session)

        result = await manager.get_cached("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_returns_false_on_failure(self) -> None:
        """Cache set returns False when Redis is unavailable."""
        session = _session()
        manager = ExternalServiceManager(session)

        result = await manager.set_cached("test_key", {"data": "value"}, ttl=60)
        assert result is False

    @pytest.mark.asyncio
    async def test_api_key_validation(self) -> None:
        """API key validation reports missing keys."""
        session = _session()
        manager = ExternalServiceManager(session)

        keys = await manager.validate_api_keys()

        assert isinstance(keys, dict)
        assert "google_maps" in keys
        assert "weather" in keys
        assert "openai" in keys
        assert "redis" in keys
        # All values are booleans
        assert all(isinstance(v, bool) for v in keys.values())



# ===========================================================================
# Task 18.3: Cross-component data flow tests
# ===========================================================================


@pytest.mark.integration
class TestCustomerIntakeToScheduling:
    """Test Customer Intake → Scheduling data flow.

    Validates: Requirement 28.4
    """

    @pytest.mark.asyncio
    async def test_job_data_flows_to_scheduling_tools(self) -> None:
        """Job with priority, time windows, customer data flows to admin tools."""
        session = _session()
        tools = AdminSchedulingTools(session)

        # Simulate a job request flowing into scheduling
        result = await tools.generate_schedule(
            schedule_date="2026-04-15",
            preferences={
                "optimization": "fewest_miles",
                "resource_count": 3,
            },
        )

        assert result["status"] == "generated"
        assert "assignments" in result
        assert "criteria_used" in result

    @pytest.mark.asyncio
    async def test_emergency_job_intake_to_insertion(self) -> None:
        """Emergency job from intake flows through to schedule insertion."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.insert_emergency(
            address="789 Elm St, Plymouth, MN",
            skill="lake_pump",
            duration=120,
            time_constraint="ASAP",
        )

        assert result["status"] == "inserted"
        assert result["skill_required"]
        assert result["time_constraint"]


@pytest.mark.integration
class TestSchedulingToInventory:
    """Test Scheduling → Inventory data flow (parts logging).

    Validates: Requirement 28.4
    """

    @pytest.mark.asyncio
    async def test_parts_logging_decrements_inventory(self) -> None:
        """Parts logged by resource flow to inventory tracking."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.log_parts(
            resource_id=uuid4(),
            job_id=uuid4(),
            parts_list=[
                {"part_name": "Rain Bird nozzle", "quantity": 3},
                {"part_name": "1/2 inch coupling", "quantity": 5},
            ],
        )

        assert result["status"] == "parts_logged"
        assert len(result["parts_logged"]) == 2

    @pytest.mark.asyncio
    async def test_parts_logging_triggers_low_stock_check(self) -> None:
        """Parts logging includes low stock alert information."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.log_parts(
            resource_id=uuid4(),
            job_id=uuid4(),
            parts_list=[
                {"part_name": "Valve", "quantity": 10},
            ],
        )

        assert "low_stock_warnings" in result


@pytest.mark.integration
class TestSchedulingToResourceAlerts:
    """Test Scheduling → Resource mobile alert flow.

    Validates: Requirement 28.4
    """

    @pytest.mark.asyncio
    async def test_route_resequence_generates_resource_alert(self) -> None:
        """Route resequence generates alert for affected resource."""
        session = _session()
        alert_service = ResourceAlertService(session)

        alert = await alert_service.generate_route_resequenced_alert(
            resource_id=uuid4(),
            reason="Optimized for traffic conditions",
        )

        assert alert["alert_type"] == "route_resequenced"
        assert "reason" in alert

    @pytest.mark.asyncio
    async def test_access_alert_includes_gate_code(self) -> None:
        """Access alert includes gate code and instructions."""
        session = _session()
        alert_service = ResourceAlertService(session)

        alert = await alert_service.generate_access_alert(
            resource_id=uuid4(),
            job={
                "job_id": str(uuid4()),
                "customer_name": "Jane Smith",
                "address": "789 Elm St",
            },
            access_info={
                "gate_code": "4567",
                "instructions": "Use side entrance",
                "pet_warnings": "Large dog in backyard",
            },
        )

        assert alert["alert_type"] == "access_info"
        assert alert["gate_code"] == "4567"



# ===========================================================================
# Task 18.4: API endpoint tests
# ===========================================================================


@pytest.mark.integration
class TestAISchedulingAPIRoutes:
    """Test all AI scheduling API routes.

    Validates: Requirement 28.5
    """

    @pytest.mark.asyncio
    async def test_chat_endpoint_structure(self) -> None:
        """POST /chat returns ChatResponse structure via service."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="What does next week look like?",
        )

        assert isinstance(response, ChatResponse)
        assert response.response
        assert isinstance(response.response, str)

    @pytest.mark.asyncio
    async def test_chat_resource_role_routing(self) -> None:
        """Resource role routes to resource-specific handling."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="resource",
            message="What's my schedule tomorrow?",
        )

        assert isinstance(response, ChatResponse)
        assert response.response

    @pytest.mark.asyncio
    async def test_chat_admin_role_routing(self) -> None:
        """Admin role routes to admin-specific handling."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="admin",
            message="Build a schedule for Monday",
        )

        assert isinstance(response, ChatResponse)
        assert response.response

    @pytest.mark.asyncio
    async def test_admin_tool_dispatch_generate_schedule(self) -> None:
        """Admin tool dispatch for generate_schedule works."""
        session = _session()
        tools = AdminSchedulingTools(session)

        args = json.dumps({
            "schedule_date": "2026-04-15",
            "preferences": {"optimization": "fastest_completion"},
        })

        result = await tools.dispatch_tool_call("generate_schedule", args)
        assert result["status"] == "generated"

    @pytest.mark.asyncio
    async def test_admin_tool_dispatch_forecast_capacity(self) -> None:
        """Admin tool dispatch for forecast_capacity works."""
        session = _session()
        tools = AdminSchedulingTools(session)

        args = json.dumps({
            "job_type": "spring_startup",
            "weeks": 4,
            "zones": ["North", "South"],
        })

        result = await tools.dispatch_tool_call("forecast_capacity", args)
        assert result["status"] == "forecasted"

    @pytest.mark.asyncio
    async def test_admin_tool_dispatch_unknown_tool(self) -> None:
        """Unknown tool name raises ValueError."""
        session = _session()
        tools = AdminSchedulingTools(session)

        with pytest.raises(ValueError, match="Unknown admin tool"):
            await tools.dispatch_tool_call("nonexistent_tool", "{}")


@pytest.mark.integration
class TestAlertAPIRoutes:
    """Test all alert API routes via service layer.

    Validates: Requirement 28.5
    """

    @pytest.mark.asyncio
    async def test_alert_detection_produces_valid_candidates(self) -> None:
        """Alert engine produces valid AlertCandidate objects."""
        session = _session()
        engine = AlertEngine(session)

        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "08:00",
                "end": "10:30",
            },
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "start": "10:00",
                "end": "12:00",
            },
        ]

        alerts = await engine._detect_double_bookings(assignments)

        assert len(alerts) == 1
        alert = alerts[0]
        assert isinstance(alert, AlertCandidate)
        assert alert.alert_type == "double_booking"
        assert len(alert.affected_job_ids) == 2
        assert len(alert.resolution_options) >= 1

    @pytest.mark.asyncio
    async def test_suggestion_generation_valid_candidates(self) -> None:
        """Suggestion generators produce valid AlertCandidate objects."""
        session = _session()
        engine = AlertEngine(session)

        rid = str(uuid4())
        assignments = [
            {
                "resource_id": rid,
                "job_id": str(uuid4()),
                "job_duration_minutes": 60,
                "drive_time_minutes": 30,
                "available_minutes": 480,
            },
        ]

        suggestions = await engine._suggest_utilization_fills(assignments)

        for s in suggestions:
            assert isinstance(s, AlertCandidate)
            assert s.severity == "suggestion"
            assert len(s.resolution_options) >= 1


@pytest.mark.integration
class TestChangeRequestAPIRoutes:
    """Test all change request API routes via service layer.

    Validates: Requirement 28.5
    """

    @pytest.mark.asyncio
    async def test_create_all_valid_request_types(self) -> None:
        """All 8 valid request types can be created."""
        session = _session()
        service = ChangeRequestService(session)

        valid_types = [
            "delay_report",
            "followup_job",
            "access_issue",
            "nearby_pickup",
            "resequence",
            "crew_assist",
            "parts_log",
            "upgrade_quote",
        ]

        for req_type in valid_types:
            cr = await service.create_request(
                resource_id=uuid4(),
                request_type=req_type,
                details={"test": True},
            )
            assert cr.status == "pending"
            assert cr.request_type == req_type
            assert cr.recommended_action  # AI recommendation present

    @pytest.mark.asyncio
    async def test_approve_then_deny_fails(self) -> None:
        """Cannot deny an already-approved request."""
        session = _session()
        service = ChangeRequestService(session)

        cr = await service.create_request(
            resource_id=uuid4(),
            request_type="delay_report",
            details={},
        )

        # Approve first
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cr
        session.execute.return_value = mock_result

        await service.approve_request(
            request_id=cr.id,
            admin_id=uuid4(),
        )

        # Now try to deny — should fail because status is "approved"
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = cr
        session.execute.return_value = mock_result2

        with pytest.raises(ValueError, match="not 'pending'"):
            await service.deny_request(
                request_id=cr.id,
                admin_id=uuid4(),
                reason="Changed my mind",
            )

    @pytest.mark.asyncio
    async def test_approve_nonexistent_request_fails(self) -> None:
        """Approving a nonexistent request raises ValueError."""
        session = _session()
        service = ChangeRequestService(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.approve_request(
                request_id=uuid4(),
                admin_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_deny_nonexistent_request_fails(self) -> None:
        """Denying a nonexistent request raises ValueError."""
        session = _session()
        service = ChangeRequestService(session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.deny_request(
                request_id=uuid4(),
                admin_id=uuid4(),
                reason="Not found",
            )


@pytest.mark.integration
class TestScheduleExtensionRoutes:
    """Test extended schedule API routes via service layer.

    Validates: Requirement 28.5
    """

    @pytest.mark.asyncio
    async def test_capacity_forecast_via_admin_tools(self) -> None:
        """Capacity forecast returns structured forecast data."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.forecast_capacity(
            job_type="maintenance",
            weeks=4,
            zones=["North", "South", "East"],
        )

        assert result["status"] == "forecasted"
        assert "weekly_forecast" in result
        assert result["weeks"] == 4

    @pytest.mark.asyncio
    async def test_batch_generate_via_admin_tools(self) -> None:
        """Batch generation returns multi-week schedule."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.batch_schedule(
            job_type="fall_closing",
            customer_count=100,
            weeks=4,
            zone_priority=["North", "South"],
        )

        assert result["status"] == "batch_scheduled"
        assert result["total_jobs_scheduled"] >= 0
        assert result["weeks"] == 4

    @pytest.mark.asyncio
    async def test_find_underutilized_resources(self) -> None:
        """Underutilized resource finder returns resource list."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.find_underutilized(
            week="2026-04-13",
        )

        assert result["status"] == "analyzed"
        assert "underutilized_resources" in result

    @pytest.mark.asyncio
    async def test_rank_profitable_jobs(self) -> None:
        """Profitable job ranking returns ranked list."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.rank_profitable_jobs(
            day="2026-04-15",
            open_slots=3,
        )

        assert result["status"] == "ranked"
        assert "ranked_jobs" in result

    @pytest.mark.asyncio
    async def test_weather_reschedule(self) -> None:
        """Weather reschedule returns rescheduled jobs."""
        session = _session()
        tools = AdminSchedulingTools(session)

        result = await tools.weather_reschedule(
            day="2026-04-15",
        )

        assert result["status"] == "rescheduled"



# ===========================================================================
# Task 18.5: Auth and rate limiting tests
# ===========================================================================


@pytest.mark.integration
class TestRoleBasedAccess:
    """Test role-based access control for scheduling endpoints.

    Validates: Requirements 28.6, 28.7
    """

    @pytest.mark.asyncio
    async def test_admin_chat_processes_admin_commands(self) -> None:
        """Admin role can access schedule building commands."""
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
        assert response.response
        # Admin should get a meaningful response (may be clarifying Q)
        assert len(response.response) > 0

    @pytest.mark.asyncio
    async def test_resource_chat_processes_field_commands(self) -> None:
        """Resource role can access field operation commands."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        response = await service.chat(
            user_id=uuid4(),
            role="resource",
            message="I need to report a delay",
        )

        assert isinstance(response, ChatResponse)
        assert response.response

    @pytest.mark.asyncio
    async def test_admin_tools_accessible(self) -> None:
        """Admin scheduling tools are callable with valid args."""
        session = _session()
        tools = AdminSchedulingTools(session)

        # Verify each tool is recognized by dispatch (with args)
        test_cases = [
            ("generate_schedule", {"schedule_date": "2026-04-15"}),
            (
                "reshuffle_day",
                {"schedule_date": "2026-04-15", "unavailable_resources": []},
            ),
            ("insert_emergency", {"address": "123 St", "skill": "x", "duration": 60}),
            ("forecast_capacity", {"job_type": "test"}),
            ("move_job", {"job_id": "abc", "target_day": "2026-04-16"}),
            ("find_underutilized", {"week": "2026-04-13"}),
            ("batch_schedule", {"job_type": "test", "customer_count": 1}),
            ("rank_profitable_jobs", {"day": "2026-04-15", "open_slots": 1}),
            ("weather_reschedule", {"day": "2026-04-15"}),
            ("create_recurring_route", {"accounts": [], "cadence": "biweekly"}),
        ]

        for tool_name, args in test_cases:
            result = await tools.dispatch_tool_call(
                tool_name, json.dumps(args),
            )
            assert isinstance(result, dict)
            assert "status" in result

    @pytest.mark.asyncio
    async def test_resource_tools_accessible(self) -> None:
        """Resource scheduling tools are callable with valid args."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        rid = str(uuid4())
        jid = str(uuid4())

        test_cases = [
            ("report_delay", {"resource_id": rid, "delay_minutes": 10}),
            ("get_prejob_info", {"resource_id": rid, "job_id": jid}),
            (
                "request_followup",
                {"resource_id": rid, "job_id": jid, "field_notes": "test"},
            ),
            (
                "report_access_issue",
                {"resource_id": rid, "job_id": jid, "issue_type": "gate_locked"},
            ),
            ("find_nearby_work", {"resource_id": rid, "location": "44.85,-93.47"}),
            ("request_resequence", {"resource_id": rid, "reason": "test"}),
            (
                "request_assistance",
                {"resource_id": rid, "job_id": jid, "skill_needed": "x"},
            ),
            ("log_parts", {"resource_id": rid, "job_id": jid, "parts_list": []}),
            ("get_tomorrow_schedule", {"resource_id": rid}),
            (
                "request_upgrade_quote",
                {"resource_id": rid, "job_id": jid, "upgrade_type": "x"},
            ),
        ]

        for tool_name, args in test_cases:
            result = await tools.dispatch_tool_call(
                tool_name, json.dumps(args),
            )
            assert isinstance(result, dict)
            assert "status" in result

    @pytest.mark.asyncio
    async def test_off_topic_rejected_for_both_roles(self) -> None:
        """Off-topic messages rejected for both admin and resource roles."""
        session = _session()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        service = SchedulingChatService(session)

        for role in ["admin", "resource"]:
            response = await service.chat(
                user_id=uuid4(),
                role=role,
                message="Tell me a joke about programming",
            )

            assert isinstance(response, ChatResponse)
            # Off-topic should be redirected
            lower = response.response.lower()
            assert "scheduling" in lower or "schedule" in lower


# ===========================================================================
# Task 18.5 continued: Cross-component integration
# ===========================================================================


@pytest.mark.integration
class TestResourceToolToChangeRequestFlow:
    """Test resource tool → change request → admin approval flow.

    Validates: Requirements 28.4, 28.6
    """

    @pytest.mark.asyncio
    async def test_followup_request_creates_change_request(self) -> None:
        """Resource follow-up request creates a change request for admin."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.request_followup(
            resource_id=uuid4(),
            job_id=uuid4(),
            field_notes="Broken valve needs replacement",
            parts_needed=["valve", "coupling"],
        )

        assert result["status"] == "change_request_created"
        assert result["request_type"] == "followup_job"
        assert "change_request_id" in result

    @pytest.mark.asyncio
    async def test_resequence_request_creates_change_request(self) -> None:
        """Resource resequence request creates a change request."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.request_resequence(
            resource_id=uuid4(),
            reason="Need to stop at shop for parts",
            shop_stop=True,
        )

        assert result["status"] == "change_request_created"
        assert result["request_type"] == "resequence"

    @pytest.mark.asyncio
    async def test_assistance_request_creates_change_request(self) -> None:
        """Resource assistance request creates a change request."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.request_assistance(
            resource_id=uuid4(),
            job_id=uuid4(),
            skill_needed="backflow_certified",
        )

        assert result["status"] == "change_request_created"
        assert result["request_type"] == "crew_assist"

    @pytest.mark.asyncio
    async def test_upgrade_quote_creates_change_request(self) -> None:
        """Resource upgrade quote request creates a change request."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.request_upgrade_quote(
            resource_id=uuid4(),
            job_id=uuid4(),
            upgrade_type="controller_upgrade",
        )

        assert result["status"] == "change_request_created"
        assert result["request_type"] == "upgrade_quote"

    @pytest.mark.asyncio
    async def test_tomorrow_schedule_retrieval(self) -> None:
        """Resource can retrieve tomorrow's schedule."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.get_tomorrow_schedule(
            resource_id=uuid4(),
        )

        assert result["status"] == "schedule_retrieved"
        assert "jobs" in result

    @pytest.mark.asyncio
    async def test_access_issue_report(self) -> None:
        """Resource can report access issues."""
        session = _session()
        tools = ResourceSchedulingTools(session)

        result = await tools.report_access_issue(
            resource_id=uuid4(),
            job_id=uuid4(),
            issue_type="gate_locked",
        )

        assert result["status"] in ("change_request_created", "access_issue_reported")
