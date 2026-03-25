"""InvoicePortalService for token-based public invoice access.

Generates UUID tokens with 90-day expiry for customer invoice viewing.
Returns sanitized invoice data without internal IDs.

Validates: CRM Gap Closure Req 84.1, 84.2, 84.7, 84.8, 84.9
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.invoice import Invoice
from grins_platform.schemas.portal import PortalInvoiceResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Token validity period
INVOICE_TOKEN_EXPIRY_DAYS = 90


class InvoiceTokenExpiredError(Exception):
    """Raised when an invoice token has expired."""

    def __init__(self) -> None:
        super().__init__("Invoice token has expired")


class InvoiceTokenNotFoundError(Exception):
    """Raised when an invoice token is not found."""

    def __init__(self) -> None:
        super().__init__("Invoice not found or token invalid")


class InvoicePortalService(LoggerMixin):
    """Service for token-based public invoice access.

    Generates UUID tokens with 90-day expiry for invoices.
    Returns sanitized invoice data without internal IDs.

    Validates: CRM Gap Closure Req 84.1, 84.2, 84.7, 84.8, 84.9
    """

    DOMAIN = "portal"

    async def generate_invoice_token(
        self,
        db: AsyncSession,
        invoice_id: UUID,
    ) -> str:
        """Generate a UUID token with 90-day expiry for an invoice.

        Args:
            db: Database session.
            invoice_id: Invoice UUID.

        Returns:
            Generated token string.

        Raises:
            ValueError: If invoice not found.

        Validates: Req 84.1
        """
        self.log_started(
            "generate_invoice_token",
            invoice_id=str(invoice_id),
        )

        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if invoice is None:
            self.log_rejected(
                "generate_invoice_token",
                reason="invoice_not_found",
                invoice_id=str(invoice_id),
            )
            msg = f"Invoice {invoice_id} not found"
            raise ValueError(msg)

        token = uuid.uuid4()
        invoice.invoice_token = token
        invoice.invoice_token_expires_at = datetime.now(
            tz=timezone.utc,
        ) + timedelta(days=INVOICE_TOKEN_EXPIRY_DAYS)
        await db.flush()

        self.log_completed(
            "generate_invoice_token",
            invoice_id=str(invoice_id),
            token=str(token),
        )
        return str(token)

    async def get_invoice_by_token(
        self,
        db: AsyncSession,
        token: str,
    ) -> PortalInvoiceResponse:
        """Retrieve invoice data by token without internal IDs.

        Args:
            db: Database session.
            token: Invoice access token string.

        Returns:
            PortalInvoiceResponse with sanitized invoice data.

        Raises:
            InvoiceTokenNotFoundError: If token not found.
            InvoiceTokenExpiredError: If token has expired.

        Validates: Req 84.2, 84.8, 84.9
        """
        self.log_started("get_invoice_by_token")

        try:
            token_uuid = UUID(token)
        except ValueError:
            raise InvoiceTokenNotFoundError from None

        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.customer))  # type: ignore[arg-type]
            .where(Invoice.invoice_token == token_uuid)
        )
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if invoice is None:
            self.log_rejected(
                "get_invoice_by_token",
                reason="token_not_found",
            )
            raise InvoiceTokenNotFoundError

        # Check expiry
        if invoice.invoice_token_expires_at is not None:
            now = datetime.now(tz=timezone.utc)
            expires_at = invoice.invoice_token_expires_at
            # Make expires_at timezone-aware if it isn't
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now > expires_at:
                self.log_rejected(
                    "get_invoice_by_token",
                    reason="token_expired",
                )
                raise InvoiceTokenExpiredError

        # Get company branding
        company_info = await self._get_company_info(db)

        # Calculate balance
        paid_amount = invoice.paid_amount or Decimal(0)
        balance = invoice.total_amount - paid_amount

        # Build sanitized response (no internal IDs)
        portal_response = PortalInvoiceResponse(
            invoice_number=invoice.invoice_number,
            invoice_date=str(invoice.invoice_date),
            due_date=str(invoice.due_date),
            line_items=invoice.line_items,
            total=invoice.total_amount,
            paid=paid_amount,
            balance=balance,
            status=invoice.status,
            payment_link=None,  # Stripe link would be set by payment integration
            company_name=company_info.get("company_name"),
            company_address=company_info.get("company_address"),
            company_phone=company_info.get("company_phone"),
            company_logo_url=company_info.get("company_logo_url"),
        )

        self.log_completed("get_invoice_by_token")
        return portal_response

    async def _get_company_info(
        self,
        db: AsyncSession,
    ) -> dict[str, str]:
        """Read company info from business_settings.

        Args:
            db: Database session.

        Returns:
            Dict with company branding fields.
        """
        from grins_platform.models.business_setting import (  # noqa: PLC0415
            BusinessSetting,
        )

        defaults: dict[str, str] = {
            "company_name": "Grins Irrigation",
            "company_address": "",
            "company_phone": "",
            "company_logo_url": "",
        }

        stmt = select(BusinessSetting).where(
            BusinessSetting.setting_key == "company_info",
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting and setting.setting_value:
            for k, v in setting.setting_value.items():
                if k in defaults and isinstance(v, str):
                    defaults[k] = v

        return defaults

    def get_portal_invoice_url(self, token: str) -> str:
        """Generate the portal invoice URL for notifications.

        Args:
            token: Invoice access token.

        Returns:
            Portal URL string.

        Validates: Req 84.7
        """
        return f"/portal/invoices/{token}"
