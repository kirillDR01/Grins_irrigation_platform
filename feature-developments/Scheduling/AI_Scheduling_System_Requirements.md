# AI-POWERED SCHEDULING

**System Requirements & AI Interaction Design**

30 Decision Criteria | User Admin & Resource Interactions
Chat, Alerts, Suggestions | Required Data & Component Map

February 2026 | DRAFT v1.0 | CONFIDENTIAL

---

# 1. UI Architecture & User Roles

The scheduling system is built around two key user roles and three primary UI surfaces. The AI operates across all surfaces, making autonomous decisions, generating alerts and suggestions, and responding to conversational commands.

## User Roles

| Role | Description | Primary UI Surfaces |
| --- | --- | --- |
| User Admin | Creates, manages, and approves schedules. Typically a dispatcher, office manager, or owner. | Schedule Overview, Alerts/Suggestions Panel, AI Chat |
| Resource | Follows the schedule. Typically a field technician, crew lead, or subcontractor. | Mobile Schedule View, Pre-Job Requirements, AI Chat (resource-facing) |

## UI Surfaces

| Surface | Description |
| --- | --- |
| Schedule Overview | A summarized view of the current schedule state. Shows all assigned jobs across technicians by day/week, capacity utilization, and status indicators (confirmed, in-progress, completed, flagged). Options to add or remove resources on the schedule. |
| Alerts / Suggestions | Panel below the Schedule Overview. Alerts are critical conflicts requiring immediate human attention (red). Suggestions are AI-recommended improvements that can be accepted or dismissed (green). Both are generated autonomously by the AI based on the decision criteria. |
| AI Chat | Conversational interface where User Admins give natural-language commands to build/modify schedules and Resources request changes or get pre-job guidance. The AI asks clarifying questions to build the most efficient schedule possible. |

## AI Samples:

Admin: See docs
Resource: See docs

## AI Function Summary

The AI operates in four distinct modes across the two user roles:

| User | AI Mode | What It Does |
| --- | --- | --- |
| User Admin | Autonomous Decision-Making | AI evaluates decision criteria/constraints to autonomously build schedules, generate alerts for conflicts, and surface suggestions for improvements. No human input required to trigger. |
| User Admin | Conversational Co-Pilot | Admin interacts with AI via chat to create, modify, or optimize schedules. AI asks clarifying questions to ensure the most efficient outcome. |
| Resource | Pre-Job Requirements Generator & Notification | AI generates job-specific requirements and checklists the resource must address before arriving at the job site, based on job type, customer profile, and equipment needs. Alerts resource on changes to schedule. |
| Resource | Change Request via Chat | Resource interacts with AI to request schedule changes (running late, needs help, customer not home). AI packages the request and presents it to the User Admin via their Alerts panel for approval. |
| Admin & Resource | Make Update to UI | Admin/resource can interact with AI in the chat function to request changes to UI that are specifically for them. For example Admin requests to add a report of total jobs complete within the schedule overview |

---

# 2. 30 Key Decision Criteria / Constraints

These are criteria the AI evaluates autonomously to build, validate, and optimize schedules. They span real-time operational data, historical patterns, external signals, and business rules. No competitor evaluates all 30 simultaneously — most only handle 5–8 basic constraints (availability, location, skills).

### Geographic & Logistics (1–5)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 1 | Resource-to-Job Proximity | Straight-line and drive-time distance between the resource's current/home location and the job site. Minimizes dead-head miles. |
| 2 | Intra-Route Drive Time | Total cumulative drive time across all jobs in a resource's daily route. AI sequences stops to minimize this total. |
| 3 | Service Zone Boundaries | Configurable geographic zones (North, South, East, West or custom polygons). AI keeps resources within their assigned zone unless cross-zone is more efficient. |
| 4 | Real-Time Traffic Conditions | Live traffic data overlaid on route calculations. AI adjusts ETAs and resequences when traffic spikes on a planned route segment. |
| 5 | Job Site Access Constraints | Gate codes, HOA entry requirements, construction site access windows, gated community hours. AI schedules around these hard windows. |

### Resource Capabilities (6–10)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 6 | Skill / Certification Match | Each job type requires specific skill tags (backflow certified, lake pump trained). AI only assigns resources who hold the required certifications. |
| 7 | Equipment on Truck | AI verifies the resource's truck carries the required equipment for the job type (pressure gauge, compressor, specific fittings). Prevents 'wrong truck' dispatches. |
| 8 | Resource Availability Windows | Shift start/end times, PTO, half-days, training blocks. AI respects hard availability and does not schedule outside approved hours. |
| 9 | Resource Workload Balance | Distributes jobs evenly across the team. Prevents one resource from being overloaded while another is underutilized on the same day. |
| 10 | Resource Performance History | Historical job completion speed, customer satisfaction scores, and callback rate per resource. AI matches high-complexity jobs to top performers. |

### Customer & Job Attributes (11–15)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 11 | Customer Time-Window Preference | Customer-requested AM/PM/specific-hour windows. Hard constraints that cannot be violated vs. soft preferences the AI tries to honor. |
| 12 | Job Type Duration Estimate | Default duration from the job type template, adjusted by AI based on historical actual durations for similar jobs (zone count, system age, resource speed). |
| 13 | Job Priority Level | Priority tiers (emergency, VIP, standard, flexible). AI schedules emergencies first, ensures VIPs get preferred windows, and fills remaining capacity with standard/flexible jobs. |
| 14 | Customer Lifetime Value | High-LTV customers get scheduling preference during high-demand periods. AI uses CLV data to break ties when two jobs compete for the same slot. |
| 15 | Customer-Resource Relationship History | If a customer previously rated a specific resource 5 stars or requested them by name, AI prefers that pairing. Builds loyalty and reduces friction. |

### Capacity & Demand (16–20)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 16 | Daily Capacity Utilization | Percentage of available resource-hours filled for each day. AI flags days over 90% (overbooking risk) and under 60% (underutilization opportunity). |
| 17 | Weekly Demand Forecast | AI's predicted job volume for the coming 2–8 weeks based on historical patterns, seasonal trends, weather, and customer base size. Used to pre-position capacity. |
| 18 | Seasonal Peak Windows | Known high-demand periods (Spring Opening season, pre-freeze Fall Closing rush). AI front-loads scheduling and recommends overtime or temp staffing. |
| 19 | Cancellation / No-Show Probability | ML model predicting which scheduled jobs are most likely to cancel or no-show, based on customer history, weather forecast, and day-of-week patterns. AI can over-schedule low-risk slots. |
| 20 | Pipeline / Backlog Pressure | Number of unscheduled jobs in the queue and their aging (days since requested). AI escalates aging jobs and increases scheduling density when backlog grows. |

### Business Rules & Compliance (21–25)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 21 | Compliance Deadlines | Hard deadlines like backflow test certification expiration, municipal inspection windows, or warranty service windows. AI schedules these before the deadline, not after. |
| 22 | Revenue Per Resource-Hour | AI calculates effective revenue/hour (including drive time) for different job type mixes and optimizes the schedule to maximize total daily revenue, not just job count. |
| 23 | Contract / SLA Commitments | Service-level agreements with commercial or HOA customers that mandate response times (e.g., 24-hour, same-week). AI treats SLA deadlines as hard constraints. |
| 24 | Overtime Cost Threshold | Business rule defining when overtime becomes uneconomical. AI avoids scheduling into overtime unless the job's revenue justifies the added labor cost. |
| 25 | Seasonal Pricing Signals | Dynamic pricing rules (premium for Saturday, discount for Wednesday PM). AI steers flexible jobs toward off-peak slots and reserves peak slots for full-price work. |

### External & Predictive Signals (26–30)

| # | Criterion | What the AI Evaluates |
| --- | --- | --- |
| 26 | Weather Forecast Impact | AI checks 7-day weather forecast. Outdoor jobs get rescheduled proactively before rain/freeze events. Indoor-safe jobs fill the gap. |
| 27 | Predicted Job Complexity | ML model estimating actual job difficulty based on customer system age, zone count, last service date, and historical repair frequency. Complex jobs get longer time slots. |
| 28 | Lead-to-Job Conversion Timing | Hot leads from the sales pipeline that are likely to convert this week. AI reserves tentative capacity so new jobs can be slotted quickly without disrupting existing schedules. |
| 29 | Resource Location at Shift Start | Whether the resource starts from home, the shop, or a job site. Varies by day and resource. AI uses the correct origin point for first-job routing. |
| 30 | Cross-Job Dependency Chains | Multi-phase projects where Job B cannot start until Job A is complete (e.g., rough-in before head installation). AI enforces phase sequencing and alerts if upstream delays threaten downstream jobs. |

> **COMPETITIVE DIFFERENTIATION** ServiceTitan, Jobber, and Housecall Pro evaluate 5–8 basic constraints (availability, location, skills). Our AI evaluates all 30 simultaneously, including predictive signals (weather, cancellation probability, job complexity, lead conversion timing) that no competitor considers. This is the core differentiator: the AI doesn't just check if a schedule is valid — it builds the most profitable, efficient, and resilient schedule possible.

---

# 3. User Admin – AI Chat Interactions (10)

These are example prompts the User Admin types into the AI Chat to create and modify schedules. For each, the AI asks clarifying questions before executing, ensuring the most efficient outcome. The AI uses the decision criteria behind the scenes.

| # | User Admin Prompt | AI Response & Criteria Used |
| --- | --- | --- |
| 1 | "Build next week's schedule for spring openings." | AI asks: How many resources are available? Any customer priority overrides? Should I optimize for fewest miles or fastest completion? Then auto-builds the full week using criteria 1–5 (geography), 6–8 (resource fit), 11–13 (customer windows/priority), 16–18 (capacity), and 26 (weather). |
| 2 | "Reshuffle Thursday — two resources called out sick." | AI asks: Which resources are out? Should I redistribute their jobs to remaining resources, push to Friday, or flag for customer reschedule? Then recalculates using criteria 8–9 (availability, workload balance), 1–2 (proximity, drive time), and 11 (customer windows). |
| 3 | "Add an emergency break-fix at 456 Oak Street, needs lake pump specialist." | AI asks: What's the estimated duration? Any customer time constraint? Then evaluates criteria 6 (lake pump skill), 7 (equipment), 1 (proximity), 13 (emergency priority) to find the best-fit resource and slot. |
| 4 | "What does next month's capacity look like for new build installs?" | AI asks: Are you looking at crew availability or total project slots? Any specific zones? Then pulls criteria 16–18 (capacity, demand, seasonal peaks) and 20 (backlog) to forecast. |
| 5 | "Move Mrs. Rodriguez to Tuesday morning and make sure she gets the same tech as last time." | AI confirms: Mrs. Rodriguez – Job #2041, currently scheduled Wednesday PM. Last tech was Mike D. (rated 5 stars). Checking Tuesday AM availability for Mike D. Uses criteria 15 (relationship history), 11 (time window), 1–2 (route impact). |
| 6 | "Show me which resources are underutilized this week and suggest how to fill their time." | AI evaluates criteria 9 (workload balance), 16 (utilization), 20 (backlog pressure), and 17 (demand forecast). Identifies resources below 70% utilization. |
| 7 | "Schedule all 350 fall closing customers across the next 5 weeks." | AI asks: Any zones to prioritize first (frost risk)? Customer preferences to honor? Overtime approved? Then batch-assigns using criteria 3 (zones), 11 (preferences), 18 (seasonal peak), 26 (weather/frost forecast), and 6–7 (skills/equipment). |
| 8 | "What's the most profitable way to fill Friday — we have 3 open slots." | AI evaluates criteria 22 (revenue per resource-hour), 13 (priority), 14 (customer LTV), 25 (pricing signals), and 20 (backlog aging). Ranks candidate jobs by profitability. |
| 9 | "Rain is forecast all day Wednesday. Reschedule outdoor jobs and backfill with indoor work." | AI applies criteria 26 (weather), identifies all outdoor-flagged jobs on Wednesday, and searches for indoor-eligible backlog (controller replacements, consultations). Uses criteria 1–2 (routing) to rebuild. |
| 10 | "Set up a recurring bi-weekly maintenance route for our top 20 commercial accounts." | AI asks: Which day(s) preferred? Same resource each visit? Any SLA requirements? Then uses criteria 23 (SLA), 14 (LTV), 15 (relationship), 3 (zones), 1–2 (routing) to build an efficient recurring template. |

### Outputs from AI Chat Interactions

| # | Prompt | Output to Schedule Overview |
| --- | --- | --- |
| 1 | "Build next week's schedule for spring openings."... | Auto-generated weekly schedule with jobs assigned by day, resource, and route sequence. Capacity heat map and flagged conflicts presented for review. |
| 2 | "Reshuffle Thursday — two resources called out sick."... | Revised Thursday schedule with reassigned jobs, updated ETAs, and a list of jobs that couldn't be absorbed (recommended for reschedule). |
| 3 | "Add an emergency break-fix at 456 Oak Street, needs lake pu..." | Emergency job inserted into the nearest qualified resource's route. Downstream ETAs recalculated. Affected customers notified of adjusted windows. |
| 4 | "What does next month's capacity look like for new build ins..." | Capacity forecast showing available multi-day project slots by week, crew availability, and recommended booking limits before over-commitment. |
| 5 | "Move Mrs. Rodriguez to Tuesday morning and make sure she ge..." | Job moved to Tuesday AM with Mike D. assigned. Route recalculated for both Tuesday and Wednesday. Customer confirmation notification drafted. |
| 6 | "Show me which resources are underutilized this week and sug..." | Utilization report per resource with specific suggestions: pull-forward jobs from next week, assign backlog items, or schedule proactive maintenance for service-agreement customers. |
| 7 | "Schedule all 350 fall closing customers across the next 5 w..." | Complete 5-week fall closing campaign with jobs assigned by week, zone, and resource. Capacity utilization by week shown. Customer appointment notifications ready for batch send. |
| 8 | "What's the most profitable way to fill Friday — we have 3 o..." | Ranked list of best-fit jobs for Friday's open slots with projected revenue impact. One-click to assign the AI's top recommendation. |
| 9 | "Rain is forecast all day Wednesday. Reschedule outdoor jobs..." | Revised Wednesday schedule: outdoor jobs pushed to next available clear day. Indoor backfill jobs assigned. Affected customers notified with new dates. |
| 10 | "Set up a recurring bi-weekly maintenance route for our top ..." | Recurring route template created: 20 accounts clustered into 2–3 geographic groups, assigned to designated resources, locked into bi-weekly cadence. Template auto-populates future schedules. |

---

# 4. User Admin – Alert / Suggestion Interactions (10)

These are generated autonomously by the AI and presented in the Alerts/Suggestions panel. The User Admin reviews and acts on them. Alerts (red) require immediate attention. Suggestions (green) are optional improvements.

| # | Type | Alert / Suggestion |
| --- | --- | --- |
| 1 | ALERT | Double-Booking Conflict — AI detects two jobs assigned to the same resource at overlapping times on Tuesday. Criteria 8 (availability) and 12 (duration estimates) triggered the conflict. |
| 2 | ALERT | Skill Mismatch Detected — AI finds a backflow test job assigned to a resource who lacks backflow certification. Criteria 6 (skill match) flagged the violation. |
| 3 | ALERT | SLA Deadline at Risk — A commercial customer's 48-hour SLA commitment expires tomorrow but the job is scheduled for next week. Criteria 23 (SLA) and 20 (backlog aging) triggered. |
| 4 | ALERT | Resource Running 40+ Min Behind — Live tracking shows a resource's current job is significantly over estimate. Criteria 12 (duration), 27 (predicted complexity), and 4 (traffic) analyzed. Downstream jobs at risk. |
| 5 | ALERT | Severe Weather Incoming — AI detects a freeze warning for Thursday. 12 outdoor jobs scheduled. Criteria 26 (weather) triggered. |
| 6 | SUGGESTION | Route Swap Saves 45 Minutes — AI identified that swapping two jobs between Resource A and Resource B would reduce combined drive time by 45 minutes. Criteria 1–2 (proximity, drive time) and 9 (workload balance) analyzed. |
| 7 | SUGGESTION | Underutilized Resource – Fill Gap — Resource C has 2.5 hours unused on Wednesday afternoon. 3 backlog jobs match their skills and are within their zone. Criteria 9 (balance), 16 (utilization), 20 (backlog). |
| 8 | SUGGESTION | Customer Prefers Different Resource — Customer feedback from the last visit indicates dissatisfaction with the assigned resource. Criteria 15 (relationship history) and 10 (performance) suggest reassignment. |
| 9 | SUGGESTION | Overtime Avoidable by Shifting 1 Job — Friday's schedule puts Resource D into 1.5 hours of overtime. Moving one low-priority job to Monday eliminates the overtime. Criteria 24 (overtime cost) and 13 (priority) analyzed. |
| 10 | SUGGESTION | High-Revenue Job Available for Open Slot — A new maintenance request just entered the queue. It matches an open slot on Thursday with a nearby resource. Revenue per hour is 2x the average. Criteria 22 (revenue/hour) and 14 (CLV) flagged it. |

### Admin Actions on Alerts / Suggestions

| # | Type + Name | Admin Interaction |
| --- | --- | --- |
| 1 | ALERT: Double-Booking Conflict | Admin clicks to see both jobs. Options: reassign one to another resource, shift one by 30 min, or extend the time gap. One-click resolution. |
| 2 | ALERT: Skill Mismatch Detected | Admin sees the flagged job and a list of certified alternatives. Swap resource with one click. AI recalculates both routes. |
| 3 | ALERT: SLA Deadline at Risk | Admin sees the SLA countdown and a recommended slot today or tomorrow. Approve to force-schedule or override to accept the SLA miss. |
| 4 | ALERT: Resource Running 40+ Min Behind | Admin sees impacted jobs with new ETAs. Options: absorb delay, move last job to another resource, or reschedule last job to tomorrow. Customer notifications auto-drafted. |
| 5 | ALERT: Severe Weather Incoming | Admin sees all affected jobs highlighted. One-click to batch-reschedule outdoor jobs to next available day and backfill with indoor-eligible work. |
| 6 | SUGGESTION: Route Swap Saves 45 Minutes | Admin sees the proposed swap visualized on a map with before/after drive times. Accept to execute swap and update both routes. Dismiss to keep current. |
| 7 | SUGGESTION: Underutilized Resource – Fill Gap | Admin sees the gap and three candidate jobs ranked by revenue and proximity. Accept one or all. AI re-routes automatically. |
| 8 | SUGGESTION: Customer Prefers Different Resource | Admin sees the customer's feedback and the AI's recommended alternative resource (higher satisfaction scores). Accept to reassign for all future jobs. |
| 9 | SUGGESTION: Overtime Avoidable by Shifting 1 Job | Admin sees the job recommended for shift, the overtime cost saved ($67), and the Monday slot. Accept to move or dismiss to keep overtime. |
| 10 | SUGGESTION: High-Revenue Job Available for Open Slot | Admin sees the job details, the proposed slot, and the projected revenue impact. Accept to auto-schedule. AI handles routing and customer confirmation. |

---

# 5. Resource – AI Chat Interactions (10)

These are prompts the Resource (field technician) sends via the mobile AI Chat. The AI either handles the request autonomously or packages it as a change request for the User Admin's approval.

| # | Resource Chat Prompt | AI Response |
| --- | --- | --- |
| 1 | "I'm running about 30 minutes behind on this job." | AI auto-recalculates remaining ETAs on the resource's route. If no customer windows are violated, it adjusts silently. If a window is at risk, it drafts a delay notification and alerts the User Admin with resolution options. |
| 2 | "What do I need for my next job?" | AI pulls the next job's type template, customer system profile, and equipment checklist. Generates a pre-arrival requirements list specific to that job. |
| 3 | "This customer needs additional work — 3 broken heads and a leaking valve. Can you add a follow-up?" | AI creates a follow-up job request with the resource's field notes (3 broken heads, leaking valve). Estimates parts needed. Packages as a scheduling request for the Admin. |
| 4 | "Customer isn't home and the gate is locked. What should I do?" | AI checks customer profile for alternative access instructions or secondary contact. If none found, generates a change request to Admin: reschedule or attempt customer contact. |
| 5 | "I finished early. Do I have anything nearby I can pick up?" | AI evaluates unassigned jobs and backlog within a 15-min radius that match the resource's skills and truck equipment. Ranks by priority and revenue. |
| 6 | "I don't have the right nozzle kit for this job. Can it be swapped with my afternoon job while I stop at the shop?" | AI checks if resequencing the route to shop stop + afternoon job first is feasible without violating time windows. Packages the route change for Admin approval. |
| 7 | "This system is way more complex than expected — it's a 16-zone with a lake pump. I need help." | AI identifies available resources nearby with the required skill (lake pump) who have capacity. Creates a crew assistance request for Admin. |
| 8 | "Log that I replaced 4 spray heads and 2 rotors on this job." | AI captures the parts used, updates the job completion record, and adjusts truck inventory. If stock is below reorder threshold, it flags for restocking. |
| 9 | "What's my schedule look like tomorrow?" | AI pulls tomorrow's assigned schedule with job details, route sequence, ETAs, and pre-job requirements for each stop. |
| 10 | "This customer wants to upgrade to a smart controller. Can you quote it and schedule the install?" | AI pulls the upgrade pricing from the catalog, creates a quote draft, and identifies available install slots. Packages both the quote and scheduling request for Admin. |

### Outputs from Resource Chat

| # | Prompt (short) | Output / Escalation |
| --- | --- | --- |
| 1 | "I'm running about 30 minutes behind on this job."... | Updated ETAs on resource's mobile view. If escalated: alert sent to Admin with options (absorb, reassign last job, notify customer). |
| 2 | "What do I need for my next job?"... | Pre-job checklist: Job type, customer name/address, required equipment, known system issues, gate code, special instructions, estimated duration. |
| 3 | "This customer needs additional work — 3 broken heads a..." | Change request sent to Admin's Alerts panel: 'Resource requests follow-up at 123 Oak St — 3 heads + valve repair, est. 90 min. Recommended slot: Thursday PM.' |
| 4 | "Customer isn't home and the gate is locked. What shoul..." | Immediate response with any alternate access info. If no resolution: alert to Admin — 'Resource on-site, customer unavailable. Recommend: call customer, reschedule, or proceed to next job and return later.' |
| 5 | "I finished early. Do I have anything nearby I can pick..." | List of 2–3 nearby available jobs with details. Resource selects one; AI requests Admin approval. Once approved, job is added to route with navigation. |
| 6 | "I don't have the right nozzle kit for this job. Can it..." | Proposed resequenced route shown to resource. Change request sent to Admin: 'Resource requests resequence for shop stop. New route saves 12 min overall. Approve?' |
| 7 | "This system is way more complex than expected — it's a..." | Alert to Admin: 'Resource requests backup at 789 Elm St — 16-zone lake pump system. Nearest qualified resource: Mike D., 8 min away, current job wrapping in 20 min. Approve crew assist?' |
| 8 | "Log that I replaced 4 spray heads and 2 rotors on this..." | Job record updated. Truck inventory decremented. If threshold breached: suggestion to Admin — 'Resource's truck stock below minimum for spray heads. Recommend resupply before tomorrow.' |
| 9 | "What's my schedule look like tomorrow?"... | Tomorrow's schedule card: 6 jobs listed in route order with addresses, job types, estimated durations, customer notes, and total estimated drive time. Pre-job requirements flagged for any job needing special prep. |
| 10 | "This customer wants to upgrade to a smart controller. ..." | Quote draft sent to Admin for approval. Scheduling request: 'Upgrade install at 456 Pine St — est. 2 hours. Recommended slot: next Tuesday AM. Quote: $385. Approve quote + schedule?' |

---

# 6. Resource – Alerts / Suggestions (10)

These are AI-generated alerts and suggestions that appear on the Resource's mobile view. They provide proactive guidance, pre-job preparation requirements, and real-time schedule updates pushed from the Admin or AI.

| # | Type | Alert / Suggestion |
| --- | --- | --- |
| 1 | ALERT | Schedule Change – Job Added — Admin approved a new job inserted into the resource's route. AI recalculated the sequence. |
| 2 | ALERT | Schedule Change – Job Removed — A cancellation removed a job from the resource's route. AI adjusted remaining ETAs. |
| 3 | ALERT | Route Resequenced — Admin or AI resequenced the resource's remaining jobs (traffic, swap, weather). New route order pushed. |
| 4 | ALERT | Pre-Job Requirement – Special Equipment — Next job requires equipment not typically on the truck (e.g., compressor for fall closing). AI flagged before the resource leaves for the job. |
| 5 | ALERT | Pre-Job Requirement – Customer Access — Next job has specific access instructions (gate code, meet at back door, dog in yard). AI surfaces before arrival. |
| 6 | SUGGESTION | Pre-Job Prep – Review Customer History — AI identifies that the next customer had a recurring valve issue on Zone 3 in the last two visits. Suggests carrying extra valve parts. |
| 7 | SUGGESTION | Upsell Opportunity — AI detects the next customer's controller is 12+ years old and has had 3 service calls in 2 years. Suggests mentioning a smart controller upgrade. |
| 8 | SUGGESTION | Optimized Departure Time — AI calculates that leaving 10 minutes later for the next job will avoid a traffic spike and arrive at the same time. |
| 9 | SUGGESTION | Parts Running Low — Based on today's remaining jobs, AI predicts the resource will run out of a commonly needed part (spray heads) before the last job. |
| 10 | ALERT | Admin Decision Required – Pending Approval — Resource previously requested a schedule change via chat. Admin hasn't responded yet. AI nudges. |

### Resource Actions on Alerts / Suggestions

| # | Type + Name | Resource Interaction |
| --- | --- | --- |
| 1 | ALERT: Schedule Change – Job Added | Resource sees the new job in their route with updated sequence and ETA. Tap to view job details and pre-job requirements. |
| 2 | ALERT: Schedule Change – Job Removed | Resource sees the updated route (one fewer stop). Gap time shown — AI suggests: 'You have a 45-min gap. Nearby backlog job available — tap to request.' |
| 3 | ALERT: Route Resequenced | Resource sees the reordered job list with a brief reason ('Traffic on I-35, new route avoids 20-min delay'). Updated navigation ready. |
| 4 | ALERT: Pre-Job Requirement – Special Equipment | Alert 30 min before job: 'Next job requires 185 CFM compressor. Confirm you have it or reroute to shop first.' Resource taps 'Confirmed' or 'Need Shop Stop.' |
| 5 | ALERT: Pre-Job Requirement – Customer Access | Alert 15 min before arrival: 'Gate code: 4521. Enter through side gate. Dog is friendly but loose in backyard. Customer requests text before arrival.' |
| 6 | SUGGESTION: Pre-Job Prep – Review Customer History | Suggestion card: 'Customer history: Zone 3 valve replaced twice in 18 months. Recommend carrying spare 1" globe valve and diaphragm kit.' |
| 7 | SUGGESTION: Upsell Opportunity | Suggestion card: 'Customer's Hunter Pro-C is 14 years old (3 repairs in 2 yrs). Consider suggesting Hydrawise upgrade — saves customer on water bills and reduces callbacks.' |
| 8 | SUGGESTION: Optimized Departure Time | Suggestion: 'Traffic on Hwy 71 peaks in 8 min. If you depart at 1:25 instead of 1:15, ETA is the same (1:52) with less drive stress.' |
| 9 | SUGGESTION: Parts Running Low | Suggestion: 'Based on today's remaining 3 jobs, you may need 6+ spray heads. Current truck stock: 4. Consider picking up 6 more at supply house (2 min from Job #4).' |
| 10 | ALERT: Admin Decision Required – Pending Approval | Alert: 'Your schedule change request (follow-up at 123 Oak St) is pending Admin approval. Submitted 25 min ago. Proceeding to next job per current route.' |

---

# 7. Required Data

This is the complete data inventory required to power the 30 decision criteria, all chat interactions, and all alert/suggestion functions described above. Data is grouped by domain.

### Customer Data

- Customer ID, name, billing/service addresses (geocoded lat/long)
- Phone, email, preferred contact method
- Property type (residential, commercial, HOA, municipal)
- Customer time-window preferences (hard AM/PM, soft preferred times)
- Customer lifetime value (CLV) score
- Customer satisfaction scores (per-visit and aggregate NPS)
- Customer-resource relationship history (who served them, ratings)
- Service agreement details (level, SLA terms, pricing tier)
- Gate codes, access instructions, pet warnings, special notes
- Communication preference (SMS, email, phone, app notification)

### Customer System / Asset Profile

- System age and install date
- Zone count, zone types (rotor, spray, drip), head counts per zone
- Water source type (city, well, lake, reclaimed)
- Controller make/model, station count, Wi-Fi capability
- Backflow preventer type, serial number, last test date, certification expiry
- Pump details (make, model, HP) if applicable
- Known recurring issues (from service history)
- Equipment installed (head models, pipe types, valve types)
- Last service date and type per asset

### Job Data

- Job ID, job type (from configurable template), status (unscheduled, scheduled, in-progress, complete)
- Job address (geocoded), service zone assignment
- Estimated duration (template default + AI-adjusted prediction)
- Required skills and certifications
- Required equipment checklist
- Priority level (emergency, VIP, standard, flexible)
- Customer-requested time window (hard/soft)
- Revenue / price for the job
- Job phase (for multi-day projects: phase sequence, dependencies)
- Job notes, field observations, parts used, completion photos
- SLA deadline (if commercial/contract)
- Source (customer-requested, proactive AI-generated, follow-up from field)

### Resource (Technician) Data

- Resource ID, name, contact info
- Skill tags and certifications (with expiration dates)
- Home base address (geocoded)
- Shift schedule (start/end times, days of week)
- PTO, sick days, training blocks, unavailability windows
- Current GPS location (live, from mobile app)
- Truck/vehicle assignment and current equipment inventory
- Performance metrics: average job duration by type, customer satisfaction, callback rate
- Preferred zones / geographic assignments
- Current job status (idle, en route, on-site, complete)

### Schedule Data

- Daily/weekly schedule: job-to-resource assignments with sequence order
- Route sequence per resource (ordered stops with ETAs)
- Job status transitions with timestamps (assigned, departed, arrived, started, completed)
- Actual vs. estimated duration per job
- Cancellations, no-shows, reschedules with reasons
- Capacity utilization by day/zone/resource
- Historical schedule data (multi-year for ML training)

### Geographic & Logistics Data

- Drive-time matrix between all job-pair addresses (from mapping API)
- Real-time traffic conditions (from mapping API)
- Service zone boundary definitions (polygon coordinates or ZIP groupings)
- Supply house / shop locations (for restocking stops)

### External & Predictive Data

- 7-day weather forecast (temperature, precipitation, freeze warnings)
- Municipal compliance calendars (backflow test deadlines, watering restrictions)
- Seasonal demand patterns (historical job volume by week/type/zone, multi-year)
- Cancellation/no-show probability model outputs (per scheduled job)
- Job complexity prediction model outputs (predicted actual duration)
- Lead conversion probability scores (from sales pipeline)

### Financial Data

- Revenue per job (actual, by type)
- Cost per resource-hour (fully loaded: wages, benefits, truck, fuel)
- Overtime rate and threshold rules
- Dynamic pricing rules (peak/off-peak multipliers, discount triggers)
- Parts/material costs per job
- Customer payment history and billing preferences

---

# 8. Interacting Business Components

The Scheduling module does not operate in isolation. Below are the other business process components it will interact with to source data and trigger actions. This section identifies what the scheduling AI needs from each component — not how those components should be improved.

## Component Interaction Map

The scheduling module sits at the center, pulling data from surrounding components and pushing schedule events back to them:

| Component | What Scheduling Needs From It |
| --- | --- |
| Customer Intake | Provides the job creation pipeline. When a new customer or service request is taken in, it flows into the scheduling queue. Scheduling reads: new job requests, job type classification, customer details, urgency level, requested time windows. |
| Sales / Quoting | Provides quoted jobs awaiting scheduling (new builds, upgrades). Scheduling reads: approved quotes with scope/duration, customer contact info, preferred start dates, project phases for multi-day installs. |
| Marketing & Lead Management | Provides demand signals. Scheduling reads: active campaign calendars (which may drive inbound volume spikes), lead conversion probabilities (to reserve tentative capacity), seasonal outreach schedules (spring opening reminders that generate scheduling demand). |
| Customer Communication | The outbound channel for schedule notifications. Scheduling triggers: appointment confirmations, ETA updates, delay notifications, reschedule requests, pre-job reminders. Communication component handles delivery via SMS, email, or app push. |
| Workforce / HR Management | Provides the resource pool. Scheduling reads: employee roster with roles, certifications, and skill tags; shift schedules and PTO calendars; onboarding status of new hires; certification expiration dates for compliance scheduling. |
| Inventory / Equipment Management | Provides equipment availability. Scheduling reads: what equipment is on each truck, stock levels of common parts, reorder thresholds. Scheduling triggers: low-stock alerts when field consumption depletes a resource's truck inventory. |
| Financial / Billing / Invoicing | Provides revenue and cost data. Scheduling reads: job pricing, resource cost rates (for revenue-per-hour optimization), overtime thresholds, customer payment status (to deprioritize delinquent accounts). Scheduling triggers: job completion events that initiate invoicing. |
| Reporting & Analytics | Provides historical performance data for ML model training. Scheduling reads: historical job durations, customer satisfaction trends, seasonal volume patterns, resource efficiency metrics. Scheduling writes: schedule adherence data, capacity utilization, delay frequency. |
| Compliance / Regulatory | Provides deadline-driven scheduling triggers. Scheduling reads: backflow test certification expiry dates, municipal inspection requirements, watering restriction schedules, permit deadlines. Scheduling generates proactive jobs when compliance deadlines approach. |
| Customer Relationship Management (CRM) | The master customer record. Scheduling reads: customer profiles, lifetime value scores, satisfaction history, communication preferences, resource-customer relationship ratings. CRM is the single source of truth for all customer-facing data. |

```
SCHEDULING MODULE (AI ENGINE)
        |            |            |
        v            v            v
CRM (Customer Data Pool)  +  Compliance / Regulatory
```

---

# 9. Competitive Differentiation Summary

This section summarizes why this system is fundamentally different from ServiceTitan, Jobber, Housecall Pro, FieldEdge, and every other FSM scheduling tool on the market.

| Differentiator | Why It Matters | Competitors vs. Us |
| --- | --- | --- |
| Constraint Depth | Competitors evaluate 5–8 basic scheduling constraints (availability, location, skills). Our AI evaluates 30 constraints simultaneously, including predictive signals no competitor considers. | Them: 5–8 constraints Us: 30 constraints with ML-driven predictions |
| Autonomous Decision-Making | Competitors require humans to build every schedule manually. Our AI builds complete schedules autonomously and presents them for review — the admin approves, not creates. | Them: Manual schedule building Us: AI-generated schedules with human approval |
| Predictive Intelligence | Competitors are purely reactive (things happen, humans respond). Our AI predicts delays, cancellations, demand spikes, and job complexity before they occur. | Them: Reactive only Us: Predictive + reactive |
| Resource Chat + Escalation | Competitors have no field-to-office AI layer. Our resource chat handles field requests, generates pre-job checklists, and routes change requests through an approval workflow. | Them: Phone calls to office Us: AI-mediated field requests with structured escalation |
| Alert / Suggestion Engine | Competitors show a calendar. Our system proactively surfaces conflicts, optimization opportunities, and revenue-maximizing moves that humans would miss. | Them: Static calendar view Us: Proactive alert + suggestion feed |
| Revenue Optimization | Competitors optimize for job count. Our AI optimizes for revenue per resource-hour, factoring in CLV, dynamic pricing, and cost-to-serve. | Them: Maximize jobs scheduled Us: Maximize revenue per resource-hour |
| Vertical Configurability | Competitors hard-code for one vertical. Our engine is generic with vertical playbooks — irrigation is a configuration pack, not custom code. | Them: Hard-coded vertical Us: Configurable engine + vertical playbooks |
| Weather-Aware Scheduling | Competitors ignore weather. Our AI monitors forecasts and proactively reschedules outdoor jobs before weather hits, backfilling with indoor-eligible work. | Them: No weather integration Us: Proactive weather-driven rescheduling |

---

# Key Questions/Considerations:

- What are the security/compliance items that we need to follow to ensure data is protected and can be used?
- What will be the costs for using this service and how will we set up pricing?
- How will our code be differentiated from others currently and in the future to protect from people copying easily?
- What will be the minimum data needed?
- What data do we need now and have to start? (Set up oriented)
- What data do we need now but we don't have and how will we attain it? (Set up oriented)
- What data will we need in the future and how will we attain it? (Trends learning)
- Difficulty for someone to start using from the start (How easy is it for them to start using it? How difficult would it be for them to get their unclean data over to the system, will we have a function to clean data up and implement it into the system?)
- People will ask questions that are not relative to the situation, can we set guard rails around that?
- How will we test functionality prior to sending it to market?
- How will we make sure we don't overbuild this and get into technical debt before testing it within the market?
- What is the next component that you will need or may we need to build asap in order for key functions to work within the scheduling component?
- Storage per user
- What large language model do we want to use?
