"""SMS Service for customer communications.

Validates: AI Assistant Requirements 12.1-12.10
Validates: Requirements 8.1-8.6, 9.1-9.5
"""

import os
import re
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import DeliveryStatus, MessageType

logger = get_logger(__name__)

# Exact opt-out keywords (Req 8.1)
EXACT_OPT_OUT_KEYWORDS: frozenset[str] = frozenset(
    {"stop", "quit", "cancel", "unsubscribe", "end", "revoke"},
)

# Informal opt-out phrases (Req 8.5)
INFORMAL_OPT_OUT_PHRASES: tuple[str, ...] = (
    "stop texting me",
    "take me off the list",
    "no more texts",
    "opt out",
    "don't text me",
)

# Central timezone for time window enforcement
CT_TZ = ZoneInfo("America/Chicago")

# Opt-out confirmation message
OPT_OUT_CONFIRMATION_MSG = (
    "You've been unsubscribed from Grins Irrigation texts. Reply START to re-subscribe."
)


class SMSError(Exception):
    """Base exception for SMS errors."""


class SMSOptInError(SMSError):
    """Raised when customer has not opted in to SMS."""


class SMSService(LoggerMixin):
    """Service for sending SMS messages via Twilio."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize SMS service.

        Args:
            session: Database session
        """
        super().__init__()
        self.session = session
        self.message_repo = SentMessageRepository(session)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")

    async def send_message(
        self,
        customer_id: UUID,
        phone: str,
        message: str,
        message_type: MessageType,
        sms_opt_in: bool = False,
        job_id: UUID | None = None,
        appointment_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Send an SMS message to a customer.

        Args:
            customer_id: Customer ID
            phone: Phone number
            message: Message content
            message_type: Type of message
            sms_opt_in: Whether customer has opted in
            job_id: Optional job ID
            appointment_id: Optional appointment ID

        Returns:
            Result with message ID and status

        Raises:
            SMSOptInError: If customer has not opted in
            SMSError: If sending fails
        """
        self.log_started(
            "send_message",
            customer_id=str(customer_id),
            message_type=message_type.value,
        )

        # Check opt-in
        if not sms_opt_in:
            self.log_rejected("send_message", reason="not_opted_in")
            msg = "Customer has not opted in to SMS messages"
            raise SMSOptInError(msg)

        # Check for duplicate messages within 24 hours (Requirement 7.7)
        recent_messages = await self.message_repo.get_by_customer_and_type(
            customer_id=customer_id,
            message_type=message_type,
            hours_back=24,
        )

        if recent_messages:
            self.log_rejected(
                "send_message",
                reason="duplicate_message_within_24_hours",
                recent_message_id=str(recent_messages[0].id),
            )
            return {
                "success": False,
                "reason": (
                    "Duplicate message prevented - "
                    "same message type sent within 24 hours"
                ),
                "recent_message_id": str(recent_messages[0].id),
                "recent_message_sent_at": recent_messages[0].created_at.isoformat(),
            }

        # Format phone number to E.164
        formatted_phone = self._format_phone(phone)

        # Create message record
        sent_message = await self.message_repo.create(
            customer_id=customer_id,
            message_type=message_type,
            message_content=message,
            recipient_phone=formatted_phone,
            job_id=job_id,
            appointment_id=appointment_id,
        )

        # Send via Twilio (placeholder - would use actual Twilio client)
        try:
            twilio_sid = await self._send_via_twilio(formatted_phone, message)

            # Update message record
            await self.message_repo.update(
                sent_message.id,
                delivery_status=DeliveryStatus.SENT,
                twilio_sid=twilio_sid,
                sent_at=datetime.now(),
            )

            self.log_completed("send_message", message_id=str(sent_message.id))
            return {
                "success": True,
                "message_id": str(sent_message.id),
                "twilio_sid": twilio_sid,
                "status": "sent",
            }

        except Exception as e:
            # Update message record with failure
            await self.message_repo.update(
                sent_message.id,
                delivery_status=DeliveryStatus.FAILED,
                error_message=str(e),
            )

            self.log_failed("send_message", error=e)
            msg = f"Failed to send SMS: {e}"
            raise SMSError(msg) from e

    async def send_automated_message(
        self,
        phone: str,
        message: str,
        message_type: str = "automated",
    ) -> dict[str, Any]:
        """Send an automated SMS with consent check and time window enforcement.

        Args:
            phone: Phone number
            message: Message content
            message_type: Type of message (automated or manual)

        Returns:
            Result dict with success status

        Validates: Requirements 8.6, 9.4, 9.5
        """
        self.log_started("send_automated_message", phone=phone)

        # Check consent before sending (Req 8.6)
        has_consent = await self.check_sms_consent(phone)
        if not has_consent:
            self.log_rejected(
                "send_automated_message",
                reason="opted_out",
                phone=phone,
            )
            return {"success": False, "reason": "opted_out"}

        # Enforce time window for automated messages (Req 9.4, 9.5)
        scheduled_time = self.enforce_time_window(phone, message, message_type)
        if scheduled_time is not None:
            return {
                "success": True,
                "deferred": True,
                "scheduled_for": scheduled_time.isoformat(),
            }

        # Send immediately
        twilio_sid = await self._send_via_twilio(
            self._format_phone(phone),
            message,
        )
        self.log_completed("send_automated_message", phone=phone)
        return {"success": True, "twilio_sid": twilio_sid}

    async def _send_via_twilio(
        self,
        phone: str,  # noqa: ARG002
        message: str,  # noqa: ARG002
    ) -> str:
        """Send message via Twilio API.

        Args:
            phone: Formatted phone number
            message: Message content

        Returns:
            Twilio message SID
        """
        # Placeholder - in production would use Twilio client
        return f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format.

        Args:
            phone: Raw phone number

        Returns:
            E.164 formatted phone number
        """
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 10:
            digits = "1" + digits
        return f"+{digits}"

    async def handle_inbound(
        self,
        from_phone: str,
        body: str,
        twilio_sid: str,
    ) -> dict[str, Any]:
        """Handle incoming SMS with STOP keyword and informal opt-out processing.

        Args:
            from_phone: Sender phone number
            body: Message body
            twilio_sid: Twilio message SID

        Returns:
            Processing result

        Validates: Requirements 8.1-8.5
        """
        self.log_started("handle_inbound", from_phone=from_phone)

        body_stripped = body.strip()
        body_lower = body_stripped.lower()

        # 10.1: Exact opt-out keyword match (Req 8.1, 8.2, 8.3, 8.4)
        if body_lower in EXACT_OPT_OUT_KEYWORDS:
            return await self._process_exact_opt_out(from_phone, body_lower)

        # 10.2: Informal opt-out phrase detection (Req 8.5)
        if self._matches_informal_opt_out(body_lower):
            return await self._flag_informal_opt_out(from_phone, body_stripped)

        # Delegate to existing webhook handler for other messages
        return await self.handle_webhook(from_phone, body, twilio_sid)

    async def _process_exact_opt_out(
        self,
        phone: str,
        keyword: str,
    ) -> dict[str, Any]:
        """Process exact opt-out keyword: create consent record and send confirmation.

        Args:
            phone: Sender phone number
            keyword: The matched keyword

        Returns:
            Processing result

        Validates: Requirements 8.1, 8.2, 8.3, 8.4
        """
        now = datetime.now(timezone.utc)
        formatted_phone = self._format_phone(phone)

        record = SmsConsentRecord(
            phone_number=formatted_phone,
            consent_type="marketing",
            consent_given=False,
            consent_timestamp=now,
            consent_method="text_stop",
            consent_language_shown=f"Keyword: {keyword}",
            opt_out_timestamp=now,
            opt_out_method="text_stop",
            opt_out_processed_at=now,
            opt_out_confirmation_sent=True,
        )
        self.session.add(record)
        await self.session.flush()

        # Send confirmation SMS (Req 8.3)
        await self._send_via_twilio(formatted_phone, OPT_OUT_CONFIRMATION_MSG)

        self.log_completed(
            "handle_inbound",
            webhook_action="exact_opt_out",
            keyword=keyword,
            phone=phone,
        )
        return {
            "action": "opt_out",
            "phone": phone,
            "keyword": keyword,
            "message": OPT_OUT_CONFIRMATION_MSG,
        }

    @staticmethod
    def _matches_informal_opt_out(body_lower: str) -> bool:
        """Check if message body contains an informal opt-out phrase.

        Args:
            body_lower: Lowercased message body

        Returns:
            True if informal opt-out phrase detected
        """
        return any(phrase in body_lower for phrase in INFORMAL_OPT_OUT_PHRASES)

    async def _flag_informal_opt_out(
        self,
        phone: str,
        body: str,
    ) -> dict[str, Any]:
        """Flag informal opt-out for admin review without auto-processing.

        Args:
            phone: Sender phone number
            body: Original message body

        Returns:
            Processing result

        Validates: Requirements 8.5
        """
        self.log_started(
            "flag_informal_opt_out",
            phone=phone,
            body=body,
        )
        logger.warning(
            "sms.informal_opt_out.flagged",
            phone=phone,
            body=body,
            action="admin_review_required",
        )
        self.log_completed(
            "handle_inbound",
            webhook_action="informal_opt_out_flagged",
            phone=phone,
        )
        return {
            "action": "informal_opt_out_flagged",
            "phone": phone,
            "body": body,
            "message": "Informal opt-out detected. Flagged for admin review.",
        }

    async def check_sms_consent(self, phone: str) -> bool:
        """Check most recent consent record for a phone number.

        Args:
            phone: Phone number (any format)

        Returns:
            True if most recent consent record has consent_given=True,
            or True if no records exist (default allow).

        Validates: Requirements 8.6
        """
        formatted_phone = self._format_phone(phone)
        stmt = (
            select(SmsConsentRecord.consent_given)
            .where(SmsConsentRecord.phone_number == formatted_phone)
            .order_by(SmsConsentRecord.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return True  # No records = default allow
        return bool(row)

    def enforce_time_window(
        self,
        phone: str,
        message: str,  # noqa: ARG002
        message_type: str = "automated",
    ) -> datetime | None:
        """Enforce 8AM-9PM CT time window for automated SMS.

        Args:
            phone: Recipient phone number (for logging)
            message: Message content (for logging)
            message_type: "automated" or "manual"

        Returns:
            None if send immediately, or scheduled datetime if deferred.

        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        # Manual messages bypass time window (Req 9.5)
        if message_type == "manual":
            return None

        now_ct = datetime.now(CT_TZ)
        window_start = time(8, 0)
        window_end = time(21, 0)

        if window_start <= now_ct.time() < window_end:
            return None

        # Compute next 8:00 AM CT
        if now_ct.time() >= window_end:
            next_day = now_ct.date() + timedelta(days=1)
        else:
            next_day = now_ct.date()

        scheduled = datetime.combine(next_day, window_start, tzinfo=CT_TZ)

        self.log_started(
            "enforce_time_window",
            original_time=now_ct.isoformat(),
            scheduled_time=scheduled.isoformat(),
            phone=phone,
        )
        logger.info(
            "sms.time_window.deferred",
            original_time=now_ct.isoformat(),
            scheduled_time=scheduled.isoformat(),
            phone=phone,
        )
        return scheduled

    async def handle_webhook(
        self,
        from_phone: str,
        body: str,
        twilio_sid: str,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Handle incoming SMS webhook from Twilio.

        Args:
            from_phone: Sender phone number
            body: Message body
            twilio_sid: Twilio message SID

        Returns:
            Processing result
        """
        self.log_started("handle_webhook", from_phone=from_phone)

        body_lower = body.strip().lower()

        # Handle opt-out keywords
        if body_lower in ["stop", "unsubscribe", "cancel"]:
            self.log_completed("handle_webhook", webhook_action="opt_out")
            return {
                "action": "opt_out",
                "phone": from_phone,
                "message": "You have been unsubscribed from SMS messages.",
            }

        # Handle confirmation keywords
        if body_lower in ["yes", "confirm", "y"]:
            self.log_completed("handle_webhook", webhook_action="confirm")
            return {
                "action": "confirm",
                "phone": from_phone,
                "message": "Thank you for confirming!",
            }

        # Handle help keywords
        if body_lower in ["help", "info"]:
            self.log_completed("handle_webhook", webhook_action="help")
            return {
                "action": "help",
                "phone": from_phone,
                "message": "Reply STOP to unsubscribe. Call (612) 555-0100 for help.",
            }

        # Default - forward to admin
        self.log_completed("handle_webhook", webhook_action="forward")
        return {
            "action": "forward",
            "phone": from_phone,
            "body": body,
            "message": "Message received and forwarded to admin.",
        }

    async def check_opt_in(self, customer_id: UUID) -> bool:  # noqa: ARG002
        """Check if customer has opted in to SMS.

        Args:
            customer_id: Customer ID

        Returns:
            True if opted in, False otherwise
        """
        # Placeholder - would query customer record
        return False
