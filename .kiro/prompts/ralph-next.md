# Ralph Wiggum Next

Execute just the next task from a spec (single iteration).

## Usage

`@ralph-next {spec-name}`

Example: `@ralph-next admin-dashboard`

## Instructions

This is identical to `@ralph-loop` but stops after completing ONE task instead of continuing.

### Step 1: Validate Spec

1. Verify spec exists at `.kiro/specs/{spec-name}/`
2. Read `requirements.md`, `design.md`, `tasks.md`

### Step 2: Initialize Activity Log

Create `.kiro/specs/{spec-name}/activity.md` if it doesn't exist using the template from `@ralph-loop`.

### Step 3: Find Next Task

1. Parse `tasks.md` for task states
2. Find first `- [ ]` or `- [-]` task (not started or in progress)
3. If task has sub-tasks, find first incomplete sub-task

### Step 3.5: Check Retry State

**CRITICAL:** Check retry tracking before executing (same as `@ralph-loop` Step 3.5).

### Step 4: Execute Task (WITH TIMEOUT)

1. Log start time in retry tracking
2. Call `@update-task-state {spec-name} "{task-text}" "in_progress"`
3. Implement the task following code-standards.md
4. Include logging, type hints, tests
5. Check elapsed time (15-minute timeout rule applies)

### Step 5: Validate Work

1. Determine task type (backend/frontend)
2. Call `@validate-quality {task-type} {retry-attempt}`
3. For frontend UI tasks, also call `@validate-visual {spec-name} {task-id} "{commands}"`
4. If FAILED and retry < 3:
   - Fix issues
   - Increment retry
   - Go back to Step 4
5. If FAILED and retry >= 3:
   - Output USER INPUT REQUIRED
   - Stop

### Step 6: Mark Complete

1. Call `@update-task-state {spec-name} "{task-text}" "completed"`
2. Update retry tracking to "completed"

### Step 7: Log Activity

Call `@log-activity` with all required parameters (same as `@ralph-loop` Step 7).

### Step 8: STOP

**Unlike `@ralph-loop`, this command STOPS after one task.**

Output:
```
✅ Task {task-id} complete.

Next task: {next-task-id} - {next-task-name}

Run `@ralph-next {spec-name}` to execute next task.
Run `@ralph-loop {spec-name}` to continue automatically.
```

## Use Cases

- **Manual step-through:** Execute tasks one at a time with review between each
- **Testing:** Verify loop behavior on a single task
- **Debugging:** Isolate issues to specific tasks
- **Learning:** Understand what each task does

## Failure Handling

Same as `@ralph-loop`:
- Retry up to 3 times with quality gate enforcement
- Visual validation for frontend UI tasks
- Timeout detection and recovery (15-minute limit)
- After 3 failures, output `USER INPUT REQUIRED` and stop
- Use internal prompts: `@update-task-state`, `@validate-quality`, `@validate-visual`, `@log-activity`

## Output Format

```
🔄 Ralph Wiggum Next: {spec-name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Task: {task-id} - {task-name}
   Status: In Progress
   Attempt: {n}/3
   Started: {timestamp}

   [... implementation details ...]

✅ Quality Checks:
   - Ruff: ✅
   - MyPy: ✅
   - Pyright: ✅
   - Tests: ✅ 127/127

{For frontend UI tasks:}
✅ Visual Validation:
   - Page loads: ✅
   - Elements visible: ✅
   - No console errors: ✅
   - Screenshot: screenshots/{spec-name}/{task-id}.png

📝 Logged to activity.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Task {task-id} complete.

Next task: {next-task-id} - {next-task-name}

Run `@ralph-next {spec-name}` to execute next task.
Run `@ralph-loop {spec-name}` to continue automatically.
```
