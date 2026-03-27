"""Add customer_type and property_type columns to leads table.

Revision ID: 20260326_100000
Revises: 20260325_100000
Create Date: 2026-03-26

Adds nullable columns for customer_type (new/existing) and
property_type (RESIDENTIAL/COMMERCIAL) to capture frontend form data.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260326_100000"
down_revision: Union[str, None] = "20260325_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leads", sa.Column("customer_type", sa.String(20), nullable=True))
    op.add_column("leads", sa.Column("property_type", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("leads", "property_type")
    op.drop_column("leads", "customer_type")
