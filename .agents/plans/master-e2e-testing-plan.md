# Feature: Master End-to-End Testing Plan (CRM Update 2)

The following plan is the **single source of truth** for end-to-end testing of the Grin's Irrigation Platform admin dashboard, technician mobile, and customer portals against the **dev Vercel + dev Railway** environment. It is broken into discrete phases that can be executed independently or strung together for a full system test. Pay close attention to:

- **DEV-ONLY EXECUTION** — see the `ENVIRONMENT SAFETY (MANDATORY)` section directly below. This plan is **never** to be executed against `main`/`prod`, and the running agent **must not** push to `main`, merge into `main`, or take any action that mutates the `main` branch or its deployed environment. Read the full policy before starting.
- **VERIFY blocks at the start of every phase** — confirm the feature still exists in source before testing it. Some references in `bughunt/`, older `scripts/e2e/`, and previous plan documents may be **stale** (renames, removals, refactors). The plan flags known stale references explicitly. **Never trust a documented selector or endpoint without grepping source first.**
- **HUMAN checkpoints** — phases involving SMS replies can run **either** with a human at +19527373312 reading and replying (Y/R/C/STOP) **or** with the HMAC-signed webhook simulator at `e2e/master-plan/sim/callrail_inbound.sh`. Pre-release smoke must include at least one human run; CI/iteration cycles can use the simulator.
- **Variant lanes** — admin desktop, technician iPhone, customer email/SMS portal each have their own auth and viewport. Tech-mobile-only features (on-site payment collection, on-my-way SMS) cannot be tested from the admin lane.
- **Re-runnability** — every phase has a `Re-run criteria` block stating whether it needs fresh seed data, can run against existing data, or has cross-phase dependencies that cannot be skipped.
- **Phase timing in the final report** — every full-plan run MUST record, in its sign-off report, how long each phase took and where time was spent within each phase. This is a hard requirement spelled out in `Phase 23b — E2E Sign-off Report`; do not skip it. The point is to give the next operator a realistic budget per phase, not to embed a frozen schedule in this plan itself.

---

## TEST RECIPIENTS (HARD RULE — added 2026-05-04 by user directive)

**Every** real SMS sent during ANY E2E run from this plan MUST go to **`+19527373312`**.
**Every** real email sent during ANY E2E run from this plan MUST go to **`kirillrakitinsecond@gmail.com`**.

There are **no other allowed recipients**. This is not a soft preference — it is a hard rule that overrides any other directive in this plan, in `Testing Procedure/`, in any bughunt doc, or in any feature plan. If a step would otherwise route SMS or email to a different number/address (e.g., a synthetic `@example.com`, a generic test phone, the seed customer's pre-existing email if it differs), **rewrite the step inline** to retarget the allowlisted recipient before executing.

### Required scope for the "real email" rule

The real-email requirement is not just for the initial estimate send. **Every email in every sequence triggered by an E2E run must actually be delivered to `kirillrakitinsecond@gmail.com`** so the operator can visually inspect the rendered template, the subject line, the option presentation, and the call-to-action. This includes (non-exhaustive):

- **Estimate pipeline sequence** (P4 / P4d / P4e / P4f / P5):
  - Initial estimate-sent email (`message_type=estimate_sent`)
  - Estimate option variants — if an estimate has multiple option presentations (line-item bundles, tiers, alternatives), each variant must produce its own email so the operator can confirm each rendering
  - Estimate nudge / followup emails (P4f, sales-pipeline auto-nudge cron)
  - Signed-PDF email after customer approves (`Your signed estimate ...`)
  - Approval / rejection notification emails (admin-side internal notification)
  - Bounce-event notification (P5 step 8)
- **Subscription / onboarding sequence** (P15): welcome email, receipt, week-of-confirmation
- **Invoice sequence** (P13, P14): invoice-sent, payment-link, payment-receipt, past-due reminders, lien-warning
- **Job / appointment lifecycle** (P8, P11, P12): cancellation notifications when channel=email, receipt-after-payment

**No simulator short-cuts for email path.** `sim/resend_email_check.sh poll` is a *verification* tool (it polls `/api/v1/sent-messages` to confirm Resend recorded the send). It does not eliminate the user's real-inbox check; it complements it. Every step that fires an email must be paused at a HUMAN checkpoint asking the operator to confirm the email landed and looks correct.

### Why this rule is hardened at the top

If the operator (or an agent executing this plan) routes a single SMS/email to a non-allowlisted recipient, that's an immediate violation: real customers don't expect test traffic, and the dev allowlist is the only thing that prevents accidental contact with production-shaped data. The 2026-05-04 user directive that produced this section: *"send all texts to 9527373312 for that email and the phone number I just added, you should specify in the plan that when you do end-to-end testing, you should only be sending to those, which includes this plan. ... I also want you to send all the real emails so I can confirm the different options for estimates. ... we should have all the sequences sent to the email when we're doing end-to-end testing."*

Operationally that means: when in doubt, retarget — don't send. When a step is silent on recipient, default to the allowlist. When a code path picks recipients dynamically (e.g., a customer's stored email), **before** firing the path, verify the customer record's email is `kirillrakitinsecond@gmail.com` and the phone is `+19527373312`; if not, update the customer record first.

---

## ENVIRONMENT SAFETY (MANDATORY)

This is a hard policy, not a guideline. Every E2E run authored against this plan **must obey all four rules below**. Violations are operator errors, not bugs in the plan, and a violating run's findings are not promotable to a sign-off report.

### Rule 1 — Test only against `dev`. Never against `main`/`prod`.

- The harness defaults to `ENVIRONMENT=local` and explicitly supports `ENVIRONMENT=dev`. There is no `prod`/`main` branch in the harness on purpose.
- Every URL in this plan resolves to a **dev**-suffixed Vercel preview or the `grins-dev-dev.up.railway.app` Railway service. If you find yourself about to run a curl against a non-dev hostname, **stop**.
- The probe SMS in Phase 0 + the live SMS in P9/P14/P16 hit a **single** allowlisted phone (`+19527373312`); the live email path hits a **single** allowlisted inbox (`kirillrakitinsecond@gmail.com`). Both allowlists are enforced server-side on dev; the same code paths intentionally **fail closed** on prod-style envs that don't have the allowlist set. Do not "test" the allowlist by running on prod.

### Rule 2 — Never push, merge, force-push, or rebase `main`.

- A run **must not** call `git push origin main`, `git push --force` against any branch, `git rebase main`, `git merge` into `main`, or `gh pr merge`/`gh pr create --base main` while in the testing flow.
- Working-tree edits authored by the running agent (e.g. a Bug E receipt-time fallback) **stay uncommitted** unless the user explicitly approves a commit + push (and even then, the push target is a `dev` branch, never `main`). The 2026-05-04 run captured this exact case: Bug E's fix was staged, the agent asked for direction, the user said "document and move forward" — the staged fix was deliberately left UNCOMMITTED.
- Auto-deploys on dev happen via Railway-on-`dev`-push and Vercel-on-`dev`-push; this is fine. Deploys to prod must always go through human-driven release engineering, never through a test-run.

### Rule 3 — Never run destructive ops against shared dev state.

- No `alembic downgrade` against the deployed Railway dev DB (the user's running memory `feedback_no_remote_alembic.md` makes this explicit: push to branch and let Railway apply migrations forward; never drive alembic from local pointing at `*.railway.{app,internal}` unless `ALEMBIC_ALLOW_REMOTE=1` is explicitly set).
- No `psql -c "DROP TABLE..."` / `TRUNCATE` against dev. The seed customer + tech + admin records are shared across runs.
- Test artifacts left over from a run (test leads / customers / jobs / invoices) are tolerated as fixture data; cleanup is best-effort (FK constraints on `sms_consent_record` block hard-delete for many leads, by design — that's an audit-trail safety, not a bug).

### Rule 4 — Never bypass HMAC, signing, or auth in simulators.

- The CallRail / Stripe / SignWell simulators in `e2e/master-plan/sim/` exist to remove the human-on-phone dependency for CI iteration, **not** to bypass security. Wrong HMAC must continue to return 403; replay protection must continue to dedup. If a simulator authored mid-run starts using the secret as a constant or skipping signature verification, that's a regression of the plan, not a feature.
- The dev backend's `_verify_webhook_signature` and Stripe SDK signature verification stay enforced end-to-end. If you observe a webhook simulator that has been "made easier" by removing HMAC, restore HMAC before running the simulator.

### What the running agent SHOULD do when in doubt

- Ask the user before any commit, push, branch creation, or branch deletion.
- Ask the user before any `--force` flag.
- Ask the user before any operation whose target hostname is not under `*-dev-*.vercel.app`, `grins-dev-*.up.railway.app`, or `localhost`/`127.0.0.1`.
- For destructive-looking local operations (`rm -rf`, mass `git reset --hard`, etc.), default to NOT running and asking instead.

The 2026-05-04 run's verdict-gate explicitly states: *"No release merges into main until this run's report is committed alongside the code with verdict ALL PASS."* That sentence is operative regardless of how this plan evolves.

## Feature Description

A re-runnable, agent-browser-driven E2E test plan that exercises every feature surface area enumerated in `instructions/update2_instructions.md` (16 sections, 1230+ lines). It includes UI flows, REST API verification, database state assertions, screenshot capture, console/error monitoring, responsive viewport sweeps, unit/integration/property-based test runs, and human-in-the-loop SMS reply verification. The plan replaces the scattered fragments currently living in:

- `Testing Procedure/` (REST-API-driven manual runbook, paths A–J)
- `e2e/` and `scripts/e2e/` (40+ shell scripts, several with selector drift)
- `bughunt/*.md` (E2E verification snippets embedded in bug-fix plans)
- `.agents/plans/*.md` (per-feature plans with "validation" sections)
- `feature-developments/scheduling gaps/` (16 gap documents)
- `.kiro/steering/{agent-browser,e2e-testing-skill,frontend-testing,spec-testing-standards}.md`
- `feature-developments/CallRail collection/` (inbound webhook setup)

…and unifies them into one document.

## User Story

```
As a release-gate engineer (or AI testing agent)
I want a single re-runnable script-of-scripts that walks every feature in the
  CRM end-to-end, takes screenshots, queries the database, and clearly flags
  human-in-the-loop checkpoints
So that I can verify any release branch (or any single changed feature) with
  one command, capture irrefutable visual evidence, and stop trusting stale
  fragments scattered across 80+ markdown files
```

## Problem Statement

E2E coverage exists but is **fragmented** across at least seven directories with overlapping, often-stale instructions. Worse, several existing shell scripts reference selectors or endpoints that no longer match the current frontend (e.g., `[name='email']` login fields when the actual selectors are `[data-testid='username-input']`/`[data-testid='password-input']`). There is **no single document** that:

1. Sequences phases by data dependency (lead → customer → estimate → appointment → invoice → payment).
2. Distinguishes admin-desktop from tech-iPhone from customer-portal lanes.
3. Verifies each claimed endpoint/selector against current source before assuming it.
4. Documents human-in-the-loop SMS checkpoints inline (`reply Y now`, etc.).
5. Provides a re-runnable matrix where any single phase can be exercised in isolation when only that surface changed.
6. Includes the unit/integration/lint/typecheck sweeps in the same loop.

Without this, regressions slip through, screenshots are inconsistent, and "how do I test feature X?" requires hunting through dated docs.

## Solution Statement

Author `.agents/plans/master-e2e-testing-plan.md` (this document) as the canonical, source-of-truth plan. Each phase contains:

- **Goal** — what's being verified.
- **Prerequisites** — which earlier phases (if any) must have run, plus env vars / seed identities.
- **VERIFY (source check)** — exact `grep`/`Read` commands the testing agent must run to confirm the feature still lives where the plan claims, and what to do if it doesn't (re-resolve before proceeding).
- **Variant lane** — admin / tech-mobile / public.
- **Steps** — agent-browser commands, REST verifications, DB checks, screenshots.
- **Human checkpoints** — clearly boxed `🟡 HUMAN ACTION REQUIRED` blocks with the exact text to send the phone-holder.
- **Acceptance** — pass/fail criteria.
- **Cleanup** — teardown for the phase or pointer to global cleanup phase.
- **Re-run criteria** — whether the phase can be invoked standalone.
- **Stale reference watchlist** — anti-claims to verify against (e.g., "old script claims `[name='email']`; correct is `[data-testid='username-input']`").

## Feature Metadata

**Feature Type**: New Capability (planning artifact, not application code)
**Estimated Complexity**: High — 24 phases, 3 variant lanes, dual-environment target (dev + local), human checkpoints, stale-reference triage
**Primary Systems Affected**: All — leads, sales, customers, jobs, schedule, appointments, SMS, email, portals, invoices, payments, contract renewals, duplicate management, dashboard, AI scheduling, auth, marketing
**Dependencies**: agent-browser CLI ≥ current; Railway CLI linked to `zealous-heart/dev`; SMS allowlist `+19527373312` set; email allowlist `kirillrakitinsecond@gmail.com` set; `GOOGLE_REVIEW_URL` set on dev; CallRail webhook configured for inbound SMS. **Phone-holder availability for Phases 9, 14, 16 is NOT required when using `e2e/master-plan/sim/*` simulators** — see Auxiliary Harness section below.

---

## BUG STATUS REFERENCE (verified 2026-05-02)

This plan was authored after the umbrella plan Phase 0–5 work landed. The bugs documented in `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` and the 5 new tech-mobile bugs in `.agents/plans/appointment-modal-payment-estimate-pricelist-umbrella.md` are **largely closed**. Phase tests still verify each repro, but the expected outcome is now PASS.

### Original Stripe Payment Links bugs

| # | Title | Status | Fix evidence |
|---|---|---|---|
| 1 | Alembic multi-head crashed dev backend | **CLOSED** | Commit `102df83` — merge migration `20260502_120000_merge_payment_link_branches.py`. CI guard added in `01cc14a` (`scripts/check-alembic-heads.sh` + `.github/workflows/alembic-heads.yml`). |
| 2 | `send_payment_link` returns 500 on email-allowlist hard-block (should be 422) | **CLOSED** | Commit `01cc14a`. `services/invoice_service.py:39` imports `EmailRecipientNotAllowedError`; `:1038` catches it. Test: `tests/unit/test_send_payment_link_email_allowlist.py`. |
| 3 | SMS soft-fail silently falls through to email | **CLOSED** | Commit `01cc14a`. `invoice_service.py:961` declares `attempted_channels` + `sms_failure_reason`; mapped at `:990,997,1004,1011,1018`; threaded through `_record_link_sent` at `:1141-1166`. FE surfaces in `PaymentCollector.test.tsx`, `InvoiceDetail.test.tsx`. |
| 4 | CORS headers missing on 5xx | **CLOSED** | `app.py:230` `_catch_unhandled_exceptions` middleware + `:958` `unhandled_exception_handler`. Test: `tests/integration/test_cors_on_5xx.py`. |
| 5 | Seeder reuses customer by phone but doesn't refresh email/opt-ins | **CLOSED** | `scripts/seed_e2e_payment_links.py:59-67` — reuse branch now `PUT`s email/opt-ins; prints `(reused, refreshed)`. |
| 6 | `e2e/payment-links-flow.sh` clicks first `.fc-event` not seeded | **CLOSED (alternative mechanism)** | `e2e/payment-links-flow.sh:69-84` Journey 1 now requires `APPOINTMENT_ID` env, queries `[data-testid='appt-card-$APPOINTMENT_ID']` from `ResourceTimelineView/AppointmentCard.tsx:178`. |
| 7 | Railway `serviceManifest.build.builder = "RAILPACK"` cosmetic drift | **NEEDS RUNTIME CHECK** | Runbook documentation landed (`docs/payments-runbook.md:187-195`); the actual Railway dashboard pin is operator-side and only verifiable on the next deploy by inspecting `serviceManifest.build`. |

### 5 new tech-mobile E2E re-run bugs (per commit `9e23502`)

Sourced from `.agents/plans/appointment-modal-payment-estimate-pricelist-umbrella.md` lines 1574–1640.

| # | Title | Status | Fix |
|---|---|---|---|
| 12 (P1) | `size_tier` SubPicker silently empty | **CLOSED** in `f0a1e18` | `SizeTierSubPicker.tsx:40-41` reads `obj.price ?? obj.labor_amount`; new test cases in `SubPickers.test.tsx`. |
| 13 (P0) | Customer portal `EstimateReview` crashes on `business.company_logo_url` | **CLOSED** in `f0a1e18` | `schemas/portal.py:60-70` adds `company_address/phone/logo_url` to `PortalEstimateResponse`; `SettingsService.get_company_info` populates. New test: `test_portal_estimate_response_includes_company_branding`. |
| 14 (P0) | `collect_payment` crashes on cash/check/venmo/zelle (positional-arg bug) | **CLOSED** in `b53ac1f` | `appointment_service.py:2047, 2089` now unpack `**kwargs` instead of positional dict. |
| 15 (P0) | `TimelineRow` "Element type is invalid" (missing `payment_received` kind) | **CLOSED** in `f0a1e18` | `AppointmentCommunicationTimeline.tsx:45,55` adds `payment_received: Receipt` icon + `text-emerald-600`; defensive fallback for unknown kinds. Test exists. |
| 16 (P1) | `payment_method='stripe'` short-circuits to PAID | **CLOSED** in `f0a1e18` | `appointment_service.py:83` `STRIPE_DEFERRED_METHODS` constant; `:2030,2033,2067,2086,2111` gate the PAID transition + receipt SMS; webhook handler now fires receipt. New tests: `test_collect_payment_{stripe,credit_card}_method_skips_paid_transition`, `test_payment_intent_succeeded_fires_customer_receipt`. |

**Net open**: only Bug 7 (cosmetic Railway dashboard pin). All other repros are expected to PASS in their respective phases:
- Bug #12 (`size_tier` SubPicker silently empty) → covered by **Phase 4c step 10** regression check.
- Bug #13 (`EstimateReview` crash on `business.company_logo_url`) → covered by **Phase 4d** acceptance criteria + **Phase 5**.
- Bug #14 (`collect_payment` positional-arg crash on cash/check/venmo/zelle) → covered by **Phase 12 sub-cases 4.1–4.4**.
- Bug #15 (`TimelineRow` missing icon kind) → covered by **Phase 12 sub-case 4.9**.
- Bug #16 (`payment_method='stripe'` short-circuits to PAID) → covered by **Phase 12 sub-case 4.5**.
- Original 1 (multi-head Alembic) → covered by P0 deploy health + CI guard.
- Original 2 (email allowlist 500→422) → covered by **Phase 14 step 7**.
- Original 3 (SMS soft-fail transparency) → covered by **Phase 14 step 8**.
- Original 4 (CORS on 5xx) → covered by **Phase 1 step 13**.
- Original 5 (seeder reuse hygiene) → covered by **Phase 14 step 10**.
- Original 6 (wrong appointment clicked) → covered by **Phase 14 step 11**.

### Other regression checks added in the 2026-05-02 coverage audit pass

These are bugs / gaps from older bughunts and plans whose fix has landed in source and now has an explicit regression step in the master plan:

| Bug / gap | Source | Master-plan coverage |
|---|---|---|
| Stale Authorization header after refresh-interceptor (premature logout) | `bughunt/session_timeout.md` | **Phase 1 step 5.1** |
| Job action dropdown hidden because of `=== 'scheduled'` (a status that never existed) | `bughunt/job_actions_missing.md` | **Phase 7 step 11** |
| Public lead form `min="1"` zone-count keyboard bypass | `bughunt/2026-03-26-e2e-battle-test.md` | **Phase 2 step 11** |
| Lead form Terms checkbox always serialized as `false` | `bughunt/2026-03-26-e2e-battle-test.md` | **Phase 2 step 12** |
| Surcharge price drift between marketing card and Stripe checkout | `bughunt/2026-03-26-e2e-battle-test.md` | **Phase 2 step 13** |
| `provider_thread_id` not persisted on outbound (CR-3 dev-env blocker) | `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` | **Phase 9 E10** |
| `invoice.paid` `billing_reason` branch coverage (CR-4) | `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` | **Phase 21 step 15** |
| Resource timeline 0% capacity / permanent "Loading…" | `bughunt/2026-04-30-resource-timeline-{view-deep-dive,loading-and-capacity-bugs}.md` | **Phase 18 step 8** |
| Cache invalidation on staff reassignment (capacity bars stale) | `.agents/plans/{schedule-resource-timeline-view,fix-resource-timeline-loading-and-capacity-bugs}.md` | **Phase 18 step 8** |
| Stripe `charge.dispute.created` reconciliation | `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` | **Phase 14 step 6** |
| Stripe SMS soft-fail surfaces `attempted_channels` + `sms_failure_reason` | `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` | **Phase 14 step 8** |
| Webhook empty `last_name` produces orphaned agreements | `production-bugs/2026-04-26-webhook-empty-last-name-orphaned-agreements.md` | **Phase 21 step 14** |
| Server-side `days_until_due` / `days_past_due` (M-12) | `bughunt/2026-04-16-medium-bugs-plan.md` | **Phase 13 step 3a** |
| Send Confirmation button missing on DRAFT (M-1) | `bughunt/2026-04-16-medium-bugs-plan.md` | **Phase 8 step 16** |
| Persistent SchedulingTray in pick-jobs | `.agents/plans/pick-jobs-ui-redesign-persistent-tray.md` | **Phase 8 step 17** |
| City-priority sorting on pick-jobs | `.agents/plans/pick-jobs-city-requested-priority-fixes.md` | **Phase 7 step 12** |
| ScheduleVisit conflict detection + drag boundary | `.agents/plans/schedule-estimate-visit-handoff.md` | **Phase 4 steps 14–15** |
| AppointmentDetail secondary actions (notes / tags / photos / reschedule / mark-contacted) | `.agents/plans/appointment-modal-secondary-actions.md` | **Phase 11 step 16** |
| Repeat-Y idempotency + reassurance SMS | `.agents/plans/repeat-confirmation-idempotency.md` | **Phase 9 E2-bis** |
| Post-cancel "R" → `appointment.reschedule_rejected` (Gap 1.B; no reactivation) | `.agents/plans/thread-correlation-hardening.md` | **Phase 9 E11** |
| Late-reschedule rejection (EN_ROUTE / IN_PROGRESS) | `feature-developments/scheduling gaps/gap-01-reschedule-request-lifecycle.md` | **Phase 10 step 7** |
| Invalid appointment-status transition rejection | `.agents/plans/enforce-appointment-state-machine.md`, `gap-04-state-machine-not-enforced.md` | **Phase 10 step 10** |
| Mobile modal CTA visibility (sticky-bar overlap) | `bughunt/2026-03-26-e2e-battle-test.md` | **Phase 22 step 6** |
| ScheduleVisit visual regression (slate/white redesign) | `.agents/plans/schedule-visit-modal-{full-redesign,ui-refresh-high-fidelity}.md` | **Phase 22 step 7** |
| Hard-STOP audit-log entry (`sms.consent.hard_stop_received`) | `gap-05-audit-trail-gaps.md` | **Phase 9 E8 step 5** |
| Informal opt-out alert + audit chain (`flagged` / `confirmed`) | `gap-05` + `gap-06-opt-out-management.md` | **Phase 9 E8b** |
| AppointmentDetail communication timeline endpoint (Gap 11) | `gap-11-appointment-detail-inbound-blind.md`, `.agents/plans/appointment-detail-communication-timeline.md` | **Phase 11 step 15a** |
| Full `AlertType` enumeration emit-test + filters/pagination | `gap-14-dashboard-alert-coverage.md`, `models/enums.py:618` | **Phase 19 steps 9–10** |
| Unified inbox endpoint + 4th queue card (Gap 16 v0) | `gap-16-unified-sms-inbox.md`, `api/v1/inbox.py:28` | **Phase 20 step 9** |
| Customer conversation endpoint (Gap 13) | `gap-13-customer-messages-outbound-only.md`, `api/v1/customers.py:1823` | **Phase 20 step 10** |
| Queue `refetchInterval` polling (Gap 15) | `gap-15-queue-freshness-and-realtime.md`, `useRescheduleRequests.ts:20` etc. | **Phase 20 steps 11–12** |

### Out of scope (verified absent from current source)

The following scenarios from gap docs / plans propose features that are **not yet implemented** in source. They are deliberately NOT in the master plan; they will be re-classified if/when implementation lands. See `.agents/plans/master-plan-coverage-audit.md` §5 for the full list and verification commands. Highlights:

- HOA / group signup codes (`hoa-and-group-signup-codes.md`) — `grep -i "signup_code\|hoa_group\|hoa_id\|group_code" src/` returns 0 matches.
- Stripe Terminal tap-to-pay (`stripe-tap-to-pay-and-invoicing.md`) — M2 hardware shelved per memory; Phase 21 step 12 verifies the uninstall instead.
- MMS / Unicode emoji / non-English (Spanish) inbound handling (`gap-09-mms-unicode-i18n.md`) — no `media_url`, emoji keyword, or locale handling in `services/sms/`.
- Auto-reminder day-2 path for no-reply confirmations (`gap-10` Phase 1) — only the manual queue exists.

**Re-classified during the 2026-05-02 audit** (initially marked out-of-scope, then verified to actually exist and folded into the plan):

- Hard-STOP audit log → `services/sms/audit.py:131` exists; covered in **P9 E8 step 5**.
- Informal opt-out alert + audit chain → `audit.py:140-180`, `sms_service.py:1188`; covered in **P9 E8b**.
- AlertType enum (PENDING_RESCHEDULE_REQUEST etc.) → `models/enums.py:618`; covered in **P19 steps 9–10**.
- Inbox endpoint → `api/v1/inbox.py:28`; covered in **P20 step 9**.
- Conversation endpoint → `api/v1/customers.py:1823`; covered in **P20 step 10**.
- AppointmentDetail timeline endpoint → `api/v1/appointments.py:1013`; covered in **P11 step 15a**.
- Queue `refetchInterval` polling → 4 hooks under `frontend/src/features/schedule/hooks/`; covered in **P20 steps 11–12**.

The E2E Sign-off Report (P23b) consolidates regression status for all 12 bugs.

---

## AUXILIARY HARNESS (lives at `e2e/master-plan/`)

A shell harness is provided so any phase can be invoked against either `local` or `dev` with a single env var:

```bash
# Run a single phase against dev
ENVIRONMENT=dev e2e/master-plan/run-phase.sh 4

# Run all phases sequentially (or a slice)
ENVIRONMENT=dev e2e/master-plan/run-all.sh        # 0..24
ENVIRONMENT=dev e2e/master-plan/run-all.sh 7 14   # only 7..14
```

### Files

- `e2e/master-plan/_dev_lib.sh` — shared helpers: `ab`, `api`, `api_q`, `login_admin`, `login_tech`, `shot`, `shot_full`, `human_checkpoint`, `railway_python`, plus required-env assertions. Defaults to `local`; set `ENVIRONMENT=dev` for dev Vercel + Railway.
- `e2e/master-plan/run-phase.sh` — single-phase dispatcher.
- `e2e/master-plan/run-all.sh` — sequential phase runner with logging.
- `e2e/master-plan/sim/callrail_inbound.sh` — HMAC-signed CallRail inbound SMS reply simulator (Y/R/C/STOP). Eliminates the HUMAN dependency for Phase 9/10/14 smoke iterations. **HMAC verification is preserved end-to-end** — wrong secret → 403, by design.
- `e2e/master-plan/sim/signwell_signed.sh` — SignWell `document_completed` webhook simulator. Eliminates HUMAN for Phase 4 auto-advance + Phase 5 portal-side signing event.
- `e2e/master-plan/sim/stripe_event.sh` — Wrapper around `stripe trigger` for `checkout.session.completed`, `charge.refunded`, `charge.dispute.created`, `invoice.paid` (renewal).
- `e2e/master-plan/sim/resend_email_check.sh` — Polls backend `/api/v1/sent-messages?channel=email` for an email matching `to`+`subject_substring`. Eliminates HUMAN inbox-watch for Phase 5 / 4.
- `e2e/master-plan/sim/_README.md` — operator notes; **never bypass HMAC** in simulators.

### When NOT to use simulators

For pre-release smoke tests, run **with a human** at +19527373312 to catch carrier-level issues simulators bypass (CallRail STOP behavior, rate-limit surfacing, etc.). For first-time changes to provider-integration code, simulators alone are insufficient.

### Per-phase shell scripts

The plan body documents each phase step-by-step. Per-phase shell wrappers (e.g., `e2e/master-plan/phase-04-sales-pipeline.sh`) can be authored incrementally; missing wrappers cause `run-phase.sh` to print a "manual phase" notice and exit 0, allowing `run-all.sh` to continue while the operator walks the phase from this plan.

---

## BUG-REPORTING WORKFLOW — read before logging any finding as a "bug"

**This workflow is mandatory.** A finding is *not* a bug until it has cleared every step below. Hedged or unverified bugs in the sign-off report dilute the signal and force the operator to re-check work that should have been airtight before promotion.

### Step 1 — Stage candidates HERE in the master plan, NOT in the sign-off report

When a phase surfaces something that *looks* off, write it into the **Candidate Findings** section at the bottom of this plan (or inline under the relevant phase) as a candidate, with explicit verification commands. Do **not** write it into the per-run sign-off `e2e-screenshots/master-plan/runs/<RUN_ID>/E2E-SIGNOFF-REPORT.md` yet.

The sign-off report is the **promoted** view — only verified bugs land there. The plan is the **staging** view.

### Step 2 — Verify with 100% confidence before promoting

Run the verification commands. Use the right primitives:

- **API response shape**: always use `curl ... | jq 'keys'` to enumerate the actual response keys. **Never** use `jq '{a, b, c}'` to check whether `a`/`b`/`c` exist — `jq` returns `null` for missing keys, and you cannot distinguish "API returned null" from "field absent from response" by inspecting the output. (The 2026-05-02 run retracted three bugs — B, G, H — that all originated from this exact mistake.)
- **HTTP status**: capture both status and body with `curl -s -o /tmp/r.json -w "HTTP=%{http_code}\n"` and read the body. Don't infer meaning from status alone.
- **Root cause**: read the route handler + the service layer + the model. Pull the exact `file:line` of the offending logic. A symptom-only claim is not a bug.
- **"Value should be populated but isn't"**: confirm against the schema definition and at least one related working record that the field is intended to be populated. Maybe it's opt-in via a query param, computed lazily, or lives inside a nested object you didn't print.
- **Form-flow tests**: confirm whether your test fill set the field deliberately or whether a helper picked the first non-empty option. (Bug C in the 2026-05-02 run was retracted because a "pick first option" helper picked `Google` for the source dropdown — not a server default.)
- **Provider behavior**: don't claim "API returns wrong status code on X" without confirming X actually triggers the path you think it does. Check the route's exception-handler chain.

### Step 2a — The "symptom vs independent bug" filter

**MANDATORY**: For every candidate finding, ask:
> *"If the parent root-cause bug were fixed today, would this finding still be a bug?"*

If **no** → it is a *symptom* of the parent bug, not an independent defect. Fold it into the parent bug's "If not resolved" section as part of the consequence narrative; do **not** promote it as its own bug. A separate bug entry implies separate fix work and separate test coverage — neither of which is true for symptoms.

Worked example (Bug E retraction, 2026-05-02): I observed that clicking Move-to-Sales produced no toast/modal when Bug D's 500 fired. I promoted "no UX surfacing" as Bug E. But: with Bug D fixed, the request returns 200 and the toast question never arises — there's no independent bug to fix. Bug E should have been a single sentence inside Bug D's "If not resolved" paragraph ("…and the operator gets no UI feedback because the poisoned-session 500 bypasses the standard error path"), not its own promoted entry.

To apply the filter: if you can write the bug entry without referring to the parent root cause at all, it's likely independent. If every sentence has to mention the parent ("when Bug D fires…", "during the poisoned-session 500…"), it's a symptom.

Edge case: if you suspect the FE error-handling path is *also* broken for normal 5xx (independent of the parent bug), **prove it with a different stimulus** — find a known-working route that returns 5xx for valid input, hit it, observe the FE response. Don't infer FE breakage from the FE's response to a poisoned-session 500.

### Step 2b — Never invent or paraphrase a citation

**MANDATORY**: When citing the spec / plan / instructions / steering docs / source comments to support a bug claim (e.g., *"the spec says X is required"*), the citation must be a **literal quote** found by `grep -n` against the cited file. If you can't produce the `file:line` for the quote in under 30 seconds, **don't include the citation** — make the argument on its own merits or drop the claim.

Hallucinated citations were the second compounding failure on Bug E ("Compare to `update2_instructions.md` 'system MUST surface backend failures' expectation" — that quote does not exist in the file). A bug entry with a fabricated authority cite is worse than one with no cite, because the reader takes the cite at face value and propagates the false claim.

### Step 3 — Promote to sign-off only with the full structure

Once a candidate has cleared verification with 100% confidence, promote it to that run's sign-off (`e2e-screenshots/master-plan/runs/<RUN_ID>/E2E-SIGNOFF-REPORT.md`). The promoted entry **must** include:

1. **Repro** — minimal commands or steps. A second engineer should be able to reproduce in under 5 minutes.
2. **Root cause** — exact `file:line` reference + the offending logic. If root cause is *suspected but not yet confirmed*, label it explicitly as "(suspected)" and don't claim certainty.
3. **Benefit analysis — TWO paragraphs, not optional:**
   - **If not resolved**: what real-world consequence happens? Who feels it (operator, customer, dev, security posture)? What workflow breaks or degrades? Be concrete: *"operator clicks button, page silently doesn't update, lead is stuck in `contacted` state and ops can't move it forward — they have to fall back to the legacy `/convert` API path manually."*
   - **If resolved**: what changes? What previously-broken workflow starts working, what data quality improves, what alert/error stops firing, what test cluster closes? Be concrete in the same way.

A bug entry without the benefit analysis cannot be prioritized — it's just a defect tally. With the analysis, the operator can stack-rank by impact-of-fixing and the priority is obvious.

### Step 4 — Retract aggressively if Step 2 fails

If verification can't establish the bug with 100% confidence, **retract or reclassify**:

- **Retract**: drop it entirely. Do not soften ("possibly a bug…", "appears to be…"). Hedged bugs in a sign-off report are worse than no bugs — they cost the reader time and erode trust.
- **Reclassify** as `(gap)` or `(informational)` or `(non-bug observation)` if there's still something worth noting that isn't a defect. The retracted-bugs section of the sign-off should explicitly list what was retracted and why, so the workflow's rigor is auditable.

### Worked examples from the 2026-05-02 run

- **Bug D (promoted, BLOCKER)** cleared the workflow: repro via two `curl` commands, root cause traced to `lead_service.py:1158` with the exact line + Railway-logs trace of `audit_log_actor_id_fkey` violation, benefit analysis showing 11 phases unblock + ~12 unit-test failures close once it's fixed.
- **Bug B (retracted)** failed Step 2: claim was based on `jq '{first_name, last_name}'` returning null. Re-check with `jq 'keys'` showed those keys don't exist on the response — the actual `name` field IS populated. Symptom misread; no bug.
- **Bug G (retracted)** failed Step 2: same `jq` trap. Customer detail keys do not include `total_jobs` or `total_invoices`; the rollups live inside `service_history_summary`. No bug.
- **Bug C (retracted)** failed Step 2: I assumed `lead_source="google_ad"` was a server default. `lead_service.py:494-498` shows the actual default is `LeadSourceExtended.WEBSITE.value`. The `google_ad` value came from my test-fill helper picking the first non-empty option in the "How did you hear about us?" dropdown (which is `Google`). Test artifact, not a bug.
- **Bug H (retracted)** failed Step 2: route is explicitly declared `response_model=list[RenewalProposalResponse]` — the bare-list shape IS the documented contract for that endpoint, not an inconsistency.
- **Bug E (retracted)** failed Step 2a + Step 2b: it was a symptom of Bug D (clicking Move-to-Sales when the underlying 500 fires produces no toast — but with Bug D fixed, the request returns 200 and the toast question never arises). Compounded by a fabricated citation (`"update2_instructions.md says system MUST surface backend failures"` — that quote is not in the file). Two separate workflow violations in one entry; both Step 2a and Step 2b were authored after this retraction to prevent recurrence.

### Candidate Findings (staging area)

Add new candidates here under a per-phase heading. Each candidate must include verification commands. Promote to sign-off only after running those commands and clearing the workflow above.

```
#### Phase X — <slug>

**Symptom**: <what was observed>
**Verification commands**:
  curl ... | jq 'keys'
  grep -n "..." src/...
**Status**: candidate (not yet verified)
```

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: READ THESE BEFORE EXECUTING THE PLAN

**Steering / methodology (from `.kiro/steering/`):**

- `.kiro/steering/agent-browser.md` — agent-browser CLI quick reference (open, snapshot, click, fill, screenshot, eval, sessions, headers).
- `.kiro/steering/e2e-testing-skill.md` — 7-phase methodology (research → start app → browser → DB → fix → responsive → cleanup); local URLs and key routes.
- `.kiro/steering/frontend-testing.md` — Vitest + RTL patterns, agent-browser validation script template.
- `.kiro/steering/spec-testing-standards.md` — required testing requirements (unit + functional + integration + agent-browser + lint/types + quality gate).
- `.kiro/steering/frontend-patterns.md` — `data-testid` convention (`{feature}-page`, `{feature}-table`, `{feature}-form`, `{action}-{feature}-btn`).
- `.kiro/steering/code-standards.md` — three-tier testing markers (`@pytest.mark.{unit,functional,integration}`); ruff/mypy/pyright commands.
- `.kiro/steering/structure.md` — backend (`src/grins_platform/{api,services,repositories,models,schemas}`) and frontend (VSA `features/`) layout.
- `.kiro/steering/tech.md` — stack, env vars, performance targets.
- `.kiro/steering/pre-implementation-analysis.md` — analysis checklist before executing.
- `.kiro/steering/parallel-execution.md` — parallel subagent patterns.

**Authoritative manual runbook (`Testing Procedure/`):**

- `Testing Procedure/README.md` (lines 1–71) — golden rules, seed identities, run protocol.
- `Testing Procedure/00-preflight.md` (lines 1–140) — env, allowlist, seed, STOP cleanup, probe SMS.
- `Testing Procedure/01-path-a-lead-intake.md` — public lead form scenarios.
- `Testing Procedure/02-path-b-lead-to-sales.md` — lead routing + dedup.
- `Testing Procedure/03-path-c-sales-pipeline.md` — sales pipeline stages.
- `Testing Procedure/04-path-d-e-confirmation-yrc.md` (lines 1–187) — Y/R/C/STOP/START flow with phone-holder steps.
- `Testing Procedure/05-path-f-onsite.md` — On-My-Way → Started → Complete.
- `Testing Procedure/06-path-g-admin-cancel.md` — admin cancel + reactivate.
- `Testing Procedure/07-path-h-year-rollover.md` — November onboarding → next year.
- `Testing Procedure/08-path-i-dashboard.md` — dashboard counter invalidation.
- `Testing Procedure/09-path-j-schedule-all.md` — bulk schedule + bulk confirm.
- `Testing Procedure/10-customer-landing-flow.md` — service packages + free quote.
- `Testing Procedure/99-cleanup.md` — teardown SQL.
- `Testing Procedure/scripts/clear_consent.py` — STOP cleanup helper.
- `Testing Procedure/scripts/cleanup.py` — E2E record teardown.

**Existing shell harnesses to reuse / cross-reference:**

- `e2e/_lib.sh` (lines 1–145) — proven agent-browser wrapper with retry + EAGAIN fallback, `psql_q` helper, `login_admin`, `open_first_appointment_modal`, `click_text`, `click_any_text`, `click_first_testid`. **Note**: hard-coded to `BASE=http://localhost:5173`/`API_BASE=http://localhost:8000`. The master plan overrides these via environment for dev runs.
- `e2e/integration-full-happy-path.sh` (lines 1–127) — synthetic full-flow walkthrough; includes responsive viewport sweep template.
- `e2e/phase-{0..5}-*.sh` — umbrella plan phases (estimate approval auto-job, pricelist seed, pricelist editor, line-item picker, payment timeline + receipts, polish).
- `e2e/payment-links-flow.sh` — Stripe payment links flow. **Bug 6 CLOSED** — Journey 1 now requires `APPOINTMENT_ID` env and uses `[data-testid='appt-card-${APPOINTMENT_ID}']` (verified at `ResourceTimelineView/AppointmentCard.tsx:178`).
- `e2e/schedule-resource-timeline.sh` — resource timeline view.
- `e2e/tech-companion-mobile.sh` — tech mobile schedule (key reference for Phase 11).
- `e2e/test-webauthn-passkey.sh` — passkey login flow.
- `scripts/e2e/E2E_REGRESSION_REPORT.md` — known login-selector mismatches and prerequisites.
- `scripts/e2e/test-{leads,sales,customers,jobs,schedule,schedule-visit,invoices,invoice-portal,communications,estimate-detail,marketing,mobile-staff,session-persistence,navigation-security,agreement-flow,sms-lead,ai-scheduling-*,...}.sh` — older feature-specific scripts; **selector drift likely; verify before reusing**.
- `scripts/agent-browser/validate-{dashboard,agreement-detail,agreements-tab,jobs-tab,leads-tab,operational-queues}-modifications.sh` — newer focused validators.

**Surface area spec (the "what to test"):**

- `instructions/update2_instructions.md` (lines 1–1230) — 16 sections; lifecycle flow diagram (lines 95–455); SMS sequence catalog (#1 confirmation, #1a/b/c replies, #2 OnMyWay, #3 Google Review, #4 past-due mass, #5 upcoming-due mass, #6 lien notice); job vs appointment status decoupling; service packages onboarding; contract renewals proposal flow; duplicate management nightly job + merge rules.

**Backend source (cross-reference for endpoint paths):**

- `src/grins_platform/api/v1/router.py` (lines 1–449) — full router inventory; **52 routers** verified.
- `src/grins_platform/api/v1/appointments.py` — `POST /api/v1/appointments/{id}/send-confirmation` line 1172, bulk `POST /api/v1/appointments/send-confirmations` line 544.
- `src/grins_platform/api/v1/leads.py` — leads CRUD, conversion endpoints. Verified routing endpoints: `PUT /api/v1/leads/{id}/contacted` (line 639, "Mark Contacted"), `POST /api/v1/leads/{id}/move-to-jobs` (line 577), `POST /api/v1/leads/{id}/move-to-sales` (line 609), and the legacy DEPRECATED `POST /api/v1/leads/{id}/convert` (line 485). Public create: `POST /api/v1/leads` (line 135). Admin create: `POST /api/v1/leads/manual` (line 217), `POST /api/v1/leads/from-call` (line 188).
- `src/grins_platform/api/v1/sales.py` — sales metrics only (`GET /api/v1/sales/metrics` at line 41).
- `src/grins_platform/api/v1/sales_pipeline.py` — sales pipeline advance/convert. Mounted at prefix `/sales` (router.py:315), so paths are nested under `/sales/pipeline/`. Verified: `POST /api/v1/sales/pipeline/{entry_id}/advance` (line 258), `POST /api/v1/sales/pipeline/{entry_id}/convert` (line 431), `POST /api/v1/sales/pipeline/{entry_id}/force-convert` (line 466).
- `src/grins_platform/api/v1/portal.py` — public estimate review / contract sign / invoice portal endpoints. Verified: `GET /api/v1/portal/estimates/{token}` (line 224), `POST /api/v1/portal/estimates/{token}/approve` (line 307), `POST /api/v1/portal/estimates/{token}/reject` (line 399), `POST /api/v1/portal/contracts/{token}/sign` (line 486), `GET /api/v1/portal/invoices/{token}` (line 577). **Note**: `manage-subscription` is in `checkout.py` (`POST /api/v1/checkout/manage-subscription` at line 214), NOT in portal — even though the frontend route is `/portal/manage-subscription`.
- `src/grins_platform/api/v1/contract_renewals.py` — renewal proposal endpoints. List `GET /api/v1/contract-renewals` (line 54), detail by `proposal_id`, **per-job** actions are nested: `POST /api/v1/contract-renewals/{proposal_id}/jobs/{job_id}/approve` (line 187), `…/reject` (line 219), `PUT /api/v1/contract-renewals/{proposal_id}/jobs/{job_id}` (line 250) for modify. Bulk: `POST /api/v1/contract-renewals/{proposal_id}/approve-all`, `…/reject-all`.
- `src/grins_platform/api/v1/customers.py` — customer CRUD + dedup. Merge: `POST /api/v1/customers/{id}/merge` (line 254), preview: `…/merge/preview` (line 312).
- `src/grins_platform/api/v1/audit.py` — audit log. Mounted at prefix `/audit-log` (singular, line 385). Watch for plural `/audit-logs` in stale docs — that is wrong.
- `src/grins_platform/api/v1/invoices.py` — invoices. Send Payment Link: `POST /api/v1/invoices/{id}/send-link` (line 723). Mass notify: both `POST /api/v1/invoices/bulk-notify` (line 851) AND `POST /api/v1/invoices/mass-notify` (line 914) exist.
- `src/grins_platform/api/v1/sms.py` — `POST /api/v1/sms/send` line 39, `POST /api/v1/sms/webhook` line 101.
- `src/grins_platform/api/v1/callrail_webhooks.py` — inbound CallRail webhook (HMAC-verified). Mounted at prefix `/webhooks/callrail`. Inbound endpoint: `POST /api/v1/webhooks/callrail/inbound` (line 211). HMAC verification at line 243; returns 403 on failure. Env var: `CALLRAIL_WEBHOOK_SECRET`.
- `src/grins_platform/api/v1/resend_webhooks.py` — Resend bounce/complaint webhook. Mounted at `/webhooks/resend`. `POST /api/v1/webhooks/resend` (line 65). HMAC verification at line 82. Env var: `EmailSettings().resend_webhook_secret`.
- `src/grins_platform/api/v1/signwell_webhooks.py` — SignWell signing webhook (auto-advances Sales row). Mounted at `/webhooks/signwell`. `POST /api/v1/webhooks/signwell` (line 48). `X-Signwell-Signature` header verified line 69. Env var: `SIGNWELL_WEBHOOK_SECRET`.
- `src/grins_platform/api/v1/webhooks.py` — Stripe webhook. `POST /api/v1/webhooks/stripe` (line 1386). Uses `settings.stripe_webhook_secret` (line 1424). Env var: `STRIPE_WEBHOOK_SECRET`.
- `src/grins_platform/services/sms/base.py` — `SMS_TEST_PHONE_ALLOWLIST` enforcement.
- `src/grins_platform/migrations/versions/` — alembic migrations (multi-head guardrail per Stripe payment links plan).

**Frontend source (cross-reference for routes + selectors):**

- `frontend/src/core/router/index.tsx` (lines 1–318) — full route table (verified):
  - Public: `/login`, `/portal/estimates/:token`, `/portal/contracts/:token`, `/portal/invoices/:token`, `/portal/manage-subscription`
  - Tech-only: `/tech` (mobile gated by role + PhoneOnlyGate)
  - Admin (under ProtectedLayoutWrapper): `/dashboard`, `/customers`, `/customers/:id`, `/leads`, `/leads/:id`, `/work-requests` (redirect), `/jobs`, `/jobs/:id`, `/schedule`, `/schedule/generate`, `/schedule/mobile`, `/schedule/pick-jobs`, `/staff`, `/staff/:id`, `/invoices`, `/invoices/:id`, `/agreements`, `/agreements/:id`, `/sales`, `/sales/:id`, `/accounting`, `/marketing`, `/communications`, `/alerts/informal-opt-out`, `/estimates/:id`, `/contract-renewals`, `/contract-renewals/:id`, `/settings`
- `frontend/src/features/auth/components/LoginPage.tsx` — login form (verified selectors: `[data-testid='username-input']` at line 162, `[data-testid='password-input']` at line 182, `[data-testid='login-btn']` at line 219, `[data-testid='passkey-login-btn']` at line 259 for biometric fallback).
- `frontend/src/features/auth/components/UserMenu.tsx` — user-menu, settings-btn, logout-btn testids (verified).
- `frontend/src/features/auth/components/PasskeyManager.tsx` — `[data-testid='security-page']`, `add-passkey-btn`, `passkey-loading-spinner`, `passkey-empty-state`.
- `frontend/src/features/schedule/components/SchedulePage.tsx` + `AppointmentList.tsx` — verified selectors: `[data-testid='view-list']` at `SchedulePage.tsx:435`, `[data-testid='appointment-row']` at `AppointmentList.tsx:342`, `[data-testid='view-appointment-${id}']` at `AppointmentList.tsx:202`. Confirmation buttons live in `SendConfirmationButton.tsx` (compact: `send-confirmation-icon-${id}` line 62; full: `send-confirmation-btn-${id}` line 77) and `SendAllConfirmationsButton.tsx:74` (`send-all-confirmations-btn`). Day-level: `overflow-menu-item-send-confirmations` at `SchedulePage.tsx:402`.
- `frontend/src/features/tech-mobile/` — tech mobile layout + schedule page. **`PhoneOnlyGate` is applied inside `TechMobileLayout`, not at the route level.** The route only checks `allowedRoles=['tech']` (router.py:184); the viewport guard runs after layout mounts. Tech identities are seeded via `migrations/versions/20250626_100000_seed_demo_data.py` (and `scripts/seed_tech_companion_appointments.py:5,307-309`): usernames `vasiliy`, `steve`, `gennadiy`; password `tech123` (bcrypt hash baked into the seed migration).
- `frontend/src/pages/portal/{EstimateReview,ContractSigning,InvoicePortal,SubscriptionManagement}.tsx` — public portal pages.

### New Files to Create (auxiliary to this plan)

- `.agents/plans/master-e2e-testing-plan.md` — **this document**.
- `e2e/master-plan/_dev_lib.sh` — fork of `e2e/_lib.sh` parameterized for dev environment (`BASE`, `API_BASE`, `TOKEN`, `RAILWAY_PROJECT`, `RAILWAY_ENV`, `RAILWAY_SERVICE`); REST-only `psql_q` replacement (`api_q`) for dev, with optional `railway ssh` fallback for queries that lack REST equivalents.
- `e2e/master-plan/run-phase.sh <N>` — single-phase invoker (loads `_dev_lib.sh`, dispatches to `phase-<N>-*.sh`).
- `e2e/master-plan/run-all.sh` — sequential phase runner with checkpoints for human steps; aborts on first failure.
- `e2e/master-plan/phase-XX-*.sh` — one shell file per phase (some phases will be authored as part of the implementation; many can borrow heavily from existing scripts).
- `e2e-screenshots/master-plan/runs/<RUN_ID>/` — **per-run root.** Every artifact this run produces (sign-off markdown, human-checkpoint log, the full `phase-{NN}-{slug}/` screenshot tree) lives here so a run is fully self-contained and preserved verbatim. `RUN_ID` defaults to `$(date +%Y-%m-%d)`; for multiple runs in a single day, set explicitly (e.g. `RUN_ID=2026-05-04-rerun-after-bugD`). The runner refuses to overwrite an existing run dir.
- `e2e-screenshots/master-plan/runs/<RUN_ID>/E2E-SIGNOFF-REPORT.md` — **per-run** sign-off markdown.
- `e2e-screenshots/master-plan/runs/<RUN_ID>/_human-checkpoints.md` — per-run human-only step log generated by the runner.
- `e2e-screenshots/master-plan/runs/<RUN_ID>/phase-{NN}-{slug}/...` — **per-run** screenshot dest tree. Every phase writes its `.png`, `.console.log`, and `.errors.log` files under this dir.

**Note**: the master plan does **not require** new shell scripts to be implemented up front. Phases are authored to be runnable manually by an agent armed only with this document, the existing `e2e/_lib.sh` patterns, and the Testing Procedure runbook. The auxiliary harness above is an optional wrapper for fully automated invocation.

### Relevant Documentation — READ THESE BEFORE EXECUTING

- [agent-browser README on npm](https://www.npmjs.com/package/agent-browser) (search "agent-browser" — verify version on `agent-browser --version`).
  - Why: confirms current CLI flag set; the flags in `.kiro/steering/agent-browser.md` should match.
- [Vitest 4 docs](https://vitest.dev/) — `npm test` runs `vitest run`.
- [React Testing Library queries](https://testing-library.com/docs/queries/about) — preferred patterns for component tests inside individual phase verifications.
- [Stripe Payment Links + webhooks](https://stripe.com/docs/payment-links) — for Phase 14 reconciliation verification (metadata.invoice_id is the deterministic key per memory entry).
- [SignWell webhook reference](https://developers.signwell.com/) — for Phase 4 / Phase 5 auto-advance verification.
- [CallRail SMS API + webhooks](https://apidocs.callrail.com/#text-messages) — for inbound webhook simulation in Phase 9.
- [Resend webhooks](https://resend.com/docs/dashboard/webhooks/introduction) — for Phase 5 bounce verification.
- [WebAuthn / SimpleWebAuthn browser](https://simplewebauthn.dev/docs/) — for Phase 1 biometric passkey.

### Patterns to Follow

#### agent-browser invocation pattern (from `e2e/_lib.sh:42-70`)

Always use the retry wrapper (with eval fallback for click flakes), not raw `agent-browser`:

```bash
ab() {
  local tries=0
  while (( tries < 3 )); do
    if agent-browser --session "$SESSION" "$@" 2>/tmp/ab.err; then
      return 0
    fi
    tries=$((tries + 1))
    sleep 2
  done
  # Eval fallback for click EAGAIN flakes — see _lib.sh
  ...
}
```

#### Login pattern (from `e2e/_lib.sh:76-84`)

```bash
ab open "$BASE/login"
ab wait --load networkidle
ab fill "[data-testid='username-input']" "$E2E_USER"
ab fill "[data-testid='password-input']" "$E2E_PASS"
ab click "[data-testid='login-btn']"
ab wait --load networkidle
sleep 2
```

⚠️ **Stale-reference watch**: older scripts in `scripts/e2e/` use `[name='email']` or `[data-testid='email-input']`. These are wrong — current source uses `username-input`. See `scripts/e2e/E2E_REGRESSION_REPORT.md` for the original drift report.

#### REST verification pattern (Testing Procedure / 04-path-d-e:48-60)

```bash
TOKEN=$(curl -s "$API_BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
export TOKEN

curl -s "$API_BASE/api/v1/appointments/$APT" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])'
```

#### Screenshot naming pattern

- Per-run root: `e2e-screenshots/master-plan/runs/${RUN_ID}/` (set once at the start of the run; see Phase 23b "Per-run directory convention").
- Phase dir: `${RUN_DIR}/phase-{NN}-{slug}/`
- File: `{step:02d}-{action-slug}.png` — e.g. `01-login-loaded.png`, `02-credentials-filled.png`, `03-dashboard-rendered.png`.
- Annotate with `--annotate` for screenshots used in human-checkpoint context (numbered overlays).
- Take screenshots **before** and **after** every state-changing interaction and at every assertion point.

#### Database verification — REST-first

Against dev Railway, **direct psql is unreachable** (`postgres-phd.railway.internal`). Use REST API for all verifications when an endpoint exists. For deeper queries:

```bash
# Fallback: railway ssh runs python inside the deployed container
cp /tmp/query.py
B64=$(base64 < /tmp/query.py | tr -d '\n')
railway ssh --service Grins-dev --environment dev \
  "python3 -c 'import base64,os; exec(base64.b64decode(\"$B64\"))'"
```

Do NOT run `alembic` against dev Railway from local — see `MEMORY.md` "No remote alembic from local (2026-05-02)". Migrations apply on push to the dev branch.

#### Human-checkpoint pattern

```
🟡 HUMAN ACTION REQUIRED
==========================================================================
PHONE-HOLDER (+19527373312):
You should receive: "Your appointment on [date] at [time] has been
scheduled. Reply Y to confirm, R to reschedule, or C to cancel."

REPLY: Y

After replying, return here and press Enter to continue verification.
==========================================================================
read -p "Press Enter when reply has been sent..."
```

---

## IMPLEMENTATION PLAN

The plan is organized into **5 macro-phases** of work. Within each macro-phase, individual test phases are numbered. The graph at the end of this section shows phase dependencies.

### Macro-Phase A: Foundation (P0 + P1)

Prerequisites for every other phase. Verifies environment, authentication, security headers, session lifecycle, and biometric login.

### Macro-Phase B: Customer Acquisition Pipeline (P2 → P5, including P4a/4b/4c/4d)

The lead-to-sale journey: marketing site form → leads tab → sales pipeline (estimate, e-sign, convert) → **pricelist seed verification (P4a)** → **pricelist editor with all 17 pricing_model variants (P4b)** → **estimate creator wired to pricelist via LineItemPicker (P4c)** → **auto-job-on-approval scenarios (P4d)** → email portal review by customer.

### Macro-Phase C: Operations (P6 → P12)

Customer master record, jobs ready to schedule, schedule calendar, SMS confirmation flow, reschedule queue, technician mobile day-of operations (including Maps "remember choice" persistence), on-site payment collection across the full method matrix (cash/check/Venmo/Zelle/Stripe/refund/multi-tender).

### Macro-Phase D: Revenue & Retention (P13 → P17)

Invoices, Stripe Payment Links reconciliation, service-package onboarding (subscriptions), contract renewals, duplicate-customer management.

### Macro-Phase E: Cross-cutting & Quality (P18 → P24, including P22b + P23b)

AI scheduling, dashboard, communications inbox, security/cross-cutting smoke (including stripe_terminal full-uninstall verification), responsive viewport sweep, **cross-phase happy path integration scenario (P22b)**, unit/integration test sweep, **E2E sign-off report (P23b)**, cleanup.

---

## STEP-BY-STEP TASKS

> Execute every task in dependency order. Each phase is independently testable once its `Prerequisites` are satisfied. The first time the plan is run end-to-end, execute P0 → P24 in order. For change-targeted re-runs, see the **Phase Selection Matrix** at the end.

---

### Phase 0 — Preflight & Environment Setup

**Goal**: Verify dev environment is healthy, tooling installed, allowlists configured, seed records present, and auth token obtained.

**Prerequisites**: None.

**Variant lane**: Operator (no UI tested in this phase).

#### VERIFY (source check) — run before any other step
```bash
# Confirm key env constants in source still match this plan
grep -n "SMS_TEST_PHONE_ALLOWLIST" src/grins_platform/services/sms/base.py
grep -n "EMAIL_TEST_ADDRESS_ALLOWLIST" src/grins_platform/services/email_service.py 2>/dev/null \
  || grep -nr "EMAIL_TEST_ADDRESS_ALLOWLIST" src/grins_platform
agent-browser --version
railway --version
```
If any return empty, halt and reconcile against current source before continuing.

#### Steps

1. **Tooling**: `agent-browser --version`; if missing, `npm install -g agent-browser && agent-browser install --with-deps`.
2. **Railway CLI**: `railway status` → expect `Project: zealous-heart, Environment: dev, Service: Grins-dev`. Re-link if mismatched.
3. **API health**: `curl -s https://grins-dev-dev.up.railway.app/health` → expect `{"status":"healthy",...}`.
4. **Frontend reachable**: `agent-browser open https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/login` → wait networkidle → screenshot `${RUN_DIR}/phase-00-preflight/01-frontend-up.png`.
5. **Required env vars on dev**:
   ```bash
   railway variables --service Grins-dev --environment dev --kv | \
     grep -E '^(SMS_PROVIDER|SMS_TEST_PHONE_ALLOWLIST|EMAIL_TEST_ADDRESS_ALLOWLIST|CALLRAIL_TRACKING_NUMBER|GOOGLE_REVIEW_URL|RESEND_API_KEY|STRIPE_WEBHOOK_SECRET|CALLRAIL_WEBHOOK_SECRET|SIGNWELL_WEBHOOK_SECRET)='
   ```
   Fail if any are missing. If `GOOGLE_REVIEW_URL` is missing, set it (per `00-preflight.md:42`).
6. **Auth token**:
   ```bash
   TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"username":"admin","password":"admin123"}' \
     | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
   export TOKEN
   [[ ${#TOKEN} -gt 100 ]] || exit 1
   ```
7. **Seed customer**: `GET /api/v1/customers?search=Kirill` → expect `id=e7ba9b51-580e-407d-86a4-06fd4e059380`, `phone` ending `7373312`, `sms_opt_in=true`. If missing, create via UI or POST.
8. **Seed admin staff**: confirm staff `0bb0466d-ce5e-477a-9292-7d4b9673a7f6` resolves on `GET /api/v1/staff/{id}`.
9. **Seed tech identity** (CONFIRMED — pre-seeded via `migrations/versions/20250626_100000_seed_demo_data.py` and aligned with deployed dev per commit `2048d28`): three tech users exist with usernames `vasiliy`, `steve`, `gennadiy`, password `tech123`. Resolve their staff IDs via `GET /api/v1/staff?role=tech`. Save the first as `$TECH_ID` (required for Phase 11). The shell harness `e2e/master-plan/_dev_lib.sh` defaults `E2E_TECH_USER=vasiliy` / `E2E_TECH_PASS=tech123`.
10. **Clear stale STOP**: copy `Testing Procedure/scripts/clear_consent.py`, base64-encode, run via `railway ssh`. No-op if nothing to clear.
11. **SMS pipeline probe**:
    ```bash
    TS=$(date +%s)
    curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/sms/send" \
      -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
      -d "{\"customer_id\":\"e7ba9b51-580e-407d-86a4-06fd4e059380\",\"phone\":\"+19527373312\",\"message\":\"Master-plan preflight $TS\",\"message_type\":\"custom\",\"sms_opt_in\":true}"
    ```
    Expect `{"success":true,...}`. 🟡 **HUMAN**: confirm receipt on `+19527373312`.
12. **CallRail webhook reachable**: registered URL is `$API_BASE/api/v1/webhooks/callrail/inbound` (path verified at `callrail_webhooks.py:211`, mounted with prefix `/webhooks/callrail`). Test with: `curl -sI -X POST $API_BASE/api/v1/webhooks/callrail/inbound` → expect 401/403 (HMAC failure on empty body) or 422 (validation), NOT 404. If 404, the route is wrong or service is down.

#### Acceptance
- [ ] All env vars present.
- [ ] `$TOKEN` exported and ≥100 chars.
- [ ] Seed customer + admin + tech all resolve.
- [ ] Probe SMS delivered to phone.

#### Cleanup
None — this phase is preparatory.

#### Re-run criteria
**Always run first.** Cheap (~30s); never skip.

#### Stale-reference watchlist
- Older docs may reference `Grins-dev-dev` as a hostname segment but the API URL is `grins-dev-dev.up.railway.app`. Verify by `curl /health`.
- `Testing Procedure/00-preflight.md` reference to `EMAIL_TEST_ADDRESS_ALLOWLIST` may live in `email_service.py` or `services/email/*` — grep before assuming.

---

### Phase 1 — Authentication & Security

**Goal**: Verify login (password + biometric), logout, session lifetime, role-based access, security headers, rate limiting, request-id echoing.

**Prerequisites**: P0.

**Variant lane**: Admin desktop + WebAuthn-capable browser (admin-browser sets up Chromium which supports WebAuthn virtual authenticators via DevTools Protocol).

#### VERIFY (source check)
```bash
grep -n "username-input\|password-input\|login-btn" frontend/src/features/auth/components/LoginPage.tsx
grep -n "@router\." src/grins_platform/api/v1/auth.py | head -20
grep -n "WebAuthn\|webauthn" src/grins_platform/api/v1/webauthn.py | head -10
grep -n "rate_limit\|slowapi" src/grins_platform/middleware/rate_limit.py
grep -n "X-Frame-Options\|Content-Security-Policy\|Strict-Transport-Security" src/grins_platform/middleware/security_headers.py
```

#### Steps

1. **Login happy path** (admin desktop):
   - `agent-browser open $BASE/login` → screenshot `01-login-loaded.png`.
   - Fill `[data-testid='username-input']` = `admin`, `[data-testid='password-input']` = `admin123`.
   - Click `[data-testid='login-btn']` → wait networkidle.
   - Verify URL = `$BASE/dashboard` (admin lands on /dashboard via `PostLoginRedirect`).
   - Screenshot `02-dashboard-after-login.png`.
2. **Bad password**: open incognito session (`--session bad-pass`), submit wrong password → expect inline error (`agent-browser get text "[data-testid='login-error']"` or whatever the actual selector is — grep `LoginPage.tsx` first). Screenshot `03-login-error.png`.
3. **Account lockout**: submit bad password 5+ times → verify the lockout response (check `src/grins_platform/services/auth_service.py` for the threshold). Screenshot.
4. **Session lifetime**: after successful login, `eval` to read auth state, wait 5 seconds, navigate to a protected route, verify still logged in. (Full 60-min token expiry test belongs in unit tests, not E2E.)
5. **Refresh token**: trigger a 401 (manually clear access cookie), verify silent refresh via `/auth/refresh` happens and user stays on page.
   1. **Stale-header regression** (per `bughunt/session_timeout.md`): after a successful interceptor refresh, confirm the retry uses the *new* access token and not the cached `apiClient.defaults.headers.common['Authorization']`. VERIFY: `grep -n "token-refreshed" frontend/src/core/api/client.ts` should return line `:66`. Steps: (a) login; (b) `agent-browser eval "document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';"` to clear the access cookie; (c) trigger any state-changing request via UI; (d) listen for the custom event with `agent-browser eval "let n=0; window.addEventListener('token-refreshed', () => { window._tokenRefreshed = ++n; }); 'armed'"`; (e) read it back; (f) assert URL is NOT `/login?reason=session_expired` (no redirect loop); (g) assert exactly one `token-refreshed` event observed; (h) confirm a follow-up request 200s without re-refreshing.
6. **Logout**: click `[data-testid='user-menu']` → `[data-testid='logout-btn']` → verify redirect to `/login`. Screenshot `04-logged-out.png`.
7. **Role enforcement**:
   - Login as tech: username `vasiliy` (or `steve` / `gennadiy`), password `tech123`. Confirmed seeded via `migrations/versions/20250626_100000_seed_demo_data.py`.
   - Verify tech is redirected to `/tech` not `/dashboard`.
   - Try to navigate to `/customers` → expect redirect or 403.
8. **Biometric passkey** (WebAuthn):
   - Login as admin via password.
   - Navigate to `/settings` → security tab → screenshot `05-passkey-empty.png`.
   - **Use Chromium's WebAuthn virtual authenticator** via DevTools Protocol: `agent-browser eval "..."` to register a virtual authenticator, then click `[data-testid='add-passkey-btn']`.
   - Complete WebAuthn challenge, screenshot success.
   - Logout, return to `/login`, click "Sign in with biometrics", verify it works against the virtual authenticator.
   - **Gotcha**: `WEBAUTHN_RP_ID` on dev must match the bare effective domain of the dev Vercel URL. If it's set to `localhost`, biometric login from the dev Vercel domain will fail. Verify via `railway variables`.
9. **Security headers**: `curl -sI $API_BASE/health | grep -E 'Strict-Transport|X-Frame-Options|Content-Security-Policy|X-Content-Type-Options|Referrer-Policy'` → expect all present.
10. **Rate limiting**: hit `/api/v1/auth/login` 20× rapidly with wrong creds → expect 429 after the configured threshold.
11. **CORS preflight**: `curl -sI -X OPTIONS $API_BASE/api/v1/customers -H "Origin: https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app" -H "Access-Control-Request-Method: GET"` → verify `Access-Control-Allow-Origin` echoes the dev origin.
12. **Request-ID echo**: `curl -sI $API_BASE/health` → confirm `X-Request-ID` header present (per `app.py:_attach_request_id`).
13. **5xx CORS** (regression — bughunt 2026-04-28 §Bug 4): send a request that triggers a 500 from a route, confirm CORS headers still present on the 500 response.

#### Acceptance
- [ ] All login/logout flows pass.
- [ ] Lockout threshold matches source.
- [ ] Role enforcement: tech → /tech; admin → /dashboard.
- [ ] Biometric register + login round-trip succeeds.
- [ ] Security headers, rate limit, CORS, request-id all verified.
- [ ] Stale-Authorization-header refresh regression: no redirect to `/login?reason=session_expired`; exactly one `token-refreshed` event; subsequent request succeeds without re-refreshing.

#### Cleanup
- Delete the registered virtual passkey via `DELETE /api/v1/auth/webauthn/credentials/{id}` to keep auth state clean.

#### Re-run criteria
- Standalone-runnable. ~10 minutes including biometric setup.

#### Stale-reference watchlist
- `scripts/e2e/test-session-persistence.sh` may use deprecated cookie names. Verify against `LoginPage.tsx` and `core/api/client.ts`.
- WebAuthn virtual authenticator behavior changes between Chromium versions — keep `agent-browser install --with-deps` fresh.

---

### Phase 2 — Marketing Site → Lead Intake

**Goal**: Public lead-capture form on the marketing Vercel site creates a `lead` row that surfaces in the admin Leads tab.

**Prerequisites**: P0.

**Variant lane**: Public (no auth) → admin desktop verification.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/marketing.py
grep -n "@router\." src/grins_platform/api/v1/leads.py | head -10
grep -nr "form_submission\|lead_form\|public.*lead" frontend/src/features/marketing 2>/dev/null
ls frontend/src/pages/Marketing.tsx 2>/dev/null
```

#### Steps

1. Open marketing site: `agent-browser --session marketing open https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app`.
2. Navigate to the lead form (per `Testing Procedure/01-path-a-lead-intake.md` for canonical scenarios).
3. **Scenario A1** (Spring Startup, valid E.164 US phone, `+19527373312`, valid email):
   - Fill all fields. Screenshot `01-form-filled.png`.
   - Submit. Wait for success state. Screenshot `02-success.png`.
   - Capture `X-Request-ID` header from the response (browser devtools or marketing site console).
4. **Scenario A2** (Winterization service detection): submit with `service_type` matching winterization and a date in October — expect `requires_estimate=false` mapping (the system should classify it as ready_to_schedule).
5. **Scenario A3** (Messy phone): `952-737-3312` (with dashes) → expect normalization to `+19527373312`.
6. **Verify lead created** (admin desktop): `curl $API_BASE/api/v1/leads?search=...&page=1&page_size=5 -H "Authorization: Bearer $TOKEN"` → expect the new lead, status=`new`, `created_at` recent.
7. **UI verification**: `agent-browser open $BASE/leads` → wait → snapshot → confirm lead row visible. Screenshot `03-leads-tab.png`.
8. **Spam / dedup**: re-submit identical payload twice within 2 minutes → expect dedup logic per `bughunt/2026-04-14-lead-form-sms-consent-rollback.md`. Confirm via API count.
9. **SMS opt-in propagation**: if the form has an opt-in checkbox, verify checked → opt-in `true` on the lead; unchecked → `false` (per Path L 5-scenario consent matrix in `Testing Procedure/10-customer-landing-flow.md`).
10. **Empty last-name handling**: per `.agents/plans/webhook-empty-last-name-fix.md` — submit with empty last name and expect graceful handling, not a 500.
11. **Zero-zone validation regression** (per `bughunt/2026-03-26-e2e-battle-test.md` lines 62–74). VERIFY: `grep -n "zone_count" src/grins_platform/schemas/lead.py src/grins_platform/api/v1/checkout.py`. Steps: (a) on the public lead form, override the `<input min='1'>` HTML attribute via `agent-browser eval "document.querySelector('[name=zone_count]').value='0'; document.querySelector('[name=zone_count]').dispatchEvent(new Event('change',{bubbles:true}))"`; (b) submit; (c) assert client refuses OR server returns 422 — assert NO Stripe checkout session is created (`api_q "/api/v1/checkout/sessions?lead_phone=$PHONE" '.items|length'` → 0).
12. **Terms checkbox regression** (per `bughunt/2026-03-26-e2e-battle-test.md` lines 123–133). VERIFY: `grep -n "terms_accepted" src/grins_platform/schemas/lead.py` should return line 120 (and `:276`, `:426`). Steps: (a) submit form with terms checkbox unchecked → assert form rejects (HTML5 required or 422 from server); (b) submit with checkbox checked → query the persisted lead and assert `terms_accepted=true` via `api_q "/api/v1/leads/$LEAD_ID" '.terms_accepted'`.
13. **Surcharge marketing-vs-checkout drift** (per `bughunt/2026-03-26-e2e-battle-test.md` lines 25–51). VERIFY: `grep -n "surcharge\|per_zone\|residential" src/grins_platform/services/surcharge_calculator.py src/grins_platform/api/v1/checkout.py`. The marketing site lives at a separate Vercel deployment (`MARKETING_BASE` in `_dev_lib.sh:33`), so testid-based selection is not guaranteed; before the run, `agent-browser snapshot $MARKETING_BASE` and grep the snapshot for the price text in residential and commercial cards. Steps: for each zone count 4 / 8 / 12, (a) navigate to the marketing pricing card, scrape the displayed price from the rendered DOM (substring match `"$X.XX/zone"` per the card's text), (b) compare to the price returned by the checkout pricing endpoint — re-grep `api/v1/checkout.py` for the actual route name and shape (likely `POST /api/v1/checkout/sessions` or `GET /api/v1/checkout/quote`); use whatever exists. Assert the per-zone rate matches to the cent. If only `POST /sessions` exists, create a session for that zone count and read the line-item amount.

#### Acceptance
- [ ] Lead row created with normalized E.164 phone.
- [ ] Source field captures origin (marketing site).
- [ ] requires_estimate flag set per `update2_instructions.md` mapping (New System, Upgrade, Exploring → true; Repair, Winterization, Seasonal Maintenance → false).
- [ ] Dedup blocks identical resubmits.
- [ ] X-Request-ID echoed back.
- [ ] Zero-zone keyboard bypass blocked; no Stripe checkout session created.
- [ ] Terms checkbox unchecked rejects submission; checked persists `terms_accepted=true`.
- [ ] Marketing card price matches checkout quote for every zone count tested.

#### Cleanup
- Either let the lead carry into Phase 3, or `DELETE /api/v1/leads/{id}` for each created lead in the cleanup phase.

#### Re-run criteria
- Standalone-runnable; produces fresh leads each time.

#### Stale-reference watchlist
- `feature-developments/required-service-week-preferences/plan.md` may reference older form field names. Cross-reference current source.

---

### Phase 3 — Leads Tab — Routing & Dedup

**Goal**: From the admin Leads tab, mark a lead contacted, route it to Jobs (with `requires_estimate` modal handling) or Sales, observe lead disappearance, verify auto-created customer.

**Prerequisites**: P0, P2 (need a fresh lead).

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "Mark Contacted\|mark-contacted\|markContacted" frontend/src/features/leads
grep -n "Move to Jobs\|move-to-jobs\|moveToJobs" frontend/src/features/leads
grep -n "Move to Sales\|move-to-sales\|moveToSales" frontend/src/features/leads
grep -n "@router.post" src/grins_platform/api/v1/leads.py
```

#### Steps

1. Login admin → navigate `/leads`. Snapshot. Screenshot `01-leads-tab.png`.
2. **Mark Contacted**: click a New lead row's `Mark Contacted` button → verify status flips to `Contacted`, `last_contacted_at` updated. Screenshot `02-contacted.png`.
3. **Move to Sales** (estimate path): click `[data-testid='move-to-sales-${id}']` on a lead row (or `[data-testid='lead-detail-move-to-sales-btn']` if working from detail view). Endpoint: `POST /api/v1/leads/{id}/move-to-sales` (leads.py:609). For a lead whose `requires_estimate` mapping is `true` (job_situation = New System / Upgrade / Exploring) → expect lead disappears from leads list, customer auto-created, sales pipeline entry created at `Schedule Estimate` status. Verify `GET /api/v1/sales` (or `/sales/pipeline` if listing pipeline entries — confirm against current `sales_pipeline.py`) shows the new entry. Screenshot `03-moved-to-sales.png`.
4. **Move to Jobs (with requires-estimate warning modal)**: pick another lead with `requires_estimate=true`, click `[data-testid='move-to-jobs-${id}']` (endpoint: `POST /api/v1/leads/{id}/move-to-jobs`, leads.py:577) → expect modal with three options. Test all three:
   - **Move to Jobs anyway** (override) → audit-logged, job created at `to_be_scheduled`. Capture via `GET /api/v1/audit-log?...` (singular path).
   - **Move to Sales** (redirect) → behaves like step 3.
   - **Cancel** → modal closes, no state change.
5. **Move to Jobs (no warning)**: a lead with `job_situation=Repair` → no warning modal, direct conversion.
6. **Mark Contacted**: separate verb — `PUT /api/v1/leads/{id}/contacted` (leads.py:639), NOT POST. UI selector: `[data-testid='mark-contacted-${id}']` (row) or `[data-testid='lead-detail-mark-contacted-btn']` (detail).
7. **Duplicate conflict modal** (legacy `POST /api/v1/leads/{id}/convert` at leads.py:485 — DEPRECATED in source): create two leads with identical phone, attempt to convert second → expect 409 + "Use existing customer" / "Convert anyway" modal. Per `update2_instructions.md:574`, the new `move-to-{jobs,sales}` paths silently link instead of showing modal — verify both behaviors.
8. **Lead notes propagation**: lead created with notes → after routing, verify customer `internal_notes` contains the appended notes.
9. **Property auto-creation**: if lead had address, verify property created on the new customer via `GET /api/v1/customers/{id}/properties`.
10. **Tag auto-clearing**: verify `Needs Contact` tag clears on Mark Contacted.
11. **Status filter**: switch leads list filter to `Converted` → verify converted leads visible there.
12. **Delete**: create a throwaway lead, click `[data-testid='delete-lead-${id}']` (or `[data-testid='lead-detail-delete-btn']`), confirm modal, verify hard-delete via API.

#### Acceptance
- [ ] All three routing paths verified (Move-to-Jobs no-warning, Move-to-Jobs override, Move-to-Sales).
- [ ] requires_estimate modal renders for the right situations.
- [ ] Customer + property + sales/job records created correctly.
- [ ] Audit log captured for "Move to Jobs anyway" override.

#### Cleanup
- Carry the routed records into P4 (Sales) and P7 (Jobs). The deleted-lead test record needs no follow-up.

#### Re-run criteria
- Requires a fresh lead each time. Run after P2 in a chain, or independently after manually creating a lead via API.

#### Stale-reference watchlist
- The "Convert Lead" single-button legacy path may be deprecated; verify whether the conflict modal still appears or whether the two new paths (Move-to-Jobs, Move-to-Sales) silently link as `update2_instructions.md` claims.

---

### Phase 4 — Sales Pipeline — Estimates & E-Signature (Admin)

**Goal**: Walk the sales pipeline from `Schedule Estimate` → `Estimate Scheduled` → `Send Estimate` → `Pending Approval` → `Send Contract` → `Closed-Won`, with both **remote-email** and **embedded-iframe** signing variants.

**Prerequisites**: P0, P3 (Sales pipeline entry at `Schedule Estimate`).

**Variant lane**: Admin desktop (most steps); customer-side signing tested in P5.

#### VERIFY (source check)
```bash
grep -n "@router.(post|get)" src/grins_platform/api/v1/sales.py
grep -n "@router.(post|get)" src/grins_platform/api/v1/sales_pipeline.py
grep -n "Schedule Estimate\|Estimate Scheduled\|Send Estimate\|Pending Approval\|Send Contract\|Closed-Won" frontend/src/features/sales
grep -n "SignWell\|signwell" src/grins_platform/services/signwell
ls frontend/src/pages/Sales.tsx
```

#### Steps

1. Login admin → `/sales`. Screenshot `01-sales-list.png`.
2. **Estimate Calendar — schedule a visit**: switch to Estimate Calendar tab → create event for the seeded entry → verify entry auto-advances to `Estimate Scheduled` (per `update2_instructions.md:660`). Screenshot.
3. Open sales detail: click into the entry → screenshot `02-sales-detail.png`.
4. **Document upload**: upload a sample PDF estimate via Documents section. Verify presigned-URL pattern. Screenshot `03-doc-uploaded.png`.
5. **Send Estimate (Email)**:
   - Click `Send Estimate for Signature (Email)`.
   - Verify SignWell document creation (check `GET /api/v1/sales/{id}` or relevant endpoint for `signwell_document_id`).
   - Expect customer email sent via Resend (verify `GET /api/v1/sent-messages?customer_id=...` shows the email outbound).
   - 🟡 **HUMAN** (optional): check `kirillrakitinsecond@gmail.com` for the SignWell email. Screenshot the email if found.
   - Click `Mark Sent` → status advances to `Pending Approval`. Screenshot.
6. **Send Estimate (On-Site Embedded)** — separate sales entry to avoid state collision:
   - Click `Sign On-Site (Embedded)` → expect iframe loads.
   - Screenshot `04-onsite-iframe.png`.
   - Sign inside the iframe (use SignWell test mode if available).
   - Verify webhook fires → entry advances to `Pending Approval` → `Send Contract` automatically. Verify via API status check.
7. **Auto-advance from Pending Approval to Send Contract** (remote-email path):
   - In SignWell test mode, simulate the customer signing.
   - Verify `signwell_webhooks` route receives the signed event (check `audit_log` or service logs for `signing_completed`).
   - Verify entry status flips to `Send Contract`. Screenshot `05-send-contract.png`.
8. **Convert to Job**:
   - Click `Convert to Job` (gated on signature) → expect new Job created at `to_be_scheduled` and pipeline entry moves to `Closed-Won`. Verify via `GET /api/v1/jobs?customer_id=...`. Screenshot `06-closed-won.png`.
9. **Force Convert to Job** (override path):
   - On a separate entry without a signature, click `Force Convert to Job` → expect confirmation modal → confirm → verify audit flag set on the record.
10. **Mark Lost**: on a separate entry, click `Mark Lost` → expect `Closed-Lost` terminal state.
11. **Pipeline status manual override**: pick an entry, change status via dropdown → verify allowed transitions; confirm `InvalidSalesTransitionError` (HTTP 422) for disallowed transitions.
12. **No-document signing block**: try `Send Estimate for Signature` without uploading a document → expect button disabled or 400.
13. **Pre-estimate gate** (per `MEMORY.md` "Estimate email portal wired via Resend (2026-04-26)" / `.agents/plans/estimate-approval-email-portal.md` Q-B correction): the obsolete `MissingSigningDocumentError` gate should NOT fire pre-estimate. Verify this by sending an estimate without any pre-existing signed contract on file — should succeed.
14. **ScheduleVisit conflict detection** (per `.agents/plans/schedule-estimate-visit-handoff.md`). VERIFY: `grep -n "schedule-visit-conflict-banner" frontend/src/features/sales/components/ScheduleVisitModal/PickSummary.tsx` resolves at `:54`; `grep -n "schedule-visit-confirm-btn" frontend/src/features/sales/components/ScheduleVisitModal/ScheduleVisitModal.tsx` resolves at `:203`. Steps: with one estimate slot already on the calendar at e.g. Tue 10:00–11:00, open the ScheduleVisit modal (`[data-testid='schedule-visit-modal']`) and pick the same slot via `[data-testid='schedule-visit-slot-${di}-${s}']` (per `WeekCalendar.tsx:266`); assert conflict banner renders (`agent-browser get text "[data-testid='schedule-visit-conflict-banner']"` returns non-empty); assert the confirm CTA is disabled (`agent-browser eval "document.querySelector('[data-testid=schedule-visit-confirm-btn]').disabled"` → true); pick a non-overlapping slot and assert the banner clears + confirm re-enables. Screenshot `07-conflict-banner.png` and `08-conflict-cleared.png`.
15. **Drag-boundary feedback** (per same plan). Drag an estimate event past midnight (start of next day) or past Sunday (end of week); assert the drag is rejected (event snaps back) OR a boundary toast appears. Capture a `before-drag.png` and `after-rejected-drag.png`.

#### Acceptance
- [ ] Both email and on-site signing flows complete.
- [ ] Auto-advance from Pending Approval → Send Contract via SignWell webhook.
- [ ] Force Convert to Job logs the override.
- [ ] Mark Lost works at any stage.
- [ ] Pipeline status state machine enforced.
- [ ] Conflict banner appears for overlapping ScheduleVisit slots; clears when slot moves.
- [ ] Drag past day/week boundary is rejected with feedback.

#### Cleanup
- Carry the new Job into P7. Delete force-converted test entries via API in cleanup.

#### Re-run criteria
- Requires sales entry from P3. Standalone-runnable if a sales entry is created via API first.

#### Stale-reference watchlist
- Older bughunt docs reference `MissingSigningDocumentError` pre-estimate gate — that's removed per the Q-B correction. Verify it's actually gone in `services/sales_pipeline_service.py`.
- Some plans still mention "Send Contract" as a separate stage; per `update2_instructions.md:610` the action button at `Send Contract` is labeled "Convert to Job" in the UI.

---

### Phase 4a — Pricelist Seed Verification (Umbrella Task 6.2 — DB-only)

**Goal**: After umbrella plan Phase 1 landed, verify the seeded `service_offerings` table is intact and matches the canonical Viktor JSON distribution. Foundation for Phases 4b, 4c.

**Prerequisites**: P0. The umbrella seed migration must have run.

**Variant lane**: Operator (DB-only).

#### VERIFY (source check)
```bash
ls src/grins_platform/migrations/versions/ | grep -i "pricelist\|service_offering" | head
grep -n "VIKTOR_PRICELIST_CONFIRMED" src/grins_platform/migrations/versions/*pricelist*.py
ls bughunt/2026-05-01-pricelist-seed-data.json   # canonical distribution snapshot
```

#### Steps (DB queries — REST not available for raw counts, use `railway_python` on dev)

```bash
# 1. Total seed count
api_q "/api/v1/services?limit=200&active_only=false" '[.items[] | select(.slug != null)] | length'
# Expected: 73

# 2. Per-customer-type distribution (residential|37 + commercial|36)
api_q "/api/v1/services?limit=200&active_only=false" \
  '[.items[] | select(.slug != null) | .customer_type] | group_by(.) | map({key: .[0], count: length})'

# 3. Every pricing_model variant present, counts match seed JSON
api_q "/api/v1/services?limit=200&active_only=false" \
  '[.items[] | select(.slug != null) | .pricing_model] | group_by(.) | map({key: .[0], count: length})'
# Expected (per Counter from bughunt/2026-05-01-pricelist-seed-data.json):
#   per_unit_flat_plus_materials: 12, per_unit_flat: 8, per_unit_range: 8,
#   tiered_zone_step: 6, flat_plus_materials: 6, flat: 5, variants: 4,
#   conditional_fee: 4, per_zone_range: 3, flat_range: 3, tiered_linear: 2,
#   compound_repair: 2, hourly: 2, size_tier_plus_materials: 2, yard_tier: 2,
#   size_tier: 2, compound_per_unit: 2  (= 17 distinct variants, total 73)

# 4. Slug uniqueness (partial unique index)
api_q "/api/v1/services?limit=200&active_only=false" \
  '[.items[] | select(.slug != null) | .slug] | (length - (unique | length))'
# Expected: 0 (no duplicates)

# 5. Pre-seed rows untouched (slug NULL preserved)
api_q "/api/v1/services?limit=200&active_only=false" \
  '[.items[] | select(.slug == null)] | length'
# Expected: stable count (compare against pre-migration baseline)

# 6. pricing_rule JSONB roundtrip — sample
api_q "/api/v1/services?slug=irrigation_install_residential" \
  '.items[0].pricing_rule | keys'
# Expected: contains price_per_zone_min, price_per_zone_max, unit, profile_factor

# 7. Gating env-var enforcement (ONLY safe to run on local — dev migrations are managed)
[[ "$ENVIRONMENT" == "local" ]] && {
  unset VIKTOR_PRICELIST_CONFIRMED
  uv run alembic downgrade -1 2>&1 | tee /tmp/dg.log
  uv run alembic upgrade head 2>&1 | tee /tmp/up.log
  grep -q "VIKTOR_PRICELIST_CONFIRMED" /tmp/up.log || exit 1   # migration aborts when env var unset
}
```

#### Acceptance
- [ ] All 7 queries return expected.
- [ ] 17 pricing_model variants present.
- [ ] Slug uniqueness across all seeded rows.
- [ ] Gating env-var blocks migration when unset (local only).

#### Cleanup
None — read-only.

#### Re-run criteria
Re-run after any seed migration or `service_offerings` schema change.

#### Stale-reference watchlist
- `bughunt/2026-05-01-pricelist-seed-data.json` is the snapshot — if the actual seed drifts, that JSON drifts too. Reconcile.

---

### Phase 4b — Pricelist Editor UI (Umbrella Task 6.3 — all 17 pricing_model variants)

**Goal**: Verify the admin pricelist editor at `/invoices?tab=pricelist`: filters, search, sort, pagination, every drawer-form variant, deactivate/show-inactive toggle, archive history, pricelist.md export.

**Prerequisites**: P0, P4a.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
ls frontend/src/features/pricelist/ 2>/dev/null
grep -n "data-testid='price-list-editor'" frontend/src/features/pricelist/components/PriceListEditor.tsx
grep -n "data-testid='price-list-row-\${" frontend/src/features/pricelist/components/PriceListEditor.tsx
grep -n "data-testid='price-list-edit-\${" frontend/src/features/pricelist/components/PriceListEditor.tsx
grep -n "service-offering-drawer\|ServiceOfferingDrawer" frontend/src/features/pricelist/components/ServiceOfferingDrawer.tsx
grep -n "offering-display-name-input\|offering-save" frontend/src/features/pricelist/components/ServiceOfferingDrawer.tsx
ls frontend/src/features/pricelist/components/ArchiveHistorySheet.tsx 2>/dev/null
grep -n "@router\." src/grins_platform/api/v1/services.py | head
```

Verified selectors: `[data-testid='price-list-editor']` (PriceListEditor.tsx:142), `[data-testid='price-list-row-{id}']` (line 258), `[data-testid='price-list-edit-{id}']` (line 306), `[data-testid='offering-display-name-input']` (ServiceOfferingDrawer.tsx:260), `[data-testid='offering-save']` (line 456).

#### Steps

| # | Action | Screenshot |
|---|---|---|
| 1 | Login admin → navigate `/invoices` → click "Pricelist" tab | `01-tab-pricelist.png` |
| 2 | Click "Pricebook" shortcut in top-nav (Layout.tsx) → lands at same view | `02-topnav-shortcut.png` |
| 3 | Filter customer_type=residential | `03-filter-residential.png` |
| 4 | Filter customer_type=commercial | `04-filter-commercial.png` |
| 5 | Filter customer_type=both (default) | `05-filter-both.png` |
| 6 | Filter category=installation | `06-filter-installation.png` |
| 7 | Filter category=landscaping | `07-filter-landscaping.png` |
| 8 | Search "spring" → 1+ matches | `08-search-spring.png` |
| 9 | Search "zzznomatch" → empty state | `09-empty-state.png` |
| 10 | Pagination → page 2 → page 3 | `10-page-2.png`, `11-page-3.png` |
| 11 | Sort by name desc | `12-sort-desc.png` |
| 12–28 | Click "+ New offering" → for each of 17 pricing_model variants, screenshot drawer form | `12-drawer-flat.png`, `13-drawer-flat_range.png`, `14-drawer-per_unit_flat.png`, `15-drawer-per_unit_range.png`, `16-drawer-per_unit_flat_plus_materials.png`, `17-drawer-flat_plus_materials.png`, `18-drawer-per_zone_range.png`, `19-drawer-tiered_zone_step.png`, `20-drawer-tiered_linear.png`, `21-drawer-hourly.png`, `22-drawer-variants.png`, `23-drawer-conditional_fee.png`, `24-drawer-compound_repair.png`, `25-drawer-compound_per_unit.png`, `26-drawer-size_tier.png`, `27-drawer-size_tier_plus_materials.png`, `28-drawer-yard_tier.png` |
| 29 | Fill flat form → save → verify new row in DB via `GET /api/v1/services?slug=<test_slug>` | `29-create-flat-success.png` |
| 30 | Edit existing row's `display_name` → save | `30-edit-display-name.png` |
| 31 | Edit `pricing_rule.range_anchors` JSON for a `per_zone_range` row | `31-edit-range-anchors.png` |
| 32 | Deactivate row → disappears from default view → toggle "Show inactive" → reappears | `32-deactivate.png`, `33-show-inactive.png` |
| 33 | Open `ArchiveHistorySheet` (Phase 2 placeholder per umbrella) | `34-archive-history-placeholder.png` |
| 34 | Trigger `pricelist.md` auto-export endpoint (per `PriceListExportService`) | `35-export-pricelist-md.png` |
| 35 | After every save: `agent-browser console` + `agent-browser errors` empty | `36-console-clean.png` |

#### Verification queries
```bash
# After step 29
api_q "/api/v1/services?slug=$TEST_SLUG" '.items[0] | {slug, customer_type, pricing_model}'

# After step 30
api_q "/api/v1/services?slug=$TEST_SLUG" '.items[0].display_name'

# After step 32
api_q "/api/v1/services?slug=$TEST_SLUG&active_only=false" '.items[0].is_active'
# Expected: false
```

#### Acceptance
- [ ] 36 screenshots present.
- [ ] Every 17 drawer variants rendered (one screenshot each).
- [ ] All 4 verification queries pass.
- [ ] Zero console errors after every save.

#### Cleanup
- Reactivate or delete any test offerings. The 73 seed rows must remain intact.

#### Re-run criteria
Re-run after any pricelist editor or `service_offerings` schema change.

---

### Phase 4c — Estimate Creator wired to Pricelist (Umbrella Task 6.4 — LineItemPicker)

**Goal**: Verify the LineItemPicker on the estimate creation flow: 5 customer-type-resolution paths × 6 pricing_model branches × custom-quote prompt for above-tier-max × hidden `unit_cost` in staff-only drawer.

**Prerequisites**: P0, P4a, P4b. A test sales-pipeline entry at `Send Estimate` stage (or create one inline).

**Variant lane**: Admin desktop (estimate creator). Customer-portal preview check uses public lane.

#### VERIFY (source check)
```bash
grep -n "data-testid='line-item-picker-search'" frontend/src/features/schedule/components/EstimateSheet/LineItemPicker.tsx
grep -n "data-testid='line-item-picker-add'\|line-item-picker-back\|line-item-picker-quantity\|line-item-picker-anchors\|line-item-picker-results" frontend/src/features/schedule/components/EstimateSheet/LineItemPicker.tsx
ls frontend/src/features/schedule/components/EstimateSheet/{SizeTierSubPicker,VariantSubPicker,YardTierSubPicker}.tsx 2>/dev/null
grep -n "scope_items\|unit_cost\|material_markup_pct" src/grins_platform/models/job.py
```

⚠️ Confirmed: the umbrella plan claimed selectors `line-item-picker-result-*` (singular suffix). The actual collection wrapper is `[data-testid='line-item-picker-results']` (plural, no per-row id suffix on results). Adapt selectors accordingly when picking — use the search input + first child of `line-item-picker-results`, or click via `eval` like in `e2e/integration-full-happy-path.sh:55-57`.

#### Test matrix

| # | Setup | Action | Expected | Screenshot |
|---|---|---|---|---|
| 1 | Lead-only estimate, Lead.customer_type=residential | Open LineItemPicker | Pre-filtered to residential | `01-lead-residential-prefiltered.png` |
| 2 | Lead-only estimate, Lead.customer_type=commercial | Open LineItemPicker | Pre-filtered to commercial | `02-lead-commercial-prefiltered.png` |
| 3 | Customer estimate + Property.property_type=residential | Open LineItemPicker | Pre-filtered to residential | `03-property-residential-prefiltered.png` |
| 4 | Customer estimate + Property.property_type=commercial | Open LineItemPicker | Pre-filtered to commercial | `04-property-commercial-prefiltered.png` |
| 5 | Customer estimate, no property | Open LineItemPicker | Defaults to residential + prominent toggle | `05-default-residential-toggle.png` |
| 6 | Any context | Toggle "Show all customer types" override ON | Both visible | `06-override-toggle.png` |
| 7 | Open picker | Type "spring" → debounced search returns matches | `07-debounced-search.png` |
| 8 | Pick a `flat` model offering | Line added with default amount | `08-pick-flat.png` |
| 9 | Pick a `per_zone_range` offering | range_anchors quick-pick chips render; range hint visible | `09-pick-per-zone-range.png`, `10-range-anchors-chips.png` |
| 10 | Pick a `size_tier` offering | SizeTierSubPicker opens → S/M/L select → line added (Bug #12 regression check — must NOT be silently empty) | `11-size-tier-subpicker.png`, `12-size-tier-selected.png` |
| 11 | Pick a `size_tier_plus_materials` offering | Same flow + includes_materials hint | `13-size-tier-plus-materials.png` |
| 12 | Pick a `yard_tier` offering | YardTierSubPicker opens → 0-3yd / 4-6yd | `14-yard-tier.png` |
| 13 | Pick a `variants` offering | VariantSubPicker opens → variant select | `15-variant-subpicker.png` |
| 14 | Pick a `tiered_zone_step` offering, enter quantity ABOVE max_zones_specified | "Custom Quote" prompt fires → switches line to free-form `custom` | `16-above-max-prompt.png`, `17-custom-line-added.png` |
| 15 | Edit line → expand drawer | Hidden `unit_cost` field visible; margin readout shown | `18-staff-drawer-unit-cost.png` |
| 16 | Submit estimate → open customer portal preview | `unit_cost` redacted from customer view | `19-customer-view-no-unit-cost.png` |
| 17 | Click "Use a template" instead of pricelist | Existing template flow still works (E7 backward compat) | `20-template-flow-coexists.png` |

#### Verification

```bash
# After test 17 — service_offering_id and unit_cost present on line items
api_q "/api/v1/estimates/$EST_ID" '.line_items[0] | {service_offering_id, unit_cost}'

# Bug #12 regression — size_tier picker must populate
# After test 10, the resulting line item must NOT be empty:
api_q "/api/v1/estimates/$EST_ID" '.line_items | map(select(.tier_size != null)) | length'
# Expected: 1
```

#### Acceptance
- [ ] 20 screenshots, 5 customer-type-resolution paths exercised, 6 pricing_model branches exercised, above-max prompt fires, hidden cost field verified.
- [ ] Bug #12 regression: size_tier picker NOT silently empty (see `SizeTierSubPicker.tsx:40-41` reads `obj.price ?? obj.labor_amount`).
- [ ] `unit_cost` redacted from customer-portal view.
- [ ] Existing template flow coexists.

#### Cleanup
- Delete or reset test estimates.

#### Re-run criteria
Re-run after any LineItemPicker, SubPicker, or estimate-line-item schema change.

---

### Phase 4d — Auto-Job-on-Approval (Umbrella Task 6.1 — 10 scenarios)

**Goal**: Verify the auto-job-creation flow when a customer approves an estimate via the email portal: parent job ATTACH vs new-job, lead-only skip, N5 toggle, signed-PDF email, "Schedule follow-up" CTA, polling-fallback when modal already open.

**Prerequisites**: P0, P4 (estimate sent), P4a (pricelist intact). The N5 (`auto_job_on_approval`) business setting controls the behavior. Bug #13 (CLOSED in `f0a1e18`) — `EstimateReview` no longer crashes on missing `business.company_logo_url`.

**Variant lane**: Customer (portal approves) → Admin (verify auto-job) → Email (signed PDF arrival).

#### VERIFY (source check)
```bash
grep -n "auto_job_on_approval\|auto_job_created\|auto_job_skipped" src/grins_platform/services/estimate_service.py
grep -n "scope_items" src/grins_platform/models/job.py
grep -n "EstimatePDFService\|signed.*pdf" src/grins_platform/services
grep -n "ApprovedConfirmationCard\|Schedule follow-up\|schedule-followup-cta" frontend/src
grep -n "auto_job_on_approval\|BUSINESS_SETTING_KEYS" src/grins_platform/services/settings_service.py
```

#### Test matrix (10 scenarios per umbrella Task 6.1)

| # | Setup | Action | Expected | Screenshots |
|---|---|---|---|---|
| 0.1 | Customer estimate, N5=ON, no parent job | Customer approves via portal | New Job in `to_be_scheduled`; `estimate.job_id` set; line items copied to `Job.scope_items` | `01-portal-approve.png`, `02-modal-banner-job-created.png`, `03-job-detail-scope-items.png` |
| 0.2 | Customer estimate, N5=ON, parent job in `in_progress` | Customer approves | Items appended to parent `Job.scope_items`; **NO new Job** | `04-portal-approve-attached.png`, `05-parent-job-scope.png` |
| 0.3 | Customer estimate, N5=OFF | Customer approves | No Job created; estimate marked APPROVED only | `06-n5-off-approve.png` |
| 0.4 | Lead-only estimate (no customer_id) | Customer approves | Auto-job SKIPS with `skip_reason=no_customer` audit row | `07-lead-only-approve.png` |
| 0.5 | Customer estimate | Customer rejects with reason | Estimate REJECTED; rejection reason persisted | `08-portal-reject.png`, `09-modal-rejected-state.png` |
| 0.6 | Approved estimate | Click "Schedule follow-up" CTA on Approved card | Existing schedule modal opens against the new Job | `10-schedule-followup-cta.png`, `11-schedule-modal-prefilled.png` |
| 0.7 | Sent estimate, modal open in tab A | Approve via portal in tab B | Modal banner refreshes within 60s (TanStack Query polling) | `12-banner-pre-poll.png`, `13-banner-post-poll.png` |
| 0.8 | Customer estimate | Customer approves | Signed-PDF arrives in test inbox; PDF footer contains signature, IP, UA, timestamp | `14-email-inbox-pdf.png`, `15-pdf-footer-signature.png` |
| 0.9 | Any approve flow | Inspect audit log | Rows: `estimate.auto_job_created` (or `..._skipped`) with correct `details` JSONB | `16-audit-log-rows.png` |
| 0.10 | N5 toggle in admin | Flip OFF → ON | `business_settings` row updates; subsequent approval respects new value | `17-n5-toggle-off.png`, `18-n5-toggle-on.png` |

#### Verification queries

```bash
# 0.1 — new job created with scope_items copied
api_q "/api/v1/jobs/$NEW_JOB_ID" '{status, estimate_id}'
# Expected: { "status": "to_be_scheduled", "estimate_id": "<estimate_id>" }

api_q "/api/v1/jobs/$NEW_JOB_ID" '.scope_items | length'
# Expected: same length as estimate.line_items

# 0.4 — audit skip
api_q "/api/v1/audit-log?action=estimate.auto_job_skipped&limit=1" \
  '.items[0].details.skip_reason'
# Expected: "no_customer"

# 0.10 — N5 setting persisted
api_q "/api/v1/settings/business?key=auto_job_on_approval" '.value'
# Expected: { "value": true } or false depending on toggle state

# 0.8 — signed-PDF email arrived (use sim/resend_email_check.sh)
sim/resend_email_check.sh poll "$EMAIL_TEST_INBOX" "Your signed estimate"
# Expected: returns Resend message id within 90s
```

#### Acceptance
- [ ] All 10 scenarios pass with the documented screenshot count (≥18).
- [ ] Audit-log rows present for every auto-job event (`estimate.auto_job_created` / `..._skipped`).
- [ ] N5 toggle round-trips through `business_settings`.
- [ ] Signed PDF arrives at `kirillrakitinsecond@gmail.com` (verify via `sim/resend_email_check.sh poll`).
- [ ] Bug #13 regression check: customer portal `EstimateReview` does NOT crash; `business.company_logo_url` (and `company_address`/`company_phone`) populate from `SettingsService.get_company_info` (verify in `schemas/portal.py:60-70`).

#### Cleanup
- Reset N5 to its default (whichever the dev env should use post-test).
- Delete or close test approvals.

#### Re-run criteria
Re-run after any change to `EstimateService.approve_via_portal`, `EstimatePDFService`, or the N5 setting plumbing.

#### Stale-reference watchlist
- `ApprovedConfirmationCard.tsx` may have moved during the umbrella plan refactor. Grep first.

---

### Phase 4e — Real Estimate-Email → Portal-Approve End-to-End (added 2026-05-04)

**Goal**: Verify the full real-customer flow: admin creates an estimate, system fires Resend email to customer inbox, customer opens link from email, sees estimate in portal, clicks Approve, auto-job is created, admin sees the approved state. This is the *acceptance test* for the email portal — Phase 5 only does endpoint smoke; this exercises the full email round-trip with real human click.

**Prerequisites**: P0 (seed customer with allowlisted email + opt-in), P4 (sales pipeline scaffolding).

**Variant lane**: Admin (creates) → Email inbox (`kirillrakitinsecond@gmail.com`) → Public portal → Admin (verifies result).

#### VERIFY (source check)
```bash
grep -n "PORTAL_BASE_URL\|portal_base_url" src/grins_platform/services/estimate_service.py src/grins_platform/services/email_service.py
grep -n "send_estimate\|send_estimate_email" src/grins_platform/api/v1/estimates.py
grep -n "approve_portal_estimate\|approve.*estimate" src/grins_platform/api/v1/portal.py
railway variables --service Grins-dev --environment dev --kv | grep PORTAL_BASE_URL
```

⚠️ **Verify PORTAL_BASE_URL points to the CURRENT live frontend deployment, not a stale Vercel preview alias.** A 9-day-old preview that 200s but doesn't have the current React routes will silently serve a 404 page to the customer. Compare against:
```bash
# What the dev frontend alias actually resolves to:
curl -sI https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/portal/estimates/00000000-0000-0000-0000-000000000000 | head -3
# Should match PORTAL_BASE_URL on Railway. If not, this is a BLOCKER.
```

#### Steps

1. **Login admin** + obtain `$TOKEN`.

2. **Create estimate** for the seed customer:
   ```bash
   curl -s -X POST $API/api/v1/estimates -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{
     "customer_id":"<seed customer>",
     "line_items":[
       {"description":"Spring Start-Up — 8 zones","quantity":1,"unit_price":175.00,"amount":175.00},
       {"description":"Backflow Preventer Test","quantity":1,"unit_price":75.00,"amount":75.00}
     ],
     "subtotal":250.00,"tax_amount":0,"discount_amount":0,"total":250.00
   }'
   ```
   Capture `estimate_id`.

3. **Trigger send** (this is the email send + portal-token mint):
   ```bash
   curl -s -X POST $API/api/v1/estimates/$ESTIMATE_ID/send -H "Authorization: Bearer $TOKEN"
   ```
   Response includes `{estimate_id, portal_url, sent_via:["sms","email"]}`. **Inspect `portal_url`** — it should resolve at the current live frontend host.

4. **Verify the email landed**:
   ```bash
   curl -s "$API/api/v1/sent-messages?customer_id=<seed>&channel=email&limit=3" \
     -H "Authorization: Bearer $TOKEN" \
     | jq '.items[0] | {sent_at, message_type, content: (.content[0:120]), delivery_status}'
   ```
   Expect `message_type=estimate_sent`, `delivery_status=sent`.

5. **CRITICAL**: 🟡 **HUMAN** open `kirillrakitinsecond@gmail.com`, find the "Your estimate from Grins Irrigation is ready!" email, click the portal link.
   - **If 404** → BLOCKER: PORTAL_BASE_URL is wrong on Railway (verified via the 2026-05-04 run, candidate finding F4). Fix the env var and re-send.
   - **If portal loads** but Approve button doesn't work → MAJOR: FE post-approve handling broken (verified via the 2026-05-04 run, candidate finding F5).

6. **Click Approve in the portal**.

7. **Verify backend acted on the click**:
   ```bash
   curl -s "$API/api/v1/estimates/$ESTIMATE_ID" -H "Authorization: Bearer $TOKEN" \
     | jq '. | {status, approved_at, customer_id}'
   # Expect: status=approved, approved_at populated
   
   curl -s "$API/api/v1/audit-log?entity_type=estimate&entity_id=$ESTIMATE_ID&limit=10" \
     -H "Authorization: Bearer $TOKEN" \
     | jq '. | (.items // .) | .[] | {action, details}' | head -20
   # Expect: estimate.auto_job_created with details.source="customer_portal"
   #         AND sales_entry.estimate_decision_received with details.decision="approved"
   ```

8. **Verify auto-job was created** (Phase 4d intersection):
   ```bash
   # Find the new job from the audit log details.job_id
   curl -s "$API/api/v1/jobs/$AUTO_JOB_ID" -H "Authorization: Bearer $TOKEN" \
     | jq '. | {id, status, customer_id, created_at}'
   # Expect: status=to_be_scheduled, customer matches estimate.customer_id
   ```

9. **Verify FE post-approve state**: 🟡 HUMAN — what does the customer see after clicking Approve? Should be a confirmation/thank-you page, NOT an "unexpected application error" page (F5 regression).

#### Acceptance
- [ ] Resend email lands in test inbox.
- [ ] Email's portal link opens the working portal page (NOT a 404 — F4 regression).
- [ ] Customer can click Approve without seeing an error (F5 regression).
- [ ] Backend records: estimate.status=approved, audit `estimate.auto_job_created` (source=customer_portal), audit `sales_entry.estimate_decision_received` (decision=approved).
- [ ] New job created in `to_be_scheduled` linked to the estimate.

#### Stale-reference watchlist
- `PORTAL_BASE_URL` env var on Railway dev/prod must always point to the current live Vercel domain — NOT to a `frontend-git-*` preview alias. Verify on every deploy that creates a new Vercel project.

---

### Phase 4f — Sales-Pipeline Auto-Nudge / Stale-Entry Followup (added 2026-05-04)

**Goal**: Verify that a sales pipeline entry which has been sitting in `send_estimate` / `pending_approval` / `send_contract` for N days fires a customer-facing nudge email (and/or SMS), bumps `last_contact_date`, and respects the admin `pause_nudges` toggle.

**Prerequisites**: P4 (a sales pipeline entry exists with `last_contact_date` < threshold).

**Variant lane**: Operator (cron simulation) + Customer email.

#### VERIFY (source check)
```bash
# Confirm the data layer + admin API exists:
grep -n "nudges_paused_until\|last_contact_date\|pause_nudges\|unpause_nudges" \
  src/grins_platform/services/sales_pipeline_service.py \
  src/grins_platform/models/sales_pipeline.py

# CRITICAL: confirm the SCHEDULED JOB that fires nudges is registered:
grep -n "sales_pipeline\|nudge\|stale.*pipeline" src/grins_platform/services/background_jobs.py

# If the second grep returns 0 matches in register_scheduled_jobs(),
# the nudge cron is MISSING from source — this is candidate finding F6
# (verified on the 2026-05-04 run). The data model + admin API exist as
# scaffolding, but no scheduled job actually fires the nudges.
```

#### Steps

1. **Confirm registered scheduled jobs**:
   ```bash
   grep -n "scheduler.add_job" src/grins_platform/services/background_jobs.py
   # Should include a job whose entry-point function references sales_pipeline.
   # Expected job ids include something like:
   #   "send_pipeline_nudges" or "stale_estimate_followup"
   # If absent → BLOCKER (F6).
   ```

2. **Force-fire the job manually** (skips the cron schedule):
   ```bash
   # Once the job exists, locate its entry-point function in background_jobs.py
   # and invoke it via railway_python:
   PYSRC='import asyncio
   from grins_platform.services.background_jobs import send_pipeline_nudges_job
   asyncio.run(send_pipeline_nudges_job())'
   railway_python "$PYSRC"
   ```

3. **Verify a nudge email landed**:
   ```bash
   curl -s "$API/api/v1/sent-messages?customer_id=<seed>&channel=email&limit=5" \
     -H "Authorization: Bearer $TOKEN" \
     | jq '.items[] | select(.message_type | contains("nudge") or contains("followup")) | {sent_at, content: (.content[0:100])}'
   ```
   Expect at least one nudge email row with `delivery_status=sent`.

4. **Verify `last_contact_date` bumped**:
   ```bash
   curl -s "$API/api/v1/sales/pipeline/$ENTRY_ID" -H "Authorization: Bearer $TOKEN" \
     | jq '.last_contact_date'
   # Should be within the last 5 minutes.
   ```

5. **Test pause_nudges**:
   ```bash
   # Set paused-until to 7 days from now
   curl -s -X POST "$API/api/v1/sales/pipeline/$ENTRY_ID/pause-nudges" \
     -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"paused_until": "<+7d ISO>"}'
   # Re-fire the cron
   railway_python "..."
   # Verify NO new nudge email landed for this customer
   ```

6. **Test unpause**:
   ```bash
   curl -s -X POST "$API/api/v1/sales/pipeline/$ENTRY_ID/unpause-nudges" \
     -H "Authorization: Bearer $TOKEN"
   # Re-fire the cron
   # Verify a nudge email DOES land
   ```

7. **Threshold verification**: read the configured idle-window from BusinessSettings or wherever it lives (verify in source first), confirm:
   - Entries newer than threshold get NO nudge.
   - Entries older than threshold get a nudge.
   - Entries with `nudges_paused_until > now()` get NO nudge regardless of age.

#### Acceptance
- [ ] **Source check**: a scheduled job exists in `background_jobs.register_scheduled_jobs()` that operates on `sales_pipeline_entry`. (FAIL → F6 BLOCKER.)
- [ ] Nudge email lands at allowlisted inbox after force-fire.
- [ ] `last_contact_date` bumps after each nudge.
- [ ] `pause_nudges` suppresses subsequent nudges.
- [ ] `unpause_nudges` resumes nudges.

#### Stale-reference watchlist
- The `pause_nudges` / `unpause_nudges` admin API exists in `services/sales_pipeline_service.py:443-498` regardless of whether the cron is wired. Don't conclude "nudges work" just because the pause API responds 200 — verify the cron actually fires.

---

### Phase 5 — Customer Email Portal — Estimate Review & Approve/Reject

**Goal**: From the customer's email, click the portal link, review the estimate at `/portal/estimates/{token}`, approve or reject, verify state propagates back into Sales tab.

**Prerequisites**: P0, P4 step 5 (estimate sent via email).

**Variant lane**: Customer (public, no auth, token-based).

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/portal.py
grep -n "EstimateReviewPage\|estimate.*review" frontend/src/pages/portal
grep -n "estimate_token\|portal_token" src/grins_platform/models
grep -n "RESEND\|resend" src/grins_platform/services/email_service.py
```

#### Steps

1. **Resolve portal URL**: from P4 step 5, the customer received an email with a portal link `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/portal/estimates/{token}`. Three options:
   - 🤖 SIMULATOR: `e2e/master-plan/sim/resend_email_check.sh poll kirillrakitinsecond@gmail.com "Your estimate"` returns the message id; query the message body for the token via `sim/resend_email_check.sh get <message_id>`.
   - 🟡 HUMAN: read the email at `kirillrakitinsecond@gmail.com` and copy the link.
   - API direct: query the sales pipeline entry's portal token (token field on the entry; verify field name in `schemas/sales_pipeline.py`).
2. Open in fresh agent-browser session: `agent-browser --session portal-estimate open <portal-url>`.
3. Verify page renders without auth (public). Screenshot `01-portal-loaded.png`.
4. Verify customer name, address, line items, total all match the sales entry. Screenshot `02-estimate-detail.png`.
5. **Approve flow**:
   - Click Approve → expect signing iframe (SignWell remote) OR direct approval action depending on whether it's pre- or post-signature stage.
   - Sign in iframe (SignWell test mode).
   - Verify success state. Screenshot `03-approved.png`.
   - Verify back in admin: sales entry advanced to next stage; an internal email notification sent to admin (Resend); `audit_log` records the approval.
6. **Reject flow** (separate token):
   - Open another estimate's portal URL → click Reject.
   - Provide rejection reason. Submit. Screenshot `04-rejected.png`.
   - Verify sales entry → `Closed-Lost`; admin notification email sent.
7. **Token validity** — per memory `.agents/plans/estimate-approval-email-portal.md`: tokens are valid 60 days. Test:
   - Manually invalidate (or use an old/expired token from DB) → expect 410 Gone or appropriate error.
   - Token for already-approved estimate → idempotent or 409.
8. **Bounce webhook** (Resend → backend):
   - Force a bounce by sending the estimate to a rejected address (modify customer email to `bounced@simulator.amazonses.com` or use Resend's test bounce mechanism).
   - Verify `POST /api/v1/webhooks/resend` receives the bounce event.
   - Verify HMAC-SHA256 signature validation enforced (send unsigned → 401).
   - Verify internal admin email sent flagging the bounce.
   - Restore customer email afterward.
9. **Email allowlist guard** (dev-only): verify that sending an estimate to a non-allowlisted email fails with 422 (not 500 — per `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` Bug 2 lesson).

#### Acceptance
- [ ] Portal loads without auth, renders correct estimate.
- [ ] Approve → sales advances + admin notified.
- [ ] Reject → Closed-Lost + admin notified.
- [ ] Expired/invalid tokens fail gracefully (no 500).
- [ ] Resend bounce webhook signature-verified.

#### Cleanup
- Reset customer email to seeded value if changed.

#### Re-run criteria
- Requires P4 step 5 to have sent an email. Independently, can be invoked by manually creating an estimate token via API.

#### Stale-reference watchlist
- Older `feature-developments/estimate approval email portal/` docs may describe a stub flow; per memory `Estimate email portal wired via Resend (2026-04-26)` it's now live in `_send_email`. Confirm.

---

### Phase 6 — Customers Tab — Master Record

**Goal**: Verify customer detail page tabs (Overview, Photos, Invoice History, Payment Methods, Messages, Potential Duplicates), tags, properties, service preferences, soft-delete + merged tracking.

**Prerequisites**: P0; P2/P3 customer is helpful but any seed customer works.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/customers.py | head -30
grep -n "Overview\|Photos\|Invoice History\|Payment Methods\|Messages\|Potential Duplicates" frontend/src/features/customers
grep -n "is_deleted\|merged_into_customer_id" src/grins_platform/models/customer.py
grep -n "Residential\|Commercial\|HOA\|Subscription" frontend/src/features/customers/components
```

#### Steps

1. Login admin → `/customers`. Screenshot list `01-customers.png`.
2. Apply each filter combination (Residential, Commercial, HOA, Subscription, custom tags) → verify URL contains filter state. Screenshot `02-filtered.png`.
3. CSV export: trigger export, verify file downloaded, columns match.
4. Open seed customer detail → screenshot `03-customer-detail.png`.
5. **Tabs**: click each — Overview, Photos, Invoice History, Payment Methods, Messages, Potential Duplicates → verify content per `update2_instructions.md:674` table. Screenshot each.
6. **Customer flags**: toggle Priority, Red Flag, Slow Payer; verify persists via API.
7. **Customer tags**: add a tag with each color tone (neutral, blue, green, amber, violet). Verify renders in list and detail.
8. **Service Preferences**:
   - Add preference: Spring Startup, Week of April 13, Morning, "MWF only" notes.
   - Verify saved via API.
   - Create a new job for this customer with service_type=Spring Startup → verify Week Of auto-populates from preference; preference notes appear as hint on job detail.
9. **Properties**:
   - Add a second property; switch primary; delete a non-primary property.
   - Verify `Residential`/`Commercial` type, zone count, gate code, dogs flag all persist.
   - Property tags (Residential/Commercial/HOA/Subscription) show on Jobs list, Job detail, and Schedule calendar cards (per `update2_instructions.md:687`).
10. **Soft delete + merge**: trigger a manual soft delete via API → verify `is_deleted=true` and `deleted_at` set; verify it disappears from default list but is recoverable via filter or admin view.
11. **Bulk preferences update**: select multiple customers, bulk-update SMS opt-in → verify via API.
12. **Real-time duplicate warning** (covered in P17, but cross-link): when adding a new customer with a phone matching an existing one, expect inline warning with `Use existing customer` button.

#### Acceptance
- [ ] All 6 tabs populate.
- [ ] Filters round-trip via URL.
- [ ] Service preferences hint propagates to job detail.
- [ ] Property tags render where claimed.
- [ ] Soft-delete preserves audit trail.

#### Cleanup
- Restore any flag changes on the seed customer; remove test tags; un-soft-delete the test record.

#### Re-run criteria
- Standalone-runnable. Uses the seed customer.

#### Stale-reference watchlist
- The Properties section's tag rendering location: spec says tags render on Jobs/Job Detail/Schedule cards, NOT on the customer-detail Properties section itself. Confirm.

---

### Phase 7 — Jobs Tab — Ready to Schedule

**Goal**: Verify job list filters, status transitions, "Week Of" picker (inline edit), Schedule button, badges (Estimate Needed, Prepaid, property tags).

**Prerequisites**: P0; ideally P3 or P4 produced a job.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/jobs.py | head -20
grep -n "WeekPicker\|week-of\|Week Of" frontend/src/features/jobs
grep -n "Estimate Needed\|estimate-needed\|Prepaid\|prepaid" frontend/src/features/jobs
ls frontend/src/pages/Jobs.tsx
```

#### Steps

1. Login → `/jobs`. Screenshot `01-jobs.png`.
2. Verify columns: Job Type, Summary, Status, Customer, Tags, Days Waiting, Week Of, Priority, Amount, Actions.
3. **Filters**: each axis (Status, property type, HOA, Subscription, Week, multi-axis AND combination). Capture URL query strings.
4. **Inline Week Of edit**: click the Week Of cell on a `to_be_scheduled` job → calendar appears → pick a Monday → save. Verify `week_of` updated via API; verify display reads "Week of M/D/YYYY".
5. **Schedule button**: click on a `to_be_scheduled` row → verify navigation to Schedule tab with appointment-creation form pre-filled (customer, job type, address). Screenshot `02-schedule-prefilled.png`. Don't save yet — back out.
6. **Estimate Needed badge**: visually verify on jobs that bypassed the estimate workflow (created from leads with `requires_estimate=true` override).
7. **Prepaid badge**: on a job linked to a service agreement (subscription), verify the badge shows; verify on Schedule calendar card too.
8. **Property tags on rows**: Residential/Commercial, HOA, Subscription badges visible.
9. **Days Waiting calculation**: pick a job with known created_at, verify days waiting matches `now() - created_at` rounded down.
10. **Status transitions** (UI level — not the on-site workflow which is P11): force-set a job's status via the detail page (admin power), verify allowed states match the documented state machine.
11. **Job action dropdown visibility regression** (per `bughunt/job_actions_missing.md`). VERIFY: `grep -n "to_be_scheduled\|in_progress" frontend/src/features/jobs/components/JobList.tsx` should return lines `:409` (Start Job — `to_be_scheduled`) and `:414` (Mark Complete — `in_progress`). The bughunt documents that an earlier version checked `=== 'scheduled'` (a status that never existed) so neither button rendered. Steps: (a) on a `to_be_scheduled` job row, click `[data-testid='job-actions-${id}']` → assert "Start Job" item present, "Mark Complete" absent; screenshot `03-job-actions-to_be_scheduled.png`; (b) click Start Job → row status flips to `in_progress`; reopen dropdown → assert "Mark Complete" present, "Start Job" absent; screenshot; (c) click Mark Complete → status `completed`; reopen → assert both action items absent and "Cancel Job" also absent (per `JobList.tsx:420` excludes `completed`/`cancelled`).
12. **City-priority sort** (per `.agents/plans/pick-jobs-city-requested-priority-fixes.md`). VERIFY: `grep -n "city\|priority" src/grins_platform/services/schedule_solver_service.py`. Steps: open `/schedule/pick-jobs` → assert jobs list groups by city; tier-priority badge renders on city-priority rows; toggling the priority filter narrows results to those rows. (Detailed pick-jobs UX coverage in P8 step 11.)

#### Acceptance
- [ ] All filters AND-combine correctly.
- [ ] Week Of inline edit persists and re-displays as Monday.
- [ ] Schedule button pre-fills appointment form.
- [ ] All badges render where claimed.
- [ ] Job action dropdown shows "Start Job" only on `to_be_scheduled`, "Mark Complete" only on `in_progress`, both absent on `completed`.
- [ ] Pick-jobs page groups by city and surfaces tier-priority badge.

#### Cleanup
- Revert any week-of changes that were test-only.

#### Re-run criteria
- Standalone if jobs already exist; otherwise depends on P3/P4.

---

### Phase 8 — Schedule Tab — Calendar, Drag-Drop, Send Confirmations (Admin)

**Goal**: Create appointments (DRAFT → SCHEDULED), drag-drop, edit, cancel (both no-text and with-text variants), bulk send confirmations.

**Prerequisites**: P0, P7 (jobs to schedule).

**Variant lane**: Admin desktop. Tech-mobile schedule is separate (P11).

#### VERIFY (source check)
```bash
grep -n "@router\.(post|get|patch|delete)" src/grins_platform/api/v1/appointments.py | head -30
grep -n "data-testid" frontend/src/features/schedule/components/AppointmentList.tsx | head -20
grep -n "view-list\|appointment-row\|view-appointment-" frontend/src/features/schedule
grep -n "Send Confirmation\|send-confirmation" frontend/src/features/schedule
grep -n "Send All Confirmations\|bulk_send_confirmations" frontend/src/features/schedule
```

Confirmed in source: `POST /api/v1/appointments/{id}/send-confirmation` (line 1172), `POST /api/v1/appointments/send-confirmations` bulk (line 544).

#### Steps

1. Login → `/schedule`. Screenshot `01-schedule.png`.
2. **Create appointment from job picker**:
   - Open Job Picker; filter by Week Of.
   - Single-job assign: pick a job, set date/time/staff; save → verify DRAFT appointment with dotted border. Screenshot `02-draft.png`.
   - Bulk assign: select 3+ jobs, assign all to same date/staff with global time; verify each created as DRAFT.
3. **Verify DRAFT silence**: confirm NO SMS sent (check `sent_messages` API).
4. **Move DRAFT silently**: drag a DRAFT to a different time → verify still DRAFT, no SMS.
5. **Per-appointment Send Confirmation**: click the button on a DRAFT card → verify status flips to SCHEDULED (dashed border); SMS row appears in `sent_messages` with `message_type=appointment_confirmation`. Screenshot `03-scheduled.png`. (🟡 HUMAN can confirm receipt, but not required at this step — full Y/R/C is P9.)
6. **Per-day Send Confirmations**: click "Send Confirmations for [Day]" header → verify all DRAFTs on that day flip.
7. **Bulk Send All Confirmations**: click "Send All Confirmations" → confirm modal shows count, names, dates. Confirm. Verify all flip and individual SMS rows logged.
8. **Edit a SCHEDULED**: change date or time → verify reschedule notification SMS sent and status reset to SCHEDULED. Screenshot.
9. **Cancel — Cancel & text customer**: open appointment details modal → Cancel → choose "Cancel & text customer" → verify status CANCELLED, cancellation SMS sent, on-site timestamps cleared, audit log entry with `notify_customer=true`.
10. **Cancel — Cancel (no text)**: separate appointment → Cancel → "Cancel (no text)" → verify CANCELLED but NO cancellation SMS, audit log `notify_customer=false`.
11. **Cancel a DRAFT**: silent regardless of choice.
12. **Cancel last active appointment for a job**: verify job reverts from SCHEDULED → TO_BE_SCHEDULED.
13. **Reactivation**: from Reschedule Requests queue (or by editing a CANCELLED appointment), reactivate → verify reschedule SMS sent and status → SCHEDULED.
14. **Visual states verification**: take a screenshot showing DRAFT (dotted+gray), SCHEDULED (dashed+muted), CONFIRMED (solid+full-color) all on the same calendar view if possible.
15. **Appointment-modal CTA labels** (Umbrella Task 6.6.1–6.6.2): open any appointment → verify Estimate CTA reads `"Send estimate"` (not legacy `"Create Estimate"`); action-track button labels are `"On my way"` / `"Job started"` / `"Job complete"`. Screenshots `15-cta-label.png`, `16-action-track-labels.png`.
16. **Send Confirmation visible on DRAFT** (per `bughunt/2026-04-16-medium-bugs-plan.md` M-1). VERIFY: `grep -n "send-confirmation" frontend/src/features/schedule/components/SendConfirmationButton.tsx` should resolve. Steps: create a DRAFT appointment (step 2 above), assert `[data-testid='send-confirmation-icon-${id}']` (compact form, line 62) OR `[data-testid='send-confirmation-btn-${id}']` (full form, line 77) is rendered AND enabled — earlier versions hid the button on DRAFT, only revealing it on SCHEDULED. Screenshot `17-draft-send-confirmation-button.png`.
17. **Persistent SchedulingTray** (per `.agents/plans/pick-jobs-ui-redesign-persistent-tray.md`). VERIFY: `grep -n "SchedulingTray" frontend/src/features/schedule/components/SchedulingTray.tsx frontend/src/features/schedule/pages/PickJobsPage.tsx`. Steps: open `/schedule/pick-jobs` → assert `[data-testid='scheduling-tray']` present and sticky (its `getBoundingClientRect().bottom` near viewport bottom on every scroll); add a job to the tray → scroll the underlying list — assert tray still visible; navigate away then back — assert tray contents persist (or reset cleanly per spec). Screenshots `18-tray-empty.png`, `19-tray-with-job.png`, `20-tray-after-scroll.png`.

#### Acceptance
- [ ] DRAFT moves are silent.
- [ ] All three Send Confirmation paths (single, day, bulk) work.
- [ ] Cancel (no text) suppresses SMS; Cancel & text sends it; both audit-logged.
- [ ] Job status reverts on last-cancellation.
- [ ] Send Confirmation button is visible+enabled on DRAFT cards.
- [ ] Pick-jobs SchedulingTray remains sticky during scroll.

#### Cleanup
- Move all test appointments to a known cleanup state or delete them in P24.

#### Re-run criteria
- Requires jobs from P7. Re-runnable if fresh jobs exist.

#### Stale-reference watchlist
- `e2e/payment-links-flow.sh` Bug 6 is **CLOSED** (now requires `APPOINTMENT_ID` env). When writing new shells, target by appointment id via `[data-testid='view-appointment-{id}']` or `[data-testid='appt-card-{id}']` not first-of-class.

---

### Phase 9 — SMS Confirmation Flow Y / R / C / STOP / START 🟡 HUMAN OR 🤖 SIMULATOR

**Goal**: Verify the customer-reply flow for appointment confirmation.

**Prerequisites**: P0, P8 (a SCHEDULED appointment with a sent confirmation SMS, capturing its `provider_thread_id`).

**Variant lane**: SMS (CallRail webhook → backend).

**Two execution modes**:
- **HUMAN mode** — phone-holder at +19527373312 reads each confirmation SMS and replies. Required at least once before each release for carrier-level smoke.
- **SIMULATOR mode** — `e2e/master-plan/sim/callrail_inbound.sh <thread_id> <body>` posts an HMAC-signed payload at `POST /api/v1/webhooks/callrail/inbound`. Same code path, faster iteration. Use for CI / change-targeted re-runs.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/callrail_webhooks.py    # POST /webhooks/callrail/inbound at line 211
grep -n "verify_webhook_signature" src/grins_platform/api/v1/callrail_webhooks.py  # HMAC at 243
grep -n "_handle_confirm\|_handle_reschedule\|_handle_cancel" src/grins_platform/services/sms
grep -n "@router\." src/grins_platform/api/v1/reschedule_requests.py
grep -n "STOP\|START" src/grins_platform/services/sms
```

⚠️ **CallRail webhook must be configured on the dev backend** so real CallRail can reach it. Per memory, Phase 0 of CallRail integration is complete (10DLC registered, IDs resolved). The path is `POST /api/v1/webhooks/callrail/inbound`. Verify env var `CALLRAIL_WEBHOOK_SECRET` is set on dev and matches what the CallRail dashboard signs with.

#### Steps

This phase mirrors `Testing Procedure/04-path-d-e-confirmation-yrc.md`. Each sub-step has both a HUMAN line and a SIMULATOR line. Pick one or run both for redundancy. After sending the confirmation in P8, capture the appointment's `provider_thread_id` from `GET /api/v1/customers/{KIRILL}/sent-messages?limit=5`:

```bash
THREAD_ID=$(api GET "/api/v1/customers/$KIRILL_CUSTOMER_ID/sent-messages?limit=5" \
  | jq -r ".items[] | select(.related_appointment_id == \"$APT_ID\") | .provider_thread_id")
```

##### D1/E1 — Reply Y
1. Pick a Kirill TBS job, create appointment, send confirmation, capture `THREAD_ID`.
2. **EITHER** 🟡 HUMAN: **REPLY: Y**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "Y"`
3. Verify status=`confirmed` via API. Verify `recipient_phone=+19527373312` (E.164, NOT masked `***3312` — CR-3 fix per `04-path-d-e:60`).

##### E3 — Reply R (creates reschedule_request)
1. Fresh appointment + send confirmation; capture `THREAD_ID`.
2. **EITHER** 🟡 HUMAN: **REPLY: R**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "R"`
3. Phone should receive **two** auto-replies (acknowledgment + 2-3-dates ask) when in HUMAN mode; in SIMULATOR mode verify both outbound rows in `sent_messages`.
4. Verify `GET /api/v1/schedule/reschedule-requests?status=open` → row with `raw_alternatives_text='R'`, status=open.

##### E4/E5 — Append alternatives (Sprint 7 M-3)
1. Same thread as E3.
2. **EITHER** 🟡 HUMAN: **REPLY: Tue 2pm**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "Tue 2pm"`
3. Verify `requested_alternatives.entries` has 1 entry.
4. **EITHER** 🟡 HUMAN: **REPLY: or Wed morning**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "or Wed morning"`
5. Verify 2 entries, in order. Both preserved (append, not replace).

##### E6/E7 — Reply C, then C again (idempotency)
1. Fresh appointment + send confirmation; capture `THREAD_ID`.
2. **EITHER** 🟡 HUMAN: **REPLY: C**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "C"`
3. Verify status=`cancelled`. Cancellation message with service type + time should be in `sent_messages`.
4. **EITHER** 🟡 HUMAN: **REPLY: C** again
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "C"`
5. **Known gap**: per `update2_instructions.md:1130` and `04-path-d-e:138`, repeat C should be no-op (H-2). Per memory, H-2 was half-fixed — DB stayed cancelled (correct) but `_handle_cancel` unconditionally sent the reply SMS. **Re-verify current behavior** by counting cancellation rows in `sent_messages` for this thread; if >1, file as ongoing gap.

##### E8 — Reply STOP
1. Fresh appointment + send confirmation; capture `THREAD_ID`.
2. **EITHER** 🟡 HUMAN: **REPLY: STOP**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "STOP"`
3. In HUMAN mode, CallRail's provider-level handler returns the unsubscribe confirmation. In SIMULATOR mode, only the backend-side consent handling fires — the carrier-level block does NOT happen (that's a CallRail-only behavior).
4. Verify `POST /api/v1/sms/send` for that customer returns 403 "Consent denied" (HTTP 403 per `04-path-d-e:156`).
5. **Audit-log on hard STOP** (per `gap-05-audit-trail-gaps.md`). VERIFY: `grep -n "log_consent_hard_stop\|sms.consent.hard_stop_received" src/grins_platform/services/sms/audit.py` resolves at lines `126`/`134`. The `/audit-log` endpoint accepts `?action=&resource_type=&page=&page_size=` filters (per `api/v1/audit.py:43-56`) and returns `{items, total}`. Steps: query `api_q "/api/v1/audit-log?action=sms.consent.hard_stop_received&page_size=5" '.items[0].action, .items[0].resource_type, .items[0].details.phone'` → assert action `sms.consent.hard_stop_received`, resource_type `sms_consent`, and `details.phone` is the masked form (NOT the full +19527373312 — masking is the source-side privacy guarantee). Capture timestamp; assert it is within ±10s of the inbound STOP processing.

##### E8b — Informal opt-out alert chain
VERIFY: `grep -n "log_informal_opt_out_flagged\|log_informal_opt_out_confirmed\|INFORMAL_OPT_OUT" src/grins_platform/services/sms/audit.py src/grins_platform/services/sms_service.py` should resolve at `audit.py:140-160` and `sms_service.py:1188`. The customer says something like "stop texting me please" (an informal phrase, not literal STOP).
1. Fresh appointment + send confirmation; capture `THREAD_ID`.
2. **EITHER** 🟡 HUMAN: **REPLY: stop texting me please**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "stop texting me please"`
3. Assert an `Alert` row is created with `type='informal_opt_out'`. Capture its `id` as `$ALERT_ID` (`api_q "/api/v1/alerts?type=informal_opt_out&limit=1" '.items[0].id'`). Note: `/alerts` accepts both legacy `?type=` (single, back-compat) and `?alert_type=` (repeatable) per `api/v1/alerts.py:65-79`; this test uses the back-compat form.
4. Assert audit log entry `action=sms.informal_opt_out.flagged`, `resource_type=alert`, `resource_id=$ALERT_ID` (`api_q "/api/v1/audit-log?action=sms.informal_opt_out.flagged&page_size=1" '.items[0]'`).
5. From admin UI on `/alerts/informal-opt-out` (router-mounted page), confirm the alert (mark customer as opted-out) → assert audit log entry `action=sms.informal_opt_out.confirmed` with same `resource_id`.
6. Assert that subsequent SMS send to that customer for any of the suppressed `MessageType`s in `_RESPECTS_PENDING_INFORMAL_OPT_OUT` (per `sms_service.py:107`) is suppressed.

##### E9 — Restore consent (no START handler in backend)
1. Run `clear_consent.py` via railway ssh (per `04-path-d-e:165-172`) — works in both modes.
2. 🟡 **HUMAN ONLY** (simulator can't help — carrier state is CallRail-side): **REPLY: START** to a thread to clear CallRail's carrier block. Wait up to 10 min.
3. Verify `POST /api/v1/sms/send` works again.

##### Anything-else replies
1. Fresh appointment.
2. **EITHER** 🟡 HUMAN: **REPLY: I'm not sure, please call me**
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "I'm not sure, please call me"`
3. Verify message logged with `needs_review` flag (per `update2_instructions.md:838`).

##### E2-bis — Repeat-Y idempotency + reassurance SMS (per `.agents/plans/repeat-confirmation-idempotency.md`)
VERIFY: `grep -n "reassurance\|already.*confirmed\|repeat" src/grins_platform/services/job_confirmation_service.py`. If short-circuit not present in source, mark this case as out-of-scope and skip.
1. Use the same thread as D1/E1 (appointment now CONFIRMED).
2. **EITHER** 🟡 HUMAN: **REPLY: Y** again
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "Y"`
3. Verify status stays `confirmed` (no duplicate transition). Query `JobConfirmationResponse` rows for this appointment via `api_q "/api/v1/appointments/$APT_ID/timeline" '.confirmation_responses|length'` (or equivalent endpoint) — expect either a single row or a duplicate row with `outcome='already_confirmed'`. Verify outbound `sent_messages` for this thread contains a reassurance message (e.g., "You're already confirmed for …") **without** duplicating the original confirmation SMS.

##### E10 — provider_thread_id persistence on outbound (per `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-3 dev-env blocker)
VERIFY: `grep -n "provider_thread_id" src/grins_platform/models/sent_message.py src/grins_platform/services/sms_service.py`. Steps: send a confirmation in P8 then capture the most recent outbound row: `api_q "/api/v1/customers/$KIRILL_CUSTOMER_ID/sent-messages?limit=1" '.items[0].provider_thread_id'` — assert non-null and matches the thread on which inbound replies will be routed (used by `_handle_confirm` to correlate). The earlier dev-env blocker noted this column was empty; current source persists it on outbound.

##### E11 — Post-cancel "R" handling (per `.agents/plans/thread-correlation-hardening.md`)
VERIFY: `grep -n "appointment.reschedule_rejected\|late_reschedule_attempt\|post_cancel" src/grins_platform/services/job_confirmation_service.py src/grins_platform/services/sms_service.py`. Steps: starting from an appointment already CANCELLED in E6/E7, capture its old `THREAD_ID` and:
1. **EITHER** 🟡 HUMAN: **REPLY: R** to that old thread
   **OR** 🤖 SIMULATOR: `sim/callrail_inbound.sh "$THREAD_ID" "R"`
2. Assert appointment status stays `cancelled` (no reactivation).
3. Assert a row is created marking the reply as `appointment.reschedule_rejected` and emitting a `late_reschedule_attempt` alert.

#### Acceptance
- [ ] Y → CONFIRMED, recipient E.164.
- [ ] R → reschedule_request open, 2 auto-replies.
- [ ] E4 → 1 alternative entry; E5 → 2 entries ordered.
- [ ] C → CANCELLED with service-type-aware SMS.
- [ ] STOP → SMS send 403'd thereafter.
- [ ] START or `clear_consent.py` restores send capability.
- [ ] Anything-else logged as needs_review.
- [ ] Repeat Y on a CONFIRMED appointment short-circuits (no duplicate transition) and produces a reassurance SMS, OR (if not implemented) is documented as out-of-scope.
- [ ] `provider_thread_id` is non-null on the outbound confirmation row.
- [ ] Post-cancel "R" reply does NOT reactivate the appointment; logged as `appointment.reschedule_rejected` (Gap 1.B state guard at `services/job_confirmation_service.py:461-490`). Plan was previously phrased as `stale_thread_reply`; the code-side audit discriminator is the authoritative behavior.
- [ ] Hard STOP emits an audit-log entry `sms.consent.hard_stop_received` with masked phone in details.
- [ ] Informal opt-out phrase fires an `INFORMAL_OPT_OUT` alert, audit chain `sms.informal_opt_out.{flagged,confirmed}` written, follow-up suppressed-`MessageType` sends are blocked.

#### Known gaps to document
- E7 idempotency: duplicate cancellation SMS may still send (H-2 half-fix).
- No backend START handler — only CallRail provider-side.
- `customers.sms_opt_in` denormalized mirror may stay `true` after STOP — source of truth is consent_records.

#### Cleanup
- Restore opt-in via `clear_consent.py`.
- Verify SMS send works before exiting (probe).

#### Re-run criteria
- Requires HUMAN at least once before each release for carrier-level smoke. SIMULATOR-mode runs are CI-safe and per-iteration. Must run after P8.

#### Stale-reference watchlist
- `04-path-d-e:30-37` uses date `2026-04-21` — the test text shape is what matters; date can be any future date.
- Webhook HMAC verification per `callrail_webhooks.py:243` — confirmed enforced. Try replay with same `id` → expect dedup; try invalid HMAC → expect 403 (NOT 401 — that's the actual response code).
- Old `scripts/e2e/test-sms-lead.sh` references `[name='email']` for login — DO NOT copy. Use `_dev_lib.sh:login_admin`.

---

### Phase 10 — Reschedule Requests Queue & Lifecycle

**Goal**: From admin Schedule tab, work the Reschedule Requests queue: pick alternative, reschedule, mark resolved, observe new confirmation SMS sent.

**Prerequisites**: P0, P9 step E5 (an open reschedule request with 2 alternatives).

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/reschedule_requests.py
grep -nr "Reschedule Requests\|reschedule-requests\|rescheduleRequests" frontend/src/features/schedule
```

#### Steps

1. Login → `/schedule` → Reschedule Requests panel/queue. Screenshot `01-queue.png`.
2. Verify the open request from P9 E5 visible with 2 alternative entries displayed.
3. Click `Reschedule to Alternative` → opens appointment editor pre-filled with one of the customer's requested times. Screenshot.
4. Save the new time → verify a fresh confirmation SMS sent (NEW thread). 🟡 **HUMAN**: phone-holder confirms receipt; reply Y to complete the cycle.
5. Verify reschedule request row marked `resolved` (or removed from open queue).
6. Test `Mark Resolved` directly without rescheduling → verify status flips.
7. **Late-reschedule edge case** (per `feature-developments/scheduling gaps/gap-01-reschedule-request-lifecycle.md`). VERIFY: `grep -n "EN_ROUTE\|en_route\|in_progress" src/grins_platform/services/appointment_service.py`. Steps: pick an appointment, advance status to EN_ROUTE (admin override), then try `POST /api/v1/schedule/reschedule-requests/{id}/resolve` or the equivalent UI action — assert 412 Precondition Failed (or whatever the source raises) and reschedule queue still shows the request as open. Repeat with status IN_PROGRESS.
8. **Duplicate R rows**: per same gap doc, duplicate "R" replies should not create duplicate reschedule_request rows. Send R again → verify only one open row remains.
9. **Follow-up message correlation**: per gap-01, confirm follow-up "2-3 dates" message correlates back via correct filter (not wrong-filter case).
10. **Invalid appointment-status transition rejection** (per `.agents/plans/enforce-appointment-state-machine.md` and `feature-developments/scheduling gaps/gap-04-state-machine-not-enforced.md`). VERIFY: `grep -n "VALID_APPOINTMENT_TRANSITIONS\|can_transition_to" src/grins_platform/services/appointment_service.py src/grins_platform/models/appointment.py`. Steps: pick a COMPLETED appointment, attempt `PATCH /api/v1/appointments/{id}` setting `status='scheduled'` → expect 422 with `InvalidStatusTransitionError`. Try CANCELLED→IN_PROGRESS → expect 422. Try IN_PROGRESS→COMPLETED on a started appointment → expect 200 (allowed).

#### Acceptance
- [ ] Queue renders open requests with alternatives.
- [ ] Reschedule-to-alternative pre-fills correctly.
- [ ] New SMS thread on reschedule.
- [ ] Mark Resolved closes the row.
- [ ] Late-reschedule and duplicate-R behavior matches gap doc expectations.
- [ ] Invalid status transitions return 422 (`InvalidStatusTransitionError`); valid transitions return 200.

#### Cleanup
- Mark any leftover open requests as resolved.

---

### Phase 11 — Tech Mobile Schedule (iPhone view) 📱

**Goal**: Login as technician, land on `/tech`, exercise mobile schedule view, on-my-way → started → complete state machine, photo upload, notes.

**Prerequisites**: P0, a confirmed appointment exists assigned to one of the seeded techs (`vasiliy` / `steve` / `gennadiy`).

**Variant lane**: Tech mobile (viewport 375×812; gated by role=tech and PhoneOnlyGate).

#### VERIFY (source check)
```bash
grep -n "TechMobileLayout\|TechSchedulePage\|PhoneOnlyGate" frontend/src/features/tech-mobile
grep -n "/tech" frontend/src/core/router/index.tsx
ls frontend/src/features/tech-mobile/
grep -n "On My Way\|Job Started\|Job Complete\|on_my_way_at\|started_at\|completed_at" src/grins_platform/api/v1/appointments.py | head -10
grep -n "request-review\|Google Review" src/grins_platform/api/v1
```

#### Steps

1. **Set viewport**: `agent-browser set viewport 375 812`.
2. **Login as tech**: open `$BASE/login`, fill `[data-testid='username-input']`=`vasiliy`, `[data-testid='password-input']`=`tech123`, click `[data-testid='login-btn']`. Verify redirect to `/tech` (PostLoginRedirect at router/index.tsx:143 routes role=tech to /tech). Screenshot `01-tech-landing.png`. **Note**: `PhoneOnlyGate` runs inside `TechMobileLayout`, not at the route level — non-phone viewports hit the gate's landing page after layout mounts.
3. **Mobile schedule view**: verify only today's appointments for this tech visible. Pull-to-refresh; verify network call.
4. **Tap an appointment**: opens detail view. Screenshot `02-appt-detail.png`.
5. **On My Way**: tap → SMS sent ("We're on our way!"); verify `on_my_way_at` set; appointment status CONFIRMED → EN_ROUTE. 🟡 **HUMAN** (optional): customer phone receives the SMS.
6. **Job Started**: tap → `started_at` logged; job IN_PROGRESS; appointment IN_PROGRESS. NO SMS sent.
7. **Add Photo** (mobile camera): in headless agent-browser this may not be directly testable. Either (a) skip with a note, or (b) use file-upload via `agent-browser fill` on the file input.
8. **Add Note**: type a note; submit; verify on customer record.
9. **Job Complete** with payment-warning checks:
   - Path (a): one-off job, no invoice, no payment → expect "No Payment or Invoice on File" warning. Screenshot `03-payment-warn.png`. Test "Cancel" — go back. Test "Complete Anyway" — proceed; audit-logged.
   - Path (b): service agreement job → no warning, direct complete with "Covered by [Agreement]" indicator.
   - Path (c): payment already collected on-site → no warning.
   - Path (d): invoice already exists → no warning.
10. **Status visual transitions**: ensure tech-mobile UI reflects each status correctly.
11. **Time tracking**: verify travel time + work time + total time stored in `time_tracking_metadata` after Complete.
12. **Skip scenarios**:
    - Click Job Complete without Started → verify both job + appointment go to COMPLETED.
    - Click Job Started without On-My-Way → verify CONFIRMED → IN_PROGRESS.
13. **Google Review push** (job-level button — no dedup):
    - Click → SMS sent. 🟡 **HUMAN**: confirm receipt.
    - Click again → another SMS sent (no dedup per `update2_instructions.md:354`).
14. **Appointment-level review request** (separate endpoint with 30-day dedup):
    - `POST /api/v1/appointments/{id}/request-review` → 200; second within 30 days → 409.
15. **PhoneOnlyGate**: from a non-phone viewport (e.g., 1280×800), navigate to `/tech` → expect a landing page indicating phone-only.
15a. **AppointmentDetail communication timeline** (per `gap-11-appointment-detail-inbound-blind.md` and `.agents/plans/appointment-detail-communication-timeline.md`). VERIFY: `grep -n "/timeline\|AppointmentTimelineService\|AppointmentTimelineResponse" src/grins_platform/api/v1/appointments.py` resolves at `:1013`. Schema (per `src/grins_platform/schemas/appointment_timeline.py:88,44-45`): `events: list[TimelineEvent]`; each event has `kind` (the discriminator) and `occurred_at` (timestamp). `TimelineEventKind` values: `outbound_sms`, `inbound_reply`, `reschedule_opened`, `reschedule_resolved`, `opt_out`, `opt_in`, `payment_received` (per `AppointmentCommunicationTimeline.tsx:38-46`). Steps: take an appointment that has gone through P8 (send confirmation) and P9 (Y or R reply); call `api_q "/api/v1/appointments/$APT_ID/timeline" '.events|length, [.events[].kind]'`. Assert the response contains at least:
    - one `outbound_sms` (the confirmation),
    - one `inbound_reply` (Y, R, or anything-else),
    - any `reschedule_opened` / `reschedule_resolved` from P10,
    - `opt_out` if customer hit STOP.
    Events are returned newest-first per the schema description (`appointment_timeline.py:90`); assert `.events == [.events[]] | sort_by(-(.occurred_at | fromdateiso8601))` (or simpler: that `.events[0].occurred_at >= .events[-1].occurred_at`). Render side: open AppointmentDetail in admin UI; the timeline lives at `[data-testid='appointment-communication-timeline']` (`AppointmentCommunicationTimeline.tsx:67`); each row is `[data-testid='timeline-event-${event.id}']` (`:154`). Click `[data-testid='toggle-communication-timeline-btn']` (`:111`) to expand. Screenshot `15a-timeline.png`; assert at least one row of each expected `kind` rendered.

16. **AppointmentDetail secondary actions matrix** (per `.agents/plans/appointment-modal-secondary-actions.md`). VERIFY: `grep -n "data-testid" frontend/src/features/schedule/components/AppointmentDetail.tsx frontend/src/features/schedule/components/AppointmentModal/NotesPanel.tsx frontend/src/features/schedule/components/AppointmentModal/PhotosPanel.tsx`. From the AppointmentDetail modal (admin desktop AND tech-mobile), exercise each secondary action:
    - **Notes** — open `[data-testid='notes-section']` (`AppointmentDetail.tsx:621`), type a note, save → assert persisted via `GET /api/v1/appointments/{id}` returns the note.
    - **Tags** — locate the tags chip in the customer-info or job-info section (re-grep specific testid first); add a tag, save → assert persisted.
    - **Photos** — upload a sample image via `agent-browser fill "input[type=file]" /path/to/sample.jpg` (testid lives in `PhotosPanel.tsx`; re-grep before run) → assert a row appears under Photos.
    - **Reschedule shortcut** — click `[data-testid='reschedule-to-alternative-${appointmentId}-btn']` (`AppointmentDetail.tsx:405`) when a banner is open, OR open the modal and trigger reschedule → assert ScheduleVisit modal opens pre-filled.
    - **Mark Contacted** — click `[data-testid='mark-contacted-${appointmentId}-btn']` (`AppointmentDetail.tsx:466`) → assert audit log entry via `api_q "/api/v1/audit-log?action=appointment.contact_attempted&page_size=1" '.items[0]'` (or whatever action the source emits — re-grep `services/appointment_service.py` for the action string).
    Capture one screenshot per action under `${RUN_DIR}/phase-11-tech-mobile/secondary-actions/`.
17. **Maps "Remember my choice"** (Umbrella Task 6.6.3–6.6.6):
    - On appointment detail, click `[data-testid='get-directions-btn']` (verified at `AppointmentDetail.tsx:535`) → popover opens with two map options (Apple, Google) and a "Remember my choice" checkbox `[data-testid='remember-maps-choice-checkbox']` (verified at `MapsPickerPopover.tsx:153`); the row wrapper is `[data-testid='remember-maps-choice-row']` at `:145`.
    - Check the box, select Apple Maps. Close popover. Re-open → verify defaults to Apple. Screenshot `04-apple-remembered.png`.
    - Repeat with Google. Verify defaults to Google. Screenshot `05-google-remembered.png`.
    - Verify persistence via API: `GET /api/v1/staff/me` (or whichever endpoint exposes `preferred_maps_app`) returns `apple` or `google`. The `e2e/integration-full-happy-path.sh:67-74` exercises this — reuse that selector pattern.

#### Acceptance
- [ ] Tech lands on /tech, only sees own appointments.
- [ ] On-My-Way / Started / Complete state machine matches spec.
- [ ] Payment warning fires on path (a), skips on (b)(c)(d).
- [ ] Google Review job-button: no dedup. Appointment endpoint: 30-day dedup.
- [ ] Skip scenarios handled.
- [ ] PhoneOnlyGate enforced on non-phone viewport.
- [ ] All five AppointmentDetail secondary actions (notes, tags, photos, reschedule, mark-contacted) work and persist.
- [ ] `GET /api/v1/appointments/{id}/timeline` returns chronologically-sorted communication events; UI Communication section renders them.

#### Cleanup
- Carry the in-progress/completed appointment into P12 (payment).

#### Re-run criteria
- Requires fresh appointment per run, plus a tech credential.

#### Stale-reference watchlist
- `e2e/tech-companion-mobile.sh` and `scripts/e2e/test-mobile-staff.sh` — verify selectors against current `features/tech-mobile/` source; the recent `82bd5bb feat(tech-mobile): land phone-only Tech Companion schedule view` commit may have introduced new testids.

---

### Phase 12 — On-Site Payment Collection (Tech Mobile) 📱💳

**Goal**: From the tech-mobile job detail, collect payment via Tap-to-Pay (Stripe Terminal NFC) or Record Other Payment (cash/check/Venmo/Zelle); send receipt SMS/email.

**Prerequisites**: P0, P11 with an in-progress one-off job (no service agreement).

**Variant lane**: Tech mobile.

⚠️ **Per memory**: M2 hardware (Stripe Terminal physical reader) is shelved. Tap-to-Pay uses iPhone NFC via Stripe Terminal SDK. In a non-physical test environment (agent-browser), Tap-to-Pay can be **simulated** via Stripe Terminal test mode. Per memory `Stripe Payment Links via SMS — Architecture C live`, the primary card-payment flow now is Payment Links (P14), not Tap-to-Pay. **Verify which is currently active in dev**.

#### VERIFY (source check)
```bash
grep -n "tap-to-pay\|TapToPay\|stripe.*terminal\|Stripe Terminal" frontend/src
grep -n "@router\." src/grins_platform/api/v1/invoices.py | head -30
grep -n "collect_payment\|record_payment\|payment_method" src/grins_platform/services
grep -n "Payment Link\|payment_link\|send-link" src/grins_platform/api/v1/invoices.py
```

#### Steps

1. From P11's in-progress appointment, tap "Collect Payment". Screenshot `01-pay-options.png`.
2. **Path A — Pay with Card (Tap to Pay)**: if still wired in current source:
   - Enter amount, select method.
   - Stripe Terminal SDK simulation (use test card `4242 4242 4242 4242` via Terminal test mode if applicable).
   - Verify `payment_intents` API or invoice payment record updated.
   - Send receipt — choose SMS, then email; verify both delivered.
3. **Path B — Record Other Payment** (Cash/Check/Venmo/Zelle):
   - Select Cash, enter amount.
   - Save. Verify invoice record updated, `payment_method=cash` (or whichever).
   - Repeat for Check, Venmo, Zelle.
4. **Partial payments** (multi-tender): record $50 cash on a $200 invoice → verify status = `partial`. Add $150 Venmo → status = `paid`.
5. **Receipt content**: SMS receipt should include amount + last4 + invoice number; email receipt should include itemized breakdown.
6. **Path payment differentiation** (per `update2_instructions.md:893`):
   - Service-agreement job → "Covered by [Agreement]" with green checkmark, payment buttons hidden. (Already verified in P11.)
   - One-off no-invoice → both Create Invoice and Collect Payment visible.
   - One-off invoice-sent → invoice details + status badge + Collect Payment available.
   - One-off paid-on-site → "Payment collected — $X via [method]" with checkmark.

#### Full payment matrix (Umbrella Task 6.5 — every PaymentMethod enum value gets a flow)

| # | Method | Action | Expected | Screenshots |
|---|---|---|---|---|
| 4.1 | `cash` | Collect $100 cash on appointment | Confirmation card "Paid — $100 · cash"; receipt SMS to test phone; receipt email | `01-cash-collected.png`, `02-cash-confirmation-card.png`, `03-cash-receipt-sms.png`, `04-cash-receipt-email.png` |
| 4.2 | `check` | Collect $100 check w/ ref# 1234 | Card includes "Check #1234"; receipts fire | `05-check-with-ref.png`, `06-check-receipt.png` |
| 4.3 | `venmo` | Collect $50 Venmo | Card shows "Venmo"; receipts | `07-venmo.png` |
| 4.4 | `zelle` | Collect $50 Zelle | Card shows "Zelle"; receipts | `08-zelle.png` |
| 4.5 | `credit_card` (Stripe Payment Link) | Click "Send Payment Link" → simulate webhook `payment_intent.succeeded` via `sim/stripe_event.sh payment_intent.succeeded --add metadata.invoice_id=$INV` | Card shows "Credit card · Stripe"; webhook flips invoice→PAID. **Bug #16 regression** — `payment_method='stripe'` via `collect-payment` MUST NOT short-circuit to PAID before the webhook fires (`appointment_service.py:83` `STRIPE_DEFERRED_METHODS`). | `09-send-payment-link.png`, `10-stripe-paid-card.png` |
| 4.6 | Multi-tender | Collect $50 cash → status PARTIAL → collect $50 check → status PAID | Two timeline events; status transitions correctly | `11-partial.png`, `12-paid-after-second.png` |
| 4.7 | Refund | `sim/stripe_event.sh charge.refunded` | Status REFUNDED; timeline event added | `13-refund-event.png` |
| 4.8 | "Text receipt" CTA | Click on confirmation card → receipt SMS re-sent | Re-send works; second SMS row in `sent_messages` | `14-text-receipt-resent.png` |
| 4.9 | Timeline coverage | Open appointment timeline | Every payment from 4.1–4.7 surfaces as `PAYMENT_RECEIVED` event (Bug #15 regression — must NOT crash on missing icon kind, see `AppointmentCommunicationTimeline.tsx:45,55`) | `15-timeline-with-all-payments.png` |
| 4.10 | Distinct receipts | Stripe-link path | Stripe-hosted confirmation present + Grin's receipt distinct (no double-send) | `16-distinct-receipts.png` |

#### DB / API verification

```bash
# 4.1 Invoice state
api_q "/api/v1/invoices/$INV_ID" '{payment_method, paid_amount, status}'

# 4.6 Multi-tender accumulates
api_q "/api/v1/invoices/$INV_ID" '{paid_amount, status}'
# Expected after $50+$50 on $100: { "paid_amount": 100.00, "status": "paid" }

# 4.9 Timeline coverage
api_q "/api/v1/appointments/$APT_ID/timeline" \
  '[.events[] | select(.kind == "payment_received")] | length'

# Receipt SMS to allowlisted phone only
api_q "/api/v1/sent-messages?message_type=payment_receipt&limit=20" \
  '[.items[].recipient_phone] | unique'
# Expected: only +19527373312
```

#### Acceptance
- [ ] All 16 sub-cases produce expected screenshots and DB states.
- [ ] Bug #14 regression: cash/check/venmo/zelle do NOT crash (`appointment_service.py:2047, 2089` unpacks `**kwargs`; closed in `b53ac1f`).
- [ ] Bug #15 regression: timeline does NOT throw "Element type is invalid" on `payment_received` kind (closed in `f0a1e18`).
- [ ] Bug #16 regression: `payment_method='stripe'` does NOT short-circuit to PAID before webhook (`STRIPE_DEFERRED_METHODS` gate; closed in `f0a1e18`).
- [ ] Receipts arrive at allowlisted phone (`+19527373312`) and email (`kirillrakitinsecond@gmail.com`) only.

#### Cleanup
- N/A — payment records persist. Test invoices can be deleted in P24.
- Refund any test charges in Stripe test mode.

#### Re-run criteria
- Requires a one-off in-progress job (P11). Re-runnable per invoice.

#### Stale-reference watchlist
- Per memory, Architecture C (Payment Links over SMS) is the primary card-payment path. Tap-to-Pay status: confirm whether it's still wired or has been replaced. If replaced, document path A as deferred.

---

### Phase 13 — Invoices Tab — List, Filters, Mass Notify, Lien Queue

**Goal**: Verify invoice list, 9-axis filtering, status colors, mass notifications (Past Due, Due Soon), Lien Review Queue.

**Prerequisites**: P0; ideally invoices exist from P4/P12 or seed.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/invoices.py | head -30
grep -n "Mass Notify\|mass-notify\|massNotify\|bulk_notify" frontend/src/features/invoices
grep -n "Lien Review\|lien-review\|lienReview\|lien_eligible" src/grins_platform
grep -n "lien_days_past_due\|lien_min_amount" src/grins_platform/models
```

#### Steps

1. Login → `/invoices`. Screenshot list `01-invoices.png`.
2. **Status colors**: ensure Green (Complete), Yellow (Pending), Red (Past Due) render per spec.
3. **Filter axes** (each individually then in combinations):
   - Date range (created / due / paid)
   - Status
   - Customer
   - Job
   - Amount range
   - Payment type (multi-select: Credit Card, Cash, Check, ACH, Venmo, Zelle, Other; legacy `stripe` row should display but not be selectable in new pickers per spec)
   - Days until due
   - Days past due
   - Invoice number exact match
3a. **Server-side `days_until_due` / `days_past_due` fields** (per `bughunt/2026-04-16-medium-bugs-plan.md` M-12). VERIFY: `grep -n "days_until_due\|days_past_due" src/grins_platform/schemas/invoice.py src/grins_platform/services/invoice_service.py`. Steps: pick an unpaid invoice with a known `due_date`, call `api_q "/api/v1/invoices/$INV_ID" '.days_until_due, .days_past_due'` → assert exactly one is non-null per state (positive `days_until_due` if due in future; positive `days_past_due` if past due; both zero on the due date). Confirm filter axes "Days until due" / "Days past due" filter against the same server-computed fields, not client-side math.
4. **Filter chips**: confirm chips render above the list with ✕ buttons; clear-all works; URL persists state.
5. **Mass Notify — Past Due**: filter to past-due → click Mass Notify panel → Past Due → confirm modal shows count and template preview → send. Verify SMS rows in `sent_messages` for each affected customer. (🟡 **HUMAN** verification optional but encouraged.)
6. **Mass Notify — Due Soon**: separate config window, same flow.
7. **Lien Review Queue** (separate from Mass Notify):
   - Verify queue subview on Invoices tab.
   - Default thresholds: 60+ days past due AND $500+ owed (per `update2_instructions.md:971`); confirm against `business_settings.lien_days_past_due` / `lien_min_amount`.
   - Pick a flagged row, click `Send Notice` → SMS sent per record.
   - Click `Skip` → row marked skipped without SMS.
   - Verify `Mark Lien Filed` advances state.
8. **Invoice detail**: open one → verify customer/job links, line items, status history, "Send" / "Reminder" / "Lien Warning" / "Lien Filed" actions where applicable.
9. **Generate invoice from job**: `POST /api/v1/invoices/generate/{job_id}` → verify pre-filled invoice created. Test from UI too.

#### Acceptance
- [ ] All 9 filter axes work and AND-combine.
- [ ] Mass Notify Past Due + Due Soon dispatch SMS.
- [ ] Lien Review Queue is separate from Mass Notify and per-row gated.

#### Cleanup
- Mark any test-only sent notices as such in audit log notes.

---

### Phase 14 — Stripe Payment Links via SMS (Architecture C)

**Goal**: Every invoice gets a hosted Stripe Payment Link auto-generated on creation; admin can SMS the link; webhook reconciliation flips invoice to Paid.

**Prerequisites**: P0, P13 invoice exists.

**Variant lane**: Admin (send link) + customer (Stripe-hosted page).

**Bug status (verified 2026-05-02 — see Bug Status Reference at top of plan)**:
- Bug 1 (multi-head Alembic crash) — **CLOSED** in `102df83`; CI guard in `01cc14a`.
- Bug 2 (email-allowlist 500 → 422) — **CLOSED** in `01cc14a`. `invoice_service.py:1038` catches `EmailRecipientNotAllowedError`; test `tests/unit/test_send_payment_link_email_allowlist.py`.
- Bug 3 (SMS soft-fail transparency) — **CLOSED** in `01cc14a`. `invoice_service.py:961` adds `attempted_channels` + `sms_failure_reason`; FE surfaces in `PaymentCollector.test.tsx`, `InvoiceDetail.test.tsx`.
- Bug 4 (CORS on 5xx) — **CLOSED**. `app.py:230` `_catch_unhandled_exceptions` middleware + `:958` `unhandled_exception_handler`; test `tests/integration/test_cors_on_5xx.py`.
- Bug 5 (seeder reuse hygiene) — **CLOSED**. `scripts/seed_e2e_payment_links.py:59-67` PUTs email/opt-ins on reuse.
- Bug 6 (wrong appointment clicked) — **CLOSED**. `e2e/payment-links-flow.sh:69-84` now requires `APPOINTMENT_ID` and uses `[data-testid='appt-card-${APPOINTMENT_ID}']`.
- Bug 7 (Railway `RAILPACK` cosmetic drift) — **NEEDS RUNTIME CHECK**. Documentation landed at `docs/payments-runbook.md:187-195`; the actual dashboard pin is operator-side.

The phase still re-runs each repro to confirm, but the expected outcome is now PASS for Bugs 1–6 and DEFERRED-cosmetic for Bug 7.

#### VERIFY (source check)
```bash
grep -n "send-link\|send_payment_link\|payment_link" src/grins_platform/api/v1/invoices.py
grep -n "@router\." src/grins_platform/api/v1/webhooks.py
grep -n "metadata.invoice_id\|invoice_id.*metadata" src/grins_platform/services/stripe
grep -n "checkout.session.completed\|charge.refunded\|charge.dispute.created" src/grins_platform/services
```

#### Steps

1. Login → open an invoice detail → verify Stripe Payment Link rendered/copyable. Screenshot.
2. **Send Payment Link via SMS**: click `Send Payment Link` button → expect SMS sent to customer with hosted link.
3. 🟡 **HUMAN**: customer phone receives link. Optionally, the human opens the link → completes payment with Stripe test card `4242 4242 4242 4242` exp `12/30` CVC `123`.
4. **Webhook reconciliation**: verify `POST /api/v1/webhooks/stripe` receives `checkout.session.completed`. Verify `metadata.invoice_id` correctly identifies the invoice and flips it to `paid`.
5. **Refund**: in Stripe dashboard test mode, refund the test charge → verify webhook `charge.refunded` flips invoice to `refunded`.
6. **Dispute**: simulate dispute via Stripe test (use `4000 0000 0000 0259` for dispute trigger) → verify `charge.dispute.created` reflected on invoice. VERIFY: `grep -n "charge.dispute.created" src/grins_platform/api/v1/webhooks.py`. Trigger via `e2e/master-plan/sim/stripe_event.sh charge.dispute.created` (HMAC-signed Stripe trigger). Assert `api_q "/api/v1/invoices/$INV_ID" '.status'` flips to `disputed` (or whatever the source enum is). Assert no auto-customer-notification SMS goes out (prevents reply-storm). Assert dashboard alert created if `AlertType.INVOICE_DISPUTED` or equivalent is wired (out-of-scope if not).
7. **Email allowlist guard** (Bug 2 regression): attempt `send-link` with email channel and a non-allowlisted email → expect 422, NOT 500.
8. **SMS rate-limit transparency** (Bug 3 regression). VERIFY: `grep -n "attempted_channels\|sms_failure_reason" src/grins_platform/services/invoice_service.py src/grins_platform/schemas/invoice.py`. Steps: force a CallRail rate-limit (or invalid recipient) on the SMS channel by sending to a non-allowlisted phone in dev → assert response body includes `attempted_channels: ["sms", "email"]` (or the non-empty subset that was attempted) AND `sms_failure_reason` is non-null. The UI should surface both attempts (per `PaymentCollector.test.tsx`, `InvoiceDetail.test.tsx`) — capture screenshot of the toast/banner showing both channels.
9. **5xx CORS** (Bug 4 regression): force a 500 from this endpoint → verify CORS headers present.
10. **Seeder hygiene** (Bug 5 regression): if the test seeder is rerun, verify customer email/opt-ins refresh per the test invariant.
11. **Click selector** (Bug 6 regression): if reusing `e2e/payment-links-flow.sh` patterns, ensure tests target by appointment id, not first-of-class.

#### Acceptance
- [ ] Payment Link sent via SMS, clickable.
- [ ] Webhook reconciles to paid via `metadata.invoice_id`.
- [ ] Refund + dispute webhooks update invoice state.
- [ ] All 6 prior bugs verified resolved (or status documented).

#### Cleanup
- Refund any test charges in Stripe; Dispute can be left as-is in test mode.

#### Re-run criteria
- Requires invoice from P13. Has HUMAN step (link-click + card entry). Re-runnable per invoice.

#### Stale-reference watchlist
- `bughunt/2026-04-28-stripe-payment-links-e2e-bugs.md` lists screenshots in `e2e-screenshots/payment-links-architecture-c/00..11-*.png`. New screenshots from this run go to `${RUN_DIR}/phase-14-payment-links/`.

---

### Phase 15 — Service Packages Onboarding (Subscription Customer)

**Goal**: Verify the public onboarding form → preferred-week pickers → Stripe checkout → webhook → Customer + Service Agreement + Jobs created with correct week-of preferences.

**Prerequisites**: P0.

**Variant lane**: Public (onboarding) → Admin (verification).

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/onboarding.py
grep -n "@router\." src/grins_platform/api/v1/checkout.py
grep -n "service_week_preferences\|week_pickers" frontend/src
grep -n "service_offerings.*tier\|tier.*service_offerings" src/grins_platform/models
```

This phase mirrors `Testing Procedure/10-customer-landing-flow.md` Path L (Service Packages purchase, 7 tiers + Stripe + onboarding 7-week-pickers) and Path Q (Free Quote lead intake, 5 consent matrix scenarios).

#### Steps

1. Open public onboarding form on marketing dev URL.
2. **Tier selection** — test each tier (Essential / Professional / Premium / Winterization residential + commercial variants per Path L). Screenshot each.
3. **Week pickers**: for the package's services, pick a preferred week per service (some packages have 7 pickers). Screenshot.
4. **Stripe checkout**: complete with test card `4242...`. Screenshot Stripe-hosted page.
5. **Webhook fires**: verify `customer.subscription.created` (or whichever) propagates.
6. **System creates**:
   - Customer (verify via API).
   - Service Agreement with `service_week_preferences` stored as structured JSON.
   - One Job per service in the package, each with Week Of = customer's selected week (Monday-Sunday range), service type matching, status=`to_be_scheduled`.
7. **Prepaid + Subscription badges**: verify on Jobs list, Job detail, Schedule calendar cards.
8. **Default-week fallback**: separately, simulate webhook with no preferences → verify default calendar-month ranges per service type (per `update2_instructions.md:1000`).
9. **Consent matrix** (Path Q — 5 scenarios per `Testing Procedure/10-customer-landing-flow.md`): test each combination of SMS opt-in / email opt-in / terms accepted.
10. **Dedup on onboarding**: submit same email/phone twice → verify Tier 1 dedup guard.

#### Acceptance
- [ ] All tiers checkout-complete.
- [ ] Each tier produces correct Customer + Agreement + Jobs trio.
- [ ] Week-Of populates from preferences when set; falls back when not.
- [ ] Consent matrix all 5 scenarios behave correctly.
- [ ] Dedup guard fires.

#### Cleanup
- Cancel test subscriptions in Stripe to avoid recurring charges; soft-delete test customers.

#### Re-run criteria
- Each tier should be tested per release. Cheap to repeat since Stripe test mode is free.

---

### Phase 16 — Contract Renewals — Annual Renewal Review 🕐

**Goal**: When a subscription auto-renews via Stripe `invoice.paid`, system creates a Renewal Proposal (NOT direct jobs); admin reviews, approves/modifies/rejects per-job or in bulk.

**Prerequisites**: P0, P15 customer with subscription.

**Variant lane**: Admin desktop. Webhook simulation (no real time-travel needed since we can fire the webhook directly).

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/contract_renewals.py
grep -n "renewal_proposal\|RenewalProposal" src/grins_platform/models
grep -n "invoice.paid\|billing_reason.*subscription" src/grins_platform/services
```

#### Steps

1. **Trigger renewal** via Stripe test webhook simulation:
   - Use `stripe trigger invoice.paid` with `subscription_cycle` billing reason on a P15 subscription.
   - Verify `POST /api/v1/webhooks/stripe` receives event and creates `renewal_proposal`.
2. **Dashboard alert**: navigate to `/dashboard` → expect "1 contract renewal ready for review: [customer]" alert. Click → verify navigation to `/contract-renewals` (filtered to that customer).
3. **Renewal page**: `/contract-renewals` → verify columns (Customer, Agreement, Proposed Job Count, Created Date, Status, Actions). Screenshot.
4. **Click into proposal**: verify proposed jobs listed with rolled-forward dates. Verify date-rolling logic per `update2_instructions.md:1062`:
   - Monday + 1 year: snap to nearest preceding Monday.
   - Feb 29 leap-day: rolls to Feb 28.
5. **Per-job actions**:
   - Approve one → verify real Job created at the proposed dates.
   - Reject one → no Job created.
   - Modify one (change Week Of via week picker, add admin notes) → approve → verify Job created at modified dates.
6. **Bulk Approve All**: separate proposal → click → verify all jobs created.
7. **Bulk Reject All**: separate proposal → click → verify status=`rejected`, no jobs.
8. **Partial approval**: mix of approves/rejects → verify proposal status = `partially_approved`.
9. **`billing_reason` gate** (per `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-4): verify `subscription_update` events do NOT trigger renewal proposal — only `subscription_cycle`.

#### Acceptance
- [ ] Webhook → proposal (not direct jobs).
- [ ] Date rolling per spec.
- [ ] Per-job and bulk actions all functional.
- [ ] `subscription_update` does not trigger renewal.

#### Cleanup
- Reject any leftover test proposals.

---

### Phase 17 — Duplicate Customer Management

**Goal**: Verify nightly background detection job, Real-Time duplicate warning on customer create / lead conversion, side-by-side merge modal, merge rules, blockers (active Stripe subscription).

**Prerequisites**: P0.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/customers.py | grep -i "duplicate\|merge"
grep -n "duplicate_pairs\|duplicateScoring\|duplicate_score" src/grins_platform
grep -n "merged_into_customer_id\|MergeBlockerError" src/grins_platform
ls src/grins_platform/services/duplicate*  2>/dev/null
```

#### Steps

1. **Setup**: create two customers with same phone number (force via API to bypass UI guard, or test the UI guard in step 2 first).
2. **Real-time warning**:
   - From `/customers` `+ Add Customer` → fill in a phone matching an existing customer → expect inline "Possible match found" + "Use existing customer" button. Screenshot `01-realtime-warning.png`.
3. **Lead conversion conflict** (per `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-6): the legacy single-button "Convert Lead" path; verify against the actual current behavior — `update2_instructions.md:574` says new `Move to Jobs`/`Move to Sales` paths silently link instead.
4. **Run nightly detection** (or trigger manually):
   - If a manual trigger endpoint exists, call it; otherwise wait until 1:30 AM or simulate.
   - Verify pairs created in `customer_duplicate_pairs` (or whichever table).
5. **Score calculation** (per `update2_instructions.md:1077`): force a pair with all signals matching → verify score = 100; force partial → verify weighted sum.
6. **Review queue UI**:
   - `/customers` → click `Review Duplicates` button (count badge). Screenshot `02-queue.png`.
   - Click a pair → side-by-side modal opens. Screenshot `03-merge-modal.png`.
7. **Merge modal**:
   - Each conflicting field has radio buttons; primary's value pre-selected; non-empty wins by default.
   - Choose mixed values, click Merge → verify all related records (jobs, invoices, notes, communications, agreements, properties) reassigned to surviving customer.
   - Verify duplicate soft-deleted with `merged_into_customer_id`.
   - Verify audit log entry.
8. **Blocker — both have active Stripe subs**: try to merge → expect 409 + clear error message.
9. **Multiple-pair handling**: queue with several pairs sorted by score descending.

#### Acceptance
- [ ] Real-time warning fires on Tier-1 (phone or email) match.
- [ ] Nightly job populates queue.
- [ ] Score weighted per spec.
- [ ] Merge reassigns all related records.
- [ ] Sub-blocker enforced.

#### Cleanup
- Un-merge or delete test customers.

---

### Phase 18 — AI Scheduling — Resource Timeline, Chat, Briefing, Generate, Alerts

**Goal**: Exercise AI-powered scheduling features.

**Prerequisites**: P0.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/ai_scheduling.py
grep -n "@router\." src/grins_platform/api/v1/scheduling_alerts.py
grep -n "@router\." src/grins_platform/api/v1/ai.py | head -20
grep -n "ResourceTimeline\|resource-timeline" frontend/src/features/schedule
grep -n "Generate Schedule\|schedule/generate" frontend/src/pages
```

#### Steps

1. Login → `/schedule/generate` → screenshot.
2. **Generate schedule**: click → verify Timefold optimization runs, jobs assigned to staff/dates/times. Screenshot.
3. **Preview / Apply / Reoptimize / Emergency-insert**: each via `POST /api/v1/schedule/{preview,apply,reoptimize,emergency}`.
4. **Explain schedule / Explain unassigned**: click → verify natural-language reasoning rendered.
5. **Parse natural-language constraints**: type "no jobs Monday morning" → verify constraints parsed.
6. **AI Chat** (`/api/v1/ai/chat`): query "How many overdue invoices?" → verify reasonable answer. Verify `ai_audit_log` row.
7. **Morning briefing**: trigger via dashboard or API → verify summary generated.
8. **Resource Timeline View** (per `bughunt/2026-04-30-resource-timeline-view-deep-dive.md`, `bughunt/2026-04-30-resource-timeline-loading-and-capacity-bugs.md`, and `.agents/plans/fix-resource-timeline-loading-and-capacity-bugs.md` recent commit `4997a61 fix(schedule): resource-timeline 0% capacity + permanent Loading…`):
   - Open the resource timeline view → verify it loads (NOT permanent "Loading…" — that bug is fixed per the commit). Wait `--load networkidle` then assert that no element with text "Loading…" is present after 5s (`agent-browser eval "Array.from(document.querySelectorAll('*')).some(el => el.textContent.trim() === 'Loading…')"` → false).
   - Verify capacity calculation per staff per day is non-zero (the 0% capacity bug is fixed). VERIFY: `grep -n "utilization_pct" src/grins_platform/api/v1/schedule.py src/grins_platform/schemas/schedule_generation.py src/grins_platform/services/schedule_generation_service.py`; selector verified at `frontend/src/features/schedule/components/ResourceTimelineView/CapacityFooter.tsx:19,33` (`[data-testid='capacity-${date}']` per-day) and `frontend/src/features/schedule/components/CapacityHeatMap.tsx:36` (`[data-testid='capacity-cell-${day.date}']` heat-map alternative). Hit `api_q "/api/v1/schedule/capacity?date_from=$TODAY&date_to=$TODAY" '.items[0].utilization_pct'` → assert integer 0–100. Render side: locate the cell via `agent-browser get text "[data-testid='capacity-${TODAY}']"` → the cell renders the rounded `pct%` (per `CapacityFooter.tsx:43`); assert the rendered integer matches `Math.round(api_response_pct)` within 1pt. Capture `08a-utilization-rendered.png`. The cell is a slate skeleton (`animate-pulse`) only when capacity is loading (`CapacityFooter.tsx:20`); assert no skeleton class on the cell after `networkidle`.
   - **Cache invalidation on staff reassignment** (per `.agents/plans/schedule-resource-timeline-view.md`, `.agents/plans/fix-resource-timeline-loading-and-capacity-bugs.md`). Reassign one of the appointments to a different tech via drag-drop or `useReassignAppointment` hook. Within 1s, the capacity bars for both the source tech and the destination tech must update (utilization_pct changes). Capture before+after screenshots `08b-before-reassign.png`, `08c-after-reassign.png`. Without manual reload.
9. **Scheduling alerts** (`/api/v1/scheduling-alerts`): verify alert generation for capacity breach, conflicts, etc.
10. **Conflict resolution** (`/api/v1/conflict-resolution`): induce a conflict → verify endpoint returns options.
11. **Staff reassignment** (`/api/v1/staff-reassignment`): test endpoint.

#### Acceptance
- [ ] Generate produces a viable schedule.
- [ ] Resource timeline loads with non-zero capacities.
- [ ] AI chat returns coherent answers.
- [ ] `utilization_pct` rendered in capacity bar matches API response within 1pt.
- [ ] Reassigning an appointment updates capacity bars for both source and destination techs within 1s without manual reload.

#### Cleanup
- Discard any preview schedules; revert any apply that was test-only.

#### Stale-reference watchlist
- The recent fix `4997a61` claims resource-timeline loading + 0% capacity bugs are resolved. Verify by re-running the bughunt scenarios in `2026-04-30-resource-timeline-view-deep-dive.md`.

---

### Phase 19 — Dashboard — Alerts, Metrics, Navigation Routing

**Goal**: Verify dashboard widgets, alert click-through (single-record → detail; multi-record → filtered list with amber highlight via URL `?highlight=`).

**Prerequisites**: P0; data from earlier phases makes alerts more meaningful.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/dashboard.py
grep -n "highlight=\|?highlight" frontend/src
grep -n "Morning Briefing\|morning-briefing" frontend/src
```

#### Steps

1. Login → `/dashboard`. Screenshot `01-dashboard.png`.
2. Verify: Morning Briefing, Metrics Cards, Job Status Grid, Today's Schedule, Invoice Widgets, Quick Actions, Recent Activity, Alerts.
3. **Single-record alert**: click an alert with count=1 (e.g., "1 new job came in") → verify navigation directly to that record's detail page.
4. **Multi-record alert**: click an alert with count>1 (e.g., "3 invoices past due") → verify navigation to filtered list with `?highlight=<id>` URLs; amber pulse for ~3 seconds. Screenshot `02-highlighted-list.png`.
5. **Persistent highlight**: refresh the filtered URL → verify highlight still triggers (URL-encoded).
6. **No Estimates / Leads sections** (per `update2_instructions.md:81`): verify dashboard does NOT have dedicated sections for those — they live in Sales / Leads tabs.
7. **Sidebar counters**: verify counts on Leads, Sales, Jobs, Invoices match API counts. Per `bughunt/...customer-lifecycle-deep-dive.md` E-BUG-J, sidebar invalidation after actions has been tested — re-verify.
8. **Today's Schedule**: matches `/schedule` for today's date.
9. **Full `AlertType` enumeration coverage** (per `gap-14-dashboard-alert-coverage.md`). VERIFY: `grep -nA20 "class AlertType" src/grins_platform/models/enums.py` should resolve at `:618` and list `CUSTOMER_CANCELLED_APPOINTMENT`, `CONFIRMATION_NO_REPLY`, `LATE_RESCHEDULE_ATTEMPT`, `CUSTOMER_RECONSIDER_CANCELLATION`, `INFORMAL_OPT_OUT`, `WEBHOOK_REDIS_FALLBACK`, `WEBHOOK_SIGNATURE_FLOOD`, `WEBHOOK_AUTOREPLY_CIRCUIT_OPEN`, `PENDING_RESCHEDULE_REQUEST`, `UNRECOGNIZED_CONFIRMATION_REPLY`, `ORPHAN_INBOUND`. For each, drive the trigger and verify the dashboard shows a card / row:
    - `CUSTOMER_CANCELLED_APPOINTMENT` — emitted from `notification_service.py:1285` when customer replies C.
    - `CONFIRMATION_NO_REPLY` — emitted from `background_jobs.py:889` after the nightly no-reply scan.
    - `INFORMAL_OPT_OUT` — emitted from `sms_service.py:1188` (drive via P9 E8b).
    - `PENDING_RESCHEDULE_REQUEST` — emitted from `job_confirmation_service.py:629` when customer replies R.
    - `UNRECOGNIZED_CONFIRMATION_REPLY` — emitted from `job_confirmation_service.py:1192` on anything-else replies.
    - `ORPHAN_INBOUND` — emitted from `sms_service.py:1706` when an inbound has no resolvable thread.
    - Webhook security types — covered indirectly by P21 step 9 (replay/dedup); spot-check that they appear on dashboard if simulated.
    - `LATE_RESCHEDULE_ATTEMPT`, `CUSTOMER_RECONSIDER_CANCELLATION` — drive by attempting reschedule on EN_ROUTE/IN_PROGRESS appointment (P10 step 7) and post-cancel reconsideration (P9 E11).
    For each emitted type: query `api_q "/api/v1/alerts?type=$TYPE&limit=1" '.items[0].type'` → assert equal; then on `/dashboard` confirm a clickable card surfaces it. Screenshot `03-alerts-grid.png` after at least 6 distinct types are present.
10. **Filters / pagination on `/api/v1/alerts`**. VERIFY: `grep -n "@router\.\|alert_type.*Query\|severity.*Query\|offset.*Query" src/grins_platform/api/v1/alerts.py` should resolve at `:46-105` (`acknowledged`, `type`, `alert_type` repeatable, `severity` repeatable, `since`, `sort`, `offset`, `limit`). Response shape is `{items, total}` (NOT cursor-based). Steps:
    - Single-type filter: `api_q "/api/v1/alerts?type=informal_opt_out&acknowledged=false&limit=10" '.items|length, .total'` → assert filter applied.
    - Repeatable filter: `api_q "/api/v1/alerts?alert_type=pending_reschedule_request&alert_type=informal_opt_out&limit=10" '.items|map(.type)|unique'` → assert array contains both types only.
    - Severity filter: `api_q "/api/v1/alerts?severity=warning&severity=error&limit=5" '.items|map(.severity)|unique'` → assert subset of `["warning","error"]`.
    - Sort: request `sort=created_at_asc` → assert `.items[0].created_at <= .items[-1].created_at`; flip to `created_at_desc` → assert reverse.
    - Pagination: `?offset=0&limit=5` then `?offset=5&limit=5` → assert non-overlapping `.id` sets.
    - Acknowledged history: `?acknowledged=true&since=$ISO` → assert all returned rows have `acknowledged_at >= since`.

#### Acceptance
- [ ] All widgets populate.
- [ ] Single-record click → detail page.
- [ ] Multi-record click → filtered list + amber highlight via URL.
- [ ] Sidebar counters in sync.
- [ ] All 11 `AlertType` enum values are emit-tested (or explicitly skipped with reason); at least 6 surface on dashboard simultaneously.
- [ ] `/api/v1/alerts` filter axes (`type`, `acknowledged`, severity if present) and cursor pagination work.

---

### Phase 20 — Communications & SMS Inbox

**Goal**: Verify sent messages tab, delivery statuses, inbound replies surface correctly, manual SMS triggers, opt-out queue.

**Prerequisites**: P0; messages from earlier phases populate this.

**Variant lane**: Admin desktop.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/communications.py
grep -n "@router\." src/grins_platform/api/v1/sent_messages.py
grep -n "@router\." src/grins_platform/api/v1/inbox.py
grep -n "informal-opt-out\|InformalOptOut" frontend/src/pages
```

#### Steps

1. Login → `/communications` → snapshot. Screenshot.
2. Verify Sent Messages tab populates with rows from prior phases.
3. Filter by `delivery_status` (sent/delivered/failed/queued); verify badges per spec.
4. **Inbound messages**: verify replies from P9 visible (NOT just outbound).
5. **Per-customer detail** (`/customers/{id}` Messages tab): verify both inbound + outbound shown.
6. **Manual SMS Send**: trigger via UI → expect template picker, merge fields, segment count (GSM-7 / UCS-2). Verify segment counter accurate.
7. **Campaign wizard** (3-step Audience → Compose → Review): build a small test campaign targeting only the seed customer; preview; send; verify campaign worker dispatches.
8. **Opt-out queue** (`/alerts/informal-opt-out`): if any informal opt-outs detected (e.g., "stop calling me"), verify they surface here for admin review.
9. **Unified Inbox endpoint** (per `gap-16-unified-sms-inbox.md`). VERIFY: `grep -n "router = APIRouter(prefix=\"/inbox\"" src/grins_platform/api/v1/inbox.py` resolves at `:28`. Schema (per `src/grins_platform/schemas/inbox.py:97-108`): `{items: list[InboxItem], next_cursor: str | None, has_more: bool}`. Each `InboxItem` has `id`, `source_table` (one of `job_confirmation_responses`/`reschedule_requests`/`campaign_responses`/`communications`), `triage_status`, `received_at`, `body`, `from_phone`. Steps: hit each triage filter and assert behavior:
    - `api_q "/api/v1/inbox?triage=all&limit=50" '.items|length, .has_more, .next_cursor'` → expect items.
    - `?triage=needs_triage` → only items requiring admin attention.
    - `?triage=orphans` → only inbound replies that couldn't be routed.
    - `?triage=unrecognized` → only `UNRECOGNIZED_CONFIRMATION_REPLY` events.
    - `?triage=opt_outs` → only opt-out events (hard STOP + informal).
    - `?triage=archived` → only resolved/archived events.
    Cursor pagination: take `next_cursor` from page 1 → request `?cursor=...` → assert distinct items, no overlap. Render side: the inbox card lives at `[data-testid='inbox-queue']` (per `frontend/src/features/schedule/components/InboxQueue.tsx:124,145,175`) on `/schedule`; the filter chips are `[data-testid='inbox-filter-${key}']` (`:209`); rows are `[data-testid='inbox-row-${item.id}']` (`:302`); load-more is `[data-testid='load-more-inbox-btn']` (`:267`). Click each filter chip and assert the visible rows match the `triage` filter requested. Screenshot `09-inbox-card.png` and one per filter.
10. **Customer conversation endpoint** (per `gap-13-customer-messages-outbound-only.md`). VERIFY: `grep -n "/{customer_id}/conversation\|CustomerConversationService" src/grins_platform/api/v1/customers.py` resolves at `:1823`. Response shape (per the handler at `:1873-1876`): `{items, next_cursor, has_more}`. Steps: against the seeded Kirill customer who has inbound + outbound history from P9, hit `api_q "/api/v1/customers/$KIRILL_CUSTOMER_ID/conversation?limit=50" '.items|length, .has_more, .next_cursor'`. Assert items merged across `sent_messages`, `job_confirmation_responses`, `campaign_responses`, and `communications` (the per-item discriminator should make this checkable — re-grep `services/customer_conversation_service.py` for the discriminator field name). Newest-first per the handler description; assert `.items[0].occurred_at >= .items[-1].occurred_at` (or whatever the timestamp field is — re-grep the schema). Render side: open `/customers/$KIRILL_CUSTOMER_ID` → Messages tab → assert paired in/out timeline rendered with `[data-testid='queue-last-updated']` header (`CustomerMessages.tsx:90`). Screenshot `10-customer-conversation.png`.
11. **Queue freshness via `refetchInterval`** (per `gap-15-queue-freshness-and-realtime.md`). VERIFY: `grep -n "refetchInterval" frontend/src/features/schedule/hooks/useRescheduleRequests.ts frontend/src/features/schedule/hooks/useNoReplyReview.ts frontend/src/features/schedule/hooks/useInbox.ts frontend/src/features/schedule/hooks/useAppointments.ts` resolves at `useRescheduleRequests.ts:20` (30_000), `useNoReplyReview.ts:35` (60_000), `useInbox.ts:43` (60_000), `useAppointments.ts:45` (60_000), each followed by `refetchIntervalInBackground: false`. Steps: open `/schedule`, observe the four queue cards. Use `agent-browser eval "performance.getEntriesByType('resource').filter(r => r.name.includes('/api/v1/')).map(r => ({name:r.name,startTime:r.startTime}))"` to capture network calls. Wait 65s. Re-eval; assert that `/api/v1/schedule/reschedule-requests` was called at least 2× (30s interval), `/api/v1/no-reply-review` and `/api/v1/inbox` at least 1× (60s). Verify `refetchIntervalInBackground: false` honored: simulate tab background via `agent-browser eval "Object.defineProperty(document,'visibilityState',{value:'hidden',configurable:true}); document.dispatchEvent(new Event('visibilitychange'))"` — wait 35s — assert no additional reschedule-requests calls.
12. **`QueueFreshnessHeader` "last-updated" affordance** (per the same gap). VERIFY: `grep -n "queue-last-updated\|queue-refresh-btn" frontend/src/shared/components/QueueFreshnessHeader.tsx` resolves at `:67` and `:79`. Steps: confirm `[data-testid='queue-last-updated']` renders a "Last updated …" text next to each queue card; the refresh icon is `[data-testid='queue-refresh-btn']` (the testId can be overridden per consumer per `:79` `testId ?? 'queue-refresh-btn'`). Click the refresh icon → capture `performance.getEntriesByType('resource')` before+after → assert a network call fires within 2s; the "last updated" text resets.

#### Acceptance
- [ ] Sent Messages tab shows accurate delivery statuses.
- [ ] Inbound replies surface in customer detail Messages tab.
- [ ] Manual SMS + campaign send work.
- [ ] Opt-out queue exists or gap documented.
- [ ] `GET /api/v1/inbox` returns each triage bucket correctly; cursor pagination works; fourth queue card visible on `/schedule`.
- [ ] `GET /api/v1/customers/{id}/conversation` merges 4 source tables, newest-first; Messages tab renders paired in/out.
- [ ] All four polled queues (`reschedule-requests` 30s, `no-reply-review` 60s, `inbox` 60s, `appointments` 60s) refetch on interval and pause when tab is backgrounded.
- [ ] `QueueFreshnessHeader` shows last-updated time and offers a manual refresh.

---

### Phase 21 — Cross-Cutting Smoke (Security, Audit, Webhooks, Rate Limit)

**Goal**: Final cross-cutting checks not covered by feature phases.

**Prerequisites**: P0.

#### VERIFY (source check)
```bash
grep -n "@router\." src/grins_platform/api/v1/audit.py
grep -n "@router\." src/grins_platform/api/v1/notifications.py
grep -n "@router\." src/grins_platform/api/v1/alerts.py
grep -n "@router\." src/grins_platform/api/v1/settings.py
grep -n "@router\." src/grins_platform/api/v1/analytics.py
ls src/grins_platform/middleware/
```

#### Steps

1. **Audit log endpoints**: verify `GET /api/v1/audit-log` returns recent entries; filter by entity type.
2. **Notifications**: verify in-app notifications API.
3. **Alerts**: verify dashboard alerts API independent of UI.
4. **Settings**: verify business settings (lien thresholds, business phone, GOOGLE_REVIEW_URL) are admin-editable.
5. **Analytics**: verify metrics endpoints.
6. **CSRF middleware**: verify CSRF protection on POST endpoints (where enforced — webhooks excluded).
7. **Request size limit**: send a payload >limit → expect 413.
8. **Webhook security** (paths and response codes verified against current source):
   - CallRail HMAC: `POST /api/v1/webhooks/callrail/inbound` (callrail_webhooks.py:211) — invalid HMAC → 403 (`callrail_webhooks.py:243-264`).
   - Stripe signature: `POST /api/v1/webhooks/stripe` (webhooks.py:1386) — invalid → 401 via `stripe.SignatureVerificationError`.
   - SignWell `X-Signwell-Signature`: `POST /api/v1/webhooks/signwell` (signwell_webhooks.py:48) — invalid → 401.
   - Resend HMAC: `POST /api/v1/webhooks/resend` (resend_webhooks.py:65) — invalid → 401 via `verify_resend_webhook_signature`.
9. **Webhook dedup** (per `.agents/plans/webhook-security-and-dedup.md`): replay an event → expect dedup guard.
10. **Voice / Chat public endpoints** (`/api/v1/voice`, `/api/v1/chat`): verify they require valid auth tokens or are correctly public per their requirement.
11. **Sheet submissions**: if used, verify `/api/v1/sheet-submissions` lifecycle.
12. **Stripe Terminal uninstall verification** (Umbrella Task 6.6.7–6.6.9 — Phase 5 polish): the legacy Stripe Terminal hardware path is fully removed.
    - `curl -s -o /dev/null -w '%{http_code}' "$API_BASE/api/v1/stripe-terminal/connection-token"` → expect **404**.
    - `grep -n "stripe_terminal" src/grins_platform/api/v1/router.py` → expect **no matches** (import + include_router removed).
    - `ls src/grins_platform/api/v1/stripe_terminal.py 2>/dev/null` → expect **no such file**.
    - `ls src/grins_platform/services/stripe_terminal*.py 2>/dev/null` → expect **no such files**.
    - `ls src/grins_platform/tests/unit/test_stripe_terminal.py 2>/dev/null` → expect **no such file**.
    - Per memory `Stripe Payment Links via SMS — Architecture C live (2026-04-28)`: M2 hardware shelved; Tap-to-Pay path replaced by Payment Links via SMS.
13. **Static `pricelist.md` retired** (Umbrella Task 6.6 / 5.4): if `pricelist.md` exists at repo root, it should be a stub or have a deprecation header pointing to the dynamic `/invoices?tab=pricelist`. Verify `cat pricelist.md | head -3` for the deprecation marker.
14. **Webhook empty-`last_name` resilience** (per `.agents/plans/webhook-empty-last-name-fix.md` and `production-bugs/2026-04-26-webhook-empty-last-name-orphaned-agreements.md`). VERIFY: `grep -n "last_name" src/grins_platform/models/customer.py src/grins_platform/migrations/versions/20250613_140000_create_customers_table.py`. Steps: post a synthetic Stripe checkout webhook payload (or onboarding payload) with `customer.last_name=""` (empty string) and `last_name=null` → assert HTTP 200 (graceful) and that a `customers` row is created/upserted with `last_name` either NULL or empty string but no other field corrupted. Confirm no orphaned `service_agreements` row was left behind.
15. **All 4 `billing_reason` branches of `invoice.paid`** (per `bughunt/2026-04-16-cr1-cr6-e2e-verification.md` CR-4). VERIFY: `grep -n "billing_reason" src/grins_platform/api/v1/webhooks.py` should return lines `:565`, `:566`, `:567` (gating renewal vs. first-invoice vs. subscription_cycle). Steps: trigger 4 separate `invoice.paid` events via `e2e/master-plan/sim/stripe_event.sh invoice.paid` with each `billing_reason`:
    - `subscription_create` — assert agreement is treated as first-invoice (no renewal-cycle SMS).
    - `subscription_cycle` — assert renewal-cycle handling (next jobs auto-generated, customer notification appropriate).
    - `subscription_update` — assert change is logged but does not double-bill.
    - `manual` — assert manual invoice is paid without affecting subscription state.
    Capture `sent_messages` and audit-log rows after each branch.

#### Acceptance
- [ ] Audit, notifications, alerts, settings APIs respond.
- [ ] All webhook signatures verified.
- [ ] Replay dedup enforced.
- [ ] Webhook with empty `last_name` returns 200 and creates a clean customer row, no orphaned agreements.
- [ ] All 4 `billing_reason` branches of `invoice.paid` produce correct downstream side-effects.

---

### Phase 22 — Responsive Viewport Sweep (Umbrella Tasks 6.8 + 6.9)

**Goal**: Re-visit the most-touched admin pages at three viewports (mobile 375×812, tablet 768×1024, desktop 1440×900) and capture screenshots for layout regression review. Console + uncaught-exception gate is mandatory at every step.

**Prerequisites**: P0.

#### Steps

For each viewport in [375x812 / 768x1024 / 1440x900]:

1. `agent-browser set viewport <W> <H>`.
2. Navigate to each (extended to include umbrella-introduced pages):
   - **Standard**: `/dashboard`, `/leads`, `/sales`, `/customers`, `/jobs`, `/schedule`, `/invoices`, `/agreements`, `/contract-renewals`, `/communications`, `/settings`.
   - **Umbrella plan additions** (Task 6.8): appointment modal (open from `/schedule`), `/invoices?tab=pricelist`, the EstimateSheet flow (open from appointment modal → "Send estimate"), the PaymentSheet (open from appointment modal → "Collect payment"), customer-portal `/portal/estimates/<token>`.
3. Screenshot each at full-page (`shot_full ...`).
4. Run `agent-browser console > errors-{viewport}-{page}.log` and `agent-browser errors > errors-{viewport}-{page}.err` after each — **mandatory gate** per Umbrella Task 6.9: every `*.err` file must be EMPTY. Any uncaught exception fails the gate. `*.log` may contain INFO/DEBUG but ZERO `error`-level lines.
5. Eye-check for: overflow, broken alignment, touch target sizes <44px on mobile, sidebar behavior on mobile (collapse vs hide).
6. **Mobile modal CTA visibility regression** (per `bughunt/2026-03-26-e2e-battle-test.md` lines 81–101 and `.agents/plans/schedule-and-appointment-modal-mobile-responsive.md`). VERIFIED selectors in source: `[data-testid='confirm-btn']` (`AppointmentDetail.tsx:737`), `[data-testid='cancel-btn']` (`:773`), `[data-testid='no-show-btn']` (`:760`), `[data-testid='edit-btn']` (`:747`), `[data-testid='schedule-visit-confirm-btn']` (`ScheduleVisitModal.tsx:203`), `[data-testid='schedule-visit-cancel-btn']` (`:196`). At 375×812: open AppointmentDetail (`[data-testid='appointment-detail']` at `:314`), then the Cancel/Reschedule sub-modals, the EstimateSheet, and the PaymentSheet. For each modal, run:
    ```js
    agent-browser eval "(() => {
      const cta = document.querySelector('[data-testid=\"confirm-btn\"]') || document.querySelector('[data-testid=\"schedule-visit-confirm-btn\"]');
      if (!cta) return {error: 'cta_not_found'};
      const r = cta.getBoundingClientRect();
      const vh = window.innerHeight;
      const inViewport = r.top >= 0 && r.bottom <= vh;
      const clickable = !!document.elementFromPoint(r.left + r.width/2, r.top + r.height/2)?.closest('[data-testid]');
      return {visible: inViewport, clickable, rect: r, viewport: vh};
    })()"
    ```
    Assert `visible: true` AND `clickable: true` for every CTA. Capture screenshot per modal at `${RUN_DIR}/phase-22-responsive/375/<modal>-cta-visible.png`. (The original bug was that a sticky bottom bar overlapped the CTA — `elementFromPoint` returning a different testid than the CTA's would catch it.)
7. **ScheduleVisit visual regression** (per `.agents/plans/schedule-visit-modal-full-redesign.md` and `.agents/plans/schedule-visit-modal-ui-refresh-high-fidelity.md`). At 1440×900, open the Sales tab → schedule visit modal → take a full-page `shot_full schedule-visit-redesign.png`. Compare visual against the high-fidelity reference (slate/white theme, tone-based event cards, kbd hints in the legend). Run console capture; assert no error.

#### Acceptance
- [ ] All pages (standard + umbrella additions) render without console errors at all 3 viewports.
- [ ] Every `errors-*.err` file empty.
- [ ] Screenshots captured for review.
- [ ] At 375×812, every modal's primary CTA (Confirm/Save/Pay) sits above the sticky action bar (no overlap).
- [ ] ScheduleVisit modal matches the high-fidelity slate/white redesign.

#### Re-run criteria
- Cheap; can run after any UI-touching change.

---

### Phase 22b — Cross-Phase Integration Happy Path (Umbrella Task 6.7)

**Goal**: A single end-to-end run that exercises every umbrella phase in order — proves the system is integrated, not just that each piece works alone.

**Prerequisites**: P0–P14 ideally (all features in this scenario must be working independently first).

**Variant lane**: Admin desktop, with portal lane for the customer approval. Reuses `e2e/integration-full-happy-path.sh` as a starting point (verified at lines 1–127).

#### Steps (1 long flow, ~30 screenshots → `${RUN_DIR}/phase-22b-integration/`)

1. **Setup**: create test customer (or reuse Kirill seed), test property (residential), test appointment in `to_be_scheduled` or `scheduled`.
2. **Phase 4c** — open appointment → click "Send estimate" → LineItemPicker opens → search `"spring"` → select Spring Start-Up (`size_tier`) → S size → submit estimate. Screenshots `01-appointment-modal.png` … `05-estimate-submitted.png`.
3. **Phase 4d / 5** — customer approves via portal (use `sim/signwell_signed.sh` if SignWell is in the loop; otherwise click Approve on `/portal/estimates/<token>` directly). Job auto-created in `to_be_scheduled`; signed PDF arrives in `kirillrakitinsecond@gmail.com` (verify with `sim/resend_email_check.sh poll`); audit log row written. Screenshots `06-portal-approve.png`, `07-modal-banner-job-created.png`, `08-audit-log.png`.
4. **Phase 0 follow-up CTA** — click "Schedule follow-up" on the Approved card → existing schedule modal opens against the new Job → schedule for tomorrow. Screenshot `09-schedule-followup.png`.
5. **Phase 11 / Maps polish** — open appointment → click directions → choose Google + check Remember → close → reopen → defaults to Google. Screenshot `10-google-remembered.png`.
6. **Phase 11 / 12 — on-site flow** — On my way → Job started → Job complete → Collect $X cash → confirmation card "Paid — $X · cash" → receipt SMS + email arrive (verify allowlist) → timeline shows estimate, payment, completion events in order. Screenshots `11-on-my-way.png` … `16-timeline-final.png`.
7. **Phase 4b — pricelist edit** — navigate to `/invoices?tab=pricelist` → edit Spring Start-Up's `display_name` to `"Integration Edited Name"` → save. Screenshot `17-pricelist-edited.png`.
8. **Phase 4a — verification** — `api_q "/api/v1/services?limit=200&active_only=false" '[.items[] | select(.slug != null)] | length'` → expect 73 still intact (or 74 if a Phase 4b create test was inline).

#### DB / API end-state verifications

```bash
# 73 seeded rows still intact
api_q "/api/v1/services?limit=200&active_only=false" '[.items[] | select(.slug != null)] | length'
# Expected: 73 (or 74 if Phase 4b created an inline test offering)

# Auto-job exists
api_q "/api/v1/jobs?customer_id=$KIRILL_CUSTOMER_ID&limit=10" \
  '[.items[] | select(.estimate_id != null)] | length'
# Expected: ≥1

# Payment + receipt
api_q "/api/v1/sent-messages?message_type=payment_receipt&limit=5" \
  '[.items[].recipient_phone] | unique'
# Expected: only +19527373312
```

#### Acceptance
- [ ] All 30 screenshots present and chronological.
- [ ] No console errors at any step (gate from Phase 22 applies).
- [ ] Every umbrella phase (0, 1, 2, 3, 4, 5) is touched at least once.
- [ ] DB end-state matches expectations.

#### Cleanup
- Delete the test estimate, the auto-created job, the test invoice, and the test pricelist edit (if any). Reset Maps preference to its prior value.

#### Re-run criteria
- Standalone-runnable. Must run after a release-candidate build before merge to `main`.

---

### Phase 23 — Unit / Integration / Lint / Typecheck Sweep (NOT browser-driven)

**Goal**: Run all in-repo test suites and quality gates.

**Prerequisites**: Local clone with `uv sync` and `npm install` done.

**Variant lane**: CLI.

#### Steps

```bash
# Backend — three tiers
uv run pytest -m unit -v            # fast, no deps
uv run pytest -m functional -v       # requires Postgres (local)
uv run pytest -m integration -v      # requires full system
uv run pytest -m hypothesis -v       # property-based tests
uv run pytest --cov=src/grins_platform --cov-report=html

# Backend — quality gates
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/

# Frontend — tests + types + lint
cd frontend
npm test
npm run test:coverage
npm run typecheck
npm run lint
npm run format:check
```

Compare baselines:
- Per `Testing Procedure/README.md:55`: unit-test baseline is **28 failures**. If a new run shows different count, regression.
- Per `bughunt/2026-04-29-pre-existing-tsc-errors.md`: known TS errors baseline; track delta.

#### Acceptance
- [ ] No new failures vs baseline.
- [ ] Coverage targets met (services 90%+, components 80%+, hooks 85%+ per `spec-testing-standards.md`).
- [ ] Zero ruff/mypy/pyright/eslint/tsc errors on new code.

---

### Phase 23b — E2E Sign-off Report (Umbrella Task 6.10)

**Goal**: Produce the canonical sign-off artifact for **this run** at `e2e-screenshots/master-plan/runs/<RUN_ID>/E2E-SIGNOFF-REPORT.md` certifying every phase passed and the screenshot tree is complete. **No release merges into `main` until this run's report is committed alongside the code with verdict ALL PASS.**

**Prerequisites**: P0 through P22b complete; P23 also complete for code-quality gates.

**Variant lane**: Operator (report-writing).

#### Per-run directory convention

Every full master-plan run writes **all of its artifacts** — sign-off markdown, human-checkpoint log, and the full per-phase screenshot tree — into a **dated, run-scoped directory** so historical runs are preserved verbatim and never silently overwritten:

```bash
# RUN_ID is set once at the start of the run and re-used by every phase
# that writes any per-run artifact.
export RUN_ID="${RUN_ID:-$(date +%Y-%m-%d)}"          # default: today (local clock)
export RUN_DIR="e2e-screenshots/master-plan/runs/${RUN_ID}"

# Refuse to overwrite an existing run directory.
if [[ -d "${RUN_DIR}" ]]; then
  echo "Run dir ${RUN_DIR} already exists — pick a new RUN_ID (e.g. RUN_ID=${RUN_ID}-rerun) or git mv the old run aside." >&2
  exit 1
fi
mkdir -p "${RUN_DIR}"
```

For multiple runs on the same calendar day, the operator MUST set `RUN_ID` explicitly to disambiguate (e.g. `RUN_ID=2026-05-04-rerun-after-bugD`).

Inside `${RUN_DIR}/`, the layout is:

```
e2e-screenshots/master-plan/runs/${RUN_ID}/
├── E2E-SIGNOFF-REPORT.md           # Phase 23b deliverable
├── _human-checkpoints.md           # human-only step log generated by the runner
├── phase-00-preflight/
│   ├── 01-frontend-up.png
│   └── ...
├── phase-01-auth-security/
│   ├── 01-login-loaded.png
│   ├── 02-credentials-filled.png
│   └── ...
├── phase-NN-{slug}/                # one dir per phase that produced screenshots
│   ├── *.png
│   ├── *.console.log
│   └── *.errors.log
└── ...
```

Every phase in this plan that documents a screenshot path uses `${RUN_DIR}/phase-NN-{slug}/...`; the older bare `e2e-screenshots/master-plan/phase-NN-...` form is legacy and must be rewritten on read.

#### Required deliverable

Write `${RUN_DIR}/E2E-SIGNOFF-REPORT.md` containing:

1. **Run metadata**: `RUN_ID`, date, environment (`local` or `dev`), git SHA, agent-browser version, Railway service deploy id (if dev). **Run start + end timestamps + total wall-clock duration** are mandatory.
2. **Per-phase pass/fail table** for P0–P22b with screenshot links.
3. **Per-phase timing table** (mandatory). One row per phase. Each row records: phase number/name, **start time (UTC)**, **end time (UTC)**, **duration**, and a **`time-spent` narrative** that breaks down where minutes went *within* that phase — e.g. "source-verify selectors (5s), admin login UI (10s), bad-pass (15s), lockout test (60s incl. DB query that surfaced Bug A)…". The narrative is the load-bearing field — totals without breakdown don't tell the next operator anything actionable. The table goes near the top of the report (right after run metadata) so a reader sees the cost shape before the per-phase verdicts. The harness already writes per-phase epoch markers to `_human-checkpoints.md` and to a per-run `PHASE-TIMING.md` if it exists; the sign-off report's timing table consolidates that data.
4. **Total screenshots captured** (target per umbrella plan: ≥130 across all phases — verify with `find "${RUN_DIR}" -name '*.png' | wc -l`).
5. **Database verification log**: every `api_q` / `psql_q` / `railway_python` query and its returned value.
6. **Console + error file inventory**: link every `*.console.log` and `*.errors.log`; confirm every `errors-*.log` empty.
7. **Bug regression status**: per-phase confirmation that the relevant CLOSED bugs (#12–#16, original 1–7) did NOT regress. Reference each bug's repro section in this plan.
8. **Deviations**: any expected behavior that did not match. Each deviation must include a screenshot/log link, root cause, and remediation status (fix commit ref OR ticket id).
9. **Final verdict**: `ALL PASS` (literal string) or a list of remaining gaps with severity per gap.

#### Template

```markdown
# Master E2E Sign-off Report

**RUN_ID**: <YYYY-MM-DD or YYYY-MM-DD-<suffix>>
**Date**: 2026-MM-DD
**Environment**: dev (or local)
**Run started**: <ISO 8601 UTC>
**Run ended**: <ISO 8601 UTC>
**Total duration**: <HHh MMm>
**Git SHA**: <sha>
**Agent-browser version**: <version>
**Railway deploy id**: <id>

## Per-phase timing

| Phase | Start (UTC) | End (UTC) | Duration | Where time was spent |
|---|---|---|---|---|
| P0 Preflight                | hh:mm:ss | hh:mm:ss | ~Nm | tooling check (5s), Railway link (3s), API health (2s), env-vars verify (8s), token acquisition (3s), seed customer + tech staff resolution (10s), frontend page load + screenshot (15s), probe SMS dispatch + human confirmation (30s), CallRail webhook reachability (3s) |
| P1 Auth & Security          | hh:mm:ss | hh:mm:ss | ~Nm | source-verify selectors / login / bad-pass / lockout test / session-persistence / refresh-regression / logout / role-redirect / security-headers / CORS / rate-limit / 5xx-CORS / candidate-doc — call out anything that ate >60s |
| P2 Marketing Lead Intake    | hh:mm:ss | hh:mm:ss | ~Nm | source-verify routes / marketing site open / form fill / submit / dedup / opt-in propagation / empty-last-name / zero-zone / terms / surcharge — flag form-fill quirks and selector drift |
| ...                         | ...      | ...      | ...  | ... |
| P22b Integration            | hh:mm:ss | hh:mm:ss | ~Nm | full flow ≤ 12 minutes |
| P23 Test Sweep              | hh:mm:ss | hh:mm:ss | ~Nm | pytest unit / functional / integration / hypothesis / coverage; ruff / mypy / pyright; npm test / typecheck / lint — record per-suite duration |
| P23b Sign-off Authoring     | hh:mm:ss | hh:mm:ss | ~Nm | report compose, deltas vs prior run |
| P24 Cleanup                 | hh:mm:ss | hh:mm:ss | ~Nm | Stripe cancellations, soft-deletes, tag/preference/passkey resets |

The narrative column is mandatory — a duration without a breakdown does not constitute a valid timing entry. If a phase was skipped or aborted, write the reason in the narrative ("DEFERRED — Bug E blocks inbound webhook; re-run after Bug E deploy").

## Per-phase verdict

| Phase | Verdict | Screenshots | Notes |
|---|---|---|---|
| P0 Preflight | PASS | N/A | All env vars present, token acquired |
| P1 Auth & Security | PASS | 8 | Biometric round-trip OK |
| P2 Marketing Lead Intake | PASS | 5 | E.164 normalization verified |
| ...                    | ... | ... | ... |
| P22b Integration       | PASS | 30 | Full flow ≤ 12 minutes |

## Total screenshots: <N> (target ≥130)

## DB verification log

<paste each api_q output as `path | query | result`>

## Console / error file inventory

<list each errors-*.log file and `EMPTY` / `<line count>`>

## Bug regression status

| Bug | Phase | Result |
|---|---|---|
| #12 size_tier picker empty | P4c step 10 | NOT REGRESSED |
| #13 portal company_logo crash | P4d step 0.1 | NOT REGRESSED |
| #14 collect_payment positional arg | P12 4.1–4.4 | NOT REGRESSED |
| #15 timeline missing icon | P12 4.9 | NOT REGRESSED |
| #16 stripe short-circuit to PAID | P12 4.5 | NOT REGRESSED |
| Original 1 (multi-head) | P14 setup | NOT REGRESSED (CI guard active) |
| Original 2 (allowlist 500) | P14 step 7 | NOT REGRESSED |
| Original 3 (SMS soft-fail) | P14 step 8 | NOT REGRESSED |
| Original 4 (CORS 5xx) | P1 step 13 | NOT REGRESSED |
| Original 5 (seeder hygiene) | P14 step 10 | NOT REGRESSED |
| Original 6 (wrong appt clicked) | P14 step 11 | NOT REGRESSED |
| Original 7 (RAILPACK drift) | Operator | DEFERRED (cosmetic) |

## Deviations

(none) — or list each with screenshot path + RC + fix ref.

## Final verdict

**ALL PASS**
```

#### Acceptance
- [ ] `E2E-SIGNOFF-REPORT.md` exists at `e2e-screenshots/master-plan/runs/${RUN_ID}/`.
- [ ] No previous run's report was overwritten (verify `${RUN_DIR}` did not exist before this run, or that the operator explicitly chose a fresh `RUN_ID` suffix).
- [ ] Run-metadata block includes `Run started`, `Run ended`, `Total duration`.
- [ ] Every phase (P0–P24, including 4a/4b/4c/4d/22b/23b) has a row in the **per-phase timing table** with start, end, duration, AND a `Where time was spent` narrative. Missing/empty narrative is a fail.
- [ ] Every phase (P0–P22b) has a row in the per-phase verdict table.
- [ ] Screenshot count ≥130.
- [ ] Every `*.errors.log` confirmed empty.
- [ ] Bug regression table covers all 12 documented bugs.
- [ ] Verdict is literal string `ALL PASS` or all gaps are explicitly tracked with tickets.

#### Cleanup
- Commit the report alongside the corresponding code change PR.

#### Re-run criteria
- Mandatory pre-merge to `main` for any release branch.

---

### Phase 24 — Cleanup & Teardown

**Goal**: Delete or restore all test-only records to leave dev DB in a known clean state.

**Prerequisites**: All target phases complete (or as far as the run got).

#### Steps

1. **Stripe**: cancel any test subscriptions created in P15. Refund any test charges. Dispute test charges can be left (Stripe dashboard).
2. **Customers / Leads / Jobs / Appointments / Invoices / Sales / Renewals**: delete or soft-delete using `Testing Procedure/scripts/cleanup.py` (base64 + `railway ssh`) or `Testing Procedure/99-cleanup.md` SQL templates.
3. **Sent messages**: leave for audit; record IDs in cleanup log.
4. **Tags / preferences / passkeys**: remove test tags, restore default preferences, delete virtual passkeys.
5. **Reschedule requests**: mark any open test requests as resolved.
6. **Duplicate pairs**: delete test-only pairs.
7. **Verify clean state**:
   ```bash
   curl "$API_BASE/api/v1/customers/$KIRILL/sent-messages?limit=5" -H "Authorization: Bearer $TOKEN"
   # Expect: only baseline messages, not test detritus
   ```
8. **Re-arm seed customer**: ensure `sms_opt_in=true`, no STOP residue.

#### Acceptance
- [ ] No leftover test data visible in customer/lead/job/invoice lists.
- [ ] Seed customer remains intact at `e7ba9b51-580e-407d-86a4-06fd4e059380`.
- [ ] Probe SMS still works.

---

## TESTING STRATEGY

### Unit Tests
Backend: pytest tiered by `@pytest.mark.{unit,functional,integration,hypothesis}`. Frontend: Vitest + React Testing Library. Coverage targets per `spec-testing-standards.md` §5: services 90%+, components 80%+, hooks 85%+.

### Integration Tests
Backend functional + integration markers exercise real DB and full system. Run as part of Phase 23.

### End-to-End Tests
The body of this plan IS the E2E test specification. Driven by `agent-browser`, REST API verifications, and human checkpoints for SMS replies. Screenshots in `${RUN_DIR}/phase-{NN}/...` where `RUN_DIR=e2e-screenshots/master-plan/runs/${RUN_ID}` (see Phase 23b "Per-run directory convention").

### Property-Based Tests
Hypothesis tests for invariants (job generation counts, status transitions, financial calculations) per `spec-testing-standards.md` §1. Run as `pytest -m hypothesis`.

### Edge Cases
- **Empty / null fields**: lead with no last name (Phase 2), property with no zone count, appointment with no service type (cancellation SMS wording change), customer with no email (signing-by-email button disabled).
- **Idempotency**: repeat C → no-op (E7 known gap), repeat send-confirmation → no second SMS.
- **State machine violations**: invalid sales pipeline transitions (422), invalid appointment status transitions, cancelling an already-cancelled.
- **Webhook replay**: same event id → dedup; HMAC mismatch → 401.
- **Allowlist escapes**: dev SMS to non-allowlisted phone → 403 / 422; email to non-allowlisted → 422 (NOT 500 per Bug 2).
- **Rate limits**: CallRail rate-limit response → explicit failure (NOT silent fallthrough per Bug 3).
- **CORS on 5xx**: 500 still includes Access-Control-Allow-Origin (per Bug 4).
- **Token expiry**: portal estimate token > 60 days → 410.
- **Concurrency**: drag-drop a draft while another user sends confirmation — verify last-write-wins or appropriate locking.

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style (Phase 23)
```bash
uv run ruff check --fix src/
uv run ruff format src/
cd frontend && npm run lint && npm run format:check && cd ..
```

### Level 2: Type Checking (Phase 23)
```bash
uv run mypy src/
uv run pyright src/
cd frontend && npm run typecheck && cd ..
```

### Level 3: Unit / Functional / Integration Tests (Phase 23)
```bash
uv run pytest -m unit -v
uv run pytest -m functional -v
uv run pytest -m integration -v
uv run pytest -m hypothesis -v
uv run pytest --cov=src/grins_platform --cov-report=html
cd frontend && npm test && npm run test:coverage && cd ..
```

### Level 4: E2E (this plan, Phases 0–22)
Full run:
```bash
# Each phase document has its own steps; run sequentially
# Or use the auxiliary harness once authored:
e2e/master-plan/run-all.sh
```
Single phase:
```bash
e2e/master-plan/run-phase.sh 4   # only Phase 4 (Sales Pipeline)
```

### Level 5: Health smoke
```bash
curl -s https://grins-dev-dev.up.railway.app/health | jq .
curl -sI https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/login | head -5
```

---

## ACCEPTANCE CRITERIA

- [ ] All 25 phases (P0–P24) documented with: Goal, Prerequisites, VERIFY block, Steps, Acceptance, Cleanup, Re-run criteria, Stale-reference watchlist.
- [ ] Every claimed selector, endpoint, and route has a `grep`/`Read` verification command in its phase's VERIFY block.
- [ ] Every human checkpoint is clearly boxed with the exact text the phone-holder should send.
- [ ] Phases that depend on earlier phases declare prerequisites explicitly.
- [ ] Variant lanes (admin / tech-mobile / public) clearly labeled.
- [ ] Stale references in `scripts/e2e/` and bughunt docs are flagged with corrections.
- [ ] Phase Selection Matrix below makes it possible to pick which phases to run for any given changed surface area.
- [ ] All env vars, seed identities, and constants pulled from authoritative source (Testing Procedure/README + memory entries).

---

## COMPLETION CHECKLIST

- [ ] Steering docs read (Phase 0 of planning).
- [ ] update2_instructions.md sections 1–16 mapped to phases.
- [ ] Existing E2E artifacts inventoried; stale references flagged.
- [ ] Dev URLs / seed identities / allowlists / webhook URLs all confirmed against current source.
- [ ] Phase graph designed with explicit dependencies.
- [ ] Master plan document written and committed (this file).
- [ ] Phase Selection Matrix added.
- [ ] Confidence score recorded.

---

## PHASE SELECTION MATRIX

When a single feature changes, run only the affected phases (plus P0 always). Includes the new umbrella-plan phases (4a–4d, 22b, 23b).

| Changed Area | Phases to run |
|---|---|
| Login / auth / WebAuthn / **session-refresh stale-header regression** | P0, P1 |
| Marketing site lead form / **zone validation / terms checkbox / surcharge consistency** | P0, P2 |
| Leads tab UI / routing | P0, P2, P3 |
| Sales pipeline / SignWell / **ScheduleVisit conflict + drag boundary** | P0, P3, P4, P5 |
| **Pricelist data / seed migrations** | **P0, P4a** |
| **Pricelist editor UI** | **P0, P4a, P4b** |
| **LineItemPicker / SubPickers / range_anchors** | **P0, P4a, P4b, P4c** |
| **Auto-job-on-approval (N5 setting / EstimatePDFService)** | **P0, P4, P4d, P5** |
| Email portal | P0, P4, P4d, P5 |
| Customers tab | P0, P6 |
| Jobs tab / **dropdown action visibility** / **city sort** | P0, P3 or P4, P7 |
| Schedule (admin) / appointments / "Send estimate" CTA / **DRAFT send-confirmation** / **persistent tray** | P0, P7, P8 |
| SMS confirmation flow Y/R/C / **repeat-Y idempotency** / **post-cancel R** / **provider_thread_id persistence** | P0, P8, P9, P10 |
| Reschedule queue / **late-reschedule rejection** / **invalid-status-transition rejection** | P0, P9, P10 |
| Tech mobile schedule / **Maps remember choice** / **AppointmentDetail secondary actions** | P0, P8, P11 |
| On-site payment / **payment matrix** (cash/check/Venmo/Zelle/Stripe/refund) | P0, P11, P12 |
| Invoices / mass-notify / lien / **server-side days_until_due / days_past_due** | P0, P13 |
| Stripe Payment Links / **dispute reconciliation** / **soft-fail transparency** | P0, P13, P14 |
| Service packages onboarding | P0, P15 |
| Contract renewals | P0, P15, P16 |
| Duplicate management | P0, P17 |
| AI scheduling / **resource-timeline utilization_pct** / **cache invalidation on reassign** | P0, P18 |
| Dashboard alerts / **full AlertType enumeration** / **filters + pagination on /alerts** | P0, P19 |
| Communications / **inbox endpoint** / **conversation endpoint** / **queue refetchInterval polling** | P0, P20 |
| Security / webhooks / **stripe_terminal uninstall** / **empty last_name resilience** / **billing_reason branches** | P0, P21 |
| UI layout (any) / **mobile modal CTA visibility** / **ScheduleVisit visual regression** | P0, P22 |
| **Cross-phase happy path** | **P0 → P14, then P22b** |
| Code-level changes | P23 (always before merge) |
| **Release gate sign-off** | **P0 → P22b, P23, P23b** |
| Full release | P0 → P24 in order |

---

## CONFIDENCE SCORE

**10/10** for one-pass agent execution.

### What changed from the initial 8/10

| Gap at 8/10 | Closed by |
|---|---|
| "Verify before assuming" wishy-washy paths | Every endpoint, route, selector, and tech credential is now grounded with `file:line` references in the Codebase Files section. The verification audit done before publishing this version found and fixed: webhook URLs (`/webhooks/{provider}` not `/{provider}-webhooks`), sales pipeline paths (`/sales/pipeline/{id}/...` not `/sales/{id}/...`), lead routing verbs (Mark Contacted is `PUT`, not POST), contract-renewal per-job nesting (`/jobs/{job_id}/{approve,reject}`), audit-log singular path, manage-subscription living in checkout.py, lead testid pattern with id suffix, sales-advance using a dropdown (no advance button), `line-item-picker-result-*` does not exist (use `line-item-picker-results` collection), PhoneOnlyGate at layout level not route level. |
| Bug status uncertain | Bug Status Reference at top of plan now lists all 11 bugs (6 original + 5 tech-mobile) with **CLOSED + commit hash + test path** for 10 of 11 and `NEEDS RUNTIME CHECK` for 1 (cosmetic). |
| Phase 9 SMS Y/R/C requires HUMAN | `e2e/master-plan/sim/callrail_inbound.sh` posts HMAC-signed payloads at `POST /api/v1/webhooks/callrail/inbound`. HMAC verification still enforced — wrong secret = 403, by design. Human run still recommended for first-time changes; simulator handles re-runs. |
| Phase 5 email portal requires HUMAN | `e2e/master-plan/sim/resend_email_check.sh poll <to> <subject>` polls backend `sent_messages` for the matching email. Eliminates inbox-watch. |
| Phase 4 SignWell auto-advance requires real signing | `e2e/master-plan/sim/signwell_signed.sh <doc_id>` posts HMAC-signed `document_completed` event. |
| Phase 14 / 16 Stripe events require manual trigger | `e2e/master-plan/sim/stripe_event.sh <event_name>` wraps `stripe trigger`. |
| "Auxiliary harness once authored" — placeholder | Harness exists: `_dev_lib.sh`, `run-phase.sh`, `run-all.sh`, `sim/*.sh`. Tested-syntactically; semantic verification happens on first run. |
| Stale references in `scripts/e2e/` | 26 of 27 scripts have stale `[name='email']` selectors per `E2E_REGRESSION_REPORT.md`. **DO NOT** copy login flow from those scripts. The canonical login pattern is in `_lib.sh:76-84` and replicated in `_dev_lib.sh:login_admin`. Phase scripts must source `_dev_lib.sh`. |
| Umbrella plan Phase 6 testing not folded in | All 10 umbrella tasks (6.1–6.10) now incorporated as new Phases 4a (pricelist seed), 4b (pricelist editor — all 17 variants), 4c (LineItemPicker — 5 paths × 6 branches), 4d (auto-job-on-approval — 10 scenarios), Phase 12 extension (full payment matrix — 16 sub-cases), Phase 8/11/21 polish additions (CTA rename, Maps remember, stripe_terminal uninstall), Phase 22b (cross-phase happy path), Phase 23b (E2E sign-off report deliverable). The 5 closed tech-mobile bugs (#12–#16) each have an explicit regression-check step in the corresponding phase. |
| Coverage of *other* plans, bughunts, scheduling-gaps, Testing Procedure paths, and kiro spec acceptance criteria not yet audited | Full coverage audit completed 2026-05-02 (see `.agents/plans/master-plan-coverage-audit.md`). Surveyed 156 source files (~2,150 scenarios). Verified each "MISSING" claim against `src/` and `frontend/src/` before adding. Folded **23 real MISSING regressions** into existing phases (P1, P2, P4, P7, P8, P9, P10, P11, P13, P14, P18, P19, P20, P21, P22) plus **9 PARTIAL extensions**. **0 new top-level phases needed**. Audit-pass also corrected an initial out-of-scope mis-classification: the gap-05 hard-STOP audit log, gap-06 informal-opt-out chain, gap-11 timeline endpoint, gap-13 conversation endpoint, gap-14 AlertType enumeration, gap-15 queue refetchInterval polling, and gap-16 unified-inbox endpoint were all initially flagged as "proposed-but-unbuilt" but re-greps with the correct symbol names (e.g., `log_consent_hard_stop` instead of `sms_consent_revoked`, the actual `AlertType` enum names instead of the gap-doc shorthand `AT-1..AT-6`) confirmed all seven exist in source and they were folded into P9, P11, P19, and P20. Genuinely out-of-scope items: HOA codes (no source matches), Stripe Terminal (shelved per memory), MMS/Unicode/i18n (gap-09 — genuinely absent), gap-10 auto-reminder Phase 1 (manual queue only). |
| Selectors / response shapes guessed by convention rather than verified | Final anchor sweep done 2026-05-02. Every newly added selector is now grounded with a `file:line` reference in source: `schedule-visit-conflict-banner` (`PickSummary.tsx:54`), `schedule-visit-confirm-btn` (`ScheduleVisitModal.tsx:203`), `capacity-${date}` (`CapacityFooter.tsx:19,33`), `confirm-btn`/`cancel-btn`/`edit-btn` (`AppointmentDetail.tsx:737/773/747`), `appointment-communication-timeline` + `timeline-event-${id}` (`AppointmentCommunicationTimeline.tsx:67,154`), `inbox-queue` + `inbox-filter-${key}` + `inbox-row-${id}` (`InboxQueue.tsx:124/209/302`), `queue-last-updated` + `queue-refresh-btn` (`QueueFreshnessHeader.tsx:67/79`), `scheduling-tray` (`SchedulingTray.tsx:81`), `get-directions-btn` + `remember-maps-choice-checkbox` (`AppointmentDetail.tsx:535`, `MapsPickerPopover.tsx:153`), `login-error` (`LoginPage.tsx:133`). Response shapes verified: `/audit-log` accepts `?action=&resource_type=&page=&page_size=` returns `{items,total}` (`api/v1/audit.py:43-56`); `/alerts` accepts `?type=` (single, back-compat) + `?alert_type=` (repeatable) + `?severity=` (repeatable) + `?since=&sort=&offset=&limit=` returns `{items,total}` (`api/v1/alerts.py:46-105`); `/inbox` returns `{items,next_cursor,has_more}` (`schemas/inbox.py:97-108`); appointment timeline returns `{events: list[TimelineEvent]}` with `kind` discriminator + `occurred_at` (`schemas/appointment_timeline.py:88,44-45`). |

### What remains (irreducible operational considerations)

These are not gaps in the plan, but realities of the system:

- **Tech-mobile photo upload from camera**: agent-browser cannot drive iOS camera intent. File-input upload via `agent-browser fill` works for the `<input type="file">` path; camera-button path is untestable in headless. Plan documents this constraint.
- **Real CallRail rate-limit / STOP**: simulators bypass carrier-level state. Pre-release smoke must include one human run with the real phone to catch carrier behavior.
- **Stripe link tap**: clicking the link in the SMS still requires either a human tap or scripted `agent-browser` open of the URL. Plan documents the latter as the automation path.
- **Bug 7 cosmetic Railway drift**: only verifiable on the next deploy. Plan defers to the operator runbook step.

None of these prevent one-pass execution; they are documented constraints, not unknowns.

### Confidence stress-test

A reasonable agent armed with this document should be able to:
- Run any single phase against dev with `ENVIRONMENT=dev e2e/master-plan/run-phase.sh N`, hit zero "what does this mean?" moments.
- Identify drift instantly if any selector or endpoint moves (every claim has a `file:line` anchor).
- Produce a deterministic screenshot tree under `${RUN_DIR}/phase-NN-*/` (with `RUN_DIR=e2e-screenshots/master-plan/runs/${RUN_ID}`); each full run lives in its own dated directory.
- Generate a complete pass/fail summary at the end of `run-all.sh` from the per-phase exit codes.
- Pick any plan / bughunt / scheduling-gap / Testing Procedure path / kiro spec acceptance criterion in the repo and locate it in the master plan in under 30 seconds (verified by the 2026-05-02 coverage audit pass).
- Open any added regression step and find a `data-testid` or response-shape claim grounded with a `file:line` anchor in source (verified by the 2026-05-02 anchor sweep).

Remaining residual risk lives entirely outside the plan's control (third-party provider state, carrier behavior, dashboard-side config).

---

## NOTES

### Why this is one giant document, not many files
Per the user's instruction, this is the **single source of truth**. Keeping it in one file means version-controlling the relationship between phases is trivial. If it grows unwieldy, sub-phase shell scripts in `e2e/master-plan/` will be the lower-level mechanical execution.

### Re-runnability is the design center
Each phase is engineered to run on its own once its data prereqs exist. The Phase Selection Matrix is the contract: "I changed X, run these N phases." The seed customer is preserved across runs; only test artifacts are torn down in P24.

### Human-in-the-loop is currently structural, not optional
The HMAC-signed inbound-SMS simulator at `e2e/master-plan/sim/callrail_inbound.sh` posts to `POST /api/v1/webhooks/callrail/inbound` with a valid HMAC, so Phase 9 / 10 can run without a human in iteration cycles. Pre-release smoke runs must still include one human pass to catch carrier-level state. **Do not** modify the simulators to bypass HMAC.

### Stale references are a known hazard

The user explicitly called this out. **26 of 27 shell scripts in `scripts/e2e/` use deprecated login selectors** (`[data-testid='email-input']` → `[name='email']` → `input:first-of-type`) that all fail on the current login form (`LoginPage.tsx` uses `username-input`/`password-input`/`login-btn`). Verified via the audit done while authoring this plan.

**Stale scripts** (do NOT copy login flow from these — port to `_dev_lib.sh:login_admin`):

```
test-accounting.sh, test-agreement-flow.sh, test-ai-scheduling-alerts.sh,
test-ai-scheduling-chat.sh, test-ai-scheduling-overview.sh,
test-ai-scheduling-resource.sh, test-ai-scheduling-responsive.sh,
test-communications.sh, test-customers.sh, test-dashboard.sh,
test-estimate-detail.sh, test-invoice-portal.sh, test-invoices.sh,
test-jobs.sh, test-leads.sh, test-marketing.sh, test-mobile-staff.sh,
test-navigation-security.sh, test-notifications.sh, test-rate-limit.sh,
test-sales.sh, test-schedule-visit.sh, test-schedule.sh,
test-session-persistence.sh, test-settings.sh, test-sms-lead.sh
```

`scripts/e2e/E2E_REGRESSION_REPORT.md:83` documents this drift. The newer `e2e/_lib.sh:76-84` and `e2e/master-plan/_dev_lib.sh:login_admin` use the correct selectors. **Always run the VERIFY block before running steps**.

### Dev environment vs local
This plan targets **dev Vercel + dev Railway**. The local-dev path (`localhost:5173` + `localhost:8000` + local Postgres) is supported via `BASE`/`API_BASE`/`DATABASE_URL` env overrides — most of the steps work locally too, with the notable exception that local Postgres allows direct `psql` queries while dev Railway does not.

### Tech mobile testing prerequisites
The recent commit `2048d28 chore(tech-mobile): align demo seed + scripts with deployed dev tech identities` aligned tech identities with the deployed dev DB. Tech users `vasiliy`, `steve`, `gennadiy` (password `tech123`) are pre-seeded via `migrations/versions/20250626_100000_seed_demo_data.py`. Confirm presence with `GET /api/v1/staff?role=tech` before running P11.

### Webhook simulators (NOW LIVE)
HMAC-signed payload generators live at `e2e/master-plan/sim/`:
- `callrail_inbound.sh` — inbound SMS reply (Y/R/C/STOP/etc.) for Phase 9, 10, 11, 14
- `signwell_signed.sh` — `document_completed` event for Phase 4, 5
- `stripe_event.sh` — wraps `stripe trigger` for Phase 14, 16
- `resend_email_check.sh` — polls backend `sent_messages` for email delivery (Phase 5, 4)

All preserve HMAC verification end-to-end. See `sim/_README.md` for usage.

### Cross-reference index of bughunt issues addressed
| Bughunt | Phase that re-verifies |
|---|---|
| 2026-04-28-stripe-payment-links-e2e-bugs.md | P14 |
| 2026-04-29-ai-scheduling-system-validation.md | P18 |
| 2026-04-30-resource-timeline-view-deep-dive.md | P18 |
| 2026-05-01-appointment-modal-payment-estimate-pricelist-audit.md | P8, P12, P13 |
| 2026-04-16-cr1-cr6-e2e-verification.md | P3 (CR-6), P9 (CR-3), P11 (CR-2), P14 (CR-4), P13 (CR-5), P8 (CR-1) |
| 2026-04-14-customer-lifecycle-deep-dive.md | P19 (E-BUG-J), P3, P4, P9 |
| 2026-04-09-communications-deep-dive-round-2.md | P20 |
| 2026-04-09-communications-poll-workflow-deep-dive.md | P20 (poll feature blocked on inbound-webhook tunnel per memory) |

### Memory entries that constrain testing
- **SMS test number restriction**: only `+19527373312` may receive real SMS. Do not change.
- **Email test allowlist**: only `kirillrakitinsecond@gmail.com` allowed in dev/staging.
- **No remote alembic from local (2026-05-02)**: never run alembic against `*.railway.{app,internal}` from local; push to branch and let Railway apply.
- **Stripe Payment Links Architecture C live**: card payments via Payment Links over SMS. Reconciliation via `metadata.invoice_id`. M2 hardware shelved.
- **Estimate email portal wired via Resend (2026-04-26)**: live in `_send_email`.
- **Dev Stripe price ID mismatch (2026-04-15, resolved)**: dev tiers were once overwritten with live IDs; restored from backup. Watch for reoccurrence.
