# Checkpoint

Save your progress: run quality checks, update devlog, and commit changes.

## Instructions

Execute these steps in order:

### 1. Run Quality Checks
```bash
uv run ruff check src/
uv run mypy src/
uv run pytest -v --tb=short
```

If any checks fail, report the issues but continue with the checkpoint.

### 2. Update DEVLOG

Add an entry to DEVLOG.md at the TOP (after "## Recent Activity"):

```markdown
## [YYYY-MM-DD HH:MM] - CHECKPOINT: {Brief Description}

### What Was Accomplished
- {List of completed work since last checkpoint}

### Quality Status
- Ruff: {Pass/X violations}
- MyPy: {Pass/X errors}
- Tests: {X/Y passing}

### Next Steps
- {What to work on next}
```

### 3. Stage and Commit

Generate a meaningful commit message based on the work done:

```bash
git add -A
git commit -m "{type}: {description}

- {bullet point of change 1}
- {bullet point of change 2}

Checkpoint: {quality status summary}"
```

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `docs:` - Documentation
- `chore:` - Maintenance

### 4. Report Summary

```
✅ Checkpoint Complete

Quality:
  - Ruff: {status}
  - MyPy: {status}
  - Tests: {X/Y passing}

Committed: {commit hash}
Message: {commit message}

Ready to continue with: {next task}
```

## Usage

```
@checkpoint
@checkpoint "Completed service layer for jobs"
```

## Related Prompts
- `@quality-check` - Just run quality checks
- `@devlog-entry` - Just update devlog
- `@git-commit-push` - Just commit and push
