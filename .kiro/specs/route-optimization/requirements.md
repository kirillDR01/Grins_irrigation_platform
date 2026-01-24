# Requirements Document

## Introduction

This document defines the requirements for the Route Optimization feature of the Grin's Irrigation Platform. This feature enables intelligent, constraint-based schedule generation using Timefold, replacing Viktor's manual scheduling process that currently consumes 12+ hours per week during peak season (150+ jobs × 5+ minutes each).

The Route Optimization feature will provide one-click schedule generation that respects equipment requirements, staff availability, geographic batching, and other business constraints. It also includes emergency job insertion, schedule conflict resolution, and staff reassignment capabilities.

## Glossary

- **Timefold**: Open-source constraint satisfaction solver for optimization problems
- **Schedule_Generator**: The service that creates optimized daily schedules using Timefold
- **Staff_Availability_Service**: Service managing staff availability calendar entries
- **Travel_Time_Service**: Service calculating driving times between locations via Google Maps API
- **Schedule_Assignment**: A pairing of a job to a staff member with a specific time slot
- **Hard_Constraint**: A constraint that must never be violated (e.g., staff must be available)
- **Soft_Constraint**: A constraint that should be optimized but can be relaxed (e.g., minimize travel time)
- **Route_Order**: The sequence number of a job in a staff member's daily route
- **Buffer_Time**: Additional time added between jobs for parking, walking, and brief customer interaction
- **Emergency_Job**: A high-priority job that must be inserted into an existing schedule
- **Schedule_Waitlist**: Queue of customers waiting for earlier appointment slots
- **Staff_Reassignment**: Transfer of jobs from one staff member to another

## Requirements

### Requirement 1: Staff Availability Calendar

**User Story:** As an admin, I want to manage staff availability calendars, so that the schedule generator knows when each staff member can work.

#### Acceptance Criteria

1. WHEN an admin creates a staff availability entry, THE Staff_Availability_Service SHALL store the date, start time, end time, lunch break, and availability status
2. WHEN an admin queries staff availability for a date range, THE Staff_Availability_Service SHALL return all availability entries within that range
3. WHEN an admin updates a staff availability entry, THE Staff_Availability_Service SHALL modify the existing entry for that staff member and date
4. WHEN an admin deletes a staff availability entry, THE Staff_Availability_Service SHALL remove the entry and allow default availability to apply
5. WHEN querying available staff for a specific date, THE Staff_Availability_Service SHALL return only staff members with `is_available=true` entries for that date
6. THE Staff_Availability_Service SHALL enforce that start_time is before end_time
7. THE Staff_Availability_Service SHALL enforce that lunch_start is within the availability window
8. WHEN no availability entry exists for a staff member on a date, THE Staff_Availability_Service SHALL treat them as unavailable

### Requirement 2: Equipment Assignment on Staff

**User Story:** As an admin, I want to assign equipment to staff members, so that the schedule generator can match jobs requiring specific equipment to staff who have it.

#### Acceptance Criteria

1. WHEN an admin assigns equipment to a staff member, THE System SHALL store the equipment list on the staff record
2. WHEN a job requires specific equipment, THE Schedule_Generator SHALL only assign it to staff who have that equipment
3. THE System SHALL support multiple equipment items per staff member (e.g., ["compressor", "pipe_puller"])
4. WHEN a staff member has no assigned equipment, THE Schedule_Generator SHALL only assign them jobs requiring no special equipment

### Requirement 3: Staff Starting Location

**User Story:** As an admin, I want to set default starting locations for staff members, so that the schedule generator can calculate travel time from their starting point to the first job.

#### Acceptance Criteria

1. WHEN an admin sets a staff starting location, THE System SHALL store the address, city, latitude, and longitude
2. WHEN generating a schedule, THE Schedule_Generator SHALL calculate travel time from each staff member's starting location to their first assigned job
3. IF a staff member has no starting location configured, THE Schedule_Generator SHALL use a default depot location
4. THE System SHALL validate that latitude and longitude are within valid ranges

### Requirement 4: Travel Time Calculation

**User Story:** As a system, I want to calculate accurate travel times between locations, so that schedules are realistic and achievable.

#### Acceptance Criteria

1. WHEN calculating travel time between two locations, THE Travel_Time_Service SHALL use the Google Maps Distance Matrix API
2. WHEN the Google Maps API is unavailable, THE Travel_Time_Service SHALL fall back to straight-line distance calculation with a 1.4x factor
3. WHEN calculating travel for multiple locations, THE Travel_Time_Service SHALL use batch requests to minimize API calls
4. THE Travel_Time_Service SHALL return travel time in minutes
5. IF a route cannot be calculated, THE Travel_Time_Service SHALL return a default of 60 minutes

### Requirement 5: Schedule Generation

**User Story:** As Viktor, I want to generate an optimized daily schedule with one click, so that I can reduce my scheduling time from 12+ hours per week to under 1 hour.

#### Acceptance Criteria

1. WHEN an admin requests schedule generation for a date, THE Schedule_Generator SHALL create optimized assignments for all approved jobs
2. WHEN generating a schedule, THE Schedule_Generator SHALL complete optimization within 30 seconds for up to 50 jobs
3. WHEN a schedule is generated, THE Schedule_Generator SHALL return the list of assignments, unassigned jobs, total travel time, and optimization score
4. WHEN jobs cannot be assigned due to constraint violations, THE Schedule_Generator SHALL return them in the unassigned_jobs list with reasons
5. THE Schedule_Generator SHALL prevent concurrent generation for the same date using a locking mechanism
6. WHEN schedule generation is already in progress for a date, THE System SHALL return HTTP 409 Conflict
7. WHEN previewing a schedule, THE Schedule_Generator SHALL return proposed assignments without persisting them
8. WHEN checking capacity for a date, THE System SHALL return available staff, total available minutes, and estimated job capacity

### Requirement 6: Hard Constraints

**User Story:** As a system, I want to enforce hard constraints that must never be violated, so that generated schedules are always valid and executable.

#### Acceptance Criteria

1. THE Schedule_Generator SHALL NOT assign a job to a staff member who is unavailable on that date/time
2. THE Schedule_Generator SHALL NOT assign a job requiring specific equipment to staff without that equipment
3. THE Schedule_Generator SHALL NOT create overlapping time slots for the same staff member
4. WHEN a job requires multiple staff members, THE Schedule_Generator SHALL assign the required number of staff
5. THE Schedule_Generator SHALL NOT schedule jobs during a staff member's lunch break
6. THE Schedule_Generator SHALL ensure the first job is reachable from the staff member's starting location within their shift start time
7. THE Schedule_Generator SHALL ensure the last job completes with enough time for the staff member to travel home before their shift ends

### Requirement 7: Soft Constraints

**User Story:** As a system, I want to optimize soft constraints to improve schedule quality, so that routes are efficient and customer preferences are respected.

#### Acceptance Criteria

1. THE Schedule_Generator SHALL minimize total travel time across all staff (weight: 80)
2. THE Schedule_Generator SHALL batch jobs in the same city together (weight: 70)
3. THE Schedule_Generator SHALL batch jobs of the same type together when possible (weight: 50)
4. THE Schedule_Generator SHALL schedule higher priority jobs earlier in the day (weight: 90)
5. THE Schedule_Generator SHALL consider weather sensitivity when scheduling outdoor jobs (weight: 40)
6. THE Schedule_Generator SHALL prefer buffer time between jobs (weight: 60)
7. THE Schedule_Generator SHALL minimize backtracking to previously visited areas (weight: 50)
8. THE Schedule_Generator SHALL respect customer time window preferences when specified (weight: 70)
9. THE Schedule_Generator SHALL give slight preference to earlier job requests (FCFS) (weight: 30)

### Requirement 8: Buffer Time Configuration

**User Story:** As an admin, I want to configure buffer time between jobs, so that staff have time for parking, walking, and brief customer interactions.

#### Acceptance Criteria

1. WHEN an admin sets buffer time on a service offering, THE System SHALL store the buffer_minutes value
2. WHEN generating a schedule, THE Schedule_Generator SHALL add the buffer time to the job duration
3. THE System SHALL support buffer times from 0 to 60 minutes
4. IF no buffer time is configured, THE Schedule_Generator SHALL use a default of 10 minutes

### Requirement 9: Emergency Job Insertion

**User Story:** As Viktor, I want to insert emergency jobs into an existing schedule, so that urgent customer needs can be addressed without manually reworking the entire schedule.

#### Acceptance Criteria

1. WHEN an emergency job is submitted, THE Schedule_Generator SHALL attempt to insert it into the existing schedule
2. WHEN inserting an emergency job, THE Schedule_Generator SHALL re-optimize affected routes while minimizing disruption
3. WHEN an emergency job cannot be inserted without violating hard constraints, THE System SHALL return the constraint violations
4. THE System SHALL support priority levels: normal (0), high (1), urgent (2), emergency (3)
5. WHEN re-optimizing after emergency insertion, THE Schedule_Generator SHALL complete within 15 seconds
6. WHEN jobs are bumped due to emergency insertion, THE System SHALL flag affected customers for notification

### Requirement 10: Schedule Conflict Resolution

**User Story:** As Viktor, I want to handle customer cancellations and reschedules efficiently, so that slots are freed up and waitlisted customers can be notified.

#### Acceptance Criteria

1. WHEN a customer cancels an appointment, THE System SHALL mark the appointment as cancelled and free up the time slot
2. WHEN an appointment is cancelled, THE System SHALL record the cancellation reason and timestamp
3. WHEN a customer requests a reschedule, THE System SHALL create a new appointment linked to the original
4. WHEN a slot becomes available, THE System SHALL check the waitlist for customers who want that date/time
5. WHEN a waitlisted customer matches an available slot, THE System SHALL flag them for notification
6. THE System SHALL support a "fill the gap" operation that suggests waitlisted jobs for cancelled slots
7. WHEN re-optimizing after cancellation, THE Schedule_Generator SHALL attempt to fill gaps with nearby jobs

### Requirement 11: Staff Reassignment

**User Story:** As Viktor, I want to reassign jobs when a staff member becomes unavailable mid-day, so that customers are still served and jobs are not orphaned.

#### Acceptance Criteria

1. WHEN a staff member is marked unavailable, THE System SHALL identify all their remaining jobs for that day
2. WHEN reassigning jobs, THE System SHALL find available staff with matching equipment
3. WHEN jobs are reassigned, THE System SHALL create a reassignment record with original staff, new staff, reason, and job list
4. WHEN no suitable staff is available for reassignment, THE System SHALL return the jobs as unassignable
5. THE System SHALL support partial day unavailability (staff leaves early, arrives late)
6. WHEN viewing coverage options for a date, THE System SHALL show which staff can cover which jobs

### Requirement 12: Minimal Schedule Generation UI

**User Story:** As Viktor, I want a simple interface to trigger and view schedule generation, so that I can generate and review schedules without using the API directly.

#### Acceptance Criteria

1. WHEN Viktor visits the schedule generation page, THE System SHALL display a date picker and generate button
2. WHEN Viktor clicks generate, THE System SHALL show a loading indicator during optimization
3. WHEN generation completes, THE System SHALL display assignments grouped by staff member
4. WHEN jobs cannot be assigned, THE System SHALL highlight them with reasons
5. THE System SHALL display total travel time and optimization metrics
6. WHEN generation is already in progress, THE System SHALL show the current status

### Requirement 13: Test Data Seeding

**User Story:** As a developer, I want realistic test data for route optimization, so that I can test the schedule generator with representative scenarios.

#### Acceptance Criteria

1. THE Seeding_Script SHALL create 20-30 test properties with real Twin Cities coordinates
2. THE Seeding_Script SHALL create 15-25 test jobs with varied types, priorities, and equipment needs
3. THE Seeding_Script SHALL create 3-5 test staff with different equipment assignments
4. THE Seeding_Script SHALL create staff availability entries for the next 7 days
5. THE Seeding_Script SHALL ensure all test properties have valid latitude and longitude
6. THE Seeding_Script SHALL distribute jobs across multiple cities (Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, Rogers)

### Requirement 14: Functional End-to-End Validation

**User Story:** As a developer, I want to validate that each feature works end-to-end from a user's perspective, so that I can ensure the system is usable and not just passing unit tests.

#### Acceptance Criteria

1. WHEN staff availability is created via API, THE System SHALL allow querying that availability and using it in schedule generation
2. WHEN equipment is assigned to staff via API, THE System SHALL correctly match jobs to staff during schedule generation
3. WHEN schedule generation is triggered via API, THE System SHALL create appointments that can be viewed in the schedule UI
4. WHEN an emergency job is inserted via API, THE System SHALL update the existing schedule and the changes SHALL be visible in the UI
5. WHEN an appointment is cancelled via API, THE System SHALL free the slot and waitlisted customers SHALL be notified
6. WHEN staff is marked unavailable via API, THE System SHALL reassign jobs and the reassignments SHALL be visible in the schedule
7. WHEN the schedule generation UI is used, THE System SHALL display real-time generation status and results
8. FOR EACH task completion, THE Developer SHALL verify the feature works by making actual API calls or using the UI, not just running unit tests
