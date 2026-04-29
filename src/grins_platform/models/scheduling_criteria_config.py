"""
Scheduling criteria configuration model.

Stores the 30 criteria weights and hard/soft classification for the
AI scheduling engine. Enables runtime tuning without code changes.

Validates: Requirements 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5,
           7.1-7.5, 8.1-8.5, 19.1, 19.2
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
    """Configuration for a single scheduling criterion.

    Each row represents one of the 30 decision criteria used by the
    AI scheduling engine. Weights, hard/soft classification, and
    per-criterion configuration can be tuned at runtime.

    Attributes:
        id: Unique identifier (UUID).
        criterion_number: Criterion number (1-30), unique.
        criterion_name: Human-readable name.
        criterion_group: Grouping category (geographic, resource, etc.).
        weight: Relative importance (0-100).
        is_hard_constraint: True = must satisfy, False = optimize.
        is_enabled: Feature flag per criterion.
        config_json: Criterion-specific configuration (thresholds, etc.).
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "scheduling_criteria_config"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    # Criterion identification
    criterion_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )
    criterion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    criterion_group: Mapped[str] = mapped_column(String(50), nullable=False)

    # Scoring configuration
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
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

    # Criterion-specific configuration
    config_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"<SchedulingCriteriaConfig("
            f"id={self.id}, "
            f"criterion_number={self.criterion_number}, "
            f"criterion_name='{self.criterion_name}')>"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
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
