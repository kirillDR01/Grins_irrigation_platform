# Design Document: Customer Management

## Introduction

This document provides the technical design for the Customer Management feature of Grin's Irrigation Platform. It defines the database schema, API endpoints, service layer architecture, and implementation patterns that will fulfill the requirements specified in requirements.md.

## Design Overview

The Customer Management feature follows a layered architecture pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  FastAPI endpoints with Pydantic request/response models     │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                             │
│  CustomerService with LoggerMixin for business logic         │
├─────────────────────────────────────────────────────────────┤
│                   Repository Layer                           │
│  CustomerRepository for database operations                  │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                            │
│  PostgreSQL with SQLAlchemy async models                     │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### customers Table

```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255),
    
    -- Status and Flags
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive
    is_priority BOOLEAN DEFAULT FALSE,
    is_red_flag BOOLEAN DEFAULT FALSE,
    is_slow_payer BOOLEAN DEFAULT FALSE,
    is_new_customer BOOLEAN DEFAULT TRUE,
    
    -- Communication Preferences
    sms_opt_in BOOLEAN DEFAULT FALSE,
    email_opt_in BOOLEAN DEFAULT FALSE,
    communication_preferences_updated_at TIMESTAMP WITH TIME ZONE,
    
    -- Lead Tracking
    lead_source VARCHAR(50),  -- website, google, referral, ad, word_of_mouth
    lead_source_details JSONB,
    
    -- Soft Delete
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_status ON customers(status);
CREATE INDEX idx_customers_lead_source ON customers(lead_source);
CREATE INDEX idx_customers_is_deleted ON customers(is_deleted);
CREATE INDEX idx_customers_name ON customers(last_name, first_name);
```

### properties Table

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
    
    -- System Details
    zone_count INTEGER CHECK (zone_count >= 1 AND zone_count <= 50),
    system_type VARCHAR(20) DEFAULT 'standard',  -- standard, lake_pump
    property_type VARCHAR(20) DEFAULT 'residential',  -- residential, commercial
    
    -- Access Information
    is_primary BOOLEAN DEFAULT FALSE,
    access_instructions TEXT,
    gate_code VARCHAR(50),
    has_dogs BOOLEAN DEFAULT FALSE,
    special_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_properties_customer ON properties(customer_id);
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_location ON properties(latitude, longitude);
CREATE INDEX idx_properties_is_primary ON properties(customer_id, is_primary);
```

## API Endpoints

### Customer Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/customers` | Create customer | CustomerCreate | CustomerResponse |
| GET | `/api/v1/customers/{id}` | Get customer by ID | - | CustomerDetailResponse |
| PUT | `/api/v1/customers/{id}` | Update customer | CustomerUpdate | CustomerResponse |
| DELETE | `/api/v1/customers/{id}` | Soft delete customer | - | 204 No Content |
| GET | `/api/v1/customers` | List customers | Query params | PaginatedCustomerResponse |
| PUT | `/api/v1/customers/{id}/flags` | Update customer flags | CustomerFlagsUpdate | CustomerResponse |
| GET | `/api/v1/customers/lookup/phone/{phone}` | Lookup by phone | - | CustomerResponse[] |
| GET | `/api/v1/customers/lookup/email/{email}` | Lookup by email | - | CustomerResponse[] |
| GET | `/api/v1/customers/{id}/service-history` | Get service history | Query params | ServiceHistoryResponse |
| POST | `/api/v1/customers/export` | Export customers CSV | ExportRequest | CSV file |
| PUT | `/api/v1/customers/bulk/preferences` | Bulk update preferences | BulkPreferencesUpdate | BulkUpdateResponse |

### Property Endpoints

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/customers/{customer_id}/properties` | Add property | PropertyCreate | PropertyResponse |
| GET | `/api/v1/customers/{customer_id}/properties` | List properties | - | PropertyResponse[] |
| GET | `/api/v1/properties/{id}` | Get property by ID | - | PropertyResponse |
| PUT | `/api/v1/properties/{id}` | Update property | PropertyUpdate | PropertyResponse |
| DELETE | `/api/v1/properties/{id}` | Delete property | - | 204 No Content |
| PUT | `/api/v1/properties/{id}/primary` | Set as primary | - | PropertyResponse |

## Pydantic Schemas

### Customer Schemas

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class CustomerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class LeadSource(str, Enum):
    WEBSITE = "website"
    GOOGLE = "google"
    REFERRAL = "referral"
    AD = "ad"
    WORD_OF_MOUTH = "word_of_mouth"

class CustomerCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    lead_source: Optional[LeadSource] = None
    lead_source_details: Optional[dict] = None
    sms_opt_in: bool = False
    email_opt_in: bool = False
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove non-digits and validate 10-digit format
        digits = ''.join(filter(str.isdigit, v))
        if len(digits) != 10:
            raise ValueError('Phone must be 10 digits')
        return digits

class CustomerUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    status: Optional[CustomerStatus] = None
    lead_source: Optional[LeadSource] = None
    lead_source_details: Optional[dict] = None
    sms_opt_in: Optional[bool] = None
    email_opt_in: Optional[bool] = None

class CustomerFlagsUpdate(BaseModel):
    is_priority: Optional[bool] = None
    is_red_flag: Optional[bool] = None
    is_slow_payer: Optional[bool] = None
    is_new_customer: Optional[bool] = None

class CustomerResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone: str
    email: Optional[str]
    status: CustomerStatus
    is_priority: bool
    is_red_flag: bool
    is_slow_payer: bool
    is_new_customer: bool
    sms_opt_in: bool
    email_opt_in: bool
    lead_source: Optional[LeadSource]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CustomerDetailResponse(CustomerResponse):
    properties: List['PropertyResponse']
    service_history_summary: Optional['ServiceHistorySummary']

class ServiceHistorySummary(BaseModel):
    total_jobs: int
    last_service_date: Optional[datetime]
    total_revenue: float
```

### Property Schemas

```python
class SystemType(str, Enum):
    STANDARD = "standard"
    LAKE_PUMP = "lake_pump"

class PropertyType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"

class PropertyCreate(BaseModel):
    address: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(default="MN", max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    zone_count: Optional[int] = Field(None, ge=1, le=50)
    system_type: SystemType = SystemType.STANDARD
    property_type: PropertyType = PropertyType.RESIDENTIAL
    is_primary: bool = False
    access_instructions: Optional[str] = None
    gate_code: Optional[str] = Field(None, max_length=50)
    has_dogs: bool = False
    special_notes: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v: str) -> str:
        # Validate city is in service area
        service_cities = [
            'eden prairie', 'plymouth', 'maple grove', 'brooklyn park',
            'rogers', 'minnetonka', 'wayzata', 'hopkins', 'st. louis park',
            'golden valley', 'new hope', 'crystal', 'robbinsdale',
            'champlin', 'corcoran', 'medina', 'orono', 'minnetrista'
        ]
        if v.lower() not in service_cities:
            # Allow but log warning - don't reject
            pass
        return v

class PropertyUpdate(BaseModel):
    address: Optional[str] = Field(None, min_length=1, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    zone_count: Optional[int] = Field(None, ge=1, le=50)
    system_type: Optional[SystemType] = None
    property_type: Optional[PropertyType] = None
    access_instructions: Optional[str] = None
    gate_code: Optional[str] = Field(None, max_length=50)
    has_dogs: Optional[bool] = None
    special_notes: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PropertyResponse(BaseModel):
    id: UUID
    customer_id: UUID
    address: str
    city: str
    state: str
    zip_code: Optional[str]
    zone_count: Optional[int]
    system_type: SystemType
    property_type: PropertyType
    is_primary: bool
    access_instructions: Optional[str]
    gate_code: Optional[str]
    has_dogs: bool
    special_notes: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Query and Response Schemas

```python
class CustomerListParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    city: Optional[str] = None
    status: Optional[CustomerStatus] = None
    is_priority: Optional[bool] = None
    is_red_flag: Optional[bool] = None
    is_slow_payer: Optional[bool] = None
    search: Optional[str] = None  # Search name or email
    sort_by: str = Field(default="last_name")
    sort_order: str = Field(default="asc")

class PaginatedResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class BulkPreferencesUpdate(BaseModel):
    customer_ids: List[UUID] = Field(..., max_length=1000)
    sms_opt_in: Optional[bool] = None
    email_opt_in: Optional[bool] = None

class BulkUpdateResponse(BaseModel):
    updated_count: int
    failed_count: int
    errors: List[dict]
```

## Service Layer Design

### CustomerService

```python
from grins_platform.log_config import LoggerMixin

class CustomerService(LoggerMixin):
    """Service for customer management operations."""
    
    DOMAIN = "customer"
    
    def __init__(self, repository: CustomerRepository):
        self.repository = repository
    
    async def create_customer(self, data: CustomerCreate) -> Customer:
        """Create a new customer with validation."""
        self.log_started("create_customer", phone=data.phone)
        
        # Check for duplicate phone
        existing = await self.repository.find_by_phone(data.phone)
        if existing:
            self.log_rejected("create_customer", reason="duplicate_phone")
            raise DuplicateCustomerError(existing.id)
        
        # Normalize phone number
        normalized_phone = self._normalize_phone(data.phone)
        
        customer = await self.repository.create(
            first_name=data.first_name,
            last_name=data.last_name,
            phone=normalized_phone,
            email=data.email,
            lead_source=data.lead_source,
            sms_opt_in=data.sms_opt_in,
            email_opt_in=data.email_opt_in
        )
        
        self.log_completed("create_customer", customer_id=str(customer.id))
        return customer
    
    async def get_customer(self, customer_id: UUID) -> CustomerDetail:
        """Get customer with properties and service history."""
        self.log_started("get_customer", customer_id=str(customer_id))
        
        customer = await self.repository.get_by_id(customer_id)
        if not customer or customer.is_deleted:
            self.log_rejected("get_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)
        
        properties = await self.repository.get_properties(customer_id)
        service_summary = await self.repository.get_service_summary(customer_id)
        
        self.log_completed("get_customer", customer_id=str(customer_id))
        return CustomerDetail(
            customer=customer,
            properties=properties,
            service_history_summary=service_summary
        )
    
    async def update_customer(self, customer_id: UUID, data: CustomerUpdate) -> Customer:
        """Update customer information."""
        self.log_started("update_customer", customer_id=str(customer_id))
        
        customer = await self.repository.get_by_id(customer_id)
        if not customer or customer.is_deleted:
            self.log_rejected("update_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)
        
        # Check phone uniqueness if changing
        if data.phone and data.phone != customer.phone:
            existing = await self.repository.find_by_phone(data.phone)
            if existing and existing.id != customer_id:
                self.log_rejected("update_customer", reason="duplicate_phone")
                raise DuplicateCustomerError(existing.id)
        
        updated = await self.repository.update(customer_id, data.model_dump(exclude_unset=True))
        
        self.log_completed("update_customer", customer_id=str(customer_id))
        return updated
    
    async def delete_customer(self, customer_id: UUID) -> None:
        """Soft delete a customer."""
        self.log_started("delete_customer", customer_id=str(customer_id))
        
        customer = await self.repository.get_by_id(customer_id)
        if not customer:
            self.log_rejected("delete_customer", reason="not_found")
            raise CustomerNotFoundError(customer_id)
        
        await self.repository.soft_delete(customer_id)
        
        self.log_completed("delete_customer", customer_id=str(customer_id))
    
    async def list_customers(self, params: CustomerListParams) -> PaginatedResult:
        """List customers with filtering and pagination."""
        self.log_started("list_customers", page=params.page, filters=params.model_dump())
        
        result = await self.repository.list_with_filters(params)
        
        self.log_completed("list_customers", total=result.total)
        return result
    
    async def lookup_by_phone(self, phone: str) -> List[Customer]:
        """Lookup customers by phone number."""
        self.log_started("lookup_by_phone", phone=phone[-4:])  # Log last 4 digits only
        
        normalized = self._normalize_phone(phone)
        customers = await self.repository.find_by_phone_partial(normalized)
        
        self.log_completed("lookup_by_phone", count=len(customers))
        return customers
    
    async def update_flags(self, customer_id: UUID, flags: CustomerFlagsUpdate) -> Customer:
        """Update customer flags."""
        self.log_started("update_flags", customer_id=str(customer_id))
        
        customer = await self.repository.get_by_id(customer_id)
        if not customer or customer.is_deleted:
            self.log_rejected("update_flags", reason="not_found")
            raise CustomerNotFoundError(customer_id)
        
        updated = await self.repository.update_flags(customer_id, flags.model_dump(exclude_unset=True))
        
        self.log_completed("update_flags", customer_id=str(customer_id))
        return updated
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to 10 digits."""
        return ''.join(filter(str.isdigit, phone))[-10:]
```

### PropertyService

```python
class PropertyService(LoggerMixin):
    """Service for property management operations."""
    
    DOMAIN = "customer"
    
    def __init__(self, repository: PropertyRepository):
        self.repository = repository
    
    async def add_property(self, customer_id: UUID, data: PropertyCreate) -> Property:
        """Add a property to a customer."""
        self.log_started("add_property", customer_id=str(customer_id))
        
        # If this is the first property or marked as primary, handle primary flag
        if data.is_primary:
            await self.repository.clear_primary_flag(customer_id)
        
        property = await self.repository.create(
            customer_id=customer_id,
            **data.model_dump()
        )
        
        self.log_completed("add_property", property_id=str(property.id))
        return property
    
    async def set_primary(self, property_id: UUID) -> Property:
        """Set a property as the primary property."""
        self.log_started("set_primary", property_id=str(property_id))
        
        property = await self.repository.get_by_id(property_id)
        if not property:
            self.log_rejected("set_primary", reason="not_found")
            raise PropertyNotFoundError(property_id)
        
        await self.repository.clear_primary_flag(property.customer_id)
        updated = await self.repository.update(property_id, {"is_primary": True})
        
        self.log_completed("set_primary", property_id=str(property_id))
        return updated
```

## Error Handling

### Custom Exceptions

```python
class CustomerError(Exception):
    """Base exception for customer operations."""
    pass

class CustomerNotFoundError(CustomerError):
    """Raised when customer is not found."""
    def __init__(self, customer_id: UUID):
        self.customer_id = customer_id
        super().__init__(f"Customer not found: {customer_id}")

class DuplicateCustomerError(CustomerError):
    """Raised when attempting to create duplicate customer."""
    def __init__(self, existing_id: UUID):
        self.existing_id = existing_id
        super().__init__(f"Customer already exists with ID: {existing_id}")

class PropertyNotFoundError(CustomerError):
    """Raised when property is not found."""
    def __init__(self, property_id: UUID):
        self.property_id = property_id
        super().__init__(f"Property not found: {property_id}")

class ValidationError(CustomerError):
    """Raised when validation fails."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error on {field}: {message}")
```

### API Error Responses

```python
@router.exception_handler(CustomerNotFoundError)
async def customer_not_found_handler(request: Request, exc: CustomerNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": "CUSTOMER_NOT_FOUND",
                "message": str(exc),
                "customer_id": str(exc.customer_id)
            }
        }
    )

@router.exception_handler(DuplicateCustomerError)
async def duplicate_customer_handler(request: Request, exc: DuplicateCustomerError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "DUPLICATE_CUSTOMER",
                "message": "Customer with this phone number already exists",
                "existing_id": str(exc.existing_id)
            }
        }
    )
```

## Testing Strategy

### Unit Tests

- Test CustomerService methods with mocked repository
- Test PropertyService methods with mocked repository
- Test Pydantic schema validation
- Test phone number normalization
- Test email validation

### Integration Tests

- Test full customer CRUD workflow
- Test property management workflow
- Test customer lookup operations
- Test pagination and filtering
- Test bulk operations

### Property-Based Tests

- Test phone normalization with various formats
- Test email validation with edge cases
- Test zone count validation boundaries
- Test pagination with various page sizes

## Correctness Properties

### Property 1: Phone Number Uniqueness
**Validates: Requirement 6.6**
- For any two active customers C1 and C2, if C1.id ≠ C2.id then normalize(C1.phone) ≠ normalize(C2.phone)

### Property 2: Soft Delete Preservation
**Validates: Requirement 6.8**
- For any soft-deleted customer C, all properties P where P.customer_id = C.id remain accessible

### Property 3: Primary Property Uniqueness
**Validates: Requirement 2.7**
- For any customer C, at most one property P where P.customer_id = C.id has P.is_primary = true

### Property 4: Zone Count Bounds
**Validates: Requirement 2.2**
- For any property P, P.zone_count is null OR (1 ≤ P.zone_count ≤ 50)

### Property 5: Communication Opt-In Default
**Validates: Requirement 5.1, 5.2**
- For any newly created customer C, C.sms_opt_in = false AND C.email_opt_in = false

### Property 6: Phone Normalization Idempotence
**Validates: Requirement 6.10**
- For any phone string P, normalize(normalize(P)) = normalize(P)

## File Structure

```
src/grins_platform/
├── api/
│   ├── __init__.py
│   ├── dependencies.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       └── customers.py
├── schemas/
│   ├── __init__.py
│   ├── customer.py
│   └── property.py
├── services/
│   ├── __init__.py
│   ├── customer_service.py
│   └── property_service.py
├── repositories/
│   ├── __init__.py
│   ├── customer_repository.py
│   └── property_repository.py
├── models/
│   ├── __init__.py
│   ├── customer.py
│   └── property.py
├── exceptions/
│   ├── __init__.py
│   └── customer.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_customer_service.py
    ├── test_property_service.py
    ├── test_customer_api.py
    └── test_schemas.py
```

## Dependencies

### Python Packages

```toml
[project.dependencies]
fastapi = ">=0.109.0"
pydantic = ">=2.5.0"
sqlalchemy = ">=2.0.0"
asyncpg = ">=0.29.0"
alembic = ">=1.13.0"
python-multipart = ">=0.0.6"
email-validator = ">=2.1.0"
```

### Testing Packages

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.26.0",
    "hypothesis>=6.92.0",
]
```
