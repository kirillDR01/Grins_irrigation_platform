"""Create sent_messages table.

Revision ID: 011_sent_messages
Revises: 010_ai_usage
Create Date: 2025-06-20 10:02:00

This migration creates the sent_messages table for tracking all SMS communications
sent to customers. Supports delivery status tracking and Twilio integration.

Validates: AI Assistant Requirements 7.8, 12.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250620_100200"
down_revision: Union[str, None] = "20250620_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sent_messages table with foreign keys and indexes."""
    op.create_table(
        "sent_messages",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("appointment_id", sa.UUID(), nullable=True),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("message_content", sa.Text(), nullable=False),
        sa.Column("recipient_phone", sa.String(20), nullable=False),
        sa.Column(
            "delivery_status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("twilio_sid", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_sent_messages_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            name="fk_sent_messages_job_id",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_sent_messages_appointment_id",
        ),
        sa.CheckConstraint(
            "message_type IN ('appointment_confirmation', 'appointment_reminder', "
            "'on_the_way', 'arrival', 'completion', 'invoice', 'payment_reminder', "
            "'custom')",
            name="ck_sent_messages_message_type",
        ),
        sa.CheckConstraint(
            "delivery_status IN ('pending', 'scheduled', 'sent', 'delivered', "
            "'failed', 'cancelled')",
            name="ck_sent_messages_delivery_status",
        ),
    )

    op.create_index("idx_sent_messages_customer_id", "sent_messages", ["customer_id"])
    op.create_index("idx_sent_messages_job_id", "sent_messages", ["job_id"])
    op.create_index("idx_sent_messages_message_type", "sent_messages", ["message_type"])
    op.create_index(
        "idx_sent_messages_delivery_status",
        "sent_messages",
        ["delivery_status"],
    )
    op.create_index(
        "idx_sent_messages_scheduled_for",
        "sent_messages",
        ["scheduled_for"],
    )


def downgrade() -> None:
    """Drop sent_messages table and indexes."""
    op.drop_index("idx_sent_messages_scheduled_for", table_name="sent_messages")
    op.drop_index("idx_sent_messages_delivery_status", table_name="sent_messages")
    op.drop_index("idx_sent_messages_message_type", table_name="sent_messages")
    op.drop_index("idx_sent_messages_job_id", table_name="sent_messages")
    op.drop_index("idx_sent_messages_customer_id", table_name="sent_messages")
    op.drop_table("sent_messages")
