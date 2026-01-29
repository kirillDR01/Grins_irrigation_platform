"""Add staff authentication columns.

Revision ID: 20250621_100000
Revises: 20250620_100200
Create Date: 2025-01-28

This migration adds authentication-related columns to the staff table:
- username: Unique username for login
- password_hash: Bcrypt hashed password
- is_login_enabled: Whether the user can log in
- last_login: Timestamp of last successful login
- failed_login_attempts: Counter for failed login attempts
- locked_until: Timestamp until which account is locked

Requirements: 15.1-15.8
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250621_100000"
down_revision = "20250620_100200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add authentication columns to staff table."""
    # Add username column (unique, nullable)
    op.add_column(
        "staff",
        sa.Column("username", sa.String(50), nullable=True),
    )

    # Add password_hash column (nullable)
    op.add_column(
        "staff",
        sa.Column("password_hash", sa.String(255), nullable=True),
    )

    # Add is_login_enabled column (default FALSE)
    op.add_column(
        "staff",
        sa.Column(
            "is_login_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Add last_login column
    op.add_column(
        "staff",
        sa.Column("last_login", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Add failed_login_attempts column (default 0)
    op.add_column(
        "staff",
        sa.Column(
            "failed_login_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Add locked_until column
    op.add_column(
        "staff",
        sa.Column("locked_until", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create unique index on username where username is not null
    op.create_index(
        "ix_staff_username",
        "staff",
        ["username"],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove authentication columns from staff table."""
    # Drop the index first
    op.drop_index("ix_staff_username", table_name="staff")

    # Drop columns in reverse order
    op.drop_column("staff", "locked_until")
    op.drop_column("staff", "failed_login_attempts")
    op.drop_column("staff", "last_login")
    op.drop_column("staff", "is_login_enabled")
    op.drop_column("staff", "password_hash")
    op.drop_column("staff", "username")
