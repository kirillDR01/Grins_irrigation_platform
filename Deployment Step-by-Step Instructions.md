# Grin's Irrigation Platform - Deployment Step-by-Step

A concise guide to deploy the full stack: PostgreSQL + FastAPI Backend on Railway, React Frontend on Vercel.

---

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐
│    FRONTEND     │  HTTPS  │    BACKEND      │   SQL   │   DATABASE   │
│    (Vercel)     │────────>│    (Railway)    │────────>│  (Railway)   │
│  React + Vite   │         │  FastAPI + uv   │         │  PostgreSQL  │
└─────────────────┘         └─────────────────┘         └──────────────┘
```

**Key Point:** Frontend NEVER connects directly to database. All data flows through the Backend API.

---

## Prerequisites

- [ ] GitHub account with repository access
- [ ] Vercel account (free tier works)
- [ ] Railway account (free $5 credit, then ~$5/month)

---

## Step 1: Create Railway Account

1. Go to https://railway.app
2. Click **"Login"** → **"Continue with GitHub"**
3. Authorize Railway to access your repositories
4. Complete account setup (verify email if prompted)

---

## Step 2: Deploy Backend to Railway

### 2.1 Create Project from GitHub

1. Go to https://railway.app/dashboard
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your `Grins_irrigation_platform` repository
4. Railway will start building (may fail initially - that's OK)

### 2.2 Add PostgreSQL Database

1. In your Railway project, click **"New"** (or **"+"** icon)
2. Select **"Database"** → **"Add PostgreSQL"**
3. Wait for database to provision (~30 seconds)

### 2.3 Link Database to Backend

1. Click on your backend service (e.g., `Grins_irrigation_platform`)
2. Go to **"Variables"** tab
3. Click **"New Variable"**
4. Name: `DATABASE_URL`
5. Click **"Add Reference"** → Select your PostgreSQL → Choose `DATABASE_URL`
6. Click **"Add"**

### 2.4 Generate Public Domain

1. Go to **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. **Save this URL!** Example: `https://grinsirrigationplatform-production.up.railway.app`

### 2.5 Redeploy

1. Go to **"Deployments"** tab
2. Click **"..."** on latest deployment → **"Redeploy"**
3. Wait for build to complete (2-5 minutes)

### 2.6 Verify Backend

```bash
curl https://YOUR-BACKEND-URL.up.railway.app/health
```

Expected: `{"status": "healthy", "service": "grins-platform-api", "version": "1.0.0"}`

---

## Step 3: Run Database Migrations

### Important: Use PUBLIC Database URL

Railway provides two database URLs:
- `DATABASE_URL` (internal) - Only works from within Railway
- `DATABASE_PUBLIC_URL` (external) - Works from your local machine

**You MUST use `DATABASE_PUBLIC_URL` when running migrations locally!**

### 3.1 Get Public Database URL

1. Go to Railway → Click on your **PostgreSQL** service
2. Go to **"Variables"** tab
3. Find **`DATABASE_PUBLIC_URL`** (NOT `DATABASE_URL`)
4. Copy the value (looks like: `postgresql://postgres:PASSWORD@HOST.proxy.rlwy.net:PORT/railway`)

### 3.2 Run Migrations

```bash
# Set the PUBLIC database URL
export DATABASE_URL="postgresql://postgres:YOUR-PASSWORD@YOUR-HOST.proxy.rlwy.net:PORT/railway"

# Run migrations (creates tables AND seeds demo data)
uv run alembic upgrade head
```

### 3.3 What Gets Created

The migrations automatically create:
- **All database tables** (customers, properties, staff, jobs, etc.)
- **Admin user** (`admin` / `admin123`)
- **Demo data** including:
  - 10 sample customers (with various flags: priority, slow payer, red flag)
  - 10 properties with GPS coordinates
  - 4 technicians (Vas, Steven, Viktor Sr, Vitallik)
  - 10 service offerings (seasonal, repair, installation)
  - 9 sample jobs in various statuses
  - **Staff availability for 30 days** (required for schedule generation)

### 3.4 Verify Migration Success

```bash
uv run alembic current
```

Expected output shows the latest migration version (e.g., `20250626_100000`).

---

## Step 4: Deploy Frontend to Vercel

### 4.1 Import Project

1. Go to https://vercel.com/dashboard
2. Click **"Add New..."** → **"Project"**
3. Select your `Grins_irrigation_platform` repository
4. Click **"Import"**

### 4.2 Configure Build Settings

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` |
| **Root Directory** | `frontend` (click "Edit" to change) |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

### 4.3 Add Environment Variables

Add these environment variables in Vercel:

| Name | Value |
|------|-------|
| `VITE_API_BASE_URL` | `https://YOUR-BACKEND-URL.up.railway.app` |
| `VITE_GOOGLE_MAPS_API_KEY` | `AIzaSyAyB_Gbhgx7b2RHfCfprAuG_lP9Wsk3_TA` |

**⚠️ Important Notes:**
- NO trailing slash on `VITE_API_BASE_URL`!
  - ✅ Correct: `https://grinsirrigationplatform-production.up.railway.app`
  - ❌ Wrong: `https://grinsirrigationplatform-production.up.railway.app/`
- The Google Maps API key is required for the map view in the schedule page

### 4.4 Deploy

1. Click **"Deploy"**
2. Wait for build (2-5 minutes)
3. **Save your frontend URL!** Example: `https://grins-irrigation-platform.vercel.app`

---

## Step 5: Configure CORS

The backend must allow requests from your frontend domain.

### 5.1 Add CORS_ORIGINS on Railway

1. Go to Railway → Your backend service → **"Variables"** tab
2. Click **"New Variable"**
3. Name: `CORS_ORIGINS`
4. Value: `https://YOUR-FRONTEND-URL.vercel.app`

**⚠️ Include `https://` prefix, NO trailing slash!**

Example: `https://grins-irrigation-platform.vercel.app`

### 5.2 Redeploy Backend

Railway auto-redeploys after adding variables. If not:
1. Go to **"Deployments"** tab
2. Click **"..."** → **"Redeploy"**

---

## Step 6: Test Everything

### 6.1 Test Backend Health

```bash
curl https://YOUR-BACKEND-URL.up.railway.app/health
```

### 6.2 Test API

```bash
curl https://YOUR-BACKEND-URL.up.railway.app/api/v1/customers
```

Expected: `{"items": [], "total": 0, "page": 1, "page_size": 20}`

### 6.3 Test Frontend

1. Open your Vercel URL in browser
2. Open Developer Tools (F12) → Console
3. Check for CORS errors (red text mentioning "CORS policy")

### 6.4 Test Login

1. Go to your frontend URL
2. Login with default credentials:
   - **Username:** `admin`
   - **Password:** `admin123`
3. You should see the dashboard with:
   - 10 customers in the Customers page
   - 9 jobs in the Jobs page
   - 5 staff members in the Staff page

### 6.5 Test End-to-End

1. Navigate to Customers page
2. Click "Add Customer"
3. Fill in test data and submit
4. Verify customer appears in list

---

## Quick Reference

### Your URLs

| Service | URL |
|---------|-----|
| Railway Backend | `https://________________________________.up.railway.app` |
| Vercel Frontend | `https://________________________________.vercel.app` |
| API Docs | `https://YOUR-BACKEND-URL.up.railway.app/docs` |

### Environment Variables

| Platform | Variable | Value |
|----------|----------|-------|
| Railway Backend | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (reference) |
| Railway Backend | `CORS_ORIGINS` | `https://your-frontend.vercel.app` |
| Vercel Frontend | `VITE_API_BASE_URL` | `https://your-backend.up.railway.app` |
| Vercel Frontend | `VITE_GOOGLE_MAPS_API_KEY` | `AIzaSyAyB_Gbhgx7b2RHfCfprAuG_lP9Wsk3_TA` |

### Login Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `vas` | `tech123` | Senior Technician |
| `steven` | `tech123` | Lead Technician |
| `vitallik` | `tech123` | Senior Technician |

*Note: Viktor Sr has no login (field-only technician)*

---

## Troubleshooting

### CORS Errors

```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

**Fix:**
1. Verify `CORS_ORIGINS` on Railway matches your exact Vercel URL
2. Include `https://` prefix
3. No trailing slash
4. Redeploy backend after changes

### Database Connection Error (Local Migrations)

```
socket.gaierror: [Errno 8] nodename nor servname provided
```

**Fix:** You're using the internal `DATABASE_URL`. Use `DATABASE_PUBLIC_URL` instead:
```bash
export DATABASE_URL="postgresql://postgres:PASSWORD@HOST.proxy.rlwy.net:PORT/railway"
```

### Backend 500 Error

**Fix:**
1. Check Railway logs: Service → Deployments → Click deployment → View logs
2. Verify `DATABASE_URL` is set correctly
3. Ensure migrations have been run

### Frontend Blank Page

**Fix:**
1. Verify Root Directory is set to `frontend` in Vercel
2. Check `VITE_API_BASE_URL` is correct
3. Redeploy frontend after changing env vars

---

## Optional: Additional Features

After basic deployment works, add these environment variables on Railway:

| Variable | Purpose |
|----------|---------|
| `GOOGLE_MAPS_API_KEY` | Map view in schedule |
| `OPENAI_API_KEY` | AI assistant features |
| `TWILIO_ACCOUNT_SID` | SMS notifications |
| `TWILIO_AUTH_TOKEN` | SMS notifications |

---

## Production Security Checklist

Before going live:

- [ ] Change default admin password
- [ ] Use strong JWT secret keys
- [ ] Enable HTTPS only (Railway/Vercel handle this automatically)
- [ ] Review CORS origins (only allow your production domain)
