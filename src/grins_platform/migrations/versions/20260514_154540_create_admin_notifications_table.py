"""create admin_notifications table

Revision ID: 47e2024a00da
Revises: 20260513_130000
Create Date: 2026-05-14 15:45:40.399032

Cluster H §5 — in-app notifications inbox for admin users. Parallels
existing email/SMS admin alerts so missed estimate decisions,
appointment cancellations, and late reschedules surface in the top-nav
bell even when the originating channel is unreliable.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47e2024a00da"
down_revision: Union[str, None] = "20260513_130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create admin_notifications table + indexes."""
    op.create_table(
        "admin_notifications",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("subject_resource_type", sa.String(length=32), nullable=False),
        sa.Column("subject_resource_id", sa.UUID(), nullable=False),
        sa.Column("summary", sa.String(length=280), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["staff.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_notifications_event_type",
        "admin_notifications",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_notifications_read_created",
        "admin_notifications",
        ["read_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop admin_notifications table + indexes."""
    op.drop_index(
        "ix_admin_notifications_read_created",
        table_name="admin_notifications",
    )
    op.drop_index(
        "ix_admin_notifications_event_type",
        table_name="admin_notifications",
    )
    op.drop_table("admin_notifications")
