"""Repository for ServiceAgreement database operations.

Validates: Requirements 19.1, 19.2, 20.2, 20.3, 37.1
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import extract, func, select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.agreement_status_log import AgreementStatusLog
from grins_platform.models.enums import AgreementPaymentStatus, AgreementStatus
from grins_platform.models.service_agreement import ServiceAgreement

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class AgreementRepository(LoggerMixin):
    """Repository for ServiceAgreement database operations.

    Validates: Requirements 19.1, 19.2, 20.2, 20.3, 37.1
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def create(self, **kwargs: Any) -> ServiceAgreement:
        """Create a new ServiceAgreement record.

        Returns:
            Created ServiceAgreement instance.
        """
        self.log_started("create", agreement_number=kwargs.get("agreement_number"))
        agreement = ServiceAgreement(**kwargs)
        self.session.add(agreement)
        await self.session.flush()
        await self.session.refresh(agreement)
        self.log_completed("create", agreement_id=str(agreement.id))
        return agreement

    async def get_by_stripe_subscription_id(
        self,
        subscription_id: str,
    ) -> ServiceAgreement | None:
        """Get a ServiceAgreement by Stripe subscription ID with eager loads."""
        self.log_started(
            "get_by_stripe_subscription_id",
            subscription_id=subscription_id,
        )
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
                selectinload(ServiceAgreement.jobs),
                selectinload(ServiceAgreement.status_logs),
                selectinload(ServiceAgreement.property),
            )
            .where(ServiceAgreement.stripe_subscription_id == subscription_id)
        )
        result = await self.session.execute(stmt)
        agreement: ServiceAgreement | None = result.scalar_one_or_none()
        self.log_completed(
            "get_by_stripe_subscription_id",
            found=agreement is not None,
        )
        return agreement

    async def get_by_stripe_customer_id(
        self,
        stripe_customer_id: str,
    ) -> ServiceAgreement | None:
        """Get a ServiceAgreement by Stripe customer ID with eager loads.

        Fallback lookup when subscription_id is unavailable (newer Stripe API).
        Returns the most recently created agreement for the customer.
        """
        self.log_started(
            "get_by_stripe_customer_id",
            stripe_customer_id=stripe_customer_id,
        )
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
                selectinload(ServiceAgreement.jobs),
                selectinload(ServiceAgreement.status_logs),
                selectinload(ServiceAgreement.property),
            )
            .where(ServiceAgreement.stripe_customer_id == stripe_customer_id)
            .order_by(ServiceAgreement.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        agreement: ServiceAgreement | None = result.scalar_one_or_none()
        self.log_completed(
            "get_by_stripe_customer_id",
            found=agreement is not None,
        )
        return agreement

    async def get_by_id(self, agreement_id: UUID) -> ServiceAgreement | None:
        """Get a ServiceAgreement by ID with joins to customer, tier, jobs, status logs.

        Validates: Requirement 19.2
        """
        self.log_started("get_by_id", agreement_id=str(agreement_id))
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
                selectinload(ServiceAgreement.jobs),
                selectinload(ServiceAgreement.status_logs).selectinload(
                    AgreementStatusLog.changed_by_staff,
                ),
                selectinload(ServiceAgreement.property),
            )
            .where(ServiceAgreement.id == agreement_id)
        )
        result = await self.session.execute(stmt)
        agreement: ServiceAgreement | None = result.scalar_one_or_none()
        self.log_completed("get_by_id", found=agreement is not None)
        return agreement

    async def list_with_filters(
        self,
        *,
        status: str | None = None,
        tier_id: UUID | None = None,
        customer_id: UUID | None = None,
        payment_status: str | None = None,
        expiring_soon: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ServiceAgreement], int]:
        """List agreements with filters and pagination.

        Validates: Requirement 19.1
        """
        self.log_started("list_with_filters", page=page, page_size=page_size)

        base = select(ServiceAgreement)

        if status:
            base = base.where(ServiceAgreement.status == status)
        if tier_id:
            base = base.where(ServiceAgreement.tier_id == tier_id)
        if customer_id:
            base = base.where(ServiceAgreement.customer_id == customer_id)
        if payment_status:
            base = base.where(ServiceAgreement.payment_status == payment_status)
        if expiring_soon:
            threshold = date.today() + timedelta(days=30)
            base = base.where(
                ServiceAgreement.renewal_date <= threshold,
                ServiceAgreement.renewal_date >= date.today(),
                ServiceAgreement.status != AgreementStatus.PENDING_RENEWAL.value,
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        paginated = (
            base.options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
            )
            .order_by(ServiceAgreement.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(paginated)
        agreements = list(result.scalars().all())

        self.log_completed("list_with_filters", count=len(agreements), total=total)
        return agreements, total

    async def get_renewal_pipeline(self) -> list[ServiceAgreement]:
        """Get agreements in PENDING_RENEWAL status sorted by renewal_date ASC.

        Validates: Requirement 20.2
        """
        self.log_started("get_renewal_pipeline")
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
            )
            .where(ServiceAgreement.status == AgreementStatus.PENDING_RENEWAL.value)
            .order_by(ServiceAgreement.renewal_date.asc())
        )
        result = await self.session.execute(stmt)
        agreements = list(result.scalars().all())
        self.log_completed("get_renewal_pipeline", count=len(agreements))
        return agreements

    async def get_failed_payments(self) -> list[ServiceAgreement]:
        """Get agreements with PAST_DUE or FAILED payment_status.

        Validates: Requirement 20.3
        """
        self.log_started("get_failed_payments")
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
            )
            .where(
                ServiceAgreement.payment_status.in_(
                    [
                        AgreementPaymentStatus.PAST_DUE.value,
                        AgreementPaymentStatus.FAILED.value,
                    ],
                ),
            )
            .order_by(ServiceAgreement.last_payment_date.asc())
        )
        result = await self.session.execute(stmt)
        agreements = list(result.scalars().all())
        self.log_completed("get_failed_payments", count=len(agreements))
        return agreements

    async def get_annual_notice_due(self) -> list[ServiceAgreement]:
        """Get ACTIVE agreements needing annual notice.

        Returns agreements where last_annual_notice_sent is NULL
        or the year of last_annual_notice_sent < current year.

        Validates: Requirement 37.1
        """
        self.log_started("get_annual_notice_due")
        current_year = date.today().year
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.tier),
            )
            .where(
                ServiceAgreement.status == AgreementStatus.ACTIVE.value,
                (
                    ServiceAgreement.last_annual_notice_sent.is_(None)
                    | (
                        extract("year", ServiceAgreement.last_annual_notice_sent)
                        < current_year
                    )
                ),
            )
            .order_by(ServiceAgreement.created_at.asc())
        )
        result = await self.session.execute(stmt)
        agreements = list(result.scalars().all())
        self.log_completed("get_annual_notice_due", count=len(agreements))
        return agreements

    async def update(
        self,
        agreement: ServiceAgreement,
        data: dict[str, Any],
    ) -> ServiceAgreement:
        """Update a ServiceAgreement with the given data dict."""
        self.log_started("update", agreement_id=str(agreement.id))
        for key, value in data.items():
            setattr(agreement, key, value)
        agreement.updated_at = datetime.now()  # type: ignore[assignment]
        await self.session.flush()
        await self.session.refresh(agreement)
        self.log_completed("update", agreement_id=str(agreement.id))
        return agreement

    async def get_next_agreement_number_seq(self, year: int) -> int:
        """Get the next sequential number for agreement_number within a year."""
        self.log_started("get_next_agreement_number_seq", year=year)
        prefix = f"AGR-{year}-"
        stmt = (
            select(func.count())
            .select_from(ServiceAgreement)
            .where(ServiceAgreement.agreement_number.like(f"{prefix}%"))
        )
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        next_seq = count + 1
        self.log_completed("get_next_agreement_number_seq", next_seq=next_seq)
        return next_seq

    async def add_status_log(
        self,
        *,
        agreement_id: UUID,
        old_status: str | None,
        new_status: str,
        changed_by: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgreementStatusLog:
        """Create an AgreementStatusLog entry."""
        self.log_started("add_status_log", agreement_id=str(agreement_id))
        log = AgreementStatusLog(
            agreement_id=agreement_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason,
            metadata_=metadata,
        )
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        self.log_completed("add_status_log", log_id=str(log.id))
        return log
