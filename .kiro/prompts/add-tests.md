---
name: add-tests
category: Testing
tags: [testing, pytest, unit-tests, integration-tests]
description: Generate comprehensive test suite for existing code
created: 2025-01-13
updated: 2025-01-13
usage: "@add-tests [file or module to test]"
related: [new-feature, quality-check]
---

# Add Tests

Generate a comprehensive test suite for existing code.

## What This Prompt Does

When you use `@add-tests`, I will:

1. **Analyze the Code**
   - Identify public methods and functions
   - Understand dependencies and interactions
   - Find edge cases and error conditions

2. **Generate Test Suite**
   - Unit tests for each public method
   - Integration tests for workflows
   - Edge case tests
   - Error handling tests
   - Mock tests for dependencies

3. **Create Test File**
   - Location: `tests/test_{module}.py`
   - Proper fixtures and setup
   - Clear test naming
   - Comprehensive assertions

4. **Run and Validate**
   - Execute all tests
   - Fix any failures
   - Ensure coverage targets met

## Test Types Generated

### Unit Tests
- Test each method individually
- Valid input scenarios
- Invalid input scenarios
- Return value verification

### Integration Tests
- Test component interactions
- Workflow testing
- End-to-end scenarios

### Edge Case Tests
- Empty inputs
- Boundary values
- Null/None handling
- Large inputs

### Error Tests
- Exception handling
- Error messages
- Recovery behavior

### Mock Tests
- External dependencies
- Database operations
- API calls

## Usage

Point to the code you want tested:

```
@add-tests src/grins_platform/services/user_service.py
```

```
@add-tests UserService class
```

```
@add-tests the payment processing module
```

## Example Output

```
## Tests Added: UserService

### Test File
- Created: src/grins_platform/tests/test_user_service.py

### Test Classes
- TestUserServiceInit (2 tests)
- TestRegisterUser (5 tests)
- TestAuthenticate (4 tests)
- TestGetProfile (3 tests)
- TestUpdateProfile (4 tests)

### Test Summary
- Total: 18 tests
- Passing: 18/18
- Coverage: 89%

### Sample Tests
```python
class TestRegisterUser:
    def test_register_with_valid_email_creates_user(self):
        """Test successful registration."""
        
    def test_register_with_invalid_email_raises_validation_error(self):
        """Test validation error for invalid email."""
        
    def test_register_with_existing_email_raises_duplicate_error(self):
        """Test duplicate email handling."""
        
    def test_register_logs_started_and_completed_events(self):
        """Test logging behavior."""
```
```

## Coverage Targets

| Code Type | Target |
|-----------|--------|
| Services | 85%+ |
| API endpoints | 80%+ |
| Utilities | 70%+ |
| Models | 60%+ |

## Notes

- Tests follow patterns from `code-standards.md`
- Uses pytest fixtures for setup
- Includes logging verification where appropriate
- Mocks external dependencies
- Runs `uv run pytest -v` to validate
