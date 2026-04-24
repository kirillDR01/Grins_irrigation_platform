"""Functional tests for customer tag lifecycle.

Tests the full tag lifecycle as a user would experience it:
create → read → update (add/remove) → read → verify diff.

Validates: Requirements 12.1, 12.2, 12.3, 12.5, 12.6, 12.7
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

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


def _make_service() -> tuple[CustomerTagService, AsyncMock]:
    repo = AsyncMock()
    svc = CustomerTagService(repo)
    return svc, repo


# ---------------------------------------------------------------------------
# Tag lifecycle: create → read → update → read
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestTagLifecycle:
    async def test_create_then_read_tags(self) -> None:
        """Create tags → read → verify returned."""
        svc, repo = _make_service()
        cid = uuid4()
        tag1 = _make_tag("VIP", customer_id=cid)
        tag2 = _make_tag("Commercial", customer_id=cid)
        repo.get_by_customer_id.return_value = [tag1, tag2]

        result = await svc.get_tags(cid)

        assert len(result) == 2
        labels = {t.label for t in result}
        assert labels == {"VIP", "Commercial"}

    async def test_update_add_and_remove_then_read(self) -> None:
        """Update (add NewTag, remove OldTag) → verify diff applied."""
        svc, repo = _make_service()
        cid = uuid4()
        old_tag = _make_tag("OldTag", customer_id=cid)
        new_tag = _make_tag("NewTag", customer_id=cid)

        repo.get_by_customer_id.return_value = [old_tag]
        repo.create.return_value = new_tag
        repo.delete_by_ids.return_value = 1

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="NewTag", tone=TagTone.blue)]
        )
        result = await svc.save_tags(cid, request, session)

        repo.delete_by_ids.assert_awaited_once_with([old_tag.id])
        repo.create.assert_awaited_once()
        assert len(result.tags) == 1
        assert result.tags[0].label == "NewTag"

    async def test_read_after_update_reflects_new_state(self) -> None:
        """After update, subsequent read returns updated tags."""
        svc, repo = _make_service()
        cid = uuid4()
        new_tag = _make_tag("NewTag", customer_id=cid)

        # First call: empty, second call: new tag present
        repo.get_by_customer_id.side_effect = [[], [new_tag]]

        # Save new tag
        repo.create.return_value = new_tag
        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="NewTag", tone=TagTone.neutral)]
        )
        await svc.save_tags(cid, request, session)

        # Read again
        result = await svc.get_tags(cid)
        assert len(result) == 1
        assert result[0].label == "NewTag"


# ---------------------------------------------------------------------------
# System tag protection
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestSystemTagProtection:
    async def test_system_tag_preserved_when_not_in_put_request(self) -> None:
        """PUT without system tag → system tag is preserved."""
        svc, repo = _make_service()
        cid = uuid4()
        system_tag = _make_tag("AutoTag", source="system", customer_id=cid)
        repo.get_by_customer_id.return_value = [system_tag]

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])
        result = await svc.save_tags(cid, request, session)

        # System tag must not be in delete list
        if repo.delete_by_ids.called:
            deleted_ids = repo.delete_by_ids.call_args[0][0]
            assert system_tag.id not in deleted_ids

        assert any(t.label == "AutoTag" for t in result.tags)

    async def test_system_tag_preserved_alongside_new_manual_tag(self) -> None:
        """System tag stays when new manual tags are added."""
        svc, repo = _make_service()
        cid = uuid4()
        system_tag = _make_tag("AutoTag", source="system", customer_id=cid)
        new_manual = _make_tag("VIP", source="manual", customer_id=cid)

        repo.get_by_customer_id.return_value = [system_tag]
        repo.create.return_value = new_manual

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="VIP", tone=TagTone.neutral)]
        )
        result = await svc.save_tags(cid, request, session)

        labels = {t.label for t in result.tags}
        assert "AutoTag" in labels
        assert "VIP" in labels


# ---------------------------------------------------------------------------
# Unique constraint enforcement
# ---------------------------------------------------------------------------


@pytest.mark.functional
class TestUniqueConstraintEnforcement:
    @pytest.mark.asyncio
    async def test_409_on_race_condition_duplicate(self) -> None:
        """Race condition unique violation → 409 Conflict."""
        svc, repo = _make_service()
        cid = uuid4()
        repo.get_by_customer_id.return_value = []
        repo.create.side_effect = IntegrityError("stmt", {}, Exception("unique"))

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[TagInput(label="VIP")])

        with pytest.raises(HTTPException) as exc_info:
            await svc.save_tags(cid, request, session)

        assert exc_info.value.status_code == 409

    def test_422_on_duplicate_labels_in_request(self) -> None:
        """Duplicate labels in a single request → 422 via schema validation."""
        with pytest.raises(ValidationError):
            CustomerTagsUpdateRequest(
                tags=[TagInput(label="VIP"), TagInput(label="VIP")]
            )


# ---------------------------------------------------------------------------
# Cascade delete (simulated via repository mock)
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestCascadeDelete:
    async def test_tags_deleted_when_customer_deleted(self) -> None:
        """Simulate cascade: after customer deletion, get_by_customer_id returns []."""
        svc, repo = _make_service()
        cid = uuid4()

        # Before deletion: tags exist
        tag = _make_tag("VIP", customer_id=cid)
        repo.get_by_customer_id.return_value = [tag]
        result_before = await svc.get_tags(cid)
        assert len(result_before) == 1

        # After deletion: DB cascade removes tags
        repo.get_by_customer_id.return_value = []
        result_after = await svc.get_tags(cid)
        assert result_after == []


# ---------------------------------------------------------------------------
# Tag validation
# ---------------------------------------------------------------------------


@pytest.mark.functional
class TestTagValidation:
    def test_invalid_label_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TagInput(label="A" * 33)

    def test_empty_label_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TagInput(label="")

    def test_invalid_tone_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TagInput(label="VIP", tone="rainbow")  # type: ignore[arg-type]

    def test_empty_request_is_valid(self) -> None:
        req = CustomerTagsUpdateRequest(tags=[])
        assert req.tags == []

    def test_max_50_tags_accepted(self) -> None:
        tags = [TagInput(label=f"tag{i}") for i in range(50)]
        req = CustomerTagsUpdateRequest(tags=tags)
        assert len(req.tags) == 50

    def test_51_tags_rejected(self) -> None:
        tags = [TagInput(label=f"tag{i}") for i in range(51)]
        with pytest.raises(ValidationError):
            CustomerTagsUpdateRequest(tags=tags)
