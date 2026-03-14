"""Add has_rpz_backflow column to service_agreements.

Revision ID: 20260313_100000
Revises: 20260312_100000
Create Date: 2026-03-13
"""

import sqlalchemy as sa
from alembic import op

revision = "20260313_100000"
down_revision = "20260312_100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_agreements",
        sa.Column(
            "has_rpz_backflow",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("service_agreements", "has_rpz_backflow")
