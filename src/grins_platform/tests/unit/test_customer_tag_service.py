"""Unit tests for CustomerTagService.

Validates: Requirements 12.5, 12.6, 12.7
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

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
        customer_id=customer_id or uuid.uuid4(),
        label=label,
        tone=tone,
        source=source,
    )
    tag.id = uuid.uuid4()
    tag.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return tag


def _make_service() -> tuple[CustomerTagService, AsyncMock]:
    repo = AsyncMock()
    svc = CustomerTagService(repo)
    return svc, repo


# ---------------------------------------------------------------------------
# get_tags
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTags:
    async def test_returns_empty_list_when_no_tags(self) -> None:
        svc, repo = _make_service()
        repo.get_by_customer_id.return_value = []
        result = await svc.get_tags(uuid.uuid4())
        assert result == []

    async def test_returns_all_tags_for_customer(self) -> None:
        svc, repo = _make_service()
        cid = uuid.uuid4()
        tags = [
            _make_tag("VIP", customer_id=cid),
            _make_tag("Commercial", customer_id=cid),
        ]
        repo.get_by_customer_id.return_value = tags
        result = await svc.get_tags(cid)
        assert len(result) == 2
        assert result[0].label == "VIP"
        assert result[1].label == "Commercial"


# ---------------------------------------------------------------------------
# save_tags — diff logic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveTags:
    async def test_inserts_new_manual_tags(self) -> None:
        svc, repo = _make_service()
        cid = uuid.uuid4()
        repo.get_by_customer_id.return_value = []
        new_tag = _make_tag("VIP", customer_id=cid)
        repo.create.return_value = new_tag

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="VIP", tone=TagTone.neutral)]
        )
        result = await svc.save_tags(cid, request, session)

        repo.create.assert_awaited_once_with(
            customer_id=cid, label="VIP", tone="neutral", source="manual"
        )
        assert len(result.tags) == 1
        assert result.tags[0].label == "VIP"

    async def test_deletes_removed_manual_tags(self) -> None:
        svc, repo = _make_service()
        cid = uuid.uuid4()
        existing = _make_tag("OldTag", customer_id=cid)
        repo.get_by_customer_id.return_value = [existing]
        repo.delete_by_ids.return_value = 1

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])
        result = await svc.save_tags(cid, request, session)

        repo.delete_by_ids.assert_awaited_once_with([existing.id])
        assert result.tags == []

    async def test_preserves_system_tags(self) -> None:
        svc, repo = _make_service()
        cid = uuid.uuid4()
        system_tag = _make_tag("AutoTag", source="system", customer_id=cid)
        repo.get_by_customer_id.return_value = [system_tag]

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[])
        result = await svc.save_tags(cid, request, session)

        if repo.delete_by_ids.called:
            call_args = repo.delete_by_ids.call_args[0][0]
            assert system_tag.id not in call_args

        assert any(t.label == "AutoTag" for t in result.tags)

    async def test_keeps_existing_manual_tag_not_deleted(self) -> None:
        """Manual tag present in both existing and incoming is kept, not re-created."""
        svc, repo = _make_service()
        cid = uuid.uuid4()
        existing = _make_tag("VIP", customer_id=cid)
        repo.get_by_customer_id.return_value = [existing]

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(
            tags=[TagInput(label="VIP", tone=TagTone.neutral)]
        )
        result = await svc.save_tags(cid, request, session)

        repo.create.assert_not_awaited()
        assert len(result.tags) == 1

    async def test_mixed_add_and_remove(self) -> None:
        svc, repo = _make_service()
        cid = uuid.uuid4()
        old_tag = _make_tag("OldTag", customer_id=cid)
        repo.get_by_customer_id.return_value = [old_tag]
        new_tag = _make_tag("NewTag", customer_id=cid)
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

    async def test_409_on_integrity_error(self) -> None:
        from sqlalchemy.exc import IntegrityError

        svc, repo = _make_service()
        cid = uuid.uuid4()
        repo.get_by_customer_id.return_value = []
        repo.create.side_effect = IntegrityError("stmt", {}, Exception("unique"))

        session = AsyncMock()
        request = CustomerTagsUpdateRequest(tags=[TagInput(label="VIP")])
        with pytest.raises(HTTPException) as exc_info:
            await svc.save_tags(cid, request, session)
        assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Schema-level duplicate validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTagSchemaValidation:
    def test_duplicate_labels_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CustomerTagsUpdateRequest(
                tags=[
                    TagInput(label="VIP"),
                    TagInput(label="VIP"),
                ]
            )

    def test_label_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TagInput(label="A" * 33)

    def test_empty_label_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TagInput(label="")

    def test_max_50_tags_allowed(self) -> None:
        tags = [TagInput(label=f"tag{i}") for i in range(50)]
        req = CustomerTagsUpdateRequest(tags=tags)
        assert len(req.tags) == 50

    def test_51_tags_rejected(self) -> None:
        tags = [TagInput(label=f"tag{i}") for i in range(51)]
        with pytest.raises(ValidationError):
            CustomerTagsUpdateRequest(tags=tags)

    def test_all_valid_tones_accepted(self) -> None:
        for tone in TagTone:
            tag = TagInput(label="Test", tone=tone)
            assert tag.tone == tone
