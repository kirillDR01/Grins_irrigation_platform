"""Unit tests for lead move-out (to Jobs/Sales) and deletion.

Tests cover:
- Hard delete with confirmation
- Move to Jobs: customer auto-gen, Job creation, lead marking
- Move to Sales: customer auto-generation, SalesEntry creation, lead marking
- Lead filtering excludes moved leads

Validates: Requirements 9.1, 9.2, 12.1, 12.2
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import LeadAlreadyConvertedError, LeadNotFoundError
from grins_platform.models.enums import LeadSituation
from grins_platform.services.lead_service import LeadService

# =============================================================================
# Helpers
# =============================================================================


def _make_lead(
    *,
    lead_id=None,
    name="John Doe",
    phone="6125550123",
    email=None,
    situation=LeadSituation.REPAIR.value,
    notes=None,
    customer_id=None,
    moved_to=None,
    moved_at=None,
    job_requested=None,
    sms_consent=False,
):
    """Create a mock Lead model."""
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.email = email
    lead.situation = situation
    lead.notes = notes
    lead.customer_id = customer_id
    lead.moved_to = moved_to
    lead.moved_at = moved_at
    lead.job_requested = job_requested
    lead.sms_consent = sms_consent
    lead.source_site = "residential"
    lead.lead_source = "website"
    return lead


def _build_service(
    *,
    lead_repo=None,
    customer_service=None,
    job_service=None,
    staff_repo=None,
) -> LeadService:
    """Build LeadService with mocked deps."""
    return LeadService(
        lead_repository=lead_repo or AsyncMock(),
        customer_service=customer_service or AsyncMock(),
        job_service=job_service or AsyncMock(),
        staff_repository=staff_repo or AsyncMock(),
    )


# =============================================================================
# Delete Lead — Req 9.1
# =============================================================================


@pytest.mark.unit
class TestDeleteLead:
    """Tests for lead hard deletion. Validates: Req 9.1"""

    @pytest.mark.asyncio
    async def test_delete_lead_with_valid_id_deletes(self) -> None:
        lead_id = uuid4()
        lead = _make_lead(lead_id=lead_id)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.delete = AsyncMock()

        svc = _build_service(lead_repo=repo)
        await svc.delete_lead(lead_id)

        repo.delete.assert_awaited_once_with(lead_id)

    @pytest.mark.asyncio
    async def test_delete_lead_with_not_found_raises(self) -> None:
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(lead_repo=repo)
        with pytest.raises(LeadNotFoundError):
            await svc.delete_lead(uuid4())


# =============================================================================
# Move to Jobs — Req 9.2, 12.1
# =============================================================================


@pytest.mark.unit
class TestMoveToJobs:
    """Tests for moving a lead to Jobs. Validates: Req 9.2, 12.1"""

    @pytest.mark.asyncio
    async def test_move_to_jobs_with_existing_customer_creates_job(self) -> None:
        customer_id = uuid4()
        lead = _make_lead(customer_id=customer_id, situation=LeadSituation.REPAIR.value)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        job_mock = MagicMock()
        job_mock.id = uuid4()
        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=job_mock)

        svc = _build_service(lead_repo=repo, job_service=job_service)
        result = await svc.move_to_jobs(lead.id)

        assert result.customer_id == customer_id
        assert result.job_id == job_mock.id
        job_service.create_job.assert_awaited_once()
        # Verify lead marked as moved
        update_call = repo.update.call_args
        assert update_call[0][1]["moved_to"] == "jobs"
        assert "moved_at" in update_call[0][1]

    @pytest.mark.asyncio
    async def test_move_to_jobs_without_customer_auto_generates(self) -> None:
        lead = _make_lead(customer_id=None, name="Jane Smith")
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        new_customer = MagicMock()
        new_customer.id = uuid4()
        customer_service = AsyncMock()
        customer_service.create_customer = AsyncMock(return_value=new_customer)
        customer_service.lookup_by_phone = AsyncMock(return_value=[])

        job_mock = MagicMock()
        job_mock.id = uuid4()
        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=job_mock)

        svc = _build_service(
            lead_repo=repo,
            customer_service=customer_service,
            job_service=job_service,
        )
        result = await svc.move_to_jobs(lead.id)

        assert result.customer_id == new_customer.id
        customer_service.create_customer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_move_to_jobs_with_job_requested_uses_description(self) -> None:
        lead = _make_lead(
            customer_id=uuid4(),
            job_requested="Fix broken sprinkler head",
            situation=LeadSituation.REPAIR.value,
        )
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()

        job_mock = MagicMock()
        job_mock.id = uuid4()
        job_service = AsyncMock()
        job_service.create_job = AsyncMock(return_value=job_mock)

        svc = _build_service(lead_repo=repo, job_service=job_service)
        await svc.move_to_jobs(lead.id)

        create_call = job_service.create_job.call_args[0][0]
        assert create_call.description == "Fix broken sprinkler head"

    @pytest.mark.asyncio
    async def test_move_to_jobs_with_not_found_raises(self) -> None:
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(lead_repo=repo)
        with pytest.raises(LeadNotFoundError):
            await svc.move_to_jobs(uuid4())

    @pytest.mark.asyncio
    async def test_move_to_jobs_with_already_moved_raises(self) -> None:
        lead = _make_lead(moved_to="sales")
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)

        svc = _build_service(lead_repo=repo)
        with pytest.raises(LeadAlreadyConvertedError):
            await svc.move_to_jobs(lead.id)


# =============================================================================
# Move to Sales — Req 9.2, 12.2
# =============================================================================


@pytest.mark.unit
class TestMoveToSales:
    """Tests for moving a lead to Sales. Validates: Req 9.2, 12.2"""

    @pytest.mark.asyncio
    async def test_move_to_sales_with_existing_customer_creates_entry(self) -> None:
        customer_id = uuid4()
        lead = _make_lead(
            customer_id=customer_id,
            job_requested="New irrigation system",
            notes="Large backyard",
        )
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def fake_refresh(obj):
            obj.id = uuid4()

        session.refresh = AsyncMock(side_effect=fake_refresh)

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()
        repo.session = session

        svc = _build_service(lead_repo=repo)
        result = await svc.move_to_sales(lead.id)

        assert result.customer_id == customer_id
        assert result.sales_entry_id is not None
        session.add.assert_called_once()
        added_entry = session.add.call_args[0][0]
        assert added_entry.status == "schedule_estimate"
        assert added_entry.job_type == "New irrigation system"
        # Verify lead marked as moved
        update_call = repo.update.call_args
        assert update_call[0][1]["moved_to"] == "sales"

    @pytest.mark.asyncio
    async def test_move_to_sales_without_customer_auto_generates(self) -> None:
        lead = _make_lead(customer_id=None, name="Bob Jones")
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()

        async def fake_refresh(obj):
            obj.id = uuid4()

        session.refresh = AsyncMock(side_effect=fake_refresh)

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)
        repo.update = AsyncMock()
        repo.session = session

        new_customer = MagicMock()
        new_customer.id = uuid4()
        customer_service = AsyncMock()
        customer_service.create_customer = AsyncMock(return_value=new_customer)
        customer_service.lookup_by_phone = AsyncMock(return_value=[])

        svc = _build_service(lead_repo=repo, customer_service=customer_service)
        result = await svc.move_to_sales(lead.id)

        assert result.customer_id == new_customer.id
        customer_service.create_customer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_move_to_sales_with_not_found_raises(self) -> None:
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(lead_repo=repo)
        with pytest.raises(LeadNotFoundError):
            await svc.move_to_sales(uuid4())

    @pytest.mark.asyncio
    async def test_move_to_sales_with_already_moved_raises(self) -> None:
        lead = _make_lead(moved_to="jobs")
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=lead)

        svc = _build_service(lead_repo=repo)
        with pytest.raises(LeadAlreadyConvertedError):
            await svc.move_to_sales(lead.id)


# =============================================================================
# _ensure_customer_for_lead — Req 12.1, 12.2
# =============================================================================


@pytest.mark.unit
class TestEnsureCustomerForLead:
    """Tests for customer auto-generation from lead. Validates: Req 12.1, 12.2"""

    @pytest.mark.asyncio
    async def test_ensure_customer_with_existing_returns_id(self) -> None:
        existing_id = uuid4()
        lead = _make_lead(customer_id=existing_id)

        repo = AsyncMock()
        svc = _build_service(lead_repo=repo)
        result = await svc._ensure_customer_for_lead(lead)

        assert result == existing_id

    @pytest.mark.asyncio
    async def test_ensure_customer_without_creates_new(self) -> None:
        lead = _make_lead(customer_id=None, name="Alice Wonder", phone="6125559999")

        new_customer = MagicMock()
        new_customer.id = uuid4()
        customer_service = AsyncMock()
        customer_service.create_customer = AsyncMock(return_value=new_customer)
        customer_service.lookup_by_phone = AsyncMock(return_value=[])

        repo = AsyncMock()
        repo.update = AsyncMock()

        svc = _build_service(lead_repo=repo, customer_service=customer_service)
        result = await svc._ensure_customer_for_lead(lead)

        assert result == new_customer.id
        customer_service.create_customer.assert_awaited_once()
        # Verify lead linked to new customer
        repo.update.assert_awaited_once()
        update_data = repo.update.call_args[1]["update_data"]
        assert update_data["customer_id"] == new_customer.id

    @pytest.mark.asyncio
    async def test_ensure_customer_with_single_name_uses_as_last(self) -> None:
        lead = _make_lead(customer_id=None, name="Madonna")

        new_customer = MagicMock()
        new_customer.id = uuid4()
        customer_service = AsyncMock()
        customer_service.create_customer = AsyncMock(return_value=new_customer)
        customer_service.lookup_by_phone = AsyncMock(return_value=[])

        repo = AsyncMock()
        repo.update = AsyncMock()

        svc = _build_service(lead_repo=repo, customer_service=customer_service)
        await svc._ensure_customer_for_lead(lead)

        create_call = customer_service.create_customer.call_args[0][0]
        # Single name → customer_last_name = first_name
        assert create_call.first_name == "Madonna"
        assert create_call.last_name == "Madonna"
