"""Unit tests for MarketingService and MediaService.

Properties:
  P61: Lead source analytics and conversion funnel
  P62: Marketing budget vs actual spend
  P63: QR code URL contains correct UTM parameters

Validates: Requirements 49.6, 58.5, 63.7, 64.5, 65.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest

from grins_platform.models.enums import MediaType
from grins_platform.schemas.marketing import QRCodeRequest
from grins_platform.schemas.media import MediaCreate
from grins_platform.services.marketing_service import (
    MarketingService,
)
from grins_platform.services.media_service import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    MediaNotFoundError,
    MediaService,
    MediaValidationError,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_source_row(
    source: str,
    total: int,
    converted: int,
) -> tuple[str, int, int]:
    """Create a mock row for source analytics query results."""
    return (source, total, converted)


def _make_funnel_row(
    total: int,
    contacted: int,
    qualified: int,
    converted: int,
) -> tuple[int, int, int, int]:
    """Create a mock row for funnel query results."""
    return (total, contacted, qualified, converted)


def _make_spend_row(
    source: str,
    amount: Decimal,
) -> tuple[str, Decimal]:
    """Create a mock row for spend-by-source query results."""
    return (source, amount)


def _make_conversion_row(
    source: str,
    count: int,
) -> tuple[str, int]:
    """Create a mock row for conversions-by-source query results."""
    return (source, count)


def _mock_db_for_analytics(
    source_rows: list[tuple[str, int, int]],
    avg_conversion_hours: float | None,
    funnel_row: tuple[int, int, int, int],
) -> AsyncMock:
    """Build a mock db session for get_lead_analytics.

    The service calls db.execute() three times:
    1. _get_source_analytics → result.all() returns source_rows
    2. _get_avg_conversion_time → result.scalar() returns avg hours
    3. _get_funnel → result.one() returns funnel_row
    """
    db = AsyncMock()

    source_result = MagicMock()
    source_result.all.return_value = source_rows

    avg_result = MagicMock()
    avg_result.scalar.return_value = avg_conversion_hours

    funnel_result = MagicMock()
    funnel_result.one.return_value = funnel_row

    db.execute.side_effect = [source_result, avg_result, funnel_result]
    return db


def _mock_db_for_cac(
    spend_rows: list[tuple[str, Decimal]],
    conversion_rows: list[tuple[str, int]],
) -> AsyncMock:
    """Build a mock db session for get_cac.

    The service calls db.execute() twice:
    1. _get_spend_by_source → result.all() returns spend_rows
    2. _get_conversions_by_source → result.all() returns conversion_rows
    """
    db = AsyncMock()

    spend_result = MagicMock()
    spend_result.all.return_value = spend_rows

    conv_result = MagicMock()
    conv_result.all.return_value = conversion_rows

    db.execute.side_effect = [spend_result, conv_result]
    return db


def _make_media_item_mock(
    *,
    media_id: str | None = None,
    file_key: str = "media/test.jpg",
    file_name: str = "test.jpg",
    file_size: int = 1024,
    content_type: str = "image/jpeg",
    media_type: str = "image",
    category: str | None = "photos",
    caption: str | None = "Test caption",
    is_public: bool = False,
) -> MagicMock:
    """Create a mock MediaLibraryItem."""
    item = MagicMock()
    item.id = media_id or uuid4()
    item.file_key = file_key
    item.file_name = file_name
    item.file_size = file_size
    item.content_type = content_type
    item.media_type = media_type
    item.category = category
    item.caption = caption
    item.is_public = is_public
    item.created_at = datetime.now(tz=timezone.utc)
    item.updated_at = datetime.now(tz=timezone.utc)
    return item


# =============================================================================
# Property 61: Lead source analytics and conversion funnel
# Validates: Requirements 63.2, 63.3, 63.4, 63.5
# =============================================================================


@pytest.mark.unit
class TestProperty61LeadSourceAnalyticsAndConversionFunnel:
    """P61: Lead source analytics and conversion funnel.

    Validates: Requirements 63.2, 63.3, 63.4, 63.5
    """

    @pytest.mark.asyncio
    async def test_get_lead_analytics_with_multiple_sources_returns_correct_counts(
        self,
    ) -> None:
        """get_lead_analytics returns correct source counts and conversion rates."""
        db = _mock_db_for_analytics(
            source_rows=[
                _make_source_row("website", 50, 10),
                _make_source_row("referral", 30, 15),
            ],
            avg_conversion_hours=48.5,
            funnel_row=_make_funnel_row(80, 60, 40, 25),
        )
        svc = MarketingService()

        result = await svc.get_lead_analytics(db)

        assert result.total_leads == 80
        assert len(result.sources) == 2
        assert result.sources[0].source == "website"
        assert result.sources[0].count == 50
        assert result.sources[0].converted == 10
        assert result.sources[0].conversion_rate == 20.0
        assert result.sources[1].source == "referral"
        assert result.sources[1].count == 30
        assert result.sources[1].converted == 15
        assert result.sources[1].conversion_rate == 50.0
        assert result.top_source == "website"
        assert result.avg_time_to_conversion_hours == 48.5

    @pytest.mark.asyncio
    async def test_get_lead_analytics_with_no_leads_returns_zero_totals(
        self,
    ) -> None:
        """get_lead_analytics with no leads returns zero totals."""
        db = _mock_db_for_analytics(
            source_rows=[],
            avg_conversion_hours=None,
            funnel_row=_make_funnel_row(0, 0, 0, 0),
        )
        svc = MarketingService()

        result = await svc.get_lead_analytics(db)

        assert result.total_leads == 0
        assert result.conversion_rate == 0.0
        assert result.avg_time_to_conversion_hours is None
        assert result.top_source is None
        assert result.sources == []

    @pytest.mark.asyncio
    async def test_get_lead_analytics_funnel_has_four_stages_in_correct_order(
        self,
    ) -> None:
        """get_lead_analytics funnel has 4 stages in correct order."""
        db = _mock_db_for_analytics(
            source_rows=[_make_source_row("website", 100, 20)],
            avg_conversion_hours=72.0,
            funnel_row=_make_funnel_row(100, 75, 50, 20),
        )
        svc = MarketingService()

        result = await svc.get_lead_analytics(db)

        assert len(result.funnel) == 4
        assert result.funnel[0].stage == "Total Leads"
        assert result.funnel[0].count == 100
        assert result.funnel[1].stage == "Contacted"
        assert result.funnel[1].count == 75
        assert result.funnel[2].stage == "Qualified"
        assert result.funnel[2].count == 50
        assert result.funnel[3].stage == "Converted"
        assert result.funnel[3].count == 20

    @pytest.mark.asyncio
    async def test_get_lead_analytics_with_overall_conversion_rate_calculated(
        self,
    ) -> None:
        """Overall conversion rate is calculated from source totals."""
        db = _mock_db_for_analytics(
            source_rows=[
                _make_source_row("website", 60, 12),
                _make_source_row("referral", 40, 8),
            ],
            avg_conversion_hours=36.0,
            funnel_row=_make_funnel_row(100, 80, 60, 20),
        )
        svc = MarketingService()

        result = await svc.get_lead_analytics(db)

        # 20 converted / 100 total = 20.0%
        assert result.conversion_rate == 20.0


# =============================================================================
# Property 62: Marketing budget vs actual spend
# Validates: Requirements 64.3, 64.4
# =============================================================================


@pytest.mark.unit
class TestProperty62MarketingBudgetVsActualSpend:
    """P62: Marketing budget vs actual spend (CAC calculation).

    Validates: Requirements 64.3, 64.4
    """

    @pytest.mark.asyncio
    async def test_get_cac_with_spend_and_conversions_returns_correct_cac(
        self,
    ) -> None:
        """get_cac calculates CAC correctly per source."""
        db = _mock_db_for_cac(
            spend_rows=[
                _make_spend_row("google_ads", Decimal("1000.00")),
                _make_spend_row("facebook", Decimal("500.00")),
            ],
            conversion_rows=[
                _make_conversion_row("google_ads", 10),
                _make_conversion_row("facebook", 5),
            ],
        )
        svc = MarketingService()

        results = await svc.get_cac(db)

        by_source = {r.source: r for r in results}
        assert by_source["google_ads"].cac == Decimal("100.00")
        assert by_source["google_ads"].total_spend == Decimal("1000.00")
        assert by_source["google_ads"].customers_acquired == 10
        assert by_source["facebook"].cac == Decimal("100.00")
        assert by_source["facebook"].total_spend == Decimal("500.00")
        assert by_source["facebook"].customers_acquired == 5

    @pytest.mark.asyncio
    async def test_get_cac_with_zero_conversions_returns_zero_cac(
        self,
    ) -> None:
        """get_cac with zero conversions returns zero CAC (no division error)."""
        db = _mock_db_for_cac(
            spend_rows=[
                _make_spend_row("google_ads", Decimal("500.00")),
            ],
            conversion_rows=[],
        )
        svc = MarketingService()

        results = await svc.get_cac(db)

        assert len(results) == 1
        assert results[0].source == "google_ads"
        assert results[0].cac == Decimal(0)
        assert results[0].customers_acquired == 0

    @pytest.mark.asyncio
    async def test_get_cac_with_no_data_returns_empty_list(
        self,
    ) -> None:
        """get_cac with no data returns empty list."""
        db = _mock_db_for_cac(
            spend_rows=[],
            conversion_rows=[],
        )
        svc = MarketingService()

        results = await svc.get_cac(db)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_cac_with_conversions_but_no_spend_returns_zero_cac(
        self,
    ) -> None:
        """Source with conversions but no spend returns zero CAC."""
        db = _mock_db_for_cac(
            spend_rows=[],
            conversion_rows=[
                _make_conversion_row("referral", 8),
            ],
        )
        svc = MarketingService()

        results = await svc.get_cac(db)

        assert len(results) == 1
        assert results[0].source == "referral"
        assert results[0].cac == Decimal(0)
        assert results[0].total_spend == Decimal(0)
        assert results[0].customers_acquired == 8


# =============================================================================
# Property 63: QR code URL contains correct UTM parameters
# Validates: Requirements 65.1, 65.3
# =============================================================================


@pytest.mark.unit
class TestProperty63QRCodeUTMParameters:
    """P63: QR code URL contains correct UTM parameters.

    Validates: Requirements 65.1, 65.3
    """

    def test_generate_qr_code_returns_png_bytes(self) -> None:
        """generate_qr_code returns PNG bytes."""
        svc = MarketingService()
        request = QRCodeRequest(
            target_url="https://example.com",
            campaign_name="summer2024",
        )

        result = svc.generate_qr_code(request)

        # PNG magic bytes: \x89PNG
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:4] == b"\x89PNG"

    def test_generate_qr_code_url_contains_utm_params(self) -> None:
        """generate_qr_code URL contains utm_source, utm_campaign, utm_medium."""
        url = MarketingService._build_utm_url(
            "https://example.com/landing",
            "summer2024",
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["utm_source"] == ["qr_code"]
        assert params["utm_campaign"] == ["summer2024"]
        assert params["utm_medium"] == ["print"]

    def test_build_utm_url_preserves_existing_query_parameters(self) -> None:
        """_build_utm_url preserves existing query parameters."""
        url = MarketingService._build_utm_url(
            "https://example.com/page?ref=homepage&lang=en",
            "fall_promo",
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert params["ref"] == ["homepage"]
        assert params["lang"] == ["en"]
        assert params["utm_source"] == ["qr_code"]
        assert params["utm_campaign"] == ["fall_promo"]
        assert params["utm_medium"] == ["print"]

    def test_build_utm_url_with_no_existing_params_adds_utm_correctly(
        self,
    ) -> None:
        """_build_utm_url with no existing params adds UTM correctly."""
        url = MarketingService._build_utm_url(
            "https://example.com",
            "winter_sale",
        )

        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        assert len(params) == 3
        assert params["utm_source"] == ["qr_code"]
        assert params["utm_campaign"] == ["winter_sale"]
        assert params["utm_medium"] == ["print"]
        assert parsed.scheme == "https"
        assert parsed.netloc == "example.com"


# =============================================================================
# MediaService unit tests
# Validates: Requirements 49.6
# =============================================================================


@pytest.mark.unit
class TestMediaServiceCRUD:
    """MediaService CRUD and validation tests.

    Validates: Requirements 49.6
    """

    @pytest.mark.asyncio
    async def test_create_with_valid_data_returns_media_response(
        self,
    ) -> None:
        """create with valid data returns MediaResponse."""
        repo = AsyncMock()
        mock_item = _make_media_item_mock()
        repo.create.return_value = mock_item
        svc = MediaService(media_repository=repo)

        data = MediaCreate(
            file_key="media/photo.jpg",
            file_name="photo.jpg",
            file_size=2048,
            content_type="image/jpeg",
            media_type=MediaType.IMAGE,
            category="photos",
        )

        result = await svc.create(data)

        assert result.file_name == mock_item.file_name
        repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_oversized_file_raises_media_validation_error(
        self,
    ) -> None:
        """create with oversized file raises MediaValidationError."""
        repo = AsyncMock()
        svc = MediaService(media_repository=repo)

        data = MediaCreate(
            file_key="media/huge.jpg",
            file_name="huge.jpg",
            file_size=MAX_FILE_SIZE_BYTES + 1,
            content_type="image/jpeg",
            media_type=MediaType.IMAGE,
        )

        with pytest.raises(MediaValidationError, match="exceeds maximum"):
            await svc.create(data)

        repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_with_invalid_content_type_raises_media_validation_error(
        self,
    ) -> None:
        """create with invalid content type raises MediaValidationError."""
        repo = AsyncMock()
        svc = MediaService(media_repository=repo)

        data = MediaCreate(
            file_key="media/file.exe",
            file_name="file.exe",
            file_size=1024,
            content_type="application/x-executable",
            media_type=MediaType.IMAGE,
        )

        with pytest.raises(MediaValidationError, match="not allowed"):
            await svc.create(data)

        repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_with_existing_item_returns_media_response(
        self,
    ) -> None:
        """get_by_id with existing item returns MediaResponse."""
        mock_item = _make_media_item_mock()
        repo = AsyncMock()
        repo.get_by_id.return_value = mock_item
        svc = MediaService(media_repository=repo)

        result = await svc.get_by_id(mock_item.id)

        assert result.id == mock_item.id
        assert result.file_name == mock_item.file_name

    @pytest.mark.asyncio
    async def test_get_by_id_with_missing_item_raises_media_not_found_error(
        self,
    ) -> None:
        """get_by_id with missing item raises MediaNotFoundError."""
        repo = AsyncMock()
        repo.get_by_id.return_value = None
        svc = MediaService(media_repository=repo)

        with pytest.raises(MediaNotFoundError):
            await svc.get_by_id(uuid4())

    @pytest.mark.asyncio
    async def test_delete_with_existing_item_returns_true(self) -> None:
        """delete with existing item returns True."""
        repo = AsyncMock()
        repo.delete.return_value = True
        svc = MediaService(media_repository=repo)

        result = await svc.delete(uuid4())

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_with_missing_item_raises_media_not_found_error(
        self,
    ) -> None:
        """delete with missing item raises MediaNotFoundError."""
        repo = AsyncMock()
        repo.delete.return_value = False
        svc = MediaService(media_repository=repo)

        with pytest.raises(MediaNotFoundError):
            await svc.delete(uuid4())

    @pytest.mark.asyncio
    async def test_list_items_returns_paginated_results(self) -> None:
        """list_items returns paginated results."""
        items = [_make_media_item_mock() for _ in range(3)]
        repo = AsyncMock()
        repo.list_with_filters.return_value = (items, 10)
        svc = MediaService(media_repository=repo)

        results, total = await svc.list_items(page=1, page_size=3)

        assert len(results) == 3
        assert total == 10
        repo.list_with_filters.assert_called_once_with(
            page=1,
            page_size=3,
            media_type=None,
            category=None,
            is_public=None,
        )

    def test_validate_media_accepts_valid_image_types(self) -> None:
        """_validate_media accepts valid image types."""
        svc = MediaService(media_repository=AsyncMock())

        for ct in ALLOWED_CONTENT_TYPES[MediaType.IMAGE]:
            data = MediaCreate(
                file_key=f"media/file.{ct.split('/')[-1]}",
                file_name=f"file.{ct.split('/')[-1]}",
                file_size=1024,
                content_type=ct,
                media_type=MediaType.IMAGE,
            )
            # Should not raise
            svc._validate_media(data)

    def test_validate_media_rejects_video_content_type_for_image_media_type(
        self,
    ) -> None:
        """_validate_media rejects video content type for image media type."""
        svc = MediaService(media_repository=AsyncMock())

        data = MediaCreate(
            file_key="media/video.mp4",
            file_name="video.mp4",
            file_size=1024,
            content_type="video/mp4",
            media_type=MediaType.IMAGE,
        )

        with pytest.raises(MediaValidationError, match="not allowed"):
            svc._validate_media(data)
