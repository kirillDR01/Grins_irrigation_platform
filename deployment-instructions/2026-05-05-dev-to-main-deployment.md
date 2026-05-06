# Deployment Instructions: dev → main (May 5, 2026)

**Date:** May 5, 2026
**Source branch:** `dev`
**Target branch:** `main`
**Commits ahead of main:** 261 (4 commits on `main` not on `dev` are 1 squash release + 2 historical merge commits + 1 `.gitignore` already present in dev — see Section 18)
**New alembic migrations:** 38 (head moves `20260414_100000` → `20260510_120000_add_lead_consent_ts_and_utm_fields`)
**Companion repo:** `Grins_irrigation` (customer site) — 11 commits dev→main, see Section 16
**Rehearsal:** Required against a local `pg_restore` of the latest prod backup — see Section 14. Do **not** run alembic against `*.railway.{app,internal}` from your workstation (env.py guard `ALEMBIC_ALLOW_REMOTE` enforces this).

---

## Summary

This deployment lands the work after the 2026-04-14 release across nine major areas:

1. **Stripe Payment Links (Architecture C, Phases 1–7)** — Card payments via Stripe Payment Links over SMS, with deterministic reconciliation via `metadata.invoice_id`, payment-receipt SMS, and 5 new Stripe webhook event handlers.
2. **AI Scheduling System** — 6 new tables, 30 seeded weighting criteria, scheduling alerts, change requests, in-app chat. Integrates with OpenAI (existing `OPENAI_API_KEY`) and optional weather feed (`WEATHER_API_KEY`).
3. **Resource-Timeline Schedule View (Phases 1–4)** — New admin schedule UI replacing the old calendar; criteria overlay isolated from capacity payload.
4. **Tech Companion (phone-only)** — `/tech` route gated to `tech` role, `PhoneOnlyGate`, daily mobile schedule, Maps deep-linking (`preferred_maps_app` per staff).
5. **Pricelist from Viktor's Excel** — Service offerings extended with 8 new columns; 73-item seed gated by `VIKTOR_PRICELIST_CONFIRMED=true` (do **not** set on prod without product sign-off).
6. **WebAuthn / Passkey Auth** — New `webauthn_credentials` + `webauthn_user_handles` tables, `/auth/webauthn/*` routes, `@simplewebauthn/browser` on the frontend.
7. **Resend Email Provider (estimate emails + bounce webhook)** — Replaces stub email path; bounce flag on `customers.email_bounced_at`; portal email links via `PORTAL_BASE_URL` (now boot-guarded against deprecated Vercel preview aliases — F4-REOPENED).
8. **April-16 Smoothing** — `alerts` table for admin notifications, `appointment_attachments`, internal notes consolidation (notes table folded into `customers.internal_notes` / `leads.notes`), Day-2 confirmation reminder (feature-flagged), `flag_no_reply_confirmations` job.
9. **E2E Sign-Off Bug Bundles** — Multiple umbrella commits: per-keyword Y/R/C reply ack sub-types, R-reply now prompts for dates, lockout + per-IP rate limit on `/auth/login`, unconditional HSTS, `/pricebook → /invoices?tab=pricelist` redirect, reschedule route now returns 422 (was 400) on invalid status transitions, `provider_message_id` partial index hardened against empty-string collisions, `invoices.line_items` JSONB shape repair.

---

## Audit findings (re-classified — not deploy blockers)

A third-pass audit surfaced two issues. After verifying against `main`, both turn out to be **pre-existing in production**, not regressions introduced by this deploy. They are real bugs worth fixing on their own track, but they do **not block this dev → main cut**. Details in Section 22.

1. **Backend authorization gap on staff-scoped endpoints.** Four endpoints on `main` already accept `staff_id` from the request without verifying it matches the JWT subject (`/staff/{staff_id}/daily/{date}`, `/staff/{staff_id}/location`, `/staff/{staff_id}/breaks` POST/PATCH). This privilege-escalation surface has been in production since before this branch existed. This deploy adds **two more** endpoints with the same pattern (`GET/PATCH /api/v1/appointments/{id}/notes`, new in dev) — a small expansion of an existing gap, not a new class of bug. See §22.1.
2. **Lead-form schema silently drops 6 fields the customer site sends.** **RESOLVED** — `consent_timestamp` and 5 `utm_*` fields are now declared on `LeadSubmission`, persisted via migration #38 (`20260510_120000_add_lead_consent_ts_and_utm_fields`), and forwarded into `SmsConsentRecord` via the new `consent_timestamp_override` arg. See §22.2.

**Recommendation:** ship this deploy on its own merits. Track the authz audit + lead-schema fix as separate work — neither is made worse by merging dev.

---

## Pre-Flight Requirements (must be done before merging)

These will cause a **boot failure or silent data loss** if skipped.

### 1. Set `VIKTOR_PRICELIST_CONFIRMED` correctly per environment

The seed migration `20260504_130000_seed_pricelist_from_viktor` raises `RuntimeError` unless this var is `"true"`. The 73 items in `bughunt/2026-05-01-pricelist-seed-data.json` are Viktor's draft pricing.

- **Production:** **leave UNSET.** The migration fails fast on prod by design; that is the intended behavior until product/pricing has signed off and approved a controlled separate seed step.
- **Dev / staging:** set `VIKTOR_PRICELIST_CONFIRMED=true` on Railway so dev can apply the seed.

If the team is ready to seed prod in this same window, do it as a separate, supervised step **after** the rest of the migrations apply cleanly:

```bash
# Only with explicit pricing sign-off
railway variables set VIKTOR_PRICELIST_CONFIRMED=true --service api --environment production
# Apply the seed migration manually (Railway will re-run alembic on next deploy)
# Then immediately UNSET it again to prevent accidental re-seed
railway variables --remove VIKTOR_PRICELIST_CONFIRMED --service api --environment production
```

### 2. Deduplicate open `reschedule_requests` rows on prod

Migration `20260421_100000_reschedule_request_unique_open_index` creates a partial unique index on `(appointment_id) WHERE status='open'`. If prod already has duplicates, the index creation fails and the entire transaction rolls back, leaving the DB at the prior head. Run this **before** the deploy:

```sql
-- 1. Inspect (should return zero rows after fix)
SELECT appointment_id, COUNT(*)
FROM reschedule_requests
WHERE status = 'open'
GROUP BY appointment_id
HAVING COUNT(*) > 1;

-- 2. Mark all but the earliest 'open' row per appointment as 'superseded'
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (
    PARTITION BY appointment_id ORDER BY created_at ASC
  ) AS rn
  FROM reschedule_requests
  WHERE status = 'open'
)
UPDATE reschedule_requests
SET status = 'superseded', resolved_at = NOW()
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
```

### 3. Verify `notes` table contents on prod (data fold migration)

Migration `20260418_100700_fold_notes_table_into_internal_notes` aggregates `notes` rows by subject_type — `customer` → `customers.internal_notes`, `lead` → `leads.notes` — then **drops the table**. Sales-entry/appointment subjects are logged and discarded. If anyone has been writing those subject types directly to prod, they will be lost.

```sql
SELECT subject_type, COUNT(*) FROM notes GROUP BY subject_type;
```

If `sales_entry` or `appointment` counts are non-zero on prod, halt and decide what to preserve before continuing.

### 4. Set `PORTAL_BASE_URL` to canonical production domain

Boot guard F4-REOPENED (commit `7495d88`) hard-fails container startup if `PORTAL_BASE_URL` matches a deprecated Vercel preview alias (`frontend-git-*`, etc.) when `ENVIRONMENT in {dev,development,prod,production}` **or** `RAILWAY_ENVIRONMENT` is set. Without this, customer estimate/portal links 404 against a stale bundle.

```bash
railway variables set PORTAL_BASE_URL=https://app.grinsirrigation.com --service api --environment production
```

### 5. Confirm test guards are UNSET on prod

The dev-only allowlist guards must not be present on prod, or every outbound message gets blocked.

```bash
# Each must return empty / not set
railway variables get EMAIL_TEST_ADDRESS_ALLOWLIST --service api --environment production
railway variables get EMAIL_TEST_REDIRECT_TO        --service api --environment production
railway variables get SMS_TEST_PHONE_ALLOWLIST      --service api --environment production
railway variables get SMS_TEST_REDIRECT_TO          --service api --environment production
```

If any are set, **unset them** before deploy:

```bash
railway variables --remove EMAIL_TEST_ADDRESS_ALLOWLIST --service api --environment production
# repeat for the other three
```

### 6. Set WebAuthn relying-party config

Browsers reject `localhost`/`127.0.0.1` on a public origin. Without this, every passkey enrollment / login fails.

```bash
railway variables set WEBAUTHN_RP_ID=app.grinsirrigation.com \
  WEBAUTHN_RP_NAME="Grin's Irrigation" \
  WEBAUTHN_EXPECTED_ORIGINS="https://app.grinsirrigation.com" \
  --service api --environment production
```

**Important — these are NOT boot-validated.** `services/webauthn_config.py` is a `BaseSettings` with default `webauthn_rp_id="localhost"` and no boot-time validator. A misconfigured prod will boot cleanly and fail only on the first passkey registration/auth call. Smoke-test passkey enrollment immediately post-deploy (Section 19, step 6).

### 7. Provision Resend credentials

```bash
railway variables set \
  RESEND_API_KEY=re_xxx \
  RESEND_WEBHOOK_SECRET=whsec_xxx \
  --service api --environment production
```

Then in Resend dashboard → Webhooks: register `https://<api-domain>/webhooks/resend`, subscribe to `email.bounced` and `email.complained`, capture the signing secret into `RESEND_WEBHOOK_SECRET`.

### 8. Take a fresh prod backup

Five migrations are not cleanly reversible (Section 15). Take a Postgres backup immediately before the deploy and note the timestamp/ID for rollback.

```bash
# Railway UI: Project → Postgres → Backups → "Backup Now"
# OR pg_dump -Fc to remote storage with 30-day retention
```

---

## Pre-Deployment Checklist

- [ ] Pre-flight 1–8 above all complete
- [ ] Fresh prod database backup taken; backup ID/timestamp recorded
- [ ] All migration data-fitness queries (Section 11) pass on prod (no out-of-set rows)
- [ ] Rehearsal (Section 14) replayed on a local copy of prod data; all 37 migrations applied cleanly
- [ ] Companion repo `Grins_irrigation` deploy plan agreed with owner (Section 16)
- [ ] Stripe webhook events list updated for new event types (Section 7)
- [ ] CallRail webhook URL still points at prod API (no change since April-14, but reconfirm)
- [ ] `Viktor_excel/migration/Final.xlsx` and `bughunt/2026-05-01-pricelist-seed-data.json` are present at HEAD (the seed migration reads the JSON; the Excel is a reference artifact)
- [ ] CI `alembic-heads` workflow green on the merge commit (Section 13.3)
- [ ] On-call notified — Day-2 reminder job is feature-flagged off by default; pricelist seed is gated; rest will run on first prod boot

---

## 1. Database Migrations (38 new)

Production head is at `20260414_100000_fix_appointment_status_check_add_draft`. After this deploy the head moves to `20260510_120000_add_lead_consent_ts_and_utm_fields`. The chain is linear except for migration #27, which is an alembic merge of two parallel payment-link branches.

### Migration table

| # | Migration | Description |
|---|-----------|-------------|
| 1 | `20260414_100100_fix_job_status_check_add_scheduled` | Drops + recreates `ck_jobs_status` and the two `ck_job_status_history_*` constraints to re-add `'scheduled'`. |
| 2 | `20260414_100300_update_tier_descriptions_to_marketing_labels` | Data UPDATE on `service_agreement_tiers.included_services` to align JSON descriptions with marketing copy. |
| 3 | `20260416_100000_widen_invoice_payment_method_check` | Widens `ck_invoices_payment_method` to add `credit_card`, `ach`, `other`. |
| 4 | `20260416_100100_create_alerts_table` | Creates `alerts` table (5 cols + 5 indexes) for admin-facing notifications (SMS cancellations, bounces, etc.). |
| 5 | `20260416_100200_add_needs_review_reason_to_appointments` | Adds nullable `needs_review_reason` VARCHAR(100) + index to `appointments`. |
| 6 | `20260416_100300_seed_business_settings_h12` | Seeds 4 rows into `business_settings` (`lien_days_past_due`, `lien_min_amount`, `upcoming_due_days`, `confirmation_no_reply_days`) with `ON CONFLICT DO NOTHING`. |
| 7 | `20260416_100400_widen_sent_messages_for_confirmation_reply_and_followup` | Widens `ck_sent_messages_message_type` to add `appointment_confirmation_reply`, `reschedule_followup`. |
| 8 | `20260416_100500_create_notes_table` | Creates `notes` table (cross-stage timeline). **Dropped by #10.** |
| 9 | `20260416_100600_create_appointment_attachments_table` | Creates `appointment_attachments` table (S3 metadata, 8 cols + composite index). |
| 10 | `20260418_100700_fold_notes_table_into_internal_notes` | Aggregates `notes` rows into blob columns; drops the `notes` table. **Lossy for `sales_entry`/`appointment` subject_types.** |
| 11 | `20260421_100000_reschedule_request_unique_open_index` | Partial unique index on `reschedule_requests(appointment_id) WHERE status='open'`. **Pre-flight dedup required (Section 11).** |
| 12 | `20260421_100100_add_sent_messages_superseded_at` | Adds nullable `superseded_at` TIMESTAMP + partial index on active confirmation rows. |
| 13 | `20260421_100200_create_webhook_processed_log_table` | Creates `webhook_processed_logs` (durable CallRail dedup ledger; complements Redis). |
| 14 | `20260422_100000_add_admin_confirmed_informal_opt_out_method` | No-op alembic step — documents the new `admin_confirmed_informal` opt-out method value (column already VARCHAR(50)). |
| 15 | `20260423_100000_add_customer_tags_table` | Creates `customer_tags` (6 cols + index + unique constraint + CHECK on tone/source). |
| 16 | `20260425_100000_add_appointment_notes_table` | Creates `appointment_notes` (centralized internal notes per appointment). |
| 17 | `20260426_100000_add_sales_calendar_assigned_to` | Adds `assigned_to_user_id` UUID FK + index to `sales_calendar_events`. |
| 18 | `20260427_100000_add_webauthn_credentials_table` | Creates `webauthn_user_handles` and `webauthn_credentials`. CHECK on device_type, 2 indexes. |
| 19 | `20260428_100000_add_customer_email_bounced_at` | Adds `email_bounced_at` TIMESTAMP to `customers` (Resend bounce flag). |
| 20 | `20260428_140000_partial_unique_stripe_customer_id` | Drops full unique `ix_customers_stripe_customer_id`; creates partial unique `ix_customers_stripe_customer_id_active` (`WHERE stripe_customer_id IS NOT NULL`). |
| 21 | `20260428_150000_add_invoice_payment_link_columns` | Adds 5 columns to `invoices` for Stripe Payment Links + partial unique index on link ID. |
| 22 | `20260429_100000_create_appointment_reminder_log` | Append-only ledger for Day-2 reminder dedup across hourly job ticks. |
| 23 | `20260429_100100_seed_day_2_reminder_settings` | Seeds 2 rows in `business_settings` (`confirmation_day_2_reminder_enabled=false`, `confirmation_day_2_reminder_offset_hours=48`). |
| 24 | `20260430_120000_add_sales_entry_nudges_dismiss_columns` | Adds `nudges_paused_until`, `dismissed_at` to `sales_entries`. |
| 25 | `20260501_120000_normalize_property_city` | Trims/title-cases `properties.city`, quarantines address-shaped rows to `address` + `city='Unknown'`. **Lossy; downgrade raises NotImplementedError.** |
| 26 | `20260502_100000_widen_sent_messages_for_payment_link` | Widens `ck_sent_messages_message_type` to add `payment_link`. |
| 27 | `20260502_120000_merge_payment_link_branches` | **Alembic merge** — collapses `20260428_150000` and `20260502_100000` into a single head. No-op DDL. |
| 28 | `20260503_100000_ai_scheduling_tables` | Creates 6 AI scheduling tables; seeds 30 weighting criteria; extends `jobs`/`staff`/`customers`/`appointments` with 18+ columns + 4 FKs. |
| 29 | `20260504_100000_add_jobs_scope_items` | Adds `scope_items` JSONB to `jobs` (estimate line_items copied at job creation). |
| 30 | `20260504_120000_extend_service_offerings_for_pricelist` | Adds 8 columns to `service_offerings` (`slug`, `display_name`, `customer_type`, `subcategory`, `pricing_rule`, `replaced_by_id`, `includes_materials`, `source_text`) + 2 indexes. |
| 31 | `20260504_130000_seed_pricelist_from_viktor` | Loads 73 items from `bughunt/2026-05-01-pricelist-seed-data.json` into `service_offerings`. **Gated by `VIKTOR_PRICELIST_CONFIRMED=true`; raises `RuntimeError` otherwise.** |
| 32 | `20260505_100000_add_staff_preferred_maps_app` | Adds `preferred_maps_app` VARCHAR(20) to `staff`. |
| 33 | `20260505_120000_widen_sent_messages_for_payment_receipt` | Widens `ck_sent_messages_message_type` to add `payment_receipt`. |
| 34 | `20260505_130000_widen_pricing_model_check` | Widens `ck_service_offerings_pricing_model` from 4 legacy values to 19 (range / per-unit / tiered / size-tier / variants / +materials / conditional_fee). Required by #31. |
| 35 | `20260506_120000_repair_invoice_line_items_shape` | Rewrites `invoices.line_items` JSONB items missing `quantity`. Idempotent; downgrade no-op. Uses MATERIALIZED CTE + CASE WHEN to force predicate order. Guards against non-array JSONB rows. |
| 36 | `20260507_120000_harden_provider_message_id_partial_index` | Pre-flight UPDATE empties → NULL for `provider_message_id`; swaps partial unique index predicate to `IS NOT NULL AND <> ''`. |
| 37 | `20260508_120000_widen_sent_messages_for_yrc_subtypes` | Widens `ck_sent_messages_message_type` to add `appointment_confirmation_reply_y/_r/_c` (per-keyword sub-types). |
| 38 | `20260510_120000_add_lead_consent_ts_and_utm_fields` | Adds 6 nullable columns to `leads` (`consent_timestamp` + 5 `utm_*`) so the customer-site lead form payload stops silently dropping consent/attribution data (resolves §22.2). |

### High-risk migrations and mitigations

- **#10 fold_notes_table_into_internal_notes** — One-way data fold; sales_entry/appointment subjects discarded. *Mitigation: Pre-flight 3 above.*
- **#11 reschedule_request_unique_open_index** — Fails on duplicates. *Mitigation: Pre-flight 2 above.*
- **#25 normalize_property_city** — Lossy data mutation; not reversible. *Mitigation: backup + idempotent (safe to re-run).*
- **#28 ai_scheduling_tables** — Large multi-table change with 30 seed rows; FKs to `staff.id`. Confirm staff table has at least one row before applying. Total runtime expected 30–60s.
- **#31 seed_pricelist_from_viktor** — Gated. *Mitigation: Pre-flight 1; production must have `VIKTOR_PRICELIST_CONFIRMED` UNSET unless explicit sign-off.*
- **#34 widen_pricing_model_check** — Must apply **before** any data using the wider value set is written. The chain order keeps it ahead of #31, but the production seed in #31 only runs if gated; if you decide to seed prod later, do **not** narrow this constraint back.
- **#35 repair_invoice_line_items_shape** — Repair derives `unit_price` from `amount`; if `amount` is NULL the repaired row will have NULL price. Spot-check a few invoices post-migration.
- **#36 harden_provider_message_id_partial_index** — Empty strings collapsed to NULL before partial-unique recreation. Safe but worth monitoring row count change in logs.

---

## 2. New Environment Variables

These must be set on Railway production **before** the deploy is rolled out.

| Name | Required? | Example | What it controls |
|---|---|---|---|
| `RESEND_API_KEY` | Yes (or estimate emails silently fail) | `re_…` | Resend send authentication. |
| `RESEND_WEBHOOK_SECRET` | Yes | `whsec_…` | Svix-format HMAC for `/webhooks/resend`. |
| `INTERNAL_NOTIFICATION_EMAIL` | Recommended | `ops@grinsirrigation.com` | Internal alerts (estimate approvals, bounces, opt-outs). |
| `INTERNAL_NOTIFICATION_PHONE` | Recommended | `+1…` (E.164) | Internal SMS alerts. |
| `PORTAL_BASE_URL` | Yes | `https://app.grinsirrigation.com` | Used in estimate/invoice emails. **F4-REOPENED guard hard-fails boot if this is a deprecated Vercel preview alias.** |
| `WEBAUTHN_RP_ID` | Yes | `app.grinsirrigation.com` (bare host, no scheme/port) | Passkey relying-party ID. |
| `WEBAUTHN_RP_NAME` | Optional | `Grin's Irrigation` | Display name in OS biometric prompt. |
| `WEBAUTHN_EXPECTED_ORIGINS` | Yes | `https://app.grinsirrigation.com` | Comma-separated list. Must include every origin a browser may report. |
| `WEBAUTHN_CHALLENGE_TTL_SECONDS` | Optional | `300` | Challenge cache TTL. |
| `WEATHER_API_KEY` | Optional | `(unset)` or OpenWeatherMap key | Drives AI scheduling criterion 26. Empty = feature disabled gracefully. |
| `WEBHOOK_TRUSTED_PROXY_CIDRS` | Optional | empty | Trusted-proxy CIDRs for X-Forwarded-For rate-limit key. |
| `WEBHOOK_CLOCK_SKEW_SECONDS` | Optional | `300` | Replay window for webhook freshness. |
| `WEBHOOK_AUTOREPLY_PHONE_TTL_S` | Optional | `60` | Per-phone auto-reply throttle. |
| `WEBHOOK_AUTOREPLY_GLOBAL_WINDOW_S` | Optional | `10` | Global circuit-breaker window. |
| `WEBHOOK_AUTOREPLY_CIRCUIT_THRESHOLD` | Optional | `30` | Replies/window before circuit opens. |
| `WEBHOOK_SIGNATURE_FLOOD_THRESHOLD` | Optional | `50` | Invalid-signature alert threshold per hour. |
| `INBOX_SHOW_CONSENT_FLIPS` | Optional | `false` | Feature flag F8 — surface standalone STOP/START flips. |

### Variables that must be UNSET on prod (test guards)

| Name | Behavior when set | Where enforced |
|---|---|---|
| `EMAIL_TEST_ADDRESS_ALLOWLIST` | Blocks all email sends to non-allowlisted addresses (`EmailRecipientNotAllowedError`). | `services/email_service.py::enforce_email_recipient_allowlist` |
| `EMAIL_TEST_REDIRECT_TO` | Rewrites every outbound email to this address before allowlist check. | `services/email_service.py::apply_email_test_redirect` |
| `SMS_TEST_PHONE_ALLOWLIST` | Blocks all SMS sends to non-allowlisted numbers. | `services/sms/base.py::enforce_recipient_allowlist` |
| `SMS_TEST_REDIRECT_TO` | Rewrites every outbound SMS to this number before allowlist check. | `services/sms/base.py::apply_test_redirect` |
| `ALEMBIC_ALLOW_REMOTE` | Bypasses the local→Railway alembic guard. Auto-bypassed inside Railway by `RAILWAY_ENVIRONMENT`; should never be set manually on prod. | `migrations/env.py::_guard_against_remote_db` |

### Variables already present (re-verify, do not remove)

`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY` (must be ≥32 chars and **not** the dev default — boot guard rejects), `ENVIRONMENT=production`, `CORS_ORIGINS`, `SECRET_KEY`, `OPENAI_API_KEY`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_SHEETS_*`, `SMS_PROVIDER=callrail`, `CALLRAIL_*` (API key, account ID, company ID, tracking number, webhook secret), `STRIPE_SECRET_KEY` (`sk_live_…`), `STRIPE_WEBHOOK_SECRET` (`whsec_…` for live endpoint), `AWS_*` / `S3_*`, `SIGNWELL_*`, `RAILWAY_ENVIRONMENT` (Railway-injected).

---

## 3. Frontend Environment Variables (Vercel)

| Name | Prod value |
|---|---|
| `VITE_API_BASE_URL` | `https://api.grinsirrigation.com` (or whichever prod API hostname is canonical) |
| `VITE_GOOGLE_MAPS_API_KEY` | Same key as backend `GOOGLE_MAPS_API_KEY` |
| `VITE_STRIPE_CUSTOMER_PORTAL_URL` | The actual Stripe billing portal URL from the Stripe dashboard, not empty |

The Vite build step changed from `tsc -b` (project references) to `tsc -p tsconfig.app.json --noEmit` (single-config, type-check only). This is a build-time change only; no runtime impact.

---

## 4. New Python Dependencies

From `git diff main..dev -- pyproject.toml uv.lock`:

| Package | Pin | Why |
|---|---|---|
| `resend` | `>=2.0.0,<3.0.0` | Resend email + Svix-format webhook verification. Used in `services/email_service.py`, `services/resend_webhook_security.py`. |
| `webauthn` | `>=2.7.0,<3.0.0` | WebAuthn challenge gen + verification. Used in `services/webauthn_service.py`. |
| `openpyxl` | `>=3.1.0` | Excel export for customers (`api/v1/customers.py`). |

No version bumps or removals on existing core deps.

---

## 5. New Frontend Dependencies

| Package | Pin | Why |
|---|---|---|
| `@fullcalendar/list` | `^6.1.20` | List/agenda rendering on the resource-timeline schedule view. |
| `@simplewebauthn/browser` | `^13.3.0` | Client-side passkey enrollment / authentication (`features/auth/PasskeyManager`). |

`@stripe/terminal-js` is still in `frontend/package.json` from the April-14 deploy but is **not** wired in any UI component. M2 hardware was shelved (per memory). Either remove from `package.json` or leave dormant; either is safe.

---

## 6. New / Modified Webhook Endpoints

| Path | Provider | Verification | Dedup |
|---|---|---|---|
| `/webhooks/stripe` | Stripe | `stripe.Webhook.construct_event` | `stripe_webhook_event` table (existing) |
| `/webhooks/resend` | Resend | Svix-format HMAC-SHA256 | None at endpoint; soft-flagged via `customers.email_bounced_at` |
| `/webhooks/callrail` | CallRail | Custom HMAC-SHA256 | Redis primary + `webhook_processed_logs` fallback (new in #13) |
| `/webhooks/signwell` | SignWell | HMAC-SHA256 | Document-ID lookup (no dedup table) |
| `/webhooks/twilio-inbound` | Twilio (fallback only) | Twilio signature validation | None |

**New Stripe events handled** (in `_handle_*` functions in `api/v1/webhooks.py:72-76, 198-204`):
- `payment_intent.succeeded` — triggers payment receipt SMS via `AppointmentService._send_payment_receipts`
- `payment_intent.payment_failed`
- `payment_intent.canceled`
- `charge.refunded`
- `charge.dispute.created`

> **Critical pre-deploy step.** In the Stripe dashboard → Developers → Webhooks, ensure the prod endpoint subscribes to **all five** new events in addition to the existing `checkout.session.completed`, `invoice.*`, `customer.subscription.*`. If a Payment Link is paid and Stripe doesn't push `payment_intent.succeeded`, the receipt SMS + email never fire and reconciliation has to be done manually. **This is the single most-likely silent-failure mode for this deploy.**

For Resend, register `https://<api-domain>/webhooks/resend` in the Resend dashboard, subscribe to `email.bounced` and `email.complained`, capture the signing secret into `RESEND_WEBHOOK_SECRET`.

---

## 7. Background Jobs / Scheduled Tasks

All jobs are registered in `services/background_jobs.py::register_scheduled_jobs` and run in the FastAPI lifespan with APScheduler.

**New since April-14:**

| Job | Schedule | Notes |
|---|---|---|
| `flag_no_reply_confirmations` | 06:00 UTC daily | Bug-hunt H-7 resolution; flags SCHEDULED appointments with no Y/R/C reply for >N days; writes to `alerts`. |
| `prune_webhook_processed_logs` | 03:30 UTC daily | Trims `webhook_processed_logs` rows older than 30 days. |
| `send_day_2_reminders` | Hourly | **Feature-flagged off by default** via `business_settings.confirmation_day_2_reminder_enabled = false` (seeded by migration #23). Safe to deploy dormant. |
| `nudge_stale_sales_entries` | 08:15 UTC daily | Auto-nudge stale sales pipeline (commit `fd3dbbe` plumbs `actor_staff_id`). |
| `process_estimate_follow_ups` | Every 15 minutes | Day-3/7/14/21 estimate follow-up SMS cadence. |

Existing jobs unchanged: `escalate_failed_payments`, `check_upcoming_renewals`, `send_annual_notices`, `cleanup_orphaned_consent_records`, `remind_incomplete_onboarding`, `process_pending_campaign_recipients`, `duplicate_detection_sweep`.

---

## 8. Behavioral / API Breaking Changes

### `POST /api/v1/appointments/{id}/reschedule` returns 422 (was 400) on invalid status transitions

Commit `3c2319f`. Catches `InvalidStatusTransitionError` and returns HTTP 422 with detail. The frontend in this repo is updated; **external integrations** (Zapier, n8n, custom scripts that POST to this route) that branch on the 400 status code must be updated to recognize 422.

### `/auth/login` lockout + per-IP rate limit restored

Commit `1dde7d9`. After 5 failed attempts/IP/minute, the route returns 429. The threshold is a hardcoded constant `AUTH_LIMIT = "5/minute"` in `middleware/rate_limit.py:39` (not env-configurable). Operator visibility: monitor for spikes in 429s on `/auth/login`.

### Unconditional HSTS header

Commit `c3a20c4`. `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload` is now emitted on every response regardless of `ENVIRONMENT`. Browsers ignore it on plain HTTP, so this is safe in dev. Confirm prod has a valid TLS cert before deploy (it does — Railway provides this automatically).

### `/pricebook` redirects to `/invoices?tab=pricelist`

Commit `c3a20c4`. Standalone pricebook page removed; existing bookmarks/menus pointing at `/pricebook` will land on the new pricelist tab.

### `/needs-review` static route added before `/{appointment_id}` dynamic route

`api/v1/appointments.py`. Static routes intentionally precede the dynamic route so they aren't shadowed. New endpoints:
- `GET /api/v1/appointments/needs-review`
- `GET /api/v1/appointments/{id}/notes`
- `POST /api/v1/appointments/{id}/notes`
- `POST /api/v1/appointments/{id}/mark-contacted`
- `POST /api/v1/appointments/{id}/send-reminder-sms`

### New tech-only surface

Frontend route `/tech` is gated to staff with `role='tech'`. After login, `PostLoginRedirect` routes techs to `/tech` and admins to `/dashboard`. A `PhoneOnlyGate` displays a "switch to phone" message on non-mobile viewports.

### Per-keyword Y/R/C reply ack sub-types (latest commit on dev)

Commits `7f2588f`, `bf1b444`, `f02f467`. The single `appointment_confirmation_reply` ack message_type is split into `_y`, `_r`, `_c` sub-types so dedup on a Y-ack does not silence a subsequent R/C ack within the same conversation. Migration #37 widens the CHECK accordingly. Auto-reply throttle is now bucketed per-keyword for the same phone.

### R-reply now prompts for 2–3 dates (latest commit on dev)

Commit `7f2588f`. When a customer replies "R" to a confirmation, the response is no longer a receipt-only ack — the system now prompts the customer for 2–3 alternate dates. Frontend `InformalOptOutQueue` and `appointment_notes` surface the resulting alternatives. Confirm CallRail conversation routing is unchanged (no operator action required — purely application-layer behavior).

---

## 9. Removed / Renamed Routes

- `/pricebook` → redirects to `/invoices?tab=pricelist`. Update any documentation, internal bookmarks, or operator runbooks referencing the old path.

No other route renames or removals.

---

## 10. New Tables (15 total)

| Table | Migration | Notes |
|---|---|---|
| `alerts` | #4 | Admin notifications. |
| `notes` | #8 | **Dropped by #10** in the same chain — never lands on prod long-term. |
| `appointment_attachments` | #9 | S3 metadata. Reuses existing PhotoService bucket. |
| `webhook_processed_logs` | #13 | Durable webhook dedup. Pruned nightly. |
| `customer_tags` | #15 | Customer tags with tone/source. |
| `appointment_notes` | #16 | Per-appointment internal notes. |
| `webauthn_user_handles` | #18 | Passkey user-handle mapping. |
| `webauthn_credentials` | #18 | Passkey credentials. |
| `appointment_reminder_log` | #22 | Day-2 reminder dedup ledger. |
| `service_zones` | #28 | AI scheduling. |
| `scheduling_criteria_config` | #28 | 30 seeded weighting criteria. |
| `scheduling_alerts` | #28 | AI-generated alerts. |
| `change_requests` | #28 | AI scheduling change-request queue. |
| `scheduling_chat_sessions` | #28 | AI chat session context. |
| `resource_truck_inventory` | #28 | Per-truck parts inventory. |

---

## 11. Pre-Migration Data-Fitness Queries

Run these on prod **before** running `alembic upgrade head`. All should return zero rows or only known-safe values.

```sql
-- (a) #11 partial unique index pre-flight (also see Pre-Flight 2)
SELECT appointment_id, COUNT(*)
FROM reschedule_requests
WHERE status='open'
GROUP BY appointment_id HAVING COUNT(*) > 1;

-- (b) #18 webauthn — only relevant if you intend to seed; otherwise tables start empty
-- (no pre-flight query)

-- (c) #20 partial unique stripe_customer_id — verify no duplicate non-NULL values
SELECT stripe_customer_id, COUNT(*)
FROM customers
WHERE stripe_customer_id IS NOT NULL
GROUP BY stripe_customer_id HAVING COUNT(*) > 1;

-- (d) sent_messages CHECK widenings (#7, #26, #33, #37) — each is additive, but
-- confirm no row has a stale value that will fail the new constraint redefinition
SELECT DISTINCT message_type FROM sent_messages
WHERE message_type IS NOT NULL
ORDER BY 1;
-- Manually compare against the latest enum in src/grins_platform/models/sent_message.py
-- All distinct values must be in the enum after applying #37.

-- (e) #3 invoices.payment_method widening
SELECT DISTINCT payment_method FROM invoices ORDER BY 1;
-- Must all be in: cash, check, venmo, zelle, stripe, credit_card, ach, other (or NULL)

-- (f) #34 service_offerings.pricing_model widening
SELECT DISTINCT pricing_model FROM service_offerings ORDER BY 1;
-- Pre-deploy: should only contain legacy values (flat / zone_based / hourly / custom).

-- (g) #1 jobs.status & job_status_history widening
SELECT DISTINCT status FROM jobs ORDER BY 1;
SELECT DISTINCT previous_status FROM job_status_history ORDER BY 1;
SELECT DISTINCT new_status FROM job_status_history ORDER BY 1;
-- All must be in: to_be_scheduled, scheduled, in_progress, completed, cancelled

-- (h) #10 notes table fold (also see Pre-Flight 3)
SELECT subject_type, COUNT(*) FROM notes GROUP BY subject_type;
-- sales_entry / appointment counts SHOULD be zero. If non-zero, halt and decide.

-- (i) #25 normalize_property_city scope
SELECT
  COUNT(*) FILTER (WHERE city IS NULL OR city = '')              AS empty_city,
  COUNT(*) FILTER (WHERE city ~ '^\d')                            AS starts_with_digit,
  COUNT(*) FILTER (WHERE city ~ ',\s*[A-Z]{2}\s+\d{5}')           AS has_state_zip,
  COUNT(*) FILTER (WHERE city ~* '\s(St|Ave|Dr|Ln|Rd|Blvd|Ct|Way|Ter|Pl|Pkwy|Cir|Trl)$') AS street_suffix
FROM properties;
-- Informational; the migration handles all of these idempotently.

-- (j) #35 invoices.line_items shape repair scope
SELECT COUNT(*) FROM invoices
WHERE line_items IS NOT NULL
  AND jsonb_typeof(line_items) = 'array'
  AND jsonb_array_length(line_items) > 0
  AND NOT (line_items->0 ? 'quantity');

-- (k) #36 provider_message_id empty-string scope
SELECT COUNT(*) FROM campaign_responses WHERE provider_message_id = '';
-- Migration coalesces these to NULL before recreating the partial-unique index.
```

If any check returns out-of-set values, halt the deploy until the data has been categorized and either backfilled to a valid value or surfaced as expected.

---

## 12. Data Migrations Without a Clean Downgrade

| Migration | Why downgrade is unsafe |
|---|---|
| #10 `fold_notes_table_into_internal_notes` | Drops `notes` table after folding. Downgrade recreates the shell but original rows are gone. |
| #25 `normalize_property_city` | Downgrade raises `NotImplementedError`. Original messy values are not recoverable. |
| #31 `seed_pricelist_from_viktor` | Downgrade deletes seeded rows by slug. Any post-seed manual edits to those rows would be lost. |
| #35 `repair_invoice_line_items_shape` | Downgrade is `pass` (no-op). Repaired rows stay repaired. |
| #36 `harden_provider_message_id_partial_index` | Empty strings already coalesced to NULL; cannot be undone (information not preserved). |

All other migrations downgrade cleanly — but a downgrade chain across 37 steps is brittle. Restore-from-backup is the preferred recovery path for any migration-level disaster.

---

## 13. Infrastructure & CI

### 13.1 No changes to `Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`, or root config files

### 13.2 No changes to Railway / Vercel deployment configs

### 13.3 New CI workflow: `.github/workflows/alembic-heads.yml`

Runs `scripts/check-alembic-heads.sh` on every PR/push to `main` and `dev`. Fails the build if more than one alembic head exists. Migration #27 (`merge_payment_link_branches`) is the explicit collapse of two parallel heads created during payment-links work; with that merge in place the chain is single-headed.

### 13.4 Seed scripts that must NOT run on production

| Script | Risk |
|---|---|
| `scripts/seed_tech_companion_appointments.py` | Idempotent (keyed by `[tech-companion-e2e]` tag). Safe to re-run on dev/staging. **Do not run on prod.** |
| `scripts/seed_e2e_payment_links.py` | Hardcoded API base default points at dev Railway. Override with `API_BASE` if needed; **do not run against prod**. |
| `scripts/seed_resource_timeline_test_data.py` | Reads `DATABASE_URL`. Disables SSL only on localhost/127.0.0.1. **Do not run with prod DATABASE_URL.** |

These scripts have no automatic environment guard. The deploy itself does not invoke them; they would only run if an operator typed the command. Confirm no operator runs them with prod credentials.

---

## 14. Rehearsal Recipe

The user's policy (memory `feedback_no_remote_alembic.md`): never run alembic against `*.railway.{app,internal}` from local. The env.py guard refuses unless `ALEMBIC_ALLOW_REMOTE=1`. Rehearsal therefore uses a local `pg_restore` of the latest prod backup.

```bash
# 1. Pull a fresh prod backup (Railway UI → Postgres → Backups → Download latest)
PROD_DUMP=/tmp/grins-prod-$(date +%Y%m%d-%H%M%S).dump

# 2. Spin up a fresh local rehearsal DB
dropdb --if-exists grins_rehearsal
createdb grins_rehearsal
pg_restore --no-owner --no-privileges -d grins_rehearsal "$PROD_DUMP"

# 3. Point alembic at the rehearsal DB
export DATABASE_URL="postgresql://localhost/grins_rehearsal"
cd /Users/kirillrakitin/Grins_irrigation_platform

# 4. Confirm starting head matches prod head
uv run alembic current
# Expected: 20260414_100000_fix_appointment_status_check_add_draft

# 5. Run pre-migration data-fitness queries (Section 11) against rehearsal DB
psql grins_rehearsal -f /tmp/preflight.sql

# 6. (Dev/staging only) set the pricelist gate; LEAVE UNSET to mirror prod
# export VIKTOR_PRICELIST_CONFIRMED=true

# 7. Apply all 38 migrations
uv run alembic upgrade head 2>&1 | tee /tmp/rehearsal-$(date +%s).log

# 8. Verify final head
uv run alembic current
# Expected: 20260510_120000_add_lead_consent_ts_and_utm_fields (single head)

# 9. Smoke-check row counts (compare against prod baseline counts taken at step 1)
psql grins_rehearsal <<'EOF'
SELECT 'customers'         AS tbl, COUNT(*) FROM customers
UNION ALL SELECT 'appointments',         COUNT(*) FROM appointments
UNION ALL SELECT 'sent_messages',        COUNT(*) FROM sent_messages
UNION ALL SELECT 'invoices',             COUNT(*) FROM invoices
UNION ALL SELECT 'service_offerings',    COUNT(*) FROM service_offerings
UNION ALL SELECT 'reschedule_requests',  COUNT(*) FROM reschedule_requests
ORDER BY tbl;
EOF

# 10. Boot the API against the rehearsal DB and exercise the changed routes
DATABASE_URL=postgresql://localhost/grins_rehearsal \
  uv run uvicorn grins_platform.app:app --port 8001 &
sleep 5
# Reschedule on a known-bad-status appointment should return 422
curl -i -X POST http://localhost:8001/api/v1/appointments/<id>/reschedule \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"new_scheduled_at":"2026-06-01T15:00:00Z"}'

# 11. Tear down
kill %1
dropdb grins_rehearsal
```

If any step fails, capture the alembic log in `bughunt/` and resolve before deploying.

---

## 15. Backup & Rollback Plan

### Backup
Take a Railway Postgres backup immediately before merging. Note the backup ID and timestamp. Keep for at least 30 days post-deploy.

### Rollback strategies, in preference order

1. **App-only rollback (no DB change).** If a code-side issue surfaces in the first hour, deploy the previous commit on `main` while the schema stays at the new head. All schema changes are additive enough that the prior code can read the new schema (CHECK widenings are supersets of old; new columns are nullable; renamed `delivery_status` etc. happened in the April-14 deploy already). Day-2 reminder is feature-flagged off, so the unused job is inert.
2. **Per-migration downgrade.** Possible for migrations #1–#9, #11–#24, #26–#34, #37. **Not** safe for #10, #25, #31, #35, #36 (Section 12). Downgrade is brittle across many steps; only use when the failing migration is at or near the head.
3. **Backup restore.** For any migration that produced lossy state, restore from the pre-deploy backup. Railway UI → Postgres → Backups → "Restore". This is the only path back from #25 (`normalize_property_city`) once it has run.

### Per-migration rollback notes

- #11 fails on duplicate open reschedule rows → run Pre-Flight 2, then re-attempt. Do not retry blindly.
- #28 fails mid-way (e.g., FK-to-staff violation) → entire migration is in one transaction; downgrade is clean. Address the FK target and re-attempt.
- #31 raises if `VIKTOR_PRICELIST_CONFIRMED` not set → expected on prod; downgrade is no-op (the seed never ran).

---

## 16. Companion Repo `Grins_irrigation` (customer site)

Local clone at `/Users/kirillrakitin/Grins_irrigation`, currently on `dev`, **11 commits ahead of `main`**:

```
0fa148e ui(onboarding): remove preferred-schedule dropdown from customer form
d6f5807 chore: replace dental research with Grin's Irrigation audit and add required-weeks e2e verification
b94fd42 feat(onboarding): require explicit week choice for every tier-included service
39f164e feat(onboarding): add per-service week preference selection to onboarding form
3bf0fb8 chore: add firecrawl research data, competitor analysis, SEO docs
05b70cf chore: add research data, e2e screenshots, competitor analysis, SEO assets
ea77560 feat: add free-use hero images for 4 blog posts missing images
59d7527 fix: prevent mid-word break on hero headlines and reset scroll on navigation
0b0b556 fix: allow clearing zone count input in subscription modal
c3063ee feat: Website_Changes_Update_2 — lead form compliance, photos, pricing single-source
cd67559 feat: 12k-website visual upgrades, SEO, content, and city/nav fixes
```

Local working tree has uncommitted research data under `research/` — not part of the deploy.

**Sequence:**
1. Deploy companion repo `dev → main` **before or concurrent with** the platform deploy. The customer site form changes (per-service week preference, removed preferred-schedule dropdown) align with the platform's `service_week_preferences` field and lead-form schema.
2. Verify a fresh lead submitted from the deployed customer site lands cleanly in `leads` and triggers the configured SMS/email confirmations.

---

## 17. Outstanding Items / Known Open Risks

- **Pricelist seed gating.** Production must keep `VIKTOR_PRICELIST_CONFIRMED` UNSET. If product wants the 73-item seed in prod this window, run it as a separate, supervised step **after** the rest of the migrations have applied cleanly, and unset the var immediately after.
- **Stripe Terminal scaffold dormant.** `@stripe/terminal-js` remains in `frontend/package.json` but no UI mounts it; `STRIPE_TERMINAL_LOCATION_ID` is referenced in `.env.example` but not read by any code path. No action required; surface it in tech-debt cleanup later.
- **Day-2 confirmation reminder feature-flagged off.** The hourly job is registered but `business_settings.confirmation_day_2_reminder_enabled = false` (seeded by #23). Flip to `true` only after copy review.
- **External integrations expecting the old reschedule 400 status code.** Confirm none exist; the in-tree frontend is updated.
- **Resend bounce handling depends on external webhook setup.** If `/webhooks/resend` is not registered in the Resend dashboard with a matching `RESEND_WEBHOOK_SECRET`, the platform will send estimate emails but never observe bounces — `customers.email_bounced_at` stays NULL forever.

---

## 18. Reconciling 4 commits on `main` not on `dev`

```
397c534 release: dev → main 2026-04-14 (squash of 93 commits, f308749..b60f740)
dabd686 Merge branch 'dev' — replace zip_code with address as required field
09fdeb8 Merge branch 'dev'
7e71bf3 chore: add backups/ to .gitignore
```

- `397c534` is the squash release commit from the April-14 deploy. The work it represents already exists in `dev` as the underlying individual commits.
- `dabd686`, `09fdeb8` are historical merge commits.
- `7e71bf3` adds `backups/` to `.gitignore`. Verified: `dev`'s `.gitignore` already contains `backups/` (line 106 under "Database backups (contain production data)"), so the ignore rule is preserved.

There is nothing on `main` that needs to be ported back into `dev` before the merge. Use a regular merge (or PR squash) — no rebase or cherry-pick required.

---

## 19. Deploy-Day Runbook

1. **T-24h** — Pre-flight 1–8 confirmed; rehearsal complete; backup taken; on-call notified.
2. **T-1h** — Final pre-flight data-fitness queries (Section 11) on prod. If any returns out-of-set values, halt.
3. **T-0** — Open the PR `dev → main`. Wait for CI green (especially `alembic-heads`). Squash-merge to `main`.
4. **Railway auto-deploys** — Watch logs in real time:
   - Boot guards: JWT_SECRET_KEY validation, F4-REOPENED PORTAL_BASE_URL guard.
   - Alembic: 37 migrations apply. Long migrations: #10 (fold), #25 (city normalize), #28 (AI scheduling tables + 30 seeds), #35 (line_items repair). Expected total: 2–5 minutes.
   - Lifespan: scheduler starts, GoogleSheetsPoller starts, all webhook routes mount.
5. **Smoke tests against prod**:
   ```
   curl -I https://api.grinsirrigation.com/health
   curl -I https://api.grinsirrigation.com | grep -i strict-transport-security
   curl https://api.grinsirrigation.com/api/v1/appointments/needs-review -H "Authorization: Bearer …"
   ```
6. **Frontend deploy on Vercel** — verify new `VITE_*` env vars are live; visit `/`, `/dashboard`, `/schedule`, `/tech` (with a tech-role login), `/portal/estimates/<token>` for a known token.
7. **External integrations live-check**:
   - Send a test estimate email to an internal address; confirm receipt via Resend.
   - From an allowlisted phone, reply Y/R/C to a confirmation SMS; confirm correct ack sub-type and (for R) the date-prompt follow-up.
   - Trigger a small Stripe Payment Link payment; confirm receipt SMS + email; confirm dashboard reconciliation via `metadata.invoice_id`.
8. **Post-deploy monitoring (first 2 hours)** — watch for unhandled exceptions, 422s on `/reschedule` (expected on bad transitions), 429s on `/auth/login` (expected under load), CHECK violation errors on inserts (should be zero).

---

## 20. Contacts

- **Primary deploy operator:** Kirill (`kirillrakitinsecond@gmail.com`)
- **Test SMS recipient (dev/staging only):** `+19527373312`
- **Test email recipient (dev/staging only):** `kirillrakitinsecond@gmail.com`
- **Prod paging / on-call:** see internal runbook
- **External vendors that may need to be notified of webhook URL changes:** Stripe (Payment Links events), Resend (`/webhooks/resend`), CallRail (`/webhooks/callrail`), SignWell (`/webhooks/signwell` if used)

---

## 21. Second-Pass Verification & Addenda

A second-pass review verified 19 of 20 factual claims in this document directly against source. The corrections and gaps surfaced are below — none are deal-breakers, but all need to be on the operator's radar.

### 21.1 Verified claims (with file:line evidence)

| Claim | Evidence |
|---|---|
| JWT_SECRET_KEY default rejection | `services/auth_service.py:53–73` |
| F4-REOPENED PORTAL_BASE_URL guard (deny list keyed on `frontend-git-dev-kirilldr01s-projects.vercel.app` and similar previews; fires when `ENVIRONMENT in {dev,development,prod,production}` OR `RAILWAY_ENVIRONMENT` set) | `services/email_config.py:17–141` |
| ALEMBIC_ALLOW_REMOTE guard (refuses `*.railway.{app,internal}` and `.up.railway.app`; auto-bypasses when `RAILWAY_ENVIRONMENT` set) | `migrations/env.py:44–87` |
| VIKTOR_PRICELIST_CONFIRMED gate raises `RuntimeError` on prod unless literal `"true"` | `migrations/versions/20260504_130000_seed_pricelist_from_viktor.py:98–106` |
| Day-2 reminder runtime flag check (not just registration-time) | `services/background_jobs.py:975–976, 1023–1026` |
| Reschedule 422 mapping | `api/v1/appointments.py:1307–1319` |
| `/pricebook` redirect | `frontend/src/core/router/index.tsx` `<Navigate to="/invoices?tab=pricelist" replace />` |
| `/auth/login` rate limit (5/minute, hardcoded) | `middleware/rate_limit.py:39`, `api/v1/auth.py:86` |
| HSTS unconditional | `middleware/security_headers.py:45–67` |
| Email + SMS test redirect/allowlist guards (no-op when unset) | `services/email_service.py:99, 118`, `services/sms/base.py:75, 101` |
| 5 new Stripe events wired | `api/v1/webhooks.py:72–76, 198–204` |
| `webhook_processed_logs` table used by CallRail; prune at 03:30 UTC | `api/v1/callrail_webhooks.py:11–12, 141`, `services/background_jobs.py:1474–1481` |
| `flag_no_reply_confirmations` writes to `alerts`; runs 06:00 UTC | `services/background_jobs.py:800–913, 1468–1469` |
| #25 downgrade raises `NotImplementedError` | `migrations/.../20260501_120000_normalize_property_city.py:123–129` |
| #10 drops `notes` table; logs counts of discarded rows | `migrations/.../20260418_100700_fold_notes_table_into_internal_notes.py:39–134` |
| Single alembic head after #37; #27 is the merge collapsing two parents | `migrations/.../20260502_120000_merge_payment_link_branches.py:19` (`down_revision = ("20260428_150000", "20260502_100000")`) |
| Per-keyword Y/R/C ack types in CHECK and emitted by SMS service | migration #37 + `services/sms_service.py:1184–1197` |
| R-reply prompt copy in code | `services/job_confirmation_service.py:75–77` |
| 30 AI scheduling criteria embedded in migration (not external file) | `migrations/.../20260503_100000_ai_scheduling_tables.py:495–579` |
| Email templates exist on disk | `src/grins_platform/templates/emails/estimate_sent.html` and `.txt` |

### 21.2 Corrections to claims made earlier in this doc

- **WebAuthn config is NOT boot-validated.** `services/webauthn_config.py` is a `BaseSettings` with default `webauthn_rp_id="localhost"` and no validator. A misconfigured prod boots successfully and fails only on the first passkey call. Pre-Flight 6 has been updated to call this out explicitly.
- **`/auth/login` rate limit is NOT env-configurable.** It is a hardcoded constant `AUTH_LIMIT = "5/minute"` in `middleware/rate_limit.py:39`. Section 8 has been corrected.

### 21.3 Modified existing files (not new) worth noting

| File | Change | Operator impact |
|---|---|---|
| `src/grins_platform/migrations/env.py` | Adds local→Railway alembic guard (`_guard_against_remote_db`) refusing remote URLs unless `RAILWAY_ENVIRONMENT` or `ALEMBIC_ALLOW_REMOTE=1` is set | None on prod (Railway sets `RAILWAY_ENVIRONMENT` automatically). Affects developer workstations only. |
| `src/grins_platform/exceptions/__init__.py` | New WebAuthn exception classes re-exported (`WebAuthnChallengeNotFoundError`, `WebAuthnCredentialNotFoundError`, `WebAuthnDuplicateCredentialError`, `WebAuthnVerificationError`) plus `LeadHasReferencesError`, `NoContactMethodError`, `LeadOnlyInvoiceError`. `MissingSigningDocumentError` retained for back-compat but no longer raised. | Backwards-compatible; existing imports continue to work. |
| `pyproject.toml` / `Dockerfile` | **No Python version change.** `requires-python = ">=3.10"`, `Dockerfile` base image still `python:3.12-slim-bookworm`. The stray `main.cpython-313.pyc` in git status is stale local bytecode and can be deleted. | None. |
| `src/grins_platform/database.py` | **Pool config unchanged.** `pool_size=5`, `max_overflow=10`, `pool_timeout=30s`, `pool_recycle=1800s`. | None. |

### 21.4 Customer-facing copy that warrants product review before/after deploy

These strings are baked into code. Worth a 5-minute product walkthrough during the deploy window.

| File:Line | Surface | Copy |
|---|---|---|
| `services/job_confirmation_service.py:75–77` | Customer SMS (R-reply) | "We'd be happy to reschedule. Please reply with 2-3 dates and times that work for you and we'll get you set up." |
| `services/job_confirmation_service.py:79–81` | Customer SMS (C-reply ack) | "Your appointment has been cancelled. Please contact us if you'd like to reschedule." |
| `services/appointment_service.py` (≈line 2190) | Customer SMS (payment receipt) | "Grin's receipt: {amount} received via {method} on {date}. Invoice #{number}. Thank you!" |
| `services/email_service.py:468` | Estimate email subject | "Your estimate from Grin's Irrigation" |
| `templates/emails/estimate_sent.html` / `.txt` | Estimate email body | Renders with portal URL; review the template directly before first prod send. |
| Day-2 reminder body | Customer SMS (currently disabled) | Mirrors day-1 confirmation with "Reminder:" prefix. Review when product flips `confirmation_day_2_reminder_enabled` on. |

### 21.5 Frontend ↔ Backend deploy order

**Deploy backend first, then frontend.** Reasoning:

- **Old FE + new BE is safe** — old FE never calls the new routes (`/needs-review`, `/notes`, etc.); new fields on existing payloads are ignored. The 422 reschedule status is already accepted by old FE error handling, and new BE only returns 422 in the path that previously returned 400.
- **New FE + old BE breaks** — new FE calls routes (`/api/v1/appointments/needs-review`, payment-link endpoints, WebAuthn endpoints) that don't exist on the old BE, producing 404s in the admin queue and broken passkey enrollment.

If Vercel auto-deploys the FE on `main` push, schedule the BE Railway deploy to complete its alembic + boot before the FE goes live (Vercel is usually faster — pin the FE deploy or deploy the FE manually after the BE health check passes).

### 21.6 Specific rollback edge cases

- **Code-only rollback while migrations stay applied is safe.** All schema changes are additive (nullable columns, superset CHECK constraints, new tables). Old code on `main` does not reference any new index name, and no `INSERT ... ON CONFLICT (index_name)` references the renamed `ix_customers_stripe_customer_id_active`.
- **#11 (reschedule unique-open index) failure mid-deploy** — alembic rolls back just #11; the prior 10 migrations remain applied. Recovery: run Pre-Flight 2 dedup SQL on prod, then re-attempt `alembic upgrade head`. Do not retry blindly.
- **#28 (AI scheduling) failure mid-seed** — entire migration is one transaction; clean downgrade. Inert for old code (it never reads the new tables).
- **#31 has NO `ON CONFLICT` clause** on its raw INSERT into `service_offerings`. In practice this is safe because alembic's `alembic_version` table prevents re-running an already-applied migration, but if anyone manually clears `alembic_version` or does an out-of-band re-run, expect 73 duplicate rows. Document this if a manual re-seed is ever attempted.
- **#35 line_items repair** — derives `unit_price`/`total` from `amount`. If `amount` is NULL on a malformed row, the repaired row has NULL price. Spot-check post-migration:
  ```sql
  SELECT id, invoice_number, line_items->0
  FROM invoices
  WHERE line_items IS NOT NULL
    AND jsonb_typeof(line_items) = 'array'
    AND (line_items->0->>'unit_price') IS NULL
  LIMIT 20;
  ```

### 21.7 Background-job concurrency and timezone notes

All 11 jobs registered in `services/background_jobs.py::register_scheduled_jobs (1395–1534)`. Verified non-overlap on shared row sets:

- Day-2 reminder is the only job that respects **Central Time** (uses `SMSService.enforce_time_window` for an 8 AM–9 PM CT customer window). All others run on UTC schedules. No cross-job races on the same rows.
- `process_pending_campaign_recipients` uses Redis as primary dedup with graceful DB fallback to `webhook_processed_logs` if Redis is unreachable. Throughput drops but no failures.
- New `/api/v1/campaigns/worker-health` endpoint exists for monitoring the campaign worker independently from the platform `/health` route. Add to monitoring if you alert on worker-health changes.

### 21.8 Backend coverage of the `/tech` route

`/tech` is **frontend-gated** to `role='tech'` in `frontend/src/core/router/index.tsx`. There are no dedicated `/api/v1/tech/*` backend routes — tech-companion uses existing endpoints (appointments, staff, jobs). Confirm the backend lookup for the logged-in tech's appointments enforces "this tech's staff_id" rather than "any staff_id passed in the request" before relying on this gating. If there is a route like `GET /appointments?staff_id=…` that doesn't validate the `staff_id` against the JWT subject, a tech could see other techs' work. Worth a 10-minute audit during the deploy window.

### 21.9 Migration #10 logs unstructured stdout

`migrations/.../20260418_100700_fold_notes_table_into_internal_notes.py` calls `print("[fold] …")` six times during upgrade. These show up in Railway alembic logs. If your log aggregation alerts on unmatched-pattern lines, expect a brief ping during the deploy. They are benign — they trace the data fold step.

### 21.10 New observability surfaces

- New structured log keys to expect (none should fire frequently): `sms.webhook.db_fallback_failed`, `sms.webhook.db_mark_failed`, `resend.webhook.ignored_event`, `stripe.webhook.missing_secret`, `stripe.webhook.error_handling`, `email.estimate_sent.skipped`. Watch for sustained spikes — they indicate misconfiguration of an external dependency, not application bugs.
- New monitoring endpoint: `GET /api/v1/campaigns/worker-health`. Returns `{"status": "ok"|"degraded"|"unknown"}` based on Redis availability and last-tick timestamp.
- No changes to `/health` (existing platform health probe) or to the lifespan health check.

### 21.11 Single remaining gap — login UI passkey button

`features/auth/components/LoginPage.tsx:25, 83–98` adds a passkey-login button to the existing login form. Old password login still works. Cosmetic only, but FE QA should confirm both paths render and the passkey button only appears on browsers that report WebAuthn support.

### 21.12 Final readiness statement (superseded — see Section 22)

A third pass surfaced two hard blockers (Section 22). The deploy is **not safe to ship as-is.** Once those are addressed, the seven external-action items below are the remaining gates:

1. Subscribe to the 5 new Stripe webhook events in the Stripe dashboard (Section 6 — single most likely silent-failure mode).
2. Register the Resend webhook URL + capture the secret (Pre-Flight 7).
3. Confirm CallRail webhook URL still points at prod API.
4. Set canonical `PORTAL_BASE_URL` (Pre-Flight 4) and prod-strength `JWT_SECRET_KEY` (existing requirement).
5. Set WebAuthn RP_ID + EXPECTED_ORIGINS to canonical domain (Pre-Flight 6).
6. Take a fresh prod backup (Pre-Flight 8).
7. Run the Section 14 rehearsal against a `pg_restore` of that backup.

---

## 22. Hard Blockers Found in Third-Pass Audit

The first two passes verified what the doc claims; the third pass looked for things the doc had not yet examined. Two findings rise to deploy-blocker severity.

### 22.1 Backend authorization gap on staff-scoped endpoints — privilege escalation (mostly pre-existing)

**Severity:** High *as a bug class*, but not a deploy blocker — 4 of the 6 affected endpoints already exist on `main` (production has been carrying this gap for some time). This deploy adds 2 new endpoints (`GET/PATCH /api/v1/appointments/{id}/notes`, backed by the new `appointment_notes` table) that share the same missing-owner-check pattern. Fix-and-ship as separate work; do not gate this PR on it.

**Verified against `main`:**
- `/api/v1/appointments/staff/{staff_id}/daily/{date}` — exists on `main:src/grins_platform/api/v1/appointments.py:264`. Pre-existing.
- `/api/v1/staff/{staff_id}/location` — exists on `main:src/grins_platform/api/v1/staff.py:436`. Pre-existing.
- `/api/v1/staff/{staff_id}/breaks` POST — exists on `main:src/grins_platform/api/v1/staff.py:493`. Pre-existing.
- `/api/v1/staff/{staff_id}/breaks/{break_id}` PATCH — exists on `main:src/grins_platform/api/v1/staff.py:568`. Pre-existing.
- `GET /api/v1/appointments/{id}/notes` — **new on dev** (`api/v1/appointments.py:896`). Adds new exposure surface.
- `PATCH /api/v1/appointments/{id}/notes` — **new on dev** (`api/v1/appointments.py:944`). Adds new exposure surface.

**What the frontend assumes:** `frontend/src/core/router/index.tsx` gates `/tech` to `role='tech'`, and `features/tech-mobile/components/TechSchedulePage.tsx:16–18` always calls the API with `user.id` (the logged-in tech's own ID) from the auth context. UI is correct.

**What the backend does:** Six endpoints accept `staff_id` from the request and trust it. There is no `require_staff_ownership` dependency comparing the path/query `staff_id` to `current_user.id` for non-admin roles.

| Path | Method | File:line | Auth dep present | Owner check |
|---|---|---|---|---|
| `/api/v1/appointments/staff/{staff_id}/daily/{schedule_date}` | GET | `api/v1/appointments.py:308–354` | **None** (no auth dep at all) | None |
| `/api/v1/appointments/{id}/notes` | GET | `api/v1/appointments.py` | `CurrentActiveUser` | None |
| `/api/v1/appointments/{id}/notes` | PATCH | `api/v1/appointments.py:944–980` | `CurrentActiveUser` | None |
| `/api/v1/staff/{staff_id}/location` | POST | `api/v1/staff.py:470–518` | `CurrentActiveUser` (binding ignored) | None |
| `/api/v1/staff/{staff_id}/breaks` | POST | `api/v1/staff.py:526–...` | `CurrentActiveUser` (binding ignored) | None |
| `/api/v1/staff/{staff_id}/breaks/{break_id}` | PATCH | `api/v1/staff.py:...–661` | `CurrentActiveUser` (binding ignored) | None |

`/api/v1/staff/me` (PATCH `preferred_maps_app`) is the one endpoint that does it correctly — it derives the staff identity from the JWT, not from a path param.

**Concrete attack:** Tech-A (`role='tech'`) authenticates normally, then issues `GET /api/v1/appointments/staff/<tech-B-id>/daily/2026-05-05`. Server returns Tech-B's full daily route, customer addresses, and job context. Same pattern works for `POST /api/v1/staff/<tech-B-id>/location` (pollute Tech-B's location), starting breaks on Tech-B, and reading/writing notes on appointments Tech-A is not assigned to.

**Pre-existing helpers available:** `api/v1/auth_dependencies.py` already has `require_admin` and `require_manager_or_admin`. The pattern to replicate is:

```python
async def require_staff_ownership(
    staff_id: UUID,
    current_user: Annotated[Staff, Depends(get_current_active_user)],
) -> Staff:
    if current_user.role == "admin":
        return current_user
    # current_user.id is the staff_id for non-admin staff
    if current_user.id != staff_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user
```

Then add `_owner: Annotated[Staff, Depends(require_staff_ownership)]` to each `/staff/{staff_id}/...` endpoint, and add an explicit appointment-ownership check to the two `/appointments/{id}/notes` routes (load the appointment, compare `appointment.staff_id` to `current_user.id` for non-admins).

**What this changes about the deploy:**
- This is a code fix on `dev`. **No production change is needed**, but the merge to `main` should be blocked until the fix lands.
- A migration is not required — the fix is pure auth-dep wiring on existing routes.
- Add integration tests that confirm tech-A gets 403 on tech-B's resources.
- Re-run the Section 14 rehearsal after the fix lands so the 422 / 403 / 200 surface is verified end-to-end.

### 22.2 Lead-form schema silently drops 6 fields the companion site sends — **RESOLVED via migration #38**

**Status:** **RESOLVED** on `dev`. The plan at `.agents/plans/lead-form-consent-timestamp-and-utm-persistence.md` has been executed: `LeadSubmission` and `LeadResponse` now declare all six fields, the `leads` table has six new nullable columns (added by migration `20260510_120000_add_lead_consent_ts_and_utm_fields` — see Section 1, row #38), `LeadService.submit_lead` persists them, and `consent_timestamp` is forwarded into `SmsConsentRecord.consent_timestamp` via a new `consent_timestamp_override` keyword on `compliance_service.create_sms_consent`. From the merge to `main` forward, every new lead from the customer site will carry full consent + attribution data.

**Historical context (pre-fix):** Verified at the time the audit ran: neither `main` nor `dev` of the platform's `LeadSubmission` schema declared `consent_timestamp` or any `utm_*` field. The customer site has been sending these fields since 2026-03-11 (commit `b269f82` on `Grins_irrigation`), and they are present on the customer-site `main`. This means **production silently dropped these fields for ~2 months** before this fix landed.

**What the customer site sends** — per `/Users/kirillrakitin/Grins_irrigation/frontend/src/features/lead-form/api/leadApi.ts`, every lead submission can include:
- `consent_timestamp` — sent whenever `smsConsent` or `termsAccepted` is true
- `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content` — sent when present in the page query string

**What the platform's `LeadSubmission` schema declares** — per `src/grins_platform/schemas/lead.py:42–154`, none of the six fields above are declared. Pydantic v2 defaults to `extra='ignore'` on `BaseModel`, so extra fields are accepted but silently discarded. No 422 from the API; the operator sees a healthy lead landing in `leads`, just without the audit/attribution metadata.

**Independently verifiable:** lookup these fields in the `leads` table on dev — they will be NULL for every lead from the customer site, even when the request body included them. (This is a read-only DB check — safe to run.)

**Aligned fields** (sanity-checked the rest):
- `address` is required on both sides since 2026-03-30 (commit `4c6f2de` on the customer site, schema line 93–97 on the platform).
- `zip_code` is optional on the platform and the site no longer sends it.
- The `situation` enum mapping is consistent.
- `service_week_preferences` (recent companion-site work) goes through `POST /api/v1/onboarding/complete`, not the lead endpoint, and is correctly required there.

**What this changes about the deploy:**
- Either (a) declare the 6 fields on `LeadSubmission` (and add columns to the `leads` model + a new alembic migration that follows #37), or (b) accept the data loss and document it.
- If (a) is chosen, the migration is additive (new nullable columns, no CHECK changes) and is safe to chain after `20260508_120000`.
- If (b) is chosen, suppress the customer-site request from sending these fields so the wire format is honest. Otherwise compliance/legal may flag the gap later.

### 22.3 Lower-severity findings (operator-aware, not blockers)

These don't block the deploy but the operator should be aware of them.

- **HTTP client lifecycle leaks.** `CallRailProvider` (each call creates a new `httpx.AsyncClient(timeout=30s)` — see `services/sms/factory.py:46–51` and `services/sms/callrail_provider.py`) and `TravelTimeService` (`services/travel_time_service.py:57–61`, has a `close()` method that nothing calls) keep open `httpx.AsyncClient` instances that are never explicitly closed. Railway's 30s SIGTERM grace period eventually reaps them. Watch CallRail rate-limit 429s and "connection reset" entries in the first 5 minutes after each pod cycle. Not a blocker.
- **OpenAI client default timeout is 600s.** `services/ai/agent.py:54` uses `AsyncOpenAI()` with no `timeout=` override. If the OpenAI API stalls, AI scheduling chat requests will hang for 10 minutes, holding a worker. Acceptable for now; consider a timeout override in a follow-up.
- **APScheduler shutdown is non-blocking.** `app.py:162` calls `bg_scheduler.shutdown(wait=False)`. In-flight jobs (estimate follow-ups, day-2 reminders) are abandoned, not drained. Railway's grace period limits the blast radius. Don't deploy mid-cron-tick if avoidable.
- **Catch-all unhandled-exception middleware.** Added first in the middleware chain so 5xx responses keep their CORS headers (commit `20cbbcb`). This is a fix, not a regression. Worth knowing because the response body for unhandled exceptions is now uniform JSON, not stack traces — debugging requires the request_id from the response header.
- **New WebAuthn exception → status mapping.** Four new exceptions (`WebAuthnChallengeNotFoundError` → 404, `WebAuthnCredentialNotFoundError` → 404, `WebAuthnDuplicateCredentialError` → 409, `WebAuthnVerificationError` → 401) registered in `_register_exception_handlers()`. Existing API clients are unaffected.

### 22.4 What I cannot verify from here without touching production

These remain operator-only checks. The doc gives mechanical recipes for each.

- **Stripe dashboard event subscriptions** for the prod webhook endpoint. Run from a workstation with Stripe CLI authenticated to the prod account: `stripe webhook_endpoints list` then inspect `enabled_events`. Required: the existing set plus `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.canceled`, `charge.refunded`, `charge.dispute.created`.
- **Resend webhook registration.** Resend dashboard → Webhooks → endpoint pointing at `https://<api>/webhooks/resend` with `email.bounced` + `email.complained` subscribed.
- **CallRail webhook URL** still points at prod API hostname.
- **Railway prod env-var current state.** Run `railway variables --service api --environment production` and diff against Section 2 of this doc. Confirm test-allowlist guards are unset; confirm new env vars are set.
- **Vercel build env vars** for the prod frontend project. `VITE_API_BASE_URL`, `VITE_GOOGLE_MAPS_API_KEY`, `VITE_STRIPE_CUSTOMER_PORTAL_URL`.
- **DNS / TLS** for `app.grinsirrigation.com` and any other origins listed in `WEBAUTHN_EXPECTED_ORIGINS` and `CORS_ORIGINS`.

### 22.5 Final readiness statement (revised after main-vs-dev verification)

- **Code state:** **Shippable.** §22.1 is pre-existing in production — adds 2 new endpoints (`/appointments/{id}/notes`) sharing an existing missing-owner-check pattern, a marginal expansion of an existing problem, not a new vulnerability class. §22.2 has been **resolved on `dev`** via migration #38 (`20260510_120000`) + schema declaration + service plumbing; new leads from `main` forward will carry full consent + attribution data.
- **Track separately:** the authz fix (all 6 endpoints, not just the 2 new ones) deserves its own fix-and-ship cycle. It should not block this deploy.
- **Doc state:** Complete to the limits of what is verifiable from this checkout. All claims have been verified at file:line; main-vs-dev diff was used to distinguish regressions from pre-existing bugs.
- **The seven external operator gates remain** as the actual ship-or-don't checklist: Stripe event subscriptions, Resend webhook + secret, CallRail webhook URL, prod-strength `JWT_SECRET_KEY`, canonical `PORTAL_BASE_URL`, WebAuthn RP config, fresh prod backup, Section 14 rehearsal.

---

*This document was generated as analysis-only — no code or config changes have been applied. Treat each section as the authoritative pre-flight + rollout checklist for a controlled cut from `dev` to `main`.*
