"""Business settings model for configurable platform settings.

Validates: CRM Gap Closure Req 87.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class BusinessSetting(Base):
    """Key-value business setting with JSONB value.

    Validates: CRM Gap Closure Req 87.1
    """

    __tablename__ = "business_settings"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    setting_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    setting_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    updated_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    updated_by_staff: Mapped["Staff | None"] = relationship("Staff", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<BusinessSetting(key='{self.setting_key}')>"
