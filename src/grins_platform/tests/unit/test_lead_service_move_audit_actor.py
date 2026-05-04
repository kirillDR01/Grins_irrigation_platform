"""Regression tests for Bug D — `_carry_forward_lead_notes` actor_id FK violation.

Bug D (dev-branch-only, fixed by `actor_staff_id` plumbing): the previous code
wrote `lead.id` (a Lead UUID) into `audit_log.actor_id` (a FK to `staff.id`)
whenever a lead had `notes` set AND `assigned_to=None`. The FK violation
poisoned the SQLAlchemy session; the wrapping `try/except` swallowed the
audit error but couldn't recover the session, so the next `flush` raised
`PendingRollbackError` and the route returned HTTP 500.

The fix: callers (route handlers) now pass `actor_staff_id=_current_user.id`
all the way through `move_to_sales` / `move_to_jobs` into
`_carry_forward_lead_notes`, which uses
`actor_id = actor_staff_id or lead.assigned_to`. When neither is available,
`actor_id` is `None` — valid because `audit_log.actor_id` is nullable with
`ondelete=SET NULL`.

Validates: e2e-signoff Bug D regression
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from grins_platform.services.lead_service import LeadService


def _make_lead(
    *,
    notes: str | None = None,
    assigned_to: uuid.UUID | None = None,
    created_at: datetime | None = None,
) -> MagicMock:
    """Build a Lead mock with the fields `_carry_forward_lead_notes` reads."""
    lead = MagicMock()
    lead.id = uuid.uuid4()
    lead.notes = notes
    lead.assigned_to = assigned_to
    lead.created_at = created_at or datetime(2026, 5, 3, tzinfo=timezone.utc)
    return lead


def _make_customer(*, internal_notes: str | None = None) -> MagicMock:
    """Build a Customer mock for the carry-forward target."""
    customer = MagicMock()
    customer.id = uuid.uuid4()
    customer.internal_notes = internal_notes
    return customer


def _make_service() -> LeadService:
    """Build a LeadService with mocked dependencies."""
    lead_repo = AsyncMock()
    lead_repo.session = AsyncMock()
    return LeadService(
        lead_repository=lead_repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
    )


@pytest.mark.unit
class TestCarryForwardActorId:
    """Bug D regression — actor_id is never a Lead UUID."""

    @pytest.mark.asyncio
    async def test_actor_staff_id_wins_over_lead_assigned_to(self) -> None:
        """When the route passes actor_staff_id, it takes precedence over assignee."""
        service = _make_service()
        actor_id = uuid.uuid4()
        assignee_id = uuid.uuid4()
        lead = _make_lead(notes="lead notes", assigned_to=assignee_id)
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(
                lead, customer, actor_staff_id=actor_id
            )

        mock_audit.log_action.assert_awaited_once()
        assert mock_audit.log_action.call_args.kwargs["actor_id"] == actor_id

    @pytest.mark.asyncio
    async def test_falls_back_to_assigned_to_when_actor_missing(self) -> None:
        """When no actor_staff_id but assigned_to is set, fall back to assigned_to."""
        service = _make_service()
        assignee_id = uuid.uuid4()
        lead = _make_lead(notes="lead notes", assigned_to=assignee_id)
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        assert mock_audit.log_action.call_args.kwargs["actor_id"] == assignee_id

    @pytest.mark.asyncio
    async def test_actor_id_is_none_when_neither_provided(self) -> None:
        """Bug D: no actor and no assignee → actor_id is None (never lead.id)."""
        service = _make_service()
        lead = _make_lead(notes="lead notes", assigned_to=None)
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        actor_id = mock_audit.log_action.call_args.kwargs["actor_id"]
        assert actor_id is None
        assert actor_id != lead.id

    @pytest.mark.asyncio
    async def test_no_audit_when_lead_notes_empty(self) -> None:
        """Early-return path (lead.notes empty) writes no audit entry."""
        service = _make_service()
        lead = _make_lead(notes="", assigned_to=None)
        customer = _make_customer(internal_notes="existing")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            await service._carry_forward_lead_notes(
                lead, customer, actor_staff_id=uuid.uuid4()
            )

        mock_audit_cls.assert_not_called()
        assert customer.internal_notes == "existing"


@pytest.mark.unit
class TestMoveActorPassthrough:
    """move_to_sales / move_to_jobs forward actor_staff_id to carry-forward."""

    @pytest.mark.asyncio
    async def test_move_to_sales_forwards_actor_staff_id(self) -> None:
        """Live trigger condition: assigned_to=None, notes set, actor passed."""
        service = _make_service()
        actor_id = uuid.uuid4()
        lead_id = uuid.uuid4()

        lead = _make_lead(notes="trigger Bug D", assigned_to=None)
        lead.id = lead_id
        lead.moved_to = None
        lead.customer_id = None
        lead.phone = "9525550123"
        lead.email = None
        lead.name = "Test Lead"
        lead.sms_consent = False
        lead.job_requested = None
        lead.situation = "new_system"

        customer = _make_customer(internal_notes=None)
        customer_id = customer.id

        service.lead_repository.get_by_id = AsyncMock(return_value=lead)
        service.lead_repository.update = AsyncMock()
        service.customer_service.lookup_by_phone = AsyncMock(return_value=[])
        service.customer_service.create_customer = AsyncMock(return_value=customer)
        service.customer_service.repository = MagicMock()
        service.customer_service.repository.get_by_id = AsyncMock(return_value=customer)

        with (
            patch(
                "grins_platform.services.property_service.ensure_property_for_lead",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "grins_platform.services.audit_service.AuditService"
            ) as mock_audit_cls,
        ):
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service.move_to_sales(lead_id, actor_staff_id=actor_id)

        mock_audit.log_action.assert_awaited_once()
        assert mock_audit.log_action.call_args.kwargs["actor_id"] == actor_id
        assert mock_audit.log_action.call_args.kwargs["resource_id"] == customer_id

    @pytest.mark.asyncio
    async def test_move_to_jobs_force_forwards_actor_staff_id(self) -> None:
        """move_to_jobs(force=True) on a requires_estimate lead also forwards actor."""
        service = _make_service()
        actor_id = uuid.uuid4()
        lead_id = uuid.uuid4()

        lead = _make_lead(notes="trigger Bug D", assigned_to=None)
        lead.id = lead_id
        lead.moved_to = None
        lead.customer_id = None
        lead.phone = "9525550123"
        lead.email = None
        lead.name = "Test Lead"
        lead.sms_consent = False
        lead.job_requested = None
        lead.situation = "new_system"

        customer = _make_customer(internal_notes=None)
        job = MagicMock()
        job.id = uuid.uuid4()

        service.lead_repository.get_by_id = AsyncMock(return_value=lead)
        service.lead_repository.update = AsyncMock()
        service.customer_service.lookup_by_phone = AsyncMock(return_value=[])
        service.customer_service.create_customer = AsyncMock(return_value=customer)
        service.customer_service.repository = MagicMock()
        service.customer_service.repository.get_by_id = AsyncMock(return_value=customer)
        service.job_service.create_job = AsyncMock(return_value=job)

        with (
            patch(
                "grins_platform.services.property_service.ensure_property_for_lead",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "grins_platform.services.audit_service.AuditService"
            ) as mock_audit_cls,
        ):
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service.move_to_jobs(lead_id, force=True, actor_staff_id=actor_id)

        mock_audit.log_action.assert_awaited_once()
        assert mock_audit.log_action.call_args.kwargs["actor_id"] == actor_id
