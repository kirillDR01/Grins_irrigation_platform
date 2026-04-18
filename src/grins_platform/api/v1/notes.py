"""
Notes API endpoints.

This module provides REST API endpoints for the unified notes timeline,
supporting notes on leads, sales entries, customers, and direct note
operations (edit, delete).

Validates: april-16th-fixes-enhancements Requirement 4
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from grins_platform.services.note_service import (
    NoteNotFoundError,
    NotePermissionError,
    NoteService,
)

router = APIRouter()


class NoteEndpoints(LoggerMixin):
    """Note API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = NoteEndpoints()


async def _get_note_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NoteService:
    """Build NoteService dependency.

    Args:
        session: Database session from dependency injection.

    Returns:
        NoteService instance.
    """
    return NoteService(session=session)


# =============================================================================
# GET /api/v1/leads/{lead_id}/notes — List notes for a lead
# =============================================================================


@router.get(
    "/leads/{lead_id}/notes",
    response_model=list[NoteResponse],
    summary="List notes for a lead",
    description="Returns the merged notes timeline for a lead, ordered newest first.",
)
async def list_lead_notes(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> list[NoteResponse]:
    """List notes for a lead.

    Validates: Requirement 4.2, 4.7
    """
    _endpoints.log_started("list_lead_notes", lead_id=str(lead_id))
    result = await service.list_notes("lead", lead_id)
    _endpoints.log_completed("list_lead_notes", lead_id=str(lead_id), count=len(result))
    return result


# =============================================================================
# POST /api/v1/leads/{lead_id}/notes — Create note on a lead
# =============================================================================


@router.post(
    "/leads/{lead_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create note on a lead",
    description="Create a new note on a lead.",
)
async def create_lead_note(
    lead_id: UUID,
    data: NoteCreate,
    current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> NoteResponse:
    """Create a note on a lead.

    Validates: Requirement 4.3, 4.7
    """
    _endpoints.log_started("create_lead_note", lead_id=str(lead_id))
    result = await service.create_note(
        subject_type="lead",
        subject_id=lead_id,
        body=data.body,
        author_id=current_user.id,
    )
    _endpoints.log_completed("create_lead_note", note_id=str(result.id))
    return result


# =============================================================================
# GET /api/v1/sales/{sales_id}/notes — List notes for a sales entry
# =============================================================================


@router.get(
    "/sales/{sales_id}/notes",
    response_model=list[NoteResponse],
    summary="List notes for a sales entry",
    description=(
        "Returns the merged notes timeline for a sales entry, ordered newest first."
    ),
)
async def list_sales_notes(
    sales_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> list[NoteResponse]:
    """List notes for a sales entry.

    Validates: Requirement 4.2, 4.4, 4.7
    """
    _endpoints.log_started("list_sales_notes", sales_id=str(sales_id))
    result = await service.list_notes("sales_entry", sales_id)
    _endpoints.log_completed(
        "list_sales_notes", sales_id=str(sales_id), count=len(result)
    )
    return result


# =============================================================================
# POST /api/v1/sales/{sales_id}/notes — Create note on a sales entry
# =============================================================================


@router.post(
    "/sales/{sales_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create note on a sales entry",
    description="Create a new note on a sales entry.",
)
async def create_sales_note(
    sales_id: UUID,
    data: NoteCreate,
    current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> NoteResponse:
    """Create a note on a sales entry.

    Validates: Requirement 4.3, 4.7
    """
    _endpoints.log_started("create_sales_note", sales_id=str(sales_id))
    result = await service.create_note(
        subject_type="sales_entry",
        subject_id=sales_id,
        body=data.body,
        author_id=current_user.id,
    )
    _endpoints.log_completed("create_sales_note", note_id=str(result.id))
    return result


# =============================================================================
# GET /api/v1/customers/{customer_id}/notes — List notes for a customer
# =============================================================================


@router.get(
    "/customers/{customer_id}/notes",
    response_model=list[NoteResponse],
    summary="List notes for a customer",
    description=(
        "Returns the merged notes timeline for a customer, ordered newest first."
    ),
)
async def list_customer_notes(
    customer_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> list[NoteResponse]:
    """List notes for a customer.

    Validates: Requirement 4.2, 4.5, 4.7
    """
    _endpoints.log_started("list_customer_notes", customer_id=str(customer_id))
    result = await service.list_notes("customer", customer_id)
    _endpoints.log_completed(
        "list_customer_notes", customer_id=str(customer_id), count=len(result)
    )
    return result


# =============================================================================
# POST /api/v1/customers/{customer_id}/notes — Create note on a customer
# =============================================================================


@router.post(
    "/customers/{customer_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create note on a customer",
    description="Create a new note on a customer.",
)
async def create_customer_note(
    customer_id: UUID,
    data: NoteCreate,
    current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> NoteResponse:
    """Create a note on a customer.

    Validates: Requirement 4.3, 4.7
    """
    _endpoints.log_started("create_customer_note", customer_id=str(customer_id))
    result = await service.create_note(
        subject_type="customer",
        subject_id=customer_id,
        body=data.body,
        author_id=current_user.id,
    )
    _endpoints.log_completed("create_customer_note", note_id=str(result.id))
    return result


# =============================================================================
# PATCH /api/v1/notes/{note_id} — Edit a note
# =============================================================================


@router.patch(
    "/notes/{note_id}",
    response_model=NoteResponse,
    summary="Edit a note",
    description="Edit a note's body. Only the original author or an admin can edit.",
)
async def update_note(
    note_id: UUID,
    data: NoteUpdate,
    current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> NoteResponse:
    """Edit a note.

    Validates: Requirement 4.7
    """
    _endpoints.log_started("update_note", note_id=str(note_id))
    try:
        result = await service.update_note(
            note_id=note_id,
            body=data.body,
            actor_id=current_user.id,
        )
    except NoteNotFoundError as e:
        _endpoints.log_rejected("update_note", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found",
        ) from e
    except NotePermissionError as e:
        _endpoints.log_rejected("update_note", reason="forbidden")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the original author or an admin can edit this note",
        ) from e

    _endpoints.log_completed("update_note", note_id=str(note_id))
    return result


# =============================================================================
# DELETE /api/v1/notes/{note_id} — Soft-delete a note
# =============================================================================


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
    description="Soft-delete a note. Only the original author or an admin can delete.",
)
async def delete_note(
    note_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[NoteService, Depends(_get_note_service)],
) -> None:
    """Soft-delete a note.

    Validates: Requirement 4.7
    """
    _endpoints.log_started("delete_note", note_id=str(note_id))
    try:
        await service.delete_note(
            note_id=note_id,
            actor_id=current_user.id,
        )
    except NoteNotFoundError as e:
        _endpoints.log_rejected("delete_note", reason="not_found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found",
        ) from e
    except NotePermissionError as e:
        _endpoints.log_rejected("delete_note", reason="forbidden")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the original author or an admin can delete this note",
        ) from e

    _endpoints.log_completed("delete_note", note_id=str(note_id))
