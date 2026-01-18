# Kiro Hooks Guide

## Overview

Hooks are automated actions that trigger on specific IDE events. They can run commands or prompt the agent to take action.

## Current Hooks

| Hook | File | Trigger | Status | Purpose |
|------|------|---------|--------|---------|
| Quality Completion Check | `completion-check.kiro.hook` | agentStop | **Disabled** | Runs quality checks when agent finishes |
| Quality Reminder | `quality-reminder.kiro.hook` | agentSpawn | **Disabled** | Shows quality standards when agent starts |
| Auto Lint | `auto-lint.json` | fileEdited | **Disabled** | Runs ruff on Python file edits |
| Auto Typecheck | `auto-typecheck.json` | fileEdited | **Disabled** | Runs mypy on Python file edits |
| Test on Complete | `test-on-complete.json` | agentStop | **Disabled** | Runs pytest when agent finishes |
| Quality on Submit | `quality-on-submit.json` | promptSubmit | **Disabled** | Quick lint check on prompt submit |

## Hook Triggers

| Trigger | When It Fires |
|---------|---------------|
| `agentSpawn` | When a new agent session starts |
| `agentStop` | When the agent finishes responding |
| `promptSubmit` | When you send a message to the agent |
| `fileEdited` | When you save a file (with pattern matching) |
| `fileCreated` | When a new file is created |
| `fileDeleted` | When a file is deleted |
| `userTriggered` | Manual trigger only |

## Hook Actions

| Action | Description |
|--------|-------------|
| `runCommand` | Executes a shell command |
| `askAgent` | Sends a prompt to the agent |

## How to Enable/Disable Hooks

### For `.json` files:
```json
{
  "disabled": false,  // Change to true to disable
  ...
}
```

### For `.kiro.hook` files:
```json
{
  "enabled": true,  // Change to false to disable
  ...
}
```

## Recommended Configurations

### Minimal (Current - All Disabled)
Best for: General development without interruptions
- All hooks disabled
- Run quality checks manually when needed

### Light Quality Checks
Best for: Catching issues early without slowdown
- Enable: `auto-lint.json` (ruff on save)
- Keep disabled: Everything else

To enable:
```bash
# Edit .kiro/hooks/auto-lint.json
# Change "disabled": true to "disabled": false
```

### Full Quality Pipeline
Best for: Strict quality enforcement (requires fixing pyright errors first)
- Enable: `completion-check.kiro.hook`
- Enable: `quality-reminder.kiro.hook`

**Warning:** The full pipeline includes pyright which currently has 119 errors in test files. Fix those first or modify the hook to exclude pyright.

## Manual Quality Commands

Instead of hooks, run these manually:

```bash
# Quick lint check
uv run ruff check src/

# Lint with auto-fix
uv run ruff check --fix src/

# Type checking (mypy)
uv run mypy src/

# Type checking (pyright) - has errors in tests
uv run pyright src/

# Run all tests
uv run pytest -v

# Full quality pipeline (excluding pyright)
uv run ruff check src/ && uv run mypy src/ && uv run pytest -v
```

## Creating Custom Hooks

### Basic Structure (`.json` format)
```json
{
  "name": "My Hook",
  "version": "1.0.0",
  "description": "What this hook does",
  "disabled": false,
  "when": {
    "type": "agentStop"
  },
  "then": {
    "type": "runCommand",
    "command": "echo 'Hook executed'"
  }
}
```

### File Pattern Hook
```json
{
  "name": "Lint Python Files",
  "version": "1.0.0",
  "disabled": false,
  "when": {
    "type": "fileEdited",
    "patterns": ["src/**/*.py", "tests/**/*.py"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Check the edited file for issues"
  }
}
```

### Agent Prompt Hook
```json
{
  "name": "Remind About Tests",
  "version": "1.0.0",
  "disabled": false,
  "when": {
    "type": "agentStop"
  },
  "then": {
    "type": "askAgent",
    "prompt": "Did you write tests for the changes you made?"
  }
}
```

## Troubleshooting

### "Hook execution failed with exit code 1"
- The hook's command returned a non-zero exit code
- Check if the command works manually
- Common cause: Quality check found errors

### Hook not triggering
- Check if `disabled: true` or `enabled: false`
- Verify the trigger type matches your action
- For file hooks, check the pattern matches your file

### Hook runs too often
- Disable hooks you don't need
- Use more specific file patterns
- Consider using `userTriggered` for manual-only hooks

## Current Status Summary

All hooks are currently **disabled** to prevent the "exit code 1" errors that were occurring. The errors were caused by:

1. `completion-check.kiro.hook` running pyright which has 119 type errors in test files
2. The hook command chain failing when pyright reported errors

To use hooks effectively:
1. Start with all disabled (current state)
2. Enable one at a time as needed
3. Test each hook works before enabling the next
4. Fix pyright errors before enabling the full quality pipeline
