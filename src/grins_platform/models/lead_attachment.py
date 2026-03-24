"""Lead attachment model for file management.

Validates: CRM Gap Closure Req 15.1
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class LeadAttachment(Base):
    """Lead attachment record linked to S3 storage.

    Validates: CRM Gap Closure Req 15.1
    """

    __tablename__ = "lead_attachments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    lead_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    attachment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (Index("idx_lead_attachments_lead_id", "lead_id"),)

    def __repr__(self) -> str:
        return (
            f"<LeadAttachment(id={self.id}, lead_id={self.lead_id}, "
            f"file_name='{self.file_name}', type='{self.attachment_type}')>"
        )
