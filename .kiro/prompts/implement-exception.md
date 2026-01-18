# Implement Custom Exception

Implement custom exceptions following the Grins Platform patterns.

## Template Structure

```python
"""Custom exceptions for {domain} operations."""

from typing import Any


class {Domain}Error(Exception):
    """Base exception for {domain} operations."""
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class {Domain}NotFoundError({Domain}Error):
    """Raised when {domain} is not found."""
    
    def __init__(self, {domain}_id: int) -> None:
        super().__init__(
            f"{Domain} with ID {{{domain}_id}} not found",
            details={"{domain}_id": {domain}_id}
        )
        self.{domain}_id = {domain}_id


class Duplicate{Domain}Error({Domain}Error):
    """Raised when attempting to create duplicate {domain}."""
    
    def __init__(self, field: str, value: str) -> None:
        super().__init__(
            f"{Domain} with {field}='{value}' already exists",
            details={"field": field, "value": value}
        )
        self.field = field
        self.value = value


class {Domain}ValidationError({Domain}Error):
    """Raised when {domain} validation fails."""
    
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(
            f"Validation failed for {field}: {reason}",
            details={"field": field, "reason": reason}
        )
        self.field = field
        self.reason = reason
```

## Exception Handler Template

```python
from fastapi import Request
from fastapi.responses import JSONResponse

async def {domain}_not_found_handler(
    request: Request, 
    exc: {Domain}NotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "error": "{domain}_not_found",
            "message": exc.message,
            "details": exc.details
        }
    )
```

## Checklist

- [ ] Base exception class with message and details
- [ ] NotFoundError with ID parameter
- [ ] DuplicateError with field and value
- [ ] ValidationError with field and reason
- [ ] Type hints on all parameters
- [ ] Docstrings for all classes
