# Requirements Document: Admin Dashboard (Phase 3)

## Overview

Phase 3 introduces the first user interface for the Grin's Irrigation Platform. After completing the backend foundation (Phase 1: Customer Management, Phase 2: Field Operations), we now build a React-based Admin Dashboard that enables Viktor to manage customers, jobs, and staff through a visual interface with simple scheduling capabilities.

## User Stories

### 1. Dashboard Overview

#### 1.1 View Business Metrics
**As** Viktor (business owner)  
**I want** to see key business metrics at a glance  
**So that** I can understand the current state of operations

**Acceptance Criteria:**
- 1.1.1 Dashboard displays total active customers count
- 1.1.2 Dashboard displays jobs by status (requested, approved, scheduled, in-progress, completed)
- 1.1.3 Dashboard displays today's scheduled appointments count
- 1.1.4 Dashboard displays available staff count
- 1.1.5 Metrics refresh automatically or on page load
- 1.1.6 Dashboard loads within 2 seconds

#### 1.2 View Recent Activity
**As** Viktor  
**I want** to see recent activity (new jobs, status changes)  
**So that** I can stay informed about what's happening

**Acceptance Criteria:**
- 1.2.1 Recent activity shows last 10 job status changes
- 1.2.2 Each activity item shows job type, customer name, and timestamp
- 1.2.3 Activity items are clickable and navigate to job detail

---

### 2. Customer Management UI

#### 2.1 View Customer List
**As** Viktor  
**I want** to see a list of all customers  
**So that** I can find and manage customer information

**Acceptance Criteria:**
- 2.1.1 Customer list displays in a sortable table
- 2.1.2 Table shows: name, phone, email, status, flags (priority, red flag, slow payer)
- 2.1.3 Table supports pagination (20 items per page default)
- 2.1.4 Table supports sorting by name, created date, status
- 2.1.5 Clicking a row navigates to customer detail

#### 2.2 Search and Filter Customers
**As** Viktor  
**I want** to search and filter customers  
**So that** I can quickly find specific customers

**Acceptance Criteria:**
- 2.2.1 Search box filters by name, phone, or email
- 2.2.2 Search is debounced (300ms delay)
- 2.2.3 Filter by status (active/inactive)
- 2.2.4 Filter by flags (priority, red flag, slow payer)
- 2.2.5 Filters can be combined
- 2.2.6 Clear filters button resets all filters

#### 2.3 Create New Customer
**As** Viktor  
**I want** to create a new customer  
**So that** I can add new clients to the system

**Acceptance Criteria:**
- 2.3.1 "Add Customer" button opens a form dialog
- 2.3.2 Form includes: first name, last name, phone (required), email (optional)
- 2.3.3 Form includes: lead source dropdown
- 2.3.4 Form includes: SMS opt-in and email opt-in checkboxes
- 2.3.5 Phone number is validated (10 digits)
- 2.3.6 Duplicate phone shows error message
- 2.3.7 Success shows toast notification and adds customer to list
- 2.3.8 Form can be cancelled without saving

#### 2.4 View Customer Detail
**As** Viktor  
**I want** to view complete customer information  
**So that** I can see all details about a customer

**Acceptance Criteria:**
- 2.4.1 Detail page shows all customer fields
- 2.4.2 Detail page shows customer flags with visual indicators
- 2.4.3 Detail page shows list of customer's properties
- 2.4.4 Detail page shows list of customer's jobs
- 2.4.5 Edit button opens edit form
- 2.4.6 Back button returns to customer list

#### 2.5 Edit Customer
**As** Viktor  
**I want** to edit customer information  
**So that** I can keep customer data up to date

**Acceptance Criteria:**
- 2.5.1 Edit form pre-populates with current values
- 2.5.2 All fields are editable
- 2.5.3 Validation rules same as create
- 2.5.4 Save shows success toast
- 2.5.5 Cancel discards changes

#### 2.6 Update Customer Flags
**As** Viktor  
**I want** to update customer flags (priority, red flag, slow payer)  
**So that** I can mark important customer attributes

**Acceptance Criteria:**
- 2.6.1 Flags are toggleable from detail page
- 2.6.2 Flag changes save immediately
- 2.6.3 Visual feedback shows flag state change

---

### 3. Job Management UI

#### 3.1 View Job List
**As** Viktor  
**I want** to see a list of all jobs  
**So that** I can manage job requests and track progress

**Acceptance Criteria:**
- 3.1.1 Job list displays in a sortable table
- 3.1.2 Table shows: job type, customer name, status, priority, created date
- 3.1.3 Status shown with color-coded badges
- 3.1.4 Priority shown with visual indicator (normal, high, urgent)
- 3.1.5 Table supports pagination
- 3.1.6 Clicking a row navigates to job detail

#### 3.2 Filter Jobs by Status
**As** Viktor  
**I want** to filter jobs by status  
**So that** I can focus on jobs in specific stages

**Acceptance Criteria:**
- 3.2.1 Status filter dropdown with all status options
- 3.2.2 "Ready to Schedule" quick filter button
- 3.2.3 "Needs Estimate" quick filter button
- 3.2.4 Filter by category (ready_to_schedule, requires_estimate)
- 3.2.5 Filter by priority level
- 3.2.6 Date range filter for created date

#### 3.3 Create New Job
**As** Viktor  
**I want** to create a new job request  
**So that** I can track work that needs to be done

**Acceptance Criteria:**
- 3.3.1 "Add Job" button opens form dialog
- 3.3.2 Customer selection with search/autocomplete
- 3.3.3 Property selection (filtered by selected customer)
- 3.3.4 Service type selection from service catalog
- 3.3.5 Job type text field
- 3.3.6 Description text area
- 3.3.7 Priority level selection (normal, high, urgent)
- 3.3.8 Job auto-categorizes based on type
- 3.3.9 Success shows toast and adds to list

#### 3.4 View Job Detail
**As** Viktor  
**I want** to view complete job information  
**So that** I can see all details about a job

**Acceptance Criteria:**
- 3.4.1 Detail page shows all job fields
- 3.4.2 Shows linked customer with link to customer detail
- 3.4.3 Shows linked property with address
- 3.4.4 Shows linked service offering
- 3.4.5 Shows status history timeline
- 3.4.6 Shows pricing information

#### 3.5 Update Job Status
**As** Viktor  
**I want** to update job status  
**So that** I can track job progress through the workflow

**Acceptance Criteria:**
- 3.5.1 Status dropdown shows only valid next statuses
- 3.5.2 Status change requires confirmation for certain transitions
- 3.5.3 Status change updates timestamp automatically
- 3.5.4 Status change adds entry to history
- 3.5.5 Invalid transitions show error message

#### 3.6 Edit Job
**As** Viktor  
**I want** to edit job information  
**So that** I can update job details as needed

**Acceptance Criteria:**
- 3.6.1 Edit form pre-populates with current values
- 3.6.2 Can update description, priority, pricing
- 3.6.3 Cannot change customer after creation
- 3.6.4 Save shows success toast

---

### 4. Staff Management UI

#### 4.1 View Staff List
**As** Viktor  
**I want** to see a list of all staff members  
**So that** I can manage my team

**Acceptance Criteria:**
- 4.1.1 Staff list displays in a table
- 4.1.2 Table shows: name, role, skill level, availability status
- 4.1.3 Availability shown with visual indicator (available/unavailable)
- 4.1.4 Filter by role (tech, sales, admin)
- 4.1.5 Filter by availability

#### 4.2 View Staff Detail
**As** Viktor  
**I want** to view staff member details  
**So that** I can see their information and assignments

**Acceptance Criteria:**
- 4.2.1 Detail page shows all staff fields
- 4.2.2 Shows certifications list
- 4.2.3 Shows current availability status
- 4.2.4 Shows upcoming appointments (future feature)

#### 4.3 Update Staff Availability
**As** Viktor  
**I want** to update staff availability  
**So that** I can manage who is available for work

**Acceptance Criteria:**
- 4.3.1 Toggle availability from list or detail page
- 4.3.2 Can add availability notes
- 4.3.3 Change saves immediately

---

### 5. Scheduling UI

#### 5.1 View Schedule Calendar
**As** Viktor  
**I want** to see appointments on a calendar  
**So that** I can visualize the schedule

**Acceptance Criteria:**
- 5.1.1 Calendar displays in month, week, and day views
- 5.1.2 Appointments shown as events on calendar
- 5.1.3 Events color-coded by status
- 5.1.4 Events show customer name and job type
- 5.1.5 Clicking event opens appointment detail
- 5.1.6 Can navigate between dates

#### 5.2 Create Appointment
**As** Viktor  
**I want** to create an appointment for a job  
**So that** I can schedule work

**Acceptance Criteria:**
- 5.2.1 "Create Appointment" button opens form
- 5.2.2 Job selection (only approved jobs without appointments)
- 5.2.3 Staff assignment selection
- 5.2.4 Date picker for scheduled date
- 5.2.5 Time window selection (start and end time)
- 5.2.6 Notes field
- 5.2.7 Success shows appointment on calendar
- 5.2.8 Job status updates to "scheduled"

#### 5.3 View Appointment Detail
**As** Viktor  
**I want** to view appointment details  
**So that** I can see all scheduling information

**Acceptance Criteria:**
- 5.3.1 Shows job information
- 5.3.2 Shows customer and property information
- 5.3.3 Shows assigned staff
- 5.3.4 Shows date and time window
- 5.3.5 Shows appointment status
- 5.3.6 Edit and cancel buttons available

#### 5.4 Edit Appointment
**As** Viktor  
**I want** to edit an appointment  
**So that** I can reschedule or reassign

**Acceptance Criteria:**
- 5.4.1 Can change date and time
- 5.4.2 Can change assigned staff
- 5.4.3 Can update notes
- 5.4.4 Cannot change linked job
- 5.4.5 Save updates calendar view

#### 5.5 Cancel Appointment
**As** Viktor  
**I want** to cancel an appointment  
**So that** I can handle schedule changes

**Acceptance Criteria:**
- 5.5.1 Cancel requires confirmation
- 5.5.2 Cancelled appointments removed from calendar
- 5.5.3 Job status reverts to "approved"
- 5.5.4 Appointment record retained with cancelled status

#### 5.6 View Daily Schedule
**As** Viktor  
**I want** to see all appointments for a specific day  
**So that** I can review the daily workload

**Acceptance Criteria:**
- 5.6.1 Daily view shows all appointments
- 5.6.2 Appointments grouped by staff member
- 5.6.3 Shows time windows and job details
- 5.6.4 Can navigate to previous/next day

#### 5.7 View Staff Daily Schedule
**As** Viktor  
**I want** to see a specific staff member's daily schedule  
**So that** I can review their workload

**Acceptance Criteria:**
- 5.7.1 Shows all appointments for selected staff on selected date
- 5.7.2 Shows route order if multiple appointments
- 5.7.3 Shows total scheduled time

---

### 6. Navigation and Layout

#### 6.1 Main Navigation
**As** Viktor  
**I want** consistent navigation throughout the app  
**So that** I can easily move between sections

**Acceptance Criteria:**
- 6.1.1 Sidebar navigation with links to all sections
- 6.1.2 Current section highlighted in navigation
- 6.1.3 Navigation icons for visual recognition
- 6.1.4 Sidebar can be collapsed on smaller screens
- 6.1.5 Header shows current page title

#### 6.2 Responsive Design
**As** Viktor  
**I want** the dashboard to work on different screen sizes  
**So that** I can use it on my laptop or tablet

**Acceptance Criteria:**
- 6.2.1 Layout adapts to screen width
- 6.2.2 Tables scroll horizontally on small screens
- 6.2.3 Forms remain usable on tablet
- 6.2.4 Minimum supported width: 768px

---

### 7. Backend: Appointment Management

#### 7.1 Create Appointment
**As** the system  
**I need** to create appointment records  
**So that** jobs can be scheduled

**Acceptance Criteria:**
- 7.1.1 Appointment links to job, staff, and inherits customer/property
- 7.1.2 Scheduled date and time window are required
- 7.1.3 Creating appointment updates job status to "scheduled"
- 7.1.4 Appointment status defaults to "scheduled"
- 7.1.5 Validates job is in "approved" status
- 7.1.6 Validates staff exists and is active

#### 7.2 Update Appointment
**As** the system  
**I need** to update appointment records  
**So that** schedules can be modified

**Acceptance Criteria:**
- 7.2.1 Can update date, time window, staff, notes
- 7.2.2 Cannot change linked job
- 7.2.3 Updates timestamp on modification

#### 7.3 Cancel Appointment
**As** the system  
**I need** to cancel appointments  
**So that** schedule changes can be handled

**Acceptance Criteria:**
- 7.3.1 Cancellation sets status to "cancelled"
- 7.3.2 Cancellation reverts job status to "approved"
- 7.3.3 Cancelled appointments retained for history

#### 7.4 List Appointments
**As** the system  
**I need** to query appointments  
**So that** schedules can be displayed

**Acceptance Criteria:**
- 7.4.1 Filter by date range
- 7.4.2 Filter by staff
- 7.4.3 Filter by status
- 7.4.4 Support pagination
- 7.4.5 Include related job, customer, property data

#### 7.5 Daily Schedule View
**As** the system  
**I need** to provide daily schedule data  
**So that** daily views can be rendered

**Acceptance Criteria:**
- 7.5.1 Return all appointments for a specific date
- 7.5.2 Include full job and customer details
- 7.5.3 Order by time window start

#### 7.6 Staff Daily Schedule
**As** the system  
**I need** to provide staff-specific daily schedules  
**So that** individual workloads can be viewed

**Acceptance Criteria:**
- 7.6.1 Return appointments for specific staff on specific date
- 7.6.2 Include route order if available
- 7.6.3 Calculate total scheduled time

---

## Non-Functional Requirements

### 8. Performance

#### 8.1 Page Load Time
- 8.1.1 Initial page load under 3 seconds
- 8.1.2 Subsequent navigation under 1 second
- 8.1.3 API responses under 500ms

#### 8.2 Responsiveness
- 8.2.1 UI remains responsive during data loading
- 8.2.2 Loading indicators shown for async operations
- 8.2.3 Optimistic updates for better UX

### 9. Accessibility

#### 9.1 WCAG Compliance
- 9.1.1 All interactive elements keyboard accessible
- 9.1.2 Proper ARIA labels on components
- 9.1.3 Color contrast meets WCAG AA standards
- 9.1.4 Form fields have associated labels

### 10. Error Handling

#### 10.1 User Feedback
- 10.1.1 API errors show user-friendly messages
- 10.1.2 Form validation errors shown inline
- 10.1.3 Network errors show retry option
- 10.1.4 Success actions show confirmation toast

---

## Technical Constraints

- Frontend must use React 18 with TypeScript
- Must integrate with existing FastAPI backend
- Must follow Vertical Slice Architecture patterns
- Must use TanStack Query for server state
- Must use shadcn/ui for UI components
- Must be validated with agent-browser automation

---

## Out of Scope (Phase 3)

- Customer portal (self-service)
- Mobile PWA for field staff
- Route optimization
- Automated notifications
- Invoice generation
- Estimate management
- GPS tracking
- Offline support
