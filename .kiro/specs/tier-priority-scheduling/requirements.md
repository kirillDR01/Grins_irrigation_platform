# Requirements Document

## Introduction

The platform advertises tier-based priority scheduling as a perk for Professional and Premium service agreement tiers, but the backend never sets the `priority_level` field during job generation. All jobs default to priority 0 (normal) regardless of tier, making the scheduling priority feature non-functional. This spec covers wiring the tier-to-priority mapping into job generation so the existing scheduler and UI correctly reflect tier-based priority.

## Glossary

- **Job_Generator**: The `JobGenerator` service (`job_generator.py`) responsible for creating `Job` records from service agreements.
- **Job**: A database record representing a scheduled service visit, containing a `priority_level` field (0=normal, 1=high, 2=urgent).
- **Schedule_Solver**: The `ScheduleSolverService` (`schedule_solver_service.py`) that orders and assigns jobs to staff, already sorting by `priority_level` descending.
- **Service_Agreement_Tier**: A database record defining a service package tier (Essential, Professional, or Premium) with associated pricing and perks.
- **Tier_Priority_Map**: A mapping from tier name to integer priority level: Essential→0, Professional→1, Premium→2.
- **Admin_UI**: The frontend admin interface displaying job lists and job details, including priority badges.

## Requirements

### Requirement 1: Tier-to-Priority Mapping During Job Generation

**User Story:** As a platform operator, I want jobs to be created with the correct priority level based on the customer's service agreement tier, so that higher-tier customers receive scheduling priority as advertised.

#### Acceptance Criteria

1. WHEN the Job_Generator creates a Job for an Essential tier agreement, THE Job_Generator SHALL set the Job priority_level to 0 (normal).
2. WHEN the Job_Generator creates a Job for a Professional tier agreement, THE Job_Generator SHALL set the Job priority_level to 1 (high).
3. WHEN the Job_Generator creates a Job for a Premium tier agreement, THE Job_Generator SHALL set the Job priority_level to 2 (urgent).
4. WHEN the Job_Generator creates a Job for a winterization-only tier agreement, THE Job_Generator SHALL set the Job priority_level to 0 (normal).
5. FOR ALL generated Jobs, THE Job priority_level SHALL match the value defined in the Tier_Priority_Map for the associated Service_Agreement_Tier.

### Requirement 2: Scheduler Respects Priority

**User Story:** As a platform operator, I want the schedule solver to order higher-priority jobs before lower-priority jobs, so that Premium and Professional customers are scheduled first within each batch.

#### Acceptance Criteria

1. THE Schedule_Solver SHALL sort jobs by priority_level descending before applying other scheduling criteria.
2. WHEN two jobs have equal priority_level, THE Schedule_Solver SHALL apply secondary sort criteria (city, duration) to determine order.
3. WHEN a priority_level 2 (urgent) job and a priority_level 0 (normal) job compete for the same time slot, THE Schedule_Solver SHALL assign the priority_level 2 job first.

### Requirement 3: Priority Visibility in Admin UI

**User Story:** As an admin, I want to see the tier-based priority level on job list and detail views, so that I can understand why certain jobs are ordered higher in the schedule.

#### Acceptance Criteria

1. THE Admin_UI job list view SHALL display a priority badge for each Job showing "Normal", "High", or "Urgent" based on the Job priority_level.
2. THE Admin_UI job detail view SHALL display a priority badge showing "Normal", "High", or "Urgent" based on the Job priority_level.
3. WHEN a Job has priority_level 0, THE Admin_UI SHALL display the badge as "Normal".
4. WHEN a Job has priority_level 1, THE Admin_UI SHALL display the badge as "High".
5. WHEN a Job has priority_level 2, THE Admin_UI SHALL display the badge as "Urgent".

### Requirement 4: Priority Consistency Across Job Lifecycle

**User Story:** As a platform operator, I want the priority level to remain consistent from job creation through scheduling, so that the tier benefit is reliably applied.

#### Acceptance Criteria

1. THE Job priority_level value set during generation SHALL persist unchanged through scheduling and completion.
2. WHEN the Job_Generator generates multiple jobs for a single agreement, THE Job_Generator SHALL assign the same priority_level to all jobs in that agreement.
3. FOR ALL Jobs linked to a Service_Agreement_Tier, reading the Job priority_level and then mapping it back through the Tier_Priority_Map SHALL produce the original tier name (round-trip property).
