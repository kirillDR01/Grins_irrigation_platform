# PROD-BUG-001: Webhook crash on single-word Stripe customer names → orphaned paid subscriptions

**Discovered:** 2026-04-26
**Reporter:** kirillrakitinsecond@gmail.com (user-reported customer support tickets)
**Investigated by:** Claude Code (Opus 4.7) + user
**Severity:** Critical — paying customers cannot complete onboarding
**Status:** Root cause identified. Fix plan written. Not yet deployed.

---

## TL;DR

`checkout.session.completed` webhook handler in production crashes with a Pydantic `ValidationError` when a Stripe Checkout customer enters only one name (mononym, or first name only). The exception propagates uncaught, the entire SQL transaction rolls back, and **no `service_agreement` row is ever persisted** — even though Stripe successfully charged the customer's card and created an active subscription. The customer is then permanently locked out of `/onboarding` with the user-visible error **"We couldn't find your session. Please contact us."**

**Confirmed bug occurrences (single-word name):** 3 customers between 2026-04-22 and 2026-04-25.
**Other orphaned subscriptions found during investigation (different/unidentified causes):** 14 customers + 2 likely admin-created subs (no checkout metadata).
**Total orphaned active subscriptions in live Stripe with no matching agreement in prod DB:** 19.

> **2026-04-27 update (see §15):** A read-only production DB query overturned the §13.3 hypothesis for Bucket B. **All 14 Bucket B customers fully completed onboarding** — `status='active'`, `property_id IS NOT NULL`, `service_week_preferences` populated. No customer outreach is required for them. The genuinely-orphaned cohort is **Bucket A (3) + Bucket C (2) = 5 subscriptions**, not 19.

---

## 1. The user-visible symptom

After completing Stripe Checkout (card charged, redirect to `/onboarding?session_id=cs_live_…`), the customer:
1. Sees the onboarding page render correctly with their name and selected package — **`verify-session` succeeds**.
2. Fills out the property details form (preferred service times, per-service week preferences, etc.).
3. Clicks **Complete Onboarding**.
4. Sees the red error **"We couldn't find your session. Please contact us."**

The form is unrecoverable — refreshing, retrying, or returning later all show the same error indefinitely.

Screenshot evidence: `/Users/kirillrakitin/Desktop/IMG_8061.HEIC` (provided by user 2026-04-26).

---

## 2. Root cause — exact code path

### 2.1 Where the user-visible error string is rendered

**File:** `Grins_irrigation/frontend/src/features/onboarding/components/OnboardingPage.tsx:119`

```tsx
} else if (result.error === 'not_found') {
  setSubmitError("We couldn't find your session. Please contact us.");
}
```

This branch fires when `POST /api/v1/onboarding/complete` returns HTTP 404. It is gated on a *successful* prior `verify-session` call, so the customer reached the form correctly — only the submit failed.

### 2.2 Where the 404 originates

**File:** `Grins_irrigation_platform/src/grins_platform/api/v1/onboarding.py:434-443`

```python
except AgreementNotFoundForSessionError:
    _endpoints.log_rejected(
        "complete_onboarding",
        reason="agreement_not_found",
        session_id=data.session_id,
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "No agreement found for this session."},
    )
```

The `AgreementNotFoundForSessionError` is raised when no `service_agreements` row exists with `stripe_subscription_id == <subscription_id_from_session>`.

### 2.3 Where the agreement *should* have been created

**File:** `Grins_irrigation_platform/src/grins_platform/api/v1/webhooks.py:220-474`

The `_handle_checkout_completed` method is invoked by Stripe's `checkout.session.completed` webhook event. It performs ~14 ordered operations, in roughly this order:

1. Find or create `Customer` (`webhooks.py:268-331`).
2. Update `Customer.stripe_customer_id` (`webhooks.py:333-335`).
3. Resolve tier from metadata (`webhooks.py:345-354`).
4. Create `ServiceAgreement` (`webhooks.py:356-365`).
5. Activate agreement (`webhooks.py:367-372`).
6. Apply surcharge calculation, update agreement (`webhooks.py:374-392`).
7. Carry email_marketing_consent (`webhooks.py:394-400`).
8. Generate seasonal `Job` rows (`webhooks.py:402-403`).
9. Refresh agreement to load jobs (`webhooks.py:405-406`).
10. Link orphaned consent / disclosure records (`webhooks.py:408-435`).
11. Transfer SMS consent flags to customer (`webhooks.py:418-428`).
12. Create pre-sale disclosure (`webhooks.py:438-444`).
13. Send confirmation email (stub on `main` — only logs; `webhooks.py:446-462`).
14. Send welcome email (stub on `main`; `webhooks.py:465`).

**The crash happens in step 1**, before agreement creation in step 4, so everything rolls back via SQLAlchemy's transaction semantics.

### 2.4 The exact crashing line

**File:** `Grins_irrigation_platform/src/grins_platform/api/v1/webhooks.py:277-315`

```python
if customer is None:
    # Extract name and phone from session
    cust_details: dict[str, Any] = session_obj.get("customer_details", {}) or {}
    full_name = str(cust_details.get("name", "") or "")
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0] if parts else "Customer"
    last_name = parts[1] if len(parts) > 1 else ""        # ← line 283
    phone_raw = str(cust_details.get("phone", "") or "")

    # …phone normalization + lookup…

    if customer is None:
        create_data = CustomerCreate(
            first_name=first_name,
            last_name=last_name,                           # ← line 312
            phone=normalized_phone or phone_raw or f"000{event['id'][-7:]}",
            email=customer_email or None,
        )
        try:
            cust_svc = CustomerService(customer_repo)
            cust_resp = await cust_svc.create_customer(create_data)
            …
```

When `full_name = "Madonna"` (or `"Kirill"`, `"Andres"`, `"Chetan"`, `"Jerry"`):
- `parts = ["Madonna"]`
- `first_name = "Madonna"`
- `last_name = ""` ← empty string

### 2.5 Where the empty string is rejected

**File:** `Grins_irrigation_platform/src/grins_platform/schemas/customer.py:69-86`

```python
class CustomerCreate(BaseModel):
    """Schema for creating a new customer.

    Validates: Requirement 1.2, 1.3
    """

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Customer's first name",
    )
    last_name: str = Field(
        ...,
        min_length=1,                                    # ← strict
        max_length=100,
        description="Customer's last name",
    )
```

Pydantic v2 raises `ValidationError` on `min_length=1` violation:

```
1 validation error for CustomerCreate
last_name
  String should have at least 1 character [type=string_too_short,
  input_value='', input_type=str]
```

There is no `try/except` around the `CustomerCreate(...)` call (`webhooks.py:310-315`), and the surrounding `try` at `webhooks.py:316-331` only catches `DuplicateCustomerError`. So `ValidationError` propagates all the way up to `handle_event`, which logs `webhook_checkout_session_completed_failed` and rolls back the transaction.

### 2.6 Why Stripe Checkout produces single-word names

Stripe's hosted Checkout page collects the buyer's billing name in **one combined "Name" field** (cardholder name). It does not split into first/last fields. Whatever the customer types lands verbatim in `checkout.session.customer_details.name`. Common single-word inputs:
- Mononyms ("Madonna", "Bono", "Cher")
- Customer types only their first name (extremely common — see Bucket A below)
- Customer types a business name with no last name format (rare)
- Browser autofill behaves oddly and only fills one field

Reference: [Stripe Checkout — `customer_details` object](https://docs.stripe.com/api/checkout/sessions/object#checkout_session_object-customer_details). Stripe documents `name` as "The customer's full name or business name" — explicitly free-form.

---

## 3. Investigation timeline (2026-04-26)

| Step | Tool | Finding |
|---|---|---|
| 1 | Read screenshot `IMG_8061.HEIC` | Identified user-facing error string and which step (Complete Onboarding) |
| 2 | `Grep` for "couldn't find your session" in `Grins_irrigation` repo | Located string at `OnboardingPage.tsx:119` |
| 3 | Read `OnboardingPage.tsx` + `onboardingApi.ts` | Confirmed 404 from `/complete` is the only path to this string |
| 4 | Read `onboarding.py` + `onboarding_service.py` on platform `main` | Confirmed two 404 sources: `SessionNotFoundError` and `AgreementNotFoundForSessionError`; verified retry-with-backoff exists (4 attempts, 12s total) |
| 5 | Read `webhooks.py` `_handle_checkout_completed` on `main` | Mapped the 14-step transaction; identified `CustomerCreate` instantiation |
| 6 | `git log main..dev` on both repos | Confirmed prod main is missing the email/Resend wire-up (`db7befa` is dev-only); ruled out DNS-related causes |
| 7 | `mcp__stripe__get_stripe_account_info` | Confirmed live account `acct_1RDrfSG1xK8dFlaf` "Grin's Irrigation" |
| 8 | `mcp__railway__list-projects` + `list-services` | Located prod service `Grins_irrigation_platform` in project `zealous-heart` |
| 9 | `mcp__railway__list-variables environment=production` | Verified `STRIPE_SECRET_KEY=sk_live_…`, `STRIPE_WEBHOOK_SECRET` set, `CORS_ORIGINS` correct, `RAILWAY_PUBLIC_DOMAIN=grinsirrigationplatform-production.up.railway.app` |
| 10 | `mcp__railway__get-logs filter=webhook lines=300` | All `POST /api/v1/webhooks/stripe` returning 200 → secret correct, signature verification passing |
| 11 | `mcp__railway__get-logs filter=@level:error lines=200 json=true` | **Smoking gun**: Three explicit `webhook_checkout_session_completed_failed` entries with `ValidationError: last_name String should have at least 1 character`. 16 additional `webhook_invoice_paid_failed: "No agreement for subscription …"` entries — downstream effect |
| 12 | `vercel env pull --environment=production` on `grins-irrigation` and `frontend` projects | Verified `VITE_API_URL=https://grinsirrigationplatform-production.up.railway.app` (pointing at prod Railway, not dev) |
| 13 | `stripe subscriptions retrieve … --api-key sk_live_… --live` for all 19 subs | Cross-referenced sub_id → cus_id, retrieved metadata (tier, zones, consent token) |
| 14 | `stripe customers retrieve … --live` for all 19 customers | Retrieved name/email/phone, classified into Bucket A (single-word — matches bug), Bucket B (multi-word — different cause), Bucket C (no metadata — admin-created) |

---

## 4. Production environment confirmation

All findings below are from the **live/production** environment, not dev. Evidence:

- **Stripe account:** `acct_1RDrfSG1xK8dFlaf` (live). Note: the dev sandbox is a separate account `acct_1RDrfZQDNzCTp6j5` (`Z` not `S`); the local `stripe` CLI is configured for the sandbox by default, but all queries in this investigation passed `--live` and `--api-key sk_live_…` explicitly.
- **Railway service:** `Grins_irrigation_platform` in environment `production` (project `zealous-heart`, ID `13317c6b-ca1f-48dd-b00b-91bfda8a7e5a`). The dev counterpart `Grins-dev` is a separate service.
- **Postgres:** `Postgres` (production). The dev DB is `Postgres-PH_d` (separate).
- **Public domain:** `grinsirrigationplatform-production.up.railway.app`.
- **Vercel project:** `grins-irrigation` (`prj_4cEl6tD6pgaXGnspzJTmxx0Kw8Qw`) under team `team_FANuLIVR0JFqdlXMuNgcJKvi`. `VITE_API_URL` resolves to the production Railway URL.
- **Branches deployed:**
  - Frontend (`Grins_irrigation` repo): `main` at commit `5daabd0` ("ui(onboarding): remove preferred-schedule dropdown from customer form").
  - Backend (`Grins_irrigation_platform` repo): `main` at commit `397c534` ("release: dev → main 2026-04-14 (squash of 93 commits, f308749..b60f740)") — last deployed 2026-04-14.

---

## 5. Evidence — production Railway logs

Three explicit `ValidationError` events surfaced when filtering on `@level:error`. Log entries are JSON, reformatted here for readability. All timestamps UTC.

### 5.1 Bucket A event #1 — Jerry (cus_UNsDC0zDE527dT)

```json
{
  "timestamp": "2026-04-22T19:29:38.972230Z",
  "level": "error",
  "logger": "StripeWebhookHandler",
  "event": "stripe.stripewebhookhandler.webhook_checkout_session_completed_failed",
  "error_type": "ValidationError",
  "error": "1 validation error for CustomerCreate\\nlast_name\\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]\\n    For further information visit https://errors.pydantic.dev/2.12/v/string_too_short",
  "stripe_event_id": "evt_1TP6SsG1xK8dFlafLXj9Pcl4",
  "request_id": "c815a659-784d-4439-a7d2-31cbaafb2650",
  "exc_info": true
}
```

Followed milliseconds later (same request_id is not used; Stripe re-fires `invoice.paid` separately):

```json
{
  "timestamp": "2026-04-22T19:29:38.789156Z",
  "level": "error",
  "logger": "StripeWebhookHandler",
  "event": "stripe.stripewebhookhandler.webhook_invoice_paid_failed",
  "error_type": "ValueError",
  "error": "No agreement for subscription sub_1TP6SqG1xK8dFlafOGEwjNu9",
  "request_id": "8b4df959-7fc8-4217-a2d1-a20b965359d9",
  "exc_info": true
}
```

### 5.2 Bucket A event #2 — Andres (cus_UOcRXOUJlQqgY3)

```json
{
  "timestamp": "2026-04-24T19:16:02.191327Z",
  "level": "error",
  "logger": "StripeWebhookHandler",
  "event": "stripe.stripewebhookhandler.webhook_checkout_session_completed_failed",
  "error_type": "ValidationError",
  "error": "1 validation error for CustomerCreate\\nlast_name\\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]",
  "stripe_event_id": "evt_1TPpCnG1xK8dFlafmfSObbxa",
  "request_id": "666bb502-0dfb-47ab-970d-f3abcd380c45",
  "exc_info": true
}
```

```json
{
  "timestamp": "2026-04-24T19:16:02.890460Z",
  "level": "error",
  "event": "stripe.stripewebhookhandler.webhook_invoice_paid_failed",
  "error": "No agreement for subscription sub_1TPpCmG1xK8dFlafzNPCfJWB",
  "error_type": "ValueError",
  "request_id": "e3fddfd4-eb7d-43ae-85fd-2a546fdb3836"
}
```

### 5.3 Bucket A event #3 — Chetan (cus_UP2QPiKeru3CrC)

```json
{
  "timestamp": "2026-04-25T22:06:44.187072Z",
  "level": "error",
  "logger": "StripeWebhookHandler",
  "event": "stripe.stripewebhookhandler.webhook_checkout_session_completed_failed",
  "error_type": "ValidationError",
  "error": "1 validation error for CustomerCreate\\nlast_name\\n  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]",
  "stripe_event_id": "evt_1TQELXG1xK8dFlafoofKg46o",
  "request_id": "c4ca6d83-2ee9-47e8-9758-0a5849be4f63",
  "exc_info": true
}
```

```json
{
  "timestamp": "2026-04-25T22:06:44.393278Z",
  "level": "error",
  "event": "stripe.stripewebhookhandler.webhook_invoice_paid_failed",
  "error": "No agreement for subscription sub_1TQELWG1xK8dFlafeg0JTAGI",
  "error_type": "ValueError",
  "request_id": "737a3ea3-f016-402c-ad6f-855c9f5cabd0"
}
```

### 5.4 Bucket B `invoice.paid` failures (no matching `checkout_session_completed_failed` log line found)

For these, only the downstream invoice failure is in retention. The original checkout failure either rolled out of the log retention window, was logged at a level we filtered out, or had a different exception class:

| Sub ID | Timestamp (UTC) | Customer (from Stripe) |
|---|---|---|
| `sub_1TOTzjG1xK8dFlafZGGFo5DP` | 2026-04-21 02:25:02 | diane beddor (`cus_UNESkIJRi3YoU5`) |
| `sub_1TOg3YG1xK8dFlaf8ejiSWUT` | 2026-04-21 15:17:47 | Laura Collier (`cus_UNQvNrkrEaXL8M`) |
| `sub_1TOgC0G1xK8dFlafpN8UpefE` | 2026-04-21 15:26:30 | David Schmaltz (`cus_UNR4hcCBMD1ZfN`) |
| `sub_1TOhHCG1xK8dFlafsUHsIxEc` | 2026-04-21 16:35:56 | James R Cosmano (`cus_UNSBFsCuIV2KPP`) |
| `sub_1TOjcOG1xK8dFlafK4Pq1GLU` | 2026-04-21 19:05:59 | Kristi Hendricks (`cus_UNUbMdMIfI2YF6`) |
| `sub_1TP11aG1xK8dFlafZciW8QiV` | 2026-04-22 13:41:08 | Gail Ancier (`cus_UNmaaSOGYgSl1t`) |
| `sub_1TPB8eG1xK8dFlafZjjZuCHL` | 2026-04-23 00:29:06 | Alex Lelchuk (`cus_UNx25pVeAYq3gF`) |
| `sub_1TPrM1G1xK8dFlafX2atcFBn` | 2026-04-24 21:33:43 | Sulmaan Khan (`cus_UOef8o6ccXxzls`) |
| `sub_1TPs4RG1xK8dFlaf2mFtDzjD` | 2026-04-24 22:19:36 | Eric W Forsberg (`cus_UOfPZyijmGI4pT`) |
| `sub_1TPtmQG1xK8dFlafQHHOGDo8` | 2026-04-25 00:09:08 | Brent Ryan (`cus_UOhASJmmnEtzF6`) ⚠️ |
| `sub_1TQB69G1xK8dFlafMTSh9YHt` | 2026-04-25 18:38:39 | Daniel kahner (`cus_UOz4mUjZkgFaJW`) |
| `sub_1TQBUlG1xK8dFlaf5X9O10Se` | 2026-04-25 19:04:06 | Mitchell Bay Townhomes Association (`cus_UOzPVYtbrdgI0t`) |
| `sub_1TQBeOG1xK8dFlafPJKDjyN3` | 2026-04-25 19:14:02 | Shores Of Kraetz Lake (`cus_UOzbMlO04AqRLj`) |
| `sub_1TQDeOG1xK8dFlaf35SZ079r` | 2026-04-25 21:22:10 | Prasanth Prabhakaran (`cus_UP1hedqzSy65OQ`) |
| `sub_1TQILUG1xK8dFlafDLMNIIt3` | 2026-04-26 02:22:58 | Elizabeth A Sweeney (`cus_UP6YEqUMoFReDZ`) |
| `sub_1TQTVLG1xK8dFlaf3fN2xE1G` | 2026-04-26 14:17:53 | Madalyn Larsen (`cus_UPI53Sax9TDMTm`) |

⚠️ Brent Ryan's phone `+17634588674` is identical to Bucket C's "Shores Of Kraetz Lake" — same-phone-different-email pattern matches BUG #18 (DuplicateCustomerError); details in §7.

---

## 6. Affected customers — full inventory

### 6.1 Bucket A — Confirmed single-word name (the bug this document is about)

These three have an explicit `webhook_checkout_session_completed_failed` log entry with `ValidationError` AND a single-word name in Stripe. The fix in `.agents/plans/webhook-empty-last-name-fix.md` + a Stripe event replay will recover them.

| Customer ID | Name (Stripe) | Email | Phone | Sub ID | Tier | Zones | Stripe checkout event | Failed at (UTC) |
|---|---|---|---|---|---|---|---|---|
| `cus_UP2QPiKeru3CrC` | **Chetan** | cshenoy3@gmail.com | +1 732-221-4061 | `sub_1TQELWG1xK8dFlafeg0JTAGI` | essential-residential | 6 | `evt_1TQELXG1xK8dFlafoofKg46o` | 2026-04-25 22:06 |
| `cus_UOcRXOUJlQqgY3` | **Andres** | act.msp@gmail.com | +1 651-756-9816 | `sub_1TPpCmG1xK8dFlafzNPCfJWB` | essential-residential | 8 | `evt_1TPpCnG1xK8dFlafmfSObbxa` | 2026-04-24 19:15 |
| `cus_UNsDC0zDE527dT` | **Jerry** | jerrymitchell3@gmail.com | +1 612-618-1487 | `sub_1TP6SqG1xK8dFlafOGEwjNu9` | essential-residential | 12 | `evt_1TP6SsG1xK8dFlafLXj9Pcl4` | 2026-04-22 19:29 |

Subscription metadata for each (from `stripe subscriptions retrieve --live`):

```
sub_1TQELWG1xK8dFlafeg0JTAGI (Chetan)
  status: active
  created: 2026-04-25 22:06 UTC
  items:    price_1TFXuUG1xK8dFlafdvfKzu5m (essential-residential), qty=1
  metadata: consent_token=dff655d9-a31f-4493-804f-8b691085b3ae,
            email_marketing_consent=false, has_lake_pump=false,
            has_rpz_backflow=false, package_tier=essential-residential,
            package_type=residential, zone_count=6

sub_1TPpCmG1xK8dFlafzNPCfJWB (Andres)
  status: active
  created: 2026-04-24 19:15 UTC
  items:    price_1TFXuUG1xK8dFlafdvfKzu5m (essential-residential), qty=1
  metadata: consent_token=4844a4eb-f34b-440f-ba6e-ae1409092bc6,
            email_marketing_consent=false, has_lake_pump=false,
            has_rpz_backflow=false, package_tier=essential-residential,
            package_type=residential, zone_count=8

sub_1TP6SqG1xK8dFlafOGEwjNu9 (Jerry)
  status: active
  created: 2026-04-22 19:29 UTC
  items:    price_1TFXuUG1xK8dFlafdvfKzu5m (essential-residential), qty=1
            price_1TP6S5G1xK8dFlafQmPJFgvj (zone surcharge for >5 zones), qty=1
  metadata: consent_token=14c23e4e-7857-4f42-ab41-db1dc3211a2a,
            email_marketing_consent=false, has_lake_pump=false,
            has_rpz_backflow=false, package_tier=essential-residential,
            package_type=residential, zone_count=12
```

### 6.2 Bucket B — Different / unidentified failure mode

These 14 customers have valid 2+ word names yet their `checkout.session.completed` webhook still failed. **The fix in the plan will NOT help these.** Each needs separate root-cause analysis before any replay.

| Customer ID | Name (Stripe) | Email | Phone | Sub ID | Tier | Zones | Sub created (UTC) |
|---|---|---|---|---|---|---|---|
| `cus_UPI53Sax9TDMTm` | Madalyn Larsen | wohlmad@gmail.com | +1 262-441-0662 | `sub_1TQTVLG1xK8dFlaf3fN2xE1G` | essential-residential | 8 | 2026-04-26 14:17 |
| `cus_UP6YEqUMoFReDZ` | Elizabeth A Sweeney | Easweeney6@gmail.com | +1 952-826-9616 | `sub_1TQILUG1xK8dFlafDLMNIIt3` | essential-residential | 8 | 2026-04-26 02:22 |
| `cus_UP1hedqzSy65OQ` | Prasanth Prabhakaran | prasanthorion@yahoo.co.in | +1 920-634-8275 | `sub_1TQDeOG1xK8dFlaf35SZ079r` | essential-residential | 5 | 2026-04-25 21:22 |
| `cus_UOz4mUjZkgFaJW` | Daniel kahner | dkahner@icloud.com | +1 612-860-4614 | `sub_1TQB69G1xK8dFlafMTSh9YHt` | essential-residential | 7 | 2026-04-25 18:38 |
| `cus_UOhASJmmnEtzF6` | Brent Ryan ⚠️ | commerce@brentjryan.us | +1 763-458-8674 | `sub_1TPtmQG1xK8dFlafQHHOGDo8` | professional-residential | 6 | 2026-04-25 00:09 |
| `cus_UOfPZyijmGI4pT` | Eric W Forsberg | ewforsberg@msn.com | +1 612-434-2896 | `sub_1TPs4RG1xK8dFlaf2mFtDzjD` | essential-residential | 5 | 2026-04-24 22:19 |
| `cus_UOef8o6ccXxzls` | Sulmaan Khan | sulmaanmkhan@gmail.com | +1 612-865-8486 | `sub_1TPrM1G1xK8dFlafX2atcFBn` | essential-residential | 7 | 2026-04-24 21:33 |
| `cus_UNx25pVeAYq3gF` | Alex Lelchuk | lely09@gmail.com | +1 612-382-4953 | `sub_1TPB8eG1xK8dFlafZjjZuCHL` | essential-residential | 8 | 2026-04-23 00:29 |
| `cus_UNmaaSOGYgSl1t` | Gail Ancier | yaelancier@gmail.com | +1 612-799-9833 | `sub_1TP11aG1xK8dFlafZciW8QiV` | essential-residential + RPZ | 3 | 2026-04-22 13:41 |
| `cus_UNUbMdMIfI2YF6` | Kristi Hendricks | kjhendricks09@gmail.com | +1 763-688-3751 | `sub_1TOjcOG1xK8dFlafK4Pq1GLU` | professional-residential | 12 | 2026-04-21 19:05 |
| `cus_UNSBFsCuIV2KPP` | James R Cosmano | James.cosmano@gmail.com | +1 701-200-6275 | `sub_1TOhHCG1xK8dFlafsUHsIxEc` | winterization-only-residential | 7 | 2026-04-21 16:35 |
| `cus_UNR4hcCBMD1ZfN` | David Schmaltz | dschmaltz@merchantgould.com | +1 612-201-9815 | `sub_1TOgC0G1xK8dFlafpN8UpefE` | essential-residential | 5 | 2026-04-21 15:26 |
| `cus_UNQvNrkrEaXL8M` | Laura Collier | laurasc8375@yahoo.com | +1 612-237-5478 | `sub_1TOg3YG1xK8dFlaf8ejiSWUT` | essential-residential | 7 | 2026-04-21 15:17 |
| `cus_UNESkIJRi3YoU5` | diane beddor | dibeddor@gmail.com | +1 612-581-8014 | `sub_1TOTzjG1xK8dFlafZGGFo5DP` | essential-residential | 12 | 2026-04-21 02:24 |

⚠️ **Brent Ryan + Shores Of Kraetz Lake** share phone `+17634588674`. This is the BUG #18 same-phone-different-email pattern (`E2E-STRESS-TEST-REPORT.md:21-23`). Brent's webhook crashed first (for an as-yet-unknown reason); when "Shores Of Kraetz Lake" arrived later with the same phone but a different email, the existing-customer phone fallback found nothing (Brent's record was rolled back), and "Shores" then went down its own crash path. This is a candidate hypothesis for some of Bucket B's other failures — if any other Bucket B customer's phone collides with another orphan or with an existing customer, we may be seeing cascading rollback. Needs DB query to confirm.

### 6.3 Bucket C — Likely admin-created or non-checkout subscriptions

These two have **empty subscription metadata** (no `consent_token`, no `package_tier`, no `zone_count`). That signature points to subscriptions created directly in the Stripe Dashboard or via Stripe API, not through the website checkout flow. There would be no `checkout.session.completed` event for these — only `invoice.paid` — which is why the only log entry is `webhook_invoice_paid_failed: "No agreement for subscription …"`. They never had a chance to create an agreement.

| Customer ID | Name (Stripe) | Email | Phone | Sub ID | Items | Sub created (UTC) |
|---|---|---|---|---|---|---|
| `cus_UOzbMlO04AqRLj` | Shores Of Kraetz Lake | commerce@brentjryan.us | +1 763-458-8674 | `sub_1TQBeOG1xK8dFlafPJKDjyN3` | 2 line items, qty=3, metadata={} | 2026-04-25 19:14 |
| `cus_UOzPVYtbrdgI0t` | Mitchell Bay Townhomes Association | rogerdsims@gmail.com | +1 970-214-1137 | `sub_1TQBUlG1xK8dFlaf5X9O10Se` | 2 line items, qty=4, metadata={} | 2026-04-25 19:04 |

Do **not** replay these — they need an agreement created manually with whatever pricing the operator agreed to. Confirm with whoever created them in the Stripe Dashboard.

---

## 7. Hypotheses ruled out

| Hypothesis | Evidence collected | Verdict |
|---|---|---|
| Resend MX/TXT DNS records broke session/webhook/cookie flow | Records scoped to `send.grinsirrigation.com` and `resend._domainkey.grinsirrigation.com` only. `email_service.py` on prod `main` is the stub version (no `import resend`). The Resend wire-up commit `db7befa` is on dev only. | **Not the cause.** DNS additions are orthogonal to the crash. |
| Vercel `VITE_API_URL` points at dev backend | `vercel env pull --environment=production` returned `VITE_API_URL=https://grinsirrigationplatform-production.up.railway.app` for both Vercel projects (`grins-irrigation` and `frontend`). | **Not the cause.** Frontend correctly hits prod backend. |
| `STRIPE_WEBHOOK_SECRET` missing or stale | Railway env vars show `STRIPE_WEBHOOK_SECRET=whsec_X9C7…` set. All `POST /api/v1/webhooks/stripe` returning 200 → signature verification passing. | **Not the cause.** |
| Stripe in test mode in production | Railway `STRIPE_SECRET_KEY=sk_live_…`. Webhook handler reaching real customer data. | **Not the cause.** |
| CORS misconfig | `CORS_ORIGINS` includes `https://grinsirrigation.com`, `https://www.grinsirrigation.com`, plus all the Vercel preview URLs. | **Not the cause.** |
| Webhook race condition (12s retry window insufficient) | `OnboardingService.complete_onboarding` retries 4× with 0+2+4+6 = 12s delay. Possible that some Bucket B failures are this. But Bucket A is *not* this — those have an explicit ValidationError. | **Secondary, not primary.** Some Bucket B may still be this. |
| BUG #15 timezone regression | `git show main:src/grins_platform/models/job.py | grep DateTime(timezone=True)` shows the fix is in place on prod main. | **Not the cause.** |
| BUG #18 DuplicateCustomerError | Phone fallback + safety-net in webhook handler exists on prod main (`webhooks.py:288-331`). However, Brent Ryan / Shores Of Kraetz Lake may be exhibiting this under cascading rollback conditions. | **Possible secondary cause for one Bucket B customer pair.** |
| Database connection pool exhaustion | No connection-pool errors in 200-line filtered log dump. | **Not seen in evidence.** |
| Pricing IDs misconfigured (per memory: 2026-04-15 dev tier mismatch) | All Bucket A subs use `price_1TFXuUG1xK8dFlafdvfKzu5m` which matches the live tier price for essential-residential. | **Not the cause.** |
| Stripe webhook URL changed/unreachable | All recent webhook deliveries logged as 200 OK on Railway. | **Not the cause.** |

---

## 8. The fix

A detailed implementation plan exists at:

```
/Users/kirillrakitin/Grins_irrigation_platform/.agents/plans/webhook-empty-last-name-fix.md
```

Summary:
- **Single-line behavior change** in `webhooks.py:283`: `last_name = parts[1] if len(parts) > 1 else _MISSING_LAST_NAME_PLACEHOLDER` (sentinel `"-"`).
- **One module-level constant** added at top of `webhooks.py`.
- **One conditional log line** when the placeholder is used (`webhook_customer_placeholder_last_name`).
- **Four new unit tests** in `test_webhook_handlers.py` covering single-word, empty, whitespace-only, and multi-word names.
- **Schema unchanged** — `CustomerCreate.last_name = Field(..., min_length=1, ...)` stays as-is. Every other caller (admin form, lead conversion) keeps its strict invariant.
- **No try/except added** — genuine validation errors continue to propagate as before.

Confidence: 9/10 for one-pass implementation success per the plan.

---

## 9. Recovery steps after deploying the fix

### 9.1 Bucket A (3 customers) — replay the original `checkout.session.completed` event

For each of:
- `evt_1TQELXG1xK8dFlafoofKg46o` (Chetan)
- `evt_1TPpCnG1xK8dFlafmfSObbxa` (Andres)
- `evt_1TP6SsG1xK8dFlafLXj9Pcl4` (Jerry)

**Procedure** (do this AFTER the fix is deployed to Railway production):

1. Log in to Stripe Dashboard (live mode) → Developers → Events.
2. Search for the `evt_…` ID.
3. Click "Resend" on the event to redeliver it to the production webhook.
4. Watch Railway logs for `webhook_customer_placeholder_last_name` AND `webhook_checkout_completed` (success).
5. Verify the agreement now exists by querying production Postgres:
   ```sql
   SELECT id, agreement_number, status, stripe_subscription_id, customer_id, created_at
     FROM service_agreements
    WHERE stripe_subscription_id IN (
      'sub_1TQELWG1xK8dFlafeg0JTAGI',
      'sub_1TPpCmG1xK8dFlafzNPCfJWB',
      'sub_1TP6SqG1xK8dFlafOGEwjNu9'
    );
   ```
6. The customer's onboarding URL is `https://grinsirrigation.com/onboarding?session_id=cs_live_<the_session_id_from_the_event_payload>`. The session_id is in the event's `data.object.id`. After replay, that URL should load the form and submit successfully.
7. Reach out to each customer (Chetan, Andres, Jerry) by email or phone with the recovered onboarding link so they can fill in property details (zone count, gate code, dogs, access instructions, preferred service times, per-service week selections). Without onboarding completion, the agreement exists but property/job linkage is incomplete.

**Stripe event retention is 30 days.** Earliest Bucket A event is from 2026-04-22 — must be replayed before approximately 2026-05-22. Reasonable buffer left as of writing (2026-04-26).

### 9.2 Bucket B (14 customers) — separate investigation required

**Do NOT replay these without first identifying the actual crash class.** Replaying would re-trigger whatever bug orphaned them, with the same outcome.

Suggested follow-up tasks:
1. Pull deeper Railway logs (longer retention) for each of the 14 sub IDs in §6.2 to find the original `webhook_checkout_session_completed_failed` entry (if it survived).
2. For Brent Ryan + Shores Of Kraetz Lake (shared phone): query production Postgres for any existing customer with phone `+17634588674` — there should be either zero (both were rolled back) or one (one succeeded, one didn't).
3. Categorize each Bucket B failure into: (a) race condition (12s timeout), (b) duplicate-phone cascade, (c) some unknown ValidationError class, (d) DB constraint violation. Each may need its own fix.
4. For each customer, prepare a manual SQL backfill or Stripe replay plan once the cause is known.

### 9.3 Bucket C (2 customers) — manual reconciliation

`sub_1TQBeOG1xK8dFlafPJKDjyN3` (Shores Of Kraetz Lake) and `sub_1TQBUlG1xK8dFlaf5X9O10Se` (Mitchell Bay Townhomes Association) have empty checkout metadata. They need:
1. Confirmation from whoever created them in the Stripe Dashboard about intended tier, zone count, and pricing.
2. Manual `INSERT INTO service_agreements` with derived fields, plus `JobGenerator`-equivalent job creation.
3. Customer record creation if not already present in the DB (Brent Ryan's `+17634588674` may collide here too).

---

## 10. Why this wasn't caught earlier

- **Pre-launch E2E testing** used multi-word names exclusively (`smoke-test-2.md` and `smoke-test-3.md` both used "Smoke Test User", "E2E-PROD-TEST Essential", "Jane Doe", "John Smith"). The single-word path was never exercised against the strict schema.
- **Unit test coverage** for `_handle_checkout_completed` (`test_webhook_handlers.py`) tests both `"Jane Doe"` (multi-word) and `"John"` (single word) — but the `"John"` test short-circuits via email-match at `webhooks.py:271-273`, so `CustomerCreate` is never actually exercised on a single-word input. The bug is thus invisible to the existing test suite.
- **Production deploy was 2026-04-14**; first known affected customer (Bucket B) was 2026-04-21; first confirmed Bucket A failure was Jerry on 2026-04-22. Approximately 1 week of silent failures before the user's first awareness on 2026-04-26.

---

## 11. References

### 11.1 Internal documents

- `/Users/kirillrakitin/Grins_irrigation_platform/.agents/plans/webhook-empty-last-name-fix.md` — implementation plan
- `/Users/kirillrakitin/Grins_irrigation/changes_part_2.md:113-134` — prior "couldn't find your session" fix (race condition retry, March 2026)
- `/Users/kirillrakitin/Grins_irrigation/smoke-test-2.md` — BUG #15 (timezone) discovery, March 2026
- `/Users/kirillrakitin/Grins_irrigation/e2e-screenshots/E2E-STRESS-TEST-REPORT.md` — BUG #18 (DuplicateCustomerError) discovery, March 2026
- `/Users/kirillrakitin/Grins_irrigation/production-deployment-log.md` — March 14 production cutover log

### 11.2 Code references (prod main, as of investigation date)

- `Grins_irrigation_platform` @ `397c534` (backend)
  - `src/grins_platform/api/v1/webhooks.py:220-474` — `_handle_checkout_completed`
  - `src/grins_platform/api/v1/webhooks.py:281-283` — name splitting (the bug)
  - `src/grins_platform/api/v1/webhooks.py:309-315` — `CustomerCreate` instantiation (the crash site)
  - `src/grins_platform/schemas/customer.py:69-86` — `CustomerCreate` schema
  - `src/grins_platform/services/onboarding_service.py:316-339` — retry-with-backoff for the race condition
  - `src/grins_platform/api/v1/onboarding.py:434-443` — `AgreementNotFoundForSessionError` → 404

- `Grins_irrigation` @ `5daabd0` (frontend)
  - `frontend/src/features/onboarding/components/OnboardingPage.tsx:119` — user-facing error string
  - `frontend/src/features/onboarding/api/onboardingApi.ts:34-52` — `completeOnboarding` API call

### 11.3 External references

- [Stripe Checkout — `customer_details` object](https://docs.stripe.com/api/checkout/sessions/object#checkout_session_object-customer_details)
- [Pydantic v2 — `min_length` constraint](https://docs.pydantic.dev/latest/concepts/fields/#string-constraints)
- [Stripe — Resending events from the Dashboard](https://docs.stripe.com/webhooks#manually-trigger-events)

### 11.4 Investigation tooling used

- `mcp__stripe__get_stripe_account_info`, `list_customers`, `list_subscriptions`, `fetch_stripe_resources`, `stripe_api_search`
- `mcp__railway__check-railway-status`, `list-projects`, `list-services`, `list-deployments`, `list-variables`, `get-logs` (filter `@level:error`, `last_name`, `webhook`, etc.)
- `mcp__vercel__list_teams`, `list_projects`, `get_project`, `get_runtime_logs`
- Local `stripe` CLI (live mode via `--api-key` and `--live`) for customer/subscription detail retrieval
- Local `vercel` CLI for `env pull --environment=production`
- Local `git`, `grep`, `Read` for code introspection on both repos

---

## 12. Open questions / followups

1. **(Resolved — see §13.)** ~~What is the actual crash class for each Bucket B customer?~~ Bucket B has been investigated; root cause is a different class (webhook ordering race + onboarding-submit timing) and is documented below.
2. **Is there a phone-collision pattern across other Bucket B customers?** Brent Ryan + Shores Of Kraetz Lake (Bucket C) share `+17634588674`. No other Bucket B-internal collisions found. Need a DB query to check Bucket B vs existing customers from before April 21.
3. **Should the platform add an end-to-end test that fires `checkout.session.completed` with a single-word customer name through the real webhook signature path?** Currently, single-word coverage exists in `test_webhook_handlers.py` only via mocked dependencies; an integration test against an in-memory DB would guard against future regressions of the same shape.
4. **Should we add a feature-flag-gated DLQ** (dead-letter queue) for failed webhooks? Today, when `_handle_checkout_completed` raises, the event is logged-and-rolled-back, but Stripe's retry retries the same broken handler. A DLQ would catch the original payload for offline replay.
5. **Should `CustomerCreate.last_name` be loosened generally** (separate from the webhook fix) to accept empty strings, normalizing to a placeholder server-side? The plan deliberately doesn't do this — but if multiple integration points (webhook, lead import, future SMS-only signups) all run into the same boundary, centralizing the placeholder logic in the schema may make sense as a follow-up. Out of scope for the immediate fix.
6. **Should the 12-second retry budget in `OnboardingService.complete_onboarding` be extended?** See §13.4. The current budget (4 attempts at 0+2+4+6=12s) works for Essential tiers (2 jobs) but is borderline for Premium (5+ jobs). **Update (§15):** DB evidence shows the 12s budget was sufficient for all 14 Bucket B customers in production — every one returned 200 OK. No retry-budget change is justified by current evidence.

---

# §13 — Root cause for Bucket B (added 2026-04-26 after follow-up investigation)

> **⚠️ §13.3 was partially wrong — see §15 for DB-confirmed correction (2026-04-27).** The "ordering-race log noise" finding in §13.1 / §13.2 is correct. The "onboarding-submit race → 404 → never persisted" hypothesis in §13.3 is contradicted by Railway access logs and a read-only DB query: every Bucket B customer's `POST /onboarding/complete` returned **200 OK**, and every `service_agreements` row is `status=active` with `property_id NOT NULL` and `service_week_preferences` populated. They are fully onboarded. The customer-visible "We couldn't find your session" symptom in §1 was *not* experienced by any Bucket B customer — it remains scoped to Bucket A.

## 13.1 Summary

**Bucket B is NOT a `checkout.session.completed` crash.** The handler runs to completion for all 14 customers. The "No agreement for subscription" error log entries are produced by the **`invoice.paid` handler** running in **parallel** (and arriving slightly *before*) the `checkout.session.completed` handler — a Stripe webhook ordering race. The error log line is largely **diagnostic noise**, not the customer-impacting failure.

~~The user-visible "We couldn't find your session" symptom for Bucket B customers is most likely the **pre-existing onboarding-submit race**: the customer's `POST /onboarding/complete` request lands before the `checkout.session.completed` handler has finished committing the agreement. The 12-second retry budget in `OnboardingService.complete_onboarding` is insufficient under real production load for some tiers.~~ **(Superseded by §15.)** No Bucket B customer hit a 404 on `/onboarding/complete`; the 12s retry budget was sufficient for all of them. The "user-visible symptom" framing in §1 applies only to Bucket A.

This is **a different bug class from Bucket A** and is **not fixed by the empty-`last_name` plan**. The agreements for Bucket B customers **DO exist in the production database** (confirmed by §15 query), and those customers are already fully onboarded — no replay or outreach required.

## 13.2 Evidence

### 13.2.1 The handler reached step 13 (email send) for all 14 customers

`_handle_checkout_completed` has 14 ordered operations. Step 13 is the `send_confirmation_email` call at `webhooks.py:446`. On production main, `email_service.py` is the **stub** — `is_configured` is False, so `_send_email` emits a `warn`-level log entry `email.send.pending` with `message: "Email API not configured"` and the masked recipient.

Filtering Railway logs at `@level:warn` for the time window 2026-04-21 → 2026-04-26 reveals **a 1:1 timestamp+email match** between Bucket B customer emails and `email.send.pending` warning entries. Every one of the 14 Bucket B customers has a corresponding warning at the right second:

| Bucket B customer | Email (full) | Warning recipient (masked) | Warning timestamp (UTC) |
|---|---|---|---|
| diane beddor | dibeddor@gmail.com | `d***@gmail.com` | 2026-04-21 02:25:02.364 |
| Laura Collier | laurasc8375@yahoo.com | `l***@yahoo.com` | 2026-04-21 15:17:48.105 |
| David Schmaltz | dschmaltz@merchantgould.com | `d***@merchantgould.com` | 2026-04-21 15:26:30.874 |
| James Cosmano | James.cosmano@gmail.com | `J***@gmail.com` | 2026-04-21 16:35:57.262 |
| Kristi Hendricks | kjhendricks09@gmail.com | `k***@gmail.com` | 2026-04-21 19:05:59.469 |
| Gail Ancier | yaelancier@gmail.com | `y***@gmail.com` | 2026-04-22 13:41:08.403 |
| Alex Lelchuk | lely09@gmail.com | `l***@gmail.com` | 2026-04-23 00:29:07.239 |
| Sulmaan Khan | sulmaanmkhan@gmail.com | `s***@gmail.com` | 2026-04-24 21:33:43.836 |
| Eric Forsberg | ewforsberg@msn.com | `e***@msn.com` | 2026-04-24 22:19:37.307 |
| Brent Ryan | commerce@brentjryan.us | `c***@brentjryan.us` | 2026-04-25 00:09:09.050 |
| Daniel kahner | dkahner@icloud.com | `d***@icloud.com` | 2026-04-25 18:38:39.620 |
| Prasanth Prabhakaran | prasanthorion@yahoo.co.in | `p***@yahoo.co.in` | 2026-04-25 21:22:10.965 |
| Elizabeth Sweeney | Easweeney6@gmail.com | `E***@gmail.com` | 2026-04-26 02:22:58.712 |
| Madalyn Larsen | wohlmad@gmail.com | `w***@gmail.com` | 2026-04-26 14:17:53.139 |

Each warning is logged from inside `EmailService._send_email`. To reach that line, `_handle_checkout_completed` must have already executed steps 1-12 in the same transaction:

1. ✓ Customer found/created (otherwise `agreement.id` reference at line 449 would fail)
2. ✓ `customer.stripe_customer_id` updated
3. ✓ Tier resolved
4. ✓ `agreement` created (via `agreement_svc.create_agreement`)
5. ✓ Agreement transitioned to `ACTIVE`
6. ✓ Surcharge calculated and persisted
7. ✓ `email_marketing_consent` propagated to customer
8. ✓ Seasonal jobs generated (`job_gen.generate_jobs`)
9. ✓ Agreement refreshed
10. ✓ Orphaned consent records linked
11. ✓ SMS consent transferred to customer
12. ✓ Pre-sale disclosure created

**This effectively rules out the agreement creation step (4) as the failure point.** If step 4 raised, the email warning at step 13 could not have fired.

### 13.2.2 The `invoice.paid` "No agreement" log fires *before* the email warning, every time

A 14-of-14 timing pattern, computed by subtracting the `webhook_invoice_paid_failed` timestamp from the corresponding `email.send.pending` (confirmation) timestamp:

| Customer | invoice_paid_failed timestamp | email.send.pending timestamp | Δ (email - invoice) |
|---|---|---|---|
| diane beddor | 02:25:02.050 | 02:25:02.364 | +314 ms |
| Laura Collier | 15:17:47.857 | 15:17:48.105 | +248 ms |
| David Schmaltz | 15:26:30.466 | 15:26:30.874 | +408 ms |
| James Cosmano | 16:35:56.893 | 16:35:57.262 | +369 ms |
| Kristi Hendricks | 19:05:59.236 | 19:05:59.469 | +233 ms |
| Gail Ancier | 13:41:08.275 | 13:41:08.403 | +128 ms |
| Alex Lelchuk | 00:29:06.602 | 00:29:07.239 | +637 ms |
| Sulmaan Khan | 21:33:43.546 | 21:33:43.836 | +290 ms |
| Eric Forsberg | 22:19:36.862 | 22:19:37.307 | +445 ms |
| Brent Ryan | 00:09:08.280 | 00:09:09.050 | +770 ms |
| Daniel kahner | 18:38:39.211 | 18:38:39.620 | +409 ms |
| Prasanth Prabhakaran | 21:22:10.697 | 21:22:10.965 | +268 ms |
| Elizabeth Sweeney | 02:22:58.128 | 02:22:58.712 | +584 ms |
| Madalyn Larsen | 14:17:53.131 | 14:17:53.139 | +008 ms |

Every Δ is positive (between +8 ms and +770 ms). In **every case**, the `invoice.paid` handler fired its "No agreement" error before the `checkout.session.completed` handler reached step 13. This is the signature of a Stripe webhook ordering race: both events originated from the same Stripe operation, were dispatched in parallel, and the `invoice.paid` arrived/finished first.

### 13.2.3 The `invoice.paid` failure path returns gracefully (does not raise)

Looking at `webhooks.py:521-526` (production main):

```python
if not agreement:
    self.log_failed(
        "webhook_invoice_paid",
        error=ValueError(f"No agreement for subscription {subscription_id}"),
    )
    return
```

The handler logs `webhook_invoice_paid_failed` and **returns normally** — it does not raise. So the outer `handle_event` `try/except` does not catch this — the event is `mark_processed` and committed as "successfully processed" (a noop). No transaction rollback. No retry from Stripe.

This explains why we see the error log but the system is, in some sense, "fine" — the `invoice.paid` handler is designed to no-op when the agreement doesn't exist yet, on the (incorrect) assumption that the agreement will exist by the next invoice.

### 13.2.4 Why no `webhook_checkout_session_completed_failed` log for Bucket B

If `_handle_checkout_completed` had raised, `handle_event` (`webhooks.py:117-145`) would have caught it, rolled back, recorded a failed event record, and called `log_failed("webhook_checkout_session_completed", error=…)` — producing an `error`-level log. We have none of those for Bucket B subscription IDs.

The success path (`webhooks.py:120-126`) emits `log_completed("webhook_checkout_session_completed", …)` at **info** level. Our error/warn filter does not show info logs, and the available info-level retention window in Railway only goes back ~23 minutes from now. We cannot directly observe the success log entries — but the pattern of evidence (email warning → no error log → no rollback signal) is consistent with the success path executing.

### 13.2.5 Stripe API version + payload format are not the cause

I initially hypothesized that Stripe's `2025-03-31.basil` API version had moved `subscription` from the top-level field to `parent.subscription_details.subscription` (which `_extract_subscription_id` handles, but `_handle_checkout_completed` line 242 does not). Verified false:

```bash
curl -s 'https://api.stripe.com/v1/events/evt_1TQTVMG1xK8dFlafkJVXDuiv' \
  -u "$STRIPE_LIVE_KEY:" \
  -H 'Stripe-Version: 2025-03-31.basil'
```

Returns:
```
event_api_version: 2025-03-31.basil
obj.subscription: 'sub_1TQTVLG1xK8dFlaf3fN2xE1G'   # ← top-level, not nested
obj.parent: None
```

Webhook endpoint `we_1TBNmgG1xK8dFlafKXD6UaCf` confirmed at `api_version: 2025-03-31.basil`. The webhook payload Stripe delivered has `subscription` at the top level, so `webhooks.py:242` correctly extracts the sub ID and passes it to `agreement_svc.create_agreement`. The agreement should be created with the correct `stripe_subscription_id`.

## 13.3 Root cause (most likely)

**Bucket B failure mode is the pre-existing onboarding submit race** (the same race that motivated the 12-second retry in `changes_part_2.md:113-134`), now manifesting in production under real customer load. Sequence of events for an affected customer:

```
T+0.0s  Customer completes Stripe Checkout (clicks "Pay")
T+0.0s  Stripe creates subscription sub_xxx and dispatches BOTH events:
        - checkout.session.completed   (evt_A)
        - invoice.paid                 (evt_B, for the first invoice)

T+0.1s  Both events arrive at the FastAPI webhook endpoint, processed in
        parallel as separate requests. Each gets its own DB session via
        Depends(get_db).

T+0.1s  Customer's browser is redirected to /onboarding?session_id=cs_xxx
        Frontend immediately calls /verify-session — succeeds because that
        endpoint hits Stripe directly, no DB dependency.

T+0.3s  Process B (invoice.paid) finishes its tier/customer/agreement DB
        lookup, finds nothing, logs "No agreement for subscription sub_xxx",
        returns. Event marked as processed.

T+0.5s  Process A (checkout.session.completed) is mid-transaction:
        - Customer created
        - Tier resolved
        - Agreement created (with stripe_subscription_id=sub_xxx)
        - Agreement transitioned to ACTIVE
        - Surcharge applied
        - Jobs generated
        - Disclosure created
        - send_confirmation_email called → logs email.send.pending warning

T+1-5s  Process A continues:
        - send_welcome_email → second email.send.pending warning
        - session.flush()
        - Returns from _handle_checkout_completed
        - Back in handle_event:
          - mark_processed
          - log_completed (info)
          - session.commit()  ← AGREEMENT BECOMES VISIBLE TO OTHER TXNS

T+5-10s Customer fills out onboarding form (preferred times, week pickers,
        gate code, etc.). Total form time depends on customer reading speed
        and field count.

T+10s+  Customer clicks "Complete Onboarding"
        Frontend POST /api/v1/onboarding/complete with session_id

        OnboardingService.complete_onboarding fires:
          - Stripe.checkout.Session.retrieve(session_id) — returns sub_xxx
          - _find_agreement_by_subscription("sub_xxx")  — RACE WINDOW

        If commit at T+1-5s has happened: lookup succeeds, onboarding works.
        If commit hasn't happened yet: lookup fails (agreement invisible to
        this transaction).

        Retry budget kicks in: 4 attempts at 0+2+4+6 = 12s of wall-clock
        retries. If commit happens within 12s of first attempt: ok.
        If commit takes longer (slow tier, slow DB, contention): 404 → BUG.
```

**Two reinforcing race conditions cause the customer-visible bug:**

1. **Webhook ordering race** (logged but benign): `invoice.paid` arrives before `checkout.session.completed` finishes. The `_handle_invoice_paid` handler logs an error but no-ops — the `checkout.session.completed` handler subsequently creates and activates the agreement correctly. The error log is misleading: it suggests something broke, but nothing actually did.

2. **Onboarding submit race** (causes the customer-visible 404): The customer's `/complete` request can land before `checkout.session.completed`'s DB commit. The 12-second retry budget assumes the webhook always completes within 12s, which is not robust under production conditions:
   - Tier complexity affects step 8 (job generation): Premium with 5 monthly visits = 5+ job inserts; Essential with 2 services = 2 job inserts. More jobs = longer transaction.
   - DB contention between concurrent `invoice.paid` and `checkout.session.completed` transactions can extend the commit time (both are touching the same `service_agreements` row indirectly via foreign keys).
   - Network latency / slow Stripe API calls inside the handler add variable wall-clock time.

## 13.4 Why the 12-second retry isn't enough in practice

The retry in `OnboardingService.complete_onboarding` (`onboarding_service.py:316-339` on prod main):

```python
agreement = None
max_attempts = 4
for attempt in range(max_attempts):
    agreement = await self._find_agreement_by_subscription(str(subscription_id))
    if agreement:
        break
    if attempt < max_attempts - 1:
        delay = (attempt + 1) * 2  # 2s, 4s, 6s
        await asyncio.sleep(delay)
```

Total budget: 4 attempts at delays 0 + 2 + 4 + 6 = **12 seconds wall-clock**.

This was sized in 2026-03 (`changes_part_2.md`) against test mode loads. Under real production:

- The `_handle_checkout_completed` handler does ~14 sequential DB operations spanning customer creation, agreement creation, status transition, surcharge update, job generation (1 to 5+ inserts depending on tier), refresh, disclosure creation, two email sends.
- For Premium tier (5 monthly_visits + 1 spring + 1 fall = 7 jobs): the transaction is dominated by job inserts.
- Concurrent `invoice.paid` processing for the same Stripe customer adds row-lock contention.
- A cold Postgres connection / connection-pool checkout adds 50-200ms.

Empirically, **the email warning fires within 8-770ms after invoice.paid**, but the FULL transaction (including post-email steps + commit) can easily extend several seconds further. If the customer's onboarding form takes 5s to fill and the webhook takes 15s to commit, the 12s retry budget is exhausted.

## 13.5 Recovery for Bucket B

> **2026-04-27 update:** This query was run (§15). Outcome was **(d): all 14 rows returned `status='active'` with `property_id NOT NULL` and full onboarding data**, which §13.5 did not anticipate as an option. **No recovery action is needed.** Steps 1–2 below are kept for the historical record only.

**Step 1 — verify agreements exist in production DB.** The most important diagnostic. Run on production Postgres:

```sql
SELECT
  stripe_subscription_id,
  agreement_number,
  status,
  customer_id,
  property_id,
  created_at,
  CASE WHEN property_id IS NULL THEN 'NOT YET ONBOARDED'
       ELSE 'ONBOARDED'
  END AS onboarding_state
FROM service_agreements
WHERE stripe_subscription_id IN (
  'sub_1TOTzjG1xK8dFlafZGGFo5DP',  -- diane beddor
  'sub_1TOg3YG1xK8dFlaf8ejiSWUT',  -- Laura Collier
  'sub_1TOgC0G1xK8dFlafpN8UpefE',  -- David Schmaltz
  'sub_1TOhHCG1xK8dFlafsUHsIxEc',  -- James Cosmano
  'sub_1TOjcOG1xK8dFlafK4Pq1GLU',  -- Kristi Hendricks
  'sub_1TP11aG1xK8dFlafZciW8QiV',  -- Gail Ancier
  'sub_1TPB8eG1xK8dFlafZjjZuCHL',  -- Alex Lelchuk
  'sub_1TPrM1G1xK8dFlafX2atcFBn',  -- Sulmaan Khan
  'sub_1TPs4RG1xK8dFlaf2mFtDzjD',  -- Eric W Forsberg
  'sub_1TPtmQG1xK8dFlafQHHOGDo8',  -- Brent Ryan
  'sub_1TQB69G1xK8dFlafMTSh9YHt',  -- Daniel kahner
  'sub_1TQDeOG1xK8dFlaf35SZ079r',  -- Prasanth Prabhakaran
  'sub_1TQILUG1xK8dFlafDLMNIIt3',  -- Elizabeth Sweeney
  'sub_1TQTVLG1xK8dFlaf3fN2xE1G'   -- Madalyn Larsen
)
ORDER BY created_at;
```

**Expected outcomes and follow-up:**

- **All 14 rows return** with `status='active'` and `property_id IS NULL`: The agreements exist, were activated by the checkout webhook, but onboarding never completed. Each customer can be sent a **fresh onboarding link** (`https://grinsirrigation.com/onboarding?session_id=cs_live_<their_session_id>`) and should succeed on retry. Pull the session_id for each from Stripe via `stripe checkout sessions list --live --customer=cus_<customer_id>`. **No code change needed for these — purely a customer outreach problem.**

- **Some rows missing**: Those subs really do lack agreements. They join Bucket A's recovery path (replay `checkout.session.completed` event from Stripe Dashboard → Developers → Events). Do this only if a clear root cause is identified for the missing ones — replaying without identifying the cause risks the same crash.

- **Rows present but `status='pending'`** (no transition logs in error stream): The checkout handler created the agreement but didn't transition to ACTIVE. Possible explanation: `agreement_svc.transition_status` (`webhooks.py:367-372`) raised silently. Worth a separate investigation. Manually transition via admin API or SQL.

**Step 2 — fix the underlying race(s).** Two recommended changes (separate from the empty-`last_name` fix):

1. **Make the `invoice.paid` "No agreement" log non-error.** It is benign noise during the normal first-invoice flow. Current code at `webhooks.py:521-526` calls `log_failed`, which emits at error level. Change to `log_started` or `log_skipped` at info/warn level with reason `agreement_not_yet_created`. Stripe will not retry (the handler returns 200), so the log is the only artifact. Reducing noise will make future bug investigations easier.

2. **Extend the onboarding-submit retry budget** in `OnboardingService.complete_onboarding`. Current 4 attempts × (0,2,4,6)s = 12s. Recommend 6 attempts × (0,2,4,6,8,10)s = 30s, OR more aggressive: switch from polling to a database NOTIFY/LISTEN (Postgres async pubsub) so the onboarding endpoint blocks until the webhook commits, with a 30s total ceiling. The polling approach is simpler; the LISTEN approach is more robust under high contention.

3. **(Optional follow-up):** Address the parent webhook-ordering issue at the Stripe end. In Stripe Dashboard → Developers → Webhooks, change the subscribed events to NOT include `invoice.paid` for first invoices, OR add a delivery delay. Stripe doesn't directly support either; the clean architectural answer is just (1) above.

## 13.6 Why this hadn't been caught

- Pre-launch E2E (smoke-test-2.md, smoke-test-3.md) used CLI-driven Stripe events that fired sequentially, not in parallel, so the webhook ordering race was never observed.
- The 12-second retry in `OnboardingService.complete_onboarding` was tested against synthetic loads in March 2026 where webhook handlers completed in <1s; real production with multiple concurrent customers and Premium-tier job generation extends transaction times beyond the budget.
- The `webhook_invoice_paid_failed` error log line is alarming in retrospect, but in the developer's mental model it appears as a routine "out-of-order events recover on the next invoice" — which is true for everything except first-invoice/onboarding flows.

## 13.7 Customer impact summary

| Group | Count | Most likely state | Action |
|---|---|---|---|
| Bucket A (single-word name) | 3 | No agreement in DB. Permanent crash. | Deploy fix → replay checkout event from Stripe Dashboard → reach out to customer with onboarding link. |
| Bucket B (race condition) | 14 | **Probably has agreement in DB, status=ACTIVE, just never onboarded.** | DB query (above) to confirm → reach out to customer with fresh onboarding link → no code fix required for these specific customers, but the race deserves a separate fix to prevent future occurrences. |
| Bucket C (no checkout metadata) | 2 | Likely admin-created, never had a checkout event | Manual reconciliation with whoever created them in Stripe Dashboard. |

## 13.8 Diagnostic commands used

```bash
# Confirm Stripe live account
mcp__stripe__get_stripe_account_info
# → acct_1RDrfSG1xK8dFlaf, "Grin's Irrigation"

# Webhook endpoint configuration
curl -s "https://api.stripe.com/v1/webhook_endpoints" -u "$STRIPE_LIVE_KEY:"
# → we_1TBNmgG1xK8dFlafKXD6UaCf, api_version=2025-03-31.basil, status=enabled,
#   url=https://grinsirrigationplatform-production.up.railway.app/api/v1/webhooks/stripe

# Verify event payload format
curl -s "https://api.stripe.com/v1/events/evt_1TQTVMG1xK8dFlafkJVXDuiv" \
  -u "$STRIPE_LIVE_KEY:" -H "Stripe-Version: 2025-03-31.basil"
# → obj.subscription: 'sub_1TQTVLG1xK8dFlaf3fN2xE1G' (top-level)
# → obj.parent: None

# Pull all error-level Railway logs (where Bucket B's invoice_paid_failed entries are)
mcp__railway__get-logs
  workspacePath=/Users/kirillrakitin/Grins_irrigation_platform
  logType=deploy
  environment=production
  service=Grins_irrigation_platform
  lines=500
  filter=@level:error
  json=true

# Pull all warn-level Railway logs (where the email.send.pending entries are)
mcp__railway__get-logs
  workspacePath=/Users/kirillrakitin/Grins_irrigation_platform
  logType=deploy
  environment=production
  service=Grins_irrigation_platform
  lines=300
  filter=@level:warn
  json=true
```

---

---

# §14 — Root cause for Bucket C (added 2026-04-26 after follow-up investigation)

## 14.1 Summary

**Bucket C is not a bug. It is operator-initiated subscription creation via the Stripe Dashboard, which by design does not produce a `checkout.session.completed` webhook event.** Both subscriptions (`sub_1TQBeOG1xK8dFlafPJKDjyN3` for Shores Of Kraetz Lake, `sub_1TQBUlG1xK8dFlaf5X9O10Se` for Mitchell Bay Townhomes Association) were manually created by a human operator clicking "+ New Customer" and "+ New Subscription" in the Stripe Dashboard, with a 100% discount applied so the first invoice settles at $0 without a payment method.

The platform's webhook handler subscribes to `checkout.session.completed` for agreement creation, but it does **not** subscribe to `customer.subscription.created`. When the admin-created subscription's first `invoice.paid` event fires (synthetically, because of the discount), the handler tries to look up an agreement by `stripe_subscription_id` and naturally finds none — producing the `webhook_invoice_paid_failed: "No agreement for subscription …"` error log entry that surfaces these in the same Railway log query as Bucket A and B.

The "No agreement" error log is **expected** for Dashboard-created subscriptions, but the system has no special-case path for them — every admin who creates a subscription via Dashboard must follow up by manually creating the corresponding `service_agreements` row, generating jobs, and linking property data, **or** these customers are paying for an active subscription with no platform-side service plan.

## 14.2 Evidence

### 14.2.1 Zero `checkout.session.completed` events for either subscription

Direct query against Stripe's events API for the time window 2026-04-25 18:55:00 → 19:20:00 UTC (which fully encompasses both subscriptions' creation):

```bash
curl -s 'https://api.stripe.com/v1/events?limit=100' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'created[gte]=1777143300' \
  --data-urlencode 'created[lte]=1777144800'
```

Filtered for events referencing either Bucket C subscription or customer ID, **no `checkout.session.completed` events appear**. Same query against Stripe's checkout session search API:

```bash
curl -s 'https://api.stripe.com/v1/checkout/sessions/search' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'query=subscription:"sub_1TQBeOG1xK8dFlafPJKDjyN3"'
# → matching checkout sessions: 0

curl -s 'https://api.stripe.com/v1/checkout/sessions/search' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'query=subscription:"sub_1TQBUlG1xK8dFlaf5X9O10Se"'
# → matching checkout sessions: 0
```

No checkout session was ever created for either subscription. This is impossible if the customer paid via the website (which always uses `mode=subscription` Stripe Checkout sessions). Therefore both originated from the Stripe Dashboard or direct API.

### 14.2.2 Event timeline confirms Dashboard-style operator workflow

All Stripe events in the 25-minute window for both customers, ordered chronologically. Same-`request_id` events were produced by a single API call; same-`idempotency_key` events were produced as part of one client-side action.

**Mitchell Bay Townhomes Association timeline:**

| Time (UTC) | Event | Object | request_id | idempotency_key |
|---|---|---|---|---|
| 18:59:54 | `customer.created` | `cus_UOzPVYtbrdgI0t` | `req_Y3gqYzfbSHQy69` | `cced34ee-db67-…` |
| 19:01:49 | `customer.updated` | `cus_UOzPVYtbrdgI0t` | `req_nALxeBoXKlwCwQ` | `8efaa570-277c-…` |
| 19:02:01 | `payment_intent.created` | `pi_3TQBSnG1xK8dFlaf…` | `req_GEc8m3vhjyPubN` | `6395cc74-9547-…` |
| 19:02:02 | `payment_intent.canceled` | `pi_3TQBSnG1xK8dFlaf…` | `req_GEc8m3vhjyPubN` | `6395cc74-9547-…` |
| 19:04:04 | `setup_intent.created` | `seti_1TQBUmG1xK8dFlaf…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `customer.subscription.created` | `sub_1TQBUlG1xK8dFlaf…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `invoice.created` | `in_1TQBUlG1xK8dFlafy6…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `invoice.finalized` | `in_1TQBUlG1xK8dFlafy6…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `invoice.paid` | `in_1TQBUlG1xK8dFlafy6…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `invoice.payment_succeeded` | `in_1TQBUlG1xK8dFlafy6…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |
| 19:04:05 | `customer.discount.created` | `di_1TQBUlG1xK8dFlaf…` | `req_uimE1dEZ5Ve9gd` | `fdc10d89-8cc8-…` |

Reading the timeline: the operator created the customer (18:59), edited the customer (19:01 — likely fixing address fields), tried to add a card (`payment_intent.created` immediately followed by `payment_intent.canceled` — clicked away from the card form), then 2 minutes later created the subscription (19:04). The subscription creation produced **eight events all sharing one `request_id` and one `idempotency_key`** — the giveaway that this is a single Dashboard "Create Subscription" submission.

Note `customer.discount.created` firing in the same request as the subscription: the operator selected a coupon (likely 100% off) when creating the subscription. This explains why the first invoice is $0 paid — the coupon zeroed it out. The `setup_intent.created` event in the same request indicates the operator selected "send invoice and collect later" or similar — Stripe set up an off-session payment method placeholder.

**Shores Of Kraetz Lake timeline:**

| Time (UTC) | Event | Object | request_id | idempotency_key |
|---|---|---|---|---|
| 19:11:23 | `customer.created` | `cus_UOzbMlO04AqRLj` | `req_Xvhja2heF5CwQv` | `4c142195-1ca5-…` |
| 19:14:01 | `customer.subscription.created` | `sub_1TQBeOG1xK8dFlaf…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `invoice.created` | `in_1TQBeOG1xK8dFlafgK…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `invoice.finalized` | `in_1TQBeOG1xK8dFlafgK…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `invoice.paid` | `in_1TQBeOG1xK8dFlafgK…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `invoice.payment_succeeded` | `in_1TQBeOG1xK8dFlafgK…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `customer.discount.created` | `di_1TQBeOG1xK8dFlafcA…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |
| 19:14:01 | `setup_intent.created` | `seti_1TQBePG1xK8dFlaf…` | `req_eH541SmBhkRVIv` | `d170f96f-68d8-…` |

Same pattern: customer creation, then a single multi-event subscription request 158 seconds later. Same `customer.discount.created + setup_intent.created` co-firing — Dashboard "Create subscription with 100% off, collect payment method later."

The two subscriptions were created **10 minutes apart by the same operator session** (19:04 and 19:14 UTC, both on 2026-04-25). They share workflow signatures.

### 14.2.3 Subscription line-item structure with telltale typos

`sub_1TQBeOG1xK8dFlafPJKDjyN3` (Shores Of Kraetz Lake):

| Line item | Product ID | Price ID | Unit | Qty |
|---|---|---|---|---|
| **Commercial Essential Package** | `prod_UDzuHPjCrA2ffj` | `price_1TFXuXG1xK8dFlafE70M6fKM` | $235.00 / year | 1 |
| **RPZ Intall & Removal** ⚠ | `prod_UOzdTQdKek9IdA` | `price_1TQBe1G1xK8dFlaf0naq9MUz` | $55.00 / month | 2 |

`sub_1TQBUlG1xK8dFlaf5X9O10Se` (Mitchell Bay Townhomes Association):

| Line item | Product ID | Price ID | Unit | Qty |
|---|---|---|---|---|
| **Zone Sucharge** ⚠ | `prod_UOzQKzgXl63p72` | `price_1TQBRJG1xK8dFlafDB6jsTwR` | $8.00 / month | 3 |
| **Residential Professional Package** | `prod_UDzuA8iqVPTQUK` | `price_1TFXuUG1xK8dFlafPWS8gQKi` | $260.00 / year | 1 |

⚠ The line-item names "RPZ **Intall** & Removal" (should be "Install") and "Zone **Sucharge**" (should be "Surcharge") contain typos. The catalog product names ("Commercial Essential Package", "Residential Professional Package") are clean and match the website's seed data — these are the canonical recurring tier products used in the regular checkout flow. The typo'd line items have product IDs (`prod_UOzdTQdKek9IdA`, `prod_UOzQKzgXl63p72`) and price IDs (`price_1TQBe1G1xK8dFlaf0naq9MUz`, `price_1TQBRJG1xK8dFlafDB6jsTwR`) created on the same day as the subscriptions, which means they were created freshly by the operator in the Dashboard alongside the subscription, not pulled from the website's price seed file.

**Conclusion:** The operator created two ad-hoc Stripe Products in the Dashboard for "RPZ install + removal" and "Zone surcharge" billing add-ons, attached them to the catalog tier products, and started subscriptions. The website's checkout flow does NOT create one-off products — it only uses the pre-seeded canonical catalog. So these subs cannot have come from the website.

### 14.2.4 Customer profiles confirm partial-form Dashboard entry

```
cus_UOzPVYtbrdgI0t (Mitchell Bay Townhomes Association)
  name: Mitchell Bay Townhomes Association
  email: rogerdsims@gmail.com
  phone: +19702141137
  created: 2026-04-25 18:59:54 UTC
  description: None
  address: {city: '', country: 'US', line1: '16847 Terrey Pine Dr.',
            line2: '', postal_code: '', state: 'MN'}    ← incomplete (no city, no zip)
  default_source: None        ← no payment method
  metadata: {}
  invoice_settings.default_payment_method: None

cus_UOzbMlO04AqRLj (Shores Of Kraetz Lake)
  name: Shores Of Kraetz Lake
  email: commerce@brentjryan.us
  phone: +17634588674          ← SAME phone as Brent Ryan (Bucket B sub_1TPtmQ)
  created: 2026-04-25 19:11:23 UTC
  description: None
  address: {city: '', country: 'US', line1: '5707 Excelsior BLVD St.louis Park',
            line2: '', postal_code: '55416', 'state': 'MN'}    ← city blank, "St.louis Park" mashed into line1
  default_source: None
  metadata: {}
```

Both customer records have:
- `metadata: {}` — no `consent_token`, no website-flow markers
- `default_source: None` — no card on file
- `address.city: ''` — blank, not validated. The website checkout form's billing-address step always requires city; this is unreachable via checkout.
- For Shores Of Kraetz Lake: city ("St.louis Park") was typed into `line1` instead of `city`, alongside the actual street ("5707 Excelsior BLVD") — a classic data-entry anomaly, only possible through manual form entry where the operator concatenated fields.

Combined with the timeline above, this is a textbook signature of operator-driven Dashboard input.

### 14.2.5 First invoice is $0 because of coupon, not because no items billed

Both subscriptions show `latest_invoice.total = $0.00, amount_paid = $0.00, status = paid, billing_reason = subscription_create`. With line items totaling $235/yr + $55/mo × 2 = $1,555/yr (Shores) and $260/yr + $8/mo × 3 = $548/yr (Mitchell Bay), this is impossible without a discount.

The `customer.discount.created` event firing at the same `request_id` as the subscription creation confirms a 100% discount coupon was applied at sub-creation time. This is a Stripe Dashboard "Create subscription" feature — the operator selected "Apply coupon" when creating the subscription. The coupon is attached to the customer (not the subscription), so it persists; future invoices would also be discounted unless the coupon is removed.

This means **the customers paid $0 (despite being marked active)** and the platform should not treat these as revenue-bearing accounts until the coupon is removed or the subscriptions are reconfigured. Whatever the operator's intent, these are NOT in a normal billing state.

## 14.3 Why the platform never created agreements for these

The platform's webhook handler subscribes to (`webhooks.py:62-71`):

```python
HANDLED_EVENT_TYPES = frozenset(
    {
        "checkout.session.completed",
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.upcoming",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    },
)
```

**Notably absent:** `customer.subscription.created`, `customer.created`, `invoice.created`, `invoice.finalized`. Stripe's webhook endpoint registration (`we_1TBNmgG1xK8dFlafKXD6UaCf`) was set up in March 2026 with a deliberately narrow event set — only the events the website checkout flow generates plus the lifecycle events for active subscriptions.

For website-originated subscriptions, the canonical agreement-creation event is `checkout.session.completed`. For Dashboard-originated subscriptions, **no event fires that the platform listens for that triggers agreement creation.**

When `invoice.paid` fires for a Dashboard-created subscription (as it did at 19:04:05 and 19:14:01 for Bucket C), the handler routes to `_handle_invoice_paid` (`webhooks.py:480+`), which does:

```python
agreement = await agreement_repo.get_by_stripe_subscription_id(subscription_id)
if not agreement:
    self.log_failed(
        "webhook_invoice_paid",
        error=ValueError(f"No agreement for subscription {subscription_id}"),
    )
    return
```

The handler returns gracefully (no raise → no rollback), but emits an error-level log. This is the **same** "No agreement" error pattern surfaced by Bucket B's webhook ordering race — but the cause is different.

## 14.4 Distinguishing Bucket C from Bucket A and B in logs

Future investigators should look for these signatures to disambiguate:

| Signal | Bucket A (single-word name) | Bucket B (race condition) | Bucket C (Dashboard-created) |
|---|---|---|---|
| `webhook_checkout_session_completed_failed` log entry | **Yes**, with `ValidationError` | No | No |
| `email.send.pending` warning at the matching second | No | **Yes** | No |
| Subscription metadata in Stripe | Populated (`consent_token`, `package_tier`, `zone_count`, etc.) | Populated | **Empty** `{}` |
| `customer.discount.created` event | No | No | **Yes**, same `request_id` as `customer.subscription.created` |
| Checkout session exists in Stripe | **Yes** | **Yes** | **No** |
| First invoice amount | Standard tier price | Standard tier price | **$0** (coupon applied) |
| Customer `default_source` / payment method | Set | Set | **None** |
| Operator workflow signature in events | None | None | `customer.created` → `customer.updated` (optional) → `payment_intent` (canceled) → `subscription.created`+`discount.created` cluster |

## 14.5 Recovery for Bucket C

These are operational/data-entry questions, not code bugs. Recovery is a manual reconciliation between the operator who created the subs and the platform's data model.

### 14.5.1 Confirm operator intent

Before any data action, ask whoever has Stripe Dashboard access in the live account about:

- **Mitchell Bay Townhomes Association** (`cus_UOzPVYtbrdgI0t`, `sub_1TQBUlG1xK8dFlaf5X9O10Se`)
  - Was this a real commercial customer onboarded outside the website? If yes: needs an agreement record, property record, and jobs generated for the 2026 season.
  - Was this a manual fixup of a customer who tried to use the website but failed? If yes: pull their original failed checkout session and follow Bucket A/B recovery instead.
  - Was this a test/scratch entry that should be deleted? If yes: cancel the subscription in Stripe, delete the customer.

- **Shores Of Kraetz Lake** (`cus_UOzbMlO04AqRLj`, `sub_1TQBeOG1xK8dFlafPJKDjyN3`)
  - **High likelihood this is Brent Ryan's HOA**: same phone (`+17634588674`) and the email domain (`brentjryan.us`) suggests Brent Ryan's business. Brent Ryan also has a failed website-checkout sub in Bucket B (`sub_1TPtmQG1xK8dFlafQHHOGDo8`, professional-residential, $260/yr) — possible the operator was trying to manually fix Brent's account when the original onboarding broke. If so: Bucket C's subscription is a **duplicate billing setup** for the same person, and one of the two needs to be canceled before any agreement creation.

### 14.5.2 If the operator confirms these are real and intended

For each, manually create:
1. A `service_agreements` row with `stripe_subscription_id = sub_xxx`, `stripe_customer_id = cus_xxx`, `tier_id` matching the line items (Mitchell Bay → Residential Professional; Shores → Commercial Essential), `customer_id` linked to a `customers` row, and `status = 'ACTIVE'` (since payment effectively succeeded via discount).
2. A `customers` row if not already present (Mitchell Bay almost certainly is new; Shores Of Kraetz Lake may already exist if Brent Ryan's record was created during one of the earlier Bucket B checkouts — check by phone).
3. A `properties` row with the address from Stripe's customer record (note both addresses are incomplete — operator must collect the missing fields offline).
4. `jobs` rows for the tier's seasonal services. Since these are operator-created, the operator must collect preferred service times and week preferences offline; default to mid-season weeks.
5. The custom add-on line items (`RPZ Intall & Removal`, `Zone Sucharge`) need a decision: are they recurring monthly fees that should appear as additional jobs, or are they billing-only adjustments not corresponding to specific services? This is the operator's call.

### 14.5.3 If these are unintended or duplicates

For Shores Of Kraetz Lake, if it's a duplicate of Brent Ryan's Bucket B sub:
1. In Stripe Dashboard, cancel `sub_1TQBeOG1xK8dFlafPJKDjyN3` immediately (`Cancel at period end` or `Cancel immediately + prorate`).
2. Recover Brent Ryan's website-originated subscription via §13.5 (DB query → fresh onboarding link).

For Mitchell Bay, if it's a test entry: cancel `sub_1TQBUlG1xK8dFlaf5X9O10Se` and delete `cus_UOzPVYtbrdgI0t`.

## 14.6 Prevention — recommended platform changes

These would all reduce future Bucket C churn:

1. **Subscribe to `customer.subscription.created`** on the Stripe webhook endpoint and add a handler in `_route_event` that:
   - Detects subscriptions with empty metadata (no `package_tier`)
   - Logs an info-level `webhook_subscription_created_dashboard` event with the customer name, line items, and operator-needs-followup flag
   - Does NOT auto-create an agreement (because tier mapping is ambiguous for ad-hoc line items), but surfaces the sub on a "Pending operator reconciliation" admin dashboard view

2. **Promote the `_handle_invoice_paid` "No agreement" log from error to warn** with a reason classifier:
   - `agreement_not_yet_created` (Bucket B race) — info or warn
   - `subscription_created_outside_checkout` (Bucket C Dashboard) — warn with operator-followup flag
   - This requires checking subscription metadata to distinguish — empty metadata → Dashboard, populated metadata → race

3. **Add an admin UI** in the platform that lists "Stripe subscriptions without a matching agreement" so operators can reconcile after Dashboard activity. Queries are simple: `SELECT * FROM stripe_subscriptions LEFT JOIN service_agreements ON stripe_sub_id WHERE service_agreements.id IS NULL` (assuming we add a Stripe-sub mirror table; or query Stripe API directly).

4. **Document operational guidance**: if an operator creates a subscription in Stripe Dashboard, they MUST create the corresponding agreement via the platform admin API. Adding a "Create from Stripe sub" admin endpoint that takes a `sub_xxx` and creates the agreement + property + jobs would close this gap cleanly.

## 14.7 Customer impact summary (updated)

| Group | Count | Cause | Customer state | Action |
|---|---|---|---|---|
| **Bucket A** (single-word name) | 3 | Hard webhook crash on Pydantic `min_length=1` validation | Paid Stripe; no agreement in DB; locked out of `/onboarding` | Deploy fix → replay checkout event → reach out with onboarding link |
| **Bucket B** (log noise only — see §15) | 14 | `invoice.paid` arriving microseconds before `checkout.session.completed` produces a noisy "No agreement" error log. Customer-side flow completes normally. | Paid Stripe; **active agreement in DB with full onboarding data** (DB query confirmed §15); no customer impact | **No action.** Demote `_handle_invoice_paid` "No agreement" error log to warn/info (§14.6 item 2) to silence the noise. |
| **Bucket C** (admin-created) | 2 | Stripe Dashboard "Create subscription" with 100% coupon; no `checkout.session.completed` event ever fired | Active Stripe sub at $0 effective price (coupon applied); no agreement in DB; possibly duplicate of a Bucket B record (Shores Of Kraetz Lake = Brent Ryan?) | Confirm operator intent → manually create agreement OR cancel sub. **No automated recovery** — these need a human decision per record. |

## 14.8 Diagnostic commands used

```bash
# Confirm zero checkout sessions for either Bucket C sub
curl -s 'https://api.stripe.com/v1/checkout/sessions/search' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'query=subscription:"sub_1TQBeOG1xK8dFlafPJKDjyN3"'
# → "data": [], total_count: 0

# Pull all Stripe events in the operator-creation time window
curl -s 'https://api.stripe.com/v1/events?limit=100' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'created[gte]=1777143300' \
  --data-urlencode 'created[lte]=1777144800'

# Subscription detail with expanded items.data.price.product and latest_invoice
curl -s 'https://api.stripe.com/v1/subscriptions/sub_1TQBeOG1xK8dFlafPJKDjyN3' \
  -u "$STRIPE_LIVE_KEY:" \
  -G --data-urlencode 'expand[]=customer' \
     --data-urlencode 'expand[]=items.data.price.product' \
     --data-urlencode 'expand[]=latest_invoice'

# Customer detail
curl -s 'https://api.stripe.com/v1/customers/cus_UOzbMlO04AqRLj' \
  -u "$STRIPE_LIVE_KEY:"
```

---

# §15 — Bucket B fully resolved (added 2026-04-27 after prod DB read-only query)

## 15.1 Summary

**Bucket B is not a customer-impacting bug.** All 14 "Bucket B" customers fully completed both checkout and onboarding. Their service agreements are active in the production database with all onboarding form data persisted. The only artifact of any "failure" is the noisy `webhook_invoice_paid_failed: "No agreement for subscription …"` error log — pure diagnostic noise from the webhook ordering race described in §13.2.

This contradicts §13.3's "onboarding submit race → 404 → never persisted" hypothesis, which was based on the assumption that the original 19-customer count came from real customer-impact reports. In fact, only Bucket A's 3 customers reported the "We couldn't find your session" symptom in §1; Bucket B was inferred from log noise alone.

## 15.2 Evidence — Railway access logs

A `--filter '/onboarding/complete'` query against the production Railway service returned uvicorn access-log entries for every Bucket B customer's POST submission. Every one returned **200 OK**, not 404:

| Customer | Sub created (UTC) | POST `/onboarding/complete` (UTC) | Result |
|---|---|---|---|
| diane beddor | 2026-04-21 02:24 | 2026-04-21 02:28:08 | **200 OK** |
| Laura Collier | 2026-04-21 15:17 | 2026-04-21 15:18:41 | **200 OK** |
| David Schmaltz | 2026-04-21 15:26 | 2026-04-21 15:27:34 | **200 OK** |
| James Cosmano | 2026-04-21 16:35 | 2026-04-21 16:37:25 | **200 OK** |
| Kristi Hendricks | 2026-04-21 19:05 | 2026-04-21 19:07:01 | **200 OK** |
| Gail Ancier | 2026-04-22 13:41 | 2026-04-22 13:41:55 | **200 OK** |
| Alex Lelchuk | 2026-04-23 00:29 | 2026-04-23 00:28:24 + 00:29:54 | **200 OK** (2 submissions) |
| Sulmaan Khan | 2026-04-24 21:33 | 2026-04-24 21:34:35 | **200 OK** |
| Eric Forsberg | 2026-04-24 22:19 | 2026-04-24 22:20:42 | **200 OK** |
| Brent Ryan | 2026-04-25 00:09 | 2026-04-25 00:10:21 | **200 OK** |
| Daniel kahner | 2026-04-25 18:38 | 2026-04-25 18:39:48 | **200 OK** |
| Prasanth Prabhakaran | 2026-04-25 21:22 | 2026-04-25 21:22:47 | **200 OK** |
| Elizabeth Sweeney | 2026-04-26 02:22 | 2026-04-26 02:27:38 | **200 OK** |
| Madalyn Larsen | 2026-04-26 14:17 | 2026-04-26 14:18:26 | **200 OK** |

The 404 responses present in the same retention window (2026-04-22 19:30:36, 19:30:56, 19:31:27; 2026-04-24 19:16:40; 2026-04-25 22:07:13, 22:07:28, 22:07:54) **do not align with any Bucket B sub-creation timestamp** and are unrelated to this investigation.

The endpoint at `onboarding.py:386-472` only returns 200 by reaching the `return CompleteOnboardingResponse(...)` line, which only executes after `await db.commit()` of the property creation, agreement linkage, job updates, and customer preference write. A 200 is unambiguous evidence of full persistence.

## 15.3 Evidence — production DB read-only query

Run 2026-04-27 with `default_transaction_read_only = on` and `SET transaction_read_only = on` confirmed at session start:

```sql
SELECT
  sa.stripe_subscription_id,
  sa.agreement_number,
  sa.status::text                AS agreement_status,
  sa.property_id IS NOT NULL     AS has_property,
  sa.preferred_schedule,
  sa.preferred_schedule_details,
  sa.service_week_preferences,
  sa.created_at,
  sa.updated_at,
  p.zone_count,
  p.gate_code,
  p.has_dogs,
  p.access_instructions,
  c.preferred_service_times
FROM service_agreements sa
LEFT JOIN properties p ON p.id = sa.property_id
LEFT JOIN customers  c ON c.id = sa.customer_id
WHERE sa.stripe_subscription_id = ANY($1::text[]);
```

Result: **14 rows / 14 expected.** Every row had `agreement_status='active'` and `has_property=true`. Every row had `service_week_preferences` populated (either explicit dates or explicit `null` for "no preference"). `updated_at` matched the corresponding access-log POST timestamp ±10s.

### Per-customer onboarding form values

| Customer | Agreement | Tier | preferred_schedule | spring_startup | mid_season_inspection | fall_winterization | preferred_service_times | has_dogs | gate_code | access_instructions |
|---|---|---|---|---|---|---|---|---|---|---|
| diane beddor | AGR-2026-123 | essential-residential | ASAP | 2026-04-27 | — | 2026-10-19 | NO_PREFERENCE | false | — | — |
| Laura Collier | AGR-2026-124 | essential-residential | ASAP | 2026-04-27 | — | 2026-09-21 | NO_PREFERENCE | true | — | — |
| David Schmaltz | AGR-2026-125 | essential-residential | ASAP | *no preference* | — | *no preference* | NO_PREFERENCE | false | — | — |
| James Cosmano | AGR-2026-126 | winterization-only | ASAP | — | — | 2026-11-02 | NO_PREFERENCE | true | — | "Gate is locked with carabiner to prevent dog from getting out. Please come to front door to confirm dog is inside before starting work, and please ensure gate is locked when completing work." |
| Kristi Hendricks | AGR-2026-127 | professional-residential | ASAP | 2026-04-27 | 2026-07-20 | 2026-10-19 | NO_PREFERENCE | true | — | — |
| Gail Ancier | AGR-2026-129 | essential+RPZ | ASAP | 2026-02-23 ⚠️ | — | 2026-09-21 | NO_PREFERENCE | false | — | — |
| Alex Lelchuk | AGR-2026-132 | essential-residential | ASAP | 2026-04-27 | — | 2026-10-19 | NO_PREFERENCE | false | — | — |
| Sulmaan Khan | AGR-2026-134 | essential-residential | ASAP | *no preference* | — | *no preference* | NO_PREFERENCE | false | — | — |
| Eric Forsberg | AGR-2026-136 | essential-residential | ASAP | 2026-05-11 | — | 2026-10-19 | MORNING | false | — | "controller is in basement" |
| Brent Ryan | AGR-2026-137 | professional-residential | ASAP | *no preference* | *no preference* | *no preference* | NO_PREFERENCE | false | "121804" | "Garage code" |
| Daniel kahner | AGR-2026-138 | essential-residential | ASAP | *no preference* | — | *no preference* | NO_PREFERENCE | false | — | — |
| Prasanth Prabhakaran | AGR-2026-140 | essential-residential | ASAP | 2026-04-27 | — | 2026-10-05 | NO_PREFERENCE | false | — | — |
| Elizabeth Sweeney | AGR-2026-141 | essential-residential | ASAP | 2026-05-04 | — | 2026-10-05 | MORNING | true | — | — |
| Madalyn Larsen | AGR-2026-142 | essential-residential | ASAP | 2026-05-11 | — | 2026-10-19 | NO_PREFERENCE | true | — | — |

⚠️ Gail Ancier's `spring_startup = 2026-02-23` is a past date relative to her 2026-04-22 sub creation. Likely a stale-Monday default in the date picker or her clicking an option that was no longer relevant. Worth a one-line frontend check; not a data-loss issue.

## 15.4 Where §13.3 went wrong

§13.3 reasoned backward from a noisy log line ("No agreement for subscription") to a hypothesized customer-impact failure (404 on `/onboarding/complete`). Two errors compounded:

1. **The log line was never proven to correlate with a 404.** The §13.3 timeline was a plausible mechanism, but no Railway access-log search for `/onboarding/complete` 404s was run against the Bucket B sub-creation timestamps to confirm. Had it been run, the 14× 200 OK pattern would have been visible immediately.
2. **The 19-customer "orphaned" count conflated three distinct populations** (Bucket A: real crash; Bucket B: log noise only; Bucket C: Dashboard-created). The original anchor for "orphaned" was *"Stripe sub with no matching agreement in DB"* — but that join was never run for Bucket B specifically. Had it been, the 14 agreements would have been visible.

The right shape of investigation for an inferred-from-logs hypothesis: **always cross-check against the customer-visible HTTP response and the DB end-state before locking in a customer-impact claim.** Logs describe what the system thought happened; the response code and DB rows describe what actually happened.

## 15.5 Side observations from the DB query

- **`properties.zone_count` is NULL for all 14 Bucket B customers**, despite Stripe sub metadata having a `zone_count` value (e.g., diane=12, Madalyn=8). The onboarding form's `zone_count` field is being submitted as null, OR the frontend doesn't render that field, OR it's intentionally read from Stripe metadata at job-execution time and never written to `properties.zone_count`. **Worth a separate investigation** — not Bucket-B-specific, but surfaced by this query. Zone count is needed for accurate per-zone scheduling and surcharge logic.
- **`preferred_schedule` is "ASAP" for all 14.** Either the form defaults to ASAP and most customers don't change it, or only ASAP-pickers ended up in this Bucket B sample. Probably the former.
- **`preferred_service_times` is "NO_PREFERENCE" for 12 of 14**, with Eric Forsberg and Elizabeth Sweeney choosing "MORNING". Form default is `NO_PREFERENCE`; this is a low-engagement field.
- **3 customers have `has_dogs=true` with no access_instructions** (Laura Collier, Kristi Hendricks, Madalyn Larsen). Worth confirming with them in case the access detail was meant to be filled.

## 15.6 Action items invalidated by §15

- ❌ ~~Reach out to Bucket B customers with fresh onboarding links~~ — they are fully onboarded.
- ❌ ~~Extend the 12-second retry budget in `OnboardingService.complete_onboarding`~~ — current budget worked for all 14 production cases.
- ❌ ~~Add Bucket B to the empty-`last_name` fix replay scope~~ — Bucket B has no missing data to recover.

## 15.7 Action items still valid (and now higher priority)

- ✅ **Demote `_handle_invoice_paid` "No agreement" error log to warn/info** with reason `agreement_not_yet_created` (already in §14.6 item 2). This is now the *only* code change Bucket B motivates — it removes the diagnostic noise that misled this entire investigation.
- ✅ **Investigate `properties.zone_count` always being NULL** (new — see §15.5).
- ✅ **Investigate Gail Ancier's past-date `spring_startup`** to determine if the date picker has a stale-default bug.

## 15.8 Methodology — the read-only DB session

For audit traceability, the query was executed as follows:

```python
import asyncpg
conn = await asyncpg.connect(
    DATABASE_URL,  # Railway production Postgres TCP proxy
    server_settings={'default_transaction_read_only': 'on'},
)
# SHOW transaction_read_only → 'on' (verified before any SELECT)
rows = await conn.fetch(SELECT_SQL, [...sub_ids...])
```

Only SELECT statements were executed. No mutation tools (no `psql -c "UPDATE..."`, no migrations, no admin API calls).

---

# §16 — Bucket A + C orphan validation (added 2026-04-27 after read-only DB sweep)

## 16.1 Summary

A read-only sweep of the production DB and `stripe_webhook_events` table confirmed that **Bucket A (3) and Bucket C (2) are the only true orphans — total 5**. Each bucket's hypothesized root cause is now confirmed by direct evidence:

- **Bucket A** — the actual stored Pydantic `ValidationError` on `CustomerCreate.last_name` `min_length=1` is recorded in `stripe_webhook_events.error_message` for all 3 failed `checkout.session.completed` events. Identical error string for all three.
- **Bucket C** — neither subscription has any `checkout.session.completed` event in `stripe_webhook_events`, only `invoice.paid`. This is the definitive signature of Stripe-Dashboard-created subs that bypass the website checkout flow.

The phone-collision cascade hypothesis (§6.2 ⚠️ note about Brent Ryan / Shores Of Kraetz Lake) is **ruled out** — Brent Ryan exists cleanly in `customers` and `service_agreements`; Shores has no webhook trail beyond a single `invoice.paid` no-op.

## 16.2 DB-state validation — both buckets fully orphan

Read-only query (`default_transaction_read_only = on`) against all relevant tables for the 5 candidate cus_ids and sub_ids:

| Table | Bucket A rows | Bucket C rows |
|---|---|---|
| `customers` (by `stripe_customer_id`) | 0 / 3 | 0 / 2 |
| `service_agreements` (by `stripe_subscription_id`) | 0 / 3 | 0 / 2 |
| `service_agreements` (by `stripe_customer_id`) | 0 | 0 |
| `customers` (by email) | 0 | 1 (Brent Ryan match — see §16.5) |
| `customers` (by phone) | 0 | 1 (Brent Ryan match — see §16.5) |
| All other `customer_id`/`agreement_id`-referencing tables (`properties`, `jobs`, `disclosure_records`, `sms_consent_records`, `invoices`, `estimates`, `leads`, `communications`, etc.) | 0 | 0 |

**Conclusion:** every `_handle_checkout_completed` rollback was clean — no partial-write residue anywhere in the schema. The `stripe_webhook_events` row is the only persisted artifact (it's written outside the rolled-back transaction by design).

## 16.3 Bucket A — root cause confirmed end-to-end

### The actual stored error message

All 3 events recorded as `processing_status='failed'` in `stripe_webhook_events`, with **byte-identical** error messages:

```
1 validation error for CustomerCreate
last_name
  String should have at least 1 character [type=string_too_short, input_value='', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/string_too_short
```

| Customer | `stripe_event_id` | Failed at (UTC) |
|---|---|---|
| Jerry | `evt_1TP6SsG1xK8dFlafLXj9Pcl4` | 2026-04-22 19:29:38 |
| Andres | `evt_1TPpCnG1xK8dFlafmfSObbxa` | 2026-04-24 19:16:02 |
| Chetan | `evt_1TQELXG1xK8dFlafoofKg46o` | 2026-04-25 22:06:44 |

### Confirmed via stored event_data

The `event_data` column for `evt_1TP6SsG1xK8dFlafLXj9Pcl4` (Jerry) contains the original Stripe payload as delivered. Relevant slice:

```json
"customer_details": {
  "name": "Jerry",
  "email": "jerrymitchell3@gmail.com",
  "phone": "+16126181487",
  ...
}
```

Single-word `name="Jerry"` confirmed at the source of truth (Stripe's signed payload, persisted by us before the handler ran). This rules out any "stripped during transit" or "frontend trimmed it wrong" hypothesis — Stripe sent the single word, and the handler crashed on it.

### The full code path

1. **`webhooks.py:281`** — `parts = full_name.strip().split(maxsplit=1)` with `full_name="Jerry"` → `parts = ["Jerry"]`
2. **`webhooks.py:283`** — `last_name = parts[1] if len(parts) > 1 else ""` → assigns empty string
3. **`webhooks.py:310-315`** — `CustomerCreate(first_name="Jerry", last_name="", phone="...", email="...")`
4. **`schemas/customer.py:81-86`** — `last_name: str = Field(..., min_length=1, max_length=100)` → Pydantic raises `ValidationError(string_too_short)`
5. **Exception propagates** out of `_handle_checkout_completed`; outer `handle_event` catches it, rolls back the SQL transaction, persists a row in `stripe_webhook_events` with `processing_status='failed'` and the rendered `ValidationError` text in `error_message`, then logs `webhook_checkout_session_completed_failed` at `error` level.
6. Stripe retries the same event; the same code path fails the same way. **Permanent crash for these customers.**

### Companion `invoice.paid` events also recorded

Each Bucket A sub also has a corresponding `invoice.paid` event with `processing_status='processed'` (no-op'd because no agreement exists in DB):

| Sub | `checkout.session.completed` | `invoice.paid` |
|---|---|---|
| `sub_1TP6SqG1xK8dFlafOGEwjNu9` (Jerry) | `evt_1TP6SsG1xK8dFlafLXj9Pcl4` (failed) | `evt_1TP6SsG1xK8dFlafSqEuafOs` (processed) |
| `sub_1TPpCmG1xK8dFlafzNPCfJWB` (Andres) | `evt_1TPpCnG1xK8dFlafmfSObbxa` (failed) | `evt_1TPpCoG1xK8dFlafHFHKZNRJ` (processed) |
| `sub_1TQELWG1xK8dFlafeg0JTAGI` (Chetan) | `evt_1TQELXG1xK8dFlafoofKg46o` (failed) | `evt_1TQELYG1xK8dFlaf93QI9Ba4` (processed) |

This confirms that the `_handle_invoice_paid` "No agreement" no-op path (`webhooks.py:521-526`) ran for each Bucket A sub — same diagnostic-noise pattern as Bucket B, but here the noise is real signal that nothing else committed.

## 16.4 Bucket C — root cause confirmed end-to-end

### Webhook event signature

Both subs in `stripe_webhook_events`:

| Sub | Customer | `checkout.session.completed`? | `invoice.paid`? |
|---|---|---|---|
| `sub_1TQBUlG1xK8dFlaf5X9O10Se` | Mitchell Bay Townhomes | **None** | `evt_1TQBUnG1xK8dFlafAbEV38ez` (processed) |
| `sub_1TQBeOG1xK8dFlafPJKDjyN3` | Shores Of Kraetz Lake | **None** | `evt_1TQBeQG1xK8dFlafSNKYvVOs` (processed) |

**Zero `checkout.session.completed` events for either Bucket C sub.** This is the diagnostic signature of subs created via the Stripe Dashboard "Create subscription" UI: there is no checkout flow, no consent token, no metadata, no checkout session — only the recurring `invoice.paid` events that Stripe fires on every billing cycle.

### Why no agreement exists

The webhook handler is subscribed to `checkout.session.completed` and `invoice.paid` (and a few subscription-lifecycle events), but **agreement creation is gated entirely on `_handle_checkout_completed`**. There is no fallback path that creates an agreement from `invoice.paid`. So when a Dashboard-created sub fires its first `invoice.paid`:

- `_handle_invoice_paid` looks up the sub → no agreement found
- Logs `webhook_invoice_paid_failed: "No agreement for subscription sub_xxx"`
- Returns gracefully (does not raise)
- Event recorded as `processed`
- Stripe doesn't retry

The customer pays Stripe on a recurring basis; the platform has no record of them.

### Cross-validated against Stripe dashboard query (§14.2)

§14.2 already showed `customer.subscription.created` events for both Bucket C subs but no `checkout.session.completed`. §16 adds the platform-side confirmation: our `stripe_webhook_events` table is consistent with that — we received `invoice.paid` only.

## 16.5 Phone-collision hypothesis ruled out

The §6.2 ⚠️ marker raised a hypothesis that Brent Ryan + Shores Of Kraetz Lake's shared phone (`+17634588674`) might have caused a "duplicate-phone cascade" rolling back Brent's record. The DB shows otherwise:

| Record | Customer ID | Phone | Status |
|---|---|---|---|
| Brent Ryan (Bucket B) | `cus_UOhASJmmnEtzF6` | `7634588674` | **Exists** in `customers` (id `5449f346-…`); active agreement `AGR-2026-137` / `sub_1TPtmQ`; fully onboarded (per §15) |
| Shores Of Kraetz Lake (Bucket C) | `cus_UOzbMlO04AqRLj` | `+17634588674` | **Not in DB**; only `invoice.paid` event received; no `customer.created` / `checkout.session.completed` ever fired for this Stripe customer |

Brent's record was created cleanly via the standard webhook flow on 2026-04-25 00:09:08, the same second Stripe sent his `checkout.session.completed`. Shores never went through any webhook flow that would have triggered customer creation; no cascade was possible.

The shared phone is coincidence (Brent presumably owns/manages the Shores property and used the same business phone when the operator created Shores in the Stripe Dashboard). Important consequence: **when the operator decides what to do with `sub_1TQBeOG1xK8dFlafPJKDjyN3` per §14.5, they must distinguish Shores from Brent's existing customer** — they have different Stripe `cus_id`s and Brent's is the only one with platform state.

## 16.6 Recovery scope — confirmed

The recovery plan in §9 + §14.5 matches the validation:

| Bucket | Count | Recovery action | Stripe event retention deadline |
|---|---|---|---|
| **A** | 3 | Deploy empty-`last_name` fix → replay each `checkout.session.completed` event from Stripe Dashboard → reach out to customer with onboarding link to fill in property details | Earliest event 2026-04-22 → must replay before ~2026-05-22 (30-day Stripe retention) |
| **C** | 2 | No replay possible (no checkout event exists). Operator decides per §14.5: confirm intent → create agreement manually OR cancel sub | n/a — no event to replay |

Replay is safe for Bucket A because the fix removes the only failure point on the path, and the rest of `_handle_checkout_completed` (1-12 + 13-14) is deterministic and idempotent for a sub that has no existing agreement. The DB state confirms idempotency: there is no partial customer/agreement/property to clash with.

## 16.7 What this validation rules out

- ❌ **Hidden orphan cohort.** Beyond the 5 confirmed, the schema sweep across 22 customer-referencing tables surfaced no other rows tied to these 5 cus_ids/sub_ids. No partial-write residue.
- ❌ **Different crash classes within Bucket A.** All 3 errors are byte-identical — same Pydantic field, same constraint, same input value (empty string). One root cause, three instances.
- ❌ **A "Bucket A or B" boundary case.** None of the 5 has both a failed checkout event AND a successful `/onboarding/complete` 200 (which would suggest a partial recovery). Bucket A = clean rollback; Bucket B = full success; no in-between.
- ❌ **Phone-cascade between Brent Ryan and Shores.** Confirmed independently — Brent's record exists in DB, Shores has no webhook-driven persistence path.

## 16.8 Methodology — DB queries used

All queries executed via asyncpg with `default_transaction_read_only='on'` and verified by `SHOW transaction_read_only` returning `'on'` before any SELECT. No mutation paths invoked. Queries:

```sql
-- 1) service_agreements presence by sub_id
SELECT * FROM service_agreements WHERE stripe_subscription_id = ANY($1::text[]);

-- 2) customers presence by stripe_customer_id, email, phone
SELECT * FROM customers WHERE stripe_customer_id = ANY(...);
SELECT * FROM customers WHERE LOWER(email) = ANY(...);
SELECT * FROM customers WHERE phone = ANY(...);

-- 3) Failed-event evidence
SELECT stripe_event_id, event_type, processing_status, error_message, processed_at
FROM stripe_webhook_events
WHERE stripe_event_id = ANY($1::text[]);

-- 4) Per-sub event trail (LIKE search of event_data jsonb cast to text)
SELECT stripe_event_id, event_type, processing_status, error_message, processed_at
FROM stripe_webhook_events
WHERE event_data::text LIKE '%sub_xxx%';

-- 5) Per-cus event trail
SELECT stripe_event_id, event_type, processing_status, error_message, processed_at
FROM stripe_webhook_events
WHERE event_data::text LIKE '%cus_xxx%';

-- 6) Schema-wide partial-write sweep (information_schema-driven)
SELECT table_name FROM information_schema.columns
 WHERE column_name IN ('customer_id','agreement_id','stripe_customer_id','stripe_subscription_id','consent_token');
-- then for each: SELECT COUNT(*) FROM <table> WHERE stripe_customer_id = ANY(...);
```

Same connection mode as §15.8: read-only Railway TCP proxy, `default_transaction_read_only='on'`, only `SELECT` statements.

---

---

# §17 — Recovery plan and customer journey (added 2026-04-27 — brainstorm; not yet executed)

## 17.1 Recommendation summary

| Bucket | Recovery path | Customer effort | Operator effort |
|---|---|---|---|
| **A** (3) — Jerry, Andres, Chetan | Deploy empty-`last_name` fix → **replay each `checkout.session.completed` event from Stripe Dashboard** → email each customer a fresh onboarding link | 1 click on email link + ~3-5 min on the onboarding form they originally got 404'd on | Deploy + 3× "Resend" clicks in Stripe Dashboard + send 3 personal emails |
| **C** (2) — Mitchell Bay Townhomes, Shores Of Kraetz Lake | **Pause here.** Don't touch either record until the operator who created them confirms intent. Then either manually backfill (if real) or cancel the Stripe sub (if test/duplicate). | TBD — depends on operator decision | Conversation with operator first; per-record handling after |

**Do not manual-SQL-backfill Bucket A.** `_handle_checkout_completed` does ~14 sequential operations across 6+ tables (customers, service_agreements, jobs, disclosure_records, sms_consent_records, properties via a different code path, plus side effects like `email_opt_in_at`, `stripe_customer_id` updates, orphaned-consent linking, surcharge calc, per-tier job count). Manually replicating it is high-risk; replay uses the actual production code path.

## 17.2 Bucket A recovery flow — what replay does and doesn't do

### What "replay" means

Stripe retains every event payload it sent us for 30 days. In the Stripe Dashboard under **Developers → Events**, each event has a **"Resend"** button. Clicking it makes Stripe POST the same event payload to our webhook endpoint with a fresh signature. From our app's perspective it's identical to the original delivery — same JSON body, same `event.id`. The Stripe CLI equivalent is `stripe events resend evt_xxx --live`; the API equivalent is `POST /v1/events/{id}/retry`.

### Original attempt vs. replay flow (using Jerry as example)

| Step | Original (2026-04-22 19:29) | After empty-`last_name` fix is deployed |
|---|---|---|
| Stripe POST → webhook | ✓ | ✓ (identical payload) |
| Signature verification | ✓ | ✓ |
| `_handle_checkout_completed` runs | ✓ | ✓ |
| `parts = ["Jerry"]` → `last_name=""` | ✓ | ✓ (still single-word) |
| `CustomerCreate(...)` validation | ❌ Raises `ValidationError(string_too_short)` | ✓ Fix maps `last_name=""` to placeholder (per webhook-empty-last-name-fix plan) |
| Customer created | (rolled back) | ✓ |
| Agreement created | (rolled back) | ✓ |
| Jobs generated (default month-range targets) | (rolled back) | ✓ |
| Consent records linked, disclosure created | (rolled back) | ✓ |
| Welcome + confirmation emails | (rolled back) | ✓ (sent via Resend per `project_estimate_email_portal_wired` memory) |
| `stripe_webhook_events.processing_status` | `failed` | `processed` (overwritten) |
| Stripe response | 500 | 200 |

After replay: Jerry now has a row in `customers`, `service_agreements`, `jobs`, etc. — exactly as if the original event had succeeded.

### What replay does NOT do

- It does **not** create a `properties` row. Property creation only happens when the customer submits the onboarding form (`POST /onboarding/complete` → `OnboardingService.complete_onboarding` → `property_repo.create`).
- It does **not** capture preferences (zone count, gate code, has_dogs, access_instructions, preferred_times, preferred_schedule, service_week_preferences). Those only enter via the onboarding form.
- It does **not** update job target dates from default month-ranges to the customer's chosen weeks. That happens in `complete_onboarding` (`onboarding_service.py:421-438`).

So after replay, the customer's state is `agreement.status='active'`, `agreement.property_id IS NULL` — exactly the same state as a Bucket B customer who hasn't yet onboarded. They still have to submit the form.

### Idempotency note

`handle_event` (`webhooks.py:117-145`) checks `stripe_webhook_events` to short-circuit already-processed events. For the 3 Bucket A events, the existing row has `processing_status='failed'`, which the handler treats as "retry allowed" — so replay re-runs the handler instead of short-circuiting. **Verify this assumption in `webhooks.py:117-145` before pulling the trigger.** If the check is by-event-id-with-any-status, replay won't actually re-run, and we'd need to delete the failed-event rows or use a different trigger.

## 17.3 Customer effort split

| Step | Who | How |
|---|---|---|
| Deploy empty-`last_name` fix | Us | Standard deploy of `.agents/plans/webhook-empty-last-name-fix.md` |
| Re-create customer + agreement + jobs | Us | Click "Resend" on each event in Stripe Dashboard |
| Construct recovery URL | Us | `https://grinsirrigation.com/onboarding?session_id=<cs_live_id>`. The `cs_live_id` is in `event_data->'data'->'object'->>'id'` for each Bucket A row in `stripe_webhook_events` (see §16.3 — Jerry's stored payload already has it). Or pull from Stripe via `stripe checkout sessions list --customer=cus_xxx --live`. |
| Email the customer | Us | Personal apology + link. Tone: own the glitch, don't over-explain, make the link prominent. |
| Click link | Customer | One click |
| Fill out form | Customer | ~3-5 min — service address (or "same as billing"), zone count, gate code, dogs, access instructions, preferred times, preferred schedule, per-service week selections |
| Click Complete Onboarding | Customer | One click — succeeds because the agreement now exists |
| Welcome + confirmation emails | Auto | Already wired (Resend per memory `project_estimate_email_portal_wired`) |

### What the customer is NOT asked to do

- Re-pay (Stripe already charged them; nothing changes there)
- Re-consent to SMS or terms of service (already captured via the `consent_token` in checkout metadata; replay re-applies via `compliance_svc`)
- Re-enter name, email, phone (Stripe has these; the form prefills via `verify-session`)
- Create an account or remember a password (no auth on the onboarding flow — knowledge of the `cs_live_…` session ID is the credential)

## 17.4 Onboarding link lifetime

**Effectively no expiration.** The link works as long as (a) the Stripe subscription stays active and (b) the agreement exists in our DB.

### Mechanism

The URL contains the `cs_live_…` Stripe Checkout Session ID. Both `/verify-session` (`onboarding_service.py:179-266`) and `/complete` (`onboarding_service.py:268-455`) re-retrieve the session from Stripe by that ID at request time.

### What can invalidate the link

| Failure mode | When this happens |
|---|---|
| `stripe.InvalidRequestError` on `Session.retrieve` | If Stripe deleted the session — never happens for `complete` (paid) sessions. Stripe retains them indefinitely as transaction records. The 30-day window is for *events*, not sessions. |
| `AgreementNotFoundForSessionError` | If the underlying subscription is canceled/deleted, or our agreement row is removed. |
| `verify_session` returns `already_completed=true` | After successful submission, `agreement.property_id IS NOT NULL` triggers the success-state UI (`onboarding_service.py:217-224`). The link still loads but the form is replaced with a success message — the customer can't accidentally re-submit. |

### What's NOT in the code

- No time-based expiration check on session age
- No `expires_at` field comparison (it exists on Checkout Sessions but only matters for unpaid sessions; once `status='complete'`, it's informational)
- No "link valid for N days" token
- No single-use enforcement
- No rate limit specifically tied to the link (the `5 req/IP/min` limiter on the endpoint is incidental — it'd take 5 form submits in a minute from one IP to trip)

### Practical implications for Jerry/Andres/Chetan

After replay:

- They can click the link today, next week, or 3 months from now — it still works
- They can open it on their phone, lose the email, find it later — still works
- They can't accidentally double-submit — `already_completed=true` blocks that path

For outreach copy, treat the link as **effectively permanent**. No urgency-based language needed; "whenever you're ready" is accurate. The Stripe retention deadline (~2026-05-22) applies to *replaying the event*, not to the customer using the link after we've replayed it.

## 17.5 Abandon-and-return behavior

**The link works on return, but anything they typed is gone.** The form has no draft persistence.

### What happens on a second visit

1. Browser opens the URL → frontend boots → `useEffect` calls `verifySession(sessionId)` again
2. `verify_session` returns customer name, billing address, package info — these re-prefill correctly
3. The form fields re-initialize to defaults (`OnboardingPage.tsx:27-36`):
   - `gate_code: ''`
   - `has_dogs: false`
   - `access_instructions: ''`
   - `preferred_times: 'NO_PREFERENCE'`
   - `preferred_schedule: 'ASAP'`
   - `service_week_preferences: {}`
4. The customer starts over from scratch

### Two scenarios

| State before they returned | What they see now |
|---|---|
| Typed half the form, closed tab without submitting | Empty form, has to retype everything. Header/package info still rendered correctly from `verify-session`. |
| Successfully submitted (200 OK) | "Already completed" success page (`already_completed=true` gated on `agreement.property_id IS NOT NULL`). They can't accidentally re-submit and overwrite. |

### Why no draft persistence

The frontend uses pure React `useState` (`OnboardingPage.tsx:27`). Confirmed via grep: no `localStorage`, no `sessionStorage`, no API endpoint for partial saves. Whatever they type lives in tab memory only. Tab close = data loss.

### UX implications for the apology email

- The form is short enough (~3-5 min) that re-entering is mildly annoying, not a blocker. Acceptable for one-shot recovery.
- **One real edge case to mention in the email:** if they accidentally type the wrong gate code or pick the wrong week and submit, the "already completed" guard blocks them from fixing it via the same link. Recommend the email include: *"If you need to make corrections after submitting, just reply to this email and we'll fix it."*

### Optional hardening (out of scope for Bucket A recovery)

`localStorage`-backed form persistence is ~15 lines: save `formData` to `localStorage` on every change (`useEffect([formData])`), restore from `localStorage` on mount if `already_completed=false`. Worth doing if onboarding completion rate is low generally, not worth blocking the 3-customer recovery on.

## 17.6 Bucket C recovery — operator decision required

**Don't touch either record until you talk to whoever created them in the Stripe Dashboard.** Three possible operator answers:

| Operator says | Action |
|---|---|
| "These are real customers I onboarded manually" | Manually backfill `customers`, `service_agreements`, `properties`, `jobs`, etc. via admin API or SQL. **Address details from Stripe are incomplete** (per §14.4: `address.city: ''`) — operator must collect missing fields offline. **Pricing must match what the operator agreed to with the customer** — confirm with operator before creating tier-linked agreement. |
| "These were tests / mistakes" | Cancel the Stripe sub (`Cancel immediately + prorate` if any payment was processed). Delete from Stripe Customer list if appropriate. |
| "Shores Of Kraetz Lake was meant to be Brent Ryan's second property" (phone collision per §16.5) | Cancel `sub_1TQBeOG1xK8dFlafPJKDjyN3`. Brent already has an active platform agreement (`AGR-2026-137`); add Shores as a second `properties` row under his existing customer record via admin API. |

**Operational risk if the operator is slow to respond:** the Stripe subs continue to bill on their cycle. To avoid charging customers without delivering service, consider pausing the subs (`update_subscription` with `pause_collection.behavior='void'`) until the operator decides.

## 17.7 Sequence and timeline

| Day | Action | Blocking? |
|---|---|---|
| **Day 0 (today, 2026-04-27)** | Talk to operator about Mitchell Bay + Shores intent | No — parallelizable with Bucket A work |
| **Day 0** | Verify `webhooks.py:117-145` idempotency check treats `processing_status='failed'` as retry-allowed | Yes — blocks replay |
| **Day 0-1** | Review and merge empty-`last_name` fix (plan in `.agents/plans/webhook-empty-last-name-fix.md`) | Yes — blocks replay |
| **Day 1-2** | Deploy fix to prod → smoke test by triggering a single-word-name checkout in dev or with a test sub | Yes |
| **Day 1-2** | Replay the 3 Bucket A events from Stripe Dashboard, in oldest-first order: Jerry → Andres → Chetan | — |
| **Day 1-2** | Read-only DB check that all 3 appear in `service_agreements` with `status=active`, `property_id IS NULL` | — |
| **Day 1-2** | Pull each `cs_live_…` from `stripe_webhook_events.event_data` (already in our DB per §16.3) and construct onboarding URLs | — |
| **Day 1-2** | Send personal apology emails to Jerry, Andres, Chetan with the recovery link | — |
| **Day N (whenever operator responds)** | Handle Bucket C per their answer | Independent of Bucket A timeline |

Earliest event is 2026-04-22 → Stripe retention deadline ~2026-05-22 → ~25 days of buffer, but no reason to delay. Jerry has been silent-failing for 5 days as of today.

## 17.8 Apology email — draft

> Subject: A quick fix needed to start your service with Grin's Irrigation
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

Tone notes: lead with what's wrong, then the fix, then the small ask. Don't over-apologize. Make the link impossible to miss. End with reassurance about corrections.

## 17.9 What this plan does NOT cover

- **Long-tail follow-ups** — what if a Bucket A customer doesn't respond to the email? Recommend a 5-day retry, then a final reminder, then offer a phone call. Not in this plan.
- **The `properties.zone_count` always-NULL bug** (§15.5) — these recoveries will hit the same path; the bug doesn't break recovery, just continues a known data-quality gap. Track separately.
- **Adding admin endpoint for "create agreement from sub_id"** — discussed and ruled out for this recovery (overkill for 3 customers). May still be worth building for future Bucket-C-style cases; track separately.
- **Onboarding draft persistence** — UX improvement noted in §17.5 but not blocking.

---

**Document version:** 1.5
**Last updated:** 2026-04-27 (added §17 — recovery plan and customer journey)
**Next review trigger:** After empty-`last_name` fix deploys and Bucket A events are replayed (must complete before ~2026-05-22 Stripe retention deadline); after operator confirms intent for Bucket C subs (§14.5.1); after Bucket A customers complete onboarding via the recovery link
