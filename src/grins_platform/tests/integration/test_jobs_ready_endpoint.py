"""Tests for jobs ready to schedule endpoint."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from grins_platform.database import DatabaseSettings
from grins_platform.models.customer import Customer
from grins_platform.models.customer_tag import CustomerTag
from grins_platform.models.job import Job
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.service_agreement_tier import ServiceAgreementTier

if TYPE_CHECKING:
    from collections.abc import Iterator

    from httpx import AsyncClient
    from sqlalchemy.orm import Session


def _sync_session_factory() -> tuple[sessionmaker, object]:
    """Build the same sync engine the ``get_sync_db`` dependency uses."""
    settings = DatabaseSettings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )
    engine = create_engine(sync_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False), engine


@pytest.fixture
def sync_session() -> Iterator[Session]:
    """Yield a sync SQLAlchemy session bound to the test Postgres."""
    factory, engine = _sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()  # type: ignore[attr-defined]


@pytest.mark.integration
class TestJobsReadyToScheduleEndpoint:
    """Test GET /api/v1/schedule/jobs-ready endpoint."""

    @pytest.mark.asyncio
    async def test_get_jobs_ready_endpoint_exists(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that endpoint exists and returns valid response."""
        # Call endpoint
        response = await client.get("/api/v1/schedule/jobs-ready")

        # Verify response structure
        assert response.status_code == 200
        data = response.json()

        # Verify response has required fields
        assert "jobs" in data
        assert "total_count" in data
        assert "by_city" in data
        assert "by_job_type" in data

        # Verify types
        assert isinstance(data["jobs"], list)
        assert isinstance(data["total_count"], int)
        assert isinstance(data["by_city"], dict)
        assert isinstance(data["by_job_type"], dict)

    @pytest.mark.asyncio
    async def test_get_jobs_ready_accepts_date_filters(
        self,
        client: AsyncClient,
    ) -> None:
        """Test that endpoint accepts date filter parameters."""
        # Call endpoint with date filters
        response = await client.get(
            "/api/v1/schedule/jobs-ready",
            params={
                "date_from": "2025-01-01",
                "date_to": "2025-12-31",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "jobs" in data
        assert "total_count" in data

    @pytest.mark.asyncio
    async def test_jobs_ready_returns_extended_fields(
        self,
        client: AsyncClient,
        sync_session: Session,
    ) -> None:
        """Pick-Jobs requires extended fields populated server-side.

        Seeds a customer with a ``priority`` tag and an active service
        agreement, plus an unscheduled approved job whose target_start_date
        is set. Asserts the response surfaces the new contract fields:
        ``priority_level`` / ``effective_priority_level`` / ``requested_week``
        / ``customer_tags`` / ``has_active_agreement``.
        """
        unique = uuid.uuid4().hex[:8]

        customer = Customer(
            first_name="Pick",
            last_name=f"Jobs-{unique}",
            phone=f"+1612{unique[:7].zfill(7)}",
        )
        sync_session.add(customer)
        sync_session.flush()
        customer_id = customer.id

        sync_session.add(
            CustomerTag(
                customer_id=customer_id,
                label="priority",
                tone="amber",
                source="manual",
            ),
        )

        # Locate any tier — the schema requires a non-null ``tier_id`` and
        # the seed data already provisions tiers in dev/test environments.
        tier = sync_session.query(ServiceAgreementTier).first()
        assert tier is not None, (
            "ServiceAgreementTier seed missing — required for the FK"
        )

        agreement = ServiceAgreement(
            agreement_number=f"TEST-{unique}",
            customer_id=customer_id,
            tier_id=tier.id,
            status="active",
            annual_price=Decimal("100.00"),
        )
        sync_session.add(agreement)

        job = Job(
            customer_id=customer_id,
            job_type="spring_startup",
            category="ready_to_schedule",
            status="to_be_scheduled",
            target_start_date=date(2026, 4, 27),
            priority_level=0,
            estimated_duration_minutes=60,
        )
        sync_session.add(job)
        sync_session.commit()
        job_id = job.id

        try:
            response = await client.get("/api/v1/schedule/jobs-ready")
            assert response.status_code == 200
            data = response.json()

            row = next(
                (j for j in data["jobs"] if j["job_id"] == str(job_id)),
                None,
            )
            assert row is not None, "seeded job missing from response"

            # Contract: keys exist
            for key in (
                "priority_level",
                "effective_priority_level",
                "requested_week",
                "customer_tags",
                "has_active_agreement",
                "address",
                "notes",
            ):
                assert key in row, f"missing key {key!r}"

            assert row["priority_level"] == 0
            assert row["effective_priority_level"] >= 1, (
                "priority should escalate from 0 → 1+ given tag/agreement"
            )
            assert row["requested_week"] == "2026-04-27"
            assert "priority" in row["customer_tags"]
            assert row["has_active_agreement"] is True
        finally:
            # Tidy up seeded rows so reruns don't accumulate state.
            sync_session.execute(delete(Job).where(Job.id == job_id))
            sync_session.execute(
                delete(ServiceAgreement).where(
                    ServiceAgreement.id == cast("uuid.UUID", agreement.id),
                ),
            )
            sync_session.execute(
                delete(CustomerTag).where(
                    CustomerTag.customer_id == customer_id,
                ),
            )
            sync_session.execute(
                delete(Customer).where(Customer.id == customer_id),
            )
            sync_session.commit()
