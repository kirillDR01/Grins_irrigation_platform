"""
Pydantic schemas for schedule clear operations.

This module defines the Pydantic schemas for schedule clear-related
API requests and responses.

Validates: Schedule Workflow Improvements Requirements 3.1-3.7, 5.1-5.6, 6.1-6.5
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScheduleClearRequest(BaseModel):
    """Schema for clearing a schedule.

    Validates: Requirements 3.1-3.7
    """

    schedule_date: date = Field(..., description="Date to clear appointments for")
    notes: Optional[str] = Field(None, description="Optional notes about the clear")


class ScheduleClearResponse(BaseModel):
    """Schema for schedule clear response.

    Validates: Requirements 3.1-3.7
    """

    audit_id: UUID = Field(..., description="ID of the audit record")
    schedule_date: date = Field(..., description="Date that was cleared")
    appointments_deleted: int = Field(..., description="Number of appointments deleted")
    jobs_reset: int = Field(..., description="Number of jobs reset to approved")
    cleared_at: datetime = Field(..., description="Timestamp of the clear operation")


class ScheduleClearAuditResponse(BaseModel):
    """Schema for schedule clear audit response.

    Validates: Requirements 5.1-5.6, 6.1-6.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Audit record ID")
    schedule_date: date = Field(..., description="Date that was cleared")
    appointment_count: int = Field(..., description="Number of appointments cleared")
    cleared_at: datetime = Field(..., description="Timestamp of the clear operation")
    cleared_by: Optional[UUID] = Field(None, description="Staff ID who cleared")
    notes: Optional[str] = Field(None, description="Notes about the clear")


class ScheduleClearAuditDetailResponse(ScheduleClearAuditResponse):
    """Schema for detailed schedule clear audit response.

    Extends ScheduleClearAuditResponse with full appointment data and job IDs.

    Validates: Requirements 6.3
    """

    appointments_data: list[dict[str, Any]] = Field(
        ..., description="Serialized appointment data",
    )
    jobs_reset: list[UUID] = Field(..., description="List of job IDs that were reset")
