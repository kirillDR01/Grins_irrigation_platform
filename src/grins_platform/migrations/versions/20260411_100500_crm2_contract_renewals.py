"""CRM2: Create contract_renewal_proposals and contract_renewal_proposed_jobs tables.

Tables for the contract renewal review queue where admins can
approve, reject, or modify proposed jobs before they become real jobs.

Revision ID: 20260411_100500
Revises: 20260411_100400
Requirements: 31.1, 31.5
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100500"
down_revision: Union[str, None] = "20260411_100400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_renewal_proposals",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "service_agreement_id",
            sa.UUID(),
            sa.ForeignKey("service_agreements.id"),
            nullable=False,
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("proposed_job_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by",
            sa.UUID(),
            sa.ForeignKey("staff.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_renewal_proposals_status",
        "contract_renewal_proposals",
        ["status"],
    )

    op.create_table(
        "contract_renewal_proposed_jobs",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "proposal_id",
            sa.UUID(),
            sa.ForeignKey("contract_renewal_proposals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_type", sa.String(100), nullable=False),
        sa.Column("target_start_date", sa.Date(), nullable=True),
        sa.Column("target_end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("proposed_job_payload", sa.JSON(), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_renewal_proposed_jobs_proposal",
        "contract_renewal_proposed_jobs",
        ["proposal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_renewal_proposed_jobs_proposal",
        table_name="contract_renewal_proposed_jobs",
    )
    op.drop_table("contract_renewal_proposed_jobs")
    op.drop_index(
        "idx_renewal_proposals_status",
        table_name="contract_renewal_proposals",
    )
    op.drop_table("contract_renewal_proposals")
