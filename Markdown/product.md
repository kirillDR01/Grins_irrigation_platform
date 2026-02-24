# Product Overview

## Product Purpose

Grin's Irrigation Platform is a field service automation system designed to replace manual spreadsheet-based operations for a residential and commercial irrigation service business. The platform eliminates the time-consuming manual processes of tracking job requests, scheduling appointments, managing field staff, and handling invoicing that currently consume 15-20+ hours per week of administrative time.

### The Problem We're Solving

Viktor Grin runs a successful irrigation business serving the Twin Cities metro area (Eden Prairie, Plymouth, Maple Grove, Brooklyn Park, Rogers, and surrounding cities). His current operations rely on:

- **Google Spreadsheets** for tracking all job requests, customer data, leads, and payments
- **Google Calendar** for scheduling appointments with manual color-coding for staff assignments
- **Manual text/call communication** with each customer individually
- **Template-based invoices** created and sent manually via text
- **Mental calculations** for route optimization and time estimation

During peak seasons (spring startups and fall winterizations), the business handles 150+ individual jobs per week, with each job requiring 5+ minutes of manual administrative work. This creates bottlenecks, missed opportunities, and customer service issues.

### Why This Product Exists

This platform exists to:
1. **Eliminate manual data entry** - Auto-populate customer and job data from intake forms
2. **Automate scheduling** - Intelligent route building with constraint-based optimization
3. **Enable field mobility** - Give technicians all job information on their phones
4. **Streamline communication** - Automated appointment confirmations and reminders
5. **Centralize operations** - Single source of truth replacing scattered spreadsheets

---

## Target Users

### Primary Users

#### 1. Business Owner/Manager (Viktor)
**Role:** Coordination, estimates, complex scheduling, customer relations

**Current Pain Points:**
- Lives in spreadsheets during busy season, constantly updating
- Spends 5+ minutes per job on manual scheduling and communication
- Forgets to update important information due to being overwhelmed
- Can't easily delegate because system is in his head
- Loses jobs due to slow response times during peak season

**Needs:**
- Dashboard view of all incoming requests and their status
- One-click schedule generation with intelligent batching
- Automated customer communication (confirmations, reminders)
- Easy invoice generation and payment tracking
- Visibility into staff locations and job progress

#### 2. Field Technicians (Vas, Dad)
**Role:** Small appointments, routine service calls, seasonal work

**Current Pain Points:**
- Schedule information scattered across calendar notes
- Missing customer contact info or special instructions
- No easy way to update job status in real-time
- Have to call Viktor for pricing information
- Can't collect credit card payments on-site

**Needs:**
- Mobile-friendly daily route view
- Complete job cards with all customer/property info
- Offline capability for areas with poor signal
- Quick job completion workflow
- On-site invoice/estimate generation
- Standard price list reference

#### 3. Major Job Technicians (Vas, Steven, Vitallik)
**Role:** Installations, complex repairs, landscaping projects

**Current Pain Points:**
- Multi-day jobs hard to track across calendar
- Equipment and material requirements not clearly documented
- Coordination between team members is ad-hoc

**Needs:**
- Multi-day job tracking
- Equipment/material checklists
- Team coordination features
- Photo documentation capability

### Secondary Users (Future Phases)

#### 4. Customers
**Needs:** Self-service portal for requesting work, viewing appointments, paying invoices

#### 5. Sales Staff (Future)
**Needs:** Estimate pipeline management, follow-up automation, proposal tools

---

## Key Features

### Phase 1: Foundation (CRM + Job Tracking)

#### Customer Management
- **Customer profiles** with contact info, address, property details
- **Customer flags** for priority status, red flags, slow payers
- **Property information** including zone count, system type (standard/lake pump), commercial/residential
- **Communication preferences** (SMS opt-in, email opt-in)
- **Service history** tracking all past jobs

#### Job Request Intake
- **Automatic categorization** into "Ready to Schedule" vs "Requires Estimate"
- **Job types:** Seasonal services, repairs, installations, estimates, diagnostics
- **Status workflow:** Requested → Approved → Scheduled → In-Progress → Completed → Closed
- **Source tracking** for lead attribution (website, Google, referral, etc.)

#### Service Catalog
- **Seasonal services** with zone-based pricing (startups, tune-ups, winterizations)
- **Repair services** with standard pricing ($50/head, $100 diagnostic, etc.)
- **Custom pricing** for partner deals (e.g., $700/zone for builder)
- **Time estimates** based on job type and system complexity

#### Admin Dashboard API
- Request volume metrics and trends
- Jobs by status (needs scheduling, scheduled, in-progress, completed)
- Payment status overview (pending, past due)
- Staff availability view

### Phase 2: Field Operations

#### Staff Management
- **Staff profiles** with roles, skills, availability
- **Assignment rules** based on job type and staffing requirements
- **GPS location tracking** during work hours
- **Current job status** visibility for admin

#### Appointment Scheduling
- **Time window assignments** (2-hour windows as Viktor prefers)
- **Route optimization** by location (city batching)
- **Job type batching** (seasonal together, repairs together, etc.)
- **Equipment/material requirements** flagging
- **Weather sensitivity** flagging for outdoor work

#### Job Cards (Staff Mobile View)
- Customer name and contact info
- Property address with map link
- Job type and description
- Materials/equipment needed
- Amount to charge
- Time allocated for job
- Special directions (gate codes, dog warnings, access instructions)
- Customer history and notes

#### Job Completion Workflow (Enforced Sequential Steps)
1. Mark "Arrived" - triggers customer notification
2. Review job scope with customer
3. Complete work
4. Capture photos of completed work
5. Adjust pricing if additional work done
6. Collect payment OR generate invoice
7. Request review (or skip with reason)
8. Update job notes (completion status, materials used, future work needed)
9. Mark "Complete" - triggers next customer notification

#### Notifications
- **Customer notifications:** Appointment confirmation, day-before reminder, "on the way" alert, arrival notification, completion summary
- **Staff notifications:** Daily schedule, running late alert, time remaining warning
- **Admin notifications:** Job completed, payment collected, issue flagged

---

## Business Objectives

### Primary Objectives

1. **Reduce Administrative Time by 70%**
   - Current: 15-20 hours/week on manual tracking, scheduling, communication
   - Target: 4-6 hours/week with automated workflows
   - Metric: Hours spent on administrative tasks per week

2. **Increase Job Capacity by 25%**
   - Current: Limited by scheduling bottleneck and communication overhead
   - Target: Handle 25% more jobs with same staff
   - Metric: Jobs completed per week

3. **Improve Customer Response Time**
   - Current: Hours to days for response during busy season
   - Target: Automated acknowledgment within minutes
   - Metric: Average time from request to first response

4. **Reduce Missed Appointments**
   - Current: Customers forget, staff show up to empty houses
   - Target: 90%+ confirmation rate with automated reminders
   - Metric: No-show rate

5. **Accelerate Payment Collection**
   - Current: Manual invoice creation, manual follow-up
   - Target: Same-day invoicing, automated reminders
   - Metric: Days to payment, past-due rate

### Secondary Objectives

6. **Enable Business Scaling**
   - System should support adding new staff without proportional admin increase
   - Metric: Admin hours per staff member

7. **Improve Data Quality**
   - Eliminate lost information, duplicate entries, outdated records
   - Metric: Data completeness rate

8. **Provide Business Insights**
   - Revenue by service type, customer acquisition cost, profit margins
   - Metric: Availability of key business metrics

---

## User Journey

### Journey 1: New Customer Request (Ready to Schedule)

```
Customer calls/texts Viktor about spring startup
         ↓
Viktor asks them to fill out work request form (or enters manually)
         ↓
Request appears in Admin Dashboard as "Ready to Schedule"
         ↓
System auto-categorizes based on service type and customer history
         ↓
Viktor reviews weekly schedule, clicks "Generate Schedule"
         ↓
System batches jobs by location and job type, proposes schedule
         ↓
Viktor reviews, adjusts if needed, clicks "Send Confirmations"
         ↓
Customers receive SMS: "Your spring startup is scheduled for Tuesday 10am-12pm. Reply YES to confirm."
         ↓
Customer confirms, appointment moves to "Confirmed" status
         ↓
Day before: Customer receives reminder SMS
         ↓
Day of: Staff sees job on mobile app with all details
         ↓
Staff marks "Arrived", customer gets notification
         ↓
Staff completes work, follows completion workflow
         ↓
Staff collects payment or sends invoice
         ↓
Job marked complete, customer gets summary
         ↓
If invoice sent, automated reminders at 3 days, 7 days, 14 days
```

### Journey 2: Field Technician Daily Workflow

```
Morning: Tech opens mobile app, sees daily route
         ↓
Route shows optimized order of 8-10 jobs with time allocations
         ↓
Tech reviews first job card: customer info, address, job type, special notes
         ↓
Tech drives to location (GPS tracking active)
         ↓
Tech arrives, marks "Arrived" in app
         ↓
Customer receives "Your technician has arrived" notification
         ↓
Tech completes work, takes photos
         ↓
Tech opens completion form, enters:
  - Completion status (complete/partial/reschedule)
  - Materials used
  - Payment collected or invoice needed
  - Notes for future reference
         ↓
Tech requests review or skips with reason
         ↓
Tech marks "Complete"
         ↓
Next customer automatically notified of ETA
         ↓
Tech proceeds to next job
         ↓
End of day: All job data synced to central database
```

### Journey 3: Admin Daily Operations

```
Morning: Viktor opens Admin Dashboard
         ↓
Sees overnight requests that came in (auto-categorized)
         ↓
Reviews any flagged items needing attention
         ↓
Checks today's schedule - all staff routes visible
         ↓
Monitors real-time progress via GPS and job status updates
         ↓
Handles any escalations (customer complaints, schedule changes)
         ↓
End of day: Reviews completed jobs
         ↓
System auto-generates invoices for unpaid jobs
         ↓
Viktor reviews and sends invoices with one click
         ↓
Checks payment status, system handles reminders automatically
```

---

## Success Criteria

### Hackathon Success (January 23, 2025)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Working End-to-End Flow** | Complete job lifecycle from request to completion | Demo video showing full workflow |
| **API Completeness** | 25-30 endpoints covering Phase 1+2 | API documentation |
| **Test Coverage** | 70%+ code coverage | pytest coverage report |
| **Code Quality** | Zero linting errors, full type hints | Ruff + MyPy + Pyright passing |
| **Documentation** | Complete DEVLOG, README, steering docs | File presence and quality |
| **Kiro Usage** | Formal spec, custom prompts, agents | .kiro/ directory contents |

### Production Success (Future)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| **Admin Time Reduction** | 70% reduction | Weekly time tracking |
| **Job Capacity Increase** | 25% more jobs/week | Jobs completed comparison |
| **Customer Response Time** | < 5 minutes for auto-response | System logs |
| **No-Show Rate** | < 10% | Appointment tracking |
| **Payment Collection** | < 14 days average | Invoice aging report |
| **User Adoption** | All staff using mobile app daily | Login/usage metrics |
| **Data Quality** | 95%+ complete customer records | Data audit |
| **System Uptime** | 99.5%+ availability | Monitoring |

---

## Business Context

### Team Structure

| Role | Person(s) | Responsibilities | System Access |
|------|-----------|------------------|---------------|
| Owner/Manager | Viktor | Coordination, estimates, scheduling, customer relations | Full admin |
| Field Tech (Small Jobs) | Dad | Small appointments, routine service calls | Staff mobile |
| Field Tech (Major Jobs) | Vas, Steven, Vitallik | Major jobs, installations, complex repairs | Staff mobile |
| Referral Sources | Gennadiy, Vasiliy | Word-of-mouth lead generation | None (leads forwarded to Viktor) |

### Service Categories

| Category | Examples | Staffing | Pricing Model | Duration |
|----------|----------|----------|---------------|----------|
| Seasonal Services | Spring startup, summer tune-up, winterization | 1 person | Zone-based ($X per zone) | 30-60 min |
| Small Repairs | Broken sprinkler heads, minor leaks | 1 person | Flat rate ($50/head) | 30 min |
| Diagnostics | System troubleshooting | 1 person | $100 first hour + hourly | Variable |
| Major Repairs | Pipe replacement, valve repair | 2 people | Custom estimate | 2-4 hours |
| Installations | New irrigation systems | 2-4 people | Zone-based ($700/zone for partners) | 1+ days |
| Landscaping | Sod, plants, hardscaping | 2-4 people | Custom estimate | 1-2+ days |

### Equipment Requirements

| Job Type | Equipment Needed |
|----------|------------------|
| Seasonal Services | Standard tools (in vehicle) |
| Winterizations | Compressor |
| Major Repairs | Pipe puller, utility trailer |
| Installations | Pipe puller, utility trailer |
| Landscaping | Pipe puller, skid steer, utility trailer, dump trailer |

### Geographic Coverage

Primary service area: Twin Cities metro
- Eden Prairie
- Plymouth
- Maple Grove
- Brooklyn Park
- Rogers
- Surrounding suburbs

### Seasonal Patterns

| Season | Primary Work | Volume |
|--------|--------------|--------|
| Spring (Mar-May) | System startups | HIGH - 150+ jobs/week |
| Summer (Jun-Aug) | Repairs, tune-ups, installations | MEDIUM |
| Fall (Sep-Nov) | Winterizations | HIGH - 150+ jobs/week |
| Winter (Dec-Feb) | Planning, equipment maintenance | LOW |

---

## Constraints and Considerations

### Technical Constraints
- Must work offline for field technicians (poor cell coverage in some areas)
- Must be mobile-friendly (staff use phones, not tablets)
- Must integrate with existing Google Calendar (transition period)
- Must handle concurrent users during peak season

### Business Constraints
- Staff have varying technical comfort levels (especially Dad)
- Cannot disrupt operations during busy season for training
- Must be simple enough that Viktor can manage without IT support
- Budget-conscious - prefer open-source solutions where possible

### Regulatory Considerations
- SMS opt-in compliance required for marketing messages
- Mechanic's lien rules for unpaid work (45-day notification, 120-day filing)
- Lien eligibility varies by service type (installations yes, seasonal services no)

### User Experience Priorities
1. **Simplicity over features** - Viktor emphasized this repeatedly
2. **Visual status indicators** - Color-coding is essential (red/yellow/green)
3. **Mobile-first for field staff** - Must work on phones
4. **Minimal clicks** - Every extra step costs time during busy season
