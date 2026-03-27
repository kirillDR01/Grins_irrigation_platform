"""Service for managing ServiceAgreement lifecycle.

Handles creation, status transitions, renewal approval/rejection,
cancellation with prorated refunds, and mid-season tier change enforcement.

Validates: Requirements 2.3, 2.4, 5.1, 5.2, 5.3, 8.4, 8.6, 14.1, 14.2,
14.3, 14.4, 17.2, 17.3, 18.1
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import stripe

from grins_platform.exceptions import (
    AgreementNotFoundError,
    InactiveTierError,
    InvalidAgreementStatusTransitionError,
    MidSeasonTierChangeError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    VALID_AGREEMENT_STATUS_TRANSITIONS,
    AgreementStatus,
    JobStatus,
)
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.service_agreement import ServiceAgreement
    from grins_platform.repositories.agreement_repository import AgreementRepository
    from grins_platform.repositories.agreement_tier_repository import (
        AgreementTierRepository,
    )


class AgreementService(LoggerMixin):
    """Service for ServiceAgreement lifecycle management.

    Validates: Requirements 2.3, 2.4, 5.1, 5.2, 5.3, 8.4, 8.6,
    14.1, 14.2, 14.3, 14.4, 17.2, 17.3, 18.1
    """

    DOMAIN = "agreements"

    def __init__(
        self,
        agreement_repo: AgreementRepository,
        tier_repo: AgreementTierRepository,
        stripe_settings: StripeSettings | None = None,
    ) -> None:
        """Initialize with repositories and optional Stripe settings."""
        super().__init__()
        self.agreement_repo = agreement_repo
        self.tier_repo = tier_repo
        self.stripe_settings = stripe_settings or StripeSettings()

    async def generate_agreement_number(self) -> str:
        """Generate agreement number in format AGR-YYYY-NNN.

        Validates: Requirement 2.3
        """
        year = datetime.now(timezone.utc).year
        seq = await self.agreement_repo.get_next_agreement_number_seq(year)
        return f"AGR-{year}-{seq:03d}"

    async def create_agreement(
        self,
        customer_id: UUID,
        tier_id: UUID,
        stripe_data: dict[str, Any] | None = None,
    ) -> ServiceAgreement:
        """Create a new agreement with PENDING status, locking price from tier.

        Validates: Requirements 2.4, 8.4, 8.6
        """
        self.log_started(
            "create_agreement",
            customer_id=str(customer_id),
            tier_id=str(tier_id),
        )

        tier = await self.tier_repo.get_by_id(tier_id)
        if not tier:
            self.log_failed(
                "create_agreement",
                error=ValueError(f"Tier not found: {tier_id}"),
            )
            msg = f"Tier not found: {tier_id}"
            raise ValueError(msg)

        if not tier.is_active:
            self.log_rejected(
                "create_agreement",
                reason="inactive_tier",
                tier_id=str(tier_id),
            )
            raise InactiveTierError(tier_id)

        agreement_number = await self.generate_agreement_number()

        create_kwargs: dict[str, Any] = {
            "agreement_number": agreement_number,
            "customer_id": customer_id,
            "tier_id": tier_id,
            "status": AgreementStatus.PENDING.value,
            "annual_price": tier.annual_price,
            "payment_status": "current",
        }

        if stripe_data:
            for key in (
                "stripe_subscription_id",
                "stripe_customer_id",
                "property_id",
                "start_date",
                "end_date",
                "renewal_date",
                "consent_recorded_at",
                "consent_method",
                "disclosure_version",
            ):
                if key in stripe_data:
                    create_kwargs[key] = stripe_data[key]

        agreement = await self.agreement_repo.create(**create_kwargs)

        await self.agreement_repo.add_status_log(
            agreement_id=agreement.id,
            old_status=None,
            new_status=AgreementStatus.PENDING.value,
            reason="Agreement created",
        )

        self.log_completed(
            "create_agreement",
            agreement_id=str(agreement.id),
            agreement_number=agreement_number,
        )
        return agreement

    async def transition_status(
        self,
        agreement_id: UUID,
        new_status: AgreementStatus,
        actor: UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceAgreement:
        """Transition agreement status with validation.

        Validates: Requirements 5.1, 5.2, 5.3
        """
        self.log_started(
            "transition_status",
            agreement_id=str(agreement_id),
            new_status=new_status.value,
        )

        agreement = await self.agreement_repo.get_by_id(agreement_id)
        if not agreement:
            raise AgreementNotFoundError(agreement_id)

        current = AgreementStatus(agreement.status)
        valid = VALID_AGREEMENT_STATUS_TRANSITIONS.get(current, set())

        if new_status not in valid:
            self.log_rejected(
                "transition_status",
                reason="invalid_transition",
                current=current.value,
                requested=new_status.value,
            )
            raise InvalidAgreementStatusTransitionError(
                current.value,
                new_status.value,
            )

        old_status = agreement.status
        update_data: dict[str, Any] = {"status": new_status.value}

        if new_status == AgreementStatus.CANCELLED:
            update_data["cancelled_at"] = datetime.now(timezone.utc)

        agreement = await self.agreement_repo.update(agreement, update_data)

        await self.agreement_repo.add_status_log(
            agreement_id=agreement_id,
            old_status=old_status,
            new_status=new_status.value,
            changed_by=actor,
            reason=reason,
            metadata=metadata,
        )

        self.log_completed(
            "transition_status",
            agreement_id=str(agreement_id),
            old_status=old_status,
            new_status=new_status.value,
        )
        return agreement

    async def approve_renewal(
        self,
        agreement_id: UUID,
        staff_id: UUID,
    ) -> ServiceAgreement:
        """Record renewal approval.

        Validates: Requirement 17.2
        """
        self.log_started(
            "approve_renewal",
            agreement_id=str(agreement_id),
            staff_id=str(staff_id),
        )

        agreement = await self.agreement_repo.get_by_id(agreement_id)
        if not agreement:
            raise AgreementNotFoundError(agreement_id)

        now = datetime.now(timezone.utc)
        agreement = await self.agreement_repo.update(
            agreement,
            {
                "renewal_approved_by": staff_id,
                "renewal_approved_at": now,
            },
        )

        await self.agreement_repo.add_status_log(
            agreement_id=agreement_id,
            old_status=agreement.status,
            new_status=agreement.status,
            changed_by=staff_id,
            reason="Renewal approved by admin",
        )

        self.log_completed(
            "approve_renewal",
            agreement_id=str(agreement_id),
        )
        return agreement

    async def reject_renewal(
        self,
        agreement_id: UUID,
        staff_id: UUID,
    ) -> ServiceAgreement:
        """Reject renewal: set cancel_at_period_end in Stripe, transition to EXPIRED.

        Validates: Requirement 17.3
        """
        self.log_started(
            "reject_renewal",
            agreement_id=str(agreement_id),
            staff_id=str(staff_id),
        )

        agreement = await self.agreement_repo.get_by_id(agreement_id)
        if not agreement:
            raise AgreementNotFoundError(agreement_id)

        if agreement.stripe_subscription_id and self.stripe_settings.is_configured:
            stripe.api_key = self.stripe_settings.stripe_secret_key
            stripe.Subscription.modify(
                agreement.stripe_subscription_id,
                cancel_at_period_end=True,
            )

        agreement = await self.transition_status(
            agreement_id,
            AgreementStatus.EXPIRED,
            actor=staff_id,
            reason="Renewal rejected by admin",
        )

        self.log_completed(
            "reject_renewal",
            agreement_id=str(agreement_id),
        )
        return agreement

    async def cancel_agreement(
        self,
        agreement_id: UUID,
        reason: str,
        actor: UUID | None = None,
    ) -> ServiceAgreement:
        """Cancel agreement: cancel APPROVED jobs, compute prorated refund.

        Preserves SCHEDULED/IN_PROGRESS/COMPLETED jobs.

        Validates: Requirements 14.1, 14.2, 14.3, 14.4
        """
        self.log_started(
            "cancel_agreement",
            agreement_id=str(agreement_id),
            reason=reason,
        )

        agreement = await self.agreement_repo.get_by_id(agreement_id)
        if not agreement:
            raise AgreementNotFoundError(agreement_id)

        # Cancel TO_BE_SCHEDULED jobs, preserve others
        total_visits = len(agreement.jobs)
        remaining_visits = 0
        for job in agreement.jobs:
            if job.status == JobStatus.TO_BE_SCHEDULED.value:
                job.status = JobStatus.CANCELLED.value
                remaining_visits += 1
            elif job.status not in (
                JobStatus.COMPLETED.value,
                JobStatus.CANCELLED.value,
            ):
                # IN_PROGRESS — not completed, count as remaining
                remaining_visits += 1

        # Compute prorated refund
        refund_amount = Decimal("0.00")
        if total_visits > 0:
            refund_amount = (
                agreement.annual_price
                * Decimal(str(remaining_visits))
                / Decimal(str(total_visits))
            ).quantize(Decimal("0.01"))

        # Transition status
        agreement = await self.transition_status(
            agreement_id,
            AgreementStatus.CANCELLED,
            actor=actor,
            reason=reason,
        )

        # Store refund amount
        agreement = await self.agreement_repo.update(
            agreement,
            {
                "cancellation_reason": reason,
                "cancellation_refund_amount": refund_amount,
            },
        )

        self.log_completed(
            "cancel_agreement",
            agreement_id=str(agreement_id),
            refund_amount=str(refund_amount),
            remaining_visits=remaining_visits,
            total_visits=total_visits,
        )
        return agreement

    async def enforce_no_mid_season_tier_change(
        self,
        agreement_id: UUID,
        new_tier_id: UUID,
    ) -> None:
        """Reject tier changes while agreement is ACTIVE.

        Validates: Requirement 18.1
        """
        agreement = await self.agreement_repo.get_by_id(agreement_id)
        if not agreement:
            raise AgreementNotFoundError(agreement_id)

        if (
            agreement.status == AgreementStatus.ACTIVE.value
            and agreement.tier_id != new_tier_id
        ):
            self.log_rejected(
                "tier_change",
                reason="mid_season_change",
                agreement_id=str(agreement_id),
            )
            raise MidSeasonTierChangeError(agreement_id)
