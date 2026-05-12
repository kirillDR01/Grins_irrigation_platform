#!/usr/bin/env python3
"""Create a login-enabled technician staff row for dev/QA.

Idempotent upsert keyed by username. Creates (or resets) a Staff row with:
  username=tech, password=tech123, role=tech, is_login_enabled=True

Refuses to run against production. Uses the test-safe phone/email pair so
the same row is safe if the script is re-run in any env.

Usage:
    python scripts/oneoff/2026-05-12-create-tech-staff.py
"""

from __future__ import annotations

import os
import sys
import uuid

import bcrypt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

BCRYPT_ROUNDS = 12

USERNAME = "tech"
PASSWORD = "tech123"
NAME = "Dev Technician"
ROLE = "tech"
PHONE = "9527373312"  # +19527373312 normalized (SMS_TEST_PHONE_ALLOWLIST)
EMAIL = "kirillrakitinsecond+tech@gmail.com"


def get_database_url() -> str:
    load_dotenv()
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL is not set.")
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://")


def main() -> None:
    load_dotenv()

    env = os.getenv("ENVIRONMENT", "development").lower()
    if env == "production":
        print("ERROR: Refusing to create weak-password tech account in production.")
        sys.exit(1)

    password_hash = bcrypt.hashpw(
        PASSWORD.encode("utf-8"),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")

    engine = create_engine(get_database_url())
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM staff WHERE username = :u"),
            {"u": USERNAME},
        ).first()

        if existing:
            conn.execute(
                text(
                    "UPDATE staff SET password_hash = :h, is_login_enabled = TRUE, "
                    "is_active = TRUE, role = :r, failed_login_attempts = 0, "
                    "locked_until = NULL WHERE username = :u"
                ),
                {"h": password_hash, "r": ROLE, "u": USERNAME},
            )
            print(f"SUCCESS: Reset password and re-enabled login for '{USERNAME}' (id={existing[0]}).")
        else:
            new_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO staff (id, name, phone, email, role, username, "
                    "password_hash, is_login_enabled, is_available, is_active) "
                    "VALUES (:id, :name, :phone, :email, :role, :username, "
                    ":pwd, TRUE, TRUE, TRUE)"
                ),
                {
                    "id": new_id,
                    "name": NAME,
                    "phone": PHONE,
                    "email": EMAIL,
                    "role": ROLE,
                    "username": USERNAME,
                    "pwd": password_hash,
                },
            )
            print(f"SUCCESS: Created technician staff '{USERNAME}' (id={new_id}).")

    engine.dispose()
    print(f"Login at /login with username='{USERNAME}' password='{PASSWORD}'.")


if __name__ == "__main__":
    main()
