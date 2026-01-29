"""Invoice Repository for invoice database operations.

Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import InvoiceStatus
from grins_platform.models.invoice import Invoice
from grins_platform.schemas.invoice import InvoiceListParams


class InvoiceRepository(LoggerMixin):
    """Repository for invoice database operations."""

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(
        self,
        job_id: UUID,
        customer_id: UUID,
        invoice_number: str,
        amount: Decimal,
        total_amount: Decimal,
        due_date: date,
        late_fee_amount: Decimal = Decimal(0),
        invoice_date: date | None = None,
        status: str = "draft",
        lien_eligible: bool = False,
        line_items: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> Invoice:
        """Create a new invoice record.

        Args:
            job_id: Reference to the job
            customer_id: Reference to the customer
            invoice_number: Unique invoice number
            amount: Base invoice amount
            total_amount: Total amount (amount + late_fee)
            due_date: Payment due date
            late_fee_amount: Late fee amount
            invoice_date: Date invoice was created
            status: Invoice status
            lien_eligible: Whether job type is lien-eligible
            line_items: JSONB array of line items
            notes: Optional notes

        Returns:
            The created invoice
        """
        self.log_started(
            "create",
            job_id=str(job_id),
            invoice_number=invoice_number,
        )

        invoice = Invoice(
            job_id=job_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            late_fee_amount=late_fee_amount,
            total_amount=total_amount,
            invoice_date=invoice_date or date.today(),
            due_date=due_date,
            status=status,
            lien_eligible=lien_eligible,
            line_items=line_items,
            notes=notes,
        )

        self.session.add(invoice)
        await self.session.flush()
        await self.session.refresh(invoice)

        self.log_completed("create", invoice_id=str(invoice.id))
        return invoice

    async def get_by_id(
        self,
        invoice_id: UUID,
        include_relationships: bool = False,
    ) -> Invoice | None:
        """Get an invoice by ID.

        Args:
            invoice_id: The invoice ID
            include_relationships: Whether to load job and customer

        Returns:
            The invoice or None if not found
        """
        self.log_started("get_by_id", invoice_id=str(invoice_id))

        stmt = select(Invoice).where(Invoice.id == invoice_id)

        if include_relationships:
            stmt = stmt.options(
                selectinload(Invoice.job),
                selectinload(Invoice.customer),
            )

        result = await self.session.execute(stmt)
        invoice: Invoice | None = result.scalar_one_or_none()

        self.log_completed("get_by_id", found=invoice is not None)
        return invoice

    async def update(
        self,
        invoice_id: UUID,
        **kwargs: Any,
    ) -> Invoice | None:
        """Update an invoice record.

        Args:
            invoice_id: The invoice ID
            **kwargs: Fields to update

        Returns:
            The updated invoice or None if not found
        """
        self.log_started("update", invoice_id=str(invoice_id))

        invoice = await self.get_by_id(invoice_id)
        if not invoice:
            self.log_completed("update", found=False)
            return None

        for key, value in kwargs.items():
            if hasattr(invoice, key):
                setattr(invoice, key, value)

        await self.session.flush()
        await self.session.refresh(invoice)

        self.log_completed("update", invoice_id=str(invoice.id))
        return invoice

    async def list_with_filters(
        self,
        params: InvoiceListParams,
    ) -> tuple[list[Invoice], int]:
        """List invoices with pagination and filters.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            Tuple of (list of invoices, total count)
        """
        self.log_started(
            "list_with_filters",
            page=params.page,
            page_size=params.page_size,
        )

        # Base query
        stmt = select(Invoice)
        count_stmt = select(func.count(Invoice.id))

        # Apply filters
        if params.status:
            stmt = stmt.where(Invoice.status == params.status.value)
            count_stmt = count_stmt.where(Invoice.status == params.status.value)

        if params.customer_id:
            stmt = stmt.where(Invoice.customer_id == params.customer_id)
            count_stmt = count_stmt.where(Invoice.customer_id == params.customer_id)

        if params.date_from:
            stmt = stmt.where(Invoice.invoice_date >= params.date_from)
            count_stmt = count_stmt.where(Invoice.invoice_date >= params.date_from)

        if params.date_to:
            stmt = stmt.where(Invoice.invoice_date <= params.date_to)
            count_stmt = count_stmt.where(Invoice.invoice_date <= params.date_to)

        if params.lien_eligible is not None:
            stmt = stmt.where(Invoice.lien_eligible == params.lien_eligible)
            count_stmt = count_stmt.where(Invoice.lien_eligible == params.lien_eligible)

        # Get total count
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply sorting
        sort_column = getattr(Invoice, params.sort_by, Invoice.created_at)
        if params.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Apply pagination
        offset = (params.page - 1) * params.page_size
        stmt = stmt.offset(offset).limit(params.page_size)

        # Execute query
        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(invoices), total=total)
        return invoices, total

    async def get_next_sequence(self) -> int:
        """Get the next invoice number sequence value.

        Returns:
            The next sequence value
        """
        self.log_started("get_next_sequence")

        result = await self.session.execute(
            text("SELECT nextval('invoice_number_seq')"),
        )
        seq_value = result.scalar() or 1

        self.log_completed("get_next_sequence", value=seq_value)
        return int(seq_value)

    async def find_overdue(self) -> list[Invoice]:
        """Find all overdue invoices.

        Returns invoices where:
        - due_date < today
        - status is sent, viewed, or partial (not paid, cancelled, etc.)

        Returns:
            List of overdue invoices
        """
        self.log_started("find_overdue")

        today = date.today()
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
        ]

        stmt = (
            select(Invoice)
            .where(Invoice.due_date < today)
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.due_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_overdue", count=len(invoices))
        return invoices

    async def find_lien_warning_due(self, days_threshold: int = 45) -> list[Invoice]:
        """Find invoices approaching 45-day lien warning deadline.

        Args:
            days_threshold: Days since invoice date to trigger warning

        Returns:
            List of invoices needing lien warning
        """
        self.log_started("find_lien_warning_due", days_threshold=days_threshold)

        cutoff_date = date.today() - timedelta(days=days_threshold)
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
        ]

        stmt = (
            select(Invoice)
            .where(Invoice.lien_eligible.is_(True))
            .where(Invoice.invoice_date <= cutoff_date)
            .where(Invoice.lien_warning_sent.is_(None))
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.invoice_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_lien_warning_due", count=len(invoices))
        return invoices

    async def find_lien_filing_due(self, days_threshold: int = 120) -> list[Invoice]:
        """Find invoices approaching 120-day lien filing deadline.

        Args:
            days_threshold: Days since invoice date to trigger filing

        Returns:
            List of invoices needing lien filing
        """
        self.log_started("find_lien_filing_due", days_threshold=days_threshold)

        cutoff_date = date.today() - timedelta(days=days_threshold)
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
            InvoiceStatus.LIEN_WARNING.value,
        ]

        stmt = (
            select(Invoice)
            .where(Invoice.lien_eligible.is_(True))
            .where(Invoice.invoice_date <= cutoff_date)
            .where(Invoice.lien_filed_date.is_(None))
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.invoice_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_lien_filing_due", count=len(invoices))
        return invoices
