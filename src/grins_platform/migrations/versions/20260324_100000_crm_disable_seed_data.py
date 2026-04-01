"""CRM Gap Closure: Disable seed data migrations.

Revision ID: 20260324_100000
Revises: 20260313_100000
Create Date: 2026-03-24

Removes seed demo data inserted by earlier seed migrations.
Only references tables that exist at this point in the migration chain
(before 20260324_100100 creates new CRM tables).

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

    Only deletes from tables that exist BEFORE 20260324_100100.
    Tables like expenses, estimates, campaigns, communications,
    customer_photos are created in later migrations and are skipped here.

    FK-safe delete order:
      disclosure_records(agr) → agreement_status_logs → jobs(nullify agr) →
      service_agreements → appointments → job_status_history →
      schedule_waitlist → invoices(job) → sent_messages(job) → jobs →
      invoices(cust) → disclosure_records(cust) → sms_consent_records →
      sent_messages(cust) → email_suppression_list → properties → customers →
      staff_availability → staff → service_offerings
    """
    _SEED_PHONES_SUBQUERY = """
        SELECT id FROM customers
        WHERE phone IN (
            '6125551001','6125551002','6125551003','6125551004',
            '6125551005','6125551006','6125551007','6125551008',
            '6125551009','6125551010'
        )
    """

    _SEED_AGREEMENTS_SUBQUERY = f"""
        SELECT id FROM service_agreements
        WHERE customer_id IN ({_SEED_PHONES_SUBQUERY})
    """

    _SEED_JOBS_SUBQUERY = f"""
        SELECT id FROM jobs
        WHERE customer_id IN ({_SEED_PHONES_SUBQUERY})
    """

    # ── Phase 1: Clear service_agreement dependents ──────────────────

    # disclosure_records → service_agreements.id (no CASCADE)
    op.execute(
        text(
            f"""
            DELETE FROM disclosure_records
            WHERE agreement_id IN ({_SEED_AGREEMENTS_SUBQUERY});
            """,
        ),
    )

    # agreement_status_logs → service_agreements.id (CASCADE, but explicit)
    op.execute(
        text(
            f"""
            DELETE FROM agreement_status_logs
            WHERE agreement_id IN ({_SEED_AGREEMENTS_SUBQUERY});
            """,
        ),
    )

    # jobs.service_agreement_id → service_agreements.id (no CASCADE)
    op.execute(
        text(
            f"""
            UPDATE jobs SET service_agreement_id = NULL
            WHERE service_agreement_id IN ({_SEED_AGREEMENTS_SUBQUERY});
            """,
        ),
    )

    # Delete seed service_agreements
    op.execute(
        text(
            f"""
            DELETE FROM service_agreements
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # ── Phase 2: Clear job dependents ────────────────────────────────

    # appointments → jobs.id (no CASCADE)
    op.execute(
        text(
            f"""
            DELETE FROM appointments
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # job_status_history → jobs.id (CASCADE, but explicit)
    op.execute(
        text(
            f"""
            DELETE FROM job_status_history
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # schedule_waitlist → jobs.id
    op.execute(
        text(
            f"""
            DELETE FROM schedule_waitlist
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # invoices → jobs.id (RESTRICT)
    op.execute(
        text(
            f"""
            DELETE FROM invoices
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # sent_messages → jobs.id
    op.execute(
        text(
            f"""
            DELETE FROM sent_messages
            WHERE job_id IN ({_SEED_JOBS_SUBQUERY});
            """,
        ),
    )

    # Delete seed jobs
    op.execute(
        text(
            f"""
            DELETE FROM jobs
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # ── Phase 3: Clear customer dependents ───────────────────────────

    # invoices → customers.id (RESTRICT)
    op.execute(
        text(
            f"""
            DELETE FROM invoices
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # disclosure_records → customers.id
    op.execute(
        text(
            f"""
            DELETE FROM disclosure_records
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # sms_consent_records → customers.id
    op.execute(
        text(
            f"""
            DELETE FROM sms_consent_records
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # sent_messages → customers.id
    op.execute(
        text(
            f"""
            DELETE FROM sent_messages
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # email_suppression_list → customers.id
    op.execute(
        text(
            f"""
            DELETE FROM email_suppression_list
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # leads.customer_id → customers.id (SET NULL — auto-handled, but explicit)
    op.execute(
        text(
            f"""
            UPDATE leads SET customer_id = NULL
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
            """,
        ),
    )

    # properties → customers.id (CASCADE — auto-handled, but explicit)
    op.execute(
        text(
            f"""
            DELETE FROM properties
            WHERE customer_id IN ({_SEED_PHONES_SUBQUERY});
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

    # ── Phase 4: Staff and offerings ─────────────────────────────────

    op.execute(
        text(
            "DELETE FROM staff_availability "
            "WHERE notes = 'Auto-generated availability';",
        ),
    )

    op.execute(
        text(
            """
            DELETE FROM staff
            WHERE phone IN ('6125552001','6125552002','6125552003','6125552004');
            """,
        ),
    )

    # Only delete seed service_offerings that are NOT referenced by any jobs
    op.execute(
        text(
            """
            DELETE FROM service_offerings
            WHERE name IN (
                'Spring Startup','Summer Tune-Up','Winterization',
                'Sprinkler Head Replacement','Valve Repair','Pipe Repair',
                'System Diagnostic','New Zone Installation',
                'Drip Irrigation Setup','Full System Installation'
            )
            AND id NOT IN (
                SELECT DISTINCT service_offering_id FROM jobs
                WHERE service_offering_id IS NOT NULL
            );
            """,
        ),
    )


def downgrade() -> None:
    """Seed data removal is not reversible via migration.

    Re-run the original seed migrations manually if needed.
    """
