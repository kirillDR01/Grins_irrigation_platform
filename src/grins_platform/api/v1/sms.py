"""SMS API endpoints.

Validates: AI Assistant Requirements 15.8-15.10
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.database import get_db_session as get_db
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import DeliveryStatus
from grins_platform.schemas.sms import (
    BulkSendRequest,
    BulkSendResponse,
    CommunicationsQueueResponse,
    SMSSendRequest,
    SMSSendResponse,
    WebhookResponse,
)
from grins_platform.services.ai.security import validate_twilio_signature
from grins_platform.services.sms_service import SMSOptInError, SMSService

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
    """
    sms_service = SMSService(db)

    try:
        result = await sms_service.send_message(
            customer_id=request.customer_id,
            phone=request.phone,
            message=request.message,
            message_type=request.message_type,
            sms_opt_in=request.sms_opt_in,
            job_id=request.job_id,
            appointment_id=request.appointment_id,
        )

        return SMSSendResponse(
            success=result["success"],
            message_id=UUID(result["message_id"]),
            twilio_sid=result.get("twilio_sid"),
            status=result["status"],
        )

    except SMSOptInError as e:
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
    twilio_sid = str(form_data.get("MessageSid", ""))

    sms_service = SMSService(db)
    result = await sms_service.handle_webhook(from_phone, body, twilio_sid)

    return WebhookResponse(
        action=result["action"],
        phone=result.get("phone"),
        message=result.get("message"),
    )


# Communications queue endpoints
communications_router = APIRouter(prefix="/communications", tags=["Communications"])


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


@communications_router.post("/send-bulk", response_model=BulkSendResponse)
async def send_bulk(
    request: BulkSendRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkSendResponse:
    """Send bulk SMS messages.

    Args:
        request: Bulk send request
        db: Database session

    Returns:
        Bulk send results
    """
    sms_service = SMSService(db)
    results = []
    success_count = 0
    failure_count = 0

    for recipient in request.recipients:
        try:
            result = await sms_service.send_message(
                customer_id=recipient.customer_id,
                phone=recipient.phone,
                message=request.message,
                message_type=request.message_type,
                sms_opt_in=recipient.sms_opt_in,
            )
            results.append({
                "customer_id": str(recipient.customer_id),
                "success": True,
                "message_id": result["message_id"],
            })
            success_count += 1
        except Exception as e:  # noqa: PERF203
            results.append({
                "customer_id": str(recipient.customer_id),
                "success": False,
                "error": str(e),
            })
            failure_count += 1

    return BulkSendResponse(
        total=len(request.recipients),
        success_count=success_count,
        failure_count=failure_count,
        results=results,
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
