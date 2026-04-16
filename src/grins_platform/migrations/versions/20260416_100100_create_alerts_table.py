"""Create ``alerts`` table for admin-facing dashboard notifications.

The bughunt 2026-04-16 H-5 finding added an :class:`Alert` model used by
``NotificationService.send_admin_cancellation_alert`` to record customer
SMS cancellations for admin review. This migration creates the backing
``alerts`` table with indexes matching the model definition.

Revision ID: 20260416_100100
Revises: 20260416_100000
Requirements: bughunt 2026-04-16 finding H-5
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_100100"
down_revision: str | None = "20260416_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the alerts table + indexes."""
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "acknowledged_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.create_index("ix_alerts_type", "alerts", ["type"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_entity_id", "alerts", ["entity_id"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    # Composite index for "unacknowledged alerts of type X" queries (H-5).
    op.create_index(
        "idx_alerts_type_acknowledged_at",
        "alerts",
        ["type", "acknowledged_at"],
    )


def downgrade() -> None:
    """Drop the alerts table + indexes."""
    op.drop_index("idx_alerts_type_acknowledged_at", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_entity_id", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_type", table_name="alerts")
    op.drop_table("alerts")
