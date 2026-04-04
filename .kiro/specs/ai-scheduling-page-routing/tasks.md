# Implementation Plan: AI Scheduling Page Routing

## Overview

Compose existing AI scheduling components into two page views (admin and mobile), register routes, and update exports. All components already exist — this is purely composition, routing, and wiring. Implementation follows a phased approach: core implementation → unit tests → property-based tests → integration tests → E2E verification → quality gate.

## Tasks

- [x] 1. Create AIScheduleView composed page component
  - [x] 1.1 Create `frontend/src/features/schedule/components/AIScheduleView.tsx`
    - Import `ScheduleOverviewEnhanced` from local components, `AlertsPanel` from `@/features/scheduling-alerts`, `SchedulingChat` from `@/features/ai/components/SchedulingChat`
    - Manage shared `scheduleDate` state via `useState<string>` defaulting to today's ISO date
    - Use CSS Grid layout with `grid-template-columns: 1fr 380px` for main content + chat sidebar
    - Render `<main>` landmark wrapping `ScheduleOverviewEnhanced` and `AlertsPanel`
    - Render `<aside>` landmark wrapping `SchedulingChat` inside a React error boundary
    - Include `data-testid="ai-schedule-page"` on root element
    - Include a visually hidden `<h1>` heading for screen reader navigation
    - Pass `scheduleDate` to both `ScheduleOverviewEnhanced` (via data hooks) and `AlertsPanel`
    - Wire `onViewModeChange` callback from `ScheduleOverviewEnhanced` to update `scheduleDate`
    - Wire `onPublishSchedule` callback from `SchedulingChat` to invalidate schedule/alert queries
    - Create a `ChatErrorFallback` component for the error boundary fallback
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 5.1, 5.2, 5.3, 5.5, 6.1, 6.3, 6.4_

  - [x] 1.2 Export `AIScheduleView` from `frontend/src/features/schedule/index.ts`
    - Add `AIScheduleView` to the components export list
    - _Requirements: 5.1_

  - [x] 1.3 Update `frontend/src/pages/ScheduleGenerate.tsx` to render `AIScheduleView`
    - Replace `ScheduleGenerationPage` import with `AIScheduleView` from `@/features/schedule`
    - _Requirements: 2.2_

- [x] 2. Create ResourceMobileView composed page component
  - [x] 2.1 Create `frontend/src/features/resource-mobile/components/ResourceMobileView.tsx`
    - Import `ResourceScheduleView` from local components, `ResourceMobileChat` from `@/features/ai/components/ResourceMobileChat`
    - Use mobile-first stacked layout (flex column) with schedule view on top, chat below
    - Include `data-testid="resource-mobile-page"` on root element
    - Render `ResourceScheduleView` with no params (defaults to current day)
    - Render `ResourceMobileChat` below the schedule view
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.4, 6.2_

  - [x] 2.2 Export `ResourceMobileView` from `frontend/src/features/resource-mobile/index.ts`
    - Add `ResourceMobileView` to the components export list
    - _Requirements: 5.4_

  - [x] 2.3 Create `frontend/src/pages/ScheduleMobile.tsx` page wrapper
    - Follow the thin page-wrapper pattern: import `ResourceMobileView` from `@/features/resource-mobile` and render it
    - Export `ScheduleMobilePage` as named export
    - _Requirements: 4.2_

- [ ] 3. Register routes in the router
  - [x] 3.1 Add `/schedule/mobile` route to `frontend/src/core/router/index.tsx`
    - Add lazy import for `ScheduleMobilePage` from `@/pages/ScheduleMobile`
    - Register `schedule/mobile` route inside the ProtectedLayoutWrapper children, after the existing `schedule/generate` route
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 4. Checkpoint — Verify implementation compiles
  - Run TypeScript type checking (`npx tsc --noEmit`) and ESLint to ensure all new files compile without errors. Ask the user if questions arise.

- [x] 5. Unit tests for composed pages and page wrappers
  - [x] 5.1 Create `frontend/src/features/schedule/components/AIScheduleView.test.tsx`
    - Test that AIScheduleView renders all three child components (overview, alerts, chat) with mocked query hooks
    - Test that `data-testid="ai-schedule-page"` is present on root element
    - Test that `<main>` landmark contains overview and alerts
    - Test that `<aside>` landmark contains scheduling chat
    - Test that visually hidden `<h1>` heading exists
    - Test that AlertsPanel receives the current scheduleDate prop
    - Test that error boundary catches SchedulingChat crash and renders fallback while overview + alerts remain
    - Mock `ScheduleOverviewEnhanced`, `AlertsPanel`, `SchedulingChat` as simple stubs with data-testid attributes
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 5.2, 5.5, 6.1, 6.3, 6.4_

  - [x] 5.2 Create `frontend/src/features/resource-mobile/components/ResourceMobileView.test.tsx`
    - Test that ResourceMobileView renders both child components (schedule view, mobile chat)
    - Test that `data-testid="resource-mobile-page"` is present on root element
    - Test that ResourceScheduleView appears before ResourceMobileChat in document order
    - Mock `ResourceScheduleView` and `ResourceMobileChat` as simple stubs with data-testid attributes
    - _Requirements: 3.1, 3.2, 6.2_

  - [x] 5.3 Create `frontend/src/pages/ScheduleGenerate.test.tsx`
    - Test that ScheduleGeneratePage renders AIScheduleView
    - _Requirements: 2.2_

  - [x] 5.4 Create `frontend/src/pages/ScheduleMobile.test.tsx`
    - Test that ScheduleMobilePage renders ResourceMobileView
    - _Requirements: 4.2_

  - [x] 5.5 Add router route verification tests in `frontend/src/core/router/router.test.tsx`
    - Test that router config contains `/schedule/generate` path
    - Test that router config contains `/schedule/mobile` path
    - _Requirements: 2.1, 4.1_

- [x] 6. Checkpoint — Ensure unit tests pass
  - Run `cd frontend && npx vitest --run AIScheduleView.test ResourceMobileView.test ScheduleGenerate.test ScheduleMobile.test router.test` and ensure all pass. Ask the user if questions arise.

- [x] 7. Property-based tests with fast-check
  - [x] 7.1 Write PBT for Property 1: Admin Page Composition Structure in `frontend/src/features/schedule/components/AIScheduleView.test.tsx`
    - **Property 1: Admin Page Composition Structure**
    - **Validates: Requirements 1.1, 1.2, 1.3, 6.1, 6.3, 6.4**
    - Generate random schedule data (resources, days, cells, capacity arrays) via `fc.record` arbitraries
    - For each generated dataset, render AIScheduleView with mocked query hooks returning that data
    - Assert DOM contains: root with `data-testid="ai-schedule-page"`, `<main>` with overview + alerts, `<aside>` with chat, visually hidden `<h1>`

  - [x] 7.2 Write PBT for Property 2: Shared Schedule Date Propagation in `frontend/src/features/schedule/components/AIScheduleView.test.tsx`
    - **Property 2: Shared Schedule Date Propagation**
    - **Validates: Requirements 1.6, 5.2**
    - Generate random ISO date strings via `fc.date()` mapped to ISO format
    - For each date, verify both ScheduleOverviewEnhanced and AlertsPanel receive the same date value as a prop

  - [x] 7.3 Write PBT for Property 3: Date Context Update on View Change in `frontend/src/features/schedule/components/AIScheduleView.test.tsx`
    - **Property 3: Date Context Update on View Change**
    - **Validates: Requirements 5.3**
    - Generate random sequences of view mode changes via `fc.array(fc.constantFrom('day', 'week', 'month'))`
    - Simulate view mode changes and verify AlertsPanel's scheduleDate prop updates after each change

  - [x] 7.4 Write PBT for Property 4: Mobile Page Composition Structure in `frontend/src/features/resource-mobile/components/ResourceMobileView.test.tsx`
    - **Property 4: Mobile Page Composition Structure**
    - **Validates: Requirements 3.1, 3.2, 6.2**
    - Generate random resource schedule data
    - Render ResourceMobileView with mocked hooks and assert DOM ordering: schedule-view before mobile-chat

  - [x] 7.5 Write PBT for Property 5: Chat Error Isolation in `frontend/src/features/schedule/components/AIScheduleView.test.tsx`
    - **Property 5: Chat Error Isolation**
    - **Validates: Requirements 5.5**
    - Generate random Error objects via `fc.string().map(msg => new Error(msg))`
    - Mock SchedulingChat to throw each error, render AIScheduleView, verify overview + alerts testids remain in DOM

- [x] 8. Checkpoint — Ensure PBT tests pass
  - Run `cd frontend && npx vitest --run AIScheduleView.test ResourceMobileView.test` and ensure all property-based tests pass. Ask the user if questions arise.

- [x] 9. Integration tests — verify composed pages work with router and layout
  - [x] 9.1 Create `frontend/src/features/schedule/components/AIScheduleView.integration.test.tsx`
    - Render the full router with `MemoryRouter` at `/schedule/generate` inside `QueryClientProvider`
    - Verify the AIScheduleView renders within the ProtectedLayoutWrapper
    - Verify the "Generate Routes" nav item is active when on `/schedule/generate`
    - Verify navigation from `/schedule` to `/schedule/generate` works
    - Mock auth context to simulate authenticated user
    - _Requirements: 2.1, 2.3, 2.4, 2.5_

  - [x] 9.2 Create `frontend/src/features/resource-mobile/components/ResourceMobileView.integration.test.tsx`
    - Render the full router with `MemoryRouter` at `/schedule/mobile` inside `QueryClientProvider`
    - Verify the ResourceMobileView renders within the ProtectedLayoutWrapper
    - Verify navigation to `/schedule/mobile` works
    - Mock auth context to simulate authenticated user
    - _Requirements: 4.1, 4.3, 4.4_

- [x] 10. Checkpoint — Ensure integration tests pass
  - Run `cd frontend && npx vitest --run AIScheduleView.integration ResourceMobileView.integration` and ensure all pass. Ask the user if questions arise.

- [x] 11. E2E verification with agent-browser
  - [x] 11.1 Create E2E test script `scripts/e2e/test-ai-scheduling-pages.sh`
    - Start the frontend dev server (`cd frontend && npm run dev &`) and wait for it to be ready
    - Open `/schedule/generate` and verify all three components render (overview, alerts, chat sidebar) using `agent-browser snapshot` and `agent-browser is visible`
    - Take screenshot: `e2e-screenshots/ai-schedule-page-desktop.png`
    - Open `/schedule/mobile` and verify both components render (schedule view, mobile chat)
    - Take screenshot: `e2e-screenshots/resource-mobile-page-desktop.png`
    - Test responsive behavior:
      - Mobile viewport (375×812): screenshot both pages, verify stacked layout
      - Tablet viewport (768×1024): screenshot both pages
      - Desktop viewport (1440×900): screenshot both pages
    - Check for console errors on both pages via `agent-browser console` and `agent-browser errors`
    - Close browser and stop dev server
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 3.1, 3.2, 3.3, 4.1, 6.1, 6.2_

- [x] 12. Linting and type checking verification
  - Run `cd frontend && npx tsc --noEmit` to verify TypeScript strict mode passes with zero errors
  - Run `cd frontend && npx eslint src/features/schedule/components/AIScheduleView.tsx src/features/resource-mobile/components/ResourceMobileView.tsx src/pages/ScheduleGenerate.tsx src/pages/ScheduleMobile.tsx src/core/router/index.tsx` to verify lint passes
  - Ask the user if questions arise.

- [x] 13. Final quality gate
  - Run all frontend tests: `cd frontend && npx vitest --run`
  - Run TypeScript type checking: `cd frontend && npx tsc --noEmit`
  - Run ESLint on all modified/new files
  - Verify zero test failures, zero type errors, zero lint errors
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required — no optional tasks
- Each task references specific requirements for traceability
- Property-based tests use fast-check and validate all 5 correctness properties from the design document
- Checkpoints ensure incremental validation at each phase boundary
- E2E verification uses agent-browser (Vercel) for real browser testing with screenshots
- The phased approach follows: implementation → unit tests → PBT → integration tests → E2E → quality gate
