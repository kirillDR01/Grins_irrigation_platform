# Phase 1 Implementation Planning

**Date:** January 15, 2025  
**Status:** Planning Complete - Ready for Implementation  
**Timeline:** Days 1-7 (Jan 15-21)  
**Goal:** Implement Customer Management, Job Request Management, and Basic Scheduling

---

## Codebase Analysis Summary

### Current Implementation Status

#### ✅ **Infrastructure Complete**
- **Logging System**: Fully implemented with structlog
  - Hybrid dotted namespace pattern (`{domain}.{component}.{action}_{state}`)
  - Request ID correlation
  - LoggerMixin for class-based logging
  - DomainLogger helpers for common patterns
- **Quality Tools**: Configured and tested
  - Ruff (800+ rules)
  - MyPy (strict mode)
  - Pyright (comprehensive type checking)
  - Pytest with coverage
- **Docker Setup**: Complete with docker-compose
- **Database Schema**: Initial SQL schema in `scripts/init-db.sql`
  - Users, Customers, Services, Jobs tables
  - Indexes and triggers
  - Sample data

#### ✅ **Kiro Foundation Complete**
- 9 steering documents
- 25+ custom prompts
- 2 agent hooks
- 2 custom agents (devlog, prompt-manager)
- Comprehensive DEVLOG

#### 🔲 **Missing Implementation** (What We Need to Build)
- **No FastAPI application** - main.py is a test script
- **No API endpoints** - no routes defined
- **No service layer** - no business logic
- **No repository layer** - no database access
- **No Pydantic models** - no request/response schemas
- **No database migrations** - no Alembic setup
- **No actual features** - only test/demo code

### Key Insight
**We have excellent infrastructure but zero application code.** This is perfect for demonstrating Kiro's spec-driven development from scratch!

---

## First Feature Decision: Customer Management

### Why Customer Management First?

1. **Foundation Feature**: All other features depend on customers
2. **Complete CRUD**: Demonstrates full API development cycle
3. **Clear Requirements**: Well-defined in product.md
4. **Testable**: Easy to write comprehensive tests
5. **Demo-Worthy**: Shows working API with database

### Customer Management Scope

#### Core Entities
- **Customer**: Basic customer information
- **Property**: Customer property details (zones, system type)
- **CustomerFlag**: Priority status, red flags, payment history

#### API Endpoints (8 endpoints)
```
POST   /api/v1/customers              # Create customer
GET    /api/v1/customers/{id}         # Get customer by ID
PUT    /api/v1/customers/{id}         # Update customer
DELETE /api/v1/customers/{id}         # Delete customer
GET    /api/v1/customers              # List customers (with filters)
POST   /api/v1/customers/{id}/properties  # Add property
GET    /api/v1/customers/{id}/properties  # List properties
PUT    /api/v1/customers/{id}/flags   # Update customer flags
```

#### Business Logic
- Customer validation (email, phone format)
- Property validation (zone count, system type)
- Flag management (priority, red flag, slow pay)
- Service history tracking
- Communication preferences (SMS/email opt-in)

---

## Kiro Setup for Customer Management

### Priority 0: Essential Setup (2 hours)

#### 1. Git MCP Server (30 minutes)
**Purpose**: Automated git operations, commit messages, branch management

**Setup**:
```bash
# Create MCP configuration
mkdir -p .kiro/settings

# Create mcp.json
```

**Configuration**:
```json
{
  "mcpServers": {
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git"],
      "disabled": false,
      "autoApprove": ["git/status", "git/diff", "git/log"]
    }
  }
}
```

**Usage During Development**:
- `"Use @git to create a feature branch for customer-management"`
- `"Use @git to commit the customer repository implementation"`
- `"Show me the git diff for the last commit using @git/diff"`

**Why First**: Immediate workflow improvement, used throughout development

---

#### 2. Database Agent (30 minutes)
**Purpose**: Database schema design, migrations, SQLAlchemy models

**Create**: `.kiro/agents/database-agent.json`

```json
{
  "name": "database-agent",
  "description": "Specialized agent for PostgreSQL schema design, Alembic migrations, and SQLAlchemy models with async support",
  "prompt": "You are a database specialist for the Grin's Irrigation Platform.\n\nYour expertise:\n1. PostgreSQL schema design following best practices\n2. Alembic migration creation and management\n3. SQLAlchemy 2.0 async models with proper relationships\n4. Query optimization and indexing strategies\n5. Data integrity constraints and validation\n\nYou MUST:\n- Use structured logging (LoggerMixin) in repository classes\n- Follow patterns in tech.md and structure.md\n- Write comprehensive tests for all database operations\n- Use async/await patterns with asyncpg\n- Include proper type hints (MyPy + Pyright compliant)\n\nDatabase connection: PostgreSQL 15+ with asyncpg driver\nORM: SQLAlchemy 2.0 with async support\nMigrations: Alembic",
  "tools": ["read", "write", "shell"],
  "allowedTools": ["read", "write", "shell:alembic", "shell:psql", "shell:pytest"],
  "resources": [
    "file://scripts/init-db.sql",
    "file://.kiro/steering/tech.md",
    "file://.kiro/steering/structure.md",
    "file://.kiro/steering/code-standards.md",
    "file://ARCHITECTURE.md"
  ],
  "model": "claude-sonnet-4"
}
```

**Usage**:
```bash
/agent swap database-agent
"Create the customers table migration with all required fields and relationships"
"Implement the Customer SQLAlchemy model with async support"
```

**Why First**: Needed immediately for database schema and models

---

#### 3. API Agent (30 minutes)
**Purpose**: FastAPI endpoint development with validation and testing

**Create**: `.kiro/agents/api-agent.json`

```json
{
  "name": "api-agent",
  "description": "Specialized agent for FastAPI endpoint development with comprehensive testing and validation",
  "prompt": "You are an API development specialist for the Grin's Irrigation Platform.\n\nYour expertise:\n1. FastAPI endpoint implementation with proper HTTP methods\n2. Pydantic request/response schema design\n3. Error handling with appropriate status codes\n4. Request validation and sanitization\n5. API documentation and OpenAPI specs\n\nYou MUST:\n- Follow patterns in api-patterns.md exactly\n- Use request ID correlation (set_request_id/clear_request_id)\n- Log all API events (started, completed, failed)\n- Include comprehensive API tests with TestClient\n- Use proper HTTP status codes (200, 201, 400, 404, 500)\n- Write Pydantic schemas for all requests/responses\n\nFramework: FastAPI with async support\nValidation: Pydantic v2\nTesting: pytest with TestClient",
  "tools": ["read", "write", "shell"],
  "allowedTools": ["read", "write", "shell:pytest", "shell:uvicorn"],
  "resources": [
    "file://.kiro/steering/api-patterns.md",
    "file://.kiro/steering/code-standards.md",
    "file://.kiro/steering/tech.md",
    "file://ARCHITECTURE.md"
  ],
  "model": "claude-sonnet-4"
}
```

**Usage**:
```bash
/agent swap api-agent
"Implement the customer CRUD endpoints with full validation"
"Create comprehensive API tests for customer endpoints"
```

**Why First**: Core to implementing customer API

---

#### 4. Service Agent (30 minutes)
**Purpose**: Business logic and service layer implementation

**Create**: `.kiro/agents/service-agent.json`

```json
{
  "name": "service-agent",
  "description": "Specialized agent for business logic and service layer implementation with comprehensive testing",
  "prompt": "You are a service layer specialist for the Grin's Irrigation Platform.\n\nYour expertise:\n1. Service class implementation with LoggerMixin\n2. Business logic and validation rules\n3. Error handling with custom exceptions\n4. Service-to-repository communication\n5. Transaction management and data consistency\n\nYou MUST:\n- Follow patterns in service-patterns.md exactly\n- Inherit from LoggerMixin and set DOMAIN attribute\n- Log all operations (started, completed, failed, validated, rejected)\n- Write comprehensive service tests (85%+ coverage)\n- Use proper exception handling (ValidationError, NotFoundError, ServiceError)\n- Include type hints for all methods\n\nPattern: Service → Repository → Database\nLogging: Structured with request correlation\nTesting: pytest with mocks for repositories",
  "tools": ["read", "write", "shell"],
  "allowedTools": ["read", "write", "shell:pytest"],
  "resources": [
    "file://.kiro/steering/service-patterns.md",
    "file://.kiro/steering/code-standards.md",
    "file://.kiro/steering/tech.md",
    "file://ARCHITECTURE.md"
  ],
  "model": "claude-sonnet-4"
}
```

**Usage**:
```bash
/agent swap service-agent
"Implement CustomerService with all CRUD operations and business logic"
"Add validation for customer email and phone formats"
```

**Why First**: Business logic layer for customer management

---

### Priority 1: Spec Creation (2 hours)

#### Customer Management Spec

**Create**: `.kiro/specs/customer-management/`

**Structure**:
```
.kiro/specs/customer-management/
├── requirements.md    # User stories and acceptance criteria
├── design.md          # Technical design and architecture
└── tasks.md           # Implementation task breakdown
```

**Requirements.md Content** (30 minutes):
- User stories for customer CRUD
- Acceptance criteria for each operation
- Data requirements (customer, property, flags)
- Validation rules
- API contract specifications

**Design.md Content** (45 minutes):
- API endpoint specifications
- Pydantic schema definitions
- Service layer design
- Repository layer design
- Database schema (customers, properties, customer_flags tables)
- Error handling strategy
- Logging patterns
- Testing strategy

**Tasks.md Content** (45 minutes):
- Task 1: Database Setup
  - 1.1 Set up Alembic for migrations
  - 1.2 Create customers table migration
  - 1.3 Create properties table migration
  - 1.4 Create customer_flags table migration
  - 1.5 Test migrations
- Task 2: Models & Schemas
  - 2.1 Create Customer SQLAlchemy model
  - 2.2 Create Property SQLAlchemy model
  - 2.3 Create CustomerFlag SQLAlchemy model
  - 2.4 Create Pydantic request schemas
  - 2.5 Create Pydantic response schemas
- Task 3: Repository Layer
  - 3.1 Create CustomerRepository with CRUD operations
  - 3.2 Create PropertyRepository
  - 3.3 Write repository tests (85%+ coverage)
- Task 4: Service Layer
  - 4.1 Create CustomerService with LoggerMixin
  - 4.2 Implement business logic and validation
  - 4.3 Write service tests (85%+ coverage)
- Task 5: API Layer
  - 5.1 Create FastAPI application structure
  - 5.2 Implement customer CRUD endpoints
  - 5.3 Implement property endpoints
  - 5.4 Implement flag management endpoint
  - 5.5 Write API tests (85%+ coverage)
- Task 6: Integration Testing
  - 6.1 End-to-end customer workflow tests
  - 6.2 Property management workflow tests
  - 6.3 Flag management workflow tests

**How to Create**:
```bash
# Use Kiro's spec workflow
"Create a formal spec for Customer Management feature following the requirements-first workflow. Include:
- User stories for customer CRUD operations
- Technical design with API/service/repository layers
- Detailed task breakdown with 20-25 tasks
- Database schema for customers, properties, and flags
- Comprehensive testing strategy"
```

---

## Implementation Timeline

### Day 1 (Today - Jan 15) [4-5 hours]
**Goal**: Complete Kiro setup

- ✅ Steering documents (DONE)
- ✅ Custom prompts (DONE)
- ✅ Agent hooks (DONE)
- ✅ Existing agents (DONE)
- 🔲 Git MCP server setup (30 min)
- 🔲 Create database-agent (30 min)
- 🔲 Create api-agent (30 min)
- 🔲 Create service-agent (30 min)
- 🔲 Test all agents and MCP (30 min)
- 🔲 Update DEVLOG (30 min)

**Deliverables**:
- `.kiro/settings/mcp.json` with Git MCP
- `.kiro/agents/database-agent.json`
- `.kiro/agents/api-agent.json`
- `.kiro/agents/service-agent.json`
- All agents tested and working

---

### Day 2 (Jan 16) [4-5 hours]
**Goal**: Create Customer Management spec

- 🔲 Create spec directory structure (15 min)
- 🔲 Write requirements.md (1h)
  - User stories
  - Acceptance criteria
  - Data requirements
- 🔲 Write design.md (1.5h)
  - API endpoints
  - Schemas
  - Service/repository design
  - Database schema
- 🔲 Write tasks.md (1h)
  - 20-25 detailed tasks
  - Dependencies mapped
  - Testing requirements
- 🔲 Review and refine spec (30 min)
- 🔲 Update DEVLOG (30 min)

**Deliverables**:
- Complete Customer Management spec in `.kiro/specs/customer-management/`
- Ready-to-execute task list

---

### Days 3-5 (Jan 17-19) [12-15 hours]
**Goal**: Implement Customer Management feature

**Day 3 - Database Layer** [4-5h]:
- Set up Alembic
- Create migrations (customers, properties, flags)
- Create SQLAlchemy models
- Write repository layer
- Repository tests

**Day 4 - Service & API Layer** [4-5h]:
- Create CustomerService with business logic
- Service tests
- Create FastAPI application structure
- Implement customer CRUD endpoints
- API tests

**Day 5 - Complete & Polish** [4-5h]:
- Property management endpoints
- Flag management endpoint
- Integration tests
- Quality checks (ruff, mypy, pyright, pytest)
- Documentation

**Deliverables**:
- Fully working Customer Management API
- 85%+ test coverage
- All quality checks passing
- Comprehensive documentation

---

## Success Criteria

### Feature Complete When:
- ✅ All 8 API endpoints implemented and tested
- ✅ Database schema created with migrations
- ✅ Service layer with business logic
- ✅ Repository layer with database access
- ✅ 85%+ test coverage
- ✅ All quality checks passing (ruff, mypy, pyright, pytest)
- ✅ Comprehensive logging throughout
- ✅ API documentation (OpenAPI)
- ✅ Integration tests passing

### Kiro Usage Demonstrated:
- ✅ Spec-driven development (requirements → design → tasks)
- ✅ Git MCP for automated commits
- ✅ Specialized agents (database, API, service)
- ✅ Subagent delegation for parallel work
- ✅ Comprehensive DEVLOG updates
- ✅ Quality automation with hooks

---

## Next Steps

### Immediate Actions (Next 30 minutes):
1. Create `.kiro/settings/mcp.json` with Git MCP configuration
2. Create `database-agent.json`
3. Create `api-agent.json`
4. Create `service-agent.json`
5. Test Git MCP: `"Use @git to show current status"`
6. Test agents: `/agent swap database-agent` and ask a database question

### After Setup Complete:
1. Use spec workflow to create Customer Management spec
2. Review and refine spec
3. Begin Day 3 implementation following task list

---

## Questions to Confirm

Before we proceed with implementation, please confirm:

1. **Git MCP**: Should we set up Git MCP first? (Recommended: Yes)
2. **Filesystem MCP**: Should we also set up Filesystem MCP now, or wait? (Recommend: Wait until needed)
3. **Testing Agent**: Should we create a testing-agent now, or wait? (Recommend: Wait, use service/api agents for tests)
4. **Spec Creation**: Should we create the spec manually or use Kiro's spec workflow? (Recommend: Use Kiro workflow)

**Ready to begin implementation?** Let me know and I'll start with the Kiro setup!
