"""Drop additional_info column from google_sheet_submissions.

Revision ID: 20250701_100000
Revises: 20250630_100000
Create Date: 2025-07-01 10:00:00

Column layout changed from 19 to 18 columns — the additional_info
column (old column O) was removed and subsequent columns shifted up.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250701_100000"
down_revision: Union[str, None] = "20250630_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the additional_info column from google_sheet_submissions."""
    op.drop_column("google_sheet_submissions", "additional_info")


def downgrade() -> None:
    """Re-add the additional_info column to google_sheet_submissions."""
    op.add_column(
        "google_sheet_submissions",
        sa.Column("additional_info", sa.Text(), nullable=True),
    )
