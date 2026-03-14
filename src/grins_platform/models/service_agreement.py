"""ServiceAgreement SQLAlchemy model.

Represents a customer's subscription instance linked to a tier, customer,
and property with Stripe integration and compliance tracking fields.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
"""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.agreement_status_log import AgreementStatusLog
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job
    from grins_platform.models.property import Property
    from grins_platform.models.service_agreement_tier import ServiceAgreementTier
    from grins_platform.models.staff import Staff


class ServiceAgreement(Base):
    """A customer's service agreement subscription instance.

    Validates: Requirements 2.1, 2.2, 2.5
    """

    __tablename__ = "service_agreements"
    __table_args__ = (
        Index("ix_service_agreements_customer_id", "customer_id"),
        Index("ix_service_agreements_tier_id", "tier_id"),
        Index("ix_service_agreements_status", "status"),
        Index("ix_service_agreements_payment_status", "payment_status"),
        Index("ix_service_agreements_renewal_date", "renewal_date"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    agreement_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )

    # Foreign keys
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    tier_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_agreement_tiers.id"),
        nullable=False,
    )
    property_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=True,
    )

    # Stripe fields
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="pending",
    )

    # Dates
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Auto-renew
    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pause_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Price (locked at purchase time — Req 2.4)
    annual_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    base_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Surcharge fields (Req 3.13)
    zone_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    has_lake_pump: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    has_rpz_backflow: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )

    # Payment
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="current",
    )
    last_payment_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_payment_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Renewal approval
    renewal_approved_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=True,
    )
    renewal_approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Consent tracking
    consent_recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    consent_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    disclosure_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Notice tracking
    last_annual_notice_sent: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_renewal_notice_sent: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Cancellation refund (Req 2.5)
    cancellation_refund_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    cancellation_refund_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Onboarding reminder tracking (Req 10.6)
    onboarding_reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_reminder_count: Mapped[int] = mapped_column(
        nullable=False,
        server_default="0",
    )

    # Timestamps
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
    customer: Mapped["Customer"] = relationship(
        "Customer",
        lazy="selectin",
    )
    tier: Mapped["ServiceAgreementTier"] = relationship(
        "ServiceAgreementTier",
        lazy="selectin",
    )
    property: Mapped[Optional["Property"]] = relationship(
        "Property",
        lazy="selectin",
    )
    approved_by_staff: Mapped[Optional["Staff"]] = relationship(
        "Staff",
        lazy="selectin",
    )
    status_logs: Mapped[list["AgreementStatusLog"]] = relationship(
        "AgreementStatusLog",
        back_populates="agreement",
        lazy="selectin",
        order_by="AgreementStatusLog.created_at",
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job",
        back_populates="service_agreement",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<ServiceAgreement(id={self.id}, "
            f"agreement_number='{self.agreement_number}', "
            f"status='{self.status}')>"
        )
