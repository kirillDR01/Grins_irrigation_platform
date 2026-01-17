# Requirements Document: Customer Management

## Introduction

The Customer Management feature is the foundational component of Grin's Irrigation Platform, providing the core data structures and operations for managing customer information, property details, and customer flags. This feature replaces the current Google Spreadsheet-based customer tracking system with a robust, API-driven solution that enables automated workflows, mobile field access, and centralized data management.

## Glossary

- **System**: The Grin's Irrigation Platform backend API
- **Customer**: A client of the irrigation business with contact information and service history
- **Property**: A physical location owned by a customer where irrigation services are performed
- **Customer_Flag**: A status indicator for customer priority, payment history, or behavioral concerns
- **Zone**: A section of an irrigation system controlled by a single valve
- **System_Type**: The category of irrigation system (standard or lake pump)
- **Soft_Delete**: Marking a record as deleted without removing it from the database
- **Service_History**: A record of all jobs performed for a customer
- **Communication_Preference**: Customer opt-in status for SMS and email communications

## Requirements

### Requirement 1: Customer Profile Management

**User Story:** As a business owner, I want to create and manage customer profiles with complete contact information, so that I can maintain accurate customer records and enable automated communications.

#### Acceptance Criteria

1. WHEN a user creates a customer with valid data, THE System SHALL create a new customer record with a unique identifier
2. WHEN a user provides an email address, THE System SHALL validate it against RFC 5322 email format standards
3. WHEN a user provides a phone number, THE System SHALL validate it against North American phone number formats (10 digits)
4. WHEN a user retrieves a customer by ID, THE System SHALL return the complete customer profile including all properties and flags
5. WHEN a user updates customer information, THE System SHALL validate all fields and persist the changes
6. WHEN a user deletes a customer, THE System SHALL perform a soft delete preserving all historical data and related properties
7. THE System SHALL track creation and modification timestamps for all customer records
8. THE System SHALL store first_name and last_name as separate fields for proper name handling
9. THE System SHALL track lead_source (website, google, referral, ad, word_of_mouth) for marketing attribution
10. THE System SHALL track is_new_customer flag to distinguish new customers from returning customers
11. WHEN a customer is created, THE System SHALL default is_new_customer to true
12. THE System SHALL support customer status (active, inactive) for managing customer lifecycle

### Requirement 2: Property Management

**User Story:** As a business owner, I want to associate properties with customers and track property-specific details, so that I can accurately scope work and price services based on system complexity.

#### Acceptance Criteria

1. WHEN a user adds a property to a customer, THE System SHALL create a property record linked to that customer
2. WHEN a user specifies zone count, THE System SHALL validate it is between 1 and 50 inclusive
3. WHEN a user specifies system type, THE System SHALL validate it is either "standard" or "lake_pump"
4. WHEN a user specifies property type, THE System SHALL validate it is either "residential" or "commercial"
5. WHEN a user retrieves customer properties, THE System SHALL return all properties associated with that customer
6. THE System SHALL allow multiple properties per customer
7. THE System SHALL track which property is the primary property for each customer
8. WHEN a user provides an address, THE System SHALL store latitude and longitude coordinates for route optimization
9. THE System SHALL store access instructions including gate codes and special entry requirements
10. THE System SHALL track safety flags including has_dogs for field technician awareness
11. WHEN a user updates a property, THE System SHALL validate the address format and city is within service area

### Requirement 3: Customer Flag Management

**User Story:** As a business owner, I want to flag customers with priority status, payment concerns, or behavioral issues, so that I can provide appropriate service levels and manage business risk.

#### Acceptance Criteria

1. WHEN a user sets a priority flag, THE System SHALL mark the customer as requiring expedited service
2. WHEN a user sets a red flag, THE System SHALL mark the customer as having behavioral or access concerns
3. WHEN a user sets a slow pay flag, THE System SHALL mark the customer as having payment history issues
4. WHEN a user updates customer flags, THE System SHALL persist the changes and track modification timestamps
5. WHEN a user retrieves customer information, THE System SHALL include all active flags
6. THE System SHALL allow multiple flags to be active simultaneously for a single customer

### Requirement 4: Customer Search and Filtering

**User Story:** As a business owner, I want to search and filter customers by various criteria, so that I can quickly find customers for scheduling, follow-up, or reporting purposes.

#### Acceptance Criteria

1. WHEN a user requests a customer list, THE System SHALL return customers with pagination support
2. WHEN a user filters by city, THE System SHALL return only customers with properties in that city
3. WHEN a user filters by status, THE System SHALL return only customers matching that status
4. WHEN a user filters by flags, THE System SHALL return only customers with those flags active
5. WHEN a user combines multiple filters, THE System SHALL apply all filters using AND logic
6. THE System SHALL support case-insensitive search for name and email fields
7. THE System SHALL return results sorted by customer name by default

### Requirement 5: Communication Preferences

**User Story:** As a business owner, I want to track customer communication preferences, so that I can comply with opt-in requirements and respect customer preferences for automated notifications.

#### Acceptance Criteria

1. WHEN a user creates a customer, THE System SHALL default SMS opt-in to false (opted-out)
2. WHEN a user creates a customer, THE System SHALL default email opt-in to false (opted-out)
3. WHEN a user updates SMS opt-in status, THE System SHALL persist the preference
4. WHEN a user updates email opt-in status, THE System SHALL persist the preference
5. WHEN a user retrieves customer information, THE System SHALL include current communication preferences
6. THE System SHALL track when communication preferences were last modified
7. THE System SHALL prevent sending automated communications to customers who have not opted in

### Requirement 6: Data Validation and Integrity

**User Story:** As a system administrator, I want comprehensive data validation, so that the system maintains data quality and prevents invalid records.

#### Acceptance Criteria

1. WHEN a user provides invalid email format, THE System SHALL reject the request with a descriptive error
2. WHEN a user provides invalid phone format, THE System SHALL reject the request with a descriptive error
3. WHEN a user provides zone count outside valid range (1-50), THE System SHALL reject the request with a descriptive error
4. WHEN a user provides invalid system type, THE System SHALL reject the request with a descriptive error
5. WHEN a user provides invalid property type, THE System SHALL reject the request with a descriptive error
6. WHEN a user attempts to create a customer with a phone number that already exists, THE System SHALL reject the request and return the existing customer ID
7. THE System SHALL enforce referential integrity between customers and properties
8. WHEN a customer is soft-deleted, THE System SHALL preserve all related properties and service history
9. THE System SHALL validate city is within the service area (Twin Cities metro: Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, Rogers, and surrounding cities)
10. THE System SHALL normalize phone numbers to a consistent format (removing dashes, parentheses, spaces)

### Requirement 7: Service History Tracking

**User Story:** As a business owner, I want to track all services performed for each customer, so that I can reference past work, identify patterns, and provide informed service recommendations.

#### Acceptance Criteria

1. WHEN a job is completed for a customer, THE System SHALL create a service history record linked to both customer and property
2. WHEN a user retrieves customer information, THE System SHALL include service history summary with total jobs and last service date
3. THE System SHALL track service date, service type, job outcome, and amount charged for each history record
4. THE System SHALL maintain service history even when customers are soft-deleted
5. THE System SHALL allow filtering service history by date range and service type
6. THE System SHALL provide an endpoint to retrieve detailed service history for a customer
7. THE System SHALL track which property each service was performed at
8. THE System SHALL calculate and return total revenue from customer across all services

### Requirement 8: API Operations and Logging

**User Story:** As a system administrator, I want comprehensive logging of all customer management operations, so that I can audit changes, troubleshoot issues, and monitor system usage.

#### Acceptance Criteria

1. WHEN any customer operation is initiated, THE System SHALL log the operation start with relevant parameters
2. WHEN any customer operation completes successfully, THE System SHALL log the completion with result identifiers
3. WHEN any customer operation fails validation, THE System SHALL log the rejection with validation errors
4. WHEN any customer operation encounters an error, THE System SHALL log the failure with error details
5. THE System SHALL use structured logging with the "customer" domain namespace
6. THE System SHALL include request correlation IDs in all log entries
7. THE System SHALL log at appropriate levels (DEBUG for queries, INFO for operations, WARNING for rejections, ERROR for failures)

### Requirement 9: Performance and Scalability

**User Story:** As a system administrator, I want efficient database operations and query performance, so that the system remains responsive as the customer base grows.

#### Acceptance Criteria

1. WHEN a user retrieves a customer by ID, THE System SHALL complete the operation in under 50ms at p95
2. WHEN a user lists customers with filters, THE System SHALL complete the operation in under 200ms at p95
3. THE System SHALL use database indexes on frequently queried fields (email, city, status)
4. THE System SHALL use connection pooling for database operations
5. THE System SHALL support concurrent operations without data corruption

### Requirement 10: API Response Standards

**User Story:** As an API consumer, I want consistent, well-structured API responses, so that I can reliably integrate with the customer management endpoints.

#### Acceptance Criteria

1. WHEN an operation succeeds, THE System SHALL return appropriate HTTP status codes (200, 201, 204)
2. WHEN validation fails, THE System SHALL return 400 Bad Request with detailed error messages
3. WHEN a resource is not found, THE System SHALL return 404 Not Found with descriptive message
4. WHEN a server error occurs, THE System SHALL return 500 Internal Server Error with correlation ID
5. THE System SHALL return JSON responses following consistent schema patterns
6. THE System SHALL include appropriate HTTP headers (Content-Type, Cache-Control)
7. THE System SHALL support CORS for web client access

### Requirement 11: Customer Lookup Operations

**User Story:** As a business owner, I want to quickly look up customers by phone number or email, so that I can identify existing customers when they call or text without searching through lists.

#### Acceptance Criteria

1. WHEN a user searches by phone number, THE System SHALL return matching customer(s) with normalized phone comparison
2. WHEN a user searches by email, THE System SHALL return matching customer(s) with case-insensitive comparison
3. WHEN no customer matches the search criteria, THE System SHALL return an empty result set (not an error)
4. THE System SHALL support partial phone number matching for quick lookup
5. THE System SHALL return customer with all properties and flags in lookup results
6. THE System SHALL complete phone/email lookup operations in under 50ms at p95

### Requirement 12: Bulk Operations

**User Story:** As a business owner, I want to perform bulk operations on customers, so that I can efficiently manage large numbers of customers during seasonal campaigns.

#### Acceptance Criteria

1. WHEN a user requests bulk customer export, THE System SHALL return customer data in CSV format
2. WHEN a user requests customers for a specific city, THE System SHALL return all customers with properties in that city
3. THE System SHALL support bulk update of communication preferences for marketing campaigns
4. THE System SHALL limit bulk operations to 1000 records per request to prevent timeout
5. THE System SHALL log all bulk operations with record counts and operation details
