"""Unit tests for GoogleSheetsService.

Tests process_row, create_lead_from_submission, list_submissions,
get_submission with mocked repositories.

Validates: Requirements 3.1-3.11, 12.1, 12.4
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.schemas.google_sheet_submission import SubmissionListParams
from grins_platform.services.google_sheets_service import GoogleSheetsService

_SUB_REPO = (
    "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository"
)
_LEAD_REPO = "grins_platform.services.google_sheets_service.LeadRepository"


@pytest.fixture
def service() -> GoogleSheetsService:
    return GoogleSheetsService(submission_repo=None, lead_repo=None)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


def _make_submission(
    *,
    lead_id=None,
    processing_status: str = "imported",
    name: str | None = "Jane Smith",
    phone: str | None = "6125559876",
    email: str | None = "jane@example.com",
) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid4()
    sub.lead_id = lead_id
    sub.processing_status = processing_status
    sub.name = name
    sub.phone = phone
    sub.email = email
    for attr in (
        "timestamp",
        "spring_startup",
        "fall_blowout",
        "summer_tuneup",
        "repair_existing",
        "new_system_install",
        "addition_to_system",
        "additional_services_info",
        "date_work_needed_by",
        "city",
        "address",
        "property_type",
        "referral_source",
        "landscape_hardscape",
    ):
        setattr(sub, attr, "")
    sub.client_type = "new"
    return sub


# =============================================================================
# process_row tests
# =============================================================================


@pytest.mark.unit
class TestProcessRow:
    """Tests for GoogleSheetsService.process_row."""

    @pytest.mark.asyncio
    async def test_new_client_creates_lead(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        mock_sub = _make_submission()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated_sub = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            result = await service.process_row(sample_sheet_row, 2, mock_session)

        lead_repo.create.assert_awaited_once()
        create_kwargs = lead_repo.create.call_args[1]
        assert create_kwargs["lead_source"] == "google_form"
        assert create_kwargs["source_detail"] == "New client work request"
        sub_repo.update.assert_awaited()
        update_kwargs = sub_repo.update.call_args[0][1]
        assert update_kwargs["promoted_to_lead_id"] == mock_lead.id
        assert update_kwargs["promoted_at"] is not None
        assert result.processing_status == "lead_created"
        assert result.lead_id == mock_lead.id

    @pytest.mark.asyncio
    async def test_existing_client_creates_lead(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        sample_sheet_row[14] = "existing"
        mock_sub = _make_submission(processing_status="imported")
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated_sub = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            result = await service.process_row(sample_sheet_row, 2, mock_session)

        lead_repo.create.assert_awaited_once()
        create_kwargs = lead_repo.create.call_args[1]
        assert create_kwargs["lead_source"] == "google_form"
        assert create_kwargs["source_detail"] == "Existing client work request"
        assert result.processing_status == "lead_created"

    @pytest.mark.asyncio
    async def test_new_client_duplicate_phone_links_existing_lead(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        existing_lead = MagicMock()
        existing_lead.id = uuid4()
        mock_sub = _make_submission()
        updated_sub = _make_submission(
            lead_id=existing_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(
                return_value=existing_lead,
            )
            lead_repo.create = AsyncMock()

            result = await service.process_row(sample_sheet_row, 2, mock_session)

        lead_repo.create.assert_not_awaited()
        assert result.lead_id == existing_lead.id

    @pytest.mark.asyncio
    async def test_empty_client_type_creates_lead(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        sample_sheet_row[14] = ""
        mock_sub = _make_submission()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated_sub = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            result = await service.process_row(sample_sheet_row, 2, mock_session)

        lead_repo.create.assert_awaited_once()
        create_kwargs = lead_repo.create.call_args[1]
        assert create_kwargs["lead_source"] == "google_form"
        assert create_kwargs["source_detail"] == "Existing client work request"
        assert result.processing_status == "lead_created"

    @pytest.mark.asyncio
    async def test_name_fallback_to_unknown(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        sample_sheet_row[9] = ""
        mock_sub = _make_submission()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated_sub = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            await service.process_row(sample_sheet_row, 2, mock_session)

        assert lead_repo.create.call_args[1]["name"] == "Unknown"

    @pytest.mark.asyncio
    async def test_phone_fallback_to_zeros(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_sheet_row: list[str],
    ) -> None:
        sample_sheet_row[10] = ""
        mock_sub = _make_submission()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated_sub = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.create = AsyncMock(return_value=mock_sub)
            sub_repo.update = AsyncMock()
            sub_repo.get_by_id = AsyncMock(return_value=updated_sub)

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            await service.process_row(sample_sheet_row, 2, mock_session)

        assert lead_repo.create.call_args[1]["phone"] == "0000000000"


# =============================================================================
# create_lead_from_submission tests
# =============================================================================


@pytest.mark.unit
class TestCreateLeadFromSubmission:
    """Tests for GoogleSheetsService.create_lead_from_submission."""

    @pytest.mark.asyncio
    async def test_creates_lead_for_unlinked_submission(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        sub = _make_submission()
        mock_lead = MagicMock()
        mock_lead.id = uuid4()
        updated = _make_submission(
            lead_id=mock_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(side_effect=[sub, updated])
            sub_repo.update = AsyncMock()

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(return_value=None)
            lead_repo.create = AsyncMock(return_value=mock_lead)

            result = await service.create_lead_from_submission(sub.id, mock_session)

        lead_repo.create.assert_awaited_once()
        assert result.lead_id == mock_lead.id

    @pytest.mark.asyncio
    async def test_conflict_when_lead_already_linked(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        sub = _make_submission(lead_id=uuid4(), processing_status="lead_created")

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO):
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(return_value=sub)

            with pytest.raises(ValueError, match="already has a linked lead"):
                await service.create_lead_from_submission(sub.id, mock_session)

    @pytest.mark.asyncio
    async def test_not_found_raises_value_error(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO):
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(ValueError, match="not found"):
                await service.create_lead_from_submission(uuid4(), mock_session)

    @pytest.mark.asyncio
    async def test_links_existing_lead_on_duplicate_phone(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        sub = _make_submission()
        existing_lead = MagicMock()
        existing_lead.id = uuid4()
        updated = _make_submission(
            lead_id=existing_lead.id,
            processing_status="lead_created",
        )

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO) as lead_cls:
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(side_effect=[sub, updated])
            sub_repo.update = AsyncMock()

            lead_repo = lead_cls.return_value
            lead_repo.get_by_phone_and_active_status = AsyncMock(
                return_value=existing_lead,
            )
            lead_repo.create = AsyncMock()

            result = await service.create_lead_from_submission(sub.id, mock_session)

        lead_repo.create.assert_not_awaited()
        assert result.lead_id == existing_lead.id


# =============================================================================
# list_submissions tests
# =============================================================================


@pytest.mark.unit
class TestListSubmissions:
    """Tests for GoogleSheetsService.list_submissions."""

    @pytest.mark.asyncio
    async def test_returns_paginated_response(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
        sample_submission_model: MagicMock,
    ) -> None:
        with patch(_SUB_REPO) as sub_cls:
            sub_repo = sub_cls.return_value
            sub_repo.list_with_filters = AsyncMock(
                return_value=([sample_submission_model], 1),
            )

            params = SubmissionListParams(page=1, page_size=20)
            result = await service.list_submissions(params, mock_session)

        assert result.total == 1
        assert result.page == 1
        assert result.total_pages == 1
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_empty_list(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        with patch(_SUB_REPO) as sub_cls:
            sub_repo = sub_cls.return_value
            sub_repo.list_with_filters = AsyncMock(return_value=([], 0))

            params = SubmissionListParams()
            result = await service.list_submissions(params, mock_session)

        assert result.total == 0
        assert result.total_pages == 0
        assert len(result.items) == 0


# =============================================================================
# get_submission tests
# =============================================================================


@pytest.mark.unit
class TestGetSubmission:
    """Tests for GoogleSheetsService.get_submission."""

    @pytest.mark.asyncio
    async def test_returns_submission(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        sub = _make_submission()

        with patch(_SUB_REPO) as sub_cls:
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(return_value=sub)

            result = await service.get_submission(sub.id, mock_session)

        assert result == sub

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self,
        service: GoogleSheetsService,
        mock_session: AsyncMock,
    ) -> None:
        with patch(_SUB_REPO) as sub_cls:
            sub_repo = sub_cls.return_value
            sub_repo.get_by_id = AsyncMock(return_value=None)

            result = await service.get_submission(uuid4(), mock_session)

        assert result is None
