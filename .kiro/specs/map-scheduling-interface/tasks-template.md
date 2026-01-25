# Map-Based Scheduling Interface - Tasks (With Inline Validations)

## Overview

This task list implements Phase 5: Map-Based Scheduling Interface for the Grin's Irrigation Platform.
**Every UI component task group includes an inline agent-browser validation task.**

**Total Estimated Time:** 14-20 hours
**Phases:** 5A (Basic Map), 5B (Routes), 5C (Interactive Features)

---

## Phase 5A: Basic Map View (5-7 hours)

### 5A.1 Backend Schema Updates

- [ ] 1.1 Add coordinate fields to ScheduleJobAssignment schema
- [ ] 1.2 Add start location fields to ScheduleStaffAssignment schema
- [ ] 1.3 Update schedule generation service to pass coordinates
- [ ] 1.4 Write backend unit tests for schema changes
- [ ] 1.5 Run backend quality checks

### 5A.2 Frontend Type Updates

- [ ] 2.1 Update ScheduleJobAssignment type with coordinates
- [ ] 2.2 Update ScheduleStaffAssignment type with start location
- [ ] 2.3 Create map-specific types file

### 5A.3 Staff Colors Utility

- [ ] 3.1 Create staff colors utility
- [ ] 3.2 Write unit tests for staff colors

### 5A.4 Map Styling Utility

- [ ] 4.1 Create map styles utility

### 5A.5 MapProvider Component

- [ ] 5.1 Create MapProvider component
- [ ] 5.2 Create map components barrel export

### 5A.6 ScheduleMap Container Component

- [ ] 6.1 Create ScheduleMap component
- [ ] 6.2 Add data-testid attributes to ScheduleMap
- [ ] 6.3 **Validate ScheduleMap renders correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='schedule-map']"
    agent-browser screenshot screenshots/map/6-schedule-map.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5A.7 MapMarker Component

- [ ] 7.1 Create MapMarker component
- [ ] 7.2 Add data-testid to MapMarker
- [ ] 7.3 **Validate MapMarker renders correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid^='map-marker']"
    agent-browser screenshot screenshots/map/7-map-markers.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5A.8 View Toggle Integration

- [ ] 8.1 Add view toggle buttons to ScheduleGenerationPage
- [ ] 8.2 Conditionally render ScheduleMap or ScheduleResults
- [ ] 8.3 **Validate view toggle works correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser is visible "[data-testid='view-toggle-list']"
    agent-browser is visible "[data-testid='view-toggle-map']"
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='schedule-map']"
    agent-browser click "[data-testid='view-toggle-list']"
    agent-browser wait "[data-testid='schedule-results']"
    agent-browser is visible "[data-testid='schedule-results']"
    agent-browser screenshot screenshots/map/8-view-toggle.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5A.9 MapLegend Component

- [ ] 9.1 Create MapLegend component
- [ ] 9.2 Add MapLegend to ScheduleMap with data-testid
- [ ] 9.3 **Validate MapLegend renders correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-legend']"
    agent-browser screenshot screenshots/map/9-map-legend.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5A.10 Phase 5A Quality Checks

- [ ] 10.1 Run frontend linting and type checks
- [ ] 10.2 Run frontend tests

- [ ] 11. Checkpoint - Phase 5A Complete

---

## Phase 5B: Route Visualization (4-6 hours)

### 5B.1 StaffHomeMarker Component

- [ ] 12.1 Create StaffHomeMarker component
- [ ] 12.2 Add data-testid to StaffHomeMarker
- [ ] 12.3 Render StaffHomeMarkers in ScheduleMap
- [ ] 12.4 **Validate StaffHomeMarker renders correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid^='staff-home-marker']"
    agent-browser screenshot screenshots/map/12-staff-home-markers.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5B.2 RoutePolyline Component

- [ ] 13.1 Create RoutePolyline component
- [ ] 13.2 Add data-testid to RoutePolyline
- [ ] 13.3 Render RoutePolylines in ScheduleMap
- [ ] 13.4 **Validate RoutePolyline renders correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid^='route-polyline']"
    agent-browser screenshot screenshots/map/13-route-polylines.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5B.3 useMapData Hook

- [ ] 14.1 Create useMapData hook
- [ ] 14.2 Write unit tests for useMapData

### 5B.4 useMapBounds Hook

- [ ] 15.1 Create useMapBounds hook
- [ ] 15.2 Write unit tests for useMapBounds
- [ ] 15.3 Integrate auto-fit bounds in ScheduleMap
- [ ] 15.4 **Validate auto-fit bounds works correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser wait 1000
    agent-browser screenshot screenshots/map/15-auto-bounds.png
    ```
  - **On Failure:** Fix hook, re-run typecheck, re-validate

### 5B.5 Show Routes Toggle

- [ ] 16.1 Add show routes toggle state
- [ ] 16.2 Create show routes toggle UI
- [ ] 16.3 **Validate show routes toggle works correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='show-routes-toggle']"
    agent-browser click "[data-testid='show-routes-toggle']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/16-routes-toggle.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5B.6 Phase 5B Quality Checks

- [ ] 17.1 Run frontend quality checks

- [ ] 18. Checkpoint - Phase 5B Complete

---

## Phase 5C: Interactive Features (7-9 hours)

### 5C.1 MapFilters Component

- [ ] 19.1 Create MapFilters component
- [ ] 19.2 Add data-testid attributes to MapFilters
- [ ] 19.3 Integrate MapFilters with ScheduleMap
- [ ] 19.4 **Validate MapFilters renders and works correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-filters']"
    agent-browser click "[data-testid^='staff-filter-']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/19-map-filters.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5C.2 MapInfoWindow Component

- [ ] 20.1 Create MapInfoWindow component
- [ ] 20.2 Add data-testid to MapInfoWindow
- [ ] 20.3 Integrate MapInfoWindow with marker clicks
- [ ] 20.4 **Validate MapInfoWindow renders on marker click**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid^='map-marker']"
    agent-browser wait "[data-testid='map-info-window']"
    agent-browser is visible "[data-testid='map-info-window']"
    agent-browser screenshot screenshots/map/20-info-window.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5C.3 Hover Preview

- [ ] 21.1 Add hover state to MapMarker
- [ ] 21.2 Create hover tooltip UI
- [ ] 21.3 **Validate hover tooltip appears**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser hover "[data-testid^='map-marker']"
    agent-browser wait 300
    agent-browser screenshot screenshots/map/21-hover-tooltip.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5C.4 Marker Clustering

- [ ] 22.1 Integrate MarkerClusterer
- [ ] 22.2 Configure clustering options

### 5C.5 MapControls Component

- [ ] 23.1 Create MapControls component
- [ ] 23.2 Add data-testid to MapControls
- [ ] 23.3 Integrate MapControls with ScheduleMap
- [ ] 23.4 **Validate MapControls renders and works correctly**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='fit-bounds-btn']"
    agent-browser click "[data-testid='fit-bounds-btn']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/23-map-controls.png
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5C.6 Empty States and Error Handling

- [ ] 24.1 Create MapEmptyState component
- [ ] 24.2 Add data-testid to MapEmptyState
- [ ] 24.3 Create MapErrorState component
- [ ] 24.4 Add data-testid to MapErrorState
- [ ] 24.5 Create MissingCoordsWarning component
- [ ] 24.6 Add data-testid to MissingCoordsWarning
- [ ] 24.7 Integrate empty/error states in ScheduleMap

### 5C.7 Loading State

- [ ] 25.1 Create MapLoadingState component
- [ ] 25.2 Add data-testid to MapLoadingState

### 5C.8 Mobile Responsive Layout

- [ ] 26.1 Create MobileJobSheet component
- [ ] 26.2 Add responsive breakpoints to ScheduleMap
- [ ] 26.3 **Validate mobile responsive layout**
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser click "[data-testid='preview-btn']"
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser set viewport 375 667
    agent-browser wait 500
    agent-browser screenshot screenshots/map/26-mobile-layout.png
    agent-browser set viewport 1280 720
    ```
  - **On Failure:** Fix component, re-run typecheck, re-validate

### 5C.9 Phase 5C Quality Checks

- [ ] 27.1 Run all frontend quality checks
- [ ] 27.2 Run backend quality checks

- [ ] 28. Checkpoint - Phase 5C Complete

---

## Phase 5 Completion

- [ ] 29.1 Create screenshots directory
- [ ] 29.2 Final end-to-end validation
- [ ] 29.3 Update DEVLOG with Phase 5 completion

- [ ] 30. Checkpoint - Phase 5 Complete
