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

Create `.kiro/specs/{spec-name}/activity.md` if it doesn't exist.

### Step 3: Find Next Task

1. Parse `tasks.md` for task states
2. Find first `- [ ]` task (not started)
3. If task has sub-tasks, find first incomplete sub-task

### Step 4: Execute Task

1. Mark task as in-progress using `taskStatus` tool
2. Implement the task following code-standards.md
3. Include logging, type hints, tests

### Step 5: Validate Work

Run ALL quality checks:
```bash
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v
```

### Step 6: Mark Complete

Use `taskStatus` tool to mark task as completed.

### Step 7: Log Activity

Append completion entry to `activity.md`.

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
- Retry up to 3 times
- After 3 failures, output `USER INPUT REQUIRED` and stop

## Output Format

```
🔄 Ralph Wiggum Next: {spec-name}
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Task {task-id} complete.

Next task: {next-task-id} - {next-task-name}

Run `@ralph-next {spec-name}` to execute next task.
Run `@ralph-loop {spec-name}` to continue automatically.
```
