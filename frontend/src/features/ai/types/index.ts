/**
 * AI Assistant TypeScript types matching backend schemas
 * 
 * This file defines all TypeScript types for AI Assistant Integration
 * matching the Pydantic schemas in src/grins_platform/schemas/ai.py
 * and src/grins_platform/schemas/sms.py
 */

// =============================================================================
// Enums
// =============================================================================

export enum AIActionType {
  SCHEDULE_GENERATION = 'schedule_generation',
  JOB_CATEGORIZATION = 'job_categorization',
  COMMUNICATION_DRAFT = 'communication_draft',
  ESTIMATE_GENERATION = 'estimate_generation',
  BUSINESS_QUERY = 'business_query',
}

export enum AIEntityType {
  JOB = 'job',
  CUSTOMER = 'customer',
  APPOINTMENT = 'appointment',
  SCHEDULE = 'schedule',
  COMMUNICATION = 'communication',
  ESTIMATE = 'estimate',
}

export enum UserDecision {
  APPROVED = 'approved',
  REJECTED = 'rejected',
  MODIFIED = 'modified',
  PENDING = 'pending',
}

export enum MessageType {
  APPOINTMENT_CONFIRMATION = 'appointment_confirmation',
  APPOINTMENT_REMINDER = 'appointment_reminder',
  ON_THE_WAY = 'on_the_way',
  ARRIVAL = 'arrival',
  COMPLETION = 'completion',
  INVOICE = 'invoice',
  PAYMENT_REMINDER = 'payment_reminder',
  CUSTOM = 'custom',
}

export enum DeliveryStatus {
  PENDING = 'pending',
  SCHEDULED = 'scheduled',
  SENT = 'sent',
  DELIVERED = 'delivered',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// =============================================================================
// Chat Types
// =============================================================================

export interface AIChatRequest {
  message: string;
  session_id?: string;
}

export interface AIChatResponse {
  message: string;
  session_id: string;
  tokens_used: number;
  is_streaming?: boolean;
}

// =============================================================================
// Schedule Generation Types
// =============================================================================

export interface ScheduledJob {
  job_id: string;
  customer_name: string;
  address: string;
  job_type: string;
  estimated_duration_minutes: number;
  time_window_start: string;
  time_window_end: string;
  notes?: string;
}

export interface StaffAssignment {
  staff_id: string;
  staff_name: string;
  jobs: ScheduledJob[];
  total_jobs: number;
  total_minutes: number;
}

export interface ScheduleWarning {
  warning_type: string;
  message: string;
  job_id?: string;
  staff_id?: string;
}

export interface ScheduleDay {
  date: string;
  staff_assignments: StaffAssignment[];
  warnings: ScheduleWarning[];
}

export interface ScheduleSummary {
  total_jobs: number;
  total_staff: number;
  total_days: number;
  jobs_per_day_avg: number;
  warnings_count: number;
}

export interface ScheduleGenerateRequest {
  target_date: string;
  job_ids?: string[];
}

export interface GeneratedSchedule {
  schedule_id: string;
  days: ScheduleDay[];
  summary: ScheduleSummary;
  ai_explanation: string;
  confidence_score: number;
}

export interface ScheduleGenerateResponse {
  audit_id: string;
  schedule: Record<string, unknown>;
  confidence_score: number;
  warnings: string[];
}

// =============================================================================
// Job Categorization Types
// =============================================================================

export interface JobCategorization {
  job_id: string;
  suggested_category: string;
  suggested_job_type: string;
  suggested_price?: string;
  confidence_score: number;
  ai_notes?: string;
  requires_review: boolean;
}

export interface CategorizationSummary {
  total_jobs: number;
  ready_to_schedule: number;
  requires_review: number;
  avg_confidence: number;
}

export interface JobCategorizationRequest {
  description: string;
  customer_history?: Record<string, unknown>[];
}

export interface JobCategorizationResponse {
  audit_id: string;
  category: string;
  confidence_score: number;
  reasoning: string;
  suggested_services: string[];
  needs_review: boolean;
}

// =============================================================================
// Communication Draft Types
// =============================================================================

export interface CommunicationDraft {
  draft_id: string;
  customer_id: string;
  customer_name: string;
  customer_phone: string;
  message_type: MessageType;
  message_content: string;
  ai_notes?: string;
  is_slow_payer?: boolean;
}

export interface CommunicationDraftRequest {
  customer_id?: string;
  job_id?: string;
  appointment_id?: string;
  message_type: MessageType;
}

export interface CommunicationDraftResponse {
  draft: CommunicationDraft;
  audit_log_id: string;
}

// =============================================================================
// Estimate Generation Types
// =============================================================================

export interface SimilarJob {
  job_id: string;
  job_type: string;
  zone_count: number;
  final_amount: string;
  completed_at: string;
}

export interface EstimateBreakdown {
  materials: string;
  labor: string;
  equipment: string;
  margin: string;
  total: string;
}

export interface EstimateGenerateRequest {
  job_id: string;
  zone_count?: number;
  include_similar_jobs?: boolean;
}

export interface EstimateGenerateResponse {
  job_id: string;
  zone_count: number;
  similar_jobs: SimilarJob[];
  breakdown: EstimateBreakdown;
  recommended_price: string;
  ai_recommendation: string;
  requires_site_visit: boolean;
  confidence_score: number;
  audit_log_id: string;
}

// Frontend-specific estimate response type for UI components
export interface EstimateSimilarJob {
  service_type: string;
  zone_count: number;
  final_price: number;
  similarity_score: number;
}

export interface EstimateBreakdownNumeric {
  materials: number;
  labor: number;
  equipment: number;
  margin: number;
}

export interface EstimateResponse {
  estimated_price: number;
  estimated_zones: number;
  confidence_score: number;
  breakdown: EstimateBreakdownNumeric;
  similar_jobs: EstimateSimilarJob[];
  recommendation?: string;
  ai_notes?: string;
}

// =============================================================================
// AI Usage and Audit Types
// =============================================================================

export interface AIUsageResponse {
  user_id: string;
  usage_date: string;
  request_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  estimated_cost_usd: number;
  daily_limit: number;
  remaining_requests: number;
}

export interface AIAuditLogEntry {
  id: string;
  action_type: AIActionType;
  entity_type: AIEntityType;
  entity_id?: string;
  ai_recommendation: Record<string, unknown>;
  confidence_score?: number;
  user_decision?: UserDecision;
  decision_at?: string;
  request_tokens?: number;
  response_tokens?: number;
  estimated_cost_usd?: number;
  created_at: string;
}

export interface AIAuditLogResponse {
  entries: AIAuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AIDecisionRequest {
  decision: UserDecision;
  modified_data?: Record<string, unknown>;
}

// =============================================================================
// SMS Types
// =============================================================================

export interface SMSSendRequest {
  customer_id: string;
  phone: string;
  message: string;
  message_type: MessageType;
  sms_opt_in?: boolean;
  job_id?: string;
  appointment_id?: string;
}

export interface SMSSendResponse {
  success: boolean;
  message_id: string;
  twilio_sid?: string;
  status: string;
}

export interface CommunicationsQueueItem {
  id: string;
  customer_id: string;
  message_type: string;
  message_content: string;
  recipient_phone: string;
  delivery_status: string;
  scheduled_for?: string;
  created_at: string;
}

export interface CommunicationsQueueResponse {
  items: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

export interface BulkRecipient {
  customer_id: string;
  phone: string;
  sms_opt_in?: boolean;
}

export interface BulkSendRequest {
  recipients: BulkRecipient[];
  message: string;
  message_type: MessageType;
}

export interface BulkSendResponse {
  total: number;
  success_count: number;
  failure_count: number;
  results: Record<string, unknown>[];
}
