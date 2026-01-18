# Tasks: Customer Management

## Task 1: Database Setup and Migrations

- [x] 1.1 Set up Alembic for database migrations
  - Create alembic.ini configuration
  - Create migrations directory structure
  - Configure async database connection for migrations
  - **Validates: Requirement 9.4**

- [x] 1.2 Create customers table migration
  - Define customers table with all columns from design
  - Add indexes for phone, email, status, lead_source, name
  - Add check constraints for status enum
  - **Validates: Requirement 1.1, 1.7, 9.3**

- [x] 1.3 Create properties table migration
  - Define properties table with all columns from design
  - Add foreign key to customers table
  - Add indexes for customer_id, city, location
  - Add check constraints for zone_count, system_type, property_type
  - **Validates: Requirement 2.1, 2.2, 2.3, 2.4**

- [x] 1.4 Create updated_at trigger
  - Create trigger function for automatic timestamp updates
  - Apply trigger to customers and properties tables
  - **Validates: Requirement 1.7**

- [x] 1.5 Test migrations
  - Run migrations against test database
  - Verify all tables and indexes created correctly
  - Test rollback functionality
  - **Note: Migrations verified with `alembic history`. Full test requires running database.**

## Task 2: SQLAlchemy Models

- [x] 2.1 Create Customer model
  - Define Customer class with all fields
  - Add relationship to properties
  - Configure soft delete behavior
  - Add model-level validation
  - **Validates: Requirement 1.1, 1.6, 1.8**

- [x] 2.2 Create Property model
  - Define Property class with all fields
  - Add relationship to customer
  - Configure cascade delete behavior
  - **Validates: Requirement 2.1, 2.6**

- [x] 2.3 Create enum types
  - Define CustomerStatus enum
  - Define LeadSource enum
  - Define SystemType enum
  - Define PropertyType enum
  - **Validates: Requirement 1.12, 2.3, 2.4**

## Task 3: Pydantic Schemas

- [x] 3.1 Create customer request schemas
  - CustomerCreate with validation
  - CustomerUpdate with optional fields
  - CustomerFlagsUpdate for flag management
  - **Validates: Requirement 1.2, 1.3, 3.1-3.4**

- [x] 3.2 Create customer response schemas
  - CustomerResponse with all fields
  - CustomerDetailResponse with properties and service history
  - ServiceHistorySummary for aggregated data
  - **Validates: Requirement 1.4, 7.2**

- [x] 3.3 Create property schemas
  - PropertyCreate with validation
  - PropertyUpdate with optional fields
  - PropertyResponse with all fields
  - **Validates: Requirement 2.2, 2.3, 2.4, 2.8-2.11**

- [x] 3.4 Create query and pagination schemas
  - CustomerListParams for filtering
  - PaginatedResponse for list results
  - BulkPreferencesUpdate for bulk operations
  - **Validates: Requirement 4.1-4.7, 12.3-12.4**

- [x] 3.5 Write schema validation tests
  - Test phone number validation and normalization
  - Test email validation
  - Test zone count bounds
  - Test enum validation
  - **PBT: Property 4, Property 6**

## Task 4: Repository Layer

- [x] 4.1 Create CustomerRepository
  - Implement create method
  - Implement get_by_id method
  - Implement update method
  - Implement soft_delete method
  - **Validates: Requirement 1.1, 1.4, 1.5, 1.6**

- [x] 4.2 Implement customer query methods
  - Implement find_by_phone method
  - Implement find_by_phone_partial method
  - Implement find_by_email method
  - Implement list_with_filters method
  - **Validates: Requirement 4.1-4.7, 11.1-11.4**

- [x] 4.3 Implement customer flag methods
  - Implement update_flags method
  - Implement get_service_summary method
  - **Validates: Requirement 3.4, 7.2**

- [x] 4.4 Create PropertyRepository
  - Implement create method
  - Implement get_by_id method
  - Implement update method
  - Implement delete method
  - Implement get_by_customer_id method
  - **Validates: Requirement 2.1, 2.5, 2.6**

- [x] 4.5 Implement property primary flag methods
  - Implement clear_primary_flag method
  - Implement set_primary method
  - **Validates: Requirement 2.7**

- [x] 4.6 Write repository tests
  - Test CRUD operations
  - Test query methods with various filters
  - Test soft delete behavior
  - Test primary property uniqueness
  - **PBT: Property 1, Property 2, Property 3**

## Task 5: Service Layer

- [x] 5.1 Create CustomerService with LoggerMixin
  - Implement create_customer with duplicate check
  - Implement get_customer with properties and history
  - Implement update_customer with validation
  - Implement delete_customer (soft delete)
  - **Validates: Requirement 1.1-1.6, 6.6, 8.1-8.4**

- [x] 5.2 Implement customer list and lookup methods
  - Implement list_customers with pagination
  - Implement lookup_by_phone with normalization
  - Implement lookup_by_email case-insensitive
  - **Validates: Requirement 4.1-4.7, 11.1-11.6**

- [x] 5.3 Implement customer flag management
  - Implement update_flags method
  - Add logging for flag changes
  - **Validates: Requirement 3.1-3.6**

- [x] 5.4 Implement bulk operations
  - Implement bulk_update_preferences
  - Implement export_customers_csv
  - Add rate limiting (1000 records max)
  - **Validates: Requirement 12.1-12.5**

- [x] 5.5 Create PropertyService with LoggerMixin
  - Implement add_property with primary flag handling
  - Implement update_property
  - Implement delete_property
  - Implement set_primary
  - **Validates: Requirement 2.1, 2.5-2.11**

- [x] 5.6 Write service tests
  - Test customer CRUD with mocked repository
  - Test duplicate phone detection
  - Test soft delete preserves properties
  - Test primary property uniqueness
  - Target 85%+ coverage
  - **PBT: Property 1, Property 2, Property 3, Property 5**

## Task 6: Custom Exceptions

- [x] 6.1 Create customer exceptions
  - CustomerError base class
  - CustomerNotFoundError
  - DuplicateCustomerError
  - PropertyNotFoundError
  - ValidationError
  - **Validates: Requirement 6.1-6.5, 10.2-10.4**

- [x] 6.2 Create exception handlers
  - Handler for CustomerNotFoundError (404)
  - Handler for DuplicateCustomerError (400)
  - Handler for PropertyNotFoundError (404)
  - Handler for ValidationError (400)
  - **Validates: Requirement 10.1-10.4**

## Task 7: API Endpoints - Customer CRUD

- [x] 7.1 Create FastAPI router structure
  - Create api/v1/router.py
  - Create api/v1/customers.py
  - Set up dependency injection for services
  - **Validates: Requirement 10.5-10.7**

- [x] 7.2 Implement POST /api/v1/customers
  - Create customer endpoint
  - Return 201 on success
  - Return 400 on duplicate phone
  - Add request correlation ID
  - **Validates: Requirement 1.1, 6.6, 8.5-8.7, 10.1**

- [x] 7.3 Implement GET /api/v1/customers/{id}
  - Get customer with properties and service history
  - Return 404 if not found
  - Include all flags and preferences
  - **Validates: Requirement 1.4, 3.5, 5.5**

- [x] 7.4 Implement PUT /api/v1/customers/{id}
  - Update customer endpoint
  - Validate all fields
  - Return 404 if not found
  - **Validates: Requirement 1.5, 6.1-6.5**

- [x] 7.5 Implement DELETE /api/v1/customers/{id}
  - Soft delete customer
  - Return 204 on success
  - Preserve related data
  - **Validates: Requirement 1.6, 6.8**

- [x] 7.6 Implement GET /api/v1/customers
  - List customers with pagination
  - Support all filter parameters
  - Support sorting
  - **Validates: Requirement 4.1-4.7**

- [x] 7.7 Write customer CRUD API tests
  - Test all endpoints with valid data
  - Test validation errors
  - Test not found scenarios
  - Test pagination
  - Target 85%+ coverage

## Task 8: API Endpoints - Customer Operations

- [x] 8.1 Implement PUT /api/v1/customers/{id}/flags
  - Update customer flags
  - Return updated customer
  - Log flag changes
  - **Validates: Requirement 3.1-3.6**

- [x] 8.2 Implement GET /api/v1/customers/lookup/phone/{phone}
  - Lookup by phone with normalization
  - Support partial matching
  - Return empty array if not found
  - **Validates: Requirement 11.1, 11.3-11.5**

- [x] 8.3 Implement GET /api/v1/customers/lookup/email/{email}
  - Lookup by email case-insensitive
  - Return empty array if not found
  - **Validates: Requirement 11.2, 11.3**

- [x] 8.4 Implement GET /api/v1/customers/{id}/service-history
  - Get service history for customer
  - Support date range filtering
  - Support service type filtering
  - **Validates: Requirement 7.1-7.8**

- [x] 8.5 Implement POST /api/v1/customers/export
  - Export customers to CSV
  - Support city filter
  - Limit to 1000 records
  - **Validates: Requirement 12.1-12.2, 12.4**

- [x] 8.6 Implement PUT /api/v1/customers/bulk/preferences
  - Bulk update communication preferences
  - Limit to 1000 customer IDs
  - Return success/failure counts
  - **Validates: Requirement 12.3-12.5**

- [x] 8.7 Write customer operations API tests
  - Test lookup endpoints
  - Test service history
  - Test bulk operations
  - Test rate limiting

## Task 9: API Endpoints - Properties

- [x] 9.1 Implement POST /api/v1/customers/{customer_id}/properties
  - Add property to customer
  - Handle primary flag
  - Validate all fields
  - **Validates: Requirement 2.1, 2.7-2.11**

- [x] 9.2 Implement GET /api/v1/customers/{customer_id}/properties
  - List all properties for customer
  - Include all property details
  - **Validates: Requirement 2.5**

- [x] 9.3 Implement GET /api/v1/properties/{id}
  - Get property by ID
  - Return 404 if not found
  - **Validates: Requirement 2.5**

- [x] 9.4 Implement PUT /api/v1/properties/{id}
  - Update property
  - Validate all fields
  - **Validates: Requirement 2.2-2.4, 2.8-2.11**

- [x] 9.5 Implement DELETE /api/v1/properties/{id}
  - Delete property
  - Return 204 on success
  - **Validates: Requirement 2.6**

- [x] 9.6 Implement PUT /api/v1/properties/{id}/primary
  - Set property as primary
  - Clear other primary flags
  - **Validates: Requirement 2.7**

- [x] 9.7 Write property API tests
  - Test all property endpoints
  - Test primary flag behavior
  - Test validation errors
  - Target 85%+ coverage

## Task 10: Integration Testing

- [x] 10.1 Create test fixtures
  - Database fixtures for customers
  - Database fixtures for properties
  - Test client setup
  - **Validates: Requirement 9.5**

- [x] 10.2 Write customer workflow integration tests
  - Test complete customer lifecycle
  - Test customer with multiple properties
  - Test soft delete behavior
  - **Validates: Requirement 1.1-1.12**

- [x] 10.3 Write property workflow integration tests
  - Test property CRUD workflow
  - Test primary property switching
  - Test cascade behavior
  - **Validates: Requirement 2.1-2.11**

- [x] 10.4 Write search and filter integration tests
  - Test pagination with large datasets
  - Test all filter combinations
  - Test sorting options
  - **Validates: Requirement 4.1-4.7**

- [ ]* 10.5 Write performance tests
  - Test customer lookup under 50ms
  - Test list operation under 200ms
  - Test concurrent operations
  - **Validates: Requirement 9.1-9.2, 9.5, 11.6**

## Task 11: Property-Based Tests

- [x] 11.1 Write phone normalization property tests
  - Test idempotence: normalize(normalize(x)) == normalize(x)
  - Test various input formats
  - **PBT: Property 6**

- [x] 11.2 Write zone count bounds property tests
  - Test all values in valid range accepted
  - Test values outside range rejected
  - **PBT: Property 4**

- [x] 11.3 Write phone uniqueness property tests
  - Test no two active customers share phone
  - Test after normalization
  - **PBT: Property 1**

- [x] 11.4 Write primary property uniqueness tests
  - Test at most one primary per customer
  - Test setting new primary clears old
  - **PBT: Property 3**

- [x] 11.5 Write communication opt-in default tests
  - Test new customers default to opted-out
  - Test both SMS and email
  - **PBT: Property 5**

## Task 12: Documentation and Quality

- [x] 12.1 Run quality checks
  - Run ruff check and fix all issues
  - Run mypy and fix all type errors
  - Run pyright and fix all errors
  - **Validates: Code Standards**

- [x] 12.2 Verify test coverage
  - Run pytest with coverage
  - Ensure 85%+ coverage on services
  - Ensure 80%+ coverage on API
  - **Validates: Code Standards**

- [x] 12.3 Update API documentation
  - Verify OpenAPI spec is complete
  - Add example requests/responses
  - Document error codes
  - **Validates: Requirement 10.5**

- [x] 12.4 Update DEVLOG
  - Document implementation progress
  - Document decisions made
  - Document any deviations from design
