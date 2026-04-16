"""Alert model for admin-facing dashboard notifications.

An :class:`Alert` row captures a noteworthy event — for example a customer
cancelling an appointment by SMS (``C`` reply) — so the admin dashboard can
surface it for triage. Rows are created by service-layer handlers and
consumed by the ``GET /api/v1/alerts`` endpoint.

Validates: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import (
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base
from grins_platform.models.enums import AlertSeverity, AlertType


class Alert(Base):
    """Admin-facing alert row.

    Attributes:
        id: Unique identifier (UUID).
        type: Alert type (see :class:`AlertType`). Indexed for "alerts of
            type X" queries.
        severity: Alert severity (see :class:`AlertSeverity`). Indexed for
            dashboard filters.
        entity_type: The logical entity the alert references (e.g.
            ``"appointment"``).
        entity_id: The primary-key UUID of the referenced entity.
        message: Short human-readable summary shown on the dashboard.
        created_at: When the alert was raised (tz-aware UTC).
        acknowledged_at: When an admin acknowledged / dismissed the alert,
            or ``None`` if still unacknowledged.

    Validates: bughunt 2026-04-16 finding H-5
    """

    __tablename__ = "alerts"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Classification
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Entity reference
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Human-readable summary
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # Composite index for "unacknowledged alerts of type X" queries
        Index("idx_alerts_type_acknowledged_at", "type", "acknowledged_at"),
    )

    @property
    def severity_enum(self) -> AlertSeverity:
        """Return :attr:`severity` as an :class:`AlertSeverity` member."""
        return AlertSeverity(self.severity)

    @property
    def type_enum(self) -> AlertType:
        """Return :attr:`type` as an :class:`AlertType` member."""
        return AlertType(self.type)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation of the alert."""
        return {
            "id": str(self.id),
            "type": self.type,
            "severity": self.severity,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
        }

    def __repr__(self) -> str:
        """Return string representation of the alert."""
        return (
            f"<Alert(id={self.id}, type='{self.type}', "
            f"severity='{self.severity}', entity={self.entity_type}:"
            f"{self.entity_id})>"
        )
