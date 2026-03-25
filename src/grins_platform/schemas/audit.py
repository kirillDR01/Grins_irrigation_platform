"""Pydantic schemas for audit log.

Validates: CRM Gap Closure Req 74.3
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema for audit log entry response.

    Validates: CRM Gap Closure Req 74.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Audit log entry UUID")
    actor_id: UUID | None = Field(default=None, description="Staff actor UUID")
    actor_role: str | None = Field(
        default=None,
        max_length=50,
        description="Actor role",
    )
    action: str = Field(..., max_length=100, description="Action performed")
    resource_type: str = Field(
        ...,
        max_length=50,
        description="Resource type affected",
    )
    resource_id: str | None = Field(
        default=None,
        max_length=50,
        description="Resource UUID",
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="Additional event details",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Client IP address",
    )
    created_at: datetime = Field(..., description="Event timestamp")


class AuditLogFilters(BaseModel):
    """Filters for querying audit log.

    Validates: CRM Gap Closure Req 74.3
    """

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    actor_id: UUID | None = Field(default=None, description="Filter by actor")
    action: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by action",
    )
    resource_type: str | None = Field(
        default=None,
        max_length=50,
        description="Filter by resource type",
    )
    date_from: datetime | None = Field(
        default=None,
        description="Filter from date",
    )
    date_to: datetime | None = Field(default=None, description="Filter to date")
