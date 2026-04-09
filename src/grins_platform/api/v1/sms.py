"""SMS API endpoints.

Validates: AI Assistant Requirements 15.8-15.10
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.repositories.communication_repository import (
    CommunicationRepository,
)
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import DeliveryStatus
from grins_platform.schemas.communication import UnaddressedCountResponse
from grins_platform.models.enums import CampaignStatus
from grins_platform.schemas.sms import (
    BulkSendAcceptedResponse,
    BulkSendRequest,
    CommunicationsQueueResponse,
    SMSSendRequest,
    SMSSendResponse,
    WebhookResponse,
)
from grins_platform.services.ai.security import validate_twilio_signature
from grins_platform.services.sms.recipient import Recipient
from grins_platform.services.sms_service import SMSConsentDeniedError, SMSService

router = APIRouter(prefix="/sms", tags=["SMS"])


@router.post("/send", response_model=SMSSendResponse)
async def send_sms(
    request: SMSSendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SMSSendResponse:
    """Send an SMS message.

    Args:
        request: SMS send request
        db: Database session

    Returns:
        Send result

    Validates: Requirements 4.7, 26
    """
    # Fetch customer to build Recipient
    stmt = select(Customer).where(Customer.id == request.customer_id)
    result = await db.execute(stmt)
    customer = result.scalar_one_or_none()
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {request.customer_id} not found",
        )

    recipient = Recipient.from_customer(customer)
    sms_service = SMSService(db)

    try:
        send_result = await sms_service.send_message(
            recipient=recipient,
            message=request.message,
            message_type=request.message_type,
            consent_type="transactional",
            job_id=request.job_id,
            appointment_id=request.appointment_id,
        )

        return SMSSendResponse(
            success=send_result["success"],
            message_id=UUID(send_result["message_id"]),
            provider_message_id=send_result.get("provider_message_id"),
            status=send_result["status"],
        )

    except SMSConsentDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        ) from e


@router.post("/webhook", response_model=WebhookResponse)
async def handle_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookResponse:
    """Handle incoming SMS webhook from Twilio.

    Args:
        request: Incoming request
        db: Database session

    Returns:
        Webhook processing result

    Raises:
        HTTPException: If signature validation fails
    """
    # Validate Twilio signature (Requirement 17.9)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    form_data = await request.form()
    params = dict(form_data)

    if not validate_twilio_signature(url, params, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature",
        )

    from_phone = str(form_data.get("From", ""))
    body = str(form_data.get("Body", ""))
    provider_sid = str(form_data.get("MessageSid", ""))

    sms_service = SMSService(db)
    result = await sms_service.handle_webhook(from_phone, body, provider_sid)

    return WebhookResponse(
        action=result["action"],
        phone=result.get("phone"),
        message=result.get("message"),
    )


# Communications queue endpoints
communications_router = APIRouter(prefix="/communications", tags=["Communications"])


class _CommunicationsEndpoints(LoggerMixin):
    """Communications API endpoint handlers with logging."""

    DOMAIN = "api"


_comms_endpoints = _CommunicationsEndpoints()


@communications_router.get(
    "/unaddressed-count",
    response_model=UnaddressedCountResponse,
    summary="Get unaddressed communication count",
    description="Get the count of communications not yet marked as addressed.",
)
async def get_unaddressed_count(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UnaddressedCountResponse:
    """Get count of unaddressed communications.

    Validates: CRM Gap Closure Req 4.2
    """
    _comms_endpoints.log_started("get_unaddressed_count")

    repo = CommunicationRepository(db)
    count = await repo.get_unaddressed_count()

    _comms_endpoints.log_completed("get_unaddressed_count", count=count)
    return UnaddressedCountResponse(count=count)


@communications_router.get("/queue", response_model=CommunicationsQueueResponse)
async def get_communications_queue(
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: DeliveryStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> CommunicationsQueueResponse:
    """Get communications queue.

    Args:
        db: Database session
        status_filter: Filter by status
        limit: Maximum results
        offset: Results to skip

    Returns:
        Queue items
    """
    repo = SentMessageRepository(db)
    messages, total = await repo.get_queue(
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return CommunicationsQueueResponse(
        items=[
            {
                "id": str(msg.id),
                "customer_id": str(msg.customer_id),
                "message_type": msg.message_type,
                "message_content": msg.message_content,
                "recipient_phone": msg.recipient_phone,
                "delivery_status": msg.delivery_status,
                "scheduled_for": msg.scheduled_for,
                "created_at": msg.created_at,
            }
            for msg in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@communications_router.post(
    "/send-bulk",
    response_model=BulkSendAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_bulk(
    request: BulkSendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkSendAcceptedResponse:
    """Enqueue bulk SMS for background delivery.

    Persists recipients as CampaignRecipient rows with delivery_status='pending'.
    A background worker drains the queue asynchronously.

    Validates: Requirements 8.1, 8.2, 8.3, 8.4

    Args:
        request: Bulk send request with recipients and message.
        db: Database session.

    Returns:
        HTTP 202 with campaign ID and recipient count.
    """
    _comms_endpoints.log_started(
        "send_bulk",
        recipient_count=len(request.recipients),
    )

    repo = CampaignRepository(db)

    campaign = await repo.create(
        name=f"Bulk SMS ({len(request.recipients)} recipients)",
        campaign_type="SMS",
        status=CampaignStatus.SENDING.value,
        body=request.message,
    )

    recipient_dicts: list[dict[str, Any]] = [
        {
            "campaign_id": campaign.id,
            "customer_id": r.customer_id,
            "lead_id": r.lead_id,
            "channel": "sms",
            "delivery_status": "pending",
        }
        for r in request.recipients
    ]
    _ = await repo.add_recipients_bulk(recipient_dicts)
    await db.commit()

    _comms_endpoints.log_completed(
        "send_bulk",
        campaign_id=str(campaign.id),
        recipient_count=len(request.recipients),
    )

    return BulkSendAcceptedResponse(
        campaign_id=campaign.id,
        total_recipients=len(request.recipients),
    )


@communications_router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | bool]:
    """Delete a pending message.

    Args:
        message_id: Message ID
        db: Database session

    Returns:
        Deletion result
    """
    repo = SentMessageRepository(db)
    deleted = await repo.delete(message_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or already sent",
        )

    return {"success": True, "message_id": str(message_id)}
