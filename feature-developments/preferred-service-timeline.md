# Feature: Preferred Service Timeline (Onboarding)

**Status:** Planning
**Date:** 2026-03-28
**Repos:** `Grins_irrigation` (frontend), `Grins_irrigation_platform` (backend)

---

## Overview

Add a "Preferred Service Timeline" dropdown to the onboarding form so customers can indicate **when** they'd like their service performed. This sits between the existing "Preferred Service Times" (morning/afternoon) radio buttons and the "Complete Onboarding" button.

### Customer-facing copy

- **Label:** "When would you like this service done?"
- **Note below dropdown:** "We will contact you the week prior to schedule your service. Please note that your selected timeframe is not guaranteed and may be adjusted based on lead time, availability, weather, and other factors."

### Options

| Display Label | Enum Value |
|---|---|
| As Soon As Possible | `ASAP` |
| Within 1-2 Weeks | `ONE_TWO_WEEKS` |
| Within 3-4 Weeks | `THREE_FOUR_WEEKS` |
| Other (please specify week or dates) | `OTHER` |

When "Other" is selected, a free-text input appears for the customer to specify their preferred week or dates.

---

## Implementation Steps

### Phase 1: Backend — Database & Model (Platform Repo)

#### Step 1.1: Add Alembic migration for new columns

- **File:** `src/grins_platform/migrations/versions/{next}_add_preferred_schedule.py`
- Add two columns to the `customers` table:
  - `preferred_schedule` — `String(30)`, nullable, default `NULL`
  - `preferred_schedule_details` — `Text`, nullable, default `NULL`
- Migration naming convention per steering: `{num}_customer_add_preferred_schedule.py`

#### Step 1.2: Update Customer model

- **File:** `src/grins_platform/models/customer.py`
- Add `preferred_schedule: Mapped[Optional[str]]` — `mapped_column(String(30), nullable=True)`
- Add `preferred_schedule_details: Mapped[Optional[str]]` — `mapped_column(Text, nullable=True)`
- Place after the existing `preferred_service_times` field (~line 147)

### Phase 2: Backend — API & Service Layer (Platform Repo)

#### Step 2.1: Update `CompleteOnboardingRequest` schema

- **File:** `src/grins_platform/api/v1/onboarding.py`
- Add to `CompleteOnboardingRequest` (after `preferred_times` field, ~line 130):
  - `preferred_schedule: str = Field(default="ASAP", description="When customer wants service done")`
  - `preferred_schedule_details: str | None = Field(default=None, description="Free-text details for 'Other' schedule preference")`
- Valid enum values: `ASAP`, `ONE_TWO_WEEKS`, `THREE_FOUR_WEEKS`, `OTHER`
- Add a `@model_validator` (or field validator) to enforce that `preferred_schedule_details` is required when `preferred_schedule == "OTHER"`

#### Step 2.2: Update `OnboardingService.complete_onboarding()`

- **File:** `src/grins_platform/services/onboarding_service.py`
- Add `preferred_schedule` and `preferred_schedule_details` parameters to the method signature (~line 194)
- After the existing `customer.preferred_service_times` update (~line 312), add:
  ```python
  customer.preferred_schedule = preferred_schedule
  customer.preferred_schedule_details = preferred_schedule_details
  ```
- Add structured logging per steering (`code-standards.md`):
  ```python
  self.log_started("update_preferred_schedule", schedule=preferred_schedule)
  self.log_completed("update_preferred_schedule", schedule=preferred_schedule)
  ```

#### Step 2.3: Update the `/complete` endpoint handler

- **File:** `src/grins_platform/api/v1/onboarding.py`
- In the `complete_onboarding` endpoint handler (~line 308-381), pass the new fields through to the service:
  ```python
  result = await service.complete_onboarding(
      ...,
      preferred_schedule=body.preferred_schedule,
      preferred_schedule_details=body.preferred_schedule_details,
  )
  ```

#### Step 2.4: Expose in Customer API responses (admin dashboard)

- **File:** `src/grins_platform/schemas/customer.py` (or wherever `CustomerResponse` is defined)
- Add `preferred_schedule: str | None` and `preferred_schedule_details: str | None` to the response schema
- Ensure the GET customer endpoint returns these fields

#### Step 2.5: Update Customer PUT/PATCH endpoint

- If the admin dashboard allows editing customer preferences, ensure the update schema also accepts `preferred_schedule` and `preferred_schedule_details`
- **File:** `src/grins_platform/api/v1/customers.py` (update request schema)

### Phase 3: Frontend — Onboarding Form (Grins_irrigation Repo)

#### Step 3.1: Update TypeScript types

- **File:** `frontend/src/features/onboarding/types/index.ts`
- Add to `OnboardingFormData`:
  ```typescript
  preferred_schedule: 'ASAP' | 'ONE_TWO_WEEKS' | 'THREE_FOUR_WEEKS' | 'OTHER';
  preferred_schedule_details?: string;
  ```
- Add same fields to `OnboardingCompleteRequest`

#### Step 3.2: Update form state initialization

- **File:** `frontend/src/features/onboarding/components/OnboardingPage.tsx`
- Add to the `useState<OnboardingFormData>` initial state (~line 20-26):
  ```typescript
  preferred_schedule: 'ASAP',
  preferred_schedule_details: '',
  ```

#### Step 3.3: Add the dropdown + conditional text input to the form

- **File:** `frontend/src/features/onboarding/components/OnboardingPage.tsx`
- Insert **after** the "Preferred Service Times" `<fieldset>` (~line 280) and **before** the submit error/button (~line 282)
- Structure:
  ```
  <div className="mb-6">
    <label for="preferred-schedule">When would you like this service done?</label>
    <select id="preferred-schedule" data-testid="onboarding-preferred-schedule" ...>
      <option value="ASAP">As Soon As Possible</option>
      <option value="ONE_TWO_WEEKS">Within 1-2 Weeks</option>
      <option value="THREE_FOUR_WEEKS">Within 3-4 Weeks</option>
      <option value="OTHER">Other (please specify week or dates)</option>
    </select>

    {formData.preferred_schedule === 'OTHER' && (
      <input type="text" data-testid="onboarding-schedule-details" placeholder="..." />
    )}

    <p className="mt-2 text-sm text-gray-500">
      We will contact you the week prior to schedule your service.
      Please note that your selected timeframe is not guaranteed and
      may be adjusted based on lead time, availability, weather, and
      other factors.
    </p>
  </div>
  ```
- **data-testid values** (per `frontend-patterns.md` convention):
  - Dropdown: `onboarding-preferred-schedule`
  - Text input: `onboarding-schedule-details`
  - Note paragraph: `onboarding-schedule-note`
- Ensure the `<select>` and `<input>` have `min-h-[44px]` for touch targets (consistent with existing form elements)
- Use `onChange` to update `formData.preferred_schedule` and `formData.preferred_schedule_details`

#### Step 3.4: Update form submission payload

- **File:** `frontend/src/features/onboarding/components/OnboardingPage.tsx`
- In `handleSubmit` (~line 67-70), the spread `...formData` already includes the new fields
- Add validation: if `preferred_schedule === 'OTHER'` and `preferred_schedule_details` is empty, show error "Please specify your preferred week or dates."
- Ensure `preferred_schedule_details` is only sent when `preferred_schedule === 'OTHER'` (set to `undefined` otherwise)

### Phase 4: Frontend — Admin Dashboard (Platform Repo)

#### Step 4.1: Update customer types

- **File:** `frontend/src/features/customers/types/index.ts` (platform repo)
- Add `preferred_schedule?: string` and `preferred_schedule_details?: string` to the Customer type

#### Step 4.2: Display in CustomerDetail component

- **File:** `frontend/src/features/customers/components/CustomerDetail.tsx`
- Add a read-only display section near the existing "Preferred Service Times" display (~line 410-426)
- Show:
  - **Label:** "Preferred Service Timeline"
  - **Value:** Human-readable label (map enum → display: `ASAP` → "As Soon As Possible", etc.)
  - If `OTHER`, also show the `preferred_schedule_details` text
- Use `data-testid="customer-preferred-schedule"` per steering convention
- Consider making it editable (inline edit pattern matching existing service time edit at ~line 97-102)

#### Step 4.3: Add to OnboardingIncompleteQueue (if applicable)

- **File:** `frontend/src/features/agreements/components/OnboardingIncompleteQueue.tsx` (platform repo)
- If this queue shows onboarding details, consider displaying the preferred schedule here too so the team can prioritize ASAP requests

### Phase 5: Backend Testing (Platform Repo)

Per `code-standards.md` — three-tier testing is mandatory.

#### Step 5.1: Unit tests

- **File:** `src/grins_platform/tests/unit/test_onboarding_preferred_schedule.py`
- Mark with `@pytest.mark.unit`
- Test cases:
  - `test_complete_onboarding_request_defaults_to_asap` — verify default value
  - `test_complete_onboarding_request_validates_other_requires_details` — `OTHER` without details → validation error
  - `test_complete_onboarding_request_accepts_all_enum_values` — all 4 values accepted
  - `test_complete_onboarding_request_rejects_invalid_schedule` — invalid value → validation error

#### Step 5.2: Functional tests

- **File:** `src/grins_platform/tests/functional/test_onboarding_preferred_schedule.py`
- Mark with `@pytest.mark.functional`
- Test cases (real DB):
  - `test_complete_onboarding_saves_preferred_schedule_to_customer` — submit with `ONE_TWO_WEEKS`, verify customer record
  - `test_complete_onboarding_saves_other_with_details` — submit `OTHER` + details text, verify both columns
  - `test_complete_onboarding_asap_has_no_details` — submit `ASAP`, verify `preferred_schedule_details` is `NULL`
  - `test_customer_api_returns_preferred_schedule` — GET customer includes new fields

#### Step 5.3: Integration tests

- **File:** `src/grins_platform/tests/integration/test_onboarding_preferred_schedule.py`
- Mark with `@pytest.mark.integration`
- End-to-end: POST `/api/v1/onboarding/complete` with schedule fields → verify response + DB state + GET customer reflects values

### Phase 6: Frontend Testing (Grins_irrigation Repo)

Per `frontend-testing.md` — Vitest + RTL + fast-check.

#### Step 6.1: Update existing onboarding tests

- **File:** `frontend/src/features/onboarding/__tests__/onboarding-page.test.tsx`
- **Update existing test** `'submits form and transitions to success state'` (~line 130-135) — add `preferred_schedule: 'ASAP'` to the `expect.objectContaining({...})` assertion, since the new field will now be part of the submit payload
- Add new test cases:
  - `renders preferred schedule dropdown with all 4 options`
  - `shows schedule details input when "Other" is selected`
  - `hides schedule details input when non-Other option is selected`
  - `renders the disclaimer note about scheduling not being guaranteed`
  - `defaults to ASAP`

#### Step 6.2: Update form submission payload tests

- **File:** `frontend/src/features/onboarding/__tests__/form-submission-payload.property.test.ts`
- Add property-based tests:
  - `payload always includes preferred_schedule field`
  - `preferred_schedule_details only present when preferred_schedule is OTHER`
  - `preferred_schedule is always one of the 4 valid enum values`

#### Step 6.3: Validation tests

- New or existing test file
- `shows error when Other is selected but details field is empty on submit`
- `submits successfully when Other is selected with details filled`

### Phase 7: Quality Checks

#### Step 7.1: Backend quality (platform repo)

```bash
uv run ruff check --fix src/
uv run ruff format src/
uv run mypy src/
uv run pyright src/
uv run pytest -m unit -v
uv run pytest -m functional -v
```

#### Step 7.2: Frontend quality (Grins_irrigation repo)

```bash
cd frontend && npm run typecheck
cd frontend && npm run lint
cd frontend && npm test
```

### Phase 8: Migration & Deployment

#### Step 8.1: Run migration on dev

```bash
alembic upgrade head
```

#### Step 8.2: Deploy to dev environment

- Deploy backend (Railway) first — migration + code
- Deploy frontend (Vercel) second — both repos
- Confirm both services are healthy before proceeding to E2E testing

---

### Phase 9: End-to-End Testing (agent-browser)

Full browser-based E2E validation using `agent-browser` CLI, following the patterns established in `.claude/skills/e2e-test/SKILL.md` and the existing scripts in `scripts/e2e/`.

#### Step 9.0: Pre-flight checks

Per the E2E skill's pre-flight protocol:
```bash
# Verify platform
uname -s   # Must be Darwin or Linux

# Verify agent-browser is installed
agent-browser --version

# If not installed:
npm install -g agent-browser && agent-browser install --with-deps
```

#### Step 9.1: E2E — Onboarding form (Grins_irrigation frontend on Vercel dev)

**Goal:** Validate the new preferred schedule dropdown renders correctly, "Other" conditional input works, disclaimer note is visible, and the form submits successfully with each option.

Screenshots saved to: `e2e-screenshots/preferred-schedule/`

##### Test 9.1.1: Full Stripe checkout → onboarding flow with ASAP

Follow the Stripe Checkout Automation Guide (`.claude/skills/e2e-test/STRIPE-CHECKOUT-AUTOMATION-GUIDE.md`):

```bash
# 1. Navigate to service packages page (dev Vercel deployment)
agent-browser open "https://grins-irrigation-git-dev-kirilldr01s-projects.vercel.app/service-packages"
agent-browser wait --load networkidle

# 2. Subscribe to a tier (e.g., Essential — $170/year)
agent-browser scroll down
agent-browser snapshot -i
# Click the subscribe button for the desired tier
agent-browser click @eXX   # "Subscribe to Essential Plan"

# 3. Fill pre-checkout modal
agent-browser snapshot -i
agent-browser fill @eXX "6125550199"    # Phone number
agent-browser fill @eXX "5"              # Zone count
agent-browser click @eXX                 # SMS consent checkbox
agent-browser click @eXX                 # "Confirm Subscription" button

# 4. Complete Stripe checkout (test card 4242424242424242)
# (Follow steps 2-8 from STRIPE-CHECKOUT-AUTOMATION-GUIDE.md)
sleep 10
agent-browser get url   # Should be checkout.stripe.com
# ... fill email, phone, expand card accordion via eval, fill card, billing, subscribe ...

# 5. Land on onboarding page
sleep 15
agent-browser get url   # Should be /onboarding?session_id=cs_test_...
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/preferred-schedule/01-onboarding-page-loaded.png
```

##### Test 9.1.2: Verify new dropdown renders with all 4 options

```bash
# Snapshot interactive elements
agent-browser snapshot -i

# Verify the preferred schedule dropdown is visible
agent-browser is visible "[data-testid='onboarding-preferred-schedule']"
agent-browser screenshot e2e-screenshots/preferred-schedule/02-dropdown-visible.png

# Verify default is "As Soon As Possible" (ASAP)
agent-browser get text "[data-testid='onboarding-preferred-schedule']"
# Should contain "As Soon As Possible"

# Verify the disclaimer note is visible
agent-browser is visible "[data-testid='onboarding-schedule-note']"
agent-browser get text "[data-testid='onboarding-schedule-note']"
# Should contain "not guaranteed" and "lead time, availability, weather"
agent-browser screenshot e2e-screenshots/preferred-schedule/03-disclaimer-note.png

# Verify all 4 options exist in the dropdown
agent-browser select "[data-testid='onboarding-preferred-schedule']" "As Soon As Possible"
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Within 1-2 Weeks"
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Within 3-4 Weeks"
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Other (please specify week or dates)"
agent-browser screenshot e2e-screenshots/preferred-schedule/04-all-options-verified.png
```

##### Test 9.1.3: "Other" conditional text input

```bash
# Select "Other" — details input should appear
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Other (please specify week or dates)"
agent-browser wait 500
agent-browser is visible "[data-testid='onboarding-schedule-details']"
agent-browser screenshot e2e-screenshots/preferred-schedule/05-other-details-input-visible.png

# Switch to a non-Other option — details input should disappear
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Within 1-2 Weeks"
agent-browser wait 500
# Verify details input is NOT visible
agent-browser screenshot e2e-screenshots/preferred-schedule/06-details-input-hidden.png
```

##### Test 9.1.4: Validation — "Other" requires details

```bash
# Select "Other" and leave details empty, try to submit
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Other (please specify week or dates)"
agent-browser wait 500
# Leave the details field empty
agent-browser click "[data-testid='onboarding-submit-btn']"
agent-browser wait 1000

# Should show validation error
agent-browser screenshot e2e-screenshots/preferred-schedule/07-other-validation-error.png
# Verify error text is visible: "Please specify your preferred week or dates."
```

##### Test 9.1.5: Submit with ASAP and verify success

```bash
# Select ASAP
agent-browser select "[data-testid='onboarding-preferred-schedule']" "As Soon As Possible"

# Fill other required onboarding fields
agent-browser fill "[data-testid='onboarding-gate-code']" "4321"
agent-browser click "[data-testid='onboarding-has-dogs']"
agent-browser fill "[data-testid='onboarding-access-instructions']" "E2E test — side gate"
agent-browser click "[data-testid='onboarding-time-morning']"

# Submit
agent-browser click "[data-testid='onboarding-submit-btn']"
agent-browser wait --load networkidle
sleep 5

# Should transition to success state
agent-browser is visible "[data-testid='onboarding-success']"
agent-browser screenshot e2e-screenshots/preferred-schedule/08-submit-asap-success.png
```

##### Test 9.1.6: Submit with "Other" + details (separate checkout)

Repeat the Stripe checkout flow (steps 9.1.1) for a new test customer, then:

```bash
# On the onboarding page, select "Other" and fill details
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Other (please specify week or dates)"
agent-browser fill "[data-testid='onboarding-schedule-details']" "Week of April 14th preferred"

# Fill other onboarding fields and submit
agent-browser fill "[data-testid='onboarding-gate-code']" "9999"
agent-browser fill "[data-testid='onboarding-access-instructions']" "E2E test — Other option"
agent-browser click "[data-testid='onboarding-submit-btn']"
agent-browser wait --load networkidle
sleep 5

agent-browser is visible "[data-testid='onboarding-success']"
agent-browser screenshot e2e-screenshots/preferred-schedule/09-submit-other-success.png
```

#### Step 9.2: Database validation via Railway API

After each successful onboarding submission, verify the data persisted correctly using the Railway REST API (per `RAILWAY-API-ACCESS-GUIDE.md`). No direct DB access — Railway PostgreSQL uses an internal hostname.

```bash
# Authenticate
TOKEN=$(curl -s "https://grins-dev-dev.up.railway.app/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Get the most recent customer (the one we just onboarded)
curl -s "https://grins-dev-dev.up.railway.app/api/v1/customers?page=1&page_size=1&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
data = json.load(sys.stdin)
c = data['items'][0]
print(f\"Customer: {c['first_name']} {c['last_name']}\")
print(f\"preferred_schedule: {c.get('preferred_schedule', 'MISSING')}\")
print(f\"preferred_schedule_details: {c.get('preferred_schedule_details', 'MISSING')}\")
print(f\"preferred_service_times: {c.get('preferred_service_times', 'MISSING')}\")
"
```

**Validation checks:**

| Test Case | Expected `preferred_schedule` | Expected `preferred_schedule_details` |
|---|---|---|
| ASAP submission (Test 9.1.5) | `ASAP` | `NULL` / not present |
| Other submission (Test 9.1.6) | `OTHER` | `"Week of April 14th preferred"` |

Also verify via the agreement and jobs endpoints:
```bash
# Get the latest agreement to confirm it's linked correctly
curl -s "https://grins-dev-dev.up.railway.app/api/v1/agreements?page=1&page_size=1&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "
import sys,json
a = json.load(sys.stdin)['items'][0]
print(f\"Agreement: {a['agreement_number']} | Status: {a['status']} | Payment: {a['payment_status']}\")
print(f\"Customer: {a.get('customer_name','?')}\")
"
```

#### Step 9.3: E2E — Admin dashboard (Platform frontend)

**Goal:** Verify the preferred schedule is visible in the CustomerDetail view on the admin dashboard, and that it can be edited if the edit feature is implemented.

##### Test 9.3.1: Login to admin dashboard

Follow the pattern from `scripts/e2e/test-customers.sh`:

```bash
BASE_URL="http://localhost:5173"  # or Vercel dev deployment URL

agent-browser open "${BASE_URL}/login"
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/preferred-schedule/10-admin-login.png

# Fill credentials (using data-testid with fallbacks per test-customers.sh pattern)
if agent-browser is visible "[data-testid='email-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='email-input']" "admin@grins.com"
elif agent-browser is visible "[name='email']" 2>/dev/null; then
  agent-browser fill "[name='email']" "admin@grins.com"
elif agent-browser is visible "input[type='email']" 2>/dev/null; then
  agent-browser fill "input[type='email']" "admin@grins.com"
fi

if agent-browser is visible "[data-testid='password-input']" 2>/dev/null; then
  agent-browser fill "[data-testid='password-input']" "admin123"
elif agent-browser is visible "input[type='password']" 2>/dev/null; then
  agent-browser fill "input[type='password']" "admin123"
fi

if agent-browser is visible "[data-testid='login-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='login-btn']"
elif agent-browser is visible "button[type='submit']" 2>/dev/null; then
  agent-browser click "button[type='submit']"
fi

agent-browser wait --load networkidle
agent-browser wait 2000
agent-browser screenshot e2e-screenshots/preferred-schedule/11-admin-dashboard.png
```

##### Test 9.3.2: Navigate to the customer detail page

```bash
# Navigate to customers list
agent-browser open "${BASE_URL}/customers"
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/preferred-schedule/12-customers-list.png

# Click on the most recently created customer (the one from our E2E checkout)
agent-browser snapshot -i
# Click the first customer row
agent-browser click @eXX  # First customer row
agent-browser wait --load networkidle
agent-browser screenshot e2e-screenshots/preferred-schedule/13-customer-detail.png
```

##### Test 9.3.3: Verify preferred schedule is displayed

```bash
# Scroll to the service preferences section
agent-browser scroll down 500
agent-browser wait 500

# Verify the preferred schedule section is visible
agent-browser is visible "[data-testid='customer-preferred-schedule']"
agent-browser get text "[data-testid='customer-preferred-schedule']"
# Should show "As Soon As Possible" or "Other: Week of April 14th preferred"

agent-browser screenshot e2e-screenshots/preferred-schedule/14-preferred-schedule-visible.png
```

##### Test 9.3.4: Verify preferred schedule edit (if editable)

```bash
# If an edit button exists, test the edit flow
if agent-browser is visible "[data-testid='edit-preferred-schedule-btn']" 2>/dev/null; then
  agent-browser click "[data-testid='edit-preferred-schedule-btn']"
  agent-browser wait 500
  agent-browser screenshot e2e-screenshots/preferred-schedule/15-schedule-edit-mode.png

  # Change the selection
  agent-browser select "[data-testid='preferred-schedule-select']" "Within 3-4 Weeks"
  agent-browser screenshot e2e-screenshots/preferred-schedule/16-schedule-changed.png

  # Save
  if agent-browser is visible "[data-testid='save-preferred-schedule-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-preferred-schedule-btn']"
  elif agent-browser is visible "[data-testid='save-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='save-btn']"
  fi

  agent-browser wait --load networkidle
  agent-browser wait 1000

  # Reload page and verify persistence
  DETAIL_URL=$(agent-browser get url)
  agent-browser open "$DETAIL_URL"
  agent-browser wait --load networkidle
  agent-browser scroll down 500
  agent-browser wait 500

  SCHEDULE_TEXT=$(agent-browser get text "[data-testid='customer-preferred-schedule']" 2>/dev/null || echo "")
  if echo "$SCHEDULE_TEXT" | grep -qi "3-4 Weeks"; then
    echo "  ✓ Preferred schedule persisted after reload (3-4 Weeks)"
  else
    echo "  ⚠ Could not confirm '3-4 Weeks' preference persisted (text: ${SCHEDULE_TEXT:0:80})"
  fi

  agent-browser screenshot e2e-screenshots/preferred-schedule/17-schedule-persisted.png
fi
```

#### Step 9.4: E2E — Add to `scripts/e2e/test-customers.sh` (Platform Repo)

**File:** `scripts/e2e/test-customers.sh`

Add a new step after the existing "Step 7: Preferred Service Times" block (~line 596) to test the new preferred schedule field. Follow the same pattern as Step 7 (which tests `preferred_service_times`):

```bash
# ---------------------------------------------------------------------------
# Step 7b: Test Preferred Service Timeline Display & Edit
# ---------------------------------------------------------------------------
echo ""
echo "Step 7b: Testing preferred service timeline display (preferred_schedule)..."

agent-browser scroll down 500 2>/dev/null || true
agent-browser wait 500
agent-browser screenshot "$SCREENSHOT_DIR/20b-before-preferred-schedule.png"

if agent-browser is visible "[data-testid='customer-preferred-schedule']" 2>/dev/null; then
  echo "  ✓ Preferred Schedule section visible"
  PASS_COUNT=$((PASS_COUNT + 1))

  SCHEDULE_TEXT=$(agent-browser get text "[data-testid='customer-preferred-schedule']" 2>/dev/null || echo "")
  echo "  Current preferred schedule: $SCHEDULE_TEXT"

  # Test edit flow if available
  if agent-browser is visible "[data-testid='edit-preferred-schedule-btn']" 2>/dev/null; then
    agent-browser click "[data-testid='edit-preferred-schedule-btn']"
    agent-browser wait 500
    agent-browser screenshot "$SCREENSHOT_DIR/20c-preferred-schedule-edit.png"

    # Select a new preference
    if agent-browser is visible "[data-testid='preferred-schedule-select']" 2>/dev/null; then
      agent-browser select "[data-testid='preferred-schedule-select']" "Within 1-2 Weeks" 2>/dev/null || \
        agent-browser select "[data-testid='preferred-schedule-select']" "ONE_TWO_WEEKS" 2>/dev/null || true
    fi

    agent-browser screenshot "$SCREENSHOT_DIR/20d-preferred-schedule-selected.png"

    # Save
    if agent-browser is visible "[data-testid='save-preferred-schedule-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='save-preferred-schedule-btn']"
    elif agent-browser is visible "[data-testid='save-btn']" 2>/dev/null; then
      agent-browser click "[data-testid='save-btn']"
    fi

    agent-browser wait --load networkidle
    agent-browser wait 1000
    agent-browser screenshot "$SCREENSHOT_DIR/20e-preferred-schedule-saved.png"

    echo "  ✓ Preferred Schedule edit flow completed"
    PASS_COUNT=$((PASS_COUNT + 1))
  fi
else
  echo "  ✗ FAIL: Preferred Schedule section not found (data-testid='customer-preferred-schedule')"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi
```

#### Step 9.5: Responsive testing — onboarding form

Per the E2E skill's responsive testing protocol, verify the new dropdown renders correctly at all viewports:

```bash
# Test on the onboarding page (or use a snapshot if session expired)
# Mobile
agent-browser set viewport 375 812
agent-browser open "https://grins-irrigation-git-dev.../onboarding?session_id=cs_test_..."
agent-browser wait --load networkidle
agent-browser scroll down 300
agent-browser screenshot e2e-screenshots/preferred-schedule/18-mobile-dropdown.png

# Verify dropdown and note are visible and not clipped
agent-browser is visible "[data-testid='onboarding-preferred-schedule']"
agent-browser is visible "[data-testid='onboarding-schedule-note']"

# Select "Other" and verify details input renders on mobile
agent-browser select "[data-testid='onboarding-preferred-schedule']" "Other (please specify week or dates)"
agent-browser wait 500
agent-browser screenshot e2e-screenshots/preferred-schedule/19-mobile-other-input.png

# Tablet
agent-browser set viewport 768 1024
agent-browser screenshot e2e-screenshots/preferred-schedule/20-tablet-dropdown.png

# Desktop
agent-browser set viewport 1440 900
agent-browser screenshot e2e-screenshots/preferred-schedule/21-desktop-dropdown.png
```

#### Step 9.6: Console & error checks

```bash
# Check for JavaScript errors throughout all tests
agent-browser console    # Review for warnings/errors
agent-browser errors     # Check for uncaught exceptions

# Any JS errors related to preferred_schedule, onboarding, or form state = FAIL
```

#### Step 9.7: E2E test report

After all E2E tests complete, generate a summary following the E2E skill report format:

```
## E2E Testing Complete — Preferred Service Timeline

**Journeys Tested:** [count]
**Screenshots Captured:** [count] (saved to e2e-screenshots/preferred-schedule/)
**Issues Found:** [count] ([count] fixed, [count] remaining)

### Test Results
| Test | Status | Screenshot |
|---|---|---|
| 9.1.2 Dropdown renders with 4 options | ✓/✗ | 02-dropdown-visible.png |
| 9.1.3 "Other" conditional input toggle | ✓/✗ | 05/06-*.png |
| 9.1.4 Validation — Other requires details | ✓/✗ | 07-other-validation-error.png |
| 9.1.5 Submit with ASAP | ✓/✗ | 08-submit-asap-success.png |
| 9.1.6 Submit with Other + details | ✓/✗ | 09-submit-other-success.png |
| 9.2 DB validation — preferred_schedule persisted | ✓/✗ | — |
| 9.3.3 Admin dashboard — schedule displayed | ✓/✗ | 14-preferred-schedule-visible.png |
| 9.3.4 Admin dashboard — schedule edit | ✓/✗ | 15-17-*.png |
| 9.5 Responsive — mobile/tablet/desktop | ✓/✗ | 18-21-*.png |
| 9.6 No JS errors | ✓/✗ | — |

### Issues Found & Fixed
- [Description] — [file:line]

### Remaining Issues
- [Description] — [severity: high/medium/low] — [file:line]

### Screenshots
All saved to: `e2e-screenshots/preferred-schedule/`
```

Optionally export the full report to `e2e-screenshots/preferred-schedule/E2E-REPORT.md`.

---

### Phase 10: Production Deployment

#### Step 10.1: Deploy to production

- Deploy backend (Railway) first — migration + code
- Deploy frontend (Vercel) second — both repos

#### Step 10.2: Production smoke test

- Complete one real onboarding flow on production with each schedule option
- Verify data appears in the production admin dashboard
- Confirm no JS errors in browser console

---

## Steering Compliance Checklist

| Steering Doc | Requirement | How This Plan Addresses It |
|---|---|---|
| `structure.md` (frontend) | VSA — features import from `core/` and `shared/` only | New fields added within existing `onboarding` feature slice |
| `frontend-patterns.md` | `data-testid` on all interactive elements | Specified: `onboarding-preferred-schedule`, `onboarding-schedule-details`, `onboarding-schedule-note` |
| `frontend-patterns.md` | Native `fetch`, no Axios | Using existing `completeOnboarding()` in `onboardingApi.ts` — no new API function needed |
| `frontend-patterns.md` | Discriminated union return types | Existing API pattern preserved |
| `frontend-patterns.md` | `min-h-[44px]` touch targets | Specified for dropdown and text input |
| `frontend-testing.md` | Vitest + RTL + fast-check | Property-based tests for payload, RTL tests for rendering |
| `frontend-testing.md` | Tests in `__tests__/` subdirectories | All test files placed in `features/onboarding/__tests__/` |
| `structure.md` (backend) | Models in `models/`, services in `services/`, API in `api/v1/` | Customer model, onboarding service, onboarding API all updated in correct locations |
| `api-patterns.md` | Request/response Pydantic models, DomainLogger | New fields added to existing `CompleteOnboardingRequest` with proper validation |
| `code-standards.md` | Structured logging with LoggerMixin | Logging added in service layer for schedule updates |
| `code-standards.md` | Three-tier testing (unit/functional/integration) | All three tiers covered with specific test cases |
| `code-standards.md` | Ruff + MyPy + Pyright zero errors | Quality check phase included |
| `code-standards.md` | Type hints on all functions | New parameters fully typed |
| `tech.md` | Alembic migrations for schema changes | Migration step included |
| `vertical-slice-setup-guide.md` | Feature-specific changes within feature slice | No cross-feature imports added |
| `frontend-patterns.md` (platform) | TanStack Query + React Hook Form + Zod (admin) | Admin dashboard update uses existing mutation pattern |
| `frontend-patterns.md` (platform) | `data-testid` convention | `customer-preferred-schedule` specified |
| `.claude/skills/e2e-test/SKILL.md` | agent-browser E2E with screenshots, DB validation, responsive testing, report | Phase 9 follows full SKILL.md protocol: pre-flight, browser testing, DB validation, responsive viewports, error checks, report |
| `.claude/skills/e2e-test/STRIPE-CHECKOUT-AUTOMATION-GUIDE.md` | Stripe test card checkout → onboarding flow via agent-browser | Test 9.1.1 follows the guide step-by-step including accordion JS eval |
| `.claude/skills/e2e-test/RAILWAY-API-ACCESS-GUIDE.md` | JWT auth + REST API for DB validation (no direct psql) | Step 9.2 uses Railway API with token auth to verify `preferred_schedule` persisted |
| `scripts/e2e/test-customers.sh` pattern | Bash E2E scripts with PASS/FAIL counts, data-testid selectors with fallbacks, screenshot capture | Step 9.4 adds Step 7b following the exact same pattern as existing Step 7 |

---

## Files Modified (Summary)

### Platform Repo (`Grins_irrigation_platform`)

| File | Change |
|---|---|
| `migrations/versions/{next}_add_preferred_schedule.py` | **NEW** — Alembic migration |
| `models/customer.py` | Add 2 columns |
| `api/v1/onboarding.py` | Add 2 fields to request schema + validator |
| `services/onboarding_service.py` | Pass & persist new fields |
| `schemas/customer.py` | Add fields to response schema |
| `api/v1/customers.py` | Add fields to update schema (if editable) |
| `frontend/.../CustomerDetail.tsx` | Display preferred schedule |
| `frontend/.../types/index.ts` | Add fields to Customer type |
| `tests/unit/test_onboarding_preferred_schedule.py` | **NEW** — Unit tests |
| `tests/functional/test_onboarding_preferred_schedule.py` | **NEW** — Functional tests |
| `tests/integration/test_onboarding_preferred_schedule.py` | **NEW** — Integration tests |
| `scripts/e2e/test-customers.sh` | Add Step 7b for preferred schedule E2E |

### Frontend Repo (`Grins_irrigation`)

| File | Change |
|---|---|
| `features/onboarding/types/index.ts` | Add 2 fields to types |
| `features/onboarding/components/OnboardingPage.tsx` | Add dropdown + text input + note |
| `features/onboarding/__tests__/onboarding-page.test.tsx` | Add rendering tests |
| `features/onboarding/__tests__/form-submission-payload.property.test.ts` | Add payload tests |

### E2E Artifacts (generated during testing)

| Path | Description |
|---|---|
| `e2e-screenshots/preferred-schedule/*.png` | ~21 screenshots covering all E2E test scenarios |
| `e2e-screenshots/preferred-schedule/E2E-REPORT.md` | Optional detailed test report |
