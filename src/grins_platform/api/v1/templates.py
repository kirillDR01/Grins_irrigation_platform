"""
Template API endpoints for estimate and contract templates.

This module provides REST API endpoints for CRUD operations on
estimate templates and contract templates.

Validates: CRM Gap Closure Req 17.3, 17.4
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001 - Required at runtime for FastAPI DI
)
from grins_platform.api.v1.dependencies import get_estimate_service
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.estimate import (
    ContractTemplateCreate,
    ContractTemplateResponse,
    ContractTemplateUpdate,
    EstimateTemplateCreate,
    EstimateTemplateResponse,
    EstimateTemplateUpdate,
)
from grins_platform.services.estimate_service import (
    EstimateService,  # noqa: TC001 - Required at runtime for FastAPI DI
)

router = APIRouter()


class TemplateEndpoints(LoggerMixin):
    """Template API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = TemplateEndpoints()


# =============================================================================
# Estimate Template CRUD — Req 17.3
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/estimates",
    response_model=EstimateTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an estimate template",
    description="Create a reusable estimate template with default line items.",
)
async def create_estimate_template(
    data: EstimateTemplateCreate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateTemplateResponse:
    """Create an estimate template.

    Args:
        data: Template creation data.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Created template response.

    Validates: CRM Gap Closure Req 17.3
    """
    _endpoints.log_started(
        "create_estimate_template",
        user_id=str(current_user.id),
        name=data.name,
    )

    template = await service.repo.create_template(
        name=data.name,
        description=data.description,
        line_items=data.line_items,
        terms=data.terms,
    )

    _endpoints.log_completed(
        "create_estimate_template",
        template_id=str(template.id),
    )
    return EstimateTemplateResponse.model_validate(template)


@router.get(  # type: ignore[untyped-decorator]
    "/estimates",
    response_model=list[EstimateTemplateResponse],
    summary="List estimate templates",
    description="List all estimate templates, optionally filtered by active status.",
)
async def list_estimate_templates(
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
    active_only: bool = Query(default=True, description="Return only active templates"),
) -> list[EstimateTemplateResponse]:
    """List estimate templates.

    Args:
        current_user: Authenticated active user.
        service: EstimateService instance.
        active_only: Whether to return only active templates.

    Returns:
        List of estimate template responses.

    Validates: CRM Gap Closure Req 17.3
    """
    _endpoints.log_started("list_estimate_templates", active_only=active_only)

    templates = await service.repo.list_templates(active_only=active_only)

    _endpoints.log_completed("list_estimate_templates", count=len(templates))
    return [EstimateTemplateResponse.model_validate(t) for t in templates]


@router.get(  # type: ignore[untyped-decorator]
    "/estimates/{template_id}",
    response_model=EstimateTemplateResponse,
    summary="Get estimate template by ID",
    description="Retrieve a single estimate template by its UUID.",
)
async def get_estimate_template(
    template_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateTemplateResponse:
    """Get an estimate template by ID.

    Args:
        template_id: Template UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Estimate template response.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.3
    """
    _endpoints.log_started("get_estimate_template", template_id=str(template_id))

    template = await service.repo.get_template_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate template not found: {template_id}",
        )

    _endpoints.log_completed("get_estimate_template", template_id=str(template_id))
    return EstimateTemplateResponse.model_validate(template)


@router.patch(  # type: ignore[untyped-decorator]
    "/estimates/{template_id}",
    response_model=EstimateTemplateResponse,
    summary="Update an estimate template",
    description="Update fields on an existing estimate template.",
)
async def update_estimate_template(
    template_id: UUID,
    data: EstimateTemplateUpdate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> EstimateTemplateResponse:
    """Update an estimate template.

    Args:
        template_id: Template UUID.
        data: Fields to update.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Updated template response.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.3
    """
    _endpoints.log_started(
        "update_estimate_template",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        template = await service.repo.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estimate template not found: {template_id}",
            )
        return EstimateTemplateResponse.model_validate(template)

    updated = await service.repo.update_template(template_id, **update_fields)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate template not found: {template_id}",
        )

    _endpoints.log_completed(
        "update_estimate_template",
        template_id=str(template_id),
    )
    return EstimateTemplateResponse.model_validate(updated)


@router.delete(  # type: ignore[untyped-decorator]
    "/estimates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an estimate template",
    description="Soft-delete an estimate template by setting is_active to false.",
)
async def delete_estimate_template(
    template_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> None:
    """Delete (deactivate) an estimate template.

    Args:
        template_id: Template UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.3
    """
    _endpoints.log_started(
        "delete_estimate_template",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    deleted = await service.repo.delete_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate template not found: {template_id}",
        )

    _endpoints.log_completed(
        "delete_estimate_template",
        template_id=str(template_id),
    )


# =============================================================================
# Contract Template CRUD — Req 17.4
# =============================================================================


@router.post(  # type: ignore[untyped-decorator]
    "/contracts",
    response_model=ContractTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a contract template",
    description="Create a reusable contract template with body and terms.",
)
async def create_contract_template(
    data: ContractTemplateCreate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> ContractTemplateResponse:
    """Create a contract template.

    Args:
        data: Template creation data.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Created contract template response.

    Validates: CRM Gap Closure Req 17.4
    """
    _endpoints.log_started(
        "create_contract_template",
        user_id=str(current_user.id),
        name=data.name,
    )

    template = await service.repo.create_contract_template(
        name=data.name,
        body=data.body,
        terms_and_conditions=data.terms_and_conditions,
    )

    _endpoints.log_completed(
        "create_contract_template",
        template_id=str(template.id),
    )
    return ContractTemplateResponse.model_validate(template)


@router.get(  # type: ignore[untyped-decorator]
    "/contracts",
    response_model=list[ContractTemplateResponse],
    summary="List contract templates",
    description="List all contract templates, optionally filtered by active status.",
)
async def list_contract_templates(
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
    active_only: bool = Query(default=True, description="Return only active templates"),
) -> list[ContractTemplateResponse]:
    """List contract templates.

    Args:
        current_user: Authenticated active user.
        service: EstimateService instance.
        active_only: Whether to return only active templates.

    Returns:
        List of contract template responses.

    Validates: CRM Gap Closure Req 17.4
    """
    _endpoints.log_started("list_contract_templates", active_only=active_only)

    templates = await service.repo.list_contract_templates(active_only=active_only)

    _endpoints.log_completed("list_contract_templates", count=len(templates))
    return [ContractTemplateResponse.model_validate(t) for t in templates]


@router.get(  # type: ignore[untyped-decorator]
    "/contracts/{template_id}",
    response_model=ContractTemplateResponse,
    summary="Get contract template by ID",
    description="Retrieve a single contract template by its UUID.",
)
async def get_contract_template(
    template_id: UUID,
    _current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> ContractTemplateResponse:
    """Get a contract template by ID.

    Args:
        template_id: Template UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Contract template response.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.4
    """
    _endpoints.log_started("get_contract_template", template_id=str(template_id))

    template = await service.repo.get_contract_template_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template not found: {template_id}",
        )

    _endpoints.log_completed("get_contract_template", template_id=str(template_id))
    return ContractTemplateResponse.model_validate(template)


@router.patch(  # type: ignore[untyped-decorator]
    "/contracts/{template_id}",
    response_model=ContractTemplateResponse,
    summary="Update a contract template",
    description="Update fields on an existing contract template.",
)
async def update_contract_template(
    template_id: UUID,
    data: ContractTemplateUpdate,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> ContractTemplateResponse:
    """Update a contract template.

    Args:
        template_id: Template UUID.
        data: Fields to update.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Returns:
        Updated contract template response.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.4
    """
    _endpoints.log_started(
        "update_contract_template",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    update_fields = data.model_dump(exclude_unset=True)
    if not update_fields:
        template = await service.repo.get_contract_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contract template not found: {template_id}",
            )
        return ContractTemplateResponse.model_validate(template)

    updated = await service.repo.update_contract_template(
        template_id,
        **update_fields,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template not found: {template_id}",
        )

    _endpoints.log_completed(
        "update_contract_template",
        template_id=str(template_id),
    )
    return ContractTemplateResponse.model_validate(updated)


@router.delete(  # type: ignore[untyped-decorator]
    "/contracts/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contract template",
    description="Soft-delete a contract template by setting is_active to false.",
)
async def delete_contract_template(
    template_id: UUID,
    current_user: CurrentActiveUser,
    service: Annotated[EstimateService, Depends(get_estimate_service)],
) -> None:
    """Delete (deactivate) a contract template.

    Args:
        template_id: Template UUID.
        current_user: Authenticated active user.
        service: EstimateService instance.

    Raises:
        HTTPException: 404 if not found.

    Validates: CRM Gap Closure Req 17.4
    """
    _endpoints.log_started(
        "delete_contract_template",
        template_id=str(template_id),
        user_id=str(current_user.id),
    )

    deleted = await service.repo.delete_contract_template(template_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract template not found: {template_id}",
        )

    _endpoints.log_completed(
        "delete_contract_template",
        template_id=str(template_id),
    )
