"""
Tests for DashboardService lead metrics integration.

Verifies that DashboardService correctly includes lead counts
(new_leads_today, uncontacted_leads) when a LeadRepository is provided.

Validates: Requirement 8.1-8.2
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.models.enums import JobStatus
from grins_platform.schemas.dashboard import DashboardMetrics
from grins_platform.services.dashboard_service import DashboardService

if TYPE_CHECKING:
    from unittest.mock import Mock


@pytest.fixture
def mock_customer_repository() -> Mock:
    """Create mock customer repository."""
    repo = MagicMock()
    repo.count_all = AsyncMock(return_value=50)
    repo.count_active = AsyncMock(return_value=30)
    return repo


@pytest.fixture
def mock_job_repository() -> Mock:
    """Create mock job repository."""
    repo = MagicMock()
    repo.count_by_status = AsyncMock(
        return_value={
            JobStatus.REQUESTED.value: 5,
            JobStatus.COMPLETED.value: 20,
        },
    )
    return repo


@pytest.fixture
def mock_staff_repository() -> Mock:
    """Create mock staff repository."""
    repo = MagicMock()
    repo.count_active = AsyncMock(return_value=4)
    repo.count_available = AsyncMock(return_value=2)
    return repo


@pytest.fixture
def mock_appointment_repository() -> Mock:
    """Create mock appointment repository."""
    repo = MagicMock()
    repo.count_by_date = AsyncMock(return_value=6)
    return repo


@pytest.fixture
def mock_lead_repository() -> Mock:
    """Create mock lead repository with count methods."""
    repo = MagicMock()
    repo.count_new_today = AsyncMock(return_value=3)
    repo.count_uncontacted = AsyncMock(return_value=7)
    return repo


@pytest.fixture
def service_with_leads(
    mock_customer_repository: Mock,
    mock_job_repository: Mock,
    mock_staff_repository: Mock,
    mock_appointment_repository: Mock,
    mock_lead_repository: Mock,
) -> DashboardService:
    """Create DashboardService with lead repository."""
    return DashboardService(
        customer_repository=mock_customer_repository,
        job_repository=mock_job_repository,
        staff_repository=mock_staff_repository,
        appointment_repository=mock_appointment_repository,
        lead_repository=mock_lead_repository,
    )


@pytest.fixture
def service_without_leads(
    mock_customer_repository: Mock,
    mock_job_repository: Mock,
    mock_staff_repository: Mock,
    mock_appointment_repository: Mock,
) -> DashboardService:
    """Create DashboardService without lead repository."""
    return DashboardService(
        customer_repository=mock_customer_repository,
        job_repository=mock_job_repository,
        staff_repository=mock_staff_repository,
        appointment_repository=mock_appointment_repository,
    )


@pytest.mark.unit
class TestDashboardLeadMetrics:
    """Tests for lead metrics in dashboard overview."""

    @pytest.mark.asyncio
    async def test_metrics_include_new_leads_today(
        self,
        service_with_leads: DashboardService,
    ) -> None:
        """Test that dashboard metrics include new_leads_today count."""
        result = await service_with_leads.get_overview_metrics()

        assert isinstance(result, DashboardMetrics)
        assert result.new_leads_today == 3

    @pytest.mark.asyncio
    async def test_metrics_include_uncontacted_leads(
        self,
        service_with_leads: DashboardService,
    ) -> None:
        """Test that dashboard metrics include uncontacted_leads count."""
        result = await service_with_leads.get_overview_metrics()

        assert result.uncontacted_leads == 7

    @pytest.mark.asyncio
    async def test_metrics_default_zero_without_lead_repository(
        self,
        service_without_leads: DashboardService,
    ) -> None:
        """Test that lead counts default to 0 when no lead repository."""
        result = await service_without_leads.get_overview_metrics()

        assert result.new_leads_today == 0
        assert result.uncontacted_leads == 0

    @pytest.mark.asyncio
    async def test_lead_repository_count_methods_called(
        self,
        service_with_leads: DashboardService,
        mock_lead_repository: Mock,
    ) -> None:
        """Test that lead repository count methods are called."""
        await service_with_leads.get_overview_metrics()

        mock_lead_repository.count_new_today.assert_called_once()
        mock_lead_repository.count_uncontacted.assert_called_once()

    @pytest.mark.asyncio
    async def test_lead_counts_zero_when_no_leads(
        self,
        mock_customer_repository: Mock,
        mock_job_repository: Mock,
        mock_staff_repository: Mock,
        mock_appointment_repository: Mock,
    ) -> None:
        """Test lead counts are 0 when repository returns 0."""
        lead_repo = MagicMock()
        lead_repo.count_new_today = AsyncMock(return_value=0)
        lead_repo.count_uncontacted = AsyncMock(return_value=0)

        service = DashboardService(
            customer_repository=mock_customer_repository,
            job_repository=mock_job_repository,
            staff_repository=mock_staff_repository,
            appointment_repository=mock_appointment_repository,
            lead_repository=lead_repo,
        )

        result = await service.get_overview_metrics()

        assert result.new_leads_today == 0
        assert result.uncontacted_leads == 0
