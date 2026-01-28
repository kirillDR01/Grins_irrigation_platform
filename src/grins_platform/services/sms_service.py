"""SMS Service for customer communications.

Validates: AI Assistant Requirements 12.1-12.10
"""

import os
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import DeliveryStatus, MessageType


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
        # from twilio.rest import Client
        # client = Client(self.twilio_account_sid, self.twilio_auth_token)
        # message = client.messages.create(
        #     body=message,
        #     from_=self.twilio_phone_number,
        #     to=phone
        # )
        # return message.sid

        # Return placeholder SID for testing
        return f"SM{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format.

        Args:
            phone: Raw phone number

        Returns:
            E.164 formatted phone number
        """
        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone)

        # Add country code if not present
        if len(digits) == 10:
            digits = "1" + digits

        return f"+{digits}"

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

        # Process incoming message
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
        # In production, this would check customer.sms_opt_in
        return False
