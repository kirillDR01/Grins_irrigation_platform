"""Create disclosure_records table.

Revision ID: 20250702_100400
Revises: 20250702_100300
Create Date: 2025-07-02 10:04:00

Creates the disclosure_records table for MN auto-renewal compliance.
INSERT-ONLY table with indexes on agreement_id, customer_id,
(disclosure_type, sent_at), and consent_token.

Validates: Requirements 33.1, 33.2, 33.3, 33.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100400"
down_revision: Union[str, None] = "20250702_100300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create disclosure_records table."""
    op.create_table(
        "disclosure_records",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "agreement_id",
            sa.UUID(),
            sa.ForeignKey("service_agreements.id"),
            nullable=True,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=True,
        ),
        sa.Column("disclosure_type", sa.String(30), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("sent_via", sa.String(20), nullable=False),
        sa.Column("recipient_email", sa.String(255), nullable=True),
        sa.Column("recipient_phone", sa.String(20), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=True),
        sa.Column("consent_token", sa.UUID(), nullable=True),
        sa.Column(
            "delivery_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_disclosure_records_agreement_id",
        "disclosure_records",
        ["agreement_id"],
    )
    op.create_index(
        "ix_disclosure_records_customer_id",
        "disclosure_records",
        ["customer_id"],
    )
    op.create_index(
        "ix_disclosure_records_type_sent_at",
        "disclosure_records",
        ["disclosure_type", "sent_at"],
    )
    op.create_index(
        "ix_disclosure_records_consent_token",
        "disclosure_records",
        ["consent_token"],
    )


def downgrade() -> None:
    """Drop disclosure_records table."""
    op.drop_index("ix_disclosure_records_consent_token", "disclosure_records")
    op.drop_index("ix_disclosure_records_type_sent_at", "disclosure_records")
    op.drop_index("ix_disclosure_records_customer_id", "disclosure_records")
    op.drop_index("ix_disclosure_records_agreement_id", "disclosure_records")
    op.drop_table("disclosure_records")
