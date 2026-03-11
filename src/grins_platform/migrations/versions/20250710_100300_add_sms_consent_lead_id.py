"""Add lead_id foreign key to sms_consent_records table.

Revision ID: 20250710_100300
Revises: 20250710_100200
Create Date: 2025-07-10 10:03:00

Adds lead_id (UUID FK to leads.id, nullable) with index for linking
consent records to leads before customer conversion.

Validates: Requirements 7.2
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250710_100300"
down_revision: Union[str, None] = "20250710_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add lead_id FK to sms_consent_records."""
    op.add_column(
        "sms_consent_records",
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_sms_consent_records_lead_id",
        "sms_consent_records",
        ["lead_id"],
    )


def downgrade() -> None:
    """Remove lead_id from sms_consent_records."""
    op.drop_index("ix_sms_consent_records_lead_id", table_name="sms_consent_records")
    op.drop_column("sms_consent_records", "lead_id")
