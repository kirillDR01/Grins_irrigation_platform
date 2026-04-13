"""Contract renewal proposal API endpoints.

Validates: CRM Changes Update 2 Req 31.5, 31.6, 31.7, 31.8, 31.9, 31.10, 31.11
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.auth_dependencies import CurrentActiveUser
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import ProposalStatus
from grins_platform.schemas.contract_renewal import (
    ProposedJobModification,
    ProposedJobResponse,
    RenewalProposalResponse,
)
from grins_platform.services.contract_renewal_service import (
    ContractRenewalReviewService,
)

router = APIRouter(
    prefix="/contract-renewals",
    tags=["contract-renewals"],
)


class _Endpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _Endpoints()


@router.get(
    "",
    response_model=list[RenewalProposalResponse],
    summary="List pending renewal proposals",
)
async def list_proposals(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by proposal status",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[RenewalProposalResponse]:
    """List contract renewal proposals. Defaults to pending.

    Validates: Req 31.5
    """
    _ep.log_started("list_proposals", status_filter=status_filter)

    from sqlalchemy import select  # noqa: PLC0415

    from grins_platform.models.contract_renewal import (  # noqa: PLC0415
        ContractRenewalProposal,
    )

    query = select(ContractRenewalProposal)
    if status_filter:
        query = query.where(ContractRenewalProposal.status == status_filter)
    else:
        query = query.where(
            ContractRenewalProposal.status == ProposalStatus.PENDING.value,
        )
    query = (
        query.order_by(ContractRenewalProposal.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(query)
    proposals = list(result.scalars().all())

    _ep.log_completed("list_proposals", count=len(proposals))
    return [RenewalProposalResponse.model_validate(p) for p in proposals]


@router.get(
    "/{proposal_id}",
    response_model=RenewalProposalResponse,
    summary="Get proposal detail with proposed jobs",
)
async def get_proposal(
    proposal_id: UUID,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RenewalProposalResponse:
    """Get a single renewal proposal with its proposed jobs.

    Validates: Req 31.5
    """
    _ep.log_started("get_proposal", proposal_id=str(proposal_id))
    svc = ContractRenewalReviewService(session)
    try:
        proposal = await svc._load_proposal(proposal_id)  # noqa: SLF001
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        ) from None

    _ep.log_completed("get_proposal", proposal_id=str(proposal_id))
    resp: RenewalProposalResponse = RenewalProposalResponse.model_validate(proposal)
    return resp


@router.post(
    "/{proposal_id}/approve-all",
    response_model=RenewalProposalResponse,
    summary="Bulk approve all proposed jobs",
)
async def approve_all(
    proposal_id: UUID,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RenewalProposalResponse:
    """Approve all proposed jobs and create real Job records.

    Validates: Req 31.6
    """
    _ep.log_started("approve_all", proposal_id=str(proposal_id))
    svc = ContractRenewalReviewService(session)
    try:
        proposal = await svc.approve_all(proposal_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        ) from None
    await session.commit()

    _ep.log_completed("approve_all", proposal_id=str(proposal_id))
    resp: RenewalProposalResponse = RenewalProposalResponse.model_validate(proposal)
    return resp


@router.post(
    "/{proposal_id}/reject-all",
    response_model=RenewalProposalResponse,
    summary="Bulk reject all proposed jobs",
)
async def reject_all(
    proposal_id: UUID,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RenewalProposalResponse:
    """Reject all proposed jobs. No Job records created.

    Validates: Req 31.10
    """
    _ep.log_started("reject_all", proposal_id=str(proposal_id))
    svc = ContractRenewalReviewService(session)
    try:
        proposal = await svc.reject_all(proposal_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        ) from None
    await session.commit()

    _ep.log_completed("reject_all", proposal_id=str(proposal_id))
    resp: RenewalProposalResponse = RenewalProposalResponse.model_validate(proposal)
    return resp


@router.post(
    "/{proposal_id}/jobs/{job_id}/approve",
    response_model=ProposedJobResponse,
    summary="Approve a single proposed job",
)
async def approve_job(
    proposal_id: UUID,  # noqa: ARG001 - kept for URL consistency
    job_id: UUID,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    modifications: ProposedJobModification | None = None,
) -> ProposedJobResponse:
    """Approve one proposed job with optional Week Of / notes modification.

    Validates: Req 31.7, 31.8, 31.9
    """
    _ep.log_started("approve_job", proposed_job_id=str(job_id))
    svc = ContractRenewalReviewService(session)
    try:
        pj = await svc.approve_job(job_id, current_user.id, modifications)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposed job {job_id} not found",
        ) from None
    await session.commit()

    _ep.log_completed("approve_job", proposed_job_id=str(job_id))
    resp: ProposedJobResponse = ProposedJobResponse.model_validate(pj)
    return resp


@router.post(
    "/{proposal_id}/jobs/{job_id}/reject",
    response_model=ProposedJobResponse,
    summary="Reject a single proposed job",
)
async def reject_job(
    proposal_id: UUID,  # noqa: ARG001 - kept for URL consistency
    job_id: UUID,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProposedJobResponse:
    """Reject one proposed job.

    Validates: Req 31.7, 31.11
    """
    _ep.log_started("reject_job", proposed_job_id=str(job_id))
    svc = ContractRenewalReviewService(session)
    try:
        pj = await svc.reject_job(job_id, current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposed job {job_id} not found",
        ) from None
    await session.commit()

    _ep.log_completed("reject_job", proposed_job_id=str(job_id))
    resp: ProposedJobResponse = ProposedJobResponse.model_validate(pj)
    return resp


@router.put(
    "/{proposal_id}/jobs/{job_id}",
    response_model=ProposedJobResponse,
    summary="Modify a proposed job (Week Of, admin_notes)",
)
async def modify_proposed_job(
    proposal_id: UUID,  # noqa: ARG001 - kept for URL consistency
    job_id: UUID,
    modifications: ProposedJobModification,
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProposedJobResponse:
    """Modify a proposed job's dates or admin notes without approving.

    Validates: Req 31.9
    """
    _ep.log_started("modify_proposed_job", proposed_job_id=str(job_id))

    from sqlalchemy import select as sa_select  # noqa: PLC0415

    from grins_platform.models.contract_renewal import (  # noqa: PLC0415
        ContractRenewalProposedJob,
    )

    result = await session.execute(
        sa_select(ContractRenewalProposedJob).where(
            ContractRenewalProposedJob.id == job_id,
        ),
    )
    pj = result.scalar_one_or_none()
    if not pj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposed job {job_id} not found",
        )

    if modifications.target_start_date is not None:
        pj.target_start_date = modifications.target_start_date
    if modifications.target_end_date is not None:
        pj.target_end_date = modifications.target_end_date
    if modifications.admin_notes is not None:
        pj.admin_notes = modifications.admin_notes

    await session.commit()
    await session.refresh(pj)

    _ep.log_completed("modify_proposed_job", proposed_job_id=str(job_id))
    resp: ProposedJobResponse = ProposedJobResponse.model_validate(pj)
    return resp


__all__ = ["router"]
