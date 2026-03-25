"""
Unit tests for CRM Gap Closure Customer API endpoints (Task 7.3).

Tests: duplicates, merge, photos, invoices, payment methods, charge, PATCH.

Validates: CRM Gap Closure Req 7.1, 7.2, 8.4, 9.2, 9.3, 9.4, 10.3, 11.3, 56.2, 56.3
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.customers import router
from grins_platform.api.v1.dependencies import (
    get_customer_service,
    get_db_session,
    get_photo_service,
)
from grins_platform.exceptions import (
    CustomerNotFoundError,
    MergeConflictError,
)
from grins_platform.models.enums import CustomerStatus, LeadSource
from grins_platform.schemas.customer import (
    ChargeResponse,
    CustomerResponse,
    DuplicateCustomerMatch,
    DuplicateGroup,
    PaymentMethodResponse,
)
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.photo_service import PhotoService

# =============================================================================
# Helpers
# =============================================================================


def _sample_customer(
    customer_id: uuid.UUID | None = None,
) -> CustomerResponse:
    return CustomerResponse(
        id=customer_id or uuid.uuid4(),
        first_name="John",
        last_name="Doe",
        phone="6125551234",
        email="john@example.com",
        status=CustomerStatus.ACTIVE,
        is_priority=False,
        is_red_flag=False,
        is_slow_payer=False,
        is_new_customer=True,
        sms_opt_in=False,
        email_opt_in=False,
        lead_source=LeadSource.WEBSITE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_service() -> AsyncMock:
    """Create a mock CustomerService."""
    return AsyncMock(spec=CustomerService)


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock async DB session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_photo_svc() -> MagicMock:
    """Create a mock PhotoService."""
    return MagicMock(spec=PhotoService)


@pytest.fixture
def app(
    mock_service: AsyncMock,
    mock_db: AsyncMock,
    mock_photo_svc: MagicMock,
) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/customers")

    test_app.dependency_overrides[get_customer_service] = lambda: mock_service

    async def _db_override() -> AsyncMock:
        return mock_db

    test_app.dependency_overrides[get_db_session] = _db_override
    test_app.dependency_overrides[get_photo_service] = lambda: mock_photo_svc

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


# =============================================================================
# GET /api/v1/customers/duplicates
# =============================================================================


@pytest.mark.unit
class TestGetDuplicates:
    """Tests for GET /api/v1/customers/duplicates."""

    def test_get_duplicates_returns_groups(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Duplicate detection returns groups of matching customers."""
        cid1, cid2 = uuid.uuid4(), uuid.uuid4()
        mock_service.find_duplicates.return_value = [
            DuplicateGroup(
                customers=[
                    DuplicateCustomerMatch(
                        id=cid1,
                        first_name="John",
                        last_name="Doe",
                        phone="6125551234",
                        email=None,
                        match_type="phone",
                        similarity_score=None,
                    ),
                    DuplicateCustomerMatch(
                        id=cid2,
                        first_name="Jon",
                        last_name="Doe",
                        phone="6125551234",
                        email=None,
                        match_type="phone",
                        similarity_score=None,
                    ),
                ],
            ),
        ]

        resp = client.get("/api/v1/customers/duplicates")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert len(data[0]["customers"]) == 2

    def test_get_duplicates_with_no_duplicates_returns_empty(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """No duplicates returns empty list."""
        mock_service.find_duplicates.return_value = []

        resp = client.get("/api/v1/customers/duplicates")

        assert resp.status_code == 200
        assert resp.json() == []


# =============================================================================
# POST /api/v1/customers/merge
# =============================================================================


@pytest.mark.unit
class TestMergeCustomers:
    """Tests for POST /api/v1/customers/merge."""

    def test_merge_customers_returns_primary(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Successful merge returns the primary customer."""
        primary_id = uuid.uuid4()
        dup_id = uuid.uuid4()
        mock_service.merge_customers.return_value = _sample_customer(primary_id)

        resp = client.post(
            "/api/v1/customers/merge",
            json={
                "primary_customer_id": str(primary_id),
                "duplicate_customer_ids": [str(dup_id)],
            },
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(primary_id)

    def test_merge_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Merge with non-existent customer returns 404."""
        primary_id = uuid.uuid4()
        mock_service.merge_customers.side_effect = CustomerNotFoundError(primary_id)

        resp = client.post(
            "/api/v1/customers/merge",
            json={
                "primary_customer_id": str(primary_id),
                "duplicate_customer_ids": [str(uuid.uuid4())],
            },
        )

        assert resp.status_code == 404

    def test_merge_with_conflict_returns_409(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Merge conflict returns 409."""
        mock_service.merge_customers.side_effect = MergeConflictError(
            "Primary in duplicates",
        )

        resp = client.post(
            "/api/v1/customers/merge",
            json={
                "primary_customer_id": str(uuid.uuid4()),
                "duplicate_customer_ids": [str(uuid.uuid4())],
            },
        )

        assert resp.status_code == 409


# =============================================================================
# PATCH /api/v1/customers/{id}
# =============================================================================


@pytest.mark.unit
class TestPatchCustomer:
    """Tests for PATCH /api/v1/customers/{id}."""

    def test_patch_with_internal_notes_returns_updated(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """PATCH with internal_notes updates the customer."""
        cid = uuid.uuid4()
        response = _sample_customer(cid)
        mock_service.update_customer.return_value = response

        resp = client.patch(
            f"/api/v1/customers/{cid}",
            json={"internal_notes": "VIP customer, handle with care"},
        )

        assert resp.status_code == 200
        mock_service.update_customer.assert_called_once()

    def test_patch_with_preferred_service_times_returns_updated(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """PATCH with preferred_service_times updates the customer."""
        cid = uuid.uuid4()
        response = _sample_customer(cid)
        mock_service.update_customer.return_value = response

        resp = client.patch(
            f"/api/v1/customers/{cid}",
            json={
                "preferred_service_times": {
                    "preference": "morning",
                    "windows": ["8:00-12:00"],
                },
            },
        )

        assert resp.status_code == 200

    def test_patch_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """PATCH on non-existent customer returns 404."""
        cid = uuid.uuid4()
        mock_service.update_customer.side_effect = CustomerNotFoundError(cid)

        resp = client.patch(
            f"/api/v1/customers/{cid}",
            json={"internal_notes": "test"},
        )

        assert resp.status_code == 404


# =============================================================================
# GET /api/v1/customers/{id}/invoices
# =============================================================================


@pytest.mark.unit
class TestGetCustomerInvoices:
    """Tests for GET /api/v1/customers/{id}/invoices."""

    def test_get_invoices_returns_paginated(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Invoice history returns paginated results."""
        cid = uuid.uuid4()
        mock_service.get_customer_invoices.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }

        resp = client.get(f"/api/v1/customers/{cid}/invoices")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["page"] == 1

    def test_get_invoices_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Invoice history for non-existent customer returns 404."""
        cid = uuid.uuid4()
        mock_service.get_customer_invoices.side_effect = CustomerNotFoundError(cid)

        resp = client.get(f"/api/v1/customers/{cid}/invoices")

        assert resp.status_code == 404


# =============================================================================
# GET /api/v1/customers/{id}/payment-methods
# =============================================================================


@pytest.mark.unit
class TestGetPaymentMethods:
    """Tests for GET /api/v1/customers/{id}/payment-methods."""

    def test_get_payment_methods_returns_list(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Payment methods returns list of cards."""
        cid = uuid.uuid4()
        mock_service.get_payment_methods.return_value = [
            PaymentMethodResponse(
                id="pm_test123",
                brand="visa",
                last4="4242",
                exp_month=12,
                exp_year=2026,
                is_default=True,
            ),
        ]

        resp = client.get(f"/api/v1/customers/{cid}/payment-methods")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["brand"] == "visa"
        assert data[0]["last4"] == "4242"

    def test_get_payment_methods_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Payment methods for non-existent customer returns 404."""
        cid = uuid.uuid4()
        mock_service.get_payment_methods.side_effect = CustomerNotFoundError(cid)

        resp = client.get(f"/api/v1/customers/{cid}/payment-methods")

        assert resp.status_code == 404


# =============================================================================
# POST /api/v1/customers/{id}/charge
# =============================================================================


@pytest.mark.unit
class TestChargeCustomer:
    """Tests for POST /api/v1/customers/{id}/charge."""

    def test_charge_returns_payment_intent(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Successful charge returns payment intent details."""
        cid = uuid.uuid4()
        mock_service.charge_customer.return_value = ChargeResponse(
            payment_intent_id="pi_test123",
            status="succeeded",
            amount=5000,
            currency="usd",
        )

        resp = client.post(
            f"/api/v1/customers/{cid}/charge",
            json={"amount": 5000, "description": "Service charge"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["payment_intent_id"] == "pi_test123"
        assert data["status"] == "succeeded"
        assert data["amount"] == 5000

    def test_charge_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Charge for non-existent customer returns 404."""
        cid = uuid.uuid4()
        mock_service.charge_customer.side_effect = CustomerNotFoundError(cid)

        resp = client.post(
            f"/api/v1/customers/{cid}/charge",
            json={"amount": 5000, "description": "Test"},
        )

        assert resp.status_code == 404

    def test_charge_with_no_payment_method_returns_409(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Charge without payment method returns 409."""
        cid = uuid.uuid4()
        mock_service.charge_customer.side_effect = MergeConflictError(
            "No default payment method",
        )

        resp = client.post(
            f"/api/v1/customers/{cid}/charge",
            json={"amount": 5000, "description": "Test"},
        )

        assert resp.status_code == 409

    def test_charge_with_zero_amount_returns_422(
        self,
        client: TestClient,
    ) -> None:
        """Charge with zero amount returns validation error."""
        cid = uuid.uuid4()

        resp = client.post(
            f"/api/v1/customers/{cid}/charge",
            json={"amount": 0, "description": "Test"},
        )

        assert resp.status_code == 422


# =============================================================================
# POST /api/v1/customers/{id}/photos (upload)
# =============================================================================


@pytest.mark.unit
class TestUploadCustomerPhoto:
    """Tests for POST /api/v1/customers/{id}/photos."""

    def test_upload_photo_with_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Upload photo for non-existent customer returns 404."""
        cid = uuid.uuid4()
        mock_service.get_customer.side_effect = CustomerNotFoundError(cid)

        resp = client.post(
            f"/api/v1/customers/{cid}/photos",
            files={"file": ("test.jpg", b"fake-image-data", "image/jpeg")},
        )

        assert resp.status_code == 404

    def test_upload_photo_with_invalid_file_returns_400(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        mock_photo_svc: MagicMock,
    ) -> None:
        """Upload with invalid file type returns 400."""
        cid = uuid.uuid4()
        mock_service.get_customer.return_value = _sample_customer(cid)
        mock_photo_svc.upload_file.side_effect = ValueError(
            "File type not allowed",
        )

        resp = client.post(
            f"/api/v1/customers/{cid}/photos",
            files={"file": ("test.exe", b"bad-data", "application/octet-stream")},
        )

        assert resp.status_code == 400


# =============================================================================
# DELETE /api/v1/customers/{id}/photos/{photo_id}
# =============================================================================


@pytest.mark.unit
class TestDeleteCustomerPhoto:
    """Tests for DELETE /api/v1/customers/{id}/photos/{photo_id}."""

    def test_delete_photo_with_customer_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
    ) -> None:
        """Delete photo for non-existent customer returns 404."""
        cid = uuid.uuid4()
        photo_id = uuid.uuid4()
        mock_service.get_customer.side_effect = CustomerNotFoundError(cid)

        resp = client.delete(
            f"/api/v1/customers/{cid}/photos/{photo_id}",
        )

        assert resp.status_code == 404

    def test_delete_photo_with_photo_not_found_returns_404(
        self,
        client: TestClient,
        mock_service: AsyncMock,
        mock_db: AsyncMock,
    ) -> None:
        """Delete non-existent photo returns 404."""
        cid = uuid.uuid4()
        photo_id = uuid.uuid4()
        mock_service.get_customer.return_value = _sample_customer(cid)

        # Mock DB query returning no photo
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        resp = client.delete(
            f"/api/v1/customers/{cid}/photos/{photo_id}",
        )

        assert resp.status_code == 404
