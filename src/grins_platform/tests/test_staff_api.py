"""
Staff API endpoint tests.

Validates: Requirement 8.1-8.10, 9.1-9.5, 12.1-12.7
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_staff_service
from grins_platform.api.v1.staff import router
from grins_platform.exceptions import StaffNotFoundError
from grins_platform.models.enums import SkillLevel, StaffRole


@pytest.fixture
def mock_staff_service() -> AsyncMock:
    """Create a mock StaffService."""
    return AsyncMock()


@pytest.fixture
def sample_staff_data() -> dict[str, Any]:
    """Create sample staff data for testing."""
    return {
        "name": "John Technician",
        "phone": "6125551234",
        "email": "john@example.com",
        "role": "tech",
        "skill_level": "senior",
        "certifications": ["irrigation_certified"],
        "hourly_rate": "25.00",
        "is_available": True,
        "availability_notes": "Available weekdays",
    }


@pytest.fixture
def mock_staff_model() -> Mock:
    """Create a mock Staff model instance."""
    staff = Mock()
    staff.id = uuid4()
    staff.name = "John Technician"
    staff.phone = "6125551234"
    staff.email = "john@example.com"
    staff.role = StaffRole.TECH
    staff.skill_level = SkillLevel.SENIOR
    staff.certifications = ["irrigation_certified"]
    staff.assigned_equipment = ["standard_tools"]
    staff.default_start_address = None
    staff.default_start_city = None
    staff.default_start_lat = None
    staff.default_start_lng = None
    staff.hourly_rate = Decimal("25.00")
    staff.is_available = True
    staff.availability_notes = "Available weekdays"
    staff.is_active = True
    staff.created_at = datetime.now()
    staff.updated_at = datetime.now()
    return staff


@pytest.fixture
def app(mock_staff_service: AsyncMock) -> FastAPI:
    """Create FastAPI app with mocked dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/staff")
    test_app.dependency_overrides[get_staff_service] = lambda: mock_staff_service
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.mark.unit
class TestCreateStaff:
    """Tests for POST /api/v1/staff endpoint."""

    def test_create_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
        sample_staff_data: dict[str, Any],
    ) -> None:
        """Test successful staff creation returns 201."""
        mock_staff_service.create_staff.return_value = mock_staff_model
        response = client.post("/api/v1/staff", json=sample_staff_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == mock_staff_model.name
        mock_staff_service.create_staff.assert_called_once()

    def test_create_staff_minimal_data(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test staff creation with minimal required fields."""
        mock_staff_service.create_staff.return_value = mock_staff_model
        minimal_data = {"name": "Jane Tech", "phone": "6125559999", "role": "tech"}
        response = client.post("/api/v1/staff", json=minimal_data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_staff_invalid_role(self, client: TestClient) -> None:
        """Test staff creation with invalid role returns 422."""
        invalid_data = {"name": "Test", "phone": "6125551234", "role": "invalid"}
        response = client.post("/api/v1/staff", json=invalid_data)
        assert response.status_code == 422

    def test_create_staff_missing_name(self, client: TestClient) -> None:
        """Test staff creation without name returns 422."""
        invalid_data = {"phone": "6125551234", "role": "tech"}
        response = client.post("/api/v1/staff", json=invalid_data)
        assert response.status_code == 422


@pytest.mark.unit
class TestGetStaff:
    """Tests for GET /api/v1/staff/{id} endpoint."""

    def test_get_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test successful staff retrieval returns 200."""
        mock_staff_service.get_staff.return_value = mock_staff_model
        response = client.get(f"/api/v1/staff/{mock_staff_model.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(mock_staff_model.id)

    def test_get_staff_not_found(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test staff not found returns 404."""
        staff_id = uuid4()
        mock_staff_service.get_staff.side_effect = StaffNotFoundError(staff_id)
        response = client.get(f"/api/v1/staff/{staff_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestUpdateStaff:
    """Tests for PUT /api/v1/staff/{id} endpoint."""

    def test_update_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test successful staff update returns 200."""
        mock_staff_model.name = "Updated Name"
        mock_staff_service.update_staff.return_value = mock_staff_model
        response = client.put(
            f"/api/v1/staff/{mock_staff_model.id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_staff_not_found(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test update staff not found returns 404."""
        staff_id = uuid4()
        mock_staff_service.update_staff.side_effect = StaffNotFoundError(staff_id)
        response = client.put(f"/api/v1/staff/{staff_id}", json={"name": "New"})
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestDeleteStaff:
    """Tests for DELETE /api/v1/staff/{id} endpoint."""

    def test_delete_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test successful staff deletion returns 204."""
        staff_id = uuid4()
        mock_staff_service.deactivate_staff.return_value = None
        response = client.delete(f"/api/v1/staff/{staff_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_staff_not_found(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test delete staff not found returns 404."""
        staff_id = uuid4()
        mock_staff_service.deactivate_staff.side_effect = StaffNotFoundError(staff_id)
        response = client.delete(f"/api/v1/staff/{staff_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
class TestListStaff:
    """Tests for GET /api/v1/staff endpoint."""

    def test_list_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test successful staff listing returns 200."""
        mock_staff_service.list_staff.return_value = ([mock_staff_model], 1)
        response = client.get("/api/v1/staff")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_list_staff_empty(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test empty staff list returns 200 with empty items."""
        mock_staff_service.list_staff.return_value = ([], 0)
        response = client.get("/api/v1/staff")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0

    def test_list_staff_filter_by_role(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test staff listing filtered by role."""
        mock_staff_service.list_staff.return_value = ([mock_staff_model], 1)
        response = client.get("/api/v1/staff?role=tech")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.unit
class TestGetAvailableStaff:
    """Tests for GET /api/v1/staff/available endpoint."""

    def test_get_available_staff_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test successful available staff retrieval returns 200."""
        mock_staff_service.get_available_staff.return_value = [mock_staff_model]
        response = client.get("/api/v1/staff/available")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1


@pytest.mark.unit
class TestGetStaffByRole:
    """Tests for GET /api/v1/staff/by-role/{role} endpoint."""

    def test_get_staff_by_role_tech(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test get staff by tech role returns 200."""
        mock_staff_service.get_by_role.return_value = [mock_staff_model]
        response = client.get("/api/v1/staff/by-role/tech")
        assert response.status_code == status.HTTP_200_OK
        mock_staff_service.get_by_role.assert_called_once_with(StaffRole.TECH)


@pytest.mark.unit
class TestUpdateStaffAvailability:
    """Tests for PUT /api/v1/staff/{id}/availability endpoint."""

    def test_update_availability_success(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
        mock_staff_model: Mock,
    ) -> None:
        """Test successful availability update returns 200."""
        mock_staff_model.is_available = False
        mock_staff_service.update_availability.return_value = mock_staff_model
        response = client.put(
            f"/api/v1/staff/{mock_staff_model.id}/availability",
            json={"is_available": False, "availability_notes": "On vacation"},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_update_availability_not_found(
        self,
        client: TestClient,
        mock_staff_service: AsyncMock,
    ) -> None:
        """Test update availability for non-existent staff returns 404."""
        staff_id = uuid4()
        mock_staff_service.update_availability.side_effect = StaffNotFoundError(
            staff_id,
        )
        response = client.put(
            f"/api/v1/staff/{staff_id}/availability",
            json={"is_available": True},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
