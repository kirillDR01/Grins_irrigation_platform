"""Pydantic schemas for :class:`Alert`.

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    """Schema for a single :class:`Alert` row in API responses.

    Validates: bughunt 2026-04-16 finding H-5
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Alert UUID")
    type: str = Field(..., max_length=100, description="Alert type")
    severity: str = Field(
        ...,
        max_length=20,
        description="Alert severity (info / warning / error)",
    )
    entity_type: str = Field(
        ...,
        max_length=50,
        description="Referenced entity type (e.g. 'appointment')",
    )
    entity_id: UUID = Field(
        ...,
        description="UUID of the referenced entity",
    )
    message: str = Field(..., description="Short human-readable summary")
    created_at: datetime = Field(..., description="When the alert was raised")
    acknowledged_at: datetime | None = Field(
        default=None,
        description="When an admin acknowledged the alert, or null",
    )


class AlertListResponse(BaseModel):
    """Container for a list of alerts returned by the index endpoint.

    Validates: bughunt 2026-04-16 finding H-5
    """

    items: list[AlertResponse] = Field(
        default_factory=list,
        description="Returned alerts in ascending created_at order",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Number of alerts returned (bounded by the query limit)",
    )


class AlertCountsResponse(BaseModel):
    """Per-type counts of unacknowledged alerts (gap-14 dashboard cards).

    The ``counts`` mapping is keyed by ``AlertType`` value strings; types
    with no open rows are filled with zero so dashboard cards do not need
    to special-case missing keys.
    """

    counts: dict[str, int] = Field(
        default_factory=dict,
        description="Map of alert_type → count of unacknowledged rows",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total unacknowledged alerts across all types",
    )
