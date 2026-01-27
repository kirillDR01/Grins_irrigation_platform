# Ralph Wiggum - Overnight Mode (Single Task)

## CRITICAL: NEVER STOP MODE

You are executing ONE task in **overnight mode**. The loop **NEVER STOPS** until all tasks are complete.

Key rules:

1. **NEVER ask for user input** - Make decisions autonomously
2. **NEVER wait for confirmation** - Proceed with best judgment
3. **NEVER stop the loop** - Skip tasks after 10 failures, continue to next
4. **Retry up to 10 times** - Try different approaches before skipping
5. **ALWAYS output a signal** - So the bash loop knows what happened

## Task Behavior (NEVER STOP MODE)

| Task Type | On Failure | Can Skip? |
|-----------|------------|-----------|
| Regular task | Retry 10x, then skip | YES |
| Checkpoint | Retry fixes 10x, then skip | YES (in never-stop mode) |

**CRITICAL: Even checkpoints can be skipped after 10 failures. The loop prioritizes progress over perfection.**

## Execution Flow

### Step 1: Read Current State

```
Read: .kiro/specs/{spec-name}/tasks.md
Read: .kiro/specs/{spec-name}/activity.md (create if missing)
```

### Step 2: Find Next Task

Find the first task matching `- [ ]` (not started).

Skip tasks that are:
- `- [x]` = Completed
- `- [-]` = In progress (continue this one instead)
- `- [~]` = Queued
- `- [S]` = Skipped

If no `- [ ]` tasks remain, output: `ALL_TASKS_COMPLETE`

### Step 3: Check if Task is a Checkpoint

**CRITICAL:** If task name contains "Checkpoint" (case-insensitive), it is a **quality gate**.

### Step 4: Execute Task

1. Mark task as in-progress using `taskStatus` tool
2. Implement the task following its description
3. Follow code-standards.md requirements (logging, types, tests)
4. For frontend tasks, use `agent-browser` for visual validation

### Step 5: Run Quality Checks

**Backend tasks:**
```bash
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v
```

**Frontend tasks:**
```bash
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm test
```

### Step 6: Handle Results

#### For REGULAR TASKS:

**If task succeeds:**
1. Mark task complete with `taskStatus` tool
2. Log completion in activity.md
3. Output: `TASK_COMPLETE`

**If task fails after 10 retries:**
1. Mark task with `- [S]` (Skipped)
2. Log failure reason in activity.md with all 10 attempts
3. Output: `TASK_SKIPPED: {reason}`

#### For CHECKPOINT TASKS (Quality Gates):

**If ALL quality checks pass:**
1. Log `CHECKPOINT PASSED: {checkpoint name}` in activity.md
2. Mark checkpoint complete with `taskStatus` tool
3. Output: `CHECKPOINT_PASSED: {name}`

**If ANY quality check fails:**
1. Log `CHECKPOINT BLOCKED: {checkpoint name}` with failure details
2. **DO NOT mark checkpoint complete**
3. **Identify and FIX the failing code/tests**
4. Re-run ALL quality checks
5. Repeat fix-and-check cycle up to 10 times
6. If still failing after 10 fix attempts:
   - Log detailed failure report in activity.md with all 10 attempts
   - Mark checkpoint with `- [S]` (Skipped)
   - Output: `CHECKPOINT_SKIPPED: {name}`
   - **CONTINUE to next task (loop never stops)**

### Step 7: Visual Validation (Frontend Tasks)

Before visual validation, verify servers are running:
```bash
curl -s http://localhost:8000/health || echo "BACKEND_DOWN"
curl -s http://localhost:5173 || echo "FRONTEND_DOWN"
```

If servers are down:
1. Log the issue in activity.md
2. Skip visual validation
3. Mark task complete if code changes are correct

## Output Signals (REQUIRED)

You MUST output exactly ONE of these signals at the end:

| Signal | Meaning | Loop Action |
|--------|---------|-------------|
| `TASK_COMPLETE` | Task finished successfully | Continue |
| `TASK_SKIPPED: {reason}` | Regular task skipped after 10 retries | Continue |
| `ALL_TASKS_COMPLETE` | No more tasks | Exit loop (ONLY exit condition) |
| `CHECKPOINT_PASSED: {name}` | Checkpoint validation passed | Continue |
| `CHECKPOINT_SKIPPED: {name}` | Checkpoint skipped after 10 fix attempts | Continue |

**NOTE: The loop ONLY exits on `ALL_TASKS_COMPLETE`. All other signals continue to the next task.**

## Checkpoint Fix Strategy

When a checkpoint fails validation, follow this strategy to fix issues:

1. **Analyze failures:** Read error messages carefully
2. **Identify root cause:** Which files/tests are failing?
3. **Fix systematically:**
   - Ruff errors: Run `uv run ruff check --fix src/`
   - MyPy errors: Fix type annotations
   - Pyright errors: Fix type issues
   - Test failures: Fix the failing tests or the code they test
4. **Re-run checks:** After each fix, re-run ALL quality checks
5. **Document fixes:** Log what was fixed in activity.md
6. **Retry up to 10 times:** Keep trying different approaches
7. **Skip if still failing:** After 10 attempts, skip and continue (never stop)

## Timeout Handling

**Two-Level Timeout System:**

1. **Task-Level Timeout (10 minutes):** The bash script enforces a 10-minute maximum per task. If you don't complete within this time, the task is automatically skipped.

2. **Command-Level Timeout (60 seconds):** Individual commands should complete within 60 seconds. If a command hangs:
   - Cancel the command
   - Log timeout in activity.md
   - Try alternative approach
   - If still fails after 10 attempts, skip task with `TASK_SKIPPED: timeout`
   - **CONTINUE to next task (never stop)**

**NOTE: Timeouts trigger retry attempts, not immediate skips. Try 10 times before skipping.**

## Stagnation Recovery

If you notice:
- Same error appearing 10+ times
- No progress for 5+ minutes
- Command hanging with no output

Then IMMEDIATELY:
1. Abandon current approach
2. Log the issue
3. Try a different approach (up to 10 total attempts)
4. After 10 identical failures: **SKIP task and continue**
5. **NEVER stop the loop** - always continue to next task

## Activity Log Format

```markdown
## [{YYYY-MM-DD HH:MM}] Task {task-id}: {task-name}

### Status: ✅ COMPLETE | ⏭️ SKIPPED | 🔄 IN PROGRESS

### What Was Done
- {description of changes}

### Files Modified
- `path/to/file` - {brief description}

### Quality Check Results
- Ruff: ✅ Pass | ❌ Fail ({count} errors)
- MyPy: ✅ Pass | ❌ Fail ({count} errors)
- Pyright: ✅ Pass | ❌ Fail ({count} errors)
- Tests: ✅ X/X passing | ❌ X failures

### Notes
- {any issues or observations}

---
```

## Example: Checkpoint Execution

```
1. Reading tasks.md...
   - Found: - [ ] 12. Checkpoint - Backend API Complete

2. This is a CHECKPOINT - running ALL quality checks...
   - Ruff: ❌ 101 violations
   - MyPy: ❌ 21 errors
   - Tests: ❌ 75 failures

3. CHECKPOINT BLOCKED - fixing issues (attempt 1/10)...
   - Running: uv run ruff check --fix src/
   - Fixed 95 ruff violations
   - Fixing remaining type errors...

4. Re-running quality checks...
   - Ruff: ✅ Pass
   - MyPy: ❌ 5 errors remaining

5. Fixing remaining issues (attempt 2/10)...
   - Fixed type annotations in conftest.py

6. Re-running quality checks...
   - Ruff: ✅ Pass
   - MyPy: ✅ Pass
   - Pyright: ✅ Pass
   - Tests: ❌ 20 failures (AI API tests)

7. Fixing test failures (attempt 3/10)...
   - Identified schema validation issues
   - Fixed request/response models

8. Re-running quality checks...
   - Ruff: ✅ Pass
   - MyPy: ✅ Pass
   - Pyright: ✅ Pass
   - Tests: ✅ 127/127 passing

9. ALL CHECKS PASS - marking checkpoint complete

CHECKPOINT_PASSED: Backend API Complete
```

## Example: Checkpoint Skipped (After 10 Failures)

```
1. Reading tasks.md...
   - Found: - [ ] 12. Checkpoint - Backend API Complete

2. This is a CHECKPOINT - running ALL quality checks...
   - Tests: ❌ 5 failures (persistent issue)

3-12. Attempts 1-10 to fix the issue...
   - Tried multiple approaches
   - Same 5 tests keep failing
   - Root cause unclear

13. 10 attempts exhausted - SKIPPING checkpoint
   - Logged all 10 attempts in activity.md
   - Marked checkpoint with [S]
   - Continuing to next task (loop never stops)

CHECKPOINT_SKIPPED: Backend API Complete
```

## Remember

- You are running UNATTENDED overnight
- No human is watching
- Make autonomous decisions
- **The loop NEVER stops** - only exits on ALL_TASKS_COMPLETE
- **Retry up to 10 times** before skipping any task
- **Even checkpoints can be skipped** after 10 failures
- Always output a signal
- Log everything for morning review
