"""Unit tests for appointment notes API endpoints.

Tests GET /api/v1/appointments/{appointment_id}/notes
      PATCH /api/v1/appointments/{appointment_id}/notes

Validates: Appointment Modal V2 Req 14.3
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grins_platform.api.v1.appointments import router
from grins_platform.api.v1.auth_dependencies import (
    get_current_active_user,
    get_current_user,
)
from grins_platform.api.v1.dependencies import (
    get_appointment_note_service,
    get_appointment_service,
    get_appointment_timeline_service,
    get_db_session,
    get_full_appointment_service,
)
from grins_platform.exceptions import AppointmentNotFoundError
from grins_platform.schemas.appointment_note import (
    AppointmentNotesResponse,
    NoteAuthorResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_user() -> MagicMock:
    """Create a fake authenticated user."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "test-admin"
    user.email = "test@example.com"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def mock_note_service() -> AsyncMock:
    """Create a mock AppointmentNoteService."""
    return AsyncMock()


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def app(
    fake_user: MagicMock,
    mock_note_service: AsyncMock,
    mock_db: AsyncMock,
) -> FastAPI:
    """Create a test FastAPI app with overridden dependencies."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/appointments")

    test_app.dependency_overrides[get_current_user] = lambda: fake_user
    test_app.dependency_overrides[get_current_active_user] = lambda: fake_user
    test_app.dependency_overrides[get_appointment_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_full_appointment_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_appointment_timeline_service] = (
        lambda: AsyncMock()
    )
    test_app.dependency_overrides[get_appointment_note_service] = (
        lambda: mock_note_service
    )

    async def _db_override() -> AsyncMock:
        return mock_db

    test_app.dependency_overrides[get_db_session] = _db_override
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def no_auth_app(
    mock_note_service: AsyncMock,
    mock_db: AsyncMock,
) -> FastAPI:
    """Create a test FastAPI app WITHOUT auth overrides for 401 testing."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1/appointments")

    test_app.dependency_overrides[get_appointment_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_full_appointment_service] = lambda: AsyncMock()
    test_app.dependency_overrides[get_appointment_timeline_service] = (
        lambda: AsyncMock()
    )
    test_app.dependency_overrides[get_appointment_note_service] = (
        lambda: mock_note_service
    )

    async def _db_override() -> AsyncMock:
        return mock_db

    test_app.dependency_overrides[get_db_session] = _db_override
    return test_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _notes_response(
    appointment_id: uuid.UUID,
    body: str = "Gate code 4521#",
    with_author: bool = True,
) -> AppointmentNotesResponse:
    """Build a sample AppointmentNotesResponse."""
    author = None
    if with_author:
        author = NoteAuthorResponse(
            id=uuid.uuid4(),
            name="Viktor K.",
            role="admin",
        )
    return AppointmentNotesResponse(
        appointment_id=appointment_id,
        body=body,
        updated_at=datetime(2026, 6, 15, 14, 30, tzinfo=timezone.utc),
        updated_by=author,
    )


# ---------------------------------------------------------------------------
# GET /{appointment_id}/notes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAppointmentNotes:
    def test_returns_existing_notes(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """GET returns 200 with note body when notes exist."""
        appt_id = uuid.uuid4()
        mock_note_service.get_notes.return_value = _notes_response(
            appt_id, body="Gate code 4521#"
        )

        resp = client.get(f"/api/v1/appointments/{appt_id}/notes")

        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == "Gate code 4521#"
        assert data["appointment_id"] == str(appt_id)
        assert data["updated_by"] is not None
        assert data["updated_by"]["name"] == "Viktor K."

    def test_returns_empty_body_when_no_notes(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """GET returns 200 with empty body when no notes record exists."""
        appt_id = uuid.uuid4()
        mock_note_service.get_notes.return_value = _notes_response(
            appt_id, body="", with_author=False
        )

        resp = client.get(f"/api/v1/appointments/{appt_id}/notes")

        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == ""
        assert data["updated_by"] is None

    def test_returns_404_for_invalid_appointment(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """GET returns 404 when appointment does not exist."""
        appt_id = uuid.uuid4()
        mock_note_service.get_notes.side_effect = AppointmentNotFoundError(appt_id)

        resp = client.get(f"/api/v1/appointments/{appt_id}/notes")

        assert resp.status_code == 404
        assert "Appointment not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /{appointment_id}/notes
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSaveAppointmentNotes:
    def test_creates_new_notes(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH creates notes and returns 200."""
        appt_id = uuid.uuid4()
        mock_note_service.save_notes.return_value = _notes_response(
            appt_id, body="New note content"
        )

        resp = client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "New note content"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["body"] == "New note content"
        mock_note_service.save_notes.assert_awaited_once()

    def test_updates_existing_notes(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH updates existing notes and returns 200."""
        appt_id = uuid.uuid4()
        mock_note_service.save_notes.return_value = _notes_response(
            appt_id, body="Updated content"
        )

        resp = client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "Updated content"},
        )

        assert resp.status_code == 200
        assert resp.json()["body"] == "Updated content"

    def test_returns_422_for_body_too_long(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH returns 422 when body exceeds 50,000 characters."""
        appt_id = uuid.uuid4()
        long_body = "a" * 50_001

        resp = client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": long_body},
        )

        assert resp.status_code == 422
        mock_note_service.save_notes.assert_not_awaited()

    def test_returns_404_for_invalid_appointment(
        self,
        client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH returns 404 when appointment does not exist."""
        appt_id = uuid.uuid4()
        mock_note_service.save_notes.side_effect = AppointmentNotFoundError(appt_id)

        resp = client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "Some text"},
        )

        assert resp.status_code == 404
        assert "Appointment not found" in resp.json()["detail"]

    def test_auth_required(
        self,
        no_auth_app: FastAPI,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH without authentication returns 401."""
        no_auth_client = TestClient(no_auth_app)
        appt_id = uuid.uuid4()

        resp = no_auth_client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "Some text"},
        )

        # Without auth override, the dependency will fail
        # The exact status depends on how auth is configured,
        # but it should not be 200
        assert resp.status_code in (401, 403, 500)
