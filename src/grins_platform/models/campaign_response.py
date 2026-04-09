"""CampaignResponse model for storing inbound poll replies.

Validates: Scheduling Poll Req 2.1-2.7, 15.4
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class CampaignResponse(Base):
    """Inbound SMS reply correlated to a campaign."""

    __tablename__ = "campaign_responses"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    sent_message_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    customer_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_option_key: Mapped[str | None] = mapped_column(String(8), nullable=True)
    selected_option_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_reply_body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    campaign: Mapped["Campaign | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Campaign",
        lazy="selectin",
    )
    sent_message: Mapped["SentMessage | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "SentMessage",
        lazy="selectin",
    )
    customer: Mapped["Customer | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Customer",
        lazy="selectin",
    )
    lead: Mapped["Lead | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Lead",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('parsed', 'needs_review', 'opted_out', 'orphan')",
            name="ck_campaign_responses_status",
        ),
        Index("ix_campaign_responses_campaign_id", "campaign_id"),
        Index("ix_campaign_responses_status", "status"),
        Index(
            "ix_campaign_responses_campaign_phone_received",
            "campaign_id",
            "phone",
            received_at.desc(),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignResponse(id={self.id}, campaign_id={self.campaign_id}, "
            f"status='{self.status}')>"
        )
