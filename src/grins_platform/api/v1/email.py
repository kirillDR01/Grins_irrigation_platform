"""Email endpoints — public unsubscribe.

Validates: Requirements 67.4, 67.6, 67.8
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import get_logger
from grins_platform.models.customer import Customer
from grins_platform.models.email_suppression_list import EmailSuppressionList
from grins_platform.services.email_service import EmailService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["email"])

_CONFIRMATION_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Unsubscribed</title>
<style>body{font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center}
h1{color:#2d6a4f}p{color:#555;line-height:1.6}</style></head>
<body>
<h1>You've been unsubscribed</h1>
<p>You've been unsubscribed from marketing emails.
You'll still receive transactional emails (invoices, appointment confirmations).</p>
</body></html>"""

_ERROR_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Invalid Link</title>
<style>body{font-family:sans-serif;max-width:480px;margin:60px auto;text-align:center}
h1{color:#d32f2f}p{color:#555;line-height:1.6}</style></head>
<body>
<h1>Invalid or expired link</h1>
<p>This unsubscribe link is no longer valid. Please contact us at
info@grinsirrigation.com if you need assistance.</p>
</body></html>"""


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(
    token: str = Query(..., description="Signed unsubscribe token"),
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """Process email unsubscribe via signed token.

    Public endpoint — no auth required.

    Validates: Requirements 67.4, 67.8
    """
    payload = EmailService.verify_unsubscribe_token(token)
    if payload is None:
        logger.warning("email.unsubscribe.invalid_token")
        return HTMLResponse(content=_ERROR_HTML, status_code=400)

    customer_id_str: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    if not customer_id_str or not email:
        logger.warning("email.unsubscribe.missing_fields")
        return HTMLResponse(content=_ERROR_HTML, status_code=400)

    try:
        customer_id = UUID(customer_id_str)
    except ValueError:
        logger.warning("email.unsubscribe.bad_uuid", raw=customer_id_str)
        return HTMLResponse(content=_ERROR_HTML, status_code=400)

    # Update customer opt-in
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id),
    )
    customer = result.scalar_one_or_none()
    if customer is not None:
        customer.email_opt_in = False
        customer.email_opt_out_at = datetime.now(UTC)

    # Add to suppression list (ignore if already present)
    existing = await db.execute(
        select(EmailSuppressionList).where(
            EmailSuppressionList.email == email.lower(),
        ),
    )
    if existing.scalar_one_or_none() is None:
        db.add(
            EmailSuppressionList(
                email=email.lower(),
                customer_id=customer_id if customer else None,
                reason="unsubscribe_link",
            ),
        )

    await db.commit()

    logger.info(
        "email.unsubscribe.completed",
        customer_id=customer_id_str,
    )
    return HTMLResponse(content=_CONFIRMATION_HTML)
