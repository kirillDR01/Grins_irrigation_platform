"""Onboarding service for post-purchase property collection.

Verifies Stripe sessions and collects property details from customers
after purchase, linking properties to agreements and jobs.

Validates: Requirements 32.1, 32.2, 32.3, 32.4, 32.5, 32.6, 32.7
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any

import stripe
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.services.stripe_config import StripeSettings
from grins_platform.utils.week_alignment import align_to_week

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.agreement_repository import AgreementRepository
    from grins_platform.repositories.agreement_tier_repository import (
        AgreementTierRepository,
    )
    from grins_platform.repositories.property_repository import PropertyRepository


class OnboardingError(Exception):
    """Base error for onboarding operations."""


class SessionNotFoundError(OnboardingError):
    """Raised when Stripe session is not found or invalid."""

    def __init__(self, session_id: str) -> None:
        """Initialize with missing session ID."""
        super().__init__(f"Stripe session not found: {session_id}")
        self.session_id = session_id


class AgreementNotFoundForSessionError(OnboardingError):
    """Raised when no agreement matches the Stripe session."""

    def __init__(self, session_id: str) -> None:
        """Initialize with session ID that has no matching agreement."""
        super().__init__(f"No agreement found for session: {session_id}")
        self.session_id = session_id


class IncompleteServiceWeekPreferencesError(OnboardingError):
    """Raised when service_week_preferences doesn't cover every tier service.

    For new onboardings, the customer must make an explicit choice (a
    specific Monday or ``null`` = "No preference") for every job_type
    included in their tier. Missing keys surface as a 422 at the
    endpoint layer.
    """

    def __init__(
        self,
        expected_job_types: set[str],
        submitted_job_types: set[str],
    ) -> None:
        self.expected_job_types = expected_job_types
        self.submitted_job_types = submitted_job_types
        self.missing_job_types = expected_job_types - submitted_job_types
        super().__init__(
            "service_week_preferences incomplete: missing "
            f"{sorted(self.missing_job_types)}",
        )


def _lookup_week_preference(
    prefs: dict[str, Any],
    job_type: str,
    month_start: int | None,
) -> str | None:
    """Return the ISO Monday string for a job, trying month-qualified key first.

    Mirrors JobGenerator._resolve_dates so job_generation-time and
    onboarding-completion-time behavior stay consistent. For
    ``monthly_visit``-style jobs, the key is ``{job_type}_{month}``
    (e.g. ``monthly_visit_5``); for other service types, it's just
    ``{job_type}``.

    Returns ``None`` when the customer actively chose "No preference"
    (value is null) or when the key is absent.
    """
    candidates: list[str] = []
    if month_start is not None:
        candidates.append(f"{job_type}_{month_start}")
    candidates.append(job_type)
    for key in candidates:
        val = prefs.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def expected_job_types_for_tier(tier: Any) -> set[str]:
    """Return the set of job_type keys required in service_week_preferences.

    Mirrors the frontend's mapServicesToPickerList expansion: monthly_visit
    with frequency "5x" expands to monthly_visit_5 through monthly_visit_9.
    Other service types are used as-is.

    The set is derived from tier.included_services so future tier
    shape changes don't require code updates here.
    """
    expected: set[str] = set()
    for svc in tier.included_services or []:
        svc_type = svc.get("service_type") if isinstance(svc, dict) else None
        if not svc_type:
            continue
        if svc_type == "monthly_visit":
            for month in range(5, 10):
                expected.add(f"monthly_visit_{month}")
            continue
        expected.add(svc_type)
    return expected


@dataclass
class VerifiedSessionInfo:
    """Information extracted from a verified Stripe Checkout Session."""

    customer_name: str
    email: str
    phone: str
    billing_address: dict[str, str]
    package_tier: str
    package_type: str
    payment_status: str
    already_completed: bool = False
    stripe_customer_portal_url: str = ""
    services_included: list[str] | None = None
    services_with_types: list[dict[str, str]] | None = None

    def __post_init__(self) -> None:
        """Default list fields to empty lists."""
        if self.services_included is None:
            self.services_included = []
        if self.services_with_types is None:
            self.services_with_types = []


class OnboardingService(LoggerMixin):
    """Service for post-purchase onboarding.

    Validates: Requirements 32.1, 32.2, 32.3, 32.4, 32.5, 32.6, 32.7
    """

    DOMAIN = "onboarding"

    def __init__(
        self,
        session: AsyncSession,
        agreement_repo: AgreementRepository,
        property_repo: PropertyRepository,
        tier_repo: AgreementTierRepository | None = None,
        stripe_settings: StripeSettings | None = None,
    ) -> None:
        """Initialize with database session and repositories."""
        super().__init__()
        self.session = session
        self.agreement_repo = agreement_repo
        self.property_repo = property_repo
        self.tier_repo = tier_repo
        self.stripe_settings = stripe_settings or StripeSettings()

    async def verify_session(self, session_id: str) -> VerifiedSessionInfo:
        """Verify a Stripe Checkout Session and return customer/package info.

        Validates: Requirement 32.1
        """
        self.log_started("verify_session", session_id=session_id)

        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            checkout_session = stripe.checkout.Session.retrieve(
                session_id,
                expand=["customer"],
            )
        except stripe.InvalidRequestError as exc:
            self.log_rejected(
                "verify_session",
                reason="not_found",
                session_id=session_id,
            )
            raise SessionNotFoundError(session_id) from exc

        metadata = checkout_session.metadata or {}
        customer_details = checkout_session.customer_details
        billing_address: dict[str, str] = {}

        if customer_details and customer_details.address:
            addr = customer_details.address
            billing_address = {
                "line1": addr.line1 or "",
                "line2": addr.line2 or "",
                "city": addr.city or "",
                "state": addr.state or "",
                "postal_code": addr.postal_code or "",
                "country": addr.country or "",
            }

        # Check if onboarding already completed (property linked to agreement)
        already_completed = False
        subscription_id = checkout_session.subscription
        if subscription_id:
            agreement = await self._find_agreement_by_subscription(
                str(subscription_id),
            )
            if agreement and agreement.property_id is not None:
                already_completed = True

        # Get portal URL from settings
        portal_url = self.stripe_settings.stripe_customer_portal_url

        # Look up tier for included_services descriptions
        services_included: list[str] = []
        services_with_types: list[dict[str, str]] = []
        tier_slug = metadata.get("package_tier", "")
        pkg_type = metadata.get("package_type", "")
        if self.tier_repo and tier_slug and pkg_type:
            tier = await self.tier_repo.get_by_slug_and_type(tier_slug, pkg_type)
            if tier and tier.included_services:
                for svc in tier.included_services:
                    desc = svc.get("description", "")
                    svc_type = svc.get("service_type", "")
                    if desc:
                        services_included.append(desc)
                    if svc_type:
                        services_with_types.append(
                            {"service_type": svc_type, "description": desc},
                        )

        info = VerifiedSessionInfo(
            customer_name=(customer_details.name or "") if customer_details else "",
            email=(customer_details.email or "") if customer_details else "",
            phone=(customer_details.phone or "") if customer_details else "",
            billing_address=billing_address,
            package_tier=tier_slug,
            package_type=pkg_type,
            payment_status=(
                str(checkout_session.payment_status)
                if checkout_session.payment_status
                else ""
            ),
            already_completed=already_completed,
            stripe_customer_portal_url=portal_url,
            services_included=services_included,
            services_with_types=services_with_types,
        )

        self.log_completed("verify_session", session_id=session_id)
        return info

    async def complete_onboarding(
        self,
        session_id: str,
        *,
        service_address_same_as_billing: bool = True,
        service_address: dict[str, str] | None = None,
        zone_count: int | None = None,
        gate_code: str | None = None,
        has_dogs: bool = False,
        access_instructions: str | None = None,
        preferred_times: str = "NO_PREFERENCE",
        preferred_schedule: str = "ASAP",
        preferred_schedule_details: str | None = None,
        service_week_preferences: dict[str, str | None] | None = None,
    ) -> ServiceAgreement:
        """Complete onboarding by creating property and linking to agreement/jobs.

        Validates: Requirements 32.2, 32.3, 32.4, 32.5, 32.6, 32.7
        """
        self.log_started("complete_onboarding", session_id=session_id)

        # Retrieve Stripe session to get subscription ID
        stripe.api_key = self.stripe_settings.stripe_secret_key
        stripe.api_version = self.stripe_settings.stripe_api_version

        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
        except stripe.InvalidRequestError as exc:
            self.log_rejected(
                "complete_onboarding",
                reason="session_not_found",
                session_id=session_id,
            )
            raise SessionNotFoundError(session_id) from exc

        subscription_id = checkout_session.subscription
        if not subscription_id:
            self.log_rejected(
                "complete_onboarding",
                reason="no_subscription",
                session_id=session_id,
            )
            raise AgreementNotFoundForSessionError(session_id)

        # Find agreement by stripe_subscription_id.
        # The agreement is created by the Stripe webhook, which may still
        # be processing when the customer submits the onboarding form.
        # Retry a few times with short delays to handle this race condition.
        agreement = None
        max_attempts = 4
        for attempt in range(max_attempts):
            agreement = await self._find_agreement_by_subscription(
                str(subscription_id),
            )
            if agreement:
                break
            if attempt < max_attempts - 1:
                delay = (attempt + 1) * 2  # 2s, 4s, 6s
                self.log_started(
                    "complete_onboarding_retry",
                    attempt=attempt + 1,
                    delay_seconds=delay,
                    session_id=session_id,
                )
                await asyncio.sleep(delay)

        if not agreement:
            self.log_rejected(
                "complete_onboarding",
                reason="agreement_not_found",
                session_id=session_id,
            )
            raise AgreementNotFoundForSessionError(session_id)

        # Tier-aware completeness check for service_week_preferences.
        # The customer must have made an explicit choice (specific Monday
        # or null = "No preference") for every job_type in their tier.
        prefs = service_week_preferences or {}
        expected = expected_job_types_for_tier(agreement.tier)
        submitted = set(prefs.keys())
        if not expected.issubset(submitted):
            self.log_rejected(
                "complete_onboarding",
                reason="incomplete_service_week_preferences",
                session_id=session_id,
                missing=sorted(expected - submitted),
            )
            raise IncompleteServiceWeekPreferencesError(expected, submitted)

        # Determine address source
        if service_address_same_as_billing:
            customer_details = checkout_session.customer_details
            if customer_details and customer_details.address:
                addr = customer_details.address
                address_data: dict[str, Any] = {
                    "address": addr.line1 or "",
                    "city": addr.city or "",
                    "state": addr.state or "MN",
                    "zip_code": addr.postal_code or None,
                }
            else:
                address_data = {
                    "address": "",
                    "city": "",
                    "state": "MN",
                    "zip_code": None,
                }
        else:
            address_data = {
                "address": (service_address or {}).get("street", ""),
                "city": (service_address or {}).get("city", ""),
                "state": (service_address or {}).get("state", "MN"),
                "zip_code": (service_address or {}).get("zip", None),
            }

        # Create property
        prop = await self.property_repo.create(
            customer_id=agreement.customer_id,
            address=address_data["address"],
            city=address_data["city"],
            state=address_data["state"],
            zip_code=address_data["zip_code"],
            zone_count=zone_count,
            gate_code=gate_code,
            has_dogs=has_dogs,
            access_instructions=access_instructions,
            is_primary=True,
        )

        # Link property to agreement and persist the customer's raw
        # week-preference answers (the chosen weeks are also propagated
        # to each Job's target dates below). Live values for gate code,
        # dogs flag, access instructions, and preferred service time
        # are stored on the property and customer rows themselves and
        # are not duplicated on the agreement.
        update_data: dict[str, Any] = {
            "property_id": prop.id,
            "preferred_schedule": preferred_schedule,
            "preferred_schedule_details": preferred_schedule_details,
            "service_week_preferences": prefs,
        }
        agreement = await self.agreement_repo.update(
            agreement,
            update_data,
        )

        # Update all linked jobs with property_id AND apply the customer's
        # chosen week to each job's target date range.
        #
        # Jobs are created upstream at webhook time (before the customer
        # has selected weeks), so their target dates default to the full
        # calendar month. Now that the customer has answered, re-apply
        # the selections in-place. A `null` value means "no preference"
        # — leave the default full-month range untouched.
        for job in agreement.jobs:
            job.property_id = prop.id
            month_start = job.target_start_date.month if job.target_start_date else None
            pref_iso = _lookup_week_preference(prefs, job.job_type, month_start)
            if pref_iso:
                try:
                    chosen = date.fromisoformat(pref_iso)
                    job.target_start_date, job.target_end_date = align_to_week(
                        chosen,
                    )
                except ValueError:
                    # Malformed ISO — skip, keep default month range
                    pass
        await self.session.flush()

        # Update customer preferred_service_times
        # Reload customer — session.refresh() in agreement_repo.update()
        # expires the selectin-loaded relationship
        cust_stmt = select(Customer).where(Customer.id == agreement.customer_id)
        cust_result = await self.session.execute(cust_stmt)
        customer = cust_result.scalar_one_or_none()
        if customer:
            customer.preferred_service_times = {"preference": preferred_times}
            await self.session.flush()

        self.log_completed(
            "complete_onboarding",
            agreement_id=str(agreement.id),
            property_id=str(prop.id),
        )
        return agreement

    async def _find_agreement_by_subscription(
        self,
        subscription_id: str,
    ) -> ServiceAgreement | None:
        """Find agreement by Stripe subscription ID."""
        stmt = (
            select(ServiceAgreement)
            .options(
                selectinload(ServiceAgreement.customer),
                selectinload(ServiceAgreement.jobs),
                selectinload(ServiceAgreement.property),
            )
            .where(ServiceAgreement.stripe_subscription_id == subscription_id)
        )
        result = await self.session.execute(stmt)
        agreement: ServiceAgreement | None = result.scalar_one_or_none()
        return agreement
