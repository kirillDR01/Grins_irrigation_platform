# Implementation Plan: Field Operations (Phase 2)

## Overview

This implementation plan breaks down the Field Operations feature into discrete coding tasks. Each task builds on previous work and includes testing requirements. The plan follows the established patterns from Phase 1 (Customer Management) and integrates with existing Customer and Property systems.

## Tasks

- [x] 1. Database Migrations
  - [x] 1.1 Create service_offerings table migration
    - Define table with all columns from design
    - Add indexes for category, pricing_model, is_active, name
    - Add check constraints for enums and positive values
    - _Requirements: 1.1, 1.7, 1.8-1.13_

  - [x] 1.2 Create jobs table migration
    - Define table with all columns from design
    - Add foreign keys to customers, properties, service_offerings
    - Add indexes for customer_id, property_id, status, category, created_at
    - Add check constraints for enums and positive values
    - _Requirements: 2.1, 2.6-2.12, 10.8-10.10_

  - [x] 1.3 Create job_status_history table migration
    - Define table with job_id foreign key
    - Add indexes for job_id, changed_at
    - Add check constraints for status enums
    - _Requirements: 7.1, 7.2_

  - [x] 1.4 Create staff table migration
    - Define table with all columns from design
    - Add indexes for role, skill_level, is_available, is_active, name
    - Add check constraints for enums and positive values
    - _Requirements: 8.1, 8.7-8.10_

  - [x] 1.5 Test migrations
    - Run migrations against test database
    - Verify all tables, indexes, and constraints created
    - Test rollback functionality
    - _Requirements: All database requirements_


- [x] 2. SQLAlchemy Models and Enums
  - [x] 2.1 Create field operations enum types
    - Add ServiceCategory, PricingModel enums
    - Add JobCategory, JobStatus, JobSource enums
    - Add StaffRole, SkillLevel enums
    - _Requirements: 1.2, 1.3, 4.1, 8.2, 8.3_

  - [x] 2.2 Create ServiceOffering model
    - Define model with all fields from design
    - Add model-level validation
    - Configure timestamps
    - _Requirements: 1.1, 1.4-1.13_

  - [x] 2.3 Create Job model
    - Define model with all fields from design
    - Add relationships to Customer, Property, ServiceOffering
    - Configure soft delete behavior
    - Add status transition helper methods
    - _Requirements: 2.1-2.12, 4.1-4.9_

  - [x] 2.4 Create JobStatusHistory model
    - Define model with job relationship
    - Configure cascade delete
    - _Requirements: 7.1-7.4_

  - [x] 2.5 Create Staff model
    - Define model with all fields from design
    - Add model-level validation
    - Configure timestamps
    - _Requirements: 8.1-8.10_

  - [x] 2.6 Write model tests
    - Test model instantiation
    - Test relationships
    - Test helper methods
    - _Requirements: All model requirements_

- [x] 3. Pydantic Schemas
  - [x] 3.1 Create service offering schemas
    - ServiceOfferingCreate with validation
    - ServiceOfferingUpdate with optional fields
    - ServiceOfferingResponse
    - _Requirements: 1.1-1.13, 10.1-10.2, 10.6-10.7_

  - [x] 3.2 Create job schemas
    - JobCreate with validation
    - JobUpdate with optional fields
    - JobStatusUpdate for status transitions
    - JobResponse and JobDetailResponse
    - JobStatusHistoryResponse
    - PriceCalculationResponse
    - _Requirements: 2.1-2.12, 4.1-4.10, 5.1-5.7_

  - [x] 3.3 Create staff schemas
    - StaffCreate with phone validation
    - StaffUpdate with optional fields
    - StaffAvailabilityUpdate
    - StaffResponse
    - _Requirements: 8.1-8.10, 9.1-9.5_

  - [x] 3.4 Create query and pagination schemas
    - JobListParams with all filters
    - StaffListParams with all filters
    - ServiceListParams
    - Paginated response schemas
    - _Requirements: 6.1-6.9_

  - [x] 3.5 Write schema validation tests
    - Test enum validation
    - Test price field validation (non-negative)
    - Test phone normalization
    - Test required field validation
    - **Property 2: Enum Validation Completeness**
    - _Requirements: 10.1-10.7_


- [ ] 4. Repository Layer
  - [ ] 4.1 Create ServiceOfferingRepository
    - Implement create method
    - Implement get_by_id method
    - Implement update method
    - Implement list_with_filters method
    - Implement find_by_category method
    - _Requirements: 1.1, 1.4-1.6, 1.11_

  - [ ] 4.2 Create JobRepository
    - Implement create method
    - Implement get_by_id method
    - Implement update method
    - Implement soft_delete method
    - Implement list_with_filters method
    - Implement find_by_status method
    - Implement find_by_category method
    - Implement find_by_customer method
    - _Requirements: 2.1-2.12, 6.1-6.9_

  - [ ] 4.3 Implement job status history methods
    - Implement add_status_history method
    - Implement get_status_history method
    - _Requirements: 7.1-7.4_

  - [ ] 4.4 Create StaffRepository
    - Implement create method
    - Implement get_by_id method
    - Implement update method
    - Implement list_with_filters method
    - Implement find_available method
    - Implement find_by_role method
    - _Requirements: 8.1-8.6, 9.1-9.5_

  - [ ] 4.5 Write repository tests
    - Test CRUD operations for all repositories
    - Test query methods with various filters
    - Test soft delete behavior
    - Test status history recording
    - _Requirements: All repository requirements_

- [ ] 5. Checkpoint - Database and Repository Layer
  - Ensure all migrations run successfully
  - Ensure all repository tests pass
  - Ask the user if questions arise


- [ ] 6. Service Layer - Service Offerings
  - [ ] 6.1 Create ServiceOfferingService with LoggerMixin
    - Implement create_service method
    - Implement get_service method
    - Implement update_service method
    - Implement deactivate_service method
    - Implement list_services method
    - Implement get_by_category method
    - _Requirements: 1.1-1.13, 11.1, 11.4-11.9_

  - [ ] 6.2 Write ServiceOfferingService unit tests
    - Test CRUD operations with mocked repository
    - Test deactivation preserves record
    - Test category filtering
    - **Property 8: Soft Deactivation Preservation**
    - **Property 14: CRUD Round-Trip Consistency**
    - _Requirements: 1.1-1.13_

- [ ] 7. Service Layer - Jobs
  - [ ] 7.1 Create JobService with LoggerMixin
    - Implement create_job with auto-categorization
    - Implement get_job method
    - Implement update_job method
    - Implement delete_job (soft delete)
    - Implement list_jobs with filters
    - _Requirements: 2.1-2.12, 3.1-3.7, 6.1-6.9, 11.2, 11.4-11.9_

  - [ ] 7.2 Implement auto-categorization logic
    - Implement _determine_category method
    - Handle seasonal job types
    - Handle small repairs
    - Handle quoted amounts
    - Handle partner source
    - _Requirements: 3.1-3.7_

  - [ ] 7.3 Implement status transition logic
    - Define VALID_TRANSITIONS mapping
    - Implement update_status method
    - Implement _validate_transition method
    - Update corresponding timestamp fields
    - Record status history on change
    - _Requirements: 4.1-4.10, 7.1-7.4_

  - [ ] 7.4 Implement price calculation
    - Implement calculate_price method
    - Implement _calculate_by_model for flat pricing
    - Implement _calculate_by_model for zone_based pricing
    - Implement _calculate_by_model for hourly pricing
    - Handle custom pricing (return null)
    - Round to 2 decimal places
    - _Requirements: 5.1-5.7_

  - [ ] 7.5 Write JobService unit tests
    - Test job creation with mocked repositories
    - Test auto-categorization logic
    - Test status transitions (valid and invalid)
    - Test price calculation for all models
    - **Property 1: Job Creation Defaults**
    - **Property 3: Job Auto-Categorization Correctness**
    - **Property 4: Status Transition Validity**
    - **Property 5: Pricing Calculation Correctness**
    - _Requirements: 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7_


- [ ] 8. Service Layer - Staff
  - [ ] 8.1 Create StaffService with LoggerMixin
    - Implement create_staff with phone normalization
    - Implement get_staff method
    - Implement update_staff method
    - Implement deactivate_staff method
    - Implement update_availability method
    - Implement list_staff with filters
    - Implement get_available_staff method
    - Implement get_by_role method
    - _Requirements: 8.1-8.10, 9.1-9.5, 11.3-11.9_

  - [ ] 8.2 Write StaffService unit tests
    - Test CRUD operations with mocked repository
    - Test phone normalization
    - Test availability filtering
    - Test role filtering
    - **Property 8: Soft Deactivation Preservation**
    - **Property 12: Available Staff Filter Correctness**
    - _Requirements: 8.1-8.10, 9.1-9.5_

- [ ] 9. Custom Exceptions
  - [ ] 9.1 Create field operations exceptions
    - FieldOperationsError base class
    - ServiceOfferingNotFoundError
    - JobNotFoundError
    - InvalidStatusTransitionError
    - StaffNotFoundError
    - PropertyCustomerMismatchError
    - _Requirements: 10.1-10.5, 12.2-12.4_

  - [ ] 9.2 Create exception handlers
    - Handler for ServiceOfferingNotFoundError (404)
    - Handler for JobNotFoundError (404)
    - Handler for InvalidStatusTransitionError (400)
    - Handler for StaffNotFoundError (404)
    - Handler for PropertyCustomerMismatchError (400)
    - _Requirements: 12.1-12.7_

- [ ] 10. Checkpoint - Service Layer
  - Ensure all service tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise


- [ ] 11. API Endpoints - Service Offerings
  - [ ] 11.1 Create FastAPI router for services
    - Create api/v1/services.py
    - Set up dependency injection for ServiceOfferingService
    - Register router in main app
    - _Requirements: 12.5-12.7_

  - [ ] 11.2 Implement GET /api/v1/services
    - List all services with pagination
    - Support filtering by category, is_active
    - Return PaginatedServiceResponse
    - _Requirements: 1.11, 12.1, 12.5_

  - [ ] 11.3 Implement GET /api/v1/services/{id}
    - Get service by ID
    - Return 404 if not found
    - Return ServiceOfferingResponse
    - _Requirements: 1.4, 12.1, 12.3_

  - [ ] 11.4 Implement GET /api/v1/services/category/{category}
    - Get services by category
    - Return only active services
    - Return ServiceOfferingResponse[]
    - _Requirements: 1.11, 12.1_

  - [ ] 11.5 Implement POST /api/v1/services
    - Create service offering
    - Return 201 on success
    - Return ServiceOfferingResponse
    - _Requirements: 1.1-1.3, 12.1_

  - [ ] 11.6 Implement PUT /api/v1/services/{id}
    - Update service offering
    - Return 404 if not found
    - Return ServiceOfferingResponse
    - _Requirements: 1.5, 12.1, 12.3_

  - [ ] 11.7 Implement DELETE /api/v1/services/{id}
    - Deactivate service (soft delete)
    - Return 204 on success
    - Return 404 if not found
    - _Requirements: 1.6, 12.1, 12.3_

  - [ ] 11.8 Write service offering API tests
    - Test all endpoints with valid data
    - Test validation errors
    - Test not found scenarios
    - Target 85%+ coverage
    - _Requirements: 1.1-1.13, 12.1-12.7_


- [ ] 12. API Endpoints - Jobs
  - [ ] 12.1 Create FastAPI router for jobs
    - Create api/v1/jobs.py
    - Set up dependency injection for JobService
    - Register router in main app
    - _Requirements: 12.5-12.7_

  - [ ] 12.2 Implement POST /api/v1/jobs
    - Create job request with auto-categorization
    - Validate customer_id, property_id, service_offering_id
    - Return 201 on success
    - Return JobResponse
    - _Requirements: 2.1-2.12, 3.1-3.5, 12.1_

  - [ ] 12.3 Implement GET /api/v1/jobs/{id}
    - Get job with customer, property, service details
    - Include status history
    - Return 404 if not found
    - Return JobDetailResponse
    - _Requirements: 6.1, 7.2, 12.1, 12.3_

  - [ ] 12.4 Implement PUT /api/v1/jobs/{id}
    - Update job details
    - Re-evaluate category if quoted_amount set
    - Return 404 if not found
    - Return JobResponse
    - _Requirements: 3.6, 3.7, 12.1, 12.3_

  - [ ] 12.5 Implement DELETE /api/v1/jobs/{id}
    - Soft delete job
    - Return 204 on success
    - Return 404 if not found
    - _Requirements: 10.11, 12.1, 12.3_

  - [ ] 12.6 Implement GET /api/v1/jobs
    - List jobs with pagination
    - Support all filter parameters
    - Return PaginatedJobResponse
    - _Requirements: 6.1-6.6, 6.9, 12.1_

  - [ ] 12.7 Implement PUT /api/v1/jobs/{id}/status
    - Update job status with validation
    - Record status history
    - Update timestamp fields
    - Return 400 on invalid transition
    - Return JobResponse
    - _Requirements: 4.1-4.10, 7.1, 12.1, 12.2_

  - [ ] 12.8 Implement GET /api/v1/jobs/{id}/history
    - Get job status history
    - Return in chronological order
    - Return JobStatusHistoryResponse[]
    - _Requirements: 7.2, 12.1_

  - [ ] 12.9 Implement GET /api/v1/jobs/ready-to-schedule
    - Get jobs with category=ready_to_schedule
    - Support pagination
    - Return PaginatedJobResponse
    - _Requirements: 6.7, 12.1_

  - [ ] 12.10 Implement GET /api/v1/jobs/needs-estimate
    - Get jobs with category=requires_estimate
    - Support pagination
    - Return PaginatedJobResponse
    - _Requirements: 6.8, 12.1_

  - [ ] 12.11 Implement GET /api/v1/jobs/by-status/{status}
    - Get jobs by status
    - Support pagination
    - Return PaginatedJobResponse
    - _Requirements: 6.2, 12.1_

  - [ ] 12.12 Implement GET /api/v1/customers/{id}/jobs
    - Get all jobs for a customer
    - Support pagination
    - Return PaginatedJobResponse
    - _Requirements: 6.4, 12.1_

  - [ ] 12.13 Implement POST /api/v1/jobs/{id}/calculate-price
    - Calculate price based on service and property
    - Return PriceCalculationResponse
    - _Requirements: 5.1-5.7, 12.1_

  - [ ] 12.14 Write job API tests
    - Test all endpoints with valid data
    - Test validation errors
    - Test status transitions
    - Test price calculation
    - Target 85%+ coverage
    - _Requirements: 2.1-2.12, 3.1-3.7, 4.1-4.10, 5.1-5.7, 6.1-6.9, 7.1-7.4, 12.1-12.7_


- [ ] 13. API Endpoints - Staff
  - [ ] 13.1 Create FastAPI router for staff
    - Create api/v1/staff.py
    - Set up dependency injection for StaffService
    - Register router in main app
    - _Requirements: 12.5-12.7_

  - [ ] 13.2 Implement POST /api/v1/staff
    - Create staff member
    - Normalize phone number
    - Return 201 on success
    - Return StaffResponse
    - _Requirements: 8.1-8.10, 12.1_

  - [ ] 13.3 Implement GET /api/v1/staff/{id}
    - Get staff by ID
    - Return 404 if not found
    - Return StaffResponse
    - _Requirements: 8.4, 12.1, 12.3_

  - [ ] 13.4 Implement PUT /api/v1/staff/{id}
    - Update staff member
    - Return 404 if not found
    - Return StaffResponse
    - _Requirements: 8.5, 12.1, 12.3_

  - [ ] 13.5 Implement DELETE /api/v1/staff/{id}
    - Deactivate staff (soft delete)
    - Return 204 on success
    - Return 404 if not found
    - _Requirements: 8.6, 12.1, 12.3_

  - [ ] 13.6 Implement GET /api/v1/staff
    - List staff with pagination
    - Support filtering by role, skill_level, is_available, is_active
    - Return PaginatedStaffResponse
    - _Requirements: 9.4, 9.5, 12.1_

  - [ ] 13.7 Implement GET /api/v1/staff/available
    - Get available and active staff
    - Return StaffResponse[]
    - _Requirements: 9.3, 12.1_

  - [ ] 13.8 Implement GET /api/v1/staff/by-role/{role}
    - Get staff by role
    - Return only active staff
    - Return StaffResponse[]
    - _Requirements: 9.4, 12.1_

  - [ ] 13.9 Implement PUT /api/v1/staff/{id}/availability
    - Update staff availability
    - Return 404 if not found
    - Return StaffResponse
    - _Requirements: 9.1, 9.2, 12.1, 12.3_

  - [ ] 13.10 Write staff API tests
    - Test all endpoints with valid data
    - Test validation errors
    - Test availability filtering
    - Test role filtering
    - Target 85%+ coverage
    - _Requirements: 8.1-8.10, 9.1-9.5, 12.1-12.7_

- [ ] 14. Checkpoint - API Layer
  - Ensure all API tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise


- [ ] 15. Integration Testing
  - [ ] 15.1 Create test fixtures
    - Database fixtures for service offerings
    - Database fixtures for jobs with customer/property
    - Database fixtures for staff
    - Test client setup
    - _Requirements: All integration requirements_

  - [ ] 15.2 Write job-customer integration tests
    - Test job creation with existing customer
    - Test job creation with non-existent customer (should fail)
    - Test job retrieval includes customer details
    - Test customer deletion preserves jobs
    - **Property 9: Referential Integrity - Job to Customer**
    - _Requirements: 2.2, 10.8, 10.11_

  - [ ] 15.3 Write job-property integration tests
    - Test job creation with valid property
    - Test job creation with property from different customer (should fail)
    - Test job retrieval includes property details
    - Test price calculation uses property zone_count
    - **Property 10: Referential Integrity - Property to Customer**
    - _Requirements: 2.3, 5.2, 5.5, 10.9_

  - [ ] 15.4 Write job-service integration tests
    - Test job creation with active service
    - Test job creation with inactive service (should fail)
    - Test price calculation uses service pricing model
    - **Property 11: Referential Integrity - Job to Service**
    - _Requirements: 2.4, 5.1-5.4, 10.10_

  - [ ] 15.5 Write status workflow integration tests
    - Test complete job lifecycle (requested → closed)
    - Test status history is recorded correctly
    - Test timestamp fields are updated
    - **Property 6: Status History Completeness**
    - **Property 7: Status Timestamp Updates**
    - _Requirements: 4.1-4.9, 7.1-7.4_

  - [ ] 15.6 Write cross-component integration tests
    - Test creating job with all references
    - Test listing jobs with customer filter
    - Test field operations with existing Phase 1 data
    - _Requirements: All integration requirements_


- [ ] 16. Property-Based Tests
  - [ ] 16.1 Write job status transition property tests
    - Test all valid transitions are accepted
    - Test all invalid transitions are rejected
    - Test terminal states have no valid transitions
    - **Property 4: Status Transition Validity**
    - _Requirements: 4.2-4.7, 4.10_

  - [ ] 16.2 Write auto-categorization property tests
    - Test seasonal job types → ready_to_schedule
    - Test small_repair → ready_to_schedule
    - Test quoted_amount set → ready_to_schedule
    - Test partner source → ready_to_schedule
    - Test other cases → requires_estimate
    - **Property 3: Job Auto-Categorization Correctness**
    - _Requirements: 3.1-3.5_

  - [ ] 16.3 Write pricing calculation property tests
    - Test flat pricing returns base_price
    - Test zone_based pricing formula
    - Test hourly pricing formula
    - Test custom pricing returns null
    - Test rounding to 2 decimal places
    - **Property 5: Pricing Calculation Correctness**
    - _Requirements: 5.1-5.6_

  - [ ] 16.4 Write job creation defaults property tests
    - Test status defaults to "requested"
    - Test priority_level defaults to 0
    - **Property 1: Job Creation Defaults**
    - _Requirements: 2.9, 2.10, 4.1_

  - [ ] 16.5 Write category re-evaluation property tests
    - Test setting quoted_amount changes category
    - **Property 13: Category Re-evaluation on Quote**
    - _Requirements: 3.7_

- [ ] 17. Default Data Seeding
  - [ ] 17.1 Create seed data script
    - Create default seasonal services (spring_startup, summer_tuneup, winterization)
    - Create default repair services (head_replacement, diagnostic)
    - Create default installation services (new_system, zone_addition)
    - Set appropriate pricing for each service
    - Set equipment requirements
    - _Requirements: 13.1-13.6_

  - [ ] 17.2 Integrate seeding with migrations
    - Add seed data to migration or startup script
    - Ensure idempotent seeding (don't duplicate on re-run)
    - _Requirements: 13.1-13.6_


- [ ] 18. Documentation and Quality
  - [ ] 18.1 Run quality checks
    - Run ruff check and fix all issues
    - Run mypy and fix all type errors
    - Run pyright and fix all errors
    - _Requirements: Code Standards_

  - [ ] 18.2 Verify test coverage
    - Run pytest with coverage
    - Ensure 85%+ coverage on services
    - Ensure 80%+ coverage on API
    - Ensure 80%+ coverage on repositories
    - _Requirements: Code Standards_

  - [ ] 18.3 Update API documentation
    - Verify OpenAPI spec is complete for all 26 endpoints
    - Add example requests/responses
    - Document error codes
    - _Requirements: 12.5_

  - [ ] 18.4 Update DEVLOG
    - Document implementation progress
    - Document decisions made
    - Document any deviations from design

- [ ] 19. Final Checkpoint
  - Ensure all tests pass (unit, functional, integration, property-based)
  - Ensure all quality checks pass
  - Verify 26 new API endpoints are working
  - Verify integration with Phase 1 Customer/Property system
  - Ask the user if questions arise

## Notes

- All tasks are required for comprehensive coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- This phase builds on Phase 1 - ensure Customer and Property systems are working before starting

## Dependencies

- Phase 1 (Customer Management) must be complete
- Database must be running with Phase 1 migrations applied
- All Phase 1 tests should be passing

