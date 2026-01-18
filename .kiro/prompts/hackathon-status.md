# Hackathon Status

Generate a comprehensive status report for hackathon submission.

## Instructions

1. **Gather Metrics**:
   - Count API endpoints in `src/grins_platform/api/v1/`
   - Run `uv run pytest -v --tb=no -q` to count tests
   - Run `uv run pytest --cov=src/grins_platform --cov-report=term-missing` for coverage
   - Check quality: `uv run ruff check src/ && uv run mypy src/`

2. **Check Spec Progress**:
   - Read all tasks.md files in `.kiro/specs/`
   - Calculate completion percentage for each spec

3. **Generate Report**:

```markdown
# 🏆 Hackathon Status Report

**Date:** {current date}
**Project:** Grin's Irrigation Platform

## Progress Summary

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| API Endpoints | X | 42 | ✅/⚠️/❌ |
| Tests Passing | X | 700+ | ✅/⚠️/❌ |
| Code Coverage | X% | 90%+ | ✅/⚠️/❌ |
| Quality Checks | Pass/Fail | Pass | ✅/❌ |

## Feature Completion

| Feature | Tasks | Complete | Status |
|---------|-------|----------|--------|
| Customer Management | X/Y | Z% | ✅/⚠️/❌ |
| Field Operations | X/Y | Z% | ✅/⚠️/❌ |

## Hackathon Criteria Checklist

- [ ] Working end-to-end flow
- [ ] 25-30 API endpoints
- [ ] 70%+ code coverage
- [ ] Zero linting errors
- [ ] Complete documentation
- [ ] Kiro usage (specs, prompts, agents)

## Next Steps
1. {highest priority item}
2. {second priority}
3. {third priority}
```

4. **Provide Recommendations**:
   - Identify gaps against hackathon criteria
   - Suggest priority actions to close gaps

## Usage

```
@hackathon-status
```

## Related Prompts
- `@task-progress` - Detailed task breakdown
- `@feature-complete-check` - Verify specific feature
- `@demo-prep` - Prepare for demo
