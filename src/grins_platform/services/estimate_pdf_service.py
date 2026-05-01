"""EstimatePDFService — generate signed-PDF estimates on portal approval.

Mirrors :class:`InvoicePDFService` but produces a customer-signed PDF
for an :class:`Estimate` with the approval signature, IP, user-agent
and timestamp baked into the document footer.

Decision (umbrella plan AJ-8): for v1 the service does NOT round-trip
through S3. Callers receive the PDF as bytes and attach it directly
to the Resend email. S3 archival is a follow-on enhancement and is
omitted here to keep the call site simple.

Validates: appointment-modal umbrella plan Phase 0 (Task 0.3, AJ-8).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.business_setting import BusinessSetting

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.models.estimate import Estimate


class EstimatePDFService(LoggerMixin):
    """Render a signed-PDF for an approved :class:`Estimate`.

    Reads company branding from ``business_settings`` (same source as
    :class:`InvoicePDFService`), then composes an HTML document with
    line items + total + a signed-by footer (signature digest, IP,
    user-agent, ISO timestamp). WeasyPrint converts to PDF bytes.
    """

    DOMAIN = "estimate_pdf"

    async def _get_company_branding(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Load company branding (name / address / phone / logo)."""
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

    @staticmethod
    def _resolve_recipient_name(estimate: Estimate) -> str:
        """Return a display name for the estimate's recipient."""
        customer = getattr(estimate, "customer", None)
        if customer is not None:
            full_name = getattr(customer, "full_name", None)
            if full_name:
                return str(full_name)
            first = getattr(customer, "first_name", "") or ""
            last = getattr(customer, "last_name", "") or ""
            joined = f"{first} {last}".strip()
            if joined:
                return joined
        lead = getattr(estimate, "lead", None)
        if lead is not None:
            first = getattr(lead, "first_name", "") or ""
            last = getattr(lead, "last_name", "") or ""
            joined = f"{first} {last}".strip()
            if joined:
                return joined
        return "Customer"

    def _render_html(
        self,
        estimate: Estimate,
        branding: dict[str, Any],
    ) -> str:
        """Render estimate data as HTML for PDF conversion.

        The footer includes a "Signed by" block with the customer's
        approval signature (their typed name or token-bound proxy),
        IP address, user-agent and the approval timestamp — these
        are baked into the PDF so the signed copy is reproducible.
        """
        company_name = branding.get("company_name", "Grins Irrigation")
        company_address = branding.get("company_address", "")
        company_phone = branding.get("company_phone", "")
        company_logo_url = branding.get("company_logo_url", "")

        recipient_name = self._resolve_recipient_name(estimate)

        line_items_html = ""
        if estimate.line_items:
            for item in estimate.line_items:
                desc = item.get("description") or item.get("item") or ""
                qty = item.get("quantity", 1)
                price = item.get("unit_price", 0)
                try:
                    qty_f = float(qty)
                    price_f = float(price)
                    total = qty_f * price_f
                except (TypeError, ValueError):
                    qty_f, price_f, total = 0.0, 0.0, 0.0
                line_items_html += (
                    f"<tr>"
                    f"<td>{desc}</td>"
                    f"<td style='text-align:center'>{qty_f:g}</td>"
                    f"<td style='text-align:right'>${price_f:.2f}</td>"
                    f"<td style='text-align:right'>${total:.2f}</td>"
                    f"</tr>"
                )

        logo_html = ""
        if company_logo_url:
            logo_html = (
                f'<img src="{company_logo_url}" '
                f'alt="{company_name}" style="max-height:80px;" />'
            )

        approved_at = getattr(estimate, "approved_at", None)
        approved_at_str = (
            approved_at.isoformat()
            if approved_at
            else datetime.now(tz=timezone.utc).isoformat()
        )
        approved_ip = getattr(estimate, "approved_ip", "") or ""
        approved_ua = getattr(estimate, "approved_user_agent", "") or ""

        valid_until = getattr(estimate, "valid_until", None)
        valid_until_str = ""
        if valid_until is not None:
            try:
                valid_until_str = valid_until.date().isoformat()
            except AttributeError:
                valid_until_str = str(valid_until)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
  .company h1 {{ margin: 0; font-size: 24px; color: #2d5016; }}
  .estimate-title {{ font-size: 28px; color: #2d5016; margin-bottom: 20px; }}
  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; margin-bottom: 30px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  th {{ background: #2d5016; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
  .total-row {{ font-weight: bold; font-size: 16px; }}
  .signature {{ margin-top: 40px; padding-top: 16px;
    border-top: 1px dashed #999; font-size: 12px; color: #555; }}
  .signature .label {{ color: #2d5016; font-weight: bold; }}
  .footer {{ margin-top: 24px; font-size: 12px; color: #666; text-align: center; }}
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
  <div class="estimate-title">Approved Estimate</div>
  <div class="info-grid">
    <div>
      <strong>For:</strong><br>
      {recipient_name}
    </div>
    <div>
      <strong>Estimate ID:</strong> {estimate.id}<br>
      <strong>Valid Until:</strong> {valid_until_str}<br>
      <strong>Status:</strong> {estimate.status}
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
    <p class="total-row">Total: ${float(estimate.total):.2f}</p>
  </div>
  {f"<div><strong>Notes:</strong> {estimate.notes}</div>" if estimate.notes else ""}
  <div class="signature">
    <p class="label">Signed by customer</p>
    <p>Recipient: {recipient_name}</p>
    <p>IP address: {approved_ip}</p>
    <p>User agent: {approved_ua}</p>
    <p>Approved at: {approved_at_str}</p>
  </div>
  <div class="footer">
    Thank you for your business — {company_name}
  </div>
</body>
</html>"""

    async def generate_pdf_bytes(
        self,
        db: AsyncSession,
        estimate: Estimate,
    ) -> bytes:
        """Render and return the signed-PDF bytes for ``estimate``.

        Args:
            db: Active database session (used to read company branding).
            estimate: Estimate whose approval is being archived.

        Returns:
            PDF document as bytes (suitable for Resend attachment).

        Raises:
            ImportError: WeasyPrint missing (deployment misconfig).
        """
        self.log_started("generate_pdf_bytes", estimate_id=str(estimate.id))

        branding = await self._get_company_branding(db)
        html_content = self._render_html(estimate, branding)

        try:
            from weasyprint import HTML  # noqa: PLC0415
        except ImportError:
            self.log_failed(
                "generate_pdf_bytes",
                error=Exception("WeasyPrint not installed"),
                estimate_id=str(estimate.id),
            )
            raise

        try:
            pdf_bytes: bytes = HTML(string=html_content).write_pdf()
        except Exception as exc:
            self.log_failed(
                "generate_pdf_bytes",
                error=exc,
                estimate_id=str(estimate.id),
            )
            raise

        self.log_completed(
            "generate_pdf_bytes",
            estimate_id=str(estimate.id),
            byte_size=len(pdf_bytes),
        )
        return pdf_bytes
