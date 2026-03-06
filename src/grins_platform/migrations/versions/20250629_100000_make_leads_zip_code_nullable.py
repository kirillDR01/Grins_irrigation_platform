"""Make leads.zip_code nullable for Google Sheet submissions.

Revision ID: 20250629_100000
Revises: 20250628_100000
Create Date: 2025-06-29 10:00:00

Google Sheet submissions lack zip codes. Rather than inventing data,
leads.zip_code becomes nullable. The public form endpoint continues
to require it via Pydantic validation.

Validates: Requirements 4.1, 4.3, 15.3
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250629_100000"
down_revision: Union[str, None] = "20250628_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make leads.zip_code nullable."""
    op.alter_column("leads", "zip_code", nullable=True, existing_type=sa.String(10))


def downgrade() -> None:
    """Backfill NULLs with placeholder and restore NOT NULL."""
    op.execute("UPDATE leads SET zip_code = '00000' WHERE zip_code IS NULL")
    op.alter_column("leads", "zip_code", nullable=False, existing_type=sa.String(10))
