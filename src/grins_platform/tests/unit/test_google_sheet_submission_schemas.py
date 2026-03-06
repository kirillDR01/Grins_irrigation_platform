"""Tests for Google Sheet submission Pydantic schemas.

Validates: Requirements 12.1, 12.4
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.google_sheet_submission import (
    GoogleSheetSubmissionResponse,
    PaginatedSubmissionResponse,
    SubmissionListParams,
    SyncStatusResponse,
    TriggerSyncResponse,
)


def _mock_submission(**overrides: object) -> MagicMock:
    """Create a mock ORM submission with defaults."""
    now = datetime.now()
    m = MagicMock()
    defaults = {
        "id": uuid4(),
        "sheet_row_number": 2,
        "timestamp": "2024-01-15 10:00:00",
        "spring_startup": "Yes",
        "fall_blowout": None,
        "summer_tuneup": None,
        "repair_existing": None,
        "new_system_install": None,
        "addition_to_system": None,
        "additional_services_info": None,
        "date_work_needed_by": "ASAP",
        "name": "John Doe",
        "phone": "6125550123",
        "email": "john@example.com",
        "city": "Minneapolis",
        "address": "123 Main St",
        "additional_info": None,
        "client_type": "New Client",
        "property_type": "Residential",
        "referral_source": "Google",
        "landscape_hardscape": None,
        "processing_status": "imported",
        "processing_error": None,
        "lead_id": None,
        "imported_at": now,
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


# =============================================================================
# GoogleSheetSubmissionResponse tests
# =============================================================================


@pytest.mark.unit
class TestGoogleSheetSubmissionResponse:
    """Test GoogleSheetSubmissionResponse serialization from ORM model."""

    def test_from_orm_model_all_fields(self) -> None:
        """Test all fields are present when serialized from ORM."""
        mock = _mock_submission()
        resp = GoogleSheetSubmissionResponse.model_validate(mock, from_attributes=True)
        assert resp.id == mock.id
        assert resp.sheet_row_number == 2
        assert resp.name == "John Doe"
        assert resp.phone == "6125550123"
        assert resp.processing_status == "imported"
        assert resp.imported_at == mock.imported_at

    def test_nullable_fields_as_none(self) -> None:
        """Test nullable sheet columns accept None."""
        mock = _mock_submission(
            spring_startup=None,
            name=None,
            phone=None,
            email=None,
            client_type=None,
            lead_id=None,
            processing_error=None,
        )
        resp = GoogleSheetSubmissionResponse.model_validate(mock, from_attributes=True)
        assert resp.spring_startup is None
        assert resp.name is None
        assert resp.phone is None
        assert resp.email is None
        assert resp.client_type is None
        assert resp.lead_id is None
        assert resp.processing_error is None

    def test_lead_id_present(self) -> None:
        """Test lead_id is serialized when set."""
        lid = uuid4()
        mock = _mock_submission(lead_id=lid, processing_status="lead_created")
        resp = GoogleSheetSubmissionResponse.model_validate(mock, from_attributes=True)
        assert resp.lead_id == lid
        assert resp.processing_status == "lead_created"

    def test_all_19_sheet_columns_present(self) -> None:
        """Test all 19 sheet columns are in the response."""
        sheet_cols = [
            "timestamp",
            "spring_startup",
            "fall_blowout",
            "summer_tuneup",
            "repair_existing",
            "new_system_install",
            "addition_to_system",
            "additional_services_info",
            "date_work_needed_by",
            "name",
            "phone",
            "email",
            "city",
            "address",
            "additional_info",
            "client_type",
            "property_type",
            "referral_source",
            "landscape_hardscape",
        ]
        mock = _mock_submission()
        resp = GoogleSheetSubmissionResponse.model_validate(mock, from_attributes=True)
        for col in sheet_cols:
            assert hasattr(resp, col), f"Missing column: {col}"


# =============================================================================
# SubmissionListParams tests
# =============================================================================


@pytest.mark.unit
class TestSubmissionListParams:
    """Test SubmissionListParams defaults and validation."""

    def test_defaults(self) -> None:
        """Test default values for all parameters."""
        params = SubmissionListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.processing_status is None
        assert params.client_type is None
        assert params.search is None
        assert params.sort_by == "imported_at"
        assert params.sort_order == "desc"

    def test_page_minimum_is_1(self) -> None:
        """Test page < 1 is rejected."""
        with pytest.raises(ValidationError):
            SubmissionListParams(page=0)

    def test_page_size_minimum_is_1(self) -> None:
        """Test page_size < 1 is rejected."""
        with pytest.raises(ValidationError):
            SubmissionListParams(page_size=0)

    def test_page_size_maximum_is_100(self) -> None:
        """Test page_size > 100 is rejected."""
        with pytest.raises(ValidationError):
            SubmissionListParams(page_size=101)

    def test_page_size_at_bounds(self) -> None:
        """Test page_size at 1 and 100 are accepted."""
        p1 = SubmissionListParams(page_size=1)
        assert p1.page_size == 1
        p100 = SubmissionListParams(page_size=100)
        assert p100.page_size == 100

    def test_sort_order_asc_accepted(self) -> None:
        """Test sort_order 'asc' is accepted."""
        params = SubmissionListParams(sort_order="asc")
        assert params.sort_order == "asc"

    def test_sort_order_invalid_rejected(self) -> None:
        """Test invalid sort_order is rejected."""
        with pytest.raises(ValidationError):
            SubmissionListParams(sort_order="invalid")

    def test_filters_set(self) -> None:
        """Test filter parameters are accepted."""
        params = SubmissionListParams(
            processing_status="imported",
            client_type="New Client",
            search="john",
        )
        assert params.processing_status == "imported"
        assert params.client_type == "New Client"
        assert params.search == "john"


# =============================================================================
# SyncStatusResponse tests
# =============================================================================


@pytest.mark.unit
class TestSyncStatusResponse:
    """Test SyncStatusResponse for running/stopped states."""

    def test_running_state(self) -> None:
        """Test running poller with last sync time."""
        now = datetime.now()
        resp = SyncStatusResponse(last_sync=now, is_running=True, last_error=None)
        assert resp.is_running is True
        assert resp.last_sync == now
        assert resp.last_error is None

    def test_stopped_state(self) -> None:
        """Test stopped poller with no sync time."""
        resp = SyncStatusResponse(last_sync=None, is_running=False, last_error=None)
        assert resp.is_running is False
        assert resp.last_sync is None

    def test_with_error(self) -> None:
        """Test poller with last error."""
        resp = SyncStatusResponse(
            last_sync=None,
            is_running=False,
            last_error="Connection timeout",
        )
        assert resp.last_error == "Connection timeout"


# =============================================================================
# TriggerSyncResponse tests
# =============================================================================


@pytest.mark.unit
class TestTriggerSyncResponse:
    """Test TriggerSyncResponse serialization."""

    def test_serialization(self) -> None:
        """Test new_rows_imported is serialized."""
        resp = TriggerSyncResponse(new_rows_imported=5)
        assert resp.new_rows_imported == 5

    def test_zero_rows(self) -> None:
        """Test zero rows imported."""
        resp = TriggerSyncResponse(new_rows_imported=0)
        assert resp.new_rows_imported == 0


# =============================================================================
# PaginatedSubmissionResponse tests
# =============================================================================


@pytest.mark.unit
class TestPaginatedSubmissionResponse:
    """Test PaginatedSubmissionResponse structure."""

    def test_empty_page(self) -> None:
        """Test empty paginated response."""
        resp = PaginatedSubmissionResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert resp.items == []
        assert resp.total == 0
        assert resp.total_pages == 0

    def test_with_items(self) -> None:
        """Test paginated response with items."""
        mock = _mock_submission()
        item = GoogleSheetSubmissionResponse.model_validate(mock, from_attributes=True)
        resp = PaginatedSubmissionResponse(
            items=[item],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert len(resp.items) == 1
        assert resp.total == 1
