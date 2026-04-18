# E2E Regression Test Report — ASAP Platform Fixes

**Date:** Auto-generated during Task 12 execution
**Status:** REQUIRES MANUAL VERIFICATION
**Reason:** Default test credentials (`admin` / `admin123`) rejected by running database. E2E tests require a seeded test database with known admin credentials.

## Environment Status

| Component | Status | Details |
|-----------|--------|---------|
| agent-browser | ✅ Installed | v0.7.6 |
| Backend (localhost:8000) | ✅ Running | Health check passes, Docker-based |
| Frontend (localhost:5173) | ✅ Running | Vite v7.3.1 |
| Test Credentials | ❌ Invalid | `admin@grins.com`/`admin123` rejected |
| Login Form | ⚠️ Note | Uses `data-testid='username-input'` (not `email-input`) |

## Prerequisites to Run E2E Tests

1. Seed the database with test admin user: `admin@grins.com` / `admin123`
   - OR set `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` environment variables
2. Ensure both servers are running (backend:8000, frontend:5173)
3. Run: `bash scripts/e2e-tests.sh` (all tests) or individual scripts below

## Task 12.1: Core E2E Scripts

| Script | What It Tests | ASAP Relevance |
|--------|--------------|----------------|
| `test-customers.sh` | Customer list, search, detail, duplicates, notes, photos, invoices, service times, payments | Validates customer search debounce (Req 1) doesn't break customer features |
| `test-leads.sh` | Lead list, city display, tags, bulk outreach, attachments, portal estimate, estimate creation, work-requests redirect | Validates lead deletion (Req 5), conversion (Req 6), manual creation (Req 7) don't break lead pipeline |
| `test-jobs.sh` | Job list, summary column, notes, status filter, column changes, due-by dates, financials | Validates job type editing (Req 8) doesn't break job features |
| `test-dashboard.sh` | Dashboard alerts, messages widget, pending invoices, job status categories | Validates auth changes (Req 3,4) don't break dashboard loading |

**Run command:** `bash scripts/e2e/test-customers.sh && bash scripts/e2e/test-leads.sh && bash scripts/e2e/test-jobs.sh && bash scripts/e2e/test-dashboard.sh`

## Task 12.2: Auth-Related E2E Scripts

| Script | What It Tests | ASAP Relevance |
|--------|--------------|----------------|
| `test-session-persistence.sh` | Login → wait → navigate → verify session active | Directly validates Req 3 (extended token duration) and Req 4 (session persistence) |
| `test-navigation-security.sh` | Sidebar nav, rate limiting, security headers, auth token storage, portal security | Validates auth changes don't break route protection or token handling |

**Run command:** `bash scripts/e2e/test-session-persistence.sh && bash scripts/e2e/test-navigation-security.sh`

**Key verifications for ASAP auth changes:**
- Session persists after 5s idle (configurable via `E2E_SESSION_WAIT_MS`)
- Auth token NOT stored in localStorage (cookie-only)
- All sidebar navigation items accessible with valid session
- Portal links work without auth (public routes)

## Task 12.3: Critical Flow E2E Scripts

| Script | What It Tests | ASAP Relevance |
|--------|--------------|----------------|
| `test-agreement-flow.sh` | Service package tiers, checkout redirect, customer agreements | Agreement flow is OFF-LIMITS for modification — must still work |
| `test-schedule.sh` | Calendar, drag-drop, appointments, staff workflow, payments, invoices, estimates | Validates auth changes don't break scheduling |
| `test-invoices.sh` | Invoice list, bulk notify, reminder status, PDF download | Validates auth changes don't break invoice operations |
| `test-invoice-portal.sh` | Portal invoice view, Pay Now button, no internal IDs | Validates portal access still works (public routes) |

**Run command:** `bash scripts/e2e/test-agreement-flow.sh && bash scripts/e2e/test-schedule.sh && bash scripts/e2e/test-invoices.sh && bash scripts/e2e/test-invoice-portal.sh`

## Task 12.4: Full Platform Smoke Test Checklist

Manual verification via agent-browser (or browser):

| # | Step | Expected Result | Status |
|---|------|----------------|--------|
| 1 | Login with valid credentials | Redirects to /dashboard | ⬜ |
| 2 | Navigate to /dashboard | Dashboard loads with widgets, no errors | ⬜ |
| 3 | Navigate to /customers | Customer list loads, search works | ⬜ |
| 4 | Navigate to /leads | Leads list loads, "Add Lead" button visible | ⬜ |
| 5 | Navigate to /jobs | Jobs list loads, job type editable | ⬜ |
| 6 | Navigate to /schedule | Calendar renders with appointments | ⬜ |
| 7 | Navigate to /invoices | Invoice list loads | ⬜ |
| 8 | Navigate to /sales | Sales/estimates page loads | ⬜ |
| 9 | Navigate to /accounting | Accounting page loads | ⬜ |
| 10 | Navigate to /marketing | Marketing page loads | ⬜ |
| 11 | Navigate to /settings | Settings page loads | ⬜ |
| 12 | Refresh page (F5) | Session persists, no redirect to login | ⬜ |
| 13 | Navigate to /work-requests | Redirects to /leads | ⬜ |

## Known Script Issues

1. **Login selector mismatch:** Scripts check for `data-testid='email-input'` first, but the actual login form uses `data-testid='username-input'`. The fallback chain (`[name='email']` → `input[type='email']` → `input:first-of-type`) also fails because the form uses text-type username input. Scripts should be updated to check `data-testid='username-input'` first.

2. **Strict mode violation:** The `input:first-of-type` fallback selector matches multiple elements (username, password, checkbox), causing agent-browser strict mode errors that crash scripts using `set -euo pipefail`.

## Recommendation

To enable E2E testing:
1. Create a database seed script that provisions test admin credentials
2. Update E2E scripts to check for `data-testid='username-input'` in the login fallback chain
3. Set `E2E_ADMIN_EMAIL` and `E2E_ADMIN_PASSWORD` environment variables matching a valid user
4. Run `bash scripts/e2e-tests.sh` for the full suite
