"""Create sms_consent_records table.

Revision ID: 20250702_100500
Revises: 20250702_100400
Create Date: 2025-07-02 10:05:00

Creates the sms_consent_records table for TCPA compliance.
INSERT-ONLY table with indexes on phone_number, customer_id, and consent_token.

Validates: Requirements 29.1, 29.2, 29.3, 29.4
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20250702_100500"
down_revision: Union[str, None] = "20250702_100400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sms_consent_records table."""
    op.create_table(
        "sms_consent_records",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=True,
        ),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("consent_type", sa.String(20), nullable=False),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column(
            "consent_timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("consent_method", sa.String(50), nullable=False),
        sa.Column("consent_language_shown", sa.Text(), nullable=False),
        sa.Column("consent_form_version", sa.String(20), nullable=True),
        sa.Column("consent_ip_address", sa.String(45), nullable=True),
        sa.Column("consent_user_agent", sa.String(500), nullable=True),
        sa.Column("consent_token", sa.UUID(), nullable=True),
        sa.Column(
            "opt_out_timestamp",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column("opt_out_method", sa.String(50), nullable=True),
        sa.Column(
            "opt_out_processed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "opt_out_confirmation_sent",
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
        "ix_sms_consent_records_phone_number",
        "sms_consent_records",
        ["phone_number"],
    )
    op.create_index(
        "ix_sms_consent_records_customer_id",
        "sms_consent_records",
        ["customer_id"],
    )
    op.create_index(
        "ix_sms_consent_records_consent_token",
        "sms_consent_records",
        ["consent_token"],
    )


def downgrade() -> None:
    """Drop sms_consent_records table."""
    op.drop_index("ix_sms_consent_records_consent_token", "sms_consent_records")
    op.drop_index("ix_sms_consent_records_customer_id", "sms_consent_records")
    op.drop_index("ix_sms_consent_records_phone_number", "sms_consent_records")
    op.drop_table("sms_consent_records")
