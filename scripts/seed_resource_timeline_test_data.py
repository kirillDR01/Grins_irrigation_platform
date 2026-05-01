"""Seed visual-QA fixtures for the Schedule Resource Timeline view.

Inserts [TIMELINE-TEST]-prefixed customers/properties/jobs/appointments (and one
service agreement + a few RescheduleRequests + needs_review_reason values) into
the connected Postgres so a human can validate every icon/badge/status/job-type
combination on the new ResourceTimelineView.

Connects via DATABASE_URL env var (sslmode=require). Direct psycopg2 INSERTs —
the service layer is bypassed entirely so no SMS/email/webhook side effects fire.

Layout (week of Mon 2026-05-04 → Sun 2026-05-10):

  Mon  status × border showcase (7 statuses across techs)
  Tue  each icon alone (⭐/🔔/🔁/💎)
  Wed  icon combos incl. all-4 flags → max-3 cap
  Thu  8 job-type palettes
  Fri  lane overlap on Viktor + push utilization ≥85% (orange capacity bar)
  Sat  light day (low utilization, teal capacity bar)
  Sun  empty (whitespace)

Re-run safe: deletes prior [TIMELINE-TEST] rows before inserting fresh ones.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, time, timedelta

import psycopg2
import psycopg2.extras

# =============================================================================
# Connection
# =============================================================================

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var required", file=sys.stderr)
    sys.exit(1)

# Local dev DB does not require SSL; remote (railway proxy) does.
SSL_MODE = "disable" if "localhost" in DATABASE_URL or "127.0.0.1" in DATABASE_URL else "require"

# =============================================================================
# Constants
# =============================================================================

TAG = "[TIMELINE-TEST]"

# Targets the week of Mon 2026-05-04 → Sun 2026-05-10
WEEK_START = date(2026, 5, 4)
MON, TUE, WED, THU, FRI, SAT = (WEEK_START + timedelta(days=i) for i in range(6))

# Job types that match jobTypeColors.ts palette keys (case-insensitive).
JOB_TYPES = {
    "spring": "spring opening",       # emerald
    "fall": "fall closing",           # orange
    "maint": "maintenance",           # blue
    "backflow": "backflow test",      # teal
    "newbuild": "new build",          # purple
    "repair": "repair",               # rose
    "diagnostic": "diagnostic",       # amber
    "estimate": "estimate",           # indigo
}


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    conn = psycopg2.connect(DATABASE_URL, sslmode=SSL_MODE)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # ----- Look up existing staff (use the four real techs) -----------------
    cur.execute(
        "SELECT id, name FROM staff WHERE is_active = TRUE AND role IN ('tech', 'admin') "
        "AND name NOT LIKE 'webauthn-%' ORDER BY name"
    )
    staff_rows = cur.fetchall()
    staff_by_first = {row["name"].split()[0]: row["id"] for row in staff_rows}

    # Pick four techs we will scatter test data across.
    needed = ["Viktor", "Vasiliy", "Gennadiy", "Steve"]
    missing = [n for n in needed if n not in staff_by_first]
    if missing:
        print(f"ERROR: missing required staff: {missing}", file=sys.stderr)
        print(f"Found: {list(staff_by_first.keys())}", file=sys.stderr)
        sys.exit(1)

    viktor = staff_by_first["Viktor"]
    vas = staff_by_first["Vasiliy"]
    dad = staff_by_first["Gennadiy"]
    steven = staff_by_first["Steve"]
    techs = [viktor, vas, dad, steven]
    print(f"Using techs: Viktor={viktor}, Vasiliy={vas}, Gennadiy={dad}, Steve={steven}")

    # ----- Pick a service-agreement tier for the 💎 case --------------------
    cur.execute(
        "SELECT id FROM service_agreement_tiers WHERE slug = 'essential-residential' LIMIT 1"
    )
    row = cur.fetchone()
    if not row:
        print("ERROR: no essential-residential tier found", file=sys.stderr)
        sys.exit(1)
    tier_id = row["id"]

    # ----- Wipe prior test rows ---------------------------------------------
    print(f"Cleaning prior {TAG} rows ...")
    cur.execute(
        f"""
        DELETE FROM reschedule_requests WHERE appointment_id IN (
            SELECT a.id FROM appointments a
            JOIN jobs j ON a.job_id = j.id
            JOIN customers c ON j.customer_id = c.id
            WHERE c.first_name LIKE %s
        )
        """,
        (f"{TAG}%",),
    )
    cur.execute(
        f"""
        DELETE FROM appointments WHERE job_id IN (
            SELECT j.id FROM jobs j
            JOIN customers c ON j.customer_id = c.id
            WHERE c.first_name LIKE %s
        )
        """,
        (f"{TAG}%",),
    )
    cur.execute(
        "DELETE FROM jobs WHERE customer_id IN (SELECT id FROM customers WHERE first_name LIKE %s)",
        (f"{TAG}%",),
    )
    cur.execute(
        "DELETE FROM service_agreements WHERE customer_id IN (SELECT id FROM customers WHERE first_name LIKE %s)",
        (f"{TAG}%",),
    )
    cur.execute(
        "DELETE FROM properties WHERE customer_id IN (SELECT id FROM customers WHERE first_name LIKE %s)",
        (f"{TAG}%",),
    )
    cur.execute("DELETE FROM customers WHERE first_name LIKE %s", (f"{TAG}%",))

    # ----- Backfill staff_availability for the QA week ----------------------
    # Without this, ScheduleGenerationService falls back to a synthetic 480-min
    # shift; with it, /capacity reports realistic numbers (incl. lunch break).
    print("Cleaning prior availability rows for QA week ...")
    cur.execute(
        """
        DELETE FROM staff_availability
        WHERE staff_id IN (%s, %s, %s, %s)
          AND date BETWEEN %s AND %s
        """,
        (
            str(viktor),
            str(vas),
            str(dad),
            str(steven),
            WEEK_START,
            WEEK_START + timedelta(days=6),
        ),
    )
    print("Seeding staff_availability for Mon-Fri ...")
    for tech_id in (viktor, vas, dad, steven):
        for offset in range(5):  # Mon-Fri
            day = WEEK_START + timedelta(days=offset)
            cur.execute(
                """
                INSERT INTO staff_availability (
                    id, staff_id, date, start_time, end_time, is_available,
                    lunch_start, lunch_duration_minutes
                ) VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    str(tech_id),
                    day,
                    time(8, 0),
                    time(17, 0),
                    time(12, 0),
                    60,
                ),
            )

    # ----- Helper inserts ----------------------------------------------------
    counter = {"i": 0}

    def insert_customer(suffix: str, *, with_agreement: bool = False) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None]:
        """Insert customer + property; optionally a service_agreement. Returns (cust_id, prop_id, agreement_id)."""
        counter["i"] += 1
        cust_id = uuid.uuid4()
        prop_id = uuid.uuid4()
        agreement_id: uuid.UUID | None = None
        # Phone uses a sentinel so any code that filters real numbers still ignores us.
        # Pad index to keep the unique-constraint happy.
        phone = f"+1555000{counter['i']:04d}"
        cur.execute(
            """
            INSERT INTO customers (id, first_name, last_name, phone, status, sms_opt_in, email_opt_in, terms_accepted)
            VALUES (%s, %s, %s, %s, 'active', FALSE, FALSE, FALSE)
            """,
            (str(cust_id), TAG, suffix, phone),
        )
        cur.execute(
            """
            INSERT INTO properties (id, customer_id, address, city, state, zip_code, zone_count, system_type, property_type, is_primary)
            VALUES (%s, %s, %s, %s, 'MN', '55401', 8, 'standard', 'residential', TRUE)
            """,
            (str(prop_id), str(cust_id), f"{counter['i']} Test Ave", "Eden Prairie"),
        )
        if with_agreement:
            agreement_id = uuid.uuid4()
            agreement_number = f"TT-{counter['i']:05d}"
            cur.execute(
                """
                INSERT INTO service_agreements (
                    id, agreement_number, customer_id, tier_id, property_id,
                    status, annual_price, payment_status, notes
                )
                VALUES (%s, %s, %s, %s, %s, 'active', 175.00, 'current', %s)
                """,
                (
                    str(agreement_id),
                    agreement_number,
                    str(cust_id),
                    str(tier_id),
                    str(prop_id),
                    f"{TAG} prepaid demo",
                ),
            )
        return cust_id, prop_id, agreement_id

    def insert_job(
        cust_id: uuid.UUID,
        prop_id: uuid.UUID,
        *,
        job_type: str,
        priority_level: int = 0,
        agreement_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        job_id = uuid.uuid4()
        cur.execute(
            """
            INSERT INTO jobs (
                id, customer_id, property_id, service_agreement_id,
                job_type, category, status, priority_level
            )
            VALUES (%s, %s, %s, %s, %s, 'ready_to_schedule', 'scheduled', %s)
            """,
            (
                str(job_id),
                str(cust_id),
                str(prop_id),
                str(agreement_id) if agreement_id else None,
                job_type,
                priority_level,
            ),
        )
        return job_id

    def insert_appt(
        *,
        job_id: uuid.UUID,
        staff_id: uuid.UUID,
        scheduled_date: date,
        start: time,
        end: time,
        status: str,
        needs_review_reason: str | None = None,
    ) -> uuid.UUID:
        appt_id = uuid.uuid4()
        cur.execute(
            """
            INSERT INTO appointments (
                id, job_id, staff_id, scheduled_date, time_window_start, time_window_end,
                status, notes, needs_review_reason
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(appt_id),
                str(job_id),
                str(staff_id),
                scheduled_date,
                start,
                end,
                status,
                f"{TAG} fixture",
                needs_review_reason,
            ),
        )
        return appt_id

    def insert_reschedule_request(appt_id: uuid.UUID, job_id: uuid.UUID, cust_id: uuid.UUID) -> None:
        cur.execute(
            """
            INSERT INTO reschedule_requests (id, appointment_id, job_id, customer_id, status, raw_alternatives_text)
            VALUES (%s, %s, %s, %s, 'open', %s)
            """,
            (
                str(uuid.uuid4()),
                str(appt_id),
                str(job_id),
                str(cust_id),
                f"{TAG} please reschedule next week",
            ),
        )

    # =========================================================================
    # MON 5/4 — Status × border showcase (one appt per status, varied techs)
    # =========================================================================
    print("Seeding Mon 5/4 — status showcase ...")
    statuses = [
        ("confirmed", time(8, 0), time(9, 30)),
        ("en_route", time(9, 30), time(11, 0)),
        ("in_progress", time(11, 0), time(12, 30)),
        ("completed", time(12, 30), time(14, 0)),
        ("pending", time(14, 0), time(15, 30)),
        ("scheduled", time(15, 30), time(17, 0)),
        ("draft", time(17, 0), time(18, 30)),
    ]
    for idx, (status, s, e) in enumerate(statuses):
        tech = techs[idx % len(techs)]
        cust, prop, _ = insert_customer(f"Mon-{status}")
        job = insert_job(cust, prop, job_type=JOB_TYPES["maint"])
        insert_appt(job_id=job, staff_id=tech, scheduled_date=MON, start=s, end=e, status=status)

    # =========================================================================
    # TUE 5/5 — Each icon alone
    # =========================================================================
    print("Seeding Tue 5/5 — single-icon showcase ...")
    # ⭐ priority only
    cust, prop, _ = insert_customer("Tue-priority")
    job = insert_job(cust, prop, job_type=JOB_TYPES["spring"], priority_level=2)
    insert_appt(job_id=job, staff_id=viktor, scheduled_date=TUE, start=time(8, 0), end=time(9, 30), status="confirmed")

    # 🔔 needs-review only
    cust, prop, _ = insert_customer("Tue-no-reply")
    job = insert_job(cust, prop, job_type=JOB_TYPES["fall"])
    insert_appt(
        job_id=job, staff_id=vas, scheduled_date=TUE, start=time(9, 0), end=time(10, 30),
        status="scheduled", needs_review_reason="no_reply_3d",
    )

    # 🔁 reschedule only
    cust, prop, _ = insert_customer("Tue-reschedule")
    job = insert_job(cust, prop, job_type=JOB_TYPES["maint"])
    appt = insert_appt(job_id=job, staff_id=dad, scheduled_date=TUE, start=time(10, 0), end=time(11, 30), status="confirmed")
    insert_reschedule_request(appt, job, cust)

    # 💎 prepaid only
    cust, prop, agreement = insert_customer("Tue-prepaid", with_agreement=True)
    job = insert_job(cust, prop, job_type=JOB_TYPES["backflow"], agreement_id=agreement)
    insert_appt(job_id=job, staff_id=steven, scheduled_date=TUE, start=time(11, 0), end=time(12, 30), status="scheduled")

    # =========================================================================
    # WED 5/6 — Combinations (incl. all-4 flags → max-3 cap)
    # =========================================================================
    print("Seeding Wed 5/6 — icon combos ...")
    # All 4 flags → only top 3 render (priority + no-reply + reschedule, NOT prepaid)
    cust, prop, agreement = insert_customer("Wed-all4flags", with_agreement=True)
    job = insert_job(cust, prop, job_type=JOB_TYPES["repair"], priority_level=2, agreement_id=agreement)
    appt = insert_appt(
        job_id=job, staff_id=viktor, scheduled_date=WED, start=time(8, 0), end=time(9, 30),
        status="scheduled", needs_review_reason="no_reply_3d",
    )
    insert_reschedule_request(appt, job, cust)

    # priority + no-reply
    cust, prop, _ = insert_customer("Wed-pri-noreply")
    job = insert_job(cust, prop, job_type=JOB_TYPES["spring"], priority_level=1)
    insert_appt(
        job_id=job, staff_id=vas, scheduled_date=WED, start=time(9, 0), end=time(10, 30),
        status="scheduled", needs_review_reason="no_reply_3d",
    )

    # priority + prepaid
    cust, prop, agreement = insert_customer("Wed-pri-prepaid", with_agreement=True)
    job = insert_job(cust, prop, job_type=JOB_TYPES["maint"], priority_level=1, agreement_id=agreement)
    insert_appt(job_id=job, staff_id=dad, scheduled_date=WED, start=time(10, 0), end=time(11, 30), status="confirmed")

    # no-reply + prepaid
    cust, prop, agreement = insert_customer("Wed-noreply-prepaid", with_agreement=True)
    job = insert_job(cust, prop, job_type=JOB_TYPES["backflow"], agreement_id=agreement)
    insert_appt(
        job_id=job, staff_id=steven, scheduled_date=WED, start=time(11, 0), end=time(12, 30),
        status="scheduled", needs_review_reason="no_reply_5d",
    )

    # priority + reschedule
    cust, prop, _ = insert_customer("Wed-pri-resched")
    job = insert_job(cust, prop, job_type=JOB_TYPES["newbuild"], priority_level=2)
    appt = insert_appt(job_id=job, staff_id=viktor, scheduled_date=WED, start=time(13, 0), end=time(14, 30), status="confirmed")
    insert_reschedule_request(appt, job, cust)

    # reschedule + prepaid
    cust, prop, agreement = insert_customer("Wed-resched-prepaid", with_agreement=True)
    job = insert_job(cust, prop, job_type=JOB_TYPES["estimate"], agreement_id=agreement)
    appt = insert_appt(job_id=job, staff_id=vas, scheduled_date=WED, start=time(14, 0), end=time(15, 30), status="scheduled")
    insert_reschedule_request(appt, job, cust)

    # =========================================================================
    # THU 5/7 — All 8 job-type palettes
    # =========================================================================
    print("Seeding Thu 5/7 — job-type palettes ...")
    palette_demo = [
        ("spring", time(8, 0), time(9, 0)),
        ("fall", time(9, 0), time(10, 0)),
        ("maint", time(10, 0), time(11, 0)),
        ("backflow", time(11, 0), time(12, 0)),
        ("newbuild", time(12, 0), time(13, 0)),
        ("repair", time(13, 0), time(14, 0)),
        ("diagnostic", time(14, 0), time(15, 0)),
        ("estimate", time(15, 0), time(16, 0)),
    ]
    for idx, (key, s, e) in enumerate(palette_demo):
        tech = techs[idx % len(techs)]
        cust, prop, _ = insert_customer(f"Thu-{key}")
        job = insert_job(cust, prop, job_type=JOB_TYPES[key])
        insert_appt(job_id=job, staff_id=tech, scheduled_date=THU, start=s, end=e, status="confirmed")

    # =========================================================================
    # FRI 5/8 — Lane overlap on Viktor + heavy utilization
    # =========================================================================
    print("Seeding Fri 5/8 — overlap + heavy util ...")
    # 5 overlapping windows on Viktor to exercise lane-assignment in Day mode.
    overlaps = [
        (time(8, 0), time(11, 0)),
        (time(9, 0), time(11, 30)),
        (time(9, 30), time(10, 30)),
        (time(10, 0), time(13, 0)),
        (time(12, 0), time(14, 0)),
    ]
    for idx, (s, e) in enumerate(overlaps):
        cust, prop, _ = insert_customer(f"Fri-overlap-{idx}")
        job = insert_job(cust, prop, job_type=JOB_TYPES["maint"])
        insert_appt(job_id=job, staff_id=viktor, scheduled_date=FRI, start=s, end=e, status="confirmed")
    # Push other techs' utilization too
    for idx, (tech, s) in enumerate(zip([vas, dad, steven], [time(8, 0), time(9, 0), time(10, 0)])):
        cust, prop, _ = insert_customer(f"Fri-load-{idx}")
        job = insert_job(cust, prop, job_type=JOB_TYPES["repair"])
        insert_appt(
            job_id=job, staff_id=tech, scheduled_date=FRI,
            start=s, end=time(s.hour + 6, 0), status="confirmed",
        )

    # =========================================================================
    # SAT 5/9 — Light day (each tech: one 1-hr appt)
    # =========================================================================
    print("Seeding Sat 5/9 — light day ...")
    for idx, tech in enumerate(techs):
        cust, prop, _ = insert_customer(f"Sat-light-{idx}")
        job = insert_job(cust, prop, job_type=JOB_TYPES["estimate"])
        insert_appt(
            job_id=job, staff_id=tech, scheduled_date=SAT,
            start=time(9 + idx, 0), end=time(10 + idx, 0), status="scheduled",
        )

    # =========================================================================
    # SUN 5/10 — Empty (no inserts)
    # =========================================================================

    conn.commit()

    # ----- Verification ------------------------------------------------------
    cur.execute(
        """
        SELECT a.scheduled_date, count(*)
        FROM appointments a
        JOIN jobs j ON a.job_id = j.id
        JOIN customers c ON j.customer_id = c.id
        WHERE c.first_name = %s
          AND a.scheduled_date BETWEEN %s AND %s
        GROUP BY a.scheduled_date
        ORDER BY a.scheduled_date
        """,
        (TAG, WEEK_START, WEEK_START + timedelta(days=6)),
    )
    print("\nSeeded appointment counts per day:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} appts")

    cur.execute(
        "SELECT count(*) FROM customers WHERE first_name = %s",
        (TAG,),
    )
    print(f"Total {TAG} customers: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
