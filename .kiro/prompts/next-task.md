# Next Task

Find and execute the next incomplete task from the active spec.

## Instructions

1. **Find Active Spec**: Look in `.kiro/specs/` for the most recently modified tasks.md file, or use the spec specified by the user.

2. **Parse Tasks**: Read the tasks.md file and identify:
   - Tasks marked `[ ]` (not started)
   - Tasks marked `[-]` (in progress)
   - Tasks marked `[x]` (completed)

3. **Determine Next Task**:
   - If any task is `[-]` (in progress), continue that task
   - Otherwise, find the first `[ ]` task that has all dependencies completed
   - Consider task numbering (1.1 before 1.2, etc.)

4. **Display Status**:
   ```
   📋 Spec: {spec-name}
   ✅ Completed: X/Y tasks
   🔄 In Progress: {task if any}
   ➡️ Next Task: {task number and title}
   ```

5. **Execute the Task**:
   - Read the task details and requirements
   - Reference the design.md for implementation details
   - Follow the established patterns from existing code
   - Include appropriate tests
   - Run quality checks after implementation

6. **Update Task Status**:
   - Mark task as `[-]` when starting
   - Mark task as `[x]` when complete

## Usage

```
@next-task
@next-task field-operations
@next-task customer-management
```

## Related Prompts
- `@task-progress` - View overall task progress
- `@checkpoint` - Save progress after completing task
- `@feature-complete-check` - Verify feature is done
