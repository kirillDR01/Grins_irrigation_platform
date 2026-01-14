---
name: add-logging
category: Logging
tags: [logging, structlog, monitoring, observability]
description: Add structured logging to existing code
created: 2025-01-13
updated: 2025-01-13
usage: "@add-logging [file or module]"
related: [new-feature, quality-check]
---

# Add Logging

Add comprehensive structured logging to existing code.

## What This Prompt Does

When you use `@add-logging`, I will:

1. **Analyze the Code**
   - Identify classes and functions
   - Find key operations to log
   - Determine appropriate domains

2. **Add Logging Infrastructure**
   - Import logging utilities
   - Add LoggerMixin to classes
   - Set DOMAIN attributes

3. **Add Log Statements**
   - `log_started` at method entry
   - `log_completed` on success
   - `log_failed` on errors
   - `log_validated` for validations
   - `log_rejected` for rejections

4. **Validate Changes**
   - Run quality checks
   - Ensure no regressions
   - Verify log output

## Logging Pattern

### Namespace Format
```
{domain}.{component}.{action}_{state}
```

### States
- `_started`: Operation beginning
- `_completed`: Successful completion
- `_failed`: Error occurred
- `_validated`: Validation passed
- `_rejected`: Validation failed

### Domains
- `user`: User-related operations
- `database`: Data access operations
- `api`: API request handling
- `validation`: Input validation
- `business`: Business logic
- `system`: System operations

## Usage

Point to the code you want to add logging to:

```
@add-logging src/grins_platform/services/payment_service.py
```

```
@add-logging PaymentService class
```

```
@add-logging the order processing module
```

## Example Transformation

### Before
```python
class PaymentService:
    def process_payment(self, amount: Decimal, card_token: str) -> PaymentResult:
        if amount <= 0:
            raise ValidationError("Amount must be positive")
        
        try:
            result = self.gateway.charge(card_token, amount)
            return PaymentResult(success=True, transaction_id=result.id)
        except GatewayError as e:
            raise PaymentError(f"Payment failed: {e}")
```

### After
```python
from grins_platform.logging import LoggerMixin


class PaymentService(LoggerMixin):
    DOMAIN = "business"
    
    def process_payment(self, amount: Decimal, card_token: str) -> PaymentResult:
        self.log_started("process_payment", amount=float(amount))
        
        if amount <= 0:
            self.log_rejected("process_payment", reason="invalid_amount", amount=float(amount))
            raise ValidationError("Amount must be positive")
        
        self.log_validated("payment_amount", amount=float(amount))
        
        try:
            result = self.gateway.charge(card_token, amount)
            self.log_completed("process_payment", transaction_id=result.id)
            return PaymentResult(success=True, transaction_id=result.id)
        except GatewayError as e:
            self.log_failed("process_payment", error=e, amount=float(amount))
            raise PaymentError(f"Payment failed: {e}")
```

## Log Output Example

```json
{"event": "business.paymentservice.process_payment_started", "amount": 99.99, "timestamp": "2025-01-13T15:30:00Z", "level": "info"}
{"event": "business.paymentservice.payment_amount_validated", "amount": 99.99, "timestamp": "2025-01-13T15:30:00Z", "level": "info"}
{"event": "business.paymentservice.process_payment_completed", "transaction_id": "txn_123", "timestamp": "2025-01-13T15:30:01Z", "level": "info"}
```

## What NOT to Log

- ❌ Passwords or tokens
- ❌ Full credit card numbers
- ❌ Personal identification numbers
- ❌ API keys or secrets
- ❌ Every internal function call

## Notes

- Follows patterns from `code-standards.md`
- Uses LoggerMixin for classes
- Uses get_logger() for standalone functions
- Includes request_id correlation for APIs
- Runs quality checks after changes
