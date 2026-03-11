"""ConsentLanguageVersion model for tracking TCPA disclosure text versions.

Append-only table — versions are never updated or deleted.

Validates: Requirements 11.1, 11.2, 11.3
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class ConsentLanguageVersion(Base):
    """Tracks versions of TCPA consent disclosure text.

    Append-only — new versions are added, old ones deprecated.

    Validates: Requirements 11.1, 11.2, 11.3
    """

    __tablename__ = "consent_language_versions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )
    consent_text: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    deprecated_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<ConsentLanguageVersion(id={self.id}, version='{self.version}')>"
