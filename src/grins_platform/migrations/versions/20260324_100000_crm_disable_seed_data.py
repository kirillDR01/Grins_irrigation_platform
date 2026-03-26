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

    Delete order respects FK constraints:
      agreement_status_logs → service_agreements → jobs → invoices →
      disclosure_records → sms_consent_records → sent_messages →
      communications → customer_photos → email_suppression_list →
      estimates → campaigns → properties → customers
    """
    _SEED_PHONES_SUBQUERY = """
        SELECT id FROM customers
        WHERE phone IN (
            '6125551001','6125551002','6125551003','6125551004',
            '6125551005','6125551006','6125551007','6125551008',
            '6125551009','6125551010'
        )
    """

    # 1. Delete agreement_status_logs for seed agreements
    op.execute(
        text(
            f"""
            DELETE FROM agreement_status_logs
            WHERE agreement_id IN (
                SELECT id FROM service_agreements
                WHERE customer_id IN ({_SEED_PHONES_SUBQUERY})
            );
            """,
        ),
    )

    # 2. Delete service_agreements for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM service_agreements
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 3. Delete job-dependent tables before deleting jobs
    _SEED_JOBS_SUBQUERY = f"""
        SELECT id FROM jobs
        WHERE customer_id IN ({_SEED_PHONES_SUBQUERY})
    """
    # 3a. Appointments → jobs.id
    op.execute(
        text(
            f"""
            DELETE FROM appointments
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3b. Job status history → jobs.id (CASCADE, but be explicit)
    op.execute(
        text(
            f"""
            DELETE FROM job_status_history
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3c. Schedule waitlist → jobs.id
    op.execute(
        text(
            f"""
            DELETE FROM schedule_waitlist
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3d. Invoices → jobs.id (RESTRICT)
    op.execute(
        text(
            f"""
            DELETE FROM invoices
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3e. Expenses → jobs.id (SET NULL — nullify instead of delete)
    op.execute(
        text(
            f"""
            UPDATE expenses SET job_id = NULL
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3f. Estimates → jobs.id (SET NULL)
    op.execute(
        text(
            f"""
            UPDATE estimates SET job_id = NULL
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )
    # 3g. Sent messages → jobs.id
    op.execute(
        text(
            f"""
            DELETE FROM sent_messages
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # 4. Delete seed jobs
    op.execute(
        text(
            f"""
            DELETE FROM jobs
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 5. Delete remaining invoices referencing seed customers (not via jobs)
    op.execute(
        text(
            f"""
            DELETE FROM invoices
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 5. Delete disclosure_records for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM disclosure_records
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 6. Delete sms_consent_records for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM sms_consent_records
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 7. Delete sent_messages for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM sent_messages
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 8. Delete communications for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM communications
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 9. Delete customer_photos for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM customer_photos
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 10. Delete email_suppression_list for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM email_suppression_list
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 11. Delete estimates for seed customers
    op.execute(
        text(
            f"""
            DELETE FROM estimates
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 12. Delete campaigns targeting seed customers
    op.execute(
        text(
            f"""
            DELETE FROM campaigns
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 13. Delete seed properties (now safe — no FK refs remain)
    op.execute(
        text(
            f"""
            DELETE FROM properties
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # 14. Delete seed customers
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
