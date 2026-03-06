"""Create google_sheet_submissions table.

Revision ID: 20250630_100000
Revises: 20250629_100000
Create Date: 2025-06-30 10:00:00

Stores raw Google Form response rows (19 columns as nullable strings),
processing metadata, and an optional foreign key to leads.

Validates: Requirements 2.2
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250630_100000"
down_revision: Union[str, None] = "20250629_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create google_sheet_submissions table with indexes and constraints."""
    op.create_table(
        "google_sheet_submissions",
        # Primary key
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("sheet_row_number", sa.Integer(), nullable=False, unique=True),
        # 19 sheet columns — all nullable strings
        sa.Column("timestamp", sa.String(255), nullable=True),
        sa.Column("spring_startup", sa.String(255), nullable=True),
        sa.Column("fall_blowout", sa.String(255), nullable=True),
        sa.Column("summer_tuneup", sa.String(255), nullable=True),
        sa.Column("repair_existing", sa.String(255), nullable=True),
        sa.Column("new_system_install", sa.String(255), nullable=True),
        sa.Column("addition_to_system", sa.String(255), nullable=True),
        sa.Column("additional_services_info", sa.Text(), nullable=True),
        sa.Column("date_work_needed_by", sa.String(255), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("additional_info", sa.Text(), nullable=True),
        sa.Column("client_type", sa.String(50), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("referral_source", sa.Text(), nullable=True),
        sa.Column("landscape_hardscape", sa.Text(), nullable=True),
        # Processing metadata
        sa.Column(
            "processing_status",
            sa.String(20),
            nullable=False,
            server_default="imported",
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Timestamps
        sa.Column(
            "imported_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
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
    )

    # Indexes for query performance
    op.create_index(
        "idx_submissions_client_type",
        "google_sheet_submissions",
        ["client_type"],
    )
    op.create_index(
        "idx_submissions_processing_status",
        "google_sheet_submissions",
        ["processing_status"],
    )
    op.create_index(
        "idx_submissions_imported_at",
        "google_sheet_submissions",
        ["imported_at"],
    )


def downgrade() -> None:
    """Drop google_sheet_submissions table and indexes."""
    op.drop_index(
        "idx_submissions_imported_at",
        table_name="google_sheet_submissions",
    )
    op.drop_index(
        "idx_submissions_processing_status",
        table_name="google_sheet_submissions",
    )
    op.drop_index(
        "idx_submissions_client_type",
        table_name="google_sheet_submissions",
    )
    op.drop_table("google_sheet_submissions")
