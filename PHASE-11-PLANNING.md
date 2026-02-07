# Phase 11: Customer-Facing Frontend Integration

## Overview

This document outlines the architecture for integrating a customer-facing frontend (separate repository) with the existing admin/employee backend system.

## Architecture Decision

**Recommendation: Keep Separate Repositories**

The customer-facing frontend remains in its own repository while sharing the backend API and database with the admin dashboard.

---

## Complete Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CUSTOMER JOURNEY                                   │
└─────────────────────────────────────────────────────────────────────────────┘

   Customer visits grins-irrigation.com (separate repo)
                          │
                          ▼
   ┌──────────────────────────────────────┐
   │   CUSTOMER-FACING FRONTEND           │
   │   (Separate Repository)              │
   │                                      │
   │   • Landing page                     │
   │   • Service request form             │
   │   • Contact form                     │
   │   • Maybe: login to view job status  │
   └──────────────────┬───────────────────┘
                      │
                      │  HTTP POST request
                      │  (JSON payload)
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MAIN REPOSITORY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │  BACKEND API (FastAPI) - src/grins_platform/                         │  │
│   │                                                                      │  │
│   │  EXISTING ENDPOINTS (require auth):                                  │  │
│   │  ├── /api/v1/auth/*          (staff login)                          │  │
│   │  ├── /api/v1/customers/*     (CRUD customers)                       │  │
│   │  ├── /api/v1/jobs/*          (CRUD jobs)                            │  │
│   │  ├── /api/v1/appointments/*  (scheduling)                           │  │
│   │  └── /api/v1/invoices/*      (billing)                              │  │
│   │                                                                      │  │
│   │  NEW PUBLIC ENDPOINTS (no auth required):                           │  │
│   │  ├── /api/v1/public/service-request                                 │  │
│   │  │     Customer submits: name, phone, email,                        │  │
│   │  │     address, service needed, description                         │  │
│   │  │                                                                   │  │
│   │  ├── /api/v1/public/contact                                         │  │
│   │  │     General inquiries                                            │  │
│   │  │                                                                   │  │
│   │  └── /api/v1/public/quote-request                                   │  │
│   │        Request an estimate                                          │  │
│   │                                                                      │  │
│   └──────────────────────────────┬───────────────────────────────────────┘  │
│                                  │                                           │
│                                  │ writes to                                 │
│                                  ▼                                           │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │  POSTGRESQL DATABASE                                                 │  │
│   │                                                                      │  │
│   │  customers table    ◄── New customer created (or matched by phone)  │  │
│   │  properties table   ◄── Property created if address provided        │  │
│   │  jobs table         ◄── Job created with status="requested"         │  │
│   │                          source="website", category=AI-determined   │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                  │                                           │
│                                  │ reads from                                │
│                                  ▼                                           │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │  ADMIN DASHBOARD FRONTEND - frontend/                                │  │
│   │                                                                      │  │
│   │  Staff logs in and sees:                                            │  │
│   │  • Dashboard shows "3 new service requests"                         │  │
│   │  • Jobs page shows new job with status "Requested"                  │  │
│   │  • Customer was auto-created or matched                             │  │
│   │  • Staff can approve, schedule, assign technician                   │  │
│   └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Concrete Example: Customer Submits Service Request

### Step 1: Customer fills out form on landing page

```typescript
// In the SEPARATE customer-facing repo
const formData = {
  firstName: "John",
  lastName: "Smith",
  phone: "612-555-1234",
  email: "john@example.com",
  address: "123 Main St, Minneapolis, MN 55401",
  serviceType: "Spring Turn-On",
  description: "Need irrigation system turned on for the season. 6 zones.",
  preferredDate: "2026-04-15"
};

// Customer clicks "Submit Request"
await fetch("https://api.grins-irrigation.com/api/v1/public/service-request", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(formData)
});
```

### Step 2: Backend API receives and processes

```python
# NEW FILE: src/grins_platform/api/v1/public.py

@router.post("/service-request")
async def submit_service_request(
    request: PublicServiceRequest,
    db: AsyncSession = Depends(get_db)
):
    # 1. Check if customer exists (by phone number)
    existing_customer = await customer_repo.get_by_phone(db, request.phone)

    if existing_customer:
        customer = existing_customer
    else:
        # 2. Create new customer
        customer = await customer_repo.create(db, CustomerCreate(
            first_name=request.first_name,
            last_name=request.last_name,
            phone=request.phone,
            email=request.email,
            lead_source="website"
        ))

    # 3. Create property if address provided
    property = await property_repo.create(db, PropertyCreate(
        customer_id=customer.id,
        address=request.address
    ))

    # 4. Create job with status "requested"
    job = await job_repo.create(db, JobCreate(
        customer_id=customer.id,
        property_id=property.id,
        description=request.description,
        status="requested",
        source="website",
        category=await ai_service.categorize(request.description)  # AI determines category
    ))

    # 5. Optionally send confirmation SMS
    if customer.sms_opt_in:
        await sms_service.send(customer.phone, "Thanks! We received your request...")

    return {"success": True, "reference_number": job.id}
```

### Step 3: Admin sees it in the dashboard

When a staff member logs into the admin dashboard:

```
┌─────────────────────────────────────────────────────────────┐
│  GRINS IRRIGATION ADMIN DASHBOARD                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Dashboard                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ New Requests│  │ Today's Jobs│  │ Pending     │         │
│  │     3       │  │     12      │  │ Invoices: 5 │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  📋 Recent Service Requests (from website)                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ John Smith - Spring Turn-On                         │   │
│  │ 123 Main St, Minneapolis | 612-555-1234             │   │
│  │ Status: REQUESTED | Source: Website                 │   │
│  │ [Approve] [View Details] [Call Customer]            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Requirements

### Files to Create in This Repository

#### 1. New Public API Router

**File:** `src/grins_platform/api/v1/public.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from grins_platform.db.session import get_db
from grins_platform.schemas.public import (
    PublicServiceRequest,
    PublicServiceResponse,
    PublicContactRequest,
    PublicContactResponse,
    PublicQuoteRequest,
    PublicQuoteResponse,
)
from grins_platform.services.public_service import PublicService

router = APIRouter(prefix="/public", tags=["public"])

@router.post("/service-request", response_model=PublicServiceResponse)
async def submit_service_request(
    request: PublicServiceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a service request from the customer-facing website.
    No authentication required.
    """
    service = PublicService(db)
    return await service.create_service_request(request)


@router.post("/contact", response_model=PublicContactResponse)
async def submit_contact_form(
    request: PublicContactRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a general contact/inquiry form.
    No authentication required.
    """
    service = PublicService(db)
    return await service.create_contact_inquiry(request)


@router.post("/quote-request", response_model=PublicQuoteResponse)
async def submit_quote_request(
    request: PublicQuoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a quote/estimate request.
    No authentication required.
    """
    service = PublicService(db)
    return await service.create_quote_request(request)
```

#### 2. New Schemas for Public Requests

**File:** `src/grins_platform/schemas/public.py`

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date


class PublicServiceRequest(BaseModel):
    """Schema for customer service request submission."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\d{3}-?\d{3}-?\d{4}$")
    email: Optional[EmailStr] = None
    address: str = Field(..., min_length=5, max_length=500)
    city: Optional[str] = None
    state: Optional[str] = "MN"
    zip_code: Optional[str] = None
    service_type: str = Field(..., description="Type of service requested")
    description: str = Field(..., min_length=10, max_length=2000)
    preferred_date: Optional[date] = None
    preferred_time_window: Optional[str] = None  # "morning", "afternoon", "anytime"
    how_heard_about_us: Optional[str] = None
    sms_opt_in: bool = False


class PublicServiceResponse(BaseModel):
    """Response after submitting a service request."""
    success: bool
    reference_number: int
    message: str
    estimated_response_time: str = "within 24 hours"


class PublicContactRequest(BaseModel):
    """Schema for general contact form."""
    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = None
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


class PublicContactResponse(BaseModel):
    """Response after submitting contact form."""
    success: bool
    message: str


class PublicQuoteRequest(BaseModel):
    """Schema for quote/estimate request."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., pattern=r"^\d{3}-?\d{3}-?\d{4}$")
    email: Optional[EmailStr] = None
    address: str = Field(..., min_length=5, max_length=500)
    property_type: Optional[str] = None  # "residential", "commercial"
    zone_count: Optional[int] = None
    system_age: Optional[str] = None
    services_interested_in: list[str] = []
    additional_notes: Optional[str] = None
    sms_opt_in: bool = False


class PublicQuoteResponse(BaseModel):
    """Response after submitting quote request."""
    success: bool
    reference_number: int
    message: str
```

#### 3. New Public Service

**File:** `src/grins_platform/services/public_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.schemas.public import (
    PublicServiceRequest,
    PublicServiceResponse,
    PublicContactRequest,
    PublicContactResponse,
    PublicQuoteRequest,
    PublicQuoteResponse,
)
from grins_platform.schemas.customer import CustomerCreate
from grins_platform.schemas.property import PropertyCreate
from grins_platform.schemas.job import JobCreate
from grins_platform.services.ai_service import AIService


class PublicService:
    """Service for handling public (unauthenticated) requests."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = CustomerRepository()
        self.property_repo = PropertyRepository()
        self.job_repo = JobRepository()
        self.ai_service = AIService()

    async def create_service_request(
        self, request: PublicServiceRequest
    ) -> PublicServiceResponse:
        """
        Process a service request from the public website.
        Creates or matches customer, creates property, creates job.
        """
        # 1. Find or create customer
        customer = await self.customer_repo.get_by_phone(self.db, request.phone)

        if not customer:
            customer = await self.customer_repo.create(
                self.db,
                CustomerCreate(
                    first_name=request.first_name,
                    last_name=request.last_name,
                    phone=request.phone,
                    email=request.email,
                    lead_source=request.how_heard_about_us or "website",
                    sms_opt_in=request.sms_opt_in,
                )
            )

        # 2. Create property
        property = await self.property_repo.create(
            self.db,
            PropertyCreate(
                customer_id=customer.id,
                address=request.address,
                city=request.city,
                state=request.state,
                zip_code=request.zip_code,
            )
        )

        # 3. AI categorize the request
        category = await self.ai_service.categorize_job(request.description)

        # 4. Create job
        job = await self.job_repo.create(
            self.db,
            JobCreate(
                customer_id=customer.id,
                property_id=property.id,
                description=request.description,
                status="requested",
                source="website",
                category=category,
            )
        )

        return PublicServiceResponse(
            success=True,
            reference_number=job.id,
            message=f"Thank you, {request.first_name}! Your service request has been received.",
        )

    async def create_contact_inquiry(
        self, request: PublicContactRequest
    ) -> PublicContactResponse:
        """Process a general contact form submission."""
        # Could store in a contact_inquiries table or send email notification
        # For now, just acknowledge receipt
        return PublicContactResponse(
            success=True,
            message="Thank you for your message. We'll get back to you soon!",
        )

    async def create_quote_request(
        self, request: PublicQuoteRequest
    ) -> PublicQuoteResponse:
        """Process a quote/estimate request."""
        # Similar to service request but creates job with category="estimate"
        customer = await self.customer_repo.get_by_phone(self.db, request.phone)

        if not customer:
            customer = await self.customer_repo.create(
                self.db,
                CustomerCreate(
                    first_name=request.first_name,
                    last_name=request.last_name,
                    phone=request.phone,
                    email=request.email,
                    lead_source="website",
                    sms_opt_in=request.sms_opt_in,
                )
            )

        property = await self.property_repo.create(
            self.db,
            PropertyCreate(
                customer_id=customer.id,
                address=request.address,
                property_type=request.property_type,
                zone_count=request.zone_count,
            )
        )

        description = f"Quote request. Services interested in: {', '.join(request.services_interested_in)}"
        if request.additional_notes:
            description += f"\nNotes: {request.additional_notes}"

        job = await self.job_repo.create(
            self.db,
            JobCreate(
                customer_id=customer.id,
                property_id=property.id,
                description=description,
                status="requested",
                source="website",
                category="estimate",
            )
        )

        return PublicQuoteResponse(
            success=True,
            reference_number=job.id,
            message=f"Thank you, {request.first_name}! We'll prepare your quote and contact you soon.",
        )
```

#### 4. Register Router in Main App

**Update:** `src/grins_platform/api/v1/__init__.py`

```python
from grins_platform.api.v1.public import router as public_router

# Add to router includes
api_router.include_router(public_router)
```

#### 5. CORS Configuration Update

**Update:** `src/grins_platform/core/config.py` or CORS middleware

```python
CORS_ORIGINS = [
    "https://grins-irrigation.com",           # Customer-facing site (production)
    "https://www.grins-irrigation.com",       # Customer-facing site with www
    "https://admin.grins-irrigation.com",     # Admin dashboard (production)
    "http://localhost:5173",                  # Admin dashboard (development)
    "http://localhost:3000",                  # Customer site (development)
]
```

#### 6. Rate Limiting on Public Endpoints

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/service-request")
@limiter.limit("10/hour")  # 10 requests per hour per IP
async def submit_service_request(...):
    ...
```

---

## Why This Architecture is Recommended

| Aspect | Benefit |
|--------|---------|
| **Single database** | No data sync issues - everything in one place |
| **Single backend** | One API to maintain, one source of truth |
| **Separate frontends** | Customer site stays simple and fast |
| **Security** | Public endpoints are isolated, admin requires auth |
| **Reuses existing code** | Customer/Job creation logic already exists |
| **AI integration** | Auto-categorize customer requests using existing AI |
| **SMS integration** | Auto-confirm using existing Twilio setup |

---

## Customer-Facing Repository Requirements

The customer-facing frontend only needs:

1. **Static/simple pages** - Landing, About, Services, Contact
2. **Forms** - Service request, contact, quote request
3. **API calls** - POST to the public endpoints in this backend
4. **No database** - It doesn't need its own database at all

The customer repo is essentially a "dumb" frontend that collects info and sends it to this backend.

---

## Security Considerations

### Public Endpoints Security

1. **Rate limiting** - Prevent spam and abuse
2. **Input validation** - Pydantic schemas validate all input
3. **CORS** - Only allow requests from known domains
4. **No sensitive data exposure** - Public endpoints return minimal info
5. **Honeypot fields** - Optional: add hidden fields to catch bots
6. **CAPTCHA** - Optional: add reCAPTCHA for form submissions

### Data Privacy

1. **Phone number normalization** - Store consistent format
2. **Email validation** - Verify format before storing
3. **SMS opt-in tracking** - Respect customer preferences
4. **No password storage for customers** - Customers don't have accounts (yet)

---

## Future Enhancements

### Phase 11.1: Customer Portal (Optional)

If customers need to track their service requests:

```
┌─────────────────────────────────────────┐
│  Customer Portal (Optional Future)      │
│                                         │
│  • Login with phone + verification code │
│  • View job status                      │
│  • View upcoming appointments           │
│  • View/pay invoices                    │
│  • Update contact preferences           │
└─────────────────────────────────────────┘
```

This would require:
- Customer authentication (phone + SMS code)
- New customer-facing authenticated endpoints
- Additional frontend pages in customer repo

---

## Implementation Checklist

- [ ] Create `src/grins_platform/api/v1/public.py`
- [ ] Create `src/grins_platform/schemas/public.py`
- [ ] Create `src/grins_platform/services/public_service.py`
- [ ] Register public router in API v1
- [ ] Update CORS configuration
- [ ] Add rate limiting middleware
- [ ] Test endpoints with sample requests
- [ ] Update customer-facing frontend to call new endpoints
- [ ] Deploy and verify end-to-end flow
