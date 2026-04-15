# 99 — Cleanup

Remove E2E-* records from dev so the next session starts clean.

```bash
cp "Testing Procedure/scripts/cleanup.py" /tmp/cleanup.py
B64=$(base64 < /tmp/cleanup.py | tr -d '\n')
railway ssh --service Grins-dev --environment dev \
  "python3 -c 'import base64,os; exec(base64.b64decode(\"$B64\"))'"
```

Output shows a `post` row per table. All should read `matching: 0` after
cleanup (except `customers`, which can stay non-zero if E2E-created
customers have residual jobs — that's harmless on dev).

## Manual cleanup for stubborn E2E customers

If a residual E2E customer blocks cleanup because it still has jobs
attached (force-convert paths create them):

```bash
# Drop into an interactive Railway Postgres shell
railway ssh --service Grins-dev --environment dev

# Inside:
python3 <<'PY'
import asyncio, os, asyncpg
async def main():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    # Identify orphan jobs tied to E2E customers
    rows = await conn.fetch("""
      SELECT j.id, j.status, c.first_name
      FROM jobs j JOIN customers c ON c.id = j.customer_id
      WHERE c.first_name LIKE 'E2E-%'
    """)
    for r in rows: print(r)
    await conn.close()
asyncio.run(main())
PY
```

Review the list and delete with care. Production data is not in this
environment, but always double-check `first_name LIKE 'E2E-%'` before
deleting.

## Restore opt-in state

If the E2E session ran STOP/START tests and CallRail may still have the
number blocked, wait ~10-30 minutes or contact CallRail support before
the next run. The probe in `00-preflight.md` tells you when it's clear
(success vs "recipient has opted out").
