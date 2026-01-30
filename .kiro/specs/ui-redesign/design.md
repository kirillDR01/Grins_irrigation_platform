# UI Redesign Design Document

## Overview

This design document outlines the implementation approach for Phase 10: Complete UI Redesign of the Grin's Irrigation Platform. The redesign focuses **exclusively on visual/UI changes** - no functionality will be modified.

## Design Principles

1. **Visual-Only Changes**: All API calls, state management, routing, and business logic remain unchanged
2. **Test Compatibility**: All `data-testid` attributes must be preserved for agent-browser validation
3. **Reference Fidelity**: Match `UI_RE-DESIGN/Re-Design-Visual.png` and `UI_RE-DESIGN/App.tsx` as closely as possible
4. **Desktop-First**: Primary users use desktop; mobile responsiveness as secondary pass
5. **Incremental Implementation**: Each phase validated before proceeding

---

## Design System Specifications

### Color Palette

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--primary` | Teal-500 (`#14B8A6`) | Teal-500 (`#14B8A6`) | Primary actions, active states |
| `--primary-hover` | Teal-600 (`#0D9488`) | Teal-400 (`#2DD4BF`) | Hover states |
| `--background` | Slate-50 (`#F8FAFC`) | `oklch(0.15 0.01 250)` | Page background |
| `--card` | White (`#FFFFFF`) | `oklch(0.2 0.01 250)` | Card backgrounds |
| `--border` | Slate-100 (`#F1F5F9`) | `oklch(0.3 0.01 250)` | Borders |
| `--text-primary` | Slate-800 (`#1E293B`) | `oklch(0.95 0.005 250)` | Primary text |
| `--text-secondary` | Slate-500 (`#64748B`) | `oklch(0.6 0.02 250)` | Secondary text |
| `--muted` | Slate-50 (`#F8FAFC`) | `oklch(0.25 0.01 250)` | Muted backgrounds |
| `--accent` | Teal-50 (`#F0FDFA`) | `oklch(0.25 0.05 180)` | Accent backgrounds |

### Typography

| Element | Specification |
|---------|---------------|
| Font Family | Inter (Google Fonts CDN) |
| Font Weights | 300, 400, 500, 600, 700 |
| Page Title | `text-2xl font-bold text-slate-800` |
| Section Header | `text-lg font-bold text-slate-800` |
| Body Text | `text-sm text-slate-600` |
| Labels | `text-xs font-semibold uppercase tracking-wider text-slate-400` |
| Subtext | `text-xs text-slate-400` |

### Spacing & Layout

| Element | Specification |
|---------|---------------|
| Card Padding | `p-6` (24px) |
| Card Border Radius | `rounded-2xl` (16px) |
| Button Border Radius | `rounded-lg` (8px) |
| Job Item Border Radius | `rounded-xl` (12px) |
| Nav Item Padding | `px-6 py-4` |
| Grid Gap (Cards) | `gap-8` (32px) |
| Job Items Spacing | `space-y-4` (16px) |
| Technician Items Spacing | `space-y-6` (24px) |
| Card Header Margin | `mb-6` (24px) |

### Shadows

| Element | Specification |
|---------|---------------|
| Card Default | `shadow-sm` |
| Card Hover | `hover:shadow-md transition-shadow` |
| Primary Button | `shadow-sm shadow-teal-200` |
| Logo Icon | `shadow-lg shadow-teal-500/30` |

### Animations

| Animation | Specification |
|-----------|---------------|
| Page Entry | `animate-in fade-in slide-in-from-bottom-4 duration-500` |
| Hover Transitions | `transition-all duration-200` |
| Card Hover | `hover:shadow-md transition-shadow` |
| Row Hover | `transition-colors` |

---

## Component Specifications

### Avatar Variants

| Variant | Location | Specification |
|---------|----------|---------------|
| Staff List | Technician Availability | `w-10 h-10 rounded-full bg-slate-200 text-slate-600 font-semibold text-sm` (initials) |
| Header | Top Right | `w-8 h-8 rounded-full bg-teal-100 text-teal-700 font-bold text-xs` (initials) |
| Sidebar Profile | Bottom | `w-10 h-10 rounded-full border-2 border-white shadow-sm` (photo) |

### Button Variants

| Variant | Specification |
|---------|---------------|
| Primary | `bg-teal-500 hover:bg-teal-600 text-white px-5 py-2.5 rounded-lg shadow-sm shadow-teal-200 transition-all` |
| Secondary | `bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 px-4 py-2.5 rounded-lg transition-all` |
| Icon Button | `text-slate-400 hover:text-teal-600 p-2 hover:bg-teal-50 rounded-lg transition-colors` |

### Status Badge Colors

| Status | Specification |
|--------|---------------|
| Completed | `bg-emerald-100 text-emerald-700` |
| Scheduled | `bg-violet-100 text-violet-700` |
| Approved | `bg-blue-100 text-blue-700` |
| Ready | `bg-emerald-50 text-emerald-600 border border-emerald-100` |
| Needs Estimate | `bg-amber-50 text-amber-600 border border-amber-100` |
| New Customer | `bg-blue-50 text-blue-600 border border-blue-100` |
| Priority | `bg-rose-50 text-rose-600 border border-rose-100` |
| New (Status) | `bg-teal-50 text-teal-600` |
| High Priority | `bg-orange-50 text-orange-600` |
| Normal Priority | `bg-slate-100 text-slate-500` |

### Card Specifications

| Element | Specification |
|---------|---------------|
| Container | `bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow` |
| Header | `flex justify-between items-center mb-6` |
| Title | `font-bold text-slate-800 text-lg` |
| View All Link | `text-teal-600 text-sm font-medium hover:text-teal-700 flex items-center gap-1` |

### Table Specifications

| Element | Specification |
|---------|---------------|
| Container | `bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden` |
| Toolbar | `p-4 border-b border-slate-100 flex gap-4` |
| Search Input | `pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-teal-500/20 focus:border-teal-500` |
| Header Row | `bg-slate-50/50 text-slate-500 text-xs uppercase tracking-wider` |
| Header Cell | `px-6 py-4 font-medium` |
| Body Row | `hover:bg-slate-50/80 transition-colors` |
| Body Cell | `px-6 py-4` |
| Dividers | `divide-y divide-slate-50` |
| Pagination | `p-4 border-t border-slate-100 flex justify-between items-center text-sm text-slate-500` |

### Modal Specifications

| Element | Specification |
|---------|---------------|
| Backdrop | `bg-slate-900/20 backdrop-blur-sm` |
| Container | `bg-white rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in duration-200` |
| Header | `p-6 border-b border-slate-100 bg-slate-50/50` |
| Footer | `p-6 border-t border-slate-100 bg-slate-50/50` |
| Close Button | `text-slate-400 hover:text-slate-600` |

### Alert Specifications

| Element | Specification |
|---------|---------------|
| Container | `bg-white p-4 rounded-xl shadow-sm border-l-4` |
| Icon Container | `p-2 rounded-full` |
| Title | `text-slate-800 font-medium` |
| Description | `text-slate-500 text-sm` |
| Amber Alert | `border-amber-400`, icon: `bg-amber-100 text-amber-600`, button: `text-amber-600 bg-amber-50` |
| Red Alert | `border-red-400`, icon: `bg-red-100 text-red-600`, button: `text-red-600 bg-red-50` |

---

## Implementation Phases

### Phase 10A: Foundation (CSS & Core Components)
**Components: 8**

1. `index.html` - Add Inter font from Google Fonts CDN
2. `index.css` - New CSS variables for teal color scheme
3. `tailwind.config.js` - Extended theme with teal colors
4. `Layout.tsx` - Complete sidebar + header redesign
5. `PageHeader.tsx` - Typography, spacing updates
6. `StatusBadge.tsx` - New color scheme
7. `LoadingSpinner.tsx` - Teal color
8. `ErrorBoundary.tsx` - Card styling

### Phase 10B: UI Components (shadcn/ui)
**Components: ~17**

1. `button.tsx` - Primary teal, secondary white variants
2. `card.tsx` - Rounded-2xl, shadow-sm, hover states
3. `badge.tsx` - New color variants
4. `table.tsx` - Header styling, hover states
5. `input.tsx` - Teal focus ring
6. `select.tsx` - Consistent styling
7. `dialog.tsx` - Modal styling with backdrop blur
8. `dropdown-menu.tsx` - Hover states
9. `tabs.tsx` - Active state styling
10. `alert.tsx` - Left border accent style
11. `checkbox.tsx` - Teal checked state
12. `switch.tsx` - Teal checked state
13. `popover.tsx` - Rounded corners
14. `calendar.tsx` - Teal selection
15. `textarea.tsx` - Consistent with input
16. `sheet.tsx` - Rounded corners, backdrop blur
17. `skeleton.tsx` - Slate-100 background

### Phase 10C: Auth & Settings
**Components: 3**

1. `LoginPage.tsx` - Full page redesign with teal branding
2. `UserMenu.tsx` - Avatar and dropdown styling
3. `Settings.tsx` (page) - Create full settings page design with theme toggle

### Phase 10D: Dashboard
**Components: 4**

1. `DashboardPage.tsx` - Layout, alerts section, stat cards
2. `MetricsCard.tsx` - Icon containers, typography
3. `RecentActivity.tsx` - Card styling, list items
4. `MorningBriefing.tsx` - Alert styling

### Phase 10E: List Views
**Components: 5**

1. `CustomerList.tsx` - Table, toolbar, pagination
2. `JobList.tsx` - Table, filters, badges
3. `StaffList.tsx` - Table, availability indicators
4. `AppointmentList.tsx` - Table, filters
5. `InvoiceList.tsx` - Table, status badges

### Phase 10F: Detail Views
**Components: 5**

1. `CustomerDetail.tsx` - Card layout, sections
2. `JobDetail.tsx` - Card layout, status display
3. `StaffDetail.tsx` - Card layout
4. `AppointmentDetail.tsx` - Card layout
5. `InvoiceDetail.tsx` - Card layout

### Phase 10G: Forms & Modals
**Components: 12**

1. `CustomerForm.tsx` - Form styling
2. `JobForm.tsx` - Form styling
3. `AppointmentForm.tsx` - Form styling
4. `InvoiceForm.tsx` - Form styling
5. `CreateInvoiceDialog.tsx` - Modal styling
6. `PaymentDialog.tsx` - Modal styling
7. `ClearDayDialog.tsx` - Modal styling
8. `ScheduleExplanationModal.tsx` - Modal styling
9. `SearchableCustomerDropdown.tsx` - Dropdown styling
10. `NaturalLanguageConstraintsInput.tsx` - Input/chip styling
11. `JobSelectionControls.tsx` - Button/checkbox styling
12. `CustomerSearch.tsx` - Search input styling

### Phase 10H: AI Components
**Components: 10**

1. `AIQueryChat.tsx` - Card, message bubbles, input
2. `AICategorization.tsx` - Modal styling (reference design)
3. `AICommunicationDrafts.tsx` - Card/list styling
4. `AIEstimateGenerator.tsx` - Card/form styling
5. `AIScheduleGenerator.tsx` - Card/form styling
6. `AIErrorState.tsx` - Error alert styling
7. `AILoadingState.tsx` - Teal spinner
8. `AIStreamingText.tsx` - Text animation
9. `CommunicationsQueue.tsx` - Queue list styling
10. `SchedulingHelpAssistant.tsx` - Card/chat styling

### Phase 10I: Map Components
**Components: 15**

1. `mapStyles.ts` - Map theme colors
2. `staffColors.ts` - Staff color palette
3. `ScheduleMap.tsx` - Container, controls layout
4. `MapMarker.tsx` - Marker colors
5. `MapInfoWindow.tsx` - Info window card styling
6. `MapLegend.tsx` - Legend card styling
7. `MapFilters.tsx` - Filter button/dropdown styling
8. `MapControls.tsx` - Control button styling
9. `MapEmptyState.tsx` - Empty state card
10. `MapErrorState.tsx` - Error state styling
11. `MapLoadingState.tsx` - Teal spinner
12. `MissingCoordsWarning.tsx` - Warning alert
13. `MobileJobSheet.tsx` - Sheet/card styling
14. `RoutePolyline.tsx` - Polyline colors
15. `StaffHomeMarker.tsx` - Home marker styling

### Phase 10J: Schedule Workflow Components
**Components: 8**

1. `ScheduleGenerationPage.tsx` - Card layouts
2. `ScheduleResults.tsx` - Results card styling
3. `JobsReadyToSchedulePreview.tsx` - Table/card styling
4. `ClearResultsButton.tsx` - Button styling
5. `ClearDayButton.tsx` - Button styling
6. `RecentlyClearedSection.tsx` - Card styling
7. `UnassignedJobExplanationCard.tsx` - Card styling
8. `CalendarView.tsx` - Calendar color scheme

### Phase 10K: Invoice Widgets & Final Polish
**Components: 5 + validation**

1. `GenerateInvoiceButton.tsx` - Button styling
2. `LienDeadlinesWidget.tsx` - Card/alert styling
3. `OverdueInvoicesWidget.tsx` - Card/alert styling
4. `InvoiceStatusBadge.tsx` - New color scheme
5. `JobStatusBadge.tsx` - New color scheme
6. Final consistency check across all components

---

## Correctness Properties

### CP-1: Data-TestID Preservation
All existing `data-testid` attributes must be preserved exactly as they are. No additions, removals, or modifications to test IDs.

### CP-2: Functionality Preservation
All existing functionality must work identically:
- API calls return same data
- State management behaves identically
- Routing works the same
- Form validation unchanged
- Business logic unchanged

### CP-3: Visual Consistency
All components must follow the design system specifications:
- Colors match the defined palette
- Typography follows the defined scale
- Spacing follows the defined values
- Animations match the defined specifications

### CP-4: Responsive Behavior
Desktop layout must work correctly at all breakpoints:
- Sidebar collapses on mobile
- Tables scroll horizontally on small screens
- Cards stack vertically on mobile

### CP-5: Accessibility
WCAG 2.1 AA compliance:
- Color contrast ratios maintained
- Focus states visible
- Screen reader compatibility

---

## Comprehensive Agent-Browser Test Plan

This section defines **every possible user interaction** that must be validated using agent-browser. Tests are organized by feature area and cover all interactive elements.

### Test Infrastructure Setup

Before running tests:
```bash
# Start backend
cd /path/to/project && uv run uvicorn grins_platform.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend
cd frontend && npm run dev

# Verify servers
curl -s http://localhost:8000/health
curl -s http://localhost:5173
```

---


### ABT-1: Authentication Tests

#### ABT-1.1: Login Page Visual Validation
```bash
# Navigate to login page
agent-browser open http://localhost:5173/login
agent-browser wait --load networkidle
agent-browser snapshot -i

# Validate login page elements
agent-browser is visible "[data-testid='login-page']"
agent-browser is visible "[data-testid='login-form']"
agent-browser is visible "[data-testid='email-input']"
agent-browser is visible "[data-testid='password-input']"
agent-browser is visible "[data-testid='login-button']"

# Screenshot for visual validation
agent-browser screenshot screenshots/ui-redesign/login-page.png
```

#### ABT-1.2: Login Form Interactions
```bash
# Test email input focus
agent-browser click "[data-testid='email-input']"
agent-browser snapshot -i
# Verify teal focus ring visible

# Test password input focus
agent-browser click "[data-testid='password-input']"
agent-browser snapshot -i

# Test form submission with invalid data
agent-browser fill "[data-testid='email-input']" "invalid-email"
agent-browser fill "[data-testid='password-input']" "short"
agent-browser click "[data-testid='login-button']"
agent-browser wait --text "Invalid"
# Verify error alert styling

# Test successful login
agent-browser fill "[data-testid='email-input']" "admin@grins.com"
agent-browser fill "[data-testid='password-input']" "password123"
agent-browser click "[data-testid='login-button']"
agent-browser wait --url "**/dashboard"
```

#### ABT-1.3: User Menu Interactions
```bash
# Navigate to dashboard (logged in)
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Test user menu dropdown
agent-browser is visible "[data-testid='user-menu']"
agent-browser click "[data-testid='user-menu']"
agent-browser wait "[data-testid='user-menu-dropdown']"
agent-browser is visible "[data-testid='user-menu-dropdown']"

# Verify dropdown items
agent-browser is visible "[data-testid='logout-button']"

# Test logout
agent-browser click "[data-testid='logout-button']"
agent-browser wait --url "**/login"
```

---

### ABT-2: Layout & Navigation Tests

#### ABT-2.1: Sidebar Visual Validation
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate sidebar structure
agent-browser is visible "[data-testid='sidebar']"
agent-browser is visible "[data-testid='sidebar-nav']"

# Validate all navigation items
agent-browser is visible "[data-testid='nav-dashboard']"
agent-browser is visible "[data-testid='nav-customers']"
agent-browser is visible "[data-testid='nav-jobs']"
agent-browser is visible "[data-testid='nav-schedule']"
agent-browser is visible "[data-testid='nav-generate']"
agent-browser is visible "[data-testid='nav-staff']"
agent-browser is visible "[data-testid='nav-invoices']"
agent-browser is visible "[data-testid='nav-settings']"

# Screenshot sidebar
agent-browser screenshot screenshots/ui-redesign/sidebar.png
```

#### ABT-2.2: Navigation Click Tests
```bash
# Test each navigation item
agent-browser click "[data-testid='nav-customers']"
agent-browser wait --url "**/customers"
agent-browser is visible "[data-testid='customers-page']"

agent-browser click "[data-testid='nav-jobs']"
agent-browser wait --url "**/jobs"
agent-browser is visible "[data-testid='jobs-page']"

agent-browser click "[data-testid='nav-schedule']"
agent-browser wait --url "**/schedule"
agent-browser is visible "[data-testid='schedule-page']"

agent-browser click "[data-testid='nav-generate']"
agent-browser wait --url "**/schedule/generate"
agent-browser is visible "[data-testid='schedule-generate-page']"

agent-browser click "[data-testid='nav-staff']"
agent-browser wait --url "**/staff"
agent-browser is visible "[data-testid='staff-page']"

agent-browser click "[data-testid='nav-invoices']"
agent-browser wait --url "**/invoices"
agent-browser is visible "[data-testid='invoices-page']"

agent-browser click "[data-testid='nav-settings']"
agent-browser wait --url "**/settings"
agent-browser is visible "[data-testid='settings-page']"

agent-browser click "[data-testid='nav-dashboard']"
agent-browser wait --url "**/dashboard"
agent-browser is visible "[data-testid='dashboard-page']"
```

#### ABT-2.3: Navigation Active State Tests
```bash
# Verify active state styling on each page
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle
agent-browser snapshot -i
# Verify nav-dashboard has active styling (teal-50 bg, teal-500 left border)

agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
agent-browser snapshot -i
# Verify nav-customers has active styling

agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle
agent-browser snapshot -i
# Verify nav-jobs has active styling
```

#### ABT-2.4: Header Visual Validation
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate header structure
agent-browser is visible "[data-testid='header']"

# Screenshot header
agent-browser screenshot screenshots/ui-redesign/header.png
```

#### ABT-2.5: Mobile Menu Tests
```bash
# Set mobile viewport
agent-browser set viewport 375 812

agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Verify sidebar is hidden
agent-browser snapshot -i

# Test mobile menu button
agent-browser is visible "[data-testid='mobile-menu-button']"
agent-browser click "[data-testid='mobile-menu-button']"
agent-browser wait "[data-testid='sidebar']"

# Verify sidebar backdrop
agent-browser is visible "[data-testid='sidebar-backdrop']"

# Close sidebar by clicking backdrop
agent-browser click "[data-testid='sidebar-backdrop']"

# Reset viewport
agent-browser set viewport 1920 1080
```

---

### ABT-3: Dashboard Tests

#### ABT-3.1: Dashboard Page Visual Validation
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate dashboard structure
agent-browser is visible "[data-testid='dashboard-page']"
agent-browser is visible "[data-testid='page-header']"

# Screenshot full dashboard
agent-browser screenshot screenshots/ui-redesign/dashboard-full.png --full
```

#### ABT-3.2: Stat Cards Validation
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate stat cards
agent-browser is visible "[data-testid='metrics-card']"

# Test stat card hover effects
agent-browser hover "[data-testid='metrics-card']"
agent-browser snapshot -i
# Verify shadow-md on hover
```

#### ABT-3.3: Recent Activity Section
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate recent activity
agent-browser is visible "[data-testid='recent-activity']"

# Test job item hover
agent-browser hover "[data-testid='job-item']"
agent-browser snapshot -i
# Verify hover:bg-slate-100 effect
```

#### ABT-3.4: Dashboard Action Buttons
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Test View Schedule button
agent-browser is visible "[data-testid='view-schedule-btn']"
agent-browser click "[data-testid='view-schedule-btn']"
agent-browser wait --url "**/schedule"

# Go back and test New Job button
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle
agent-browser is visible "[data-testid='new-job-btn']"
agent-browser click "[data-testid='new-job-btn']"
# Verify job form opens
```

---

### ABT-4: Customer Tests

#### ABT-4.1: Customer List Visual Validation
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Validate customer list structure
agent-browser is visible "[data-testid='customers-page']"
agent-browser is visible "[data-testid='customer-table']"
agent-browser is visible "[data-testid='customer-search']"

# Screenshot customer list
agent-browser screenshot screenshots/ui-redesign/customer-list.png --full
```

#### ABT-4.2: Customer Search Interaction
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Test search input
agent-browser click "[data-testid='customer-search']"
agent-browser fill "[data-testid='customer-search']" "John"
agent-browser wait 500
# Verify filtered results

# Clear search
agent-browser fill "[data-testid='customer-search']" ""
agent-browser wait 500
```

#### ABT-4.3: Customer Table Row Interactions
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Test row hover
agent-browser hover "[data-testid='customer-row']"
agent-browser snapshot -i
# Verify hover:bg-slate-50/80 effect

# Test row click (navigate to detail)
agent-browser click "[data-testid='customer-row']"
agent-browser wait --url "**/customers/*"
agent-browser is visible "[data-testid='customer-detail']"
```

#### ABT-4.4: Customer Pagination
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Test pagination if available
agent-browser is visible "[data-testid='pagination']"
agent-browser click "[data-testid='next-page-btn']"
agent-browser wait 500
agent-browser click "[data-testid='prev-page-btn']"
agent-browser wait 500
```

#### ABT-4.5: Add Customer Flow
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Click Add Customer button
agent-browser is visible "[data-testid='add-customer-btn']"
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"

# Validate form fields
agent-browser is visible "[data-testid='customer-form']"
agent-browser is visible "[name='first_name']"
agent-browser is visible "[name='last_name']"
agent-browser is visible "[name='phone']"
agent-browser is visible "[name='email']"

# Test form input focus states
agent-browser click "[name='first_name']"
agent-browser snapshot -i
# Verify teal focus ring

# Fill form
agent-browser fill "[name='first_name']" "Test"
agent-browser fill "[name='last_name']" "Customer"
agent-browser fill "[name='phone']" "6125551234"
agent-browser fill "[name='email']" "test@example.com"

# Submit form
agent-browser click "[data-testid='submit-btn']"
agent-browser wait --text "Success"
```

#### ABT-4.6: Customer Detail View
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Navigate to customer detail
agent-browser click "[data-testid='customer-row']"
agent-browser wait --url "**/customers/*"

# Validate detail view
agent-browser is visible "[data-testid='customer-detail']"

# Screenshot detail view
agent-browser screenshot screenshots/ui-redesign/customer-detail.png
```

#### ABT-4.7: Customer Edit Flow
```bash
# From customer detail
agent-browser is visible "[data-testid='edit-customer-btn']"
agent-browser click "[data-testid='edit-customer-btn']"
agent-browser wait "[data-testid='customer-form']"

# Verify form is pre-filled
agent-browser snapshot -i

# Cancel edit
agent-browser click "[data-testid='cancel-btn']"
```

---

### ABT-5: Job Tests

#### ABT-5.1: Job List Visual Validation
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Validate job list structure
agent-browser is visible "[data-testid='jobs-page']"
agent-browser is visible "[data-testid='job-table']"

# Screenshot job list
agent-browser screenshot screenshots/ui-redesign/job-list.png --full
```

#### ABT-5.2: Job Status Badges
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Validate status badges are visible
agent-browser is visible "[data-testid='job-status-badge']"

# Screenshot badges
agent-browser snapshot -i
```

#### ABT-5.3: Job Filters
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Test status filter dropdown
agent-browser is visible "[data-testid='status-filter']"
agent-browser click "[data-testid='status-filter']"
agent-browser wait "[data-testid='status-filter-options']"

# Select a status
agent-browser click "[data-testid='status-scheduled']"
agent-browser wait 500
# Verify filtered results
```

#### ABT-5.4: AI Categorize Modal
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Open AI Categorize modal
agent-browser is visible "[data-testid='ai-categorize-btn']"
agent-browser click "[data-testid='ai-categorize-btn']"
agent-browser wait "[data-testid='ai-categorize-modal']"

# Validate modal structure
agent-browser is visible "[data-testid='ai-categorize-modal']"
agent-browser is visible "[data-testid='job-description-input']"

# Screenshot modal
agent-browser screenshot screenshots/ui-redesign/ai-categorize-modal.png

# Test textarea input
agent-browser fill "[data-testid='job-description-input']" "Broken sprinkler head needs replacement"
agent-browser snapshot -i

# Close modal
agent-browser click "[data-testid='close-modal-btn']"
```

#### ABT-5.5: New Job Flow
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Click New Job button
agent-browser is visible "[data-testid='new-job-btn']"
agent-browser click "[data-testid='new-job-btn']"
agent-browser wait "[data-testid='job-form']"

# Validate form
agent-browser is visible "[data-testid='job-form']"

# Screenshot form
agent-browser screenshot screenshots/ui-redesign/job-form.png
```

#### ABT-5.6: Job Detail View
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Navigate to job detail
agent-browser click "[data-testid='job-row']"
agent-browser wait --url "**/jobs/*"

# Validate detail view
agent-browser is visible "[data-testid='job-detail']"

# Screenshot detail
agent-browser screenshot screenshots/ui-redesign/job-detail.png
```

---

### ABT-6: Staff Tests

#### ABT-6.1: Staff List Visual Validation
```bash
agent-browser open http://localhost:5173/staff
agent-browser wait --load networkidle

# Validate staff list structure
agent-browser is visible "[data-testid='staff-page']"
agent-browser is visible "[data-testid='staff-table']"

# Screenshot staff list
agent-browser screenshot screenshots/ui-redesign/staff-list.png --full
```

#### ABT-6.2: Staff Availability Indicators
```bash
agent-browser open http://localhost:5173/staff
agent-browser wait --load networkidle

# Validate availability indicators
agent-browser is visible "[data-testid='availability-indicator']"
agent-browser snapshot -i
# Verify emerald-500 for Available, amber-500 for On Job
```

#### ABT-6.3: Staff Detail View
```bash
agent-browser open http://localhost:5173/staff
agent-browser wait --load networkidle

# Navigate to staff detail
agent-browser click "[data-testid='staff-row']"
agent-browser wait --url "**/staff/*"

# Validate detail view
agent-browser is visible "[data-testid='staff-detail']"

# Screenshot detail
agent-browser screenshot screenshots/ui-redesign/staff-detail.png
```

---

### ABT-7: Invoice Tests

#### ABT-7.1: Invoice List Visual Validation
```bash
agent-browser open http://localhost:5173/invoices
agent-browser wait --load networkidle

# Validate invoice list structure
agent-browser is visible "[data-testid='invoices-page']"
agent-browser is visible "[data-testid='invoice-table']"

# Screenshot invoice list
agent-browser screenshot screenshots/ui-redesign/invoice-list.png --full
```

#### ABT-7.2: Invoice Status Badges
```bash
agent-browser open http://localhost:5173/invoices
agent-browser wait --load networkidle

# Validate status badges
agent-browser is visible "[data-testid='invoice-status-badge']"
agent-browser snapshot -i
```

#### ABT-7.3: Create Invoice Dialog
```bash
agent-browser open http://localhost:5173/invoices
agent-browser wait --load networkidle

# Open create invoice dialog
agent-browser is visible "[data-testid='create-invoice-btn']"
agent-browser click "[data-testid='create-invoice-btn']"
agent-browser wait "[data-testid='create-invoice-dialog']"

# Validate dialog structure
agent-browser is visible "[data-testid='create-invoice-dialog']"

# Screenshot dialog
agent-browser screenshot screenshots/ui-redesign/create-invoice-dialog.png

# Close dialog
agent-browser click "[data-testid='close-dialog-btn']"
```

#### ABT-7.4: Payment Dialog
```bash
agent-browser open http://localhost:5173/invoices
agent-browser wait --load networkidle

# Click on an invoice to open detail
agent-browser click "[data-testid='invoice-row']"
agent-browser wait --url "**/invoices/*"

# Open payment dialog
agent-browser is visible "[data-testid='record-payment-btn']"
agent-browser click "[data-testid='record-payment-btn']"
agent-browser wait "[data-testid='payment-dialog']"

# Validate dialog
agent-browser is visible "[data-testid='payment-dialog']"

# Screenshot dialog
agent-browser screenshot screenshots/ui-redesign/payment-dialog.png

# Close dialog
agent-browser click "[data-testid='close-dialog-btn']"
```

#### ABT-7.5: Invoice Detail View
```bash
agent-browser open http://localhost:5173/invoices
agent-browser wait --load networkidle

# Navigate to invoice detail
agent-browser click "[data-testid='invoice-row']"
agent-browser wait --url "**/invoices/*"

# Validate detail view
agent-browser is visible "[data-testid='invoice-detail']"

# Screenshot detail
agent-browser screenshot screenshots/ui-redesign/invoice-detail.png
```

---


### ABT-8: Schedule Tests

#### ABT-8.1: Schedule Page Visual Validation
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Validate schedule page structure
agent-browser is visible "[data-testid='schedule-page']"

# Screenshot schedule page
agent-browser screenshot screenshots/ui-redesign/schedule-page.png --full
```

#### ABT-8.2: Calendar View Interactions
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Validate calendar
agent-browser is visible "[data-testid='calendar-view']"

# Test date selection
agent-browser click "[data-testid='calendar-day']"
agent-browser snapshot -i
# Verify teal-500 selection color

# Test month navigation
agent-browser click "[data-testid='next-month-btn']"
agent-browser wait 300
agent-browser click "[data-testid='prev-month-btn']"
agent-browser wait 300
```

#### ABT-8.3: Appointment List
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Validate appointment list
agent-browser is visible "[data-testid='appointment-list']"

# Test appointment row hover
agent-browser hover "[data-testid='appointment-row']"
agent-browser snapshot -i
```

#### ABT-8.4: Appointment Detail
```bash
agent-browser open http://localhost:5173/schedule
agent-browser wait --load networkidle

# Click on appointment
agent-browser click "[data-testid='appointment-row']"
agent-browser wait "[data-testid='appointment-detail']"

# Validate detail view
agent-browser is visible "[data-testid='appointment-detail']"

# Screenshot detail
agent-browser screenshot screenshots/ui-redesign/appointment-detail.png
```

---

### ABT-9: Schedule Generation Tests

#### ABT-9.1: Schedule Generation Page Visual Validation
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Validate page structure
agent-browser is visible "[data-testid='schedule-generate-page']"

# Screenshot full page
agent-browser screenshot screenshots/ui-redesign/schedule-generate-page.png --full
```

#### ABT-9.2: Date Picker Interaction
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Test date picker
agent-browser is visible "[data-testid='date-picker']"
agent-browser click "[data-testid='date-picker']"
agent-browser wait "[data-testid='calendar-popover']"

# Select a date
agent-browser click "[data-testid='calendar-day']"
agent-browser snapshot -i
```

#### ABT-9.3: Jobs Ready to Schedule Preview
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Validate jobs preview
agent-browser is visible "[data-testid='jobs-preview']"

# Test job selection
agent-browser click "[data-testid='job-checkbox']"
agent-browser snapshot -i
```

#### ABT-9.4: Natural Language Constraints Input
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Test constraints input
agent-browser is visible "[data-testid='constraints-input']"
agent-browser fill "[data-testid='constraints-input']" "No jobs after 4pm"
agent-browser press "Enter"
agent-browser snapshot -i
# Verify chip styling
```

#### ABT-9.5: Generate Schedule Button
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Test generate button
agent-browser is visible "[data-testid='generate-schedule-btn']"
agent-browser click "[data-testid='generate-schedule-btn']"
agent-browser wait "[data-testid='schedule-results']"
```

#### ABT-9.6: Schedule Results View
```bash
# After generating schedule
agent-browser is visible "[data-testid='schedule-results']"

# Screenshot results
agent-browser screenshot screenshots/ui-redesign/schedule-results.png --full
```

#### ABT-9.7: View Toggle (List/Map)
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Generate schedule first
agent-browser click "[data-testid='generate-schedule-btn']"
agent-browser wait "[data-testid='schedule-results']"

# Test view toggle
agent-browser is visible "[data-testid='view-toggle']"
agent-browser click "[data-testid='view-toggle-map']"
agent-browser wait "[data-testid='schedule-map']"

agent-browser click "[data-testid='view-toggle-list']"
agent-browser wait "[data-testid='schedule-results']"
```

#### ABT-9.8: Schedule Explanation Modal
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Generate schedule
agent-browser click "[data-testid='generate-schedule-btn']"
agent-browser wait "[data-testid='schedule-results']"

# Open explanation modal
agent-browser is visible "[data-testid='explain-schedule-btn']"
agent-browser click "[data-testid='explain-schedule-btn']"
agent-browser wait "[data-testid='schedule-explanation-modal']"

# Validate modal
agent-browser is visible "[data-testid='schedule-explanation-modal']"

# Screenshot modal
agent-browser screenshot screenshots/ui-redesign/schedule-explanation-modal.png

# Close modal
agent-browser click "[data-testid='close-modal-btn']"
```

#### ABT-9.9: Clear Day Dialog
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Test clear day button
agent-browser is visible "[data-testid='clear-day-btn']"
agent-browser click "[data-testid='clear-day-btn']"
agent-browser wait "[data-testid='clear-day-dialog']"

# Validate dialog
agent-browser is visible "[data-testid='clear-day-dialog']"

# Screenshot dialog
agent-browser screenshot screenshots/ui-redesign/clear-day-dialog.png

# Cancel
agent-browser click "[data-testid='cancel-btn']"
```

#### ABT-9.10: Apply Schedule Flow
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Generate schedule
agent-browser click "[data-testid='generate-schedule-btn']"
agent-browser wait "[data-testid='schedule-results']"

# Apply schedule
agent-browser is visible "[data-testid='apply-schedule-btn']"
agent-browser click "[data-testid='apply-schedule-btn']"
agent-browser wait --text "Success"
```

---

### ABT-10: Map Tests

#### ABT-10.1: Map Visual Validation
```bash
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Generate schedule
agent-browser click "[data-testid='generate-schedule-btn']"
agent-browser wait "[data-testid='schedule-results']"

# Switch to map view
agent-browser click "[data-testid='view-toggle-map']"
agent-browser wait "[data-testid='schedule-map']"

# Validate map structure
agent-browser is visible "[data-testid='schedule-map']"

# Screenshot map
agent-browser screenshot screenshots/ui-redesign/schedule-map.png
```

#### ABT-10.2: Map Markers
```bash
# From map view
agent-browser is visible "[data-testid='map-marker']"

# Click on marker
agent-browser click "[data-testid='map-marker']"
agent-browser wait "[data-testid='map-info-window']"

# Validate info window
agent-browser is visible "[data-testid='map-info-window']"

# Screenshot info window
agent-browser screenshot screenshots/ui-redesign/map-info-window.png
```

#### ABT-10.3: Map Legend
```bash
# From map view
agent-browser is visible "[data-testid='map-legend']"

# Screenshot legend
agent-browser snapshot -i
```

#### ABT-10.4: Map Filters
```bash
# From map view
agent-browser is visible "[data-testid='map-filters']"
agent-browser click "[data-testid='map-filters']"
agent-browser wait "[data-testid='map-filter-options']"

# Test filter selection
agent-browser click "[data-testid='filter-staff-1']"
agent-browser snapshot -i
```

#### ABT-10.5: Map Controls
```bash
# From map view
agent-browser is visible "[data-testid='map-controls']"

# Test zoom controls
agent-browser click "[data-testid='zoom-in-btn']"
agent-browser wait 300
agent-browser click "[data-testid='zoom-out-btn']"
agent-browser wait 300
```

#### ABT-10.6: Map Empty State
```bash
# Navigate to map with no data
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

# Switch to map view without generating
agent-browser click "[data-testid='view-toggle-map']"
agent-browser wait "[data-testid='map-empty-state']"

# Validate empty state
agent-browser is visible "[data-testid='map-empty-state']"

# Screenshot empty state
agent-browser screenshot screenshots/ui-redesign/map-empty-state.png
```

#### ABT-10.7: Map Loading State
```bash
# Trigger loading state
agent-browser open http://localhost:5173/schedule/generate
agent-browser wait --load networkidle

agent-browser click "[data-testid='generate-schedule-btn']"
# Capture loading state quickly
agent-browser snapshot -i
# Verify teal spinner
```

---

### ABT-11: AI Component Tests

#### ABT-11.1: AI Chat Interface
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Open AI chat (if available on dashboard)
agent-browser is visible "[data-testid='ai-chat']"

# Test chat input
agent-browser fill "[data-testid='ai-chat-input']" "What jobs are scheduled for today?"
agent-browser click "[data-testid='ai-send-btn']"

# Wait for response
agent-browser wait "[data-testid='ai-message']"

# Validate message styling
agent-browser snapshot -i
# Verify user message: teal-500 bg, AI message: slate-100 bg

# Screenshot chat
agent-browser screenshot screenshots/ui-redesign/ai-chat.png
```

#### ABT-11.2: AI Loading State
```bash
# Trigger AI loading
agent-browser fill "[data-testid='ai-chat-input']" "Generate a schedule"
agent-browser click "[data-testid='ai-send-btn']"

# Capture loading state
agent-browser is visible "[data-testid='ai-loading']"
agent-browser snapshot -i
# Verify teal spinner
```

#### ABT-11.3: AI Error State
```bash
# Trigger error (if possible)
# Validate error styling
agent-browser is visible "[data-testid='ai-error']"
agent-browser snapshot -i
# Verify red left-border alert style
```

#### ABT-11.4: Morning Briefing
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Validate morning briefing
agent-browser is visible "[data-testid='morning-briefing']"

# Screenshot briefing
agent-browser screenshot screenshots/ui-redesign/morning-briefing.png
```

#### ABT-11.5: AI Estimate Generator
```bash
# Navigate to estimate generator (if accessible)
agent-browser is visible "[data-testid='ai-estimate-generator']"

# Test form
agent-browser fill "[data-testid='estimate-description']" "Install new irrigation system"
agent-browser click "[data-testid='generate-estimate-btn']"

# Wait for result
agent-browser wait "[data-testid='estimate-result']"

# Screenshot
agent-browser screenshot screenshots/ui-redesign/ai-estimate.png
```

---

### ABT-12: Settings Tests

#### ABT-12.1: Settings Page Visual Validation
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate settings page structure
agent-browser is visible "[data-testid='settings-page']"

# Screenshot full settings
agent-browser screenshot screenshots/ui-redesign/settings-page.png --full
```

#### ABT-12.2: Profile Settings Section
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate profile section
agent-browser is visible "[data-testid='profile-settings']"

# Test profile form inputs
agent-browser click "[data-testid='profile-name-input']"
agent-browser snapshot -i
# Verify teal focus ring
```

#### ABT-12.3: Notification Preferences
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate notification section
agent-browser is visible "[data-testid='notification-settings']"

# Test toggle switches
agent-browser is visible "[data-testid='sms-toggle']"
agent-browser click "[data-testid='sms-toggle']"
agent-browser snapshot -i
# Verify teal checked state

agent-browser is visible "[data-testid='email-toggle']"
agent-browser click "[data-testid='email-toggle']"
```

#### ABT-12.4: Theme Toggle (Dark Mode)
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate theme section
agent-browser is visible "[data-testid='display-settings']"
agent-browser is visible "[data-testid='theme-toggle']"

# Test dark mode toggle
agent-browser click "[data-testid='theme-toggle']"
agent-browser wait 500

# Screenshot dark mode
agent-browser screenshot screenshots/ui-redesign/dark-mode.png --full

# Toggle back to light mode
agent-browser click "[data-testid='theme-toggle']"
agent-browser wait 500
```

#### ABT-12.5: Business Settings
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate business section
agent-browser is visible "[data-testid='business-settings']"

# Test form inputs
agent-browser click "[data-testid='company-name-input']"
agent-browser snapshot -i
```

#### ABT-12.6: Account Actions
```bash
agent-browser open http://localhost:5173/settings
agent-browser wait --load networkidle

# Validate account actions
agent-browser is visible "[data-testid='account-actions']"
agent-browser is visible "[data-testid='change-password-btn']"
agent-browser is visible "[data-testid='logout-btn']"

# Test change password button
agent-browser click "[data-testid='change-password-btn']"
agent-browser wait "[data-testid='change-password-dialog']"

# Close dialog
agent-browser click "[data-testid='close-dialog-btn']"
```

---

### ABT-13: Form Validation Tests

#### ABT-13.1: Required Field Validation
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Open add customer form
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"

# Submit empty form
agent-browser click "[data-testid='submit-btn']"

# Verify validation errors
agent-browser is visible "[data-testid='validation-error']"
agent-browser snapshot -i
# Verify error styling
```

#### ABT-13.2: Email Validation
```bash
# From customer form
agent-browser fill "[name='email']" "invalid-email"
agent-browser click "[data-testid='submit-btn']"

# Verify email validation error
agent-browser is visible "[data-testid='email-error']"
```

#### ABT-13.3: Phone Validation
```bash
# From customer form
agent-browser fill "[name='phone']" "123"
agent-browser click "[data-testid='submit-btn']"

# Verify phone validation error
agent-browser is visible "[data-testid='phone-error']"
```

---

### ABT-14: Modal/Dialog Tests

#### ABT-14.1: Modal Backdrop Click
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Open AI categorize modal
agent-browser click "[data-testid='ai-categorize-btn']"
agent-browser wait "[data-testid='ai-categorize-modal']"

# Click backdrop to close
agent-browser click "[data-testid='modal-backdrop']"

# Verify modal closed
agent-browser snapshot -i
```

#### ABT-14.2: Modal Escape Key
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Open modal
agent-browser click "[data-testid='ai-categorize-btn']"
agent-browser wait "[data-testid='ai-categorize-modal']"

# Press Escape to close
agent-browser press "Escape"

# Verify modal closed
agent-browser snapshot -i
```

#### ABT-14.3: Modal Close Button
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Open modal
agent-browser click "[data-testid='ai-categorize-btn']"
agent-browser wait "[data-testid='ai-categorize-modal']"

# Click close button
agent-browser click "[data-testid='close-modal-btn']"

# Verify modal closed
agent-browser snapshot -i
```

---

### ABT-15: Responsive Tests

#### ABT-15.1: Tablet Viewport
```bash
agent-browser set viewport 768 1024

agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Screenshot tablet view
agent-browser screenshot screenshots/ui-redesign/dashboard-tablet.png --full

agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
agent-browser screenshot screenshots/ui-redesign/customers-tablet.png --full
```

#### ABT-15.2: Mobile Viewport
```bash
agent-browser set viewport 375 812

agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Screenshot mobile view
agent-browser screenshot screenshots/ui-redesign/dashboard-mobile.png --full

agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle
agent-browser screenshot screenshots/ui-redesign/customers-mobile.png --full

# Reset viewport
agent-browser set viewport 1920 1080
```

---

### ABT-16: Hover State Tests

#### ABT-16.1: Button Hover States
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Test primary button hover
agent-browser hover "[data-testid='new-job-btn']"
agent-browser snapshot -i
# Verify bg-teal-600 on hover

# Test secondary button hover
agent-browser hover "[data-testid='view-schedule-btn']"
agent-browser snapshot -i
# Verify bg-slate-50 on hover
```

#### ABT-16.2: Card Hover States
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Test card hover
agent-browser hover "[data-testid='metrics-card']"
agent-browser snapshot -i
# Verify shadow-md on hover
```

#### ABT-16.3: Table Row Hover States
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Test row hover
agent-browser hover "[data-testid='customer-row']"
agent-browser snapshot -i
# Verify bg-slate-50/80 on hover
```

#### ABT-16.4: Navigation Hover States
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Test nav item hover (inactive item)
agent-browser hover "[data-testid='nav-customers']"
agent-browser snapshot -i
# Verify hover:text-slate-600 hover:bg-slate-50
```

---

### ABT-17: Focus State Tests

#### ABT-17.1: Input Focus States
```bash
agent-browser open http://localhost:5173/customers
agent-browser wait --load networkidle

# Open form
agent-browser click "[data-testid='add-customer-btn']"
agent-browser wait "[data-testid='customer-form']"

# Tab through inputs
agent-browser press "Tab"
agent-browser snapshot -i
# Verify teal focus ring

agent-browser press "Tab"
agent-browser snapshot -i

agent-browser press "Tab"
agent-browser snapshot -i
```

#### ABT-17.2: Button Focus States
```bash
agent-browser open http://localhost:5173/dashboard
agent-browser wait --load networkidle

# Focus on button
agent-browser focus "[data-testid='new-job-btn']"
agent-browser snapshot -i
# Verify focus ring visible
```

---

### ABT-18: Animation Tests

#### ABT-18.1: Page Entry Animation
```bash
agent-browser open http://localhost:5173/dashboard
# Capture immediately to see animation
agent-browser snapshot -i
# Verify animate-in fade-in slide-in-from-bottom-4

agent-browser open http://localhost:5173/customers
agent-browser snapshot -i
```

#### ABT-18.2: Modal Animation
```bash
agent-browser open http://localhost:5173/jobs
agent-browser wait --load networkidle

# Open modal and capture animation
agent-browser click "[data-testid='ai-categorize-btn']"
agent-browser snapshot -i
# Verify animate-in fade-in zoom-in
```

---

## Visual Validation Checklist

After implementation, validate each view using the test plan above. Mark each item as complete:

### Core Layout
- [ ] Sidebar displays with teal accent on active item
- [ ] Sidebar logo shows static "Grin's Irrigation" text with teal icon
- [ ] Sidebar user profile card at bottom with photo avatar
- [ ] Header has backdrop blur effect
- [ ] Header search input styled correctly
- [ ] Header notification bell with badge
- [ ] Header user avatar displays correctly

### Authentication
- [ ] Login page has teal branding
- [ ] Login form card has rounded-2xl corners
- [ ] Login inputs have teal focus ring
- [ ] Login button is teal-500
- [ ] Error alert has left border accent
- [ ] User menu dropdown styled correctly
- [ ] Logout button has destructive styling

### Dashboard
- [ ] Dashboard loads with new styling
- [ ] Stat cards show colored icon containers
- [ ] Stat cards have hover shadow effect
- [ ] Alert notifications have left border accent
- [ ] Recent jobs section styled correctly
- [ ] Job items have bg-slate-50 rounded-xl with hover effect
- [ ] Technician availability section styled
- [ ] Staff avatars show correctly

### List Views
- [ ] Customer list table has new styling
- [ ] Customer list toolbar with search/filter
- [ ] Customer list pagination styled
- [ ] Job list filters and badges work
- [ ] Job list status badges correct colors
- [ ] Staff list availability indicators display
- [ ] Invoice list status badges correct colors
- [ ] Appointment list styled correctly

### Detail Views
- [ ] Customer detail cards styled
- [ ] Job detail status display correct
- [ ] Staff detail card layout correct
- [ ] Invoice detail styled correctly
- [ ] Appointment detail styled correctly

### Forms & Modals
- [ ] All form inputs have teal focus ring
- [ ] All form labels uppercase tracking-wider
- [ ] All modals have backdrop blur
- [ ] All modals have rounded-2xl corners
- [ ] All modals have bg-slate-50/50 header/footer
- [ ] Create invoice dialog styled
- [ ] Payment dialog styled
- [ ] Clear day dialog styled

### AI Components
- [ ] AI chat card styled correctly
- [ ] AI chat message bubbles correct colors
- [ ] AI chat input area styled
- [ ] AI categorization modal styled
- [ ] AI loading states show teal spinner
- [ ] AI error states show left border alert
- [ ] Morning briefing styled correctly

### Schedule Generation
- [ ] Schedule generation page cards styled
- [ ] Date picker styled correctly
- [ ] Capacity overview card styled
- [ ] Jobs ready to schedule preview styled
- [ ] Schedule results styled correctly
- [ ] View toggle buttons styled
- [ ] Natural language input styled

### Map Components
- [ ] Map container styled correctly
- [ ] Map markers use staff colors
- [ ] Map info windows styled as cards
- [ ] Map legend styled correctly
- [ ] Map filters styled correctly
- [ ] Map controls styled correctly
- [ ] Map empty state styled
- [ ] Map loading state shows teal spinner

### Settings Page
- [ ] Settings page has full design
- [ ] Settings sections styled as cards
- [ ] Theme toggle works (dark mode)
- [ ] All toggles have teal checked state

### General
- [ ] All hover/transition effects work
- [ ] Loading states show teal spinner
- [ ] Error states display correctly
- [ ] Mobile responsive layout works
- [ ] All data-testid attributes preserved
- [ ] No console errors
- [ ] All existing tests pass

---

## Dependencies

### Font Addition
Add to `index.html`:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

### No New Package Dependencies
All styling uses existing Tailwind CSS utilities. No new npm packages required.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Only modify styling, preserve all data-testid attributes |
| Inconsistent styling | Follow reference design strictly, use design system tokens |
| Mobile responsiveness | Test all breakpoints with agent-browser |
| Accessibility | Maintain color contrast ratios, test focus states |
| Performance | Minimize CSS bundle size, use Tailwind utilities efficiently |
| Test failures | Run existing test suite after each phase |

---

## Success Criteria

1. **Visual Match**: UI closely matches `Re-Design-Visual.png`
2. **Functionality Preserved**: All existing features work identically
3. **Tests Pass**: All existing tests continue to pass
4. **Agent-Browser Validation**: All ABT tests pass
5. **Responsive**: Works on mobile, tablet, desktop
6. **Accessible**: Meets WCAG 2.1 AA standards
7. **Performance**: No degradation in load times
