"""SignWell e-signature webhook endpoint.

Receives webhook events from SignWell, verifies HMAC-SHA256 signature,
and processes document_completed events to store signed PDFs and advance
sales pipeline status.

Validates: CRM Changes Update 2 Req 14.6, 17.4, 18.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select

from grins_platform.database import get_db_session as get_db
from grins_platform.log_config import LoggerMixin, get_logger
from grins_platform.models.customer_document import CustomerDocument
from grins_platform.models.enums import SalesEntryStatus
from grins_platform.models.sales import SalesEntry
from grins_platform.services.signwell.client import (
    SignWellClient,
    SignWellError,
    SignWellWebhookVerificationError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/signwell", tags=["signwell-webhooks"])


class _SignWellWebhookEndpoints(LoggerMixin):
    DOMAIN = "api"


_ep = _SignWellWebhookEndpoints()


def _get_signwell_client() -> SignWellClient:
    return SignWellClient()


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Handle SignWell webhook events",
    description=(
        "Receives webhook events from SignWell, verifies HMAC-SHA256 "
        "signature, and processes document_completed events."
    ),
)
async def signwell_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: SignWellClient = Depends(_get_signwell_client),
) -> Response:
    """Handle SignWell webhook.

    Validates: CRM Changes Update 2 Req 14.6, 17.4, 18.4
    """
    _ep.log_started("signwell_webhook")

    raw_body = await request.body()
    signature = request.headers.get("X-Signwell-Signature", "")

    # 1. Verify HMAC-SHA256 signature
    try:
        _ = client.verify_webhook_signature(raw_body, signature)
    except SignWellWebhookVerificationError:
        logger.warning("signwell.webhook.signature_invalid")
        return Response(
            content='{"error": "Invalid signature"}',
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json",
        )

    # 2. Parse payload
    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        logger.warning("signwell.webhook.malformed_payload")
        return Response(
            content='{"error": "Malformed payload"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    event_type = payload.get("event_type") or payload.get("event", "")

    # 3. Only handle document_completed
    if event_type != "document_completed":
        logger.info(
            "signwell.webhook.ignored_event",
            event_type=event_type,
        )
        return Response(
            content='{"status": "ignored"}',
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )

    document_data = payload.get("data", payload.get("document", {}))
    document_id = str(document_data.get("id", ""))
    if not document_id:
        logger.warning("signwell.webhook.missing_document_id")
        return Response(
            content='{"error": "Missing document ID"}',
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json",
        )

    # 4. Find the sales entry linked to this SignWell document
    result = await db.execute(
        select(SalesEntry).where(
            SalesEntry.signwell_document_id == document_id,
        ),
    )
    entry: SalesEntry | None = result.scalar_one_or_none()

    if not entry:
        logger.warning(
            "signwell.webhook.no_matching_entry",
            document_id=document_id,
        )
        return Response(
            content='{"status": "no_matching_entry"}',
            status_code=status.HTTP_200_OK,
            media_type="application/json",
        )

    # 5. Fetch signed PDF and store as CustomerDocument
    try:
        pdf_bytes = await client.fetch_signed_pdf(document_id)
    except SignWellError:
        logger.exception(
            "signwell.webhook.fetch_pdf_failed",
            document_id=document_id,
        )
        return Response(
            content='{"error": "Failed to fetch signed PDF"}',
            status_code=status.HTTP_502_BAD_GATEWAY,
            media_type="application/json",
        )

    # Store in S3 via PhotoService
    from grins_platform.services.photo_service import (  # noqa: PLC0415
        PhotoService,
        UploadContext,
    )

    photo_service = PhotoService()
    upload_result = photo_service.upload_file(
        data=pdf_bytes,
        file_name=f"signed_contract_{document_id}.pdf",
        context=UploadContext.CUSTOMER_DOCUMENT,
        strip_metadata=False,
    )

    # Create CustomerDocument record
    doc = CustomerDocument(
        customer_id=entry.customer_id,
        file_key=upload_result.file_key,
        file_name=upload_result.file_name,
        document_type="signed_contract",
        mime_type="application/pdf",
        size_bytes=upload_result.file_size,
        uploaded_at=datetime.now(tz=timezone.utc),
    )
    db.add(doc)

    # 6. Advance sales entry status: pending_approval → send_contract
    if entry.status == SalesEntryStatus.PENDING_APPROVAL.value:
        entry.status = SalesEntryStatus.SEND_CONTRACT.value
        entry.updated_at = datetime.now(tz=timezone.utc)

    await db.commit()

    _ep.log_completed(
        "signwell_webhook",
        document_id=document_id,
        entry_id=str(entry.id),
        new_status=entry.status,
    )

    return Response(
        content='{"status": "processed"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json",
    )
