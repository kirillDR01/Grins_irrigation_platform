"""Business settings API endpoints.

Provides list and update for business settings.

H-12 (bughunt 2026-04-16) adds ``GET /business`` and ``PATCH /business``
for the firm-wide threshold knobs (lien_days_past_due, lien_min_amount,
upcoming_due_days, confirmation_no_reply_days) that the admin can
configure from the Settings page.

Validates: CRM Gap Closure Req 87.2; bughunt 2026-04-16 finding H-12.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from grins_platform.api.v1.auth_dependencies import (
    CurrentActiveUser,  # noqa: TC001
    ManagerOrAdminUser,  # noqa: TC001
)
from grins_platform.api.v1.dependencies import get_db_session
from grins_platform.log_config import LoggerMixin
from grins_platform.schemas.settings import (
    BusinessSettingResponse,
    BusinessSettingUpdate,
)
from grins_platform.services.business_setting_service import (
    BUSINESS_SETTING_KEYS,
    BusinessSettingService,
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


# =============================================================================
# H-12: firm-wide threshold knobs
# =============================================================================


class BusinessThresholdsResponse(BaseModel):
    """Flat view of the four H-12 knobs for the admin Settings panel.

    Null values mean the row is missing in ``business_settings`` — the
    consumer can render the migration default as placeholder. The admin
    panel always re-PATCHes a concrete number, so ``None`` is purely a
    boot-strap signal.

    Validates: bughunt 2026-04-16 finding H-12.
    """

    model_config = ConfigDict(from_attributes=True)

    lien_days_past_due: int | None = Field(
        default=None,
        description="Min days past due before an invoice is lien-eligible.",
    )
    lien_min_amount: Decimal | None = Field(
        default=None,
        description="Min $ past due to flag a lien candidate.",
    )
    upcoming_due_days: int | None = Field(
        default=None,
        description="Days-window used by mass-notify 'due-soon'.",
    )
    confirmation_no_reply_days: int | None = Field(
        default=None,
        description="Days until the no-reply review queue picks up an invite (H-7).",
    )


class BusinessThresholdsUpdate(BaseModel):
    """PATCH body — every field is optional so admins can edit one at a time.

    Validates: bughunt 2026-04-16 finding H-12.
    """

    lien_days_past_due: int | None = Field(default=None, ge=1, le=3650)
    lien_min_amount: Decimal | None = Field(default=None, ge=Decimal(0))
    upcoming_due_days: int | None = Field(default=None, ge=1, le=365)
    confirmation_no_reply_days: int | None = Field(default=None, ge=1, le=365)


@router.get(
    "/business",
    response_model=BusinessThresholdsResponse,
    summary="Get firm-wide business thresholds",
    description="Return the four H-12 firm-wide threshold knobs.",
)
async def get_business_thresholds(
    _current_user: CurrentActiveUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessThresholdsResponse:
    """Return the four H-12 firm-wide threshold knobs as a flat object.

    Any authenticated active user can read; only manager/admin can PATCH.

    Validates: bughunt 2026-04-16 finding H-12.
    """
    _endpoints.log_started("get_business_thresholds")
    service = BusinessSettingService(session)
    values = await service.get_all()
    # Coerce Decimal for the min_amount key; Pydantic handles other ints.
    min_amount = values.get("lien_min_amount")
    if min_amount is not None and not isinstance(min_amount, Decimal):
        try:
            min_amount = Decimal(str(min_amount))
        except Exception:
            min_amount = None
    payload = BusinessThresholdsResponse(
        lien_days_past_due=_as_int(values.get("lien_days_past_due")),
        lien_min_amount=min_amount,
        upcoming_due_days=_as_int(values.get("upcoming_due_days")),
        confirmation_no_reply_days=_as_int(
            values.get("confirmation_no_reply_days"),
        ),
    )
    _endpoints.log_completed("get_business_thresholds")
    return payload


@router.patch(
    "/business",
    response_model=BusinessThresholdsResponse,
    summary="Update firm-wide business thresholds",
    description=(
        "Partial update — only the supplied fields are written. Each "
        "write emits an AuditLog row. Manager/admin only."
    ),
)
async def update_business_thresholds(
    data: BusinessThresholdsUpdate,
    current_user: ManagerOrAdminUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BusinessThresholdsResponse:
    """Partial update of the H-12 firm-wide threshold knobs.

    Validates: bughunt 2026-04-16 finding H-12.
    """
    _endpoints.log_started("update_business_thresholds")
    service = BusinessSettingService(session)

    # Only write fields the caller supplied (exclude_unset drops defaults).
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key not in BUSINESS_SETTING_KEYS:
            # Guard against future schema drift.
            continue
        stored: Any = value
        if isinstance(stored, Decimal):
            # JSON can't carry Decimal — serialize as a float-valued string
            # so round-trip through get_decimal stays exact.
            stored = str(stored)
        await service.set_value(
            key=key,
            value=stored,
            updated_by=current_user.id,
        )

    # Return the fresh view so the client can render the saved state.
    values = await service.get_all()
    min_amount = values.get("lien_min_amount")
    if min_amount is not None and not isinstance(min_amount, Decimal):
        try:
            min_amount = Decimal(str(min_amount))
        except Exception:
            min_amount = None
    _endpoints.log_completed("update_business_thresholds")
    return BusinessThresholdsResponse(
        lien_days_past_due=_as_int(values.get("lien_days_past_due")),
        lien_min_amount=min_amount,
        upcoming_due_days=_as_int(values.get("upcoming_due_days")),
        confirmation_no_reply_days=_as_int(
            values.get("confirmation_no_reply_days"),
        ),
    )


def _as_int(raw: Any) -> int | None:  # noqa: ANN401 — JSONB scalar
    """Coerce ``raw`` to int or return None on mismatch."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# =============================================================================
# Legacy dict-valued settings (SettingsService)
# =============================================================================


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
