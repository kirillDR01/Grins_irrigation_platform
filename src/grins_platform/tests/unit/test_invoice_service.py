"""Unit tests for InvoiceService.

Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7
Property 5: Invoice Number Uniqueness
Property 6: Payment Recording Correctness
Property 7: Lien Eligibility Determination
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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
        invoice.document_url = None
        invoice.invoice_token = None
        invoice.customer_name = None
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


@pytest.mark.unit
class TestInvoiceServiceFilterAxes:
    """Tests for each of the 9 filter axes individually and in combination.

    Validates: Requirements 28.1, 28.3
    """

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _mock_invoice(self, **overrides: object) -> MagicMock:
        inv = MagicMock()
        inv.id = uuid4()
        inv.invoice_number = "INV-2025-000001"
        inv.job_id = uuid4()
        inv.customer_id = uuid4()
        inv.amount = Decimal("150.00")
        inv.late_fee_amount = Decimal("0.00")
        inv.total_amount = Decimal("150.00")
        inv.invoice_date = date.today()
        inv.due_date = date.today() + timedelta(days=30)
        inv.status = InvoiceStatus.DRAFT.value
        inv.paid_amount = None
        inv.payment_method = None
        inv.payment_reference = None
        inv.paid_at = None
        inv.reminder_count = 0
        inv.last_reminder_sent = None
        inv.lien_eligible = False
        inv.lien_warning_sent = None
        inv.lien_filed_date = None
        inv.line_items = None
        inv.notes = None
        inv.document_url = None
        inv.invoice_token = None
        inv.customer_name = None
        inv.created_at = datetime.now(timezone.utc)
        inv.updated_at = datetime.now(timezone.utc)
        for k, v in overrides.items():
            setattr(inv, k, v)
        return inv

    # --- Axis 3: Job filter ---

    @pytest.mark.asyncio
    async def test_filter_by_job_id(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 3: job_id filter passes through to repository."""
        job_id = uuid4()
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(job_id=job_id)
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.job_id == job_id

    # --- Axis 5: Amount range ---

    @pytest.mark.asyncio
    async def test_filter_by_amount_min(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 5: amount_min filter."""
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(amount_min=Decimal("100.00"))
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.amount_min == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_filter_by_amount_range(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 5: amount_min + amount_max compose."""
        mock_invoice_repo.list_with_filters.return_value = ([], 0)
        params = InvoiceListParams(
            amount_min=Decimal("50.00"),
            amount_max=Decimal("200.00"),
        )
        result = await service.list_invoices(params)
        assert result.total == 0
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.amount_min == Decimal("50.00")
        assert call_params.amount_max == Decimal("200.00")

    # --- Axis 6: Payment type ---

    @pytest.mark.asyncio
    async def test_filter_by_payment_types(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 6: payment_types multi-select filter."""
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(payment_types="cash,check")
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.payment_types == "cash,check"

    # --- Axis 7: Days until due ---

    @pytest.mark.asyncio
    async def test_filter_by_days_until_due(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 7: days_until_due_min/max filter."""
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(days_until_due_min=0, days_until_due_max=7)
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.days_until_due_min == 0
        assert call_params.days_until_due_max == 7

    # --- Axis 8: Days past due ---

    @pytest.mark.asyncio
    async def test_filter_by_days_past_due(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 8: days_past_due_min/max filter."""
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(days_past_due_min=30, days_past_due_max=90)
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.days_past_due_min == 30
        assert call_params.days_past_due_max == 90

    # --- Axis 9: Invoice number ---

    @pytest.mark.asyncio
    async def test_filter_by_invoice_number(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 9: exact invoice number match."""
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(invoice_number="INV-2025-000042")
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.invoice_number == "INV-2025-000042"

    # --- Axis 4 date_type variants ---

    @pytest.mark.asyncio
    async def test_filter_by_due_date_type(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 4: date_type='due' variant."""
        mock_invoice_repo.list_with_filters.return_value = ([], 0)
        params = InvoiceListParams(
            date_type="due",
            date_from=date.today(),
            date_to=date.today() + timedelta(days=7),
        )
        await service.list_invoices(params)
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.date_type == "due"

    @pytest.mark.asyncio
    async def test_filter_by_paid_date_type(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Axis 4: date_type='paid' variant."""
        mock_invoice_repo.list_with_filters.return_value = ([], 0)
        params = InvoiceListParams(
            date_type="paid",
            date_from=date(2025, 1, 1),
            date_to=date(2025, 3, 31),
        )
        await service.list_invoices(params)
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.date_type == "paid"

    # --- Multi-axis combination ---

    @pytest.mark.asyncio
    async def test_combined_three_axis_filter(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Multiple axes compose via AND."""
        customer_id = uuid4()
        mock_invoice_repo.list_with_filters.return_value = (
            [self._mock_invoice()],
            1,
        )
        params = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            customer_id=customer_id,
            amount_min=Decimal("100.00"),
        )
        result = await service.list_invoices(params)
        assert result.total == 1
        call_params = mock_invoice_repo.list_with_filters.call_args[0][0]
        assert call_params.status == InvoiceStatus.OVERDUE
        assert call_params.customer_id == customer_id
        assert call_params.amount_min == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_all_nine_axes_combined(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """All 9 axes can be set simultaneously."""
        customer_id = uuid4()
        job_id = uuid4()
        mock_invoice_repo.list_with_filters.return_value = ([], 0)
        params = InvoiceListParams(
            status=InvoiceStatus.SENT,
            customer_id=customer_id,
            job_id=job_id,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
            date_type="created",
            amount_min=Decimal("50.00"),
            amount_max=Decimal("500.00"),
            payment_types="cash,stripe",
            days_until_due_min=0,
            days_until_due_max=30,
            days_past_due_min=0,
            days_past_due_max=60,
            invoice_number="INV-2025-000001",
        )
        result = await service.list_invoices(params)
        assert result.total == 0
        mock_invoice_repo.list_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """No filters returns unfiltered result set (clear-all identity)."""
        invoices = [self._mock_invoice() for _ in range(5)]
        mock_invoice_repo.list_with_filters.return_value = (invoices, 5)
        params = InvoiceListParams()
        result = await service.list_invoices(params)
        assert result.total == 5
        assert len(result.items) == 5


@pytest.mark.unit
class TestInvoiceListParamsRoundTrip:
    """Test InvoiceListParams serialization/deserialization round-trip.

    Validates: Requirements 28.3 (URL persistence)
    """

    def test_round_trip_with_all_axes(self) -> None:
        """Serialize then deserialize preserves all filter values."""
        customer_id = uuid4()
        job_id = uuid4()
        original = InvoiceListParams(
            status=InvoiceStatus.OVERDUE,
            customer_id=customer_id,
            job_id=job_id,
            date_from=date(2025, 3, 1),
            date_to=date(2025, 3, 31),
            date_type="due",
            amount_min=Decimal("100.00"),
            amount_max=Decimal("999.99"),
            payment_types="cash,check",
            days_until_due_min=0,
            days_until_due_max=14,
            days_past_due_min=30,
            days_past_due_max=90,
            invoice_number="INV-2025-000042",
        )
        data = original.model_dump(mode="json")
        restored = InvoiceListParams.model_validate(data)
        assert restored.status == original.status
        assert restored.customer_id == original.customer_id
        assert restored.job_id == original.job_id
        assert restored.date_from == original.date_from
        assert restored.date_to == original.date_to
        assert restored.date_type == original.date_type
        assert restored.amount_min == original.amount_min
        assert restored.amount_max == original.amount_max
        assert restored.payment_types == original.payment_types
        assert restored.days_until_due_min == original.days_until_due_min
        assert restored.days_until_due_max == original.days_until_due_max
        assert restored.days_past_due_min == original.days_past_due_min
        assert restored.days_past_due_max == original.days_past_due_max
        assert restored.invoice_number == original.invoice_number

    def test_round_trip_defaults(self) -> None:
        """Default params survive round-trip."""
        original = InvoiceListParams()
        data = original.model_dump(mode="json")
        restored = InvoiceListParams.model_validate(data)
        assert restored.page == original.page
        assert restored.page_size == original.page_size
        assert restored.sort_by == original.sort_by
        assert restored.sort_order == original.sort_order
        assert restored.status is None
        assert restored.customer_id is None


@pytest.mark.unit
class TestInvoiceServiceMassNotify:
    """Tests for InvoiceService.mass_notify targeting logic.

    Validates: Requirements 29.3, 29.4, H-11 (bughunt 2026-04-16).
    """

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.update = AsyncMock()
        # H-11: the new SmsConsentRepository pre-filter calls
        # ``session.execute(stmt).scalars().all()`` inside mass_notify. Give
        # the default mock session a sync MagicMock result chain that
        # returns "no opt-outs" so legacy tests (which don't care about
        # consent) still exercise the send loop.
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value = scalars_mock
        repo.session = MagicMock()
        repo.session.execute = AsyncMock(return_value=execute_result_mock)
        return repo

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _mock_invoice_with_customer(
        self,
        *,
        phone: str | None = "+16125551234",
    ) -> MagicMock:
        customer = MagicMock()
        customer.first_name = "Jane"
        customer.last_name = "Doe"
        customer.phone = phone
        customer.id = uuid4()
        customer.sms_opt_in = True
        customer.sms_consent_type = "transactional"
        customer.sms_consent_date = datetime.now(timezone.utc)

        inv = MagicMock()
        inv.id = uuid4()
        inv.invoice_number = "INV-2025-000001"
        inv.total_amount = Decimal("250.00")
        inv.due_date = date.today() - timedelta(days=45)
        inv.reminder_count = 0
        inv.customer = customer
        return inv

    @pytest.mark.asyncio
    async def test_mass_notify_past_due_targets_correct_invoices(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """past_due type calls find_past_due."""
        invoices = [self._mock_invoice_with_customer()]
        mock_invoice_repo.find_past_due.return_value = invoices
        result = await service.mass_notify("past_due")
        mock_invoice_repo.find_past_due.assert_called_once()
        assert result.notification_type == "past_due"
        assert result.targeted == 1

    @pytest.mark.asyncio
    async def test_mass_notify_due_soon_targets_correct_invoices(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """due_soon type calls find_due_soon with days param."""
        mock_invoice_repo.find_due_soon.return_value = []
        result = await service.mass_notify("due_soon", due_soon_days=14)
        mock_invoice_repo.find_due_soon.assert_called_once_with(14)
        assert result.notification_type == "due_soon"
        assert result.targeted == 0

    @pytest.mark.asyncio
    async def test_mass_notify_lien_eligible_raises_deprecation_error(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """CR-5: mass_notify('lien_eligible') now raises the deprecation error
        to push callers onto the lien-review-queue endpoints.
        """
        from grins_platform.services.invoice_service import (
            LienMassNotifyDeprecatedError,
        )

        with pytest.raises(LienMassNotifyDeprecatedError):
            await service.mass_notify(
                "lien_eligible",
                lien_days_past_due=90,
                lien_min_amount=1000.0,
            )
        mock_invoice_repo.find_lien_eligible.assert_not_called()

    @pytest.mark.asyncio
    async def test_mass_notify_invalid_type_targets_nothing(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Unknown notification_type targets zero invoices."""
        result = await service.mass_notify("nonexistent")
        assert result.targeted == 0
        assert result.sent == 0

    @pytest.mark.asyncio
    async def test_mass_notify_skips_customer_without_phone(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Customers without phone are skipped."""
        inv = self._mock_invoice_with_customer(phone=None)
        mock_invoice_repo.find_past_due.return_value = [inv]
        result = await service.mass_notify("past_due")
        assert result.targeted == 1
        assert result.skipped == 1
        assert result.sent == 0

    @pytest.mark.asyncio
    async def test_mass_notify_skips_customer_with_no_customer(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """Invoices with no customer relationship are skipped."""
        inv = MagicMock()
        inv.id = uuid4()
        inv.customer = None
        inv.reminder_count = 0
        mock_invoice_repo.find_past_due.return_value = [inv]
        result = await service.mass_notify("past_due")
        assert result.targeted == 1
        assert result.skipped == 1
        assert result.sent == 0


# ---------------------------------------------------------------------------
# bughunt M-14: canonical merge keys + admin template validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderInvoiceTemplate:
    """``render_invoice_template`` accepts both the canonical curly form
    and the spec brackets, mapping the latter to canonical at parse
    time so all rendering goes through one ``str.format`` call."""

    def test_canonical_curly_form_renders(self) -> None:
        from grins_platform.services.invoice_service import (
            render_invoice_template,
        )

        body = render_invoice_template(
            "{customer_name}, invoice {invoice_number} for ${amount} due {due_date}.",
            customer_name="Jane Doe",
            invoice_number="INV-2026-0001",
            amount="250.00",
            due_date="2026-04-22",
        )
        assert (
            body == "Jane Doe, invoice INV-2026-0001 for $250.00 due 2026-04-22."
        )

    def test_spec_brackets_translate_to_canonical(self) -> None:
        from grins_platform.services.invoice_service import (
            render_invoice_template,
        )

        body = render_invoice_template(
            "[Customer name], invoice #[number] for $[amount] was due on [date].",
            customer_name="Jane Doe",
            invoice_number="INV-2026-0001",
            amount="250.00",
            due_date="2026-04-22",
        )
        assert (
            body
            == "Jane Doe, invoice #INV-2026-0001 for $250.00 was due on 2026-04-22."
        )


@pytest.mark.unit
class TestValidateInvoiceTemplate:
    """Admin custom templates must reference the four canonical merge
    keys so the loop never silently drops merge fields."""

    def test_complete_template_passes(self) -> None:
        from grins_platform.services.invoice_service import (
            validate_invoice_template,
        )

        validate_invoice_template(
            "{customer_name} {invoice_number} {amount} {due_date}",
        )

    def test_complete_bracket_template_passes(self) -> None:
        from grins_platform.services.invoice_service import (
            validate_invoice_template,
        )

        validate_invoice_template(
            "[Customer name] [number] [amount] [date]",
        )

    def test_missing_keys_raises_with_named_offenders(self) -> None:
        from grins_platform.services.invoice_service import (
            InvalidInvoiceTemplateError,
            validate_invoice_template,
        )

        with pytest.raises(InvalidInvoiceTemplateError) as exc_info:
            validate_invoice_template("Pay your invoice now.")

        missing = exc_info.value.missing
        assert set(missing) == {
            "customer_name",
            "invoice_number",
            "amount",
            "due_date",
        }


@pytest.mark.unit
class TestMassNotifyValidatesCustomTemplate:
    """``mass_notify`` raises ``InvalidInvoiceTemplateError`` upfront for
    admin-supplied templates that omit required merge keys, so the
    endpoint can return 400 with named offenders instead of failing
    silently per-row inside the send loop."""

    @pytest.fixture
    def service(self) -> InvoiceService:
        return InvoiceService(
            invoice_repository=AsyncMock(),
            job_repository=AsyncMock(),
        )

    @pytest.mark.asyncio
    async def test_mass_notify_with_invalid_template_raises_before_send(
        self,
        service: InvoiceService,
    ) -> None:
        from grins_platform.services.invoice_service import (
            InvalidInvoiceTemplateError,
        )

        with pytest.raises(InvalidInvoiceTemplateError):
            await service.mass_notify(
                "past_due",
                template="Pay up.",
            )


@pytest.mark.unit
class TestInvoiceServiceMassNotifyExtra:
    """Continuation of TestInvoiceServiceMassNotify. Split from the
    original class so the bughunt M-14 test classes can sit between
    them without breaking fixture inheritance — these tests use the
    repo-mock fixture flavor, not the `InvoiceService(AsyncMock())`
    fixture used by the M-14 templating-validation tests above.
    """

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.update = AsyncMock()
        # H-11: SmsConsentRepository pre-filter calls
        # session.execute(stmt).scalars().all() — give it a sync mock
        # chain returning "no opt-outs" so the send loop runs.
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        execute_result_mock = MagicMock()
        execute_result_mock.scalars.return_value = scalars_mock
        repo.session = MagicMock()
        repo.session.execute = AsyncMock(return_value=execute_result_mock)
        return repo

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _mock_invoice_with_customer(
        self,
        *,
        phone: str | None = "+16125551234",
    ) -> MagicMock:
        customer = MagicMock()
        customer.first_name = "Jane"
        customer.last_name = "Doe"
        customer.phone = phone
        customer.id = uuid4()
        customer.sms_opt_in = True
        customer.sms_consent_type = "transactional"
        customer.sms_consent_date = datetime.now(timezone.utc)

        inv = MagicMock()
        inv.id = uuid4()
        inv.invoice_number = "INV-2025-000001"
        inv.total_amount = Decimal("250.00")
        inv.due_date = date.today() - timedelta(days=45)
        inv.reminder_count = 0
        inv.customer = customer
        return inv

    @pytest.mark.asyncio
    async def test_mass_notify_counts_send_failures(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """SMS send failures are counted, not raised."""
        from unittest.mock import patch

        inv = self._mock_invoice_with_customer()
        mock_invoice_repo.find_past_due.return_value = [inv]

        with patch(
            "grins_platform.services.sms_service.SMSService",
            side_effect=Exception("SMS down"),
        ):
            result = await service.mass_notify("past_due")
        assert result.targeted == 1
        assert result.failed == 1
        assert result.sent == 0

    @pytest.mark.asyncio
    async def test_mass_notify_default_lien_thresholds_still_raises(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """CR-5: mass_notify('lien_eligible') raises even with default thresholds."""
        from grins_platform.services.invoice_service import (
            LienMassNotifyDeprecatedError,
        )

        with pytest.raises(LienMassNotifyDeprecatedError):
            await service.mass_notify("lien_eligible")
        mock_invoice_repo.find_lien_eligible.assert_not_called()

    # ==========================================================================
    # H-11: batch SMS-consent pre-filter
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_mass_notify_past_due_skips_opted_out_customers(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """H-11: past_due branch skips opted-out customers before send."""
        from unittest.mock import patch

        inv_opted_out = self._mock_invoice_with_customer()
        inv_ok = self._mock_invoice_with_customer()
        mock_invoice_repo.find_past_due.return_value = [inv_opted_out, inv_ok]

        with patch(
            "grins_platform.repositories.sms_consent_repository."
            "SmsConsentRepository.get_opted_out_customer_ids",
            new=AsyncMock(return_value={inv_opted_out.customer.id}),
        ), patch(
            "grins_platform.services.sms_service.SMSService",
        ) as mock_sms_cls:
            mock_sms_instance = MagicMock()
            mock_sms_instance.send_message = AsyncMock(
                return_value={"success": True, "message_id": str(uuid4())},
            )
            mock_sms_cls.return_value = mock_sms_instance

            result = await service.mass_notify("past_due")

        assert result.targeted == 2
        assert result.skipped_count == 1
        assert result.skipped_reasons == {"opted_out": 1}
        assert result.sent == 1
        assert result.failed == 0
        # SMSService.send_message was only called for the non-opted-out one.
        assert mock_sms_instance.send_message.await_count == 1
        send_kwargs = mock_sms_instance.send_message.await_args.kwargs
        # Opted-out customer's phone must NOT appear in any send call.
        assert send_kwargs["recipient"].customer_id == inv_ok.customer.id

    @pytest.mark.asyncio
    async def test_mass_notify_upcoming_due_skips_opted_out_customers(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """H-11: due_soon branch skips opted-out customers before send."""
        from unittest.mock import patch

        inv_opted_out = self._mock_invoice_with_customer()
        inv_ok_a = self._mock_invoice_with_customer()
        inv_ok_b = self._mock_invoice_with_customer()
        mock_invoice_repo.find_due_soon.return_value = [
            inv_opted_out,
            inv_ok_a,
            inv_ok_b,
        ]

        with patch(
            "grins_platform.repositories.sms_consent_repository."
            "SmsConsentRepository.get_opted_out_customer_ids",
            new=AsyncMock(return_value={inv_opted_out.customer.id}),
        ), patch(
            "grins_platform.services.sms_service.SMSService",
        ) as mock_sms_cls:
            mock_sms_instance = MagicMock()
            mock_sms_instance.send_message = AsyncMock(
                return_value={"success": True, "message_id": str(uuid4())},
            )
            mock_sms_cls.return_value = mock_sms_instance

            result = await service.mass_notify("due_soon", due_soon_days=14)

        assert result.targeted == 3
        assert result.skipped_count == 1
        assert result.skipped_reasons == {"opted_out": 1}
        assert result.sent == 2
        # SMSService.send_message must not have been called for the opted-out
        # customer.
        sent_to_customer_ids = {
            call.kwargs["recipient"].customer_id
            for call in mock_sms_instance.send_message.await_args_list
        }
        assert inv_opted_out.customer.id not in sent_to_customer_ids
        assert inv_ok_a.customer.id in sent_to_customer_ids
        assert inv_ok_b.customer.id in sent_to_customer_ids

    @pytest.mark.asyncio
    async def test_mass_notify_response_includes_skipped_count_and_reasons(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """H-11: response schema exposes skipped_count and skipped_reasons.

        Default values (no opt-outs) must still be present as 0 and {}
        so API consumers never see a missing key.
        """
        from unittest.mock import patch

        inv = self._mock_invoice_with_customer()
        mock_invoice_repo.find_past_due.return_value = [inv]

        # No opt-outs -> empty set from the repo.
        with patch(
            "grins_platform.repositories.sms_consent_repository."
            "SmsConsentRepository.get_opted_out_customer_ids",
            new=AsyncMock(return_value=set()),
        ), patch(
            "grins_platform.services.sms_service.SMSService",
        ) as mock_sms_cls:
            mock_sms_instance = MagicMock()
            mock_sms_instance.send_message = AsyncMock(
                return_value={"success": True, "message_id": str(uuid4())},
            )
            mock_sms_cls.return_value = mock_sms_instance

            result = await service.mass_notify("past_due")

        # Field presence and sensible defaults.
        assert hasattr(result, "skipped_count")
        assert hasattr(result, "skipped_reasons")
        assert result.skipped_count == 0
        assert result.skipped_reasons == {}
        # And the serialized response (API contract) includes them too.
        payload = result.model_dump()
        assert payload["skipped_count"] == 0
        assert payload["skipped_reasons"] == {}


# =============================================================================
# CR-5: compute_lien_candidates + send_lien_notice
# =============================================================================


@pytest.mark.unit
class TestInvoiceServiceLienReviewQueue:
    """CR-5 (bughunt 2026-04-16) — lien review queue service coverage."""

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.session = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
    ) -> InvoiceService:
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
        )

    def _make_invoice(
        self,
        *,
        customer_id: UUID,
        amount: Decimal = Decimal("750.00"),
        days_overdue: int = 90,
        invoice_number: str = "INV-2025-000001",
        phone: str | None = "+19527373312",
        first_name: str = "Alice",
        last_name: str = "Smith",
    ) -> MagicMock:
        customer = MagicMock()
        customer.id = customer_id
        customer.first_name = first_name
        customer.last_name = last_name
        customer.phone = phone
        customer.sms_opt_in = True
        customer.sms_consent_type = "transactional"

        inv = MagicMock()
        inv.id = uuid4()
        inv.invoice_number = invoice_number
        inv.total_amount = amount
        inv.due_date = date.today() - timedelta(days=days_overdue)
        inv.reminder_count = 0
        inv.customer_id = customer_id
        inv.customer = customer
        return inv

    @pytest.mark.asyncio
    async def test_compute_lien_candidates_groups_by_customer(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        cust_a = uuid4()
        cust_b = uuid4()
        # Two invoices for A, one for B — expect 2 candidate rows.
        invoices = [
            self._make_invoice(
                customer_id=cust_a,
                amount=Decimal(500),
                days_overdue=90,
                invoice_number="INV-A-1",
            ),
            self._make_invoice(
                customer_id=cust_a,
                amount=Decimal(300),
                days_overdue=65,
                invoice_number="INV-A-2",
                first_name="Alice",
                last_name="Smith",
            ),
            self._make_invoice(
                customer_id=cust_b,
                amount=Decimal(1000),
                days_overdue=80,
                invoice_number="INV-B-1",
                first_name="Bob",
                last_name="Jones",
            ),
        ]
        mock_invoice_repo.find_lien_eligible.return_value = invoices

        candidates = await service.compute_lien_candidates()

        assert len(candidates) == 2
        by_id = {c.customer_id: c for c in candidates}
        a = by_id[cust_a]
        assert a.total_past_due_amount == Decimal(800)
        assert a.oldest_invoice_age_days == 90
        assert set(a.invoice_numbers) == {"INV-A-1", "INV-A-2"}

    @pytest.mark.asyncio
    async def test_compute_lien_candidates_filters_by_days_past_due(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        mock_invoice_repo.find_lien_eligible.return_value = []
        await service.compute_lien_candidates(days_past_due=120)
        mock_invoice_repo.find_lien_eligible.assert_awaited_once_with(
            days_past_due=120,
            min_amount=Decimal("500.0"),
        )

    @pytest.mark.asyncio
    async def test_compute_lien_candidates_filters_by_min_amount(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        mock_invoice_repo.find_lien_eligible.return_value = []
        await service.compute_lien_candidates(min_amount=1000.0)
        mock_invoice_repo.find_lien_eligible.assert_awaited_once_with(
            days_past_due=60,
            min_amount=Decimal("1000.0"),
        )

    @pytest.mark.asyncio
    async def test_send_lien_notice_sends_sms_and_writes_audit(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        from unittest.mock import patch

        customer_id = uuid4()
        invoice = self._make_invoice(customer_id=customer_id)
        mock_invoice_repo.find_lien_eligible_for_customer.return_value = [invoice]

        # No opt-out record.
        consent_result_mock = MagicMock()
        consent_scalars_mock = MagicMock()
        consent_scalars_mock.first.return_value = None
        consent_result_mock.scalars.return_value = consent_scalars_mock
        mock_invoice_repo.session.execute = AsyncMock(
            return_value=consent_result_mock,
        )

        admin_id = uuid4()

        with patch(
            "grins_platform.services.sms_service.SMSService",
        ) as mock_sms_cls, patch(
            "grins_platform.repositories.audit_log_repository.AuditLogRepository",
        ) as mock_audit_cls:
            mock_sms_instance = MagicMock()
            mock_sms_instance.send_message = AsyncMock(
                return_value={"success": True, "message_id": str(uuid4())},
            )
            mock_sms_cls.return_value = mock_sms_instance

            mock_audit_instance = AsyncMock()
            mock_audit_cls.return_value = mock_audit_instance

            result = await service.send_lien_notice(
                customer_id=customer_id,
                admin_user_id=admin_id,
            )

        assert result.success is True
        assert result.message == "sent"
        mock_sms_instance.send_message.assert_awaited_once()
        mock_audit_instance.create.assert_awaited_once()
        audit_kwargs = mock_audit_instance.create.await_args.kwargs
        assert audit_kwargs["action"] == "invoice.lien_notice.sent"
        assert audit_kwargs["resource_type"] == "customer"
        assert str(invoice.id) in audit_kwargs["details"]["invoice_ids"]

    @pytest.mark.asyncio
    async def test_send_lien_notice_fails_when_customer_opted_out(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        from unittest.mock import patch

        customer_id = uuid4()
        invoice = self._make_invoice(customer_id=customer_id)
        mock_invoice_repo.find_lien_eligible_for_customer.return_value = [invoice]

        opted_out_record = MagicMock()
        opted_out_record.consent_given = False
        consent_result_mock = MagicMock()
        consent_scalars_mock = MagicMock()
        consent_scalars_mock.first.return_value = opted_out_record
        consent_result_mock.scalars.return_value = consent_scalars_mock
        mock_invoice_repo.session.execute = AsyncMock(
            return_value=consent_result_mock,
        )

        with patch(
            "grins_platform.services.sms_service.SMSService",
        ) as mock_sms_cls:
            mock_sms_instance = MagicMock()
            mock_sms_instance.send_message = AsyncMock()
            mock_sms_cls.return_value = mock_sms_instance

            result = await service.send_lien_notice(
                customer_id=customer_id,
                admin_user_id=uuid4(),
            )

        assert result.success is False
        assert result.message == "customer_opted_out"
        mock_sms_instance.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_lien_notice_fails_when_customer_has_no_phone(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        customer_id = uuid4()
        invoice = self._make_invoice(customer_id=customer_id, phone=None)
        mock_invoice_repo.find_lien_eligible_for_customer.return_value = [invoice]

        result = await service.send_lien_notice(
            customer_id=customer_id, admin_user_id=uuid4(),
        )

        assert result.success is False
        assert result.message == "no_phone"

    @pytest.mark.asyncio
    async def test_send_lien_notice_no_eligible_invoices(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
    ) -> None:
        """If eligibility changed (payment received), the send must no-op."""
        mock_invoice_repo.find_lien_eligible_for_customer.return_value = []

        result = await service.send_lien_notice(
            customer_id=uuid4(), admin_user_id=uuid4(),
        )

        assert result.success is False
        assert result.message == "no_eligible_invoices"


# =============================================================================
# H-12: compute_lien_candidates reads defaults from BusinessSettings
# =============================================================================


@pytest.mark.unit
class TestInvoiceServiceH12ReadsBusinessSettings:
    """H-12 — compute_lien_candidates / mass_notify read defaults from
    the business-settings service when callers don't override.

    Validates: bughunt 2026-04-16 finding H-12.
    """

    @pytest.fixture
    def mock_invoice_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.session = AsyncMock()
        return repo

    @pytest.fixture
    def mock_job_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_settings(self) -> AsyncMock:
        """A BusinessSettingService stub with configured return values."""
        settings = AsyncMock()
        settings.get_int = AsyncMock()
        settings.get_decimal = AsyncMock()
        return settings

    @pytest.fixture
    def service(
        self,
        mock_invoice_repo: AsyncMock,
        mock_job_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> InvoiceService:
        return InvoiceService(
            invoice_repository=mock_invoice_repo,
            job_repository=mock_job_repo,
            business_settings=mock_settings,
        )

    @pytest.mark.asyncio
    async def test_compute_lien_candidates_reads_defaults_from_business_settings(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> None:
        """compute_lien_candidates() with no args → uses settings defaults."""
        mock_invoice_repo.find_lien_eligible.return_value = []
        mock_settings.get_int.return_value = 90
        mock_settings.get_decimal.return_value = Decimal("1250.00")

        await service.compute_lien_candidates()

        # The service pulled both knobs from BusinessSettings.
        mock_settings.get_int.assert_awaited_once_with(
            "lien_days_past_due", 60,
        )
        mock_settings.get_decimal.assert_awaited_once_with(
            "lien_min_amount", Decimal(500),
        )
        # And forwarded them to the repository.
        mock_invoice_repo.find_lien_eligible.assert_awaited_once_with(
            days_past_due=90,
            min_amount=Decimal("1250.00"),
        )

    @pytest.mark.asyncio
    async def test_compute_lien_candidates_explicit_args_override_settings(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> None:
        """Explicit args still win over the persisted defaults."""
        mock_invoice_repo.find_lien_eligible.return_value = []
        mock_settings.get_int.return_value = 90
        mock_settings.get_decimal.return_value = Decimal("1250.00")

        await service.compute_lien_candidates(
            days_past_due=45, min_amount=250.0,
        )

        # Settings service should NOT be queried when explicit args given.
        mock_settings.get_int.assert_not_called()
        mock_settings.get_decimal.assert_not_called()
        mock_invoice_repo.find_lien_eligible.assert_awaited_once_with(
            days_past_due=45,
            min_amount=Decimal("250.0"),
        )

    @pytest.mark.asyncio
    async def test_send_lien_notice_reads_defaults_from_business_settings(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> None:
        """send_lien_notice also pulls thresholds from BusinessSettings."""
        mock_invoice_repo.find_lien_eligible_for_customer.return_value = []
        mock_settings.get_int.return_value = 90
        mock_settings.get_decimal.return_value = Decimal(1000)

        customer_id = uuid4()
        await service.send_lien_notice(
            customer_id=customer_id, admin_user_id=uuid4(),
        )

        mock_settings.get_int.assert_awaited_once_with(
            "lien_days_past_due", 60,
        )
        mock_settings.get_decimal.assert_awaited_once_with(
            "lien_min_amount", Decimal(500),
        )
        mock_invoice_repo.find_lien_eligible_for_customer.assert_awaited_once_with(
            customer_id,
            days_past_due=90,
            min_amount=Decimal(1000),
        )

    @pytest.mark.asyncio
    async def test_mass_notify_due_soon_reads_upcoming_due_days(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> None:
        """mass_notify('due_soon') with no override reads upcoming_due_days."""
        mock_invoice_repo.find_due_soon.return_value = []
        mock_settings.get_int.return_value = 14

        await service.mass_notify("due_soon")

        mock_settings.get_int.assert_awaited_once_with(
            "upcoming_due_days", 7,
        )
        mock_invoice_repo.find_due_soon.assert_awaited_once_with(14)

    @pytest.mark.asyncio
    async def test_mass_notify_due_soon_explicit_override_wins(
        self,
        service: InvoiceService,
        mock_invoice_repo: AsyncMock,
        mock_settings: AsyncMock,
    ) -> None:
        """Explicit due_soon_days overrides the persisted setting."""
        mock_invoice_repo.find_due_soon.return_value = []

        await service.mass_notify("due_soon", due_soon_days=3)

        mock_settings.get_int.assert_not_called()
        mock_invoice_repo.find_due_soon.assert_awaited_once_with(3)
