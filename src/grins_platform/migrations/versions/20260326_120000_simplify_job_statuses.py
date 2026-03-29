"""Simplify job statuses from 7 to 4.

Collapse requested/approved → to_be_scheduled, scheduled → in_progress,
closed → completed. Keep in_progress, completed, cancelled as-is.

Revision ID: simplify_job_statuses
Revises: 20260326_100000
"""

from alembic import op

revision = "20260326_120000"
down_revision = "20260326_100000"
branch_labels = None
depends_on = None

# Old → New mapping
_STATUS_MAP = {
    "requested": "to_be_scheduled",
    "approved": "to_be_scheduled",
    "scheduled": "in_progress",
    "closed": "completed",
}

_NEW_STATUSES = ("to_be_scheduled", "in_progress", "completed", "cancelled")

_OLD_STATUSES = (
    "requested",
    "approved",
    "scheduled",
    "in_progress",
    "completed",
    "cancelled",
    "closed",
)


def upgrade() -> None:
    # --- jobs table ---
    # Drop old CHECK constraint
    op.drop_constraint("ck_jobs_status", "jobs", type_="check")

    # Migrate data
    for old, new in _STATUS_MAP.items():
        op.execute(f"UPDATE jobs SET status = '{new}' WHERE status = '{old}'")

    # Change server_default
    op.alter_column("jobs", "status", server_default="to_be_scheduled")

    # Add new CHECK constraint
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        f"status IN {_NEW_STATUSES!r}",
    )

    # --- job_status_history table ---
    # Drop old CHECK constraints (they may not exist in all environments)
    op.drop_constraint(
        "ck_job_status_history_previous_status",
        "job_status_history",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_status_history_new_status",
        "job_status_history",
        type_="check",
    )

    # Migrate history data
    for old, new in _STATUS_MAP.items():
        op.execute(
            f"UPDATE job_status_history SET previous_status = '{new}' "
            f"WHERE previous_status = '{old}'",
        )
        op.execute(
            f"UPDATE job_status_history SET new_status = '{new}' "
            f"WHERE new_status = '{old}'",
        )

    # Add new CHECK constraints for history
    new_with_null = _NEW_STATUSES
    op.create_check_constraint(
        "ck_job_status_history_previous_status",
        "job_status_history",
        f"previous_status IS NULL OR previous_status IN {new_with_null!r}",
    )
    op.create_check_constraint(
        "ck_job_status_history_new_status",
        "job_status_history",
        f"new_status IN {new_with_null!r}",
    )


def downgrade() -> None:
    # Reverse mapping: new → old (pick canonical old value)
    _REVERSE_MAP = {
        "to_be_scheduled": "approved",
    }

    # --- jobs table ---
    op.drop_constraint("ck_jobs_status", "jobs", type_="check")

    for new, old in _REVERSE_MAP.items():
        op.execute(f"UPDATE jobs SET status = '{old}' WHERE status = '{new}'")

    op.alter_column("jobs", "status", server_default="requested")

    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        f"status IN {_OLD_STATUSES!r}",
    )

    # --- job_status_history table ---
    op.drop_constraint(
        "ck_job_status_history_previous_status",
        "job_status_history",
        type_="check",
    )
    op.drop_constraint(
        "ck_job_status_history_new_status",
        "job_status_history",
        type_="check",
    )

    for new, old in _REVERSE_MAP.items():
        op.execute(
            f"UPDATE job_status_history SET previous_status = '{old}' "
            f"WHERE previous_status = '{new}'",
        )
        op.execute(
            f"UPDATE job_status_history SET new_status = '{old}' "
            f"WHERE new_status = '{new}'",
        )

    op.create_check_constraint(
        "ck_job_status_history_previous_status",
        "job_status_history",
        f"previous_status IS NULL OR previous_status IN {_OLD_STATUSES!r}",
    )
    op.create_check_constraint(
        "ck_job_status_history_new_status",
        "job_status_history",
        f"new_status IN {_OLD_STATUSES!r}",
    )
