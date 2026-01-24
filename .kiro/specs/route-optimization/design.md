# Design Document: Route Optimization

## Overview

The Route Optimization feature implements intelligent, constraint-based schedule generation for Grin's Irrigation Platform using Timefold, an open-source constraint satisfaction solver. This feature replaces Viktor's manual scheduling process (12+ hours/week during peak season) with one-click schedule generation that completes in under 30 seconds.

The system handles:
- Staff availability calendar management
- Equipment assignment and matching
- Travel time calculation via Google Maps API
- Constraint-based schedule optimization (7 hard constraints, 9 soft constraints)
- Emergency job insertion and re-optimization
- Schedule conflict resolution (cancellations, reschedules, waitlist)
- Staff reassignment when staff become unavailable

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ Staff Availability│  │ Schedule Gen   │  │ Conflict Resolution        │  │
│  │ Endpoints        │  │ Endpoints      │  │ Endpoints                  │  │
│  └────────┬─────────┘  └────────┬───────┘  └─────────────┬───────────────┘  │
└───────────┼─────────────────────┼───────────────────────┼───────────────────┘
            │                     │                       │
┌───────────┼─────────────────────┼───────────────────────┼───────────────────┐
│           ▼                     ▼                       ▼                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ StaffAvailability│  │ ScheduleService │  │ ConflictResolutionService  │  │
│  │ Service          │  │                 │  │                            │  │
│  └────────┬─────────┘  └────────┬───────┘  └─────────────┬───────────────┘  │
│           │                     │                       │                   │
│           │            ┌────────┴───────┐               │                   │
│           │            ▼                ▼               │                   │
│           │   ┌─────────────────┐ ┌─────────────────┐   │                   │
│           │   │ TimefoldSolver  │ │ TravelTimeService│   │                   │
│           │   │                 │ │                 │   │                   │
│           │   └─────────────────┘ └────────┬────────┘   │                   │
│           │                                │            │                   │
│                        Service Layer                                        │
└───────────┼────────────────────────────────┼────────────┼───────────────────┘
            │                                │            │
┌───────────┼────────────────────────────────┼────────────┼───────────────────┐
│           ▼                                ▼            ▼                   │
│  ┌─────────────────┐              ┌─────────────────┐                       │
│  │ StaffAvailability│              │ Google Maps API │                       │
│  │ Repository       │              │ (External)      │                       │
│  └────────┬─────────┘              └─────────────────┘                       │
│           │                                                                  │
│           ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         PostgreSQL Database                              ││
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐││
│  │  │staff_availability│ │schedule_waitlist│ │schedule_reassignment│ │staff (modified)│││
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                        Repository Layer                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Staff Availability Service

Manages staff availability calendar entries.

```python
class StaffAvailabilityService:
    """Service for managing staff availability calendar."""
    
    async def create_availability(
        self,
        staff_id: UUID,
        data: StaffAvailabilityCreate
    ) -> StaffAvailabilityResponse:
        """Create availability entry for a staff member on a date."""
    
    async def get_availability(
        self,
        staff_id: UUID,
        start_date: date,
        end_date: date
    ) -> list[StaffAvailabilityResponse]:
        """Get availability entries for a staff member in date range."""
    
    async def update_availability(
        self,
        staff_id: UUID,
        target_date: date,
        data: StaffAvailabilityUpdate
    ) -> StaffAvailabilityResponse:
        """Update availability entry for a specific date."""
    
    async def delete_availability(
        self,
        staff_id: UUID,
        target_date: date
    ) -> None:
        """Delete availability entry for a specific date."""
    
    async def get_available_staff_on_date(
        self,
        target_date: date
    ) -> list[StaffWithAvailability]:
        """Get all staff members available on a specific date."""
```

### 2. Travel Time Service

Calculates travel times between locations using Google Maps API.

```python
class TravelTimeService:
    """Service for calculating travel times between locations."""
    
    async def get_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        departure_time: datetime | None = None
    ) -> int:
        """Get driving time in minutes between two points."""
    
    async def get_travel_matrix(
        self,
        locations: list[tuple[float, float]]
    ) -> dict[tuple[int, int], int]:
        """Get travel times between all pairs of locations."""
    
    def calculate_fallback_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float]
    ) -> int:
        """Calculate travel time using straight-line distance with 1.4x factor."""
```

### 3. Schedule Generation Service

Core service for generating optimized schedules using Timefold.

```python
class ScheduleGenerationService:
    """Service for generating optimized schedules."""
    
    async def generate_schedule(
        self,
        request: ScheduleGenerateRequest
    ) -> ScheduleGenerateResponse:
        """Generate optimized schedule for a date."""
    
    async def preview_schedule(
        self,
        request: ScheduleGenerateRequest
    ) -> ScheduleGenerateResponse:
        """Preview schedule without persisting."""
    
    async def get_capacity(
        self,
        target_date: date
    ) -> ScheduleCapacityResponse:
        """Get scheduling capacity for a date."""
    
    async def get_generation_status(
        self,
        target_date: date
    ) -> ScheduleGenerationStatus:
        """Get status of schedule generation for a date."""
    
    async def insert_emergency_job(
        self,
        request: EmergencyInsertRequest
    ) -> ScheduleGenerateResponse:
        """Insert emergency job into existing schedule."""
    
    async def re_optimize(
        self,
        target_date: date
    ) -> ScheduleGenerateResponse:
        """Re-optimize schedule for a date."""
```

### 4. Conflict Resolution Service

Handles cancellations, reschedules, and waitlist management.

```python
class ConflictResolutionService:
    """Service for handling schedule conflicts."""
    
    async def cancel_appointment(
        self,
        appointment_id: UUID,
        reason: str
    ) -> AppointmentResponse:
        """Cancel an appointment and free up the slot."""
    
    async def reschedule_appointment(
        self,
        appointment_id: UUID,
        new_date: date,
        new_time_start: time,
        new_time_end: time
    ) -> AppointmentResponse:
        """Reschedule an appointment to a new date/time."""
    
    async def get_waitlist(
        self,
        target_date: date | None = None
    ) -> list[WaitlistEntry]:
        """Get waitlist entries, optionally filtered by date."""
    
    async def fill_gap(
        self,
        cancelled_appointment_id: UUID
    ) -> list[WaitlistSuggestion]:
        """Suggest waitlisted jobs to fill a cancelled slot."""
```

### 5. Staff Reassignment Service

Handles staff unavailability and job reassignment.

```python
class StaffReassignmentService:
    """Service for handling staff reassignment."""
    
    async def mark_staff_unavailable(
        self,
        staff_id: UUID,
        target_date: date,
        reason: str,
        from_time: time | None = None
    ) -> list[JobResponse]:
        """Mark staff unavailable and return affected jobs."""
    
    async def reassign_jobs(
        self,
        original_staff_id: UUID,
        new_staff_id: UUID,
        job_ids: list[UUID],
        reason: str
    ) -> ReassignmentResponse:
        """Reassign jobs from one staff to another."""
    
    async def get_coverage_options(
        self,
        target_date: date
    ) -> list[CoverageOption]:
        """Get coverage options showing which staff can cover which jobs."""
```

### 6. Timefold Solver Integration

Defines the optimization problem for Timefold.

```python
@dataclass
class ScheduleJob:
    """Job to be scheduled (Timefold planning entity)."""
    id: str
    property_lat: float
    property_lng: float
    duration_minutes: int
    buffer_minutes: int
    equipment_required: list[str]
    staffing_required: int
    priority_level: int
    weather_sensitive: bool
    city: str
    job_type: str
    created_at: datetime
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
    route_order: int | None = None
```

## Data Models

### New Tables

#### staff_availability

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

#### schedule_waitlist

```sql
CREATE TABLE schedule_waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    preferred_date DATE NOT NULL,
    preferred_time_start TIME,
    preferred_time_end TIME,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notified_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(job_id)
);

CREATE INDEX idx_schedule_waitlist_date ON schedule_waitlist(preferred_date);
```

#### schedule_reassignment

```sql
CREATE TABLE schedule_reassignment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_staff_id UUID NOT NULL REFERENCES staff(id),
    new_staff_id UUID NOT NULL REFERENCES staff(id),
    date DATE NOT NULL,
    reason TEXT NOT NULL,
    jobs_reassigned JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_schedule_reassignment_date ON schedule_reassignment(date);
```

### Modified Tables

#### staff (additions)

```sql
ALTER TABLE staff ADD COLUMN assigned_equipment JSONB DEFAULT '[]';
ALTER TABLE staff ADD COLUMN default_start_address VARCHAR(255);
ALTER TABLE staff ADD COLUMN default_start_city VARCHAR(100);
ALTER TABLE staff ADD COLUMN default_start_lat DECIMAL(10, 8);
ALTER TABLE staff ADD COLUMN default_start_lng DECIMAL(11, 8);
```

#### service_offering (additions)

```sql
ALTER TABLE service_offerings ADD COLUMN buffer_minutes INT DEFAULT 10;
```

#### appointment (additions)

```sql
ALTER TABLE appointments ADD COLUMN cancellation_reason TEXT;
ALTER TABLE appointments ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN rescheduled_from_id UUID REFERENCES appointments(id);
ALTER TABLE appointments ADD COLUMN travel_minutes_from_previous INT;
```

### Pydantic Schemas

```python
# Staff Availability Schemas
class StaffAvailabilityCreate(BaseModel):
    date: date
    start_time: time = time(7, 0)
    end_time: time = time(17, 0)
    is_available: bool = True
    lunch_start: time | None = time(12, 0)
    lunch_duration_minutes: int = Field(default=30, ge=0, le=120)
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
    created_at: datetime
    updated_at: datetime

# Schedule Generation Schemas
class ScheduleGenerateRequest(BaseModel):
    date: date
    job_ids: list[UUID] | None = None
    staff_ids: list[UUID] | None = None
    optimization_time_seconds: int = Field(default=30, ge=5, le=300)

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

class ScheduleGenerateResponse(BaseModel):
    date: date
    assignments: list[ScheduleAssignmentResponse]
    unassigned_jobs: list[UnassignedJobResponse]
    optimization_score: str
    total_travel_minutes: int
    warnings: list[str]
    generation_time_seconds: float

class UnassignedJobResponse(BaseModel):
    job_id: UUID
    reason: str

class ScheduleCapacityResponse(BaseModel):
    date: date
    available_staff: list[StaffCapacity]
    total_available_minutes: int
    jobs_ready_to_schedule: int
    estimated_jobs_capacity: int

# Emergency Insertion Schemas
class EmergencyInsertRequest(BaseModel):
    job_id: UUID
    target_date: date
    priority_level: int = Field(default=3, ge=0, le=3)

# Conflict Resolution Schemas
class AppointmentCancelRequest(BaseModel):
    reason: str

class AppointmentRescheduleRequest(BaseModel):
    new_date: date
    new_time_start: time
    new_time_end: time

class WaitlistEntry(BaseModel):
    id: UUID
    job_id: UUID
    preferred_date: date
    preferred_time_start: time | None
    preferred_time_end: time | None
    created_at: datetime
    notified_at: datetime | None

# Staff Reassignment Schemas
class StaffUnavailableRequest(BaseModel):
    reason: str
    from_time: time | None = None

class ReassignmentRequest(BaseModel):
    new_staff_id: UUID
    job_ids: list[UUID]
    reason: str

class ReassignmentResponse(BaseModel):
    id: UUID
    original_staff_id: UUID
    new_staff_id: UUID
    date: date
    reason: str
    jobs_reassigned: list[UUID]
    created_at: datetime
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Staff Availability Round-Trip

*For any* valid staff availability entry, creating it and then reading it back SHALL return an equivalent entry with all fields preserved.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

### Property 2: Availability Time Validation

*For any* staff availability entry, the start_time SHALL always be before end_time, and lunch_start (if specified) SHALL be within the availability window.

**Validates: Requirements 1.6, 1.7**

### Property 3: Available Staff Query Correctness

*For any* date, querying available staff SHALL return exactly those staff members who have `is_available=true` entries for that date, and SHALL NOT return staff without entries.

**Validates: Requirements 1.5, 1.8**

### Property 4: Equipment Assignment Persistence

*For any* staff member, assigning equipment and then reading the staff record SHALL return the exact equipment list that was assigned.

**Validates: Requirements 2.1, 2.3**

### Property 5: No Availability Violations (Hard Constraint)

*For any* generated schedule, no job SHALL be assigned to a staff member who is unavailable on that date/time according to their availability entry.

**Validates: Requirement 6.1**

### Property 6: No Equipment Violations (Hard Constraint)

*For any* generated schedule, every job requiring specific equipment SHALL only be assigned to staff members who have that equipment in their assigned_equipment list.

**Validates: Requirements 2.2, 2.4, 6.2**

### Property 7: No Time Overlap Violations (Hard Constraint)

*For any* generated schedule, no staff member SHALL have overlapping time slots for different jobs.

**Validates: Requirement 6.3**

### Property 8: Multi-Staff Job Assignment (Hard Constraint)

*For any* job requiring multiple staff members, the generated schedule SHALL create exactly the required number of assignments.

**Validates: Requirement 6.4**

### Property 9: Lunch Break Enforcement (Hard Constraint)

*For any* generated schedule, no job SHALL be scheduled during a staff member's lunch break window.

**Validates: Requirement 6.5**

### Property 10: Start Location Travel Validation (Hard Constraint)

*For any* generated schedule, the first job for each staff member SHALL start at a time that allows travel from their starting location within their shift start time.

**Validates: Requirement 6.6**

### Property 11: End Time Validation (Hard Constraint)

*For any* generated schedule, the last job for each staff member SHALL complete with enough time for travel home before their shift ends.

**Validates: Requirement 6.7**

### Property 12: Schedule Generation Completeness

*For any* schedule generation request, the response SHALL contain all approved jobs either in the assignments list or the unassigned_jobs list with reasons.

**Validates: Requirements 5.1, 5.3, 5.4**

### Property 13: Concurrent Generation Lock

*For any* two concurrent schedule generation requests for the same date, exactly one SHALL succeed and the other SHALL receive HTTP 409 Conflict.

**Validates: Requirements 5.5, 5.6**

### Property 14: Preview Non-Persistence

*For any* schedule preview request, the database state SHALL remain unchanged after the preview completes.

**Validates: Requirement 5.7**

### Property 15: Emergency Job Insertion

*For any* emergency job insertion, the job SHALL either be successfully inserted into the schedule or the response SHALL contain the specific constraint violations preventing insertion.

**Validates: Requirements 9.1, 9.3**

### Property 16: Cancellation State Transition

*For any* appointment cancellation, the appointment status SHALL change to cancelled, and the cancellation_reason and cancelled_at fields SHALL be populated.

**Validates: Requirements 10.1, 10.2**

### Property 17: Reschedule Linkage

*For any* appointment reschedule, the new appointment SHALL have rescheduled_from_id pointing to the original appointment.

**Validates: Requirement 10.3**

### Property 18: Staff Reassignment Record

*For any* staff reassignment, a reassignment record SHALL be created with the original staff, new staff, reason, and list of reassigned job IDs.

**Validates: Requirements 11.1, 11.2, 11.3**

### Property 19: Travel Time Fallback

*For any* travel time calculation where the Google Maps API fails, the service SHALL return a fallback value calculated from straight-line distance with a 1.4x factor.

**Validates: Requirements 4.2, 4.5**

### Property 20: Buffer Time Application

*For any* generated schedule, the time allocated for each job SHALL include the buffer_minutes from the service offering (or default 10 minutes if not configured).

**Validates: Requirements 8.2, 8.4**

## Error Handling

### API Error Responses

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `AVAILABILITY_NOT_FOUND` | 404 | Staff availability entry not found |
| `AVAILABILITY_CONFLICT` | 409 | Availability entry already exists for date |
| `INVALID_TIME_RANGE` | 400 | Start time is not before end time |
| `INVALID_LUNCH_TIME` | 400 | Lunch time is outside availability window |
| `STAFF_NOT_FOUND` | 404 | Staff member not found |
| `JOB_NOT_FOUND` | 404 | Job not found |
| `APPOINTMENT_NOT_FOUND` | 404 | Appointment not found |
| `GENERATION_IN_PROGRESS` | 409 | Schedule generation already in progress for date |
| `NO_AVAILABLE_STAFF` | 400 | No staff available for the requested date |
| `NO_JOBS_TO_SCHEDULE` | 400 | No approved jobs found for scheduling |
| `CONSTRAINT_VIOLATION` | 400 | Hard constraint violation prevents operation |
| `REASSIGNMENT_FAILED` | 400 | No suitable staff available for reassignment |
| `GOOGLE_MAPS_ERROR` | 503 | Google Maps API error (fallback used) |
| `INVALID_COORDINATES` | 400 | Invalid latitude or longitude values |

### Exception Classes

```python
class RouteOptimizationError(Exception):
    """Base exception for route optimization errors."""
    pass

class AvailabilityNotFoundError(RouteOptimizationError):
    """Raised when staff availability entry is not found."""
    pass

class AvailabilityConflictError(RouteOptimizationError):
    """Raised when availability entry already exists."""
    pass

class InvalidTimeRangeError(RouteOptimizationError):
    """Raised when time range is invalid."""
    pass

class GenerationInProgressError(RouteOptimizationError):
    """Raised when schedule generation is already in progress."""
    pass

class ConstraintViolationError(RouteOptimizationError):
    """Raised when a hard constraint would be violated."""
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__(f"Constraint violations: {violations}")

class ReassignmentFailedError(RouteOptimizationError):
    """Raised when job reassignment fails."""
    def __init__(self, unassignable_jobs: list[UUID]):
        self.unassignable_jobs = unassignable_jobs
        super().__init__(f"Cannot reassign jobs: {unassignable_jobs}")
```

## Testing Strategy

### Dual Testing Approach

This feature requires both unit tests and property-based tests:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all valid inputs using randomized testing

### Property-Based Testing Configuration

- **Library**: Hypothesis (Python)
- **Minimum iterations**: 100 per property test
- **Tag format**: `Feature: route-optimization, Property {number}: {property_text}`

### Test Categories

#### Unit Tests

1. **Staff Availability CRUD**
   - Create availability with valid data
   - Create availability with invalid time range (should fail)
   - Update existing availability
   - Delete availability
   - Query availability by date range

2. **Equipment Matching**
   - Staff with matching equipment can be assigned
   - Staff without required equipment cannot be assigned
   - Jobs with no equipment requirements can go to any staff

3. **Travel Time Calculation**
   - Google Maps API success case
   - Google Maps API failure with fallback
   - Batch matrix calculation

4. **Schedule Generation**
   - Generate schedule with valid inputs
   - Handle no available staff
   - Handle no jobs to schedule
   - Concurrent generation lock

5. **Conflict Resolution**
   - Cancel appointment
   - Reschedule appointment
   - Waitlist matching

6. **Staff Reassignment**
   - Mark staff unavailable
   - Reassign jobs to available staff
   - Handle no available staff for reassignment

#### Property-Based Tests

Each correctness property (1-20) should have a corresponding property-based test that:
1. Generates random valid inputs
2. Executes the operation
3. Verifies the property holds

### Coverage Targets

| Component | Unit | Property | Integration |
|-----------|------|----------|-------------|
| StaffAvailabilityService | 85%+ | 80%+ | 70%+ |
| TravelTimeService | 80%+ | 70%+ | 60%+ |
| ScheduleGenerationService | 85%+ | 85%+ | 80%+ |
| ConflictResolutionService | 85%+ | 80%+ | 70%+ |
| StaffReassignmentService | 85%+ | 80%+ | 70%+ |
| API Endpoints | 80%+ | N/A | 85%+ |

### Test Data Requirements

The test data seeding script (`scripts/seed_route_optimization_test_data.py`) should create:
- 20-30 properties with Twin Cities coordinates
- 15-25 jobs with varied types, priorities, equipment needs
- 3-5 staff with different equipment assignments
- Staff availability for 7 days
- Distribution across Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, Rogers

### Functional End-to-End Validation

Every task completion requires functional validation beyond unit tests:

1. **API Validation**: Make actual HTTP requests to verify endpoints work
2. **Data Flow Validation**: Verify data created via API is usable by other features
3. **UI Validation**: For frontend tasks, verify the UI displays and functions correctly
4. **Integration Validation**: Verify features work together (e.g., availability → schedule generation)

**Validation Scripts**: Create validation scripts in `scripts/validate_*.py` for each major feature:
- `scripts/validate_staff_availability.py` - Test availability CRUD and query
- `scripts/validate_schedule_generation.py` - Test full schedule generation flow
- `scripts/validate_conflict_resolution.py` - Test cancellation and reschedule flows
- `scripts/validate_staff_reassignment.py` - Test reassignment flow

**Validation Checklist per Task**:
- [ ] API endpoint responds correctly
- [ ] Data persists to database
- [ ] Data is retrievable via query endpoints
- [ ] Feature integrates with dependent features
- [ ] UI displays data correctly (for frontend tasks)
- [ ] Error cases return appropriate responses
