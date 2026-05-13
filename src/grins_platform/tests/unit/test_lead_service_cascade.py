"""Unit tests for the Cluster A lead → customer cascade helpers.

Covers:
- _carry_forward_lead_attachments: idempotent on file_key collision.
- _cascade_lead_intake_tag: humanizes + skips dupes.
- _cascade_lead_action_tags: filters terminal markers, idempotent.
- _carry_forward_lead_data: umbrella emits the structured complete log.

The cascade helpers do not need a real DB — they touch
self.lead_repository.session via mocks of select/execute, the
CustomerTagRepository, and CustomerPhoto/LeadAttachment models. Patching
those collaborators is sufficient for unit coverage.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import ActionTag
from grins_platform.services.lead_service import LeadService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service() -> LeadService:
    repo = AsyncMock()
    repo.session = MagicMock()
    repo.session.add = MagicMock()
    repo.session.flush = AsyncMock()
    repo.session.execute = AsyncMock()
    return LeadService(
        lead_repository=repo,
        customer_service=AsyncMock(),
        job_service=AsyncMock(),
        staff_repository=AsyncMock(),
    )


def _make_lead(*, intake_tag=None, action_tags=None) -> MagicMock:
    lead = MagicMock()
    lead.id = uuid4()
    lead.intake_tag = intake_tag
    lead.action_tags = action_tags
    lead.assigned_to = uuid4()
    return lead


def _make_customer() -> MagicMock:
    customer = MagicMock()
    customer.id = uuid4()
    return customer


def _make_attachment(file_key: str) -> MagicMock:
    att = MagicMock()
    att.file_key = file_key
    att.file_name = f"{file_key}.jpg"
    att.file_size = 1024
    att.content_type = "image/jpeg"
    return att


def _execute_results(*results) -> list[MagicMock]:
    """Return a list of mock result objects that emulate session.execute()."""
    objs = []
    for items in results:
        result = MagicMock()
        scalars = MagicMock()
        scalars.all = MagicMock(return_value=list(items))
        result.scalars = MagicMock(return_value=scalars)
        result.all = MagicMock(return_value=[(item,) for item in items])
        objs.append(result)
    return objs


# ---------------------------------------------------------------------------
# Attachments cascade
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_carry_forward_lead_attachments_inserts_customer_photos() -> None:
    service = _make_service()
    lead = _make_lead()
    customer = _make_customer()
    attachments = [_make_attachment("k1"), _make_attachment("k2")]
    # First call → list of LeadAttachment rows.
    # Second call → list of existing file_keys on customer_photos (none).
    service.lead_repository.session.execute.side_effect = _execute_results(
        attachments,
        [],
    )

    with patch(
        "grins_platform.services.audit_service.AuditService",
        autospec=True,
    ):
        inserted = await service._carry_forward_lead_attachments(
            lead, customer, actor_staff_id=lead.assigned_to
        )

    assert inserted == 2
    # Two CustomerPhoto session.add() calls.
    assert service.lead_repository.session.add.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_carry_forward_lead_attachments_idempotent() -> None:
    service = _make_service()
    lead = _make_lead()
    customer = _make_customer()
    attachments = [_make_attachment("dup-key"), _make_attachment("new-key")]
    service.lead_repository.session.execute.side_effect = _execute_results(
        attachments,
        ["dup-key"],  # existing CustomerPhoto.file_key
    )

    # Audit service path also does session.add — stub it to isolate the
    # CustomerPhoto add count.
    with patch(
        "grins_platform.services.audit_service.AuditService"
    ) as audit_cls:
        audit_cls.return_value.log_action = AsyncMock(return_value=None)
        inserted = await service._carry_forward_lead_attachments(
            lead, customer
        )

    assert inserted == 1
    assert service.lead_repository.session.add.call_count == 1


# ---------------------------------------------------------------------------
# Intake tag cascade
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_intake_tag_creates_system_tag() -> None:
    service = _make_service()
    lead = _make_lead(intake_tag="qualified")
    customer = _make_customer()

    fake_repo = AsyncMock()
    fake_repo.get_by_customer_and_label = AsyncMock(return_value=None)
    fake_repo.create = AsyncMock()

    with patch(
        "grins_platform.repositories.customer_tag_repository.CustomerTagRepository",
        return_value=fake_repo,
    ):
        ok = await service._cascade_lead_intake_tag(lead, customer)

    assert ok is True
    fake_repo.create.assert_awaited_once()
    kwargs = fake_repo.create.await_args.kwargs
    assert kwargs["label"] == "Qualified"
    assert kwargs["source"] == "system"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_intake_tag_skips_duplicate() -> None:
    service = _make_service()
    lead = _make_lead(intake_tag="schedule")
    customer = _make_customer()

    fake_repo = AsyncMock()
    fake_repo.get_by_customer_and_label = AsyncMock(return_value=MagicMock())
    fake_repo.create = AsyncMock()

    with patch(
        "grins_platform.repositories.customer_tag_repository.CustomerTagRepository",
        return_value=fake_repo,
    ):
        ok = await service._cascade_lead_intake_tag(lead, customer)

    assert ok is False
    fake_repo.create.assert_not_awaited()


# ---------------------------------------------------------------------------
# Action tags cascade
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_action_tags_filters_terminal() -> None:
    service = _make_service()
    lead = _make_lead(
        action_tags=[
            ActionTag.NEEDS_ESTIMATE.value,
            ActionTag.ESTIMATE_APPROVED.value,
            ActionTag.ESTIMATE_REJECTED.value,
        ]
    )
    customer = _make_customer()

    fake_repo = AsyncMock()
    fake_repo.get_by_customer_and_label = AsyncMock(return_value=None)
    fake_repo.create = AsyncMock()

    with patch(
        "grins_platform.repositories.customer_tag_repository.CustomerTagRepository",
        return_value=fake_repo,
    ):
        inserted = await service._cascade_lead_action_tags(lead, customer)

    assert inserted == 1
    assert fake_repo.create.await_count == 1
    label_arg = fake_repo.create.await_args.kwargs["label"]
    # ActionTag.NEEDS_ESTIMATE.value humanized.
    assert label_arg == "Needs Estimate"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cascade_action_tags_empty_is_noop() -> None:
    service = _make_service()
    lead = _make_lead(action_tags=None)
    customer = _make_customer()
    inserted = await service._cascade_lead_action_tags(lead, customer)
    assert inserted == 0


# ---------------------------------------------------------------------------
# Umbrella
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_carry_forward_lead_data_emits_complete_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    service = _make_service()
    lead = _make_lead()
    customer = _make_customer()

    # Stub out the four sub-helpers so the umbrella is the unit under test.
    service._carry_forward_lead_notes = AsyncMock(return_value=True)
    service._carry_forward_lead_attachments = AsyncMock(return_value=3)
    service._cascade_lead_intake_tag = AsyncMock(return_value=True)
    service._cascade_lead_action_tags = AsyncMock(return_value=2)

    with caplog.at_level(logging.INFO):
        out = await service._carry_forward_lead_data(
            lead, customer, actor_staff_id=lead.assigned_to
        )

    assert out == {
        "notes_carried": True,
        "attachments_moved": 3,
        "intake_cascaded": True,
        "action_tags_cascaded": 2,
    }
    service._carry_forward_lead_notes.assert_awaited_once()
    service._carry_forward_lead_attachments.assert_awaited_once()
    service._cascade_lead_intake_tag.assert_awaited_once()
    service._cascade_lead_action_tags.assert_awaited_once()
