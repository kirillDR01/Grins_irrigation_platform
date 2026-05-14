"""Pydantic schemas for :class:`AdminNotification`.

Validates: Cluster H §5.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminNotificationResponse(BaseModel):
    """Schema for a single :class:`AdminNotification` row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Notification UUID")
    event_type: str = Field(
        ...,
        max_length=64,
        description="Event type (see AdminNotificationEventType)",
    )
    subject_resource_type: str = Field(
        ...,
        max_length=32,
        description="Referenced entity type (e.g. 'estimate', 'appointment')",
    )
    subject_resource_id: UUID = Field(
        ...,
        description="UUID of the referenced entity",
    )
    summary: str = Field(
        ...,
        max_length=280,
        description="Short human-readable summary",
    )
    actor_user_id: UUID | None = Field(
        default=None,
        description="Staff UUID who triggered the event, or null for portal actions",
    )
    created_at: datetime = Field(..., description="When the notification was created")
    read_at: datetime | None = Field(
        default=None,
        description="When the notification was marked read, or null",
    )


class AdminNotificationListResponse(BaseModel):
    """Container for a list of admin notifications."""

    items: list[AdminNotificationResponse] = Field(
        default_factory=list,
        description="Returned notifications in descending created_at order",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Number of notifications returned (bounded by query limit)",
    )


class AdminNotificationUnreadCountResponse(BaseModel):
    """Container for the unread-count endpoint response."""

    unread: int = Field(..., ge=0, description="Count of unread notifications")
