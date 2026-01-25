# Validate Quality (Internal)

**Purpose:** Run quality checks and enforce that ALL pass before marking task complete.

**Usage:** Called internally by ralph-loop after implementation.

---

## Parameters

- `task_type`: "backend" | "frontend"
- `retry_attempt`: Current retry attempt number (1, 2, or 3)

---

## Instructions

You are validating code quality. ALL checks must pass for SUCCESS.

### Step 1: Determine Task Type

Based on `task_type` parameter, run appropriate checks.

---

## Backend Quality Checks

Run these checks in order:

### Check 1: Ruff (Linting)

```bash
uv run ruff check src/
```

**Parse output for:**
- ✅ SUCCESS: "All checks passed!" or "0 errors"
- ❌ FAILED: Any error count > 0

**Example Success:**
```
All checks passed!
```

**Example Failure:**
```
src/grins_platform/schemas/schedule_generation.py:45:1: E501 Line too long (92 > 88 characters)
Found 3 errors.
```

### Check 2: MyPy (Type Checking)

```bash
uv run mypy src/
```

**Parse output for:**
- ✅ SUCCESS: "Success: no issues found"
- ❌ FAILED: Any error count > 0

**Example Success:**
```
Success: no issues found in 127 source files
```

**Example Failure:**
```
src/grins_platform/services/schedule_generation_service.py:45: error: Argument 1 has incompatible type "str"; expected "int"
Found 2 errors in 1 file (checked 127 source files)
```

### Check 3: Pyright (Type Checking)

```bash
uv run pyright src/
```

**Parse output for:**
- ✅ SUCCESS: "0 errors, 0 warnings"
- ❌ FAILED: Any error count > 0

**Example Success:**
```
0 errors, 0 warnings, 0 informations
```

**Example Failure:**
```
src/grins_platform/schemas/schedule_generation.py:45:5 - error: Type "str" cannot be assigned to type "int"
1 error, 0 warnings, 0 informations
```

### Check 4: Pytest (Tests)

```bash
uv run pytest -v
```

**Parse output for:**
- ✅ SUCCESS: All tests passed, no failures
- ❌ FAILED: Any test failures or errors

**Example Success:**
```
======================== 127 passed in 5.23s ========================
```

**Example Failure:**
```
FAILED src/grins_platform/tests/test_schedule_generation.py::test_coordinate_fields - AssertionError: assert None is not None
======================== 2 failed, 125 passed in 5.45s ========================
```

---

## Frontend Quality Checks

Run these checks in order:

### Check 1: ESLint (Linting)

```bash
cd frontend && npm run lint
```

**Parse output for:**
- ✅ SUCCESS: "0 problems" or no errors
- ❌ FAILED: Any error count > 0

**Example Success:**
```
✔ No ESLint warnings or errors
```

**Example Failure:**
```
/frontend/src/features/schedule/components/MapView.tsx
  45:10  error  'useState' is not defined  no-undef
  52:5   error  Missing return type on function  @typescript-eslint/explicit-function-return-type

✖ 2 problems (2 errors, 0 warnings)
```

### Check 2: TypeScript (Type Checking)

```bash
cd frontend && npm run typecheck
```

**Parse output for:**
- ✅ SUCCESS: "0 errors"
- ❌ FAILED: Any error count > 0

**Example Success:**
```
tsc --noEmit
```

**Example Failure:**
```
src/features/schedule/components/MapView.tsx:45:10 - error TS2304: Cannot find name 'useState'.
src/features/schedule/types/index.ts:12:3 - error TS2322: Type 'string' is not assignable to type 'number'.

Found 2 errors in 2 files.
```

### Check 3: Vitest (Tests)

```bash
cd frontend && npm test
```

**Parse output for:**
- ✅ SUCCESS: All tests passed
- ❌ FAILED: Any test failures

**Example Success:**
```
✓ src/features/schedule/components/MapView.test.tsx (5 tests) 234ms
Test Files  1 passed (1)
     Tests  5 passed (5)
```

**Example Failure:**
```
✓ src/features/schedule/components/MapView.test.tsx (4 tests) 234ms
✗ src/features/schedule/components/MapView.test.tsx > renders map correctly
  AssertionError: expected null to be defined

Test Files  1 failed (1)
     Tests  4 passed | 1 failed (5)
```

---

## Output Format

### On SUCCESS

```
✅ Quality Checks PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Type: {backend|frontend}
Attempt: {retry_attempt}/3

Results:
{For backend:}
  - Ruff: ✅ Pass (0 errors)
  - MyPy: ✅ Pass (0 errors)
  - Pyright: ✅ Pass (0 errors)
  - Tests: ✅ Pass (127/127 passing)

{For frontend:}
  - ESLint: ✅ Pass (0 problems)
  - TypeScript: ✅ Pass (0 errors)
  - Tests: ✅ Pass (5/5 passing)

Status: READY TO MARK COMPLETE
```

### On FAILURE

```
❌ Quality Checks FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Type: {backend|frontend}
Attempt: {retry_attempt}/3

Results:
{For backend:}
  - Ruff: ❌ FAILED (3 errors)
  - MyPy: ✅ Pass (0 errors)
  - Pyright: ❌ FAILED (1 error)
  - Tests: ❌ FAILED (2/127 failed)

{For frontend:}
  - ESLint: ❌ FAILED (2 errors)
  - TypeScript: ✅ Pass (0 errors)
  - Tests: ❌ FAILED (1/5 failed)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Error Details:

{Paste actual error messages from failed checks}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next Steps:
{If retry_attempt < 3:}
  1. Fix the errors listed above
  2. Re-run quality checks
  3. This will be attempt {retry_attempt + 1}/3

{If retry_attempt >= 3:}
  ⚠️ RETRY LIMIT REACHED
  
  This task has failed quality checks 3 times.
  
  Action Required: USER INPUT REQUIRED
  
  Please review the errors and either:
  - Fix the underlying issue manually
  - Skip this task with @ralph-skip
  - Adjust the task requirements
```

---

## Retry Logic

### Attempt 1-2: Continue with Retry

1. Output FAILED with error details
2. Agent should fix the errors
3. Re-run quality checks
4. Increment retry_attempt

### Attempt 3: Stop and Request User Input

1. Output FAILED with error details
2. Output "RETRY LIMIT REACHED"
3. Output "USER INPUT REQUIRED"
4. Stop execution (don't continue to next task)

---

## Error Parsing Examples

### Ruff Error Parsing

```bash
# Run check
uv run ruff check src/

# Parse output
if output contains "All checks passed!" or "0 errors":
    ruff_status = "✅ Pass (0 errors)"
else:
    # Extract error count
    match = re.search(r"Found (\d+) error", output)
    error_count = match.group(1) if match else "unknown"
    ruff_status = f"❌ FAILED ({error_count} errors)"
```

### MyPy Error Parsing

```bash
# Run check
uv run mypy src/

# Parse output
if output contains "Success: no issues found":
    mypy_status = "✅ Pass (0 errors)"
else:
    # Extract error count
    match = re.search(r"Found (\d+) error", output)
    error_count = match.group(1) if match else "unknown"
    mypy_status = f"❌ FAILED ({error_count} errors)"
```

### Pytest Error Parsing

```bash
# Run check
uv run pytest -v

# Parse output
if output contains "passed" and not contains "failed":
    # Extract passed count
    match = re.search(r"(\d+) passed", output)
    passed_count = match.group(1) if match else "unknown"
    pytest_status = f"✅ Pass ({passed_count}/{passed_count} passing)"
else:
    # Extract failed and passed counts
    failed_match = re.search(r"(\d+) failed", output)
    passed_match = re.search(r"(\d+) passed", output)
    failed_count = failed_match.group(1) if failed_match else "0"
    passed_count = passed_match.group(1) if passed_match else "0"
    total = int(failed_count) + int(passed_count)
    pytest_status = f"❌ FAILED ({passed_count}/{total} passing, {failed_count} failed)"
```

---

## Integration with Ralph-Loop

Ralph-loop should call this prompt after implementation:

```markdown
### Step 5: Validate Work

1. Determine task type:
   - If task modifies src/grins_platform/ → backend
   - If task modifies frontend/ → frontend

2. Call @validate-quality:
   @validate-quality {task_type} {retry_attempt}

3. Parse output:
   - If "Quality Checks PASSED" → proceed to Step 6
   - If "Quality Checks FAILED" and retry_attempt < 3:
     a. Read error details
     b. Fix the issues
     c. Increment retry_attempt
     d. Go back to Step 4 (re-implement)
   - If "Quality Checks FAILED" and retry_attempt >= 3:
     a. Output "USER INPUT REQUIRED"
     b. Stop execution
```

---

## Safety Rules

1. **Never skip quality checks** - ALL must pass
2. **Never mark complete if checks fail** - Enforce strictly
3. **Always show error details** - Help agent fix issues
4. **Respect retry limit** - Stop after 3 attempts
5. **Parse output carefully** - Don't misinterpret success/failure

---

## Testing

To test this prompt:

```bash
# Test 1: Backend task with passing checks
@validate-quality backend 1

# Test 2: Backend task with failing checks
# (Introduce a linting error first)
@validate-quality backend 1

# Test 3: Frontend task with passing checks
@validate-quality frontend 1

# Test 4: Retry limit reached
@validate-quality backend 3
```

---

## Known Limitations

1. **Tool output changes** - If ruff/mypy/pytest change output format, parsing may break
2. **Partial failures** - If one check hangs, others won't run
3. **No parallel checks** - Checks run sequentially (slower but more reliable)
4. **No check skipping** - Can't skip a check even if not relevant

### Future Enhancements

- Add timeout per check (e.g., 2 minutes max)
- Add parallel check execution
- Add check-specific retry logic
- Add smart error categorization (syntax vs logic vs type)
