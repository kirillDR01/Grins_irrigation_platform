# Implementation Plan: Route Optimization

## Overview

This implementation plan covers Phase 4A of the Route Optimization feature, implementing constraint-based schedule generation using Timefold. The tasks are organized to build foundational components first (availability, equipment, travel time) before implementing the core optimization service.

## Tasks

- [-] 1. Test Data Seeding (Prerequisite)
  - [-] 1.1 Create test data seeding script
    - Create `scripts/seed_route_optimization_test_data.py`
    - Generate 20-30 test properties with real Twin Cities coordinates
    - Generate 15-25 test jobs with varied types, priorities, equipment needs
    - Generate 3-5 test staff with different equipment assignments
    - Distribute jobs across Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, Rogers
    - _Requirements: 13.1, 13.2, 13.3, 13.6_
  
  - [ ] 1.2 Create staff availability test data
    - Generate availability entries for all test staff for next 7 days
    - Include varied lunch times and availability windows
    - Ensure all test properties have valid lat/lng coordinates
    - _Requirements: 13.4, 13.5_
  
  - [ ] 1.3 Validate test data seeding
    - Run seeding script and verify data in database
    - Query properties, jobs, staff via API to confirm data exists
    - _Requirements: 14.1_

- [ ] 2. Staff Availability Calendar
  - [ ] 2.1 Create staff_availability database migration
    - Create migration file for staff_availability table
    - Add indexes for staff_id, date queries
    - Add unique constraint on (staff_id, date)
    - _Requirements: 1.1, 1.2_
  
  - [ ] 2.2 Create StaffAvailability SQLAlchemy model
    - Define model with all fields (date, start_time, end_time, lunch_start, etc.)
    - Add relationship to Staff model
    - Add validation for time ranges
    - _Requirements: 1.1, 1.6, 1.7_
  
  - [ ] 2.3 Create staff availability Pydantic schemas
    - Create StaffAvailabilityCreate, StaffAvailabilityUpdate, StaffAvailabilityResponse
    - Add validators for time range validation
    - Add validators for lunch time within availability window
    - _Requirements: 1.1, 1.6, 1.7_
  
  - [ ] 2.4 Create StaffAvailabilityRepository
    - Implement CRUD operations
    - Implement get_by_staff_and_date_range
    - Implement get_available_staff_on_date
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ] 2.5 Create StaffAvailabilityService
    - Implement create_availability with validation
    - Implement get_availability for date range
    - Implement update_availability
    - Implement delete_availability
    - Implement get_available_staff_on_date
    - _Requirements: 1.1-1.8_
  
  - [ ] 2.6 Create staff availability API endpoints
    - GET /api/v1/staff/{staff_id}/availability
    - POST /api/v1/staff/{staff_id}/availability
    - PUT /api/v1/staff/{staff_id}/availability/{date}
    - DELETE /api/v1/staff/{staff_id}/availability/{date}
    - GET /api/v1/staff/available-on/{date}
    - _Requirements: 1.1-1.5_
  
  - [ ] 2.7 Functional validation: Staff availability
    - Create `scripts/validate_staff_availability.py`
    - Test creating availability via API
    - Test querying availability by date range
    - Test updating and deleting availability
    - Test get_available_staff_on_date endpoint
    - Verify data persists and is queryable
    - _Requirements: 14.1_
  
  - [ ] 2.8 Write property test for staff availability round-trip
    - **Property 1: Staff Availability Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
  
  - [ ] 2.9 Write property test for availability time validation
    - **Property 2: Availability Time Validation**
    - **Validates: Requirements 1.6, 1.7**
  
  - [ ] 2.10 Write property test for available staff query
    - **Property 3: Available Staff Query Correctness**
    - **Validates: Requirements 1.5, 1.8**

- [ ] 3. Checkpoint - Staff Availability Complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run quality checks: ruff, mypy, pyright, pytest
  - Run functional validation script: `python scripts/validate_staff_availability.py`
  - Verify staff availability can be created, queried, updated, deleted via API

- [ ] 4. Equipment on Staff
  - [ ] 4.1 Create migration to add assigned_equipment to staff table
    - Add assigned_equipment JSONB column with default '[]'
    - _Requirements: 2.1_
  
  - [ ] 4.2 Update Staff model with assigned_equipment field
    - Add assigned_equipment: list[str] | None field
    - _Requirements: 2.1, 2.3_
  
  - [ ] 4.3 Update Staff Pydantic schemas
    - Add assigned_equipment to StaffCreate, StaffUpdate, StaffResponse
    - _Requirements: 2.1_
  
  - [ ] 4.4 Create equipment matching utility function
    - Implement can_staff_handle_job(staff, job) function
    - Return True if staff has all required equipment
    - _Requirements: 2.2, 2.4_
  
  - [ ] 4.5 Functional validation: Equipment assignment
    - Update existing staff via API with equipment
    - Query staff and verify equipment is returned
    - Test equipment matching function with various scenarios
    - _Requirements: 14.2_
  
  - [ ] 4.6 Write property test for equipment assignment persistence
    - **Property 4: Equipment Assignment Persistence**
    - **Validates: Requirements 2.1, 2.3**

- [ ] 5. Staff Starting Location
  - [ ] 5.1 Create migration to add starting location fields to staff table
    - Add default_start_address, default_start_city, default_start_lat, default_start_lng
    - _Requirements: 3.1_
  
  - [ ] 5.2 Update Staff model with starting location fields
    - Add all starting location fields
    - Add coordinate validation
    - _Requirements: 3.1, 3.4_
  
  - [ ] 5.3 Update Staff Pydantic schemas with starting location
    - Add starting location fields to StaffCreate, StaffUpdate, StaffResponse
    - Add validators for coordinate ranges
    - _Requirements: 3.1, 3.4_
  
  - [ ] 5.4 Functional validation: Starting location
    - Update staff via API with starting location
    - Query staff and verify location is returned
    - Test coordinate validation with invalid values
    - _Requirements: 14.2_

- [ ] 6. Google Maps Integration
  - [ ] 6.1 Create TravelTimeService
    - Implement get_travel_time using Google Maps Distance Matrix API
    - Implement get_travel_matrix for batch calculations
    - Implement calculate_fallback_travel_time using haversine formula
    - Add error handling and fallback logic
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ] 6.2 Add Google Maps API configuration
    - Add GOOGLE_MAPS_API_KEY to environment configuration
    - Add rate limiting configuration
    - Document API key setup in README
    - _Requirements: 4.1_
  
  - [ ] 6.3 Functional validation: Travel time calculation
    - Test travel time between two known Twin Cities locations
    - Test fallback calculation when API is unavailable
    - Test batch matrix calculation
    - _Requirements: 14.2_
  
  - [ ] 6.4 Write property test for travel time fallback
    - **Property 19: Travel Time Fallback**
    - **Validates: Requirements 4.2, 4.5**

- [ ] 7. Checkpoint - Foundation Complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run quality checks: ruff, mypy, pyright, pytest
  - Verify staff availability, equipment, starting location, and travel time services work
  - Run all functional validation scripts

- [ ] 8. Buffer Time Configuration
  - [ ] 8.1 Create migration to add buffer_minutes to service_offerings
    - Add buffer_minutes INT column with default 10
    - _Requirements: 8.1_
  
  - [ ] 8.2 Update ServiceOffering model and schemas
    - Add buffer_minutes field to model
    - Add buffer_minutes to Pydantic schemas with validation (0-60)
    - _Requirements: 8.1, 8.3_

- [ ] 9. Timefold Scheduling Service
  - [ ] 9.1 Install and configure Timefold
    - Add timefold-solver to dependencies
    - Create Timefold configuration
    - _Requirements: 5.1_
  
  - [ ] 9.2 Create Timefold domain models
    - Create ScheduleJob dataclass (planning entity)
    - Create ScheduleStaff dataclass
    - Create ScheduleAssignment dataclass (planning variable)
    - Create ScheduleSolution dataclass
    - _Requirements: 5.1_
  
  - [ ] 9.3 Implement hard constraints
    - Staff availability constraint
    - Equipment matching constraint
    - No time overlap constraint
    - Multi-staff job constraint
    - Lunch break constraint
    - Start location travel constraint
    - End time validation constraint
    - _Requirements: 6.1-6.7_
  
  - [ ] 9.4 Implement soft constraints
    - Minimize travel time (weight: 80)
    - Batch by city (weight: 70)
    - Batch by job type (weight: 50)
    - Priority first (weight: 90)
    - Buffer time preference (weight: 60)
    - Minimize backtracking (weight: 50)
    - Customer time preference (weight: 70)
    - FCFS ordering (weight: 30)
    - _Requirements: 7.1-7.4, 7.6-7.9_
  
  - [ ] 9.5 Create TimefoldSolver wrapper service
    - Implement solve method with timeout
    - Implement solution extraction
    - Implement score calculation
    - _Requirements: 5.1, 5.2_
  
  - [ ] 9.6 Write property tests for hard constraints
    - **Property 5: No Availability Violations**
    - **Property 6: No Equipment Violations**
    - **Property 7: No Time Overlap Violations**
    - **Property 8: Multi-Staff Job Assignment**
    - **Property 9: Lunch Break Enforcement**
    - **Property 10: Start Location Travel Validation**
    - **Property 11: End Time Validation**
    - **Validates: Requirements 6.1-6.7**

- [ ] 10. Schedule Generation API
  - [ ] 10.1 Create schedule generation Pydantic schemas
    - Create ScheduleGenerateRequest, ScheduleGenerateResponse
    - Create ScheduleAssignmentResponse, UnassignedJobResponse
    - Create ScheduleCapacityResponse, ScheduleGenerationStatus
    - _Requirements: 5.1, 5.3, 5.4, 5.8_
  
  - [ ] 10.2 Create ScheduleGenerationService
    - Implement generate_schedule with locking
    - Implement preview_schedule (no persistence)
    - Implement get_capacity
    - Implement get_generation_status
    - _Requirements: 5.1-5.8_
  
  - [ ] 10.3 Create schedule generation API endpoints
    - POST /api/v1/schedule/generate
    - POST /api/v1/schedule/preview
    - GET /api/v1/schedule/capacity/{date}
    - GET /api/v1/schedule/generation-status/{date}
    - _Requirements: 5.1, 5.6, 5.7, 5.8_
  
  - [ ] 10.4 Functional validation: Schedule generation
    - Create `scripts/validate_schedule_generation.py`
    - Test schedule generation with seeded test data
    - Verify appointments are created in database
    - Verify assignments can be queried via appointments API
    - Test preview mode doesn't persist data
    - Test capacity endpoint returns correct values
    - Verify optimization completes within 30 seconds
    - _Requirements: 14.3_
  
  - [ ] 10.5 Write property test for schedule generation completeness
    - **Property 12: Schedule Generation Completeness**
    - **Validates: Requirements 5.1, 5.3, 5.4**
  
  - [ ] 10.6 Write property test for concurrent generation lock
    - **Property 13: Concurrent Generation Lock**
    - **Validates: Requirements 5.5, 5.6**
  
  - [ ] 10.7 Write property test for preview non-persistence
    - **Property 14: Preview Non-Persistence**
    - **Validates: Requirement 5.7**
  
  - [ ] 10.8 Write property test for buffer time application
    - **Property 20: Buffer Time Application**
    - **Validates: Requirements 8.2, 8.4**

- [ ] 11. Checkpoint - Core Optimization Complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run quality checks: ruff, mypy, pyright, pytest
  - Run `scripts/validate_schedule_generation.py`
  - Test schedule generation with seeded data
  - Verify optimization completes within 30 seconds for 50 jobs
  - Verify all hard constraints are satisfied in generated schedules

- [ ] 12. Emergency Job Insertion
  - [ ] 12.1 Create EmergencyInsertRequest schema
    - Define job_id, target_date, priority_level fields
    - _Requirements: 9.1, 9.4_
  
  - [ ] 12.2 Implement insert_emergency_job in ScheduleGenerationService
    - Load existing schedule for date
    - Attempt to insert emergency job
    - Re-optimize affected routes
    - Return updated schedule or constraint violations
    - _Requirements: 9.1, 9.2, 9.3, 9.5_
  
  - [ ] 12.3 Create emergency insertion API endpoint
    - POST /api/v1/schedule/insert-emergency
    - POST /api/v1/schedule/re-optimize/{date}
    - _Requirements: 9.1_
  
  - [ ] 12.4 Functional validation: Emergency insertion
    - Generate a schedule for a date
    - Insert an emergency job via API
    - Verify schedule is updated with new job
    - Verify existing appointments are adjusted if needed
    - Verify re-optimization completes within 15 seconds
    - _Requirements: 14.4_
  
  - [ ] 12.5 Write property test for emergency job insertion
    - **Property 15: Emergency Job Insertion**
    - **Validates: Requirements 9.1, 9.3**

- [ ] 13. Schedule Conflict Resolution
  - [ ] 13.1 Create migration to add cancellation fields to appointments
    - Add cancellation_reason, cancelled_at, rescheduled_from_id
    - _Requirements: 10.2, 10.3_
  
  - [ ] 13.2 Create schedule_waitlist table migration
    - Create table with job_id, preferred_date, preferred_time_start/end, notified_at
    - _Requirements: 10.4_
  
  - [ ] 13.3 Create ScheduleWaitlist model and schemas
    - Create SQLAlchemy model
    - Create Pydantic schemas for waitlist entries
    - _Requirements: 10.4, 10.5_
  
  - [ ] 13.4 Create ConflictResolutionService
    - Implement cancel_appointment
    - Implement reschedule_appointment
    - Implement get_waitlist
    - Implement fill_gap suggestions
    - _Requirements: 10.1-10.7_
  
  - [ ] 13.5 Create conflict resolution API endpoints
    - POST /api/v1/appointments/{id}/cancel
    - POST /api/v1/appointments/{id}/reschedule
    - GET /api/v1/schedule/waitlist
    - POST /api/v1/schedule/fill-gap
    - _Requirements: 10.1, 10.3, 10.4, 10.6_
  
  - [ ] 13.6 Functional validation: Conflict resolution
    - Create `scripts/validate_conflict_resolution.py`
    - Generate a schedule with appointments
    - Cancel an appointment via API
    - Verify appointment status is cancelled
    - Verify cancellation reason and timestamp are recorded
    - Test reschedule creates linked appointment
    - Test waitlist matching when slot becomes available
    - _Requirements: 14.5_
  
  - [ ] 13.7 Write property test for cancellation state transition
    - **Property 16: Cancellation State Transition**
    - **Validates: Requirements 10.1, 10.2**
  
  - [ ] 13.8 Write property test for reschedule linkage
    - **Property 17: Reschedule Linkage**
    - **Validates: Requirement 10.3**

- [ ] 14. Staff Reassignment
  - [ ] 14.1 Create schedule_reassignment table migration
    - Create table with original_staff_id, new_staff_id, date, reason, jobs_reassigned
    - _Requirements: 11.3_
  
  - [ ] 14.2 Create ScheduleReassignment model and schemas
    - Create SQLAlchemy model
    - Create Pydantic schemas for reassignment
    - _Requirements: 11.3_
  
  - [ ] 14.3 Create StaffReassignmentService
    - Implement mark_staff_unavailable
    - Implement reassign_jobs
    - Implement get_coverage_options
    - _Requirements: 11.1-11.6_
  
  - [ ] 14.4 Create staff reassignment API endpoints
    - POST /api/v1/staff/{id}/mark-unavailable
    - POST /api/v1/schedule/reassign-staff
    - GET /api/v1/schedule/coverage-options/{date}
    - _Requirements: 11.1, 11.2, 11.6_
  
  - [ ] 14.5 Functional validation: Staff reassignment
    - Create `scripts/validate_staff_reassignment.py`
    - Generate a schedule with staff assignments
    - Mark a staff member unavailable via API
    - Verify affected jobs are identified
    - Reassign jobs to another staff member
    - Verify reassignment record is created
    - Verify appointments are updated with new staff
    - _Requirements: 14.6_
  
  - [ ] 14.6 Write property test for staff reassignment record
    - **Property 18: Staff Reassignment Record**
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [ ] 15. Checkpoint - Backend Complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run quality checks: ruff, mypy, pyright, pytest
  - Run all functional validation scripts:
    - `python scripts/validate_staff_availability.py`
    - `python scripts/validate_schedule_generation.py`
    - `python scripts/validate_conflict_resolution.py`
    - `python scripts/validate_staff_reassignment.py`
  - Test emergency insertion, conflict resolution, and reassignment
  - Verify all 20 correctness properties pass

- [ ] 16. Minimal Schedule Generation UI
  - [ ] 16.1 Create schedule generation frontend types
    - Define TypeScript interfaces for all schedule generation schemas
    - _Requirements: 12.1_
  
  - [ ] 16.2 Create schedule generation API client
    - Implement generateSchedule, previewSchedule, getCapacity, getGenerationStatus
    - _Requirements: 12.1, 12.2_
  
  - [ ] 16.3 Create ScheduleGenerationPage component
    - Add date picker for selecting generation date
    - Add generate button with loading state
    - Display generation status during optimization
    - _Requirements: 12.1, 12.2, 12.6_
  
  - [ ] 16.4 Create ScheduleResults component
    - Display assignments grouped by staff member
    - Show route order, time windows, travel times
    - Highlight unassigned jobs with reasons
    - Display total travel time and optimization metrics
    - _Requirements: 12.3, 12.4, 12.5_
  
  - [ ] 16.5 Functional validation: Schedule generation UI
    - Start frontend dev server
    - Navigate to schedule generation page
    - Select a date and click generate
    - Verify loading indicator appears
    - Verify results display with staff assignments
    - Verify unassigned jobs are highlighted
    - Verify metrics are displayed
    - _Requirements: 14.7_
  
  - [ ] 16.6 Write frontend tests for schedule generation UI
    - Test date picker interaction
    - Test generate button and loading state
    - Test results display
    - _Requirements: 12.1-12.6_

- [ ] 17. Final Checkpoint - Phase 4A Complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run full quality checks: backend and frontend
  - Run all functional validation scripts
  - Demo schedule generation with test data via UI
  - Verify success criteria:
    - Generate schedule for 10+ jobs in < 30 seconds
    - All hard constraints satisfied
    - Travel time reduced vs random assignment
    - Jobs batched by city
    - Equipment requirements satisfied
    - Staff availability respected
    - Lunch breaks enforced
    - Emergency jobs can be inserted
    - Re-optimization completes in < 15 seconds
    - Cancellations free up slots
    - Staff can be marked unavailable mid-day
    - Jobs automatically reassigned
    - UI displays real-time generation status and results

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Functional validation scripts verify end-to-end user workflows
- The implementation order ensures dependencies are satisfied before dependent tasks
