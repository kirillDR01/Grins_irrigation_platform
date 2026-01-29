# Implementation Plan: Schedule Workflow Improvements (Phase 8)

## Overview

This implementation plan breaks down the Schedule Workflow Improvements feature into discrete coding tasks. The plan covers three major priorities: Schedule Clear & Reset Features, Invoice Management System, and Authentication & Login System. Tasks are organized to build incrementally, with authentication implemented first (security foundation), followed by schedule clear features, and finally the invoice management system.

## Implementation Order

1. **Phase 8A-8C**: Authentication & Login System (security first)
2. **Phase 8D-8F**: Schedule Clear & Reset Features
3. **Phase 8G-8K**: Invoice Management System
4. **Phase 8L**: Comprehensive Unit Testing (90%+ coverage)
5. **Phase 8M**: End-to-End UI Validation (agent-browser)
6. **Phase 8N**: Documentation & Quality

## Tasks

### Phase 8A: Authentication - Database & Models

- [ ] 1. Database Migrations for Authentication
  - [x] 1.1 Create staff authentication columns migration
    - Add username (VARCHAR(50), UNIQUE, nullable)
    - Add password_hash (VARCHAR(255), nullable)
    - Add is_login_enabled (BOOLEAN, default FALSE)
    - Add last_login (TIMESTAMP WITH TIME ZONE)
    - Add failed_login_attempts (INTEGER, default 0)
    - Add locked_until (TIMESTAMP WITH TIME ZONE)
    - Add index on username WHERE username IS NOT NULL
    - _Requirements: 15.1-15.8_

  - [x] 1.2 Test authentication migration
    - Run migration against test database
    - Verify columns added correctly
    - Test rollback functionality
    - _Requirements: 15.1-15.8_

- [ ] 2. Authentication Models and Enums
  - [x] 2.1 Create UserRole enum
    - Add ADMIN, MANAGER, TECH values
    - Add to models/enums.py
    - _Requirements: 17.1_

  - [x] 2.2 Update Staff model with authentication fields
    - Add username field (unique, nullable)
    - Add password_hash field (nullable)
    - Add is_login_enabled field (default False)
    - Add last_login field
    - Add failed_login_attempts field (default 0)
    - Add locked_until field
    - _Requirements: 15.1-15.8_

  - [x] 2.3 Write model tests for authentication fields
    - Test Staff model with auth fields
    - Test UserRole enum values
    - _Requirements: 15.1-15.8, 17.1_

- [ ] 3. Authentication Schemas
  - [x] 3.1 Create authentication request/response schemas
    - LoginRequest (username, password, remember_me)
    - LoginResponse (access_token, token_type, expires_in, user)
    - TokenResponse (access_token, token_type, expires_in)
    - UserResponse (id, username, name, email, role, is_active)
    - ChangePasswordRequest with password validation
    - _Requirements: 14.1-14.8, 18.1-18.8_

  - [x] 3.2 Write schema validation tests
    - Test password strength validation
    - Test required field validation
    - _Requirements: 16.1-16.4_

### Phase 8B: Authentication - Service Layer

- [ ] 4. Authentication Service
  - [x] 4.1 Create AuthService with LoggerMixin
    - Implement authenticate method
    - Implement _verify_password method (bcrypt)
    - Implement _hash_password method (bcrypt, cost 12)
    - Implement _create_access_token method (JWT, 15 min)
    - Implement _create_refresh_token method (JWT, 7 days)
    - Implement verify_access_token method
    - Implement verify_refresh_token method
    - Implement refresh_access_token method
    - Implement change_password method
    - Implement get_current_user method
    - _Requirements: 14.1-14.8, 16.1-16.8_

  - [x] 4.2 Implement account lockout logic
    - Track failed login attempts
    - Lock account after 5 failed attempts
    - Set lockout duration to 15 minutes
    - Reset counter on successful login
    - _Requirements: 16.5-16.7_

  - [x] 4.3 Create authentication exceptions
    - InvalidCredentialsError
    - AccountLockedError
    - TokenExpiredError
    - InvalidTokenError
    - UserNotFoundError
    - _Requirements: 14.2, 16.5-16.7_

  - [x] 4.5 Implement CSRF protection middleware
    - Create CSRFMiddleware class
    - Generate secure CSRF tokens (secrets.token_urlsafe)
    - Validate X-CSRF-Token header against csrf_token cookie
    - Skip CSRF check for safe methods (GET, HEAD, OPTIONS)
    - Return 403 Forbidden on validation failure
    - _Requirements: 16.8_

  - [x] 4.4 Write AuthService unit tests
    - Test successful authentication
    - Test invalid credentials
    - Test account lockout
    - Test token generation and verification
    - Test password change
    - **Property 1: Password Hashing Round-Trip**
    - _Requirements: 14.1-14.8, 16.1-16.8_

- [x] 5. Role-Based Access Control
  - [x] 5.1 Create permission decorator
    - Implement require_roles decorator
    - Support multiple allowed roles
    - Return 403 Forbidden for unauthorized access
    - _Requirements: 17.1-17.12_

  - [x] 5.2 Create FastAPI dependencies for auth
    - get_current_user dependency
    - get_current_active_user dependency
    - require_admin dependency
    - require_manager_or_admin dependency
    - _Requirements: 17.1-17.12, 20.1-20.6_

  - [x] 5.3 Write RBAC unit tests
    - Test permission decorator
    - Test role-based access
    - **Property 2: Role Permission Hierarchy**
    - _Requirements: 17.1-17.12_

- [x] 6. Checkpoint - Authentication Service Layer
  - Ensure all authentication service tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise

### Phase 8C: Authentication - API & Frontend

- [ ] 7. Authentication API Endpoints
  - [x] 7.1 Create FastAPI router for auth
    - Create api/v1/auth.py
    - Set up dependency injection for AuthService
    - Register router in main app
    - _Requirements: 18.1-18.8_

  - [x] 7.2 Implement POST /api/v1/auth/login
    - Authenticate user with username/password
    - Return access token and user info
    - Set refresh token as HttpOnly cookie
    - Generate and set CSRF token cookie (not HttpOnly)
    - Return CSRF token in response body
    - Return 401 on invalid credentials
    - _Requirements: 14.1-14.2, 16.8, 18.1, 18.6-18.8_

  - [x] 7.3 Implement POST /api/v1/auth/logout
    - Clear refresh token cookie
    - Clear CSRF token cookie
    - Return 204 No Content
    - _Requirements: 14.8, 16.8, 18.2_

  - [x] 7.4 Implement POST /api/v1/auth/refresh
    - Verify refresh token from cookie
    - Generate new access token
    - Return 401 if refresh token invalid
    - _Requirements: 18.3, 18.8_

  - [x] 7.5 Implement GET /api/v1/auth/me
    - Return current user info
    - Require valid access token
    - _Requirements: 18.4_

  - [x] 7.6 Implement POST /api/v1/auth/change-password
    - Verify current password
    - Validate new password strength
    - Update password hash
    - Return 204 No Content
    - _Requirements: 18.5_

  - [x] 7.7 Write authentication API tests
    - Test login success and failure
    - Test logout
    - Test token refresh
    - Test password change
    - Target 85%+ coverage
    - _Requirements: 14.1-14.8, 18.1-18.8_

- [ ] 8. Frontend Authentication Components
  - [x] 8.1 Create AuthProvider context
    - Manage user state
    - Manage access token in memory
    - Manage CSRF token (read from cookie, send in headers)
    - Implement login function
    - Implement logout function
    - Implement token refresh
    - Auto-refresh before expiration
    - _Requirements: 16.8, 19.1-19.8, 20.5-20.6_

  - [x] 8.2 Create LoginPage component
    - Username input with User icon
    - Password input with visibility toggle
    - Remember me checkbox
    - Sign In button with loading state
    - Error alert for invalid credentials
    - Redirect to dashboard on success
    - Add data-testid attributes
    - _Requirements: 19.1-19.7_

  - [x] 8.3 Create ProtectedRoute component
    - Check authentication state
    - Redirect to login if not authenticated
    - Check role permissions
    - Display AccessDenied for unauthorized roles
    - _Requirements: 20.1-20.4_

  - [x] 8.4 Create UserMenu component
    - Display user name
    - Dropdown with settings and logout
    - Add data-testid attributes
    - _Requirements: 19.8_

  - [x] 8.5 Update App.tsx with auth routes
    - Wrap routes with AuthProvider
    - Add /login route
    - Protect all other routes with ProtectedRoute
    - _Requirements: 20.1-20.6_

  - [x] 8.6 Create auth API client
    - login function
    - logout function
    - refresh function
    - me function
    - changePassword function
    - _Requirements: 18.1-18.8_

  - [x] 8.7 Write frontend auth tests
    - Test LoginPage rendering
    - Test form validation
    - Test login flow
    - Test protected route redirect
    - Test user menu
    - _Requirements: 19.1-19.8, 20.1-20.6_

- [x] 9. Checkpoint - Authentication Complete
  - Ensure all authentication tests pass
  - Ensure login flow works end-to-end
  - Ensure protected routes redirect correctly
  - Ask the user if questions arise

### Phase 8D: Schedule Clear - Database & Models

- [ ] 10. Database Migrations for Schedule Clear
  - [x] 10.1 Create schedule_clear_audit table migration
    - id (UUID, PRIMARY KEY)
    - schedule_date (DATE, NOT NULL)
    - appointments_data (JSONB, NOT NULL)
    - jobs_reset (UUID[], NOT NULL)
    - appointment_count (INTEGER, NOT NULL)
    - cleared_by (UUID, REFERENCES staff)
    - cleared_at (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
    - notes (TEXT)
    - created_at (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
    - Add indexes on schedule_date and cleared_at
    - _Requirements: 5.1-5.6_

  - [x] 10.2 Test schedule clear audit migration
    - Run migration against test database
    - Verify table and indexes created
    - Test rollback functionality
    - _Requirements: 5.1-5.6_

- [ ] 11. Schedule Clear Models
  - [x] 11.1 Create ScheduleClearAudit model
    - Define model with all fields from design
    - Add relationship to Staff (cleared_by)
    - Configure timestamps
    - _Requirements: 5.1-5.6_

  - [x] 11.2 Write model tests
    - Test model instantiation
    - Test JSON serialization of appointments_data
    - _Requirements: 5.1-5.6_

- [ ] 12. Schedule Clear Schemas
  - [x] 12.1 Create schedule clear request/response schemas
    - ScheduleClearRequest (schedule_date, notes)
    - ScheduleClearResponse (audit_id, schedule_date, appointments_deleted, jobs_reset, cleared_at)
    - ScheduleClearAuditResponse (id, schedule_date, appointment_count, cleared_at, cleared_by, notes)
    - ScheduleClearAuditDetailResponse (extends with appointments_data, jobs_reset)
    - _Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5_

  - [x] 12.2 Write schema validation tests
    - Test date validation
    - Test response serialization
    - _Requirements: 3.1-3.7, 5.1-5.6_

### Phase 8E: Schedule Clear - Service & Repository

- [ ] 13. Schedule Clear Repository
  - [x] 13.1 Create ScheduleClearAuditRepository
    - Implement create method
    - Implement get_by_id method
    - Implement find_since method (for recent clears)
    - _Requirements: 5.1-5.6, 6.1-6.5_

  - [x] 13.2 Write repository tests
    - Test CRUD operations
    - Test find_since filtering
    - _Requirements: 5.1-5.6, 6.1-6.5_

- [ ] 14. Schedule Clear Service
  - [x] 14.1 Create ScheduleClearService with LoggerMixin
    - Implement clear_schedule method
    - Get appointments for date
    - Serialize appointment data for audit
    - Find jobs with status 'scheduled' to reset
    - Create audit log before deletion
    - Delete appointments
    - Reset job statuses to 'approved'
    - Return response with counts
    - _Requirements: 3.1-3.7_

  - [x] 14.2 Implement get_recent_clears method
    - Get clears from last N hours (default 24)
    - Return list of audit records
    - _Requirements: 6.1-6.5_

  - [x] 14.3 Implement get_clear_details method
    - Get full audit record by ID
    - Include appointments_data and jobs_reset
    - _Requirements: 6.3_

  - [x] 14.4 Create schedule clear exceptions
    - ScheduleClearAuditNotFoundError
    - _Requirements: 22.3_

  - [x] 14.5 Write ScheduleClearService unit tests
    - Test clear_schedule with appointments
    - Test clear_schedule with no appointments
    - Test job status reset logic
    - Test audit log creation
    - **Property 3: Clear Schedule Audit Completeness**
    - **Property 4: Job Status Reset Correctness**
    - _Requirements: 3.1-3.7, 5.1-5.6_

- [x] 15. Checkpoint - Schedule Clear Service Layer
  - Ensure all schedule clear service tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise

### Phase 8F: Schedule Clear - API & Frontend

- [ ] 16. Schedule Clear API Endpoints
  - [x] 16.1 Create FastAPI router for schedule clear
    - Create api/v1/schedule_clear.py
    - Set up dependency injection for ScheduleClearService
    - Register router in main app
    - Apply require_manager_or_admin to all endpoints
    - _Requirements: 17.5-17.6, 22.5-22.7_

  - [x] 16.2 Implement POST /api/v1/schedule/clear
    - Clear appointments for specified date
    - Create audit log
    - Reset job statuses
    - Return ScheduleClearResponse
    - _Requirements: 3.1-3.7, 21.1_

  - [x] 16.3 Implement GET /api/v1/schedule/clear/recent
    - Get recently cleared schedules (last 24 hours)
    - Return ScheduleClearAuditResponse[]
    - _Requirements: 6.1-6.2, 21.4_

  - [x] 16.4 Implement GET /api/v1/schedule/clear/{audit_id}
    - Get detailed audit log
    - Return 404 if not found
    - Return ScheduleClearAuditDetailResponse
    - _Requirements: 6.3, 22.3_

  - [x] 16.5 Write schedule clear API tests
    - Test clear endpoint
    - Test recent clears endpoint
    - Test audit details endpoint
    - Test authorization (manager/admin only)
    - Target 85%+ coverage
    - _Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5_

- [ ] 17. Frontend Schedule Clear Components
  - [x] 17.1 Create ClearResultsButton component
    - Button with X icon
    - Variant: outline
    - Only visible when schedule results present
    - Add data-testid="clear-results-btn"
    - _Requirements: 1.1-1.6_

  - [x] 17.2 Create JobSelectionControls component
    - "Select All" and "Deselect All" text links
    - Style: text-sm text-blue-600 hover:underline
    - Add data-testid attributes
    - _Requirements: 2.1-2.5_

  - [x] 17.3 Create ClearDayButton component
    - Button with Trash2 icon
    - Variant: destructive outline
    - Add data-testid="clear-day-btn"
    - _Requirements: 3.1_

  - [x] 17.4 Create ClearDayDialog component
    - AlertTriangle warning icon
    - Show date in title
    - Show appointment count
    - Show affected jobs preview (first 5 + "and X more")
    - Show status reset notice
    - Show audit notice
    - Cancel and "Clear Schedule" buttons
    - Add data-testid="clear-day-dialog"
    - _Requirements: 4.1-4.8_

  - [x] 17.5 Create RecentlyClearedSection component
    - Show clears from last 24 hours
    - Display date, count, timestamp
    - "View Details" action
    - Add data-testid attributes
    - _Requirements: 6.1-6.5_

  - [x] 17.6 Update GenerateRoutesTab with clear features
    - Add ClearResultsButton to results section
    - Add JobSelectionControls above job list
    - Implement select all/deselect all logic
    - Implement clear results logic
    - _Requirements: 1.1-1.6, 2.1-2.5_

  - [x] 17.7 Update ScheduleTab with clear day feature
    - Add ClearDayButton to toolbar
    - Integrate ClearDayDialog
    - Add RecentlyClearedSection below calendar
    - Implement clear day API call
    - _Requirements: 3.1-3.7, 4.1-4.8, 6.1-6.5_

  - [x] 17.8 Create schedule clear API client
    - clearSchedule function
    - getRecentClears function
    - getClearDetails function
    - _Requirements: 3.1-3.7, 6.1-6.5_

  - [x] 17.9 Write frontend schedule clear tests
    - Test ClearResultsButton visibility
    - Test JobSelectionControls
    - Test ClearDayDialog
    - Test RecentlyClearedSection
    - _Requirements: 1.1-1.6, 2.1-2.5, 3.1-3.7, 4.1-4.8, 6.1-6.5_

- [x] 18. Checkpoint - Schedule Clear Complete
  - Ensure all schedule clear tests pass
  - Ensure clear results works in Generate Routes tab
  - Ensure clear day works in Schedule tab
  - Ask the user if questions arise

### Phase 8G: Invoice - Database & Models

- [ ] 19. Database Migrations for Invoices
  - [x] 19.1 Create invoices table migration
    - id (UUID, PRIMARY KEY)
    - job_id (UUID, REFERENCES jobs, NOT NULL)
    - customer_id (UUID, REFERENCES customers, NOT NULL)
    - invoice_number (VARCHAR(50), UNIQUE, NOT NULL)
    - amount (DECIMAL(10,2), NOT NULL)
    - late_fee_amount (DECIMAL(10,2), DEFAULT 0)
    - total_amount (DECIMAL(10,2), NOT NULL)
    - invoice_date (DATE, DEFAULT CURRENT_DATE)
    - due_date (DATE, NOT NULL)
    - status (VARCHAR(50), DEFAULT 'draft')
    - payment_method (VARCHAR(50))
    - payment_reference (VARCHAR(255))
    - paid_at (TIMESTAMP WITH TIME ZONE)
    - paid_amount (DECIMAL(10,2))
    - reminder_count (INTEGER, DEFAULT 0)
    - last_reminder_sent (TIMESTAMP WITH TIME ZONE)
    - lien_eligible (BOOLEAN, DEFAULT FALSE)
    - lien_warning_sent (TIMESTAMP WITH TIME ZONE)
    - lien_filed_date (DATE)
    - line_items (JSONB)
    - notes (TEXT)
    - created_at, updated_at timestamps
    - Add check constraints for status and payment_method enums
    - Add check constraints for positive amounts
    - Add indexes on job_id, customer_id, status, dates, lien_eligible
    - _Requirements: 7.1-7.10_

  - [x] 19.2 Create invoice_number_seq sequence
    - PostgreSQL sequence for thread-safe numbering
    - Start at 1
    - _Requirements: 7.1_

  - [x] 19.3 Add payment_collected_on_site to jobs table
    - Add column (BOOLEAN, DEFAULT FALSE)
    - _Requirements: 10.6_

  - [x] 19.4 Test invoice migrations
    - Run migrations against test database
    - Verify tables, indexes, constraints, sequence
    - Test rollback functionality
    - _Requirements: 7.1-7.10_

- [ ] 20. Invoice Models and Enums
  - [x] 20.1 Create InvoiceStatus enum
    - DRAFT, SENT, VIEWED, PAID, PARTIAL
    - OVERDUE, LIEN_WARNING, LIEN_FILED, CANCELLED
    - Add to models/enums.py
    - _Requirements: 8.1-8.10_

  - [x] 20.2 Create PaymentMethod enum
    - CASH, CHECK, VENMO, ZELLE, STRIPE
    - Add to models/enums.py
    - _Requirements: 9.2_

  - [x] 20.3 Create Invoice model
    - Define model with all fields from design
    - Add relationships to Job and Customer
    - Configure timestamps
    - _Requirements: 7.1-7.10_

  - [x] 20.4 Update Job model with payment_collected_on_site
    - Add field (default False)
    - _Requirements: 10.6_

  - [x] 20.6 Update Job schemas with payment_collected_on_site
    - [x] Add payment_collected_on_site to JobResponse schema
    - [x] Add payment_collected_on_site to JobUpdate schema (optional field)
    - [x] Add payment_collected_on_site to job completion workflow schemas
    - _Requirements: 10.5.1-10.5.3_

  - [x] 20.5 Write model tests
    - Test Invoice model instantiation
    - Test relationships
    - Test enum values
    - _Requirements: 7.1-7.10, 8.1-8.10, 9.2_

- [ ] 21. Invoice Schemas
  - [x] 21.1 Create invoice line item schema
    - InvoiceLineItem (description, quantity, unit_price, total)
    - Validation for positive values
    - _Requirements: 7.8_

  - [x] 21.2 Create invoice request/response schemas
    - InvoiceCreate (job_id, amount, late_fee_amount, due_date, line_items, notes)
    - InvoiceUpdate (amount, late_fee_amount, due_date, line_items, notes)
    - InvoiceResponse (all fields)
    - InvoiceDetailResponse (with job and customer)
    - _Requirements: 7.1-7.10, 13.1-13.7_

  - [x] 21.3 Create payment and lien schemas
    - PaymentRecord (amount, payment_method, payment_reference)
    - LienFiledRequest (filing_date, notes)
    - LienDeadlineResponse (approaching_45_day, approaching_120_day)
    - _Requirements: 9.1-9.7, 11.1-11.8_

  - [x] 21.4 Create invoice list params schema
    - InvoiceListParams (page, page_size, status, customer_id, date_from, date_to, lien_eligible, sort_by, sort_order)
    - PaginatedInvoiceResponse
    - _Requirements: 13.1-13.7_

  - [x] 21.5 Write schema validation tests
    - Test line item validation
    - Test payment amount validation
    - Test enum validation
    - _Requirements: 7.1-7.10, 9.1-9.7_

### Phase 8H: Invoice - Service & Repository

- [ ] 22. Invoice Repository
  - [x] 22.1 Create InvoiceRepository
    - Implement create method
    - Implement get_by_id method
    - Implement update method
    - Implement list_with_filters method
    - Implement get_next_sequence method (for invoice numbers)
    - Implement find_overdue method
    - Implement find_lien_warning_due method
    - Implement find_lien_filing_due method
    - _Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7_

  - [x] 22.2 Write repository tests
    - Test CRUD operations
    - Test sequence generation
    - Test filter methods
    - Test lien deadline queries
    - _Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7_

- [ ] 23. Invoice Service
  - [x] 23.1 Create InvoiceService with LoggerMixin
    - Define LIEN_ELIGIBLE_TYPES constant
    - Implement create_invoice method
    - Implement _generate_invoice_number method
    - Implement get_invoice method
    - Implement update_invoice method
    - Implement cancel_invoice method
    - Implement list_invoices method
    - _Requirements: 7.1-7.10, 13.1-13.7_

  - [x] 23.2 Implement invoice status operations
    - Implement send_invoice method (draft → sent)
    - Implement mark_viewed method (sent → viewed)
    - Implement mark_overdue method
    - _Requirements: 8.1-8.6_

  - [x] 23.3 Implement payment recording
    - Implement record_payment method
    - Calculate new paid amount
    - Determine status (paid vs partial)
    - Store payment method and reference
    - _Requirements: 9.1-9.7_

  - [x] 23.4 Implement reminder functionality
    - Implement send_reminder method
    - Increment reminder_count
    - Update last_reminder_sent
    - _Requirements: 12.1-12.5_

  - [x] 23.5 Implement lien tracking
    - Implement send_lien_warning method
    - Implement mark_lien_filed method
    - Implement get_lien_deadlines method
    - _Requirements: 11.1-11.8_

  - [x] 23.6 Implement generate_from_job method
    - Validate job exists and not deleted
    - Check payment_collected_on_site flag
    - Use final_amount or quoted_amount
    - Create line items from job
    - _Requirements: 10.1-10.7_

  - [x] 23.7 Create invoice exceptions
    - InvoiceNotFoundError
    - InvalidInvoiceOperationError
    - _Requirements: 22.2-22.4_

  - [x] 23.8 Write InvoiceService unit tests

- [x] 24. Checkpoint - Invoice Service Layer
  - Ensure all invoice service tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise

### Phase 8I: Invoice - API Endpoints

- [x] 25. Invoice API Endpoints
  - [x] 25.1 Create FastAPI router for invoices
    - Create api/v1/invoices.py
    - Set up dependency injection for InvoiceService
    - Register router in main app
    - Apply require_manager_or_admin to most endpoints
    - _Requirements: 17.7, 22.5-22.7_

  - [x] 25.2 Implement POST /api/v1/invoices
    - Create invoice
    - Return 201 on success
    - Return InvoiceResponse
    - _Requirements: 7.1-7.10, 22.1_

  - [x] 25.3 Implement GET /api/v1/invoices/{id}
    - Get invoice with job and customer details
    - Return 404 if not found
    - Return InvoiceDetailResponse
    - _Requirements: 13.1, 22.3_

  - [x] 25.4 Implement PUT /api/v1/invoices/{id}
    - Update invoice (draft only)
    - Return 404 if not found
    - Return InvoiceResponse
    - _Requirements: 7.1-7.10, 22.3_

  - [x] 25.5 Implement DELETE /api/v1/invoices/{id}
    - Cancel invoice
    - Return 204 on success
    - Return 404 if not found
    - _Requirements: 8.9, 22.3_

  - [x] 25.6 Implement GET /api/v1/invoices
    - List invoices with pagination and filters
    - Return PaginatedInvoiceResponse
    - _Requirements: 13.1-13.7_

  - [x] 25.7 Implement POST /api/v1/invoices/{id}/send
    - Mark invoice as sent
    - Return InvoiceResponse
    - _Requirements: 8.2_

  - [x] 25.8 Implement POST /api/v1/invoices/{id}/payment
    - Record payment
    - Return InvoiceResponse
    - _Requirements: 9.1-9.7_

  - [x] 25.9 Implement POST /api/v1/invoices/{id}/reminder
    - Send payment reminder
    - Return InvoiceResponse
    - _Requirements: 12.1-12.5_

  - [x] 25.10 Implement POST /api/v1/invoices/{id}/lien-warning
    - Send lien warning (admin only)
    - Return InvoiceResponse
    - _Requirements: 11.6, 17.8_

  - [x] 25.11 Implement POST /api/v1/invoices/{id}/lien-filed
    - Mark lien as filed (admin only)
    - Return InvoiceResponse
    - _Requirements: 11.7, 17.8_

  - [x] 25.12 Implement GET /api/v1/invoices/overdue
    - List overdue invoices
    - Return PaginatedInvoiceResponse
    - _Requirements: 13.5_

  - [x] 25.13 Implement GET /api/v1/invoices/lien-deadlines
    - Get invoices approaching lien deadlines
    - Return LienDeadlineResponse
    - _Requirements: 11.4-11.5, 13.6_

  - [x] 25.14 Implement POST /api/v1/invoices/generate-from-job/{job_id}
    - Generate invoice from completed job
    - Return InvoiceResponse
    - _Requirements: 10.1-10.7_

  - [x] 25.15 Write invoice API tests
    - Test all CRUD endpoints
    - Test status transitions
    - Test payment recording
    - Test lien operations
    - Test generate from job
    - Test authorization
    - Target 85%+ coverage
    - _Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7_

- [x] 26. Checkpoint - Invoice API Complete
  - Ensure all invoice API tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Ask the user if questions arise

### Phase 8J: Invoice - Frontend

- [ ] 27. Invoice Frontend Components
  - [x] 27.1 Create InvoiceStatusBadge component
    - Color-coded badges for all statuses
    - draft: gray, sent: blue, paid: green
    - partial: yellow, overdue: red
    - lien_warning: orange, lien_filed: dark red
    - cancelled: gray
    - Add data-testid attributes
    - _Requirements: 8.1-8.10_

  - [x] 27.2 Create InvoiceList component
    - DataTable with pagination
    - Columns: number, customer, amount, status, due_date, actions
    - Filter controls for status, customer, date range
    - Add data-testid="invoice-list"
    - _Requirements: 13.1-13.7_

  - [x] 27.3 Create InvoiceDetail component
    - Display all invoice fields
    - Show job and customer info
    - Show line items
    - Action buttons based on status
    - Add data-testid="invoice-detail"
    - _Requirements: 7.1-7.10_

  - [x] 27.4 Create InvoiceForm component
    - Form for creating/editing invoices
    - Line items editor
    - Due date picker
    - Notes field
    - Add data-testid="invoice-form"
    - _Requirements: 7.1-7.10_

  - [x] 27.5 Create PaymentDialog component
    - Amount input (default: remaining balance)
    - Payment method select
    - Reference input (optional)
    - Add data-testid="payment-dialog"
    - _Requirements: 9.1-9.7_

  - [x] 27.6 Create GenerateInvoiceButton component
    - Button on JobDetail page
    - Only visible when payment_collected_on_site is false
    - Opens invoice creation flow
    - Add data-testid="generate-invoice-btn"
    - _Requirements: 10.1-10.7_

  - [x] 27.7 Create LienDeadlinesWidget component
    - Dashboard widget
    - Show invoices approaching 45-day warning
    - Show invoices approaching 120-day filing
    - Quick action buttons
    - Add data-testid="lien-deadlines-widget"
    - _Requirements: 11.4-11.5, 11.8_

  - [x] 27.8 Create invoice API client
    - All CRUD operations
    - Status operations
    - Payment recording
    - Lien operations
    - Generate from job
    - _Requirements: All invoice API requirements_

  - [x] 27.9 Add Invoices to navigation
    - Add "Invoices" item to sidebar
    - Route to /invoices
    - _Requirements: UI organization_

  - [x] 27.10 Update JobDetail with invoice features
    - [x] Add GenerateInvoiceButton
    - [x] Show linked invoice if exists
    - [x] Add payment_collected_on_site toggle/checkbox
    - [x] Update job completion workflow to set payment_collected_on_site
    - _Requirements: 10.1-10.7, 10.5.1-10.5.3_

  - [x] 27.11 Update Dashboard with invoice widgets
    - Add "Overdue Invoices" widget
    - Add LienDeadlinesWidget
    - _Requirements: 11.4-11.5_

  - [x] 27.12 Write frontend invoice tests
    - Test InvoiceList rendering
    - Test InvoiceDetail rendering
    - Test InvoiceForm validation
    - Test PaymentDialog
    - Test LienDeadlinesWidget
    - _Requirements: All invoice frontend requirements_

- [x] 28. Checkpoint - Invoice Frontend Complete
  - Ensure all invoice frontend tests pass
  - Ensure invoice list and detail pages work
  - Ensure payment recording works
  - Ask the user if questions arise

### Phase 8K: Integration Testing & Property-Based Tests

- [ ] 29. Integration Testing
  - [x] 29.1 Create test fixtures
    - Database fixtures for invoices
    - Database fixtures for schedule clear audit
    - Database fixtures for authenticated users
    - Test client setup with auth
    - _Requirements: All integration requirements_

  - [x] 29.2 Write authentication integration tests
    - Test login flow end-to-end
    - Test token refresh flow
    - Test protected route access
    - Test role-based access control
    - _Requirements: 14.1-14.8, 17.1-17.12, 20.1-20.6_

  - [x] 29.3 Write schedule clear integration tests
    - Test clear schedule with appointments
    - Test job status reset
    - Test audit log creation
    - Test recent clears retrieval
    - _Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5_

  - [x] 29.4 Write invoice integration tests
    - Test invoice creation from job
    - Test payment recording
    - Test status transitions
    - Test lien tracking workflow
    - _Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8_

  - [x] 29.5 Write cross-component integration tests
    - Test invoice generation requires auth
    - Test schedule clear requires manager role
    - Test lien warning requires admin role
    - _Requirements: 17.5-17.9_

- [ ] 30. Property-Based Tests
  - [x] 30.1 Write password hashing property tests
    - Test hash then verify returns true
    - Test different passwords produce different hashes
    - **Property 1: Password Hashing Round-Trip**
    - _Requirements: 15.8, 16.1-16.4_

  - [x] 30.2 Write role permission property tests
    - Test admin has all permissions
    - Test manager has subset of admin
    - Test tech has subset of manager
    - **Property 2: Role Permission Hierarchy**
    - _Requirements: 17.1-17.12_

  - [x] 30.3 Write schedule clear audit property tests
    - Test audit contains all deleted appointments
    - Test audit contains all reset job IDs
    - **Property 3: Clear Schedule Audit Completeness**
    - _Requirements: 5.1-5.6_

  - [x] 30.4 Write job status reset property tests
    - Test only 'scheduled' jobs are reset
    - Test 'in_progress' and 'completed' jobs unchanged
    - **Property 4: Job Status Reset Correctness**
    - _Requirements: 3.3-3.4_

  - [x] 30.5 Write invoice number property tests
    - Test invoice numbers are unique
    - Test format matches INV-{YEAR}-{SEQUENCE}
    - **Property 5: Invoice Number Uniqueness**
    - _Requirements: 7.1_

  - [x] 30.6 Write payment recording property tests
    - Test paid_amount >= total_amount → status = paid
    - Test paid_amount < total_amount → status = partial
    - **Property 6: Payment Recording Correctness**
    - _Requirements: 9.5-9.6_

  - [x] 30.7 Write lien eligibility property tests
    - Test installation jobs are lien-eligible
    - Test major_repair jobs are lien-eligible
    - Test seasonal services are not lien-eligible
    - **Property 7: Lien Eligibility Determination**
    - _Requirements: 11.1_

### Phase 8L: Comprehensive Unit Testing (90%+ Coverage)

- [x] 31. Backend Unit Tests - Authentication
  - [x] 31.1 AuthService unit tests (target: 95% coverage)
    - Test authenticate with valid credentials
    - Test authenticate with invalid username
    - Test authenticate with invalid password
    - Test authenticate with locked account
    - Test account lockout after 5 failed attempts
    - Test lockout duration (15 minutes)
    - Test lockout reset on successful login
    - Test _hash_password produces valid bcrypt hash
    - Test _verify_password with correct password
    - Test _verify_password with incorrect password
    - Test _create_access_token generates valid JWT
    - Test _create_access_token with custom expiration
    - Test _create_refresh_token generates valid JWT
    - Test verify_access_token with valid token
    - Test verify_access_token with expired token
    - Test verify_access_token with invalid token
    - Test verify_refresh_token with valid token
    - Test verify_refresh_token with expired token
    - Test refresh_access_token generates new token
    - Test change_password with correct current password
    - Test change_password with incorrect current password
    - Test change_password validates new password strength
    - Test get_current_user returns user info
    - _Requirements: 14.1-14.8, 16.1-16.8_

  - [x] 31.2 RBAC unit tests (target: 95% coverage)
    - Test require_roles decorator with allowed role
    - Test require_roles decorator with disallowed role
    - Test require_roles decorator with multiple allowed roles
    - Test get_current_user dependency with valid token
    - Test get_current_user dependency with invalid token
    - Test get_current_user dependency with expired token
    - Test get_current_active_user with active user
    - Test get_current_active_user with inactive user
    - Test require_admin with admin user
    - Test require_admin with non-admin user
    - Test require_manager_or_admin with manager
    - Test require_manager_or_admin with admin
    - Test require_manager_or_admin with tech (denied)
    - _Requirements: 17.1-17.12_

- [ ] 32. Backend Unit Tests - Schedule Clear
  - [x] 32.1 ScheduleClearService unit tests (target: 95% coverage)
    - Test clear_schedule with appointments present
    - Test clear_schedule with no appointments
    - Test clear_schedule creates audit log
    - Test clear_schedule serializes appointment data correctly
    - Test clear_schedule identifies scheduled jobs
    - Test clear_schedule resets job status to approved
    - Test clear_schedule does not reset in_progress jobs
    - Test clear_schedule does not reset completed jobs
    - Test clear_schedule returns correct counts
    - Test get_recent_clears with default 24 hours
    - Test get_recent_clears with custom hours
    - Test get_recent_clears returns empty list when none
    - Test get_clear_details with valid ID
    - Test get_clear_details with invalid ID raises error
    - Test get_clear_details includes appointments_data
    - Test get_clear_details includes jobs_reset
    - _Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5_

  - [x] 32.2 ScheduleClearAuditRepository unit tests (target: 90% coverage)
    - Test create audit record
    - Test get_by_id with valid ID
    - Test get_by_id with invalid ID returns None
    - Test find_since with matching records
    - Test find_since with no matching records
    - Test find_since respects time boundary
    - _Requirements: 5.1-5.6, 6.1-6.5_

- [ ] 33. Backend Unit Tests - Invoice
  - [x] 33.1 InvoiceService unit tests (target: 95% coverage)
    - Test create_invoice with valid data
    - Test create_invoice generates unique invoice number
    - Test create_invoice calculates total_amount correctly
    - Test create_invoice sets lien_eligible based on job type
    - Test _generate_invoice_number format (INV-YEAR-SEQ)
    - Test _generate_invoice_number increments sequence
    - Test get_invoice with valid ID
    - Test get_invoice with invalid ID raises error
    - Test update_invoice with draft status
    - Test update_invoice with non-draft status raises error
    - Test cancel_invoice sets status to cancelled
    - Test list_invoices with no filters
    - Test list_invoices with status filter
    - Test list_invoices with customer_id filter
    - Test list_invoices with date range filter
    - Test list_invoices with lien_eligible filter
    - Test list_invoices pagination
    - Test list_invoices sorting
    - Test send_invoice transitions draft to sent
    - Test send_invoice with non-draft raises error
    - Test mark_viewed transitions sent to viewed
    - Test mark_overdue transitions to overdue
    - Test record_payment with full amount (status = paid)
    - Test record_payment with partial amount (status = partial)
    - Test record_payment stores payment_method
    - Test record_payment stores payment_reference
    - Test record_payment sets paid_at timestamp
    - Test send_reminder increments reminder_count
    - Test send_reminder updates last_reminder_sent
    - Test send_lien_warning sets lien_warning_sent
    - Test mark_lien_filed sets lien_filed_date
    - Test get_lien_deadlines returns approaching 45-day
    - Test get_lien_deadlines returns approaching 120-day
    - Test generate_from_job with valid job
    - Test generate_from_job with deleted job raises error
    - Test generate_from_job with payment_collected_on_site raises error
    - Test generate_from_job uses final_amount when present
    - Test generate_from_job uses quoted_amount as fallback
    - Test generate_from_job creates line items from job
    - _Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.7, 10.1-10.7, 11.1-11.8, 12.1-12.5, 13.1-13.7_

  - [x] 33.2 InvoiceRepository unit tests (target: 90% coverage)
    - Test create invoice record
    - Test get_by_id with valid ID
    - Test get_by_id with invalid ID returns None
    - Test update invoice record
    - Test list_with_filters with various filter combinations
    - Test get_next_sequence returns incrementing values
    - Test find_overdue returns overdue invoices
    - Test find_lien_warning_due returns eligible invoices
    - Test find_lien_filing_due returns eligible invoices
    - _Requirements: 7.1-7.10, 11.2-11.4, 13.1-13.7_

- [ ] 34. Frontend Unit Tests - Authentication
  - [x] 34.1 AuthProvider tests (target: 90% coverage)
    - Test initial state (not authenticated)
    - Test login success updates user state
    - Test login failure does not update state
    - Test logout clears user state
    - Test token refresh updates access token
    - Test auto-refresh triggers before expiration
    - Test CSRF token read from cookie
    - Test CSRF token sent in headers
    - _Requirements: 16.8, 19.1-19.8, 20.5-20.6_

  - [x] 34.2 LoginPage tests (target: 90% coverage)
    - Test renders username input
    - Test renders password input
    - Test renders remember me checkbox
    - Test renders sign in button
    - Test password visibility toggle works
    - Test form validation for empty username
    - Test form validation for empty password
    - Test loading state during login
    - Test error alert on invalid credentials
    - Test redirect to dashboard on success
    - _Requirements: 19.1-19.7_

  - [x] 34.3 ProtectedRoute tests (target: 90% coverage)
    - Test redirects to login when not authenticated
    - Test renders children when authenticated
    - Test checks role permissions
    - Test displays AccessDenied for unauthorized roles
    - _Requirements: 20.1-20.4_

  - [x] 34.4 UserMenu tests (target: 90% coverage)
    - Test displays user name
    - Test dropdown opens on click
    - Test settings option present
    - Test logout option present
    - Test logout calls logout function
    - _Requirements: 19.8_

- [x] 35. Frontend Unit Tests - Schedule Clear
  - [x] 35.1 ClearResultsButton tests (target: 90% coverage)
    - Test renders when schedule results present
    - Test hidden when no schedule results
    - Test click triggers clear action
    - Test has correct data-testid
    - _Requirements: 1.1-1.6_

  - [x] 35.2 JobSelectionControls tests (target: 90% coverage)
    - Test renders Select All link
    - Test renders Deselect All link
    - Test Select All selects all jobs
    - Test Deselect All deselects all jobs
    - Test has correct data-testid attributes
    - _Requirements: 2.1-2.5_

  - [x] 35.3 ClearDayButton tests (target: 90% coverage)
    - Test renders with Trash2 icon
    - Test click opens dialog
    - Test has correct data-testid
    - _Requirements: 3.1_

  - [x] 35.4 ClearDayDialog tests (target: 90% coverage)
    - Test renders warning icon
    - Test displays date in title
    - Test displays appointment count
    - Test displays affected jobs preview
    - Test shows "and X more" for many jobs
    - Test displays status reset notice
    - Test displays audit notice
    - Test Cancel button closes dialog
    - Test Clear Schedule button triggers action
    - Test has correct data-testid
    - _Requirements: 4.1-4.8_

  - [x] 35.5 RecentlyClearedSection tests (target: 90% coverage)
    - Test renders clears from last 24 hours
    - Test displays date, count, timestamp
    - Test View Details action present
    - Test empty state when no recent clears
    - Test has correct data-testid attributes
    - _Requirements: 6.1-6.5_

- [x] 36. Frontend Unit Tests - Invoice
  - [x] 36.1 InvoiceStatusBadge tests (target: 90% coverage)
    - Test draft status renders gray badge
    - Test sent status renders blue badge
    - Test paid status renders green badge
    - Test partial status renders yellow badge
    - Test overdue status renders red badge
    - Test lien_warning status renders orange badge
    - Test lien_filed status renders dark red badge
    - Test cancelled status renders gray badge
    - Test has correct data-testid
    - _Requirements: 8.1-8.10_

  - [x] 36.2 InvoiceList tests (target: 90% coverage)
    - Test renders DataTable
    - Test displays invoice number column
    - Test displays customer column
    - Test displays amount column
    - Test displays status column
    - Test displays due_date column
    - Test displays actions column
    - Test filter controls render
    - Test status filter works
    - Test customer filter works
    - Test date range filter works
    - Test pagination works
    - Test has correct data-testid
    - _Requirements: 13.1-13.7_

  - [x] 36.3 InvoiceDetail tests (target: 90% coverage)
    - Test displays all invoice fields
    - Test displays job info
    - Test displays customer info
    - Test displays line items
    - Test action buttons based on status
    - Test has correct data-testid
    - _Requirements: 7.1-7.10_

  - [x] 36.4 InvoiceForm tests (target: 90% coverage)
    - Test renders amount input
    - Test renders due date picker
    - Test renders line items editor
    - Test renders notes field
    - Test add line item works
    - Test remove line item works
    - Test form validation
    - Test submit creates invoice
    - Test has correct data-testid
    - _Requirements: 7.1-7.10_

  - [x] 36.5 PaymentDialog tests (target: 90% coverage)
    - Test renders amount input with default
    - Test renders payment method select
    - Test renders reference input
    - Test amount validation
    - Test submit records payment
    - Test has correct data-testid
    - _Requirements: 9.1-9.7_

  - [x] 36.6 LienDeadlinesWidget tests (target: 90% coverage)
    - Test displays 45-day warning invoices
    - Test displays 120-day filing invoices
    - Test quick action buttons present
    - Test empty state when no deadlines
    - Test has correct data-testid
    - _Requirements: 11.4-11.5, 11.8_

- [x] 37. Checkpoint - Unit Test Coverage
  - Run `uv run pytest --cov=src/grins_platform --cov-report=term-missing`
  - Run `cd frontend && npm run test:coverage`
  - **REQUIRED: Backend coverage must be 90%+ overall**
  - **REQUIRED: Frontend coverage must be 90%+ overall**
  - **REQUIRED: All tests must pass (100% pass rate)**
  - Fix any failing tests before proceeding
  - Ask the user if questions arise

### Phase 8M: End-to-End UI Validation (agent-browser)

- [x] 38. Authentication E2E Validation
  - [x] 38.1 Validate login page renders correctly
    - `agent-browser open http://localhost:5173/login`
    - `agent-browser snapshot -i`
    - `agent-browser is visible "[data-testid='login-page']"`
    - `agent-browser is visible "[data-testid='username-input']"`
    - `agent-browser is visible "[data-testid='password-input']"`
    - `agent-browser is visible "[data-testid='remember-me-checkbox']"`
    - `agent-browser is visible "[data-testid='login-btn']"`
    - If any fail: fix component, re-run quality checks, retry validation
    - _Requirements: 19.1-19.7_

  - [x] 38.2 Validate login flow with valid credentials
    - `agent-browser open http://localhost:5173/login`
    - `agent-browser fill "[data-testid='username-input']" "admin"`
    - `agent-browser fill "[data-testid='password-input']" "password123"`
    - `agent-browser click "[data-testid='login-btn']"`
    - `agent-browser wait --url "**/dashboard"`
    - `agent-browser is visible "[data-testid='dashboard-page']"`
    - If any fail: fix auth flow, re-run quality checks, retry validation
    - _Requirements: 14.1-14.2, 19.1-19.7_

  - [x] 38.3 Validate login error handling
    - `agent-browser open http://localhost:5173/login`
    - `agent-browser fill "[data-testid='username-input']" "invalid"`
    - `agent-browser fill "[data-testid='password-input']" "wrong"`
    - `agent-browser click "[data-testid='login-btn']"`
    - `agent-browser wait "[data-testid='login-error']"`
    - `agent-browser is visible "[data-testid='login-error']"`
    - If any fail: fix error handling, re-run quality checks, retry validation
    - _Requirements: 14.2, 19.6_

  - [x] 38.4 Validate password visibility toggle
    - `agent-browser open http://localhost:5173/login`
    - `agent-browser fill "[data-testid='password-input']" "testpass"`
    - `agent-browser click "[data-testid='password-toggle']"`
    - Verify password is visible (type="text")
    - `agent-browser click "[data-testid='password-toggle']"`
    - Verify password is hidden (type="password")
    - If any fail: fix toggle, re-run quality checks, retry validation
    - _Requirements: 19.3_

  - [x] 38.5 Validate protected route redirect
    - `agent-browser open http://localhost:5173/customers`
    - `agent-browser wait --url "**/login"`
    - Verify redirected to login page
    - If any fail: fix ProtectedRoute, re-run quality checks, retry validation
    - _Requirements: 20.1-20.2_

  - [x] 38.6 Validate user menu
    - Login as admin user first
    - `agent-browser is visible "[data-testid='user-menu']"`
    - `agent-browser click "[data-testid='user-menu']"`
    - `agent-browser is visible "[data-testid='user-menu-dropdown']"`
    - `agent-browser is visible "[data-testid='logout-btn']"`
    - If any fail: fix UserMenu, re-run quality checks, retry validation
    - _Requirements: 19.8_

  - [x] 38.7 Validate logout flow
    - Login as admin user first
    - `agent-browser click "[data-testid='user-menu']"`
    - `agent-browser click "[data-testid='logout-btn']"`
    - `agent-browser wait --url "**/login"`
    - Verify redirected to login page
    - If any fail: fix logout flow, re-run quality checks, retry validation
    - _Requirements: 14.8_

- [ ] 39. Schedule Clear E2E Validation
  - [x] 39.1 Validate Generate Routes tab clear results button
    - Login as manager/admin
    - Navigate to schedule generation page
    - Generate a schedule with results
    - `agent-browser is visible "[data-testid='clear-results-btn']"`
    - `agent-browser click "[data-testid='clear-results-btn']"`
    - Verify results are cleared
    - If any fail: fix ClearResultsButton, re-run quality checks, retry validation
    - _Requirements: 1.1-1.6_

  - [x] 39.2 Validate job selection controls
    - Login as manager/admin
    - Navigate to schedule generation page
    - Generate a schedule with multiple jobs
    - `agent-browser is visible "[data-testid='select-all-btn']"`
    - `agent-browser is visible "[data-testid='deselect-all-btn']"`
    - `agent-browser click "[data-testid='select-all-btn']"`
    - Verify all jobs selected
    - `agent-browser click "[data-testid='deselect-all-btn']"`
    - Verify all jobs deselected
    - If any fail: fix JobSelectionControls, re-run quality checks, retry validation
    - _Requirements: 2.1-2.5_

  - [x] 39.3 Validate clear day button and dialog
    - Login as manager/admin
    - Navigate to schedule tab with appointments
    - `agent-browser is visible "[data-testid='clear-day-btn']"`
    - `agent-browser click "[data-testid='clear-day-btn']"`
    - `agent-browser wait "[data-testid='clear-day-dialog']"`
    - `agent-browser is visible "[data-testid='clear-day-dialog']"`
    - `agent-browser is visible "[data-testid='clear-day-warning']"`
    - `agent-browser is visible "[data-testid='clear-day-cancel']"`
    - `agent-browser is visible "[data-testid='clear-day-confirm']"`
    - If any fail: fix ClearDayDialog, re-run quality checks, retry validation
    - _Requirements: 3.1, 4.1-4.8_

  - [x] 39.4 Validate clear day confirmation flow
    - Login as manager/admin
    - Navigate to schedule tab with appointments
    - `agent-browser click "[data-testid='clear-day-btn']"`
    - `agent-browser wait "[data-testid='clear-day-dialog']"`
    - `agent-browser click "[data-testid='clear-day-confirm']"`
    - Verify appointments are cleared
    - Verify success notification shown
    - If any fail: fix clear flow, re-run quality checks, retry validation
    - _Requirements: 3.1-3.7_

  - [ ] 39.5 Validate recently cleared section
    - Login as manager/admin
    - Clear a schedule first
    - Navigate to schedule tab
    - `agent-browser is visible "[data-testid='recently-cleared-section']"`
    - Verify cleared schedule appears in list
    - `agent-browser is visible "[data-testid='view-clear-details-btn']"`
    - If any fail: fix RecentlyClearedSection, re-run quality checks, retry validation
    - _Requirements: 6.1-6.5_

- [ ] 40. Invoice E2E Validation
  - [ ] 40.1 Validate invoice list page
    - Login as manager/admin
    - `agent-browser open http://localhost:5173/invoices`
    - `agent-browser is visible "[data-testid='invoice-list']"`
    - `agent-browser is visible "[data-testid='invoice-table']"`
    - `agent-browser is visible "[data-testid='invoice-filter-status']"`
    - `agent-browser is visible "[data-testid='invoice-filter-customer']"`
    - `agent-browser is visible "[data-testid='invoice-filter-date']"`
    - If any fail: fix InvoiceList, re-run quality checks, retry validation
    - _Requirements: 13.1-13.7_

  - [ ] 40.2 Validate invoice detail page
    - Login as manager/admin
    - Navigate to an existing invoice
    - `agent-browser is visible "[data-testid='invoice-detail']"`
    - `agent-browser is visible "[data-testid='invoice-number']"`
    - `agent-browser is visible "[data-testid='invoice-amount']"`
    - `agent-browser is visible "[data-testid='invoice-status']"`
    - `agent-browser is visible "[data-testid='invoice-line-items']"`
    - If any fail: fix InvoiceDetail, re-run quality checks, retry validation
    - _Requirements: 7.1-7.10_

  - [ ] 40.3 Validate invoice creation form
    - Login as manager/admin
    - Navigate to create invoice page
    - `agent-browser is visible "[data-testid='invoice-form']"`
    - `agent-browser fill "[data-testid='invoice-amount']" "150.00"`
    - `agent-browser click "[data-testid='add-line-item-btn']"`
    - `agent-browser fill "[data-testid='line-item-description']" "Spring Startup"`
    - `agent-browser fill "[data-testid='line-item-amount']" "150.00"`
    - `agent-browser click "[data-testid='submit-invoice-btn']"`
    - Verify invoice created successfully
    - If any fail: fix InvoiceForm, re-run quality checks, retry validation
    - _Requirements: 7.1-7.10_

  - [ ] 40.4 Validate payment dialog
    - Login as manager/admin
    - Navigate to a sent invoice
    - `agent-browser click "[data-testid='record-payment-btn']"`
    - `agent-browser wait "[data-testid='payment-dialog']"`
    - `agent-browser is visible "[data-testid='payment-amount']"`
    - `agent-browser is visible "[data-testid='payment-method']"`
    - `agent-browser is visible "[data-testid='payment-reference']"`
    - `agent-browser fill "[data-testid='payment-amount']" "150.00"`
    - `agent-browser select "[data-testid='payment-method']" "venmo"`
    - `agent-browser click "[data-testid='submit-payment-btn']"`
    - Verify payment recorded
    - If any fail: fix PaymentDialog, re-run quality checks, retry validation
    - _Requirements: 9.1-9.7_

  - [ ] 40.5 Validate invoice status transitions
    - Login as manager/admin
    - Create a draft invoice
    - `agent-browser click "[data-testid='send-invoice-btn']"`
    - Verify status changes to "sent"
    - Record full payment
    - Verify status changes to "paid"
    - If any fail: fix status transitions, re-run quality checks, retry validation
    - _Requirements: 8.1-8.6_

  - [ ] 40.6 Validate generate invoice from job
    - Login as manager/admin
    - Navigate to a completed job
    - `agent-browser is visible "[data-testid='generate-invoice-btn']"`
    - `agent-browser click "[data-testid='generate-invoice-btn']"`
    - Verify invoice form pre-populated with job data
    - If any fail: fix GenerateInvoiceButton, re-run quality checks, retry validation
    - _Requirements: 10.1-10.7_

  - [ ] 40.7 Validate lien deadlines widget
    - Login as admin
    - Navigate to dashboard
    - `agent-browser is visible "[data-testid='lien-deadlines-widget']"`
    - Verify widget displays approaching deadlines
    - If any fail: fix LienDeadlinesWidget, re-run quality checks, retry validation
    - _Requirements: 11.4-11.5, 11.8_

  - [ ] 40.8 Validate invoice filters and pagination
    - Login as manager/admin
    - Navigate to invoice list
    - `agent-browser select "[data-testid='invoice-filter-status']" "overdue"`
    - Verify only overdue invoices shown
    - `agent-browser click "[data-testid='pagination-next']"`
    - Verify pagination works
    - If any fail: fix filters/pagination, re-run quality checks, retry validation
    - _Requirements: 13.1-13.7_

- [ ] 41. Cross-Feature E2E Validation
  - [ ] 41.1 Validate role-based access control
    - Login as tech user
    - Navigate to invoice list
    - Verify limited actions available
    - Try to access admin-only features
    - Verify access denied
    - Login as admin user
    - Verify full access to all features
    - If any fail: fix RBAC, re-run quality checks, retry validation
    - _Requirements: 17.1-17.12_

  - [ ] 41.2 Validate complete workflow: Job → Invoice → Payment
    - Login as manager
    - Create a new job
    - Complete the job
    - Generate invoice from job
    - Send invoice
    - Record payment
    - Verify job and invoice statuses updated
    - If any fail: fix workflow, re-run quality checks, retry validation
    - _Requirements: 10.1-10.7, 8.1-8.6, 9.1-9.7_

  - [ ] 41.3 Validate complete workflow: Schedule → Clear → Audit
    - Login as manager
    - Generate a schedule
    - Apply schedule to calendar
    - Clear the day's schedule
    - Verify audit log created
    - View audit details
    - Verify all data captured
    - If any fail: fix workflow, re-run quality checks, retry validation
    - _Requirements: 3.1-3.7, 5.1-5.6, 6.1-6.5_

- [ ] 42. Checkpoint - E2E Validation Complete
  - **REQUIRED: All E2E validations must pass**
  - **REQUIRED: Any failures must be fixed and re-validated**
  - **REQUIRED: Maximum 3 retry attempts per validation**
  - Document any issues encountered
  - Ask the user if questions arise

### Phase 8N: Documentation & Quality

- [ ] 43. Documentation and Quality
  - [ ] 43.1 Run quality checks
    - Run ruff check and fix all issues
    - Run mypy and fix all type errors
    - Run pyright and fix all errors
    - **REQUIRED: Zero violations/errors**
    - _Requirements: Code Standards_

  - [ ] 43.2 Verify test coverage
    - Run pytest with coverage
    - **REQUIRED: 90%+ coverage on services**
    - **REQUIRED: 90%+ coverage on API**
    - **REQUIRED: 90%+ coverage on repositories**
    - **REQUIRED: 90%+ coverage on frontend components**
    - _Requirements: Code Standards_

  - [ ] 43.3 Update API documentation
    - Verify OpenAPI spec is complete for all new endpoints
    - Add example requests/responses
    - Document error codes
    - _Requirements: 22.5_

  - [ ] 43.4 Update DEVLOG
    - Document implementation progress
    - Document decisions made
    - Document any deviations from design

- [ ] 44. Final Checkpoint
  - **REQUIRED: All unit tests pass (100% pass rate)**
  - **REQUIRED: All integration tests pass (100% pass rate)**
  - **REQUIRED: All property-based tests pass (100% pass rate)**
  - **REQUIRED: All E2E validations pass (100% pass rate)**
  - **REQUIRED: Backend coverage 90%+**
  - **REQUIRED: Frontend coverage 90%+**
  - **REQUIRED: All quality checks pass (zero violations)**
  - Verify authentication flow works end-to-end
  - Verify schedule clear features work
  - Verify invoice management works
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Authentication is implemented first as it's the security foundation
- **CRITICAL: 90%+ test coverage is REQUIRED before marking tasks complete**
- **CRITICAL: All E2E validations must pass with retry/fix cycles**
- **CRITICAL: Any failing validation must be fixed and re-validated (max 3 retries)**

## Testing Requirements Summary

### Coverage Targets (MANDATORY)

| Component | Target Coverage | Minimum Acceptable |
|-----------|-----------------|-------------------|
| Backend Services | 95%+ | 90% |
| Backend API | 90%+ | 85% |
| Backend Repositories | 90%+ | 85% |
| Frontend Components | 90%+ | 85% |
| Frontend Hooks | 90%+ | 85% |
| **Overall Backend** | **90%+** | **90%** |
| **Overall Frontend** | **90%+** | **90%** |

### Test Pass Rate (MANDATORY)

| Test Type | Required Pass Rate |
|-----------|-------------------|
| Unit Tests | 100% |
| Functional Tests | 100% |
| Integration Tests | 100% |
| Property-Based Tests | 100% |
| E2E Validations | 100% |

### E2E Validation Retry Policy

When an E2E validation fails:
1. **Identify the issue** - Check console errors, missing elements, incorrect behavior
2. **Fix the component** - Update the relevant code
3. **Run quality checks** - `ruff`, `mypy`, `pyright`, `npm run lint`, `npm run typecheck`
4. **Re-run the validation** - Execute the same agent-browser commands
5. **Maximum 3 retries** - If still failing after 3 attempts, escalate to user

## Dependencies

- Previous phases (Customer Management, Field Operations, Scheduling) must be complete
- Database must be running with all previous migrations applied
- All previous phase tests should be passing

## Test Count Summary

| Category | Test Count |
|----------|------------|
| **Backend Unit Tests** | |
| - Authentication Service | 24 tests |
| - RBAC | 13 tests |
| - Schedule Clear Service | 16 tests |
| - Schedule Clear Repository | 6 tests |
| - Invoice Service | 38 tests |
| - Invoice Repository | 9 tests |
| **Frontend Unit Tests** | |
| - Auth Provider | 8 tests |
| - Login Page | 10 tests |
| - Protected Route | 4 tests |
| - User Menu | 5 tests |
| - Clear Results Button | 4 tests |
| - Job Selection Controls | 5 tests |
| - Clear Day Button | 3 tests |
| - Clear Day Dialog | 10 tests |
| - Recently Cleared Section | 5 tests |
| - Invoice Status Badge | 9 tests |
| - Invoice List | 13 tests |
| - Invoice Detail | 5 tests |
| - Invoice Form | 9 tests |
| - Payment Dialog | 6 tests |
| - Lien Deadlines Widget | 5 tests |
| **E2E Validations** | |
| - Authentication | 7 validations |
| - Schedule Clear | 5 validations |
| - Invoice | 8 validations |
| - Cross-Feature | 3 validations |
| **Integration Tests** | 5 test suites |
| **Property-Based Tests** | 7 properties |
| **Total Unit Tests** | **~200+ tests** |
| **Total E2E Validations** | **23 validations** |
| **Grand Total** | **~230+ tests/validations** |

## Effort Estimate

| Phase | Estimated Hours |
|-------|-----------------|
| 8A-8C: Authentication | 10-14 hours |
| 8D-8F: Schedule Clear | 9-13 hours |
| 8G-8J: Invoice Management | 16-21 hours |
| 8K: Integration & PBT | 4-6 hours |
| 8L: Comprehensive Unit Tests | 8-12 hours |
| 8M: E2E UI Validation | 6-10 hours |
| 8N: Documentation & Quality | 2-4 hours |
| **Total** | **55-80 hours** |
