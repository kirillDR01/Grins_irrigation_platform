# Ralph Wiggum Skip

Skip a blocked task with a reason and continue to the next task.

## Usage

`@ralph-skip {spec-name} {task-id} "{reason}"`

Example: `@ralph-skip admin-dashboard 2.1 "Waiting for database migration approval"`

## Instructions

### Step 1: Validate Input

1. Verify spec exists at `.kiro/specs/{spec-name}/`
2. Verify task-id exists in `tasks.md`
3. Verify reason is provided

### Step 2: Mark Task as Skipped

1. The task checkbox should be updated to indicate skipped status
2. Use `taskStatus` tool if available, or note in activity log

### Step 3: Log Skip in Activity

Append to `.kiro/specs/{spec-name}/activity.md`:

```markdown
## [{timestamp}] Task {task-id}: SKIPPED

### Reason
{reason}

### Action Required
- {what needs to happen before this task can be completed}

### Skipped By
Ralph Wiggum Loop (user requested)
```

### Step 4: Find Next Task

1. Skip the marked task
2. Find the next `- [ ]` task
3. Output what the next task is

## Output Format

```
⏭️ Ralph Wiggum Skip: {spec-name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Skipped: {task-id} - {task-name}
   Reason: {reason}

📝 Logged to activity.md

➡️ Next task: {next-task-id} - {next-task-name}

Run `@ralph-next {spec-name}` to execute next task.
Run `@ralph-loop {spec-name}` to continue automatically.
```

## Use Cases

- **Blocked tasks:** Task depends on external approval or resource
- **Deferred tasks:** Task should be done later
- **Optional tasks:** Task is nice-to-have but not required now
- **Dependency issues:** Task requires something not yet available

## Notes

- Skipped tasks should be revisited later
- Use `@ralph-status {spec-name}` to see all skipped tasks
- Skipped tasks don't count as "complete" for checkpoint purposes
- The loop will not automatically retry skipped tasks

## Example

```
User: @ralph-skip admin-dashboard 2.1 "Database team needs to review migration first"

Agent:
⏭️ Ralph Wiggum Skip: admin-dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Skipped: 2.1 - Create appointments table migration
   Reason: Database team needs to review migration first

📝 Logged to activity.md

➡️ Next task: 2.2 - Create Appointment SQLAlchemy model

Run `@ralph-next admin-dashboard` to execute next task.
Run `@ralph-loop admin-dashboard` to continue automatically.
```
