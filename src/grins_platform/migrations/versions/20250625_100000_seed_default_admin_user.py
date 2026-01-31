"""Seed default admin user.

Revision ID: 20250625_100000
Revises: 20250624_100000
Create Date: 2025-01-31

This migration seeds a default admin user for initial system access.
The password is 'admin123' - MUST be changed in production!

Requirements: Initial system access
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20250625_100000"
down_revision: Union[str, None] = "20250624_100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Bcrypt hash for password 'admin123' with cost factor 12
# Generated using: bcrypt.hashpw(b'admin123', bcrypt.gensalt(rounds=12))
ADMIN_PASSWORD_HASH = "$2b$12$78/uKg0svkDIbuPjaUemkOvVApU7z6dJfgXfODGiw8w27KRtzCcL."


def upgrade() -> None:
    """Seed default admin user.

    Creates an admin user with:
    - Username: admin
    - Password: admin123 (bcrypt hashed)
    - Role: admin
    - Login enabled: true

    WARNING: Change this password immediately in production!
    """
    op.execute(
        text(
            """
            INSERT INTO staff (
                name,
                phone,
                email,
                role,
                username,
                password_hash,
                is_login_enabled,
                is_active,
                is_available
            ) VALUES (
                'Admin User',
                '6125551234',
                'admin@grins-irrigations.com',
                'admin',
                'admin',
                :password_hash,
                true,
                true,
                true
            )
            ON CONFLICT DO NOTHING;
            """,
        ).bindparams(password_hash=ADMIN_PASSWORD_HASH),
    )


def downgrade() -> None:
    """Remove default admin user."""
    op.execute(
        text(
            """
            DELETE FROM staff
            WHERE username = 'admin'
            AND email = 'admin@grins-irrigations.com';
            """,
        ),
    )
