# Agent Communication File

> **Purpose:** This file is designed for communication between AI agents (Claude instances) working on separate repositories that need to integrate with each other.

---

## About This Repository

**Repository:** `Grins_irrigation_platform_release`
**Type:** Backend API + Admin Dashboard
**Owner:** Grin's Irrigation (field service business)

### What This Repo Contains

| Component | Description | Location |
|-----------|-------------|----------|
| **Backend API** | FastAPI REST API serving all data | `src/grins_platform/` |
| **Admin Frontend** | React dashboard for staff/admin | `frontend/` |
| **Database** | PostgreSQL schemas and migrations | `migrations/` |
| **Documentation** | API docs and planning | `docs/` |

### What This Repo Does NOT Contain

- Customer-facing website/landing page (separate repo)
- Public marketing content
- Customer portal/login

---

## Integration Point: Customer-Facing Frontend

A **separate repository** contains the customer-facing frontend (landing page, service request forms, etc.). That frontend needs to communicate with this backend.

### Architecture Overview

```
┌─────────────────────────────────┐
│  CUSTOMER-FACING FRONTEND       │  ◄── Separate repo (you are here if reading this)
│  (Landing page, forms)          │
└───────────────┬─────────────────┘
                │
                │  HTTPS POST requests
                │
                ▼
┌─────────────────────────────────┐
│  THIS REPOSITORY                │
│  Backend API (FastAPI)          │
│  Database (PostgreSQL)          │
│  Admin Dashboard (React)        │
└─────────────────────────────────┘
```

---

## API Contract for Customer-Facing Frontend

The customer-facing frontend should call these **public endpoints** (no authentication required).

### Base URL

```
Production: https://api.grins-irrigation.com
Development: http://localhost:8000
```

---

## Endpoint 1: Service Request

**Purpose:** Customer submits a request for irrigation service.

### Request

```
POST /api/v1/public/service-request
Content-Type: application/json
```

### Request Body (TypeScript Interface)

```typescript
interface ServiceRequestPayload {
  // Required fields
  firstName: string;        // min 1, max 100 chars
  lastName: string;         // min 1, max 100 chars
  phone: string;            // format: "612-555-1234" or "6125551234"
  address: string;          // min 5, max 500 chars
  serviceType: string;      // e.g., "Spring Turn-On", "Repair", "Winterization"
  description: string;      // min 10, max 2000 chars - details about the request

  // Optional fields
  email?: string;           // valid email format
  city?: string;
  state?: string;           // defaults to "MN"
  zipCode?: string;
  preferredDate?: string;   // ISO date format: "2026-04-15"
  preferredTimeWindow?: "morning" | "afternoon" | "anytime";
  howHeardAboutUs?: string; // lead source tracking
  smsOptIn?: boolean;       // consent to receive SMS, defaults to false
}
```

### Response (Success - 200)

```typescript
interface ServiceRequestResponse {
  success: true;
  referenceNumber: number;  // Job ID for customer reference
  message: string;          // e.g., "Thank you, John! Your service request has been received."
  estimatedResponseTime: string; // e.g., "within 24 hours"
}
```

### Response (Error - 422)

```typescript
interface ValidationError {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}
```

### Example Implementation

```typescript
async function submitServiceRequest(formData: ServiceRequestPayload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/public/service-request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      firstName: formData.firstName,
      lastName: formData.lastName,
      phone: formData.phone,
      address: formData.address,
      serviceType: formData.serviceType,
      description: formData.description,
      email: formData.email,
      city: formData.city,
      state: formData.state || 'MN',
      zipCode: formData.zipCode,
      preferredDate: formData.preferredDate,
      preferredTimeWindow: formData.preferredTimeWindow,
      howHeardAboutUs: formData.howHeardAboutUs,
      smsOptIn: formData.smsOptIn || false,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.[0]?.msg || 'Failed to submit request');
  }

  return response.json();
}
```

---

## Endpoint 2: Contact Form

**Purpose:** General inquiries that don't require a service request.

### Request

```
POST /api/v1/public/contact
Content-Type: application/json
```

### Request Body (TypeScript Interface)

```typescript
interface ContactPayload {
  // Required fields
  name: string;             // min 1, max 200 chars
  email: string;            // valid email format
  subject: string;          // min 1, max 200 chars
  message: string;          // min 10, max 5000 chars

  // Optional fields
  phone?: string;
}
```

### Response (Success - 200)

```typescript
interface ContactResponse {
  success: true;
  message: string;  // e.g., "Thank you for your message. We'll get back to you soon!"
}
```

---

## Endpoint 3: Quote Request

**Purpose:** Customer requests a quote/estimate for services.

### Request

```
POST /api/v1/public/quote-request
Content-Type: application/json
```

### Request Body (TypeScript Interface)

```typescript
interface QuoteRequestPayload {
  // Required fields
  firstName: string;        // min 1, max 100 chars
  lastName: string;         // min 1, max 100 chars
  phone: string;            // format: "612-555-1234" or "6125551234"
  address: string;          // min 5, max 500 chars

  // Optional fields
  email?: string;
  propertyType?: "residential" | "commercial";
  zoneCount?: number;       // number of irrigation zones
  systemAge?: string;       // e.g., "1-5 years", "5-10 years", "10+ years"
  servicesInterestedIn?: string[];  // e.g., ["Spring Turn-On", "System Audit"]
  additionalNotes?: string;
  smsOptIn?: boolean;
}
```

### Response (Success - 200)

```typescript
interface QuoteResponse {
  success: true;
  referenceNumber: number;
  message: string;  // e.g., "Thank you, John! We'll prepare your quote and contact you soon."
}
```

---

## Service Types (Valid Options)

These are the valid service types the backend recognizes:

```typescript
const SERVICE_TYPES = [
  "Spring Turn-On",
  "Winterization",
  "Repair",
  "Diagnostic",
  "System Audit",
  "New Installation",
  "Head Replacement",
  "Controller Programming",
  "Valve Repair",
  "Leak Detection",
  "Other"
] as const;
```

---

## Form Validation Rules

Implement these validations on the frontend before submitting:

| Field | Validation |
|-------|------------|
| `firstName` | Required, 1-100 characters |
| `lastName` | Required, 1-100 characters |
| `phone` | Required, US phone format (10 digits) |
| `email` | Optional, valid email format |
| `address` | Required, 5-500 characters |
| `description` | Required for service request, 10-2000 characters |
| `message` | Required for contact, 10-5000 characters |

### Phone Normalization

The backend accepts these formats (normalize on frontend if desired):
- `612-555-1234`
- `6125551234`
- `(612) 555-1234`

---

## Error Handling

### Common Error Responses

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Show success message, display reference number |
| 422 | Validation Error | Show field-specific error messages |
| 429 | Rate Limited | Show "Please wait before submitting again" |
| 500 | Server Error | Show generic error, suggest calling instead |

### Rate Limits

- **Service Request:** 10 requests per hour per IP
- **Contact Form:** 10 requests per hour per IP
- **Quote Request:** 10 requests per hour per IP

---

## CORS Configuration

The backend allows requests from:

```
https://grins-irrigation.com
https://www.grins-irrigation.com
http://localhost:3000  (development)
```

If your frontend domain is different, notify the backend team to add it.

---

## Testing the Integration

### Development Setup

1. Backend runs on: `http://localhost:8000`
2. Test with curl:

```bash
curl -X POST http://localhost:8000/api/v1/public/service-request \
  -H "Content-Type: application/json" \
  -d '{
    "firstName": "Test",
    "lastName": "Customer",
    "phone": "612-555-0000",
    "address": "123 Test St, Minneapolis, MN 55401",
    "serviceType": "Spring Turn-On",
    "description": "Test request - please ignore. Testing integration."
  }'
```

### Expected Response

```json
{
  "success": true,
  "referenceNumber": 42,
  "message": "Thank you, Test! Your service request has been received.",
  "estimatedResponseTime": "within 24 hours"
}
```

---

## Questions or Issues?

If you (the other agent) have questions about this API:

1. Check `docs/phase11planning.md` for more detailed architecture
2. Check `src/grins_platform/schemas/public.py` for exact Pydantic schemas
3. Check `src/grins_platform/api/v1/public.py` for endpoint implementations

---

## Status

| Endpoint | Backend Status | Notes |
|----------|----------------|-------|
| `/api/v1/public/service-request` | **PLANNED** | See phase11planning.md |
| `/api/v1/public/contact` | **PLANNED** | See phase11planning.md |
| `/api/v1/public/quote-request` | **PLANNED** | See phase11planning.md |

*Last updated: 2026-02-04*
