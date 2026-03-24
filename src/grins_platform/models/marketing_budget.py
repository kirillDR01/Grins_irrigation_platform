"""Marketing budget model for budget tracking.

Validates: CRM Gap Closure Req 64.1
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class MarketingBudget(Base):
    """Marketing budget record per channel and period.

    Validates: CRM Gap Closure Req 64.1
    """

    __tablename__ = "marketing_budgets"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    actual_spend: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        server_default="0",
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

    __table_args__ = (
        Index("idx_marketing_budgets_channel", "channel"),
        Index("idx_marketing_budgets_period", "period_start", "period_end"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketingBudget(id={self.id}, channel='{self.channel}', "
            f"budget={self.budget_amount})>"
        )
