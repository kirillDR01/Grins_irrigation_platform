"""DisclosureRecord model for MN auto-renewal compliance.

INSERT-ONLY table — records are never updated or deleted.

Validates: Requirements 33.1, 33.2, 33.3, 33.4
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from grins_platform.database import Base


class DisclosureRecord(Base):
    """Immutable compliance disclosure record.

    Tracks disclosures sent to customers for MN Stat. 325G.56-325G.62
    auto-renewal compliance. INSERT-ONLY - never updated or deleted.

    Validates: Requirements 33.1, 33.2, 33.3, 33.4
    """

    __tablename__ = "disclosure_records"
    __table_args__ = (
        Index("ix_disclosure_records_agreement_id", "agreement_id"),
        Index("ix_disclosure_records_customer_id", "customer_id"),
        Index(
            "ix_disclosure_records_type_sent_at",
            "disclosure_type",
            "sent_at",
        ),
        Index("ix_disclosure_records_consent_token", "consent_token"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agreement_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_agreements.id"),
        nullable=True,
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
    )
    disclosure_type: Mapped[str] = mapped_column(String(30), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sent_via: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    recipient_phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consent_token: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    delivery_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<DisclosureRecord(id={self.id}, "
            f"type='{self.disclosure_type}', "
            f"sent_at='{self.sent_at}')>"
        )
