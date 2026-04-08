"""Unit tests for CampaignService.

Tests campaign creation, consent-gated recipient filtering, CAN-SPAM
compliance, delivery stats, automation rule evaluation, and error handling.

Properties:
  P48: Campaign recipient filtering by consent

Validates: Requirements 45.5, 45.6, 45.11, 45.12
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from grins_platform.models.enums import CampaignStatus, CampaignType
from grins_platform.schemas.campaign import CampaignCreate
from grins_platform.services.campaign_service import (
    _DEFAULT_ADDRESS,
    CampaignAlreadySentError,
    CampaignNotFoundError,
    CampaignService,
    NoRecipientsError,
)
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSConsentDeniedError


def _recipient_from_customer(customer: MagicMock) -> Recipient:
    """Build a Recipient from a mock Customer."""
    return Recipient(
        phone=customer.phone,
        source_type="customer",
        customer_id=customer.id,
    )


# =============================================================================
# Helpers
# =============================================================================


def _make_campaign_mock(
    *,
    campaign_id: UUID | None = None,
    name: str = "Summer Promo",
    campaign_type: str = CampaignType.SMS.value,
    status: str = CampaignStatus.DRAFT.value,
    target_audience: dict[str, Any] | None = None,
    subject: str | None = None,
    body: str = "Check out our summer deals!",
    scheduled_at: datetime | None = None,
    sent_at: datetime | None = None,
    automation_rule: dict[str, Any] | None = None,
    created_by: UUID | None = None,
) -> MagicMock:
    """Create a mock Campaign."""
    c = MagicMock()
    c.id = campaign_id or uuid4()
    c.name = name
    c.campaign_type = campaign_type
    c.status = status
    c.target_audience = target_audience
    c.subject = subject
    c.body = body
    c.scheduled_at = scheduled_at
    c.sent_at = sent_at
    c.automation_rule = automation_rule
    c.created_by = created_by
    return c


def _make_customer_mock(
    *,
    customer_id: UUID | None = None,
    first_name: str = "Jane",
    last_name: str = "Smith",
    phone: str = "5125551234",
    email: str | None = "jane@example.com",
    sms_opt_in: bool = True,
    email_opt_in: bool = True,
    is_active: bool = True,
    lead_source: str | None = None,
) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.sms_opt_in = sms_opt_in
    c.email_opt_in = email_opt_in
    c.is_active = is_active
    c.lead_source = lead_source
    c.internal_notes = None
    c.preferred_service_times = None
    return c


def _recipient_from(c: MagicMock) -> Recipient:
    """Convert a customer mock to a Recipient."""
    return Recipient(
        phone=c.phone,
        source_type="customer",
        customer_id=c.id,
        first_name=c.first_name,
        last_name=c.last_name,
    )


def _scalar_result(value: Any) -> AsyncMock:
    """Create a mock DB execute result returning *value*."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _build_service(
    *,
    repo: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
) -> CampaignService:
    """Build a CampaignService with mocked dependencies."""
    return CampaignService(
        campaign_repository=repo or AsyncMock(),
        sms_service=sms_service,
        email_service=email_service,
    )


def _mock_db_with_business_address(
    address: str | None = None,
) -> AsyncMock:
    """Create a mock db session that returns a business address setting."""
    db = AsyncMock()
    if address is not None:
        setting = MagicMock()
        setting.setting_value = address
        result = MagicMock()
        result.scalar_one_or_none.return_value = setting
    else:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return db


# =============================================================================
# Property 48: Campaign recipient filtering by consent
# Validates: Requirements 45.5, 45.6
# =============================================================================


@pytest.mark.unit
class TestProperty48CampaignRecipientFilteringByConsent:
    """Property 48: Campaign recipient filtering by consent.

    For any campaign send, recipients shall be filtered by target_audience
    criteria. For SMS campaigns, customers without sms_opt_in=True shall
    be skipped. For email campaigns, customers who opted out shall be
    skipped. The delivery stats shall accurately reflect sent, skipped,
    and failed counts.

    **Validates: Requirements 45.6, 45.5**
    """

    # ----------------------------------------------------------------
    # 1. create_campaign creates with DRAFT status
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_campaign_with_valid_data_returns_draft_status(
        self,
    ) -> None:
        """Campaign creation always starts in DRAFT status."""
        repo = AsyncMock()
        created_campaign = _make_campaign_mock(
            status=CampaignStatus.DRAFT.value,
        )
        repo.create.return_value = created_campaign

        svc = _build_service(repo=repo)
        data = CampaignCreate(
            name="Fall Promo",
            campaign_type=CampaignType.SMS,
            body="Fall deals are here!",
        )

        result = await svc.create_campaign(data, created_by=uuid4())

        assert result.status == CampaignStatus.DRAFT.value
        repo.create.assert_called_once()
        call_kwargs = repo.create.call_args.kwargs
        assert call_kwargs["status"] == CampaignStatus.DRAFT.value
        assert call_kwargs["name"] == "Fall Promo"
        assert call_kwargs["campaign_type"] == CampaignType.SMS.value

    # ----------------------------------------------------------------
    # 2. send_campaign filters recipients by consent (SMS)
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_sms_type_skips_non_sms_consented(
        self,
    ) -> None:
        """SMS campaigns skip customers denied by centralized consent check (B2)."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.SMS.value,
            status=CampaignStatus.DRAFT.value,
        )
        consented = _make_customer_mock(sms_opt_in=True)
        non_consented = _make_customer_mock(sms_opt_in=False)

        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.update.return_value = campaign

        sms_service = AsyncMock()
        # First call succeeds (consented), second raises consent denied
        sms_service.send_message.side_effect = [
            {"success": True},
            SMSConsentDeniedError("Consent denied"),
        ]

        svc = _build_service(repo=repo, sms_service=sms_service)

        db = AsyncMock()
        # DB returns Customer mocks for email channel resolution
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(consented),
                _scalar_result(non_consented),
            ],
        )

        with (
            patch.object(
                svc,
                "_get_business_address",
                return_value=_DEFAULT_ADDRESS,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[
                    _recipient_from(consented),
                    _recipient_from(non_consented),
                ],
            ),
        ):
            result = await svc.send_campaign(db, campaign.id)

        assert result.sent == 1
        assert result.skipped == 0
        assert result.failed == 1
        assert result.total_recipients == 2
        # Verify opted_out recipient was recorded
        repo.add_recipient.assert_any_call(
            campaign_id=campaign.id,
            customer_id=non_consented.id,
            lead_id=None,
            channel="sms",
            delivery_status="opted_out",
        )

    # ----------------------------------------------------------------
    # 3. send_campaign filters recipients by consent (EMAIL)
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_email_type_skips_non_email_consented(
        self,
    ) -> None:
        """Email campaigns skip customers without email_opt_in."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.EMAIL.value,
            status=CampaignStatus.DRAFT.value,
            subject="Deals!",
        )
        consented = _make_customer_mock(
            email_opt_in=True,
            email="yes@example.com",
        )
        no_consent = _make_customer_mock(
            email_opt_in=False,
            email="no@example.com",
        )
        no_email = _make_customer_mock(
            email_opt_in=True,
            email=None,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.update.return_value = campaign

        email_service = MagicMock()
        email_service._send_email.return_value = True

        svc = _build_service(repo=repo, email_service=email_service)

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(consented),
                _scalar_result(no_consent),
                _scalar_result(no_email),
            ],
        )

        with (
            patch.object(
                svc,
                "_get_business_address",
                return_value=_DEFAULT_ADDRESS,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[
                    _recipient_from(consented),
                    _recipient_from(no_consent),
                    _recipient_from(no_email),
                ],
            ),
        ):
            result = await svc.send_campaign(db, campaign.id)

        # consented sends, no_consent skipped, no_email skipped (no email addr)
        assert result.sent == 1
        assert result.skipped == 2
        assert result.total_recipients == 3

    # ----------------------------------------------------------------
    # 4. send_campaign with BOTH type respects per-channel consent
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_both_type_respects_per_channel_consent(
        self,
    ) -> None:
        """BOTH campaigns send on each channel; SMS consent via SMSService (B2)."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.BOTH.value,
            status=CampaignStatus.DRAFT.value,
            subject="Deals!",
        )
        # Customer with both consents
        both = _make_customer_mock(
            sms_opt_in=True,
            email_opt_in=True,
            email="both@example.com",
        )
        # Customer with only SMS consent
        sms_only = _make_customer_mock(
            sms_opt_in=True,
            email_opt_in=False,
            email="sms@example.com",
        )
        # Customer with neither — SMS consent denied by SMSService
        neither = _make_customer_mock(
            sms_opt_in=False,
            email_opt_in=False,
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.update.return_value = campaign

        sms_service = AsyncMock()
        # both: success, sms_only: success, neither: consent denied
        sms_service.send_message.side_effect = [
            {"success": True},
            {"success": True},
            SMSConsentDeniedError("Consent denied"),
        ]
        email_service = MagicMock()
        email_service._send_email.return_value = True

        svc = _build_service(
            repo=repo,
            sms_service=sms_service,
            email_service=email_service,
        )

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(both),
                _scalar_result(sms_only),
                _scalar_result(neither),
            ],
        )

        with (
            patch.object(
                svc,
                "_get_business_address",
                return_value=_DEFAULT_ADDRESS,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[
                    _recipient_from(both),
                    _recipient_from(sms_only),
                    _recipient_from(neither),
                ],
            ),
        ):
            result = await svc.send_campaign(db, campaign.id)

        # both: sms(sent) + email(sent) = 2 sent
        # sms_only: sms(sent) = 1 sent, no email channel (no email_opt_in)
        # neither: sms(consent denied → opted_out, counted as failed)
        #          no email channel (no email_opt_in)
        assert result.sent == 3
        assert result.skipped == 0
        assert result.failed == 1
        assert result.total_recipients == 3

    # ----------------------------------------------------------------
    # 5. send_campaign appends CAN-SPAM footer
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_email_appends_can_spam_footer(
        self,
    ) -> None:
        """Email campaigns append physical address + unsubscribe link."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.EMAIL.value,
            status=CampaignStatus.DRAFT.value,
            subject="Promo",
            body="Great deals!",
        )
        customer = _make_customer_mock(
            email_opt_in=True,
            email="test@example.com",
        )

        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.update.return_value = campaign

        email_service = MagicMock()
        email_service._send_email.return_value = True

        svc = _build_service(repo=repo, email_service=email_service)
        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(customer),
            ],
        )

        biz_addr = "123 Main St, Austin TX 78701"
        with (
            patch.object(
                svc,
                "_get_business_address",
                return_value=biz_addr,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[_recipient_from(customer)],
            ),
        ):
            await svc.send_campaign(db, campaign.id)

        # Verify the email body sent includes the CAN-SPAM footer
        email_service._send_email.assert_called_once()
        call_kwargs = email_service._send_email.call_args.kwargs
        sent_body = call_kwargs["html_body"]
        assert "123 Main St, Austin TX 78701" in sent_body
        assert "unsubscribe" in sent_body.lower()

    # ----------------------------------------------------------------
    # 6. send_campaign raises CampaignAlreadySentError
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_already_sent_raises_error(
        self,
    ) -> None:
        """Sending an already-sent campaign raises CampaignAlreadySentError."""
        campaign = _make_campaign_mock(
            status=CampaignStatus.SENT.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = campaign

        svc = _build_service(repo=repo)
        db = AsyncMock()

        with pytest.raises(CampaignAlreadySentError) as exc_info:
            await svc.send_campaign(db, campaign.id)

        assert exc_info.value.campaign_id == campaign.id

    @pytest.mark.asyncio
    async def test_send_campaign_with_sending_status_raises_error(
        self,
    ) -> None:
        """Sending a campaign in SENDING status raises CampaignAlreadySentError."""
        campaign = _make_campaign_mock(
            status=CampaignStatus.SENDING.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = campaign

        svc = _build_service(repo=repo)
        db = AsyncMock()

        with pytest.raises(CampaignAlreadySentError):
            await svc.send_campaign(db, campaign.id)

    # ----------------------------------------------------------------
    # 7. send_campaign raises CampaignNotFoundError
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_missing_campaign_raises_not_found(
        self,
    ) -> None:
        """Sending a non-existent campaign raises CampaignNotFoundError."""
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = _build_service(repo=repo)
        db = AsyncMock()
        missing_id = uuid4()

        with pytest.raises(CampaignNotFoundError) as exc_info:
            await svc.send_campaign(db, missing_id)

        assert exc_info.value.campaign_id == missing_id

    # ----------------------------------------------------------------
    # 8. send_campaign raises NoRecipientsError
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_campaign_with_no_matching_recipients_raises_error(
        self,
    ) -> None:
        """Sending to an empty audience raises NoRecipientsError."""
        campaign = _make_campaign_mock(
            status=CampaignStatus.DRAFT.value,
        )
        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.update.return_value = campaign

        svc = _build_service(repo=repo)
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_business_address",
                return_value=_DEFAULT_ADDRESS,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[],
            ),
            pytest.raises(NoRecipientsError) as exc_info,
        ):
            await svc.send_campaign(db, campaign.id)

        assert exc_info.value.campaign_id == campaign.id
        # Verify status reverted to DRAFT
        repo.update.assert_any_call(
            campaign.id,
            status=CampaignStatus.DRAFT.value,
        )

    # ----------------------------------------------------------------
    # 9. get_campaign_stats returns correct delivery metric counts
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_campaign_stats_with_valid_campaign_returns_counts(
        self,
    ) -> None:
        """Stats endpoint returns correct delivery metric counts."""
        campaign = _make_campaign_mock()
        repo = AsyncMock()
        repo.get_by_id.return_value = campaign
        repo.get_campaign_stats.return_value = {
            "total": 10,
            "sent": 7,
            "delivered": 5,
            "failed": 2,
            "bounced": 1,
            "opted_out": 0,
        }

        svc = _build_service(repo=repo)
        stats = await svc.get_campaign_stats(campaign.id)

        assert stats.campaign_id == campaign.id
        assert stats.total == 10
        assert stats.sent == 7
        assert stats.delivered == 5
        assert stats.failed == 2
        assert stats.bounced == 1
        assert stats.opted_out == 0

    # ----------------------------------------------------------------
    # 10. get_campaign_stats raises CampaignNotFoundError
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_campaign_stats_with_missing_campaign_raises_not_found(
        self,
    ) -> None:
        """Stats for non-existent campaign raises CampaignNotFoundError."""
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = _build_service(repo=repo)
        missing_id = uuid4()

        with pytest.raises(CampaignNotFoundError) as exc_info:
            await svc.get_campaign_stats(missing_id)

        assert exc_info.value.campaign_id == missing_id

    # ----------------------------------------------------------------
    # 11. evaluate_automation_rules triggers campaigns based on frequency
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_automation_rules_with_due_rule_triggers_campaign(
        self,
    ) -> None:
        """Automation rules that are due get triggered."""
        template_campaign = _make_campaign_mock(
            name="Weekly Reminder",
            campaign_type=CampaignType.SMS.value,
            automation_rule={
                "trigger": "no_appointment_in_days",
                "days": 90,
                "frequency": "weekly",
                "last_triggered_at": (
                    datetime.now(tz=timezone.utc) - timedelta(days=8)
                ).isoformat(),
            },
        )

        new_campaign = _make_campaign_mock(
            name="Weekly Reminder — Auto 2025-07-20",
            campaign_type=CampaignType.SMS.value,
            status=CampaignStatus.DRAFT.value,
        )

        repo = AsyncMock()
        repo.create.return_value = new_campaign
        repo.get_by_id.return_value = new_campaign
        repo.update.return_value = new_campaign

        customer = _make_customer_mock(sms_opt_in=True)
        sms_service = AsyncMock()
        sms_service.send_message.return_value = {"success": True}

        svc = _build_service(repo=repo, sms_service=sms_service)

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[
                _scalar_result(customer),
            ],
        )

        with (
            patch.object(
                svc,
                "_get_campaigns_with_rules",
                return_value=[template_campaign],
            ),
            patch.object(
                svc,
                "_get_business_address",
                return_value=_DEFAULT_ADDRESS,
            ),
            patch.object(
                svc,
                "_filter_recipients",
                return_value=[_recipient_from(customer)],
            ),
        ):
            triggered = await svc.evaluate_automation_rules(db)

        assert triggered == 1
        repo.create.assert_called_once()

    # ----------------------------------------------------------------
    # 12. evaluate_automation_rules skips recently triggered rules
    # ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_evaluate_automation_rules_with_recent_trigger_skips(
        self,
    ) -> None:
        """Rules triggered recently are not re-triggered."""
        template_campaign = _make_campaign_mock(
            automation_rule={
                "trigger": "no_appointment_in_days",
                "days": 90,
                "frequency": "weekly",
                "last_triggered_at": (
                    datetime.now(tz=timezone.utc) - timedelta(days=2)
                ).isoformat(),
            },
        )

        repo = AsyncMock()
        svc = _build_service(repo=repo)

        db = AsyncMock()

        with patch.object(
            svc,
            "_get_campaigns_with_rules",
            return_value=[template_campaign],
        ):
            triggered = await svc.evaluate_automation_rules(db)

        assert triggered == 0
        repo.create.assert_not_called()

    # ----------------------------------------------------------------
    # 13. _should_trigger with daily/weekly/monthly frequencies
    # ----------------------------------------------------------------

    def test_should_trigger_with_daily_frequency_after_one_day(self) -> None:
        """Daily rule triggers after 1+ day."""
        rule = {
            "frequency": "daily",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=1, hours=1)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is True

    def test_should_trigger_with_daily_frequency_within_one_day(self) -> None:
        """Daily rule does not trigger within 1 day."""
        rule = {
            "frequency": "daily",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(hours=12)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is False

    def test_should_trigger_with_weekly_frequency_after_seven_days(
        self,
    ) -> None:
        """Weekly rule triggers after 7+ days."""
        rule = {
            "frequency": "weekly",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=8)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is True

    def test_should_trigger_with_weekly_frequency_within_seven_days(
        self,
    ) -> None:
        """Weekly rule does not trigger within 7 days."""
        rule = {
            "frequency": "weekly",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=5)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is False

    def test_should_trigger_with_monthly_frequency_after_thirty_days(
        self,
    ) -> None:
        """Monthly rule triggers after 30+ days."""
        rule = {
            "frequency": "monthly",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=31)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is True

    def test_should_trigger_with_monthly_frequency_within_thirty_days(
        self,
    ) -> None:
        """Monthly rule does not trigger within 30 days."""
        rule = {
            "frequency": "monthly",
            "last_triggered_at": (
                datetime.now(tz=timezone.utc) - timedelta(days=15)
            ).isoformat(),
        }
        assert CampaignService._should_trigger(rule) is False

    def test_should_trigger_with_no_last_triggered_returns_true(
        self,
    ) -> None:
        """Rule with no last_triggered_at always triggers."""
        rule: dict[str, Any] = {"frequency": "weekly"}
        assert CampaignService._should_trigger(rule) is True

    def test_should_trigger_with_invalid_timestamp_returns_true(
        self,
    ) -> None:
        """Rule with unparseable last_triggered_at triggers."""
        rule = {"frequency": "daily", "last_triggered_at": "not-a-date"}
        assert CampaignService._should_trigger(rule) is True

    # ----------------------------------------------------------------
    # 14. _resolve_channels returns correct channels based on consent
    # ----------------------------------------------------------------

    def test_resolve_channels_with_sms_campaign_and_sms_consent(
        self,
    ) -> None:
        """SMS campaign returns ['sms'] regardless of sms_opt_in (B2 fix)."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.SMS.value,
        )
        customer = _make_customer_mock(sms_opt_in=True)
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == ["sms"]

    def test_resolve_channels_with_sms_campaign_and_no_sms_consent(
        self,
    ) -> None:
        """SMS campaign still returns ['sms'] — consent checked downstream (B2 fix)."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.SMS.value,
        )
        customer = _make_customer_mock(sms_opt_in=False)
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == ["sms"]

    def test_resolve_channels_with_email_campaign_and_email_consent(
        self,
    ) -> None:
        """Email campaign + email_opt_in + email returns ['email']."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.EMAIL.value,
        )
        customer = _make_customer_mock(
            email_opt_in=True,
            email="test@example.com",
        )
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == ["email"]

    def test_resolve_channels_with_email_campaign_and_no_email(
        self,
    ) -> None:
        """Email campaign + email_opt_in but no email address returns []."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.EMAIL.value,
        )
        customer = _make_customer_mock(email_opt_in=True, email=None)
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == []

    def test_resolve_channels_with_both_campaign_and_full_consent(
        self,
    ) -> None:
        """BOTH campaign + both consents returns ['sms', 'email']."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.BOTH.value,
        )
        customer = _make_customer_mock(
            sms_opt_in=True,
            email_opt_in=True,
            email="test@example.com",
        )
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == ["sms", "email"]

    def test_resolve_channels_with_both_campaign_and_no_consent(
        self,
    ) -> None:
        """BOTH campaign + no consent returns ['sms'] — consent downstream (B2)."""
        campaign = _make_campaign_mock(
            campaign_type=CampaignType.BOTH.value,
        )
        customer = _make_customer_mock(
            sms_opt_in=False,
            email_opt_in=False,
        )
        recipient = _recipient_from_customer(customer)
        channels = CampaignService._resolve_channels(
            campaign,
            recipient,
            customer,
        )
        assert channels == ["sms"]

    # ----------------------------------------------------------------
    # 15. _apply_can_spam appends correct footer
    # ----------------------------------------------------------------

    def test_apply_can_spam_with_address_appends_footer(self) -> None:
        """CAN-SPAM footer includes physical address and unsubscribe."""
        body = "Hello, check out our deals!"
        address = "123 Main St, Austin TX 78701"
        result = CampaignService._apply_can_spam(body, address)

        assert result.startswith(body)
        assert address in result
        assert "unsubscribe" in result.lower()
        assert "STOP" in result

    def test_apply_can_spam_with_default_address(self) -> None:
        """CAN-SPAM footer works with default address."""
        body = "Promo message"
        result = CampaignService._apply_can_spam(body, _DEFAULT_ADDRESS)

        assert _DEFAULT_ADDRESS in result
        assert "unsubscribe" in result.lower()
