# UI Redesign Requirements

## Overview

Phase 10 is a comprehensive visual redesign of the Grin's Irrigation Platform frontend. This phase focuses **exclusively on visual/UI changes** - no functionality will be modified. The goal is to transform the current interface into a modern, polished, professional design based on the reference implementation in `UI_RE-DESIGN/`.

## Reference Materials

- **Reference Folder**: `UI_RE-DESIGN/`
- **Visual Reference**: `UI_RE-DESIGN/Re-Design-Visual.png`
- **Component Reference**: `UI_RE-DESIGN/App.tsx`

---

## Functional Requirements

### FR-1: Design System Foundation

#### FR-1.1: Color Palette Implementation
**As a** user of the platform,
**I want** a consistent teal-centric color scheme throughout the application,
**So that** the interface feels modern, cohesive, and professionally branded.

**Acceptance Criteria:**
- Primary color is Teal-500 (`#14B8A6`) replacing current dark gray
- Primary hover state uses Teal-600 (`#0D9488`)
- Background color is Slate-50 (`#F8FAFC`) replacing pure white
- Card backgrounds are white with subtle shadow
- Text primary color is Slate-800 (`#1E293B`)
- Text secondary color is Slate-400/500
- Border color is Slate-100 (`#F1F5F9`)
- Active navigation uses Teal-50 background with Teal-500 left border indicator

#### FR-1.2: Typography System
**As a** user of the platform,
**I want** consistent, readable typography using the Inter font family,
**So that** text is easy to read and the interface feels polished.

**Acceptance Criteria:**
- Inter font is loaded from Google Fonts CDN
- Headings use bold weight with Slate-800 color
- Body text uses regular weight with Slate-600/700 color
- Labels use uppercase, tracking-wider, Slate-400 color
- Page titles are 2xl (24px), bold
- Font weights available: 300, 400, 500, 600, 700

#### FR-1.3: Spacing and Layout Standards
**As a** user of the platform,
**I want** consistent spacing and generous padding throughout the interface,
**So that** the UI feels spacious and elements are clearly separated.

**Acceptance Criteria:**
- Border radius uses rounded-2xl (16px) for cards, rounded-xl (12px) for buttons
- Card padding is p-6 (24px)
- Navigation items use px-6 py-4 padding
- Shadows use shadow-sm with hover:shadow-md transitions
- Borders use Slate-100 color (very subtle)
- Grid gap between cards is gap-8 (32px)
- Space between job items is space-y-4 (16px)
- Space between technician items is space-y-6 (24px)

#### FR-1.4: CSS Variables Update
**As a** developer,
**I want** updated CSS variables in index.css,
**So that** the new color scheme is applied consistently via Tailwind.

**Acceptance Criteria:**
- `--primary` set to teal-500 oklch value
- `--background` set to slate-50 oklch value
- `--card` set to white
- `--border` set to slate-100 oklch value
- `--muted` set to slate-50 oklch value
- `--accent` set to teal-50 oklch value
- `--radius` set to 0.75rem (larger default)
- Custom scrollbar styling with slate colors

#### FR-1.5: Tailwind Configuration
**As a** developer,
**I want** extended Tailwind configuration with custom colors and utilities,
**So that** the design system is available throughout the codebase.

**Acceptance Criteria:**
- Teal color palette (50-900) added to theme
- Inter font family configured as default sans
- Custom border-radius values (2xl, 3xl) defined
- Custom shadow-teal utility defined
- Animation utilities for spin-slow defined

---

### FR-2: Core Layout Components

#### FR-2.1: Sidebar Redesign
**As a** user navigating the platform,
**I want** a modern sidebar with clear visual hierarchy and active state indicators,
**So that** I can easily navigate between sections.

**Acceptance Criteria:**
- Fixed width of 256px (w-64)
- White background with right border (border-slate-100)
- Logo displays static teal icon (w-8 h-8 bg-teal-500 rounded-lg) with "Grin's Irrigation" text
- Logo text uses text-lg font-bold tracking-tight text-slate-900
- Navigation items are full-width, left-aligned with icons
- Active state shows Teal-50 background with Teal-500 left border indicator (w-1 rounded-r-full)
- Inactive items show text-slate-400 with hover:text-slate-600 hover:bg-slate-50
- User profile card at bottom with photo avatar (w-10 h-10 rounded-full border-2 border-white shadow-sm)
- User profile card has bg-slate-50 rounded-xl with hover:bg-slate-100 transition

#### FR-2.2: Header Redesign
**As a** user of the platform,
**I want** a modern header with search, notifications, and user avatar,
**So that** I can quickly access global functions.

**Acceptance Criteria:**
- Height of 64px (h-16)
- Backdrop blur effect (bg-white/80 backdrop-blur-md)
- Global search input on left side with Search icon
- Search input has transparent background, no border, placeholder-slate-400
- Notification bell on right side with badge indicator
- Badge shows rose-500 dot with white border
- User avatar on right side (w-8 h-8 rounded-full bg-teal-100 text-teal-700)
- Vertical separator (h-8 w-px bg-slate-200) between notification and avatar

#### FR-2.3: Page Header Component
**As a** user viewing any page,
**I want** consistent page headers with title, description, and action buttons,
**So that** I understand the context and can take primary actions.

**Acceptance Criteria:**
- Title uses text-2xl font-bold text-slate-800
- Description uses text-slate-500 mt-1
- Action buttons aligned to the right on desktop
- Responsive layout (flex-col on mobile, flex-row on desktop)
- Gap of 4 between elements

---

### FR-3: UI Component Library Updates

#### FR-3.1: Button Components
**As a** user interacting with the platform,
**I want** visually distinct primary and secondary buttons,
**So that** I can identify the main action on each screen.

**Acceptance Criteria:**
- Primary button: bg-teal-500 hover:bg-teal-600, text-white, px-5 py-2.5, rounded-lg, shadow-sm shadow-teal-200
- Secondary button: bg-white hover:bg-slate-50, border border-slate-200, text-slate-700, px-4 py-2.5, rounded-lg
- Both buttons support icon prop with gap-2 spacing
- Transition-all for smooth hover effects

#### FR-3.2: Card Components
**As a** user viewing content,
**I want** cards with consistent styling and hover effects,
**So that** content is clearly grouped and interactive elements are obvious.

**Acceptance Criteria:**
- White background
- Rounded-2xl corners (16px)
- Shadow-sm with hover:shadow-md transition
- Border: border-slate-100
- Padding: p-6 (24px)

#### FR-3.3: Badge/Status Components
**As a** user viewing job and customer status,
**I want** color-coded status badges that are easy to distinguish,
**So that** I can quickly understand the state of items.

**Acceptance Criteria:**
- Job Status - Completed: bg-emerald-100 text-emerald-700
- Job Status - Scheduled: bg-violet-100 text-violet-700
- Job Status - Approved: bg-blue-100 text-blue-700
- Job Category - Ready: bg-emerald-50 text-emerald-600 border-emerald-100
- Job Category - Needs Estimate: bg-amber-50 text-amber-600 border-amber-100
- Customer Tag - New Customer: bg-blue-50 text-blue-600 border-blue-100
- Customer Tag - Priority: bg-rose-50 text-rose-600 border-rose-100
- Customer Status - New: bg-teal-50 text-teal-600
- All badges use px-3 py-1 rounded-full text-xs font-medium

#### FR-3.4: Table Components
**As a** user viewing lists of data,
**I want** clean, readable tables with hover states and clear headers,
**So that** I can scan and interact with data efficiently.

**Acceptance Criteria:**
- White background card wrapper with rounded-2xl
- Toolbar with search input and filter buttons (p-4 border-b border-slate-100)
- Search input has Search icon, pl-10, bg-slate-50, rounded-lg, focus:ring-2 focus:ring-teal-500/20
- Header row: bg-slate-50/50, text-slate-500, text-xs, uppercase, tracking-wider
- Body rows: hover:bg-slate-50/80 transition-colors
- Dividers: divide-y divide-slate-50
- Pagination at bottom with "Showing X-Y of Z" text

#### FR-3.5: Input Components
**As a** user filling out forms,
**I want** inputs with clear focus states and consistent styling,
**So that** I know which field is active and the form feels cohesive.

**Acceptance Criteria:**
- Border: border-slate-200
- Focus: focus:border-teal-500 focus:ring-2 focus:ring-teal-100
- Background: bg-slate-50 or white depending on context
- Rounded-lg or rounded-xl corners
- Placeholder: placeholder-slate-400
- Text: text-slate-700 text-sm

#### FR-3.6: Modal/Dialog Components
**As a** user interacting with dialogs,
**I want** modern modals with backdrop blur and clear sections,
**So that** I can focus on the modal content.

**Acceptance Criteria:**
- Backdrop: bg-slate-900/20 backdrop-blur-sm
- Container: rounded-2xl, shadow-xl, overflow-hidden
- Header: p-6 border-b border-slate-100 bg-slate-50/50
- Footer: p-6 border-t border-slate-100 bg-slate-50/50
- Animation: animate-in fade-in zoom-in duration-200
- Close button: text-slate-400 hover:text-slate-600

#### FR-3.7: Alert Components
**As a** user receiving notifications,
**I want** alerts with clear visual hierarchy and action buttons,
**So that** I can understand the message and take action.

**Acceptance Criteria:**
- Left border accent (border-l-4) with appropriate color
- Icon in colored rounded-full container
- Title: text-slate-800 font-medium
- Description: text-slate-500 text-sm
- Action button on right side with matching color scheme
- Example: Amber alert uses border-amber-400, bg-amber-100 icon container, text-amber-600 button

---

### FR-4: Dashboard Page

#### FR-4.1: Dashboard Layout
**As a** business owner viewing the dashboard,
**I want** a comprehensive overview of today's operations,
**So that** I can quickly assess the state of the business.

**Acceptance Criteria:**
- Page header with greeting "Hello, Viktor! Here's what's happening today."
- Action buttons: "View Schedule" (secondary) and "New Job" (primary)
- Alerts section for overnight requests and important notifications
- Stats grid with 4 metric cards
- Two-column layout for Recent Jobs and Technician Availability
- Animation: animate-in fade-in slide-in-from-bottom-4 duration-500

#### FR-4.2: Stat Cards
**As a** business owner,
**I want** metric cards showing key business indicators,
**So that** I can monitor important numbers at a glance.

**Acceptance Criteria:**
- Icon in colored rounded-xl container (top-right)
- Icon colors: teal-500 (schedule), violet-500 (messages), emerald-500 (invoices), blue-500 (staff)
- Title: uppercase, tracking-wider, text-slate-400, text-sm
- Value: text-3xl font-bold text-slate-800
- Subtext: text-xs text-slate-400
- Card styling per FR-3.2

#### FR-4.3: Recent Jobs Section
**As a** business owner,
**I want** to see recent job activity,
**So that** I can track work progress.

**Acceptance Criteria:**
- Card with "Recent Jobs" header and "View All" link (text-teal-600)
- Job items: flex items-center justify-between p-4 bg-slate-50 rounded-xl
- Job items hover: hover:bg-slate-100 transition-colors cursor-pointer group
- Job icon container: bg-white p-3 rounded-lg shadow-sm group-hover:shadow text-teal-600
- Job title: font-semibold text-slate-800
- Job subtitle: text-xs text-slate-500 (date and ID)
- Status badge on right side

#### FR-4.4: Technician Availability Section
**As a** business owner,
**I want** to see staff availability status,
**So that** I can plan assignments.

**Acceptance Criteria:**
- Card with "Technician Availability" header and "Manage" link
- Staff items: space-y-6 with border-b border-slate-50 pb-4 last:border-0 last:pb-0
- Staff avatar: w-10 h-10 rounded-full bg-slate-200 text-slate-600 font-semibold text-sm (initials)
- Staff name: text-sm font-medium text-slate-800
- Staff time: text-xs text-slate-500
- Status indicator: w-2 h-2 rounded-full (emerald-500 for Available, amber-500 for On Job)
- Status text: text-xs font-medium text-slate-600

---

### FR-5: List View Pages

#### FR-5.1: Customer List
**As a** user managing customers,
**I want** a searchable, filterable customer table,
**So that** I can find and manage customer records.

**Acceptance Criteria:**
- Page header with "Add Customer" primary button
- Table toolbar with search, Filter button, Export button
- Columns: Name, Contact (phone + email), Source, Flags, Actions
- Name column: font-semibold text-slate-700
- Contact column: phone in text-sm text-slate-600, email in text-xs text-slate-400
- Flags column: status badges per FR-3.3
- Actions column: MoreHorizontal icon with hover:text-teal-600 hover:bg-teal-50
- Pagination per FR-3.4

#### FR-5.2: Job List
**As a** user managing jobs,
**I want** a job table with status filters and AI categorization,
**So that** I can track and manage job requests.

**Acceptance Criteria:**
- Page header with "AI Categorize" secondary button and "New Job" primary button
- Table toolbar with search and status dropdown filter
- Columns: Job Type, Status, Category, Priority, Amount, Created, Actions
- Status and Category columns use badges per FR-3.3
- Priority column: High uses bg-orange-50 text-orange-600, Normal uses bg-slate-100 text-slate-500
- Amount column: formatted currency or "Not quoted" in text-slate-400 italic
- AI Categorize button opens modal per FR-6.1

#### FR-5.3: Staff List
**As a** user managing staff,
**I want** a staff table with availability indicators,
**So that** I can see who is available for assignments.

**Acceptance Criteria:**
- Table with staff information and availability status
- Availability indicators using emerald/amber color scheme
- Staff avatars with initials

#### FR-5.4: Invoice List
**As a** user managing invoices,
**I want** an invoice table with status badges,
**So that** I can track payment status.

**Acceptance Criteria:**
- Status badges for Paid, Pending, Overdue, etc.
- Amount column with currency formatting
- Due date column with overdue highlighting

#### FR-5.5: Appointment List
**As a** user managing appointments,
**I want** an appointment table with date/time and status,
**So that** I can manage the schedule.

**Acceptance Criteria:**
- Date/time formatting
- Status badges
- Staff assignment display

---

### FR-6: AI Components

#### FR-6.1: AI Categorization Modal
**As a** user categorizing jobs,
**I want** an AI-powered categorization modal,
**So that** I can quickly classify job requests.

**Acceptance Criteria:**
- Modal header with Sparkles icon and "AI Job Categorization" title
- Description text explaining the feature
- Textarea for job description (h-32, rounded-xl, focus:ring-2 focus:ring-teal-100)
- AI Prediction Preview section: bg-teal-50 p-4 rounded-xl border border-teal-100
- Preview shows CheckCircle2 icon in bg-teal-100 p-2 rounded-lg
- Preview tags: bg-white text-teal-700 px-2 py-1 rounded text-xs border border-teal-100
- Footer with Cancel (secondary) and "Categorize Job" (primary with Sparkles icon) buttons

#### FR-6.2: AI Chat Interface
**As a** user interacting with the AI assistant,
**I want** a chat interface with distinct message bubbles,
**So that** I can have a conversation with the AI.

**Acceptance Criteria:**
- User messages: teal-500 background, white text
- AI messages: slate-100 background, slate-800 text
- AI icon: Sparkles in teal
- Input area with send button
- Loading state: teal spinner with "AI thinking..." text

#### FR-6.3: AI Loading and Error States
**As a** user waiting for AI responses,
**I want** clear loading and error indicators,
**So that** I know the system status.

**Acceptance Criteria:**
- Loading: teal spinner animation
- Error: red left-border alert style per FR-3.7

---

### FR-7: Authentication Components

#### FR-7.1: Login Page
**As a** user logging in,
**I want** a branded login page with teal accents,
**So that** the login experience matches the new design.

**Acceptance Criteria:**
- Background: slate-50
- Card: rounded-2xl, shadow-lg
- Logo: teal-500 accent
- Inputs: teal focus ring per FR-3.5
- Login button: teal-500 primary button
- Error alert: left border accent style

#### FR-7.2: User Menu
**As a** logged-in user,
**I want** a user menu dropdown with profile and logout options,
**So that** I can manage my session.

**Acceptance Criteria:**
- Avatar styling per FR-2.2
- Dropdown with rounded corners and shadow
- Logout button with destructive styling

---

### FR-8: Settings Page

#### FR-8.1: Settings Page Design
**As a** user managing preferences,
**I want** a comprehensive settings page,
**So that** I can customize my experience.

**Acceptance Criteria:**
- Profile Settings section: name, email, avatar
- Notification Preferences section: SMS, email, push toggles
- Display Settings section: theme toggle (light/dark mode)
- Business Settings section: company info, default pricing
- Integration Settings section: API keys, connected services
- Account Actions section: change password, logout
- Each section in a card per FR-3.2

---

### FR-9: Dark Mode Support

#### FR-9.1: Dark Mode Implementation
**As a** user who prefers dark interfaces,
**I want** a dark mode option,
**So that** I can use the platform comfortably in low-light conditions.

**Acceptance Criteria:**
- Theme toggle switch in Settings page
- ThemeProvider context for state management
- Dark mode CSS variables defined
- Preference stored in localStorage
- System preference respected as default
- Dark mode colors: background oklch(0.15 0.01 250), foreground oklch(0.95 0.005 250), card oklch(0.2 0.01 250)

---

### FR-10: Map Components

#### FR-10.1: Map Styling
**As a** user viewing the schedule map,
**I want** map components styled consistently with the new design,
**So that** the map integrates seamlessly with the UI.

**Acceptance Criteria:**
- Map container with consistent card styling
- Map controls match button styling (rounded-lg, shadow-sm)
- Info windows use card styling (rounded-xl, shadow-lg)
- Legend as floating card with staff color indicators
- Staff colors use diverse palette for differentiation (keep existing)
- Loading state: teal spinner
- Empty state: styled card
- Error state: alert styling

---

### FR-11: Schedule Components

#### FR-11.1: Schedule Generation Page
**As a** user generating schedules,
**I want** the schedule generation interface styled consistently,
**So that** the workflow feels cohesive.

**Acceptance Criteria:**
- Card layouts for each section
- Date picker with teal selection
- Capacity overview card
- Jobs ready to schedule preview table
- View toggle buttons styled
- Natural language input with chip styling

#### FR-11.2: Calendar View
**As a** user viewing the calendar,
**I want** calendar styling with teal accents,
**So that** selected dates and appointments are clear.

**Acceptance Criteria:**
- Teal-500 for selected dates
- Teal-50 for hover states
- Slate-100 borders between days
- Rounded corners on date cells
- Staff color indicators for appointments

---

### FR-12: Animation and Transitions

#### FR-12.1: Page Transitions
**As a** user navigating between pages,
**I want** smooth page transitions,
**So that** the interface feels responsive and polished.

**Acceptance Criteria:**
- Page entry: animate-in fade-in slide-in-from-bottom-4 duration-500
- Hover transitions: transition-all duration-200
- Card hover: hover:shadow-md transition-shadow

#### FR-12.2: Interactive Element Transitions
**As a** user interacting with elements,
**I want** smooth hover and focus transitions,
**So that** the interface feels responsive.

**Acceptance Criteria:**
- Buttons: transition-all on hover
- Cards: transition-shadow on hover
- Table rows: transition-colors on hover
- Navigation items: transition-all duration-200

---

## Non-Functional Requirements

### NFR-1: Functionality Preservation
**All existing functionality must remain unchanged.** This includes:
- API calls and data fetching
- State management (TanStack Query)
- Routing
- Form validation (Zod schemas)
- Business logic
- Data structures and types

### NFR-2: Test Compatibility
**All existing tests must continue to pass.** This includes:
- All `data-testid` attributes must be preserved
- Component behavior must remain identical
- Agent-browser validation scripts must work

### NFR-3: Responsive Design
**The interface must work on all screen sizes.**
- Desktop-first approach (primary users use desktop)
- Mobile responsiveness as secondary pass
- Breakpoints: md (768px), lg (1024px)

### NFR-4: Accessibility
**The interface must meet WCAG 2.1 AA standards.**
- Color contrast ratios maintained
- Focus states visible
- Screen reader compatibility

### NFR-5: Performance
**No degradation in load times or performance.**
- Minimize CSS bundle size
- Efficient use of Tailwind utilities
- No unnecessary re-renders

---

## Component Inventory Summary

| Category | Count |
|----------|-------|
| Core/Shared | 8 |
| UI Components (shadcn) | ~20 |
| Auth | 4 |
| Dashboard | 4 |
| Customers | 4 |
| Jobs | 5 |
| Staff | 2 |
| Invoices | 9 |
| Schedule (non-map) | 14 |
| Map | 15 |
| AI | 12 |
| Pages | 9 |
| **TOTAL** | **~106 components** |

---

## Success Criteria

1. **Visual Match**: UI closely matches `Re-Design-Visual.png`
2. **Functionality Preserved**: All existing features work identically
3. **Tests Pass**: All existing tests continue to pass
4. **Responsive**: Works on mobile, tablet, desktop
5. **Accessible**: Meets WCAG 2.1 AA standards
6. **Performance**: No degradation in load times
