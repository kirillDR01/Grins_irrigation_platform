# Validate Visual (Internal)

**Purpose:** Enforce visual validation for frontend UI tasks using agent-browser.

**Usage:** Called internally by ralph-loop for frontend tasks that modify UI components.

---

## Parameters

- `spec_name`: Name of the spec (e.g., "map-scheduling-interface")
- `task_id`: Task ID (e.g., "2.1")
- `validation_commands`: agent-browser commands from tasks.md

---

## Instructions

You are validating that frontend UI changes work correctly in the browser.

### Step 1: Determine if Visual Validation Required

Visual validation is REQUIRED if:
- Task modifies `frontend/src/` files
- Task creates or modifies UI components
- Task changes styling or layout
- Task adds interactive features

Visual validation is OPTIONAL if:
- Task only modifies types or utilities
- Task only modifies tests
- Task only modifies configuration

### Step 2: Ensure Dev Server Running

1. Check if frontend dev server is running:
   ```bash
   curl -s http://localhost:5173 > /dev/null && echo "Running" || echo "Not running"
   ```

2. If not running, start it:
   ```bash
   cd frontend && npm run dev &
   sleep 5
   ```

3. Verify server started:
   ```bash
   curl -s http://localhost:5173 > /dev/null
   ```

4. If server fails to start:
   - Check for port conflicts
   - Check for npm errors
   - Output ERROR and stop

### Step 3: Run Validation Commands

Execute the validation commands from tasks.md:

**Example commands:**
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle
agent-browser snapshot -i
agent-browser is visible "[data-testid='map-view']"
agent-browser is visible "[data-testid='schedule-list']"
```

**Parse each command output:**
- If contains "visible" or "exists" → PASS
- If contains "not found" or "error" → FAIL

### Step 4: Take Screenshot

Save screenshot for documentation:

```bash
agent-browser screenshot screenshots/{spec-name}/{task-id}.png
```

Create screenshots directory if it doesn't exist:
```bash
mkdir -p screenshots/{spec-name}
```

### Step 5: Check Console Errors

Use agent-browser to check for console errors:

```bash
agent-browser eval "console.error.toString()"
```

**Parse output:**
- If no errors or empty → PASS
- If errors present → WARN (not critical, but note in output)

### Step 6: Output Result

**On SUCCESS:**
```
✅ Visual Validation PASSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_id}
URL: http://localhost:5173/...
Screenshot: screenshots/{spec-name}/{task-id}.png

Validation Results:
  ✅ Page loads successfully
  ✅ [data-testid='map-view'] is visible
  ✅ [data-testid='schedule-list'] is visible
  ✅ No console errors

Status: READY TO MARK COMPLETE
```

**On FAILURE:**
```
❌ Visual Validation FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task: {task_id}
URL: http://localhost:5173/...
Screenshot: screenshots/{spec-name}/{task-id}.png

Validation Results:
  ✅ Page loads successfully
  ❌ [data-testid='map-view'] not found
  ✅ [data-testid='schedule-list'] is visible
  ⚠️  Console errors detected

Console Errors:
{paste console error messages}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next Steps:
  1. Fix the missing element or console errors
  2. Re-run visual validation
  3. This counts as a quality check failure (retry logic applies)
```

---

## Validation Command Patterns

### Common Patterns from tasks.md

**Pattern 1: Check element visibility**
```bash
agent-browser is visible "[data-testid='element-id']"
```

**Pattern 2: Check element text**
```bash
agent-browser get text "[data-testid='element-id']"
```

**Pattern 3: Check element count**
```bash
agent-browser get count "[data-testid='list-item']"
```

**Pattern 4: Interact and verify**
```bash
agent-browser click "[data-testid='button']"
agent-browser wait "[data-testid='result']"
agent-browser is visible "[data-testid='result']"
```

### Parsing agent-browser Output

**Success indicators:**
- "true" (for is visible)
- "element found"
- "visible: true"
- Text content returned (for get text)
- Number returned (for get count)

**Failure indicators:**
- "false" (for is visible)
- "element not found"
- "visible: false"
- "timeout"
- "error"

---

## Integration with Ralph-Loop

Ralph-loop should call this after @validate-quality for frontend tasks:

```markdown
### Step 5: Validate Work (Frontend Tasks)

1. Call @validate-quality frontend {retry-attempt}
2. If PASSED, call @validate-visual:
   @validate-visual {spec-name} {task-id} "{validation-commands}"
3. If visual validation FAILED:
   - Treat as quality check failure
   - Retry up to 3 times
   - After 3 failures, output USER INPUT REQUIRED
```

---

## Error Handling

### Dev Server Errors

1. **Port already in use:**
   - Try port 5174, 5175, etc.
   - Update validation URL accordingly

2. **npm run dev fails:**
   - Check for dependency errors
   - Check for syntax errors in code
   - Output ERROR and stop

3. **Server starts but page doesn't load:**
   - Check for build errors
   - Check browser console
   - Output ERROR with details

### agent-browser Errors

1. **Command timeout:**
   - Retry once with longer wait
   - If still timeout, output FAILED

2. **Element not found:**
   - Check if element exists in code
   - Check if data-testid is correct
   - Output FAILED with details

3. **Screenshot fails:**
   - Continue anyway (screenshot is nice-to-have)
   - Note in output but don't fail validation

---

## Examples

### Example 1: Map Component Validation

**Input:**
- spec_name: "map-scheduling-interface"
- task_id: "2.1"
- validation_commands: 
  ```
  agent-browser open http://localhost:5173/schedule
  agent-browser wait --load networkidle
  agent-browser is visible "[data-testid='map-view']"
  agent-browser is visible "[data-testid='map-container']"
  ```

**Process:**
1. Check dev server running
2. Execute validation commands
3. Parse results: both elements visible
4. Take screenshot
5. Check console errors: none
6. Output SUCCESS

### Example 2: Failed Validation

**Input:**
- spec_name: "map-scheduling-interface"
- task_id: "2.2"
- validation_commands:
  ```
  agent-browser open http://localhost:5173/schedule
  agent-browser is visible "[data-testid='route-list']"
  ```

**Process:**
1. Check dev server running
2. Execute validation commands
3. Parse results: element not found
4. Take screenshot (shows missing element)
5. Check console errors: "Cannot read property 'map' of undefined"
6. Output FAILED with details

---

## Safety Rules

1. **Always start dev server** - Don't assume it's running
2. **Always take screenshot** - Visual proof of state
3. **Check console errors** - Catch runtime issues
4. **Use exact data-testid** - Don't guess element selectors
5. **Fail on missing elements** - Don't mark complete if UI broken

---

## Testing

To test this prompt:

```bash
# Test 1: Validate existing component
@validate-visual map-scheduling-interface "2.1" "agent-browser open http://localhost:5173/schedule\nagent-browser is visible '[data-testid=\"schedule-page\"]'"

# Test 2: Validate with missing element (should fail)
@validate-visual map-scheduling-interface "2.2" "agent-browser is visible '[data-testid=\"nonexistent\"]'"

# Test 3: Check screenshots directory
ls -la screenshots/map-scheduling-interface/
```

---

## Known Limitations

1. **Requires agent-browser** - Must be installed and working
2. **Requires dev server** - Must be able to start frontend
3. **No cross-browser testing** - Only tests in Chromium
4. **No mobile testing** - Only tests desktop viewport
5. **No accessibility testing** - Only checks visual presence

### Future Enhancements

- Add mobile viewport testing
- Add accessibility checks (ARIA, contrast)
- Add cross-browser testing
- Add performance metrics
- Add visual regression testing
