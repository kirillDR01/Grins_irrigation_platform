"""Invoice Service for invoice management operations.

This service handles the business logic for creating, updating,
and managing invoices including payments and lien tracking.

Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, Literal, cast
from uuid import UUID

from grins_platform.exceptions import (
    InvalidInvoiceOperationError,
    InvoiceNotFoundError,
    LeadOnlyInvoiceError,
    NoContactMethodError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import EmailType, InvoiceStatus
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetailResponse,
    InvoiceLineItem,
    InvoiceListParams,
    InvoiceResponse,
    InvoiceUpdate,
    LienCandidateResponse,
    LienDeadlineInvoice,
    LienDeadlineResponse,
    LienNoticeResult,
    MassNotifyResponse,
    PaginatedInvoiceResponse,
    PaymentRecord,
    SendLinkResponse,
)
from grins_platform.services.email_service import EmailRecipientNotAllowedError
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import (
    SMSConsentDeniedError,
    SMSError,
    SMSRateLimitDeniedError,
)
from grins_platform.services.stripe_payment_link_service import (
    StripePaymentLinkError,
)

if TYPE_CHECKING:
    from grins_platform.models.invoice import Invoice
    from grins_platform.repositories.customer_repository import CustomerRepository
    from grins_platform.repositories.invoice_repository import InvoiceRepository
    from grins_platform.repositories.job_repository import JobRepository
    from grins_platform.services.business_setting_service import (
        BusinessSettingService,
    )
    from grins_platform.services.customer_service import CustomerService
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.sms_service import SMSService
    from grins_platform.services.stripe_payment_link_service import (
        StripePaymentLinkService,
    )


# Job types that are eligible for mechanic's lien (Requirement 11.1)
LIEN_ELIGIBLE_TYPES: set[str] = {
    "installation",
    "major_repair",
    "new_system",
    "system_upgrade",
}


class LienMassNotifyDeprecatedError(Exception):
    """Raised when a caller hits ``mass_notify('lien_eligible')``.

    CR-5 moves lien notices out of the fire-and-forget mass path into an
    admin review queue. Callers should use ``compute_lien_candidates`` +
    ``send_lien_notice`` instead. The endpoint layer translates this to
    HTTP 400 with a pointer to the new endpoints.
    """

    def __init__(self) -> None:
        super().__init__(
            "mass_notify('lien_eligible') is deprecated. Use "
            "GET /api/v1/invoices/lien-candidates + "
            "POST /api/v1/invoices/lien-notices/{customer_id}/send instead.",
        )


# bughunt M-14: canonical merge keys for invoice notification templates.
# Spec §11 lists the merge fields as bracket-form
# ``[Customer name] [number] [amount] [date]``; admins writing custom
# templates use either the canonical curly form or the spec brackets.
_REQUIRED_INVOICE_MERGE_KEYS: tuple[str, ...] = (
    "customer_name",
    "invoice_number",
    "amount",
    "due_date",
)
_BRACKET_TO_CANONICAL: dict[str, str] = {
    "[Customer name]": "{customer_name}",
    "[customer name]": "{customer_name}",
    "[number]": "{invoice_number}",
    "[amount]": "{amount}",
    "[date]": "{due_date}",
}


class InvalidInvoiceTemplateError(Exception):
    """Raised when a custom mass-notify template is missing required keys.

    The endpoint layer translates this to HTTP 400 so admins know which
    merge fields they forgot. bughunt M-14.
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        msg = (
            "Custom invoice template is missing required merge keys: "
            + ", ".join(sorted(missing))
            + ". Use the canonical curly-brace form (e.g. {customer_name}) "
            "or the spec brackets (e.g. [Customer name])."
        )
        super().__init__(msg)


def render_invoice_template(
    template: str,
    *,
    customer_name: str,
    invoice_number: str,
    amount: str,
    due_date: str,
) -> str:
    """Render a mass-notify template with the canonical merge keys.

    Accepts both the canonical curly form (``{customer_name}``) and the
    spec brackets (``[Customer name]``). Bracket forms are translated
    to canonical form at parse time so the rendering always uses one
    code path. Required keys are documented in
    :data:`_REQUIRED_INVOICE_MERGE_KEYS`.

    bughunt M-14.
    """
    canonical = template
    for bracket, curly in _BRACKET_TO_CANONICAL.items():
        canonical = canonical.replace(bracket, curly)
    return canonical.format(
        customer_name=customer_name,
        invoice_number=invoice_number,
        amount=amount,
        due_date=due_date,
    )


def validate_invoice_template(template: str) -> None:
    """Reject custom templates that drop a required merge key.

    Caller (mass_notify) raises :class:`InvalidInvoiceTemplateError` so
    the endpoint can return 400 with the offending keys named.
    """
    canonical = template
    for bracket, curly in _BRACKET_TO_CANONICAL.items():
        canonical = canonical.replace(bracket, curly)
    missing = [
        key for key in _REQUIRED_INVOICE_MERGE_KEYS if "{" + key + "}" not in canonical
    ]
    if missing:
        raise InvalidInvoiceTemplateError(missing)


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
        business_settings: BusinessSettingService | None = None,
        *,
        customer_repository: CustomerRepository | None = None,
        customer_service: CustomerService | None = None,
        payment_link_service: StripePaymentLinkService | None = None,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        """Initialize service with repositories.

        Args:
            invoice_repository: Repository for invoice operations
            job_repository: Repository for job operations
            business_settings: Optional :class:`BusinessSettingService` used
                by :meth:`compute_lien_candidates` and :meth:`mass_notify` to
                read firm-wide defaults from the ``business_settings`` table.
                If ``None`` (legacy / unit-test constructions), the service
                lazily instantiates one against the repository's session when
                first needed. Dependency injection in the API layer passes
                this explicitly. See H-12 (bughunt 2026-04-16).
            customer_repository: Optional :class:`CustomerRepository` used by
                the Payment Link send-flow (plan §Phase 2.7).
            customer_service: Optional :class:`CustomerService` used to
                ensure a Stripe Customer exists before creating a Payment
                Link (plan §Phase 2.5).
            payment_link_service: Optional :class:`StripePaymentLinkService`
                used to create / deactivate Payment Links (plan §Phase 2.4).
            sms_service: Optional :class:`SMSService` used by the Payment
                Link delivery path (plan §Phase 2.7). When ``None`` the
                send-link flow falls straight to email.
            email_service: Optional :class:`EmailService` used by the
                Payment Link email-fallback path (plan §Phase 2.7).
        """
        super().__init__()
        self.invoice_repository = invoice_repository
        self.job_repository = job_repository
        self._settings = business_settings
        self.customer_repository = customer_repository
        self.customer_service = customer_service
        self.payment_link_service = payment_link_service
        self.sms_service = sms_service
        self.email_service = email_service

    def _get_settings_service(self) -> BusinessSettingService:
        """Return (and cache) a :class:`BusinessSettingService`.

        Lazy so unit tests that pass in a mocked repo with a ``.session``
        attribute still work without having to construct the settings
        service themselves. The API layer's DI should inject one via the
        ``business_settings`` constructor argument instead.
        """
        if self._settings is None:
            from grins_platform.services.business_setting_service import (  # noqa: PLC0415
                BusinessSettingService,
            )

            self._settings = BusinessSettingService(
                self.invoice_repository.session,
            )
        return self._settings

    async def _resolve_lien_defaults(
        self,
        days_past_due: int | None,
        min_amount: float | None,
    ) -> tuple[int, Decimal]:
        """Coalesce per-call lien thresholds against the business settings.

        If the caller passed explicit values they win (backwards-compat +
        one-time overrides). Otherwise we pull defaults from the
        ``business_settings`` table via :class:`BusinessSettingService`.
        Final fallback: the hard-coded CR-5 defaults (60 days, $500).
        """
        settings = self._get_settings_service()
        resolved_days = (
            days_past_due
            if days_past_due is not None
            else await settings.get_int("lien_days_past_due", 60)
        )
        resolved_amount = (
            Decimal(str(min_amount))
            if min_amount is not None
            else await settings.get_decimal("lien_min_amount", Decimal(500))
        )
        return resolved_days, resolved_amount

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
            line_items_data = [item.model_dump(mode="json") for item in data.line_items]

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

        # Phase 2.5: best-effort Payment Link auto-creation. The hook
        # mirrors the new link fields onto ``invoice`` directly so the
        # response below reflects them without a separate refetch.
        await self._attach_payment_link(invoice)

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

        # Phase 2.6: detect changes that should regenerate the Payment Link.
        # Only line_items or total_amount drive regeneration — notes/due_date
        # changes don't affect the Stripe-side amount.
        old_total = invoice.total_amount
        old_line_items = invoice.line_items
        new_total = update_data.get("total_amount", old_total)
        new_line_items = update_data.get("line_items", old_line_items)
        link_inputs_changed = new_total != old_total or new_line_items != old_line_items

        updated = await self.invoice_repository.update(invoice_id, **update_data)
        if not updated:
            raise InvoiceNotFoundError(invoice_id)

        if link_inputs_changed:
            # Best-effort regenerate: persists new link to DB. The
            # response shape below may show stale link fields if Stripe
            # refresh raced; the next GET returns the new state.
            await self._regenerate_payment_link(updated)

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

        items: list[InvoiceResponse] = []
        for inv in invoices:
            resp = InvoiceResponse.model_validate(inv)
            # Populate customer_name from eager-loaded relationship
            if hasattr(inv, "customer") and inv.customer is not None:
                cust = inv.customer
                resp.customer_name = f"{cust.first_name} {cust.last_name}"
            items.append(cast("InvoiceResponse", resp))

        return PaginatedInvoiceResponse(
            items=items,
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
    # Stripe Payment Link Operations (Architecture C — plan §Phase 2)
    # =========================================================================

    async def _attach_payment_link(
        self,
        invoice: Invoice,
    ) -> None:
        """Best-effort Payment Link creation hook.

        Idempotent: re-running on an invoice that already has an active
        Payment Link is a no-op. Failures (Stripe outage, missing
        customer, $0 invoice) are logged but never raise — the invoice
        is still saved and the link is created lazily on first
        ``send_payment_link`` attempt.

        Validates: Stripe Payment Links plan §Phase 2.5.
        """
        if (
            invoice.stripe_payment_link_id is not None
            and invoice.stripe_payment_link_active
        ):
            # Already attached and live — nothing to do.
            return

        if self.payment_link_service is None or self.customer_repository is None:
            # Best-effort wiring; missing DI means tests / legacy callers.
            self.logger.debug(
                "payment.invoice.attach_payment_link_skipped_missing_di",
                invoice_id=str(invoice.id),
            )
            return

        customer = await self.customer_repository.get_by_id(invoice.customer_id)
        if customer is None:
            self.logger.warning(
                "payment.invoice.attach_payment_link_no_customer",
                invoice_id=str(invoice.id),
                customer_id=str(invoice.customer_id),
            )
            return

        # Make sure a Stripe customer exists so receipts auto-send. Do not
        # fail invoice creation if Stripe linking has a transient outage.
        if self.customer_service is not None:
            try:
                await self.customer_service.get_or_create_stripe_customer(
                    customer.id,
                )
            except Exception as exc:
                self.logger.warning(
                    "payment.invoice.stripe_customer_link_failed",
                    invoice_id=str(invoice.id),
                    error=str(exc),
                )

        try:
            link_id, link_url = self.payment_link_service.create_for_invoice(
                invoice,
                customer,
            )
        except StripePaymentLinkError as exc:
            self.logger.warning(
                "payment.invoice.create_failed_at_invoice_creation",
                invoice_id=str(invoice.id),
                error=str(exc),
            )
            return

        if link_id is None:
            # F11: $0 invoice — no link, no persistence.
            return

        await self.invoice_repository.update(
            invoice.id,
            stripe_payment_link_id=link_id,
            stripe_payment_link_url=link_url,
            stripe_payment_link_active=True,
        )
        # Also mirror the new fields onto the in-memory object so callers
        # who already hold the invoice see the new state without a refetch.
        invoice.stripe_payment_link_id = link_id
        invoice.stripe_payment_link_url = link_url
        invoice.stripe_payment_link_active = True

    async def _regenerate_payment_link(
        self,
        invoice: Invoice,
    ) -> None:
        """Deactivate the old Payment Link and create a fresh one.

        Used by :meth:`update_invoice` when ``line_items`` or
        ``total_amount`` change (plan §Phase 2.6). Best-effort: any
        failure is logged and the invoice update still wins.
        """
        if self.payment_link_service is None:
            return
        old_id = invoice.stripe_payment_link_id
        if old_id is not None and invoice.stripe_payment_link_active:
            try:
                self.payment_link_service.deactivate(old_id)
            except StripePaymentLinkError as exc:
                self.logger.warning(
                    "payment.invoice.deactivate_failed_during_regenerate",
                    invoice_id=str(invoice.id),
                    error=str(exc),
                )
        # Force a re-attach by zeroing the cached fields on the loaded model
        # (the database row is updated in _attach_payment_link).
        invoice.stripe_payment_link_id = None
        invoice.stripe_payment_link_url = None
        invoice.stripe_payment_link_active = False
        await self._attach_payment_link(invoice)
        self.logger.info(
            "payment.invoice.payment_link_regenerated",
            invoice_id=str(invoice.id),
            old_link_id_suffix=(old_id[-6:] if old_id else None),
        )

    async def send_payment_link(
        self,
        invoice_id: UUID,
    ) -> SendLinkResponse:
        """Deliver the Stripe Payment Link to the customer.

        Tries SMS first (transactional, bypasses ``sms_opt_in`` per F12),
        then falls back to Resend email (transactional, bypasses
        ``email_opt_in``). Hard-STOP customers fall through to email
        cleanly. If neither channel can deliver, raises
        ``NoContactMethodError``.

        Lazy-creates the Payment Link if it's missing (covers the
        best-effort failure case from :meth:`_attach_payment_link`).
        Refuses $0 invoices (no link possible) and Lead-only invoices
        (D12 backend safety net).

        Validates: Stripe Payment Links plan §Phase 2.7.
        """
        self.log_started("send_payment_link", invoice_id=str(invoice_id))

        invoice = await self.invoice_repository.get_by_id(invoice_id)
        if invoice is None:
            err = InvoiceNotFoundError(invoice_id)
            self.log_failed("send_payment_link", error=err)
            raise err

        if invoice.total_amount == Decimal(0):
            self.log_rejected(
                "send_payment_link",
                reason="zero_amount",
                invoice_id=str(invoice_id),
            )
            msg = "Cannot send payment link for $0 invoice"
            raise InvalidInvoiceOperationError(msg)

        if self.customer_repository is None:
            msg = "InvoiceService.customer_repository is required for send_payment_link"
            raise RuntimeError(msg)
        customer = await self.customer_repository.get_by_id(invoice.customer_id)
        if customer is None:
            self.log_rejected(
                "send_payment_link",
                reason="lead_only",
                invoice_id=str(invoice_id),
            )
            raise LeadOnlyInvoiceError(invoice_id)

        # Lazy-create if missing (covers best-effort failures at create time).
        if (
            invoice.stripe_payment_link_url is None
            or not invoice.stripe_payment_link_active
        ):
            await self._attach_payment_link(invoice)
            refreshed = await self.invoice_repository.get_by_id(invoice_id)
            if refreshed is None:
                raise InvoiceNotFoundError(invoice_id)
            invoice = refreshed

        if invoice.stripe_payment_link_url is None:
            # Lazy-create still failed — Stripe down or another error.
            self.log_failed(
                "send_payment_link",
                error=None,
                invoice_id=str(invoice_id),
                reason="lazy_create_failed",
            )
            msg = (
                f"Could not generate a Stripe Payment Link for invoice "
                f"{invoice_id}; check Stripe status."
            )
            raise InvalidInvoiceOperationError(msg)

        body = self._build_payment_link_sms_body(customer, invoice)

        attempted_channels: list[Literal["sms", "email"]] = []
        sms_failure_reason: (
            Literal["consent", "rate_limit", "provider_error", "no_phone"] | None
        ) = None

        # SMS path — transactional, bypasses sms_opt_in per F12.
        if customer.phone and self.sms_service is not None:
            attempted_channels.append("sms")
            recipient = Recipient(
                phone=customer.phone,
                source_type="customer",
                customer_id=customer.id,
                first_name=customer.first_name,
                last_name=customer.last_name,
            )
            try:
                result = await self.sms_service.send_message(
                    recipient=recipient,
                    message=body,
                    message_type=MessageType.PAYMENT_LINK,
                    consent_type="transactional",
                )
                if result.get("success") is True:
                    return await self._record_link_sent(
                        invoice,
                        channel="sms",
                        attempted_channels=attempted_channels,
                        sms_failure_reason=None,
                    )
                sms_failure_reason = "provider_error"
                self.logger.warning(
                    "payment.send_link.sms_failed_soft",
                    invoice_id=str(invoice.id),
                    status=result.get("status"),
                )
            except SMSConsentDeniedError:
                sms_failure_reason = "consent"
                # Customer hard-STOP'd — fall through to email.
                self.logger.info(
                    "payment.send_link.sms_blocked_by_consent",
                    invoice_id=str(invoice.id),
                )
            except SMSRateLimitDeniedError as exc:
                sms_failure_reason = "rate_limit"
                self.logger.warning(
                    "payment.send_link.sms_failed_hard",
                    invoice_id=str(invoice.id),
                    error=str(exc),
                )
            except SMSError as exc:
                sms_failure_reason = "provider_error"
                self.logger.warning(
                    "payment.send_link.sms_failed_hard",
                    invoice_id=str(invoice.id),
                    error=str(exc),
                )
        elif customer.phone is None:
            sms_failure_reason = "no_phone"

        # Email fallback — transactional, bypasses email_opt_in per F12.
        if customer.email and self.email_service is not None:
            attempted_channels.append("email")
            html_body, text_body = self._render_payment_link_email(
                customer,
                invoice,
            )
            try:
                sent = self.email_service._send_email(  # noqa: SLF001 — established pattern
                    to_email=customer.email,
                    subject=(
                        f"Your invoice from Grin's Irrigation — ${invoice.total_amount}"
                    ),
                    html_body=html_body,
                    text_body=text_body,
                    email_type="payment_link",
                    classification=EmailType.TRANSACTIONAL,
                )
            except EmailRecipientNotAllowedError:
                self.logger.warning(
                    "payment.send_link.email_blocked_by_allowlist",
                    invoice_id=str(invoice.id),
                    recipient_last4=(customer.email[-4:] if customer.email else None),
                )
                sent = False
            if sent:
                return await self._record_link_sent(
                    invoice,
                    channel="email",
                    attempted_channels=attempted_channels,
                    sms_failure_reason=sms_failure_reason,
                )

        self.log_rejected(
            "send_payment_link",
            reason="no_contact_method",
            invoice_id=str(invoice_id),
        )
        raise NoContactMethodError(invoice_id)

    @staticmethod
    def _build_payment_link_sms_body(
        customer: object,
        invoice: Invoice,
    ) -> str:
        """Render the D4 short SMS template for Payment Links."""
        first_name = getattr(customer, "first_name", "") or "there"
        return (
            f"Hi {first_name}, your invoice from Grin's Irrigation for "
            f"${invoice.total_amount} is ready: "
            f"{invoice.stripe_payment_link_url}"
        )

    def _render_payment_link_email(
        self,
        customer: object,
        invoice: Invoice,
    ) -> tuple[str, str]:
        """Render the email body (HTML + plaintext) for the Payment Link.

        Uses the Jinja2 templates at
        ``templates/emails/payment_link_email.{html,txt}`` per plan
        §Phase 4.3. Defaults (``business_name``, ``business_phone``,
        ``business_email``) are injected by ``EmailService._render_template``.
        Falls back to a minimal inline body if the email service or
        templates are unavailable so callers never crash on render.
        """
        first_name = getattr(customer, "first_name", "") or "there"
        context = {
            "customer_first_name": first_name,
            "invoice_number": invoice.invoice_number,
            "total_amount": str(invoice.total_amount),
            "payment_link_url": invoice.stripe_payment_link_url,
        }

        if self.email_service is not None:
            try:
                html_body = self.email_service._render_template(  # noqa: SLF001 — established pattern
                    "payment_link_email.html",
                    context,
                )
                text_body = self.email_service._render_template(  # noqa: SLF001
                    "payment_link_email.txt",
                    context,
                )
            except Exception as exc:  # pragma: no cover — defensive fallback
                self.logger.warning(
                    "payment.send_link.email_template_render_failed",
                    invoice_id=str(invoice.id),
                    error=str(exc),
                )
            else:
                return html_body, text_body

        link = invoice.stripe_payment_link_url
        amount = invoice.total_amount
        invoice_number = invoice.invoice_number
        html_body = (
            f"<p>Hi {first_name},</p>"
            f"<p>Your invoice <strong>{invoice_number}</strong> from "
            f"Grin's Irrigation is ready. The total is "
            f"<strong>${amount}</strong>.</p>"
            f'<p><a href="{link}">Pay invoice</a></p>'
            f"<p>Or copy this link into your browser:<br/>"
            f'<a href="{link}">{link}</a></p>'
            f"<p>Thanks,<br/>Grin's Irrigation</p>"
        )
        text_body = (
            f"Hi {first_name},\n\n"
            f"Your invoice {invoice_number} from Grin's Irrigation is "
            f"ready. The total is ${amount}.\n\n"
            f"Pay here: {link}\n\n"
            f"Thanks,\nGrin's Irrigation"
        )
        return html_body, text_body

    async def _record_link_sent(
        self,
        invoice: Invoice,
        *,
        channel: str,
        attempted_channels: list[Literal["sms", "email"]],
        sms_failure_reason: (
            Literal["consent", "rate_limit", "provider_error", "no_phone"] | None
        ) = None,
    ) -> SendLinkResponse:
        """Increment send count + persist sent_at; return SendLinkResponse."""
        now = datetime.now(timezone.utc)
        new_count = invoice.payment_link_sent_count + 1
        await self.invoice_repository.update(
            invoice.id,
            payment_link_sent_at=now,
            payment_link_sent_count=new_count,
        )
        self.log_completed(
            "send_payment_link",
            invoice_id=str(invoice.id),
            channel=channel,
            sent_count=new_count,
        )
        return SendLinkResponse(
            channel=channel,  # type: ignore[arg-type]
            link_url=str(invoice.stripe_payment_link_url),
            sent_at=now,
            sent_count=new_count,
            attempted_channels=attempted_channels,
            sms_failure_reason=sms_failure_reason,
        )

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

    # =========================================================================
    # Mass Notification (Requirement 29.3, 29.4)
    # =========================================================================

    # bughunt M-14: defaults use the canonical merge keys
    # (customer_name / invoice_number / amount / due_date). The spec's
    # bracket form is also accepted by render_invoice_template().
    _DEFAULT_TEMPLATES: ClassVar[dict[str, str]] = {
        "past_due": (
            "{customer_name}, invoice {invoice_number} for ${amount} was due "
            "on {due_date} and is now past due. Please remit payment at your "
            "earliest convenience."
        ),
        "due_soon": (
            "{customer_name}, this is a reminder that invoice "
            "{invoice_number} for ${amount} is due on {due_date}."
        ),
        "lien_eligible": (
            "{customer_name}, invoice {invoice_number} for ${amount} (due "
            "{due_date}) is significantly past due. Please contact us "
            "immediately to arrange payment and avoid further action."
        ),
    }

    async def mass_notify(
        self,
        notification_type: str,
        *,
        due_soon_days: int | None = None,
        lien_days_past_due: int | None = None,  # noqa: ARG002
        lien_min_amount: float | None = None,  # noqa: ARG002
        template: str | None = None,
    ) -> MassNotifyResponse:
        """Send mass notifications to customers based on invoice criteria.

        Args:
            notification_type: One of past_due, due_soon, lien_eligible.
            due_soon_days: Days window for due-soon targeting. ``None`` reads
                ``upcoming_due_days`` from the ``business_settings`` table
                (default 7). Accepted for back-compat / one-time override.
            lien_days_past_due: Deprecated one-time override (lien branch is
                routed through the review queue now — CR-5). Ignored here.
            lien_min_amount: Deprecated one-time override (see above).
            template: Custom message template (uses default if None).

        Returns:
            MassNotifyResponse with counts.

        Validates: Requirements 29.3, 29.4; H-12 (persisted defaults).
        """
        # CR-5: mass_notify("lien_eligible") is deprecated — admins must
        # send lien notices via the review queue instead. Endpoint layer
        # translates this to HTTP 400.
        if notification_type == "lien_eligible":
            raise LienMassNotifyDeprecatedError

        self.log_started(
            "mass_notify",
            notification_type=notification_type,
        )

        # H-12: resolve due-soon window from BusinessSettings when caller
        # didn't pass an explicit override.
        if due_soon_days is None:
            settings = self._get_settings_service()
            due_soon_days = await settings.get_int("upcoming_due_days", 7)

        # Discover target invoices
        invoices: list[Invoice]
        if notification_type == "past_due":
            invoices = await self.invoice_repository.find_past_due()
        elif notification_type == "due_soon":
            invoices = await self.invoice_repository.find_due_soon(due_soon_days)
        else:
            invoices = []

        targeted = len(invoices)
        sent = 0
        failed = 0
        skipped = 0
        skipped_count = 0
        skipped_reasons: dict[str, int] = {}

        msg_template = template or self._DEFAULT_TEMPLATES.get(
            notification_type,
            self._DEFAULT_TEMPLATES["past_due"],
        )

        # bughunt M-14: validate admin-supplied templates so we 400 with
        # named missing keys instead of failing per-row inside the loop.
        # Defaults are vouched for by InvoiceService and don't need
        # re-validation on every request.
        if template is not None:
            validate_invoice_template(template)

        # H-11: batch SMS-consent pre-filter. One query resolves the opt-out
        # set for every targeted customer, so we don't hand STOPed customers
        # to SMSService.send_message (which would raise and silently bump
        # `failed`). The lien branch already has a per-customer check via
        # ``send_lien_notice`` (CR-5) — this covers the past_due / due_soon
        # branches at batch granularity.
        from grins_platform.repositories.sms_consent_repository import (  # noqa: PLC0415
            SmsConsentRepository,
        )

        candidate_customer_ids: list[UUID] = [
            inv.customer.id  # type: ignore[union-attr]
            for inv in invoices
            if inv.customer is not None and getattr(inv.customer, "id", None)
        ]
        consent_repo = SmsConsentRepository(self.invoice_repository.session)
        opted_out_ids = await consent_repo.get_opted_out_customer_ids(
            customer_ids=candidate_customer_ids,
        )

        for inv in invoices:
            try:
                customer = inv.customer  # type: ignore[union-attr]
                if customer is None or not getattr(customer, "phone", None):
                    skipped += 1
                    continue

                # H-11: filter opted-out customers before any SMS dispatch so
                # the send loop doesn't blow up into `failed` on STOPed phones.
                if customer.id in opted_out_ids:
                    skipped_reasons["opted_out"] = (
                        skipped_reasons.get("opted_out", 0) + 1
                    )
                    skipped_count += 1
                    continue

                # bughunt M-14: render through the canonical helper using
                # the spec's full ``customer_name`` (first + last) instead
                # of `first_name` only. The helper also accepts the spec's
                # bracket form for admin-supplied templates.
                full_name = " ".join(
                    p
                    for p in [
                        getattr(customer, "first_name", None),
                        getattr(customer, "last_name", None),
                    ]
                    if p
                )
                body = render_invoice_template(
                    msg_template,
                    customer_name=full_name,
                    invoice_number=inv.invoice_number,
                    amount=f"{inv.total_amount:.2f}",
                    due_date=inv.due_date.isoformat() if inv.due_date else "",
                )

                # Import SMS dependencies lazily to avoid circular imports
                from grins_platform.schemas.ai import (  # noqa: PLC0415
                    MessageType,
                )
                from grins_platform.services.sms.recipient import (  # noqa: PLC0415
                    Recipient,
                )
                from grins_platform.services.sms_service import (  # noqa: PLC0415
                    SMSService,
                )

                sms_service = SMSService(
                    self.invoice_repository.session,
                )
                recipient = Recipient.from_customer(customer)
                await sms_service.send_message(
                    recipient=recipient,
                    message=body,
                    message_type=MessageType.PAYMENT_REMINDER,
                    consent_type="transactional",
                )

                # Update reminder count
                await self.invoice_repository.update(
                    inv.id,
                    reminder_count=inv.reminder_count + 1,
                    last_reminder_sent=datetime.now(timezone.utc),
                )
                sent += 1
            except Exception:
                self.logger.warning(
                    "invoice.mass_notify.single_failure",
                    invoice_id=str(inv.id),
                    notification_type=notification_type,
                )
                failed += 1

        self.log_completed(
            "mass_notify",
            notification_type=notification_type,
            targeted=targeted,
            sent=sent,
            failed=failed,
            skipped=skipped,
            skipped_count=skipped_count,
            skipped_reasons=skipped_reasons,
        )
        return MassNotifyResponse(
            notification_type=notification_type,
            targeted=targeted,
            sent=sent,
            failed=failed,
            skipped=skipped,
            skipped_count=skipped_count,
            skipped_reasons=skipped_reasons,
        )

    async def compute_lien_candidates(
        self,
        *,
        days_past_due: int | None = None,
        min_amount: float | None = None,
    ) -> list[LienCandidateResponse]:
        """Build the admin review queue of lien-eligible customers.

        Groups :meth:`InvoiceRepository.find_lien_eligible` by customer
        so the admin sees one row per customer with the aggregated
        oldest-invoice age and total past-due amount.

        When ``days_past_due`` / ``min_amount`` are ``None``, defaults come
        from the ``business_settings`` table (H-12). Explicit values still
        win so one-time overrides stay possible.

        Validates: CR-5 (bughunt 2026-04-16); H-12 (persisted defaults).
        """
        resolved_days, resolved_amount = await self._resolve_lien_defaults(
            days_past_due,
            min_amount,
        )

        self.log_started(
            "compute_lien_candidates",
            days_past_due=resolved_days,
            min_amount=float(resolved_amount),
        )

        invoices = await self.invoice_repository.find_lien_eligible(
            days_past_due=resolved_days,
            min_amount=resolved_amount,
        )

        # Group by customer_id.
        today = date.today()
        by_customer: dict[UUID, dict[str, object]] = {}
        for inv in invoices:
            customer = inv.customer  # type: ignore[union-attr]
            if customer is None:
                continue
            key = customer.id
            bucket = by_customer.setdefault(
                key,
                {
                    "customer_id": customer.id,
                    "customer_name": (
                        f"{customer.first_name} {customer.last_name}".strip()
                    ),
                    "customer_phone": getattr(customer, "phone", None),
                    "oldest_age": 0,
                    "total": Decimal(0),
                    "invoice_ids": [],
                    "invoice_numbers": [],
                },
            )

            age_days = (today - inv.due_date).days if inv.due_date else 0
            bucket["oldest_age"] = max(int(bucket["oldest_age"]), age_days)  # type: ignore[arg-type]
            bucket["total"] = cast("Decimal", bucket["total"]) + inv.total_amount
            cast("list", bucket["invoice_ids"]).append(inv.id)
            cast("list", bucket["invoice_numbers"]).append(inv.invoice_number)

        candidates: list[LienCandidateResponse] = [
            LienCandidateResponse(
                customer_id=cast("UUID", b["customer_id"]),
                customer_name=cast("str", b["customer_name"]),
                customer_phone=cast("str | None", b["customer_phone"]),
                oldest_invoice_age_days=int(cast("int", b["oldest_age"])),
                total_past_due_amount=cast("Decimal", b["total"]),
                invoice_ids=cast("list[UUID]", b["invoice_ids"]),
                invoice_numbers=cast("list[str]", b["invoice_numbers"]),
            )
            for b in by_customer.values()
        ]

        self.log_completed(
            "compute_lien_candidates",
            count=len(candidates),
        )
        return candidates

    async def send_lien_notice(
        self,
        *,
        customer_id: UUID,
        admin_user_id: UUID | None,
        days_past_due: int | None = None,
        min_amount: float | None = None,
    ) -> LienNoticeResult:
        """Send a single lien-notice SMS after admin approval.

        Re-runs the eligibility check against the current DB state before
        sending, pre-filters for SMS consent (H-11 overlap), dispatches via
        :class:`SMSService`, and writes an AuditLog row
        (``action="invoice.lien_notice.sent"``).

        When ``days_past_due`` / ``min_amount`` are ``None``, defaults come
        from the ``business_settings`` table (H-12).

        Validates: CR-5 (bughunt 2026-04-16); H-12 (persisted defaults).
        """
        resolved_days, resolved_amount = await self._resolve_lien_defaults(
            days_past_due,
            min_amount,
        )

        self.log_started(
            "send_lien_notice",
            customer_id=str(customer_id),
        )

        now = datetime.now(timezone.utc)

        invoices = await self.invoice_repository.find_lien_eligible_for_customer(
            customer_id,
            days_past_due=resolved_days,
            min_amount=resolved_amount,
        )
        if not invoices:
            self.log_completed(
                "send_lien_notice",
                customer_id=str(customer_id),
                result="no_eligible_invoices",
            )
            return LienNoticeResult(
                success=False,
                customer_id=customer_id,
                sent_at=None,
                sms_message_id=None,
                message="no_eligible_invoices",
            )

        customer = invoices[0].customer  # type: ignore[union-attr]
        if customer is None or not getattr(customer, "phone", None):
            return LienNoticeResult(
                success=False,
                customer_id=customer_id,
                sent_at=None,
                sms_message_id=None,
                message="no_phone",
            )

        # SMS consent pre-filter (overlaps H-11).
        from sqlalchemy import select as _select  # noqa: PLC0415

        from grins_platform.models.sms_consent_record import (  # noqa: PLC0415
            SmsConsentRecord,
        )

        consent_stmt = _select(SmsConsentRecord).where(
            SmsConsentRecord.customer_id == customer.id,
        )
        consent_result = await self.invoice_repository.session.execute(consent_stmt)
        consent_record = consent_result.scalars().first()
        if consent_record is not None and not consent_record.consent_given:
            self.log_completed(
                "send_lien_notice",
                customer_id=str(customer_id),
                result="customer_opted_out",
            )
            return LienNoticeResult(
                success=False,
                customer_id=customer_id,
                sent_at=None,
                sms_message_id=None,
                message="customer_opted_out",
            )

        # Build the SMS body from the lien template. Pick the oldest
        # invoice for the template fields (matches mass_notify's
        # behavior). Now uses canonical merge keys (bughunt M-14).
        oldest_inv = invoices[0]
        total_amount = sum(
            (inv.total_amount for inv in invoices),
            start=Decimal(0),
        )
        full_name = " ".join(
            p
            for p in [
                getattr(customer, "first_name", None),
                getattr(customer, "last_name", None),
            ]
            if p
        )
        body = render_invoice_template(
            self._DEFAULT_TEMPLATES["lien_eligible"],
            customer_name=full_name,
            invoice_number=oldest_inv.invoice_number,
            amount=f"{total_amount:.2f}",
            due_date=oldest_inv.due_date.isoformat() if oldest_inv.due_date else "",
        )

        # Lazy imports to avoid circular references.
        from grins_platform.schemas.ai import (  # noqa: PLC0415
            MessageType,
        )
        from grins_platform.services.sms.recipient import (  # noqa: PLC0415
            Recipient,
        )
        from grins_platform.services.sms_service import (  # noqa: PLC0415
            SMSService,
        )

        sms_service = SMSService(self.invoice_repository.session)
        recipient = Recipient.from_customer(customer)
        send_result = await sms_service.send_message(
            recipient=recipient,
            message=body,
            message_type=MessageType.PAYMENT_REMINDER,
            consent_type="transactional",
        )

        sms_id_raw = (
            send_result.get("message_id") if isinstance(send_result, dict) else None
        )
        sms_id: UUID | None = None
        if isinstance(sms_id_raw, UUID):
            sms_id = sms_id_raw
        elif isinstance(sms_id_raw, str):
            try:
                sms_id = UUID(sms_id_raw)
            except ValueError:
                sms_id = None

        # Bump reminder_count on every notified invoice so the dashboard
        # reflects the outreach.
        for inv in invoices:
            await self.invoice_repository.update(
                inv.id,
                reminder_count=inv.reminder_count + 1,
                last_reminder_sent=now,
            )

        # AuditLog: invoice.lien_notice.sent (mirrors
        # appointment_service._record_cancellation_audit).
        try:
            from grins_platform.repositories.audit_log_repository import (  # noqa: PLC0415
                AuditLogRepository,
            )

            audit_repo = AuditLogRepository(self.invoice_repository.session)
            await audit_repo.create(
                action="invoice.lien_notice.sent",
                resource_type="customer",
                resource_id=customer.id,
                actor_id=admin_user_id,
                details={
                    "admin_user_id": str(admin_user_id) if admin_user_id else None,
                    "customer_id": str(customer.id),
                    "invoice_ids": [str(inv.id) for inv in invoices],
                    "sent_at": now.isoformat(),
                    "sms_message_id": str(sms_id) if sms_id else None,
                },
            )
        except Exception:
            # Audit must never block the SMS dispatch.
            self.log_failed(
                "send_lien_notice_audit",
                customer_id=str(customer_id),
            )

        self.log_completed(
            "send_lien_notice",
            customer_id=str(customer_id),
            result="sent",
            invoice_count=len(invoices),
        )
        return LienNoticeResult(
            success=True,
            customer_id=customer.id,
            sent_at=now,
            sms_message_id=sms_id,
            message="sent",
        )
