"""Unit tests for InvoiceService.

Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7
Property 5: Invoice Number Uniqueness
Property 6: Payment Recording Correctness
Property 7: Lien Eligibility Determination
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import InvoiceStatus, PaymentMethod
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItem,
    InvoiceListParams,
    InvoiceUpdate,
    PaymentRecord,
)
from grins_platform.services.invoice_service import (
    LIEN_ELIGIBLE_TYPES,
    InvalidInvoiceOperationError,
    InvoiceNotFoundError,
    InvoiceService,
)


@pytest.mark.unit
class TestInvoiceServiceCreateInvoice:
    """Tests for InvoiceService.create_invoice method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_job(
        self,
        job_type: str = "seasonal",
        customer_id: str | None = None,
    ) -> MagicMock:
        """Create a mock job object."""
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = uuid4() if customer_id is None else customer_id
        job.job_type = job_type
        job.description = "Test job"
        job.quoted_amount = Decimal("150.00")
        job.final_amount = None
        job.is_deleted = False
        job.payment_collected_on_site = False
        return job

    def _create_mock_invoice(
        self,
        invoice_id: str | None = None,
        status: str = InvoiceStatus.DRAFT.value,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4() if invoice_id is None else invoice_id
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = status
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_create_invoice_with_valid_data(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test creating invoice with valid data."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("150.00"),
            late_fee_amount=Decimal("0.00"),
            due_date=date.today() + timedelta(days=30),
        )

        result = await service.create_invoice(data)

        assert result.invoice_number == "INV-2025-000001"
        mock_invoice_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_generates_unique_number(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test invoice number generation format."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 42

        created_invoice = self._create_mock_invoice()
        created_invoice.invoice_number = "INV-2025-000042"
        mock_invoice_repo.create.return_value = created_invoice

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=30),
        )

        result = await service.create_invoice(data)

        assert "INV-" in result.invoice_number
        mock_invoice_repo.get_next_sequence.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_invoice_calculates_total_correctly(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test total amount calculation."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        created_invoice.amount = Decimal("100.00")
        created_invoice.late_fee_amount = Decimal("25.00")
        created_invoice.total_amount = Decimal("125.00")
        mock_invoice_repo.create.return_value = created_invoice

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("100.00"),
            late_fee_amount=Decimal("25.00"),
            due_date=date.today() + timedelta(days=30),
        )

        await service.create_invoice(data)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["total_amount"] == Decimal("125.00")

    @pytest.mark.asyncio
    async def test_create_invoice_sets_lien_eligible_for_installation(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test lien eligibility for installation jobs."""
        job = self._create_mock_job(job_type="installation")
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        created_invoice.lien_eligible = True
        mock_invoice_repo.create.return_value = created_invoice

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        await service.create_invoice(data)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["lien_eligible"] is True

    @pytest.mark.asyncio
    async def test_create_invoice_not_lien_eligible_for_seasonal(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test seasonal services are not lien eligible."""
        job = self._create_mock_job(job_type="seasonal")
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=30),
        )

        await service.create_invoice(data)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["lien_eligible"] is False

    @pytest.mark.asyncio
    async def test_create_invoice_job_not_found(
        self,
        service: InvoiceService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test error when job not found."""
        mock_job_repo.get_by_id.return_value = None

        data = InvoiceCreate(
            job_id=uuid4(),
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=30),
        )

        with pytest.raises(InvalidInvoiceOperationError, match="Job not found"):
            await service.create_invoice(data)

    @pytest.mark.asyncio
    async def test_create_invoice_with_line_items(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test creating invoice with line items."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        line_items = [
            InvoiceLineItem(
                description="Spring Startup",
                quantity=Decimal(1),
                unit_price=Decimal("100.00"),
                total=Decimal("100.00"),
            ),
        ]

        data = InvoiceCreate(
            job_id=job.id,
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=30),
            line_items=line_items,
        )

        await service.create_invoice(data)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["line_items"] is not None
        assert len(call_kwargs["line_items"]) == 1


@pytest.mark.unit
class TestInvoiceServiceGetInvoice:
    """Tests for InvoiceService.get_invoice method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.DRAFT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_get_invoice_with_valid_id(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test getting invoice with valid ID."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        result = await service.get_invoice(invoice.id)

        assert result.id == invoice.id
        mock_invoice_repo.get_by_id.assert_called_once_with(invoice.id)

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        invoice_id = uuid4()
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.get_invoice(invoice_id)


@pytest.mark.unit
class TestInvoiceServiceUpdateInvoice:
    """Tests for InvoiceService.update_invoice method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(
        self,
        status: str = InvoiceStatus.DRAFT.value,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = status
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_update_invoice_draft_status(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating invoice in draft status."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.DRAFT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        updated_invoice = self._create_mock_invoice()
        updated_invoice.amount = Decimal("200.00")
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(amount=Decimal("200.00"))
        result = await service.update_invoice(invoice.id, data)

        assert result is not None
        mock_invoice_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invoice_non_draft_raises_error(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating non-draft invoice raises error."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.SENT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        data = InvoiceUpdate(amount=Decimal("200.00"))

        with pytest.raises(
            InvalidInvoiceOperationError,
            match="draft status",
        ):
            await service.update_invoice(invoice.id, data)

    @pytest.mark.asyncio
    async def test_update_invoice_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        data = InvoiceUpdate(amount=Decimal("200.00"))

        with pytest.raises(InvoiceNotFoundError):
            await service.update_invoice(uuid4(), data)


@pytest.mark.unit
class TestInvoiceServiceStatusOperations:
    """Tests for InvoiceService status transition methods."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(
        self,
        status: str = InvoiceStatus.DRAFT.value,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = status
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_send_invoice_from_draft(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test sending invoice transitions draft to sent."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.DRAFT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice(status=InvoiceStatus.SENT.value)
        mock_invoice_repo.update.return_value = updated

        result = await service.send_invoice(invoice.id)

        assert result.status == InvoiceStatus.SENT.value
        mock_invoice_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_invoice_non_draft_raises_error(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test sending non-draft invoice raises error."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.SENT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        with pytest.raises(
            InvalidInvoiceOperationError,
            match="draft status",
        ):
            await service.send_invoice(invoice.id)

    @pytest.mark.asyncio
    async def test_send_invoice_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.send_invoice(uuid4())

    @pytest.mark.asyncio
    async def test_mark_viewed_from_sent(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test marking sent invoice as viewed."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.SENT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice(status=InvoiceStatus.VIEWED.value)
        mock_invoice_repo.update.return_value = updated

        result = await service.mark_viewed(invoice.id)

        assert result.status == InvoiceStatus.VIEWED.value

    @pytest.mark.asyncio
    async def test_mark_viewed_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.mark_viewed(uuid4())

    @pytest.mark.asyncio
    async def test_mark_overdue(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test marking invoice as overdue."""
        invoice = self._create_mock_invoice(status=InvoiceStatus.SENT.value)
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice(status=InvoiceStatus.OVERDUE.value)
        mock_invoice_repo.update.return_value = updated

        result = await service.mark_overdue(invoice.id)

        assert result.status == InvoiceStatus.OVERDUE.value

    @pytest.mark.asyncio
    async def test_cancel_invoice(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test cancelling invoice."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice(status=InvoiceStatus.CANCELLED.value)
        mock_invoice_repo.update.return_value = updated

        await service.cancel_invoice(invoice.id)

        mock_invoice_repo.update.assert_called_once()
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["status"] == InvoiceStatus.CANCELLED.value


@pytest.mark.unit
class TestInvoiceServicePaymentOperations:
    """Tests for InvoiceService payment methods."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(
        self,
        total_amount: Decimal = Decimal("150.00"),
        paid_amount: Decimal | None = None,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = total_amount
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = total_amount
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.SENT.value
        invoice.paid_amount = paid_amount
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_record_payment_full_amount_status_paid(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test full payment sets status to paid."""
        invoice = self._create_mock_invoice(total_amount=Decimal("150.00"))
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        updated.status = InvoiceStatus.PAID.value
        updated.paid_amount = Decimal("150.00")
        mock_invoice_repo.update.return_value = updated

        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.VENMO,
        )

        result = await service.record_payment(invoice.id, payment)

        assert result.status == InvoiceStatus.PAID.value
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["status"] == InvoiceStatus.PAID.value

    @pytest.mark.asyncio
    async def test_record_payment_partial_amount_status_partial(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test partial payment sets status to partial."""
        invoice = self._create_mock_invoice(total_amount=Decimal("150.00"))
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        updated.status = InvoiceStatus.PARTIAL.value
        updated.paid_amount = Decimal("50.00")
        mock_invoice_repo.update.return_value = updated

        payment = PaymentRecord(
            amount=Decimal("50.00"),
            payment_method=PaymentMethod.CASH,
        )

        result = await service.record_payment(invoice.id, payment)

        assert result.status == InvoiceStatus.PARTIAL.value
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["status"] == InvoiceStatus.PARTIAL.value

    @pytest.mark.asyncio
    async def test_record_payment_stores_payment_method(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test payment method is stored."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        updated.payment_method = PaymentMethod.ZELLE.value
        mock_invoice_repo.update.return_value = updated

        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.ZELLE,
        )

        await service.record_payment(invoice.id, payment)

        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["payment_method"] == PaymentMethod.ZELLE.value

    @pytest.mark.asyncio
    async def test_record_payment_stores_reference(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test payment reference is stored."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        mock_invoice_repo.update.return_value = updated

        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.CHECK,
            payment_reference="Check #1234",
        )

        await service.record_payment(invoice.id, payment)

        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["payment_reference"] == "Check #1234"

    @pytest.mark.asyncio
    async def test_record_payment_sets_paid_at(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test paid_at timestamp is set."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        mock_invoice_repo.update.return_value = updated

        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.CASH,
        )

        await service.record_payment(invoice.id, payment)

        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["paid_at"] is not None

    @pytest.mark.asyncio
    async def test_record_payment_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        payment = PaymentRecord(
            amount=Decimal("150.00"),
            payment_method=PaymentMethod.CASH,
        )

        with pytest.raises(InvoiceNotFoundError):
            await service.record_payment(uuid4(), payment)


@pytest.mark.unit
class TestInvoiceServiceReminderOperations:
    """Tests for InvoiceService reminder methods."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self, reminder_count: int = 0) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.SENT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = reminder_count
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_send_reminder_increments_count(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test reminder increments reminder_count."""
        invoice = self._create_mock_invoice(reminder_count=2)
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice(reminder_count=3)
        mock_invoice_repo.update.return_value = updated

        result = await service.send_reminder(invoice.id)

        assert result.reminder_count == 3
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["reminder_count"] == 3

    @pytest.mark.asyncio
    async def test_send_reminder_updates_last_sent(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test reminder updates last_reminder_sent."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        mock_invoice_repo.update.return_value = updated

        await service.send_reminder(invoice.id)

        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["last_reminder_sent"] is not None

    @pytest.mark.asyncio
    async def test_send_reminder_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.send_reminder(uuid4())


@pytest.mark.unit
class TestInvoiceServiceLienOperations:
    """Tests for InvoiceService lien tracking methods."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self, lien_eligible: bool = True) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("1000.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("1000.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() - timedelta(days=50)
        invoice.status = InvoiceStatus.OVERDUE.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = lien_eligible
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_send_lien_warning_sets_timestamp(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test lien warning sets lien_warning_sent."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        updated.status = InvoiceStatus.LIEN_WARNING.value
        mock_invoice_repo.update.return_value = updated

        result = await service.send_lien_warning(invoice.id)

        assert result.status == InvoiceStatus.LIEN_WARNING.value
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["lien_warning_sent"] is not None

    @pytest.mark.asyncio
    async def test_send_lien_warning_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.send_lien_warning(uuid4())

    @pytest.mark.asyncio
    async def test_mark_lien_filed_sets_date(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test marking lien filed sets lien_filed_date."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice

        updated = self._create_mock_invoice()
        updated.status = InvoiceStatus.LIEN_FILED.value
        mock_invoice_repo.update.return_value = updated

        filing_date = date.today()
        result = await service.mark_lien_filed(invoice.id, filing_date)

        assert result.status == InvoiceStatus.LIEN_FILED.value
        call_kwargs = mock_invoice_repo.update.call_args.kwargs
        assert call_kwargs["lien_filed_date"] == filing_date

    @pytest.mark.asyncio
    async def test_mark_lien_filed_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test error when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.mark_lien_filed(uuid4(), date.today())

    @pytest.mark.asyncio
    async def test_get_lien_deadlines_returns_approaching_45_day(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test get_lien_deadlines returns 45-day warning invoices."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.find_lien_warning_due.return_value = [invoice]
        mock_invoice_repo.find_lien_filing_due.return_value = []

        result = await service.get_lien_deadlines()

        assert len(result.approaching_45_day) == 1
        assert len(result.approaching_120_day) == 0

    @pytest.mark.asyncio
    async def test_get_lien_deadlines_returns_approaching_120_day(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test get_lien_deadlines returns 120-day filing invoices."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.find_lien_warning_due.return_value = []
        mock_invoice_repo.find_lien_filing_due.return_value = [invoice]

        result = await service.get_lien_deadlines()

        assert len(result.approaching_45_day) == 0
        assert len(result.approaching_120_day) == 1


@pytest.mark.unit
class TestInvoiceServiceGenerateFromJob:
    """Tests for InvoiceService.generate_from_job method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_job(
        self,
        is_deleted: bool = False,
        payment_collected: bool = False,
        final_amount: Decimal | None = None,
        quoted_amount: Decimal | None = Decimal("150.00"),
    ) -> MagicMock:
        """Create a mock job object."""
        job = MagicMock()
        job.id = uuid4()
        job.customer_id = uuid4()
        job.job_type = "seasonal"
        job.description = "Spring startup service"
        job.quoted_amount = quoted_amount
        job.final_amount = final_amount
        job.is_deleted = is_deleted
        job.payment_collected_on_site = payment_collected
        return job

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.DRAFT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_generate_from_job_with_valid_job(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test generating invoice from valid job."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        result = await service.generate_from_job(job.id)

        assert result is not None
        mock_invoice_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_from_job_not_found(
        self,
        service: InvoiceService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test error when job not found."""
        mock_job_repo.get_by_id.return_value = None

        with pytest.raises(InvalidInvoiceOperationError, match="Job not found"):
            await service.generate_from_job(uuid4())

    @pytest.mark.asyncio
    async def test_generate_from_job_deleted_raises_error(
        self,
        service: InvoiceService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test error when job is deleted."""
        job = self._create_mock_job(is_deleted=True)
        mock_job_repo.get_by_id.return_value = job

        with pytest.raises(
            InvalidInvoiceOperationError,
            match="deleted job",
        ):
            await service.generate_from_job(job.id)

    @pytest.mark.asyncio
    async def test_generate_from_job_payment_collected_raises_error(
        self,
        service: InvoiceService,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test error when payment was collected on site."""
        job = self._create_mock_job(payment_collected=True)
        mock_job_repo.get_by_id.return_value = job

        with pytest.raises(
            InvalidInvoiceOperationError,
            match="collected on site",
        ):
            await service.generate_from_job(job.id)

    @pytest.mark.asyncio
    async def test_generate_from_job_uses_final_amount(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test uses final_amount when present."""
        job = self._create_mock_job(
            final_amount=Decimal("200.00"),
            quoted_amount=Decimal("150.00"),
        )
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        created_invoice.amount = Decimal("200.00")
        mock_invoice_repo.create.return_value = created_invoice

        await service.generate_from_job(job.id)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["amount"] == Decimal("200.00")

    @pytest.mark.asyncio
    async def test_generate_from_job_uses_quoted_amount_fallback(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test uses quoted_amount as fallback."""
        job = self._create_mock_job(
            final_amount=None,
            quoted_amount=Decimal("150.00"),
        )
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        await service.generate_from_job(job.id)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["amount"] == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_generate_from_job_creates_line_items(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> None:
        """Test line items are created from job."""
        job = self._create_mock_job()
        mock_job_repo.get_by_id.return_value = job
        mock_invoice_repo.get_next_sequence.return_value = 1

        created_invoice = self._create_mock_invoice()
        mock_invoice_repo.create.return_value = created_invoice

        await service.generate_from_job(job.id)

        call_kwargs = mock_invoice_repo.create.call_args.kwargs
        assert call_kwargs["line_items"] is not None


@pytest.mark.unit
class TestInvoiceServiceListInvoices:
    """Tests for InvoiceService.list_invoices method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.DRAFT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_list_invoices_with_no_filters(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with no filters."""
        invoices = [self._create_mock_invoice() for _ in range(3)]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 3)

        params = InvoiceListParams()
        result = await service.list_invoices(params)

        assert len(result.items) == 3
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_list_invoices_pagination(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test pagination works correctly."""
        invoices = [self._create_mock_invoice() for _ in range(10)]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 25)

        params = InvoiceListParams(page=1, page_size=10)
        result = await service.list_invoices(params)

        assert result.page == 1
        assert result.page_size == 10
        assert result.total == 25
        assert result.total_pages == 3


@pytest.mark.unit
class TestLienEligibilityProperty:
    """Property-based tests for lien eligibility determination.

    Property 7: Lien Eligibility Determination
    - Installation jobs are lien-eligible
    - Major repair jobs are lien-eligible
    - Seasonal services are not lien-eligible
    """

    def test_installation_is_lien_eligible(self) -> None:
        """Test installation jobs are lien eligible."""
        assert "installation" in LIEN_ELIGIBLE_TYPES

    def test_major_repair_is_lien_eligible(self) -> None:
        """Test major_repair jobs are lien eligible."""
        assert "major_repair" in LIEN_ELIGIBLE_TYPES

    def test_new_system_is_lien_eligible(self) -> None:
        """Test new_system jobs are lien eligible."""
        assert "new_system" in LIEN_ELIGIBLE_TYPES

    def test_system_upgrade_is_lien_eligible(self) -> None:
        """Test system_upgrade jobs are lien eligible."""
        assert "system_upgrade" in LIEN_ELIGIBLE_TYPES

    def test_seasonal_not_lien_eligible(self) -> None:
        """Test seasonal services are not lien eligible."""
        assert "seasonal" not in LIEN_ELIGIBLE_TYPES

    def test_repair_not_lien_eligible(self) -> None:
        """Test regular repairs are not lien eligible."""
        assert "repair" not in LIEN_ELIGIBLE_TYPES

    def test_diagnostic_not_lien_eligible(self) -> None:
        """Test diagnostics are not lien eligible."""
        assert "diagnostic" not in LIEN_ELIGIBLE_TYPES


@pytest.mark.unit
class TestInvoiceServiceGetInvoiceDetail:
    """Tests for InvoiceService.get_invoice_detail method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice_with_relations(self) -> MagicMock:
        """Create a mock invoice with job and customer relations."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.DRAFT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)

        # Add job relation
        invoice.job = MagicMock()
        invoice.job.description = "Spring startup service"

        # Add customer relation
        invoice.customer = MagicMock()
        invoice.customer.first_name = "John"
        invoice.customer.last_name = "Doe"
        invoice.customer.phone = "6125551234"
        invoice.customer.email = "john@example.com"

        return invoice

    @pytest.mark.asyncio
    async def test_get_invoice_detail_with_relations(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test getting invoice detail with job and customer info."""
        invoice = self._create_mock_invoice_with_relations()
        mock_invoice_repo.get_by_id.return_value = invoice

        result = await service.get_invoice_detail(invoice.id)

        assert result.job_description == "Spring startup service"
        assert result.customer_name == "John Doe"
        assert result.customer_phone == "6125551234"
        assert result.customer_email == "john@example.com"
        mock_invoice_repo.get_by_id.assert_called_once_with(
            invoice.id,
            include_relationships=True,
        )

    @pytest.mark.asyncio
    async def test_get_invoice_detail_without_customer(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test getting invoice detail when customer is None."""
        invoice = self._create_mock_invoice_with_relations()
        invoice.customer = None
        mock_invoice_repo.get_by_id.return_value = invoice

        result = await service.get_invoice_detail(invoice.id)

        assert result.customer_name is None
        assert result.customer_phone is None
        assert result.customer_email is None

    @pytest.mark.asyncio
    async def test_get_invoice_detail_without_job(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test getting invoice detail when job is None."""
        invoice = self._create_mock_invoice_with_relations()
        invoice.job = None
        mock_invoice_repo.get_by_id.return_value = invoice

        result = await service.get_invoice_detail(invoice.id)

        assert result.job_description is None

    @pytest.mark.asyncio
    async def test_get_invoice_detail_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test getting invoice detail when not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.get_invoice_detail(uuid4())


@pytest.mark.unit
class TestInvoiceServiceUpdateInvoiceFields:
    """Tests for InvoiceService.update_invoice with various field updates."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(
        self,
        status: str = InvoiceStatus.DRAFT.value,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = status
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_update_invoice_amount_only(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating only the amount field."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.amount = Decimal("200.00")
        updated_invoice.total_amount = Decimal("200.00")
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(amount=Decimal("200.00"))
        result = await service.update_invoice(invoice.id, data)

        assert result.amount == Decimal("200.00")
        mock_invoice_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invoice_late_fee_only(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating only the late fee field."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.late_fee_amount = Decimal("25.00")
        updated_invoice.total_amount = Decimal("175.00")
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(late_fee_amount=Decimal("25.00"))
        result = await service.update_invoice(invoice.id, data)

        assert result.late_fee_amount == Decimal("25.00")

    @pytest.mark.asyncio
    async def test_update_invoice_due_date_only(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating only the due date field."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        new_due_date = date.today() + timedelta(days=60)
        updated_invoice = self._create_mock_invoice()
        updated_invoice.due_date = new_due_date
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(due_date=new_due_date)
        result = await service.update_invoice(invoice.id, data)

        assert result.due_date == new_due_date

    @pytest.mark.asyncio
    async def test_update_invoice_line_items(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating line items."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.line_items = [
            {
                "description": "Service",
                "quantity": 1,
                "unit_price": "150.00",
                "total": "150.00",
            },
        ]
        mock_invoice_repo.update.return_value = updated_invoice

        line_items = [
            InvoiceLineItem(
                description="Service",
                quantity=1,
                unit_price=Decimal("150.00"),
                total=Decimal("150.00"),
            ),
        ]
        data = InvoiceUpdate(line_items=line_items)
        await service.update_invoice(invoice.id, data)

        mock_invoice_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invoice_notes_only(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test updating only the notes field."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.notes = "Updated notes"
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(notes="Updated notes")
        result = await service.update_invoice(invoice.id, data)

        assert result.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_invoice_recalculates_total(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test that total is recalculated when amount or late fee changes."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.amount = Decimal("200.00")
        updated_invoice.late_fee_amount = Decimal("25.00")
        updated_invoice.total_amount = Decimal("225.00")
        mock_invoice_repo.update.return_value = updated_invoice

        data = InvoiceUpdate(
            amount=Decimal("200.00"),
            late_fee_amount=Decimal("25.00"),
        )
        await service.update_invoice(invoice.id, data)

        # Verify update was called with recalculated total
        call_kwargs = mock_invoice_repo.update.call_args[1]
        assert call_kwargs["total_amount"] == Decimal("225.00")

    @pytest.mark.asyncio
    async def test_update_invoice_update_returns_none(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test update when repository update returns None."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        mock_invoice_repo.update.return_value = None

        data = InvoiceUpdate(amount=Decimal("200.00"))

        with pytest.raises(InvoiceNotFoundError):
            await service.update_invoice(invoice.id, data)


@pytest.mark.unit
class TestInvoiceServiceCancelInvoice:
    """Tests for InvoiceService.cancel_invoice method."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.status = InvoiceStatus.DRAFT.value
        return invoice

    @pytest.mark.asyncio
    async def test_cancel_invoice_success(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test successful invoice cancellation."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        mock_invoice_repo.update.return_value = invoice

        await service.cancel_invoice(invoice.id)

        mock_invoice_repo.update.assert_called_once_with(
            invoice.id,
            status=InvoiceStatus.CANCELLED.value,
        )

    @pytest.mark.asyncio
    async def test_cancel_invoice_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test cancelling non-existent invoice."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.cancel_invoice(uuid4())


@pytest.mark.unit
class TestInvoiceServiceSendInvoiceEdgeCases:
    """Additional tests for InvoiceService.send_invoice edge cases."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(
        self,
        status: str = InvoiceStatus.DRAFT.value,
    ) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = status
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_send_invoice_update_returns_none(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test send_invoice when repository update returns None."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        mock_invoice_repo.update.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.send_invoice(invoice.id)


@pytest.mark.unit
class TestInvoiceServiceMarkOverdueEdgeCases:
    """Additional tests for InvoiceService.mark_overdue edge cases."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.SENT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_mark_overdue_success(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test successful mark overdue."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        updated_invoice = self._create_mock_invoice()
        updated_invoice.status = InvoiceStatus.OVERDUE.value
        mock_invoice_repo.update.return_value = updated_invoice

        result = await service.mark_overdue(invoice.id)

        assert result.status == InvoiceStatus.OVERDUE.value

    @pytest.mark.asyncio
    async def test_mark_overdue_not_found(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test mark overdue when invoice not found."""
        mock_invoice_repo.get_by_id.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.mark_overdue(uuid4())

    @pytest.mark.asyncio
    async def test_mark_overdue_update_returns_none(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test mark_overdue when repository update returns None."""
        invoice = self._create_mock_invoice()
        mock_invoice_repo.get_by_id.return_value = invoice
        mock_invoice_repo.update.return_value = None

        with pytest.raises(InvoiceNotFoundError):
            await service.mark_overdue(invoice.id)


@pytest.mark.unit
class TestInvoiceServiceListInvoicesFilters:
    """Tests for InvoiceService.list_invoices with various filters."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        """Create mock invoice repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        """Create mock job repository."""
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        """Create service with mock repositories."""
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _create_mock_invoice(self) -> MagicMock:
        """Create a mock invoice object."""
        invoice = MagicMock()
        invoice.id = uuid4()
        invoice.invoice_number = "INV-2025-000001"
        invoice.job_id = uuid4()
        invoice.customer_id = uuid4()
        invoice.amount = Decimal("150.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal("150.00")
        invoice.invoice_date = date.today()
        invoice.due_date = date.today() + timedelta(days=30)
        invoice.status = InvoiceStatus.DRAFT.value
        invoice.paid_amount = None
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = None
        invoice.notes = None
        invoice.created_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)
        return invoice

    @pytest.mark.asyncio
    async def test_list_invoices_with_status_filter(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with status filter."""
        invoices = [self._create_mock_invoice() for _ in range(2)]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 2)

        params = InvoiceListParams(status=InvoiceStatus.DRAFT)
        result = await service.list_invoices(params)

        assert len(result.items) == 2
        mock_invoice_repo.list_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_invoices_with_customer_filter(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with customer_id filter."""
        customer_id = uuid4()
        invoices = [self._create_mock_invoice()]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 1)

        params = InvoiceListParams(customer_id=customer_id)
        result = await service.list_invoices(params)

        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_invoices_with_date_range_filter(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with date range filter."""
        invoices = [self._create_mock_invoice()]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 1)

        params = InvoiceListParams(
            date_from=date.today() - timedelta(days=30),
            date_to=date.today(),
        )
        result = await service.list_invoices(params)

        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_invoices_with_lien_eligible_filter(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with lien_eligible filter."""
        invoice = self._create_mock_invoice()
        invoice.lien_eligible = True
        mock_invoice_repo.list_with_filters.return_value = ([invoice], 1)

        params = InvoiceListParams(lien_eligible=True)
        result = await service.list_invoices(params)

        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_list_invoices_with_sorting(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with sorting."""
        invoices = [self._create_mock_invoice() for _ in range(3)]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 3)

        params = InvoiceListParams(sort_by="due_date", sort_order="desc")
        result = await service.list_invoices(params)

        assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_list_invoices_empty_result(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Test listing invoices with no results."""
        mock_invoice_repo.list_with_filters.return_value = ([], 0)

        params = InvoiceListParams()
        result = await service.list_invoices(params)

        assert len(result.items) == 0
        assert result.total == 0
        assert result.total_pages == 0
