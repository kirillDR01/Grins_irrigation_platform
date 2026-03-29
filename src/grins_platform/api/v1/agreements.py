"""Admin API endpoints for agreements, compliance, and dashboard extension.

Authenticated endpoints for agreement CRUD, metrics, queues,
compliance audit, and dashboard summary extension.

Validates: Requirements 19.1-19.7, 20.1-20.3, 21.1, 37.1, 38.1-38.3, 62.1
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import (
    func as sa_func,
    select as sa_select,
)
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import ManagerOrAdminUser  # noqa: TC001
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions import (
    AgreementNotFoundError,
    InvalidAgreementStatusTransitionError,
)
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import AgreementStatus, LeadStatus
from grins_platform.models.lead import Lead
from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.schemas.agreement import (
    AgreementDetailResponse,
    AgreementJobSummary,
    AgreementMetricsResponse,
    AgreementNotesUpdateRequest,
    AgreementRenewalRejectRequest,
    AgreementResponse,
    AgreementStatusLogResponse,
    AgreementStatusUpdateRequest,
    AgreementTierResponse,
    DashboardSummaryExtension,
    DisclosureRecordResponse,
    MrrDataPointResponse,
    MrrHistoryResponse,
    PaginatedAgreementResponse,
    TierDistributionItemResponse,
    TierDistributionResponse,
)
from grins_platform.services.agreement_service import AgreementService
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.metrics_service import MetricsService

if TYPE_CHECKING:
    from grins_platform.models.service_agreement import ServiceAgreement

logger = get_logger(__name__)

router = APIRouter(prefix="/agreements", tags=["agreements"])
tier_router = APIRouter(prefix="/agreement-tiers", tags=["agreement-tiers"])


class AgreementEndpoints(LoggerMixin):
    """Agreement endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = AgreementEndpoints()


# ---------------------------------------------------------------------------
# Helper: build response from model
# ---------------------------------------------------------------------------


def _agreement_to_response(agr: ServiceAgreement) -> AgreementResponse:
    """Convert a ServiceAgreement model to AgreementResponse."""
    customer_name = None
    tier_name = None
    package_type = None
    if hasattr(agr, "customer") and agr.customer:
        customer_name = agr.customer.full_name  # type: ignore[union-attr]
    if hasattr(agr, "tier") and agr.tier:
        tier_name = agr.tier.name  # type: ignore[union-attr]
        package_type = agr.tier.package_type  # type: ignore[union-attr]
    return AgreementResponse(
        id=agr.id,
        agreement_number=agr.agreement_number,
        customer_id=agr.customer_id,
        customer_name=customer_name,
        tier_id=agr.tier_id,
        tier_name=tier_name,
        package_type=package_type,
        property_id=agr.property_id,
        status=agr.status,
        annual_price=agr.annual_price,
        start_date=agr.start_date,
        end_date=agr.end_date,
        renewal_date=agr.renewal_date,
        auto_renew=agr.auto_renew,
        payment_status=agr.payment_status,
        preferred_schedule=agr.preferred_schedule,
        preferred_schedule_details=agr.preferred_schedule_details,
        created_at=agr.created_at,
    )


def _agreement_to_detail(agr: ServiceAgreement) -> AgreementDetailResponse:
    """Convert a ServiceAgreement model to AgreementDetailResponse."""
    base = _agreement_to_response(agr)
    jobs: list[AgreementJobSummary] = []
    if hasattr(agr, "jobs") and agr.jobs:
        jobs.extend(
            AgreementJobSummary(
                id=j.id,
                job_type=j.job_type,
                status=j.status,
                target_start_date=j.target_start_date,
                target_end_date=j.target_end_date,
            )
            for j in agr.jobs
        )
    status_logs: list[AgreementStatusLogResponse] = []
    if hasattr(agr, "status_logs") and agr.status_logs:
        for log in agr.status_logs:
            changed_by_name = None
            if hasattr(log, "changed_by_staff") and log.changed_by_staff:
                changed_by_name = log.changed_by_staff.name
            status_logs.append(
                AgreementStatusLogResponse(
                    id=log.id,
                    old_status=log.old_status,
                    new_status=log.new_status,
                    changed_by=log.changed_by,
                    changed_by_name=changed_by_name,
                    reason=log.reason,
                    metadata_=log.metadata_,
                    created_at=log.created_at,
                ),
            )
    return AgreementDetailResponse(
        **base.model_dump(),
        stripe_subscription_id=agr.stripe_subscription_id,
        stripe_customer_id=agr.stripe_customer_id,
        cancelled_at=agr.cancelled_at,
        cancellation_reason=agr.cancellation_reason,
        cancellation_refund_amount=agr.cancellation_refund_amount,
        pause_reason=agr.pause_reason,
        last_payment_date=agr.last_payment_date,
        last_payment_amount=agr.last_payment_amount,
        renewal_approved_by=agr.renewal_approved_by,
        renewal_approved_at=agr.renewal_approved_at,
        consent_recorded_at=agr.consent_recorded_at,
        consent_method=agr.consent_method,
        last_annual_notice_sent=agr.last_annual_notice_sent,
        last_renewal_notice_sent=agr.last_renewal_notice_sent,
        notes=agr.notes,
        jobs=jobs,
        status_logs=status_logs,
    )


# =========================================================================
# Agreement CRUD endpoints (Req 19.1-19.5)
# =========================================================================


@router.get(
    "",
    response_model=PaginatedAgreementResponse,
    summary="List agreements",
)
async def list_agreements(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = Query(None, description="Filter by status"),
    tier_id: UUID | None = Query(None, description="Filter by tier ID"),
    customer_id: UUID | None = Query(None, description="Filter by customer ID"),
    payment_status: str | None = Query(None, description="Filter by payment status"),
    expiring_soon: bool = Query(False, description="Only expiring within 30 days"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedAgreementResponse:
    """List agreements with filters and pagination.

    Validates: Requirement 19.1
    """
    _endpoints.log_started("list_agreements")
    repo = AgreementRepository(session=db)
    agreements, total = await repo.list_with_filters(
        status=status,
        tier_id=tier_id,
        customer_id=customer_id,
        payment_status=payment_status,
        expiring_soon=expiring_soon,
        page=page,
        page_size=page_size,
    )
    items = [_agreement_to_response(a) for a in agreements]
    _endpoints.log_completed("list_agreements", count=len(items), total=total)
    return PaginatedAgreementResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{agreement_id}",
    response_model=AgreementDetailResponse,
    summary="Get agreement detail",
)
async def get_agreement(
    agreement_id: UUID,
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementDetailResponse | JSONResponse:
    """Get agreement detail with customer, tier, jobs, status logs.

    Validates: Requirement 19.2
    """
    _endpoints.log_started("get_agreement", agreement_id=str(agreement_id))
    repo = AgreementRepository(session=db)
    agr = await repo.get_by_id(agreement_id)
    if not agr:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Agreement {agreement_id} not found"},
        )
    _endpoints.log_completed("get_agreement", agreement_id=str(agreement_id))
    return _agreement_to_detail(agr)


@router.patch(
    "/{agreement_id}/status",
    response_model=AgreementDetailResponse,
    summary="Update agreement status",
)
async def update_agreement_status(
    agreement_id: UUID,
    data: AgreementStatusUpdateRequest,
    current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementDetailResponse | JSONResponse:
    """Validate and update agreement status.

    Validates: Requirement 19.3
    """
    _endpoints.log_started(
        "update_agreement_status",
        agreement_id=str(agreement_id),
        new_status=data.status,
    )
    repo = AgreementRepository(session=db)
    tier_repo = AgreementTierRepository(session=db)
    service = AgreementService(agreement_repo=repo, tier_repo=tier_repo)
    try:
        new_status = AgreementStatus(data.status)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid status: {data.status}"},
        )
    try:
        await service.transition_status(
            agreement_id,
            new_status,
            actor=current_user.id,
            reason=data.reason,
        )
    except AgreementNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Agreement {agreement_id} not found"},
        )
    except InvalidAgreementStatusTransitionError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    await db.commit()
    agr = await repo.get_by_id(agreement_id)
    _endpoints.log_completed(
        "update_agreement_status",
        agreement_id=str(agreement_id),
    )
    assert agr is not None  # just committed; must exist
    return _agreement_to_detail(agr)


@router.patch(
    "/{agreement_id}/notes",
    response_model=AgreementDetailResponse,
    summary="Update agreement admin notes",
)
async def update_agreement_notes(
    agreement_id: UUID,
    data: AgreementNotesUpdateRequest,
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementDetailResponse | JSONResponse:
    """Update the admin notes field on an agreement.

    Validates: Requirement 24.5
    """
    _endpoints.log_started("update_notes", agreement_id=str(agreement_id))
    repo = AgreementRepository(session=db)
    agr = await repo.get_by_id(agreement_id)
    if agr is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Agreement {agreement_id} not found"},
        )
    agr.notes = data.notes
    await db.commit()
    agr = await repo.get_by_id(agreement_id)
    assert agr is not None
    _endpoints.log_completed("update_notes", agreement_id=str(agreement_id))
    return _agreement_to_detail(agr)


@router.post(
    "/{agreement_id}/approve-renewal",
    response_model=AgreementDetailResponse,
    summary="Approve agreement renewal",
)
async def approve_renewal(
    agreement_id: UUID,
    current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementDetailResponse | JSONResponse:
    """Record renewal approval.

    Validates: Requirement 19.4
    """
    _endpoints.log_started("approve_renewal", agreement_id=str(agreement_id))
    repo = AgreementRepository(session=db)
    tier_repo = AgreementTierRepository(session=db)
    service = AgreementService(agreement_repo=repo, tier_repo=tier_repo)
    try:
        await service.approve_renewal(agreement_id, current_user.id)
    except AgreementNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Agreement {agreement_id} not found"},
        )
    await db.commit()
    agr = await repo.get_by_id(agreement_id)
    _endpoints.log_completed("approve_renewal", agreement_id=str(agreement_id))
    assert agr is not None  # just committed; must exist
    return _agreement_to_detail(agr)


@router.post(
    "/{agreement_id}/reject-renewal",
    response_model=AgreementDetailResponse,
    summary="Reject agreement renewal",
)
async def reject_renewal(
    agreement_id: UUID,
    current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _data: AgreementRenewalRejectRequest | None = None,
) -> AgreementDetailResponse | JSONResponse:
    """Reject renewal, triggers Stripe cancel_at_period_end.

    Validates: Requirement 19.5
    """
    _endpoints.log_started("reject_renewal", agreement_id=str(agreement_id))
    repo = AgreementRepository(session=db)
    tier_repo = AgreementTierRepository(session=db)
    service = AgreementService(agreement_repo=repo, tier_repo=tier_repo)
    try:
        await service.reject_renewal(agreement_id, current_user.id)
    except AgreementNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Agreement {agreement_id} not found"},
        )
    except InvalidAgreementStatusTransitionError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    await db.commit()
    agr = await repo.get_by_id(agreement_id)
    _endpoints.log_completed("reject_renewal", agreement_id=str(agreement_id))
    assert agr is not None  # just committed; must exist
    return _agreement_to_detail(agr)


# =========================================================================
# Tier endpoints (Req 19.6, 19.7)
# =========================================================================


@tier_router.get(
    "",
    response_model=list[AgreementTierResponse],
    summary="List active tiers",
)
async def list_tiers(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AgreementTierResponse]:
    """List active agreement tiers.

    Validates: Requirement 19.6
    """
    _endpoints.log_started("list_tiers")
    repo = AgreementTierRepository(session=db)
    tiers = await repo.list_active()
    _endpoints.log_completed("list_tiers", count=len(tiers))
    return [AgreementTierResponse.model_validate(t) for t in tiers]


@tier_router.get(
    "/{tier_id}",
    response_model=AgreementTierResponse,
    summary="Get tier detail",
)
async def get_tier(
    tier_id: UUID,
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementTierResponse | JSONResponse:
    """Get tier detail.

    Validates: Requirement 19.7
    """
    _endpoints.log_started("get_tier", tier_id=str(tier_id))
    repo = AgreementTierRepository(session=db)
    tier = await repo.get_by_id(tier_id)
    if not tier:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Tier {tier_id} not found"},
        )
    _endpoints.log_completed("get_tier", tier_id=str(tier_id))
    return AgreementTierResponse.model_validate(tier)


# =========================================================================
# Metrics and queue endpoints (Req 20.1-20.3, 37.1)
# =========================================================================


@router.get(
    "/metrics/summary",
    response_model=AgreementMetricsResponse,
    summary="Get agreement metrics",
)
async def get_agreement_metrics(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AgreementMetricsResponse:
    """Get agreement business metrics: active count, MRR, ARPA, etc.

    Validates: Requirement 20.1
    """
    _endpoints.log_started("get_agreement_metrics")
    service = MetricsService(session=db)
    m = await service.compute_metrics()
    _endpoints.log_completed("get_agreement_metrics", active_count=m.active_count)
    return AgreementMetricsResponse(
        active_count=m.active_count,
        mrr=m.mrr,
        arpa=m.arpa,
        renewal_rate=m.renewal_rate,
        churn_rate=m.churn_rate,
        past_due_amount=m.past_due_amount,
    )


@router.get(
    "/metrics/mrr-history",
    response_model=MrrHistoryResponse,
    summary="Get MRR history (trailing 12 months)",
)
async def get_mrr_history(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> MrrHistoryResponse:
    """Get MRR over trailing 12 months.

    Validates: Requirement 22.3
    """
    _endpoints.log_started("get_mrr_history")
    service = MetricsService(session=db)
    history = await service.get_mrr_history()
    _endpoints.log_completed("get_mrr_history", count=len(history.data_points))
    return MrrHistoryResponse(
        data_points=[
            MrrDataPointResponse(month=dp.month, mrr=dp.mrr)
            for dp in history.data_points
        ],
    )


@router.get(
    "/metrics/tier-distribution",
    response_model=TierDistributionResponse,
    summary="Get active agreements by tier",
)
async def get_tier_distribution(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TierDistributionResponse:
    """Get active agreement counts grouped by tier.

    Validates: Requirement 22.4
    """
    _endpoints.log_started("get_tier_distribution")
    service = MetricsService(session=db)
    dist = await service.get_tier_distribution()
    _endpoints.log_completed("get_tier_distribution", count=len(dist.items))
    return TierDistributionResponse(
        items=[
            TierDistributionItemResponse(
                tier_id=item.tier_id,
                tier_name=item.tier_name,
                package_type=item.package_type,
                active_count=item.active_count,
            )
            for item in dist.items
        ],
    )


@router.get(
    "/queues/renewal-pipeline",
    response_model=list[AgreementResponse],
    summary="Get renewal pipeline",
)
async def get_renewal_pipeline(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AgreementResponse]:
    """Get PENDING_RENEWAL agreements sorted by renewal_date ASC.

    Validates: Requirement 20.2
    """
    _endpoints.log_started("get_renewal_pipeline")
    repo = AgreementRepository(session=db)
    agreements = await repo.get_renewal_pipeline()
    _endpoints.log_completed("get_renewal_pipeline", count=len(agreements))
    return [_agreement_to_response(a) for a in agreements]


@router.get(
    "/queues/failed-payments",
    response_model=list[AgreementResponse],
    summary="Get failed payments",
)
async def get_failed_payments(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AgreementResponse]:
    """Get agreements with PAST_DUE/FAILED payment_status.

    Validates: Requirement 20.3
    """
    _endpoints.log_started("get_failed_payments")
    repo = AgreementRepository(session=db)
    agreements = await repo.get_failed_payments()
    _endpoints.log_completed("get_failed_payments", count=len(agreements))
    return [_agreement_to_response(a) for a in agreements]


@router.get(
    "/queues/annual-notice-due",
    response_model=list[AgreementResponse],
    summary="Get agreements needing annual notice",
)
async def get_annual_notice_due(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AgreementResponse]:
    """Get ACTIVE agreements needing annual notice.

    Validates: Requirement 37.1
    """
    _endpoints.log_started("get_annual_notice_due")
    repo = AgreementRepository(session=db)
    agreements = await repo.get_annual_notice_due()
    _endpoints.log_completed("get_annual_notice_due", count=len(agreements))
    return [_agreement_to_response(a) for a in agreements]


# =========================================================================
# Compliance audit endpoints (Req 38.1-38.3)
# =========================================================================


@router.get(
    "/{agreement_id}/compliance",
    response_model=list[DisclosureRecordResponse],
    summary="Get compliance disclosures for agreement",
)
async def get_agreement_compliance(
    agreement_id: UUID,
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DisclosureRecordResponse]:
    """Get disclosure records for an agreement, sorted by sent_at DESC.

    Validates: Requirements 38.1, 38.2
    """
    _endpoints.log_started(
        "get_agreement_compliance",
        agreement_id=str(agreement_id),
    )
    service = ComplianceService(session=db)
    records = await service.get_disclosures_for_agreement(agreement_id)
    _endpoints.log_completed("get_agreement_compliance", count=len(records))
    return [DisclosureRecordResponse.model_validate(r) for r in records]


compliance_router = APIRouter(prefix="/compliance", tags=["compliance"])


@compliance_router.get(
    "/customer/{customer_id}",
    response_model=list[DisclosureRecordResponse],
    summary="Get compliance disclosures for customer",
)
async def get_customer_compliance(
    customer_id: UUID,
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[DisclosureRecordResponse]:
    """Get all disclosures for a customer across agreements.

    Sorted by sent_at DESC.

    Validates: Requirements 38.2, 38.3
    """
    _endpoints.log_started("get_customer_compliance", customer_id=str(customer_id))
    service = ComplianceService(session=db)
    records = await service.get_disclosures_for_customer(customer_id)
    _endpoints.log_completed("get_customer_compliance", count=len(records))
    return [DisclosureRecordResponse.model_validate(r) for r in records]


# =========================================================================
# Dashboard summary extension (Req 21.1, 62.1)
# =========================================================================

dashboard_ext_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_ext_router.get(
    "/summary",
    response_model=DashboardSummaryExtension,
    summary="Get extended dashboard summary",
)
async def get_dashboard_summary(
    _current_user: ManagerOrAdminUser,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardSummaryExtension:
    """Extended dashboard summary with agreement and lead metrics.

    Validates: Requirements 21.1, 62.1
    """
    _endpoints.log_started("get_dashboard_summary")

    metrics_service = MetricsService(session=db)
    m = await metrics_service.compute_metrics()

    agr_repo = AgreementRepository(session=db)
    renewal_pipeline = await agr_repo.get_renewal_pipeline()
    failed_payments = await agr_repo.get_failed_payments()
    failed_amount = sum(
        (a.annual_price for a in failed_payments),
        Decimal("0.00"),
    )

    lead_repo = LeadRepository(session=db)
    new_leads = await lead_repo.count_new_today()
    follow_up_count = 0
    oldest_age: float | None = None

    try:
        _fq_leads, fq_total = await lead_repo.get_follow_up_queue(
            page=1,
            page_size=1,
        )
        follow_up_count = fq_total
    except Exception:
        logger.warning("dashboard.follow_up_queue_failed")

    uncontacted = await lead_repo.count_uncontacted()
    if uncontacted > 0:
        try:
            stmt = sa_select(sa_func.min(Lead.created_at)).where(
                Lead.status == LeadStatus.NEW.value,
            )
            result = await db.execute(stmt)
            oldest_created = result.scalar()
            if oldest_created:
                now = datetime.now(timezone.utc)
                if oldest_created.tzinfo is None:
                    oldest_created = oldest_created.replace(tzinfo=timezone.utc)
                delta = now - oldest_created
                oldest_age = delta.total_seconds() / 3600.0
        except Exception:
            logger.warning("dashboard.oldest_lead_age_failed")

    _endpoints.log_completed("get_dashboard_summary")
    return DashboardSummaryExtension(
        active_agreement_count=m.active_count,
        mrr=m.mrr,
        renewal_pipeline_count=len(renewal_pipeline),
        failed_payment_count=len(failed_payments),
        failed_payment_amount=failed_amount,
        new_leads_count=new_leads,
        follow_up_queue_count=follow_up_count,
        leads_awaiting_contact_oldest_age_hours=oldest_age,
    )
