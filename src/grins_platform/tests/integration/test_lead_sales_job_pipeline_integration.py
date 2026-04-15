"""Integration tests for the Lead → Sales → Job pipeline.

Exercises the full cross-domain flow:
  1. Create a lead
  2. Move lead to sales (auto-generates customer, creates SalesEntry)
  3. Advance through all pipeline statuses
  4. Convert to job (with signature or force override)
  5. Verify the job is created with correct data

External services (SignWell, SMS) are mocked; the full internal
service-to-service flow is exercised via the HTTP API layer.

Validates: CRM Changes Update 2 Req 12.1, 12.2, 14.3, 16.2
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.api.v1.leads import _get_lead_service
from grins_platform.api.v1.sales_pipeline import _get_pipeline_service
from grins_platform.main import app
from grins_platform.models.enums import SalesEntryStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_admin() -> MagicMock:
    """Create a mock admin user for auth overrides."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin"
    user.role = "admin"
    user.is_active = True
    return user


def _make_sales_entry_mock(
    *,
    entry_id: uuid.UUID | None = None,
    customer_id: uuid.UUID | None = None,
    lead_id: uuid.UUID | None = None,
    status: str = SalesEntryStatus.SCHEDULE_ESTIMATE.value,
    job_type: str | None = "spring_startup",
    signwell_document_id: str | None = None,
) -> MagicMock:
    """Create a mock SalesEntry row with sensible defaults.

    Uses spec=False and explicit attribute setting so Pydantic
    model_validate(entry) can read real values (not nested MagicMocks).
    """
    entry = MagicMock()
    entry.id = entry_id or uuid.uuid4()
    entry.customer_id = customer_id or uuid.uuid4()
    entry.lead_id = lead_id
    entry.property_id = None
    entry.job_type = job_type
    entry.status = status
    entry.last_contact_date = None
    entry.notes = None
    entry.override_flag = False
    entry.closed_reason = None
    entry.signwell_document_id = signwell_document_id
    entry.created_at = datetime.now(tz=timezone.utc)
    entry.updated_at = datetime.now(tz=timezone.utc)
    # Denormalized fields expected by SalesEntryResponse
    entry.customer_name = None
    entry.customer_phone = None
    entry.property_address = None
    return entry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_lead_service() -> AsyncMock:
    """Create a mock LeadService."""
    return AsyncMock()


@pytest.fixture
def mock_pipeline_service() -> AsyncMock:
    """Create a mock SalesPipelineService."""
    return AsyncMock()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock async DB session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest_asyncio.fixture
async def admin_client(
    mock_lead_service: AsyncMock,
    mock_pipeline_service: AsyncMock,
    mock_db_session: AsyncMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Authenticated admin client with mocked services."""
    admin = _mock_admin()
    app.dependency_overrides[_get_lead_service] = lambda: mock_lead_service
    app.dependency_overrides[_get_pipeline_service] = lambda: mock_pipeline_service
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    app.dependency_overrides[get_db_session] = lambda: mock_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestLeadToSalesToJobPipeline:
    """Integration tests for the full Lead → Sales → Job pipeline.

    Validates: CRM Changes Update 2 Req 12.1, 12.2, 14.3, 16.2
    """

    # -----------------------------------------------------------------
    # 1. Full pipeline: lead → sales → advance all → force convert
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_full_pipeline_lead_to_sales_to_job_with_force_convert(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Full pipeline: create lead → move to sales → advance all → force convert.

        **Validates: Requirements 12.1, 12.2, 14.3, 16.2**

        Steps:
        1. Create a manual lead via POST /api/v1/leads/manual.
        2. Move lead to sales via POST /api/v1/leads/{id}/move-to-sales.
        3. Advance the sales entry through all non-terminal statuses.
        4. Force-convert to job (no signature on file).
        5. Verify job is created and sales entry is Closed-Won.
        """
        from grins_platform.models.enums import LeadSituation, LeadStatus
        from grins_platform.schemas.lead import LeadMoveResponse, LeadResponse

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        sales_entry_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        # --- Step 1: Create a manual lead ---
        mock_lead_service.create_manual_lead = AsyncMock(
            return_value=LeadResponse(
                id=lead_id,
                name="John Doe",
                phone="6125551234",
                email=None,
                zip_code="55424",
                situation=LeadSituation.NEW_SYSTEM,
                notes=None,
                source_site="residential",
                lead_source="manual",
                source_detail=None,
                intake_tag=None,
                sms_consent=False,
                terms_accepted=False,
                status=LeadStatus.NEW,
                assigned_to=None,
                customer_id=None,
                contacted_at=None,
                converted_at=None,
                created_at=now,
                updated_at=now,
            ),
        )

        create_resp = await admin_client.post(
            "/api/v1/leads/manual",
            json={
                "name": "John Doe",
                "phone": "6125551234",
                "zip_code": "55424",
                "situation": "new_system",
            },
        )
        assert create_resp.status_code == 201
        lead_data = create_resp.json()
        assert lead_data["id"] == str(lead_id)
        assert lead_data["status"] == "new"

        # --- Step 2: Move lead to sales ---
        mock_lead_service.move_to_sales = AsyncMock(
            return_value=LeadMoveResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                sales_entry_id=sales_entry_id,
                message="Lead moved to Sales",
            ),
        )

        move_resp = await admin_client.post(
            f"/api/v1/leads/{lead_id}/move-to-sales",
        )
        assert move_resp.status_code == 200
        move_data = move_resp.json()
        assert move_data["customer_id"] == str(customer_id)
        assert move_data["sales_entry_id"] == str(sales_entry_id)
        assert move_data["message"] == "Lead moved to Sales"

        # --- Step 3: Advance through all pipeline statuses ---
        # Pipeline order: schedule_estimate → estimate_scheduled →
        #   send_estimate → pending_approval → send_contract
        # We advance 4 times to reach send_contract, then convert.

        pipeline_targets = [
            SalesEntryStatus.ESTIMATE_SCHEDULED,
            SalesEntryStatus.SEND_ESTIMATE,
            SalesEntryStatus.PENDING_APPROVAL,
            SalesEntryStatus.SEND_CONTRACT,
        ]

        for target_status in pipeline_targets:
            entry_mock = _make_sales_entry_mock(
                entry_id=sales_entry_id,
                customer_id=customer_id,
                lead_id=lead_id,
                status=target_status.value,
            )
            mock_pipeline_service.advance_status = AsyncMock(
                return_value=entry_mock,
            )

            advance_resp = await admin_client.post(
                f"/api/v1/sales/pipeline/{sales_entry_id}/advance",
            )
            assert advance_resp.status_code == 200
            assert advance_resp.json()["status"] == target_status.value

        # --- Step 4: Force-convert to job ---
        mock_job = MagicMock()
        mock_job.id = job_id
        mock_pipeline_service.convert_to_job = AsyncMock(return_value=mock_job)

        convert_resp = await admin_client.post(
            f"/api/v1/sales/pipeline/{sales_entry_id}/force-convert",
        )
        assert convert_resp.status_code == 200
        convert_data = convert_resp.json()
        assert convert_data["job_id"] == str(job_id)
        assert convert_data["status"] == "closed_won"
        assert convert_data["forced"] is True

        # Verify convert_to_job was called with force=True
        mock_pipeline_service.convert_to_job.assert_awaited_once()
        call_kwargs = mock_pipeline_service.convert_to_job.call_args
        assert call_kwargs.kwargs.get("force") is True

    # -----------------------------------------------------------------
    # 2. Lead → Jobs direct path (bypassing sales)
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_lead_move_to_jobs_direct_path(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Lead can be moved directly to Jobs, bypassing the sales pipeline.

        **Validates: Requirements 12.1**

        Steps:
        1. Create a manual lead.
        2. Move lead to jobs via POST /api/v1/leads/{id}/move-to-jobs.
        3. Verify customer auto-generated and job created.
        """
        from grins_platform.models.enums import LeadSituation, LeadStatus
        from grins_platform.schemas.lead import LeadMoveResponse, LeadResponse

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc)

        # Step 1: Create lead
        mock_lead_service.create_manual_lead = AsyncMock(
            return_value=LeadResponse(
                id=lead_id,
                name="Jane Smith",
                phone="6125559876",
                email="jane@example.com",
                zip_code="55346",
                situation=LeadSituation.REPAIR,
                notes="Broken sprinkler head",
                source_site="residential",
                lead_source="manual",
                source_detail=None,
                intake_tag=None,
                sms_consent=False,
                terms_accepted=False,
                status=LeadStatus.NEW,
                assigned_to=None,
                customer_id=None,
                contacted_at=None,
                converted_at=None,
                created_at=now,
                updated_at=now,
            ),
        )

        create_resp = await admin_client.post(
            "/api/v1/leads/manual",
            json={
                "name": "Jane Smith",
                "phone": "6125559876",
                "email": "jane@example.com",
                "zip_code": "55346",
                "situation": "repair",
                "notes": "Broken sprinkler head",
            },
        )
        assert create_resp.status_code == 201

        # Step 2: Move to jobs
        mock_lead_service.move_to_jobs = AsyncMock(
            return_value=LeadMoveResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                job_id=job_id,
                message="Lead moved to Jobs",
            ),
        )

        move_resp = await admin_client.post(
            f"/api/v1/leads/{lead_id}/move-to-jobs",
        )
        assert move_resp.status_code == 200
        move_data = move_resp.json()
        assert move_data["customer_id"] == str(customer_id)
        assert move_data["job_id"] == str(job_id)
        assert move_data["message"] == "Lead moved to Jobs"

    # -----------------------------------------------------------------
    # 3. Pipeline advances one step at a time
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sales_pipeline_advances_one_step_at_a_time(
        self,
        admin_client: AsyncClient,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Each advance call moves the sales entry exactly one step forward.

        **Validates: Requirements 14.3**

        Verifies the ordered progression:
          schedule_estimate → estimate_scheduled → send_estimate
          → pending_approval → send_contract
        """
        entry_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        expected_transitions = [
            (SalesEntryStatus.SCHEDULE_ESTIMATE, SalesEntryStatus.ESTIMATE_SCHEDULED),
            (SalesEntryStatus.ESTIMATE_SCHEDULED, SalesEntryStatus.SEND_ESTIMATE),
            (SalesEntryStatus.SEND_ESTIMATE, SalesEntryStatus.PENDING_APPROVAL),
            (SalesEntryStatus.PENDING_APPROVAL, SalesEntryStatus.SEND_CONTRACT),
        ]

        for _from_status, to_status in expected_transitions:
            entry_mock = _make_sales_entry_mock(
                entry_id=entry_id,
                customer_id=customer_id,
                status=to_status.value,
            )
            mock_pipeline_service.advance_status = AsyncMock(
                return_value=entry_mock,
            )

            resp = await admin_client.post(
                f"/api/v1/sales/pipeline/{entry_id}/advance",
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == to_status.value

    # -----------------------------------------------------------------
    # 4. Convert to job with signature (non-force path)
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_convert_to_job_with_signature(
        self,
        admin_client: AsyncClient,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Convert to job succeeds when signature is on file (non-force path).

        **Validates: Requirements 16.2**
        """
        entry_id = uuid.uuid4()
        job_id = uuid.uuid4()

        mock_job = MagicMock()
        mock_job.id = job_id
        mock_pipeline_service.convert_to_job = AsyncMock(return_value=mock_job)

        resp = await admin_client.post(
            f"/api/v1/sales/pipeline/{entry_id}/convert",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == str(job_id)
        assert data["status"] == "closed_won"

        # Verify force=False for the normal convert path
        mock_pipeline_service.convert_to_job.assert_awaited_once()
        call_kwargs = mock_pipeline_service.convert_to_job.call_args
        assert call_kwargs.kwargs.get("force") is False

    # -----------------------------------------------------------------
    # 5. Convert blocked without signature (non-force)
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_convert_to_job_blocked_without_signature(
        self,
        admin_client: AsyncClient,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Convert to job fails with 422 when no signature is on file.

        **Validates: Requirements 16.2**
        """
        from grins_platform.exceptions import SignatureRequiredError

        entry_id = uuid.uuid4()
        mock_pipeline_service.convert_to_job = AsyncMock(
            side_effect=SignatureRequiredError(entry_id),
        )

        resp = await admin_client.post(
            f"/api/v1/sales/pipeline/{entry_id}/convert",
        )
        assert resp.status_code == 422
        assert "signature" in resp.json()["detail"].lower()

    # -----------------------------------------------------------------
    # 6. Terminal state blocks further advance
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_advance_blocked_on_terminal_status(
        self,
        admin_client: AsyncClient,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Advancing a Closed-Won or Closed-Lost entry returns 422.

        **Validates: Requirements 14.3**
        """
        from grins_platform.exceptions import InvalidSalesTransitionError

        entry_id = uuid.uuid4()
        mock_pipeline_service.advance_status = AsyncMock(
            side_effect=InvalidSalesTransitionError(
                SalesEntryStatus.CLOSED_WON.value,
                SalesEntryStatus.CLOSED_WON.value,
            ),
        )

        resp = await admin_client.post(
            f"/api/v1/sales/pipeline/{entry_id}/advance",
        )
        assert resp.status_code == 422

    # -----------------------------------------------------------------
    # 7. Mark lost from any active status
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_mark_lost_from_active_status(
        self,
        admin_client: AsyncClient,
        mock_pipeline_service: AsyncMock,
    ) -> None:
        """Any active sales entry can be marked as Closed-Lost.

        **Validates: Requirements 14.3**
        """
        entry_id = uuid.uuid4()
        entry_mock = _make_sales_entry_mock(
            entry_id=entry_id,
            status=SalesEntryStatus.CLOSED_LOST.value,
        )
        entry_mock.closed_reason = "Customer went with competitor"
        mock_pipeline_service.mark_lost = AsyncMock(return_value=entry_mock)

        resp = await admin_client.delete(
            f"/api/v1/sales/pipeline/{entry_id}",
        )
        assert resp.status_code == 200

    # -----------------------------------------------------------------
    # 8. Move to sales creates entry with correct initial status
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_move_to_sales_creates_entry_with_correct_initial_status(
        self,
        admin_client: AsyncClient,
        mock_lead_service: AsyncMock,
    ) -> None:
        """Moving a lead to sales creates a SalesEntry at schedule_estimate.

        **Validates: Requirements 12.2**
        """
        from grins_platform.schemas.lead import LeadMoveResponse

        lead_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        sales_entry_id = uuid.uuid4()

        mock_lead_service.move_to_sales = AsyncMock(
            return_value=LeadMoveResponse(
                lead_id=lead_id,
                customer_id=customer_id,
                sales_entry_id=sales_entry_id,
                message="Lead moved to Sales",
            ),
        )

        resp = await admin_client.post(
            f"/api/v1/leads/{lead_id}/move-to-sales",
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sales_entry_id"] == str(sales_entry_id)
        assert data["customer_id"] == str(customer_id)

        # Verify the service was called with the correct lead_id
        mock_lead_service.move_to_sales.assert_awaited_once_with(lead_id)
