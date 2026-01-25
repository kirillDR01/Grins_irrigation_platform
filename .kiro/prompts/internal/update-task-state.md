# Update Task State (Internal)

**Purpose:** Atomically update a task's checkbox state in tasks.md with validation.

**Usage:** Called internally by ralph-loop, not by users directly.

---

## Parameters

- `spec_name`: Name of the spec (e.g., "map-scheduling-interface")
- `task_text`: EXACT text of the task (e.g., "1.1 Add coordinate fields to ScheduleJobAssignment schema")
- `new_state`: One of: "in_progress" | "completed" | "skipped"

---

## Instructions

You are updating a task's checkbox state in tasks.md. This must be done atomically with verification.

### Step 1: Read Current State

1. Read `.kiro/specs/{spec_name}/tasks.md`
2. Search for the exact task text
3. Identify current checkbox state:
   - `- [ ]` = Not started
   - `- [-]` = In progress
   - `- [x]` = Completed
   - `- [~]` = Queued
   - `- [S]` = Skipped

### Step 2: Determine Replacement

Based on `new_state` parameter:

| new_state | Replacement Pattern |
|-----------|-------------------|
| in_progress | `- [-] {task_text}` |
| completed | `- [x] {task_text}` |
| skipped | `- [S] {task_text}` |

### Step 3: Update File

1. Use `fs_write` with `str_replace` command
2. Replace the ENTIRE line (including checkbox and task text)
3. **Critical:** Match the exact indentation and spacing

**Example:**
```markdown
Old: - [ ] 1.1 Add coordinate fields to ScheduleJobAssignment schema
New: - [x] 1.1 Add coordinate fields to ScheduleJobAssignment schema
```

### Step 4: Verify Update

1. Read `.kiro/specs/{spec_name}/tasks.md` again
2. Search for the new checkbox state with task text
3. Use grep to verify:

```bash
# For completed state
grep "^\- \[x\] {task_text}" .kiro/specs/{spec_name}/tasks.md

# For in_progress state
grep "^\- \[-\] {task_text}" .kiro/specs/{spec_name}/tasks.md

# For skipped state
grep "^\- \[S\] {task_text}" .kiro/specs/{spec_name}/tasks.md
```

4. If grep returns a match → SUCCESS
5. If grep returns no match → ERROR

### Step 5: Handle Sub-Tasks

If the task has sub-tasks (indented tasks below it):

1. Check if ALL sub-tasks are completed (`[x]`)
2. If yes, and marking parent as completed → proceed
3. If no, and marking parent as completed → ERROR (sub-tasks incomplete)

**Example:**
```markdown
- [ ] 2. Backend - Appointments
  - [x] 2.1 Create appointments table migration
  - [x] 2.2 Create Appointment SQLAlchemy model
  - [ ] 2.3 Create appointment repository
```

Cannot mark task 2 as completed because 2.3 is incomplete.

### Step 6: Output Result

**On SUCCESS:**
```
✅ Task State Updated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_text}
State: {new_state}
File: .kiro/specs/{spec_name}/tasks.md
Verified: ✅
```

**On ERROR:**
```
❌ Task State Update Failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_text}
Attempted State: {new_state}
Reason: {error reason}

Possible causes:
- Task text doesn't match exactly
- File was modified during update
- Sub-tasks are incomplete (for parent tasks)

Action Required: USER INPUT REQUIRED
```

---

## Error Handling

### Common Errors

1. **Task text not found:**
   - Verify exact text match (including spaces, punctuation)
   - Check if task was already updated
   - Check if task exists in tasks.md

2. **Update didn't persist:**
   - Retry once with same parameters
   - If still fails, output ERROR

3. **Sub-tasks incomplete:**
   - List which sub-tasks are incomplete
   - Suggest completing sub-tasks first
   - Output ERROR

### Retry Logic

1. If verification fails, retry ONCE
2. If second attempt fails, output ERROR and stop
3. Do NOT retry more than once (prevents infinite loops)

---

## Examples

### Example 1: Mark Task as In Progress

**Input:**
- spec_name: "map-scheduling-interface"
- task_text: "1.1 Add coordinate fields to ScheduleJobAssignment schema"
- new_state: "in_progress"

**Process:**
1. Read tasks.md
2. Find: `- [ ] 1.1 Add coordinate fields to ScheduleJobAssignment schema`
3. Replace with: `- [-] 1.1 Add coordinate fields to ScheduleJobAssignment schema`
4. Verify with grep
5. Output SUCCESS

### Example 2: Mark Task as Completed

**Input:**
- spec_name: "map-scheduling-interface"
- task_text: "1.1 Add coordinate fields to ScheduleJobAssignment schema"
- new_state: "completed"

**Process:**
1. Read tasks.md
2. Find: `- [-] 1.1 Add coordinate fields to ScheduleJobAssignment schema`
3. Replace with: `- [x] 1.1 Add coordinate fields to ScheduleJobAssignment schema`
4. Verify with grep
5. Output SUCCESS

### Example 3: Mark Parent Task (Error Case)

**Input:**
- spec_name: "map-scheduling-interface"
- task_text: "5A.1 Backend Schema Updates"
- new_state: "completed"

**Current State:**
```markdown
- [ ] 5A.1 Backend Schema Updates
  - [x] 1.1 Add coordinate fields
  - [ ] 1.2 Add start location fields
```

**Process:**
1. Read tasks.md
2. Find parent task
3. Check sub-tasks: 1.2 is incomplete
4. Output ERROR: "Cannot mark parent complete, sub-task 1.2 incomplete"

---

## Integration with Ralph-Loop

Ralph-loop should call this prompt at these points:

1. **Before starting a task:**
   ```
   @update-task-state {spec_name} "{task_text}" "in_progress"
   ```

2. **After completing a task:**
   ```
   @update-task-state {spec_name} "{task_text}" "completed"
   ```

3. **When skipping a task:**
   ```
   @update-task-state {spec_name} "{task_text}" "skipped"
   ```

---

## Safety Rules

1. **Never modify multiple tasks at once** - One task per call
2. **Always verify after update** - Don't trust the write succeeded
3. **Preserve file formatting** - Match exact indentation and spacing
4. **Don't update if sub-tasks incomplete** - Enforce hierarchy
5. **Stop on error** - Don't continue if update fails

---

## Testing

To test this prompt:

```bash
# Test 1: Mark task as in progress
@update-task-state map-scheduling-interface "0.1 Verify Google Maps API key is configured" "in_progress"

# Test 2: Mark task as completed
@update-task-state map-scheduling-interface "0.1 Verify Google Maps API key is configured" "completed"

# Test 3: Try to mark parent with incomplete sub-tasks (should fail)
@update-task-state map-scheduling-interface "5A.1 Backend Schema Updates" "completed"
```
