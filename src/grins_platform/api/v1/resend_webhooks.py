"""Resend email webhook endpoint.

Receives bounce/complaint events from Resend, verifies HMAC signature
(via the Svix-format ``resend.Webhooks.verify`` helper), notifies
internal staff, and soft-flags the affected customer on a permanent
bounce.

Validates: Estimate approval email portal — bounce handling.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import update

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.middleware.rate_limit import WEBHOOK_LIMIT, limiter
from grins_platform.models.customer import Customer
from grins_platform.services.email_config import EmailSettings
from grins_platform.services.email_service import EmailService
from grins_platform.services.resend_webhook_security import (
    ResendWebhookVerificationError,
    verify_resend_webhook_signature,
)
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms_service import SMSService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)
router = APIRouter(prefix="/webhooks/resend", tags=["resend-webhooks"])


class _ResendWebhookEndpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _ResendWebhookEndpoints()


def _extract_estimate_id(tags: Any) -> str:  # noqa: ANN401
    """Pull the ``estimate_id`` value out of Resend's tags structure.

    Resend echoes back the ``tags`` we passed on send. Format may be
    ``[{"name": "estimate_id", "value": "<uuid>"}, ...]`` (list-of-dicts)
    or ``{"estimate_id": "<uuid>"}`` (dict). Default ``"unknown"``.
    """
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get("name") == "estimate_id":
                return str(tag.get("value", "unknown"))
    elif isinstance(tags, dict):
        value = tags.get("estimate_id")
        if value:
            return str(value)
    return "unknown"


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Handle Resend email webhook",
)
@limiter.limit(WEBHOOK_LIMIT)
async def resend_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Handle Resend email webhook events."""
    _ep.log_started("resend_webhook")
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    settings = EmailSettings()
    try:
        payload: dict[str, Any] = verify_resend_webhook_signature(
            secret=settings.resend_webhook_secret,
            headers=headers,
            raw_body=raw_body,
        )
    except ResendWebhookVerificationError as e:
        logger.warning("resend.webhook.signature_invalid", error=str(e))
        return Response(
            content='{"error":"Invalid signature"}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
        )

    event_type = payload.get("type", "")
    data = payload.get("data", {}) or {}

    if event_type not in {"email.bounced", "email.complained"}:
        logger.info("resend.webhook.ignored_event", event_type=event_type)
        _ep.log_completed(
            "resend_webhook",
            event_type=event_type,
            outcome="ignored",
        )
        return Response(status_code=status.HTTP_200_OK)

    bounce = data.get("bounce", {}) or {}
    bounce_type = bounce.get("type", "Permanent")
    to_emails = data.get("to", []) or []
    to_email = to_emails[0] if to_emails else None
    reason = bounce.get("message") or "unknown"
    estimate_id = _extract_estimate_id(data.get("tags"))

    if not to_email:
        logger.warning(
            "resend.webhook.bounce_missing_recipient",
            payload_keys=list(payload.keys()),
        )
        return Response(status_code=status.HTTP_200_OK)

    # Hard bounce only: stamp customer.email_bounced_at.
    if bounce_type == "Permanent" and event_type == "email.bounced":
        stmt = (
            update(Customer)
            .where(Customer.email == to_email)
            .values(email_bounced_at=datetime.now(timezone.utc))
        )
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            logger.warning("resend.webhook.bounce_flag_failed", error=str(e))

    recipient_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
    recipient_phone = os.getenv("INTERNAL_NOTIFICATION_PHONE", "").strip()
    email_service = EmailService()

    if recipient_email:
        try:
            email_service.send_internal_estimate_bounce_email(
                to_email=recipient_email,
                recipient_email=to_email,
                reason=reason,
                estimate_id=estimate_id,
            )
        except Exception as e:
            logger.warning("resend.webhook.bounce_email_failed", error=str(e))

    if recipient_phone:
        try:
            sms_service = SMSService(session=session, provider=get_sms_provider())
            sms_text = f"Estimate email BOUNCED for {to_email}. Reason: {reason[:80]}"
            await sms_service.send_automated_message(
                phone=recipient_phone,
                message=sms_text,
                message_type="internal_estimate_bounce",
            )
        except Exception as e:
            logger.warning("resend.webhook.bounce_sms_failed", error=str(e))

    _ep.log_completed(
        "resend_webhook",
        event_type=event_type,
        bounce_type=bounce_type,
    )
    return Response(status_code=status.HTTP_200_OK)
