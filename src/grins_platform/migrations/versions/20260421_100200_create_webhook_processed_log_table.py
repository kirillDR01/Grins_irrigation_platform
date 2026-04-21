"""Create ``webhook_processed_logs`` table for fallback dedup.

Introduces a durable dedup log backing the CallRail inbound webhook
endpoint so that duplicate deliveries are correctly rejected even when
Redis (the primary dedup store) is unavailable. See Gap 07 — Webhook
Security & Dedup (7.B) for the full design.

Revision ID: 20260421_100200
Revises: 20260422_100000
Requirements: Gap 07 — Webhook Security & Dedup (7.B)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_100200"
down_revision: str | None = "20260422_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the webhook_processed_logs table + indexes."""
    op.create_table(
        "webhook_processed_logs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_message_id",
            name="uq_webhook_processed_logs_provider_msgid",
        ),
    )
    op.create_index(
        "ix_webhook_processed_logs_created_at",
        "webhook_processed_logs",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop the webhook_processed_logs table + indexes."""
    op.drop_index(
        "ix_webhook_processed_logs_created_at",
        table_name="webhook_processed_logs",
    )
    op.drop_table("webhook_processed_logs")
