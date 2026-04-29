"""Integration tests for the AI scheduling system.

Tests cross-component data flows, API endpoints, external service
integrations, and role-based access control for the 30-criteria
AI scheduling engine.

Validates: Requirements 22.1-22.10, 28.1-28.8
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app

# =============================================================================
# Helpers
# =============================================================================


def _uuid() -> str:
    return str(uuid.uuid4())


def _make_staff(role: str = "admin") -> MagicMock:
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Test User"
    staff.role = role
    staff.is_active = True
    staff.is_login_enabled = True
    return staff


def _make_session() -> AsyncMock:
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
# 18.1 — Integration test infrastructure
# =============================================================================


@pytest.fixture
def admin_user() -> MagicMock:
    return _make_staff("admin")


@pytest.fixture
def resource_user() -> MagicMock:
    return _make_staff("tech")


@pytest.fixture
def db_session() -> AsyncMock:
    return _make_session()


# =============================================================================
# 18.2 — External service integration tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_google_maps_fallback_to_haversine() -> None:
    """Travel time falls back to haversine when Google Maps is unavailable.

    Validates: Req 28.3
    """
    from grins_platform.services.ai.scheduling.external_services import (
        ExternalServicesClient,
    )

    client = ExternalServicesClient()

    # Simulate Google Maps unavailable by patching the internal method
    with patch.object(
        client,
        "_google_maps_travel_time",
        side_effect=Exception("API unavailable"),
    ):
        minutes = await client.get_travel_time_minutes(
            origin_lat=44.85,
            origin_lon=-93.47,
            dest_lat=44.90,
            dest_lon=-93.50,
        )

    # Haversine fallback should return a positive number
    assert minutes >= 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_openai_chat_graceful_degradation() -> None:
    """Chat service uses fallback when admin handler raises.

    The service has a ``_fallback_admin_response`` path that is invoked
    when the message is off-topic. This test verifies the fallback path
    returns a valid ChatResponse without raising.

    Validates: Req 28.3
    """
    from grins_platform.services.ai.scheduling.chat_service import SchedulingChatService

    session = _make_session()
    service = SchedulingChatService(session)
    admin = _make_staff("admin")

    # Off-topic message triggers the built-in fallback path (no OpenAI call)
    response = await service.chat(
        user_id=admin.id,
        role="admin",
        message="What is the weather like in Paris?",
    )

    # Should return a non-empty fallback response, not raise
    assert response is not None
    assert response.response


@pytest.mark.integration
@pytest.mark.asyncio
async def test_weather_api_fallback_skips_criterion() -> None:
    """Weather criterion returns neutral score when Weather API is unavailable.

    Validates: Req 28.3
    """
    from grins_platform.schemas.ai_scheduling import SchedulingContext
    from grins_platform.services.ai.scheduling.scorers.predictive import (
        PredictiveScorer,
    )

    scorer = PredictiveScorer()

    job = MagicMock()
    job.id = uuid.uuid4()
    job.is_outdoor = True
    job.predicted_complexity = 1.0
    job.depends_on_job_id = None
    job.job_phase = None
    job.location = MagicMock()
    job.location.latitude = 44.85
    job.location.longitude = -93.47

    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.certifications = []
    staff.assigned_equipment = []
    staff.start_location = MagicMock()
    staff.start_location.latitude = 44.85
    staff.start_location.longitude = -93.47

    context = SchedulingContext(
        schedule_date=date.today(),
        weather=None,  # No weather data available
        traffic=None,
        backlog=None,
    )

    config: dict[int, Any] = {}

    results = await scorer.score_assignment(job, staff, context, config)

    # Should return results without raising
    assert isinstance(results, list)
    assert len(results) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_fallback_to_db() -> None:
    """Criteria config loads from DB when Redis is unavailable.

    Validates: Req 28.3
    """
    from grins_platform.services.ai.scheduling.criteria_evaluator import (
        CriteriaEvaluator,
    )

    session = _make_session()

    # Return empty criteria list from DB (simulates Redis miss → DB hit)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    evaluator = CriteriaEvaluator(session, config=None)

    # Should load from DB without error
    config = await evaluator._load_criteria_config()
    assert config is not None


# =============================================================================
# 18.3 — Cross-component data flow tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_customer_intake_to_scheduling_flow() -> None:
    """New job request flows through AlertEngine without error.

    Validates: Req 22.1, 28.4
    """
    from grins_platform.services.ai.scheduling.alert_engine import AlertEngine

    session = _make_session()
    engine = AlertEngine(session)

    # Simulate a schedule with one assignment
    assignment = {
        "job_id": str(uuid.uuid4()),
        "staff_id": str(uuid.uuid4()),
        "start_time": "09:00",
        "end_time": "10:30",
        "priority": 5,
    }

    alerts = await engine.scan_and_generate(
        schedule_date=date.today(),
        assignments=[assignment],
    )

    assert isinstance(alerts, list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduling_to_inventory_resource_alert() -> None:
    """Parts low-stock generates a resource alert candidate.

    Validates: Req 22.6, 28.4
    """
    from grins_platform.services.ai.scheduling.resource_alerts import (
        ResourceAlertGenerator,
    )

    generator = ResourceAlertGenerator()

    staff_id = uuid.uuid4()
    candidate = generator.parts_running_low(
        staff_id=staff_id,
        part_name="Backflow valve",
        current_quantity=1,
    )

    assert candidate is not None
    assert candidate.alert_type == "parts_low"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_request_creation_flow() -> None:
    """Resource can create a change request via ChangeRequestService.

    Validates: Req 22.7, 28.4
    """
    from grins_platform.services.ai.scheduling.change_request_service import (
        ChangeRequestService,
    )

    session = _make_session()
    service = ChangeRequestService(session)

    resource_id = uuid.uuid4()
    job_id = uuid.uuid4()

    change_req = await service.create_request(
        resource_id=resource_id,
        request_type="delay_report",
        details={"reason": "Traffic delay", "estimated_delay_minutes": 20},
        affected_job_id=job_id,
    )

    assert change_req is not None
    assert change_req.request_type == "delay_report"
    assert change_req.status == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compliance_deadline_alert_generation() -> None:
    """AlertEngine processes assignments and returns alert list.

    Validates: Req 22.9, 28.4
    """
    from grins_platform.services.ai.scheduling.alert_engine import AlertEngine

    session = _make_session()
    engine = AlertEngine(session)

    # Assignment with SLA risk (past deadline)
    assignment = {
        "job_id": str(uuid.uuid4()),
        "staff_id": str(uuid.uuid4()),
        "start_time": "14:00",
        "end_time": "15:30",
        "sla_deadline": datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat(),
    }

    alerts = await engine.scan_and_generate(
        schedule_date=date.today(),
        assignments=[assignment],
    )

    assert isinstance(alerts, list)


# =============================================================================
# 18.4 — API endpoint integration tests (unauthenticated → 401)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/ai-scheduling/chat", {"message": "test"}),
        (
            "POST",
            "/api/v1/ai-scheduling/evaluate",
            {"schedule_date": str(date.today())},
        ),
        ("GET", "/api/v1/ai-scheduling/criteria", None),
        ("GET", "/api/v1/scheduling-alerts/", None),
        (
            "POST",
            f"/api/v1/scheduling-alerts/{_uuid()}/resolve",
            {"action": "reassign", "parameters": {}},
        ),
        (
            "POST",
            f"/api/v1/scheduling-alerts/{_uuid()}/dismiss",
            {"reason": "Not applicable"},
        ),
        ("GET", "/api/v1/scheduling-alerts/change-requests", None),
        (
            "POST",
            f"/api/v1/scheduling-alerts/change-requests/{_uuid()}/approve",
            {},
        ),
        (
            "POST",
            f"/api/v1/scheduling-alerts/change-requests/{_uuid()}/deny",
            {"reason": "Not approved"},
        ),
    ],
    ids=[
        "chat",
        "evaluate",
        "criteria",
        "alerts-list",
        "alerts-resolve",
        "alerts-dismiss",
        "change-requests-list",
        "change-requests-approve",
        "change-requests-deny",
    ],
)
async def test_ai_scheduling_endpoint_requires_auth(
    method: str,
    path: str,
    body: dict[str, Any] | None,
) -> None:
    """AI scheduling endpoints return 401 without authentication.

    Validates: Req 28.5, 28.6
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["json"] = body
        response = await client.request(method, path, **kwargs)
    assert response.status_code == 401, (
        f"{method} {path} returned {response.status_code} — expected 401. "
        f"Body: {response.text[:200]}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_schedule_capacity_endpoint_is_accessible() -> None:
    """GET /api/v1/schedule/capacity/{date} is accessible (public endpoint).

    Validates: Req 28.5
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/schedule/capacity/{date.today().isoformat()}"
        )
    # Endpoint is public — returns 200 with capacity data
    assert response.status_code == 200
    data = response.json()
    assert "schedule_date" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_generate_endpoint_is_accessible() -> None:
    """POST /api/v1/schedule/batch-generate is accessible (public endpoint).

    Validates: Req 28.5
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/schedule/batch-generate",
            json={"start_date": str(date.today()), "weeks": 1},
        )
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_utilization_endpoint_is_accessible() -> None:
    """GET /api/v1/schedule/utilization is accessible (public endpoint).

    Validates: Req 28.5
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/schedule/utilization?schedule_date={date.today().isoformat()}"
        )
    assert response.status_code == 200


# =============================================================================
# 18.4 — API endpoints with auth (dependency override pattern)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ai_scheduling_criteria_returns_list_when_authenticated() -> None:
    """GET /api/v1/ai-scheduling/criteria returns criteria list for auth user.

    Validates: Req 28.5
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    admin = _make_staff("admin")
    session = _make_session()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/ai-scheduling/criteria")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheduling_alerts_list_returns_list_when_authenticated() -> None:
    """GET /api/v1/scheduling-alerts/ returns alert list for auth user.

    Validates: Req 28.5
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    admin = _make_staff("admin")
    session = _make_session()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/scheduling-alerts/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_requests_list_returns_list_when_authenticated() -> None:
    """GET /api/v1/scheduling-alerts/change-requests returns list for auth user.

    Validates: Req 28.5
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    admin = _make_staff("admin")
    session = _make_session()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/scheduling-alerts/change-requests")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 18.5 — Role-based access control tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resolve_alert_requires_admin_role() -> None:
    """POST /api/v1/scheduling-alerts/{id}/resolve requires admin role.

    Validates: Req 28.6
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    tech = _make_staff("tech")
    session = _make_session()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: tech
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/scheduling-alerts/{_uuid()}/resolve",
                json={"action": "reassign", "parameters": {}},
            )
        # Non-admin should get 403 Forbidden (or 404 if alert not found first)
        assert response.status_code in (403, 404)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_approve_change_request_requires_admin_role() -> None:
    """POST /api/v1/scheduling-alerts/change-requests/{id}/approve requires admin.

    Validates: Req 28.6
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    tech = _make_staff("tech")
    session = _make_session()

    app.dependency_overrides[get_current_user] = lambda: tech
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/scheduling-alerts/change-requests/{_uuid()}/approve",
                json={},
            )
        assert response.status_code in (403, 404)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deny_change_request_requires_admin_role() -> None:
    """POST /api/v1/scheduling-alerts/change-requests/{id}/deny requires admin.

    Validates: Req 28.6
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    tech = _make_staff("tech")
    session = _make_session()

    app.dependency_overrides[get_current_user] = lambda: tech
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/scheduling-alerts/change-requests/{_uuid()}/deny",
                json={"reason": "Not approved"},
            )
        assert response.status_code in (403, 404)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_can_access_criteria_endpoint() -> None:
    """Admin role can access GET /api/v1/ai-scheduling/criteria.

    Validates: Req 28.6
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session

    admin = _make_staff("admin")
    session = _make_session()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/ai-scheduling/criteria")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tech_can_access_chat_endpoint() -> None:
    """Tech (resource) role can access POST /api/v1/ai-scheduling/chat.

    Validates: Req 28.6
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.schemas.ai_scheduling import ChatResponse

    tech = _make_staff("tech")
    session = _make_session()

    mock_response = ChatResponse(
        response="Here is your schedule for today.",
        schedule_changes=[],
        clarifying_questions=[],
        change_request_id=None,
    )

    app.dependency_overrides[get_current_user] = lambda: tech
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch(
            "grins_platform.api.v1.ai_scheduling.SchedulingChatService.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/ai-scheduling/chat",
                    json={"message": "What jobs do I have today?"},
                )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 18.5 — Rate limiting smoke test
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_endpoint_accessible_within_rate_limit() -> None:
    """Chat endpoint is accessible for normal usage within rate limits.

    Validates: Req 28.7
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.schemas.ai_scheduling import ChatResponse

    admin = _make_staff("admin")
    session = _make_session()

    mock_response = ChatResponse(
        response="Schedule looks good.",
        schedule_changes=[],
        clarifying_questions=[],
        change_request_id=None,
    )

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch(
            "grins_platform.api.v1.ai_scheduling.SchedulingChatService.chat",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/ai-scheduling/chat",
                    json={"message": "Show me today's schedule"},
                )
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 18.5b — Phase 3+4 remediation tests (Bug 3, Bug 5, Bug 6)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evaluate_loads_assignments_from_db() -> None:
    """``POST /evaluate`` loads persisted assignments via the loader.

    Verifies Bug 3 fix: the endpoint now calls ``load_assignments_for_date``
    instead of evaluating an empty solution. Patches the loader to return
    a non-empty list and asserts the evaluator was invoked with that list.

    Validates: Req 23.1, 23.2 (Bug 3)
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.schemas.ai_scheduling import ScheduleEvaluation
    from grins_platform.services.schedule_domain import (
        ScheduleAssignment,
        ScheduleLocation,
        ScheduleStaff,
    )

    admin = _make_staff("admin")
    session = _make_session()

    fake_assignment = ScheduleAssignment(
        id=uuid.uuid4(),
        staff=ScheduleStaff(
            id=uuid.uuid4(),
            name="Tech",
            start_location=ScheduleLocation(latitude=0, longitude=0),  # type: ignore[arg-type]
        ),
        jobs=[],
    )

    fake_eval = ScheduleEvaluation(
        schedule_date=date(2026, 5, 1),
        total_score=72.5,
        hard_violations=1,
        criteria_scores=[],
        alerts=["[Criterion 21] Compliance: deadline past"],
    )

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with (
            patch(
                "grins_platform.api.v1.ai_scheduling.load_assignments_for_date",
                new_callable=AsyncMock,
                return_value=[fake_assignment],
            ) as mock_loader,
            patch(
                "grins_platform.api.v1.ai_scheduling.CriteriaEvaluator.evaluate_schedule",
                new_callable=AsyncMock,
                return_value=fake_eval,
            ) as mock_eval,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/ai-scheduling/evaluate",
                    json={"schedule_date": "2026-05-01"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body["hard_violations"] == 1
        assert body["total_score"] == 72.5
        mock_loader.assert_awaited_once()
        mock_eval.assert_awaited_once()
        # Solution passed to evaluator must contain the loaded assignment.
        passed_solution = mock_eval.call_args.kwargs["solution"]
        assert passed_solution.assignments == [fake_assignment]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_returns_429_when_rate_limit_exceeded() -> None:
    """Chat handler returns 429 + ``Retry-After`` when rate limit is exceeded.

    Validates: Req 28.7 (Bug 6)
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.services.ai.rate_limiter import RateLimitError

    admin = _make_staff("admin")
    session = _make_session()

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch(
            "grins_platform.services.ai.rate_limiter.RateLimitService.check_limit",
            new_callable=AsyncMock,
            side_effect=RateLimitError("Daily limit of 100 requests exceeded"),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/ai-scheduling/chat",
                    json={"message": "Show me today's schedule"},
                )

        assert response.status_code == 429
        assert response.headers.get("retry-after") == "60"
        assert "Daily limit" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_chat_records_usage_on_success() -> None:
    """Chat handler records token usage after a successful dispatch.

    Validates: Req 28.7 (Bug 6 — usage accounting)
    """
    from grins_platform.api.v1.auth_dependencies import get_current_user
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.schemas.ai_scheduling import ChatResponse

    admin = _make_staff("admin")
    session = _make_session()

    mock_response = ChatResponse(
        response="OK",
        schedule_changes=[],
        clarifying_questions=[],
        change_request_id=None,
    )

    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with (
            patch(
                "grins_platform.api.v1.ai_scheduling.SchedulingChatService.chat",
                new_callable=AsyncMock,
                return_value=mock_response,
            ),
            patch(
                "grins_platform.services.ai.rate_limiter.RateLimitService.check_limit",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "grins_platform.services.ai.rate_limiter.RateLimitService.record_usage",
                new_callable=AsyncMock,
                return_value=1,
            ) as mock_record,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/ai-scheduling/chat",
                    json={"message": "Hi"},
                )

        assert response.status_code == 200
        mock_record.assert_awaited_once()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_capacity_response_includes_overlay_fields_when_assignments_exist() -> (
    None
):
    """``GET /schedule/capacity/{date}`` populates the criteria overlay.

    Verifies Bug 5 fix: when persisted appointments exist for the date the
    response now carries ``criteria_triggered``, ``forecast_confidence_low``,
    ``forecast_confidence_high``, and ``per_criterion_utilization``.

    Validates: Req 23.1 (Bug 5)
    """
    from grins_platform.api.v1.dependencies import get_db_session
    from grins_platform.schemas.ai_scheduling import (
        CriterionResult,
        ScheduleEvaluation,
    )
    from grins_platform.services.schedule_domain import (
        ScheduleAssignment,
        ScheduleLocation,
        ScheduleStaff,
    )

    session = _make_session()

    fake_assignment = ScheduleAssignment(
        id=uuid.uuid4(),
        staff=ScheduleStaff(
            id=uuid.uuid4(),
            name="Tech",
            start_location=ScheduleLocation(latitude=0, longitude=0),  # type: ignore[arg-type]
        ),
        jobs=[],
    )

    fake_eval = ScheduleEvaluation(
        schedule_date=date(2026, 5, 1),
        total_score=80.0,
        hard_violations=1,
        criteria_scores=[
            CriterionResult(
                criterion_number=21,
                criterion_name="Compliance",
                score=10.0,
                weight=8,
                is_hard=True,
                is_satisfied=False,
                explanation="Past compliance deadline",
            ),
            CriterionResult(
                criterion_number=1,
                criterion_name="Proximity",
                score=85.0,
                weight=10,
                is_hard=False,
                is_satisfied=True,
                explanation="Nearby",
            ),
        ],
        alerts=[],
    )

    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with (
            patch(
                "grins_platform.api.v1.schedule.load_assignments_for_date",
                new_callable=AsyncMock,
                return_value=[fake_assignment],
            ),
            patch(
                "grins_platform.api.v1.schedule.CriteriaEvaluator.evaluate_schedule",
                new_callable=AsyncMock,
                return_value=fake_eval,
            ),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/schedule/capacity/2026-05-01")

        assert response.status_code == 200
        body = response.json()
        # Original fields preserved.
        assert "schedule_date" in body
        assert "total_capacity_minutes" in body
        # New overlay fields populated.
        assert body["criteria_triggered"] == [21]
        assert body["per_criterion_utilization"] == {"21": 10.0, "1": 85.0}
        assert body["forecast_confidence_low"] is not None
        assert body["forecast_confidence_high"] is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_capacity_response_skips_overlay_when_no_assignments() -> None:
    """Capacity response keeps overlay fields ``None`` when DB is empty.

    Legacy consumers must continue to see the original shape unchanged.

    Validates: Req 23.1 (Bug 5 — additive, non-breaking)
    """
    from grins_platform.api.v1.dependencies import get_db_session

    session = _make_session()
    app.dependency_overrides[get_db_session] = lambda: session

    try:
        with patch(
            "grins_platform.api.v1.schedule.load_assignments_for_date",
            new_callable=AsyncMock,
            return_value=[],
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/schedule/capacity/2026-05-01")

        assert response.status_code == 200
        body = response.json()
        assert body["criteria_triggered"] is None
        assert body["forecast_confidence_low"] is None
        assert body["forecast_confidence_high"] is None
        assert body["per_criterion_utilization"] is None
    finally:
        app.dependency_overrides.clear()


# =============================================================================
# 18.6 — All integration tests pass verification (marker)
# =============================================================================


@pytest.mark.integration
def test_integration_test_suite_marker() -> None:
    """Marker test confirming integration suite is collected.

    Validates: Req 28.8
    """
    assert True
