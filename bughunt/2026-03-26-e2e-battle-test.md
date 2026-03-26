# E2E Battle Test Report — 2026-03-26

**Target:** Customer-facing frontend at `frontend-git-dev-kirilldr01s-projects.vercel.app`
**Backend:** `grins-dev-dev.up.railway.app` (dev Railway, Stripe test mode)
**Tester:** Claude (automated via agent-browser)
**Screenshots:** `e2e-screenshots/` (organized by category)

---

## Summary

**Tests executed:** 28
**Tests passed:** 24
**Bugs found:** 4 (2 HIGH, 1 MEDIUM, 1 LOW)
**Full E2E checkouts completed:** 3 (Professional $260, Premium $725, Winterization $85 with decline card)

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

## Successful Tests

### Checkout Flows

| # | Test | Result | Details |
|---|---|---|---|
| T01 | Professional Res ($260) full checkout | PASS | Modal → Stripe → onboarding → "You're All Set!" Customer `e2e-test@grins.dev` created |
| T02 | Premium Res ($725) full checkout | PASS | 3 zones + lake pump, SMS + email consent. Customer `premium-test@grins.dev` created, sms:true, email:true, pref:AFTERNOON |
| T03 | Stripe decline card (4000...0002) | PASS | "Your card was declined. Please try a different card." shown in red. User stays on checkout page |

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

### Responsive

| # | Test | Result | Details |
|---|---|---|---|
| T27 | Mobile (375×812) | PASS (with caveat) | Homepage: hamburger menu, stacked CTAs, sticky bottom bar. Service packages: single column. Modal: BUG-003 |
| T28 | Tablet (768×1024) | PASS | 2-column package grid, full nav bar, all readable |

---

## Tests Not Yet Performed

- [ ] Stripe insufficient funds card (4000000000009995) — error handling
- [ ] Onboarding — unchecking "Service address same as billing address" (manual address entry)
- [ ] Lead form — duplicate submission handling
- [ ] Lead form — invalid email/phone format validation
- [ ] Blog individual post pages
- [ ] Legal pages (Privacy Policy, Terms of Service, Accessibility)
- [ ] Google Maps integration on Service Area page (may need API key)
- [ ] "Manage Your Subscription" button on success page → Stripe Customer Portal
- [ ] Mobile lead form submission
- [ ] Performance / Lighthouse audit
