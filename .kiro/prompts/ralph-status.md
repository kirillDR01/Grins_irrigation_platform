# Ralph Wiggum Status

Check the current progress of a spec without executing any tasks.

## Usage

`@ralph-status {spec-name}`

Example: `@ralph-status admin-dashboard`

## Instructions

1. Read `.kiro/specs/{spec-name}/tasks.md`
2. Read `.kiro/specs/{spec-name}/activity.md` (if exists)
3. Parse task states and calculate progress
4. Output formatted status report

## Task State Detection

Parse `tasks.md` for these patterns:
- `- [ ]` = Not started
- `- [x]` = Completed
- `- [-]` = In progress
- `- [~]` = Queued
- `- [S]` = Skipped

Count only top-level tasks (not sub-tasks) for main progress.

## Output Format

```markdown
## Ralph Wiggum Status: {spec-name}

### Progress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **Total Tasks:** {total} top-level ({sub-total} sub-tasks)
- **Completed:** {completed} ({percentage}%)
- **In Progress:** {in_progress}
- **Remaining:** {remaining}

### Progress Bar
[████████░░░░░░░░░░░░] {percentage}%

### Current/Next Task
{If in-progress task exists:}
🔄 **In Progress:** {task-id} - {task-name}

{If no in-progress task:}
➡️ **Next:** {task-id} - {task-name}

### Last Completed
✅ {task-id} - {task-name}

### Next Checkpoint
⏸️ {checkpoint-task-id} - {checkpoint-name} ({tasks-away} tasks away)

### Recent Activity (last 5)
{If activity.md exists:}
- [{timestamp}] {task-id}: {task-name}
- [{timestamp}] {task-id}: {task-name}
- ...

{If no activity.md:}
No activity log found. Run `@ralph-loop {spec-name}` to start.

### Commands
- Start/continue loop: `@ralph-loop {spec-name}`
- Execute single task: `@ralph-next {spec-name}`
- Skip blocked task: `@ralph-skip {spec-name} {task-id} "reason"`
```

## Example Output

```markdown
## Ralph Wiggum Status: admin-dashboard

### Progress
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- **Total Tasks:** 18 top-level (85 sub-tasks)
- **Completed:** 5 (28%)
- **In Progress:** 0
- **Remaining:** 13

### Progress Bar
[█████░░░░░░░░░░░░░░░] 28%

### Current/Next Task
➡️ **Next:** 2.1 - Create appointments table migration

### Last Completed
✅ 1.5 - Create steering documents

### Next Checkpoint
⏸️ 4 - Checkpoint - Backend Complete (7 tasks away)

### Recent Activity (last 5)
- [2026-01-21 10:30] 1.5: Create steering documents
- [2026-01-21 10:15] 1.4: Create frontend hooks
- [2026-01-21 10:00] 1.3: Create frontend prompts
- [2026-01-21 09:45] 1.2: Create component-agent
- [2026-01-21 09:30] 1.1: Create frontend-agent

### Commands
- Start/continue loop: `@ralph-loop admin-dashboard`
- Execute single task: `@ralph-next admin-dashboard`
- Skip blocked task: `@ralph-skip admin-dashboard 2.1 "reason"`
```
