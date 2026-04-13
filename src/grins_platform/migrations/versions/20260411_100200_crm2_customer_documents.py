"""CRM2: Create customer_documents table.

Table for storing customer document metadata (PDFs, images, etc.)
with S3 file references.

Revision ID: 20260411_100200
Revises: 20260411_100100
Requirements: 17.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_100200"
down_revision: Union[str, None] = "20260411_100100"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_documents",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "customer_id",
            sa.UUID(),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(512), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_customer_documents_customer_id",
        "customer_documents",
        ["customer_id"],
    )
    op.create_index(
        "ix_customer_documents_document_type",
        "customer_documents",
        ["document_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_customer_documents_document_type",
        table_name="customer_documents",
    )
    op.drop_index(
        "ix_customer_documents_customer_id",
        table_name="customer_documents",
    )
    op.drop_table("customer_documents")
