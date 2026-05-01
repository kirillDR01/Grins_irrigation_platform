"""Public portal API endpoints (no authentication required).

Provides customer-facing endpoints for estimate review, approval/rejection,
and contract signing via secure token-based access.

Validates: CRM Gap Closure Req 16.1, 16.2, 16.3, 16.4, 78.3, 78.5, 78.6
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.dependencies import get_db_session, get_job_service
from grins_platform.exceptions import (
    EstimateAlreadyApprovedError,
    EstimateNotFoundError,
    EstimateTokenExpiredError,
)
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.middleware.rate_limit import PORTAL_LIMIT, limiter
from grins_platform.repositories.estimate_repository import EstimateRepository
from grins_platform.schemas.portal import (
    PortalApproveRequest,
    PortalEstimateResponse,
    PortalInvoiceResponse,
    PortalRejectRequest,
    PortalSignRequest,
)
from grins_platform.services.audit_service import AuditService
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService
from grins_platform.services.estimate_service import EstimateService
from grins_platform.services.job_service import (
    JobService,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.services.sales_pipeline_service import SalesPipelineService
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from grins_platform.models.estimate import Estimate
    from grins_platform.schemas.estimate import EstimateResponse

router = APIRouter(prefix="/portal")

logger = get_logger(__name__)


class PortalEndpoints(LoggerMixin):
    """Portal API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = PortalEndpoints()


# =============================================================================
# Helpers
# =============================================================================


async def _get_estimate_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> EstimateService:
    """Get EstimateService for portal endpoints.

    Wires EmailService + SMSService + SalesPipelineService so customer
    portal approve/reject triggers internal staff notifications and the
    Q-A SalesEntry breadcrumb. Mirrors the admin-side
    ``get_estimate_service`` factory in ``api/v1/dependencies.py`` so
    both code paths produce identically-configured EstimateService
    instances.

    Args:
        session: Database session from dependency injection.
        job_service: JobService dependency (required by SalesPipelineService).

    Returns:
        EstimateService instance with all dependencies wired.
    """
    from grins_platform.services.business_setting_service import (  # noqa: PLC0415
        BusinessSettingService,
    )
    from grins_platform.services.estimate_pdf_service import (  # noqa: PLC0415
        EstimatePDFService,
    )

    repo = EstimateRepository(session=session)
    email_service = EmailService()
    sms_service = SMSService(session=session, provider=get_sms_provider())
    audit_service = AuditService()
    sales_pipeline_service = SalesPipelineService(
        job_service=job_service,
        audit_service=audit_service,
    )
    business_setting_service = BusinessSettingService(session=session)
    estimate_pdf_service = EstimatePDFService()
    return EstimateService(
        estimate_repository=repo,
        portal_base_url=EmailSettings().portal_base_url,
        email_service=email_service,
        sms_service=sms_service,
        sales_pipeline_service=sales_pipeline_service,
        job_service=job_service,
        business_setting_service=business_setting_service,
        audit_service=audit_service,
        estimate_pdf_service=estimate_pdf_service,
    )


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For.

    Args:
        request: FastAPI request object.

    Returns:
        Client IP address string.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _mask_token(token: UUID) -> str:
    """Return last 8 characters of token for safe logging (Req 78.5).

    Args:
        token: Portal access token.

    Returns:
        Last 8 chars of the token string.
    """
    return str(token)[-8:]


def _to_portal_response(
    estimate: Estimate | EstimateResponse,
    *,
    force_readonly: bool = False,
) -> PortalEstimateResponse:
    """Convert an Estimate model or EstimateResponse to PortalEstimateResponse.

    Excludes all internal IDs (Req 78.6).

    Args:
        estimate: Estimate model instance or EstimateResponse schema.
        force_readonly: Override readonly to True (for approve/sign).

    Returns:
        PortalEstimateResponse with no internal IDs.
    """
    est_id = estimate.id if hasattr(estimate, "id") else None
    number = f"EST-{str(est_id)[:8].upper()}" if est_id else None

    readonly = force_readonly
    if not force_readonly:
        token_ro = getattr(estimate, "token_readonly", None)
        readonly = bool(token_ro) if token_ro is not None else False

    # Extract the status value — handle both enum and string
    raw_status = estimate.status
    if hasattr(raw_status, "value"):
        status_str = str(raw_status.value)
    else:
        status_str = str(raw_status) if raw_status else "draft"

    return PortalEstimateResponse(
        estimate_number=number,
        status=status_str,
        line_items=estimate.line_items,
        options=estimate.options,
        subtotal=estimate.subtotal,
        tax_amount=estimate.tax_amount,
        discount_amount=estimate.discount_amount,
        total=estimate.total,
        promotion_code=estimate.promotion_code,
        valid_until=estimate.valid_until,
        notes=estimate.notes,
        readonly=readonly,
    )


# =============================================================================
# GET /api/v1/portal/estimates/{token} — View estimate (Req 16.1)
# =============================================================================


@router.get(
    "/estimates/{token}",
    response_model=PortalEstimateResponse,
    summary="View estimate via portal link",
    description="Public endpoint for customers to view an estimate. "
    "No authentication required. Token must be valid and not expired.",
    responses={
        404: {"description": "Token not found"},
        410: {"description": "Token expired"},
    },
)
@limiter.limit(PORTAL_LIMIT)
async def get_portal_estimate(
    token: UUID,
    request: Request,
    service: Annotated[EstimateService, Depends(_get_estimate_service)],
) -> PortalEstimateResponse:
    """Retrieve estimate details for customer review.

    Validates: Requirements 16.1, 78.5, 78.6
    """
    _endpoints.log_started(
        "get_portal_estimate",
        token_suffix=_mask_token(token),
    )

    logger.info(
        "portal.access.attempted",
        token_suffix=_mask_token(token),
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown"),
        action="view",
    )

    try:
        estimate = await service.get_by_portal_token(token)
    except EstimateNotFoundError as exc:
        _endpoints.log_rejected(
            "get_portal_estimate",
            reason="token_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found.",
        ) from exc
    except EstimateTokenExpiredError as exc:
        _endpoints.log_rejected(
            "get_portal_estimate",
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This estimate link has expired.",
        ) from exc

    # Transition SENT → VIEWED on first portal load (idempotent).
    from grins_platform.models.enums import EstimateStatus  # noqa: PLC0415

    if estimate.status == EstimateStatus.SENT.value:
        try:
            _ = await service.repo.update(
                estimate.id,
                status=EstimateStatus.VIEWED.value,
            )
        except Exception as e:  # pragma: no cover — best-effort
            logger.warning("portal.viewed_transition.failed", error=str(e))

    response = _to_portal_response(estimate)

    _endpoints.log_completed(
        "get_portal_estimate",
        token_suffix=_mask_token(token),
    )
    return response


# =============================================================================
# POST /api/v1/portal/estimates/{token}/approve — Approve estimate (Req 16.2)
# =============================================================================


@router.post(
    "/estimates/{token}/approve",
    response_model=PortalEstimateResponse,
    summary="Approve estimate via portal",
    description="Public endpoint for customers to approve an estimate. "
    "Records approval with timestamp, IP address, and user agent.",
    responses={
        404: {"description": "Token not found"},
        409: {"description": "Estimate already decided"},
        410: {"description": "Token expired"},
    },
)
@limiter.limit(PORTAL_LIMIT)
async def approve_portal_estimate(
    token: UUID,
    request: Request,
    service: Annotated[EstimateService, Depends(_get_estimate_service)],
    body: PortalApproveRequest | None = None,
) -> PortalEstimateResponse:
    """Record customer approval of an estimate.

    Validates: Requirements 16.2, 78.4, 78.5
    """
    _endpoints.log_started(
        "approve_portal_estimate",
        token_suffix=_mask_token(token),
    )

    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    logger.info(
        "portal.access.attempted",
        token_suffix=_mask_token(token),
        ip_address=ip_address,
        user_agent=user_agent,
        action="approve",
    )

    final_ip = body.ip_address if body and body.ip_address else ip_address
    final_ua = body.user_agent if body and body.user_agent else user_agent

    try:
        result = await service.approve_via_portal(
            token=token,
            ip_address=final_ip,
            user_agent=final_ua,
        )
    except EstimateNotFoundError as exc:
        _endpoints.log_rejected(
            "approve_portal_estimate",
            reason="token_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found.",
        ) from exc
    except EstimateTokenExpiredError as exc:
        _endpoints.log_rejected(
            "approve_portal_estimate",
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This estimate link has expired.",
        ) from exc
    except EstimateAlreadyApprovedError as exc:
        _endpoints.log_rejected(
            "approve_portal_estimate",
            reason="already_decided",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This estimate has already been approved or rejected.",
        ) from exc

    response = _to_portal_response(result, force_readonly=True)

    _endpoints.log_completed(
        "approve_portal_estimate",
        token_suffix=_mask_token(token),
    )
    return response


# =============================================================================
# POST /api/v1/portal/estimates/{token}/reject — Reject estimate (Req 16.3)
# =============================================================================


@router.post(
    "/estimates/{token}/reject",
    response_model=PortalEstimateResponse,
    summary="Reject estimate via portal",
    description="Public endpoint for customers to reject an estimate. "
    "Records rejection with optional reason.",
    responses={
        404: {"description": "Token not found"},
        409: {"description": "Estimate already decided"},
        410: {"description": "Token expired"},
    },
)
@limiter.limit(PORTAL_LIMIT)
async def reject_portal_estimate(
    token: UUID,
    request: Request,
    service: Annotated[EstimateService, Depends(_get_estimate_service)],
    body: PortalRejectRequest | None = None,
) -> PortalEstimateResponse:
    """Record customer rejection of an estimate.

    Validates: Requirements 16.3, 78.5
    """
    _endpoints.log_started(
        "reject_portal_estimate",
        token_suffix=_mask_token(token),
    )

    logger.info(
        "portal.access.attempted",
        token_suffix=_mask_token(token),
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown"),
        action="reject",
    )

    reason = body.reason if body else None

    try:
        result = await service.reject_via_portal(
            token=token,
            reason=reason,
        )
    except EstimateNotFoundError as exc:
        _endpoints.log_rejected(
            "reject_portal_estimate",
            reason="token_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found.",
        ) from exc
    except EstimateTokenExpiredError as exc:
        _endpoints.log_rejected(
            "reject_portal_estimate",
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This estimate link has expired.",
        ) from exc
    except EstimateAlreadyApprovedError as exc:
        _endpoints.log_rejected(
            "reject_portal_estimate",
            reason="already_decided",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This estimate has already been approved or rejected.",
        ) from exc

    response = _to_portal_response(result, force_readonly=True)

    _endpoints.log_completed(
        "reject_portal_estimate",
        token_suffix=_mask_token(token),
    )
    return response


# =============================================================================
# POST /api/v1/portal/contracts/{token}/sign — Sign contract (Req 16.4)
# =============================================================================


@router.post(
    "/contracts/{token}/sign",
    response_model=PortalEstimateResponse,
    summary="Sign contract via portal",
    description="Public endpoint for customers to electronically sign a contract. "
    "Records signature with timestamp, IP address, and user agent.",
    responses={
        404: {"description": "Token not found"},
        409: {"description": "Contract already signed"},
        410: {"description": "Token expired"},
    },
)
async def sign_portal_contract(
    token: UUID,
    request: Request,
    body: PortalSignRequest,
    service: Annotated[EstimateService, Depends(_get_estimate_service)],
) -> PortalEstimateResponse:
    """Record customer's electronic signature on a contract.

    Validates: Requirements 16.4, 78.5
    """
    _endpoints.log_started(
        "sign_portal_contract",
        token_suffix=_mask_token(token),
    )

    ip_address = _get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")

    logger.info(
        "portal.access.attempted",
        token_suffix=_mask_token(token),
        ip_address=ip_address,
        user_agent=user_agent,
        action="sign",
    )

    final_ip = body.ip_address if body.ip_address else ip_address
    final_ua = body.user_agent if body.user_agent else user_agent

    try:
        result = await service.approve_via_portal(
            token=token,
            ip_address=final_ip,
            user_agent=final_ua,
        )
    except EstimateNotFoundError as exc:
        _endpoints.log_rejected(
            "sign_portal_contract",
            reason="token_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found.",
        ) from exc
    except EstimateTokenExpiredError as exc:
        _endpoints.log_rejected(
            "sign_portal_contract",
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This contract link has expired.",
        ) from exc
    except EstimateAlreadyApprovedError as exc:
        _endpoints.log_rejected(
            "sign_portal_contract",
            reason="already_signed",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This contract has already been signed.",
        ) from exc

    response = _to_portal_response(result, force_readonly=True)

    _endpoints.log_completed(
        "sign_portal_contract",
        token_suffix=_mask_token(token),
    )
    return response


# =============================================================================
# Invoice Portal — Req 84
# =============================================================================


@router.get(
    "/invoices/{token}",
    response_model=PortalInvoiceResponse,
    summary="View invoice (public)",
    description="Public endpoint for customers to view their invoice via token.",
    responses={
        404: {"description": "Token not found"},
        410: {"description": "Token expired"},
    },
)
async def get_portal_invoice(
    token: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PortalInvoiceResponse:
    """Get invoice by portal token.

    This endpoint is PUBLIC — no authentication required.

    Validates: CRM Gap Closure Req 84.2, 84.3
    """
    from grins_platform.services.invoice_portal_service import (  # noqa: PLC0415
        InvoicePortalService,
        InvoiceTokenExpiredError,
        InvoiceTokenNotFoundError,
    )

    _endpoints.log_started("get_portal_invoice")

    svc = InvoicePortalService()
    try:
        result = await svc.get_invoice_by_token(session, token)
    except InvoiceTokenNotFoundError as exc:
        _endpoints.log_rejected(
            "get_portal_invoice",
            reason="token_not_found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found or token invalid.",
        ) from exc
    except InvoiceTokenExpiredError as exc:
        _endpoints.log_rejected(
            "get_portal_invoice",
            reason="token_expired",
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invoice link has expired. Please contact us for assistance.",
        ) from exc
    else:
        _endpoints.log_completed("get_portal_invoice")
        return result
