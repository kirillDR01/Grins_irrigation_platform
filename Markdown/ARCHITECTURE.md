# Grin's Irrigation Platform - Complete Architecture Document

**Version:** 1.0  
**Date:** January 15, 2025  
**Status:** Final Architecture Decision  

This document represents the best-of-both-worlds architecture combining insights from the Platform_Architecture_Ideas.md technical feasibility report and additional architectural recommendations for a production-ready field service automation platform.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Layered Architecture](#layered-architecture)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Service Layer Design](#service-layer-design)
8. [Frontend Architecture](#frontend-architecture)
9. [Integration Architecture](#integration-architecture)
10. [Security Architecture](#security-architecture)
11. [Deployment Architecture](#deployment-architecture)
12. [Phase Implementation Details](#phase-implementation-details)

---

## Executive Summary

### Project Overview

The Grin's Irrigation Platform is a comprehensive field service automation system designed to replace manual spreadsheet-based operations. The platform serves a residential and commercial irrigation service business in the Twin Cities metro area, handling 150+ jobs per week during peak seasons.

### Architecture Philosophy

This architecture follows these core principles:

1. **Layered Separation** - Clear boundaries between API, Service, Repository, and Infrastructure layers
2. **Domain-Driven Design** - Business logic organized around core domains (Customer, Job, Staff, etc.)
3. **Offline-First Mobile** - PWA architecture for field technicians with unreliable connectivity
4. **Event-Driven Communication** - Async processing for notifications and background tasks
5. **Type Safety** - Full type hints with dual validation (MyPy + Pyright)
6. **Observability** - Structured logging with request correlation throughout

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Async, type-safe, auto-generated OpenAPI docs |
| AI Agent Framework | Pydantic AI | Native FastAPI integration, same Pydantic foundation |
| Route Optimization | Timefold | Python-native, free, supports all scheduling constraints |
| Database | PostgreSQL | Robust relational model for CRM data |
| Task Queue | Celery + Redis | Proven async task processing for notifications |
| Staff Mobile | PWA (React) | Offline capability, no app store deployment |
| SMS/Voice | Twilio | Industry standard, excellent Python SDK |
| Payments | Stripe | Invoicing API, stored payment methods |

---

## System Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT APPLICATIONS                                │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Admin Web   │  │  Staff PWA   │  │  Customer    │  │   Public     │    │
│  │  Dashboard   │  │  (Offline)   │  │   Portal     │  │   Website    │    │
│  │              │  │              │  │              │  │              │    │
│  │ • Client     │  │ • Job Cards  │  │ • Booking    │  │ • Landing    │    │
│  │ • Schedule   │  │ • GPS Track  │  │ • Payments   │  │ • Pricing    │    │
│  │ • Sales      │  │ • Payments   │  │ • History    │  │ • AI Chat    │    │
│  │ • Accounting │  │ • Offline    │  │ • Profile    │  │ • Contact    │    │
│  │ • Marketing  │  │ • Photos     │  │              │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│        │                  │                  │                  │           │
└────────┼──────────────────┼──────────────────┼──────────────────┼───────────┘
         │                  │                  │                  │
         └──────────────────┴──────────────────┴──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY (FastAPI)                              │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Auth      │  │   Rate      │  │  Request    │  │  Validation │        │
│  │   (JWT)     │  │  Limiting   │  │ Correlation │  │  (Pydantic) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  Endpoints: /api/v1/customers, /api/v1/jobs, /api/v1/staff, etc.           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                      │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Customer   │  │    Job      │  │  Schedule   │  │   Staff     │        │
│  │  Service    │  │  Service    │  │  Service    │  │  Service    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Invoice    │  │  Estimate   │  │  Payment    │  │ Notification│        │
│  │  Service    │  │  Service    │  │  Service    │  │  Service    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │  Marketing  │  │ Accounting  │  │  AI Agent   │                         │
│  │  Service    │  │  Service    │  │  Service    │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REPOSITORY LAYER                                    │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ CustomerRepo│  │  JobRepo    │  │ StaffRepo   │  │ InvoiceRepo │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │EstimateRepo │  │ PaymentRepo │  │ RouteRepo   │  │AppointmentRp│        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INFRASTRUCTURE LAYER                                  │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ PostgreSQL  │  │   Redis     │  │   Celery    │  │     S3      │        │
│  │  (Primary)  │  │(Cache/Queue)│  │  (Tasks)    │  │  (Files)    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Timefold   │  │ Pydantic AI │  │   Twilio    │  │   Stripe    │        │
│  │  (Routes)   │  │  (AI Chat)  │  │ (SMS/Voice) │  │ (Payments)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │Google Maps  │  │   Plaid     │  │ Cloud Vision│                         │
│  │(GPS/Address)│  │  (Banking)  │  │   (OCR)     │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### The Six Dashboards

Based on Viktor's detailed vision, the system includes six interconnected dashboards:

| Dashboard | Purpose | Primary User | Phase |
|-----------|---------|--------------|-------|
| **Client Dashboard** | Lead intake, request management, customer overview | Admin (Viktor) | 1 |
| **Scheduling Dashboard** | Route building, staff assignment, calendar management | Admin (Viktor) | 1-2 |
| **Staff/Crew Dashboard** | Mobile job cards, GPS tracking, job completion | Field Techs | 2 |
| **Sales Dashboard** | Estimates, pipeline management, follow-ups | Sales Staff | 5 |
| **Accounting Dashboard** | Invoicing, expenses, tax preparation | Admin (Viktor) | 6 |
| **Marketing Dashboard** | Campaigns, lead attribution, ROI tracking | Admin (Viktor) | 6 |

---

## Technology Stack

### Core Technologies

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Language** | Python | 3.11+ | Type hints, async/await, performance improvements |
| **Package Manager** | uv | Latest | 10-100x faster than pip |
| **Build System** | Hatchling | Latest | Modern Python packaging |

### Backend Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Web Framework** | FastAPI | Async, type-safe, auto-generated OpenAPI docs, excellent performance |
| **Validation** | Pydantic v2 | Data validation, serialization, settings management |
| **ORM** | SQLAlchemy 2.0 | Async support, type hints, mature ecosystem |
| **Migrations** | Alembic | Database schema versioning |
| **Database Driver** | asyncpg | High-performance async PostgreSQL driver |

### Data Layer

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Primary Database** | PostgreSQL 15+ | Robust relational model, JSON support, full-text search |
| **Cache** | Redis 7+ | Session storage, rate limiting, pub/sub |
| **Task Queue** | Celery | Distributed task processing, scheduling |
| **Message Broker** | Redis | Celery broker, simple setup |
| **File Storage** | S3 / MinIO | Photos, receipts, documents |

### AI & Optimization

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **AI Agent** | Pydantic AI | Native FastAPI integration, type-safe, tool calling |
| **LLM Provider** | Claude (Anthropic) | Best coding/reasoning, Pydantic AI support |
| **Route Optimization** | Timefold | Python-native, free, constraint-based scheduling |

### External Integrations

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **SMS/Voice** | Twilio | Industry standard, Conversations API, webhooks |
| **Payments** | Stripe | Invoicing API, stored payments, subscriptions |
| **Maps/GPS** | Google Maps Platform | Geocoding, directions, ETA calculation |
| **Address Validation** | Google Address Validation | Prevent wrong address issues |
| **Banking** | Plaid | Bank account connection for accounting |
| **OCR** | Google Cloud Vision | Receipt text extraction |

### Frontend Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Admin Dashboard** | React + TypeScript | Type safety, component ecosystem |
| **Staff PWA** | React + TypeScript | Offline-first, installable |
| **Customer Portal** | React + TypeScript | Consistent stack |
| **Public Website** | Next.js | SEO optimization, SSR |
| **State Management** | TanStack Query | Server state, caching, offline |
| **UI Components** | Tailwind CSS + shadcn/ui | Rapid development, consistent design |

### Quality & Testing

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Linting** | Ruff | 800+ rules, fast, replaces multiple tools |
| **Type Checking** | MyPy + Pyright | Dual validation for maximum safety |
| **Testing** | pytest | Fixtures, async support, plugins |
| **Coverage** | pytest-cov | Coverage reporting |
| **Property Testing** | Hypothesis | Property-based testing for data transformations |
| **Logging** | structlog | Structured JSON logging |

### DevOps

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Containerization** | Docker | Consistent local development environments |
| **Orchestration** | Docker Compose | Local development only (not for production) |
| **CI/CD** | GitHub Actions | Automated testing and deployment |
| **Backend Hosting** | Railway (recommended) | Zero-config deployment, managed services |
| **Frontend Hosting** | Vercel (recommended) | Global CDN, automatic HTTPS, preview deploys |
| **Alternative Hosting** | Render / AWS | Render similar to Railway; AWS for enterprise scale |

---

## Layered Architecture

### Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                        API LAYER                                 │
│  • HTTP request/response handling                                │
│  • Request validation (Pydantic models)                          │
│  • Authentication/authorization                                  │
│  • Request correlation ID injection                              │
│  • Error response formatting                                     │
│  • OpenAPI documentation                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
│  • Business logic implementation                                 │
│  • Transaction management                                        │
│  • Cross-cutting concerns (logging, validation)                  │
│  • Orchestration of multiple repositories                        │
│  • External service integration                                  │
│  • Event emission for async processing                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    REPOSITORY LAYER                              │
│  • Data access abstraction                                       │
│  • CRUD operations                                               │
│  • Query building                                                │
│  • Database-specific logic                                       │
│  • Caching integration                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                            │
│  • Database connections                                          │
│  • External API clients                                          │
│  • Message queue producers/consumers                             │
│  • File storage                                                  │
│  • Configuration management                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/grins_platform/
├── __init__.py
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management
├── exceptions.py                # Custom exception classes
├── log_config.py                # Structured logging setup
│
├── api/                         # API Layer
│   ├── __init__.py
│   ├── dependencies.py          # Dependency injection
│   ├── middleware.py            # Request correlation, auth
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── router.py            # Main API router
│   │   ├── customers.py         # Customer endpoints
│   │   ├── jobs.py              # Job endpoints
│   │   ├── staff.py             # Staff endpoints
│   │   ├── appointments.py      # Appointment endpoints
│   │   ├── invoices.py          # Invoice endpoints
│   │   └── estimates.py         # Estimate endpoints
│   └── schemas/                 # Pydantic request/response models
│       ├── __init__.py
│       ├── customer.py
│       ├── job.py
│       ├── staff.py
│       └── common.py
│
├── services/                    # Service Layer
│   ├── __init__.py
│   ├── base.py                  # Base service with LoggerMixin
│   ├── customer_service.py
│   ├── job_service.py
│   ├── staff_service.py
│   ├── schedule_service.py
│   ├── appointment_service.py
│   ├── invoice_service.py
│   ├── estimate_service.py
│   ├── notification_service.py
│   └── payment_service.py
│
├── repositories/                # Repository Layer
│   ├── __init__.py
│   ├── base.py                  # Base repository
│   ├── customer_repository.py
│   ├── job_repository.py
│   ├── staff_repository.py
│   ├── appointment_repository.py
│   ├── invoice_repository.py
│   └── estimate_repository.py
│
├── models/                      # SQLAlchemy Models
│   ├── __init__.py
│   ├── base.py                  # Base model with common fields
│   ├── customer.py
│   ├── property.py
│   ├── job.py
│   ├── staff.py
│   ├── appointment.py
│   ├── invoice.py
│   ├── estimate.py
│   └── enums.py                 # Shared enumerations
│
├── infrastructure/              # Infrastructure Layer
│   ├── __init__.py
│   ├── database.py              # Database connection
│   ├── redis.py                 # Redis client
│   ├── celery.py                # Celery configuration
│   └── external/
│       ├── __init__.py
│       ├── twilio_client.py
│       ├── stripe_client.py
│       ├── google_maps_client.py
│       └── timefold_client.py
│
├── tasks/                       # Celery Tasks
│   ├── __init__.py
│   ├── notifications.py         # SMS/email tasks
│   ├── scheduling.py            # Route optimization tasks
│   └── invoicing.py             # Invoice reminder tasks
│
└── tests/                       # Test Files
    ├── __init__.py
    ├── conftest.py              # Shared fixtures
    ├── test_customers.py
    ├── test_jobs.py
    ├── test_staff.py
    └── integration/
        ├── __init__.py
        └── test_job_workflow.py
```

---

## Database Schema

### Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Customer     │       │    Property     │       │      Job        │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │──┐    │ id (PK)         │
│ first_name      │  │    │ customer_id(FK) │◄─┘    │ customer_id(FK) │
│ last_name       │  │    │ address         │       │ property_id(FK) │
│ phone           │  │    │ city            │       │ job_type        │
│ email           │  │    │ zone_count      │       │ status          │
│ username        │  │    │ system_type     │       │ category        │
│ password_hash   │  │    │ property_type   │       │ description     │
│ flags           │  │    │ special_notes   │       │ estimated_dur   │
│ sms_opt_in      │  │    │ access_instruct │       │ priority_level  │
│ email_opt_in    │  │    │ created_at      │       │ source          │
│ lead_source     │  └───►│ updated_at      │       │ created_at      │
│ created_at      │       └─────────────────┘       │ updated_at      │
│ updated_at      │                                 └─────────────────┘
└─────────────────┘                                         │
        │                                                   │
        │       ┌─────────────────┐       ┌─────────────────┐
        │       │     Staff       │       │   Appointment   │
        │       ├─────────────────┤       ├─────────────────┤
        │       │ id (PK)         │──┐    │ id (PK)         │
        │       │ name            │  │    │ job_id (FK)     │◄───┘
        │       │ phone           │  │    │ staff_id (FK)   │◄───┘
        │       │ email           │  │    │ scheduled_date  │
        │       │ role            │  │    │ time_window_st  │
        │       │ skill_level     │  │    │ time_window_end │
        │       │ hourly_rate     │  │    │ status          │
        │       │ availability    │  │    │ confirmation_st │
        │       │ current_loc     │  │    │ notes           │
        │       │ created_at      │  │    │ created_at      │
        │       │ updated_at      │  │    │ updated_at      │
        │       └─────────────────┘  │    └─────────────────┘
        │                            │
        │       ┌─────────────────┐  │    ┌─────────────────┐
        │       │    Invoice      │  │    │    Estimate     │
        │       ├─────────────────┤  │    ├─────────────────┤
        └──────►│ id (PK)         │  │    │ id (PK)         │◄───┐
                │ customer_id(FK) │  │    │ customer_id(FK) │    │
                │ job_id (FK)     │  │    │ job_type        │    │
                │ amount          │  │    │ description     │    │
                │ due_date        │  │    │ amount          │    │
                │ status          │  │    │ tier_options    │    │
                │ late_fee        │  │    │ status          │    │
                │ lien_eligible   │  │    │ contract_signed │    │
                │ reminder_count  │  │    │ follow_up_count │    │
                │ created_at      │  │    │ created_at      │    │
                │ updated_at      │  │    │ updated_at      │    │
                └─────────────────┘  │    └─────────────────┘    │
                                     │                           │
                                     └───────────────────────────┘
```

### Complete Table Definitions

#### customers
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    
    -- Flags
    is_priority BOOLEAN DEFAULT FALSE,
    is_red_flag BOOLEAN DEFAULT FALSE,
    is_slow_payer BOOLEAN DEFAULT FALSE,
    is_new_customer BOOLEAN DEFAULT TRUE,
    
    -- Communication preferences
    sms_opt_in BOOLEAN DEFAULT TRUE,
    email_opt_in BOOLEAN DEFAULT TRUE,
    
    -- Lead tracking
    lead_source VARCHAR(50),  -- website, google, referral, ad, etc.
    lead_source_details JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_lead_source ON customers(lead_source);
```

#### properties
```sql
CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Location
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) DEFAULT 'MN',
    zip_code VARCHAR(20),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- System details
    zone_count INTEGER,
    system_type VARCHAR(50) DEFAULT 'standard',  -- standard, lake_pump
    property_type VARCHAR(50) DEFAULT 'residential',  -- residential, commercial
    
    -- Access information
    access_instructions TEXT,
    gate_code VARCHAR(50),
    has_dogs BOOLEAN DEFAULT FALSE,
    special_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_properties_customer ON properties(customer_id);
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_location ON properties(latitude, longitude);
```

#### service_offerings
```sql
CREATE TABLE service_offerings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- seasonal, repair, installation, diagnostic
    description TEXT,
    
    -- Pricing
    base_price DECIMAL(10, 2),
    price_per_zone DECIMAL(10, 2),
    pricing_model VARCHAR(50),  -- flat, zone_based, hourly, custom
    
    -- Time estimates
    estimated_duration_minutes INTEGER,
    duration_per_zone_minutes INTEGER,
    
    -- Requirements
    staffing_required INTEGER DEFAULT 1,
    equipment_required JSONB,  -- ["compressor", "pipe_puller"]
    
    -- Lien eligibility
    lien_eligible BOOLEAN DEFAULT FALSE,
    requires_prepay BOOLEAN DEFAULT FALSE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### jobs
```sql
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
    time_allocated_minutes INTEGER,
    priority_level INTEGER DEFAULT 0,
    weather_sensitive BOOLEAN DEFAULT FALSE,
    
    -- Requirements
    staffing_required INTEGER DEFAULT 1,
    equipment_required JSONB,
    materials_required JSONB,
    materials_used JSONB,
    
    -- Pricing
    quoted_amount DECIMAL(10, 2),
    final_amount DECIMAL(10, 2),
    
    -- Completion
    completion_status VARCHAR(50),
    completion_notes TEXT,
    photos JSONB,  -- Array of photo URLs
    additional_work_requested TEXT,
    review_collected BOOLEAN DEFAULT FALSE,
    review_skipped_reason VARCHAR(255),
    
    -- Validation
    pre_scheduling_validated BOOLEAN DEFAULT FALSE,
    
    -- Source tracking
    source VARCHAR(50),
    source_details JSONB,
    
    -- Timestamps
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    approved_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_jobs_customer ON jobs(customer_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_category ON jobs(category);
CREATE INDEX idx_jobs_job_type ON jobs(job_type);
```

#### staff
```sql
CREATE TABLE staff (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    
    -- Role and skills
    role VARCHAR(50) NOT NULL,  -- tech, sales, admin
    skill_level VARCHAR(50),
    certifications JSONB,
    
    -- Availability
    availability_calendar JSONB,
    
    -- Compensation
    hourly_rate DECIMAL(10, 2),
    
    -- Current status
    current_location_lat DECIMAL(10, 8),
    current_location_lng DECIMAL(11, 8),
    last_location_update TIMESTAMP WITH TIME ZONE,
    current_job_id UUID REFERENCES jobs(id),
    current_job_started_at TIMESTAMP WITH TIME ZONE,
    
    -- Vehicle assignment
    assigned_vehicle_id UUID,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_staff_role ON staff(role);
CREATE INDEX idx_staff_current_job ON staff(current_job_id);
```

#### appointments
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
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, confirmed, in_progress, completed, cancelled
    confirmation_status VARCHAR(50) DEFAULT 'unconfirmed',
    confirmation_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Execution
    arrived_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Notes
    notes TEXT,
    
    -- Route information
    route_order INTEGER,
    estimated_arrival TIME,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_appointments_job ON appointments(job_id);
CREATE INDEX idx_appointments_staff ON appointments(staff_id);
CREATE INDEX idx_appointments_date ON appointments(scheduled_date);
CREATE INDEX idx_appointments_status ON appointments(status);
```

#### invoices
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    
    -- Amounts
    amount DECIMAL(10, 2) NOT NULL,
    late_fee_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    
    -- Dates
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- draft, sent, paid, overdue, lien_warning, lien_filed
    
    -- Payment
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Reminders
    reminder_count INTEGER DEFAULT 0,
    last_reminder_sent TIMESTAMP WITH TIME ZONE,
    
    -- Lien tracking
    lien_eligible BOOLEAN DEFAULT FALSE,
    lien_warning_sent TIMESTAMP WITH TIME ZONE,
    lien_filed_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
```

#### estimates
```sql
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    property_id UUID REFERENCES properties(id),
    sales_staff_id UUID REFERENCES staff(id),
    
    -- Estimate details
    job_type VARCHAR(50) NOT NULL,
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    tier_options JSONB,  -- Multiple pricing tiers
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- draft, sent, viewed, approved, declined, expired
    
    -- Contract
    contract_signed BOOLEAN DEFAULT FALSE,
    contract_url VARCHAR(500),
    
    -- Follow-up
    follow_up_count INTEGER DEFAULT 0,
    last_follow_up_sent TIMESTAMP WITH TIME ZONE,
    last_contact_date TIMESTAMP WITH TIME ZONE,
    
    -- Promotional
    promotional_discount_applied DECIMAL(10, 2),
    
    -- Attachments
    diagrams JSONB,
    photos JSONB,
    videos JSONB,
    
    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE,
    viewed_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_estimates_customer ON estimates(customer_id);
CREATE INDEX idx_estimates_status ON estimates(status);
CREATE INDEX idx_estimates_sales_staff ON estimates(sales_staff_id);
```

#### staff_locations (for GPS tracking)
```sql
CREATE TABLE staff_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(id),
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    accuracy DECIMAL(10, 2),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_staff_locations_staff ON staff_locations(staff_id);
CREATE INDEX idx_staff_locations_time ON staff_locations(recorded_at);
```

#### notifications
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_type VARCHAR(50) NOT NULL,  -- customer, staff
    recipient_id UUID NOT NULL,
    
    -- Content
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,  -- sms, email, push
    subject VARCHAR(255),
    body TEXT NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, sent, delivered, failed
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Reference
    reference_type VARCHAR(50),  -- job, appointment, invoice
    reference_id UUID,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_recipient ON notifications(recipient_type, recipient_id);
CREATE INDEX idx_notifications_status ON notifications(status);
```

---

## API Design

### API Versioning

All API endpoints are versioned under `/api/v1/`. This allows for future breaking changes without disrupting existing clients.

### Endpoint Overview

#### Customer Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/customers` | List customers with filtering/pagination |
| POST | `/api/v1/customers` | Create new customer |
| GET | `/api/v1/customers/{id}` | Get customer by ID |
| PUT | `/api/v1/customers/{id}` | Update customer |
| DELETE | `/api/v1/customers/{id}` | Soft delete customer |
| GET | `/api/v1/customers/{id}/properties` | Get customer's properties |
| GET | `/api/v1/customers/{id}/jobs` | Get customer's job history |
| GET | `/api/v1/customers/{id}/invoices` | Get customer's invoices |

#### Property Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/properties` | List properties with filtering |
| POST | `/api/v1/properties` | Create new property |
| GET | `/api/v1/properties/{id}` | Get property by ID |
| PUT | `/api/v1/properties/{id}` | Update property |
| DELETE | `/api/v1/properties/{id}` | Delete property |

#### Job Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobs` | List jobs with filtering/pagination |
| POST | `/api/v1/jobs` | Create new job request |
| GET | `/api/v1/jobs/{id}` | Get job by ID |
| PUT | `/api/v1/jobs/{id}` | Update job |
| POST | `/api/v1/jobs/{id}/approve` | Approve job for scheduling |
| POST | `/api/v1/jobs/{id}/complete` | Mark job as complete |
| POST | `/api/v1/jobs/{id}/cancel` | Cancel job |
| GET | `/api/v1/jobs/ready-to-schedule` | Get jobs ready to schedule |
| GET | `/api/v1/jobs/requires-estimate` | Get jobs requiring estimate |

#### Staff Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/staff` | List staff members |
| POST | `/api/v1/staff` | Create staff member |
| GET | `/api/v1/staff/{id}` | Get staff by ID |
| PUT | `/api/v1/staff/{id}` | Update staff |
| GET | `/api/v1/staff/{id}/schedule` | Get staff's schedule |
| POST | `/api/v1/staff/{id}/location` | Update staff location |
| GET | `/api/v1/staff/{id}/current-job` | Get staff's current job |

#### Appointment Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/appointments` | List appointments with filtering |
| POST | `/api/v1/appointments` | Create appointment |
| GET | `/api/v1/appointments/{id}` | Get appointment by ID |
| PUT | `/api/v1/appointments/{id}` | Update appointment |
| POST | `/api/v1/appointments/{id}/confirm` | Confirm appointment |
| POST | `/api/v1/appointments/{id}/arrive` | Mark arrival |
| POST | `/api/v1/appointments/{id}/complete` | Complete appointment |
| POST | `/api/v1/appointments/{id}/cancel` | Cancel appointment |
| GET | `/api/v1/appointments/daily/{date}` | Get appointments for date |
| GET | `/api/v1/appointments/staff/{staff_id}/daily/{date}` | Get staff's daily route |

#### Schedule Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/schedule/generate` | Generate optimized schedule |
| GET | `/api/v1/schedule/weekly` | Get weekly schedule overview |
| POST | `/api/v1/schedule/send-confirmations` | Send appointment confirmations |
| GET | `/api/v1/schedule/capacity` | Get scheduling capacity |

#### Invoice Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/invoices` | List invoices with filtering |
| POST | `/api/v1/invoices` | Create invoice |
| GET | `/api/v1/invoices/{id}` | Get invoice by ID |
| PUT | `/api/v1/invoices/{id}` | Update invoice |
| POST | `/api/v1/invoices/{id}/send` | Send invoice to customer |
| POST | `/api/v1/invoices/{id}/mark-paid` | Mark invoice as paid |
| GET | `/api/v1/invoices/pending` | Get pending invoices |
| GET | `/api/v1/invoices/overdue` | Get overdue invoices |

#### Estimate Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/estimates` | List estimates with filtering |
| POST | `/api/v1/estimates` | Create estimate |
| GET | `/api/v1/estimates/{id}` | Get estimate by ID |
| PUT | `/api/v1/estimates/{id}` | Update estimate |
| POST | `/api/v1/estimates/{id}/send` | Send estimate to customer |
| POST | `/api/v1/estimates/{id}/approve` | Mark estimate as approved |
| GET | `/api/v1/estimates/pending` | Get pending estimates |

#### Service Offering Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/services` | List service offerings |
| GET | `/api/v1/services/{id}` | Get service by ID |
| GET | `/api/v1/services/pricing` | Get pricing calculator |

#### Dashboard Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/overview` | Get dashboard overview metrics |
| GET | `/api/v1/dashboard/requests` | Get request volume metrics |
| GET | `/api/v1/dashboard/schedule` | Get schedule overview |
| GET | `/api/v1/dashboard/payments` | Get payment status overview |

### Request/Response Patterns

#### Standard Response Format
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

#### Error Response Format
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": {
      "field": "email",
      "constraint": "required"
    }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

#### Pagination
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8
  }
}
```

### Authentication

JWT-based authentication with role-based access control:

```
Authorization: Bearer <jwt_token>
```

Roles:
- `admin` - Full access to all endpoints
- `staff` - Access to job completion, location updates
- `customer` - Access to own data only

---

## Service Layer Design

### Base Service Pattern

All services inherit from a base class that provides logging and common functionality:

```python
from grins_platform.log_config import LoggerMixin

class BaseService(LoggerMixin):
    """Base service class with logging and common patterns."""
    
    DOMAIN = "business"  # Override in subclasses
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
```

### Service Responsibilities

#### CustomerService
- Customer CRUD operations
- Customer flag management (priority, red flag, slow payer)
- Customer search and filtering
- Lead source tracking
- Communication preference management

#### JobService
- Job request creation and categorization
- Job status workflow management
- Job approval and completion
- Job history tracking
- Source attribution

#### StaffService
- Staff profile management
- Availability calendar management
- GPS location tracking
- Current job status
- Skill and certification tracking

#### ScheduleService
- Schedule generation with constraints
- Route optimization (via Timefold)
- Staff assignment
- Capacity planning
- Lead time calculation

#### AppointmentService
- Appointment creation and management
- Confirmation workflow
- Arrival and completion tracking
- Route ordering
- Time window management

#### InvoiceService
- Invoice generation from jobs
- Payment tracking
- Reminder scheduling
- Late fee calculation
- Lien eligibility checking

#### EstimateService
- Estimate creation with tiers
- Follow-up tracking
- Contract management
- Approval workflow

#### NotificationService
- SMS sending via Twilio
- Email sending
- Push notifications
- Notification templates
- Delivery tracking

#### PaymentService
- Stripe integration
- Payment processing
- Stored payment methods
- Refund handling

### Service Interaction Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    Job Completion Flow                          │
└─────────────────────────────────────────────────────────────────┘

Staff marks arrival
        │
        ▼
┌─────────────────┐
│ AppointmentSvc  │──► Update appointment status to "in_progress"
│                 │──► Record arrival time
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ NotificationSvc │──► Send "technician arrived" SMS to customer
└─────────────────┘
        │
        ▼
Staff completes work
        │
        ▼
┌─────────────────┐
│ AppointmentSvc  │──► Update appointment status to "completed"
│                 │──► Record completion time
└─────────────────┘
        │
        ▼
┌─────────────────┐
│    JobService   │──► Update job status to "completed"
│                 │──► Record materials used, photos, notes
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  InvoiceService │──► Generate invoice if payment not collected
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ NotificationSvc │──► Send completion summary to customer
│                 │──► Notify next customer of ETA
└─────────────────┘
```

---

## Frontend Architecture

### Admin Dashboard (React + TypeScript)

#### Component Structure
```
src/
├── components/
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Table.tsx
│   │   ├── Modal.tsx
│   │   └── StatusBadge.tsx
│   ├── customers/
│   │   ├── CustomerList.tsx
│   │   ├── CustomerDetail.tsx
│   │   └── CustomerForm.tsx
│   ├── jobs/
│   │   ├── JobList.tsx
│   │   ├── JobDetail.tsx
│   │   └── JobStatusBadge.tsx
│   ├── schedule/
│   │   ├── ScheduleCalendar.tsx
│   │   ├── RouteBuilder.tsx
│   │   └── StaffAssignment.tsx
│   └── dashboard/
│       ├── MetricsCard.tsx
│       ├── RequestsChart.tsx
│       └── ScheduleOverview.tsx
├── pages/
│   ├── Dashboard.tsx
│   ├── Customers.tsx
│   ├── Jobs.tsx
│   ├── Schedule.tsx
│   ├── Invoices.tsx
│   └── Settings.tsx
├── hooks/
│   ├── useCustomers.ts
│   ├── useJobs.ts
│   ├── useSchedule.ts
│   └── useNotifications.ts
├── services/
│   └── api.ts
└── types/
    └── index.ts
```

### Staff PWA (React + TypeScript)

#### Offline-First Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Staff PWA Architecture                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────►│  Service Worker │────►│   IndexedDB     │
│                 │     │                 │     │                 │
│ • Route View    │     │ • Cache API     │     │ • Jobs          │
│ • Job Cards     │     │ • Background    │     │ • Customers     │
│ • Completion    │     │   Sync          │     │ • Pending       │
│   Form          │     │ • Offline       │     │   Updates       │
│                 │     │   Detection     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Backend API                              │
│                                                                  │
│  • Sync endpoint for bulk updates                                │
│  • Conflict resolution (last-write-wins)                         │
│  • Delta sync for efficiency                                     │
└─────────────────────────────────────────────────────────────────┘
```

#### PWA Features
- **Installable** - Add to home screen
- **Offline capable** - Full functionality without network
- **Background sync** - Queue updates until online
- **Push notifications** - Real-time alerts
- **GPS tracking** - Location updates

#### Component Structure
```
src/
├── components/
│   ├── RouteView.tsx
│   ├── JobCard.tsx
│   ├── CompletionForm.tsx
│   ├── PhotoCapture.tsx
│   ├── PriceList.tsx
│   └── Navigation.tsx
├── pages/
│   ├── DailyRoute.tsx
│   ├── JobDetail.tsx
│   ├── Complete.tsx
│   └── Settings.tsx
├── hooks/
│   ├── useOfflineSync.ts
│   ├── useGeolocation.ts
│   └── useJobCompletion.ts
├── services/
│   ├── api.ts
│   ├── offlineStorage.ts
│   └── syncService.ts
└── sw.ts  # Service Worker
```

---

## Integration Architecture

### Twilio Integration (SMS/Voice)

#### Configuration
```python
TWILIO_ACCOUNT_SID = "..."
TWILIO_AUTH_TOKEN = "..."
TWILIO_PHONE_NUMBER = "+1..."
TWILIO_MESSAGING_SERVICE_SID = "..."  # For bulk messaging
```

#### Notification Types
| Type | Trigger | Template |
|------|---------|----------|
| Appointment Confirmation | Schedule created | "Your {service} is scheduled for {date} {time}. Reply YES to confirm." |
| Appointment Reminder | 48 hours before | "Reminder: {service} tomorrow {time}. Reply CHANGE to reschedule." |
| On The Way | Staff departs previous job | "{tech_name} is on the way. ETA: {eta}" |
| Arrival | Staff marks arrived | "Your technician has arrived." |
| Completion | Job completed | "Service complete! {summary}. Invoice: {link}" |
| Invoice Reminder | 3 days before due | "Invoice #{id} due in 3 days. Pay: {link}" |
| Overdue Notice | 7 days overdue | "Invoice #{id} is overdue. Pay: {link}" |

#### Two-Way Messaging
```python
# Webhook endpoint for incoming SMS
@router.post("/webhooks/twilio/sms")
async def handle_incoming_sms(request: Request):
    body = await request.form()
    from_number = body.get("From")
    message = body.get("Body").strip().upper()
    
    if message == "YES":
        # Confirm appointment
        await appointment_service.confirm_by_phone(from_number)
    elif message == "CHANGE":
        # Initiate reschedule flow
        await appointment_service.request_reschedule(from_number)
```

### Stripe Integration (Payments)

#### Configuration
```python
STRIPE_SECRET_KEY = "sk_..."
STRIPE_PUBLISHABLE_KEY = "pk_..."
STRIPE_WEBHOOK_SECRET = "whsec_..."
```

#### Invoice Flow
```
Job Completed
      │
      ▼
┌─────────────────┐
│ Create Stripe   │
│ Invoice         │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Send Invoice    │──► Customer receives email with payment link
│ via Stripe      │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Webhook:        │──► Update local invoice status
│ invoice.paid    │
└─────────────────┘
```

#### Stored Payment Methods
```python
# Store card for future charges
customer = stripe.Customer.create(
    email=customer.email,
    name=f"{customer.first_name} {customer.last_name}"
)

# Attach payment method
stripe.PaymentMethod.attach(
    payment_method_id,
    customer=customer.id
)

# Charge stored card
stripe.PaymentIntent.create(
    amount=amount_cents,
    currency="usd",
    customer=customer.id,
    payment_method=payment_method_id,
    off_session=True,
    confirm=True
)
```

### Timefold Integration (Route Optimization)

#### Constraint Model
```python
from timefold.solver import SolverFactory
from timefold.solver.config import SolverConfig

# Define constraints
constraints = [
    # Hard constraints (must satisfy)
    "staff_availability",      # Staff must be available
    "equipment_requirements",  # Required equipment must be on vehicle
    "time_windows",           # Must arrive within customer's window
    "skill_requirements",     # Staff must have required skills
    
    # Soft constraints (optimize)
    "minimize_travel_time",   # Reduce total driving
    "batch_by_location",      # Group jobs in same city
    "batch_by_job_type",      # Group similar jobs
    "first_come_first_serve", # Respect request order
    "priority_customers",     # VIP customers first
]
```

#### Schedule Generation
```python
async def generate_schedule(
    jobs: list[Job],
    staff: list[Staff],
    date: date
) -> Schedule:
    """Generate optimized schedule for a day."""
    
    # Build problem
    problem = ScheduleProblem(
        jobs=jobs,
        staff=staff,
        date=date
    )
    
    # Solve
    solver = SolverFactory.create(solver_config)
    solution = solver.solve(problem)
    
    # Convert to appointments
    appointments = []
    for assignment in solution.assignments:
        appointments.append(Appointment(
            job_id=assignment.job.id,
            staff_id=assignment.staff.id,
            scheduled_date=date,
            time_window_start=assignment.start_time,
            time_window_end=assignment.end_time,
            route_order=assignment.order
        ))
    
    return Schedule(appointments=appointments)
```

### Google Maps Integration

#### Address Validation
```python
from google.maps import addressvalidation_v1

async def validate_address(address: str, city: str) -> ValidatedAddress:
    """Validate and geocode address."""
    client = addressvalidation_v1.AddressValidationClient()
    
    response = client.validate_address(
        address={
            "address_lines": [address],
            "locality": city,
            "administrative_area": "MN",
            "country_code": "US"
        }
    )
    
    return ValidatedAddress(
        formatted_address=response.result.address.formatted_address,
        latitude=response.result.geocode.location.latitude,
        longitude=response.result.geocode.location.longitude,
        is_valid=response.result.verdict.address_complete
    )
```

#### ETA Calculation
```python
from googlemaps import Client

async def calculate_eta(
    origin: tuple[float, float],
    destination: tuple[float, float]
) -> timedelta:
    """Calculate driving time between two points."""
    gmaps = Client(key=GOOGLE_MAPS_API_KEY)
    
    result = gmaps.directions(
        origin=origin,
        destination=destination,
        mode="driving",
        departure_time="now"
    )
    
    duration_seconds = result[0]["legs"][0]["duration_in_traffic"]["value"]
    return timedelta(seconds=duration_seconds)
```

---

## Security Architecture

### Authentication Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Client      │────►│   API Gateway   │────►│  Auth Service   │
│                 │     │                 │     │                 │
│ POST /auth/login│     │ Validate JWT    │     │ Issue JWT       │
│ {email, pass}   │     │ Extract claims  │     │ Verify password │
│                 │◄────│ Set user context│◄────│ Return tokens   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### JWT Structure
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "role": "admin",
  "exp": 1705420800,
  "iat": 1705334400
}
```

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| `admin` | Full access to all resources |
| `staff` | Read own schedule, update job status, update location |
| `sales` | Read/write estimates, read customers |
| `customer` | Read/write own data only |

### Data Protection

- **Passwords**: bcrypt hashing with salt
- **API Keys**: Encrypted at rest
- **PII**: Masked in logs
- **HTTPS**: Required in production
- **CORS**: Restricted to known origins

### Logging Security

```python
# Never log sensitive data
SENSITIVE_FIELDS = ["password", "token", "api_key", "card_number"]

def sanitize_log_data(data: dict) -> dict:
    """Remove sensitive fields from log data."""
    return {
        k: "***REDACTED***" if k in SENSITIVE_FIELDS else v
        for k, v in data.items()
    }
```

---

## Deployment Architecture

### Recommended Deployment Strategy

**For development and production, we recommend Railway + Vercel:**

- **Backend (Railway):** FastAPI, Celery workers, PostgreSQL, Redis
- **Frontend (Vercel):** All React dashboards, PWA, customer portal, public website
- **Deployment Time:** 15-30 minutes (after code is ready)
- **Monthly Cost:** $50-100 for full production system
- **Complexity:** Zero DevOps required - push to deploy

**📖 See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete step-by-step instructions.**

---

### Production Deployment Options

#### Option 1: Railway + Vercel (Recommended) ⭐

**Best for:** MVP, hackathon demos, small-to-medium scale (0-10,000 users)

**Backend (Railway):**
- Deploy directly from GitHub (automatic builds)
- Managed PostgreSQL and Redis (one-click add)
- Auto-scaling and automatic backups
- Built-in monitoring and logs
- Multiple services from one repo (API, workers, beat)
- Automatic HTTPS and health checks
- Cost: ~$20-50/month

**Frontend (Vercel):**
- Deploy from GitHub (automatic builds)
- Global CDN for fast loading worldwide
- Automatic HTTPS and SSL certificates
- Preview deployments for every PR
- Supports React, Next.js, PWA
- Free tier available for testing
- Cost: ~$0-20/month

**Total Cost:** $50-100/month  
**Setup Time:** 15-30 minutes  
**DevOps Required:** None  
**Scalability:** Handles 0-10,000+ users without code changes

**Why This Option:**
- ✅ Fastest deployment (push to deploy)
- ✅ Lowest cost for features provided
- ✅ Zero infrastructure management
- ✅ Perfect for hackathon judging (one-click deploy buttons)
- ✅ Production-ready with enterprise features
- ✅ Easy migration path to AWS if needed later

#### Option 2: Render

**Best for:** Alternative to Railway with similar features

- Similar feature set to Railway
- Free tier available for testing
- Managed databases included
- Slightly more configuration required
- Cost: ~$25-75/month for production

#### Option 3: AWS (ECS/Fargate)

**Best for:** Enterprise scale (10,000+ users), specific compliance requirements

- Maximum control and scalability
- Higher complexity (requires DevOps expertise)
- Manual infrastructure setup required
- Better for very large scale deployments
- Cost: ~$50-200/month depending on usage

**Migration Note:** Code is portable - can move from Railway to AWS later with minimal changes.

---

### Local Development

**Docker Compose is used for local development only:**

```yaml
# docker-compose.yml (for local development)
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  celery-worker:
    build: .
    command: celery -A grins_platform.tasks worker -l info
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A grins_platform.tasks beat -l info
    depends_on:
      - redis

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=grins
      - POSTGRES_USER=grins
      - POSTGRES_PASSWORD=...

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Note:** Do not use Docker Compose for production deployment. Use Railway/Vercel instead for automatic scaling, backups, monitoring, and zero-downtime deployments.

### Environment Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # Auth
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    
    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str
    
    # Google
    google_maps_api_key: str
    
    # Environment
    environment: str = "development"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
```

---

## Phase Implementation Details

### Phase 1: Foundation (Weeks 1-4)

**Focus:** Core CRM and job tracking to replace spreadsheet

#### Deliverables
| Component | Description |
|-----------|-------------|
| Database Schema | All tables for Phase 1 entities |
| Customer Service | Full CRUD with flags, preferences |
| Property Service | Property management with geocoding |
| Job Service | Job intake, categorization, status workflow |
| Service Catalog | Service offerings with pricing |
| Basic API | All Phase 1 endpoints |
| Admin Dashboard API | Metrics and overview endpoints |
| Authentication | JWT-based auth with roles |

#### Database Tables
- customers
- properties
- service_offerings
- jobs
- staff (basic)

#### API Endpoints (25+)
- Customer CRUD (8 endpoints)
- Property CRUD (5 endpoints)
- Job CRUD + workflow (10 endpoints)
- Service catalog (3 endpoints)
- Dashboard (4 endpoints)
- Auth (3 endpoints)

### Phase 2: Field Operations (Weeks 5-8)

**Focus:** Staff PWA with offline capability

#### Deliverables
| Component | Description |
|-----------|-------------|
| Staff Service | Full staff management |
| Appointment Service | Scheduling and assignment |
| GPS Tracking | Location updates and history |
| Job Completion Workflow | Enforced sequential steps |
| Staff PWA | Offline-first mobile app |
| Notification Service | Basic SMS notifications |

#### Database Tables
- appointments
- staff_locations
- notifications

#### PWA Features
- Daily route view
- Job cards with all info
- Offline data sync
- Photo capture
- Job completion form
- GPS tracking

#### Notifications
- Appointment confirmation
- Day-before reminder
- On-the-way notification
- Arrival notification
- Completion summary

### Phase 3: Customer Communication (Weeks 9-12)

**Focus:** AI chat agent and automated SMS

#### Deliverables
- Pydantic AI chat agent
- Two-way SMS with Twilio
- Automated appointment reminders
- Customer notification preferences
- Escalation to human

### Phase 4: Scheduling & Payments (Weeks 13-16)

**Focus:** Route optimization and invoice automation

#### Deliverables
- Timefold route optimization
- One-click schedule generation
- Stripe invoicing integration
- Payment tracking
- Automated invoice reminders
- Lien workflow

### Phase 5: Customer Self-Service & Sales (Weeks 17-20)

**Focus:** Customer portal and Sales Dashboard

#### Deliverables
- Customer portal (booking, payments, history)
- Sales Dashboard
- Estimate pipeline management
- Follow-up automation
- E-signature for contracts

### Phase 6: Accounting & Marketing (Weeks 21-24)

**Focus:** Financial dashboards and marketing automation

#### Deliverables
- Accounting Dashboard
- Expense tracking
- Receipt OCR
- Tax preparation
- Marketing Dashboard
- Campaign management
- Lead source attribution

### Phase 7: Website & Growth (Weeks 25-28)

**Focus:** Public website optimization

#### Deliverables
- Next.js public website
- SEO optimization
- Instant quote calculator
- System design tool
- Social media integration

---

## Appendix: Business Rules

### Job Categorization Rules

| Condition | Category |
|-----------|----------|
| Seasonal service (startup, tune-up, winterization) | Ready to Schedule |
| Small repair with known scope | Ready to Schedule |
| Approved estimate | Ready to Schedule |
| Partner/builder deal | Ready to Schedule |
| New system install | Requires Estimate |
| Unknown repair scope | Requires Estimate |
| Diagnostic needed | Requires Estimate |
| New commercial client | Requires Estimate |

### Pricing Rules

| Service | Pricing Model | Example |
|---------|---------------|---------|
| Spring Startup | Zone-based | $X per zone |
| Summer Tune-up | Zone-based | $X per zone |
| Winterization | Zone-based | $X per zone |
| Small Repair | Flat rate | $50 per head |
| Diagnostic | Hourly | $100 first hour |
| Installation | Zone-based | $700 per zone (partner) |

### Lien Eligibility Rules

| Service Type | Lien Eligible | Prepay Required |
|--------------|---------------|-----------------|
| System installs | ✅ Yes | No |
| Major repairs | ✅ Yes | No |
| Landscaping | ✅ Yes | No |
| Spring startups | ❌ No | Yes |
| Summer tune-ups | ❌ No | Yes |
| Winterizations | ❌ No | Yes |
| Diagnostics | ❌ No | Yes |

### Lien Timeline
- **45 days**: Send lien warning notification
- **120 days**: File formal lien (if still unpaid)

### Time Estimation Rules

| Job Type | System Type | Duration |
|----------|-------------|----------|
| Seasonal Service | Standard Residential | 30-60 min |
| Seasonal Service | Commercial/Lake Pump | 60-120 min |
| Small Repair | Any | 30 min |
| Diagnostic | Any | 60+ min |
| Major Repair | Any | 2-4 hours |
| Installation | Any | 1+ days |

### Staffing Requirements

| Job Type | Staff Needed |
|----------|--------------|
| Seasonal Service | 1 |
| Small Repair | 1 |
| Diagnostic | 1 |
| Major Repair | 2 |
| Installation | 2-4 |
| Landscaping | 2-4 |

### Equipment Requirements

| Job Type | Equipment |
|----------|-----------|
| Winterization | Compressor |
| Major Repair | Pipe puller |
| Installation | Pipe puller, utility trailer |
| Landscaping | Pipe puller, skid steer, utility trailer, dump trailer |

---

*This architecture document serves as the definitive technical reference for the Grin's Irrigation Platform.*
