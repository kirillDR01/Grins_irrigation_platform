"""Contract renewal review service.

Generates renewal proposals from auto-renewed service agreements and
provides approve/reject workflows for individual or batch proposed jobs.

Validates: CRM Changes Update 2 Req 31.1, 31.2, 31.3, 31.6, 31.7, 31.8, 31.10
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
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
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.utils.week_alignment import align_to_week

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.schemas.contract_renewal import ProposedJobModification

# Tier name → list of (job_type, description, month_start, month_end)
_ESSENTIAL_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]
_PROFESSIONAL_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("mid_season_inspection", "Mid-season system inspection and adjustment", 7, 7),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]
_PREMIUM_JOBS: list[tuple[str, str, int, int]] = [
    ("spring_startup", "Spring system activation and inspection", 4, 4),
    ("monthly_visit", "Monthly system check and adjustment", 5, 5),
    ("monthly_visit", "Monthly system check and adjustment", 6, 6),
    ("monthly_visit", "Monthly system check and adjustment", 7, 7),
    ("monthly_visit", "Monthly system check and adjustment", 8, 8),
    ("monthly_visit", "Monthly system check and adjustment", 9, 9),
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]
_WINTERIZATION_ONLY_JOBS: list[tuple[str, str, int, int]] = [
    ("fall_winterization", "Fall system winterization and blowout", 10, 10),
]
_TIER_JOB_MAP: dict[str, list[tuple[str, str, int, int]]] = {
    "Essential": _ESSENTIAL_JOBS,
    "Professional": _PROFESSIONAL_JOBS,
    "Premium": _PREMIUM_JOBS,
}
_TIER_PRIORITY_MAP: dict[str, int] = {
    "Essential": 0,
    "Professional": 1,
    "Premium": 2,
}


def _roll_forward_prefs(
    prefs: dict[str, Any],
) -> dict[str, Any]:
    """Roll forward week preferences by +1 calendar year, Monday-aligned.

    Each value is an ISO date string (Monday). We parse it, advance by
    exactly one calendar year (falling back to Feb 28 if the source is
    Feb 29 of a leap year), and snap to the closest preceding Monday so
    the renewal keeps its weekly slot across many years without drifting
    off the original weekday.

    Validates: Req 31.2
    """
    rolled: dict[str, Any] = {}
    for key, val in prefs.items():
        if not isinstance(val, str):
            rolled[key] = val
            continue
        try:
            d = date.fromisoformat(val)
        except ValueError:
            rolled[key] = val
            continue
        try:
            candidate = d.replace(year=d.year + 1)
        except ValueError:
            # Feb 29 → Feb 28 next year.
            candidate = d.replace(year=d.year + 1, day=28)
        monday = candidate - timedelta(days=candidate.weekday())
        rolled[key] = monday.isoformat()
    return rolled


def _resolve_proposed_dates(
    job_type: str,
    month_start: int,
    month_end: int,
    year: int,
    week_prefs: dict[str, Any],
) -> tuple[date, date]:
    """Resolve target dates for a proposed job, mirroring JobGenerator logic."""
    candidates = [f"{job_type}_{month_start}", job_type]
    for key in candidates:
        pref_monday_iso = week_prefs.get(key)
        if pref_monday_iso and isinstance(pref_monday_iso, str):
            try:
                pref_date = date.fromisoformat(pref_monday_iso)
                return align_to_week(pref_date)
            except ValueError:  # noqa: S110
                pass
    last_day = calendar.monthrange(year, month_end)[1]
    return date(year, month_start, 1), date(year, month_end, last_day)


class ContractRenewalReviewService(LoggerMixin):
    """Manages contract renewal proposal lifecycle.

    Validates: Req 31.1, 31.2, 31.3, 31.6, 31.7, 31.8, 31.10
    """

    DOMAIN = "renewals"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def _load_agreement(self, agreement_id: UUID) -> ServiceAgreement:
        stmt = (
            select(ServiceAgreement)
            .options(selectinload(ServiceAgreement.tier))
            .where(ServiceAgreement.id == agreement_id)
        )
        result = await self.session.execute(stmt)
        agreement: ServiceAgreement | None = result.scalar_one_or_none()
        if agreement is None:
            msg = f"ServiceAgreement {agreement_id} not found"
            raise ValueError(msg)
        return agreement

    async def _load_proposal(self, proposal_id: UUID) -> ContractRenewalProposal:
        stmt = (
            select(ContractRenewalProposal)
            .options(selectinload(ContractRenewalProposal.proposed_jobs))
            .where(ContractRenewalProposal.id == proposal_id)
        )
        result = await self.session.execute(stmt)
        proposal: ContractRenewalProposal | None = result.scalar_one_or_none()
        if proposal is None:
            msg = f"RenewalProposal {proposal_id} not found"
            raise ValueError(msg)
        return proposal

    async def generate_proposal(
        self,
        agreement_id: UUID,
    ) -> ContractRenewalProposal:
        """Create a renewal proposal with proposed jobs.

        Rolls forward prior-year service_week_preferences by +1 year.
        Falls back to calendar-month defaults if no preferences exist.

        Validates: Req 31.1, 31.2, 31.3
        """
        self.log_started("generate_proposal", agreement_id=str(agreement_id))

        agreement = await self._load_agreement(agreement_id)
        tier_name: str = agreement.tier.name
        tier_slug: str = agreement.tier.slug

        if tier_slug.startswith("winterization-only-"):
            job_specs: list[tuple[str, str, int, int]] | None = _WINTERIZATION_ONLY_JOBS
        else:
            job_specs = _TIER_JOB_MAP.get(tier_name)

        if not job_specs:
            self.log_failed(
                "generate_proposal",
                error=ValueError(f"Unknown tier: {tier_name}"),
            )
            msg = f"Unknown tier name: {tier_name}"
            raise ValueError(msg)

        # Roll forward preferences by +1 year (Req 31.2)
        raw_prefs: dict[str, Any] = agreement.service_week_preferences or {}
        week_prefs = _roll_forward_prefs(raw_prefs) if raw_prefs else {}

        now = datetime.now(timezone.utc)
        year = now.year

        proposal = ContractRenewalProposal(
            service_agreement_id=agreement.id,
            customer_id=agreement.customer_id,
            status=ProposalStatus.PENDING.value,
            proposed_job_count=len(job_specs),
            created_at=now,
        )
        self.session.add(proposal)
        await self.session.flush()

        for job_type, description, month_start, month_end in job_specs:
            start, end = _resolve_proposed_dates(
                job_type,
                month_start,
                month_end,
                year,
                week_prefs,
            )
            proposed_job = ContractRenewalProposedJob(
                proposal_id=proposal.id,
                service_type=job_type,
                target_start_date=start,
                target_end_date=end,
                status=ProposedJobStatus.PENDING.value,
                proposed_job_payload={
                    "description": description,
                    "month_start": month_start,
                    "month_end": month_end,
                    "priority": _TIER_PRIORITY_MAP.get(tier_name, 0),
                },
            )
            self.session.add(proposed_job)

        await self.session.flush()
        await self.session.refresh(proposal)

        self.log_completed(
            "generate_proposal",
            proposal_id=str(proposal.id),
            job_count=len(job_specs),
        )
        return proposal

    async def approve_all(
        self,
        proposal_id: UUID,
        admin_id: UUID,
    ) -> ContractRenewalProposal:
        """Bulk approve all proposed jobs and create real Job records.

        Validates: Req 31.6
        """
        self.log_started("approve_all", proposal_id=str(proposal_id))
        proposal = await self._load_proposal(proposal_id)
        now = datetime.now(timezone.utc)

        for pj in proposal.proposed_jobs:
            if pj.status == ProposedJobStatus.PENDING.value:
                pj.status = ProposedJobStatus.APPROVED.value
                job = self._create_job_from_proposed(pj, proposal)
                self.session.add(job)
                await self.session.flush()
                pj.created_job_id = job.id

        proposal.status = ProposalStatus.APPROVED.value
        proposal.reviewed_at = now
        proposal.reviewed_by = admin_id
        await self.session.flush()
        await self.session.refresh(proposal)

        self.log_completed("approve_all", proposal_id=str(proposal_id))
        return proposal

    async def reject_all(
        self,
        proposal_id: UUID,
        admin_id: UUID,
    ) -> ContractRenewalProposal:
        """Bulk reject all proposed jobs. No Job records created.

        Validates: Req 31.10
        """
        self.log_started("reject_all", proposal_id=str(proposal_id))
        proposal = await self._load_proposal(proposal_id)
        now = datetime.now(timezone.utc)

        for pj in proposal.proposed_jobs:
            if pj.status == ProposedJobStatus.PENDING.value:
                pj.status = ProposedJobStatus.REJECTED.value

        proposal.status = ProposalStatus.REJECTED.value
        proposal.reviewed_at = now
        proposal.reviewed_by = admin_id
        await self.session.flush()
        await self.session.refresh(proposal)

        self.log_completed("reject_all", proposal_id=str(proposal_id))
        return proposal

    async def approve_job(
        self,
        proposed_job_id: UUID,
        admin_id: UUID,
        modifications: ProposedJobModification | None = None,
    ) -> ContractRenewalProposedJob:
        """Approve a single proposed job, optionally modifying dates/notes.

        Validates: Req 31.7, 31.8, 31.9
        """
        self.log_started("approve_job", proposed_job_id=str(proposed_job_id))

        stmt = select(ContractRenewalProposedJob).where(
            ContractRenewalProposedJob.id == proposed_job_id,
        )
        result = await self.session.execute(stmt)
        pj: ContractRenewalProposedJob | None = result.scalar_one_or_none()
        if pj is None:
            msg = f"ProposedJob {proposed_job_id} not found"
            raise ValueError(msg)

        if modifications:
            if modifications.target_start_date is not None:
                pj.target_start_date = modifications.target_start_date
            if modifications.target_end_date is not None:
                pj.target_end_date = modifications.target_end_date
            if modifications.admin_notes is not None:
                pj.admin_notes = modifications.admin_notes

        pj.status = ProposedJobStatus.APPROVED.value

        proposal = await self._load_proposal(pj.proposal_id)
        job = self._create_job_from_proposed(pj, proposal)
        self.session.add(job)
        await self.session.flush()
        pj.created_job_id = job.id

        await self._update_proposal_status(proposal, admin_id)
        await self.session.refresh(pj)

        self.log_completed("approve_job", proposed_job_id=str(proposed_job_id))
        return pj

    async def reject_job(
        self,
        proposed_job_id: UUID,
        admin_id: UUID,
    ) -> ContractRenewalProposedJob:
        """Reject a single proposed job.

        Validates: Req 31.7, 31.11
        """
        self.log_started("reject_job", proposed_job_id=str(proposed_job_id))

        stmt = select(ContractRenewalProposedJob).where(
            ContractRenewalProposedJob.id == proposed_job_id,
        )
        result = await self.session.execute(stmt)
        pj: ContractRenewalProposedJob | None = result.scalar_one_or_none()
        if pj is None:
            msg = f"ProposedJob {proposed_job_id} not found"
            raise ValueError(msg)

        pj.status = ProposedJobStatus.REJECTED.value

        proposal = await self._load_proposal(pj.proposal_id)
        await self._update_proposal_status(proposal, admin_id)
        await self.session.refresh(pj)

        self.log_completed("reject_job", proposed_job_id=str(proposed_job_id))
        return pj

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_job_from_proposed(
        pj: ContractRenewalProposedJob,
        proposal: ContractRenewalProposal,
    ) -> Job:
        """Build a real Job from a proposed job."""
        payload: dict[str, Any] = pj.proposed_job_payload or {}
        return Job(
            customer_id=proposal.customer_id,
            property_id=proposal.service_agreement.property_id
            if proposal.service_agreement
            else None,
            service_agreement_id=proposal.service_agreement_id,
            job_type=pj.service_type,
            category=JobCategory.READY_TO_SCHEDULE.value,
            status=JobStatus.TO_BE_SCHEDULED.value,
            description=payload.get("description", pj.service_type),
            priority_level=payload.get("priority", 0),
            target_start_date=pj.target_start_date,
            target_end_date=pj.target_end_date,
            requested_at=datetime.now(timezone.utc),
        )

    async def _update_proposal_status(
        self,
        proposal: ContractRenewalProposal,
        admin_id: UUID,
    ) -> None:
        """Recompute proposal status from its proposed jobs.

        bughunt M-13: ``PARTIALLY_APPROVED`` now fires whenever at least
        one job is APPROVED *and* at least one is REJECTED or PENDING.
        Previously the partial state required *all* jobs to have been
        decided (no PENDING remaining), so a proposal where the admin
        approved 2 of 7 and walked away stayed PENDING on the dashboard
        even though it visibly had approvals.
        """
        now = datetime.now(timezone.utc)
        statuses = {pj.status for pj in proposal.proposed_jobs}

        approved_present = ProposedJobStatus.APPROVED.value in statuses
        rejected_present = ProposedJobStatus.REJECTED.value in statuses
        pending_present = ProposedJobStatus.PENDING.value in statuses

        if statuses == {ProposedJobStatus.APPROVED.value}:
            # Terminal: every job approved.
            proposal.status = ProposalStatus.APPROVED.value
        elif statuses == {ProposedJobStatus.REJECTED.value}:
            # Terminal: every job rejected.
            proposal.status = ProposalStatus.REJECTED.value
        elif approved_present and (rejected_present or pending_present):
            # Mixed signal: at least one approval landed alongside
            # rejections or still-pending jobs.
            proposal.status = ProposalStatus.PARTIALLY_APPROVED.value
        # else: only REJECTED+PENDING (no approvals yet) — keep PENDING.

        proposal.reviewed_at = now
        proposal.reviewed_by = admin_id
        await self.session.flush()
