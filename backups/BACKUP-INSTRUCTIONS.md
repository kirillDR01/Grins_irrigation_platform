# Production Database Backup — Instructions

This document describes how to produce a point-in-time backup of the Railway production PostgreSQL database, matching the file-set convention used in this folder.

Backups in this folder are **read-only snapshots**. Producing one does not alter production in any way.

---

## File-set convention

Every backup is committed as three files sharing the same timestamp stem `production_backup_YYYYMMDD_HHMMSS`:

| Extension | Format | Purpose |
|-----------|--------|---------|
| `.dump`   | PostgreSQL custom format (`pg_dump -Fc`, gzip-compressed internally) | Canonical restore artifact — use with `pg_restore`. |
| `.sql`    | Plain SQL text (`pg_dump --format=plain`)                             | Human-readable schema + `COPY` data blocks. Editable with text tools. |
| `.xlsx`   | Excel workbook, one sheet per table                                   | Quick tabular inspection without a Postgres client. 50 sheets in the current schema. |

The timestamp stem **represents the target snapshot time in Central Time (America/Chicago)**, not the time pg_dump finished writing. Example: a backup whose filename contains `20260414_195000` reflects the production state near 2026-04-14 19:50:00 CDT.

---

## Prerequisites (one-time setup)

1. **PostgreSQL client tools (no server needed)**
   ```bash
   brew install libpq
   # pg_dump, pg_restore, psql will live at /opt/homebrew/opt/libpq/bin/
   export PATH="/opt/homebrew/opt/libpq/bin:$PATH"
   pg_dump --version   # verify — any 14.x+ works; 18.3+ is preferred
   ```

2. **Railway CLI authenticated**
   - `railway status` should show project `zealous-heart` and respond without prompting for login.

3. **Python 3.12+ with `uv` available** (for the xlsx export step)
   - The export script below uses `uv run --with` so no global installs are required.

4. **Docker** (for the end-to-end restore verification step)
   - Docker Desktop on macOS is sufficient. Used only to host a throwaway Postgres of the same major version as production.

---

## Retrieving the production connection URL

Never hard-code DB credentials — read them live from Railway each time:

```bash
railway variables list \
  --service Postgres \
  --environment production \
  --json \
| jq -r '.DATABASE_PUBLIC_URL'
```

Assign it to a shell variable that is **not** echoed into logs or committed:

```bash
export PROD_DB_URL="$(railway variables list --service Postgres --environment production --json | jq -r '.DATABASE_PUBLIC_URL')"
```

Alternatively, the Railway MCP server exposes `mcp__railway__list-variables` which returns the same map. The Railway MCP tools are read-only for variable retrieval and do not mutate the service.

> **Why `DATABASE_PUBLIC_URL` and not `DATABASE_URL`?** The `DATABASE_URL` hostname (`postgres.railway.internal`) only resolves inside Railway's VPC. The public URL proxies through `nozomi.proxy.rlwy.net` and is reachable from a developer workstation.

---

## Step 1 — `.dump` (canonical)

```bash
TS="$(TZ='America/Chicago' date +%Y%m%d_%H%M%S)"  # or hard-code the target snapshot time, e.g. TS=20260414_195000
pg_dump -Fc --no-owner --no-privileges "$PROD_DB_URL" \
  -f "backups/production_backup_${TS}.dump"
```

Flags:
- `-Fc` — custom (binary) format, the only format that `pg_restore` can parallel-restore and selectively replay.
- `--no-owner` / `--no-privileges` — strips ownership + GRANT/REVOKE lines. Restoring the dump into a different environment (staging, laptop, ephemeral Railway env) will not attempt to reassign ownership to the prod `postgres` role.

Verify the TOC without touching any database:

```bash
pg_restore --list "backups/production_backup_${TS}.dump" | head
pg_restore --list "backups/production_backup_${TS}.dump" | grep -c '^.*TABLE DATA'
# Should print 50 (matches the current schema). If it drops below that,
# something was excluded and you should investigate before relying on the dump.
```

---

## Step 2 — `.sql` (plain text)

```bash
pg_dump --no-owner --no-privileges "$PROD_DB_URL" \
  -f "backups/production_backup_${TS}.sql"
```

This is slower to restore than the `.dump` but is grep-friendly and survives binary-format incompatibility between client/server major versions.

---

## Step 3 — `.xlsx` (tabular view)

Create a temp export script:

```bash
cat > /tmp/export_xlsx_backup.py <<'PY'
"""Export every public.* table to an xlsx workbook, one sheet per table."""
import os
import sys
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from uuid import UUID

import psycopg
from openpyxl import Workbook

DB_URL = os.environ["PROD_DB_URL"]
OUT_PATH = sys.argv[1]

REFERENCE_TABLES = [
    "agreement_status_logs", "ai_audit_log", "ai_usage", "alembic_version",
    "appointments", "audit_log", "business_settings", "campaign_recipients",
    "campaign_responses", "campaigns", "communications",
    "consent_language_versions", "contract_renewal_proposals",
    "contract_renewal_proposed_jobs", "contract_templates",
    "customer_documents", "customer_merge_candidates", "customer_photos",
    "customers", "disclosure_records", "email_suppression_list",
    "estimate_follow_ups", "estimate_templates", "estimates", "expenses",
    "google_sheet_submissions", "invoices", "job_confirmation_responses",
    "job_status_history", "jobs", "lead_attachments", "leads",
    "marketing_budgets", "media_library", "properties", "reschedule_requests",
    "sales_calendar_events", "sales_entries", "schedule_clear_audit",
    "schedule_reassignments", "schedule_waitlist", "sent_messages",
    "service_agreement_tiers", "service_agreements", "service_offerings",
    "sms_consent_records", "staff", "staff_availability", "staff_breaks",
    "stripe_webhook_events",
]


def scalarize(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=None) if v.tzinfo else v
    if isinstance(v, time):
        return v.replace(tzinfo=None) if v.tzinfo else v
    if isinstance(v, (str, int, float, bool, date)):
        return v
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, timedelta):
        return str(v)
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, (bytes, bytearray, memoryview)):
        return f"<binary {len(bytes(v))}B>"
    if isinstance(v, (list, dict, tuple)):
        import json
        try:
            return json.dumps(v, default=str)
        except Exception:
            return str(v)
    return str(v)


def main():
    wb = Workbook(write_only=True)
    with psycopg.connect(DB_URL) as conn:
        conn.read_only = True
        with conn.cursor() as cur:
            for table in REFERENCE_TABLES:
                ws = wb.create_sheet(title=table)
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s "
                    "ORDER BY ordinal_position",
                    (table,),
                )
                cols = [r[0] for r in cur.fetchall()]
                if not cols:
                    ws.append(["<table not present>"])
                    continue
                ws.append(cols)
                cur.execute(f'SELECT * FROM "{table}"')
                n = 0
                for row in cur:
                    ws.append([scalarize(v) for v in row])
                    n += 1
                print(f"  {table}: {n} rows x {len(cols)} cols")
    wb.save(OUT_PATH)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
PY

uv run --with 'psycopg[binary]' --with openpyxl \
  python /tmp/export_xlsx_backup.py \
  "backups/production_backup_${TS}.xlsx"
```

Notes:
- The connection is opened with `conn.read_only = True` — the session cannot execute DDL or DML even if the script has a bug.
- The script uses a **fixed** reference table list. When the schema adds a table, update `REFERENCE_TABLES` in the next backup run or the new table will be silently omitted from the xlsx.
- `timedelta`, `Decimal`, `UUID`, list/dict are coerced to strings/floats because openpyxl rejects them. The `.dump` / `.sql` retain the native types — the xlsx is a *convenience view*, not a source of truth.

---

## Step 4 — End-to-end restore verification

The TOC produced by `pg_restore --list` only proves the file is *structurally* a valid pg_dump archive. It does not prove that the data blocks decompress, that constraints can be re-applied, or that schema objects rebuild. The only way to be 100% confident the dump captures everything is to actually restore it into a throwaway Postgres and diff every table and schema-object count against production.

**Do this every time** — before Step 5. If either diff is non-empty (and prod is not concurrently taking writes), the dump cannot be trusted.

### 4a. Pick the matching server version

Restore into a Postgres of the **same major version** as production to avoid catalog/SQL incompatibilities:

```bash
PROD_PG_MAJOR="$(psql "$PROD_DB_URL" -t -A -c "SHOW server_version;" | cut -d. -f1)"
echo "Prod major version: $PROD_PG_MAJOR"
```

### 4b. Spin up the throwaway target

```bash
docker rm -f grins-restore-test 2>/dev/null
docker run -d --name grins-restore-test \
  -e POSTGRES_PASSWORD=throwaway \
  -e POSTGRES_DB=restore_target \
  -p 55432:5432 \
  postgres:${PROD_PG_MAJOR}-alpine

# Wait for the daemon to accept connections
for i in $(seq 1 30); do
  sleep 1
  docker exec grins-restore-test pg_isready -U postgres >/dev/null 2>&1 && { echo "ready"; break; }
done

export TARGET_DB_URL='postgresql://postgres:throwaway@localhost:55432/restore_target'
```

### 4c. Replay the dump

```bash
pg_restore --clean --if-exists --no-owner --no-privileges --jobs 4 \
  --dbname "$TARGET_DB_URL" \
  "backups/production_backup_${TS}.dump"
```

A clean restore prints nothing. **Any error or warning here is a red flag** — investigate before continuing.

### 4d. Diff per-table row counts (prod vs restored)

```bash
ROW_QUERY="SELECT table_name,
  (xpath('/row/c/text()',
    query_to_xml('SELECT COUNT(*) AS c FROM \"' || table_name || '\"',
                 false, true, '')))[1]::text::bigint AS rows
  FROM information_schema.tables
  WHERE table_schema='public' AND table_type='BASE TABLE'
  ORDER BY table_name;"

psql "$PROD_DB_URL"   -t -A -F'|' -c "$ROW_QUERY" > /tmp/prod_counts.txt
psql "$TARGET_DB_URL" -t -A -F'|' -c "$ROW_QUERY" > /tmp/restored_counts.txt

diff /tmp/prod_counts.txt /tmp/restored_counts.txt && echo "ROW COUNTS: 100% MATCH"
```

If `diff` reports differences, **first re-query prod** to determine whether prod itself has taken writes since the dump (i.e. the diff is live drift, not a backup defect). If prod row counts are stable, the diff represents data the dump failed to capture and the backup must be regenerated.

### 4e. Diff schema-object counts

```bash
OBJ_QUERY="
SELECT 'tables',    COUNT(*) FROM information_schema.tables           WHERE table_schema='public' AND table_type='BASE TABLE'
UNION ALL SELECT 'columns',   COUNT(*) FROM information_schema.columns          WHERE table_schema='public'
UNION ALL SELECT 'indexes',   COUNT(*) FROM pg_indexes                          WHERE schemaname='public'
UNION ALL SELECT 'fks',       COUNT(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='FOREIGN KEY'
UNION ALL SELECT 'pks',       COUNT(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='PRIMARY KEY'
UNION ALL SELECT 'uniques',   COUNT(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='UNIQUE'
UNION ALL SELECT 'checks',    COUNT(*) FROM information_schema.table_constraints WHERE table_schema='public' AND constraint_type='CHECK'
UNION ALL SELECT 'sequences', COUNT(*) FROM information_schema.sequences         WHERE sequence_schema='public'
UNION ALL SELECT 'triggers',  COUNT(*) FROM information_schema.triggers          WHERE trigger_schema='public'
UNION ALL SELECT 'views',     COUNT(*) FROM information_schema.views             WHERE table_schema='public'
UNION ALL SELECT 'functions', COUNT(*) FROM information_schema.routines          WHERE routine_schema='public'
ORDER BY 1;"

psql "$PROD_DB_URL"   -t -A -F'|' -c "$OBJ_QUERY" > /tmp/prod_objects.txt
psql "$TARGET_DB_URL" -t -A -F'|' -c "$OBJ_QUERY" > /tmp/restored_objects.txt

diff /tmp/prod_objects.txt /tmp/restored_objects.txt && echo "SCHEMA OBJECTS: 100% MATCH"
```

### 4f. Tear down

```bash
docker rm -f grins-restore-test
rm -f /tmp/prod_counts.txt /tmp/restored_counts.txt /tmp/prod_objects.txt /tmp/restored_objects.txt
```

Only proceed to Step 5 once both diffs exit cleanly.

---

## Step 5 — Validation & commit

```bash
# checksums (lets anyone downstream confirm the file wasn't truncated in transfer)
shasum -a 256 backups/production_backup_${TS}.*

# sanity check: Alembic head recorded in the xlsx should match prod's current head
psql "$PROD_DB_URL" -c "SELECT version_num FROM alembic_version;" -t
```

Commit all three files together — the set is meaningful only if every file has the same stem.

```bash
git add backups/production_backup_${TS}.*
git commit -m "chore(backup): production snapshot ${TS} CT"
```

---

## Restoring from a backup (staging / emergency path)

> **Never restore into the production database.** Restore into a disposable target — a fresh Railway ephemeral environment, a local docker-compose Postgres, or a staging DB.

```bash
# Point at a throwaway target DB:
export TARGET_DB_URL='postgresql://user:pass@host:port/restore_target'

# Fast path — custom-format dump in parallel:
pg_restore --clean --if-exists --no-owner --no-privileges \
  --jobs 4 --dbname "$TARGET_DB_URL" \
  backups/production_backup_20260414_195000.dump

# Or the plain-SQL path (slower, text-readable, more portable):
psql "$TARGET_DB_URL" -f backups/production_backup_20260414_195000.sql
```

After restore:

```bash
psql "$TARGET_DB_URL" -c "SELECT version_num FROM alembic_version;"
# Should match the value recorded in the backup's alembic_version.xlsx sheet
```

---

## What each backup captures

- **Full schema:** every `public.*` table, view, sequence, function, check constraint, trigger, index, and FK relationship.
- **Full data:** every row in every table at the snapshot moment.
- **`alembic_version` row:** identifies the migration head at the time of backup — critical for deciding which migrations would have to run on a restored copy to bring it current.

What the backup does **not** capture:
- Railway environment variables (retrieve those separately via `railway variables list --json`).
- Redis state (webhook dedup keys, rate-limit counters). These are ephemeral by design.
- S3 bucket contents (`grins-platform-files`). Photos and customer documents live there, not in Postgres.
- Running process state / in-flight requests.

---

## Release history of backups in this folder

| Stem timestamp | Notes |
|----------------|-------|
| `20260326_220747` | Pre–CRM Changes Update 1 deploy |
| `20260409_110450` | Pre–April 9 dev→main (original baseline for the current deployment plan) |
| `20260414_065724` | Morning-of April 14, prior to Sprint 1-7 bughunt remediation merges |
| `20260414_195000` | Evening-of April 14 (7:50 PM CT) — latest snapshot before the dev→main cutover window |
| `20260415_055000` | Morning-of April 15 (5:50 AM CT) — schema head `20260414_100900`; first backup with the expanded 50-table reference list and the first to be **restore-verified end-to-end** (Step 4 — zero diff on row counts and schema objects against live prod). |
| `20260415_182500` | Evening-of April 15 (6:25 PM CT) — schema head `20260414_100900`; restore-verified end-to-end against postgres:17-alpine (Step 4 — zero diff on row counts and schema objects against live prod). |
| `20260416_060900` | Morning-of April 16 (6:09 AM CT) — schema head `20260414_100900`; restore-verified end-to-end against postgres:17-alpine (Step 4 — zero diff on row counts and schema objects against live prod). |

Add a row to this table every time you produce a new backup.
