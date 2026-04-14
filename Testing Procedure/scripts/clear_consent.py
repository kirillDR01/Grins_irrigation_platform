import asyncio, os, asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch(
        "SELECT id, phone_number, consent_type, consent_method, consent_given, created_at "
        "FROM sms_consent_records "
        "WHERE phone_number IN ('+19527373312','9527373312','19527373312') "
        "ORDER BY created_at DESC LIMIT 10"
    )
    print(f"Current rows: {len(rows)}")
    for r in rows:
        print(f"  {r['id']} | {r['phone_number']} | {r['consent_type']} | method={r['consent_method']} | given={r['consent_given']} | {r['created_at']}")
    deleted = await conn.execute(
        "DELETE FROM sms_consent_records "
        "WHERE phone_number IN ('+19527373312','9527373312','19527373312') "
        "  AND consent_method = 'text_stop'"
    )
    print(f"Deleted: {deleted}")
    updated = await conn.execute(
        "UPDATE customers SET sms_opt_in = TRUE "
        "WHERE phone IN ('+19527373312','9527373312','19527373312')"
    )
    print(f"Updated: {updated}")
    await conn.close()

asyncio.run(main())
