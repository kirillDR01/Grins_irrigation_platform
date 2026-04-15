"""Contract renewal proposal models.

Validates: CRM Changes Update 2 Req 31.1, 31.5
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import (
    JSON,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base

if TYPE_CHECKING:
    from grins_platform.models.customer import Customer
    from grins_platform.models.job import Job
    from grins_platform.models.service_agreement import ServiceAgreement
    from grins_platform.models.staff import Staff


class ContractRenewalProposal(Base):
    """Batch of proposed jobs for a renewed service agreement.

    Validates: CRM Changes Update 2 Req 31.1, 31.5
    """

    __tablename__ = "contract_renewal_proposals"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    service_agreement_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("service_agreements.id"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="pending",
    )
    proposed_job_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id"),
        nullable=True,
    )

    # Relationships
    service_agreement: Mapped["ServiceAgreement"] = relationship(
        "ServiceAgreement",
        lazy="selectin",
    )
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    reviewer: Mapped[Optional["Staff"]] = relationship("Staff", lazy="selectin")
    proposed_jobs: Mapped[list["ContractRenewalProposedJob"]] = relationship(
        "ContractRenewalProposedJob",
        back_populates="proposal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (Index("idx_renewal_proposals_status", "status"),)

    def __repr__(self) -> str:
        return (
            f"<ContractRenewalProposal(id={self.id}, "
            f"status='{self.status}', jobs={self.proposed_job_count})>"
        )


class ContractRenewalProposedJob(Base):
    """Individual proposed job within a renewal proposal.

    Validates: CRM Changes Update 2 Req 31.5
    """

    __tablename__ = "contract_renewal_proposed_jobs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    proposal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contract_renewal_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="pending",
    )
    proposed_job_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_job_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=True,
    )

    # Relationships
    proposal: Mapped["ContractRenewalProposal"] = relationship(
        "ContractRenewalProposal",
        back_populates="proposed_jobs",
    )
    created_job: Mapped[Optional["Job"]] = relationship("Job", lazy="selectin")

    __table_args__ = (Index("idx_renewal_proposed_jobs_proposal", "proposal_id"),)

    def __repr__(self) -> str:
        return (
            f"<ContractRenewalProposedJob(id={self.id}, "
            f"service='{self.service_type}', status='{self.status}')>"
        )
