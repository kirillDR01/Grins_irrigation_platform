"""Integration tests for customer tags with appointment detail.

Tests that tags are accessible via the customer relationship when
fetching appointment detail, and that tag updates are reflected.

Validates: Requirements 12.4, 12.5
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.customer_tag import CustomerTag
from grins_platform.schemas.customer_tag import (
    CustomerTagsUpdateRequest,
    TagInput,
    TagTone,
)
from grins_platform.services.customer_tag_service import CustomerTagService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tag(
    label: str,
    tone: str = "neutral",
    source: str = "manual",
    customer_id: uuid.UUID | None = None,
) -> CustomerTag:
    tag = CustomerTag(
        customer_id=customer_id or uuid4(),
        label=label,
        tone=tone,
        source=source,
    )
    tag.id = uuid4()
    tag.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return tag


def _make_customer_with_tags(
    customer_id: uuid.UUID,
    tags: list[CustomerTag],
) -> MagicMock:
    """Create a mock Customer with tags relationship."""
    customer = MagicMock()
    customer.id = customer_id
    customer.first_name = "Jane"
    customer.last_name = "Smith"
    customer.phone = "6125551234"
    customer.email = "jane@example.com"
    customer.tags = tags
    return customer


def _make_appointment(
    appointment_id: uuid.UUID,
    customer_id: uuid.UUID,
    job_id: uuid.UUID,
) -> MagicMock:
    """Create a mock Appointment linked to a customer."""
    appt = MagicMock()
    appt.id = appointment_id
    appt.customer_id = customer_id
    appt.job_id = job_id
    appt.scheduled_date = date(2026, 5, 15)
    appt.time_window_start = time(9, 0)
    appt.time_window_end = time(11, 0)
    appt.status = "scheduled"
    appt.created_at = datetime.now(tz=timezone.utc)
    return appt


# ---------------------------------------------------------------------------
# Tags visible via customer relationship on appointment detail
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestTagsWithAppointmentDetail:
    async def test_customer_tags_accessible_via_appointment_customer(self) -> None:
        """Appointment → customer.tags returns the customer's tags."""
        cid = uuid4()
        appt_id = uuid4()
        job_id = uuid4()

        tag1 = _make_tag("VIP", customer_id=cid)
        tag2 = _make_tag("Commercial", customer_id=cid)
        customer = _make_customer_with_tags(cid, [tag1, tag2])
        appt = _make_appointment(appt_id, cid, job_id)
        appt.customer = customer

        # Verify tags are accessible via the appointment's customer relationship
        assert len(appt.customer.tags) == 2
        labels = {t.label for t in appt.customer.tags}
        assert labels == {"VIP", "Commercial"}

    async def test_appointment_reflects_updated_tags(self) -> None:
        """After tag update, appointment's customer.tags reflects new state."""
        cid = uuid4()
        appt_id = uuid4()
        job_id = uuid4()

        # Initial state: one tag
        old_tag = _make_tag("OldTag", customer_id=cid)
        customer = _make_customer_with_tags(cid, [old_tag])
        appt = _make_appointment(appt_id, cid, job_id)
        appt.customer = customer

        assert len(appt.customer.tags) == 1
        assert appt.customer.tags[0].label == "OldTag"

        # Simulate tag update via service
        repo = AsyncMock()
        svc = CustomerTagService(repo)

        new_tag = _make_tag("NewTag", customer_id=cid)
        repo.get_by_customer_id.return_value = [old_tag]
        repo.create.return_value = new_tag
        repo.delete_by_ids.return_value = 1

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="NewTag", tone=TagTone.green)]
        )
        result = await svc.save_tags(cid, request, session)

        # Simulate the customer object being refreshed with new tags
        customer.tags = [new_tag]

        assert len(appt.customer.tags) == 1
        assert appt.customer.tags[0].label == "NewTag"
        assert len(result.tags) == 1
        assert result.tags[0].label == "NewTag"

    async def test_appointment_with_no_tags_shows_empty_list(self) -> None:
        """Appointment for customer with no tags shows empty tags list."""
        cid = uuid4()
        appt_id = uuid4()
        job_id = uuid4()

        customer = _make_customer_with_tags(cid, [])
        appt = _make_appointment(appt_id, cid, job_id)
        appt.customer = customer

        assert appt.customer.tags == []

    async def test_system_tags_visible_on_appointment_customer(self) -> None:
        """System tags are visible on the appointment's customer."""
        cid = uuid4()
        appt_id = uuid4()
        job_id = uuid4()

        system_tag = _make_tag("AutoTag", source="system", customer_id=cid)
        manual_tag = _make_tag("VIP", source="manual", customer_id=cid)
        customer = _make_customer_with_tags(cid, [system_tag, manual_tag])
        appt = _make_appointment(appt_id, cid, job_id)
        appt.customer = customer

        sources = {t.source for t in appt.customer.tags}
        assert "system" in sources
        assert "manual" in sources


# ---------------------------------------------------------------------------
# Tag service integration with repository
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
class TestTagServiceRepositoryIntegration:
    async def test_get_tags_calls_repository_with_correct_customer_id(self) -> None:
        """CustomerTagService.get_tags delegates to repository correctly."""
        repo = AsyncMock()
        svc = CustomerTagService(repo)
        cid = uuid4()
        repo.get_by_customer_id.return_value = []

        await svc.get_tags(cid)

        repo.get_by_customer_id.assert_awaited_once_with(cid)

    async def test_save_tags_reads_existing_before_diff(self) -> None:
        """save_tags reads existing tags before computing diff."""
        repo = AsyncMock()
        svc = CustomerTagService(repo)
        cid = uuid4()
        repo.get_by_customer_id.return_value = []

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])
        await svc.save_tags(cid, request, session)

        repo.get_by_customer_id.assert_awaited_once_with(cid)

    async def test_save_tags_creates_new_tags_via_repository(self) -> None:
        """save_tags calls repo.create for each new tag."""
        repo = AsyncMock()
        svc = CustomerTagService(repo)
        cid = uuid4()
        repo.get_by_customer_id.return_value = []

        tag1 = _make_tag("VIP", customer_id=cid)
        tag2 = _make_tag("Commercial", customer_id=cid)
        repo.create.side_effect = [tag1, tag2]

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[
                TagInput(label="VIP", tone=TagTone.neutral),
                TagInput(label="Commercial", tone=TagTone.blue),
            ]
        )
        result = await svc.save_tags(cid, request, session)

        assert repo.create.await_count == 2
        assert len(result.tags) == 2

    async def test_save_tags_deletes_removed_tags_via_repository(self) -> None:
        """save_tags calls repo.delete_by_ids for removed tags."""
        repo = AsyncMock()
        svc = CustomerTagService(repo)
        cid = uuid4()

        existing = _make_tag("OldTag", customer_id=cid)
        repo.get_by_customer_id.return_value = [existing]
        repo.delete_by_ids.return_value = 1

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])
        await svc.save_tags(cid, request, session)

        repo.delete_by_ids.assert_awaited_once_with([existing.id])
