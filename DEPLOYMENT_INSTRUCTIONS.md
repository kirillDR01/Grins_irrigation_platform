# Grin's Irrigation Platform - Deployment Instructions

**Follow these steps exactly in order. Check off each step as you complete it.**

---

## Prerequisites Checklist

Before starting, confirm you have:
- [ ] GitHub account with repository access
- [ ] Vercel account ✅ (you have this)
- [ ] Railway account (create below)
- [ ] Google Cloud account (for Maps API - can do later)

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

### 7.1 Option A: Run Migrations via Railway Shell (Recommended)

1. Go to Railway → Your Backend Service
2. Click **"Settings"** tab
3. Scroll down to **"Service"** section
4. Find **"Railway Shell"** or use the **"Connect"** button
5. Run:

```bash
alembic upgrade head
```

### 7.2 Option B: Run Migrations Locally

If Railway Shell isn't available, run migrations from your local machine:

1. Get your Railway PostgreSQL connection string:
   - Go to Railway → PostgreSQL service
   - Click **"Connect"** tab
   - Copy the **"Public URL"** (starts with `postgresql://`)

2. Run locally:
```bash
# Set the DATABASE_URL temporarily
export DATABASE_URL="postgresql://postgres:your-password@your-host.railway.app:port/railway"

# Run migrations
uv run alembic upgrade head
```

### 7.3 Verify Migrations

After running migrations, verify tables were created:

1. Go to Railway → PostgreSQL service
2. Click **"Data"** tab
3. You should see tables like:
   - `customers`
   - `properties`
   - `jobs`
   - `staff`
   - `appointments`
   - `service_offerings`
   - etc.

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
- Run migrations: `alembic upgrade head`
- Check migration logs for errors

**Problem: Connection refused**
- Verify PostgreSQL service is running in Railway
- Check `DATABASE_URL` format is correct

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
