"""Functional tests for CRM gap closure background jobs.

Tests full background job workflows with mocked repositories and
external services, verifying cross-service interactions as a user
would experience them.

Validates: Requirements 39.11, 54.7, 55.7
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    AppointmentStatus,
    CampaignStatus,
    EstimateStatus,
    FollowUpStatus,
    InvoiceStatus,
)
from grins_platform.services.campaign_service import CampaignService
from grins_platform.services.estimate_service import EstimateService
from grins_platform.services.notification_service import (
    NotificationService,
)
from grins_platform.services.sms.recipient import Recipient

# =============================================================================
# Helpers
# =============================================================================


def _make_customer(
    *,
    customer_id: Any | None = None,
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
    return c


def _recipient_from(c: MagicMock) -> Recipient:
    """Convert a customer mock to a Recipient."""
    return Recipient(
        phone=c.phone,
        source_type="customer",
        customer_id=c.id,
        first_name=c.first_name,
        last_name=c.last_name,
    )


def _scalar_result(value: Any) -> MagicMock:
    """Create a mock DB execute result returning *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_appointment(
    *,
    appointment_id: Any | None = None,
    job_id: Any | None = None,
    scheduled_date: date | None = None,
    time_window_start: time | None = None,
    time_window_end: time | None = None,
    status: str = AppointmentStatus.SCHEDULED.value,
    staff: MagicMock | None = None,
    job: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Appointment."""
    a = MagicMock()
    a.id = appointment_id or uuid4()
    a.job_id = job_id or uuid4()
    a.scheduled_date = scheduled_date or date.today()
    a.time_window_start = time_window_start or time(9, 0)
    a.time_window_end = time_window_end or time(11, 0)
    a.status = status
    a.staff = staff or _make_staff()
    a.job = job
    return a


def _make_staff(*, name: str = "Mike Tech") -> MagicMock:
    """Create a mock Staff."""
    s = MagicMock()
    s.name = name
    return s


def _make_invoice(
    *,
    invoice_id: Any | None = None,
    invoice_number: str = "INV-2025-0100",
    total_amount: Decimal = Decimal("500.00"),
    due_date: date | None = None,
    status: str = InvoiceStatus.SENT.value,
    pre_due_reminder_sent_at: datetime | None = None,
    last_past_due_reminder_at: datetime | None = None,
    lien_eligible: bool = False,
    lien_warning_sent: datetime | None = None,
    customer: MagicMock | None = None,
    job_id: Any | None = None,
) -> MagicMock:
    """Create a mock Invoice."""
    inv = MagicMock()
    inv.id = invoice_id or uuid4()
    inv.job_id = job_id or uuid4()
    inv.customer_id = customer.id if customer else uuid4()
    inv.invoice_number = invoice_number
    inv.total_amount = total_amount
    inv.due_date = due_date or (date.today() + timedelta(days=2))
    inv.status = status
    inv.pre_due_reminder_sent_at = pre_due_reminder_sent_at
    inv.last_past_due_reminder_at = last_past_due_reminder_at
    inv.lien_eligible = lien_eligible
    inv.lien_warning_sent = lien_warning_sent
    inv.customer = customer
    return inv


def _make_estimate(
    *,
    estimate_id: Any | None = None,
    customer_id: Any | None = None,
    status: str = EstimateStatus.SENT.value,
    approved_at: datetime | None = None,
    rejected_at: datetime | None = None,
    customer_token: Any | None = None,
    lead_id: Any | None = None,
    customer: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Estimate."""
    e = MagicMock()
    e.id = estimate_id or uuid4()
    e.customer_id = customer_id or uuid4()
    e.lead_id = lead_id
    e.status = status
    e.approved_at = approved_at
    e.rejected_at = rejected_at
    e.customer_token = customer_token or uuid4()
    e.customer = customer
    return e


def _make_follow_up(
    *,
    follow_up_id: Any | None = None,
    estimate_id: Any | None = None,
    follow_up_number: int = 1,
    scheduled_at: datetime | None = None,
    status: str = FollowUpStatus.SCHEDULED.value,
    message: str | None = None,
    promotion_code: str | None = None,
) -> MagicMock:
    """Create a mock EstimateFollowUp."""
    fu = MagicMock()
    fu.id = follow_up_id or uuid4()
    fu.estimate_id = estimate_id or uuid4()
    fu.follow_up_number = follow_up_number
    fu.scheduled_at = scheduled_at or (
        datetime.now(tz=timezone.utc) - timedelta(hours=1)
    )
    fu.status = status
    fu.message = message
    fu.promotion_code = promotion_code
    fu.sent_at = None
    return fu


def _make_campaign(
    *,
    campaign_id: Any | None = None,
    name: str = "Summer Promo",
    campaign_type: str = "sms",
    status: str = CampaignStatus.SCHEDULED.value,
    body: str = "Check out our summer deals!",
    subject: str | None = None,
    scheduled_at: datetime | None = None,
    target_audience: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock Campaign."""
    c = MagicMock()
    c.id = campaign_id or uuid4()
    c.name = name
    c.campaign_type = campaign_type
    c.status = status
    c.body = body
    c.subject = subject
    c.scheduled_at = scheduled_at or (
        datetime.now(tz=timezone.utc) - timedelta(minutes=10)
    )
    c.target_audience = target_audience or {"all": True}
    c.sent_at = None
    return c


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
    customer_results: list[MagicMock] = []
    for cust in customers:
        cr = MagicMock()
        cr.scalar_one_or_none.return_value = cust
        customer_results.append(cr)

    db.execute = AsyncMock(side_effect=[appt_result, *customer_results])
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _mock_db_for_invoices(
    invoices: list[MagicMock],
) -> AsyncMock:
    """Create a mock db for send_invoice_reminders."""
    db = AsyncMock()

    # First execute: _get_notification_settings (business_settings query)
    # Returns empty so defaults are used
    settings_result = MagicMock()
    settings_scalars = MagicMock()
    settings_scalars.all.return_value = []
    settings_result.scalars.return_value = settings_scalars

    # Second execute: invoice query
    inv_result = MagicMock()
    inv_scalars = MagicMock()
    inv_scalars.all.return_value = invoices
    inv_result.scalars.return_value = inv_scalars

    db.execute = AsyncMock(side_effect=[inv_result])
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


def _build_notification_service(
    *,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
) -> NotificationService:
    """Build a NotificationService with mocked external deps."""
    sms = sms_service or AsyncMock()
    sms.send_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )
    sms.send_automated_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )
    email = email_service or MagicMock()
    email._send_email = MagicMock(return_value=True)
    return NotificationService(
        sms_service=sms,
        email_service=email,
    )


def _build_estimate_service(
    *,
    repo: AsyncMock | None = None,
    lead_service: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
) -> tuple[EstimateService, AsyncMock]:
    """Build an EstimateService with mocked deps."""
    estimate_repo = repo or AsyncMock()
    sms = sms_service or AsyncMock()
    sms.send_automated_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )
    lead_svc = lead_service or AsyncMock()
    lead_svc.create_lead_from_estimate = AsyncMock(return_value=MagicMock())
    svc = EstimateService(
        estimate_repository=estimate_repo,
        lead_service=lead_svc,
        sms_service=sms,
    )
    return svc, estimate_repo


def _build_campaign_service(
    *,
    repo: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
) -> tuple[CampaignService, AsyncMock]:
    """Build a CampaignService with mocked deps."""
    campaign_repo = repo or AsyncMock()
    sms = sms_service or AsyncMock()
    sms.send_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )
    email = email_service or MagicMock()
    email._send_email = MagicMock(return_value=True)
    svc = CampaignService(
        campaign_repository=campaign_repo,
        sms_service=sms,
        email_service=email,
    )
    return svc, campaign_repo


# =============================================================================
# 1. Day-of Reminder Job
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestDayOfReminderJob:
    """Test send_day_of_reminders sends to all same-day appointments.

    Validates: Requirement 39.11
    """

    async def test_day_of_reminders_sends_to_all_same_day_appointments(
        self,
    ) -> None:
        """Multiple appointments today each get a reminder."""
        svc = _build_notification_service()

        cust1 = _make_customer(first_name="Alice", sms_opt_in=True)
        cust2 = _make_customer(first_name="Bob", sms_opt_in=True)
        cust3 = _make_customer(first_name="Carol", sms_opt_in=False)

        appt1 = _make_appointment(scheduled_date=date.today())
        appt2 = _make_appointment(scheduled_date=date.today())
        appt3 = _make_appointment(
            scheduled_date=date.today(),
            status=AppointmentStatus.CONFIRMED.value,
        )

        db = _mock_db_for_day_of_reminders(
            [appt1, appt2, appt3],
            [cust1, cust2, cust3],
        )

        count = await svc.send_day_of_reminders(db)

        # All 3 should get notifications (SMS or email fallback)
        assert count == 3

    async def test_day_of_reminders_skips_missing_customer(self) -> None:
        """Appointments with no resolvable customer are skipped."""
        svc = _build_notification_service()

        appt = _make_appointment(scheduled_date=date.today())
        db = _mock_db_for_day_of_reminders([appt], [None])

        count = await svc.send_day_of_reminders(db)
        assert count == 0

    async def test_day_of_reminders_empty_schedule_returns_zero(self) -> None:
        """No appointments today means zero reminders sent."""
        svc = _build_notification_service()
        db = _mock_db_for_day_of_reminders([], [])

        count = await svc.send_day_of_reminders(db)
        assert count == 0


# =============================================================================
# 2. Invoice Reminder Job
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestInvoiceReminderJob:
    """Test send_invoice_reminders sends pre-due, past-due, and lien.

    Validates: Requirements 54.7, 55.7
    """

    async def test_pre_due_reminder_sent_for_invoice_due_soon(self) -> None:
        """Invoice due in 2 days (within 3-day window) gets pre-due reminder."""
        svc = _build_notification_service()
        customer = _make_customer(sms_opt_in=True)
        invoice = _make_invoice(
            due_date=date.today() + timedelta(days=2),
            status=InvoiceStatus.SENT.value,
            pre_due_reminder_sent_at=None,
            customer=customer,
        )
        db = _mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.pre_due_sent == 1
        assert summary.past_due_sent == 0
        assert summary.lien_sent == 0

    async def test_past_due_reminder_sent_for_overdue_invoice(self) -> None:
        """Invoice 10 days past due gets a past-due reminder."""
        svc = _build_notification_service()
        customer = _make_customer(sms_opt_in=True)
        invoice = _make_invoice(
            due_date=date.today() - timedelta(days=10),
            status=InvoiceStatus.OVERDUE.value,
            last_past_due_reminder_at=None,
            lien_eligible=False,
            customer=customer,
        )
        db = _mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.past_due_sent == 1
        assert summary.pre_due_sent == 0
        assert summary.lien_sent == 0

    async def test_lien_notification_sent_for_eligible_invoice(self) -> None:
        """Invoice 35 days past due with lien_eligible gets lien warning."""
        svc = _build_notification_service()
        customer = _make_customer(sms_opt_in=True)
        invoice = _make_invoice(
            due_date=date.today() - timedelta(days=35),
            status=InvoiceStatus.OVERDUE.value,
            lien_eligible=True,
            lien_warning_sent=None,
            customer=customer,
        )
        db = _mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.lien_sent == 1
        assert summary.pre_due_sent == 0
        assert summary.past_due_sent == 0

    async def test_mixed_invoices_get_correct_notifications(self) -> None:
        """Batch with pre-due, past-due, and lien invoices all handled."""
        svc = _build_notification_service()
        cust = _make_customer(sms_opt_in=True)

        pre_due_inv = _make_invoice(
            invoice_number="INV-PRE",
            due_date=date.today() + timedelta(days=1),
            status=InvoiceStatus.SENT.value,
            pre_due_reminder_sent_at=None,
            customer=cust,
        )
        past_due_inv = _make_invoice(
            invoice_number="INV-PAST",
            due_date=date.today() - timedelta(days=14),
            status=InvoiceStatus.OVERDUE.value,
            last_past_due_reminder_at=None,
            lien_eligible=False,
            customer=cust,
        )
        lien_inv = _make_invoice(
            invoice_number="INV-LIEN",
            due_date=date.today() - timedelta(days=35),
            status=InvoiceStatus.OVERDUE.value,
            lien_eligible=True,
            lien_warning_sent=None,
            customer=cust,
        )

        db = _mock_db_for_invoices([pre_due_inv, past_due_inv, lien_inv])

        summary = await svc.send_invoice_reminders(db)

        assert summary.pre_due_sent == 1
        assert summary.past_due_sent == 1
        assert summary.lien_sent == 1

    async def test_invoice_without_customer_is_skipped(self) -> None:
        """Invoice with no customer attached is skipped."""
        svc = _build_notification_service()
        invoice = _make_invoice(
            due_date=date.today() + timedelta(days=2),
            customer=None,
        )
        db = _mock_db_for_invoices([invoice])

        summary = await svc.send_invoice_reminders(db)

        assert summary.skipped == 1
        assert summary.pre_due_sent == 0


# =============================================================================
# 3. Estimate Approval Check
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimateApprovalCheck:
    """Test check_unapproved_estimates routes to leads pipeline.

    Validates: Requirement 39.11 (background job testing)
    """

    async def test_unapproved_estimates_routed_to_leads(self) -> None:
        """Estimates >4hrs old without approval create leads."""
        est1 = _make_estimate(customer_id=uuid4())
        est2 = _make_estimate(customer_id=uuid4())

        svc, repo = _build_estimate_service()
        repo.find_unapproved_older_than = AsyncMock(return_value=[est1, est2])

        count = await svc.check_unapproved_estimates()

        assert count == 2
        assert svc.lead_service.create_lead_from_estimate.call_count == 2  # type: ignore[union-attr]

    async def test_unapproved_estimate_without_customer_skipped(self) -> None:
        """Estimates with no customer_id are skipped."""
        est = _make_estimate()
        est.customer_id = None  # Explicitly set to None after creation

        svc, repo = _build_estimate_service()
        repo.find_unapproved_older_than = AsyncMock(return_value=[est])

        count = await svc.check_unapproved_estimates()

        assert count == 0
        svc.lead_service.create_lead_from_estimate.assert_not_called()  # type: ignore[union-attr]

    async def test_no_unapproved_estimates_returns_zero(self) -> None:
        """No unapproved estimates means zero routed."""
        svc, repo = _build_estimate_service()
        repo.find_unapproved_older_than = AsyncMock(return_value=[])

        count = await svc.check_unapproved_estimates()
        assert count == 0


# =============================================================================
# 4. Follow-Up Processing
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestFollowUpProcessing:
    """Test process_follow_ups sends due follow-ups.

    Validates: Requirement 39.11 (background job testing)
    """

    async def test_due_follow_ups_are_sent(self) -> None:
        """Pending follow-ups with scheduled_at in the past are sent."""
        est = _make_estimate(
            approved_at=None,
            rejected_at=None,
        )
        fu1 = _make_follow_up(
            estimate_id=est.id,
            follow_up_number=1,
        )
        fu2 = _make_follow_up(
            estimate_id=est.id,
            follow_up_number=2,
        )

        svc, repo = _build_estimate_service()
        repo.get_pending_follow_ups = AsyncMock(return_value=[fu1, fu2])
        repo.get_by_id = AsyncMock(return_value=est)

        # Mock phone resolution
        est.customer = _make_customer(phone="5125551234")
        est.lead_id = None

        count = await svc.process_follow_ups()

        assert count == 2
        assert fu1.status == FollowUpStatus.SENT.value
        assert fu2.status == FollowUpStatus.SENT.value

    async def test_follow_up_for_approved_estimate_is_cancelled(self) -> None:
        """Follow-ups for already-approved estimates are cancelled."""
        est = _make_estimate(
            approved_at=datetime.now(tz=timezone.utc),
        )
        fu = _make_follow_up(estimate_id=est.id)

        svc, repo = _build_estimate_service()
        repo.get_pending_follow_ups = AsyncMock(return_value=[fu])
        repo.get_by_id = AsyncMock(return_value=est)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=1)

        count = await svc.process_follow_ups()

        assert count == 0
        repo.cancel_follow_ups_for_estimate.assert_called_once_with(est.id)

    async def test_no_pending_follow_ups_returns_zero(self) -> None:
        """No pending follow-ups means zero sent."""
        svc, repo = _build_estimate_service()
        repo.get_pending_follow_ups = AsyncMock(return_value=[])

        count = await svc.process_follow_ups()
        assert count == 0


# =============================================================================
# 5. Campaign Sender
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCampaignSender:
    """Test send_campaign processes scheduled campaigns.

    Validates: Requirement 39.11 (background job testing)
    """

    async def test_scheduled_campaign_sends_to_recipients(self) -> None:
        """A scheduled campaign sends to all matching recipients."""
        campaign = _make_campaign(
            status=CampaignStatus.SCHEDULED.value,
            campaign_type="sms",
        )
        cust1 = _make_customer(sms_opt_in=True)
        cust2 = _make_customer(sms_opt_in=True)

        svc, repo = _build_campaign_service()
        repo.get_by_id = AsyncMock(return_value=campaign)
        repo.update = AsyncMock()
        repo.add_recipient = AsyncMock()

        # Mock _filter_recipients to return Recipient objects
        svc._filter_recipients = AsyncMock(  # type: ignore[method-assign]
            return_value=[_recipient_from(cust1), _recipient_from(cust2)],
        )
        # Mock _get_business_address
        svc._get_business_address = AsyncMock(  # type: ignore[method-assign]
            return_value="123 Main St, Austin TX",
        )
        # Mock _send_to_recipient to succeed
        svc._send_to_recipient = AsyncMock(return_value=True)  # type: ignore[method-assign]

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(cust1),
                _scalar_result(cust2),
            ],
        )
        result = await svc.send_campaign(db, campaign.id)

        assert result.sent == 2
        assert result.total_recipients == 2
        assert result.failed == 0

    async def test_campaign_skips_opted_out_recipients(self) -> None:
        """Recipients without consent are skipped."""
        campaign = _make_campaign(
            status=CampaignStatus.SCHEDULED.value,
            campaign_type="sms",
        )
        opted_out_cust = _make_customer(sms_opt_in=False, email=None)

        svc, repo = _build_campaign_service()
        repo.get_by_id = AsyncMock(return_value=campaign)
        repo.update = AsyncMock()
        repo.add_recipient = AsyncMock()

        svc._filter_recipients = AsyncMock(  # type: ignore[method-assign]
            return_value=[_recipient_from(opted_out_cust)],
        )
        svc._get_business_address = AsyncMock(  # type: ignore[method-assign]
            return_value="123 Main St",
        )
        # _resolve_channels returns empty for no consent
        svc._resolve_channels = MagicMock(return_value=[])  # type: ignore[method-assign]

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(opted_out_cust),
            ],
        )
        result = await svc.send_campaign(db, campaign.id)

        assert result.skipped == 1
        assert result.sent == 0
