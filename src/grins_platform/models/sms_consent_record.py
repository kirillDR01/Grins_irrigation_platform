"""SmsConsentRecord model for TCPA compliance.

INSERT-ONLY table — records are never updated or deleted.
Opt-outs are recorded as new rows with consent_given=false.

Validates: Requirements 29.1, 29.2, 29.3, 29.4
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.lead import Lead


class SmsConsentRecord(Base):
    """Immutable SMS consent record for TCPA compliance.

    Tracks SMS consent given/revoked by customers.
    INSERT-ONLY — opt-outs create new rows with consent_given=false.
    7-year minimum retention.

    Validates: Requirements 29.1, 29.2, 29.3, 29.4
    """

    __tablename__ = "sms_consent_records"
    __table_args__ = (
        Index("ix_sms_consent_records_phone_number", "phone_number"),
        Index("ix_sms_consent_records_customer_id", "customer_id"),
        Index("ix_sms_consent_records_consent_token", "consent_token"),
        Index("ix_sms_consent_records_lead_id", "lead_id"),
        Index("ix_sms_consent_records_created_by_staff_id", "created_by_staff_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=True,
    )
    lead_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=True,
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    consent_method: Mapped[str] = mapped_column(String(50), nullable=False)
    consent_language_shown: Mapped[str] = mapped_column(Text, nullable=False)
    consent_form_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    consent_ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    consent_user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    consent_token: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    opt_out_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    opt_out_method: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    opt_out_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    opt_out_confirmation_sent: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    created_by_staff_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", name="fk_sms_consent_records_created_by_staff"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship(
        "Lead",
        foreign_keys=[lead_id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<SmsConsentRecord(id={self.id}, "
            f"phone='{self.phone_number}', "
            f"consent_given={self.consent_given})>"
        )
