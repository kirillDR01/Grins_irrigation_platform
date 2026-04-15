"""Pydantic schemas for customer duplicate detection and merge.

Validates: CRM Changes Update 2 Req 5.1, 6.2
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import MergeCandidateStatus


class MergeCandidateResponse(BaseModel):
    """Duplicate merge candidate response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_a_id: UUID
    customer_b_id: UUID
    score: int
    match_signals: dict[str, Any]
    status: MergeCandidateStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class MergeFieldSelection(BaseModel):
    """Field selection for merge — which record's value to keep."""

    field_name: str
    source: str = Field(description="'a' or 'b' — which customer's value to keep")


class MergeRequest(BaseModel):
    """Request to merge two customer records."""

    primary_id: UUID = Field(description="Surviving customer ID")
    duplicate_id: UUID = Field(description="Customer to be merged away")
    field_selections: list[MergeFieldSelection] = Field(default_factory=list)


class MergeExecuteBody(BaseModel):
    """Body for POST /customers/{id}/merge — primary_id comes from URL."""

    duplicate_id: UUID = Field(description="Customer to be merged away")
    field_selections: list[MergeFieldSelection] = Field(default_factory=list)


class MergePreviewResponse(BaseModel):
    """Preview of what a merge would produce."""

    primary_id: UUID
    duplicate_id: UUID
    merged_fields: dict[str, Any]
    jobs_to_reassign: int
    invoices_to_reassign: int
    properties_to_reassign: int
    communications_to_reassign: int
    agreements_to_reassign: int
    blockers: list[str] = Field(default_factory=list)


class PaginatedMergeCandidateResponse(BaseModel):
    """Paginated list of merge candidates."""

    items: list[MergeCandidateResponse]
    total: int
    skip: int
    limit: int
