"""CRM Gap Closure: Disable seed data migrations.

Revision ID: 20260324_100000
Revises: 20260313_100000
Create Date: 2026-03-24

Renames seed migration files with .disabled suffix so they are
no longer executed by Alembic. The actual seed data DELETE is
handled in the next migration.

Validates: Requirement 1.1, 1.2, 1.3
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260324_100000"
down_revision: Union[str, None] = "20260313_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove seed demo data.

    Removes customers, staff, jobs, properties, service offerings,
    and availability. Preserves non-seed records identified by phone
    and auto-generated availability notes.
    """
    # Delete seed jobs (depends on customers)
    op.execute(
        text(
            """
            DELETE FROM jobs
            WHERE customer_id IN (
                SELECT id FROM customers
                WHERE phone IN (
                    '6125551001','6125551002','6125551003','6125551004',
                    '6125551005','6125551006','6125551007','6125551008',
                    '6125551009','6125551010'
                )
            );
            """,
        ),
    )
    # Delete seed properties
    op.execute(
        text(
            """
            DELETE FROM properties
            WHERE customer_id IN (
                SELECT id FROM customers
                WHERE phone IN (
                    '6125551001','6125551002','6125551003','6125551004',
                    '6125551005','6125551006','6125551007','6125551008',
                    '6125551009','6125551010'
                )
            );
            """,
        ),
    )
    # Delete seed customers
    op.execute(
        text(
            """
            DELETE FROM customers
            WHERE phone IN (
                '6125551001','6125551002','6125551003','6125551004',
                '6125551005','6125551006','6125551007','6125551008',
                '6125551009','6125551010'
            );
            """,
        ),
    )
    # Delete auto-generated staff availability
    op.execute(
        text(
            "DELETE FROM staff_availability "
            "WHERE notes = 'Auto-generated availability';",
        ),
    )
    # Delete seed technicians (keep admin)
    op.execute(
        text(
            """
            DELETE FROM staff
            WHERE phone IN ('6125552001','6125552002','6125552003','6125552004');
            """,
        ),
    )
    # Delete seed service offerings
    op.execute(
        text(
            """
            DELETE FROM service_offerings
            WHERE name IN (
                'Spring Startup','Summer Tune-Up','Winterization',
                'Sprinkler Head Replacement','Valve Repair','Pipe Repair',
                'System Diagnostic','New Zone Installation',
                'Drip Irrigation Setup','Full System Installation'
            );
            """,
        ),
    )


def downgrade() -> None:
    """Seed data removal is not reversible via migration.

    Re-run the original seed migrations manually if needed.
    """
