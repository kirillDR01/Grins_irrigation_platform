"""Seed today's appointments for the tech-companion mobile schedule view.

Idempotent. Does NOT create or modify Staff rows — they were seeded by
migration ``20250626_100000_seed_demo_data.py`` with login credentials
``vas / steven / vitallik`` (password ``tech123``). This script only
creates / updates Customers, Properties, Jobs, and Appointments so each
tech has a distinct daily schedule that exercises every visual state of
the ``MobileJobCard``:

  vas        — 3 appts today: completed / in_progress / scheduled
  steven     — 2 appts today: scheduled  / en_route   (per-tech isolation)
  vitallik   — 0 appts today                          (empty state)

Re-run safe:
- Customers / properties keyed by stable email (e2e+<tech>@grins.test)
- Jobs reuse the tech's customer + property
- Appointments upserted by (staff_id, scheduled_date, time_window_start)
- All script-owned rows tagged ``[tech-companion-e2e]`` so the
  vitallik-cleanup step only deletes script-owned rows.

Usage:
    uv run python scripts/seed_tech_companion_appointments.py

Connects via ``DATABASE_URL`` (same as scripts/seed_resource_timeline_test_data.py).
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, time

import psycopg2
import psycopg2.extras

# =============================================================================
# Connection
# =============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var required", file=sys.stderr)
    sys.exit(1)

SSL_MODE = (
    "disable"
    if "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL
    else "require"
)

# Stable tag for script-owned rows; lets us safely delete vitallik's
# pre-existing tagged appointments without touching anything else.
TAG = "[tech-companion-e2e]"

# Per-tech fixture data: stable email → unique customer/property.
TECH_FIXTURES = {
    "vas": {
        "first_name": "Avery",
        "last_name": "Park",
        "phone": "+19525550101",
        "email": "e2e+vas@grins.test",
        "address": "12345 Eden Way",
        "city": "Eden Prairie",
        "state": "MN",
        "zip_code": "55344",
        "zone_count": 8,
        "system_type": "standard",
    },
    "steven": {
        "first_name": "Brooks",
        "last_name": "Lopez",
        "phone": "+19525550102",
        "email": "e2e+steven@grins.test",
        "address": "8901 Anderson Lakes Pkwy",
        "city": "Eden Prairie",
        "state": "MN",
        "zip_code": "55344",
        "zone_count": 6,
        "system_type": "standard",
    },
    "vitallik": {
        "first_name": "Casey",
        "last_name": "Reyes",
        "phone": "+19525550103",
        "email": "e2e+vitallik@grins.test",
        "address": "555 Mitchell Rd",
        "city": "Eden Prairie",
        "state": "MN",
        "zip_code": "55347",
        "zone_count": 10,
        "system_type": "lake_pump",
    },
}

# Per-tech appointment plan for today.
APPT_PLAN: dict[str, list[tuple[str, time, time]]] = {
    "vas": [
        ("completed", time(8, 0), time(9, 25)),
        ("in_progress", time(10, 30), time(12, 0)),
        ("scheduled", time(13, 0), time(14, 15)),
    ],
    "steven": [
        ("scheduled", time(9, 0), time(10, 30)),
        ("en_route", time(11, 0), time(12, 30)),
    ],
    "vitallik": [],
}


def main() -> None:
    today = date.today()
    conn = psycopg2.connect(DATABASE_URL, sslmode=SSL_MODE)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # ----- Resolve the three existing tech rows by username ------------------
    cur.execute(
        "SELECT id, username FROM staff "
        "WHERE username IN ('vas', 'steven', 'vitallik')"
    )
    rows = cur.fetchall()
    staff_by_username = {row["username"]: row["id"] for row in rows}
    missing = [u for u in TECH_FIXTURES if u not in staff_by_username]
    if missing:
        print(
            f"ERROR: missing tech staff rows: {missing}\n"
            "Run migration 20250626_100000_seed_demo_data.py "
            "to seed Vas / Steven / Vitallik with login enabled.",
            file=sys.stderr,
        )
        sys.exit(1)

    summary: dict[str, dict[str, int]] = {
        u: {"customer": 0, "property": 0, "job": 0, "appt": 0, "deleted": 0}
        for u in TECH_FIXTURES
    }

    # ----- Per-tech upsert ---------------------------------------------------
    for username, fix in TECH_FIXTURES.items():
        staff_id = staff_by_username[username]

        # Customer (upsert by email)
        cur.execute(
            "SELECT id FROM customers WHERE email = %s LIMIT 1",
            (fix["email"],),
        )
        row = cur.fetchone()
        if row:
            customer_id = row["id"]
        else:
            customer_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO customers (
                    id, first_name, last_name, phone, email, status,
                    sms_opt_in, email_opt_in, terms_accepted
                )
                VALUES (%s, %s, %s, %s, %s, 'active',
                        FALSE, FALSE, FALSE)
                """,
                (
                    str(customer_id),
                    fix["first_name"],
                    fix["last_name"],
                    fix["phone"],
                    fix["email"],
                ),
            )
            summary[username]["customer"] += 1

        # Property (upsert by customer_id — exactly one per customer)
        cur.execute(
            "SELECT id FROM properties WHERE customer_id = %s LIMIT 1",
            (str(customer_id),),
        )
        row = cur.fetchone()
        if row:
            property_id = row["id"]
            # Keep the address fresh in case the fixtures changed.
            cur.execute(
                """
                UPDATE properties SET
                    address = %s, city = %s, state = %s, zip_code = %s,
                    zone_count = %s, system_type = %s
                WHERE id = %s
                """,
                (
                    fix["address"],
                    fix["city"],
                    fix["state"],
                    fix["zip_code"],
                    fix["zone_count"],
                    fix["system_type"],
                    str(property_id),
                ),
            )
        else:
            property_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO properties (
                    id, customer_id, address, city, state, zip_code,
                    zone_count, system_type, property_type, is_primary
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'residential', TRUE)
                """,
                (
                    str(property_id),
                    str(customer_id),
                    fix["address"],
                    fix["city"],
                    fix["state"],
                    fix["zip_code"],
                    fix["zone_count"],
                    fix["system_type"],
                ),
            )
            summary[username]["property"] += 1

        # Job (one per tech, idempotent on customer_id + script tag in notes)
        cur.execute(
            "SELECT id FROM jobs WHERE customer_id = %s AND notes = %s LIMIT 1",
            (str(customer_id), TAG),
        )
        row = cur.fetchone()
        if row:
            job_id = row["id"]
        else:
            job_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO jobs (
                    id, customer_id, property_id,
                    job_type, category, status,
                    description, estimated_duration_minutes,
                    priority_level, notes
                )
                VALUES (%s, %s, %s,
                        'spring_opening', 'ready_to_schedule', 'scheduled',
                        'Spring system startup', 75,
                        0, %s)
                """,
                (
                    str(job_id),
                    str(customer_id),
                    str(property_id),
                    TAG,
                ),
            )
            summary[username]["job"] += 1

        # Appointments — clean script-owned ones for today, then re-insert.
        # Idempotent: every run leaves exactly the planned set.
        cur.execute(
            """
            DELETE FROM appointments
            WHERE staff_id = %s
              AND scheduled_date = %s
              AND notes = %s
            """,
            (str(staff_id), today, TAG),
        )
        deleted_count = cur.rowcount
        summary[username]["deleted"] += deleted_count

        for status, start, end in APPT_PLAN[username]:
            appt_id = uuid.uuid4()
            cur.execute(
                """
                INSERT INTO appointments (
                    id, job_id, staff_id, scheduled_date,
                    time_window_start, time_window_end,
                    status, notes
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(appt_id),
                    str(job_id),
                    str(staff_id),
                    today,
                    start,
                    end,
                    status,
                    TAG,
                ),
            )
            summary[username]["appt"] += 1

    conn.commit()
    cur.close()
    conn.close()

    # ----- Report ------------------------------------------------------------
    print(f"\nTech-companion seed complete for {today.isoformat()}")
    print(f"Tag: {TAG}")
    print()
    for username, stats in summary.items():
        print(
            f"  {username:9s}  +cust={stats['customer']}  +prop={stats['property']}  "
            f"+job={stats['job']}  -appt={stats['deleted']}  +appt={stats['appt']}"
        )

    print(
        "\nDev tech logins (seeded by migration 20250626_100000_seed_demo_data):\n"
        "  vas      / tech123   (3 appts today: completed / in_progress / scheduled)\n"
        "  steven   / tech123   (2 appts today: scheduled / en_route)\n"
        "  vitallik / tech123   (0 appts today — empty state)\n"
    )


if __name__ == "__main__":
    main()
