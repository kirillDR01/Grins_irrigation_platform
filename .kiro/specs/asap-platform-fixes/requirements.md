# Requirements Document

## Introduction

This document captures the ASAP platform fixes for the Grins Platform — a collection of bugs, usability issues, and missing features reported by users across the UI/UX, authentication, CRM/leads, jobs, forms, and navigation areas. Each issue is formalized as a requirement with EARS-pattern acceptance criteria to ensure testable, verifiable fixes.

## Glossary

- **Platform**: The Grins Platform application, consisting of a React 19 frontend and FastAPI backend
- **Customer_Search**: The search input field in the Customers list page (`CustomerList.tsx`) that filters customers by name, phone, or email
- **Zone_Count_Input**: The numeric input on the public service package sign-up page where users specify the number of irrigation zones on their property
- **Subscription_Portal**: The Stripe Customer Portal used by end-customers to manage their subscription billing, accessed via email link
- **Auth_System**: The JWT-based authentication system using access tokens (15-minute expiry) and refresh tokens (7-day expiry stored as HttpOnly cookies)
- **Lead**: A prospective customer record in the CRM, sourced from website forms, Google Sheets, or phone calls
- **Lead_Conversion**: The process of promoting a Lead to a Customer record, optionally creating a Job simultaneously
- **Google_Sheets_Poller**: The background service that polls a Google Sheet for new form submissions and creates Lead records
- **Job**: A work order associated with a Customer, with a type (e.g., spring_startup, repair, installation) and lifecycle status
- **Job_Type**: The classification of a Job (spring_startup, summer_tuneup, winterization, repair, diagnostic, installation, landscaping)
- **Service_Package_Form**: The public-facing checkout flow for subscribing to a service package via Stripe
- **Work_Request_Tab**: The navigation entry and page for viewing Google Sheets form submissions, currently accessible at `/work-requests`
- **Sidebar**: The main navigation component (`Layout.tsx`) containing links to all platform sections

## Requirements

### Requirement 1: Debounce Customer Search Input

**User Story:** As a platform user, I want the customer search to wait until I finish typing before fetching results, so that the page does not refresh on every keystroke.

#### Acceptance Criteria

1. WHEN a user types into the Customer_Search field, THE Platform SHALL debounce the search query by at least 300 milliseconds before issuing an API request
2. WHILE the user is actively typing in the Customer_Search field, THE Platform SHALL not trigger additional API requests until the debounce period elapses
3. WHEN the debounced search query changes, THE Platform SHALL reset pagination to page 1
4. THE Customer_Search SHALL preserve the current search text in the input field without visual delay or flicker during debounce



### Requirement 2: Fix Subscription Management Email Flow

**User Story:** As a subscriber, I want to receive a working login email when I request to manage my subscription, so that I can access the Subscription_Portal without confusion.

#### Acceptance Criteria

1. WHEN a subscriber enters a valid email address to manage their subscription, THE Subscription_Portal SHALL send a login email within 60 seconds
2. IF the email address does not match any active subscription, THEN THE Platform SHALL display a clear error message indicating no subscription was found for that email
3. WHEN the login email is sent, THE Platform SHALL display a confirmation message with instructions to check their inbox and spam folder
4. THE Platform SHALL provide a "Resend Email" option if the subscriber does not receive the initial email

### Requirement 3: Extend Authentication Session Duration

**User Story:** As a platform user, I want my login session to last longer, so that I do not have to re-authenticate frequently during my workday.

#### Acceptance Criteria

1. THE Auth_System SHALL issue access tokens with a minimum expiration of 60 minutes
2. THE Auth_System SHALL issue refresh tokens with a minimum expiration of 30 days
3. WHEN an access token expires, THE Auth_System SHALL automatically refresh the token using the refresh token cookie without requiring user interaction
4. THE Auth_System SHALL update the access token cookie max-age to match the new access token expiration

### Requirement 4: Persist Authentication Across Page Refresh

**User Story:** As a platform user, I want to remain logged in after refreshing the page, so that I do not lose my session unexpectedly.

#### Acceptance Criteria

1. WHEN the user refreshes the browser page, THE Auth_System SHALL attempt to restore the session by calling the refresh token endpoint
2. WHEN the refresh token is valid, THE Auth_System SHALL obtain a new access token and restore the user session without displaying the login page
3. IF the refresh token has expired or is invalid, THEN THE Auth_System SHALL redirect the user to the login page
4. WHILE the session restoration is in progress, THE Platform SHALL display a loading indicator instead of the login page



### Requirement 5: Fix Lead Deletion

**User Story:** As a platform user, I want to delete leads without encountering network errors, so that I can keep my CRM clean.

#### Acceptance Criteria

1. WHEN a user requests to delete a Lead, THE Platform SHALL send a DELETE request to the leads API and remove the Lead record from the database
2. WHEN the deletion succeeds, THE Platform SHALL remove the Lead from the displayed list without requiring a full page refresh
3. IF the deletion fails due to a network error, THEN THE Platform SHALL display a descriptive error message and allow the user to retry
4. WHEN a user requests to delete a Lead, THE Platform SHALL display a confirmation dialog before executing the deletion

### Requirement 6: Fix Lead-to-Customer Conversion

**User Story:** As a platform user, I want lead conversion to use my specified job name and auto-remove the lead from the leads list, so that my CRM stays organized.

#### Acceptance Criteria

1. WHEN a user converts a Lead to a Customer with a job, THE Lead_Conversion SHALL use the user-provided job description as the job description, not a default value
2. WHEN a Lead is successfully converted, THE Lead_Conversion SHALL update the Lead status to "converted" and remove the Lead from the active leads list view
3. WHEN a user converts a Lead to a Customer without creating a job (toggle off), THE Lead_Conversion SHALL create the Customer record without requiring a job
4. IF the Lead has already been converted, THEN THE Lead_Conversion SHALL display an error message indicating the Lead is already converted
5. WHEN the create-job toggle is off, THE Platform SHALL not display the job description field and SHALL not send a job_description in the API request

### Requirement 7: Add Manual Lead Creation

**User Story:** As a platform user, I want to manually add leads through the CRM interface, so that I can capture leads from phone calls, walk-ins, or other offline sources.

#### Acceptance Criteria

1. THE Platform SHALL provide an "Add Lead" button on the Leads list page
2. WHEN the user clicks "Add Lead", THE Platform SHALL display a form with fields for: name, phone, email, address, city, state, zip code, situation, and notes
3. THE Platform SHALL require at minimum a name and phone number for manual lead creation
4. WHEN the user submits a valid manual lead form, THE Platform SHALL create the Lead via the API and display the new Lead in the leads list
5. IF the lead creation fails, THEN THE Platform SHALL display a descriptive error message without losing the form data

### Requirement 8: Enable Job Type Editing

> Note: See also Requirement 9 (Regression Testing) which ensures none of the fixes in Requirements 1-8 break existing platform functionality.

**User Story:** As a platform user, I want to change the job type of an existing job, so that I can correct mistakes or update the job classification as work scope changes.

#### Acceptance Criteria

1. WHEN a user edits an existing Job, THE Platform SHALL allow changing the Job_Type via the job type dropdown selector
2. THE Platform SHALL populate the job type dropdown with the current Job_Type value when editing
3. WHEN the user saves a Job with a changed Job_Type, THE Platform SHALL send the updated job_type to the API and reflect the change in the Job detail view
4. IF the job type update fails, THEN THE Platform SHALL display an error message and retain the previous Job_Type value

### Requirement 9: Regression Testing

**User Story:** As a business owner, I want confidence that the ASAP fixes do not break any existing platform functionality, so that my team can continue using all features without disruption.

#### Acceptance Criteria

1. AFTER all ASAP fixes are implemented, THE Platform SHALL pass all existing backend test suites (unit, functional, integration) with zero new failures
2. AFTER all ASAP fixes are implemented, THE Platform SHALL pass all existing frontend test suites (Vitest) with zero new failures
3. THE Platform SHALL pass E2E regression tests verifying that the following critical user flows still work: customer CRUD, lead-to-customer pipeline, job creation and listing, estimate creation, invoice portal, agreement flow, scheduling, dashboard, and navigation/auth
4. WHEN auth token durations are changed (Req 3), THE Platform SHALL verify that all authenticated API endpoints still accept valid tokens and reject expired tokens
5. WHEN lead service methods are modified (Req 5, 6, 7), THE Platform SHALL verify that the Google Sheets poller, lead-to-estimate flow, and lead SMS workflows still function correctly
6. WHEN the customer search is modified (Req 1), THE Platform SHALL verify that customer detail navigation, customer editing, and property management still work correctly



