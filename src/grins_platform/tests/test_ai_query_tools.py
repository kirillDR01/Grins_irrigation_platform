"""Tests for AI query tools.

Validates: AI Assistant Requirements 8.2-8.8
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from grins_platform.services.ai.tools.queries import QueryTools


@pytest.mark.asyncio
class TestQueryTools:
    """Test suite for QueryTools."""

    @pytest.fixture
    def query_tools(self) -> QueryTools:
        """Create QueryTools instance with mock session."""
        mock_session = AsyncMock()
        return QueryTools(mock_session)

    async def test_query_customers_no_filters(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying customers without filters."""
        result = await query_tools.query_customers()

        assert "customers" in result
        assert "total" in result
        assert "filters_applied" in result
        assert isinstance(result["customers"], list)
        assert result["filters_applied"] == {}

    async def test_query_customers_with_filters(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying customers with filters."""
        filters = {"city": "Eden Prairie", "status": "active"}
        result = await query_tools.query_customers(filters=filters, limit=10)

        assert result["filters_applied"] == filters
        assert isinstance(result["customers"], list)

    async def test_query_customers_respects_limit(
        self, query_tools: QueryTools,
    ) -> None:
        """Test that query respects limit parameter."""
        result = await query_tools.query_customers(limit=5)

        assert "total" in result
        # Placeholder returns empty list, but structure is correct
        assert len(result["customers"]) <= 5

    async def test_query_jobs_no_filters(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying jobs without filters."""
        result = await query_tools.query_jobs()

        assert "jobs" in result
        assert "total" in result
        assert "filters_applied" in result
        assert "date_range" in result
        assert isinstance(result["jobs"], list)

    async def test_query_jobs_with_date_range(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying jobs with date range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)
        date_range = (start_date, end_date)

        result = await query_tools.query_jobs(date_range=date_range)

        assert result["date_range"]["start"] == "2024-01-01"
        assert result["date_range"]["end"] == "2024-01-31"

    async def test_query_jobs_with_filters(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying jobs with filters."""
        filters = {"status": "scheduled", "type": "startup"}
        result = await query_tools.query_jobs(filters=filters)

        assert result["filters_applied"] == filters

    async def test_query_revenue_default_date_range(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying revenue with default date range (last 30 days)."""
        result = await query_tools.query_revenue()

        assert "total_revenue" in result
        assert "date_range" in result
        assert "group_by" in result
        assert "breakdown" in result
        assert result["group_by"] == "day"

        # Verify default date range is last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        assert result["date_range"]["start"] == start_date.isoformat()
        assert result["date_range"]["end"] == end_date.isoformat()

    async def test_query_revenue_custom_date_range(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying revenue with custom date range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)
        date_range = (start_date, end_date)

        result = await query_tools.query_revenue(date_range=date_range)

        assert result["date_range"]["start"] == "2024-01-01"
        assert result["date_range"]["end"] == "2024-03-31"

    async def test_query_revenue_group_by_week(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying revenue grouped by week."""
        result = await query_tools.query_revenue(group_by="week")

        assert result["group_by"] == "week"

    async def test_query_revenue_group_by_month(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying revenue grouped by month."""
        result = await query_tools.query_revenue(group_by="month")

        assert result["group_by"] == "month"

    async def test_query_staff_without_availability(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying staff without availability."""
        result = await query_tools.query_staff()

        assert "staff" in result
        assert "total" in result
        assert "include_availability" in result
        assert result["include_availability"] is False

    async def test_query_staff_with_availability(
        self, query_tools: QueryTools,
    ) -> None:
        """Test querying staff with availability."""
        result = await query_tools.query_staff(include_availability=True)

        assert result["include_availability"] is True

    async def test_query_tools_logging(
        self, query_tools: QueryTools, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that query tools log operations."""
        await query_tools.query_customers()

        # Check for log entries
        assert any("query_customers" in record.message for record in caplog.records)

    async def test_query_customers_empty_result_structure(
        self, query_tools: QueryTools,
    ) -> None:
        """Test that empty results have correct structure."""
        result = await query_tools.query_customers()

        assert isinstance(result["customers"], list)
        assert result["total"] == 0
        assert isinstance(result["filters_applied"], dict)

    async def test_query_jobs_empty_result_structure(
        self, query_tools: QueryTools,
    ) -> None:
        """Test that empty job results have correct structure."""
        result = await query_tools.query_jobs()

        assert isinstance(result["jobs"], list)
        assert result["total"] == 0
        assert result["date_range"]["start"] is None
        assert result["date_range"]["end"] is None

    async def test_query_revenue_structure(
        self, query_tools: QueryTools,
    ) -> None:
        """Test revenue query result structure."""
        result = await query_tools.query_revenue()

        assert isinstance(result["total_revenue"], float)
        assert result["total_revenue"] == 0.0
        assert isinstance(result["breakdown"], list)

    async def test_query_staff_empty_result_structure(
        self, query_tools: QueryTools,
    ) -> None:
        """Test that empty staff results have correct structure."""
        result = await query_tools.query_staff()

        assert isinstance(result["staff"], list)
        assert result["total"] == 0
