# E2E Battle Test Report — 2026-03-26

**Target:** Customer-facing frontend at `frontend-git-dev-kirilldr01s-projects.vercel.app`
**Backend:** `grins-dev-dev.up.railway.app` (dev Railway, Stripe test mode)
**Tester:** Claude (automated via agent-browser)
**Screenshots:** `e2e-screenshots/` (organized by category)

---

## Summary

**Tests executed:** 52 (browser) + code analysis
**Tests passed:** 45
**Bugs found:** 12 total
- Browser-tested: 6 (2 HIGH, 2 MEDIUM, 2 LOW)
- Code analysis: 6 (1 HIGH, 3 MEDIUM, 2 LOW)
**Full E2E checkouts completed:** 5 (Professional $260, Premium $725, Winterization $85 decline, Winterization $85 address test, Commercial Essential $235 with Mastercard)
**Stripe error cards tested:** 2 (decline 4000...0002, insufficient funds 4000...9995)
**Test card types used:** Visa (4242...), Mastercard (5555...4444), Decline (4000...0002), NSF (4000...9995)

---

## Bugs Found

### BUG-001: Surcharge Price Mismatch — Package Cards vs Checkout Modal (HIGH)

**Location:** `Grins_irrigation/frontend/src/shared/components/sections/PricingSection.tsx` lines 16-20

**Description:** The pricing text on package cards shows outdated surcharge amounts that don't match the checkout modal calculation (powered by `surcharge.ts` and backend `surcharge_calculator.py`). ALL surcharge categories are wrong.

**Full mismatch table:**

| Surcharge | Card Text (displayed) | Calculator (charged) | Delta |
|---|---|---|---|
| Zone rate (res standard) | $7.50/zone | $8.00/zone | +$0.50/zone |
| Zone rate (res winterization) | $5.00/zone | $8.00/zone | +$3.00/zone |
| Zone rate (com standard) | $10.00/zone | $11.00/zone | +$1.00/zone |
| Zone rate (com winterization) | $10.00/zone | $11.00/zone | +$1.00/zone |
| Lake pump (res standard) | $175 | $125 | -$50 |
| Lake pump (res winterization) | $75 | $125 | +$50 |
| Lake pump (com standard) | $200 | $150 | -$50 |
| Lake pump (com winterization) | $100 | $150 | +$50 |
| RPZ/backflow (standard) | $50 | $110 | +$60 |
| RPZ/backflow (winterization) | $50 | $55 | +$5 |

**Buggy display text:** `PricingSection.tsx` lines 16-20:
```tsx
const zoneRate = isWint ? (isCom ? '$10' : '$5') : isCom ? '$10' : '$7.50';
const lakePump = isWint ? (isCom ? '$100' : '$75') : isCom ? '$200' : '$175';
return `...Lake pump add-on: ${lakePump}. ${rpzLabel}: $50.`;
```

**Source of truth (correct):** `surcharge.ts` lines 22-35, backend `surcharge_calculator.py` lines 42-46.

**Also affected:** Backend test comments reference old prices:
- `test_checkout_onboarding_service.py` line 681: says "$175" (should be $125)
- `test_checkout_onboarding_service.py` line 780: says "$50" (should be $110)

**Severity:** HIGH — pricing discrepancy shown to customers

---

### BUG-002: Zero Zone Count Accepted — Creates Stripe Checkout Session (HIGH)

**Location:** Frontend `SubscriptionConfirmModal.tsx` + Backend checkout endpoint

**Description:** The zone count spinbutton has `min="1"` in HTML but accepts `0` via keyboard input. Neither the frontend nor the backend validates that `zone_count >= 1`. Submitting with 0 zones creates a valid Stripe Checkout session. An irrigation service with 0 zones is semantically invalid.

**Reproduction:**
1. Open any Subscribe modal
2. Change "Number of irrigation zones" from 1 to 0 (type, don't use spinner arrows)
3. Fill phone, check SMS consent
4. Click "Confirm Subscription" — succeeds and redirects to Stripe

**Screenshot:** `e2e-screenshots/edge-cases/01-zero-zones.png`, `02-zero-zones-submit.png`

**Severity:** HIGH — allows nonsensical subscription, potential customer confusion

---

### BUG-003: Mobile Sticky Bar Overlaps Modal Confirm/Cancel Buttons (MEDIUM)

**Location:** Frontend — mobile viewport (375x812)

**Description:** On mobile, the "Call Now | Get Free Quote" sticky bottom bar overlaps the Confirm Subscription and Cancel buttons in the checkout modal. The modal backdrop is scrollable (`overflow: auto`), but when scrolled to the bottom, the Confirm/Cancel buttons are hidden behind the sticky bar.

**Details:**
- Modal content height: 936px
- Viewport height: 812px
- Confirm button y-position: 884px (72px below viewport)
- After scrolling backdrop: buttons visible but covered by sticky bar at y=780

**Fix options:**
1. Add `pb-16` padding to modal when on mobile
2. Hide sticky bar when modal is open
3. Set `max-height: calc(100vh - 80px)` on modal with `overflow-y: auto`

**Screenshot:** `e2e-screenshots/responsive/05-mobile-modal-bottom.png`, `06-mobile-modal-scrolled.png`

**Severity:** MEDIUM — mobile users may be unable to confirm subscription

---

### BUG-004: Missing Environment Variables for Production Readiness (LOW)

**Location:** Vercel frontend environment configuration

**Console warnings on every page load:**
```
[warning] VITE_STRIPE_PUBLISHABLE_KEY is not set
[warning] VITE_GA4_MEASUREMENT_ID is not set
[warning] VITE_GTM_CONTAINER_ID is not set
```

**Impact:**
- `VITE_STRIPE_PUBLISHABLE_KEY` — Low impact (checkout uses hosted Stripe page, not client-side Elements)
- `GA4` + `GTM` — No analytics tracking on dev (acceptable), but must be set for production

**Severity:** LOW for dev, must be addressed before production deploy

---

### BUG-005: Missing Terms Acceptance Checkbox in Lead Form (HIGH — code analysis)

**Location:** `Grins_irrigation/frontend/src/features/lead-form/components/LeadForm.tsx` lines 71, 270-280

**Description:** The `termsAccepted` field exists in form state (initialized `false` at line 71) and is sent in the payload, but the `TermsCheckbox` component is imported but **never rendered** in the form JSX. Only `SmsConsentCheckbox` and `EmailMarketingCheckbox` are rendered. Terms acceptance is always submitted as `false`.

**Impact:** Terms acceptance requirement cannot be enforced. Compliance gap — users never explicitly accept terms before lead submission.

**Severity:** HIGH — compliance/legal risk

---

### BUG-006: Unhandled JSON Parse Errors in API Calls (MEDIUM — code analysis)

**Location:**
- `checkoutApi.ts` lines 41, 57
- `onboardingApi.ts` lines 24, 44
- `chatbotApi.ts` line 11

**Description:** `.json()` calls on API responses are not wrapped in try/catch. If the server returns malformed JSON, an HTML error page, or a network interruption occurs during parsing, the unhandled rejection will crash the component.

**Example (chatbotApi.ts):**
```typescript
const data = await response.json();  // Can throw if not valid JSON
return data.response;                // Also undefined if field missing
```

**Severity:** MEDIUM — causes unhandled promise rejections on API errors

---

### BUG-007: Missing Email Validation in Lead Form (MEDIUM — code analysis)

**Location:** `Grins_irrigation/frontend/src/features/lead-form/components/LeadForm.tsx` lines 42-52

**Description:** The `validate()` function checks for name, phone format, and zip code, but has no email format validation. The input uses `type="email"` for browser-level hints, but the form's custom validation logic doesn't verify email format. Invalid emails (e.g., "not-an-email") can be submitted.

**Severity:** MEDIUM — junk emails in lead database

---

### BUG-008: Onboarding Service Address Has No Validation (MEDIUM — code analysis)

**Location:** `Grins_irrigation/frontend/src/features/onboarding/components/OnboardingPage.tsx` lines 185-209

**Description:** When user unchecks "Service address same as billing address", the address fields appear with `aria-required="true"` but **no form validation** enforces them. The onSubmit handler will send empty/undefined service_address fields to the backend.

**Severity:** MEDIUM — incomplete property data for service scheduling

---

### BUG-009: Hardcoded API Domains in CSP Header (LOW — code analysis)

**Location:** `Grins_irrigation/frontend/index.html` line 6

**Description:** The `Content-Security-Policy` `connect-src` directive hardcodes both Railway domains:
```
https://grinsirrigationplatform-production.up.railway.app
https://grins-dev-dev.up.railway.app
```
If API domains change, browser will block API requests with CSP violations. Should be environment-based.

**Severity:** LOW — works currently, fragile for domain changes

---

### BUG-010: Invisible Router Loading Fallback (LOW — code analysis)

**Location:** `Grins_irrigation/frontend/src/core/router.tsx` line 42

**Description:** The React Suspense fallback is `<div className="flex-1" />` — an invisible empty div. Users see a blank page while lazy-loaded route chunks download. No loading spinner or skeleton.

**Severity:** LOW — poor UX during page transitions, especially on slow connections

---

### BUG-011: Footer Customer Portal Links to Production Stripe (MEDIUM)

**Location:** `Grins_irrigation/frontend/src/core/config.ts` line 24, used in `Footer.tsx` line 116

**Description:** The footer "Customer Portal" link is hardcoded to the **production** Stripe Customer Portal URL:
```
https://billing.stripe.com/p/login/00waEXaaqack8zGa7N5Ne00  (production — no "test_" prefix)
```
While the onboarding success page correctly uses the dynamic `stripe_customer_portal_url` from the backend API (which is environment-aware):
```
https://billing.stripe.com/p/login/test_6oU8wR0zu8QUcQ4amueQM00  (test mode)
```

**Impact:** On dev, clicking "Customer Portal" in the footer takes users to production Stripe where their test subscriptions don't exist. On production, it would work correctly (by coincidence).

**Fix:** Replace hardcoded URL in `config.ts` with `VITE_STRIPE_CUSTOMER_PORTAL_URL` environment variable, or fetch from backend API.

**Severity:** MEDIUM — wrong environment in dev, data leak risk if test users land on production portal

---

### BUG-012: `/accessibility` Page Linked From Footer Is 404 (LOW)

**Location:** Footer links to `/accessibility`, but no route exists in the React router

**Description:** The footer contains an "Accessibility" link that navigates to `/accessibility`, which renders the "Page Not Found" 404 page. Either the route needs to be added or the footer link removed.

**Screenshot:** `e2e-screenshots/navigation/15-accessibility.png`

**Severity:** LOW — missing page, not critical for launch but bad for accessibility compliance perception

---

## Successful Tests

### Checkout Flows

| # | Test | Result | Details |
|---|---|---|---|
| T01 | Professional Res ($260) full checkout | PASS | Modal → Stripe → onboarding → "You're All Set!" Customer `e2e-test@grins.dev` created |
| T02 | Premium Res ($725) full checkout | PASS | 3 zones + lake pump, SMS + email consent. Customer `premium-test@grins.dev` created, sms:true, email:true, pref:AFTERNOON |
| T03 | Stripe decline card (4000...0002) | PASS | "Your card was declined. Please try a different card." shown in red. User stays on checkout page |
| T29 | Stripe insufficient funds (4000...9995) | PASS | "Your card has insufficient funds. Try a different card." shown in red. User stays on checkout page |
| T47 | Commercial Essential ($235) full checkout | PASS | Mastercard 5555..4444, 8 zones, SMS+email consent. Stripe shows "Commercial Essential Package". Customer `commercial-test@grins.dev` created |

### Package Modal Pricing (All 8 Tiers)

| # | Package | Base | Add-ons Tested | Total Verified | Result |
|---|---|---|---|---|---|
| T04 | Essential Res | $175 | 5 zones + LP + RPZ | $410 ($175+$125+$110) | PASS (math correct, card text wrong - BUG-001) |
| T05 | Essential Res | $175 | 12 zones + LP + RPZ | $434 ($175+$24+$125+$110) | PASS (zone surcharge: 3×$8=$24) |
| T06 | Professional Res | $260 | base only | $260 | PASS |
| T07 | Premium Res | $725 | base only | $725 | PASS |
| T08 | Winterization Res | $85 | LP + RPZ removal | $265 ($85+$125+$55) | PASS, RPZ label correctly says "Removal" |
| T09 | Essential Com | $235 | 15 zones + LP + RPZ | $561 ($235+$66+$150+$110) | PASS (zone: 6×$11=$66, LP=$150 commercial) |
| T10 | Professional Com | $390 | base only | $390 | PASS |
| T11 | Premium Com | $880 | base only | $880 | PASS |
| T12 | Winterization Com | $105 | LP + RPZ removal | $310 ($105+$150+$55) | PASS |

### Lead Form

| # | Test | Result | Details |
|---|---|---|---|
| T13 | Valid submission | PASS | Name, phone, email, zip, service, customer type, property type, referral → "Thank You!" success message |
| T14 | Missing required fields | PASS | Without customer type + property type: validation errors shown as red text (`role="alert"`) |
| T15 | Button disabled without phone | PASS | Confirm button disabled until phone entered |
| T34 | Invalid email rejected | PASS | "not-a-valid-email" → backend returns error, frontend shows "Please check your information" |
| T35 | Duplicate lead handled | PASS | Same email twice → "We already have your information — a team member will be in touch shortly." |
| T36 | Existing customer radio | PASS | Form renders same fields for existing customer flow |

### Navigation & Pages

| # | Test | Result | Details |
|---|---|---|---|
| T16 | Homepage | PASS | Hero, lead form, trust badges, CTAs all render |
| T17 | Service Packages | PASS | 8 packages in 2 sections (residential/commercial) |
| T18 | About page | PASS | Content loads correctly |
| T19 | Service Area | PASS | Community listings render |
| T20 | Blog | PASS | Blog listing page loads |
| T21 | Contact | PASS | Form + contact info side by side |
| T22 | 404 page | PASS | "Page Not Found" with "Return to Home" link |
| T23 | Services dropdown | PASS | Mega dropdown shows Irrigation, Landscaping, Maintenance categories |
| T24 | Service sub-pages | PASS | `/services/residential-irrigation` etc. all render with content |
| T25 | "Get Your Free Quote" CTA | PASS | Opens modal with lead form |
| T26 | Chatbot | PASS | Opens, accepts messages, responds with lead capture flow |
| T30 | Privacy Policy page | PASS | Renders with breadcrumbs, data inventory, proper legal content |
| T31 | Terms of Service page | PASS | Renders correctly |
| T32 | Blog post page | PASS | "How Much Does a Sprinkler System Cost?" — title, author, date, TOC render |
| T33 | "Get Your Free Quote" CTA | PASS | Opens modal with full lead form |
| T37 | "Get Your Exact Quote" CTAs | PASS | Multiple CTAs on homepage all open same quote modal |
| T38 | Privacy Policy page | PASS | Full legal content with data inventory, breadcrumbs |
| T39 | Terms of Service page | PASS | Renders correctly with all sections |
| T40 | Sitemap page | PASS | Renders with page listing |
| T41 | Accessibility page | FAIL | 404 — route not defined (BUG-012) |
| T42 | Blog post detail | PASS | "Sprinkler System Cost" post with title, author, date, TOC |
| T43 | All 9 service sub-pages | PASS | residential-irrigation, luxury-irrigation, residential-landscaping, luxury-landscaping, commercial, commercial-grounds, smart-irrigation, irrigation-repair, seasonal-maintenance — all render with unique H1s |
| T44 | Manage Your Subscription link | PASS | Opens Stripe Customer Portal (test mode) in new tab |
| T45 | Footer Customer Portal link | FAIL | Points to production Stripe URL, not test (BUG-011) |
| T46 | Onboarding — empty service address | FAIL | Submits with empty street/city/state/zip, no validation (BUG-008 confirmed) |
| T48 | Back button from Stripe | PASS | Returns to Service Packages page cleanly, no broken state |
| T49 | "Design Consultation" CTA | PASS | Opens same quote modal as other CTAs |
| T50 | Homepage full scroll-through | PASS | All sections render: hero, pain points, process steps, services grid, trust signals, reviews (5-star/122), FAQ, footer |
| T51 | Mobile sticky "Get Free Quote" | PASS | Opens lead form modal on mobile |
| T52 | Doubled accessible names in modal | OBSERVATION | Modal labels read twice ("Full Name Full Name") — caused by duplicate form instances (modal + background page) |

### Responsive

| # | Test | Result | Details |
|---|---|---|---|
| T27 | Mobile (375×812) | PASS (with caveat) | Homepage: hamburger menu, stacked CTAs, sticky bottom bar. Service packages: single column. Modal: BUG-003 |
| T28 | Tablet (768×1024) | PASS | 2-column package grid, full nav bar, all readable |

---

## Tests Not Yet Performed

- [ ] Google Maps integration on Service Area page (may need API key)
- [ ] Mobile lead form submission
- [ ] Mobile checkout full flow
- [ ] Performance / Lighthouse audit
- [x] ~~Commercial Essential full checkout~~ (PASS - T47, Mastercard)
- [ ] Remaining 3 commercial packages full checkout
- [ ] Onboarding with filled service address (non-empty, valid data)
- [ ] Back button behavior during checkout flow
- [ ] Session timeout / expired checkout session handling
- [ ] Multiple rapid form submissions (double-click prevention)
