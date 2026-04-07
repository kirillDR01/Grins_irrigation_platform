"""Google Sheet submission model.

Stores raw data from Google Form-linked Google Sheet rows
and tracks processing status for lead creation.

Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.lead import Lead


class GoogleSheetSubmission(Base):
    """Google Sheet submission record.

    Stores all 18 columns from the Google Form response sheet
    as nullable strings, plus processing metadata and lead linkage.
    """

    __tablename__ = "google_sheet_submissions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    sheet_row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    # 18 sheet columns — all nullable strings
    timestamp: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spring_startup: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fall_blowout: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summer_tuneup: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repair_existing: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_system_install: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    addition_to_system: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    additional_services_info: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    date_work_needed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referral_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    landscape_hardscape: Mapped[str | None] = mapped_column(Text, nullable=True)

    # New form fields (columns W, Z, AC — added when form was restructured)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    work_requested: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agreed_to_terms: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Processing metadata
    processing_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="imported",
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lead promotion tracking (Req 52.3, 52.4)
    promoted_to_lead_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Timestamps
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    lead: Mapped["Lead | None"] = relationship(
        "Lead",
        foreign_keys=[lead_id],
        lazy="selectin",
    )
    promoted_to_lead: Mapped["Lead | None"] = relationship(
        "Lead",
        foreign_keys=[promoted_to_lead_id],
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_submissions_client_type", "client_type"),
        Index("idx_submissions_processing_status", "processing_status"),
        Index("idx_submissions_imported_at", "imported_at"),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<GoogleSheetSubmission(id={self.id}, "
            f"row={self.sheet_row_number}, status='{self.processing_status}')>"
        )
