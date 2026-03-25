"""VoiceWebhookService for handling Vapi voice AI webhooks.

Extracts caller name, phone, and service requested from Vapi payload,
then creates a Lead via the Lead model.

Validates: CRM Gap Closure Req 44.1, 44.2, 44.3, 44.5
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.models.lead import Lead

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class VoiceWebhookService(LoggerMixin):
    """Service for processing Vapi voice AI webhook payloads.

    Extracts caller information and creates Lead records.

    Validates: CRM Gap Closure Req 44.1, 44.2, 44.3, 44.5
    """

    DOMAIN = "voice"

    def _extract_caller_info(
        self,
        payload: dict[str, Any],
    ) -> dict[str, str | None]:
        """Extract name, phone, and service from Vapi webhook payload.

        Vapi payloads typically include:
        - message.call.customer.number (phone)
        - message.transcript or message.functionCall.parameters

        Args:
            payload: Raw Vapi webhook payload.

        Returns:
            Dict with name, phone, service_requested keys.
        """
        info: dict[str, str | None] = {
            "name": None,
            "phone": None,
            "service_requested": None,
        }

        # Extract from Vapi call structure
        message = payload.get("message", {})
        call = message.get("call", {})
        customer = call.get("customer", {})

        # Phone from customer number
        phone = customer.get("number", "")
        if phone:
            # Normalize: strip +1 prefix and non-digits
            import re  # noqa: PLC0415

            digits = re.sub(r"[^0-9]", "", phone)
            if len(digits) == 11 and digits.startswith("1"):
                digits = digits[1:]
            if len(digits) == 10:
                info["phone"] = digits

        # Extract from function call parameters (if Vapi collected info)
        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})
        if parameters:
            info["name"] = parameters.get("name") or parameters.get("caller_name")
            info["service_requested"] = (
                parameters.get("service")
                or parameters.get("service_requested")
                or parameters.get("reason")
            )

        # Fallback: extract from transcript
        if not info["name"]:
            transcript = message.get("transcript", "")
            if isinstance(transcript, str) and transcript:
                # Simple heuristic for name extraction
                import re  # noqa: PLC0415

                name_re = (
                    r"(?:my name is|this is|i'm|i am)"
                    r"\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
                )
                name_match = re.search(
                    name_re,
                    transcript,
                    re.IGNORECASE,
                )
                if name_match:
                    info["name"] = name_match.group(1).strip()

        # Fallback name
        if not info["name"]:
            info["name"] = "Voice Caller"

        return info

    async def handle_webhook(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
    ) -> UUID | None:
        """Process a Vapi voice webhook and create a Lead.

        Extracts caller name, phone, and service requested from the
        payload, then creates a Lead record with source='voice'.

        Args:
            db: Database session.
            payload: Raw Vapi webhook payload.

        Returns:
            UUID of the created Lead, or None if phone not extracted.

        Validates: Req 44.1, 44.2, 44.3
        """
        self.log_started("handle_webhook")

        caller_info = self._extract_caller_info(payload)

        if not caller_info.get("phone"):
            self.log_rejected(
                "handle_webhook",
                reason="no_phone_extracted",
            )
            return None

        name = caller_info["name"] or "Voice Caller"
        phone = caller_info["phone"] or ""
        service = caller_info.get("service_requested") or "General inquiry"

        try:
            lead = Lead(
                name=name,
                phone=phone,
                situation="exploring",
                notes=f"Voice AI inquiry: {service}",
                lead_source="voice",
                source_detail="Vapi voice webhook",
                action_tags=["NEEDS_CONTACT"],
                status="new",
            )
            db.add(lead)
            await db.flush()

            self.logger.info(
                "voice.webhook.lead_created",
                lead_id=str(lead.id),
                caller_name=name,
                service_requested=service,
            )
        except Exception as exc:
            self.log_failed("handle_webhook", error=exc)
            raise
        else:
            self.log_completed(
                "handle_webhook",
                lead_id=str(lead.id),
            )
            return lead.id
