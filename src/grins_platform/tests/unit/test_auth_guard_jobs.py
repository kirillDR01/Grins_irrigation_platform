"""
Unit tests for auth guard on POST /api/v1/jobs endpoint.

Verifies that the `CurrentActiveUser` dependency on `create_job`
rejects unauthenticated requests with 401 and allows authenticated
requests to create jobs normally.

Validates: Requirements 4.1, 4.2
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import get_job_service
from grins_platform.app import create_app
from grins_platform.models.enums import JobCategory, JobStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_job():
    """Create a mock job object returned by the service."""
    job = Mock()
    job.id = uuid4()
    job.customer_id = uuid4()
    job.property_id = uuid4()
    job.service_offering_id = uuid4()
    job.job_type = "spring_startup"
    job.category = JobCategory.READY_TO_SCHEDULE.value
    job.status = JobStatus.TO_BE_SCHEDULED.value
    job.description = "Test job"
    job.estimated_duration_minutes = 60
    job.priority_level = 0
    job.weather_sensitive = False
    job.staffing_required = 1
    job.equipment_required = None
    job.materials_required = None
    job.quoted_amount = None
    job.final_amount = None
    job.payment_collected_on_site = False
    job.source = None
    job.source_details = None
    job.service_agreement_id = None
    job.target_start_date = None
    job.target_end_date = None
    job.requested_at = datetime.now()
    job.approved_at = None
    job.scheduled_at = None
    job.on_my_way_at = None
    job.started_at = None
    job.completed_at = None
    job.closed_at = None
    job.notes = None
    job.summary = None
    job.customer_name = None
    job.customer_phone = None
    job.customer = None
    job.job_property = None
    job.property_address = None
    job.property_city = None
    job.property_type = None
    job.property_is_hoa = None
    job.property_is_subscription = None
    job.time_tracking_metadata = None
    job.service_preference_notes = None
    job.created_at = datetime.now()
    job.updated_at = datetime.now()
    return job


@pytest.fixture
def mock_job_service():
    """Create a mock job service."""
    return AsyncMock()


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user for auth."""
    user = Mock()
    user.id = uuid4()
    user.email = "admin@test.com"
    user.is_active = True
    user.role = "admin"
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuthGuardJobCreation:
    """Tests for auth guard on POST /api/v1/jobs.

    Validates: Requirements 4.1, 4.2
    """

    def test_post_jobs_with_no_auth_returns_401(self, mock_job_service):
        """Unauthenticated POST /api/v1/jobs returns 401.

        Validates: Requirement 4.2
        """
        app = create_app()
        # Override only the service — leave auth dependency intact so it
        # rejects requests that carry no token / cookie. The session-wide
        # conftest autouse fixture installs a fake authenticated user on
        # every app created via create_app; clear those so this test can
        # exercise the real auth-guard path.
        app.dependency_overrides[get_job_service] = lambda: mock_job_service
        app.dependency_overrides.pop(get_current_active_user, None)
        app.dependency_overrides.pop(get_current_user, None)

        client = TestClient(app)
        response = client.post(
            "/api/v1/jobs",
            json={
                "customer_id": str(uuid4()),
                "job_type": "spring_startup",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_post_jobs_with_auth_returns_201(
        self,
        mock_job,
        mock_job_service,
        mock_admin_user,
    ):
        """Authenticated POST /api/v1/jobs creates job normally.

        Validates: Requirements 4.1, 4.2
        """
        mock_job_service.create_job.return_value = mock_job

        app = create_app()
        app.dependency_overrides[get_job_service] = lambda: mock_job_service
        app.dependency_overrides[get_current_active_user] = lambda: mock_admin_user

        client = TestClient(app)
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
