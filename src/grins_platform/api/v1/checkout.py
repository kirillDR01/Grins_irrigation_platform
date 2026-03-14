"""Checkout endpoints — public Stripe checkout session creation.

Validates: Requirements 31.1, 31.7
"""

import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.services.checkout_service import (
    CheckoutService,
    ConsentTokenExpiredError,
    ConsentTokenNotFoundError,
    TierInactiveError,
    TierNotConfiguredError,
    TierNotFoundError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/checkout", tags=["checkout"])

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (5 requests per IP per minute)
# ---------------------------------------------------------------------------
_rate_store: dict[str, list[float]] = {}
_RATE_LIMIT = 5
_RATE_WINDOW = 60.0  # seconds


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is within rate limit."""
    now = time.monotonic()
    hits = _rate_store.get(ip, [])
    hits = [t for t in hits if now - t < _RATE_WINDOW]
    if len(hits) >= _RATE_LIMIT:
        _rate_store[ip] = hits
        return False
    hits.append(now)
    _rate_store[ip] = hits
    return True


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CreateCheckoutSessionRequest(BaseModel):
    """Request body for creating a Stripe checkout session."""

    package_tier: str = Field(
        ...,
        description="Service tier slug (e.g. essential-residential)",
    )
    package_type: str = Field(..., description="Package type (residential/commercial)")
    consent_token: UUID = Field(..., description="Pre-checkout consent token")
    zone_count: int = Field(default=1, ge=1, description="Number of irrigation zones")
    has_lake_pump: bool = Field(default=False, description="Property has a lake pump")
    has_rpz_backflow: bool = Field(
        default=False,
        description="Property has RPZ/backflow device",
    )
    email_marketing_consent: bool = Field(
        default=False,
        description="Email marketing consent",
    )
    utm_params: dict[str, str] | None = Field(
        default=None,
        description="UTM tracking parameters",
    )
    success_url: str = Field(default="", description="Redirect URL on success")
    cancel_url: str = Field(default="", description="Redirect URL on cancel")


class CreateCheckoutSessionResponse(BaseModel):
    """Response with Stripe checkout URL."""

    checkout_url: str


# ---------------------------------------------------------------------------
# Endpoint handler
# ---------------------------------------------------------------------------


class CheckoutEndpoints(LoggerMixin):
    """Checkout endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = CheckoutEndpoints()


@router.post(
    "/create-session",
    response_model=CreateCheckoutSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Stripe checkout session",
    description=(
        "Public endpoint. Creates a Stripe Checkout Session for subscription "
        "purchase. Rate-limited to 5 requests per IP per minute."
    ),
)
async def create_checkout_session(
    data: CreateCheckoutSessionRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CreateCheckoutSessionResponse | JSONResponse:
    """Create a Stripe Checkout Session.

    Public, rate-limited (5/IP/min). Validates consent token and tier,
    then creates a Stripe Checkout Session.

    Validates: Requirements 31.1, 31.7
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        logger.warning("checkout.create_session.rate_limited", ip=client_ip)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    _endpoints.log_started("create_checkout_session", package_tier=data.package_tier)

    tier_repo = AgreementTierRepository(session=db)
    service = CheckoutService(session=db, tier_repo=tier_repo)

    try:
        checkout_url = await service.create_checkout_session(
            package_tier=data.package_tier,
            package_type=data.package_type,
            consent_token=data.consent_token,
            zone_count=data.zone_count,
            has_lake_pump=data.has_lake_pump,
            has_rpz_backflow=data.has_rpz_backflow,
            email_marketing_consent=data.email_marketing_consent,
            utm_params=data.utm_params,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
    except ConsentTokenNotFoundError:
        _endpoints.log_rejected(
            "create_checkout_session",
            reason="consent_token_not_found",
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Consent token not found."},
        )
    except ConsentTokenExpiredError:
        _endpoints.log_rejected(
            "create_checkout_session",
            reason="consent_token_expired",
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Consent token has expired. "
                "Please restart the consent process.",
            },
        )
    except TierNotFoundError:
        _endpoints.log_rejected("create_checkout_session", reason="tier_not_found")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Service tier not found."},
        )
    except TierInactiveError:
        _endpoints.log_rejected("create_checkout_session", reason="tier_inactive")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Service tier is not currently available."},
        )
    except TierNotConfiguredError:
        _endpoints.log_rejected("create_checkout_session", reason="tier_not_configured")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Payment processing is not configured for this tier."},
        )

    _endpoints.log_completed("create_checkout_session", checkout_url=checkout_url)
    return CreateCheckoutSessionResponse(checkout_url=checkout_url)
