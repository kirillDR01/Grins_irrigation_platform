"""Unit tests for the _carry_forward_lead_notes helper.

Covers the four merge branches from Requirement 5:
  - Empty lead notes no-op (Req 5.7)
  - Newly created customer overwrite (Req 5.2)
  - Empty customer overwrite (Req 5.3)
  - Appended customer with divider (Req 5.4)
  - Audit entry written with correct actor/subject/old-len/new-len

Validates: internal-notes-simplification Requirements 5.2, 5.3, 5.4, 5.7
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
    """Create a mock Lead with the fields _carry_forward_lead_notes reads."""
    lead = MagicMock()
    lead.id = uuid.uuid4()
    lead.notes = notes
    lead.assigned_to = assigned_to
    lead.created_at = created_at or datetime(2026, 4, 15, tzinfo=timezone.utc)
    return lead


def _make_customer(*, internal_notes: str | None = None) -> MagicMock:
    """Create a mock Customer with internal_notes."""
    customer = MagicMock()
    customer.id = uuid.uuid4()
    customer.internal_notes = internal_notes
    return customer


def _make_service() -> LeadService:
    """Create a LeadService with mocked dependencies."""
    lead_repo = AsyncMock()
    lead_repo.session = AsyncMock()
    customer_service = AsyncMock()
    job_service = AsyncMock()
    staff_repo = AsyncMock()

    return LeadService(
        lead_repository=lead_repo,
        customer_service=customer_service,
        job_service=job_service,
        staff_repository=staff_repo,
    )


@pytest.mark.unit
class TestCarryForwardLeadNotes:
    """Unit tests for LeadService._carry_forward_lead_notes.

    Validates: internal-notes-simplification Requirements 5.2, 5.3, 5.4, 5.7
    """

    # -----------------------------------------------------------------
    # Req 5.7: Empty lead notes → no-op
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_null_lead_notes_is_noop(self) -> None:
        """When lead.notes is None, customer.internal_notes is unchanged.

        **Validates: Requirement 5.7**
        """
        service = _make_service()
        lead = _make_lead(notes=None)
        customer = _make_customer(internal_notes="existing notes")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "existing notes"
        mock_audit_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_string_lead_notes_is_noop(self) -> None:
        """When lead.notes is empty string, customer.internal_notes is unchanged.

        **Validates: Requirement 5.7**
        """
        service = _make_service()
        lead = _make_lead(notes="")
        customer = _make_customer(internal_notes="existing notes")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "existing notes"
        mock_audit_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_whitespace_only_lead_notes_is_noop(self) -> None:
        """When lead.notes is whitespace-only, customer.internal_notes is unchanged.

        **Validates: Requirement 5.7**
        """
        service = _make_service()
        lead = _make_lead(notes="   \n  ")
        customer = _make_customer(internal_notes="existing notes")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "existing notes"
        mock_audit_cls.assert_not_called()

    # -----------------------------------------------------------------
    # Req 5.2: Newly created customer (empty internal_notes) → overwrite
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_new_customer_gets_lead_notes(self) -> None:
        """When customer.internal_notes is None, set to lead.notes.

        **Validates: Requirement 5.2**
        """
        service = _make_service()
        lead = _make_lead(notes="original lead context")
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "original lead context"

    # -----------------------------------------------------------------
    # Req 5.3: Empty customer internal_notes → overwrite
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_empty_customer_notes_gets_lead_notes(self) -> None:
        """When customer.internal_notes is empty string, set to lead.notes.

        **Validates: Requirement 5.3**
        """
        service = _make_service()
        lead = _make_lead(notes="lead context here")
        customer = _make_customer(internal_notes="")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "lead context here"

    @pytest.mark.asyncio
    async def test_whitespace_customer_notes_gets_lead_notes(self) -> None:
        """When customer.internal_notes is whitespace-only, set to lead.notes.

        **Validates: Requirement 5.3**
        """
        service = _make_service()
        lead = _make_lead(notes="lead context here")
        customer = _make_customer(internal_notes="   ")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        assert customer.internal_notes == "lead context here"

    # -----------------------------------------------------------------
    # Req 5.4: Both populated → append with divider
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_append_with_divider_when_both_populated(self) -> None:
        """When both have content, append lead notes with divider.

        **Validates: Requirement 5.4**
        """
        service = _make_service()
        created = datetime(2026, 4, 15, tzinfo=timezone.utc)
        lead = _make_lead(notes="new lead info", created_at=created)
        customer = _make_customer(internal_notes="existing customer notes")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        expected = (
            "existing customer notes\n\n--- From lead (2026-04-15) ---\nnew lead info"
        )
        assert customer.internal_notes == expected

    @pytest.mark.asyncio
    async def test_divider_contains_lead_created_date(self) -> None:
        """The divider line includes the lead's created_at date.

        **Validates: Requirement 5.4**
        """
        service = _make_service()
        created = datetime(2025, 12, 25, tzinfo=timezone.utc)
        lead = _make_lead(notes="holiday lead", created_at=created)
        customer = _make_customer(internal_notes="prior notes")

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        assert "--- From lead (2025-12-25) ---" in customer.internal_notes

    # -----------------------------------------------------------------
    # Audit entry
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_audit_entry_written_on_carry_forward(self) -> None:
        """An audit entry is written with correct actor/subject/old-len/new-len.

        **Validates: Requirement 5.6**
        """
        service = _make_service()
        actor_id = uuid.uuid4()
        lead = _make_lead(notes="lead notes", assigned_to=actor_id)
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        # Verify audit was called
        mock_audit.log_action.assert_awaited_once()
        call_kwargs = mock_audit.log_action.call_args.kwargs

        assert call_kwargs["actor_id"] == actor_id
        assert call_kwargs["action"] == "internal_notes.carry_forward"
        assert call_kwargs["resource_type"] == "customer"
        assert call_kwargs["resource_id"] == customer.id

        details = call_kwargs["details"]
        assert details["lead_id"] == str(lead.id)
        assert details["old_value_len"] == 0
        assert details["new_value_len"] == len("lead notes")

    @pytest.mark.asyncio
    async def test_audit_actor_is_none_when_no_actor_or_assigned_to(self) -> None:
        """Bug D guard: with no actor_staff_id and no lead.assigned_to, actor_id=None.

        Previously fell back to ``lead.id`` (a Lead UUID), which violated the
        ``audit_log.actor_id → staff.id`` FK and poisoned the session. The fix
        passes ``None`` in this case — valid since ``actor_id`` is nullable
        with ``ondelete=SET NULL``.

        **Validates: Requirement 5.6, e2e-signoff Bug D regression**
        """
        service = _make_service()
        lead = _make_lead(notes="some notes", assigned_to=None)
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit_cls.return_value = mock_audit
            await service._carry_forward_lead_notes(lead, customer)

        call_kwargs = mock_audit.log_action.call_args.kwargs
        assert call_kwargs["actor_id"] is None
        assert call_kwargs["actor_id"] != lead.id

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_raise(self) -> None:
        """If audit logging fails, the carry-forward still succeeds.

        The method catches audit exceptions and logs a warning.
        """
        service = _make_service()
        lead = _make_lead(notes="some notes")
        customer = _make_customer(internal_notes=None)

        with patch(
            "grins_platform.services.audit_service.AuditService"
        ) as mock_audit_cls:
            mock_audit = AsyncMock()
            mock_audit.log_action.side_effect = RuntimeError("DB error")
            mock_audit_cls.return_value = mock_audit
            # Should not raise
            await service._carry_forward_lead_notes(lead, customer)

        # Customer notes should still be set despite audit failure
        assert customer.internal_notes == "some notes"
