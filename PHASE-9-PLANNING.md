# Phase 9 Planning - Telnyx SMS Integration

## Overview

Phase 9 focuses on implementing two-way SMS communication using Telnyx as the SMS provider. This was originally planned for Phase 8 but has been moved to Phase 9 to allow for proper Telnyx account setup and verification time.

**PRIMARY FOCUS: Telnyx SMS Integration (Twilio Replacement)**

---

## 🎯 PRIORITY 1: Telnyx SMS Integration

### Background & Problem Statement

The current Twilio integration is blocked by regulatory requirements:
- **A2P 10DLC Registration**: All US carriers now require Application-to-Person (A2P) registration for 10-digit long codes (10DLC)
- **Registration Complexity**: Twilio's 10DLC registration process involves brand verification, campaign registration, and carrier approval - can take weeks
- **Blocking Issue**: Without registration, SMS messages are being filtered/blocked by carriers

### Why Telnyx?

After researching alternatives, **Telnyx** is the recommended replacement:

| Factor | Telnyx Advantage |
|--------|------------------|
| **Cost** | 30-70% cheaper than Twilio |
| **Toll-Free Option** | Simpler verification process than 10DLC |
| **API Compatibility** | Similar REST API, easy migration |
| **Two-Way SMS** | Full support for inbound + outbound |
| **Documentation** | Excellent Python SDK and docs |
| **Reliability** | Enterprise-grade, used by major companies |

### Toll-Free vs 10DLC Comparison

| Feature | Toll-Free (1-800) | 10DLC (Local Number) |
|---------|-------------------|----------------------|
| **Verification Time** | 1-3 business days | 2-4 weeks |
| **Verification Complexity** | Simple form | Brand + Campaign registration |
| **Monthly Cost** | ~$2/month | ~$2/month + campaign fees |
| **Per-Message Cost** | ~$0.008/segment | ~$0.004/segment |
| **Throughput** | 3 MPS (messages/sec) | 1-75 MPS (varies by trust score) |
| **Customer Perception** | Professional/business | Local/personal |

**Recommendation**: Start with **Toll-Free** for faster deployment. Customers are okay with 1-800 style numbers for business communications.

---

## Two-Way SMS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     OUTBOUND SMS FLOW                           │
│                                                                 │
│  Grins Platform                                                 │
│       │                                                         │
│       ▼                                                         │
│  TelnyxSMSService.send_message()                               │
│       │                                                         │
│       ▼                                                         │
│  POST https://api.telnyx.com/v2/messages                       │
│       │                                                         │
│       ▼                                                         │
│  Telnyx → Carrier → Customer Phone                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     INBOUND SMS FLOW                            │
│                                                                 │
│  Customer Phone → Carrier → Telnyx                             │
│       │                                                         │
│       ▼                                                         │
│  Telnyx Webhook                                                 │
│       │                                                         │
│       ▼                                                         │
│  POST /api/v1/sms/inbound (our endpoint)                       │
│       │                                                         │
│       ▼                                                         │
│  TelnyxSMSService.handle_inbound()                             │
│       │                                                         │
│       ├── Parse message (YES/NO/STOP/etc.)                     │
│       ├── Update appointment status                             │
│       └── Log to sms_messages table                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Message Types to Support

| Message Type | Trigger | Template |
|--------------|---------|----------|
| **Appointment Confirmation** | After schedule applied | "Hi {name}, your {service} appointment is scheduled for {date} at {time}. Reply YES to confirm or call us to reschedule." |
| **Day-Before Reminder** | Cron job, day before | "Reminder: Your {service} appointment is tomorrow, {date} at {time}. Reply YES to confirm." |
| **On-The-Way Notification** | Tech marks "en route" | "Your technician is on the way! Expected arrival: {time}. Reply STOP to opt out of messages." |
| **Arrival Notification** | Tech marks "arrived" | "Your technician has arrived for your {service} appointment." |
| **Completion Summary** | Job completed | "Your {service} is complete! Total: ${amount}. Thank you for choosing Grin's Irrigation." |

### Message Template Specifications

**Character Limits**: SMS segments are 160 characters (or 70 for Unicode). Templates should be designed to fit within a single segment when possible.

| Template | Max Length | Actual Length (approx) |
|----------|------------|------------------------|
| Appointment Confirmation | 160 chars | ~140 chars |
| Day-Before Reminder | 160 chars | ~100 chars |
| On-The-Way | 160 chars | ~90 chars |
| Arrival | 160 chars | ~60 chars |
| Completion Summary | 160 chars | ~80 chars |

**Truncation Rules**:
- Customer first name: Max 15 characters, truncate with "..."
- Service name: Max 25 characters, truncate with "..."
- If message exceeds 160 chars, split into multiple segments

---

## Inbound Message Handling

| Customer Reply | Action |
|----------------|--------|
| **YES** / **CONFIRM** / **Y** | Update appointment status to "confirmed" |
| **NO** / **CANCEL** / **N** | Flag appointment for follow-up, notify admin |
| **STOP** / **UNSUBSCRIBE** / **QUIT** | Set customer `sms_opt_in = false` |
| **HELP** | Send help message with contact info |
| **Other** | Log message, optionally notify admin |

### Handling Multiple Pending Appointments

When a customer replies "YES" and has multiple pending appointments:
1. Confirm the **most recent unconfirmed appointment**
2. Send a clarifying message about other pending appointments
3. Allow customer to reply "YES" again to confirm additional appointments

---

## Python Code Examples

### Sending SMS (Outbound)

```python
import telnyx
from grins_platform.config import settings

telnyx.api_key = settings.TELNYX_API_KEY

class TelnyxSMSService:
    """Service for sending and receiving SMS via Telnyx."""
    
    def __init__(self):
        self.from_number = settings.TELNYX_PHONE_NUMBER
    
    async def send_message(
        self, 
        to_number: str, 
        message: str,
        customer_id: int | None = None,
        appointment_id: int | None = None,
        message_type: str = "general"
    ) -> dict:
        """Send an SMS message via Telnyx."""
        # Check opt-in status
        if customer_id:
            customer = await self.customer_repo.get_by_id(customer_id)
            if customer and not customer.sms_opt_in:
                logger.warning("sms.send.blocked.opt_out", customer_id=customer_id)
                return {"success": False, "error": "Customer has opted out of SMS"}
        
        try:
            response = telnyx.Message.create(
                from_=self.from_number,
                to=self._format_phone(to_number),
                text=message
            )
            
            # Log to database
            await self._log_message(
                direction="outbound",
                to_number=to_number,
                from_number=self.from_number,
                message=message,
                message_type=message_type,
                customer_id=customer_id,
                appointment_id=appointment_id,
                telnyx_id=response.id,
                status="sent"
            )
            
            return {"success": True, "message_id": response.id}
            
        except telnyx.error.TelnyxError as e:
            logger.error("sms.send.failed", error=str(e), to=to_number)
            return {"success": False, "error": str(e)}
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number to E.164 format."""
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        return f"+{digits}"
```

### Receiving SMS (Inbound Webhook) with Signature Verification

```python
from fastapi import APIRouter, Request, HTTPException, Header
import telnyx
from grins_platform.services.sms_service import TelnyxSMSService
from grins_platform.config import settings

router = APIRouter()

@router.post("/api/v1/sms/inbound")
async def handle_inbound_sms(
    request: Request,
    telnyx_signature_ed25519: str = Header(..., alias="Telnyx-Signature-ed25519"),
    telnyx_timestamp: str = Header(..., alias="Telnyx-Timestamp"),
):
    """Webhook endpoint for incoming SMS from Telnyx with signature verification."""
    payload = await request.body()
    
    # Verify webhook signature
    try:
        telnyx.Webhook.construct_event(
            payload=payload.decode(),
            signature=telnyx_signature_ed25519,
            timestamp=telnyx_timestamp,
            webhook_secret=settings.TELNYX_WEBHOOK_SECRET,
        )
    except telnyx.error.SignatureVerificationError:
        logger.warning("sms.webhook.invalid_signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse the verified payload
    data = await request.json()
    event_type = data.get("data", {}).get("event_type")
    
    if event_type == "message.received":
        message_data = data["data"]["payload"]
        
        from_number = message_data["from"]["phone_number"]
        to_number = message_data["to"][0]["phone_number"]
        text = message_data["text"]
        telnyx_id = message_data.get("id")
        
        # Check for duplicate (idempotency)
        existing = await sms_repo.get_by_telnyx_id(telnyx_id)
        if existing:
            logger.info("sms.webhook.duplicate", telnyx_id=telnyx_id)
            return {"status": "duplicate"}
        
        sms_service = TelnyxSMSService()
        await sms_service.handle_inbound(
            from_number=from_number,
            to_number=to_number,
            message=text,
            telnyx_id=telnyx_id
        )
    
    return {"status": "received"}
```

### Handling Inbound Messages

```python
async def handle_inbound(
    self, 
    from_number: str, 
    to_number: str, 
    message: str,
    telnyx_id: str | None = None
) -> None:
    """Process an inbound SMS message."""
    
    # Log the message
    await self._log_message(
        direction="inbound",
        from_number=from_number,
        to_number=to_number,
        message=message,
        message_type="customer_reply",
        telnyx_id=telnyx_id,
        status="received"
    )
    
    # Find customer by phone number
    customer = await self.customer_repo.find_by_phone(from_number)
    if not customer:
        logger.warning("sms.inbound.unknown_customer", phone=from_number)
        return
    
    # Parse the message
    normalized = message.strip().upper()
    
    if normalized in ["YES", "CONFIRM", "Y"]:
        await self._handle_confirmation(customer, from_number)
    elif normalized in ["NO", "CANCEL", "N"]:
        await self._handle_cancellation(customer, from_number)
    elif normalized in ["STOP", "UNSUBSCRIBE", "QUIT"]:
        await self._handle_opt_out(customer)
    elif normalized == "HELP":
        await self._send_help_message(from_number)
    else:
        # Log for manual review
        logger.info("sms.inbound.unrecognized", 
                   customer_id=customer.id, 
                   message=message)

async def _handle_confirmation(self, customer, phone: str) -> None:
    """Handle YES/CONFIRM reply."""
    # Find all unconfirmed appointments for this customer
    pending_appointments = await self.appointment_repo.find_pending_for_customer(
        customer.id, 
        status="sent"  # Only appointments where confirmation was sent
    )
    
    if not pending_appointments:
        await self.send_message(
            to_number=phone,
            message="We don't have any pending appointments to confirm. Please call us if you need assistance.",
            customer_id=customer.id,
            message_type="no_pending_appointment"
        )
        return
    
    # Confirm the most recent one
    most_recent = pending_appointments[0]  # Ordered by scheduled_date DESC
    most_recent.status = "confirmed"
    await self.appointment_repo.update(most_recent)
    
    # Send confirmation
    if len(pending_appointments) == 1:
        await self.send_message(
            to_number=phone,
            message=f"Thank you! Your appointment on {most_recent.scheduled_date.strftime('%B %d')} is confirmed. See you then!",
            customer_id=customer.id,
            appointment_id=most_recent.id,
            message_type="confirmation_ack"
        )
    else:
        # Multiple appointments - confirm one and notify about others
        other_dates = [a.scheduled_date.strftime('%B %d') for a in pending_appointments[1:]]
        await self.send_message(
            to_number=phone,
            message=f"Thank you! Your appointment on {most_recent.scheduled_date.strftime('%B %d')} is confirmed. You also have appointments on {', '.join(other_dates)}. Reply YES again to confirm those, or call us to reschedule.",
            customer_id=customer.id,
            appointment_id=most_recent.id,
            message_type="confirmation_ack_with_others"
        )

async def _handle_opt_out(self, customer) -> None:
    """Handle STOP/UNSUBSCRIBE reply."""
    customer.sms_opt_in = False
    await self.customer_repo.update(customer)
    logger.info("sms.opt_out", customer_id=customer.id)
    # Note: Do NOT send a confirmation message after opt-out (compliance requirement)
```

### SMS Send with Retry Logic

```python
async def send_message_with_retry(
    self, 
    to_number: str, 
    message: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> dict:
    """Send SMS with automatic retry on transient failures."""
    for attempt in range(max_retries):
        try:
            return await self.send_message(to_number, message, **kwargs)
        except SMSDeliveryError as e:
            if attempt < max_retries - 1 and self._is_retryable(e):
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            raise

def _is_retryable(self, error: SMSDeliveryError) -> bool:
    """Check if error is retryable (transient network issues, rate limits)."""
    retryable_codes = ["rate_limit", "timeout", "service_unavailable"]
    return error.telnyx_error_code in retryable_codes
```

---

## Backend Components to Create

| Component | Location | Purpose |
|-----------|----------|---------|
| `TelnyxSMSService` | `src/grins_platform/services/sms_service.py` | Send/receive SMS, handle replies |
| `SMSMessage` model | `src/grins_platform/models/sms_message.py` | Database model for message logging |
| `sms_messages` migration | `alembic/versions/` | Create sms_messages table |
| Inbound webhook | `src/grins_platform/api/v1/sms.py` | `POST /api/v1/sms/inbound` |
| SMS templates | `src/grins_platform/services/sms_templates.py` | Message templates |

---

## Database Schema: `sms_messages` Table

```sql
CREATE TABLE sms_messages (
    id SERIAL PRIMARY KEY,
    direction VARCHAR(10) NOT NULL,  -- 'inbound' or 'outbound'
    from_number VARCHAR(20) NOT NULL,
    to_number VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(50),  -- 'confirmation', 'reminder', 'on_the_way', etc.
    customer_id INTEGER REFERENCES customers(id),
    appointment_id INTEGER REFERENCES appointments(id),
    telnyx_id VARCHAR(100) UNIQUE,  -- Telnyx message ID (for idempotency)
    status VARCHAR(20),  -- 'sent', 'delivered', 'failed', 'received'
    error_message TEXT,  -- Error details if failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sms_messages_customer ON sms_messages(customer_id);
CREATE INDEX idx_sms_messages_appointment ON sms_messages(appointment_id);
CREATE INDEX idx_sms_messages_created ON sms_messages(created_at);
CREATE INDEX idx_sms_messages_telnyx_id ON sms_messages(telnyx_id);
```

---

## Environment Variables

```bash
# Telnyx Configuration
TELNYX_API_KEY=KEY_xxxxxxxxxxxxxxxx
TELNYX_PHONE_NUMBER=+18005551234
TELNYX_WEBHOOK_SECRET=whsec_xxxxxxxx  # For webhook signature verification

# Optional: Messaging Profile ID (if using multiple numbers)
TELNYX_MESSAGING_PROFILE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## Rate Limiting Considerations

Telnyx toll-free numbers have a **3 MPS (messages per second)** limit. When sending bulk messages (e.g., after applying a schedule with 150 jobs):

1. **Queue SMS sends** using a background task queue (Celery or similar)
2. **Implement rate limiting** in the send function
3. **Handle rate limit errors** gracefully with exponential backoff

```python
import asyncio
from collections import deque
from datetime import datetime, timedelta

class SMSRateLimiter:
    """Rate limiter for SMS sending (3 MPS for toll-free)."""
    
    def __init__(self, max_per_second: int = 3):
        self.max_per_second = max_per_second
        self.timestamps: deque = deque()
    
    async def acquire(self):
        """Wait until we can send another message."""
        now = datetime.now()
        
        # Remove timestamps older than 1 second
        while self.timestamps and self.timestamps[0] < now - timedelta(seconds=1):
            self.timestamps.popleft()
        
        # If at limit, wait
        if len(self.timestamps) >= self.max_per_second:
            wait_time = (self.timestamps[0] + timedelta(seconds=1) - now).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        self.timestamps.append(datetime.now())
```

---

## Implementation Phases

### Phase 9A: Telnyx Account Setup & Basic Outbound (2-3 hours)

**Tasks**:
1. Create Telnyx account and get API key
2. Purchase toll-free number
3. Complete toll-free verification (1-3 business days wait)
4. Create `TelnyxSMSService` with `send_message()` method
5. Add environment variables to `.env`
6. Test sending a message to a test phone

**Deliverables**:
- Working outbound SMS capability
- Verified toll-free number

---

### Phase 9B: Inbound Webhook & Message Handling (3-4 hours)

**Tasks**:
1. Create `sms_messages` database migration
2. Create `SMSMessage` SQLAlchemy model
3. Create `POST /api/v1/sms/inbound` endpoint with signature verification
4. Configure Telnyx webhook URL in dashboard
5. Implement `handle_inbound()` with YES/NO/STOP parsing
6. Implement appointment confirmation flow
7. Implement opt-out handling
8. Implement idempotency check (duplicate webhook handling)
9. Test full two-way flow

**Deliverables**:
- Working inbound SMS webhook
- Automatic appointment confirmation via SMS reply
- Opt-out handling

---

### Phase 9C: Message Templates & Automation (2-3 hours)

**Tasks**:
1. Create SMS message templates with character limits
2. Implement appointment confirmation sender
3. Implement day-before reminder (manual trigger first, cron later)
4. Implement "on the way" notification trigger
5. Add SMS send buttons to admin UI (optional)
6. Implement rate limiting for bulk sends
7. Test all message types

**Deliverables**:
- All message templates working
- Manual triggers for each message type
- Rate limiting implemented
- Ready for automation (cron jobs in future phase)

---

### Phase 9D: Testing & Polish (2-3 hours)

**Tasks**:
1. Unit tests for SMS service
2. Integration tests for webhook handling
3. Test opt-out compliance
4. Test rate limiting
5. Test error handling and retries
6. Frontend tests for SMS UI (if applicable)

**Deliverables**:
- Comprehensive test coverage
- Production-ready SMS system

---

## Telnyx Setup Checklist

- [ ] Create Telnyx account at https://telnyx.com
- [ ] Add payment method
- [ ] Purchase toll-free number (~$2/month)
- [ ] Submit toll-free verification form
- [ ] Wait for verification approval (1-3 business days)
- [ ] Get API key from Portal → API Keys
- [ ] Get webhook secret from Portal → API Keys
- [ ] Configure webhook URL in Portal → Messaging → Inbound Settings
- [ ] Test outbound message
- [ ] Test inbound message

---

## Cost Estimate

| Item | Cost |
|------|------|
| Toll-Free Number | ~$2/month |
| Outbound SMS | ~$0.008/segment |
| Inbound SMS | ~$0.008/segment |
| **Monthly Estimate** (500 messages) | ~$10/month |

*Much cheaper than Twilio's ~$0.0079/segment + higher number fees*

---

## Summary: Telnyx SMS Implementation

| Phase | Focus | Effort |
|-------|-------|--------|
| Phase 9A | Account setup + outbound SMS | 2-3 hours |
| Phase 9B | Inbound webhook + reply handling | 3-4 hours |
| Phase 9C | Templates + automation triggers | 2-3 hours |
| Phase 9D | Testing & polish | 2-3 hours |
| **Total** | **Full two-way SMS** | **9-13 hours** |

---

## SMS UI Validation Checklist (Agent-Browser)

```bash
# SMS Send (if UI exists)
- [ ] Send SMS button visible for opted-in customers
- [ ] Send SMS disabled for opted-out customers
- [ ] Message template selection
- [ ] Preview before send
- [ ] Success/failure feedback

# SMS History
- [ ] View SMS history for customer
- [ ] Inbound/outbound indicators
- [ ] Timestamps correct
- [ ] Status indicators (sent, delivered, failed)
```

---

## Error Handling

```python
class SMSSendError(Exception):
    """Base exception for SMS sending errors."""
    pass

class SMSOptOutError(SMSSendError):
    """Customer has opted out of SMS."""
    pass

class SMSDeliveryError(SMSSendError):
    """SMS delivery failed."""
    def __init__(self, message: str, telnyx_error_code: str | None = None):
        super().__init__(message)
        self.telnyx_error_code = telnyx_error_code

class SMSRateLimitError(SMSSendError):
    """Rate limit exceeded."""
    pass
```

---

## Dependencies on Phase 8

Phase 9 depends on the following from Phase 8:
- Invoice system (for completion summary SMS with amount)
- Job `payment_collected_on_site` field (to determine if invoice SMS needed)

Phase 9 can be started in parallel with Phase 8 for the account setup portion, but full integration requires Phase 8 completion.

---

## Future Enhancements (Not in Phase 9)

- **Automated Cron Jobs**: Day-before reminders, overdue invoice reminders
- **MMS Support**: Send images (e.g., before/after photos)
- **Conversation Threading**: Track full conversation history
- **AI-Powered Responses**: Use AI to handle complex customer replies
- **Multi-Number Support**: Different numbers for different purposes

---

*This document was created on January 28, 2026 by extracting SMS/Telnyx content from PHASE-8-PLANNING.md*
