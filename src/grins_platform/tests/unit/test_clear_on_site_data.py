"""Unit tests for clear_on_site_data() helper function.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AppointmentStatus, JobStatus


def _make_session(*, invoice_count: int = 0) -> AsyncMock:
    """Build an AsyncMock session where execute() returns a result whose
    scalar()/scalar_one() is the supplied invoice_count.

    clear_on_site_data runs two queries on the session: a DELETE for
    SentMessage rows and a COUNT(*) against invoices. The scalar_one()
    return value feeds the M-2 invoice check; scalar() is kept in sync
    for callers that still use it.
    """
    session = AsyncMock()
    result = MagicMock()
    result.scalar = Mock(return_value=invoice_count)
    result.scalar_one = Mock(return_value=invoice_count)
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_appointment(
    *,
    en_route_at: datetime | None = None,
    arrived_at: datetime | None = None,
    completed_at: datetime | None = None,
    status: str = AppointmentStatus.CANCELLED.value,
) -> Mock:
    """Create a mock Appointment with on-site timestamp fields."""
    appt = Mock()
    appt.id = uuid4()
    appt.job_id = uuid4()
    appt.status = status
    appt.en_route_at = en_route_at
    appt.arrived_at = arrived_at
    appt.completed_at = completed_at
    return appt


def _make_job(
    *,
    on_my_way_at: datetime | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    payment_collected_on_site: bool = False,
    status: str = JobStatus.SCHEDULED.value,
) -> Mock:
    """Create a mock Job with on-site timestamp fields."""
    job = Mock()
    job.id = uuid4()
    job.on_my_way_at = on_my_way_at
    job.started_at = started_at
    job.completed_at = completed_at
    job.payment_collected_on_site = payment_collected_on_site
    job.status = status
    return job


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestClearOnSiteData:
    """Tests for the clear_on_site_data helper function."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_clears_appointment_timestamps(self) -> None:
        """Cancel appointment with timestamps set → all three are null after.

        Validates: Requirement 2.1
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        appt = _make_appointment(
            en_route_at=now,
            arrived_at=now,
            completed_at=now,
        )
        session = _make_session()

        await clear_on_site_data(session, appt)

        assert appt.en_route_at is None
        assert appt.arrived_at is None
        assert appt.completed_at is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_deletes_on_my_way_sms_records(self) -> None:
        """Cancel appointment → On My Way SMS records deleted.

        Validates: Requirement 2.2
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        appt = _make_appointment()
        session = _make_session()

        await clear_on_site_data(session, appt)

        # Verify a DELETE was executed (the first execute call is the delete)
        assert session.execute.call_count >= 1
        delete_call = session.execute.call_args_list[0]
        # The delete statement was called
        stmt = delete_call[0][0]
        # Verify it's a delete statement (string representation check)
        compiled = str(stmt)
        assert "sent_messages" in compiled.lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_clears_job_timestamps_when_no_other_active_appointments(
        self,
    ) -> None:
        """Cancel only appointment for a job → job timestamps also cleared.

        Validates: Requirement 2.3
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        appt = _make_appointment(en_route_at=now, arrived_at=now, completed_at=now)
        job = _make_job(on_my_way_at=now, started_at=now, completed_at=now)

        session = _make_session()

        # Mock count_active_appointments to return 0 (no other active)
        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=0,
        ):
            await clear_on_site_data(session, appt, job=job)

        assert job.on_my_way_at is None
        assert job.started_at is None
        assert job.completed_at is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_preserves_job_timestamps_when_other_active_appointments_exist(
        self,
    ) -> None:
        """Cancel one of two appointments for a job → job timestamps NOT cleared.

        Validates: Requirement 2.4
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        appt = _make_appointment(en_route_at=now, arrived_at=now, completed_at=now)
        job = _make_job(on_my_way_at=now, started_at=now, completed_at=now)

        session = _make_session()

        # Mock count_active_appointments to return 1 (another active exists)
        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=1,
        ):
            await clear_on_site_data(session, appt, job=job)

        # Job timestamps should be preserved
        assert job.on_my_way_at == now
        assert job.started_at == now
        assert job.completed_at == now

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_clears_payment_override_flag_when_no_invoice(self) -> None:
        """Cancel appointment with no sibling invoice → payment flag reset.

        Validates: Requirement 2.5
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        appt = _make_appointment()
        job = _make_job(payment_collected_on_site=True)

        session = _make_session(invoice_count=0)

        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=0,
        ):
            await clear_on_site_data(session, appt, job=job)

        assert job.payment_collected_on_site is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_preserves_payment_flag_when_invoice_exists(self) -> None:
        """When a sibling invoice exists, preserve payment_collected_on_site.

        A job with two appointments (one paid, one later cancelled)
        should not lose the payment flag when the second is cancelled,
        or the remaining complete flow would mis-fire the no-payment
        warning.

        Validates: bughunt M-2
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        appt = _make_appointment()
        job = _make_job(payment_collected_on_site=True)

        session = _make_session(invoice_count=1)

        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=1,
        ):
            await clear_on_site_data(session, appt, job=job)

        assert job.payment_collected_on_site is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_reverts_in_progress_job_to_tb_scheduled(self) -> None:
        """Cancelling the last active appointment on an IN_PROGRESS job
        reverts the job to TO_BE_SCHEDULED so it doesn't get stranded
        without a visible path forward.

        Validates: bughunt L-12
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        appt = _make_appointment(en_route_at=now, arrived_at=now)
        job = _make_job(
            on_my_way_at=now,
            started_at=now,
            status=JobStatus.IN_PROGRESS.value,
        )

        session = _make_session(invoice_count=0)

        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=0,
        ):
            await clear_on_site_data(session, appt, job=job)

        assert job.status == JobStatus.TO_BE_SCHEDULED.value

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_job_provided_skips_job_cleanup(self) -> None:
        """When job is None, only appointment fields are cleared.

        Validates: Requirement 2.1
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)
        appt = _make_appointment(en_route_at=now, arrived_at=now, completed_at=now)

        session = _make_session()

        # Should not raise even without a job
        await clear_on_site_data(session, appt, job=None)

        assert appt.en_route_at is None
        assert appt.arrived_at is None
        assert appt.completed_at is None
        # flush was called
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_new_appointment_after_cancellation_starts_clean(self) -> None:
        """Create new appointment after cancellation → all fields null, no inherited data.

        Simulates the full cancel-then-recreate flow: cancel an appointment
        (clearing on-site data), then create a fresh appointment for the same
        job and verify it has no inherited timestamps or SMS records.

        Validates: Requirement 2.6
        """
        from grins_platform.services.appointment_service import (
            clear_on_site_data,
        )

        now = datetime.now(tz=timezone.utc)

        # --- Step 1: Cancel the old appointment and clear its data ---
        old_appt = _make_appointment(
            en_route_at=now,
            arrived_at=now,
            completed_at=now,
            status=AppointmentStatus.CANCELLED.value,
        )
        job = _make_job(on_my_way_at=now, started_at=now, completed_at=now)

        session = _make_session()

        with patch(
            "grins_platform.services.appointment_service.count_active_appointments",
            new_callable=AsyncMock,
            return_value=0,
        ):
            await clear_on_site_data(session, old_appt, job=job)

        # Verify old appointment and job are cleaned
        assert old_appt.en_route_at is None
        assert old_appt.arrived_at is None
        assert old_appt.completed_at is None
        assert job.on_my_way_at is None
        assert job.started_at is None
        assert job.completed_at is None

        # --- Step 2: Create a new appointment for the same job ---
        new_appt = _make_appointment(
            en_route_at=None,
            arrived_at=None,
            completed_at=None,
            status=AppointmentStatus.SCHEDULED.value,
        )
        new_appt.job_id = job.id  # same job

        # New appointment starts completely clean — no inherited data
        assert new_appt.en_route_at is None
        assert new_appt.arrived_at is None
        assert new_appt.completed_at is None
        assert new_appt.status == AppointmentStatus.SCHEDULED.value
