# Log Activity (Internal)

**Purpose:** Append a structured entry to activity.md with consistent format and validation.

**Usage:** Called internally by ralph-loop after task completion.

---

## Parameters

- `spec_name`: Name of the spec (e.g., "map-scheduling-interface")
- `task_id`: Task ID (e.g., "1.1")
- `task_name`: Task name (e.g., "Add coordinate fields to ScheduleJobAssignment schema")
- `what_was_done`: Bullet list of changes made
- `files_modified`: List of file paths with descriptions
- `quality_results`: Output from @validate-quality
- `notes`: Any issues, decisions, or observations

---

## Instructions

You are logging a completed task to activity.md. Use the exact template format.

### Step 1: Get Current Timestamp

Format: `YYYY-MM-DD HH:MM`

Example: `2026-01-24 18:15`

### Step 2: Format Entry

Use this EXACT template:

```markdown
## [{timestamp}] Task {task_id}: {task_name}

### What Was Done
{what_was_done}

### Files Modified
{files_modified}

### Quality Check Results
{quality_results}

### Notes
{notes}
```

**Field Requirements:**

1. **What Was Done** - Bullet list format:
   ```markdown
   - Implemented coordinate fields in ScheduleJobAssignment schema
   - Added latitude and longitude as float fields
   - Updated schema validation
   ```

2. **Files Modified** - File path with description:
   ```markdown
   - `src/grins_platform/schemas/schedule_generation.py` - Added latitude/longitude fields
   - `src/grins_platform/tests/test_schemas.py` - Added tests for new fields
   ```

3. **Quality Check Results** - Paste output from @validate-quality:
   ```markdown
   ✅ Quality Checks PASSED
   - Ruff: ✅ Pass (0 errors)
   - MyPy: ✅ Pass (0 errors)
   - Pyright: ✅ Pass (0 errors)
   - Tests: ✅ Pass (127/127 passing)
   ```

4. **Notes** - Any observations:
   ```markdown
   - Used float type for coordinates (sufficient precision)
   - Considered Decimal but float is standard for lat/lng
   - All existing tests still pass
   ```

### Step 3: Append to Activity.md

1. Read `.kiro/specs/{spec_name}/activity.md`
2. Find the "Activity Entries" section
3. Use `fs_write` with `append` command to add the entry
4. Add blank line before entry for readability

**Important:** Append to the END of the file, not after the header.

### Step 4: Update Current Status

After appending the entry, update the "Current Status" section:

1. Read tasks.md to count completed tasks
2. Calculate total tasks
3. Find next incomplete task
4. Update the status section:

```markdown
## Current Status
**Last Updated:** {current_timestamp}
**Tasks Completed:** {completed_count} / {total_count}
**Current Task:** {next_task_id} - {next_task_name}
**Loop Status:** Running
```

Use `fs_write` with `str_replace` to update this section.

### Step 5: Verify Entry Was Added

1. Read activity.md again
2. Search for the task_id in the last 50 lines
3. Use grep to verify:

```bash
tail -50 .kiro/specs/{spec_name}/activity.md | grep "Task {task_id}"
```

4. If grep returns a match → SUCCESS
5. If grep returns no match → ERROR

### Step 6: Output Result

**On SUCCESS:**
```
✅ Activity Logged
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_id} - {task_name}
File: .kiro/specs/{spec_name}/activity.md
Verified: ✅
```

**On ERROR:**
```
❌ Activity Logging Failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_id} - {task_name}
Reason: {error reason}

Action: Continue anyway (logging failure is not critical)
```

---

## Error Handling

### Common Errors

1. **File not found:**
   - Create activity.md with template
   - Retry append

2. **Append failed:**
   - Retry once
   - If still fails, output ERROR but continue

3. **Verification failed:**
   - Check if entry was actually added
   - If added, ignore verification error
   - If not added, output ERROR

### Retry Logic

1. If append fails, retry ONCE
2. If second attempt fails, output ERROR but continue
3. Do NOT stop execution for logging failures

---

## Examples

### Example 1: Backend Task

**Input:**
- spec_name: "map-scheduling-interface"
- task_id: "1.1"
- task_name: "Add coordinate fields to ScheduleJobAssignment schema"
- what_was_done: "- Added latitude and longitude fields\n- Updated schema validation\n- Added type hints"
- files_modified: "- `src/grins_platform/schemas/schedule_generation.py` - Added coordinate fields"
- quality_results: "✅ Quality Checks PASSED\n- Ruff: ✅ Pass\n- MyPy: ✅ Pass\n- Pyright: ✅ Pass\n- Tests: ✅ 127/127"
- notes: "- Used float type for coordinates\n- All tests pass"

**Output Entry:**
```markdown
## [2026-01-24 18:15] Task 1.1: Add coordinate fields to ScheduleJobAssignment schema

### What Was Done
- Added latitude and longitude fields
- Updated schema validation
- Added type hints

### Files Modified
- `src/grins_platform/schemas/schedule_generation.py` - Added coordinate fields

### Quality Check Results
✅ Quality Checks PASSED
- Ruff: ✅ Pass
- MyPy: ✅ Pass
- Pyright: ✅ Pass
- Tests: ✅ 127/127

### Notes
- Used float type for coordinates
- All tests pass
```

### Example 2: Frontend Task

**Input:**
- spec_name: "map-scheduling-interface"
- task_id: "2.1"
- task_name: "Create MapView component"
- what_was_done: "- Created MapView.tsx component\n- Added Google Maps integration\n- Implemented marker display"
- files_modified: "- `frontend/src/features/schedule/components/MapView.tsx` - New component\n- `frontend/src/features/schedule/types/index.ts` - Added MapProps type"
- quality_results: "✅ Quality Checks PASSED\n- ESLint: ✅ Pass\n- TypeScript: ✅ Pass\n- Tests: ✅ 5/5"
- notes: "- Used @react-google-maps/api library\n- Component is responsive"

**Output Entry:**
```markdown
## [2026-01-24 18:30] Task 2.1: Create MapView component

### What Was Done
- Created MapView.tsx component
- Added Google Maps integration
- Implemented marker display

### Files Modified
- `frontend/src/features/schedule/components/MapView.tsx` - New component
- `frontend/src/features/schedule/types/index.ts` - Added MapProps type

### Quality Check Results
✅ Quality Checks PASSED
- ESLint: ✅ Pass
- TypeScript: ✅ Pass
- Tests: ✅ 5/5

### Notes
- Used @react-google-maps/api library
- Component is responsive
```

---

## Integration with Ralph-Loop

Ralph-loop should call this prompt at Step 7:

```markdown
### Step 7: Log Activity

Call @log-activity with:
- spec_name: {current spec}
- task_id: {task ID from tasks.md}
- task_name: {task name from tasks.md}
- what_was_done: {bullet list of what you implemented}
- files_modified: {list of files you changed}
- quality_results: {output from @validate-quality}
- notes: {any observations or decisions}

If ERROR returned, continue anyway (logging is not critical).
```

---

## Safety Rules

1. **Never skip logging** - Always attempt to log
2. **Use exact template** - Don't modify format
3. **Append to end** - Don't insert in middle
4. **Continue on error** - Logging failure is not critical
5. **Verify after append** - Ensure entry was added

---

## Testing

To test this prompt:

```bash
# Test 1: Log a backend task
@log-activity map-scheduling-interface "1.1" "Add coordinate fields" "- Added fields" "- schema.py" "✅ All pass" "- No issues"

# Test 2: Log a frontend task
@log-activity map-scheduling-interface "2.1" "Create MapView" "- Created component" "- MapView.tsx" "✅ All pass" "- Responsive"

# Test 3: Verify entry in activity.md
tail -50 .kiro/specs/map-scheduling-interface/activity.md
```

---

## Known Limitations

1. **No structured data** - Uses markdown, not JSON
2. **No search capability** - Must read entire file
3. **No entry editing** - Can only append
4. **No entry deletion** - Permanent record

### Future Enhancements

- Add JSON export for analysis
- Add search/filter capability
- Add entry editing for corrections
- Add summary generation
