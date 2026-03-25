"""Pydantic schemas for business settings.

Validates: CRM Gap Closure Req 87.2
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessSettingResponse(BaseModel):
    """Schema for business setting response.

    Validates: CRM Gap Closure Req 87.2
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Setting UUID")
    setting_key: str = Field(..., max_length=100, description="Setting key")
    setting_value: dict[str, Any] | None = Field(
        default=None,
        description="Setting value as JSON",
    )
    updated_by: UUID | None = Field(
        default=None,
        description="Staff who last updated",
    )
    updated_at: datetime = Field(..., description="Last update timestamp")


class BusinessSettingUpdate(BaseModel):
    """Schema for updating a business setting.

    Validates: CRM Gap Closure Req 87.2
    """

    setting_value: dict[str, Any] = Field(
        ...,
        description="New setting value as JSON",
    )
