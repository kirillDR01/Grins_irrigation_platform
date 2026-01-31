# Frontend UI Test Guide

This document provides reproducible UI tests for the Grin's Irrigation Platform admin dashboard. Tests can be run manually or automated using `agent-browser`.

## Prerequisites

Before running UI tests:

```bash
# 1. Start the database
docker-compose up -d db

# 2. Start the backend API (port 8000)
uv run uvicorn grins_platform.main:app --reload --port 8000

# 3. Start the frontend dev server (port 5173)
cd frontend && npm run dev
```

Verify services are running:
- Backend: http://localhost:8000/docs (Swagger UI)
- Frontend: http://localhost:5173

---

## Test Summary

| Area | Status | Screenshot |
|------|--------|------------|
| Layout/Navigation | ✅ PASS | `screenshots/01-dashboard-initial.png` |
| Dashboard | ✅ PASS | `screenshots/01-dashboard-initial.png` |
| Customer List | ✅ PASS | `screenshots/02-customers-list.png` |
| Customer Detail | ✅ PASS | `screenshots/03-customer-detail-fixed.png` |
| Customer Form | ✅ PASS | `screenshots/13-create-customer-form.png` |
| Job List | ✅ PASS | `screenshots/04-jobs-list.png` |
| Job Detail | ✅ PASS | `screenshots/05-job-detail.png` |
| Schedule Calendar | ✅ PASS | `screenshots/06-schedule.png` |
| Schedule List | ✅ PASS | `screenshots/07-schedule-list.png` |
| Staff List | ✅ PASS | `screenshots/08-staff.png` |
| Staff Detail | ✅ PASS | `screenshots/10-staff-detail.png` |
| Settings | ✅ PASS | `screenshots/11-settings.png` |

---

## Detailed Test Cases

### 1. Layout & Navigation

**Test:** Verify sidebar navigation renders all menu items

```bash
agent-browser open http://localhost:5173
agent-browser wait --load networkidle
agent-browser snapshot -i

# Verify navigation items
agent-browser is visible "[data-testid='nav-dashboard']"
agent-browser is visible "[data-testid='nav-customers']"
agent-browser is visible "[data-testid='nav-jobs']"
agent-browser is visible "[data-testid='nav-schedule']"
agent-browser is visible "[data-testid='nav-staff']"
agent-browser is visible "[data-testid='nav-settings']"

agent-browser screenshot screenshots/layout-nav.png
```

**Expected:** All 6 navigation items visible in sidebar

---

### 2. Dashboard Page

**Test:** Verify dashboard loads with metrics and activity

```bash
agent-browser open http://localhost:5173
agent-browser wait --load networkidle

# Verify metrics cards
agent-browser is visible "[data-testid='metrics-card']"
agent-browser is visible "[data-testid='recent-activity']"
agent-browser is visible "[data-testid='quick-actions']"

agent-browser screenshot screenshots/dashboard.png
```

**Expected:** 
- Metrics cards showing counts (customers, jobs, etc.)
- Recent activity section
- Quick action buttons

---

### 3. Customer List

**Test:** Verify customer list displays table with data

```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Verify table structure
agent-browser is visible "[data-testid='customer-table']"
agent-browser is visible "[data-testid='customer-row']"
agent-browser is visible "[data-testid='add-customer-btn']"

# Verify table headers
agent-browser get text "th" # Should include Name, Phone, Email, etc.

agent-browser screenshot screenshots/customer-list.png
```

**Expected:**
- Table with customer rows
- "Add Customer" button visible
- Columns: Name, Phone, Email, Status, Actions

---

### 4. Customer Detail

**Test:** Navigate to customer detail and verify info displays

```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Click on first customer name link
agent-browser click "[data-testid='customer-row'] a"
agent-browser wait --load networkidle

# Verify detail page elements
agent-browser is visible "[data-testid='customer-detail']"
agent-browser get text "[data-testid='customer-name']"
agent-browser get text "[data-testid='customer-phone']"

agent-browser screenshot screenshots/customer-detail.png
```

**Expected:**
- Customer name displayed
- Contact info (phone, email)
- Customer flags (priority, red flag, slow payer)
- Properties section
- Jobs history section

---

### 5. Customer Form (Create)

**Test:** Open create customer dialog and verify form fields

```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Open create dialog
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"

# Verify form fields exist
agent-browser is visible "[data-testid='first-name-input']"
agent-browser is visible "[data-testid='last-name-input']"
agent-browser is visible "[data-testid='phone-input']"
agent-browser is visible "[data-testid='email-input']"
agent-browser is visible "[data-testid='lead-source-select']"
agent-browser is visible "[data-testid='is-priority-checkbox']"
agent-browser is visible "[data-testid='sms-opt-in-checkbox']"
agent-browser is visible "[data-testid='submit-btn']"

agent-browser screenshot screenshots/customer-form.png
```

**Expected:**
- Form dialog opens
- All required fields present
- Submit button visible

---

### 6. Job List

**Test:** Verify job list displays with status badges

```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Verify table
agent-browser is visible "[data-testid='job-table']"
agent-browser is visible "[data-testid='job-row']"

# Verify status badges render
agent-browser is visible "[data-testid^='status-']"

agent-browser screenshot screenshots/job-list.png
```

**Expected:**
- Table with job rows
- Status badges with colors (requested=yellow, scheduled=purple, etc.)
- Job type column
- Customer name column

---

### 7. Job Detail

**Test:** Navigate to job detail page

```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Click on first job
agent-browser click "[data-testid='job-row'] a"
agent-browser wait --load networkidle

# Verify detail elements
agent-browser is visible "[data-testid='job-detail']"
agent-browser get text "[data-testid='job-type']"
agent-browser get text "[data-testid='job-status']"

agent-browser screenshot screenshots/job-detail.png
```

**Expected:**
- Job type displayed
- Status badge
- Customer info
- Property info
- Description
- Scheduling details

---

### 8. Schedule - Calendar View

**Test:** Verify schedule calendar renders

```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Verify calendar elements
agent-browser is visible "[data-testid='schedule-calendar']"
agent-browser is visible "[data-testid='view-toggle']"

# Check calendar navigation
agent-browser is visible "[data-testid='prev-month']"
agent-browser is visible "[data-testid='next-month']"

agent-browser screenshot screenshots/schedule-calendar.png
```

**Expected:**
- Calendar grid visible
- Month/week navigation
- View toggle (calendar/list)

---

### 9. Schedule - List View

**Test:** Toggle to list view and verify appointments

```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Toggle to list view
agent-browser click "[data-testid='view-toggle-list']"
agent-browser wait "[data-testid='appointment-list']"

# Verify list elements
agent-browser is visible "[data-testid='appointment-row']"

agent-browser screenshot screenshots/schedule-list.png
```

**Expected:**
- Appointment list table
- Date/time columns
- Staff assignment
- Job info

---

### 10. Staff List

**Test:** Verify staff list displays

```bash
agent-browser open http://localhost:5173/staff
agent-browser wait --load networkidle

# Verify table
agent-browser is visible "[data-testid='staff-table']"
agent-browser is visible "[data-testid='staff-row']"

# Verify columns
agent-browser get text "th" # Name, Role, Phone, etc.

agent-browser screenshot screenshots/staff-list.png
```

**Expected:**
- Table with staff members
- Columns: Name, Role, Phone, Email, Status

---

### 11. Staff Detail

**Test:** Navigate to staff detail page

```bash
agent-browser open http://localhost:5173/staff
agent-browser wait --load networkidle

# Click on first staff member
agent-browser click "[data-testid='staff-row'] a"
agent-browser wait --load networkidle

# Verify detail elements
agent-browser is visible "[data-testid='staff-detail']"
agent-browser get text "[data-testid='staff-name']"
agent-browser get text "[data-testid='staff-role']"
agent-browser get text "[data-testid='hourly-rate']"

agent-browser screenshot screenshots/staff-detail.png
```

**Expected:**
- Staff name displayed
- Role badge
- Contact info
- Hourly rate (formatted as currency)
- Availability section

---

### 12. Settings Page

**Test:** Verify settings page renders

```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Verify page content
agent-browser is visible "[data-testid='settings-page']"

agent-browser screenshot screenshots/settings.png
```

**Expected:**
- Settings page placeholder content

---

## Automated Test Script

Save as `scripts/validate-ui.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Frontend UI Validation Suite"
echo "================================"

BASE_URL="http://localhost:5173"
SCREENSHOT_DIR="screenshots/validation"
mkdir -p $SCREENSHOT_DIR

# Test 1: Dashboard
echo "Test 1: Dashboard..."
agent-browser open $BASE_URL
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='metrics-card']" && echo "  ✓ Metrics visible"
agent-browser screenshot $SCREENSHOT_DIR/01-dashboard.png

# Test 2: Customers
echo "Test 2: Customers..."
agent-browser open $BASE_URL/customers
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='customer-table']" && echo "  ✓ Customer table visible"
agent-browser is visible "[data-testid='add-customer-btn']" && echo "  ✓ Add button visible"
agent-browser screenshot $SCREENSHOT_DIR/02-customers.png

# Test 3: Customer Detail
echo "Test 3: Customer Detail..."
agent-browser click "[data-testid='customer-row'] a"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='customer-detail']" && echo "  ✓ Detail page visible"
agent-browser screenshot $SCREENSHOT_DIR/03-customer-detail.png

# Test 4: Jobs
echo "Test 4: Jobs..."
agent-browser open $BASE_URL/jobs
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='job-table']" && echo "  ✓ Job table visible"
agent-browser screenshot $SCREENSHOT_DIR/04-jobs.png

# Test 5: Job Detail
echo "Test 5: Job Detail..."
agent-browser click "[data-testid='job-row'] a"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='job-detail']" && echo "  ✓ Detail page visible"
agent-browser screenshot $SCREENSHOT_DIR/05-job-detail.png

# Test 6: Schedule
echo "Test 6: Schedule..."
agent-browser open $BASE_URL/schedule
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='schedule-calendar']" && echo "  ✓ Calendar visible"
agent-browser screenshot $SCREENSHOT_DIR/06-schedule.png

# Test 7: Staff
echo "Test 7: Staff..."
agent-browser open $BASE_URL/staff
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='staff-table']" && echo "  ✓ Staff table visible"
agent-browser screenshot $SCREENSHOT_DIR/07-staff.png

# Test 8: Staff Detail
echo "Test 8: Staff Detail..."
agent-browser click "[data-testid='staff-row'] a"
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='staff-detail']" && echo "  ✓ Detail page visible"
agent-browser screenshot $SCREENSHOT_DIR/08-staff-detail.png

# Test 9: Settings
echo "Test 9: Settings..."
agent-browser open $BASE_URL/settings
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='settings-page']" && echo "  ✓ Settings visible"
agent-browser screenshot $SCREENSHOT_DIR/09-settings.png

agent-browser close

echo ""
echo "✅ All UI tests passed!"
echo "Screenshots saved to: $SCREENSHOT_DIR/"
```

---

## Bugs Fixed During Testing

| Issue | File | Fix |
|-------|------|-----|
| Staff API 404 | `frontend/src/features/staff/api/staffApi.ts` | Changed `BASE_URL` from `/api/v1/staff` to `/staff` (apiClient already has baseURL) |
| Staff detail routing | `frontend/src/pages/Staff.tsx` | Rewrote to use `useParams` pattern instead of nested Routes |
| Staff hourly_rate error | `frontend/src/features/staff/components/StaffDetail.tsx` | Wrapped in `Number()` before calling `.toFixed(2)` |
| JobForm TypeScript errors | `frontend/src/features/jobs/components/JobForm.tsx` | Removed `z.coerce.number()` and `.default()` from schema, used explicit defaults |
| CustomerForm TypeScript errors | `frontend/src/features/customers/components/CustomerForm.tsx` | Same pattern - removed `.default()` from boolean fields |

---

## Remaining Tests (Not Yet Implemented)

### Form Submission Tests
- [ ] Create customer - fill form and submit
- [ ] Edit customer - modify and save
- [ ] Create job - fill form and submit
- [ ] Create appointment - schedule new appointment

### Error State Tests
- [ ] API error handling (network failure)
- [ ] Form validation errors display
- [ ] 404 page for invalid routes
- [ ] Empty state displays (no data)

### Interactive Tests
- [ ] Pagination navigation
- [ ] Search/filter functionality
- [ ] Sort columns
- [ ] Delete confirmation dialogs

### Mobile Responsiveness
- [ ] Sidebar collapse on mobile
- [ ] Table horizontal scroll
- [ ] Form layout on small screens

---

## Test Data IDs Reference

| Component | Test ID Pattern |
|-----------|-----------------|
| Navigation | `nav-{page}` |
| Tables | `{feature}-table` |
| Table rows | `{feature}-row` |
| Detail pages | `{feature}-detail` |
| Forms | `{feature}-form` |
| Add buttons | `add-{feature}-btn` |
| Submit buttons | `submit-btn` |
| Status badges | `status-{status}` |
| Form inputs | Use `name` attribute or `data-testid="{field}-input"` |

---

## Running Unit Tests

In addition to UI tests, run the frontend unit test suite:

```bash
cd frontend

# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test CustomerForm
```

Current test coverage: See `frontend/coverage/` after running coverage report.
