"""Stripe webhook endpoint.

Receives and routes Stripe webhook events with signature verification
and idempotent processing.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3,
8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 28.2, 34.1, 34.2, 34.3, 39B.3,
39C.1, 39C.2, 68.2
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select

from grins_platform.database import get_db_session as get_db
from grins_platform.exceptions import DuplicateCustomerError
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import (
    VALID_AGREEMENT_STATUS_TRANSITIONS,
    AgreementPaymentStatus,
    AgreementStatus,
    DisclosureType,
)
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.stripe_webhook_event_repository import (
    StripeWebhookEventRepository,
)
from grins_platform.schemas.customer import CustomerCreate, normalize_phone
from grins_platform.services.agreement_service import AgreementService
from grins_platform.services.ai.security import validate_twilio_signature
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.contract_renewal_service import (
    ContractRenewalReviewService,
)
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.email_service import EmailService
from grins_platform.services.job_generator import JobGenerator
from grins_platform.services.sms_service import SMSService
from grins_platform.services.stripe_config import StripeSettings
from grins_platform.services.surcharge_calculator import SurchargeCalculator

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Event types we handle
HANDLED_EVENT_TYPES = frozenset(
    {
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.upcoming",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        # Architecture C — Stripe Payment Links (plan §Phase 2.9-2.13)
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "payment_intent.canceled",
        "charge.refunded",
        "charge.dispute.created",
    },
)

# Sentinel for missing last_name in checkout.session.completed.
# Stripe's Checkout name field is a single string; mononyms ("Madonna")
# and first-name-only inputs ("Kirill") have no last name to extract.
# Using a non-empty placeholder lets CustomerCreate (min_length=1) succeed
# without rolling back the entire agreement transaction.
_MISSING_LAST_NAME_PLACEHOLDER = "-"


class StripeWebhookHandler(LoggerMixin):
    """Handles incoming Stripe webhook events.

    Validates: Requirements 6.1-6.7, 7.2, 7.3, 8.1-8.7
    """

    DOMAIN = "stripe"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session
        self.repo = StripeWebhookEventRepository(session)

    async def handle_event(self, event: stripe.Event) -> dict[str, str]:
        """Process a verified Stripe event with idempotency.

        Args:
            event: Verified Stripe event object.

        Returns:
            Dict with processing status.
        """
        event_id: str = event["id"]
        event_type: str = event["type"]

        # Deduplicate: check if already processed
        existing = await self.repo.get_by_stripe_event_id(event_id)
        if existing is not None:
            self.log_completed(
                "webhook_deduplicate",
                stripe_event_id=event_id,
                event_type=event_type,
            )
            return {"status": "already_processed"}

        # Create event record
        event_record = await self.repo.create_event_record(
            stripe_event_id=event_id,
            event_type=event_type,
            event_data=dict(event),
            processing_status="pending",
        )

        # Route to handler
        try:
            await self._route_event(event_type, event)
            await self.repo.mark_processed(event_record)
            self.log_completed(
                f"webhook_{event_type.replace('.', '_')}",
                stripe_event_id=event_id,
            )
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            # Re-create event record after rollback (original was rolled back)
            failed_record = await self.repo.create_event_record(
                stripe_event_id=event_id,
                event_type=event_type,
                event_data=dict(event),
                processing_status="failed",
            )
            failed_record.error_message = str(e)
            failed_record.processed_at = datetime.now(timezone.utc)
            self.log_failed(
                f"webhook_{event_type.replace('.', '_')}",
                error=e,
                stripe_event_id=event_id,
            )
            await self.session.commit()
            return {"status": "failed", "error": str(e)}
        else:
            return {"status": "processed"}

    async def _route_event(
        self,
        event_type: str,
        event: stripe.Event,
    ) -> None:
        """Route event to the appropriate handler.

        Args:
            event_type: Stripe event type string.
            event: The full Stripe event.
        """
        handlers: dict[str, Any] = {
            "checkout.session.completed": self._handle_checkout_completed,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "invoice.upcoming": self._handle_invoice_upcoming,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            # Architecture C — Payment Links handlers (plan §Phase 2.10-2.13)
            "payment_intent.succeeded": self._handle_payment_intent_succeeded,
            "payment_intent.payment_failed": (
                self._handle_payment_intent_payment_failed
            ),
            "payment_intent.canceled": self._handle_payment_intent_canceled,
            "charge.refunded": self._handle_charge_refunded,
            "charge.dispute.created": self._handle_charge_dispute_created,
        }
        handler = handlers.get(event_type)
        if handler is not None:
            await handler(event)
        else:
            self.log_started(
                "webhook_unhandled",
                event_type=event_type,
                stripe_event_id=event["id"],
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_subscription_id(obj: dict[str, Any]) -> str:
        """Extract subscription ID from a Stripe invoice or session object.

        Handles three formats:
        1. Legacy: obj["subscription"] is a string ID
        2. Expanded object: obj["subscription"] is a dict with "id"
        3. New (2025-03-31+): obj["parent"]["subscription_details"]["subscription"]

        Returns:
            Subscription ID string, or empty string if not found.
        """
        # 1. Legacy string field
        sub = obj.get("subscription")
        if isinstance(sub, str) and sub:
            return sub
        # 2. Expanded object
        if isinstance(sub, dict):
            sub_id = sub.get("id", "")
            if sub_id:
                return str(sub_id)
        # 3. New parent.subscription_details.subscription path
        parent = obj.get("parent")
        if isinstance(parent, dict):
            sub_details = parent.get("subscription_details")
            if isinstance(sub_details, dict):
                nested_sub = sub_details.get("subscription", "")
                if isinstance(nested_sub, str) and nested_sub:
                    return nested_sub
                if isinstance(nested_sub, dict):
                    return str(nested_sub.get("id", ""))
        return ""

    # ------------------------------------------------------------------
    # checkout.session.completed handler
    # Validates: Requirements 8.1-8.7, 28.2, 34.1-34.3, 39B.3,
    # 39C.1, 39C.2, 68.2
    # ------------------------------------------------------------------

    async def _handle_checkout_completed(self, event: stripe.Event) -> None:
        """Handle checkout.session.completed event.

        Creates or matches customer, creates agreement with PENDING status,
        generates seasonal jobs, links orphaned consent records, creates
        compliance disclosures, and sends welcome + confirmation emails.

        Validates: Requirements 8.1-8.7, 28.2, 34.1-34.3, 39B.3,
        39C.1, 39C.2, 68.2
        """
        self.log_started(
            "webhook_checkout_completed",
            stripe_event_id=event["id"],
        )

        session_obj = event["data"]["object"]
        customer_email: str = (
            session_obj.get("customer_details", {}).get("email", "")
            or session_obj.get("customer_email", "")
            or ""
        )
        stripe_customer_id: str = session_obj.get("customer", "") or ""
        subscription_id: str = session_obj.get("subscription", "") or ""
        metadata: dict[str, str] = session_obj.get("metadata", {}) or {}

        consent_token_str = metadata.get("consent_token", "")
        tier_slug = metadata.get("package_tier", "")
        package_type = metadata.get("package_type", "residential")

        # Extract surcharge and consent metadata (Req 3.14, 2.5)
        meta_zone_count = int(metadata.get("zone_count", "1") or "1")
        meta_has_lake_pump = metadata.get("has_lake_pump", "false").lower() == "true"
        meta_has_rpz_backflow = (
            metadata.get("has_rpz_backflow", "false").lower() == "true"
        )
        meta_email_marketing_consent = (
            metadata.get("email_marketing_consent", "false").lower() == "true"
        )

        # Build services
        customer_repo = CustomerRepository(self.session)
        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        compliance_svc = ComplianceService(self.session)
        email_svc = EmailService()
        job_gen = JobGenerator(self.session)

        # 1. Find or create customer by email, then phone (Req 8.1, 8.2, 8.3)
        customer = None
        if customer_email:
            existing = await customer_repo.find_by_email(customer_email)
            if existing:
                customer = existing[0]

        now = datetime.now(timezone.utc)

        if customer is None:
            # Extract name and phone from session
            cust_details: dict[str, Any] = session_obj.get("customer_details", {}) or {}
            full_name = str(cust_details.get("name", "") or "")
            parts = full_name.strip().split(maxsplit=1)
            first_name = parts[0] if parts else "Customer"
            last_name = parts[1] if len(parts) > 1 else _MISSING_LAST_NAME_PLACEHOLDER
            if last_name == _MISSING_LAST_NAME_PLACEHOLDER:
                self.log_started(
                    "webhook_customer_placeholder_last_name",
                    full_name_provided=bool(full_name),
                    first_name=first_name,
                )
            phone_raw = str(cust_details.get("phone", "") or "")

            # Normalize phone and try phone-based lookup before creating
            normalized_phone = ""
            if phone_raw:
                try:
                    normalized_phone = normalize_phone(phone_raw)
                    existing_by_phone = await customer_repo.find_by_phone(
                        normalized_phone,
                    )
                    if existing_by_phone:
                        customer = existing_by_phone
                        self.log_started(
                            "webhook_customer_matched_by_phone",
                            customer_id=str(customer.id),
                        )
                        # Update email if customer doesn't have one
                        if customer_email and not customer.email:
                            customer.email = customer_email  # type: ignore[assignment]
                except ValueError:
                    self.log_started(
                        "webhook_phone_normalize_failed",
                        phone_raw=phone_raw[-4:] if phone_raw else "",
                    )

            if customer is None:
                create_data = CustomerCreate(
                    first_name=first_name,
                    last_name=last_name,
                    phone=normalized_phone or phone_raw or f"000{event['id'][-7:]}",
                    email=customer_email or None,
                )
                try:
                    cust_svc = CustomerService(customer_repo)
                    cust_resp = await cust_svc.create_customer(create_data)
                    customer = await customer_repo.get_by_id(cust_resp.id)
                    assert customer is not None
                except DuplicateCustomerError:
                    # Race condition safety net
                    self.log_started(
                        "webhook_customer_duplicate_fallback",
                        phone=normalized_phone[-4:] if normalized_phone else "unknown",
                    )
                    customer = await customer_repo.find_by_phone(
                        normalized_phone or phone_raw,
                    )
                    if customer is None:
                        raise

        # Update stripe_customer_id (Req 8.3, 28.2)
        if stripe_customer_id and customer.stripe_customer_id != stripe_customer_id:
            customer.stripe_customer_id = stripe_customer_id  # type: ignore[assignment]

        # Track that customer went through Stripe checkout (Req 68.2)
        # Note: email_opt_in is set below based on actual metadata consent
        if not customer.email_opt_in_at:
            customer.email_opt_in_at = now  # type: ignore[assignment]
            customer.email_opt_in_source = "stripe_checkout"  # type: ignore[assignment]

        await self.session.flush()

        # 2. Resolve tier (Req 8.4)
        tier = None
        if tier_slug:
            tier = await tier_repo.get_by_slug_and_type(tier_slug, package_type)
        if not tier:
            active_tiers = await tier_repo.list_active()
            tier = active_tiers[0] if active_tiers else None
        if not tier:
            msg = f"No tier found for slug={tier_slug}, type={package_type}"
            raise ValueError(msg)

        # 3. Create agreement and activate (Req 8.4, 8.6)
        stripe_data: dict[str, Any] = {
            "stripe_subscription_id": subscription_id or None,
            "stripe_customer_id": stripe_customer_id or None,
        }
        agreement = await agreement_svc.create_agreement(
            customer_id=customer.id,
            tier_id=tier.id,
            stripe_data=stripe_data,
        )

        # Activate immediately — payment confirmed by Stripe checkout
        _ = await agreement_svc.transition_status(
            agreement.id,
            AgreementStatus.ACTIVE,
            reason="Payment confirmed via Stripe checkout",
        )

        # Populate surcharge fields on agreement (Req 3.14)
        surcharge_breakdown = SurchargeCalculator.calculate(
            tier_slug=tier_slug,
            package_type=package_type,
            zone_count=meta_zone_count,
            has_lake_pump=meta_has_lake_pump,
            base_price=tier.annual_price,
            has_rpz_backflow=meta_has_rpz_backflow,
        )
        _ = await agreement_repo.update(
            agreement,
            {
                "zone_count": meta_zone_count,
                "has_lake_pump": meta_has_lake_pump,
                "has_rpz_backflow": meta_has_rpz_backflow,
                "base_price": tier.annual_price,
                "annual_price": surcharge_breakdown.total,
            },
        )

        # Carry email_marketing_consent to customer (Req 2.5)
        if meta_email_marketing_consent:
            customer.email_opt_in = True
            customer.email_opt_in_at = now  # type: ignore[assignment]
            customer.email_opt_in_source = "checkout_marketing_consent"  # type: ignore[assignment]
        else:
            customer.email_opt_in = False

        # 4. Generate seasonal jobs (Req 8.5)
        _ = await job_gen.generate_jobs(agreement)

        # Refresh agreement to pick up jobs relationship
        await self.session.refresh(agreement)

        # 5. Link orphaned consent/disclosure records (Req 8.7)
        if consent_token_str:
            try:
                consent_uuid = UUID(consent_token_str)
                _ = await compliance_svc.link_orphaned_records(
                    consent_token=consent_uuid,
                    customer_id=customer.id,
                    agreement_id=agreement.id,
                )

                # Transfer SMS consent to customer record (Req 29)
                sms_stmt = select(SmsConsentRecord).where(
                    SmsConsentRecord.consent_token == consent_uuid,
                    SmsConsentRecord.consent_given.is_(True),
                )
                sms_result = await self.session.execute(sms_stmt)
                sms_consented = sms_result.scalar_one_or_none()
                if sms_consented:
                    customer.sms_opt_in = True
                    customer.sms_opt_in_at = now  # type: ignore[assignment]
                    customer.sms_opt_in_source = "stripe_checkout"  # type: ignore[assignment]
            except (ValueError, AttributeError):
                self.log_failed(
                    "webhook_link_orphaned",
                    error=ValueError(
                        f"Invalid consent_token: {consent_token_str}",
                    ),
                )

        # 6. Create compliance disclosures (Req 34.1, 34.2, 34.3)
        _ = await compliance_svc.create_disclosure(
            disclosure_type=DisclosureType.PRE_SALE,
            agreement_id=agreement.id,
            customer_id=customer.id,
            content=f"Pre-sale disclosure for {tier.name} {package_type}",
            sent_via="stripe_checkout",
        )

        confirmation_result = email_svc.send_confirmation_email(
            customer,
            agreement,
            tier,
        )
        confirmation_content = confirmation_result.get("content", "")
        _ = await compliance_svc.create_disclosure(
            disclosure_type=DisclosureType.CONFIRMATION,
            agreement_id=agreement.id,
            customer_id=customer.id,
            content=(
                confirmation_content or f"Confirmation for {agreement.agreement_number}"
            ),
            sent_via=confirmation_result.get("sent_via", "pending"),
            recipient_email=confirmation_result.get("recipient_email"),
            delivery_confirmed=confirmation_result.get("sent", False),
        )

        # 7. Send welcome email (Req 39C.1, 39C.2)
        _ = email_svc.send_welcome_email(customer, agreement, tier)

        await self.session.flush()

        self.log_completed(
            "webhook_checkout_completed",
            agreement_id=str(agreement.id),
            customer_id=str(customer.id),
            stripe_event_id=event["id"],
        )

    # ------------------------------------------------------------------
    # Stub handlers — real logic implemented in tasks 10.2-10.6
    # ------------------------------------------------------------------

    async def _handle_invoice_paid(self, event: stripe.Event) -> None:
        """Handle invoice.paid event.

        First invoice: transition PENDING → ACTIVE.
        Renewal invoice: transition to ACTIVE, update end_date/renewal_date,
        trigger Job_Generator for next season.
        Always updates last_payment_date, last_payment_amount, payment_status.

        Validates: Requirements 10.1, 10.2, 10.3
        """
        self.log_started(
            "webhook_invoice_paid",
            stripe_event_id=event["id"],
        )

        invoice_obj = event["data"]["object"]
        subscription_id = self._extract_subscription_id(invoice_obj)

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        job_gen = JobGenerator(self.session)

        # Look up agreement: try subscription_id first, then customer_id fallback
        agreement = None
        if subscription_id:
            agreement = await agreement_repo.get_by_stripe_subscription_id(
                subscription_id,
            )
        if not agreement:
            stripe_cust_id: str = invoice_obj.get("customer", "") or ""
            if stripe_cust_id:
                agreement = await agreement_repo.get_by_stripe_customer_id(
                    stripe_cust_id,
                )
                if agreement:
                    self.log_started(
                        "webhook_invoice_paid_fallback",
                        lookup="stripe_customer_id",
                        stripe_customer_id=stripe_cust_id,
                    )
        if not agreement:
            self.log_failed(
                "webhook_invoice_paid",
                error=ValueError(f"No agreement for subscription {subscription_id}"),
            )
            return

        now = datetime.now(timezone.utc)
        amount_paid_cents: int = invoice_obj.get("amount_paid", 0)
        amount_paid = Decimal(str(amount_paid_cents)) / Decimal(100)

        # CR-4: Gate the renewal branch on Stripe's ``billing_reason`` rather
        # than "any invoice after the first." Mid-cycle prorated additions
        # and manual top-ups have ``last_payment_date != None`` too, but only
        # ``subscription_cycle`` means "this is the renewal charge for the
        # next term." Everything else (subscription_create/update/manual,
        # or missing) is either the first invoice or a non-renewal charge.
        billing_reason = (invoice_obj.get("billing_reason") or "").strip()
        is_renewal_cycle = billing_reason == "subscription_cycle"
        is_first_invoice = (
            agreement.last_payment_date is None
            and billing_reason in ("subscription_create", "", "manual")
        )

        if is_first_invoice:
            # First invoice (Req 10.1)
            # Activate legacy PENDING agreements (backward compat)
            if agreement.status == AgreementStatus.PENDING.value:
                _ = await agreement_svc.transition_status(
                    agreement.id,
                    AgreementStatus.ACTIVE,
                    reason="First invoice paid",
                )
            # No date updates or job generation — checkout already handled those
        elif is_renewal_cycle:
            # Renewal invoice (Req 10.2)
            current_status = AgreementStatus(agreement.status)
            if current_status != AgreementStatus.ACTIVE:
                _ = await agreement_svc.transition_status(
                    agreement.id,
                    AgreementStatus.ACTIVE,
                    reason="Renewal invoice paid",
                )

            # Update end_date and renewal_date for new term
            new_end = date(now.year + 1, now.month, now.day)
            new_renewal = new_end - timedelta(days=30)
            _ = await agreement_repo.update(
                agreement,
                {"end_date": new_end, "renewal_date": new_renewal},
            )

            # Generate next season's jobs or renewal proposal (Req 31.1)
            await self.session.refresh(agreement)
            if agreement.auto_renew:
                renewal_svc = ContractRenewalReviewService(self.session)
                _ = await renewal_svc.generate_proposal(agreement.id)
                self.log_completed(
                    "webhook_renewal_proposal_created",
                    agreement_id=str(agreement.id),
                )
            else:
                _ = await job_gen.generate_jobs(agreement)
        else:
            # Non-first, non-renewal invoice (mid-cycle prorated add-on,
            # subscription_update, manual top-up, etc.). No renewal logic;
            # payment fields still update below so the dashboard stays fresh.
            self.log_started(
                "webhook_invoice_paid_noncycle",
                agreement_id=str(agreement.id),
                billing_reason=billing_reason,
                stripe_event_id=event["id"],
            )

        # Update payment fields (Req 10.3)
        _ = await agreement_repo.update(
            agreement,
            {
                "last_payment_date": now,
                "last_payment_amount": amount_paid,
                "payment_status": AgreementPaymentStatus.CURRENT.value,
            },
        )

        await self.session.flush()

        self.log_completed(
            "webhook_invoice_paid",
            agreement_id=str(agreement.id),
            is_first_invoice=is_first_invoice,
            is_renewal_cycle=is_renewal_cycle,
            billing_reason=billing_reason,
            stripe_event_id=event["id"],
        )

    async def _handle_invoice_payment_failed(self, event: stripe.Event) -> None:
        """Handle invoice.payment_failed event.

        Transition to PAST_DUE and set payment_status=PAST_DUE.
        If already PAST_DUE with retries exhausted: transition to PAUSED,
        set payment_status=FAILED.

        Validates: Requirements 11.1, 11.2
        """
        self.log_started(
            "webhook_invoice_payment_failed",
            stripe_event_id=event["id"],
        )

        invoice_obj = event["data"]["object"]
        subscription_id = self._extract_subscription_id(invoice_obj)

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)

        agreement = None
        if subscription_id:
            agreement = await agreement_repo.get_by_stripe_subscription_id(
                subscription_id,
            )
        if not agreement:
            stripe_cust_id_fail: str = invoice_obj.get("customer", "") or ""
            if stripe_cust_id_fail:
                agreement = await agreement_repo.get_by_stripe_customer_id(
                    stripe_cust_id_fail,
                )
        if not agreement:
            self.log_failed(
                "webhook_invoice_payment_failed",
                error=ValueError(
                    f"No agreement for subscription={subscription_id}",
                ),
            )
            return

        current_status = AgreementStatus(agreement.status)
        attempt_count: int = invoice_obj.get("attempt_count", 1)

        if current_status == AgreementStatus.PAST_DUE and attempt_count > 1:
            # Retries exhausted: escalate to PAUSED (Req 11.2)
            _ = await agreement_svc.transition_status(
                agreement.id,
                AgreementStatus.PAUSED,
                reason=f"Payment failed after {attempt_count} attempts",
            )
            _ = await agreement_repo.update(
                agreement,
                {
                    "payment_status": AgreementPaymentStatus.FAILED.value,
                    "pause_reason": f"Payment failed after {attempt_count} attempts",
                },
            )
        else:
            # First failure or non-PAST_DUE: transition to PAST_DUE (Req 11.1)
            if current_status != AgreementStatus.PAST_DUE:
                _ = await agreement_svc.transition_status(
                    agreement.id,
                    AgreementStatus.PAST_DUE,
                    reason="Invoice payment failed",
                )
            _ = await agreement_repo.update(
                agreement,
                {"payment_status": AgreementPaymentStatus.PAST_DUE.value},
            )

        await self.session.flush()

        self.log_completed(
            "webhook_invoice_payment_failed",
            agreement_id=str(agreement.id),
            attempt_count=attempt_count,
            stripe_event_id=event["id"],
        )

    async def _handle_invoice_upcoming(self, event: stripe.Event) -> None:
        """Handle invoice.upcoming event.

        Transition to PENDING_RENEWAL, create RENEWAL_NOTICE disclosure,
        send renewal notice email, update last_renewal_notice_sent.

        Validates: Requirements 13.1, 13.2, 35.1, 35.2, 35.3, 39B.4
        """
        self.log_started(
            "webhook_invoice_upcoming",
            stripe_event_id=event["id"],
        )

        invoice_obj = event["data"]["object"]
        subscription_id = self._extract_subscription_id(invoice_obj)

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        compliance_svc = ComplianceService(self.session)
        email_svc = EmailService()

        agreement = None
        if subscription_id:
            agreement = await agreement_repo.get_by_stripe_subscription_id(
                subscription_id,
            )
        if not agreement:
            stripe_cust_id_upcoming: str = invoice_obj.get("customer", "") or ""
            if stripe_cust_id_upcoming:
                agreement = await agreement_repo.get_by_stripe_customer_id(
                    stripe_cust_id_upcoming,
                )
        if not agreement:
            self.log_failed(
                "webhook_invoice_upcoming",
                error=ValueError(
                    f"No agreement for subscription={subscription_id}",
                ),
            )
            return

        # Transition to PENDING_RENEWAL (Req 13.1)
        current_status = AgreementStatus(agreement.status)
        if current_status != AgreementStatus.PENDING_RENEWAL:
            _ = await agreement_svc.transition_status(
                agreement.id,
                AgreementStatus.PENDING_RENEWAL,
                reason="Upcoming invoice received from Stripe",
            )

        # Send renewal notice email (Req 39B.4)
        customer = agreement.customer
        renewal_result = email_svc.send_renewal_notice(customer, agreement)

        # Create RENEWAL_NOTICE disclosure record (Req 35.1, 35.2, 35.3)
        renewal_content = renewal_result.get("content", "")
        _ = await compliance_svc.create_disclosure(
            disclosure_type=DisclosureType.RENEWAL_NOTICE,
            agreement_id=agreement.id,
            customer_id=agreement.customer_id,
            content=(
                renewal_content or f"Renewal notice for {agreement.agreement_number}"
            ),
            sent_via=renewal_result.get("sent_via", "pending"),
            recipient_email=renewal_result.get("recipient_email"),
            delivery_confirmed=renewal_result.get("sent", False),
        )

        # Update last_renewal_notice_sent (Req 13.2)
        now = datetime.now(timezone.utc)
        _ = await agreement_repo.update(
            agreement,
            {"last_renewal_notice_sent": now},
        )

        await self.session.flush()

        self.log_completed(
            "webhook_invoice_upcoming",
            agreement_id=str(agreement.id),
            stripe_event_id=event["id"],
        )

    async def _handle_subscription_updated(self, event: stripe.Event) -> None:
        """Handle customer.subscription.updated event.

        Updates stripe_subscription_id and metadata, transitions status
        if Stripe status changed, handles payment recovery (PAUSED → ACTIVE),
        and syncs auto_renew from cancel_at_period_end.
        Idempotent: skips if local state already matches.

        Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5
        """
        self.log_started(
            "webhook_subscription_updated",
            stripe_event_id=event["id"],
        )

        sub_obj = event["data"]["object"]
        subscription_id: str = sub_obj.get("id", "") or ""
        if not subscription_id:
            self.log_completed(
                "webhook_subscription_updated",
                skipped="no_subscription_id",
            )
            return

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)

        agreement = await agreement_repo.get_by_stripe_subscription_id(subscription_id)
        if not agreement:
            self.log_failed(
                "webhook_subscription_updated",
                error=ValueError(f"No agreement for subscription {subscription_id}"),
            )
            return

        current_status = AgreementStatus(agreement.status)
        updates: dict[str, Any] = {}

        # Sync auto_renew from cancel_at_period_end (Req 12.4)
        cancel_at_period_end: bool = sub_obj.get("cancel_at_period_end", False)
        new_auto_renew = not cancel_at_period_end
        if agreement.auto_renew != new_auto_renew:
            updates["auto_renew"] = new_auto_renew

        # Map Stripe subscription status to local AgreementStatus (Req 12.1, 12.2)
        stripe_status: str = sub_obj.get("status", "") or ""
        status_map: dict[str, AgreementStatus] = {
            "active": AgreementStatus.ACTIVE,
            "past_due": AgreementStatus.PAST_DUE,
            "paused": AgreementStatus.PAUSED,
            "canceled": AgreementStatus.CANCELLED,
            "unpaid": AgreementStatus.PAUSED,
        }
        target_status = status_map.get(stripe_status)

        if target_status and target_status != current_status:
            # Payment recovery: PAUSED → ACTIVE (Req 12.3)
            is_recovery = (
                current_status == AgreementStatus.PAUSED
                and target_status == AgreementStatus.ACTIVE
            )
            if is_recovery:
                updates["pause_reason"] = None
                updates["payment_status"] = AgreementPaymentStatus.CURRENT.value

            valid_targets = VALID_AGREEMENT_STATUS_TRANSITIONS.get(
                current_status,
                set(),
            )
            if target_status in valid_targets:
                _ = await agreement_svc.transition_status(
                    agreement.id,
                    target_status,
                    reason=f"Stripe subscription status changed to {stripe_status}",
                )

        # Apply remaining field updates (Req 12.5)
        if updates:
            _ = await agreement_repo.update(agreement, updates)

        await self.session.flush()

        self.log_completed(
            "webhook_subscription_updated",
            agreement_id=str(agreement.id),
            stripe_status=stripe_status,
            stripe_event_id=event["id"],
        )

    async def _handle_subscription_deleted(self, event: stripe.Event) -> None:
        """Handle customer.subscription.deleted event.

        Transitions to CANCELLED, cancels APPROVED jobs, preserves
        SCHEDULED/IN_PROGRESS/COMPLETED, computes prorated refund,
        creates CANCELLATION_CONF disclosure, sends cancellation email.

        Validates: Requirements 14.1, 14.2, 14.3, 14.4, 36.1, 36.2, 39B.6
        """
        self.log_started(
            "webhook_subscription_deleted",
            stripe_event_id=event["id"],
        )

        sub_obj = event["data"]["object"]
        subscription_id: str = sub_obj.get("id", "") or ""
        if not subscription_id:
            self.log_completed(
                "webhook_subscription_deleted",
                skipped="no_subscription_id",
            )
            return

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        compliance_svc = ComplianceService(self.session)
        email_svc = EmailService()

        agreement = await agreement_repo.get_by_stripe_subscription_id(subscription_id)
        if not agreement:
            self.log_failed(
                "webhook_subscription_deleted",
                error=ValueError(f"No agreement for subscription {subscription_id}"),
            )
            return

        # Cancel agreement: cancels APPROVED jobs, computes refund (Req 14.1-14.4)
        cancellation_reason = (
            sub_obj.get("cancellation_details", {}).get(
                "reason",
                "Subscription cancelled via Stripe",
            )
            or "Subscription cancelled via Stripe"
        )
        agreement = await agreement_svc.cancel_agreement(
            agreement.id,
            reason=cancellation_reason,
        )

        # Refresh to get updated relationships
        await self.session.refresh(agreement, ["customer"])
        customer = agreement.customer

        # Send cancellation confirmation email (Req 39B.6)
        cancel_result = email_svc.send_cancellation_confirmation(customer, agreement)

        # Create CANCELLATION_CONF disclosure record (Req 36.1, 36.2)
        cancel_content = cancel_result.get("content", "")
        _ = await compliance_svc.create_disclosure(
            disclosure_type=DisclosureType.CANCELLATION_CONF,
            agreement_id=agreement.id,
            customer_id=agreement.customer_id,
            content=(
                cancel_content
                or f"Cancellation confirmation for {agreement.agreement_number}"
            ),
            sent_via=cancel_result.get("sent_via", "pending"),
            recipient_email=cancel_result.get("recipient_email"),
            delivery_confirmed=cancel_result.get("sent", False),
        )

        await self.session.flush()

        self.log_completed(
            "webhook_subscription_deleted",
            agreement_id=str(agreement.id),
            stripe_event_id=event["id"],
        )

    # ------------------------------------------------------------------
    # Architecture C — Stripe Payment Links handlers
    # Validates: Stripe Payment Links plan §Phase 2.10-2.13.
    # ------------------------------------------------------------------

    @staticmethod
    def _mask_pi(pi_id: str) -> str:
        """Mask a Stripe payment_intent ID for safe INFO-level logging."""
        if len(pi_id) <= 9:
            return pi_id
        return f"{pi_id[:6]}***{pi_id[-4:]}"

    async def _handle_payment_intent_succeeded(self, event: stripe.Event) -> None:
        """Handle ``payment_intent.succeeded`` for Architecture C invoices.

        Marks the matched invoice PAID, sets ``Job.payment_collected_on_site``
        true, and mirrors ``stripe_payment_link_active = false``. Idempotent
        on replay (no-op if invoice is already PAID). Subscription-driven
        intents are short-circuited (CG-7); cancelled invoices are flagged
        for manual refund (CG-8); non-USD charges are refused (currency
        out of scope per plan).
        """
        from grins_platform.models.enums import (  # noqa: PLC0415
            InvoiceStatus,
            PaymentMethod,
        )
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
            InvoiceRepository,
        )
        from grins_platform.repositories.job_repository import (  # noqa: PLC0415
            JobRepository,
        )
        from grins_platform.schemas.invoice import (  # noqa: PLC0415
            PaymentRecord,
        )
        from grins_platform.services.invoice_service import (  # noqa: PLC0415
            InvoiceService,
        )

        intent = event["data"]["object"]
        intent_id: str = intent.get("id", "")
        masked = self._mask_pi(intent_id)
        self.log_started(
            "webhook_payment_intent_succeeded",
            stripe_event_id=event["id"],
            payment_intent=masked,
        )

        # CG-7: subscription-side PaymentIntents are owned by invoice.paid.
        related_invoice = intent.get("invoice")
        if related_invoice:
            self.log_completed(
                "webhook_payment_intent_succeeded",
                payment_intent=masked,
                outcome="subscription_intent_skipped",
            )
            return

        # Currency check — out-of-scope for this feature.
        currency = (intent.get("currency") or "").lower()
        if currency != "usd":
            self.log_failed(
                "webhook_payment_intent_succeeded",
                error=ValueError(f"Unsupported currency: {currency}"),
                payment_intent=masked,
            )
            return

        metadata = intent.get("metadata") or {}
        invoice_id_raw = metadata.get("invoice_id")
        if not invoice_id_raw:
            self.logger.warning(
                "stripe.webhook.payment_intent.unmatched_metadata",
                payment_intent=masked,
            )
            return

        try:
            invoice_id = UUID(str(invoice_id_raw))
        except (ValueError, AttributeError):
            self.logger.warning(
                "stripe.webhook.payment_intent.invalid_metadata_uuid",
                payment_intent=masked,
                invoice_id_raw=str(invoice_id_raw)[:50],
            )
            return

        invoice_repo = InvoiceRepository(session=self.session)
        invoice = await invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            self.logger.warning(
                "stripe.webhook.payment_intent.invoice_not_found",
                payment_intent=masked,
                invoice_id=str(invoice_id),
            )
            return

        # CG-8: refuse to mark cancelled invoices paid.
        if invoice.status == InvoiceStatus.CANCELLED.value:
            self.logger.warning(
                "stripe.webhook.payment_intent.cancelled_invoice_charged",
                payment_intent=masked,
                invoice_id=str(invoice_id),
            )
            return

        # Idempotency double-layer: if invoice is already PAID, no-op.
        if invoice.status == InvoiceStatus.PAID.value:
            self.log_completed(
                "webhook_payment_intent_succeeded",
                payment_intent=masked,
                invoice_id=str(invoice_id),
                outcome="invoice_already_paid",
            )
            return

        amount_received_cents = intent.get("amount_received") or intent.get(
            "amount",
            0,
        )
        amount = Decimal(str(amount_received_cents)) / Decimal(100)

        invoice_service = InvoiceService(
            invoice_repository=invoice_repo,
            job_repository=JobRepository(session=self.session),
        )
        payment_record = PaymentRecord(
            amount=amount,
            payment_method=PaymentMethod.CREDIT_CARD,
            payment_reference=f"stripe:{intent_id}",
        )
        await invoice_service.record_payment(invoice_id, payment_record)

        # Mirror Stripe's auto-deactivation (completed_sessions.limit=1).
        await invoice_repo.update(
            invoice_id,
            stripe_payment_link_active=False,
        )

        # Job.payment_collected_on_site = True
        job_stmt = select(Job).where(Job.id == invoice.job_id)
        job_result = await self.session.execute(job_stmt)
        job = job_result.scalar_one_or_none()
        if job is not None:
            job.payment_collected_on_site = True

        await self.session.flush()
        self.log_completed(
            "webhook_payment_intent_succeeded",
            payment_intent=masked,
            invoice_id=str(invoice_id),
            amount=str(amount),
        )

    async def _handle_payment_intent_payment_failed(
        self,
        event: stripe.Event,
    ) -> None:
        """Handle ``payment_intent.payment_failed``.

        No invoice mutation: failed customer attempts simply leave the
        invoice in its current state. The link is still active (Stripe
        only deactivates on a *completed* session). We log enough context
        to investigate failures from Sentry / log aggregation.
        """
        intent = event["data"]["object"]
        intent_id: str = intent.get("id", "")
        masked = self._mask_pi(intent_id)
        last_error = (intent.get("last_payment_error") or {}).get("code", "")
        self.log_started(
            "webhook_payment_intent_payment_failed",
            stripe_event_id=event["id"],
            payment_intent=masked,
            last_error=last_error,
        )
        self.log_completed(
            "webhook_payment_intent_payment_failed",
            payment_intent=masked,
        )

    async def _handle_payment_intent_canceled(
        self,
        event: stripe.Event,
    ) -> None:
        """Handle ``payment_intent.canceled``.

        No-op for Payment Link flows; logged so unexpected cancellations
        are visible in the audit trail.
        """
        intent = event["data"]["object"]
        intent_id: str = intent.get("id", "")
        masked = self._mask_pi(intent_id)
        self.log_started(
            "webhook_payment_intent_canceled",
            stripe_event_id=event["id"],
            payment_intent=masked,
        )
        self.log_completed(
            "webhook_payment_intent_canceled",
            payment_intent=masked,
        )

    async def _handle_charge_refunded(self, event: stripe.Event) -> None:
        """Handle ``charge.refunded`` events.

        Full refund (``amount_refunded == amount``): transitions the
        invoice to REFUNDED and clears
        ``Job.payment_collected_on_site``. Idempotent.

        Partial refund: leaves the invoice PAID/PARTIAL, updates
        ``paid_amount`` to ``amount - amount_refunded``, and appends a
        note documenting the refund.
        """
        from grins_platform.models.enums import InvoiceStatus  # noqa: PLC0415
        from grins_platform.models.job import Job  # noqa: PLC0415
        from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
            InvoiceRepository,
        )

        charge = event["data"]["object"]
        intent_id = charge.get("payment_intent") or ""
        masked = self._mask_pi(str(intent_id))
        self.log_started(
            "webhook_charge_refunded",
            stripe_event_id=event["id"],
            payment_intent=masked,
        )

        if not intent_id:
            self.logger.warning(
                "stripe.webhook.charge_refunded.missing_payment_intent",
            )
            return

        invoice_repo = InvoiceRepository(session=self.session)
        invoice = await invoice_repo.get_by_payment_intent_reference(
            str(intent_id),
        )
        if invoice is None:
            self.logger.warning(
                "stripe.webhook.charge_refunded.unmatched",
                payment_intent=masked,
            )
            return

        amount_cents = int(charge.get("amount") or 0)
        refunded_cents = int(charge.get("amount_refunded") or 0)
        is_full_refund = refunded_cents >= amount_cents > 0

        if is_full_refund:
            if invoice.status == InvoiceStatus.REFUNDED.value:
                self.log_completed(
                    "webhook_charge_refunded",
                    payment_intent=masked,
                    outcome="already_refunded",
                )
                return
            await invoice_repo.update(
                invoice.id,
                status=InvoiceStatus.REFUNDED.value,
                stripe_payment_link_active=False,
            )
            job_stmt = select(Job).where(Job.id == invoice.job_id)
            job_result = await self.session.execute(job_stmt)
            job = job_result.scalar_one_or_none()
            if job is not None:
                job.payment_collected_on_site = False
            await self.session.flush()
            self.log_completed(
                "webhook_charge_refunded",
                payment_intent=masked,
                invoice_id=str(invoice.id),
                outcome="full_refund",
            )
            return

        # Partial refund — keep the invoice paid but reflect the
        # remaining balance and annotate the notes field.
        net_paid_cents = max(amount_cents - refunded_cents, 0)
        net_paid = Decimal(str(net_paid_cents)) / Decimal(100)
        prior_notes = invoice.notes or ""
        annotation = (
            f"Stripe partial refund: ${Decimal(str(refunded_cents)) / Decimal(100)} "
            f"refunded on {datetime.now(timezone.utc).date().isoformat()}."
        )
        new_notes = f"{prior_notes}\n{annotation}".strip()
        await invoice_repo.update(
            invoice.id,
            paid_amount=net_paid,
            status=InvoiceStatus.PARTIAL.value,
            notes=new_notes,
        )
        await self.session.flush()
        self.log_completed(
            "webhook_charge_refunded",
            payment_intent=masked,
            invoice_id=str(invoice.id),
            outcome="partial_refund",
            refunded_cents=refunded_cents,
        )

    async def _handle_charge_dispute_created(
        self,
        event: stripe.Event,
    ) -> None:
        """Handle ``charge.dispute.created``.

        Marks the invoice DISPUTED, appends the dispute reason and
        ``due_by`` deadline to ``notes``, and emits a WARNING log so the
        on-call alerting can page admins.
        """
        from grins_platform.models.enums import InvoiceStatus  # noqa: PLC0415
        from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
            InvoiceRepository,
        )

        dispute = event["data"]["object"]
        intent_id = dispute.get("payment_intent") or ""
        masked = self._mask_pi(str(intent_id))
        reason = dispute.get("reason") or "unknown"
        due_by = dispute.get("evidence_details", {}).get("due_by")

        self.logger.warning(
            "stripe.webhook.charge_dispute_created",
            stripe_event_id=event["id"],
            payment_intent=masked,
            reason=reason,
        )

        if not intent_id:
            return

        invoice_repo = InvoiceRepository(session=self.session)
        invoice = await invoice_repo.get_by_payment_intent_reference(
            str(intent_id),
        )
        if invoice is None:
            self.logger.warning(
                "stripe.webhook.charge_dispute_created.unmatched",
                payment_intent=masked,
            )
            return

        if invoice.status == InvoiceStatus.DISPUTED.value:
            return

        prior_notes = invoice.notes or ""
        due_str = (
            datetime.fromtimestamp(int(due_by), tz=timezone.utc).date().isoformat()
            if due_by
            else "unknown"
        )
        annotation = (
            f"Stripe dispute opened ({reason}); evidence due by {due_str}."
        )
        new_notes = f"{prior_notes}\n{annotation}".strip()
        await invoice_repo.update(
            invoice.id,
            status=InvoiceStatus.DISPUTED.value,
            notes=new_notes,
        )
        await self.session.flush()
        self.log_completed(
            "webhook_charge_dispute_created",
            payment_intent=masked,
            invoice_id=str(invoice.id),
            reason=reason,
        )


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Receive and process Stripe webhook events.

    Verifies signature, deduplicates, and routes to handlers.
    Always returns HTTP 200 within 5 seconds.

    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.2, 7.3
    """
    settings = StripeSettings()

    # Read raw body for signature verification
    raw_body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # bughunt M-15: missing secret is an *infrastructure* misconfig, not a
    # bad request. Returning 400 makes Stripe stop retrying (4xx is
    # treated as terminal), so the webhook quietly fails until someone
    # notices the missed events. 503 keeps Stripe retrying with backoff
    # *and* surfaces the issue on the on-call dashboard.
    if not settings.stripe_webhook_secret:
        logger.error("stripe.webhook.missing_secret")
        return Response(
            content='{"error": "Webhook secret not configured"}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload=raw_body,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError:
        logger.warning("stripe.webhook.invalid_payload")
        return Response(
            content='{"error": "Invalid payload"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )
    except stripe.SignatureVerificationError:
        logger.warning(
            "stripe.webhook.signature_failed",
        )
        return Response(
            content='{"error": "Invalid signature"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    logger.info(
        "stripe.webhook.received",
        stripe_event_id=event["id"],
        event_type=event["type"],
    )

    # Process event
    handler = StripeWebhookHandler(db)
    result = await handler.handle_event(event)

    return Response(
        content=f'{{"status": "{result["status"]}"}}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Twilio inbound SMS webhook — routes to SMS_Service.handle_inbound()
# Validates: Requirement 8.1
# ---------------------------------------------------------------------------


@router.post(
    "/twilio-inbound",
    status_code=status.HTTP_200_OK,
    summary="Handle inbound SMS from Twilio",
    description=(
        "Receives inbound SMS from Twilio, processes STOP keywords and "
        "informal opt-out phrases via SMS_Service.handle_inbound()."
    ),
)
async def twilio_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Handle inbound SMS webhook from Twilio.

    Validates Twilio signature, extracts From/Body/MessageSid,
    and routes to SMS_Service.handle_inbound().

    Validates: Requirement 8.1
    """
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data)

    if not validate_twilio_signature(url, params, signature):
        return Response(
            content='{"error": "Invalid Twilio signature"}',
            status_code=status.HTTP_403_FORBIDDEN,
            media_type="application/json",
        )

    from_phone = str(form_data.get("From", ""))
    body = str(form_data.get("Body", ""))
    message_sid = str(form_data.get("MessageSid", ""))

    sms_service = SMSService(db)
    result = await sms_service.handle_inbound(from_phone, body, message_sid)

    logger.info(
        "twilio.inbound.processed",
        action=result.get("action"),
        from_phone=from_phone,
    )

    return Response(
        content="<Response></Response>",
        status_code=status.HTTP_200_OK,
        media_type="application/xml",
    )
