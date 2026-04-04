# Implementation Tasks

## Task 1: Debounce Customer Search Input
- [ ] 1.1 Replace inline search input in `CustomerList.tsx` with the existing `CustomerSearch` component, passing `onSearch` callback that updates `searchQuery` state
- [ ] 1.2 Add `useEffect` to reset `params.page` to 1 when `searchQuery` changes (debounced value)
- [ ] 1.3 Write/update `CustomerList.test.tsx` to verify debounce integration and pagination reset on search change

## Task 2: Fix Subscription Management Email Flow
- [ ] 2.1 Add `SubscriptionManageRequest` schema in `src/grins_platform/schemas/checkout.py` with email field
- [ ] 2.2 Add `create_portal_session(email)` method to `CheckoutService` that looks up Stripe customer by email and creates a Stripe billing portal session URL
- [ ] 2.3 Add `POST /api/v1/checkout/manage-subscription` endpoint that accepts email, calls `create_portal_session`, and sends login email via `EmailService`
- [ ] 2.4 Add subscription management email template with portal session link and instructions
- [ ] 2.5 Update frontend subscription management UI to show confirmation message after email sent, error for unknown email, and "Resend Email" button
- [ ] 2.6 Write unit tests for the `create_portal_session` method and the manage-subscription endpoint

## Task 3: Extend Authentication Session Duration
- [ ] 3.1 Update `ACCESS_TOKEN_EXPIRE_MINUTES` from 15 to 60 in `src/grins_platform/services/auth_service.py`
- [ ] 3.2 Update `REFRESH_TOKEN_EXPIRE_DAYS` from 7 to 30 in `src/grins_platform/services/auth_service.py`
- [ ] 3.3 Update cookie `max-age` values in `src/grins_platform/api/v1/auth.py` to match new token expiry (3600s for access, 2592000s for refresh)
- [ ] 3.4 Update existing auth unit tests to reflect new expiry values

## Task 4: Persist Authentication Across Page Refresh
- [ ] 4.1 Verify `ProtectedRoute.tsx` shows a loading spinner while `isLoading` is true instead of redirecting to login; fix if needed
- [ ] 4.2 Verify `AuthProvider.tsx` `restoreSession` correctly handles both success and failure cases; fix if needed
- [ ] 4.3 Write/update `ProtectedRoute.test.tsx` to verify loading state is shown during session restoration

## Task 5: Fix Lead Deletion
- [ ] 5.1 Verify the `DELETE /api/v1/leads/{lead_id}` endpoint works correctly; fix any issues
- [ ] 5.2 Add/fix `useDeleteLead` mutation hook in `frontend/src/features/leads/hooks/` that calls the DELETE endpoint and invalidates the leads query on success
- [ ] 5.3 Add a confirmation dialog (using existing Dialog component) to `LeadDetail.tsx` before executing deletion
- [ ] 5.4 Add error handling with toast notification and retry option for failed deletions
- [ ] 5.5 Write unit tests for lead deletion flow (confirmation dialog, success removal, error handling)

## Task 6: Fix Lead-to-Customer Conversion
- [ ] 6.1 Fix `lead_service.py` `convert_lead` method: change `data.job_description or default_description` to `data.job_description if data.job_description is not None else default_description` to respect user-provided empty-ish descriptions
- [ ] 6.2 Fix `ConvertLeadDialog.tsx`: ensure job description field is hidden and `job_description` is not sent when `createJob` toggle is off (verify current implementation)
- [ ] 6.3 Ensure the `useConvertLead` mutation hook invalidates the leads list query on success so the converted lead is removed from the active list
- [ ] 6.4 Add error handling for already-converted leads (display toast with specific message)
- [ ] 6.5 Write/update `ConvertLeadDialog.test.tsx` to verify job description behavior and list invalidation

## Task 7: Add Manual Lead Creation
- [ ] 7.1 Add `ManualLeadCreate` schema in `src/grins_platform/schemas/leads.py` with required name/phone and optional email, address, city, state, zip_code, situation, notes
- [ ] 7.2 Add `create_manual_lead` method to `LeadService` that creates a lead with `lead_source="manual"`
- [ ] 7.3 Add `POST /api/v1/leads/manual` endpoint in `src/grins_platform/api/v1/leads.py`
- [ ] 7.4 Create `CreateLeadDialog.tsx` component with React Hook Form + Zod validation (name and phone required)
- [ ] 7.5 Add "Add Lead" button to `LeadsList.tsx` header that opens the `CreateLeadDialog`
- [ ] 7.6 Add `useCreateManualLead` mutation hook that calls the manual endpoint and invalidates leads list on success
- [ ] 7.7 Write unit tests for manual lead creation (backend validation, frontend form validation, API integration)

## Task 8: Enable Job Type Editing
- [ ] 8.1 Fix `JobForm.tsx`: change the job type `<Select>` from `defaultValue={field.value}` to `value={field.value}` so it reflects the current value when editing
- [ ] 8.2 Write/update `JobForm.test.tsx` to verify job type dropdown shows current value when editing an existing job and allows changing it

## Task 9: Property-Based Tests
- [ ] 9.1 Write Hypothesis property tests for token expiry thresholds (Property 4) and refresh token validity (Property 5) in `tests/unit/test_pbt_asap_platform_fixes.py`
- [ ] 9.2 Write Hypothesis property tests for lead deletion (Property 6), conversion job description preservation (Property 7), conversion status update (Property 8), conversion without job (Property 9), and already-converted rejection (Property 10) in `tests/unit/test_pbt_asap_platform_fixes.py`
- [ ] 9.3 Write Hypothesis property tests for manual lead validation (Property 11), manual lead round trip (Property 12), and job type update persistence (Property 13) in `tests/unit/test_pbt_asap_platform_fixes.py`

## Task 10: Regression Testing — Backend Test Suite Gate
- [ ] 10.1 Run the full existing backend test suite (`uv run pytest -v`) and capture baseline results — document any pre-existing failures
- [ ] 10.2 After all Tasks 1-9 are complete, re-run the full backend test suite and verify zero new failures compared to baseline
- [ ] 10.3 Run the full existing frontend test suite (`npm test` in `frontend/`) and verify zero new failures

## Task 11: Regression Testing — Cross-Feature Integration Tests
- [ ] 11.1 Write `tests/integration/test_asap_regression.py` with tests verifying auth token changes don't break: customer API CRUD, lead API CRUD, job API CRUD, invoice API, schedule API, and agreement API endpoints (all should still accept valid tokens and reject expired ones)
- [ ] 11.2 Add regression tests verifying lead service changes don't break: Google Sheets poller lead creation flow, lead-to-estimate pipeline, and lead SMS deferred processing
- [ ] 11.3 Add regression tests verifying customer search changes don't break: customer detail retrieval, customer update, and property listing via customer API

## Task 12: Regression Testing — E2E Browser Smoke Tests
- [ ] 12.1 Run existing E2E scripts (`scripts/e2e/test-customers.sh`, `test-leads.sh`, `test-jobs.sh`, `test-dashboard.sh`) via agent-browser and verify all pass
- [ ] 12.2 Run auth-related E2E scripts (`scripts/e2e/test-session-persistence.sh`, `test-navigation-security.sh`) and verify session persistence and route protection still work with new token durations
- [ ] 12.3 Run critical flow E2E scripts (`scripts/e2e/test-agreement-flow.sh`, `test-schedule.sh`, `test-invoices.sh`, `test-invoice-portal.sh`) and verify these untouched features still work end-to-end
- [ ] 12.4 Perform full platform smoke test via agent-browser: login → navigate every major page (dashboard, customers, leads, jobs, schedule, invoices, sales, accounting, marketing, settings) → verify each loads without errors → refresh page and verify session persists → navigate to /work-requests and verify redirect to leads
