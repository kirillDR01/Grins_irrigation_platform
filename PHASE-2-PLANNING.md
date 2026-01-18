# Phase 2 Implementation Planning

**Date:** January 17, 2026  
**Status:** Planning Complete - Ready for Implementation  
**Timeline:** Days 8-14 (Jan 17-23)  
**Goal:** Implement Job Request Management, Service Catalog, and Staff Management

---

## Phase 1 Completion Summary

### What Was Accomplished ✅

**Customer Management Feature - COMPLETE**
- 12 tasks completed across all layers
- 482 tests passing (unit, integration, property-based)
- 95% code coverage
- 22 functional API tests passing
- All quality checks passing (Ruff, MyPy)

**Infrastructure Established:**
- FastAPI application with async support
- PostgreSQL database with Alembic migrations
- Layered architecture (API → Service → Repository → Database)
- Structured logging with LoggerMixin
- Comprehensive testing patterns (unit, functional, integration, PBT)

**API Endpoints Delivered (Phase 1):**
```
POST   /api/v1/customers              # Create customer
GET    /api/v1/customers/{id}         # Get customer by ID
PUT    /api/v1/customers/{id}         # Update customer
DELETE /api/v1/customers/{id}         # Soft delete customer
GET    /api/v1/customers              # List customers (with filters)
PUT    /api/v1/customers/{id}/flags   # Update customer flags
PUT    /api/v1/customers/{id}/preferences  # Update communication preferences
GET    /api/v1/customers/{id}/service-history  # Get service history
GET    /api/v1/customers/lookup/phone/{phone}  # Lookup by phone
GET    /api/v1/customers/lookup/email/{email}  # Lookup by email
POST   /api/v1/properties             # Create property
GET    /api/v1/properties/{id}        # Get property by ID
PUT    /api/v1/properties/{id}        # Update property
DELETE /api/v1/properties/{id}        # Delete property
GET    /api/v1/customers/{id}/properties  # List customer properties
PUT    /api/v1/properties/{id}/primary    # Set primary property
```

---

## Phase 2 Overview

### Features to Implement

| Feature | Priority | Complexity | Dependencies |
|---------|----------|------------|--------------|
| **Job Request Management** | P0 | High | Customer, Property |
| **Service Catalog** | P0 | Medium | None |
| **Staff Management** | P1 | Medium | None |

### Why These Features?

1. **Job Request Management** - Core business value
   - Replaces Viktor's spreadsheet tracking
   - Enables job status workflow (Requested → Completed)
   - Links customers to work requests
   - Foundation for scheduling (Phase 3)

2. **Service Catalog** - Pricing and service definitions
   - Zone-based pricing for seasonal services
   - Flat-rate pricing for repairs
   - Equipment and staffing requirements
   - Lien eligibility tracking

3. **Staff Management** - Required for job assignment
   - Staff profiles with roles and skills
   - Availability tracking
   - Hourly rates for cost calculation
   - Foundation for scheduling (Phase 3)

---

## Feature 1: Job Request Management

### Business Context

From Viktor's process (Grins_Irrigation_Backend_System.md):

**Job Categories:**
- **Ready to Schedule**: Seasonal work, small repairs, approved estimates, partner deals
- **Requires Estimate**: New installs, complex repairs, diagnostics, new commercial

**Job Status Workflow:**
```
Requested → Approved → Scheduled → In-Progress → Completed → Closed
                ↓
            Cancelled
```

**Job Types:**
- Seasonal: Spring startup, summer tune-up, fall winterization
- Repair: Small repairs ($50/head), major repairs (custom)
- Installation: New systems ($700/zone for partners)
- Diagnostic: $100 first hour + hourly
- Landscaping: Custom estimates

### Database Schema

```sql
-- Service offerings catalog
CREATE TABLE service_offerings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- seasonal, repair, installation, diagnostic, landscaping
    description TEXT,
    
    -- Pricing
    base_price DECIMAL(10, 2),
    price_per_zone DECIMAL(10, 2),
    pricing_model VARCHAR(50) NOT NULL,  -- flat, zone_based, hourly, custom
    
    -- Time estimates
    estimated_duration_minutes INTEGER,
    duration_per_zone_minutes INTEGER,
    
    -- Requirements
    staffing_required INTEGER DEFAULT 1,
    equipment_required JSONB,  -- ["compressor", "pipe_puller"]
    
    -- Lien eligibility
    lien_eligible BOOLEAN DEFAULT FALSE,
    requires_prepay BOOLEAN DEFAULT FALSE,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    property_id UUID REFERENCES properties(id),
    service_offering_id UUID REFERENCES service_offerings(id),
    
    -- Job details
    job_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- ready_to_schedule, requires_estimate
    status VARCHAR(50) NOT NULL DEFAULT 'requested',
    description TEXT,
    
    -- Scheduling
    estimated_duration_minutes INTEGER,
    priority_level INTEGER DEFAULT 0,  -- 0=normal, 1=high, 2=urgent
    weather_sensitive BOOLEAN DEFAULT FALSE,
    
    -- Requirements
    staffing_required INTEGER DEFAULT 1,
    equipment_required JSONB,
    materials_required JSONB,
    
    -- Pricing
    quoted_amount DECIMAL(10, 2),
    final_amount DECIMAL(10, 2),
    
    -- Source tracking
    source VARCHAR(50),  -- website, google, referral, phone, partner
    source_details JSONB,
    
    -- Timestamps
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_jobs_customer ON jobs(customer_id);
CREATE INDEX idx_jobs_property ON jobs(property_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
CREATE INDEX idx_jobs_requested_at ON jobs(requested_at);
```

### API Endpoints

```
# Job CRUD
POST   /api/v1/jobs                    # Create job request
GET    /api/v1/jobs/{id}               # Get job by ID
PUT    /api/v1/jobs/{id}               # Update job
DELETE /api/v1/jobs/{id}               # Delete job (soft delete)
GET    /api/v1/jobs                    # List jobs (with filters)

# Job Status Management
PUT    /api/v1/jobs/{id}/status        # Update job status
GET    /api/v1/jobs/{id}/history       # Get job status history

# Job Categorization
GET    /api/v1/jobs/ready-to-schedule  # Jobs ready to schedule
GET    /api/v1/jobs/needs-estimate     # Jobs needing estimates
GET    /api/v1/jobs/by-status/{status} # Jobs by status

# Customer Jobs
GET    /api/v1/customers/{id}/jobs     # Get customer's jobs

# Service Catalog
GET    /api/v1/services                # List all services
GET    /api/v1/services/{id}           # Get service details
GET    /api/v1/services/category/{cat} # Services by category
POST   /api/v1/services                # Create service (admin)
PUT    /api/v1/services/{id}           # Update service (admin)
```

### Business Logic

**Auto-Categorization Rules:**
```python
def categorize_job(job_type: str, customer: Customer) -> str:
    """Determine if job is ready to schedule or needs estimate."""
    
    # Seasonal work is always ready to schedule
    if job_type in ["spring_startup", "summer_tuneup", "winterization"]:
        return "ready_to_schedule"
    
    # Small repairs with known pricing
    if job_type == "small_repair":
        return "ready_to_schedule"
    
    # Approved estimates
    if job.has_approved_estimate:
        return "ready_to_schedule"
    
    # Partner deals with pre-negotiated pricing
    if customer.is_partner and job_type == "installation":
        return "ready_to_schedule"
    
    # Everything else needs an estimate
    return "requires_estimate"
```

**Status Transitions:**
```python
VALID_TRANSITIONS = {
    "requested": ["approved", "cancelled"],
    "approved": ["scheduled", "cancelled"],
    "scheduled": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": ["closed"],
    "cancelled": [],  # Terminal state
    "closed": [],     # Terminal state
}
```

**Pricing Calculation:**
```python
def calculate_price(service: ServiceOffering, property: Property) -> Decimal:
    """Calculate job price based on service and property."""
    
    if service.pricing_model == "flat":
        return service.base_price
    
    if service.pricing_model == "zone_based":
        return service.base_price + (service.price_per_zone * property.zone_count)
    
    if service.pricing_model == "hourly":
        # Estimate based on duration
        hours = service.estimated_duration_minutes / 60
        return service.base_price * hours
    
    # Custom pricing requires manual quote
    return None
```

---

## Feature 2: Service Catalog

### Service Categories

| Category | Examples | Pricing Model | Staffing |
|----------|----------|---------------|----------|
| **Seasonal** | Spring startup, tune-up, winterization | Zone-based | 1 person |
| **Repair** | Broken heads, minor leaks | Flat rate | 1 person |
| **Major Repair** | Pipe replacement, valve repair | Custom | 2 people |
| **Installation** | New irrigation systems | Zone-based | 2-4 people |
| **Diagnostic** | System troubleshooting | Hourly | 1 person |
| **Landscaping** | Sod, plants, hardscaping | Custom | 2-4 people |

### Default Services to Seed

```python
DEFAULT_SERVICES = [
    # Seasonal Services
    {
        "name": "Spring Startup",
        "category": "seasonal",
        "description": "Turn on irrigation system, check all zones, adjust heads",
        "base_price": 75.00,
        "price_per_zone": 5.00,
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 45,
        "duration_per_zone_minutes": 5,
        "staffing_required": 1,
        "equipment_required": [],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Summer Tune-Up",
        "category": "seasonal",
        "description": "Mid-season check, adjust coverage, check for issues",
        "base_price": 65.00,
        "price_per_zone": 5.00,
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 40,
        "duration_per_zone_minutes": 4,
        "staffing_required": 1,
        "equipment_required": [],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Fall Winterization",
        "category": "seasonal",
        "description": "Blow out system with compressed air, shut down for winter",
        "base_price": 70.00,
        "price_per_zone": 5.00,
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 35,
        "duration_per_zone_minutes": 3,
        "staffing_required": 1,
        "equipment_required": ["compressor"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    # Repair Services
    {
        "name": "Sprinkler Head Replacement",
        "category": "repair",
        "description": "Replace broken or damaged sprinkler head",
        "base_price": 50.00,
        "price_per_zone": None,
        "pricing_model": "flat",
        "estimated_duration_minutes": 20,
        "staffing_required": 1,
        "equipment_required": [],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Diagnostic Visit",
        "category": "diagnostic",
        "description": "Troubleshoot system issues, identify problems",
        "base_price": 100.00,
        "price_per_zone": None,
        "pricing_model": "hourly",
        "estimated_duration_minutes": 60,
        "staffing_required": 1,
        "equipment_required": [],
        "lien_eligible": False,
        "requires_prepay": True,
    },
    # Installation Services
    {
        "name": "New System Installation",
        "category": "installation",
        "description": "Complete new irrigation system installation",
        "base_price": 500.00,
        "price_per_zone": 700.00,
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 480,  # 8 hours base
        "duration_per_zone_minutes": 60,
        "staffing_required": 3,
        "equipment_required": ["pipe_puller", "utility_trailer"],
        "lien_eligible": True,
        "requires_prepay": False,
    },
]
```

---

## Feature 3: Staff Management

### Database Schema

```sql
CREATE TABLE staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    
    -- Role and skills
    role VARCHAR(50) NOT NULL,  -- tech, sales, admin
    skill_level VARCHAR(50),    -- junior, senior, lead
    certifications JSONB,       -- ["backflow_certified", "licensed_irrigator"]
    
    -- Availability
    is_available BOOLEAN DEFAULT TRUE,
    availability_notes TEXT,
    
    -- Compensation
    hourly_rate DECIMAL(10, 2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_staff_role ON staff(role);
CREATE INDEX idx_staff_is_active ON staff(is_active);
```

### API Endpoints

```
POST   /api/v1/staff                   # Create staff member
GET    /api/v1/staff/{id}              # Get staff by ID
PUT    /api/v1/staff/{id}              # Update staff
DELETE /api/v1/staff/{id}              # Deactivate staff
GET    /api/v1/staff                   # List staff (with filters)
GET    /api/v1/staff/available         # List available staff
GET    /api/v1/staff/by-role/{role}    # Staff by role
PUT    /api/v1/staff/{id}/availability # Update availability
```

### Default Staff to Seed

```python
DEFAULT_STAFF = [
    {
        "name": "Viktor Grin",
        "phone": "6125551001",
        "email": "viktor@grins-irrigation.com",
        "role": "admin",
        "skill_level": "lead",
        "certifications": ["licensed_irrigator", "backflow_certified"],
        "hourly_rate": 75.00,
    },
    {
        "name": "Dad",
        "phone": "6125551002",
        "role": "tech",
        "skill_level": "senior",
        "certifications": ["backflow_certified"],
        "hourly_rate": 45.00,
    },
    {
        "name": "Vas",
        "phone": "6125551003",
        "role": "tech",
        "skill_level": "senior",
        "certifications": ["licensed_irrigator", "backflow_certified"],
        "hourly_rate": 50.00,
    },
    {
        "name": "Steven",
        "phone": "6125551004",
        "role": "tech",
        "skill_level": "junior",
        "certifications": [],
        "hourly_rate": 35.00,
    },
    {
        "name": "Vitallik",
        "phone": "6125551005",
        "role": "tech",
        "skill_level": "junior",
        "certifications": [],
        "hourly_rate": 35.00,
    },
]
```

---

## Pre-Implementation: Tooling & Efficiency Analysis

**CRITICAL: Before starting any implementation tasks, the agent MUST complete this analysis step.**

### Purpose
Analyze the planned work to determine the most efficient execution strategy using available Kiro tooling.

### Analysis Checklist

#### 1. MCP Servers Assessment
- [ ] Review available MCP servers that could assist with implementation
- [ ] Identify if any external documentation servers would help (AWS docs, library docs, etc.)
- [ ] Determine if database or API testing MCP servers would be beneficial
- [ ] Document which MCP servers to activate and why

#### 2. Powers Assessment
- [ ] List any installed Kiro Powers that could accelerate development
- [ ] Identify if any new Powers should be installed for this phase
- [ ] Document which Powers to use and for what purpose

#### 3. Parallel Execution Opportunities
- [ ] Analyze task dependencies to identify independent work streams
- [ ] Determine which tasks can be executed in parallel by subagents
- [ ] Create dependency graph showing parallelization opportunities
- [ ] Estimate time savings from parallel execution

#### 4. Subagent Strategy
- [ ] Identify specialized subagents needed (e.g., database-agent, api-agent, test-agent)
- [ ] Define clear boundaries for each subagent's responsibilities
- [ ] Plan handoff points between subagents
- [ ] Document subagent invocation order

#### 5. Custom Agents Assessment
- [ ] Review existing custom agents in `.kiro/agents/`
- [ ] Determine if new specialized agents should be created
- [ ] Document agent configurations needed

### Parallelization Analysis for Phase 2

Based on the task dependencies:

```
Service Catalog (Day 8)     Staff Management (Day 11)
        ↓                           ↓
Job Request Management (Days 9-10)  ←──────┘
        ↓
Integration & Polish (Day 12)
```

**Parallel Execution Opportunities:**
- Service Catalog and Staff Management have NO dependencies on each other
- Both can be implemented in parallel by separate subagents
- Job Request Management depends on Service Catalog (for service_offering_id)
- Estimated time savings: 30-40% with parallel execution

### Recommended Tooling Configuration

| Tool Type | Recommendation | Rationale |
|-----------|----------------|-----------|
| **Subagents** | Use `spec-task-execution` for independent features | Parallel implementation of Service Catalog + Staff Management |
| **MCP Servers** | None required for Phase 2 | All work is internal Python/FastAPI development |
| **Powers** | None required | Standard development patterns sufficient |
| **Custom Agents** | Use existing patterns | Established patterns from Phase 1 work well |

### Questions for User Before Implementation

Before proceeding, confirm:
1. Should Service Catalog and Staff Management be implemented in parallel?
2. Are there any MCP servers you'd like to use for documentation or testing?
3. Do you want to create any new custom agents for Phase 2?
4. Any preference on subagent delegation strategy?

---

## Implementation Timeline

### Day 8 (Jan 17) - Service Catalog [4-5 hours]
**Goal:** Implement service catalog as foundation for jobs

- [ ] Create service_offerings migration
- [ ] Create ServiceOffering SQLAlchemy model
- [ ] Create Pydantic schemas (ServiceOfferingCreate, ServiceOfferingResponse)
- [ ] Create ServiceOfferingRepository
- [ ] Create ServiceOfferingService with LoggerMixin
- [ ] Implement service catalog API endpoints
- [ ] Write tests (unit, functional, integration)
- [ ] Seed default services
- [ ] Quality checks

**Deliverables:**
- Service catalog API (6 endpoints)
- Default services seeded
- 85%+ test coverage

---

### Day 9 (Jan 18) - Job Request Management Part 1 [4-5 hours]
**Goal:** Core job CRUD and status management

- [ ] Create jobs migration
- [ ] Create Job SQLAlchemy model with relationships
- [ ] Create Pydantic schemas (JobCreate, JobUpdate, JobResponse)
- [ ] Create JobRepository with filtering
- [ ] Create JobService with LoggerMixin
- [ ] Implement auto-categorization logic
- [ ] Implement status transition validation
- [ ] Write unit tests

**Deliverables:**
- Job model and repository
- Auto-categorization working
- Status transitions validated

---

### Day 10 (Jan 19) - Job Request Management Part 2 [4-5 hours]
**Goal:** Job API endpoints and business logic

- [ ] Implement job CRUD endpoints
- [ ] Implement status update endpoint
- [ ] Implement job filtering (by status, category, customer)
- [ ] Implement pricing calculation
- [ ] Implement customer jobs endpoint
- [ ] Write API tests
- [ ] Write integration tests
- [ ] Quality checks

**Deliverables:**
- Job API (12 endpoints)
- Pricing calculation working
- 85%+ test coverage

---

### Day 11 (Jan 20) - Staff Management [4-5 hours]
**Goal:** Staff profiles and availability

- [ ] Create staff migration
- [ ] Create Staff SQLAlchemy model
- [ ] Create Pydantic schemas
- [ ] Create StaffRepository
- [ ] Create StaffService with LoggerMixin
- [ ] Implement staff API endpoints
- [ ] Write tests (unit, functional, integration)
- [ ] Seed default staff
- [ ] Quality checks

**Deliverables:**
- Staff API (8 endpoints)
- Default staff seeded
- 85%+ test coverage

---

### Day 12 (Jan 21) - Integration & Polish [4-5 hours]
**Goal:** Cross-feature integration and testing

- [ ] Integration tests for job-customer-property relationships
- [ ] Integration tests for job-service relationships
- [ ] Functional testing with real database
- [ ] Update functional test script
- [ ] Performance testing (response times)
- [ ] Documentation updates
- [ ] DEVLOG update

**Deliverables:**
- All integration tests passing
- Functional tests passing
- Documentation complete

---

### Day 13-14 (Jan 22-23) - Buffer & Demo Prep
**Goal:** Handle overflow and prepare for hackathon submission

- [ ] Fix any remaining issues
- [ ] Final quality checks
- [ ] Demo video preparation
- [ ] README updates
- [ ] Submission preparation

---

## Task Breakdown Summary

### Service Catalog Tasks (8 tasks)
1. Database migration
2. SQLAlchemy model
3. Pydantic schemas
4. Repository layer
5. Service layer
6. API endpoints
7. Tests (unit, functional, integration)
8. Seed data

### Job Request Management Tasks (15 tasks)
1. Database migration
2. SQLAlchemy model with relationships
3. Pydantic schemas (create, update, response, filters)
4. Repository layer with filtering
5. Service layer with LoggerMixin
6. Auto-categorization logic
7. Status transition validation
8. Pricing calculation
9. Job CRUD endpoints
10. Status update endpoint
11. Job filtering endpoints
12. Customer jobs endpoint
13. Unit tests
14. API tests
15. Integration tests

### Staff Management Tasks (8 tasks)
1. Database migration
2. SQLAlchemy model
3. Pydantic schemas
4. Repository layer
5. Service layer
6. API endpoints
7. Tests (unit, functional, integration)
8. Seed data

**Total: 31 tasks**

---

## Success Criteria

### Feature Complete When:

**Service Catalog:**
- [ ] 6 API endpoints implemented and tested
- [ ] Default services seeded
- [ ] Pricing models working (flat, zone_based, hourly, custom)
- [ ] 85%+ test coverage

**Job Request Management:**
- [ ] 12 API endpoints implemented and tested
- [ ] Auto-categorization working
- [ ] Status transitions validated
- [ ] Pricing calculation working
- [ ] Job-customer-property relationships working
- [ ] 85%+ test coverage

**Staff Management:**
- [ ] 8 API endpoints implemented and tested
- [ ] Default staff seeded
- [ ] Availability tracking working
- [ ] 85%+ test coverage

### Quality Standards:
- [ ] All Ruff checks passing
- [ ] All MyPy checks passing
- [ ] All tests passing (target: 600+ tests)
- [ ] Functional tests passing
- [ ] API documentation complete (OpenAPI)

---

## Definition of Done

**A feature is considered COMPLETE when ALL of the following are true:**

### Required Criteria (ALL must pass)

1. **All Tasks Completed**
   - Every task and subtask in the feature's task list is marked as `[x]` complete
   - No tasks are left in progress `[-]` or not started `[ ]`

2. **All Tests Passing**
   - Unit tests: All pass (`uv run pytest -m unit`)
   - Functional tests: All pass (`uv run pytest -m functional`)
   - Integration tests: All pass (`uv run pytest -m integration`)
   - Property-based tests: All pass (if applicable)
   - Full test suite: `uv run pytest -v` shows 0 failures

3. **Quality Checks Passing**
   - Ruff: `uv run ruff check src/` returns 0 violations
   - MyPy: `uv run mypy src/` returns 0 errors

### Verification Command

Run this single command to verify a feature is complete:

```bash
uv run ruff check src/ && uv run mypy src/ && uv run pytest -v
```

**If this command passes with 0 errors and all tasks are marked complete, the feature is DONE.**

### NOT Complete If:
- ❌ Any task is still `[ ]` or `[-]`
- ❌ Any test is failing
- ❌ Ruff reports any violations
- ❌ MyPy reports any errors
- ❌ Functional tests haven't been run against real database

---

## API Summary (Phase 2)

### New Endpoints (26 total)

**Service Catalog (6 endpoints):**
```
GET    /api/v1/services                # List all services
GET    /api/v1/services/{id}           # Get service details
GET    /api/v1/services/category/{cat} # Services by category
POST   /api/v1/services                # Create service
PUT    /api/v1/services/{id}           # Update service
DELETE /api/v1/services/{id}           # Deactivate service
```

**Job Request Management (12 endpoints):**
```
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
```

**Staff Management (8 endpoints):**
```
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

## Cumulative Progress

### After Phase 1:
- 16 API endpoints
- 482 tests
- 95% coverage

### After Phase 2 (Target):
- 42 API endpoints (+26)
- 700+ tests (+220)
- 90%+ coverage

---

## Dependencies for Phase 3

Phase 2 establishes the foundation for Phase 3 (Scheduling):

- **Jobs** → Required for appointment scheduling
- **Staff** → Required for staff assignment
- **Services** → Required for duration/equipment planning

Phase 3 will add:
- Appointment scheduling
- Route optimization (Timefold)
- Staff assignment
- Calendar management

---

## Notes

- Follow same patterns established in Phase 1
- Use LoggerMixin with appropriate domains ("job", "service", "staff")
- Three-tier testing (unit, functional, integration)
- Property-based tests for validation logic
- Update DEVLOG after each major milestone
