# Implementation Plan: Admin Dashboard (Phase 3)

## Overview

This implementation plan breaks down the Admin Dashboard feature into discrete coding tasks. Each task builds on previous work and includes testing requirements. The plan follows Vertical Slice Architecture patterns for the frontend and integrates with the existing backend (Phase 1: Customer Management, Phase 2: Field Operations).

## Tasks

- [x] 1. Kiro Setup
  - [x] 1.1 Create frontend-agent
    - Create `.kiro/agents/frontend-agent.json`
    - Configure for React + TypeScript development
    - Add resources for frontend patterns
    - _Requirements: Kiro Integration_

  - [x] 1.2 Create component-agent
    - Create `.kiro/agents/component-agent.json`
    - Configure for React component creation with shadcn/ui
    - Add resources for UI components
    - _Requirements: Kiro Integration_

  - [x] 1.3 Create frontend prompts
    - Create `@implement-feature-slice` prompt
    - Create `@implement-api-client` prompt
    - Create `@implement-tanstack-hook` prompt
    - _Requirements: Kiro Integration_

  - [x] 1.4 Create frontend hooks
    - Create `frontend-lint.json` hook
    - Create `frontend-typecheck.json` hook
    - Create `validate-ui-on-complete.json` hook
    - _Requirements: Kiro Integration_

  - [x] 1.5 Create steering documents
    - Create `frontend-patterns.md` steering document
    - Create `frontend-testing.md` steering document
    - _Requirements: Kiro Integration_


- [ ] 2. Backend - Appointments
  - [ ] 2.1 Create appointments table migration
    - Define table with all columns from design
    - Add foreign keys to jobs and staff tables
    - Add indexes for job_id, staff_id, scheduled_date, status
    - Add check constraints for status enum
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 2.2 Create Appointment SQLAlchemy model
    - Define model with all fields from design
    - Add relationships to Job and Staff
    - Add AppointmentStatus enum
    - Configure timestamps
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ] 2.3 Create appointment Pydantic schemas
    - AppointmentCreate with validation
    - AppointmentUpdate with optional fields
    - AppointmentResponse
    - AppointmentListParams with filters
    - DailyScheduleResponse
    - WeeklyScheduleResponse
    - _Requirements: 1.1-1.5_

  - [ ] 2.4 Create AppointmentRepository
    - Implement create method
    - Implement get_by_id method
    - Implement update method
    - Implement delete method
    - Implement list_with_filters method
    - Implement get_daily_schedule method
    - Implement get_staff_daily_schedule method
    - Implement get_weekly_schedule method
    - _Requirements: 1.1-1.5_

  - [ ] 2.5 Create AppointmentService with LoggerMixin
    - Implement create_appointment method
    - Implement get_appointment method
    - Implement update_appointment method
    - Implement cancel_appointment method
    - Implement list_appointments method
    - Implement get_daily_schedule method
    - Implement get_staff_daily_schedule method
    - Implement get_weekly_schedule method
    - _Requirements: 1.1-1.5_

  - [ ] 2.6 Implement appointment API endpoints
    - POST /api/v1/appointments (create)
    - GET /api/v1/appointments/{id} (get by ID)
    - PUT /api/v1/appointments/{id} (update)
    - DELETE /api/v1/appointments/{id} (cancel)
    - GET /api/v1/appointments (list with filters)
    - GET /api/v1/appointments/daily/{date} (daily schedule)
    - GET /api/v1/appointments/staff/{staff_id}/daily/{date} (staff daily)
    - GET /api/v1/appointments/weekly (weekly overview)
    - _Requirements: 1.1-1.5_

  - [ ] 2.7 Write appointment unit tests
    - Test AppointmentService methods with mocked repository
    - Test validation logic
    - Test status transitions
    - Target 85%+ coverage
    - _Requirements: 1.1-1.5_

  - [ ] 2.8 Write appointment integration tests
    - Test appointment-job relationship
    - Test appointment-staff relationship
    - Test daily and weekly schedule queries
    - Test with existing Phase 1/2 data
    - _Requirements: 1.1-1.5_


- [ ] 3. Backend - Dashboard Metrics
  - [ ] 3.1 Create dashboard Pydantic schemas
    - DashboardMetrics schema
    - RequestVolumeMetrics schema
    - ScheduleOverview schema
    - PaymentStatusOverview schema
    - _Requirements: 1.6_

  - [ ] 3.2 Create DashboardService with LoggerMixin
    - Implement get_overview_metrics method
    - Implement get_request_volume method
    - Implement get_schedule_overview method
    - Implement get_payment_status method
    - _Requirements: 1.6_

  - [ ] 3.3 Implement dashboard API endpoints
    - GET /api/v1/dashboard/overview (metrics)
    - GET /api/v1/dashboard/requests (request volume)
    - GET /api/v1/dashboard/schedule (schedule overview)
    - GET /api/v1/dashboard/payments (payment status)
    - _Requirements: 1.6_

  - [ ] 3.4 Write dashboard tests
    - Test DashboardService methods
    - Test API endpoints
    - Test with sample data
    - _Requirements: 1.6_

- [ ] 4. Checkpoint - Backend Complete
  - Ensure all backend tests pass
  - Ensure all quality checks pass (ruff, mypy, pyright)
  - Verify 12 new API endpoints working
  - Ask the user if questions arise


- [ ] 5. Frontend Foundation
  - [ ] 5.1 Initialize Vite + React + TypeScript project
    - Create frontend directory
    - Initialize with Vite React TypeScript template
    - Configure TypeScript strict mode
    - Set up path aliases (@/)
    - _Requirements: 2.1_

  - [ ] 5.2 Configure Tailwind CSS
    - Install Tailwind CSS and dependencies
    - Create tailwind.config.js
    - Configure content paths
    - Add base styles
    - _Requirements: 2.1_

  - [ ] 5.3 Install and configure shadcn/ui
    - Initialize shadcn/ui
    - Install core components (button, card, input, label, select, table, dialog, dropdown-menu, badge, toast, form, calendar, popover, separator, skeleton, tabs)
    - Configure component paths
    - _Requirements: 2.1_

  - [ ] 5.4 Set up TanStack Query provider
    - Install @tanstack/react-query
    - Create QueryProvider component
    - Configure default options
    - Add React Query DevTools
    - _Requirements: 2.1_

  - [ ] 5.5 Create Axios API client
    - Install axios
    - Create core/api/client.ts
    - Configure base URL from environment
    - Add request/response interceptors
    - Add error handling
    - Create core/api/types.ts for response types
    - _Requirements: 2.1_

  - [ ] 5.6 Set up React Router
    - Install react-router-dom
    - Create core/router/index.tsx
    - Define route structure
    - Create placeholder pages
    - _Requirements: 2.1_

  - [ ] 5.7 Create Layout component
    - Create shared/components/Layout.tsx
    - Implement sidebar navigation
    - Implement header with user info
    - Add responsive design
    - Add data-testid attributes for testing
    - _Requirements: 2.2_

  - [ ] 5.8 Create shared UI components
    - Create PageHeader component
    - Create StatusBadge component
    - Create LoadingSpinner component
    - Create ErrorBoundary component
    - _Requirements: 2.2_

  - [ ] 5.9 Configure ESLint + Prettier
    - Install ESLint with TypeScript support
    - Install Prettier
    - Configure rules for React
    - Add lint and format scripts
    - _Requirements: 2.1_

  - [ ] 5.10 Set up Vitest for testing
    - Install vitest and @testing-library/react
    - Configure vitest.config.ts
    - Create test setup file
    - Add test script to package.json
    - _Requirements: 2.1_


- [ ] 6. Checkpoint - Frontend Foundation
  - Ensure frontend builds without errors
  - Ensure TypeScript compiles
  - Ensure ESLint passes
  - Verify layout renders correctly
  - Run agent-browser layout validation
  - Ask the user if questions arise

- [ ] 7. Customer Feature Slice
  - [ ] 7.1 Create customer types and API client
    - Create features/customers/types/index.ts
    - Define Customer, CustomerCreate, CustomerUpdate types
    - Create features/customers/api/customerApi.ts
    - Implement all API functions
    - _Requirements: 3.1_

  - [ ] 7.2 Create customer query hooks
    - Create useCustomers hook (list with pagination)
    - Create useCustomer hook (single customer)
    - Create useCustomerSearch hook
    - Use queryKey factory pattern
    - _Requirements: 3.1_

  - [ ] 7.3 Create customer mutation hooks
    - Create useCreateCustomer mutation
    - Create useUpdateCustomer mutation
    - Create useDeleteCustomer mutation
    - Add optimistic updates
    - _Requirements: 3.1_

  - [ ] 7.4 Create CustomerList component
    - Use TanStack Table for data display
    - Implement sorting and pagination
    - Add status badges for flags
    - Add data-testid attributes
    - _Requirements: 3.1_

  - [ ] 7.5 Create CustomerDetail component
    - Display customer information
    - Show properties list
    - Show jobs history
    - Add edit and delete actions
    - _Requirements: 3.1_

  - [ ] 7.6 Create CustomerForm component
    - Use React Hook Form + Zod
    - Implement all fields from schema
    - Add validation messages
    - Handle create and edit modes
    - _Requirements: 3.1_

  - [ ] 7.7 Create CustomerSearch component
    - Implement debounced search
    - Integrate with useCustomers hook
    - Add clear functionality
    - _Requirements: 3.1_

  - [ ] 7.8 Write customer component tests
    - Test CustomerList rendering
    - Test CustomerForm validation
    - Test CustomerSearch functionality
    - Use React Testing Library
    - _Requirements: 3.1_


- [ ] 8. Checkpoint - Customer Feature
  - Ensure all customer tests pass
  - Ensure TypeScript compiles
  - Ensure ESLint passes
  - Run agent-browser customer CRUD validation
  - Ask the user if questions arise

- [ ] 9. Jobs Feature Slice
  - [ ] 9.1 Create job types and API client
    - Create features/jobs/types/index.ts
    - Define Job, JobCreate, JobUpdate, JobStatus types
    - Create features/jobs/api/jobApi.ts
    - Implement all API functions
    - _Requirements: 4.1_

  - [ ] 9.2 Create job query hooks
    - Create useJobs hook (list with filters)
    - Create useJob hook (single job)
    - Create useJobsByStatus hook
    - Create useJobsReadyToSchedule hook
    - _Requirements: 4.1_

  - [ ] 9.3 Create job mutation hooks
    - Create useCreateJob mutation
    - Create useUpdateJob mutation
    - Create useUpdateJobStatus mutation
    - Create useDeleteJob mutation
    - _Requirements: 4.1_

  - [ ] 9.4 Create JobList component
    - Use TanStack Table for data display
    - Implement status filtering
    - Add sorting and pagination
    - Add data-testid attributes
    - _Requirements: 4.1_

  - [ ] 9.5 Create JobDetail component
    - Display job information
    - Show customer and property info
    - Show status history
    - Add status update actions
    - _Requirements: 4.1_

  - [ ] 9.6 Create JobForm component
    - Use React Hook Form + Zod
    - Implement customer and service selection
    - Add property selection based on customer
    - Handle create and edit modes
    - _Requirements: 4.1_

  - [ ] 9.7 Create JobStatusBadge component
    - Display status with appropriate colors
    - Handle all status values
    - Add tooltip with status description
    - _Requirements: 4.1_

  - [ ] 9.8 Write job component tests
    - Test JobList rendering and filtering
    - Test JobForm validation
    - Test JobStatusBadge display
    - Use React Testing Library
    - _Requirements: 4.1_


- [ ] 10. Checkpoint - Jobs Feature
  - Ensure all job tests pass
  - Ensure TypeScript compiles
  - Ensure ESLint passes
  - Run agent-browser jobs validation
  - Ask the user if questions arise

- [ ] 11. Schedule Feature Slice
  - [ ] 11.1 Create appointment types and API client
    - Create features/schedule/types/index.ts
    - Define Appointment, AppointmentCreate types
    - Create features/schedule/api/appointmentApi.ts
    - Implement all API functions
    - _Requirements: 5.1_

  - [ ] 11.2 Create appointment query hooks
    - Create useAppointments hook (list with filters)
    - Create useAppointment hook (single appointment)
    - Create useDailySchedule hook
    - Create useStaffDailySchedule hook
    - Create useWeeklySchedule hook
    - _Requirements: 5.1_

  - [ ] 11.3 Create appointment mutation hooks
    - Create useCreateAppointment mutation
    - Create useUpdateAppointment mutation
    - Create useCancelAppointment mutation
    - Add cache invalidation
    - _Requirements: 5.1_

  - [ ] 11.4 Install and configure FullCalendar
    - Install @fullcalendar/react and plugins
    - Configure daygrid and timegrid views
    - Set up interaction plugin
    - _Requirements: 5.1_

  - [ ] 11.5 Create SchedulePage component
    - Create main schedule page layout
    - Add view toggle (day/week/month)
    - Add create appointment button
    - Integrate with calendar view
    - _Requirements: 5.1_

  - [ ] 11.6 Create CalendarView component
    - Integrate FullCalendar
    - Display appointments as events
    - Handle event click for details
    - Handle date click for creation
    - Add data-testid attributes
    - _Requirements: 5.1_

  - [ ] 11.7 Create AppointmentForm component
    - Use React Hook Form + Zod
    - Implement job selection (ready to schedule)
    - Implement staff selection (available)
    - Add date and time window inputs
    - Handle create and edit modes
    - _Requirements: 5.1_

  - [ ] 11.8 Write schedule component tests
    - Test SchedulePage rendering
    - Test CalendarView event display
    - Test AppointmentForm validation
    - Use React Testing Library
    - _Requirements: 5.1_


- [ ] 12. Checkpoint - Schedule Feature
  - Ensure all schedule tests pass
  - Ensure TypeScript compiles
  - Ensure ESLint passes
  - Run agent-browser schedule validation
  - Ask the user if questions arise

- [ ] 13. Dashboard Feature
  - [ ] 13.1 Create dashboard types and API client
    - Create features/dashboard/types/index.ts
    - Define DashboardMetrics, RequestVolume types
    - Create features/dashboard/api/dashboardApi.ts
    - Implement all API functions
    - _Requirements: 6.1_

  - [ ] 13.2 Create dashboard query hooks
    - Create useDashboardMetrics hook
    - Create useRequestVolume hook
    - Create useScheduleOverview hook
    - _Requirements: 6.1_

  - [ ] 13.3 Create DashboardPage component
    - Create main dashboard layout
    - Add metrics cards section
    - Add recent activity section
    - Add quick actions section
    - _Requirements: 6.1_

  - [ ] 13.4 Create MetricsCard component
    - Display metric value and label
    - Add trend indicator
    - Add icon support
    - _Requirements: 6.1_

  - [ ] 13.5 Create RecentActivity component
    - Display recent jobs and appointments
    - Add links to detail pages
    - Add time formatting
    - _Requirements: 6.1_

  - [ ] 13.6 Write dashboard component tests
    - Test DashboardPage rendering
    - Test MetricsCard display
    - Test RecentActivity list
    - _Requirements: 6.1_


- [ ] 14. Staff Feature (Basic)
  - [ ] 14.1 Create staff types and API client
    - Create features/staff/types/index.ts
    - Define Staff, StaffCreate types
    - Create features/staff/api/staffApi.ts
    - Implement API functions
    - _Requirements: 7.1_

  - [ ] 14.2 Create staff query hooks
    - Create useStaff hook (list)
    - Create useStaffMember hook (single)
    - Create useAvailableStaff hook
    - _Requirements: 7.1_

  - [ ] 14.3 Create StaffList component
    - Display staff members in table
    - Show availability status
    - Add role badges
    - _Requirements: 7.1_

  - [ ] 14.4 Create StaffDetail component
    - Display staff information
    - Show daily schedule
    - Add availability toggle
    - _Requirements: 7.1_

- [ ] 15. Integration and Polish
  - [ ] 15.1 Implement cross-feature navigation
    - Add links from customer to jobs
    - Add links from job to customer
    - Add links from appointment to job/staff
    - Ensure consistent navigation patterns
    - _Requirements: 8.1_

  - [ ] 15.2 Implement error handling
    - Create global error boundary
    - Add toast notifications for errors
    - Handle API errors gracefully
    - Add retry functionality
    - _Requirements: 8.2_

  - [ ] 15.3 Implement loading states
    - Add skeleton loaders for lists
    - Add loading spinners for actions
    - Handle optimistic updates
    - _Requirements: 8.2_

  - [ ] 15.4 Verify responsive design
    - Test on mobile viewport
    - Test on tablet viewport
    - Ensure sidebar collapses properly
    - Verify table scrolling
    - _Requirements: 8.3_

  - [ ] 15.5 Conduct accessibility audit
    - Run axe accessibility checker
    - Verify keyboard navigation
    - Check color contrast
    - Add ARIA labels where needed
    - _Requirements: 8.4_

  - [ ] 15.6 Performance optimization
    - Add React.memo where appropriate
    - Optimize re-renders
    - Verify bundle size
    - Add code splitting for routes
    - _Requirements: 8.5_


- [ ] 16. Agent-Browser Validation
  - [ ] 16.1 Install and configure agent-browser
    - Install agent-browser globally
    - Download Chromium browser
    - Verify installation works
    - _Requirements: 9.1_

  - [ ] 16.2 Create validate-layout.sh script
    - Validate main layout renders
    - Validate sidebar navigation works
    - Validate header displays
    - Take screenshot for documentation
    - _Requirements: 9.1_

  - [ ] 16.3 Create validate-customers.sh script
    - Validate customer list displays
    - Validate customer CRUD operations
    - Validate search functionality
    - Take screenshots for documentation
    - _Requirements: 9.1_

  - [ ] 16.4 Create validate-jobs.sh script
    - Validate job list displays
    - Validate job status filtering
    - Validate job status updates
    - Take screenshots for documentation
    - _Requirements: 9.1_

  - [ ] 16.5 Create validate-schedule.sh script
    - Validate calendar renders
    - Validate appointment creation
    - Validate appointment display
    - Take screenshots for documentation
    - _Requirements: 9.1_

  - [ ] 16.6 Create validate-integration.sh script
    - Validate full user journey
    - Test customer → job → appointment flow
    - Verify cross-feature navigation
    - Generate final screenshots
    - _Requirements: 9.1_

- [ ] 17. Documentation and Quality
  - [ ] 17.1 Run all quality checks
    - Run ESLint and fix all issues
    - Run TypeScript compiler
    - Run Vitest and verify coverage
    - Run backend quality checks
    - _Requirements: Code Standards_

  - [ ] 17.2 Verify test coverage
    - Ensure 80%+ coverage on components
    - Ensure 85%+ coverage on hooks
    - Ensure 85%+ coverage on backend services
    - _Requirements: Code Standards_

  - [ ] 17.3 Update documentation
    - Update frontend README
    - Document component usage
    - Document API integration
    - _Requirements: Documentation_

  - [ ] 17.4 Update DEVLOG
    - Document implementation progress
    - Document decisions made
    - Document any deviations from design
    - _Requirements: Documentation_

- [ ] 18. Final Checkpoint
  - Ensure all frontend tests pass
  - Ensure all backend tests pass
  - Ensure all quality checks pass
  - Ensure all agent-browser validations pass
  - Verify 50 total API endpoints working (42 existing + 8 new)
  - Verify full admin dashboard functionality
  - Ask the user if questions arise


## Notes

- All tasks are required for comprehensive coverage
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Agent-browser validation is MANDATORY before moving to next feature
- Follow Vertical Slice Architecture patterns for frontend
- Use TanStack Query for ALL API calls (no manual fetch)
- Prioritize working features over polish

## Dependencies

- Phase 1 (Customer Management) must be complete
- Phase 2 (Field Operations) must be complete
- Database must be running with Phase 1/2 migrations applied
- All Phase 1/2 tests should be passing

## Frontend Dependencies (npm)

```bash
# Core
npm install react react-dom
npm install -D typescript @types/react @types/react-dom
npm install -D vite @vitejs/plugin-react

# Styling
npm install -D tailwindcss postcss autoprefixer
npm install class-variance-authority clsx tailwind-merge

# State Management
npm install @tanstack/react-query
npm install -D @tanstack/react-query-devtools

# Forms
npm install react-hook-form @hookform/resolvers zod

# Tables
npm install @tanstack/react-table

# Calendar
npm install @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction

# Routing
npm install react-router-dom

# HTTP
npm install axios

# Utilities
npm install date-fns lucide-react

# Testing
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

## Backend Dependencies (Python)

No new Python dependencies required - uses existing FastAPI, SQLAlchemy, Pydantic stack.

## Verification Commands

### Backend
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest -v
```

### Frontend
```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

### Agent-Browser UI Validation
```bash
# Ensure frontend is running first: cd frontend && npm run dev
bash scripts/validate-layout.sh
bash scripts/validate-customers.sh
bash scripts/validate-jobs.sh
bash scripts/validate-schedule.sh
bash scripts/validate-integration.sh
```

### Full Validation
```bash
bash scripts/validate-all.sh
```
