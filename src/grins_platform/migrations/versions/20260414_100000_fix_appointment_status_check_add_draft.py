"""Fix ck_appointments_status CHECK constraint to include 'draft'.

The previous migration (20260412_100200) was a no-op because it assumed
status was only enforced at the Python level. However, the CHECK constraint
ck_appointments_status (created in 20250615_100000, updated in
20260324_100200) blocks INSERT with status='draft'. This migration drops
and recreates the constraint with all 9 valid statuses.

Revision ID: 20260414_100000
Revises: 20260412_100200
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260414_100000"
down_revision: Union[str, None] = "20260412_100200"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('pending','draft','scheduled','confirmed','en_route',"
        "'in_progress','completed','cancelled','no_show')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_appointments_status", "appointments", type_="check")
    op.create_check_constraint(
        "ck_appointments_status",
        "appointments",
        "status IN ('pending','scheduled','confirmed','en_route',"
        "'in_progress','completed','cancelled','no_show')",
    )
