"""Stripe Terminal API endpoints for tap-to-pay integration.

Validates: Requirements 16.2, 16.6, 16.7
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.services.stripe_config import StripeSettings
from grins_platform.services.stripe_terminal import (
    StripeTerminalError,
    StripeTerminalService,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/stripe/terminal", tags=["stripe-terminal"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ConnectionTokenResponse(BaseModel):
    """Response containing a Stripe Terminal connection token."""

    secret: str = Field(..., description="Connection token secret for the Terminal SDK")


class CreatePaymentIntentRequest(BaseModel):
    """Request body for creating a PaymentIntent for tap-to-pay."""

    amount_cents: int = Field(
        ...,
        gt=0,
        description="Amount in cents (e.g. 5000 for $50.00)",
    )
    currency: str = Field(
        default="usd",
        description="Three-letter ISO currency code",
    )
    description: str = Field(
        default="",
        description="Optional description for the payment",
    )


class PaymentIntentResponse(BaseModel):
    """Response containing PaymentIntent details."""

    id: str = Field(..., description="PaymentIntent ID")
    client_secret: str = Field(
        ...,
        description="Client secret for the Terminal SDK",
    )
    amount: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="PaymentIntent status")


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def _get_stripe_terminal_service() -> StripeTerminalService:
    """Create a StripeTerminalService instance."""
    settings = StripeSettings()
    return StripeTerminalService(stripe_settings=settings)


# ---------------------------------------------------------------------------
# Endpoint handler
# ---------------------------------------------------------------------------


class StripeTerminalEndpoints(LoggerMixin):
    """Stripe Terminal endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = StripeTerminalEndpoints()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/connection-token",
    response_model=ConnectionTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Stripe Terminal connection token",
    description="Returns a connection token for the Stripe Terminal JavaScript SDK. Requires authentication.",
)
async def create_connection_token(
    _current_user: CurrentActiveUser,
    service: Annotated[
        StripeTerminalService, Depends(_get_stripe_terminal_service)
    ],
) -> ConnectionTokenResponse | JSONResponse:
    """Create a Stripe Terminal connection token.

    Validates: Requirement 16.6
    """
    _endpoints.log_started("create_connection_token")

    try:
        secret = service.create_connection_token()
        _endpoints.log_completed("create_connection_token")
        return ConnectionTokenResponse(secret=secret)
    except StripeTerminalError as e:
        _endpoints.log_failed("create_connection_token", error=e)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"Stripe Terminal error: {e.message}"},
        )


@router.post(
    "/create-payment-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_200_OK,
    summary="Create PaymentIntent for tap-to-pay",
    description="Creates a Stripe PaymentIntent with card_present payment method type for in-person collection. Requires authentication.",
)
async def create_payment_intent(
    data: CreatePaymentIntentRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[
        StripeTerminalService, Depends(_get_stripe_terminal_service)
    ],
) -> PaymentIntentResponse | JSONResponse:
    """Create a PaymentIntent for tap-to-pay collection.

    Validates: Requirements 16.2, 16.7
    """
    _endpoints.log_started(
        "create_payment_intent",
        amount_cents=data.amount_cents,
        currency=data.currency,
    )

    try:
        intent = service.create_payment_intent(
            amount_cents=data.amount_cents,
            currency=data.currency,
            description=data.description,
        )
        _endpoints.log_completed(
            "create_payment_intent",
            payment_intent_id=intent.id,
        )
        return PaymentIntentResponse(
            id=intent.id,
            client_secret=intent.client_secret or "",
            amount=intent.amount or 0,
            currency=intent.currency or "usd",
            status=intent.status or "requires_payment_method",
        )
    except StripeTerminalError as e:
        _endpoints.log_failed("create_payment_intent", error=e)
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": f"Stripe Terminal error: {e.message}"},
        )
