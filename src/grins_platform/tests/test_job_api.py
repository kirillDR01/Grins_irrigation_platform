"""
Unit tests for Job API endpoints.

This module tests all job API endpoints with mocked services.

Validates: Requirement 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4, 12.1-12.7
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.dependencies import get_job_service
from grins_platform.app import create_app
from grins_platform.exceptions import (
    CustomerNotFoundError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
)
from grins_platform.models.enums import JobCategory, JobStatus


@pytest.fixture
def mock_job():
    """Create a mock job object."""
    job = Mock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.property_id = uuid4()
    job.service_offering_id = uuid4()
    job.job_type = "spring_startup"
    job.category = JobCategory.READY_TO_SCHEDULE.value
    job.status = JobStatus.REQUESTED.value
    job.description = "Test job"
    job.estimated_duration_minutes = 60
    job.priority_level = 0
    job.weather_sensitive = False
    job.staffing_required = 1
    job.equipment_required = None
    job.materials_required = None
    job.quoted_amount = None
    job.final_amount = None
    job.source = None
    job.source_details = None
    job.requested_at = datetime.now()
    job.approved_at = None
    job.scheduled_at = None
    job.started_at = None
    job.completed_at = None
    job.closed_at = None
    job.created_at = datetime.now()
    job.updated_at = datetime.now()
    return job


@pytest.fixture
def mock_job_service():
    """Create a mock job service."""
    return AsyncMock()


@pytest.fixture
def app(mock_job_service):
    """Create test application with mocked service."""
    application = create_app()
    application.dependency_overrides[get_job_service] = lambda: mock_job_service
    return application


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestCreateJob:
    """Tests for POST /api/v1/jobs endpoint."""

    def test_create_job_success(self, client, mock_job, mock_job_service):
        """Test successful job creation."""
        mock_job_service.create_job.return_value = mock_job

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(mock_job.customer_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == str(mock_job.id)
        assert data["job_type"] == "spring_startup"

    def test_create_job_customer_not_found(self, client, mock_job_service):
        """Test job creation with non-existent customer."""
        customer_id = uuid4()
        mock_job_service.create_job.side_effect = CustomerNotFoundError(customer_id)

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(customer_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Customer not found" in response.json()["detail"]

    def test_create_job_property_not_found(self, client, mock_job_service):
        """Test job creation with non-existent property."""
        property_id = uuid4()
        mock_job_service.create_job.side_effect = PropertyNotFoundError(property_id)

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(uuid4()),
                "property_id": str(property_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Property not found" in response.json()["detail"]

    def test_create_job_property_customer_mismatch(self, client, mock_job_service):
        """Test job creation with property not belonging to customer."""
        property_id = uuid4()
        customer_id = uuid4()
        mock_job_service.create_job.side_effect = PropertyCustomerMismatchError(
            property_id,
            customer_id,
        )

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(customer_id),
                "property_id": str(property_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not belong to customer" in response.json()["detail"]

    def test_create_job_service_not_found(self, client, mock_job_service):
        """Test job creation with non-existent service offering."""
        service_id = uuid4()
        mock_job_service.create_job.side_effect = ServiceOfferingNotFoundError(
            service_id,
        )

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(uuid4()),
                "service_offering_id": str(service_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Service offering not found" in response.json()["detail"]

    def test_create_job_service_inactive(self, client, mock_job_service):
        """Test job creation with inactive service offering."""
        service_id = uuid4()
        mock_job_service.create_job.side_effect = ServiceOfferingInactiveError(
            service_id,
        )

        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(uuid4()),
                "service_offering_id": str(service_id),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Service offering is inactive" in response.json()["detail"]


class TestGetJob:
    """Tests for GET /api/v1/jobs/{id} endpoint."""

    def test_get_job_success(self, client, mock_job, mock_job_service):
        """Test successful job retrieval."""
        mock_job_service.get_job.return_value = mock_job

        response = client.get(f"/api/v1/jobs/{mock_job.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(mock_job.id)

    def test_get_job_not_found(self, client, mock_job_service):
        """Test job retrieval with non-existent ID."""
        job_id = uuid4()
        mock_job_service.get_job.side_effect = JobNotFoundError(job_id)

        response = client.get(f"/api/v1/jobs/{job_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Job not found" in response.json()["detail"]


class TestUpdateJob:
    """Tests for PUT /api/v1/jobs/{id} endpoint."""

    def test_update_job_success(self, client, mock_job, mock_job_service):
        """Test successful job update."""
        mock_job.description = "Updated description"
        mock_job_service.update_job.return_value = mock_job

        response = client.put(
            f"/api/v1/jobs/{mock_job.id}",
            json={"description": "Updated description"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "Updated description"

    def test_update_job_not_found(self, client, mock_job_service):
        """Test job update with non-existent ID."""
        job_id = uuid4()
        mock_job_service.update_job.side_effect = JobNotFoundError(job_id)

        response = client.put(
            f"/api/v1/jobs/{job_id}",
            json={"description": "Updated"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteJob:
    """Tests for DELETE /api/v1/jobs/{id} endpoint."""

    def test_delete_job_success(self, client, mock_job, mock_job_service):
        """Test successful job deletion."""
        mock_job_service.delete_job.return_value = None

        response = client.delete(f"/api/v1/jobs/{mock_job.id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_job_not_found(self, client, mock_job_service):
        """Test job deletion with non-existent ID."""
        job_id = uuid4()
        mock_job_service.delete_job.side_effect = JobNotFoundError(job_id)

        response = client.delete(f"/api/v1/jobs/{job_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListJobs:
    """Tests for GET /api/v1/jobs endpoint."""

    def test_list_jobs_success(self, client, mock_job, mock_job_service):
        """Test successful job listing."""
        mock_job_service.list_jobs.return_value = ([mock_job], 1)

        response = client.get("/api/v1/jobs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_list_jobs_with_filters(self, client, mock_job, mock_job_service):
        """Test job listing with filters."""
        mock_job_service.list_jobs.return_value = ([mock_job], 1)

        response = client.get(
            "/api/v1/jobs",
            params={
                "status": "requested",
                "category": "ready_to_schedule",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == status.HTTP_200_OK

    def test_list_jobs_empty(self, client, mock_job_service):
        """Test job listing with no results."""
        mock_job_service.list_jobs.return_value = ([], 0)

        response = client.get("/api/v1/jobs")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0


class TestUpdateJobStatus:
    """Tests for PUT /api/v1/jobs/{id}/status endpoint."""

    def test_update_status_success(self, client, mock_job, mock_job_service):
        """Test successful status update."""
        mock_job.status = JobStatus.APPROVED.value
        mock_job_service.update_status.return_value = mock_job

        response = client.put(
            f"/api/v1/jobs/{mock_job.id}/status",
            json={"status": "approved"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "approved"

    def test_update_status_invalid_transition(self, client, mock_job_service):
        """Test status update with invalid transition."""
        job_id = uuid4()
        mock_job_service.update_status.side_effect = InvalidStatusTransitionError(
            JobStatus.REQUESTED,
            JobStatus.COMPLETED,
        )

        response = client.put(
            f"/api/v1/jobs/{job_id}/status",
            json={"status": "completed"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid status transition" in response.json()["detail"]

    def test_update_status_not_found(self, client, mock_job_service):
        """Test status update with non-existent job."""
        job_id = uuid4()
        mock_job_service.update_status.side_effect = JobNotFoundError(job_id)

        response = client.put(
            f"/api/v1/jobs/{job_id}/status",
            json={"status": "approved"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetJobHistory:
    """Tests for GET /api/v1/jobs/{id}/history endpoint."""

    def test_get_history_success(self, client, mock_job, mock_job_service):
        """Test successful history retrieval."""
        history_entry = Mock()
        history_entry.id = uuid4()
        history_entry.job_id = mock_job.id
        history_entry.previous_status = None
        history_entry.new_status = JobStatus.REQUESTED.value
        history_entry.changed_at = datetime.now()
        history_entry.changed_by = None
        history_entry.notes = None

        mock_job_service.get_status_history.return_value = [history_entry]

        response = client.get(f"/api/v1/jobs/{mock_job.id}/history")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["new_status"] == "requested"

    def test_get_history_not_found(self, client, mock_job_service):
        """Test history retrieval with non-existent job."""
        job_id = uuid4()
        mock_job_service.get_status_history.side_effect = JobNotFoundError(job_id)

        response = client.get(f"/api/v1/jobs/{job_id}/history")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetReadyToSchedule:
    """Tests for GET /api/v1/jobs/ready-to-schedule endpoint."""

    def test_get_ready_to_schedule_success(self, client, mock_job, mock_job_service):
        """Test successful ready-to-schedule retrieval."""
        mock_job_service.get_ready_to_schedule.return_value = ([mock_job], 1)

        response = client.get("/api/v1/jobs/ready-to-schedule")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1


class TestGetNeedsEstimate:
    """Tests for GET /api/v1/jobs/needs-estimate endpoint."""

    def test_get_needs_estimate_success(self, client, mock_job, mock_job_service):
        """Test successful needs-estimate retrieval."""
        mock_job.category = JobCategory.REQUIRES_ESTIMATE.value
        mock_job_service.get_needs_estimate.return_value = ([mock_job], 1)

        response = client.get("/api/v1/jobs/needs-estimate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1


class TestGetJobsByStatus:
    """Tests for GET /api/v1/jobs/by-status/{status} endpoint."""

    def test_get_by_status_success(self, client, mock_job, mock_job_service):
        """Test successful by-status retrieval."""
        mock_job_service.get_by_status.return_value = ([mock_job], 1)

        response = client.get("/api/v1/jobs/by-status/requested")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1


class TestCalculatePrice:
    """Tests for POST /api/v1/jobs/{id}/calculate-price endpoint."""

    def test_calculate_price_success(self, client, mock_job, mock_job_service):
        """Test successful price calculation."""
        mock_job_service.calculate_price.return_value = {
            "job_id": str(mock_job.id),
            "service_offering_id": str(mock_job.service_offering_id),
            "pricing_model": "flat",
            "base_price": Decimal("100.00"),
            "zone_count": None,
            "calculated_price": Decimal("100.00"),
            "requires_manual_quote": False,
        }

        response = client.post(f"/api/v1/jobs/{mock_job.id}/calculate-price")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["calculated_price"] == "100.00"
        assert data["requires_manual_quote"] is False

    def test_calculate_price_not_found(self, client, mock_job_service):
        """Test price calculation with non-existent job."""
        job_id = uuid4()
        mock_job_service.calculate_price.side_effect = JobNotFoundError(job_id)

        response = client.post(f"/api/v1/jobs/{job_id}/calculate-price")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_calculate_price_requires_manual_quote(
        self,
        client,
        mock_job,
        mock_job_service,
    ):
        """Test price calculation requiring manual quote."""
        mock_job_service.calculate_price.return_value = {
            "job_id": str(mock_job.id),
            "service_offering_id": None,
            "pricing_model": None,
            "base_price": None,
            "zone_count": None,
            "calculated_price": None,
            "requires_manual_quote": True,
        }

        response = client.post(f"/api/v1/jobs/{mock_job.id}/calculate-price")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["calculated_price"] is None
        assert data["requires_manual_quote"] is True
