# Bug Fix Plan — E2E Battle Test (2026-03-26)

## Overview

Fix 12 bugs found during battle testing. Grouped into 3 phases by repo/blast radius. Each phase can be committed and deployed independently.

**Source:** `bughunt/2026-03-26-e2e-battle-test.md`

## Phase 1: Frontend Fixes (Grins_irrigation repo) — HIGH + MEDIUM

These all touch the customer-facing frontend. Do in one branch, one PR.

- [ ] 1. Fix surcharge display text (BUG-001, HIGH)
  - Edit `frontend/src/shared/components/sections/PricingSection.tsx` lines 16-20
  - Replace hardcoded values with rates from `surcharge.ts`: zone $8/$11, lake pump $125/$150, RPZ $110/$55
  - Import constants or derive from `calculateSurcharge` so there's a single source of truth
  - _Files: PricingSection.tsx_

- [ ] 2. Validate zone count ≥ 1 in modal (BUG-002, HIGH — frontend half)
  - Edit `frontend/src/features/service-packages/components/SubscriptionConfirmModal.tsx`
  - Clamp zone input `onChange` to `Math.max(1, value)` instead of only on blur
  - Disable Confirm button when `zoneCount < 1`
  - _Files: SubscriptionConfirmModal.tsx_

- [ ] 3. Render TermsCheckbox in lead form (BUG-005, HIGH)
  - Edit `frontend/src/features/lead-form/components/LeadForm.tsx`
  - Add `<TermsCheckbox>` to the JSX (already imported at line 8, never rendered)
  - Make `termsAccepted` required for submit button to enable
  - Update consent metadata capture to fire on `termsAccepted || smsConsent`
  - _Files: LeadForm.tsx, possibly leadApi.ts line 102_

- [ ] 4. Hide mobile sticky bar when modal is open (BUG-003, MEDIUM)
  - Edit the sticky bar component (likely in `frontend/src/shared/components/layout/`)
  - Add a CSS class or React context that hides the bar when any modal is open
  - Simplest: `z-index` fix or conditional render based on modal state
  - _Files: Layout component, possibly MobileBottomBar or similar_

- [ ] 5. Wrap API .json() calls in try/catch (BUG-006, MEDIUM)
  - Edit `checkoutApi.ts`, `onboardingApi.ts`, `chatbotApi.ts`
  - Wrap all `.json()` calls in try/catch, return `{ ok: false, error: 'server' }` on failure
  - Add null check for `data.response` in chatbotApi
  - _Files: 3 API files_

- [ ] 6. Add email validation to lead form (BUG-007, MEDIUM)
  - Edit `frontend/src/features/lead-form/components/LeadForm.tsx` validate() function (line ~42-52)
  - Add email format regex check when email is non-empty
  - Show inline error below email field matching existing error styling
  - _Files: LeadForm.tsx_

- [ ] 7. Validate service address on onboarding (BUG-008, MEDIUM)
  - Edit `frontend/src/features/onboarding/components/OnboardingPage.tsx`
  - When same-as-billing unchecked, require street/city/state/zip non-empty
  - Disable Complete Onboarding button until fields valid
  - _Files: OnboardingPage.tsx_

- [ ] 8. Replace hardcoded Customer Portal URL (BUG-011, MEDIUM)
  - Edit `frontend/src/core/config.ts` line 24
  - Replace hardcoded production URL with `import.meta.env.VITE_STRIPE_CUSTOMER_PORTAL_URL || ''`
  - In Footer.tsx, hide the Customer Portal link when URL is empty
  - _Files: config.ts, Footer.tsx_

- [ ] 9. Fix CSP connect-src (BUG-009, LOW)
  - Edit `frontend/index.html` CSP `connect-src`
  - Replace hardcoded Railway URLs with `https://*.up.railway.app` wildcard
  - _Files: index.html_

- [ ] 10. Add loading spinner to Suspense fallback (BUG-010, LOW)
  - Edit `frontend/src/core/router.tsx` line 42
  - Replace empty div with a centered spinner using existing brand colors
  - _Files: router.tsx_

- [ ] 11. Create accessibility page or remove link (BUG-012, LOW)
  - Option A: Add `/accessibility` route with basic accessibility statement
  - Option B: Remove the Accessibility link from Footer.tsx
  - Recommend Option A for compliance optics
  - _Files: router.tsx + new AccessibilityPage.tsx, OR Footer.tsx_

## Phase 2: Backend Validation Fix (Grins_irrigation_platform repo)

- [ ] 12. Validate zone_count ≥ 1 on backend (BUG-002, HIGH — backend half)
  - Edit `src/grins_platform/services/checkout_service.py` or the pre-checkout-consent endpoint
  - Add validation: if `zone_count < 1`, return HTTP 422
  - Update backend test comments for correct surcharge amounts (BUG-001 related)
  - _Files: checkout_service.py or agreements/routes.py, test_checkout_onboarding_service.py_

- [ ] 13. Fix backend test comments (BUG-001 related)
  - Edit `test_checkout_onboarding_service.py` lines ~681 and ~780
  - Update comments from "$175" to "$125" and "$50" to "$110"
  - _Files: test_checkout_onboarding_service.py_

## Phase 3: Vercel Environment Configuration

- [ ] 14. Add missing env vars to frontend Vercel project (BUG-004 + BUG-011)
  - `VITE_GOOGLE_MAPS_API_KEY` — Preview + Production (copy from admin dashboard project)
  - `VITE_STRIPE_CUSTOMER_PORTAL_URL` — Preview: `https://billing.stripe.com/p/login/test_6oU8wR0zu8QUcQ4amueQM00`, Production: `https://billing.stripe.com/p/login/00waEXaaqack8zGa7N5Ne00`
  - `VITE_GA4_MEASUREMENT_ID` — Production only (when ready)
  - `VITE_GTM_CONTAINER_ID` — Production only (when ready)
  - Run via `vercel env add` CLI

## Execution Order

```
Phase 1 (items 1-11) ← All in Grins_irrigation repo, one branch
    ↓ push to dev → Vercel auto-deploys
Phase 2 (items 12-13) ← Grins_irrigation_platform repo
    ↓ push to dev → Railway auto-deploys
Phase 3 (item 14)    ← Vercel CLI, no code changes
    ↓ redeploy frontend to pick up new env vars
    ↓
Verification: Re-run E2E battle test on all 12 bugs
```

## Estimated Scope

- **Phase 1:** ~10 files modified in Grins_irrigation repo
- **Phase 2:** ~2-3 files modified in Grins_irrigation_platform repo
- **Phase 3:** CLI commands only, no code
- **Total:** ~13 file changes across 2 repos
