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

### Graduated Response

```
Task Fails
    │
    ▼
┌─────────────────┐
│  Retry 1/3      │──► Success? → Continue
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  Retry 2/3      │──► Success? → Continue
│  (try different │
│   approach)     │
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  Retry 3/3      │──► Success? → Continue
│  (simplify if   │
│   possible)     │
└─────────────────┘
    │ Fail
    ▼
┌─────────────────┐
│  USER INPUT     │
│  REQUIRED       │
└─────────────────┘
```

### Retry Strategies

1. **First retry:** Same approach, check for typos/errors
2. **Second retry:** Try alternative implementation
3. **Third retry:** Simplify scope if possible

### Logging Failures

Log each retry attempt:

```markdown
## [{timestamp}] Task {task-id}: RETRY {n}/3

### Issue
{description of what failed}

### Approach
{what will be tried differently}
```

### User Input Required

When all retries fail:

```markdown
## [{timestamp}] Task {task-id}: USER INPUT REQUIRED

### Issue
{detailed description of the problem}

### Attempts Made
1. {first approach and result}
2. {second approach and result}
3. {third approach and result}

### Suggested Actions
- {option 1}
- {option 2}
- {option 3}

### To Continue
Run `@ralph-loop {spec-name}` after resolving the issue.
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

The loop stops automatically when:
1. A checkpoint is reached
2. All tasks are complete
3. User input is required (after 3 retries)
4. Max iterations (100) is reached

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

### Stagnation Detection Rules

If you notice:
- Command running > 60 seconds with no output
- Same error appearing 3+ times
- No progress for 2+ minutes

Then IMMEDIATELY:
1. Cancel/abandon the current approach
2. Log the issue in activity.md
3. Try an alternative approach
4. If no alternative works after 3 attempts, mark task as blocked and continue to next task

### Never Wait for User Input During Autonomous Execution

The Ralph loop is designed for overnight/unattended execution. When stuck:
- DO try alternative approaches
- DO skip and document blockers
- DO continue with next tasks
- DO NOT wait for user confirmation
- DO NOT ask clarifying questions

---

## Overnight Mode Rules (CRITICAL FOR UNATTENDED EXECUTION)

When running in overnight mode (`./scripts/ralph-overnight.sh`), the following rules apply:

### CHECKPOINTS ARE MANDATORY QUALITY GATES

**CRITICAL: Checkpoints CANNOT be skipped. They are quality gates that ensure all code passes validation.**

In overnight mode, the loop handles situations as follows:

| Situation | Overnight Mode Behavior |
|-----------|-------------------------|
| Checkpoint reached | Run ALL quality checks, BLOCK until all pass |
| Checkpoint validation fails | FIX issues, retry up to 5 times, then STOP (not skip) |
| Regular task fails | Retry 3x, then skip with [S] marker |
| Visual validation fails | Retry 3x, screenshot, skip if still fails |
| Command timeout | Skip after 60 seconds |

### Task Skip Behavior (Regular Tasks Only)

When a **regular task** (not a checkpoint) cannot be completed:

1. Mark with `- [S]` (Skipped) instead of leaving incomplete
2. Log detailed reason in activity.md
3. Continue to next task immediately

**NOTE: Checkpoints are NEVER skipped. If a checkpoint fails, the loop STOPS.**

### Checkpoint Behavior (Overnight Mode) - QUALITY GATE

```markdown
# Checkpoint reached:
- [ ] 11. Checkpoint - Phase 5A Complete
  → Run ALL quality checks (ruff, mypy, pyright, pytest)
  → If ALL pass: Log "CHECKPOINT PASSED", mark [x], continue
  → If ANY fail: FIX the issues, retry quality checks
  → After 5 fix attempts still failing: Output "CHECKPOINT_FAILED", STOP loop
```

### Checkpoint Validation Flow

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
│ (attempt 1/5)   │
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
│ (attempt 2-5/5) │──► Repeat until pass or 5 attempts
└─────────────────┘
      │ 5 attempts exhausted
      ▼
┌─────────────────┐
│ CHECKPOINT_FAILED│
│ STOP LOOP       │
└─────────────────┘
```

### Output Signals

The overnight prompt MUST output exactly ONE of these signals:

| Signal | Meaning | Action |
|--------|---------|--------|
| `TASK_COMPLETE` | Task finished successfully | Continue to next |
| `TASK_SKIPPED: {reason}` | Regular task skipped due to failure | Continue to next |
| `ALL_TASKS_COMPLETE` | No more tasks to execute | Exit loop |
| `CHECKPOINT_PASSED: {name}` | Checkpoint validation passed | Continue to next |
| `CHECKPOINT_FAILED: {name}` | Checkpoint validation failed after 5 fix attempts | **STOP loop** |

### Timeout Handling

**Two-Level Timeout System:**

1. **Task-Level Timeout (10 minutes):** The bash script enforces a 10-minute maximum per task execution.

2. **Command-Level Timeout (60 seconds):** Individual commands should complete within 60 seconds.

If any command takes > 60 seconds:
1. Cancel the command
2. Log timeout in activity.md
3. Try alternative approach
4. If still fails, skip task with `TASK_SKIPPED: timeout`

### Server Health Checks

Before visual validation tasks:
```bash
curl -s http://localhost:8000/health || echo "BACKEND_DOWN"
curl -s http://localhost:5173 || echo "FRONTEND_DOWN"
```

If servers are down:
1. Attempt automatic restart (overnight script handles this)
2. If restart fails, skip visual validation
3. Mark task complete if code changes are correct

### Starting Overnight Mode

```bash
# Full overnight run
./scripts/ralph-overnight.sh <spec-name> [max-iterations]

# Examples
./scripts/ralph-overnight.sh map-scheduling-interface 100
./scripts/ralph-overnight.sh admin-dashboard 50
```

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
continue_mode: auto_until_checkpoint
task_execution: single_task

state_storage:
  task_status: .kiro/specs/{feature}/tasks.md
  activity_log: .kiro/specs/{feature}/activity.md

failure_handling: graduated_response
max_iterations: 100
retry_limit: 3
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

# Overnight mode specific
overnight_mode:
  enabled: false  # Set to true when running ralph-overnight.sh
  checkpoint_pause: false
  checkpoint_skip: false  # CRITICAL: Checkpoints are NEVER skipped
  checkpoint_quality_gate: true  # Checkpoints block until all checks pass
  checkpoint_fix_attempts: 5  # Max attempts to fix failing code at checkpoint
  user_input_wait: false
  max_task_timeout: 600  # 10 minutes per task (bash script level)
  max_command_timeout: 60  # 60 seconds per command (prompt level)
  server_health_check: true
  auto_restart_servers: true
```
