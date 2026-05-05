# Feature: e2e-signoff-portal-cron-2026-05-04 — F4-REOPENED, F7, F8

> **Source report**: `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/E2E-SIGNOFF-REPORT.md`
> **Candidate findings**: `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/CANDIDATE-FINDINGS.md`
>
> The following plan should be complete, but it's important that you validate documentation, codebase patterns, and task sanity before implementing.
>
> Pay special attention to the naming of existing utils, types, and models. Import from the right files.

---

## Feature Description

Three findings from the 2026-05-04 portal+cron focused E2E sign-off (run `run-20260504-184355-portal-cron`):

1. **F4-REOPENED (BLOCKER)** — Railway dev `PORTAL_BASE_URL` still resolves to a 9-day-stale Vercel preview alias (`frontend-git-dev-kirilldr01s-projects.vercel.app`), so every estimate and Stripe Payment Link email/SMS the platform has sent today contains a portal link that lands on the **marketing** site bundle rather than the React portal. Customers cannot Approve, cannot pay, cannot view their estimate. The deprecated-host warning *is* present in `email_config.py:68-79` (so we know the env is wrong on boot) — but the env var was never actually flipped in the Railway dashboard and **there is no automated guard that fails the boot or alerts when the variable is misconfigured**.
2. **F7 (MAJOR)** — `EstimateService.process_follow_ups()` exists (`estimate_service.py:1036-1131`) and `_schedule_follow_ups` writes 4 `estimate_follow_up` rows per sent estimate (Day 3 / 7 / 14 / 21), but no scheduled job ever calls `process_follow_ups`. Same shape as the F6 fix that landed `nudge_stale_sales_entries_job` at `background_jobs.py:1494-1501`. Today: rows accumulate forever; the documented Day 3/7/14/21 SMS nudge cadence is silently dead.
3. **F8 (INFORMATIONAL → SCOPED FIX)** — `/api/v1/inbox` only surfaces inbound rows from four UNIONed source tables (`job_confirmation_responses`, `reschedule_requests`, `campaign_responses`, `communications`). Standalone STOP / START replies that arrive **outside** a campaign or confirmation context are correctly written to `sms_consent_record` + audit log, but never appear in the operator's `/inbox` view. Product decision: surface them as a new `opt_outs` / `opt_in` triage class so admins can see consent flips in their day-to-day inbox without having to grep audit logs.

> **MANDATORY** for sign-off: every fix must be verified by **real browser E2E against the Vercel deployment** using the Vercel MCP tools (`mcp__vercel__web_fetch_vercel_url`, `mcp__vercel__get_runtime_logs`, `mcp__vercel__list_deployments`) **and** the `agent-browser` skill. **API-only verification is not acceptable** for F4-REOPENED — the bug is "200 status code, wrong bundle" and **only a real browser session driving the portal page can prove the customer-facing fix**.

## User Story

**F4-REOPENED**
> As a customer who receives an estimate email,
> I want clicking the portal link to land on the React estimate-review page with my line items and Approve / Reject buttons,
> so that I can complete the approval flow without calling the business.

**F7**
> As a salesperson at Grin's,
> I want customers who haven't approved their estimate to receive Day 3 / 7 / 14 / 21 SMS nudges automatically,
> so that I don't have to manually chase every stalled estimate and the documented promo cadence (SAVE10 from Day 14) actually fires.

**F8**
> As an operator triaging inbound SMS,
> I want standalone STOP and START replies to appear in `/inbox` with an `opt_outs` / `opt_ins` triage badge,
> so that I can see consent flips in the same surface as confirmation replies and campaign responses without grepping audit logs.

## Problem Statement

1. **F4-REOPENED**: customer-facing portal links from production-natural traffic (estimates, Stripe Payment Links, sales-pipeline nudges) land on a 9-day-old marketing-site bundle. The send-estimate flow is broken end-to-end. Sign-off blocker. Existing boot-time warning fires but does NOT enforce — the env stays wrong silently.
2. **F7**: `estimate_follow_up` rows pile up indefinitely; the Day 3 / 7 / 14 / 21 SMS follow-up cadence the product was designed around is dead. Customers who don't approve immediately get only the email-only sales-pipeline nudge, not the promised SMS sequence.
3. **F8**: standalone STOP / START replies write consent records but are invisible in the unified inbox, so an operator who wants to "see all inbound messages today" misses every plain-language consent flip.

## Solution Statement

**F4-REOPENED — three-layer fix**

1. **Operational** — flip `PORTAL_BASE_URL` on Railway dev (and prod, mirrored) to the canonical project alias `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`. No code change.
2. **Code-level boot guard** — upgrade `email_config.py` to **fail boot** in non-test environments when `PORTAL_BASE_URL` matches a deprecated host (env-aware: warn-only in `pytest`/`local`, hard-fail in `dev`/`staging`/`prod`). The current implementation only logs `error` — boot proceeds.
3. **Healthcheck** — add a tiny CI/cron check that hits `<PORTAL_BASE_URL>/portal/estimates/__healthcheck__` (fake token) and asserts the response **is** the React app (looks for `<title>Grin's Irrigation Platform`), not the marketing site. Run nightly in dev/staging.

**F7 — mirror F6**

1. **CREATE** `src/grins_platform/services/estimate_follow_up_job.py` containing a `process_estimate_follow_ups_job` async wrapper that constructs an `EstimateService` with all required deps (mirror `sales_pipeline_nudge_job.py:133-138`).
2. **REGISTER** the job in `background_jobs.register_scheduled_jobs()` with a 15-minute interval (Day 3/7/14/21 cadence has hours of slack — 15 min is fine).
3. **ADD** the new job id `process_estimate_follow_ups` to the `scheduler.jobs.registered` log line at `background_jobs.py:1503-1518`.
4. **TEST** end-to-end — unit + functional test that fires the job once and asserts (a) a `SCHEDULED` row whose `scheduled_at <= now()` flips to `SENT`, (b) an SMS was issued to the test number.

**F8 — extend inbox UNION**

1. **EXTEND** `InboxService` to also UNION `sms_consent_record` rows (or `audit_log` rows with `action in {consent.opt_out_sms, consent.opt_in_sms}`) and surface them as `source_table=consent` items.
2. **ADD** triage filters `opt_outs` and `opt_ins` (already wired conceptually in `_FILTER_OPT_OUTS` at `inbox_service.py:63` — currently filters by status string only; extend to actual rows).
3. **ADD** classification in `_classify_triage` for the new `consent` source — STOP is always `pending` (operator should see it), START is `handled` (informational).
4. **GATE** behind a feature flag `INBOX_SHOW_CONSENT_FLIPS=true` so we can land the schema change risk-free and flip on after browser verification.

## Feature Metadata

**Feature Type**: Bug Fix (3 distinct findings, bundled because all three came from the same E2E run and ship together as the next sign-off)
**Estimated Complexity**: Medium overall (F4 ops+code, F7 boilerplate cron, F8 inbox UNION extension)
**Primary Systems Affected**: Email/SMS portal links (F4); APScheduler + EstimateService (F7); InboxService UNION + frontend triage filter chips (F8)
**Dependencies**: Railway CLI (env flip); Vercel MCP server connection (browser E2E); APScheduler (already wired); SQLAlchemy async session

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE BEFORE IMPLEMENTING

**F4-REOPENED**
- `src/grins_platform/services/email_config.py` (lines 12-79) — `_DEPRECATED_PORTAL_HOSTS` list and the existing `log_configuration_status()` warning that today only logs (does NOT raise). This is what we'll harden.
- `src/grins_platform/services/estimate_service.py` (lines 83-130, 305-308, 940, 1067-1070) — every place that builds the portal URL. All three call sites read `self.portal_base_url`.
- `.env.example` (lines 148-160) — documents `PORTAL_BASE_URL` convention. Update guidance.
- `.agents/plans/e2e-signoff-2026-05-04-bugs-f2-f6.md` (entire F4 section, lines 78-396) — prior plan that *introduced* the deprecated-host warning. Read **before** changing `email_config.py` so we extend the existing pattern rather than replacing it.
- `src/grins_platform/tests/unit/test_email_config.py` — existing tests for the deprecated-host warning. Mirror this for the new boot-fail behavior.
- `src/grins_platform/api/v1/dependencies.py` (lines 261-264, 401-405) — `EmailSettings().portal_base_url` injection points. No change needed; just confirm the chain.

**F7**
- `src/grins_platform/services/background_jobs.py` (lines 1392-1518) — `register_scheduled_jobs()`. This is the file to edit.
- `src/grins_platform/services/background_jobs.py` (lines 56-58) — existing import of `nudge_stale_sales_entries_job`. The new import goes here.
- `src/grins_platform/services/sales_pipeline_nudge_job.py` (entire file, ~140 lines) — the F6 reference pattern. **Mirror this file's shape exactly** for the new job (LoggerMixin class, module-level singleton, `async def …_job()` wrapper).
- `src/grins_platform/services/estimate_service.py` (lines 53, 1036-1131, 1250-1282) — `FOLLOW_UP_DAYS`, `process_follow_ups`, `_schedule_follow_ups`. The new wrapper job must construct an `EstimateService` with `estimate_repository`, `portal_base_url`, **and `sms_service`** (line 1086: `if self.sms_service and phone:` — without it, every follow-up is `SKIPPED`).
- `src/grins_platform/api/v1/dependencies.py` (lines 240-271) — example of how to construct an `EstimateService`. **The cron job must construct its own SMSService instance** (mirror how `sales_pipeline_nudge_job.py:53` instantiates `EmailService` directly).
- `src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py` — F6 unit test pattern to mirror.
- `src/grins_platform/tests/functional/test_background_jobs_functional.py` (lines 295-310 area) — functional pattern with real DB session.
- `src/grins_platform/repositories/estimate_repository.py` (`get_pending_follow_ups`, `cancel_follow_ups_for_estimate`, `create_follow_up`) — read these to understand the row lifecycle.

**F8**
- `src/grins_platform/services/inbox_service.py` (entire file) — UNION-style aggregator. Specifically:
  - lines 37-50 (imports) — add `SmsConsentRecord` import
  - lines 103-110 (`_HANDLED_STATUSES`) — add a `"consent"` entry
  - lines 113-134 (`_classify_triage`) — extend for the consent source
  - lines 137-154 (`_matches_filter`) — extend `_FILTER_OPT_OUTS` to also match `source_table == "consent"`
  - the four `_gather_*` methods (search the file for `select(` followed by each model) — add a new `_gather_consent` method modeled on `_gather_communications`
- `src/grins_platform/api/v1/inbox.py` (entire file) — no change needed; the query param doc string at line 56-58 needs an `opt_ins` mention.
- `src/grins_platform/schemas/inbox.py` — extend `InboxSourceTable` literal to include `"consent"`. Extend `InboxFilterCounts` if a new bucket is required.
- `src/grins_platform/models/sms_consent_record.py` — verify column names (`method`, `consent_type`, `customer_id`, `created_at`).
- `src/grins_platform/tests/unit/test_inbox_service.py` — extend with consent-source tests. Mirror existing per-source test sections.

### New Files to Create

- `src/grins_platform/services/estimate_follow_up_job.py` — F7 cron wrapper. ~80 lines following `sales_pipeline_nudge_job.py` exactly.
- `src/grins_platform/tests/unit/test_estimate_follow_up_job.py` — F7 unit test (mock SMSService, mock repo).
- `src/grins_platform/tests/functional/test_estimate_follow_up_job_functional.py` — F7 functional test (real session, real follow-up rows).
- `scripts/healthcheck-portal-base-url.sh` — F4 nightly healthcheck (curl + grep `<title>`). 15 lines of bash.
- `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/SIGNOFF-VERIFICATION.md` — write-up of the mandatory Vercel browser E2E run results (created during Phase 4, not 1).

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING

**Vercel browser E2E (this run's mandate)**
- Vercel MCP tool reference (already loaded in this environment). Specifically:
  - `mcp__vercel__list_projects` / `mcp__vercel__list_deployments` — find the **current** dev deployment URL (do not hard-code; the alias rotates).
  - `mcp__vercel__web_fetch_vercel_url` — bypasses Vercel auth headers; required because the dev preview is behind Vercel auth.
  - `mcp__vercel__get_access_to_vercel_url` — generates a 23-hour shareable URL that bypasses auth via cookie. Use this URL inside the `agent-browser` session.
  - `mcp__vercel__get_runtime_logs` — pull logs after a portal click to confirm the React route resolved.
- `.vercel/project.json` (already exists at repo root and `frontend/`): `projectId=prj_SZexdljNexKryhM7PAJn3DQkDbSK`, `orgId=team_FANuLIVR0JFqdlXMuNgcJKvi`. **Use these in every Vercel MCP call** — do NOT use a different team or project.
- `agent-browser` skill (loaded). Use to (a) open the Vercel portal URL with the share token, (b) screenshot, (c) click the Approve button on the React portal page, (d) verify the post-approval state.

**APScheduler**
- [APScheduler v3 cron + interval triggers](https://apscheduler.readthedocs.io/en/3.x/userguide.html#cron-style-scheduling)
  - Specific section: *Mixing trigger types — IntervalTrigger*. Why: F7 uses `interval` like `process_pending_campaign_recipients` at `background_jobs.py:1443-1449`.
- Already-shipped patterns in this repo: see `background_jobs.py:1494-1501` (cron, daily 8:15 UTC) and `:1471-1478` (cron daily 3:30 UTC) — both `replace_existing=True`. **Always set `replace_existing=True`** on `add_job` calls in this codebase.

**SQLAlchemy 2.0 async select + UNION**
- [SQLAlchemy 2.0 async tutorial — select() and execute()](https://docs.sqlalchemy.org/en/20/orm/queryguide/select.html)
- The repo's UNION pattern is `parallel-gather + heapq.merge` (per `inbox_service.py:1`). Mirror it; do **not** introduce raw SQL UNION.

**Resend (email) link wiring**
- The portal_url is built from `EmailSettings().portal_base_url` and inlined into Resend templates. No change to Resend templates is needed for F4 — the env-var flip alone fixes every template.

### Patterns to Follow

**Naming Conventions**
- Module-level singleton + async wrapper exposed for APScheduler:
  ```python
  # sales_pipeline_nudge_job.py:133-138 (REFERENCE PATTERN)
  _sales_pipeline_nudge_job = SalesPipelineNudgeJob()

  async def nudge_stale_sales_entries_job() -> None:
      """Async wrapper for APScheduler registration."""
      await _sales_pipeline_nudge_job.run()
  ```
- New file MUST follow this exact shape: class with `DOMAIN = "estimate_follow_up"`, module-level instance, async wrapper named `process_estimate_follow_ups_job`.

**Error Handling**
- LoggerMixin gives `log_started("run")`, `log_completed("run", n=…)`, `log_failed("step", error=e, …)`. Use these (not `logger.info` directly) inside `run()` to match the F6 / F7 / F1 jobs already running.

**Logging Pattern**
- Final log line in `register_scheduled_jobs()` (`background_jobs.py:1503-1518`) lists all registered job ids as a single `jobs=[…]` keyword. **Add the new id to that list** — the log is a smoke check.

**Boot-time validation**
- Mirror `email_config.py:48-79` style: structlog `logger.error(…)` with a stable event name (`email.config.deprecated_portal_base_url` already exists). Extend, don't replace.

---

## IMPLEMENTATION PLAN

### Phase 1: F4-REOPENED — env flip + boot guard + healthcheck

> Goal: **eliminate** the failure mode where Railway's env stays wrong silently. After this phase, sending an estimate from any environment must produce a portal URL that resolves to the React app.

**Tasks:**
- Flip `PORTAL_BASE_URL` on Railway dev (and prod, if it mirrors). No code change.
- Harden `email_config.py` so a deprecated host **fails boot** in `dev`/`staging`/`prod` (warn-only in `local`/`pytest`).
- Add a 15-line nightly healthcheck script that proves the live portal serves the React bundle.
- Update `.env.example` to call out the canonical alias and warn against `frontend-git-*` aliases.

### Phase 2: F7 — register estimate follow-up cron

> Goal: Day 3 / 7 / 14 / 21 SMS nudges actually fire.

**Tasks:**
- Create `services/estimate_follow_up_job.py` mirroring `sales_pipeline_nudge_job.py`.
- Wire it into `background_jobs.register_scheduled_jobs()` as a 15-minute `interval` job.
- Add the new job id to the `scheduler.jobs.registered` log line.
- Author unit + functional tests.

### Phase 3: F8 — extend inbox UNION with consent flips

> Goal: standalone STOP/START replies surface in `/inbox` with `opt_outs` / `opt_ins` triage filters.

**Tasks:**
- Extend `InboxSourceTable` literal in `schemas/inbox.py` to include `"consent"`.
- Add `_gather_consent` method to `InboxService` mirroring `_gather_communications`.
- Extend `_classify_triage`, `_matches_filter`, `_HANDLED_STATUSES` for the new source.
- Gate behind `INBOX_SHOW_CONSENT_FLIPS` env flag (default `false`); flip to `true` after browser verification.
- Frontend: extend the inbox triage filter chip bar to render `Opt-outs` / `Opt-ins` chips. (Verify via browser — see Phase 4.)

### Phase 4: MANDATORY Vercel browser E2E verification

> **No fix lands in `main` until this phase passes.** API curl is **not acceptable** for the F4-REOPENED verdict — the bug is "200 OK + wrong bundle".

**Tasks:**
- Use `mcp__vercel__list_deployments` to fetch the **current** dev preview URL (do not assume; the alias may have rotated).
- Use `mcp__vercel__get_access_to_vercel_url` to mint a 23-hour share URL.
- Use `agent-browser` skill to open the portal URL, screenshot the page, and click Approve.
- Use `mcp__vercel__get_runtime_logs` to confirm the React route resolved server-side.
- Capture screenshots into `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/SIGNOFF-VERIFICATION.md` with timestamps.

### Phase 5: Sign-off

**Tasks:**
- Update `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/E2E-SIGNOFF-REPORT.md` with PASS verdicts for F4-REOPENED, F7, F8.
- Append a `Resolved on 2026-05-05` line under each finding.
- Move the file's verdict gate from "BLOCKER" to "CLEARED".
- Add release-note entry for the next deploy.

---

## STEP-BY-STEP TASKS

Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task Format Guidelines

Use information-dense keywords for clarity:
- **CREATE**: New files or components
- **UPDATE**: Modify existing files
- **ADD**: Insert new functionality into existing code
- **REMOVE**: Delete deprecated code
- **REFACTOR**: Restructure without changing behavior
- **MIRROR**: Copy pattern from elsewhere in codebase

---

### Phase 1 — F4-REOPENED

#### 1.1 OPERATIONAL FIX: flip Railway dev `PORTAL_BASE_URL`

- **IMPLEMENT**: Update Railway env var on `Grins-dev` / `dev` environment.
- **PATTERN**: One-line env flip; no code change.
- **GOTCHA**: This is *not* `railway run` from local — that's a no-op. Use the Railway dashboard or `railway variables --set ... --service Grins-dev --environment dev`. Mirror in `prod` only after dev passes browser verification.
- **GOTCHA**: The user (`memory: feedback_no_remote_alembic.md`) has a hard rule: do **NOT** run remote alembic from local; that constraint does not apply to env-var flips, but stay disciplined — push the flip from the dashboard in the user's presence rather than running CLI commands automatically.
- **VALIDATE**:
  ```bash
  railway variables --service Grins-dev --environment dev --kv | grep PORTAL_BASE_URL
  # Must print: PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app
  ```

#### 1.2 UPDATE `src/grins_platform/services/email_config.py` — make deprecated host a boot failure

- **IMPLEMENT**: Add `def validate_portal_base_url(self) -> None:` that **raises** `RuntimeError` on deprecated host when `os.getenv("ENVIRONMENT", "local")` is in `{"dev", "staging", "production"}`. Otherwise log error and continue (existing behavior).
- **PATTERN**: existing `log_configuration_status` at `email_config.py:48-79`. Add a sibling method; do not change existing behavior in test/local.
- **IMPORTS**:
  ```python
  import os
  ```
- **GOTCHA**: Pydantic-settings reads env on instantiation, so any code path that creates `EmailSettings()` triggers this. Call `validate_portal_base_url()` from `app.py` startup hook *only* — do not call from inside `EmailSettings.__init__` (would break unit tests that import EmailSettings without setting `ENVIRONMENT`).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_config.py -v`

#### 1.3 UPDATE `src/grins_platform/app.py` — call `validate_portal_base_url()` at startup

- **IMPLEMENT**: In the existing `@app.on_event("startup")` (or lifespan handler — check the file's existing convention first), call `EmailSettings().validate_portal_base_url()`.
- **PATTERN**: Find the existing startup hook in `app.py`; add the validation call after other config validations. If `app.py` already calls `EmailSettings().log_configuration_status()`, put the new call adjacent.
- **GOTCHA**: If `app.py` uses `@asynccontextmanager` lifespan, this validation goes in the `yield` setup phase. Don't put it in middleware.
- **VALIDATE**:
  ```bash
  ENVIRONMENT=dev PORTAL_BASE_URL=https://frontend-git-dev-kirilldr01s-projects.vercel.app \
    uv run python -c "from grins_platform.app import app; print('boot ok')"
  # Must exit non-zero with the deprecated-host error.
  ENVIRONMENT=local PORTAL_BASE_URL=https://frontend-git-dev-kirilldr01s-projects.vercel.app \
    uv run python -c "from grins_platform.app import app; print('boot ok')"
  # Must exit 0 (warn only).
  ```

#### 1.4 ADD `tests/unit/test_email_config.py` cases

- **IMPLEMENT**: Add three test cases:
  1. `test_validate_portal_base_url_raises_in_dev_with_deprecated_host`
  2. `test_validate_portal_base_url_warns_only_in_local`
  3. `test_validate_portal_base_url_passes_with_canonical_alias`
- **PATTERN**: existing tests in the same file (file already exists per the F4-prior plan).
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_email_config.py -v` — all green.

#### 1.5 CREATE `scripts/healthcheck-portal-base-url.sh`

- **IMPLEMENT**: 15-line bash that takes `$PORTAL_BASE_URL` from env, curls `<base>/portal/estimates/__healthcheck__` with `-sL`, greps the response body for `<title>Grin's Irrigation Platform`, and exits non-zero if absent.
- **PATTERN**: similar smoke scripts already exist under `scripts/` — `ls scripts/*.sh` and mirror the one closest in shape. Use `set -euo pipefail`.
- **GOTCHA**: The marketing site bundle returns 200 with `<title>Grins Irrigation &amp; Landscaping | Twin Cities MN`. The check MUST grep for the **React** title (`Grin's Irrigation Platform`), not just the response code.
- **VALIDATE**:
  ```bash
  PORTAL_BASE_URL=https://frontend-git-dev-kirilldr01s-projects.vercel.app \
    bash scripts/healthcheck-portal-base-url.sh
  # Must exit non-zero with: "PORTAL_BASE_URL serves marketing bundle, not React portal"
  PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app \
    bash scripts/healthcheck-portal-base-url.sh
  # Must exit 0.
  ```

#### 1.6 UPDATE `.env.example` (lines 148-160)

- **IMPLEMENT**: Add a comment block immediately above `PORTAL_BASE_URL=http://localhost:5173`:
  ```
  # CANONICAL alias only. Never set to a `frontend-git-*` Vercel preview alias —
  # those rotate when the Vercel project is renamed and silently 200 with the
  # wrong bundle (see CANDIDATE-FINDINGS.md F4-REOPENED, 2026-05-04).
  # Dev:  https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app
  # Prod: https://app.grinsirrigation.com (or canonical custom domain when live)
  ```
- **VALIDATE**: `grep -A6 'PORTAL_BASE_URL' .env.example` shows the comment.

---

### Phase 2 — F7

#### 2.1 CREATE `src/grins_platform/services/estimate_follow_up_job.py`

- **IMPLEMENT**: New file mirroring `sales_pipeline_nudge_job.py:1-138` exactly. The class `EstimateFollowUpJob(LoggerMixin)` with `DOMAIN = "estimate_follow_up"` and an async `run()` that:
  1. Resolves a DB session via `get_database_manager()`.
  2. Constructs `EstimateRepository(session)`.
  3. Constructs `SMSService` (look at `dependencies.py` for the canonical builder; mirror).
  4. Constructs `EstimateService(estimate_repository=..., portal_base_url=EmailSettings().portal_base_url, sms_service=...)`.
  5. Calls `await estimate_service.process_follow_ups()`.
  6. `await session.commit()`.
- **PATTERN**: `sales_pipeline_nudge_job.py:39-138`. **Do not deviate** from the LoggerMixin / module-level singleton / async-wrapper convention.
- **IMPORTS**:
  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  from grins_platform.database import get_database_manager
  from grins_platform.log_config import LoggerMixin, get_logger
  from grins_platform.repositories.estimate_repository import EstimateRepository
  from grins_platform.services.email_config import EmailSettings
  from grins_platform.services.estimate_service import EstimateService
  from grins_platform.services.sms.factory import get_sms_provider
  from grins_platform.services.sms_service import SMSService
  ```
- **GOTCHA**: `EstimateService.process_follow_ups()` requires `self.sms_service` to be non-None *and* a phone to be resolvable from the estimate. If you forget to wire the SMS service, **every follow-up will be `SKIPPED`** with `reason="no_channel_available"` — appears to "work" but never sends. Verify the unit test asserts `sent` count > 0.
- **GOTCHA**: `EmailSettings().portal_base_url` must be the canonical alias post-Phase-1; if Phase 1 hasn't shipped, follow-up SMS will *also* contain the broken portal URL. Run Phase 1 first.
- **VALIDATE**:
  ```bash
  uv run python -c "from grins_platform.services.estimate_follow_up_job import process_estimate_follow_ups_job; print('import ok')"
  ```

#### 2.2 UPDATE `src/grins_platform/services/background_jobs.py` imports (lines 56-58 area)

- **IMPLEMENT**: Add import alongside the existing `nudge_stale_sales_entries_job` import:
  ```python
  from grins_platform.services.estimate_follow_up_job import (
      process_estimate_follow_ups_job,
  )
  ```
- **PATTERN**: existing `from grins_platform.services.sales_pipeline_nudge_job import (...)` — mirror exact style.
- **VALIDATE**: `uv run ruff check src/grins_platform/services/background_jobs.py`

#### 2.3 UPDATE `src/grins_platform/services/background_jobs.py:register_scheduled_jobs` (lines 1492-1501 vicinity)

- **IMPLEMENT**: Add a new `scheduler.add_job(...)` block immediately AFTER the `nudge_stale_sales_entries` block:
  ```python
  # F7 — estimate follow-up SMS cadence (Day 3/7/14/21).
  # 15-minute interval is plenty: the cadence has hours of slack and the
  # job is idempotent (process_follow_ups skips already-SENT/SKIPPED rows).
  scheduler.add_job(
      process_estimate_follow_ups_job,
      "interval",
      minutes=15,
      id="process_estimate_follow_ups",
      replace_existing=True,
  )
  ```
- **PATTERN**: `background_jobs.py:1494-1501` (F6 cron block) and `:1443-1449` (interval-style).
- **GOTCHA**: `replace_existing=True` is mandatory. Without it, a job-id conflict on redeploy raises `ConflictingIdError` and the entire scheduler fails to start.
- **VALIDATE**: `grep -n 'process_estimate_follow_ups' src/grins_platform/services/background_jobs.py | wc -l` — expect 3 (import, add_job id, jobs=[…] log entry).

#### 2.4 UPDATE the `scheduler.jobs.registered` log line (lines 1503-1518)

- **IMPLEMENT**: Append `"process_estimate_follow_ups"` to the `jobs=[...]` list.
- **VALIDATE**: `uv run python -c "from grins_platform.services.background_jobs import register_scheduled_jobs; print('ok')"` — no import errors.

#### 2.5 CREATE `src/grins_platform/tests/unit/test_estimate_follow_up_job.py`

- **IMPLEMENT**: Mock `EstimateRepository.get_pending_follow_ups` to return 2 rows (Day 3 and Day 7), mock SMSService to return `{"sent": True}`. Assert `process_follow_ups()` returns `2` and both rows are flipped to `SENT`.
- **PATTERN**: `tests/unit/test_sales_pipeline_nudge_job.py` — mirror fixture/mocking style exactly.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_estimate_follow_up_job.py -v`

#### 2.6 CREATE `src/grins_platform/tests/functional/test_estimate_follow_up_job_functional.py`

- **IMPLEMENT**: Use the standard functional fixture (real DB session). Insert one estimate + 4 follow-up rows (Day 3 already in the past, Day 7/14/21 future). Run the job. Assert exactly 1 row flipped to `SENT` (the Day 3) and the other 3 remain `SCHEDULED`.
- **PATTERN**: `tests/functional/test_background_jobs_functional.py:295-310` for session/fixture usage.
- **GOTCHA**: Use `email=kirillrakitinsecond@gmail.com` and phone `+19527373312` per the user's hard rule (`memory: feedback_test_email_only_allowlist.md` and `feedback_sms_test_number.md`). Never use `@example.com` or any synthetic address.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/functional/test_estimate_follow_up_job_functional.py -v`

---

### Phase 3 — F8

#### 3.1 UPDATE `src/grins_platform/schemas/inbox.py` — add `"consent"` to `InboxSourceTable`

- **IMPLEMENT**: Find the `InboxSourceTable = Literal[...]` definition and append `"consent"`.
- **PATTERN**: existing literal; mirror the style.
- **VALIDATE**: `uv run mypy src/grins_platform/schemas/inbox.py` — no errors.

#### 3.2 UPDATE `src/grins_platform/services/inbox_service.py` — add consent gather + classify

- **IMPLEMENT** in this order:
  1. Add `from grins_platform.models.sms_consent_record import SmsConsentRecord` to imports.
  2. Add `"consent": frozenset({"opt_in_processed"})` (or whatever the model's "settled" status is — verify against the model) to `_HANDLED_STATUSES` at line 103.
  3. Extend `_classify_triage` (lines 113-134): if `source_table == "consent"` and `status in {"opt_out", "stop"}`, return `"pending"` (operator should see it); else `"handled"`.
  4. Extend `_matches_filter` (lines 137-154): when `triage == _FILTER_OPT_OUTS`, also match `source_table == "consent" and status in {"opt_out", "stop"}`. Add a new `_FILTER_OPT_INS = "opt_ins"` constant and matching branch.
  5. Add `async def _gather_consent(self, session, ...)` mirroring `_gather_communications` — select recent `SmsConsentRecord` rows where `method in {"text_stop", "text_start"}`. Map to `InboxItem(source_table="consent", id=row.id, status=row.method, customer_id=row.customer_id, received_at=row.created_at, ...)`.
  6. Add the new gather to the `asyncio.gather` parallel-fetch block in `list_events()`.
- **PATTERN**: `_gather_communications` is the closest match because consent rows, like communications, are not always tied to a campaign or confirmation.
- **GATE**: wrap the new gather call in `if os.getenv("INBOX_SHOW_CONSENT_FLIPS", "false").lower() == "true":` so we can land the schema and gather code without flipping behavior. Verify in browser, then flip the env var.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_inbox_service.py -v`

#### 3.3 UPDATE `src/grins_platform/api/v1/inbox.py` — extend Query doc string

- **IMPLEMENT**: Update the `triage` Query parameter description at lines 53-58 to include `opt_ins` and document the new `source_table=consent` rows.
- **VALIDATE**: `curl http://localhost:8000/openapi.json | jq '.paths."/api/v1/inbox".get.parameters[] | select(.name=="triage")'` shows the updated description.

#### 3.4 EXTEND `src/grins_platform/tests/unit/test_inbox_service.py`

- **IMPLEMENT**: Add 4 cases:
  1. `test_consent_stop_appears_in_opt_outs_filter`
  2. `test_consent_start_appears_in_opt_ins_filter`
  3. `test_consent_handled_classification_for_start`
  4. `test_consent_pending_classification_for_stop`
- **PATTERN**: existing test sections per source.
- **VALIDATE**: `uv run pytest src/grins_platform/tests/unit/test_inbox_service.py -v -k consent`

#### 3.5 UPDATE `frontend/src/features/schedule/components/InboxQueue.tsx`

- **IMPLEMENT** in this exact order, using these exact line numbers (verified against current file):
  1. **Line 48-55** — Add `{ key: 'opt_ins', label: 'Opt-ins' }` to `FILTER_OPTIONS` array. (`opt_outs` chip already exists at line 53.) The token order should be: all, needs_triage, orphans, unrecognized, opt_outs, **opt_ins** (new), archived.
  2. **Line 59-66** — Add `consent: <Phone className="h-3 w-3 text-rose-500" />` (or similar lucide icon) to `sourceIcons: Record<InboxSourceTable, React.ReactNode>`.
  3. **Line 68-73** — Add `consent: 'Consent'` to `sourceLabels: Record<InboxSourceTable, string>`.
- **PATTERN**: existing entries at the same lines. Mirror style exactly (3-character indent, alphabetical-ish order — `consent` goes first by convention).
- **IMPORTS**: add `Phone` (or chosen icon) to the lucide-react import block at lines 20-31.
- **GOTCHA**: `InboxSourceTable` and `InboxFilterToken` are exported from `frontend/src/features/schedule/api/inboxApi.ts` — that file must be updated too (Task 3.5.1) before this file will type-check.
- **VALIDATE**: `cd frontend && npx tsc --noEmit` from the repo root (via `npm run typecheck`).

#### 3.5.1 UPDATE `frontend/src/features/schedule/api/inboxApi.ts`

- **IMPLEMENT**: extend the `InboxSourceTable` literal union to include `'consent'`, and the `InboxFilterToken` literal union to include `'opt_ins'`.
- **PATTERN**: existing literal unions in the same file.
- **VALIDATE**: `cd frontend && npm run typecheck` exits 0.

#### 3.5.2 UPDATE `frontend/src/features/schedule/components/InboxQueue.tsx` counts type

- **IMPLEMENT**: if the `InboxFilterCounts` (consumed at line 193 as `counts[opt.key]`) does not already accept the new keys, extend it in `inboxApi.ts` (counts dict shape) and in `schemas/inbox.py::InboxFilterCounts`. Default the new counts to 0 in `_count_filter_buckets` inside `inbox_service.py`.
- **VALIDATE**: `npm run typecheck` and `uv run pytest src/grins_platform/tests/unit/test_inbox_service.py -v`.

#### 3.6 UPDATE `.env.example` — document `INBOX_SHOW_CONSENT_FLIPS`

- **IMPLEMENT**: Add a new commented line near other feature flags:
  ```
  # F8 — surface standalone STOP/START consent flips in /inbox.
  # Default false; flip true after browser verification.
  # INBOX_SHOW_CONSENT_FLIPS=false
  ```
- **VALIDATE**: `grep INBOX_SHOW_CONSENT_FLIPS .env.example`

---

### Phase 4 — MANDATORY Vercel browser E2E

> **STOP.** Read this whole section before opening a tool. Do not curl / API-only verify and call it done. The F4 bug is "200 OK + wrong bundle" — only a real DOM render proves the fix.

#### 4.1 RESOLVE current Vercel deployment URL

- **IMPLEMENT**: Call `mcp__vercel__list_deployments` with `projectId=prj_SZexdljNexKryhM7PAJn3DQkDbSK`, `teamId=team_FANuLIVR0JFqdlXMuNgcJKvi`, filter to dev environment, take the most recent `READY` deployment. Capture the URL.
- **GOTCHA**: Don't hard-code `grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app`. The alias rotates if the Vercel project is renamed (which is exactly how F4 happened). Always resolve fresh.
- **VALIDATE**: Save the resolved URL to a shell variable and echo it back in the verification doc.

#### 4.2 MINT a Vercel auth-bypass URL

- **IMPLEMENT**: Call `mcp__vercel__get_access_to_vercel_url` with the URL from 4.1. The response includes a `_vercel_share` URL that bypasses Vercel auth for 23 hours.
- **GOTCHA**: The dev preview is behind Vercel auth. Without this share URL, the agent-browser session sees the Vercel login page, not the React portal — and you'll incorrectly conclude the fix is broken.

#### 4.3 SEED an estimate via API (use the existing seed customer)

- **IMPLEMENT**:
  ```bash
  TOKEN=$(curl -s -X POST $API/api/v1/auth/login -d '{"email":"kirillrakitinsecond@gmail.com","password":"..."}' | jq -r .access_token)
  # Confirm seed customer.email is kirillrakitinsecond@gmail.com BEFORE sending — this is the inbox the user is monitoring.
  curl -s $API/api/v1/customers/a44dc81f-ce81-4a6f-81f5-4676886cef1a -H "Authorization: Bearer $TOKEN" | jq '.email'
  # Expected: "kirillrakitinsecond@gmail.com". If different, PATCH the customer email FIRST. Do NOT send to any other address.
  EST=$(curl -s -X POST $API/api/v1/estimates -H "Authorization: Bearer $TOKEN" \
    -d '{"customer_id":"a44dc81f-ce81-4a6f-81f5-4676886cef1a","line_items":[{"description":"Test","quantity":1,"unit_price":100}],"total":100}')
  ESTIMATE_ID=$(echo $EST | jq -r .id)
  curl -s -X POST $API/api/v1/estimates/$ESTIMATE_ID/send -H "Authorization: Bearer $TOKEN"
  PORTAL_URL=$(curl -s $API/api/v1/estimates/$ESTIMATE_ID -H "Authorization: Bearer $TOKEN" | jq -r .portal_url)
  echo "Portal URL: $PORTAL_URL"
  ```
- **GOTCHA**: The seed customer is `a44dc81f-ce81-4a6f-81f5-4676886cef1a` per memory `project_e2e_seed_identities.md`. Do NOT create a new customer.
- **GOTCHA**: phone `+19527373312` and email `kirillrakitinsecond@gmail.com` are the only allowlisted test contacts. The user is actively watching **both** the SMS at +19527373312 **and** the inbox at kirillrakitinsecond@gmail.com — every SMS and email this run produces MUST land at those exact destinations.
- **PRE-SEND PHONE CHECK**: Before any send-estimate or follow-up cron fire, run:
  ```bash
  curl -s $API/api/v1/customers/a44dc81f-ce81-4a6f-81f5-4676886cef1a -H "Authorization: Bearer $TOKEN" | jq '.phone'
  ```
  Expected: `"9527373312"` or `"+19527373312"` (normalized form). If different, PATCH first. **Do NOT proceed with any SMS send until the seed customer's phone matches.** A wrong phone here means a real text to a stranger.

#### 4.3.1 EMAIL + SMS RECEIPT CONFIRMATION (PAUSE for user)

> The send-estimate flow fires **both** an email (to `kirillrakitinsecond@gmail.com`) **and** an SMS (to `+19527373312`). The user is monitoring **both** channels live. Pause for human confirmation on **each** before moving on.

- **IMPLEMENT — EMAIL leg**:
  - After step 4.3 fires the send, **stop and ask the user** to confirm the email landed at `kirillrakitinsecond@gmail.com`. Do not proceed until confirmed.
  - Capture the Resend `message_id` from:
    ```bash
    curl -s "$API/api/v1/communications?customer_id=a44dc81f-ce81-4a6f-81f5-4676886cef1a&limit=5" -H "Authorization: Bearer $TOKEN" | jq '.[] | {channel, message_type, provider_message_id, sent_at}'
    ```
- **IMPLEMENT — SMS leg**:
  - **Stop and ask the user** to confirm the SMS landed at `+19527373312`. The SMS body must contain the canonical portal URL (the Phase 1 env-flip's payoff — if the human sees `frontend-git-dev-...` in the SMS, F4 is NOT actually fixed).
  - Capture the SMS `provider_conversation_id` from `sent_messages` (same `/communications` endpoint, channel=sms rows).
- **VALIDATE**: User replies "got the email" AND "got the text" with the URL preview. **Do NOT infer** from `sent_messages.status=delivered` — provider statuses lie sometimes; only the human's eyes count for the F4 portal-URL correctness check.
- **GOTCHA — email**: If the email does NOT land within 90 seconds, do NOT silently retry. The dev allowlist (`EMAIL_TEST_ADDRESS_ALLOWLIST` per memory `feedback_email_test_inbox.md`) may have rejected it. Investigate the Resend dashboard / structlog `email.send.*` events before re-sending.
- **GOTCHA — SMS**: If the SMS does NOT land within 60 seconds, do NOT silently retry. The dev allowlist (`SMS_TEST_PHONE_ALLOWLIST` per memory `feedback_sms_test_number.md`) may have rejected it; or the seed customer's phone column is wrong (re-check Step 4.3 PRE-SEND PHONE CHECK). Investigate via `sent_messages.last_error` + structlog `sms.send.*` events.

#### 4.4 OPEN the portal URL in agent-browser

- **IMPLEMENT**: Use the `agent-browser` skill. Navigate to `$PORTAL_URL`. **First** open the share URL from 4.2 to set the auth cookie, **then** navigate to `$PORTAL_URL`. Take a screenshot.
- **VALIDATE**: The screenshot must show:
  - Page title `Grin's Irrigation Platform` (NOT `Grins Irrigation & Landscaping | Twin Cities MN`)
  - Line items table populated with the seeded line item
  - Visible Approve and Reject buttons
- **FAIL CRITERIA**: any of these missing → F4 is NOT fixed; revert the env flip and investigate.

#### 4.5 CLICK Approve and verify post-approval state

- **IMPLEMENT**: Use agent-browser to click the Approve button. Wait for the success state. Screenshot.
- **VALIDATE**:
  - Frontend shows approval confirmation.
  - Backend: `curl $API/api/v1/estimates/$ESTIMATE_ID -H "Authorization: Bearer $TOKEN" | jq '.status, .approved_at'` shows `"approved"` and a timestamp.
  - A `Job` row was auto-created with `job_type=estimate_approved` and `status=to_be_scheduled` (per the report's note about `estimate.auto_job_created`).

#### 4.6 PULL Vercel runtime logs to confirm React route resolution

- **IMPLEMENT**: `mcp__vercel__get_runtime_logs` with `projectId`, `teamId`, `since=15m`, `query=portal/estimates`.
- **VALIDATE**: At least one log line for `/portal/estimates/<token>` from the timestamp of step 4.4. Log source should be `static` (the React SPA), not `serverless` (marketing site).

#### 4.7 F7 browser verification — fire the cron once, confirm SMS

- **IMPLEMENT — exact incantation** (do not improvise):
  - **Step A**: Confirm seed customer phone = `9527373312` (or `+19527373312` normalized) AND email = `kirillrakitinsecond@gmail.com`. Use the `curl ... | jq '.phone, .email'` from Step 4.3.
  - **Step B**: Insert a `SCHEDULED` follow-up row with `scheduled_at = now() - interval '1 minute'`:
    ```bash
    railway run --service Grins-dev --environment dev -- python -c "
    import asyncio
    from datetime import datetime, timedelta, timezone
    from grins_platform.database import get_database_manager
    from grins_platform.repositories.estimate_repository import EstimateRepository
    from grins_platform.models.enums import FollowUpStatus

    async def seed():
        async for s in get_database_manager().get_session():
            r = EstimateRepository(s)
            # Use the estimate seeded in 4.3 (ESTIMATE_ID).
            await r.create_follow_up(
                estimate_id='<ESTIMATE_ID from 4.3>',
                follow_up_number=99,
                scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                channel='sms',
                message=None,
                promotion_code=None,
                status=FollowUpStatus.SCHEDULED.value,
            )
            await s.commit()
    asyncio.run(seed())
    "
    ```
  - **Step C**: Fire the job ad-hoc via Railway (NOT local — local connects to a different DB):
    ```bash
    railway run --service Grins-dev --environment dev -- python -c "
    import asyncio
    from grins_platform.services.estimate_follow_up_job import process_estimate_follow_ups_job
    asyncio.run(process_estimate_follow_ups_job())
    "
    ```
  - **Step D**: **WAIT for the human at +19527373312 to confirm SMS receipt before continuing.** The SMS body should contain the canonical portal URL (from Phase 1 fix) — the human should ALSO confirm the URL they see is the `grins-irrigation-platform-git-dev-...` alias, not the deprecated one.
- **VALIDATE**:
  - Database: `SELECT status, sent_at FROM estimate_follow_up WHERE follow_up_number=99` shows `SENT` and a non-null timestamp.
  - SMS provider: `sent_messages` row with `provider_conversation_id` set.
  - **HUMAN PAUSE**: explicit "got the text" from user at +19527373312 — do not infer from logs alone.
  - Log line: `estimate.follow_up.sent` event in structlog output.
- **GOTCHA**: `railway run` against a deployed service injects the **container's** internal env, including `DATABASE_URL` (internal hostname). That's exactly what you want — it's the same DB the cron itself touches. Do NOT run this locally with the public DATABASE_URL — the seeded row would land in a different DB than the deployed cron reads.
- **GOTCHA**: This is the `railway run python` pattern (works fine), NOT `railway run alembic` (which is documented as broken in `docs/troubleshooting/Leads/leads-network-error-500.md:516`). Different commands.

#### 4.8 F8 browser verification — see opt-out / opt-in in `/inbox`

- **IMPLEMENT**:
  - Set `INBOX_SHOW_CONSENT_FLIPS=true` in dev Railway env.
  - From the human phone (+19527373312), send a standalone `STOP` to the CallRail tracking number (`CALLRAIL_TRACKING_NUMBER` from `.env`), **outside** any active campaign or confirmation flow.
  - **Pause for the user** to confirm "STOP sent at HH:MM" — capture the timestamp.
  - Within 30s, open `/inbox?triage=opt_outs` in the agent-browser session.
  - Send `START` from the same phone next.
  - **Pause for the user** to confirm "START sent at HH:MM".
  - Open `/inbox?triage=opt_ins` in agent-browser.
- **VALIDATE**:
  - Browser screenshot shows the STOP row with `source_table=consent` and `status` like `opt_out` / `text_stop`.
  - Browser screenshot shows the START row with `source_table=consent` and `status` like `opt_in` / `text_start`.
  - Both rows have correct `customer_id` populated (the seed customer, NOT orphan).
  - The `Opt-outs` and `Opt-ins` chip badges in `inbox-filter-bar` (Task 3.5 line 188-225) show counts ≥ 1 each.
- **GOTCHA**: STOP/START reach the backend through the CallRail inbound webhook (`/api/v1/webhooks/callrail-inbound`). If the webhook isn't configured or HMAC fails, the consent record never writes and you'll see nothing in `/inbox` regardless of fix correctness. Verify by checking `audit_log` for a `consent.opt_out_sms` row with the human's timestamp before concluding F8 is broken.

#### 4.9 WRITE `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/SIGNOFF-VERIFICATION.md`

- **IMPLEMENT**: Document each verification step from 4.1–4.8 with:
  - timestamps,
  - tool calls actually used (with the resolved URLs),
  - screenshot file paths,
  - human-confirmed SMS receipts,
  - the exact `<title>` string that proved 4.4.
- **VALIDATE**: file exists; manual review.

---

### Phase 5 — Sign-off

#### 5.1 UPDATE `e2e-screenshots/master-plan/runs/run-20260504-184355-portal-cron/E2E-SIGNOFF-REPORT.md`

- **IMPLEMENT**: For each of F4-REOPENED / F7 / F8, append a `**Status (2026-05-05)**: RESOLVED — verified via Vercel browser E2E (see SIGNOFF-VERIFICATION.md).` line.
- **IMPLEMENT**: Replace the verdict block at the top with `PASS — all blockers cleared`.
- **VALIDATE**: manual.

#### 5.2 UPDATE `DEVLOG.md` with the three fixes

- **IMPLEMENT**: One paragraph per finding with the commit SHA.
- **PATTERN**: `DEVLOG.md` entry style.
- **VALIDATE**: manual.

#### 5.3 RELEASE NOTES — ready-to-merge

- **IMPLEMENT**: Confirm `git status` is clean apart from the planned files. `git log --oneline -5` ready to PR.
- **VALIDATE**: see "Validation Commands" below.

---

## TESTING STRATEGY

### Unit Tests

- F4: `test_email_config.py::test_validate_portal_base_url_*` (3 cases) — boot fail / boot warn / boot pass.
- F7: `test_estimate_follow_up_job.py` — mock SMSService + repo, assert `sent_count == 2` and rows flipped.
- F8: `test_inbox_service.py::test_consent_*` (4 cases) — STOP→pending, START→handled, opt_outs filter, opt_ins filter.

### Integration / Functional Tests

- F7 functional: real DB session, 4 inserted follow-up rows (Day 3 past, others future), assert exactly 1 SENT and 3 SCHEDULED post-run.
- F8 functional: insert real `SmsConsentRecord` rows with `method=text_stop`/`text_start`, assert they appear in `/inbox` UNION result.

### Edge Cases

- **F4**: `PORTAL_BASE_URL=""` → boot pass (default `http://localhost:5173`); `PORTAL_BASE_URL=https://frontend-git-staging-…` → variant deprecated alias must also be added to `_DEPRECATED_PORTAL_HOSTS` if/when staging stale alias appears (defer to discovery).
- **F7**: estimate already approved between job runs → `process_follow_ups` cancels remaining rows (covered by `estimate_service.py:1063-1064` — verify in functional test). Estimate has no phone → row flipped to `SKIPPED`; do not retry.
- **F7**: 4 follow-ups all due simultaneously (long downtime) → all 4 sent in one run; verify SMS rate limit guard isn't hit (the existing rate limiter is per-customer, not per-job; should be fine but assert in functional test).
- **F8**: STOP from a phone not linked to any customer → `customer_id is None`, classify as `pending` (orphan), surface in `/inbox?triage=opt_outs`. START re-opt-in for the same phone → flips to `handled`.
- **F8**: Multiple consecutive STOP/START flips within minutes → each row appears separately (do not deduplicate; the audit chain matters).

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check src/grins_platform/services/email_config.py
uv run ruff check src/grins_platform/services/estimate_follow_up_job.py
uv run ruff check src/grins_platform/services/background_jobs.py
uv run ruff check src/grins_platform/services/inbox_service.py
uv run ruff format --check src/grins_platform/
uv run mypy src/grins_platform/services/email_config.py src/grins_platform/services/estimate_follow_up_job.py src/grins_platform/services/inbox_service.py
```

> **Known**: ruff currently has 111 PRE-EXISTING errors (per the source report §23). Do **not** fix unrelated lints in this PR. Only assert that the *new* files / changed lines have zero new ruff errors.

### Level 2: Unit Tests

```bash
uv run pytest src/grins_platform/tests/unit/test_email_config.py -v
uv run pytest src/grins_platform/tests/unit/test_estimate_follow_up_job.py -v
uv run pytest src/grins_platform/tests/unit/test_inbox_service.py -v
uv run pytest src/grins_platform/tests/unit/test_sales_pipeline_nudge_job.py -v   # regression — must still pass
```

### Level 3: Functional / Integration Tests

```bash
uv run pytest src/grins_platform/tests/functional/test_estimate_follow_up_job_functional.py -v
uv run pytest src/grins_platform/tests/functional/test_background_jobs_functional.py -v
uv run pytest src/grins_platform/tests/functional/test_estimate_operations_functional.py -v   # regression
```

### Level 4: Manual / API Validation

```bash
# F4 - boot guard
ENVIRONMENT=dev PORTAL_BASE_URL=https://frontend-git-dev-kirilldr01s-projects.vercel.app \
  uv run python -c "from grins_platform.app import app"
# Expected: non-zero exit with deprecated-host RuntimeError

# F4 - healthcheck script
PORTAL_BASE_URL=https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app \
  bash scripts/healthcheck-portal-base-url.sh
# Expected: exit 0 + "ok: React portal bundle confirmed"

# F7 - manual fire
uv run python -c "import asyncio; from grins_platform.services.estimate_follow_up_job import process_estimate_follow_ups_job; asyncio.run(process_estimate_follow_ups_job())"
# Expected: structlog "estimate_follow_up.run.completed" with entries_sent>=0

# F8 - inbox filter
curl "$API/api/v1/inbox?triage=opt_outs&limit=20" -H "Authorization: Bearer $TOKEN" | jq '.items[].source_table' | sort -u
# Expected (after a real STOP arrives): includes "consent"
```

### Level 5: MANDATORY Vercel browser E2E (NOT OPTIONAL)

This level is **required** for sign-off. API-only validation does NOT satisfy it.

```text
1. mcp__vercel__list_deployments
   projectId=prj_SZexdljNexKryhM7PAJn3DQkDbSK
   teamId=team_FANuLIVR0JFqdlXMuNgcJKvi
   → capture latest READY URL.

2. mcp__vercel__get_access_to_vercel_url
   url=<latest URL from step 1>
   → capture share URL.

3. agent-browser:
   - navigate to share URL (sets cookie)
   - navigate to $PORTAL_URL (from 4.3)
   - screenshot
   - assert <title> == "Grin's Irrigation Platform"
   - click Approve
   - screenshot post-approval
   - navigate to /inbox?triage=opt_outs (after STOP from human phone)
   - screenshot

4. mcp__vercel__get_runtime_logs
   projectId=prj_SZexdljNexKryhM7PAJn3DQkDbSK
   teamId=team_FANuLIVR0JFqdlXMuNgcJKvi
   query="portal/estimates"
   since="15m"
   → confirm React route resolved.

5. Human-confirmed SMS receipt at +19527373312 for the F7 follow-up.

6. **Human-confirmed email receipt at kirillrakitinsecond@gmail.com** for:
   - F4 estimate-send email (from step 4.3.1) — confirms the new portal link works in the inbox the user is monitoring.
   - F7 follow-up email (if the SMS-no-phone branch routes to email) — confirm whichever landed.
   - Stripe Payment Link email (recommended bonus check, since the same `PORTAL_BASE_URL` env powers payment links).

7. Write SIGNOFF-VERIFICATION.md with all artifacts (URLs, screenshots, Resend message_ids, SMS provider_conversation_ids, human-confirmation timestamps).
```

**No PR ships without Level 5 artifacts attached.** This is the user's explicit mandate for this plan.

**The user is actively monitoring `kirillrakitinsecond@gmail.com`** — pause for explicit human confirmation after each email send, do not batch-fire and assume.

---

## ACCEPTANCE CRITERIA

**F4-REOPENED**
- [ ] Railway dev `PORTAL_BASE_URL` reads as canonical alias (`grins-irrigation-platform-git-dev-…`).
- [ ] `email_config.py::EmailSettings.validate_portal_base_url()` raises `RuntimeError` in dev/staging/prod when host is deprecated; warns-only in local/test.
- [ ] `app.py` startup hook calls `validate_portal_base_url`.
- [ ] `scripts/healthcheck-portal-base-url.sh` exists, exits 0 on canonical, non-zero on deprecated.
- [ ] `.env.example` documents the canonical alias rule.
- [ ] **Vercel browser E2E** screenshot proves a real customer-facing portal page renders the React app with line items + Approve button.
- [ ] Approve click flips estimate to `approved` and auto-creates the job.

**F7**
- [ ] `services/estimate_follow_up_job.py` exists and follows F6 pattern.
- [ ] `register_scheduled_jobs()` registers `process_estimate_follow_ups` with 15-min interval.
- [ ] Unit + functional tests pass.
- [ ] **Vercel browser E2E** + human-confirmed SMS receipt at +19527373312 for an artificially-due Day 3 row.
- [ ] `scheduler.jobs.registered` log line includes the new id.

**F8**
- [ ] `InboxSourceTable` literal includes `"consent"`.
- [ ] `_gather_consent` UNIONs `SmsConsentRecord` rows when `INBOX_SHOW_CONSENT_FLIPS=true`.
- [ ] STOP rows classify as `pending`; START rows classify as `handled`.
- [ ] `opt_outs` and `opt_ins` triage filters work end-to-end.
- [ ] Unit tests cover all four classification cases.
- [ ] **Vercel browser E2E** screenshot of `/inbox?triage=opt_outs` showing the new STOP row from a real phone.
- [ ] Frontend chip bar shows `Opt-outs` / `Opt-ins` chips.

**Cross-cutting**
- [ ] All Level 1-5 validation commands pass.
- [ ] No regressions in `test_sales_pipeline_nudge_job` or `test_email_config` (existing tests).
- [ ] `SIGNOFF-VERIFICATION.md` exists with all 6 Level-5 artifacts.
- [ ] `E2E-SIGNOFF-REPORT.md` updated with RESOLVED status for F4-REOPENED, F7, F8.

---

## COMPLETION CHECKLIST

- [ ] All Phase 1-5 tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All Level 1-5 validation commands executed successfully
- [ ] Full unit + functional test suite passes
- [ ] Zero new ruff / mypy errors (pre-existing 111 unchanged)
- [ ] **Vercel browser E2E (Level 5) artifacts captured** — required, non-negotiable
- [ ] Manual SMS receipt confirmation at +19527373312 for F7
- [ ] Acceptance criteria all met
- [ ] DEVLOG.md updated
- [ ] E2E-SIGNOFF-REPORT.md updated with RESOLVED verdicts

---

## NOTES

### Why Vercel browser E2E is mandatory (and not "nice-to-have")

The F4 bug is a **silent 200**. Every API-only verification this run produced reported "the endpoint returns a portal_url, status 200, looks fine" — and yet every customer-facing email sent today contained a link to a 9-day-old marketing-site bundle. The only way to catch this class of bug is to actually render the page and assert on the bundle.

Concrete failure modes API-only verification misses:
- Vercel project rename → preview alias rotates → old alias 200s with whatever bundle was deployed last
- Vite chunk hash drift between marketing site and React app → both serve from the same alias path with different bundles
- Vercel auth wall → curl returns 200 (HTML login page); a curl-only check thinks the portal works

Real-browser E2E catches all three because it asserts on the rendered DOM (`<title>`, line-items rows, Approve button) — properties that only the right bundle can produce.

### Why F7 mirrors F6 instead of factoring a shared base class

The F6 fix landed 5 days ago. Refactoring both jobs into a common `BackgroundJob` abstraction is **out of scope** here — it's exactly the kind of "while we're at it" refactor the project's CLAUDE-rules forbid for bug fixes. Two ~140-line jobs that are 80% similar is fine; one ~120-line abstraction with two ~40-line subclasses is premature.

### Why F8 is gated behind an env flag

Adding a new source to a UNION query carries non-zero performance risk. Keeping `INBOX_SHOW_CONSENT_FLIPS=false` by default until browser verification confirms (a) the SQL plan is acceptable on the prod-sized table and (b) the operator UX with the new chips is right means we can land the schema + code without flipping the surface. Flip the var on after Phase 4 passes.

### Coordination with already-shipped F4-prior plan

`.agents/plans/e2e-signoff-2026-05-04-bugs-f2-f6.md` introduced the deprecated-host **warning** at `email_config.py:68-79`. This plan **upgrades** that to a **boot failure** in non-test envs. Read the prior plan's F4 section before changing the warning code so we extend (not replace) the existing structlog event name `email.config.deprecated_portal_base_url` — preserving log queries that already exist.

### Memory cross-references

- `feedback_sms_test_number.md` — only +19527373312 may receive real SMS during testing
- `feedback_test_email_only_allowlist.md` — only `kirillrakitinsecond@gmail.com` may receive real email during testing
- `project_e2e_seed_identities.md` — seed customer is `a44dc81f-ce81-4a6f-81f5-4676886cef1a`
- `feedback_no_remote_alembic.md` — no remote alembic from local; env-var flips via dashboard, not CLI

### Confidence score for one-pass execution

**10/10**

All gaps from the original 8/10 are now closed:

- **F8 frontend chip-bar location** — confirmed at `frontend/src/features/schedule/components/InboxQueue.tsx:48-55` (FILTER_OPTIONS), `:59-66` (sourceIcons), `:68-73` (sourceLabels), with type sources at `frontend/src/features/schedule/api/inboxApi.ts`. Tasks 3.5 / 3.5.1 / 3.5.2 give exact line numbers and the exact array entries to add. The `opt_outs` chip already exists at line 53 — implementer is **extending** an established three-place change (FILTER_OPTIONS + sourceIcons + sourceLabels), not designing a new chip system.

- **F7 cron-fire incantation** — exact `railway run --service Grins-dev --environment dev -- python -c "..."` command inlined in Task 4.7 Step C, including the seed step and the verification SQL. Documented gotcha that distinguishes this from the broken `railway run alembic` pattern at `docs/troubleshooting/Leads/leads-network-error-500.md:516`. No improvisation needed.

- **Real-time human confirmation loops** — every email and SMS send in Phase 4 now has a paired pause-and-wait-for-human step. The user is monitoring `kirillrakitinsecond@gmail.com` and `+19527373312` simultaneously; the plan never advances past a send without explicit "got it" confirmation **with URL preview** (which is the only way to verify F4 from the customer's perspective).

Foundations:
- F4 fix is a 1-line env flip + a 20-line code change. Existing test file (`test_email_config.py`) and existing structlog event name (`email.config.deprecated_portal_base_url`) get extended, not replaced.
- F7 is a copy-mirror of an already-shipped pattern (F6, 5 days old, same shape).
- F8 has a clear extension point (`_gather_*` methods + already-stubbed `_FILTER_OPT_OUTS` constant) — the SQL UNION pattern (`heapq.merge` over parallel `asyncio.gather`) is already established.
- Vercel MCP tools, `agent-browser` skill, `.vercel/project.json` (`prj_SZexdljNexKryhM7PAJn3DQkDbSK` / `team_FANuLIVR0JFqdlXMuNgcJKvi`) all confirmed present in the operator's environment.
- All test allowlists (`+19527373312` / `kirillrakitinsecond@gmail.com`), seed customer (`a44dc81f-ce81-4a6f-81f5-4676886cef1a`), and operational guardrails (no remote alembic from local) are stated explicitly with their memory citations so the implementer cannot accidentally violate them.

Residual risk:
- The CallRail inbound webhook reaching the dev container reliably for the F8 STOP/START test is the single environmental dependency outside our control (covered by the GOTCHA in Task 4.8). If the webhook is silent for non-fix reasons, the F8 verification will read as a false negative — but that scenario is detectable (audit log empty for the consent flip) before incorrectly reverting code.
