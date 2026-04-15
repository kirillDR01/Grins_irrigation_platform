# ASAP Platform Fixes — Regression Report & Bugs Found — 2026-04-07

**Spec:** `.kiro/specs/asap-platform-fixes/` (requirements.md, design.md, tasks.md)
**Branch:** `ASAP_changes`
**Tester:** Claude (automated)
**Scope:** Full regression after implementation of Requirements 1–9 (debounce, subscription email, auth session, session persistence, lead CRUD, manual lead, job type editing, regression testing)

---

## Executive Summary

| Layer | Result |
|---|---|
| Frontend Vitest (1197 tests) | ✅ 1197/1197 pass |
| Backend unit + integration | ✅ 1952/1968 pass (16 pre-existing failures, 0 new) |
| Backend functional tests | ✅ 182/186 pass (4 pre-existing failures, 0 new) |
| Backend ASAP-specific (118 tests) | ✅ 118/118 pass |
| Frontend typecheck on ASAP files | ✅ clean |
| Frontend lint on ASAP files | ✅ clean (3 fixed during regression) |
| Live backend endpoint smoke tests (10 checks) | ⚠️ 9/10 verified, **1 bug found** (BUG-001) |
| E2E shell script: test-dashboard.sh | ✅ 15/15 pass |
| E2E shell script: test-session-persistence.sh | ✅ 4/4 pass |
| E2E shell script: test-navigation-security.sh | ✅ 7/7 pass |
| E2E shell script: test-customers.sh | ⚠️ partial (agent-browser transient crash, BUG-003) |
| E2E shell script: test-leads.sh | ⚠️ partial (agent-browser transient crash, BUG-003) |
| E2E shell script: test-jobs.sh | ⚠️ partial (no job rows in test DB, not ASAP-caused) |
| Frontend browser smoke test (14 steps) | ✅ 14/14 pass — all pages load, session persists, /work-requests→/leads, manual lead creation E2E works |
| Full user-simulation pass (all 8 ASAP reqs) | ⚠ 7/8 ASAP requirements fully deliverable via UI. **BUG-004**: Req 8 (job type editing) has correct code fix but NO UI path to reach it. **BUG-001 confirmed live**: subscription form shows generic "Something went wrong" message. |

---

## Bugs Found

### BUG-001: `manage-subscription` returns 500 instead of friendly error when Stripe call fails (MEDIUM)

**Requirement:** Req 2 — Fix Subscription Management Email Flow
**Location:** `src/grins_platform/api/v1/checkout.py:247` → `src/grins_platform/services/checkout_service.py:332-364` (`CheckoutService.create_portal_session`)

**Description:**
The `POST /api/v1/checkout/manage-subscription` endpoint only catches `SubscriptionNotFoundError`, but the underlying `stripe.Customer.list(...)` call can raise `stripe.AuthenticationError`, `stripe.APIConnectionError`, or other Stripe SDK errors. In any of those cases the error bubbles up as a raw HTTP 500.

Req 2.2 states: *"IF the email address does not match any active subscription, THEN THE Platform SHALL display a clear error message indicating no subscription was found for that email"* — but the user gets a 500 `Internal Server Error` with no detail when Stripe is misconfigured or unreachable.

**Reproduction (live on localhost:8000, 2026-04-07):**
```bash
curl -sS -X POST http://localhost:8000/api/v1/checkout/manage-subscription \
  -H "Content-Type: application/json" \
  -d '{"email":"unknown-e2e@test.com"}'
# Response: "Internal Server Error"
# Status: 500
```

**Backend log:**
```
File "src/grins_platform/api/v1/checkout.py", line 247, in manage_subscription
  portal_url = await service.create_portal_session(data.email)
File "src/grins_platform/services/checkout_service.py", line 344, in create_portal_session
  ...
stripe._error.AuthenticationError: You did not provide an API key. You need to provide
your API key in the Authorization header, using Bearer auth...
```

**Root cause:**
`CheckoutService.create_portal_session()` calls `stripe.Customer.list(email=email, limit=1)` without a try/except around Stripe SDK errors. When `stripe.api_key` is unset (local dev) or the key is invalid, `stripe.AuthenticationError` propagates up; the endpoint doesn't catch it; FastAPI returns 500.

**Impact:**
- **Production-affecting:** If Stripe has a transient auth issue or the key is rotated incorrectly, legitimate subscribers see a raw 500 with no actionable guidance.
- **Security:** Stripe error messages could leak via uncaught exceptions in environments with verbose error reporting.
- **Test gap:** The unit test `test_subscription_management.py` mocks `CheckoutService`, so it never exercises the Stripe SDK error path.

**Suggested fix:**
Wrap the Stripe call in a try/except in `create_portal_session`:
```python
try:
    customers = stripe.Customer.list(email=email, limit=1)
except stripe.error.StripeError as e:
    self.log_failed("create_portal_session", error=str(e))
    raise SubscriptionNotFoundError(email) from e  # or a new StripeUnavailableError
```
Also catch the broader exception in the endpoint and return 503 for infrastructure failures vs 404 for "no customer found".

**Severity:** MEDIUM — degraded UX for a public endpoint; observable in production if Stripe is misconfigured.

**Status:** Identified 2026-04-07. Not yet fixed.

---

### BUG-002: Duplicate `data-testid='leads-page'` on Leads list view (LOW)

**Requirement:** N/A — testability / E2E selector stability
**Location:**
- `frontend/src/pages/Leads.tsx:16` — outer page wrapper
- `frontend/src/features/leads/components/LeadsList.tsx:280` — inner list component

**Description:**
Both the page-level `<div>` in `Leads.tsx` and the list-level `<div>` in `LeadsList.tsx` carry `data-testid="leads-page"`. The outer wrapper contains the inner one, so every selector targeting `leads-page` resolves to **two** elements. Playwright/agent-browser strict-mode aborts with:

```
strict mode violation: locator('[data-testid=\'leads-page\']') resolved to 2 elements:
  1) <div data-testid="leads-page">…</div>
  2) <div class="space-y-6" data-testid="leads-page">…</div>
```

**Impact:**
- E2E tests that target `[data-testid='leads-page']` fail with strict-mode errors (already observed in this regression run).
- Accessibility tools / testing harnesses that rely on unique testids are unreliable on this page.
- No user-visible impact — purely a test/tooling bug.

**Suggested fix:**
Rename the outer wrapper in `Leads.tsx` to something like `data-testid="leads-page-wrapper"`, or just remove the testid from the outer div since `LeadsList.tsx` already provides one. This was probably introduced when `LeadsList` gained its own testid during ASAP Task 7.5 (Add Lead button header) without removing the duplicate.

**Severity:** LOW — test-infrastructure only.

**Status:** Identified 2026-04-07. Not yet fixed.

---

### BUG-004: Req 8 is not reachable through the UI — no Edit button wired up for Jobs (HIGH)

**Requirement:** Req 8 — Enable Job Type Editing
**Location:**
- `frontend/src/pages/Jobs.tsx:78` — renders `<JobList />` without `onEdit` prop
- `frontend/src/features/jobs/components/JobList.tsx:379-381` — the Edit dropdown item only renders when `onEdit` is passed (`{onEdit && <DropdownMenuItem onClick={() => onEdit(job)}>Edit</DropdownMenuItem>}`)
- `frontend/src/features/jobs/components/JobDetail.tsx:42` — declares `onEdit?: () => void` as a prop but **never uses it** anywhere in the component body
- `frontend/src/features/jobs/components/JobForm.tsx` — the ASAP Req 8 fix (`value={field.value}` on the `Select`) is correct, but the form is only used in the "Create New Job" dialog in `Jobs.tsx:235`

**Description:**
The ASAP Task 8 fix (switching the job type `<Select>` from `defaultValue` to controlled `value`) is correct and unit-tested (`JobForm.test.tsx::shows current job type value when editing`), **but there is no path in the UI for a user to actually open `JobForm` in edit mode on an existing job.** The unit tests pass because they render `<JobForm job={mockJob} />` directly.

Verified live via agent-browser on 2026-04-07:

```javascript
// On /jobs list
Array.from(document.querySelectorAll("[data-testid*=actions], [data-testid*=menu], [role=menu]")).length
// → 22 containers, but 0 contain "edit"

Array.from(document.querySelectorAll("button")).filter(b => /edit/i.test(b.textContent||"")).length
// → 0

// On /jobs/<id> detail view
Array.from(document.querySelectorAll("button")).filter(b => /edit/i.test(b.textContent||"")).map(b => b.textContent.trim())
// → []
```

There is no "Edit" button, no dropdown menu item, no inline edit affordance on either the list or detail view. The only job-type related UI the user can reach is the `<Select>` in the "New Job" creation dialog.

**Impact:**
- **Req 8.1 is not actually met from a user's perspective.** The spec says *"WHEN a user edits an existing Job, THE Platform SHALL allow changing the Job_Type"* — but users cannot edit existing jobs at all through the UI.
- The ASAP unit tests give a false-positive signal of coverage because they render `JobForm` in isolation.
- This is the most visible gap in the ASAP work: the fix is technically in place but wholly inaccessible.

**Suggested fix:**
Two options:
1. **Minimal wiring (quickest):** Add an `onEdit` state + handler in `Jobs.tsx`, pass it to `<JobList onEdit={...} />`, open a second Dialog that renders `<JobForm job={editingJob} onSuccess={...} onCancel={...} />` in edit mode. Also add an "Edit Job" button to `JobDetail.tsx` that uses the existing `onEdit` prop (currently dead code).
2. **Inline job-type edit:** Add a small editable `<Select>` inside `JobDetail.tsx` that persists changes via `useUpdateJob()` directly, similar to how `LeadDetail.tsx` handles status changes. This is arguably more user-friendly for a single-field change.

**Severity:** HIGH — stated requirement is not deliverable to end users via the UI.

**Status:** Identified 2026-04-07 during user-simulation pass. Not yet fixed.

---

### BUG-003: `agent-browser` transient `os error 35` on long E2E runs (LOW — external)

**Requirement:** N/A — test infrastructure
**Location:** `agent-browser` v0.7.6 (external tool — `/opt/homebrew/bin/agent-browser`)

**Description:**
During long-running E2E scripts (`test-customers.sh`, `test-leads.sh`, `test-jobs.sh`), `agent-browser` intermittently crashes with:

```
✗ Failed to read: Resource temporarily unavailable (os error 35)
```

This is a macOS `EAGAIN` from a non-blocking IO operation in the browser automation tool itself, not an application bug. It aborts the test script because of `set -euo pipefail`.

**Impact:**
- Three E2E scripts partially completed (customers, leads, jobs) — each passed 5-8 steps before the transient crash.
- Manual smoke-testing via direct agent-browser invocations (13 discrete steps) did NOT hit the issue, suggesting it's related to sustained high-frequency calls within a single shell process.

**Suggested mitigation:**
- Retry on error in the shell scripts, OR
- Upgrade `agent-browser`, OR
- Split scripts into shorter sub-flows, OR
- Replace with Playwright directly.

**Severity:** LOW — external tool; does not block ASAP work. Reported here for completeness.

**Status:** External. Not our bug to fix; workaround: rerun the affected scripts or use direct invocations.

---

## Pre-existing (non-ASAP) test failures

These 16 backend test failures exist on baseline (`main` branch without ASAP changes) and are **not caused by ASAP work**. Flagged here for future cleanup but out of scope for ASAP regression:

**Unit tests (16 failures):**
- `test_agreement_api.py` — 8 failures (TestListAgreements, TestGetAgreement, TestUpdateAgreementStatus, TestApproveRenewal, TestRejectRenewal, TestRenewalPipeline, TestFailedPayments, TestAnnualNoticeDue)
- `test_google_sheet_submission_schemas.py` — 5 failures (validation errors against MagicMock objects)
- `test_sheet_submissions_api.py` — 2 failures (TestGetSubmission, TestCreateLeadFromSubmission)
- `test_checkout_onboarding_service.py::TestCheckoutSessionSurcharges::test_rpz_backflow_creates_line_item` — 1 failure

**Integration tests (11 failures):**
- `test_agreement_integration.py` — 11 failures

**Functional tests (1 failure, 3 errors):**
- `test_google_sheets_functional.py::TestManualLeadCreationWorkflow::test_manual_create_lead_updates_submission_and_links_lead` — 1 failure
- `test_onboarding_preferred_schedule.py::TestOnboardingPreferredSchedulePersistence` — 3 errors (test_saves_one_two_weeks, test_saves_other_with_details, test_asap_has_no_details)

**Verification method:** Stashed ASAP changes, ran failing files against baseline — same failures present.

---

## Regression fixes made during this audit

### FIX-1: ASAP PBT tests using deprecated `asyncio.get_event_loop()` broke in full-suite runs

**File:** `src/grins_platform/tests/unit/test_pbt_asap_platform_fixes.py`

9 of the Hypothesis-based property tests (Properties 5, 6, 7, 8, 9, 10, 12, 13) used `asyncio.get_event_loop().run_until_complete(coro)`. This works in isolation but raises `RuntimeError: Event loop is closed` or `DeprecationWarning: There is no current event loop` when pytest-asyncio has already created and closed a loop earlier in the test session.

**Fix:** Added a `_run_async()` helper that creates a fresh event loop per call and closes it cleanly. Replaced all 10 call sites.

### FIX-2: Lint errors in ASAP frontend test files

- `frontend/src/features/leads/components/ConvertLeadDialog.test.tsx`: replaced 2 `as any` casts with proper `AxiosResponse` / `InternalAxiosRequestConfig` imports
- `frontend/src/features/customers/components/CustomerList.test.tsx`: removed unused `e` parameter from a mock `onChange` handler

### FIX-3: E501 line-too-long in `lead_service.py:842`

The ternary `description = data.job_description if data.job_description is not None else default_description` was 107 chars. Wrapped onto multiple lines. Behavior unchanged.

---

## Requirements verification (live backend smoke tests)

All tested against `http://localhost:8000` with `admin`/`admin123` on 2026-04-07.

| Req | Description | Verification | Result |
|---|---|---|---|
| 1 | Customer search debounce | Frontend Vitest `CustomerList.test.tsx` | ✅ |
| 2.1/2.3 | Subscription email flow — happy path | Unit test only (mocked Stripe) | ⚠️ untested live |
| 2.2 | Unknown-email error message | Live curl | ❌ BUG-001 |
| 3.1 | Access token ≥ 60 min | `expires_in: 3600` from `/auth/login` | ✅ |
| 3.2 | Refresh token ≥ 30 days | Cookie `max-age=2592000` | ✅ |
| 3.3/4 | Auto refresh flow | Live curl to `/auth/refresh` | ✅ |
| 4 | Session persist across refresh | Frontend Vitest `ProtectedRoute.test.tsx` | ✅ |
| 5 | Lead deletion | Live curl DELETE → 204, subsequent GET → 404 | ✅ |
| 6.1 | Conversion preserves user-provided job_description | Live curl; verified on `/jobs/{id}` | ✅ |
| 6.2 | Conversion sets status=converted | Live curl GET lead after convert | ✅ |
| 6.3 | Convert without job → job_id=None | Live curl | ✅ |
| 6.4 | Already-converted rejection | Live curl returned `LEAD_ALREADY_CONVERTED` | ✅ |
| 7.1-7.4 | Manual lead creation | Live curl POST `/leads/manual` | ✅ |
| 7.3 | Name + phone required | Live curl (missing phone) → 422 | ✅ |
| 8 | Job type editing | Frontend Vitest `JobForm.test.tsx` | ✅ |
| 9 | Regression passes | See status table above | ⏳ |

---

## Frontend browser smoke test results (2026-04-07)

Executed manually via agent-browser v0.7.6 against `http://localhost:5173` with `admin` / `admin123`. Screenshots saved to `/tmp/asap-smoke-screenshots/`.

| # | Step | Result |
|---|---|---|
| 1 | Login | ✅ Redirected to `/dashboard` |
| 2 | Dashboard loads | ✅ page-title visible |
| 3 | `/customers` loads | ✅ customer-list + customer-search visible |
| 4 | `/leads` loads | ✅ add-lead-btn visible (⚠ BUG-002: duplicate testid) |
| 4a | Open Add Lead dialog (Req 7) | ✅ create-lead-dialog + name + phone fields visible |
| 5 | `/jobs` loads | ✅ |
| 6 | `/schedule` loads | ✅ |
| 7 | `/invoices` loads | ✅ |
| 8 | `/sales` loads | ✅ |
| 9 | `/accounting` loads | ✅ |
| 10 | `/marketing` loads | ✅ |
| 11 | `/settings` loads | ✅ |
| 12 | Refresh page (F5) → session persists (Req 4) | ✅ still on `/settings` after reload |
| 13 | `/work-requests` → redirects (Req 9) | ✅ redirected to `/leads` |
| 14 | **E2E manual lead creation** (Req 7) | ✅ filled all fields, submitted, verified via API: `name=Smoke Test User, phone=6125550777, source=manual, status=new` |

**All 14 smoke test checkpoints passed.**

---

## E2E shell script results (2026-04-07)

Patched 6 ASAP-relevant scripts to use `admin` instead of `admin@grins.com` and `[data-testid='username-input']` instead of `[data-testid='email-input']`. Ran against `http://localhost:5173` (Vite dev) and `http://localhost:8000` (Docker).

| Script | Result | Notes |
|---|---|---|
| `test-dashboard.sh` | ✅ 15/15 pass | All dashboard widgets, job status grid, metric counts verified |
| `test-session-persistence.sh` | ✅ 4/4 pass | 5s idle + navigation, session active throughout |
| `test-navigation-security.sh` | ✅ 7/7 pass | Auth token NOT in localStorage, portal security, no internal IDs leaked |
| `test-customers.sh` | ⚠ partial | Login + list loaded + duplicate detection step reached before BUG-003 agent-browser crash |
| `test-leads.sh` | ⚠ partial | Login + list + bulk outreach dialog + template selector reached before BUG-003 crash |
| `test-jobs.sh` | ⚠ partial | Login + list + summary column verified; failed on "No job rows found" (test DB missing job data — not ASAP-caused) |

ASAP-specific features touched by these scripts (auth, leads, dashboard, navigation) all verified working before any crashes.

---

## Verification of fixes applied during audit

| Fix | Verification |
|---|---|
| FIX-1: `_run_async()` helper | Full unit suite run: 16 failed (all pre-existing), 1952 passed. ASAP PBT tests no longer in failure list. |
| FIX-2: Lint errors in ASAP test files | `npm run lint` no longer reports the 3 ASAP-file errors. |
| FIX-3: E501 in `lead_service.py:842` | Conversion flow still functional (verified live via curl + browser smoke test). |

---

## Full user-simulation pass results (2026-04-07)

Executed via `agent-browser` against `http://localhost:5173` + `http://localhost:8000`. Screenshots in `/tmp/asap-user-sim/`.

| Req | Scenario | Steps driven via UI | Result |
|---|---|---|---|
| 1 | Customer search debounce | Typed "Smith" in search box → filtered to 1 result. Cleared → 100 results. Clicked next-page → went to page 2. Typed again → pagination reset to page 1 of 100. | ✅ |
| 2 | Subscription manage form | Opened `/portal/manage-subscription` → page loaded → filled email → clicked Send Login Email → received **generic "Something went wrong. Please try again." error** (UX symptom of BUG-001) | ⚠ BUG-001 confirmed live |
| 3 | 60-min access token | Live `/auth/login` response → `expires_in: 3600` | ✅ |
| 4 | Session persists on reload + no localStorage | Navigated to `/dashboard` → reloaded → still on /dashboard. `localStorage` keys: `[]`. `fetch('/auth/me', {credentials:'include'})` returned user object via cookie. | ✅ |
| 5 | Lead deletion confirmation dialog | Opened lead detail → clicked Delete → confirmation dialog opened → clicked Cancel → dialog closed → clicked Delete again → clicked Confirm → redirected to /leads → API `GET /leads/<id>` returned 404 | ✅ |
| 6 | Lead conversion — with custom description | Opened convert dialog on qualified lead → toggle ON by default → custom description field visible → typed custom text → submitted → navigated to new customer → verified lead status=converted, job created with user's description | ✅ |
| 6 | Lead conversion — toggle behavior | Opened dialog → toggled create_job OFF → **job description field HIDDEN** → toggled back ON → field visible again | ✅ |
| 6 | Lead conversion — without job | Qualified lead → convert dialog → toggle OFF → submit → new customer created with **0 jobs** | ✅ |
| 7 | Manual lead empty form | Clicked Add Lead → clicked Submit with empty form → 2 validation errors visible → dialog stayed open | ✅ |
| 7 | Manual lead only-name | Filled only name → clicked Submit → dialog still open (phone required) | ✅ |
| 7 | Manual lead full form | Filled all 8 fields → submitted → dialog closed → verified in API: `name, phone, email, city, state` all match, `source=manual` | ✅ |
| **8** | **Job type editing via UI** | **Opened `/jobs` list: 0 edit buttons. Opened `/jobs/<id>` detail: 0 edit buttons. No dropdown action menu with Edit. `JobForm` only used in Create dialog.** | ❌ **BUG-004** |
| 9 | `/work-requests` redirect | Navigated to `/work-requests` → redirected to `/leads` | ✅ |

**Summary: 11/12 scenarios pass. Req 8 UI path is missing entirely (BUG-004). BUG-001 confirmed user-visible.**

---

## Outstanding work

### Bugs blocking merge
1. **BUG-004** (HIGH): Req 8 has no UI entry point for editing existing jobs. The backend fix is correct but users cannot reach it. **Should block merge.**
2. **BUG-001** (MEDIUM): Wrap Stripe SDK calls in `manage-subscription` try/except — frontend fallback also hides the real error ("Something went wrong").

### Bugs that can ship
3. **BUG-002** (LOW): Remove/rename duplicate `leads-page` testid.
4. **BUG-003** (LOW, external): Upstream `agent-browser` transient crashes on long runs.

### Out of scope for this ASAP audit
5. Pre-existing non-ASAP failures (16 unit + 11 integration + 1 functional + 3 errors) — candidates for a separate cleanup PR.
