# Phase 3 Implementation Planning

**Status:** Planning Complete - Ready for Implementation  
**Goal:** Implement Admin Dashboard UI with Simple Scheduling

---

## Executive Summary

Phase 3 introduces the first user interface for the Grin's Irrigation Platform. After completing the backend foundation (Phase 1: Customer Management, Phase 2: Field Operations), we now build a React-based Admin Dashboard that enables Viktor to manage customers, jobs, and staff through a visual interface.

### Selected Approach: Option D - Hybrid Admin Dashboard + Simple Scheduling

This approach balances:
- **Immediate Value**: Visual interface for daily operations
- **Technical Foundation**: PWA-ready architecture for future mobile app
- **Hackathon Scoring**: Maximum Kiro feature integration
- **Time Constraints**: Achievable in 6 days

### Key Deliverables

| Deliverable | Description | Priority |
|-------------|-------------|----------|
| **Admin Dashboard** | React SPA with customer, job, staff management | P0 |
| **Simple Scheduling** | Appointment creation and calendar view | P0 |
| **Backend Additions** | Appointment model and API endpoints | P0 |
| **Kiro Integration** | New spec, agents, prompts, hooks | P0 |

---

## Phase 2 Completion Summary

### What Was Accomplished ✅

**Field Operations Feature - COMPLETE**
- 26 new API endpoints (42 total)
- 764 tests passing (unit, functional, integration, PBT)
- All quality checks passing (Ruff, MyPy)
- 22/22 user interaction tests passing

**API Endpoints Delivered (Phase 2):**

```
# Service Catalog (6 endpoints)
GET    /api/v1/services                # List all services
GET    /api/v1/services/{id}           # Get service details
GET    /api/v1/services/category/{cat} # Services by category
POST   /api/v1/services                # Create service
PUT    /api/v1/services/{id}           # Update service
DELETE /api/v1/services/{id}           # Deactivate service

# Job Management (12 endpoints)
POST   /api/v1/jobs                    # Create job request
GET    /api/v1/jobs/{id}               # Get job by ID
PUT    /api/v1/jobs/{id}               # Update job
DELETE /api/v1/jobs/{id}               # Delete job
GET    /api/v1/jobs                    # List jobs (with filters)
PUT    /api/v1/jobs/{id}/status        # Update job status
GET    /api/v1/jobs/{id}/history       # Get job status history
GET    /api/v1/jobs/ready-to-schedule  # Jobs ready to schedule
GET    /api/v1/jobs/needs-estimate     # Jobs needing estimates
GET    /api/v1/jobs/by-status/{status} # Jobs by status
GET    /api/v1/customers/{id}/jobs     # Get customer's jobs
POST   /api/v1/jobs/{id}/calculate-price  # Calculate job price

# Staff Management (8 endpoints)
POST   /api/v1/staff                   # Create staff member
GET    /api/v1/staff/{id}              # Get staff by ID
PUT    /api/v1/staff/{id}              # Update staff
DELETE /api/v1/staff/{id}              # Deactivate staff
GET    /api/v1/staff                   # List staff
GET    /api/v1/staff/available         # List available staff
GET    /api/v1/staff/by-role/{role}    # Staff by role
PUT    /api/v1/staff/{id}/availability # Update availability
```

---

## Technology Stack Decision

### Frontend Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Framework** | React 18 + TypeScript | Type safety, component ecosystem, team familiarity |
| **Build Tool** | Vite | Fast builds, HMR, PWA plugin ready |
| **State Management** | TanStack Query v5 | Server state, caching, offline support |
| **Styling** | Tailwind CSS + shadcn/ui | Rapid development, consistent design |
| **Forms** | React Hook Form + Zod | Type-safe validation, performance |
| **Calendar** | FullCalendar | Industry standard, React integration |
| **Tables** | TanStack Table | Sorting, filtering, pagination |
| **Routing** | React Router v6 | Standard routing solution |
| **HTTP Client** | Axios | Interceptors, error handling |

### Why This Stack?

1. **React + TypeScript**: Type safety catches errors at compile time, excellent IDE support
2. **Vite**: 10-100x faster than Create React App, native ESM, PWA plugin
3. **TanStack Query**: Automatic caching, background refetching, offline support (critical for PWA)
4. **Tailwind + shadcn/ui**: Pre-built accessible components, consistent design system
5. **FullCalendar**: Handles complex scheduling UI out of the box

---

## Vertical Slice Architecture (Frontend)

Following the patterns from `vertical-slice-setup-guide-full.md`, the frontend will use feature-based organization:

### Directory Structure

```
frontend/
├── public/
│   ├── manifest.json           # PWA manifest
│   └── icons/                  # App icons
├── src/
│   ├── main.tsx                # Entry point
│   ├── App.tsx                 # Root component with providers
│   ├── vite-env.d.ts           # Vite types
│   │
│   ├── core/                   # Foundation (exists before features)
│   │   ├── api/
│   │   │   ├── client.ts       # Axios instance with interceptors
│   │   │   └── types.ts        # API response types
│   │   ├── config/
│   │   │   └── index.ts        # Environment configuration
│   │   ├── providers/
│   │   │   ├── QueryProvider.tsx    # TanStack Query setup
│   │   │   └── ThemeProvider.tsx    # Theme context
│   │   └── router/
│   │       └── index.tsx       # Route definitions
│   │
│   ├── shared/                 # Cross-feature utilities (3+ features)
│   │   ├── components/
│   │   │   ├── ui/             # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   ├── card.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── table.tsx
│   │   │   │   └── ...
│   │   │   ├── Layout.tsx      # Main layout with sidebar
│   │   │   ├── PageHeader.tsx  # Consistent page headers
│   │   │   ├── StatusBadge.tsx # Status indicators
│   │   │   └── LoadingSpinner.tsx
│   │   ├── hooks/
│   │   │   ├── useDebounce.ts
│   │   │   └── usePagination.ts
│   │   └── utils/
│   │       ├── formatters.ts   # Date, currency formatting
│   │       └── validators.ts   # Zod schemas
│   │
│   └── features/               # Feature slices (self-contained)
│       ├── dashboard/
│       │   ├── components/
│       │   │   ├── DashboardPage.tsx
│       │   │   ├── MetricsCard.tsx
│       │   │   └── RecentActivity.tsx
│       │   ├── hooks/
│       │   │   └── useDashboardMetrics.ts
│       │   └── index.ts        # Public exports
│       │
│       ├── customers/
│       │   ├── components/
│       │   │   ├── CustomerList.tsx
│       │   │   ├── CustomerDetail.tsx
│       │   │   ├── CustomerForm.tsx
│       │   │   └── CustomerSearch.tsx
│       │   ├── hooks/
│       │   │   ├── useCustomers.ts
│       │   │   ├── useCustomer.ts
│       │   │   └── useCreateCustomer.ts
│       │   ├── api/
│       │   │   └── customerApi.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   └── index.ts
│       │
│       ├── jobs/
│       │   ├── components/
│       │   │   ├── JobList.tsx
│       │   │   ├── JobDetail.tsx
│       │   │   ├── JobForm.tsx
│       │   │   └── JobStatusBadge.tsx
│       │   ├── hooks/
│       │   │   ├── useJobs.ts
│       │   │   ├── useJob.ts
│       │   │   └── useUpdateJobStatus.ts
│       │   ├── api/
│       │   │   └── jobApi.ts
│       │   └── index.ts
│       │
│       ├── staff/
│       │   ├── components/
│       │   │   ├── StaffList.tsx
│       │   │   ├── StaffDetail.tsx
│       │   │   └── StaffForm.tsx
│       │   ├── hooks/
│       │   │   └── useStaff.ts
│       │   └── index.ts
│       │
│       └── schedule/           # NEW for Phase 3
│           ├── components/
│           │   ├── SchedulePage.tsx
│           │   ├── CalendarView.tsx
│           │   ├── AppointmentForm.tsx
│           │   └── StaffAssignment.tsx
│           ├── hooks/
│           │   ├── useAppointments.ts
│           │   └── useCreateAppointment.ts
│           ├── api/
│           │   └── appointmentApi.ts
│           └── index.ts
│
├── index.html
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── package.json
└── README.md
```

### VSA Principles Applied

1. **Feature Isolation**: Each feature (customers, jobs, staff, schedule) is self-contained
2. **Core Foundation**: API client, providers, router exist before features
3. **Shared Components**: UI components used by 3+ features go in `shared/`
4. **Duplication Until Proven Shared**: Start with feature-specific code, extract when pattern emerges
5. **Clear Dependencies**: Features can import from `core/` and `shared/`, not from each other

---

## Backend Additions (Appointment Model)

### Database Schema

```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id),
    staff_id UUID NOT NULL REFERENCES staff(id),
    
    -- Scheduling
    scheduled_date DATE NOT NULL,
    time_window_start TIME NOT NULL,
    time_window_end TIME NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'scheduled',
    -- scheduled, confirmed, in_progress, completed, cancelled
    
    -- Execution
    arrived_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_appointments_job ON appointments(job_id);
CREATE INDEX idx_appointments_staff ON appointments(staff_id);
CREATE INDEX idx_appointments_date ON appointments(scheduled_date);
CREATE INDEX idx_appointments_status ON appointments(status);
```

### New API Endpoints (8 endpoints)

```
# Appointment Management
POST   /api/v1/appointments              # Create appointment
GET    /api/v1/appointments/{id}         # Get appointment by ID
PUT    /api/v1/appointments/{id}         # Update appointment
DELETE /api/v1/appointments/{id}         # Cancel appointment
GET    /api/v1/appointments              # List appointments (with filters)

# Schedule Views
GET    /api/v1/appointments/daily/{date}           # Get appointments for date
GET    /api/v1/appointments/staff/{staff_id}/daily/{date}  # Staff's daily schedule
GET    /api/v1/appointments/weekly                 # Weekly schedule overview
```

---

## Kiro Integration Strategy

### Current Kiro Usage (Already Excellent)

| Category | Count | Details |
|----------|-------|---------|
| **Steering Documents** | 14 | product.md, tech.md, structure.md, code-standards.md, etc. |
| **Custom Prompts** | 37+ | @implement-service, @implement-api, @quality-check, etc. |
| **Custom Agents** | 7 | service-layer, api-layer, repository-layer, test-specialist, etc. |
| **Hooks** | 6 | auto-lint, auto-typecheck, test-on-complete, etc. |
| **Specs** | 2 | customer-management, field-operations |

### New Kiro Items for Phase 3

#### 1. New Spec: Admin Dashboard

```
.kiro/specs/admin-dashboard/
├── requirements.md     # User stories and acceptance criteria
├── design.md           # Technical design with VSA patterns
└── tasks.md            # Implementation task breakdown
```

**Impact**: ⭐⭐⭐⭐⭐ (Shows spec-driven development for frontend)

#### 2. New Custom Agents (2 agents)

**Frontend Agent** (`.kiro/agents/frontend-agent.json`):
```json
{
  "name": "frontend-agent",
  "description": "Specialized agent for React + TypeScript frontend development",
  "prompt": "You are a frontend development specialist for the Grin's Irrigation Platform. You focus on:\n\n1. React 18 with TypeScript and functional components\n2. TanStack Query for server state management\n3. Tailwind CSS + shadcn/ui for styling\n4. Vertical Slice Architecture patterns\n5. Type-safe API integration\n\nAlways follow the patterns in frontend-patterns.md and ensure accessibility compliance.",
  "tools": ["read", "write", "shell"],
  "allowedTools": ["read", "write", "shell:npm", "shell:pnpm"],
  "resources": [
    "file://.kiro/steering/frontend-patterns.md",
    "file://.kiro/steering/vertical-slice-setup-guide-full.md",
    "file://frontend/README.md"
  ],
  "model": "claude-sonnet-4"
}
```

**Component Agent** (`.kiro/agents/component-agent.json`):
```json
{
  "name": "component-agent",
  "description": "Specialized agent for React component creation with shadcn/ui",
  "prompt": "You are a React component specialist. You focus on:\n\n1. Creating accessible, reusable components\n2. Using shadcn/ui as the foundation\n3. Proper TypeScript typing for props\n4. Component composition patterns\n5. Storybook documentation (if applicable)\n\nAlways ensure components are accessible and follow WCAG guidelines.",
  "tools": ["read", "write"],
  "allowedTools": ["read", "write"],
  "resources": [
    "file://frontend/src/shared/components/ui/"
  ],
  "model": "claude-sonnet-4"
}
```

**Impact**: ⭐⭐⭐⭐ (Shows workflow specialization for frontend)

#### 3. New Custom Prompts (3 prompts)

**@implement-feature-slice** (`.kiro/prompts/implement-feature-slice.md`):
```markdown
# Implement Feature Slice

Create a complete feature slice following VSA patterns.

## Required Information
- Feature name (e.g., "customers", "jobs", "schedule")
- API endpoints to integrate
- Key components needed

## Structure to Create
1. `features/{name}/components/` - React components
2. `features/{name}/hooks/` - TanStack Query hooks
3. `features/{name}/api/` - API integration
4. `features/{name}/types/` - TypeScript types
5. `features/{name}/index.ts` - Public exports

## Patterns to Follow
- Use TanStack Query for all API calls
- Use Zod for runtime validation
- Use shadcn/ui components as base
- Export only public API from index.ts
```

**@implement-api-client** (`.kiro/prompts/implement-api-client.md`):
```markdown
# Implement API Client

Create type-safe API client for a feature.

## Required Information
- Feature name
- Backend API endpoints
- Request/response types

## Implementation Pattern
1. Define TypeScript types matching backend schemas
2. Create API functions using Axios client
3. Add proper error handling
4. Export from feature's api/ directory
```

**@implement-tanstack-hook** (`.kiro/prompts/implement-tanstack-hook.md`):
```markdown
# Implement TanStack Query Hook

Create a TanStack Query hook for data fetching.

## Required Information
- Hook name (e.g., useCustomers, useCreateJob)
- API endpoint to call
- Query key structure
- Mutation or query?

## Implementation Pattern
- Use queryKey factory pattern
- Include proper TypeScript generics
- Handle loading, error, success states
- Add optimistic updates for mutations
```

**Impact**: ⭐⭐⭐⭐ (Accelerates frontend development)


#### 4. New Hooks (2 hooks)

**Frontend Lint Hook** (`.kiro/hooks/frontend-lint.json`):
```json
{
  "name": "Frontend Lint on Save",
  "version": "1.0.0",
  "description": "Run ESLint on frontend TypeScript files when edited",
  "when": {
    "type": "fileEdited",
    "patterns": ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run `cd frontend && npm run lint` and fix any errors in the edited file"
  }
}
```

**Frontend Typecheck Hook** (`.kiro/hooks/frontend-t


#### 4. New Hooks (2 hooks)

**Frontend Lint Hook** (`.kiro/hooks/frontend-lint.json`):
```json
{
  "name": "Frontend Lint on Save",
  "version": "1.0.0",
  "description": "Run ESLint on frontend TypeScript files when edited",
  "when": {
    "type": "fileEdited",
    "patterns": ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run `cd frontend && npm run lint` and fix any errors in the edited file"
  }
}
```

**Frontend Typecheck Hook** (`.kiro/hooks/frontend-typecheck.json`):
```json
{
  "name": "Frontend Typecheck on Save",
  "version": "1.0.0",
  "description": "Run TypeScript type checking on frontend files",
  "when": {
    "type": "fileEdited",
    "patterns": ["frontend/src/**/*.tsx", "frontend/src/**/*.ts"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Run `cd frontend && npm run typecheck` and fix any type errors"
  }
}
```

**Impact**: ⭐⭐⭐ (Automation for frontend quality)

#### 5. New Steering Documents (2 documents)

**Frontend Patterns** (`.kiro/steering/frontend-patterns.md`):
- React component patterns
- TanStack Query usage patterns
- Form handling with React Hook Form + Zod
- Error boundary patterns
- Accessibility guidelines

**Frontend Testing** (`.kiro/steering/frontend-testing.md`):
- Vitest setup and patterns
- React Testing Library usage
- Component testing strategies
- Integration testing with MSW

**Impact**: ⭐⭐⭐ (Consistent frontend development)

#### 6. MCP Servers (2 servers)

**Git MCP Server** - Already configured, use for:
- Automated commits during development
- Branch management for frontend feature branches
- Git history analysis

**Filesystem MCP Server** - Already configured, use for:
- Project structure analysis
- File search across frontend codebase
- Batch file operations

**Impact**: ⭐⭐⭐⭐⭐ (Enhanced development workflow)

#### 7. Subagent Strategy

**Parallel Execution Opportunities:**
```
Backend (Appointment API)     Frontend (Dashboard Shell)
        ↓                              ↓
        └──────────┬───────────────────┘
                   ↓
         Feature Integration
                   ↓
    ┌──────────────┼──────────────┐
    ↓              ↓              ↓
Customers UI   Jobs UI      Schedule UI
    ↓              ↓              ↓
    └──────────────┴──────────────┘
                   ↓
         Integration Testing
```

**Subagent Delegation Plan:**
- **Subagent A**: Backend appointment API (spec-task-execution)
- **Subagent B**: Frontend core setup (frontend-agent)
- **Main Agent**: Orchestration and integration

**Estimated Time Savings**: 30-40% with parallel execution

#### 8. Knowledge Management

**New Knowledge Bases:**
```bash
# Index frontend codebase
/knowledge add --name "frontend-src" --path ./frontend/src --index-type Best

# Index shadcn/ui components
/knowledge add --name "ui-components" --path ./frontend/src/shared/components/ui --index-type Fast
```

**Impact**: ⭐⭐⭐ (Semantic search across frontend code)

---

## Kiro Integration Summary

| Feature | New Items | Impact | Time |
|---------|-----------|--------|------|
| **Spec** | 1 new spec (admin-dashboard) | ⭐⭐⭐⭐⭐ | 2h |
| **Agents** | 2 new agents (frontend, component) | ⭐⭐⭐⭐ | 1h |
| **Prompts** | 3 new prompts | ⭐⭐⭐⭐ | 30m |
| **Hooks** | 3 new hooks (frontend-lint, frontend-typecheck, validate-ui) | ⭐⭐⭐⭐ | 45m |
| **Steering** | 2 new docs (frontend-patterns, frontend-testing) | ⭐⭐⭐ | 1h |
| **MCP** | Use existing git + filesystem | ⭐⭐⭐⭐⭐ | 0h |
| **Subagents** | Parallel delegation strategy | ⭐⭐⭐⭐ | 0h |
| **Knowledge** | 2 new knowledge bases | ⭐⭐⭐ | 30m |
| **Agent-Browser** | UI validation scripts + automation | ⭐⭐⭐⭐⭐ | 1h |

**Total Kiro Setup Time**: ~6.5 hours
**Expected Score Improvement**: +20-25 points on Kiro usage

---

## Implementation Phases

### Phase 1 - Kiro Setup + Backend Appointments [4-5 hours]

**Morning: Kiro Setup (2.5 hours)**
- [ ] Create admin-dashboard spec (requirements.md, design.md, tasks.md)
- [ ] Create frontend-agent and component-agent
- [ ] Create 3 new prompts
- [ ] Create 3 new hooks (including validate-ui-on-complete)
- [ ] Create 2 new steering documents
- [ ] Set up knowledge bases
- [ ] Install and configure agent-browser globally
- [ ] Create UI validation scripts (scripts/validate-ui.sh)

**Afternoon: Backend Appointments (2-3 hours)**
- [ ] Create appointments migration
- [ ] Create Appointment SQLAlchemy model
- [ ] Create Pydantic schemas
- [ ] Create AppointmentRepository
- [ ] Create AppointmentService with LoggerMixin
- [ ] Implement 8 appointment API endpoints
- [ ] Write tests (unit, functional, integration)

**Deliverables:**
- All Kiro items created
- Agent-browser configured and ready
- Appointment API complete (8 endpoints)
- Backend ready for frontend integration

---

### Phase 2 - Frontend Foundation [4-5 hours]

**Goal:** Set up React project with core infrastructure

- [ ] Initialize Vite + React + TypeScript project
- [ ] Configure Tailwind CSS
- [ ] Install and configure shadcn/ui
- [ ] Set up TanStack Query provider
- [ ] Create Axios API client with interceptors
- [ ] Set up React Router with route definitions
- [ ] Create Layout component with sidebar navigation
- [ ] Create shared UI components (Button, Card, Input, Table)
- [ ] Configure ESLint + Prettier
- [ ] Set up Vitest for testing
- [ ] Validate core layout with agent-browser

**Deliverables:**
- Frontend project scaffolded
- Core infrastructure complete
- Shared components ready
- Development environment working
- Agent-browser validation passing for layout

---

### Phase 3 - Customer Feature Slice [4-5 hours]

**Goal:** Complete customer management UI

- [ ] Create customer types matching backend schemas
- [ ] Create customerApi.ts with all API calls
- [ ] Create useCustomers hook (list with pagination)
- [ ] Create useCustomer hook (single customer)
- [ ] Create useCreateCustomer mutation
- [ ] Create useUpdateCustomer mutation
- [ ] Create CustomerList component with TanStack Table
- [ ] Create CustomerDetail component
- [ ] Create CustomerForm component with React Hook Form + Zod
- [ ] Create CustomerSearch component
- [ ] Write component tests

**Deliverables:**
- Customer feature slice complete
- Full CRUD operations working
- Search and filtering working
- Agent-browser CRUD validation passing

---

### Phase 4 - Jobs Feature Slice [4-5 hours]

**Goal:** Complete job management UI

- [ ] Create job types matching backend schemas
- [ ] Create jobApi.ts with all API calls
- [ ] Create useJobs hook with filtering
- [ ] Create useJob hook
- [ ] Create useUpdateJobStatus mutation
- [ ] Create JobList component with status filtering
- [ ] Create JobDetail component
- [ ] Create JobForm component
- [ ] Create JobStatusBadge component
- [ ] Write component tests
- [ ] Validate jobs UI with agent-browser

**Deliverables:**
- Jobs feature slice complete
- Status workflow visible
- Job-customer relationship working
- Agent-browser validation passing

---

### Phase 5 - Schedule Feature Slice [4-5 hours]

**Goal:** Complete scheduling UI with calendar

- [ ] Create appointment types
- [ ] Create appointmentApi.ts
- [ ] Create useAppointments hook
- [ ] Create useCreateAppointment mutation
- [ ] Install and configure FullCalendar
- [ ] Create SchedulePage component
- [ ] Create CalendarView component with FullCalendar
- [ ] Create AppointmentForm component
- [ ] Create StaffAssignment component
- [ ] Integrate with staff and jobs data
- [ ] Write component tests
- [ ] Validate calendar UI with agent-browser

**Deliverables:**
- Schedule feature slice complete
- Calendar view working
- Appointment creation working
- Agent-browser validation passing

---

### Phase 6 - Integration + Polish [4-5 hours]

**Goal:** Final integration, testing, and polish

- [ ] Dashboard page with metrics
- [ ] Staff feature slice (basic list/detail)
- [ ] Cross-feature navigation
- [ ] Error handling and loading states
- [ ] Responsive design verification
- [ ] Accessibility audit
- [ ] Full agent-browser E2E validation suite
- [ ] Screenshot documentation with agent-browser
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] DEVLOG update

**Deliverables:**
- All features integrated
- Dashboard complete
- Production-ready UI
- Complete agent-browser validation suite passing
- Screenshot documentation for demo

---

## Task Breakdown Summary

### Backend Tasks (8 tasks)
1. Appointments migration
2. Appointment SQLAlchemy model
3. Pydantic schemas
4. AppointmentRepository
5. AppointmentService
6. API endpoints (8 endpoints)
7. Unit tests
8. Integration tests

### Frontend Tasks (40+ tasks)

**Core Setup (10 tasks):**
1. Vite + React + TypeScript initialization
2. Tailwind CSS configuration
3. shadcn/ui installation
4. TanStack Query setup
5. Axios client configuration
6. React Router setup
7. Layout component
8. Shared UI components
9. ESLint + Prettier
10. Vitest setup

**Customer Feature (8 tasks):**
1. Types and API client
2. Query hooks (list, single)
3. Mutation hooks (create, update)
4. CustomerList component
5. CustomerDetail component
6. CustomerForm component
7. CustomerSearch component
8. Component tests

**Jobs Feature (8 tasks):**
1. Types and API client
2. Query hooks
3. Mutation hooks
4. JobList component
5. JobDetail component
6. JobForm component
7. JobStatusBadge component
8. Component tests

**Schedule Feature (8 tasks):**
1. Types and API client
2. Query hooks
3. Mutation hooks
4. FullCalendar setup
5. SchedulePage component
6. CalendarView component
7. AppointmentForm component
8. Component tests

**Integration (6 tasks):**
1. Dashboard page
2. Staff feature (basic)
3. Cross-feature navigation
4. Error handling
5. E2E testing
6. Documentation

**Agent-Browser Validation (6 tasks):**
1. Install and configure agent-browser
2. Create validate-ui.sh script
3. Create validate-customer-crud.sh script
4. Create validate-jobs.sh script
5. Create validate-schedule.sh script
6. Screenshot documentation generation

**Total: ~56 tasks**

---

## Success Criteria

### Feature Complete When:

**Backend (Appointments):**
- [ ] 8 API endpoints implemented and tested
- [ ] Appointment-job-staff relationships working
- [ ] 85%+ test coverage

**Frontend (Admin Dashboard):**
- [ ] Customer management UI complete
- [ ] Job management UI complete
- [ ] Schedule/calendar UI complete
- [ ] Dashboard with metrics
- [ ] Responsive design
- [ ] Accessibility compliant

**Agent-Browser Validation:**
- [ ] All UI validation scripts passing
- [ ] CRUD operations validated for each feature
- [ ] Screenshot documentation generated
- [ ] Accessibility tree shows proper structure

### Quality Standards:
- [ ] All backend tests passing
- [ ] All frontend tests passing
- [ ] ESLint passing (frontend)
- [ ] TypeScript strict mode passing
- [ ] Ruff + MyPy passing (backend)
- [ ] Agent-browser validation passing

---

## Definition of Done

**A feature is considered COMPLETE when ALL of the following are true:**

### Backend
1. All API endpoints implemented
2. All tests passing (`uv run pytest -v`)
3. Quality checks passing (`uv run ruff check src/ && uv run mypy src/`)

### Frontend
1. All components implemented
2. All tests passing (`cd frontend && npm test`)
3. TypeScript compiles without errors (`npm run typecheck`)
4. ESLint passes (`npm run lint`)
5. Feature works in browser (manual verification)
6. Agent-browser validation passing

### Verification Commands

**Backend:**
```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest -v
```

**Frontend:**
```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

**Agent-Browser UI Validation:**
```bash
# Ensure frontend is running first: cd frontend && npm run dev
bash scripts/validate-ui.sh
```

---

## API Summary (Phase 3)

### New Backend Endpoints (8 total)

```
# Appointment Management
POST   /api/v1/appointments              # Create appointment
GET    /api/v1/appointments/{id}         # Get appointment by ID
PUT    /api/v1/appointments/{id}         # Update appointment
DELETE /api/v1/appointments/{id}         # Cancel appointment
GET    /api/v1/appointments              # List appointments

# Schedule Views
GET    /api/v1/appointments/daily/{date}           # Daily schedule
GET    /api/v1/appointments/staff/{id}/daily/{date} # Staff daily
GET    /api/v1/appointments/weekly                 # Weekly overview
```

### Frontend Pages

| Page | Route | Features |
|------|-------|----------|
| Dashboard | `/` | Metrics, recent activity |
| Customers | `/customers` | List, search, CRUD |
| Customer Detail | `/customers/:id` | View, edit, properties, jobs |
| Jobs | `/jobs` | List, filter by status, CRUD |
| Job Detail | `/jobs/:id` | View, edit, status workflow |
| Schedule | `/schedule` | Calendar view, appointments |
| Staff | `/staff` | List, availability |

---

## Cumulative Progress

### After Phase 2:
- 42 API endpoints
- 764 tests
- Backend only (no UI)

### After Phase 3 (Target):
- 50 API endpoints (+8)
- 800+ tests (+40)
- Full Admin Dashboard UI
- Calendar/scheduling view

---

## Risk Mitigation

### Time Risks

**Risk:** Frontend setup takes longer than expected
**Mitigation:** Use Vite's scaffolding, shadcn/ui CLI for components

**Risk:** FullCalendar integration complex
**Mitigation:** Start with basic calendar, add features incrementally

### Technical Risks

**Risk:** API integration issues
**Mitigation:** Use TypeScript for type safety, test API calls early

**Risk:** State management complexity
**Mitigation:** TanStack Query handles most complexity, avoid Redux

### Quality Risks

**Risk:** Accessibility issues
**Mitigation:** Use shadcn/ui (accessible by default), audit with axe

---

## Agent-Browser Integration for UI Validation

### Overview

We will use `agent-browser` for automated UI validation during development. This headless browser automation CLI is optimized for AI agents and provides a powerful way to validate that our React frontend works correctly as we build it.

### Installation

```bash
# Install globally
npm install -g agent-browser

# Download Chromium browser
agent-browser install
```

### Why Agent-Browser for Phase 3?

| Benefit | Description |
|---------|-------------|
| **AI-Optimized** | Snapshot + ref workflow is perfect for Kiro agents to validate UI |
| **Fast Feedback** | Validate UI changes immediately without manual testing |
| **Accessibility Tree** | Snapshots show accessibility structure, catching a11y issues early |
| **Deterministic** | Refs provide exact element targeting, no flaky selectors |
| **Headless** | Runs in CI/CD and during development without browser windows |

### Core Workflow for UI Validation

```bash
# 1. Start the frontend dev server (in separate terminal)
cd frontend && npm run dev

# 2. Open the page
agent-browser open http://localhost:5173

# 3. Get accessibility snapshot with interactive elements
agent-browser snapshot -i

# 4. Validate specific elements exist
agent-browser get text @e1              # Check heading text
agent-browser is visible @e2            # Check button visibility
agent-browser get count "[data-testid='customer-row']"  # Count table rows

# 5. Test interactions
agent-browser click @e3                 # Click a button
agent-browser fill @e4 "John Doe"       # Fill a form field
agent-browser snapshot -i               # Re-snapshot after interaction

# 6. Take screenshot for visual verification
agent-browser screenshot customer-list.png

# 7. Close browser
agent-browser close
```

### UI Validation Test Scenarios

#### Customer Feature Validation

```bash
# Test: Customer List Page
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
agent-browser snapshot -i --json

# Verify page structure
agent-browser get text "h1"                    # Should be "Customers"
agent-browser is visible "[data-testid='customer-table']"
agent-browser is visible "[data-testid='add-customer-btn']"

# Test: Add Customer Flow
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "Viktor"
agent-browser fill "[name='lastName']" "Grin"
agent-browser fill "[name='phone']" "6125551234"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer created"

# Verify customer appears in list
agent-browser snapshot -i
agent-browser get text "[data-testid='customer-row']:first-child"
```

#### Jobs Feature Validation

```bash
# Test: Jobs List with Status Filtering
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Test status filter
agent-browser click "[data-testid='status-filter']"
agent-browser click "text=Ready to Schedule"
agent-browser wait --load networkidle
agent-browser snapshot -i

# Verify filtered results
agent-browser get count "[data-testid='job-row']"
```

#### Schedule Feature Validation

```bash
# Test: Calendar View
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Verify calendar renders
agent-browser is visible ".fc-daygrid"          # FullCalendar grid
agent-browser is visible "[data-testid='create-appointment-btn']"

# Test: Create Appointment
agent-browser click "[data-testid='create-appointment-btn']"
agent-browser wait "[data-testid='appointment-form']"
agent-browser snapshot -i
```

### Integration with Development Workflow

#### Per-Feature Validation Script

Create `scripts/validate-ui.sh`:

```bash
#!/bin/bash
# UI Validation Script for Phase 3 Frontend

set -e

echo "🔍 Starting UI Validation..."

# Ensure frontend is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ Frontend not running. Start with: cd frontend && npm run dev"
    exit 1
fi

echo "✅ Frontend is running"

# Dashboard validation
echo "📊 Validating Dashboard..."
agent-browser open http://localhost:5173
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='metrics-card']" && echo "  ✓ Metrics card visible"
agent-browser is visible "[data-testid='recent-activity']" && echo "  ✓ Recent activity visible"

# Customers validation
echo "👥 Validating Customers..."
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='customer-table']" && echo "  ✓ Customer table visible"
agent-browser is visible "[data-testid='add-customer-btn']" && echo "  ✓ Add button visible"

# Jobs validation
echo "📋 Validating Jobs..."
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='job-table']" && echo "  ✓ Job table visible"
agent-browser is visible "[data-testid='status-filter']" && echo "  ✓ Status filter visible"

# Schedule validation
echo "📅 Validating Schedule..."
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser is visible ".fc-daygrid" && echo "  ✓ Calendar visible"

# Cleanup
agent-browser close

echo ""
echo "✅ UI Validation Complete!"
```

#### Kiro Hook for UI Validation

Create `.kiro/hooks/validate-ui-on-complete.json`:

```json
{
  "name": "Validate UI on Agent Stop",
  "version": "1.0.0",
  "description": "Run UI validation after frontend changes",
  "when": {
    "type": "agentStop"
  },
  "then": {
    "type": "runCommand",
    "command": "bash scripts/validate-ui.sh"
  }
}
```

### Snapshot-Based Testing Pattern

The most powerful pattern for AI-driven UI validation:

```bash
# 1. Capture baseline snapshot
agent-browser open http://localhost:5173/customers
agent-browser snapshot -i > snapshots/customers-baseline.txt

# 2. After making changes, compare
agent-browser open http://localhost:5173/customers
agent-browser snapshot -i > snapshots/customers-current.txt

# 3. Diff to see what changed
diff snapshots/customers-baseline.txt snapshots/customers-current.txt
```

### Test Data IDs Convention

For reliable element targeting, use consistent `data-testid` attributes:

| Component | Test ID Pattern | Example |
|-----------|-----------------|---------|
| Page containers | `{feature}-page` | `customers-page` |
| Tables | `{feature}-table` | `customer-table` |
| Table rows | `{feature}-row` | `customer-row` |
| Forms | `{feature}-form` | `customer-form` |
| Buttons | `{action}-{feature}-btn` | `add-customer-btn` |
| Inputs | Form field `name` attribute | `name="firstName"` |
| Status badges | `status-{status}` | `status-scheduled` |
| Cards | `{feature}-card` | `metrics-card` |

### Headed Mode for Debugging

When validation fails, use headed mode to see what's happening:

```bash
# Open browser visibly for debugging
agent-browser open http://localhost:5173/customers --headed

# Take screenshot of current state
agent-browser screenshot debug-screenshot.png

# Get full accessibility tree for analysis
agent-browser snapshot > debug-snapshot.txt
```

### CI/CD Integration (Future)

For automated testing in CI:

```yaml
# .github/workflows/ui-tests.yml
name: UI Tests

on: [push, pull_request]

jobs:
  ui-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install agent-browser
        run: |
          npm install -g agent-browser
          agent-browser install --with-deps
      
      - name: Install frontend dependencies
        run: cd frontend && npm ci
      
      - name: Start frontend
        run: cd frontend && npm run dev &
        
      - name: Wait for frontend
        run: sleep 10
      
      - name: Run UI validation
        run: bash scripts/validate-ui.sh
```

### Implementation Integration

| Phase | Agent-Browser Usage |
|-------|---------------------|
| Phase 2 | Validate core layout, navigation, shared components |
| Phase 3 | Validate customer list, detail, form, search |
| Phase 4 | Validate job list, detail, status workflow |
| Phase 5 | Validate calendar view, appointment creation |
| Phase 6 | Full integration validation, screenshot documentation |

### Example: Complete Customer CRUD Validation

```bash
#!/bin/bash
# scripts/validate-customer-crud.sh

echo "🧪 Testing Customer CRUD Operations"

# Setup
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# CREATE
echo "📝 Testing Create..."
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "Test"
agent-browser fill "[name='lastName']" "Customer"
agent-browser fill "[name='phone']" "6125559999"
agent-browser fill "[name='email']" "test@example.com"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer created"
echo "  ✓ Create successful"

# READ
echo "📖 Testing Read..."
agent-browser click "[data-testid='customer-row']:first-child"
agent-browser wait "[data-testid='customer-detail']"
agent-browser get text "[data-testid='customer-name']" | grep -q "Test Customer"
echo "  ✓ Read successful"

# UPDATE
echo "✏️ Testing Update..."
agent-browser click "[data-testid='edit-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "Updated"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer updated"
echo "  ✓ Update successful"

# DELETE
echo "🗑️ Testing Delete..."
agent-browser click "[data-testid='delete-btn']"
agent-browser wait "[data-testid='confirm-dialog']"
agent-browser click "[data-testid='confirm-delete-btn']"
agent-browser wait --text "Customer deleted"
echo "  ✓ Delete successful"

agent-browser close
echo "✅ Customer CRUD validation complete!"
```

### Benefits for Hackathon Scoring

| Kiro Feature | Agent-Browser Integration |
|--------------|---------------------------|
| **Automation** | Hook triggers UI validation automatically |
| **Quality** | Catches UI bugs before manual testing |
| **Documentation** | Screenshots provide visual proof of working features |
| **AI-Friendly** | Snapshot workflow perfect for agent-driven testing |
| **Accessibility** | Accessibility tree reveals a11y issues early |

---

## MANDATORY: UI Validation After Every Feature

### Core Principle

**⚠️ NO FEATURE IS COMPLETE UNTIL IT HAS BEEN VALIDATED THROUGH USER JOURNEY TESTING**

After implementing each feature, we MUST validate it by simulating exactly what a user would do to use that feature. This ensures:
1. The feature actually works end-to-end
2. Bugs are caught immediately, not days later
3. We never build on top of broken functionality
4. Each feature is demonstrably working before moving on

### The Validation Gate Rule

```
┌─────────────────────────────────────────────────────────────────┐
│                    FEATURE IMPLEMENTATION                        │
│                           ↓                                      │
│                    Write Code + Tests                            │
│                           ↓                                      │
│                    Quality Checks Pass                           │
│                           ↓                                      │
│              ┌───────────────────────────┐                      │
│              │  🚫 VALIDATION GATE 🚫    │                      │
│              │                           │                      │
│              │  Run User Journey Test    │                      │
│              │  with agent-browser       │                      │
│              │                           │                      │
│              │  ❌ FAIL → Fix & Retry    │                      │
│              │  ✅ PASS → Continue       │                      │
│              └───────────────────────────┘                      │
│                           ↓                                      │
│                    FEATURE COMPLETE                              │
│                           ↓                                      │
│                    Next Feature                                  │
└─────────────────────────────────────────────────────────────────┘
```

### User Journey Tests by Feature

Each feature has a specific user journey that MUST pass before the feature is considered complete.

#### Phase 2: Core Layout Validation

**User Journey: "Viktor opens the dashboard for the first time"**

```bash
#!/bin/bash
# scripts/validate-layout.sh

echo "🧪 Core Layout User Journey Test"
echo "========================================="
echo "Scenario: Viktor opens the dashboard for the first time"
echo ""

# Start fresh
agent-browser open http://localhost:5173
agent-browser wait --load networkidle

# Step 1: Dashboard loads
echo "Step 1: Dashboard loads correctly"
agent-browser is visible "[data-testid='main-layout']" && echo "  ✓ Main layout visible"
agent-browser is visible "[data-testid='sidebar']" && echo "  ✓ Sidebar visible"
agent-browser is visible "[data-testid='header']" && echo "  ✓ Header visible"

# Step 2: Navigation works
echo "Step 2: Navigation links work"
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --url "**/customers"
agent-browser get url | grep -q "customers" && echo "  ✓ Customers navigation works"

agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --url "**/jobs"
agent-browser get url | grep -q "jobs" && echo "  ✓ Jobs navigation works"

agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --url "**/schedule"
agent-browser get url | grep -q "schedule" && echo "  ✓ Schedule navigation works"

agent-browser click "[data-testid='nav-dashboard']"
agent-browser wait --url "**/"
echo "  ✓ Dashboard navigation works"

# Step 3: Responsive sidebar
echo "Step 3: Sidebar is functional"
agent-browser is visible "[data-testid='sidebar-toggle']" && echo "  ✓ Sidebar toggle visible"

agent-browser close
echo ""
echo "✅ Layout Validation PASSED!"
```

#### Phase 3: Customer Feature Validation

**User Journey: "Viktor adds a new customer and views their details"**

```bash
#!/bin/bash
# scripts/validate-customers.sh

echo "🧪 Customer Feature User Journey Test"
echo "=============================================="
echo "Scenario: Viktor adds a new customer and views their details"
echo ""

agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Step 1: View customer list
echo "Step 1: Viktor sees the customer list"
agent-browser is visible "[data-testid='customer-table']" && echo "  ✓ Customer table visible"
agent-browser is visible "[data-testid='add-customer-btn']" && echo "  ✓ Add button visible"
agent-browser is visible "[data-testid='customer-search']" && echo "  ✓ Search box visible"

# Step 2: Add new customer
echo "Step 2: Viktor clicks 'Add Customer' and fills the form"
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser is visible "[data-testid='customer-form']" && echo "  ✓ Customer form opened"

agent-browser fill "[name='firstName']" "John"
agent-browser fill "[name='lastName']" "Smith"
agent-browser fill "[name='phone']" "6125551234"
agent-browser fill "[name='email']" "john.smith@example.com"
echo "  ✓ Form filled out"

# Step 3: Submit and verify
echo "Step 3: Viktor submits the form"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer created" --timeout 5000
echo "  ✓ Success message shown"

# Step 4: View customer in list
echo "Step 4: Viktor sees the new customer in the list"
agent-browser wait "[data-testid='customer-row']"
agent-browser get text "[data-testid='customer-table']" | grep -q "John Smith" && echo "  ✓ Customer appears in list"

# Step 5: View customer details
echo "Step 5: Viktor clicks on the customer to see details"
agent-browser click "[data-testid='customer-row']:first-child"
agent-browser wait "[data-testid='customer-detail']"
agent-browser get text "[data-testid='customer-name']" | grep -q "John Smith" && echo "  ✓ Customer detail page shows correct name"
agent-browser get text "[data-testid='customer-phone']" | grep -q "6125551234" && echo "  ✓ Phone number displayed"

# Step 6: Edit customer
echo "Step 6: Viktor edits the customer"
agent-browser click "[data-testid='edit-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "Jonathan"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer updated"
echo "  ✓ Customer updated successfully"

# Step 7: Search for customer
echo "Step 7: Viktor searches for the customer"
agent-browser click "[data-testid='nav-customers']"
agent-browser wait "[data-testid='customer-search']"
agent-browser fill "[data-testid='customer-search']" "Jonathan"
agent-browser wait --load networkidle
agent-browser get count "[data-testid='customer-row']" | grep -q "1" && echo "  ✓ Search returns correct result"

agent-browser close
echo ""
echo "✅ Customer Validation PASSED!"
```

#### Phase 4: Jobs Feature Validation

**User Journey: "Viktor creates a job for a customer and updates its status"**

```bash
#!/bin/bash
# scripts/validate-jobs.sh

echo "🧪 Jobs Feature User Journey Test"
echo "=========================================="
echo "Scenario: Viktor creates a job for a customer and updates its status"
echo ""

agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Step 1: View jobs list
echo "Step 1: Viktor sees the jobs list"
agent-browser is visible "[data-testid='job-table']" && echo "  ✓ Job table visible"
agent-browser is visible "[data-testid='add-job-btn']" && echo "  ✓ Add job button visible"
agent-browser is visible "[data-testid='status-filter']" && echo "  ✓ Status filter visible"

# Step 2: Create new job
echo "Step 2: Viktor creates a new job"
agent-browser click "[data-testid='add-job-btn']"
agent-browser wait "[data-testid='job-form']"

# Select customer (assuming dropdown)
agent-browser click "[data-testid='customer-select']"
agent-browser click "[data-testid='customer-option']:first-child"
echo "  ✓ Customer selected"

# Select service type
agent-browser click "[data-testid='service-select']"
agent-browser click "[data-testid='service-option']:first-child"
echo "  ✓ Service selected"

agent-browser fill "[name='description']" "Spring startup - 6 zones"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Job created"
echo "  ✓ Job created successfully"

# Step 3: View job details
echo "Step 3: Viktor views the job details"
agent-browser click "[data-testid='job-row']:first-child"
agent-browser wait "[data-testid='job-detail']"
agent-browser is visible "[data-testid='job-status-badge']" && echo "  ✓ Status badge visible"
agent-browser get text "[data-testid='job-status-badge']" | grep -q "requested" && echo "  ✓ Initial status is 'requested'"

# Step 4: Update job status
echo "Step 4: Viktor updates the job status to 'approved'"
agent-browser click "[data-testid='status-dropdown']"
agent-browser click "[data-testid='status-approved']"
agent-browser wait --text "Status updated"
agent-browser get text "[data-testid='job-status-badge']" | grep -q "approved" && echo "  ✓ Status updated to 'approved'"

# Step 5: Filter jobs by status
echo "Step 5: Viktor filters jobs by status"
agent-browser click "[data-testid='nav-jobs']"
agent-browser wait "[data-testid='status-filter']"
agent-browser click "[data-testid='status-filter']"
agent-browser click "[data-testid='filter-approved']"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='job-row']" && echo "  ✓ Filtered results shown"

agent-browser close
echo ""
echo "✅ Jobs Validation PASSED!"
```

#### Phase 5: Schedule Feature Validation

**User Journey: "Viktor schedules an appointment for a job"**

```bash
#!/bin/bash
# scripts/validate-schedule.sh

echo "🧪 Schedule Feature User Journey Test"
echo "=============================================="
echo "Scenario: Viktor schedules an appointment for a job"
echo ""

agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Step 1: View calendar
echo "Step 1: Viktor sees the calendar"
agent-browser is visible ".fc-daygrid" && echo "  ✓ Calendar grid visible"
agent-browser is visible "[data-testid='create-appointment-btn']" && echo "  ✓ Create appointment button visible"

# Step 2: Create appointment
echo "Step 2: Viktor creates a new appointment"
agent-browser click "[data-testid='create-appointment-btn']"
agent-browser wait "[data-testid='appointment-form']"

# Select job
agent-browser click "[data-testid='job-select']"
agent-browser click "[data-testid='job-option']:first-child"
echo "  ✓ Job selected"

# Select staff
agent-browser click "[data-testid='staff-select']"
agent-browser click "[data-testid='staff-option']:first-child"
echo "  ✓ Staff assigned"

# Select date (click on calendar)
agent-browser click ".fc-daygrid-day:not(.fc-day-past):first-child"
echo "  ✓ Date selected"

# Set time window
agent-browser fill "[name='timeWindowStart']" "09:00"
agent-browser fill "[name='timeWindowEnd']" "11:00"
echo "  ✓ Time window set"

agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Appointment created"
echo "  ✓ Appointment created successfully"

# Step 3: View appointment on calendar
echo "Step 3: Viktor sees the appointment on the calendar"
agent-browser is visible ".fc-event" && echo "  ✓ Appointment event visible on calendar"

# Step 4: Click appointment to view details
echo "Step 4: Viktor clicks the appointment to see details"
agent-browser click ".fc-event:first-child"
agent-browser wait "[data-testid='appointment-detail']"
agent-browser is visible "[data-testid='appointment-customer']" && echo "  ✓ Customer info shown"
agent-browser is visible "[data-testid='appointment-staff']" && echo "  ✓ Staff assignment shown"
agent-browser is visible "[data-testid='appointment-time']" && echo "  ✓ Time window shown"

# Step 5: View staff's daily schedule
echo "Step 5: Viktor views a staff member's daily schedule"
agent-browser click "[data-testid='staff-schedule-link']"
agent-browser wait "[data-testid='staff-daily-view']"
agent-browser is visible "[data-testid='staff-appointment']" && echo "  ✓ Staff's appointments visible"

agent-browser close
echo ""
echo "✅ Schedule Validation PASSED!"
```

#### Phase 6: Full Integration Validation

**User Journey: "Viktor completes a full workflow from customer to scheduled appointment"**

```bash
#!/bin/bash
# scripts/validate-integration.sh

echo "🧪 Full Integration User Journey Test"
echo "=============================================="
echo "Scenario: Viktor completes a full workflow from customer to scheduled appointment"
echo ""

# This test validates the ENTIRE user journey across all features

agent-browser open http://localhost:5173
agent-browser wait --load networkidle

# PHASE 1: Dashboard Overview
echo "PHASE 1: Dashboard Overview"
agent-browser is visible "[data-testid='metrics-card']" && echo "  ✓ Metrics visible"
agent-browser is visible "[data-testid='recent-activity']" && echo "  ✓ Recent activity visible"

# PHASE 2: Create Customer
echo "PHASE 2: Create Customer"
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --load networkidle
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"
agent-browser fill "[name='firstName']" "Integration"
agent-browser fill "[name='lastName']" "Test"
agent-browser fill "[name='phone']" "6125550001"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Customer created"
echo "  ✓ Customer created"

# PHASE 3: Create Job for Customer
echo "PHASE 3: Create Job for Customer"
agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --load networkidle
agent-browser click "[data-testid='add-job-btn']"
agent-browser wait "[data-testid='job-form']"
agent-browser click "[data-testid='customer-select']"
# Select the customer we just created
agent-browser fill "[data-testid='customer-search-input']" "Integration Test"
agent-browser click "[data-testid='customer-option']:first-child"
agent-browser click "[data-testid='service-select']"
agent-browser click "[data-testid='service-option']:first-child"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Job created"
echo "  ✓ Job created for customer"

# PHASE 4: Approve Job
echo "PHASE 4: Approve Job"
agent-browser click "[data-testid='job-row']:first-child"
agent-browser wait "[data-testid='job-detail']"
agent-browser click "[data-testid='status-dropdown']"
agent-browser click "[data-testid='status-approved']"
agent-browser wait --text "Status updated"
echo "  ✓ Job approved"

# PHASE 5: Schedule Appointment
echo "PHASE 5: Schedule Appointment"
agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --load networkidle
agent-browser click "[data-testid='create-appointment-btn']"
agent-browser wait "[data-testid='appointment-form']"
agent-browser click "[data-testid='job-select']"
agent-browser click "[data-testid='job-option']:first-child"
agent-browser click "[data-testid='staff-select']"
agent-browser click "[data-testid='staff-option']:first-child"
agent-browser click ".fc-daygrid-day:not(.fc-day-past):first-child"
agent-browser fill "[name='timeWindowStart']" "10:00"
agent-browser fill "[name='timeWindowEnd']" "12:00"
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Appointment created"
echo "  ✓ Appointment scheduled"

# PHASE 6: Verify Everything Connected
echo "PHASE 6: Verify Everything Connected"
agent-browser click ".fc-event:first-child"
agent-browser wait "[data-testid='appointment-detail']"
agent-browser get text "[data-testid='appointment-customer']" | grep -q "Integration Test" && echo "  ✓ Appointment shows correct customer"

# Navigate to customer and verify job
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --load networkidle
agent-browser fill "[data-testid='customer-search']" "Integration Test"
agent-browser wait --load networkidle
agent-browser click "[data-testid='customer-row']:first-child"
agent-browser wait "[data-testid='customer-detail']"
agent-browser is visible "[data-testid='customer-jobs']" && echo "  ✓ Customer shows linked job"

# Take final screenshot
agent-browser screenshot screenshots/integration-test-complete.png
echo "  ✓ Screenshot saved"

agent-browser close
echo ""
echo "✅ Full Integration Validation PASSED!"
echo ""
echo "🎉 ALL USER JOURNEY TESTS COMPLETE!"
```

### Validation Checklist Template

Use this checklist after completing each feature:

```markdown
## Feature Validation Checklist: [Feature Name]

### Pre-Validation
- [ ] All code written
- [ ] Unit tests passing
- [ ] TypeScript compiles
- [ ] ESLint passes

### User Journey Validation
- [ ] User journey script created: `scripts/validate-[feature].sh`
- [ ] Script runs without errors
- [ ] All steps pass
- [ ] Screenshot captured

### Post-Validation
- [ ] Any bugs found have been fixed
- [ ] Re-run validation after fixes
- [ ] Final validation PASSED

### Sign-off
- Date: ____
- Validation Script: ____
- Result: PASS / FAIL
```

### Enforcement: No Moving Forward Without Validation

**This is a HARD RULE:**

1. **After Layout**: Run `validate-layout.sh` - MUST PASS before Customers
2. **After Customers**: Run `validate-customers.sh` - MUST PASS before Jobs
3. **After Jobs**: Run `validate-jobs.sh` - MUST PASS before Schedule
4. **After Schedule**: Run `validate-schedule.sh` - MUST PASS before Integration
5. **Integration**: Run `validate-integration.sh` - MUST PASS for Phase 3 completion

**If validation fails:**
1. STOP - Do not proceed to next feature
2. Debug using headed mode: `agent-browser open http://localhost:5173 --headed`
3. Fix the issue
4. Re-run validation
5. Only proceed when validation PASSES

### Quick Validation Commands

```bash
# Run specific validation
bash scripts/validate-layout.sh
bash scripts/validate-customers.sh
bash scripts/validate-jobs.sh
bash scripts/validate-schedule.sh
bash scripts/validate-integration.sh

# Run all validations
bash scripts/validate-all.sh
```

### Master Validation Script

Create `scripts/validate-all.sh`:

```bash
#!/bin/bash
# Master validation script - runs all user journey tests

set -e  # Exit on first failure

echo "🚀 Running ALL User Journey Validations"
echo "========================================"
echo ""

# Check frontend is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ Frontend not running!"
    echo "Start with: cd frontend && npm run dev"
    exit 1
fi

echo "✅ Frontend is running"
echo ""

# Run each validation in order
bash scripts/validate-day16-layout.sh
echo ""

bash scripts/validate-day17-customers.sh
echo ""

bash scripts/validate-day18-jobs.sh
echo ""

bash scripts/validate-day19-schedule.sh
echo ""

bash scripts/validate-day20-integration.sh
echo ""

echo "========================================"
echo "🎉 ALL VALIDATIONS PASSED!"
echo "========================================"
```

---

## Notes

- Follow VSA patterns from steering document
- Use TanStack Query for ALL API calls (no manual fetch)
- Prioritize working features over polish
- Test critical paths first
- Update DEVLOG after each major milestone
- Use Kiro agents for specialized work

---

## Next Steps

1. **Review this plan** with user
2. **Create admin-dashboard spec** in `.kiro/specs/`
3. **Create new Kiro agents and prompts**
4. **Begin implementation**

---

## Appendix: Component Library (shadcn/ui)

### Components to Install

```bash
# Core components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add card
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add select
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add form
npx shadcn-ui@latest add calendar
npx shadcn-ui@latest add popover
npx shadcn-ui@latest add separator
npx shadcn-ui@latest add skeleton
npx shadcn-ui@latest add tabs
```

### Additional Dependencies

```bash
# TanStack
npm install @tanstack/react-query @tanstack/react-table

# Forms
npm install react-hook-form @hookform/resolvers zod

# Calendar
npm install @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid @fullcalendar/interaction

# Routing
npm install react-router-dom

# HTTP
npm install axios

# Date handling
npm install date-fns

# Icons
npm install lucide-react
```
