# 10 — Customer Landing: Service Packages + Free Quote Lead Intake

Replayable runbook for the **dev customer landing page** flow. Covers the two independent customer journeys and verifies both round-trip into the dev admin dashboard:

- **Path L — Service Packages purchase** (8 tier combinations through Subscribe modal → Stripe → onboarding → admin agreement + jobs)
- **Path Q — "Get Your Free Quote" lead intake** (5 scenarios across consent combinations, dedupe, validation)

Last verified: 2026-04-14. Run `00-preflight.md` first.

---

## Environment

| Thing | Value |
|---|---|
| Marketing frontend (dev) | `https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app` |
| Marketing — packages page | `…/service-packages` |
| Marketing — onboarding (post-Stripe) | `…/onboarding?session_id=cs_test_…` |
| CRM frontend (dev) | `https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app` |
| Backend API (dev) | `https://grins-dev-dev.up.railway.app` |
| Stripe test card | `4242 4242 4242 4242`, `12/30`, CVC `123` |
| Customer source repo | `/Users/kirillrakitin/Grins_irrigation` (sibling repo, READ ONLY here) |
| Platform/admin source repo | `/Users/kirillrakitin/Grins_irrigation_platform` (this repo) |
| Test allowlisted phone | `+19527373312` (only number that gets real SMS — see `00-preflight.md`) |

---

## Known issues to remember

Before you run anything, know these — they will bite you:

1. **BUG-001 (P0 — ACTIVE as of 2026-04-14)** — Lead form submissions with `sms_consent=true` return HTTP 201 + lead_id but the DB row is rolled back. Customer sees the green "We'll reach out" banner, admin never sees the row. Documented in `bughunt/2026-04-14-lead-form-sms-consent-rollback.md`. Until fixed, expect **scenarios Q1 + Q2 to NOT land in admin** (this is now the regression-detection signal). Scenario Q3 (sms_consent=false) is the control case that should still persist.
2. **24-hour duplicate window** — `services/lead_service.py:285-446` rejects any POST whose phone OR email matches a lead from the last 24h. Use **distinct phones per scenario** (e.g. `9527370310`, `9527370311`, …) and `*@grinstest.example` emails. Scenario Q4 deliberately reuses Q3's phone to trigger the dup banner.
3. **Admin list response is CDN-cached** (BUG-003). Add `?_t=$(date +%s)` to admin GETs against the API, and hard-refresh the admin UI between checks. Otherwise newly-created leads appear "missing."
4. **Phone allowlist (`SMS_TEST_PHONE_ALLOWLIST`)** at `services/sms/base.py:65` blocks SMS to anything other than `+19527373312`. So you can safely use varied test phones for the lead form — non-allowlisted numbers just won't receive the confirmation SMS, but the lead row still attempts to persist.
5. **`VITE_API_URL` has a trailing newline** on Vercel dev (BUG-002). Cosmetic — fetch URLs end up with `\n` between origin and path. Doesn't break anything but shows up if you intercept fetches.

---

## Path L — Service Packages Purchase

### Setup

```bash
agent-browser --version                       # expect 0.7.x
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/service-packages"
agent-browser wait --load networkidle
mkdir -p e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/{00-preflight,01-res-essential,02-res-professional,03-res-premium,04-res-winterization,05-com-essential,06-com-professional,07-com-premium,08-com-winterization}
```

### L1 — Modal field check for all 8 tiers

`agent-browser snapshot -i` and grep for Subscribe button refs. As of 2026-04-14 the page renders all 8 tiers simultaneously (no Residential/Commercial toggle); refs are stable e13–e27 (odd numbers):

| Tier | Subscribe ref | Expected base | RPZ surcharge label | Fields in modal |
|---|---|---|---|---|
| Residential Essential | `e13` | $175/yr | `$110` | phone, zones (default 1), lake pump, RPZ, SMS, email-mktg, auto-renew disclosures |
| Residential Professional | `e15` | $260/yr | `$110` | same |
| Residential **Premium** | `e17` | $725/yr | `$110` | same |
| Residential Winterization Only | `e19` | $85/yr | **`$55`** | same |
| Commercial Essential | `e21` | $235/yr | `$110` | same |
| Commercial Professional | `e23` | $390/yr | `$110` | same |
| Commercial **Premium** | `e25` | $880/yr | `$110` | same |
| Commercial Winterization Only | `e27` | $105/yr | **`$55`** | same |

Smoke-check each tier's modal — open, screenshot, cancel:

```bash
# Repeat for each REF/DIR pair
REF=e13 DIR=01-res-essential
agent-browser click @$REF
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/$DIR/02-modal-open.png
# verify the screenshot shows the expected base price + correct RPZ label
CANCEL=$(agent-browser snapshot -i | grep 'button "Cancel"' | grep -oE 'ref=e[0-9]+' | head -1 | cut -d= -f2)
agent-browser click "@$CANCEL"
```

**If any tier's modal doesn't open, OR shows wrong base price, OR shows wrong RPZ surcharge** — log it and stop; the pricing data in `pricing.ts` (sibling repo `frontend/src/shared/data/pricing.ts:86-205`) doesn't match what's deployed.

### L2 — Full E2E for one Premium tier

This is the load-bearing scenario. It proves the conditional 7-week-picker logic works (the rest of the tiers are structural copies). Run for **Residential Premium** (or Commercial Premium — pick one per session, alternating across sessions builds coverage over time).

```bash
# Open Subscribe modal for the Premium tier
agent-browser click @e17    # Premium Residential
sleep 2

# Snapshot to find form refs (they reset each modal open)
agent-browser snapshot -i | grep -E '\[ref=' | grep -E 'Phone|zone|Lake|Backflow|SMS|promotional|Subscription|Cancel'
```

Fill the modal — phone `9527373312`, 10 zones, RPZ checked, SMS+email-marketing checked, then click Confirm Subscription. Wait ~12s for the Stripe redirect.

```bash
agent-browser fill @e28 "9527373312"       # Phone
agent-browser fill @e29 "10"                # Zones
agent-browser click @e31                     # RPZ/Backflow
agent-browser click @e32                     # SMS consent
agent-browser click @e35                     # Email marketing consent
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/03-res-premium/03-modal-filled.png
agent-browser click @e36                     # Confirm Subscription
```

After ~12s, `agent-browser get url` should show `checkout.stripe.com/c/pay/cs_test_…`. Stripe checkout fields (after `agent-browser snapshot -i`):

```bash
# Card number is direct-input (no accordion required as of 2026-04-14, contrary to STRIPE-CHECKOUT-AUTOMATION-GUIDE.md)
agent-browser fill @e2  "e2e-premiumres-$(date +%s)@grinstest.example"   # Email
agent-browser fill @e4  "9527373312"                                       # Phone
agent-browser fill @e6  "4242424242424242"                                 # Card
agent-browser fill @e7  "1230"                                             # Exp 12/30
agent-browser fill @e8  "123"                                              # CVC
agent-browser fill @e9  "E2E Premium Res"                                  # Cardholder
agent-browser click @e249                                                  # "Enter address manually"
sleep 2
# Re-snapshot — manual address opens new fields
agent-browser fill @e248 "303 E2E Premium Res St"
agent-browser fill @e250 "Plymouth"
agent-browser fill @e251 "55441"
agent-browser select @e252 "Minnesota"
# Re-snapshot for Subscribe + ToS refs (they shift after manual address opens)
agent-browser click @e318    # ToS checkbox
agent-browser click @e321    # Subscribe button
sleep 18                       # webhook + redirect to /onboarding
agent-browser get url
# Expect: https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/onboarding?session_id=cs_test_…
```

### L3 — Onboarding week-picker count (the critical assertion)

`agent-browser screenshot` at top of `/onboarding` then scroll-and-screenshot to capture all dropdowns. The header should read "Welcome, {Cardholder name}!" / "{Tier} — {Residential|Commercial}". The "Preferred Service Weeks" section must render the **exact picker count for the tier**:

| Tier | Expected picker labels (top-to-bottom) | Total |
|---|---|---|
| Essential | Spring Start-Up · Fall Winterization | **2** |
| Professional | Spring Start-Up · Mid-Season Inspection · Fall Winterization | **3** |
| **Premium** | Spring Start-Up · May Monitoring Visit & Tune Up · June · July · August · September Monitoring Visit & Tune Up · Fall Winterization | **7** |
| Winterization Only | Fall Winterization | **1** |

Each picker's option list is constrained to a sensible date range — Spring opens Feb–Jun, monthly_visit_5 is May only, fall_winterization is Sep–Nov. "No preference" is always option [1]. If a Premium picker shows e.g. 5 entries instead of 7 it's a regression in `frontend/src/features/portal/components/WeekPickerStep.tsx:14-72` (the `mapServicesToPickerList` expansion of `monthly_visit` into 5 month-specific keys).

Fill at least one specific week in `Spring Start-Up` and `Fall Winterization` (use real Mondays from the option list — e.g. `"Week of April 27, 2026"` and `"Week of October 5, 2026"`). Use `"No preference"` for the rest to save time.

```bash
agent-browser select @e24 "Week of April 27, 2026"
agent-browser select @e46 "No preference"   # May
agent-browser select @e54 "No preference"   # June
agent-browser select @e62 "No preference"   # July
agent-browser select @e70 "No preference"   # August
agent-browser select @e79 "No preference"   # September
agent-browser select @e87 "Week of October 5, 2026"
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/03-res-premium/13-onboarding-filled.png
agent-browser click @e104    # Complete Onboarding
sleep 6
```

After "You're All Set!" page loads, the test is functionally complete on the customer side.

### L4 — Verify in admin (API)

```bash
TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# Newest agreements (cache-bust required)
curl -s "https://grins-dev-dev.up.railway.app/api/v1/agreements?page_size=3&sort_by=created_at&sort_order=desc&_t=$(date +%s)" \
  -H "Authorization: Bearer $TOKEN" -H 'Cache-Control: no-cache' \
  | python3 -c "
import sys,json
for a in json.load(sys.stdin)['items'][:3]:
    print(f'{a[\"created_at\"][:19]} | tier={a[\"tier_name\"]} status={a[\"status\"]} customer={a[\"customer_id\"]}')"
# Expect newest row: tier=Premium status=active customer=e7ba9b51-… (Kirill Rakitin, since phone matched seed)

# Newest jobs created in the last 5 minutes (should be 7 for Premium)
SINCE=$(python3 -c "from datetime import datetime,timedelta,timezone;print((datetime.now(tz=timezone.utc)-timedelta(minutes=10)).isoformat())")
curl -s "https://grins-dev-dev.up.railway.app/api/v1/jobs?created_from=$SINCE&page_size=20&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
items = json.load(sys.stdin)['items']
print(f'Jobs in last 10 min: {len(items)}')
for j in items:
    s = j.get('target_start_date','?')[:10]; e = j.get('target_end_date','?')[:10]
    print(f'  {s} → {e} | {j[\"job_type\"]}')"
```

For Premium: expect **7 jobs**, types `spring_startup`, `monthly_visit` × 5, `fall_winterization`, with `target_start_date` matching the picker selections (full month windows for "No preference", specific Monday-week for explicit selections).

### L5 — Verify in admin (UI smoke)

```bash
agent-browser open "https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/agreements"
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/15-admin-agreements/01-agreements-list.png
# Expect newest row: AGR-2026-NNN Premium Residential Active $843 (= $725 base + $110 RPZ + $8 zone surcharge for the 10th zone)

agent-browser open "https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/jobs"
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/16-admin-jobs/01-jobs-list.png
# Expect rows: Monthly Visit + Fall Winterization with [Prepaid][Residential][Subscription] badges, status=To Be Scheduled, customer=Kirill Rakitin
```

If the agreement total doesn't match `base + RPZ + zone surcharge`, the surcharge math in `SubscriptionConfirmModal.tsx:209-233` (sibling repo) is out of sync with the backend pricing.

---

## Path Q — "Get Your Free Quote" Lead Intake

### Setup

```bash
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/"
agent-browser wait --load networkidle
mkdir -p e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/{09-lead-q1,10-lead-q2,11-lead-q3,12-lead-q4,13-lead-q5,14-admin-leads-verify}
```

The form is on the homepage right rail. Snapshot refs are stable across sessions:

```
e13 = radio "I'm a new customer"
e14 = radio "I'm an existing customer requesting work"
e15 = textbox "Full Name"
e16 = textbox "Phone Number"
e17 = textbox "Email"
e18 = textbox "Address"
e19 = combobox "Service Interested In"
e28 = radio "Residential"   |   e29 = radio "Commercial"   |   e30 = radio "Government"
e31 = combobox "How did you hear about us?"
e40 = textbox "Additional Notes"
e41 = button "Get My Free Quote"
e42 = checkbox SMS consent (transactional/informational)
e45 = checkbox Email marketing consent (promotional offers)
e46 = checkbox "I agree to the Terms & Conditions and Privacy Policy."
```

### Q1 — New + Residential + all consents (BUG-001 expected)

```bash
agent-browser click @e13                                          # New customer
agent-browser fill @e15 "E2E-Lead-Q1 Res New"
agent-browser fill @e16 "9527370310"                              # Unique phone
agent-browser fill @e17 "e2e-q1-$(date +%s)@grinstest.example"
agent-browser fill @e18 "310 E2E Q1 Res St, Plymouth, MN 55441"
agent-browser select @e19 "Irrigation Install"
agent-browser click @e28                                          # Residential
agent-browser select @e31 "Google"
agent-browser fill @e40 "Q1 — new + residential + all consents"
agent-browser click @e42                                          # SMS consent
agent-browser click @e45                                          # Email marketing
agent-browser click @e46                                          # T&C
agent-browser click @e41                                          # Submit
sleep 4
agent-browser eval "window.scrollTo(0,0);'ok'"
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/09-lead-q1/02-after-submit.png
# Expect customer-side: green "We'll reach out to you within 1-2 business days." banner
```

**Verify in admin:**

```bash
TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s "https://grins-dev-dev.up.railway.app/api/v1/leads?page_size=5&sort_by=created_at&sort_order=desc&_t=$(date +%s)" \
  -H "Authorization: Bearer $TOKEN" -H 'Cache-Control: no-cache' \
  | python3 -c "
import sys,json
for l in json.load(sys.stdin)['items'][:5]:
    print(f'{l[\"created_at\"][:19]} | {l[\"name\"]:35s} | phone={l[\"phone\"]:12s} | sms={l.get(\"sms_consent\")} cust={l.get(\"customer_type\")}')"
# Expect (until BUG-001 fixed): Q1 row is MISSING. Total count unchanged.
# After fix: Q1 row at top with sms_consent=True, customer_type=new, property_type=RESIDENTIAL.
```

### Q2 — New + Commercial + SMS only (BUG-001 expected)

Same flow with phone `9527370320`, click @e29 (Commercial), select "Smart Irrigation Upgrade", select "Referral", check SMS + T&C only (skip email marketing). Same expected outcome until BUG-001 is fixed.

### Q3 — Existing + Residential + email only (control case, MUST persist)

This is the canary. With `sms_consent=false` it should always land in admin — if it doesn't, something else broke.

```bash
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/"
agent-browser wait --load networkidle
agent-browser click @e14                                          # Existing customer
agent-browser fill @e15 "E2E-Lead-Q3 Res Existing"
agent-browser fill @e16 "9527370330"
agent-browser fill @e17 "e2e-q3-$(date +%s)@grinstest.example"
agent-browser fill @e18 "330 E2E Q3 St, Edina, MN 55424"
agent-browser select @e19 "Irrigation Repair"
agent-browser click @e28                                          # Residential
agent-browser select @e31 "Referral"
agent-browser fill @e40 "Q3 — existing + residential + repair, SMS OFF, email ON, TC ON"
# DO NOT click @e42 (no SMS consent)
agent-browser click @e45                                          # Email marketing
agent-browser click @e46                                          # T&C
agent-browser click @e41
sleep 4

# Verify (cache-bust!)
curl -s "https://grins-dev-dev.up.railway.app/api/v1/leads?page_size=3&sort_by=created_at&sort_order=desc&_t=$(date +%s)" \
  -H "Authorization: Bearer $TOKEN" -H 'Cache-Control: no-cache' \
  | python3 -c "
import sys,json
top = json.load(sys.stdin)['items'][0]
expected = {
  'name':'E2E-Lead-Q3 Res Existing','phone':'9527370330',
  'sms_consent':False,'terms_accepted':True,'email_marketing_consent':True,
  'customer_type':'existing','property_type':'RESIDENTIAL',
  'situation':'repair','source_site':'website','lead_source':'referral'}
for k,v in expected.items():
    actual = top.get(k)
    status = 'OK' if actual == v else 'FAIL'
    print(f'  {status:4s} {k}: expected={v!r:30s} actual={actual!r}')"
# Every line must say OK. If any FAIL, regression.
```

### Q4 — Duplicate of Q3 (expect 409 banner)

Re-submit the exact same Q3 payload (or just the same phone `9527370330`) within 24h. Expect:

- Customer-side banner changes to **"We already have your information. A team member will be in touch shortly."**
- POST returns HTTP 409 with body `{"detail":"duplicate_lead", ...}`. Verify in `agent-browser network requests --filter leads`.

### Q5 — Missing T&C → client-side validation block

```bash
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/"
agent-browser wait --load networkidle
# Fill everything EXCEPT click @e46
agent-browser click @e13
agent-browser fill @e15 "E2E-Lead-Q5 No TC"
agent-browser fill @e16 "9527370350"
agent-browser fill @e17 "e2e-q5-$(date +%s)@grinstest.example"
agent-browser fill @e18 "350 E2E Q5 St"
agent-browser select @e19 "Seasonal Maintenance"
agent-browser click @e28
agent-browser select @e31 "Google"
agent-browser fill @e40 "Q5 — no T&C"
agent-browser click @e42                                          # SMS consent (irrelevant since blocked)
# Skip @e46 — no T&C
agent-browser click @e41
sleep 2
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/13-lead-q5/02-validation-error.png
# Expect: red text "You must agree to the Terms & Conditions and Privacy Policy." near the checkbox.
# No POST should fire — verify with `agent-browser network requests --filter leads` (should be empty for this submit).
```

### Q6 (optional) — Lead detail field round-trip in admin UI

After Q3 lands, open the admin and screenshot the detail card to prove every field surfaces:

```bash
agent-browser open "https://grins-irrigation-platform-git-dev-kirilldr01s-projects.vercel.app/leads"
agent-browser wait --load networkidle
# Find row by name
LINK=$(agent-browser snapshot -i | grep 'link "E2E-Lead-Q3 Res Existing"' | grep -oE 'ref=e[0-9]+' | head -1 | cut -d= -f2)
agent-browser click "@$LINK"
agent-browser wait --load networkidle
agent-browser scroll down
agent-browser screenshot e2e-screenshots/customer-landing-$(date +%Y-%m-%d)/14-admin-leads-verify/06-lead-detail.png
# Expected sections (top-to-bottom):
#   Contact Information  → Phone, Email
#   Address              → 330 E2E Q3 St, Edina, MN 55424
#   Service Details      → Situation: Repair, Source Site: website, Lead Source: Referral, Intake Tag: Schedule
#   Notes                → "Q3 — existing + residential + repair, SMS OFF, email ON, TC ON"
#   Consent Status       → SMS Consent: Not given · Email Marketing Consent: Opted in · T&Cs: Accepted
```

---

## Quick-fire smoke (5 minutes)

If you only have 5 minutes between sprints and want to detect regressions:

```bash
# 1. Lead form control case (Q3 only — proves the non-bug path still works)
curl -sS -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"Smoke-$(date +%s)\",\"phone\":\"95273703$(date +%S)\",
       \"email\":\"smoke-$(date +%s)@grinstest.example\",\"address\":\"1 Smoke St\",
       \"situation\":\"repair\",\"source_site\":\"website\",\"website\":\"\",
       \"property_type\":\"RESIDENTIAL\",\"lead_source\":\"other\",
       \"sms_consent\":false,\"terms_accepted\":true,\"email_marketing_consent\":false}" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("lead_id:",d.get("lead_id"));assert d.get("success")'

# 2. BUG-001 regression check (this should FAIL until the bug is fixed; once fixed it should succeed)
RESP=$(curl -s -X POST "https://grins-dev-dev.up.railway.app/api/v1/leads" \
  -H 'Content-Type: application/json' \
  -d "{\"name\":\"BugCheck-$(date +%s)\",\"phone\":\"95273704$(date +%S)\",
       \"email\":\"bugcheck-$(date +%s)@grinstest.example\",\"address\":\"1 Bug St\",
       \"situation\":\"new_system\",\"source_site\":\"website\",\"website\":\"\",
       \"property_type\":\"RESIDENTIAL\",\"lead_source\":\"other\",
       \"sms_consent\":true,\"terms_accepted\":true,\"email_marketing_consent\":true}")
LID=$(echo "$RESP" | python3 -c 'import sys,json;print(json.load(sys.stdin)["lead_id"])')
TOKEN=$(curl -s https://grins-dev-dev.up.railway.app/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s "https://grins-dev-dev.up.railway.app/api/v1/leads/$LID" -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("BUG-001:", "STILL ACTIVE" if d.get("error",{}).get("code")=="LEAD_NOT_FOUND" else "FIXED")'

# 3. Service packages page renders all 8 tiers
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/service-packages"
agent-browser wait --load networkidle
COUNT=$(agent-browser snapshot -i | grep -cE 'button "Subscribe to .* Plan')
[ "$COUNT" = "8" ] && echo "Subscribe buttons: 8 ✓" || echo "Subscribe buttons: $COUNT (expected 8) ✗"
```

---

## When something fails

- **No 8 Subscribe buttons** → check sibling repo `frontend/src/shared/components/sections/PricingSection.tsx` and `frontend/src/shared/data/pricing.ts:86-205`. Check the deployed Vercel commit on dev branch matches.
- **Premium onboarding shows fewer than 7 pickers** → check `frontend/src/features/portal/components/WeekPickerStep.tsx:14-72` (mapServicesToPickerList expansion) and `src/grins_platform/api/v1/onboarding.py` `verify-session` response — `services_with_types` must contain a `monthly_visit` entry for Premium.
- **Q3 lead doesn't appear in admin** → first try cache-bust (`?_t=$(date +%s)`). If still missing, check `services/lead_service.py` — something else regressed beyond BUG-001.
- **Q4 doesn't show duplicate banner** → 24h dedup window may have lapsed. Use a phone that was just submitted in the same session.
- **Stripe redirect never happens** → check `agent-browser console` for `pre-checkout-consent` 4xx/5xx; check Railway logs for `consent_token` errors. May indicate `STRIPE_SECRET_KEY` mismatch on dev.
- **Onboarding 404s after Stripe** → the `success_url` template (sibling repo `frontend/src/features/service-packages/api/checkoutApi.ts:114`) may not match the deployed origin.

After a clean run, bug-hunt findings (if any) go into `bughunt/YYYY-MM-DD-<short-name>.md`.

---

## Reference artifacts from 2026-04-14 baseline run

- Bughunt: `bughunt/2026-04-14-lead-form-sms-consent-rollback.md`
- Full report: `e2e-screenshots/customer-landing-2026-04-14/REPORT.md`
- 59 screenshots across 17 folders under `e2e-screenshots/customer-landing-2026-04-14/`
