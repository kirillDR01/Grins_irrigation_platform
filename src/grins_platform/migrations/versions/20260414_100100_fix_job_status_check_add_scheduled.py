"""Fix ck_jobs_status CHECK constraint to include 'scheduled'.

The simplify_job_statuses migration (20260326_120000) removed 'scheduled'
from the allowed job statuses. The smoothing-out update re-added
SCHEDULED to the Python enum and the appointment service auto-transitions
jobs to 'scheduled', but the DB constraint was never updated.

Also updates the job_status_history constraints to match.

Revision ID: 20260414_100100
Revises: 20260414_100000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260414_100100"
down_revision: Union[str, None] = "20260414_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_STATUSES = (
    "to_be_scheduled",
    "scheduled",
    "in_progress",
    "completed",
    "cancelled",
)


def upgrade() -> None:
    # jobs table
    op.drop_constraint("ck_jobs_status", "jobs", type_="check")
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        f"status IN {_NEW_STATUSES!r}",
    )

    # job_status_history table
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
    op.create_check_constraint(
        "ck_job_status_history_previous_status",
        "job_status_history",
        f"previous_status IS NULL OR previous_status IN {_NEW_STATUSES!r}",
    )
    op.create_check_constraint(
        "ck_job_status_history_new_status",
        "job_status_history",
        f"new_status IN {_NEW_STATUSES!r}",
    )


def downgrade() -> None:
    _OLD_STATUSES = ("to_be_scheduled", "in_progress", "completed", "cancelled")

    op.drop_constraint("ck_jobs_status", "jobs", type_="check")
    op.create_check_constraint(
        "ck_jobs_status",
        "jobs",
        f"status IN {_OLD_STATUSES!r}",
    )

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
