"""AppointmentNote service for business logic.

Provides get and save operations for centralized appointment internal notes.

Validates: Appointment Modal V2 Req 5.3, 5.4, 5.5, 5.7, 10.2, 10.4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.appointment_note import (
    AppointmentNotesResponse,
    NoteAuthorResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from grins_platform.repositories.appointment_note_repository import (
        AppointmentNoteRepository,
    )


class AppointmentNoteService(LoggerMixin):
    """Service for appointment note operations.

    Validates: Appointment Modal V2 Req 5.3, 5.4, 5.5, 5.7, 10.2, 10.4
    """

    DOMAIN = "appointment_notes"

    def __init__(
        self,
        repo: AppointmentNoteRepository,
        session: AsyncSession,
    ) -> None:
        """Initialize service with repository and session.

        Args:
            repo: AppointmentNoteRepository instance
            session: AsyncSession for appointment existence checks
        """
        super().__init__()
        self.repo = repo
        self.session = session

    async def _check_appointment_exists(self, appointment_id: UUID) -> None:
        """Verify that the appointment exists, raise 404 if not.

        Args:
            appointment_id: Appointment UUID

        Raises:
            AppointmentNotFoundError: if appointment does not exist
        """
        from grins_platform.models.appointment import Appointment  # noqa: PLC0415

        result = await self.session.get(Appointment, appointment_id)
        if result is None:
            from grins_platform.exceptions import (  # noqa: PLC0415
                AppointmentNotFoundError,
            )

            raise AppointmentNotFoundError(appointment_id)

    def _build_response(
        self,
        appointment_id: UUID,
        body: str,
        updated_at: datetime,
        updated_by_author: NoteAuthorResponse | None,
    ) -> AppointmentNotesResponse:
        """Build an AppointmentNotesResponse from components.

        Args:
            appointment_id: Appointment UUID
            body: Note body text
            updated_at: Last update timestamp
            updated_by_author: Author info or None

        Returns:
            AppointmentNotesResponse
        """
        return AppointmentNotesResponse(
            appointment_id=appointment_id,
            body=body,
            updated_at=updated_at,
            updated_by=updated_by_author,
        )

    @staticmethod
    def _staff_to_author(staff: object) -> NoteAuthorResponse | None:
        """Convert a Staff ORM object to NoteAuthorResponse.

        Args:
            staff: Staff ORM instance or None

        Returns:
            NoteAuthorResponse or None
        """
        if staff is None:
            return None
        return NoteAuthorResponse(
            id=staff.id,  # type: ignore[union-attr]
            name=staff.name,  # type: ignore[union-attr]
            role=staff.role,  # type: ignore[union-attr]
        )

    async def get_notes(self, appointment_id: UUID) -> AppointmentNotesResponse:
        """Get notes for an appointment. Returns empty body if none exist.

        Args:
            appointment_id: Appointment UUID

        Returns:
            AppointmentNotesResponse with note data or empty defaults

        Raises:
            AppointmentNotFoundError: if appointment does not exist
        """
        self.log_started("get_notes", appointment_id=str(appointment_id))

        await self._check_appointment_exists(appointment_id)

        note = await self.repo.get_by_appointment_id(appointment_id)

        if note is None:
            self.log_completed("get_notes", found=False)
            return self._build_response(
                appointment_id=appointment_id,
                body="",
                updated_at=datetime.now(timezone.utc),
                updated_by_author=None,
            )

        author = self._staff_to_author(note.updated_by)
        self.log_completed("get_notes", found=True, body_len=len(note.body))
        return self._build_response(
            appointment_id=appointment_id,
            body=note.body,
            updated_at=note.updated_at,
            updated_by_author=author,
        )

    async def save_notes(
        self,
        appointment_id: UUID,
        body: str,
        updated_by_id: UUID | None,
    ) -> AppointmentNotesResponse:
        """Upsert notes for an appointment.

        Args:
            appointment_id: Appointment UUID
            body: Note body text
            updated_by_id: Staff UUID of the editor

        Returns:
            AppointmentNotesResponse with the saved note data

        Raises:
            AppointmentNotFoundError: if appointment does not exist
        """
        self.log_started(
            "save_notes",
            appointment_id=str(appointment_id),
            body_len=len(body),
        )

        await self._check_appointment_exists(appointment_id)

        note = await self.repo.upsert(
            appointment_id=appointment_id,
            body=body,
            updated_by_id=updated_by_id,
        )

        author = self._staff_to_author(note.updated_by)
        self.log_completed(
            "save_notes",
            appointment_id=str(appointment_id),
            note_id=str(note.id),
        )
        return self._build_response(
            appointment_id=appointment_id,
            body=note.body,
            updated_at=note.updated_at,
            updated_by_author=author,
        )
