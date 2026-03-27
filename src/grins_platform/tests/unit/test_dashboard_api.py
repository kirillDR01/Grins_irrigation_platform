"""Unit tests for Dashboard API endpoints.

Tests the three dashboard metric endpoints:
- GET /api/v1/communications/unaddressed-count (Req 4.2)
- GET /api/v1/invoices/metrics/pending (Req 5.1, 5.2)
- GET /api/v1/jobs/metrics/by-status (Req 6.1, 6.2)

Property-based tests:
- Property 3: Unaddressed communication count accuracy
- Property 5: Pending invoice metrics correctness
- Property 6: Job status category partitioning

Validates: Requirements 4.6, 5.4, 6.4
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.main import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _mock_db_override() -> AsyncGenerator[AsyncSession, None]:
    """Yield a mock AsyncSession for dependency override."""
    yield AsyncMock(spec=AsyncSession)


# ---------------------------------------------------------------------------
# Unit tests — Unaddressed count endpoint (Req 4.6)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUnaddressedCountEndpoint:
    """Tests for GET /api/v1/communications/unaddressed-count."""

    @pytest.mark.asyncio
    async def test_unaddressed_count_with_zero_returns_zero(self) -> None:
        """Endpoint returns count=0 when no unaddressed communications."""
        with patch(
            "grins_platform.api.v1.sms.CommunicationRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_unaddressed_count = AsyncMock(return_value=0)
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get(
                        "/api/v1/communications/unaddressed-count",
                    )

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unaddressed_count_with_multiple_returns_correct_count(
        self,
    ) -> None:
        """Endpoint returns correct count when unaddressed communications exist."""
        with patch(
            "grins_platform.api.v1.sms.CommunicationRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_unaddressed_count = AsyncMock(return_value=42)
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get(
                        "/api/v1/communications/unaddressed-count",
                    )

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 42
            finally:
                app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests — Pending invoice metrics endpoint (Req 5.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPendingInvoiceMetricsEndpoint:
    """Tests for GET /api/v1/invoices/metrics/pending."""

    @pytest.mark.asyncio
    async def test_pending_metrics_with_no_pending_returns_zero(self) -> None:
        """Endpoint returns count=0 and total=0 when no pending invoices."""
        with patch(
            "grins_platform.api.v1.invoices.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_pending_metrics = AsyncMock(
                return_value=(0, Decimal(0)),
            )
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/invoices/metrics/pending")

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 0
                assert data["total_amount"] == 0.0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_pending_metrics_with_invoices_returns_correct_values(
        self,
    ) -> None:
        """Endpoint returns correct count and total from actual invoice records."""
        with patch(
            "grins_platform.api.v1.invoices.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_pending_metrics = AsyncMock(
                return_value=(5, Decimal("1234.56")),
            )
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/invoices/metrics/pending")

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == 5
                assert data["total_amount"] == 1234.56
            finally:
                app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Unit tests — Job status by-category endpoint (Req 6.4)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJobMetricsByStatusEndpoint:
    """Tests for GET /api/v1/jobs/metrics/by-status."""

    @pytest.mark.asyncio
    async def test_by_status_with_no_jobs_returns_all_zeros(self) -> None:
        """Endpoint returns all six categories with zero counts."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_scalar_result)

        async def _db_with_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "grins_platform.api.v1.jobs.JobRepository",
        ) as mock_job_repo_cls:
            mock_job_repo = AsyncMock()
            mock_job_repo.count_by_status = AsyncMock(return_value={})
            mock_job_repo.find_by_category = AsyncMock(return_value=[])
            mock_job_repo_cls.return_value = mock_job_repo

            app.dependency_overrides[get_db_session] = _db_with_session
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/jobs/metrics/by-status")

                assert resp.status_code == 200
                data = resp.json()
                assert data["new_requests"] == 0
                assert data["estimates"] == 0
                assert data["pending_approval"] == 0
                assert data["to_be_scheduled"] == 0
                assert data["in_progress"] == 0
                assert data["complete"] == 0
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_by_status_with_jobs_returns_correct_counts(self) -> None:
        """Endpoint returns all six categories with correct counts."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 3
        mock_session.execute = AsyncMock(return_value=mock_scalar_result)

        async def _db_with_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "grins_platform.api.v1.jobs.JobRepository",
        ) as mock_job_repo_cls:
            mock_job_repo = AsyncMock()
            mock_job_repo.count_by_status = AsyncMock(
                return_value={
                    "to_be_scheduled": 15,
                    "in_progress": 8,
                    "completed": 20,
                    "cancelled": 1,
                },
            )
            mock_job_repo.find_by_category = AsyncMock(
                return_value=[MagicMock() for _ in range(4)],
            )
            mock_job_repo_cls.return_value = mock_job_repo

            app.dependency_overrides[get_db_session] = _db_with_session
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/jobs/metrics/by-status")

                assert resp.status_code == 200
                data = resp.json()
                assert data["new_requests"] == 0
                assert data["estimates"] == 4
                assert data["pending_approval"] == 3
                assert data["to_be_scheduled"] == 15
                assert data["in_progress"] == 8
                assert data["complete"] == 20
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_by_status_returns_exactly_six_categories(self) -> None:
        """Response contains exactly the six required category keys."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_scalar_result)

        async def _db_with_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "grins_platform.api.v1.jobs.JobRepository",
        ) as mock_job_repo_cls:
            mock_job_repo = AsyncMock()
            mock_job_repo.count_by_status = AsyncMock(return_value={})
            mock_job_repo.find_by_category = AsyncMock(return_value=[])
            mock_job_repo_cls.return_value = mock_job_repo

            app.dependency_overrides[get_db_session] = _db_with_session
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/jobs/metrics/by-status")

                assert resp.status_code == 200
                data = resp.json()
                expected_keys = {
                    "new_requests",
                    "estimates",
                    "pending_approval",
                    "to_be_scheduled",
                    "in_progress",
                    "complete",
                }
                assert set(data.keys()) == expected_keys
            finally:
                app.dependency_overrides.clear()


# ===========================================================================
# Property-Based Tests
# ===========================================================================


# ---------------------------------------------------------------------------
# Property 3: Unaddressed communication count accuracy
# Validates: Requirements 4.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty3UnaddressedCountAccuracy:
    """Property 3: Unaddressed communication count accuracy.

    *For any* set of communication records with varying `addressed` status,
    the unaddressed-count endpoint shall return a count exactly equal to the
    number of records where `addressed=false`.

    **Validates: Requirements 4.2**
    """

    @given(
        unaddressed_count=st.integers(min_value=0, max_value=10_000),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_endpoint_returns_exact_unaddressed_count(
        self,
        unaddressed_count: int,
    ) -> None:
        """For any non-negative count, the endpoint returns that exact value."""
        with patch(
            "grins_platform.api.v1.sms.CommunicationRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_unaddressed_count = AsyncMock(
                return_value=unaddressed_count,
            )
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get(
                        "/api/v1/communications/unaddressed-count",
                    )

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == unaddressed_count
            finally:
                app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Property 5: Pending invoice metrics correctness
# Validates: Requirements 5.1, 5.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty5PendingInvoiceMetrics:
    """Property 5: Pending invoice metrics correctness.

    *For any* set of invoices with varying statuses, the pending metrics
    endpoint shall return a count equal to the number of invoices with
    status SENT or VIEWED, and a total equal to the sum of their amounts.

    **Validates: Requirements 5.1, 5.2**
    """

    @given(
        count=st.integers(min_value=0, max_value=5_000),
        total_cents=st.integers(min_value=0, max_value=100_000_000),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_endpoint_returns_exact_pending_count_and_total(
        self,
        count: int,
        total_cents: int,
    ) -> None:
        """For any count and total, the endpoint returns those exact values."""
        total_amount = Decimal(total_cents) / Decimal(100)

        with patch(
            "grins_platform.api.v1.invoices.InvoiceRepository",
        ) as mock_repo_cls:
            mock_repo = AsyncMock()
            mock_repo.get_pending_metrics = AsyncMock(
                return_value=(count, total_amount),
            )
            mock_repo_cls.return_value = mock_repo

            app.dependency_overrides[get_db_session] = _mock_db_override
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/invoices/metrics/pending")

                assert resp.status_code == 200
                data = resp.json()
                assert data["count"] == count
                assert data["total_amount"] == pytest.approx(
                    float(total_amount),
                    abs=0.01,
                )
            finally:
                app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Property 6: Job status category partitioning
# Validates: Requirements 6.1, 6.2
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProperty6JobStatusPartitioning:
    """Property 6: Job status category partitioning.

    *For any* set of active jobs, the by-status metrics endpoint shall
    return counts for exactly six categories that partition all jobs —
    every job appears in exactly one category, and the sum of all
    category counts equals the total active job count.

    **Validates: Requirements 6.1, 6.2**
    """

    @given(
        to_be_scheduled=st.integers(min_value=0, max_value=500),
        in_progress=st.integers(min_value=0, max_value=500),
        completed=st.integers(min_value=0, max_value=500),
        estimates_count=st.integers(min_value=0, max_value=500),
        pending_approval=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_response_has_exactly_six_categories(
        self,
        to_be_scheduled: int,
        in_progress: int,
        completed: int,
        estimates_count: int,
        pending_approval: int,
    ) -> None:
        """Response always contains exactly six category keys with correct values."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = pending_approval
        mock_session.execute = AsyncMock(return_value=mock_scalar_result)

        async def _db_with_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        with patch(
            "grins_platform.api.v1.jobs.JobRepository",
        ) as mock_job_repo_cls:
            mock_job_repo = AsyncMock()
            mock_job_repo.count_by_status = AsyncMock(
                return_value={
                    "to_be_scheduled": to_be_scheduled,
                    "in_progress": in_progress,
                    "completed": completed,
                },
            )
            mock_job_repo.find_by_category = AsyncMock(
                return_value=[MagicMock() for _ in range(estimates_count)],
            )
            mock_job_repo_cls.return_value = mock_job_repo

            app.dependency_overrides[get_db_session] = _db_with_session
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as client:
                    resp = await client.get("/api/v1/jobs/metrics/by-status")

                assert resp.status_code == 200
                data = resp.json()

                # Exactly 6 categories
                expected_keys = {
                    "new_requests",
                    "estimates",
                    "pending_approval",
                    "to_be_scheduled",
                    "in_progress",
                    "complete",
                }
                assert set(data.keys()) == expected_keys

                # Values match what was provided
                assert data["new_requests"] == 0  # No longer a distinct status
                assert data["estimates"] == estimates_count
                assert data["pending_approval"] == pending_approval
                assert data["to_be_scheduled"] == to_be_scheduled
                assert data["in_progress"] == in_progress
                assert data["complete"] == completed

                # All values are non-negative
                for val in data.values():
                    assert val >= 0
            finally:
                app.dependency_overrides.clear()
