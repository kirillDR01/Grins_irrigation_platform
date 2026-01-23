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

---

## Session Log

<!-- Ralph Wiggum loop will append entries here -->
```

### Step 3: Find Next Task

1. Parse `tasks.md` to find task states:
   - `- [ ]` = Not started (execute this)
   - `- [x]` = Completed (skip)
   - `- [-]` = In progress (continue this)
   - `- [~]` = Queued (skip for now)
2. Find the first task with `- [ ]` that is NOT a sub-task of an incomplete parent
3. If task has sub-tasks, start with the first incomplete sub-task

### Step 4: Execute Task

1. Mark task as in-progress using `taskStatus` tool
2. Read relevant files for context
3. Implement the task following:
   - `.kiro/steering/code-standards.md` requirements
   - Include logging (LoggerMixin for classes)
   - Include type hints
   - Include tests (unit, functional, integration)
4. Write code changes

### Step 5: Validate Work

Run quality checks (ALL must pass):

```bash
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v
```

For frontend tasks, also run:
```bash
cd frontend && npm run lint && npm run typecheck && npm test
```

For visual validation (frontend), use `agent-browser`:
```bash
agent-browser open http://localhost:5173
agent-browser snapshot -i
```

### Step 6: Mark Complete

1. Use `taskStatus` tool to mark task as completed
2. If task has sub-tasks and all are complete, mark parent complete too

### Step 7: Log Activity

Append entry to `activity.md`:

```markdown
## [{timestamp}] Task {task-id}: {task-name}

### What Was Done
- {description of changes}

### Files Modified
- {list of files}

### Quality Check Results
- Ruff: ✅ Pass / ❌ Fail
- MyPy: ✅ Pass / ❌ Fail
- Pyright: ✅ Pass / ❌ Fail
- Tests: ✅ X/Y passing / ❌ Failed

### Notes
- {any issues or observations}
```

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

If a task fails:

1. **Retry (up to 3 times):**
   - Log retry attempt in activity.md
   - Try alternative approach if possible

2. **After 3 retries:**
   - Output: `USER INPUT REQUIRED: {task-id} failed after 3 attempts`
   - Log failure details in activity.md
   - Stop and wait for user guidance

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
