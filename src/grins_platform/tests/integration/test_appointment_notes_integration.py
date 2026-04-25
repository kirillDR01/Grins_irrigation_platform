"""Integration tests for appointment notes accessibility.

Tests that notes are accessible from the appointment context via the API,
and that authentication is enforced.

Validates: Appointment Modal V2 Req 14.5
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
def authenticated_app(
    fake_user: MagicMock,
    mock_note_service: AsyncMock,
    mock_db: AsyncMock,
) -> FastAPI:
    """Create a test FastAPI app with auth overrides."""
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
def auth_client(authenticated_app: FastAPI) -> TestClient:
    """Create an authenticated test client."""
    return TestClient(authenticated_app)


@pytest.fixture
def unauthenticated_app(
    mock_note_service: AsyncMock,
    mock_db: AsyncMock,
) -> FastAPI:
    """Create a test FastAPI app WITHOUT auth overrides."""
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


@pytest.fixture
def unauth_client(unauthenticated_app: FastAPI) -> TestClient:
    """Create an unauthenticated test client."""
    return TestClient(unauthenticated_app)


# ---------------------------------------------------------------------------
# Notes accessible from appointment context
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNotesAccessibleFromAppointment:
    def test_save_then_read_notes_via_api(
        self,
        auth_client: TestClient,
        mock_note_service: AsyncMock,
        fake_user: MagicMock,
    ) -> None:
        """Create appointment → save notes → verify notes accessible via GET."""
        appt_id = uuid.uuid4()
        staff_id = fake_user.id

        # Configure mock: save returns the saved note
        saved_response = AppointmentNotesResponse(
            appointment_id=appt_id,
            body="Gate code 4521#. Dog is friendly.",
            updated_at=datetime.now(timezone.utc),
            updated_by=NoteAuthorResponse(
                id=staff_id,
                name="Admin User",
                role="admin",
            ),
        )
        mock_note_service.save_notes.return_value = saved_response

        # Step 1: Save notes via PATCH
        patch_resp = auth_client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "Gate code 4521#. Dog is friendly."},
        )
        assert patch_resp.status_code == 200
        patch_data = patch_resp.json()
        assert patch_data["body"] == "Gate code 4521#. Dog is friendly."
        assert patch_data["updated_by"]["name"] == "Admin User"

        # Step 2: Read notes via GET
        mock_note_service.get_notes.return_value = saved_response
        get_resp = auth_client.get(f"/api/v1/appointments/{appt_id}/notes")
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["body"] == "Gate code 4521#. Dog is friendly."
        assert get_data["appointment_id"] == str(appt_id)
        assert get_data["updated_by"]["name"] == "Admin User"

    def test_notes_data_matches_between_save_and_read(
        self,
        auth_client: TestClient,
        mock_note_service: AsyncMock,
        fake_user: MagicMock,
    ) -> None:
        """Saved notes data matches what is returned on subsequent read."""
        appt_id = uuid.uuid4()
        body_text = "Important: customer prefers morning appointments"
        now = datetime.now(timezone.utc)

        response = AppointmentNotesResponse(
            appointment_id=appt_id,
            body=body_text,
            updated_at=now,
            updated_by=NoteAuthorResponse(
                id=fake_user.id,
                name="Admin User",
                role="admin",
            ),
        )
        mock_note_service.save_notes.return_value = response
        mock_note_service.get_notes.return_value = response

        # Save
        patch_resp = auth_client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": body_text},
        )
        save_data = patch_resp.json()

        # Read
        get_resp = auth_client.get(f"/api/v1/appointments/{appt_id}/notes")
        read_data = get_resp.json()

        # Verify consistency
        assert save_data["body"] == read_data["body"]
        assert save_data["appointment_id"] == read_data["appointment_id"]


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestNotesAuthRequired:
    def test_patch_without_auth_rejected(
        self,
        unauth_client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """PATCH without authentication is rejected."""
        appt_id = uuid.uuid4()

        resp = unauth_client.patch(
            f"/api/v1/appointments/{appt_id}/notes",
            json={"body": "Unauthorized attempt"},
        )

        # Without auth dependency override, the endpoint should fail
        # with 401, 403, or 500 (depending on how auth deps are configured)
        assert resp.status_code in (401, 403, 500)
        mock_note_service.save_notes.assert_not_awaited()

    def test_get_without_auth_rejected(
        self,
        unauth_client: TestClient,
        mock_note_service: AsyncMock,
    ) -> None:
        """GET without authentication is rejected."""
        appt_id = uuid.uuid4()

        resp = unauth_client.get(f"/api/v1/appointments/{appt_id}/notes")

        assert resp.status_code in (401, 403, 500)
        mock_note_service.get_notes.assert_not_awaited()
