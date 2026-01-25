# Phase 5: Map-Based Scheduling Interface

**Date:** January 24, 2026  
**Status:** Planning  
**Scope:** Full (5A + 5B + 5C) - ~14-20 hours  
**Focus:** Google Maps visualization for schedule management and route optimization  
**Research:** See `phase5-map-ui-design-research.md` for detailed competitor analysis

---

## Executive Summary

Phase 5 implements a Google Maps-based interface that allows Viktor to visualize customer locations, job assignments, and optimized routes on an interactive map. This transforms the schedule generation experience from a text-based list view to a visual, geographic interface.

### Business Value
- **Visual Context:** See all jobs geographically instead of as a list
- **Route Verification:** Visually confirm routes make geographic sense
- **Quick Assessment:** Instantly identify clustering opportunities and outliers
- **Pre-Schedule Planning:** See unscheduled jobs on map BEFORE generating to understand geographic spread
- **Customer Communication:** Show customers their technician's route/ETA visually

### Why Map Interface Now?

1. **Foundation Complete:** Phase 4A built all the data we need (coordinates, routes, travel times)
2. **Natural Extension:** Schedule generation already calculates routes - now visualize them
3. **Viktor's Vision:** From PHASE-4-PLANNING-ADDONS.md - "Staff will have a clear understanding of their route that day"
4. **Competitive Advantage:** Visual route management is a premium feature in competitors

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Route Lines** | Straight-line polylines | FREE vs $5/1000 for Directions API |
| **Marker Clustering** | Essential for 20+ jobs | Performance + clean UI |
| **Base Map Style** | Clean, minimal, brand-matched | Reduces cognitive load (Airbnb pattern) |
| **Mobile Layout** | Bottom sheet for job details | Tablet-friendly for dispatchers |
| **Layer Management** | Uber's sandbox pattern | Prevents feature conflicts |
| **Staff Colors** | Hardcoded per staff name | Simple, consistent, no DB changes |
| **Default Date** | Today | Most common use case |
| **Planning Mode** | Show unscheduled jobs | Visualize before generating |

---

## Map Modes

The map supports two distinct modes to cover the full scheduling workflow:

### Planning Mode (Before Schedule Generation)

**Purpose:** Visualize unscheduled jobs to understand geographic spread before generating routes.

```
┌─────────────────────────────────────────────────────────────────┐
│  📅 Today (Jan 24)  │  Mode: [Planning ✓] [Scheduled]          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        Google Map                                │
│                                                                  │
│         ⚫ Unscheduled job (gray, pulsing)                      │
│         ⚫ Unscheduled job                                       │
│         ⚫ Unscheduled job                                       │
│         ⚫ Unscheduled job                                       │
│                                                                  │
│  No routes shown - jobs not yet assigned                        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  📊 12 unscheduled jobs for today                               │
│  [Generate Schedule →]                                          │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- All unscheduled jobs shown as gray pulsing markers
- No routes (jobs not assigned yet)
- Job count summary
- Quick "Generate Schedule" button
- Helps identify geographic clusters before optimization

### Schedule Mode (After Schedule Generation)

**Purpose:** Visualize generated routes with staff assignments and sequences.

```
┌─────────────────────────────────────────────────────────────────┐
│  📅 Today (Jan 24)  │  Mode: [Planning] [Scheduled ✓]          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        Google Map                                │
│                                                                  │
│         🏠 Viktor ─── ❶ ─── ❷ ─── ❸                            │
│                                                                  │
│         🏠 Vas ─── ❶ ─── ❷                                      │
│                                                                  │
│         ⚫ Unassigned job (if any remain)                       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Legend: 🔴 Viktor (5)  🔵 Vas (8)  🟢 Dad (6)  ⚫ Unassigned (1)│
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- Staff-colored markers with sequence numbers
- Route polylines connecting jobs in order
- Staff home locations shown
- Unassigned jobs still visible (gray, pulsing)
- Filter by staff member

### Mode Switching

- **Default:** Planning mode if no schedule exists for date, Schedule mode if one does
- **Toggle:** User can switch between modes to compare before/after
- **Auto-switch:** After generating schedule, automatically switch to Schedule mode

---

## Identified Improvements

Based on codebase analysis, here are all improvements needed:

### Critical Data Gaps (Must Fix)

| Gap | Current State | Required Change |
|-----|---------------|-----------------|
| **Job coordinates missing** | `ScheduleJobAssignment` has `address` but no `lat/lng` | Add `latitude`, `longitude` to schema |
| **Staff start location missing** | `ScheduleStaffAssignment` has no start coordinates | Add `start_lat`, `start_lng` to schema |
| **Unscheduled jobs endpoint** | No way to fetch approved-but-unscheduled jobs | Create `GET /api/v1/map/unscheduled-jobs` |

### UX Enhancements (Nice to Have)

| Enhancement | Description | Phase |
|-------------|-------------|-------|
| **Job type icons** | Different icons: 🌱 Startup, ❄️ Winterize, 🔧 Repair | 5A |
| **Priority indicators** | ⚡ High, 🚨 Urgent badges on markers | 5A |
| **Route statistics** | Total drive time, longest segment, efficiency ratio | 5B |
| **Distance labels** | "12 min" labels on route segments | 5B |
| **Time window colors** | Morning=light, afternoon=dark marker intensity | 5C |
| **Quick date nav** | ← Previous \| Today \| Next → buttons | 5C |
| **Staff availability** | Gray out unavailable staff in legend | 5C |
| **Weather sensitivity** | ☀️ icon for weather-sensitive jobs | 5C |
| **Route animation** | Animate route drawing to show sequence | 5D |

### Error Handling

| Scenario | Handling |
|----------|----------|
| **Missing coordinates** | Warning banner: "3 jobs missing coordinates" with list |
| **API failure** | Show error message, retry button, cached data if available |
| **No jobs for date** | Empty state with date navigation |
| **All filtered out** | "No matching jobs" with clear filters button |

### Performance Optimizations

| Optimization | Description |
|--------------|-------------|
| **Lazy load routes** | Don't fetch routes until "Show Routes" toggled |
| **Debounced filters** | 200ms delay before applying filter changes |
| **Marker virtualization** | Only render visible markers (for 100+ jobs) |

### Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Keyboard navigation** | Tab through markers, Enter to select, Escape to close |
| **Screen reader** | ARIA labels on all markers, live region for updates |
| **Color + icon** | Never rely on color alone (always include number/icon) |
| **Focus indicators** | Visible focus ring on all interactive elements |

---

## Backend Schema Updates Required

### Update: ScheduleJobAssignment

```python
class ScheduleJobAssignment(BaseModel):
    """A job assignment in the generated schedule."""
    job_id: UUID
    customer_name: str
    address: str | None = None
    city: str | None = None
    latitude: float | None = None      # NEW
    longitude: float | None = None     # NEW
    service_type: str
    start_time: time
    end_time: time
    duration_minutes: int
    travel_time_minutes: int
    sequence_index: int
    priority_level: int = 0            # NEW
    weather_sensitive: bool = False    # NEW
    zone_count: int | None = None      # NEW
```

### Update: ScheduleStaffAssignment

```python
class ScheduleStaffAssignment(BaseModel):
    """Staff assignment with their jobs for the day."""
    staff_id: UUID
    staff_name: str
    start_lat: float | None = None     # NEW
    start_lng: float | None = None     # NEW
    jobs: list[ScheduleJobAssignment] = Field(default_factory=list)
    total_jobs: int = 0
    total_travel_minutes: int = 0
    first_job_start: time | None = None
    last_job_end: time | None = None
```

### New: UnscheduledJobsResponse

```python
class MapUnscheduledJob(BaseModel):
    """Unscheduled job for map display."""
    job_id: UUID
    customer_name: str
    address: str
    city: str
    latitude: float | None
    longitude: float | None
    service_type: str
    zone_count: int | None
    priority_level: int
    weather_sensitive: bool
    requested_at: datetime

class UnscheduledJobsResponse(BaseModel):
    """Response for unscheduled jobs endpoint."""
    date: date
    jobs: list[MapUnscheduledJob]
    total: int
    missing_coordinates: int
```

---

## Current State Analysis

### What We Have ✅

| Component | Status | Details |
|-----------|--------|---------|
| **Property Coordinates** | ✅ Complete | `latitude`, `longitude` fields on Property model |
| **Staff Starting Locations** | ✅ Complete | `default_start_lat`, `default_start_lng` on Staff |
| **Schedule Generation** | ✅ Complete | Returns assignments with job sequences |
| **Travel Time Service** | ✅ Complete | Google Maps Distance Matrix API integrated |
| **Route Optimization** | ✅ Complete | Jobs ordered by optimized route per staff |
| **Schedule Generation UI** | ✅ Complete | Date picker, generate button, results list |

### What's Missing for Map View

| Gap | Description | Priority |
|-----|-------------|----------|
| **Map Component** | Google Maps React integration | 🔴 Critical |
| **Custom Markers** | Staff-colored numbered markers | 🔴 Critical |
| **Route Polylines** | Straight-line routes on map | 🔴 Critical |
| **Staff Color Coding** | Consistent color palette | 🔴 Critical |
| **Info Windows** | Job details on click | 🟡 Important |
| **Interactive Filters** | Filter by date, staff, status | 🟡 Important |
| **Marker Clustering** | Performance for many jobs | 🟡 Important |
| **Mobile Responsiveness** | Bottom sheet pattern | 🟡 Important |

---

## Design System

### Staff Color Palette

Based on research, using high-contrast, accessible colors:

| Staff Member | Color | Hex Code | Usage |
|--------------|-------|----------|-------|
| Viktor | Red | `#EF4444` | Markers, routes, legend |
| Vas | Blue | `#3B82F6` | Markers, routes, legend |
| Dad (Gennadiy) | Green | `#22C55E` | Markers, routes, legend |
| Steven | Amber | `#F59E0B` | Markers, routes, legend |
| Vitallik | Purple | `#8B5CF6` | Markers, routes, legend |
| Unassigned | Gray | `#6B7280` | Pulsing animation to draw attention |

### Custom Marker Design

```
Staff Home Marker:          Job Marker (with sequence):
┌─────────┐                 ┌─────────┐
│   🏠    │                 │    1    │  ← Sequence number
│ ─────── │                 │ ─────── │
│  [Name] │                 │  [Color │  ← Staff color ring
└─────────┘                 │   Ring] │
                            └─────────┘
```

**Marker States:**
- **Default:** Staff color with sequence number
- **Hover:** Slight scale up (1.1x) + shadow
- **Selected:** Larger scale (1.2x) + info window open
- **Unassigned:** Gray with pulsing animation

### Info Window Design

**Full Info Window (on click):**
```
┌─────────────────────────────────────┐
│  John Smith                    🔴   │  ← Staff color indicator
│  📍 123 Oak Lane, Eden Prairie      │
│  🔧 Spring Startup (6 zones)        │
│  ⏰ 9:00 AM - 11:00 AM             │
│  📍 Route Stop #2                   │
│  🚗 ~12 min from previous          │
│                                     │
│  [View Details]  [Reassign ▼]       │
└─────────────────────────────────────┘
```

**Hover Preview (quick glance):**
```
┌─────────────────────────┐
│  John Smith             │
│  Spring Startup · 6z    │
│  9:00 AM - 11:00 AM    │
└─────────────────────────┘
```

### Map Base Styling

Using SnazzyMaps-inspired clean style:
- **Roads:** Muted gray (`#E5E7EB`)
- **Water:** Soft blue (`#DBEAFE`)
- **Parks:** Light green (`#DCFCE7`)
- **Labels:** Minimal, only major roads/cities
- **POIs:** Hidden (reduce clutter)

---

## Responsive Layouts

### Desktop Layout (>1024px)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Generate Schedule                                                    │
│  Optimize routes and generate schedules for field staff              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │ 📅 Jan 27    │  │ [Generate]   │  │  [📋 List] [🗺️ Map ✓]      │ │
│  └──────────────┘  │ [Preview]    │  └─────────────────────────────┘ │
│                    └──────────────┘                                   │
│                                                                       │
│  ┌────────────────────┬──────────────────────────────────────────┐   │
│  │  Filter Panel      │                                          │   │
│  │  (250px)           │              Google Map                  │   │
│  │                    │              (Remaining Width)           │   │
│  │  Staff Members     │                                          │   │
│  │  ☑️ Viktor (5)     │         🏠 Viktor Start                  │   │
│  │  ☑️ Vas (8)        │            │                             │   │
│  │  ☑️ Dad (6)        │            ├── ❶ Eden Prairie            │   │
│  │  ☐ Steven (0)      │            │                             │   │
│  │                    │            ├── ❷ Eden Prairie            │   │
│  │  Job Status        │            │                             │   │
│  │  [All ▼]           │            └── ❸ Plymouth                │   │
│  │                    │                                          │   │
│  │  ☑️ Show Routes    │         🏠 Vas Start                     │   │
│  │  [Fit Bounds]      │            │                             │   │
│  │                    │            ├── ❶ Maple Grove             │   │
│  │                    │            │                             │   │
│  │                    │            └── ❷ Brooklyn Park           │   │
│  └────────────────────┴──────────────────────────────────────────┘   │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Legend: 🔴 Viktor (5 jobs)  🔵 Vas (8 jobs)  🟢 Dad (6 jobs)  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Tablet Layout (768-1024px)

```
┌─────────────────────────────────────────────────────────────────┐
│  Generate Schedule                                               │
├─────────────────────────────────────────────────────────────────┤
│  [📅 Jan 27]  [Generate]  [Preview]  [📋|🗺️]  [Filters ▼]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        Google Map                                │
│                        (Full Width)                              │
│                                                                  │
│         🏠 Viktor ─── ❶ ─── ❷ ─── ❸                            │
│                                                                  │
│         🏠 Vas ─── ❶ ─── ❷                                      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Legend: 🔴 Viktor (5)  🔵 Vas (8)  🟢 Dad (6)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile Layout (<768px)

```
┌─────────────────────────────────────────────────────────────────┐
│  [☰]  Generate Schedule  [🔍]                                   │
├─────────────────────────────────────────────────────────────────┤
│  [📅 Jan 27 ▼]  [📋|🗺️]                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                        Google Map                                │
│                        (Full Screen)                             │
│                                                                  │
│         🏠 ─── ❶ ─── ❷ ─── ❸                                   │
│                                                                  │
│         🏠 ─── ❶ ─── ❷                                          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  ═══════════════════════════════════════════════════    │    │  ← Drag handle
│  │  John Smith · Spring Startup                            │    │
│  │  9:00 AM - 11:00 AM · Route #2                         │    │
│  │                                                         │    │
│  │  [View Details]  [Call]  [Navigate]                     │    │
│  │                                                         │    │
│  │  ↑ Swipe up for more details                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Component Structure

```
frontend/src/features/schedule/
├── components/
│   ├── ScheduleGenerationPage.tsx    # Existing - add map toggle
│   ├── ScheduleResults.tsx           # Existing - list view
│   │
│   │   # NEW Map Components
│   ├── map/
│   │   ├── ScheduleMap.tsx           # Main map container
│   │   ├── MapProvider.tsx           # Google Maps API provider
│   │   ├── MapMarker.tsx             # Custom marker with sequence
│   │   ├── StaffHomeMarker.tsx       # Staff starting location
│   │   ├── RoutePolyline.tsx         # Straight-line route
│   │   ├── MapInfoWindow.tsx         # Job details popup
│   │   ├── MapLegend.tsx             # Staff color legend
│   │   ├── MapFilters.tsx            # Filter panel
│   │   ├── MapControls.tsx           # Zoom, recenter buttons
│   │   └── MobileJobSheet.tsx        # Bottom sheet for mobile
│   │
├── hooks/
│   ├── useScheduleGeneration.ts      # Existing
│   ├── useMapJobs.ts                 # NEW - Jobs with coordinates
│   ├── useMapRoutes.ts               # NEW - Route polyline data
│   └── useMapBounds.ts               # NEW - Auto-fit bounds
│
├── utils/
│   ├── mapStyles.ts                  # Custom map styling
│   ├── staffColors.ts                # Color palette
│   └── markerIcons.ts                # SVG marker generators
│
└── types/
    └── map.ts                        # Map-specific types
```

### Key Components

**MapProvider.tsx** - Wraps app with Google Maps context:
```typescript
import { LoadScript } from '@react-google-maps/api';

export const MapProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <LoadScript
    googleMapsApiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}
    libraries={['places', 'geometry']}
  >
    {children}
  </LoadScript>
);
```

**ScheduleMap.tsx** - Main map container with layer management:
```typescript
// Uber's Layer Manager pattern - each feature controls only its own elements
const ScheduleMap: React.FC<ScheduleMapProps> = ({ date, filters }) => {
  const { jobs, isLoading } = useMapJobs(date, filters);
  const { routes } = useMapRoutes(date, filters);
  const { bounds, fitBounds } = useMapBounds(jobs);

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={defaultCenter}
      zoom={10}
      options={mapOptions}
    >
      {/* Layer 1: Route polylines (bottom) */}
      {routes.map(route => (
        <RoutePolyline key={route.staff_id} route={route} />
      ))}
      
      {/* Layer 2: Staff home markers */}
      {routes.map(route => (
        <StaffHomeMarker key={route.staff_id} location={route.start_location} />
      ))}
      
      {/* Layer 3: Job markers (top) */}
      {jobs.map(job => (
        <MapMarker key={job.job_id} job={job} />
      ))}
      
      {/* Layer 4: Info window (topmost) */}
      {selectedJob && <MapInfoWindow job={selectedJob} />}
    </GoogleMap>
  );
};
```

---

## Backend API

### New Endpoints

```
GET /api/v1/map/jobs?date={date}&staff_id={staff_id}&status={status}
    Returns jobs with property coordinates for map display

GET /api/v1/map/routes/{date}
    Returns route data for all staff on a date

GET /api/v1/map/staff-locations
    Returns staff starting locations
```

### API Schemas

```python
# src/grins_platform/schemas/map.py

class MapJobResponse(BaseModel):
    """Job data for map display."""
    job_id: UUID
    customer_name: str
    address: str
    city: str
    latitude: float
    longitude: float
    service_type: str
    zone_count: int | None = None
    status: str
    staff_id: UUID | None = None
    staff_name: str | None = None
    staff_color: str | None = None
    sequence_index: int | None = None
    scheduled_start: time | None = None
    scheduled_end: time | None = None
    travel_time_from_previous: int | None = None  # minutes


class MapRouteWaypoint(BaseModel):
    """A waypoint in a route."""
    lat: float
    lng: float
    job_id: UUID
    sequence: int


class MapRouteResponse(BaseModel):
    """Route data for map display."""
    staff_id: UUID
    staff_name: str
    color: str
    job_count: int
    start_location: dict[str, float]  # {lat, lng}
    waypoints: list[MapRouteWaypoint]
    total_travel_time: int  # minutes
    total_work_time: int  # minutes


class MapStaffLocationResponse(BaseModel):
    """Staff starting location for map."""
    staff_id: UUID
    staff_name: str
    latitude: float
    longitude: float
    color: str
```

---

## Phased Implementation

### Phase 5A: Basic Map View (5-7 hours)

**Goal:** Display properties and jobs on Google Maps with custom styling, including Planning Mode

| Task | Description | Effort |
|------|-------------|--------|
| **5A.1** | Install @react-google-maps/api, configure env | 30 min |
| **5A.2** | Create MapProvider with custom map styling | 1 hr |
| **5A.3** | Create ScheduleMap container component | 1.5 hrs |
| **5A.4** | Create MapMarker with staff colors + sequence | 1.5 hrs |
| **5A.5** | Add map/list toggle to ScheduleGenerationPage | 1 hr |
| **5A.6** | Create MapLegend component | 30 min |
| **5A.7** | Add Planning/Schedule mode toggle | 30 min |
| **5A.8** | Create unscheduled job markers (gray, pulsing) | 30 min |

**Deliverable:** Clean map showing all job locations with staff-colored numbered markers, plus Planning Mode for unscheduled jobs

### Phase 5B: Route Visualization (4-6 hours)

**Goal:** Display optimized routes as colored polylines

| Task | Description | Effort |
|------|-------------|--------|
| **5B.1** | Create GET /api/v1/map/routes endpoint | 1.5 hrs |
| **5B.2** | Create RoutePolyline component (straight lines) | 1 hr |
| **5B.3** | Create StaffHomeMarker component | 30 min |
| **5B.4** | Add useMapRoutes hook | 1 hr |
| **5B.5** | Implement auto-fit bounds | 30 min |
| **5B.6** | Add route toggle (show/hide routes) | 30 min |

**Deliverable:** Routes drawn on map with staff colors connecting jobs in sequence

### Phase 5C: Interactive Features (7-9 hours)

**Goal:** Filters, info windows, hover states, empty states, and enhanced UX

| Task | Description | Effort |
|------|-------------|--------|
| **5C.1** | Create MapFilters panel (staff, status) | 1.5 hrs |
| **5C.2** | Create MapInfoWindow with job details | 1.5 hrs |
| **5C.3** | Add hover preview on markers | 1 hr |
| **5C.4** | Add marker clustering for 20+ jobs | 1.5 hrs |
| **5C.5** | Create MapControls (zoom, recenter) | 30 min |
| **5C.6** | Add loading states and error handling | 1 hr |
| **5C.7** | Add empty state components | 30 min |
| **5C.8** | Mobile responsive layout + bottom sheet | 1.5 hrs |

**Deliverable:** Fully interactive map with filters, popups, empty states, and mobile support

### Phase 5D: Advanced Features (Future - 8-10 hours)

**Goal:** Real-time tracking and route editing (defer to later)

| Task | Description | Effort |
|------|-------------|--------|
| **5D.1** | Real-time GPS tracking integration | 3 hrs |
| **5D.2** | "On my way" notifications with live link | 2 hrs |
| **5D.3** | Drag marker to reassign job | 2 hrs |
| **5D.4** | Route reordering via drag | 2 hrs |
| **5D.5** | Live map updates (WebSocket) | 2 hrs |

**Note:** Phase 5D is optional and can be deferred to Phase 6+

---

## Performance Guidelines

### Marker Performance

| Job Count | Strategy |
|-----------|----------|
| < 20 jobs | Show all markers individually |
| 20-50 jobs | Enable clustering when zoomed out |
| 50+ jobs | Mandatory clustering, lazy load routes |

### Clustering Configuration

```typescript
const clusterOptions = {
  gridSize: 60,
  minimumClusterSize: 3,
  maxZoom: 14,  // Uncluster at street level
  styles: [{
    textColor: 'white',
    url: '/cluster-icon.png',
    height: 40,
    width: 40,
    textSize: 14,
  }]
};
```

### Data Loading Strategy

1. **Initial Load:** Fetch jobs for selected date
2. **Date Change:** Clear markers, fetch new data
3. **Filter Change:** Filter client-side (no API call)
4. **Zoom Change:** Adjust clustering level
5. **Pan:** No additional data fetch (all jobs loaded)

---

## Accessibility Checklist

- [ ] Keyboard navigation for map controls (Tab, Enter, Arrow keys)
- [ ] ARIA labels for all markers (`aria-label="Job 1: John Smith, Spring Startup"`)
- [ ] Color + icon/number for staff (not color alone)
- [ ] High contrast mode support
- [ ] Minimum 44px tap targets for mobile
- [ ] Screen reader announcements for state changes
- [ ] Focus indicators for interactive elements
- [ ] Skip link to bypass map for keyboard users

---

## API Cost Analysis

| Component | Monthly Cost | Notes |
|-----------|--------------|-------|
| Maps JavaScript API | **FREE** | First 28,000 loads/month |
| Straight-line polylines | **FREE** | Canvas drawing, no API call |
| Custom markers | **FREE** | SVG/Canvas rendering |
| Distance Matrix (existing) | ~$30-50 | Already in Phase 4A |
| Directions API | **NOT USED** | Would be ~$5/1000 |

**Total Estimated Cost:** ~$30-50/month (no change from Phase 4A)

---

## Competitive Positioning

| Feature | Grin's Platform | Housecall Pro | Jobber | ServiceTitan |
|---------|-----------------|---------------|--------|--------------|
| Map view | ✅ Phase 5A | ✅ | ✅ | ✅ |
| Staff colors | ✅ Phase 5A | ✅ | ✅ | ✅ |
| Route lines | ✅ Phase 5B | ✅ | ✅ | ✅ |
| Sequence numbers | ✅ Phase 5B | ❌ | ✅ | ✅ |
| Clustering | ✅ Phase 5C | ❌ | ❓ | ✅ |
| Info windows | ✅ Phase 5C | ✅ | ✅ | ✅ |
| Mobile responsive | ✅ Phase 5C | ✅ | ✅ | ✅ |
| Real-time GPS | 🔮 Phase 5D | ✅ | ✅ | ✅ |
| Drag-and-drop | 🔮 Phase 5D | ❌ | ❌ | ✅ Premium |

**Phase 5A+5B** = Matches Housecall Pro, Jobber basic  
**Phase 5C** = Matches mid-tier competitors  
**Phase 5D** = Matches ServiceTitan basic

---

## Success Criteria

### Phase 5A Success
- [ ] Map displays with custom clean styling
- [ ] All jobs with coordinates shown as colored numbered markers
- [ ] Map/List toggle works smoothly
- [ ] Map centers on Twin Cities area by default
- [ ] Legend shows staff colors and job counts

### Phase 5B Success
- [ ] Routes drawn as colored straight-line polylines
- [ ] Each staff has distinct, consistent color
- [ ] Sequence numbers clearly visible on markers
- [ ] Staff home locations shown with house icon
- [ ] Auto-fit bounds shows all markers with padding

### Phase 5C Success
- [ ] Filter by staff member works (multi-select)
- [ ] Filter by job status works
- [ ] Info window shows complete job details on click
- [ ] Hover preview shows quick summary
- [ ] Marker clustering works for 20+ jobs
- [ ] Mobile layout with bottom sheet works on tablet

### Overall Phase 5 Success
- [ ] Viktor can visualize entire day's schedule on map
- [ ] Routes are clearly distinguishable by staff
- [ ] Geographic clustering is visually apparent
- [ ] Map loads in < 3 seconds
- [ ] Works on desktop, tablet, and mobile

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Google Maps API rate limits | Low | Medium | Cache map tiles, limit API calls |
| Properties without coordinates | Medium | High | Show warning badge, exclude from map |
| Too many markers (performance) | Low | Medium | Mandatory clustering at 50+ jobs |
| Mobile responsiveness issues | Medium | Medium | Test on real devices, use bottom sheet |
| API key exposure | Low | High | Environment variables, restrict key by domain |
| Color accessibility | Low | Medium | Use color + number, test with colorblind tools |

---

## Empty States

### No Jobs for Date
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│                        Google Map                                │
│                   (Twin Cities centered)                         │
│                                                                  │
│              ┌─────────────────────────────┐                    │
│              │  📭 No jobs for Jan 24      │                    │
│              │                             │                    │
│              │  No jobs are scheduled or   │                    │
│              │  pending for this date.     │                    │
│              │                             │                    │
│              │  [← Previous Day] [Next →]  │                    │
│              └─────────────────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### No Schedule Generated Yet
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│         ⚫ ⚫ ⚫ (unscheduled jobs visible)                      │
│                                                                  │
│              ┌─────────────────────────────┐                    │
│              │  📋 Schedule not generated  │                    │
│              │                             │                    │
│              │  12 jobs ready to schedule  │                    │
│              │                             │                    │
│              │  [Generate Schedule →]      │                    │
│              └─────────────────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### All Jobs Filtered Out
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│                        Google Map                                │
│                   (empty, zoomed out)                            │
│                                                                  │
│              ┌─────────────────────────────┐                    │
│              │  🔍 No matching jobs        │                    │
│              │                             │                    │
│              │  Try adjusting your filters │                    │
│              │                             │                    │
│              │  [Clear Filters]            │                    │
│              └─────────────────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependencies

### Required Before Starting
- [x] Phase 4A complete (schedule generation, coordinates, routes)
- [x] Google Maps API key (already have for travel time)
- [ ] VITE_GOOGLE_MAPS_API_KEY environment variable in frontend
- [ ] Enable Maps JavaScript API in Google Cloud Console

### External Dependencies
- `@react-google-maps/api` npm package
- `@googlemaps/markerclusterer` npm package (for clustering)

---

## Decisions Made

| Question | Decision | Notes |
|----------|----------|-------|
| **Planning Mode** | ✅ Yes | Show unscheduled jobs before generating |
| **Staff Colors** | Hardcoded per name | Viktor=Red, Vas=Blue, etc. |
| **Default Date** | Today | Most common use case |
| **Print/Export** | Not needed | Skip for now |
| **Scope** | Full (5A+5B+5C) | ~14-20 hours total |
| **Coordinate Source** | Existing domain models | `ScheduleLocation` already has lat/lng - just pass through to API |

---

## Data Availability Summary

After codebase analysis, here's what exists vs what needs to be added:

| Data | Status | Location |
|------|--------|----------|
| Job coordinates | ✅ Exists in domain | `ScheduleLocation.latitude/longitude` |
| Staff start coordinates | ✅ Exists in domain | `ScheduleStaff.start_location` |
| Job coordinates in API | ❌ Missing | Need to add to `ScheduleJobAssignment` schema |
| Staff coordinates in API | ❌ Missing | Need to add to `ScheduleStaffAssignment` schema |
| Unscheduled jobs endpoint | ❌ Missing | Need new `GET /api/v1/map/unscheduled-jobs` |
| Staff color mapping | ✅ Frontend only | Hardcoded in `staffColors.ts` |

---

## Next Steps

1. ~~**Confirm scope:** MVP (5A+5B) or Full (5A+5B+5C)?~~ → **Full scope confirmed**
2. **Set up environment:** Add VITE_GOOGLE_MAPS_API_KEY to frontend .env
3. **Install dependencies:** `npm install @react-google-maps/api @googlemaps/markerclusterer`
4. **Begin Phase 5A.1:** Create MapProvider with custom styling
5. **Iterate:** Build incrementally with visual validation

---

## Implementation Notes

### Data Flow Analysis

After analyzing the codebase, here's the current data flow and what needs to change:

```
Current Flow (Schedule Generation):
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Job + Property  │ ──► │ ScheduleLocation │ ──► │ ScheduleJobAssign.  │
│ (has lat/lng)   │     │ (has lat/lng)    │     │ (NO lat/lng ❌)     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘

Required Flow (For Map):
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Job + Property  │ ──► │ ScheduleLocation │ ──► │ ScheduleJobAssign.  │
│ (has lat/lng)   │     │ (has lat/lng)    │     │ (WITH lat/lng ✅)   │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

**Key Finding:** The coordinates already exist in `ScheduleLocation` (domain model). We just need to pass them through to the API response schema.

### Files to Modify

| File | Change Required |
|------|-----------------|
| `src/grins_platform/schemas/schedule_generation.py` | Add `latitude`, `longitude` to `ScheduleJobAssignment`; Add `start_lat`, `start_lng` to `ScheduleStaffAssignment` |
| `src/grins_platform/services/schedule_generation_service.py` | Pass coordinates when creating `ScheduleJobAssignment` (line ~326) |
| `src/grins_platform/api/v1/schedule.py` | Add new endpoint for unscheduled jobs |

### Code Change Preview

**Schema Update (schedule_generation.py):**
```python
class ScheduleJobAssignment(BaseModel):
    """A job assignment in the generated schedule."""
    job_id: UUID
    customer_name: str
    address: str | None = None
    city: str | None = None
    latitude: float | None = None      # ADD THIS
    longitude: float | None = None     # ADD THIS
    service_type: str
    # ... rest unchanged
```

**Service Update (schedule_generation_service.py, ~line 326):**
```python
job_assignments.append(ScheduleJobAssignment(
    job_id=slot.job.id,
    customer_name=slot.job.customer_name,
    address=slot.job.location.address,
    city=slot.job.location.city,
    latitude=float(slot.job.location.latitude),   # ADD THIS
    longitude=float(slot.job.location.longitude), # ADD THIS
    service_type=slot.job.service_type,
    # ... rest unchanged
))
```

---

## Testing Strategy

### Backend Tests

#### Unit Tests (pytest)

| Test | Description | File |
|------|-------------|------|
| Schema validation | Verify lat/lng fields accept valid coordinates | `test_schedule_generation_schemas.py` |
| Schema validation | Verify lat/lng fields handle None gracefully | `test_schedule_generation_schemas.py` |
| Service mapping | Verify coordinates pass through from domain to schema | `test_schedule_generation_service.py` |

#### Integration Tests (pytest)

| Test | Description | File |
|------|-------------|------|
| API response | Verify `/api/v1/schedule/generate` returns coordinates | `test_schedule_api.py` |
| Unscheduled jobs | Verify new endpoint returns jobs with coordinates | `test_schedule_api.py` |
| Missing coordinates | Verify jobs without coordinates are flagged | `test_schedule_api.py` |

### Frontend Tests

#### Unit Tests (Vitest)

| Test | File | Description |
|------|------|-------------|
| `staffColors.test.ts` | `utils/staffColors.ts` | Color mapping returns correct hex codes for each staff name |
| `mapStyles.test.ts` | `utils/mapStyles.ts` | Map style config is valid JSON |
| `useMapBounds.test.ts` | `hooks/useMapBounds.ts` | Bounds calculation includes all markers with padding |
| `markerIcons.test.ts` | `utils/markerIcons.ts` | SVG generation produces valid markup |

#### Component Tests (Vitest + React Testing Library)

| Test | Component | Description |
|------|-----------|-------------|
| Renders loading state | `ScheduleMap` | Shows spinner while fetching data |
| Renders markers | `MapMarker` | Displays correct sequence number and color |
| Renders info window | `MapInfoWindow` | Shows job details on click |
| Filter updates | `MapFilters` | Toggling staff filter updates visible markers |
| Empty state | `ScheduleMap` | Shows empty state when no jobs |
| Mode toggle | `ScheduleMap` | Switches between Planning and Schedule modes |

#### E2E Tests (agent-browser)

```bash
# scripts/validate-map.sh

echo "🗺️ Map Interface Validation"
echo "Scenario: Viktor views schedule on map"

# Start with schedule page
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Step 1: Toggle to map view
echo "Step 1: Switch to map view"
agent-browser click "[data-testid='view-toggle-map']"
agent-browser wait "[data-testid='schedule-map']"
agent-browser is visible "[data-testid='schedule-map']" && echo "  ✓ Map visible"

# Step 2: Verify markers
echo "Step 2: Verify markers render"
agent-browser wait "[data-testid='map-marker']"
agent-browser is visible "[data-testid='map-marker']" && echo "  ✓ Markers visible"

# Step 3: Click marker for info window
echo "Step 3: Test info window"
agent-browser click "[data-testid='map-marker']:first-child"
agent-browser wait "[data-testid='map-info-window']"
agent-browser is visible "[data-testid='map-info-window']" && echo "  ✓ Info window opens"

# Step 4: Test staff filter
echo "Step 4: Test staff filter"
agent-browser click "[data-testid='staff-filter-viktor']"
agent-browser wait --text "Viktor"
echo "  ✓ Staff filter works"

# Step 5: Test legend
echo "Step 5: Verify legend"
agent-browser is visible "[data-testid='map-legend']" && echo "  ✓ Legend visible"

# Step 6: Test mode toggle (if in Schedule mode)
echo "Step 6: Test mode toggle"
agent-browser click "[data-testid='mode-toggle-planning']"
agent-browser wait "[data-testid='unscheduled-marker']"
echo "  ✓ Planning mode shows unscheduled jobs"

agent-browser close
echo "✅ Map Validation PASSED!"
```

### Test Data Requirements

For testing, ensure seed data includes:

| Data | Requirement |
|------|-------------|
| **Properties with coordinates** | At least 10 properties in Twin Cities area |
| **Properties without coordinates** | At least 2 properties with NULL lat/lng (for error handling) |
| **Jobs for today** | At least 15 jobs with status "approved" |
| **Multiple staff** | At least 3 staff members with different start locations |
| **Generated schedule** | Pre-generated schedule for today with assignments |

### Coverage Targets

| Component | Target |
|-----------|--------|
| Backend schema changes | 100% |
| Backend service changes | 90%+ |
| Frontend hooks | 85%+ |
| Frontend components | 80%+ |
| E2E critical paths | 100% |

---

## Additional Implementation Details

### Frontend Type Updates Required

The frontend types in `frontend/src/features/schedule/types/index.ts` must be updated to match backend schema changes:

```typescript
// Update ScheduleJobAssignment
export interface ScheduleJobAssignment {
  job_id: string;
  customer_name: string;
  address: string | null;
  city: string | null;
  latitude: number | null;      // ADD THIS
  longitude: number | null;     // ADD THIS
  service_type: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  travel_time_minutes: number;
  sequence_index: number;
}

// Update ScheduleStaffAssignment
export interface ScheduleStaffAssignment {
  staff_id: string;
  staff_name: string;
  start_lat: number | null;     // ADD THIS
  start_lng: number | null;     // ADD THIS
  jobs: ScheduleJobAssignment[];
  total_jobs: number;
  total_travel_minutes: number;
  first_job_start: string | null;
  last_job_end: string | null;
}
```

### Decimal to Float Conversion

The domain model uses `Decimal` for coordinates (for precision), but the API should return `float`:

```python
# In schedule_generation_service.py
latitude=float(slot.job.location.latitude) if slot.job.location.latitude else None,
longitude=float(slot.job.location.longitude) if slot.job.location.longitude else None,
```

### Existing Page Structure

The `ScheduleGenerationPage.tsx` already has:
- Date picker with calendar popover
- Preview and Generate buttons
- Capacity overview card
- Results section using `ScheduleResults` component

**Integration approach:** Add a view toggle (List/Map) that conditionally renders either `ScheduleResults` or the new `ScheduleMap` component.

### New Map Types File

Create `frontend/src/features/schedule/types/map.ts`:

```typescript
export interface MapJob {
  job_id: string;
  customer_name: string;
  address: string;
  city: string;
  latitude: number;
  longitude: number;
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
  waypoints: Array<{ lat: number; lng: number; job_id: string; sequence: number }>;
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

export interface MapFilters {
  staffIds: string[];
  showRoutes: boolean;
  mode: MapMode;
}
```

### Staff Color Utility

Create `frontend/src/features/schedule/utils/staffColors.ts`:

```typescript
export const STAFF_COLORS: Record<string, string> = {
  'Viktor': '#EF4444',    // Red
  'Vas': '#3B82F6',       // Blue
  'Dad': '#22C55E',       // Green
  'Gennadiy': '#22C55E',  // Green (alias)
  'Steven': '#F59E0B',    // Amber
  'Vitallik': '#8B5CF6',  // Purple
};

export const DEFAULT_COLOR = '#6B7280'; // Gray for unknown staff

export function getStaffColor(staffName: string): string {
  return STAFF_COLORS[staffName] || DEFAULT_COLOR;
}
```

### New Endpoint: Unscheduled Jobs for Planning Mode

Create `GET /api/v1/map/unscheduled-jobs` endpoint:

**Backend Implementation:**

```python
# src/grins_platform/api/v1/map.py (NEW FILE)

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from uuid import UUID

from grins_platform.api.dependencies import get_db
from grins_platform.schemas.map import UnscheduledJobsResponse, MapUnscheduledJob
from grins_platform.models.job import Job
from grins_platform.models.property import Property
from grins_platform.models.enums import JobStatus

router = APIRouter(prefix="/map", tags=["map"])

@router.get("/unscheduled-jobs", response_model=UnscheduledJobsResponse)
def get_unscheduled_jobs(
    target_date: date = Query(..., description="Date to check for unscheduled jobs"),
    db: Session = Depends(get_db),
) -> UnscheduledJobsResponse:
    """Get all approved jobs that are not yet scheduled for a date."""
    
    # Query jobs that are approved but not scheduled
    jobs = db.query(Job).filter(
        Job.status == JobStatus.APPROVED,
        # Add date filter if jobs have a target_date field
    ).all()
    
    unscheduled = []
    missing_coords = 0
    
    for job in jobs:
        property = job.property
        lat = property.latitude if property else None
        lng = property.longitude if property else None
        
        if lat is None or lng is None:
            missing_coords += 1
        
        unscheduled.append(MapUnscheduledJob(
            job_id=job.id,
            customer_name=f"{job.customer.first_name} {job.customer.last_name}",
            address=property.address if property else "",
            city=property.city if property else "",
            latitude=float(lat) if lat else None,
            longitude=float(lng) if lng else None,
            service_type=job.service_offering.name if job.service_offering else "Unknown",
            zone_count=property.zone_count if property else None,
            priority_level=job.priority_level or 0,
        ))
    
    return UnscheduledJobsResponse(
        date=target_date,
        jobs=unscheduled,
        total=len(unscheduled),
        missing_coordinates=missing_coords,
    )
```

**Register Router:**

```python
# In src/grins_platform/api/v1/__init__.py
from grins_platform.api.v1.map import router as map_router

# Add to router includes
api_router.include_router(map_router)
```

---

## Pre-Implementation Checklist

Before starting implementation, verify:

- [ ] **Google Cloud Console:** Maps JavaScript API is enabled (not just Distance Matrix)
- [ ] **Environment variable:** `VITE_GOOGLE_MAPS_API_KEY` added to `frontend/.env`
- [ ] **API key restrictions:** Key restricted to localhost and production domain
- [ ] **Seed data:** Test database has properties with coordinates
- [ ] **Backend running:** Schedule generation endpoint works
- [ ] **Frontend running:** Schedule page loads without errors

### Quick Verification Commands

```bash
# 1. Check if Google Maps API key is set
grep VITE_GOOGLE_MAPS frontend/.env

# 2. Verify backend has coordinate data
curl http://localhost:8000/api/v1/properties | jq '.[0] | {latitude, longitude}'

# 3. Verify schedule generation works
curl -X POST http://localhost:8000/api/v1/schedule/generate \
  -H "Content-Type: application/json" \
  -d '{"schedule_date": "2026-01-24"}' | jq '.assignments[0].jobs[0]'

# 4. Check frontend builds
cd frontend && npm run build
```

---

## Appendix: Research References

See `phase5-map-ui-design-research.md` for:
- Detailed competitor analysis (ServiceTitan, Housecall Pro, Jobber, OptimoRoute)
- Dribbble/Behance design inspiration
- Uber's Layer Manager pattern
- Map UI best practices from Eleken
- SnazzyMaps styling examples
- Full accessibility checklist
