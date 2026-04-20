"""Postgres-level test for the partial unique index on reschedule_requests.

Safeguards the gap-01 migration ``20260421_100000_reschedule_request_
unique_open_index``: at most one ``status='open'`` row per appointment,
while resolved / cancelled / superseded rows are free to coexist.

Requires a live Postgres DB (the ``WHERE status='open'`` clause is
Postgres-specific). Skipped if the connection fails.

Validates: gap-01 (1.A DB safety net).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from grins_platform.database import DatabaseSettings

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def sync_engine() -> Engine:
    settings = DatabaseSettings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        engine = create_engine(sync_url, pool_pre_ping=True)
        # Actually connect — if Postgres is down, we skip.
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"Postgres not available for migration test: {exc}")
    return engine


@pytest.fixture
def sync_session(sync_engine: Engine) -> Generator[Session, None, None]:
    session_factory = sessionmaker(bind=sync_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.mark.integration
def test_reschedule_unique_open_index_exists(sync_engine: Engine) -> None:
    """The partial unique index must be present after ``alembic upgrade head``."""
    inspector = inspect(sync_engine)
    indexes = inspector.get_indexes("reschedule_requests")
    names = {idx["name"] for idx in indexes}
    assert "uq_reschedule_requests_open_per_appointment" in names, (
        "Partial unique index missing — was the migration applied?"
    )


@pytest.mark.integration
def test_reschedule_unique_open_index_rejects_duplicate_open_rows(
    sync_session: Session,
) -> None:
    """Two ``status='open'`` rows for the same appointment must collide.

    Sets up ad-hoc customer/job/appointment rows so the FK targets
    exist, inserts one open RescheduleRequest, then expects
    :class:`IntegrityError` on the second insert with the same
    appointment_id + status='open'.
    """
    customer_id = uuid4()
    job_id = uuid4()
    appointment_id = uuid4()
    now = datetime.now(tz=timezone.utc)

    try:
        sync_session.execute(
            text(
                "INSERT INTO customers (id, first_name, last_name, "
                "phone, address, created_at, updated_at, status) "
                "VALUES (:id, 'Test', 'Customer', '5551234567', "
                "'123 Main', :now, :now, 'active')",
            ),
            {"id": customer_id, "now": now},
        )
        sync_session.execute(
            text(
                "INSERT INTO jobs (id, customer_id, job_type, status, "
                "created_at, updated_at) VALUES (:id, :cust, "
                "'spring_startup', 'to_be_scheduled', :now, :now)",
            ),
            {"id": job_id, "cust": customer_id, "now": now},
        )
        sync_session.execute(
            text(
                "INSERT INTO appointments (id, job_id, scheduled_date, "
                "time_window_start, time_window_end, status, created_at, "
                "updated_at) VALUES (:id, :job, CURRENT_DATE, "
                "'09:00', '11:00', 'scheduled', :now, :now)",
            ),
            {"id": appointment_id, "job": job_id, "now": now},
        )
        sync_session.commit()

        # Seed first open row — must succeed.
        sync_session.execute(
            text(
                "INSERT INTO reschedule_requests "
                "(id, job_id, appointment_id, customer_id, status, "
                "created_at) VALUES "
                "(:id, :job, :appt, :cust, 'open', :now)",
            ),
            {
                "id": uuid4(),
                "job": job_id,
                "appt": appointment_id,
                "cust": customer_id,
                "now": now,
            },
        )
        sync_session.commit()

        # Second open row with same appointment_id — must collide.
        with pytest.raises(IntegrityError):
            sync_session.execute(
                text(
                    "INSERT INTO reschedule_requests "
                    "(id, job_id, appointment_id, customer_id, status, "
                    "created_at) VALUES "
                    "(:id, :job, :appt, :cust, 'open', :now)",
                ),
                {
                    "id": uuid4(),
                    "job": job_id,
                    "appt": appointment_id,
                    "cust": customer_id,
                    "now": now,
                },
            )
            sync_session.commit()
        sync_session.rollback()

        # Resolving the first row frees the slot — a new open row is allowed.
        sync_session.execute(
            text(
                "UPDATE reschedule_requests SET status = 'resolved', "
                "resolved_at = :now WHERE appointment_id = :appt",
            ),
            {"now": now, "appt": appointment_id},
        )
        sync_session.commit()

        sync_session.execute(
            text(
                "INSERT INTO reschedule_requests "
                "(id, job_id, appointment_id, customer_id, status, "
                "created_at) VALUES "
                "(:id, :job, :appt, :cust, 'open', :now)",
            ),
            {
                "id": uuid4(),
                "job": job_id,
                "appt": appointment_id,
                "cust": customer_id,
                "now": now,
            },
        )
        sync_session.commit()
    finally:
        # Cleanup — rollback any pending + delete seed data.
        sync_session.rollback()
        sync_session.execute(
            text("DELETE FROM reschedule_requests WHERE appointment_id = :id"),
            {"id": appointment_id},
        )
        sync_session.execute(
            text("DELETE FROM appointments WHERE id = :id"),
            {"id": appointment_id},
        )
        sync_session.execute(
            text("DELETE FROM jobs WHERE id = :id"),
            {"id": job_id},
        )
        sync_session.execute(
            text("DELETE FROM customers WHERE id = :id"),
            {"id": customer_id},
        )
        sync_session.commit()
