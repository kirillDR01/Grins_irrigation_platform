# Requirements Document

## Introduction

This document defines the requirements for wiring existing AI scheduling frontend components into composed page views with routing. All individual components (ScheduleOverviewEnhanced, SchedulingChat, AlertsPanel, CapacityHeatMap, BatchScheduleResults, ResourceScheduleView, ResourceMobileChat, PreJobChecklist) are already built and exported from their respective feature slices but are not rendered by any page or reachable via any route. The existing `/schedule` route still renders the old `SchedulePage` with FullCalendar. This spec covers creating the page compositions, adding routes, and updating navigation so users can access the AI scheduling views.

The user specifically requested that these changes live under the "Generate Routes" tab (`/schedule/generate`), replacing or extending the current schedule generation page to serve as the AI scheduling hub.

## Glossary

- **AI_Schedule_Page**: The composed page view that renders ScheduleOverviewEnhanced (with CapacityHeatMap integrated at the bottom), AlertsPanel below the overview, and SchedulingChat as a persistent right sidebar — forming the admin AI scheduling workspace.
- **Resource_Mobile_Page**: The composed mobile page view that renders ResourceScheduleView, ResourceMobileChat, and PreJobChecklist for field technicians.
- **Router**: The `createBrowserRouter` configuration in `frontend/src/core/router/index.tsx` that maps URL paths to page components.
- **Layout**: The shared `Layout` component in `frontend/src/shared/components/Layout.tsx` that renders the sidebar navigation and wraps all authenticated pages.
- **Page_Wrapper**: A thin page component in `frontend/src/pages/` that imports and renders a composed feature view, following the project's existing pattern (e.g., `Schedule.tsx` wraps `SchedulePageComponent`).
- **Generate_Routes_Tab**: The existing "Generate Routes" navigation item at `/schedule/generate` in the sidebar, which the user identified as the entry point for AI scheduling.
- **ScheduleOverviewEnhanced**: The custom resource-row × day-column grid component in `features/schedule/components/` that replaces FullCalendar for the AI scheduling view.
- **SchedulingChat**: The persistent right sidebar AI chat panel in `features/ai/components/` for admin scheduling commands.
- **AlertsPanel**: The alerts and suggestions panel in `features/scheduling-alerts/components/` displaying red alerts and green suggestions.
- **CapacityHeatMap**: The utilization bar component in `features/schedule/components/` showing daily aggregate capacity percentages.
- **BatchScheduleResults**: The multi-week campaign results component in `features/schedule/components/`.
- **ResourceScheduleView**: The mobile schedule card component in `features/resource-mobile/components/` showing daily route with ETAs.
- **ResourceMobileChat**: The mobile-optimized chat component in `features/ai/components/` for field technician interactions.
- **PreJobChecklist**: The pre-job requirements display component in `features/ai/components/` for resource mobile view.

## Requirements

### Requirement 1: AI Schedule Admin Page Composition

**User Story:** As a User Admin, I want a single page that composes the AI scheduling components together (overview grid, alerts panel, and chat sidebar), so that I can manage AI-powered scheduling from one unified view.

#### Acceptance Criteria

1. THE AI_Schedule_Page SHALL render ScheduleOverviewEnhanced as the primary content area occupying the left portion of the viewport, with CapacityHeatMap integrated at the bottom of the overview grid.
2. THE AI_Schedule_Page SHALL render AlertsPanel below the ScheduleOverviewEnhanced component.
3. THE AI_Schedule_Page SHALL render SchedulingChat as a persistent right sidebar panel alongside the overview and alerts content.
4. THE AI_Schedule_Page SHALL use a responsive layout where the SchedulingChat sidebar has a fixed width and the overview and alerts content fills the remaining horizontal space.
5. WHEN the SchedulingChat produces schedule changes via the "Publish Schedule" button, THE AI_Schedule_Page SHALL pass those changes to the ScheduleOverviewEnhanced component for display.
6. THE AI_Schedule_Page SHALL pass the current schedule date context to both the ScheduleOverviewEnhanced and AlertsPanel components so alerts are filtered to the viewed date.

### Requirement 2: Route Registration for AI Schedule Page

**User Story:** As a User Admin, I want to navigate to the AI scheduling view via the existing "Generate Routes" tab, so that I can access the AI scheduling workspace from the sidebar navigation without adding new navigation items.

#### Acceptance Criteria

1. THE Router SHALL register a route at `/schedule/generate` that renders the AI_Schedule_Page.
2. THE Page_Wrapper for the AI schedule view SHALL follow the existing project pattern of a thin page component in `frontend/src/pages/` that imports and renders the composed view.
3. THE Router SHALL lazy-load the AI_Schedule_Page using the same `lazy(() => import(...))` pattern used by all other pages in the router.
4. THE Generate_Routes_Tab navigation item in the Layout sidebar SHALL continue to point to `/schedule/generate` and remain accessible to authenticated users.
5. WHEN a user navigates to `/schedule/generate`, THE Router SHALL render the AI_Schedule_Page within the existing ProtectedLayoutWrapper (requiring authentication).

### Requirement 3: Resource Mobile Page Composition

**User Story:** As a Resource (field technician), I want a mobile-optimized page that composes my daily schedule view with the AI chat assistant, so that I can view my route and interact with the scheduling AI from the field.

#### Acceptance Criteria

1. THE Resource_Mobile_Page SHALL render ResourceScheduleView as the primary content showing the daily route with job cards, ETAs, and pre-job flags.
2. THE Resource_Mobile_Page SHALL render ResourceMobileChat below the schedule view, providing the field assistant chat interface.
3. THE Resource_Mobile_Page SHALL use a mobile-first stacked layout where the schedule view and chat are vertically arranged.
4. WHEN a Resource accesses the Resource_Mobile_Page, THE page SHALL display the current day's schedule by default.

### Requirement 4: Route Registration for Resource Mobile Page

**User Story:** As a Resource (field technician), I want a dedicated mobile route to access my schedule and chat assistant, so that I can reach the mobile scheduling view from a direct URL.

#### Acceptance Criteria

1. THE Router SHALL register a route at `/schedule/mobile` that renders the Resource_Mobile_Page.
2. THE Page_Wrapper for the resource mobile view SHALL follow the existing project pattern of a thin page component in `frontend/src/pages/`.
3. THE Router SHALL lazy-load the Resource_Mobile_Page using the same `lazy(() => import(...))` pattern.
4. WHEN a user navigates to `/schedule/mobile`, THE Router SHALL render the Resource_Mobile_Page within the existing ProtectedLayoutWrapper (requiring authentication).

### Requirement 5: Component Integration and Data Flow

**User Story:** As a developer, I want the composed pages to properly wire component props and callbacks, so that the AI scheduling components communicate correctly within the page layout.

#### Acceptance Criteria

1. THE AI_Schedule_Page SHALL import ScheduleOverviewEnhanced from `@/features/schedule`, AlertsPanel from `@/features/scheduling-alerts`, and SchedulingChat from `@/features/ai`.
2. THE AI_Schedule_Page SHALL manage a shared `scheduleDate` state that is passed to both ScheduleOverviewEnhanced and AlertsPanel for date-synchronized display.
3. WHEN the user changes the view mode or navigates to a different week in ScheduleOverviewEnhanced, THE AI_Schedule_Page SHALL update the shared schedule date context.
4. THE Resource_Mobile_Page SHALL import ResourceScheduleView from `@/features/resource-mobile` and ResourceMobileChat from `@/features/ai`.
5. IF the SchedulingChat returns an error, THEN THE AI_Schedule_Page SHALL continue rendering the ScheduleOverviewEnhanced and AlertsPanel without disruption.

### Requirement 6: Accessibility and Test Identifiers

**User Story:** As a developer, I want the composed pages to include proper test identifiers and semantic structure, so that the pages are testable and accessible.

#### Acceptance Criteria

1. THE AI_Schedule_Page SHALL include a `data-testid="ai-schedule-page"` attribute on its root element.
2. THE Resource_Mobile_Page SHALL include a `data-testid="resource-mobile-page"` attribute on its root element.
3. THE AI_Schedule_Page SHALL use semantic HTML landmarks: a `main` element wrapping the overview and alerts content, and an `aside` element wrapping the SchedulingChat sidebar.
4. THE AI_Schedule_Page SHALL include a visually hidden heading (e.g., `<h1>`) identifying the page as the AI Scheduling workspace for screen reader navigation.
