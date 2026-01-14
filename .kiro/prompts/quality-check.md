---
name: quality-check
category: Development
tags: [quality, testing, linting, type-checking, validation]
description: Run all quality checks and fix any issues found
created: 2025-01-13
updated: 2025-01-13
usage: "@quality-check [optional: specific file or directory]"
related: [new-feature, add-tests, add-logging]
---

# Quality Check

Run all quality checks and fix any issues found.

## What This Prompt Does

When you use `@quality-check`, I will:

1. **Run Ruff** (linting + formatting)
   - `uv run ruff check --fix src/`
   - Fix all auto-fixable violations
   - Report remaining issues

2. **Run MyPy** (type checking)
   - `uv run mypy src/`
   - Report all type errors
   - Suggest fixes for common issues

3. **Run Pyright** (type checking)
   - `uv run pyright src/`
   - Report additional type issues
   - Catch issues MyPy might miss

4. **Run pytest** (testing)
   - `uv run pytest -v`
   - Report test results
   - Show coverage summary

5. **Fix Issues** iteratively
   - Address each category of issues
   - Re-run checks until clean
   - Report final status

## What You Get

- ✅ Zero Ruff violations
- ✅ Zero MyPy errors
- ✅ Zero Pyright errors
- ✅ All tests passing
- ✅ Summary of what was fixed

## Usage

Run on entire project:
```
@quality-check
```

Run on specific file:
```
@quality-check src/grins_platform/services/user_service.py
```

Run on specific directory:
```
@quality-check src/grins_platform/services/
```

## Example Output

```
## Quality Check Results

### Initial State
- Ruff: 3 violations found
- MyPy: 2 errors found
- Pyright: 1 error found
- pytest: 12/12 passing

### Fixes Applied
1. **Ruff**: Auto-fixed 2 violations (unused import, line length)
2. **Ruff**: Manual fix for 1 violation (missing type hint)
3. **MyPy**: Added return type to `process_data` function
4. **Pyright**: Added explicit type annotation for generic parameter

### Final State
- ✅ Ruff: 0 violations
- ✅ MyPy: 0 errors
- ✅ Pyright: 0 errors
- ✅ pytest: 12/12 passing

### Summary
Fixed 4 issues across 2 files. All quality checks now passing.
```

## Quick Commands Reference

```bash
# Individual checks
uv run ruff check --fix src/
uv run mypy src/
uv run pyright src/
uv run pytest -v

# Full validation (all at once)
uv run ruff check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v

# With coverage
uv run pytest --cov=src/grins_platform --cov-report=term-missing
```

## Notes

- This prompt follows the quality workflow defined in `code-standards.md`
- Issues are fixed in order: Ruff → MyPy → Pyright → pytest
- Some issues may cascade (fixing one reveals another)
- The goal is always zero errors across all tools
