"""
Note Pydantic schemas for request/response validation.

This module defines Pydantic schemas for note-related API operations,
including creation, updates, and responses for the unified notes timeline.

Validates: april-16th-fixes-enhancements Requirement 4
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    """Schema for creating a new note.

    Validates: Requirement 4.3
    """

    body: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Note content text",
    )


class NoteUpdate(BaseModel):
    """Schema for updating an existing note.

    Validates: Requirement 4.3
    """

    body: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Updated note content text",
    )


class NoteResponse(BaseModel):
    """Schema for note response data.

    Includes computed fields like author_name and stage_tag that are
    populated by the service layer for timeline rendering.

    Validates: Requirement 4.2, 4.3
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique note identifier")
    subject_type: str = Field(
        ...,
        description="Entity type: lead, sales_entry, customer, or appointment",
    )
    subject_id: UUID = Field(..., description="ID of the subject entity")
    author_id: UUID = Field(..., description="Staff ID of the note author")
    author_name: str = Field(
        ...,
        description="Display name of the note author",
    )
    body: str = Field(..., description="Note content text")
    origin_lead_id: UUID | None = Field(
        default=None,
        description="Cross-stage threading link to originating lead",
    )
    is_system: bool = Field(
        ...,
        description="Whether this is a system-generated stage-transition note",
    )
    created_at: datetime = Field(..., description="Note creation timestamp")
    updated_at: datetime = Field(..., description="Note last update timestamp")
    stage_tag: str = Field(
        ...,
        description="Display tag for the stage (Lead, Sales, Customer, Appointment)",
    )
