"""Functional tests for appointment and schedule operations.

Tests appointment rescheduling, payment collection, invoice creation,
estimate creation from appointments, photo uploads, and the full
status transition chain with mocked repositories and external services.

Validates: Requirements 24.7, 30.8, 31.7, 32.9, 33.7, 35.9
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    AppointmentNotFoundError,
    InvalidStatusTransitionError,
    PaymentRequiredError,
    StaffConflictError,
)
from grins_platform.models.enums import (
    AppointmentStatus,
    InvoiceStatus,
    PaymentMethod,
)
from grins_platform.schemas.appointment_ops import PaymentCollectionRequest
from grins_platform.schemas.estimate import EstimateCreate
from grins_platform.services.appointment_service import AppointmentService

# =============================================================================
# Helpers
# =============================================================================


def _make_appointment(**overrides: Any) -> MagicMock:
    """Create a mock Appointment with all fields."""
    apt = MagicMock()
    apt.id = overrides.get("id", uuid4())
    apt.job_id = overrides.get("job_id", uuid4())
    apt.staff_id = overrides.get("staff_id", uuid4())
    apt.scheduled_date = overrides.get("scheduled_date", date(2025, 3, 15))
    apt.time_window_start = overrides.get("time_window_start", time(9, 0))
    apt.time_window_end = overrides.get("time_window_end", time(11, 0))
    apt.status = overrides.get("status", AppointmentStatus.SCHEDULED.value)
    apt.notes = overrides.get("notes")
    apt.en_route_at = overrides.get("en_route_at")
    apt.arrived_at = overrides.get("arrived_at")
    apt.completed_at = overrides.get("completed_at")
    apt.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    apt.updated_at = datetime.now(tz=timezone.utc)
    return apt


def _make_job(**overrides: Any) -> MagicMock:
    """Create a mock Job."""
    job = MagicMock()
    job.id = overrides.get("id", uuid4())
    job.customer_id = overrides.get("customer_id", uuid4())
    job.job_type = overrides.get("job_type", "spring_startup")
    job.quoted_amount = overrides.get("quoted_amount", Decimal("250.00"))
    job.final_amount = overrides.get("final_amount")
    job.customer = overrides.get("customer")
    return job


def _make_invoice(**overrides: Any) -> MagicMock:
    """Create a mock Invoice."""
    inv = MagicMock()
    inv.id = overrides.get("id", uuid4())
    inv.job_id = overrides.get("job_id", uuid4())
    inv.customer_id = overrides.get("customer_id", uuid4())
    inv.invoice_number = overrides.get("invoice_number", "INV-2025-0001")
    inv.amount = overrides.get("amount", Decimal("250.00"))
    inv.total_amount = overrides.get("total_amount", Decimal("250.00"))
    inv.paid_amount = overrides.get("paid_amount", Decimal(0))
    inv.status = overrides.get("status", InvoiceStatus.SENT.value)
    inv.payment_method = overrides.get("payment_method")
    inv.created_at = overrides.get("created_at", datetime.now(tz=timezone.utc))
    return inv


def _make_customer(**overrides: Any) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.first_name = overrides.get("first_name", "Jane")
    c.last_name = overrides.get("last_name", "Smith")
    c.phone = overrides.get("phone", "5125551234")
    c.email = overrides.get("email", "jane@example.com")
    c.internal_notes = overrides.get("internal_notes")
    c.sms_opt_in = overrides.get("sms_opt_in", True)
    return c



def _build_appointment_service(
    *,
    appt_repo: AsyncMock | None = None,
    job_repo: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    invoice_repo: AsyncMock | None = None,
    estimate_service: AsyncMock | None = None,
) -> tuple[AppointmentService, AsyncMock, AsyncMock, AsyncMock]:
    """Build an AppointmentService with mocked dependencies.

    Returns (service, appointment_repo, job_repo, invoice_repo).
    """
    appointment_repo = appt_repo or AsyncMock()
    job_repository = job_repo or AsyncMock()
    staff_repository = staff_repo or AsyncMock()
    invoice_repository = invoice_repo or AsyncMock()
    est_svc = estimate_service or AsyncMock()

    svc = AppointmentService(
        appointment_repository=appointment_repo,
        job_repository=job_repository,
        staff_repository=staff_repository,
        invoice_repository=invoice_repository,
        estimate_service=est_svc,
        google_review_url="https://g.page/grins-irrigation/review",
    )
    return svc, appointment_repo, job_repository, invoice_repository


# =============================================================================
# 1. Appointment Time Update via PATCH (Reschedule)
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAppointmentRescheduleWorkflow:
    """Test appointment rescheduling via drag-drop as user would experience.

    Validates: Requirement 24.7
    """

    async def test_reschedule_appointment_updates_time_as_user_would_experience(
        self,
    ) -> None:
        """Dragging an appointment to a new slot updates date and time."""
        svc, appt_repo, _job_repo, _ = _build_appointment_service()

        staff_id = uuid4()
        apt = _make_appointment(
            staff_id=staff_id,
            scheduled_date=date(2025, 3, 15),
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )
        appt_repo.get_by_id.return_value = apt

        # No conflicts — empty schedule for the new date
        appt_repo.get_staff_daily_schedule.return_value = []

        updated_apt = _make_appointment(
            id=apt.id,
            staff_id=staff_id,
            scheduled_date=date(2025, 3, 17),
            time_window_start=time(13, 0),
            time_window_end=time(15, 0),
        )
        appt_repo.update.return_value = updated_apt

        result = await svc.reschedule(
            appointment_id=apt.id,
            new_date=date(2025, 3, 17),
            new_start=time(13, 0),
            new_end=time(15, 0),
        )

        assert result.scheduled_date == date(2025, 3, 17)
        assert result.time_window_start == time(13, 0)
        assert result.time_window_end == time(15, 0)

        # Verify update was called with correct data
        appt_repo.update.assert_called_once_with(
            apt.id,
            {
                "scheduled_date": date(2025, 3, 17),
                "time_window_start": time(13, 0),
                "time_window_end": time(15, 0),
            },
        )

    async def test_reschedule_rejects_staff_conflict_as_user_would_experience(
        self,
    ) -> None:
        """Dragging to a slot with an existing appointment shows conflict error."""
        svc, appt_repo, _, _ = _build_appointment_service()

        staff_id = uuid4()
        apt = _make_appointment(staff_id=staff_id)
        appt_repo.get_by_id.return_value = apt

        # Existing appointment at the target time
        conflicting = _make_appointment(
            staff_id=staff_id,
            scheduled_date=date(2025, 3, 17),
            time_window_start=time(12, 0),
            time_window_end=time(14, 0),
            status=AppointmentStatus.CONFIRMED.value,
        )
        appt_repo.get_staff_daily_schedule.return_value = [conflicting]

        with pytest.raises(StaffConflictError):
            await svc.reschedule(
                appointment_id=apt.id,
                new_date=date(2025, 3, 17),
                new_start=time(13, 0),
                new_end=time(15, 0),
            )

    async def test_reschedule_nonexistent_appointment_raises_error(
        self,
    ) -> None:
        """Rescheduling a non-existent appointment raises not found."""
        svc, appt_repo, _, _ = _build_appointment_service()
        appt_repo.get_by_id.return_value = None

        with pytest.raises(AppointmentNotFoundError):
            await svc.reschedule(
                appointment_id=uuid4(),
                new_date=date(2025, 3, 17),
                new_start=time(13, 0),
                new_end=time(15, 0),
            )


# =============================================================================
# 2. Payment Collection → Invoice Updated → Customer History
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestPaymentCollectionWorkflow:
    """Test full payment collection flow as user would experience.

    Collect payment → invoice created/updated → customer payment history.

    Validates: Requirement 30.8
    """

    async def test_collect_payment_creates_invoice_as_user_would_experience(
        self,
    ) -> None:
        """Collecting payment on-site creates a new invoice when none exists."""
        svc, appt_repo, job_repo, inv_repo = _build_appointment_service()

        customer_id = uuid4()
        job = _make_job(customer_id=customer_id, job_type="spring_startup")
        apt = _make_appointment(
            job_id=job.id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job
        inv_repo.get_next_sequence.return_value = 1

        new_invoice = _make_invoice(
            job_id=job.id,
            customer_id=customer_id,
            invoice_number="INV-2025-0001",
            amount=Decimal("150.00"),
            total_amount=Decimal("150.00"),
            status=InvoiceStatus.PAID.value,
        )
        inv_repo.create.return_value = new_invoice
        inv_repo.update.return_value = new_invoice

        # Mock _find_invoice_for_job to return None (no existing invoice)
        svc._find_invoice_for_job = AsyncMock(return_value=None)  # type: ignore[method-assign]

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("150.00"),
            reference_number=None,
        )

        result = await svc.collect_payment(apt.id, payment)

        assert result.amount_paid == Decimal("150.00")
        assert result.payment_method == PaymentMethod.CASH.value
        assert result.invoice_id == new_invoice.id

        # Verify invoice was created
        inv_repo.create.assert_called_once()
        create_kwargs = inv_repo.create.call_args.kwargs
        assert create_kwargs["customer_id"] == customer_id
        assert create_kwargs["job_id"] == job.id

    async def test_collect_payment_updates_existing_invoice_as_user_would_experience(
        self,
    ) -> None:
        """Collecting payment updates an existing invoice with partial payment."""
        svc, appt_repo, job_repo, inv_repo = _build_appointment_service()

        customer_id = uuid4()
        job = _make_job(customer_id=customer_id)
        apt = _make_appointment(
            job_id=job.id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        existing_invoice = _make_invoice(
            job_id=job.id,
            customer_id=customer_id,
            total_amount=Decimal("250.00"),
            paid_amount=Decimal("100.00"),
            status=InvoiceStatus.PARTIAL.value,
        )

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job

        # Existing invoice found
        svc._find_invoice_for_job = AsyncMock(return_value=existing_invoice)  # type: ignore[method-assign]

        updated_invoice = _make_invoice(
            id=existing_invoice.id,
            job_id=job.id,
            customer_id=customer_id,
            total_amount=Decimal("250.00"),
            paid_amount=Decimal("250.00"),
            status=InvoiceStatus.PAID.value,
        )
        inv_repo.update.return_value = updated_invoice

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CHECK,
            amount=Decimal("150.00"),
            reference_number="CHK-4567",
        )

        result = await svc.collect_payment(apt.id, payment)

        assert result.amount_paid == Decimal("150.00")
        assert result.payment_method == PaymentMethod.CHECK.value

        # Verify invoice was updated with new paid_amount
        inv_repo.update.assert_called_once()
        update_args = inv_repo.update.call_args
        update_data = update_args[0][1]
        assert update_data["paid_amount"] == Decimal("250.00")  # 100 + 150
        assert update_data["payment_method"] == PaymentMethod.CHECK.value
        assert update_data["payment_reference"] == "CHK-4567"
        assert update_data["status"] == InvoiceStatus.PAID.value

    async def test_collect_payment_nonexistent_appointment_raises_error(
        self,
    ) -> None:
        """Payment collection on non-existent appointment raises error."""
        svc, appt_repo, _, _ = _build_appointment_service()
        appt_repo.get_by_id.return_value = None

        payment = PaymentCollectionRequest(
            payment_method=PaymentMethod.CASH,
            amount=Decimal("100.00"),
        )

        with pytest.raises(AppointmentNotFoundError):
            await svc.collect_payment(uuid4(), payment)



# =============================================================================
# 3. Invoice Creation from Appointment
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestInvoiceFromAppointmentWorkflow:
    """Test invoice creation from appointment as user would experience.

    Invoice pre-populated from job/customer data, payment link generated.

    Validates: Requirement 31.7
    """

    async def test_create_invoice_from_appointment_as_user_would_experience(
        self,
    ) -> None:
        """Creating invoice from appointment pre-populates from job data."""
        svc, appt_repo, job_repo, inv_repo = _build_appointment_service()

        customer_id = uuid4()
        job = _make_job(
            customer_id=customer_id,
            job_type="fall_blowout",
            quoted_amount=Decimal("175.00"),
        )
        apt = _make_appointment(
            job_id=job.id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job
        inv_repo.get_next_sequence.return_value = 42

        created_invoice = _make_invoice(
            job_id=job.id,
            customer_id=customer_id,
            invoice_number="INV-2025-0042",
            amount=Decimal("175.00"),
            total_amount=Decimal("175.00"),
            status=InvoiceStatus.SENT.value,
        )
        inv_repo.create.return_value = created_invoice

        result = await svc.create_invoice_from_appointment(apt.id)

        assert result.id == created_invoice.id
        assert result.invoice_number == "INV-2025-0042"
        assert result.status == InvoiceStatus.SENT.value

        # Verify invoice was created with correct pre-populated data
        inv_repo.create.assert_called_once()
        create_kwargs = inv_repo.create.call_args.kwargs
        assert create_kwargs["job_id"] == job.id
        assert create_kwargs["customer_id"] == customer_id
        assert create_kwargs["amount"] == Decimal("175.00")
        assert create_kwargs["total_amount"] == Decimal("175.00")
        assert create_kwargs["status"] == InvoiceStatus.SENT.value
        assert "fall_blowout" in create_kwargs["line_items"][0]["description"]

    async def test_create_invoice_uses_final_amount_over_quoted(
        self,
    ) -> None:
        """Invoice uses final_amount when available instead of quoted_amount."""
        svc, appt_repo, job_repo, inv_repo = _build_appointment_service()

        customer_id = uuid4()
        job = _make_job(
            customer_id=customer_id,
            quoted_amount=Decimal("200.00"),
            final_amount=Decimal("275.00"),
        )
        apt = _make_appointment(job_id=job.id)

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job
        inv_repo.get_next_sequence.return_value = 1

        created_invoice = _make_invoice(
            amount=Decimal("275.00"),
            total_amount=Decimal("275.00"),
        )
        inv_repo.create.return_value = created_invoice

        await svc.create_invoice_from_appointment(apt.id)

        create_kwargs = inv_repo.create.call_args.kwargs
        assert create_kwargs["amount"] == Decimal("275.00")

    async def test_create_invoice_nonexistent_appointment_raises_error(
        self,
    ) -> None:
        """Invoice creation on non-existent appointment raises error."""
        svc, appt_repo, _, _ = _build_appointment_service()
        appt_repo.get_by_id.return_value = None

        with pytest.raises(AppointmentNotFoundError):
            await svc.create_invoice_from_appointment(uuid4())


# =============================================================================
# 4. Estimate Creation from Appointment
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimateFromAppointmentWorkflow:
    """Test estimate creation from appointment as user would experience.

    Estimate linked to appointment's job and customer, delegated to
    EstimateService.

    Validates: Requirement 32.9
    """

    async def test_create_estimate_from_appointment_as_user_would_experience(
        self,
    ) -> None:
        """Creating estimate from appointment links to job and customer."""
        estimate_svc = AsyncMock()
        svc, appt_repo, job_repo, _ = _build_appointment_service(
            estimate_service=estimate_svc,
        )

        customer_id = uuid4()
        job = _make_job(customer_id=customer_id, job_type="new_installation")
        apt = _make_appointment(
            job_id=job.id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job

        mock_estimate = MagicMock()
        mock_estimate.id = uuid4()
        mock_estimate.job_id = job.id
        mock_estimate.customer_id = customer_id
        estimate_svc.create_estimate.return_value = mock_estimate

        data = EstimateCreate(
            line_items=[
                {"item": "Drip System", "unit_price": "500.00", "quantity": "1"},
            ],
            tax_amount=Decimal("41.25"),
        )

        result = await svc.create_estimate_from_appointment(apt.id, data)

        assert result.id == mock_estimate.id  # type: ignore[attr-defined]

        # Verify data was enriched with job/customer IDs
        assert data.job_id == job.id
        assert data.customer_id == customer_id

        # Verify EstimateService was called
        estimate_svc.create_estimate.assert_called_once_with(data)

    async def test_create_estimate_without_estimate_service_raises_error(
        self,
    ) -> None:
        """Estimate creation without EstimateService configured raises error."""
        appt_repo = AsyncMock()
        job_repo = AsyncMock()
        staff_repo = AsyncMock()

        svc = AppointmentService(
            appointment_repository=appt_repo,
            job_repository=job_repo,
            staff_repository=staff_repo,
            invoice_repository=None,
            estimate_service=None,
        )

        apt = _make_appointment()
        appt_repo.get_by_id.return_value = apt

        data = EstimateCreate(
            line_items=[{"item": "Test", "unit_price": "10.00", "quantity": "1"}],
        )

        with pytest.raises(RuntimeError, match="EstimateService is required"):
            await svc.create_estimate_from_appointment(apt.id, data)

    async def test_create_estimate_nonexistent_appointment_raises_error(
        self,
    ) -> None:
        """Estimate creation on non-existent appointment raises error."""
        svc, appt_repo, _, _ = _build_appointment_service()
        appt_repo.get_by_id.return_value = None

        data = EstimateCreate(
            line_items=[{"item": "Test", "unit_price": "10.00", "quantity": "1"}],
        )

        with pytest.raises(AppointmentNotFoundError):
            await svc.create_estimate_from_appointment(uuid4(), data)


# =============================================================================
# 5. Photo Upload from Appointment Context
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAppointmentPhotoWorkflow:
    """Test photo upload from appointment links to both appointment and customer.

    Validates: Requirement 33.7
    """

    async def test_notes_and_photos_propagate_to_customer_as_user_would_experience(
        self,
    ) -> None:
        """Notes saved on appointment also append to customer internal_notes."""
        svc, appt_repo, job_repo, _ = _build_appointment_service()

        customer = _make_customer(internal_notes="Existing customer notes.")
        job = _make_job(customer_id=customer.id, customer=customer)
        apt = _make_appointment(
            job_id=job.id,
            status=AppointmentStatus.IN_PROGRESS.value,
        )

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job

        updated_apt = _make_appointment(
            id=apt.id,
            notes="Found broken sprinkler head in zone 3",
        )
        appt_repo.update.return_value = updated_apt

        result = await svc.add_notes_and_photos(
            appointment_id=apt.id,
            notes="Found broken sprinkler head in zone 3",
        )

        assert result.notes == "Found broken sprinkler head in zone 3"

        # Verify appointment was updated with notes
        appt_repo.update.assert_called_once()
        update_data = appt_repo.update.call_args[0][1]
        assert update_data["notes"] == "Found broken sprinkler head in zone 3"

        # Verify customer internal_notes was appended
        assert "Existing customer notes." in customer.internal_notes
        assert "Found broken sprinkler head in zone 3" in customer.internal_notes
        assert "Appointment note:" in customer.internal_notes

    async def test_notes_create_customer_notes_when_none_exist(
        self,
    ) -> None:
        """Notes append to customer even when no existing notes."""
        svc, appt_repo, job_repo, _ = _build_appointment_service()

        customer = _make_customer(internal_notes=None)
        job = _make_job(customer_id=customer.id, customer=customer)
        apt = _make_appointment(job_id=job.id)

        appt_repo.get_by_id.return_value = apt
        job_repo.get_by_id.return_value = job
        appt_repo.update.return_value = apt

        await svc.add_notes_and_photos(
            appointment_id=apt.id,
            notes="New system looks good",
        )

        assert customer.internal_notes is not None
        assert "New system looks good" in customer.internal_notes

    async def test_notes_nonexistent_appointment_raises_error(
        self,
    ) -> None:
        """Adding notes to non-existent appointment raises error."""
        svc, appt_repo, _, _ = _build_appointment_service()
        appt_repo.get_by_id.return_value = None

        with pytest.raises(AppointmentNotFoundError):
            await svc.add_notes_and_photos(
                appointment_id=uuid4(),
                notes="Some notes",
            )



# =============================================================================
# 6. Full Status Transition Chain with Timestamp Recording
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestStatusTransitionChainWorkflow:
    """Test full status transition chain as user would experience.

    confirmed → en_route → in_progress → completed with timestamps.

    Validates: Requirement 35.9
    """

    async def test_full_transition_chain_with_timestamps_as_user_would_experience(
        self,
    ) -> None:
        """Full chain: confirmed → en_route → in_progress → completed."""
        svc, appt_repo, _job_repo, _inv_repo = _build_appointment_service()

        staff_id = uuid4()
        actor_id = uuid4()
        apt_id = uuid4()

        # Start at CONFIRMED
        apt = _make_appointment(
            id=apt_id,
            staff_id=staff_id,
            status=AppointmentStatus.CONFIRMED.value,
        )
        appt_repo.get_by_id.return_value = apt

        # --- Step 1: "On My Way" → EN_ROUTE ---
        en_route_apt = _make_appointment(
            id=apt_id,
            status=AppointmentStatus.EN_ROUTE.value,
            en_route_at=datetime.now(tz=timezone.utc),
        )
        appt_repo.update.return_value = en_route_apt

        result1 = await svc.transition_status(
            appointment_id=apt_id,
            new_status=AppointmentStatus.EN_ROUTE,
            actor_id=actor_id,
        )

        assert result1.status == AppointmentStatus.EN_ROUTE.value
        assert result1.en_route_at is not None

        # Verify update was called with en_route_at timestamp
        update_data_1 = appt_repo.update.call_args[0][1]
        assert update_data_1["status"] == AppointmentStatus.EN_ROUTE.value
        assert "en_route_at" in update_data_1

        # --- Step 2: "Job Started" → IN_PROGRESS ---
        apt.status = AppointmentStatus.EN_ROUTE.value
        appt_repo.get_by_id.return_value = apt

        in_progress_apt = _make_appointment(
            id=apt_id,
            status=AppointmentStatus.IN_PROGRESS.value,
            en_route_at=en_route_apt.en_route_at,
            arrived_at=datetime.now(tz=timezone.utc),
        )
        appt_repo.update.return_value = in_progress_apt

        result2 = await svc.transition_status(
            appointment_id=apt_id,
            new_status=AppointmentStatus.IN_PROGRESS,
            actor_id=actor_id,
        )

        assert result2.status == AppointmentStatus.IN_PROGRESS.value
        assert result2.arrived_at is not None

        update_data_2 = appt_repo.update.call_args[0][1]
        assert update_data_2["status"] == AppointmentStatus.IN_PROGRESS.value
        assert "arrived_at" in update_data_2

        # --- Step 3: "Job Complete" → COMPLETED (with payment gate) ---
        apt.status = AppointmentStatus.IN_PROGRESS.value
        appt_repo.get_by_id.return_value = apt

        # Mock payment check — invoice exists
        svc._has_payment_or_invoice = AsyncMock(return_value=True)  # type: ignore[method-assign]

        completed_apt = _make_appointment(
            id=apt_id,
            status=AppointmentStatus.COMPLETED.value,
            en_route_at=en_route_apt.en_route_at,
            arrived_at=in_progress_apt.arrived_at,
            completed_at=datetime.now(tz=timezone.utc),
        )
        appt_repo.update.return_value = completed_apt

        result3 = await svc.transition_status(
            appointment_id=apt_id,
            new_status=AppointmentStatus.COMPLETED,
            actor_id=actor_id,
        )

        assert result3.status == AppointmentStatus.COMPLETED.value
        assert result3.completed_at is not None

        update_data_3 = appt_repo.update.call_args[0][1]
        assert update_data_3["status"] == AppointmentStatus.COMPLETED.value
        assert "completed_at" in update_data_3

    async def test_invalid_transition_skipping_en_route_raises_error(
        self,
    ) -> None:
        """Skipping en_route (confirmed → in_progress) is rejected."""
        svc, appt_repo, _, _ = _build_appointment_service()

        apt = _make_appointment(status=AppointmentStatus.CONFIRMED.value)
        appt_repo.get_by_id.return_value = apt

        with pytest.raises(InvalidStatusTransitionError):
            await svc.transition_status(
                appointment_id=apt.id,
                new_status=AppointmentStatus.IN_PROGRESS,
                actor_id=uuid4(),
            )

    async def test_completion_blocked_without_payment_raises_error(
        self,
    ) -> None:
        """Completing without payment or invoice raises PaymentRequiredError."""
        svc, appt_repo, _, _ = _build_appointment_service()

        apt = _make_appointment(status=AppointmentStatus.IN_PROGRESS.value)
        appt_repo.get_by_id.return_value = apt

        # No payment or invoice
        svc._has_payment_or_invoice = AsyncMock(return_value=False)  # type: ignore[method-assign]

        with pytest.raises(PaymentRequiredError):
            await svc.transition_status(
                appointment_id=apt.id,
                new_status=AppointmentStatus.COMPLETED,
                actor_id=uuid4(),
            )

    async def test_completion_with_admin_override_bypasses_payment_gate(
        self,
    ) -> None:
        """Admin override allows completion without payment."""
        svc, appt_repo, _, _ = _build_appointment_service()

        apt = _make_appointment(status=AppointmentStatus.IN_PROGRESS.value)
        appt_repo.get_by_id.return_value = apt

        # No payment — but admin override
        svc._has_payment_or_invoice = AsyncMock(return_value=False)  # type: ignore[method-assign]

        completed_apt = _make_appointment(
            id=apt.id,
            status=AppointmentStatus.COMPLETED.value,
            completed_at=datetime.now(tz=timezone.utc),
        )
        appt_repo.update.return_value = completed_apt

        result = await svc.transition_status(
            appointment_id=apt.id,
            new_status=AppointmentStatus.COMPLETED,
            actor_id=uuid4(),
            admin_override=True,
        )

        assert result.status == AppointmentStatus.COMPLETED.value

    async def test_cancellation_from_confirmed_status_succeeds(
        self,
    ) -> None:
        """Cancellation is allowed from confirmed status."""
        svc, appt_repo, _, _ = _build_appointment_service()

        apt = _make_appointment(status=AppointmentStatus.CONFIRMED.value)
        appt_repo.get_by_id.return_value = apt

        cancelled_apt = _make_appointment(
            id=apt.id,
            status=AppointmentStatus.CANCELLED.value,
        )
        appt_repo.update.return_value = cancelled_apt

        result = await svc.transition_status(
            appointment_id=apt.id,
            new_status=AppointmentStatus.CANCELLED,
            actor_id=uuid4(),
        )

        assert result.status == AppointmentStatus.CANCELLED.value

    async def test_no_show_from_confirmed_status_succeeds(
        self,
    ) -> None:
        """No-show is allowed from confirmed status."""
        svc, appt_repo, _, _ = _build_appointment_service()

        apt = _make_appointment(status=AppointmentStatus.CONFIRMED.value)
        appt_repo.get_by_id.return_value = apt

        no_show_apt = _make_appointment(
            id=apt.id,
            status=AppointmentStatus.NO_SHOW.value,
        )
        appt_repo.update.return_value = no_show_apt

        result = await svc.transition_status(
            appointment_id=apt.id,
            new_status=AppointmentStatus.NO_SHOW,
            actor_id=uuid4(),
        )

        assert result.status == AppointmentStatus.NO_SHOW.value
