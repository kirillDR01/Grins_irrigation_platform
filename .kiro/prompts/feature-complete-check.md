# Feature Complete Check

Verify a feature meets the Definition of Done before marking it complete.

## Instructions

1. **Identify Feature**: Determine which feature/spec to check (from user input or most recent spec)

2. **Read Definition of Done**: Reference the project's Definition of Done from PHASE-2-PLANNING.md:
   - All tasks completed
   - All tests passing
   - Quality checks passing

3. **Run Verification**:

### Task Completion Check
- Read `.kiro/specs/{feature}/tasks.md`
- Count tasks: `[ ]` not started, `[-]` in progress, `[x]` complete
- List any incomplete tasks

### Test Check
```bash
uv run pytest -v --tb=no
```
- All tests must pass
- No skipped tests (unless documented)

### Quality Check
```bash
uv run ruff check src/
uv run mypy src/
```
- Zero Ruff violations
- Zero MyPy errors

### Coverage Check (Optional)
```bash
uv run pytest --cov=src/grins_platform --cov-report=term-missing
```
- Target: 85%+ for services, 80%+ for API

4. **Generate Report**:

```markdown
# Feature Complete Check: {feature-name}

## Task Status
- Total Tasks: X
- Completed: Y (Z%)
- In Progress: A
- Not Started: B

### Incomplete Tasks:
- [ ] {task 1}
- [ ] {task 2}

## Quality Status

| Check | Status | Details |
|-------|--------|---------|
| Ruff | ✅/❌ | {X violations} |
| MyPy | ✅/❌ | {X errors} |
| Tests | ✅/❌ | {X/Y passing} |
| Coverage | ✅/❌ | {X%} |

## Verdict

{✅ FEATURE COMPLETE - Ready for merge/demo}
or
{❌ NOT COMPLETE - See issues above}

## Required Actions (if not complete):
1. {action 1}
2. {action 2}
```

5. **Provide Guidance**: If not complete, suggest the fastest path to completion.

## Usage

```
@feature-complete-check
@feature-complete-check field-operations
@feature-complete-check customer-management
```

## Related Prompts
- `@hackathon-status` - Overall project status
- `@next-task` - Continue working on incomplete tasks
- `@checkpoint` - Save progress
