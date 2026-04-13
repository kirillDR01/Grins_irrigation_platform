#!/usr/bin/env python3
"""Password hardening migration script.

Standalone script (not Alembic) that reads NEW_ADMIN_PASSWORD from env,
validates strength criteria, hashes with bcrypt cost 12, and updates
the admin staff row.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

from __future__ import annotations

import os
import re
import sys

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BCRYPT_ROUNDS = 12
USERNAME = "admin"


def get_database_url() -> str:
    """Load DATABASE_URL from environment or .env file."""
    load_dotenv()
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)
    # Ensure sync driver (strip asyncpg if present)
    return url.replace("postgresql+asyncpg://", "postgresql://")


def validate_password(password: str) -> list[str]:
    """Validate password meets strength criteria.

    Criteria: 16+ chars, mixed case, digits, at least one common symbol.
    Returns list of failure reasons (empty = valid).
    """
    errors: list[str] = []
    if len(password) < 16:
        errors.append(f"Must be at least 16 characters (got {len(password)})")
    if not re.search(r"[a-z]", password):
        errors.append("Must contain at least one lowercase letter")
    if not re.search(r"[A-Z]", password):
        errors.append("Must contain at least one uppercase letter")
    if not re.search(r"\d", password):
        errors.append("Must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        errors.append("Must contain at least one symbol")
    return errors


def main() -> None:
    """Run the password hardening migration."""
    load_dotenv()

    # Req 1.2: Abort if env var missing
    new_password = os.getenv("NEW_ADMIN_PASSWORD")
    if not new_password:
        print("ERROR: NEW_ADMIN_PASSWORD environment variable is not set.")
        print("Set it before running this script:")
        print('  export NEW_ADMIN_PASSWORD="YourStr0ng!Passphrase"')
        sys.exit(1)

    # Req 1.4: Validate strength
    errors = validate_password(new_password)
    if errors:
        print("ERROR: Password does not meet strength requirements:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Req 1.1: Hash with bcrypt cost 12
    password_hash = bcrypt.hashpw(
        new_password.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")

    # Update admin row (Req 1.3: username stays 'admin')
    db_url = get_database_url()
    engine = create_engine(db_url)

    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE staff SET password_hash = :hash WHERE username = :username",
            ),
            {"hash": password_hash, "username": USERNAME},
        )
        if result.rowcount == 0:
            print(f"ERROR: No staff row found with username '{USERNAME}'.")
            sys.exit(1)

    print(f"SUCCESS: Password updated for user '{USERNAME}'.")
    engine.dispose()


if __name__ == "__main__":
    main()
