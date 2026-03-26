# Requirements Document — E2E Battle Test Bug Fixes

## Introduction

This spec addresses 12 bugs discovered during the 2026-03-26 E2E battle test of the customer-facing frontend (`frontend-git-dev-kirilldr01s-projects.vercel.app`) and backend (`grins-dev-dev.up.railway.app`). The bugs span two repos: `Grins_irrigation` (customer frontend) and `Grins_irrigation_platform` (backend + admin dashboard). Fixes are prioritized by severity (HIGH → MEDIUM → LOW) and grouped by blast radius to minimize cross-repo coordination.

**Source:** `bughunt/2026-03-26-e2e-battle-test.md`

## Glossary

- **PricingSection**: React component in `Grins_irrigation` that renders the surcharge text on service package cards
- **SurchargeCalculator**: Backend Python class and frontend TypeScript utility that compute zone, lake pump, and RPZ surcharges
- **SubscriptionConfirmModal**: React component rendering the pre-checkout consent modal with phone, zones, add-ons, and disclosures
- **LeadForm**: React component rendering the "Get Your Free Quote" lead capture form on the homepage and modal
- **OnboardingPage**: React component rendering the post-checkout property details form

## Requirements

### Requirement 1: Fix Surcharge Display Text on Package Cards (BUG-001, HIGH)

**User Story:** As a customer browsing service packages, I want the surcharge prices shown on the package cards to match what I'll actually be charged at checkout, so that I'm not misled about pricing.

#### Acceptance Criteria

1. THE PricingSection component SHALL display zone surcharge rates matching the SurchargeCalculator: $8.00/zone (residential), $11.00/zone (commercial) for all tier types
2. THE PricingSection component SHALL display lake pump surcharge matching the SurchargeCalculator: $125 (residential), $150 (commercial) for all tier types
3. THE PricingSection component SHALL display RPZ/backflow surcharge matching the SurchargeCalculator: $110 (standard tiers), $55 (winterization-only tiers)
4. THE PricingSection component SHALL use "RPZ/backflow removal" label for winterization-only tiers and "RPZ/backflow connection" for standard tiers (already correct)
5. THE surcharge values in PricingSection SHALL be derived from a single source of truth (either imported constants or the `calculateSurcharge` utility) rather than hardcoded strings
6. THE backend test comments in `test_checkout_onboarding_service.py` SHALL be updated to reflect the correct surcharge amounts ($125 for lake pump, $110 for RPZ)

#### Verification

- agent-browser: Open each of the 8 package modals, compare card text to modal calculation — all must match
- Unit test: Property test that PricingSection surcharge text matches `calculateSurcharge` output for all tier/type combinations

---

### Requirement 2: Validate Zone Count ≥ 1 (BUG-002, HIGH)

**User Story:** As a system, I want to reject subscriptions with zero irrigation zones, so that nonsensical orders don't enter the pipeline.

#### Acceptance Criteria

1. THE SubscriptionConfirmModal SHALL enforce `zone_count >= 1` by disabling the Confirm button when zones < 1
2. THE SubscriptionConfirmModal SHALL prevent typing values below 1 into the zone input (clamp on change, not just on blur)
3. THE backend `POST /api/v1/onboarding/pre-checkout-consent` endpoint SHALL reject requests with `zone_count < 1` and return HTTP 422 with a clear error message
4. THE backend `checkout_service.create_checkout_session` SHALL validate `zone_count >= 1` before creating a Stripe Checkout Session

#### Verification

- agent-browser: Set zones to 0 or negative → Confirm button stays disabled, no Stripe redirect
- Backend test: `POST /pre-checkout-consent` with `zone_count=0` returns 422

---

### Requirement 3: Render Terms Checkbox in Lead Form (BUG-005, HIGH)

**User Story:** As a customer submitting a lead form, I want to explicitly accept the Terms of Service before my information is submitted, so that the business has documented consent.

#### Acceptance Criteria

1. THE LeadForm component SHALL render the `TermsCheckbox` component (already imported but unused) before the submit button
2. THE LeadForm SHALL require `termsAccepted === true` before enabling the submit button
3. THE TermsCheckbox label SHALL link to the `/terms-of-service` page
4. THE `buildLeadPayload` function SHALL include `terms_accepted: true` in the API payload when the checkbox is checked
5. THE consent metadata capture (`captureConsentMetadata`) SHALL run when `termsAccepted` is true, regardless of `smsConsent` state

#### Verification

- agent-browser: Submit button disabled until terms checked; success after checking
- Unit test: `buildLeadPayload` includes `terms_accepted: true` when checkbox checked

---

### Requirement 4: Fix Mobile Sticky Bar Overlap on Modal (BUG-003, MEDIUM)

**User Story:** As a mobile user, I want to see and tap the Confirm/Cancel buttons in the checkout modal, so that I can complete my subscription.

#### Acceptance Criteria

1. WHEN the SubscriptionConfirmModal is open on mobile viewports (< 768px), the sticky bottom bar ("Call Now" / "Get Free Quote") SHALL be hidden
2. THE modal Confirm and Cancel buttons SHALL be fully visible and tappable on a 375×812 viewport without manual scrolling
3. WHEN the modal is closed, the sticky bottom bar SHALL reappear

#### Verification

- agent-browser: Set viewport 375×812, open modal → Confirm/Cancel buttons visible, no overlap with sticky bar

---

### Requirement 5: Add Error Handling to API JSON Parsing (BUG-006, MEDIUM)

**User Story:** As a customer, I want graceful error messages when the API returns unexpected responses, so that the app doesn't crash.

#### Acceptance Criteria

1. ALL `.json()` calls in `checkoutApi.ts`, `onboardingApi.ts`, and `chatbotApi.ts` SHALL be wrapped in try/catch
2. WHEN JSON parsing fails, the function SHALL return a typed error result (e.g., `{ ok: false, error: 'server' }`) rather than throwing
3. THE chatbot `sendAiChat` function SHALL return a fallback message ("Sorry, I'm having trouble right now.") when JSON parsing fails or `data.response` is undefined

#### Verification

- Unit test: Mock `fetch` returning non-JSON body → functions return error result, no unhandled exceptions

---

### Requirement 6: Add Email Validation to Lead Form (BUG-007, MEDIUM)

**User Story:** As a customer, I want to see an error if I enter an invalid email, so that I can fix it before submitting.

#### Acceptance Criteria

1. THE LeadForm `validate()` function SHALL check email format using a standard regex when the email field is non-empty
2. WHEN email validation fails, THE form SHALL display an inline error message "Please enter a valid email address"
3. THE error SHALL appear as a `role="alert"` element below the email input, consistent with existing phone/zip validation styling

#### Verification

- agent-browser: Enter "not-an-email" → inline error appears, submit button disabled
- Unit test: `validate({ email: 'bad' })` returns error for email field

---

### Requirement 7: Validate Onboarding Service Address (BUG-008, MEDIUM)

**User Story:** As a system, I want to ensure customers provide a complete service address when it differs from billing, so that the field crew has the correct location.

#### Acceptance Criteria

1. WHEN the "Service address same as billing address" checkbox is unchecked, THE OnboardingPage SHALL validate that street, city, state, and zip are non-empty before allowing submission
2. WHEN any required service address field is empty, THE OnboardingPage SHALL display inline validation errors on the empty fields
3. THE Complete Onboarding button SHALL be disabled until all required service address fields are filled (or the checkbox is re-checked)

#### Verification

- agent-browser: Uncheck same-as-billing → leave fields empty → Complete Onboarding disabled → fill fields → enabled
- Unit test: `onSubmit` with empty service address fields does not call API

---

### Requirement 8: Use Environment Variable for Customer Portal URL (BUG-011, MEDIUM)

**User Story:** As a developer, I want the Customer Portal URL to be environment-aware, so that dev and production use the correct Stripe portal.

#### Acceptance Criteria

1. THE frontend `config.ts` SHALL read `customerPortalUrl` from `import.meta.env.VITE_STRIPE_CUSTOMER_PORTAL_URL` instead of a hardcoded production URL
2. IF the environment variable is not set, THE frontend SHALL fall back to the onboarding page's `stripe_customer_portal_url` from the API (already dynamic) and hide the footer Customer Portal link
3. THE `VITE_STRIPE_CUSTOMER_PORTAL_URL` SHALL be added to Vercel Preview (dev branch) pointing to the test Stripe portal, and Production pointing to the live Stripe portal

#### Verification

- agent-browser: Footer "Customer Portal" link href contains `test_` on dev frontend
- Verify Vercel env vars set for both environments

---

### Requirement 9: Add Missing Vercel Environment Variables (BUG-004, LOW)

**User Story:** As a developer, I want all environment variables properly set for both dev and production, so that all features work.

#### Acceptance Criteria

1. THE Vercel frontend project SHALL have `VITE_GOOGLE_MAPS_API_KEY` set for Preview and Production environments
2. THE Vercel frontend project SHALL have `VITE_GA4_MEASUREMENT_ID` and `VITE_GTM_CONTAINER_ID` set for Production environment (optional for Preview)
3. THE Vercel frontend project SHALL have `VITE_STRIPE_CUSTOMER_PORTAL_URL` set per Requirement 8

#### Verification

- `vercel env ls` shows all variables set
- agent-browser: Service Area page loads Google Maps on dev

---

### Requirement 10: Externalize CSP Domains (BUG-009, LOW)

**User Story:** As a developer, I want the Content Security Policy to work across environments without hardcoded URLs.

#### Acceptance Criteria

1. THE `connect-src` directive in `index.html` SHALL include `import.meta.env.VITE_API_URL` domain dynamically (via build-time injection or a meta tag)
2. IF dynamic injection is too complex, THE CSP SHALL use a wildcard pattern `https://*.up.railway.app` to cover both dev and production Railway domains

#### Verification

- No CSP violations in browser console when making API calls on dev

---

### Requirement 11: Add Loading Spinner to Route Suspense (BUG-010, LOW)

**User Story:** As a customer navigating between pages, I want a loading indicator instead of a blank screen while pages load.

#### Acceptance Criteria

1. THE `router.tsx` Suspense fallback SHALL render a centered spinner or skeleton component instead of an empty div
2. THE spinner SHALL be visually consistent with the site's design (use existing brand colors)

#### Verification

- Visual: Navigate between lazy-loaded routes — spinner appears briefly during chunk download

---

### Requirement 12: Create Accessibility Page or Remove Footer Link (BUG-012, LOW)

**User Story:** As a customer, I want the Accessibility link in the footer to work, so that I can learn about the site's accessibility features.

#### Acceptance Criteria

1. EITHER the frontend SHALL add an `/accessibility` route with a basic accessibility statement page
2. OR the footer SHALL remove the Accessibility link until the page is ready
3. IF a page is created, it SHALL include at minimum: WCAG 2.1 AA compliance commitment, contact information for accessibility issues, and a last-updated date

#### Verification

- agent-browser: Click "Accessibility" in footer → page renders (not 404)
