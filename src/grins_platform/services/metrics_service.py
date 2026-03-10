"""Service for computing agreement business metrics.

Computes active agreement count, MRR, ARPA, renewal rate,
churn rate, past-due amount, MRR history, and tier distribution.

Validates: Requirement 20.1, 22.3, 22.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.agreement_status_log import AgreementStatusLog
from grins_platform.models.enums import (
    AgreementPaymentStatus,
    AgreementStatus,
)
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.service_agreement_tier import ServiceAgreementTier

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AgreementMetrics:
    """Computed agreement business metrics."""

    active_count: int
    mrr: Decimal
    arpa: Decimal
    renewal_rate: Decimal
    churn_rate: Decimal
    past_due_amount: Decimal


@dataclass
class MrrDataPoint:
    """Single month MRR data point."""

    month: str  # YYYY-MM
    mrr: Decimal


@dataclass
class TierDistributionItem:
    """Active agreement count for a single tier."""

    tier_id: str
    tier_name: str
    package_type: str
    active_count: int


@dataclass
class MrrHistory:
    """MRR over trailing 12 months."""

    data_points: list[MrrDataPoint] = field(default_factory=list)


@dataclass
class TierDistribution:
    """Active agreement counts grouped by tier."""

    items: list[TierDistributionItem] = field(default_factory=list)


class MetricsService(LoggerMixin):
    """Service for computing agreement business KPIs.

    Validates: Requirement 20.1
    """

    DOMAIN = "agreements"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def compute_metrics(self) -> AgreementMetrics:
        """Compute all agreement business metrics.

        Returns:
            AgreementMetrics with active_count, MRR, ARPA,
            renewal_rate, churn_rate, past_due_amount.
        """
        self.log_started("compute_metrics")

        active_count, mrr = await self._get_active_metrics()
        arpa = (mrr / active_count) if active_count > 0 else Decimal("0.00")
        renewal_rate = await self._get_renewal_rate()
        churn_rate = await self._get_churn_rate()
        past_due_amount = await self._get_past_due_amount()

        metrics = AgreementMetrics(
            active_count=active_count,
            mrr=mrr.quantize(Decimal("0.01")),
            arpa=arpa.quantize(Decimal("0.01")),
            renewal_rate=renewal_rate.quantize(Decimal("0.01")),
            churn_rate=churn_rate.quantize(Decimal("0.01")),
            past_due_amount=past_due_amount.quantize(Decimal("0.01")),
        )

        self.log_completed(
            "compute_metrics",
            active_count=active_count,
            mrr=str(metrics.mrr),
        )
        return metrics

    async def _get_active_metrics(self) -> tuple[int, Decimal]:
        """Get active agreement count and MRR."""
        stmt = select(
            func.count(),
            func.coalesce(func.sum(ServiceAgreement.annual_price / 12), 0),
        ).where(ServiceAgreement.status == AgreementStatus.ACTIVE.value)

        result = await self.session.execute(stmt)
        row = result.one()
        return int(row[0]), Decimal(str(row[1]))

    async def _get_renewal_rate(self, days: int = 90) -> Decimal:
        """Compute renewal rate over trailing period.

        Renewal rate = renewed / (renewed + expired) in the period.
        Renewed = PENDING_RENEWAL -> ACTIVE transitions.
        Expired = PENDING_RENEWAL -> EXPIRED/CANCELLED transitions.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        renewed_stmt = select(func.count()).where(
            and_(
                AgreementStatusLog.old_status == AgreementStatus.PENDING_RENEWAL.value,
                AgreementStatusLog.new_status == AgreementStatus.ACTIVE.value,
                AgreementStatusLog.created_at >= cutoff,
            ),
        )
        renewed_result = await self.session.execute(renewed_stmt)
        renewed = renewed_result.scalar() or 0

        not_renewed_stmt = select(func.count()).where(
            and_(
                AgreementStatusLog.old_status == AgreementStatus.PENDING_RENEWAL.value,
                AgreementStatusLog.new_status.in_(
                    [
                        AgreementStatus.EXPIRED.value,
                        AgreementStatus.CANCELLED.value,
                    ],
                ),
                AgreementStatusLog.created_at >= cutoff,
            ),
        )
        not_renewed_result = await self.session.execute(not_renewed_stmt)
        not_renewed = not_renewed_result.scalar() or 0

        total = renewed + not_renewed
        if total == 0:
            return Decimal("0.00")
        return Decimal(str(renewed)) / Decimal(str(total)) * Decimal(100)

    async def _get_churn_rate(self, days: int = 90) -> Decimal:
        """Compute churn rate over trailing period.

        Churn rate = cancelled / (active + cancelled) in the period.
        Cancelled = transitions to CANCELLED in the period.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        cancelled_stmt = select(func.count()).where(
            and_(
                AgreementStatusLog.new_status == AgreementStatus.CANCELLED.value,
                AgreementStatusLog.created_at >= cutoff,
            ),
        )
        cancelled_result = await self.session.execute(cancelled_stmt)
        cancelled = cancelled_result.scalar() or 0

        # Current active count
        active_stmt = select(func.count()).where(
            ServiceAgreement.status == AgreementStatus.ACTIVE.value,
        )
        active_result = await self.session.execute(active_stmt)
        active = active_result.scalar() or 0

        total = active + cancelled
        if total == 0:
            return Decimal("0.00")
        return Decimal(str(cancelled)) / Decimal(str(total)) * Decimal(100)

    async def _get_past_due_amount(self) -> Decimal:
        """Get total annual_price for agreements with past-due payment status."""
        stmt = select(
            func.coalesce(func.sum(ServiceAgreement.annual_price), 0),
        ).where(
            ServiceAgreement.payment_status.in_(
                [
                    AgreementPaymentStatus.PAST_DUE.value,
                    AgreementPaymentStatus.FAILED.value,
                ],
            ),
        )
        result = await self.session.execute(stmt)
        return Decimal(str(result.scalar() or 0))

    async def get_mrr_history(self, months: int = 12) -> MrrHistory:
        """Compute MRR for each of the trailing N months.

        For each month, MRR = sum(annual_price / 12) for agreements that
        were ACTIVE at the end of that month (created before month end,
        not cancelled/expired before month end).

        Validates: Requirement 22.3
        """
        self.log_started("get_mrr_history", months=months)
        now = datetime.now(timezone.utc)
        data_points: list[MrrDataPoint] = []

        for i in range(months - 1, -1, -1):
            # Compute the last day of the target month
            target = now - timedelta(days=i * 30)
            month_str = target.strftime("%Y-%m")

            # For current month, use current active MRR
            if i == 0:
                _, mrr = await self._get_active_metrics()
                data_points.append(
                    MrrDataPoint(month=month_str, mrr=mrr.quantize(Decimal("0.01"))),
                )
                continue

            # For past months: agreements created before month end that were
            # active (not cancelled/expired before that month end).
            # Approximation: count agreements whose start_date <= month end
            # and (status is still active OR cancelled_at > month end).
            month_end = target.replace(day=28) + timedelta(days=4)
            month_end = month_end.replace(day=1)  # first of next month

            stmt = select(
                func.coalesce(func.sum(ServiceAgreement.annual_price / 12), 0),
            ).where(
                and_(
                    ServiceAgreement.created_at < month_end,
                    ServiceAgreement.status.in_(
                        [
                            AgreementStatus.ACTIVE.value,
                            AgreementStatus.PAST_DUE.value,
                            AgreementStatus.PAUSED.value,
                            AgreementStatus.PENDING_RENEWAL.value,
                        ],
                    ),
                ),
            )
            result = await self.session.execute(stmt)
            mrr_val = Decimal(str(result.scalar() or 0))
            data_points.append(
                MrrDataPoint(month=month_str, mrr=mrr_val.quantize(Decimal("0.01"))),
            )

        self.log_completed("get_mrr_history", count=len(data_points))
        return MrrHistory(data_points=data_points)

    async def get_tier_distribution(self) -> TierDistribution:
        """Get active agreement counts grouped by tier.

        Validates: Requirement 22.4
        """
        self.log_started("get_tier_distribution")

        stmt = (
            select(
                ServiceAgreementTier.id,
                ServiceAgreementTier.name,
                ServiceAgreementTier.package_type,
                func.count(ServiceAgreement.id),
            )
            .outerjoin(
                ServiceAgreement,
                and_(
                    ServiceAgreement.tier_id == ServiceAgreementTier.id,
                    ServiceAgreement.status == AgreementStatus.ACTIVE.value,
                ),
            )
            .where(ServiceAgreementTier.is_active.is_(True))
            .group_by(
                ServiceAgreementTier.id,
                ServiceAgreementTier.name,
                ServiceAgreementTier.package_type,
            )
            .order_by(ServiceAgreementTier.display_order)
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        items = [
            TierDistributionItem(
                tier_id=str(row[0]),
                tier_name=str(row[1]),
                package_type=str(row[2]),
                active_count=int(row[3]),
            )
            for row in rows
        ]

        self.log_completed("get_tier_distribution", count=len(items))
        return TierDistribution(items=items)
