"""Pydantic schemas for appointment notes.

Validates: Appointment Modal V2 Req 5.3, 10.1-10.6
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteAuthorResponse(BaseModel):
    """Author info for the last editor."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str


class AppointmentNotesResponse(BaseModel):
    """Response for GET /appointments/:id/notes."""

    model_config = ConfigDict(from_attributes=True)

    appointment_id: UUID
    body: str
    updated_at: datetime
    updated_by: NoteAuthorResponse | None = None


class AppointmentNotesSaveRequest(BaseModel):
    """Request for PATCH /appointments/:id/notes."""

    body: str = Field(max_length=50_000)
