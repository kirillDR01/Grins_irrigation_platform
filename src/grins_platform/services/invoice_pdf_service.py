"""InvoicePDFService for generating and managing invoice PDFs.

Generates professional PDFs using WeasyPrint, uploads to S3,
and provides pre-signed download URLs.

Validates: CRM Gap Closure Req 80.2, 80.3, 80.4, 87.7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.invoice import Invoice
from grins_platform.services.photo_service import format_attachment_disposition

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class S3ClientProtocol(Protocol):
    """Protocol for S3 client interface."""

    def put_object(self, **kwargs: Any) -> dict[str, Any]: ...
    def generate_presigned_url(
        self,
        method: str,
        Params: dict[str, str],  # noqa: N803
        ExpiresIn: int,  # noqa: N803
    ) -> str: ...


class InvoicePDFNotFoundError(Exception):
    """Raised when an invoice PDF does not exist."""

    def __init__(self, invoice_id: UUID) -> None:
        super().__init__(f"No PDF found for invoice {invoice_id}")
        self.invoice_id = invoice_id


class InvoiceNotFoundError(Exception):
    """Raised when an invoice does not exist."""

    def __init__(self, invoice_id: UUID) -> None:
        super().__init__(f"Invoice {invoice_id} not found")
        self.invoice_id = invoice_id


class InvoicePDFService(LoggerMixin):
    """Service for invoice PDF generation and management.

    Uses WeasyPrint for HTML→PDF conversion, uploads to S3,
    and manages pre-signed download URLs.

    Reads company branding from business_settings (Req 87.7).

    Validates: CRM Gap Closure Req 80.2, 80.3, 80.4, 87.7
    """

    DOMAIN = "invoice_pdf"

    def __init__(
        self,
        s3_client: S3ClientProtocol | None = None,
        s3_bucket: str = "grins-platform-files",
    ) -> None:
        """Initialize InvoicePDFService.

        Args:
            s3_client: boto3 S3 client instance.
            s3_bucket: S3 bucket name for PDF storage.
        """
        super().__init__()
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket

    async def _get_company_branding(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Read company branding from business_settings.

        Validates: Req 87.7

        Args:
            db: Database session.

        Returns:
            Dict with company_name, company_address, company_phone,
            company_logo_url.
        """
        from grins_platform.models.business_setting import (  # noqa: PLC0415
            BusinessSetting,
        )

        defaults: dict[str, Any] = {
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
            defaults.update(setting.setting_value)

        return defaults

    def _render_invoice_html(
        self,
        invoice: Invoice,
        branding: dict[str, Any],
    ) -> str:
        """Render invoice data as HTML for PDF conversion.

        Args:
            invoice: Invoice model instance.
            branding: Company branding dict.

        Returns:
            HTML string.
        """
        company_name = branding.get("company_name", "Grins Irrigation")
        company_address = branding.get("company_address", "")
        company_phone = branding.get("company_phone", "")
        company_logo_url = branding.get("company_logo_url", "")

        # Build line items HTML
        line_items_html = ""
        if invoice.line_items:
            for item in invoice.line_items:
                desc = item.get("description", "")
                qty = item.get("quantity", 1)
                price = item.get("unit_price", 0)
                total = float(qty) * float(price)
                line_items_html += (
                    f"<tr>"
                    f"<td>{desc}</td>"
                    f"<td style='text-align:center'>{qty}</td>"
                    f"<td style='text-align:right'>${price:.2f}</td>"
                    f"<td style='text-align:right'>${total:.2f}</td>"
                    f"</tr>"
                )

        logo_html = ""
        if company_logo_url:
            logo_html = (
                f'<img src="{company_logo_url}" '
                f'alt="{company_name}" style="max-height:80px;" />'
            )

        customer_name = ""
        if invoice.customer:
            first = getattr(invoice.customer, "first_name", "")
            last = getattr(invoice.customer, "last_name", "")
            customer_name = f"{first} {last}".strip()

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
  .company {{ font-size: 14px; }}
  .company h1 {{ margin: 0; font-size: 24px; color: #2d5016; }}
  .invoice-title {{ font-size: 28px; color: #2d5016; margin-bottom: 20px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; margin-bottom: 30px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  th {{ background: #2d5016; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
  .total-row {{ font-weight: bold; font-size: 16px; }}
  .footer {{ margin-top: 40px; font-size: 12px; color: #666; text-align: center; }}
</style>
</head>
<body>
  <div class="header">
    <div class="company">
      {logo_html}
      <h1>{company_name}</h1>
      <p>{company_address}</p>
      <p>{company_phone}</p>
    </div>
  </div>
  <div class="invoice-title">Invoice {invoice.invoice_number}</div>
  <div class="info-grid">
    <div>
      <strong>Bill To:</strong><br>
      {customer_name}
    </div>
    <div>
      <strong>Invoice Date:</strong> {invoice.invoice_date}<br>
      <strong>Due Date:</strong> {invoice.due_date}<br>
      <strong>Status:</strong> {invoice.status}
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th>Description</th>
        <th style="text-align:center">Qty</th>
        <th style="text-align:right">Unit Price</th>
        <th style="text-align:right">Total</th>
      </tr>
    </thead>
    <tbody>
      {line_items_html}
    </tbody>
  </table>
  <div style="text-align:right; margin-top:20px;">
    <p class="total-row">Total: ${invoice.total_amount:.2f}</p>
  </div>
  {f"<div><strong>Notes:</strong> {invoice.notes}</div>" if invoice.notes else ""}
  <div class="footer">
    <p>Thank you for your business! — {company_name}</p>
  </div>
</body>
</html>"""

    async def generate_pdf(
        self,
        db: AsyncSession,
        invoice_id: UUID,
    ) -> str:
        """Generate a professional PDF for the invoice.

        Renders HTML template with invoice data and company branding,
        converts to PDF via WeasyPrint, uploads to S3, updates
        invoice.document_url.

        Args:
            db: Database session.
            invoice_id: Invoice UUID.

        Returns:
            Pre-signed download URL for the generated PDF.

        Raises:
            InvoiceNotFoundError: If invoice not found.

        Validates: Req 80.2, 80.3, 87.7
        """
        self.log_started("generate_pdf", invoice_id=str(invoice_id))

        # Load invoice with customer
        from sqlalchemy.orm import selectinload  # noqa: PLC0415

        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.customer))  # type: ignore[arg-type]
            .where(Invoice.id == invoice_id)
        )
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if invoice is None:
            raise InvoiceNotFoundError(invoice_id)

        # Get company branding from business_settings (Req 87.7)
        branding = await self._get_company_branding(db)

        # Render HTML
        html_content = self._render_invoice_html(invoice, branding)

        # Convert to PDF via WeasyPrint
        try:
            from weasyprint import HTML  # noqa: PLC0415

            pdf_bytes = HTML(string=html_content).write_pdf()
        except ImportError:
            self.log_failed(
                "generate_pdf",
                error=Exception("WeasyPrint not installed"),
                invoice_id=str(invoice_id),
            )
            raise
        except Exception as exc:
            self.log_failed(
                "generate_pdf",
                error=exc,
                invoice_id=str(invoice_id),
            )
            raise

        # Upload to S3
        s3_key = f"invoices/{invoice_id}.pdf"
        if self.s3_client is not None:
            try:
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=pdf_bytes,
                    ContentType="application/pdf",
                )
            except Exception as exc:
                self.log_failed(
                    "upload_pdf",
                    error=exc,
                    invoice_id=str(invoice_id),
                )
                raise

        # Update invoice.document_url
        invoice.document_url = s3_key
        await db.flush()

        # Generate pre-signed URL — force browser to save-as-file so
        # clicking "Download PDF" in InvoiceDetail actually triggers a
        # download instead of opening the PDF inline in a new tab.
        download_url = self._generate_presigned_url(
            s3_key,
            download_filename=f"{invoice.invoice_number}.pdf",
        )

        self.logger.info(
            "invoice.pdf.generated",
            invoice_id=str(invoice_id),
            invoice_number=invoice.invoice_number,
            s3_key=s3_key,
        )
        self.log_completed("generate_pdf", invoice_id=str(invoice_id))
        return download_url

    async def get_pdf_url(
        self,
        db: AsyncSession,
        invoice_id: UUID,
    ) -> str:
        """Return a pre-signed S3 download URL for an existing invoice PDF.

        Args:
            db: Database session.
            invoice_id: Invoice UUID.

        Returns:
            Pre-signed download URL (1hr expiry).

        Raises:
            InvoiceNotFoundError: If invoice not found.
            InvoicePDFNotFoundError: If document_url is null.

        Validates: Req 80.4
        """
        self.log_started("get_pdf_url", invoice_id=str(invoice_id))

        stmt = select(Invoice).where(Invoice.id == invoice_id)
        result = await db.execute(stmt)
        invoice = result.scalar_one_or_none()

        if invoice is None:
            raise InvoiceNotFoundError(invoice_id)

        if invoice.document_url is None:
            raise InvoicePDFNotFoundError(invoice_id)

        url = self._generate_presigned_url(
            invoice.document_url,
            download_filename=f"{invoice.invoice_number}.pdf",
        )

        self.log_completed("get_pdf_url", invoice_id=str(invoice_id))
        return url

    def _generate_presigned_url(
        self,
        s3_key: str,
        *,
        download_filename: str | None = None,
    ) -> str:
        """Generate a pre-signed S3 download URL.

        When ``download_filename`` is provided, the response carries a
        ``Content-Disposition: attachment; filename=…`` header so the
        browser saves the PDF to disk instead of rendering it inline.

        Args:
            s3_key: S3 object key.
            download_filename: Optional filename for forced download.

        Returns:
            Pre-signed URL string (1hr expiry).
        """
        if self.s3_client is None:
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"

        params: dict[str, Any] = {"Bucket": self.s3_bucket, "Key": s3_key}
        if download_filename:
            params["ResponseContentDisposition"] = format_attachment_disposition(
                download_filename
            )
        try:
            url: str = self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=3600,
            )
        except Exception as exc:
            self.log_failed("generate_presigned_url", error=exc, s3_key=s3_key)
            return f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
        else:
            return url
