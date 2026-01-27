# AI Assistant API Documentation

## Overview

The AI Assistant API provides intelligent automation features for Grin's Irrigation Platform, including:
- Natural language business queries
- Automated schedule generation
- Job categorization
- Communication drafting
- Estimate generation

All AI features follow a human-in-the-loop principle where AI recommends but never executes without explicit user approval.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All endpoints require authentication via JWT token in the Authorization header:

```
Authorization: Bearer <token>
```

## Rate Limiting

- **Limit:** 100 AI requests per user per day
- **Headers:** 
  - `X-RateLimit-Remaining`: Requests remaining today
  - `X-RateLimit-Reset`: UTC timestamp when limit resets

## AI Chat Endpoints

### POST /ai/chat

Stream a conversational AI response for business queries.

**Request:**
```json
{
  "message": "How many jobs do we have scheduled for tomorrow?",
  "session_id": "optional-session-id"
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "token", "content": "You"}
data: {"type": "token", "content": " have"}
data: {"type": "token", "content": " 15"}
data: {"type": "done"}
```

**Status Codes:**
- `200 OK` - Streaming response
- `429 Too Many Requests` - Rate limit exceeded
- `401 Unauthorized` - Invalid or missing token

---

## Schedule Generation

### POST /ai/schedule/generate

Generate an optimized weekly schedule using AI.

**Request:**
```json
{
  "start_date": "2025-02-01",
  "end_date": "2025-02-07",
  "staff_ids": ["uuid1", "uuid2"],
  "job_type_filter": "seasonal"
}
```

**Response:**
```json
{
  "schedule": {
    "days": [
      {
        "date": "2025-02-01",
        "staff_assignments": [
          {
            "staff_id": "uuid1",
            "staff_name": "Vas",
            "jobs": [
              {
                "job_id": "uuid",
                "customer_name": "John Doe",
                "address": "123 Main St",
                "time_window": "09:00-11:00",
                "estimated_duration": 60,
                "service_type": "Spring Startup"
              }
            ]
          }
        ]
      }
    ],
    "warnings": [
      {
        "type": "equipment_conflict",
        "message": "Compressor needed for 2 jobs at same time",
        "affected_jobs": ["uuid1", "uuid2"]
      }
    ],
    "summary": {
      "total_jobs": 45,
      "total_staff": 3,
      "avg_jobs_per_day": 9,
      "estimated_revenue": 12500.00
    }
  },
  "ai_explanation": "I've optimized the schedule by batching jobs in Eden Prairie on Monday...",
  "confidence_score": 92
}
```

**Status Codes:**
- `200 OK` - Schedule generated
- `400 Bad Request` - Invalid date range or parameters
- `429 Too Many Requests` - Rate limit exceeded

---

## Job Categorization

### POST /ai/jobs/categorize

Categorize pending job requests using AI.

**Request:**
```json
{
  "job_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:**
```json
{
  "categorizations": [
    {
      "job_id": "uuid1",
      "category": "ready_to_schedule",
      "service_type": "Spring Startup",
      "suggested_price": 180.00,
      "confidence_score": 95,
      "ai_notes": "Standard 6-zone system, straightforward startup"
    },
    {
      "job_id": "uuid2",
      "category": "requires_estimate",
      "service_type": "Installation",
      "confidence_score": 45,
      "ai_notes": "Complex installation, needs site visit for accurate quote"
    }
  ],
  "summary": {
    "total_jobs": 2,
    "ready_to_schedule": 1,
    "requires_estimate": 1,
    "avg_confidence": 70
  }
}
```

**Confidence Threshold:**
- `>= 85%` - Ready to schedule
- `< 85%` - Requires manual review

**Status Codes:**
- `200 OK` - Categorization complete
- `400 Bad Request` - Invalid job IDs
- `429 Too Many Requests` - Rate limit exceeded

---

## Communication Drafting

### POST /ai/communication/draft

Generate a draft message for customer communication.

**Request:**
```json
{
  "customer_id": "uuid",
  "message_type": "appointment_confirmation",
  "context": {
    "appointment_date": "2025-02-01",
    "time_window": "09:00-11:00",
    "service_type": "Spring Startup"
  }
}
```

**Response:**
```json
{
  "draft": {
    "message_type": "appointment_confirmation",
    "message_content": "Hi John, your spring startup is scheduled for Saturday 2/1 between 9-11am. Reply YES to confirm.",
    "customer_name": "John Doe",
    "customer_phone": "6125551234",
    "is_slow_payer": false,
    "ai_notes": null
  }
}
```

**Message Types:**
- `appointment_confirmation`
- `appointment_reminder`
- `payment_reminder`
- `follow_up`
- `estimate_ready`

**Status Codes:**
- `200 OK` - Draft generated
- `400 Bad Request` - Invalid customer or message type
- `429 Too Many Requests` - Rate limit exceeded

---

## Estimate Generation

### POST /ai/estimate/generate

Generate an AI-powered estimate for a job.

**Request:**
```json
{
  "job_id": "uuid",
  "property_details": {
    "zone_count": 8,
    "system_type": "standard",
    "property_size_sqft": 15000
  }
}
```

**Response:**
```json
{
  "estimate": {
    "total_estimate": 5600.00,
    "breakdown": {
      "materials": 2800.00,
      "labor": 2000.00,
      "equipment": 400.00,
      "margin": 400.00
    },
    "similar_jobs": [
      {
        "job_id": "uuid",
        "customer_name": "Jane Smith",
        "zone_count": 8,
        "final_price": 5400.00,
        "completion_date": "2024-05-15"
      }
    ],
    "ai_recommendation": "Recommend site visit due to complex terrain",
    "confidence_score": 78
  }
}
```

**Status Codes:**
- `200 OK` - Estimate generated
- `400 Bad Request` - Invalid job or property details
- `429 Too Many Requests` - Rate limit exceeded

---

## Usage Tracking

### GET /ai/usage

Get AI usage statistics for the current user.

**Response:**
```json
{
  "today": {
    "request_count": 45,
    "remaining": 55,
    "total_tokens": 125000,
    "estimated_cost_usd": 0.38
  },
  "this_month": {
    "request_count": 890,
    "total_tokens": 2450000,
    "estimated_cost_usd": 7.35
  }
}
```

**Status Codes:**
- `200 OK` - Usage retrieved
- `401 Unauthorized` - Invalid token

---

## Audit Logs

### GET /ai/audit

Query AI audit logs with filters.

**Query Parameters:**
- `action_type` - Filter by action (schedule_generation, job_categorization, etc.)
- `entity_type` - Filter by entity (job, customer, appointment)
- `user_decision` - Filter by decision (approved, rejected, modified)
- `start_date` - Filter from date (ISO 8601)
- `end_date` - Filter to date (ISO 8601)
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20, max: 100)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "action_type": "schedule_generation",
      "entity_type": "schedule",
      "entity_id": null,
      "ai_recommendation": {
        "schedule": {...}
      },
      "confidence_score": 92,
      "user_decision": "approved",
      "user_id": "uuid",
      "decision_at": "2025-01-27T10:30:00Z",
      "request_tokens": 1500,
      "response_tokens": 3000,
      "estimated_cost_usd": 0.015,
      "created_at": "2025-01-27T10:29:45Z"
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**Status Codes:**
- `200 OK` - Logs retrieved
- `400 Bad Request` - Invalid filter parameters

### POST /ai/audit/{id}/decision

Record a user decision on an AI recommendation.

**Request:**
```json
{
  "decision": "approved",
  "notes": "Schedule looks good, proceeding with these assignments"
}
```

**Decision Types:**
- `approved` - User accepted AI recommendation
- `rejected` - User rejected AI recommendation
- `modified` - User modified AI recommendation before accepting

**Response:**
```json
{
  "id": "uuid",
  "action_type": "schedule_generation",
  "user_decision": "approved",
  "decision_at": "2025-01-27T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Decision recorded
- `404 Not Found` - Audit log not found
- `400 Bad Request` - Invalid decision type

---

## SMS Communication Endpoints

### POST /sms/send

Send an SMS message to a customer.

**Request:**
```json
{
  "customer_id": "uuid",
  "message_type": "appointment_confirmation",
  "message_content": "Hi John, your appointment is confirmed for 2/1 at 9am.",
  "scheduled_for": null
}
```

**Response:**
```json
{
  "id": "uuid",
  "customer_id": "uuid",
  "message_type": "appointment_confirmation",
  "delivery_status": "sent",
  "twilio_sid": "SM1234567890abcdef",
  "sent_at": "2025-01-27T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Message sent
- `400 Bad Request` - Customer not opted in or invalid phone
- `429 Too Many Requests` - Rate limit exceeded

### POST /sms/webhook

Twilio webhook for incoming SMS and delivery status updates.

**Note:** This endpoint is called by Twilio, not by frontend clients.

### GET /communications/queue

Get the communications queue with pending, scheduled, and sent messages.

**Query Parameters:**
- `status` - Filter by status (pending, scheduled, sent, failed)
- `message_type` - Filter by message type
- `customer_search` - Search by customer name or phone

**Response:**
```json
{
  "pending": [
    {
      "id": "uuid",
      "customer_name": "John Doe",
      "customer_phone": "6125551234",
      "message_type": "appointment_confirmation",
      "message_content": "Hi John...",
      "created_at": "2025-01-27T10:00:00Z"
    }
  ],
  "scheduled": [],
  "sent_today": [],
  "failed": []
}
```

**Status Codes:**
- `200 OK` - Queue retrieved

### POST /communications/send-bulk

Send multiple pending messages at once.

**Request:**
```json
{
  "message_ids": ["uuid1", "uuid2", "uuid3"]
}
```

**Response:**
```json
{
  "sent": 2,
  "failed": 1,
  "results": [
    {
      "id": "uuid1",
      "status": "sent"
    },
    {
      "id": "uuid2",
      "status": "sent"
    },
    {
      "id": "uuid3",
      "status": "failed",
      "error": "Customer not opted in"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Bulk send completed (check individual results)

### DELETE /communications/{id}

Delete a pending or scheduled message.

**Status Codes:**
- `204 No Content` - Message deleted
- `404 Not Found` - Message not found
- `400 Bad Request` - Cannot delete sent messages

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Rate limit exceeded. Try again in 3 hours."
}
```

**Common Error Codes:**
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

---

## Best Practices

1. **Rate Limiting:** Monitor `X-RateLimit-Remaining` header and implement client-side throttling
2. **Streaming:** Use SSE for chat endpoint to provide real-time feedback
3. **Audit Logs:** Always record user decisions on AI recommendations
4. **Error Handling:** Implement graceful degradation when AI services are unavailable
5. **SMS Opt-in:** Always verify customer SMS opt-in before sending messages
6. **Confidence Scores:** Use confidence thresholds to determine when manual review is needed

---

## Environment Configuration

See [AI_SETUP.md](./AI_SETUP.md) for environment variable configuration.
