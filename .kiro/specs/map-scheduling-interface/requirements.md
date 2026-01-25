# Map-Based Scheduling Interface - Requirements

## Overview

Phase 5 implements a Google Maps-based interface that allows Viktor to visualize customer locations, job assignments, and optimized routes on an interactive map. This transforms the schedule generation experience from a text-based list view to a visual, geographic interface.

## User Stories

### 1. Map Visualization

#### 1.1 View Schedule on Map
**As** Viktor (business owner)  
**I want** to see all scheduled jobs displayed on a Google Map  
**So that** I can visually understand the geographic distribution of work for the day

**Acceptance Criteria:**
- Map displays with clean, minimal styling centered on Twin Cities area
- Each job appears as a colored marker with sequence number
- Staff members have distinct, consistent colors (Viktor=Red, Vas=Blue, Dad=Green, Steven=Amber, Vitallik=Purple)
- Map loads in under 3 seconds
- Default zoom level shows all markers with padding

#### 1.2 Toggle Between List and Map Views
**As** Viktor  
**I want** to switch between list view and map view  
**So that** I can use whichever visualization is most helpful for my current task

**Acceptance Criteria:**
- Toggle buttons clearly labeled "List" and "Map"
- Current view is visually indicated (highlighted/selected state)
- Switching views preserves the selected date and any filters
- Transition is smooth without page reload

#### 1.3 View Planning Mode (Unscheduled Jobs)
**As** Viktor  
**I want** to see unscheduled jobs on the map before generating a schedule  
**So that** I can understand the geographic spread and make informed decisions

**Acceptance Criteria:**
- Planning mode shows all approved-but-unscheduled jobs
- Unscheduled jobs appear as gray pulsing markers
- Job count summary displayed ("12 unscheduled jobs for today")
- "Generate Schedule" button prominently displayed
- After generating, automatically switches to Schedule mode

### 2. Route Visualization

#### 2.1 View Route Lines
**As** Viktor  
**I want** to see route lines connecting jobs in sequence  
**So that** I can verify the route makes geographic sense

**Acceptance Criteria:**
- Straight-line polylines connect jobs in sequence order
- Lines are colored to match staff member
- Route starts from staff home location
- Lines are semi-transparent to not obscure markers
- Toggle to show/hide routes

#### 2.2 View Staff Home Locations
**As** Viktor  
**I want** to see where each staff member starts their day  
**So that** I can understand the full route context

**Acceptance Criteria:**
- Staff home locations shown with house icon
- Icon colored to match staff member
- Staff name displayed on hover
- Home marker is visually distinct from job markers

#### 2.3 Auto-Fit Map Bounds
**As** Viktor  
**I want** the map to automatically zoom to show all markers  
**So that** I don't have to manually adjust the view

**Acceptance Criteria:**
- Map automatically fits bounds to include all visible markers
- Includes padding around markers (not edge-to-edge)
- "Fit Bounds" button available to reset view
- Respects current filter selections

### 3. Interactive Features

#### 3.1 Filter by Staff Member
**As** Viktor  
**I want** to filter the map to show only specific staff members  
**So that** I can focus on one technician's route at a time

**Acceptance Criteria:**
- Checkbox list of staff members with job counts
- Multi-select supported (show multiple staff)
- Filtering updates map immediately (client-side)
- Filtered-out markers are hidden, not grayed
- Legend updates to reflect visible staff only

#### 3.2 View Job Details on Click
**As** Viktor  
**I want** to click a marker to see job details  
**So that** I can quickly access information without leaving the map

**Acceptance Criteria:**
- Info window opens on marker click
- Shows: customer name, address, service type, time window, route position, travel time
- Staff color indicator visible
- "View Details" button links to full job page
- Click outside or press Escape to close

#### 3.3 Hover Preview
**As** Viktor  
**I want** to see a quick preview when hovering over a marker  
**So that** I can scan jobs without clicking each one

**Acceptance Criteria:**
- Small tooltip appears on hover (not full info window)
- Shows: customer name, service type, time window
- Appears after 200ms delay (not instant)
- Disappears when mouse leaves marker

#### 3.4 Marker Clustering
**As** Viktor  
**I want** markers to cluster when zoomed out  
**So that** the map remains readable with many jobs

**Acceptance Criteria:**
- Clustering activates when 20+ jobs visible
- Cluster shows count of jobs contained
- Clicking cluster zooms in to show individual markers
- Clusters use neutral color (not staff-specific)

### 4. Empty States and Error Handling

#### 4.1 No Jobs for Date
**As** Viktor  
**I want** to see a helpful message when there are no jobs  
**So that** I understand the map is working correctly

**Acceptance Criteria:**
- Centered message: "No jobs for [date]"
- Map still displays (centered on Twin Cities)
- Date navigation buttons visible
- Suggestion to check another date

#### 4.2 No Schedule Generated
**As** Viktor  
**I want** to see unscheduled jobs with a prompt to generate  
**So that** I can take action

**Acceptance Criteria:**
- Shows unscheduled jobs as gray markers
- Message: "Schedule not generated - 12 jobs ready to schedule"
- Prominent "Generate Schedule" button
- After generating, shows scheduled view

#### 4.3 Missing Coordinates Warning
**As** Viktor  
**I want** to know if some jobs can't be displayed  
**So that** I can fix the data

**Acceptance Criteria:**
- Warning banner: "3 jobs missing coordinates"
- List of affected jobs with links
- Jobs without coordinates excluded from map
- Warning dismissible but persists until fixed

#### 4.4 API Error Handling
**As** Viktor  
**I want** to see a clear error message if something fails  
**So that** I know what went wrong

**Acceptance Criteria:**
- Error message displayed in map area
- "Retry" button to attempt reload
- Cached data shown if available
- Error logged for debugging

### 5. Legend and Controls

#### 5.1 Staff Color Legend
**As** Viktor  
**I want** to see a legend explaining the colors  
**So that** I can quickly identify which staff has which jobs

**Acceptance Criteria:**
- Legend shows all staff with their color
- Job count per staff displayed
- Unassigned jobs shown in gray
- Legend updates when filters change

#### 5.2 Map Controls
**As** Viktor  
**I want** standard map controls  
**So that** I can navigate the map easily

**Acceptance Criteria:**
- Zoom in/out buttons
- "Fit Bounds" button to reset view
- Full-screen toggle (optional)
- Controls positioned consistently (top-right)

### 6. Mobile Responsiveness

#### 6.1 Mobile Layout
**As** Viktor (on tablet)  
**I want** the map to work well on smaller screens  
**So that** I can use it in the field

**Acceptance Criteria:**
- Map takes full width on mobile
- Filters collapse into dropdown/modal
- Bottom sheet for job details (not info window)
- Touch-friendly tap targets (44px minimum)
- Swipe up to expand job details

## Non-Functional Requirements

### Performance
- Map initial load: < 3 seconds
- Marker rendering: < 500ms for 50 markers
- Filter updates: < 200ms (client-side)
- Smooth 60fps pan/zoom

### Accessibility
- Keyboard navigation for all controls
- ARIA labels on markers
- Color + icon/number (never color alone)
- Screen reader announcements for state changes
- Focus indicators on interactive elements

### Browser Support
- Chrome (latest 2 versions)
- Safari (latest 2 versions)
- Firefox (latest 2 versions)
- Edge (latest 2 versions)

### API Costs
- Maps JavaScript API: FREE (first 28,000 loads/month)
- Straight-line polylines: FREE (canvas drawing)
- Custom markers: FREE (SVG rendering)
- No additional API costs beyond existing Distance Matrix

## Out of Scope (Phase 5D - Future)

- Real-time GPS tracking
- "On my way" notifications
- Drag-and-drop job reassignment
- Route reordering via drag
- Live map updates (WebSocket)

## Dependencies

### Required Before Starting
- Phase 4A complete (schedule generation, coordinates, routes)
- Google Maps API key configured
- VITE_GOOGLE_MAPS_API_KEY environment variable
- Maps JavaScript API enabled in Google Cloud Console

### External Dependencies
- `@react-google-maps/api` npm package
- `@googlemaps/markerclusterer` npm package

## Success Metrics

- Viktor can visualize entire day's schedule on map
- Routes are clearly distinguishable by staff
- Geographic clustering is visually apparent
- Map loads in < 3 seconds
- Works on desktop, tablet, and mobile
