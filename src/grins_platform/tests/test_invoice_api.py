"""
Invoice API endpoint tests.

Tests for invoice CRUD, status transitions, payments, and lien operations.

Validates: Requirements 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7,
           11.1-11.8, 12.1-12.5, 13.1-13.7, 17.7-17.8
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from grins_platform.api.v1.auth_dependencies import (
    require_admin,
    require_manager_or_admin,
)
from grins_platform.api.v1.invoices import get_invoice_service
from grins_platform.exceptions import (
    InvalidInvoiceOperationError,
    InvoiceNotFoundError,
)
from grins_platform.main import app
from grins_platform.models.enums import InvoiceStatus, PaymentMethod, UserRole
from grins_platform.schemas.invoice import (
    InvoiceDetailResponse,
    InvoiceResponse,
    LienDeadlineResponse,
    PaginatedInvoiceResponse,
)

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_manager_user() -> MagicMock:
    """Create a mock manager user for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "manager"
    user.name = "Manager User"
    user.email = "manager@example.com"
    user.role = UserRole.MANAGER.value
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user() -> MagicMock:
    """Create a mock admin user for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.name = "Admin User"
    user.email = "admin@example.com"
    user.role = UserRole.ADMIN.value
    user.is_active = True
    return user


@pytest.fixture
def mock_invoice_service() -> MagicMock:
    """Create a mock InvoiceService."""
    service = MagicMock()
    service.create_invoice = AsyncMock()
    service.get_invoice_detail = AsyncMock()
    service.update_invoice = AsyncMock()
    service.cancel_invoice = AsyncMock()
    service.list_invoices = AsyncMock()
    service.send_invoice = AsyncMock()
    service.record_payment = AsyncMock()
    service.send_reminder = AsyncMock()
    service.send_lien_warning = AsyncMock()
    service.mark_lien_filed = AsyncMock()
    service.get_lien_deadlines = AsyncMock()
    service.generate_from_job = AsyncMock()
    return service


@pytest.fixture
def override_invoice_service(
    mock_invoice_service: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for invoice service."""

    async def _override() -> MagicMock:
        return mock_invoice_service

    return _override  # type: ignore[return-value]


@pytest.fixture
def override_manager_or_admin(
    mock_manager_user: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for require_manager_or_admin."""

    async def _override() -> MagicMock:
        return mock_manager_user

    return _override  # type: ignore[return-value]


@pytest.fixture
def override_admin_user(
    mock_admin_user: MagicMock,
) -> Callable[[], MagicMock]:
    """Create an async override function for require_admin."""

    async def _override() -> MagicMock:
        return mock_admin_user

    return _override  # type: ignore[return-value]


@pytest.fixture
def sample_invoice_response() -> InvoiceResponse:
    """Create a sample invoice response."""
    return InvoiceResponse(
        id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        invoice_number="INV-2025-0001",
        amount=Decimal("150.00"),
        late_fee_amount=Decimal("0.00"),
        total_amount=Decimal("150.00"),
        invoice_date=date.today(),
        due_date=date.today(),
        status=InvoiceStatus.DRAFT,
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


# =============================================================================
# Create Invoice Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestCreateInvoiceEndpoint:
    """Tests for POST /api/v1/invoices endpoint."""

    @pytest.mark.asyncio
    async def test_create_invoice_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful invoice creation."""
        mock_invoice_service.create_invoice.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/invoices",
                    json={
                        "job_id": str(uuid.uuid4()),
                        "amount": "150.00",
                        "due_date": str(date.today()),
                    },
                )

            assert response.status_code == 201
            data = response.json()
            assert data["invoice_number"] == "INV-2025-0001"
            assert data["status"] == "draft"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_invoice_unauthorized(self) -> None:
        """Test invoice creation denied without authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/invoices",
                json={
                    "job_id": str(uuid.uuid4()),
                    "amount": "150.00",
                    "due_date": str(date.today()),
                },
            )

        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_invoice_invalid_job(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test invoice creation with invalid job returns 400."""
        mock_invoice_service.create_invoice.side_effect = InvalidInvoiceOperationError(
            "Job not found",
        )

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    "/api/v1/invoices",
                    json={
                        "job_id": str(uuid.uuid4()),
                        "amount": "150.00",
                        "due_date": str(date.today()),
                    },
                )

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Get Invoice Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestGetInvoiceEndpoint:
    """Tests for GET /api/v1/invoices/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_invoice_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test successful invoice retrieval."""
        invoice_id = uuid.uuid4()
        mock_response = InvoiceDetailResponse(
            id=invoice_id,
            job_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            invoice_number="INV-2025-0001",
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("0.00"),
            total_amount=Decimal("150.00"),
            invoice_date=date.today(),
            due_date=date.today(),
            status=InvoiceStatus.DRAFT,
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
            job_description="Spring Startup",
            customer_name="John Doe",
            customer_phone="6125551234",
            customer_email="john@example.com",
        )
        mock_invoice_service.get_invoice_detail.return_value = mock_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/invoices/{invoice_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["customer_name"] == "John Doe"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test invoice retrieval returns 404 when not found."""
        invoice_id = uuid.uuid4()
        mock_invoice_service.get_invoice_detail.side_effect = InvoiceNotFoundError(
            invoice_id,
        )

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(f"/api/v1/invoices/{invoice_id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Update Invoice Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestUpdateInvoiceEndpoint:
    """Tests for PUT /api/v1/invoices/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_invoice_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful invoice update."""
        mock_invoice_service.update_invoice.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.put(
                    f"/api/v1/invoices/{sample_invoice_response.id}",
                    json={"amount": "200.00"},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_invoice_not_draft(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test update fails for non-draft invoice."""
        invoice_id = uuid.uuid4()
        mock_invoice_service.update_invoice.side_effect = InvalidInvoiceOperationError(
            "Can only update draft invoices",
        )

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.put(
                    f"/api/v1/invoices/{invoice_id}",
                    json={"amount": "200.00"},
                )

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Cancel Invoice Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestCancelInvoiceEndpoint:
    """Tests for DELETE /api/v1/invoices/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_invoice_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test successful invoice cancellation."""
        invoice_id = uuid.uuid4()
        mock_invoice_service.cancel_invoice.return_value = None

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.delete(f"/api/v1/invoices/{invoice_id}")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_invoice_not_found(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test cancel returns 404 when invoice not found."""
        invoice_id = uuid.uuid4()
        mock_invoice_service.cancel_invoice.side_effect = InvoiceNotFoundError(
            invoice_id,
        )

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.delete(f"/api/v1/invoices/{invoice_id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# List Invoices Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestListInvoicesEndpoint:
    """Tests for GET /api/v1/invoices endpoint."""

    @pytest.mark.asyncio
    async def test_list_invoices_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful invoice listing."""
        mock_response = PaginatedInvoiceResponse(
            items=[sample_invoice_response],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )
        mock_invoice_service.list_invoices.return_value = mock_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/invoices")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_invoices_with_filters(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test invoice listing with filters."""
        mock_response = PaginatedInvoiceResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        mock_invoice_service.list_invoices.return_value = mock_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/invoices",
                    params={"status": "overdue", "page": 1, "page_size": 10},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Send Invoice Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestSendInvoiceEndpoint:
    """Tests for POST /api/v1/invoices/{id}/send endpoint."""

    @pytest.mark.asyncio
    async def test_send_invoice_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful invoice send."""
        sent_response = sample_invoice_response.model_copy(
            update={"status": InvoiceStatus.SENT},
        )
        mock_invoice_service.send_invoice.return_value = sent_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/{sample_invoice_response.id}/send",
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "sent"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Record Payment Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestRecordPaymentEndpoint:
    """Tests for POST /api/v1/invoices/{id}/payment endpoint."""

    @pytest.mark.asyncio
    async def test_record_payment_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful payment recording."""
        paid_response = sample_invoice_response.model_copy(
            update={
                "status": InvoiceStatus.PAID,
                "paid_amount": Decimal("150.00"),
                "payment_method": PaymentMethod.VENMO,
            },
        )
        mock_invoice_service.record_payment.return_value = paid_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/{sample_invoice_response.id}/payment",
                    json={
                        "amount": "150.00",
                        "payment_method": "venmo",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "paid"
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Lien Endpoints Tests
# =============================================================================


@pytest.mark.unit
class TestLienEndpoints:
    """Tests for lien-related endpoints."""

    @pytest.mark.asyncio
    async def test_send_lien_warning_admin_only(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_admin_user: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test lien warning requires admin role."""
        mock_invoice_service.send_lien_warning.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_admin] = override_admin_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/{sample_invoice_response.id}/lien-warning",
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_mark_lien_filed_admin_only(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_admin_user: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test mark lien filed requires admin role."""
        mock_invoice_service.mark_lien_filed.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_admin] = override_admin_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/{sample_invoice_response.id}/lien-filed",
                    json={"filing_date": str(date.today())},
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_lien_deadlines(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test get lien deadlines endpoint."""
        mock_response = LienDeadlineResponse(
            approaching_45_day=[],
            approaching_120_day=[],
        )
        mock_invoice_service.get_lien_deadlines.return_value = mock_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/invoices/lien-deadlines")

            assert response.status_code == 200
            data = response.json()
            assert "approaching_45_day" in data
            assert "approaching_120_day" in data
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# Generate from Job Endpoint Tests
# =============================================================================


@pytest.mark.unit
class TestGenerateFromJobEndpoint:
    """Tests for POST /api/v1/invoices/generate-from-job/{job_id} endpoint."""

    @pytest.mark.asyncio
    async def test_generate_from_job_success(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
        sample_invoice_response: InvoiceResponse,
    ) -> None:
        """Test successful invoice generation from job."""
        mock_invoice_service.generate_from_job.return_value = sample_invoice_response

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        job_id = uuid.uuid4()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/generate-from-job/{job_id}",
                )

            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_from_job_payment_collected(
        self,
        mock_invoice_service: MagicMock,
        override_invoice_service: Callable[[], MagicMock],
        override_manager_or_admin: Callable[[], MagicMock],
    ) -> None:
        """Test generate fails when payment already collected on site."""
        mock_invoice_service.generate_from_job.side_effect = (
            InvalidInvoiceOperationError("Payment already collected on site")
        )

        app.dependency_overrides[get_invoice_service] = override_invoice_service
        app.dependency_overrides[require_manager_or_admin] = override_manager_or_admin

        job_id = uuid.uuid4()
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/api/v1/invoices/generate-from-job/{job_id}",
                )

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()


__all__ = [
    "TestCancelInvoiceEndpoint",
    "TestCreateInvoiceEndpoint",
    "TestGenerateFromJobEndpoint",
    "TestGetInvoiceEndpoint",
    "TestLienEndpoints",
    "TestListInvoicesEndpoint",
    "TestRecordPaymentEndpoint",
    "TestSendInvoiceEndpoint",
    "TestUpdateInvoiceEndpoint",
]
