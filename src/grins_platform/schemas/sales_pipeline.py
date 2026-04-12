"""Pydantic schemas for the Sales pipeline.

Validates: CRM Changes Update 2 Req 14.2, 15.1
"""

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import SalesEntryStatus


class SalesEntryCreate(BaseModel):
    """Create a new sales pipeline entry."""

    customer_id: UUID
    property_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    job_type: Optional[str] = None
    notes: Optional[str] = None


class SalesEntryStatusUpdate(BaseModel):
    """Manual status override for a sales entry."""

    status: SalesEntryStatus
    closed_reason: Optional[str] = None


class SalesEntryResponse(BaseModel):
    """Sales pipeline entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    property_id: Optional[UUID] = None
    lead_id: Optional[UUID] = None
    job_type: Optional[str] = None
    status: SalesEntryStatus
    last_contact_date: Optional[datetime] = None
    notes: Optional[str] = None
    override_flag: bool = False
    closed_reason: Optional[str] = None
    signwell_document_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Denormalized fields for list view display
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    property_address: Optional[str] = None


class SalesCalendarEventCreate(BaseModel):
    """Create an estimate appointment on the Sales calendar."""

    sales_entry_id: UUID
    customer_id: UUID
    title: str = Field(min_length=1, max_length=255)
    scheduled_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None


class SalesCalendarEventUpdate(BaseModel):
    """Update an estimate appointment."""

    title: Optional[str] = Field(default=None, max_length=255)
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None


class SalesCalendarEventResponse(BaseModel):
    """Sales calendar event response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sales_entry_id: UUID
    customer_id: UUID
    title: str
    scheduled_date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
