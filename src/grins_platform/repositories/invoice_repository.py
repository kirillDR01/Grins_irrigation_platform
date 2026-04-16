"""Invoice Repository for invoice database operations.

Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload, selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
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

    def _date_column_for_type(
        self,
        date_type: str,
    ) -> InstrumentedAttribute:  # type: ignore[type-arg]
        """Return the Invoice column matching the date_type string."""
        if date_type == "due":
            return Invoice.due_date
        if date_type == "paid":
            return Invoice.paid_at
        return Invoice.invoice_date  # default: created

    def _build_filters(
        self,
        params: InvoiceListParams,
    ) -> list[Any]:
        """Build a list of SQLAlchemy filter clauses from params.

        Validates: Requirement 28.1 — 9-axis composable AND filtering.
        """
        filters: list[Any] = []

        # Axis 1: Status
        if params.status:
            filters.append(Invoice.status == params.status.value)

        # Axis 2: Customer
        if params.customer_id:
            filters.append(Invoice.customer_id == params.customer_id)

        # Axis 2b: Customer name search
        if params.customer_search:
            search_term = f"%{params.customer_search}%"
            filters.append(
                Invoice.customer_id.in_(
                    select(Customer.id).where(
                        or_(
                            func.concat(
                                Customer.first_name,
                                " ",
                                Customer.last_name,
                            ).ilike(search_term),
                            Customer.first_name.ilike(search_term),
                            Customer.last_name.ilike(search_term),
                        ),
                    ),
                ),
            )

        # Axis 3: Job
        if params.job_id:
            filters.append(Invoice.job_id == params.job_id)

        # Axis 4: Date range (created/due/paid)
        date_col = self._date_column_for_type(params.date_type)
        if params.date_from:
            filters.append(date_col >= params.date_from)
        if params.date_to:
            filters.append(date_col <= params.date_to)

        # Axis 5: Amount range
        if params.amount_min is not None:
            filters.append(Invoice.total_amount >= params.amount_min)
        if params.amount_max is not None:
            filters.append(Invoice.total_amount <= params.amount_max)

        # Axis 6: Payment type (multi-select)
        if params.payment_types:
            types = [t.strip() for t in params.payment_types.split(",") if t.strip()]
            if types:
                filters.append(Invoice.payment_method.in_(types))

        # Axis 7: Days until due (positive = future due date)
        today = date.today()
        if params.days_until_due_min is not None:
            min_date = today + timedelta(days=params.days_until_due_min)
            filters.append(Invoice.due_date >= min_date)
        if params.days_until_due_max is not None:
            max_date = today + timedelta(days=params.days_until_due_max)
            filters.append(Invoice.due_date <= max_date)

        # Axis 8: Days past due (positive = overdue)
        if params.days_past_due_min is not None:
            cutoff = today - timedelta(days=params.days_past_due_min)
            filters.append(Invoice.due_date <= cutoff)
        if params.days_past_due_max is not None:
            cutoff = today - timedelta(days=params.days_past_due_max)
            filters.append(Invoice.due_date >= cutoff)

        # Axis 9: Invoice number (exact match)
        if params.invoice_number:
            filters.append(Invoice.invoice_number == params.invoice_number)

        # Legacy: lien eligibility
        if params.lien_eligible is not None:
            filters.append(Invoice.lien_eligible == params.lien_eligible)

        return filters

    async def list_with_filters(
        self,
        params: InvoiceListParams,
    ) -> tuple[list[Invoice], int]:
        """List invoices with pagination and 9-axis composable AND filters.

        Args:
            params: Query parameters for filtering and pagination

        Returns:
            Tuple of (list of invoices, total count)

        Validates: Requirement 28.1
        """
        self.log_started(
            "list_with_filters",
            page=params.page,
            page_size=params.page_size,
        )

        # Base query — eager-load customer for customer_name in list response
        stmt = select(Invoice).options(joinedload(Invoice.customer))
        count_stmt = select(func.count(Invoice.id))

        # Apply all filter axes (AND composition)
        for clause in self._build_filters(params):
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)

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

    async def get_pending_metrics(self) -> tuple[int, Decimal]:
        """Get count and total amount of pending invoices.

        Pending invoices are those with status SENT or VIEWED
        (not yet paid).

        Returns:
            Tuple of (count, total_amount)

        Validates: CRM Gap Closure Req 5.2
        """
        self.log_started("get_pending_metrics")

        pending_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
        ]

        count_stmt = select(func.count(Invoice.id)).where(
            Invoice.status.in_(pending_statuses),
        )
        total_stmt = select(
            func.coalesce(func.sum(Invoice.total_amount), Decimal(0)),
        ).where(
            Invoice.status.in_(pending_statuses),
        )

        count_result = await self.session.execute(count_stmt)
        count = count_result.scalar() or 0

        total_result = await self.session.execute(total_stmt)
        total_amount = total_result.scalar() or Decimal(0)

        self.log_completed(
            "get_pending_metrics",
            count=count,
            total_amount=str(total_amount),
        )
        return int(count), Decimal(str(total_amount))

    async def find_past_due(self) -> list[Invoice]:
        """Find all past-due invoices with customer eager-loaded.

        Returns:
            List of past-due invoices with customer relationship loaded.

        Validates: Requirement 29.3
        """
        self.log_started("find_past_due")

        today = date.today()
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
        ]

        stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(Invoice.due_date < today)
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.due_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_past_due", count=len(invoices))
        return invoices

    async def find_due_soon(self, days_window: int = 7) -> list[Invoice]:
        """Find invoices due within the given days window.

        Args:
            days_window: Number of days ahead to look.

        Returns:
            List of due-soon invoices with customer relationship loaded.

        Validates: Requirement 29.3
        """
        self.log_started("find_due_soon", days_window=days_window)

        today = date.today()
        cutoff = today + timedelta(days=days_window)
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
        ]

        stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(Invoice.due_date >= today)
            .where(Invoice.due_date <= cutoff)
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.due_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_due_soon", count=len(invoices))
        return invoices

    async def find_lien_eligible(
        self,
        days_past_due: int = 60,
        min_amount: Decimal = Decimal(500),
    ) -> list[Invoice]:
        """Find invoices eligible for lien notice.

        Criteria: past due by ``days_past_due``+ days AND total >= ``min_amount``.

        Args:
            days_past_due: Minimum days past due.
            min_amount: Minimum total amount.

        Returns:
            List of lien-eligible invoices with customer relationship loaded.

        Validates: Requirement 29.3
        """
        self.log_started(
            "find_lien_eligible",
            days_past_due=days_past_due,
            min_amount=str(min_amount),
        )

        cutoff = date.today() - timedelta(days=days_past_due)
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
            InvoiceStatus.LIEN_WARNING.value,
        ]

        stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(Invoice.due_date <= cutoff)
            .where(Invoice.total_amount >= min_amount)
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.due_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed("find_lien_eligible", count=len(invoices))
        return invoices

    async def find_lien_eligible_for_customer(
        self,
        customer_id: UUID,
        days_past_due: int = 60,
        min_amount: Decimal = Decimal(500),
    ) -> list[Invoice]:
        """Find lien-eligible invoices for a single customer.

        Mirrors :meth:`find_lien_eligible` with an extra ``customer_id``
        filter so the admin's per-row "Send Notice" action re-runs the
        eligibility check against the latest DB state before sending.

        Validates: CR-5 (bughunt 2026-04-16).
        """
        self.log_started(
            "find_lien_eligible_for_customer",
            customer_id=str(customer_id),
            days_past_due=days_past_due,
            min_amount=str(min_amount),
        )

        cutoff = date.today() - timedelta(days=days_past_due)
        active_statuses = [
            InvoiceStatus.SENT.value,
            InvoiceStatus.VIEWED.value,
            InvoiceStatus.PARTIAL.value,
            InvoiceStatus.OVERDUE.value,
            InvoiceStatus.LIEN_WARNING.value,
        ]

        stmt = (
            select(Invoice)
            .options(joinedload(Invoice.customer))
            .where(Invoice.customer_id == customer_id)
            .where(Invoice.due_date <= cutoff)
            .where(Invoice.total_amount >= min_amount)
            .where(Invoice.status.in_(active_statuses))
            .order_by(Invoice.due_date.asc())
        )

        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())

        self.log_completed(
            "find_lien_eligible_for_customer",
            customer_id=str(customer_id),
            count=len(invoices),
        )
        return invoices
