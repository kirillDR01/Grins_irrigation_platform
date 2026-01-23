# Ralph Wiggum Loop Implementation Planning

**Date:** January 21, 2026  
**Status:** Planning Complete - Ready for Implementation  
**Reference:** `Ralph_Wiggum_Guide.md`

---

## Executive Summary

This document captures the complete planning and design decisions for implementing a Ralph Wiggum-style autonomous agent loop adapted for the Grins Platform's existing Kiro spec infrastructure. The goal is to enable continuous, autonomous task execution through specs while maintaining safety, quality, and cost control.

---

## Table of Contents

1. [What is Ralph Wiggum?](#what-is-ralph-wiggum)
2. [Why Adapt for Grins Platform?](#why-adapt-for-grins-platform)
3. [Concept Mapping](#concept-mapping)
4. [Key Differences from Original](#key-differences-from-original)
5. [Design Decisions](#design-decisions)
6. [Recommended Configuration](#recommended-configuration)
7. [Implementation Plan](#implementation-plan)
8. [File Specifications](#file-specifications)
9. [Example Workflows](#example-workflows)
10. [Safety and Cost Control](#safety-and-cost-control)
11. [Testing Strategy](#testing-strategy)

---

## What is Ralph Wiggum?

Ralph Wiggum is a methodology for running AI coding agents in a continuous autonomous loop. It solves the common problem of agents finishing too early by forcing them to keep working and checking until tasks are truly complete.

### Core Loop Concept

```
┌─────────────────────────────────────────────────────────────┐
│                    RALPH WIGGUM LOOP                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  1. Read activity.md   │
              │     (current state)    │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  2. Read plan.md       │
              │     (find next task)   │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  3. Execute ONE task   │
              │     (implement change) │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  4. Validate work      │
              │     (tests, visual)    │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  5. Mark task complete │
              │     (update plan.md)   │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  6. Log in activity.md │
              │     (what was done)    │
              └────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  7. Check completion   │
              │     All tasks done?    │
              └────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
         ┌────────┐              ┌────────────┐
         │  YES   │              │     NO     │
         │ OUTPUT │              │  CONTINUE  │
         │COMPLETE│              │  TO STEP 1 │
         └────────┘              └────────────┘
```

### Best Used For

- Long-running tasks with clear task lists
- Projects where you already know what to build (specs exist)
- Tasks that benefit from continuous iteration without manual intervention
- Executing Kiro specs autonomously

### Not Ideal For

- Exploratory work without clear goals
- Quick one-off tasks
- Situations requiring frequent human input
- Tasks without defined acceptance criteria

---

## Why Adapt for Grins Platform?

The Grins Platform already has robust infrastructure that aligns with Ralph Wiggum concepts:

| Existing Infrastructure | Ralph Wiggum Equivalent |
|------------------------|------------------------|
| `.kiro/specs/{feature}/tasks.md` | `plan.md` |
| `taskStatus` tool | Task completion tracking |
| `agent-browser` CLI | Visual validation (Playwright) |
| `.kiro/steering/code-standards.md` | Quality enforcement |
| Checkpoint tasks in specs | Natural stopping points |

### Benefits of Adaptation

1. **Leverage Existing Specs**: Use the detailed task lists already created
2. **Integrated Quality Checks**: Enforce ruff, mypy, pyright, pytest automatically
3. **Visual Validation**: Use agent-browser for frontend testing
4. **Per-Spec Activity Logs**: Keep activity logs scoped to each feature
5. **Checkpoint Support**: Natural pause points at major milestones

---

## Concept Mapping

### Final Mapping (Grins Platform Adaptation)

| Ralph Wiggum Concept | Grins Platform Equivalent | Notes |
|---------------------|---------------------------|-------|
| `plan.md` | `.kiro/specs/{feature}/tasks.md` | Uses markdown checkbox format |
| `activity.md` | `.kiro/specs/{feature}/activity.md` | **NEW** - Per-spec activity log |
| `PROMPT.md` | `.kiro/prompts/ralph-loop.md` | Main entry point prompt |
| `passes: true/false` | `[x]` / `[ ]` checkbox format | Kiro's native task format |
| Playwright MCP | `agent-browser` CLI tool | Already installed and documented |
| `<promise>COMPLETE</promise>` | All tasks marked `[x]` | Or checkpoint reached |
| `ralph.sh` | `scripts/ralph.sh` | Bash wrapper for fresh context |
| Screenshots folder | `screenshots/{feature}/` | Per-spec screenshot storage |

### Task Format Comparison

**Original Ralph Wiggum (JSON):**
```json
{
  "category": "feature",
  "description": "Implement user authentication",
  "steps": ["Create login form", "Add validation", "Connect to API"],
  "passes": false
}
```

**Grins Platform (Markdown Checkbox):**
```markdown
- [ ] 2.1 Create appointments table migration
    - Define table with all columns from design
    - Add foreign keys to jobs and staff tables
    - Add indexes for job_id, staff_id, scheduled_date, status
    - _Requirements: 1.1, 1.2, 1.3_
```

---

## Key Differences from Original

### 1. Task Format
- **Original**: JSON with `passes: true/false`
- **Grins**: Markdown checkboxes `- [ ]` / `- [x]`
- **Rationale**: Leverages existing Kiro spec format, human-readable

### 2. Activity Log Scope
- **Original**: Single global `activity.md`
- **Grins**: Per-spec `activity.md` in `.kiro/specs/{feature}/`
- **Rationale**: Keeps logs organized by feature, easier to track progress

### 3. Quality Enforcement
- **Original**: Optional linting/testing
- **Grins**: Mandatory quality checks (ruff, mypy, pyright, pytest)
- **Rationale**: Follows existing code-standards.md requirements

### 4. Visual Validation
- **Original**: Playwright MCP or Claude for Chrome
- **Grins**: `agent-browser` CLI tool
- **Rationale**: Already documented in steering files, consistent tooling

### 5. Task Management
- **Original**: Manual file editing
- **Grins**: `taskStatus` tool integration
- **Rationale**: Uses Kiro's built-in task tracking

### 6. Checkpoint Support
- **Original**: Runs until all tasks complete
- **Grins**: Pauses at checkpoint tasks for user review
- **Rationale**: Natural stopping points in specs (e.g., "4. Checkpoint - Backend Complete")

---

## Design Decisions

### Decision 1: Context Mode

**Options Analyzed:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Fresh Context Each Iteration** | New context window per task (bash loop) | No context bloat, reduced hallucination | Loses context between tasks, slower startup |
| **Continuous Context** | Single context window for all tasks | Maintains context, faster | Context bloat, potential hallucination |
| **Continuous with Checkpoint Reset** ⭐ | Continuous until checkpoint, then fresh | Best of both worlds | Slightly more complex |

**Recommendation:** Continuous with Checkpoint Reset

**Rationale:** 
- Maintains context within a phase (e.g., all backend tasks)
- Fresh start at major milestones (checkpoints)
- Balances efficiency with context management
- Aligns with spec structure (checkpoints are natural boundaries)

---

### Decision 2: Continue Mode

**Options Analyzed:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Manual Continue** | User must trigger each task | Maximum control | Tedious, defeats purpose |
| **Auto-Continue All** | Runs until all tasks done | Fully autonomous | Risk of runaway costs, no review points |
| **Auto-Until-Checkpoint** ⭐ | Auto-continues until checkpoint task | Autonomous with review points | Requires checkpoint detection |

**Recommendation:** Auto-Until-Checkpoint

**Rationale:**
- Autonomous execution within phases
- Natural pause points for user review
- Prevents runaway execution
- Aligns with spec checkpoint structure

---

### Decision 3: Task Execution Granularity

**Options Analyzed:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Single Task** ⭐ | Execute one task per iteration | Safer, easier to debug, clear progress | Slower overall |
| **Batch Tasks** | Execute multiple related tasks | Faster | Harder to debug failures |
| **Full Phase** | Execute entire phase at once | Fastest | High risk, hard to recover |

**Recommendation:** Single Task

**Rationale:**
- Matches Ralph Wiggum philosophy ("ONLY WORK ON A SINGLE TASK")
- Easier to identify and fix failures
- Clear progress tracking
- Safer for autonomous execution

---

### Decision 4: State Storage

**Options Analyzed:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Tasks.md Only** | All state in task checkboxes | Simple | No execution history |
| **Activity.md Only** | All state in activity log | Rich history | No quick status view |
| **Hybrid** ⭐ | Tasks.md for status, activity.md for log | Best of both | Two files to maintain |

**Recommendation:** Hybrid

**Rationale:**
- `tasks.md`: Quick status view (what's done/pending)
- `activity.md`: Detailed execution history (what happened, when, issues)
- Matches Ralph Wiggum's original two-file approach
- Leverages existing Kiro task format

---

### Decision 5: Failure Handling

**Options Analyzed:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Abort Immediately** | Stop on first failure | Safe | May stop on transient issues |
| **Retry Forever** | Keep retrying failed task | Persistent | Risk of infinite loop |
| **Graduated Response** ⭐ | Retry → Ask User → Abort | Balanced | More complex logic |

**Recommendation:** Graduated Response

**Rationale:**
- Retry 3 times for transient failures
- Ask user for guidance if retries fail
- Abort if user doesn't respond or issue persists
- Prevents runaway costs while handling recoverable errors

---

### Decision 6: DEVLOG vs Activity.md

**User Modification:** Use per-spec `activity.md` instead of global `DEVLOG.md`

**Rationale:**
- `DEVLOG.md`: Reserved for manual development notes, high-level progress
- `activity.md`: Automated loop execution log, per-spec scope
- Keeps concerns separated
- Activity logs are disposable (can be cleared between runs)

---

## Recommended Configuration

```yaml
# Ralph Wiggum Loop Configuration for Grins Platform

context_mode: continuous_with_checkpoint_reset
# Options: fresh_each_iteration, continuous, continuous_with_checkpoint_reset
# Recommendation: continuous_with_checkpoint_reset

continue_mode: auto_until_checkpoint
# Options: manual, auto_all, auto_until_checkpoint
# Recommendation: auto_until_checkpoint

task_execution: single_task
# Options: single_task, batch_tasks, full_phase
# Recommendation: single_task

state_storage:
  task_status: .kiro/specs/{feature}/tasks.md
  activity_log: .kiro/specs/{feature}/activity.md
# Hybrid approach: tasks.md for status, activity.md for history

failure_handling: graduated_response
# Options: abort_immediately, retry_forever, graduated_response
# Recommendation: graduated_response

max_iterations: 50
# Maximum iterations before forced stop (cost control)

retry_limit: 3
# Number of retries before asking user

checkpoint_detection: true
# Pause at checkpoint tasks for user review

quality_checks:
  - ruff check src/
  - mypy src/
  - pyright src/
  - pytest -v
# Mandatory quality checks after each task

visual_validation:
  enabled: true
  tool: agent-browser
  screenshot_dir: screenshots/{feature}/
# Visual validation for frontend tasks
```

---

## Implementation Plan

### Phase 1: Core Components (Priority: High)

| File | Purpose | Description |
|------|---------|-------------|
| `.kiro/prompts/ralph-loop.md` | Main entry point | Starts the loop for a spec |
| `.kiro/prompts/ralph-status.md` | Status check | Shows current progress without executing |
| `.kiro/prompts/ralph-next.md` | Single task execution | Executes just the next task |
| `.kiro/prompts/ralph-skip.md` | Skip blocked task | Marks task as skipped with reason |
| `.kiro/steering/ralph-loop-patterns.md` | Behavior rules | Steering document for loop behavior |
| `.kiro/templates/activity-template.md` | Activity template | Template for per-spec activity.md |

### Phase 2: Automation (Priority: Medium)

| File | Purpose | Description |
|------|---------|-------------|
| `.kiro/hooks/ralph-continue.json` | Auto-continue hook | Triggers next iteration automatically |
| `scripts/ralph.sh` | Bash wrapper | Fresh context iterations (optional) |

### Phase 3: Integration (Priority: Medium)

| Integration | Description |
|-------------|-------------|
| `taskStatus` tool | Use Kiro's built-in task status updates |
| `agent-browser` | Visual validation for frontend tasks |
| Auto-create `activity.md` | Create activity.md when starting loop |
| Screenshot management | Organize screenshots by feature |

### Phase 4: Testing & Refinement (Priority: Low)

| Activity | Description |
|----------|-------------|
| Test with `admin-dashboard` | Full test run with 18 top-level tasks |
| Refine prompts | Adjust based on real-world results |
| Document lessons learned | Update this planning doc |
| Create troubleshooting guide | Common issues and solutions |

---

## File Specifications

### `.kiro/prompts/ralph-loop.md`

**Purpose:** Main entry point for starting the Ralph Wiggum loop

**Usage:** `@ralph-loop {spec-name}`

**Example:** `@ralph-loop admin-dashboard`

**Behavior:**
1. Validate spec exists at `.kiro/specs/{spec-name}/`
2. Read `tasks.md` to find current state
3. Read or create `activity.md`
4. Find next incomplete task (first `- [ ]`)
5. Execute task following code-standards.md
6. Run quality checks
7. Mark task complete using `taskStatus` tool
8. Log completion in `activity.md`
9. Check if at checkpoint → pause for user
10. If not checkpoint → continue to next task
11. Repeat until all tasks `[x]` or checkpoint reached

**Template Structure:**
```markdown
# Ralph Wiggum Loop

## Instructions

You are executing the Ralph Wiggum autonomous loop for the `{spec-name}` spec.

### Step 1: Read Current State
- Read `.kiro/specs/{spec-name}/activity.md` (create if missing)
- Read `.kiro/specs/{spec-name}/tasks.md`

### Step 2: Find Next Task
- Find the first task with `- [ ]` (not started)
- Skip tasks marked `- [~]` (queued) or `- [-]` (in progress)

### Step 3: Execute Task
- Follow the task description and sub-tasks
- Apply code-standards.md requirements
- Include logging, testing, type hints

### Step 4: Validate
- Run quality checks: ruff, mypy, pyright, pytest
- For frontend tasks: use agent-browser validation

### Step 5: Mark Complete
- Use taskStatus tool to mark task complete
- Update activity.md with completion entry

### Step 6: Check Continuation
- If task is a "Checkpoint" task → STOP and ask user
- If all tasks complete → output "LOOP COMPLETE"
- Otherwise → continue to next task

## Configuration
- Max iterations: 50
- Retry limit: 3
- Quality checks: MANDATORY
```

---

### `.kiro/prompts/ralph-status.md`

**Purpose:** Check current progress without executing

**Usage:** `@ralph-status {spec-name}`

**Output:**
```
## Ralph Wiggum Status: {spec-name}

### Progress
- Total Tasks: 18
- Completed: 5 (28%)
- In Progress: 1
- Remaining: 12

### Current Task
- [ ] 2.1 Create appointments table migration

### Recent Activity
- [2026-01-21 10:30] Completed: 1.5 Create steering documents
- [2026-01-21 10:15] Completed: 1.4 Create frontend hooks

### Next Checkpoint
- [ ] 4. Checkpoint - Backend Complete (7 tasks away)
```

---

### `.kiro/prompts/ralph-next.md`

**Purpose:** Execute just the next task (single iteration)

**Usage:** `@ralph-next {spec-name}`

**Behavior:**
- Same as ralph-loop but stops after one task
- Useful for manual step-through
- Does not auto-continue

---

### `.kiro/prompts/ralph-skip.md`

**Purpose:** Skip a blocked task with reason

**Usage:** `@ralph-skip {spec-name} {task-id} {reason}`

**Example:** `@ralph-skip admin-dashboard 2.1 "Waiting for database migration approval"`

**Behavior:**
- Marks task with `- [S]` (skipped)
- Logs skip reason in activity.md
- Continues to next task

---

### `.kiro/steering/ralph-loop-patterns.md`

**Purpose:** Steering document defining loop behavior rules

**Content:**
```markdown
# Ralph Wiggum Loop Patterns

## Core Rules

1. **Single Task Focus**: Execute ONE task at a time
2. **Quality First**: All quality checks must pass before marking complete
3. **Checkpoint Respect**: Always pause at checkpoint tasks
4. **Activity Logging**: Log every action in activity.md
5. **Failure Handling**: Retry 3x → Ask user → Abort

## Task Detection

### Task States
- `- [ ]` = Not started (execute this)
- `- [x]` = Completed (skip)
- `- [-]` = In progress (continue this)
- `- [~]` = Queued (skip for now)
- `- [S]` = Skipped (skip)

### Checkpoint Detection
Tasks containing "Checkpoint" in the name are checkpoint tasks.
Example: `- [ ] 4. Checkpoint - Backend Complete`

## Quality Requirements

Before marking any task complete:
1. Run `uv run ruff check src/`
2. Run `uv run mypy src/`
3. Run `uv run pyright src/`
4. Run `uv run pytest -v`

All must pass with zero errors.

## Activity Log Format

Each entry in activity.md should follow:
```
## [YYYY-MM-DD HH:MM] Task {task-id}: {task-name}

### What Was Done
- {description of changes}

### Files Modified
- {list of files}

### Quality Check Results
- Ruff: ✅ Pass
- MyPy: ✅ Pass
- Pyright: ✅ Pass
- Tests: ✅ 45/45 passing

### Notes
- {any issues or observations}
```
```

---

### `.kiro/templates/activity-template.md`

**Purpose:** Template for per-spec activity.md files

**Content:**
```markdown
# Activity Log: {spec-name}

## Current Status
**Last Updated:** {timestamp}
**Tasks Completed:** 0 / {total}
**Current Task:** None
**Loop Status:** Not Started

---

## Session Log

<!-- Ralph Wiggum loop will append entries here -->
```

---

### `scripts/ralph.sh`

**Purpose:** Bash wrapper for fresh context iterations (optional)

**Content:**
```bash
#!/bin/bash
# Ralph Wiggum Loop - Fresh Context Wrapper
# Usage: ./scripts/ralph.sh <spec-name> <max-iterations>

SPEC_NAME=$1
MAX_ITERATIONS=${2:-20}

if [ -z "$SPEC_NAME" ]; then
  echo "Usage: $0 <spec-name> [max-iterations]"
  echo "Example: $0 admin-dashboard 20"
  exit 1
fi

SPEC_DIR=".kiro/specs/$SPEC_NAME"
if [ ! -d "$SPEC_DIR" ]; then
  echo "Error: Spec not found at $SPEC_DIR"
  exit 1
fi

echo "🔄 Starting Ralph Wiggum Loop for: $SPEC_NAME"
echo "📊 Max iterations: $MAX_ITERATIONS"
echo "----------------------------------------"

for ((i=1; i<=$MAX_ITERATIONS; i++)); do
  echo ""
  echo "🔁 Iteration $i of $MAX_ITERATIONS"
  echo "----------------------------------------"
  
  # Run Kiro with the ralph-next prompt
  # Note: This assumes kiro-cli is available
  result=$(kiro-cli "@ralph-next $SPEC_NAME" 2>&1) || true
  
  echo "$result"
  
  # Check for completion
  if [[ "$result" == *"LOOP COMPLETE"* ]]; then
    echo ""
    echo "✅ All tasks complete after $i iterations!"
    exit 0
  fi
  
  # Check for checkpoint
  if [[ "$result" == *"CHECKPOINT REACHED"* ]]; then
    echo ""
    echo "⏸️  Checkpoint reached after $i iterations."
    echo "Review progress and run again to continue."
    exit 0
  fi
  
  # Check for error requiring user input
  if [[ "$result" == *"USER INPUT REQUIRED"* ]]; then
    echo ""
    echo "❓ User input required after $i iterations."
    exit 1
  fi
  
  echo ""
  echo "--- End of iteration $i ---"
done

echo ""
echo "⚠️  Reached max iterations ($MAX_ITERATIONS)"
echo "Run again to continue or increase max iterations."
exit 1
```

---

## Example Workflows

### Workflow 1: Full Autonomous Run

```
User: @ralph-loop admin-dashboard

Agent:
1. Reading .kiro/specs/admin-dashboard/tasks.md...
   - Total tasks: 18 top-level, 85 sub-tasks
   - Completed: 5 (Task 1.x)
   - Next: 2.1 Create appointments table migration

2. Creating activity.md...
   - Created .kiro/specs/admin-dashboard/activity.md

3. Executing Task 2.1...
   - Creating migration file
   - Adding columns, foreign keys, indexes
   - Running alembic upgrade head

4. Running quality checks...
   - Ruff: ✅ Pass
   - MyPy: ✅ Pass
   - Pyright: ✅ Pass
   - Tests: ✅ 127/127 passing

5. Marking task complete...
   - Updated tasks.md: [x] 2.1
   - Logged in activity.md

6. Continuing to Task 2.2...
   [... continues until checkpoint ...]

7. CHECKPOINT REACHED: Task 4 - Backend Complete
   - Pausing for user review
   - Run @ralph-loop admin-dashboard to continue
```

### Workflow 2: Single Task Execution

```
User: @ralph-next admin-dashboard

Agent:
1. Finding next task...
   - Next: 2.3 Create appointment Pydantic schemas

2. Executing Task 2.3...
   - Creating AppointmentCreate schema
   - Creating AppointmentUpdate schema
   - Creating AppointmentResponse schema
   - Adding validation

3. Running quality checks...
   - All passing ✅

4. Task 2.3 complete.
   - Stopping (single task mode)
```

### Workflow 3: Status Check

```
User: @ralph-status admin-dashboard

Agent:
## Ralph Wiggum Status: admin-dashboard

### Progress
- Total Tasks: 18 top-level (85 sub-tasks)
- Completed: 8 (44%)
- In Progress: 0
- Remaining: 10

### Last Completed
- [x] 2.8 Write appointment integration tests

### Next Task
- [ ] 3.1 Create dashboard Pydantic schemas

### Next Checkpoint
- [ ] 4. Checkpoint - Backend Complete (4 tasks away)

### Recent Activity (last 3)
- [2026-01-21 14:30] Completed: 2.8 Write appointment integration tests
- [2026-01-21 14:15] Completed: 2.7 Write appointment unit tests
- [2026-01-21 13:45] Completed: 2.6 Implement appointment API endpoints
```

---

## Safety and Cost Control

### Max Iterations

Always set a maximum iteration limit to prevent runaway costs:

```yaml
max_iterations: 50  # Recommended for large specs
max_iterations: 20  # Recommended for testing
max_iterations: 10  # Recommended for first run
```

### Checkpoint Pauses

Checkpoint tasks force a pause for user review:
- Review completed work
- Verify quality
- Decide whether to continue
- Adjust course if needed

### Quality Gates

Every task must pass quality checks before completion:
- Prevents accumulation of technical debt
- Catches issues early
- Ensures code standards compliance

### Graduated Failure Handling

```
Failure Detected
      │
      ▼
┌─────────────────┐
│  Retry (1/3)    │──► Success? → Continue
└─────────────────┘
      │ Fail
      ▼
┌─────────────────┐
│  Retry (2/3)    │──► Success? → Continue
└─────────────────┘
      │ Fail
      ▼
┌─────────────────┐
│  Retry (3/3)    │──► Success? → Continue
└─────────────────┘
      │ Fail
      ▼
┌─────────────────┐
│  Ask User       │──► User provides guidance → Retry
└─────────────────┘
      │ No response / Can't fix
      ▼
┌─────────────────┐
│  Abort Loop     │──► Log failure, stop execution
└─────────────────┘
```

### Cost Monitoring

Monitor costs by:
- Tracking iterations in activity.md
- Setting conservative max_iterations initially
- Reviewing activity logs after each run
- Adjusting based on actual usage

---

## Testing Strategy

### Phase 1: Manual Testing

1. Run `@ralph-status admin-dashboard` - verify status output
2. Run `@ralph-next admin-dashboard` - verify single task execution
3. Run `@ralph-loop admin-dashboard` - verify loop behavior
4. Verify checkpoint detection and pause

### Phase 2: Integration Testing

1. Test with `admin-dashboard` spec (18 top-level tasks)
2. Verify `taskStatus` tool integration
3. Verify `agent-browser` integration for frontend tasks
4. Verify activity.md logging

### Phase 3: Edge Case Testing

1. Test failure handling (introduce intentional failure)
2. Test retry logic
3. Test max iterations limit
4. Test checkpoint detection with various formats

### Success Criteria

- [ ] Loop executes tasks in correct order
- [ ] Quality checks run after each task
- [ ] Tasks marked complete correctly
- [ ] Activity.md updated with each task
- [ ] Checkpoints pause execution
- [ ] Failures handled gracefully
- [ ] Max iterations respected
- [ ] Screenshots captured for frontend tasks

---

## Appendix A: Existing Infrastructure Reference

### Specs Available for Testing

| Spec | Tasks | Status |
|------|-------|--------|
| `customer-management` | 12 top-level | Complete |
| `field-operations` | 17 top-level | Complete |
| `admin-dashboard` | 18 top-level | Partial (Task 1 complete) |

### Relevant Steering Documents

| Document | Purpose |
|----------|---------|
| `code-standards.md` | Quality requirements |
| `agent-browser.md` | Visual validation tool |
| `frontend-patterns.md` | Frontend development patterns |
| `frontend-testing.md` | Frontend testing patterns |
| `pre-implementation-analysis.md` | Pre-task analysis checklist |

### Relevant Tools

| Tool | Purpose |
|------|---------|
| `taskStatus` | Mark tasks in/complete |
| `agent-browser` | Headless browser automation |
| `getDiagnostics` | Check for code issues |
| `executeBash` | Run quality check commands |

---

## Appendix B: Quick Reference

### Commands

```bash
# Start autonomous loop
@ralph-loop {spec-name}

# Check status
@ralph-status {spec-name}

# Execute single task
@ralph-next {spec-name}

# Skip blocked task
@ralph-skip {spec-name} {task-id} {reason}

# Bash wrapper (fresh context)
./scripts/ralph.sh {spec-name} {max-iterations}
```

### File Locations

```
.kiro/
├── prompts/
│   ├── ralph-loop.md           # Main entry point
│   ├── ralph-status.md         # Status check
│   ├── ralph-next.md           # Single task
│   └── ralph-skip.md           # Skip task
├── steering/
│   └── ralph-loop-patterns.md  # Behavior rules
├── templates/
│   └── activity-template.md    # Activity log template
└── specs/
    └── {feature}/
        ├── requirements.md
        ├── design.md
        ├── tasks.md            # Task list (plan.md equivalent)
        └── activity.md         # Execution log (NEW)

scripts/
└── ralph.sh                    # Bash wrapper
```

### Quality Check Commands

```bash
# All checks (must all pass)
uv run ruff check src/
uv run mypy src/
uv run pyright src/
uv run pytest -v

# Combined
uv run ruff check src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v
```

---

## Next Steps

When ready to implement:

1. **Create Phase 1 files** (prompts and steering)
2. **Test with admin-dashboard spec**
3. **Refine based on results**
4. **Add automation (Phase 2)**
5. **Document lessons learned**

---

*This planning document captures the complete design for adapting Ralph Wiggum to the Grins Platform. Implementation should follow the phased approach outlined above.*
