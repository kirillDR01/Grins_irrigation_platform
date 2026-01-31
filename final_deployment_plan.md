# Grin's Irrigation Platform - Final Deployment Plan

**Version:** 1.0  
**Date:** January 30, 2026  
**Status:** Ready for Deployment  
**Strategy:** Railway (Backend) + Vercel (Frontend)  
**Estimated Deployment Time:** 30-45 minutes  
**Monthly Cost:** $50-100 (production)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Phase 1: Backend Deployment (Railway)](#phase-1-backend-deployment-railway)
4. [Phase 2: Frontend Deployment (Vercel)](#phase-2-frontend-deployment-vercel)
5. [Phase 3: External Services Configuration](#phase-3-external-services-configuration)
6. [Phase 4: Database Migration & Seeding](#phase-4-database-migration--seeding)
7. [Phase 5: Integration Testing](#phase-5-integration-testing)
8. [Phase 6: DNS & Custom Domain Setup](#phase-6-dns--custom-domain-setup)
9. [Post-Deployment Verification](#post-deployment-verification)
10. [Rollback Procedures](#rollback-procedures)
11. [Cost Breakdown](#cost-breakdown)
12. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Executive Summary

### Why Railway + Vercel?

| Aspect | Railway + Vercel | Traditional (AWS/GCP) |
|--------|------------------|----------------------|
| Setup Time | 30-45 minutes | 4-8 hours |
| DevOps Required | None | Significant |
| Auto-Scaling | ✅ Built-in | Manual configuration |
| SSL/HTTPS | ✅ Automatic | Manual setup |
| Database Backups | ✅ Automatic | Manual configuration |
| CI/CD | ✅ Git push to deploy | Manual pipeline setup |
| Monthly Cost | $50-100 | $100-300+ |
| Monitoring | ✅ Built-in | Additional setup |

### Current System Status

**Backend (Ready for Deployment):**
- ✅ FastAPI application with 30+ API endpoints
- ✅ PostgreSQL database schema with migrations
- ✅ Customer, Job, Staff, Appointment management
- ✅ Service catalog with pricing
- ✅ Dashboard metrics API
- ✅ Health check endpoint
- ✅ Structured logging
- ✅ Docker containerization ready

**Frontend (Ready for Deployment):**
- ✅ React + TypeScript admin dashboard
- ✅ Customer, Job, Staff, Schedule views
- ✅ TanStack Query for data fetching
- ✅ Tailwind CSS + shadcn/ui styling
- ✅ Vite build system
- ✅ Environment variable configuration

---

## Pre-Deployment Checklist

### Required Accounts (Create Before Starting)

| Service | Purpose | Signup URL | Time |
|---------|---------|------------|------|
| **GitHub** | Code repository | github.com | 2 min |
| **Railway** | Backend hosting | railway.app | 3 min |
| **Vercel** | Frontend hosting | vercel.com | 2 min |
| **Google Cloud** | Maps API | console.cloud.google.com | 10 min |

### Optional Services (Can Add Later)

| Service | Purpose | When Needed |
|---------|---------|-------------|
| Twilio | SMS notifications | Phase 3 (Communication) |
| Stripe | Payment processing | Phase 4 (Payments) |
| Anthropic | AI chat agent | Phase 3 (AI Assistant) |
| Cloudflare R2 | File storage | Phase 2 (Photo uploads) |
| Resend | Email notifications | Phase 3 (Communication) |
| Sentry | Error monitoring | Production launch |

### Local Verification Before Deployment

```bash
# 1. Verify backend runs locally
cd /Users/kirillrakitin/Grins_irrigation_platform
uv run uvicorn grins_platform.main:app --reload --port 8000

# 2. Test health endpoint
curl http://localhost:8000/health

# 3. Verify frontend builds
cd frontend
npm run build

# 4. Run quality checks
uv run ruff check src/
uv run mypy src/
uv run pytest -v
```

---

## Phase 1: Backend Deployment (Railway)

### Step 1.1: Create Railway Project

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select `Grins_irrigation_platform` repository

### Step 1.2: Configure Railway Service

**Build Settings:**
- **Builder:** Nixpacks (auto-detected)
- **Root Directory:** `/` (project root)
- **Build Command:** Auto-detected from `pyproject.toml`

**Start Command:**
```bash
uvicorn grins_platform.main:app --host 0.0.0.0 --port $PORT
```

### Step 1.3: Add PostgreSQL Database

1. In Railway project dashboard
2. Click "New" → "Database" → "Add PostgreSQL"
3. Railway automatically creates and injects `DATABASE_URL`

**Database Configuration:**
- Version: PostgreSQL 15
- Auto-backups: Enabled
- Connection pooling: Enabled

### Step 1.4: Add Redis (Optional - For Future Celery)

1. Click "New" → "Database" → "Add Redis"
2. Railway injects `REDIS_URL` automatically

### Step 1.5: Configure Environment Variables

In Railway dashboard → Your Service → Variables:

```bash
# === Application ===
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# === Database (Auto-injected by Railway) ===
DATABASE_URL=${{Postgres.DATABASE_URL}}

# === Security ===
JWT_SECRET=<generate-with-openssl-rand-base64-32>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
SECRET_KEY=<generate-with-openssl-rand-base64-32>

# === Google Maps ===
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>

# === OpenAI (for AI features) ===
OPENAI_API_KEY=<your-openai-api-key>

# === Feature Flags ===
ENABLE_AI_FEATURES=true
```

**Generate Secure Secrets:**
```bash
# Run locally to generate secrets
openssl rand -base64 32
```

### Step 1.6: Verify Backend Deployment

1. Railway provides URL: `https://your-app.up.railway.app`
2. Test health endpoint: `https://your-app.up.railway.app/health`
3. Test API docs: `https://your-app.up.railway.app/docs`

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "grins-platform-api",
  "version": "1.0.0"
}
```

---

## Phase 2: Frontend Deployment (Vercel)

### Step 2.1: Create Vercel Project

1. Go to [vercel.com](https://vercel.com)
2. Click "Add New" → "Project"
3. Import `Grins_irrigation_platform` repository
4. **Important:** Set root directory to `frontend`

### Step 2.2: Configure Build Settings

**Framework Preset:** Vite  
**Build Command:** `npm run build`  
**Output Directory:** `dist`  
**Install Command:** `npm install`

### Step 2.3: Configure Environment Variables

In Vercel dashboard → Your Project → Settings → Environment Variables:

```bash
# === API Configuration ===
VITE_API_BASE_URL=https://your-app.up.railway.app

# === Google Maps ===
VITE_GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>

# === Feature Flags ===
VITE_ENABLE_AI_FEATURES=true
```

### Step 2.4: Deploy Frontend

1. Click "Deploy"
2. Vercel builds and deploys automatically
3. Get URL: `https://your-frontend.vercel.app`

### Step 2.5: Configure CORS on Backend

Update Railway environment variables to allow frontend origin:

```bash
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
```

**Or update `main.py` if not using environment variable:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend.vercel.app",
        "http://localhost:5173",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Phase 3: External Services Configuration

### Google Maps API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project: "Grins Irrigation Platform"
3. Enable APIs:
   - Maps JavaScript API
   - Geocoding API
   - Directions API
   - Places API
4. Create API key
5. Restrict API key:
   - HTTP referrers: `your-frontend.vercel.app/*`, `localhost:*`
   - API restrictions: Only enabled APIs

### Twilio Setup (Phase 3 - Communication)

1. Create account at [twilio.com](https://www.twilio.com)
2. Get Account SID and Auth Token
3. Buy phone number (~$1/month)
4. Add to Railway environment:
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your-auth-token
   TWILIO_PHONE_NUMBER=+15551234567
   ```

### Stripe Setup (Phase 4 - Payments)

1. Create account at [stripe.com](https://stripe.com)
2. Get API keys (test mode first)
3. Add to Railway environment:
   ```bash
   STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
   ```
4. Add to Vercel environment:
   ```bash
   VITE_STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxxx
   ```

---

## Phase 4: Database Migration & Seeding

### Run Migrations

**Option A: Automatic on Startup (Recommended)**

Add to `main.py`:
```python
@app.on_event("startup")
async def startup_event():
    """Run database migrations on startup."""
    from alembic.config import Config
    from alembic import command
    
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed")
```

**Option B: Manual via Railway Shell**

1. In Railway dashboard → Your Service → Shell
2. Run:
   ```bash
   alembic upgrade head
   ```

### Seed Demo Data (Optional)

```bash
# In Railway shell
python scripts/seed_service_offerings.py
```

---

## Phase 5: Integration Testing

### Backend API Tests

```bash
# Test health endpoint
curl https://your-app.up.railway.app/health

# Test API documentation
curl https://your-app.up.railway.app/docs

# Test customers endpoint
curl https://your-app.up.railway.app/api/v1/customers

# Test jobs endpoint
curl https://your-app.up.railway.app/api/v1/jobs
```

### Frontend Tests

1. Open `https://your-frontend.vercel.app`
2. Verify dashboard loads
3. Test navigation to all pages:
   - Dashboard
   - Customers
   - Jobs
   - Staff
   - Schedule
   - Settings

### End-to-End Flow Test

1. Create a new customer
2. Create a job for that customer
3. Create an appointment
4. Verify data appears in dashboard

---

## Phase 6: DNS & Custom Domain Setup

### Custom Domain for Frontend (Vercel)

1. In Vercel → Your Project → Settings → Domains
2. Add domain: `app.grins-irrigation.com`
3. Configure DNS:
   - Type: CNAME
   - Name: app
   - Value: cname.vercel-dns.com

### Custom Domain for Backend (Railway)

1. In Railway → Your Service → Settings → Domains
2. Add domain: `api.grins-irrigation.com`
3. Configure DNS:
   - Type: CNAME
   - Name: api
   - Value: your-app.up.railway.app

### Update Environment Variables

After custom domains are configured:

**Railway:**
```bash
CORS_ORIGINS=https://app.grins-irrigation.com,https://your-frontend.vercel.app
```

**Vercel:**
```bash
VITE_API_BASE_URL=https://api.grins-irrigation.com
```

---

## Post-Deployment Verification

### Verification Checklist

- [ ] Backend health check returns 200
- [ ] API documentation accessible at /docs
- [ ] Frontend loads without errors
- [ ] API calls from frontend succeed (no CORS errors)
- [ ] Database connection working (can create/read data)
- [ ] Google Maps loads on schedule page
- [ ] All navigation links work
- [ ] Forms submit successfully

### Performance Checks

- [ ] Page load time < 3 seconds
- [ ] API response time < 500ms
- [ ] No console errors in browser
- [ ] Mobile responsive design works

### Security Checks

- [ ] HTTPS enabled on both frontend and backend
- [ ] API keys not exposed in frontend code
- [ ] CORS properly configured
- [ ] JWT authentication working

---

## Rollback Procedures

### Backend Rollback (Railway)

1. Go to Railway → Your Service → Deployments
2. Find previous successful deployment
3. Click "Redeploy" on that deployment

### Frontend Rollback (Vercel)

1. Go to Vercel → Your Project → Deployments
2. Find previous successful deployment
3. Click "..." → "Promote to Production"

### Database Rollback

```bash
# In Railway shell
alembic downgrade -1  # Rollback one migration
alembic downgrade <revision>  # Rollback to specific revision
```

---

## Cost Breakdown

### Monthly Costs (Production)

| Service | Tier | Estimated Cost | Notes |
|---------|------|----------------|-------|
| **Railway - API** | Hobby | $10-20 | Based on usage |
| **Railway - PostgreSQL** | Shared | $10-20 | 1-10GB storage |
| **Railway - Redis** | Shared | $5-10 | Optional, for Celery |
| **Vercel** | Hobby/Pro | $0-20 | Free tier often sufficient |
| **Google Maps** | Pay-as-you-go | $0-50 | $200 free credit |
| **Domain** | Annual | $12/year | ~$1/month |

**Total Fixed Cost:** $25-70/month  
**Variable Cost:** Based on usage

### Cost Optimization Tips

1. **Start with free tiers** - Test before committing
2. **Monitor usage** - Set billing alerts
3. **Use Railway's $5 credit** - Test deployment
4. **Vercel free tier** - Sufficient for MVP
5. **Google Maps $200 credit** - Covers ~40,000 geocodes

---

## Monitoring & Maintenance

### Railway Monitoring

- **Logs:** Railway dashboard → Your Service → Logs
- **Metrics:** CPU, Memory, Request count
- **Alerts:** Configure in Settings → Notifications

### Vercel Monitoring

- **Analytics:** Vercel dashboard → Analytics
- **Logs:** Function logs for any serverless functions
- **Speed Insights:** Performance monitoring

### Recommended Monitoring Setup

1. **Sentry** (Error tracking):
   ```bash
   # Add to Railway environment
   SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
   ```

2. **Uptime Monitoring** (Free options):
   - UptimeRobot (free tier)
   - Better Uptime (free tier)
   - Configure to ping `/health` endpoint

### Maintenance Tasks

**Weekly:**
- Review error logs
- Check database size
- Monitor API response times

**Monthly:**
- Review costs
- Update dependencies
- Database backup verification

**Quarterly:**
- Security audit
- Performance optimization
- Feature review

---

## Quick Reference Commands

### Local Development

```bash
# Start backend
uv run uvicorn grins_platform.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Run tests
uv run pytest -v

# Quality checks
uv run ruff check src/ && uv run mypy src/
```

### Deployment

```bash
# Deploy backend (automatic on git push)
git push origin main

# Deploy frontend (automatic on git push)
git push origin main

# Manual redeploy (Railway)
# Use Railway dashboard

# Manual redeploy (Vercel)
# Use Vercel dashboard
```

### Database

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Deployment Timeline

| Step | Duration | Cumulative |
|------|----------|------------|
| Create accounts | 15 min | 15 min |
| Deploy backend (Railway) | 10 min | 25 min |
| Add PostgreSQL | 2 min | 27 min |
| Configure env vars | 5 min | 32 min |
| Deploy frontend (Vercel) | 5 min | 37 min |
| Configure CORS | 3 min | 40 min |
| Integration testing | 10 min | 50 min |
| Custom domain (optional) | 15 min | 65 min |

**Total Time:** 40-65 minutes

---

## Support Resources

- **Railway Docs:** [docs.railway.app](https://docs.railway.app)
- **Railway Discord:** [discord.gg/railway](https://discord.gg/railway)
- **Vercel Docs:** [vercel.com/docs](https://vercel.com/docs)
- **Vercel Discord:** [vercel.com/discord](https://vercel.com/discord)

---

## Next Steps After Deployment

1. **Test all features** with real data
2. **Set up monitoring** (Sentry, uptime)
3. **Configure custom domain** if needed
4. **Add Twilio** for SMS notifications (Phase 3)
5. **Add Stripe** for payments (Phase 4)
6. **Deploy Staff PWA** (Phase 2 completion)

---

**You're ready to deploy! 🚀**

Follow the phases in order, and you'll have a production system running in under an hour.
