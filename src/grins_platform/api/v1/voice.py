"""Voice AI webhook API endpoint.

Provides a webhook endpoint for voice AI (Vapi) integration.

Validates: CRM Gap Closure Req 44.5
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from grins_platform.log_config import LoggerMixin

router = APIRouter()


class _VoiceEndpoints(LoggerMixin):
    """Voice API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _VoiceEndpoints()


class VoiceWebhookResponse(BaseModel):
    """Voice webhook response."""

    status: str = Field(default="ok", description="Processing status")
    message: str | None = Field(
        default=None,
        description="Optional response message",
    )


@router.post(
    "/webhook",
    response_model=VoiceWebhookResponse,
    summary="Voice AI webhook",
    description="Webhook endpoint for voice AI (Vapi) events. No auth required.",
)
async def voice_webhook(
    request: Request,
) -> VoiceWebhookResponse:
    """Handle voice AI webhook events.

    This endpoint is PUBLIC — no authentication required.
    Vapi sends call events (started, ended, transcript, etc.).

    Validates: CRM Gap Closure Req 44.5
    """
    _endpoints.log_started("voice_webhook")

    try:
        body: dict[str, Any] = await request.json()
        event_type = body.get("type", "unknown")

        _endpoints.log_completed(
            "voice_webhook",
            event_type=event_type,
        )

        return VoiceWebhookResponse(
            status="ok",
            message=f"Processed event: {event_type}",
        )
    except Exception as e:
        _endpoints.log_failed("voice_webhook", error=e)
        # Always return 200 to webhooks to prevent retries
        return VoiceWebhookResponse(
            status="error",
            message="Failed to process webhook",
        )
