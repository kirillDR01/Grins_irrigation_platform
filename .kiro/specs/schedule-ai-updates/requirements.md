# Requirements Document

## Introduction

This document specifies the requirements for overhauling the AI scheduling system in Grin's Irrigation Platform. The current "AI Generation" tab is broken and confusing - it doesn't actually use AI for scheduling decisions and assigns all jobs to a single staff member. This feature will remove the broken AI tab, keep the working OR-Tools optimization, and add practical AI features that enhance the scheduling workflow with explanations, suggestions, and natural language interaction.

The key principle is: **Use AI for what it's good at** (explaining decisions, understanding context, parsing natural language) while keeping algorithms for what they're good at (route optimization, constraint satisfaction, travel time calculation).

## Glossary

- **Schedule_Generator**: The system component that creates optimized schedules using OR-Tools constraint solver
- **AI_Explanation_Service**: The service that uses Claude API to generate natural language explanations of scheduling decisions
- **Constraint_Parser**: The service that converts natural language constraints into solver parameters
- **Scheduling_Help_Assistant**: The AI chat component that answers questions about the scheduling system
- **Unassigned_Job**: A job that could not be scheduled due to constraints (capacity, equipment, time)
- **OR_Tools_Solver**: The Google OR-Tools constraint programming solver used for route optimization
- **Staff_Assignment**: The mapping of jobs to staff members with time slots and routes
- **Natural_Language_Constraint**: A scheduling rule expressed in plain English by the user

## Requirements

### Requirement 1: Remove Broken AI Generation Tab

**User Story:** As a business owner, I want a single clear scheduling workflow, so that I'm not confused by duplicate options that don't work properly.

#### Acceptance Criteria

1. WHEN the user navigates to the Schedule Generation page THEN THE System SHALL display only one generation option (not separate Manual/AI tabs)
2. THE System SHALL rename "Manual Generation" to "Generate Schedule" as the single scheduling action
3. WHEN the broken AI Generation tab code is removed THEN THE System SHALL preserve all working OR-Tools optimization functionality
4. THE System SHALL maintain all existing schedule preview, capacity overview, and map visualization features

### Requirement 2: Schedule Explanation Feature

**User Story:** As a business owner, I want to understand why jobs were assigned the way they were, so that I can trust the system and make informed adjustments.

#### Acceptance Criteria

1. WHEN a schedule is generated THEN THE System SHALL display an "Explain This Schedule" button in the results view
2. WHEN the user clicks the explain button THEN THE AI_Explanation_Service SHALL analyze the schedule and generate a natural language explanation
3. THE AI_Explanation_Service SHALL explain staff assignments including geographic grouping rationale
4. THE AI_Explanation_Service SHALL explain time slot decisions including priority job handling
5. THE AI_Explanation_Service SHALL mention equipment-based assignment decisions when relevant
6. THE AI_Explanation_Service SHALL describe route optimization choices (e.g., "Eden Prairie jobs grouped in morning")
7. WHEN generating explanations THEN THE System SHALL NOT include customer PII (full addresses, phone numbers) in AI prompts
8. THE System SHALL display the explanation in a readable card or modal format
9. IF the AI service is unavailable THEN THE System SHALL display a graceful error message and allow retry

### Requirement 3: Unassigned Job Explanations

**User Story:** As a business owner, I want to know why specific jobs couldn't be scheduled with actionable suggestions, so that I can quickly resolve scheduling conflicts.

#### Acceptance Criteria

1. WHEN a schedule is generated with unassigned jobs THEN THE System SHALL display each unassigned job with a "Why?" link
2. WHEN the user clicks the "Why?" link THEN THE AI_Explanation_Service SHALL explain the specific reason the job couldn't be scheduled
3. THE AI_Explanation_Service SHALL identify constraint violations (equipment mismatch, capacity exceeded, time conflicts)
4. THE AI_Explanation_Service SHALL provide actionable suggestions for resolving the conflict
5. THE suggestions SHALL include specific alternatives (e.g., "Move a non-compressor job to tomorrow", "Schedule for Thursday when Viktor has 2 hours free")
6. THE System SHALL display explanations in an expandable card format for each unassigned job
7. WHEN multiple jobs are unassigned for the same reason THEN THE System SHALL group similar explanations to reduce redundancy
8. IF the AI service is unavailable THEN THE System SHALL display the basic constraint violation reason from the solver

### Requirement 4: Natural Language Constraints

**User Story:** As a business owner, I want to express scheduling preferences in plain English, so that I don't need to learn complex UI controls.

#### Acceptance Criteria

1. THE System SHALL display a "Scheduling Constraints" text area on the schedule generation page
2. WHEN the user types a constraint in natural language THEN THE Constraint_Parser SHALL parse it into structured parameters
3. THE Constraint_Parser SHALL support staff time restrictions (e.g., "Don't schedule Viktor before 10am on Mondays")
4. THE Constraint_Parser SHALL support job grouping requests (e.g., "Keep Johnson and Smith jobs together")
5. THE Constraint_Parser SHALL support staff-job restrictions (e.g., "Vas shouldn't do lake pump jobs")
6. THE Constraint_Parser SHALL support geographic preferences (e.g., "Finish Eden Prairie by noon")
7. WHEN constraints are parsed THEN THE System SHALL display a preview of the interpreted constraints before generation
8. THE System SHALL allow the user to edit or remove parsed constraints before generating
9. WHEN the schedule is generated THEN THE OR_Tools_Solver SHALL respect the parsed constraints
10. IF a constraint cannot be parsed THEN THE System SHALL display a helpful error message with examples
11. THE System SHALL optionally save frequently used constraints for future use

### Requirement 5: Scheduling AI Help Assistant

**User Story:** As a user, I want an AI assistant that can answer questions about the scheduling system, so that I can learn how to use it effectively without reading documentation.

#### Acceptance Criteria

1. THE System SHALL display an AI Help panel on the Schedule Generation page
2. THE Scheduling_Help_Assistant SHALL display sample questions as clickable buttons
3. THE sample questions SHALL include: "How do I generate a schedule?", "How does the system decide who to assign jobs to?", "Why wasn't a job scheduled?", "What does the optimization consider?"
4. WHEN the user clicks a sample question THEN THE Scheduling_Help_Assistant SHALL provide a helpful response
5. WHEN the user types a custom question THEN THE Scheduling_Help_Assistant SHALL respond with scheduling-specific knowledge
6. THE Scheduling_Help_Assistant SHALL explain equipment compatibility, geographic batching, capacity management, and priority handling
7. THE System SHALL use the existing AI chat infrastructure with scheduling-specific context
8. THE AI Help panel SHALL be collapsible to not obstruct the main workflow

### Requirement 6: API Endpoints

**User Story:** As a developer, I want well-defined API endpoints for AI scheduling features, so that the frontend can integrate reliably.

#### Acceptance Criteria

1. THE System SHALL provide a POST `/api/v1/schedule/explain` endpoint for schedule explanations
2. THE System SHALL provide a POST `/api/v1/schedule/explain-unassigned` endpoint for unassigned job explanations
3. THE System SHALL provide a POST `/api/v1/schedule/parse-constraints` endpoint for natural language constraint parsing
4. THE System SHALL use the existing POST `/api/v1/ai/chat` endpoint for the scheduling help assistant
5. WHEN API calls fail THEN THE System SHALL return appropriate error codes and messages
6. THE API endpoints SHALL include request validation and rate limiting

### Requirement 7: Integration with Existing Systems

**User Story:** As a developer, I want the new AI features to integrate seamlessly with existing infrastructure, so that we don't duplicate code or break existing functionality.

#### Acceptance Criteria

1. THE AI_Explanation_Service SHALL use the existing AIAgentService infrastructure
2. THE System SHALL use the existing OpenAI/Claude API integration
3. THE System SHALL respect existing rate limiting and usage tracking
4. THE System SHALL log AI interactions to the existing ai_audit_log table
5. THE System SHALL NOT modify the working OR-Tools ScheduleGenerationService
6. THE frontend components SHALL follow existing patterns from AIQueryChat and dashboard components

### Requirement 8: Job Form - Searchable Customer Dropdown

**User Story:** As a business owner, I want to select customers from a searchable dropdown when creating jobs, so that I don't have to copy/paste customer UUIDs.

#### Acceptance Criteria

1. WHEN creating a new job THEN THE System SHALL display a searchable customer dropdown instead of a raw UUID text input
2. THE customer dropdown SHALL support type-ahead search by customer name, phone number, or email
3. THE customer dropdown SHALL display customer name and phone number in the dropdown options for easy identification
4. WHEN a customer is selected THEN THE System SHALL populate the customer_id field with the selected customer's UUID
5. THE customer dropdown SHALL load customers asynchronously with debounced search to prevent excessive API calls
6. THE customer dropdown SHALL display a loading indicator while fetching customer results
7. IF no customers match the search THEN THE System SHALL display "No customers found" message
8. THE customer dropdown SHALL support keyboard navigation (arrow keys, enter to select, escape to close)
9. WHEN editing an existing job THEN THE System SHALL display the current customer's name in the dropdown (pre-selected)
10. THE System SHALL maintain the existing customer_id validation (required field for new jobs)

### Requirement 9: Jobs Ready to Schedule Preview

**User Story:** As a business owner, I want to see which jobs will be included in the schedule before generating, so that I can verify the right jobs are being scheduled and make adjustments if needed.

#### Acceptance Criteria

1. WHEN the user navigates to the Schedule Generation page THEN THE System SHALL display a "Jobs to Schedule" preview section
2. THE preview section SHALL show all jobs with status "approved" or "requested" for the selected date range
3. THE preview section SHALL display job details including: customer name, job type, city/location, priority level, and estimated duration
4. THE preview section SHALL show the total count of jobs to be scheduled
5. THE preview section SHALL allow filtering jobs by job type, priority, or city
6. THE preview section SHALL allow the user to exclude specific jobs from the current schedule generation
7. WHEN a job is excluded THEN THE System SHALL visually indicate the exclusion (e.g., strikethrough, dimmed)
8. THE excluded jobs SHALL NOT be passed to the schedule generation algorithm
9. THE preview section SHALL show a summary: "X jobs selected for scheduling (Y excluded)"
10. WHEN the user clicks "Generate Schedule" THEN THE System SHALL only schedule the non-excluded jobs
11. THE preview section SHALL update automatically when the selected date changes
12. IF no jobs are available for scheduling THEN THE System SHALL display an empty state with helpful message
