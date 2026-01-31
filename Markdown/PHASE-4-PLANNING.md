# Phase 4: Route Optimization Planning

**Date:** January 23, 2026  
**Status:** Planning → Ready for Implementation  
**Focus:** Timefold-based route optimization with constraint-based scheduling

---

## 📋 Readiness Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Gap Analysis** | ✅ Complete | 12 gaps identified, 3 high-priority in Phase 4A |
| **Data Model Changes** | ✅ Complete | All schemas defined |
| **API Endpoints** | ✅ Complete | All endpoints specified |
| **Timefold Integration** | ✅ Complete | Problem definition, constraints documented |
| **Constraint System** | ✅ Complete | Hard/soft constraints, weights, profiles |
| **Notification System** | ✅ Complete | Twilio/SendGrid integration planned |
| **Timezone Handling** | ✅ Added | UTC storage, Central display |
| **Job Status Workflow** | ✅ Added | Status transitions documented |
| **Concurrent Lock** | ✅ Added | Prevents duplicate generation |
| **API Key Management** | ✅ Added | Secure storage, fallback strategy |
| **Timefold POC** | ⏭️ Skipped | Validation will happen during 4A.5 implementation |
| **Test Data Seeding** | ✅ Added | Task 4A.0.5 for realistic test data |
| **Minimal UI** | ✅ Added | Task 4A.11 for schedule generation UI |
| **Cost Estimates** | ✅ Complete | ~$110/month peak season |
| **Success Criteria** | ✅ Complete | Measurable goals defined |
| **Risk Assessment** | ✅ Complete | Risks identified with mitigations |
| **Implementation Order** | ✅ Complete | Week-by-week breakdown |
| **Future Enhancements** | ✅ Complete | 11 items documented for Phase 5+ |

**Overall Readiness: 100% - Ready to create formal spec and begin implementation**

---

## 📝 Decision Notes

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-23 | **Skip Timefold POC (4A.0)** | Timefold has good Python documentation and our use case is relatively simple (10-50 jobs, 3-5 staff). Any issues with Timefold will be discovered during 4A.5 implementation. Saves 2-4 hours of upfront work. |

---

## Executive Summary

Phase 4 implements intelligent route optimization using Timefold, enabling Viktor to generate optimized daily schedules with one click. This replaces the current manual process of scheduling 150+ jobs per week during peak season.

### Business Value
- **Current Pain:** 5+ minutes per job for manual scheduling = 12+ hours/week during peak season
- **Target:** One-click schedule generation in < 30 seconds
- **Constraints Handled:** Equipment, staff skills, weather, time windows, location batching, VIP priority

### Why Route Optimization is the Right Choice

**Arguments FOR Route Optimization:**
1. **Biggest single time sink** - 12+ hours/week during peak season (150 jobs × 5 min each)
2. **Directly addresses Viktor's #1 complaint** - "Mental calculations for route optimization and time estimation"
3. **Enables scaling** - Can't hire more staff if scheduling is the bottleneck
4. **Immediate ROI** - 96% time reduction (12 hrs → 30 min)
5. **Foundation for automation** - Once schedules are generated, notifications can be automated
6. **Competitive differentiator** - Most competitors don't have true constraint-based route optimization

---

## Current State Analysis

### What We Have ✅

| Component | Status | Details |
|-----------|--------|---------|
| **Jobs** | ✅ Complete | Full CRUD, status workflow, filtering by status/category |
| **Staff** | ✅ Complete | CRUD, availability flag, role/skill level |
| **Appointments** | ✅ Complete | CRUD, daily/weekly schedule views, staff assignment |
| **Properties** | ✅ Complete | Address, city, lat/lng coordinates, zone_count |
| **Service Offerings** | ✅ Complete | Duration estimates, staffing requirements, equipment |
| **Job → Property** | ✅ Complete | Jobs link to properties with coordinates |
| **Job → Service Offering** | ✅ Complete | Jobs link to service offerings for duration/requirements |


### Existing Data Model Summary

```
Job Model:
├── customer_id, property_id, service_offering_id (relationships)
├── job_type, category, status, description
├── estimated_duration_minutes
├── priority_level (0=normal, 1=high, 2=urgent)
├── weather_sensitive (boolean)
├── staffing_required (int, default 1)
├── equipment_required (JSON list: ["compressor", "pipe_puller"])
└── materials_required (JSON list)

Staff Model:
├── name, phone, email
├── role (tech, sales, admin)
├── skill_level (junior, senior, lead)
├── certifications (JSON list)
├── is_available (boolean flag)
├── availability_notes (text)
└── hourly_rate

Property Model:
├── address, city, state, zip_code
├── latitude, longitude (for route optimization)
├── zone_count (affects job duration)
├── system_type (standard, lake_pump)
└── property_type (residential, commercial)

Service Offering Model:
├── name, category, description
├── estimated_duration_minutes
├── duration_per_zone_minutes
├── staffing_required
├── equipment_required (JSON list)
└── pricing fields
```

---

## Gap Analysis: What's Missing

### Gap 1: Staff Availability Calendar 🔴 CRITICAL

**Current State:** Staff has `is_available` boolean flag only  
**Problem:** Can't determine if staff is available on specific dates/times  
**Impact:** Timefold can't assign staff to specific days without this data

**Current Model (Insufficient):**
```python
class Staff:
    is_available: bool  # Just a flag - doesn't tell us WHEN
    availability_notes: str  # Free text, not queryable
```

**Needed Model:**
```python
class StaffAvailability:
    id: UUID
    staff_id: UUID (FK → staff.id)
    date: date
    start_time: time  # e.g., 07:00
    end_time: time    # e.g., 17:00
    is_available: bool
    lunch_start: time | None  # e.g., 12:00
    lunch_duration_minutes: int  # e.g., 30
    notes: str | None
    created_at: datetime
    updated_at: datetime
```

**New API Endpoints Needed:**
- `GET /api/v1/staff/{id}/availability` - Get staff availability for date range
- `POST /api/v1/staff/{id}/availability` - Set availability for a date
- `PUT /api/v1/staff/{id}/availability/{date}` - Update availability for a date
- `DELETE /api/v1/staff/{id}/availability/{date}` - Remove availability entry
- `GET /api/v1/staff/available-on/{date}` - Get all staff available on a date


---

### Gap 2: Equipment/Vehicle Assignment 🔴 IMPORTANT

**Current State:**
- Jobs have `equipment_required: list[str]` (e.g., `["compressor", "pipe_puller"]`)
- Service offerings have `equipment_required: list[str]`
- Staff has NO equipment/vehicle assignment

**Problem:** Can't match jobs requiring compressor to staff who have compressor  
**Impact:** Winterization jobs can't be auto-assigned correctly

**Solution Options:**

**Option A: Simple - Add equipment to Staff model**
```python
class Staff:
    # ... existing fields ...
    assigned_equipment: list[str] | None  # ["compressor", "standard_tools"]
```

**Option B: Full Vehicle Management (Future)**
```python
class Vehicle:
    id: UUID
    name: str  # "Truck 1", "Van 2"
    equipment: list[str]  # ["compressor", "pipe_puller"]
    assigned_staff_id: UUID | None
```

**Recommendation:** Start with Option A (simple), migrate to Option B if needed.

---

### Gap 3: Travel Time Calculation 🔴 CRITICAL

**Current State:** No integration with Google Maps  
**Problem:** Can't calculate realistic drive times between appointments  
**Impact:** Schedules may be impossible to execute (jobs 45 min apart scheduled back-to-back)

**Needed Service:**
```python
class TravelTimeService:
    async def get_travel_time(
        origin: tuple[float, float],      # (lat, lng)
        destination: tuple[float, float]  # (lat, lng)
    ) -> timedelta:
        """Get driving time between two points using Google Maps API."""
    
    async def get_travel_matrix(
        locations: list[tuple[float, float]]
    ) -> dict[tuple[int, int], timedelta]:
        """Get travel times between all pairs of locations (for batch optimization)."""
```

**Google Maps API Required:**
- Distance Matrix API for travel times
- Directions API for route details (optional)

---

### Gap 4: Geocoding Service 🟡 IMPORTANT

**Current State:** Properties have `latitude` and `longitude` fields, but may be NULL  
**Problem:** Route optimization requires coordinates for all properties  
**Impact:** Jobs at properties without coordinates can't be optimized

**Needed Service:**
```python
class GeocodingService:
    async def geocode_address(
        address: str, 
        city: str, 
        state: str, 
        zip_code: str | None
    ) -> tuple[float, float] | None:
        """Convert address to lat/lng coordinates using Google Maps API."""
    
    async def validate_and_geocode(
        address: str,
        city: str,
        state: str
    ) -> GeocodingResult:
        """Validate address and return coordinates + formatted address."""
```

**Integration Points:**
- Auto-geocode when property is created
- Auto-geocode when property address is updated
- Batch geocode existing properties without coordinates


---

### Gap 5: Customer Time Window Preferences 🟡 NICE TO HAVE

**Current State:** Appointments have time windows, but jobs don't capture customer preferences  
**Problem:** Customer's preferred time (morning/afternoon) not captured at intake  
**Impact:** May schedule customers at inconvenient times

**Potential Addition to Job Model:**
```python
class Job:
    # ... existing fields ...
    preferred_time_window_start: time | None  # Customer prefers after 10am
    preferred_time_window_end: time | None    # Customer prefers before 2pm
```

---

### Gap 6: Staff Starting Location 🔴 CRITICAL

**Problem:** Routes need a starting point - where does each staff member begin their day?

**Options:**
1. **Central depot** - All staff start from Viktor's shop
2. **Staff home address** - Each staff starts from home
3. **Configurable** - Admin sets starting location per staff per day

**Recommendation:** Add `default_start_address` fields to Staff model

**Schema Addition:**
```python
class Staff:
    # ... existing fields ...
    default_start_address: str | None
    default_start_city: str | None
    default_start_lat: float | None
    default_start_lng: float | None
```

---

### Gap 7: Break/Lunch Handling 🟡 IMPORTANT

**Problem:** 8-hour work days need breaks. Current model doesn't account for lunch.

**Options:**
1. **Fixed lunch block** - 12:00-12:30 blocked for all staff
2. **Flexible lunch** - System inserts 30-min break after 4 hours
3. **Manual** - Staff marks when they take lunch

**Recommendation:** Add configurable lunch window to staff availability

**Schema Addition:**
```python
class StaffAvailability:
    # ... existing fields ...
    lunch_start: time | None = time(12, 0)
    lunch_duration_minutes: int = 30
```

---

### Gap 8: Buffer Time Between Jobs 🟡 IMPORTANT

**Problem:** Travel time alone isn't enough - need buffer for:
- Finding parking
- Walking to door
- Brief customer chat before starting
- Unexpected delays

**Recommendation:** Add configurable buffer to service offerings

**Schema Addition:**
```python
class ServiceOffering:
    # ... existing fields ...
    buffer_minutes: int = 10  # Added to estimated duration
```

---

### Gap 9: Multi-Staff Job Coordination 🟡 IMPORTANT

**Problem:** Jobs requiring 2+ staff need coordination:
- Both staff must be available at same time
- Both must arrive at same location
- One might be "lead" and other "helper"

**Current Model:** `job.staffing_required: int` exists but no coordination logic

**Recommendation:** For MVP, treat multi-staff jobs as single assignment to "lead" staff. Phase 4B can add full coordination.

---

### Gap 10: Emergency/Priority Job Insertion 🔴 HIGH PRIORITY

**Problem:** No mechanism to handle urgent/emergency jobs that need to be inserted into an existing schedule.

**Current State:** Schedule generation is a one-time operation with no re-optimization capability.

**Impact:** When an emergency call comes in (e.g., flooded basement, broken main line), Viktor has to manually figure out how to fit it in.

**Needed Capability:**
- Priority flag system: Emergency (same-day), High (24-48 hrs), Normal, Low (flexible)
- Re-optimization API that can insert a new job into existing schedule
- Automatic notification to affected customers if their time shifts
- "Bump" logic to determine which jobs can be moved

**Schema Addition:**
```python
class Job:
    # ... existing fields ...
    priority_level: int = 0  # 0=normal, 1=high, 2=urgent, 3=emergency
    is_flexible: bool = True  # Can this job be moved if needed?
```

**New API Endpoints:**
```
POST /api/v1/schedule/insert-emergency
POST /api/v1/schedule/re-optimize/{date}
```

---

### Gap 11: Schedule Conflict Resolution 🔴 HIGH PRIORITY

**Problem:** No workflow for handling customer cancellations or reschedules after confirmations are sent.

**Current State:** If a customer cancels, the slot is wasted and staff may show up to an empty house.

**Impact:** Lost productivity, wasted travel time, poor customer experience.

**Needed Capability:**
- Customer cancellation handling (free up slot, notify staff)
- Customer reschedule request workflow
- Re-optimization after cancellations to fill gaps
- Waitlist system for customers who want earlier slots
- "Fill the gap" suggestions when cancellation creates opening

**Schema Addition:**
```python
class Appointment:
    # ... existing fields ...
    cancellation_reason: str | None
    cancelled_at: datetime | None
    rescheduled_from_id: UUID | None  # Link to original appointment

class ScheduleWaitlist:
    id: UUID
    job_id: UUID
    preferred_date: date
    preferred_time_start: time | None
    preferred_time_end: time | None
    created_at: datetime
    notified_at: datetime | None  # When we offered them a slot
```

**New API Endpoints:**
```
POST /api/v1/appointments/{id}/cancel
POST /api/v1/appointments/{id}/reschedule
GET  /api/v1/schedule/waitlist
POST /api/v1/schedule/fill-gap
```

---

### Gap 12: Staff Unavailability Mid-Day 🔴 HIGH PRIORITY

**Problem:** No mechanism to handle staff calling in sick or having emergencies mid-day.

**Current State:** If a staff member can't continue, all their remaining jobs are orphaned.

**Impact:** Customers don't get served, no automatic reassignment, manual scramble to fix.

**Needed Capability:**
- Real-time schedule reassignment capability
- "Reassign all jobs from Staff X to Staff Y" function
- Automatic customer notification when technician changes
- Partial day availability (staff leaves early, arrives late)
- Emergency coverage assignment

**Schema Addition:**
```python
class StaffAvailability:
    # ... existing fields ...
    actual_start_time: time | None  # If different from planned
    actual_end_time: time | None    # If different from planned
    unavailable_reason: str | None  # "sick", "emergency", "vehicle_issue"

class ScheduleReassignment:
    id: UUID
    original_staff_id: UUID
    new_staff_id: UUID
    date: date
    reason: str
    jobs_reassigned: list[UUID]
    created_at: datetime
```

**New API Endpoints:**
```
POST /api/v1/schedule/reassign-staff
POST /api/v1/staff/{id}/mark-unavailable
GET  /api/v1/schedule/coverage-options/{date}
```

---

## Phased Implementation Approach

### Phase 4A: MVP Route Optimization (Priority)

**Goal:** Working one-click schedule generation with core constraints

| Task | Description | New Tables | New APIs | Effort |
|------|-------------|------------|----------|--------|
| ~~**4A.0**~~ | ~~Timefold POC/Spike~~ | ~~None~~ | ~~None~~ | ~~2-4 hrs~~ |
| **4A.0.5** | Test Data Seeding (PREREQUISITE) | None | Script | 2-3 hrs |
| **4A.1** | Staff Availability Calendar | `staff_availability` | 5 endpoints | 4-6 hrs |
| **4A.2** | Equipment on Staff | Modify `staff` table | Update existing | 1-2 hrs |
| **4A.3** | Staff Starting Location | Modify `staff` table | Update existing | 1-2 hrs |
| **4A.4** | Google Maps Integration | None | Internal service | 2-3 hrs |
| **4A.5** | Timefold Scheduling Service | None | 3 endpoints | 6-8 hrs |
| **4A.6** | Schedule Generation API | None | 4 endpoints | 2-3 hrs |
| **4A.7** | Buffer Time Configuration | Modify `service_offering` | Update existing | 1 hr |
| **4A.8** | Emergency Job Insertion (Gap 10) | Modify `job` table | 2 endpoints | 3-4 hrs |
| **4A.9** | Schedule Conflict Resolution (Gap 11) | `schedule_waitlist` | 4 endpoints | 4-5 hrs |
| **4A.10** | Staff Reassignment (Gap 12) | `schedule_reassignment` | 3 endpoints | 3-4 hrs |
| **4A.11** | Minimal Schedule Generation UI | None | Frontend | 4-6 hrs |

**Total Phase 4A Effort:** 31-45 hours (reduced from 33-49 after skipping 4A.0 POC)

#### 4A.11: Minimal Schedule Generation UI

**Purpose:** Provide Viktor with a simple interface to trigger and view schedule generation.

**Components:**
1. **Generate Schedule Button** - On Schedule page, button to trigger generation for selected date
2. **Date Picker** - Select which date to generate schedule for
3. **Generation Status** - Show "Generating..." spinner while optimization runs
4. **Results Display** - Show generated assignments in a table/list
5. **Unassigned Jobs Alert** - Highlight any jobs that couldn't be scheduled

**UI Mockup:**
```
┌─────────────────────────────────────────────────────────────┐
│ Schedule Generation                                          │
├─────────────────────────────────────────────────────────────┤
│ Date: [January 24, 2026 ▼]  [🔄 Generate Schedule]          │
│                                                              │
│ Status: ✅ Generated 12 assignments in 28 seconds            │
│ Total Travel Time: 2h 45m                                    │
│ Unassigned Jobs: 2 (equipment mismatch)                      │
├─────────────────────────────────────────────────────────────┤
│ Staff: Vas                                                   │
│ ┌─────┬──────────────┬─────────────────┬──────────────────┐ │
│ │ #   │ Time         │ Customer        │ Job Type         │ │
│ ├─────┼──────────────┼─────────────────┼──────────────────┤ │
│ │ 1   │ 8:00-9:00    │ John Smith      │ Spring Startup   │ │
│ │ 2   │ 9:30-10:30   │ Jane Doe        │ Spring Startup   │ │
│ │ 3   │ 11:00-12:00  │ Bob Wilson      │ Repair           │ │
│ │ ... │ ...          │ ...             │ ...              │ │
│ └─────┴──────────────┴─────────────────┴──────────────────┘ │
│                                                              │
│ Staff: Dad                                                   │
│ ┌─────┬──────────────┬─────────────────┬──────────────────┐ │
│ │ #   │ Time         │ Customer        │ Job Type         │ │
│ │ ... │ ...          │ ...             │ ...              │ │
│ └─────┴──────────────┴─────────────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**API Integration:**
```typescript
// frontend/src/features/schedule/api/scheduleApi.ts
export const scheduleApi = {
  generateSchedule: async (date: string, options?: GenerateOptions) => {
    return apiClient.post<ScheduleGenerateResponse>('/schedule/generate', {
      date,
      ...options
    });
  },
  
  getCapacity: async (date: string) => {
    return apiClient.get<ScheduleCapacityResponse>(`/schedule/capacity/${date}`);
  },
  
  getGenerationStatus: async (date: string) => {
    return apiClient.get<GenerationStatus>(`/schedule/generation-status/${date}`);
  }
};
```

**Effort:** 4-6 hours


### Phase 4B: Automated Notifications & Configurable Constraints (Enhanced)

**Goal:** Customer communication automation and admin-configurable optimization settings

| Task | Description | Effort |
|------|-------------|--------|
| **4B.1** | Notification Service (Twilio/SendGrid) | 3-4 hrs |
| **4B.2** | Appointment Confirmation SMS/Email | 2-3 hrs |
| **4B.3** | Day-Before Reminder | 1-2 hrs |
| **4B.4** | "On the Way" Notification | 1-2 hrs |
| **4B.5** | Completion Summary | 1-2 hrs |
| **4B.6** | Configurable Constraints System | 4-5 hrs |
| **4B.7** | Optimization Settings Admin UI | 3-4 hrs |
| **4B.8** | Additional Timefold Constraints | 3-4 hrs |

**Total Phase 4B Effort:** 18-26 hours

#### 4B.6: Configurable Constraints System

**Purpose:** Allow admin to enable/disable and weight optimization constraints

**Database Schema:**
```sql
CREATE TABLE optimization_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    
    -- Hard Constraints (toggleable)
    enforce_staff_availability BOOLEAN DEFAULT TRUE,
    enforce_equipment_match BOOLEAN DEFAULT TRUE,
    enforce_no_overlap BOOLEAN DEFAULT TRUE,
    enforce_staffing_requirements BOOLEAN DEFAULT TRUE,
    enforce_lunch_break BOOLEAN DEFAULT TRUE,
    enforce_start_location_travel BOOLEAN DEFAULT TRUE,
    enforce_end_time_validation BOOLEAN DEFAULT TRUE,
    
    -- Soft Constraints (toggleable + weighted 0-100)
    enable_minimize_travel BOOLEAN DEFAULT TRUE,
    weight_minimize_travel INT DEFAULT 80,
    
    enable_batch_by_city BOOLEAN DEFAULT TRUE,
    weight_batch_by_city INT DEFAULT 70,
    
    enable_batch_by_job_type BOOLEAN DEFAULT TRUE,
    weight_batch_by_job_type INT DEFAULT 50,
    
    enable_priority_first BOOLEAN DEFAULT TRUE,
    weight_priority_first INT DEFAULT 90,
    
    enable_weather_sensitive BOOLEAN DEFAULT TRUE,
    weight_weather_sensitive INT DEFAULT 40,
    
    enable_buffer_time BOOLEAN DEFAULT TRUE,
    weight_buffer_time INT DEFAULT 60,
    
    enable_minimize_backtracking BOOLEAN DEFAULT TRUE,
    weight_minimize_backtracking INT DEFAULT 50,
    
    enable_customer_time_preference BOOLEAN DEFAULT TRUE,
    weight_customer_time_preference INT DEFAULT 70,
    
    enable_fcfs_ordering BOOLEAN DEFAULT TRUE,
    weight_fcfs_ordering INT DEFAULT 30,
    
    -- Metadata
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default settings
INSERT INTO optimization_settings (name, is_default) VALUES ('Default', TRUE);
```

**Pydantic Schemas:**
```python
class OptimizationSettingsCreate(BaseModel):
    name: str
    
    # Hard Constraints
    enforce_staff_availability: bool = True
    enforce_equipment_match: bool = True
    enforce_no_overlap: bool = True
    enforce_staffing_requirements: bool = True
    enforce_lunch_break: bool = True
    enforce_start_location_travel: bool = True
    enforce_end_time_validation: bool = True
    
    # Soft Constraints with weights
    enable_minimize_travel: bool = True
    weight_minimize_travel: int = Field(default=80, ge=0, le=100)
    
    enable_batch_by_city: bool = True
    weight_batch_by_city: int = Field(default=70, ge=0, le=100)
    
    enable_batch_by_job_type: bool = True
    weight_batch_by_job_type: int = Field(default=50, ge=0, le=100)
    
    enable_priority_first: bool = True
    weight_priority_first: int = Field(default=90, ge=0, le=100)
    
    enable_weather_sensitive: bool = True
    weight_weather_sensitive: int = Field(default=40, ge=0, le=100)
    
    enable_buffer_time: bool = True
    weight_buffer_time: int = Field(default=60, ge=0, le=100)
    
    enable_minimize_backtracking: bool = True
    weight_minimize_backtracking: int = Field(default=50, ge=0, le=100)
    
    enable_customer_time_preference: bool = True
    weight_customer_time_preference: int = Field(default=70, ge=0, le=100)
    
    enable_fcfs_ordering: bool = True
    weight_fcfs_ordering: int = Field(default=30, ge=0, le=100)
```

**API Endpoints:**
```
GET  /api/v1/optimization/settings - List all settings profiles
GET  /api/v1/optimization/settings/{id} - Get specific profile
POST /api/v1/optimization/settings - Create new profile
PUT  /api/v1/optimization/settings/{id} - Update profile
DELETE /api/v1/optimization/settings/{id} - Delete profile
POST /api/v1/optimization/settings/{id}/set-default - Set as default
```


### Phase 4C: Schedule Management UI (Future)

**Goal:** Visual schedule review and management interface

| Task | Description | Effort |
|------|-------------|--------|
| **4C.1** | Visual Schedule Review (Calendar View) | 4-6 hrs |
| **4C.2** | Drag-and-Drop Schedule Editor | 4-6 hrs |
| **4C.3** | One-Click "Send All Confirmations" | 2-3 hrs |
| **4C.4** | Unassigned Jobs Queue | 2-3 hrs |

**Total Phase 4C Effort:** 12-18 hours

---

## Phase 4A Detailed Design

### ~~4A.0: Timefold POC/Spike~~ (SKIPPED)

> **Decision:** POC skipped on January 23, 2026. Timefold has good Python documentation and our use case is relatively simple (10-50 jobs, 3-5 staff). Any issues with Timefold will be discovered during 4A.5 implementation. This saves 2-4 hours of upfront work.

---

### 4A.0.5: Test Data Seeding (PREREQUISITE)

**Purpose:** Create realistic test data for development and testing of route optimization.

**Why This Matters:** Route optimization requires:
- Multiple jobs with real coordinates in Twin Cities area
- Staff with different equipment and availability
- Properties with valid lat/lng coordinates
- Service offerings with realistic durations

**Seeding Script Tasks:**
1. Create 20-30 test properties with real Twin Cities coordinates
2. Create 5-10 test customers
3. Create 15-25 test jobs (mix of types, priorities, equipment needs)
4. Create 3-5 test staff with different equipment assignments
5. Create staff availability for next 7 days
6. Ensure all properties have valid lat/lng

**Test Data Distribution:**
```
Cities:
- Eden Prairie: 5 properties
- Plymouth: 5 properties
- Maple Grove: 4 properties
- Brooklyn Park: 4 properties
- Rogers: 3 properties
- Minnetonka: 3 properties

Job Types:
- Spring Startup: 8 jobs
- Winterization: 6 jobs
- Repair: 5 jobs
- Diagnostic: 3 jobs
- Installation: 2 jobs

Equipment Requirements:
- Standard tools only: 15 jobs
- Compressor required: 6 jobs
- Pipe puller required: 3 jobs
```

**Script Location:** `scripts/seed_route_optimization_test_data.py`

**Effort:** 2-3 hours

---

### 4A.1: Staff Availability Calendar

**Database Schema:**
```sql
CREATE TABLE staff_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    start_time TIME NOT NULL DEFAULT '07:00',
    end_time TIME NOT NULL DEFAULT '17:00',
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    lunch_start TIME DEFAULT '12:00',
    lunch_duration_minutes INT DEFAULT 30,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(staff_id, date)
);

CREATE INDEX idx_staff_availability_staff_date ON staff_availability(staff_id, date);
CREATE INDEX idx_staff_availability_date ON staff_availability(date);
```

**API Endpoints:**
```
GET  /api/v1/staff/{staff_id}/availability?start_date=&end_date=
POST /api/v1/staff/{staff_id}/availability
PUT  /api/v1/staff/{staff_id}/availability/{date}
DELETE /api/v1/staff/{staff_id}/availability/{date}
GET  /api/v1/staff/available-on/{date}
```

**Pydantic Schemas:**
```python
class StaffAvailabilityCreate(BaseModel):
    date: date
    start_time: time = time(7, 0)
    end_time: time = time(17, 0)
    is_available: bool = True
    lunch_start: time | None = time(12, 0)
    lunch_duration_minutes: int = 30
    notes: str | None = None

class StaffAvailabilityResponse(BaseModel):
    id: UUID
    staff_id: UUID
    date: date
    start_time: time
    end_time: time
    is_available: bool
    lunch_start: time | None
    lunch_duration_minutes: int
    notes: str | None
```

---

### 4A.2: Equipment on Staff

**Migration:**
```sql
ALTER TABLE staff ADD COLUMN assigned_equipment JSONB DEFAULT '[]';
```

**Update Staff Schema:**
```python
class StaffCreate(BaseModel):
    # ... existing fields ...
    assigned_equipment: list[str] | None = None

class StaffResponse(BaseModel):
    # ... existing fields ...
    assigned_equipment: list[str] | None
```

**Equipment Matching Logic:**
```python
def can_staff_handle_job(staff: Staff, job: Job) -> bool:
    """Check if staff has required equipment for job."""
    if not job.equipment_required:
        return True
    if not staff.assigned_equipment:
        return False
    return all(
        equip in staff.assigned_equipment 
        for equip in job.equipment_required
    )
```

---

### 4A.3: Staff Starting Location

**Migration:**
```sql
ALTER TABLE staff ADD COLUMN default_start_address VARCHAR(255);
ALTER TABLE staff ADD COLUMN default_start_city VARCHAR(100);
ALTER TABLE staff ADD COLUMN default_start_lat DECIMAL(10, 8);
ALTER TABLE staff ADD COLUMN default_start_lng DECIMAL(11, 8);
```

**Update Staff Schema:**
```python
class StaffCreate(BaseModel):
    # ... existing fields ...
    default_start_address: str | None = None
    default_start_city: str | None = None
    default_start_lat: float | None = None
    default_start_lng: float | None = None
```


---

### 4A.4: Google Maps Integration

**Service Implementation:**
```python
from googlemaps import Client

class TravelTimeService:
    def __init__(self, api_key: str):
        self.client = Client(key=api_key)
    
    async def get_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        departure_time: datetime | None = None
    ) -> timedelta:
        """Get driving time between two points."""
        result = self.client.distance_matrix(
            origins=[origin],
            destinations=[destination],
            mode="driving",
            departure_time=departure_time or "now"
        )
        
        duration_seconds = result["rows"][0]["elements"][0]["duration"]["value"]
        return timedelta(seconds=duration_seconds)
    
    async def get_travel_matrix(
        self,
        locations: list[tuple[float, float]]
    ) -> dict[tuple[int, int], int]:
        """Get travel times (seconds) between all pairs of locations."""
        result = self.client.distance_matrix(
            origins=locations,
            destinations=locations,
            mode="driving"
        )
        
        matrix = {}
        for i, row in enumerate(result["rows"]):
            for j, element in enumerate(row["elements"]):
                if element["status"] == "OK":
                    matrix[(i, j)] = element["duration"]["value"]
                else:
                    matrix[(i, j)] = 3600  # Default 1 hour if route not found
        
        return matrix
```

**Configuration:**
```python
# .env
GOOGLE_MAPS_API_KEY=your_api_key_here
```

**API Key Management:**
- Store API key in environment variable (never in code)
- Use `.env` file for local development
- Use secrets manager (AWS Secrets Manager, Railway secrets) for production
- Implement rate limiting to prevent cost overruns
- Set up billing alerts in Google Cloud Console
- Consider IP restriction for production API key

**Fallback Strategy:**
```python
async def get_travel_time_with_fallback(
    self,
    origin: tuple[float, float],
    destination: tuple[float, float]
) -> timedelta:
    """Get travel time with fallback to straight-line estimate."""
    try:
        return await self.get_travel_time(origin, destination)
    except Exception as e:
        # Fallback: straight-line distance × 1.4 factor at 30 mph
        distance_km = haversine_distance(origin, destination)
        estimated_minutes = (distance_km * 1.4) / 0.8  # 0.8 km/min = 48 km/hr
        return timedelta(minutes=int(estimated_minutes))
```

---

### 4A.5: Timefold Scheduling Service

**Timefold Problem Definition:**
```python
from timefold.solver import SolverFactory
from timefold.solver.config import SolverConfig, TerminationConfig
from dataclasses import dataclass

@dataclass
class ScheduleJob:
    """Job to be scheduled (Timefold planning entity)."""
    id: str
    property_lat: float
    property_lng: float
    duration_minutes: int
    equipment_required: list[str]
    staffing_required: int
    priority_level: int
    weather_sensitive: bool
    city: str
    job_type: str
    created_at: datetime  # For FCFS ordering
    preferred_time_start: time | None
    preferred_time_end: time | None

@dataclass
class ScheduleStaff:
    """Staff member available for scheduling."""
    id: str
    name: str
    available_start: time
    available_end: time
    lunch_start: time | None
    lunch_duration_minutes: int
    assigned_equipment: list[str]
    skill_level: str
    start_lat: float
    start_lng: float

@dataclass
class ScheduleAssignment:
    """Assignment of job to staff with time slot (Timefold planning variable)."""
    job: ScheduleJob
    staff: ScheduleStaff | None = None
    start_time: time | None = None
```


---

### 4A.6: Schedule Generation API

**New Endpoints:**
```
POST /api/v1/schedule/generate
GET  /api/v1/schedule/capacity/{date}
POST /api/v1/schedule/preview
GET  /api/v1/schedule/generation-status/{date}
```

**Request/Response Schemas:**
```python
class ScheduleGenerateRequest(BaseModel):
    date: date
    job_ids: list[UUID] | None = None  # If None, use all ready-to-schedule jobs
    staff_ids: list[UUID] | None = None  # If None, use all available staff
    optimization_time_seconds: int = 30
    settings_id: UUID | None = None  # Use specific optimization settings profile

class ScheduleGenerateResponse(BaseModel):
    date: date
    assignments: list[ScheduleAssignmentResponse]
    unassigned_jobs: list[UUID]
    optimization_score: str
    total_travel_minutes: int
    warnings: list[str]
    settings_used: str  # Name of optimization settings profile used

class ScheduleAssignmentResponse(BaseModel):
    job_id: UUID
    staff_id: UUID
    staff_name: str
    scheduled_date: date
    time_window_start: time
    time_window_end: time
    route_order: int
    estimated_arrival: time
    travel_minutes_from_previous: int

class ScheduleCapacityResponse(BaseModel):
    date: date
    available_staff: list[StaffCapacity]
    total_available_minutes: int
    jobs_ready_to_schedule: int
    estimated_jobs_capacity: int

class StaffCapacity(BaseModel):
    staff_id: UUID
    staff_name: str
    available_start: time
    available_end: time
    available_minutes: int
    assigned_equipment: list[str]
```

**Concurrent Generation Lock:**

To prevent multiple simultaneous schedule generations for the same date (which could cause conflicts), implement a locking mechanism:

```python
class ScheduleGenerationLock:
    """Prevent concurrent schedule generation for the same date."""
    
    # In-memory lock (for single instance) or Redis lock (for distributed)
    _locks: dict[date, datetime] = {}
    LOCK_TIMEOUT_SECONDS = 120  # 2 minutes max
    
    @classmethod
    def acquire(cls, target_date: date) -> bool:
        """Attempt to acquire lock for a date. Returns True if successful."""
        now = datetime.utcnow()
        
        # Check if lock exists and is still valid
        if target_date in cls._locks:
            lock_time = cls._locks[target_date]
            if (now - lock_time).total_seconds() < cls.LOCK_TIMEOUT_SECONDS:
                return False  # Lock is held
            # Lock expired, can acquire
        
        cls._locks[target_date] = now
        return True
    
    @classmethod
    def release(cls, target_date: date) -> None:
        """Release lock for a date."""
        cls._locks.pop(target_date, None)
    
    @classmethod
    def is_locked(cls, target_date: date) -> bool:
        """Check if a date is currently locked."""
        if target_date not in cls._locks:
            return False
        lock_time = cls._locks[target_date]
        return (datetime.utcnow() - lock_time).total_seconds() < cls.LOCK_TIMEOUT_SECONDS

class ScheduleGenerationStatus(BaseModel):
    """Status of schedule generation for a date."""
    date: date
    is_generating: bool
    started_at: datetime | None
    estimated_completion: datetime | None
```

**Usage in API:**
```python
@router.post("/generate")
async def generate_schedule(request: ScheduleGenerateRequest):
    # Check for concurrent generation
    if not ScheduleGenerationLock.acquire(request.date):
        raise HTTPException(
            status_code=409,
            detail=f"Schedule generation already in progress for {request.date}"
        )
    
    try:
        result = await schedule_service.generate(request)
        return result
    finally:
        ScheduleGenerationLock.release(request.date)
```

---

## Timezone Handling

**Design Decision:** All times stored in UTC, displayed in Central Time (America/Chicago).

**Implementation:**
```python
from datetime import datetime, time
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")
UTC_TZ = ZoneInfo("UTC")

def to_utc(local_time: time, local_date: date) -> datetime:
    """Convert Central time to UTC datetime."""
    local_dt = datetime.combine(local_date, local_time, tzinfo=CENTRAL_TZ)
    return local_dt.astimezone(UTC_TZ)

def to_central(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to Central time."""
    return utc_dt.astimezone(CENTRAL_TZ)

def format_time_for_display(utc_dt: datetime) -> str:
    """Format UTC datetime for display in Central time."""
    central_dt = to_central(utc_dt)
    return central_dt.strftime("%I:%M %p")  # e.g., "10:30 AM"
```

**Database Storage:**
- All `datetime` columns store UTC timestamps
- All `time` columns store local Central time (for availability windows)
- API responses include timezone info when relevant

**API Response Example:**
```json
{
  "scheduled_date": "2026-01-24",
  "time_window_start": "10:00",
  "time_window_end": "12:00",
  "timezone": "America/Chicago",
  "utc_start": "2026-01-24T16:00:00Z"
}
```

---

## Job Status Workflow Clarification

**Job Status Transitions:**
```
REQUESTED → APPROVED → SCHEDULED → IN_PROGRESS → COMPLETED → CLOSED
                ↓
            CANCELLED
```

**Schedule Generation Impact:**
- Only jobs with status `APPROVED` are eligible for schedule generation
- When schedule is generated, job status changes to `SCHEDULED`
- When staff marks "Arrived", job status changes to `IN_PROGRESS`
- When staff completes job, status changes to `COMPLETED`
- Admin closes job after payment received → `CLOSED`

**Appointment Creation:**
- Schedule generation creates `Appointment` records
- Each `Appointment` links to a `Job` and a `Staff` member
- `Appointment.status` tracks the appointment lifecycle (confirmed, in_progress, completed)
- `Job.status` tracks the overall job lifecycle

**Relationship:**
```
Job (1) ←→ (0..1) Appointment
- A job may have zero appointments (not yet scheduled)
- A job has exactly one appointment when scheduled
- Appointment contains the specific date/time/staff assignment
```

---

## Timefold Constraint Summary

### Hard Constraints (Must Satisfy - All Configurable)

| Constraint | Description | Source | Default |
|------------|-------------|--------|---------|
| Staff Availability | Staff must be available on scheduled date/time | `staff_availability` table | ✅ Enabled |
| Equipment Match | Staff must have required equipment | `staff.assigned_equipment` vs `job.equipment_required` | ✅ Enabled |
| No Overlap | Staff can't be in two places at once | Time window comparison | ✅ Enabled |
| Staffing Requirements | Jobs requiring 2+ staff get multiple assignments | `job.staffing_required` | ✅ Enabled |
| Lunch Break | Staff must have lunch break during shift | `staff_availability.lunch_*` fields | ✅ Enabled |
| Start Location Travel | First job must be reachable from staff start location | Calculate travel from home/depot | ✅ Enabled |
| End Time Validation | Last job must complete + travel home before shift ends | Include travel back to start | ✅ Enabled |

### Soft Constraints (Optimize - All Configurable with Weights)

| Constraint | Description | Default Weight | Explanation |
|------------|-------------|----------------|-------------|
| Minimize Travel | Reduce total driving time | 80 | High priority - saves time and fuel |
| Batch by City | Group jobs in same city | 70 | Medium-high - reduces travel |
| Batch by Job Type | Group similar jobs (all winterizations together) | 50 | Medium - efficiency gains |
| Priority First | Schedule high-priority jobs earlier | 90 | High - VIP customers first |
| Weather Sensitive | Schedule weather-sensitive jobs on good weather days | 40 | Lower - manual override common |
| Buffer Time | Prefer 10-15 min between jobs | 60 | Medium - prevents rushing |
| Minimize Backtracking | Avoid returning to areas already visited | 50 | Medium - route efficiency |
| Customer Time Preference | Respect customer's preferred time windows | 70 | Medium-high - customer satisfaction |
| FCFS Ordering | Earlier job requests scheduled first (First Come First Serve) | 30 | Lower - fairness factor |


### Constraint Explanations

**End Time Validation:** Ensures the last job of the day finishes with enough time for the staff member to travel back to their starting location before their shift ends. For example, if a staff member's shift ends at 5:00 PM and their last job is 30 minutes from home, the last job must complete by 4:30 PM.

**Minimize Backtracking:** Penalizes routes where staff return to geographic areas they've already visited earlier in the day. For example, if a technician does jobs in Eden Prairie in the morning, then Plymouth, then goes back to Eden Prairie - that's backtracking and should be avoided.

**FCFS Ordering (First Come First Serve):** Gives slight preference to scheduling older job requests before newer ones. If two jobs are otherwise equal in priority and constraints, the one that was requested first gets scheduled first. This ensures fairness for customers who've been waiting longer.

**Weather Sensitive (MVP Approach):** For MVP, weather sensitivity is handled via manual override:
- Jobs marked `weather_sensitive=True` are flagged in the UI
- Admin can manually exclude weather-sensitive jobs on bad weather days
- Future enhancement: Integrate weather API (OpenWeatherMap, Weather.gov) for automatic scheduling

---

## Constraint Configuration Examples

### Example 1: Speed-Focused Profile
```json
{
  "name": "Speed Focused",
  "enable_minimize_travel": true,
  "weight_minimize_travel": 100,
  "enable_batch_by_city": true,
  "weight_batch_by_city": 90,
  "enable_buffer_time": false,
  "weight_buffer_time": 0,
  "enable_fcfs_ordering": false,
  "weight_fcfs_ordering": 0
}
```
*Use case: Peak season when maximizing jobs per day is critical*

### Example 2: Customer-Focused Profile
```json
{
  "name": "Customer Focused",
  "enable_customer_time_preference": true,
  "weight_customer_time_preference": 100,
  "enable_priority_first": true,
  "weight_priority_first": 95,
  "enable_buffer_time": true,
  "weight_buffer_time": 80,
  "enable_minimize_travel": true,
  "weight_minimize_travel": 50
}
```
*Use case: Off-season when customer satisfaction is more important than efficiency*

### Example 3: Balanced Profile (Default)
```json
{
  "name": "Default",
  "enable_minimize_travel": true,
  "weight_minimize_travel": 80,
  "enable_batch_by_city": true,
  "weight_batch_by_city": 70,
  "enable_priority_first": true,
  "weight_priority_first": 90,
  "enable_customer_time_preference": true,
  "weight_customer_time_preference": 70,
  "enable_buffer_time": true,
  "weight_buffer_time": 60
}
```
*Use case: Normal operations with balanced priorities*

---

## Implementation Order

### Week 1: Prerequisites
1. **Day 1-2:** Staff Availability Calendar (model, repository, service, API)
2. **Day 2-3:** Equipment on Staff + Starting Location (migrations, schema updates)
3. **Day 3-4:** Google Maps Integration (service, configuration, testing)

### Week 2: Core Optimization
4. **Day 1-3:** Timefold Scheduling Service (problem definition, constraints)
5. **Day 3-4:** Schedule Generation API (endpoints, integration)
6. **Day 4-5:** Testing and refinement

### Week 3: Phase 4B (Notifications & Config)
7. **Day 1-2:** Notification Service (Twilio/SendGrid integration)
8. **Day 2-3:** Appointment notifications (confirmation, reminder, on-the-way)
9. **Day 3-4:** Configurable Constraints System (model, API)
10. **Day 4-5:** Optimization Settings Admin UI

---

## Testing Strategy

### Unit Tests
- Staff availability CRUD operations
- Equipment matching logic
- Travel time calculations (mocked)
- Constraint validation
- Optimization settings CRUD

### Integration Tests
- Full schedule generation with test data
- API endpoint testing
- Database integration
- Notification delivery (sandbox mode)

### Property-Based Tests
- Generated schedules never violate enabled hard constraints
- All assigned jobs have valid staff
- No time overlaps for same staff
- Constraint weights affect optimization score correctly


### Demo Scenario
```
Input:
- 10 jobs ready to schedule (mix of cities, job types)
- 3 staff members with different equipment
- Date: Tomorrow
- Optimization profile: Default

Expected Output:
- Optimized assignments for all 10 jobs
- Jobs batched by city
- Equipment requirements satisfied
- Total travel time minimized
- Lunch breaks respected
- Staff end times validated
```

---

## Success Criteria

### Phase 4A Success Criteria
- [ ] Generate schedule for 10+ jobs in < 30 seconds
- [ ] All hard constraints satisfied (no violations)
- [ ] Travel time reduced by 20%+ vs random assignment
- [ ] Jobs batched by city (same city jobs consecutive)
- [ ] Equipment requirements satisfied
- [ ] Staff availability respected
- [ ] Lunch breaks enforced
- [ ] Start/end location travel calculated
- [ ] Emergency jobs can be inserted into existing schedule (Gap 10)
- [ ] Re-optimization completes in < 15 seconds
- [ ] Customer cancellations free up slots immediately (Gap 11)
- [ ] Waitlist customers notified when slots open
- [ ] Staff can be marked unavailable mid-day (Gap 12)
- [ ] Jobs automatically reassigned to available staff

### Phase 4B Success Criteria
- [ ] Confirmation SMS sent within 1 minute of schedule generation
- [ ] Day-before reminder sent at 9 AM
- [ ] "On the way" notification sent when staff marks en route
- [ ] 90%+ delivery rate for SMS
- [ ] Customer can reply "YES" to confirm
- [ ] Admin can create/edit optimization profiles
- [ ] Admin can toggle individual constraints on/off
- [ ] Admin can adjust constraint weights via sliders
- [ ] Schedule generation uses selected profile

### Phase 4C Success Criteria
- [ ] Visual calendar view of generated schedule
- [ ] Drag-and-drop to manually adjust assignments
- [ ] One-click "Send All Confirmations" button
- [ ] Unassigned jobs clearly visible in queue

### Overall Phase 4 Success
- [ ] Viktor's scheduling time reduced from 12+ hrs/week to < 1 hr/week
- [ ] No-show rate reduced by 50%+ (due to reminders)
- [ ] Staff know their routes before leaving in morning
- [ ] Customers receive professional, timely communication
- [ ] Admin has full control over optimization behavior

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Timefold learning curve | Medium | Medium | Start with simple constraints, add complexity |
| Google Maps API costs | Low | Low | Cache travel times, use matrix API for batches |
| Properties without coordinates | Medium | High | Add geocoding service, validate on property create |
| Complex constraint interactions | Medium | Medium | Extensive testing, gradual constraint addition |
| Twilio/SendGrid integration | Low | Medium | Use well-documented APIs, test in sandbox |
| Staff adoption | Medium | High | Simple mobile UI, training session |
| Customer opt-out | Low | Low | Respect SMS opt-in preferences |
| Constraint configuration complexity | Medium | Low | Good defaults, clear UI, tooltips |
| Emergency job disruption | Medium | High | Gap 10 addresses with re-optimization API |
| Customer cancellations | Medium | Medium | Gap 11 addresses with conflict resolution |
| Staff unavailability mid-day | Medium | High | Gap 12 addresses with reassignment capability |

---

## Dependencies

### External Services
- **Google Maps Platform:** Distance Matrix API, Geocoding API
- **Timefold:** Python solver library (open source, free)
- **Twilio:** SMS notifications (~$0.0075/message)
- **SendGrid:** Email notifications (free tier sufficient)

### Internal Dependencies
- Phase 1-3 complete (customers, jobs, staff, appointments)
- Properties have lat/lng coordinates (or geocoding service)
- Service offerings have duration estimates

---

## Cost Estimates

### Google Maps API
- Distance Matrix API: ~$5 per 1000 requests
- Peak season estimate: 150 jobs/week × 4 weeks = 600 jobs/month
- With matrix optimization: ~$30-50/month

### Twilio SMS
- SMS: ~$0.0075 per message
- Peak season: 150 jobs × 3 notifications = 450 SMS/week = ~$15/week

### Total Monthly Cost (Peak Season)
- Google Maps: ~$50
- Twilio: ~$60
- **Total: ~$110/month**


---

## Competitor Analysis

### Detailed Competitor Breakdown

#### ServiceTitan
**Route Optimization Offering:** "Dispatch Pro" and "Scheduling Pro" add-ons

| Feature | Details |
|---------|---------|
| **Skill Matching** | ✅ Matches technicians to jobs based on skills |
| **Route Optimization** | ✅ Basic route optimization |
| **Adaptive Capacity Planning** | ✅ Adjusts based on demand |
| **Constraint-Based** | Partial - skills only, not equipment |
| **Pricing** | Premium add-on ($100-200/month extra) |
| **One-Click Generation** | ❌ Still requires manual dispatch decisions |

#### Housecall Pro
**Route Optimization Offering:** Built-in basic features

| Feature | Details |
|---------|---------|
| **GPS Tracking** | ✅ Real-time technician location |
| **Route Optimization** | ✅ Basic - suggests efficient routes |
| **Drag-and-Drop Scheduling** | ✅ Manual scheduling interface |
| **Constraint-Based** | ❌ No constraint-based optimization |
| **Pricing** | Included in plans ($169-499/month) |
| **One-Click Generation** | ❌ Manual drag-and-drop only |

#### Jobber
**Route Optimization Offering:** Built-in route optimization

| Feature | Details |
|---------|---------|
| **Master Route** | ✅ Create recurring route templates |
| **Daily Optimization** | ✅ Optimize routes for the day |
| **Team/Individual** | ✅ Can optimize for team or individuals |
| **Constraint-Based** | ❌ No equipment or skill constraints |
| **Pricing** | Included in plans ($69-349/month) |
| **One-Click Generation** | Partial - still requires manual review |

### Feature Comparison Matrix

| Feature | Housecall Pro | ServiceTitan | Jobber | **Grin's Platform** |
|---------|---------------|--------------|--------|---------------------|
| **Basic Scheduling** | ✅ | ✅ | ✅ | ✅ |
| **Route Optimization** | ✅ Basic | ✅ Add-on ($$) | ✅ Built-in | ✅ Timefold (Free) |
| **Constraint-Based** | ❌ | Partial (skills) | ❌ | ✅ **Full** |
| **Equipment Matching** | ❌ | ❌ | ❌ | ✅ **Yes** |
| **One-Click Generation** | ❌ | ❌ | Partial | ✅ **Yes** |
| **City Batching** | ❌ Manual | Partial | ❌ | ✅ **Automatic** |
| **Job Type Batching** | ❌ | ❌ | ❌ | ✅ **Automatic** |
| **Weather Sensitivity** | ❌ | ❌ | ❌ | ✅ **Yes** |
| **Configurable Constraints** | ❌ | ❌ | ❌ | ✅ **Yes** |
| **Custom Constraint Weights** | ❌ | ❌ | ❌ | ✅ **Yes** |
| **SMS Notifications** | ✅ ($) | ✅ ($) | ✅ ($) | ✅ (~$15/week) |
| **Open Source Solver** | ❌ | ❌ | ❌ | ✅ **Timefold** |

### Grin's Competitive Advantages

1. **TRUE Constraint-Based Optimization** - Equipment matching, skill levels, weather sensitivity, staffing requirements
2. **Intelligent Batching** - City batching + job type batching (automatic)
3. **One-Click Schedule Generation** - No manual intervention required
4. **Configurable Constraints** - Admin can enable/disable and weight each constraint
5. **Open Source Solver (Timefold)** - No licensing fees, full customization
6. **Irrigation-Specific Design** - Zone-based duration, seasonal work, lake pump handling

### Cost Comparison

| Platform | Route Optimization Cost | Total Monthly Cost |
|----------|------------------------|-------------------|
| **ServiceTitan** | $100-200/month add-on | $300-500+/month |
| **Housecall Pro** | Included (basic) | $169-499/month |
| **Jobber** | Included | $69-349/month |
| **Grin's Platform** | $0 (Timefold is free) | ~$110/month (APIs only) |

**Annual Savings vs ServiceTitan:** $2,700-5,100/year
**Annual Savings vs Housecall Pro:** $1,128-5,088/year

---

## Next Steps

1. **Create Spec:** Generate formal spec in `.kiro/specs/route-optimization/`
2. ~~**Implement Phase 4A.0:** Timefold POC/Spike~~ (SKIPPED - validation during 4A.5)
3. **Implement Phase 4A.0.5:** Test Data Seeding (PREREQUISITE - create realistic test data)
4. **Implement Phase 4A.1:** Staff Availability Calendar
5. **Implement Phase 4A.2-3:** Equipment and Starting Location on Staff
6. **Implement Phase 4A.4:** Google Maps Integration (with API key management)
7. **Implement Phase 4A.5-6:** Timefold Service and Schedule Generation API (with concurrent lock)
8. **Implement Phase 4A.7:** Buffer Time Configuration
9. **Implement Phase 4A.8:** Emergency Job Insertion (Gap 10)
10. **Implement Phase 4A.9:** Schedule Conflict Resolution (Gap 11)
11. **Implement Phase 4A.10:** Staff Reassignment (Gap 12)
12. **Implement Phase 4A.11:** Minimal Schedule Generation UI
13. **Demo:** Show one-click schedule generation with emergency handling
14. **Implement Phase 4B:** Notifications + Configurable Constraints
15. **Implement Phase 4C:** Schedule Management UI

---

## ⚠️ FUTURE PHASE ENHANCEMENTS - DO NOT INCLUDE AS OF NOW ⚠️

> **IMPORTANT:** The following features have been identified as valuable enhancements but should NOT be included in the current Phase 4 implementation. These are documented for future reference and should be considered for Phase 5 or later.

---

### Future Gap A: Recurring Customer Preferences 🟡 MEDIUM PRIORITY

**Problem:** No mechanism to capture and honor customer preferences for specific technicians or time slots.

**Value:** Improves customer satisfaction, reduces complaints, builds loyalty.

**Needed Capability:**
- Preferred technician (soft constraint)
- Preferred time window (morning/afternoon)
- "Same technician as last time" preference
- Notes about customer availability patterns

**Schema Addition:**
```python
class CustomerPreferences:
    id: UUID
    customer_id: UUID
    preferred_staff_id: UUID | None
    preferred_time_start: time | None
    preferred_time_end: time | None
    same_technician_preference: bool = False
    availability_notes: str | None
```

---

### Future Gap B: Travel Time Caching Strategy 🟡 MEDIUM PRIORITY

**Problem:** Google Maps API calls are expensive and add latency. No explicit caching strategy defined.

**Value:** Reduces API costs by 60-80%, improves optimization speed.

**Needed Capability:**
- Cache travel times between frequently-visited locations
- Cache duration: 7-30 days (traffic patterns are relatively stable)
- Pre-compute travel matrix for service area
- Fallback to straight-line distance × 1.4 factor if API fails

**Schema Addition:**
```python
class TravelTimeCache:
    id: UUID
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    travel_seconds: int
    distance_meters: int
    cached_at: datetime
    expires_at: datetime
```

---

### Future Gap C: Optimization Time Limits 🟡 MEDIUM PRIORITY

**Problem:** No configurable time limits for how long the optimizer should run.

**Value:** Allows admin to balance speed vs quality based on urgency.

**Needed Capability:**
- Quick mode: 5-10 seconds (for small batches)
- Standard mode: 30-60 seconds (daily schedule)
- Deep optimization: 2-5 minutes (weekly planning)
- Admin can choose based on urgency

**Schema Addition:**
```python
class OptimizationSettings:
    # ... existing fields ...
    quick_mode_seconds: int = 10
    standard_mode_seconds: int = 30
    deep_mode_seconds: int = 180
    default_mode: str = "standard"
```

---

### Future Gap D: Schedule Quality Metrics Dashboard 🟡 MEDIUM PRIORITY

**Problem:** No metrics to evaluate how "good" a generated schedule is.

**Value:** Helps Viktor understand optimization quality, identify improvement opportunities.

**Needed Capability:**
- Total travel time for the day
- Average jobs per staff member
- Utilization rate (scheduled time vs available time)
- Number of constraint violations (if any soft constraints relaxed)
- Comparison to previous schedules
- Trend analysis over time

**API Endpoints:**
```
GET /api/v1/schedule/metrics/{date}
GET /api/v1/schedule/metrics/comparison?date1=&date2=
GET /api/v1/schedule/metrics/trends?start_date=&end_date=
```

---

### Future Gap E: Notification Delivery Tracking 🟡 MEDIUM PRIORITY

**Problem:** No tracking of whether notifications were actually delivered/read.

**Value:** Ensures customers receive communications, enables follow-up on failures.

**Needed Capability:**
- SMS delivery status tracking (Twilio webhooks)
- Email open tracking (SendGrid)
- Failed delivery alerts to admin
- Retry logic for failed messages
- Customer response tracking (confirmed/declined)

**Schema Addition:**
```python
class NotificationLog:
    id: UUID
    appointment_id: UUID
    customer_id: UUID
    notification_type: str  # "confirmation", "reminder", "on_the_way", "completion"
    channel: str  # "sms", "email"
    sent_at: datetime
    delivered_at: datetime | None
    opened_at: datetime | None  # For email
    response: str | None  # "confirmed", "declined", None
    error_message: str | None
    retry_count: int = 0
```

---

### Future Gap F: Seasonal Capacity Planning 🟡 MEDIUM PRIORITY

**Problem:** No mechanism to handle peak season capacity constraints proactively.

**Value:** Prevents overbooking, manages customer expectations, enables waitlist.

**Needed Capability:**
- Maximum jobs per day limit (configurable)
- Overbooking prevention
- Waitlist when capacity reached
- Capacity forecasting based on historical data
- "Book next available" feature

**Schema Addition:**
```python
class CapacitySettings:
    id: UUID
    date: date
    max_jobs: int
    max_staff_hours: int
    is_blocked: bool = False  # Holiday, weather day
    notes: str | None

class CapacityForecast:
    date: date
    predicted_demand: int
    available_capacity: int
    utilization_percent: float
```

---

### Future Gap G: Multi-Day Job Handling 🟡 MEDIUM PRIORITY

**Problem:** Jobs spanning multiple days (installations, large projects) not fully addressed.

**Value:** Enables proper scheduling of large projects without manual coordination.

**Needed Capability:**
- How to schedule Day 2, Day 3 of a multi-day job
- Same staff requirement across days
- Equipment reservation across days
- Customer notification for multi-day jobs
- Progress tracking across days

**Schema Addition:**
```python
class MultiDayJob:
    id: UUID
    job_id: UUID
    total_days: int
    current_day: int
    same_staff_required: bool = True
    equipment_reserved: list[str]
    daily_notes: dict[int, str]  # {1: "Day 1 notes", 2: "Day 2 notes"}
```

---

### Future Gap H: Rollback/Undo Capability 🟢 LOW PRIORITY

**Problem:** No way to undo a schedule generation if Viktor realizes it's wrong.

**Value:** Reduces risk of schedule generation, enables experimentation.

**Needed Capability:**
- "Undo last schedule generation" button
- Schedule version history
- Compare current vs previous schedule
- Restore previous schedule option

**Schema Addition:**
```python
class ScheduleVersion:
    id: UUID
    date: date
    version: int
    created_at: datetime
    created_by: str
    assignments_snapshot: dict  # JSON snapshot of all assignments
    is_current: bool
    notes: str | None
```

---

### Future Gap I: Testing Strategy for Optimization 🟡 MEDIUM PRIORITY

**Problem:** No defined approach for testing the optimization algorithm.

**Value:** Ensures optimization quality, prevents regressions, enables confident changes.

**Needed Capability:**
- Unit tests for individual constraints
- Integration tests with sample data
- Performance tests (100+ jobs)
- Regression tests when adding new constraints
- A/B testing capability (compare two optimization strategies)
- Golden dataset for consistent testing

---

### Future Gap J: Offline/Degraded Mode 🟢 LOW PRIORITY

**Problem:** No fallback strategy if Google Maps API is down.

**Value:** Ensures system continues working even with external service failures.

**Needed Capability:**
- Use cached travel times
- Fall back to straight-line distance × 1.4 factor
- Alert admin that optimization is using estimates
- Queue jobs for re-optimization when API recovers
- Graceful degradation messaging

---

### Future Gap K: Customer Communication Templates 🟢 LOW PRIORITY

**Problem:** No mention of customizable message templates.

**Value:** Enables personalization, seasonal messaging, brand consistency.

**Needed Capability:**
- Admin-editable SMS/email templates
- Variable substitution ({customer_name}, {appointment_time}, etc.)
- Different templates for different job types
- Seasonal message variations
- A/B testing for message effectiveness

**Schema Addition:**
```python
class MessageTemplate:
    id: UUID
    name: str
    notification_type: str  # "confirmation", "reminder", etc.
    channel: str  # "sms", "email"
    subject: str | None  # For email
    body: str  # With {variable} placeholders
    is_active: bool = True
    job_types: list[str] | None  # Specific job types, or None for all
    season: str | None  # "spring", "fall", or None for all
```

---

### Future Enhancements Priority Summary

| Gap | Priority | Effort | Impact | Phase |
|-----|----------|--------|--------|-------|
| A. Customer Preferences | Medium | Medium | Medium | 5 |
| B. Travel Time Caching | Medium | Low | Medium | 5 |
| C. Optimization Time Limits | Medium | Low | Medium | 5 |
| D. Quality Metrics Dashboard | Medium | Medium | High | 5 |
| E. Notification Tracking | Medium | Low | Medium | 5 |
| F. Capacity Planning | Medium | Medium | High | 5 |
| G. Multi-Day Jobs | Medium | Medium | Medium | 5 |
| H. Rollback/Undo | Low | Low | Medium | 6 |
| I. Testing Strategy | Medium | Medium | High | 5 |
| J. Offline Mode | Low | Low | Low | 6 |
| K. Message Templates | Low | Low | Low | 6 |

---

## Appendix: Viktor's Key Quotes

From `Grins_Irrigation_Backend_System.md`:

> "150+ individual jobs per week with 5+ min per job to schedule from start to finish"

> "Mental calculations for route optimization and time estimation"

> "Manually needing to track and type everything has to be Viktor's biggest waste of time"

> "With a click of a button it should be able to build Viktor a schedule for a specific day/week for each staff/crew"

> "All communications to customers throughout this process will be handled by AI agents"

> "Customers should get a simple notification that shows service request, service cost, time proposed, and a confirmation option"

> "Two days prior to the appointment, clients will be notified again of their upcoming appointments in case they forget"
