# Map-Based Scheduling Interface - Tasks

## Overview

This task list implements Phase 5: Map-Based Scheduling Interface for the Grin's Irrigation Platform.
Every task includes agent-browser validation commands for Ralph Wiggum autonomous loop execution.

**Total Estimated Time:** 14-20 hours
**Phases:** 5A (Basic Map), 5B (Routes), 5C (Interactive Features)

---

<!-- ## Pre-Implementation Setup

- [ ] 0.1 Verify Google Maps API key is configured
  - **Implementation:** Check VITE_GOOGLE_MAPS_API_KEY in frontend/.env
  - **Files:** `frontend/.env`
  - **Validation:**
    ```bash
    grep VITE_GOOGLE_MAPS_API_KEY frontend/.env
    ```
  - **Success:** Environment variable exists with valid API key

- [ ] 0.2 Install Google Maps dependencies
  - **Implementation:** Install @react-google-maps/api and @googlemaps/markerclusterer
  - **Files:** `frontend/package.json`
  - **Validation:**
    ```bash
    cd frontend && npm install @react-google-maps/api @googlemaps/markerclusterer
    npm list @react-google-maps/api
    ```
  - **Success:** Packages installed without errors

- [ ] 0.3 Verify backend schedule generation returns data
  - **Implementation:** Test existing schedule generation endpoint
  - **Validation:**
    ```bash
    curl -s http://localhost:8000/api/v1/schedule/preview?schedule_date=2026-01-24 | head -100
    ```
  - **Success:** API returns schedule data with assignments -->

---

## Phase 5A: Basic Map View (5-7 hours)

### 5A.1 Backend Schema Updates

- [x] 1.1 Add coordinate fields to ScheduleJobAssignment schema
  - **Implementation:** Add latitude, longitude fields to ScheduleJobAssignment
  - **Files:** `src/grins_platform/schemas/schedule_generation.py`
  - **Validation:**
    ```bash
    grep -A 5 "latitude" src/grins_platform/schemas/schedule_generation.py
    uv run python -c "from grins_platform.schemas.schedule_generation import ScheduleJobAssignment; print(ScheduleJobAssignment.model_fields.keys())"
    ```
  - **Success:** Schema includes latitude and longitude fields

- [x] 1.2 Add start location fields to ScheduleStaffAssignment schema
  - **Implementation:** Add start_lat, start_lng fields to ScheduleStaffAssignment
  - **Files:** `src/grins_platform/schemas/schedule_generation.py`
  - **Validation:**
    ```bash
    grep -A 5 "start_lat" src/grins_platform/schemas/schedule_generation.py
    uv run python -c "from grins_platform.schemas.schedule_generation import ScheduleStaffAssignment; print(ScheduleStaffAssignment.model_fields.keys())"
    ```
  - **Success:** Schema includes start_lat and start_lng fields

- [x] 1.3 Update schedule generation service to pass coordinates
  - **Implementation:** Modify _build_response to include lat/lng from ScheduleLocation
  - **Files:** `src/grins_platform/services/schedule_generation_service.py`
  - **Validation:**
    ```bash
    grep -B 2 -A 2 "latitude=float" src/grins_platform/services/schedule_generation_service.py
    curl -s -X POST http://localhost:8000/api/v1/schedule/generate \
      -H "Content-Type: application/json" \
      -d '{"schedule_date": "2026-01-24"}' | jq '.assignments[0].jobs[0] | {latitude, longitude}'
    ```
  - **Success:** API response includes latitude and longitude for jobs

- [x] 1.4 Write backend unit tests for schema changes
  - **Implementation:** Test coordinate fields in schemas
  - **Files:** `src/grins_platform/tests/test_schedule_generation_schemas.py`
  - **Validation:**
    ```bash
    uv run pytest src/grins_platform/tests/test_schedule_generation_schemas.py -v -k "coordinate or lat"
    ```
  - **Success:** All schema tests pass

- [x] 1.5 Run backend quality checks
  - **Implementation:** Ensure all backend changes pass quality checks
  - **Validation:**
    ```bash
    uv run ruff check src/grins_platform/schemas/schedule_generation.py
    uv run mypy src/grins_platform/schemas/schedule_generation.py
    uv run pytest src/grins_platform/tests/ -v --tb=short
    ```
  - **Success:** Zero linting errors, zero type errors, all tests pass

### 5A.2 Frontend Type Updates

- [x] 2.1 Update ScheduleJobAssignment type with coordinates
  - **Implementation:** Add latitude, longitude to ScheduleJobAssignment interface
  - **Files:** `frontend/src/features/schedule/types/index.ts`
  - **Validation:**
    ```bash
    grep -A 3 "latitude" frontend/src/features/schedule/types/index.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Type includes coordinate fields, typecheck passes

- [x] 2.2 Update ScheduleStaffAssignment type with start location
  - **Implementation:** Add start_lat, start_lng to ScheduleStaffAssignment interface
  - **Files:** `frontend/src/features/schedule/types/index.ts`
  - **Validation:**
    ```bash
    grep -A 3 "start_lat" frontend/src/features/schedule/types/index.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Type includes start location fields, typecheck passes

- [x] 2.3 Create map-specific types file
  - **Implementation:** Create map.ts with MapJob, MapRoute, MapFilters, MapMode types
  - **Files:** `frontend/src/features/schedule/types/map.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/types/map.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Map types file exists with all required interfaces

### 5A.3 Staff Colors Utility

- [x] 3.1 Create staff colors utility
  - **Implementation:** Create staffColors.ts with STAFF_COLORS mapping and getStaffColor function
  - **Files:** `frontend/src/features/schedule/utils/staffColors.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/utils/staffColors.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Staff colors utility exists with Viktor=Red, Vas=Blue, etc.

- [x] 3.2 Write unit tests for staff colors
  - **Implementation:** Test getStaffColor returns correct colors for each staff name
  - **Files:** `frontend/src/features/schedule/utils/staffColors.test.ts`
  - **Validation:**
    ```bash
    cd frontend && npm test -- staffColors --run
    ```
  - **Success:** All staff color tests pass

### 5A.4 Map Styling Utility

- [x] 4.1 Create map styles utility
  - **Implementation:** Create mapStyles.ts with MAP_STYLES, DEFAULT_CENTER, MAP_OPTIONS
  - **Files:** `frontend/src/features/schedule/utils/mapStyles.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/utils/mapStyles.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Map styles utility exists with clean styling config

### 5A.5 MapProvider Component

- [x] 5.1 Create MapProvider component
  - **Implementation:** Create MapProvider.tsx wrapping LoadScript from @react-google-maps/api
  - **Files:** `frontend/src/features/schedule/components/map/MapProvider.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapProvider.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapProvider component exists and loads Google Maps API

- [x] 5.2 Create map components barrel export
  - **Implementation:** Create index.ts exporting all map components
  - **Files:** `frontend/src/features/schedule/components/map/index.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/index.ts
    ```
  - **Success:** Barrel export file exists

### 5A.6 ScheduleMap Container Component

- [x] 6.1 Create ScheduleMap component
  - **Implementation:** Create main map container with GoogleMap component
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/ScheduleMap.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** ScheduleMap component renders GoogleMap with custom styling

- [x] 6.2 Add data-testid attributes to ScheduleMap
  - **Implementation:** Add data-testid="schedule-map" to container
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid="schedule-map"' frontend/src/features/schedule/components/map/ScheduleMap.tsx
    ```
  - **Success:** data-testid attribute present

- [x] 6.3 **Validate ScheduleMap renders correctly**
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

- [x] 7.1 Create MapMarker component
  - **Implementation:** Create marker with staff color and sequence number
  - **Files:** `frontend/src/features/schedule/components/map/MapMarker.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapMarker.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapMarker component renders colored numbered markers

- [x] 7.2 Add data-testid to MapMarker
  - **Implementation:** Add data-testid="map-marker-{job_id}" to each marker
  - **Files:** `frontend/src/features/schedule/components/map/MapMarker.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MapMarker.tsx
    ```
  - **Success:** data-testid attribute with job_id present

- [x] 7.3 **Validate MapMarker renders correctly**
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

- [x] 8.1 Add view toggle buttons to ScheduleGenerationPage
  - **Implementation:** Add List/Map toggle buttons with ViewMode state
  - **Files:** `frontend/src/features/schedule/components/ScheduleGenerationPage.tsx`
  - **Validation:**
    ```bash
    grep -A 5 "view-toggle" frontend/src/features/schedule/components/ScheduleGenerationPage.tsx
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser is visible "[data-testid='view-toggle-list']"
    agent-browser is visible "[data-testid='view-toggle-map']"
    agent-browser screenshot screenshots/map/5a8-view-toggle.png
    agent-browser close
    ```
  - **Success:** View toggle buttons visible on schedule page

- [x] 8.2 Conditionally render ScheduleMap or ScheduleResults
  - **Implementation:** Show ScheduleMap when map view selected, ScheduleResults for list
  - **Files:** `frontend/src/features/schedule/components/ScheduleGenerationPage.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='schedule-map']"
    agent-browser screenshot screenshots/map/5a8-map-view.png
    agent-browser click "[data-testid='view-toggle-list']"
    agent-browser wait "[data-testid='schedule-results']"
    agent-browser is visible "[data-testid='schedule-results']"
    agent-browser close
    ```
  - **Success:** Clicking toggle switches between map and list views

- [x] 8.3 **Validate view toggle works correctly**
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

- [x] 9.1 Create MapLegend component
  - **Implementation:** Create legend showing staff colors and job counts
  - **Files:** `frontend/src/features/schedule/components/map/MapLegend.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapLegend.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapLegend component exists with staff color indicators

- [x] 9.2 Add MapLegend to ScheduleMap with data-testid
  - **Implementation:** Render MapLegend below map with data-testid="map-legend"
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-legend']"
    agent-browser screenshot screenshots/map/5a9-legend.png
    agent-browser close
    ```
  - **Success:** Legend visible below map with staff colors

- [x] 9.3 **Validate MapLegend renders correctly**
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

- [x] 10.1 Run frontend linting and type checks
  - **Implementation:** Ensure all Phase 5A code passes quality checks
  - **Validation:**
    ```bash
    cd frontend && npm run lint
    cd frontend && npm run typecheck
    ```
  - **Success:** Zero linting errors, zero type errors

- [x] 10.2 Run frontend tests
  - **Implementation:** Run all frontend tests including new map components
  - **Validation:**
    ```bash
    cd frontend && npm test -- --run
    ```
  - **Success:** All tests pass

- [x] 10.3 Visual validation of Phase 5A
  - **Implementation:** Complete visual validation of basic map view
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser snapshot -i
    agent-browser is visible "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-legend']"
    agent-browser screenshot screenshots/map/5a-complete.png
    agent-browser close
    ```
  - **Success:** Map displays with markers and legend

- [x] 11. Checkpoint - Phase 5A Complete
  - **Validation:** All Phase 5A tasks complete, map displays with markers
  - **Review:** Pause for user review before continuing to Phase 5B

---

## Phase 5B: Route Visualization (4-6 hours)

### 5B.1 StaffHomeMarker Component

- [x] 12.1 Create StaffHomeMarker component
  - **Implementation:** Create marker with house icon for staff starting location
  - **Files:** `frontend/src/features/schedule/components/map/StaffHomeMarker.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/StaffHomeMarker.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** StaffHomeMarker component renders house icon with staff color

- [x] 12.2 Add data-testid to StaffHomeMarker
  - **Implementation:** Add data-testid="staff-home-marker-{staff_id}"
  - **Files:** `frontend/src/features/schedule/components/map/StaffHomeMarker.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/StaffHomeMarker.tsx
    ```
  - **Success:** data-testid attribute with staff_id present

- [x] 12.3 Render StaffHomeMarkers in ScheduleMap
  - **Implementation:** Add StaffHomeMarker for each staff with start coordinates
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid^='staff-home-marker']"
    agent-browser screenshot screenshots/map/5b1-home-markers.png
    agent-browser close
    ```
  - **Success:** Staff home markers visible on map

- [x] 12.4 **Validate StaffHomeMarker renders correctly**
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

- [x] 13.1 Create RoutePolyline component
  - **Implementation:** Create straight-line polyline connecting jobs in sequence
  - **Files:** `frontend/src/features/schedule/components/map/RoutePolyline.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/RoutePolyline.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** RoutePolyline component renders colored polyline

- [x] 13.2 Add data-testid to RoutePolyline
  - **Implementation:** Add data-testid="route-polyline-{staff_id}"
  - **Files:** `frontend/src/features/schedule/components/map/RoutePolyline.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/RoutePolyline.tsx
    ```
  - **Success:** data-testid attribute with staff_id present

- [x] 13.3 Render RoutePolylines in ScheduleMap
  - **Implementation:** Add RoutePolyline for each staff route
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid^='route-polyline']"
    agent-browser screenshot screenshots/map/5b2-routes.png
    agent-browser close
    ```
  - **Success:** Route polylines visible connecting jobs

- [x] 13.4 **Validate RoutePolyline renders correctly**
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

- [x] 14.1 Create useMapData hook
  - **Implementation:** Transform schedule data into map-friendly format (jobs, routes)
  - **Files:** `frontend/src/features/schedule/hooks/useMapData.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/hooks/useMapData.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Hook transforms schedule data to MapJob[] and MapRoute[]

- [x] 14.2 Write unit tests for useMapData
  - **Implementation:** Test data transformation logic
  - **Files:** `frontend/src/features/schedule/hooks/useMapData.test.ts`
  - **Validation:**
    ```bash
    cd frontend && npm test -- useMapData --run
    ```
  - **Success:** All useMapData tests pass

### 5B.4 useMapBounds Hook

- [x] 15.1 Create useMapBounds hook
  - **Implementation:** Calculate bounds to fit all markers with padding
  - **Files:** `frontend/src/features/schedule/hooks/useMapBounds.ts`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/hooks/useMapBounds.ts
    cd frontend && npm run typecheck
    ```
  - **Success:** Hook calculates bounds from marker positions

- [x] 15.2 Write unit tests for useMapBounds
  - **Implementation:** Test bounds calculation includes all markers
  - **Files:** `frontend/src/features/schedule/hooks/useMapBounds.test.ts`
  - **Validation:**
    ```bash
    cd frontend && npm test -- useMapBounds --run
    ```
  - **Success:** All useMapBounds tests pass

- [x] 15.3 Integrate auto-fit bounds in ScheduleMap
  - **Implementation:** Auto-fit map to show all markers on load
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser wait 1000
    agent-browser screenshot screenshots/map/5b4-auto-bounds.png
    agent-browser close
    ```
  - **Success:** Map automatically zooms to fit all markers

- [x] 15.4 **Validate auto-fit bounds works correctly**
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

- [x] 16.1 Add show routes toggle state
  - **Implementation:** Add showRoutes state to ScheduleMap
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    grep -A 3 "showRoutes" frontend/src/features/schedule/components/map/ScheduleMap.tsx
    ```
  - **Success:** showRoutes state exists

- [x] 16.2 Create show routes toggle UI
  - **Implementation:** Add toggle button with data-testid="show-routes-toggle"
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='show-routes-toggle']"
    agent-browser click "[data-testid='show-routes-toggle']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/5b5-routes-toggle.png
    agent-browser close
    ```
  - **Success:** Toggle shows/hides route polylines

- [x] 16.3 **Validate show routes toggle works correctly**
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

- [x] 17.1 Run frontend quality checks
  - **Implementation:** Ensure all Phase 5B code passes quality checks
  - **Validation:**
    ```bash
    cd frontend && npm run lint
    cd frontend && npm run typecheck
    cd frontend && npm test -- --run
    ```
  - **Success:** Zero errors, all tests pass

- [x] 17.2 Visual validation of Phase 5B
  - **Implementation:** Complete visual validation of route visualization
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser snapshot -i
    agent-browser is visible "[data-testid^='staff-home-marker']"
    agent-browser is visible "[data-testid^='route-polyline']"
    agent-browser is visible "[data-testid='show-routes-toggle']"
    agent-browser screenshot screenshots/map/5b-complete.png
    agent-browser close
    ```
  - **Success:** Routes, home markers, and toggle all visible

- [x] 18. Checkpoint - Phase 5B Complete
  - **Validation:** All Phase 5B tasks complete, routes display correctly
  - **Review:** Pause for user review before continuing to Phase 5C

---

## Phase 5C: Interactive Features (7-9 hours)

### 5C.1 MapFilters Component

- [x] 19.1 Create MapFilters component
  - **Implementation:** Create filter panel with staff checkboxes
  - **Files:** `frontend/src/features/schedule/components/map/MapFilters.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapFilters.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapFilters component with staff filter checkboxes

- [x] 19.2 Add data-testid attributes to MapFilters
  - **Implementation:** Add data-testid="map-filters" and data-testid="staff-filter-{name}"
  - **Files:** `frontend/src/features/schedule/components/map/MapFilters.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MapFilters.tsx
    ```
  - **Success:** data-testid attributes present

- [x] 19.3 Integrate MapFilters with ScheduleMap
  - **Implementation:** Add filter state and connect to marker visibility
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-filters']"
    agent-browser screenshot screenshots/map/5c1-filters.png
    agent-browser close
    ```
  - **Success:** Filter panel visible on map view

- [x] 19.4 Test staff filter functionality
  - **Implementation:** Verify clicking staff filter hides/shows their markers
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid='staff-filter-Viktor']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/5c1-filter-applied.png
    agent-browser close
    ```
  - **Success:** Filtering by staff updates visible markers

- [x] 19.5 **Validate MapFilters renders and works correctly**
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

- [x] 20.1 Create MapInfoWindow component
  - **Implementation:** Create info window showing job details on marker click
  - **Files:** `frontend/src/features/schedule/components/map/MapInfoWindow.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapInfoWindow.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapInfoWindow shows customer name, address, service type, time

- [x] 20.2 Add data-testid to MapInfoWindow
  - **Implementation:** Add data-testid="map-info-window"
  - **Files:** `frontend/src/features/schedule/components/map/MapInfoWindow.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid="map-info-window"' frontend/src/features/schedule/components/map/MapInfoWindow.tsx
    ```
  - **Success:** data-testid attribute present

- [x] 20.3 Integrate MapInfoWindow with marker clicks
  - **Implementation:** Show info window when marker clicked, close on outside click
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid^='map-marker-']"
    agent-browser wait "[data-testid='map-info-window']"
    agent-browser is visible "[data-testid='map-info-window']"
    agent-browser screenshot screenshots/map/5c2-info-window.png
    agent-browser close
    ```
  - **Success:** Info window opens on marker click

- [x] 20.4 **Validate MapInfoWindow renders on marker click**
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

- [x] 21.1 Add hover state to MapMarker
  - **Implementation:** Show tooltip preview on marker hover (200ms delay)
  - **Files:** `frontend/src/features/schedule/components/map/MapMarker.tsx`
  - **Validation:**
    ```bash
    grep -A 5 "onMouseEnter\|onMouseOver" frontend/src/features/schedule/components/map/MapMarker.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** Hover handlers added to marker

- [x] 21.2 Create hover tooltip UI
  - **Implementation:** Small tooltip with customer name, service type, time window
  - **Files:** `frontend/src/features/schedule/components/map/MapMarker.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser hover "[data-testid^='map-marker-']"
    agent-browser wait 300
    agent-browser screenshot screenshots/map/5c3-hover.png
    agent-browser close
    ```
  - **Success:** Tooltip appears on hover

- [x] 21.3 **Validate hover tooltip appears**
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

- [x] 22.1 Integrate MarkerClusterer
  - **Implementation:** Add @googlemaps/markerclusterer for 20+ markers
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    grep -A 5 "MarkerClusterer\|Clusterer" frontend/src/features/schedule/components/map/ScheduleMap.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MarkerClusterer integrated

- [x] 22.2 Configure clustering options
  - **Implementation:** Set gridSize, minimumClusterSize, maxZoom
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    grep -A 10 "cluster" frontend/src/features/schedule/components/map/ScheduleMap.tsx
    ```
  - **Success:** Clustering configured with appropriate thresholds

### 5C.5 MapControls Component

- [x] 23.1 Create MapControls component
  - **Implementation:** Create zoom and fit bounds buttons
  - **Files:** `frontend/src/features/schedule/components/map/MapControls.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapControls.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapControls with zoom and fit bounds buttons

- [x] 23.2 Add data-testid to MapControls
  - **Implementation:** Add data-testid="fit-bounds-btn"
  - **Files:** `frontend/src/features/schedule/components/map/MapControls.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MapControls.tsx
    ```
  - **Success:** data-testid attributes present

- [x] 23.3 Integrate MapControls with ScheduleMap
  - **Implementation:** Add controls to map, wire up fit bounds
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='fit-bounds-btn']"
    agent-browser click "[data-testid='fit-bounds-btn']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/5c5-controls.png
    agent-browser close
    ```
  - **Success:** Fit bounds button works

- [x] 23.4 **Validate MapControls renders and works correctly**
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

- [x] 24.1 Create MapEmptyState component
  - **Implementation:** Create empty state for no jobs, no schedule, all filtered
  - **Files:** `frontend/src/features/schedule/components/map/MapEmptyState.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapEmptyState.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapEmptyState component with appropriate messages

- [x] 24.2 Add data-testid to MapEmptyState
  - **Implementation:** Add data-testid="map-empty-state"
  - **Files:** `frontend/src/features/schedule/components/map/MapEmptyState.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MapEmptyState.tsx
    ```
  - **Success:** data-testid attribute present

- [x] 24.3 Create MapErrorState component
  - **Implementation:** Create error state with retry button
  - **Files:** `frontend/src/features/schedule/components/map/MapErrorState.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapErrorState.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MapErrorState component with retry button

- [x] 24.4 Add data-testid to MapErrorState
  - **Implementation:** Add data-testid="map-error-state"
  - **Files:** `frontend/src/features/schedule/components/map/MapErrorState.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MapErrorState.tsx
    ```
  - **Success:** data-testid attribute present

- [x] 24.5 Create MissingCoordsWarning component
  - **Implementation:** Warning banner for jobs without coordinates
  - **Files:** `frontend/src/features/schedule/components/map/MissingCoordsWarning.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MissingCoordsWarning.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** Warning component shows count of jobs missing coordinates

- [x] 24.6 Add data-testid to MissingCoordsWarning
  - **Implementation:** Add data-testid="missing-coords-warning"
  - **Files:** `frontend/src/features/schedule/components/map/MissingCoordsWarning.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid=' frontend/src/features/schedule/components/map/MissingCoordsWarning.tsx
    ```
  - **Success:** data-testid attribute present

- [x] 24.7 Integrate empty/error states in ScheduleMap
  - **Implementation:** Show appropriate state based on data/error conditions
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    grep -A 3 "MapEmptyState\|MapErrorState" frontend/src/features/schedule/components/map/ScheduleMap.tsx
    ```
  - **Success:** Empty and error states integrated

### 5C.7 Loading State

- [x] 25.1 Create MapLoadingState component
  - **Implementation:** Loading spinner for map data
  - **Files:** `frontend/src/features/schedule/components/map/MapLoadingState.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MapLoadingState.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** Loading state component exists

- [x] 25.2 Add data-testid to MapLoadingState
  - **Implementation:** Add data-testid="map-loading"
  - **Files:** `frontend/src/features/schedule/components/map/MapLoadingState.tsx`
  - **Validation:**
    ```bash
    grep 'data-testid="map-loading"' frontend/src/features/schedule/components/map/MapLoadingState.tsx
    ```
  - **Success:** data-testid attribute present

### 5C.8 Mobile Responsive Layout

- [x] 26.1 Create MobileJobSheet component
  - **Implementation:** Bottom sheet for job details on mobile
  - **Files:** `frontend/src/features/schedule/components/map/MobileJobSheet.tsx`
  - **Validation:**
    ```bash
    cat frontend/src/features/schedule/components/map/MobileJobSheet.tsx
    cd frontend && npm run typecheck
    ```
  - **Success:** MobileJobSheet component with swipe-up behavior

- [x] 26.2 Add responsive breakpoints to ScheduleMap
  - **Implementation:** Collapse filters on tablet, use bottom sheet on mobile
  - **Files:** `frontend/src/features/schedule/components/map/ScheduleMap.tsx`
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser set viewport 768 1024
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser screenshot screenshots/map/5c8-tablet.png
    agent-browser set viewport 375 667
    agent-browser wait 500
    agent-browser screenshot screenshots/map/5c8-mobile.png
    agent-browser close
    ```
  - **Success:** Layout adapts to tablet and mobile viewports

- [x] 26.3 **Validate mobile responsive layout**
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

- [x] 27.1 Run all frontend quality checks
  - **Implementation:** Ensure all Phase 5C code passes quality checks
  - **Validation:**
    ```bash
    cd frontend && npm run lint
    cd frontend && npm run typecheck
    cd frontend && npm test -- --run
    ```
  - **Success:** Zero errors, all tests pass

- [x] 27.2 Run backend quality checks
  - **Implementation:** Ensure all backend changes still pass
  - **Validation:**
    ```bash
    uv run ruff check src/
    uv run mypy src/
    uv run pytest src/grins_platform/tests/ -v --tb=short
    ```
  - **Success:** Zero errors, all tests pass

### 5C.10 Final Visual Validation

- [x] 28.1 Complete map view validation
  - **Implementation:** Full visual validation of all map features
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser snapshot -i
    agent-browser is visible "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='map-legend']"
    agent-browser is visible "[data-testid='map-filters']"
    agent-browser is visible "[data-testid='show-routes-toggle']"
    agent-browser is visible "[data-testid='fit-bounds-btn']"
    agent-browser screenshot screenshots/map/5c-complete.png
    agent-browser close
    ```
  - **Success:** All map components visible and functional

- [x] 28.2 Test marker click flow
  - **Implementation:** Validate info window opens on marker click
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid^='map-marker-']"
    agent-browser wait "[data-testid='map-info-window']"
    agent-browser is visible "[data-testid='map-info-window']"
    agent-browser screenshot screenshots/map/5c-info-window-final.png
    agent-browser press Escape
    agent-browser wait 300
    agent-browser close
    ```
  - **Success:** Info window opens and closes correctly

- [x] 28.3 Test filter flow
  - **Implementation:** Validate staff filter updates markers
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid='staff-filter-Viktor']"
    agent-browser wait 500
    agent-browser screenshot screenshots/map/5c-filter-final.png
    agent-browser close
    ```
  - **Success:** Filter updates visible markers

- [x] 28.4 Test view toggle persistence
  - **Implementation:** Validate switching views preserves date selection
  - **Validation:**
    ```bash
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser click "[data-testid='view-toggle-list']"
    agent-browser wait "[data-testid='schedule-results']"
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser screenshot screenshots/map/5c-toggle-final.png
    agent-browser close
    ```
  - **Success:** View toggle works smoothly without data loss

- [x] 29. Checkpoint - Phase 5C Complete
  - **Validation:** All Phase 5C tasks complete, interactive features working
  - **Review:** Pause for user review

---

## Phase 5 Completion

- [x] 30.1 Create screenshots directory
  - **Implementation:** Ensure screenshots/map directory exists
  - **Validation:**
    ```bash
    mkdir -p screenshots/map
    ls screenshots/map/
    ```
  - **Success:** Directory exists

- [x] 30.2 Final end-to-end validation
  - **Implementation:** Complete user journey validation
  - **Validation:**
    ```bash
    echo "🗺️ Phase 5 Map Interface - Final Validation"
    echo "============================================"
    
    agent-browser open http://localhost:5173/schedule/generate
    agent-browser wait --load networkidle
    
    echo "Step 1: Verify list view loads"
    agent-browser is visible "[data-testid='schedule-results']"
    
    echo "Step 2: Switch to map view"
    agent-browser click "[data-testid='view-toggle-map']"
    agent-browser wait "[data-testid='schedule-map']"
    agent-browser is visible "[data-testid='schedule-map']"
    
    echo "Step 3: Verify markers visible"
    agent-browser is visible "[data-testid^='map-marker-']"
    
    echo "Step 4: Verify routes visible"
    agent-browser is visible "[data-testid^='route-polyline-']"
    
    echo "Step 5: Verify legend visible"
    agent-browser is visible "[data-testid='map-legend']"
    
    echo "Step 6: Test info window"
    agent-browser click "[data-testid^='map-marker-']"
    agent-browser wait "[data-testid='map-info-window']"
    agent-browser is visible "[data-testid='map-info-window']"
    
    echo "Step 7: Test filter"
    agent-browser press Escape
    agent-browser click "[data-testid='staff-filter-Viktor']"
    agent-browser wait 500
    
    echo "Step 8: Test fit bounds"
    agent-browser click "[data-testid='fit-bounds-btn']"
    agent-browser wait 500
    
    agent-browser screenshot screenshots/map/phase5-final.png
    agent-browser close
    
    echo "✅ Phase 5 Map Interface - VALIDATION COMPLETE"
    ```
  - **Success:** All validation steps pass

- [x] 30.3 Update DEVLOG with Phase 5 completion
  - **Implementation:** Add comprehensive DEVLOG entry for Phase 5
  - **Files:** `DEVLOG.md`
  - **Validation:**
    ```bash
    grep -A 5 "Phase 5" DEVLOG.md | head -20
    ```
  - **Success:** DEVLOG updated with Phase 5 summary

- [x] 31. Checkpoint - Phase 5 Complete
  - **Validation:** All Phase 5 tasks complete, map interface fully functional
  - **Review:** Final review before marking spec complete

---

## Summary

### Task Count by Phase
| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| Setup | 3 | 0.5 |
| 5A: Basic Map | 15 | 5-7 |
| 5B: Routes | 11 | 4-6 |
| 5C: Interactive | 17 | 7-9 |
| Completion | 4 | 1 |
| **Total** | **50** | **14-20** |

### Files Created/Modified
**Backend:**
- `src/grins_platform/schemas/schedule_generation.py` (modified)
- `src/grins_platform/services/schedule_generation_service.py` (modified)
- `src/grins_platform/tests/test_schedule_generation_schemas.py` (modified)

**Frontend:**
- `frontend/src/features/schedule/types/index.ts` (modified)
- `frontend/src/features/schedule/types/map.ts` (new)
- `frontend/src/features/schedule/utils/staffColors.ts` (new)
- `frontend/src/features/schedule/utils/mapStyles.ts` (new)
- `frontend/src/features/schedule/hooks/useMapData.ts` (new)
- `frontend/src/features/schedule/hooks/useMapBounds.ts` (new)
- `frontend/src/features/schedule/components/ScheduleGenerationPage.tsx` (modified)
- `frontend/src/features/schedule/components/map/index.ts` (new)
- `frontend/src/features/schedule/components/map/MapProvider.tsx` (new)
- `frontend/src/features/schedule/components/map/ScheduleMap.tsx` (new)
- `frontend/src/features/schedule/components/map/MapMarker.tsx` (new)
- `frontend/src/features/schedule/components/map/StaffHomeMarker.tsx` (new)
- `frontend/src/features/schedule/components/map/RoutePolyline.tsx` (new)
- `frontend/src/features/schedule/components/map/MapInfoWindow.tsx` (new)
- `frontend/src/features/schedule/components/map/MapLegend.tsx` (new)
- `frontend/src/features/schedule/components/map/MapFilters.tsx` (new)
- `frontend/src/features/schedule/components/map/MapControls.tsx` (new)
- `frontend/src/features/schedule/components/map/MapEmptyState.tsx` (new)
- `frontend/src/features/schedule/components/map/MapErrorState.tsx` (new)
- `frontend/src/features/schedule/components/map/MapLoadingState.tsx` (new)
- `frontend/src/features/schedule/components/map/MissingCoordsWarning.tsx` (new)
- `frontend/src/features/schedule/components/map/MobileJobSheet.tsx` (new)

### Checkpoints
1. **Task 11:** Phase 5A Complete - Basic map with markers and legend
2. **Task 18:** Phase 5B Complete - Routes and home markers
3. **Task 29:** Phase 5C Complete - Interactive features
4. **Task 31:** Phase 5 Complete - Full map interface
