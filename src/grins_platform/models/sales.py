"""Sales pipeline models.

Validates: CRM Changes Update 2 Req 13.3, 14.1, 14.2, 15.1
"""

from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.lead import Lead
    from grins_platform.models.property import Property


class SalesEntry(Base):
    """Sales pipeline entry for estimate-to-job workflow.

    Validates: CRM Changes Update 2 Req 14.1, 14.2
    """

    __tablename__ = "sales_entries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    property_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("properties.id"),
        nullable=True,
    )
    lead_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id"),
        nullable=True,
    )
    job_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="schedule_estimate",
    )
    last_contact_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    closed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signwell_document_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    nudges_paused_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    property: Mapped[Optional["Property"]] = relationship("Property", lazy="selectin")
    lead: Mapped[Optional["Lead"]] = relationship("Lead", lazy="selectin")
    calendar_events: Mapped[list["SalesCalendarEvent"]] = relationship(
        "SalesCalendarEvent",
        back_populates="sales_entry",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_sales_entries_status", "status"),
        Index("idx_sales_entries_customer", "customer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<SalesEntry(id={self.id}, status='{self.status}', "
            f"customer_id={self.customer_id})>"
        )


class SalesCalendarEvent(Base):
    """Estimate appointment on the Sales calendar.

    Validates: CRM Changes Update 2 Req 15.1
    """

    __tablename__ = "sales_calendar_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    sales_entry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sales_entries.id"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    end_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to_user_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Y/R/C confirmation lifecycle (migration 20260509_120000). One of:
    # 'pending' (default on insert), 'confirmed' (customer replied Y),
    # 'reschedule_requested' (customer replied R), 'cancelled' (customer
    # replied C). Mirrors AppointmentStatus's confirmation slice but kept
    # on the calendar event itself because SalesCalendarEvent has no
    # AppointmentStatus column.
    confirmation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="pending",
        default="pending",
    )
    confirmation_status_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    sales_entry: Mapped["SalesEntry"] = relationship(
        "SalesEntry",
        back_populates="calendar_events",
    )
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")

    __table_args__ = (
        Index("idx_sales_calendar_date", "scheduled_date"),
        Index("ix_sales_calendar_assigned_to", "assigned_to_user_id"),
        CheckConstraint(
            "confirmation_status IN ("
            "'pending','confirmed','reschedule_requested','cancelled')",
            name="ck_sales_calendar_events_confirmation_status",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<SalesCalendarEvent(id={self.id}, "
            f"date={self.scheduled_date}, title='{self.title}')>"
        )
