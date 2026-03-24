# End-to-End Application Testing with agent-browser

This steering document provides the complete E2E testing methodology using the Vercel Agent Browser CLI. It is loaded automatically when working on E2E test files.

## Pre-flight Check

### 1. Platform Check

agent-browser requires Linux, WSL, or macOS. Check with `uname -s`. If unsupported, stop execution.

### 2. Frontend Check

Verify the app has a browser-accessible frontend (package.json with dev/start script, frontend framework files, etc.). If no frontend is detected, stop.

### 3. agent-browser Installation

```bash
agent-browser --version
```

If not found, install:
```bash
npm install -g agent-browser
agent-browser install --with-deps
```

The `--with-deps` flag installs system-level Chromium dependencies on Linux/WSL. On macOS it is harmless.

## Phase 1: Parallel Research

Launch three sub-agents simultaneously:

### Sub-agent 1: Application Structure & User Journeys
Research: how to start the app, authentication/login, every user-facing route/page, every user journey (complete flows with steps, interactions, expected outcomes), key UI components.

### Sub-agent 2: Database Schema & Data Flows
Research: database type and connection (from .env.example, NOT .env), full schema, data flows per user action, validation queries.

### Sub-agent 3: Bug Hunting
Analyze: logic errors, UI/UX issues, data integrity risks, security concerns. Return prioritized list with file paths and line numbers.

Wait for all three to complete before proceeding.

## Phase 2: Start the Application

1. Install dependencies if needed
2. Start the dev server in the background
3. Wait for server ready
4. `agent-browser open <url>` and confirm it loads
5. `agent-browser screenshot e2e-screenshots/00-initial-load.png`

## Phase 3: Browser Testing Workflow

Use the Vercel Agent Browser CLI for all browser interaction:

```bash
agent-browser open <url>              # Navigate to a page
agent-browser snapshot -i             # Get interactive elements with refs (@e1, @e2...)
agent-browser click @eN               # Click element by ref
agent-browser fill @eN "text"         # Clear field and type
agent-browser select @eN "option"     # Select dropdown option
agent-browser press Enter             # Press a key
agent-browser screenshot <path>       # Save screenshot
agent-browser screenshot --annotate   # Screenshot with numbered element labels
agent-browser set viewport W H        # Set viewport size
agent-browser wait --load networkidle # Wait for page to settle
agent-browser console                 # Check for JS errors
agent-browser errors                  # Check for uncaught exceptions
agent-browser get text @eN            # Get element text
agent-browser get url                 # Get current URL
agent-browser close                   # End session
```

CRITICAL: Refs become invalid after navigation or DOM changes. Always re-snapshot after page navigation, form submissions, or dynamic content updates.

For each step in a user journey:
1. Snapshot to get current refs
2. Perform the interaction
3. Wait for the page to settle
4. Take a screenshot — save to `e2e-screenshots/` organized by journey
5. Analyze the screenshot for visual correctness, UX issues, broken layouts
6. Check `agent-browser console` and `agent-browser errors` periodically

## Phase 4: Database Validation

After any interaction that modifies data:
1. Query the database to verify records
   - Postgres: `psql "$DATABASE_URL" -c "SELECT ..."`
   - SQLite: `sqlite3 db.sqlite "SELECT ..."`
2. Verify: records created/updated/deleted as expected, values match UI input, relationships correct, no orphaned/duplicate records

## Phase 5: Issue Handling

When an issue is found:
1. Document it: expected vs actual, screenshot path, DB query results
2. Fix the code directly
3. Re-run the failing step to verify
4. Take a new screenshot confirming the fix

## Phase 6: Responsive Testing

Revisit key pages at these viewports:
- Mobile: `agent-browser set viewport 375 812`
- Tablet: `agent-browser set viewport 768 1024`
- Desktop: `agent-browser set viewport 1440 900`

Screenshot every major page at each viewport. Check for layout issues, overflow, broken alignment, touch target sizes.

## Phase 7: Cleanup & Report

1. Stop the dev server background process
2. `agent-browser close`
3. Present summary:

```
## E2E Testing Complete

**Journeys Tested:** [count]
**Screenshots Captured:** [count]
**Issues Found:** [count] ([count] fixed, [count] remaining)

### Issues Fixed During Testing
- [Description] — [file:line]

### Remaining Issues
- [Description] — [severity: high/medium/low] — [file:line]

### Screenshots
All saved to: `e2e-screenshots/`
```

## Grins Platform Specifics

- Backend: FastAPI at `http://localhost:8000`
- Frontend: Vite dev server at `http://localhost:5173`
- Database: PostgreSQL (connection via `DATABASE_URL` env var)
- Auth: JWT-based, login at `/login`
- Key routes to test: `/dashboard`, `/customers`, `/leads`, `/jobs`, `/schedule`, `/invoices`, `/sales`, `/accounting`, `/marketing`
- Service agreement flow is OFF-LIMITS — verify it works but do NOT modify it
- Use `data-testid` attributes for reliable element selection where available
- All screenshots go to `e2e-screenshots/` organized by feature
