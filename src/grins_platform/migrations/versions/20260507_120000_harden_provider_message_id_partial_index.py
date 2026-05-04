"""Harden ix_campaign_responses_provider_message_id partial index.

Bug #4 (master-plan-run-findings 2026-05-04): the previous predicate
``WHERE provider_message_id IS NOT NULL`` allowed empty strings to
collide on a second-empty insert. Postgres treats ``''`` as a
non-NULL value, so two ``CampaignResponse`` orphan rows with
``provider_message_id=''`` failed the unique partial index.

This migration tightens the predicate to also exclude empty strings.
A pre-flight ``UPDATE`` backfills any pre-existing empty rows to
``NULL`` (allowed under both the old and new predicate) so the new
unique constraint can be created without conflict.

Defense in depth: the application-side coercion in
``campaign_response_service.record_poll_reply`` now passes
``provider_sid or None``, so new rows never reach this path with
an empty string. This migration handles the historical fleet.

Revision ID: 20260507_120000
Revises: 20260506_120000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260507_120000"
down_revision: Union[str, None] = "20260506_120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INDEX_NAME = "ix_campaign_responses_provider_message_id"
_TABLE_NAME = "campaign_responses"
_NEW_PREDICATE = (
    "provider_message_id IS NOT NULL AND provider_message_id <> ''"
)
_OLD_PREDICATE = "provider_message_id IS NOT NULL"


def upgrade() -> None:
    # Step 1: pre-flight backfill so the new predicate doesn't fail
    # if multiple existing rows already have provider_message_id=''.
    op.execute(
        "UPDATE campaign_responses "
        "SET provider_message_id = NULL "
        "WHERE provider_message_id = ''",
    )
    # Step 2: drop the old partial index.
    op.drop_index(
        _INDEX_NAME,
        table_name=_TABLE_NAME,
    )
    # Step 3: recreate with the stricter predicate.
    op.create_index(
        _INDEX_NAME,
        _TABLE_NAME,
        ["provider_message_id"],
        unique=True,
        postgresql_where=_NEW_PREDICATE,
    )


def downgrade() -> None:
    op.drop_index(
        _INDEX_NAME,
        table_name=_TABLE_NAME,
    )
    op.create_index(
        _INDEX_NAME,
        _TABLE_NAME,
        ["provider_message_id"],
        unique=True,
        postgresql_where=_OLD_PREDICATE,
    )
