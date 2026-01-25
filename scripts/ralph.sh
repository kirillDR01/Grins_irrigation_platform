#!/bin/bash
# Ralph Wiggum Loop - Fresh Context Wrapper
# 
# This script runs the Ralph Wiggum loop with fresh context for each iteration.
# Use this when you want to avoid context bloat during long-running executions.
#
# Usage: ./scripts/ralph.sh <spec-name> [max-iterations]
# Example: ./scripts/ralph.sh admin-dashboard 20
#
# Note: This requires kiro-cli to be installed and authenticated.
# If kiro-cli is not available, use the @ralph-loop prompt directly in Kiro.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Arguments
SPEC_NAME=$1
MAX_ITERATIONS=${2:-20}

# Validate arguments
if [ -z "$SPEC_NAME" ]; then
  echo -e "${RED}Error: Spec name required${NC}"
  echo ""
  echo "Usage: $0 <spec-name> [max-iterations]"
  echo ""
  echo "Examples:"
  echo "  $0 admin-dashboard        # Run with default 20 iterations"
  echo "  $0 admin-dashboard 50     # Run with 50 iterations max"
  echo "  $0 field-operations 10    # Run field-operations with 10 iterations"
  echo ""
  echo "Available specs:"
  ls -1 .kiro/specs/ 2>/dev/null || echo "  (no specs found)"
  exit 1
fi

# Validate spec exists
SPEC_DIR=".kiro/specs/$SPEC_NAME"
if [ ! -d "$SPEC_DIR" ]; then
  echo -e "${RED}Error: Spec not found at $SPEC_DIR${NC}"
  echo ""
  echo "Available specs:"
  ls -1 .kiro/specs/ 2>/dev/null || echo "  (no specs found)"
  exit 1
fi

# Validate tasks.md exists
if [ ! -f "$SPEC_DIR/tasks.md" ]; then
  echo -e "${RED}Error: tasks.md not found in $SPEC_DIR${NC}"
  exit 1
fi

# Check if kiro-cli is available
if ! command -v kiro-cli &> /dev/null; then
  echo -e "${YELLOW}Warning: kiro-cli not found${NC}"
  echo ""
  echo "This script requires kiro-cli for fresh context iterations."
  echo "Alternative: Use @ralph-loop $SPEC_NAME directly in Kiro IDE."
  echo ""
  echo "To install kiro-cli:"
  echo "  curl -fsSL https://cli.kiro.dev/install | bash"
  echo "  kiro-cli login"
  exit 1
fi

# Header
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔄 Ralph Wiggum Loop - Fresh Context Mode${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📁 Spec: ${GREEN}$SPEC_NAME${NC}"
echo -e "🔢 Max iterations: ${GREEN}$MAX_ITERATIONS${NC}"
echo -e "📄 Tasks file: ${GREEN}$SPEC_DIR/tasks.md${NC}"
echo ""

# Count tasks
TOTAL_TASKS=$(grep -c "^- \[" "$SPEC_DIR/tasks.md" 2>/dev/null || echo "0")
COMPLETED_TASKS=$(grep -c "^- \[x\]" "$SPEC_DIR/tasks.md" 2>/dev/null || echo "0")
echo -e "📊 Progress: ${GREEN}$COMPLETED_TASKS${NC} / ${TOTAL_TASKS} tasks complete"
echo ""

# Confirm before starting
read -p "Start Ralph Wiggum loop? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Aborted.${NC}"
  exit 0
fi

echo ""
echo -e "${BLUE}Starting loop...${NC}"
echo ""

# Main loop
for ((i=1; i<=$MAX_ITERATIONS; i++)); do
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}🔁 Iteration $i of $MAX_ITERATIONS${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  
  # Run Kiro with the ralph-next prompt (single task per iteration)
  # This gives fresh context for each task
  result=$(kiro-cli "@ralph-next $SPEC_NAME" 2>&1) || true
  
  echo "$result"
  
  # Check for completion signals
  if [[ "$result" == *"LOOP COMPLETE"* ]]; then
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ All tasks complete after $i iterations!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
  fi
  
  if [[ "$result" == *"CHECKPOINT PASSED"* ]]; then
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}✓ Checkpoint passed, continuing execution...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    # Continue to next iteration (do not exit)
  fi
  
  if [[ "$result" == *"USER INPUT REQUIRED"* ]]; then
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❓ User input required after $i iterations.${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Check activity.md for details on the issue."
    echo "After resolving, run again to continue:"
    echo "  ./scripts/ralph.sh $SPEC_NAME $MAX_ITERATIONS"
    exit 1
  fi
  
  # Brief pause between iterations
  sleep 2
done

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  Reached max iterations ($MAX_ITERATIONS)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Run again to continue or increase max iterations:"
echo "  ./scripts/ralph.sh $SPEC_NAME 50"
exit 1
