# Ralph Wiggum Overnight Mode - Startup Guide

This guide explains how to start the Ralph Wiggum autonomous execution loop for overnight/unattended runs.

---

## Quick Start

```bash
# Basic usage
./scripts/ralph-overnight.sh <spec-name> [max-iterations]

# Examples
./scripts/ralph-overnight.sh map-scheduling-interface 100
./scripts/ralph-overnight.sh admin-dashboard 50
```

---

## Prerequisites

Before starting an overnight run, ensure you have:

### 1. Required Tools

| Tool | Purpose | Check Command |
|------|---------|---------------|
| `kiro-cli` | Execute tasks via Kiro | `kiro-cli --version` |
| `uv` | Python package manager | `uv --version` |
| `npm` | Node.js package manager | `npm --version` |
| `docker` (optional) | PostgreSQL database | `docker --version` |

### 2. Install kiro-cli (if not installed)

```bash
curl -fsSL https://cli.kiro.dev/install | bash
kiro-cli login  # Authenticate
```

### 3. Verify Spec Exists

```bash
# List available specs
ls -1 .kiro/specs/

# Verify spec has tasks.md
cat .kiro/specs/<spec-name>/tasks.md | head -20
```

---

## Step-by-Step Startup

### Step 1: Choose Your Spec

Available specs in this project:
- `admin-dashboard` - Admin dashboard features
- `map-scheduling-interface` - Map-based scheduling UI
- `field-operations` - Field operations management
- `customer-management` - Customer CRM features
- `route-optimization` - Route optimization engine
- `ai-assistant` - AI assistant features

### Step 2: Check Current Progress

```bash
# See how many tasks are complete
grep -c "^\- \[x\]" .kiro/specs/<spec-name>/tasks.md
grep -c "^\- \[ \]" .kiro/specs/<spec-name>/tasks.md
```

### Step 3: Start the Overnight Run

```bash
# Run with default 100 iterations
./scripts/ralph-overnight.sh map-scheduling-interface

# Run with custom iteration limit
./scripts/ralph-overnight.sh map-scheduling-interface 50

# Run in background (for true overnight execution)
nohup ./scripts/ralph-overnight.sh map-scheduling-interface 100 > /tmp/ralph-run.log 2>&1 &
```

### Step 4: Monitor Progress (Optional)

```bash
# Watch the log file
tail -f /tmp/ralph-run.log

# Check activity log
cat .kiro/specs/<spec-name>/activity.md

# Check task completion
grep "^\- \[x\]" .kiro/specs/<spec-name>/tasks.md | wc -l
```

---

## What Happens During Execution

### Pre-Flight Phase
1. ✅ Validates spec exists and has tasks.md
2. ✅ Checks for required tools (kiro-cli, uv, npm)
3. ✅ Starts PostgreSQL via Docker (if available)
4. ✅ Starts backend server on port 8000
5. ✅ Starts frontend server on port 5173
6. ✅ Verifies all services are healthy

### Main Loop Phase
For each iteration:
1. 🔄 Checks server health (restarts if needed)
2. 🔄 Calls `kiro-cli chat --no-interactive --trust-all-tools "..."` with task instructions
3. 🔄 Parses output signal (TASK_COMPLETE, TASK_SKIPPED, CHECKPOINT_PASSED, CHECKPOINT_FAILED, etc.)
4. 🔄 Logs progress
5. 🔄 For checkpoints: Ensures ALL quality checks pass before continuing
6. 🔄 Continues to next iteration (or stops if CHECKPOINT_FAILED)

### Post-Flight Phase
1. 📊 Generates final report
2. 💾 Commits all changes to git
3. 🧹 Stops servers and cleans up

---

## Output Signals

The loop watches for these signals from each task execution:

| Signal | Meaning | Loop Action |
|--------|---------|-------------|
| `TASK_COMPLETE` | Task finished successfully | Continue to next |
| `TASK_SKIPPED: {reason}` | Regular task skipped due to failure | Continue to next |
| `ALL_TASKS_COMPLETE` | No more tasks to execute | Exit loop |
| `CHECKPOINT_PASSED: {name}` | Checkpoint validation passed | Continue to next |
| `CHECKPOINT_FAILED: {name}` | Checkpoint failed after 5 fix attempts | **STOP loop** |

### Checkpoint Behavior

Checkpoints are **quality gates** that ensure all code passes validation:

- **ALL quality checks must pass** (ruff, mypy, pyright, pytest)
- If checks fail, the agent will **fix the issues** and retry (up to 5 times)
- Checkpoints are **NEVER skipped** - they block until all checks pass
- If a checkpoint fails after 5 fix attempts, the loop **STOPS** to prevent proceeding with broken code

---

## Logs and Reports

### During Execution

| Log | Location | Purpose |
|-----|----------|---------|
| Main output | Terminal or `/tmp/ralph-run.log` | Overall progress |
| Backend log | `/tmp/ralph-overnight/backend.log` | Backend server output |
| Frontend log | `/tmp/ralph-overnight/frontend.log` | Frontend server output |
| Activity log | `.kiro/specs/<spec-name>/activity.md` | Per-task details |

### After Completion

| File | Location | Content |
|------|----------|---------|
| Final report | `/tmp/ralph-overnight/report.txt` | Summary statistics |
| Git commit | Repository | All changes committed |

---

## Troubleshooting

### Script Won't Start

```bash
# Check if script is executable
chmod +x scripts/ralph-overnight.sh

# Check syntax
bash -n scripts/ralph-overnight.sh
```

### kiro-cli Not Found

```bash
# Install kiro-cli
curl -fsSL https://cli.kiro.dev/install | bash

# Add to PATH (if needed)
export PATH="$HOME/.kiro/bin:$PATH"

# Authenticate
kiro-cli login
```

### Servers Won't Start

```bash
# Check if ports are in use
lsof -i :8000  # Backend
lsof -i :5173  # Frontend

# Kill existing processes
kill $(lsof -t -i :8000)
kill $(lsof -t -i :5173)
```

### Database Issues

```bash
# Start database manually
docker-compose up -d db

# Check database is running
docker ps | grep postgres
```

### Loop Stuck

```bash
# Check the activity log for errors
tail -50 .kiro/specs/<spec-name>/activity.md

# Check backend logs
tail -50 /tmp/ralph-overnight/backend.log

# Check frontend logs
tail -50 /tmp/ralph-overnight/frontend.log
```

---

## Stopping the Loop

### Graceful Stop

Press `Ctrl+C` - the script will:
1. Catch the interrupt signal
2. Stop backend and frontend servers
3. Clean up PID files
4. Exit cleanly

### Force Stop

```bash
# Find and kill the script
pkill -f ralph-overnight

# Kill servers manually
kill $(cat /tmp/ralph-overnight/backend.pid) 2>/dev/null
kill $(cat /tmp/ralph-overnight/frontend.pid) 2>/dev/null
```

---

## Best Practices

### Before Starting

1. **Review the spec** - Make sure tasks are well-defined
2. **Check dependencies** - Ensure all tools are installed
3. **Start fresh** - Consider `git stash` for uncommitted changes
4. **Set realistic iterations** - Start with 20-50 for testing

### During Execution

1. **Don't modify files** - Let the loop work uninterrupted
2. **Monitor occasionally** - Check logs every few hours
3. **Trust the process** - Tasks will be skipped if they fail

### After Completion

1. **Review activity.md** - See what was done
2. **Check skipped tasks** - May need manual intervention
3. **Run quality checks** - Verify everything passes
4. **Review git diff** - Before pushing changes

---

## Example: Full Overnight Run

```bash
# 1. Check current state
echo "=== Current Progress ==="
echo "Completed: $(grep -c '^\- \[x\]' .kiro/specs/map-scheduling-interface/tasks.md)"
echo "Remaining: $(grep -c '^\- \[ \]' .kiro/specs/map-scheduling-interface/tasks.md)"

# 2. Start overnight run in background
echo "=== Starting Overnight Run ==="
nohup ./scripts/ralph-overnight.sh map-scheduling-interface 100 > /tmp/ralph-run.log 2>&1 &
echo "Started with PID: $!"

# 3. Show how to monitor
echo "=== To Monitor ==="
echo "tail -f /tmp/ralph-run.log"
echo "tail -f .kiro/specs/map-scheduling-interface/activity.md"

# 4. Go to sleep!
echo "=== Good night! ==="
```

---

## Related Documentation

- `OVERNIGHT-RALPH-WIGGUM.md` - Design and architecture
- `RALPH-WIGGUM-PLANNING.md` - Planning and decisions
- `Ralph_Wiggum_Guide.md` - Original methodology
- `.kiro/steering/ralph-loop-patterns.md` - Behavior rules
- `.kiro/prompts/ralph-next-overnight.md` - Overnight prompt
