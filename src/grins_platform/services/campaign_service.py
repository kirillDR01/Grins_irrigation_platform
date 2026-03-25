"""Campaign management service for marketing campaigns.

Handles campaign creation, sending with consent gating, delivery stats,
and automation rule evaluation.

Validates: CRM Gap Closure Req 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9, 45.10
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.business_setting import BusinessSetting
from grins_platform.models.campaign import Campaign
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    CampaignStatus,
    CampaignType,
    EmailType,
    NotificationType,
)
from grins_platform.schemas.ai import MessageType
from grins_platform.schemas.campaign import (
    CampaignCreate,
    CampaignSendResult,
    CampaignStats,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.campaign_repository import (
        CampaignRepository,
    )
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.sms_service import SMSService


# Default CAN-SPAM unsubscribe text appended to every campaign message
_UNSUBSCRIBE_TEXT = "\n\nTo unsubscribe, reply STOP or contact us at the address above."

# Default physical address fallback when business setting is missing
_DEFAULT_ADDRESS = "Grin's Irrigations"


class CampaignAlreadySentError(Exception):
    """Raised when attempting to send an already-sent campaign."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id} has already been sent or is sending.",
        )


class CampaignNotFoundError(Exception):
    """Raised when a campaign is not found."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(f"Campaign {campaign_id} not found.")


class NoRecipientsError(Exception):
    """Raised when target audience filter matches zero customers."""

    def __init__(self, campaign_id: UUID) -> None:
        self.campaign_id = campaign_id
        super().__init__(
            f"Campaign {campaign_id}: target audience matched zero recipients.",
        )


class CampaignService(LoggerMixin):
    """Service for marketing campaign lifecycle management.

    Handles creation, consent-gated sending, delivery statistics,
    and recurring automation rule evaluation.

    Validates: CRM Gap Closure Req 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9, 45.10
    """

    DOMAIN = "campaign"

    def __init__(
        self,
        campaign_repository: CampaignRepository,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        """Initialize CampaignService with dependencies.

        Args:
            campaign_repository: Repository for campaign DB ops.
            sms_service: Optional SMSService for SMS campaigns.
            email_service: Optional EmailService for email campaigns.
        """
        super().__init__()
        self.repo = campaign_repository
        self.sms_service = sms_service
        self.email_service = email_service

    # ================================================================
    # create_campaign — Req 45.3
    # ================================================================

    async def create_campaign(
        self,
        data: CampaignCreate,
        created_by: UUID | None = None,
    ) -> Campaign:
        """Create a new campaign in DRAFT status.

        Args:
            data: Campaign creation payload.
            created_by: Staff UUID who created the campaign.

        Returns:
            The newly created Campaign record.

        Validates: CRM Gap Closure Req 45.3
        """
        self.log_started(
            "create_campaign",
            name=data.name,
            campaign_type=data.campaign_type.value,
        )

        campaign = await self.repo.create(
            name=data.name,
            campaign_type=data.campaign_type.value,
            status=CampaignStatus.DRAFT.value,
            target_audience=data.target_audience,
            subject=data.subject,
            body=data.body,
            scheduled_at=data.scheduled_at,
            created_by=created_by,
        )

        self.log_completed(
            "create_campaign",
            campaign_id=str(campaign.id),
        )
        return campaign

    # ================================================================
    # send_campaign — Req 45.4, 45.6, 45.7, 45.8
    # ================================================================

    async def send_campaign(
        self,
        db: AsyncSession,
        campaign_id: UUID,
    ) -> CampaignSendResult:
        """Send a campaign to filtered recipients with consent gating.

        Filters recipients by target_audience criteria, skips customers
        without SMS consent (for SMS) and customers who opted out of
        email (for email). Enforces CAN-SPAM compliance by appending
        physical address and unsubscribe link.

        Designed to be called as a background job (Req 45.7).

        Args:
            db: Async database session (for audience queries).
            campaign_id: UUID of the campaign to send.

        Returns:
            CampaignSendResult with delivery counts.

        Raises:
            CampaignNotFoundError: Campaign does not exist.
            CampaignAlreadySentError: Campaign already sent/sending.
            NoRecipientsError: No recipients match audience filter.

        Validates: CRM Gap Closure Req 45.4, 45.6, 45.7, 45.8
        """
        self.log_started("send_campaign", campaign_id=str(campaign_id))

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "send_campaign",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        if campaign.status in (
            CampaignStatus.SENT.value,
            CampaignStatus.SENDING.value,
        ):
            self.log_rejected(
                "send_campaign",
                reason="already_sent",
                campaign_id=str(campaign_id),
                status=campaign.status,
            )
            raise CampaignAlreadySentError(campaign_id)

        # Transition to SENDING
        await self.repo.update(
            campaign_id,
            status=CampaignStatus.SENDING.value,
        )

        # Fetch business address for CAN-SPAM (Req 45.8)
        business_address = await self._get_business_address(db)

        # Build recipients from target audience filter
        recipients = await self._filter_recipients(db, campaign)

        if not recipients:
            await self.repo.update(
                campaign_id,
                status=CampaignStatus.DRAFT.value,
            )
            self.log_rejected(
                "send_campaign",
                reason="no_recipients",
                campaign_id=str(campaign_id),
            )
            raise NoRecipientsError(campaign_id)

        sent = 0
        skipped = 0
        failed = 0

        for customer in recipients:
            channels = self._resolve_channels(campaign, customer)

            if not channels:
                skipped += 1
                self.logger.info(
                    "campaign.campaignservice.send_skipped",
                    campaign_id=str(campaign_id),
                    customer_id=str(customer.id),
                    reason="no_consented_channel",
                )
                await self.repo.add_recipient(
                    campaign_id=campaign_id,
                    customer_id=customer.id,
                    channel=campaign.campaign_type,
                    delivery_status="opted_out",
                )
                continue

            for channel in channels:
                ok = await self._send_to_recipient(
                    campaign=campaign,
                    customer=customer,
                    channel=channel,
                    business_address=business_address,
                )
                if ok:
                    sent += 1
                else:
                    failed += 1

        # Transition to SENT
        now = datetime.now(tz=timezone.utc)
        await self.repo.update(
            campaign_id,
            status=CampaignStatus.SENT.value,
            sent_at=now,
        )

        self.log_completed(
            "send_campaign",
            campaign_id=str(campaign_id),
            total_recipients=len(recipients),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )

        return CampaignSendResult(
            campaign_id=campaign_id,
            total_recipients=len(recipients),
            sent=sent,
            skipped=skipped,
            failed=failed,
        )

    # ================================================================
    # get_campaign_stats — Req 45.5
    # ================================================================

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
    ) -> CampaignStats:
        """Get delivery statistics for a campaign.

        Aggregates recipient delivery statuses from campaign_recipients.

        Args:
            campaign_id: UUID of the campaign.

        Returns:
            CampaignStats with delivery metric counts.

        Raises:
            CampaignNotFoundError: If campaign does not exist.

        Validates: CRM Gap Closure Req 45.5
        """
        self.log_started(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
        )

        campaign = await self.repo.get_by_id(campaign_id)
        if campaign is None:
            self.log_failed(
                "get_campaign_stats",
                error=CampaignNotFoundError(campaign_id),
            )
            raise CampaignNotFoundError(campaign_id)

        stats_dict = await self.repo.get_campaign_stats(campaign_id)

        result = CampaignStats(
            campaign_id=campaign_id,
            total=stats_dict.get("total", 0),
            sent=stats_dict.get("sent", 0),
            delivered=stats_dict.get("delivered", 0),
            failed=stats_dict.get("failed", 0),
            bounced=stats_dict.get("bounced", 0),
            opted_out=stats_dict.get("opted_out", 0),
        )

        self.log_completed(
            "get_campaign_stats",
            campaign_id=str(campaign_id),
            total=result.total,
        )
        return result

    # ================================================================
    # evaluate_automation_rules — Req 45.10
    # ================================================================

    async def evaluate_automation_rules(
        self,
        db: AsyncSession,
    ) -> int:
        """Evaluate recurring automation rules and trigger campaigns.

        Runs as a daily background job. Scans all campaigns with
        automation_rule set, evaluates the trigger criteria, and
        creates + sends new campaign instances for matching rules.

        Example automation_rule JSONB::

            {
                "trigger": "no_appointment_in_days",
                "days": 90,
                "frequency": "weekly",
                "last_triggered_at": "2025-01-01T00:00:00Z",
            }

        Args:
            db: Async database session.

        Returns:
            Number of campaigns triggered.

        Validates: CRM Gap Closure Req 45.10
        """
        self.log_started("evaluate_automation_rules")

        campaigns_with_rules = await self._get_campaigns_with_rules(db)
        triggered_count = 0

        for campaign in campaigns_with_rules:
            rule = campaign.automation_rule
            if rule is None:
                continue

            if not self._should_trigger(rule):
                continue

            try:
                now_str = datetime.now(tz=timezone.utc).strftime(
                    "%Y-%m-%d",
                )
                new_campaign = await self.repo.create(
                    name=f"{campaign.name} — Auto {now_str}",
                    campaign_type=campaign.campaign_type,
                    status=CampaignStatus.DRAFT.value,
                    target_audience=campaign.target_audience,
                    subject=campaign.subject,
                    body=campaign.body,
                    created_by=campaign.created_by,
                )

                await self.send_campaign(db, new_campaign.id)

                # Update last_triggered_at on the template
                updated_rule: dict[str, Any] = {**rule}
                updated_rule["last_triggered_at"] = datetime.now(
                    tz=timezone.utc,
                ).isoformat()
                await self.repo.update(
                    campaign.id,
                    automation_rule=updated_rule,
                )

                triggered_count += 1

                self.logger.info(
                    "campaign.campaignservice.automation_triggered",
                    template_id=str(campaign.id),
                    new_id=str(new_campaign.id),
                    trigger=rule.get("trigger", "unknown"),
                )

            except (
                NoRecipientsError,
                CampaignAlreadySentError,
            ) as exc:
                self.logger.warning(
                    "campaign.campaignservice.automation_skipped",
                    template_id=str(campaign.id),
                    reason=str(exc),
                )
            except Exception as exc:
                self.log_failed(
                    "evaluate_automation_rules",
                    error=exc,
                )

        self.log_completed(
            "evaluate_automation_rules",
            triggered_count=triggered_count,
        )
        return triggered_count

    # ================================================================
    # Private helpers
    # ================================================================

    async def _get_business_address(
        self,
        db: AsyncSession,
    ) -> str:
        """Fetch physical business address for CAN-SPAM.

        Validates: CRM Gap Closure Req 45.8
        """
        stmt = select(BusinessSetting).where(
            BusinessSetting.setting_key == "company_address",
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting and setting.setting_value:
            val = setting.setting_value
            if isinstance(val, str) and val.strip():
                return val.strip()
        return _DEFAULT_ADDRESS

    async def _filter_recipients(
        self,
        db: AsyncSession,
        campaign: Campaign,
    ) -> list[Customer]:
        """Filter customers by target_audience criteria.

        Supports filter keys:
        - lead_source: match customer.lead_source
        - is_active: match customer.is_active
        - no_appointment_in_days: no appointment in N days
        - (empty/None): all active customers

        Validates: CRM Gap Closure Req 45.6
        """
        from grins_platform.models.appointment import (  # noqa: PLC0415
            Appointment,
        )

        base_query = select(Customer).where(
            Customer.is_active.is_(True),
        )
        audience = campaign.target_audience or {}

        if audience.get("lead_source"):
            base_query = base_query.where(
                Customer.lead_source == audience["lead_source"],
            )

        if audience.get("is_active") is not None:
            base_query = base_query.where(
                Customer.is_active.is_(audience["is_active"]),
            )

        result = await db.execute(base_query)
        customers: list[Customer] = list(result.scalars().all())

        # Post-filter: no_appointment_in_days
        days_threshold = audience.get("no_appointment_in_days")
        if days_threshold is not None and isinstance(
            days_threshold,
            int,
        ):
            cutoff = datetime.now(tz=timezone.utc) - timedelta(
                days=days_threshold,
            )
            filtered: list[Customer] = []
            for customer in customers:
                appt_stmt = (
                    select(Appointment.id)
                    .where(
                        Appointment.customer_id == customer.id,
                    )
                    .where(Appointment.scheduled_start >= cutoff)
                    .limit(1)
                )
                appt_result = await db.execute(appt_stmt)
                if appt_result.scalar_one_or_none() is None:
                    filtered.append(customer)
            customers = filtered

        return customers

    @staticmethod
    def _resolve_channels(
        campaign: Campaign,
        customer: Customer,
    ) -> list[str]:
        """Determine channels for a customer based on consent.

        SMS requires sms_opt_in. Email requires email_opt_in.

        Validates: CRM Gap Closure Req 45.6
        """
        channels: list[str] = []
        ctype = campaign.campaign_type

        if (
            ctype
            in (
                CampaignType.SMS.value,
                CampaignType.BOTH.value,
            )
            and customer.sms_opt_in
        ):
            channels.append("sms")

        if (
            ctype
            in (
                CampaignType.EMAIL.value,
                CampaignType.BOTH.value,
            )
            and customer.email_opt_in
            and customer.email
        ):
            channels.append("email")

        return channels

    async def _send_to_recipient(
        self,
        *,
        campaign: Campaign,
        customer: Customer,
        channel: str,
        business_address: str,
    ) -> bool:
        """Send a campaign message to one recipient on one channel.

        Appends CAN-SPAM footer (physical address + unsubscribe).
        Records a CampaignRecipient row for tracking.

        Returns True if sent successfully, False otherwise.

        Validates: CRM Gap Closure Req 45.4, 45.8
        """
        compliant_body = self._apply_can_spam(
            campaign.body,
            business_address,
        )

        success = False

        if channel == "sms" and self.sms_service is not None:
            try:
                sms_result = await self.sms_service.send_message(
                    customer_id=customer.id,
                    phone=customer.phone,
                    message=compliant_body,
                    message_type=MessageType.CAMPAIGN,
                    sms_opt_in=True,
                )
                success = sms_result.get("success", False)
            except Exception as exc:
                self.log_failed(
                    "send_to_recipient_sms",
                    error=exc,
                    campaign_id=str(campaign.id),
                    customer_id=str(customer.id),
                )

        elif channel == "email" and self.email_service is not None:
            try:
                success = self.email_service._send_email(  # noqa: SLF001
                    to_email=customer.email or "",
                    subject=campaign.subject or campaign.name,
                    html_body=compliant_body,
                    email_type=NotificationType.CAMPAIGN.value,
                    classification=EmailType.COMMERCIAL,
                )
            except Exception as exc:
                self.log_failed(
                    "send_to_recipient_email",
                    error=exc,
                    campaign_id=str(campaign.id),
                    customer_id=str(customer.id),
                )

        # Record recipient
        delivery_status = "sent" if success else "failed"
        sent_at = datetime.now(tz=timezone.utc) if success else None

        await self.repo.add_recipient(
            campaign_id=campaign.id,
            customer_id=customer.id,
            channel=channel,
            delivery_status=delivery_status,
            sent_at=sent_at,
            error_message=None if success else "delivery_failed",
        )

        return success

    @staticmethod
    def _apply_can_spam(body: str, business_address: str) -> str:
        """Append CAN-SPAM physical address and unsubscribe link.

        Validates: CRM Gap Closure Req 45.8
        """
        footer = f"\n\n{business_address}{_UNSUBSCRIBE_TEXT}"
        return body + footer

    async def _get_campaigns_with_rules(
        self,
        db: AsyncSession,
    ) -> list[Campaign]:
        """Fetch campaigns that have automation_rule set."""
        stmt = (
            select(Campaign)
            .where(Campaign.automation_rule.isnot(None))
            .where(
                Campaign.status.in_(
                    [
                        CampaignStatus.DRAFT.value,
                        CampaignStatus.SENT.value,
                    ],
                ),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _should_trigger(rule: dict[str, Any]) -> bool:
        """Check if an automation rule is due based on frequency.

        Supported frequencies: daily, weekly, monthly.
        """
        frequency = rule.get("frequency", "weekly")
        last_triggered = rule.get("last_triggered_at")

        if last_triggered is None:
            return True

        try:
            last_dt = datetime.fromisoformat(str(last_triggered))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return True

        now = datetime.now(tz=timezone.utc)
        elapsed = now - last_dt

        frequency_map: dict[str, int] = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
        }
        required_days = frequency_map.get(frequency, 7)

        return elapsed >= timedelta(days=required_days)
