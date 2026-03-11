"""Add email_marketing_consent and page_url columns to leads table.

Revision ID: 20250710_100100
Revises: 20250702_101000
Create Date: 2025-07-10 10:01:00

Adds email_marketing_consent (boolean, default false) and page_url (varchar 2048)
to the leads table. Also adds composite index on (email, created_at) for
duplicate detection.

Validates: Requirements 2.1, 5.1
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250710_100100"
down_revision: Union[str, None] = "20250702_101000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email_marketing_consent and page_url to leads table."""
    op.add_column(
        "leads",
        sa.Column(
            "email_marketing_consent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "leads",
        sa.Column("page_url", sa.String(2048), nullable=True),
    )
    op.create_index(
        "idx_leads_email_created_at",
        "leads",
        ["email", "created_at"],
    )


def downgrade() -> None:
    """Remove email_marketing_consent and page_url from leads table."""
    op.drop_index("idx_leads_email_created_at", table_name="leads")
    op.drop_column("leads", "page_url")
    op.drop_column("leads", "email_marketing_consent")
