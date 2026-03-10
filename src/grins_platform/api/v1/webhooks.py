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

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.enums import (
    VALID_AGREEMENT_STATUS_TRANSITIONS,
    AgreementPaymentStatus,
    AgreementStatus,
    DisclosureType,
)
from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.stripe_webhook_event_repository import (
    StripeWebhookEventRepository,
)
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.services.agreement_service import AgreementService
from grins_platform.services.compliance_service import ComplianceService
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.email_service import EmailService
from grins_platform.services.job_generator import JobGenerator
from grins_platform.services.stripe_config import StripeSettings

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
    },
)


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
            await self.repo.mark_failed(event_record, str(e))
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

        # Build services
        customer_repo = CustomerRepository(self.session)
        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        compliance_svc = ComplianceService(self.session)
        email_svc = EmailService()
        job_gen = JobGenerator(self.session)

        # 1. Find or create customer by email (Req 8.1, 8.2, 8.3)
        customer = None
        if customer_email:
            existing = await customer_repo.find_by_email(customer_email)
            if existing:
                customer = existing[0]

        now = datetime.now(timezone.utc)

        if customer is None:
            # Extract name from session
            cust_details: dict[str, Any] = session_obj.get("customer_details", {}) or {}
            full_name = str(cust_details.get("name", "") or "")
            parts = full_name.strip().split(maxsplit=1)
            first_name = parts[0] if parts else "Customer"
            last_name = parts[1] if len(parts) > 1 else ""
            phone = str(cust_details.get("phone", "") or "")

            create_data = CustomerCreate(
                first_name=first_name,
                last_name=last_name,
                phone=phone or f"000{event['id'][-7:]}",
                email=customer_email or None,
            )
            cust_svc = CustomerService(customer_repo)
            cust_resp = await cust_svc.create_customer(create_data)
            customer = await customer_repo.get_by_id(cust_resp.id)
            assert customer is not None

        # Update stripe_customer_id (Req 8.3, 28.2)
        if stripe_customer_id and customer.stripe_customer_id != stripe_customer_id:
            customer.stripe_customer_id = stripe_customer_id  # type: ignore[assignment]

        # Set email_opt_in_at and email_opt_in_source (Req 68.2)
        if not customer.email_opt_in_at:
            customer.email_opt_in_at = now  # type: ignore[assignment]
            customer.email_opt_in_source = "stripe_checkout"  # type: ignore[assignment]
            customer.email_opt_in = True

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

        # 3. Create agreement with PENDING status (Req 8.4, 8.6)
        stripe_data: dict[str, Any] = {
            "stripe_subscription_id": subscription_id or None,
            "stripe_customer_id": stripe_customer_id or None,
        }
        agreement = await agreement_svc.create_agreement(
            customer_id=customer.id,
            tier_id=tier.id,
            stripe_data=stripe_data,
        )

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
        subscription_id: str = invoice_obj.get("subscription", "") or ""
        if not subscription_id:
            self.log_completed(
                "webhook_invoice_paid",
                skipped="no_subscription_id",
            )
            return

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        job_gen = JobGenerator(self.session)

        agreement = await agreement_repo.get_by_stripe_subscription_id(subscription_id)
        if not agreement:
            self.log_failed(
                "webhook_invoice_paid",
                error=ValueError(f"No agreement for subscription {subscription_id}"),
            )
            return

        now = datetime.now(timezone.utc)
        amount_paid_cents: int = invoice_obj.get("amount_paid", 0)
        amount_paid = Decimal(str(amount_paid_cents)) / Decimal(100)

        is_first_invoice = agreement.status == AgreementStatus.PENDING.value

        if is_first_invoice:
            # First invoice: PENDING → ACTIVE (Req 10.1)
            _ = await agreement_svc.transition_status(
                agreement.id,
                AgreementStatus.ACTIVE,
                reason="First invoice paid",
            )
        else:
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

            # Generate next season's jobs
            await self.session.refresh(agreement)
            _ = await job_gen.generate_jobs(agreement)

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
        subscription_id: str = invoice_obj.get("subscription", "") or ""
        if not subscription_id:
            self.log_completed(
                "webhook_invoice_payment_failed",
                skipped="no_subscription_id",
            )
            return

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)

        agreement = await agreement_repo.get_by_stripe_subscription_id(subscription_id)
        if not agreement:
            self.log_failed(
                "webhook_invoice_payment_failed",
                error=ValueError(f"No agreement for subscription {subscription_id}"),
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
        subscription_id: str = invoice_obj.get("subscription", "") or ""
        if not subscription_id:
            self.log_completed(
                "webhook_invoice_upcoming",
                skipped="no_subscription_id",
            )
            return

        agreement_repo = AgreementRepository(self.session)
        tier_repo = AgreementTierRepository(self.session)
        agreement_svc = AgreementService(agreement_repo, tier_repo)
        compliance_svc = ComplianceService(self.session)
        email_svc = EmailService()

        agreement = await agreement_repo.get_by_stripe_subscription_id(
            subscription_id,
        )
        if not agreement:
            self.log_failed(
                "webhook_invoice_upcoming",
                error=ValueError(
                    f"No agreement for subscription {subscription_id}",
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

    # Verify signature
    if not settings.stripe_webhook_secret:
        logger.warning("stripe.webhook.missing_secret")
        return Response(
            content='{"error": "Webhook secret not configured"}',
            status_code=status.HTTP_400_BAD_REQUEST,
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
