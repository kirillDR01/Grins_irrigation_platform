"""Unit tests for InvoiceRepository.

Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.models.enums import InvoiceStatus
from grins_platform.models.invoice import Invoice
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.schemas.invoice import InvoiceListParams


@pytest.mark.unit
class TestInvoiceRepositoryCreate:
    """Tests for InvoiceRepository.create method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create_invoice_with_all_fields(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating an invoice with all fields."""
        job_id = uuid4()
        customer_id = uuid4()
        invoice_number = "INV-2025-0001"
        amount = Decimal("150.00")
        late_fee_amount = Decimal("15.00")
        total_amount = Decimal("165.00")
        due_date = date(2025, 2, 15)
        invoice_date = date(2025, 1, 29)
        line_items = [
            {
                "description": "Spring Startup",
                "quantity": 1,
                "unit_price": "150.00",
                "total": "150.00",
            },
        ]
        notes = "Test invoice"

        result = await repository.create(
            job_id=job_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            total_amount=total_amount,
            due_date=due_date,
            late_fee_amount=late_fee_amount,
            invoice_date=invoice_date,
            status="draft",
            lien_eligible=True,
            line_items=line_items,
            notes=notes,
        )

        mock_session.add.assert_called_once()
        added_invoice = mock_session.add.call_args[0][0]
        assert isinstance(added_invoice, Invoice)
        assert added_invoice.job_id == job_id
        assert added_invoice.customer_id == customer_id
        assert added_invoice.invoice_number == invoice_number
        assert added_invoice.amount == amount
        assert added_invoice.late_fee_amount == late_fee_amount
        assert added_invoice.total_amount == total_amount
        assert added_invoice.due_date == due_date
        assert added_invoice.invoice_date == invoice_date
        assert added_invoice.status == "draft"
        assert added_invoice.lien_eligible is True
        assert added_invoice.line_items == line_items
        assert added_invoice.notes == notes

        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()
        assert result == added_invoice

    @pytest.mark.asyncio
    async def test_create_invoice_minimal_fields(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test creating an invoice with minimal required fields."""
        job_id = uuid4()
        customer_id = uuid4()
        invoice_number = "INV-2025-0002"
        amount = Decimal("100.00")
        total_amount = Decimal("100.00")
        due_date = date(2025, 2, 15)

        await repository.create(
            job_id=job_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            total_amount=total_amount,
            due_date=due_date,
        )

        mock_session.add.assert_called_once()
        added_invoice = mock_session.add.call_args[0][0]
        assert added_invoice.late_fee_amount == Decimal(0)
        assert added_invoice.status == "draft"
        assert added_invoice.lien_eligible is False
        assert added_invoice.line_items is None
        assert added_invoice.notes is None

    @pytest.mark.asyncio
    async def test_create_invoice_default_invoice_date(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test that invoice_date defaults to today when not provided."""
        await repository.create(
            job_id=uuid4(),
            customer_id=uuid4(),
            invoice_number="INV-2025-0003",
            amount=Decimal("50.00"),
            total_amount=Decimal("50.00"),
            due_date=date(2025, 2, 15),
        )

        added_invoice = mock_session.add.call_args[0][0]
        assert added_invoice.invoice_date == date.today()


@pytest.mark.unit
class TestInvoiceRepositoryGetById:
    """Tests for InvoiceRepository.get_by_id method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting an invoice by ID when it exists."""
        invoice_id = uuid4()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invoice
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(invoice_id)

        assert result == mock_invoice
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting an invoice by ID when it doesn't exist."""
        invoice_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(invoice_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_with_relationships(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting an invoice with job and customer relationships loaded."""
        invoice_id = uuid4()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invoice
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(invoice_id, include_relationships=True)

        assert result == mock_invoice
        mock_session.execute.assert_awaited_once()


@pytest.mark.unit
class TestInvoiceRepositoryUpdate:
    """Tests for InvoiceRepository.update method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_update_invoice_found(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating an invoice when it exists."""
        invoice_id = uuid4()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.id = invoice_id
        mock_invoice.status = "draft"
        mock_invoice.amount = Decimal("100.00")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_invoice
        mock_session.execute.return_value = mock_result

        result = await repository.update(
            invoice_id,
            status="sent",
            amount=Decimal("150.00"),
        )

        assert result == mock_invoice
        mock_session.flush.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_invoice_not_found(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test updating an invoice when it doesn't exist."""
        invoice_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.update(invoice_id, status="sent")

        assert result is None
        mock_session.flush.assert_not_awaited()


@pytest.mark.unit
class TestInvoiceRepositoryListWithFilters:
    """Tests for InvoiceRepository.list_with_filters method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_list_with_no_filters(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices with no filters."""
        mock_invoice1 = MagicMock(spec=Invoice)
        mock_invoice2 = MagicMock(spec=Invoice)

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock list query
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice1, mock_invoice2]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams()
        invoices, total = await repository.list_with_filters(params)

        assert len(invoices) == 2
        assert total == 2
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_with_status_filter(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices filtered by status."""
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.status = "sent"

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(status=InvoiceStatus.SENT)
        invoices, total = await repository.list_with_filters(params)

        assert len(invoices) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_with_customer_filter(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices filtered by customer."""
        customer_id = uuid4()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.customer_id = customer_id

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(customer_id=customer_id)
        invoices, total = await repository.list_with_filters(params)

        assert len(invoices) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_with_date_range_filter(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices filtered by date range."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(
            date_from=date(2025, 1, 1),
            date_to=date(2025, 1, 31),
        )
        invoices, total = await repository.list_with_filters(params)

        assert len(invoices) == 0
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_lien_eligible_filter(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices filtered by lien eligibility."""
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.lien_eligible = True

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(lien_eligible=True)
        invoices, total = await repository.list_with_filters(params)

        assert len(invoices) == 1
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_pagination(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices with pagination."""
        mock_invoice = MagicMock(spec=Invoice)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(page=3, page_size=10)
        _invoices, total = await repository.list_with_filters(params)

        assert total == 50
        assert mock_session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_sorting_asc(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices with ascending sort."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(sort_by="invoice_date", sort_order="asc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()

    @pytest.mark.asyncio
    async def test_list_sorting_desc(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test listing invoices with descending sort."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        params = InvoiceListParams(sort_by="total_amount", sort_order="desc")
        await repository.list_with_filters(params)

        mock_session.execute.assert_awaited()


@pytest.mark.unit
class TestInvoiceRepositoryGetNextSequence:
    """Tests for InvoiceRepository.get_next_sequence method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_next_sequence_returns_value(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting next sequence value."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result

        result = await repository.get_next_sequence()

        assert result == 42
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_next_sequence_default_value(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test getting next sequence when result is None."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_next_sequence()

        assert result == 1


@pytest.mark.unit
class TestInvoiceRepositoryFindOverdue:
    """Tests for InvoiceRepository.find_overdue method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_find_overdue_with_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding overdue invoices when they exist."""
        mock_invoice1 = MagicMock(spec=Invoice)
        mock_invoice1.due_date = date.today() - timedelta(days=5)
        mock_invoice1.status = "sent"
        mock_invoice2 = MagicMock(spec=Invoice)
        mock_invoice2.due_date = date.today() - timedelta(days=10)
        mock_invoice2.status = "viewed"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice1, mock_invoice2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_overdue()

        assert len(result) == 2
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_overdue_no_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding overdue invoices when none exist."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_overdue()

        assert result == []


@pytest.mark.unit
class TestInvoiceRepositoryFindLienWarningDue:
    """Tests for InvoiceRepository.find_lien_warning_due method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_find_lien_warning_due_with_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices needing lien warning."""
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.lien_eligible = True
        mock_invoice.invoice_date = date.today() - timedelta(days=50)
        mock_invoice.lien_warning_sent = None

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_lien_warning_due()

        assert len(result) == 1
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_lien_warning_due_no_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices needing lien warning when none exist."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_lien_warning_due()

        assert result == []

    @pytest.mark.asyncio
    async def test_find_lien_warning_due_custom_threshold(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices with custom days threshold."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        await repository.find_lien_warning_due(days_threshold=30)

        mock_session.execute.assert_awaited_once()


@pytest.mark.unit
class TestInvoiceRepositoryFindLienFilingDue:
    """Tests for InvoiceRepository.find_lien_filing_due method."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def repository(self, mock_session: AsyncMock) -> InvoiceRepository:
        """Create repository with mock session."""
        return InvoiceRepository(mock_session)

    @pytest.mark.asyncio
    async def test_find_lien_filing_due_with_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices needing lien filing."""
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.lien_eligible = True
        mock_invoice.invoice_date = date.today() - timedelta(days=125)
        mock_invoice.lien_filed_date = None

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_invoice]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_lien_filing_due()

        assert len(result) == 1
        mock_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_find_lien_filing_due_no_results(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices needing lien filing when none exist."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.find_lien_filing_due()

        assert result == []

    @pytest.mark.asyncio
    async def test_find_lien_filing_due_custom_threshold(
        self,
        repository: InvoiceRepository,
        mock_session: AsyncMock,
    ) -> None:
        """Test finding invoices with custom days threshold."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        await repository.find_lien_filing_due(days_threshold=90)

        mock_session.execute.assert_awaited_once()
