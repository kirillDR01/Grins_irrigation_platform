# Phase 6: AI Agent Integration Planning

## Overview

Phase 6 integrates an AI assistant powered by Pydantic AI directly into the Grin's Irrigation operations platform. The AI will automate Viktor's most time-consuming manual tasks, potentially saving 15-20 hours per week during peak season.

## Business Context

### Current Pain Points (From Viktor's Workflow Analysis)

During peak seasons (spring startups, fall winterizations), Viktor handles:
- **150+ individual jobs per week**
- **5+ minutes per job** for scheduling alone (typing into calendar, texting clients)
- **15-20+ hours per week** on administrative tasks
- **20-30 overnight requests** that need manual categorization each morning

### Key Manual Processes to Automate

| Process | Current Time | Pain Level | AI Opportunity |
|---------|--------------|------------|----------------|
| Batch scheduling (sorting, typing, texting) | 8-10 hrs/wk | CRITICAL | Schedule generation + auto-communication |
| Job request categorization | 3-4 hrs/wk | HIGH | Auto-categorize + suggest pricing |
| Customer communication | 2-3 hrs/wk | HIGH | Draft confirmations, reminders, follow-ups |
| Business queries | 1-2 hrs/wk | MEDIUM | Natural language database queries |
| Estimate generation | 1-2 hrs/wk | MEDIUM | Auto-generate based on job type + history |

---

## AI Capabilities (Prioritized)

### Priority 1: Intelligent Batch Scheduling Assistant

**Problem Solved:** Viktor spends 8-10 hours/week manually:
- Reviewing 20-30 job requests
- Mentally calculating time estimates (zone count, system type, job type)
- Batching by location (city), job type, and staffing requirements
- Typing each appointment into calendar
- Individually texting each customer for confirmation

**AI Solution - Integrated into Schedule Generation Page:**

```
┌─────────────────────────────────────────────────────────────┐
│ Schedule Generation                                          │
├─────────────────────────────────────────────────────────────┤
│ 🤖 AI Schedule Assistant                                     │
│                                                              │
│ "I found 47 jobs ready to schedule. Here's my recommended   │
│  schedule for next week:"                                    │
│                                                              │
│ MONDAY - Eden Prairie (12 startups)                          │
│   Vas: 6 jobs, 4.5 hrs estimated                            │
│   Dad: 6 jobs, 5 hrs estimated                              │
│   Route optimized: 23 miles total                           │
│                                                              │
│ TUESDAY - Plymouth (8) + Maple Grove (6)                     │
│   Vas: Plymouth route, 4 hrs                                │
│   Dad: Maple Grove route, 3.5 hrs                           │
│                                                              │
│ WEDNESDAY - Brooklyn Park (5) + Rogers (5) + Repairs (3)    │
│   Vas: Brooklyn Park → Rogers, 5 hrs                        │
│   Dad: 3 repair jobs (various), 4 hrs                       │
│                                                              │
│ ⚠️ 3 customers have availability conflicts - need review    │
│ ⚠️ 1 job requires compressor (winterization in spring batch)│
│                                                              │
│ [Accept Schedule] [Modify] [Regenerate]                      │
└─────────────────────────────────────────────────────────────┘
```

**Scheduling Factors the AI Considers:**
- **Job Type Batching:** Seasonal services together, repairs together, installs together
- **Location Clustering:** Group by city to minimize drive time
- **Time Estimates:** Based on zone count + system type (standard vs lake pump, residential vs commercial)
- **Staff Skills & Availability:** Match job requirements to staff capabilities
- **Equipment Requirements:** Compressor for winterizations, pipe puller for installs
- **First-Come-First-Serve:** With 2-4 day buffer for location optimization
- **Weather Sensitivity:** Flag outdoor-sensitive jobs on rainy days
- **Staffing Rules:** 1 person for service calls, 2 for major repairs, 2-4 for installs

**User Flow:**
1. Viktor opens Schedule Generation page
2. AI analyzes all "Ready to Schedule" jobs
3. AI generates optimized weekly schedule
4. Viktor reviews, adjusts if needed
5. One-click to send confirmation texts to all customers
6. System tracks confirmations and flags non-responders

---

### Priority 2: Automated Job Request Categorization

**Problem Solved:** Viktor manually categorizes every incoming request into:
- "Ready to Schedule" (seasonal work, small repairs, approved estimates)
- "Requires Estimate" (new installs, complex repairs, diagnostics)

**AI Solution - Integrated into Job Requests Dashboard:**

```
┌─────────────────────────────────────────────────────────────┐
│ New Requests (23 overnight)                     [Refresh 🔄] │
├─────────────────────────────────────────────────────────────┤
│ 🤖 AI Auto-Categorized:                                      │
│                                                              │
│ ✅ READY TO SCHEDULE (18)                                    │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ Spring Startups (12)                                     ││
│ │   • Auto-priced at $45-65/zone based on zone count       ││
│ │   • All existing customers with system data on file      ││
│ │                                                          ││
│ │ Winterizations (4)                                       ││
│ │   • Auto-priced at $45-65/zone                           ││
│ │   • Equipment note: Compressor required                  ││
│ │                                                          ││
│ │ Small Repairs (2)                                        ││
│ │   • "2 broken sprinkler heads" → $100 (2 × $50/head)     ││
│ │   • "Leaking valve" → $75 estimate                       ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ 📋 NEEDS ESTIMATE (4)                                        │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ • New System Install - Mike Johnson (new customer)       ││
│ │   AI Note: "Large backyard" mentioned, recommend site    ││
│ │   visit to confirm zone count                            ││
│ │                                                          ││
│ │ • "System not working" - Jane Smith                      ││
│ │   AI Note: Vague description, needs $100 diagnostic      ││
│ │                                                          ││
│ │ • Major repair - "multiple valves broken"                ││
│ │   AI Note: Complexity unclear, recommend estimate visit  ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ⚠️ NEEDS REVIEW (1)                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ • John Smith - Existing customer, NEW property           ││
│ │   AI Question: Apply existing customer pricing or        ││
│ │   treat as new property requiring site visit?            ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ 🚫 RED FLAG (0)                                              │
│   No matches against red flag customer list                 │
│                                                              │
│ [Approve All Ready] [Review Individually] [Bulk Actions ▼]   │
└─────────────────────────────────────────────────────────────┘
```

**What the AI Does:**
- Parses job request descriptions using NLP
- Matches against service catalog for automatic pricing
- Identifies existing vs new customers
- Cross-references red flag customer list
- Suggests pricing based on zone count and system type
- Flags requests needing human judgment
- Identifies partner/builder requests for special pricing

---

### Priority 3: Customer Communication Drafts

**Problem Solved:** Viktor individually texts each customer for:
- Appointment confirmations
- Day-before reminders
- "On the way" notifications
- Invoice follow-ups (past due)
- Estimate follow-ups (no response)

**AI Solution - Communication Panel in Customer/Job Detail:**

```
┌─────────────────────────────────────────────────────────────┐
│ Customer: John Smith                                         │
│ Job: Spring Startup - Scheduled Tuesday 10am-12pm           │
├─────────────────────────────────────────────────────────────┤
│ 🤖 Suggested Communications:                                 │
│                                                              │
│ ┌─ CONFIRMATION (Ready to send) ─────────────────────────┐  │
│ │ "Hi John! Your spring startup is scheduled for         │  │
│ │ Tuesday, Jan 28 between 10am-12pm. We'll text when     │  │
│ │ we're on our way. Reply YES to confirm or let us       │  │
│ │ know if you need to reschedule. - Grin's Irrigation"   │  │
│ │                                                        │  │
│ │ [Send Now] [Edit] [Schedule for Later]                 │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌─ DAY-BEFORE REMINDER (Scheduled: Mon 9am) ─────────────┐  │
│ │ "Reminder: Your spring startup is tomorrow between     │  │
│ │ 10am-12pm. Please ensure access to your irrigation     │  │
│ │ system. See you then! - Grin's Irrigation"             │  │
│ │                                                        │  │
│ │ [Edit] [Cancel Scheduled]                              │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                              │
│ ┌─ ON-THE-WAY (Auto-triggered when staff marks en route) ─┐ │
│ │ "Hi John! Our technician Vas is on his way and should  │ │
│ │ arrive in about 15 minutes. - Grin's Irrigation"       │ │
│ └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Bulk Communication for Invoice/Estimate Follow-ups:**

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Payment Follow-up Assistant                               │
├─────────────────────────────────────────────────────────────┤
│ 3 invoices are past due. Suggested follow-up texts:         │
│                                                              │
│ ┌─ Invoice #1234 - Jane Doe - $285 - 7 days overdue ──────┐ │
│ │ "Hi Jane, just a friendly reminder that invoice #1234   │ │
│ │ for $285 is now past due. You can pay via Venmo         │ │
│ │ @grins-irrigation, Zelle, or check. Let us know if      │ │
│ │ you have any questions! - Viktor, Grin's Irrigation"    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌─ Invoice #1198 - Bob Wilson - $450 - 14 days overdue ───┐ │
│ │ "Hi Bob, this is a second reminder about invoice #1198  │ │
│ │ for $450. Please arrange payment at your earliest       │ │
│ │ convenience. Per our terms, a late fee may apply after  │ │
│ │ 30 days. Thanks! - Viktor"                              │ │
│ │                                                         │ │
│ │ ⚠️ AI Note: Customer on "slow payer" list               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Send All] [Review Each] [Skip for Now]                      │
└─────────────────────────────────────────────────────────────┘
```

**Communication Types:**
- Appointment confirmations
- Day-before reminders
- On-the-way notifications
- Completion summaries
- Invoice generation and sending
- Payment reminders (3 days before due, day of, weekly after)
- Estimate follow-ups (1 week, 2 weeks, monthly)
- Seasonal service reminders (to existing customers)

---

### Priority 4: Natural Language Business Queries

**Problem Solved:** Viktor needs quick answers to business questions:
- "Which customers haven't scheduled winterization yet?"
- "How many startups do we have in Plymouth next week?"
- "Who owes us money?"
- "What's our revenue this month vs last month?"
- "Show me all jobs for the builder partner"

**AI Solution - Chat Interface in Dashboard:**

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Ask anything about your business...                       │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Viktor: "Which existing customers haven't scheduled     │ │
│ │          winterization yet?"                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ 🤖 I found 47 customers who had spring startups this year   │
│    but haven't scheduled winterization:                      │
│                                                              │
│    By City:                                                  │
│    • Eden Prairie: 12 customers                              │
│    • Plymouth: 8 customers                                   │
│    • Maple Grove: 15 customers                               │
│    • Brooklyn Park: 7 customers                              │
│    • Rogers: 5 customers                                     │
│                                                              │
│    Total potential revenue: ~$2,820 (avg $60/winterization) │
│                                                              │
│    Would you like me to:                                     │
│    [Draft Reminder Campaign] [Show Full List] [Export CSV]   │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Viktor: "Who owes us money?"                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ 🤖 Outstanding invoices: $3,450 total                        │
│                                                              │
│    Current (not yet due): $1,200 (4 invoices)               │
│    Past due 1-7 days: $850 (3 invoices)                     │
│    Past due 8-14 days: $650 (2 invoices)                    │
│    Past due 15-30 days: $450 (1 invoice) ⚠️                 │
│    Past due 30+ days: $300 (1 invoice) 🚨                   │
│                                                              │
│    [View All Invoices] [Draft Follow-up Texts] [Export]      │
└─────────────────────────────────────────────────────────────┘
```

**Query Categories:**
- **Customer queries:** "Show customers in Eden Prairie", "Who hasn't scheduled this season?"
- **Job queries:** "How many startups next week?", "Show all pending estimates"
- **Financial queries:** "Revenue this month", "Outstanding invoices", "Average job value"
- **Staff queries:** "What's Vas's schedule tomorrow?", "Who's available Friday?"
- **Trend queries:** "Compare this spring to last spring", "Busiest day of the week"

---

### Priority 5: Smart Estimate Generation

**Problem Solved:** For jobs requiring estimates, Viktor manually:
- Reviews the request details
- Calculates pricing based on zone count, system type, complexity
- Writes up the estimate
- Sends to customer and tracks follow-up

**AI Solution - Estimate Generator in Job Detail:**

```
┌─────────────────────────────────────────────────────────────┐
│ Job: New System Install - Mike Johnson                       │
│ Status: Needs Estimate                                       │
├─────────────────────────────────────────────────────────────┤
│ 🤖 AI Estimate Assistant                                     │
│                                                              │
│ Based on customer request: "New irrigation system for       │
│ front and back yard, about 1/2 acre lot"                    │
│                                                              │
│ ┌─ ANALYSIS ───────────────────────────────────────────────┐│
│ │ Estimated zones: 8-10 (based on lot size)                ││
│ │ System type: Standard residential                        ││
│ │ Similar completed jobs: 3 in same area                   ││
│ │   • 123 Oak St (8 zones): $5,600                        ││
│ │   • 456 Maple Ave (10 zones): $7,000                    ││
│ │   • 789 Pine Rd (9 zones): $6,300                       ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ┌─ RECOMMENDED QUOTE ──────────────────────────────────────┐│
│ │ Mid-range estimate: $6,300 (9 zones × $700/zone)        ││
│ │                                                          ││
│ │ Breakdown:                                               ││
│ │   Materials: ~$3,150 (50%)                              ││
│ │   Labor (2 people, 1.5 days): ~$1,800                   ││
│ │   Equipment: ~$450                                       ││
│ │   Margin: ~$900 (14%)                                   ││
│ └──────────────────────────────────────────────────────────┘│
│                                                              │
│ ⚠️ AI Recommendation: Customer mentioned "large backyard"   │
│    Consider scheduling site visit to confirm zone count     │
│    before sending final estimate.                           │
│                                                              │
│ [Generate Estimate PDF] [Schedule Site Visit] [Adjust Quote]│
└─────────────────────────────────────────────────────────────┘
```

**Estimate Intelligence:**
- Analyzes job description for scope indicators
- References similar completed jobs for pricing
- Calculates based on service catalog rates
- Factors in location (some areas have higher costs)
- Identifies when site visit is recommended
- Generates professional PDF estimate
- Tracks estimate status and auto-schedules follow-ups

---

## Technical Architecture

### Technology Stack

**Backend:**
- **Pydantic AI** - AI agent framework with type-safe tool definitions
- **OpenAI GPT-4** or **Anthropic Claude** - LLM provider (configurable)
- **FastAPI** - API endpoints for AI interactions
- **PostgreSQL** - Existing database for context retrieval

**Frontend:**
- **React + TypeScript** - Existing frontend stack
- **TanStack Query** - For AI request state management
- **Streaming responses** - For real-time AI output

### Backend Structure

```
src/grins_platform/
├── services/
│   └── ai/
│       ├── __init__.py
│       ├── agent.py                 # Main Pydantic AI agent configuration
│       ├── dependencies.py          # AI service dependencies
│       │
│       ├── tools/                   # AI tool definitions
│       │   ├── __init__.py
│       │   ├── scheduling.py        # Schedule generation tools
│       │   ├── categorization.py    # Job categorization tools
│       │   ├── communication.py     # Message drafting tools
│       │   ├── queries.py           # Business query tools
│       │   └── estimates.py         # Estimate generation tools
│       │
│       ├── prompts/                 # System prompts and templates
│       │   ├── __init__.py
│       │   ├── system.py            # Base system prompts
│       │   ├── scheduling.py        # Scheduling-specific prompts
│       │   └── templates.py         # Response templates
│       │
│       └── context/                 # Context retrieval
│           ├── __init__.py
│           ├── customers.py         # Customer context builder
│           ├── jobs.py              # Job context builder
│           └── business.py          # Business metrics context
│
├── api/v1/
│   └── ai.py                        # AI API endpoints
│
└── schemas/
    └── ai.py                        # AI request/response schemas
```

### Frontend Structure

```
frontend/src/features/
├── ai/                              # AI feature module
│   ├── components/
│   │   ├── AIAssistantPanel.tsx     # Main chat interface
│   │   ├── AIScheduleGenerator.tsx  # Schedule generation UI
│   │   ├── AICategorization.tsx     # Job categorization UI
│   │   ├── AICommunicationDrafts.tsx # Communication drafts
│   │   ├── AIEstimateGenerator.tsx  # Estimate generation UI
│   │   └── AIQueryChat.tsx          # Natural language query chat
│   │
│   ├── hooks/
│   │   ├── useAIChat.ts             # Chat interaction hook
│   │   ├── useAISchedule.ts         # Schedule generation hook
│   │   └── useAICategorize.ts       # Categorization hook
│   │
│   ├── api/
│   │   └── aiApi.ts                 # AI API client
│   │
│   └── types/
│       └── index.ts                 # AI-related types
│
├── dashboard/
│   └── components/
│       └── DashboardPage.tsx        # Add AI chat widget
│
├── schedule/
│   └── components/
│       └── ScheduleGenerate.tsx     # Add AI schedule generator
│
├── jobs/
│   └── components/
│       └── JobList.tsx              # Add AI categorization panel
│       └── JobDetail.tsx            # Add AI estimate generator
│
└── customers/
    └── components/
        └── CustomerDetail.tsx       # Add AI communication drafts
```

### API Endpoints

```
POST /api/v1/ai/chat
  - General chat interface for natural language queries
  - Streaming response support

POST /api/v1/ai/schedule/generate
  - Generate optimized schedule for given date range
  - Returns proposed schedule with explanations

POST /api/v1/ai/jobs/categorize
  - Categorize batch of job requests
  - Returns categorization with confidence scores

POST /api/v1/ai/communication/draft
  - Generate communication drafts for customer
  - Supports: confirmation, reminder, follow-up types

POST /api/v1/ai/estimate/generate
  - Generate estimate for job request
  - Returns pricing breakdown and recommendations
```

### Pydantic AI Agent Configuration

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Main agent with tools
agent = Agent(
    model=OpenAIModel('gpt-4-turbo'),
    system_prompt="""You are an AI assistant for Grin's Irrigation, 
    a field service company in the Twin Cities area. You help Viktor 
    manage scheduling, customer communication, and business operations.
    
    Key business rules:
    - Seasonal services (startups, winterizations) are priced by zone count
    - Standard residential: $45-65 per zone
    - Commercial/lake pump systems take longer
    - Batch jobs by location (city) and job type
    - First-come-first-serve with 2-4 day buffer for route optimization
    - Staff: Vas and Dad for service calls, Viktor for estimates
    """,
    tools=[
        get_pending_jobs,
        get_customer_info,
        get_service_catalog,
        generate_schedule,
        draft_communication,
        calculate_estimate,
        query_database,
    ]
)
```

---

## Implementation Phases

### Phase 6.1: Foundation (Week 1)
- Set up Pydantic AI infrastructure
- Create base agent with system prompts
- Implement database context retrieval tools
- Create basic chat API endpoint
- Build AI chat widget component

### Phase 6.2: Natural Language Queries (Week 2)
- Implement query tools for customers, jobs, invoices
- Build query result formatting
- Add query suggestions and examples
- Integrate chat widget into dashboard

### Phase 6.3: Job Categorization (Week 3)
- Implement categorization logic and tools
- Build categorization UI panel
- Add confidence scoring
- Integrate into job requests page

### Phase 6.4: Communication Drafts (Week 4)
- Implement message template system
- Build communication draft tools
- Create bulk communication UI
- Add scheduling for automated messages

### Phase 6.5: Schedule Generation (Week 5-6)
- Implement scheduling algorithm tools
- Build schedule preview UI
- Add constraint handling (availability, equipment)
- Integrate with existing schedule page

### Phase 6.6: Estimate Generation (Week 7)
- Implement estimate calculation tools
- Build estimate preview UI
- Add similar job reference lookup
- Generate PDF estimates

### Phase 6.7: Polish & Testing (Week 8)
- End-to-end testing
- Performance optimization
- Error handling improvements
- Documentation

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Weekly admin time | 15-20 hrs | 5-8 hrs | Time tracking |
| Time to schedule 50 jobs | 4-5 hrs | 30 min | Stopwatch test |
| Job categorization time | 2-3 hrs/day | 15 min/day | Stopwatch test |
| Customer response time | Hours | Minutes | System logs |
| Missed follow-ups | ~20%/week | <5%/week | Audit |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI makes incorrect categorizations | Confidence scores + human review for low-confidence |
| AI generates wrong pricing | Always show calculation breakdown, require approval |
| LLM costs too high | Caching, prompt optimization, usage monitoring |
| AI sends wrong messages | Draft-only mode, require explicit send approval |
| System downtime | Graceful degradation to manual workflows |

---

## Dependencies

**External:**
- OpenAI API or Anthropic API account
- API keys and billing setup

**Internal (from previous phases):**
- Customer management (Phase 1) ✅
- Job request management (Phase 2) ✅
- Service catalog (Phase 2) ✅
- Staff management (Phase 2) ✅
- Scheduling system (Phase 3-4) ✅
- Route optimization (Phase 4) ✅

---

## UI Placement Strategy

### Current AI Feature Placements

| AI Feature | Primary Location | Purpose |
|------------|------------------|---------|
| Schedule Assistant | Schedule Generation Page | Batch scheduling optimization |
| Categorization | Job Requests Dashboard | Auto-categorize incoming jobs |
| Communication Drafts | Customer/Job Detail pages | Draft messages per customer |
| Business Queries | Dashboard (chat widget) | Natural language queries |
| Estimate Generator | Job Detail page | Generate estimates |

### Recommended Enhancements

#### 1. Morning Briefing Panel (NEW - Dashboard)

Viktor's morning workflow is: check overnight requests → categorize → review schedule → send communications. A unified "Morning Briefing" panel consolidates this into one entry point:

```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 Good morning, Viktor! Here's your daily briefing:        │
├─────────────────────────────────────────────────────────────┤
│ 📥 OVERNIGHT REQUESTS (23 new)                              │
│    • 18 auto-categorized as Ready to Schedule               │
│    • 4 need estimates                                       │
│    • 1 needs your review                                    │
│    [Review All →]                                           │
│                                                              │
│ 📅 TODAY'S SCHEDULE                                          │
│    • Vas: 6 jobs in Eden Prairie                            │
│    • Dad: 5 jobs in Plymouth                                │
│    • 2 customers haven't confirmed yet ⚠️                   │
│    [View Schedule →]                                        │
│                                                              │
│ 💬 COMMUNICATIONS PENDING                                    │
│    • 12 confirmations ready to send                         │
│    • 3 payment reminders due                                │
│    [Send All Confirmations] [Review Reminders]              │
│                                                              │
│ 💰 OUTSTANDING                                               │
│    • $3,450 in unpaid invoices                              │
│    • 2 invoices past 14 days                                │
│    [View Details →]                                         │
└─────────────────────────────────────────────────────────────┘
```

**Rationale:** Single entry point for Viktor's morning routine. AI does the heavy lifting of summarizing everything he needs to know.

#### 2. Communications Queue (NEW - Dashboard Section)

Instead of only having contextual drafts on individual Customer/Job pages, add a centralized "Communications Queue" to the Dashboard:

```
┌─────────────────────────────────────────────────────────────┐
│ 📬 Communications Queue                          [View All] │
├─────────────────────────────────────────────────────────────┤
│ PENDING CONFIRMATIONS (12)                                  │
│   Ready to send for Tuesday's schedule                      │
│   [Send All] [Review]                                       │
│                                                              │
│ SCHEDULED REMINDERS (8)                                     │
│   Day-before reminders queued for Monday 9am                │
│   [View] [Pause All]                                        │
│                                                              │
│ OVERDUE FOLLOW-UPS (3)                                      │
│   Payment reminders that should have been sent              │
│   [Send Now] [Review]                                       │
└─────────────────────────────────────────────────────────────┘
```

**Rationale:** Viktor shouldn't have to visit each customer page to see pending messages. This provides bulk operations and a unified view of all communication status.

#### 3. Business Query Chat - Designed for Future Global Access

Start with Dashboard-only placement, but design the component to be relocatable:

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| Dashboard only | Simple, one location | Must navigate to dashboard to ask questions | **Start here** |
| Global floating button | Ask from any page, context-aware | More UI complexity, might feel cluttered | Consider for v2 |
| Command palette (Cmd+K) | Power-user friendly, no screen space | Less discoverable for non-technical users | Not recommended for Viktor |

**Implementation:** Build `AIQueryChat` as a standalone component that can be embedded in Dashboard initially, then moved to a global position (floating button or sidebar) based on user feedback.

#### 4. Mobile/Field Staff AI Features

The current plan focuses on Viktor's admin view. For field staff (Vas, Dad), consider:

| Feature | Admin (Viktor) | Field Staff (Mobile) |
|---------|----------------|---------------------|
| Schedule Generation | ✅ Full access | ❌ Not needed |
| Job Categorization | ✅ Full access | ❌ Not needed |
| Communication Drafts | ✅ Full access | ✅ Simplified ("Send on-the-way" button) |
| Business Queries | ✅ Full access | ✅ Limited ("What's my next job?", "Customer phone?") |
| Estimate Generator | ✅ Full access | ❌ Not needed |
| Job Completion AI | ❌ N/A | ✅ AI-suggested completion notes |

**Mobile-Specific AI Features:**
- Quick "Send on-the-way" notification with one tap
- Voice-to-text for job completion notes
- AI-suggested notes based on job type ("Winterization complete, all zones blown out")
- Simple queries: "What's the gate code for this customer?"

### Final Placement Summary

| AI Feature | Primary Location | Secondary Location |
|------------|------------------|-------------------|
| Morning Briefing | Dashboard (NEW) | - |
| Schedule Assistant | Schedule Generation | - |
| Categorization | Job Requests | Dashboard briefing summary |
| Communication Drafts | Customer/Job Detail | Dashboard "Communications Queue" |
| Business Queries | Dashboard chat | Consider global later |
| Estimate Generator | Job Detail | - |
| Field Staff AI | Mobile job view | - |

---

## Decisions Made ✅

### Core Principle: Human-in-the-Loop

**AI NEVER executes actions without explicit user approval.** The flow is always:

```
1. AI ANALYZES    → Reviews data, identifies opportunities
2. AI RECOMMENDS  → Presents proposed changes with reasoning
3. USER REVIEWS   → Viktor sees exactly what will happen
4. USER APPROVES  → Explicit click to confirm (or reject/modify)
5. SYSTEM EXECUTES → Only after approval, action is taken
```

**Examples:**

| Action | AI Does | User Must Approve |
|--------|---------|-------------------|
| Schedule generation | Proposes optimized schedule | "Accept Schedule" button |
| Job categorization | Suggests categories + pricing | "Approve All" or individual approvals |
| Send confirmation texts | Drafts messages | "Send" button for each or bulk |
| Create estimate | Calculates pricing | "Generate Estimate" button |
| Payment reminder | Drafts follow-up text | "Send Reminder" button |

**No auto-execution.** Even for low-risk actions like "on-the-way" notifications, user clicks to send.

| Question | Decision | Rationale |
|----------|----------|-----------|
| **SMS Provider** | Twilio | Industry standard, good API, two-way SMS support |
| **Invoice System** | Skip for Phase 6 | Focus on AI core features first, invoices can be Phase 7 |
| **LLM Provider** | OpenAI GPT-4 (design for provider swap) | Start with OpenAI, abstract for easy switch to Anthropic |
| **Autonomy Level** | Everything requires approval | Safety first - all AI suggestions need human confirmation |
| **User Verification Flow** | Recommend → Preview → Approve → Execute | AI never executes actions without explicit user approval |
| **Streaming Responses** | Yes, implement streaming | Better UX for chat interface |
| **Offline Mode** | Not in scope | Defer to future phase |
| **Weather Integration** | Rain certainty = bad weather | Flag jobs when forecast shows certain rain |
| **AI Branding** | "AI Assistant" (no personality) | Keep it professional and tool-like |
| **Conversation History** | Session-only | No persistence to DB, fresh each session |
| **Confidence Display** | Internal only | Use for routing, don't show scores to user |
| **Data Privacy / PII** | No PII sent to LLM APIs | Use IDs and placeholders, fill in PII locally after AI response |
| **Weather API** | OpenWeatherMap (free tier) | 5-day forecast, >70% precipitation = bad weather, flag only (no auto-reschedule) |
| **Confidence Thresholds** | HIGH (≥85%) → Ready to Schedule, LOW (<85%) → Needs Review | Simple binary routing, no medium tier for v1 |
| **Caching Strategy** | No caching for v1 | Add Redis caching later if LLM costs become issue |
| **Error Handling** | Graceful degradation with manual fallback | Show "AI unavailable" + enable manual workflow |
| **Audit Trail** | `ai_audit_log` table | Log action summaries, not full prompts (cost/privacy) |
| **Testing Strategy** | Mock-first approach | Use GPT-3.5-turbo for integration tests, mock for unit tests |
| **Undo Flow** | Prevention over correction | Since all actions require approval, focus on clear previews rather than undo |
| **Rate Limiting** | 100 requests/user/day, $50/month alert | Prevent runaway costs, alert before budget exceeded |
| **Session History** | 50 messages max, browser tab lifetime | Clear button available, no cross-session persistence |
| **Context Window** | Max 4000 tokens, prioritize recent data | Truncate oldest context if exceeded |
| **Multi-User** | Single admin (Viktor) for v1 | Multi-user concurrency deferred to future |
| **Mobile AI** | Deferred to Phase 7 | Focus on admin dashboard for Phase 6 |
| **Message Sent Log** | Add to Communications Queue | Visibility into what was sent, when, to whom |

## Open Questions (Resolved)

~~1. **LLM Provider:** OpenAI GPT-4 vs Anthropic Claude?~~ → **OpenAI GPT-4**
~~2. **Autonomy Level:** How much should AI auto-execute vs require approval?~~ → **All requires approval**
~~3. **Message Sending:** Should AI send messages directly or always draft for review?~~ → **Draft only, human sends**
~~4. **Offline Capability:** Should AI features work offline for field staff?~~ → **Not in scope**
~~5. **Cost Budget:** Monthly LLM API budget ceiling?~~ → **Design cost-conscious, no hard ceiling**
~~6. **Global Chat:** Should business query chat be accessible from all pages?~~ → **Dashboard only for v1**

---

## Additional Technical Specifications

### Rate Limiting & Cost Controls

**Decision:** Implement rate limiting to prevent runaway LLM costs

| Control | Limit | Action When Exceeded |
|---------|-------|---------------------|
| Per-user daily requests | 100 requests/day | Show "Daily limit reached, resets at midnight" |
| Per-request token budget | 4,000 input + 2,000 output tokens | Truncate context, warn user |
| Monthly cost alert | $50/month | Email alert to admin |
| Monthly hard cap | $100/month (optional) | Disable AI features, enable manual fallback |

**Implementation:**
```python
# Track in Redis or DB
ai_usage = {
    "user_id": "viktor",
    "date": "2025-01-26",
    "request_count": 47,
    "total_tokens": 125000,
    "estimated_cost_usd": 12.50
}
```

**UX When Rate Limited:**
- Show friendly message: "You've used your 100 AI requests for today. AI features will be available again tomorrow, or you can continue manually."
- All manual workflows remain available
- Admin can override limits if needed

---

### Context Window Management

**Decision:** Prioritize recent, relevant data within token limits

| Context Type | Priority | Max Tokens | Truncation Strategy |
|--------------|----------|------------|---------------------|
| Current request/job | HIGHEST | 500 | Never truncate |
| Customer info | HIGH | 300 | Latest address, phone only |
| Recent job history | MEDIUM | 500 | Last 5 jobs for customer |
| Service catalog | MEDIUM | 400 | Only relevant services |
| Staff availability | LOW | 200 | Today + next 7 days |
| Business rules | LOWEST | 100 | Static, always included |

**Total Budget:** 4,000 tokens max input

**Truncation Order (when over budget):**
1. Remove older job history (keep last 3)
2. Remove staff availability beyond 3 days
3. Summarize customer info
4. Never remove current request or business rules

**Implementation:**
```python
def build_context(request, customer, jobs, catalog, staff):
    context = []
    token_count = 0
    MAX_TOKENS = 4000
    
    # Always include (never truncate)
    context.append(format_request(request))  # ~500 tokens
    context.append(BUSINESS_RULES)  # ~100 tokens
    
    # Add in priority order, truncate if needed
    if token_count + 300 < MAX_TOKENS:
        context.append(format_customer(customer))
    
    # ... continue with lower priority items
    
    return "\n".join(context)
```

---

### Session History Management

**Decision:** Session-scoped chat with clear limits

| Setting | Value | Rationale |
|---------|-------|-----------|
| Session scope | Browser tab lifetime | Fresh context each session |
| Max messages | 50 messages | Prevent context bloat |
| Clear button | Yes, visible in chat UI | User control |
| Cross-session | No persistence | Privacy, simplicity |
| Export | Not in v1 | Future consideration |

**Session Reset Triggers:**
- Browser tab closed
- User clicks "Clear Chat" button
- 50 message limit reached (oldest messages dropped)
- 30 minutes of inactivity (optional)

**UX:**
```
┌─────────────────────────────────────────────────────────────┐
│ 🤖 AI Assistant                              [Clear Chat 🗑️] │
├─────────────────────────────────────────────────────────────┤
│ Session: 12 messages                                        │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### Multi-User Concurrency

**Decision:** Single admin (Viktor) for v1, multi-user deferred

**v1 Assumptions:**
- Only Viktor uses AI features
- No concurrent AI sessions
- No shared state conflicts
- No locking needed

**Future Considerations (v2+):**
- Session isolation per user
- Optimistic locking for schedule approval
- "Schedule already modified" conflict resolution
- User-specific rate limits

**Note:** If multiple admins are added before v2, implement simple "last write wins" with warning: "This schedule was modified by another user. Refresh to see changes."

---

### Message Sent Log

**Decision:** Add visibility into sent communications

**New UI Component - Communications Queue Enhancement:**

```
┌─────────────────────────────────────────────────────────────┐
│ 📬 Communications Queue                          [View All] │
├─────────────────────────────────────────────────────────────┤
│ PENDING (12)                                                │
│   [Send All] [Review]                                       │
│                                                              │
│ SENT TODAY (8)                                    [View →]  │
│   • 10:15am - John Smith - Confirmation sent ✓              │
│   • 10:14am - Jane Doe - Confirmation sent ✓                │
│   • 9:30am - Bob Wilson - Reminder sent ✓                   │
│                                                              │
│ FAILED (1)                                        [Retry]   │
│   • 9:28am - Mike Johnson - Delivery failed ❌              │
└─────────────────────────────────────────────────────────────┘
```

**Sent Message Log Schema:**
```sql
CREATE TABLE sent_messages (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id),
    message_type VARCHAR(50),  -- 'confirmation', 'reminder', 'follow_up'
    message_content TEXT,
    sent_at TIMESTAMP,
    delivery_status VARCHAR(20),  -- 'sent', 'delivered', 'failed'
    twilio_sid VARCHAR(50),  -- For tracking
    created_by UUID  -- User who clicked send
);
```

**Benefits:**
- Audit trail for all communications
- Easy to see what was sent to whom
- Retry failed messages
- Prevent duplicate sends

---

### Mobile AI Features (Deferred)

**Decision:** Mobile AI features deferred to Phase 7

**Phase 6 Scope (Admin Only):**
- ✅ Schedule Generation
- ✅ Job Categorization
- ✅ Communication Drafts
- ✅ Business Queries
- ✅ Estimate Generation

**Phase 7 Scope (Mobile/Field Staff):**
- ❌ Quick "Send on-the-way" button
- ❌ Voice-to-text for job notes
- ❌ AI-suggested completion notes
- ❌ Simple field queries ("What's the gate code?")

**Rationale:** Focus Phase 6 on Viktor's admin workflow. Mobile features require additional UX design, offline considerations, and voice integration that would expand scope significantly.

---

### Weather Integration Details

**Decision:** OpenWeatherMap with specific implementation

**When to Fetch:**
- On schedule generation (fetch for all scheduled days)
- Daily cron job at 6am (update forecasts for next 5 days)
- Manual refresh button on schedule page

**API Call Pattern:**
```python
# Fetch 5-day forecast for Twin Cities area
GET https://api.openweathermap.org/data/2.5/forecast?lat=44.98&lon=-93.27&appid={API_KEY}

# Response includes 3-hour intervals for 5 days
# Check precipitation probability (pop) field
```

**Weather Warning Display:**
```
┌─────────────────────────────────────────────────────────────┐
│ TUESDAY - Eden Prairie (8 jobs)                             │
│ ⚠️ Weather Alert: 85% chance of rain after 2pm              │
│                                                              │
│ Affected jobs:                                               │
│   • 2:00pm - Johnson (startup) - Consider rescheduling      │
│   • 3:30pm - Smith (startup) - Consider rescheduling        │
│                                                              │
│ Morning jobs unaffected (0% precipitation before noon)      │
└─────────────────────────────────────────────────────────────┘
```

**Fallback if API Down:**
- Show "Weather data unavailable" 
- Allow scheduling without weather info
- Log API failure for monitoring

---

### Prompt Management Strategy

**Decision:** Version-controlled prompts with template system

**Prompt Organization:**
```
src/grins_platform/services/ai/prompts/
├── __init__.py
├── base.py              # System prompt, business rules
├── scheduling.py        # Schedule generation prompts
├── categorization.py    # Job categorization prompts
├── communication.py     # Message drafting prompts
├── queries.py           # Business query prompts
├── estimates.py         # Estimate generation prompts
└── templates/
    ├── confirmation.txt
    ├── reminder.txt
    └── follow_up.txt
```

**Prompt Versioning:**
```python
SYSTEM_PROMPT_V1 = """
You are an AI assistant for Grin's Irrigation...
Version: 1.0.0
Last Updated: 2025-01-26
"""

# Track which version generated each response in audit log
```

**Prompt Injection Prevention:**
- Sanitize all user input before including in prompts
- Use structured tool calls instead of free-form instructions
- Validate AI outputs against expected schemas
- Never execute code from AI responses

**Testing:**
- Golden dataset of 30 input/output pairs per capability
- Run regression tests on prompt changes
- A/B test major prompt revisions (future)

---

### API Response Schema Examples

**POST /api/v1/ai/schedule/generate**

Request:
```json
{
  "date_range": {
    "start": "2025-01-27",
    "end": "2025-01-31"
  },
  "include_jobs": ["ready_to_schedule"],
  "staff_ids": ["vas-uuid", "dad-uuid"]
}
```

Response:
```json
{
  "success": true,
  "schedule": {
    "days": [
      {
        "date": "2025-01-27",
        "weather": {"condition": "clear", "precipitation_chance": 10},
        "staff_assignments": [
          {
            "staff_id": "vas-uuid",
            "staff_name": "Vas",
            "jobs": [
              {
                "job_id": "job-uuid-1",
                "customer_name": "John Smith",
                "address": "123 Oak St, Eden Prairie",
                "job_type": "spring_startup",
                "time_window": {"start": "09:00", "end": "10:00"},
                "estimated_duration_minutes": 45,
                "price": 65.00
              }
            ],
            "total_jobs": 6,
            "total_hours": 4.5,
            "route_miles": 12
          }
        ]
      }
    ],
    "warnings": [
      {
        "type": "weather",
        "message": "Rain expected Tuesday afternoon",
        "affected_jobs": ["job-uuid-5", "job-uuid-6"]
      },
      {
        "type": "equipment",
        "message": "Compressor required for winterization",
        "affected_jobs": ["job-uuid-3"]
      }
    ],
    "summary": {
      "total_jobs": 47,
      "total_revenue": 2820.00,
      "jobs_needing_review": 3
    }
  },
  "ai_explanation": "I grouped jobs by city to minimize drive time. Eden Prairie jobs are scheduled Monday, Plymouth Tuesday..."
}
```

**POST /api/v1/ai/jobs/categorize**

Response:
```json
{
  "success": true,
  "categorizations": [
    {
      "job_id": "job-uuid-1",
      "suggested_category": "ready_to_schedule",
      "confidence": 0.92,
      "suggested_price": 65.00,
      "price_breakdown": {
        "base": 45.00,
        "per_zone": 5.00,
        "zones": 4
      },
      "ai_notes": "Existing customer, 4-zone system on file, standard startup pricing"
    },
    {
      "job_id": "job-uuid-2",
      "suggested_category": "needs_estimate",
      "confidence": 0.78,
      "suggested_price": null,
      "ai_notes": "New customer, 'large property' mentioned - recommend site visit"
    }
  ],
  "summary": {
    "ready_to_schedule": 18,
    "needs_estimate": 4,
    "needs_review": 1,
    "red_flag": 0
  }
}
```

---

## Next Steps

1. Review and approve this planning document
2. Create formal spec in `.kiro/specs/ai-agent-integration/`
3. Set up Pydantic AI development environment
4. Begin Phase 6.1 implementation


---

## Identified Gaps & Prerequisites

### Gap 1: SMS/Communication Infrastructure (CRITICAL)

The plan references sending texts but doesn't address the underlying infrastructure:

| Question | Options | Decision Needed |
|----------|---------|-----------------|
| SMS Provider | Twilio, SendGrid, AWS SNS, Vonage | Which provider? |
| Two-way SMS | How to receive customer replies ("YES" to confirm)? | Webhook setup required |
| Business Phone Number | Need dedicated number for SMS | Purchase/provision |
| SMS Opt-in Compliance | Required per `product.md` | Consent tracking in DB |
| Cost per Message | ~$0.0075/SMS (Twilio) | Factor into budget |

**Prerequisite:** SMS infrastructure must be built before communication features work.

### Gap 2: Invoice System (NOT YET BUILT)

AI references invoices heavily but the system may not exist:

- [ ] Invoice database model/table
- [ ] Invoice generation (PDF? Email? Text?)
- [ ] Payment tracking (mark as paid)
- [ ] Payment method integration (Venmo, Zelle mentioned in mockups)
- [ ] Invoice aging/overdue calculation

**Question:** Is invoice management in scope for Phase 6, or should it be a separate phase?

### Gap 3: Weather Integration ✅ RESOLVED

**Decision:** OpenWeatherMap free tier, 5-day forecast, >70% precipitation probability = bad weather

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Weather API | OpenWeatherMap (free tier) | 1,000 calls/day free, sufficient for scheduling |
| Forecast Range | 5 days ahead | Matches scheduling window |
| Bad Weather Definition | >70% precipitation probability | Rain certainty as discussed |
| Action on Bad Weather | Flag only | No auto-reschedule, human decides |

### Gap 4: Confidence Scoring Details ✅ RESOLVED

**Decision:** Simple binary routing with 85% threshold

```
Confidence Levels:
- HIGH (≥85%): Route to "Ready to Schedule" queue
- LOW (<85%): Route to "Needs Review" queue
```

**Rationale:** Keep it simple for v1. No medium tier - either AI is confident enough or it needs human review. Threshold can be tuned based on real-world accuracy.

### Gap 5: Caching Strategy ✅ RESOLVED

**Decision:** No caching for v1, add Redis later if needed

| What to Cache | v1 Decision | Future (if needed) |
|---------------|-------------|-------------------|
| Customer data for context | No caching | Redis, 5 min TTL |
| Service catalog | No caching | Redis, 1 hour TTL |
| Previous AI responses | Never cache | - |
| LLM embeddings (if RAG) | Not using RAG in v1 | PostgreSQL/pgvector |

**Rationale:** Start simple, monitor LLM costs. If costs become an issue, add caching layer. Premature optimization avoided.

### Gap 6: Error Handling UX ✅ RESOLVED

**Decision:** Graceful degradation with manual fallback

| Scenario | User Experience |
|----------|-----------------|
| LLM API down | Show "AI temporarily unavailable" banner + enable manual workflow buttons |
| LLM returns nonsense | Detect via validation, retry once, then show "AI couldn't process this" |
| Rate limits hit | Queue requests, show "Processing..." with spinner |
| Network timeout | Retry with exponential backoff (max 3), then error message |
| Streaming interrupted | Show partial response + "Response incomplete, try again" |

**Key Principle:** AI features are enhancements, not blockers. If AI fails, user can always do the task manually.

### Gap 7: Audit Trail / Logging ✅ RESOLVED

**Decision:** `ai_audit_log` table with action summaries (not full prompts)

| What to Log | Details |
|-------------|---------|
| AI categorization decisions | Job ID, suggested category, confidence score, timestamp |
| AI-generated estimates | Job ID, calculated price, breakdown summary, timestamp |
| Sent communications | Customer ID, message type, sent timestamp, delivery status |
| User approvals/rejections | Action ID, user decision, timestamp |

**Schema (simplified):**
```sql
CREATE TABLE ai_audit_log (
    id UUID PRIMARY KEY,
    action_type VARCHAR(50),  -- 'categorization', 'estimate', 'communication', etc.
    entity_type VARCHAR(50),  -- 'job', 'customer', 'schedule'
    entity_id UUID,
    ai_recommendation JSONB,  -- Summary, not full prompt
    user_decision VARCHAR(20), -- 'approved', 'rejected', 'modified'
    created_at TIMESTAMP
);
```

**NOT logged:** Full prompts (cost/storage), raw LLM responses (privacy), PII

### Gap 8: Testing Strategy ✅ RESOLVED

**Decision:** Mock-first approach with GPT-3.5-turbo for integration tests

| Test Type | Approach |
|-----------|----------|
| Unit tests | Mock LLM responses with fixtures (deterministic) |
| Integration tests | Use GPT-3.5-turbo (cheaper, faster) with test prompts |
| Prompt regression | Golden dataset of 20-30 expected input/output pairs |
| A/B testing | Not in v1 scope |
| Load testing | Mock LLM, test infrastructure only |

**Test Data:**
- Create fixtures for common scenarios (startup request, repair request, etc.)
- Use anonymized/fake customer data in tests
- Maintain golden dataset for prompt regression testing

### Gap 9: Data Privacy ✅ RESOLVED

**Decision:** No PII sent to LLM APIs (OpenAI, etc.)

| Data Type | Sent to LLM? | Alternative |
|-----------|--------------|-------------|
| Customer names | ❌ No | Use "Customer #1234" or placeholders |
| Phone numbers | ❌ No | Never sent |
| Email addresses | ❌ No | Never sent |
| Street addresses | ❌ No | Use city/area only ("Eden Prairie customer") |
| Job descriptions | ✅ Yes | Non-PII content is fine |
| Zone counts, job types | ✅ Yes | Business data, not PII |
| Aggregated stats | ✅ Yes | "12 customers in Plymouth" |

**Implementation:** AI generates responses with placeholders (e.g., "Hi {first_name}..."), system fills in actual PII locally before display/send.

### Gap 10: Conversation History

For the chat interface:

| Decision | Options |
|----------|---------|
| Persistence | Session-only vs. saved to DB |
| History length | Last 10 messages? Unlimited? |
| Cross-session | Can Viktor reference yesterday's queries? |
| Export | Can conversations be exported? |

---

## Questions Requiring Answers (All Resolved ✅)

### Infrastructure Questions

~~1. **SMS Provider:** Which provider? Twilio is most common but has costs.~~ → **Twilio**
~~2. **Invoice System:** Is this built? If not, should it be Phase 6.0 or separate?~~ → **Skip for Phase 6**
~~3. **Weather API:** Which service? Free tier sufficient?~~ → **OpenWeatherMap free tier**

### Business Questions

~~4. **Timeline Reality:** Is 8 weeks realistic, or is this a hackathon demo?~~ → **Hackathon demo scope**
~~5. **Budget Ceiling:** Monthly LLM API budget? ($50? $200? $500?)~~ → **Design cost-conscious, no hard ceiling**
~~6. **Autonomy Level:** What should auto-execute vs. require approval?~~ → **All requires approval**

### Technical Questions

~~7. **LLM Provider Decision:** OpenAI vs Anthropic? Or support both?~~ → **OpenAI GPT-4, design for swap**
~~8. **Streaming:** Required for chat, but adds complexity. Worth it for v1?~~ → **Yes, implement streaming**
~~9. **Offline Mode:** Should field staff AI work offline? (Significant complexity)~~ → **Not in scope**

### UX Questions

~~10. **Confidence Display:** Show confidence scores to Viktor, or just use internally?~~ → **Internal only**
~~11. **AI Branding:** "AI Assistant" vs. giving it a name/personality?~~ → **"AI Assistant" (no personality)**
~~12. **Undo Flow:** How does Viktor correct an AI mistake?~~ → **Prevention over correction (approval flow)**

---

## Recommended Pre-Phase 6 Work

Before starting Phase 6 implementation, consider completing:

1. **Phase 6.0: Communication Infrastructure** (REQUIRED)
   - Set up Twilio SMS provider
   - Implement two-way SMS handling (webhooks for replies)
   - Build message queue and delivery tracking
   - Add SMS opt-in tracking to customer model
   - Purchase/provision business phone number

2. ~~**Phase 6.0: Invoice Foundation**~~ → **DEFERRED** (Skip for Phase 6, can be Phase 7)

**Note:** SMS infrastructure is the only hard prerequisite. AI features can draft messages, but sending requires Twilio setup.

---

## Twilio SMS Implementation Details

### Environment Configuration

Add the following to your `.env` file:

```bash
# Twilio SMS Configuration
TWILIO_ACCOUNT_SID=AC746f6b24b3a0f5d6eba29bdbbe2a5a5b
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
```

### Sending SMS via cURL (Testing)

To test SMS sending directly via Twilio API:

```bash
curl 'https://api.twilio.com/2010-04-01/Accounts/AC746f6b24b3a0f5d6eba29bdbbe2a5a5b/Messages.json' \
  -X POST \
  --data-urlencode 'To=+18777804236' \
  --data-urlencode 'From=+1XXXXXXXXXX' \
  --data-urlencode 'Body=Your message here' \
  -u AC746f6b24b3a0f5d6eba29bdbbe2a5a5b:[AuthToken]
```

Replace `[AuthToken]` with your actual auth token from the `.env` file.

### Python Implementation

```python
from twilio.rest import Client
import os

def send_sms(to_number: str, message: str) -> str:
    """Send SMS via Twilio.
    
    Args:
        to_number: Recipient phone number (E.164 format, e.g., +16125551234)
        message: Message body text
        
    Returns:
        Twilio message SID for tracking
    """
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    
    message = client.messages.create(
        body=message,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        to=to_number
    )
    
    return message.sid
```

### Webhook for Incoming SMS (Two-Way)

To receive customer replies (e.g., "YES" to confirm), configure a webhook in Twilio console:

1. Go to Twilio Console → Phone Numbers → Your Number
2. Set "A MESSAGE COMES IN" webhook to: `https://your-domain.com/api/v1/sms/webhook`
3. Method: POST

```python
# API endpoint for incoming SMS
@router.post("/api/v1/sms/webhook")
async def handle_incoming_sms(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...)
):
    """Handle incoming SMS from customers."""
    # Parse customer response
    response_text = Body.strip().upper()
    
    if response_text == "YES":
        # Confirm appointment
        await confirm_appointment_by_phone(From)
    elif response_text in ["NO", "CANCEL", "RESCHEDULE"]:
        # Flag for manual review
        await flag_for_reschedule(From)
    
    return {"status": "received"}
```

### Cost Estimate

| Message Type | Cost (Twilio) |
|--------------|---------------|
| Outbound SMS | ~$0.0079/message |
| Inbound SMS | ~$0.0079/message |
| Phone Number | ~$1.15/month |

**Estimated monthly cost for 150 jobs/week:**
- Confirmations: 150 × 4 weeks × $0.0079 = ~$4.74
- Reminders: 150 × 4 weeks × $0.0079 = ~$4.74
- On-the-way: 150 × 4 weeks × $0.0079 = ~$4.74
- Customer replies: ~100 × 4 weeks × $0.0079 = ~$3.16
- **Total: ~$18-25/month**
