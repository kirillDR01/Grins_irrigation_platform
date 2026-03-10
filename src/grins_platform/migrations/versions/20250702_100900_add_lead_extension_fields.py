"""Add lead source, intake tag, and consent fields to leads table.

Revision ID: 20250702_100900
Revises: 20250702_100800
Create Date: 2025-07-02 10:09:00

Adds lead_source, source_detail, intake_tag, sms_consent, terms_accepted
to the leads table for source attribution and consent tracking.

Validates: Requirements 44.1, 44.2, 44.3, 44.4, 47.1, 47.2, 47.3, 56.1, 56.2, 56.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100900"
down_revision: Union[str, None] = "20250702_100800"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lead extension fields to leads table."""
    op.add_column(
        "leads",
        sa.Column(
            "lead_source",
            sa.String(50),
            nullable=False,
            server_default="website",
        ),
    )
    op.add_column(
        "leads",
        sa.Column("source_detail", sa.String(255), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column("intake_tag", sa.String(20), nullable=True),
    )
    op.add_column(
        "leads",
        sa.Column(
            "sms_consent",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "leads",
        sa.Column(
            "terms_accepted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Indexes for filtering
    op.create_index("idx_leads_lead_source", "leads", ["lead_source"])
    op.create_index("idx_leads_intake_tag", "leads", ["intake_tag"])


def downgrade() -> None:
    """Remove lead extension fields from leads table."""
    op.drop_index("idx_leads_intake_tag", table_name="leads")
    op.drop_index("idx_leads_lead_source", table_name="leads")
    op.drop_column("leads", "terms_accepted")
    op.drop_column("leads", "sms_consent")
    op.drop_column("leads", "intake_tag")
    op.drop_column("leads", "source_detail")
    op.drop_column("leads", "lead_source")
