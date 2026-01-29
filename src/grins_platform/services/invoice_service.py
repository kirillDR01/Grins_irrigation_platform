"""Invoice Service for invoice management operations.

This service handles the business logic for creating, updating,
and managing invoices including payments and lien tracking.

Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, cast
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import InvoiceStatus
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceLineItem,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdate,
    LienDeadlineInvoice,
    LienDeadlineResponse,
    PaginatedInvoiceResponse,
    PaymentRecord,
)

if TYPE_CHECKING:
    from grins_platform.models.invoice import Invoice
    from grins_platform.repositories.invoice_repository import InvoiceRepository
    from grins_platform.repositories.job_repository import JobRepository


# Job types that are eligible for mechanic's lien (Requirement 11.1)
LIEN_ELIGIBLE_TYPES: set[str] = {
    "installation",
    "major_repair",
    "new_system",
    "system_upgrade",
}


class InvoiceNotFoundError(Exception):
    """Raised when an invoice is not found."""

    def __init__(self, invoice_id: UUID) -> None:
        self.invoice_id = invoice_id
        super().__init__(f"Invoice not found: {invoice_id}")


class InvalidInvoiceOperationError(Exception):
    """Raised when an invalid invoice operation is attempted."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvoiceService(LoggerMixin):
    """Service for invoice management operations.

    This class handles all business logic for invoice management,
    including creation, status transitions, payments, and lien tracking.

    Attributes:
        invoice_repository: Repository for invoice operations
        job_repository: Repository for job operations

    Validates: Requirements 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8
    """

    DOMAIN = "invoice"

    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        job_repository: JobRepository,
    ) -> None:
        """Initialize service with repositories.

        Args:
            invoice_repository: Repository for invoice operations
            job_repository: Repository for job operations
        """
        super().__init__()
        self.invoice_repository = invoice_repository
        self.job_repository = job_repository

    async def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number.

        Format: INV-{YEAR}-{SEQUENCE}

        Returns:
            Unique invoice number string

        Validates: Requirement 7.1
        """
        year = date.today().year
        seq = await self.invoice_repository.get_next_sequence()
        return f"INV-{year}-{seq:06d}"

    async def create_invoice(self, data: InvoiceCreate) -> InvoiceResponse:
        """Create a new invoice.

        Args:
            data: Invoice creation data

        Returns:
            Created invoice response

        Validates: Requirements 7.1-7.10
        """
        self.log_started("create_invoice", job_id=str(data.job_id))

        # Get job to determine customer and lien eligibility
        job = await self.job_repository.get_by_id(data.job_id)
        if not job:
            err = InvalidInvoiceOperationError("Job not found")
            self.log_failed("create_invoice", error=err)
            raise err

        # Generate invoice number
        invoice_number = await self._generate_invoice_number()

        # Calculate total amount
        total_amount = data.amount + data.late_fee_amount

        # Determine lien eligibility based on job type
        lien_eligible = job.job_type.lower() in LIEN_ELIGIBLE_TYPES

        # Convert line items to dict format for storage
        line_items_data: list[dict[str, object]] | None = None
        if data.line_items:
            line_items_data = [item.model_dump() for item in data.line_items]

        # Create invoice
        invoice = await self.invoice_repository.create(
            job_id=data.job_id,
            customer_id=job.customer_id,
            invoice_number=invoice_number,
            amount=data.amount,
            late_fee_amount=data.late_fee_amount,
            total_amount=total_amount,
            due_date=data.due_date,
            lien_eligible=lien_eligible,
            line_items=line_items_data,
            notes=data.notes,
        )

        self.log_completed(
            "create_invoice",
            invoice_id=str(invoice.id),
            invoice_number=invoice_number,
        )
        return cast("InvoiceResponse", InvoiceResponse.model_validate(invoice))

    async def get_invoice(self, invoice_id: UUID) -> InvoiceResponse:
        """Get an invoice by ID.

        Args:
            invoice_id: The invoice ID

        Returns:
            Invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 13.1
        """
        self.log_started("get_invoice", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("get_invoice", error=err)
            raise err

        self.log_completed("get_invoice", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(invoice))

    async def get_invoice_detail(self, invoice_id: UUID) -> InvoiceDetailResponse:
        """Get invoice with job and customer details.

        Args:
            invoice_id: The invoice ID

        Returns:
            Invoice detail response with job and customer info

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 13.1
        """
        self.log_started("get_invoice_detail", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(
            invoice_id,
            include_relationships=True,
        )
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("get_invoice_detail", error=err)
            raise err

        # Build response with related data
        response_data = InvoiceResponse.model_validate(invoice).model_dump()
        response_data["job_description"] = (
            invoice.job.description if invoice.job else None
        )
        if invoice.customer:
            response_data["customer_name"] = (
                f"{invoice.customer.first_name} {invoice.customer.last_name}"
            )
            response_data["customer_phone"] = invoice.customer.phone
            response_data["customer_email"] = invoice.customer.email
        else:
            response_data["customer_name"] = None
            response_data["customer_phone"] = None
            response_data["customer_email"] = None

        self.log_completed("get_invoice_detail", invoice_id=str(invoice_id))
        return cast(
            "InvoiceDetailResponse",
            InvoiceDetailResponse.model_validate(response_data),
        )

    async def update_invoice(
        self,
        invoice_id: UUID,
        data: InvoiceUpdate,
    ) -> InvoiceResponse:
        """Update an invoice (draft only).

        Args:
            invoice_id: The invoice ID
            data: Update data

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found
            InvalidInvoiceOperationError: If invoice is not in draft status

        Validates: Requirements 7.1-7.10
        """
        self.log_started("update_invoice", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("update_invoice", error=err)
            raise err

        if invoice.status != InvoiceStatus.DRAFT.value:
            self.log_rejected(
                "update_invoice",
                reason="Can only update draft invoices",
            )
            msg = "Can only update invoices in draft status"
            raise InvalidInvoiceOperationError(
                msg,
            )

        # Build update kwargs
        update_data: dict[str, object] = {}
        if data.amount is not None:
            update_data["amount"] = data.amount
        if data.late_fee_amount is not None:
            update_data["late_fee_amount"] = data.late_fee_amount
        if data.due_date is not None:
            update_data["due_date"] = data.due_date
        if data.line_items is not None:
            update_data["line_items"] = [item.model_dump() for item in data.line_items]
        if data.notes is not None:
            update_data["notes"] = data.notes

        # Recalculate total if amounts changed
        if "amount" in update_data or "late_fee_amount" in update_data:
            amount = update_data.get("amount", invoice.amount)
            late_fee = update_data.get("late_fee_amount", invoice.late_fee_amount)
            if isinstance(amount, Decimal) and isinstance(late_fee, Decimal):
                update_data["total_amount"] = amount + late_fee

        updated = await self.invoice_repository.update(invoice_id, **update_data)
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed("update_invoice", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    async def cancel_invoice(self, invoice_id: UUID) -> None:
        """Cancel an invoice.

        Args:
            invoice_id: The invoice ID

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 8.9
        """
        self.log_started("cancel_invoice", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("cancel_invoice", error=err)
            raise err

        _ = await self.invoice_repository.update(
            invoice_id,
            status=InvoiceStatus.CANCELLED.value,
        )

        self.log_completed("cancel_invoice", invoice_id=str(invoice_id))

    async def list_invoices(
        self,
        params: InvoiceListParams,
    ) -> PaginatedInvoiceResponse:
        """List invoices with pagination and filters.

        Args:
            params: Query parameters

        Returns:
            Paginated invoice response

        Validates: Requirements 13.1-13.7
        """
        self.log_started(
            "list_invoices",
            page=params.page,
            page_size=params.page_size,
        )

        invoices, total = await self.invoice_repository.list_with_filters(params)

        total_pages = (total + params.page_size - 1) // params.page_size

        self.log_completed("list_invoices", count=len(invoices), total=total)
        return PaginatedInvoiceResponse(
            items=[
                cast("InvoiceResponse", InvoiceResponse.model_validate(inv))
                for inv in invoices
            ],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )

    # =========================================================================
    # Status Operations (Requirements 8.1-8.6)
    # =========================================================================

    async def send_invoice(self, invoice_id: UUID) -> InvoiceResponse:
        """Mark invoice as sent (draft → sent).

        Args:
            invoice_id: The invoice ID

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found
            InvalidInvoiceOperationError: If not in draft status

        Validates: Requirement 8.2
        """
        self.log_started("send_invoice", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("send_invoice", error=err)
            raise err

        if invoice.status != InvoiceStatus.DRAFT.value:
            self.log_rejected(
                "send_invoice",
                reason="Invoice not in draft status",
            )
            msg = "Can only send invoices in draft status"
            raise InvalidInvoiceOperationError(
                msg,
            )

        updated = await self.invoice_repository.update(
            invoice_id,
            status=InvoiceStatus.SENT.value,
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed("send_invoice", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    async def mark_viewed(self, invoice_id: UUID) -> InvoiceResponse:
        """Mark invoice as viewed (sent → viewed).

        Args:
            invoice_id: The invoice ID

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 8.3
        """
        self.log_started("mark_viewed", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("mark_viewed", error=err)
            raise err

        result_invoice = invoice
        # Only transition from sent to viewed
        if invoice.status == InvoiceStatus.SENT.value:
            updated = await self.invoice_repository.update(
                invoice_id,
                status=InvoiceStatus.VIEWED.value,
            )
            if not updated:
                raise InvoiceNotFoundError(invoice_id)
            result_invoice = updated

        self.log_completed("mark_viewed", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(result_invoice))

    async def mark_overdue(self, invoice_id: UUID) -> InvoiceResponse:
        """Mark invoice as overdue.

        Args:
            invoice_id: The invoice ID

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 8.5
        """
        self.log_started("mark_overdue", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("mark_overdue", error=err)
            raise err

        updated = await self.invoice_repository.update(
            invoice_id,
            status=InvoiceStatus.OVERDUE.value,
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed("mark_overdue", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    # =========================================================================
    # Payment Operations (Requirements 9.1-9.7)
    # =========================================================================

    async def record_payment(
        self,
        invoice_id: UUID,
        payment: PaymentRecord,
    ) -> InvoiceResponse:
        """Record a payment on an invoice.

        Args:
            invoice_id: The invoice ID
            payment: Payment details

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirements 9.1-9.7
        """
        self.log_started(
            "record_payment",
            invoice_id=str(invoice_id),
            amount=str(payment.amount),
        )

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("record_payment", error=err)
            raise err

        # Calculate new paid amount
        current_paid = invoice.paid_amount or Decimal(0)
        new_paid_amount = current_paid + payment.amount

        # Determine new status based on payment
        if new_paid_amount >= invoice.total_amount:
            new_status = InvoiceStatus.PAID.value
        else:
            new_status = InvoiceStatus.PARTIAL.value

        updated = await self.invoice_repository.update(
            invoice_id,
            paid_amount=new_paid_amount,
            payment_method=payment.payment_method.value,
            payment_reference=payment.payment_reference,
            paid_at=datetime.now(timezone.utc),
            status=new_status,
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed(
            "record_payment",
            invoice_id=str(invoice_id),
            new_status=new_status,
        )
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    # =========================================================================
    # Reminder Operations (Requirements 12.1-12.5)
    # =========================================================================

    async def send_reminder(self, invoice_id: UUID) -> InvoiceResponse:
        """Send a payment reminder for an invoice.

        Args:
            invoice_id: The invoice ID

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirements 12.1-12.5
        """
        self.log_started("send_reminder", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("send_reminder", error=err)
            raise err

        updated = await self.invoice_repository.update(
            invoice_id,
            reminder_count=invoice.reminder_count + 1,
            last_reminder_sent=datetime.now(timezone.utc),
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed(
            "send_reminder",
            invoice_id=str(invoice_id),
            reminder_count=updated.reminder_count,
        )
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    # =========================================================================
    # Lien Operations (Requirements 11.1-11.8)
    # =========================================================================

    async def send_lien_warning(self, invoice_id: UUID) -> InvoiceResponse:
        """Send 45-day lien warning for an invoice.

        Args:
            invoice_id: The invoice ID

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 11.6
        """
        self.log_started("send_lien_warning", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("send_lien_warning", error=err)
            raise err

        updated = await self.invoice_repository.update(
            invoice_id,
            lien_warning_sent=datetime.now(timezone.utc),
            status=InvoiceStatus.LIEN_WARNING.value,
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed("send_lien_warning", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    async def mark_lien_filed(
        self,
        invoice_id: UUID,
        filing_date: date,
    ) -> InvoiceResponse:
        """Mark lien as filed for an invoice.

        Args:
            invoice_id: The invoice ID
            filing_date: Date the lien was filed

        Returns:
            Updated invoice response

        Raises:
            InvoiceNotFoundError: If invoice not found

        Validates: Requirement 11.7
        """
        self.log_started(
            "mark_lien_filed",
            invoice_id=str(invoice_id),
            filing_date=str(filing_date),
        )

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if not invoice:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("mark_lien_filed", error=err)
            raise err

        updated = await self.invoice_repository.update(
            invoice_id,
            lien_filed_date=filing_date,
            status=InvoiceStatus.LIEN_FILED.value,
        )
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        self.log_completed("mark_lien_filed", invoice_id=str(invoice_id))
        return cast("InvoiceResponse", InvoiceResponse.model_validate(updated))

    async def get_lien_deadlines(self) -> LienDeadlineResponse:
        """Get invoices approaching lien deadlines.

        Returns:
            Response with invoices approaching 45-day and 120-day deadlines

        Validates: Requirements 11.4-11.5
        """
        self.log_started("get_lien_deadlines")

        # Get invoices approaching 45-day warning
        warning_invoices = await self.invoice_repository.find_lien_warning_due()

        # Get invoices approaching 120-day filing
        filing_invoices = await self.invoice_repository.find_lien_filing_due()

        today = date.today()

        def to_deadline_invoice(inv: Invoice) -> LienDeadlineInvoice:
            days_overdue = (today - inv.due_date).days if inv.due_date < today else 0
            return LienDeadlineInvoice(
                id=inv.id,
                invoice_number=inv.invoice_number,
                customer_id=inv.customer_id,
                customer_name=None,  # Would need to join customer
                amount=inv.amount,
                total_amount=inv.total_amount,
                due_date=inv.due_date,
                days_overdue=days_overdue,
            )

        self.log_completed(
            "get_lien_deadlines",
            warning_count=len(warning_invoices),
            filing_count=len(filing_invoices),
        )
        return LienDeadlineResponse(
            approaching_45_day=[to_deadline_invoice(inv) for inv in warning_invoices],
            approaching_120_day=[to_deadline_invoice(inv) for inv in filing_invoices],
        )

    # =========================================================================
    # Generate from Job (Requirements 10.1-10.7)
    # =========================================================================

    async def generate_from_job(self, job_id: UUID) -> InvoiceResponse:
        """Generate an invoice from a completed job.

        Args:
            job_id: The job ID

        Returns:
            Created invoice response

        Raises:
            InvalidInvoiceOperationError: If job not found, deleted, or payment
                was collected on site

        Validates: Requirements 10.1-10.7
        """
        self.log_started("generate_from_job", job_id=str(job_id))

        job = await self.job_repository.get_by_id(job_id)
        if not job:
            err = InvalidInvoiceOperationError("Job not found")
            self.log_failed("generate_from_job", error=err)
            raise err

        if job.is_deleted:
            self.log_rejected(
                "generate_from_job",
                reason="Job is deleted",
            )
            msg = "Cannot generate invoice for deleted job"
            raise InvalidInvoiceOperationError(
                msg,
            )

        if job.payment_collected_on_site:
            self.log_rejected(
                "generate_from_job",
                reason="Payment already collected on site",
            )
            msg = "Cannot generate invoice - payment was collected on site"
            raise InvalidInvoiceOperationError(
                msg,
            )

        # Use final_amount if present, otherwise quoted_amount
        amount = job.final_amount or job.quoted_amount or Decimal(0)

        # Create line items from job
        line_items: list[InvoiceLineItem] = []
        description = job.description[:500] if job.description else job.job_type
        if description:
            line_items.append(
                InvoiceLineItem(
                    description=description,
                    quantity=Decimal(1),
                    unit_price=amount,
                    total=amount,
                ),
            )

        # Default due date is 30 days from today
        due_date = date.today() + timedelta(days=30)

        invoice_data = InvoiceCreate(
            job_id=job_id,
            amount=amount,
            late_fee_amount=Decimal(0),
            due_date=due_date,
            line_items=line_items if line_items else None,
            notes=f"Invoice generated from job: {job.job_type}",
        )

        result = await self.create_invoice(invoice_data)

        self.log_completed(
            "generate_from_job",
            job_id=str(job_id),
            invoice_id=str(result.id),
        )
        return result
