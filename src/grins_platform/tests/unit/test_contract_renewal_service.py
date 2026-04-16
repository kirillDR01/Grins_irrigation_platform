"""Unit tests for ContractRenewalReviewService.

Validates: CRM Changes Update 2 Req 31.1, 31.2, 31.3, 31.6, 31.10
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from grins_platform.models.contract_renewal import (
    ContractRenewalProposal,
    ContractRenewalProposedJob,
)
from grins_platform.models.enums import (
    JobCategory,
    JobStatus,
    ProposalStatus,
    ProposedJobStatus,
)
from grins_platform.schemas.contract_renewal import ProposedJobModification
from grins_platform.services.contract_renewal_service import (
    ContractRenewalReviewService,
    _resolve_proposed_dates,
    _roll_forward_prefs,
)

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture()
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture()
def service(mock_session: AsyncMock) -> ContractRenewalReviewService:
    return ContractRenewalReviewService(session=mock_session)


def _make_tier(name: str = "Essential", slug: str = "essential") -> Mock:
    tier = Mock()
    tier.name = name
    tier.slug = slug
    return tier


def _make_agreement(
    tier_name: str = "Essential",
    tier_slug: str = "essential",
    prefs: dict | None = None,
) -> Mock:
    agreement = Mock()
    agreement.id = uuid4()
    agreement.customer_id = uuid4()
    agreement.property_id = uuid4()
    agreement.tier = _make_tier(tier_name, tier_slug)
    agreement.service_week_preferences = prefs
    return agreement


def _make_proposed_job(
    status: str = ProposedJobStatus.PENDING.value,
    service_type: str = "spring_startup",
) -> Mock:
    pj = Mock(spec=ContractRenewalProposedJob)
    pj.id = uuid4()
    pj.proposal_id = uuid4()
    pj.service_type = service_type
    pj.status = status
    pj.target_start_date = date(2026, 4, 1)
    pj.target_end_date = date(2026, 4, 30)
    pj.proposed_job_payload = {"description": "test", "priority": 0}
    pj.admin_notes = None
    pj.created_job_id = None
    return pj


def _make_proposal(
    status: str = ProposalStatus.PENDING.value,
    proposed_jobs: list | None = None,
) -> Mock:
    proposal = Mock(spec=ContractRenewalProposal)
    proposal.id = uuid4()
    proposal.service_agreement_id = uuid4()
    proposal.customer_id = uuid4()
    proposal.status = status
    proposal.proposed_job_count = len(proposed_jobs or [])
    proposal.created_at = datetime.now(timezone.utc)
    proposal.reviewed_at = None
    proposal.reviewed_by = None
    proposal.proposed_jobs = proposed_jobs or []
    proposal.service_agreement = _make_agreement()
    return proposal


# ===================================================================
# _roll_forward_prefs tests (Req 31.2)
# ===================================================================


@pytest.mark.unit
class TestRollForwardPrefs:
    def test_rolls_dates_forward_52_weeks(self) -> None:
        prefs = {"spring_startup": "2025-04-07"}
        result = _roll_forward_prefs(prefs)
        rolled = date.fromisoformat(result["spring_startup"])
        original = date(2025, 4, 7)
        assert (rolled - original).days == 364  # 52 weeks

    def test_preserves_non_string_values(self) -> None:
        prefs = {"count": 5, "spring_startup": "2025-04-07"}
        result = _roll_forward_prefs(prefs)
        assert result["count"] == 5

    def test_preserves_invalid_date_strings(self) -> None:
        prefs = {"notes": "some text"}
        result = _roll_forward_prefs(prefs)
        assert result["notes"] == "some text"

    def test_empty_prefs(self) -> None:
        assert _roll_forward_prefs({}) == {}


# ===================================================================
# _resolve_proposed_dates tests (Req 31.3)
# ===================================================================


@pytest.mark.unit
class TestResolveProposedDates:
    def test_uses_week_pref_when_available(self) -> None:
        prefs = {"spring_startup_4": "2026-04-06"}
        start, end = _resolve_proposed_dates("spring_startup", 4, 4, 2026, prefs)
        # Should use align_to_week on the pref date
        assert start.weekday() == 0  # Monday
        assert end.weekday() == 6  # Sunday

    def test_falls_back_to_calendar_month_defaults(self) -> None:
        start, end = _resolve_proposed_dates("spring_startup", 4, 4, 2026, {})
        assert start == date(2026, 4, 1)
        assert end == date(2026, 4, 30)

    def test_multi_month_range_fallback(self) -> None:
        start, end = _resolve_proposed_dates("fall_winterization", 10, 10, 2026, {})
        assert start == date(2026, 10, 1)
        assert end == date(2026, 10, 31)

    def test_job_type_key_fallback(self) -> None:
        # If "spring_startup_4" not in prefs, tries "spring_startup"
        prefs = {"spring_startup": "2026-04-13"}
        start, _end = _resolve_proposed_dates("spring_startup", 4, 4, 2026, prefs)
        assert start.weekday() == 0  # Monday


# ===================================================================
# generate_proposal tests (Req 31.1, 31.2, 31.3)
# ===================================================================


@pytest.mark.unit
class TestGenerateProposal:
    @pytest.mark.asyncio
    async def test_generates_essential_proposal(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        agreement = _make_agreement("Essential", "essential")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = agreement
        mock_session.execute.return_value = mock_result

        await service.generate_proposal(agreement.id)

        # Essential tier has 2 jobs (spring_startup + fall_winterization)
        assert mock_session.add.call_count >= 3  # 1 proposal + 2 jobs

    @pytest.mark.asyncio
    async def test_generates_professional_proposal(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        agreement = _make_agreement("Professional", "professional")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = agreement
        mock_session.execute.return_value = mock_result

        await service.generate_proposal(agreement.id)

        # Professional tier has 3 jobs
        assert mock_session.add.call_count >= 4  # 1 proposal + 3 jobs

    @pytest.mark.asyncio
    async def test_generates_winterization_only_proposal(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        agreement = _make_agreement("Winterization Only", "winterization-only-basic")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = agreement
        mock_session.execute.return_value = mock_result

        await service.generate_proposal(agreement.id)

        # Winterization-only has 1 job
        assert mock_session.add.call_count >= 2  # 1 proposal + 1 job

    @pytest.mark.asyncio
    async def test_unknown_tier_raises(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        agreement = _make_agreement("UnknownTier", "unknown-tier")
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = agreement
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Unknown tier"):
            await service.generate_proposal(agreement.id)

    @pytest.mark.asyncio
    async def test_agreement_not_found_raises(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.generate_proposal(uuid4())

    @pytest.mark.asyncio
    async def test_rolls_forward_existing_prefs(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        prefs = {"spring_startup_4": "2025-04-07"}
        agreement = _make_agreement("Essential", "essential", prefs=prefs)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = agreement
        mock_session.execute.return_value = mock_result

        await service.generate_proposal(agreement.id)

        # Should have been called — we just verify no error
        assert mock_session.add.call_count >= 3


# ===================================================================
# approve_all tests (Req 31.6)
# ===================================================================


@pytest.mark.unit
class TestApproveAll:
    @pytest.mark.asyncio
    async def test_approves_all_pending_jobs(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj1 = _make_proposed_job()
        pj2 = _make_proposed_job(service_type="fall_winterization")
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = proposal
        mock_session.execute.return_value = mock_result

        admin_id = uuid4()
        result = await service.approve_all(proposal.id, admin_id)

        assert pj1.status == ProposedJobStatus.APPROVED.value
        assert pj2.status == ProposedJobStatus.APPROVED.value
        assert result.status == ProposalStatus.APPROVED.value
        assert result.reviewed_by == admin_id

    @pytest.mark.asyncio
    async def test_skips_non_pending_jobs(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj1 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        pj2 = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = proposal
        mock_session.execute.return_value = mock_result

        await service.approve_all(proposal.id, uuid4())

        # Already-rejected job stays rejected
        assert pj1.status == ProposedJobStatus.REJECTED.value
        assert pj2.status == ProposedJobStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_creates_real_jobs(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj1 = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj1])

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = proposal
        mock_session.execute.return_value = mock_result

        await service.approve_all(proposal.id, uuid4())

        # session.add called for each created Job
        assert mock_session.add.called

    @pytest.mark.asyncio
    async def test_proposal_not_found_raises(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.approve_all(uuid4(), uuid4())


# ===================================================================
# reject_all tests (Req 31.10)
# ===================================================================


@pytest.mark.unit
class TestRejectAll:
    @pytest.mark.asyncio
    async def test_rejects_all_pending_jobs(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj1 = _make_proposed_job()
        pj2 = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = proposal
        mock_session.execute.return_value = mock_result

        admin_id = uuid4()
        result = await service.reject_all(proposal.id, admin_id)

        assert pj1.status == ProposedJobStatus.REJECTED.value
        assert pj2.status == ProposedJobStatus.REJECTED.value
        assert result.status == ProposalStatus.REJECTED.value
        assert result.reviewed_by == admin_id

    @pytest.mark.asyncio
    async def test_no_jobs_created_on_reject(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj1 = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj1])

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = proposal
        mock_session.execute.return_value = mock_result

        await service.reject_all(proposal.id, uuid4())

        # No Job records should be added
        assert not mock_session.add.called


# ===================================================================
# approve_job tests (Req 31.7, 31.8, 31.9)
# ===================================================================


@pytest.mark.unit
class TestApproveJob:
    @pytest.mark.asyncio
    async def test_approves_single_job(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj])
        pj.proposal_id = proposal.id

        # First execute returns the proposed job, second returns the proposal
        mock_result_pj = Mock()
        mock_result_pj.scalar_one_or_none.return_value = pj
        mock_result_proposal = Mock()
        mock_result_proposal.scalar_one_or_none.return_value = proposal
        mock_session.execute.side_effect = [mock_result_pj, mock_result_proposal]

        await service.approve_job(pj.id, uuid4())

        assert pj.status == ProposedJobStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_applies_modifications(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj])
        pj.proposal_id = proposal.id

        mock_result_pj = Mock()
        mock_result_pj.scalar_one_or_none.return_value = pj
        mock_result_proposal = Mock()
        mock_result_proposal.scalar_one_or_none.return_value = proposal
        mock_session.execute.side_effect = [mock_result_pj, mock_result_proposal]

        mods = ProposedJobModification(
            target_start_date=date(2026, 5, 4),
            target_end_date=date(2026, 5, 10),
            admin_notes="Moved to May",
        )
        await service.approve_job(pj.id, uuid4(), modifications=mods)

        assert pj.target_start_date == date(2026, 5, 4)
        assert pj.target_end_date == date(2026, 5, 10)
        assert pj.admin_notes == "Moved to May"

    @pytest.mark.asyncio
    async def test_not_found_raises(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.approve_job(uuid4(), uuid4())


# ===================================================================
# reject_job tests (Req 31.7, 31.11)
# ===================================================================


@pytest.mark.unit
class TestRejectJob:
    @pytest.mark.asyncio
    async def test_rejects_single_job(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        pj = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj])
        pj.proposal_id = proposal.id

        mock_result_pj = Mock()
        mock_result_pj.scalar_one_or_none.return_value = pj
        mock_result_proposal = Mock()
        mock_result_proposal.scalar_one_or_none.return_value = proposal
        mock_session.execute.side_effect = [mock_result_pj, mock_result_proposal]

        await service.reject_job(pj.id, uuid4())

        assert pj.status == ProposedJobStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_not_found_raises(
        self,
        service: ContractRenewalReviewService,
        mock_session: AsyncMock,
    ) -> None:
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="not found"):
            await service.reject_job(uuid4(), uuid4())


# ===================================================================
# _update_proposal_status tests
# ===================================================================


@pytest.mark.unit
class TestUpdateProposalStatus:
    @pytest.mark.asyncio
    async def test_all_approved_sets_approved(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        pj1 = _make_proposed_job(status=ProposedJobStatus.APPROVED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.APPROVED.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        admin_id = uuid4()
        await service._update_proposal_status(proposal, admin_id)

        assert proposal.status == ProposalStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_all_rejected_sets_rejected(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        pj1 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        await service._update_proposal_status(proposal, uuid4())

        assert proposal.status == ProposalStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_mixed_sets_partially_approved(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        pj1 = _make_proposed_job(status=ProposedJobStatus.APPROVED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        await service._update_proposal_status(proposal, uuid4())

        assert proposal.status == ProposalStatus.PARTIALLY_APPROVED.value

    @pytest.mark.asyncio
    async def test_approved_plus_pending_sets_partially_approved(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        """bughunt M-13: an APPROVED+PENDING mix is now PARTIALLY_APPROVED
        instead of staying PENDING. Previously the partial state required
        every job to be decided, so a proposal where the admin approved
        2 of 7 and walked away stayed PENDING on the dashboard despite
        having visible approvals."""
        pj1 = _make_proposed_job(status=ProposedJobStatus.APPROVED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.PENDING.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        await service._update_proposal_status(proposal, uuid4())

        assert proposal.status == ProposalStatus.PARTIALLY_APPROVED.value

    @pytest.mark.asyncio
    async def test_approved_plus_rejected_plus_pending_sets_partially_approved(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        """All three statuses present → still PARTIALLY_APPROVED — at
        least one approval has landed, so the proposal is no longer in
        the "untouched" PENDING state."""
        pj1 = _make_proposed_job(status=ProposedJobStatus.APPROVED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        pj3 = _make_proposed_job(status=ProposedJobStatus.PENDING.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2, pj3])

        await service._update_proposal_status(proposal, uuid4())

        assert proposal.status == ProposalStatus.PARTIALLY_APPROVED.value

    @pytest.mark.asyncio
    async def test_rejected_plus_pending_keeps_pending(
        self,
        service: ContractRenewalReviewService,
    ) -> None:
        """bughunt M-13: REJECTED+PENDING (no approvals) stays PENDING —
        the dashboard signal is "still untouched on the approval side"."""
        pj1 = _make_proposed_job(status=ProposedJobStatus.REJECTED.value)
        pj2 = _make_proposed_job(status=ProposedJobStatus.PENDING.value)
        proposal = _make_proposal(proposed_jobs=[pj1, pj2])

        await service._update_proposal_status(proposal, uuid4())

        assert proposal.status == ProposalStatus.PENDING.value


# ===================================================================
# _create_job_from_proposed tests
# ===================================================================


@pytest.mark.unit
class TestCreateJobFromProposed:
    def test_creates_job_with_correct_fields(self) -> None:
        pj = _make_proposed_job()
        proposal = _make_proposal(proposed_jobs=[pj])

        job = ContractRenewalReviewService._create_job_from_proposed(pj, proposal)

        assert job.customer_id == proposal.customer_id
        assert job.status == JobStatus.TO_BE_SCHEDULED.value
        assert job.category == JobCategory.READY_TO_SCHEDULE.value
        assert job.job_type == pj.service_type
        assert job.target_start_date == pj.target_start_date
        assert job.target_end_date == pj.target_end_date

    def test_uses_payload_description(self) -> None:
        pj = _make_proposed_job()
        pj.proposed_job_payload = {"description": "Custom desc", "priority": 2}
        proposal = _make_proposal(proposed_jobs=[pj])

        job = ContractRenewalReviewService._create_job_from_proposed(pj, proposal)

        assert job.description == "Custom desc"
        assert job.priority_level == 2

    def test_handles_empty_payload(self) -> None:
        pj = _make_proposed_job()
        pj.proposed_job_payload = None
        proposal = _make_proposal(proposed_jobs=[pj])

        job = ContractRenewalReviewService._create_job_from_proposed(pj, proposal)

        assert job.description == pj.service_type
        assert job.priority_level == 0
