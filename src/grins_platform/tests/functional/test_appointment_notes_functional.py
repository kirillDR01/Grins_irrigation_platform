"""Functional tests for appointment notes lifecycle.

Tests the full notes lifecycle as a user would experience it:
create appointment → save notes → read → update → read → verify.

Validates: Appointment Modal V2 Req 14.4
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from grins_platform.exceptions import AppointmentNotFoundError
from grins_platform.models.appointment_note import AppointmentNote
from grins_platform.services.appointment_note_service import AppointmentNoteService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_note(
    appointment_id: uuid.UUID,
    body: str = "",
    updated_by_id: uuid.UUID | None = None,
    staff: MagicMock | None = None,
) -> AppointmentNote:
    """Create an AppointmentNote instance for testing."""
    note = AppointmentNote(
        appointment_id=appointment_id,
        body=body,
        updated_by_id=updated_by_id,
    )
    note.id = uuid.uuid4()
    note.updated_at = datetime.now(timezone.utc)
    note.updated_by = staff
    return note


def _make_staff(
    staff_id: uuid.UUID | None = None,
    name: str = "Admin User",
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
    # Default: appointment exists
    session.get = AsyncMock(return_value=MagicMock())
    svc = AppointmentNoteService(repo=repo, session=session)
    return svc, repo, session


# ---------------------------------------------------------------------------
# Notes lifecycle: create → save → read → update → read
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestNotesLifecycle:
    async def test_save_then_read_then_update_then_read(self) -> None:
        """Full lifecycle: save notes → read → update → read → verify changes."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff1_id = uuid.uuid4()
        staff2_id = uuid.uuid4()
        staff1 = _make_staff(staff_id=staff1_id, name="Tech A", role="tech")
        staff2 = _make_staff(staff_id=staff2_id, name="Admin B", role="admin")

        # Step 1: Save initial notes
        note_v1 = _make_note(
            appt_id, body="Gate code 4521#", updated_by_id=staff1_id, staff=staff1
        )
        repo.upsert.return_value = note_v1

        result1 = await svc.save_notes(appt_id, "Gate code 4521#", staff1_id)
        assert result1.body == "Gate code 4521#"
        assert result1.updated_by is not None
        assert result1.updated_by.name == "Tech A"

        # Step 2: Read notes back
        repo.get_by_appointment_id.return_value = note_v1
        result2 = await svc.get_notes(appt_id)
        assert result2.body == "Gate code 4521#"
        assert result2.updated_by is not None
        assert result2.updated_by.name == "Tech A"

        # Step 3: Update notes with different staff
        note_v2 = _make_note(
            appt_id,
            body="Gate code 4521#. Dog is friendly.",
            updated_by_id=staff2_id,
            staff=staff2,
        )
        repo.upsert.return_value = note_v2

        result3 = await svc.save_notes(
            appt_id, "Gate code 4521#. Dog is friendly.", staff2_id
        )
        assert result3.body == "Gate code 4521#. Dog is friendly."
        assert result3.updated_by is not None
        assert result3.updated_by.name == "Admin B"

        # Step 4: Read updated notes
        repo.get_by_appointment_id.return_value = note_v2
        result4 = await svc.get_notes(appt_id)
        assert result4.body == "Gate code 4521#. Dog is friendly."
        assert result4.updated_by is not None
        assert result4.updated_by.name == "Admin B"


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestCascadeDelete:
    async def test_notes_gone_after_appointment_deleted(self) -> None:
        """After appointment deletion, notes are no longer accessible.

        Simulates cascade: after appointment is deleted, session.get returns
        None for the appointment, so get_notes raises 404.
        """
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff = _make_staff()

        # Step 1: Save notes (appointment exists)
        note = _make_note(appt_id, body="Some notes", staff=staff)
        repo.upsert.return_value = note
        result = await svc.save_notes(appt_id, "Some notes", staff.id)
        assert result.body == "Some notes"

        # Step 2: Simulate appointment deletion (cascade removes notes)
        session.get.return_value = None  # Appointment no longer exists

        # Step 3: Attempting to read notes raises 404
        with pytest.raises(AppointmentNotFoundError):
            await svc.get_notes(appt_id)


# ---------------------------------------------------------------------------
# Upsert creates on first save
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestUpsertCreatesOnFirstSave:
    async def test_first_save_creates_note_record(self) -> None:
        """PATCH on a new appointment creates the notes record via upsert."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff = _make_staff(staff_id=staff_id)

        # No existing note
        repo.get_by_appointment_id.return_value = None

        # Upsert creates a new record
        new_note = _make_note(
            appt_id, body="First note ever", updated_by_id=staff_id, staff=staff
        )
        repo.upsert.return_value = new_note

        result = await svc.save_notes(appt_id, "First note ever", staff_id)

        assert result.body == "First note ever"
        repo.upsert.assert_awaited_once_with(
            appointment_id=appt_id,
            body="First note ever",
            updated_by_id=staff_id,
        )


# ---------------------------------------------------------------------------
# Empty body allowed
# ---------------------------------------------------------------------------


@pytest.mark.functional
@pytest.mark.asyncio
class TestEmptyBodyAllowed:
    async def test_save_empty_body_accepted(self) -> None:
        """PATCH with empty string body is accepted and stored."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff = _make_staff(staff_id=staff_id)

        note = _make_note(appt_id, body="", updated_by_id=staff_id, staff=staff)
        repo.upsert.return_value = note

        result = await svc.save_notes(appt_id, "", staff_id)

        assert result.body == ""
        repo.upsert.assert_awaited_once_with(
            appointment_id=appt_id,
            body="",
            updated_by_id=staff_id,
        )

    async def test_read_empty_body_after_save(self) -> None:
        """After saving empty body, reading returns empty body."""
        svc, repo, session = _make_service()
        appt_id = uuid.uuid4()
        staff = _make_staff()

        note = _make_note(appt_id, body="", staff=staff)
        repo.upsert.return_value = note
        await svc.save_notes(appt_id, "", staff.id)

        repo.get_by_appointment_id.return_value = note
        result = await svc.get_notes(appt_id)
        assert result.body == ""
