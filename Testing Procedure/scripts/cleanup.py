"""E2E cleanup v2 — each phase in its own transaction so partial progress sticks.

Safe to re-run.
"""

import asyncio
import os
import asyncpg


async def run(conn: asyncpg.Connection, label: str, sql: str) -> None:
    try:
        result = await conn.execute(sql)
        print(f"  {label}: {result}")
    except Exception as e:  # noqa: BLE001
        print(f"  {label}: SKIPPED ({type(e).__name__}: {str(e)[:100]})")


async def main() -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    print("E2E cleanup starting...")

    # Phase 1 — tear down child tables first
    async with conn.transaction():
        await run(conn, "reschedule_requests",
                  "DELETE FROM reschedule_requests WHERE appointment_id IN "
                  "(SELECT id FROM appointments WHERE notes LIKE 'E2E-20260414-%')")
        await run(conn, "job_confirmation_responses",
                  "DELETE FROM job_confirmation_responses WHERE appointment_id IN "
                  "(SELECT id FROM appointments WHERE notes LIKE 'E2E-20260414-%')")
        await run(conn, "sent_messages (by appointment)",
                  "DELETE FROM sent_messages WHERE appointment_id IN "
                  "(SELECT id FROM appointments WHERE notes LIKE 'E2E-20260414-%')")
        await run(conn, "appointments",
                  "DELETE FROM appointments WHERE notes LIKE 'E2E-20260414-%'")
        await run(conn, "sales_entries (by lead)",
                  "DELETE FROM sales_entries WHERE lead_id IN "
                  "(SELECT id FROM leads WHERE name LIKE 'E2E-20260414-%')")
        await run(conn, "sms_consent_records (by lead)",
                  "DELETE FROM sms_consent_records WHERE lead_id IN "
                  "(SELECT id FROM leads WHERE name LIKE 'E2E-20260414-%')")
        await run(conn, "leads",
                  "DELETE FROM leads WHERE name LIKE 'E2E-20260414-%'")

    # Phase 2 — E2E-created jobs (force-convert spawned them)
    async with conn.transaction():
        await run(conn, "jobs (E2E-marked descriptions)",
                  """
                  DELETE FROM jobs
                  WHERE description LIKE '%verify property_id after H-5/H-6 fix%'
                     OR description LIKE '%E2E B3 — requires_estimate warning test%'
                     OR description LIKE '%E2E A2 — Winterization via E.164%'
                     OR description LIKE '%E2E A3 — messy phone format%'
                     OR description LIKE '%E2E B2b%'
                  """)

    # Phase 3 — properties for E2E net-new customers
    async with conn.transaction():
        await run(conn, "properties (E2E address patterns)",
                  """
                  DELETE FROM properties
                  WHERE address LIKE '%Test Property Rd%'
                     OR address LIKE '%Merge Test Ln%'
                     OR address LIKE '%Counter Test St%'
                     OR address LIKE '%Example Ln%'
                  """)

    # Phase 4 — E2E customers (only if no remaining FK references)
    async with conn.transaction():
        await run(conn, "customers (first_name LIKE 'E2E-%')",
                  "DELETE FROM customers WHERE first_name LIKE 'E2E-%'")

    # Final counts
    for table, where in [
        ("leads", "name LIKE 'E2E-20260414-%'"),
        ("appointments", "notes LIKE 'E2E-20260414-%'"),
        ("sales_entries", "lead_id IS NULL AND notes LIKE 'E2E%'"),
        ("customers", "first_name LIKE 'E2E-%'"),
        ("properties", "address LIKE '%Test Property Rd%' OR address LIKE '%Merge Test Ln%' OR address LIKE '%Counter Test St%' OR address LIKE '%Example Ln%'"),
    ]:
        n = await conn.fetchval(f"SELECT COUNT(*) FROM {table} WHERE {where}")
        print(f"post {table:18} matching: {n}")

    await conn.close()
    print("Cleanup done.")


asyncio.run(main())
