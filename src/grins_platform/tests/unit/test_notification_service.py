"""Unit tests for NotificationService.

Tests consent-gated notifications, appointment notification types,
invoice reminder scheduling, lien notifications, and lead confirmation SMS.

Properties:
  P42: All customer notifications are consent-gated
  P55: Automated invoice reminder scheduling

Validates: Requirements 39.1, 39.2, 39.3, 39.4, 39.5, 39.8,
           54.1, 54.2, 54.3, 55.1, 55.2
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import (
    AppointmentStatus,
    InvoiceStatus,
)
from grins_platform.services.notification_service import (
    CT_TZ,
    LIEN_THRESHOLD_DAYS,
    PAST_DUE_INTERVAL_DAYS,
    PRE_DUE_DAYS,
    NotificationService,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_customer_mock(
    *,
    customer_id: UUID | None = None,
    first_name: str = "Jane",
    last_name: str = "Smith",
    phone: str = "5125551234",
    email: str | None = "jane@example.com",
    sms_opt_in: bool = True,
    properties: list[Any] | None = None,
) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.sms_opt_in = sms_opt_in
    c.properties = properties or []
    c.internal_notes = None
    c.preferred_service_times = None
    return c


def _make_appointment_mock(
    *,
    appointment_id: UUID | None = None,
    job_id: UUID | None = None,
    staff_id: UUID | None = None,
    scheduled_date: date | None = None,
    time_window_start: time | None = None,
    time_window_end: time | None = None,
    status: str = AppointmentStatus.CONFIRMED.value,
    job: MagicMock | None = None,
    staff: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Appointment."""
    a = MagicMock()
    a.id = appointment_id or uuid4()
    a.job_id = job_id or uuid4()
    a.staff_id = staff_id or uuid4()
    a.scheduled_date = scheduled_date or date(2025, 7, 20)
    a.time_window_start = time_window_start or time(9, 0)
    a.time_window_end = time_window_end or time(10, 0)
    a.status = status
    a.job = job
    a.staff = staff
    return a


def _make_invoice_mock(
    *,
    invoice_id: UUID | None = None,
    job_id: UUID | None = None,
    customer_id: UUID | None = None,
    invoice_number: str = "INV-2025-0100",
    total_amount: Decimal = Decimal("500.00"),
    due_date: date | None = None,
    status: str = InvoiceStatus.SENT.value,
    pre_due_reminder_sent_at: datetime | None = None,
    last_past_due_reminder_at: datetime | None = None,
    lien_eligible: bool = False,
    lien_warning_sent: datetime | None = None,
    customer: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Invoice."""
    inv = MagicMock()
    inv.id = invoice_id or uuid4()
    inv.job_id = job_id or uuid4()
    inv.customer_id = customer_id or uuid4()
    inv.invoice_number = invoice_number
    inv.total_amount = total_amount
    inv.due_date = due_date or (date.today() + timedelta(days=2))
    inv.status = status
    inv.pre_due_reminder_sent_at = pre_due_reminder_sent_at
    inv.last_past_due_reminder_at = last_past_due_reminder_at
    inv.lien_eligible = lien_eligible
    inv.lien_warning_sent = lien_warning_sent
    inv.customer = customer
    inv.document_url = None
    inv.invoice_token = None
    inv.customer_name = None
    return inv


def _make_lead_mock(
    *,
    lead_id: UUID | None = None,
    name: str = "Bob Lead",
    phone: str = "5125559999",
    sms_consent: bool = True,
) -> MagicMock:
    """Create a mock Lead."""
    lead = MagicMock()
    lead.id = lead_id or uuid4()
    lead.name = name
    lead.phone = phone
    lead.sms_consent = sms_consent
    return lead


def _make_staff_mock(*, name: str = "Mike Tech") -> MagicMock:
    """Create a mock Staff."""
    s = MagicMock()
    s.name = name
    return s


def _build_service(
    *,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
    google_review_url: str = "https://g.page/review/grins",
) -> NotificationService:
    """Build a NotificationService with mocked dependencies."""
    return NotificationService(
        sms_service=sms_service,
        email_service=email_service,
        google_review_url=google_review_url,
    )


def _mock_db_for_appointment(
    appointment: MagicMock,
    customer: MagicMock,
) -> AsyncMock:
    """Create a mock db session that returns appointment then customer."""
    db = AsyncMock()

    # First execute call returns the appointment (with relations)
    appt_result = MagicMock()
    appt_result.scalar_one_or_none.return_value = appointment

    # Second execute call returns the customer
    cust_result = MagicMock()
    cust_result.scalar_one_or_none.return_value = customer

    db.execute = AsyncMock(side_effect=[appt_result, cust_result])
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_db_for_day_of_reminders(
    appointments: list[MagicMock],
    customers: list[MagicMock | None],
) -> AsyncMock:
    """Create a mock db for send_day_of_reminders."""
    db = AsyncMock()

    # First execute returns all appointments
    appt_result = MagicMock()
    appt_scalars = MagicMock()
    appt_scalars.all.return_value = appointments
    appt_result.scalars.return_value = appt_scalars

    # Subsequent executes return customers one by one
    customer_results = []
    for c in customers:
        r = MagicMock()
        r.scalar_one_or_none.return_value = c
        customer_results.append(r)

    db.execute = AsyncMock(side_effect=[appt_result, *customer_results])
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


# =============================================================================
# Property 42: All customer notifications are consent-gated
# Validates: Requirements 39.1, 39.2, 39.3, 39.4, 39.5, 39.8
# =============================================================================


@pytest.mark.unit
class TestProperty42ConsentGatedNotifications:
    """Property 42: All customer notifications are consent-gated.

    *For any* automated customer notification (day-of, on-my-way, arrival,
    delay, completion), SMS shall only be sent if the customer has
    sms_opt_in=True. Email shall always be sent as fallback regardless
    of SMS consent.

    **Validates: Requirements 39.1, 39.2, 39.3, 39.4, 39.5, 39.8**
    """

    # ------------------------------------------------------------------ #
    # P42 — SMS consent gating: sms_opt_in=True sends SMS
    # ------------------------------------------------------------------ #

    @given(
        sms_opt_in=st.booleans(),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_send_notification_with_sms_consent_gates_sms(
        self,
        sms_opt_in: bool,
    ) -> None:
        """For any customer, SMS is sent only when sms_opt_in=True.
        Email is always sent regardless.

        **Validates: Requirements 39.8**
        """
        customer = _make_customer_mock(sms_opt_in=sms_opt_in)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id
        job.summary = "Sprinkler repair"
        appt = _make_appointment_mock(
            job_id=job.id,
            job=job,
            staff=staff,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_on_my_way(db, appt.id, eta_minutes=15)

        if sms_opt_in:
            sms_svc.send_message.assert_awaited_once()
            assert result.sms_sent is True
        else:
            sms_svc.send_message.assert_not_awaited()
            assert result.sms_sent is False

        # Email always sent
        email_svc._send_email.assert_called_once()
        assert result.email_sent is True

    # ------------------------------------------------------------------ #
    # P42 — Day-of reminders (Req 39.1)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_day_of_reminders_with_consented_customer_sends_sms(
        self,
    ) -> None:
        """Day-of reminder sends SMS when customer has sms_opt_in=True.

        **Validates: Requirements 39.1**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(
            scheduled_date=date.today(),
            status=AppointmentStatus.CONFIRMED.value,
            job=job,
            staff=staff,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_day_of_reminders([appt], [customer])

        count = await svc.send_day_of_reminders(db)

        assert count == 1
        sms_svc.send_message.assert_awaited_once()
        email_svc._send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_day_of_reminders_with_no_consent_skips_sms_sends_email(
        self,
    ) -> None:
        """Day-of reminder skips SMS but sends email when sms_opt_in=False.

        **Validates: Requirements 39.1, 39.8**
        """
        customer = _make_customer_mock(sms_opt_in=False)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(
            scheduled_date=date.today(),
            status=AppointmentStatus.CONFIRMED.value,
            job=job,
            staff=staff,
        )

        sms_svc = AsyncMock()
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_day_of_reminders([appt], [customer])

        count = await svc.send_day_of_reminders(db)

        assert count == 1
        sms_svc.send_message.assert_not_awaited()
        email_svc._send_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_day_of_reminders_with_no_appointments_returns_zero(
        self,
    ) -> None:
        """Day-of reminder with no today appointments returns 0.

        **Validates: Requirements 39.1, 39.7**
        """
        svc = _build_service()
        db = _mock_db_for_day_of_reminders([], [])

        count = await svc.send_day_of_reminders(db)
        assert count == 0

    # ------------------------------------------------------------------ #
    # P42 — On My Way notification (Req 39.2)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_on_my_way_with_consent_sends_sms_and_email(
        self,
    ) -> None:
        """On-my-way sends both SMS and email when consented.

        **Validates: Requirements 39.2**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        staff = _make_staff_mock(name="Alex")
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_on_my_way(db, appt.id, eta_minutes=20)

        assert result.sms_sent is True
        assert result.email_sent is True

    @pytest.mark.asyncio
    async def test_send_on_my_way_with_not_found_returns_error(self) -> None:
        """On-my-way with missing appointment returns error.

        **Validates: Requirements 39.2**
        """
        svc = _build_service()
        db = AsyncMock()
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=r)

        result = await svc.send_on_my_way(db, uuid4())
        assert result.error == "Appointment not found"
        assert result.sms_sent is False
        assert result.email_sent is False

    # ------------------------------------------------------------------ #
    # P42 — Arrival notification (Req 39.3)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_arrival_with_consent_sends_both_channels(
        self,
    ) -> None:
        """Arrival notification sends SMS + email when consented.

        **Validates: Requirements 39.3**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_arrival_notification(db, appt.id)

        assert result.sms_sent is True
        assert result.email_sent is True

    @pytest.mark.asyncio
    async def test_send_arrival_without_consent_sends_email_only(
        self,
    ) -> None:
        """Arrival notification skips SMS when not consented, sends email.

        **Validates: Requirements 39.3, 39.8**
        """
        customer = _make_customer_mock(sms_opt_in=False)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_arrival_notification(db, appt.id)

        assert result.sms_sent is False
        assert result.email_sent is True
        sms_svc.send_message.assert_not_awaited()

    # ------------------------------------------------------------------ #
    # P42 — Delay notification (Req 39.4)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_delay_with_consent_sends_both_channels(
        self,
    ) -> None:
        """Delay notification sends SMS + email when consented.

        **Validates: Requirements 39.4**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        new_eta = datetime(2025, 7, 20, 11, 30)
        result = await svc.send_delay_notification(db, appt.id, new_eta=new_eta)

        assert result.sms_sent is True
        assert result.email_sent is True

    @pytest.mark.asyncio
    async def test_send_delay_without_consent_sends_email_only(
        self,
    ) -> None:
        """Delay notification skips SMS when not consented.

        **Validates: Requirements 39.4, 39.8**
        """
        customer = _make_customer_mock(sms_opt_in=False)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_delay_notification(db, appt.id)

        assert result.sms_sent is False
        assert result.email_sent is True

    # ------------------------------------------------------------------ #
    # P42 — Completion notification (Req 39.5)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_completion_with_consent_sends_both_channels(
        self,
    ) -> None:
        """Completion notification sends SMS + email when consented.

        **Validates: Requirements 39.5**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id
        job.summary = "Replaced 3 sprinkler heads"

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_completion_notification(
            db,
            appt.id,
            invoice_url="https://example.com/inv/123",
        )

        assert result.sms_sent is True
        assert result.email_sent is True

    @pytest.mark.asyncio
    async def test_send_completion_without_consent_sends_email_only(
        self,
    ) -> None:
        """Completion notification skips SMS when not consented.

        **Validates: Requirements 39.5, 39.8**
        """
        customer = _make_customer_mock(sms_opt_in=False)
        staff = _make_staff_mock()
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = customer.id
        job.summary = "Winterization complete"

        appt = _make_appointment_mock(job_id=job.id, job=job, staff=staff)

        sms_svc = AsyncMock()
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = _mock_db_for_appointment(appt, customer)

        result = await svc.send_completion_notification(db, appt.id)

        assert result.sms_sent is False
        assert result.email_sent is True

    # ------------------------------------------------------------------ #
    # P42 — Lead confirmation SMS: consent + time-window gated
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_send_lead_confirmation_with_consent_in_window_sends_sms(
        self,
    ) -> None:
        """Lead confirmation SMS sent when consented and within 8AM-9PM CT.

        **Validates: Requirements 39.8**
        """
        lead = _make_lead_mock(sms_consent=True)

        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock()

        svc = _build_service(sms_service=sms_svc)

        db = AsyncMock()
        lead_result = MagicMock()
        lead_result.scalar_one_or_none.return_value = lead
        db.execute = AsyncMock(return_value=lead_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        # Patch time to be within window (noon CT)
        mock_now = datetime(2025, 7, 20, 12, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.notification_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sent = await svc.send_lead_confirmation_sms(db, lead.id)

        assert sent is True
        sms_svc.send_automated_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_lead_confirmation_without_consent_skips(
        self,
    ) -> None:
        """Lead confirmation SMS skipped when sms_consent=False.

        **Validates: Requirements 39.8**
        """
        lead = _make_lead_mock(sms_consent=False)

        sms_svc = AsyncMock()
        svc = _build_service(sms_service=sms_svc)

        db = AsyncMock()
        lead_result = MagicMock()
        lead_result.scalar_one_or_none.return_value = lead
        db.execute = AsyncMock(return_value=lead_result)

        sent = await svc.send_lead_confirmation_sms(db, lead.id)

        assert sent is False
        sms_svc.send_automated_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_lead_confirmation_outside_window_defers(
        self,
    ) -> None:
        """Lead confirmation SMS deferred when outside 8AM-9PM CT window.

        **Validates: Requirements 39.8**
        """
        lead = _make_lead_mock(sms_consent=True)

        sms_svc = AsyncMock()
        svc = _build_service(sms_service=sms_svc)

        db = AsyncMock()
        lead_result = MagicMock()
        lead_result.scalar_one_or_none.return_value = lead
        db.execute = AsyncMock(return_value=lead_result)
        db.add = MagicMock()
        db.flush = AsyncMock()

        # Patch time to be outside window (11PM CT)
        mock_now = datetime(2025, 7, 20, 23, 0, 0, tzinfo=CT_TZ)
        with patch(
            "grins_platform.services.notification_service.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            sent = await svc.send_lead_confirmation_sms(db, lead.id)

        assert sent is True  # deferred counts as True
        sms_svc.send_automated_message.assert_not_awaited()
        # A SentMessage with status "scheduled" should have been added
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_lead_confirmation_with_not_found_returns_false(
        self,
    ) -> None:
        """Lead confirmation returns False when lead not found.

        **Validates: Requirements 39.8**
        """
        svc = _build_service()
        db = AsyncMock()
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=r)

        sent = await svc.send_lead_confirmation_sms(db, uuid4())
        assert sent is False


# =============================================================================
# Property 55: Automated invoice reminder scheduling
# Validates: Requirements 54.1, 54.2, 54.3, 55.1, 55.2
# =============================================================================


@pytest.mark.unit
class TestProperty55InvoiceReminderScheduling:
    """Property 55: Automated invoice reminder scheduling.

    *For any* invoice 3 days before due_date with no pre_due_reminder_sent_at,
    a pre-due reminder shall be sent. For any invoice past due_date with
    last_past_due_reminder_at older than 7 days (or null), a past-due reminder
    shall be sent. For any lien-eligible invoice 30+ days past due with no
    lien warning sent, a lien notification shall be sent.

    **Validates: Requirements 54.1, 54.2, 54.3, 55.1, 55.2**
    """

    def _mock_db_for_invoices(
        self,
        invoices: list[MagicMock],
    ) -> AsyncMock:
        """Create a mock db for send_invoice_reminders."""
        db = AsyncMock()
        inv_result = MagicMock()
        inv_scalars = MagicMock()
        inv_scalars.all.return_value = invoices
        inv_result.scalars.return_value = inv_scalars
        db.execute = AsyncMock(return_value=inv_result)
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    # ------------------------------------------------------------------ #
    # Pre-due reminders (Req 54.2)
    # ------------------------------------------------------------------ #

    @given(
        days_until_due=st.integers(min_value=1, max_value=PRE_DUE_DAYS),
    )
    @settings(max_examples=10)
    @pytest.mark.asyncio
    async def test_pre_due_reminder_sent_when_within_threshold(
        self,
        days_until_due: int,
    ) -> None:
        """For any invoice 1-3 days before due, pre-due reminder is sent.

        **Validates: Requirements 54.1, 54.2**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        invoice = _make_invoice_mock(
            due_date=date.today() + timedelta(days=days_until_due),
            pre_due_reminder_sent_at=None,
            customer=customer,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.pre_due_sent == 1
        assert summary.past_due_sent == 0
        assert summary.lien_sent == 0

    @pytest.mark.asyncio
    async def test_pre_due_reminder_not_sent_when_already_sent(
        self,
    ) -> None:
        """Pre-due reminder skipped when pre_due_reminder_sent_at is set.

        **Validates: Requirements 54.2**
        """
        customer = _make_customer_mock()
        invoice = _make_invoice_mock(
            due_date=date.today() + timedelta(days=2),
            pre_due_reminder_sent_at=datetime.now(tz=CT_TZ),
            customer=customer,
        )

        svc = _build_service()
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.pre_due_sent == 0
        assert summary.skipped == 1

    # ------------------------------------------------------------------ #
    # Past-due reminders (Req 54.3)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_past_due_reminder_sent_when_never_reminded(
        self,
    ) -> None:
        """Past-due reminder sent when last_past_due_reminder_at is None.

        **Validates: Requirements 54.1, 54.3**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=5),
            last_past_due_reminder_at=None,
            customer=customer,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.past_due_sent == 1

    @pytest.mark.asyncio
    async def test_past_due_reminder_sent_after_7_day_interval(
        self,
    ) -> None:
        """Past-due reminder sent when last reminder was 7+ days ago.

        **Validates: Requirements 54.3**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=20),
            last_past_due_reminder_at=datetime.now(tz=CT_TZ)
            - timedelta(days=PAST_DUE_INTERVAL_DAYS),
            customer=customer,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.past_due_sent == 1

    @pytest.mark.asyncio
    async def test_past_due_reminder_skipped_when_within_interval(
        self,
    ) -> None:
        """Past-due reminder not sent when last reminder was <7 days ago.

        **Validates: Requirements 54.3**
        """
        customer = _make_customer_mock()
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=10),
            last_past_due_reminder_at=datetime.now(tz=CT_TZ) - timedelta(days=3),
            customer=customer,
        )

        svc = _build_service()
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.past_due_sent == 0
        assert summary.failed == 0

    # ------------------------------------------------------------------ #
    # Lien notifications (Req 55.1, 55.2)
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_lien_notification_sent_at_30_days_past_due(
        self,
    ) -> None:
        """Lien notification sent for eligible invoice 30+ days past due.

        **Validates: Requirements 55.1, 55.2**
        """
        customer = _make_customer_mock(sms_opt_in=True)
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=LIEN_THRESHOLD_DAYS),
            lien_eligible=True,
            lien_warning_sent=None,
            customer=customer,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.lien_sent == 1
        assert invoice.status == InvoiceStatus.LIEN_WARNING.value

    @pytest.mark.asyncio
    async def test_lien_notification_skipped_when_not_eligible(
        self,
    ) -> None:
        """Lien notification skipped for non-lien-eligible invoice.

        **Validates: Requirements 55.1**
        """
        customer = _make_customer_mock()
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=35),
            lien_eligible=False,
            lien_warning_sent=None,
            customer=customer,
        )

        svc = _build_service()
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.lien_sent == 0

    @pytest.mark.asyncio
    async def test_lien_notification_skipped_when_already_sent(
        self,
    ) -> None:
        """Lien notification skipped when lien_warning_sent is set.

        **Validates: Requirements 55.2**
        """
        customer = _make_customer_mock()
        invoice = _make_invoice_mock(
            due_date=date.today() - timedelta(days=40),
            lien_eligible=True,
            lien_warning_sent=datetime.now(tz=CT_TZ) - timedelta(days=5),
            customer=customer,
        )

        svc = _build_service()
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.lien_sent == 0

    # ------------------------------------------------------------------ #
    # Mixed batch scenarios
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_mixed_invoice_batch_categorizes_correctly(
        self,
    ) -> None:
        """A batch with pre-due, past-due, and lien invoices categorizes each.

        **Validates: Requirements 54.1, 54.2, 54.3, 55.1, 55.2**
        """
        customer = _make_customer_mock(sms_opt_in=True)

        # Pre-due: 2 days before due
        pre_due_inv = _make_invoice_mock(
            invoice_number="INV-PRE",
            due_date=date.today() + timedelta(days=2),
            pre_due_reminder_sent_at=None,
            customer=customer,
        )
        # Past-due: 10 days past, never reminded
        past_due_inv = _make_invoice_mock(
            invoice_number="INV-PAST",
            due_date=date.today() - timedelta(days=10),
            last_past_due_reminder_at=None,
            customer=customer,
        )
        # Lien: 35 days past, eligible, no warning
        lien_inv = _make_invoice_mock(
            invoice_number="INV-LIEN",
            due_date=date.today() - timedelta(days=35),
            lien_eligible=True,
            lien_warning_sent=None,
            customer=customer,
        )

        sms_svc = AsyncMock()
        sms_svc.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        svc = _build_service(sms_service=sms_svc, email_service=email_svc)
        db = self._mock_db_for_invoices(
            [pre_due_inv, past_due_inv, lien_inv],
        )

        summary = await svc.send_invoice_reminders(db)

        assert summary.pre_due_sent == 1
        assert summary.past_due_sent == 1
        assert summary.lien_sent == 1
        assert summary.failed == 0

    @pytest.mark.asyncio
    async def test_invoice_with_no_customer_is_skipped(
        self,
    ) -> None:
        """Invoice with no linked customer is skipped.

        **Validates: Requirements 54.1**
        """
        invoice = _make_invoice_mock(
            due_date=date.today() + timedelta(days=2),
            customer=None,
        )

        svc = _build_service()
        db = self._mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.skipped == 1
        assert summary.pre_due_sent == 0

    # ------------------------------------------------------------------ #
    # _should_send_past_due helper
    # ------------------------------------------------------------------ #

    @given(
        days_since_last=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=20)
    def test_should_send_past_due_respects_interval(
        self,
        days_since_last: int,
    ) -> None:
        """_should_send_past_due returns True only when interval >= 7 days.

        **Validates: Requirements 54.3**
        """
        svc = _build_service()
        invoice = _make_invoice_mock()

        if days_since_last == 0:
            # Simulate "never sent"
            invoice.last_past_due_reminder_at = None
        else:
            invoice.last_past_due_reminder_at = datetime.now(tz=CT_TZ) - timedelta(
                days=days_since_last,
            )

        result = svc._should_send_past_due(invoice, date.today())

        if days_since_last == 0:
            # None means never sent → should send
            assert result is True
        elif days_since_last >= PAST_DUE_INTERVAL_DAYS:
            assert result is True
        else:
            assert result is False


# =============================================================================
# bughunt 2026-04-16 H-5: admin cancellation alert
# =============================================================================


@pytest.mark.unit
class TestSendAdminCancellationAlert:
    """Tests for ``send_admin_cancellation_alert`` (H-5).

    D-4 (2026-04-16): the method must dispatch *both* an email to the
    configured admin address **and** create an :class:`Alert` row. Email
    failures must be logged and swallowed so the customer SMS flow is
    never blocked.

    Validates: bughunt 2026-04-16 finding H-5
    """

    @pytest.mark.asyncio
    async def test_send_admin_cancellation_alert_dispatches_email_and_creates_alert_row(
        self,
    ) -> None:
        """Both channels fire on the happy path.

        Validates: bughunt 2026-04-16 finding H-5
        """
        from grins_platform.models.alert import Alert
        from grins_platform.services.admin_config import (
            AdminNotificationSettings,
        )

        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        admin_settings = AdminNotificationSettings(
            admin_notification_email="admin@example.com",
        )

        svc = NotificationService(
            email_service=email_svc,
            admin_settings=admin_settings,
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        appointment_id = uuid4()
        customer_id = uuid4()
        scheduled_at = datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc)

        await svc.send_admin_cancellation_alert(
            db,
            appointment_id=appointment_id,
            customer_id=customer_id,
            customer_name="Jane Doe",
            scheduled_at=scheduled_at,
            source="customer_sms",
        )

        # --- Email dispatch ---
        email_svc._send_email.assert_called_once()
        email_kwargs = email_svc._send_email.call_args.kwargs
        assert email_kwargs["to_email"] == "admin@example.com"
        assert "Jane Doe" in email_kwargs["subject"]
        assert "customer_sms" in email_kwargs["html_body"]

        # --- Alert row persisted ---
        db.add.assert_called_once()
        added_alert = db.add.call_args[0][0]
        assert isinstance(added_alert, Alert)
        assert added_alert.type == "customer_cancelled_appointment"
        assert added_alert.severity == "warning"
        assert added_alert.entity_type == "appointment"
        assert added_alert.entity_id == appointment_id
        assert "Jane Doe" in added_alert.message
        assert "customer_sms" in added_alert.message
        assert "2026-04-17 09:00" in added_alert.message

    @pytest.mark.asyncio
    async def test_send_admin_cancellation_alert_swallows_email_failure(
        self,
    ) -> None:
        """Email sender raising must NOT propagate — Alert row still created.

        Validates: bughunt 2026-04-16 finding H-5
        """
        from grins_platform.models.alert import Alert
        from grins_platform.services.admin_config import (
            AdminNotificationSettings,
        )

        email_svc = MagicMock()
        email_svc._send_email = MagicMock(
            side_effect=RuntimeError("SMTP down"),
        )

        admin_settings = AdminNotificationSettings(
            admin_notification_email="admin@example.com",
        )

        svc = NotificationService(
            email_service=email_svc,
            admin_settings=admin_settings,
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        # Must not raise
        await svc.send_admin_cancellation_alert(
            db,
            appointment_id=uuid4(),
            customer_id=uuid4(),
            customer_name="Jane Doe",
            scheduled_at=datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc),
        )

        # Alert row still created despite email failure.
        db.add.assert_called_once()
        added_alert = db.add.call_args[0][0]
        assert isinstance(added_alert, Alert)

    @pytest.mark.asyncio
    async def test_send_admin_cancellation_alert_skips_email_when_not_configured(
        self,
    ) -> None:
        """No ``ADMIN_NOTIFICATION_EMAIL`` → email skipped, alert row still written.

        Validates: bughunt 2026-04-16 finding H-5
        """
        from grins_platform.services.admin_config import (
            AdminNotificationSettings,
        )

        email_svc = MagicMock()
        email_svc._send_email = MagicMock(return_value=True)

        # Empty recipient simulates the missing-env-var case.
        admin_settings = AdminNotificationSettings(admin_notification_email="")

        svc = NotificationService(
            email_service=email_svc,
            admin_settings=admin_settings,
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await svc.send_admin_cancellation_alert(
            db,
            appointment_id=uuid4(),
            customer_id=uuid4(),
            customer_name="Jane Doe",
            scheduled_at=datetime(2026, 4, 17, 9, 0, tzinfo=timezone.utc),
        )

        email_svc._send_email.assert_not_called()
        # Alert row still created.
        db.add.assert_called_once()
