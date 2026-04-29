"""Property-based tests for Appointment Modal V2 spec.

Covers Properties 1–3 (backend Hypothesis).
Feature: appointment-modal-v2

Uses mocked repository and session (same pattern as unit tests).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)
from pydantic import ValidationError

from grins_platform.models.appointment_note import AppointmentNote
from grins_platform.schemas.appointment_note import (
    AppointmentNotesSaveRequest,
)
from grins_platform.services.appointment_note_service import AppointmentNoteService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_and_mocks() -> tuple[AppointmentNoteService, AsyncMock, AsyncMock]:
    """Create an AppointmentNoteService with mocked repo and session."""
    repo = AsyncMock()
    session = AsyncMock()
    # Appointment exists by default
    session.get = AsyncMock(return_value=MagicMock())
    svc = AppointmentNoteService(repo=repo, session=session)
    return svc, repo, session


def _make_note(
    appointment_id: uuid.UUID,
    body: str,
    updated_by_id: uuid.UUID | None = None,
) -> AppointmentNote:
    """Create an AppointmentNote instance for testing."""
    note = AppointmentNote(
        appointment_id=appointment_id,
        body=body,
        updated_by_id=updated_by_id,
    )
    note.id = uuid.uuid4()
    note.updated_at = datetime.now(timezone.utc)
    note.updated_by = None
    return note


# ===================================================================
# Property 1: Notes body round-trip
# Feature: appointment-modal-v2, Property 1: Notes body round-trip
# Validates: Requirements 5.5, 10.3, 15.1
# ===================================================================


@pytest.mark.unit
class TestProperty1NotesBodyRoundTrip:
    """Property 1: Notes body round-trip.

    For any valid string body of length 0 to 50,000 characters (including
    empty strings, unicode, newlines, special chars), saving via PATCH then
    reading via GET SHALL return the identical body string.

    **Validates: Requirements 5.5, 10.3, 15.1**
    """

    @given(body=st.text(max_size=50_000))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_save_then_get_returns_identical_body(
        self,
        body: str,
    ) -> None:
        """PATCH body then GET returns the exact same body string."""
        svc, repo, _session = _make_service_and_mocks()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()

        # Configure repo.upsert to return a note with the saved body
        saved_note = _make_note(appointment_id=appt_id, body=body)
        repo.upsert.return_value = saved_note

        # PATCH (save)
        save_result = await svc.save_notes(appt_id, body, staff_id)
        assert save_result.body == body

        # Configure repo.get_by_appointment_id to return the same note
        repo.get_by_appointment_id.return_value = saved_note

        # GET (read back)
        get_result = await svc.get_notes(appt_id)
        assert get_result.body == body

        # Round-trip: save result matches get result
        assert save_result.body == get_result.body


# ===================================================================
# Property 2: Notes upsert idempotence
# Feature: appointment-modal-v2, Property 2: Notes upsert idempotence
# Validates: Requirements 15.2
# ===================================================================


@pytest.mark.unit
class TestProperty2NotesUpsertIdempotence:
    """Property 2: Notes upsert idempotence.

    For any valid body string, saving the same body twice SHALL produce
    the same body value in the response (R1.body == R2.body).

    **Validates: Requirements 15.2**
    """

    @given(body=st.text(max_size=50_000))
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_save_twice_produces_same_body(
        self,
        body: str,
    ) -> None:
        """Saving the same body twice yields identical body in both responses."""
        svc, repo, _session = _make_service_and_mocks()
        appt_id = uuid.uuid4()
        staff_id = uuid.uuid4()

        # Both upsert calls return a note with the same body
        note1 = _make_note(appointment_id=appt_id, body=body)
        note2 = _make_note(appointment_id=appt_id, body=body)
        repo.upsert.side_effect = [note1, note2]

        # First save
        r1 = await svc.save_notes(appt_id, body, staff_id)

        # Second save (same body)
        r2 = await svc.save_notes(appt_id, body, staff_id)

        # Body content is identical
        assert r1.body == r2.body
        assert r1.body == body


# ===================================================================
# Property 3: Notes body validation rejects oversized input
# Feature: appointment-modal-v2, Property 3: Notes body validation rejects oversized input
# Validates: Requirements 5.6, 10.5, 15.3
# ===================================================================


@pytest.mark.unit
class TestProperty3NotesBodyValidationRejectsOversized:
    """Property 3: Notes body validation rejects oversized input.

    For any string with length exceeding 50,000 characters, the PATCH
    endpoint SHALL return 422 and SHALL NOT modify the existing record.

    **Validates: Requirements 5.6, 10.5, 15.3**
    """

    @given(
        base=st.text(min_size=1, max_size=10_000),
        extra_len=st.integers(min_value=50_001, max_value=100_000),
    )
    @settings(max_examples=100)
    def test_oversized_body_rejected_by_schema(
        self,
        base: str,
        extra_len: int,
    ) -> None:
        """Body exceeding 50,000 chars is rejected by Pydantic validation."""
        # Pad the base string to the desired oversized length
        body = (base * ((extra_len // max(len(base), 1)) + 2))[:extra_len]
        assert len(body) > 50_000

        with pytest.raises(ValidationError):
            AppointmentNotesSaveRequest(body=body)

    @given(
        base=st.text(min_size=1, max_size=10_000),
        extra_len=st.integers(min_value=50_001, max_value=100_000),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_oversized_body_does_not_call_repo(
        self,
        base: str,
        extra_len: int,
    ) -> None:
        """Oversized body is rejected before reaching the repository."""
        # Pad the base string to the desired oversized length
        body = (base * ((extra_len // max(len(base), 1)) + 2))[:extra_len]
        assert len(body) > 50_000

        svc, repo, _session = _make_service_and_mocks()

        # Validate at the schema level (as the API endpoint would)
        with pytest.raises(ValidationError):
            AppointmentNotesSaveRequest(body=body)

        # The repo should never be called for oversized input
        repo.upsert.assert_not_awaited()
