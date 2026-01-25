# Ralph Wiggum Loop

Execute the Ralph Wiggum autonomous loop for a spec.

## Usage

`@ralph-loop {spec-name}`

Example: `@ralph-loop admin-dashboard`

## Instructions

You are executing the Ralph Wiggum autonomous loop. This loop continuously executes tasks from a spec until all tasks are complete or a checkpoint is reached.

### Step 1: Validate Spec

1. Verify spec exists at `.kiro/specs/{spec-name}/`
2. Read `requirements.md` to understand the feature
3. Read `design.md` to understand the implementation approach
4. Read `tasks.md` to find current state

### Step 2: Initialize Activity Log

1. Check if `.kiro/specs/{spec-name}/activity.md` exists
2. If not, create it using this template:

```markdown
# Activity Log: {spec-name}

## Current Status
**Last Updated:** {timestamp}
**Tasks Completed:** 0 / {total}
**Current Task:** None
**Loop Status:** Started

## Retry Tracking
<!-- Format: Task {task-id}: Attempt {n}/3 [{status}] [{timestamp}] [{reason}] -->

---

## Activity Entries

<!-- Ralph Wiggum loop will append entries here -->
```

### Step 3: Find Next Task

1. Parse `tasks.md` to find task states:
   - `- [ ]` = Not started (execute this)
   - `- [x]` = Completed (skip)
   - `- [-]` = In progress (continue this)
   - `- [~]` = Queued (skip for now)
   - `- [S]` = Skipped (skip)
2. Find the first task with `- [ ]` or `- [-]` that is NOT a sub-task of an incomplete parent
3. If task has sub-tasks, start with the first incomplete sub-task

### Step 3.5: Check Retry State

**CRITICAL:** Before executing, check if this task has already been attempted.

1. Read the "Retry Tracking" section in activity.md
2. Look for line matching: `Task {task-id}: Attempt`
3. Parse the attempt number:
   - If line exists: Extract current attempt number (e.g., "Attempt 2/3")
   - If line doesn't exist: This is attempt 1
4. **Enforce retry limit:**
   - If attempt >= 3: 
     - Output: `USER INPUT REQUIRED: Task {task-id} has failed 3 times`
     - Skip this task and continue to next task
   - If attempt < 3:
     - Increment attempt number
     - Continue to Step 4
5. Add/update retry tracking line:
   ```
   Task {task-id}: Attempt {n}/3 [started] [{timestamp}]
   ```

**Example Retry Tracking:**
```markdown
## Retry Tracking
Task 1.1: Attempt 1/3 [started] [2026-01-24 18:00]
Task 1.2: Attempt 2/3 [failed] [2026-01-24 18:15] [Type error in schema]
Task 1.3: Attempt 1/3 [completed] [2026-01-24 18:30]
```

### Step 4: Execute Task (WITH TIMEOUT)

**IMPORTANT:** Mark task as in-progress FIRST, then implement.

**Timeout Rule:** If a single task takes > 15 minutes, force alternative approach.

1. **Log start time:**
   - Add to retry tracking:
     ```
     Task {task-id}: Attempt {n}/3 [started] [{timestamp}]
     ```

2. **Update task state to in-progress:**
   - Call internal prompt: `@update-task-state {spec-name} "{exact-task-text}" "in_progress"`
   - Wait for SUCCESS confirmation
   - If ERROR, retry once
   - If still ERROR, output USER INPUT REQUIRED and stop

3. Read relevant files for context

4. Implement the task following:
   - `.kiro/steering/code-standards.md` requirements
   - Include logging (LoggerMixin for classes)
   - Include type hints
   - Include tests (unit, functional, integration)

5. Write code changes

6. **Check elapsed time before quality checks:**
   - Calculate time since start
   - If < 15 minutes → proceed to Step 5
   - If >= 15 minutes → TIMEOUT TRIGGERED

7. **On TIMEOUT:**
   a. Log timeout in activity.md:
      ```
      Task {task-id}: TIMEOUT after 15 minutes
      ```
   b. Analyze what's taking so long:
      - Stuck on npm install? → Install packages individually
      - Stuck on shadcn CLI? → Create component files manually
      - Stuck on complex logic? → Simplify scope
      - Stuck on API calls? → Use mock data
   c. Try alternative approach (counts as retry attempt)
   d. If alternative also times out → USER INPUT REQUIRED
   e. **DO NOT wait for user input** - make a decision and continue

### Step 5: Validate Work

**CRITICAL:** ALL quality checks must pass before marking complete.

1. **Determine task type:**
   - If task modifies `src/grins_platform/` → backend
   - If task modifies `frontend/` → frontend

2. **Run quality checks:**
   - Call internal prompt: `@validate-quality {task-type} {retry-attempt}`
   - Wait for result

3. **For frontend UI tasks, also run visual validation:**
   - Extract validation commands from tasks.md
   - Call internal prompt: `@validate-visual {spec-name} {task-id} "{validation-commands}"`
   - Wait for result

4. **Parse results:**
   - If ALL checks PASSED → proceed to Step 6
   - If ANY check FAILED:
     a. Read error details from output
     b. Update retry tracking:
        ```
        Task {task-id}: Attempt {n}/3 [failed] [{timestamp}] [{error-summary}]
        ```
     c. If retry_attempt < 3:
        - Fix the issues
        - Increment retry_attempt
        - Go back to Step 4 (re-implement)
     d. If retry_attempt >= 3:
        - Output: `USER INPUT REQUIRED: Task {task-id} failed quality checks 3 times`
        - Log failure details in activity.md
        - Stop execution

**Quality Check Details:**

For backend tasks:
```bash
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v
```

For frontend tasks:
```bash
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm test
```

For frontend UI tasks (ADDITIONAL):
```bash
# Validation commands from tasks.md, e.g.:
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='map-view']"
agent-browser screenshot screenshots/{spec-name}/{task-id}.png
```

### Step 6: Mark Complete

**IMPORTANT:** Only mark complete after quality checks pass.

1. **Update task state to completed:**
   - Call internal prompt: `@update-task-state {spec-name} "{exact-task-text}" "completed"`
   - Wait for SUCCESS confirmation
   - If ERROR (e.g., sub-tasks incomplete), fix issue and retry
   - If still ERROR, output USER INPUT REQUIRED and stop

2. **Update retry tracking:**
   ```
   Task {task-id}: Attempt {n}/3 [completed] [{timestamp}]
   ```

3. **Check parent task:**
   - If this task is a sub-task, check if all sibling sub-tasks are complete
   - If yes, mark parent task as completed too
   - Use `@update-task-state` for parent task

### Step 7: Log Activity

**IMPORTANT:** Log every completed task for audit trail.

Call internal prompt: `@log-activity` with these parameters:

```
@log-activity {spec-name} "{task-id}" "{task-name}" "{what-was-done}" "{files-modified}" "{quality-results}" "{notes}"
```

**Parameter Guidelines:**

1. **what_was_done** - Bullet list of changes:
   ```
   - Implemented coordinate fields in schema
   - Added validation logic
   - Updated tests
   ```

2. **files_modified** - File paths with descriptions:
   ```
   - `src/grins_platform/schemas/schedule.py` - Added fields
   - `src/grins_platform/tests/test_schema.py` - Added tests
   ```

3. **quality_results** - Paste output from @validate-quality

4. **notes** - Any observations or decisions made

**If logging fails:**
- Output warning but continue
- Logging failure is not critical
- Task is still considered complete

### Step 8: Check Continuation

1. **If task name contains "Checkpoint":**
   - Output: `CHECKPOINT REACHED: {task-name}`
   - Stop and wait for user to review
   - User can run `@ralph-loop {spec-name}` to continue

2. **If all tasks are complete (`[x]`):**
   - Output: `LOOP COMPLETE: All tasks finished!`
   - Stop execution

3. **Otherwise:**
   - Continue to Step 3 (find next task)

## Failure Handling

### Retry Logic (Automatic)

If a task fails quality checks:

1. **Attempt 1-2:**
   - Update retry tracking with failure reason
   - Fix the issues based on error messages
   - Re-run from Step 4 (implementation)
   - Increment retry_attempt

2. **Attempt 3:**
   - If still failing, output: `USER INPUT REQUIRED: Task {task-id} failed after 3 attempts`
   - Log detailed failure information in activity.md
   - Stop execution (don't continue to next task)

### Task State Update Failures

If `@update-task-state` fails:

1. **First failure:**
   - Retry once with same parameters
   - Verify task text matches exactly

2. **Second failure:**
   - Output: `USER INPUT REQUIRED: Cannot update task state for {task-id}`
   - Log error details
   - Stop execution

### Quality Check Failures

If `@validate-quality` fails to run (not just failing checks):

1. Check if tools are installed (ruff, mypy, pyright, pytest)
2. Check if virtual environment is activated
3. If tools missing, output: `USER INPUT REQUIRED: Quality check tools not available`
4. Stop execution

### Stagnation Recovery

If you notice you're stuck on the same error for >10 minutes:

1. Log the stagnation in activity.md
2. Try a completely different approach:
   - npm install stuck? → Install packages one at a time
   - shadcn CLI stuck? → Create component files manually
   - Complex logic stuck? → Simplify scope
3. If no alternative exists, mark task as blocked and continue to next task

**DO NOT wait for user input during autonomous execution.**

## Safety Rules

- Follow `.kiro/steering/workspace-safety.md` at all times
- Only modify files within workspace
- Never execute destructive commands
- All changes must be git-trackable

## Configuration

- **Max iterations:** 50 (safety limit)
- **Retry limit:** 3 per task
- **Quality checks:** MANDATORY (no skipping)
- **Checkpoint pause:** MANDATORY

## Output Format

During execution, output progress:

```
🔄 Ralph Wiggum Loop: {spec-name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Task: {task-id} - {task-name}
   Status: In Progress

   [... implementation details ...]

✅ Quality Checks:
   - Ruff: ✅
   - MyPy: ✅
   - Pyright: ✅
   - Tests: ✅ 127/127

📝 Logged to activity.md

➡️ Continuing to next task...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
