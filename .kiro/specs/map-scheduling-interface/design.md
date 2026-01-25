# Map-Based Scheduling Interface - Design

## Architecture Overview

### Component Hierarchy

```
ScheduleGenerationPage (existing)
├── PageHeader
├── DatePicker + Generate/Preview buttons
├── CapacityOverview
├── ViewToggle [List | Map]  ← NEW
│
├── [If List View]
│   └── ScheduleResults (existing)
│
└── [If Map View]  ← NEW
    └── MapProvider
        └── ScheduleMapContainer
            ├── MapFilters (sidebar)
            │   ├── StaffFilterList
            │   ├── ShowRoutesToggle
            │   └── FitBoundsButton
            │
            ├── ScheduleMap
            │   ├── RoutePolyline[] (Layer 1 - bottom)
            │   ├── StaffHomeMarker[] (Layer 2)
            │   ├── MapMarker[] (Layer 3)
            │   └── MapInfoWindow (Layer 4 - top)
            │
            ├── MapLegend
            └── MobileJobSheet (mobile only)
```

## File Structure

```
frontend/src/features/schedule/
├── components/
│   ├── ScheduleGenerationPage.tsx    # MODIFY - add view toggle
│   ├── ScheduleResults.tsx           # EXISTING - no changes
│   │
│   └── map/                          # NEW DIRECTORY
│       ├── index.ts                  # Barrel exports
│       ├── MapProvider.tsx           # Google Maps API wrapper
│       ├── ScheduleMap.tsx           # Main map container
│       ├── ScheduleMapContainer.tsx  # Layout with filters + map
│       ├── MapMarker.tsx             # Job marker with sequence
│       ├── StaffHomeMarker.tsx       # Staff home location
│       ├── RoutePolyline.tsx         # Route line component
│       ├── MapInfoWindow.tsx         # Job details popup
│       ├── MapLegend.tsx             # Staff color legend
│       ├── MapFilters.tsx            # Filter sidebar
│       ├── MapControls.tsx           # Zoom, fit bounds
│       ├── MapEmptyState.tsx         # Empty/error states
│       └── MobileJobSheet.tsx        # Mobile bottom sheet
│
├── hooks/
│   ├── useScheduleGeneration.ts      # EXISTING
│   ├── useMapData.ts                 # NEW - Combined map data hook
│   └── useMapBounds.ts               # NEW - Auto-fit bounds
│
├── utils/
│   ├── staffColors.ts                # NEW - Color mapping
│   ├── mapStyles.ts                  # NEW - Google Maps styling
│   └── markerIcons.ts                # NEW - SVG marker generation
│
└── types/
    ├── index.ts                      # EXISTING
    └── map.ts                        # NEW - Map-specific types
```

## Backend Changes

### Schema Updates

**File: `src/grins_platform/schemas/schedule_generation.py`**

```python
class ScheduleJobAssignment(BaseModel):
    """A job assignment in the generated schedule."""
    job_id: UUID
    customer_name: str
    address: str | None = None
    city: str | None = None
    latitude: float | None = None      # ADD
    longitude: float | None = None     # ADD
    service_type: str
    start_time: time
    end_time: time
    duration_minutes: int
    travel_time_minutes: int
    sequence_index: int

class ScheduleStaffAssignment(BaseModel):
    """Staff assignment with their jobs for the day."""
    staff_id: UUID
    staff_name: str
    start_lat: float | None = None     # ADD
    start_lng: float | None = None     # ADD
    jobs: list[ScheduleJobAssignment] = Field(default_factory=list)
    total_jobs: int = 0
    total_travel_minutes: int = 0
    first_job_start: time | None = None
    last_job_end: time | None = None
```

**File: `src/grins_platform/schemas/map.py`** (NEW)

```python
from datetime import date, time, datetime
from uuid import UUID
from pydantic import BaseModel, Field

class MapUnscheduledJob(BaseModel):
    """Unscheduled job for map display."""
    job_id: UUID
    customer_name: str
    address: str
    city: str
    latitude: float | None
    longitude: float | None
    service_type: str
    zone_count: int | None = None
    priority_level: int = 0

class UnscheduledJobsResponse(BaseModel):
    """Response for unscheduled jobs endpoint."""
    date: date
    jobs: list[MapUnscheduledJob] = Field(default_factory=list)
    total: int = 0
    missing_coordinates: int = 0
```

### Service Updates

**File: `src/grins_platform/services/schedule_generation_service.py`**

Update `_build_response` method (~line 326) to include coordinates:

```python
for slot in slots:
    job_assignments.append(ScheduleJobAssignment(
        job_id=slot.job.id,
        customer_name=slot.job.customer_name,
        address=slot.job.location.address,
        city=slot.job.location.city,
        latitude=float(slot.job.location.latitude) if slot.job.location.latitude else None,
        longitude=float(slot.job.location.longitude) if slot.job.location.longitude else None,
        service_type=slot.job.service_type,
        start_time=slot.start_time,
        end_time=slot.end_time,
        duration_minutes=slot.job.duration_minutes,
        travel_time_minutes=slot.travel_time_from_previous,
        sequence_index=slot.sequence_index,
    ))
```

Update staff assignment to include start location:

```python
assignments.append(ScheduleStaffAssignment(
    staff_id=assignment.staff.id,
    staff_name=assignment.staff.name,
    start_lat=float(assignment.staff.start_location.latitude) if assignment.staff.start_location.latitude else None,
    start_lng=float(assignment.staff.start_location.longitude) if assignment.staff.start_location.longitude else None,
    jobs=job_assignments,
    # ... rest unchanged
))
```

### New API Endpoint

**File: `src/grins_platform/api/v1/map.py`** (NEW)

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date

from grins_platform.api.dependencies import get_db
from grins_platform.schemas.map import UnscheduledJobsResponse, MapUnscheduledJob
from grins_platform.models.job import Job
from grins_platform.models.enums import JobStatus

router = APIRouter(prefix="/map", tags=["map"])

@router.get("/unscheduled-jobs", response_model=UnscheduledJobsResponse)
def get_unscheduled_jobs(
    target_date: date = Query(..., description="Date to check"),
    db: Session = Depends(get_db),
) -> UnscheduledJobsResponse:
    """Get approved jobs not yet scheduled."""
    # Implementation details in tasks
    pass
```

## Frontend Types

**File: `frontend/src/features/schedule/types/map.ts`** (NEW)

```typescript
export interface MapJob {
  job_id: string;
  customer_name: string;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  service_type: string;
  staff_id: string | null;
  staff_name: string | null;
  sequence_index: number | null;
  start_time: string | null;
  end_time: string | null;
  travel_time_minutes: number | null;
}

export interface MapRoute {
  staff_id: string;
  staff_name: string;
  color: string;
  start_location: { lat: number; lng: number };
  waypoints: Array<{
    lat: number;
    lng: number;
    job_id: string;
    sequence: number;
  }>;
  total_jobs: number;
  total_travel_minutes: number;
}

export interface MapUnscheduledJob {
  job_id: string;
  customer_name: string;
  address: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
  service_type: string;
  zone_count: number | null;
  priority_level: number;
}

export type MapMode = 'planning' | 'scheduled';
export type ViewMode = 'list' | 'map';

export interface MapFilters {
  staffIds: string[];
  showRoutes: boolean;
  mode: MapMode;
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}
```

## Staff Color System

**File: `frontend/src/features/schedule/utils/staffColors.ts`**

```typescript
export const STAFF_COLORS: Record<string, string> = {
  'Viktor': '#EF4444',    // Red
  'Vas': '#3B82F6',       // Blue
  'Dad': '#22C55E',       // Green
  'Gennadiy': '#22C55E',  // Green (alias)
  'Steven': '#F59E0B',    // Amber
  'Vitallik': '#8B5CF6',  // Purple
};

export const UNASSIGNED_COLOR = '#6B7280'; // Gray
export const DEFAULT_COLOR = '#9CA3AF';    // Light gray for unknown

export function getStaffColor(staffName: string): string {
  return STAFF_COLORS[staffName] || DEFAULT_COLOR;
}
```

## Map Styling

**File: `frontend/src/features/schedule/utils/mapStyles.ts`**

```typescript
export const MAP_STYLES: google.maps.MapTypeStyle[] = [
  // Hide POIs
  { featureType: 'poi', elementType: 'all', stylers: [{ visibility: 'off' }] },
  // Muted roads
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#E5E7EB' }] },
  // Soft water
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#DBEAFE' }] },
  // Light parks
  { featureType: 'landscape.natural', elementType: 'geometry', stylers: [{ color: '#DCFCE7' }] },
];

export const DEFAULT_CENTER = { lat: 44.8547, lng: -93.4708 }; // Twin Cities
export const DEFAULT_ZOOM = 10;

export const MAP_OPTIONS: google.maps.MapOptions = {
  styles: MAP_STYLES,
  disableDefaultUI: true,
  zoomControl: true,
  mapTypeControl: false,
  streetViewControl: false,
  fullscreenControl: false,
};
```

## Data-TestId Conventions

| Component | TestId Pattern |
|-----------|----------------|
| Map container | `schedule-map` |
| View toggle (list) | `view-toggle-list` |
| View toggle (map) | `view-toggle-map` |
| Mode toggle (planning) | `mode-toggle-planning` |
| Mode toggle (scheduled) | `mode-toggle-scheduled` |
| Job marker | `map-marker-{job_id}` |
| Unscheduled marker | `map-marker-unscheduled-{job_id}` |
| Staff home marker | `staff-home-marker-{staff_id}` |
| Route polyline | `route-polyline-{staff_id}` |
| Info window | `map-info-window` |
| Legend | `map-legend` |
| Filter panel | `map-filters` |
| Staff filter checkbox | `staff-filter-{name}` |
| Show routes toggle | `show-routes-toggle` |
| Fit bounds button | `fit-bounds-btn` |
| Loading state | `map-loading` |
| Empty state | `map-empty-state` |
| Error state | `map-error-state` |
| Missing coords warning | `missing-coords-warning` |

## Component Specifications

### MapProvider

Wraps the application with Google Maps API context.

```typescript
interface MapProviderProps {
  children: React.ReactNode;
}
```

### ScheduleMap

Main map component that renders all layers.

```typescript
interface ScheduleMapProps {
  jobs: MapJob[];
  routes: MapRoute[];
  selectedJobId: string | null;
  onJobSelect: (jobId: string | null) => void;
  showRoutes: boolean;
  filters: MapFilters;
}
```

### MapMarker

Individual job marker with sequence number.

```typescript
interface MapMarkerProps {
  job: MapJob;
  isSelected: boolean;
  onClick: () => void;
  onHover: (hovering: boolean) => void;
}
```

### MapInfoWindow

Job details popup.

```typescript
interface MapInfoWindowProps {
  job: MapJob;
  onClose: () => void;
}
```

### MapFilters

Filter sidebar component.

```typescript
interface MapFiltersProps {
  staffList: Array<{ id: string; name: string; jobCount: number }>;
  selectedStaffIds: string[];
  onStaffToggle: (staffId: string) => void;
  showRoutes: boolean;
  onShowRoutesToggle: () => void;
  onFitBounds: () => void;
}
```

## API Integration

### Frontend Type Updates

**File: `frontend/src/features/schedule/types/index.ts`**

Add to existing `ScheduleJobAssignment`:
```typescript
export interface ScheduleJobAssignment {
  // ... existing fields
  latitude: number | null;      // ADD
  longitude: number | null;     // ADD
}

export interface ScheduleStaffAssignment {
  // ... existing fields
  start_lat: number | null;     // ADD
  start_lng: number | null;     // ADD
}
```

### New API Hook

**File: `frontend/src/features/schedule/hooks/useMapData.ts`**

```typescript
export function useMapData(date: string, scheduleData: ScheduleGenerateResponse | null) {
  // Transform schedule data into map-friendly format
  // Returns: { jobs, routes, unscheduledJobs, isLoading, error }
}
```

## Error States

### Missing Coordinates
- Show warning banner at top of map
- List affected jobs with links
- Jobs without coordinates excluded from map

### API Failure
- Show error message in map area
- "Retry" button
- Show cached data if available

### No Jobs
- Show empty state with message
- Date navigation buttons
- Map still visible (centered on Twin Cities)

## Mobile Considerations

### Breakpoints
- Desktop: > 1024px (sidebar + map)
- Tablet: 768-1024px (collapsible filters)
- Mobile: < 768px (bottom sheet for details)

### Touch Interactions
- Tap marker to select (no hover)
- Swipe up bottom sheet for details
- Pinch to zoom
- 44px minimum tap targets

## Performance Considerations

### Marker Clustering
- Enable when > 20 markers visible
- Cluster at zoom levels < 14
- Show count in cluster icon

### Data Loading
- Fetch all jobs for date on initial load
- Filter client-side (no API calls)
- Lazy load routes (only when toggle enabled)

### Rendering
- Use React.memo for markers
- Debounce filter changes (200ms)
- Virtualize marker list if > 100 jobs

## Correctness Properties

### P1: Coordinate Passthrough
All jobs with coordinates in the database must have those coordinates available in the API response.

### P2: Staff Color Consistency
The same staff member must always have the same color across all views and sessions.

### P3: Route Sequence Integrity
Route polylines must connect jobs in the exact sequence order returned by the schedule generation.

### P4: Filter Isolation
Filtering by staff must only affect marker visibility, not the underlying data or other UI elements.

### P5: Bounds Calculation
Auto-fit bounds must include all visible markers with appropriate padding.
