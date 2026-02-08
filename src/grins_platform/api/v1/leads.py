"""
Lead API endpoints.

This module provides REST API endpoints for lead management including
public form submission (no auth), admin CRUD, status workflow, and
conversion to customer.

Validates: Requirement 1.10, 5.10, 7.9, 12.3
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI DI
)

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadConversionResponse,
    LeadListParams,
    LeadResponse,
    LeadSubmission,
    LeadSubmissionResponse,
    LeadUpdate,
    PaginatedLeadResponse,
)
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.job_service import JobService
from grins_platform.services.lead_service import LeadService

router = APIRouter()


class LeadEndpoints(LoggerMixin):
    """Lead API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = LeadEndpoints()


async def _get_lead_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LeadService:
    """Build LeadService with all dependencies.

    Args:
        session: Database session from dependency injection

    Returns:
        LeadService instance
    """
    lead_repository = LeadRepository(session=session)
    customer_repository = CustomerRepository(session=session)
    property_repository = PropertyRepository(session=session)
    service_repository = ServiceOfferingRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)

    customer_service = CustomerService(repository=customer_repository)
    job_service = JobService(
        job_repository=job_repository,
        customer_repository=customer_repository,
        property_repository=property_repository,
        service_repository=service_repository,
    )

    return LeadService(
        lead_repository=lead_repository,
        customer_service=customer_service,
        job_service=job_service,
        staff_repository=staff_repository,
    )


# =============================================================================
# POST /api/v1/leads — Public (no auth)
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "",
    response_model=LeadSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a lead from public form",
    description=(
        "Public endpoint for website form submissions. "
        "No authentication required."
    ),
)
async def submit_lead(
    data: LeadSubmission,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadSubmissionResponse:
    """Submit a lead from the public website form.

    Validates: Requirement 1, 2, 3
    """
    _endpoints.log_started("submit_lead", source_site=data.source_site)

    result = await service.submit_lead(data)

    _endpoints.log_completed(
        "submit_lead",
        lead_id=str(result.lead_id) if result.lead_id else "honeypot",
    )
    return result


# =============================================================================
# GET /api/v1/leads — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "",
    response_model=PaginatedLeadResponse,
    summary="List leads",
    description=(
        "List leads with filtering, sorting, and pagination. "
        "Admin auth required."
    ),
)
async def list_leads(
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    situation: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
) -> PaginatedLeadResponse:
    """List leads with filtering and pagination.

    Validates: Requirement 5.1-5.5
    """
    _endpoints.log_started("list_leads", page=page, page_size=page_size)

    params = LeadListParams(
        page=page,
        page_size=page_size,
        status=LeadStatus(status_filter) if status_filter else None,
        situation=LeadSituation(situation) if situation else None,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    result = await service.list_leads(params)

    _endpoints.log_completed("list_leads", total=result.total)
    return result


# =============================================================================
# GET /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.get(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead by ID",
    description="Retrieve a lead by its unique identifier. Admin auth required.",
)
async def get_lead(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Get lead by ID.

    Validates: Requirement 5.8
    """
    _endpoints.log_started("get_lead", lead_id=str(lead_id))

    result = await service.get_lead(lead_id)

    _endpoints.log_completed("get_lead", lead_id=str(lead_id))
    return result


# =============================================================================
# PATCH /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.patch(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
    description="Update lead status, assignment, or notes. Admin auth required.",
)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadResponse:
    """Update a lead.

    Validates: Requirement 5.6-5.7, 6
    """
    _endpoints.log_started("update_lead", lead_id=str(lead_id))

    result = await service.update_lead(lead_id, data)

    _endpoints.log_completed("update_lead", lead_id=str(lead_id))
    return result


# =============================================================================
# POST /api/v1/leads/{lead_id}/convert — Admin auth required
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/{lead_id}/convert",
    response_model=LeadConversionResponse,
    summary="Convert lead to customer",
    description=(
        "Convert a lead to a customer and optionally "
        "create a job. Admin auth required."
    ),
)
async def convert_lead(
    lead_id: UUID,
    data: LeadConversionRequest,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> LeadConversionResponse:
    """Convert a lead to a customer.

    Validates: Requirement 7
    """
    _endpoints.log_started("convert_lead", lead_id=str(lead_id))

    result = await service.convert_lead(lead_id, data)

    _endpoints.log_completed(
        "convert_lead",
        lead_id=str(lead_id),
        customer_id=str(result.customer_id),
    )
    return result


# =============================================================================
# DELETE /api/v1/leads/{lead_id} — Admin auth required
# =============================================================================


@router.delete(  # type: ignore[untyped-decorator]
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
    description="Delete a lead record. Admin auth required.",
)
async def delete_lead(
    lead_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[LeadService, Depends(_get_lead_service)],
) -> None:
    """Delete a lead.

    Validates: Requirement 5.9
    """
    _endpoints.log_started("delete_lead", lead_id=str(lead_id))

    await service.delete_lead(lead_id)

    _endpoints.log_completed("delete_lead", lead_id=str(lead_id))
