"""AppointmentNote repository for database operations.

Validates: Appointment Modal V2 Req 5.3, 5.5
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from grins_platform.log_config import LoggerMixin
from grins_platform.models.appointment_note import AppointmentNote

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AppointmentNoteRepository(LoggerMixin):
    """Repository for appointment note database operations.

    Validates: Appointment Modal V2 Req 5.3, 5.5
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def get_by_appointment_id(
        self, appointment_id: UUID
    ) -> AppointmentNote | None:
        """Return the note for an appointment, or None.

        Args:
            appointment_id: Appointment UUID

        Returns:
            AppointmentNote instance or None
        """
        self.log_started(
            "get_by_appointment_id",
            appointment_id=str(appointment_id),
        )
        stmt = select(AppointmentNote).where(
            AppointmentNote.appointment_id == appointment_id
        )
        result = await self.session.execute(stmt)
        note: AppointmentNote | None = result.scalar_one_or_none()
        self.log_completed(
            "get_by_appointment_id",
            found=note is not None,
        )
        return note

    async def upsert(
        self,
        appointment_id: UUID,
        body: str,
        updated_by_id: UUID | None,
    ) -> AppointmentNote:
        """Create or update the note for an appointment.

        Uses PostgreSQL INSERT ... ON CONFLICT for atomic upsert.

        Args:
            appointment_id: Appointment UUID
            body: Note body text
            updated_by_id: Staff UUID of the editor

        Returns:
            The upserted AppointmentNote instance
        """
        self.log_started(
            "upsert",
            appointment_id=str(appointment_id),
            body_len=len(body),
        )
        now = datetime.now(timezone.utc)

        stmt = pg_insert(AppointmentNote).values(
            appointment_id=appointment_id,
            body=body,
            updated_at=now,
            updated_by_id=updated_by_id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["appointment_id"],
            set_={
                "body": body,
                "updated_at": now,
                "updated_by_id": updated_by_id,
            },
        )
        stmt = stmt.returning(AppointmentNote)
        result = await self.session.execute(stmt)
        note = result.scalar_one()

        # Expire and refresh to load relationships (updated_by, appointment)
        await self.session.flush()
        await self.session.refresh(note)

        self.log_completed("upsert", note_id=str(note.id))
        return note
