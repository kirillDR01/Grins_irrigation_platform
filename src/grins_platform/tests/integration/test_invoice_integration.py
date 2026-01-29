"""
Invoice integration tests.

Tests for end-to-end invoice flows including creation from job,
payment recording, status transitions, and lien tracking workflow.

Validates: Requirements 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_user,
    require_admin,
    require_manager_or_admin,
)
from grins_platform.api.v1.invoices import get_invoice_service
from grins_platform.exceptions import (
    InvalidInvoiceOperationError,
)
from grins_platform.main import app
from grins_platform.models.enums import (
    InvoiceStatus,
    PaymentMethod,
    StaffRole,
    UserRole,
)
from grins_platform.schemas.invoice import (
    InvoiceResponse,
    LienDeadlineInvoice,
    LienDeadlineResponse,
)
from grins_platform.services.invoice_service import InvoiceService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_manager_user() -> MagicMock:
    """Create a mock manager user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Manager User"
    user.username = "manager"
    user.email = "manager@grins.com"
    user.role = UserRole.MANAGER.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_admin_user() -> MagicMock:
    """Create a mock admin user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Admin User"
    user.username = "admin"
    user.email = "admin@grins.com"
    user.role = StaffRole.ADMIN.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_tech_user() -> MagicMock:
    """Create a mock tech user for authentication."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.name = "Tech User"
    user.username = "tech"
    user.email = "tech@grins.com"
    user.role = StaffRole.TECH.value
    user.is_active = True
    user.is_login_enabled = True
    return user


@pytest.fixture
def sample_invoice_response() -> InvoiceResponse:
    """Create a sample invoice response."""
    return InvoiceResponse(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        invoice_number="INV-2025-000001",
        amount=Decimal("150.00"),
        late_fee_amount=Decimal("0.00"),
        total_amount=Decimal("150.00"),
        invoice_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.DRAFT.value,
        payment_method=None,
        payment_reference=None,
        paid_at=None,
        paid_amount=None,
        reminder_count=0,
        last_reminder_sent=None,
        lien_eligible=False,
        lien_warning_sent=None,
        lien_filed_date=None,
        line_items=None,
        notes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_invoice_service() -> MagicMock:
    """Create a mock InvoiceService."""
    service = MagicMock(spec=InvoiceService)
    service.create_invoice = AsyncMock()
    service.get_invoice = AsyncMock()
    service.get_invoice_detail = AsyncMock()
    service.update_invoice = AsyncMock()
    service.cancel_invoice = AsyncMock()
    service.list_invoices = AsyncMock()
    service.send_invoice = AsyncMock()
    service.mark_viewed = AsyncMock()
    service.mark_overdue = AsyncMock()
    service.record_payment = AsyncMock()
    service.send_reminder = AsyncMock()
    service.send_lien_warning = AsyncMock()
    service.mark_lien_filed = AsyncMock()
    service.get_lien_deadlines = AsyncMock()
    service.generate_from_job = AsyncMock()
    return service


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# Test Invoice Creation from Job
# =============================================================================


@pytest.mark.integration
class TestInvoiceCreationFromJobIntegration:
    """Integration tests for invoice creation from job."""

    @pytest.mark.asyncio
    async def test_generate_invoice_from_job_success(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test generating invoice from job returns correct response.

        Validates: Requirements 10.1-10.7
        """
        job_id = uuid.uuid4()
        mock_invoice_service.generate_from_job.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert "invoice_number" in data
            assert data["status"] == InvoiceStatus.DRAFT.value
            mock_invoice_service.generate_from_job.assert_called_once_with(job_id)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_invoice_job_not_found(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test generating invoice from non-existent job returns 400.

        Validates: Requirement 10.2
        """
        job_id = uuid.uuid4()
        err = InvalidInvoiceOperationError("Job not found")
        mock_invoice_service.generate_from_job.side_effect = err

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_invoice_payment_collected_on_site(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test generating invoice when payment collected on site returns 400.

        Validates: Requirement 10.6
        """
        job_id = uuid.uuid4()
        err_msg = "Cannot generate invoice - payment was collected on site"
        mock_invoice_service.generate_from_job.side_effect = (
            InvalidInvoiceOperationError(err_msg)
        )

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/generate-from-job/{job_id}",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 400
            assert "payment was collected on site" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Payment Recording
# =============================================================================


@pytest.mark.integration
class TestPaymentRecordingIntegration:
    """Integration tests for payment recording."""

    @pytest.mark.asyncio
    async def test_record_full_payment_marks_paid(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test recording full payment marks invoice as paid.

        Validates: Requirements 9.5-9.6
        """
        invoice_id = uuid.uuid4()
        paid_response = InvoiceResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-000001",
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("150.00"),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.PAID.value,
            payment_method=PaymentMethod.VENMO.value,
            payment_reference="venmo-123",
            paid_at=datetime.now(timezone.utc),
            paid_amount=Decimal("150.00"),
            reminder_count=0,
            last_reminder_sent=None,
            lien_eligible=False,
            lien_warning_sent=None,
            lien_filed_date=None,
            line_items=None,
            notes=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_invoice_service.record_payment.return_value = paid_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/payment",
                json={
                    "amount": "150.00",
                    "payment_method": "venmo",
                    "payment_reference": "venmo-123",
                },
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == InvoiceStatus.PAID.value
            assert data["paid_amount"] == "150.00"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_record_partial_payment_marks_partial(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test recording partial payment marks invoice as partial.

        Validates: Requirements 9.5-9.6
        """
        invoice_id = uuid.uuid4()
        partial_response = InvoiceResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-000001",
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("150.00"),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.PARTIAL.value,
            payment_method=PaymentMethod.CASH.value,
            payment_reference=None,
            paid_at=datetime.now(timezone.utc),
            paid_amount=Decimal("75.00"),
            reminder_count=0,
            last_reminder_sent=None,
            lien_eligible=False,
            lien_warning_sent=None,
            lien_filed_date=None,
            line_items=None,
            notes=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_invoice_service.record_payment.return_value = partial_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/payment",
                json={"amount": "75.00", "payment_method": "cash"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == InvoiceStatus.PARTIAL.value
            assert data["paid_amount"] == "75.00"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Status Transitions
# =============================================================================


@pytest.mark.integration
class TestStatusTransitionsIntegration:
    """Integration tests for invoice status transitions."""

    @pytest.mark.asyncio
    async def test_send_invoice_draft_to_sent(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test sending invoice transitions from draft to sent.

        Validates: Requirement 8.2
        """
        invoice_id = uuid.uuid4()
        sent_response = InvoiceResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-000001",
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("150.00"),
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=InvoiceStatus.SENT.value,
            payment_method=None,
            payment_reference=None,
            paid_at=None,
            paid_amount=None,
            reminder_count=0,
            last_reminder_sent=None,
            lien_eligible=False,
            lien_warning_sent=None,
            lien_filed_date=None,
            line_items=None,
            notes=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_invoice_service.send_invoice.return_value = sent_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/send",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == InvoiceStatus.SENT.value
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_send_invoice_not_draft_fails(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test sending non-draft invoice fails.

        Validates: Requirement 8.2
        """
        invoice_id = uuid.uuid4()
        mock_invoice_service.send_invoice.side_effect = InvalidInvoiceOperationError(
            "Can only send invoices in draft status",
        )

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/send",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Lien Tracking Workflow
# =============================================================================


@pytest.mark.integration
class TestLienTrackingWorkflowIntegration:
    """Integration tests for lien tracking workflow."""

    @pytest.mark.asyncio
    async def test_send_lien_warning_admin_only(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test sending lien warning requires admin role.

        Validates: Requirements 11.6, 17.8
        """
        invoice_id = uuid.uuid4()
        warning_response = InvoiceResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-000001",
            amount=Decimal("5000.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("5000.00"),
            invoice_date=date.today() - timedelta(days=50),
            due_date=date.today() - timedelta(days=20),
            status=InvoiceStatus.LIEN_WARNING.value,
            payment_method=None,
            payment_reference=None,
            paid_at=None,
            paid_amount=None,
            reminder_count=2,
            last_reminder_sent=None,
            lien_eligible=True,
            lien_warning_sent=datetime.now(timezone.utc),
            lien_filed_date=None,
            line_items=None,
            notes=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_invoice_service.send_lien_warning.return_value = warning_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = lambda: sample_admin_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-warning",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == InvoiceStatus.LIEN_WARNING.value
            assert data["lien_warning_sent"] is not None
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_lien_filed_admin_only(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_admin_user: MagicMock,
    ) -> None:
        """Test marking lien filed requires admin role.

        Validates: Requirements 11.7, 17.8
        """
        invoice_id = uuid.uuid4()
        filing_date = date.today()
        filed_response = InvoiceResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-000001",
            amount=Decimal("5000.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("5000.00"),
            invoice_date=date.today() - timedelta(days=130),
            due_date=date.today() - timedelta(days=100),
            status=InvoiceStatus.LIEN_FILED.value,
            payment_method=None,
            payment_reference=None,
            paid_at=None,
            paid_amount=None,
            reminder_count=3,
            last_reminder_sent=None,
            lien_eligible=True,
            lien_warning_sent=datetime.now(timezone.utc) - timedelta(days=60),
            lien_filed_date=filing_date,
            line_items=None,
            notes=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_invoice_service.mark_lien_filed.return_value = filed_response

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_admin] = lambda: sample_admin_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{invoice_id}/lien-filed",
                json={"filing_date": str(filing_date)},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == InvoiceStatus.LIEN_FILED.value
            assert data["lien_filed_date"] == str(filing_date)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_lien_deadlines(
        self,
        async_client: AsyncClient,
        mock_invoice_service: MagicMock,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test getting lien deadlines returns approaching deadlines.

        Validates: Requirements 11.4-11.5
        """
        mock_invoice_service.get_lien_deadlines.return_value = LienDeadlineResponse(
            approaching_45_day=[
                LienDeadlineInvoice(
                    id=uuid.uuid4(),
                    invoice_number="INV-2025-000001",
                    customer_id=uuid.uuid4(),
                    customer_name=None,
                    amount=Decimal("5000.00"),
                    total_amount=Decimal("5000.00"),
                    due_date=date.today() - timedelta(days=40),
                    days_overdue=40,
                ),
            ],
            approaching_120_day=[
                LienDeadlineInvoice(
                    id=uuid.uuid4(),
                    invoice_number="INV-2025-000002",
                    customer_id=uuid.uuid4(),
                    customer_name=None,
                    amount=Decimal("8000.00"),
                    total_amount=Decimal("8000.00"),
                    due_date=date.today() - timedelta(days=115),
                    days_overdue=115,
                ),
            ],
        )

        app.dependency_overrides[get_invoice_service] = lambda: mock_invoice_service
        app.dependency_overrides[require_manager_or_admin] = lambda: sample_manager_user

        try:
            response = await async_client.get(
                "/api/v1/invoices/lien-deadlines",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["approaching_45_day"]) == 1
            assert len(data["approaching_120_day"]) == 1
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Test Authorization
# =============================================================================


@pytest.mark.integration
class TestInvoiceAuthorizationIntegration:
    """Integration tests for invoice authorization."""

    @pytest.mark.asyncio
    async def test_tech_cannot_create_invoice(
        self,
        async_client: AsyncClient,
        sample_tech_user: MagicMock,
    ) -> None:
        """Test tech user cannot create invoices.

        Validates: Requirement 17.7
        """
        app.dependency_overrides[get_current_user] = lambda: sample_tech_user

        try:
            response = await async_client.post(
                "/api/v1/invoices",
                json={
                    "job_id": str(uuid.uuid4()),
                    "amount": "150.00",
                    "late_fee_amount": "0.00",
                    "due_date": str(date.today() + timedelta(days=30)),
                },
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_manager_cannot_send_lien_warning(
        self,
        async_client: AsyncClient,
        sample_manager_user: MagicMock,
    ) -> None:
        """Test manager cannot send lien warning (admin only).

        Validates: Requirement 17.8
        """
        app.dependency_overrides[get_current_user] = lambda: sample_manager_user

        try:
            response = await async_client.post(
                f"/api/v1/invoices/{uuid.uuid4()}/lien-warning",
                headers={"Authorization": "Bearer test_token"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_invoices(
        self,
        async_client: AsyncClient,
    ) -> None:
        """Test unauthenticated user cannot list invoices."""
        response = await async_client.get("/api/v1/invoices")
        assert response.status_code == 401
