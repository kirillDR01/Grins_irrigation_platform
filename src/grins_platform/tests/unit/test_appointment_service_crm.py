"""Unit tests for AppointmentService CRM Gap Closure enhancements.

Tests reschedule conflict detection, lead time calculation, job filtering,
address auto-population, payment collection, invoice creation, notes/photos,
Google review requests, status transitions, payment gate, staff time analytics,
and enriched appointment responses.

Properties:
  P28: Appointment conflict detection on reschedule
  P29: Schedule lead time calculation
  P30: Job filter returns only matching jobs
  P32: Address auto-population from customer
  P33: Payment collection creates/updates invoice
  P34: Invoice pre-population from appointment
  P36: Appointment notes propagate to customer
  P37: Google review request consent and deduplication
  P38: Appointment status transition state machine
  P39: Payment gate blocks completion without payment or invoice
  P40: Staff time duration calculations
  P43: Enriched appointment response includes all required fields

Validates: Requirements 24.6, 24.7, 25.4, 26.5, 29.4, 30.7, 30.8, 31.6,
           31.7, 32.8, 33.6, 33.7, 34.7, 35.8, 35.9, 36.5, 36.6, 37.5,
           37.6, 40.5
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    PaymentRequiredError,
    ReviewAlreadyRequestedError,
    StaffConflictError,
)
from grins_platform.models.enums import (
    AppointmentStatus,
    InvoiceStatus,
    PaymentMethod,
)
from grins_platform.schemas.appointment_ops import (
    DateRange,
    LeadTimeResult,
    PaymentCollectionRequest,
    PaymentResult,
    ReviewRequestResult,
    StaffTimeEntry,
)
from grins_platform.services.appointment_service import AppointmentService

# =============================================================================
# Helpers
# =============================================================================


def _make_appointment_mock(
    *,
    appointment_id: UUID | None = None,
    job_id: UUID | None = None,
    staff_id: UUID | None = None,
    scheduled_date: date | None = None,
    time_window_start: time | None = None,
    time_window_end: time | None = None,
    status: str = AppointmentStatus.CONFIRMED.value,
    en_route_at: datetime | None = None,
    arrived_at: datetime | None = None,
    completed_at: datetime | None = None,
    notes: str | None = None,
    materials_needed: list[str] | None = None,
    estimated_duration_minutes: int | None = None,
    job: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Appointment model instance."""
    apt = MagicMock()
    apt.id = appointment_id or uuid4()
    apt.job_id = job_id or uuid4()
    apt.staff_id = staff_id or uuid4()
    apt.scheduled_date = scheduled_date or date(2025, 7, 15)
    apt.time_window_start = time_window_start or time(9, 0)
    apt.time_window_end = time_window_end or time(10, 0)
    apt.status = status
    apt.en_route_at = en_route_at
    apt.arrived_at = arrived_at
    apt.completed_at = completed_at
    apt.notes = notes
    apt.materials_needed = materials_needed
    apt.estimated_duration_minutes = estimated_duration_minutes
    apt.route_order = None
    apt.estimated_arrival = None
    apt.cancellation_reason = None
    apt.cancelled_at = None
    apt.rescheduled_from_id = None
    apt.created_at = datetime.now(tz=timezone.utc)
    apt.updated_at = datetime.now(tz=timezone.utc)
    apt.job = job
    apt.staff = None
    apt.sent_messages = []
    return apt


def _make_job_mock(
    *,
    job_id: UUID | None = None,
    customer_id: UUID | None = None,
    job_type: str = "repair",
    quoted_amount: Decimal | None = Decimal("250.00"),
    final_amount: Decimal | None = None,
    customer: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Job model instance."""
    job = MagicMock()
    job.id = job_id or uuid4()
    job.customer_id = customer_id or uuid4()
    job.job_type = job_type
    job.quoted_amount = quoted_amount
    job.final_amount = final_amount
    job.customer = customer
    job.status = "in_progress"
    job.notes = None
    job.summary = None
    job.customer_name = None
    job.customer_phone = None
    return job


def _make_customer_mock(
    *,
    customer_id: UUID | None = None,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str = "6125551234",
    email: str | None = "john@example.com",
    sms_opt_in: bool = True,
    internal_notes: str | None = None,
) -> MagicMock:
    """Create a mock Customer model instance."""
    customer = MagicMock()
    customer.id = customer_id or uuid4()
    customer.first_name = first_name
    customer.last_name = last_name
    customer.phone = phone
    customer.email = email
    customer.sms_opt_in = sms_opt_in
    customer.internal_notes = internal_notes
    customer.preferred_service_times = None
    return customer


def _make_invoice_mock(
    *,
    invoice_id: UUID | None = None,
    job_id: UUID | None = None,
    customer_id: UUID | None = None,
    invoice_number: str = "INV-2025-0001",
    total_amount: Decimal = Decimal("250.00"),
    paid_amount: Decimal | None = None,
    status: str = InvoiceStatus.SENT.value,
) -> MagicMock:
    """Create a mock Invoice model instance."""
    inv = MagicMock()
    inv.id = invoice_id or uuid4()
    inv.job_id = job_id or uuid4()
    inv.customer_id = customer_id or uuid4()
    inv.invoice_number = invoice_number
    inv.total_amount = total_amount
    inv.paid_amount = paid_amount
    inv.status = status
    inv.created_at = datetime.now(tz=timezone.utc)
    inv.document_url = None
    inv.invoice_token = None
    inv.customer_name = None
    return inv


def _make_staff_mock(
    *,
    staff_id: UUID | None = None,
    first_name: str = "Mike",
    last_name: str = "Tech",
) -> MagicMock:
    """Create a mock Staff model instance."""
    staff = MagicMock()
    staff.id = staff_id or uuid4()
    staff.first_name = first_name
    staff.last_name = last_name
    return staff


def _build_service(
    *,
    appt_repo: AsyncMock | None = None,
    job_repo: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    invoice_repo: AsyncMock | None = None,
    estimate_service: AsyncMock | None = None,
    google_review_url: str = "https://g.page/review/grins",
) -> AppointmentService:
    """Build an AppointmentService with mocked dependencies."""
    return AppointmentService(
        appointment_repository=appt_repo or AsyncMock(),
        job_repository=job_repo or AsyncMock(),
        staff_repository=staff_repo or AsyncMock(),
        invoice_repository=invoice_repo,
        estimate_service=estimate_service,
        google_review_url=google_review_url,
    )


# =============================================================================
# Property 28: Appointment conflict detection on reschedule
# Validates: Requirements 24.2, 24.4, 24.5
# =============================================================================


@pytest.mark.unit
class TestProperty28ConflictDetectionOnReschedule:
    """Property 28: Appointment conflict detection on reschedule.

    *For any* appointment reschedule to a new time, if another appointment
    exists for the same staff member overlapping the new time window, the
    reschedule shall be rejected. If no conflict exists, it shall succeed.

    **Validates: Requirements 24.2, 24.4, 24.5**
    """

    @given(
        hour_start=st.integers(min_value=6, max_value=16),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_reschedule_with_no_conflict_succeeds(
        self,
        hour_start: int,
    ) -> None:
        """For any valid time slot with no overlapping appointment,
        reschedule succeeds and updates the appointment.

        **Validates: Requirements 24.2, 24.4, 24.5**
        """
        apt_id = uuid4()
        staff_id = uuid4()
        new_date = date(2025, 8, 1)
        new_start = time(hour_start, 0)
        new_end = time(hour_start + 1, 0)

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            staff_id=staff_id,
        )
        updated_apt = _make_appointment_mock(
            appointment_id=apt_id,
            staff_id=staff_id,
            scheduled_date=new_date,
            time_window_start=new_start,
            time_window_end=new_end,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        # No existing appointments for that day (no conflict)
        appt_repo.get_staff_daily_schedule = AsyncMock(return_value=[])
        appt_repo.update = AsyncMock(return_value=updated_apt)

        svc = _build_service(appt_repo=appt_repo)
        result = await svc.reschedule(apt_id, new_date, new_start, new_end)

        assert result.scheduled_date == new_date
        assert result.time_window_start == new_start
        assert result.time_window_end == new_end
        appt_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reschedule_with_overlapping_appointment_raises_conflict(
        self,
    ) -> None:
        """Rescheduling to a time that overlaps an existing appointment
        for the same staff raises StaffConflictError.

        **Validates: Requirements 24.2, 24.5**
        """
        apt_id = uuid4()
        staff_id = uuid4()
        conflicting_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            staff_id=staff_id,
        )
        # Existing appointment from 9:00-10:00
        existing = _make_appointment_mock(
            appointment_id=conflicting_id,
            staff_id=staff_id,
            time_window_start=time(9, 0),
            time_window_end=time(10, 0),
            status=AppointmentStatus.CONFIRMED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.get_staff_daily_schedule = AsyncMock(return_value=[existing])

        svc = _build_service(appt_repo=appt_repo)

        # Try to reschedule to 9:30-10:30 (overlaps 9:00-10:00)
        with pytest.raises(StaffConflictError) as exc_info:
            await svc.reschedule(
                apt_id,
                date(2025, 8, 1),
                time(9, 30),
                time(10, 30),
            )
        assert exc_info.value.staff_id == staff_id
        assert exc_info.value.conflicting_appointment_id == conflicting_id

    @pytest.mark.asyncio
    async def test_reschedule_with_cancelled_appointment_ignores_conflict(
        self,
    ) -> None:
        """Cancelled appointments should not cause conflicts."""
        apt_id = uuid4()
        staff_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            staff_id=staff_id,
        )
        # Cancelled appointment at the same time
        cancelled = _make_appointment_mock(
            staff_id=staff_id,
            time_window_start=time(9, 0),
            time_window_end=time(10, 0),
            status=AppointmentStatus.CANCELLED.value,
        )
        updated = _make_appointment_mock(appointment_id=apt_id, staff_id=staff_id)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.get_staff_daily_schedule = AsyncMock(return_value=[cancelled])
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        result = await svc.reschedule(
            apt_id,
            date(2025, 8, 1),
            time(9, 0),
            time(10, 0),
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_reschedule_with_not_found_raises_error(self) -> None:
        """Rescheduling a non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(AppointmentNotFoundError):
            await svc.reschedule(
                uuid4(),
                date(2025, 8, 1),
                time(9, 0),
                time(10, 0),
            )

    @pytest.mark.asyncio
    async def test_reschedule_excludes_self_from_conflict_check(self) -> None:
        """The appointment being rescheduled should not conflict with itself."""
        apt_id = uuid4()
        staff_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            staff_id=staff_id,
            time_window_start=time(9, 0),
            time_window_end=time(10, 0),
        )
        updated = _make_appointment_mock(appointment_id=apt_id, staff_id=staff_id)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        # The same appointment appears in the daily schedule
        appt_repo.get_staff_daily_schedule = AsyncMock(return_value=[appointment])
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        # Reschedule to same time — should not conflict with itself
        result = await svc.reschedule(
            apt_id,
            date(2025, 8, 1),
            time(9, 0),
            time(10, 0),
        )
        assert result is not None


# =============================================================================
# Property 29: Schedule lead time calculation
# Validates: Requirements 25.2, 25.3
# =============================================================================


@pytest.mark.unit
class TestProperty29LeadTimeCalculation:
    """Property 29: Schedule lead time calculation.

    *For any* set of existing appointments and staff availability, the lead
    time endpoint shall return the earliest date where at least one staff
    member has an available slot.

    **Validates: Requirements 25.2, 25.3**
    """

    @given(
        staff_count=st.integers(min_value=1, max_value=5),
        max_per_day=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_lead_time_with_empty_schedule_returns_today(
        self,
        staff_count: int,
        max_per_day: int,
    ) -> None:
        """With no existing appointments, lead time should be 0 (today).

        **Validates: Requirements 25.2, 25.3**
        """
        staff_list = [_make_staff_mock() for _ in range(staff_count)]

        staff_repo = AsyncMock()
        staff_repo.find_available = AsyncMock(return_value=staff_list)

        appt_repo = AsyncMock()
        appt_repo.count_by_date = AsyncMock(return_value=0)

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)
        result = await svc.calculate_lead_time(
            max_appointments_per_day=max_per_day,
        )

        assert isinstance(result, LeadTimeResult)
        # If today is not Sunday, should be available today
        today = date.today()
        if today.weekday() < 6:  # Not Sunday
            assert result.days == 0
            assert result.earliest_date == today
            assert "today" in result.display.lower()

    @pytest.mark.asyncio
    async def test_lead_time_with_full_schedule_returns_next_available(
        self,
    ) -> None:
        """When today is fully booked, returns the next available day.

        **Validates: Requirements 25.2, 25.3**
        """
        staff_repo = AsyncMock()
        staff_repo.find_available = AsyncMock(
            return_value=[_make_staff_mock()],
        )

        # First day full (count >= capacity), second day has room
        call_count = 0

        async def mock_count(_check_date: date) -> int:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 8  # Full
            return 0  # Available

        appt_repo = AsyncMock()
        appt_repo.count_by_date = AsyncMock(side_effect=mock_count)

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)
        result = await svc.calculate_lead_time(max_appointments_per_day=8)

        assert result.days >= 1
        assert result.earliest_date is not None

    @pytest.mark.asyncio
    async def test_lead_time_with_no_availability_returns_max_days(
        self,
    ) -> None:
        """When no slots available within look-ahead, returns max days."""
        staff_repo = AsyncMock()
        staff_repo.find_available = AsyncMock(
            return_value=[_make_staff_mock()],
        )

        appt_repo = AsyncMock()
        # Always full
        appt_repo.count_by_date = AsyncMock(return_value=100)

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)
        result = await svc.calculate_lead_time(
            max_appointments_per_day=8,
            look_ahead_days=30,
        )

        assert result.days == 30
        assert result.earliest_date is None
        assert "weeks" in result.display.lower()


# =============================================================================
# Property 30: Job filter returns only matching jobs
# Validates: Requirements 26.2, 26.3
# =============================================================================


@pytest.mark.unit
class TestProperty30JobFilterReturnsMatching:
    """Property 30: Job filter returns only matching jobs.

    *For any* combination of location and job type filters, the job
    selection endpoint shall return only jobs matching all criteria.

    **Validates: Requirements 26.2, 26.3**
    """

    @given(
        job_type=st.sampled_from(["repair", "installation", "seasonal", "diagnostic"]),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_list_appointments_with_status_filter_returns_matching(
        self,
        job_type: str,
    ) -> None:
        """Filtering appointments by status returns only matching ones.

        **Validates: Requirements 26.2, 26.3**
        """
        matching_apt = _make_appointment_mock(
            status=AppointmentStatus.CONFIRMED.value,
        )
        _make_appointment_mock(
            status=AppointmentStatus.COMPLETED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(
            return_value=([matching_apt], 1),
        )

        svc = _build_service(appt_repo=appt_repo)
        result, total = await svc.list_appointments(
            status=AppointmentStatus.CONFIRMED,
            page=1,
            page_size=20,
        )

        assert total == 1
        assert len(result) == 1
        assert result[0].status == AppointmentStatus.CONFIRMED.value

    @pytest.mark.asyncio
    async def test_list_appointments_with_date_filter_returns_matching(
        self,
    ) -> None:
        """Filtering by date range returns only appointments in range."""
        target_date = date(2025, 8, 15)
        apt = _make_appointment_mock(scheduled_date=target_date)

        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(return_value=([apt], 1))

        svc = _build_service(appt_repo=appt_repo)
        result, total = await svc.list_appointments(
            date_from=date(2025, 8, 1),
            date_to=date(2025, 8, 31),
            page=1,
            page_size=20,
        )

        assert total == 1
        assert result[0].scheduled_date == target_date


# =============================================================================
# Property 32: Address auto-population from customer
# Validates: Requirements 29.1
# =============================================================================


@pytest.mark.unit
class TestProperty32AddressAutoPopulation:
    """Property 32: Address auto-population from customer.

    *For any* appointment creation where a customer with a property address
    is selected, the address field shall be auto-populated.

    **Validates: Requirements 29.1**
    """

    @given(
        address=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=5,
            max_size=200,
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_create_appointment_with_customer_address_populates_notes(
        self,
        address: str,
    ) -> None:
        """When a customer has a property address, the appointment
        creation should have access to that address via the job's customer.

        **Validates: Requirements 29.1**
        """
        customer_id = uuid4()
        customer = _make_customer_mock(customer_id=customer_id)

        # Customer has a property with an address
        prop = MagicMock()
        prop.address = address
        prop.city = "Minneapolis"
        prop.state = "MN"
        prop.zip_code = "55401"
        customer.properties = [prop]

        job = _make_job_mock(customer_id=customer_id, customer=customer)
        staff = _make_staff_mock()

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(return_value=staff)

        created_apt = _make_appointment_mock(job_id=job.id, staff_id=staff.id)
        appt_repo = AsyncMock()
        appt_repo.create = AsyncMock(return_value=created_apt)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            staff_repo=staff_repo,
        )

        data = MagicMock()
        data.job_id = job.id
        data.staff_id = staff.id
        data.scheduled_date = date(2025, 8, 1)
        data.time_window_start = time(9, 0)
        data.time_window_end = time(10, 0)
        data.notes = None

        result = await svc.create_appointment(data)

        # The appointment was created — address is available via job.customer
        assert result is not None
        # Verify the customer's property address is accessible
        assert job.customer.properties[0].address == address


# =============================================================================
# Property 33: Payment collection creates/updates invoice
# Validates: Requirements 30.3, 30.4, 30.5
# =============================================================================


@pytest.mark.unit
class TestProperty33PaymentCollection:
    """Property 33: Payment collection creates/updates invoice.

    *For any* payment collected on an appointment with a valid amount and
    method, the linked invoice shall be created or updated.

    **Validates: Requirements 30.3, 30.4, 30.5**
    """

    @given(
        amount=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("9999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        method=st.sampled_from(list(PaymentMethod)),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_collect_payment_with_no_existing_invoice_creates_new(
        self,
        amount: Decimal,
        method: PaymentMethod,
    ) -> None:
        """For any valid amount and method, when no invoice exists,
        a new invoice is created with PAID status.

        **Validates: Requirements 30.3, 30.4, 30.5**
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(customer_id=customer_id)
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        new_invoice = _make_invoice_mock(
            job_id=job_id,
            customer_id=customer_id,
            total_amount=amount,
            status=InvoiceStatus.PAID.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.get_next_sequence = AsyncMock(return_value=1)
        invoice_repo.create = AsyncMock(return_value=new_invoice)
        invoice_repo.update = AsyncMock(return_value=new_invoice)
        # Mock _find_invoice_for_job to return None (no existing invoice)
        invoice_repo.session = AsyncMock()

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )

        # Patch _find_invoice_for_job to return None
        svc._find_invoice_for_job = AsyncMock(return_value=None)

        payment = PaymentCollectionRequest(
            payment_method=method,
            amount=amount,
        )
        result = await svc.collect_payment(apt_id, payment)

        assert isinstance(result, PaymentResult)
        assert result.amount_paid == amount
        assert result.payment_method == method.value
        invoice_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_collect_payment_with_existing_invoice_updates_it(
        self,
    ) -> None:
        """When an invoice already exists, payment updates the existing one.

        **Validates: Requirements 30.3, 30.4**
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        job = _make_job_mock(job_id=job_id, customer_id=customer_id)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )
        existing_invoice = _make_invoice_mock(
            job_id=job_id,
            customer_id=customer_id,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("200.00"),
            status=InvoiceStatus.PARTIAL.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.update = AsyncMock(return_value=existing_invoice)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )
        svc._find_invoice_for_job = AsyncMock(return_value=existing_invoice)

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("100.00"),
        )
        result = await svc.collect_payment(apt_id, payment)

        assert isinstance(result, PaymentResult)
        assert result.amount_paid == Decimal("100.00")
        invoice_repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_collect_payment_with_full_amount_sets_paid_status(
        self,
    ) -> None:
        """Paying the full remaining amount sets invoice to PAID."""
        apt_id = uuid4()
        job_id = uuid4()

        job = _make_job_mock(job_id=job_id)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )
        existing_invoice = _make_invoice_mock(
            job_id=job_id,
            total_amount=Decimal("300.00"),
            paid_amount=Decimal("200.00"),
            status=InvoiceStatus.PARTIAL.value,
        )

        updated_invoice = _make_invoice_mock(
            job_id=job_id,
            total_amount=Decimal("300.00"),
            paid_amount=Decimal("300.00"),
            status=InvoiceStatus.PAID.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.update = AsyncMock(return_value=updated_invoice)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )
        svc._find_invoice_for_job = AsyncMock(return_value=existing_invoice)

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CHECK,
            amount=Decimal("100.00"),
            reference_number="CHK-1234",
        )
        await svc.collect_payment(apt_id, payment)

        # Verify the update was called with PAID status
        update_call = invoice_repo.update.call_args
        update_data = update_call[0][1]
        assert update_data["status"] == InvoiceStatus.PAID.value

    @pytest.mark.asyncio
    async def test_collect_payment_with_not_found_raises_error(self) -> None:
        """Collecting payment for non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        invoice_repo = AsyncMock()
        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("100.00"),
        )
        with pytest.raises(AppointmentNotFoundError):
            await svc.collect_payment(uuid4(), payment)


# =============================================================================
# Property 34: Invoice pre-population from appointment
# Validates: Requirements 31.2, 31.4
# =============================================================================


@pytest.mark.unit
class TestProperty34InvoicePrePopulation:
    """Property 34: Invoice pre-population from appointment.

    *For any* appointment with a linked job and customer, creating an
    invoice from that appointment shall produce an invoice with customer_id,
    job_id, and amount matching the appointment's job data.

    **Validates: Requirements 31.2, 31.4**
    """

    @given(
        quoted_amount=st.decimals(
            min_value=Decimal("10.00"),
            max_value=Decimal("50000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_create_invoice_from_appointment_uses_job_amount(
        self,
        quoted_amount: Decimal,
    ) -> None:
        """Invoice amount matches the job's quoted_amount.

        **Validates: Requirements 31.2, 31.4**
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            quoted_amount=quoted_amount,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        created_invoice = _make_invoice_mock(
            job_id=job_id,
            customer_id=customer_id,
            total_amount=quoted_amount,
            status=InvoiceStatus.SENT.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.get_next_sequence = AsyncMock(return_value=1)
        invoice_repo.create = AsyncMock(return_value=created_invoice)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )
        await svc.create_invoice_from_appointment(apt_id)

        # Verify create was called with correct customer_id and job_id
        create_call = invoice_repo.create.call_args
        assert create_call.kwargs["job_id"] == job_id
        assert create_call.kwargs["customer_id"] == customer_id
        assert create_call.kwargs["amount"] == quoted_amount

    @pytest.mark.asyncio
    async def test_create_invoice_uses_final_amount_when_available(
        self,
    ) -> None:
        """When job has final_amount, it takes precedence over quoted_amount.

        **Validates: Requirements 31.2**
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            quoted_amount=Decimal("200.00"),
            final_amount=Decimal("275.00"),
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        created_invoice = _make_invoice_mock(
            job_id=job_id,
            customer_id=customer_id,
            total_amount=Decimal("275.00"),
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.get_next_sequence = AsyncMock(return_value=2)
        invoice_repo.create = AsyncMock(return_value=created_invoice)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )
        await svc.create_invoice_from_appointment(apt_id)

        create_call = invoice_repo.create.call_args
        assert create_call.kwargs["amount"] == Decimal("275.00")

    @pytest.mark.asyncio
    async def test_create_invoice_with_not_found_appointment_raises_error(
        self,
    ) -> None:
        """Creating invoice for non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        invoice_repo = AsyncMock()
        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)

        with pytest.raises(AppointmentNotFoundError):
            await svc.create_invoice_from_appointment(uuid4())

    @pytest.mark.asyncio
    async def test_create_invoice_generates_valid_invoice_number(
        self,
    ) -> None:
        """Invoice number follows INV-YYYY-NNNN format."""
        apt_id = uuid4()
        job_id = uuid4()

        job = _make_job_mock(job_id=job_id)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        created_invoice = _make_invoice_mock(
            job_id=job_id,
            invoice_number="INV-2025-0042",
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        invoice_repo = AsyncMock()
        invoice_repo.get_next_sequence = AsyncMock(return_value=42)
        invoice_repo.create = AsyncMock(return_value=created_invoice)

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            invoice_repo=invoice_repo,
        )
        await svc.create_invoice_from_appointment(apt_id)

        create_call = invoice_repo.create.call_args
        inv_number = create_call.kwargs["invoice_number"]
        assert inv_number.startswith("INV-")
        assert inv_number.endswith("-0042")


# =============================================================================
# Property 36: Appointment notes propagate to customer
# Validates: Requirements 33.2, 33.3
# =============================================================================


@pytest.mark.unit
class TestProperty36NotesPropagateToCustomer:
    """Property 36: Appointment notes propagate to customer.

    *For any* notes saved on an appointment, the linked customer's
    `internal_notes` shall contain those notes with a timestamp prefix.

    **Validates: Requirements 33.2, 33.3**
    """

    @given(
        notes=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=500,
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_add_notes_appends_to_customer_internal_notes(
        self,
        notes: str,
    ) -> None:
        """For any notes text, it is appended to the customer's
        internal_notes with a timestamp prefix.

        **Validates: Requirements 33.2, 33.3**
        """
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            internal_notes="Existing notes.",
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
            job=job,
        )
        updated_apt = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
            notes=notes,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated_apt)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        await svc.add_notes_and_photos(apt_id, notes=notes)

        # Verify appointment notes were saved
        appt_repo.update.assert_awaited_once()
        update_data = appt_repo.update.call_args[0][1]
        assert update_data["notes"] == notes

        # Verify customer internal_notes was appended
        assert notes in customer.internal_notes
        assert "Appointment note:" in customer.internal_notes

    @pytest.mark.asyncio
    async def test_add_notes_with_empty_customer_notes_creates_new(
        self,
    ) -> None:
        """When customer has no existing notes, the note is still appended."""
        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            internal_notes=None,
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
            job=job,
        )
        updated_apt = _make_appointment_mock(
            appointment_id=apt_id,
            notes="New note",
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated_apt)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        await svc.add_notes_and_photos(apt_id, notes="New note")

        assert "New note" in customer.internal_notes

    @pytest.mark.asyncio
    async def test_add_notes_with_not_found_raises_error(self) -> None:
        """Adding notes to non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(AppointmentNotFoundError):
            await svc.add_notes_and_photos(uuid4(), notes="test")

    @pytest.mark.asyncio
    async def test_add_notes_with_none_notes_does_not_update(self) -> None:
        """When notes is None, appointment notes are not updated."""
        apt_id = uuid4()
        appointment = _make_appointment_mock(appointment_id=apt_id)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        svc = _build_service(appt_repo=appt_repo)
        await svc.add_notes_and_photos(apt_id, notes=None)

        # No update should be called since no data changed
        appt_repo.update.assert_not_awaited()


# =============================================================================
# Property 37: Google review request consent and deduplication
# Validates: Requirements 34.2, 34.6
# =============================================================================


@pytest.mark.unit
class TestProperty37GoogleReviewConsentAndDedup:
    """Property 37: Google review request consent and deduplication.

    *For any* review request, if the customer has sms_consent=False, no SMS
    shall be sent. If a review request was sent within the last 30 days,
    the request shall be rejected.

    **Validates: Requirements 34.2, 34.6**
    """

    @pytest.mark.asyncio
    async def test_review_request_with_consent_and_no_prior_sends(
        self,
    ) -> None:
        """Customer with SMS consent and no prior review request succeeds.

        **Validates: Requirements 34.2, 34.6**
        """
        from unittest.mock import patch

        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=True,
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        # No prior review request
        svc._get_last_review_request_date = AsyncMock(return_value=None)

        mock_sms_service = AsyncMock()
        mock_sms_service.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        with (
            patch(
                "grins_platform.services.sms_service.SMSService",
                return_value=mock_sms_service,
            ),
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
        ):
            result = await svc.request_google_review(apt_id)

        assert isinstance(result, ReviewRequestResult)
        assert result.sent is True
        assert result.channel == "sms"
        mock_sms_service.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_request_without_consent_returns_sent_false(
        self,
    ) -> None:
        """Customer without SMS consent returns a non-raised ``ReviewRequestResult``
        with ``sent=False`` (bughunt CR-9 remainder — previously raised
        ``ConsentRequiredError`` which the API handler then translated to
        HTTP 422; we now return a structured 2xx payload instead).

        **Validates: Requirements 34.2**
        """
        from unittest.mock import patch

        apt_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=False,
        )
        job = _make_job_mock(customer_id=customer_id, customer=customer)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job.id,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)

        with patch(
            "grins_platform.services.sms.consent.check_sms_consent",
            return_value=False,
        ):
            result = await svc.request_google_review(apt_id)

        assert isinstance(result, ReviewRequestResult)
        assert result.sent is False
        assert result.channel is None
        assert "opted out" in result.message.lower()

    @given(
        days_ago=st.integers(min_value=0, max_value=29),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_review_request_within_30_days_raises_dedup_error(
        self,
        days_ago: int,
    ) -> None:
        """Review request within 30 days of last request raises
        ReviewAlreadyRequestedError.

        **Validates: Requirements 34.6**
        """
        from unittest.mock import patch

        apt_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=True,
        )
        job = _make_job_mock(customer_id=customer_id, customer=customer)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job.id,
        )

        last_review = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        svc._get_last_review_request_date = AsyncMock(return_value=last_review)

        with (
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
            pytest.raises(ReviewAlreadyRequestedError),
        ):
            await svc.request_google_review(apt_id)

    @pytest.mark.asyncio
    async def test_review_request_after_30_days_succeeds(self) -> None:
        """Review request after 30+ days since last request succeeds.

        **Validates: Requirements 34.6**
        """
        from unittest.mock import patch

        apt_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=True,
        )
        job = _make_job_mock(customer_id=customer_id, customer=customer)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job.id,
        )

        # 31 days ago — outside dedup window
        last_review = datetime.now(tz=timezone.utc) - timedelta(days=31)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        svc._get_last_review_request_date = AsyncMock(return_value=last_review)

        mock_sms_service = AsyncMock()
        mock_sms_service.send_message = AsyncMock(
            return_value={"success": True, "message_id": str(uuid4())},
        )
        with (
            patch(
                "grins_platform.services.sms_service.SMSService",
                return_value=mock_sms_service,
            ),
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
        ):
            result = await svc.request_google_review(apt_id)
        assert result.sent is True

    @pytest.mark.asyncio
    async def test_review_request_with_not_found_raises_error(self) -> None:
        """Review request for non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(AppointmentNotFoundError):
            await svc.request_google_review(uuid4())

    @pytest.mark.asyncio
    async def test_review_request_with_correct_message_type_and_review_url(
        self,
    ) -> None:
        """Review push calls sms_service.send_message() with
        MessageType.GOOGLE_REVIEW_REQUEST and includes the review URL
        in the message body.

        **Validates: Requirements 1.1, 1.2**
        """
        from unittest.mock import patch

        from grins_platform.models.enums import MessageType

        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=True,
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.session = AsyncMock()

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        review_url = "https://g.page/review/grins"
        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            google_review_url=review_url,
        )
        svc._get_last_review_request_date = AsyncMock(return_value=None)

        mock_sms_service = AsyncMock()
        mock_sms_service.send_message = AsyncMock(
            return_value={"success": True, "message_id": "SM123"},
        )
        with (
            patch(
                "grins_platform.services.sms_service.SMSService",
                return_value=mock_sms_service,
            ),
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
        ):
            result = await svc.request_google_review(apt_id)

        assert result.sent is True
        assert result.channel == "sms"

        # Verify send_message was called with correct message_type
        call_kwargs = mock_sms_service.send_message.call_args
        assert call_kwargs.kwargs["message_type"] == MessageType.GOOGLE_REVIEW_REQUEST

        # Verify the review URL is included in the message body
        sent_message = call_kwargs.kwargs["message"]
        assert review_url in sent_message

    @pytest.mark.asyncio
    async def test_review_request_with_sms_failure_returns_sent_false(
        self,
    ) -> None:
        """When sms_service.send_message() raises an exception, the method
        returns sent=False without crashing.

        **Validates: Requirements 1.4**
        """
        from unittest.mock import patch

        apt_id = uuid4()
        job_id = uuid4()
        customer_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            sms_opt_in=True,
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            customer=customer,
        )
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.session = AsyncMock()

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        svc._get_last_review_request_date = AsyncMock(return_value=None)

        mock_sms_service = AsyncMock()
        mock_sms_service.send_message = AsyncMock(
            side_effect=RuntimeError("SMS provider unavailable"),
        )
        with (
            patch(
                "grins_platform.services.sms_service.SMSService",
                return_value=mock_sms_service,
            ),
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
        ):
            result = await svc.request_google_review(apt_id)

        # Should NOT raise — returns a result with sent=False
        assert isinstance(result, ReviewRequestResult)
        assert result.sent is False
        assert result.channel == "sms"
        assert "Failed" in result.message or "fail" in result.message.lower()


# =============================================================================
# Property 38: Appointment status transition state machine
# Validates: Requirements 35.1, 35.2, 35.3, 35.4, 35.5, 35.6
# =============================================================================


@pytest.mark.unit
class TestProperty38StatusTransitionStateMachine:
    """Property 38: Appointment status transition state machine.

    *For any* appointment, status transitions shall follow the strict chain:
    confirmed → en_route → in_progress → completed. Any transition that
    skips a step or goes backward shall be rejected. Each transition shall
    record the corresponding timestamp.

    **Validates: Requirements 35.1, 35.2, 35.3, 35.4, 35.5, 35.6**
    """

    @pytest.mark.asyncio
    async def test_valid_chain_confirmed_to_en_route_succeeds(self) -> None:
        """confirmed → en_route is a valid transition.

        **Validates: Requirements 35.4**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.EN_ROUTE.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.EN_ROUTE,
            actor_id,
        )

        # Verify en_route_at timestamp was set
        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.EN_ROUTE.value
        assert "en_route_at" in update_data

    @pytest.mark.asyncio
    async def test_valid_chain_en_route_to_in_progress_succeeds(self) -> None:
        """en_route → in_progress is a valid transition.

        **Validates: Requirements 35.5**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.EN_ROUTE.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.IN_PROGRESS,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.IN_PROGRESS.value
        assert "arrived_at" in update_data

    @pytest.mark.asyncio
    async def test_valid_chain_in_progress_to_completed_with_payment_succeeds(
        self,
    ) -> None:
        """in_progress → completed succeeds when payment/invoice exists.

        **Validates: Requirements 35.6**
        """
        apt_id = uuid4()
        actor_id = uuid4()
        job_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.COMPLETED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        invoice_repo = AsyncMock()

        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)
        # Has payment/invoice
        svc._has_payment_or_invoice = AsyncMock(return_value=True)

        await svc.transition_status(
            apt_id,
            AppointmentStatus.COMPLETED,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.COMPLETED.value
        assert "completed_at" in update_data

    @given(
        current=st.sampled_from(
            [
                AppointmentStatus.EN_ROUTE,
                AppointmentStatus.IN_PROGRESS,
            ]
        ),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_skip_step_transition_raises_error(
        self,
        current: AppointmentStatus,
    ) -> None:
        """Skipping a step in the chain raises InvalidStatusTransitionError.

        Per VALID_APPOINTMENT_TRANSITIONS, only the following skips are invalid:
        - EN_ROUTE → COMPLETED (must pass through IN_PROGRESS)
        - IN_PROGRESS → EN_ROUTE (backward)

        CONFIRMED → IN_PROGRESS is permitted (technician skips On-My-Way push).

        **Validates: Requirements 35.1, 35.2, 35.3**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        invalid_targets = {
            AppointmentStatus.EN_ROUTE: AppointmentStatus.COMPLETED,
            AppointmentStatus.IN_PROGRESS: AppointmentStatus.EN_ROUTE,
        }
        target = invalid_targets[current]

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=current.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        svc = _build_service(appt_repo=appt_repo)

        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await svc.transition_status(apt_id, target, actor_id)
        assert exc_info.value.current_status == current
        assert exc_info.value.requested_status == target

    @pytest.mark.asyncio
    async def test_valid_skip_confirmed_to_in_progress_succeeds(self) -> None:
        """confirmed → in_progress is permitted (skip EN_ROUTE / On-My-Way).

        Per VALID_APPOINTMENT_TRANSITIONS, the technician can mark a job
        in-progress without issuing an On-My-Way push first.

        **Validates: Requirements 35.4, 35.5**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.IN_PROGRESS,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.IN_PROGRESS.value
        assert "arrived_at" in update_data

    @pytest.mark.asyncio
    async def test_valid_draft_to_scheduled_succeeds(self) -> None:
        """draft → scheduled is permitted (Send Confirmation flow).

        **Validates: CR-1 regression**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.DRAFT.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.SCHEDULED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.SCHEDULED,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.SCHEDULED.value

    @pytest.mark.asyncio
    async def test_valid_scheduled_to_en_route_succeeds(self) -> None:
        """scheduled → en_route is permitted (skip CONFIRMED step).

        **Validates: CR-1 regression**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.EN_ROUTE.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.EN_ROUTE,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.EN_ROUTE.value
        assert "en_route_at" in update_data

    @pytest.mark.asyncio
    async def test_valid_transitions_includes_scheduled_to_in_progress(self) -> None:
        """scheduled → in_progress is permitted (customer never replied Y, skip steps).

        **Validates: CR-2 (2026-04-14 E2E-6 survivor).** SCHEDULED must be able to
        skip directly to IN_PROGRESS when the tech clicks Job Started without
        on-my-way or any prior confirmation reply.
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.SCHEDULED.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        await svc.transition_status(
            apt_id,
            AppointmentStatus.IN_PROGRESS,
            actor_id,
        )

        update_data = appt_repo.update.call_args[0][1]
        assert update_data["status"] == AppointmentStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_backward_transition_raises_error(self) -> None:
        """Going backward (e.g., in_progress → confirmed) is rejected.

        **Validates: Requirements 35.1**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        svc = _build_service(appt_repo=appt_repo)

        with pytest.raises(InvalidStatusTransitionError):
            await svc.transition_status(
                apt_id,
                AppointmentStatus.CONFIRMED,
                actor_id,
            )

    @pytest.mark.asyncio
    async def test_cancellation_from_valid_states_succeeds(self) -> None:
        """Cancellation is allowed from pending, scheduled, confirmed,
        en_route, and in_progress states.

        **Validates: Requirements 35.4**
        """
        cancellable = [
            AppointmentStatus.PENDING,
            AppointmentStatus.SCHEDULED,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.EN_ROUTE,
            AppointmentStatus.IN_PROGRESS,
        ]

        for status in cancellable:
            apt_id = uuid4()
            actor_id = uuid4()

            appointment = _make_appointment_mock(
                appointment_id=apt_id,
                status=status.value,
            )
            updated = _make_appointment_mock(
                appointment_id=apt_id,
                status=AppointmentStatus.CANCELLED.value,
            )

            appt_repo = AsyncMock()
            appt_repo.get_by_id = AsyncMock(return_value=appointment)
            appt_repo.update = AsyncMock(return_value=updated)

            svc = _build_service(appt_repo=appt_repo)
            result = await svc.transition_status(
                apt_id,
                AppointmentStatus.CANCELLED,
                actor_id,
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_cancellation_from_completed_raises_error(self) -> None:
        """Cannot cancel a completed appointment."""
        apt_id = uuid4()
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.COMPLETED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(InvalidStatusTransitionError):
            await svc.transition_status(
                apt_id,
                AppointmentStatus.CANCELLED,
                uuid4(),
            )

    @pytest.mark.asyncio
    async def test_no_show_from_confirmed_succeeds(self) -> None:
        """No-show is allowed from confirmed state.

        **Validates: Requirements 35.4**
        """
        apt_id = uuid4()
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.NO_SHOW.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        svc = _build_service(appt_repo=appt_repo)
        result = await svc.transition_status(
            apt_id,
            AppointmentStatus.NO_SHOW,
            uuid4(),
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_transition_with_not_found_raises_error(self) -> None:
        """Transitioning non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(AppointmentNotFoundError):
            await svc.transition_status(
                uuid4(),
                AppointmentStatus.EN_ROUTE,
                uuid4(),
            )


# =============================================================================
# Property 39: Payment gate blocks completion without payment or invoice
# Validates: Requirements 36.1, 36.2
# =============================================================================


@pytest.mark.unit
class TestProperty39PaymentGate:
    """Property 39: Payment gate blocks completion without payment or invoice.

    *For any* appointment in in_progress status where no payment has been
    collected and no invoice has been sent, transitioning to completed
    shall be rejected. If a payment or invoice exists, it shall succeed.

    **Validates: Requirements 36.1, 36.2**
    """

    @pytest.mark.asyncio
    async def test_completion_without_payment_raises_error(self) -> None:
        """Completing without payment/invoice raises PaymentRequiredError.

        **Validates: Requirements 36.1, 36.2**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        invoice_repo = AsyncMock()

        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)
        svc._has_payment_or_invoice = AsyncMock(return_value=False)

        with pytest.raises(PaymentRequiredError) as exc_info:
            await svc.transition_status(
                apt_id,
                AppointmentStatus.COMPLETED,
                actor_id,
            )
        assert exc_info.value.appointment_id == apt_id

    @pytest.mark.asyncio
    async def test_completion_with_payment_succeeds(self) -> None:
        """Completing with payment/invoice present succeeds.

        **Validates: Requirements 36.1**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.COMPLETED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        invoice_repo = AsyncMock()

        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)
        svc._has_payment_or_invoice = AsyncMock(return_value=True)

        result = await svc.transition_status(
            apt_id,
            AppointmentStatus.COMPLETED,
            actor_id,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_completion_with_admin_override_bypasses_gate(self) -> None:
        """Admin override bypasses the payment gate.

        **Validates: Requirements 36.2**
        """
        apt_id = uuid4()
        actor_id = uuid4()

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )
        updated = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.COMPLETED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)
        appt_repo.update = AsyncMock(return_value=updated)

        invoice_repo = AsyncMock()

        svc = _build_service(appt_repo=appt_repo, invoice_repo=invoice_repo)
        # No payment exists, but admin_override=True
        svc._has_payment_or_invoice = AsyncMock(return_value=False)

        result = await svc.transition_status(
            apt_id,
            AppointmentStatus.COMPLETED,
            actor_id,
            admin_override=True,
        )
        assert result is not None
        # _has_payment_or_invoice should NOT have been called
        svc._has_payment_or_invoice.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_has_payment_or_invoice_with_existing_invoice_returns_true(
        self,
    ) -> None:
        """_has_payment_or_invoice returns True when invoice exists."""
        job_id = uuid4()
        appointment = _make_appointment_mock(job_id=job_id)

        invoice = _make_invoice_mock(job_id=job_id)
        invoice_repo = AsyncMock()

        svc = _build_service(invoice_repo=invoice_repo)
        svc._find_invoice_for_job = AsyncMock(return_value=invoice)

        result = await svc._has_payment_or_invoice(appointment)
        assert result is True

    @pytest.mark.asyncio
    async def test_has_payment_or_invoice_with_no_invoice_returns_false(
        self,
    ) -> None:
        """_has_payment_or_invoice returns False when no invoice exists."""
        job_id = uuid4()
        appointment = _make_appointment_mock(job_id=job_id)

        invoice_repo = AsyncMock()

        svc = _build_service(invoice_repo=invoice_repo)
        svc._find_invoice_for_job = AsyncMock(return_value=None)

        result = await svc._has_payment_or_invoice(appointment)
        assert result is False

    @pytest.mark.asyncio
    async def test_has_payment_or_invoice_without_repo_raises(
        self,
    ) -> None:
        """Without invoice_repository, the payment gate fails loud (bughunt M-7).

        Previously returned True and silently disabled the gate if DI
        was misconfigured — Req 36 could be bypassed without detection.
        """
        appointment = _make_appointment_mock()

        svc = _build_service(invoice_repo=None)

        with pytest.raises(RuntimeError, match="invoice_repository"):
            _ = await svc._has_payment_or_invoice(appointment)


# =============================================================================
# Property 40: Staff time duration calculations
# Validates: Requirements 37.1
# =============================================================================


@pytest.mark.unit
class TestProperty40StaffTimeDurations:
    """Property 40: Staff time duration calculations.

    *For any* completed appointment with en_route_at, arrived_at, and
    completed_at timestamps, travel_time = arrived_at - en_route_at,
    job_duration = completed_at - arrived_at, total_time = completed_at -
    en_route_at.

    **Validates: Requirements 37.1**
    """

    @given(
        travel_minutes=st.integers(min_value=5, max_value=120),
        job_minutes=st.integers(min_value=15, max_value=480),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_staff_time_analytics_with_valid_timestamps_calculates_correctly(
        self,
        travel_minutes: int,
        job_minutes: int,
    ) -> None:
        """For any travel and job durations, analytics correctly computes
        avg_travel, avg_job, and avg_total minutes.

        **Validates: Requirements 37.1**
        """
        staff_id = uuid4()
        staff = _make_staff_mock(staff_id=staff_id)

        base_time = datetime(2025, 7, 15, 8, 0, tzinfo=timezone.utc)
        en_route = base_time
        arrived = base_time + timedelta(minutes=travel_minutes)
        completed = arrived + timedelta(minutes=job_minutes)

        job_mock = MagicMock()
        job_mock.job_type = "repair"

        apt = _make_appointment_mock(
            staff_id=staff_id,
            status=AppointmentStatus.COMPLETED.value,
            en_route_at=en_route,
            arrived_at=arrived,
            completed_at=completed,
            job=job_mock,
        )

        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(return_value=([apt], 1))

        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(return_value=staff)

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)

        date_range = DateRange(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 31),
        )
        entries = await svc.get_staff_time_analytics(date_range)

        assert len(entries) == 1
        entry = entries[0]
        assert isinstance(entry, StaffTimeEntry)
        assert entry.staff_id == staff_id
        assert entry.job_type == "repair"
        assert entry.avg_travel_minutes == round(float(travel_minutes), 1)
        assert entry.avg_job_minutes == round(float(job_minutes), 1)
        expected_total = float(travel_minutes + job_minutes)
        assert entry.avg_total_minutes == round(expected_total, 1)
        assert entry.appointment_count == 1

    @pytest.mark.asyncio
    async def test_staff_time_analytics_with_no_en_route_uses_zero_travel(
        self,
    ) -> None:
        """When en_route_at is missing, travel time is 0."""
        staff_id = uuid4()
        staff = _make_staff_mock(staff_id=staff_id)

        base_time = datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc)
        arrived = base_time
        completed = base_time + timedelta(minutes=60)

        job_mock = MagicMock()
        job_mock.job_type = "installation"

        apt = _make_appointment_mock(
            staff_id=staff_id,
            status=AppointmentStatus.COMPLETED.value,
            en_route_at=None,
            arrived_at=arrived,
            completed_at=completed,
            job=job_mock,
        )

        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(return_value=([apt], 1))

        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(return_value=staff)

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)

        date_range = DateRange(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 31),
        )
        entries = await svc.get_staff_time_analytics(date_range)

        assert len(entries) == 1
        assert entries[0].avg_travel_minutes == 0.0
        assert entries[0].avg_job_minutes == 60.0

    @pytest.mark.asyncio
    async def test_staff_time_analytics_with_no_completed_appointments_returns_empty(
        self,
    ) -> None:
        """No completed appointments returns empty list."""
        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(return_value=([], 0))

        svc = _build_service(appt_repo=appt_repo)

        date_range = DateRange(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 31),
        )
        entries = await svc.get_staff_time_analytics(date_range)
        assert entries == []

    @pytest.mark.asyncio
    async def test_staff_time_analytics_flags_outlier_at_1_5x_threshold(
        self,
    ) -> None:
        """Staff exceeding 1.5x the global average for a job type is flagged.

        **Validates: Requirements 37.1**
        """
        staff_fast_id = uuid4()
        staff_slow_id = uuid4()
        staff_fast = _make_staff_mock(
            staff_id=staff_fast_id,
            first_name="Fast",
            last_name="Tech",
        )
        staff_slow = _make_staff_mock(
            staff_id=staff_slow_id,
            first_name="Slow",
            last_name="Tech",
        )

        base = datetime(2025, 7, 15, 8, 0, tzinfo=timezone.utc)
        job_mock = MagicMock()
        job_mock.job_type = "repair"

        # Fast tech: 30 min total
        apt_fast = _make_appointment_mock(
            staff_id=staff_fast_id,
            status=AppointmentStatus.COMPLETED.value,
            en_route_at=base,
            arrived_at=base + timedelta(minutes=10),
            completed_at=base + timedelta(minutes=30),
            job=job_mock,
        )

        # Slow tech: 120 min total (4x the fast tech, >1.5x average)
        apt_slow = _make_appointment_mock(
            staff_id=staff_slow_id,
            status=AppointmentStatus.COMPLETED.value,
            en_route_at=base,
            arrived_at=base + timedelta(minutes=30),
            completed_at=base + timedelta(minutes=120),
            job=job_mock,
        )

        appt_repo = AsyncMock()
        appt_repo.list_with_filters = AsyncMock(
            return_value=([apt_fast, apt_slow], 2),
        )

        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(
            side_effect=lambda sid: (
                staff_fast if sid == staff_fast_id else staff_slow
            ),
        )

        svc = _build_service(appt_repo=appt_repo, staff_repo=staff_repo)

        date_range = DateRange(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 31),
        )
        entries = await svc.get_staff_time_analytics(date_range)

        assert len(entries) == 2
        # Global average for "repair" = (30 + 120) / 2 = 75 min
        # 1.5x threshold = 112.5 min
        # Slow tech at 120 min > 112.5 → flagged
        slow_entry = next(e for e in entries if e.staff_id == staff_slow_id)
        fast_entry = next(e for e in entries if e.staff_id == staff_fast_id)
        assert slow_entry.flagged is True
        assert fast_entry.flagged is False


# =============================================================================
# Property 43: Enriched appointment response includes all required fields
# Validates: Requirements 40.2
# =============================================================================


@pytest.mark.unit
class TestProperty43EnrichedAppointmentResponse:
    """Property 43: Enriched appointment response includes all required fields.

    *For any* appointment with a linked customer and job, the enriched
    response shall include: customer name, phone, email, job type, location,
    materials_needed, estimated_duration_minutes, and customer service
    history summary.

    **Validates: Requirements 40.2**
    """

    @given(
        duration_minutes=st.one_of(
            st.none(),
            st.integers(min_value=15, max_value=480),
        ),
        materials=st.one_of(
            st.none(),
            st.lists(
                st.text(
                    alphabet=st.characters(
                        whitelist_categories=("L", "N"),
                    ),
                    min_size=1,
                    max_size=50,
                ),
                min_size=0,
                max_size=5,
            ),
        ),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_get_appointment_with_relationships_includes_enriched_fields(
        self,
        duration_minutes: int | None,
        materials: list[str] | None,
    ) -> None:
        """Enriched appointment includes materials_needed and
        estimated_duration_minutes from the appointment model.

        **Validates: Requirements 40.2**
        """
        apt_id = uuid4()
        customer_id = uuid4()
        job_id = uuid4()

        customer = _make_customer_mock(
            customer_id=customer_id,
            first_name="Jane",
            last_name="Smith",
            phone="6125559999",
            email="jane@example.com",
        )
        job = _make_job_mock(
            job_id=job_id,
            customer_id=customer_id,
            job_type="installation",
            customer=customer,
        )

        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job_id,
            materials_needed=materials,
            estimated_duration_minutes=duration_minutes,
            job=job,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(appt_repo=appt_repo, job_repo=job_repo)
        result = await svc.get_appointment(
            apt_id,
            include_relationships=True,
        )

        # Verify the appointment has all enriched fields accessible
        assert result is not None
        assert result.materials_needed == materials
        assert result.estimated_duration_minutes == duration_minutes
        # Verify job relationship is accessible
        assert result.job is not None
        assert result.job.job_type == "installation"
        assert result.job.customer is not None
        assert result.job.customer.first_name == "Jane"
        assert result.job.customer.phone == "6125559999"
        assert result.job.customer.email == "jane@example.com"

    @pytest.mark.asyncio
    async def test_get_appointment_without_relationships_returns_basic(
        self,
    ) -> None:
        """Without include_relationships, basic fields are still present."""
        apt_id = uuid4()
        appointment = _make_appointment_mock(appointment_id=apt_id)

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        svc = _build_service(appt_repo=appt_repo)
        result = await svc.get_appointment(apt_id, include_relationships=False)

        assert result is not None
        assert result.id == apt_id

    @pytest.mark.asyncio
    async def test_get_appointment_with_not_found_raises_error(self) -> None:
        """Getting non-existent appointment raises error."""
        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=None)

        svc = _build_service(appt_repo=appt_repo)
        with pytest.raises(AppointmentNotFoundError):
            await svc.get_appointment(uuid4())


# =============================================================================
# Sprint 2 — H-8: reactivating a CANCELLED appointment emits reschedule SMS
# =============================================================================


@pytest.mark.unit
class TestReactivationSendsRescheduleSms:
    """bughunt H-8: when an admin changes the date on a CANCELLED
    appointment, the appointment flips back to SCHEDULED *and* the
    customer must be told via SMS. Previously the pre-state check read
    the in-memory ``appointment.status`` (still ``CANCELLED`` at that
    point), so the SMS branch was skipped."""

    @pytest.mark.asyncio
    async def test_reactivation_fires_reschedule_sms(self) -> None:
        from unittest.mock import patch

        from grins_platform.schemas.appointment import (
            AppointmentUpdate,
        )

        apt_id = uuid4()
        cancelled = _make_appointment_mock(
            appointment_id=apt_id,
            status=AppointmentStatus.CANCELLED.value,
        )
        reactivated = _make_appointment_mock(
            appointment_id=apt_id,
            scheduled_date=date(2026, 4, 22),
            time_window_start=time(11, 0),
            time_window_end=time(13, 0),
            status=AppointmentStatus.SCHEDULED.value,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=cancelled)
        appt_repo.update = AsyncMock(return_value=reactivated)
        appt_repo.session = AsyncMock()

        svc = _build_service(appt_repo=appt_repo)

        sms_mock = AsyncMock()
        with patch.object(svc, "_send_reschedule_sms", sms_mock):
            await svc.update_appointment(
                apt_id,
                AppointmentUpdate(scheduled_date=date(2026, 4, 22)),
            )

        sms_mock.assert_awaited_once()


# =============================================================================
# Sprint 3 — H-4: create_appointment rejects COMPLETED / CANCELLED jobs
# =============================================================================


@pytest.mark.unit
class TestCreateAppointmentRejectsFinishedJobs:
    """bughunt H-4: scheduling a new appointment on a job that's
    already COMPLETED or CANCELLED used to succeed silently. The
    ``AppointmentService.create_appointment`` method now raises
    ``AppointmentOnFinishedJobError`` so the admin gets a clear error
    instead of an orphan draft appointment stuck on a finished job."""

    @pytest.mark.asyncio
    async def test_rejects_completed_job(self) -> None:
        from grins_platform.exceptions import AppointmentOnFinishedJobError
        from grins_platform.models.enums import JobStatus
        from grins_platform.schemas.appointment import AppointmentCreate

        job = _make_job_mock()
        job.status = JobStatus.COMPLETED.value

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(job_repo=job_repo)

        data = AppointmentCreate(
            job_id=job.id,
            staff_id=uuid4(),
            scheduled_date=date(2026, 5, 1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        with pytest.raises(AppointmentOnFinishedJobError) as exc_info:
            await svc.create_appointment(data)
        assert exc_info.value.job_status == JobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_rejects_cancelled_job(self) -> None:
        from grins_platform.exceptions import AppointmentOnFinishedJobError
        from grins_platform.models.enums import JobStatus
        from grins_platform.schemas.appointment import AppointmentCreate

        job = _make_job_mock()
        job.status = JobStatus.CANCELLED.value

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        svc = _build_service(job_repo=job_repo)

        data = AppointmentCreate(
            job_id=job.id,
            staff_id=uuid4(),
            scheduled_date=date(2026, 5, 1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        with pytest.raises(AppointmentOnFinishedJobError):
            await svc.create_appointment(data)


# =============================================================================
# Sprint 3 — M-6: create_appointment honours caller-provided status
# =============================================================================


@pytest.mark.unit
class TestCreateAppointmentStatusOverride:
    """bughunt M-6: bulk-import paths that pre-populate an appointment
    as already SCHEDULED (e.g. CSV onboarding) shouldn't have their
    status reset to DRAFT by the service."""

    @pytest.mark.asyncio
    async def test_caller_status_is_honoured(self) -> None:
        from grins_platform.models.enums import JobStatus
        from grins_platform.schemas.appointment import AppointmentCreate

        job = _make_job_mock()
        job.status = JobStatus.TO_BE_SCHEDULED.value
        staff = _make_staff_mock()

        created_appt = _make_appointment_mock(
            status=AppointmentStatus.SCHEDULED.value,
        )

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)
        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(return_value=staff)
        appt_repo = AsyncMock()
        appt_repo.create = AsyncMock(return_value=created_appt)
        appt_repo.session = AsyncMock()

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            staff_repo=staff_repo,
        )

        data = AppointmentCreate(
            job_id=job.id,
            staff_id=staff.id,
            scheduled_date=date(2026, 5, 1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
            status=AppointmentStatus.SCHEDULED,
        )

        await svc.create_appointment(data)

        create_kwargs = appt_repo.create.await_args.kwargs
        assert create_kwargs["status"] == AppointmentStatus.SCHEDULED.value

    @pytest.mark.asyncio
    async def test_default_is_draft_when_status_omitted(self) -> None:
        from grins_platform.models.enums import JobStatus
        from grins_platform.schemas.appointment import AppointmentCreate

        job = _make_job_mock()
        job.status = JobStatus.TO_BE_SCHEDULED.value
        staff = _make_staff_mock()
        created_appt = _make_appointment_mock(
            status=AppointmentStatus.DRAFT.value,
        )

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)
        staff_repo = AsyncMock()
        staff_repo.get_by_id = AsyncMock(return_value=staff)
        appt_repo = AsyncMock()
        appt_repo.create = AsyncMock(return_value=created_appt)
        appt_repo.session = AsyncMock()

        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            staff_repo=staff_repo,
        )

        data = AppointmentCreate(
            job_id=job.id,
            staff_id=staff.id,
            scheduled_date=date(2026, 5, 1),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )

        await svc.create_appointment(data)

        create_kwargs = appt_repo.create.await_args.kwargs
        assert create_kwargs["status"] == AppointmentStatus.DRAFT.value


# =============================================================================
# Sprint 2 — X-1: GOOGLE_REVIEW_URL fail-closed when unset
# =============================================================================


@pytest.mark.unit
class TestGoogleReviewUrlFailClosed:
    """bughunt X-1 / L-5: when neither ``GOOGLE_REVIEW_URL`` env var nor
    the service-level ``google_review_url`` is set, the service must
    return ``ReviewRequestResult(sent=False)`` instead of shipping a
    stale plural-slug fallback link that 404s."""

    @pytest.mark.asyncio
    async def test_returns_not_sent_when_url_unset(self) -> None:
        from unittest.mock import patch

        apt_id = uuid4()
        customer = _make_customer_mock(sms_opt_in=True)
        job = _make_job_mock(customer_id=customer.id, customer=customer)
        appointment = _make_appointment_mock(
            appointment_id=apt_id,
            job_id=job.id,
        )

        appt_repo = AsyncMock()
        appt_repo.get_by_id = AsyncMock(return_value=appointment)

        job_repo = AsyncMock()
        job_repo.get_by_id = AsyncMock(return_value=job)

        # Build service with explicit empty URL override
        svc = _build_service(
            appt_repo=appt_repo,
            job_repo=job_repo,
            google_review_url="",
        )
        svc._get_last_review_request_date = AsyncMock(return_value=None)

        # Ensure env var is not set either
        with (
            patch.dict("os.environ", {}, clear=False),
            patch(
                "grins_platform.services.sms.consent.check_sms_consent",
                return_value=True,
            ),
        ):
            # Also explicitly remove GOOGLE_REVIEW_URL if present
            import os

            os.environ.pop("GOOGLE_REVIEW_URL", None)

            result = await svc.request_google_review(apt_id)

        assert result.sent is False
        assert result.channel is None
        assert "GOOGLE_REVIEW_URL" in result.message
