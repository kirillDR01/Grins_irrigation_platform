# Lead Capture Form Submission — CORS Fix Guide

## Problem

When a visitor submits the "Get Your Free Design" form on the Grin's Irrigation landing page (`grins-irrigation.vercel.app`), the browser blocks the request with a CORS error:

```
Access to fetch at 'https://grins-platform-production.up.railway.app/api/v1/leads'
from origin 'https://grins-irrigation.vercel.app' has been blocked by CORS policy:
Response to preflight request doesn't pass access control check:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

The form fills out correctly and the submit button fires, but the POST request to the backend API is rejected by the browser before it ever reaches the server.

## Root Cause

The backend's CORS middleware only allows origins listed in the `CORS_ORIGINS` environment variable (plus localhost defaults for local dev). The landing page domain `https://grins-irrigation.vercel.app` was not included in that variable on the Railway production deployment.

## How CORS Works in This Codebase

The CORS configuration lives in `src/grins_platform/app.py` inside the `create_app()` function:

```python
# Configure CORS - read from environment variable or use defaults for local dev
# CORS_ORIGINS should be a comma-separated list of allowed origins
cors_origins_env = os.getenv("CORS_ORIGINS", "")

# Default origins for local development
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]

# Parse CORS_ORIGINS from environment (comma-separated)
if cors_origins_env:
    env_origins = [
        origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
    ]
    allowed_origins = env_origins + default_origins
else:
    allowed_origins = default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

No code changes are needed. The fix is purely a configuration change on Railway.

---

## Fix: Add Landing Page Domain to CORS_ORIGINS on Railway

### Step 1 — Open Railway Backend Variables

1. Go to [https://railway.app/dashboard](https://railway.app/dashboard)
2. Click on your **Grins Irrigation Platform** project
3. Click on the **backend service** (the FastAPI app, not the PostgreSQL database)
4. Go to the **"Variables"** tab

### Step 2 — Update CORS_ORIGINS

Find the `CORS_ORIGINS` variable. If it already exists, add the landing page domain to the comma-separated list. If it doesn't exist, create it.

**If `CORS_ORIGINS` already exists** (e.g., it has the admin dashboard domain):

Update the value to include both domains, comma-separated:

```
https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app
```

**If `CORS_ORIGINS` does not exist yet**, create a new variable:

| Variable Name | Value |
|---------------|-------|
| `CORS_ORIGINS` | `https://grins-irrigation.vercel.app` |

If you also have a separate admin dashboard frontend on Vercel, include both:

```
https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app
```

**Rules:**
- Each origin MUST include the `https://` protocol prefix
- NO trailing slash on any origin
- Separate multiple origins with commas (no spaces needed, but spaces are fine)
- Origins are case-sensitive — match the exact domain

### Step 3 — Redeploy the Backend

Railway usually auto-redeploys when environment variables change. If it doesn't:

1. Go to the **"Deployments"** tab
2. Click **"..."** on the latest deployment → **"Redeploy"**
3. Wait for the build to complete (2-5 minutes)

### Step 4 — Verify the Fix

Test the form submission from the landing page:

1. Open [https://grins-irrigation.vercel.app](https://grins-irrigation.vercel.app)
2. Scroll to the "Get Your Free Design" form
3. Fill in test data and submit
4. You should see a success message instead of a silent failure

Or verify via curl from your terminal:

```bash
# Simulate a preflight OPTIONS request
curl -I -X OPTIONS \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  https://grins-platform-production.up.railway.app/api/v1/leads
```

The response should include:

```
Access-Control-Allow-Origin: https://grins-irrigation.vercel.app
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

You can also test the actual POST:

```bash
curl -s -X POST https://grins-platform-production.up.railway.app/api/v1/leads \
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

Expected response (HTTP 201):

```json
{
  "success": true,
  "message": "Thank you! We'll be in touch within 24 hours.",
  "lead_id": "some-uuid-here"
}
```

---

## Environment Variables Reference

All environment variables involved in the lead form submission flow:

### Railway Backend

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app` |
| `DATABASE_URL` | PostgreSQL connection (auto-linked from Railway Postgres) | `${{Postgres.DATABASE_URL}}` |

### Vercel — Admin Dashboard (`grins-irrigation-platform.vercel.app`)

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `VITE_API_BASE_URL` | Backend API base URL (no trailing slash) | `https://grins-platform-production.up.railway.app` |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Maps for schedule map view | `AIzaSy...` |

### Vercel — Landing Page (`grins-irrigation.vercel.app`)

The landing page is a separate repo/deployment. It needs its own environment variable pointing to the backend:

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| API base URL (check landing page code for exact variable name) | Backend API base URL | `https://grins-platform-production.up.railway.app` |

The landing page submits to `{API_BASE_URL}/api/v1/leads` via a POST request.

### Local Development

For local development, no `CORS_ORIGINS` variable is needed. The backend defaults to allowing:

- `http://localhost:5173` (Vite dev server)
- `http://localhost:5174` (Vite alternate port)
- `http://localhost:3000` (alternate dev server)
- `http://127.0.0.1:5173`, `http://127.0.0.1:5174`, `http://127.0.0.1:3000`

The frontend `.env` file defaults to:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Troubleshooting

### Still getting CORS errors after updating?

1. **Check for typos** — The origin must match exactly. Compare the error message's `origin` value with your `CORS_ORIGINS` value character by character.
2. **No trailing slash** — `https://grins-irrigation.vercel.app` not `https://grins-irrigation.vercel.app/`
3. **Include protocol** — `https://grins-irrigation.vercel.app` not `grins-irrigation.vercel.app`
4. **Redeploy** — Make sure the backend actually redeployed after the variable change. Check the deployment timestamp on Railway.
5. **Clear browser cache** — Browsers can cache CORS preflight responses. Try an incognito window or hard refresh.

### Form submits but no success message appears?

The landing page frontend may need to handle the API response. Check the landing page code for the form submission handler and ensure it reads the `success` and `message` fields from the response.

### Lead submitted but doesn't appear in admin dashboard?

1. Log into the admin dashboard at your Vercel frontend URL
2. Navigate to the Leads tab
3. Check that the admin dashboard's `VITE_API_BASE_URL` points to the same backend
4. If the dashboard is on a different Vercel deployment, its domain also needs to be in `CORS_ORIGINS`
