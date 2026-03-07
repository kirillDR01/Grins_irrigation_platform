"""Functional tests for Google Sheets workflow.

Tests full polling cycles, manual lead creation, duplicate phone
deduplication, error isolation, and unique constraint enforcement.

Validates: Requirements 12.2, 12.5
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from grins_platform.services.google_sheets_poller import GoogleSheetsPoller
from grins_platform.services.google_sheets_service import GoogleSheetsService

_SUB_REPO = (
    "grins_platform.services.google_sheets_service.GoogleSheetSubmissionRepository"
)
_LEAD_REPO = "grins_platform.services.google_sheets_service.LeadRepository"
_POLLER_SUB_REPO = (
    "grins_platform.services.google_sheets_poller.GoogleSheetSubmissionRepository"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_submission(
    *,
    lead_id: object = None,
    processing_status: str = "imported",
    row_number: int = 2,
) -> MagicMock:
    sub = MagicMock()
    sub.id = uuid4()
    sub.sheet_row_number = row_number
    sub.lead_id = lead_id
    sub.processing_status = processing_status
    sub.name = "Jane Smith"
    sub.phone = "6125559876"
    sub.email = "jane@example.com"
    sub.client_type = "new"
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
    return sub


def _make_poller(
    service: GoogleSheetsService | None = None,
) -> GoogleSheetsPoller:
    svc = service or AsyncMock(spec=GoogleSheetsService)
    db_manager = AsyncMock()
    return GoogleSheetsPoller(
        service=svc,
        db_manager=db_manager,
        spreadsheet_id="sheet-123",
        sheet_name="Form Responses 1",
        poll_interval=1,
        key_path="sa.json",
    )


def _mock_httpx_client(response: MagicMock) -> AsyncMock:
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


_HTTPX_CLIENT = "grins_platform.services.google_sheets_poller.httpx.AsyncClient"


# =============================================================================
# Full Polling Cycle
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestPollingCycleWorkflow:
    """Test full polling cycle as user would experience."""

    async def test_poll_cycle_stores_submissions_and_creates_leads(
        self,
        sample_sheet_row: list[str],
    ) -> None:
        """Full poll: fetch rows → store submissions → create leads.

        Validates: Req 1.3, 1.4, 2.1, 3.1, 3.8
        """
        service = AsyncMock(spec=GoogleSheetsService)
        processed_sub = _make_submission(processing_status="lead_created")
        service.process_row.return_value = processed_sub

        poller = _make_poller(service=service)
        poller._access_token = "valid-token"
        poller._token_expiry = 9999999999.0

        sheet_response = MagicMock()
        sheet_response.status_code = 200
        sheet_response.raise_for_status = MagicMock()
        sheet_response.json.return_value = {
            "values": [
                ["Timestamp", "B", "C"],  # header
                sample_sheet_row,  # data row 2
            ],
        }

        mock_client = _mock_httpx_client(sheet_response)

        # db_manager.get_session yields a session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def _fake_get_session():
            yield mock_session

        poller._db_manager.get_session = _fake_get_session

        with (
            patch(_HTTPX_CLIENT, return_value=mock_client),
            patch(_POLLER_SUB_REPO) as sub_repo_cls,
        ):
            sub_repo_cls.return_value.get_max_row_number = AsyncMock(return_value=0)
            count = await poller._execute_poll_cycle()

        assert count == 1
        service.process_row.assert_awaited_once()
        mock_session.commit.assert_awaited_once()
        assert poller._last_error is None

    async def test_poll_cycle_skips_already_imported_rows(
        self,
        sample_sheet_row: list[str],
    ) -> None:
        """Rows at or below max_row_number are skipped.

        Validates: Req 1.4
        """
        service = AsyncMock(spec=GoogleSheetsService)
        poller = _make_poller(service=service)
        poller._access_token = "valid-token"
        poller._token_expiry = 9999999999.0

        sheet_response = MagicMock()
        sheet_response.status_code = 200
        sheet_response.raise_for_status = MagicMock()
        sheet_response.json.return_value = {
            "values": [
                ["Timestamp", "B"],
                sample_sheet_row,  # row 2
            ],
        }

        mock_client = _mock_httpx_client(sheet_response)
        mock_session = AsyncMock()

        async def _fake_get_session():
            yield mock_session

        poller._db_manager.get_session = _fake_get_session

        with (
            patch(_HTTPX_CLIENT, return_value=mock_client),
            patch(_POLLER_SUB_REPO) as sub_repo_cls,
        ):
            # max_row=5 means rows 1-5 already imported; row 2 is skipped
            sub_repo_cls.return_value.get_max_row_number = AsyncMock(return_value=5)
            count = await poller._execute_poll_cycle()

        assert count == 0
        service.process_row.assert_not_awaited()


# =============================================================================
# Manual Lead Creation Workflow
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestManualLeadCreationWorkflow:
    """Test manual lead creation as user would experience."""

    async def test_manual_create_lead_updates_submission_and_links_lead(
        self,
    ) -> None:
        """Admin creates lead from unlinked submission.

        Validates: Req 5.4, 5.5
        """
        service = GoogleSheetsService(submission_repo=None, lead_repo=None)
        mock_session = AsyncMock()

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

        assert result.processing_status == "lead_created"
        assert result.lead_id == mock_lead.id
        lead_repo.create.assert_awaited_once()
        # Verify lead was created with google_sheets source
        create_kwargs = lead_repo.create.call_args[1]
        assert create_kwargs["source_site"] == "google_sheets"
        assert create_kwargs["zip_code"] is None

    async def test_manual_create_lead_rejects_already_linked(self) -> None:
        """409 guard: submission already has a lead.

        Validates: Req 5.5
        """
        service = GoogleSheetsService(submission_repo=None, lead_repo=None)
        mock_session = AsyncMock()
        sub = _make_submission(lead_id=uuid4(), processing_status="lead_created")

        with patch(_SUB_REPO) as sub_cls, patch(_LEAD_REPO):
            sub_cls.return_value.get_by_id = AsyncMock(return_value=sub)

            with pytest.raises(ValueError, match="already has a linked lead"):
                await service.create_lead_from_submission(sub.id, mock_session)


# =============================================================================
# Duplicate Phone Deduplication
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestDuplicatePhoneDeduplication:
    """Test duplicate phone deduplication as user would experience."""

    async def test_duplicate_phone_links_existing_lead_instead_of_creating(
        self,
        sample_sheet_row: list[str],
    ) -> None:
        """New client with existing phone → link, don't create.

        Validates: Req 3.6
        """
        service = GoogleSheetsService(submission_repo=None, lead_repo=None)
        mock_session = AsyncMock()

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
        assert result.processing_status == "lead_created"


# =============================================================================
# Error Isolation
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestErrorIsolation:
    """Test error isolation as user would experience."""

    async def test_failed_row_does_not_block_subsequent_rows(self) -> None:
        """Row processing error on row N doesn't prevent row N+1.

        Validates: Req 3.7, 8.6, 8.7
        """
        service = AsyncMock(spec=GoogleSheetsService)
        # First row raises, second succeeds
        good_sub = _make_submission(processing_status="lead_created", row_number=3)
        service.process_row.side_effect = [
            RuntimeError("bad data"),
            good_sub,
        ]

        poller = _make_poller(service=service)
        poller._access_token = "valid-token"
        poller._token_expiry = 9999999999.0

        row_a = [""] * 18
        row_b = [""] * 18
        row_b[9] = "Good User"
        row_b[14] = "new"

        sheet_response = MagicMock()
        sheet_response.status_code = 200
        sheet_response.raise_for_status = MagicMock()
        sheet_response.json.return_value = {
            "values": [
                ["Timestamp"],  # header
                row_a,  # row 2 — will fail
                row_b,  # row 3 — should succeed
            ],
        }

        mock_client = _mock_httpx_client(sheet_response)
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        async def _fake_get_session():
            yield mock_session

        poller._db_manager.get_session = _fake_get_session

        with (
            patch(_HTTPX_CLIENT, return_value=mock_client),
            patch(_POLLER_SUB_REPO) as sub_repo_cls,
        ):
            sub_repo_cls.return_value.get_max_row_number = AsyncMock(return_value=0)
            count = await poller._execute_poll_cycle()

        # Only the second row succeeded
        assert count == 1
        assert service.process_row.await_count == 2


# =============================================================================
# Unique Constraint
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestUniqueConstraintEnforcement:
    """Test unique constraint prevents duplicate row imports."""

    async def test_integrity_error_on_duplicate_row_is_handled(self) -> None:
        """Duplicate sheet_row_number triggers IntegrityError → skipped.

        Validates: Req 2.2
        """
        service = AsyncMock(spec=GoogleSheetsService)
        service.process_row.side_effect = IntegrityError(
            "duplicate",
            params=None,
            orig=Exception("unique violation"),
        )

        poller = _make_poller(service=service)
        poller._access_token = "valid-token"
        poller._token_expiry = 9999999999.0

        sheet_response = MagicMock()
        sheet_response.status_code = 200
        sheet_response.raise_for_status = MagicMock()
        sheet_response.json.return_value = {
            "values": [
                ["Timestamp"],
                [""] * 18,  # row 2 — duplicate
            ],
        }

        mock_client = _mock_httpx_client(sheet_response)
        mock_session = AsyncMock()

        async def _fake_get_session():
            yield mock_session

        poller._db_manager.get_session = _fake_get_session

        with (
            patch(_HTTPX_CLIENT, return_value=mock_client),
            patch(_POLLER_SUB_REPO) as sub_repo_cls,
        ):
            sub_repo_cls.return_value.get_max_row_number = AsyncMock(return_value=0)
            # Should not raise — IntegrityError is caught and skipped
            count = await poller._execute_poll_cycle()

        assert count == 0
        assert poller._last_error is None
