"""Pydantic schemas for Y/R/C confirmation flow and reschedule requests.

Validates: CRM Changes Update 2 Req 24.6, 25.2
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from grins_platform.models.enums import ConfirmationKeyword


class ConfirmationResponseSchema(BaseModel):
    """Job confirmation response record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    appointment_id: UUID
    sent_message_id: Optional[UUID] = None
    customer_id: UUID
    from_phone: str
    reply_keyword: Optional[ConfirmationKeyword] = None
    raw_reply_body: str
    provider_sid: Optional[str] = None
    status: str
    received_at: datetime
    processed_at: Optional[datetime] = None


class RescheduleRequestResponse(BaseModel):
    """Reschedule request record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    appointment_id: UUID
    customer_id: UUID
    original_reply_id: Optional[UUID] = None
    requested_alternatives: Optional[dict[str, Any]] = None
    raw_alternatives_text: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class RescheduleRequestDetailResponse(BaseModel):
    """Enriched reschedule request for admin queue.

    Validates: CRM Changes Update 2 Req 25.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    appointment_id: UUID
    customer_id: UUID
    customer_name: str
    original_appointment_date: Optional[date] = None
    original_appointment_staff: Optional[str] = None
    requested_alternatives: Optional[dict[str, Any]] = None
    raw_alternatives_text: Optional[str] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class RescheduleRequestResolve(BaseModel):
    """Request body for resolving a reschedule request."""

    notes: Optional[str] = None
