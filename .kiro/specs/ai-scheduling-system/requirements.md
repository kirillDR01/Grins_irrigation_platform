# Requirements Document

## Introduction

This document defines the requirements for the AI-Powered Scheduling System for the Grin's Irrigation Platform. This is the full-vision AI scheduling engine that evaluates 30 decision criteria simultaneously to autonomously build, validate, and optimize field service schedules. The system serves two user roles (User Admin and Resource/Technician) across three UI surfaces (Schedule Overview, Alerts/Suggestions Panel, AI Chat) and integrates predictive intelligence, conversational co-piloting, resource-facing chat, and a proactive alert/suggestion engine.

This spec builds upon three existing scheduling capabilities:
- **tier-priority-scheduling**: Wires tier-to-priority mapping (Essential→0, Professional→1, Premium→2) into job generation, which feeds into criterion #13 (Job Priority Level).
- **route-optimization**: OR-Tools based schedule generation with staff availability, equipment matching, travel time, hard/soft constraints, emergency insertion, conflict resolution, and staff reassignment. This provides the constraint solver foundation for criteria #1–9 and the schedule generation engine.
- **schedule-ai-updates**: Removes broken AI tab, adds schedule explanations, unassigned job explanations, natural language constraints, and AI help assistant. This provides the initial AI explanation layer and natural language parsing that this spec extends into full conversational co-piloting.

The AI scheduling system extends these foundations with 30-constraint simultaneous evaluation (vs. competitors' 5–8), autonomous schedule building, predictive intelligence (weather, cancellation probability, job complexity, lead conversion timing), resource-facing chat with escalation workflows, a proactive alert/suggestion engine, and revenue-per-resource-hour optimization.

## Glossary

- **AI_Scheduling_Engine**: The core AI service that evaluates all 30 decision criteria simultaneously to build, validate, and optimize schedules autonomously.
- **User_Admin**: A dispatcher, office manager, or owner who creates, manages, and approves schedules via the Schedule Overview, Alerts/Suggestions Panel, and AI Chat.
- **Resource**: A field technician, crew lead, or subcontractor who follows the schedule via Mobile Schedule View, Pre-Job Requirements, and AI Chat (resource-facing).
- **Schedule_Overview**: The primary UI surface showing all assigned jobs across technicians by day/week, capacity utilization, and status indicators (confirmed, in-progress, completed, flagged).
- **Alerts_Panel**: The panel below the Schedule Overview displaying critical conflicts (red alerts) requiring immediate human attention and AI-recommended improvements (green suggestions) that can be accepted or dismissed.
- **AI_Chat**: The conversational interface where User Admins give natural-language commands to build/modify schedules and Resources request changes or get pre-job guidance.
- **Decision_Criteria**: The 30 constraints the AI evaluates simultaneously spanning geographic/logistics, resource capabilities, customer/job attributes, capacity/demand, business rules/compliance, and external/predictive signals.
- **Hard_Constraint**: A constraint that must never be violated (e.g., skill certification match, availability windows, SLA deadlines).
- **Soft_Constraint**: A constraint that should be optimized but can be relaxed (e.g., minimize drive time, honor customer preferences, balance workload).
- **Pre_Job_Requirements**: AI-generated job-specific requirements and checklists the Resource must address before arriving at the job site.
- **Change_Request**: A structured request from a Resource to the User Admin (via AI Chat) for schedule modifications, routed through the Alerts Panel for approval.
- **CLV**: Customer Lifetime Value score used to break scheduling ties during high-demand periods.
- **SLA**: Service Level Agreement with commercial or HOA customers mandating response times.
- **ML_Model**: Machine learning model used for predictive signals including cancellation probability, job complexity prediction, and lead conversion timing.
- **Capacity_Utilization**: Percentage of available resource-hours filled for a given day, flagged at over 90% (overbooking risk) and under 60% (underutilization opportunity).
- **Revenue_Per_Resource_Hour**: Effective revenue per hour including drive time, used to optimize schedule profitability rather than just job count.
- **OR_Tools_Solver**: The existing Google OR-Tools constraint programming solver from the route-optimization spec, which this system extends with additional criteria.
- **Vertical_Playbook**: A configuration pack that adapts the generic scheduling engine to a specific industry vertical (irrigation is the first playbook).
- **PBT**: Property-Based Testing using the Hypothesis library to generate random inputs and validate correctness properties hold for all generated cases.
- **agent_browser**: The Vercel Agent Browser CLI tool used for end-to-end browser testing, providing snapshot-based element refs for reliable UI automation.
- **LoggerMixin**: The project's structured logging mixin class that provides domain-scoped logging methods (log_started, log_completed, log_failed, log_rejected).

## Requirements

### Requirement 1: UI Architecture and User Roles

**User Story:** As a platform operator, I want two distinct user roles (User Admin and Resource) served across three UI surfaces, so that each role has the appropriate tools and information for their scheduling responsibilities.

#### Acceptance Criteria

1. THE System SHALL support two user roles: User_Admin (dispatcher, office manager, or owner) and Resource (field technician, crew lead, or subcontractor).
2. THE System SHALL provide three primary UI surfaces: Schedule_Overview, Alerts_Panel, and AI_Chat.
3. WHEN a User_Admin accesses the scheduling system, THE System SHALL display the Schedule_Overview showing all assigned jobs across technicians by day and week, capacity utilization percentages, and status indicators (confirmed, in-progress, completed, flagged).
4. THE Schedule_Overview SHALL provide options to add or remove resources on the schedule.
5. WHEN a User_Admin views the Alerts_Panel, THE System SHALL display the panel below the Schedule_Overview with alerts (red, critical conflicts requiring immediate attention) and suggestions (green, AI-recommended improvements that can be accepted or dismissed).
6. THE AI_Chat SHALL provide a conversational interface where User_Admins give natural-language commands to build and modify schedules.
7. THE AI_Chat SHALL provide a resource-facing interface where Resources request changes or get pre-job guidance.
8. WHEN the AI_Chat receives a command from a User_Admin, THE AI_Scheduling_Engine SHALL ask clarifying questions before executing to ensure the most efficient outcome.
9. WHEN the AI_Chat receives a request from a Resource, THE AI_Scheduling_Engine SHALL either handle the request autonomously or package it as a Change_Request for User_Admin approval.

### Requirement 2: AI Function Modes

**User Story:** As a platform operator, I want the AI to operate in distinct modes for each user role, so that the system provides appropriate autonomous actions, conversational assistance, and escalation workflows.

#### Acceptance Criteria

1. WHEN operating for a User_Admin, THE AI_Scheduling_Engine SHALL support Autonomous Decision-Making mode that evaluates Decision_Criteria to autonomously build schedules, generate alerts for conflicts, and surface suggestions for improvements without requiring human input to trigger.
2. WHEN operating for a User_Admin, THE AI_Scheduling_Engine SHALL support Conversational Co-Pilot mode where the admin interacts via AI_Chat to create, modify, or optimize schedules with the AI asking clarifying questions.
3. WHEN operating for a Resource, THE AI_Scheduling_Engine SHALL support Pre-Job Requirements Generator mode that generates job-specific requirements and checklists based on job type, customer profile, and equipment needs, and alerts the Resource on schedule changes.
4. WHEN operating for a Resource, THE AI_Scheduling_Engine SHALL support Change Request via Chat mode where the Resource requests schedule changes and the AI packages the request for User_Admin approval via the Alerts_Panel.
5. WHEN operating for either User_Admin or Resource, THE AI_Scheduling_Engine SHALL support Make Update to UI mode where the user requests personalized UI changes via AI_Chat (e.g., adding a report of total jobs complete within the Schedule_Overview).

### Requirement 3: Geographic and Logistics Criteria (Criteria 1–5)

**User Story:** As a User Admin, I want the AI to evaluate geographic and logistics constraints when building schedules, so that routes are efficient and site access requirements are respected.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate resource-to-job proximity using both straight-line and drive-time distance between the resource's current or home location and the job site to minimize dead-head miles (Criterion 1).
2. THE AI_Scheduling_Engine SHALL evaluate intra-route drive time as the total cumulative drive time across all jobs in a resource's daily route and sequence stops to minimize this total (Criterion 2).
3. THE AI_Scheduling_Engine SHALL evaluate configurable service zone boundaries (North, South, East, West, or custom polygons) and keep resources within their assigned zone unless cross-zone assignment is more efficient (Criterion 3).
4. THE AI_Scheduling_Engine SHALL evaluate real-time traffic conditions by overlaying live traffic data on route calculations, adjusting ETAs and resequencing when traffic spikes on a planned route segment (Criterion 4).
5. THE AI_Scheduling_Engine SHALL evaluate job site access constraints including gate codes, HOA entry requirements, construction site access windows, and gated community hours, scheduling around these hard windows (Criterion 5).

### Requirement 4: Resource Capabilities Criteria (Criteria 6–10)

**User Story:** As a User Admin, I want the AI to evaluate resource capabilities when assigning jobs, so that only qualified and properly equipped resources are dispatched.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate skill and certification match by verifying each job type's required skill tags (e.g., backflow certified, lake pump trained) and only assigning resources who hold the required certifications (Criterion 6).
2. THE AI_Scheduling_Engine SHALL evaluate equipment on truck by verifying the resource's truck carries the required equipment for the job type (e.g., pressure gauge, compressor, specific fittings) to prevent wrong-truck dispatches (Criterion 7).
3. THE AI_Scheduling_Engine SHALL evaluate resource availability windows including shift start and end times, PTO, half-days, and training blocks, and shall not schedule outside approved hours (Criterion 8).
4. THE AI_Scheduling_Engine SHALL evaluate resource workload balance by distributing jobs evenly across the team, preventing one resource from being overloaded while another is underutilized on the same day (Criterion 9).
5. THE AI_Scheduling_Engine SHALL evaluate resource performance history including historical job completion speed, customer satisfaction scores, and callback rate per resource, matching high-complexity jobs to top performers (Criterion 10).

### Requirement 5: Customer and Job Attributes Criteria (Criteria 11–15)

**User Story:** As a User Admin, I want the AI to evaluate customer preferences, job characteristics, and relationship history when scheduling, so that customer satisfaction and loyalty are maximized.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate customer time-window preferences including customer-requested AM/PM or specific-hour windows, distinguishing between Hard_Constraints that cannot be violated and soft preferences the AI tries to honor (Criterion 11).
2. THE AI_Scheduling_Engine SHALL evaluate job type duration estimates using the default duration from the job type template, adjusted by the ML_Model based on historical actual durations for similar jobs considering zone count, system age, and resource speed (Criterion 12).
3. THE AI_Scheduling_Engine SHALL evaluate job priority level across tiers (emergency, VIP, standard, flexible), scheduling emergencies first, ensuring VIPs get preferred windows, and filling remaining capacity with standard and flexible jobs (Criterion 13).
4. THE AI_Scheduling_Engine SHALL evaluate customer lifetime value (CLV) to give high-CLV customers scheduling preference during high-demand periods and use CLV data to break ties when two jobs compete for the same slot (Criterion 14).
5. THE AI_Scheduling_Engine SHALL evaluate customer-resource relationship history, preferring resource pairings where the customer previously rated the resource 5 stars or requested them by name (Criterion 15).

### Requirement 6: Capacity and Demand Criteria (Criteria 16–20)

**User Story:** As a User Admin, I want the AI to evaluate capacity utilization, demand forecasts, and backlog pressure, so that scheduling density is optimized and future demand is anticipated.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate daily capacity utilization as the percentage of available resource-hours filled for each day, flagging days over 90% as overbooking risk and under 60% as underutilization opportunity (Criterion 16).
2. THE AI_Scheduling_Engine SHALL evaluate weekly demand forecast as the AI's predicted job volume for the coming 2 to 8 weeks based on historical patterns, seasonal trends, weather, and customer base size, used to pre-position capacity (Criterion 17).
3. THE AI_Scheduling_Engine SHALL evaluate seasonal peak windows including known high-demand periods (Spring Opening season, pre-freeze Fall Closing rush), front-loading scheduling and recommending overtime or temp staffing (Criterion 18).
4. THE AI_Scheduling_Engine SHALL evaluate cancellation and no-show probability using an ML_Model that predicts which scheduled jobs are most likely to cancel or no-show based on customer history, weather forecast, and day-of-week patterns, enabling over-scheduling of low-risk slots (Criterion 19).
5. THE AI_Scheduling_Engine SHALL evaluate pipeline and backlog pressure by tracking the number of unscheduled jobs in the queue and their aging (days since requested), escalating aging jobs and increasing scheduling density when backlog grows (Criterion 20).

### Requirement 7: Business Rules and Compliance Criteria (Criteria 21–25)

**User Story:** As a User Admin, I want the AI to enforce compliance deadlines, SLA commitments, and business rules around revenue and overtime, so that schedules are legally compliant and financially optimized.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate compliance deadlines including backflow test certification expiration, municipal inspection windows, and warranty service windows, scheduling these before the deadline (Criterion 21).
2. THE AI_Scheduling_Engine SHALL evaluate revenue per resource-hour by calculating effective revenue per hour (including drive time) for different job type mixes and optimizing the schedule to maximize total daily revenue rather than just job count (Criterion 22).
3. THE AI_Scheduling_Engine SHALL evaluate contract and SLA commitments with commercial or HOA customers that mandate response times (e.g., 24-hour, same-week), treating SLA deadlines as Hard_Constraints (Criterion 23).
4. THE AI_Scheduling_Engine SHALL evaluate overtime cost threshold using business rules defining when overtime becomes uneconomical, avoiding scheduling into overtime unless the job's revenue justifies the added labor cost (Criterion 24).
5. THE AI_Scheduling_Engine SHALL evaluate seasonal pricing signals including dynamic pricing rules (premium for Saturday, discount for Wednesday PM), steering flexible jobs toward off-peak slots and reserving peak slots for full-price work (Criterion 25).

### Requirement 8: External and Predictive Signal Criteria (Criteria 26–30)

**User Story:** As a User Admin, I want the AI to evaluate weather forecasts, predicted job complexity, lead conversion timing, resource start locations, and cross-job dependencies, so that schedules are resilient to external factors and multi-phase projects are properly sequenced.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate weather forecast impact by checking the 7-day weather forecast and proactively rescheduling outdoor jobs before rain or freeze events, filling gaps with indoor-safe jobs (Criterion 26).
2. THE AI_Scheduling_Engine SHALL evaluate predicted job complexity using an ML_Model that estimates actual job difficulty based on customer system age, zone count, last service date, and historical repair frequency, assigning longer time slots to complex jobs (Criterion 27).
3. THE AI_Scheduling_Engine SHALL evaluate lead-to-job conversion timing by identifying hot leads from the sales pipeline likely to convert within the week and reserving tentative capacity so new jobs can be slotted without disrupting existing schedules (Criterion 28).
4. THE AI_Scheduling_Engine SHALL evaluate resource location at shift start, determining whether the resource starts from home, the shop, or a job site (varying by day and resource) and using the correct origin point for first-job routing (Criterion 29).
5. THE AI_Scheduling_Engine SHALL evaluate cross-job dependency chains for multi-phase projects where Job B cannot start until Job A is complete (e.g., rough-in before head installation), enforcing phase sequencing and alerting if upstream delays threaten downstream jobs (Criterion 30).

### Requirement 9: User Admin AI Chat – Schedule Building and Modification

**User Story:** As a User Admin, I want to interact with the AI via natural-language chat to build, modify, and optimize schedules, so that I can manage complex scheduling operations conversationally without manual drag-and-drop.

#### Acceptance Criteria

1. WHEN a User_Admin requests "Build next week's schedule for spring openings", THE AI_Chat SHALL ask clarifying questions (resource count, customer priority overrides, optimization preference for fewest miles vs. fastest completion) and then auto-build the full week using criteria 1–5 (geography), 6–8 (resource fit), 11–13 (customer windows/priority), 16–18 (capacity), and 26 (weather).
2. WHEN a User_Admin requests "Reshuffle Thursday — two resources called out sick", THE AI_Chat SHALL ask which resources are out and whether to redistribute jobs to remaining resources, push to Friday, or flag for customer reschedule, then recalculate using criteria 8–9 (availability, workload balance), 1–2 (proximity, drive time), and 11 (customer windows).
3. WHEN a User_Admin requests "Add an emergency break-fix at [address], needs [specialist skill]", THE AI_Chat SHALL ask for estimated duration and customer time constraint, then evaluate criteria 6 (skill match), 7 (equipment), 1 (proximity), and 13 (emergency priority) to find the best-fit resource and slot.
4. WHEN a User_Admin requests "What does next month's capacity look like for [job type]?", THE AI_Chat SHALL ask about crew availability vs. total project slots and specific zones, then pull criteria 16–18 (capacity, demand, seasonal peaks) and 20 (backlog) to forecast.
5. WHEN a User_Admin requests to move a customer to a specific day and time with the same technician as last time, THE AI_Chat SHALL confirm the job details, last technician (with rating), and check availability using criteria 15 (relationship history), 11 (time window), and 1–2 (route impact).
6. WHEN a User_Admin requests "Show me which resources are underutilized this week and suggest how to fill their time", THE AI_Chat SHALL evaluate criteria 9 (workload balance), 16 (utilization), 20 (backlog pressure), and 17 (demand forecast) to identify resources below 70% utilization with specific fill suggestions.
7. WHEN a User_Admin requests batch scheduling (e.g., "Schedule all 350 fall closing customers across the next 5 weeks"), THE AI_Chat SHALL ask about zone prioritization (frost risk), customer preferences, and overtime approval, then batch-assign using criteria 3 (zones), 11 (preferences), 18 (seasonal peak), 26 (weather/frost forecast), and 6–7 (skills/equipment).
8. WHEN a User_Admin requests "What's the most profitable way to fill [day] — we have [N] open slots", THE AI_Chat SHALL evaluate criteria 22 (revenue per resource-hour), 13 (priority), 14 (customer LTV), 25 (pricing signals), and 20 (backlog aging) to rank candidate jobs by profitability.
9. WHEN a User_Admin requests weather-based rescheduling (e.g., "Rain is forecast all day Wednesday. Reschedule outdoor jobs and backfill with indoor work"), THE AI_Chat SHALL apply criterion 26 (weather), identify all outdoor-flagged jobs, search for indoor-eligible backlog, and use criteria 1–2 (routing) to rebuild.
10. WHEN a User_Admin requests recurring route setup (e.g., "Set up a recurring bi-weekly maintenance route for our top 20 commercial accounts"), THE AI_Chat SHALL ask about preferred days, same-resource preference, and SLA requirements, then use criteria 23 (SLA), 14 (LTV), 15 (relationship), 3 (zones), and 1–2 (routing) to build an efficient recurring template.

### Requirement 10: User Admin AI Chat – Schedule Overview Outputs

**User Story:** As a User Admin, I want AI Chat interactions to produce visible, actionable outputs in the Schedule Overview, so that I can review and approve AI-generated schedule changes.

#### Acceptance Criteria

1. WHEN the AI builds a weekly schedule, THE Schedule_Overview SHALL display the auto-generated schedule with jobs assigned by day, resource, and route sequence, along with a capacity heat map and flagged conflicts for review.
2. WHEN the AI reshuffles a day due to resource unavailability, THE Schedule_Overview SHALL display the revised schedule with reassigned jobs, updated ETAs, and a list of jobs that could not be absorbed (recommended for reschedule).
3. WHEN the AI inserts an emergency job, THE Schedule_Overview SHALL display the emergency job inserted into the nearest qualified resource's route with downstream ETAs recalculated and affected customers flagged for notification.
4. WHEN the AI provides a capacity forecast, THE Schedule_Overview SHALL display available multi-day project slots by week, crew availability, and recommended booking limits before over-commitment.
5. WHEN the AI moves a customer's job, THE Schedule_Overview SHALL display the job in its new slot with the assigned resource, recalculated routes for both the original and new days, and a drafted customer confirmation notification.
6. WHEN the AI identifies underutilized resources, THE Schedule_Overview SHALL display a utilization report per resource with specific suggestions: pull-forward jobs from next week, assign backlog items, or schedule proactive maintenance for service-agreement customers.
7. WHEN the AI completes batch scheduling, THE Schedule_Overview SHALL display the complete multi-week campaign with jobs assigned by week, zone, and resource, capacity utilization by week, and customer appointment notifications ready for batch send.
8. WHEN the AI ranks profitable jobs for open slots, THE Schedule_Overview SHALL display a ranked list of best-fit jobs with projected revenue impact and one-click assignment of the AI's top recommendation.
9. WHEN the AI reschedules weather-affected jobs, THE Schedule_Overview SHALL display the revised schedule with outdoor jobs pushed to the next available clear day, indoor backfill jobs assigned, and affected customers notified with new dates.
10. WHEN the AI creates a recurring route template, THE Schedule_Overview SHALL display the template with accounts clustered into geographic groups, assigned to designated resources, locked into the recurring cadence, and auto-populating future schedules.

### Requirement 11: User Admin Alerts – Critical Conflict Detection

**User Story:** As a User Admin, I want the AI to autonomously detect critical scheduling conflicts and present them as red alerts requiring immediate attention, so that I can resolve problems before they impact customers.

#### Acceptance Criteria

1. WHEN the AI detects two jobs assigned to the same resource at overlapping times, THE Alerts_Panel SHALL display a Double-Booking Conflict alert (red) with options to reassign one to another resource, shift one by 30 minutes, or extend the time gap, with one-click resolution.
2. WHEN the AI detects a job assigned to a resource who lacks the required certification (e.g., backflow test assigned to uncertified resource), THE Alerts_Panel SHALL display a Skill Mismatch alert (red) with the flagged job and a list of certified alternatives for one-click swap, with the AI recalculating both routes.
3. WHEN the AI detects a commercial customer's SLA commitment expiring before the scheduled job date, THE Alerts_Panel SHALL display an SLA Deadline at Risk alert (red) with the SLA countdown, a recommended slot today or tomorrow, and options to force-schedule or override to accept the SLA miss.
4. WHEN the AI detects a resource running 40 or more minutes behind via live tracking, THE Alerts_Panel SHALL display a Resource Running Behind alert (red) with impacted downstream jobs, new ETAs, and options to absorb the delay, move the last job to another resource, or reschedule to tomorrow, with customer notifications auto-drafted.
5. WHEN the AI detects severe weather incoming (e.g., freeze warning), THE Alerts_Panel SHALL display a Severe Weather alert (red) with all affected outdoor jobs highlighted and one-click batch-reschedule to the next available day with indoor-eligible backfill.

### Requirement 12: User Admin Suggestions – Optimization Opportunities

**User Story:** As a User Admin, I want the AI to autonomously surface optimization opportunities as green suggestions I can accept or dismiss, so that I can improve schedule efficiency and revenue without manually analyzing every route.

#### Acceptance Criteria

1. WHEN the AI identifies that swapping jobs between two resources would reduce combined drive time, THE Alerts_Panel SHALL display a Route Swap suggestion (green) with the proposed swap visualized on a map showing before/after drive times, with accept to execute or dismiss to keep current.
2. WHEN the AI identifies a resource with 2 or more hours unused and matching backlog jobs available, THE Alerts_Panel SHALL display an Underutilized Resource suggestion (green) with the gap details and candidate jobs ranked by revenue and proximity, with accept for one or all.
3. WHEN the AI identifies customer dissatisfaction feedback about the assigned resource from a previous visit, THE Alerts_Panel SHALL display a Customer Prefers Different Resource suggestion (green) with the customer's feedback and the AI's recommended alternative resource (higher satisfaction scores), with accept to reassign for all future jobs.
4. WHEN the AI identifies that shifting one low-priority job to another day would eliminate overtime for a resource, THE Alerts_Panel SHALL display an Overtime Avoidable suggestion (green) with the job recommended for shift, the overtime cost saved, and the alternative slot, with accept to move or dismiss.
5. WHEN the AI identifies a high-revenue job in the queue matching an open slot with a nearby resource, THE Alerts_Panel SHALL display a High-Revenue Job Available suggestion (green) with job details, proposed slot, projected revenue impact, and accept to auto-schedule with routing and customer confirmation handled.

### Requirement 13: User Admin Alert and Suggestion Interaction

**User Story:** As a User Admin, I want one-click resolution actions on alerts and suggestions, so that I can act on AI recommendations quickly without navigating away from the schedule.

#### Acceptance Criteria

1. WHEN a User_Admin clicks on a Double-Booking Conflict alert, THE System SHALL display both conflicting jobs with options to reassign, shift timing, or extend the gap, executable with one click.
2. WHEN a User_Admin clicks on a Skill Mismatch alert, THE System SHALL display the flagged job and a list of certified alternative resources, with one-click swap that triggers route recalculation for both resources.
3. WHEN a User_Admin clicks on an SLA Deadline at Risk alert, THE System SHALL display the SLA countdown and recommended slot, with approve to force-schedule or override to accept the miss.
4. WHEN a User_Admin clicks on a Resource Running Behind alert, THE System SHALL display impacted jobs with new ETAs and options to absorb, reassign, or reschedule, with auto-drafted customer notifications.
5. WHEN a User_Admin clicks on a Severe Weather alert, THE System SHALL display all affected jobs highlighted with one-click batch-reschedule and indoor backfill.
6. WHEN a User_Admin clicks on a Route Swap suggestion, THE System SHALL display the proposed swap on a map with before/after metrics, with accept or dismiss.
7. WHEN a User_Admin clicks on an Underutilized Resource suggestion, THE System SHALL display the gap and ranked candidate jobs, with accept for individual or all jobs and automatic re-routing.
8. WHEN a User_Admin clicks on a Customer Preference suggestion, THE System SHALL display the feedback and recommended alternative, with accept to reassign current and future jobs.
9. WHEN a User_Admin clicks on an Overtime Avoidable suggestion, THE System SHALL display the job, cost savings, and alternative slot, with accept or dismiss.
10. WHEN a User_Admin clicks on a High-Revenue Job suggestion, THE System SHALL display job details and revenue impact, with accept to auto-schedule including routing and customer confirmation.

### Requirement 14: Resource AI Chat – Field Operations

**User Story:** As a Resource (field technician), I want to interact with the AI via mobile chat to report delays, get pre-job info, request changes, and log work, so that I can handle field situations without calling the office.

#### Acceptance Criteria

1. WHEN a Resource reports "I'm running about 30 minutes behind on this job", THE AI_Chat SHALL auto-recalculate remaining ETAs on the resource's route; IF no customer windows are violated, adjust silently; IF a window is at risk, draft a delay notification and alert the User_Admin with resolution options.
2. WHEN a Resource asks "What do I need for my next job?", THE AI_Chat SHALL pull the next job's type template, customer system profile, and equipment checklist, generating a pre-arrival requirements list specific to that job.
3. WHEN a Resource reports additional work needed (e.g., "This customer needs 3 broken heads and a leaking valve fixed"), THE AI_Chat SHALL create a follow-up job request with the resource's field notes, estimate parts needed, and package it as a scheduling Change_Request for the User_Admin.
4. WHEN a Resource reports "Customer isn't home and the gate is locked", THE AI_Chat SHALL check the customer profile for alternative access instructions or secondary contact; IF none found, generate a Change_Request to the User_Admin to reschedule or attempt customer contact.
5. WHEN a Resource reports finishing early and asks for nearby work, THE AI_Chat SHALL evaluate unassigned jobs and backlog within a 15-minute radius matching the resource's skills and truck equipment, ranking by priority and revenue.
6. WHEN a Resource reports missing equipment and requests route resequencing (e.g., "I don't have the right nozzle kit, can I stop at the shop first?"), THE AI_Chat SHALL check if resequencing the route with a shop stop is feasible without violating time windows and package the route change for User_Admin approval.
7. WHEN a Resource reports unexpected job complexity and requests assistance (e.g., "This is a 16-zone with a lake pump, I need help"), THE AI_Chat SHALL identify available resources nearby with the required skill who have capacity and create a crew assistance Change_Request for the User_Admin.
8. WHEN a Resource logs parts used on a job (e.g., "Log that I replaced 4 spray heads and 2 rotors"), THE AI_Chat SHALL capture the parts, update the job completion record, adjust truck inventory, and IF stock falls below reorder threshold, flag for restocking.
9. WHEN a Resource asks "What's my schedule look like tomorrow?", THE AI_Chat SHALL pull tomorrow's assigned schedule with job details, route sequence, ETAs, and pre-job requirements for each stop.
10. WHEN a Resource requests a customer upgrade quote and install scheduling (e.g., "This customer wants a smart controller upgrade"), THE AI_Chat SHALL pull upgrade pricing from the catalog, create a quote draft, identify available install slots, and package both the quote and scheduling request for User_Admin approval.

### Requirement 15: Resource AI Chat – Outputs and Escalations

**User Story:** As a User Admin, I want Resource chat interactions to produce structured outputs and escalations in my Alerts Panel, so that I can approve or modify field-initiated changes efficiently.

#### Acceptance Criteria

1. WHEN a Resource reports running behind and customer windows are at risk, THE Alerts_Panel SHALL display an alert with options to absorb the delay, reassign the last job, or notify the customer, while the Resource's mobile view shows updated ETAs.
2. WHEN a Resource requests pre-job information, THE System SHALL display a pre-job checklist on the Resource's mobile view including job type, customer name and address, required equipment, known system issues, gate code, special instructions, and estimated duration.
3. WHEN a Resource requests a follow-up job, THE Alerts_Panel SHALL display a Change_Request with the resource's field notes, estimated duration, recommended parts, and a recommended slot (e.g., "Thursday PM").
4. WHEN a Resource reports a customer unavailable, THE Alerts_Panel SHALL display an alert with the resource's on-site status and recommendations to call the customer, reschedule, or proceed to the next job and return later.
5. WHEN a Resource requests nearby pickup work, THE System SHALL display 2–3 nearby available jobs with details on the Resource's mobile view; WHEN the Resource selects one, THE System SHALL request User_Admin approval and once approved, add the job to the route with navigation.
6. WHEN a Resource requests route resequencing for a shop stop, THE Alerts_Panel SHALL display the proposed resequenced route with time impact and an approve/deny option.
7. WHEN a Resource requests crew assistance, THE Alerts_Panel SHALL display the assistance request with the nearest qualified resource, their distance, current job status, and an approve/deny option.
8. WHEN a Resource logs parts and truck stock falls below minimum, THE Alerts_Panel SHALL display a suggestion to resupply the resource's truck before the next day.
9. WHEN a Resource requests tomorrow's schedule, THE System SHALL display a schedule card on the Resource's mobile view with jobs listed in route order including addresses, job types, estimated durations, customer notes, total estimated drive time, and pre-job requirements flagged for special prep.
10. WHEN a Resource requests a customer upgrade quote and scheduling, THE Alerts_Panel SHALL display the quote draft and scheduling request with recommended slot, quote amount, and approve options for both quote and schedule.

### Requirement 16: Resource Alerts – Schedule Changes and Pre-Job Requirements

**User Story:** As a Resource, I want to receive proactive alerts on my mobile view for schedule changes, pre-job requirements, and access instructions, so that I am always prepared and aware of changes without checking manually.

#### Acceptance Criteria

1. WHEN the User_Admin or AI adds a new job to the Resource's route, THE System SHALL display a Schedule Change – Job Added alert on the Resource's mobile view with the updated sequence, ETA, and tap-to-view job details and pre-job requirements.
2. WHEN a cancellation removes a job from the Resource's route, THE System SHALL display a Schedule Change – Job Removed alert with the updated route and gap time, and the AI SHALL suggest nearby backlog jobs to fill the gap (e.g., "You have a 45-min gap. Nearby backlog job available — tap to request.").
3. WHEN the User_Admin or AI resequences the Resource's remaining jobs (due to traffic, swap, or weather), THE System SHALL display a Route Resequenced alert with the reordered job list, a brief reason (e.g., "Traffic on I-35, new route avoids 20-min delay"), and updated navigation.
4. WHEN the next job requires equipment not typically on the truck (e.g., compressor for fall closing), THE System SHALL display a Pre-Job Requirement – Special Equipment alert 30 minutes before the job with a confirmation prompt ("Confirm you have it or reroute to shop first") and options for "Confirmed" or "Need Shop Stop."
5. WHEN the next job has specific access instructions, THE System SHALL display a Pre-Job Requirement – Customer Access alert 15 minutes before arrival with gate code, entry instructions, pet warnings, and customer contact preferences (e.g., "Gate code: 4521. Enter through side gate. Dog is friendly but loose in backyard. Customer requests text before arrival.").

### Requirement 17: Resource Suggestions – Proactive Guidance

**User Story:** As a Resource, I want to receive AI-generated suggestions for pre-job preparation, upsell opportunities, departure timing, and parts inventory, so that I can work more effectively and generate additional revenue.

#### Acceptance Criteria

1. WHEN the AI identifies that the next customer had a recurring issue in previous visits (e.g., recurring valve issue on Zone 3), THE System SHALL display a Pre-Job Prep suggestion card recommending the Resource carry specific spare parts (e.g., "Customer history: Zone 3 valve replaced twice in 18 months. Recommend carrying spare 1-inch globe valve and diaphragm kit.").
2. WHEN the AI detects the next customer's equipment is aging with frequent service calls (e.g., controller 12+ years old with 3 service calls in 2 years), THE System SHALL display an Upsell Opportunity suggestion card recommending the Resource mention an upgrade (e.g., "Customer's Hunter Pro-C is 14 years old (3 repairs in 2 yrs). Consider suggesting Hydrawise upgrade — saves customer on water bills and reduces callbacks.").
3. WHEN the AI calculates that departing later for the next job would avoid a traffic spike and arrive at the same time, THE System SHALL display an Optimized Departure Time suggestion (e.g., "Traffic on Hwy 71 peaks in 8 min. If you depart at 1:25 instead of 1:15, ETA is the same (1:52) with less drive stress.").
4. WHEN the AI predicts the Resource will run out of a commonly needed part before the last job based on today's remaining jobs, THE System SHALL display a Parts Running Low suggestion with current stock, predicted need, and nearest supply house (e.g., "Based on today's remaining 3 jobs, you may need 6+ spray heads. Current truck stock: 4. Consider picking up 6 more at supply house (2 min from Job #4).").
5. WHEN a Resource's previously submitted Change_Request has been pending User_Admin approval for an extended period, THE System SHALL display an Admin Decision Required alert with the request status and time since submission (e.g., "Your schedule change request (follow-up at 123 Oak St) is pending Admin approval. Submitted 25 min ago. Proceeding to next job per current route.").

### Requirement 18: Resource Alert and Suggestion Interaction

**User Story:** As a Resource, I want to interact with alerts and suggestions on my mobile view with simple tap actions, so that I can respond quickly while in the field.

#### Acceptance Criteria

1. WHEN a Resource taps on a Job Added alert, THE System SHALL display the new job details with pre-job requirements in the updated route context.
2. WHEN a Resource sees a Job Removed alert with a gap, THE System SHALL allow the Resource to tap to request a nearby backlog job to fill the gap.
3. WHEN a Resource taps on a Route Resequenced alert, THE System SHALL display the reordered job list with updated navigation ready to launch.
4. WHEN a Resource receives a Special Equipment alert, THE System SHALL provide "Confirmed" and "Need Shop Stop" buttons; WHEN "Need Shop Stop" is selected, THE System SHALL generate a route change request to the User_Admin.
5. WHEN a Resource receives a Customer Access alert, THE System SHALL display all access details with the option to text the customer before arrival if the customer preference indicates it.
6. WHEN a Resource taps on a Pre-Job Prep suggestion, THE System SHALL display the full customer history and recommended parts list.
7. WHEN a Resource taps on an Upsell Opportunity suggestion, THE System SHALL display the upgrade details and pricing, with an option to initiate a quote via AI_Chat.
8. WHEN a Resource taps on an Optimized Departure Time suggestion, THE System SHALL update the departure reminder accordingly.
9. WHEN a Resource taps on a Parts Running Low suggestion, THE System SHALL display the nearest supply house location with navigation option.
10. WHEN a Resource taps on a Pending Approval alert, THE System SHALL display the original Change_Request details and current status.

### Requirement 19: Required Data – Customer and System Profile

**User Story:** As a platform operator, I want the AI to have access to comprehensive customer and system/asset profile data, so that the AI can make informed scheduling decisions based on customer context and equipment details.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL have access to customer data including: customer ID, name, billing and service addresses (geocoded lat/long), phone, email, preferred contact method, property type (residential, commercial, HOA, municipal), customer time-window preferences (hard AM/PM, soft preferred times), CLV score, customer satisfaction scores (per-visit and aggregate NPS), customer-resource relationship history (who served them, ratings), service agreement details (level, SLA terms, pricing tier), gate codes, access instructions, pet warnings, special notes, and communication preference (SMS, email, phone, app notification).
2. THE AI_Scheduling_Engine SHALL have access to customer system and asset profile data including: system age and install date, zone count, zone types (rotor, spray, drip), head counts per zone, water source type (city, well, lake, reclaimed), controller make/model, station count, Wi-Fi capability, backflow preventer type, serial number, last test date, certification expiry, pump details (make, model, HP) if applicable, known recurring issues (from service history), equipment installed (head models, pipe types, valve types), and last service date and type per asset.

### Requirement 20: Required Data – Job and Resource

**User Story:** As a platform operator, I want the AI to have access to comprehensive job and resource data, so that the AI can match jobs to the right resources with the right skills and equipment.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL have access to job data including: job ID, job type (from configurable template), status (unscheduled, scheduled, in-progress, complete), job address (geocoded), service zone assignment, estimated duration (template default plus AI-adjusted prediction), required skills and certifications, required equipment checklist, priority level (emergency, VIP, standard, flexible), customer-requested time window (hard/soft), revenue and price for the job, job phase (for multi-day projects: phase sequence, dependencies), job notes, field observations, parts used, completion photos, SLA deadline (if commercial/contract), and source (customer-requested, proactive AI-generated, follow-up from field).
2. THE AI_Scheduling_Engine SHALL have access to resource data including: resource ID, name, contact info, skill tags and certifications (with expiration dates), home base address (geocoded), shift schedule (start/end times, days of week), PTO, sick days, training blocks, unavailability windows, current GPS location (live, from mobile app), truck/vehicle assignment and current equipment inventory, performance metrics (average job duration by type, customer satisfaction, callback rate), preferred zones and geographic assignments, and current job status (idle, en route, on-site, complete).

### Requirement 21: Required Data – Schedule, Geographic, External, and Financial

**User Story:** As a platform operator, I want the AI to have access to schedule history, geographic data, external signals, and financial data, so that the AI can optimize routes, predict demand, and maximize revenue.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL have access to schedule data including: daily and weekly schedule with job-to-resource assignments and sequence order, route sequence per resource (ordered stops with ETAs), job status transitions with timestamps (assigned, departed, arrived, started, completed), actual vs. estimated duration per job, cancellations, no-shows, and reschedules with reasons, capacity utilization by day/zone/resource, and historical schedule data (multi-year for ML training).
2. THE AI_Scheduling_Engine SHALL have access to geographic and logistics data including: drive-time matrix between all job-pair addresses (from mapping API), real-time traffic conditions (from mapping API), service zone boundary definitions (polygon coordinates or ZIP groupings), and supply house and shop locations (for restocking stops).
3. THE AI_Scheduling_Engine SHALL have access to external and predictive data including: 7-day weather forecast (temperature, precipitation, freeze warnings), municipal compliance calendars (backflow test deadlines, watering restrictions), seasonal demand patterns (historical job volume by week/type/zone, multi-year), cancellation and no-show probability model outputs (per scheduled job), job complexity prediction model outputs (predicted actual duration), and lead conversion probability scores (from sales pipeline).
4. THE AI_Scheduling_Engine SHALL have access to financial data including: revenue per job (actual, by type), cost per resource-hour (fully loaded: wages, benefits, truck, fuel), overtime rate and threshold rules, dynamic pricing rules (peak/off-peak multipliers, discount triggers), parts and material costs per job, and customer payment history and billing preferences.

### Requirement 22: Interacting Business Components – Data Sourcing

**User Story:** As a platform operator, I want the scheduling module to integrate with all surrounding business components for data sourcing, so that the AI has complete context for scheduling decisions.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL read from Customer Intake: new job requests, job type classification, customer details, urgency level, and requested time windows.
2. THE AI_Scheduling_Engine SHALL read from Sales and Quoting: approved quotes with scope and duration, customer contact info, preferred start dates, and project phases for multi-day installs.
3. THE AI_Scheduling_Engine SHALL read from Marketing and Lead Management: active campaign calendars (which may drive inbound volume spikes), lead conversion probabilities (to reserve tentative capacity), and seasonal outreach schedules (spring opening reminders that generate scheduling demand).
4. THE AI_Scheduling_Engine SHALL trigger Customer Communication for: appointment confirmations, ETA updates, delay notifications, reschedule requests, and pre-job reminders, with the Communication component handling delivery via SMS, email, or app push.
5. THE AI_Scheduling_Engine SHALL read from Workforce and HR Management: employee roster with roles, certifications, and skill tags; shift schedules and PTO calendars; onboarding status of new hires; and certification expiration dates for compliance scheduling.
6. THE AI_Scheduling_Engine SHALL read from Inventory and Equipment Management: what equipment is on each truck, stock levels of common parts, and reorder thresholds. THE AI_Scheduling_Engine SHALL trigger low-stock alerts when field consumption depletes a resource's truck inventory.
7. THE AI_Scheduling_Engine SHALL read from Financial, Billing, and Invoicing: job pricing, resource cost rates (for revenue-per-hour optimization), overtime thresholds, and customer payment status (to deprioritize delinquent accounts). THE AI_Scheduling_Engine SHALL trigger job completion events that initiate invoicing.
8. THE AI_Scheduling_Engine SHALL read from Reporting and Analytics: historical job durations, customer satisfaction trends, seasonal volume patterns, and resource efficiency metrics. THE AI_Scheduling_Engine SHALL write schedule adherence data, capacity utilization, and delay frequency to Reporting and Analytics.
9. THE AI_Scheduling_Engine SHALL read from Compliance and Regulatory: backflow test certification expiry dates, municipal inspection requirements, watering restriction schedules, and permit deadlines. THE AI_Scheduling_Engine SHALL generate proactive jobs when compliance deadlines approach.
10. THE AI_Scheduling_Engine SHALL read from CRM as the single source of truth for all customer-facing data: customer profiles, lifetime value scores, satisfaction history, communication preferences, and resource-customer relationship ratings.

### Requirement 23: Competitive Differentiation – 30-Constraint Simultaneous Evaluation

**User Story:** As a platform operator, I want the AI scheduling engine to evaluate all 30 decision criteria simultaneously, so that the system produces schedules that are fundamentally superior to competitors who only evaluate 5–8 basic constraints.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL evaluate all 30 Decision_Criteria simultaneously when building, validating, or optimizing a schedule, compared to competitors (ServiceTitan, Jobber, Housecall Pro, FieldEdge) who evaluate only 5–8 basic constraints (availability, location, skills).
2. THE AI_Scheduling_Engine SHALL include predictive signals (weather, cancellation probability, job complexity, lead conversion timing) that no competitor considers in their scheduling algorithms.
3. THE AI_Scheduling_Engine SHALL build complete schedules autonomously and present them for User_Admin review and approval, rather than requiring humans to build every schedule manually.
4. THE AI_Scheduling_Engine SHALL predict delays, cancellations, demand spikes, and job complexity before they occur, operating proactively rather than purely reactively.
5. THE AI_Scheduling_Engine SHALL optimize for revenue per resource-hour (factoring in CLV, dynamic pricing, and cost-to-serve) rather than simply maximizing job count.
6. THE AI_Scheduling_Engine SHALL support vertical configurability through Vertical_Playbooks where irrigation is a configuration pack rather than custom code, enabling future adaptation to other field service verticals.
7. THE AI_Scheduling_Engine SHALL provide weather-aware scheduling that monitors forecasts and proactively reschedules outdoor jobs before weather hits, backfilling with indoor-eligible work.

### Requirement 24: Security, Compliance, and Guardrails

**User Story:** As a platform operator, I want the AI scheduling system to protect data, enforce guardrails on AI interactions, and comply with security requirements, so that customer data is safe and the AI stays focused on scheduling tasks.

#### Acceptance Criteria

1. THE AI_Scheduling_Engine SHALL protect all customer PII in accordance with security and compliance requirements, ensuring data is encrypted in transit and at rest.
2. THE AI_Scheduling_Engine SHALL enforce guardrails on AI_Chat interactions to prevent responses to questions not related to scheduling, job management, or field operations.
3. THE AI_Scheduling_Engine SHALL log all AI interactions to an audit trail for compliance and debugging purposes.
4. THE AI_Scheduling_Engine SHALL support configurable minimum data requirements so that the system can operate with partial data during initial setup, gracefully degrading AI capabilities when data is incomplete.
5. IF a user asks the AI_Chat a question unrelated to scheduling or field operations, THEN THE AI_Chat SHALL redirect the user to the appropriate topic and decline to answer the off-topic question.

### Requirement 25: Data Migration and Onboarding

**User Story:** As a new customer, I want a clear path to migrate my existing scheduling data into the system and start using AI features with minimal friction, so that I can realize value quickly even with imperfect data.

#### Acceptance Criteria

1. THE System SHALL provide data migration tools to import existing customer, job, resource, and schedule data from external systems.
2. THE System SHALL provide data cleaning functions to normalize and validate imported data (e.g., geocoding addresses, standardizing job types, mapping skill tags).
3. THE System SHALL define minimum data requirements for each AI capability tier, allowing customers to start with basic scheduling and unlock advanced features (predictive intelligence, revenue optimization) as more data becomes available.
4. WHEN imported data is incomplete or inconsistent, THE System SHALL flag data quality issues and provide guided remediation steps.
5. THE System SHALL support incremental data enrichment where historical data improves ML_Model accuracy over time without requiring a complete dataset at onboarding.

### Requirement 26: Unit Testing with Property-Based Testing (PBT)

**User Story:** As a developer, I want comprehensive unit tests with property-based testing for all scheduling logic, so that correctness properties are formally validated with generated inputs and all business logic is tested in isolation.

#### Acceptance Criteria

1. ALL unit tests SHALL be located in `src/grins_platform/tests/unit/` and marked with `@pytest.mark.unit`.
2. ALL unit tests SHALL mock external dependencies (database, APIs, AI services) so they run with zero infrastructure requirements.
3. THE unit test suite SHALL include property-based tests (PBT) using Hypothesis for the following correctness properties:
   - FOR ALL schedule generation operations, generating a schedule and then validating it against all Hard_Constraints SHALL produce zero violations (hard constraint invariant property).
   - FOR ALL AI_Chat constraint parsing operations, parsing a natural language constraint, converting it to structured parameters, and then describing it back in natural language SHALL preserve the original intent (round-trip property).
   - FOR ALL tier-to-priority mappings applied during scheduling, the priority assigned to a job SHALL match the Tier_Priority_Map for the associated service agreement tier (mapping correctness property).
   - FOR ALL resource-to-job assignments, the assigned resource SHALL hold every skill tag and certification required by the job type (skill match invariant property).
   - FOR ALL resource-to-job assignments, the assigned resource's truck equipment SHALL include every item in the job's required equipment checklist (equipment match invariant property).
   - FOR ALL generated schedules, no resource SHALL have overlapping job time windows (no-overlap invariant property).
   - FOR ALL generated schedules, every job assigned to a resource SHALL fall within that resource's availability window (availability invariant property).
   - FOR ALL alert generation operations, a double-booking conflict detected by the AI SHALL correspond to an actual time overlap between two jobs on the same resource (alert accuracy property).
4. THE unit test suite SHALL test the AI_Scheduling_Engine decision criteria evaluation logic for each of the 30 criteria individually with mocked data inputs.
5. THE unit test suite SHALL test the Alerts_Panel generation logic for all 5 alert types (double-booking, skill mismatch, SLA risk, resource behind, severe weather) and all 5 suggestion types (route swap, underutilized resource, customer preference, overtime avoidable, high-revenue job).
6. THE unit test suite SHALL test the Change_Request packaging logic for all 10 Resource AI Chat interaction types.
7. THE unit test suite SHALL achieve minimum 85% code coverage on all scheduling service modules.
8. ALL unit tests SHALL pass with zero failures when run via `uv run pytest -m unit -v`.

### Requirement 27: Functional Testing

**User Story:** As a developer, I want functional tests that validate complete user workflows against a real database, so that scheduling operations work end-to-end as users would experience them.

#### Acceptance Criteria

1. ALL functional tests SHALL be located in `src/grins_platform/tests/functional/` and marked with `@pytest.mark.functional`.
2. ALL functional tests SHALL use a real PostgreSQL test database (not mocks) to validate data persistence and query correctness.
3. THE functional test suite SHALL validate the following User Admin workflows:
   - Schedule building via AI_Chat (natural language command → clarifying questions → schedule generated → Schedule_Overview updated).
   - Emergency job insertion (chat command → AI finds best-fit resource → job inserted → downstream ETAs recalculated).
   - Alert resolution (double-booking detected → admin clicks alert → one-click reassignment → routes recalculated).
   - Suggestion acceptance (route swap suggested → admin accepts → both routes updated → drive time reduced).
   - Batch scheduling (350 fall closing jobs → zone prioritization → 5-week schedule generated).
4. THE functional test suite SHALL validate the following Resource workflows:
   - Running late report (resource reports delay → ETAs recalculated → admin alerted if windows at risk).
   - Pre-job requirements retrieval (resource asks → checklist generated with equipment, access, customer history).
   - Follow-up job request (resource reports additional work → Change_Request packaged → admin alert created).
   - Parts logging (resource logs parts → job record updated → truck inventory decremented → low-stock flagged).
   - Nearby pickup work (resource finishes early → nearby jobs listed → admin approval → job added to route).
5. THE functional test suite SHALL validate schedule generation constraint satisfaction with real database records for staff availability, equipment assignments, job priorities, and customer time windows.
6. THE functional test suite SHALL validate the alert and suggestion generation pipeline end-to-end: data input → criteria evaluation → alert/suggestion created → admin interaction → resolution applied.
7. ALL functional tests SHALL pass with zero failures when run via `uv run pytest -m functional -v`.

### Requirement 28: Integration Testing

**User Story:** As a developer, I want integration tests that validate cross-component interactions and external service integrations, so that the scheduling system works correctly with all surrounding business components.

#### Acceptance Criteria

1. ALL integration tests SHALL be located in `src/grins_platform/tests/integration/` and marked with `@pytest.mark.integration`.
2. ALL integration tests SHALL use the full system stack (database, Redis, API layer) to validate end-to-end behavior.
3. THE integration test suite SHALL validate the AI_Scheduling_Engine integration with external services:
   - Google Maps API integration for travel time calculations (with fallback to straight-line distance when API is unavailable).
   - OpenAI/Claude API integration for AI_Chat responses, schedule explanations, constraint parsing, and alert generation (with graceful degradation when AI service is unavailable).
   - Weather forecast API integration for weather-aware scheduling (with fallback behavior when forecast data is unavailable).
4. THE integration test suite SHALL validate cross-component data flows:
   - Customer Intake → Scheduling: new job request flows into scheduling queue with correct priority, time windows, and customer data.
   - Sales/Quoting → Scheduling: approved quote creates schedulable job with correct duration, phases, and customer preferences.
   - Scheduling → Customer Communication: schedule changes trigger correct notification events (confirmation, ETA update, delay, reschedule). Note: actual SMS/email delivery via Twilio is deferred; test validates notification event creation only.
   - Scheduling → Financial/Billing: job completion events trigger invoicing with correct amounts and customer data.
   - Scheduling → Inventory/Equipment: parts logging decrements truck inventory and triggers low-stock alerts at threshold.
   - Scheduling → Reporting/Analytics: schedule adherence data, capacity utilization, and delay frequency are written correctly.
   - CRM → Scheduling: customer profile changes (CLV score, satisfaction, relationship history) are reflected in scheduling decisions.
   - Compliance → Scheduling: approaching compliance deadlines generate proactive scheduling jobs.
5. THE integration test suite SHALL validate API endpoint behavior for all scheduling API routes:
   - POST `/api/v1/schedule/generate` — schedule generation with constraint validation.
   - POST `/api/v1/schedule/explain` — schedule explanation generation.
   - POST `/api/v1/schedule/explain-unassigned` — unassigned job explanation.
   - POST `/api/v1/schedule/parse-constraints` — natural language constraint parsing.
   - POST `/api/v1/ai/chat` — AI Chat interactions for both User Admin and Resource roles.
   - All alert and suggestion CRUD endpoints.
   - All Change_Request approval/denial endpoints.
6. THE integration test suite SHALL validate authentication and authorization: User_Admin endpoints SHALL reject Resource-role tokens and vice versa where role restrictions apply.
7. THE integration test suite SHALL validate rate limiting on AI-powered endpoints to prevent abuse.
8. ALL integration tests SHALL pass with zero failures when run via `uv run pytest -m integration -v`.

### Requirement 29: End-to-End Browser Testing with agent-browser

**User Story:** As a developer, I want end-to-end browser tests using agent-browser (Vercel) that validate the complete user experience across all three UI surfaces, so that visual rendering, user interactions, and data flows are verified in a real browser environment.

#### Acceptance Criteria

1. ALL E2E tests SHALL be implemented as bash scripts in `scripts/e2e/` and registered in the `scripts/e2e-tests.sh` test runner.
2. ALL E2E tests SHALL use the `agent-browser` CLI (Vercel Agent Browser) for browser automation, using snapshot-based element refs (`@e1`, `@e2`) for reliable element selection.
3. THE E2E test suite SHALL validate the Schedule Overview UI surface:
   - Schedule displays all assigned jobs across technicians by day and week with correct status indicators (confirmed, in-progress, completed, flagged).
   - Capacity utilization percentages are displayed and update after schedule generation.
   - Add/remove resource controls function correctly.
   - Schedule generation produces visible results grouped by staff member with route sequences.
   - Capacity heat map renders correctly with overbooking (>90%) and underutilization (<60%) indicators.
4. THE E2E test suite SHALL validate the Alerts/Suggestions Panel UI surface:
   - Alerts (red) and suggestions (green) render below the Schedule Overview with correct color coding.
   - One-click resolution actions on alerts execute correctly (reassign, shift timing, force-schedule).
   - Suggestion accept/dismiss actions execute correctly and update the schedule.
   - Alert and suggestion counts update in real-time as the AI generates new items.
5. THE E2E test suite SHALL validate the AI Chat UI surface for User Admin:
   - Chat input accepts natural language commands and displays AI responses.
   - Clarifying questions from the AI are displayed and user responses are processed.
   - Schedule changes from chat commands are reflected in the Schedule Overview.
6. THE E2E test suite SHALL validate the AI Chat UI surface for Resource (mobile viewport):
   - Mobile viewport tests SHALL use `agent-browser set viewport 375 812` for mobile simulation.
   - Pre-job requirements display correctly on the Resource's mobile view.
   - Schedule change alerts (job added, removed, resequenced) display on the Resource's mobile view.
   - Resource chat interactions (running late, pre-job info, parts logging) produce correct responses.
7. THE E2E test suite SHALL validate responsive behavior at three viewports:
   - Mobile: 375×812 (Resource mobile view).
   - Tablet: 768×1024 (Admin tablet view).
   - Desktop: 1440×900 (Admin desktop view).
8. ALL E2E tests SHALL capture screenshots to `e2e-screenshots/` organized by feature for visual regression review.
9. ALL E2E tests SHALL verify database state after UI interactions using direct database queries (e.g., `psql "$DATABASE_URL" -c "SELECT ..."`) to confirm data persistence.
10. THE E2E test runner SHALL support `--headed` mode for debugging and `--test NAME` for running individual tests.
11. THE E2E test suite SHALL include pre-flight checks for frontend (http://localhost:5173), backend (http://localhost:8000), and agent-browser installation before executing tests.
12. ALL E2E tests SHALL pass with zero failures when run via `bash scripts/e2e-tests.sh`.

### Requirement 30: Code Quality, Linting, and Type Safety

**User Story:** As a developer, I want all scheduling code to pass linting, formatting, and type checking with zero errors, so that code quality is maintained and regressions are caught early.

#### Acceptance Criteria

1. ALL Python code in the scheduling feature SHALL pass Ruff linting with zero violations when run via `uv run ruff check src/`.
2. ALL Python code in the scheduling feature SHALL be formatted according to Ruff formatting rules (88 character lines) when run via `uv run ruff format src/`.
3. ALL Python code in the scheduling feature SHALL pass MyPy type checking with zero errors when run via `uv run mypy src/`.
4. ALL Python code in the scheduling feature SHALL pass Pyright type checking with zero errors when run via `uv run pyright src/`.
5. ALL Python functions in the scheduling feature SHALL have complete type hints on all parameters and return types, with no implicit `Any` types.
6. ALL frontend TypeScript/React components for the scheduling feature SHALL pass Vitest tests when run via `npm test` in the `frontend/` directory.
7. ALL frontend components SHALL achieve minimum 80% code coverage, hooks 85%, and utility functions 90%.
8. ALL frontend components SHALL use `data-testid` attributes following the project convention (`{feature}-page`, `{feature}-table`, `{action}-{feature}-btn`) for reliable test selection.

### Requirement 31: External Service API Key Configuration and Testing

**User Story:** As a developer, I want all external service integrations to have proper API key configuration with environment variables and testable fallback behavior, so that the system works in development, testing, and production environments.

#### Acceptance Criteria

1. THE System SHALL require the following environment variables for external service integrations:
   - `OPENAI_API_KEY` for AI Chat, schedule explanations, constraint parsing, and alert generation via the OpenAI/Claude API.
   - `GOOGLE_MAPS_API_KEY` for travel time calculations, real-time traffic conditions, and drive-time matrix generation.
   - `REDIS_URL` for caching AI query results, rate limiting, and staff location data.
   - `DATABASE_URL` for PostgreSQL connection (schedule data, job data, resource data, customer data).
2. THE System SHALL validate all required API keys at startup and log clear error messages identifying which keys are missing or invalid.
3. THE System SHALL support graceful degradation for each external service:
   - WHEN `OPENAI_API_KEY` is missing or the AI service is unavailable, THE System SHALL fall back to the OR_Tools_Solver for schedule generation without AI-enhanced features (no explanations, no constraint parsing, no chat).
   - WHEN `GOOGLE_MAPS_API_KEY` is missing or the Google Maps API is unavailable, THE System SHALL fall back to straight-line distance calculation with a 1.4x factor for travel time estimates.
   - WHEN `REDIS_URL` is missing or Redis is unavailable, THE System SHALL operate without caching (direct database queries) with degraded performance.
4. ALL integration tests involving external services SHALL use mock/stub implementations by default, with an option to run against real APIs using environment flags (e.g., `USE_REAL_GOOGLE_MAPS=true`).
5. THE `.env.example` file SHALL document all required and optional environment variables for the scheduling feature with descriptions and example values.

### Requirement 32: Structured Logging for Scheduling Operations

**User Story:** As a developer, I want all scheduling operations to produce structured logs following the project's logging conventions, so that scheduling decisions, AI interactions, and errors can be traced and debugged.

#### Acceptance Criteria

1. ALL scheduling service classes SHALL use `LoggerMixin` with `DOMAIN = "scheduling"` and follow the `{domain}.{component}.{action}_{state}` naming pattern (e.g., `scheduling.engine.generate_started`, `scheduling.chat.parse_completed`, `scheduling.alert.detect_failed`).
2. THE AI_Scheduling_Engine SHALL log the start and completion of every schedule generation operation with: job count, resource count, criteria evaluated, generation duration, and optimization score.
3. THE AI_Chat SHALL log every user interaction with: user role (admin/resource), message type (command/question/change-request), parsed intent, and response time.
4. THE Alerts_Panel generation SHALL log every alert and suggestion created with: alert type, severity, criteria that triggered it, and affected resources/jobs.
5. ALL external API calls (Google Maps, OpenAI/Claude) SHALL log request initiation, response status, latency, and any errors with full context.
6. THE System SHALL NEVER log customer PII (full addresses, phone numbers, email addresses), passwords, API keys, or JWT tokens in any log output.
7. ALL scheduling logs SHALL include request correlation IDs for tracing operations across services.

### Requirement 33: Testing and Quality Assurance Strategy

**User Story:** As a platform operator, I want a comprehensive testing strategy for the AI scheduling system, so that functionality is validated before market release and technical debt is minimized.

#### Acceptance Criteria

1. THE System SHALL support a testing strategy that validates all 30 Decision_Criteria individually and in combination before market release.
2. THE System SHALL support simulation testing with realistic scheduling scenarios (seasonal peaks, emergency insertions, weather events, resource unavailability) to validate AI decision quality.
3. THE System SHALL provide schedule quality metrics (total drive time, capacity utilization, SLA compliance rate, revenue per resource-hour) that can be compared across algorithm versions.
4. THE System SHALL support A/B testing of scheduling algorithms to measure improvement before full rollout.
5. THE System SHALL implement incremental feature release to avoid overbuilding, testing each capability within the market before adding the next.
6. THE complete test suite (unit + functional + integration + E2E) SHALL be runnable via a single command sequence:
   - `uv run pytest -m unit -v` (unit tests, no infrastructure required).
   - `uv run pytest -m functional -v` (functional tests, requires PostgreSQL).
   - `uv run pytest -m integration -v` (integration tests, requires full stack).
   - `bash scripts/e2e-tests.sh` (E2E browser tests, requires frontend + backend + agent-browser).
7. ALL quality checks SHALL pass with zero errors before any code is merged: `uv run ruff check --fix src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v`.

### Requirement 34: LLM Selection and AI Infrastructure

**User Story:** As a platform operator, I want the AI infrastructure to support flexible LLM selection and cost-effective AI operations, so that the system can evolve with AI technology improvements.

#### Acceptance Criteria

1. THE System SHALL support configurable LLM selection for different AI functions (chat, explanations, constraint parsing, predictions), allowing different models for different cost/quality tradeoffs.
2. THE System SHALL track AI usage costs per function (chat interactions, schedule explanations, constraint parsing, alert generation) for pricing and optimization purposes.
3. THE System SHALL implement caching for repeated AI queries (e.g., similar schedule explanations, common constraint patterns) to reduce LLM costs.
4. THE System SHALL support graceful degradation when AI services are unavailable, falling back to the existing OR_Tools_Solver for schedule generation without AI-enhanced features.
5. THE System SHALL protect proprietary scheduling logic and AI prompts as intellectual property, separating the generic engine from vertical-specific configuration.

### Requirement 35: Storage and Scalability

**User Story:** As a platform operator, I want the system to handle per-user storage requirements and scale with growing customer bases, so that performance remains consistent as the platform grows.

#### Acceptance Criteria

1. THE System SHALL define and enforce per-user storage limits for schedule history, AI interaction logs, and ML training data.
2. THE System SHALL archive historical schedule data beyond a configurable retention period while maintaining access for ML training purposes.
3. THE System SHALL scale schedule generation performance linearly with the number of jobs and resources, maintaining sub-30-second generation for up to 50 jobs per the existing route-optimization spec.
4. WHEN the job count exceeds the single-generation threshold, THE System SHALL support batch generation that partitions jobs by zone or resource group for parallel optimization.
