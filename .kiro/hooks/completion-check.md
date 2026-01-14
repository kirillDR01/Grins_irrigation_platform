# Completion Check Hook

This hook validates code quality before marking a task as complete.

## Configuration

To enable this hook, add to your agent configuration or use Kiro's hook UI.

## Trigger
- **Event**: Stop (when agent finishes a task)

## Action
Run the following validation commands:

```bash
# Full quality validation
echo "🔍 Running Quality Checks..."

# Linting
echo "📋 Ruff Check..."
uv run ruff check src/

# Type checking (MyPy)
echo "🔷 MyPy Check..."
uv run mypy src/

# Type checking (Pyright)
echo "🔶 Pyright Check..."
uv run pyright src/

# Testing
echo "🧪 Running Tests..."
uv run pytest -v

# Summary
echo ""
echo "═══════════════════════════════════════"
if [ $? -eq 0 ]; then
    echo "✅ All quality checks passed!"
else
    echo "❌ Quality checks failed. Please fix issues before completing."
fi
echo "═══════════════════════════════════════"
```

## Expected Output

### Success
```
🔍 Running Quality Checks...
📋 Ruff Check...
All checks passed!
🔷 MyPy Check...
Success: no issues found
🔶 Pyright Check...
0 errors, 0 warnings, 0 informations
🧪 Running Tests...
75 passed in 0.45s

═══════════════════════════════════════
✅ All quality checks passed!
═══════════════════════════════════════
```

### Failure
```
🔍 Running Quality Checks...
📋 Ruff Check...
Found 3 errors.

═══════════════════════════════════════
❌ Quality checks failed. Please fix issues before completing.
═══════════════════════════════════════
```

## Purpose

This hook ensures that no task is marked complete without passing all quality checks. It's the final safety net in the quality workflow.

## Validation Criteria

A task passes completion check when:
- ✅ Ruff reports zero violations
- ✅ MyPy reports zero errors
- ✅ Pyright reports zero errors
- ✅ All tests pass

## Notes

- This hook runs automatically when the agent finishes
- If checks fail, the agent should fix issues before reporting completion
- This is the enforcement mechanism for quality standards
