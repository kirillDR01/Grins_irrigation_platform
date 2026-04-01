"""
SchedulingCriteriaConfig model for AI scheduling criteria management.

This module defines the SchedulingCriteriaConfig SQLAlchemy model representing
the 30 scheduling criteria with weights and hard/soft classification.

Validates: Requirements 19.1, 19.2, 23.1
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from grins_platform.database import Base


class SchedulingCriteriaConfig(Base):
    """SchedulingCriteriaConfig model representing a scheduling criterion.

    Stores the 30 criteria weights and hard/soft classification.
    Enables runtime tuning without code changes.

    Attributes:
        id: Unique identifier for the criterion config
        criterion_number: Criterion number (1-30)
        criterion_name: Human-readable name
        criterion_group: Group (geographic, resource, customer_job, etc.)
        weight: Relative importance (0-100)
        is_hard_constraint: True = must satisfy, False = optimize
        is_enabled: Feature flag per criterion
        config_json: Criterion-specific configuration
        created_at: Record creation timestamp
        updated_at: Record update timestamp

    Validates: Requirements 19.1, 19.2, 23.1
    """

    __tablename__ = "scheduling_criteria_config"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Criterion details
    criterion_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        unique=True,
    )
    criterion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    criterion_group: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="50",
    )
    is_hard_constraint: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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

    def __repr__(self) -> str:
        """Return string representation of the criteria config."""
        return (
            f"<SchedulingCriteriaConfig(id={self.id}, "
            f"number={self.criterion_number}, name='{self.criterion_name}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert the criteria config to a dictionary.

        Returns:
            Dictionary representation of the criteria config.
        """
        return {
            "id": str(self.id),
            "criterion_number": self.criterion_number,
            "criterion_name": self.criterion_name,
            "criterion_group": self.criterion_group,
            "weight": self.weight,
            "is_hard_constraint": self.is_hard_constraint,
            "is_enabled": self.is_enabled,
            "config_json": self.config_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
