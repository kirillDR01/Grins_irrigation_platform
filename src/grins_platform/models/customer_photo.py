"""Customer photo model for photo management.

Validates: CRM Gap Closure Req 9.1
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
    from grins_platform.models.appointment import Appointment
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job
    from grins_platform.models.staff import Staff


class CustomerPhoto(Base):
    """Customer photo record linked to S3 storage.

    Validates: CRM Gap Closure Req 9.1
    """

    __tablename__ = "customer_photos"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
        nullable=True,
    )
    appointment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    uploaded_by_staff: Mapped["Staff | None"] = relationship("Staff", lazy="selectin")
    appointment: Mapped["Appointment | None"] = relationship(
        "Appointment",
        lazy="selectin",
    )
    job: Mapped["Job | None"] = relationship(
        "Job",
        lazy="selectin",
    )

    __table_args__ = (Index("idx_customer_photos_customer_id", "customer_id"),)

    def __repr__(self) -> str:
        return (
            f"<CustomerPhoto(id={self.id}, customer_id={self.customer_id}, "
            f"file_name='{self.file_name}')>"
        )
