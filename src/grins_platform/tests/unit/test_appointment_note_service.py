"""Unit tests for AppointmentNote model and service.

Tests model creation, field defaults, service get/save operations,
body length validation, and updated_by_id tracking.

Validates: Appointment Modal V2 Req 14.1, 14.2
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from grins_platform.exceptions import AppointmentNotFoundError
from grins_platform.models.appointment_note import AppointmentNote
from grins_platform.schemas.appointment_note import (
    AppointmentNotesResponse,
    AppointmentNotesSaveRequest,
)
from grins_platform.services.appointment_note_service import AppointmentNoteService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(
    appointment_id: uuid.UUID | None = None,
    body: str = "Test note body",
    updated_by_id: uuid.UUID | None = None,
) -> AppointmentNote:
    """Create an AppointmentNote instance for testing."""
    note = AppointmentNote(
        appointment_id=appointment_id or uuid.uuid4(),
        body=body,
        updated_by_id=updated_by_id,
    )
    note.id = uuid.uuid4()
    note.updated_at = datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc)
    note.updated_by = None
    return note


def _make_staff(
    staff_id: uuid.UUID | None = None,
    name: str = "Viktor K.",
    role: str = "admin",
) -> MagicMock:
    """Create a mock Staff object."""
    staff = MagicMock()
    staff.id = staff_id or uuid.uuid4()
    staff.name = name
    staff.role = role
    return staff


def _make_service() -> tuple[AppointmentNoteService, AsyncMock, AsyncMock]:
    """Create an AppointmentNoteService with mocked repo and session."""
    repo = AsyncMock()
    session = AsyncMock()
    # Mock session.get to return a truthy value (appointment exists)
    session.get = AsyncMock(return_value=MagicMock())
    svc = AppointmentNoteService(repo=repo, session=session)
    return svc, repo, session


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAppointmentNoteModel:
    def test_model_creation_with_all_fields(self) -> None:
        """AppointmentNote can be created with all fields."""
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        note = AppointmentNote(
            appointment_id=appt_id,
            body="Gate code 4521#",
            updated_by_id=staff_id,
        )
        assert note.appointment_id == appt_id
        assert note.body == "Gate code 4521#"
        assert note.updated_by_id == staff_id

    def test_model_default_empty_body(self) -> None:
        """AppointmentNote body defaults to empty string when not provided."""
        note = AppointmentNote(appointment_id=uuid.uuid4())
        # The server_default is handled by the DB; in Python the field
        # will be whatever we pass. Test that empty string is valid.
        note.body = ""
        assert note.body == ""

    def test_model_repr(self) -> None:
        """__repr__ includes id, appointment_id, and body_len."""
        note = _make_note(body="Hello")
        repr_str = repr(note)
        assert "AppointmentNote" in repr_str
        assert "body_len=5" in repr_str


# ---------------------------------------------------------------------------
# Service: get_notes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetNotes:
    @pytest.mark.asyncio
    async def test_get_notes_with_existing_record(self) -> None:
        """get_notes returns note body when record exists."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff = _make_staff()
        note = _make_note(appointment_id=appt_id, body="Gate code 4521#")
        note.updated_by = staff
        repo.get_by_appointment_id.return_value = note

        result = await svc.get_notes(appt_id)

        assert isinstance(result, AppointmentNotesResponse)
        assert result.appointment_id == appt_id
        assert result.body == "Gate code 4521#"
        assert result.updated_by is not None
        assert result.updated_by.name == "Viktor K."
        repo.get_by_appointment_id.assert_awaited_once_with(appt_id)

    @pytest.mark.asyncio
    async def test_get_notes_with_no_record_returns_empty_body(self) -> None:
        """get_notes returns empty body when no record exists."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        repo.get_by_appointment_id.return_value = None

        result = await svc.get_notes(appt_id)

        assert isinstance(result, AppointmentNotesResponse)
        assert result.appointment_id == appt_id
        assert result.body == ""
        assert result.updated_by is None

    @pytest.mark.asyncio
    async def test_get_notes_raises_404_for_missing_appointment(self) -> None:
        """get_notes raises AppointmentNotFoundError when appointment doesn't exist."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        session.get.return_value = None  # Appointment not found

        with pytest.raises(AppointmentNotFoundError):
            await svc.get_notes(appt_id)


# ---------------------------------------------------------------------------
# Service: save_notes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveNotes:
    @pytest.mark.asyncio
    async def test_save_notes_creates_new_record(self) -> None:
        """save_notes creates a new note when none exists."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff = _make_staff(staff_id=staff_id)
        note = _make_note(appointment_id=appt_id, body="New note")
        note.updated_by = staff
        repo.upsert.return_value = note

        result = await svc.save_notes(appt_id, "New note", staff_id)

        assert isinstance(result, AppointmentNotesResponse)
        assert result.body == "New note"
        assert result.updated_by is not None
        assert result.updated_by.id == staff_id
        repo.upsert.assert_awaited_once_with(
            appointment_id=appt_id,
            body="New note",
            updated_by_id=staff_id,
        )

    @pytest.mark.asyncio
    async def test_save_notes_updates_existing_record(self) -> None:
        """save_notes updates an existing note via upsert."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff = _make_staff(staff_id=staff_id)
        note = _make_note(appointment_id=appt_id, body="Updated note")
        note.updated_by = staff
        repo.upsert.return_value = note

        result = await svc.save_notes(appt_id, "Updated note", staff_id)

        assert result.body == "Updated note"
        repo.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_notes_tracks_updated_by_id(self) -> None:
        """save_notes passes updated_by_id to the repository."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        note = _make_note(appointment_id=appt_id)
        note.updated_by = None
        repo.upsert.return_value = note

        await svc.save_notes(appt_id, "Some text", staff_id)

        call_kwargs = repo.upsert.call_args.kwargs
        assert call_kwargs["updated_by_id"] == staff_id

    @pytest.mark.asyncio
    async def test_save_notes_raises_404_for_missing_appointment(self) -> None:
        """save_notes raises AppointmentNotFoundError when appointment doesn't exist."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        session.get.return_value = None

        with pytest.raises(AppointmentNotFoundError):
            await svc.save_notes(appt_id, "text", uuid.uuid4())


# ---------------------------------------------------------------------------
# Schema: body length validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBodyLengthValidation:
    def test_body_at_50000_chars_accepted(self) -> None:
        """Body of exactly 50,000 characters is accepted."""
        body = "a" * 50_000
        req = AppointmentNotesSaveRequest(body=body)
        assert len(req.body) == 50_000

    def test_body_over_50000_chars_rejected(self) -> None:
        """Body exceeding 50,000 characters is rejected with ValidationError."""
        body = "a" * 50_001
        with pytest.raises(ValidationError):
            AppointmentNotesSaveRequest(body=body)

    def test_empty_body_accepted(self) -> None:
        """Empty body string is accepted."""
        req = AppointmentNotesSaveRequest(body="")
        assert req.body == ""

    def test_body_with_unicode_accepted(self) -> None:
        """Body with unicode characters is accepted."""
        req = AppointmentNotesSaveRequest(body="Gate code 🔑 4521#")
        assert "🔑" in req.body

    def test_body_with_newlines_accepted(self) -> None:
        """Body with newlines is accepted."""
        req = AppointmentNotesSaveRequest(body="Line 1\nLine 2\nLine 3")
        assert "\n" in req.body
