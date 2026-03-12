"""AgreementStatusLog model for tracking agreement status transitions.

Records every status change on a ServiceAgreement for audit trail purposes.

Validates: Requirements 3.1
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import (
    JSON,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.service_agreement import ServiceAgreement
    from grins_platform.models.staff import Staff


class AgreementStatusLog(Base):
    """Tracks status transitions on service agreements.

    Attributes:
        id: Unique identifier
        agreement_id: FK to service_agreements
        old_status: Status before transition
        new_status: Status after transition
        changed_by: FK to staff who made the change (nullable for system changes)
        reason: Reason for the transition
        metadata: Additional JSONB context
        created_at: When the transition occurred

    Validates: Requirements 3.1
    """

    __tablename__ = "agreement_status_logs"
    __table_args__ = (Index("ix_agreement_status_logs_agreement_id", "agreement_id"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agreement_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_agreements.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    agreement: Mapped["ServiceAgreement"] = relationship(
        "ServiceAgreement",
        back_populates="status_logs",
        lazy="selectin",
    )
    changed_by_staff: Mapped[Optional["Staff"]] = relationship(
        "Staff",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<AgreementStatusLog(id={self.id}, "
            f"'{self.old_status}' -> '{self.new_status}')>"
        )
