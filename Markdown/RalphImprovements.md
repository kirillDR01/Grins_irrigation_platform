# Ralph Wiggum Loop - Autonomy Improvements

**Created:** 2026-01-24  
**Status:** Implementation in progress  
**Goal:** Make Ralph Wiggum loop fully autonomous for overnight/unattended execution

---

## Current State Analysis

### What Works ✅

1. **Task Discovery**
   - Correctly parses tasks.md for checkbox states
   - Finds first incomplete task
   - Respects task hierarchy (sub-tasks before parent)
   - Recognizes checkpoint tasks

2. **Code Implementation**
   - Reads requirements.md and design.md for context
   - Writes code following steering documents
   - Includes logging, type hints, and tests
   - Follows code-standards.md patterns

3. **Fresh Context Execution**
   - Bash script (ralph.sh) provides fresh context per iteration
   - Prevents context bloat
   - Reduces hallucination risk
   - Handles max iterations safety limit

4. **Checkpoint System**
   - Detects "Checkpoint" in task names
   - Outputs "CHECKPOINT REACHED" signal
   - Bash script pauses for user review

5. **Basic Error Recovery**
   - ralph-nudge.json hook suggests alternatives on agent stop
   - Provides recovery strategies for common issues

### What Doesn't Work ❌

1. **Task State Updates**
   - No reliable mechanism to update checkboxes in tasks.md
   - Manual fs_write str_replace with no validation
   - Could update wrong task or corrupt file format
   - No atomic operation guarantee

2. **Quality Gate Enforcement**
   - Quality checks are suggestions, not requirements
   - Agent can mark task complete even if tests fail
   - No automatic retry on quality check failure
   - No structured error handling

3. **Activity Logging**
   - Inconsistent format across entries
   - Missing required fields
   - No validation that log was written
   - Agent could forget to log

4. **Retry State Tracking**
   - No persistence of retry attempts
   - Agent doesn't know if this is attempt 1, 2, or 3
   - Could retry infinitely or give up too early
   - No history of what approaches were tried

5. **Visual Validation**
   - Frontend tasks suggest agent-browser but it's optional
   - No enforcement that UI actually works
   - Could mark complete without visual testing

6. **Stagnation Detection**
   - No timeout within a single task
   - Agent could spin on same error for 10+ minutes
   - No forced alternative approach after timeout

7. **Parallel Execution**
   - No subagent delegation for independent tasks
   - Sequential execution even when parallelization possible
   - Slower than necessary

---

## Required Fixes for Full Autonomy

### Fix 1: Atomic Task State Updates ⚠️ CRITICAL

**Problem:** No reliable way to update task checkboxes in tasks.md.

**Impact:** Ralph can't track progress, could re-execute completed tasks, or lose state.

**Solution:** Create dedicated task state manager with validation.

**Implementation:**
- Create `.kiro/prompts/internal/update-task-state.md`
- Provides atomic checkbox updates with verification
- Handles all states: in_progress, completed, skipped
- Validates update succeeded before continuing

**Process:**
1. Read tasks.md
2. Find exact task text match
3. Determine replacement pattern based on new state
4. Use fs_write str_replace to update
5. Read file again to verify update
6. If verification fails, output ERROR and stop

**Validation:**
```bash
grep "^\- \[x\] {task_text}" .kiro/specs/{spec_name}/tasks.md
```

**Estimated Effort:** 30 minutes

---

### Fix 2: Quality Gate Enforcement ⚠️ CRITICAL

**Problem:** Quality checks are suggestions, agent can skip them.

**Impact:** Could ship broken code, failing tests, type errors.

**Solution:** Structured quality validation with automatic retry.

**Implementation:**
- Create `.kiro/prompts/internal/validate-quality.md`
- Enforces ALL quality checks must pass
- Parses output for pass/fail status
- Returns structured results

**Backend Checks:**
1. `uv run ruff check src/` - Must show "All checks passed!"
2. `uv run mypy src/` - Must show "Success: no issues found"
3. `uv run pyright src/` - Must show "0 errors"
4. `uv run pytest -v` - Must show all tests passing

**Frontend Checks:**
1. `cd frontend && npm run lint` - Must show "0 problems"
2. `cd frontend && npm run typecheck` - Must show "0 errors"
3. `cd frontend && npm test` - Must show "Tests passed"

**Retry Logic:**
- If ANY check fails → return FAILED with details
- Agent must fix issues and retry
- Max 3 retry attempts per task
- After 3 failures → USER INPUT REQUIRED

**Output Format:**
```
SUCCESS:
  - Ruff: ✅ Pass
  - MyPy: ✅ Pass
  - Pyright: ✅ Pass
  - Tests: ✅ 127/127 passing

FAILED (attempt 2/3):
  - Ruff: ❌ 3 errors
  - MyPy: ✅ Pass
  - Pyright: ❌ 1 error
  - Tests: ❌ 2/127 failed

Errors:
{actual error messages}
```

**Estimated Effort:** 45 minutes

---

### Fix 3: Structured Activity Logging 🔶 HIGH PRIORITY

**Problem:** Inconsistent activity log format, missing fields.

**Impact:** Hard to debug issues, unclear what was done.

**Solution:** Template-based logging with validation.

**Implementation:**
- Create `.kiro/prompts/internal/log-activity.md`
- Enforces consistent format
- Validates entry was written
- Includes all required fields

**Template:**
```markdown
## [{YYYY-MM-DD HH:MM}] Task {task_id}: {task_name}

### What Was Done
{bullet list of changes}

### Files Modified
{list of file paths}

### Quality Check Results
{output from validate-quality}

### Notes
{any issues or observations}
```

**Process:**
1. Get current timestamp
2. Format entry using template
3. Use fs_write append to add to activity.md
4. Read activity.md to verify entry was added
5. If verification fails, output ERROR (but continue)

**Validation:**
```bash
tail -20 .kiro/specs/{spec_name}/activity.md | grep "Task {task_id}"
```

**Estimated Effort:** 30 minutes

---

### Fix 4: Retry State Tracking ⚠️ CRITICAL

**Problem:** No way to track retry attempts across iterations.

**Impact:** Could retry infinitely or give up too early.

**Solution:** Add retry state section to activity.md.

**Implementation:**
- Modify activity.md template to include "Retry Tracking" section
- Update ralph-loop.md to check/update retry state
- Enforce 3-attempt limit per task

**Activity.md Template Update:**
```markdown
# Activity Log: {spec-name}

## Current Status
**Last Updated:** {timestamp}
**Tasks Completed:** {completed} / {total}
**Current Task:** {task-id} - {task-name}
**Loop Status:** Running

## Retry Tracking
<!-- Format: Task {task-id}: Attempt {n}/3 [{status}] [{reason}] -->

---

## Activity Entries
...
```

**Ralph-Loop Integration:**

**Step 3.5: Check Retry State**
1. Read activity.md "Retry Tracking" section
2. Look for line: "Task {task-id}: Attempt {n}/3"
3. If found:
   - Extract attempt number
   - If attempt >= 3, skip this task and output USER INPUT REQUIRED
   - Otherwise, increment attempt number
4. If not found:
   - This is attempt 1
5. Append to Retry Tracking:
   ```
   Task {task-id}: Attempt {n}/3 [started] [{timestamp}]
   ```

**Step 5.5: Update Retry State on Failure**
1. If quality checks fail:
   - Update Retry Tracking line:
     ```
     Task {task-id}: Attempt {n}/3 [failed] [{error summary}]
     ```
2. If n < 3, continue to retry
3. If n >= 3, output USER INPUT REQUIRED

**Estimated Effort:** 20 minutes

---

### Fix 5: Visual Validation Enforcement 🔶 MEDIUM PRIORITY

**Problem:** Frontend tasks don't enforce visual checks with agent-browser.

**Impact:** UI might not work even if code compiles.

**Solution:** Make agent-browser validation mandatory for frontend tasks.

**Implementation:**
- Modify ralph-loop.md to add visual validation step
- Ensure dev server is running
- Execute agent-browser commands from tasks.md
- Parse output for success/failure
- Take screenshots for documentation

**Process:**
1. Ensure frontend dev server is running:
   ```bash
   cd frontend && npm run dev &
   sleep 5
   ```

2. Run agent-browser validation from tasks.md:
   ```bash
   {copy validation commands from task}
   ```

3. Parse agent-browser output:
   - If "visible" or "exists" → SUCCESS
   - If "not found" or "error" → FAILED

4. Take screenshot for documentation:
   ```bash
   agent-browser screenshot screenshots/{task-id}.png
   ```

5. If visual validation FAILED:
   - Treat as quality check failure
   - Retry up to 3 times
   - After 3 failures, output USER INPUT REQUIRED

**Estimated Effort:** 30 minutes

---

### Fix 6: Task-Level Timeout 🔶 MEDIUM PRIORITY

**Problem:** Agent could spin on same error indefinitely within a single task.

**Impact:** Wastes time and tokens on stuck tasks.

**Solution:** Add 15-minute timeout per task with forced alternative approach.

**Implementation:**
- Modify ralph-loop.md to track task start time
- Check elapsed time before quality checks
- Force alternative approach on timeout

**Process:**

**Step 4: Execute Task (WITH TIMEOUT)**

1. Log start time in activity.md:
   ```
   Task {task-id}: Started at {timestamp}
   ```

2. Implement the task

3. Before quality checks, check elapsed time:
   - If < 15 minutes → proceed normally
   - If >= 15 minutes → TIMEOUT TRIGGERED

4. On TIMEOUT:
   a. Log: "Task {task-id}: TIMEOUT after 15 minutes"
   b. Analyze what's taking so long:
      - Stuck on npm install? → Install packages individually
      - Stuck on shadcn CLI? → Create component files manually
      - Stuck on complex logic? → Simplify scope
   c. Try alternative approach (counts as retry attempt)
   d. If alternative also times out → USER INPUT REQUIRED

**Ralph-Nudge Hook Update:**
```json
{
  "when": {
    "type": "agentStop"
  },
  "then": {
    "type": "askAgent",
    "prompt": "TIMEOUT CHECK: If you've been working on the same task for >15 minutes:\n1. Log the timeout in activity.md\n2. Try a completely different approach\n3. If no alternative exists, mark task as blocked and continue to next task\n\nDO NOT wait for user input. Make a decision and continue."
  }
}
```

**Estimated Effort:** 20 minutes

---

### Fix 7: Parallel Execution Support 🔷 LOW PRIORITY

**Problem:** Ralph executes tasks sequentially even when parallelization is possible.

**Impact:** Slower execution, but not broken.

**Solution:** Add subagent delegation for independent tasks.

**Implementation:**
- Create `.kiro/prompts/internal/check-parallelization.md`
- Analyze task dependencies
- Use use_subagent tool for parallel execution
- Modify ralph-loop.md to check for parallelization opportunities

**Process:**

**Check Parallelization:**
1. Read tasks.md
2. Find next 5 incomplete tasks
3. Analyze dependencies:
   - Do they modify the same files?
   - Do they depend on each other's output?
   - Are they in the same layer (backend/frontend)?
4. If 2+ tasks are independent → return PARALLEL_OPPORTUNITY
5. Otherwise → return SEQUENTIAL

**Parallel Execution:**
```javascript
use_subagent([
  {
    "query": "@ralph-next {spec-name} --task 1.1",
    "agent_name": "spec-task-execution"
  },
  {
    "query": "@ralph-next {spec-name} --task 1.2",
    "agent_name": "spec-task-execution"
  }
])
```

**Output Format:**
```
PARALLEL_OPPORTUNITY:
  - Task 1.1: Add coordinate fields (backend schema)
  - Task 1.2: Add start location fields (backend schema)
  - Task 2.1: Update frontend types (frontend types)
  
  Recommendation: Run 1.1 and 1.2 in parallel (same layer, different files)

SEQUENTIAL:
  - Task 1.1 must complete before 1.2 (1.2 depends on 1.1)
```

**Estimated Effort:** 60 minutes

---

## Implementation Priority

### Phase 1: Minimum Viable Autonomy (2 hours)
1. ✅ Fix 1: Atomic Task State Updates (30 min) - **CRITICAL**
2. ✅ Fix 2: Quality Gate Enforcement (45 min) - **CRITICAL**
3. ✅ Fix 4: Retry State Tracking (20 min) - **CRITICAL**
4. ✅ Fix 3: Structured Activity Logging (30 min) - **HIGH**

**After Phase 1:** Ralph can run autonomously overnight without user intervention.

### Phase 2: Enhanced Reliability (1 hour)
5. Fix 5: Visual Validation Enforcement (30 min) - **MEDIUM**
6. Fix 6: Task-Level Timeout (20 min) - **MEDIUM**

**After Phase 2:** Ralph handles edge cases and frontend validation.

### Phase 3: Performance Optimization (1 hour)
7. Fix 7: Parallel Execution Support (60 min) - **LOW**

**After Phase 3:** Ralph executes tasks faster via parallelization.

---

## Testing Strategy

### Unit Testing
- Test each internal prompt in isolation
- Verify task state updates work correctly
- Verify quality check parsing is accurate
- Verify activity logging format is consistent

### Integration Testing
- Run ralph-loop on a small spec (5-10 tasks)
- Verify all tasks complete successfully
- Verify activity.md is complete and accurate
- Verify tasks.md checkboxes are all marked

### Stress Testing
- Run ralph-loop on large spec (40+ tasks)
- Verify checkpoint pauses work
- Verify retry logic works (introduce intentional failures)
- Verify timeout recovery works

### Overnight Testing
- Run ralph-loop with max_iterations=100
- Leave running overnight
- Verify progress in morning
- Check for any stuck tasks or infinite loops

---

## Success Criteria

### Minimum Viable Autonomy
- ✅ Ralph can update task states reliably
- ✅ Ralph enforces quality checks before marking complete
- ✅ Ralph tracks retry attempts and stops after 3 failures
- ✅ Ralph logs all activity in consistent format
- ✅ Ralph can run overnight without user intervention

### Enhanced Reliability
- ✅ Ralph validates frontend UI with agent-browser
- ✅ Ralph detects and recovers from timeouts
- ✅ Ralph provides clear error messages when blocked

### Performance Optimization
- ✅ Ralph parallelizes independent tasks
- ✅ Ralph completes specs 30-50% faster

---

## Rollout Plan

### Step 1: Create Internal Prompts
- Create `.kiro/prompts/internal/` directory
- Implement update-task-state.md
- Implement validate-quality.md
- Implement log-activity.md

### Step 2: Update Ralph-Loop Prompt
- Integrate task state updates
- Integrate quality gate enforcement
- Integrate retry state tracking
- Integrate structured activity logging

### Step 3: Update Activity.md Template
- Add "Retry Tracking" section
- Update "Current Status" section format

### Step 4: Test on Small Spec
- Run on spec with 5-10 tasks
- Verify all fixes work correctly
- Fix any issues found

### Step 5: Test on Large Spec
- Run on spec with 40+ tasks
- Verify checkpoint pauses work
- Verify retry logic works
- Verify overnight execution works

### Step 6: Document and Deploy
- Update Ralph_Wiggum_Guide.md with new features
- Update ralph-loop-patterns.md with new behavior
- Announce to team

---

## Known Limitations

### After All Fixes
1. **No cross-spec dependencies** - Ralph can't handle tasks that depend on other specs
2. **No dynamic task generation** - Ralph can't add new tasks during execution
3. **No user interaction mid-loop** - Ralph can't ask clarifying questions
4. **No rollback on failure** - Ralph doesn't undo changes if task fails
5. **No cost tracking** - Ralph doesn't monitor token usage or API costs

### Future Enhancements
- Add cost tracking and budget limits
- Add rollback capability for failed tasks
- Add dynamic task generation based on discoveries
- Add cross-spec dependency resolution
- Add mid-loop user interaction for ambiguous cases

---

## Maintenance

### Regular Reviews
- Review activity logs weekly for patterns
- Identify common failure modes
- Update steering documents based on learnings
- Refine quality check parsing as tools evolve

### Version Control
- Track changes to internal prompts
- Document breaking changes
- Maintain changelog for Ralph improvements

### Performance Monitoring
- Track average time per task
- Track retry rate per task type
- Track checkpoint pause frequency
- Track overnight success rate

---

## Conclusion

These improvements transform Ralph Wiggum from a semi-autonomous loop requiring frequent user intervention into a fully autonomous system capable of overnight execution. The critical fixes (1, 2, 4) provide the foundation for reliable autonomous operation, while the additional fixes (3, 5, 6, 7) enhance reliability and performance.

**Total Implementation Time:** ~4 hours  
**Minimum Viable Autonomy:** ~2 hours  
**Expected Outcome:** Ralph can execute 40+ task specs overnight without user intervention.
