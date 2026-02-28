# Ralph Wiggum Loop Patterns

## Purpose

This steering document defines the behavior rules for the Ralph Wiggum autonomous execution loop. It ensures consistent, safe, and effective task execution across all specs.

## Core Principles

### 1. Single Task Focus
**ONLY WORK ON A SINGLE TASK AT A TIME.**

- Execute one task completely before moving to the next
- Do not batch multiple tasks together
- Do not skip ahead to "easier" tasks
- Complete sub-tasks before marking parent complete

### 2. Quality First
**ALL QUALITY CHECKS MUST PASS BEFORE MARKING COMPLETE.**

No exceptions. If quality checks fail:
1. Fix the issues
2. Re-run quality checks
3. Only mark complete when all pass

### 3. Checkpoint Handling
**CHECKPOINTS ARE QUALITY GATES - ALL CHECKS MUST PASS.**

Checkpoints are **mandatory quality gates** that ensure code quality before proceeding. When you reach a task containing "Checkpoint" in its name:

1. **Run ALL quality checks:**
   - Backend: `uv run ruff check src/`, `uv run mypy src/`, `uv run pyright src/`, `uv run pytest -v`
   - Frontend: `cd frontend && npm run lint`, `npm run typecheck`, `npm test`

2. **If ALL checks pass:**
   - Log `CHECKPOINT PASSED: {checkpoint name}` in activity.md
   - Mark the checkpoint task as complete
   - Continue to the next task

3. **If ANY check fails:**
   - Log `CHECKPOINT BLOCKED: {checkpoint name}` with failure details
   - **DO NOT mark checkpoint complete**
   - **DO NOT skip the checkpoint**
   - **FIX the issues** - go back to previous tasks and fix the failing code
   - Re-run quality checks
   - Retry up to 5 times to fix issues
   - If still failing after 5 fix attempts, output `CHECKPOINT_FAILED: {name}` and stop

**CRITICAL: Checkpoints are NOT skippable. They ensure code quality is maintained throughout the project.**

### 4. Activity Logging
**LOG EVERY ACTION IN ACTIVITY.MD.**

Every task execution must be logged with:
- Timestamp
- What was done
- Files modified
- Quality check results
- Any issues or notes

### 5. Workspace Safety
**FOLLOW WORKSPACE-SAFETY.MD AT ALL TIMES.**

- Only modify files within workspace
- Use relative paths
- Never execute destructive commands
- All changes must be reversible via git

---

## Task State Detection

### Checkbox Patterns

Parse `tasks.md` for these patterns:

| Pattern | State | Action |
|---------|-------|--------|
| `- [ ]` | Not started | Execute this task |
| `- [x]` | Completed | Skip |
| `- [-]` | In progress | Continue this task |
| `- [~]` | Queued | Skip for now |
| `- [S]` | Skipped | Skip (user requested) |

### Task Hierarchy

Tasks can have sub-tasks (indented):

```markdown
- [ ] 2. Backend - Appointments
  - [ ] 2.1 Create appointments table migration
  - [ ] 2.2 Create Appointment SQLAlchemy model
```

Rules:
- Execute sub-tasks before parent
- Parent is complete only when ALL sub-tasks are complete
- Find the deepest incomplete task first

### Checkpoint Detection

A task is a checkpoint if its name contains "Checkpoint" (case-insensitive):

```markdown
- [ ] 4. Checkpoint - Backend Complete
- [ ] 6. Checkpoint - Frontend Foundation
```

---

## Quality Requirements

### Backend Tasks

Before marking ANY backend task complete, run:

```bash
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v
```

**ALL must pass with zero errors.**

### Frontend Tasks

Before marking ANY frontend task complete, run:

```bash
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm test
```

**ALL must pass with zero errors.**

### Visual Validation

For frontend UI tasks, also validate visually:

```bash
agent-browser open http://localhost:5173
agent-browser snapshot -i
agent-browser is visible "[data-testid='expected-element']"
```

---

## Activity Log Format

### File Location

Each spec has its own activity log:
```
.kiro/specs/{spec-name}/activity.md
```

### Entry Format

```markdown
## [{YYYY-MM-DD HH:MM}] Task {task-id}: {task-name}

### What Was Done
- {bullet point description of changes}
- {another change}

### Files Modified
- `path/to/file1.py` - {brief description}
- `path/to/file2.py` - {brief description}

### Quality Check Results
- Ruff: ✅ Pass
- MyPy: ✅ Pass
- Pyright: ✅ Pass
- Tests: ✅ 127/127 passing

### Notes
- {any issues encountered}
- {decisions made}
- {things to revisit}
```

### Status Update

Update the "Current Status" section at the top of activity.md after each task:

```markdown
## Current Status
**Last Updated:** {timestamp}
**Tasks Completed:** {completed} / {total}
**Current Task:** {task-id} - {task-name}
**Loop Status:** Running / Paused at Checkpoint / Complete
```

---

## Failure Handling

### Graduated Response - NEVER STOP MODE

The Ralph Wiggum loop is designed to **NEVER STOP** until all tasks are complete. It will keep trying to fix errors and only skip tasks after 10 identical consecutive failures.

```
Task Fails
    │
    ▼
┌─────────────────┐
│  Retry 1/10     │──► Success? → Continue, reset counter
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  Retry 2/10     │──► Success? → Continue, reset counter
│  (try different │
│   approach)     │
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  Retry 3-9/10   │──► Success? → Continue, reset counter
│  (keep trying   │
│   alternatives) │
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  Retry 10/10    │──► Success? → Continue
│  (final attempt)│
└─────────────────┘
    │ Fail (10 identical failures)
    ▼
┌─────────────────┐
│  SKIP TASK      │──► Mark [S], log reason, CONTINUE to next task
│  (never stop)   │
└─────────────────┘
```

### Retry Strategies

1. **First retry:** Same approach, check for typos/errors
2. **Second retry:** Try alternative implementation
3. **Third retry:** Simplify scope if possible
4. **Retries 4-9:** Keep trying different approaches, check logs, analyze errors
5. **Retry 10:** Final attempt with most conservative approach

### CRITICAL: The Loop NEVER Stops

The overnight loop is designed for unattended execution. It will:
- ✅ Keep retrying errors (up to 10 times per task)
- ✅ Try to fix issues automatically
- ✅ Skip tasks after 10 identical failures
- ✅ Continue to the next task
- ✅ Run until ALL tasks are complete or max iterations reached
- ❌ NEVER stop for user input
- ❌ NEVER halt on checkpoint failures (skip and continue)
- ❌ NEVER wait for confirmation

### Logging Failures

Log each retry attempt:

```markdown
## [{timestamp}] Task {task-id}: RETRY {n}/10

### Issue
{description of what failed}

### Approach
{what will be tried differently}

### Previous Attempts
{summary of what was already tried}
```

### After 10 Failures - Auto Skip

When 10 identical failures occur, the task is automatically skipped:

```markdown
## [{timestamp}] Task {task-id}: AUTO-SKIPPED (10 identical failures)

### Issue
{detailed description of the problem}

### Attempts Made
1. {first approach and result}
2. {second approach and result}
...
10. {tenth approach and result}

### Reason for Skip
Same error occurred 10 consecutive times. Task marked as [S] and loop continues.

### Next Task
Proceeding to next incomplete task...
```

---

## Loop Control

### Starting the Loop

```
@ralph-loop {spec-name}
```

Starts from the first incomplete task and continues until checkpoint or completion.

### Single Task Execution

```
@ralph-next {spec-name}
```

Executes only the next task, then stops.

### Checking Status

```
@ralph-status {spec-name}
```

Shows progress without executing anything.

### Skipping Tasks

```
@ralph-skip {spec-name} {task-id} "{reason}"
```

Marks a task as skipped and moves to the next.

### Stopping the Loop

The loop stops automatically ONLY when:
1. All tasks are complete (ALL_TASKS_COMPLETE)
2. Max iterations reached (default 100)

**The loop NEVER stops for:**
- Checkpoint failures (skips and continues)
- Task failures (retries 10x, then skips)
- Stagnation (skips task after 10 identical failures)
- Errors (tries to fix, then skips)

---

## Inline Visual Validation Pattern

### Task Structure for UI Components

Every UI component task group MUST include an inline validation sub-task:

```markdown
- [ ] 6. MapMarker Component
  - [ ] 6.1 Create MapMarker component
  - [ ] 6.2 Add data-testid to MapMarker
  - [ ] 6.3 **Validate MapMarker renders correctly** ← INLINE VALIDATION
```

### Validation Task Naming Convention

Validation tasks should be named:
- `Validate {component} renders correctly`
- `Validate {feature} works end-to-end`
- `Visual validation: {description}`

### Ralph Loop Validation Behavior

When the Ralph loop encounters a validation task:

1. **Start servers** (if not running)
2. **Execute agent-browser commands** to validate
3. **If validation PASSES**: Mark complete, proceed to next task
4. **If validation FAILS**:
   - Log the failure in activity.md
   - Identify the root cause from console errors or missing elements
   - Fix the issue in the relevant component
   - Re-run quality checks (typecheck, lint)
   - **Re-validate** with agent-browser
   - Repeat until validation passes (max 3 attempts)
   - Only then proceed to next task

### Validation Failure Recovery Flow

```
Validation Task
      │
      ▼
┌─────────────────┐
│ Run agent-browser│
│ validation      │
└─────────────────┘
      │
      ├── PASS ──► Mark complete, next task
      │
      ▼ FAIL
┌─────────────────┐
│ Log failure     │
│ Analyze error   │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Fix component   │
│ Run quality     │
│ checks          │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Re-validate     │──► PASS ──► Mark complete
│ (attempt 2/3)   │
└─────────────────┘
      │ FAIL
      ▼
┌─────────────────┐
│ Fix again       │
│ Re-validate     │──► PASS ──► Mark complete
│ (attempt 3/3)   │
└─────────────────┘
      │ FAIL
      ▼
┌─────────────────┐
│ USER INPUT      │
│ REQUIRED        │
└─────────────────┘
```

### Example Validation Task Execution

For task "6.3 Validate MapMarker renders correctly":

```bash
# 1. Ensure servers running
curl -s http://localhost:8000/health || (start backend)
curl -s http://localhost:5173 || (start frontend)

# 2. Navigate and trigger component render
agent-browser open http://localhost:5173/schedule/generate
agent-browser click "[data-testid='preview-btn']"
agent-browser wait --load networkidle
agent-browser click "[data-testid='view-toggle-map']"

# 3. Validate component
agent-browser is visible "[data-testid='map-marker']"
# If false → FIX and retry

# 4. Validate interactions (if applicable)
agent-browser click "[data-testid='map-marker']"
agent-browser is visible "[data-testid='map-info-window']"
```

### Tasks.md Template for UI Features

When creating tasks.md for UI features, use this pattern:

```markdown
## Phase X: {Feature Name}

- [ ] 1. {Component A}
  - [ ] 1.1 Create {Component A}
  - [ ] 1.2 Add data-testid attributes
  - [ ] 1.3 Validate {Component A} renders correctly

- [ ] 2. {Component B}
  - [ ] 2.1 Create {Component B}
  - [ ] 2.2 Add data-testid attributes
  - [ ] 2.3 Validate {Component B} renders correctly

- [ ] 3. {Integration}
  - [ ] 3.1 Integrate {Component A} and {Component B}
  - [ ] 3.2 Validate integration works end-to-end
```

---

## Visual Validation

### Server Management for Visual Validation

Before any task requiring agent-browser validation, ensure servers are running:

```bash
# Check if servers are running
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "Backend running" || echo "Backend not running"
curl -s http://localhost:5173 > /dev/null 2>&1 && echo "Frontend running" || echo "Frontend not running"
```

**If servers are not running, start them automatically:**

```bash
# Start backend (in background)
cd /Users/kirillrakitin/Grins_irrigation_platform
nohup uv run uvicorn grins_platform.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
echo $! > /tmp/backend.pid

# Wait for backend to be ready
for i in {1..30}; do
  curl -s http://localhost:8000/health > /dev/null 2>&1 && break
  sleep 1
done

# Start frontend (in background)
cd /Users/kirillrakitin/Grins_irrigation_platform/frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
echo $! > /tmp/frontend.pid

# Wait for frontend to be ready
for i in {1..30}; do
  curl -s http://localhost:5173 > /dev/null 2>&1 && break
  sleep 1
done
```

**Server startup is MANDATORY before visual validation tasks.** Do not skip or mark visual validation tasks complete without actually running agent-browser commands.

### Cleanup After Validation

After all visual validation tasks are complete:

```bash
# Stop servers if we started them
[ -f /tmp/backend.pid ] && kill $(cat /tmp/backend.pid) 2>/dev/null && rm /tmp/backend.pid
[ -f /tmp/frontend.pid ] && kill $(cat /tmp/frontend.pid) 2>/dev/null && rm /tmp/frontend.pid
```

### Visual Validation Task Detection

A task requires visual validation if it contains any of:
- "visual validation"
- "agent-browser"
- "screenshot"
- "UI validation"
- "end-to-end validation"
- Task number pattern matching validation tasks (e.g., 28.x for map-scheduling-interface)

### taskStatus Tool

Use the `taskStatus` tool to update task states:

```
taskStatus(
  taskFilePath=".kiro/specs/{spec-name}/tasks.md",
  task="{exact task text}",
  status="in_progress" | "completed"
)
```

### agent-browser Tool

Use for visual validation:

```bash
agent-browser open {url}
agent-browser snapshot -i
agent-browser click "[data-testid='button']"
agent-browser fill "[data-testid='input']" "value"
agent-browser is visible "[data-testid='element']"
```

### getDiagnostics Tool

Use to check for code issues:

```
getDiagnostics(paths=["src/grins_platform/new_file.py"])
```

---

## Best Practices

### Before Starting

1. Read the full spec (requirements, design, tasks)
2. Understand the current state
3. Identify any blockers or dependencies

### During Execution

1. Focus on one task at a time
2. Write tests alongside implementation
3. Run quality checks frequently
4. Log progress in activity.md

### At Checkpoints

1. Review all completed work
2. Run full test suite
3. Check for any skipped tasks
4. Verify integration with existing code

### After Completion

1. Update DEVLOG.md with summary
2. Run final quality checks
3. Verify all tests pass
4. Document any deviations from design

---

## Troubleshooting

### Loop Not Progressing

1. Check if task is actually incomplete (`- [ ]`)
2. Check if there's a blocking dependency
3. Check activity.md for error messages
4. Run `@ralph-status {spec-name}` to see current state

### Quality Checks Failing

1. Read the error messages carefully
2. Fix issues one at a time
3. Re-run specific check after each fix
4. Don't skip quality checks

### Tests Failing

1. Check if test is testing the right thing
2. Check if implementation matches design
3. Check for missing dependencies
4. Run single test to isolate issue

### Stuck at Checkpoint

1. Review completed work
2. Run `@ralph-loop {spec-name}` to continue
3. Or run `@ralph-next {spec-name}` for single task

---

## Stagnation Recovery (CRITICAL FOR AUTONOMOUS EXECUTION)

### Command Timeout Recovery

When a command times out, DO NOT wait for user input. Immediately try an alternative:

| Scenario | Recovery Strategy |
|----------|-------------------|
| `npm install` timeout | Install packages one at a time, or use `--legacy-peer-deps` |
| `npx shadcn` timeout | Manually create component files from shadcn/ui source |
| `npx` init commands | Create config files manually |
| Build/compile timeout | Check for infinite loops, reduce scope |
| Test timeout | Run specific test file instead of full suite |

### Manual Component Creation (shadcn/ui)

If shadcn CLI times out, create components manually:

1. Check https://ui.shadcn.com/docs/components/{component}
2. Copy the component source code
3. Create file at `src/components/ui/{component}.tsx`
4. Install any missing dependencies individually

### NPM Timeout Recovery

```bash
# Instead of bulk install:
npm install pkg1 pkg2 pkg3  # May timeout

# Do one at a time:
npm install pkg1
npm install pkg2
npm install pkg3
```

### Stagnation Detection Rules (10 Failures = Skip)

If you notice:
- Command running > 60 seconds with no output
- Same error appearing 10+ times
- No progress for 5+ minutes

Then IMMEDIATELY:
1. Cancel/abandon the current approach
2. Log the issue in activity.md
3. Try an alternative approach
4. If same error occurs 10 times consecutively, **SKIP the task and continue**
5. **NEVER stop the loop** - always continue to next task

### Never Wait for User Input During Autonomous Execution

The Ralph loop is designed for overnight/unattended execution. When stuck:
- DO try alternative approaches (up to 10 times)
- DO skip and document blockers after 10 failures
- DO continue with next tasks
- DO NOT wait for user confirmation
- DO NOT ask clarifying questions
- DO NOT stop the loop for any reason except ALL_TASKS_COMPLETE

---

## Overnight Mode Rules (CRITICAL FOR UNATTENDED EXECUTION)

When running in overnight mode (`./scripts/ralph-overnight.sh`), the following rules apply:

### THE LOOP NEVER STOPS

**CRITICAL: The overnight loop is designed to run until completion. It will NEVER stop for errors, failures, or checkpoints.**

In overnight mode, the loop handles situations as follows:

| Situation | Overnight Mode Behavior |
|-----------|-------------------------|
| Checkpoint reached | Run quality checks, retry fixes up to 10 times, then SKIP and continue |
| Checkpoint validation fails | Try to fix 10 times, then SKIP checkpoint and continue |
| Regular task fails | Retry 10x with different approaches, then SKIP and continue |
| Visual validation fails | Retry 10x, screenshot, then SKIP and continue |
| Command timeout | Try alternative, if fails 10x then SKIP |
| Same error 10 times | SKIP task and continue to next |

### Task Skip Behavior

When a task cannot be completed after 10 identical failures:

1. Mark with `- [S]` (Skipped) instead of leaving incomplete
2. Log detailed reason in activity.md with all 10 attempts
3. Clear the failure counter
4. Continue to next task immediately

**NOTE: Even checkpoints can be skipped in "never stop" mode. The loop prioritizes progress over perfection.**

### Checkpoint Behavior (Overnight Mode) - SKIP ON FAILURE

```markdown
# Checkpoint reached:
- [ ] 11. Checkpoint - Phase 5A Complete
  → Run ALL quality checks (ruff, mypy, pyright, pytest)
  → If ALL pass: Log "CHECKPOINT PASSED", mark [x], continue
  → If ANY fail: Try to FIX the issues
  → Retry quality checks up to 10 times
  → If still failing after 10 attempts: Log "CHECKPOINT SKIPPED", mark [S], CONTINUE
```

### Checkpoint Validation Flow (Never Stop Mode)

```
Checkpoint Task
      │
      ▼
┌─────────────────┐
│ Run ALL quality │
│ checks          │
└─────────────────┘
      │
      ├── ALL PASS ──► Mark complete, continue
      │
      ▼ ANY FAIL
┌─────────────────┐
│ Identify failing│
│ code/tests      │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Fix the issues  │
│ (attempt 1/10)  │
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Re-run quality  │──► ALL PASS ──► Mark complete, continue
│ checks          │
└─────────────────┘
      │ STILL FAIL
      ▼
┌─────────────────┐
│ Fix again       │
│ (attempt 2-10)  │──► Repeat until pass or 10 attempts
└─────────────────┘
      │ 10 attempts exhausted
      ▼
┌─────────────────────────┐
│ CHECKPOINT SKIPPED      │
│ Mark [S], CONTINUE      │──► Next task (loop never stops)
└─────────────────────────┘
```

### Output Signals

The overnight prompt MUST output exactly ONE of these signals:

| Signal | Meaning | Action |
|--------|---------|--------|
| `TASK_COMPLETE` | Task finished successfully | Continue to next |
| `TASK_SKIPPED: {reason}` | Task skipped due to failure | Continue to next |
| `ALL_TASKS_COMPLETE` | No more tasks to execute | Exit loop (only exit condition) |
| `CHECKPOINT_PASSED: {name}` | Checkpoint validation passed | Continue to next |
| `CHECKPOINT_SKIPPED: {name}` | Checkpoint skipped after 10 failures | Continue to next |

### Timeout Handling

**Two-Level Timeout System:**

1. **Task-Level Timeout (10 minutes):** The bash script enforces a 10-minute maximum per task execution.

2. **Command-Level Timeout (60 seconds):** Individual commands should complete within 60 seconds.

If any command takes > 60 seconds:
1. Cancel the command
2. Log timeout in activity.md
3. Try alternative approach
4. If still fails after 10 attempts, skip task with `TASK_SKIPPED: timeout`
5. **CONTINUE to next task (never stop)**

### Server Health Checks

Before visual validation tasks:
```bash
curl -s http://localhost:8000/health || echo "BACKEND_DOWN"
curl -s http://localhost:5173 || echo "FRONTEND_DOWN"
```

If servers are down:
1. Attempt automatic restart (overnight script handles this)
2. If restart fails, skip visual validation
3. Mark task as skipped and continue
4. **NEVER stop the loop**

### Starting Overnight Mode

```bash
# Full overnight run (never stops until complete)
./scripts/ralph-overnight.sh <spec-name> [max-iterations]

# Examples
./scripts/ralph-overnight.sh map-scheduling-interface 100
./scripts/ralph-overnight.sh admin-dashboard 50
```

### Never Stop Behavior Summary

| Scenario | Old Behavior | New Behavior |
|----------|--------------|--------------|
| Task fails 3x | Stop, ask user | Retry up to 10x, then skip |
| Checkpoint fails | Stop loop | Retry 10x, then skip checkpoint |
| Same error 5x | Stop (stagnation) | Continue retrying up to 10x |
| Same error 10x | N/A | Skip task, continue to next |
| Unknown error | Stop | Log, skip, continue |
| Server down | Stop | Restart, if fails skip task |

### Overnight Activity Log Format

```markdown
## [{YYYY-MM-DD HH:MM}] Task {task-id}: {task-name}

### Status: ✅ COMPLETE | ⏭️ SKIPPED | 🔄 IN PROGRESS

### What Was Done
- {description of changes}

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
```

---

## Configuration Reference

```yaml
# Default configuration for Ralph Wiggum Loop

context_mode: continuous_with_checkpoint_reset
continue_mode: auto_until_complete  # Never stop until all tasks done
task_execution: single_task

state_storage:
  task_status: .kiro/specs/{feature}/tasks.md
  activity_log: .kiro/specs/{feature}/activity.md

failure_handling: never_stop  # Skip after 10 failures, never halt
max_iterations: 100
retry_limit: 10  # Increased from 3 to 10
checkpoint_detection: true

quality_checks:
  backend:
    - uv run ruff check src/
    - uv run mypy src/
    - uv run pyright src/
    - uv run pytest -v
  frontend:
    - cd frontend && npm run lint
    - cd frontend && npm run typecheck
    - cd frontend && npm test

visual_validation:
  enabled: true
  tool: agent-browser
  screenshot_dir: screenshots/{feature}/

# Overnight mode specific - NEVER STOP MODE
overnight_mode:
  enabled: false  # Set to true when running ralph-overnight.sh
  never_stop: true  # Loop continues until ALL_TASKS_COMPLETE
  checkpoint_pause: false
  checkpoint_skip_on_failure: true  # Skip checkpoints after 10 failures (don't stop)
  user_input_wait: false  # Never wait for user input
  max_task_timeout: 600  # 10 minutes per task (bash script level)
  max_command_timeout: 60  # 60 seconds per command (prompt level)
  stagnation_threshold: 10  # Skip task after 10 identical consecutive failures
  server_health_check: true
  auto_restart_servers: true
  skip_on_stagnation: true  # Skip task instead of stopping loop
```
