"""Pydantic schemas for Google Sheet submission API operations.

Validates: Requirements 5.1, 5.2, 5.3
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GoogleSheetSubmissionResponse(BaseModel):
    """Full submission response for API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sheet_row_number: int
    timestamp: str | None
    spring_startup: str | None
    fall_blowout: str | None
    summer_tuneup: str | None
    repair_existing: str | None
    new_system_install: str | None
    addition_to_system: str | None
    additional_services_info: str | None
    date_work_needed_by: str | None
    name: str | None
    phone: str | None
    email: str | None
    city: str | None
    address: str | None
    client_type: str | None
    property_type: str | None
    referral_source: str | None
    landscape_hardscape: str | None
    zip_code: str | None = None
    work_requested: str | None = None
    agreed_to_terms: str | None = None
    processing_status: str
    processing_error: str | None
    lead_id: UUID | None
    imported_at: datetime
    created_at: datetime
    updated_at: datetime


class SubmissionListParams(BaseModel):
    """Query parameters for listing submissions."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    processing_status: str | None = None
    client_type: str | None = None
    search: str | None = None
    sort_by: str = Field(default="imported_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedSubmissionResponse(BaseModel):
    """Paginated submission list response."""

    items: list[GoogleSheetSubmissionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SyncStatusResponse(BaseModel):
    """Poller sync status response."""

    last_sync: datetime | None
    is_running: bool
    last_error: str | None
    detected_headers: list[str] = Field(default_factory=list)
    column_map: dict[str, int] = Field(default_factory=dict)


class TriggerSyncResponse(BaseModel):
    """Response for manual sync trigger."""

    new_rows_imported: int
