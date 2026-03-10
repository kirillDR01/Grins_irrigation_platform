"""Unit tests for AgreementService.

Tests all status transitions, agreement number generation, price locking,
renewal approval/rejection, cancellation with prorated refunds, and
mid-season tier change enforcement.

Validates: Requirements 2.3, 2.4, 5.1, 5.2, 5.3, 14.2, 14.3, 14.4,
17.2, 17.3, 18.1, 40.1
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    AgreementNotFoundError,
    InvalidAgreementStatusTransitionError,
    MidSeasonTierChangeError,
)
from grins_platform.models.enums import (
    AgreementStatus,
    JobStatus,
)
from grins_platform.services.agreement_service import AgreementService

# =============================================================================
# Helpers
# =============================================================================


def _make_tier(
    *,
    tier_id=None,
    annual_price=Decimal("499.00"),
    name="Essential",
    slug="essential-residential",
) -> MagicMock:
    tier = MagicMock()
    tier.id = tier_id or uuid4()
    tier.annual_price = annual_price
    tier.name = name
    tier.slug = slug
    tier.is_active = True
    tier.stripe_price_id = "price_test"
    return tier


def _make_agreement(
    *,
    agreement_id=None,
    status=AgreementStatus.ACTIVE.value,
    annual_price=Decimal("499.00"),
    tier_id=None,
    stripe_subscription_id=None,
    jobs=None,
) -> MagicMock:
    agr = MagicMock()
    agr.id = agreement_id or uuid4()
    agr.agreement_number = "AGR-2026-001"
    agr.customer_id = uuid4()
    agr.tier_id = tier_id or uuid4()
    agr.status = status
    agr.annual_price = annual_price
    agr.stripe_subscription_id = stripe_subscription_id
    agr.jobs = jobs or []
    agr.created_at = datetime.now(tz=timezone.utc)
    agr.updated_at = datetime.now(tz=timezone.utc)
    return agr


def _make_job(*, status=JobStatus.APPROVED.value) -> MagicMock:
    job = MagicMock()
    job.id = uuid4()
    job.status = status
    job.closed_at = None
    return job


def _make_service(
    agreement_repo=None,
    tier_repo=None,
) -> AgreementService:
    return AgreementService(
        agreement_repo=agreement_repo or AsyncMock(),
        tier_repo=tier_repo or AsyncMock(),
        stripe_settings=MagicMock(is_configured=False),
    )


# =============================================================================
# Agreement Number Generation
# =============================================================================


@pytest.mark.unit
class TestGenerateAgreementNumber:
    """Tests for agreement number format AGR-YYYY-NNN."""

    @pytest.mark.asyncio
    async def test_format_matches_pattern(self) -> None:
        repo = AsyncMock()
        repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
        svc = _make_service(agreement_repo=repo)

        result = await svc.generate_agreement_number()

        year = datetime.now(tz=timezone.utc).year
        assert result == f"AGR-{year}-001"

    @pytest.mark.asyncio
    async def test_sequential_numbers(self) -> None:
        repo = AsyncMock()
        repo.get_next_agreement_number_seq = AsyncMock(side_effect=[1, 2, 3])
        svc = _make_service(agreement_repo=repo)

        r1 = await svc.generate_agreement_number()
        r2 = await svc.generate_agreement_number()
        r3 = await svc.generate_agreement_number()

        year = datetime.now(tz=timezone.utc).year
        assert r1 == f"AGR-{year}-001"
        assert r2 == f"AGR-{year}-002"
        assert r3 == f"AGR-{year}-003"

    @pytest.mark.asyncio
    async def test_three_digit_padding(self) -> None:
        repo = AsyncMock()
        repo.get_next_agreement_number_seq = AsyncMock(return_value=42)
        svc = _make_service(agreement_repo=repo)

        result = await svc.generate_agreement_number()

        year = datetime.now(tz=timezone.utc).year
        assert result == f"AGR-{year}-042"


# =============================================================================
# Create Agreement
# =============================================================================


@pytest.mark.unit
class TestCreateAgreement:
    """Tests for agreement creation with price locking."""

    @pytest.mark.asyncio
    async def test_locks_annual_price_from_tier(self) -> None:
        tier = _make_tier(annual_price=Decimal("799.00"))
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)

        agr_repo = AsyncMock()
        agr_repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
        created = _make_agreement(annual_price=Decimal("799.00"))
        agr_repo.create = AsyncMock(return_value=created)

        svc = _make_service(agreement_repo=agr_repo, tier_repo=tier_repo)
        await svc.create_agreement(uuid4(), tier.id)

        call_kwargs = agr_repo.create.call_args.kwargs
        assert call_kwargs["annual_price"] == Decimal("799.00")
        assert call_kwargs["status"] == AgreementStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_creates_status_log(self) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)

        agr_repo = AsyncMock()
        agr_repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
        agr_repo.create = AsyncMock(return_value=_make_agreement())

        svc = _make_service(agreement_repo=agr_repo, tier_repo=tier_repo)
        await svc.create_agreement(uuid4(), tier.id)

        agr_repo.add_status_log.assert_called_once()
        log_kwargs = agr_repo.add_status_log.call_args.kwargs
        assert log_kwargs["old_status"] is None
        assert log_kwargs["new_status"] == AgreementStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_tier_not_found_raises(self) -> None:
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(tier_repo=tier_repo)

        with pytest.raises(ValueError, match="Tier not found"):
            await svc.create_agreement(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_stripe_data_passed_through(self) -> None:
        tier = _make_tier()
        tier_repo = AsyncMock()
        tier_repo.get_by_id = AsyncMock(return_value=tier)

        agr_repo = AsyncMock()
        agr_repo.get_next_agreement_number_seq = AsyncMock(return_value=1)
        agr_repo.create = AsyncMock(return_value=_make_agreement())

        svc = _make_service(agreement_repo=agr_repo, tier_repo=tier_repo)
        stripe_data = {
            "stripe_subscription_id": "sub_123",
            "stripe_customer_id": "cus_456",
        }
        await svc.create_agreement(uuid4(), tier.id, stripe_data=stripe_data)

        call_kwargs = agr_repo.create.call_args.kwargs
        assert call_kwargs["stripe_subscription_id"] == "sub_123"
        assert call_kwargs["stripe_customer_id"] == "cus_456"


# =============================================================================
# Status Transitions
# =============================================================================


@pytest.mark.unit
class TestTransitionStatus:
    """Tests for valid and invalid status transitions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (AgreementStatus.PENDING, AgreementStatus.ACTIVE),
            (AgreementStatus.PENDING, AgreementStatus.CANCELLED),
            (AgreementStatus.ACTIVE, AgreementStatus.PAST_DUE),
            (AgreementStatus.ACTIVE, AgreementStatus.PENDING_RENEWAL),
            (AgreementStatus.ACTIVE, AgreementStatus.CANCELLED),
            (AgreementStatus.ACTIVE, AgreementStatus.EXPIRED),
            (AgreementStatus.ACTIVE, AgreementStatus.PAUSED),
            (AgreementStatus.PAST_DUE, AgreementStatus.ACTIVE),
            (AgreementStatus.PAST_DUE, AgreementStatus.PAUSED),
            (AgreementStatus.PAST_DUE, AgreementStatus.CANCELLED),
            (AgreementStatus.PAUSED, AgreementStatus.ACTIVE),
            (AgreementStatus.PAUSED, AgreementStatus.CANCELLED),
            (AgreementStatus.PENDING_RENEWAL, AgreementStatus.ACTIVE),
            (AgreementStatus.PENDING_RENEWAL, AgreementStatus.EXPIRED),
            (AgreementStatus.PENDING_RENEWAL, AgreementStatus.CANCELLED),
            (AgreementStatus.EXPIRED, AgreementStatus.ACTIVE),
        ],
    )
    async def test_valid_transitions_succeed(
        self,
        current: AgreementStatus,
        target: AgreementStatus,
    ) -> None:
        agr = _make_agreement(status=current.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.transition_status(agr.id, target)

        agr_repo.add_status_log.assert_called_once()
        log_kwargs = agr_repo.add_status_log.call_args.kwargs
        assert log_kwargs["old_status"] == current.value
        assert log_kwargs["new_status"] == target.value

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (AgreementStatus.CANCELLED, AgreementStatus.ACTIVE),
            (AgreementStatus.CANCELLED, AgreementStatus.PENDING),
            (AgreementStatus.PENDING, AgreementStatus.PAST_DUE),
            (AgreementStatus.PENDING, AgreementStatus.PAUSED),
            (AgreementStatus.PAUSED, AgreementStatus.PENDING_RENEWAL),
            (AgreementStatus.EXPIRED, AgreementStatus.CANCELLED),
        ],
    )
    async def test_invalid_transitions_rejected(
        self,
        current: AgreementStatus,
        target: AgreementStatus,
    ) -> None:
        agr = _make_agreement(status=current.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(InvalidAgreementStatusTransitionError):
            await svc.transition_status(agr.id, target)

    @pytest.mark.asyncio
    async def test_agreement_not_found(self) -> None:
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(AgreementNotFoundError):
            await svc.transition_status(uuid4(), AgreementStatus.ACTIVE)

    @pytest.mark.asyncio
    async def test_cancelled_sets_cancelled_at(self) -> None:
        agr = _make_agreement(status=AgreementStatus.ACTIVE.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.transition_status(agr.id, AgreementStatus.CANCELLED)

        update_data = agr_repo.update.call_args.args[1]
        assert "cancelled_at" in update_data
        assert update_data["status"] == AgreementStatus.CANCELLED.value


# =============================================================================
# Renewal Approval / Rejection
# =============================================================================


@pytest.mark.unit
class TestApproveRenewal:
    """Tests for renewal approval."""

    @pytest.mark.asyncio
    async def test_records_approval_fields(self) -> None:
        agr = _make_agreement(status=AgreementStatus.PENDING_RENEWAL.value)
        staff_id = uuid4()
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.approve_renewal(agr.id, staff_id)

        update_data = agr_repo.update.call_args.args[1]
        assert update_data["renewal_approved_by"] == staff_id
        assert "renewal_approved_at" in update_data

    @pytest.mark.asyncio
    async def test_creates_status_log(self) -> None:
        agr = _make_agreement(status=AgreementStatus.PENDING_RENEWAL.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.approve_renewal(agr.id, uuid4())

        agr_repo.add_status_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(AgreementNotFoundError):
            await svc.approve_renewal(uuid4(), uuid4())


@pytest.mark.unit
class TestRejectRenewal:
    """Tests for renewal rejection."""

    @pytest.mark.asyncio
    async def test_transitions_to_expired(self) -> None:
        agr = _make_agreement(status=AgreementStatus.PENDING_RENEWAL.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.reject_renewal(agr.id, uuid4())

        # transition_status is called which calls update
        agr_repo.update.assert_called()

    @pytest.mark.asyncio
    async def test_calls_stripe_when_configured(self) -> None:
        agr = _make_agreement(
            status=AgreementStatus.PENDING_RENEWAL.value,
            stripe_subscription_id="sub_test",
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        stripe_settings = MagicMock(
            is_configured=True,
            stripe_secret_key="sk_test",
        )
        svc = AgreementService(
            agreement_repo=agr_repo,
            tier_repo=AsyncMock(),
            stripe_settings=stripe_settings,
        )

        with patch("grins_platform.services.agreement_service.stripe") as mock_stripe:
            await svc.reject_renewal(agr.id, uuid4())
            mock_stripe.Subscription.modify.assert_called_once_with(
                "sub_test",
                cancel_at_period_end=True,
            )

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(AgreementNotFoundError):
            await svc.reject_renewal(uuid4(), uuid4())


# =============================================================================
# Cancel Agreement
# =============================================================================


@pytest.mark.unit
class TestCancelAgreement:
    """Tests for cancellation: job handling and prorated refund."""

    @pytest.mark.asyncio
    async def test_approved_jobs_cancelled(self) -> None:
        jobs = [
            _make_job(status=JobStatus.APPROVED.value),
            _make_job(status=JobStatus.APPROVED.value),
            _make_job(status=JobStatus.COMPLETED.value),
        ]
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            annual_price=Decimal("600.00"),
            jobs=jobs,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.cancel_agreement(agr.id, "Customer request")

        assert jobs[0].status == JobStatus.CANCELLED.value
        assert jobs[1].status == JobStatus.CANCELLED.value

    @pytest.mark.asyncio
    async def test_scheduled_and_in_progress_preserved(self) -> None:
        jobs = [
            _make_job(status=JobStatus.SCHEDULED.value),
            _make_job(status=JobStatus.IN_PROGRESS.value),
            _make_job(status=JobStatus.COMPLETED.value),
        ]
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            jobs=jobs,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.cancel_agreement(agr.id, "Test")

        assert jobs[0].status == JobStatus.SCHEDULED.value
        assert jobs[1].status == JobStatus.IN_PROGRESS.value
        assert jobs[2].status == JobStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_prorated_refund_calculation(self) -> None:
        # 3 total jobs: 2 APPROVED (remaining), 1 COMPLETED
        # remaining_visits = 2, total = 3
        # refund = 600 * 2/3 = 400.00
        jobs = [
            _make_job(status=JobStatus.APPROVED.value),
            _make_job(status=JobStatus.APPROVED.value),
            _make_job(status=JobStatus.COMPLETED.value),
        ]
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            annual_price=Decimal("600.00"),
            jobs=jobs,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.cancel_agreement(agr.id, "Refund test")

        # Second update call stores refund
        last_update = agr_repo.update.call_args_list[-1]
        update_data = last_update.args[1]
        assert update_data["cancellation_refund_amount"] == Decimal("400.00")
        assert update_data["cancellation_reason"] == "Refund test"

    @pytest.mark.asyncio
    async def test_zero_jobs_zero_refund(self) -> None:
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            annual_price=Decimal("500.00"),
            jobs=[],
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.cancel_agreement(agr.id, "No jobs")

        last_update = agr_repo.update.call_args_list[-1]
        update_data = last_update.args[1]
        assert update_data["cancellation_refund_amount"] == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(AgreementNotFoundError):
            await svc.cancel_agreement(uuid4(), "test")

    @pytest.mark.asyncio
    async def test_all_completed_zero_refund(self) -> None:
        jobs = [
            _make_job(status=JobStatus.COMPLETED.value),
            _make_job(status=JobStatus.COMPLETED.value),
        ]
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            annual_price=Decimal("600.00"),
            jobs=jobs,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)
        agr_repo.update = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        await svc.cancel_agreement(agr.id, "All done")

        last_update = agr_repo.update.call_args_list[-1]
        update_data = last_update.args[1]
        assert update_data["cancellation_refund_amount"] == Decimal("0.00")


# =============================================================================
# Mid-Season Tier Change Enforcement
# =============================================================================


@pytest.mark.unit
class TestEnforceNoMidSeasonTierChange:
    """Tests for mid-season tier change rejection."""

    @pytest.mark.asyncio
    async def test_rejects_tier_change_when_active(self) -> None:
        tier_id = uuid4()
        new_tier_id = uuid4()
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            tier_id=tier_id,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(MidSeasonTierChangeError):
            await svc.enforce_no_mid_season_tier_change(agr.id, new_tier_id)

    @pytest.mark.asyncio
    async def test_allows_same_tier(self) -> None:
        tier_id = uuid4()
        agr = _make_agreement(
            status=AgreementStatus.ACTIVE.value,
            tier_id=tier_id,
        )
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        # Should not raise
        await svc.enforce_no_mid_season_tier_change(agr.id, tier_id)

    @pytest.mark.asyncio
    async def test_allows_tier_change_when_not_active(self) -> None:
        agr = _make_agreement(status=AgreementStatus.PENDING.value)
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=agr)

        svc = _make_service(agreement_repo=agr_repo)
        # Should not raise for non-ACTIVE
        await svc.enforce_no_mid_season_tier_change(agr.id, uuid4())

    @pytest.mark.asyncio
    async def test_not_found_raises(self) -> None:
        agr_repo = AsyncMock()
        agr_repo.get_by_id = AsyncMock(return_value=None)
        svc = _make_service(agreement_repo=agr_repo)

        with pytest.raises(AgreementNotFoundError):
            await svc.enforce_no_mid_season_tier_change(uuid4(), uuid4())
