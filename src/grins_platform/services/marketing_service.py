"""Marketing service for lead analytics, CAC, and QR codes.

Provides: lead source analytics, conversion funnel, customer
acquisition cost per channel, and QR code generation with UTM params.

Validates: CRM Gap Closure Req 58, 63, 65
"""

from __future__ import annotations

import io
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlparse, urlunparse

import qrcode  # type: ignore[import-untyped]
from sqlalchemy import case, func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import ExpenseCategory
from grins_platform.models.expense import Expense
from grins_platform.models.lead import Lead
from grins_platform.schemas.marketing import (
    CACBySourceResponse,
    FunnelStage,
    LeadAnalyticsResponse,
    LeadSourceAnalytics,
    QRCodeRequest,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class QRCodeGenerationError(Exception):
    """Raised when QR code generation fails."""

    def __init__(self, message: str = "QR code generation failed") -> None:
        self.message = message
        super().__init__(self.message)


class MarketingService(LoggerMixin):
    """Service for marketing analytics, CAC, and QR codes.

    Validates: CRM Gap Closure Req 58, 63, 65
    """

    DOMAIN = "marketing"

    def __init__(self) -> None:
        """Initialize MarketingService."""
        super().__init__()

    # ------------------------------------------------------------------ #
    # get_lead_analytics -- Req 63.2, 63.3, 63.4, 63.5
    # ------------------------------------------------------------------ #

    async def get_lead_analytics(
        self,
        db: AsyncSession,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> LeadAnalyticsResponse:
        """Get lead source analytics with conversion funnel.

        Args:
            db: Async database session.
            date_from: Start date filter (inclusive).
            date_to: End date filter (inclusive).

        Returns:
            LeadAnalyticsResponse with per-source analytics and funnel.

        Validates: Req 63.2, 63.3, 63.4, 63.5
        """
        self.log_started(
            "get_lead_analytics",
            date_from=str(date_from),
            date_to=str(date_to),
        )

        try:
            conditions: list[object] = []
            if date_from is not None:
                conditions.append(Lead.created_at >= date_from)
            if date_to is not None:
                conditions.append(Lead.created_at <= date_to)

            sources = await self._get_source_analytics(
                db,
                conditions,
            )
            avg_hours = await self._get_avg_conversion_time(
                db,
                conditions,
            )
            funnel = await self._get_funnel(db, conditions)

            total_leads = sum(s.count for s in sources)
            total_converted = sum(s.converted for s in sources)
            overall_rate = (
                round((total_converted / total_leads) * 100, 2)
                if total_leads > 0
                else 0.0
            )
            top_source = max(sources, key=lambda s: s.count).source if sources else None

            response = LeadAnalyticsResponse(
                total_leads=total_leads,
                conversion_rate=overall_rate,
                avg_time_to_conversion_hours=avg_hours,
                top_source=top_source,
                sources=sources,
                funnel=funnel,
            )

            self.log_completed(
                "get_lead_analytics",
                total_leads=total_leads,
                sources_count=len(sources),
            )
        except Exception as e:
            self.log_failed("get_lead_analytics", error=e)
            raise
        else:
            return response

    async def _get_source_analytics(
        self,
        db: AsyncSession,
        conditions: list[object],
    ) -> list[LeadSourceAnalytics]:
        """Query per-source lead counts and conversions."""
        stmt = select(
            Lead.lead_source,
            func.count(Lead.id).label("total"),
            func.sum(
                case((Lead.status == "converted", 1), else_=0),
            ).label("converted"),
        ).group_by(Lead.lead_source)

        for cond in conditions:
            stmt = stmt.where(cond)  # type: ignore[arg-type]

        result = await db.execute(stmt)
        sources: list[LeadSourceAnalytics] = []

        for row in result.all():
            src_name = str(row[0]) if row[0] else "unknown"
            count = int(row[1])
            converted = int(row[2])
            rate = round((converted / count) * 100, 2) if count > 0 else 0.0
            sources.append(
                LeadSourceAnalytics(
                    source=src_name,
                    count=count,
                    converted=converted,
                    conversion_rate=rate,
                ),
            )

        return sources

    async def _get_avg_conversion_time(
        self,
        db: AsyncSession,
        conditions: list[object],
    ) -> float | None:
        """Query average hours from lead creation to conversion."""
        stmt = select(
            func.avg(
                func.extract(
                    "epoch",
                    Lead.converted_at - Lead.created_at,
                )
                / 3600.0,
            ),
        ).where(
            Lead.status == "converted",
            Lead.converted_at.isnot(None),
        )

        for cond in conditions:
            stmt = stmt.where(cond)  # type: ignore[arg-type]

        result = await db.execute(stmt)
        avg_raw = result.scalar()
        if avg_raw is not None:
            return round(float(avg_raw), 2)
        return None

    async def _get_funnel(
        self,
        db: AsyncSession,
        conditions: list[object],
    ) -> list[FunnelStage]:
        """Query conversion funnel stage counts."""
        stmt = select(
            func.count(Lead.id).label("total"),
            func.sum(
                case(
                    (
                        Lead.status.in_(
                            ["contacted", "qualified", "converted"],
                        ),
                        1,
                    ),
                    else_=0,
                ),
            ).label("contacted"),
            func.sum(
                case(
                    (
                        Lead.status.in_(["qualified", "converted"]),
                        1,
                    ),
                    else_=0,
                ),
            ).label("qualified"),
            func.sum(
                case((Lead.status == "converted", 1), else_=0),
            ).label("converted"),
        )

        for cond in conditions:
            stmt = stmt.where(cond)  # type: ignore[arg-type]

        result = await db.execute(stmt)
        row = result.one()

        return [
            FunnelStage(
                stage="Total Leads",
                count=int(row[0] or 0),
            ),
            FunnelStage(
                stage="Contacted",
                count=int(row[1] or 0),
            ),
            FunnelStage(
                stage="Qualified",
                count=int(row[2] or 0),
            ),
            FunnelStage(
                stage="Converted",
                count=int(row[3] or 0),
            ),
        ]

    # ------------------------------------------------------------------ #
    # get_cac -- Req 58.1, 58.2
    # ------------------------------------------------------------------ #

    async def get_cac(
        self,
        db: AsyncSession,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CACBySourceResponse]:
        """Calculate customer acquisition cost per lead source.

        CAC = marketing_spend / converted_customers per source.
        Sources with zero conversions return CAC of 0.

        Args:
            db: Async database session.
            date_from: Start date filter (inclusive).
            date_to: End date filter (inclusive).

        Returns:
            List of CACBySourceResponse per lead source.

        Validates: Req 58.1, 58.2
        """
        self.log_started(
            "get_cac",
            date_from=str(date_from),
            date_to=str(date_to),
        )

        try:
            spend_by_source = await self._get_spend_by_source(
                db,
                date_from,
                date_to,
            )
            conv_by_source = await self._get_conversions_by_source(
                db,
                date_from,
                date_to,
            )

            all_sources = sorted(
                set(spend_by_source) | set(conv_by_source),
            )

            results: list[CACBySourceResponse] = []
            for source in all_sources:
                spend = spend_by_source.get(source, Decimal(0))
                customers = conv_by_source.get(source, 0)

                cac = (
                    (spend / Decimal(customers)).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP,
                    )
                    if customers > 0
                    else Decimal(0)
                )

                results.append(
                    CACBySourceResponse(
                        source=source,
                        total_spend=spend,
                        customers_acquired=customers,
                        cac=cac,
                    ),
                )

            self.log_completed(
                "get_cac",
                sources_count=len(results),
            )
        except Exception as e:
            self.log_failed("get_cac", error=e)
            raise
        else:
            return results

    async def _get_spend_by_source(
        self,
        db: AsyncSession,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Decimal]:
        """Query marketing spend grouped by lead source."""
        stmt = (
            select(
                Expense.lead_source,
                func.sum(Expense.amount).label("total_spend"),
            )
            .where(
                Expense.category == ExpenseCategory.MARKETING.value,
                Expense.lead_source.isnot(None),
            )
            .group_by(Expense.lead_source)
        )

        if date_from is not None:
            stmt = stmt.where(Expense.expense_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Expense.expense_date <= date_to)

        result = await db.execute(stmt)
        return {str(row[0]): Decimal(str(row[1])) for row in result.all()}

    async def _get_conversions_by_source(
        self,
        db: AsyncSession,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, int]:
        """Query converted lead counts grouped by source."""
        conditions = [
            Lead.status == "converted",
            Lead.converted_at.isnot(None),
        ]
        if date_from is not None:
            conditions.append(Lead.converted_at >= date_from)
        if date_to is not None:
            conditions.append(Lead.converted_at <= date_to)

        stmt = (
            select(
                Lead.lead_source,
                func.count(Lead.id).label("converted_count"),
            )
            .where(*conditions)
            .group_by(Lead.lead_source)
        )

        result = await db.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}

    # ------------------------------------------------------------------ #
    # generate_qr_code -- Req 65.1, 65.3
    # ------------------------------------------------------------------ #

    def generate_qr_code(self, request: QRCodeRequest) -> bytes:
        """Generate a QR code PNG with UTM tracking parameters.

        Appends utm_source=qr_code, utm_campaign={campaign_name},
        and utm_medium=print to the target URL.

        Args:
            request: QRCodeRequest with target_url and campaign_name.

        Returns:
            PNG image bytes of the generated QR code.

        Raises:
            QRCodeGenerationError: If generation fails.

        Validates: Req 65.1, 65.3
        """
        self.log_started(
            "generate_qr_code",
            campaign_name=request.campaign_name,
        )

        try:
            final_url = self._build_utm_url(
                request.target_url,
                request.campaign_name,
            )

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(final_url)
            qr.make(fit=True)

            img = qr.make_image(
                fill_color="black",
                back_color="white",
            )

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            png_bytes = buffer.getvalue()

            self.log_completed(
                "generate_qr_code",
                campaign_name=request.campaign_name,
                url=final_url,
                size_bytes=len(png_bytes),
            )
        except Exception as e:
            self.log_failed(
                "generate_qr_code",
                error=e,
                campaign_name=request.campaign_name,
            )
            msg = f"Failed to generate QR code: {e}"
            raise QRCodeGenerationError(msg) from e
        else:
            return png_bytes

    @staticmethod
    def _build_utm_url(
        target_url: str,
        campaign_name: str,
    ) -> str:
        """Append UTM parameters to a URL."""
        utm_params = {
            "utm_source": "qr_code",
            "utm_campaign": campaign_name,
            "utm_medium": "print",
        }

        parsed = urlparse(target_url)
        existing_query = parsed.query
        utm_query = urlencode(utm_params)
        combined = f"{existing_query}&{utm_query}" if existing_query else utm_query
        return urlunparse(parsed._replace(query=combined))
