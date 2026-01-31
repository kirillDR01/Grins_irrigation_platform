# Grin's Irrigation Platform - Deployment Instructions

**Follow these steps exactly in order. Check off each step as you complete it.**

> **📚 For detailed architecture information and advanced configuration, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**

---

## Architecture Overview

Understanding the deployment architecture is crucial before starting:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DEPLOYMENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐ │
│   │                 │  HTTP   │                 │   SQL   │              │ │
│   │    FRONTEND     │────────>│    BACKEND      │────────>│   DATABASE   │ │
│   │    (Vercel)     │         │    (Railway)    │         │  (Railway)   │ │
│   │                 │<────────│                 │<────────│              │ │
│   │  React + Vite   │  JSON   │  FastAPI + uv   │  Data   │  PostgreSQL  │ │
│   │                 │         │                 │         │              │ │
│   └─────────────────┘         └─────────────────┘         └──────────────┘ │
│          │                            │                          │         │
│          │                            │                          │         │
│   vercel.app URL              railway.app URL            Internal only     │
│   (public)                    (public API)               (no direct access)│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Component | Platform | What It Does | Public Access |
|-----------|----------|--------------|---------------|
| **Frontend** | Vercel | React UI that users interact with | ✅ Yes - your main URL |
| **Backend** | Railway | FastAPI server handling all business logic | ✅ Yes - API endpoints |
| **Database** | Railway | PostgreSQL storing all data | ❌ No - only backend can access |

### Data Flow

1. **User** opens the frontend URL in their browser
2. **Frontend** makes HTTP requests to the backend API
3. **Backend** processes requests and queries the database
4. **Database** returns data to the backend
5. **Backend** sends JSON response to frontend
6. **Frontend** displays the data to the user

**Important:** The frontend NEVER connects directly to the database. All data flows through the backend API.

---

## Your Deployment URLs (Fill In As You Go)

Track your URLs here as you complete each step:

| Service | Your URL | Status |
|---------|----------|--------|
| **Railway Project** | `https://railway.app/project/_______________` | ⬜ |
| **Backend API** | `https://________________.up.railway.app` | ⬜ |
| **Frontend** | `https://________________.vercel.app` | ⬜ |
| **API Docs** | `https://________________.up.railway.app/docs` | ⬜ |

### Database URLs (Railway PostgreSQL)

| Variable | Value | Use Case |
|----------|-------|----------|
| **DATABASE_URL** | `postgres.railway.internal:5432` | Backend service (internal) |
| **DATABASE_PUBLIC_URL** | `________________.proxy.rlwy.net:_____` | Local migrations (external) |

---

## Prerequisites Checklist

Before starting, confirm you have:
- [ ] GitHub account with repository access
- [ ] Vercel account ✅ (you have this)
- [ ] Railway account (create below)
- [ ] Google Cloud account (for Maps API - can do later)

---

## Current State Assessment

Before proceeding, assess what's already deployed. Check each item:

### Railway (Backend Infrastructure)

| Component | Check | Status |
|-----------|-------|--------|
| Railway account exists | Go to https://railway.app/dashboard | ⬜ Not started / ✅ Done |
| Project created | See project in dashboard | ⬜ Not started / ✅ Done |
| PostgreSQL database | Database service visible in project | ⬜ Not started / ✅ Done |
| Backend service | Service named like `Grins_irrigation_platform` | ⬜ Not started / ✅ Done |
| DATABASE_URL linked | Backend Variables tab shows DATABASE_URL | ⬜ Not started / ✅ Done |
| Public domain generated | Backend Settings → Networking → Domain | ⬜ Not started / ✅ Done |
| Migrations run | Tables exist in database | ⬜ Not started / ✅ Done |

### Vercel (Frontend)

| Component | Check | Status |
|-----------|-------|--------|
| Vercel account exists | Go to https://vercel.com/dashboard | ⬜ Not started / ✅ Done |
| Project imported | See project in dashboard | ⬜ Not started / ✅ Done |
| Root directory set to `frontend` | Project Settings → General | ⬜ Not started / ✅ Done |
| VITE_API_BASE_URL set | Project Settings → Environment Variables | ⬜ Not started / ✅ Done |
| Deployment successful | Green checkmark on latest deployment | ⬜ Not started / ✅ Done |

### Connection (Frontend ↔ Backend)

| Component | Check | Status |
|-----------|-------|--------|
| CORS_ORIGINS configured | Railway Backend Variables includes Vercel URL | ⬜ Not started / ✅ Done |
| Frontend can reach backend | No CORS errors in browser console | ⬜ Not started / ✅ Done |
| API calls work | Can create/view customers | ⬜ Not started / ✅ Done |

**Skip to the appropriate step based on your current state.**

---

## Step 1: Create Railway Account

**Time: 3-5 minutes**

### 1.1 Go to Railway

Open this URL in your browser:
```
https://railway.app
```

### 1.2 Click "Login" (top right corner)

### 1.3 Choose Sign-Up Method

Railway offers these options:
- **GitHub** (Recommended - easiest for deployment)
- Email
- Google

**Choose "Continue with GitHub"** - this will make deploying your repo much easier.

### 1.4 Authorize Railway

When prompted:
1. Click "Authorize Railway"
2. This gives Railway permission to see your repositories
3. You can limit access to specific repos later if you prefer

### 1.5 Complete Account Setup

1. Choose a username (or accept the suggested one)
2. Accept the Terms of Service
3. You'll land on the Railway dashboard

### 1.6 Verify Your Account

Railway may ask you to:
- Verify your email address
- Add a payment method (required for production, but you get $5 free credit)

**Note:** Railway's Hobby plan is ~$5/month after the free trial. You can start without a payment method for testing.

### 1.7 Confirm Success

You should now see the Railway dashboard with:
- "New Project" button
- Empty project list
- Your username in the top right

---

**✅ CHECKPOINT: Railway account created**

---

## Step 2: Deploy Backend to Railway

**Time: 10-15 minutes**

### 2.1 Push Code to GitHub

First, make sure your latest code (including the fixed Dockerfile) is pushed to GitHub:

```bash
git add .
git commit -m "Fix Dockerfile for Railway deployment"
git push origin main
```

### 2.2 Create New Railway Project

1. Go to https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Find and select your `Grins_irrigation_platform` repository
5. Railway will start building automatically

### 2.3 Wait for Initial Build

Railway will:
1. Detect the Dockerfile
2. Build the container
3. Deploy it

**This first build may fail** because we haven't added the database yet. That's expected.

### 2.4 Check Build Logs

If the build fails:
1. Click on your service in Railway
2. Click **"Deployments"** tab
3. Click on the failed deployment to see logs
4. Look for error messages

**Common issues:**
- If you see "Cache mounts MUST be in the format..." → The Dockerfile fix above should resolve this
- If you see database connection errors → We'll fix this in Step 3

---

## Step 3: Add PostgreSQL Database

**Time: 2-3 minutes**

### 3.1 Add PostgreSQL to Your Project

1. In your Railway project dashboard
2. Click **"New"** button (or the **"+"** icon)
3. Select **"Database"**
4. Choose **"Add PostgreSQL"**

### 3.2 Wait for Database Provisioning

Railway will:
1. Create a PostgreSQL 15 instance
2. Automatically generate connection credentials
3. Make `DATABASE_URL` available to your services

### 3.3 Link Database to Your Service

Railway should automatically link the database. To verify:
1. Click on your backend service
2. Go to **"Variables"** tab
3. You should see `DATABASE_URL` listed (it may show as a reference like `${{Postgres.DATABASE_URL}}`)

If `DATABASE_URL` is not there:
1. Click **"New Variable"**
2. Name: `DATABASE_URL`
3. Value: Click the **"Add Reference"** button and select your PostgreSQL database

---

## Step 4: Configure Environment Variables & Generate Domain

**Time: 2-3 minutes**

### 4.1 Verify DATABASE_URL is Set

The only **required** variable is `DATABASE_URL`. Railway should have auto-linked it when you added PostgreSQL.

1. Go to Railway → Your Backend Service → **Variables** tab
2. Confirm you see `DATABASE_URL` (may show as `${{Postgres.DATABASE_URL}}`)

If it's not there:
1. Click **"New Variable"**
2. Name: `DATABASE_URL`
3. Click **"Add Reference"** → Select your PostgreSQL database

**That's it!** All other variables have sensible defaults and are optional.

### 4.2 Optional Variables (Add Later If Needed)

| Variable | Purpose | When Needed |
|----------|---------|-------------|
| `GOOGLE_MAPS_API_KEY` | Maps functionality | For schedule map view |
| `OPENAI_API_KEY` | AI features | For AI assistant |
| `TWILIO_ACCOUNT_SID` | SMS notifications | For customer notifications |
| `TWILIO_AUTH_TOKEN` | SMS notifications | For customer notifications |

### 4.3 Generate Public Domain

This is important - you need a public URL for your backend:

1. Go to your service's **"Settings"** tab
2. Scroll to **"Networking"** section
3. Click **"Generate Domain"**
4. Railway will create a URL like: `https://your-app-name.up.railway.app`

**⚠️ SAVE THIS URL - you'll need it for the frontend!**

### 4.4 Trigger Redeploy

Railway should auto-redeploy. If not:
1. Go to **"Deployments"** tab
2. Click the **"..."** menu on the latest deployment
3. Click **"Redeploy"**

### 4.5 Verify Backend is Running

1. Go to your service's **"Settings"** tab
2. Find the **"Domains"** section
3. Click **"Generate Domain"** to get a public URL
4. Your URL will look like: `https://your-app-name.up.railway.app`

Test it:
```bash
curl https://your-app-name.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "grins-platform-api", "version": "1.0.0"}
```

---

**✅ CHECKPOINT: Backend deployed and running**

**Save your Railway backend URL - you'll need it for the frontend:**
```
https://your-app-name.up.railway.app
```

---

## Step 5: Deploy Frontend to Vercel

**Time: 10-15 minutes**

### How Frontend Connects to Data

**Important:** The frontend NEVER connects directly to the database. The architecture is:

```
Frontend (Vercel) ──HTTP──> Backend API (Railway) ──SQL──> Database (PostgreSQL)
```

The frontend only needs to know the backend API URL. The backend handles all database operations.

### 5.1 Go to Vercel Dashboard

Open this URL in your browser:
```
https://vercel.com/dashboard
```

### 5.2 Import Your Project

1. Click **"Add New..."** → **"Project"**
2. Select **"Import Git Repository"**
3. Find and select your `Grins_irrigation_platform` repository
4. Click **"Import"**

### 5.3 Configure Project Settings

Vercel will auto-detect some settings, but you need to verify/adjust them:

| Setting | Value |
|---------|-------|
| **Framework Preset** | `Vite` |
| **Root Directory** | `frontend` (click "Edit" to change) |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |
| **Install Command** | `npm install` (or leave default) |

**Important:** The Root Directory must be set to `frontend` because the frontend code is in a subdirectory, not the repository root.

### 5.4 Add Environment Variables

Before deploying, add this environment variable:

| Name | Value |
|------|-------|
| `VITE_API_BASE_URL` | `https://your-railway-app.up.railway.app` |

**⚠️ Replace `your-railway-app` with your actual Railway backend URL from Step 4.3!**

This tells the frontend where to send API requests. The frontend will call endpoints like:
- `https://your-railway-app.up.railway.app/api/v1/customers`
- `https://your-railway-app.up.railway.app/api/v1/jobs`

**Optional:** Add Google Maps key if you want the map feature:
| Name | Value |
|------|-------|
| `VITE_GOOGLE_MAPS_API_KEY` | `AIzaSyAyB_Gbhgx7b2RHfCfprAuG_lP9Wsk3_TA` |

### 5.5 Deploy

1. Click **"Deploy"**
2. Wait for the build to complete (2-5 minutes)
3. Vercel will show you the deployment URL

### 5.6 Find Your Frontend URL

After deployment completes, find your URL:

**Option A: Deployment Success Screen**
- Vercel shows a "Congratulations!" page with your URL
- Click **"Visit"** to open your site

**Option B: From Dashboard**
1. Go to https://vercel.com/dashboard
2. Click on your project name
3. URL is shown at the top under **"Domains"**
4. Or click the **"Visit"** button

**Option C: Project Settings**
1. Click your project → **"Settings"** tab
2. Click **"Domains"** in left sidebar
3. See all assigned domains

Your URL will look like:
```
https://grins-irrigation-platform.vercel.app
```

**⚠️ SAVE THIS URL - you'll need it for Step 6 (CORS configuration)!**

---

**✅ CHECKPOINT: Frontend deployed to Vercel**

---

## Step 6: Connect Frontend to Backend (CORS Configuration)

**Time: 5 minutes**

### 6.1 Update Backend CORS Settings

Go back to Railway → Your Backend Service → **Variables** tab.

Add this environment variable:

| Variable | Value |
|----------|-------|
| `CORS_ORIGINS` | `https://your-frontend.vercel.app,https://grins-irrigation-platform.vercel.app` |

**Replace with your actual Vercel frontend URL(s).**

If you have multiple domains (e.g., preview deployments), separate them with commas.

### 6.2 Trigger Backend Redeploy

Railway should auto-redeploy after adding the variable. If not:
1. Go to **"Deployments"** tab
2. Click **"Redeploy"**

### 6.3 Verify CORS is Working

Open your frontend URL in a browser. Open Developer Tools (F12) → Console tab.

If you see CORS errors like:
```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

Double-check:
1. The `CORS_ORIGINS` variable has your exact frontend URL
2. No trailing slashes in the URL
3. Backend has been redeployed after adding the variable

---

**✅ CHECKPOINT: Frontend connected to Backend**

---

## Step 7: Run Database Migrations

**Time: 5-10 minutes**

Railway does NOT provide SSH or remote shell access to running containers in the traditional sense. Instead, use one of these methods to run migrations:

### ⚠️ IMPORTANT: Internal vs Public DATABASE_URL

Railway provides TWO database URLs:

| Variable | Hostname | Accessible From |
|----------|----------|-----------------|
| `DATABASE_URL` | `postgres.railway.internal:5432` | **Only from Railway services** |
| `DATABASE_PUBLIC_URL` | `*.proxy.rlwy.net:XXXXX` | **From anywhere (local machine, etc.)** |

**When running migrations from your local machine, you MUST use `DATABASE_PUBLIC_URL`!**

The internal URL (`postgres.railway.internal`) will NOT work from outside Railway's network.

### 7.1 Option A: Run Migrations with Public DATABASE_URL (Recommended)

**Step 1: Get your DATABASE_PUBLIC_URL from Railway**

Using Railway CLI:
```bash
# Install Railway CLI if not already installed
brew install railway  # macOS

# Login and link to your project
railway login
railway link

# View all variables - look for DATABASE_PUBLIC_URL
railway variables
```

Or from Railway Dashboard:
1. Go to Railway → Your PostgreSQL service
2. Click **"Variables"** tab
3. Find **`DATABASE_PUBLIC_URL`** (NOT `DATABASE_URL`)
4. Copy the value (looks like: `postgresql://postgres:password@*.proxy.rlwy.net:XXXXX/railway`)

**Step 2: Run migrations locally**
```bash
# Set the PUBLIC DATABASE_URL (replace with your actual URL)
export DATABASE_URL="postgresql://postgres:your-password@your-host.proxy.rlwy.net:PORT/railway"

# Run migrations
uv run alembic upgrade head
```

**Example output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_customers, Create customers table.
INFO  [alembic.runtime.migration] Running upgrade 001_customers -> 002_properties, Create properties table.
... (more migrations)
```

### 7.2 Option B: Why `railway run` Doesn't Work for Migrations

You might think `railway run uv run alembic upgrade head` would work, but it **doesn't** because:

1. `railway run` injects Railway's environment variables
2. Railway provides the **internal** `DATABASE_URL` (`postgres.railway.internal`)
3. This internal hostname is only resolvable from within Railway's network
4. Your local machine cannot reach `postgres.railway.internal`

**Error you'll see:**
```
socket.gaierror: [Errno 8] nodename nor servname provided, or not known
```

**Solution:** Always use `DATABASE_PUBLIC_URL` when running from your local machine.

### 7.3 Option C: Add Migrations to Startup Command (Automatic)

For automatic migrations on every deploy, modify your Railway start command:

1. Go to Railway → Your Backend Service → **Settings** tab
2. Find **"Start Command"** (or **"Custom Start Command"**)
3. Set it to:
```bash
alembic upgrade head && uvicorn grins_platform.main:app --host 0.0.0.0 --port $PORT
```

**Pros:** Migrations run automatically on every deploy
**Cons:** Adds startup time; if migration fails, service won't start

**Note:** This works because the backend service runs INSIDE Railway's network, so it can use the internal `DATABASE_URL`.

### 7.4 Verify Migrations

After running migrations, verify tables were created:

**Option A: Check Alembic Version**
```bash
# Using the PUBLIC DATABASE_URL
export DATABASE_URL="postgresql://postgres:your-password@your-host.proxy.rlwy.net:PORT/railway"
uv run alembic current

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# 20250624_100000 (head)
```

**Option B: Via Railway Data Tab**
1. Go to Railway → PostgreSQL service
2. Click **"Data"** tab
3. You should see tables like:
   - `customers`
   - `properties`
   - `jobs`
   - `staff`
   - `appointments`
   - `service_offerings`
   - `invoices`
   - `alembic_version`

**Option C: Via psql (if installed)**
```bash
# Using the PUBLIC DATABASE_URL
psql "postgresql://postgres:your-password@your-host.proxy.rlwy.net:PORT/railway" -c "\\dt"
```

---

**✅ CHECKPOINT: Database migrations complete**

---

## Step 8: Verify Full Deployment

**Time: 5-10 minutes**

### 8.1 Test Backend Health

```bash
curl https://your-railway-app.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "grins-platform-api", "version": "1.0.0"}
```

### 8.2 Test API Endpoints

```bash
# Test customers endpoint
curl https://your-railway-app.up.railway.app/api/v1/customers

# Expected: {"items": [], "total": 0, "page": 1, "page_size": 20}
```

### 8.3 Test Frontend

1. Open your Vercel frontend URL in a browser
2. You should see the Grin's Irrigation Platform dashboard
3. Navigate to different pages (Customers, Jobs, Schedule)
4. Verify no console errors related to API calls

### 8.4 Test Frontend-Backend Connection

1. Go to the Customers page
2. Click "Add Customer"
3. Fill in test data and submit
4. Verify the customer appears in the list

### 8.5 Final Checklist

- [ ] Backend health endpoint returns healthy
- [ ] Frontend loads without errors
- [ ] Frontend can fetch data from backend (no CORS errors)
- [ ] Can create a new customer
- [ ] Can view the customer list
- [ ] Schedule page loads

---

## 🎉 Deployment Complete!

Your Grin's Irrigation Platform is now live:

| Service | URL |
|---------|-----|
| **Frontend** | `https://your-frontend.vercel.app` |
| **Backend API** | `https://your-railway-app.up.railway.app` |
| **API Docs** | `https://your-railway-app.up.railway.app/docs` |

---

## Troubleshooting

### Backend Issues

**Problem: Health check fails with database error**
- Verify PostgreSQL is added in Railway
- Check `DATABASE_URL` variable is set correctly
- Ensure database is linked to your service

**Problem: Build fails with Dockerfile error**
- Ensure you're using the simplified Dockerfile (no BuildKit cache mounts)
- Check Railway build logs for specific errors

**Problem: 500 Internal Server Error**
- Check Railway logs for Python exceptions
- Verify all required environment variables are set
- Run migrations if database tables are missing

### Frontend Issues

**Problem: Blank page or build error**
- Verify Root Directory is set to `frontend`
- Check that `VITE_API_BASE_URL` is set correctly
- Review Vercel build logs

**Problem: CORS errors in browser console**
- Add your Vercel URL to `CORS_ORIGINS` in Railway
- Redeploy backend after adding the variable
- Ensure no trailing slashes in URLs

**Problem: API calls fail with network error**
- Verify `VITE_API_BASE_URL` points to your Railway backend
- Check that backend is running (test health endpoint)
- Ensure HTTPS is used for both frontend and backend

### Database Issues

**Problem: Tables don't exist**
- Run migrations: `uv run alembic upgrade head`
- Check migration logs for errors

**Problem: Connection refused / "nodename nor servname provided"**
- **Most common cause:** Using the internal `DATABASE_URL` instead of `DATABASE_PUBLIC_URL`
- The internal URL (`postgres.railway.internal`) only works from within Railway
- Use `railway variables` to find `DATABASE_PUBLIC_URL` (looks like `*.proxy.rlwy.net:PORT`)
- Export the PUBLIC URL: `export DATABASE_URL="postgresql://...@*.proxy.rlwy.net:PORT/railway"`

**Problem: `railway run` fails with database connection error**
- `railway run` injects the internal `DATABASE_URL` which doesn't work from your local machine
- Don't use `railway run` for database operations
- Instead, manually export `DATABASE_PUBLIC_URL` and run commands directly

---

## Quick Reference

| Service | URL | Purpose |
|---------|-----|---------|
| Railway Dashboard | https://railway.app/dashboard | Backend management |
| Vercel Dashboard | https://vercel.com/dashboard | Frontend management |
| Backend API | Your Railway URL | API endpoints |
| Frontend App | Your Vercel URL | User interface |
| API Documentation | Your Railway URL + `/docs` | Swagger UI |

---

## Next Steps (Optional)

After basic deployment is working:

1. **Custom Domain**: Add a custom domain in Vercel and Railway
2. **Google Maps**: Get your own Google Maps API key for production
3. **AI Features**: Add `OPENAI_API_KEY` for AI assistant
4. **SMS Notifications**: Add Twilio credentials for customer notifications
5. **Monitoring**: Set up Railway alerts for downtime

---

## Railway CLI Quick Reference

The Railway CLI is useful for managing your deployment:

```bash
# Installation
brew install railway          # macOS
npm install -g @railway/cli   # npm
curl -fsSL https://railway.app/install.sh | sh  # curl

# Authentication
railway login                 # Login (opens browser)
railway logout                # Logout

# Project Management
railway link                  # Link current directory to a Railway project
railway status                # Show current project/environment status

# View Environment Variables
railway variables             # List ALL environment variables
                              # Look for DATABASE_PUBLIC_URL for external access!

# Logs and Monitoring
railway logs                  # View service logs
railway logs -f               # Follow logs in real-time

# Environment Variables
railway variables set KEY=value  # Set an environment variable

# Deployments
railway up                    # Deploy current directory
railway redeploy              # Trigger a redeploy
```

### ⚠️ Important Note About `railway run`

`railway run <command>` executes commands **locally** but injects Railway's environment variables. However, Railway provides the **internal** `DATABASE_URL` which uses `postgres.railway.internal` - this hostname is **NOT accessible from your local machine**.

**For database operations from your local machine, always use `DATABASE_PUBLIC_URL`:**
```bash
# View all variables to find DATABASE_PUBLIC_URL
railway variables

# Then use it directly
export DATABASE_URL="postgresql://postgres:password@*.proxy.rlwy.net:PORT/railway"
uv run alembic upgrade head
```


---

## Complete Deployment Guide: Railway Backend + Vercel Frontend

This section provides a streamlined step-by-step guide for completing the deployment when you already have partial infrastructure in place.

### Current State Assessment

| Component | Status | Details |
|-----------|--------|---------|
| PostgreSQL Database | ✅ Deployed | On Railway, migrations complete |
| FastAPI Backend Service | ⚠️ Exists but needs config | Missing DATABASE_URL, no public domain |
| Vercel Frontend | ✅ Deployed | But pointing to localhost |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              VERCEL                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Frontend (React/Vite)                                           │   │
│  │  URL: https://grins-irrigation-platform.vercel.app               │   │
│  │  Env: VITE_API_BASE_URL = https://xxx.up.railway.app             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS API Calls
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              RAILWAY                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Backend Service (FastAPI)                                       │   │
│  │  URL: https://xxx.up.railway.app                                 │   │
│  │  Env: DATABASE_URL, CORS_ORIGINS                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    │ Internal Connection                 │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL Database                                             │   │
│  │  Internal: postgres.railway.internal:5432                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### STEP 1: Configure Backend Service on Railway (5 minutes)

#### 1.1 Open Railway Dashboard

Go to: https://railway.app/dashboard

Click on your project: `zealous-heart`

#### 1.2 Select the Backend Service

You should see two services:
- **Postgres** (database) ✅
- **Grins_irrigation_platform** (backend) ← Click this one

#### 1.3 Add DATABASE_URL Variable

1. Click the **"Variables"** tab
2. Click **"New Variable"**
3. For the Name, type: `DATABASE_URL`
4. Click **"Add Reference"** button (or the link icon)
5. Select your Postgres database
6. Choose `DATABASE_URL` from the dropdown
7. Click **"Add"**

This links your backend to the database using the internal URL (which works because both are on Railway).

#### 1.4 Generate a Public Domain

1. Click the **"Settings"** tab
2. Scroll down to **"Networking"** section
3. Click **"Generate Domain"**
4. Railway will create a URL like: `https://grins-irrigation-platform-production.up.railway.app`

**⚠️ COPY THIS URL - you'll need it for the next steps!**

Your backend URL: `https://_____________________________.up.railway.app`

#### 1.5 Trigger a Redeploy

1. Click the **"Deployments"** tab
2. Click the **"..."** menu on the latest deployment
3. Click **"Redeploy"**
4. Wait for the build to complete (2-5 minutes)

#### 1.6 Verify Backend is Running

Open a terminal and run:
```bash
curl https://YOUR-BACKEND-URL.up.railway.app/health
```

Expected response:
```json
{"status": "healthy", "service": "grins-platform-api", "version": "1.0.0"}
```

If you get this response, your backend is running! 🎉

---

### STEP 2: Configure CORS on Backend (2 minutes)

CORS (Cross-Origin Resource Sharing) allows your Vercel frontend to make API calls to your Railway backend.

#### 2.1 Get Your Vercel Frontend URL

Your Vercel frontend URL is likely one of:
- `https://grins-irrigation-platform.vercel.app`
- `https://grins-irrigation-platform-YOUR-USERNAME.vercel.app`

Check your Vercel dashboard to confirm the exact URL.

#### 2.2 Add CORS_ORIGINS Variable on Railway

1. Go to Railway → Grins_irrigation_platform service → **Variables** tab
2. Click **"New Variable"**
3. Name: `CORS_ORIGINS`
4. Value: `https://YOUR-VERCEL-URL.vercel.app`
   - Example: `https://grins-irrigation-platform.vercel.app`
   - If you have multiple URLs (like preview deployments), separate with commas:
     `https://grins-irrigation-platform.vercel.app,https://grins-irrigation-platform-git-main-YOUR-USERNAME.vercel.app`
5. Click **"Add"**

Railway will automatically redeploy after adding the variable.

---

### STEP 3: Configure Frontend on Vercel (5 minutes)

#### 3.1 Open Vercel Dashboard

Go to: https://vercel.com/dashboard

Click on your project: `grins-irrigation-platform` (or similar name)

#### 3.2 Update Environment Variables

1. Click **"Settings"** tab
2. Click **"Environment Variables"** in the left sidebar
3. Find `VITE_API_BASE_URL` (or add it if it doesn't exist)
4. Set the value to your Railway backend URL:
   ```
   https://YOUR-BACKEND-URL.up.railway.app
   ```

**⚠️ NO trailing slash!**
- ✅ Correct: `https://grins-irrigation-platform-production.up.railway.app`
- ❌ Wrong: `https://grins-irrigation-platform-production.up.railway.app/`

5. Make sure it's enabled for **Production** (and optionally Preview/Development)
6. Click **"Save"**

#### 3.3 Redeploy Frontend

After changing environment variables, you need to redeploy:

1. Go to the **"Deployments"** tab
2. Find the latest deployment
3. Click the **"..."** menu
4. Click **"Redeploy"**
5. In the popup, check **"Use existing Build Cache"** is **OFF** (unchecked)
6. Click **"Redeploy"**
7. Wait for the build to complete (2-3 minutes)

---

### STEP 4: Test the Full System (5 minutes)

#### 4.1 Test Backend Health

```bash
curl https://YOUR-BACKEND-URL.up.railway.app/health
```

Expected: `{"status": "healthy", ...}`

#### 4.2 Test Backend API

```bash
curl https://YOUR-BACKEND-URL.up.railway.app/api/v1/customers
```

Expected: `{"items": [], "total": 0, "page": 1, "page_size": 20}`

#### 4.3 Test Frontend

1. Open your Vercel frontend URL in a browser
2. Open Developer Tools (F12) → Console tab
3. Look for any red errors

**If you see CORS errors:**
```
Access to fetch at 'https://...' from origin 'https://...' has been blocked by CORS policy
```

This means:
- The `CORS_ORIGINS` variable on Railway doesn't include your exact Vercel URL
- Double-check the URL (no trailing slash, exact match)
- Redeploy the backend after fixing

#### 4.4 Test End-to-End

1. Navigate to the Customers page
2. Click "Add Customer"
3. Fill in test data:
   - First Name: Test
   - Last Name: User
   - Phone: 6125551234
4. Click "Create"
5. Verify the customer appears in the list

**If this works, your deployment is complete! 🎉**

---

### Summary Checklist

| Step | Action | Status |
|------|--------|--------|
| 1.1 | Open Railway Dashboard | ☐ |
| 1.2 | Select Backend Service | ☐ |
| 1.3 | Add DATABASE_URL (reference to Postgres) | ☐ |
| 1.4 | Generate Public Domain | ☐ |
| 1.5 | Redeploy Backend | ☐ |
| 1.6 | Verify Backend Health | ☐ |
| 2.1 | Get Vercel Frontend URL | ☐ |
| 2.2 | Add CORS_ORIGINS on Railway | ☐ |
| 3.1 | Open Vercel Dashboard | ☐ |
| 3.2 | Set VITE_API_BASE_URL | ☐ |
| 3.3 | Redeploy Frontend | ☐ |
| 4.1 | Test Backend Health | ☐ |
| 4.2 | Test Backend API | ☐ |
| 4.3 | Test Frontend (no CORS errors) | ☐ |
| 4.4 | Test End-to-End (create customer) | ☐ |

---

### Quick Reference: Your URLs

Fill these in as you go:

| Service | URL |
|---------|-----|
| Railway Backend | `https://________________________________.up.railway.app` |
| Vercel Frontend | `https://________________________________.vercel.app` |
| API Docs (Swagger) | `https://YOUR-BACKEND-URL.up.railway.app/docs` |

---

### Troubleshooting

#### Backend won't start
- Check Railway logs: Click on service → Deployments → Click on deployment → View logs
- Common issue: DATABASE_URL not set correctly

#### CORS errors in browser
- Verify CORS_ORIGINS on Railway matches your exact Vercel URL
- No trailing slashes
- Redeploy backend after changes

#### Frontend shows "Network Error"
- Verify VITE_API_BASE_URL on Vercel is correct
- Verify backend is running (test /health endpoint)
- Redeploy frontend after changing env vars




Make a note that we added database URL to Cleanse Irrigation Platform Service by adding this. DATABASE_URL ${{Postgres.DATABASE_URL}}

grinsirrigationplatform-production.up.railway.app


