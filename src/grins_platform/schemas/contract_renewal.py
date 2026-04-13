"""Pydantic schemas for contract renewal proposals.

Validates: CRM Changes Update 2 Req 31.5
"""

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from grins_platform.models.enums import ProposalStatus, ProposedJobStatus


class ProposedJobResponse(BaseModel):
    """Individual proposed job within a renewal proposal."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    proposal_id: UUID
    service_type: str
    target_start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    status: ProposedJobStatus
    proposed_job_payload: Optional[dict[str, Any]] = None
    admin_notes: Optional[str] = None
    created_job_id: Optional[UUID] = None


class ProposedJobModification(BaseModel):
    """Modify a proposed job before approving."""

    target_start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    admin_notes: Optional[str] = None


class RenewalProposalResponse(BaseModel):
    """Contract renewal proposal response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_agreement_id: UUID
    customer_id: UUID
    status: ProposalStatus
    proposed_job_count: int
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[UUID] = None
    proposed_jobs: list[ProposedJobResponse] = Field(default_factory=list)
