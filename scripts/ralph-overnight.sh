#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Ralph Wiggum Overnight Mode - Fully Autonomous Execution
# ═══════════════════════════════════════════════════════════════════════════════
#
# This script runs the Ralph Wiggum loop in fully autonomous overnight mode.
# It handles:
#   - Pre-flight: Auto-start servers (backend, frontend, database)
#   - Task loop: Execute tasks with fresh context per iteration
#   - Failure handling: Retry 3x, then skip and continue
#   - Post-flight: Stop servers, generate report, git commit
#
# Usage: ./scripts/ralph-overnight.sh <spec-name> [max-iterations]
# Example: ./scripts/ralph-overnight.sh map-scheduling-interface 100
#
# Requirements:
#   - kiro-cli installed and authenticated
#   - Docker (for PostgreSQL) or local PostgreSQL running
#   - Node.js and npm for frontend
#   - Python with uv for backend
#
# ═══════════════════════════════════════════════════════════════════════════════

set -o pipefail  # Don't use set -e, we handle errors ourselves

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

SPEC_NAME=$1
MAX_ITERATIONS=${2:-100}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="/tmp/ralph-overnight"
BACKEND_PORT=8000
FRONTEND_PORT=5173
HEALTH_CHECK_TIMEOUT=60
ITERATION_PAUSE=2
TASK_TIMEOUT=600  # 10 minutes max per task
STAGNATION_THRESHOLD=5  # Stop if same result 5 times in a row
MAX_LOG_SIZE_MB=50  # Max log file size before rotation

# Stagnation tracking
declare -a RECENT_RESULTS=()
STAGNATION_COUNT=0

# Source environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a  # Auto-export all variables
  source "$PROJECT_ROOT/.env"
  set +a
fi

# Set PYTHONPATH to include src directory for proper module resolution
export PYTHONPATH="$PROJECT_ROOT/src:${PYTHONPATH:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Timestamps
START_TIME=$(date +%s)
START_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ═══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════

log_info() {
  echo -e "${BLUE}[INFO]${NC} $(date '+%H:%M:%S') $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $(date '+%H:%M:%S') $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $(date '+%H:%M:%S') $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $(date '+%H:%M:%S') $1"
}

log_header() {
  echo ""
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}$1${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
  echo ""
}

# Check if a port is in use
port_in_use() {
  lsof -i :$1 > /dev/null 2>&1
}

# Wait for a service to be ready
wait_for_service() {
  local url=$1
  local name=$2
  local timeout=${3:-$HEALTH_CHECK_TIMEOUT}
  
  log_info "Waiting for $name to be ready..."
  for ((i=1; i<=timeout; i++)); do
    if curl -s "$url" > /dev/null 2>&1; then
      log_success "$name is ready!"
      return 0
    fi
    sleep 1
  done
  log_error "$name failed to start within ${timeout}s"
  return 1
}

# Count tasks in a spec
count_tasks() {
  local spec_dir=$1
  local pattern=$2
  grep -c "$pattern" "$spec_dir/tasks.md" 2>/dev/null || echo "0"
}

# Rotate log file if it exceeds max size
rotate_log_if_needed() {
  local log_file=$1
  local max_size_bytes=$((MAX_LOG_SIZE_MB * 1024 * 1024))
  
  if [ -f "$log_file" ]; then
    local current_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")
    if [ "$current_size" -gt "$max_size_bytes" ]; then
      log_info "Rotating log file: $log_file (${current_size} bytes)"
      mv "$log_file" "${log_file}.$(date +%Y%m%d_%H%M%S).bak"
      # Keep only last 3 backup files
      ls -t "${log_file}".*.bak 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true
    fi
  fi
}

# Run command with timeout
run_with_timeout() {
  local timeout_seconds=$1
  shift
  local cmd="$@"
  
  # Use timeout command if available (GNU coreutils)
  if command -v timeout &> /dev/null; then
    timeout "$timeout_seconds" bash -c "$cmd"
    return $?
  fi
  
  # Fallback: use background process with manual timeout
  bash -c "$cmd" &
  local pid=$!
  local count=0
  
  while [ $count -lt $timeout_seconds ]; do
    if ! kill -0 $pid 2>/dev/null; then
      wait $pid
      return $?
    fi
    sleep 1
    ((count++))
  done
  
  # Timeout reached, kill the process
  kill -9 $pid 2>/dev/null || true
  wait $pid 2>/dev/null || true
  log_warning "Command timed out after ${timeout_seconds}s"
  return 124  # Standard timeout exit code
}

# Track result for stagnation detection
track_result() {
  local result=$1
  
  # Add to recent results array
  RECENT_RESULTS+=("$result")
  
  # Keep only last STAGNATION_THRESHOLD results
  if [ ${#RECENT_RESULTS[@]} -gt $STAGNATION_THRESHOLD ]; then
    RECENT_RESULTS=("${RECENT_RESULTS[@]:1}")
  fi
  
  # Check for stagnation (all recent results are the same)
  if [ ${#RECENT_RESULTS[@]} -ge $STAGNATION_THRESHOLD ]; then
    local first_result="${RECENT_RESULTS[0]}"
    local all_same=true
    
    for r in "${RECENT_RESULTS[@]}"; do
      if [ "$r" != "$first_result" ]; then
        all_same=false
        break
      fi
    done
    
    if [ "$all_same" = true ]; then
      return 1  # Stagnation detected
    fi
  fi
  
  return 0  # No stagnation
}

# Check if database migrations are needed and run them
run_database_migrations() {
  log_info "Checking database migrations..."
  
  cd "$PROJECT_ROOT"
  
  # Check if alembic is configured
  if [ ! -f "alembic.ini" ]; then
    log_warning "alembic.ini not found, skipping migrations"
    return 0
  fi
  
  # Run migrations
  if uv run alembic upgrade head 2>&1 | tee -a "$LOG_DIR/migrations.log"; then
    log_success "Database migrations complete"
    return 0
  else
    log_warning "Database migrations failed - check $LOG_DIR/migrations.log"
    return 1
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════

validate_arguments() {
  if [ -z "$SPEC_NAME" ]; then
    log_error "Spec name required"
    echo ""
    echo "Usage: $0 <spec-name> [max-iterations]"
    echo ""
    echo "Examples:"
    echo "  $0 map-scheduling-interface        # Run with default 100 iterations"
    echo "  $0 admin-dashboard 50              # Run with 50 iterations max"
    echo ""
    echo "Available specs:"
    ls -1 "$PROJECT_ROOT/.kiro/specs/" 2>/dev/null || echo "  (no specs found)"
    exit 1
  fi

  SPEC_DIR="$PROJECT_ROOT/.kiro/specs/$SPEC_NAME"
  if [ ! -d "$SPEC_DIR" ]; then
    log_error "Spec not found at $SPEC_DIR"
    echo ""
    echo "Available specs:"
    ls -1 "$PROJECT_ROOT/.kiro/specs/" 2>/dev/null || echo "  (no specs found)"
    exit 1
  fi

  if [ ! -f "$SPEC_DIR/tasks.md" ]; then
    log_error "tasks.md not found in $SPEC_DIR"
    exit 1
  fi
}

validate_dependencies() {
  log_info "Checking dependencies..."
  
  # Check for kiro-cli
  if ! command -v kiro-cli &> /dev/null; then
    log_warning "kiro-cli not found - will use Kiro IDE prompts instead"
    log_info "To install kiro-cli: curl -fsSL https://cli.kiro.dev/install | bash"
    USE_KIRO_CLI=false
  else
    USE_KIRO_CLI=true
    log_success "kiro-cli found"
  fi
  
  # Check for uv
  if ! command -v uv &> /dev/null; then
    log_error "uv not found - required for backend"
    exit 1
  fi
  log_success "uv found"
  
  # Check for npm
  if ! command -v npm &> /dev/null; then
    log_error "npm not found - required for frontend"
    exit 1
  fi
  log_success "npm found"
  
  # Check for docker (optional)
  if command -v docker &> /dev/null; then
    log_success "docker found"
    HAS_DOCKER=true
  else
    log_warning "docker not found - assuming local PostgreSQL"
    HAS_DOCKER=false
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Pre-Flight: Start Services
# ═══════════════════════════════════════════════════════════════════════════════

preflight() {
  log_header "🚀 PRE-FLIGHT: Starting Services"
  
  # Create log directory
  mkdir -p "$LOG_DIR"
  
  # Rotate logs if they're too large from previous runs
  rotate_log_if_needed "$LOG_DIR/backend.log"
  rotate_log_if_needed "$LOG_DIR/frontend.log"
  rotate_log_if_needed "$LOG_DIR/migrations.log"
  
  # Start database (if using Docker)
  if [ "$HAS_DOCKER" = true ]; then
    log_info "Starting PostgreSQL via Docker..."
    cd "$PROJECT_ROOT"
    docker-compose up -d db 2>/dev/null || true
    sleep 5
  fi
  
  # Run database migrations
  run_database_migrations || log_warning "Continuing despite migration issues..."
  
  # Start backend
  start_backend
  
  # Start frontend
  start_frontend
  
  # Verify all services
  verify_services
  
  log_success "All services started successfully!"
}

start_backend() {
  log_info "Starting backend server..."
  
  # Check if already running
  if port_in_use $BACKEND_PORT; then
    log_warning "Port $BACKEND_PORT already in use - assuming backend is running"
    return 0
  fi
  
  cd "$PROJECT_ROOT"
  nohup uv run uvicorn grins_platform.main:app --host 0.0.0.0 --port $BACKEND_PORT > "$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  echo $BACKEND_PID > "$LOG_DIR/backend.pid"
  
  log_info "Backend started with PID $BACKEND_PID"
  
  # Wait for backend to be ready
  wait_for_service "http://localhost:$BACKEND_PORT/health" "Backend" || {
    log_error "Backend failed to start. Check $LOG_DIR/backend.log"
    cat "$LOG_DIR/backend.log" | tail -20
    exit 1
  }
}

start_frontend() {
  log_info "Starting frontend server..."
  
  # Check if already running
  if port_in_use $FRONTEND_PORT; then
    log_warning "Port $FRONTEND_PORT already in use - assuming frontend is running"
    return 0
  fi
  
  cd "$PROJECT_ROOT/frontend"
  nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
  FRONTEND_PID=$!
  echo $FRONTEND_PID > "$LOG_DIR/frontend.pid"
  
  log_info "Frontend started with PID $FRONTEND_PID"
  
  # Wait for frontend to be ready
  wait_for_service "http://localhost:$FRONTEND_PORT" "Frontend" || {
    log_error "Frontend failed to start. Check $LOG_DIR/frontend.log"
    cat "$LOG_DIR/frontend.log" | tail -20
    exit 1
  }
}

verify_services() {
  log_info "Verifying all services..."
  
  local all_ok=true
  
  # Check backend
  if curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    log_success "Backend: ✅ Running"
  else
    log_error "Backend: ❌ Not responding"
    all_ok=false
  fi
  
  # Check frontend
  if curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    log_success "Frontend: ✅ Running"
  else
    log_error "Frontend: ❌ Not responding"
    all_ok=false
  fi
  
  if [ "$all_ok" = false ]; then
    log_error "Some services failed to start. Aborting."
    cleanup_services
    exit 1
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main Loop: Execute Tasks
# ═══════════════════════════════════════════════════════════════════════════════

main_loop() {
  log_header "🔄 MAIN LOOP: Executing Tasks"
  
  cd "$PROJECT_ROOT"
  
  # Show initial status
  local total_tasks=$(count_tasks "$SPEC_DIR" "^- \[")
  local completed_tasks=$(count_tasks "$SPEC_DIR" "^- \[x\]")
  local remaining_tasks=$((total_tasks - completed_tasks))
  
  log_info "Spec: $SPEC_NAME"
  log_info "Total tasks: $total_tasks"
  log_info "Completed: $completed_tasks"
  log_info "Remaining: $remaining_tasks"
  log_info "Max iterations: $MAX_ITERATIONS"
  log_info "Task timeout: ${TASK_TIMEOUT}s"
  log_info "Stagnation threshold: $STAGNATION_THRESHOLD consecutive same results"
  echo ""
  
  # Initialize counters
  local tasks_completed=0
  local tasks_skipped=0
  local tasks_failed=0
  
  # Main execution loop
  for ((i=1; i<=$MAX_ITERATIONS; i++)); do
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🔁 Iteration $i of $MAX_ITERATIONS${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Rotate logs periodically (every 10 iterations)
    if [ $((i % 10)) -eq 0 ]; then
      rotate_log_if_needed "$LOG_DIR/backend.log"
      rotate_log_if_needed "$LOG_DIR/frontend.log"
    fi
    
    # Check if servers are still running
    check_server_health
    
    # Execute single task
    local result
    if [ "$USE_KIRO_CLI" = true ]; then
      result=$(execute_task_kiro_cli) || true
    else
      log_error "kiro-cli not available. Please run manually in Kiro IDE:"
      log_info "@ralph-next-overnight $SPEC_NAME"
      exit 1
    fi
    
    echo "$result"
    
    # Extract the signal from the result (last line containing a known signal)
    local signal=""
    if [[ "$result" == *"ALL_TASKS_COMPLETE"* ]]; then
      signal="ALL_TASKS_COMPLETE"
    elif [[ "$result" == *"CHECKPOINT_FAILED"* ]]; then
      signal="CHECKPOINT_FAILED"
    elif [[ "$result" == *"CHECKPOINT_PASSED"* ]]; then
      signal="CHECKPOINT_PASSED"
    elif [[ "$result" == *"TASK_COMPLETE"* ]]; then
      signal="TASK_COMPLETE"
    elif [[ "$result" == *"TASK_SKIPPED"* ]]; then
      signal="TASK_SKIPPED"
    else
      signal="UNKNOWN"
    fi
    
    # Track result for stagnation detection
    if ! track_result "$signal"; then
      log_error "Stagnation detected! Same result '$signal' for $STAGNATION_THRESHOLD consecutive iterations."
      log_error "This usually indicates the loop is stuck. Stopping to prevent infinite loop."
      log_info "Review activity.md and tasks.md to understand what's happening."
      ((tasks_failed++))
      break
    fi
    
    # Parse result and update counters
    if [[ "$signal" == "ALL_TASKS_COMPLETE" ]]; then
      log_success "All tasks complete!"
      break
    elif [[ "$signal" == "CHECKPOINT_FAILED" ]]; then
      log_error "Checkpoint failed! Quality checks did not pass after 5 fix attempts."
      log_error "Review activity.md for details on what failed."
      log_info "The loop has stopped to prevent proceeding with broken code."
      ((tasks_failed++))
      break
    elif [[ "$signal" == "CHECKPOINT_PASSED" ]]; then
      log_success "Checkpoint passed - all quality checks passed!"
      ((tasks_completed++))
    elif [[ "$signal" == "TASK_COMPLETE" ]]; then
      ((tasks_completed++))
      log_success "Task completed successfully"
    elif [[ "$signal" == "TASK_SKIPPED" ]]; then
      ((tasks_skipped++))
      log_warning "Task skipped"
    else
      # Unknown result, continue anyway but warn
      log_warning "Unknown result signal: '$signal', continuing..."
    fi
    
    # Brief pause between iterations
    sleep $ITERATION_PAUSE
  done
  
  # Store results for report
  TASKS_COMPLETED=$tasks_completed
  TASKS_SKIPPED=$tasks_skipped
  TASKS_FAILED=$tasks_failed
}

execute_task_kiro_cli() {
  # Run kiro-cli in non-interactive mode with trusted tools
  # Correct syntax: kiro-cli chat --no-interactive --trust-all-tools "message"
  
  local prompt_file="$PROJECT_ROOT/.kiro/prompts/ralph-next-overnight.md"
  
  if [ -f "$prompt_file" ]; then
    # Pass the instruction to kiro-cli in non-interactive mode with timeout
    local kiro_cmd="kiro-cli chat --no-interactive --trust-all-tools \"You are executing ONE task in overnight mode for spec '$SPEC_NAME'. 

Read .kiro/specs/$SPEC_NAME/tasks.md and find the first incomplete task (- [ ]).
Execute it following the overnight mode rules from .kiro/prompts/ralph-next-overnight.md.

CRITICAL RULES:
- NEVER ask for user input - make autonomous decisions
- NEVER wait for confirmation - proceed with best judgment  
- Run quality checks after implementation
- Mark task complete using taskStatus tool

CHECKPOINT RULES (CRITICAL):
- If task name contains 'Checkpoint', it is a QUALITY GATE
- ALL quality checks (ruff, mypy, pyright, pytest) MUST pass
- If checks fail: FIX the issues, retry up to 5 times
- Checkpoints are NEVER skipped - they block until all checks pass
- If checkpoint still fails after 5 fix attempts, output CHECKPOINT_FAILED

OUTPUT exactly ONE of these signals at the end:
- TASK_COMPLETE (if regular task succeeded)
- TASK_SKIPPED: {reason} (if regular task failed after retries)
- ALL_TASKS_COMPLETE (if no more tasks)
- CHECKPOINT_PASSED: {name} (if checkpoint validation passed)
- CHECKPOINT_FAILED: {name} (if checkpoint failed after 5 fix attempts - STOPS LOOP)

Execute now.\""

    # Run with timeout
    local result
    result=$(run_with_timeout $TASK_TIMEOUT "$kiro_cmd" 2>&1) || {
      local exit_code=$?
      if [ $exit_code -eq 124 ]; then
        log_warning "kiro-cli timed out after ${TASK_TIMEOUT}s"
        echo "TASK_SKIPPED: timeout_after_${TASK_TIMEOUT}s"
        return 0
      fi
      # Other error, return the result anyway
      echo "$result"
      return 0
    }
    
    echo "$result"
  else
    log_error "Prompt file not found: $prompt_file"
    echo "TASK_SKIPPED: prompt_file_missing"
  fi
}

check_server_health() {
  # Quick health check - restart if needed
  if ! curl -s "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    log_warning "Backend not responding, attempting restart..."
    start_backend
  fi
  
  if ! curl -s "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    log_warning "Frontend not responding, attempting restart..."
    start_frontend
  fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Post-Flight: Cleanup and Report
# ═══════════════════════════════════════════════════════════════════════════════

postflight() {
  log_header "🏁 POST-FLIGHT: Cleanup and Report"
  
  # Calculate duration
  END_TIME=$(date +%s)
  DURATION=$((END_TIME - START_TIME))
  DURATION_FORMATTED=$(printf '%02d:%02d:%02d' $((DURATION/3600)) $((DURATION%3600/60)) $((DURATION%60)))
  
  # Generate report
  generate_report
  
  # Git commit all changes
  git_commit_changes
  
  # Cleanup services
  cleanup_services
  
  log_success "Overnight run complete!"
}

generate_report() {
  log_info "Generating final report..."
  
  local final_completed=$(count_tasks "$SPEC_DIR" "^- \[x\]")
  local final_total=$(count_tasks "$SPEC_DIR" "^- \[")
  local final_skipped=$(count_tasks "$SPEC_DIR" "^- \[S\]")
  
  echo ""
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
  echo -e "${CYAN}                    OVERNIGHT RUN REPORT                           ${NC}"
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
  echo ""
  echo -e "  Spec:           ${GREEN}$SPEC_NAME${NC}"
  echo -e "  Started:        $START_TIMESTAMP"
  echo -e "  Ended:          $(date '+%Y-%m-%d %H:%M:%S')"
  echo -e "  Duration:       $DURATION_FORMATTED"
  echo ""
  echo -e "  ${GREEN}Tasks Completed:${NC}  $final_completed / $final_total"
  echo -e "  ${YELLOW}Tasks Skipped:${NC}    $final_skipped"
  echo -e "  ${RED}Tasks Failed:${NC}     ${TASKS_FAILED:-0}"
  echo ""
  echo -e "  Configuration:"
  echo -e "    Task Timeout:       ${TASK_TIMEOUT}s"
  echo -e "    Stagnation Limit:   $STAGNATION_THRESHOLD consecutive same results"
  echo -e "    Max Log Size:       ${MAX_LOG_SIZE_MB}MB"
  echo ""
  echo -e "  Logs:"
  echo -e "    Activity Log:   $SPEC_DIR/activity.md"
  echo -e "    Backend Log:    $LOG_DIR/backend.log"
  echo -e "    Frontend Log:   $LOG_DIR/frontend.log"
  echo -e "    Migrations Log: $LOG_DIR/migrations.log"
  echo ""
  echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
  echo ""
  
  # Save report to file
  cat > "$LOG_DIR/report.txt" << EOF
Ralph Wiggum Overnight Run Report
=================================

Spec: $SPEC_NAME
Started: $START_TIMESTAMP
Ended: $(date '+%Y-%m-%d %H:%M:%S')
Duration: $DURATION_FORMATTED

Results:
- Tasks Completed: $final_completed / $final_total
- Tasks Skipped: $final_skipped
- Tasks Failed: ${TASKS_FAILED:-0}

Configuration:
- Task Timeout: ${TASK_TIMEOUT}s
- Stagnation Limit: $STAGNATION_THRESHOLD consecutive same results
- Max Log Size: ${MAX_LOG_SIZE_MB}MB

Logs:
- Activity: $SPEC_DIR/activity.md
- Backend: $LOG_DIR/backend.log
- Frontend: $LOG_DIR/frontend.log
- Migrations: $LOG_DIR/migrations.log
EOF
}

git_commit_changes() {
  log_info "Committing changes to git..."
  
  cd "$PROJECT_ROOT"
  
  # Check if there are changes to commit
  if git diff --quiet && git diff --staged --quiet; then
    log_info "No changes to commit"
    return 0
  fi
  
  # Stage all changes
  git add -A
  
  # Commit with descriptive message
  local commit_msg="Ralph Wiggum overnight run: $SPEC_NAME - $(date '+%Y-%m-%d')"
  git commit -m "$commit_msg" || {
    log_warning "Git commit failed - changes may need manual review"
    return 0
  }
  
  log_success "Changes committed: $commit_msg"
}

cleanup_services() {
  log_info "Cleaning up services..."
  
  # Stop backend if we started it
  if [ -f "$LOG_DIR/backend.pid" ]; then
    local pid=$(cat "$LOG_DIR/backend.pid")
    if kill -0 $pid 2>/dev/null; then
      log_info "Stopping backend (PID $pid)..."
      kill $pid 2>/dev/null || true
    fi
    rm -f "$LOG_DIR/backend.pid"
  fi
  
  # Stop frontend if we started it
  if [ -f "$LOG_DIR/frontend.pid" ]; then
    local pid=$(cat "$LOG_DIR/frontend.pid")
    if kill -0 $pid 2>/dev/null; then
      log_info "Stopping frontend (PID $pid)..."
      kill $pid 2>/dev/null || true
    fi
    rm -f "$LOG_DIR/frontend.pid"
  fi
  
  log_success "Services cleaned up"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Signal Handlers
# ═══════════════════════════════════════════════════════════════════════════════

cleanup_on_exit() {
  log_warning "Received interrupt signal, cleaning up..."
  cleanup_services
  exit 1
}

trap cleanup_on_exit SIGINT SIGTERM

# ═══════════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

main() {
  log_header "🌙 Ralph Wiggum Overnight Mode"
  
  # Validate
  validate_arguments
  validate_dependencies
  
  # Pre-flight
  preflight
  
  # Main loop
  main_loop
  
  # Post-flight
  postflight
}

# Run main
main
