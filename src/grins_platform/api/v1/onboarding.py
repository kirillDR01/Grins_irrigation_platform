"""Onboarding endpoints — pre-checkout consent, session verification, completion.

Validates: Requirements 30.1, 30.2, 30.3, 30.4, 30.5, 32.1, 32.2
"""

import time
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.exceptions import ConsentValidationError
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.onboarding_service import (
    AgreementNotFoundForSessionError,
    IncompleteServiceWeekPreferencesError,
    OnboardingService,
    SessionNotFoundError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

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

_DEFAULT_CONSENT_LANGUAGE = (
    "I agree to receive SMS messages from Grin's Irrigations regarding "
    "my service agreement, appointments, and account updates."
)

_DEFAULT_DISCLOSURE_CONTENT = (
    "Pre-sale disclosure: By proceeding, you acknowledge the terms of "
    "service and consent to SMS communications from Grin's Irrigations."
)


class PreCheckoutConsentRequest(BaseModel):
    """Request body for pre-checkout consent."""

    sms_consent: bool = Field(..., description="SMS consent given")
    terms_accepted: bool = Field(..., description="Terms of service accepted")
    phone: str = Field(..., min_length=1, description="Phone number")
    consent_language: str = Field(
        default=_DEFAULT_CONSENT_LANGUAGE,
        description="Consent language shown to user",
    )
    disclosure_content: str = Field(
        default=_DEFAULT_DISCLOSURE_CONTENT,
        description="Disclosure content shown to user",
    )
    email_marketing_consent: bool = Field(
        default=False,
        description="Email marketing consent",
    )


class PreCheckoutConsentResponse(BaseModel):
    """Response with consent token."""

    consent_token: UUID


class VerifySessionResponse(BaseModel):
    """Response from session verification."""

    customer_name: str
    email: str
    phone: str
    billing_address: dict[str, str]
    package_tier: str
    package_type: str
    payment_status: str
    already_completed: bool = False
    stripe_customer_portal_url: str = ""
    services_included: list[str] = []
    services_with_types: list[dict[str, str]] = []


class CompleteOnboardingRequest(BaseModel):
    """Request body for completing onboarding."""

    session_id: str = Field(..., description="Stripe Checkout Session ID")
    service_address_same_as_billing: bool = Field(
        default=True,
        description="Use billing address as service address",
    )
    service_address: dict[str, str] | None = Field(
        default=None,
        description="Service address if different from billing",
    )
    zone_count: int | None = Field(default=None, description="Number of zones")
    gate_code: str | None = Field(default=None, description="Gate code")
    has_dogs: bool = Field(default=False, description="Property has dogs")
    access_instructions: str | None = Field(
        default=None,
        description="Access instructions",
    )
    preferred_times: str = Field(
        default="NO_PREFERENCE",
        description="Preferred service times",
    )
    preferred_schedule: str = Field(
        default="ASAP",
        description="When customer wants service done",
    )
    preferred_schedule_details: str | None = Field(
        default=None,
        description="Free-text details for 'Other' schedule preference",
    )
    service_week_preferences: dict[str, str | None] = Field(
        ...,
        description=(
            "Per-service week selections as {job_type: ISO Monday date | null}."
            " Every service included in the customer's tier must appear as a"
            " key. null value means the customer explicitly chose 'No"
            " preference' for that service."
        ),
    )

    @field_validator("service_week_preferences")
    @classmethod
    def validate_week_preference_values(
        cls,
        v: dict[str, str | None],
    ) -> dict[str, str | None]:
        """Ensure non-null values are ISO date strings (YYYY-MM-DD).

        Tier-level completeness (all expected job_types present) is
        enforced in the service layer, where the tier is resolved from
        the session's agreement.
        """
        for job_type, iso in v.items():
            if iso is None:
                continue
            if not isinstance(iso, str):
                msg = (
                    f"service_week_preferences[{job_type!r}] must be null or"
                    " a YYYY-MM-DD date string"
                )
                raise ValueError(msg)
            try:
                date.fromisoformat(iso)
            except ValueError as exc:
                msg = (
                    f"service_week_preferences[{job_type!r}] is not a valid"
                    f" ISO date: {iso!r}"
                )
                raise ValueError(msg) from exc
        return v

    @model_validator(mode="after")
    def validate_preferred_schedule(self) -> "CompleteOnboardingRequest":
        """Validate preferred_schedule enum and require details for OTHER."""
        valid = {"ASAP", "ONE_TWO_WEEKS", "THREE_FOUR_WEEKS", "OTHER"}
        if self.preferred_schedule not in valid:
            msg = f"preferred_schedule must be one of {sorted(valid)}"
            raise ValueError(msg)
        if self.preferred_schedule == "OTHER" and (
            not self.preferred_schedule_details
            or not self.preferred_schedule_details.strip()
        ):
            msg = (
                "preferred_schedule_details is required"
                " when preferred_schedule is 'OTHER'"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_service_address(self) -> "CompleteOnboardingRequest":
        """Require service address fields when not using billing address."""
        if not self.service_address_same_as_billing:
            addr = self.service_address or {}
            missing = [
                f
                for f in ("street", "city", "state", "zip")
                if not addr.get(f, "").strip()
            ]
            if missing:
                msg = (
                    "Service address fields required when not using "
                    f"billing address: {', '.join(missing)}"
                )
                raise ValueError(msg)
        return self


class CompleteOnboardingResponse(BaseModel):
    """Response from completing onboarding."""

    agreement_id: str
    property_id: str | None


# ---------------------------------------------------------------------------
# Endpoint handler
# ---------------------------------------------------------------------------


class OnboardingEndpoints(LoggerMixin):
    """Onboarding endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = OnboardingEndpoints()


def _build_onboarding_service(db: AsyncSession) -> OnboardingService:
    """Build OnboardingService with required repositories."""
    return OnboardingService(
        session=db,
        agreement_repo=AgreementRepository(session=db),
        property_repo=PropertyRepository(session=db),
        tier_repo=AgreementTierRepository(session=db),
    )


@router.post(
    "/pre-checkout-consent",
    response_model=PreCheckoutConsentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit pre-checkout consent",
    description=(
        "Public endpoint. Validates sms_consent and terms_accepted, "
        "creates consent and disclosure records, returns consent_token."
    ),
)
async def pre_checkout_consent(
    data: PreCheckoutConsentRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> PreCheckoutConsentResponse | JSONResponse:
    """Process pre-checkout consent.

    Public, rate-limited (5/IP/min). Returns HTTP 422 if consent
    fields are not both true.

    Validates: Requirements 30.1, 30.2, 30.3, 30.4, 30.5
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        logger.warning("onboarding.pre_checkout_consent.rate_limited", ip=client_ip)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    _endpoints.log_started("pre_checkout_consent")

    compliance = ComplianceService(session=db)

    try:
        (
            consent_token,
            _sms_record,
            _disclosure_record,
        ) = await compliance.process_pre_checkout_consent(
            sms_consent=data.sms_consent,
            terms_accepted=data.terms_accepted,
            consent_language=data.consent_language,
            disclosure_content=data.disclosure_content,
            phone=data.phone,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            email_marketing_consent=data.email_marketing_consent,
        )
    except ConsentValidationError as exc:
        _endpoints.log_rejected(
            "pre_checkout_consent",
            reason="consent_validation_failed",
            missing_fields=str(exc.missing_fields),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": str(exc),
                "missing_fields": exc.missing_fields,
            },
        )

    await db.commit()

    _endpoints.log_completed(
        "pre_checkout_consent",
        consent_token=str(consent_token),
    )
    return PreCheckoutConsentResponse(consent_token=consent_token)


@router.get(
    "/verify-session",
    response_model=VerifySessionResponse,
    summary="Verify Stripe checkout session",
    description=(
        "Public endpoint. Verifies a Stripe session and returns customer/package info."
    ),
)
async def verify_session(
    session_id: Annotated[str, Query(description="Stripe Checkout Session ID")],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> VerifySessionResponse | JSONResponse:
    """Verify a Stripe Checkout Session.

    Public. Returns HTTP 404 if session not found.

    Validates: Requirement 32.1
    """
    _endpoints.log_started("verify_session", session_id=session_id)

    service = _build_onboarding_service(db)

    try:
        info = await service.verify_session(session_id)
    except SessionNotFoundError:
        _endpoints.log_rejected(
            "verify_session",
            reason="session_not_found",
            session_id=session_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Stripe session not found."},
        )

    _endpoints.log_completed("verify_session", session_id=session_id)
    return VerifySessionResponse(
        customer_name=info.customer_name,
        email=info.email,
        phone=info.phone,
        billing_address=info.billing_address,
        package_tier=info.package_tier,
        package_type=info.package_type,
        payment_status=info.payment_status,
        already_completed=info.already_completed,
        stripe_customer_portal_url=info.stripe_customer_portal_url,
        services_included=info.services_included,
        services_with_types=info.services_with_types,
    )


@router.post(
    "/complete",
    response_model=CompleteOnboardingResponse,
    summary="Complete onboarding with property details",
    description=(
        "Public, rate-limited. Collects property details and links to agreement."
    ),
)
async def complete_onboarding(
    data: CompleteOnboardingRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> CompleteOnboardingResponse | JSONResponse:
    """Complete onboarding by creating property and linking to agreement/jobs.

    Public, rate-limited (5/IP/min). Returns HTTP 404 if agreement not found.

    Validates: Requirements 32.2, 32.3, 32.4, 32.5, 32.6, 32.7
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(client_ip):
        logger.warning("onboarding.complete.rate_limited", ip=client_ip)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Try again later."},
        )

    _endpoints.log_started("complete_onboarding", session_id=data.session_id)

    service = _build_onboarding_service(db)

    try:
        agreement = await service.complete_onboarding(
            session_id=data.session_id,
            service_address_same_as_billing=data.service_address_same_as_billing,
            service_address=data.service_address,
            zone_count=data.zone_count,
            gate_code=data.gate_code,
            has_dogs=data.has_dogs,
            access_instructions=data.access_instructions,
            preferred_times=data.preferred_times,
            preferred_schedule=data.preferred_schedule,
            preferred_schedule_details=data.preferred_schedule_details,
            service_week_preferences=data.service_week_preferences,
        )
    except SessionNotFoundError:
        _endpoints.log_rejected(
            "complete_onboarding",
            reason="session_not_found",
            session_id=data.session_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Stripe session not found."},
        )
    except AgreementNotFoundForSessionError:
        _endpoints.log_rejected(
            "complete_onboarding",
            reason="agreement_not_found",
            session_id=data.session_id,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "No agreement found for this session."},
        )
    except IncompleteServiceWeekPreferencesError as exc:
        _endpoints.log_rejected(
            "complete_onboarding",
            reason="incomplete_service_week_preferences",
            session_id=data.session_id,
            missing=str(exc.missing_job_types),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": (
                    "service_week_preferences is missing required services"
                    " for this tier."
                ),
                "missing_job_types": sorted(exc.missing_job_types),
                "expected_job_types": sorted(exc.expected_job_types),
            },
        )

    await db.commit()

    _endpoints.log_completed(
        "complete_onboarding",
        agreement_id=str(agreement.id),
    )
    return CompleteOnboardingResponse(
        agreement_id=str(agreement.id),
        property_id=str(agreement.property_id) if agreement.property_id else None,
    )
