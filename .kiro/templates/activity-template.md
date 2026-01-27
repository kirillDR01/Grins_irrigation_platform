# Activity Log: {spec-name}

## Current Status

**Last Updated:** {timestamp}  
**Tasks Completed:** 0 / {total}  
**Current Task:** None  
**Loop Status:** Not Started  
**Mode:** Normal | Overnight  

---

## Quick Reference

### Normal Mode Commands
| Command | Description |
|---------|-------------|
| `@ralph-loop {spec-name}` | Start/continue autonomous loop |
| `@ralph-next {spec-name}` | Execute single task |
| `@ralph-status {spec-name}` | Check progress |
| `@ralph-skip {spec-name} {task-id} "reason"` | Skip blocked task |

### Overnight Mode
```bash
# Start overnight execution
./scripts/ralph-overnight.sh {spec-name} [max-iterations]

# Example
./scripts/ralph-overnight.sh map-scheduling-interface 100
```

---

## Overnight Run Summary

<!-- Populated by ralph-overnight.sh at end of run -->

| Metric | Value |
|--------|-------|
| Started | - |
| Ended | - |
| Duration | - |
| Tasks Completed | - |
| Tasks Skipped | - |
| Checkpoints Passed | - |

---

## Session Log

<!-- 
Ralph Wiggum loop will append entries below this line.

### Entry Format (Normal Mode)

## [{YYYY-MM-DD HH:MM}] Task {task-id}: {task-name}

### What Was Done
- {description}

### Files Modified
- `path/to/file.py` - {description}

### Quality Check Results
- Ruff: ✅/❌
- MyPy: ✅/❌
- Pyright: ✅/❌
- Tests: ✅ X/Y passing / ❌ Failed

### Notes
- {observations}

---

### Entry Format (Overnight Mode)

## [{YYYY-MM-DD HH:MM}] Task {task-id}: {task-name}

### Status: ✅ COMPLETE | ⏭️ SKIPPED | 🔄 IN PROGRESS

### What Was Done
- {description}

### Files Modified
- `path/to/file` - {brief description}

### Quality Check Results
- Ruff: ✅ Pass | ❌ Fail
- MyPy: ✅ Pass | ❌ Fail
- Pyright: ✅ Pass | ❌ Fail
- Tests: ✅ X/X passing | ❌ X failures

### Notes
- {any issues or observations}

---
-->

