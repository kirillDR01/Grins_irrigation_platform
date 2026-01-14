---
name: new-feature
category: Development
tags: [feature, development, testing, logging, quality]
description: Create a complete feature with automatic testing and logging
created: 2025-01-13
updated: 2025-01-13
usage: "@new-feature [feature description]"
related: [add-tests, add-logging, quality-check]
---

# New Feature Development

Create a complete feature with automatic quality integration.

## What This Prompt Does

When you use `@new-feature`, I will:

1. **Write Code** with logging built-in
   - Classes inherit from LoggerMixin
   - Methods log _started, _completed, _failed
   - Type hints on all functions
   - Proper error handling

2. **Write Tests** immediately after code
   - Unit tests for public methods
   - Integration tests for workflows
   - Edge case and error tests
   - Tests in `tests/test_{module}.py`

3. **Run Quality Checks** automatically
   - `uv run ruff check --fix src/`
   - `uv run mypy src/`
   - `uv run pyright src/`
   - `uv run pytest -v`

4. **Fix Issues** until zero errors
   - Fix all Ruff violations
   - Fix all type errors
   - Fix all test failures

5. **Report Completion** with summary
   - What was created
   - Test results
   - Quality check results

## What You Get

- ✅ Feature code with structured logging
- ✅ Comprehensive test suite
- ✅ Zero Ruff violations
- ✅ Zero MyPy/Pyright errors
- ✅ All tests passing
- ✅ Ready to use

## Usage

Just describe the feature you want:

```
@new-feature Create a UserService that handles user registration, 
authentication, and profile management
```

```
@new-feature Create an API endpoint for processing payments with 
Stripe integration
```

```
@new-feature Create a notification service that sends emails and 
push notifications
```

## Example Output

```
## Feature: UserService

### Created Files
- src/grins_platform/services/user_service.py
- src/grins_platform/tests/test_user_service.py

### Implementation Summary
- UserService class with LoggerMixin
- Methods: register_user, authenticate, get_profile, update_profile
- Custom exceptions: UserNotFoundError, AuthenticationError
- Full logging with user.userservice.{action}_{state} pattern

### Test Summary
- 12 tests created
- 12/12 passing
- Coverage: 92%

### Quality Checks
- ✅ Ruff: 0 violations
- ✅ MyPy: 0 errors
- ✅ Pyright: 0 errors
- ✅ pytest: 12/12 passed

### Ready to Use
```python
from grins_platform.services.user_service import UserService

service = UserService()
user = service.register_user(email="user@example.com", password="secure123")
```
```

## Notes

- This prompt follows the quality workflow defined in `code-standards.md`
- All code follows patterns from `service-patterns.md` or `api-patterns.md`
- Tests are comprehensive but not excessive
- Logging is meaningful, not verbose
