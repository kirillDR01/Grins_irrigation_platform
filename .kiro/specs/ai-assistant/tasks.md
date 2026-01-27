# Implementation Plan: AI Assistant Integration (Phase 6)

## Overview

This implementation plan covers the AI Assistant Integration feature for Grin's Irrigation Platform. The feature integrates Pydantic AI with GPT-5-nano to automate scheduling, job categorization, customer communications, business queries, and estimate generation. All AI features follow a human-in-the-loop principle where AI recommends but never executes without explicit user approval.

**CRITICAL VALIDATION RULES:**
- ALL tests must pass before marking any task complete
- ALL quality checks (ruff, mypy, pyright) must pass with zero errors
- ALL frontend components MUST have agent-browser validation
- NO task is complete until validation is confirmed

## Tasks

- [x] 1. Database Schema and Models
  - [x] 1.1 Create Alembic migration for ai_audit_log table
    - Add columns: id, action_type, entity_type, entity_id, ai_recommendation (JSONB), confidence_score, user_decision, user_id, decision_at, request_tokens, response_tokens, estimated_cost_usd, created_at
    - Add indexes on action_type, entity_type, entity_id, created_at, user_decision
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 1.2 Create Alembic migration for ai_usage table
    - Add columns: id, user_id, usage_date, request_count, total_input_tokens, total_output_tokens, estimated_cost_usd, created_at, updated_at
    - Add unique constraint on (user_id, usage_date)
    - _Requirements: 2.1, 2.7, 2.8_
  
  - [x] 1.3 Create Alembic migration for sent_messages table
    - Add columns: id, customer_id, job_id, appointment_id, message_type, message_content, recipient_phone, delivery_status, twilio_sid, error_message, scheduled_for, sent_at, created_by, created_at, updated_at
    - Add foreign keys to customers, jobs, appointments
    - Add indexes on customer_id, job_id, message_type, delivery_status, scheduled_for
    - _Requirements: 7.8, 12.4_

  - [x] 1.4 Create SQLAlchemy models for AI tables
    - Create AIAuditLog model in src/grins_platform/models/ai_audit_log.py
    - Create AIUsage model in src/grins_platform/models/ai_usage.py
    - Create SentMessage model in src/grins_platform/models/sent_message.py
    - _Requirements: 3.1, 2.1, 7.8_
  
  - [x] 1.5 **VALIDATION: Run migrations and verify tables**
    - Run: `uv run alembic upgrade head`
    - Verify all tables created successfully
    - Run: `uv run pytest -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 2. Pydantic Schemas
  - [x] 2.1 Create AI enum types in src/grins_platform/schemas/ai.py
    - AIActionType, AIEntityType, UserDecision, MessageType, DeliveryStatus
    - _Requirements: 3.1, 6.1, 12.3_
  
  - [x] 2.2 Create AI request/response schemas
    - AIChatRequest, AIChatResponse
    - ScheduleGenerateRequest, ScheduleGenerateResponse, GeneratedSchedule, ScheduleDay, StaffAssignment, ScheduledJob, ScheduleWarning, ScheduleSummary
    - JobCategorizationRequest, JobCategorizationResponse, JobCategorization, CategorizationSummary
    - CommunicationDraftRequest, CommunicationDraftResponse, CommunicationDraft
    - EstimateGenerateRequest, EstimateGenerateResponse, SimilarJob, EstimateBreakdown
    - AIUsageResponse, AIAuditLogEntry, AIAuditLogResponse
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_
  
  - [x] 2.3 Create SMS schemas in src/grins_platform/schemas/sms.py
    - SMSSendRequest, SMSSendResponse, SMSWebhookPayload
    - CommunicationsQueueItem, CommunicationsQueueResponse
    - _Requirements: 15.8, 15.9, 15.10_
  
  - [x] 2.4 **VALIDATION: Schema tests pass**
    - Write unit tests for all schemas
    - Run: `uv run pytest src/grins_platform/tests/test_ai_schemas.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 3. Checkpoint - Database and Schemas Complete
  - **MANDATORY VALIDATION:**
  - Run: `uv run alembic upgrade head` - migrations must succeed
  - Run: `uv run pytest -v` - ALL tests must pass (zero failures)
  - Run: `uv run ruff check src/` - ZERO violations
  - Run: `uv run mypy src/` - ZERO errors
  - Run: `uv run pyright src/` - ZERO errors
  - **DO NOT PROCEED** until all validations pass

- [x] 4. Repository Layer
  - [x] 4.1 Create AIAuditLogRepository
    - Implement create, get_by_id, update_decision, list_with_filters methods
    - _Requirements: 3.1, 3.2, 3.7_
  
  - [x] 4.2 Create AIUsageRepository
    - Implement get_or_create, increment, get_monthly_cost methods
    - _Requirements: 2.1, 2.7, 2.8_
  
  - [x] 4.3 Create SentMessageRepository
    - Implement create, update, get_queue, get_by_customer_and_type methods
    - _Requirements: 7.8, 7.9, 7.10_
  
  - [x] 4.4 **VALIDATION: Repository tests pass**
    - Write unit tests for all repository methods
    - Write integration tests with real database
    - Run: `uv run pytest src/grins_platform/tests/test_ai_repositories.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 5. Core AI Services
  - [x] 5.1 Create RateLimitService in src/grins_platform/services/ai/rate_limiter.py
    - Implement check_limit method (100 requests/day)
    - Implement record_usage method with token and cost tracking
    - Implement get_usage method for statistics
    - Add LoggerMixin for structured logging
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10_
  
  - [x] 5.2 Write property test for rate limit enforcement
    - **Property 3: Rate Limit Enforcement**
    - Test that requests >= 100 are rejected, < 100 are allowed
    - **Validates: Requirements 2.1, 2.2**
    - Run: `uv run pytest -v -k "rate_limit"` - test MUST pass
  
  - [x] 5.3 Create AuditService in src/grins_platform/services/ai/audit.py
    - Implement log_recommendation method
    - Implement record_decision method
    - Implement query_logs method with filters
    - Add LoggerMixin for structured logging
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_
  
  - [x] 5.4 Write property tests for audit logging
    - **Property 4: Audit Log Completeness for Recommendations**
    - **Property 5: Audit Log Completeness for Decisions**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    - Run: `uv run pytest -v -k "audit"` - ALL tests MUST pass
  
  - [x] 5.5 Create ContextBuilder in src/grins_platform/services/ai/context/builder.py
    - Implement build method with token budget management
    - Implement _format_customer with PII removal (use placeholders)
    - Implement _format_jobs, _format_services, _format_staff
    - Implement _get_business_rules for static context
    - Implement _estimate_tokens for token counting
    - _Requirements: 1.3, 1.4, 1.6, 1.7, 13.5, 13.6, 13.7_

  - [x] 5.6 Write property tests for context builder
    - **Property 1: PII Protection**
    - **Property 2: Context Token Limit Enforcement**
    - Test that PII is never in context, token limit is enforced
    - **Validates: Requirements 1.3, 1.6, 1.7, 13.5**
    - Run: `uv run pytest -v -k "context"` - ALL tests MUST pass
  
  - [x] 5.7 **VALIDATION: All core service tests pass**
    - Run: `uv run pytest src/grins_platform/tests/test_ai_services.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 6. Checkpoint - Core Services Complete
  - **CHECKPOINT PASSED - CONTINUING EXECUTION**
  - Run: `uv run pytest -v` - ALL tests must pass (zero failures)
  - Run: `uv run ruff check src/` - ZERO violations
  - Run: `uv run mypy src/` - ZERO errors
  - Run: `uv run pyright src/` - ZERO errors
  - Verify property tests for rate limiting, audit, and context builder all pass

- [x] 7. Pydantic AI Agent Setup
  - [x] 7.1 Create system prompts in src/grins_platform/services/ai/prompts/
    - Create system.py with SYSTEM_PROMPT
    - Create scheduling.py with SCHEDULE_GENERATION_PROMPT
    - Create categorization.py with CATEGORIZATION_PROMPT
    - Create communication.py with message templates
    - Create estimates.py with ESTIMATE_PROMPT
    - _Requirements: 1.1, 4.1, 5.1, 6.1, 9.1_
  
  - [x] 7.2 Create AIAgentService in src/grins_platform/services/ai/agent.py
    - Initialize Pydantic AI agent with GPT-5-nano model
    - Configure system prompt and tools
    - Implement chat method with streaming support
    - Implement error handling with graceful degradation
    - Add LoggerMixin for structured logging
    - _Requirements: 1.1, 1.2, 1.5, 1.8, 1.9, 1.10, 1.11, 1.12_

  - [x] 7.3 Write unit tests for AIAgentService
    - Test initialization with correct model
    - Test error handling and graceful degradation
    - Test streaming response handling
    - _Requirements: 1.1, 14.1, 14.2, 14.3, 14.4_
    - Run: `uv run pytest -v -k "agent"` - ALL tests MUST pass

- [x] 8. AI Tools Implementation
  - [x] 8.1 Create scheduling tools in src/grins_platform/services/ai/tools/scheduling.py
    - Implement get_pending_jobs tool
    - Implement get_staff_availability tool
    - Implement generate_schedule tool with batching logic
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_
  
  - [x] 8.2 Write property tests for schedule generation
    - **Property 6: Schedule Location Batching**
    - **Property 7: Schedule Job Type Batching**
    - **Validates: Requirements 4.2, 4.3**
    - Run: `uv run pytest -v -k "schedule"` - ALL tests MUST pass
  
  - [x] 8.3 Create categorization tools in src/grins_platform/services/ai/tools/categorization.py
    - Implement categorize_jobs tool with confidence scoring
    - Implement threshold routing (>=85% ready, <85% review)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12, 5.13, 5.14_
  
  - [x] 8.4 Write property test for confidence threshold routing
    - **Property 9: Confidence Threshold Routing**
    - **Validates: Requirements 5.5, 5.6**
    - Run: `uv run pytest -v -k "categorization"` - ALL tests MUST pass
  
  - [x] 8.5 Create communication tools in src/grins_platform/services/ai/tools/communication.py
    - Implement draft_message tool for various message types
    - Implement message templates with placeholder support
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [x] 8.6 Create query tools in src/grins_platform/services/ai/tools/queries.py
    - Implement query_customers tool
    - Implement query_jobs tool
    - Implement query_revenue tool
    - Implement query_staff tool
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
  
  - [x] 8.7 Create estimate tools in src/grins_platform/services/ai/tools/estimates.py
    - Implement calculate_estimate tool
    - Implement find_similar_jobs tool
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7_
  
  - [x] 8.8 **VALIDATION: All AI tools tests pass**
    - Run: `uv run pytest src/grins_platform/tests/test_ai_tools.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 9. Checkpoint - AI Tools Complete
  - **CHECKPOINT PASSED - CONTINUING EXECUTION**
  - Run: `uv run pytest -v` - ALL tests must pass (zero failures)
  - Run: `uv run ruff check src/` - ZERO violations
  - Run: `uv run mypy src/` - ZERO errors
  - Run: `uv run pyright src/` - ZERO errors
  - Verify all property tests pass (schedule batching, categorization threshold)
  - **DO NOT PROCEED** until all validations pass

- [x] 10. External Service Integrations
  - [x] 10.1 Create SMSService in src/grins_platform/services/sms_service.py
    - Initialize Twilio client with credentials from environment
    - Implement send_message method with E.164 formatting
    - Implement handle_webhook for incoming SMS
    - Implement opt-in validation
    - Add LoggerMixin for structured logging
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10_

  - [x] 10.2 Write property test for SMS opt-in enforcement
    - **Property 13: SMS Opt-in Enforcement**
    - **Validates: Requirements 12.8, 12.9**
    - Run: `uv run pytest -v -k "sms_opt_in"` - test MUST pass
  
  - [x] 10.3 **VALIDATION: SMS service tests pass**
    - Run: `uv run pytest src/grins_platform/tests/test_sms_service.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 11. API Endpoints
  - [x] 11.1 Create AI API endpoints in src/grins_platform/api/v1/ai.py
    - POST /api/v1/ai/chat with streaming SSE response
    - POST /api/v1/ai/schedule/generate
    - POST /api/v1/ai/jobs/categorize
    - POST /api/v1/ai/communication/draft
    - POST /api/v1/ai/estimate/generate
    - GET /api/v1/ai/usage
    - GET /api/v1/ai/audit with query filters
    - POST /api/v1/ai/audit/{id}/decision
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_
  
  - [x] 11.2 Write property test for human approval requirement
    - **Property 10: Human Approval Required for Actions**
    - **Validates: Requirements 6.10**
    - Run: `uv run pytest -v -k "human_approval"` - test MUST pass
  
  - [x] 11.3 Create SMS API endpoints in src/grins_platform/api/v1/sms.py
    - POST /api/v1/sms/send
    - POST /api/v1/sms/webhook (Twilio webhook)
    - GET /api/v1/communications/queue
    - POST /api/v1/communications/send-bulk
    - DELETE /api/v1/communications/{id}
    - _Requirements: 15.8, 15.9, 15.10_

  - [x] 11.4 Write property test for duplicate message prevention
    - **Property 11: Duplicate Message Prevention**
    - **Validates: Requirements 7.7**
    - Run: `uv run pytest -v -k "duplicate_message"` - test MUST pass
  
  - [x] 11.5 Register all new routers in main.py
    - Add ai_router, sms_router
    - _Requirements: 15.1-15.10_
  
  - [x] 11.6 **VALIDATION: All API endpoint tests pass**
    - Run: `uv run pytest src/grins_platform/tests/test_ai_api.py -v` - ALL tests must pass
    - Run: `uv run pytest src/grins_platform/tests/test_sms_api.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [x] 12. Checkpoint - Backend API Complete
  - **PASSED: All quality checks pass, all API tests pass**
  - Ruff: All checks passed!
  - MyPy: Success: no issues found in 170 source files
  - Pyright: 0 errors
  - AI API tests: 14/14 passed
  - SMS API tests: 10/10 passed

- [x] 13. Session Management
  - [x] 13.1 Create ChatSession class for session history management
    - Implement add_message with 50 message limit
    - Implement clear method
    - Implement message count tracking
    - _Requirements: 8.9, 13.1, 13.2, 13.3, 13.4, 13.8_
  
  - [x] 13.2 Write property test for session history limit
    - **Property 12: Session History Limit**
    - **Validates: Requirements 8.9, 13.2**
    - Run: `uv run pytest -v -k "session_history"` - test MUST pass

- [ ] 14. Input Validation and Security
  - [x] 14.1 Create input sanitization utilities
    - Implement sanitize_user_input function
    - Implement prompt injection detection
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_
  
  - [x] 14.2 Write property test for input sanitization
    - **Property 14: Input Sanitization**
    - **Validates: Requirements 17.2**
    - Run: `uv run pytest -v -k "input_sanitization"` - test MUST pass
  
  - [x] 14.3 Implement Twilio webhook signature validation
    - _Requirements: 17.9_
  
  - [x] 14.4 **VALIDATION: All security tests pass**
    - Run: `uv run pytest src/grins_platform/tests/test_ai_security.py -v` - ALL tests must pass
    - Run: `uv run ruff check src/ && uv run mypy src/ && uv run pyright src/` - ZERO errors required

- [ ] 15. Checkpoint - Backend Complete
  - **MANDATORY VALIDATION:**
  - Run full backend test suite: `uv run pytest -v --cov=src/grins_platform`
  - Run: `uv run ruff check src/` - ZERO violations
  - Run: `uv run mypy src/` - ZERO errors
  - Run: `uv run pyright src/` - ZERO errors
  - Verify ALL property tests pass
  - **DO NOT PROCEED** until all validations pass

- [ ] 16. Frontend - AI Feature Module Setup
  - [ ] 16.1 Create AI feature directory structure
    - Create frontend/src/features/ai/components/
    - Create frontend/src/features/ai/hooks/
    - Create frontend/src/features/ai/api/
    - Create frontend/src/features/ai/types/
    - _Requirements: 16.1_
  
  - [ ] 16.2 Create AI TypeScript types in frontend/src/features/ai/types/index.ts
    - Define all AI request/response types matching backend schemas
    - _Requirements: 16.1_
  
  - [ ] 16.3 Create AI API client in frontend/src/features/ai/api/aiApi.ts
    - Implement chat, generateSchedule, categorizeJobs, draftCommunication, generateEstimate
    - Implement streaming support for chat endpoint
    - _Requirements: 16.1_
  
  - [ ] 16.4 **VALIDATION: Frontend setup compiles**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors

- [ ] 17. Frontend - Shared AI Components
  - [ ] 17.1 Create AILoadingState component
    - Display loading spinner with "AI is thinking..." message
    - Add data-testid="ai-loading-state"
    - _Requirements: 16.8_
  
  - [ ] 17.2 Create AIErrorState component
    - Display error message with retry button
    - Show manual fallback options
    - Add data-testid="ai-error-state"
    - _Requirements: 16.9_

  - [ ] 17.3 Create AIStreamingText component
    - Display streaming text with typing effect
    - Add data-testid="ai-streaming-text"
    - _Requirements: 16.10_
  
  - [ ] 17.4 **VALIDATION: Shared components render correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173`
    - `agent-browser is visible "[data-testid='ai-loading-state']"` - must return true when loading
    - `agent-browser is visible "[data-testid='ai-error-state']"` - must return true on error

- [ ] 18. Frontend - AIQueryChat Component
  - [ ] 18.1 Create AIQueryChat component
    - Implement chat input with submit button
    - Display message history with user/AI distinction
    - Implement streaming response display
    - Add session message count display
    - Add Clear Chat button
    - Add example query suggestions
    - Add data-testid attributes for all interactive elements
    - _Requirements: 8.1, 8.9, 8.10, 8.11, 8.12, 16.1_
  
  - [ ] 18.2 Create useAIChat hook
    - Manage chat state and session history
    - Handle streaming responses
    - Implement error handling
    - _Requirements: 8.1, 8.9_

  - [ ] 18.3 **VALIDATION: AIQueryChat renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173` (navigate to page with chat)
    - `agent-browser is visible "[data-testid='ai-chat-input']"` - must return true
    - `agent-browser is visible "[data-testid='ai-chat-submit']"` - must return true
    - `agent-browser fill "[data-testid='ai-chat-input']" "How many jobs today?"`
    - `agent-browser click "[data-testid='ai-chat-submit']"`
    - `agent-browser wait --load networkidle`
    - `agent-browser is visible "[data-testid='ai-chat-response']"` - must return true
    - `agent-browser click "[data-testid='ai-chat-clear']"`
    - Verify chat clears successfully
    - _Requirements: 19.1, 19.8, 19.9, 19.10, 19.11_

- [ ] 19. Frontend - AIScheduleGenerator Component
  - [ ] 19.1 Create AIScheduleGenerator component
    - Implement date range selector
    - Implement staff filter checkboxes
    - Display generated schedule by day with staff assignments
    - Display warnings (equipment, conflicts)
    - Add Accept Schedule, Modify, Regenerate buttons
    - Display AI explanation
    - Add data-testid attributes for all interactive elements
    - _Requirements: 4.10, 4.11, 4.12, 4.13, 4.14, 16.2_
  
  - [ ] 19.2 Create useAISchedule hook
    - Manage schedule generation state
    - Handle loading and error states
    - _Requirements: 4.10_

  - [ ] 19.3 **VALIDATION: AIScheduleGenerator renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173/schedule/generate`
    - `agent-browser is visible "[data-testid='ai-schedule-generator']"` - must return true
    - `agent-browser is visible "[data-testid='date-range-selector']"` - must return true
    - `agent-browser is visible "[data-testid='staff-filter']"` - must return true
    - `agent-browser click "[data-testid='generate-schedule-btn']"`
    - `agent-browser wait --load networkidle`
    - `agent-browser is visible "[data-testid='generated-schedule']"` - must return true
    - `agent-browser is visible "[data-testid='accept-schedule-btn']"` - must return true
    - `agent-browser is visible "[data-testid='regenerate-btn']"` - must return true
    - _Requirements: 19.2, 19.8, 19.9, 19.10_

- [ ] 20. Frontend - AICategorization Component
  - [ ] 20.1 Create AICategorization component
    - Display categorization results grouped by category
    - Show confidence scores and suggested pricing
    - Add Approve All Ready, Review Individually, Bulk Actions buttons
    - Display AI notes for each categorization
    - Add data-testid attributes for all interactive elements
    - _Requirements: 5.12, 5.13, 5.14, 16.3_
  
  - [ ] 20.2 Create useAICategorize hook
    - Manage categorization state
    - Handle bulk approval actions
    - _Requirements: 5.12_

  - [ ] 20.3 **VALIDATION: AICategorization renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173/jobs` (navigate to jobs page)
    - `agent-browser is visible "[data-testid='ai-categorization']"` - must return true
    - `agent-browser is visible "[data-testid='categorization-results']"` - must return true
    - `agent-browser is visible "[data-testid='confidence-score']"` - must return true
    - `agent-browser is visible "[data-testid='approve-all-btn']"` - must return true
    - `agent-browser click "[data-testid='approve-all-btn']"`
    - Verify approval action completes
    - _Requirements: 19.3, 19.8, 19.12_

- [ ] 21. Frontend - AICommunicationDrafts Component
  - [ ] 21.1 Create AICommunicationDrafts component
    - Display draft message with recipient info
    - Add Send Now, Edit, Schedule for Later buttons
    - Show AI notes for slow payers
    - Add data-testid attributes for all interactive elements
    - _Requirements: 6.9, 6.10, 6.11, 6.12, 16.4_
  
  - [ ] 21.2 Create useAICommunication hook
    - Manage communication draft state
    - Handle send and schedule actions
    - _Requirements: 6.9_

  - [ ] 21.3 **VALIDATION: AICommunicationDrafts renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173/customers/1` (customer detail page)
    - `agent-browser is visible "[data-testid='ai-communication-drafts']"` - must return true
    - `agent-browser is visible "[data-testid='draft-message']"` - must return true
    - `agent-browser is visible "[data-testid='send-now-btn']"` - must return true
    - `agent-browser is visible "[data-testid='edit-draft-btn']"` - must return true
    - `agent-browser is visible "[data-testid='schedule-later-btn']"` - must return true
    - _Requirements: 19.4, 19.8, 19.12_

- [ ] 22. Frontend - AIEstimateGenerator Component
  - [ ] 22.1 Create AIEstimateGenerator component
    - Display estimate analysis with zone count
    - Show similar completed jobs for reference
    - Display price breakdown (materials, labor, equipment, margin)
    - Add Generate Estimate PDF, Schedule Site Visit, Adjust Quote buttons
    - Show AI recommendation for site visit
    - Add data-testid attributes for all interactive elements
    - _Requirements: 9.7, 9.8, 9.9, 9.10, 9.11, 16.5_
  
  - [ ] 22.2 Create useAIEstimate hook
    - Manage estimate generation state
    - Handle quote adjustment
    - _Requirements: 9.7_

  - [ ] 22.3 **VALIDATION: AIEstimateGenerator renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173/jobs/1` (job detail page)
    - `agent-browser is visible "[data-testid='ai-estimate-generator']"` - must return true
    - `agent-browser is visible "[data-testid='estimate-breakdown']"` - must return true
    - `agent-browser is visible "[data-testid='similar-jobs']"` - must return true
    - `agent-browser is visible "[data-testid='generate-pdf-btn']"` - must return true
    - `agent-browser is visible "[data-testid='adjust-quote-btn']"` - must return true
    - _Requirements: 19.5, 19.8, 19.12_

- [ ] 23. Frontend - MorningBriefing Component
  - [ ] 23.1 Create MorningBriefing component
    - Display personalized greeting based on time of day
    - Show overnight requests summary with categorization counts
    - Show today's schedule summary by staff
    - Highlight unconfirmed appointments
    - Show pending communications count
    - Show outstanding invoice totals by aging bucket
    - Add quick action links
    - Add data-testid attributes for all interactive elements
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 16.6_

  - [ ] 23.2 **VALIDATION: MorningBriefing renders correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173`
    - `agent-browser is visible "[data-testid='morning-briefing']"` - must return true
    - `agent-browser is visible "[data-testid='greeting']"` - must return true
    - `agent-browser is visible "[data-testid='overnight-requests']"` - must return true
    - `agent-browser is visible "[data-testid='today-schedule']"` - must return true
    - `agent-browser is visible "[data-testid='pending-communications']"` - must return true
    - `agent-browser is visible "[data-testid='quick-actions']"` - must return true
    - _Requirements: 19.6, 19.8_

- [ ] 24. Frontend - CommunicationsQueue Component
  - [ ] 24.1 Create CommunicationsQueue component
    - Display messages grouped by status (Pending, Scheduled, Sent Today, Failed)
    - Add Send All and Review bulk actions for pending
    - Add Pause All for scheduled
    - Show sent message details with timestamps
    - Add Retry for failed messages
    - Add filtering by message type
    - Add search by customer name/phone
    - Add data-testid attributes for all interactive elements
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.9, 7.10, 16.7_
  
  - [ ] 24.2 Create useCommunications hook
    - Manage queue state
    - Handle bulk send and retry actions
    - _Requirements: 7.1_

  - [ ] 24.3 **VALIDATION: CommunicationsQueue renders and functions correctly**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - Run: `cd frontend && npm test` - ALL tests must pass
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173` (dashboard with queue)
    - `agent-browser is visible "[data-testid='communications-queue']"` - must return true
    - `agent-browser is visible "[data-testid='pending-messages']"` - must return true
    - `agent-browser is visible "[data-testid='scheduled-messages']"` - must return true
    - `agent-browser is visible "[data-testid='sent-messages']"` - must return true
    - `agent-browser is visible "[data-testid='send-all-btn']"` - must return true
    - `agent-browser is visible "[data-testid='message-filter']"` - must return true
    - `agent-browser fill "[data-testid='message-search']" "John"`
    - Verify search filters results
    - _Requirements: 19.7, 19.8, 19.12_

- [ ] 25. Checkpoint - Frontend Components Complete
  - **MANDATORY VALIDATION:**
  - Run: `cd frontend && npm run lint` - ZERO errors
  - Run: `cd frontend && npm run typecheck` - ZERO errors
  - Run: `cd frontend && npm test` - ALL tests must pass
  - **AGENT-BROWSER FULL VALIDATION:**
  - Verify ALL components have data-testid attributes
  - Verify ALL interactive elements are clickable
  - Verify ALL forms submit correctly
  - **DO NOT PROCEED** until all validations pass

- [ ] 26. Dashboard Integration
  - [ ] 26.1 Add MorningBriefing to Dashboard page
    - Position at top of dashboard
    - _Requirements: 10.1_
  
  - [ ] 26.2 Add AIQueryChat to Dashboard page
    - Position in sidebar or dedicated section
    - _Requirements: 8.1_
  
  - [ ] 26.3 Add CommunicationsQueue to Dashboard page
    - Position below MorningBriefing
    - _Requirements: 7.1_
  
  - [ ] 26.4 **VALIDATION: Dashboard with AI components**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173`
    - `agent-browser is visible "[data-testid='morning-briefing']"` - must return true
    - `agent-browser is visible "[data-testid='ai-chat-input']"` - must return true
    - `agent-browser is visible "[data-testid='communications-queue']"` - must return true
    - `agent-browser snapshot -i` - capture interactive elements
    - Verify all AI components render on dashboard
    - _Requirements: 19.1, 19.6, 19.7_

- [ ] 27. Feature Page Integrations
  - [ ] 27.1 Add AIScheduleGenerator to Schedule Generation page
    - Integrate with existing schedule page
    - _Requirements: 4.10_
  
  - [ ] 27.2 Add AICategorization to Job Requests page
    - Display for uncategorized jobs
    - _Requirements: 5.12_

  - [ ] 27.3 Add AICommunicationDrafts to Customer Detail page
    - Show contextual drafts for customer
    - _Requirements: 6.9_
  
  - [ ] 27.4 Add AICommunicationDrafts to Job Detail page
    - Show contextual drafts for job
    - _Requirements: 6.9_
  
  - [ ] 27.5 Add AIEstimateGenerator to Job Detail page
    - Show for jobs needing estimates
    - _Requirements: 9.7_
  
  - [ ] 27.6 **VALIDATION: All feature page integrations**
    - Run: `cd frontend && npm run typecheck` - ZERO errors
    - Run: `cd frontend && npm run lint` - ZERO errors
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - `agent-browser open http://localhost:5173/schedule/generate`
    - `agent-browser is visible "[data-testid='ai-schedule-generator']"` - must return true
    - `agent-browser open http://localhost:5173/jobs`
    - `agent-browser is visible "[data-testid='ai-categorization']"` - must return true
    - `agent-browser open http://localhost:5173/customers/1`
    - `agent-browser is visible "[data-testid='ai-communication-drafts']"` - must return true
    - `agent-browser open http://localhost:5173/jobs/1`
    - `agent-browser is visible "[data-testid='ai-estimate-generator']"` - must return true

- [ ] 28. Checkpoint - Frontend Integration Complete
  - **MANDATORY VALIDATION:**
  - Run full frontend test suite: `cd frontend && npm test`
  - Run: `cd frontend && npm run lint` - ZERO errors
  - Run: `cd frontend && npm run typecheck` - ZERO errors
  - **AGENT-BROWSER FULL VALIDATION:**
  - Test complete user journeys through all AI features
  - **DO NOT PROCEED** until all validations pass

- [ ] 29. Property Test for Data-testid Coverage
  - [ ] 29.1 Write property test for data-testid attribute coverage
    - **Property 15: Data-testid Attribute Coverage**
    - Verify all AI components have required data-testid attributes
    - **Validates: Requirements 19.8**
    - Run: `uv run pytest -v -k "testid_coverage"` - test MUST pass

- [ ] 30. End-to-End Validation Scripts
  - [ ] 30.1 Create validation script for AI Chat user journey
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - Test chat input, response, and session management
    - Test clear chat functionality
    - Test example query suggestions
    - _Requirements: 19.13, 19.14_
  
  - [ ] 30.2 Create validation script for Schedule Generation user journey
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - Test date selection, generation, and approval flow
    - Test regenerate functionality
    - Test modify schedule
    - _Requirements: 19.13, 19.14_
  
  - [ ] 30.3 Create validation script for Job Categorization user journey
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - Test categorization display and bulk approval
    - Test individual review
    - Test confidence score display
    - _Requirements: 19.13, 19.14_
  
  - [ ] 30.4 Create validation script for Communications user journey
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - Test draft generation, editing, and sending
    - Test schedule for later
    - Test bulk send
    - _Requirements: 19.13, 19.14_

  - [ ] 30.5 Create validation script for Estimate Generation user journey
    - **AGENT-BROWSER VALIDATION (MANDATORY):**
    - Test estimate display and adjustment
    - Test similar jobs reference
    - Test PDF generation trigger
    - _Requirements: 19.13, 19.14_

- [ ] 31. Final Checkpoint - All Tests Pass
  - **MANDATORY VALIDATION - ALL MUST PASS:**
  - Run full backend test suite: `uv run pytest -v --cov=src/grins_platform`
  - Run: `uv run ruff check src/` - ZERO violations
  - Run: `uv run mypy src/` - ZERO errors
  - Run: `uv run pyright src/` - ZERO errors
  - Run full frontend test suite: `cd frontend && npm test`
  - Run: `cd frontend && npm run lint` - ZERO errors
  - Run: `cd frontend && npm run typecheck` - ZERO errors
  - **AGENT-BROWSER FULL E2E VALIDATION:**
  - Run all validation scripts from Task 30
  - Verify ALL user journeys complete successfully
  - **DO NOT PROCEED** until all validations pass

- [ ] 32. Documentation
  - [ ] 32.1 Update API documentation with new AI endpoints
  - [ ] 32.2 Create AI feature usage guide for Viktor
  - [ ] 32.3 Document environment variables for Twilio and OpenAI

## Notes

- **Weather API tasks removed** - OpenWeatherMap integration skipped (no API key)
- All tasks including property-based tests are required for task completion
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation with STRICT requirements
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- **AGENT-BROWSER validations are MANDATORY for ALL UI components**
- **NO task is complete until ALL validations pass**
