# Leads Page — "Network Error" (HTTP 500)

**Date Diagnosed:** 2026-02-28
**Date Resolved:** 2026-02-28
**Status:** RESOLVED
**Affected URL:** `https://grins-irrigation-platform.vercel.app/leads`
**Symptom:** The Leads page displays "Error — Network Error" with a Retry button
**Root Cause:** The `leads` table did not exist in the production PostgreSQL database — the migration had never been run
**Resolution:** Ran `uv run alembic upgrade head` against the production database using `DATABASE_PUBLIC_URL`

---

## Table of Contents

1. [Background — How This Application Works](#background--how-this-application-works)
2. [The Problem — What Was Happening](#the-problem--what-was-happening)
3. [Diagnosis — How We Found the Root Cause](#diagnosis--how-we-found-the-root-cause)
4. [Root Cause — Why It Was Broken](#root-cause--why-it-was-broken)
5. [Resolution — How We Fixed It](#resolution--how-we-fixed-it)
6. [Verification — How We Confirmed the Fix](#verification--how-we-confirmed-the-fix)
7. [If This Happens Again — Step-by-Step Playbook](#if-this-happens-again--step-by-step-playbook)
8. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
9. [Key Files Reference](#key-files-reference)
10. [Architecture Reference](#architecture-reference)
11. [Prevention](#prevention)
12. [Related Documentation](#related-documentation)

---

## Background — How This Application Works

The Grin's Irrigation Platform is a field service management application with three deployed components:

### The Three Components

| Component | Platform | URL | Purpose |
|-----------|----------|-----|---------|
| **Admin Dashboard (Frontend)** | Vercel | `https://grins-irrigation-platform.vercel.app` | React/Vite web app where admins manage customers, jobs, leads, staff, invoices |
| **Landing Page (Frontend)** | Vercel | `https://grins-irrigation.vercel.app` | Public-facing website where potential customers submit contact forms (leads) |
| **Backend API** | Railway | `https://grinsirrigationplatform-production.up.railway.app` | FastAPI server that handles all business logic and database operations |
| **Database** | Railway | Internal only (`postgres.railway.internal`) | PostgreSQL database storing all application data |

### How Data Flows

```
┌──────────────────────────────────┐
│  LANDING PAGE (Vercel)           │
│  grins-irrigation.vercel.app     │
│                                  │
│  Visitor fills out contact form  │
│  → POST /api/v1/leads            │──────┐
└──────────────────────────────────┘      │
                                          │ HTTPS
┌──────────────────────────────────┐      │
│  ADMIN DASHBOARD (Vercel)        │      │
│  grins-irrigation-platform       │      │
│            .vercel.app           │      │
│                                  │      │
│  Admin views leads, customers,   │      │
│  jobs, schedule, staff, invoices │      │
│  → GET /api/v1/leads             │──┐   │
│  → GET /api/v1/customers         │  │   │
│  → GET /api/v1/jobs              │  │   │
│  → etc.                          │  │   │
└──────────────────────────────────┘  │   │
                                      │   │
                                      ▼   ▼
                          ┌──────────────────────────────┐
                          │  BACKEND API (Railway)        │
                          │  grinsirrigationplatform-     │
                          │  production.up.railway.app    │
                          │                               │
                          │  FastAPI application          │
                          │  Handles all API requests     │
                          │  Queries the database         │
                          └──────────────┬────────────────┘
                                         │ Internal SQL
                                         ▼
                          ┌──────────────────────────────┐
                          │  POSTGRESQL DATABASE          │
                          │  (Railway - internal only)    │
                          │                               │
                          │  Tables: customers,           │
                          │  properties, jobs, staff,     │
                          │  appointments, invoices,      │
                          │  leads, etc.                  │
                          └──────────────────────────────┘
```

### How the Frontend Knows Where the Backend Is

The admin dashboard frontend is configured via an environment variable on Vercel:

| Vercel Environment Variable | Value |
|----------------------------|-------|
| `VITE_API_BASE_URL` | `https://grinsirrigationplatform-production.up.railway.app` |

This variable is read at build time in `frontend/src/core/config/index.ts`:

```typescript
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  apiVersion: 'v1',
} as const;
```

The frontend then constructs API URLs like:
- `https://grinsirrigationplatform-production.up.railway.app/api/v1/leads`
- `https://grinsirrigationplatform-production.up.railway.app/api/v1/customers`
- `https://grinsirrigationplatform-production.up.railway.app/api/v1/jobs`

If `VITE_API_BASE_URL` is not set on Vercel, the frontend falls back to `http://localhost:8000`, which would cause ALL pages to fail (not just Leads). This distinction is important for diagnosis.

### How the Backend Connects to the Database

The backend on Railway has an environment variable:

| Railway Environment Variable | Value |
|-----------------------------|-------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway auto-links this to the internal PostgreSQL address) |

This is the **internal** URL (`postgres.railway.internal:5432`) which is only reachable from within Railway's private network. The backend uses this to query the database.

### How Database Schema Changes Work (Migrations)

The application uses **Alembic** (a Python database migration tool) to manage database schema. Migration files live in:

```
src/grins_platform/migrations/versions/
```

Each migration file creates or modifies database tables. When you run `uv run alembic upgrade head`, Alembic executes all migration files that haven't been applied yet, in chronological order.

**Critical point:** Deploying new backend code to Railway does NOT automatically run migrations. If new code references a database table that doesn't exist yet, the backend will crash with a 500 error when that table is queried.

---

## The Problem — What Was Happening

### What the User Saw

1. Open `https://grins-irrigation-platform.vercel.app` in a browser
2. Log in with username `admin` and password `admin123`
3. The **Dashboard** loads successfully — showing job metrics, customer counts, recent activity
4. Click **Customers** in the sidebar — loads fine, shows 10 customers
5. Click **Jobs** in the sidebar — loads fine, shows 10 jobs
6. Click **Leads** in the sidebar — **"Error — Network Error"** with a Retry button
7. Click Retry — same error

Screenshot of the error:

```
┌─────────────────────────────────────────────────┐
│  Leads                                          │
│  Manage incoming leads from the website         │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  ⚠️  Error                                │  │
│  │  Network Error                            │  │
│  │                                           │  │
│  │  [Retry]                                  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### What Made This Confusing

The error message "Network Error" is misleading. It sounds like a connectivity or CORS issue, but:
- The frontend was correctly configured (`VITE_API_BASE_URL` was correct)
- The backend was running and healthy
- All other pages worked fine
- CORS was properly configured

The "Network Error" message is Axios's generic error for failed HTTP requests. It can mean CORS failure, network timeout, DNS failure, OR a server-side 500 error. The frontend error component doesn't distinguish between these.

---

## Diagnosis — How We Found the Root Cause

### Step 1 — Ruled Out Frontend Misconfiguration

**Question:** Is the frontend pointing to the right backend URL, or is it trying to call `localhost:8000`?

**How we checked:** Used a headless browser (agent-browser) to load the live Vercel app, log in, navigate to the Leads page, and intercept the network requests using the browser's `performance.getEntriesByType('resource')` API.

**What we found:** All API calls were going to the correct URL:

```
https://grinsirrigationplatform-production.up.railway.app/api/v1/auth/login       ← worked
https://grinsirrigationplatform-production.up.railway.app/api/v1/dashboard/metrics ← worked
https://grinsirrigationplatform-production.up.railway.app/api/v1/customers         ← worked
https://grinsirrigationplatform-production.up.railway.app/api/v1/jobs              ← worked
https://grinsirrigationplatform-production.up.railway.app/api/v1/leads             ← FAILED
```

**Conclusion:** The `VITE_API_BASE_URL` is correctly configured. The frontend is hitting the right backend. The problem is that only the `/leads` endpoint is failing while all others succeed. This means the issue is on the backend, not the frontend.

### Step 2 — Confirmed the Backend is Healthy

**Question:** Is the Railway backend actually running?

**How we checked:**

```bash
curl -s https://grinsirrigationplatform-production.up.railway.app/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": {
    "status": "healthy",
    "database": "connected"
  }
}
```

**Conclusion:** The backend is running, and it can connect to the database. The problem is specific to the leads feature, not a general backend failure.

### Step 3 — Tested Individual API Endpoints with Authentication

**Question:** Does the `/api/v1/leads` endpoint actually return a 500, or is the frontend misinterpreting something?

**How we checked:** Called the API directly from the terminal using `curl`, bypassing the frontend entirely.

First, we logged in to get a JWT token:

```bash
TOKEN=$(curl -s -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
```

Then tested each endpoint:

```bash
# Customers — works
curl -s https://grinsirrigationplatform-production.up.railway.app/api/v1/customers \
  -H "Authorization: Bearer $TOKEN"
# Result: {"items": [...], "total": 10, "page": 1, "page_size": 20} — OK

# Jobs — works
curl -s https://grinsirrigationplatform-production.up.railway.app/api/v1/jobs \
  -H "Authorization: Bearer $TOKEN"
# Result: {"items": [...], "total": 10, "page": 1, "page_size": 20} — OK

# Leads — FAILS
curl -s -w "\nHTTP Status: %{http_code}" \
  https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Authorization: Bearer $TOKEN"
# Result: Internal Server Error
# HTTP Status: 500
```

**Conclusion:** The `/api/v1/leads` endpoint returns HTTP 500 (Internal Server Error) from the backend. This confirms:
- It's NOT a CORS issue (CORS errors return before the server responds)
- It's NOT a frontend issue (curl has no frontend)
- It's NOT an authentication issue (the token works for other endpoints)
- It IS a backend-side error specific to the leads feature

### Step 4 — Identified the Missing Database Migration

**Question:** Why would only the leads endpoint fail when customers and jobs work fine?

**Reasoning:** The leads feature was the newest feature added to the platform. If the database migration that creates the `leads` table was never run on production, then:
- The backend code exists (routes, models, repositories) — it was deployed with the latest code push
- But the database table doesn't exist — because migrations aren't run automatically on deploy
- When the backend tries to `SELECT * FROM leads`, PostgreSQL throws an error
- FastAPI catches this and returns a 500

**How we verified:** Checked the migration files in the repository:

```
src/grins_platform/migrations/versions/
├── 20250613_140000_create_customers_table.py         ← existed in prod
├── 20250613_140100_create_properties_table.py         ← existed in prod
├── 20250613_140200_create_updated_at_trigger.py       ← existed in prod
├── 20250614_100000_create_service_offerings_table.py  ← existed in prod
├── 20250614_100100_create_jobs_table.py               ← existed in prod
├── 20250614_100200_create_job_status_history_table.py ← existed in prod
├── 20250614_100300_create_staff_table.py              ← existed in prod
├── 20250615_100000_create_appointments_table.py       ← existed in prod
├── 20250616_100000_create_staff_availability_table.py ← existed in prod
├── 20250617_100000_add_route_optimization_fields.py   ← existed in prod
├── 20250618_100000_add_conflict_resolution_fields.py  ← existed in prod
├── 20250619_100000_add_staff_reassignment.py          ← existed in prod
├── 20250620_100000_create_ai_audit_log_table.py       ← existed in prod
├── 20250620_100100_create_ai_usage_table.py           ← existed in prod
├── 20250620_100200_create_sent_messages_table.py      ← existed in prod
├── 20250621_100000_add_staff_authentication_columns.py← existed in prod
├── 20250622_100000_create_schedule_clear_audit_table.py← existed in prod
├── 20250623_100000_create_invoices_table.py           ← existed in prod
├── 20250624_100000_add_payment_collected_on_site.py   ← existed in prod
├── 20250625_100000_seed_default_admin_user.py         ← existed in prod
├── 20250626_100000_seed_demo_data.py                  ← existed in prod
├── 20250627_100000_seed_staff_availability.py         ← existed in prod (last one applied)
└── 20250628_100000_create_leads_table.py              ← NEVER RUN ON PRODUCTION
```

The production database was last migrated through `20250627_100000` (seed staff availability). The leads migration (`20250628_100000`) was added to the codebase after that and was never applied.

---

## Root Cause — Why It Was Broken

**The `leads` table did not exist in the production PostgreSQL database on Railway.**

Here's the chain of events that caused this:

1. The initial deployment set up the database and ran all migrations up to `20250627_100000`
2. The leads feature was developed and added to the codebase — including:
   - A new migration file: `20250628_100000_create_leads_table.py`
   - Backend code: model, repository, service, API routes
   - Frontend code: components, API client, hooks
3. The code was pushed to GitHub, which triggered:
   - Railway to redeploy the backend (automatically via GitHub integration)
   - Vercel to redeploy the frontend (automatically via GitHub integration)
4. But **nobody ran `alembic upgrade head`** against the production database
5. The backend now had code referencing a `leads` table that didn't exist
6. Any request to `/api/v1/leads` caused SQLAlchemy to throw a `ProgrammingError` (relation "leads" does not exist)
7. FastAPI caught this exception and returned HTTP 500 Internal Server Error
8. The frontend's Axios client received the 500 and displayed "Network Error"

**Why the health check didn't catch it:** The `/health` endpoint only checks that the database connection is alive (`SELECT 1`). It does NOT verify that all required tables exist. So the health check passed even though the leads table was missing.

---

## Resolution — How We Fixed It

### What We Did

Ran the pending Alembic migration against the production database from the local development machine.

### Step-by-Step

#### 1. Obtained the DATABASE_PUBLIC_URL

Railway provides two database URLs:

| Variable | Hostname | Accessible From |
|----------|----------|-----------------|
| `DATABASE_URL` | `postgres.railway.internal:5432` | Only from Railway services (internal network) |
| `DATABASE_PUBLIC_URL` | `nozomi.proxy.rlwy.net:36598` | From anywhere (your local machine, CI/CD, etc.) |

**You MUST use `DATABASE_PUBLIC_URL` when running migrations from your local machine.** The internal URL will fail with a DNS resolution error.

The `DATABASE_PUBLIC_URL` was retrieved from Railway Dashboard → PostgreSQL service → Variables tab:

```
postgresql://postgres:DfKjFivfoqYAUfXcHboRRxwOnSZLCCgk@nozomi.proxy.rlwy.net:36598/railway
```

#### 2. Ran the migration

From the project root directory:

```bash
cd /Users/kirillrakitin/Grins_irrigation_platform

DATABASE_URL="postgresql://postgres:DfKjFivfoqYAUfXcHboRRxwOnSZLCCgk@nozomi.proxy.rlwy.net:36598/railway" \
  uv run alembic upgrade head
```

**Important:** We passed `DATABASE_URL` as an inline environment variable (prefix to the command), not via `export`. This ensures it only applies to this one command and doesn't accidentally persist in the shell session. You can also use `export` — either approach works.

#### 3. Migration output

```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 20250627_100000 -> 20250628_100000, Create leads table.
```

This confirmed:
- Alembic connected to the production database successfully
- It detected one pending migration (`20250627_100000` → `20250628_100000`)
- It ran the `Create leads table` migration
- No errors occurred

#### 4. No backend redeploy was needed

The backend code already knew about the leads table — it just couldn't find it in the database. Once the table was created by the migration, the existing backend code started working immediately. No restart or redeployment was necessary.

---

## Verification — How We Confirmed the Fix

### Test 1 — API endpoint (curl)

```bash
TOKEN=$(curl -s -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

curl -s https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

**Result (after fix):**

```json
{
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20,
    "total_pages": 0
}
```

The endpoint now returns a proper JSON response with an empty leads list (no leads have been submitted yet) instead of a 500 error.

### Test 2 — Admin dashboard UI

1. Opened `https://grins-irrigation-platform.vercel.app`
2. Logged in with `admin` / `admin123`
3. Clicked **Leads** in the sidebar
4. The page now shows an empty leads table with "Manage incoming leads from the website" — no more "Network Error"

### Test 3 — Lead form submission (if needed)

To submit a test lead from the landing page:

```bash
curl -s -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -d '{
    "name": "Test Lead",
    "phone": "(612) 555-0000",
    "zip_code": "55424",
    "situation": "new_system",
    "website": ""
  }'
```

Expected: HTTP 201 with `{"success": true, "message": "Thank you! We'll be in touch within 24 hours.", "lead_id": "..."}`

---

## If This Happens Again — Step-by-Step Playbook

If you see "Network Error" on any page of the admin dashboard, follow this process:

### 1. Determine if the error is on one page or all pages

- **All pages fail** → Likely a frontend config issue (`VITE_API_BASE_URL` not set or wrong) or the backend is down
- **Only one page fails** → Likely a missing database migration or backend bug for that specific feature

### 2. Check if the backend is running

```bash
curl -s https://grinsirrigationplatform-production.up.railway.app/health
```

- If you get a response with `"status": "healthy"` → Backend is running
- If you get no response or a timeout → Backend is down, check Railway dashboard

### 3. Test the specific failing endpoint directly

```bash
# Login first
TOKEN=$(curl -s -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Test the failing endpoint (replace /leads with whatever page is broken)
curl -s -w "\nHTTP Status: %{http_code}" \
  https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Authorization: Bearer $TOKEN"
```

- **HTTP 200** with data → The backend works; the issue is in the frontend
- **HTTP 401** → Token issue; the auth system may be broken
- **HTTP 404** → The route doesn't exist in the backend; check if the code was deployed
- **HTTP 500** → Server-side error; likely a missing migration or code bug

### 4. If you get a 500, check for missing migrations

```bash
# Get the DATABASE_PUBLIC_URL from Railway (Dashboard → PostgreSQL service → Variables)
# Then check migration status:
DATABASE_URL="postgresql://postgres:PASSWORD@HOST.proxy.rlwy.net:PORT/railway" \
  uv run alembic current
```

Compare the output to the latest migration file in `src/grins_platform/migrations/versions/`. If the database is behind, run:

```bash
DATABASE_URL="postgresql://postgres:PASSWORD@HOST.proxy.rlwy.net:PORT/railway" \
  uv run alembic upgrade head
```

### 5. If migrations are current but you still get a 500

Check the Railway backend logs:
1. Go to Railway Dashboard → Backend service → Deployments tab
2. Click on the latest deployment
3. View logs for Python tracebacks
4. The traceback will tell you exactly which line of code is failing and why

---

## Common Mistakes to Avoid

| Mistake | Why It Fails | What to Do Instead |
|---------|--------------|-------------------|
| Using `DATABASE_URL` (internal) from Railway to run migrations locally | Internal URL uses `postgres.railway.internal` which is only resolvable within Railway's private network. Your local machine will get `nodename nor servname provided` DNS error. | Use `DATABASE_PUBLIC_URL` which uses `*.proxy.rlwy.net` — accessible from anywhere. |
| Using `railway run alembic upgrade head` | `railway run` injects Railway's internal environment variables (including the internal `DATABASE_URL`). Since your local machine can't reach the internal hostname, the migration fails. | Don't use `railway run`. Manually set `DATABASE_URL` to the public URL and run `uv run alembic upgrade head` directly. |
| Forgetting to set `DATABASE_URL` before running alembic | Alembic reads from the local `.env` file which has `DATABASE_URL=postgresql://localhost:5432/...` (your local dev database). The migration would run against your local database, not production. | Always explicitly set `DATABASE_URL` to the Railway public URL before running. |
| Assuming a code deploy runs migrations | Railway auto-deploys from GitHub on push, but this only rebuilds and restarts the backend. It does NOT run `alembic upgrade head` unless you've configured it in the start command. | Either run migrations manually after each deploy, or add `alembic upgrade head &&` to the Railway start command. |
| Not checking which database you're migrating | If you have multiple Railway projects or environments, you could accidentally migrate the wrong database. | Always verify the hostname in the URL matches your target environment. |

---

## Key Files Reference

### Backend (FastAPI on Railway)

| File | Purpose | Why It Matters |
|------|---------|---------------|
| `src/grins_platform/migrations/versions/20250628_100000_create_leads_table.py` | Alembic migration that creates the `leads` table with all columns and indexes | This is the file that was never run on production, causing the 500 error |
| `src/grins_platform/models/lead.py` | SQLAlchemy ORM model defining the Lead class and its database columns | Defines the schema that the migration creates |
| `src/grins_platform/api/v1/leads.py` | FastAPI router with all leads API endpoints (GET, POST, PATCH, DELETE) | This is where the 500 error originated — the GET /leads route tried to query a non-existent table |
| `src/grins_platform/repositories/lead_repository.py` | Database query layer — all SQL operations for leads | Contains `list_with_filters()` which builds the SQL query that failed |
| `src/grins_platform/services/lead_service.py` | Business logic layer — lead submission, status workflow, conversion to customer | Orchestrates between the API layer and the repository |
| `src/grins_platform/api/v1/router.py` (lines 79-83) | Main API router that includes the leads sub-router at `/api/v1/leads` | Registers the leads endpoints with the FastAPI application |
| `src/grins_platform/app.py` (lines 83-116) | CORS middleware configuration | Controls which frontend domains can call the API |
| `src/grins_platform/app.py` (lines 67-80) | Application factory and lifespan management | Creates the FastAPI app and initializes the database connection |
| `alembic.ini` | Alembic configuration file | Tells Alembic where to find migrations and how to connect to the database |

### Frontend (React/Vite on Vercel)

| File | Purpose | Why It Matters |
|------|---------|---------------|
| `frontend/src/core/config/index.ts` | Reads `VITE_API_BASE_URL` and constructs the API base URL | If this is misconfigured, ALL pages fail (not just Leads) |
| `frontend/src/core/api/client.ts` | Axios HTTP client with base URL, auth token injection, and error handling | Creates the axios instance that all API calls use; its error handler shows "Network Error" |
| `frontend/src/features/leads/api/leadApi.ts` | Leads-specific API methods: `list()`, `getById()`, `update()`, `convert()`, `delete()` | Constructs the specific HTTP requests for the leads feature |
| `frontend/src/features/leads/hooks/useLeads.ts` | React Query hooks: `useLeads()`, `useLead()` | Manages caching and loading states for leads data |
| `frontend/src/features/leads/components/LeadsList.tsx` | The leads list table component with filters, sorting, and pagination | This is the UI that shows the "Network Error" when the API call fails |
| `frontend/src/pages/Leads.tsx` | Page-level component that routes to LeadsList or LeadDetail | Top-level component for the `/leads` route |
| `frontend/.env` | Local development environment variables | Contains `VITE_API_BASE_URL=http://localhost:8000` for local dev; NOT used in production |

### Configuration

| File / Setting | Where | Value |
|---------------|-------|-------|
| `VITE_API_BASE_URL` | Vercel Environment Variables | `https://grinsirrigationplatform-production.up.railway.app` |
| `VITE_GOOGLE_MAPS_API_KEY` | Vercel Environment Variables | `AIzaSyAyB_Gbhgx7b2RHfCfprAuG_lP9Wsk3_TA` |
| `DATABASE_URL` | Railway Backend Variables | `${{Postgres.DATABASE_URL}}` (auto-linked, internal) |
| `CORS_ORIGINS` | Railway Backend Variables | `https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app` |
| `DATABASE_PUBLIC_URL` | Railway PostgreSQL Variables | `postgresql://postgres:PASSWORD@nozomi.proxy.rlwy.net:36598/railway` |

---

## Architecture Reference

### Before the Fix (Broken State)

```
User clicks "Leads" in sidebar
         │
         ▼
Frontend (Vercel) sends:
  GET https://grinsirrigationplatform-production.up.railway.app/api/v1/leads
  Header: Authorization: Bearer <jwt-token>
         │
         ▼
Backend (Railway) receives request
  → leads.py router handles GET /leads
  → Calls LeadRepository.list_with_filters()
  → SQLAlchemy generates: SELECT * FROM leads WHERE ...
         │
         ▼
PostgreSQL (Railway) executes query
  → ERROR: relation "leads" does not exist
         │
         ▼
Backend catches ProgrammingError
  → Returns HTTP 500 Internal Server Error
         │
         ▼
Frontend receives 500
  → Axios throws error
  → React Query catches error
  → LeadsList component displays "Error — Network Error"
```

### After the Fix (Working State)

```
User clicks "Leads" in sidebar
         │
         ▼
Frontend (Vercel) sends:
  GET https://grinsirrigationplatform-production.up.railway.app/api/v1/leads
  Header: Authorization: Bearer <jwt-token>
         │
         ▼
Backend (Railway) receives request
  → leads.py router handles GET /leads
  → Calls LeadRepository.list_with_filters()
  → SQLAlchemy generates: SELECT * FROM leads WHERE ...
         │
         ▼
PostgreSQL (Railway) executes query
  → Returns 0 rows (table exists but is empty)
         │
         ▼
Backend formats response
  → Returns HTTP 200 with {"items": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0}
         │
         ▼
Frontend receives 200
  → React Query caches response
  → LeadsList component displays empty table with "Manage incoming leads from the website"
```

---

## Prevention

To prevent this exact issue from recurring:

### Option 1 — Auto-migrate on deploy (Recommended)

Add `alembic upgrade head` to the Railway backend start command:

1. Go to Railway → Backend Service → **Settings** tab
2. Set start command to:
   ```bash
   alembic upgrade head && uvicorn grins_platform.main:app --host 0.0.0.0 --port $PORT
   ```

**Pros:** Every deploy automatically applies pending migrations. You'll never forget.
**Cons:** Adds a few seconds to startup. If a migration has a bug, the service won't start (but this is arguably a feature — it prevents deploying broken code).

### Option 2 — Add migration step to deployment checklist

Every time you push code that adds a new database table or modifies an existing one:

1. Push code to GitHub (triggers auto-deploy on Railway and Vercel)
2. **Immediately** run migrations:
   ```bash
   DATABASE_URL="postgresql://postgres:PASSWORD@nozomi.proxy.rlwy.net:36598/railway" \
     uv run alembic upgrade head
   ```
3. Verify the feature works on the live site

### Option 3 — Add a smarter health check

Enhance the `/health` endpoint to verify that all required tables exist, not just that the database connection works. This way, monitoring tools would catch missing tables before users do.

---

## Related Documentation

- [Deployment Step-by-Step Instructions.md](../../../Deployment%20Step-by-Step%20Instructions.md) — Full deployment guide including migration steps (Step 3)
- [Markdown/DEPLOYMENT_INSTRUCTIONS.md](../../../Markdown/DEPLOYMENT_INSTRUCTIONS.md) — Detailed deployment instructions with Railway CLI reference and the internal vs public DATABASE_URL distinction
- [Markdown/DEPLOYMENT_GUIDE.md](../../../Markdown/DEPLOYMENT_GUIDE.md) — Comprehensive deployment guide covering Railway, Vercel, and all external services
- [LeadErrorSolution.md](../../../LeadErrorSolution.md) — Separate issue: CORS fix for lead form submission from the landing page (different root cause)
- [docs/lead-form-cors-fix.md](../../lead-form-cors-fix.md) — Detailed CORS troubleshooting for the lead capture form (different root cause)

---

## Timeline

| Time | Action |
|------|--------|
| 2026-02-28 ~21:00 | Issue reported: Leads page shows "Network Error" |
| 2026-02-28 ~21:05 | Explored frontend code — found `VITE_API_BASE_URL` config and Axios client setup |
| 2026-02-28 ~21:05 | Explored backend code — found leads API routes, models, repositories, CORS config |
| 2026-02-28 ~21:08 | Tested backend health — confirmed healthy |
| 2026-02-28 ~21:08 | Suspected frontend misconfiguration initially |
| 2026-02-28 ~21:10 | Found deployment docs confirming backend URL: `grinsirrigationplatform-production.up.railway.app` |
| 2026-02-28 ~21:12 | Used agent-browser to load the live app and intercept network requests |
| 2026-02-28 ~21:13 | Confirmed `VITE_API_BASE_URL` is correctly set — all API calls go to the right backend |
| 2026-02-28 ~21:13 | Reproduced the "Network Error" on the Leads page via browser screenshot |
| 2026-02-28 ~21:14 | Tested `/api/v1/leads` directly with curl — got HTTP 500 Internal Server Error |
| 2026-02-28 ~21:14 | Tested `/api/v1/customers` and `/api/v1/jobs` — both returned HTTP 200 |
| 2026-02-28 ~21:15 | Identified `20250628_100000_create_leads_table.py` as the newest migration, likely never run |
| 2026-02-28 ~21:17 | Documented the issue in `docs/troubleshooting/Leads/leads-network-error-500.md` |
| 2026-02-28 ~21:19 | Obtained `DATABASE_PUBLIC_URL` from user |
| 2026-02-28 ~21:19 | Ran `uv run alembic upgrade head` — migration `20250628_100000` applied successfully |
| 2026-02-28 ~21:19 | Verified fix: `/api/v1/leads` now returns HTTP 200 with `{"items": [], "total": 0}` |
| 2026-02-28 ~21:20 | Issue resolved |
