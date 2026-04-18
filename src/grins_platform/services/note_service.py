"""NoteService for unified cross-stage notes timeline.

Provides CRUD operations for notes and cross-stage threading via
origin_lead_id. Notes follow the lead → sales entry → customer →
appointment chain, with merged timelines at each stage.

Validates: april-16th-fixes-enhancements Requirement 4
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from grins_platform.log_config import LoggerMixin
from grins_platform.models.note import Note
from grins_platform.models.staff import Staff
from grins_platform.schemas.note import NoteResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Mapping from subject_type to display stage tag
STAGE_TAG_MAP: dict[str, str] = {
    "lead": "Lead",
    "sales_entry": "Sales",
    "customer": "Customer",
    "appointment": "Appointment",
}

VALID_SUBJECT_TYPES = frozenset(STAGE_TAG_MAP.keys())


class NoteNotFoundError(Exception):
    """Raised when a note is not found."""

    def __init__(self, note_id: UUID) -> None:
        self.note_id = note_id
        super().__init__(f"Note {note_id} not found")


class NotePermissionError(Exception):
    """Raised when an actor lacks permission to modify a note."""

    def __init__(self, note_id: UUID, actor_id: UUID) -> None:
        self.note_id = note_id
        self.actor_id = actor_id
        super().__init__(
            f"Actor {actor_id} does not have permission to modify note {note_id}"
        )


class NoteService(LoggerMixin):
    """Service for unified cross-stage notes timeline operations.

    Handles note CRUD, cross-stage threading via origin_lead_id,
    merged timeline queries, and system stage-transition notes.

    Attributes:
        session: SQLAlchemy async session for database operations.

    Validates: april-16th-fixes-enhancements Requirement 4
    """

    DOMAIN = "notes"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize NoteService with a database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        super().__init__()
        self.session = session

    async def list_notes(
        self,
        subject_type: str,
        subject_id: UUID,
    ) -> list[NoteResponse]:
        """Return merged timeline for a subject.

        For leads: returns notes WHERE subject_type='lead' AND subject_id=id.
        For other types: returns notes WHERE (subject_type=X AND subject_id=Y)
        OR (origin_lead_id=Y when subject_type is 'lead' context is available).

        The merged timeline includes direct notes on the subject plus notes
        linked via origin_lead_id for cross-stage visibility.

        Results are ordered by created_at DESC (newest first).

        Args:
            subject_type: Entity type ('lead', 'sales_entry', 'customer',
                'appointment').
            subject_id: UUID of the subject entity.

        Returns:
            List of NoteResponse ordered by created_at descending.

        Validates: Requirement 4.2, 4.4, 4.5, 4.7
        """
        self.log_started(
            "list_notes",
            subject_type=subject_type,
            subject_id=str(subject_id),
        )

        # Build query conditions
        conditions = [
            (Note.subject_type == subject_type)
            & (Note.subject_id == subject_id)
            & (Note.is_deleted == False),  # noqa: E712
        ]

        # For non-lead subjects, also include notes linked via origin_lead_id
        # This enables cross-stage visibility: notes created on a lead appear
        # on the sales entry or customer that the lead was routed to.
        if subject_type != "lead":
            conditions.append(
                (Note.origin_lead_id == subject_id) & (Note.is_deleted == False)  # noqa: E712
            )

        stmt = (
            select(Note)
            .options(selectinload(Note.author))
            .where(or_(*conditions))
            .order_by(Note.created_at.desc())
        )

        result = await self.session.execute(stmt)
        notes = list(result.scalars().all())

        responses = [self._to_response(note) for note in notes]

        self.log_completed(
            "list_notes",
            subject_type=subject_type,
            subject_id=str(subject_id),
            count=len(responses),
        )
        return responses

    async def create_note(
        self,
        subject_type: str,
        subject_id: UUID,
        body: str,
        author_id: UUID,
        origin_lead_id: UUID | None = None,
    ) -> NoteResponse:
        """Create a new note on a subject.

        Args:
            subject_type: Entity type ('lead', 'sales_entry', 'customer',
                'appointment').
            subject_id: UUID of the subject entity.
            body: Note content text.
            author_id: UUID of the staff member creating the note.
            origin_lead_id: Optional cross-stage threading link to the
                originating lead.

        Returns:
            NoteResponse with the created note data.

        Validates: Requirement 4.3, 4.7
        """
        self.log_started(
            "create_note",
            subject_type=subject_type,
            subject_id=str(subject_id),
            author_id=str(author_id),
        )

        # If creating a note on a lead, set origin_lead_id to the lead itself
        # so cross-stage queries can find it later.
        effective_origin_lead_id = origin_lead_id
        if subject_type == "lead" and origin_lead_id is None:
            effective_origin_lead_id = subject_id

        note = Note(
            subject_type=subject_type,
            subject_id=subject_id,
            author_id=author_id,
            body=body,
            origin_lead_id=effective_origin_lead_id,
            is_system=False,
            is_deleted=False,
        )

        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note, attribute_names=["author"])

        response = self._to_response(note)

        self.log_completed(
            "create_note",
            note_id=str(note.id),
            subject_type=subject_type,
            subject_id=str(subject_id),
        )
        return response

    async def update_note(
        self,
        note_id: UUID,
        body: str,
        actor_id: UUID,
    ) -> NoteResponse:
        """Update a note's body. Only the original author or an admin can edit.

        Args:
            note_id: UUID of the note to update.
            body: New note content text.
            actor_id: UUID of the staff member performing the update.

        Returns:
            NoteResponse with the updated note data.

        Raises:
            NoteNotFoundError: If the note does not exist or is deleted.
            NotePermissionError: If the actor is not the author and not admin.

        Validates: Requirement 4.7
        """
        self.log_started("update_note", note_id=str(note_id), actor_id=str(actor_id))

        note = await self._get_note_or_raise(note_id)

        # Permission check: author or admin
        if note.author_id != actor_id:
            is_admin = await self._is_admin(actor_id)
            if not is_admin:
                self.log_rejected(
                    "update_note",
                    reason="not_author_or_admin",
                    note_id=str(note_id),
                    actor_id=str(actor_id),
                )
                raise NotePermissionError(note_id, actor_id)

        note.body = body
        note.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(note, attribute_names=["author"])

        response = self._to_response(note)

        self.log_completed("update_note", note_id=str(note_id))
        return response

    async def delete_note(
        self,
        note_id: UUID,
        actor_id: UUID,
    ) -> None:
        """Soft-delete a note by setting is_deleted=True.

        Args:
            note_id: UUID of the note to delete.
            actor_id: UUID of the staff member performing the deletion.

        Raises:
            NoteNotFoundError: If the note does not exist or is already deleted.
            NotePermissionError: If the actor is not the author and not admin.

        Validates: Requirement 4.7
        """
        self.log_started("delete_note", note_id=str(note_id), actor_id=str(actor_id))

        note = await self._get_note_or_raise(note_id)

        # Permission check: author or admin
        if note.author_id != actor_id:
            is_admin = await self._is_admin(actor_id)
            if not is_admin:
                self.log_rejected(
                    "delete_note",
                    reason="not_author_or_admin",
                    note_id=str(note_id),
                    actor_id=str(actor_id),
                )
                raise NotePermissionError(note_id, actor_id)

        note.is_deleted = True
        note.updated_at = datetime.now(timezone.utc)

        await self.session.flush()

        self.log_completed("delete_note", note_id=str(note_id))

    async def create_stage_transition_note(
        self,
        from_type: str,
        from_id: UUID,
        to_type: str,
        to_id: UUID,
        actor_id: UUID,
    ) -> NoteResponse:
        """Create a system note recording a stage transition.

        Called when a lead is routed to a sales entry or customer.
        The note is created on the destination subject with is_system=True
        and origin_lead_id set to the source lead for cross-stage threading.

        Args:
            from_type: Source entity type (e.g., 'lead').
            from_id: UUID of the source entity.
            to_type: Destination entity type (e.g., 'sales_entry', 'customer').
            to_id: UUID of the destination entity.
            actor_id: UUID of the staff member who triggered the transition.

        Returns:
            NoteResponse with the created system note.

        Validates: Requirement 4.4, 4.5, 4.6
        """
        self.log_started(
            "create_stage_transition_note",
            from_type=from_type,
            from_id=str(from_id),
            to_type=to_type,
            to_id=str(to_id),
            actor_id=str(actor_id),
        )

        from_label = STAGE_TAG_MAP.get(from_type, from_type.title())
        to_label = STAGE_TAG_MAP.get(to_type, to_type.title())
        body = f"Stage transition: {from_label} → {to_label}"

        # Set origin_lead_id for cross-stage threading
        origin_lead_id = from_id if from_type == "lead" else None

        note = Note(
            subject_type=to_type,
            subject_id=to_id,
            author_id=actor_id,
            body=body,
            origin_lead_id=origin_lead_id,
            is_system=True,
            is_deleted=False,
        )

        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note, attribute_names=["author"])

        response = self._to_response(note)

        self.log_completed(
            "create_stage_transition_note",
            note_id=str(note.id),
            from_type=from_type,
            to_type=to_type,
        )
        return response

    # =========================================================================
    # Private helpers
    # =========================================================================

    async def _get_note_or_raise(self, note_id: UUID) -> Note:
        """Fetch a note by ID, raising NoteNotFoundError if missing or deleted.

        Args:
            note_id: UUID of the note.

        Returns:
            The Note instance.

        Raises:
            NoteNotFoundError: If note not found or is soft-deleted.
        """
        stmt = (
            select(Note)
            .options(selectinload(Note.author))
            .where(Note.id == note_id, Note.is_deleted == False)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        note = result.scalar_one_or_none()

        if note is None:
            raise NoteNotFoundError(note_id)

        return note

    async def _is_admin(self, staff_id: UUID) -> bool:
        """Check if a staff member has the admin role.

        Args:
            staff_id: UUID of the staff member.

        Returns:
            True if the staff member is an admin, False otherwise.
        """
        stmt = select(Staff.role).where(Staff.id == staff_id)
        result = await self.session.execute(stmt)
        role = result.scalar_one_or_none()
        return role == "admin"

    @staticmethod
    def _to_response(note: Note) -> NoteResponse:
        """Convert a Note model instance to a NoteResponse schema.

        Computes author_name from the joined Staff relationship and
        stage_tag from the subject_type.

        Args:
            note: Note model instance with author relationship loaded.

        Returns:
            NoteResponse schema instance.
        """
        author_name = note.author.name if note.author else "Unknown"
        stage_tag = STAGE_TAG_MAP.get(note.subject_type, note.subject_type.title())

        return NoteResponse(
            id=note.id,
            subject_type=note.subject_type,
            subject_id=note.subject_id,
            author_id=note.author_id,
            author_name=author_name,
            body=note.body,
            origin_lead_id=note.origin_lead_id,
            is_system=note.is_system,
            created_at=note.created_at,
            updated_at=note.updated_at,
            stage_tag=stage_tag,
        )
