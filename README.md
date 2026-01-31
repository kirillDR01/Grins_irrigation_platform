# Grin's Irrigation Platform

A comprehensive field service automation platform designed for residential and commercial irrigation businesses. This full-stack application replaces manual spreadsheet-based operations with intelligent scheduling, customer management, invoicing, and AI-powered assistance.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Frontend Application](#frontend-application)
- [AI Features](#ai-features)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Development](#development)

---

## Overview

Grin's Irrigation Platform is a field service automation system that eliminates the time-consuming manual processes of tracking job requests, scheduling appointments, managing field staff, and handling invoicing. The platform is designed to:

- **Reduce administrative time by 70%** - From 15-20 hours/week to 4-6 hours/week
- **Increase job capacity by 25%** - Handle more jobs with the same staff
- **Improve customer response time** - Automated acknowledgments within minutes
- **Reduce missed appointments** - 90%+ confirmation rate with automated reminders
- **Accelerate payment collection** - Same-day invoicing with automated reminders

### Target Users

| Role | Description | Access Level |
|------|-------------|--------------|
| **Admin** | Business owner/manager - Full system access | Full admin |
| **Manager** | Operations coordinator - Schedule and staff management | Manager access |
| **Technician** | Field staff - Job execution and completion | Tech access |

---

## Key Features

### 1. Customer Management
- Complete customer profiles with contact info, addresses, and property details
- Customer flags (priority, red flag, slow payer) for quick identification
- Multiple properties per customer with primary property designation
- Communication preferences (SMS/email opt-in)
- Service history tracking
- Bulk operations for preference updates
- CSV export functionality

### 2. Property Management
- Property details including zone count, system type, and property type
- GPS coordinates for route optimization
- Access instructions and gate codes
- Service area validation (Twin Cities metro)
- Primary property switching

### 3. Job Management
- Complete job lifecycle: Requested → Approved → Scheduled → In-Progress → Completed → Closed
- Job categories: Seasonal, Repair, Installation, Diagnostic, Estimate
- Automatic categorization based on job type and source
- Priority levels (1-5) for scheduling
- Price calculation (flat rate or zone-based)
- Status history tracking
- Jobs ready to schedule queue
- Jobs requiring estimate queue

### 4. Service Catalog
- Service offerings with categories (Seasonal, Repair, Installation, Diagnostic)
- Pricing models (flat rate, per zone, custom)
- Equipment requirements
- Staffing requirements
- Estimated duration

### 5. Staff Management
- Staff profiles with roles (Admin, Manager, Technician)
- Skill levels (Junior, Mid, Senior, Lead)
- Equipment certifications
- Availability management with time windows
- Lunch break scheduling
- GPS location tracking support

### 6. Appointment Scheduling
- Calendar and list views
- Daily and weekly schedule views
- Staff-specific schedules
- Appointment status workflow: Scheduled → Confirmed → Arrived → Completed
- Cancellation with reason tracking
- Time window management

### 7. AI-Powered Schedule Generation
- Intelligent route optimization
- City-based job batching
- Equipment constraint matching
- Staff availability consideration
- Travel time estimation (Google Maps integration)
- Natural language constraint parsing
- Schedule explanation with AI insights
- Emergency job insertion
- Schedule reoptimization

### 8. Invoice Management
- Invoice generation from completed jobs
- Line item support
- Payment tracking (Cash, Check, Venmo, Zelle, Stripe)
- Partial payment support
- Overdue invoice tracking
- Lien eligibility tracking (45-day warning, 120-day filing)
- Payment reminders
- Invoice status workflow: Draft → Sent → Viewed → Paid/Partial/Overdue

### 9. AI Assistant Features
- **Job Categorization**: AI-powered analysis of job descriptions
- **Estimate Generation**: Similar job lookup and pricing suggestions
- **Communication Drafts**: Automated message generation for customers
- **Schedule Explanation**: Natural language explanations of scheduling decisions
- **Business Query Chat**: Ask questions about customers, jobs, revenue
- **Morning Briefing**: Daily summary of scheduled work

### 10. SMS Communications
- Twilio integration for SMS messaging
- Opt-in compliance
- Message templates for common communications
- Delivery status tracking
- Communications queue management
- Bulk send capability

### 11. Dashboard & Analytics
- Overview metrics (customers, jobs, appointments)
- Request volume tracking by source and category
- Schedule overview with staff assignments
- Payment status overview
- Jobs by status breakdown
- Today's schedule summary

### 12. Authentication & Security
- JWT-based authentication with access and refresh tokens
- Role-based access control (Admin, Manager, Tech)
- Account lockout after failed attempts
- Password strength requirements
- CSRF protection
- Secure cookie handling

---

## Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Python 3.10+** | Core language |
| **FastAPI** | Web framework |
| **SQLAlchemy 2.0** | ORM with async support |
| **PostgreSQL** | Primary database |
| **Alembic** | Database migrations |
| **Pydantic 2.0** | Data validation |
| **structlog** | Structured logging |
| **OpenAI** | AI features |
| **Twilio** | SMS communications |
| **Timefold** | Schedule optimization |
| **uv** | Package management |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 19** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool |
| **TanStack Query** | Server state management |
| **React Router 7** | Routing |
| **Tailwind CSS 4** | Styling |
| **Radix UI** | Accessible components |
| **React Hook Form** | Form handling |
| **Zod** | Schema validation |
| **FullCalendar** | Calendar views |
| **Google Maps API** | Map visualization |
| **Vitest** | Testing |

### Development Tools
| Tool | Purpose |
|------|---------|
| **Ruff** | Linting and formatting |
| **MyPy** | Static type checking |
| **Pyright** | Additional type checking |
| **pytest** | Testing framework |
| **Hypothesis** | Property-based testing |
| **ESLint** | Frontend linting |
| **Prettier** | Code formatting |

---

## Architecture

### Backend Architecture

```
src/grins_platform/
├── api/v1/                 # API endpoints
│   ├── auth.py             # Authentication endpoints
│   ├── customers.py        # Customer CRUD
│   ├── properties.py       # Property management
│   ├── jobs.py             # Job management
│   ├── appointments.py     # Appointment scheduling
│   ├── staff.py            # Staff management
│   ├── services.py         # Service catalog
│   ├── invoices.py         # Invoice management
│   ├── schedule.py         # Schedule generation
│   ├── schedule_clear.py   # Schedule clearing/restore
│   ├── ai.py               # AI assistant endpoints
│   ├── sms.py              # SMS communications
│   ├── dashboard.py        # Dashboard metrics
│   └── conflict_resolution.py  # Scheduling conflicts
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic schemas
├── services/               # Business logic
│   ├── ai/                 # AI services
│   │   ├── agent.py        # Chat agent
│   │   ├── context/        # Context builders
│   │   ├── tools/          # AI tools
│   │   └── ...
│   └── ...
├── repositories/           # Data access layer
├── exceptions/             # Custom exceptions
├── middleware/             # CSRF, logging
├── migrations/             # Alembic migrations
├── app.py                  # Application factory
├── database.py             # Database configuration
└── log_config.py           # Logging configuration
```

### Frontend Architecture (Vertical Slice)

```
frontend/src/
├── core/                   # Foundation
│   ├── api/                # API client
│   ├── config/             # Environment config
│   ├── providers/          # React providers
│   └── router/             # Route definitions
├── shared/                 # Cross-feature utilities
│   ├── components/         # Shared components
│   ├── hooks/              # Shared hooks
│   └── utils/              # Utilities
├── features/               # Feature slices
│   ├── auth/               # Authentication
│   ├── customers/          # Customer management
│   ├── jobs/               # Job management
│   ├── schedule/           # Scheduling
│   ├── staff/              # Staff management
│   ├── invoices/           # Invoice management
│   ├── dashboard/          # Dashboard
│   └── ai/                 # AI features
├── components/ui/          # UI components (shadcn)
└── pages/                  # Page components
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 20 or higher
- PostgreSQL 15+
- uv package manager

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/kirillDR01/Grins_irrigation_platform.git
cd Grins_irrigation_platform

# Install dependencies with uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
uv run alembic upgrade head

# Start the backend server
uv run uvicorn grins_platform.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/grins_platform

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# AI Features
OPENAI_API_KEY=your-openai-api-key

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Google Maps
GOOGLE_MAPS_API_KEY=your-google-maps-key

# CORS
CORS_ORIGINS=http://localhost:5173,https://your-domain.com
```

---

## API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/logout` | POST | User logout |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/auth/change-password` | POST | Change password |

### Customers

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/customers` | GET | List customers |
| `/api/v1/customers` | POST | Create customer |
| `/api/v1/customers/{id}` | GET | Get customer |
| `/api/v1/customers/{id}` | PUT | Update customer |
| `/api/v1/customers/{id}` | DELETE | Delete customer |
| `/api/v1/customers/{id}/flags` | PATCH | Update flags |
| `/api/v1/customers/{id}/service-history` | GET | Get service history |
| `/api/v1/customers/lookup/phone` | GET | Lookup by phone |
| `/api/v1/customers/lookup/email` | GET | Lookup by email |
| `/api/v1/customers/export` | GET | Export to CSV |
| `/api/v1/customers/bulk/preferences` | PATCH | Bulk update preferences |

### Properties

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/customers/{id}/properties` | GET | List properties |
| `/api/v1/customers/{id}/properties` | POST | Add property |
| `/api/v1/properties/{id}` | GET | Get property |
| `/api/v1/properties/{id}` | PUT | Update property |
| `/api/v1/properties/{id}` | DELETE | Delete property |
| `/api/v1/properties/{id}/primary` | POST | Set as primary |

### Jobs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs` | GET | List jobs |
| `/api/v1/jobs` | POST | Create job |
| `/api/v1/jobs/{id}` | GET | Get job |
| `/api/v1/jobs/{id}` | PUT | Update job |
| `/api/v1/jobs/{id}` | DELETE | Delete job |
| `/api/v1/jobs/{id}/status` | PATCH | Update status |
| `/api/v1/jobs/{id}/history` | GET | Get status history |
| `/api/v1/jobs/{id}/price` | GET | Calculate price |
| `/api/v1/jobs/ready-to-schedule` | GET | Jobs ready to schedule |
| `/api/v1/jobs/needs-estimate` | GET | Jobs needing estimate |
| `/api/v1/jobs/status/{status}` | GET | Jobs by status |

### Appointments

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/appointments` | GET | List appointments |
| `/api/v1/appointments` | POST | Create appointment |
| `/api/v1/appointments/{id}` | GET | Get appointment |
| `/api/v1/appointments/{id}` | PUT | Update appointment |
| `/api/v1/appointments/{id}/cancel` | POST | Cancel appointment |
| `/api/v1/appointments/daily/{date}` | GET | Daily schedule |
| `/api/v1/appointments/weekly` | GET | Weekly schedule |
| `/api/v1/appointments/staff/{id}/daily/{date}` | GET | Staff daily schedule |

### Schedule Generation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/schedule/generate` | POST | Generate schedule |
| `/api/v1/schedule/preview` | POST | Preview schedule |
| `/api/v1/schedule/capacity` | GET | Get capacity |
| `/api/v1/schedule/apply` | POST | Apply schedule |
| `/api/v1/schedule/explain` | POST | Explain schedule |
| `/api/v1/schedule/explain-unassigned` | POST | Explain unassigned job |
| `/api/v1/schedule/parse-constraints` | POST | Parse natural language constraints |
| `/api/v1/schedule/jobs-ready` | GET | Jobs ready to schedule |
| `/api/v1/schedule/emergency` | POST | Insert emergency job |
| `/api/v1/schedule/reoptimize` | POST | Reoptimize schedule |

### Schedule Clear/Restore

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/schedule/clear` | POST | Clear day's schedule |
| `/api/v1/schedule/clear/recent` | GET | Recent clears |
| `/api/v1/schedule/clear/{id}` | GET | Clear details |
| `/api/v1/schedule/restore` | POST | Restore schedule |

### Staff

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/staff` | GET | List staff |
| `/api/v1/staff` | POST | Create staff |
| `/api/v1/staff/{id}` | GET | Get staff |
| `/api/v1/staff/{id}` | PUT | Update staff |
| `/api/v1/staff/{id}` | DELETE | Delete staff |
| `/api/v1/staff/available` | GET | Available staff |
| `/api/v1/staff/role/{role}` | GET | Staff by role |
| `/api/v1/staff/{id}/availability` | GET | Get availability |
| `/api/v1/staff/{id}/availability` | POST | Create availability |
| `/api/v1/staff/{id}/availability/{date}` | PUT | Update availability |
| `/api/v1/staff/{id}/availability/{date}` | DELETE | Delete availability |

### Services

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/services` | GET | List services |
| `/api/v1/services` | POST | Create service |
| `/api/v1/services/{id}` | GET | Get service |
| `/api/v1/services/{id}` | PUT | Update service |
| `/api/v1/services/{id}` | DELETE | Delete service |
| `/api/v1/services/category/{category}` | GET | Services by category |

### Invoices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/invoices` | GET | List invoices |
| `/api/v1/invoices` | POST | Create invoice |
| `/api/v1/invoices/{id}` | GET | Get invoice |
| `/api/v1/invoices/{id}` | PUT | Update invoice |
| `/api/v1/invoices/{id}/cancel` | POST | Cancel invoice |
| `/api/v1/invoices/{id}/send` | POST | Send invoice |
| `/api/v1/invoices/{id}/payment` | POST | Record payment |
| `/api/v1/invoices/{id}/reminder` | POST | Send reminder |
| `/api/v1/invoices/{id}/lien-warning` | POST | Send lien warning |
| `/api/v1/invoices/{id}/lien-filed` | POST | Mark lien filed |
| `/api/v1/invoices/generate/{job_id}` | POST | Generate from job |
| `/api/v1/invoices/overdue` | GET | Overdue invoices |
| `/api/v1/invoices/lien-deadlines` | GET | Lien deadlines |

### AI Assistant

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ai/chat` | POST | Chat with AI |
| `/api/v1/ai/schedule/generate` | POST | AI schedule generation |
| `/api/v1/ai/categorize` | POST | Categorize job |
| `/api/v1/ai/communication/draft` | POST | Draft communication |
| `/api/v1/ai/estimate` | POST | Generate estimate |
| `/api/v1/ai/query` | POST | Business query |
| `/api/v1/ai/usage` | GET | AI usage stats |
| `/api/v1/ai/audit` | GET | Audit logs |
| `/api/v1/ai/audit/{id}/decision` | POST | Record decision |

### SMS Communications

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sms/send` | POST | Send SMS |
| `/api/v1/sms/webhook` | POST | Twilio webhook |
| `/api/v1/communications/queue` | GET | Message queue |
| `/api/v1/communications/bulk-send` | POST | Bulk send |
| `/api/v1/communications/{id}` | DELETE | Delete message |

### Dashboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/dashboard/metrics` | GET | Overview metrics |
| `/api/v1/dashboard/request-volume` | GET | Request volume |
| `/api/v1/dashboard/schedule-overview` | GET | Schedule overview |
| `/api/v1/dashboard/payment-status` | GET | Payment status |
| `/api/v1/dashboard/jobs-by-status` | GET | Jobs by status |
| `/api/v1/dashboard/today-schedule` | GET | Today's schedule |

---

## Frontend Application

### Pages

| Page | Route | Description |
|------|-------|-------------|
| Login | `/login` | User authentication |
| Dashboard | `/dashboard` | Overview metrics and quick actions |
| Customers | `/customers` | Customer list and management |
| Customer Detail | `/customers/:id` | Individual customer view |
| Jobs | `/jobs` | Job list and management |
| Job Detail | `/jobs/:id` | Individual job view |
| Schedule | `/schedule` | Calendar and list views |
| Generate Schedule | `/schedule/generate` | AI-powered schedule generation |
| Staff | `/staff` | Staff list and management |
| Staff Detail | `/staff/:id` | Individual staff view |
| Invoices | `/invoices` | Invoice list and management |
| Invoice Detail | `/invoices/:id` | Individual invoice view |
| Settings | `/settings` | User settings and preferences |

### Key Components

- **Layout**: Main application layout with sidebar navigation
- **GlobalSearch**: Search across customers, jobs, and staff
- **CustomerForm**: Create/edit customer with property management
- **JobForm**: Create/edit job with service selection
- **AppointmentForm**: Schedule appointments with staff assignment
- **CalendarView**: FullCalendar integration for schedule visualization
- **ScheduleMap**: Google Maps integration for route visualization
- **AICategorization**: AI-powered job categorization
- **AIEstimateGenerator**: AI-powered estimate generation
- **CommunicationsQueue**: SMS message management

---

## AI Features

### Job Categorization
Analyzes job descriptions to determine:
- Job category (Seasonal, Repair, Installation, etc.)
- Whether estimate is required
- Suggested services
- Confidence score

### Estimate Generation
Provides pricing suggestions based on:
- Similar historical jobs
- Service catalog pricing
- Property characteristics
- Labor and material estimates

### Schedule Explanation
Natural language explanations of:
- Why jobs were assigned to specific staff
- Why certain jobs couldn't be scheduled
- Route optimization decisions
- Constraint violations

### Communication Drafts
Generates professional messages for:
- Appointment confirmations
- Appointment reminders
- On-the-way notifications
- Completion summaries
- Payment reminders

### Business Query Chat
Answer questions about:
- Customer information
- Job history
- Revenue metrics
- Staff availability
- Schedule status

---

## Database Schema

### Core Tables

| Table | Description |
|-------|-------------|
| `customers` | Customer information |
| `properties` | Customer properties |
| `jobs` | Job requests and work orders |
| `job_status_history` | Job status change tracking |
| `service_offerings` | Service catalog |
| `staff` | Staff members |
| `staff_availability` | Staff availability windows |
| `appointments` | Scheduled appointments |
| `invoices` | Customer invoices |
| `sent_messages` | SMS message history |
| `ai_audit_log` | AI recommendation tracking |
| `ai_usage` | AI usage statistics |
| `schedule_clear_audit` | Schedule clear history |

### Key Relationships

```
customers 1:N properties
customers 1:N jobs
jobs N:1 service_offerings
jobs 1:N appointments
jobs 1:N invoices
appointments N:1 staff
staff 1:N staff_availability
```

---

## Testing

### Backend Tests

```bash
# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/grins_platform --cov-report=html

# Run specific test file
uv run pytest src/grins_platform/tests/test_customer_api.py -v

# Run property-based tests
uv run pytest -m "hypothesis" -v
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch
```

### Test Categories

- **Unit Tests**: Isolated component testing with mocks
- **Integration Tests**: Cross-component workflow testing
- **Functional Tests**: End-to-end feature testing
- **Property-Based Tests**: Hypothesis-based invariant testing

---

## Deployment

### Production Deployment

The application is designed for deployment on:
- **Backend**: Railway, AWS, or any Docker-compatible platform
- **Frontend**: Vercel, Netlify, or any static hosting
- **Database**: PostgreSQL (Railway, AWS RDS, etc.)

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Production build
docker build -t grins-platform .
docker run -p 8000:8000 grins-platform
```

### Environment Configuration

See `DEPLOYMENT_INSTRUCTIONS.md` for detailed deployment guides.

---

## Development

### Code Quality

```bash
# Backend linting
uv run ruff check src/
uv run ruff format src/

# Type checking
uv run mypy src/
uv run pyright src/

# Frontend linting
cd frontend && npm run lint
npm run typecheck
```

### Database Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback
uv run alembic downgrade -1
```

### Development Scripts

```bash
# Setup project
./scripts/setup.sh

# Development workflow
./scripts/dev.sh

# Validate features
./scripts/validate-all.sh
```

---

## Project Structure

```
grins-irrigation-platform/
├── src/grins_platform/     # Backend source code
├── frontend/               # React frontend
├── scripts/                # Development scripts
├── docs/                   # Documentation
├── .kiro/                  # Kiro AI configuration
│   ├── specs/              # Feature specifications
│   ├── steering/           # Development guidelines
│   └── prompts/            # Custom prompts
├── screenshots/            # UI screenshots
├── pyproject.toml          # Python project config
├── docker-compose.yml      # Docker configuration
├── Dockerfile              # Container definition
└── README.md               # This file
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

For issues and feature requests, please use the [GitHub Issues](https://github.com/kirillDR01/Grins_irrigation_platform/issues) page.

---

**Built for Grin's Irrigations** - Serving the Twin Cities metro area with professional irrigation services.
