# Requirements Document: Field Operations (Phase 2)

## Introduction

The Field Operations feature is Phase 2 of Grin's Irrigation Platform, building on the Customer Management foundation established in Phase 1. This phase implements three interconnected components: Service Catalog, Job Request Management, and Staff Management. Together, these components replace Viktor's spreadsheet-based job tracking system with a robust, API-driven solution that enables automated job categorization, pricing calculation, and staff assignment.

## Glossary

- **System**: The Grin's Irrigation Platform backend API
- **Service_Offering**: A defined service type with pricing model and requirements
- **Job**: A work request linked to a customer, property, and optionally a service offering
- **Staff_Member**: An employee who can be assigned to jobs
- **Job_Category**: Classification of job readiness (ready_to_schedule, requires_estimate)
- **Job_Status**: Current state in the job lifecycle workflow
- **Pricing_Model**: Method for calculating job price (flat, zone_based, hourly, custom)
- **Service_Category**: Type of service (seasonal, repair, installation, diagnostic, landscaping)
- **Staff_Role**: Employee function (tech, sales, admin)
- **Skill_Level**: Employee experience level (junior, senior, lead)
- **Lien_Eligible**: Whether a service qualifies for mechanic's lien filing
- **Auto_Categorization**: Automatic assignment of job category based on job type and customer

## Requirements

### Requirement 1: Service Catalog Management

**User Story:** As a business owner, I want to define and manage service offerings with pricing models, so that I can standardize pricing and accurately quote jobs based on service type and property characteristics.

#### Acceptance Criteria

1. WHEN a user creates a service offering with valid data, THE System SHALL create a new service record with a unique identifier
2. WHEN a user specifies a service category, THE System SHALL validate it is one of: seasonal, repair, installation, diagnostic, landscaping
3. WHEN a user specifies a pricing model, THE System SHALL validate it is one of: flat, zone_based, hourly, custom
4. WHEN a user retrieves a service offering by ID, THE System SHALL return the complete service details including equipment requirements
5. WHEN a user updates a service offering, THE System SHALL validate all fields and persist the changes
6. WHEN a user deactivates a service offering, THE System SHALL set is_active to false without deleting the record
7. THE System SHALL track creation and modification timestamps for all service records
8. THE System SHALL store base_price and price_per_zone as decimal values with 2 decimal places
9. THE System SHALL store estimated_duration_minutes and duration_per_zone_minutes as integers
10. THE System SHALL store equipment_required as a JSON array of equipment names
11. WHEN a user lists services by category, THE System SHALL return only services matching that category
12. THE System SHALL track lien_eligible flag for services that qualify for mechanic's lien filing
13. THE System SHALL track requires_prepay flag for services requiring payment before work

### Requirement 2: Job Request Creation

**User Story:** As a business owner, I want to create job requests linked to customers and properties, so that I can track all work requests in a centralized system replacing my spreadsheet.

#### Acceptance Criteria

1. WHEN a user creates a job request with valid data, THE System SHALL create a new job record with a unique identifier
2. WHEN a user creates a job, THE System SHALL require a valid customer_id reference
3. WHEN a user provides a property_id, THE System SHALL validate it belongs to the specified customer
4. WHEN a user provides a service_offering_id, THE System SHALL validate it references an active service
5. WHEN a user specifies job_type, THE System SHALL validate it matches expected job types
6. THE System SHALL track creation and modification timestamps for all job records
7. THE System SHALL store quoted_amount and final_amount as decimal values with 2 decimal places
8. THE System SHALL store equipment_required and materials_required as JSON arrays
9. WHEN a user creates a job, THE System SHALL default status to "requested"
10. WHEN a user creates a job, THE System SHALL default priority_level to 0 (normal)
11. THE System SHALL track source (website, google, referral, phone, partner) for lead attribution
12. THE System SHALL store source_details as JSON for additional attribution data

### Requirement 3: Job Auto-Categorization

**User Story:** As a business owner, I want jobs to be automatically categorized as "ready to schedule" or "requires estimate", so that I can quickly identify which jobs need attention and which can be scheduled immediately.

#### Acceptance Criteria

1. WHEN a job is created with job_type of spring_startup, summer_tuneup, or winterization, THE System SHALL set category to "ready_to_schedule"
2. WHEN a job is created with job_type of small_repair, THE System SHALL set category to "ready_to_schedule"
3. WHEN a job is created with an approved estimate (quoted_amount is set), THE System SHALL set category to "ready_to_schedule"
4. WHEN a job is created with source of "partner", THE System SHALL set category to "ready_to_schedule"
5. WHEN a job is created that does not match ready_to_schedule criteria, THE System SHALL set category to "requires_estimate"
6. WHEN a user manually updates job category, THE System SHALL allow override of auto-categorization
7. THE System SHALL re-evaluate category when quoted_amount is set on a job that previously required estimate

### Requirement 4: Job Status Workflow

**User Story:** As a business owner, I want jobs to follow a defined status workflow, so that I can track job progress and ensure proper completion of all steps.

#### Acceptance Criteria

1. WHEN a job is created, THE System SHALL set initial status to "requested"
2. WHEN a user transitions job status from requested, THE System SHALL only allow transition to approved or cancelled
3. WHEN a user transitions job status from approved, THE System SHALL only allow transition to scheduled or cancelled
4. WHEN a user transitions job status from scheduled, THE System SHALL only allow transition to in_progress or cancelled
5. WHEN a user transitions job status from in_progress, THE System SHALL only allow transition to completed or cancelled
6. WHEN a user transitions job status from completed, THE System SHALL only allow transition to closed
7. WHEN a job status is cancelled or closed, THE System SHALL prevent any further status transitions
8. WHEN a job status changes, THE System SHALL record the transition in job status history
9. WHEN a job status changes, THE System SHALL update the corresponding timestamp field (approved_at, scheduled_at, started_at, completed_at, closed_at)
10. IF a user attempts an invalid status transition, THEN THE System SHALL reject the request with a descriptive error

### Requirement 5: Job Pricing Calculation

**User Story:** As a business owner, I want the system to calculate job prices based on service type and property zones, so that I can quickly generate accurate quotes without manual calculation.

#### Acceptance Criteria

1. WHEN calculating price for a flat pricing model, THE System SHALL return the service base_price
2. WHEN calculating price for a zone_based pricing model, THE System SHALL return base_price + (price_per_zone × property.zone_count)
3. WHEN calculating price for an hourly pricing model, THE System SHALL return base_price × (estimated_duration_minutes / 60)
4. WHEN calculating price for a custom pricing model, THE System SHALL return null indicating manual quote required
5. WHEN a property has no zone_count set, THE System SHALL use 1 as the default for zone_based calculations
6. WHEN calculating price, THE System SHALL round to 2 decimal places
7. THE System SHALL provide an endpoint to calculate price without persisting the result

### Requirement 6: Job Query and Filtering

**User Story:** As a business owner, I want to search and filter jobs by various criteria, so that I can quickly find jobs for scheduling, follow-up, or reporting purposes.

#### Acceptance Criteria

1. WHEN a user requests a job list, THE System SHALL return jobs with pagination support
2. WHEN a user filters by status, THE System SHALL return only jobs matching that status
3. WHEN a user filters by category, THE System SHALL return only jobs matching that category
4. WHEN a user filters by customer_id, THE System SHALL return only jobs for that customer
5. WHEN a user filters by date range, THE System SHALL return jobs created within that range
6. WHEN a user combines multiple filters, THE System SHALL apply all filters using AND logic
7. THE System SHALL provide an endpoint to get jobs ready to schedule
8. THE System SHALL provide an endpoint to get jobs needing estimates
9. THE System SHALL return results sorted by created_at descending by default

### Requirement 7: Job Status History

**User Story:** As a business owner, I want to view the complete status history of a job, so that I can audit job progress and identify bottlenecks in the workflow.

#### Acceptance Criteria

1. WHEN a job status changes, THE System SHALL create a history record with previous status, new status, and timestamp
2. WHEN a user retrieves job history, THE System SHALL return all status transitions in chronological order
3. THE System SHALL track who initiated each status change (when user tracking is implemented)
4. THE System SHALL include notes or reason for status change when provided

### Requirement 8: Staff Profile Management

**User Story:** As a business owner, I want to create and manage staff profiles with roles and skills, so that I can assign appropriate staff to jobs based on requirements.

#### Acceptance Criteria

1. WHEN a user creates a staff member with valid data, THE System SHALL create a new staff record with a unique identifier
2. WHEN a user specifies a role, THE System SHALL validate it is one of: tech, sales, admin
3. WHEN a user specifies a skill level, THE System SHALL validate it is one of: junior, senior, lead
4. WHEN a user retrieves a staff member by ID, THE System SHALL return the complete staff profile including certifications
5. WHEN a user updates a staff member, THE System SHALL validate all fields and persist the changes
6. WHEN a user deactivates a staff member, THE System SHALL set is_active to false without deleting the record
7. THE System SHALL track creation and modification timestamps for all staff records
8. THE System SHALL store certifications as a JSON array
9. THE System SHALL store hourly_rate as a decimal value with 2 decimal places
10. THE System SHALL require phone number for all staff members

### Requirement 9: Staff Availability Management

**User Story:** As a business owner, I want to track staff availability, so that I can schedule jobs only when appropriate staff are available.

#### Acceptance Criteria

1. WHEN a user updates staff availability, THE System SHALL persist the is_available flag
2. WHEN a user adds availability notes, THE System SHALL store the notes for scheduling reference
3. WHEN a user lists available staff, THE System SHALL return only staff with is_available = true and is_active = true
4. WHEN a user lists staff by role, THE System SHALL return only staff matching that role
5. THE System SHALL support filtering staff by skill level

### Requirement 10: Data Validation and Integrity

**User Story:** As a system administrator, I want comprehensive data validation, so that the system maintains data quality and prevents invalid records.

#### Acceptance Criteria

1. WHEN a user provides invalid service category, THE System SHALL reject the request with a descriptive error
2. WHEN a user provides invalid pricing model, THE System SHALL reject the request with a descriptive error
3. WHEN a user provides invalid job status, THE System SHALL reject the request with a descriptive error
4. WHEN a user provides invalid staff role, THE System SHALL reject the request with a descriptive error
5. WHEN a user provides invalid skill level, THE System SHALL reject the request with a descriptive error
6. WHEN a user provides negative price values, THE System SHALL reject the request with a descriptive error
7. WHEN a user provides negative duration values, THE System SHALL reject the request with a descriptive error
8. THE System SHALL enforce referential integrity between jobs and customers
9. THE System SHALL enforce referential integrity between jobs and properties
10. THE System SHALL enforce referential integrity between jobs and service offerings
11. WHEN a customer is soft-deleted, THE System SHALL preserve all related jobs

### Requirement 11: API Operations and Logging

**User Story:** As a system administrator, I want comprehensive logging of all field operations, so that I can audit changes, troubleshoot issues, and monitor system usage.

#### Acceptance Criteria

1. WHEN any service offering operation is initiated, THE System SHALL log the operation start with relevant parameters
2. WHEN any job operation is initiated, THE System SHALL log the operation start with relevant parameters
3. WHEN any staff operation is initiated, THE System SHALL log the operation start with relevant parameters
4. WHEN any operation completes successfully, THE System SHALL log the completion with result identifiers
5. WHEN any operation fails validation, THE System SHALL log the rejection with validation errors
6. WHEN any operation encounters an error, THE System SHALL log the failure with error details
7. THE System SHALL use structured logging with appropriate domain namespaces (service, job, staff)
8. THE System SHALL include request correlation IDs in all log entries
9. THE System SHALL log at appropriate levels (DEBUG for queries, INFO for operations, WARNING for rejections, ERROR for failures)

### Requirement 12: API Response Standards

**User Story:** As an API consumer, I want consistent, well-structured API responses, so that I can reliably integrate with the field operations endpoints.

#### Acceptance Criteria

1. WHEN an operation succeeds, THE System SHALL return appropriate HTTP status codes (200, 201, 204)
2. WHEN validation fails, THE System SHALL return 400 Bad Request with detailed error messages
3. WHEN a resource is not found, THE System SHALL return 404 Not Found with descriptive message
4. WHEN a server error occurs, THE System SHALL return 500 Internal Server Error with correlation ID
5. THE System SHALL return JSON responses following consistent schema patterns
6. THE System SHALL include appropriate HTTP headers (Content-Type, Cache-Control)
7. THE System SHALL support CORS for web client access

### Requirement 13: Default Data Seeding

**User Story:** As a business owner, I want the system pre-populated with standard services and staff, so that I can start using the system immediately without manual setup.

#### Acceptance Criteria

1. WHEN the system is initialized, THE System SHALL create default seasonal service offerings (spring_startup, summer_tuneup, winterization)
2. WHEN the system is initialized, THE System SHALL create default repair service offerings (head_replacement, diagnostic)
3. WHEN the system is initialized, THE System SHALL create default installation service offerings (new_system, zone_addition)
4. THE System SHALL set appropriate pricing for default services based on business requirements
5. THE System SHALL set appropriate equipment requirements for default services
6. THE System SHALL allow modification of default services after creation

