"""Reserve opt_out_method='admin_confirmed_informal' in the alembic chain.

Gap 06 — Opt-Out Management & Visibility. The ``SmsConsentRecord.opt_out_method``
column is already ``String(50)`` so no schema change is required for the new
``'admin_confirmed_informal'`` enum-like value introduced by the admin-confirmed
informal-opt-out flow. This migration is intentionally a no-op: it reserves a
revision number in the alembic chain and documents the new allowed value so
future reviewers understand it was considered.

Revision ID: 20260422_100000
Revises: 20260421_100100
Requirements: gap-06 (opt-out management & visibility)
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "20260422_100000"
down_revision: str | None = "20260421_100100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op — column is already String(50); value is new but unconstrained."""


def downgrade() -> None:
    """No-op — nothing to undo."""
