"""EmailSuppressionList model for email compliance.

Permanent suppression — entries are never auto-removed.

Validates: Requirements 67.5, 67.7
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class EmailSuppressionList(Base):
    """Permanent email suppression list entry.

    Customers on this list never receive COMMERCIAL emails.
    Entries are never auto-removed (permanent suppression).

    Validates: Requirements 67.5, 67.7
    """

    __tablename__ = "email_suppression_list"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
    )
    suppressed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<EmailSuppressionList(id={self.id}, email='{self.email}')>"
