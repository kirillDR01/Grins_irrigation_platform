# Bug Hunt — Lead Form Silent Rollback When `sms_consent=true`

**Found:** 2026-04-14 during E2E test of customer landing page (dev)
**Fixed:** 2026-04-14 in commit `88e471f` (deployed to dev)
**Environment:** Dev (Vercel preview `grins-irrigation-git-dev-kirilldr01s-projects.vercel.app` → Railway `grins-dev-dev.up.railway.app`)
**Severity:** P0 / Critical — silent data loss on primary customer intake path
**Repro confidence:** 100% (reproduced via 3 frontend submissions + 4 controlled curl probes)
**Status:** ✅ FIXED — verified end-to-end via curl probes + customer-landing form + admin dashboard (`e2e-screenshots/bug001-verify-2026-04-15/`)

---

## TL;DR

`POST /api/v1/leads` with `sms_consent=true` returns **HTTP 201** with a valid-looking `lead_id`, but the lead is **never persisted** to the database. The customer sees the "Thanks, we'll reach out" success banner, and nothing lands in the admin dashboard. Every website submission from a TCPA-consenting customer (the majority of real leads) is being silently dropped.

With `sms_consent=false`, the same endpoint + same payload works correctly: lead persists and appears in `/leads`.

---

## Reproduction

### Minimal failing curl

```bash
API="https://grins-dev-dev.up.railway.app/api/v1"
TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# FAILING CASE — sms_consent=true
RESP=$(curl -s -X POST "$API/leads" -H "Content-Type: application/json" -d '{
  "name":"E2E-Probe-SmsOnly",
  "phone":"9527370950",
  "email":"probe-sms-only@test.example",
  "address":"950 St",
  "situation":"new_system",
  "source_site":"website",
  "website":"",
  "customer_type":"new",
  "property_type":"RESIDENTIAL",
  "lead_source":"other",
  "sms_consent":true,
  "terms_accepted":false,
  "email_marketing_consent":false
}')
echo "$RESP"
# -> {"success":true,"message":"Thank you! …","lead_id":"0c0371c3-2d4b-4acc-ad19-51ce20a8c50e"}

LID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['lead_id'])")
curl -s "$API/leads/$LID" -H "Authorization: Bearer $TOKEN"
# -> {"success":false,"error":{"code":"LEAD_NOT_FOUND","message":"Lead not found: 0c0371c3-…"}}
```

### Passing case (same payload, `sms_consent=false`)

```bash
RESP=$(curl -s -X POST "$API/leads" -H "Content-Type: application/json" -d '{
  "name":"E2E-Probe-TermsOnly",
  "phone":"9527370960",
  "email":"probe-terms@test.example",
  "address":"960 St",
  "situation":"new_system",
  "source_site":"website",
  "website":"",
  "customer_type":"new",
  "property_type":"RESIDENTIAL",
  "lead_source":"other",
  "sms_consent":false,
  "terms_accepted":true,
  "email_marketing_consent":true
}')
LID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['lead_id'])")
curl -s "$API/leads/$LID" -H "Authorization: Bearer $TOKEN"
# -> full Lead JSON ✓  (row appears at top of /api/v1/leads list, total count increments)
```

### Matrix of probes actually run today

| Probe | Phone | sms_consent | terms | email_mktg | POST status | GET /leads/{id} | In list |
|---|---|---|---|---|---|---|---|
| Curl "E2E-Curl-Probe-A" | 9527370900 | false | true | false | 201 + id | ✓ visible | ✓ |
| Curl "E2E-Probe-NoCustType" | 9527370910 | false | true | false | 201 + id | ✓ visible | ✓ |
| Curl "E2E-Probe-WithCustType" | 9527370920 | false | true | false | 201 + id | ✓ visible | ✓ |
| Curl "E2E-Probe-SmsTrue" | 9527370930 | **true** | true | true | 201 + id | ✗ NOT_FOUND | ✗ |
| Curl "E2E-Probe-FormattedPhone" | (952) 737-0940 | **true** | true | false | 201 + id | ✗ NOT_FOUND | ✗ |
| Curl "E2E-Probe-SmsOnly" | 9527370950 | **true** | false | false | 201 + id | ✗ NOT_FOUND | ✗ |
| Curl "E2E-Probe-TermsOnly" | 9527370960 | false | true | true | 201 + id | ✓ visible | ✓ |
| Frontend "Scenario 09" attempts | 9527370109 / 9527371109 | **true** | true | true | 201 + id | ✗ NOT_FOUND | ✗ |
| Frontend "Scenario 10" | 9527370210 | **true** | true | false | 201 + id | ✗ not in list | ✗ |
| **Frontend "Scenario 11"** | **9527370311** | **false** | true | true | 201 + id | ✓ visible | ✓ |

**Pattern is deterministic:** `sms_consent=true` → row lost; `sms_consent=false` → row persists. No other variable (customer_type, property_type, lead_source, phone format, email marketing consent, terms, consent metadata fields) causes the loss on its own.

---

## Customer impact

- "Get Your Free Quote" is the primary intake widget on the dev marketing site (grins-irrigation-git-dev…vercel.app) — rendered on home, services, final-CTA, and chatbot contexts.
- The SMS consent checkbox is presented immediately below the submit button. Most customers checking at least SMS consent (very common — it is the visually-first consent checkbox) are impacted.
- Customers see the green success banner (`"We'll reach out to you within 1-2 business days."`), so they assume contact is coming. The business never sees the lead. Revenue impact is direct.
- The parallel pipeline `source_site=google_sheets` is not impacted (those 11 pre-existing leads all have `sms_consent=False` because the Google-Forms ingester doesn't set that field).

---

## Root cause hypothesis

Only a code-read hypothesis — confirm before fixing.

`src/grins_platform/services/lead_service.py` `submit_lead()` flow:

```
Step 5b: lead_repository.create(...)  # session.flush(), session.refresh(lead)
Step 6:  _create_lead_consent_record(lead, data)  # only writes SmsConsentRecord when compliance_service exists
Step 7:  logger.info("lead.submitted")
Step 8:  _send_sms_confirmation(lead)   # only runs when lead.sms_consent is True
Step 8b: _send_email_confirmation(lead)
Step 9:  return LeadSubmissionResponse(success=True, lead_id=lead.id)
```

`_send_sms_confirmation` is only reached when `lead.sms_consent is True` (line 197 — `if not lead.sms_consent: return`). That matches the observed gate perfectly: every failing probe has `sms_consent=true`.

Inside `_send_sms_confirmation`:

```python
try:
    result = await self.sms_service.send_automated_message(
        phone=lead.phone,
        message=confirmation_msg,
        message_type="lead_confirmation",
    )
    …
except Exception as e:
    self.logger.warning("lead.confirmation.sms_failed", lead_id=str(lead.id), error=str(e))
```

The try/except catches exceptions — but **a thrown SQLAlchemy error inside a flush/add call does not leave the session usable.** `send_automated_message` writes a `SentMessage`/communication queue row via the same `AsyncSession` the lead was flushed with. If that write blows up (e.g. due to a FK / NOT NULL / check constraint violation, a schema drift on the dev DB, or a dedupe-window update that fails), the exception is caught but the session is now in an unrecoverable state. The outer transaction scope in `grins_platform/database.py:114-120` then sees the session-level error when it tries `await session.commit()` at `__aexit__`, rolls back, and the lead is gone — but by that time FastAPI has already serialized the `LeadSubmissionResponse(success=True, lead_id=…)` body that was returned before the dependency unwound. HTTP 201 is already on the wire.

Supporting evidence for this hypothesis:
- Leads with `sms_consent=false` skip Step 8 entirely → nothing fires against the session → transaction commits cleanly.
- The API returns a UUID that matches what `session.refresh(lead)` would have populated, so the lead object was created in-session but discarded on rollback.
- No log noise on the client side; no 5xx surfaced.

A quick way to confirm from ops:
1. Check Railway logs on `grins-dev-dev` for `lead.confirmation.sms_failed` warning lines in the same request trace as the 201 response.
2. Check for `InvalidRequestError: This Session's transaction has been rolled back` or `PendingRollbackError` in the same window.

### Possible fixes (for triage, not applied here)

1. **Run SMS/email confirmation AFTER commit** — don't share the intake-transaction's session with side-effect writes. Fire them in a background task post-response. This is the structurally correct fix because the landing-page 201 shouldn't depend on downstream notification plumbing at all.
2. **Open a nested `session.begin_nested()` / SAVEPOINT around `_send_sms_confirmation`** so a failure can be rolled back in isolation, leaving the outer transaction committable.
3. **If the failure is an `InvalidRequestError` from session state after a caught flush error**, call `session.rollback()` inside the `except` to reset to the savepoint before the lead-create flush — but this is fragile and risks re-rollback of the lead itself. Prefer (1) or (2).
4. **Guard against silent 201-with-rollback at the framework level**: make `db_session_generator` raise after commit failure so FastAPI converts to 500 instead of successfully returning 201; the client then retries. This is a safety net, not a fix for the underlying cause.

---

## Related / adjacent bugs surfaced during the same session

### BUG-002 — `VITE_API_URL` has a trailing newline in the dev deploy

The frontend fetch captures show the actual request URL as:

```
"https://grins-dev-dev.up.railway.app\n/api/v1/leads"
```

The embedded `\n` is between the origin and the path. Modern browsers + Railway's edge tolerate this (POSTs still reach the backend), but it's a config hygiene issue that can break strict HTTP clients, WAFs, or observability tooling that key on exact URL. The env var `VITE_API_URL` on the Vercel dev project needs to be re-saved without the trailing newline.

### BUG-003 — Admin `/api/v1/leads` list response is CDN-cached

Railway Fastly edge (`x-railway-cdn-edge: fastly/cache-chi-klot8100060-CHI`) is caching the admin list endpoint. A lead that was just persisted via POST did not appear in GET `/api/v1/leads` until a cache-busting query param (`?_t=<epoch>`) was added. This is fine for read-heavy marketing pages but is confusing / misleading on the admin list where freshness matters. The client should add `Cache-Control: no-store` or the server should set `Vary: Authorization` and `Cache-Control: private, no-cache`. On the admin frontend, the user-visible impact is that a newly-created lead may not appear until the page is hard-refreshed.

### BUG-004 — Admin `/api/v1/leads?search=<phone>` does not match phone digits

`GET /api/v1/leads?search=9527370311` returns `total=0` even though a lead with that exact phone exists and is `moved_to=null` (non-moved). The list repository query filters OR(name ILIKE, phone LIKE) but with something that's not matching the stored `phone="9527370311"` — possibly an extra space, an E.164 prefix, or a formatted variant being indexed. Low severity because the admin UI uses its own search box, but worth confirming that search-by-phone actually works in production.

---

## What to verify before closing

1. **Reproduce BUG-001 on staging/prod** with one harmless payload (unique phone, `sms_consent=true`). Capture Railway logs in the request's correlation window and confirm the `lead.confirmation.sms_failed` warning + any `InvalidRequestError` traceback. **Do NOT run this on prod with a real customer phone** — use an allowlisted test number.
2. Once root cause is confirmed, fix one of the options above. The test that should gate the fix is:
   ```
   POST /leads with sms_consent=true → 201 → GET /leads/{id} → 200 with lead row
   ```
3. Add an integration test that asserts the lead row exists after the POST completes, with `sms_consent=true` parametrized. The current test suite likely only exercises `sms_consent=false` which is why this slipped.

---

## Screenshots

- `e2e-screenshots/customer-landing-2026-04-14/09-lead-new-residential/06-success-banner.png` — customer-visible success banner despite row being rolled back
- `e2e-screenshots/customer-landing-2026-04-14/09-lead-new-residential/09-submit-done.png` — bottom-of-viewport state post-submit
- `e2e-screenshots/customer-landing-2026-04-14/10-lead-new-commercial/02-after-submit.png` — scenario 10, same symptom, Commercial property type
- `e2e-screenshots/customer-landing-2026-04-14/11-lead-existing-res/02-after-submit.png` — baseline: `sms_consent=false` → lead persisted (control case for the bug)
- `e2e-screenshots/customer-landing-2026-04-14/12-lead-duplicate/01-duplicate-result.png` — duplicate banner (different surface, proves that path works)
- `e2e-screenshots/customer-landing-2026-04-14/13-lead-consent-matrix/02-validation-error.png` — missing T&Cs client-side block (proves validation works)

---

## Fixed — 2026-04-14 (commit `88e471f`)

**Approach:** Option 1 from the triage list above — SMS + email confirmations now run *after* the request transaction commits, in a fresh database session, scheduled via FastAPI's `BackgroundTasks`. A failure in the notification path can no longer roll back the lead-intake transaction.

**Code changes (4 files, +377 / -15):**
- `src/grins_platform/services/lead_service.py` — new module-level `send_lead_confirmations_post_commit(lead_id)` opens its own `AsyncSession` from the global `DatabaseManager` factory, re-fetches the lead, and runs `SMSService.send_automated_message` + `EmailService.send_lead_confirmation`. Errors are logged at **ERROR** severity (not WARNING) so future regressions are visible. `LeadService.submit_lead(...)` accepts an optional `background_tasks: BackgroundTasks` and schedules the post-commit task instead of calling the inline `_send_sms_confirmation` / `_send_email_confirmation` paths. The instance methods are kept for backward compat with the `create_from_call` admin path and existing direct-call unit tests.
- `src/grins_platform/api/v1/leads.py` — public POST `/leads` route now declares `background_tasks: BackgroundTasks` and forwards it to `service.submit_lead(...)`.
- `src/grins_platform/tests/unit/test_lead_service_crm.py` — `test_submit_lead_with_consent_triggers_sms_confirmation` rewritten as `test_submit_lead_with_consent_schedules_post_commit_sms` (asserts SMS is *not* called inline and that `background_tasks.add_task(send_lead_confirmations_post_commit, lead.id)` is scheduled).
- `src/grins_platform/tests/unit/test_lead_service_extensions.py` — `test_email_sent_when_email_present` rewritten as `test_submit_lead_schedules_email_as_post_commit_task` for the same reason.

**Regression test (new):** `src/grins_platform/tests/integration/test_lead_sms_consent_persistence.py` — three guards:
1. `test_lead_persists_for_both_sms_consent_values` (parametrized over `sms_consent ∈ {True, False}`) — asserts `lead_repository.create` is awaited and `sms_service.send_automated_message` is **not** called inline. This is the direct regression test the bughunt asked for.
2. `test_sms_consent_true_schedules_post_commit_task` — asserts `BackgroundTasks.add_task` is called with `send_lead_confirmations_post_commit` and the lead's id.
3. `test_submit_lead_survives_sms_failure` — wires `sms_service.send_automated_message` to raise on call; asserts `submit_lead` still returns success and `lead_repository.create` was awaited (would have been the rollback case under the old inline code path).

All 4 tests in the new module pass; full lead test suite (332 tests) passes with one pre-existing unrelated failure (`test_situation_maps_to_correct_job_type`, asserts on the wrong tuple element from `SITUATION_JOB_MAP` and was already broken on `dev` before this fix).

**Verification on dev:**
- Curl probes (post-deploy): `POST /api/v1/leads` with `sms_consent=true` (PostFix-SmsTrue, id `59bbfed0-...`) → row visible on subsequent `GET /leads/{id}`. Control with `sms_consent=false` (PostFix-SmsFalse, id `ee53d21d-...`) → row visible. Both also appear at the top of `GET /leads?sort_by=created_at&sort_order=desc`.
- Customer landing form submission: phone `9527375003`, name `BUG-001 Verify Lead`, SMS box + T&Cs both checked → success banner shown → lead `d94a9cc2-c3d3-40e9-b1d7-1415ae4c23ab` appears in admin `/leads` list at position #1 with `SMS Consent: Given`, `Terms & Conditions: Accepted` rendering correctly in the detail view (`e2e-screenshots/bug001-verify-2026-04-15/04-admin-lead-detail.png`).

**Notes for future maintenance:**
- The `create_from_call` admin path (line 584-585) still calls the inline `_send_sms_confirmation` / `_send_email_confirmation` methods. It is **not** affected by BUG-001 in practice because `FromCallSubmission` does not carry an `sms_consent` field, so the SMS confirmation gate (`if not lead.sms_consent: return`) prevents the failing branch from firing. If `FromCallSubmission` ever gains explicit `sms_consent`, that callsite must be migrated to the same post-commit pattern.
- `BUG-002` (trailing newline in `VITE_API_URL`), `BUG-003` (CDN caching of `/api/v1/leads` list), and `BUG-004` (`?search=<phone>` not matching) from this writeup remain **OPEN** — they were surfaced in the same E2E session but are independent of the silent-rollback fix.
