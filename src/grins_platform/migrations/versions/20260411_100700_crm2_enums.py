"""CRM2: Add new enum values and CHECK constraints for CRM2 tables.

Updates sent_messages.message_type CHECK to include google_review_request
and on_my_way. Adds CHECK constraints on sales_entries.status,
job_confirmation_responses.reply_keyword, customer_documents.document_type,
contract_renewal_proposals.status, and contract_renewal_proposed_jobs.status.

Revision ID: 20260411_100700
Revises: 20260411_100600
Requirements: 14.3, 24.1, 17.3, 31.1
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260411_100700"
down_revision: Union[str, None] = "20260411_100600"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Expanded message types (adds google_review_request, on_my_way)
_NEW_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign','google_review_request','on_my_way'"
)

# Previous message types (from migration 20260408_100100)
_PREV_MESSAGE_TYPES = (
    "'appointment_confirmation','appointment_reminder',"
    "'on_the_way','arrival','completion','invoice','payment_reminder',"
    "'custom','lead_confirmation','estimate_sent','contract_sent',"
    "'review_request','campaign'"
)

_SALES_ENTRY_STATUSES = (
    "'schedule_estimate','estimate_scheduled','send_estimate',"
    "'pending_approval','send_contract','closed_won','closed_lost'"
)

_CONFIRMATION_KEYWORDS = "'confirm','reschedule','cancel'"

_DOCUMENT_TYPES = (
    "'estimate','contract','photo','diagram','reference','signed_contract'"
)

_PROPOSAL_STATUSES = "'pending','approved','partially_approved','rejected'"

_PROPOSED_JOB_STATUSES = "'pending','approved','rejected'"


def upgrade() -> None:
    # 1. Update sent_messages message_type CHECK
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_NEW_MESSAGE_TYPES})",
    )

    # 2. Sales entry status CHECK
    op.create_check_constraint(
        "ck_sales_entries_status",
        "sales_entries",
        f"status IN ({_SALES_ENTRY_STATUSES})",
    )

    # 3. Confirmation reply_keyword CHECK (nullable, so NULL is allowed)
    op.create_check_constraint(
        "ck_confirmation_responses_keyword",
        "job_confirmation_responses",
        f"reply_keyword IS NULL OR reply_keyword IN ({_CONFIRMATION_KEYWORDS})",
    )

    # 4. Customer document type CHECK
    op.create_check_constraint(
        "ck_customer_documents_type",
        "customer_documents",
        f"document_type IN ({_DOCUMENT_TYPES})",
    )

    # 5. Contract renewal proposal status CHECK
    op.create_check_constraint(
        "ck_renewal_proposals_status",
        "contract_renewal_proposals",
        f"status IN ({_PROPOSAL_STATUSES})",
    )

    # 6. Contract renewal proposed job status CHECK
    op.create_check_constraint(
        "ck_renewal_proposed_jobs_status",
        "contract_renewal_proposed_jobs",
        f"status IN ({_PROPOSED_JOB_STATUSES})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_renewal_proposed_jobs_status",
        "contract_renewal_proposed_jobs",
        type_="check",
    )
    op.drop_constraint(
        "ck_renewal_proposals_status",
        "contract_renewal_proposals",
        type_="check",
    )
    op.drop_constraint(
        "ck_customer_documents_type",
        "customer_documents",
        type_="check",
    )
    op.drop_constraint(
        "ck_confirmation_responses_keyword",
        "job_confirmation_responses",
        type_="check",
    )
    op.drop_constraint(
        "ck_sales_entries_status",
        "sales_entries",
        type_="check",
    )

    # Revert sent_messages to previous constraint
    op.execute(
        "ALTER TABLE sent_messages "
        "DROP CONSTRAINT IF EXISTS ck_sent_messages_message_type",
    )
    op.create_check_constraint(
        "ck_sent_messages_message_type",
        "sent_messages",
        f"message_type IN ({_PREV_MESSAGE_TYPES})",
    )
