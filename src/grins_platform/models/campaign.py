"""Campaign and CampaignRecipient models for marketing campaigns.

Validates: CRM Gap Closure Req 45.1, 45.2
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID as PGUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class Campaign(Base):
    """Marketing campaign record.

    Validates: CRM Gap Closure Req 45.1
    """

    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="draft",
    )
    target_audience: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    subject: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    automation_rule: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("staff.id", ondelete="SET NULL"),
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
    recipients: Mapped[list["CampaignRecipient"]] = relationship(
        "CampaignRecipient",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_campaigns_status", "status"),
        Index("idx_campaigns_scheduled_at", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class CampaignRecipient(Base):
    """Individual recipient record for a campaign.

    Validates: CRM Gap Closure Req 45.2
    """

    __tablename__ = "campaign_recipients"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
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
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="pending",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sending_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="recipients",
    )

    __table_args__ = (
        Index("idx_campaign_recipients_campaign_id", "campaign_id"),
        Index("idx_campaign_recipients_delivery_status", "delivery_status"),
        Index("ix_campaign_recipients_sending_started_at", "sending_started_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<CampaignRecipient(id={self.id}, campaign_id={self.campaign_id}, "
            f"status='{self.delivery_status}')>"
        )
