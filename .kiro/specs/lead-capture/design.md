# Design Document: Lead Capture (Website Form Submission)

## Introduction

This document provides the technical design for the Lead Capture feature of Grin's Irrigation Platform. It defines the database schema, API endpoints, service layer architecture, frontend components, and correctness properties that will fulfill the requirements specified in requirements.md.

The feature enables the platform to receive leads from the public-facing landing page form, store them in a dedicated `leads` table, manage them through a status workflow, convert them to customers, and surface lead activity on the admin dashboard.

## Design Overview

The Lead Capture feature follows the existing layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  FastAPI endpoints: public POST + admin CRUD + conversion    │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                             │
│  LeadService with LoggerMixin for business logic             │
│  (honeypot, duplicate detection, conversion, status workflow)│
├─────────────────────────────────────────────────────────────┤
│                   Repository Layer                           │
│  LeadRepository for database operations                      │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                            │
│  PostgreSQL with SQLAlchemy async models (leads table)       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React)                           │
│  Leads feature slice: list, detail, conversion dialog,       │
│  dashboard widget, navigation tab                            │
└─────────────────────────────────────────────────────────────┘
```

Cross-cutting concerns:
- **Dashboard Integration**: DashboardService and DashboardMetrics schema extended with lead counts
- **Exception Handling**: New lead-specific exceptions registered as global handlers in app.py
- **Logging**: Structured logging with "lead" domain namespace, no PII


## Database Schema

### leads Table

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    zip_code VARCHAR(10) NOT NULL,
    situation VARCHAR(50) NOT NULL,       -- enum: new_system, upgrade, repair, exploring
    notes TEXT,
    source_site VARCHAR(100) NOT NULL DEFAULT 'residential',
    status VARCHAR(20) NOT NULL DEFAULT 'new',  -- enum: new, contacted, qualified, converted, lost, spam
    assigned_to UUID REFERENCES staff(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    contacted_at TIMESTAMP WITH TIME ZONE,
    converted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX idx_leads_phone ON leads(phone);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at);
CREATE INDEX idx_leads_zip_code ON leads(zip_code);
```

### Relationships

- `assigned_to` → `staff.id` (nullable FK, ON DELETE SET NULL)
- `customer_id` → `customers.id` (nullable FK, ON DELETE SET NULL, populated on conversion)

## Enums

Add to `src/grins_platform/models/enums.py`:

```python
# =============================================================================
# Lead Capture Enums
# =============================================================================

class LeadStatus(str, Enum):
    """Lead status enumeration for pipeline tracking.

    Validates: Lead Capture Requirement 4.4
    """
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"
    SPAM = "spam"


class LeadSituation(str, Enum):
    """Lead situation enumeration mapping to form dropdown options.

    Validates: Lead Capture Requirement 4.5
    """
    NEW_SYSTEM = "new_system"
    UPGRADE = "upgrade"
    REPAIR = "repair"
    EXPLORING = "exploring"
```

### Status Transition Map

```python
VALID_LEAD_STATUS_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW: {LeadStatus.CONTACTED, LeadStatus.QUALIFIED, LeadStatus.LOST, LeadStatus.SPAM},
    LeadStatus.CONTACTED: {LeadStatus.QUALIFIED, LeadStatus.LOST, LeadStatus.SPAM},
    LeadStatus.QUALIFIED: {LeadStatus.CONVERTED, LeadStatus.LOST},
    LeadStatus.CONVERTED: set(),   # terminal
    LeadStatus.LOST: {LeadStatus.NEW},  # re-engagement
    LeadStatus.SPAM: set(),        # terminal
}
```


## API Endpoints

### Lead Endpoints

| Method | Endpoint | Auth | Description | Request Body | Response |
|--------|----------|------|-------------|--------------|----------|
| POST | `/api/v1/leads` | **Public** | Submit lead from form | LeadSubmission | LeadSubmissionResponse (201) |
| GET | `/api/v1/leads` | Admin | List leads with filters | Query params | PaginatedLeadResponse |
| GET | `/api/v1/leads/{id}` | Admin | Get lead by ID | - | LeadResponse |
| PATCH | `/api/v1/leads/{id}` | Admin | Update lead | LeadUpdate | LeadResponse |
| POST | `/api/v1/leads/{id}/convert` | Admin | Convert lead to customer | LeadConversionRequest | LeadConversionResponse |
| DELETE | `/api/v1/leads/{id}` | Admin | Delete lead | - | 204 No Content |

### Public Endpoint Contract

**Request:**
```json
POST /api/v1/leads
Content-Type: application/json

{
  "name": "John Doe",
  "phone": "(612) 555-0123",
  "zip_code": "55424",
  "situation": "new_system",
  "email": "john@example.com",
  "notes": "I have a large backyard",
  "source_site": "residential",
  "website": ""
}
```

**Success Response:**
```json
HTTP 201 Created
{
  "success": true,
  "message": "Thank you! We'll be in touch within 24 hours.",
  "lead_id": "uuid-here"
}
```

**Validation Error Response:**
```json
HTTP 422 Unprocessable Entity
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [...]
  }
}
```

## Pydantic Schemas

### Lead Schemas (`schemas/lead.py`)

```python
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from grins_platform.models.enums import LeadSituation, LeadStatus
from grins_platform.schemas.customer import normalize_phone


def strip_html_tags(text: str) -> str:
    """Strip HTML tags from text to prevent stored XSS.

    Args:
        text: Input string potentially containing HTML tags

    Returns:
        String with all HTML tags removed

    Validates: Requirement 1.11, 12.4
    """
    return re.sub(r"<[^>]+>", "", text).strip()


class LeadSubmission(BaseModel):
    """Schema for public form submission.

    Validates: Requirement 1
    """
    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    phone: str = Field(..., min_length=7, max_length=20, description="Phone number")
    zip_code: str = Field(..., min_length=5, max_length=10, description="5-digit zip code")
    situation: LeadSituation = Field(..., description="Service situation from dropdown")
    email: EmailStr | None = Field(default=None, description="Optional email address")
    notes: str | None = Field(default=None, max_length=1000, description="Optional notes")
    source_site: str = Field(default="residential", max_length=100, description="Source site identifier")
    website: str | None = Field(default=None, description="Honeypot field — must be empty")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone to 10 digits."""
        return normalize_phone(v)

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, v: str) -> str:
        """Validate 5-digit zip code."""
        digits = "".join(filter(str.isdigit, v))
        if len(digits) != 5:
            raise ValueError("Zip code must be exactly 5 digits")
        return digits

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Strip HTML tags and whitespace from name."""
        return strip_html_tags(v)

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        """Strip HTML tags from notes if provided."""
        if v is None:
            return None
        sanitized = strip_html_tags(v)
        return sanitized if sanitized else None


class LeadSubmissionResponse(BaseModel):
    """Response for public lead submission.

    Validates: Requirement 1.1
    """
    success: bool = True
    message: str = "Thank you! We'll be in touch within 24 hours."
    lead_id: UUID | None = None


class LeadUpdate(BaseModel):
    """Schema for admin lead updates.

    Validates: Requirement 5
    """
    status: LeadStatus | None = Field(default=None, description="New status")
    assigned_to: UUID | None = Field(default=None, description="Staff member UUID")
    notes: str | None = Field(default=None, max_length=1000, description="Updated notes")

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return strip_html_tags(v)


class LeadResponse(BaseModel):
    """Full lead response for admin endpoints.

    Validates: Requirement 5.8
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    email: str | None
    zip_code: str
    situation: LeadSituation
    notes: str | None
    source_site: str
    status: LeadStatus
    assigned_to: UUID | None
    customer_id: UUID | None
    contacted_at: datetime | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("status", mode="before")
    @classmethod
    def convert_status(cls, v: str | LeadStatus) -> LeadStatus:
        if isinstance(v, str):
            return LeadStatus(v)
        return v

    @field_validator("situation", mode="before")
    @classmethod
    def convert_situation(cls, v: str | LeadSituation) -> LeadSituation:
        if isinstance(v, str):
            return LeadSituation(v)
        return v


class LeadListParams(BaseModel):
    """Query parameters for listing leads.

    Validates: Requirement 5.1-5.5
    """
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    status: LeadStatus | None = None
    situation: LeadSituation | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class PaginatedLeadResponse(BaseModel):
    """Paginated lead list response.

    Validates: Requirement 5.1
    """
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LeadConversionRequest(BaseModel):
    """Request body for converting a lead to a customer.

    Validates: Requirement 7
    """
    first_name: str | None = Field(default=None, max_length=100, description="Override auto-split first name")
    last_name: str | None = Field(default=None, max_length=100, description="Override auto-split last name")
    create_job: bool = Field(default=True, description="Whether to create a job during conversion")
    job_description: str | None = Field(default=None, max_length=500, description="Optional job description override")


class LeadConversionResponse(BaseModel):
    """Response for lead conversion.

    Validates: Requirement 7.6
    """
    success: bool = True
    lead_id: UUID
    customer_id: UUID
    job_id: UUID | None = None
    message: str = "Lead converted successfully"
```


## SQLAlchemy Model

### Lead Model (`models/lead.py`)

```python
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from grins_platform.database import Base


class Lead(Base):
    """Lead database model for website form submissions.

    Validates: Requirement 4
    """
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(255), nullable=True)
    zip_code = Column(String(10), nullable=False)
    situation = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    source_site = Column(String(100), nullable=False, server_default="residential")
    status = Column(String(20), nullable=False, server_default="new")
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    contacted_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    staff = relationship("Staff", foreign_keys=[assigned_to], lazy="selectin")
    customer = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")

    __table_args__ = (
        Index("idx_leads_phone", "phone"),
        Index("idx_leads_status", "status"),
        Index("idx_leads_created_at", "created_at"),
        Index("idx_leads_zip_code", "zip_code"),
    )
```

## Repository Layer

### LeadRepository (`repositories/lead_repository.py`)

```python
from grins_platform.log_config import LoggerMixin

class LeadRepository(LoggerMixin):
    """Repository for lead database operations.

    Validates: Requirement 4, 5
    """
    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        super().__init__()
        self.session = session

    async def create(self, **kwargs) -> Lead:
        """Create a new lead record."""

    async def get_by_id(self, lead_id: UUID) -> Lead | None:
        """Get lead by UUID."""

    async def get_by_phone_and_active_status(self, phone: str) -> Lead | None:
        """Find existing lead by phone with status in (new, contacted, qualified).
        Used for duplicate detection.
        """

    async def list_with_filters(self, params: LeadListParams) -> tuple[list[Lead], int]:
        """List leads with filtering, search, and pagination.
        Returns (items, total_count).
        Supports: status, situation, date_from, date_to, search (name/phone).
        """

    async def update(self, lead_id: UUID, update_data: dict) -> Lead:
        """Update lead fields. Returns updated lead."""

    async def delete(self, lead_id: UUID) -> None:
        """Hard delete a lead record."""

    async def count_new_today(self) -> int:
        """Count leads submitted today with status 'new'. For dashboard metrics."""

    async def count_uncontacted(self) -> int:
        """Count all leads with status 'new'. For dashboard metrics."""
```

## Service Layer

### LeadService (`services/lead_service.py`)

```python
from grins_platform.log_config import LoggerMixin

class LeadService(LoggerMixin):
    """Service for lead management business logic.

    Validates: Requirements 1-8, 13, 15
    """
    DOMAIN = "lead"

    def __init__(
        self,
        lead_repository: LeadRepository,
        customer_service: CustomerService,
        job_service: JobService,
        staff_repository: StaffRepository,
    ) -> None:
        super().__init__()
        self.lead_repository = lead_repository
        self.customer_service = customer_service
        self.job_service = job_service
        self.staff_repository = staff_repository

    async def submit_lead(self, data: LeadSubmission) -> LeadSubmissionResponse:
        """Process a public form submission.

        Steps:
        1. Check honeypot — if filled, return fake 201 without storing
        2. Phone is already normalized by schema validator
        3. Check for duplicate by phone + active status
        4. If duplicate found (new/contacted/qualified): update existing lead
        5. If no duplicate or existing is converted/lost/spam: create new lead
        6. Log lead.submitted event (lead_id + source_site only, no PII)

        Validates: Requirements 1, 2, 3, 15
        """

    async def get_lead(self, lead_id: UUID) -> LeadResponse:
        """Get a single lead by ID.

        Raises: LeadNotFoundError if not found.
        Validates: Requirement 5.8
        """

    async def list_leads(self, params: LeadListParams) -> PaginatedLeadResponse:
        """List leads with filtering and pagination.

        Validates: Requirement 5.1-5.5
        """

    async def update_lead(self, lead_id: UUID, data: LeadUpdate) -> LeadResponse:
        """Update a lead's status, assignment, or notes.

        Status change logic:
        - Validate transition against VALID_LEAD_STATUS_TRANSITIONS
        - If new status is 'contacted' and contacted_at is null: set contacted_at
        - If new status is 'converted': set converted_at
        - If assigning to staff: validate staff exists via staff_repository

        Raises: LeadNotFoundError, InvalidLeadStatusTransitionError, StaffNotFoundError
        Validates: Requirements 5.6-5.7, 6
        """

    async def convert_lead(self, lead_id: UUID, data: LeadConversionRequest) -> LeadConversionResponse:
        """Convert a lead to a customer and optionally a job.

        Steps:
        1. Fetch lead, verify not already converted (raise LeadAlreadyConvertedError)
        2. Split name into first/last (or use overrides from request)
        3. Create customer via CustomerService with source="website"
        4. If create_job=True: create job via JobService with category/description mapped from situation
        5. Update lead: status=converted, converted_at=now(), customer_id=new customer ID
        6. Log lead.converted event

        Name splitting:
        - "John Doe" → first="John", last="Doe"
        - "John Michael Doe" → first="John", last="Michael Doe"
        - "Viktor" → first="Viktor", last=""

        Situation → Job mapping:
        - new_system → requires_estimate, "Installation Estimate"
        - upgrade → requires_estimate, "System Upgrade Estimate"
        - repair → ready_to_schedule, "Repair Request"
        - exploring → requires_estimate, "Consultation"

        Raises: LeadNotFoundError, LeadAlreadyConvertedError, DuplicateCustomerError
        Validates: Requirement 7
        """

    async def delete_lead(self, lead_id: UUID) -> None:
        """Delete a lead record.

        Raises: LeadNotFoundError
        Validates: Requirement 5.9
        """

    async def get_dashboard_metrics(self) -> dict[str, int]:
        """Get lead metrics for dashboard integration.

        Returns: {"new_leads_today": int, "uncontacted_leads": int}
        Validates: Requirement 8
        """

    @staticmethod
    def split_name(full_name: str) -> tuple[str, str]:
        """Split full name into (first_name, last_name).

        Validates: Requirement 7.1-7.2
        """
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        return first_name, last_name
```


## API Layer

### Lead Endpoints (`api/v1/leads.py`)

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.api.v1.dependencies import get_current_user, get_db_session
from grins_platform.schemas.lead import (
    LeadConversionRequest,
    LeadConversionResponse,
    LeadListParams,
    LeadResponse,
    LeadSubmission,
    LeadSubmissionResponse,
    LeadUpdate,
    PaginatedLeadResponse,
)

router = APIRouter()


# --- Public endpoint (NO auth) ---

@router.post(
    "",
    response_model=LeadSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a lead from the website form",
)
async def submit_lead(
    data: LeadSubmission,
    session: AsyncSession = Depends(get_db_session),
) -> LeadSubmissionResponse:
    """Public endpoint for website form submissions. No authentication required."""
    service = _get_lead_service(session)
    return await service.submit_lead(data)


# --- Admin endpoints (require auth) ---

@router.get(
    "",
    response_model=PaginatedLeadResponse,
    summary="List leads with filters",
)
async def list_leads(
    params: LeadListParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> PaginatedLeadResponse:
    service = _get_lead_service(session)
    return await service.list_leads(params)


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead by ID",
)
async def get_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> LeadResponse:
    service = _get_lead_service(session)
    return await service.get_lead(lead_id)


@router.patch(
    "/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead status, assignment, or notes",
)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> LeadResponse:
    service = _get_lead_service(session)
    return await service.update_lead(lead_id, data)


@router.post(
    "/{lead_id}/convert",
    response_model=LeadConversionResponse,
    summary="Convert lead to customer and optionally a job",
)
async def convert_lead(
    lead_id: UUID,
    data: LeadConversionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> LeadConversionResponse:
    service = _get_lead_service(session)
    return await service.convert_lead(lead_id, data)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lead",
)
async def delete_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> None:
    service = _get_lead_service(session)
    await service.delete_lead(lead_id)
```

### Router Registration (`api/v1/router.py`)

Add to the existing router:

```python
from grins_platform.api.v1.leads import router as leads_router

# Include lead endpoints
api_router.include_router(
    leads_router,
    prefix="/leads",
    tags=["leads"],
)
```

## Error Handling

### Custom Exceptions

Add to `src/grins_platform/exceptions/__init__.py`:

```python
# ============================================================================
# Lead Capture Exceptions
# ============================================================================

class LeadError(Exception):
    """Base exception for lead operations."""


class LeadNotFoundError(LeadError):
    """Raised when a lead is not found.

    Validates: Requirement 13.1
    """
    def __init__(self, lead_id: UUID) -> None:
        self.lead_id = lead_id
        super().__init__(f"Lead not found: {lead_id}")


class LeadAlreadyConvertedError(LeadError):
    """Raised when attempting to convert an already-converted lead.

    Validates: Requirement 13.2
    """
    def __init__(self, lead_id: UUID) -> None:
        self.lead_id = lead_id
        super().__init__(f"Lead already converted: {lead_id}")


class InvalidLeadStatusTransitionError(LeadError):
    """Raised when an invalid lead status transition is attempted.

    Validates: Requirement 13.3
    """
    def __init__(self, current_status: LeadStatus, requested_status: LeadStatus) -> None:
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Invalid lead status transition from {current_status.value} to {requested_status.value}"
        )
```

### Exception Handlers in `app.py`

Register three new handlers following the existing pattern:

```python
@app.exception_handler(LeadNotFoundError)
async def lead_not_found_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"success": False, "error": {"code": "LEAD_NOT_FOUND", "message": str(exc), "lead_id": str(exc.lead_id)}},
    )

@app.exception_handler(LeadAlreadyConvertedError)
async def lead_already_converted_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": {"code": "LEAD_ALREADY_CONVERTED", "message": str(exc), "lead_id": str(exc.lead_id)}},
    )

@app.exception_handler(InvalidLeadStatusTransitionError)
async def invalid_lead_status_transition_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"success": False, "error": {"code": "INVALID_LEAD_STATUS_TRANSITION", "message": str(exc), "current_status": exc.current_status.value, "requested_status": exc.requested_status.value}},
    )
```


## Dashboard Integration

### Schema Changes (`schemas/dashboard.py`)

Add two fields to `DashboardMetrics`:

```python
class DashboardMetrics(BaseModel):
    # ... existing fields ...
    new_leads_today: int = Field(default=0, description="Leads submitted today with status 'new'")
    uncontacted_leads: int = Field(default=0, description="All leads with status 'new'")
```

Add `"lead_submitted"` as a valid `activity_type` value in `RecentActivityItem` (no schema change needed — it's already a free string field).

### Service Changes (`services/dashboard_service.py`)

In `get_overview_metrics()`, add lead metric queries:

```python
# Get lead counts (requires LeadRepository injected into DashboardService)
new_leads_today = await self.lead_repository.count_new_today()
uncontacted_leads = await self.lead_repository.count_uncontacted()

metrics = DashboardMetrics(
    # ... existing fields ...
    new_leads_today=new_leads_today,
    uncontacted_leads=uncontacted_leads,
)
```

DashboardService constructor gains a `lead_repository: LeadRepository` parameter.

## Frontend Design

### Feature Slice Structure

```
frontend/src/features/leads/
├── components/
│   ├── LeadsList.tsx              # Main list page with table + filters
│   ├── LeadDetail.tsx             # Lead detail view with actions
│   ├── LeadStatusBadge.tsx        # Color-coded status badge
│   ├── LeadSituationBadge.tsx     # Situation label badge
│   ├── ConvertLeadDialog.tsx      # Conversion modal
│   └── LeadFilters.tsx            # Filter bar component
├── hooks/
│   ├── useLeads.ts                # TanStack Query hook for list
│   ├── useLead.ts                 # TanStack Query hook for single lead
│   ├── useUpdateLead.ts           # Mutation hook for status/assignment
│   └── useConvertLead.ts          # Mutation hook for conversion
├── api/
│   └── leadApi.ts                 # API client functions
├── types/
│   └── index.ts                   # Lead TypeScript types
└── index.ts                       # Public exports
```

### TypeScript Types (`types/index.ts`)

```typescript
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'converted' | 'lost' | 'spam';
export type LeadSituation = 'new_system' | 'upgrade' | 'repair' | 'exploring';

export interface Lead {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  zip_code: string;
  situation: LeadSituation;
  notes: string | null;
  source_site: string;
  status: LeadStatus;
  assigned_to: string | null;
  customer_id: string | null;
  contacted_at: string | null;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadListParams {
  page?: number;
  page_size?: number;
  status?: LeadStatus;
  situation?: LeadSituation;
  search?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedLeadResponse {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface LeadConversionRequest {
  first_name?: string;
  last_name?: string;
  create_job?: boolean;
  job_description?: string;
}

export interface LeadConversionResponse {
  success: boolean;
  lead_id: string;
  customer_id: string;
  job_id: string | null;
  message: string;
}
```

### Query Key Factory

```typescript
export const leadKeys = {
  all: ['leads'] as const,
  lists: () => [...leadKeys.all, 'list'] as const,
  list: (params: LeadListParams) => [...leadKeys.lists(), params] as const,
  details: () => [...leadKeys.all, 'detail'] as const,
  detail: (id: string) => [...leadKeys.details(), id] as const,
};
```

### API Client (`api/leadApi.ts`)

```typescript
import { apiClient } from '@/core/api/client';

export const leadApi = {
  list: (params?: LeadListParams) => apiClient.get('/leads', { params }).then(r => r.data),
  getById: (id: string) => apiClient.get(`/leads/${id}`).then(r => r.data),
  update: (id: string, data: Partial<Lead>) => apiClient.patch(`/leads/${id}`, data).then(r => r.data),
  convert: (id: string, data: LeadConversionRequest) => apiClient.post(`/leads/${id}/convert`, data).then(r => r.data),
  delete: (id: string) => apiClient.delete(`/leads/${id}`),
};
```

### Status Badge Colors

```typescript
const leadStatusColors: Record<LeadStatus, string> = {
  new: 'bg-blue-100 text-blue-800',
  contacted: 'bg-yellow-100 text-yellow-800',
  qualified: 'bg-purple-100 text-purple-800',
  converted: 'bg-green-100 text-green-800',
  lost: 'bg-gray-100 text-gray-800',
  spam: 'bg-red-100 text-red-800',
};
```

### Router Integration

Add to `frontend/src/core/router/index.tsx`:

```typescript
import { LeadsList } from '@/features/leads/components/LeadsList';
import { LeadDetail } from '@/features/leads/components/LeadDetail';

// Inside route definitions:
{ path: '/leads', element: <LeadsList /> },
{ path: '/leads/:id', element: <LeadDetail /> },
```

### Navigation Tab

Add "Leads" to the sidebar navigation in `Layout.tsx` with a funnel icon (`Funnel` from lucide-react) and a badge showing the count of `new` leads (fetched from dashboard metrics `uncontacted_leads`).

### Dashboard Widget

Add a "New Leads" card to `DashboardPage.tsx` in the metrics grid:

```typescript
<MetricsCard
  title="New Leads"
  value={metrics?.new_leads_today ?? 0}
  description={`${metrics?.uncontacted_leads ?? 0} uncontacted`}
  icon={Funnel}
  variant="amber"
  testId="leads-metric"
  onClick={() => navigate('/leads?status=new')}
/>
```

Color-coding for the card:
- Green: 0 uncontacted leads
- Yellow: 1-5 uncontacted leads
- Red: 6+ uncontacted leads


## Correctness Properties

These properties define formal invariants that must hold across all inputs. They will be validated using property-based testing with Hypothesis.

### Property 1: Phone Normalization Idempotency
**Validates: Requirement 1.2**

For any phone string `p` that normalizes successfully, `normalize(normalize(p)) == normalize(p)`.

The normalization function strips non-digit characters and validates 10-digit North American format. Applying it twice must produce the same result as applying it once.

**Testing framework:** Hypothesis
**Strategy:** Generate strings of digits, parentheses, dashes, spaces, and dots of varying lengths. Filter to those that produce valid 10-digit results.

### Property 2: Status Transition Validity
**Validates: Requirement 6.2-6.3**

For any `(current_status, new_status)` pair from the `LeadStatus` enum:
- If `new_status` is in `VALID_LEAD_STATUS_TRANSITIONS[current_status]`, the transition succeeds
- If `new_status` is NOT in `VALID_LEAD_STATUS_TRANSITIONS[current_status]`, the transition raises `InvalidLeadStatusTransitionError`
- Terminal states (`converted`, `spam`) have empty transition sets

**Testing framework:** Hypothesis
**Strategy:** Generate all combinations of `(LeadStatus, LeadStatus)` pairs and verify each against the transition map.

### Property 3: Duplicate Detection Correctness
**Validates: Requirement 3.1-3.5**

For any lead submission with phone `p`:
- If an existing lead with phone `p` has status in `{new, contacted, qualified}`, the total lead count does NOT increase (existing lead is updated)
- If an existing lead with phone `p` has status in `{converted, lost, spam}`, the total lead count increases by 1 (new lead created)
- If no existing lead has phone `p`, the total lead count increases by 1

**Testing framework:** Hypothesis
**Strategy:** Generate sequences of (phone, status) pairs and verify lead count invariants after each submission.

### Property 4: Input Sanitization Completeness
**Validates: Requirement 1.11, 12.4**

For any string `s`, `strip_html_tags(strip_html_tags(s)) == strip_html_tags(s)` (idempotency).

Additionally, for any string `s`, the result of `strip_html_tags(s)` contains no substrings matching `<[^>]+>`.

**Testing framework:** Hypothesis
**Strategy:** Generate arbitrary strings including HTML-like patterns (`<tag>`, `<script>alert(1)</script>`, etc.) and verify both idempotency and absence of tags in output.

### Property 5: Name Splitting Roundtrip Consistency
**Validates: Requirement 7.1-7.2**

For any non-empty name string `n`:
- `split_name(n)` returns `(first, last)` where `first` is non-empty
- `first + " " + last` (stripped) reconstructs a string that, when split again, produces the same `(first, last)`
- Single-word names produce `(word, "")`

**Testing framework:** Hypothesis
**Strategy:** Generate name strings with 1-4 space-separated words and verify split consistency.

### Property 6: Honeypot Transparency
**Validates: Requirement 2.1, 2.4**

For any valid lead submission data `d`:
- Submitting with `website=""` returns `{"success": true}` and creates a lead
- Submitting with `website="anything"` returns `{"success": true}` and does NOT create a lead
- The response shape is identical in both cases (no information leakage)

**Testing framework:** Hypothesis
**Strategy:** Generate valid submission payloads, submit with empty and non-empty honeypot values, verify response shape equality and storage behavior difference.

## Testing Strategy

### Testing Framework
- **Backend:** pytest + pytest-asyncio + Hypothesis (PBT)
- **Frontend:** Vitest + React Testing Library
- **E2E:** agent-browser (MANDATORY for all frontend-facing features)

### Agent-Browser Validation Principle

Every frontend component and user-facing flow MUST be validated with agent-browser before the feature is considered complete. This includes:
1. Submitting the actual form on the live landing page (`https://grins-irrigation.vercel.app/`)
2. Verifying the submitted lead appears in the admin dashboard
3. Testing all CRUD operations through the admin UI
4. Verifying dashboard widget counts and navigation
5. Testing the full conversion flow from lead → customer

### Three-Tier Backend Testing

| Tier | Type | Scope | Marker |
|------|------|-------|--------|
| 1 | Unit | LeadService methods with mocked repository, schema validation, name splitting, sanitization | `@pytest.mark.unit` |
| 2 | Functional | Full lead lifecycle with real test database: submit → list → update → convert | `@pytest.mark.functional` |
| 3 | Integration | Cross-component: lead submission → dashboard metrics update, lead conversion → customer creation | `@pytest.mark.integration` |

### Property-Based Tests

| Property | Module | Description |
|----------|--------|-------------|
| P1 | `test_lead_pbt.py` | Phone normalization idempotency |
| P2 | `test_lead_pbt.py` | Status transition validity (all enum pairs) |
| P3 | `test_lead_pbt.py` | Duplicate detection lead count invariants |
| P4 | `test_lead_pbt.py` | HTML sanitization idempotency + completeness |
| P5 | `test_lead_pbt.py` | Name splitting consistency |
| P6 | `test_lead_pbt.py` | Honeypot transparency (response shape equality) |

### Frontend Tests

| Component | Test File | Coverage |
|-----------|-----------|----------|
| LeadsList | `LeadsList.test.tsx` | Rendering, filtering, pagination, row click |
| LeadDetail | `LeadDetail.test.tsx` | Rendering, status change, action buttons |
| ConvertLeadDialog | `ConvertLeadDialog.test.tsx` | Name pre-fill, form submission, job toggle |
| LeadStatusBadge | `LeadStatusBadge.test.tsx` | Color mapping for all statuses |
| useLeads / useLead | `hooks.test.ts` | Query behavior, cache invalidation |
| useConvertLead | `hooks.test.ts` | Mutation behavior, success/error handling |

### Agent-Browser E2E Validation

All frontend-facing features MUST be validated using agent-browser. This includes submitting the actual public form on the live landing page and verifying the result flows through to the admin dashboard.

| Scenario | Steps |
|----------|-------|
| **Public form submission (live site)** | `agent-browser open https://grins-irrigation.vercel.app/` → scroll to "Get Your Free Design" form → fill name, phone, zip code, select situation → submit → verify success message appears on the page |
| **Lead appears in admin dashboard** | `agent-browser open http://localhost:5173/leads` → verify the lead just submitted from the live form appears in the leads table with status "new" and correct data |
| **Dashboard widget reflects new lead** | `agent-browser open http://localhost:5173/` → verify "New Leads" card shows updated count → click card → verify navigation to leads list filtered by status=new |
| **Lead detail view** | Navigate to a lead's detail page → verify all fields render (name, phone, email, zip, situation, notes, status, timestamps) → verify action buttons present |
| **Lead status change** | Open lead detail → change status to "contacted" → verify status badge updates → verify contacted_at timestamp appears |
| **Lead conversion flow** | Open a qualified lead → click "Convert to Customer" → verify dialog pre-fills first/last name from auto-split → toggle job creation → submit → verify navigation to new customer detail page |
| **Converted lead shows links** | Return to the converted lead's detail page → verify status shows "converted" → verify links to created customer and job are visible and clickable |
| **Lead filtering and search** | On leads list page → filter by status → verify table updates → search by name → verify results → filter by situation → verify results |
| **Lead deletion** | Open a spam/test lead → delete it → verify it disappears from the list |

**Key principle:** The live landing page form at `https://grins-irrigation.vercel.app/` submits to the backend API. Agent-browser validation must prove the full round-trip: public form → API → database → admin dashboard display.

### Coverage Targets

| Component | Target |
|-----------|--------|
| LeadService | 85%+ |
| LeadRepository | 80%+ |
| API endpoints | 80%+ |
| Frontend components | 80%+ |

## File Structure (All New Files)

```
src/grins_platform/
├── models/
│   ├── enums.py                          # ADD: LeadStatus, LeadSituation enums
│   └── lead.py                           # NEW: Lead SQLAlchemy model
├── schemas/
│   ├── lead.py                           # NEW: All lead Pydantic schemas
│   └── dashboard.py                      # MODIFY: Add new_leads_today, uncontacted_leads
├── repositories/
│   └── lead_repository.py                # NEW: LeadRepository
├── services/
│   ├── lead_service.py                   # NEW: LeadService
│   └── dashboard_service.py              # MODIFY: Add lead_repository, query lead metrics
├── api/v1/
│   ├── leads.py                          # NEW: Lead API endpoints
│   └── router.py                         # MODIFY: Register leads router
├── exceptions/
│   └── __init__.py                       # MODIFY: Add LeadError, LeadNotFoundError, etc.
├── app.py                                # MODIFY: Register lead exception handlers
├── migrations/versions/
│   └── YYYYMMDD_HHMMSS_create_leads_table.py  # NEW: Alembic migration
└── tests/
    ├── unit/
    │   └── test_lead_service.py          # NEW: Unit tests
    ├── functional/
    │   └── test_lead_workflows.py        # NEW: Functional tests
    ├── integration/
    │   └── test_lead_integration.py      # NEW: Integration tests
    └── test_lead_pbt.py                  # NEW: Property-based tests

frontend/src/
├── features/leads/
│   ├── components/
│   │   ├── LeadsList.tsx                 # NEW
│   │   ├── LeadDetail.tsx                # NEW
│   │   ├── LeadStatusBadge.tsx           # NEW
│   │   ├── LeadSituationBadge.tsx        # NEW
│   │   ├── ConvertLeadDialog.tsx         # NEW
│   │   └── LeadFilters.tsx               # NEW
│   ├── hooks/
│   │   ├── useLeads.ts                   # NEW
│   │   ├── useLead.ts                    # NEW
│   │   ├── useUpdateLead.ts              # NEW
│   │   └── useConvertLead.ts             # NEW
│   ├── api/
│   │   └── leadApi.ts                    # NEW
│   ├── types/
│   │   └── index.ts                      # NEW
│   └── index.ts                          # NEW
├── features/dashboard/components/
│   └── DashboardPage.tsx                 # MODIFY: Add New Leads card
├── shared/components/
│   └── Layout.tsx                        # MODIFY: Add Leads nav tab with badge
└── core/router/
    └── index.tsx                         # MODIFY: Add /leads and /leads/:id routes
```

## Dependencies

No new Python packages required. All dependencies are already in the project:
- `fastapi`, `pydantic`, `sqlalchemy`, `asyncpg`, `alembic` (backend)
- `hypothesis`, `pytest`, `pytest-asyncio`, `httpx` (testing)
- `react`, `@tanstack/react-query`, `lucide-react`, `tailwindcss` (frontend)

