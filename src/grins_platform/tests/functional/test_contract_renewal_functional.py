"""Functional tests for contract renewal flow.

Tests the full contract renewal lifecycle with mocked DB:
- Proposal generation from service agreement
- Approve all → creates real Job records
- Reject all → sets proposal status to rejected
- Per-job approve/reject with optional Week Of modification
- Fallback to calendar-month defaults when no prior preferences

Validates: Requirements 31.1, 31.6, 31.7, 31.10
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock
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
from grins_platform.models.job import Job
from grins_platform.schemas.contract_renewal import ProposedJobModification
from grins_platform.services.contract_renewal_service import (
    ContractRenewalReviewService,
)
from grins_platform.utils.week_alignment import align_to_week


# =============================================================================
# Helpers
# =============================================================================


def _make_tier(**overrides: Any) -> MagicMock:
    """Create a mock ServiceAgreementTier."""
    tier = MagicMock()
    tier.id = overrides.get("id", uuid4())
    tier.name = overrides.get("name", "Professional")
    tier.slug = overrides.get("slug", "professional-annual")
    return tier


def _make_agreement(**overrides: Any) -> MagicMock:
    """Create a mock ServiceAgreement with tier relationship."""
    agreement = MagicMock()
    agreement.id = overrides.get("id", uuid4())
    agreement.customer_id = overrides.get("customer_id", uuid4())
    agreement.tier = overrides.get("tier", _make_tier())
    agreement.property_id = overrides.get("property_id", uuid4())
    agreement.service_week_preferences = overrides.get(
        "service_week_preferences", None,
    )
    agreement.auto_renew = overrides.get("auto_renew", True)
    return agreement


def _make_proposed_job(**overrides: Any) -> MagicMock:
    """Create a mock ContractRenewalProposedJob for testing."""
    pj = MagicMock(spec=ContractRenewalProposedJob)
    pj.id = overrides.get("id", uuid4())
    pj.proposal_id = overrides.get("proposal_id", uuid4())
    pj.service_type = overrides.get("service_type", "spring_startup")
    pj.target_start_date = overrides.get("target_start_date", date(2026, 4, 1))
    pj.target_end_date = overrides.get("target_end_date", date(2026, 4, 30))
    pj.status = overrides.get("status", ProposedJobStatus.PENDING.value)
    pj.proposed_job_payload = overrides.get("proposed_job_payload", {
        "description": "Spring system activation",
        "month_start": 4,
        "month_end": 4,
        "priority": 1,
    })
    pj.admin_notes = overrides.get("admin_notes", None)
    pj.created_job_id = overrides.get("created_job_id", None)
    return pj


def _make_proposal(**overrides: Any) -> MagicMock:
    """Create a mock ContractRenewalProposal for testing."""
    proposal = MagicMock(spec=ContractRenewalProposal)
    proposal.id = overrides.get("id", uuid4())
    proposal.service_agreement_id = overrides.get("service_agreement_id", uuid4())
    proposal.customer_id = overrides.get("customer_id", uuid4())
    proposal.status = overrides.get("status", ProposalStatus.PENDING.value)
    proposal.proposed_job_count = overrides.get("proposed_job_count", 3)
    proposal.created_at = overrides.get(
        "created_at", datetime.now(tz=timezone.utc),
    )
    proposal.reviewed_at = overrides.get("reviewed_at", None)
    proposal.reviewed_by = overrides.get("reviewed_by", None)
    proposal.proposed_jobs = overrides.get("proposed_jobs", [])
    # Wire up service_agreement for _create_job_from_proposed
    sa_mock = MagicMock()
    sa_mock.property_id = overrides.get("property_id", uuid4())
    proposal.service_agreement = overrides.get("service_agreement", sa_mock)
    proposal.service_agreement_id = overrides.get(
        "service_agreement_id", proposal.service_agreement_id,
    )
    return proposal


def _build_mock_db_for_generate(agreement: MagicMock) -> AsyncMock:
    """Build a mock AsyncSession for generate_proposal.

    Handles:
    - SELECT ServiceAgreement with selectinload(tier)
    - db.add() for proposal and proposed jobs
    - db.flush() / db.refresh()
    """
    db = AsyncMock()
    db._added_objects: list[Any] = []

    def _add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        db._added_objects.append(obj)

    db.add = MagicMock(side_effect=_add_side_effect)

    # SELECT for _load_agreement
    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        result = MagicMock()
        result.scalar_one_or_none.return_value = agreement
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    db.flush = AsyncMock()

    async def _refresh_side_effect(obj: Any) -> None:
        # Populate proposed_jobs from added objects on refresh
        if isinstance(obj, ContractRenewalProposal):
            obj.proposed_jobs = [
                o for o in db._added_objects
                if isinstance(o, ContractRenewalProposedJob)
            ]

    db.refresh = AsyncMock(side_effect=_refresh_side_effect)
    return db


def _build_mock_db_for_proposal_action(
    proposal: ContractRenewalProposal,
) -> AsyncMock:
    """Build a mock AsyncSession for approve/reject operations.

    Handles:
    - SELECT ContractRenewalProposal with selectinload(proposed_jobs)
    - db.add() for new Job records
    - db.flush() / db.refresh()
    """
    db = AsyncMock()
    db._added_objects: list[Any] = []

    def _add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        # Auto-assign id to Job objects
        if isinstance(obj, Job) and (not hasattr(obj, "id") or obj.id is None):
            obj.id = uuid4()
        db._added_objects.append(obj)

    db.add = MagicMock(side_effect=_add_side_effect)

    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        result = MagicMock()
        result.scalar_one_or_none.return_value = proposal
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _build_mock_db_for_per_job_action(
    proposed_job: ContractRenewalProposedJob,
    proposal: ContractRenewalProposal,
) -> AsyncMock:
    """Build a mock AsyncSession for per-job approve/reject.

    First execute returns the proposed_job, second returns the proposal.
    """
    db = AsyncMock()
    db._added_objects: list[Any] = []

    def _add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid4()
        db._added_objects.append(obj)

    db.add = MagicMock(side_effect=_add_side_effect)

    call_count = 0

    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        nonlocal call_count
        result = MagicMock()
        if call_count == 0:
            result.scalar_one_or_none.return_value = proposed_job
        else:
            result.scalar_one_or_none.return_value = proposal
        call_count += 1
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


# =============================================================================
# 1. Proposal Generation from Service Agreement
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestProposalGeneration:
    """Test proposal generation from a service agreement.

    Validates: Requirement 31.1
    """

    async def test_generate_proposal_creates_correct_job_count_for_professional(
        self,
    ) -> None:
        """Professional tier generates 3 proposed jobs (spring, mid, fall).

        Validates: Requirement 31.1
        """
        tier = _make_tier(name="Professional", slug="professional-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences=None)
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        proposal = await svc.generate_proposal(agreement.id)

        assert proposal.proposed_job_count == 3
        assert proposal.status == ProposalStatus.PENDING.value
        assert proposal.customer_id == agreement.customer_id
        assert proposal.service_agreement_id == agreement.id

    async def test_generate_proposal_creates_correct_job_count_for_essential(
        self,
    ) -> None:
        """Essential tier generates 2 proposed jobs (spring, fall).

        Validates: Requirement 31.1
        """
        tier = _make_tier(name="Essential", slug="essential-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences=None)
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        proposal = await svc.generate_proposal(agreement.id)

        assert proposal.proposed_job_count == 2

    async def test_generate_proposal_creates_correct_job_count_for_premium(
        self,
    ) -> None:
        """Premium tier generates 7 proposed jobs.

        Validates: Requirement 31.1
        """
        tier = _make_tier(name="Premium", slug="premium-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences=None)
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        proposal = await svc.generate_proposal(agreement.id)

        assert proposal.proposed_job_count == 7

    async def test_generate_proposal_proposed_jobs_have_pending_status(
        self,
    ) -> None:
        """All proposed jobs start with pending status.

        Validates: Requirement 31.1
        """
        tier = _make_tier(name="Professional", slug="professional-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences=None)
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        proposal = await svc.generate_proposal(agreement.id)

        proposed_jobs = [
            o for o in db._added_objects
            if isinstance(o, ContractRenewalProposedJob)
        ]
        assert len(proposed_jobs) == 3
        for pj in proposed_jobs:
            assert pj.status == ProposedJobStatus.PENDING.value

    async def test_generate_proposal_with_week_preferences_rolls_forward(
        self,
    ) -> None:
        """Week preferences are rolled forward by +1 year.

        Validates: Requirements 31.1, 31.2 (via Req 31.1 context)
        """
        # 2025-04-07 is a Monday
        prefs = {
            "spring_startup_4": "2025-04-07",
            "mid_season_inspection": "2025-07-07",
            "fall_winterization": "2025-10-06",
        }
        tier = _make_tier(name="Professional", slug="professional-annual")
        agreement = _make_agreement(
            tier=tier, service_week_preferences=prefs,
        )
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        proposal = await svc.generate_proposal(agreement.id)

        proposed_jobs = [
            o for o in db._added_objects
            if isinstance(o, ContractRenewalProposedJob)
        ]
        # The spring startup job should use the rolled-forward preference
        spring_jobs = [pj for pj in proposed_jobs if pj.service_type == "spring_startup"]
        assert len(spring_jobs) == 1
        spring = spring_jobs[0]
        # Rolled forward: 2025-04-07 + 52 weeks = 2026-04-06 (Monday)
        expected_monday = date(2025, 4, 7) + timedelta(weeks=52)
        expected_start, expected_end = align_to_week(expected_monday)
        assert spring.target_start_date == expected_start
        assert spring.target_end_date == expected_end


# =============================================================================
# 2. Fallback to Calendar-Month Defaults
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCalendarMonthFallback:
    """Test fallback to calendar-month defaults when no prior preferences.

    Validates: Requirement 31.10 (via Req 31.3 context)
    """

    async def test_no_preferences_uses_calendar_month_defaults(self) -> None:
        """Without preferences, dates fall back to month start/end.

        Validates: Requirement 31.1 (fallback behavior)
        """
        tier = _make_tier(name="Essential", slug="essential-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences=None)
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        await svc.generate_proposal(agreement.id)

        proposed_jobs = [
            o for o in db._added_objects
            if isinstance(o, ContractRenewalProposedJob)
        ]
        year = datetime.now(timezone.utc).year

        spring_jobs = [pj for pj in proposed_jobs if pj.service_type == "spring_startup"]
        assert len(spring_jobs) == 1
        spring = spring_jobs[0]
        # Calendar-month default: April 1 to April 30
        assert spring.target_start_date == date(year, 4, 1)
        last_day_apr = calendar.monthrange(year, 4)[1]
        assert spring.target_end_date == date(year, 4, last_day_apr)

        fall_jobs = [pj for pj in proposed_jobs if pj.service_type == "fall_winterization"]
        assert len(fall_jobs) == 1
        fall = fall_jobs[0]
        # Calendar-month default: October 1 to October 31
        assert fall.target_start_date == date(year, 10, 1)
        last_day_oct = calendar.monthrange(year, 10)[1]
        assert fall.target_end_date == date(year, 10, last_day_oct)

    async def test_empty_preferences_dict_uses_calendar_month_defaults(
        self,
    ) -> None:
        """Empty preferences dict {} also falls back to month defaults."""
        tier = _make_tier(name="Essential", slug="essential-annual")
        agreement = _make_agreement(tier=tier, service_week_preferences={})
        db = _build_mock_db_for_generate(agreement)

        svc = ContractRenewalReviewService(session=db)
        await svc.generate_proposal(agreement.id)

        proposed_jobs = [
            o for o in db._added_objects
            if isinstance(o, ContractRenewalProposedJob)
        ]
        year = datetime.now(timezone.utc).year

        for pj in proposed_jobs:
            if pj.service_type == "spring_startup":
                assert pj.target_start_date == date(year, 4, 1)
            elif pj.service_type == "fall_winterization":
                assert pj.target_start_date == date(year, 10, 1)


# =============================================================================
# 3. Approve All → Creates Real Job Records
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestApproveAllFlow:
    """Test bulk approve creates real Job records.

    Validates: Requirement 31.6
    """

    async def test_approve_all_creates_jobs_for_all_pending_proposed_jobs(
        self,
    ) -> None:
        """Approve all creates a real Job for each pending proposed job.

        Validates: Requirement 31.6
        """
        proposal_id = uuid4()
        customer_id = uuid4()
        agreement_id = uuid4()

        pj1 = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.PENDING.value,
        )
        pj2 = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="mid_season_inspection",
            status=ProposedJobStatus.PENDING.value,
        )
        pj3 = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            customer_id=customer_id,
            service_agreement_id=agreement_id,
            proposed_jobs=[pj1, pj2, pj3],
            proposed_job_count=3,
        )

        db = _build_mock_db_for_proposal_action(proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        result = await svc.approve_all(proposal_id, admin_id)

        # Proposal status set to approved
        assert result.status == ProposalStatus.APPROVED.value
        assert result.reviewed_by == admin_id
        assert result.reviewed_at is not None

        # All proposed jobs marked approved
        for pj in [pj1, pj2, pj3]:
            assert pj.status == ProposedJobStatus.APPROVED.value
            assert pj.created_job_id is not None

        # Real Job objects were added to the session
        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 3

    async def test_approve_all_creates_jobs_with_correct_attributes(
        self,
    ) -> None:
        """Created jobs have correct customer_id, status, and dates.

        Validates: Requirement 31.6
        """
        proposal_id = uuid4()
        customer_id = uuid4()
        start = date(2026, 4, 6)
        end = date(2026, 4, 12)

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            target_start_date=start,
            target_end_date=end,
            proposed_job_payload={
                "description": "Spring activation",
                "month_start": 4,
                "month_end": 4,
                "priority": 1,
            },
        )

        proposal = _make_proposal(
            id=proposal_id,
            customer_id=customer_id,
            proposed_jobs=[pj],
            proposed_job_count=1,
        )

        db = _build_mock_db_for_proposal_action(proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        await svc.approve_all(proposal_id, admin_id)

        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 1
        job = added_jobs[0]
        assert job.customer_id == customer_id
        assert job.status == JobStatus.TO_BE_SCHEDULED.value
        assert job.category == JobCategory.READY_TO_SCHEDULE.value
        assert job.job_type == "spring_startup"
        assert job.target_start_date == start
        assert job.target_end_date == end
        assert job.description == "Spring activation"

    async def test_approve_all_skips_already_non_pending_jobs(self) -> None:
        """Approve all only processes pending jobs, skips rejected ones."""
        proposal_id = uuid4()

        pj_pending = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.PENDING.value,
        )
        pj_rejected = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.REJECTED.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            proposed_jobs=[pj_pending, pj_rejected],
            proposed_job_count=2,
        )

        db = _build_mock_db_for_proposal_action(proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        await svc.approve_all(proposal_id, admin_id)

        # Only the pending job was approved
        assert pj_pending.status == ProposedJobStatus.APPROVED.value
        assert pj_pending.created_job_id is not None
        # Rejected job stays rejected
        assert pj_rejected.status == ProposedJobStatus.REJECTED.value
        assert pj_rejected.created_job_id is None

        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 1


# =============================================================================
# 4. Reject All → Sets Proposal Status to Rejected
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestRejectAllFlow:
    """Test bulk reject sets proposal and all jobs to rejected.

    Validates: Requirement 31.10
    """

    async def test_reject_all_marks_all_pending_jobs_rejected(self) -> None:
        """Reject all sets every pending proposed job to rejected.

        Validates: Requirement 31.10
        """
        proposal_id = uuid4()

        pj1 = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.PENDING.value,
        )
        pj2 = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            proposed_jobs=[pj1, pj2],
            proposed_job_count=2,
        )

        db = _build_mock_db_for_proposal_action(proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        result = await svc.reject_all(proposal_id, admin_id)

        # Proposal status set to rejected
        assert result.status == ProposalStatus.REJECTED.value
        assert result.reviewed_by == admin_id
        assert result.reviewed_at is not None

        # All proposed jobs marked rejected
        assert pj1.status == ProposedJobStatus.REJECTED.value
        assert pj2.status == ProposedJobStatus.REJECTED.value

    async def test_reject_all_creates_no_job_records(self) -> None:
        """Reject all does not create any real Job records.

        Validates: Requirement 31.10
        """
        proposal_id = uuid4()

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            proposed_jobs=[pj],
            proposed_job_count=1,
        )

        db = _build_mock_db_for_proposal_action(proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        await svc.reject_all(proposal_id, admin_id)

        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 0
        assert pj.created_job_id is None


# =============================================================================
# 5. Per-Job Approve/Reject with Optional Week Of Modification
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestPerJobApproveReject:
    """Test per-job approve/reject with optional modifications.

    Validates: Requirements 31.7, 31.10
    """

    async def test_approve_single_job_creates_real_job(self) -> None:
        """Approving a single proposed job creates a real Job record.

        Validates: Requirement 31.7
        """
        proposal_id = uuid4()
        customer_id = uuid4()

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.PENDING.value,
        )

        # Other job stays pending → proposal becomes partially_approved
        pj_other = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            customer_id=customer_id,
            proposed_jobs=[pj, pj_other],
            proposed_job_count=2,
        )

        db = _build_mock_db_for_per_job_action(pj, proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        result = await svc.approve_job(pj.id, admin_id)

        assert result.status == ProposedJobStatus.APPROVED.value
        assert result.created_job_id is not None

        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 1

    async def test_approve_job_with_week_of_modification(self) -> None:
        """Approving with modifications updates dates before creating job.

        Validates: Requirements 31.7, 31.8 (Week Of modification)
        """
        proposal_id = uuid4()
        customer_id = uuid4()

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            target_start_date=date(2026, 4, 6),
            target_end_date=date(2026, 4, 12),
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            customer_id=customer_id,
            proposed_jobs=[pj],
            proposed_job_count=1,
        )

        db = _build_mock_db_for_per_job_action(pj, proposal)
        admin_id = uuid4()

        # Modify Week Of to a different week
        new_start = date(2026, 4, 13)  # Monday
        new_end = date(2026, 4, 19)    # Sunday
        modifications = ProposedJobModification(
            target_start_date=new_start,
            target_end_date=new_end,
            admin_notes="Moved to second week of April per customer request",
        )

        svc = ContractRenewalReviewService(session=db)
        result = await svc.approve_job(pj.id, admin_id, modifications=modifications)

        # Dates were updated before job creation
        assert result.target_start_date == new_start
        assert result.target_end_date == new_end
        assert result.admin_notes == "Moved to second week of April per customer request"

        # Job was created with the modified dates
        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 1
        job = added_jobs[0]
        assert job.target_start_date == new_start
        assert job.target_end_date == new_end

    async def test_reject_single_job_does_not_create_job(self) -> None:
        """Rejecting a single proposed job creates no Job record.

        Validates: Requirement 31.7
        """
        proposal_id = uuid4()

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.PENDING.value,
        )

        # Other job stays pending
        pj_other = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            proposed_jobs=[pj, pj_other],
            proposed_job_count=2,
        )

        db = _build_mock_db_for_per_job_action(pj, proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        result = await svc.reject_job(pj.id, admin_id)

        assert result.status == ProposedJobStatus.REJECTED.value
        assert result.created_job_id is None

        added_jobs = [o for o in db._added_objects if isinstance(o, Job)]
        assert len(added_jobs) == 0

    async def test_mixed_approve_reject_sets_partially_approved(self) -> None:
        """Approving some and rejecting others → partially_approved.

        Validates: Requirements 31.7, 31.10
        """
        proposal_id = uuid4()
        customer_id = uuid4()

        pj_approved = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            status=ProposedJobStatus.APPROVED.value,
        )
        pj_to_reject = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="fall_winterization",
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            customer_id=customer_id,
            proposed_jobs=[pj_approved, pj_to_reject],
            proposed_job_count=2,
        )

        db = _build_mock_db_for_per_job_action(pj_to_reject, proposal)
        admin_id = uuid4()

        svc = ContractRenewalReviewService(session=db)
        await svc.reject_job(pj_to_reject.id, admin_id)

        assert pj_to_reject.status == ProposedJobStatus.REJECTED.value
        # Proposal should be partially_approved (mix of approved + rejected)
        assert proposal.status == ProposalStatus.PARTIALLY_APPROVED.value

    async def test_approve_job_with_admin_notes_only(self) -> None:
        """Approving with only admin_notes preserves original dates.

        Validates: Requirement 31.9
        """
        proposal_id = uuid4()
        original_start = date(2026, 4, 6)
        original_end = date(2026, 4, 12)

        pj = _make_proposed_job(
            proposal_id=proposal_id,
            service_type="spring_startup",
            target_start_date=original_start,
            target_end_date=original_end,
            status=ProposedJobStatus.PENDING.value,
        )

        proposal = _make_proposal(
            id=proposal_id,
            proposed_jobs=[pj],
            proposed_job_count=1,
        )

        db = _build_mock_db_for_per_job_action(pj, proposal)
        admin_id = uuid4()

        modifications = ProposedJobModification(
            admin_notes="Customer confirmed this week works",
        )

        svc = ContractRenewalReviewService(session=db)
        result = await svc.approve_job(pj.id, admin_id, modifications=modifications)

        # Dates unchanged
        assert result.target_start_date == original_start
        assert result.target_end_date == original_end
        # Notes applied
        assert result.admin_notes == "Customer confirmed this week works"
