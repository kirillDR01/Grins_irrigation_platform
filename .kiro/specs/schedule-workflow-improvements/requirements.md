# Requirements Document: Schedule Workflow Improvements (Phase 8)

## Introduction

The Schedule Workflow Improvements feature is Phase 8 of Grin's Irrigation Platform, building on the scheduling and field operations foundation established in previous phases. This phase implements three major priorities: Schedule Clear & Reset Features, Invoice Management System, and Authentication & Login System. Together, these components address critical operational gaps: the inability to clear and regenerate schedules, manual invoice tracking via spreadsheets, and the lack of user authentication for production deployment.

## Glossary

- **System**: The Grin's Irrigation Platform backend API and frontend application
- **Schedule_Results**: In-memory generated schedule data before being applied to the database
- **Applied_Schedule**: Appointments that have been created in the database from schedule generation
- **Audit_Log**: Record of destructive operations for recovery and compliance purposes
- **Invoice**: A billing document generated for completed work requiring payment
- **Invoice_Status**: Current state in the invoice lifecycle (draft, sent, paid, overdue, etc.)
- **Lien**: Legal claim against property for unpaid work (mechanic's lien)
- **Lien_Eligible**: Services that qualify for mechanic's lien filing (installations, major repairs)
- **Payment_Method**: How payment was received (cash, check, venmo, zelle, stripe)
- **User**: An authenticated person with system access
- **Role**: Permission level assigned to a user (admin, manager, tech)
- **JWT**: JSON Web Token used for API authentication
- **Access_Token**: Short-lived token for API requests (15 minutes)
- **Refresh_Token**: Long-lived token for obtaining new access tokens (7 days)

## Requirements

### Requirement 1: Clear Generated Schedule Results

**User Story:** As a business owner, I want to clear generated schedule results without affecting the database, so that I can adjust job selections and constraints and regenerate a better schedule.

#### Acceptance Criteria

1. WHEN a user clicks the "Clear Results" button, THE System SHALL clear the in-memory schedule results
2. WHEN schedule results are cleared, THE System SHALL return the view to the job selection state
3. WHEN schedule results are cleared, THE System SHALL preserve the current job checkbox selections
4. WHEN schedule results are cleared, THE System SHALL NOT modify any database records
5. THE System SHALL only display the "Clear Results" button when schedule results are present
6. THE System SHALL NOT require confirmation for clearing results (only in-memory data)

### Requirement 2: Job Selection Controls

**User Story:** As a business owner, I want to quickly select or deselect all jobs in the schedule generation view, so that I can efficiently manage which jobs to include in schedule generation.

#### Acceptance Criteria

1. WHEN a user clicks "Select All", THE System SHALL check all job checkboxes in the current filtered view
2. WHEN a user clicks "Deselect All", THE System SHALL uncheck all job checkboxes
3. THE System SHALL display "Select All" and "Deselect All" as text links above the job list
4. THE System SHALL NOT require confirmation for select/deselect operations
5. THE System SHALL apply selection changes only to jobs visible in the current filter

### Requirement 3: Clear Applied Schedule (Clear Day)

**User Story:** As a business owner, I want to clear an already-applied schedule for a specific date, so that I can regenerate the schedule with different parameters or handle scheduling conflicts.

#### Acceptance Criteria

1. WHEN a user initiates "Clear Day", THE System SHALL display a date picker to select which day to clear
2. WHEN a user confirms clearing a day, THE System SHALL delete all appointments for that date
3. WHEN appointments are deleted, THE System SHALL reset associated job statuses from "scheduled" to "approved"
4. WHEN appointments are deleted, THE System SHALL only reset jobs that currently have status "scheduled"
5. WHEN a clear operation is performed, THE System SHALL create an audit log entry before deletion
6. THE System SHALL store complete appointment data in the audit log for potential recovery
7. THE System SHALL return the count of deleted appointments and reset jobs in the response

### Requirement 4: Clear Day Confirmation Dialog

**User Story:** As a business owner, I want to see a confirmation dialog before clearing a schedule, so that I can verify the impact of the destructive action before proceeding.

#### Acceptance Criteria

1. WHEN a user requests to clear a day, THE System SHALL display a confirmation dialog
2. THE System SHALL show the selected date in the dialog title
3. THE System SHALL display the count of appointments to be deleted
4. THE System SHALL display a preview of affected jobs (first few with "and X more" for large lists)
5. THE System SHALL display a notice that jobs will be reset to "approved" status
6. THE System SHALL display a notice that the action is logged for recovery
7. THE System SHALL provide Cancel and "Clear Schedule" buttons
8. IF the user cancels, THEN THE System SHALL close the dialog without making changes

### Requirement 5: Schedule Clear Audit Log

**User Story:** As a business owner, I want all schedule clear operations logged with full data, so that I can recover from accidental deletions and maintain an audit trail.

#### Acceptance Criteria

1. WHEN a schedule is cleared, THE System SHALL create an audit log record with the schedule date
2. THE System SHALL store complete appointment data as JSON in the audit log
3. THE System SHALL store the list of job IDs that were reset
4. THE System SHALL record who performed the clear operation (when authentication is implemented)
5. THE System SHALL record the timestamp of the clear operation
6. THE System SHALL allow optional notes to be stored with the audit record

### Requirement 6: Recently Cleared Schedules View

**User Story:** As a business owner, I want to view recently cleared schedules, so that I can review past clear operations and potentially restore data if needed.

#### Acceptance Criteria

1. THE System SHALL display recently cleared schedules from the last 24 hours
2. THE System SHALL show the date, appointment count, and timestamp for each clear operation
3. THE System SHALL provide a "View Details" action to see full audit log data
4. THE System SHALL provide a "Restore" action placeholder for future implementation
5. THE System SHALL display the recently cleared section below the calendar in the Schedule tab

### Requirement 7: Invoice Model and Creation

**User Story:** As a business owner, I want to create invoices for completed jobs, so that I can track billing and payment status in the system instead of spreadsheets.

#### Acceptance Criteria

1. WHEN a user creates an invoice, THE System SHALL generate a unique invoice number (INV-{YEAR}-{SEQUENCE})
2. WHEN a user creates an invoice, THE System SHALL link it to a specific job
3. WHEN a user creates an invoice, THE System SHALL link it to the job's customer
4. THE System SHALL store invoice amount, late fee amount, and total amount as decimal values
5. THE System SHALL default invoice date to the current date
6. THE System SHALL default due date to 14 days from invoice date
7. THE System SHALL allow custom due dates (e.g., 30 days for corporations)
8. THE System SHALL store line items as JSON with description, quantity, unit price, and total
9. THE System SHALL default invoice status to "draft"
10. THE System SHALL track creation and modification timestamps

### Requirement 8: Invoice Status Workflow

**User Story:** As a business owner, I want invoices to follow a defined status workflow, so that I can track the billing lifecycle from creation to payment.

#### Acceptance Criteria

1. WHEN an invoice is created, THE System SHALL set initial status to "draft"
2. WHEN a user sends an invoice, THE System SHALL transition status to "sent"
3. WHEN a customer views an invoice, THE System SHALL transition status to "viewed"
4. WHEN full payment is recorded, THE System SHALL transition status to "paid"
5. WHEN partial payment is recorded, THE System SHALL transition status to "partial"
6. WHEN an invoice passes its due date without payment, THE System SHALL allow transition to "overdue"
7. WHEN a lien warning is sent, THE System SHALL transition status to "lien_warning"
8. WHEN a lien is filed, THE System SHALL transition status to "lien_filed"
9. WHEN an invoice is cancelled, THE System SHALL transition status to "cancelled"
10. THE System SHALL prevent status changes on cancelled invoices

### Requirement 9: Payment Recording

**User Story:** As a business owner, I want to record payments against invoices, so that I can track which invoices are paid and which are outstanding.

#### Acceptance Criteria

1. WHEN a user records a payment, THE System SHALL store the payment amount
2. WHEN a user records a payment, THE System SHALL store the payment method (cash, check, venmo, zelle, stripe)
3. WHEN a user records a payment, THE System SHALL store an optional payment reference (check number, transaction ID)
4. WHEN a user records a payment, THE System SHALL store the payment timestamp
5. WHEN payment equals or exceeds total amount, THE System SHALL transition status to "paid"
6. WHEN payment is less than total amount, THE System SHALL transition status to "partial"
7. THE System SHALL track reminder count and last reminder sent timestamp

### Requirement 10: Invoice Generation from Job

**User Story:** As a business owner, I want to generate invoices directly from completed jobs, so that I can quickly create invoices with pre-populated job data.

#### Acceptance Criteria

1. WHEN a job is completed without on-site payment, THE System SHALL display a "Generate Invoice" button
2. WHEN generating an invoice from a job, THE System SHALL pre-populate customer information
3. WHEN generating an invoice from a job, THE System SHALL pre-populate job details as line items
4. WHEN generating an invoice from a job, THE System SHALL use the job's final_amount or quoted_amount
5. THE System SHALL allow the user to review and adjust line items before creating
6. THE System SHALL track payment_collected_on_site flag on jobs
7. IF payment_collected_on_site is true, THEN THE System SHALL NOT show the "Generate Invoice" button

### Requirement 10.5: Job Payment Tracking Field

**User Story:** As a business owner, I want to track whether payment was collected on-site during job completion, so that I know which jobs need invoices generated.

#### Acceptance Criteria

1. THE System SHALL add a `payment_collected_on_site` boolean field to the Job model
2. THE System SHALL default `payment_collected_on_site` to false
3. WHEN a technician completes a job, THE System SHALL allow setting this field via the job completion workflow

### Requirement 11: Lien Tracking and Deadlines

**User Story:** As a business owner, I want to track lien-eligible invoices and their deadlines, so that I can protect my business by filing liens before the legal deadline expires.

#### Acceptance Criteria

1. THE System SHALL determine lien eligibility based on job type:
   - Lien-eligible: `installation`, `major_repair`
   - Not lien-eligible: `startup`, `winterization`, `tune_up`, `repair`, `diagnostic`
2. THE System SHALL track the 45-day warning deadline for lien notification
3. THE System SHALL track the 120-day filing deadline for lien filing
4. THE System SHALL provide a dashboard widget showing invoices approaching 45-day deadline
5. THE System SHALL provide a dashboard widget showing invoices approaching 120-day deadline
6. WHEN a lien warning is sent, THE System SHALL record the timestamp
7. WHEN a lien is filed, THE System SHALL record the filing date
8. THE System SHALL provide quick action buttons for "Send Warning" and "Mark Filed"

### Requirement 12: Invoice Reminders (Manual)

**User Story:** As a business owner, I want to manually send payment reminders for overdue invoices, so that I can follow up with customers on outstanding payments.

#### Acceptance Criteria

1. THE System SHALL provide a "Send Reminder" action on overdue invoices
2. WHEN a reminder is sent, THE System SHALL increment the reminder count
3. WHEN a reminder is sent, THE System SHALL update the last_reminder_sent timestamp
4. THE System SHALL display recommended reminder schedule (3, 7, 14 days past due)
5. THE System SHALL NOT automatically send reminders (manual triggers only)

### Requirement 13: Invoice List and Filtering

**User Story:** As a business owner, I want to view and filter invoices by various criteria, so that I can quickly find invoices for follow-up, reporting, or payment processing.

#### Acceptance Criteria

1. WHEN a user requests an invoice list, THE System SHALL return invoices with pagination support
2. WHEN a user filters by status, THE System SHALL return only invoices matching that status
3. WHEN a user filters by customer, THE System SHALL return only invoices for that customer
4. WHEN a user filters by date range, THE System SHALL return invoices within that range
5. THE System SHALL provide a dedicated endpoint for overdue invoices
6. THE System SHALL provide a dedicated endpoint for lien deadline invoices
7. THE System SHALL return results sorted by invoice_date descending by default

### Requirement 14: User Authentication

**User Story:** As a system administrator, I want users to authenticate before accessing the system, so that I can secure the application and track who performs actions.

#### Acceptance Criteria

1. WHEN a user provides valid credentials, THE System SHALL issue an access token and refresh token
2. WHEN a user provides invalid credentials, THE System SHALL reject the login with an error message
3. THE System SHALL use JWT tokens for API authentication
4. THE System SHALL set access token expiration to 15 minutes
5. THE System SHALL set refresh token expiration to 7 days
6. THE System SHALL store refresh tokens as HttpOnly cookies
7. THE System SHALL store access tokens in memory (not localStorage)
8. WHEN a user logs out, THE System SHALL invalidate the refresh token

### Requirement 15: User Model (Staff Extension)

**User Story:** As a system administrator, I want to enable login for staff members, so that existing staff can authenticate without creating duplicate user records.

#### Acceptance Criteria

1. THE System SHALL extend the Staff model with authentication fields
2. THE System SHALL add username field (unique, nullable for non-login staff)
3. THE System SHALL add password_hash field (nullable for non-login staff)
4. THE System SHALL add is_login_enabled flag (default false)
5. THE System SHALL add last_login timestamp
6. THE System SHALL add failed_login_attempts counter (default 0)
7. THE System SHALL add locked_until timestamp for account lockout
8. THE System SHALL hash passwords using bcrypt with cost factor 12

### Requirement 16: Account Security

**User Story:** As a system administrator, I want account security measures, so that the system is protected against unauthorized access attempts.

#### Acceptance Criteria

1. THE System SHALL require passwords with minimum 8 characters
2. THE System SHALL require passwords with at least one uppercase letter
3. THE System SHALL require passwords with at least one lowercase letter
4. THE System SHALL require passwords with at least one number
5. WHEN a user fails login 5 times consecutively, THE System SHALL lock the account for 15 minutes
6. WHEN an account is locked, THE System SHALL reject login attempts with a lockout message
7. WHEN a successful login occurs, THE System SHALL reset the failed login counter
8. THE System SHALL implement CSRF protection for cookie-based authentication

### Requirement 17: Role-Based Access Control

**User Story:** As a system administrator, I want to control access based on user roles, so that users can only perform actions appropriate to their responsibilities.

#### Acceptance Criteria

1. THE System SHALL support three roles: admin, manager, tech
2. WHEN a user has admin role, THE System SHALL grant full system access
3. WHEN a user has manager role, THE System SHALL grant operations management access
4. WHEN a user has tech role, THE System SHALL grant limited field technician access
5. THE System SHALL restrict schedule generation to admin and manager roles
6. THE System SHALL restrict schedule clearing to admin and manager roles
7. THE System SHALL restrict invoice management to admin and manager roles
8. THE System SHALL restrict lien warning sending to admin role only
9. THE System SHALL restrict staff management to admin role only
10. THE System SHALL allow techs to view only their assigned jobs
11. THE System SHALL allow techs to update status only on their assigned jobs
12. THE System SHALL allow techs to record on-site payments

### Requirement 18: Authentication Endpoints

**User Story:** As a frontend developer, I want authentication API endpoints, so that I can implement login, logout, and session management in the UI.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/auth/login endpoint for authentication
2. THE System SHALL provide POST /api/v1/auth/logout endpoint for session termination
3. THE System SHALL provide POST /api/v1/auth/refresh endpoint for token refresh
4. THE System SHALL provide GET /api/v1/auth/me endpoint for current user info
5. THE System SHALL provide POST /api/v1/auth/change-password endpoint for password changes
6. WHEN login succeeds, THE System SHALL return user info and access token
7. WHEN login fails, THE System SHALL return 401 Unauthorized with error message
8. WHEN token refresh fails, THE System SHALL return 401 Unauthorized

### Requirement 19: Frontend Authentication Components

**User Story:** As a user, I want a login page and authentication flow, so that I can securely access the system.

#### Acceptance Criteria

1. THE System SHALL display a login page with username and password fields
2. THE System SHALL display a password visibility toggle
3. THE System SHALL display a "Remember me" checkbox
4. THE System SHALL display error messages for invalid credentials
5. THE System SHALL display loading state during authentication
6. THE System SHALL redirect to dashboard after successful login
7. THE System SHALL redirect to login page when accessing protected routes without authentication
8. THE System SHALL display user menu in header with logout option

### Requirement 20: Protected Routes

**User Story:** As a system administrator, I want routes protected by authentication, so that unauthenticated users cannot access the application.

#### Acceptance Criteria

1. THE System SHALL wrap all application routes with authentication check
2. WHEN a user is not authenticated, THE System SHALL redirect to login page
3. WHEN a user is authenticated, THE System SHALL allow access to permitted routes
4. WHEN a user's role does not permit access, THE System SHALL display an access denied message
5. THE System SHALL maintain authentication state across page refreshes
6. THE System SHALL automatically refresh tokens before expiration

### Requirement 21: API Logging and Audit

**User Story:** As a system administrator, I want comprehensive logging of all operations, so that I can audit changes, troubleshoot issues, and monitor system usage.

#### Acceptance Criteria

1. WHEN any schedule clear operation is initiated, THE System SHALL log the operation with parameters
2. WHEN any invoice operation is initiated, THE System SHALL log the operation with parameters
3. WHEN any authentication operation is initiated, THE System SHALL log the operation (excluding passwords)
4. WHEN any operation completes successfully, THE System SHALL log the completion with result identifiers
5. WHEN any operation fails, THE System SHALL log the failure with error details
6. THE System SHALL use structured logging with appropriate domain namespaces
7. THE System SHALL include request correlation IDs in all log entries
8. THE System SHALL log at appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Requirement 22: API Response Standards

**User Story:** As an API consumer, I want consistent, well-structured API responses, so that I can reliably integrate with the new endpoints.

#### Acceptance Criteria

1. WHEN an operation succeeds, THE System SHALL return appropriate HTTP status codes (200, 201, 204)
2. WHEN validation fails, THE System SHALL return 400 Bad Request with detailed error messages
3. WHEN a resource is not found, THE System SHALL return 404 Not Found with descriptive message
4. WHEN authentication fails, THE System SHALL return 401 Unauthorized
5. WHEN authorization fails, THE System SHALL return 403 Forbidden
6. WHEN a server error occurs, THE System SHALL return 500 Internal Server Error with correlation ID
7. THE System SHALL return JSON responses following consistent schema patterns
