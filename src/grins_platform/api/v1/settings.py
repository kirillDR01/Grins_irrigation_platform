"""Business settings API endpoints.

Provides list and update for business settings.

Validates: CRM Gap Closure Req 87.2
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.settings import (
    BusinessSettingResponse,
    BusinessSettingUpdate,
)
from grins_platform.services.settings_service import (
    SettingNotFoundError,
    SettingsService,
)

router = APIRouter()


class _SettingsEndpoints(LoggerMixin):
    """Settings API endpoint handlers with logging."""

    DOMAIN = "api"


_endpoints = _SettingsEndpoints()

# Singleton service instance (uses in-memory cache)
_settings_service = SettingsService()


@router.get(
    "",
    response_model=list[BusinessSettingResponse],
    summary="List all business settings",
    description="Returns all business settings.",
)
async def list_settings(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BusinessSettingResponse]:
    """List all business settings.

    Validates: CRM Gap Closure Req 87.2
    """
    _endpoints.log_started("list_settings")
    result = await _settings_service.get_all_settings(session)
    _endpoints.log_completed("list_settings", count=len(result))
    return result


@router.patch(
    "/{key}",
    response_model=BusinessSettingResponse,
    summary="Update a business setting",
    description="Update a specific business setting by key.",
)
async def update_setting(
    key: str,
    data: BusinessSettingUpdate,
    current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessSettingResponse:
    """Update a business setting.

    Validates: CRM Gap Closure Req 87.2
    """
    _endpoints.log_started("update_setting", key=key)
    try:
        result = await _settings_service.update_setting(
            session,
            key=key,
            value=data.setting_value,
            updated_by=current_user.id,
        )
    except SettingNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    else:
        _endpoints.log_completed("update_setting", key=key)
        return result
