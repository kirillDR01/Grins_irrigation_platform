"""Add ``webauthn_credentials`` and ``webauthn_user_handles`` tables.

Revision ID: 20260427_100000
Revises: 20260426_100000
Validates: Biometric / Passkey authentication feature
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260427_100000"
down_revision: str | None = "20260426_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the WebAuthn credential and user-handle tables."""
    op.create_table(
        "webauthn_user_handles",
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_handle", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "webauthn_credentials",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "staff_id",
            sa.UUID(),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column(
            "sign_count",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("transports", postgresql.JSONB(), nullable=True),
        sa.Column("aaguid", sa.String(36), nullable=True),
        sa.Column(
            "credential_device_type",
            sa.String(20),
            sa.CheckConstraint(
                "credential_device_type IN ('single_device', 'multi_device')",
                name="ck_webauthn_credentials_device_type",
            ),
            nullable=False,
        ),
        sa.Column(
            "backup_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "backup_state",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("device_name", sa.String(100), nullable=False),
        sa.Column(
            "last_used_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "revoked_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "ix_webauthn_credentials_staff_id",
        "webauthn_credentials",
        ["staff_id"],
    )
    op.create_index(
        "ix_webauthn_credentials_credential_id",
        "webauthn_credentials",
        ["credential_id"],
    )


def downgrade() -> None:
    """Drop the WebAuthn tables in reverse-create order."""
    op.drop_index(
        "ix_webauthn_credentials_credential_id",
        table_name="webauthn_credentials",
    )
    op.drop_index(
        "ix_webauthn_credentials_staff_id",
        table_name="webauthn_credentials",
    )
    op.drop_table("webauthn_credentials")
    op.drop_table("webauthn_user_handles")
