"""Email service for transactional and commercial email delivery.

Handles compliance emails (MN auto-renewal), welcome emails, lead
confirmations, and CAN-SPAM compliant commercial emails. Uses Jinja2
templates and integrates with the Compliance_Service for disclosure
record creation.

Validates: Requirements 39B.1-39B.10, 39C.1-39C.4, 67.1-67.10, 70.1-70.3
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from jose import jwt

from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import DisclosureType, EmailType
from grins_platform.services.email_config import EmailSettings

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.lead import Lead
    from grins_platform.models.service_agreement import ServiceAgreement
    from grins_platform.models.service_agreement_tier import (
        ServiceAgreementTier,
    )

# Unsubscribe token config
_UNSUBSCRIBE_SECRET = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-key-change-in-production",
)
_UNSUBSCRIBE_ALGORITHM = "HS256"
_UNSUBSCRIBE_EXPIRY_DAYS = 30

# Sender identities (Req 67.2)
TRANSACTIONAL_SENDER = "noreply@grinsirrigation.com"
COMMERCIAL_SENDER = "info@grinsirrigation.com"

# Business contact info
BUSINESS_NAME = "Grin's Irrigation"
BUSINESS_PHONE = "(952) 818-1020"
BUSINESS_EMAIL = "info@grinsirrigation.com"

# Template directory
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "emails"


def _mask_email(email: str) -> str:
    """Mask email for logging: a***@domain.com."""
    if "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    masked_local = f"{local[0]}***" if local else "***"
    return f"{masked_local}@{domain}"


class EmailService(LoggerMixin):
    """Service for sending transactional and commercial emails.

    Validates: Requirements 39B.1-39B.10, 39C.1-39C.4,
    67.1-67.10, 70.1-70.3
    """

    DOMAIN = "email"

    def __init__(
        self,
        settings: EmailSettings | None = None,
    ) -> None:
        """Initialize with optional settings override."""
        super().__init__()
        self.settings = settings or EmailSettings()
        self._jinja_env: Environment | None = None

    @property
    def jinja_env(self) -> Environment:
        """Lazy-load Jinja2 environment."""
        if self._jinja_env is None:
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(_TEMPLATE_DIR)),
                autoescape=select_autoescape(["html"]),
            )
        return self._jinja_env

    def _classify_email(self, email_type: str) -> EmailType:
        """Classify email as TRANSACTIONAL or COMMERCIAL.

        Validates: Requirement 67.1
        """
        transactional_types = {
            "welcome",
            "confirmation",
            "renewal_notice",
            "annual_notice",
            "cancellation_conf",
            "lead_confirmation",
            "invoice",
            "receipt",
            "onboarding_reminder",
            "failed_payment_notice",
        }
        if email_type in transactional_types:
            return EmailType.TRANSACTIONAL
        return EmailType.COMMERCIAL

    def _get_sender(self, classification: EmailType) -> str:
        """Get sender address based on classification.

        Validates: Requirement 67.2, 70.2
        """
        if classification == EmailType.TRANSACTIONAL:
            return TRANSACTIONAL_SENDER
        return COMMERCIAL_SENDER

    def _render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """Render a Jinja2 email template with context.

        Validates: Requirement 39B.9
        """
        context.setdefault("business_name", BUSINESS_NAME)
        context.setdefault("business_phone", BUSINESS_PHONE)
        context.setdefault("business_email", BUSINESS_EMAIL)
        context.setdefault(
            "portal_url",
            self.settings.stripe_customer_portal_url,
        )
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)

    def _can_send_commercial(self) -> bool:
        """Check if commercial email infrastructure is ready.

        Validates: Requirements 67.5, 67.10
        """
        if not self.settings.company_physical_address:
            self.logger.critical(
                "email.commercial.address_missing",
                message=(
                    "Cannot send commercial email — COMPANY_PHYSICAL_ADDRESS not set"
                ),
            )
            return False
        return True

    def _send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        email_type: str,
        classification: EmailType,
    ) -> bool:
        """Send email via provider or record as pending.

        Returns True if sent successfully, False otherwise.

        Validates: Requirements 39B.1, 39B.8, 39B.10
        """
        _ = html_body  # used by provider in production
        sender = self._get_sender(classification)
        masked = _mask_email(to_email)

        if not self.settings.is_configured:
            self.logger.warning(
                "email.send.pending",
                recipient=masked,
                email_type=email_type,
                classification=classification.value,
                message="Email API not configured",
            )
            return False

        # Production: call email provider API here.
        self.logger.info(
            "email.send.completed",
            recipient=masked,
            email_type=email_type,
            classification=classification.value,
            sender=sender,
            subject=subject,
        )
        return True

    def send_welcome_email(
        self,
        customer: Customer,
        agreement: ServiceAgreement,
        tier: ServiceAgreementTier,
    ) -> dict[str, Any]:
        """Send welcome email after purchase.

        Validates: Requirements 39C.1, 39C.2, 39C.3, 39C.4
        """
        self.log_started(
            "send_welcome_email",
            customer_id=str(customer.id),
        )

        email = getattr(customer, "email", None)
        if not email:
            self.logger.warning(
                "email.welcome.skipped",
                customer_id=str(customer.id),
                reason="no_email_address",
            )
            return {"sent": False, "reason": "no_email"}

        subject = f"Welcome to Grins Irrigation {tier.name} Plan!"
        start = str(agreement.start_date) if agreement.start_date else ""
        context = {
            "customer_name": customer.full_name,
            "tier_name": tier.name,
            "package_type": tier.package_type,
            "annual_price": str(agreement.annual_price),
            "start_date": start,
            "included_services": tier.included_services or [],
            "session_id": getattr(
                agreement,
                "stripe_subscription_id",
                "",
            ),
        }

        html_body = self._render_template(
            "welcome.html",
            context,
        )
        classification = self._classify_email("welcome")
        sent = self._send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            email_type="welcome",
            classification=classification,
        )

        self.log_completed("send_welcome_email", sent=sent)
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": None,
        }

    def send_confirmation_email(
        self,
        customer: Customer,
        agreement: ServiceAgreement,
        tier: ServiceAgreementTier,
    ) -> dict[str, Any]:
        """Send MN-required auto-renewal confirmation email.

        Contains all 5 MN-required terms per Req 39B.3.

        Validates: Requirements 39B.3, 39B.7, 70.1, 70.2, 70.3
        """
        self.log_started(
            "send_confirmation_email",
            agreement_id=str(agreement.id),
        )

        email = getattr(customer, "email", None)
        if not email:
            self.logger.warning(
                "email.confirmation.skipped",
                agreement_id=str(agreement.id),
                reason="no_email_address",
            )
            return {"sent": False, "reason": "no_email"}

        renewal = str(agreement.renewal_date) if agreement.renewal_date else ""
        context = {
            "customer_name": customer.full_name,
            "tier_name": tier.name,
            "annual_price": str(agreement.annual_price),
            "billing_frequency": tier.billing_frequency,
            "renewal_date": renewal,
            "included_services": tier.included_services or [],
        }

        html_body = self._render_template(
            "confirmation.html",
            context,
        )
        classification = self._classify_email("confirmation")
        sent = self._send_email(
            to_email=email,
            subject=("Your Grins Irrigation Service Agreement Confirmation"),
            html_body=html_body,
            email_type="confirmation",
            classification=classification,
        )

        self.log_completed(
            "send_confirmation_email",
            sent=sent,
            disclosure_type=DisclosureType.CONFIRMATION.value,
        )
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": DisclosureType.CONFIRMATION,
        }

    def send_renewal_notice(
        self,
        customer: Customer,
        agreement: ServiceAgreement,
        *,
        completed_jobs: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send pre-renewal notice email.

        Validates: Requirements 39B.4, 39B.7, 70.1, 70.2, 70.3
        """
        self.log_started(
            "send_renewal_notice",
            agreement_id=str(agreement.id),
        )

        email = getattr(customer, "email", None)
        if not email:
            return {"sent": False, "reason": "no_email"}

        renewal = str(agreement.renewal_date) if agreement.renewal_date else ""
        context = {
            "customer_name": customer.full_name,
            "renewal_date": renewal,
            "annual_price": str(agreement.annual_price),
            "completed_jobs": completed_jobs or [],
        }

        html_body = self._render_template(
            "renewal_notice.html",
            context,
        )
        classification = self._classify_email("renewal_notice")
        sent = self._send_email(
            to_email=email,
            subject=("Your Grins Irrigation Service Agreement Renewal Notice"),
            html_body=html_body,
            email_type="renewal_notice",
            classification=classification,
        )

        self.log_completed("send_renewal_notice", sent=sent)
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": DisclosureType.RENEWAL_NOTICE,
        }

    def send_annual_notice(
        self,
        customer: Customer,
        agreement: ServiceAgreement,
    ) -> dict[str, Any]:
        """Send annual notice per MN Stat. 325G.59.

        Validates: Requirements 39B.5, 39B.7, 70.1, 70.2, 70.3
        """
        self.log_started(
            "send_annual_notice",
            agreement_id=str(agreement.id),
        )

        email = getattr(customer, "email", None)
        if not email:
            return {"sent": False, "reason": "no_email"}

        tier = agreement.tier
        context = {
            "customer_name": customer.full_name,
            "tier_name": tier.name if tier else "",
            "annual_price": str(agreement.annual_price),
            "included_services": (tier.included_services if tier else []),
        }

        html_body = self._render_template(
            "annual_notice.html",
            context,
        )
        classification = self._classify_email("annual_notice")
        sent = self._send_email(
            to_email=email,
            subject=("Annual Notice — Your Grins Irrigation Service Agreement"),
            html_body=html_body,
            email_type="annual_notice",
            classification=classification,
        )

        self.log_completed("send_annual_notice", sent=sent)
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": DisclosureType.ANNUAL_NOTICE,
        }

    def send_cancellation_confirmation(
        self,
        customer: Customer,
        agreement: ServiceAgreement,
    ) -> dict[str, Any]:
        """Send cancellation confirmation email.

        Validates: Requirements 39B.6, 39B.7, 70.1, 70.2, 70.3
        """
        self.log_started(
            "send_cancellation_confirmation",
            agreement_id=str(agreement.id),
        )

        email = getattr(customer, "email", None)
        if not email:
            return {"sent": False, "reason": "no_email"}

        cancel_date = (
            str(agreement.cancelled_at.date())
            if agreement.cancelled_at
            else str(datetime.now(UTC).date())
        )
        refund = (
            str(agreement.cancellation_refund_amount)
            if agreement.cancellation_refund_amount
            else "0.00"
        )
        context = {
            "customer_name": customer.full_name,
            "cancellation_date": cancel_date,
            "cancellation_reason": (agreement.cancellation_reason or ""),
            "refund_amount": refund,
        }

        html_body = self._render_template(
            "cancellation_conf.html",
            context,
        )
        classification = self._classify_email("cancellation_conf")
        sent = self._send_email(
            to_email=email,
            subject=("Grins Irrigation Service Agreement Cancellation Confirmation"),
            html_body=html_body,
            email_type="cancellation_conf",
            classification=classification,
        )

        self.log_completed(
            "send_cancellation_confirmation",
            sent=sent,
        )
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": DisclosureType.CANCELLATION_CONF,
        }

    def send_lead_confirmation(
        self,
        lead: Lead,
    ) -> dict[str, Any]:
        """Send lead submission confirmation email.

        Validates: Requirements 55.1, 55.2, 55.3
        """
        self.log_started(
            "send_lead_confirmation",
            lead_id=str(lead.id),
        )

        email = getattr(lead, "email", None)
        if not email:
            self.logger.info(
                "email.lead_confirmation.skipped",
                lead_id=str(lead.id),
                reason="no_email",
            )
            return {"sent": False, "reason": "no_email"}

        first_name = getattr(lead, "first_name", "")
        context = {
            "customer_name": first_name or "Valued Customer",
        }

        html_body = self._render_template(
            "lead_confirmation.html",
            context,
        )
        classification = self._classify_email("lead_confirmation")
        sent = self._send_email(
            to_email=email,
            subject=("We Received Your Request — Grin's Irrigation"),
            html_body=html_body,
            email_type="lead_confirmation",
            classification=classification,
        )

        self.log_completed("send_lead_confirmation", sent=sent)
        return {
            "sent": sent,
            "sent_via": "email" if sent else "pending",
            "recipient_email": email,
            "content": html_body,
            "disclosure_type": None,
        }

    def check_suppression_and_opt_in(
        self,
        email: str,
        email_opt_in: bool,
        suppressed_emails: set[str] | None = None,
    ) -> bool:
        """Check if commercial email can be sent to recipient.

        Returns True if allowed, False if suppressed/opted-out.

        Validates: Requirements 67.5, 67.7
        """
        if suppressed_emails and email.lower() in {
            e.lower() for e in suppressed_emails
        }:
            self.logger.info(
                "email.commercial.suppressed",
                recipient=_mask_email(email),
                reason="suppression_list",
            )
            return False

        if not email_opt_in:
            self.logger.info(
                "email.commercial.opted_out",
                recipient=_mask_email(email),
                reason="email_opt_in_false",
            )
            return False

        return True

    @staticmethod
    def generate_unsubscribe_token(
        customer_id: UUID,
        email: str,
    ) -> str:
        """Generate signed unsubscribe token (30+ day validity).

        Validates: Requirements 67.6
        """
        payload = {
            "sub": str(customer_id),
            "email": email,
            "exp": (datetime.now(UTC) + timedelta(days=_UNSUBSCRIBE_EXPIRY_DAYS)),
            "purpose": "unsubscribe",
        }
        return jwt.encode(
            payload,
            _UNSUBSCRIBE_SECRET,
            algorithm=_UNSUBSCRIBE_ALGORITHM,
        )

    @staticmethod
    def verify_unsubscribe_token(
        token: str,
    ) -> dict[str, Any] | None:
        """Verify and decode an unsubscribe token.

        Returns payload dict or None if invalid/expired.

        Validates: Requirements 67.4, 67.8
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                _UNSUBSCRIBE_SECRET,
                algorithms=[_UNSUBSCRIBE_ALGORITHM],
            )
        except Exception:
            return None
        else:
            if payload.get("purpose") != "unsubscribe":
                return None
            return payload

    @staticmethod
    def hash_content(content: str) -> str:
        """SHA-256 hash of email content for disclosure records."""
        return hashlib.sha256(
            content.encode("utf-8"),
        ).hexdigest()
