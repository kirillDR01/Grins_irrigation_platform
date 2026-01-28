"""Communication tools for AI assistant.

Validates: AI Assistant Requirements 6.1-6.9
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.log_config import LoggerMixin
from grins_platform.services.ai.prompts.communication import TEMPLATES


class CommunicationTools(LoggerMixin):
    """Tools for drafting customer communications."""

    DOMAIN = "business"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__()
        self.session = session

    async def draft_message(
        self,
        message_type: str,
        customer_data: dict[str, Any],
        appointment_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Draft a customer message.

        Args:
            message_type: Type of message to draft
            customer_data: Customer information
            appointment_data: Optional appointment information

        Returns:
            Drafted message with metadata
        """
        self.log_started("draft_message", message_type=message_type)

        # Get template
        template = TEMPLATES.get(message_type)
        if not template:
            self.log_rejected("draft_message", reason="unknown_message_type")
            return {
                "success": False,
                "error": f"Unknown message type: {message_type}",
            }

        # Build context for template
        context = self._build_context(customer_data, appointment_data)

        # Fill template
        try:
            message = template.format(**context)
        except KeyError as e:
            self.log_rejected("draft_message", reason="missing_context", field=str(e))
            return {
                "success": False,
                "error": f"Missing required field: {e}",
            }

        result = {
            "success": True,
            "message_type": message_type,
            "message": message,
            "character_count": len(message),
            "sms_segments": (len(message) // 160) + 1,
        }

        self.log_completed("draft_message", character_count=len(message))
        return result

    def _build_context(
        self,
        customer_data: dict[str, Any],
        appointment_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build context for message template.

        Args:
            customer_data: Customer information
            appointment_data: Optional appointment information

        Returns:
            Context dictionary for template
        """
        context: dict[str, Any] = {
            "customer_name": customer_data.get("first_name", "Customer"),
        }

        if appointment_data:
            context.update(
                {
                    "date": appointment_data.get("date", "TBD"),
                    "time_window": appointment_data.get("time_window", "TBD"),
                    "service_type": appointment_data.get("service_type", "service"),
                    "tech_name": appointment_data.get("tech_name", "our technician"),
                    "eta": appointment_data.get("eta", "30"),
                    "work_summary": appointment_data.get(
                        "work_summary", "Work completed",
                    ),
                    "amount": appointment_data.get("amount", "0.00"),
                },
            )

        # Add default values for optional fields
        context.setdefault("review_link", "https://g.page/grins-irrigation")
        context.setdefault("payment_link", "https://pay.grins-irrigation.com")
        context.setdefault("invoice_id", "N/A")

        return context

    async def get_message_types(self) -> list[dict[str, str]]:
        """Get available message types.

        Returns:
            List of message types with descriptions
        """
        return [
            {
                "type": "appointment_confirmation",
                "description": "Confirm scheduled appointment",
            },
            {"type": "appointment_reminder", "description": "Day-before reminder"},
            {"type": "on_the_way", "description": "Technician en route notification"},
            {"type": "completion_summary", "description": "Job completed summary"},
            {"type": "follow_up", "description": "Post-service follow-up"},
            {"type": "estimate_ready", "description": "Estimate ready for review"},
            {"type": "payment_reminder", "description": "Invoice payment reminder"},
        ]
