# Landing Page Lead Form — "Something went wrong" Submission Failure

**Date Diagnosed:** 2026-02-28
**Date Resolved:** 2026-02-28
**Status:** RESOLVED (code fix pushed; awaiting Vercel redeploy of landing page)
**Affected URL:** `https://grins-irrigation.vercel.app` — the "Get Your Free Design" contact form
**Symptom:** Submitting the lead form shows a red error: "Something went wrong. Please try again or call us directly."
**Root Cause:** The landing page was sending the form POST to a non-existent Railway backend URL (`grins-platform-production.up.railway.app`) instead of the correct one (`grinsirrigationplatform-production.up.railway.app`)
**Resolution:** Updated the hardcoded fallback URL in `lib/leadApi.ts` in the `Grins_irrigation` repo and pushed to GitHub to trigger a Vercel redeploy

---

## Table of Contents

1. [Background — How the Lead Form Works](#background--how-the-lead-form-works)
2. [The Problem — What Was Happening](#the-problem--what-was-happening)
3. [Diagnosis — How We Found the Root Cause](#diagnosis--how-we-found-the-root-cause)
4. [Root Cause — Why It Was Broken](#root-cause--why-it-was-broken)
5. [Resolution — How We Fixed It](#resolution--how-we-fixed-it)
6. [Verification — How We Confirmed the Fix](#verification--how-we-confirmed-the-fix)
7. [If This Happens Again — Step-by-Step Playbook](#if-this-happens-again--step-by-step-playbook)
8. [Key Files Reference](#key-files-reference)
9. [Related Issues](#related-issues)
10. [Related Documentation](#related-documentation)

---

## Background — How the Lead Form Works

### The Two Separate Frontends

This platform has **two separate frontend applications**, deployed as two separate Vercel projects, built from two separate GitHub repositories:

| Frontend | URL | GitHub Repo | Purpose |
|----------|-----|-------------|---------|
| **Landing Page** | `https://grins-irrigation.vercel.app` | `kirillDR01/Grins_irrigation` | Public-facing marketing website where potential customers fill out a contact form to request a free irrigation system design |
| **Admin Dashboard** | `https://grins-irrigation-platform.vercel.app` | `kirillDR01/Grins_irrigation_platform` | Internal admin panel where staff manage customers, jobs, leads, invoices, schedules |

Both frontends talk to the **same backend API**:

| Backend | URL | GitHub Repo | Hosted On |
|---------|-----|-------------|-----------|
| **FastAPI Backend** | `https://grinsirrigationplatform-production.up.railway.app` | `kirillDR01/Grins_irrigation_platform` (in `src/` directory) | Railway |

### How a Lead Flows Through the System

```
Step 1: Visitor lands on grins-irrigation.vercel.app
        ↓
Step 2: Visitor clicks "Get Your Free Design" button
        ↓
Step 3: A modal form opens with fields:
        - Your Name
        - Phone Number
        - Zip Code
        - What best describes your situation? (dropdown)
        - Email (optional)
        - Anything else we should know? (optional notes)
        ↓
Step 4: Visitor fills out the form and clicks "Send My Free Design Request"
        ↓
Step 5: The landing page JavaScript calls:
        POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads
        Body: { name, phone, zip_code, situation, email, notes, source_site, website }
        ↓
Step 6: The FastAPI backend receives the POST request
        - Checks the honeypot field ("website") — if filled, silently ignores the submission (spam)
        - Checks for duplicate leads by phone number
        - Creates a new lead record in the PostgreSQL database with status "new"
        - Returns HTTP 201 with { success: true, message: "Thank you!...", lead_id: "..." }
        ↓
Step 7: The landing page shows a success message to the visitor
        ↓
Step 8: An admin logs into grins-irrigation-platform.vercel.app
        ↓
Step 9: Admin clicks "Leads" in the sidebar
        ↓
Step 10: The admin dashboard calls:
         GET https://grinsirrigationplatform-production.up.railway.app/api/v1/leads
         ↓
Step 11: The new lead appears in the leads table with status "New"
```

### How the Landing Page Knows Where the Backend Is

The landing page's API client is in `lib/leadApi.ts` in the `Grins_irrigation` repository:

```typescript
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://grinsirrigationplatform-production.up.railway.app';
```

This works in two ways:
1. **If `VITE_API_URL` is set** as an environment variable on Vercel → uses that value
2. **If `VITE_API_URL` is NOT set** → falls back to the hardcoded URL

The `VITE_API_URL` environment variable is set at **build time** (Vite bakes it into the JavaScript bundle). Changing it requires a redeploy on Vercel.

### How CORS Fits In

The backend only allows API requests from specific frontend domains. This is controlled by the `CORS_ORIGINS` environment variable on Railway:

```
CORS_ORIGINS=https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app
```

If a frontend domain is not in this list, the browser blocks the request before it even reaches the backend (the preflight OPTIONS check fails). This produces a CORS error in the browser console.

---

## The Problem — What Was Happening

### What the User Saw

1. Open `https://grins-irrigation.vercel.app`
2. Click **"Get Your Free Design"** (orange button, top right)
3. A modal form opens
4. Fill in all required fields (name, phone, zip code, situation)
5. Click **"Send My Free Design Request"**
6. After a brief pause, a **red error message** appears below the form: **"Something went wrong. Please try again or call us directly."**
7. Clicking "Send My Free Design Request" again produces the same error

### What the Error Looked Like

```
┌───────────────────────────────────────────────────┐
│  Your Name                                        │
│  ┌─────────────────────────────────────────────┐  │
│  │ Claude Test Lead                            │  │
│  └─────────────────────────────────────────────┘  │
│  Phone Number                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ (612) 555-9999                              │  │
│  └─────────────────────────────────────────────┘  │
│  Zip Code                                         │
│  ┌─────────────────────────────────────────────┐  │
│  │ 55401                                       │  │
│  └─────────────────────────────────────────────┘  │
│  ... (more fields) ...                            │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ ⚠ Something went wrong. Please try again   │  │
│  │   or call us directly.                      │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │     Send My Free Design Request             │  │
│  └─────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
```

### Context — This Was Discovered While Testing Another Fix

This issue was discovered during end-to-end testing of a separate fix. We had just resolved the admin dashboard's Leads page "Network Error" (see [leads-network-error-500.md](./leads-network-error-500.md)) and were testing the full flow: submit a lead on the landing page → verify it appears in the admin dashboard. The landing page form submission failed, revealing this second issue.

---

## Diagnosis — How We Found the Root Cause

### Step 1 — Submitted the Form via Agent Browser

We used a headless browser to navigate to the landing page, fill out the form, and submit it. The form returned the error: "Something went wrong. Please try again or call us directly."

### Step 2 — Intercepted the Network Request

After the form submission failed, we inspected which URL the landing page was calling by querying the browser's Performance API:

```javascript
const entries = performance.getEntriesByType('resource')
  .filter(r => r.initiatorType === 'xmlhttprequest' || r.initiatorType === 'fetch');
entries.map(e => e.name);
```

**Result:**
```json
["https://grins-platform-production.up.railway.app/api/v1/leads"]
```

The landing page was sending the POST to `grins-platform-production.up.railway.app`.

### Step 3 — Realized This Is the Wrong URL

The **correct** backend URL (the one the admin dashboard uses successfully) is:
```
grinsirrigationplatform-production.up.railway.app
```

The landing page was calling:
```
grins-platform-production.up.railway.app
```

These are **two completely different Railway hostnames**. The difference is subtle:
- Correct: `grins`**`irrigationplatform`**`-production`
- Wrong: `grins-`**`platform`**`-production`

### Step 4 — Confirmed the Wrong URL Doesn't Exist

```bash
curl -s https://grins-platform-production.up.railway.app/health
```

Response:
```json
{
  "status": "error",
  "code": 404,
  "message": "Application not found",
  "request_id": "yPJUAZMhT2S0_38SAax-fw"
}
```

The URL `grins-platform-production.up.railway.app` returns a **Railway 404 — "Application not found"**. There is no service at this address. It's a completely non-existent endpoint.

### Step 5 — Confirmed the Correct URL Works

```bash
curl -s -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -d '{
    "name": "Claude Test Lead",
    "phone": "(612) 555-9999",
    "zip_code": "55401",
    "situation": "new_system",
    "email": "claudetest@example.com",
    "notes": "End-to-end test submitted via curl",
    "source_site": "residential",
    "website": ""
  }'
```

Response (HTTP 201):
```json
{
  "success": true,
  "message": "Thank you! We'll be in touch within 24 hours.",
  "lead_id": "4332385a-e439-4a0e-b32e-2165a5d804aa"
}
```

The correct backend URL accepts the lead submission and creates it in the database.

### Step 6 — Found the Wrong URL in the Source Code

Searched the landing page repo (`Grins_irrigation`) for Railway URLs:

```bash
grep -r "railway\.app" /Users/kirillrakitin/Grins_irrigation/
```

Found in `lib/leadApi.ts` at line 45:

```typescript
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://grins-platform-production.up.railway.app';  // ← WRONG URL
```

The hardcoded fallback URL was wrong. Since `VITE_API_URL` was not set as an environment variable on the Vercel deployment, the code was always using this wrong fallback.

### Step 7 — Verified the Vercel Environment Variables

Checked the landing page's Vercel environment variables. The `VITE_API_URL` variable was either not set or empty, meaning the code always fell through to the hardcoded fallback — the wrong URL.

---

## Root Cause — Why It Was Broken

**The landing page had a wrong backend URL hardcoded as the fallback in `lib/leadApi.ts`.**

Here's the chain of events:

1. When the lead form feature was developed, the developer hardcoded `https://grins-platform-production.up.railway.app` as the fallback backend URL
2. This URL **never existed** on Railway — the actual backend service is at `https://grinsirrigationplatform-production.up.railway.app`
3. The `VITE_API_URL` environment variable was not set on the Vercel deployment for the landing page
4. So the code always fell through to the wrong hardcoded URL
5. When a visitor submitted the form, the JavaScript sent a POST request to `grins-platform-production.up.railway.app`
6. Railway returned a 404 ("Application not found") because no service exists at that hostname
7. The `submitLead()` function caught the error and returned `{ ok: false, error: 'server' }`
8. The form component displayed: "Something went wrong. Please try again or call us directly."

### Why This Wasn't Caught Earlier

- The lead form feature was developed recently and may not have been thoroughly tested against the production backend
- The URL difference is subtle and easy to miss (`grins-platform-production` vs `grinsirrigationplatform-production`)
- Local development might have used `VITE_API_URL=http://localhost:8000` which would have worked fine against a local backend

---

## Resolution — How We Fixed It

### What We Changed

One line in one file in the `Grins_irrigation` repository (the landing page):

**File:** `lib/leadApi.ts` (line 45)

**Before:**
```typescript
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://grins-platform-production.up.railway.app';
```

**After:**
```typescript
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  'https://grinsirrigationplatform-production.up.railway.app';
```

### How We Deployed the Fix

1. **Edited the file** in the local clone of `Grins_irrigation` at `/Users/kirillrakitin/Grins_irrigation/lib/leadApi.ts`

2. **Committed the change:**
   ```bash
   cd /Users/kirillrakitin/Grins_irrigation
   git add lib/leadApi.ts
   git commit -m "fix: update API fallback URL to correct Railway backend

   The hardcoded fallback URL was pointing to a non-existent Railway service
   (grins-platform-production.up.railway.app) which returns 404. Updated to
   the correct backend URL (grinsirrigationplatform-production.up.railway.app)."
   ```

3. **Pushed to GitHub:**
   ```bash
   git push origin main
   ```

4. **Vercel auto-redeploy:** The landing page's Vercel project is connected to `kirillDR01/Grins_irrigation` on the `main` branch. Pushing to `main` triggers an automatic redeploy. The new build bakes the corrected URL into the JavaScript bundle.

### Additional Step — Ensure CORS Is Configured

The backend must allow requests from the landing page origin. On Railway, the `CORS_ORIGINS` environment variable must include the landing page domain:

```
CORS_ORIGINS=https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app
```

If the landing page domain is missing from `CORS_ORIGINS`, the form submission will fail with a CORS error (a different error than the one we fixed here, but the user sees the same "Something went wrong" message).

To check or update this:
1. Go to [Railway Dashboard](https://railway.app/dashboard) → your project → backend service → **Variables** tab
2. Find `CORS_ORIGINS`
3. Ensure `https://grins-irrigation.vercel.app` is in the comma-separated list
4. If you add it, Railway auto-redeploys

---

## Verification — How We Confirmed the Fix

### Verification Step 1 — Direct API Test via curl

While waiting for the Vercel redeploy, we verified the backend accepts leads from the correct URL:

```bash
curl -s -w "\nHTTP Status: %{http_code}" \
  -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Content-Type: application/json" \
  -H "Origin: https://grins-irrigation.vercel.app" \
  -d '{
    "name": "Claude Test Lead",
    "phone": "(612) 555-9999",
    "zip_code": "55401",
    "situation": "new_system",
    "email": "claudetest@example.com",
    "notes": "End-to-end test submitted via curl",
    "source_site": "residential",
    "website": ""
  }'
```

**Result:**
```json
{"success":true,"message":"Thank you! We'll be in touch within 24 hours.","lead_id":"4332385a-e439-4a0e-b32e-2165a5d804aa"}
HTTP Status: 201
```

The backend accepted the lead. HTTP 201 = created.

### Verification Step 2 — Admin Dashboard Shows the Lead

Opened the admin dashboard at `https://grins-irrigation-platform.vercel.app`, logged in with `admin` / `admin123`, and navigated to the **Leads** tab.

The sidebar showed **"Leads 1"** (a badge indicating 1 new lead), and the leads table displayed:

| Name | Phone | Situation | Status | Zip Code | Submitted | Assigned To |
|------|-------|-----------|--------|----------|-----------|-------------|
| Claude Test Lead | 6125559999 | New System | New | 55401 | less than a minute ago | Unassigned |

The end-to-end flow works: lead submitted → stored in database → visible in admin dashboard.

### Verification Step 3 — Confirm Vercel Redeploy (After Deploy Completes)

After Vercel finishes redeploying the landing page, verify the fix is live:

```bash
# Download the JS bundle and check for the correct URL
curl -s https://grins-irrigation.vercel.app/ | grep -o 'assets/index-[^"]*\.js' | \
  xargs -I{} curl -s "https://grins-irrigation.vercel.app/{}" | \
  grep -o 'https://[a-z-]*\.up\.railway\.app'
```

**Expected output after redeploy:**
```
https://grinsirrigationplatform-production.up.railway.app
```

**If it still shows the old URL:**
```
https://grins-platform-production.up.railway.app
```
Then the Vercel redeploy hasn't completed or wasn't triggered. See the troubleshooting section below.

### Verification Step 4 — Full Browser Test (After Deploy Completes)

1. Open `https://grins-irrigation.vercel.app` in an incognito/private browser window (to avoid caching)
2. Click **"Get Your Free Design"**
3. Fill in:
   - Name: `Test Verification`
   - Phone: `(612) 555-0000`
   - Zip Code: `55401`
   - Situation: any option
4. Click **"Send My Free Design Request"**
5. **Expected:** A success message (not the "Something went wrong" error)
6. Then open `https://grins-irrigation-platform.vercel.app`, log in, go to **Leads**
7. **Expected:** The test lead appears in the table

---

## If This Happens Again — Step-by-Step Playbook

If the landing page form shows "Something went wrong" after submission:

### 1. Open Browser Dev Tools and Check the Network Tab

1. Open the landing page in a browser
2. Press **F12** to open Developer Tools
3. Go to the **Network** tab
4. Fill out and submit the form
5. Look for a request to `/api/v1/leads`
6. Check:
   - **What URL was called?** — Is it the correct backend URL?
   - **What HTTP status was returned?** — 201 (success), 404 (wrong URL), 500 (backend error), or blocked by CORS?
   - **Is there a CORS error in the Console tab?** — Red text mentioning "CORS policy"

### 2. Identify Which Type of Failure

| What You See in Network Tab | What It Means | Fix |
|----------------------------|---------------|-----|
| Request to wrong URL (returns 404 from Railway) | The landing page has the wrong backend URL configured | Update the URL in `lib/leadApi.ts` or set `VITE_API_URL` on Vercel |
| CORS error (blocked by browser) | The backend doesn't allow the landing page origin | Add the landing page domain to `CORS_ORIGINS` on Railway |
| HTTP 500 Internal Server Error | The backend has a bug or the `leads` table is missing | Check Railway logs; run `uv run alembic upgrade head` if tables are missing |
| HTTP 422 Unprocessable Entity | The form data doesn't match the expected schema | Check the form field names match the API's expected payload |
| Network error / timeout | The backend is down or unreachable | Check Railway dashboard; test `curl https://grinsirrigationplatform-production.up.railway.app/health` |

### 3. Quick Test — Bypass the Frontend Entirely

Submit a lead directly via curl to rule out frontend issues:

```bash
curl -s -w "\nHTTP Status: %{http_code}" \
  -X POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Lead",
    "phone": "(612) 555-0000",
    "zip_code": "55401",
    "situation": "new_system",
    "email": "",
    "notes": "",
    "source_site": "residential",
    "website": ""
  }'
```

- **HTTP 201** → Backend works. The issue is in the frontend (wrong URL, CORS, or JavaScript error).
- **HTTP 500** → Backend error. Check Railway logs and database migrations.
- **No response / timeout** → Backend is down. Check Railway dashboard.

### 4. Check What URL the Landing Page Is Using

Download the deployed JS bundle and search for the Railway URL:

```bash
curl -s https://grins-irrigation.vercel.app/ | grep -o 'assets/index-[^"]*\.js' | \
  xargs -I{} curl -s "https://grins-irrigation.vercel.app/{}" | \
  grep -o 'https://[a-z-]*\.up\.railway\.app'
```

If this returns the wrong URL, either:
- Fix the hardcoded fallback in `lib/leadApi.ts` and push to trigger a Vercel redeploy
- Or set `VITE_API_URL` on the Vercel project's environment variables and redeploy

---

## Key Files Reference

### Landing Page (Grins_irrigation repo)

| File | Purpose | Why It Matters |
|------|---------|---------------|
| `lib/leadApi.ts` | API client for lead form submission. Contains `API_BASE_URL` (the backend URL), `buildLeadPayload()` (maps form data to API payload), and `submitLead()` (sends the POST request) | **This is where the bug was** — the fallback URL was wrong |
| `components/LeadForm.tsx` | The React form component with all input fields, validation, and the submit handler. Shows success/error messages based on the `submitLead()` result | Displays the "Something went wrong" error message |
| `.env.example` | Documents the `VITE_API_URL` environment variable | Shows developers what env vars need to be set |
| `vite.config.ts` | Vite build configuration | Determines how `import.meta.env.VITE_API_URL` is baked into the bundle |
| `package.json` | Project dependencies and build scripts | `npm run build` produces the static files deployed to Vercel |

### Backend (Grins_irrigation_platform repo)

| File | Purpose | Why It Matters |
|------|---------|---------------|
| `src/grins_platform/api/v1/leads.py` | The `/api/v1/leads` POST endpoint that receives form submissions. No authentication required for the public POST endpoint. | Processes incoming leads, checks honeypot, handles duplicates |
| `src/grins_platform/services/lead_service.py` | Business logic: `submit_lead()` handles honeypot detection, duplicate merging, and lead creation | Where the lead is actually created in the database |
| `src/grins_platform/app.py` (lines 83-116) | CORS middleware configuration. Reads `CORS_ORIGINS` env var. | Must include the landing page domain for form submission to work |

### Environment Variables

| Variable | Where It's Set | Current Value | Purpose |
|----------|---------------|---------------|---------|
| `VITE_API_URL` | Vercel → Landing Page project → Environment Variables | (should be set to) `https://grinsirrigationplatform-production.up.railway.app` | Tells the landing page where the backend is. If not set, falls back to the hardcoded URL in `lib/leadApi.ts`. |
| `CORS_ORIGINS` | Railway → Backend service → Variables | `https://grins-irrigation-platform.vercel.app,https://grins-irrigation.vercel.app` | Comma-separated list of frontend origins the backend allows. Must include the landing page domain. |

### Important URLs

| What | URL | Notes |
|------|-----|-------|
| Landing page (public) | `https://grins-irrigation.vercel.app` | Where visitors submit the form |
| Admin dashboard (internal) | `https://grins-irrigation-platform.vercel.app` | Where admins view leads |
| Backend API (correct) | `https://grinsirrigationplatform-production.up.railway.app` | The actual FastAPI backend on Railway |
| Backend API (WRONG — does not exist) | `https://grins-platform-production.up.railway.app` | Returns Railway 404. Was hardcoded as the fallback. |
| Lead submission endpoint | `POST https://grinsirrigationplatform-production.up.railway.app/api/v1/leads` | No auth required (public endpoint) |
| Health check | `GET https://grinsirrigationplatform-production.up.railway.app/health` | Quick check if backend is running |

---

## Common Mistakes and Confusing Aspects

### The Two Similar-Looking URLs

The most confusing aspect of this issue is that the correct and incorrect URLs are very similar:

```
CORRECT:  grinsirrigationplatform-production.up.railway.app
WRONG:    grins-platform-production.up.railway.app
```

The correct URL is the auto-generated Railway domain for the `Grins_irrigation_platform` GitHub repo. Railway creates domain names by concatenating the repo name (lowercased, no underscores) with the environment name.

### The Two Separate Repos

This platform uses two separate GitHub repositories that deploy to two separate Vercel projects. Changes to the landing page must be made in `Grins_irrigation`, NOT in `Grins_irrigation_platform`:

| Repo | Deploys To | Contains |
|------|-----------|----------|
| `kirillDR01/Grins_irrigation` | `grins-irrigation.vercel.app` | Landing page (React/Vite, marketing site with lead form) |
| `kirillDR01/Grins_irrigation_platform` | `grins-irrigation-platform.vercel.app` | Admin dashboard frontend + backend API code |

### The Environment Variable Name Difference

The two frontends use **different environment variable names** for the backend URL:

| Frontend | Env Var Name | Config File |
|----------|-------------|-------------|
| Landing page | `VITE_API_URL` | `lib/leadApi.ts` |
| Admin dashboard | `VITE_API_BASE_URL` | `frontend/src/core/config/index.ts` |

Don't confuse them. Setting `VITE_API_BASE_URL` on the landing page's Vercel project won't do anything — the landing page reads `VITE_API_URL`.

### Why the Error Message Is Vague

The form shows "Something went wrong. Please try again or call us directly." for **any** failure — whether it's a CORS error, a wrong URL, a 500 server error, or a network timeout. The `submitLead()` function in `lib/leadApi.ts` catches all errors and returns `{ ok: false, error: 'server' }`:

```typescript
export async function submitLead(payload: LeadPayload): Promise<SubmitResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (response.status === 201) return { ok: true };
    if (response.status === 422) return { ok: false, error: 'validation' };
    return { ok: false, error: 'server' };
  } catch {
    return { ok: false, error: 'server' };  // ← All errors land here
  }
}
```

This means you **must** use browser dev tools or curl to determine the actual cause. The user-facing error message won't tell you.

---

## Related Issues

- **[leads-network-error-500.md](./leads-network-error-500.md)** — A separate issue where the admin dashboard's Leads page showed "Network Error". Root cause: the `leads` database table hadn't been created (missing migration). This was fixed before the landing page issue was discovered.

These two issues are **independent** but were diagnosed in the same session:
1. First, we fixed the admin dashboard's Leads page (missing database migration)
2. Then, while testing the end-to-end flow, we discovered the landing page's form submission was also broken (wrong backend URL)

---

## Related Documentation

- [LeadErrorSolution.md](../../../LeadErrorSolution.md) — Earlier CORS-specific fix for the lead form (different URL was being used at the time)
- [docs/lead-form-cors-fix.md](../../lead-form-cors-fix.md) — Detailed CORS troubleshooting guide for the lead form
- [Deployment Step-by-Step Instructions.md](../../../Deployment%20Step-by-Step%20Instructions.md) — Full deployment guide with all environment variable references
- [leads-network-error-500.md](./leads-network-error-500.md) — The companion issue (admin dashboard Leads page failing with 500)

---

## Timeline

| Time | Action |
|------|--------|
| 2026-02-28 ~21:20 | After resolving the admin dashboard Leads 500 error, began end-to-end testing |
| 2026-02-28 ~21:21 | Opened landing page via agent-browser, filled out the "Get Your Free Design" form |
| 2026-02-28 ~21:22 | Form submission failed: "Something went wrong. Please try again or call us directly." |
| 2026-02-28 ~21:22 | Intercepted network requests — found the POST was going to `grins-platform-production.up.railway.app` |
| 2026-02-28 ~21:23 | Tested the wrong URL via curl — confirmed it returns Railway 404 ("Application not found") |
| 2026-02-28 ~21:23 | Tested the correct URL via curl — confirmed lead submission works (HTTP 201) |
| 2026-02-28 ~21:24 | Searched the `Grins_irrigation` repo — found the wrong URL hardcoded in `lib/leadApi.ts` line 45 |
| 2026-02-28 ~21:25 | Fixed the URL in `lib/leadApi.ts` |
| 2026-02-28 ~21:25 | Committed and pushed to `kirillDR01/Grins_irrigation` main branch |
| 2026-02-28 ~21:26 | Submitted a test lead via curl directly to the correct backend — HTTP 201 success |
| 2026-02-28 ~21:27 | Verified the test lead appears in the admin dashboard Leads tab |
| 2026-02-28 ~21:28 | Awaiting Vercel redeploy of the landing page to complete the fix for browser-based form submissions |
