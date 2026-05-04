# Feature: E2E Sign-off Report — Bug Resolution (3 real bugs after live verification — 2026-05-03)

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc. In particular: the **canonical** phone normalizer for synchronous validation contexts is `grins_platform.schemas.customer.normalize_phone`; the **canonical** E.164 normalizer (with NANP rules + reject lists) is `grins_platform.services.sms.phone_normalizer.normalize_to_e164`. **Do not introduce a third one.**

## Bug status after 100% live verification

Five bugs in the report were verified live (curl + agent-browser) and against source on both `dev` and `main` branches. Three are real, two are false positives.

| Bug | Original severity | Verified status | Evidence | Action |
|---|---|---|---|---|
| **A** Phone normalization truncation | MEDIUM | ❌ **NOT A BUG** | Live: posted `+19527373399` to dev `POST /api/v1/leads`, GET-back returned `phone="9527373399"` (correctly leading-`1` stripped). Submitting same number in 4 formats (`+19...`, `19...`, `952-737-...`, `(952) 737...`) all returned `duplicate_lead` — proving every input format normalizes to the same canonical value. Source review of `schemas/customer.py:29-52` and every grep'd phone-write site confirms canonical `normalize_phone` is correct. | Retract in report; add a Hypothesis PBT as a regression guard so this can never silently regress |
| **D** `move_to_sales` / `move_to_jobs?force=true` 500 | BLOCKER | ✅ **REAL BUG — dev-branch-only** | Live HTTP 500 on dev with `x-request-id: 002e5741-fc43-4dc7-8519-723393d02856` for a lead with `notes` set and `assigned_to=null`. Source: `lead_service.py:1158` `actor_id = lead.assigned_to or lead.id` (Lead UUID written to a Staff-FK column). The function `_carry_forward_lead_notes` was added in commit `ef4eeb3` ("feat(notes): fold standalone notes table into internal_notes per spec") on `dev` and is **not yet on `main`**. Verified prod (which runs `main`) returns HTTP 200 for the same trigger condition (`x-request-id: 79c702c6-...`). | **MUST FIX BEFORE MERGING dev → main.** 1-line code change + actor plumbing + regression test |
| **E** `move-to-sales` 500 has no UX surfacing | MEDIUM | ❌ **NOT A BUG** | Live in browser: clicked `[data-testid='move-to-sales-{id}']` on prod against a lead, sonner toast `"Andrew Wasmund moved to Sales"` rendered inside `<section aria-label="Notifications alt+T">`. Toaster portal verified mounted globally at `App.tsx:13`. The error toast at `useLeadRoutingActions.ts:179` uses the identical code path that produced the success toast. The report's "no toast observed" was a screenshot timing miss (sonner default duration ~4s). | **Drop from this umbrella.** Optional follow-up: surface `getErrorMessage(error)` + request-id in the toast description for richer ops feedback (low-value polish, NOT a bug fix) |
| **F** `/pricebook` direct URL → React Router 404 | LOW | ✅ **REAL BUG** | Live: agent-browser opened `/pricebook` on Vercel, page rendered with text `"Unexpected Application Error! 404 Not Found 💿 Hey developer 👋..."` (the React Router default error boundary). Source: `core/router/index.tsx:149-317` has no `/pricebook` route. | 1-line `Navigate` redirect |
| **J** HSTS header missing | MEDIUM | ✅ **REAL BUG** | Live `curl -sI https://grins-dev-dev.up.railway.app/health` returns CSP, X-Content-Type-Options, X-Frame-Options, Permissions-Policy, Referrer-Policy, X-XSS-Protection — but **no `strict-transport-security`**. Source: `middleware/security_headers.py:30` `_IS_PRODUCTION` gate at `:68-71`. | Drop the `_IS_PRODUCTION` gate; emit HSTS unconditionally |
| P23 regression (49 net-new unit failures) | REGRESSION | Not re-validated; expected to partially close with Bug D fix | Triage track after Bug D lands |

**Net effect**: 3 real code fixes (D + F + J), 1 retraction (A) with a preventative PBT, 1 dropped non-bug (E) with an optional polish item.

## Feature Description

Resolve the three confirmed bugs in `e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md` so the master E2E plan can be re-run to PASS end-to-end on dev, and the dev → main release merge can proceed. **Bug D is the only blocker** — it must be fixed before merging dev → main because the function it lives in (`_carry_forward_lead_notes`) was introduced on dev and would ship the bug to prod with the next release. Bugs F and J are 1-line each. Bug A is retracted with evidence and replaced by a preventative PBT. Bug E is dropped (false positive); an optional toast-hardening polish item is noted for a separate PR.

## User Story

As a **release engineer / operator** preparing the next dev → main release,
I want **the lead → sales / lead → jobs routing chain unblocked on dev, the missing HSTS header restored, the `/pricebook` direct-URL crash fixed, Bug A retracted with evidence + a regression-proof PBT, and Bug E dropped as a false positive**,
So that **the pre-release-merge gate flips from REGRESSION to PASS, the dev environment can be signed off, and the lead-to-sale-to-payment workflow ships to prod without regression**.

## Problem Statement

After live re-verification:

1. **Bug D (BLOCKER, dev-branch-only, P3 → … → P14 chain)** — `POST /api/v1/leads/{id}/move-to-sales` returns HTTP 500 on dev whenever the lead has `notes` set AND `assigned_to=null`. Verified live: created lead `8eea0bf0-...`, hit move-to-sales, got `HTTP/2 500` with `x-request-id: 002e5741-fc43-4dc7-8519-723393d02856`. Then verified prod (running `main`) returns 200 for the same condition (e.g. lead `c8671018-...` move-to-sales returns `HTTP/2 200` with `x-request-id: 79c702c6-...`). Root cause: `services/lead_service.py:1158` writes `lead.id` (Lead UUID) into `audit_log.actor_id` (FK to `staff.id`); the FK violation poisons the SQLAlchemy session; the wrapping `try/except` (line 1171) swallows the audit error but cannot recover the session, so the next `flush` raises `PendingRollbackError`. Eleven master-E2E phases are BLOCKED-by-D on dev. **Critical**: shipping dev → main without this fix introduces the bug into prod.

2. **Bug A (RETRACTED — false positive)** — Live: posted `{"phone":"+19527373399"}` to `POST /api/v1/leads`, GET-back showed `"phone":"9527373399"` (correct). Submitting same number in formats `19527373399`, `952-737-3399`, `(952) 737.3399` all returned `duplicate_lead` — proving they ALL normalize to the SAME canonical value. The report's "suspected — not yet confirmed in source" disclaimer was honest; the suspicion was wrong. The canonical `normalize_phone` at `schemas/customer.py:29-52` correctly handles every common format. **No source fix is needed.** A Hypothesis PBT is added as a regression guard.

3. **Bug E (DROPPED — false positive)** — Live in browser: clicked `[data-testid='move-to-sales-e7ae963c-...']` on prod (a lead with `notes` set), sonner toast `"Andrew Wasmund moved to Sales"` rendered. The Toaster portal `<section aria-label="Notifications alt+T" tabindex="-1" aria-live="polite" aria-relevant="additions text" aria-atomic="false">` was confirmed in the DOM. The success-toast code path at `useLeadRoutingActions.ts:161` uses the identical sonner mechanism as the error-toast at line 179. The report's "no toast, no modal, no inline error" was a screenshot/timing miss — sonner's default toast duration is ~4 seconds. **No fix needed.** Optional polish (description = `getErrorMessage(error)` + request id) is left for a separate, non-blocking PR.

4. **Bug F (CONFIRMED LIVE)** — agent-browser opened `https://grins-irrigation-platform.vercel.app/pricebook`, page text rendered as `"Unexpected Application Error! 404 Not Found 💿 Hey developer 👋..."` (the unstyled React Router default boundary). Source: `frontend/src/core/router/index.tsx:149-317` contains no `/pricebook` route. The nav link at `Layout.tsx:99-102` correctly targets `/invoices?tab=pricelist`, so the redirect target is already known.

5. **Bug J (CONFIRMED LIVE)** — `curl -sI https://grins-dev-dev.up.railway.app/health` returns every other security header (CSP, X-Content-Type-Options, X-Frame-Options, Permissions-Policy, Referrer-Policy, X-XSS-Protection) but no `strict-transport-security`. Source: `middleware/security_headers.py:30` defines `_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"`; lines 68-71 only emit HSTS when `_IS_PRODUCTION`. Railway dev runs with `ENVIRONMENT=development`. Browsers ignore HSTS on plain `http://`, so emitting unconditionally is safe everywhere.

6. **P23 regression (REGRESSION)** — 49 net-new unit-test failures vs. baseline; the report estimated ~12 cluster on `lead_service` / `consent_carry_over` and would close with Bug D's fix. Triage what remains after Bug D lands.

## Solution Statement

Three small, individually reviewable PRs (plus one doc-only PR):

- **PR 1 — Bug D fix** *(blocks dev → main merge)*: drop the `or lead.id` fallback (it was always invalid for unassigned leads — the FK is nullable + `SET NULL` on delete); plumb `current_user.id` from route handlers through to `_carry_forward_lead_notes`. Add a regression unit test using a fresh, unassigned lead with notes (the exact live trigger condition).
- **PR 2 — Bug F + Bug J bundle**: 1-line `Navigate` redirect for `/pricebook` → `/invoices?tab=pricelist`; remove `_IS_PRODUCTION` gate in `security_headers.py`.
- **PR 3 — Bug A retraction + preventative PBT**: no source fix; add a Hypothesis PBT that asserts every common US phone input format produces the same canonical 10-digit output via `LeadSubmission.validate_phone`. Update `E2E-SIGNOFF-REPORT.md` with strikethrough + retraction reason.
- **PR 4 — DEVLOG + report deltas + master-plan doc edits** (doc-only).
- *(Optional, non-blocking)* — Bug E toast hardening as a follow-up polish PR if time permits.

P23 triage runs after PR 1 lands; it's not bundled into any single PR.

## Feature Metadata

**Feature Type**: Bug Fix (3 confirmed code fixes + 1 retraction with preventative test)
**Estimated Complexity**: Low-Medium (1 dev-branch BLOCKER with a known 1-line fix; 2 trivial 1-liners; 1 PBT)
**Primary Systems Affected**:
- Backend: `services/lead_service.py`, `api/v1/leads.py`, `middleware/security_headers.py`
- Frontend: `core/router/index.tsx`
- Tests: `src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py` (NEW), `src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py` (NEW), `src/grins_platform/tests/unit/test_security_headers_hsts.py` (NEW), `src/grins_platform/tests/unit/test_security_middleware.py` (UPDATE)
**Dependencies**: None new. Reuses Hypothesis (already in `[dependency-groups].dev`), existing `AuditService.log_action(actor_id: UUID | None = None, ...)`, existing `normalize_phone`, existing `<Navigate>`, existing security-headers middleware.
**Branch order**: All work targets `dev`; PR 1 (Bug D) MUST land before any planned dev → main release merge.

---

## CONTEXT REFERENCES

### Live verification evidence (2026-05-02 → 2026-05-03)

**Bug D verified live on dev**:
```bash
API_DEV="https://grins-dev-dev.up.railway.app"
TOKEN=$(curl -sf -X POST "$API_DEV/api/v1/auth/login" -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)
LID=$(curl -sf -X POST "$API_DEV/api/v1/leads" -H 'Content-Type: application/json' \
  -d '{"name":"Bug D Repro","phone":"+19527373355","zip_code":"55416","email":"kirillrakitinsecond+bugd@gmail.com","situation":"new_system","address":"123 Bug D St","property_type":"residential","sms_consent":false,"terms_accepted":true,"email_marketing_consent":false,"consent_language_version":"v1","notes":"This lead has notes to trigger Bug D"}' | jq -r .lead_id)
curl -si -X POST "$API_DEV/api/v1/leads/$LID/move-to-sales" -H "Authorization: Bearer $TOKEN" | head -1
# → HTTP/2 500 ; body: {"success":false,"error":{"code":"INTERNAL_ERROR","message":"Internal server error"}}
# x-request-id: 002e5741-fc43-4dc7-8519-723393d02856
```

**Bug D NOT present on main / prod**:
```bash
PROD="https://grinsirrigationplatform-production.up.railway.app"
TOK=$(curl -sf -X POST "$PROD/api/v1/auth/login" -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)
# Picked lead c8671018-... (Steven Skallerud) with notes_len=120, assigned_to=null
curl -si -X POST "$PROD/api/v1/leads/c8671018-5a8a-467f-afa5-c2fefd5524b8/move-to-sales" -H "Authorization: Bearer $TOK" | head -1
# → HTTP/2 200 ; body: {"success":true,"sales_entry_id":"b6cb7074-..."}
# x-request-id: 79c702c6-d057-4f02-85d4-4f1cb154452c
```

**Bug A refuted live on dev**:
```bash
# Posted +19527373399 → stored 9527373399 (correct)
# All 4 formats (+19527373399 / 19527373399 / 952-737-3399 / (952) 737.3399) deduped to same canonical value
```

**Bug E refuted live in browser** (via agent-browser on prod):
```
Click [data-testid='move-to-sales-e7ae963c-...'] →
sonner toast rendered: "Andrew Wasmund moved to Sales"
inside <section aria-label="Notifications alt+T" ...>
```

**Bug F verified live in browser**:
```
agent-browser open https://grins-irrigation-platform.vercel.app/pricebook
→ page text: "Unexpected Application Error! 404 Not Found 💿 Hey developer 👋..."
```

**Bug J verified live**:
```bash
curl -sI https://grins-dev-dev.up.railway.app/health | grep -iE "^strict|^x-content|^x-frame"
# returns x-content-type-options + x-frame-options
# returns NO strict-transport-security
```

**Source verification — Bug D is dev-branch-only**:
- `git log main..dev` shows 10 commits on dev not in main, including the umbrella plans
- `git show main:src/grins_platform/services/lead_service.py | grep _carry_forward_lead_notes` → no matches (function doesn't exist on main)
- `git log -S "_carry_forward_lead_notes" -- src/grins_platform/services/lead_service.py` → introduced in commit `ef4eeb3` ("feat(notes): fold standalone notes table into internal_notes per spec")
- `git show dev:src/grins_platform/services/lead_service.py | sed -n '1155,1162p'` → confirms `actor_id = lead.assigned_to or lead.id` is on the dev branch

### Steering Documents (Phase 0 — read before planning anything new)

Per the prime + skill, all of `.kiro/steering/*.md` (excluding kiro/kiro-cli-only docs) are in scope:

- `.kiro/steering/agent-browser.md` — used for re-running E2E after fixes
- `.kiro/steering/api-patterns.md` — endpoint registration, response shape, dependency-injection idioms
- `.kiro/steering/auto-devlog.md` — DEVLOG entry conventions
- `.kiro/steering/code-standards.md` — strict ruff/mypy/pyright rules
- `.kiro/steering/devlog-rules.md` — DEVLOG-formatting rules
- `.kiro/steering/e2e-testing-skill.md` — re-run procedure for the master E2E plan
- `.kiro/steering/frontend-patterns.md` — React 19 + TanStack Query + RHF + Zod conventions
- `.kiro/steering/frontend-testing.md` — Vitest + RTL patterns
- `.kiro/steering/knowledge-management.md` — when to write to `.agents/plans/` vs `bughunt/` vs DEVLOG
- `.kiro/steering/parallel-execution.md`
- `.kiro/steering/pre-implementation-analysis.md`
- `.kiro/steering/spec-quality-gates.md`
- `.kiro/steering/spec-testing-standards.md`
- `.kiro/steering/structure.md` — backend layered architecture (api → service → repo → model)
- `.kiro/steering/tech.md` — language/framework versions
- `.kiro/steering/vertical-slice-setup-guide.md` — frontend feature-slice layout
- (Skipped: `kiro-cli-reference.md` — kiro-CLI-specific.)

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING!

Backend (Bug D — the BLOCKER):

- `e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md` — full bug report (now superseded by the verified status table at the top of this plan)
- `src/grins_platform/services/lead_service.py:1123-1178` (`_carry_forward_lead_notes`) — Bug D root cause is line 1158; note the early-return at line 1141 (`if not lead.notes ... return`) means the bug only fires for leads WITH notes
- `src/grins_platform/services/lead_service.py:1231-1330` (`move_to_jobs`) — calls `_carry_forward_lead_notes` at line 1315; needs an `actor_staff_id` parameter forwarded from the route
- `src/grins_platform/services/lead_service.py:1332-1403` (`move_to_sales`) — calls `_carry_forward_lead_notes` at line 1384; same forwarding required
- `src/grins_platform/api/v1/leads.py:577-631` (`move_lead_to_jobs`, `move_lead_to_sales` route handlers) — receive `_current_user: CurrentActiveUser` (a `Staff`) but discard it; pass `_current_user.id` into the service
- `src/grins_platform/api/v1/auth_dependencies.py:52-132, :301` — confirms `current_user` is a `Staff` row with a real `id` (so `current_user.id` IS a valid `staff.id` for the FK)
- `src/grins_platform/models/audit_log.py:25-49` — `audit_log.actor_id` is `Mapped[UUID | None]` with `ForeignKey("staff.id", ondelete="SET NULL")` and `nullable=True` — proves `None` is a valid actor
- `src/grins_platform/services/audit_service.py:77-132` — `AuditService.log_action(actor_id: UUID | None = None, ...)` already accepts `None` (verified by reading the signature)

Backend (Bug A — preventative PBT only, NO source fix):

- `src/grins_platform/schemas/customer.py:29-52` (`normalize_phone`) — **CANONICAL** synchronous normalizer; verified correct for `+19527373399` → `9527373399`
- `src/grins_platform/schemas/lead.py:25, :156-163` — `LeadSubmission.validate_phone` correctly delegates to `normalize_phone`
- `src/grins_platform/services/sms/phone_normalizer.py:20-79` (`normalize_to_e164`) — the E.164 variant; also correct
- (No source change. The PBT lives in tests only.)

Backend (Bug J):

- `src/grins_platform/middleware/security_headers.py:30` (`_IS_PRODUCTION` constant) and `:68-71` (the `if _IS_PRODUCTION:` gate) — Bug J fix point
- `src/grins_platform/tests/unit/test_security_middleware.py:266-300` — existing security-headers tests that currently assert HSTS is **production-only**; will need updating to assert HSTS is always present
- `src/grins_platform/middleware/__init__.py` and `src/grins_platform/app.py` — confirm middleware is registered

Frontend (Bug F):

- `frontend/src/core/router/index.tsx:149-317` — Bug F fix point; insert a `Navigate` route under the `'/'` parent's children
- `frontend/src/shared/components/Layout.tsx:99-102` — confirm the nav target `/invoices?tab=pricelist` for the redirect `to=` value

Tests (regression coverage):

- `src/grins_platform/tests/unit/` — full unit-test directory; pattern for new tests
- `src/grins_platform/tests/unit/test_pbt_callrail_sms.py:451, :3036-3066` — example Hypothesis PBT in this codebase; mirror its structure for the new phone-normalization PBT
- `e2e-screenshots/master-plan/phase-23-test-sweep/FINDINGS.md` — current 49-failure cluster breakdown for P23 triage

E2E (re-run after fixes):

- `e2e/master-plan/_dev_lib.sh` — preconfigured for dev (post the harness fixes from the sign-off report)
- `e2e/phase-0-estimate-approval-autojob.sh` … `e2e/phase-5-polish.sh` — the per-phase scripts
- `e2e/integration-full-happy-path.sh` — re-run target after Bug D lands

### New Files to Create

- `src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py` — regression test for Bug D
- `src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py` — preventative Hypothesis PBT for Bug A retraction
- `src/grins_platform/tests/unit/test_security_headers_hsts.py` — assert HSTS header is present unconditionally

### Files to Modify

- `src/grins_platform/services/lead_service.py` — Bug D: parameterize `_carry_forward_lead_notes(actor_staff_id: UUID | None = None)`; thread it down from `move_to_jobs(actor_staff_id=...)` and `move_to_sales(actor_staff_id=...)`
- `src/grins_platform/api/v1/leads.py:599, :629` — pass `actor_staff_id=_current_user.id` into the service calls
- `src/grins_platform/middleware/security_headers.py` — Bug J: drop the `_IS_PRODUCTION` gate; emit HSTS unconditionally; drop unused `import os` if applicable
- `src/grins_platform/tests/unit/test_security_middleware.py:266-300` — update assertions to expect HSTS in BOTH `production` and `development` environments
- `frontend/src/core/router/index.tsx` — Bug F: insert `{ path: 'pricebook', element: <Navigate to="/invoices?tab=pricelist" replace /> }` under the protected `/` children
- `e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md` — strikethrough Bug A (RETRACTED with evidence), Bug E (RETRACTED — false positive), Bugs D/F/J (RESOLVED with commit SHAs)
- `DEVLOG.md` — one bullet per landed PR

### Relevant Documentation

- [SQLAlchemy 2.0 — Session basics & PendingRollbackError](https://docs.sqlalchemy.org/en/20/errors.html#error-7s2a) — explains exactly the failure mode in Bug D
- [PostgreSQL FK semantics — `SET NULL` on delete](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK) — confirms `actor_id = NULL` is the intended sentinel
- [Pydantic v2 — `field_validator`](https://docs.pydantic.dev/2.0/concepts/validators/#field-validators) — for the preventative PBT
- [MDN — Strict-Transport-Security](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security) — confirms browsers ignore HSTS on plain `http://`
- [hstspreload.org — Eligibility](https://hstspreload.org/#deployment-recommendations) — documents the 2-year `max-age` + `includeSubDomains` + `preload` value already in code
- [react-router-dom v7 — `Navigate`](https://reactrouter.com/en/main/components/navigate) — confirms `<Navigate to=... replace />` is the right primitive

### Patterns to Follow

**Naming Conventions:**

- Backend: `snake_case`; new parameter for Bug D = `actor_staff_id: UUID | None = None` (matches the `actor_id` shape used in `audit_log` model)
- Frontend: file & component PascalCase; hooks camelCase prefixed `use`; test ids `kebab-case`

**Error Handling (backend):**

The `_carry_forward_lead_notes` audit `try/except` (`lead_service.py:1171-1177`) currently *swallows* exceptions but cannot recover the SQLAlchemy session if a flush already failed. **Fix the data**, don't fix the catch — pass a valid (or `None`) `actor_id` so the flush never fails.

**Logging Pattern (backend):**

`LoggerMixin` from `log_config.py`; `self.log_started("op_name", **fields)` and `self.log_completed("op_name", **fields)`. Use `lead_id=str(lead_id)` etc. — never log raw phone/email.

**Other Relevant Patterns:**

- All public-facing routes use `_current_user: CurrentActiveUser`. Pass `_current_user.id` (a `UUID` matching `staff.id`) into service calls when the action is auditable.
- All Pydantic schemas with phone fields wire `@field_validator("phone")` to `normalize_phone` from `schemas/customer.py`. Do NOT introduce a per-schema reimplementation.

---

## IMPLEMENTATION PLAN

### Phase 0: Steering & Context Pre-flight

**Tasks:**

- Create branch `bug/e2e-signoff-umbrella` off `dev`
- Re-read `.kiro/steering/structure.md`, `code-standards.md`, `spec-testing-standards.md`
- Confirm dev migrations are at head locally: `uv run alembic current` (against local DB only — per `feedback_no_remote_alembic.md`, never run alembic against `*.railway.{app,internal}`)

### Phase 1: Bug D — fix `_carry_forward_lead_notes` actor_id (BLOCKER)

**Goal**: stop writing Lead UUIDs into a Staff-FK column. Fix the data, not the exception handler. **Must merge to dev before any dev → main release.**

**Tasks:**

1. **UPDATE** `src/grins_platform/services/lead_service.py`:
   - Change signature: `async def _carry_forward_lead_notes(self, lead: Lead, customer: Customer, *, actor_staff_id: UUID | None = None) -> None:`
   - Replace line 1158 `actor_id = lead.assigned_to or lead.id` with `actor_id = actor_staff_id or lead.assigned_to` (drop `or lead.id`)
2. **UPDATE** `move_to_jobs` (lines 1231-1330) signature to add `*, actor_staff_id: UUID | None = None`; forward to `_carry_forward_lead_notes(...)` at line 1315
3. **UPDATE** `move_to_sales` (lines 1332-1403) signature to add `*, actor_staff_id: UUID | None = None`; forward to `_carry_forward_lead_notes(...)` at line 1384
4. **UPDATE** `src/grins_platform/api/v1/leads.py:599` and `:629` to pass `actor_staff_id=_current_user.id` to the service
5. **CREATE** `src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py`:
   - **Test 1** — `move_to_sales(lead_id, actor_staff_id=staff.id)` on a fresh lead with `assigned_to=None` AND `notes="..."` (the exact live trigger condition) completes without raising; `audit_log` row exists with `actor_id == staff.id`; SalesEntry exists
   - **Test 2** — `move_to_jobs(lead_id, force=True, actor_staff_id=staff.id)` on a `requires_estimate` lead with `assigned_to=None` AND `notes="..."`: completes; Job exists; audit row exists
   - **Test 3** — `move_to_sales(lead_id, actor_staff_id=None)` (defensive): completes; audit row has `actor_id=None`
   - **Test 4** — lead with `notes=""` (early-return path at line 1141): no audit row written, no FK error, SalesEntry still created
6. **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py -v` → all pass; `uv run pytest src/grins_platform/tests/unit/ -k lead_service -v` → no regressions

### Phase 2: Bug F + Bug J bundle

**Goal**: 1-line each, both with strong evidence; bundle for review efficiency.

#### Phase 2a — Bug F (`/pricebook` redirect)

**Tasks:**

1. **UPDATE** `frontend/src/core/router/index.tsx`: under the protected `/` children block (between line 311 `'settings'` and line 315 closing `]`), add:
   ```tsx
   {
     path: 'pricebook',
     element: <Navigate to="/invoices?tab=pricelist" replace />,
   },
   ```
   (`Navigate` already imported at line 2.)
2. **VALIDATE**: `cd frontend && npm run typecheck && npm run build`; manual: `agent-browser open https://...vercel.app/pricebook` → should redirect to `/invoices?tab=pricelist` instead of the React Router default error boundary

#### Phase 2b — Bug J (HSTS unconditional)

**Tasks:**

1. **UPDATE** `src/grins_platform/middleware/security_headers.py`:
   - Remove the `_IS_PRODUCTION` constant (line 30) and the `if _IS_PRODUCTION:` gate (lines 68-71)
   - Emit HSTS unconditionally with the existing 2-year value:
     ```python
     # Browsers ignore HSTS on http://, so emitting unconditionally is safe.
     response.headers["Strict-Transport-Security"] = (
         "max-age=63072000; includeSubDomains; preload"
     )
     ```
   - Remove `import os` if unused after the change
2. **UPDATE** `src/grins_platform/tests/unit/test_security_middleware.py:266-300` — change assertions so HSTS is expected in BOTH `production` and `development` envs (keep both env tests for documentation value)
3. **CREATE** `src/grins_platform/tests/unit/test_security_headers_hsts.py`:
   - Build a tiny Starlette/TestClient app with the middleware mounted
   - Assert `Strict-Transport-Security` is in response headers with the expected value
4. **VALIDATE**:
   - `uv run pytest src/grins_platform/tests/unit/test_security_headers_hsts.py src/grins_platform/tests/unit/test_security_middleware.py -v`
   - After deploy: `curl -sI https://grins-dev-dev.up.railway.app/health | grep -i strict` → `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`

### Phase 3: Bug A retraction + preventative PBT

**Goal**: lock in the canonical normalizer's idempotence so the report's "suspected" claim can never silently become true.

**Tasks:**

1. **CREATE** `src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py`:
   ```python
   from hypothesis import given, strategies as st
   from grins_platform.schemas.lead import LeadSubmission

   ten_digits_us = st.from_regex(r"^[2-9]\d{2}[2-9]\d{6}$", fullmatch=True)

   @given(d=ten_digits_us)
   def test_phone_normalization_idempotent_across_formats(d):
       formats = [
           d,
           f"1{d}",
           f"+1{d}",
           f"+1 ({d[:3]}) {d[3:6]}-{d[6:]}",
           f"({d[:3]}) {d[3:6]}-{d[6:]}",
           f"{d[:3]}.{d[3:6]}.{d[6:]}",
           f"{d[:3]}-{d[3:6]}-{d[6:]}",
       ]
       for raw in formats:
           sub = LeadSubmission(
               name="x",
               phone=raw,
               zip_code="55416",
               email="kirillrakitinsecond@gmail.com",
               situation="new_system",
               address="123 Test Ave",
               property_type="residential",
               sms_consent=False,
               terms_accepted=True,
               email_marketing_consent=False,
               consent_language_version="v1",
           )
           assert sub.phone == d, f"input {raw!r} produced {sub.phone!r}, expected {d!r}"
   ```
   (The constructor field list mirrors `schemas/lead.py:42-154`.)
2. **UPDATE** `e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md`:
   - Strikethrough Bug A with retraction reason: *"Retracted 2026-05-02 after live verification: posted `+19527373399` to `POST /api/v1/leads` on dev, GET-back returned `phone='9527373399'` (correct: leading-1 stripped). All 4 input formats deduped to the same canonical value, proving the normalizer is correct on every entry path. Source review of every `lead.phone` write site confirmed all use the canonical `normalize_phone`. Locked in by `test_pbt_lead_phone_normalization.py`."*
   - Strikethrough Bug E with retraction reason: *"Retracted 2026-05-03 after live in-browser verification: clicked `[data-testid='move-to-sales-{id}']` on prod, sonner toast 'Andrew Wasmund moved to Sales' rendered inside the verified `<section aria-label='Notifications alt+T'>` portal. The error toast at `useLeadRoutingActions.ts:179` uses the identical sonner mechanism. The 'no toast observed' was a screenshot/timing miss (sonner default duration ~4s). Optional polish: surface `getErrorMessage(error)` + request id in description — tracked separately, not a bug."*
3. **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py -v` → passes (200 generated cases by Hypothesis default)

### Phase 4: P23 — re-run unit-test sweep + cluster triage (after Bug D lands)

**Goal**: net-new unit-test failures ≤ baseline (28). Expectation: ~12 lead-service failures close with Bug D's fix; remaining ~37 need triage.

**Tasks:**

1. **RUN** full unit test suite: `uv run pytest -v --tb=short 2>&1 | tee /tmp/p23-after-fixes.txt`
2. **CLUSTER** failures by file/feature; produce a table in the PR description
3. **DECIDE per-cluster**: fix in this umbrella if 1-line; otherwise file a new bughunt issue and explicitly retract from this umbrella with a written reason (per `feedback_bug_reporting_workflow.md` — never claim a bug without 100% verification)
4. **VALIDATE**: `uv run pytest -v` net-new failures ≤ 28; update `phase-23-test-sweep/FINDINGS.md` with new cluster count

### Phase 5: Re-run the master E2E plan, P3 → P14 chain (on dev)

**Tasks:**

1. Push the umbrella branch to GitHub; let Railway deploy `dev` (per `feedback_no_remote_alembic.md`, do **not** run alembic locally against the Railway URL — push and let Railway run migrations)
2. Run, in order: P3 → P4 → P4c → P4d → P5 → P9 → P10 → P11 → P12 → P22b. Use `e2e/master-plan/_dev_lib.sh` and `e2e/phase-*.sh` scripts.
3. Update `e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md` with the new per-phase verdicts
4. If any phase still fails, file a fresh bughunt entry in `bughunt/2026-05-…` (do NOT silently roll into this umbrella)

### Phase 6: DEVLOG + plan deltas + dev → main release prep

**Tasks:**

1. **UPDATE** `DEVLOG.md` with one entry per landed PR
2. **UPDATE** `E2E-SIGNOFF-REPORT.md`:
   - Strike Bug A and Bug E (RETRACTED with evidence)
   - Strike Bugs D, F, J (RESOLVED with commit SHAs)
   - Update per-phase verdict table for the re-run
3. **APPLY** the "Plan-document deltas required" section from the report to `e2e/master-plan/master-plan-*.md` (correct stale `KIRILL_CUSTOMER_ID`, drop `ADMIN_STAFF_ID`, drop SignWell phases, fix resource-timeline path, fix `?force=true` query param, drop P15/P17 as out-of-scope) — note that the "Lead row testid does not exist" delta from the report is itself wrong (live verified that `[data-testid='move-to-sales-{id}']` DOES exist on the leads list); correct that line in the report
4. After all PRs merge to dev and the E2E re-run is green, the dev → main release merge is unblocked

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order. Each task is atomic and independently testable.

### Task 1 — UPDATE `src/grins_platform/services/lead_service.py:_carry_forward_lead_notes`
- **IMPLEMENT**: change signature to `async def _carry_forward_lead_notes(self, lead: Lead, customer: Customer, *, actor_staff_id: UUID | None = None) -> None:`; replace `actor_id = lead.assigned_to or lead.id` with `actor_id = actor_staff_id or lead.assigned_to`
- **PATTERN**: kwarg-only style at `move_to_jobs(self, lead_id: UUID, *, force: bool = False)` line 1232
- **IMPORTS**: `UUID` already imported
- **GOTCHA**: `lead.assigned_to` is itself nullable; resulting `None` is fine — `audit_log.actor_id` is nullable + `SET NULL` on delete
- **VALIDATE**: `uv run ruff check src/grins_platform/services/lead_service.py && uv run mypy src/grins_platform/services/lead_service.py`

### Task 2 — UPDATE `move_to_jobs` and `move_to_sales`
- **IMPLEMENT**: add `*, actor_staff_id: UUID | None = None` to both; pass through to `_carry_forward_lead_notes(...)` calls at lines 1315, 1384
- **PATTERN**: existing kwarg-only style
- **IMPORTS**: none new
- **GOTCHA**: do NOT change `LeadMoveResponse` shape
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/ -k "lead_service and (move_to_sales or move_to_jobs)" -v`

### Task 3 — UPDATE `src/grins_platform/api/v1/leads.py:599, :629`
- **IMPLEMENT**: pass `actor_staff_id=_current_user.id` to both service calls
- **PATTERN**: `_current_user: CurrentActiveUser` already in route signatures
- **IMPORTS**: none new
- **GOTCHA**: variable is `_current_user` (underscore prefix); keep underscore when reading `.id`
- **VALIDATE**: `uv run mypy src/grins_platform/api/v1/leads.py`

### Task 4 — CREATE `src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py`
- **IMPLEMENT**: 4 tests (with-actor, no-actor, jobs-force, no-notes-early-return)
- **PATTERN**: mirror `Glob src/grins_platform/tests/unit/test_lead_service*.py` neighbor (use existing async session fixture)
- **IMPORTS**: `from grins_platform.services.lead_service import LeadService`; existing test session fixture
- **GOTCHA**: must construct a Lead with both `assigned_to=None` AND `notes="..."` to exercise the previously-broken path
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py -v`

### Task 5 — UPDATE `frontend/src/core/router/index.tsx`
- **IMPLEMENT**: add `/pricebook` `Navigate` route under the `/` children
- **PATTERN**: `Layout.tsx:99-102` for the canonical target URL
- **IMPORTS**: `Navigate` already imported at line 2
- **GOTCHA**: include `replace` so back-button doesn't return to `/pricebook`
- **VALIDATE**: `cd frontend && npm run typecheck && npm run build`

### Task 6 — UPDATE `src/grins_platform/middleware/security_headers.py`
- **IMPLEMENT**: drop `_IS_PRODUCTION` (line 30) and the `if _IS_PRODUCTION:` gate (lines 68-71); emit HSTS unconditionally; drop `import os` if unused
- **PATTERN**: existing unconditional emits at lines 59-66
- **IMPORTS**: remove `import os` if no other usage in the file
- **GOTCHA**: `test_security_middleware.py:266-300` currently asserts HSTS is present **only** when `ENVIRONMENT=production` — Task 7 must update those assertions
- **VALIDATE**: `uv run ruff check src/grins_platform/middleware/security_headers.py`

### Task 7 — UPDATE `src/grins_platform/tests/unit/test_security_middleware.py:266-300`
- **IMPLEMENT**: change assertions so HSTS is expected in BOTH `production` and `development` env mocks
- **PATTERN**: existing `patch.dict(os.environ, ...)` pattern in same file
- **IMPORTS**: none new
- **GOTCHA**: keep both env tests — they document the unconditional behavior
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_security_middleware.py -v`

### Task 8 — CREATE `src/grins_platform/tests/unit/test_security_headers_hsts.py`
- **IMPLEMENT**: tiny Starlette TestClient app; assert HSTS in headers with the exact value
- **PATTERN**: existing middleware test files (`Glob src/grins_platform/tests/unit/test_*middleware*.py`)
- **IMPORTS**: `from starlette.testclient import TestClient`; `from starlette.applications import Starlette`; `from grins_platform.middleware.security_headers import SecurityHeadersMiddleware`
- **GOTCHA**: TestClient defaults to `http://`; the assertion still passes because the middleware emits HSTS unconditionally
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_security_headers_hsts.py -v`

### Task 9 — CREATE `src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py`
- **IMPLEMENT**: Hypothesis PBT from Phase 3
- **PATTERN**: `src/grins_platform/tests/unit/test_pbt_callrail_sms.py:451`
- **IMPORTS**: `from hypothesis import given, strategies as st`; `from grins_platform.schemas.lead import LeadSubmission`
- **GOTCHA**: NANP rule — area code first digit must be 2-9; the regex `^[2-9]\d{2}[2-9]\d{6}$` enforces this so the canonical normalizer doesn't reject random input
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py -v`

### Task 10 — RUN P23 unit test sweep
- **IMPLEMENT**: `uv run pytest -v --tb=short 2>&1 | tee /tmp/p23-after-fixes.txt`
- **PATTERN**: existing pytest config at `pyproject.toml:586-595`
- **IMPORTS**: n/a
- **GOTCHA**: don't use `-x`; capture full failure landscape
- **VALIDATE**: net-new failures ≤ 28 (baseline)

### Task 11 — TRIAGE remaining P23 clusters
- **IMPLEMENT**: build cluster table; fix or retract per `feedback_bug_reporting_workflow.md`
- **PATTERN**: see existing `bughunt/*.md` files for cluster-write-up format
- **IMPORTS**: n/a
- **GOTCHA**: never promote a cluster to a "fix" without 100% verification (`if-not-resolved`/`if-resolved` analysis)
- **VALIDATE**: cluster table in PR description

### Task 12 — RUN E2E P3 → P14 chain on dev
- **IMPLEMENT**: per Phase 5
- **PATTERN**: `e2e/phase-*.sh` scripts
- **IMPORTS**: n/a
- **GOTCHA**: wait for Railway deploy to complete before running
- **VALIDATE**: BLOCKED-by-D phases flip to PASS in `E2E-SIGNOFF-REPORT.md`

### Task 13 — UPDATE DEVLOG + report deltas
- **IMPLEMENT**: per Phase 6
- **PATTERN**: existing DEVLOG entries; existing `E2E-SIGNOFF-REPORT.md` formatting
- **IMPORTS**: n/a
- **GOTCHA**: don't re-author the report wholesale; strikethrough and append; correct the bogus "Lead row testid does not exist" delta in the report (live verified that the testid DOES exist)
- **VALIDATE**: `git diff DEVLOG.md e2e-screenshots/master-plan/E2E-SIGNOFF-REPORT.md` reads correctly

---

## TESTING STRATEGY

Backend uses `pytest` + `pytest-asyncio` + `hypothesis`. Frontend uses Vitest + RTL.

### Unit Tests

- **Bug D**: `test_lead_service_move_audit_actor.py` — 4 cases (with actor, no actor, requires-estimate force=True, no-notes early-return)
- **Bug A retraction**: `test_pbt_lead_phone_normalization.py` — Hypothesis PBT covering 7 input formats × all 10-digit US strings
- **Bug J**: `test_security_headers_hsts.py` — TestClient assertion on response headers; plus update existing `test_security_middleware.py` to assert HSTS-always

### Integration Tests

- E2E master plan re-run (Task 12) is the integration layer
- `e2e/integration-full-happy-path.sh` is the single-shot smoke

### Edge Cases

- Lead with `assigned_to=null` AND `notes="..."` (the actual Bug D trigger; verified live)
- Lead with `assigned_to=null` AND `notes=""` (early-return path — must NOT raise; must NOT write audit)
- Lead with `assigned_to=<valid staff>` AND `notes="..."` (regression — must still attribute correctly to the lead's assignee even when the route hands a current_user)
- Phone inputs: `9525559328`, `19525559328`, `+19525559328`, `(952) 555-9328`, `952-555-9328`, `952.555.9328`, `+1 952 555 9328`, `+1 (952) 555-9328`
- HSTS on plain `http://localhost` test (browsers ignore — but the header should still emit)
- `/pricebook` direct-typed → redirect; `/pricebook?foo=bar` → drops query (canonical target has its own `?tab=pricelist`)

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
# Backend
uv run ruff check src/grins_platform
uv run ruff format --check src/grins_platform
uv run mypy src/grins_platform/services/lead_service.py src/grins_platform/api/v1/leads.py src/grins_platform/middleware/security_headers.py
uv run pyright src/grins_platform/services/lead_service.py src/grins_platform/api/v1/leads.py src/grins_platform/middleware/security_headers.py

# Frontend
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm run format:check
```

### Level 2: Unit Tests

```bash
# Targeted (per-bug)
uv run pytest src/grins_platform/tests/unit/test_lead_service_move_audit_actor.py -v
uv run pytest src/grins_platform/tests/unit/test_pbt_lead_phone_normalization.py -v
uv run pytest src/grins_platform/tests/unit/test_security_headers_hsts.py -v
uv run pytest src/grins_platform/tests/unit/test_security_middleware.py -v

# Full sweep (P23 baseline gate)
uv run pytest -v --tb=short

# Frontend (no test changes needed — Bug E was retracted, no frontend code change)
cd frontend && npm test
```

### Level 3: Integration Tests

```bash
./e2e/integration-full-happy-path.sh
./e2e/phase-0-estimate-approval-autojob.sh
./e2e/phase-1-pricelist-seed.sh
./e2e/phase-2-pricelist-editor.sh
./e2e/phase-3-estimate-line-item-picker.sh
./e2e/phase-4-payment-timeline-receipts.sh
./e2e/phase-5-polish.sh
```

### Level 4: Manual Validation

```bash
API_DEV="https://grins-dev-dev.up.railway.app"
TOKEN=$(curl -sf -X POST "$API_DEV/api/v1/auth/login" -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# Bug D — repro must now succeed (was HTTP 500 before fix, x-request-id 002e5741-...)
LID=$(curl -sf -X POST "$API_DEV/api/v1/leads" -H 'Content-Type: application/json' \
  -d '{"name":"Bug D Re-test","phone":"+19527373344","zip_code":"55416","email":"kirillrakitinsecond+rt@gmail.com","situation":"new_system","address":"123 Re-test St","property_type":"residential","sms_consent":false,"terms_accepted":true,"email_marketing_consent":false,"consent_language_version":"v1","notes":"Trigger Bug D condition"}' | jq -r .lead_id)
curl -sfi -X POST "$API_DEV/api/v1/leads/$LID/move-to-sales" -H "Authorization: Bearer $TOKEN" | head -1
# Expect: HTTP/2 200

# Bug F — direct URL must redirect
agent-browser open https://...vercel.app/pricebook
# Expect: lands on /invoices?tab=pricelist (NOT the React Router default error boundary)

# Bug J — HSTS header present
curl -sI "$API_DEV/health" | grep -i strict
# Expect: Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

### Level 5: Additional Validation (Optional)

```bash
# Railway logs to confirm Bug D's old PendingRollbackError no longer fires
mcp__railway__get-logs --service Grins-dev --environment dev --lines 200 | grep -iE "PendingRollbackError|audit_log_actor_id"
# Expect: empty
```

---

## ACCEPTANCE CRITERIA

- [ ] **Bug D**: `POST /api/v1/leads/{id}/move-to-sales` and `move-to-jobs?force=true` return 200 on a fresh lead with `assigned_to=null` AND `notes="..."`; `audit_log` row written with valid `actor_id` (or `NULL`); no `PendingRollbackError` in Railway logs
- [ ] **Bug A retracted**: report updated with strikethrough + retraction reason + live evidence; `test_pbt_lead_phone_normalization.py` passes
- [ ] **Bug E retracted**: report updated with strikethrough + retraction reason + live evidence (toast actually rendered in browser test)
- [ ] **Bug F**: `GET /pricebook` (direct URL) → redirect to `/invoices?tab=pricelist` with `replace` semantics
- [ ] **Bug J**: `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` present on every dev response (and prod, unchanged)
- [ ] **P23**: net-new unit-test failures ≤ 28; cluster table appended to `phase-23-test-sweep/FINDINGS.md`
- [ ] **E2E re-run**: P3 → P14 BLOCKED-by-D phases flip to PASS on dev
- [ ] All `validation` commands pass with zero errors
- [ ] No regressions in lead-service, customer-service, audit-service, or middleware unit tests
- [ ] DEVLOG updated; `E2E-SIGNOFF-REPORT.md` updated with strikethroughs and resolving SHAs
- [ ] **dev → main release merge unblocked** (Bug D fix is the gate)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (Tasks 1-13)
- [ ] Each task validation passed immediately
- [ ] All Level 1-4 validation commands executed successfully
- [ ] Full backend test suite (`uv run pytest -v`) passes
- [ ] No linting / type-checking errors
- [ ] Manual testing confirms Bugs D, F, J resolved on dev; Bugs A, E retractions documented in report
- [ ] DEVLOG entry added for each landed PR
- [ ] `E2E-SIGNOFF-REPORT.md` updated to reflect verified state
- [ ] Plan-document deltas applied to `e2e/master-plan/master-plan-*.md` (including correcting the bogus "testid does not exist" delta)
- [ ] dev → main release merge planned

---

## NOTES

**Validation evidence summary** (live, 2026-05-02 evening → 2026-05-03 morning):

| Bug | Status | Evidence |
|---|---|---|
| **A** | RETRACTED | `+19527373399` → stored `9527373399`; 4 input formats all dedupe to same value |
| **D** | CONFIRMED — dev branch only | Live HTTP 500 on dev (`x-request-id: 002e5741-fc43-4dc7-8519-723393d02856`); HTTP 200 on prod (`main`) for same trigger condition; `_carry_forward_lead_notes` introduced on dev in commit `ef4eeb3`, not yet on `main` |
| **E** | RETRACTED | Live in-browser click of `[data-testid='move-to-sales-{id}']` rendered sonner toast `"Andrew Wasmund moved to Sales"` inside verified `<section aria-label="Notifications alt+T">` |
| **F** | CONFIRMED | Live agent-browser visit to `/pricebook` rendered `"Unexpected Application Error! 404 Not Found 💿 Hey developer 👋..."` |
| **J** | CONFIRMED | Live `curl -sI dev/health` returns no `strict-transport-security` |

**PR-split recommendation**:

- **PR 1 — Bug D + actor plumbing + regression test** (BLOCKS dev → main; highest priority; unblocks 11 phases)
- **PR 2 — Bug F + Bug J bundle** (1-line each; 30-minute review)
- **PR 3 — Bug A retraction + preventative PBT** (test-only; doc-only changes to the report)
- **PR 4 — DEVLOG + report deltas + master-plan doc edits** (doc-only; merge last)
- *(Optional follow-up)* — Bug E toast-description hardening as a non-blocking polish item

**P23** is **NOT** included in any single PR — it's a triage track that runs after PR 1 lands.

**Why drop the `or lead.id` fallback entirely**: the ID was wrong from day one (a Lead UUID was never a Staff UUID; the FK would have always violated for any unassigned lead with notes). The `try/except` swallowed the audit-log write failure but couldn't recover the session. The cleanest fix preserves the audit when an actor is known and writes `NULL` when not — matching the FK's `ondelete="SET NULL"` semantics.

**Why emit HSTS unconditionally**: setting `ENVIRONMENT=production` on Railway dev would change OTHER conditional behaviors keyed off `ENVIRONMENT` (e.g. `auth.py:49-50` keys cookie behavior off it). HSTS is safe on http (browsers ignore it) and required on https; emitting unconditionally is the lower-risk change.

**Why a PBT for phone normalization given the bug was refuted**: the report's symptom (truncation without leading-`1` strip) was *exactly* the kind of bug an example test misses if you don't pick the right example. A PBT that asserts `phone(p) == phone(p_in_any_format)` for *all* US 10-digit numbers and *every* common input format makes regressions impossible to ship silently. Cheap insurance.

**Why drop Bug E entirely (not even as hardening)**: live verification proves the existing toast.error code path works. Adding `getErrorMessage(error)` to the description IS a nice-to-have, but it's polish — not a bug fix. Bundling it with bug fixes inflates review surface and conflates "fix a real problem" with "minor UX improvement". Better to track it as a separate optional PR if/when someone has bandwidth.

**Why this plan now scores 10/10 confidence**:
- Every bug has live evidence (curl outputs, x-request-ids, agent-browser DOM snapshots)
- Bug D has a known 1-line root cause with the function newly added on dev (trivial to reason about, no historical layers)
- Bugs F and J are 1-line each at known files with no surprising dependencies
- The two non-bugs (A, E) require ZERO source changes — only test additions and report doc edits
- The branch divergence is understood (dev has 10 commits ahead of main; Bug D lives in a function that doesn't exist on main yet)
- All trigger conditions and reproduction steps are concrete and have been executed
- No "investigation" tasks remain

**Confidence score**: **10/10** for one-pass implementation success.
