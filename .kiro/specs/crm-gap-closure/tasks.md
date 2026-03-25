# Implementation Plan: CRM Gap Closure

## Overview

This plan implements all 87 requirements from the CRM Gap Closure spec across 9 phases: dependency setup, foundation infrastructure, data layer, service layer, API layer, frontend, background jobs, testing, and agreement flow regression. All tasks are required. The architecture follows Vertical Slice Architecture (VSA) with Python/FastAPI backend and React/TypeScript frontend.

**Environment Constraint:** ALL work in this plan MUST be performed exclusively on the `dev` branch and in the development environment. No changes to the `main` branch or production deployment until the full plan is implemented, all 87 requirements are verified, all tests pass, and explicit Admin approval is given to merge. The `main` branch remains untouched throughout. Every task, migration, dependency install, and test execution happens on `dev` only.

**Preservation Constraint:** The service agreement flow (ServiceAgreement, ServiceAgreementTier, AgreementJob, Stripe checkout/webhook, onboarding consent, job generation) is OFF-LIMITS and must not be modified.

## Tasks

- [ ] 0. Dependency Setup: Install all new packages, configure infrastructure services, and add environment variables
  - [x] 0.1 Add new Python backend dependencies to `pyproject.toml`
    - `redis>=5.0.0` — Redis client for rate limiting (Req 69) and staff location caching (Req 41)
    - `slowapi>=0.1.9` — Rate limiting middleware for FastAPI (Req 69)
    - `boto3>=1.34.0` — AWS S3-compatible object storage client for file uploads (Req 9, 15, 49, 60, 77, 80)
    - `weasyprint>=62.0` — HTML-to-PDF generation for invoices and estimates (Req 80)
    - `python-magic>=0.4.27` — File type validation via magic bytes (Req 77)
    - `Pillow>=10.0.0` — Image processing for EXIF stripping and thumbnail generation (Req 77)
    - `plaid-python>=22.0.0` — Plaid API client for banking integration (Req 62)
    - `qrcode[pil]>=7.4` — QR code generation for marketing campaigns (Req 65)
    - Run `uv sync` to install all new dependencies and verify no version conflicts
    - _Requirements: 9.2, 15.2, 41.1, 49.5, 60.1, 62.2, 65.1, 69.1, 77.1, 77.4, 80.2_

  - [x] 0.2 Add new frontend npm dependencies to `frontend/package.json`
    - `@excalidraw/excalidraw` — Diagram builder for estimate property diagrams (Req 50)
    - `signature_pad` — Canvas-based electronic signature for contract signing portal (Req 16)
    - `fast-check` — Property-based testing library for frontend tests (Req 67)
    - `qrcode.react` — QR code rendering component for marketing dashboard (Req 65)
    - Run `npm install` to install all new dependencies and verify no version conflicts
    - _Requirements: 16.4, 50.1, 65.2, 67.1_

  - [x] 0.3 Enable Redis in Docker infrastructure
    - Uncomment the Redis service block in `docker-compose.yml` (lines 56-68): image `redis:7-alpine`, port 6379, volume `redis_data`, healthcheck via `redis-cli ping`
    - Uncomment `redis_data` volume in `docker-compose.yml` (line 77)
    - Add equivalent Redis service to `docker-compose.dev.yml` if not already present
    - Verify Redis starts and responds to `redis-cli ping` via `docker compose up redis -d && docker compose exec redis redis-cli ping`
    - _Requirements: 41.1, 69.1_

  - [x] 0.4 Add new environment variables to `.env.example` and document in README
    - **Redis:** `REDIS_URL=redis://localhost:6379/0`
    - **S3-compatible storage:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME=grins-platform-files`, `S3_ENDPOINT_URL` (optional, for MinIO local dev), `S3_REGION=us-east-1`
    - **Plaid:** `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV=sandbox` (sandbox for dev, production for live)
    - **Vapi:** `VAPI_API_KEY`, `VAPI_WEBHOOK_SECRET`
    - **WeasyPrint:** No env var needed (library only), but ensure system dependencies are available (see 0.5)
    - Add all variables to `.env.example` with placeholder values and comments
    - _Requirements: 41.1, 44.1, 62.2, 69.1, 77.1, 80.2_

  - [x] 0.5 Update Dockerfile with system dependencies for new libraries
    - Add `libmagic1` — required by python-magic for file type detection
    - Add `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi-dev`, `libcairo2` — required by WeasyPrint for PDF rendering
    - Add these to the `apt-get install` layer in the Dockerfile, before the Python dependency install step
    - Rebuild Docker image and verify `python -c "import magic; import weasyprint"` succeeds inside container
    - _Requirements: 77.1, 80.2_

  - [x] 0.6 Create S3 bucket and verify connectivity
    - For local development: set up MinIO container in docker-compose.dev.yml (image `minio/minio`, port 9000/9001, volume `minio_data`), create bucket `grins-platform-files` with prefix directories: `customer-photos/`, `lead-attachments/`, `media-library/`, `receipts/`, `invoices/`
    - For production: create AWS S3 bucket `grins-platform-files` with private ACL, enable versioning, configure lifecycle rule (archive to Glacier after 1 year)
    - Write and run a quick verification script: upload a test file to S3, generate pre-signed URL, download via URL, delete file — all must succeed
    - _Requirements: 9.2, 15.2, 49.5, 77.1, 80.2_

  - [x] 0.7 Verify all dependencies work together
    - Run full backend test suite (`uv run pytest`) to confirm no existing tests break with new dependencies
    - Run full frontend test suite (`cd frontend && npm test`) to confirm no existing tests break
    - Run `docker compose up --build` and verify all services start (app, postgres, redis)
    - Run `uv run python -c "import redis, boto3, magic, weasyprint, PIL, plaid, qrcode; print('All imports OK')"` inside the app container
    - _Requirements: 68.6 (agreement flow regression baseline before any changes)_

- [x] 0.8 Checkpoint — Dependencies complete
  - Ensure all new packages install cleanly, Docker builds successfully, Redis responds, S3 connectivity verified, existing tests still pass. Ask the user if questions arise.

- [ ] 1. Foundation: Enums, Security Middleware, and Database Migrations
  - [x] 1.1 Add new enum types and update existing enums in `src/grins_platform/models/enums.py`
    - Add: CommunicationChannel, CommunicationDirection, AttachmentType, EstimateStatus, ActionTag, ExpenseCategory, CampaignType, CampaignStatus, MediaType, BreakType, NotificationType, FollowUpStatus
    - Update AppointmentStatus: add PENDING, EN_ROUTE, NO_SHOW
    - Update VALID_MESSAGE_TYPES: add lead_confirmation, estimate_sent, contract_sent, review_request, campaign
    - _Requirements: 4.4, 13.1, 15.1, 35.2, 42.3, 45.1, 48.1, 49.1, 51.1, 53.1, 54.1, 64.1, 74.1, 79.1, 79.2, 81.4_

  - [x] 1.2 Create security middleware: rate limiting, security headers, request size limits
    - Create `src/grins_platform/middleware/rate_limit.py` — Redis-backed sliding window via slowapi with per-endpoint limits (auth: 5/min, public: 10/min, authenticated: 200/min, uploads: 20/min, portal: 20/min/token)
    - Create `src/grins_platform/middleware/security_headers.py` — X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, CSP, HSTS (prod only)
    - Create `src/grins_platform/middleware/request_size.py` — 10MB default, 50MB for upload paths; returns 413 on exceed
    - Register all middleware in `main.py`
    - _Requirements: 69.1, 69.2, 69.3, 69.4, 70.1, 70.2, 70.3, 73.1, 73.2, 73.3, 73.4_

  - [x] 1.3 Implement PII masking structlog processor
    - Create `src/grins_platform/services/pii_masking.py` — structlog processor that masks phone (last 4), email (first char + domain), address (fully masked), card numbers (REDACTED)
    - Register processor globally in `src/grins_platform/logging.py`
    - _Requirements: 76.1, 76.2, 76.3, 76.4_

  - [x] 1.4 Implement secure token storage (httpOnly cookies) and JWT validation
    - Update auth endpoints to set JWT via `Set-Cookie: HttpOnly; Secure; SameSite=Lax; Path=/`
    - Add JWT secret validation at startup: reject default secret in production, enforce ≥32 chars
    - Add `JWT_PREVIOUS_SECRET_KEY` support for key rotation with 24h grace period
    - Update frontend API client to use `credentials: 'include'`, remove localStorage token handling
    - Add frontend 401 interceptor: attempt silent refresh → retry → redirect to `/login?reason=session_expired` on failure
    - Add frontend 429 interceptor: parse `Retry-After` header, show warning toast "Too many requests. Please wait {retry_after} seconds and try again.", do NOT auto-retry (Req 85)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 71.1, 71.2, 71.3, 71.4, 71.5, 72.1, 72.2, 72.3, 72.4, 85.1, 85.2, 85.3, 85.4, 85.5_

  - [x] 1.5 Implement secure file upload pipeline in PhotoService
    - Create/update `src/grins_platform/services/photo_service.py` with: magic byte validation (python-magic), EXIF stripping (Pillow), UUID-based S3 keys, pre-signed URL generation (1hr expiry), per-customer quota tracking (500MB)
    - Support upload for customer photos (JPEG/PNG/HEIC, 10MB), lead attachments (PDF/DOCX/JPEG/PNG, 25MB), media library (JPEG/PNG/HEIC/MP4/MOV, 50MB), receipts (JPEG/PNG/PDF, 10MB)
    - _Requirements: 9.2, 9.6, 15.2, 49.5, 75.3, 77.1, 77.2, 77.3, 77.4, 77.5, 77.6_

  - [x] 1.6 Write unit tests for security middleware and PII masking
    - Test rate limit returns 429 after threshold (P65)
    - Test all security headers present on responses (P66)
    - Test httpOnly cookie flags on login response (P67)
    - Test JWT startup validation rejects default secret in production (P68)
    - Test key rotation accepts previous key within grace period (P68)
    - Test request size limit returns 413 for oversized payloads (P69)
    - Test PII masking processor masks phone, email, address fields (P72)
    - Test magic byte validation rejects mismatched files (P11)
    - Test EXIF stripping removes GPS data (P73)
    - Test pre-signed URL expiry (P74)
    - Test input validation rejects oversized strings, invalid UUIDs, script tags (P71)
    - **Property 11: File upload validation rejects invalid files**
    - **Validates: Requirements 9.2, 15.1, 49.5, 75.3, 77.1**
    - **Property 65: Rate limiting enforces thresholds**
    - **Validates: Requirements 69.1, 69.2, 69.3**
    - **Property 66: Security headers present on all responses**
    - **Validates: Requirements 70.1**
    - **Property 67: Secure token storage in httpOnly cookies**
    - **Validates: Requirements 71.1, 71.2**
    - **Property 68: JWT secret validation at startup**
    - **Validates: Requirements 72.1, 72.2, 72.3, 72.4**
    - **Property 69: Request size limit enforcement**
    - **Validates: Requirements 73.1, 73.2, 73.3**
    - **Property 71: Input validation rejects oversized and malformed input**
    - **Validates: Requirements 75.1, 75.2, 75.4, 75.5**
    - **Property 72: PII masking in log output**
    - **Validates: Requirements 76.1, 76.2, 76.3, 76.4**
    - **Property 73: EXIF stripping removes GPS data from uploaded images**
    - **Validates: Requirements 77.4**
    - **Property 74: Pre-signed URLs expire after configured duration**
    - **Validates: Requirements 77.3**
    - _Requirements: 69.5, 70.4, 71.6, 72.5, 72.6, 73.5, 73.6, 75.7, 75.8, 76.5, 76.6, 77.7, 77.8, 77.9_

  - [x] 1.7 Create database migrations for all new and modified tables
    - Migration: Remove seed data (reversible DELETE of records from seed migrations, rename seed files with `.disabled` suffix) — Req 1
    - Migration: Add `communications` table — Req 4
    - Migration: Add `customer_photos` table — Req 9
    - Migration: Add `city`, `state`, `address`, `action_tags` (JSONB) columns to `leads` table — Req 12, 13
    - Migration: Add `lead_attachments` table — Req 15
    - Migration: Add `estimate_templates` and `contract_templates` tables — Req 17
    - Migration: Add `notes` (TEXT) and `summary` (VARCHAR(255)) columns to `jobs` table — Req 20
    - Migration: Add `en_route_at`, `materials_needed`, `estimated_duration_minutes` columns to `appointments` table — Req 35, 40
    - Migration: Update `appointments.status` CHECK constraint to accept all 8 values (pending, scheduled, confirmed, en_route, in_progress, completed, cancelled, no_show) — Req 79
    - Migration: Add `staff_breaks` table — Req 42
    - Migration: Add `estimates` table with token fields (customer_token, token_expires_at, token_readonly) — Req 48, 78
    - Migration: Add `estimate_follow_ups` table — Req 51
    - Migration: Add `expenses` table — Req 53
    - Migration: Add `pre_due_reminder_sent_at`, `last_past_due_reminder_at` columns to `invoices` table — Req 54
    - Migration: Add `document_url` (VARCHAR(500)) column to `invoices` table — Req 80
    - Migration: Add `campaigns` and `campaign_recipients` tables — Req 45
    - Migration: Add `marketing_budgets` table — Req 64
    - Migration: Add `media_library` table — Req 49
    - Migration: Add `audit_log` table — Req 74
    - Migration: Migrate GoogleSheetSubmission records to Lead records (data migration) — Req 19
    - Migration: Alter `sent_messages.customer_id` to nullable, add `lead_id` FK, add CHECK (customer_id IS NOT NULL OR lead_id IS NOT NULL), update message_type CHECK — Req 81
    - Migration: Add `invoice_token` (UUID, nullable) and `invoice_token_expires_at` (DateTime, nullable) columns to `invoices` table — Req 84
    - Migration: Create `business_settings` table (id UUID PK, setting_key VARCHAR UNIQUE, setting_value JSONB, updated_by FK staff nullable, updated_at DateTime) with seed defaults for company info, invoice terms, notification prefs, estimate defaults — Req 87
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.4, 9.1, 12.1, 13.1, 15.1, 17.1, 17.2, 20.1, 35.2, 35.3, 40.1, 42.3, 45.1, 45.2, 48.1, 49.1, 51.1, 53.1, 54.4, 64.1, 74.1, 79.3, 80.1, 81.1, 81.2, 81.3, 81.4, 84.1, 87.1, 87.9_

  - [x] 1.8 Write unit tests for seed data cleanup migration
    - Verify cleanup migration removes exactly expected seed record counts
    - Verify non-seed records remain intact after migration
    - **Property 1: Seed cleanup preserves non-seed records**
    - **Validates: Requirements 1.4**
    - _Requirements: 1.5, 1.6_

- [x] 2. Checkpoint — Foundation complete
  - Ensure all migrations run cleanly, all security middleware tests pass, ask the user if questions arise.

- [ ] 3. Data Layer: Models, Schemas, and Repositories
  - [x] 3.1 Create new SQLAlchemy models
    - `src/grins_platform/models/communication.py` — Communication model with customer_id FK, channel, direction, content, addressed, addressed_at, addressed_by
    - `src/grins_platform/models/customer_photo.py` — CustomerPhoto model with customer_id FK, file_key, file_name, file_size, content_type, caption, uploaded_by, appointment_id
    - `src/grins_platform/models/lead_attachment.py` — LeadAttachment model with lead_id FK, file_key, file_name, file_size, content_type, attachment_type
    - `src/grins_platform/models/estimate_template.py` — EstimateTemplate model with name, description, line_items (JSONB), terms, is_active
    - `src/grins_platform/models/contract_template.py` — ContractTemplate model with name, body, terms_and_conditions, is_active
    - `src/grins_platform/models/estimate.py` — Estimate model with lead_id, customer_id, job_id, template_id, status, line_items (JSONB), options (JSONB), subtotal, tax_amount, discount_amount, total, promotion_code, valid_until, customer_token, token_expires_at, token_readonly, notes, approved_at/ip/user_agent, rejected_at/reason
    - `src/grins_platform/models/estimate_follow_up.py` — EstimateFollowUp model with estimate_id FK, follow_up_number, scheduled_at, sent_at, channel, message, promotion_code, status
    - `src/grins_platform/models/expense.py` — Expense model with category, description, amount, date, job_id, staff_id, vendor, receipt_file_key, receipt_amount_extracted, lead_source, notes
    - `src/grins_platform/models/campaign.py` — Campaign + CampaignRecipient models
    - `src/grins_platform/models/marketing_budget.py` — MarketingBudget model with channel, budget_amount, period_start/end, actual_spend
    - `src/grins_platform/models/media_library.py` — MediaLibraryItem model with file_key, file_name, file_size, content_type, media_type, category, caption, is_public
    - `src/grins_platform/models/staff_break.py` — StaffBreak model with staff_id, appointment_id, start_time, end_time, break_type
    - `src/grins_platform/models/audit_log.py` — AuditLog model with actor_id, actor_role, action, resource_type, resource_id, details (JSONB), ip_address, user_agent
    - Update existing Lead model: add city, state, address, action_tags fields
    - Update existing Job model: add notes, summary fields
    - Update existing Appointment model: add en_route_at, materials_needed, estimated_duration_minutes fields
    - Update existing Invoice model: add pre_due_reminder_sent_at, last_past_due_reminder_at, document_url, invoice_token, invoice_token_expires_at fields
    - Update existing SentMessage model: make customer_id nullable, add lead_id FK
    - Create `src/grins_platform/models/business_setting.py` — BusinessSetting model with setting_key (UNIQUE), setting_value (JSONB), updated_by, updated_at (Req 87)
    - Register all new models in `__init__.py`
    - _Requirements: 4.4, 9.1, 12.1, 13.1, 15.1, 17.1, 17.2, 20.1, 35.3, 40.1, 42.3, 45.1, 45.2, 48.1, 49.1, 51.1, 53.1, 54.4, 64.1, 74.1, 80.1, 81.1, 81.2, 84.1, 87.1_

  - [x] 3.2 Create Pydantic schemas for all new entities
    - `src/grins_platform/schemas/communication.py` — CommunicationCreate, CommunicationResponse, CommunicationUpdate (address action), UnaddressedCountResponse
    - `src/grins_platform/schemas/estimate.py` — EstimateCreate, EstimateResponse, EstimateTemplateCreate/Response, ContractTemplateCreate/Response, EstimateSendResponse, FollowUpResponse
    - `src/grins_platform/schemas/expense.py` — ExpenseCreate, ExpenseResponse, ExpenseByCategoryResponse, ReceiptExtractionResponse
    - `src/grins_platform/schemas/campaign.py` — CampaignCreate, CampaignResponse, CampaignSendResult, CampaignStats, CampaignRecipientResponse
    - `src/grins_platform/schemas/media.py` — MediaCreate, MediaResponse
    - `src/grins_platform/schemas/sales.py` — SalesMetricsResponse (estimates_needing_writeup_count, pending_approval_count, needs_followup_count, total_pipeline_revenue, conversion_rate)
    - `src/grins_platform/schemas/accounting.py` — AccountingSummaryResponse, JobFinancialsResponse, TaxSummaryResponse, TaxEstimateResponse, TaxProjectionRequest/Response
    - `src/grins_platform/schemas/marketing.py` — LeadAnalyticsResponse, CACBySourceResponse, MarketingBudgetCreate/Response, QRCodeRequest
    - `src/grins_platform/schemas/portal.py` — PortalEstimateResponse (no internal IDs), PortalApproveRequest, PortalRejectRequest, PortalSignRequest
    - `src/grins_platform/schemas/audit.py` — AuditLogResponse, AuditLogFilters
    - `src/grins_platform/schemas/analytics.py` — StaffTimeAnalyticsResponse, LeadTimeResponse
    - Update existing schemas: CustomerResponse (add internal_notes, preferred_service_times), LeadCreate/Response (add city, state, address, action_tags), JobResponse (add notes, summary, customer summary object), AppointmentResponse (add en_route_at, materials_needed, estimated_duration_minutes), InvoiceResponse (add document_url, invoice_token)
    - Create `src/grins_platform/schemas/settings.py` — BusinessSettingResponse, BusinessSettingUpdate (Req 87)
    - Create `src/grins_platform/schemas/portal.py` — add PortalInvoiceResponse (no internal IDs: invoice_number, date, due_date, line_items, total, paid, balance, status, payment_link) (Req 84)
    - Create `src/grins_platform/schemas/sent_message.py` — SentMessageListResponse, SentMessageFilters (type, status, date range, search) (Req 82)
    - Create `src/grins_platform/schemas/estimate.py` — add EstimateDetailResponse with activity_timeline array (Req 83)
    - All schemas enforce max_length on strings, UUID validation on IDs, strict typing
    - _Requirements: 5.2, 6.2, 8.1, 10.3, 11.4, 12.2, 13.1, 20.2, 22.5, 37.2, 40.2, 47.3, 48.1, 52.5, 53.3, 57.2, 58.2, 59.2, 61.2, 61.4, 63.5, 64.2, 74.3, 75.1, 75.2, 75.4, 78.6, 82.2, 82.3, 83.2, 83.3, 84.2, 84.9, 87.2_

  - [x] 3.3 Create repositories for all new entities
    - `src/grins_platform/repositories/communication_repository.py` — CRUD + unaddressed count query + mark addressed
    - `src/grins_platform/repositories/estimate_repository.py` — CRUD + get_by_token + find unapproved older than N hours + template CRUD
    - `src/grins_platform/repositories/expense_repository.py` — CRUD + by-category aggregation + by-job filtering
    - `src/grins_platform/repositories/campaign_repository.py` — CRUD + recipient management + stats aggregation
    - `src/grins_platform/repositories/media_repository.py` — CRUD + filtered browsing by category/type
    - `src/grins_platform/repositories/audit_log_repository.py` — create entry + paginated filtered query
    - `src/grins_platform/repositories/marketing_budget_repository.py` — CRUD + budget vs actual calculation
    - _Requirements: 4.2, 4.4, 17.3, 17.4, 45.3, 45.5, 48.2, 49.2, 49.3, 53.2, 53.3, 64.2, 74.3_

  - [x] 3.4 Write unit tests for schema validation and model constraints
    - Test Communication record round-trip (create + read back identical fields, addressed defaults to false)
    - Test SentMessage with customer_id=NULL and valid lead_id inserts successfully
    - Test SentMessage with both customer_id=NULL and lead_id=NULL fails CHECK constraint
    - Test message_type='lead_confirmation' accepted by CHECK constraint
    - Test Pydantic schemas reject oversized strings, invalid UUIDs, disallowed file types
    - **Property 4: Communication record round-trip**
    - **Validates: Requirements 4.4**
    - **Property 78: SentMessage supports lead-only recipients**
    - **Validates: Requirements 81.1, 81.2, 81.3, 81.4**
    - _Requirements: 4.6, 4.7, 81.7, 81.8, 81.9_

- [x] 4. Checkpoint — Data layer complete
  - Ensure all models, schemas, and repositories are created, all data layer tests pass, ask the user if questions arise.

- [ ] 5. Service Layer: Core Business Logic
  - [x] 5.1 Implement CustomerService enhancements (duplicates, merge, notes, photos, invoices, service times, payment methods)
    - `find_duplicates()` — pg_trgm similarity() threshold 0.7 for name, exact match phone/email
    - `merge_customers()` — single transaction: UPDATE all FK refs → soft-delete duplicates → AuditLog entry
    - `update_internal_notes()` — PATCH internal_notes field
    - `update_preferred_service_times()` — PATCH preferred_service_times JSONB
    - `get_customer_invoices()` — paginated, sorted by date desc
    - `get_payment_methods()` — Stripe PaymentMethod.list via stripe_customer_id (read-only from agreement flow)
    - `charge_customer()` — Stripe PaymentIntent.create with default payment method
    - All methods use LoggerMixin structured logging
    - _Requirements: 7.1, 7.2, 7.4, 8.4, 10.1, 10.2, 11.3, 56.1, 56.2, 56.3, 56.5, 56.6_

  - [x] 5.2 Write unit tests for CustomerService
    - Test duplicate detection finds matches by phone, email, and similar name (P7)
    - Test merge reassigns all related records and soft-deletes duplicates (P8)
    - Test internal notes round-trip (P9)
    - Test customer photo lifecycle: upload → list → delete (P10)
    - Test customer invoice history filtered and sorted correctly (P12)
    - Test preferred service times round-trip (P13)
    - **Property 7: Duplicate detection finds matching records**
    - **Validates: Requirements 7.1**
    - **Property 8: Customer merge reassigns all related records**
    - **Validates: Requirements 7.2**
    - **Property 9: Internal notes round-trip**
    - **Validates: Requirements 8.4**
    - **Property 10: Customer photo lifecycle round-trip**
    - **Validates: Requirements 9.2, 9.3, 9.4**
    - **Property 12: Customer invoice history is correctly filtered and sorted**
    - **Validates: Requirements 10.1, 10.3**
    - **Property 13: Preferred service times round-trip**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4**
    - _Requirements: 7.5, 7.6, 8.5, 9.7, 10.4, 11.5, 56.7_

  - [x] 5.3 Implement LeadService enhancements (address, tags, bulk outreach, attachments, reverse flow, work request migration)
    - `create_lead()` — accept city/state/address, auto-assign NEEDS_CONTACT tag, auto-populate city/state from zip, trigger SMS confirmation if consented (Req 46)
    - `update_action_tags()` — atomic JSONB tag update
    - `mark_contacted()` — remove NEEDS_CONTACT, set contacted_at
    - `bulk_outreach()` — consent-gated SMS/email to multiple leads, return summary (sent/skipped/failed)
    - `create_lead_from_estimate()` — reverse flow: create/reactivate lead with ESTIMATE_PENDING tag
    - `migrate_work_requests()` — one-time GoogleSheetSubmission → Lead migration
    - All methods use LoggerMixin structured logging
    - _Requirements: 12.2, 12.5, 13.2, 13.3, 13.4, 13.5, 13.6, 14.1, 14.3, 14.4, 14.5, 18.1, 18.2, 19.1, 19.4, 19.5, 19.6, 46.1, 46.2, 46.3_

  - [x] 5.4 Write unit tests for LeadService
    - Test lead address fields round-trip (P14)
    - Test zip code auto-populates city and state (P15)
    - Test tag state machine: new→NEEDS_CONTACT→contacted→NEEDS_ESTIMATE→ESTIMATE_PENDING→ESTIMATE_APPROVED (P16)
    - Test tag filtering returns only matching leads (P17)
    - Test consent-gated bulk outreach with correct summary counts (P18)
    - Test lead attachment lifecycle: upload → list → delete (P19)
    - Test reverse flow: estimate creates lead with ESTIMATE_PENDING (P23)
    - Test work request migration preserves all data (P24)
    - Test SMS lead confirmation is consent and time-window gated (P49)
    - **Property 14: Lead address fields round-trip**
    - **Validates: Requirements 12.2**
    - **Property 15: Zip code auto-populates city and state**
    - **Validates: Requirements 12.5**
    - **Property 16: Lead action tag state machine**
    - **Validates: Requirements 13.2, 13.3, 13.4, 13.5, 13.6**
    - **Property 17: Lead tag filtering returns only matching leads**
    - **Validates: Requirements 13.8**
    - **Property 18: Consent-gated bulk outreach with correct summary**
    - **Validates: Requirements 14.1, 14.3, 14.4**
    - **Property 19: Lead attachment lifecycle round-trip**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
    - **Property 23: Reverse flow — estimate requiring approval creates lead**
    - **Validates: Requirements 18.1, 18.2**
    - **Property 24: Work request migration preserves all data**
    - **Validates: Requirements 19.1, 19.5**
    - **Property 49: SMS lead confirmation is consent and time-window gated**
    - **Validates: Requirements 46.1, 46.2**
    - _Requirements: 12.6, 12.7, 13.9, 13.10, 14.6, 14.7, 15.6, 15.7, 18.4, 18.5, 19.7, 19.8, 46.5, 46.6, 46.7_

  - [x] 5.5 Implement EstimateService (create, templates, send, portal approve/reject, follow-ups, auto-routing, promotions)
    - `create_estimate()` — line items, optional Good/Better/Best tiers, calculate subtotal/tax/discount/total, generate customer_token (UUID v4), set token_expires_at (30 days)
    - `create_from_template()` — clone template line_items, apply overrides
    - `send_estimate()` — set status=SENT, send portal link via SMS+email, schedule follow-ups at Day 3/7/14/21
    - `approve_via_portal()` — record timestamp/IP/user_agent, set token_readonly=True, update lead tag to ESTIMATE_APPROVED, cancel remaining follow-ups, create Job if needed
    - `reject_via_portal()` — record rejection, cancel follow-ups
    - `check_unapproved_estimates()` — background job: find estimates >4hrs old, create leads with ESTIMATE_PENDING
    - `process_follow_ups()` — background job: send due follow-ups
    - `apply_promotion()` — validate code, calculate discounted total
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 17.3, 17.4, 17.5, 32.3, 32.4, 32.7, 48.4, 48.5, 48.6, 48.7, 51.2, 51.3, 51.4, 51.5, 78.1, 78.2, 78.3, 78.4, 78.5_

  - [x] 5.6 Write unit tests for EstimateService
    - Test portal estimate access by valid/expired token (P20)
    - Test estimate approval updates lead tag and sets token_readonly (P21)
    - Test estimate template round-trip and creation from template with overrides (P22)
    - Test unapproved estimate auto-routing to leads after 4hrs (P35)
    - Test estimate total calculation with tiers and discounts (P51)
    - Test follow-up scheduling at correct intervals and cancellation on approval (P52)
    - Test portal responses exclude internal IDs (P75)
    - **Property 20: Portal estimate access by token**
    - **Validates: Requirements 16.1, 78.1, 78.2**
    - **Property 21: Estimate approval updates lead tag and invalidates token for writes**
    - **Validates: Requirements 16.2, 16.5, 78.4**
    - **Property 22: Estimate template round-trip**
    - **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**
    - **Property 35: Unapproved estimate auto-routing to leads**
    - **Validates: Requirements 32.4, 32.7**
    - **Property 51: Estimate total calculation with tiers and discounts**
    - **Validates: Requirements 48.4, 48.5, 48.6, 48.7**
    - **Property 52: Follow-up scheduling and cancellation**
    - **Validates: Requirements 51.2, 51.5**
    - **Property 75: Portal responses exclude internal IDs**
    - **Validates: Requirements 78.6**
    - _Requirements: 16.8, 16.9, 17.7, 17.8, 32.8, 48.8, 51.7, 51.8, 78.7, 78.8_

  - [x] 5.7 Implement AppointmentService enhancements (reschedule, status transitions, payment collection, invoice/estimate creation, notes/photos, review request, lead time, staff time analytics)
    - `reschedule()` — drag-drop: validate no staff conflict, update time
    - `transition_status()` — strict state machine: confirmed→en_route→in_progress→completed; record timestamps; payment gate on completion (Req 36); trigger notifications on each transition (Req 39)
    - `collect_payment()` — create/update invoice with payment (card, cash, check, venmo, zelle)
    - `create_invoice_from_appointment()` — pre-populate from job/customer, generate Stripe payment link, send via SMS+email
    - `create_estimate_from_appointment()` — delegate to EstimateService
    - `add_notes_and_photos()` — save notes to appointment + append to customer.internal_notes, upload photos linked to both
    - `request_google_review()` — consent-gated SMS with review link, 30-day dedup
    - `calculate_lead_time()` — earliest available slot based on staff availability and appointment density
    - `get_staff_time_analytics()` — avg travel_time, job_duration, total_time by staff/job_type, flag 1.5x threshold
    - _Requirements: 24.2, 24.5, 25.2, 25.3, 29.1, 30.3, 30.4, 30.5, 30.6, 31.2, 31.3, 31.4, 31.5, 32.5, 32.6, 33.2, 33.3, 34.2, 34.5, 34.6, 35.4, 35.5, 35.6, 36.1, 36.2, 36.4, 37.1, 37.2, 37.4_

  - [x] 5.8 Write unit tests for AppointmentService
    - Test appointment conflict detection on reschedule (P28)
    - Test schedule lead time calculation (P29)
    - Test job filter returns only matching jobs (P30)
    - Test address auto-population from customer (P32)
    - Test payment collection creates/updates invoice (P33)
    - Test invoice pre-population from appointment (P34)
    - Test appointment notes propagate to customer (P36)
    - Test Google review consent and 30-day deduplication (P37)
    - Test appointment status transition state machine (P38)
    - Test payment gate blocks completion without payment/invoice (P39)
    - Test staff time duration calculations (P40)
    - Test enriched appointment response includes all required fields (P43)
    - **Property 28: Appointment conflict detection on reschedule**
    - **Validates: Requirements 24.2, 24.4, 24.5**
    - **Property 29: Schedule lead time calculation**
    - **Validates: Requirements 25.2, 25.3**
    - **Property 30: Job filter returns only matching jobs**
    - **Validates: Requirements 26.2, 26.3**
    - **Property 32: Address auto-population from customer**
    - **Validates: Requirements 29.1**
    - **Property 33: Payment collection creates/updates invoice**
    - **Validates: Requirements 30.3, 30.4, 30.5**
    - **Property 34: Invoice pre-population from appointment**
    - **Validates: Requirements 31.2, 31.4**
    - **Property 36: Appointment notes propagate to customer**
    - **Validates: Requirements 33.2, 33.3**
    - **Property 37: Google review request consent and deduplication**
    - **Validates: Requirements 34.2, 34.6**
    - **Property 38: Appointment status transition state machine**
    - **Validates: Requirements 35.1, 35.2, 35.3, 35.4, 35.5, 35.6**
    - **Property 39: Payment gate blocks completion without payment or invoice**
    - **Validates: Requirements 36.1, 36.2**
    - **Property 40: Staff time duration calculations**
    - **Validates: Requirements 37.1**
    - **Property 43: Enriched appointment response includes all required fields**
    - **Validates: Requirements 40.2**
    - _Requirements: 24.6, 24.7, 25.4, 26.5, 29.4, 30.7, 30.8, 31.6, 31.7, 32.8, 33.6, 33.7, 34.7, 35.8, 35.9, 36.5, 36.6, 37.5, 37.6, 40.5_

  - [x] 5.9 Implement NotificationService (day-of reminders, on-my-way, arrival, delay, completion, invoice reminders, lien notifications, lead confirmation SMS)
    - `send_day_of_reminders()` — daily 7AM CT, SMS (if consented) + email for today's appointments
    - `send_on_my_way()` — staff name + Google Maps ETA to customer
    - `send_arrival_notification()` — confirm technician arrived
    - `send_delay_notification()` — appointment running >15min past scheduled end
    - `send_completion_notification()` — job summary + receipt/invoice link + Google review link
    - `send_invoice_reminders()` — pre-due (3 days), past-due (weekly), lien (30 days past due)
    - `send_lead_confirmation_sms()` — consent-gated, time-window gated (8AM-9PM CT), defers if outside window
    - All notifications consent-gated: SMS requires sms_consent=True, email always sent as fallback
    - _Requirements: 39.1, 39.2, 39.3, 39.4, 39.5, 39.6, 39.7, 39.8, 46.1, 46.2, 46.3, 54.1, 54.2, 54.3, 54.5, 55.1, 55.2, 55.3, 55.4, 55.5_

  - [x] 5.10 Write unit tests for NotificationService
    - Test each notification type triggered at correct event (P42)
    - Test SMS consent gating and email fallback (P42)
    - Test automated invoice reminder scheduling: pre-due, past-due, lien thresholds (P55)
    - **Property 42: All customer notifications are consent-gated**
    - **Validates: Requirements 39.1, 39.2, 39.3, 39.4, 39.5, 39.8**
    - **Property 55: Automated invoice reminder scheduling**
    - **Validates: Requirements 54.1, 54.2, 54.3, 55.1, 55.2**
    - _Requirements: 39.9, 39.10, 54.6, 55.6_

  - [x] 5.11 Implement CampaignService (create, send, stats, automation rules)
    - `create_campaign()` — DRAFT status
    - `send_campaign()` — filter recipients by target_audience, skip non-consented, enqueue as background job, CAN-SPAM compliance (address + unsubscribe link)
    - `get_campaign_stats()` — delivery metrics from campaign_recipients
    - `evaluate_automation_rules()` — daily job: evaluate recurring triggers, create and send matching campaigns
    - _Requirements: 45.3, 45.4, 45.5, 45.6, 45.7, 45.8, 45.9, 45.10_

  - [x] 5.12 Write unit tests for CampaignService
    - Test campaign recipient filtering by consent (P48)
    - **Property 48: Campaign recipient filtering by consent**
    - **Validates: Requirements 45.6, 45.5**
    - _Requirements: 45.11, 45.12_

  - [x] 5.13 Implement AccountingService (summary, expenses by category, job financials, tax summary, tax estimate, tax projection, receipt OCR, Plaid sync)
    - `get_summary()` — YTD revenue (paid invoices), expenses, profit, pending/past-due totals
    - `get_expenses_by_category()` — aggregate expenses by category for date range
    - `get_job_financials()` — quoted_amount, final_amount, total_paid, material_costs, labor_costs, total_costs, profit, profit_margin
    - `get_tax_summary()` — expense totals by tax category + revenue by job type, CSV exportable
    - `get_tax_estimate()` — estimated_tax_due = (revenue - deductions) × effective_tax_rate
    - `project_tax()` — what-if: add hypothetical revenue/expenses, recalculate
    - `extract_receipt()` — OpenAI Vision API: extract amount/vendor/category from receipt image
    - `sync_transactions()` — Plaid daily sync: fetch transactions, auto-categorize by MCC, create expenses
    - _Requirements: 52.2, 52.5, 53.3, 53.5, 53.6, 57.1, 57.2, 59.1, 59.2, 59.3, 59.4, 60.1, 60.2, 60.4, 61.1, 61.2, 61.3, 61.4, 62.2, 62.3, 62.4, 62.5_

  - [x] 5.14 Write unit tests for AccountingService
    - Test accounting summary calculation (P53)
    - Test expense category aggregation and per-job cost linkage (P54)
    - Test per-job financial calculations with zero division handling (P56)
    - Test CAC calculation with various spend/conversion scenarios (P57)
    - Test tax summary aggregation by category (P58)
    - Test tax estimation and what-if projection (P59)
    - Test Plaid transaction auto-categorization by MCC (P60)
    - Test receipt OCR response parsing
    - **Property 53: Accounting summary calculation correctness**
    - **Validates: Requirements 52.2, 52.5**
    - **Property 54: Expense category aggregation and per-job cost linkage**
    - **Validates: Requirements 53.3, 53.5**
    - **Property 56: Per-job financial calculations**
    - **Validates: Requirements 57.1, 57.2**
    - **Property 57: Customer acquisition cost calculation**
    - **Validates: Requirements 58.1, 58.2**
    - **Property 58: Tax summary aggregation by category**
    - **Validates: Requirements 59.1, 59.2**
    - **Property 59: Tax estimation calculation**
    - **Validates: Requirements 61.1, 61.2, 61.3, 61.4**
    - **Property 60: Plaid transaction auto-categorization**
    - **Validates: Requirements 62.4**
    - _Requirements: 52.7, 53.8, 53.9, 57.4, 58.5, 59.5, 60.6, 61.5, 62.7_

  - [x] 5.15 Implement MarketingService (lead analytics, CAC, QR codes) and MediaService (CRUD)
    - `get_lead_analytics()` — lead counts by source, conversion funnel, conversion rates, avg time to conversion, top source, trend
    - `get_cac()` — CAC per lead source = marketing_spend / converted_customers
    - `generate_qr_code()` — QR code PNG with UTM params (utm_source=qr_code, utm_campaign={name}, utm_medium=print)
    - MediaService: CRUD for media library items with file upload/download
    - _Requirements: 49.2, 49.3, 58.1, 58.2, 63.2, 63.3, 63.4, 63.5, 65.1, 65.3_

  - [x] 5.16 Write unit tests for MarketingService and MediaService
    - Test lead source analytics and conversion funnel (P61)
    - Test marketing budget vs actual spend (P62)
    - Test QR code URL contains correct UTM parameters (P63)
    - Test media file type validation and category filtering
    - **Property 61: Lead source analytics and conversion funnel**
    - **Validates: Requirements 63.2, 63.3, 63.4, 63.5**
    - **Property 62: Marketing budget vs actual spend**
    - **Validates: Requirements 64.3, 64.4**
    - **Property 63: QR code URL contains correct UTM parameters**
    - **Validates: Requirements 65.1, 65.3**
    - _Requirements: 49.6, 58.5, 63.7, 64.5, 65.5_

  - [x] 5.17 Implement AuditService, ChatService, InvoicePDFService, and remaining services
    - AuditService: `log_action()` — create audit log entry; `get_audit_log()` — paginated, filterable
    - ChatService: `handle_public_message()` — GPT-4o-mini with Grins context, Redis session (30min TTL), human escalation detection → create Communication + Lead
    - InvoicePDFService: `generate_pdf()` — WeasyPrint HTML→PDF, upload to S3, update invoice.document_url; `get_pdf_url()` — pre-signed download URL
    - Voice webhook handler: extract name/phone/service from Vapi payload → create Lead via LeadService
    - Staff location: store/retrieve from Redis with 5min TTL
    - Staff breaks: create/end break, adjust subsequent appointment ETAs
    - SettingsService: `get_all_settings()`, `update_setting()` — read/write business_settings table with caching (Req 87)
    - InvoicePortalService: `generate_invoice_token()` — create UUID token with 90-day expiry, `get_invoice_by_token()` — return invoice data without internal IDs (Req 84)
    - Update InvoicePDFService to read company branding from business_settings (Req 87.7)
    - Update NotificationService to read time windows and reminder times from business_settings (Req 87.8)
    - Update NotificationService to include portal invoice link `/portal/invoices/{token}` in invoice notifications instead of internal CRM links (Req 84.7)
    - _Requirements: 41.1, 41.2, 41.5, 42.2, 42.5, 43.1, 43.2, 43.3, 43.5, 44.1, 44.2, 44.3, 44.5, 74.1, 74.2, 74.3, 80.2, 80.3, 80.4, 80.7, 84.1, 84.2, 84.7, 84.8, 84.9, 87.2, 87.7, 87.8, 87.9_

  - [x] 5.18 Write unit tests for AuditService, ChatService, InvoicePDFService, and remaining services
    - Test audit log entry creation for auditable actions (P70)
    - Test chat escalation detection creates lead and communication (P46)
    - Test voice webhook creates lead with correct source (P47)
    - Test staff location round-trip via Redis with TTL (P44)
    - Test break adjusts subsequent appointment ETAs (P45)
    - Test invoice PDF generation round-trip (P77)
    - Test AppointmentStatus enum accepts all 8 frontend values including no_show and pending (P76)
    - **Property 44: Staff location round-trip via Redis**
    - **Validates: Requirements 41.1, 41.2**
    - **Property 45: Break adjusts subsequent appointment ETAs**
    - **Validates: Requirements 42.5**
    - **Property 46: Chat escalation detection creates lead and communication**
    - **Validates: Requirements 43.3, 43.5**
    - **Property 47: Voice webhook creates lead with correct source**
    - **Validates: Requirements 44.3, 44.5**
    - **Property 70: Audit log entry creation for auditable actions**
    - **Validates: Requirements 74.1, 74.2**
    - **Property 76: AppointmentStatus enum accepts all frontend values**
    - **Validates: Requirements 79.1, 79.2, 79.3**
    - **Property 77: Invoice PDF generation round-trip**
    - **Validates: Requirements 80.1, 80.2, 80.3, 80.4**
    - Test portal invoice access by valid/expired token (P81)
    - Test settings round-trip and service consumption (P84)
    - **Property 81: Portal invoice access by token with correct data**
    - **Validates: Requirements 84.2, 84.4, 84.5, 84.8, 84.9**
    - **Property 84: Business settings round-trip and service consumption**
    - **Validates: Requirements 87.2, 87.7, 87.8**
    - _Requirements: 41.6, 41.7, 42.6, 43.6, 44.7, 74.5, 79.6, 79.7, 80.8, 84.10, 84.11, 87.10_

- [x] 6. Checkpoint — Service layer complete
  - Ensure all service tests pass, ask the user if questions arise.

- [x] 7. API Layer: All New and Enhanced Routes
  - [x] 7.1 Create Dashboard-related API endpoints
    - `GET /api/v1/communications/unaddressed-count` — unaddressed message count (Req 4)
    - `GET /api/v1/invoices/metrics/pending` — pending invoice count + total (Req 5)
    - `GET /api/v1/jobs/metrics/by-status` — 6-category job status counts (Req 6)
    - _Requirements: 4.2, 5.2, 6.2_

  - [x] 7.2 Write unit tests for Dashboard API endpoints
    - Test unaddressed count returns correct counts (P3)
    - Test pending invoice metrics returns correct count and total from actual invoice records (P5)
    - Test by-status metrics returns all six categories with correct counts (P6)
    - **Property 3: Unaddressed communication count accuracy**
    - **Validates: Requirements 4.2**
    - **Property 5: Pending invoice metrics correctness**
    - **Validates: Requirements 5.1, 5.2**
    - **Property 6: Job status category partitioning**
    - **Validates: Requirements 6.1, 6.2**
    - _Requirements: 4.6, 5.4, 6.4_

  - [x] 7.3 Create Customer-related API endpoints
    - `GET /api/v1/customers/duplicates` — potential duplicate groups (Req 7)
    - `POST /api/v1/customers/merge` — merge duplicate customers (Req 7)
    - `POST /api/v1/customers/{id}/photos` — upload customer photos (Req 9)
    - `GET /api/v1/customers/{id}/photos` — list customer photos with pre-signed URLs (Req 9)
    - `DELETE /api/v1/customers/{id}/photos/{photo_id}` — delete photo (Req 9)
    - `GET /api/v1/customers/{id}/invoices` — customer invoice history (Req 10)
    - `GET /api/v1/customers/{id}/payment-methods` — Stripe saved cards (Req 56)
    - `POST /api/v1/customers/{id}/charge` — charge saved card (Req 56)
    - Update `PATCH /api/v1/customers/{id}` to accept internal_notes and preferred_service_times (Req 8, 11)
    - _Requirements: 7.1, 7.2, 8.4, 9.2, 9.3, 9.4, 10.3, 11.3, 56.2, 56.3_

  - [x] 7.4 Create Lead-related API endpoints
    - `POST /api/v1/leads/bulk-outreach` — bulk SMS/email outreach (Req 14)
    - `POST /api/v1/leads/{id}/attachments` — upload attachment (Req 15)
    - `GET /api/v1/leads/{id}/attachments` — list attachments with pre-signed URLs (Req 15)
    - `DELETE /api/v1/leads/{id}/attachments/{att_id}` — delete attachment (Req 15)
    - Update `POST /api/v1/leads` and `PATCH /api/v1/leads/{id}` to accept city, state, address, action_tags (Req 12, 13)
    - _Requirements: 12.2, 13.1, 14.1, 15.2, 15.3, 15.4_

  - [x] 7.5 Create Estimate and Template API endpoints
    - CRUD `/api/v1/estimates` — estimate CRUD (Req 48)
    - `POST /api/v1/estimates/{id}/send` — send estimate to customer (Req 48)
    - CRUD `/api/v1/templates/estimates` — estimate template CRUD (Req 17)
    - CRUD `/api/v1/templates/contracts` — contract template CRUD (Req 17)
    - _Requirements: 17.3, 17.4, 48.2, 48.3_

  - [x] 7.6 Create Portal API endpoints (public, no auth)
    - `GET /api/v1/portal/estimates/{token}` — view estimate (Req 16)
    - `POST /api/v1/portal/estimates/{token}/approve` — approve estimate (Req 16)
    - `POST /api/v1/portal/estimates/{token}/reject` — reject estimate (Req 16)
    - `POST /api/v1/portal/contracts/{token}/sign` — sign contract (Req 16)
    - Rate limit: 20 req/min per token (Req 78)
    - Responses exclude internal IDs (Req 78)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 78.3, 78.5, 78.6_

  - [x] 7.7 Create Schedule/Appointment API endpoints
    - Update `PATCH /api/v1/appointments/{id}` — reschedule via drag-drop (Req 24)
    - `GET /api/v1/schedule/lead-time` — booking lead time (Req 25)
    - `POST /api/v1/appointments/{id}/collect-payment` — on-site payment (Req 30)
    - `POST /api/v1/appointments/{id}/create-invoice` — on-site invoice (Req 31)
    - `POST /api/v1/appointments/{id}/create-estimate` — on-site estimate (Req 32)
    - `POST /api/v1/appointments/{id}/photos` — staff photo upload (Req 33)
    - `POST /api/v1/appointments/{id}/request-review` — Google review SMS (Req 34)
    - `POST /api/v1/staff/{id}/location` — GPS location update (Req 41)
    - `GET /api/v1/staff/locations` — all staff locations (Req 41)
    - `POST /api/v1/staff/{id}/breaks` — start break (Req 42)
    - `PATCH /api/v1/staff/{id}/breaks/{break_id}` — end break (Req 42)
    - `GET /api/v1/analytics/staff-time` — staff time analytics (Req 37)
    - `POST /api/v1/notifications/appointment/{id}/day-of` — day-of reminder trigger (Req 39)
    - _Requirements: 24.2, 25.2, 30.5, 31.4, 32.6, 33.4, 34.3, 37.2, 39.6, 41.1, 41.5, 42.2_

  - [x] 7.8 Create Sales, Accounting, Marketing, Communications, Chat, Voice, Media, Audit, and Invoice PDF API endpoints
    - `GET /api/v1/sales/metrics` — sales pipeline metrics (Req 47)
    - `GET /api/v1/accounting/summary` — YTD revenue/expenses/profit (Req 52)
    - CRUD `/api/v1/expenses` + `GET /api/v1/expenses/by-category` (Req 53)
    - `GET /api/v1/jobs/{id}/financials` + `GET /api/v1/jobs/{id}/costs` (Req 57, 53)
    - `GET /api/v1/accounting/tax-summary` (Req 59) + `GET /api/v1/accounting/tax-estimate` (Req 61) + `POST /api/v1/accounting/tax-projection` (Req 61)
    - `POST /api/v1/accounting/connect-account` — Plaid Link initiation (Req 62)
    - `POST /api/v1/expenses/extract-receipt` — OCR receipt extraction (Req 60)
    - CRUD `/api/v1/campaigns` + `POST /api/v1/campaigns/{id}/send` + `GET /api/v1/campaigns/{id}/stats` (Req 45)
    - `GET /api/v1/marketing/lead-analytics` (Req 63) + `GET /api/v1/marketing/cac` (Req 58)
    - CRUD `/api/v1/marketing/budgets` (Req 64)
    - `POST /api/v1/marketing/qr-codes` (Req 65)
    - `GET /api/v1/communications` + `PATCH /api/v1/communications/{id}/address` (Req 4)
    - `POST /api/v1/chat/public` — public AI chatbot (Req 43)
    - `POST /api/v1/voice/webhook` — voice AI webhook (Req 44)
    - CRUD `/api/v1/media` (Req 49)
    - `GET /api/v1/audit-log` — paginated audit log (Req 74)
    - `POST /api/v1/invoices/bulk-notify` — bulk notification (Req 38)
    - `POST /api/v1/invoices/{id}/generate-pdf` — generate PDF, store in S3 (Req 80)
    - `GET /api/v1/invoices/{id}/pdf` — pre-signed download URL (Req 80)
    - `GET /api/v1/sent-messages` — paginated outbound notification history with filters (Req 82)
    - `GET /api/v1/customers/{id}/sent-messages` — outbound messages for a specific customer (Req 82)
    - `GET /api/v1/estimates/{id}` — estimate detail with activity timeline (Req 83)
    - `GET /api/v1/estimates` — filtered estimate list for pipeline views (Req 83)
    - `GET /api/v1/portal/invoices/{token}` — public invoice view (Req 84)
    - `GET /api/v1/settings` — list all business settings (Req 87)
    - `PATCH /api/v1/settings/{key}` — update a specific setting (Req 87)
    - Register all new routers in `main.py` with appropriate prefixes and tags
    - _Requirements: 38.1, 43.1, 43.4, 44.5, 45.3, 45.4, 45.5, 47.3, 49.2, 49.3, 52.5, 53.2, 53.3, 53.5, 57.2, 58.2, 59.2, 60.5, 61.2, 61.4, 62.2, 63.5, 64.2, 65.1, 74.3, 80.2, 80.3, 82.1, 82.2, 82.3, 83.1, 83.2, 83.7, 84.2, 84.3, 87.2_

  - [x] 7.9 Write unit tests for Invoice bulk notify and remaining API endpoints
    - Test consent-gated bulk invoice notifications with correct summary (P41)
    - Test sales pipeline metrics accuracy (P50)
    - **Property 41: Consent-gated bulk invoice notifications**
    - **Validates: Requirements 38.1, 38.3, 38.4**
    - **Property 50: Sales pipeline metrics accuracy**
    - **Validates: Requirements 47.2, 47.3**
    - _Requirements: 38.6, 47.6_

- [x] 8. Checkpoint — API layer complete
  - Ensure all API endpoints are registered, all API tests pass, ask the user if questions arise.

- [x] 9. Frontend: Dashboard Enhancements
  - [x] 9.1 Implement Dashboard alert navigation with highlighting (Req 3)
    - Create `AlertCard.tsx` — clickable card that navigates to target page with `?status={status}&highlight={id}` query params
    - Update Job_List_View and Leads_Page to parse URL query params, auto-apply filters, and show 3-second highlight animation (CSS `@keyframes highlight-fade`)
    - Wire dashboard job status counts to navigate to `/jobs?status={clicked_status}`
    - Wire "New Leads" card to navigate to `/leads?status=new`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 9.2 Implement Dashboard Messages Widget (Req 4)
    - Create `MessagesWidget.tsx` — fetch `GET /communications/unaddressed-count`, display count badge, click navigates to `/communications`
    - _Requirements: 4.1, 4.3_

  - [x] 9.3 Implement Dashboard Invoice Metrics Widget (Req 5)
    - Create `InvoiceMetricsWidget.tsx` — fetch `GET /invoices/metrics/pending`, display count + total amount, replace old job-status-based calculation
    - _Requirements: 5.1, 5.3_

  - [x] 9.4 Implement Dashboard Job Status Grid (Req 6)
    - Create `JobStatusGrid.tsx` — fetch `GET /jobs/metrics/by-status`, render 6 cards (New Requests, Estimates, Pending Approval, To Be Scheduled, In Progress, Complete), each clickable → navigates to `/jobs?status={status}`
    - _Requirements: 6.1_

  - [x] 9.5 Write unit tests for Dashboard URL parameter parsing and filter application
    - Test URL query parameter parsing and filter application for Job_List_View and Leads_Page
    - _Requirements: 3.7_

- [x] 10. Frontend: Customer Detail Enhancements
  - [x] 10.1 Implement Customer Detail tabbed layout with all new tabs
    - Add Radix Tabs: Overview, Photos, Invoice History, Payment Methods, Potential Duplicates
    - Overview tab: editable `internal_notes` textarea (Req 8) + `preferred_service_times` editor with Morning/Afternoon/Evening/No Preference options (Req 11)
    - Photos tab: `PhotoGallery.tsx` — grid gallery with upload dropzone (accept JPEG/PNG/HEIC), caption editing, delete with confirmation. Uses `useCustomerPhotos()` hook (Req 9)
    - Invoice History tab: `InvoiceHistory.tsx` — DataTable with invoice_number, date, total_amount, status badge (color-coded), days_until_due/days_past_due, link to full invoice detail. Uses `useCustomerInvoices()` hook (Req 10)
    - Payment Methods tab: `PaymentMethods.tsx` — list Stripe saved cards (last4/brand), "Charge" button opens amount/description dialog (Req 56)
    - Messages tab: outbound messages sent to this customer (fetches `GET /customers/{id}/sent-messages`), sorted by date desc (Req 82)
    - Potential Duplicates section: `DuplicateReview.tsx` — shown conditionally when duplicates detected, side-by-side comparison, "Merge" button (Req 7)
    - _Requirements: 7.3, 8.2, 8.3, 9.5, 10.1, 10.2, 11.1, 11.2, 56.4, 82.4_

- [x] 11. Frontend: Leads Pipeline Enhancements
  - [x] 11.1 Implement Leads page enhancements (address, tags, bulk outreach, attachments, estimate/contract creation)
    - Update Leads_Page to display `city` column in list view (Req 12)
    - Lead detail: show full address fields (address, city, state, zip_code) in editable form (Req 12)
    - `LeadTagBadges.tsx` — color-coded badges: NEEDS_CONTACT (red), NEEDS_ESTIMATE (orange), ESTIMATE_PENDING (yellow), ESTIMATE_APPROVED (green), ESTIMATE_REJECTED (gray) (Req 13)
    - Add tag filter to Leads_Page (Req 13)
    - `BulkOutreach.tsx` — "Select All" checkbox + "Bulk Outreach" button → message template selector → send → display summary (Req 14)
    - `AttachmentPanel.tsx` — grouped by type (Estimates, Contracts, Other), upload dropzone, download links (pre-signed URLs), delete with confirmation (Req 15)
    - `EstimateCreator.tsx` — template selector → pre-populated form → line item editor → send to customer (Req 17)
    - `ContractCreator.tsx` — template selector → pre-populated contract form (Req 17)
    - "Create Estimate" and "Create Contract" buttons on lead detail view (Req 17)
    - Display estimate-pending leads alongside regular leads, filterable by ESTIMATE_PENDING tag (Req 18)
    - Redirect `/work-requests` to `/leads` with notification explaining consolidation (Req 19)
    - Remove WorkRequestsList and WorkRequestDetail components (Req 19)
    - _Requirements: 12.3, 12.4, 13.7, 13.8, 14.2, 15.5, 17.5, 17.6, 18.3, 19.2, 19.3_

- [x] 12. Frontend: Jobs List Enhancements
  - [x] 12.1 Implement Job List column changes and status simplification
    - Remove "Category" column (Req 22)
    - Add "Customer" column: customer full name linked to customer detail page (Req 22)
    - Add "Tags" column: customer tags (priority, red_flag, slow_payer, new_customer) as color-coded badges (Req 22)
    - Replace "Created" date with "Days Waiting" column: `current_date - created_at` calculated client-side (Req 22)
    - Add "Due By" column: `target_end_date` formatted as human-readable date, amber if within 7 days, red if past, "No deadline" in muted text if null (Req 23)
    - Implement status simplification mapping: requested/approved → "To Be Scheduled", scheduled/in_progress → "In Progress", completed/closed → "Complete", cancelled → "Cancelled" (Req 21)
    - Update status filter to use simplified labels (Req 21)
    - Add `summary` column display (Req 20)
    - Job detail: editable `notes` textarea (Req 20)
    - Job detail: "Financials" section showing quoted_amount, final_amount, total_paid, material_costs, labor_costs, total_costs, profit, profit_margin (Req 57)
    - _Requirements: 20.3, 20.4, 20.5, 21.1, 21.2, 21.3, 21.4, 22.1, 22.2, 22.3, 22.4, 23.1, 23.2, 23.3, 23.4, 57.1, 57.3_

  - [x] 12.2 Write unit tests for job status mapping and date color logic
    - Test status mapping correctly maps all existing statuses to simplified labels (P26)
    - Test Days Waiting calculation and Due By color logic (P27)
    - Test job notes and summary round-trip (P25)
    - **Property 25: Job notes and summary round-trip**
    - **Validates: Requirements 20.1, 20.2**
    - **Property 26: Job status simplification mapping**
    - **Validates: Requirements 21.1**
    - **Property 27: Days Waiting calculation and Due By color logic**
    - **Validates: Requirements 22.4, 23.1, 23.2, 23.3, 23.4**
    - _Requirements: 20.6, 21.5, 22.6, 23.5_

- [x] 13. Frontend: Schedule and Staff Workflow Enhancements
  - [x] 13.1 Implement Schedule calendar enhancements (drag-drop, lead time, job selector, inline customer info, calendar format, address auto-populate)
    - `DragDropCalendar.tsx` — FullCalendar with `editable: true`, `eventDrop` handler calls `PATCH /appointments/{id}`, on conflict (409) revert position + error toast. Event labels: `"{Staff Name} - {Job Type}"` (Req 28). Color by status (confirmed=blue, in_progress=orange, completed=green) (Req 24, 28)
    - `LeadTimeIndicator.tsx` — badge in schedule header: "Booked out {N} days/weeks", fetches `GET /schedule/lead-time` (Req 25)
    - `JobSelector.tsx` — modal with filterable DataTable of unscheduled jobs, filters: city/zip, job type, customer name, multi-select checkboxes, "Add to Schedule" creates appointments for each (Req 26)
    - `InlineCustomerPanel.tsx` — Radix Sheet (slide-over from right), shows customer name/phone/email/address/preferred times/internal notes/job details, "View Full Details" link, URL does NOT change (Req 27)
    - Update appointment creation form: auto-populate address from customer's primary property address with visual indicator, allow override (Req 29)
    - `AppointmentDetail.tsx` — enriched view: customer info, job type, location with Google Maps link, materials needed, estimated duration, customer history summary, special notes, "Get Directions" button opens `https://maps.google.com/?daddr={address}` (Req 40)
    - _Requirements: 24.1, 24.3, 24.4, 25.1, 26.1, 26.2, 26.3, 26.4, 27.1, 27.2, 27.3, 28.1, 28.2, 29.1, 29.2, 29.3, 40.2, 40.3, 40.4_

  - [x] 13.2 Implement Staff Workflow buttons and on-site actions
    - `StaffWorkflowButtons.tsx` — three sequential buttons based on current status: confirmed → "On My Way" (blue), en_route → "Job Started" (orange), in_progress → "Job Complete" (green, disabled if no payment/invoice per Req 36 with tooltip). Each click calls `PATCH /appointments/{id}/status` and triggers notification (Req 35, 36)
    - `PaymentCollector.tsx` — form with method selector (Credit Card, Cash, Check, Venmo, Zelle, Send Invoice), amount input, reference number for non-card methods, calls `POST /appointments/{id}/collect-payment` (Req 30)
    - `InvoiceCreator.tsx` — pre-populated invoice form from job/customer data, calls `POST /appointments/{id}/create-invoice` (Req 31)
    - `EstimateCreator.tsx` (schedule context) — template selection + line items, calls `POST /appointments/{id}/create-estimate` (Req 32)
    - `AppointmentNotes.tsx` — notes textarea + photo upload section (accept `image/*;capture=camera` for mobile), calls appointment notes/photos endpoints (Req 33)
    - `ReviewRequest.tsx` — "Request Google Review" button visible when status=completed, calls `POST /appointments/{id}/request-review` (Req 34)
    - _Requirements: 30.1, 30.2, 31.1, 31.2, 32.1, 32.2, 33.1, 33.5, 34.1, 34.4, 35.1, 35.7, 36.3_

  - [x] 13.3 Implement Staff tracking, breaks, and time analytics
    - `StaffLocationMap.tsx` — Google Maps embed with staff pins, fetches `GET /staff/locations` every 30 seconds, pin tooltip: staff name, current appointment, time elapsed (Req 41)
    - Staff panel: show for each active staff member: current appointment, time elapsed, estimated time remaining (Req 41)
    - `BreakButton.tsx` — "Take Break" with type selector (Lunch, Gas, Personal, Other), creates blocked calendar slot, adjusts subsequent appointment ETAs (Req 42)
    - Display calculated durations (travel_time, job_duration, total_time) on completed appointment detail view (Req 37)
    - _Requirements: 37.3, 41.3, 41.4, 42.1, 42.4_

  - [x] 13.4 Write frontend unit test for calendar event label format
    - Test calendar event label is formatted as "{Staff Name} - {Job Type}" (P31)
    - **Property 31: Calendar event label format**
    - **Validates: Requirements 28.1**
    - _Requirements: 28.3_

- [x] 14. Frontend: Invoice Enhancements
  - [x] 14.1 Implement Invoice bulk notify and PDF download
    - `BulkNotify.tsx` — "Select All" checkbox + "Bulk Notify" button with notification type selection (REMINDER, PAST_DUE, LIEN_WARNING, UPCOMING_DUE), calls `POST /invoices/bulk-notify`, display summary (Req 38)
    - Add "Download PDF" button to Invoice_Detail_View, calls `POST /invoices/{id}/generate-pdf` or `GET /invoices/{id}/pdf`, triggers browser download (Req 80)
    - _Requirements: 38.2, 80.5, 80.6_

- [x] 15. Frontend: New Dashboard Pages (Sales, Accounting, Marketing, Communications)
  - [x] 15.1 Implement Sales Dashboard page at `/sales`
    - `SalesDashboard.tsx` — four pipeline cards: Needs Estimate, Pending Approval, Needs Follow-Up, Revenue Pipeline. Conversion funnel chart (Recharts). Click-through to filtered lists (Req 47)
    - `EstimateBuilder.tsx` — multi-step form: select template or start blank → add/edit line items with material + labor costs → create Good/Better/Best tiers → apply promotional discount → preview + send. Totals auto-calculate (Req 48)
    - `MediaLibrary.tsx` — grid/list toggle, filter by category + media type, upload with drag-drop, attach to estimates (Req 49)
    - `DiagramBuilder.tsx` — Excalidraw embed or custom canvas, irrigation component icon palette, background image import, save as PNG to media library linked to estimate (Req 50)
    - `FollowUpQueue.tsx` — DataTable of estimates with upcoming follow-ups: customer, estimate total, days since sent, next follow-up date, promotion attached (Req 51)
    - _Requirements: 47.1, 47.2, 47.4, 47.5, 48.4, 48.5, 48.6, 49.4, 50.1, 50.2, 50.3, 50.4, 50.5, 51.6_

  - [x] 15.2 Implement Accounting Dashboard page at `/accounting`
    - `AccountingDashboard.tsx` — top-level metrics cards: YTD Revenue, YTD Expenses, YTD Profit, Profit Margin %. Date range picker (month/quarter/custom). Sections: Pending Invoices, Past Due Invoices (Req 52)
    - `ExpenseTracker.tsx` — DataTable with CRUD, create form: category dropdown, description, amount, date, vendor, job link (optional), receipt upload. Receipt upload triggers OCR extraction → pre-populates amount/vendor/category (Req 53, 60)
    - `SpendingChart.tsx` — Recharts pie/bar chart for expense category breakdown (Req 53)
    - `TaxPreparation.tsx` — table of tax-relevant categories with YTD totals, revenue by job type, "Export CSV" button (Req 59)
    - `TaxProjection.tsx` — what-if form: input hypothetical revenue/expenses → see projected tax impact (Req 61)
    - `ReceiptCapture.tsx` — photo upload + OCR amount extraction (Req 60)
    - `ConnectedAccounts.tsx` — Plaid Link integration button, list of connected accounts with last sync timestamp, transaction review queue (Req 62)
    - `AuditLog.tsx` — paginated audit log section showing recent administrative actions (Req 74)
    - _Requirements: 52.1, 52.2, 52.3, 52.4, 52.6, 53.4, 53.7, 59.1, 59.4, 60.1, 60.3, 61.1, 61.3, 62.1, 62.5, 62.6, 74.4_

  - [x] 15.3 Implement Marketing Dashboard page at `/marketing`
    - `MarketingDashboard.tsx` — Lead Sources chart (Recharts bar), Conversion Funnel (stepped funnel visualization), Key Metrics cards (total leads, conversion rate, avg time to conversion, top source), Advertising Channels table (Req 63)
    - `CampaignManager.tsx` — campaign list with status badges, create form: name, type (Email/SMS/Both), audience filter builder, body editor, schedule picker, send button with confirmation, stats view: sent/delivered/failed/bounced/opted_out (Req 45)
    - `BudgetTracker.tsx` — budget vs actual grouped bar chart by channel, CRUD for budget entries (Req 64)
    - `QRCodeGenerator.tsx` — form: target URL + campaign name, preview QR code, download PNG button, UTM params auto-appended (Req 65)
    - `CACChart.tsx` — customer acquisition cost per channel comparison chart (Req 58)
    - `ConversionFunnel.tsx` — lead conversion visualization (Req 63)
    - _Requirements: 45.9, 58.3, 63.1, 63.2, 63.3, 63.4, 63.6, 64.3, 64.4, 65.2, 65.4_

  - [x] 15.4 Implement Communications page at `/communications` with inbound and outbound tabs
    - `CommunicationsQueue.tsx` — "Needs Attention" tab: list of unaddressed inbound messages with customer name, channel, content preview, timestamp. "Mark as Addressed" button calls `PATCH /communications/{id}/address` (Req 4)
    - `SentMessagesLog.tsx` — "Sent Messages" tab: paginated DataTable of outbound notifications from `sent_messages`. Columns: recipient name, phone, message type, content preview (80 chars), delivery status badge (delivered=green, sent=blue, pending=yellow, failed=red with error tooltip), sent_at. Filters: message type dropdown, delivery status dropdown, date range, search. Fetches `GET /sent-messages` (Req 82)
    - _Requirements: 4.3, 82.1, 82.2, 82.3, 82.5, 82.6_

  - [x] 15.5 Implement Customer Portal pages (public, no auth)
    - `EstimateReview.tsx` — clean, mobile-responsive page: company logo, estimate details, line items table, tier options (if multi-tier), total with discount, "Approve" and "Reject" buttons. Reject shows optional reason textarea (Req 16)
    - `ContractSigning.tsx` — contract body with template variables resolved, signature pad (canvas-based), "Sign" button records electronic signature with timestamp/IP/user-agent (Req 16)
    - `ApprovalConfirmation.tsx` — thank you page after approval/signing, shows next steps, no internal IDs exposed (Req 16, 78)
    - `InvoicePortal.tsx` — mobile-responsive public invoice page: company branding (logo, name, address, phone from business_settings), invoice number, date, due date, line items table, total amount, amount paid, balance remaining, payment status badge. "Pay Now" button (Stripe link if balance > 0) or "Paid in Full" confirmation. Single-column layout on mobile. No internal IDs. Expired tokens (>90 days) show 410 message with contact info (Req 84)
    - _Requirements: 16.7, 84.3, 84.4, 84.5, 84.6, 84.8, 84.9_

  <!-- - [~] 15.6 Implement Public AI Chat Widget
    - Chat widget component: message input, AI response display, session management via session_id, calls `POST /api/v1/chat/public` (Req 43)
    - _Requirements: 43.1, 43.2, 43.3_ -->

  - [x] 15.7 Implement Estimate Detail page at `/estimates/{id}`
    - `EstimateDetail.tsx` — admin-side estimate detail page showing: estimate number, customer name + contact info, creation date, status badge (color-coded), valid_until, line items table with quantities/prices/totals, tier options, subtotal, discount, total. "Activity Timeline" section showing chronological events: created, sent, viewed, approved/rejected (with timestamps + actor) and all follow-up notifications (with status). Action buttons: "Edit" (draft), "Send/Resend" (draft/sent), "Cancel" (non-terminal), "Create Job" (approved). Linked documents section: estimate PDF, contracts, media items (Req 83)
    - `EstimateList.tsx` — filtered DataTable for pipeline views (linked from SalesDashboard pipeline cards and FollowUpQueue rows). Columns: estimate number, customer, total, status badge, days since sent, next follow-up. Click row → navigates to EstimateDetail (Req 83)
    - Link to EstimateDetail from: SalesDashboard pipeline cards, FollowUpQueue rows, Lead detail AttachmentPanel, Appointment EstimateCreator confirmation
    - _Requirements: 83.1, 83.2, 83.3, 83.4, 83.5, 83.6, 83.7_

  - [x] 15.8 Implement Settings page enhancements at `/settings`
    - `BusinessInfo.tsx` — "Business Information" section: editable fields for company_name, company_address, company_phone, company_email, company_logo_url (with image upload to S3), company_website. Reads/writes via `GET/PATCH /settings` (Req 87)
    - `InvoiceDefaults.tsx` — "Invoice Defaults" section: default_payment_terms_days (number, default 30), late_fee_percentage (number), lien_warning_days (number, default 45), lien_filing_days (number, default 120) (Req 87)
    - `NotificationPrefs.tsx` — "Notification Preferences" section: day_of_reminder_time (time picker, default 7:00 AM CT), sms_time_window_start (time picker, default 8:00 AM), sms_time_window_end (time picker, default 9:00 PM), enable_delay_notifications (toggle) (Req 87)
    - `EstimateDefaults.tsx` — "Estimate Defaults" section: default_valid_days (number, default 30), follow_up_intervals_days (comma-separated input, default "3,7,14,21"), enable_auto_follow_ups (toggle) (Req 87)
    - _Requirements: 87.3, 87.4, 87.5, 87.6_

  - [x] 15.9 Apply mobile-responsive design to all staff field components
    - Update `StaffWorkflowButtons.tsx` — full-width stacked buttons (min-height 48px, touch target ≥44px) on screens < 768px (Req 86)
    - Update `PaymentCollector.tsx` — single-column layout on mobile, large inputs (min-height 44px), full-width submit (Req 86)
    - Update `AppointmentNotes.tsx` — full-width upload area with `accept="image/*;capture=camera"` (Req 86)
    - Update `AppointmentDetail.tsx` — single-column stacked layout on mobile, collapsible sections, prominent "Get Directions" button with `tel:`/`maps:` URL schemes (Req 86)
    - Update `InlineCustomerPanel.tsx` — full-screen bottom sheet (height: 90vh) on mobile instead of side panel (Req 86)
    - Update all modal dialogs (JobSelector, PaymentCollector, InvoiceCreator, EstimateCreator) — full-screen overlays on mobile with sticky close header (Req 86)
    - Add Tailwind responsive breakpoints: `md:` prefix for desktop layouts, base styles for mobile-first
    - _Requirements: 86.1, 86.2, 86.3, 86.4, 86.5, 86.6, 86.7, 86.8_

- [x] 16. Frontend: Navigation and Route Registration
  - [x] 16.1 Register all new routes and navigation items
    - Add navigation items to main sidebar: Sales (`/sales`), Accounting (`/accounting`), Marketing (`/marketing`), Communications (`/communications`) with active state highlighting
    - Register all new frontend routes in router configuration: `/sales`, `/accounting`, `/marketing`, `/communications`, `/estimates/:id`, `/portal/estimates/:token`, `/portal/contracts/:token`, `/portal/invoices/:token`
    - Register all new backend routers in `main.py` with appropriate prefixes and tags
    - Redirect `/work-requests` to `/leads` (Req 19)
    - _Requirements: 19.2, 66.1, 66.2, 66.3, 66.4, 83.1, 84.3_

- [x] 17. Checkpoint — Frontend complete
  - Ensure all frontend components render, all frontend unit tests pass, navigation works, ask the user if questions arise.

- [x] 18. Background Jobs: Scheduled Tasks
  - [x] 18.1 Implement all background jobs in scheduler
    - `send_day_of_reminders` — Daily 7:00 AM CT: send appointment reminders for today's appointments (Req 39)
    - `send_invoice_reminders` — Daily 8:00 AM CT: pre-due (3 days), past-due (weekly), lien (30 days) (Req 54, 55)
    - `check_estimate_approvals` — Hourly: route unapproved estimates >4hrs to leads pipeline (Req 32)
    - `process_estimate_follow_ups` — Hourly: send scheduled follow-up notifications (Req 51)
    - `check_appointment_delays` — Every 15 min: detect appointments running >15min past scheduled end, send delay notifications (Req 39)
    - `send_scheduled_campaigns` — Every 5 min: send campaigns with scheduled_at in the past (Req 45)
    - `process_automation_rules` — Daily 6:00 AM CT: evaluate recurring campaign automation rules (Req 45)
    - `sync_transactions` — Daily 2:00 AM CT: fetch new transactions from Plaid-connected accounts (Req 62)
    - All jobs use existing APScheduler integration, each logs start/completion with structured logging
    - _Requirements: 32.7, 39.7, 45.7, 45.9, 45.10, 51.3, 54.1, 55.1, 62.3_

  - [x] 18.2 Write functional tests for background jobs
    - Test day-of reminder job sends to all same-day appointments
    - Test invoice reminder job sends pre-due, past-due, and lien notifications to correct invoices
    - Test estimate approval check routes unapproved estimates to leads
    - Test follow-up processing sends due follow-ups
    - Test campaign sender processes scheduled campaigns
    - _Requirements: 39.11, 54.7, 55.7_

- [x] 19. Checkpoint — Background jobs complete
  - Ensure all background jobs are registered, functional tests pass, ask the user if questions arise.

- [x] 20. Testing: Functional Tests (Real DB, Mocked External Services)
  - [x] 20.1 Write functional tests for customer operations
    - Test customer merge with FK reassignment (all related records moved to primary, duplicates soft-deleted)
    - Test customer photo upload, list, and delete against S3-compatible storage
    - _Requirements: 7.6, 9.8_

  - [x] 20.2 Write functional tests for lead operations
    - Test lead creation with full address fields
    - Test full tag lifecycle: creation → contact → estimate → approval
    - Test bulk outreach sends to multiple leads and returns correct summary counts
    - Test lead attachment upload, list, and delete
    - Test work request migration converts all existing work requests to leads
    - _Requirements: 12.7, 13.10, 14.7, 15.7, 19.8_

  - [x] 20.3 Write functional tests for estimate and portal operations
    - Test full flow: estimate creation → link generation → customer approval → lead tag update
    - Test estimate creation from template with customized line items
    - Test estimate follow-up lifecycle: estimate sent → follow-ups scheduled → customer approves → remaining cancelled
    - _Requirements: 16.9, 17.8, 51.8_

  - [x] 20.4 Write functional tests for appointment and schedule operations
    - Test appointment time update via PATCH endpoint
    - Test full flow: collect payment → invoice updated → customer payment history updated
    - Test invoice creation, payment link generation, and customer notification
    - Test estimate creation from appointment, customer notification, and approval flow
    - Test photo upload from appointment context links to both appointment and customer
    - Test full status transition chain with timestamp recording
    - _Requirements: 24.7, 30.8, 31.7, 32.9, 33.7, 35.9_

  - [x] 20.5 Write functional tests for invoice, campaign, and accounting operations
    - Test bulk notification sends to multiple invoices and returns correct summary
    - Test campaign creation, scheduling, and delivery to multiple recipients
    - Test expense CRUD with receipt upload
    - Test accounting summary returns correct aggregations from real invoice and expense data
    - Test audit log endpoint returns correctly filtered results
    - Test SentMessage record creation with lead_id linkage for SMS confirmation
    - Test invoice PDF generation stores file in S3 and updates document_url
    - Test appointment creation → no_show status transition succeeds in DB
    - _Requirements: 38.7, 45.12, 53.10, 52.8, 74.6, 81.10, 80.9, 79.8_

  - [x] 20.6 Write functional tests for marketing and remaining operations
    - Test lead source aggregation from real lead data
    - Test chat context includes service information and pricing
    - Test voice webhook endpoint processes call data and creates leads correctly
    - Test Stripe PaymentIntent creation with test mode
    - Test frontend can authenticate and make API calls using cookie-based auth
    - _Requirements: 63.8, 43.7, 44.8, 56.8, 71.7_

- [x] 21. Checkpoint — Functional tests complete
  - Ensure all functional tests pass with real DB, ask the user if questions arise.

- [x] 22. Testing: Integration Tests (Full System)
  - [x] 22.1 Write integration tests for external service interactions
    - Test S3 file upload/download round-trip (customer photos, lead attachments, media library)
    - Test Redis location storage and TTL expiry for staff tracking
    - Test end-to-end estimate portal flow: create estimate → send → customer opens portal → approves → lead tag updated → job created
    - _Requirements: 9.8, 41.6_

  - [x] 22.2 Write agreement flow regression test suite (`test_agreement_flow_preservation.py`)
    - Verify complete agreement flow end-to-end: tier retrieval → checkout session creation → webhook processing → agreement record creation → job generation → job-customer linkage
    - Verify no existing agreement-related model, service, or route has been modified
    - Verify agreement-generated jobs appear correctly in Job_List_View with all expected fields
    - Run BEFORE any migration and AFTER every major feature implementation
    - **Property 64: Agreement flow preservation invariant**
    - **Validates: Requirements 68.1, 68.2, 68.3, 68.4, 68.5**
    - _Requirements: 68.6, 68.7, 68.8, 68.10_

- [x] 23. Checkpoint — Integration tests complete
  - Ensure all integration tests pass with full system, ask the user if questions arise.

- [x] 24. Testing: Property-Based Tests (Hypothesis + fast-check)
  - [x] 24.1 Write backend property-based tests using Hypothesis
    - **Property 1: Seed cleanup preserves non-seed records** — `@settings(max_examples=100)` — Validates: Req 1.4
    - **Property 2: Token refresh extends session validity** — Validates: Req 2.1
    - **Property 3: Unaddressed communication count accuracy** — Validates: Req 4.2
    - **Property 4: Communication record round-trip** — Validates: Req 4.4
    - **Property 5: Pending invoice metrics correctness** — Validates: Req 5.1, 5.2
    - **Property 6: Job status category partitioning** — Validates: Req 6.1, 6.2
    - **Property 7: Duplicate detection finds matching records** — Validates: Req 7.1
    - **Property 8: Customer merge reassigns all related records** — Validates: Req 7.2
    - **Property 9: Internal notes round-trip** — Validates: Req 8.4
    - **Property 10: Customer photo lifecycle round-trip** — Validates: Req 9.2, 9.3, 9.4
    - **Property 11: File upload validation rejects invalid files** — Validates: Req 9.2, 15.1, 49.5, 75.3, 77.1
    - **Property 12: Customer invoice history correctly filtered and sorted** — Validates: Req 10.1, 10.3
    - **Property 13: Preferred service times round-trip** — Validates: Req 11.1, 11.2, 11.3, 11.4
    - **Property 14: Lead address fields round-trip** — Validates: Req 12.2
    - **Property 15: Zip code auto-populates city and state** — Validates: Req 12.5
    - **Property 16: Lead action tag state machine** — Validates: Req 13.2, 13.3, 13.4, 13.5, 13.6
    - **Property 17: Lead tag filtering returns only matching leads** — Validates: Req 13.8
    - **Property 18: Consent-gated bulk outreach with correct summary** — Validates: Req 14.1, 14.3, 14.4
    - **Property 19: Lead attachment lifecycle round-trip** — Validates: Req 15.1, 15.2, 15.3, 15.4
    - **Property 20: Portal estimate access by token** — Validates: Req 16.1, 78.1, 78.2
    - **Property 21: Estimate approval updates lead tag and invalidates token** — Validates: Req 16.2, 16.5, 78.4
    - **Property 22: Estimate template round-trip** — Validates: Req 17.1, 17.2, 17.3, 17.4, 17.5
    - **Property 23: Reverse flow — estimate creates lead** — Validates: Req 18.1, 18.2
    - **Property 24: Work request migration preserves all data** — Validates: Req 19.1, 19.5
    - **Property 25: Job notes and summary round-trip** — Validates: Req 20.1, 20.2
    - **Property 28: Appointment conflict detection on reschedule** — Validates: Req 24.2, 24.4, 24.5
    - **Property 29: Schedule lead time calculation** — Validates: Req 25.2, 25.3
    - **Property 30: Job filter returns only matching jobs** — Validates: Req 26.2, 26.3
    - **Property 32: Address auto-population from customer** — Validates: Req 29.1
    - **Property 33: Payment collection creates/updates invoice** — Validates: Req 30.3, 30.4, 30.5
    - **Property 34: Invoice pre-population from appointment** — Validates: Req 31.2, 31.4
    - **Property 35: Unapproved estimate auto-routing** — Validates: Req 32.4, 32.7
    - **Property 36: Appointment notes propagate to customer** — Validates: Req 33.2, 33.3
    - **Property 37: Google review consent and deduplication** — Validates: Req 34.2, 34.6
    - **Property 38: Appointment status transition state machine** — Validates: Req 35.1-35.6
    - **Property 39: Payment gate blocks completion** — Validates: Req 36.1, 36.2
    - **Property 40: Staff time duration calculations** — Validates: Req 37.1
    - **Property 41: Consent-gated bulk invoice notifications** — Validates: Req 38.1, 38.3, 38.4
    - **Property 42: All customer notifications are consent-gated** — Validates: Req 39.1-39.5, 39.8
    - **Property 43: Enriched appointment response** — Validates: Req 40.2
    - **Property 44: Staff location round-trip via Redis** — Validates: Req 41.1, 41.2
    - **Property 45: Break adjusts subsequent appointment ETAs** — Validates: Req 42.5
    - **Property 46: Chat escalation detection** — Validates: Req 43.3, 43.5
    - **Property 47: Voice webhook creates lead** — Validates: Req 44.3, 44.5
    - **Property 48: Campaign recipient filtering by consent** — Validates: Req 45.5, 45.6
    - **Property 49: SMS lead confirmation consent and time-window gated** — Validates: Req 46.1, 46.2
    - **Property 50: Sales pipeline metrics accuracy** — Validates: Req 47.2, 47.3
    - **Property 51: Estimate total calculation with tiers and discounts** — Validates: Req 48.4-48.7
    - **Property 52: Follow-up scheduling and cancellation** — Validates: Req 51.2, 51.5
    - **Property 53: Accounting summary calculation** — Validates: Req 52.2, 52.5
    - **Property 54: Expense category aggregation** — Validates: Req 53.3, 53.5
    - **Property 55: Automated invoice reminder scheduling** — Validates: Req 54.1-54.3, 55.1, 55.2
    - **Property 56: Per-job financial calculations** — Validates: Req 57.1, 57.2
    - **Property 57: Customer acquisition cost calculation** — Validates: Req 58.1, 58.2
    - **Property 58: Tax summary aggregation** — Validates: Req 59.1, 59.2
    - **Property 59: Tax estimation calculation** — Validates: Req 61.1-61.4
    - **Property 60: Plaid transaction auto-categorization** — Validates: Req 62.4
    - **Property 61: Lead source analytics and conversion funnel** — Validates: Req 63.2-63.5
    - **Property 62: Marketing budget vs actual spend** — Validates: Req 64.3, 64.4
    - **Property 63: QR code URL contains correct UTM parameters** — Validates: Req 65.1, 65.3
    - **Property 64: Agreement flow preservation invariant** — Validates: Req 68.1-68.5
    - **Property 65: Rate limiting enforces thresholds** — Validates: Req 69.1-69.3
    - **Property 66: Security headers present on all responses** — Validates: Req 70.1
    - **Property 67: Secure token storage in httpOnly cookies** — Validates: Req 71.1, 71.2
    - **Property 68: JWT secret validation at startup** — Validates: Req 72.1-72.4
    - **Property 69: Request size limit enforcement** — Validates: Req 73.1-73.3
    - **Property 70: Audit log entry creation** — Validates: Req 74.1, 74.2
    - **Property 71: Input validation rejects oversized and malformed input** — Validates: Req 75.1, 75.2, 75.4, 75.5
    - **Property 72: PII masking in log output** — Validates: Req 76.1-76.4
    - **Property 73: EXIF stripping removes GPS data** — Validates: Req 77.4
    - **Property 74: Pre-signed URLs expire** — Validates: Req 77.3
    - **Property 75: Portal responses exclude internal IDs** — Validates: Req 78.6
    - **Property 76: AppointmentStatus enum accepts all frontend values** — Validates: Req 79.1-79.3
    - **Property 77: Invoice PDF generation round-trip** — Validates: Req 80.1-80.4
    - **Property 78: SentMessage supports lead-only recipients** — Validates: Req 81.1-81.4
    - **Property 79: Outbound notification history correctly filtered and paginated** — Validates: Req 82.1-82.4
    - **Property 80: Estimate detail includes complete activity timeline** — Validates: Req 83.2, 83.3
    - **Property 81: Portal invoice access by token with correct data** — Validates: Req 84.2, 84.4, 84.5, 84.8, 84.9
    - **Property 82: 429 interceptor displays toast with retry time** — Validates: Req 85.1, 85.2
    - **Property 83: Staff workflow components are mobile-usable** — Validates: Req 86.1-86.4
    - **Property 84: Business settings round-trip and service consumption** — Validates: Req 87.2, 87.7, 87.8
    - _Requirements: All testing requirements across Req 1-87_

  - [x] 24.2 Write frontend property-based tests using fast-check
    - **Property 26: Job status simplification mapping** — all raw statuses map to exactly one simplified label, mapping is total — Validates: Req 21.1
    - **Property 27: Days Waiting calculation and Due By color logic** — correct day count, correct color for past/within-7-days/null/default — Validates: Req 22.4, 23.1-23.4
    - **Property 31: Calendar event label format** — "{Staff Name} - {Job Type}" for all appointments — Validates: Req 28.1
    - _Requirements: 21.5, 22.6, 23.5, 28.3_

- [x] 25. Checkpoint — Property-based tests complete
  - Ensure all 78 property-based tests pass, ask the user if questions arise.

- [x] 26. Testing: Comprehensive E2E Test Suite (agent-browser)
  - [x] 26.1 Create E2E test runner script and seed data cleanup verification
    - Create `scripts/e2e-tests.sh` — sequential execution of all agent-browser validation scripts, reports pass/fail for each, supports `--headed` flag for debugging
    - E2E test: navigate to `/customers`, `/staff`, `/jobs` and verify no demo names appear (Req 1)
    - E2E test: login, wait, perform action, verify session remains active without redirect (Req 2)
    - _Requirements: 1.7, 2.7, 67.1, 67.3, 67.4, 67.5_

  - [x] 26.2 Create E2E tests for Dashboard
    - E2E test: open `/dashboard`, click alert card, verify navigation to correct page with filter applied and highlight animation visible (Req 3)
    - E2E test: open `/dashboard`, verify Messages widget displays numeric count, click it, verify navigation to communications queue (Req 4)
    - E2E test: open `/dashboard`, verify Pending Invoices widget shows numeric count from invoice data (Req 5)
    - E2E test: open `/dashboard`, verify all six job status categories displayed with numeric counts (Req 6)
    - _Requirements: 3.8, 4.8, 5.5, 6.5, 67.2_

  - [x] 26.3 Create E2E tests for Customers
    - E2E test: navigate to customer with duplicates, verify "Potential Duplicates" section, perform merge (Req 7)
    - E2E test: navigate to customer detail, edit internal notes, save, verify persistence on reload (Req 8)
    - E2E test: navigate to customer detail, click Photos tab, upload test image, verify in grid, delete (Req 9)
    - E2E test: navigate to customer detail, click Invoice History tab, verify invoice records with status badges (Req 10)
    - E2E test: navigate to customer detail, edit preferred service times, save, verify persistence (Req 11)
    - E2E test: navigate to customer detail, view Payment Methods section, verify saved cards displayed (Req 56)
    - _Requirements: 7.7, 8.6, 9.9, 10.5, 11.6, 56.9, 67.2_

  - [x] 26.4 Create E2E tests for Leads
    - E2E test: open `/leads`, verify city displayed in list, click lead, verify full address fields editable (Req 12)
    - E2E test: open `/leads`, verify tag badges visible, filter by specific tag, verify filtered results (Req 13)
    - E2E test: open `/leads`, select multiple leads, click "Bulk Outreach", select template, send, verify summary (Req 14)
    - E2E test: open lead detail, upload test PDF as estimate attachment, verify in Attachments section, delete (Req 15)
    - E2E test: open portal estimate link, review estimate, click approve, verify approval confirmation (Req 16)
    - E2E test: open lead detail, click "Create Estimate", select template, modify line item, save, verify estimate appears (Req 17)
    - E2E test: verify estimate-pending lead appears in leads list with correct tag (Req 18)
    - E2E test: navigate to `/work-requests`, verify redirect to `/leads`, verify former work request data appears (Req 19)
    - _Requirements: 12.8, 13.11, 14.8, 15.8, 16.10, 17.9, 18.6, 19.9, 67.2_

  - [x] 26.5 Create E2E tests for Jobs
    - E2E test: open `/jobs`, verify summary column visible, click job, edit notes, save, verify persistence (Req 20)
    - E2E test: open `/jobs`, verify status filter shows simplified labels, verify job rows display simplified badges (Req 21)
    - E2E test: open `/jobs`, verify: Category column absent, Customer column shows names, Tags column shows badges, Days Waiting shows numeric counts (Req 22)
    - E2E test: open `/jobs`, verify "Due By" column displays dates with appropriate color coding (Req 23)
    - E2E test: open job detail, verify Financials section displays revenue, costs, profit (Req 57)
    - _Requirements: 20.7, 21.6, 22.7, 23.6, 57.5, 67.2_

  - [x] 26.6 Create E2E tests for Schedule and Staff Workflow
    - E2E test: open `/schedule`, drag appointment to new time slot, verify appointment at new time (Req 24)
    - E2E test: open `/schedule`, verify Lead Time indicator displays value (Req 25)
    - E2E test: open `/schedule`, click "Add Appointment", use job filter, select multiple jobs, verify appointments created (Req 26)
    - E2E test: open `/schedule`, click customer name, verify inline panel opens with details, verify URL unchanged (Req 27)
    - E2E test: open `/schedule`, verify calendar event labels contain staff name and job type (Req 28)
    - E2E test: open appointment creation form, select customer, verify address auto-populated (Req 29)
    - E2E test: open in-progress appointment, click "Collect Payment", select method, enter amount, submit, verify invoice updates (Req 30)
    - E2E test: open appointment, click "Create Invoice", verify pre-populated fields, submit, verify in invoice list (Req 31)
    - E2E test: open appointment, click "Create Estimate", select template, submit, verify estimate created (Req 32)
    - E2E test: open appointment, add notes, save, verify notes appear on customer detail page (Req 33)
    - E2E test: open completed appointment, verify "Request Google Review" button visible (Req 34)
    - E2E test: open confirmed appointment, click "On My Way" → verify status, click "Job Started" → verify, click "Job Complete" → verify final status (Req 35)
    - E2E test: open in-progress appointment without payment, attempt "Job Complete", verify blocking message (Req 36)
    - E2E test: open completed appointment, verify duration metrics displayed (Req 37)
    - E2E test: open appointment detail, verify all enriched fields including "Get Directions" button (Req 40)
    - E2E test: open `/schedule`, verify staff location map overlay visible with staff pins (Req 41)
    - E2E test: open `/schedule`, click "Take Break" for staff member, verify break appears as blocked slot (Req 42)
    - _Requirements: 24.8, 25.5, 26.6, 27.4, 28.3, 29.5, 30.9, 31.8, 32.10, 33.8, 34.8, 35.10, 36.7, 37.7, 40.6, 41.8, 42.7, 67.2_

  - [x] 26.7 Create E2E tests for Invoices
    - E2E test: open `/invoices`, select multiple invoices, click "Bulk Notify", select "Past Due", send, verify summary (Req 38)
    - E2E test: open `/invoices`, verify reminder status indicators visible on invoices with automated reminders (Req 54)
    - E2E test: open invoice detail, click "Download PDF", verify file download initiated (Req 80)
    - _Requirements: 38.8, 54.8, 80.10, 67.2_

  - [x] 26.8 Create E2E tests for Customer Notifications
    - E2E test: open confirmed appointment, click "On My Way", verify notification log shows "on my way" notification queued (Req 39)
    - _Requirements: 39.12, 67.2_

  <!-- - [~] 26.9 Create E2E tests for AI Chat and Voice
    - E2E test: open public chat widget, send message, verify AI response received, type "speak to a person", verify escalation response (Req 43)
    - _Requirements: 43.8, 67.2_ -->

  - [x] 26.10 Create E2E tests for Sales Dashboard
    - E2E test: open `/sales`, verify all four pipeline sections display numeric counts, click "Pending Approval", verify individual estimates listed (Req 47)
    - E2E test: open estimate builder, add line items, create Good/Better/Best options, apply promotion, verify totals calculate correctly (Req 48)
    - E2E test: open media library, upload test image, verify in grid, filter by category (Req 49)
    - E2E test: open estimate builder, open diagram tool, draw basic shape, save, verify diagram in estimate (Req 50)
    - E2E test: open `/sales`, view Follow-Up Queue, verify estimates with scheduled follow-ups listed (Req 51)
    - _Requirements: 47.8, 48.10, 49.7, 50.7, 51.9, 67.2_

  - [x] 26.11 Create E2E tests for Accounting Dashboard
    - E2E test: open `/accounting`, verify YTD Revenue, Pending Invoices, Past Due sections display numeric values, change date range filter, verify metrics update (Req 52)
    - E2E test: open `/accounting`, navigate to expenses, create new expense with category and amount, verify in list and spending chart updates (Req 53)
    - E2E test: open `/accounting`, navigate to Tax Preparation, verify category totals displayed (Req 59)
    - E2E test: open expense creation form, upload receipt image, verify amount field pre-populated (Req 60)
    - E2E test: open `/accounting`, view Estimated Tax Due widget, open What-If Projections, enter hypothetical expense, verify projected tax impact updates (Req 61)
    - E2E test: open `/accounting`, navigate to Connected Accounts, verify section displayed (Req 62)
    - E2E test: perform admin action, navigate to audit log, verify action appears (Req 74)
    - _Requirements: 52.9, 53.11, 59.6, 60.7, 61.6, 62.8, 74.7, 67.2_

  - [x] 26.12 Create E2E tests for Marketing Dashboard
    - E2E test: open `/marketing`, verify Lead Sources chart displayed, verify Conversion Funnel shows stage counts, change date range filter (Req 63)
    - E2E test: open `/marketing/campaigns`, create new campaign, select audience, schedule, verify in list with SCHEDULED status (Req 45)
    - E2E test: open `/marketing`, view Budget vs Actual chart, create new budget entry, verify in chart (Req 64)
    - E2E test: open `/marketing`, navigate to QR Codes, generate QR code, verify download link available (Req 65)
    - E2E test: open `/marketing`, verify CAC per channel displayed (Req 58)
    - _Requirements: 45.13, 58.6, 63.9, 64.6, 65.6, 67.2_

  - [x] 26.13 Create E2E tests for Navigation, Security, and Portal
    - E2E test: open application, verify all navigation items visible in sidebar (Sales, Accounting, Marketing, Communications), click each, verify correct page loads (Req 66)
    - E2E test: rapidly submit form, verify rate limit message appears (Req 69)
    - E2E test: load application, verify no console security warnings related to missing headers (Req 70)
    - E2E test: login, verify no auth token in localStorage (`eval "localStorage.getItem('auth_token')"`), verify authenticated API calls succeed (Req 71)
    - E2E test: open portal link, verify estimate content displayed, verify no internal IDs visible in page source (Req 78)
    - _Requirements: 66.5, 69.6, 70.5, 71.8, 78.9, 67.2_

  - [x] 26.14 Create E2E test for Agreement Flow Preservation
    - E2E test: navigate to service package purchase flow, verify tier selection functional, verify checkout redirect works, verify existing agreements display correctly on customer detail page (Req 68)
    - _Requirements: 68.9, 67.2_

  - [x] 26.15 Create E2E test for SMS lead confirmation flow
    - E2E test: create a lead via the leads form, verify SMS confirmation is logged (Req 46)
    - _Requirements: 46.7_

  - [x] 26.16 Create E2E tests for Outbound Notification History
    - E2E test: navigate to `/communications`, click "Sent Messages" tab, verify outbound messages displayed with delivery status badges and timestamps (Req 82)
    - E2E test: navigate to a customer detail page, click "Messages" tab, verify outbound messages for that customer are displayed (Req 82)
    - _Requirements: 82.7, 82.8, 67.2_

  - [x] 26.17 Create E2E tests for Estimate Detail
    - E2E test: open `/sales`, click a pipeline card, click an estimate row, verify EstimateDetail page shows line items, status badge, and activity timeline (Req 83)
    - E2E test: open an estimate detail, click "Resend", verify status updates and follow-up is scheduled (Req 83)
    - _Requirements: 83.8, 83.9, 67.2_

  - [x] 26.18 Create E2E tests for Customer Invoice Portal
    - E2E test: open a portal invoice link `/portal/invoices/{token}`, verify invoice content displayed (company branding, line items, total, balance), verify "Pay Now" button present, verify no internal IDs in page source (Req 84)
    - _Requirements: 84.12, 67.2_

  - [x] 26.19 Create E2E tests for Rate Limit Error Handling
    - E2E test: rapidly submit a form, verify a toast notification appears with "Too many requests" message and wait time (Req 85)
    - _Requirements: 85.6, 85.7, 67.2_

  - [x] 26.20 Create E2E tests for Mobile Staff Views
    - E2E test: set viewport to mobile (375x812), open an appointment detail, verify all workflow buttons are visible and full-width, click "On My Way", verify status updates (Req 86)
    - E2E test: set viewport to mobile, open inline customer panel, verify it renders as full-screen bottom sheet (Req 86)
    - _Requirements: 86.9, 86.10, 67.2_

  - [x] 26.21 Create E2E tests for Settings Page
    - E2E test: navigate to `/settings`, edit company name in Business Information section, save, reload page, verify change persists (Req 87)
    - E2E test: navigate to `/settings`, modify default_payment_terms_days, save, create a new invoice, verify due date reflects the new default (Req 87)
    - _Requirements: 87.10, 87.11, 67.2_

- [x] 27. Final Checkpoint — All tests pass
  - Ensure all unit, functional, integration, property-based, and E2E tests pass. Run quality checks: `uv run ruff check --fix src/ && uv run mypy src/ && uv run pyright src/ && uv run pytest -v`. Ask the user if questions arise.

## Notes

- **ALL work happens on the `dev` branch only** — no commits, pushes, or merges to `main` until all 87 requirements are verified and Admin approves
- All tasks are required — no optional markers
- Each task references specific requirements for traceability
- **Task 0 (Dependency Setup) must be completed FIRST** — all subsequent phases depend on the packages, infrastructure, and environment variables it installs
- Before starting Task 0, verify you are on the `dev` branch: `git checkout dev`
- Property-based tests validate universal correctness properties (P1-P84)
- Checkpoints ensure incremental validation between phases (9 checkpoints total including Task 0.8)
- The service agreement flow is OFF-LIMITS — regression tests in task 22.2 verify preservation
- Task 0.7 runs the agreement flow regression baseline BEFORE any code changes, establishing the pre-change passing state
- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / PostgreSQL 15+ / Redis 7+
- Frontend: React 19 / TypeScript 5.9 / Vite 7 / TanStack Query v5 / Tailwind 4 / Radix UI + shadcn
- New infrastructure: Redis 7+ (rate limiting + caching), S3-compatible storage (MinIO for dev, AWS S3 for prod)
- New external services: Plaid (banking integration), Vapi (voice AI)
- New libraries: WeasyPrint (PDF), python-magic (file validation), Pillow (image processing), boto3 (S3), qrcode (QR generation), Excalidraw (diagrams), signature_pad (e-signatures), fast-check (frontend property tests)
- All services use LoggerMixin structured logging per code-standards.md
- All tests follow three-tier pattern: unit (@pytest.mark.unit), functional (@pytest.mark.functional), integration (@pytest.mark.integration)
- E2E tests use agent-browser with data-testid attributes for reliable element selection
