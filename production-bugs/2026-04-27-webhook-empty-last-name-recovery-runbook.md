# PROD-BUG-001: Customer recovery runbook (Bucket A)

**Companion to:**
- `2026-04-26-webhook-empty-last-name-orphaned-agreements.md` (root-cause investigation)
- `2026-04-27-webhook-empty-last-name-prod-verification.md` (post-deploy verification of the fix on prod)

**Author:** Claude Code (Opus 4.7) + user
**Created:** 2026-04-27 (8:30 PM CT)

**Use when:** After all of the following are already true:
- PR #2 (`fix/webhook-empty-last-name`) is merged to `main` and deployed to Railway production. ✅ Done 2026-04-27.
- Production database backup `production_backup_20260427_201500.{dump,sql,xlsx}` exists locally. ✅ Done.
- The 3 Bucket A `stripe_webhook_events` rows have been deleted from production (idempotency blocker resolved). ✅ Done 2026-04-27 ~20:30 CT — see DEVLOG entry of the same date.
- In-DB backup table `stripe_webhook_events_bucketa_backup_20260427` exists in production with the 3 deleted rows preserved. ✅ Done.

**Purpose:** Recreate the agreement / customer / job rows for the 3 paying customers (Jerry, Andres, Chetan) whose `checkout.session.completed` webhooks originally crashed and were never persisted, then guide them through onboarding to complete their setup.

---

## TL;DR — what's left

| Phase | Action | Blocking? |
|---|---|---|
| **A** | Click "Resend" on each of 3 events in Stripe Dashboard, oldest-first, verifying after each | Yes (sequential — stop on any failure) |
| **B** | Construct 3 onboarding URLs from already-captured `cs_live_…` IDs | No (5 min) |
| **C** | Send 3 personalized apology emails | No |
| **D** | Monitor `service_agreements.property_id` for completion | Daily, until all 3 onboarded |
| **E** | Drop the in-DB backup table | ~14 days after D completes |
| **F** | Independent follow-ups (code improvement, doc sync, Bucket B/C handling) | Not blocking |
| **G** | Hard deadline: Stripe event retention | 2026-05-22 (~25 days from now) |

---

## 0. Hard deadline

Jerry's `checkout.session.completed` event is from **2026-04-22**. Stripe retains events for 30 days, so the event must be Resent before approximately **2026-05-22**. As of writing (2026-04-27) there are ~25 days of buffer, but there is no reason to delay — Jerry has been silent-failing for 5+ days.

If a Bucket A event ages out of Stripe retention before being Resent, the event payload is gone and recovery for that customer would require manual SQL backfill (subscription metadata still retrievable, but `cs_live_…` session ID and customer_details may not be — would need to be reconstructed from `customers.stripe_customer_id` + the active `subscription` row, which is more error-prone). Do not delay past 2026-05-15 without re-evaluating.

---

## A. Stripe Dashboard "Resend" — recreate the 3 customers in production

### Why this works now

Before today's work, clicking "Resend" on any of these 3 events would have hit the dedup short-circuit in `webhooks.py:108-115` and silently returned `{"status": "already_processed"}` without re-running the handler. We deleted those 3 dedup-blocking rows from `stripe_webhook_events`, so the next Resend will run the handler from scratch. The deployed handler (commit `392cb39` on `main`) tolerates the empty `last_name` via the `_MISSING_LAST_NAME_PLACEHOLDER = "-"` sentinel and creates the customer / agreement / jobs as if the original event had succeeded.

### Order

**Oldest-first**: Jerry → Andres → Chetan. Two reasons:
1. Smallest blast-radius of regression: if a regression slipped past the unit tests, Jerry hits it first and we abort the run before pinging Andres or Chetan.
2. Time-pressure ordering: Jerry's event is closest to the 30-day retention deadline.

**Stop after any failed step.** Do not Resend the next event until the previous one's verification passes.

### A.1 — Jerry (`evt_1TP6SsG1xK8dFlafLXj9Pcl4`, 2026-04-22)

1. Stripe Dashboard → toggle to **Live mode** (top-left). Verify the account name reads "Grin's Irrigation" (account ID `acct_1RDrfSG1xK8dFlaf`). If you see the dev sandbox (`acct_1RDrfZQDNzCTp6j5`), you are in the wrong account.
2. Developers → Events.
3. Search for `evt_1TP6SsG1xK8dFlafLXj9Pcl4`.
4. Open the event, scroll to the bottom, click **Resend**.
5. In the Resend dialog, confirm the target webhook is **only** the production endpoint `https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/stripe`. Do not Resend to dev or staging endpoints.
6. Click Resend. Stripe will deliver the event payload again with the same `evt_…` ID.
7. Watch Railway production logs. Expected log lines, in order:
   - `event=stripe.stripewebhookhandler.webhook_checkout_completed` (started)
   - `event=stripe.stripewebhookhandler.webhook_customer_placeholder_last_name first_name=Jerry full_name_provided=true`
   - `event=stripe.stripewebhookhandler.webhook_checkout_completed` (completed)
   - No `webhook_checkout_session_completed_failed` line.
   - Stripe Dashboard should show a **200** response from the webhook for the resent delivery attempt.
8. SQL verify (against production Postgres):
   ```sql
   -- Customer row was created
   SELECT id, first_name, last_name, email, phone, stripe_customer_id, created_at
     FROM customers
    WHERE stripe_customer_id = 'cus_UNsDC0zDE527dT';
   -- Expect: 1 row, first_name='Jerry', last_name='-' (the placeholder), email='jerrymitchell3@gmail.com'

   -- Agreement row was created
   SELECT id, agreement_number, status, stripe_subscription_id,
          customer_id, property_id, created_at
     FROM service_agreements
    WHERE stripe_subscription_id = 'sub_1TP6SqG1xK8dFlafOGEwjNu9';
   -- Expect: 1 row, status='active', property_id IS NULL (onboarding not yet submitted — normal)

   -- Default jobs were generated
   SELECT COUNT(*) AS job_count
     FROM jobs
    WHERE service_agreement_id = (
      SELECT id FROM service_agreements
       WHERE stripe_subscription_id = 'sub_1TP6SqG1xK8dFlafOGEwjNu9'
    );
   -- Expect: > 0 (Essential tier ≈ 5 jobs)

   -- Webhook event row created (this time with processing_status='processed')
   SELECT stripe_event_id, processing_status, processed_at
     FROM stripe_webhook_events
    WHERE stripe_event_id = 'evt_1TP6SsG1xK8dFlafLXj9Pcl4';
   -- Expect: 1 row, processing_status='processed'
   ```
9. **Abort criteria — if any of step 7 or 8 fails:**
   - If Stripe Dashboard shows a non-200 response: open Railway logs, find the `webhook_checkout_session_completed_failed` line, root-cause it. Do **not** proceed.
   - If logs look healthy but SQL shows no rows: there is a transaction-rollback bug we did not anticipate; capture logs and stop.
   - If SQL shows the customer / agreement was created but `customers.last_name != '-'`: the deployed image is not actually the merge commit; verify Railway deployment ID matches `3ae70ce3-861d-4005-a708-cec7730f4437` (image `sha256:3a75f99…`).

### A.2 — Andres (`evt_1TPpCnG1xK8dFlafmfSObbxa`, 2026-04-24)

Repeat A.1 step-by-step with these substitutions:

| Field | Value |
|---|---|
| Event ID | `evt_1TPpCnG1xK8dFlafmfSObbxa` |
| Subscription ID | `sub_1TPpCmG1xK8dFlafzNPCfJWB` |
| Customer ID (Stripe) | `cus_UOcRXOUJlQqgY3` |
| Email | `act.msp@gmail.com` |
| Expected `customers.first_name` | `Andres` |
| Expected `customers.last_name` | `-` |

### A.3 — Chetan (`evt_1TQELXG1xK8dFlafoofKg46o`, 2026-04-25)

Repeat A.1 with these substitutions:

| Field | Value |
|---|---|
| Event ID | `evt_1TQELXG1xK8dFlafoofKg46o` |
| Subscription ID | `sub_1TQELWG1xK8dFlafeg0JTAGI` |
| Customer ID (Stripe) | `cus_UP2QPiKeru3CrC` |
| Email | `cshenoy3@gmail.com` |
| Expected `customers.first_name` | `Chetan` |
| Expected `customers.last_name` | `-` |

### A.4 — Aggregate verification after all 3 Resends

```sql
SELECT c.first_name,
       c.last_name,
       c.email,
       sa.agreement_number,
       sa.status,
       sa.stripe_subscription_id,
       sa.property_id IS NULL AS pending_onboarding,
       sa.created_at
  FROM service_agreements sa
  JOIN customers c ON c.id = sa.customer_id
 WHERE sa.stripe_subscription_id IN (
   'sub_1TP6SqG1xK8dFlafOGEwjNu9',  -- Jerry
   'sub_1TPpCmG1xK8dFlafzNPCfJWB',  -- Andres
   'sub_1TQELWG1xK8dFlafeg0JTAGI'   -- Chetan
 )
 ORDER BY sa.created_at;
-- Expect: 3 rows, all status='active', all pending_onboarding=true, last_name='-' on all 3
```

---

## B. Construct onboarding URLs

Format: `https://grinsirrigation.com/onboarding?session_id=<cs_live_…>`

The 3 `cs_live_…` IDs were captured from the failed events on 2026-04-27 before the dedup rows were deleted. They are stored in `backups/forensic/bucket_a_pre_delete_20260427_201500.txt` and reproduced here:

| Customer | Onboarding URL |
|---|---|
| Jerry | `https://grinsirrigation.com/onboarding?session_id=cs_live_b1GctgwIkoenYuG6y2FKnr2lEmppkwvC8oXWUau66vL8MzUUEnZE8BNyHk` |
| Andres | `https://grinsirrigation.com/onboarding?session_id=cs_live_a13KZSLlNkSFXLPx4aF4N4n8Ul2dgIa3vMI2B51MYEaK59axpC4drJzt3w` |
| Chetan | `https://grinsirrigation.com/onboarding?session_id=cs_live_a12TRCOmzaFc5WjG2RqwkH2X9i7KdxKrumwuRjRzyZ1Wgy59g2QV4SBaOb` |

### B.1 — Pre-flight each link in incognito

Open each URL in a **private / incognito** browser window before sending. Expected behavior:
- Page loads without 404.
- Form pre-fills `first_name`, billing address, package info from `verify-session` response.
- Form is editable; fields like `gate_code`, `has_dogs`, `preferred_times`, `service_week_preferences` are at their defaults (per `OnboardingPage.tsx:27-36`).
- Page does **not** show "Already completed" — that would mean someone (or you, accidentally) already submitted the form.

**Do not click Submit yourself.** A successful submit consumes the link by setting `agreement.property_id` and flipping the page to the success state.

If a link returns "We couldn't find your session" (the original bug's error string), the agreement was not created — go back to A and verify SQL.

---

## C. Send apology emails

### C.1 — Recipients

| First name | Email | Onboarding URL |
|---|---|---|
| Jerry | `jerrymitchell3@gmail.com` | (from B) |
| Andres | `act.msp@gmail.com` | (from B) |
| Chetan | `cshenoy3@gmail.com` | (from B) |

Send from a real human address (not `no-reply@…`) so customers can reply if they hit issues.

### C.2 — Email body (per §17.8 of the parent investigation doc)

> **Subject:** A quick fix needed to start your service with Grin's Irrigation
>
> Hi {first_name},
>
> Thanks for signing up for Grin's Irrigation. We hit a glitch on our end while processing your sign-up, which prevented us from finalizing your service setup. **Your payment went through correctly** — that part is fine.
>
> To finish setting up your service, please click here:
>
> **{onboarding_url}**
>
> The form takes about 3-5 minutes. We just need your property details (zone count, gate code if any, etc.) and your preferred service times.
>
> If you need to make corrections after submitting, just reply to this email and we'll take care of it.
>
> Sorry for the hiccup, and thanks for your patience.
>
> — The Grin's Irrigation Team

### C.3 — Tone notes

- Lead with what's wrong, then the fix, then the small ask.
- Don't over-apologize or over-explain ("technical issue" / "ValidationError" / etc. — they don't need that).
- Make the link impossible to miss — bold + on its own line.
- End with reassurance that corrections are fixable post-submit (the current onboarding flow's `already_completed=true` guard blocks them from re-submitting via the link, so a reply-back path is the corrections channel).

### C.4 — What customers do NOT have to do

- Re-pay (Stripe already charged them; no change there).
- Re-consent to SMS or terms of service (already captured via `consent_token` in checkout metadata; replay re-applies via `compliance_svc`).
- Re-enter name, email, phone (form prefills from `verify-session`).
- Create an account or remember a password (no auth on the onboarding flow — knowledge of the `cs_live_…` session ID is the credential).

### C.5 — Link lifetime

Per §17.4 of the parent doc, the onboarding link is **effectively permanent** as long as (a) the Stripe subscription stays active and (b) the agreement exists in our DB. No time-based expiration check, no token. They can click it today, next week, or 3 months from now and it still works. They can lose the email and find it later — still works. Use "whenever you're ready" framing in any follow-up messages.

---

## D. Monitor for completion

Run daily until all 3 are onboarded:

```sql
SELECT c.first_name,
       c.email,
       sa.agreement_number,
       sa.property_id IS NOT NULL AS onboarded,
       sa.created_at,
       sa.updated_at,
       p.zone_count                AS reported_zones,
       p.gate_code IS NOT NULL     AS has_gate_code,
       p.has_dogs
  FROM service_agreements sa
  JOIN customers  c ON c.id  = sa.customer_id
  LEFT JOIN properties p ON p.id = sa.property_id
 WHERE sa.stripe_subscription_id IN (
   'sub_1TP6SqG1xK8dFlafOGEwjNu9',  -- Jerry
   'sub_1TPpCmG1xK8dFlafzNPCfJWB',  -- Andres
   'sub_1TQELWG1xK8dFlafeg0JTAGI'   -- Chetan
 );
```

Success per row = `onboarded = true`.

### D.1 — If a customer doesn't respond within 5 days

Send a brief follow-up email with the same link and a short "just checking in" note. After 10 days with no response, offer a phone call.

### D.2 — If a customer reports an error after submitting

The "already completed" guard on the form blocks re-submission via the same link. Per the email, instruct them to reply with corrections; on the admin side, edit `properties` directly via the admin UI or SQL.

---

## E. Drop the in-DB backup table — ~14 days after D completes

After all 3 customers have submitted the onboarding form (i.e., `property_id IS NOT NULL` on all 3 agreements), **wait ~2 weeks**, then drop the safety-net backup table:

```sql
DROP TABLE stripe_webhook_events_bucketa_backup_20260427;
```

**Do not drop earlier.** The backup table is the cheapest in-place rollback path if something unexpected surfaces (a customer reports a billing dispute, a duplicate agreement gets created, etc.).

If you choose to keep the backup table indefinitely, it is harmless (3 rows, tiny). But cleaning it up keeps the schema tidy.

If you've already dropped it and need to restore, the alternative paths are:
- `pg_restore --data-only --table=stripe_webhook_events_bucketa_backup_20260427` from `production_backup_20260427_201500.dump` (still on disk locally), or
- Re-extract the same 3 rows from the original Stripe events if still within the 30-day retention window.

---

## F. Independent follow-ups (not blocking the recovery)

### F.1 — One-line code improvement: relax the dedup check

**Problem:** `webhooks.py:108-115` short-circuits on **any** existing `stripe_webhook_events` row, regardless of `processing_status`. This is why we had to manually DELETE the 3 failed rows before Resend would work. A future Bucket-A-style bug class would require the same manual DELETE.

**Fix:** Patch the dedup check to only short-circuit on `processing_status='processed'`. One-line change. Suggested approach:

```python
if existing is not None and existing.processing_status == "processed":
    return {"status": "already_processed"}
```

(Plus update the existing event_record overwrite logic in the `except` block at lines 134-151 to handle the now-possible "row exists with status=failed, retry it" case cleanly. This may need to be a `mark_failed` -> `update_event_record` path rather than `create_event_record` since the unique constraint on `stripe_event_id` will fire on a duplicate INSERT.)

Open a separate PR for this. Not blocking the Bucket A recovery.

### F.2 — Doc sync: `BACKUP-INSTRUCTIONS.md`

The embedded `REFERENCE_TABLES` list inside `BACKUP-INSTRUCTIONS.md` has 41 entries. Production now has 50 public tables. The 9 missing tables are:
- `campaign_responses`
- `contract_renewal_proposals`
- `contract_renewal_proposed_jobs`
- `customer_documents`
- `customer_merge_candidates`
- `job_confirmation_responses`
- `reschedule_requests`
- `sales_calendar_events`
- `sales_entries`

I added them to `/tmp/export_xlsx_backup.py` for the 2026-04-27 backup run, but did not update the canonical doc. Update the inline script in `BACKUP-INSTRUCTIONS.md` so the next backup uses the 50-table list out of the box.

### F.3 — Bucket B (14 customers) — no action needed

Per §15 of the parent investigation doc, a read-only DB query confirmed all 14 Bucket B customers are `status='active'`, `property_id IS NOT NULL`, and fully onboarded. Their `webhook_invoice_paid_failed` log entries were transient out-of-order-events that recovered on subsequent retries. **Do not Resend their checkout events** — that would re-trigger their distinct (still-not-fully-explained) failure mode for nothing.

If a *new* customer surfaces in the future with the Bucket B log signature (`webhook_invoice_paid_failed: "No agreement for subscription …"` without a corresponding `webhook_checkout_session_completed_failed`), open a separate investigation per §13.

### F.4 — Bucket C — operator decision required

Two subscriptions with empty checkout metadata (`sub_1TQBeOG1xK8dFlafPJKDjyN3` Shores Of Kraetz Lake, `sub_1TQBUlG1xK8dFlaf5X9O10Se` Mitchell Bay Townhomes) appear admin-created or non-checkout-flow. Per §17.6 of the parent doc, talk to whoever created them in the Stripe Dashboard before doing anything. Possible outcomes: manual SQL backfill / cancel-and-clean-up / second-property under Brent Ryan's existing customer record (Shores shares his phone).

---

## G. Acceptance criteria for this runbook

This runbook is "complete" when all of the following are true:

- [ ] All 3 Bucket A events Resent successfully on Stripe Dashboard, all returning 200 to the webhook.
- [ ] All 3 customers exist in `customers` with `last_name='-'` and the expected first_name/email/phone.
- [ ] All 3 service agreements exist with `status='active'`, correct `stripe_subscription_id`, and at least the default jobs generated.
- [ ] All 3 onboarding URLs verified to load in incognito (do not submit).
- [ ] All 3 apology emails sent.
- [ ] All 3 customers have submitted the onboarding form (`property_id IS NOT NULL`).
- [ ] In-DB backup table `stripe_webhook_events_bucketa_backup_20260427` dropped (after the ~14-day waiting period from the last onboarding completion).

The follow-ups in §F are independent and do not block this checklist.

---

## H. Rollback / what-if scenarios

### H.1 — Stripe Dashboard Resend reports a non-200 response from the webhook

Cause: probably a regression in the deployed code, an unrelated bug surfacing on this specific event payload, or a transient infra issue.

1. Open Railway logs and find the failure log entry.
2. If the failure is a transient infra issue (timeout / 502): wait 5 minutes and Resend again.
3. If the failure is a code bug: do **not** Resend other events. Open an investigation. The DELETE we did earlier means the dedup-blocking row is gone — the Resend will keep trying as long as the event is in Stripe retention. So a re-Resend after a fix-deploy should still work.
4. If the failure leaves a `processing_status='failed'` row in `stripe_webhook_events` for that event ID, that row will then block the next Resend (same dedup short-circuit). Either delete it again (same SQL pattern as before) or run F.1 first to fix the dedup logic so this stops happening.

### H.2 — Customer fills out the form and gets a 404 on submit

Should not happen now (the agreement exists). If it does:
1. Verify `service_agreements` row for their `stripe_subscription_id` actually exists in production.
2. Verify the `cs_live_…` ID in their URL matches the session ID stored in the `stripe_webhook_events` row.
3. Check `OnboardingService.complete_onboarding` logs for the actual error.

### H.3 — We need to restore the deleted Bucket A `stripe_webhook_events` rows

In-place restore:
```sql
INSERT INTO stripe_webhook_events
SELECT * FROM stripe_webhook_events_bucketa_backup_20260427
ON CONFLICT (stripe_event_id) DO NOTHING;
```

This would re-introduce the dedup blocker. Only do this if you've decided to abandon the recovery and want the original audit trail back. After a successful Resend, the `stripe_webhook_events` table has a *new* row for each evt with `processing_status='processed'` — restoring the backup-table row would create a constraint violation (which the `ON CONFLICT` clause swallows safely).

If you've also dropped the backup table (per E):
```bash
# pg_restore the rows from the local pre-recovery snapshot, then INSERT manually
pg_restore --data-only --table=stripe_webhook_events \
  --file=/tmp/restored_swe.sql \
  backups/production_backup_20260427_201500.dump
# Then extract the 3 rows of interest from /tmp/restored_swe.sql and INSERT.
```

---

## I. Cross-references

- Investigation: `production-bugs/2026-04-26-webhook-empty-last-name-orphaned-agreements.md` — full root-cause analysis, the orphan inventory (Buckets A/B/C), the §17 recovery plan that this runbook implements.
- Post-deploy verification: `production-bugs/2026-04-27-webhook-empty-last-name-prod-verification.md` — proves the deployed fix actually resolves the original crash on a real production replay.
- Code fix (PR #2): `https://github.com/kirillDR01/Grins_irrigation_platform/pull/2`, merge commit `392cb39` on `main`.
- Backup files: `backups/production_backup_20260427_201500.{dump,sql,xlsx}` (local-only per `.gitignore`).
- Forensic dump of pre-delete rows: `backups/forensic/bucket_a_pre_delete_20260427_201500.txt` (local-only).
- DEVLOG entry: `DEVLOG.md` → "[2026-04-27 20:30 CT] - BUGFIX + DATA OPS: Webhook empty-last-name fix deployed; pre-recovery DB cleanup for 3 orphaned customers".

---

**Document version:** 1.0
**Created:** 2026-04-27 (8:30 PM CT)
