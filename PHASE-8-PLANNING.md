# Phase 8 Planning - Schedule Management & Workflow Improvements

## Overview

Phase 8 focuses on improving the schedule management workflow by adding the ability to clear and reset schedules, plus a complete invoice management system. This addresses key user needs: the ability to start over when iterating on schedule generation, clear applied schedules from the database when rescheduling is needed, and streamline the invoicing workflow.

**PRIMARY FOCUS: Schedule Clear/Reset Functionality + Invoice Management**

---

## 🎯 PRIORITY 1: Schedule Clear & Reset Features

### Background & Problem Statement

Currently, when Viktor generates a schedule for a date:
1. He can generate a schedule and see the results (assigned/unassigned jobs)
2. He can apply the schedule to create appointments in the database
3. **BUT** there's no easy way to:
   - Clear the generated results and start over with different job selections
   - Clear an already-applied schedule from the database to regenerate

This creates friction when:
- The generated schedule isn't optimal and he wants to try different constraints
- He accidentally applied a schedule and needs to redo it
- He wants to reschedule a day due to weather, staff changes, etc.

### Solution: Two-Location Clear Functionality

We will implement clear functionality in **two locations**, each serving a different purpose:

| Location | Feature | What it Clears | Use Case |
|----------|---------|----------------|----------|
| **Generate Routes Tab** | Clear Results + Job Selection Controls | In-memory generated schedule | "I want to regenerate with different jobs/constraints" |
| **Schedule Tab** | Clear Day | Applied appointments from database | "I need to redo the schedule for this day" |

---

## Feature 1: Generate Routes Tab - Schedule Results & Job Selection Controls

### 1.1 Clear Results Button

**Purpose**: Clear the generated (in-memory) schedule results for the currently selected date, allowing the user to regenerate with different constraints or job selections.

**Button Details**:
- **Label**: "Clear Results"
- **Location**: In the Schedule Results section, near the "Apply Schedule" button
- **Icon**: `X` or `Trash2` icon
- **Variant**: `outline` or `ghost` (secondary action)

**Behavior**:
1. User clicks "Clear Results"
2. The generated schedule results are cleared (set to null)
3. The view returns to the job selection state
4. Job checkboxes remain in their current state (selected/deselected)
5. User can adjust constraints, job selections, and regenerate

**When Visible**: Only when schedule results are displayed (after generation)

**No Confirmation Needed**: This only clears in-memory data, not database records

---

### 1.2 Job Selection Controls (Select All / Deselect All)

**Purpose**: Provide quick controls to select or deselect all jobs in the job list, making it easier to start fresh or include everything.

**Button Details**:
- **Labels**: "Select All" | "Deselect All"
- **Location**: Above the job list, as text links or small buttons
- **Style**: Text links (e.g., `text-sm text-blue-600 hover:underline`)

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│  Jobs to Schedule                                           │
│  ─────────────────                                          │
│  [Select All] | [Deselect All]            32 jobs selected │
│                                                             │
│  ☑ Laura Perez - major_repair - Brooklyn Park              │
│  ☑ Amanda Lee - winterization - Eden Prairie               │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Behavior**:
- **Select All**: Checks all job checkboxes in the current filtered view
- **Deselect All**: Unchecks all job checkboxes

**No Confirmation Needed**: These are quick toggle actions

---

### 1.3 UI Mockup - Generate Routes Tab with New Controls

```
┌─────────────────────────────────────────────────────────────────┐
│  Generate Schedule                                              │
│  ────────────────                                               │
│                                                                 │
│  📅 Select Date: [Wednesday, January 28, 2026 ▼]               │
│                                                                 │
│  Scheduling Constraints (Optional)                              │
│  [                                                    ]         │
│  [Parse Constraints]  [Preview]  [Generate Schedule]            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Jobs to Schedule                                               │
│  ─────────────────                                              │
│  [Select All] | [Deselect All]                 32 jobs selected │
│                                                                 │
│  [Filter: Job Type ▼] [Filter: Priority ▼] [Filter: City ▼]   │
│                                                                 │
│  ☑ Laura Perez - major_repair - Brooklyn Park - 163 min        │
│  ☑ Amanda Lee - winterization - Eden Prairie - 92 min          │
│  ☑ Sarah Gonzalez - winterization - Maple Grove - 98 min       │
│  ...                                                            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Schedule Results for Wednesday, January 28, 2026               │
│  ─────────────────────────────────────────────                  │
│                                                                 │
│  [Clear Results]  [Explain Schedule]  [Apply Schedule]          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ✅ Assigned: 15  ⚠️ Unassigned: 17  🚗 Travel: 45m     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Assigned Jobs Section - Light Green]                          │
│  [Unassigned Jobs Section - Light Yellow]                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature 2: Schedule Tab - Clear Day

### 2.1 Clear Day Button & Dialog

**Purpose**: Delete all applied appointments for a specific date from the database, allowing the user to regenerate and reapply a schedule.

**Button Details**:
- **Label**: "Clear Day"
- **Location**: In the Schedule tab header/toolbar area
- **Icon**: `Trash2` or `CalendarX` icon
- **Variant**: `destructive` or `outline` with red text (indicates destructive action)

**Date Selection**:
- User can select which day to clear using a date picker
- Default to currently viewed/selected date in the calendar
- Date picker should be part of the Clear Day dialog or adjacent to the button

---

### 2.2 Clear Day Confirmation Dialog

**Purpose**: Confirm the destructive action before deleting appointments

**Dialog Content**:
```
┌─────────────────────────────────────────────────────────────┐
│  Clear Schedule for Wednesday, January 28, 2026?            │
│  ─────────────────────────────────────────────────          │
│                                                             │
│  ⚠️ This will delete 15 appointments for this date.        │
│                                                             │
│  The following jobs will be reset to "approved" status      │
│  and become available for rescheduling:                     │
│                                                             │
│  • Laura Perez - major_repair                               │
│  • Amanda Lee - winterization                               │
│  • Sarah Gonzalez - winterization                           │
│  • ... and 12 more                                          │
│                                                             │
│  A record of this action will be saved for audit purposes.  │
│                                                             │
│                          [Cancel]  [Clear Schedule]         │
└─────────────────────────────────────────────────────────────┘
```

**Dialog Elements**:
- **Title**: "Clear Schedule for [Date]?"
- **Warning Icon**: ⚠️ or AlertTriangle
- **Appointment Count**: Shows how many appointments will be deleted
- **Job List Preview**: Shows first few jobs that will be affected (with "and X more" if many)
- **Status Reset Notice**: Explains that jobs will be reset to "approved"
- **Audit Notice**: Informs user that action is logged for recovery
- **Cancel Button**: Closes dialog, no action taken
- **Clear Schedule Button**: Red/destructive variant, executes the clear

---

### 2.3 Clear Day Backend Behavior

**When "Clear Schedule" is confirmed**:

1. **Create Audit Log Entry**: Before deletion, save appointment data as JSON blob for potential recovery
   ```json
   {
     "action": "schedule.cleared",
     "schedule_date": "2026-01-28",
     "appointments_deleted": [
       {
         "id": "uuid-1",
         "job_id": "job-uuid-1",
         "staff_id": "staff-uuid-1",
         "scheduled_date": "2026-01-28",
         "time_window_start": "09:00",
         "time_window_end": "11:00",
         "status": "scheduled"
       },
       // ... more appointments
     ],
     "jobs_reset": ["job-uuid-1", "job-uuid-2", ...],
     "cleared_at": "2026-01-28T14:30:00Z",
     "cleared_by": "user-uuid"
   }
   ```

2. **Delete Appointments**: Delete all appointments for the specified date
   - Query: `DELETE FROM appointments WHERE scheduled_date = :date`
   - Hard delete (not soft delete)

3. **Reset Job Statuses**: Update associated jobs back to "approved" status
   - Only reset jobs with `status = 'scheduled'`
   - Jobs in "in_progress" or "completed" status are NOT reset
   - This makes the jobs available for rescheduling

4. **Return Response**:
   ```json
   {
     "success": true,
     "date": "2026-01-28",
     "appointments_deleted": 15,
     "jobs_reset": 15,
     "audit_log_id": "audit-uuid",
     "message": "Schedule cleared for January 28, 2026"
   }
   ```

5. **Refresh UI**: 
   - Calendar view refreshes to show empty day
   - Toast notification confirms success
   - "Recently Cleared" section updates (if visible)

---

### 2.4 Rollback Strategy: Audit Log & Recently Cleared Section

**Audit Log Table**:
```sql
CREATE TABLE schedule_clear_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_date DATE NOT NULL,
    appointments_data JSONB NOT NULL,  -- Full appointment data for recovery
    jobs_reset UUID[] NOT NULL,        -- Array of job IDs that were reset
    cleared_by UUID REFERENCES users(id),
    cleared_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_schedule_clear_audit_date ON schedule_clear_audit(schedule_date);
CREATE INDEX idx_schedule_clear_audit_cleared_at ON schedule_clear_audit(cleared_at);
```

**"Recently Cleared" Section in Schedule Tab**:
```
┌─────────────────────────────────────────────────────────────┐
│  Recently Cleared (Last 24 Hours)                           │
│  ─────────────────────────────────                          │
│                                                             │
│  📅 January 28, 2026 - 15 appointments cleared at 2:30 PM  │
│     [View Details] [Restore]                                │
│                                                             │
│  📅 January 27, 2026 - 8 appointments cleared at 9:15 AM   │
│     [View Details] [Restore]                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**View Details Modal**:
- Shows list of appointments that were deleted
- Shows which jobs were reset
- Shows who cleared and when

**Restore Functionality** (Optional - can be Phase 8 or future):
- Recreates appointments from audit log JSON
- Sets jobs back to "scheduled" status
- Useful for accidental clears

---

### 2.5 API Endpoint

**Endpoint**: `POST /api/v1/schedule/clear`

**Request**:
```json
{
  "schedule_date": "2026-01-28"
}
```

**Response**:
```json
{
  "success": true,
  "schedule_date": "2026-01-28",
  "appointments_deleted": 15,
  "jobs_reset": 15,
  "audit_log_id": "uuid-of-audit-entry",
  "message": "Schedule cleared successfully"
}
```

**Additional Endpoints**:
- `GET /api/v1/schedule/clear/recent` - Get recently cleared schedules (last 24 hours)
- `GET /api/v1/schedule/clear/{audit_id}` - Get details of a specific clear action
- `POST /api/v1/schedule/clear/{audit_id}/restore` - Restore a cleared schedule (optional)

---

### 2.6 UI Mockup - Schedule Tab with Clear Day

```
┌─────────────────────────────────────────────────────────────────┐
│  Schedule                                                       │
│  ────────                                                       │
│                                                                 │
│  [◀ Prev Week]  January 27 - February 2, 2026  [Next Week ▶]   │
│                                                                 │
│  [Calendar View] [List View] [Map View]     [Clear Day 🗑️]     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Mon 27  │  Tue 28  │  Wed 29  │  Thu 30  │  Fri 31    │   │
│  │          │          │          │          │            │   │
│  │  3 appts │  15 appts│  0 appts │  8 appts │  12 appts  │   │
│  │          │          │          │          │            │   │
│  │  [...]   │  [...]   │          │  [...]   │  [...]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Recently Cleared (Last 24 Hours)                       │   │
│  │  📅 Jan 28 - 15 appts cleared at 2:30 PM [View Details] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technical Implementation Details

### Frontend Components to Create/Modify

| Component | Location | Changes |
|-----------|----------|---------|
| `ScheduleResults.tsx` | Generate Routes | Add "Clear Results" button |
| `JobsToScheduleList.tsx` | Generate Routes | Add "Select All" / "Deselect All" links |
| `ScheduleGenerationPage.tsx` | Generate Routes | Wire up clear results handler |
| `SchedulePage.tsx` | Schedule Tab | Add "Clear Day" button |
| `ClearDayDialog.tsx` | Schedule Tab | New confirmation dialog component |
| `RecentlyClearedSection.tsx` | Schedule Tab | New component showing recent clears |

### Backend Endpoints to Create

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/schedule/clear` | POST | Clear appointments for a date, reset job statuses |
| `/api/v1/schedule/clear/recent` | GET | Get recently cleared schedules |
| `/api/v1/schedule/clear/{audit_id}` | GET | Get details of a clear action |

### Backend Services to Modify

| Service | Changes |
|---------|---------|
| `AppointmentService` | Add `clear_schedule_for_date(date)` method |
| `JobService` | Add `reset_jobs_to_approved(job_ids)` method |

### Database Operations

```sql
-- Create audit log entry (before deletion)
INSERT INTO schedule_clear_audit (schedule_date, appointments_data, jobs_reset, cleared_by)
VALUES (:date, :appointments_json, :job_ids, :user_id);

-- Clear appointments for a date
DELETE FROM appointments WHERE scheduled_date = '2026-01-28';

-- Reset job statuses (only 'scheduled' jobs)
UPDATE jobs SET status = 'approved' WHERE id IN (
  SELECT job_id FROM appointments WHERE scheduled_date = '2026-01-28'
) AND status = 'scheduled';
```

---

## Implementation Phases

### Phase 8A: Generate Routes - Clear Results & Job Selection (Frontend Only)

**Tasks**:
1. Add "Clear Results" button to `ScheduleResults.tsx`
2. Add `onClearResults` handler to `ScheduleGenerationPage.tsx`
3. Add "Select All" / "Deselect All" links to job list
4. Wire up select/deselect handlers
5. Test clearing results and regenerating

**Effort**: ~2-3 hours
**No backend changes needed** - all frontend state management

---

### Phase 8B: Schedule Tab - Clear Day (Backend + Frontend)

**Tasks**:
1. Create `schedule_clear_audit` table migration
2. Create `POST /api/v1/schedule/clear` endpoint
3. Implement `clear_schedule_for_date()` in AppointmentService
4. Implement job status reset logic (only 'scheduled' jobs)
5. Create audit log entry before deletion
6. Create `ClearDayDialog.tsx` component
7. Add "Clear Day" button to Schedule tab
8. Wire up dialog and API call
9. Add success/error toast notifications
10. Test full flow: clear → verify appointments deleted → verify jobs reset → verify audit log

**Effort**: ~4-6 hours

---

### Phase 8C: Recently Cleared Section & Testing

**Tasks**:
1. Create `GET /api/v1/schedule/clear/recent` endpoint
2. Create `RecentlyClearedSection.tsx` component
3. Add "View Details" modal for audit entries
4. Unit tests for clear schedule endpoint
5. Integration tests for job status reset
6. Frontend tests for dialog and button interactions
7. Edge case handling (no appointments to clear, etc.)
8. Error handling and user feedback

**Effort**: ~3-4 hours

---

## Summary of All Buttons/Controls

### Generate Routes Tab

| Control | Type | Location | Action |
|---------|------|----------|--------|
| **Clear Results** | Button | Schedule Results section | Clears generated schedule, returns to job selection |
| **Select All** | Text Link | Above job list | Checks all job checkboxes |
| **Deselect All** | Text Link | Above job list | Unchecks all job checkboxes |

### Schedule Tab

| Control | Type | Location | Action |
|---------|------|----------|--------|
| **Clear Day** | Button | Tab header/toolbar | Opens date picker + confirmation dialog |
| **Date Picker** | Picker | In Clear Day dialog | Select which date to clear |
| **Confirmation Dialog** | Modal | Overlay | Shows appointment count, confirms deletion |
| **Recently Cleared** | Section | Below calendar | Shows recent clear actions with View Details |

---

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Should Clear Results also deselect jobs? | **No** - Keep them separate. Clear Results only clears the generated schedule. Deselect All is a separate action. |
| Should Clear Day have its own date picker? | **Yes** - User should be able to select any date to clear, not just the currently viewed date. |
| Should clearing reset job statuses? | **Yes** - Jobs should be reset to "approved" so they're available for rescheduling. |
| Should we support clearing date ranges? | **Future** - Start with single date, can add range support later if needed. |
| Soft delete vs hard delete? | **Hard delete** - With audit log for recovery if needed. |

---

## Success Criteria

| Feature | Success Metric |
|---------|----------------|
| Clear Results | User can clear generated schedule and regenerate without page refresh |
| Select All / Deselect All | User can quickly toggle all jobs with one click |
| Clear Day | User can clear an applied schedule and see jobs become available again |
| Job Status Reset | Jobs return to "approved" status after clearing |
| Confirmation Dialog | User sees clear warning before destructive action |
| Audit Log | All clear actions are logged with full appointment data |
| Recently Cleared | User can see recent clears and view details |

---


## 🎯 PRIORITY 2: Invoice Management System

### Background & Problem Statement

From Viktor's business requirements document:

> "Manually having to go through all the calendar notes and updating the spreadsheet is a huge waste of time... Having to grab a template and type in all the information about a client and then sending them the invoice wastes a lot of time."

Currently, Viktor:
1. Manually writes invoices using a template after job completion
2. Sends invoices via text message the following day
3. Tracks payment status in a spreadsheet (amount due, invoice sent date, amount paid)
4. Follows up weekly on past-due invoices
5. Highlights past-due invoices in red for visual tracking

**Pain Points**:
- 5+ minutes per invoice to create and send
- Manual tracking of payment status across spreadsheet columns
- Easy to forget follow-ups during busy season
- No automated reminders for past-due invoices
- Lien eligibility tracking is manual (45-day warning, 120-day filing)

### Solution: Invoice Management Feature

A complete invoice system that:
1. **Manually generates** invoices from completed jobs (button click from Job detail page)
2. Sends invoices via SMS/email
3. Tracks payment status with visual indicators
4. Supports manual reminder sending (3, 7, 14 days past due)
5. Tracks lien eligibility for installations/major work with dashboard widget

---

### Job Model Update: `payment_collected_on_site` Field

**New Field**: Add `payment_collected_on_site: bool` to the Job model to track whether payment was collected during the service visit.

**Purpose**: This field determines whether an invoice needs to be generated:
- `payment_collected_on_site = True` → No invoice needed, job is paid
- `payment_collected_on_site = False` → Invoice should be generated

**Schema Update**:
```python
class Job(Base):
    # ... existing fields ...
    
    # Payment tracking
    payment_collected_on_site: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether payment was collected during the service visit"
    )
```

**Migration**:
```sql
ALTER TABLE jobs ADD COLUMN payment_collected_on_site BOOLEAN NOT NULL DEFAULT FALSE;
```

**UI Integration**:
- Job completion workflow includes checkbox: "Payment collected on-site?"
- If checked, no "Generate Invoice" button appears
- If unchecked, "Generate Invoice" button is visible on Job detail page

---

### Invoice Generation: Manual Process

**IMPORTANT**: Invoice generation is a **manual process** triggered by clicking a button, NOT automatic.

**Workflow**:
1. Technician completes job and marks `payment_collected_on_site` (yes/no)
2. If payment NOT collected on-site, job detail page shows "Generate Invoice" button
3. Admin clicks "Generate Invoice" button
4. Invoice form opens with pre-populated data from job
5. Admin reviews/adjusts line items if needed
6. Admin clicks "Create Invoice" to save
7. Admin can then "Send Invoice" to customer

**Why Manual**:
- Viktor wants to review each invoice before sending
- Some jobs may have adjustments or special pricing
- Prevents accidental invoice generation
- Gives admin control over timing

---

### Invoice Model Design

#### Database Schema

```sql
CREATE TABLE invoices (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    job_id UUID NOT NULL REFERENCES jobs(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    
    -- Invoice identification
    invoice_number VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "INV-2026-0001"
    
    -- Amounts
    amount DECIMAL(10, 2) NOT NULL,              -- Base amount
    late_fee_amount DECIMAL(10, 2) DEFAULT 0,   -- Late fee (if applicable)
    total_amount DECIMAL(10, 2) NOT NULL,       -- amount + late_fee
    
    -- Dates
    invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,                      -- Default: invoice_date + 14 days
    
    -- Status workflow: draft → sent → paid | overdue → lien_warning → lien_filed
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    
    -- Payment tracking
    payment_method VARCHAR(50),                  -- cash, check, venmo, zelle, stripe
    payment_reference VARCHAR(255),              -- Transaction ID, check number
    paid_at TIMESTAMP WITH TIME ZONE,
    paid_amount DECIMAL(10, 2),                  -- For partial payments
    
    -- Reminder tracking
    reminder_count INTEGER DEFAULT 0,
    last_reminder_sent TIMESTAMP WITH TIME ZONE,
    
    -- Lien tracking (for installations/major work)
    lien_eligible BOOLEAN DEFAULT FALSE,
    lien_warning_sent TIMESTAMP WITH TIME ZONE,  -- 45-day warning sent date
    lien_filed_date DATE,                        -- 120-day filing date
    
    -- Line items (JSON for flexibility)
    line_items JSONB,
    -- Example: [{"description": "Spring Startup - 8 zones", "quantity": 1, "unit_price": 120.00}]
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_job ON invoices(job_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_invoice_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_lien_eligible ON invoices(lien_eligible) WHERE lien_eligible = TRUE;
```

#### Invoice Status Enum

```python
class InvoiceStatus(str, Enum):
    """Invoice status workflow."""
    DRAFT = "draft"           # Created but not sent
    SENT = "sent"             # Sent to customer
    VIEWED = "viewed"         # Customer viewed (if portal exists)
    PAID = "paid"             # Payment received in full
    PARTIAL = "partial"       # Partial payment received
    OVERDUE = "overdue"       # Past due date
    LIEN_WARNING = "lien_warning"  # 45-day warning sent
    LIEN_FILED = "lien_filed"      # Lien filed (120 days)
    CANCELLED = "cancelled"   # Invoice cancelled
```

#### SQLAlchemy Model

```python
class Invoice(Base):
    """Invoice model for billing and payment tracking.
    
    Tracks invoices from creation through payment collection,
    including manual reminders and lien eligibility for
    installations and major work.
    """
    
    __tablename__ = "invoices"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Foreign keys
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
    )
    
    # Invoice identification
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    
    # Amounts
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    late_fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        server_default="0",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    
    # Dates
    invoice_date: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        server_default="draft",
    )
    
    # Payment tracking
    payment_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    payment_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    
    # Reminder tracking
    reminder_count: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
    )
    last_reminder_sent: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # Lien tracking
    lien_eligible: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
    )
    lien_warning_sent: Mapped[datetime | None] = mapped_column(nullable=True)
    lien_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Line items
    line_items: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="invoices")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
```

---

### Business Rules

#### Invoice Creation
- Invoices are created **manually** when admin clicks "Generate Invoice" on a completed job
- Only jobs with `payment_collected_on_site = False` show the "Generate Invoice" button
- Invoice number format: `INV-{YEAR}-{SEQUENCE}` (e.g., `INV-2026-0001`)
- Default due date: 14 days from invoice date
- Special cases (corporations): 30 days from invoice date

#### Payment Methods Supported
| Method | Reference Field Usage |
|--------|----------------------|
| Cash | "Cash" |
| Check | Check number |
| Venmo | Venmo transaction ID or username |
| Zelle | Zelle confirmation or email |
| Stripe | Stripe payment intent ID (future) |

#### Reminder Schedule (Manual Triggers)
| Days Past Due | Action |
|---------------|--------|
| 3 days | First reminder - admin clicks "Send Reminder" button |
| 7 days | Second reminder - admin clicks "Send Reminder" button |
| 14 days | Third reminder - admin clicks "Send Reminder" button + phone call flag |
| 45 days | Lien warning - admin clicks "Send Lien Warning" button (if eligible) |
| 120 days | Lien filing deadline - admin manually files lien |

**Note**: All reminders are **manual triggers**, not automated cron jobs. Admin decides when to send each reminder.

#### Lien Eligibility
Per Viktor's business requirements:
- **Lien-eligible**: New system installations (`installation`), major repairs/updates (`major_repair`)
- **Not lien-eligible**: Seasonal services (startups, winterizations), minor repairs
- **45-day rule**: Must notify customer of intent to file lien
- **120-day rule**: Must file lien within 120 days of work completion

---

### Lien Tracking: Dashboard Widget & Manual Triggers

#### Dashboard Widget: "Lien Deadlines Approaching"

**Purpose**: Show Viktor which invoices are approaching lien deadlines so he can take action.

**Widget Design**:
```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Lien Deadlines Approaching                              │
│  ─────────────────────────────                              │
│                                                             │
│  45-Day Warning Due (send lien notice):                     │
│  • INV-2026-0042 - Johnson Installation - $4,500            │
│    Due in 3 days (Jan 31) [Send Warning]                    │
│  • INV-2026-0038 - Smith Major Repair - $1,200              │
│    Due in 7 days (Feb 4) [Send Warning]                     │
│                                                             │
│  120-Day Filing Deadline:                                   │
│  • INV-2026-0015 - Williams Installation - $8,200           │
│    Filing deadline: Feb 15 (18 days) [Mark Filed]           │
│                                                             │
│  [View All Lien-Eligible Invoices]                          │
└─────────────────────────────────────────────────────────────┘
```

**Widget Features**:
- Shows invoices approaching 45-day warning deadline
- Shows invoices approaching 120-day filing deadline
- Quick action buttons: "Send Warning", "Mark Filed"
- Link to filtered invoice list showing all lien-eligible invoices

#### Lien Tracking Fields

| Field | Purpose |
|-------|---------|
| `lien_eligible` | Boolean - set based on job type (installation, major_repair) |
| `lien_warning_sent` | Timestamp - when 45-day warning was sent |
| `lien_filed_date` | Date - when lien was actually filed |

#### Lien Workflow (All Manual)

1. **Invoice Created**: System auto-sets `lien_eligible = True` if job type is `installation` or `major_repair`
2. **45-Day Approaching**: Dashboard widget shows invoice in "45-Day Warning Due" section
3. **Admin Sends Warning**: Clicks "Send Warning" button → sends notice → sets `lien_warning_sent` timestamp
4. **120-Day Approaching**: Dashboard widget shows invoice in "120-Day Filing Deadline" section
5. **Admin Files Lien**: Clicks "Mark Filed" button → sets `lien_filed_date` → invoice status becomes `lien_filed`

**No Cron Jobs**: All lien tracking is manual. The dashboard widget surfaces deadlines, but admin takes all actions.

---

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/invoices` | GET | List invoices with filters (status, customer, date range, lien_eligible) |
| `/api/v1/invoices` | POST | Create new invoice |
| `/api/v1/invoices/{id}` | GET | Get invoice details |
| `/api/v1/invoices/{id}` | PUT | Update invoice |
| `/api/v1/invoices/{id}` | DELETE | Delete/cancel invoice |
| `/api/v1/invoices/{id}/send` | POST | Send invoice to customer (SMS/email) |
| `/api/v1/invoices/{id}/payment` | POST | Record payment |
| `/api/v1/invoices/{id}/reminder` | POST | Send payment reminder |
| `/api/v1/invoices/{id}/lien-warning` | POST | Send 45-day lien warning |
| `/api/v1/invoices/{id}/lien-filed` | POST | Mark lien as filed |
| `/api/v1/invoices/overdue` | GET | List overdue invoices |
| `/api/v1/invoices/lien-deadlines` | GET | Get invoices approaching lien deadlines |
| `/api/v1/invoices/generate-from-job/{job_id}` | POST | Generate invoice from completed job |

---

### Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `InvoiceList.tsx` | `features/invoices/` | List invoices with status filters |
| `InvoiceDetail.tsx` | `features/invoices/` | View/edit invoice details |
| `InvoiceForm.tsx` | `features/invoices/` | Create/edit invoice |
| `PaymentDialog.tsx` | `features/invoices/` | Record payment modal |
| `InvoiceStatusBadge.tsx` | `features/invoices/` | Color-coded status indicator |
| `LienDeadlinesWidget.tsx` | `features/dashboard/` | Dashboard widget for lien deadlines |
| `OverdueInvoicesCard.tsx` | `features/dashboard/` | Dashboard widget for overdue invoices |
| `GenerateInvoiceButton.tsx` | `features/jobs/` | Button on Job detail page |

### UI Organization: Separate Invoices Tab

**Decision**: Invoices will have a **dedicated tab in the sidebar navigation**, not be buried within Jobs.

**Rationale**:
1. **Viktor's workflow**: He needs to see all overdue invoices at once for follow-up, not hunt through individual jobs
2. **Payment tracking**: He tracks payments across all customers, not per-job
3. **Lien management**: He needs to see all lien-eligible invoices approaching deadlines
4. **Scalability**: During busy season with 150+ jobs/week, a dedicated invoice view is essential

**Navigation Structure**:
```
Dashboard
Customers
Jobs
Schedule
Staff
Invoices  ← New dedicated tab
```

**Access Points**:
- **Sidebar**: Direct access to full invoice list with filtering
- **Job Detail Page**: "Generate Invoice" button (only if `payment_collected_on_site = False`)
- **Dashboard**: "Overdue Invoices" widget + "Lien Deadlines" widget

#### Status Badge Colors

| Status | Color | Hex |
|--------|-------|-----|
| Draft | Gray | `#6B7280` |
| Sent | Blue | `#3B82F6` |
| Paid | Green | `#10B981` |
| Partial | Yellow | `#F59E0B` |
| Overdue | Red | `#EF4444` |
| Lien Warning | Orange | `#F97316` |
| Lien Filed | Dark Red | `#991B1B` |

---

### Implementation Phases

#### Phase 8G: Invoice Model & Basic CRUD (4-5 hours)

**Tasks**:
1. Add `payment_collected_on_site` field to Job model (migration)
2. Create `InvoiceStatus` enum in `models/enums.py`
3. Create `Invoice` SQLAlchemy model
4. Create Alembic migration for `invoices` table
5. Create `InvoiceCreate`, `InvoiceUpdate`, `InvoiceResponse` Pydantic schemas
6. Create `InvoiceRepository` with CRUD operations
7. Create `InvoiceService` with business logic
8. Create `POST/GET/PUT/DELETE /api/v1/invoices` endpoints
9. Add relationship to Job and Customer models
10. Write unit tests for service layer

**Deliverables**:
- Working Invoice model with database table
- `payment_collected_on_site` field on Job model
- Full CRUD API endpoints
- Unit tests passing

---

#### Phase 8H: Invoice Generation & Payment Recording (3-4 hours)

**Tasks**:
1. Implement `generate_invoice_from_job()` in InvoiceService
2. Implement invoice number auto-generation (`INV-2026-0001` format)
3. Implement `record_payment()` with partial payment support
4. Add `POST /api/v1/invoices/generate-from-job/{job_id}` endpoint
5. Add `POST /api/v1/invoices/{id}/payment` endpoint
6. Add "Generate Invoice" button to Job detail page (conditional on `payment_collected_on_site`)
7. Write integration tests

**Deliverables**:
- Manual invoice generation from completed jobs
- Record payments with method tracking
- Invoice number sequence working

---

#### Phase 8I: Frontend Invoice Management (4-5 hours)

**Tasks**:
1. Create `InvoiceList.tsx` with status filtering
2. Create `InvoiceDetail.tsx` with payment history
3. Create `InvoiceForm.tsx` for manual invoice creation
4. Create `PaymentDialog.tsx` for recording payments
5. Create `InvoiceStatusBadge.tsx` component
6. Add Invoice navigation to sidebar
7. Add "Generate Invoice" button to Job detail page
8. Add overdue invoices widget to Dashboard

**Deliverables**:
- Full invoice management UI
- Visual status indicators
- Dashboard integration

---

#### Phase 8J: Lien Tracking & Dashboard Widget (3-4 hours)

**Tasks**:
1. Implement `check_lien_eligibility()` based on job type (installation, major_repair)
2. Implement `send_lien_warning()` for 45-day notification (manual trigger)
3. Implement `mark_lien_filed()` for 120-day filing (manual trigger)
4. Add `POST /api/v1/invoices/{id}/lien-warning` endpoint
5. Add `POST /api/v1/invoices/{id}/lien-filed` endpoint
6. Add `GET /api/v1/invoices/lien-deadlines` endpoint
7. Create `LienDeadlinesWidget.tsx` for dashboard
8. Add lien warning indicators to invoice list/detail
9. Write tests for lien tracking logic

**Deliverables**:
- Lien eligibility auto-detection
- Dashboard widget showing approaching deadlines
- Manual lien warning and filing tracking
- `lien_warning_sent` and `lien_filed_date` audit fields

---

#### Phase 8K: Reminders (Manual Triggers) (2-3 hours)

**Tasks**:
1. Implement `send_reminder()` in InvoiceService (manual trigger)
2. Add `POST /api/v1/invoices/{id}/reminder` endpoint
3. Add `GET /api/v1/invoices/overdue` endpoint
4. Create reminder tracking in UI (reminder count, last sent)
5. Add "Send Reminder" button to invoice detail page
6. Write tests for reminder logic

**Deliverables**:
- Manual reminder sending
- Reminder count tracking
- Overdue invoice list

---

### Summary: Invoice Implementation

| Phase | Focus | Effort |
|-------|-------|--------|
| Phase 8G | Model, migration, CRUD API | 4-5 hours |
| Phase 8H | Generation, payment recording | 3-4 hours |
| Phase 8I | Frontend UI | 4-5 hours |
| Phase 8J | Lien tracking, dashboard widget | 3-4 hours |
| Phase 8K | Reminders (manual) | 2-3 hours |
| **Total** | **Complete Invoice System** | **16-21 hours** |

---

### Future Enhancements (Not in Phase 8)

- **Stripe Integration**: Accept credit card payments online
- **Automated Reminders**: Cron job for automatic reminder sending (Phase 9+)
- **Invoice PDF Generation**: Generate PDF invoices for email/print
- **Customer Portal**: Allow customers to view and pay invoices online
- **QuickBooks Integration**: Sync invoices with accounting software
- **Late Fee Automation**: Auto-calculate and apply late fees

---

## Phase 8 Total Effort

| Priority | Feature | Effort |
|----------|---------|--------|
| Priority 1 | Schedule Clear/Reset | 9-13 hours |
| Priority 2 | Invoice Management | 16-21 hours |
| **Total** | **All Phase 8 Features** | **25-34 hours** |

---

## Recommended Implementation Order

1. **Phase 8A-8C**: Schedule Clear/Reset (easiest, immediate user value)
2. **Phase 8G-8H**: Invoice Model + Generation (high business value)
3. **Phase 8I**: Invoice Frontend (complete the invoice feature)
4. **Phase 8J**: Lien Tracking & Dashboard Widget (important for compliance)
5. **Phase 8K**: Reminders (polish)

This order maximizes value delivery with the most impactful features first.

---


## 📝 Brainstorming Session & Final Decisions (January 28, 2026)

This section documents the analysis, recommendations, and final decisions made during the planning review session.

---

### Question 1: Job Status Reset Scope

**Original Question**: Should we only reset jobs that are currently in "scheduled" status, or all jobs that had appointments on that date regardless of current status?

**User Decision**: Reset only jobs that are currently in "scheduled" status.

**Rationale**:

1. **Data Integrity**: Jobs that have progressed to "in_progress" or "completed" represent real work that has happened. Resetting them would lose that business context.

2. **Workflow Safety**: If a technician has already started or completed a job, we shouldn't automatically revert it just because the admin is clearing the schedule.

3. **Edge Cases Handled**:
   - Job was scheduled → appointment deleted → job goes back to "approved" ✅
   - Job was in_progress → appointment deleted → job stays "in_progress" (tech is working on it) ✅
   - Job was completed → appointment deleted → job stays "completed" (work is done) ✅

4. **Implementation**:
```python
# Only reset jobs with status = 'scheduled'
UPDATE jobs SET status = 'approved' 
WHERE id IN (
    SELECT job_id FROM appointments WHERE scheduled_date = :date
) AND status = 'scheduled';
```

**Final Decision**: ✅ Reset only jobs with `status = 'scheduled'`

---

### Question 2: Invoice Number Sequence

**Original Question**: How should invoice numbers be generated? Global sequence, per-year, database sequence?

**Decision**: Use a **PostgreSQL sequence with year prefix** for thread-safe, gap-free invoice numbering.

**Rationale**:
1. **Thread Safety**: PostgreSQL sequences are atomic and handle concurrent requests without duplicates.
2. **Year Prefix**: Makes invoices easy to organize and search by year.
3. **No Gaps**: Using `SERIAL` or application-level counters can create gaps on rollback; sequences are more reliable.
4. **Year Rollover**: Reset sequence at year start for clean numbering.

**Implementation**:

```sql
-- Create sequence for invoice numbers
CREATE SEQUENCE invoice_number_seq START 1;

-- Function to generate invoice number
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS VARCHAR(50) AS $$
DECLARE
    current_year INTEGER;
    seq_val INTEGER;
BEGIN
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    seq_val := nextval('invoice_number_seq');
    RETURN 'INV-' || current_year || '-' || LPAD(seq_val::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;
```

**Final Decision**: ✅ PostgreSQL sequence with year prefix, format `INV-2026-0001`

---

### Question 3: Invoice Relationship - Job ID vs Appointment ID

**Original Question**: Should invoices be linked to specific appointments, or just to jobs?

**Decision**: Link to **Job ID only**, not Appointment ID.

**Rationale**:

1. **Business Logic**: An invoice is for the **work performed** (the job), not the **time slot** (the appointment). If a job is rescheduled, the invoice should still be valid.

2. **One-to-One Relationship**: In most cases, one job = one invoice. The job contains all the pricing and service information needed.

3. **Rescheduling Scenario**:
   - Job scheduled for Monday → Appointment A created
   - Customer reschedules to Wednesday → Appointment A deleted, Appointment B created
   - Work completed → Invoice created for Job (not tied to either appointment)
   - Invoice remains valid regardless of appointment changes

4. **Multiple Appointments Edge Case**: If a job spans multiple appointments (multi-day installation), the invoice is still for the job, not individual appointments.

5. **Simplicity**: Fewer foreign keys = simpler queries and less chance of orphaned records.

**Final Decision**: ✅ Link to Job ID only, not Appointment ID

---

### Question 4: Invoice Line Items Structure

**Original Question**: Should we validate line items with a Pydantic model, or keep it flexible? Should `total` be calculated or stored?

**Decision**: Use a **Pydantic model for validation** with **calculated totals**.

**Rationale**:

1. **Data Integrity**: Validating line items prevents malformed data from entering the database.

2. **Calculated Totals**: Storing `line_total` per item is redundant and can lead to inconsistencies. Calculate on read.

3. **Flexibility**: JSONB still allows schema evolution, but Pydantic ensures current data is valid.

**Implementation**:

```python
from pydantic import BaseModel, Field, computed_field
from decimal import Decimal
from typing import List

class InvoiceLineItem(BaseModel):
    """Single line item on an invoice."""
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    
    @computed_field
    @property
    def line_total(self) -> Decimal:
        """Calculate line total (quantity * unit_price)."""
        return self.quantity * self.unit_price

class InvoiceLineItems(BaseModel):
    """Container for invoice line items with validation."""
    items: List[InvoiceLineItem] = Field(default_factory=list)
    
    @computed_field
    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal of all line items."""
        return sum(item.line_total for item in self.items)
```

**Final Decision**: ✅ Pydantic validation with calculated totals (not stored)

---

### Question 5: Lien Eligibility - Job Types

**User Decision**: Lien-eligible job types are `installation` and `major_repair`.

**Implementation**:
```python
LIEN_ELIGIBLE_JOB_TYPES = {"installation", "major_repair"}

def is_lien_eligible(job_type: str) -> bool:
    """Check if job type is eligible for mechanic's lien."""
    return job_type.lower() in LIEN_ELIGIBLE_JOB_TYPES
```

**Final Decision**: ✅ `installation` and `major_repair` are lien-eligible

---

### Question 6: Clear Day - Soft Delete vs Hard Delete

**User Decision**: Hard delete with audit log for recovery.

**Implementation**:
```python
async def clear_schedule_for_date(self, schedule_date: date, user_id: UUID) -> ClearScheduleResponse:
    """Clear all appointments for a date (hard delete with audit log)."""
    # Get appointments to delete (for audit log and job status reset)
    appointments = await self.appointment_repo.get_by_date(schedule_date)
    job_ids = [a.job_id for a in appointments]
    
    # Create audit log entry BEFORE deletion
    audit_entry = await self.audit_service.log_schedule_clear(
        schedule_date=schedule_date,
        appointments=appointments,
        job_ids=job_ids,
        cleared_by=user_id,
    )
    
    # Hard delete appointments
    deleted_count = await self.appointment_repo.delete_by_date(schedule_date)
    
    # Reset job statuses (only 'scheduled' jobs)
    reset_count = await self.job_service.reset_jobs_to_approved(
        job_ids=job_ids,
        only_status="scheduled"
    )
    
    return ClearScheduleResponse(
        success=True,
        schedule_date=schedule_date,
        appointments_deleted=deleted_count,
        jobs_reset=reset_count,
        audit_log_id=audit_entry.id,
        message=f"Schedule cleared for {schedule_date.strftime('%B %d, %Y')}"
    )
```

**Final Decision**: ✅ Hard delete with audit log for potential recovery

---

### Question 7: Testing Strategy

**User Decision**: Three-tier testing (unit, functional, integration) with comprehensive coverage.

**Testing Requirements**:

#### Backend Testing
| Tier | Target | Focus |
|------|--------|-------|
| Unit | 90%+ pass rate | Service methods, business logic |
| Functional | 85%+ pass rate | API endpoints with real database |
| Integration | 80%+ pass rate | Cross-component workflows |

#### Frontend Testing (Agent-Browser)

**CRITICAL**: Every UI feature must be validated with agent-browser covering ALL possible interactions.

**Schedule Clear/Reset UI Validation Checklist**:
```bash
# Generate Routes Tab - Clear Results
- [ ] Clear Results button visible only when results exist
- [ ] Click Clear Results → results cleared, job list visible
- [ ] After clear, can regenerate schedule
- [ ] Clear Results does NOT deselect jobs

# Generate Routes Tab - Select All / Deselect All
- [ ] Select All → all visible jobs checked
- [ ] Deselect All → all jobs unchecked
- [ ] Select All with filters → only filtered jobs selected
- [ ] Job count updates correctly
- [ ] Can generate schedule after Select All
- [ ] Can generate schedule after Deselect All (should show warning)

# Schedule Tab - Clear Day
- [ ] Clear Day button visible
- [ ] Click Clear Day → date picker/dialog opens
- [ ] Select date with appointments → shows count
- [ ] Select date with no appointments → shows "no appointments" message
- [ ] Cancel button closes dialog
- [ ] Confirm button clears appointments
- [ ] Success toast appears
- [ ] Calendar refreshes to show empty day
- [ ] Jobs page shows reset jobs as "approved"
- [ ] Recently Cleared section shows the clear action
```

**Invoice UI Validation Checklist**:
```bash
# Invoice List
- [ ] Navigate to Invoices tab
- [ ] List loads with correct data
- [ ] Filter by status (draft, sent, paid, overdue)
- [ ] Filter by customer
- [ ] Filter by date range
- [ ] Filter by lien eligibility
- [ ] Sort by amount, due date, status
- [ ] Pagination works
- [ ] Status badges show correct colors

# Invoice Detail
- [ ] Click invoice → detail page loads
- [ ] All fields display correctly
- [ ] Line items show with calculated totals
- [ ] Payment history visible (if any)
- [ ] Action buttons visible (Send, Record Payment, Send Reminder, etc.)
- [ ] Lien tracking section visible for eligible invoices

# Invoice Creation (from Job)
- [ ] Navigate to completed job with payment_collected_on_site = false
- [ ] "Generate Invoice" button visible
- [ ] Click button → invoice form opens with pre-populated data
- [ ] Customer auto-populated from job
- [ ] Line items editable
- [ ] Totals calculate correctly
- [ ] Save as draft
- [ ] Validation errors show for invalid data

# Payment Recording
- [ ] Click "Record Payment" → dialog opens
- [ ] Select payment method
- [ ] Enter amount
- [ ] Partial payment handling
- [ ] Full payment marks invoice as paid
- [ ] Payment history updates

# Lien Tracking
- [ ] Dashboard shows "Lien Deadlines Approaching" widget
- [ ] Widget shows 45-day warning due invoices
- [ ] Widget shows 120-day filing deadline invoices
- [ ] "Send Warning" button works
- [ ] "Mark Filed" button works
- [ ] Invoice detail shows lien status
```

**Final Decision**: ✅ Three-tier testing with comprehensive agent-browser validation

---

### Suggested Additions: Error Handling, Audit Logging, Permissions

#### Error Handling

**Clear Day Errors**:
```python
class ClearScheduleError(Exception):
    """Base exception for schedule clearing errors."""
    pass

class NoAppointmentsError(ClearScheduleError):
    """Raised when trying to clear a date with no appointments."""
    pass

# In service
async def clear_schedule_for_date(self, schedule_date: date) -> ClearScheduleResponse:
    appointments = await self.appointment_repo.get_by_date(schedule_date)
    
    if not appointments:
        # Return success with zero counts (not an error)
        return ClearScheduleResponse(
            success=True,
            schedule_date=schedule_date,
            appointments_deleted=0,
            jobs_reset=0,
            message=f"No appointments found for {schedule_date.strftime('%B %d, %Y')}"
        )
    
    # ... proceed with deletion
```

**Invoice Generation Errors**:
```python
class InvoiceError(Exception):
    """Base exception for invoice errors."""
    pass

class JobNotCompletedError(InvoiceError):
    """Cannot generate invoice for incomplete job."""
    pass

class InvoiceAlreadyExistsError(InvoiceError):
    """Invoice already exists for this job."""
    pass

class PaymentAlreadyCollectedError(InvoiceError):
    """Payment was already collected on-site for this job."""
    pass

class InvalidLineItemsError(InvoiceError):
    """Line items validation failed."""
    pass
```

#### Audit Logging

**Recommendation**: Add audit logging for sensitive operations.

**Operations to Audit**:
| Operation | Action Name | Details |
|-----------|-------------|---------|
| Clear schedule | `schedule.cleared` | date, count deleted, jobs reset, full appointment data |
| Invoice created | `invoice.created` | invoice_id, job_id, amount |
| Invoice sent | `invoice.sent` | invoice_id, method (sms/email) |
| Payment recorded | `invoice.payment_recorded` | invoice_id, amount, method |
| Invoice cancelled | `invoice.cancelled` | invoice_id, reason |
| Lien warning sent | `invoice.lien_warning_sent` | invoice_id, customer_id |
| Lien filed | `invoice.lien_filed` | invoice_id, filing_date |

#### Permissions/Authorization

**Recommendation**: Role-based access control for sensitive operations.

| Operation | Admin | Manager | Field Tech |
|-----------|-------|---------|------------|
| Clear schedule | ✅ | ✅ | ❌ |
| Create invoice | ✅ | ✅ | ❌ |
| Send invoice | ✅ | ✅ | ❌ |
| Record payment | ✅ | ✅ | ✅ (on-site only) |
| Cancel invoice | ✅ | ❌ | ❌ |
| Send lien warning | ✅ | ❌ | ❌ |
| Mark lien filed | ✅ | ❌ | ❌ |

**Note**: Full RBAC implementation is out of scope for Phase 8, but the service layer should be designed to accept `user_id` for audit logging, making it easy to add permission checks later.

---

### Final Summary of Decisions

| Question | Decision |
|----------|----------|
| 1. Job status reset scope | Only reset jobs with `status = 'scheduled'` |
| 2. Invoice number sequence | PostgreSQL sequence with year prefix (`INV-2026-0001`) |
| 3. Invoice relationship | Link to Job ID only, not Appointment ID |
| 4. Line items structure | Pydantic validation with calculated totals |
| 5. Lien eligibility | `installation` and `major_repair` |
| 6. Clear day delete type | Hard delete with audit log |
| 7. Testing strategy | Three-tier with comprehensive agent-browser |

### Additional Decisions from Analysis

| Topic | Decision |
|-------|----------|
| Invoice generation | Manual (button click), not automatic |
| `payment_collected_on_site` | New boolean field on Job model |
| Lien tracking | Manual triggers only, dashboard widget for deadlines |
| Reminders | Manual triggers only (no cron jobs in Phase 8) |
| Rollback strategy | Audit log with JSON blob, "Recently Cleared" section |

---

*This brainstorming section was added on January 28, 2026 during the Phase 8 planning review session.*

---

## 🎯 PRIORITY 3: Authentication & Login System

### Background & Problem Statement

The admin dashboard currently has no authentication. Anyone with the URL can access all business data, customer information, and perform administrative actions. This is a critical security gap that must be addressed before production deployment.

**Current State**:
- No User model or authentication system
- `DEMO_USER_ID` placeholder in AI API
- `authenticated_client` test fixture with mock token
- Logging patterns exist for `user.auth.login_started` but no implementation

**Business Need**:
- Viktor needs to control who can access the system
- Field technicians need mobile access with limited permissions
- Sensitive operations (clear schedule, invoices, lien filing) need role-based access
- Audit logging requires user identification

---

### Solution: Simple JWT Authentication with Role-Based Access

A lightweight authentication system that:
1. Provides secure login with username/password
2. Issues JWT tokens for API authentication
3. Supports role-based access control (RBAC)
4. Integrates with existing Staff model

---

### User Roles & Permissions

Based on Viktor's team structure and business needs:

| Role | Description | Users | Access Level |
|------|-------------|-------|--------------|
| **Admin** | Full system access | Viktor | Everything |
| **Manager** | Operations management | (Future) | Most operations, no system config |
| **Tech** | Field technician | Vas, Dad, Steven, Vitallik | Mobile view, job updates, on-site payments |

#### Permission Matrix

| Operation | Admin | Manager | Tech |
|-----------|-------|---------|------|
| **Dashboard** | ✅ | ✅ | ✅ (limited) |
| **View Customers** | ✅ | ✅ | ✅ |
| **Edit Customers** | ✅ | ✅ | ❌ |
| **View Jobs** | ✅ | ✅ | ✅ (assigned only) |
| **Update Job Status** | ✅ | ✅ | ✅ (assigned only) |
| **View Schedule** | ✅ | ✅ | ✅ (own schedule) |
| **Generate Schedule** | ✅ | ✅ | ❌ |
| **Apply Schedule** | ✅ | ✅ | ❌ |
| **Clear Schedule** | ✅ | ✅ | ❌ |
| **View Invoices** | ✅ | ✅ | ❌ |
| **Create Invoice** | ✅ | ✅ | ❌ |
| **Record Payment** | ✅ | ✅ | ✅ (on-site only) |
| **Send Lien Warning** | ✅ | ❌ | ❌ |
| **Mark Lien Filed** | ✅ | ❌ | ❌ |
| **Manage Staff** | ✅ | ❌ | ❌ |
| **System Settings** | ✅ | ❌ | ❌ |

---

### User Model Design

#### Option A: Extend Staff Model (Recommended)

Add authentication fields directly to the existing `Staff` model. This is simpler and avoids a separate User table.

**Pros**:
- No new table needed
- Staff already has role, name, phone, email
- One-to-one relationship is natural
- Simpler queries

**Cons**:
- Mixes authentication with staff data
- All staff become potential users

**Implementation**:
```python
# Add to Staff model
class Staff(Base):
    # ... existing fields ...
    
    # Authentication fields
    username: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,  # Not all staff need login
        index=True,
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_login_enabled: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
    )
    last_login: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
    )
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
```

#### Option B: Separate User Model

Create a dedicated User model with a foreign key to Staff.

**Pros**:
- Clean separation of concerns
- Can have users without staff records (future: customers)
- More flexible for future expansion

**Cons**:
- Additional table and joins
- More complex queries
- Potential sync issues between User and Staff

**Implementation**:
```python
class User(Base):
    """User model for authentication."""
    
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    
    # Link to staff (optional - for staff users)
    staff_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff.id"),
        nullable=True,
        unique=True,
    )
    
    # Authentication
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    # Role (can differ from staff role)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="tech",
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
    )
    
    # Security
    last_login: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        server_default="0",
    )
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    staff: Mapped["Staff"] = relationship("Staff", back_populates="user")
```

**Recommendation**: Start with **Option A** (extend Staff model) for simplicity. Can migrate to Option B later if needed.

---

### Authentication Flow

#### Login Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Login Page                                                 │
│  ──────────                                                 │
│                                                             │
│  🌿 Grin's Irrigation Platform                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Username                                           │   │
│  │  [viktor                                          ] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Password                                           │   │
│  │  [••••••••                                        ] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ☐ Remember me                                              │
│                                                             │
│  [        Sign In        ]                                  │
│                                                             │
│  Forgot password? Contact admin                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### JWT Token Structure

```json
{
  "sub": "staff-uuid-here",
  "username": "viktor",
  "role": "admin",
  "name": "Viktor Grin",
  "iat": 1706472000,
  "exp": 1706558400
}
```

#### Token Refresh Strategy

| Token Type | Lifetime | Storage | Refresh |
|------------|----------|---------|---------|
| Access Token | 15 minutes | Memory | On API call |
| Refresh Token | 7 days | HttpOnly Cookie | On access token expiry |

---

### API Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/api/v1/auth/login` | POST | Authenticate user, return tokens | No |
| `/api/v1/auth/logout` | POST | Invalidate refresh token | Yes |
| `/api/v1/auth/refresh` | POST | Get new access token | Refresh token |
| `/api/v1/auth/me` | GET | Get current user info | Yes |
| `/api/v1/auth/change-password` | POST | Change own password | Yes |

#### Login Request/Response

**Request**:
```json
{
  "username": "viktor",
  "password": "secure_password_here"
}
```

**Response (Success)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "staff-uuid",
    "username": "viktor",
    "name": "Viktor Grin",
    "role": "admin",
    "email": "viktor@grins.com"
  }
}
```

**Response (Error)**:
```json
{
  "detail": "Invalid username or password",
  "error_code": "INVALID_CREDENTIALS"
}
```

---

### Security Considerations

#### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- Hashed with bcrypt (cost factor 12)

#### Account Lockout
- Lock account after 5 failed attempts
- Lockout duration: 15 minutes
- Reset counter on successful login

#### Session Security
- Access tokens stored in memory (not localStorage)
- Refresh tokens in HttpOnly cookies
- CSRF protection for cookie-based auth
- Token blacklist for logout (optional)

---

### Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `LoginPage.tsx` | `features/auth/` | Login form |
| `AuthProvider.tsx` | `core/providers/` | Auth context and state |
| `ProtectedRoute.tsx` | `core/router/` | Route guard for auth |
| `useAuth.ts` | `features/auth/hooks/` | Auth hook for components |
| `UserMenu.tsx` | `shared/components/` | User dropdown in header |

#### Auth Context

```typescript
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (permission: string) => boolean;
}
```

#### Protected Route Usage

```typescript
// In router
<Route
  path="/invoices"
  element={
    <ProtectedRoute requiredRole={['admin', 'manager']}>
      <InvoicesPage />
    </ProtectedRoute>
  }
/>
```

---

### UI Mockups

#### Login Page

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                                                                 │
│                    🌿 Grin's Irrigation                         │
│                       Platform                                  │
│                                                                 │
│              ┌─────────────────────────────────┐               │
│              │                                 │               │
│              │  Username                       │               │
│              │  ┌───────────────────────────┐ │               │
│              │  │                           │ │               │
│              │  └───────────────────────────┘ │               │
│              │                                 │               │
│              │  Password                       │               │
│              │  ┌───────────────────────────┐ │               │
│              │  │                           │ │               │
│              │  └───────────────────────────┘ │               │
│              │                                 │               │
│              │  ☐ Remember me                  │               │
│              │                                 │               │
│              │  ┌───────────────────────────┐ │               │
│              │  │       Sign In             │ │               │
│              │  └───────────────────────────┘ │               │
│              │                                 │               │
│              │  Forgot password? Contact admin │               │
│              │                                 │               │
│              └─────────────────────────────────┘               │
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### User Menu (Header)

```
┌─────────────────────────────────────────────────────────────────┐
│  🌿 Grin's Irrigation    Dashboard  Customers  Jobs  ...       │
│                                                    ┌──────────┐ │
│                                                    │ Viktor ▼ │ │
│                                                    └──────────┘ │
│                                                         │       │
│                                              ┌──────────┴─────┐ │
│                                              │ 👤 Profile     │ │
│                                              │ ⚙️ Settings    │ │
│                                              │ ────────────── │ │
│                                              │ 🚪 Sign Out    │ │
│                                              └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

### Implementation Phases

#### Phase 8L: Authentication Backend (4-5 hours)

**Tasks**:
1. Add authentication fields to Staff model (migration)
2. Create `UserRole` enum if needed (or use existing `StaffRole`)
3. Create `AuthService` with login, logout, token generation
4. Implement password hashing with bcrypt
5. Implement JWT token generation and validation
6. Create `POST /api/v1/auth/login` endpoint
7. Create `POST /api/v1/auth/logout` endpoint
8. Create `POST /api/v1/auth/refresh` endpoint
9. Create `GET /api/v1/auth/me` endpoint
10. Add `get_current_user` dependency for protected routes
11. Write unit tests for auth service

**Deliverables**:
- Staff model with auth fields
- Working login/logout endpoints
- JWT token generation
- Protected route dependency

---

#### Phase 8M: Authentication Frontend (3-4 hours)

**Tasks**:
1. Create `AuthProvider.tsx` context
2. Create `LoginPage.tsx` with form validation
3. Create `ProtectedRoute.tsx` component
4. Create `useAuth.ts` hook
5. Add auth state to API client (token injection)
6. Create `UserMenu.tsx` dropdown component
7. Update `Layout.tsx` to show user menu
8. Add redirect to login for unauthenticated users
9. Handle token refresh on API calls
10. Write frontend tests

**Deliverables**:
- Working login page
- Auth context with state management
- Protected routes
- User menu in header

---

#### Phase 8N: Role-Based Access Control (2-3 hours)

**Tasks**:
1. Create `hasPermission()` utility function
2. Add permission checks to sensitive API endpoints
3. Add `requiredRole` prop to `ProtectedRoute`
4. Hide UI elements based on role (conditional rendering)
5. Add role-based filtering to data queries (tech sees only assigned jobs)
6. Write integration tests for RBAC

**Deliverables**:
- Permission checks on API endpoints
- Role-based UI visibility
- Tech-specific data filtering

---

#### Phase 8O: Initial User Setup & Testing (1-2 hours)

**Tasks**:
1. Create seed script for initial admin user (Viktor)
2. Create seed script for tech users (Vas, Dad, etc.)
3. Document password reset process (manual for now)
4. End-to-end testing of login flow
5. Test role-based access for each user type
6. Security testing (invalid tokens, expired tokens, etc.)

**Deliverables**:
- Initial users seeded
- Full auth flow tested
- Security edge cases covered

---

### Summary: Authentication Implementation

| Phase | Focus | Effort |
|-------|-------|--------|
| Phase 8L | Backend auth (JWT, login/logout) | 4-5 hours |
| Phase 8M | Frontend auth (login page, context) | 3-4 hours |
| Phase 8N | Role-based access control | 2-3 hours |
| Phase 8O | User setup & testing | 1-2 hours |
| **Total** | **Complete Auth System** | **10-14 hours** |

---

### Future Enhancements (Not in Phase 8)

- **Password Reset via Email**: Send reset link to email
- **Two-Factor Authentication**: SMS or authenticator app
- **Session Management**: View and revoke active sessions
- **OAuth Integration**: Login with Google (for customers)
- **API Keys**: For external integrations
- **Audit Log UI**: View login history and security events

---

## 🎨 Detailed Login Page Design

### Component Structure

The login page will use shadcn/ui components for consistency with the rest of the application.

```
LoginPage.tsx
├── Card (container)
│   ├── CardHeader
│   │   ├── Logo (Droplet icon + text)
│   │   └── CardDescription
│   ├── CardContent
│   │   └── Form (react-hook-form + zod)
│   │       ├── FormField (username)
│   │       │   ├── FormLabel
│   │       │   ├── FormControl → Input
│   │       │   └── FormMessage (error)
│   │       ├── FormField (password)
│   │       │   ├── FormLabel
│   │       │   ├── FormControl → Input (type="password")
│   │       │   │   └── PasswordToggle (Eye/EyeOff icon)
│   │       │   └── FormMessage (error)
│   │       ├── Checkbox (Remember me)
│   │       └── Button (Sign In)
│   └── CardFooter
│       └── "Forgot password?" text
└── Alert (error message, conditional)
```

### Detailed UI Mockup with Styling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     BACKGROUND: bg-muted (gray-50)                  │   │
│  │                                                                     │   │
│  │         ┌─────────────────────────────────────────────────┐        │   │
│  │         │  CARD: w-[400px] shadow-lg rounded-xl           │        │   │
│  │         │  bg-card (white) border border-border           │        │   │
│  │         │                                                 │        │   │
│  │         │  ┌─────────────────────────────────────────┐   │        │   │
│  │         │  │  HEADER: text-center py-6              │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  🌿 (Droplet icon, h-12 w-12,          │   │        │   │
│  │         │  │      text-primary/green-600)            │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  Grin's Irrigation                      │   │        │   │
│  │         │  │  (text-2xl font-bold)                   │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  Sign in to your account                │   │        │   │
│  │         │  │  (text-sm text-muted-foreground)        │   │        │   │
│  │         │  └─────────────────────────────────────────┘   │        │   │
│  │         │                                                 │        │   │
│  │         │  ┌─────────────────────────────────────────┐   │        │   │
│  │         │  │  CONTENT: px-6 pb-6                    │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  ┌─────────────────────────────────┐   │   │        │   │
│  │         │  │  │  ERROR ALERT (conditional)      │   │   │        │   │
│  │         │  │  │  variant="destructive"          │   │   │        │   │
│  │         │  │  │  ⚠️ Invalid username or password │   │   │        │   │
│  │         │  │  └─────────────────────────────────┘   │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  Username                               │   │        │   │
│  │         │  │  ┌─────────────────────────────────┐   │   │        │   │
│  │         │  │  │ 👤 viktor                       │   │   │        │   │
│  │         │  │  └─────────────────────────────────┘   │   │        │   │
│  │         │  │  (Input with User icon prefix)          │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  Password                               │   │        │   │
│  │         │  │  ┌─────────────────────────────────┐   │   │        │   │
│  │         │  │  │ 🔒 ••••••••              👁️    │   │   │        │   │
│  │         │  │  └─────────────────────────────────┘   │   │        │   │
│  │         │  │  (Input with Lock icon, Eye toggle)     │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  ┌─────────────────────────────────┐   │   │        │   │
│  │         │  │  │ ☐ Remember me for 7 days       │   │   │        │   │
│  │         │  │  └─────────────────────────────────┘   │   │        │   │
│  │         │  │  (Checkbox + Label)                     │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  ┌─────────────────────────────────┐   │   │        │   │
│  │         │  │  │         Sign In                 │   │   │        │   │
│  │         │  │  │    (or Loading spinner...)      │   │   │        │   │
│  │         │  │  └─────────────────────────────────┘   │   │        │   │
│  │         │  │  (Button w-full, variant="default")     │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  └─────────────────────────────────────────┘   │        │   │
│  │         │                                                 │        │   │
│  │         │  ┌─────────────────────────────────────────┐   │        │   │
│  │         │  │  FOOTER: text-center text-sm           │   │        │   │
│  │         │  │  text-muted-foreground                 │   │        │   │
│  │         │  │                                         │   │        │   │
│  │         │  │  Forgot password? Contact admin         │   │        │   │
│  │         │  └─────────────────────────────────────────┘   │        │   │
│  │         │                                                 │        │   │
│  │         └─────────────────────────────────────────────────┘        │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Responsive Design Specifications

| Breakpoint | Card Width | Layout |
|------------|------------|--------|
| Mobile (< 640px) | `w-full mx-4` | Full width with padding |
| Tablet (640px+) | `w-[400px]` | Centered card |
| Desktop (1024px+) | `w-[400px]` | Centered card |

### Component Implementation Sketch

```typescript
// features/auth/components/LoginPage.tsx

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { Droplet, User, Lock, Eye, EyeOff, Loader2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { useAuth } from '../hooks/useAuth';

const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().default(false),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, isLoading } = useAuth();
  const navigate = useNavigate();

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    try {
      await login(data.username, data.password, data.rememberMe);
      navigate('/dashboard');
    } catch (err) {
      setError('Invalid username or password');
    }
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center bg-muted p-4"
      data-testid="login-page"
    >
      <Card className="w-full max-w-[400px] shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="flex justify-center">
            <Droplet className="h-12 w-12 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">
            Grin's Irrigation
          </CardTitle>
          <CardDescription>
            Sign in to your account
          </CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4" data-testid="login-error">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          {...field}
                          placeholder="Enter your username"
                          className="pl-10"
                          data-testid="username-input"
                          autoComplete="username"
                          autoFocus
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                        <Input
                          {...field}
                          type={showPassword ? 'text' : 'password'}
                          placeholder="Enter your password"
                          className="pl-10 pr-10"
                          data-testid="password-input"
                          autoComplete="current-password"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          data-testid="password-toggle"
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="rememberMe"
                render={({ field }) => (
                  <FormItem className="flex items-center space-x-2">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        data-testid="remember-me-checkbox"
                      />
                    </FormControl>
                    <FormLabel className="text-sm font-normal cursor-pointer">
                      Remember me for 7 days
                    </FormLabel>
                  </FormItem>
                )}
              />

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
                data-testid="login-submit-btn"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>
          </Form>
        </CardContent>

        <CardFooter className="justify-center">
          <p className="text-sm text-muted-foreground">
            Forgot password? Contact admin
          </p>
        </CardFooter>
      </Card>
    </div>
  );
}
```

### Login Page States

| State | Visual Feedback |
|-------|-----------------|
| **Initial** | Empty form, Sign In button enabled |
| **Typing** | Input values shown, validation on blur |
| **Submitting** | Button shows spinner + "Signing in...", inputs disabled |
| **Error** | Red alert banner above form, inputs re-enabled |
| **Success** | Redirect to /dashboard |
| **Account Locked** | Alert: "Account locked. Try again in X minutes." |

### Error Messages

| Error Code | User Message |
|------------|--------------|
| `INVALID_CREDENTIALS` | "Invalid username or password" |
| `ACCOUNT_LOCKED` | "Account locked due to too many failed attempts. Try again in 15 minutes." |
| `ACCOUNT_DISABLED` | "Your account has been disabled. Contact admin." |
| `NETWORK_ERROR` | "Unable to connect. Please check your internet connection." |
| `SERVER_ERROR` | "Something went wrong. Please try again later." |

### Accessibility Requirements

- All form fields have associated labels
- Error messages are announced to screen readers
- Password toggle has aria-label
- Focus management: auto-focus on username field
- Keyboard navigation: Tab through fields, Enter to submit
- Color contrast meets WCAG AA standards

---

## 🚀 Production Readiness Checklist

### What's Missing for Full Production Deployment

This section identifies gaps that need to be addressed before the system is production-ready.

---

### 1. Security Hardening

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **HTTPS/SSL** | ❌ Missing | Critical | Must use HTTPS in production |
| **CORS Configuration** | ⚠️ Needs Review | High | Currently allows all origins |
| **Rate Limiting** | ❌ Missing | High | Protect auth endpoints from brute force |
| **CSRF Protection** | ❌ Missing | High | For cookie-based refresh tokens |
| **Security Headers** | ❌ Missing | Medium | CSP, X-Frame-Options, etc. |
| **Input Sanitization** | ⚠️ Partial | Medium | Review all user inputs |
| **SQL Injection Prevention** | ✅ Done | - | Using SQLAlchemy ORM |
| **XSS Prevention** | ⚠️ Needs Review | Medium | React escapes by default, but review |

**Implementation Notes**:

```python
# Rate limiting for auth endpoints (using slowapi)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # 5 attempts per minute per IP
async def login(request: Request, credentials: LoginRequest):
    ...
```

```python
# Security headers middleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# In production
app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://grins-irrigation.com"],  # Specific origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

### 2. Environment & Configuration

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Secrets Management** | ❌ Missing | Critical | Use environment variables or secrets manager |
| **Environment Separation** | ⚠️ Partial | High | dev/staging/prod configs |
| **Database Connection Pooling** | ⚠️ Needs Review | Medium | Verify pool settings for production load |
| **Redis for Sessions** | ❌ Missing | Medium | For token blacklist and session storage |

**Required Environment Variables for Production**:

```bash
# .env.production (DO NOT COMMIT)

# Database
DATABASE_URL=postgresql://user:password@host:5432/grins_production

# Security
SECRET_KEY=<random-256-bit-key>
JWT_SECRET_KEY=<different-random-256-bit-key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
ALLOWED_ORIGINS=https://grins-irrigation.com,https://www.grins-irrigation.com

# External Services
OPENAI_API_KEY=<key>
GOOGLE_MAPS_API_KEY=<key>
TELNYX_API_KEY=<key>  # Phase 9

# Monitoring
SENTRY_DSN=<sentry-dsn>
LOG_LEVEL=INFO

# Feature Flags
ENABLE_AI_FEATURES=true
ENABLE_SMS_NOTIFICATIONS=false  # Until Phase 9
```

---

### 3. Error Monitoring & Logging

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Error Tracking (Sentry)** | ❌ Missing | High | Catch and alert on production errors |
| **Structured Logging** | ✅ Done | - | Using structlog |
| **Log Aggregation** | ❌ Missing | Medium | Ship logs to CloudWatch/Datadog |
| **Performance Monitoring** | ❌ Missing | Medium | APM for slow queries, endpoints |
| **Uptime Monitoring** | ❌ Missing | High | Health check endpoint monitoring |

**Sentry Integration**:

```python
# In main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        environment=settings.ENVIRONMENT,
    )
```

---

### 4. Database & Data

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Database Backups** | ❌ Missing | Critical | Automated daily backups |
| **Point-in-Time Recovery** | ❌ Missing | High | For disaster recovery |
| **Database Migrations** | ✅ Done | - | Using Alembic |
| **Data Encryption at Rest** | ⚠️ Depends on Host | Medium | Enable on database server |
| **PII Handling** | ⚠️ Needs Review | High | Customer phone, email, address |

**Backup Strategy**:

```bash
# Daily backup script (for Railway/Render)
# Most managed databases include automated backups

# For self-hosted:
pg_dump -h localhost -U grins -d grins_production | gzip > backup_$(date +%Y%m%d).sql.gz
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://grins-backups/
```

---

### 5. Authentication Gaps

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Password Reset Flow** | ❌ Missing | Medium | Currently "contact admin" |
| **Email Verification** | ❌ Missing | Low | Not critical for internal users |
| **Session Invalidation** | ⚠️ Partial | Medium | Need token blacklist for logout |
| **Initial User Seeding** | ❌ Missing | High | Script to create Viktor's account |
| **Password Complexity Validation** | ❌ Missing | Medium | Enforce strong passwords |

**Initial User Seeding Script**:

```python
# scripts/seed_users.py

import asyncio
from passlib.context import CryptContext
from grins_platform.database import get_db_session
from grins_platform.models import Staff

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def seed_admin_user():
    """Create initial admin user (Viktor)."""
    async for db in get_db_session():
        # Check if Viktor already exists
        existing = await db.execute(
            select(Staff).where(Staff.username == "viktor")
        )
        if existing.scalar_one_or_none():
            print("Admin user already exists")
            return
        
        # Create Viktor's account
        viktor = Staff(
            first_name="Viktor",
            last_name="Grin",
            email="viktor@grins.com",
            phone="6125551234",
            role="admin",
            username="viktor",
            password_hash=pwd_context.hash("CHANGE_ME_ON_FIRST_LOGIN"),
            is_login_enabled=True,
            is_active=True,
        )
        db.add(viktor)
        await db.commit()
        print("Admin user created. CHANGE PASSWORD ON FIRST LOGIN!")

if __name__ == "__main__":
    asyncio.run(seed_admin_user())
```

---

### 6. Frontend Production Build

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Production Build** | ✅ Done | - | `npm run build` works |
| **Environment Variables** | ⚠️ Needs Review | High | Ensure API URL is configurable |
| **Error Boundaries** | ⚠️ Partial | Medium | Catch React errors gracefully |
| **Loading States** | ✅ Done | - | Using LoadingSpinner |
| **Offline Handling** | ❌ Missing | Low | Show message when offline |
| **Bundle Size Optimization** | ⚠️ Needs Review | Low | Check for large dependencies |

**Frontend Environment Configuration**:

```typescript
// frontend/src/core/config/index.ts

export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  sentryDsn: import.meta.env.VITE_SENTRY_DSN,
};
```

```bash
# frontend/.env.production
VITE_API_URL=https://api.grins-irrigation.com
VITE_ENVIRONMENT=production
VITE_SENTRY_DSN=<frontend-sentry-dsn>
```

---

### 7. Deployment Infrastructure

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **CI/CD Pipeline** | ❌ Missing | High | Automated testing and deployment |
| **Staging Environment** | ❌ Missing | High | Test before production |
| **Health Check Endpoint** | ✅ Done | - | `/health` exists |
| **Graceful Shutdown** | ⚠️ Needs Review | Medium | Handle SIGTERM properly |
| **Auto-scaling** | ❌ Missing | Low | For high traffic periods |
| **CDN for Static Assets** | ❌ Missing | Low | Faster frontend loading |

**GitHub Actions CI/CD Example**:

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: |
          uv run pytest -v
          uv run ruff check src/
          uv run mypy src/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Railway
        run: |
          # Railway deployment command
          railway up
```

---

### 8. Documentation

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **API Documentation** | ✅ Done | - | FastAPI auto-generates OpenAPI |
| **Deployment Guide** | ⚠️ Partial | High | Needs production specifics |
| **User Manual** | ❌ Missing | Medium | For Viktor and technicians |
| **Runbook** | ❌ Missing | Medium | Incident response procedures |
| **Architecture Diagram** | ⚠️ Partial | Low | Update with auth flow |

---

### 9. Testing Gaps

| Item | Status | Priority | Notes |
|------|--------|----------|-------|
| **Load Testing** | ❌ Missing | Medium | Test with 150+ concurrent jobs |
| **Security Testing** | ❌ Missing | High | Penetration testing |
| **E2E Tests** | ⚠️ Partial | Medium | agent-browser scripts exist |
| **Mobile Testing** | ❌ Missing | Medium | Test on actual phones |

---

### Production Readiness Summary

| Category | Ready? | Blockers |
|----------|--------|----------|
| **Security** | ❌ No | HTTPS, rate limiting, CORS |
| **Authentication** | ❌ No | Not implemented yet |
| **Database** | ⚠️ Partial | Backups needed |
| **Monitoring** | ❌ No | Sentry, log aggregation |
| **Deployment** | ⚠️ Partial | CI/CD, staging env |
| **Documentation** | ⚠️ Partial | User manual, runbook |

**Minimum Viable Production Checklist**:

1. ✅ Implement authentication (Phase 8L-8O)
2. ⬜ Configure HTTPS
3. ⬜ Set up rate limiting on auth endpoints
4. ⬜ Configure production CORS
5. ⬜ Set up Sentry error tracking
6. ⬜ Create initial admin user
7. ⬜ Configure database backups
8. ⬜ Set up CI/CD pipeline
9. ⬜ Create staging environment
10. ⬜ Security review

---

*Production readiness section added on January 28, 2026 during the Phase 8 planning brainstorming session.*

---

## Updated Phase 8 Total Effort

| Priority | Feature | Effort |
|----------|---------|--------|
| Priority 1 | Schedule Clear/Reset | 9-13 hours |
| Priority 2 | Invoice Management | 16-21 hours |
| Priority 3 | Authentication & Login | 10-14 hours |
| **Total** | **All Phase 8 Features** | **35-48 hours** |

---

## Updated Implementation Order

1. **Phase 8L-8O**: Authentication (security first - protect the system)
2. **Phase 8A-8C**: Schedule Clear/Reset (immediate user value)
3. **Phase 8G-8H**: Invoice Model + Generation (high business value)
4. **Phase 8I**: Invoice Frontend (complete the invoice feature)
5. **Phase 8J**: Lien Tracking & Dashboard Widget (compliance)
6. **Phase 8K**: Reminders (polish)

**Rationale**: Authentication should be implemented first because:
1. All other features need user identification for audit logging
2. Invoice operations require role-based access control
3. Clear schedule needs to track who performed the action
4. Security is foundational - better to add it early

---

*Authentication section added on January 28, 2026 during the Phase 8 planning brainstorming session.*
