"""Unit tests for password hardening and dashboard alert navigation.

Tests:
- Password validation criteria (16+ chars, mixed case, digits, symbol)
- Bcrypt hashing at cost 12
- Env var missing abort
- Dashboard alert target_url generation (single vs multi-record)
- Highlight URL param structure

Validates: Requirements 1.1, 1.2, 1.4, 3.1, 3.4
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest

from grins_platform.schemas.dashboard import DashboardAlert
from grins_platform.services.dashboard_service import DashboardService

# Import validate_password from the standalone script
sys.path.insert(0, "scripts")
import harden_admin_password
from harden_admin_password import validate_password

sys.path.pop(0)


# ---------------------------------------------------------------------------
# Password Validation Tests (Req 1.1, 1.2, 1.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPasswordValidation:
    """Tests for password strength validation criteria."""

    def test_valid_password_returns_no_errors(self) -> None:
        """A password meeting all criteria returns empty error list."""
        assert validate_password("MyStr0ng!Passphrase") == []

    def test_too_short_password(self) -> None:
        """Password under 16 chars returns length error."""
        errors = validate_password("Short1!aB")
        assert any("16 characters" in e for e in errors)

    def test_missing_lowercase(self) -> None:
        """Password without lowercase returns error."""
        errors = validate_password("ALLUPPERCASE1234!@")
        assert any("lowercase" in e for e in errors)

    def test_missing_uppercase(self) -> None:
        """Password without uppercase returns error."""
        errors = validate_password("alllowercase1234!@")
        assert any("uppercase" in e for e in errors)

    def test_missing_digit(self) -> None:
        """Password without digits returns error."""
        errors = validate_password("NoDigitsHere!@abcd")
        assert any("digit" in e for e in errors)

    def test_missing_symbol(self) -> None:
        """Password without symbols returns error."""
        errors = validate_password("NoSymbolsHere1234Ab")
        assert any("symbol" in e for e in errors)

    def test_multiple_failures(self) -> None:
        """Password failing multiple criteria returns multiple errors."""
        errors = validate_password("short")
        assert len(errors) >= 3  # too short, missing uppercase, digit, symbol

    def test_exactly_16_chars_valid(self) -> None:
        """Password of exactly 16 chars passes length check."""
        pwd = "Abcdefgh1234567!"  # exactly 16
        errors = validate_password(pwd)
        assert not any("16 characters" in e for e in errors)


@pytest.mark.unit
class TestBcryptHashing:
    """Tests for bcrypt hashing at cost 12 (Req 1.1)."""

    def test_bcrypt_hash_verifies(self) -> None:
        """Hashed password verifies correctly with bcrypt."""
        password = "MyStr0ng!Passphrase"
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        )
        assert bcrypt.checkpw(password.encode("utf-8"), hashed)

    def test_bcrypt_cost_12_prefix(self) -> None:
        """Hash uses cost factor 12 (prefix $2b$12$)."""
        hashed = bcrypt.hashpw(
            b"TestPassword123!",
            bcrypt.gensalt(rounds=12),
        )
        assert hashed.decode("utf-8").startswith("$2b$12$")


@pytest.mark.unit
class TestPasswordHardeningScript:
    """Tests for the main() script behavior (Req 1.2)."""

    def test_missing_env_var_exits(self) -> None:
        """Script exits with code 1 when NEW_ADMIN_PASSWORD is not set."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("harden_admin_password.load_dotenv"),
            pytest.raises(SystemExit) as exc_info,
        ):
            harden_admin_password.main()
        assert exc_info.value.code == 1

    def test_weak_password_exits(self) -> None:
        """Script exits with code 1 when password fails validation."""
        with (
            patch.dict("os.environ", {"NEW_ADMIN_PASSWORD": "weak"}, clear=False),
            patch("harden_admin_password.load_dotenv"),
            pytest.raises(SystemExit) as exc_info,
        ):
            harden_admin_password.main()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Dashboard Alert Target URL Tests (Req 3.1, 3.4)
# ---------------------------------------------------------------------------


def _make_dashboard_service(
    *,
    overdue: list[MagicMock] | None = None,
    lien_warning: list[MagicMock] | None = None,
    uncontacted: int = 0,
    jobs_by_status: dict[str, int] | None = None,
) -> DashboardService:
    """Create a DashboardService with mocked repositories."""
    return DashboardService(
        customer_repository=AsyncMock(),
        job_repository=AsyncMock(
            count_by_status=AsyncMock(return_value=jobs_by_status or {}),
        ),
        staff_repository=AsyncMock(),
        appointment_repository=AsyncMock(),
        lead_repository=AsyncMock(
            count_uncontacted=AsyncMock(return_value=uncontacted),
        ),
        invoice_repository=AsyncMock(
            find_overdue=AsyncMock(return_value=overdue or []),
            find_lien_warning_due=AsyncMock(return_value=lien_warning or []),
        ),
    )


@pytest.mark.unit
class TestDashboardAlertTargetUrl:
    """Tests for dashboard alert target_url generation."""

    @pytest.mark.asyncio
    async def test_single_overdue_invoice_links_to_detail(self) -> None:
        """Single overdue invoice alert links to /invoices/{id}."""
        inv_id = uuid.uuid4()
        svc = _make_dashboard_service(overdue=[MagicMock(id=inv_id)])

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "overdue_invoices"),
            None,
        )
        assert alert is not None
        assert alert.target_url == f"/invoices/{inv_id}"

    @pytest.mark.asyncio
    async def test_multiple_overdue_invoices_links_to_filtered_list(self) -> None:
        """Multiple overdue invoices alert links to filtered list with highlight."""
        inv1 = MagicMock(id=uuid.uuid4())
        inv2 = MagicMock(id=uuid.uuid4())
        svc = _make_dashboard_service(overdue=[inv1, inv2])

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "overdue_invoices"),
            None,
        )
        assert alert is not None
        assert "?status=overdue" in alert.target_url
        assert f"highlight={inv1.id}" in alert.target_url

    @pytest.mark.asyncio
    async def test_single_lien_warning_links_to_detail(self) -> None:
        """Single lien warning alert links to /invoices/{id}."""
        inv_id = uuid.uuid4()
        svc = _make_dashboard_service(lien_warning=[MagicMock(id=inv_id)])

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "lien_warnings"),
            None,
        )
        assert alert is not None
        assert alert.target_url == f"/invoices/{inv_id}"

    @pytest.mark.asyncio
    async def test_multiple_lien_warnings_links_to_filtered_list(self) -> None:
        """Multiple lien warnings link to filtered list with highlight."""
        inv1 = MagicMock(id=uuid.uuid4())
        inv2 = MagicMock(id=uuid.uuid4())
        svc = _make_dashboard_service(lien_warning=[inv1, inv2])

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "lien_warnings"),
            None,
        )
        assert alert is not None
        assert "?lien_warning=true" in alert.target_url
        assert f"highlight={inv1.id}" in alert.target_url

    @pytest.mark.asyncio
    async def test_jobs_to_schedule_links_to_filtered_list(self) -> None:
        """Jobs to schedule alert links to /jobs?status=to_be_scheduled."""
        svc = _make_dashboard_service(
            jobs_by_status={"to_be_scheduled": 3},
        )

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "jobs_to_schedule"),
            None,
        )
        assert alert is not None
        assert alert.target_url == "/jobs?status=to_be_scheduled"

    @pytest.mark.asyncio
    async def test_uncontacted_leads_links_to_filtered_list(self) -> None:
        """Uncontacted leads alert links to /leads?status=new."""
        svc = _make_dashboard_service(uncontacted=5)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "uncontacted_leads"),
            None,
        )
        assert alert is not None
        assert alert.target_url == "/leads?status=new"

    @pytest.mark.asyncio
    async def test_no_alerts_when_nothing_pending(self) -> None:
        """No alerts generated when all repositories return empty."""
        svc = _make_dashboard_service()

        result = await svc.get_alerts()
        assert result.alerts == []
        assert result.total == 0


# ---------------------------------------------------------------------------
# DashboardAlert Schema Tests (Req 3.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDashboardAlertSchema:
    """Tests for DashboardAlert schema validation."""

    def test_alert_with_highlight_url(self) -> None:
        """Alert schema accepts highlight query param in target_url."""
        alert = DashboardAlert(
            id="test",
            title="Test",
            description="Test alert",
            severity="warning",
            count=2,
            target_url="/invoices?status=overdue&highlight=abc-123",
            record_ids=["abc-123", "def-456"],
            created_at=datetime.now(tz=timezone.utc),
        )
        assert "highlight=abc-123" in alert.target_url

    def test_alert_with_detail_url(self) -> None:
        """Alert schema accepts direct detail page URL."""
        alert = DashboardAlert(
            id="test",
            title="Test",
            description="Test alert",
            severity="critical",
            count=1,
            target_url="/invoices/abc-123",
            record_ids=["abc-123"],
            created_at=datetime.now(tz=timezone.utc),
        )
        assert alert.target_url == "/invoices/abc-123"


# ---------------------------------------------------------------------------
# Dashboard Alert Tests — New Domains (Req 3.1, 3.2, 31.4)
# ---------------------------------------------------------------------------


def _make_customer_mock(first: str = "John", last: str = "Doe") -> MagicMock:
    """Create a mock customer with first/last name."""
    cust = MagicMock()
    cust.first_name = first
    cust.last_name = last
    return cust


def _make_session_with_results(
    sales_entries: list[MagicMock] | None = None,
    reschedule_requests: list[MagicMock] | None = None,
    renewal_proposals: list[MagicMock] | None = None,
) -> AsyncMock:
    """Create a mock async session that returns different results per query.

    The get_alerts method issues multiple select() calls against the session.
    We use side_effect to return different results for each call.
    """
    session = AsyncMock()

    # Build a list of mock execute results in the order the service calls them:
    # 1. Sales entries query
    # 2. Reschedule requests query
    # 3. Contract renewal proposals query
    results: list[MagicMock] = []

    for data in [
        sales_entries or [],
        reschedule_requests or [],
        renewal_proposals or [],
    ]:
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = data
        mock_result.scalars.return_value = mock_scalars
        results.append(mock_result)

    session.execute = AsyncMock(side_effect=results)
    return session


def _make_dashboard_service_with_session(
    *,
    session: AsyncMock,
    overdue: list[MagicMock] | None = None,
    lien_warning: list[MagicMock] | None = None,
    uncontacted: int = 0,
    jobs_by_status: dict[str, int] | None = None,
) -> DashboardService:
    """Create a DashboardService with mocked repositories and a session."""
    return DashboardService(
        customer_repository=AsyncMock(),
        job_repository=AsyncMock(
            count_by_status=AsyncMock(return_value=jobs_by_status or {}),
        ),
        staff_repository=AsyncMock(),
        appointment_repository=AsyncMock(),
        lead_repository=AsyncMock(
            count_uncontacted=AsyncMock(return_value=uncontacted),
        ),
        invoice_repository=AsyncMock(
            find_overdue=AsyncMock(return_value=overdue or []),
            find_lien_warning_due=AsyncMock(return_value=lien_warning or []),
        ),
        session=session,
    )


@pytest.mark.unit
class TestDashboardAlertSalesPipeline:
    """Tests for sales pipeline dashboard alerts (Req 3.1, 3.2)."""

    @pytest.mark.asyncio
    async def test_single_sales_entry_links_to_detail(self) -> None:
        """Single sales entry alert links to /sales/{id}."""
        entry_id = uuid.uuid4()
        entry = MagicMock(id=entry_id, customer=_make_customer_mock("Jane", "Smith"))
        session = _make_session_with_results(sales_entries=[entry])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "sales_needing_action"),
            None,
        )
        assert alert is not None
        assert alert.target_url == f"/sales/{entry_id}"
        assert alert.count == 1
        assert "Jane Smith" in alert.description

    @pytest.mark.asyncio
    async def test_multiple_sales_entries_link_to_filtered_list(self) -> None:
        """Multiple sales entries alert links to filtered list with highlight."""
        e1 = MagicMock(id=uuid.uuid4(), customer=_make_customer_mock())
        e2 = MagicMock(id=uuid.uuid4(), customer=_make_customer_mock())
        session = _make_session_with_results(sales_entries=[e1, e2])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "sales_needing_action"),
            None,
        )
        assert alert is not None
        assert "?status=schedule_estimate" in alert.target_url
        assert f"highlight={e1.id}" in alert.target_url
        assert alert.count == 2

    @pytest.mark.asyncio
    async def test_no_sales_alert_when_none_pending(self) -> None:
        """No sales alert when no entries at schedule_estimate status."""
        session = _make_session_with_results(sales_entries=[])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "sales_needing_action"),
            None,
        )
        assert alert is None


@pytest.mark.unit
class TestDashboardAlertRescheduleRequests:
    """Tests for reschedule request dashboard alerts (Req 3.1, 3.2)."""

    @pytest.mark.asyncio
    async def test_single_reschedule_request_alert(self) -> None:
        """Single reschedule request alert includes customer name."""
        req_id = uuid.uuid4()
        req = MagicMock(id=req_id, customer=_make_customer_mock("Bob", "Jones"))
        session = _make_session_with_results(reschedule_requests=[req])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "reschedule_requests"),
            None,
        )
        assert alert is not None
        assert f"highlight={req_id}" in alert.target_url
        assert "/schedule/reschedule-requests" in alert.target_url
        assert alert.count == 1
        assert "Bob Jones" in alert.description

    @pytest.mark.asyncio
    async def test_multiple_reschedule_requests_alert(self) -> None:
        """Multiple reschedule requests alert links to queue with highlight."""
        r1 = MagicMock(id=uuid.uuid4(), customer=_make_customer_mock())
        r2 = MagicMock(id=uuid.uuid4(), customer=_make_customer_mock())
        session = _make_session_with_results(reschedule_requests=[r1, r2])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "reschedule_requests"),
            None,
        )
        assert alert is not None
        assert f"highlight={r1.id}" in alert.target_url
        assert alert.count == 2
        assert "2 reschedule requests" in alert.description

    @pytest.mark.asyncio
    async def test_no_reschedule_alert_when_none_open(self) -> None:
        """No reschedule alert when no open requests."""
        session = _make_session_with_results(reschedule_requests=[])
        svc = _make_dashboard_service_with_session(session=session)

        result = await svc.get_alerts()
        alert = next(
            (a for a in result.alerts if a.id == "reschedule_requests"),
            None,
        )
        assert alert is None
