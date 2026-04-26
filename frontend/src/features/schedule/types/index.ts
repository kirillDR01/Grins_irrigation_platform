/**
 * Schedule/Appointment types for the frontend.
 * Maps to backend appointment schemas.
 */

// --- Customer Tag types (Requirements 12.1, 17.2) ---
export type TagTone = 'neutral' | 'blue' | 'green' | 'amber' | 'violet';
export type TagSource = 'manual' | 'system';

export interface CustomerTag {
  id: string;
  customer_id: string;
  label: string;
  tone: TagTone;
  source: TagSource;
  created_at: string;
}

export interface TagSaveRequest {
  tags: Array<{ label: string; tone: TagTone }>;
}

export interface TagSaveResponse {
  tags: CustomerTag[];
  added: number;
  removed: number;
}

export type AppointmentStatus =
  | 'pending'
  | 'draft'
  | 'scheduled'
  | 'confirmed'
  | 'en_route'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'no_show';

/**
 * Per-appointment reply-state summary for calendar badges (gap-12).
 * Populated by GET /api/v1/appointments/weekly only; daily / list
 * endpoints leave it undefined.
 */
export interface ReplyState {
  has_pending_reschedule: boolean;
  has_no_reply_flag: boolean;
  customer_opted_out: boolean;
  has_unrecognized_reply: boolean;
  last_reminder_sent_at: string | null;
}

export interface Appointment {
  id: string;
  job_id: string;
  staff_id: string;
  scheduled_date: string; // ISO date string (YYYY-MM-DD)
  time_window_start: string; // Time string (HH:MM:SS)
  time_window_end: string; // Time string (HH:MM:SS)
  status: AppointmentStatus;
  arrived_at: string | null;
  en_route_at: string | null;
  completed_at: string | null;
  notes: string | null;
  route_order: number | null;
  estimated_arrival: string | null;
  created_at: string;
  updated_at: string;
  // Extended fields for display (populated from relationships)
  job_type: string | null;
  customer_name: string | null;
  staff_name: string | null;
  // Service agreement indicator for calendar display (Smoothing Req 7.5)
  service_agreement_id: string | null;
  // gap-12: only the weekly endpoint sends this.
  reply_state?: ReplyState | null;
}

export interface AppointmentCreate {
  job_id: string;
  staff_id: string;
  scheduled_date: string;
  time_window_start: string;
  time_window_end: string;
  notes?: string;
}

export interface AppointmentUpdate {
  staff_id?: string;
  scheduled_date?: string;
  time_window_start?: string;
  time_window_end?: string;
  notes?: string;
  status?: AppointmentStatus;
  route_order?: number;
  estimated_arrival?: string;
}

export interface AppointmentListParams {
  page?: number;
  page_size?: number;
  status?: AppointmentStatus;
  staff_id?: string;
  job_id?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface AppointmentPaginatedResponse {
  items: Appointment[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DailyScheduleResponse {
  date: string;
  appointments: Appointment[];
  total_count: number;
}

export interface StaffDailyScheduleResponse {
  staff_id: string;
  staff_name: string;
  date: string;
  appointments: Appointment[];
  total_scheduled_minutes: number;
}

export interface WeeklyScheduleResponse {
  start_date: string;
  end_date: string;
  days: DailyScheduleResponse[];
  total_appointments: number;
}

// Calendar event type for FullCalendar integration
export interface CalendarEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  backgroundColor?: string;
  borderColor?: string;
  textColor?: string;
  extendedProps: {
    appointment: Appointment;
    status: AppointmentStatus;
    staffId: string;
    jobId: string;
  };
}

// Status display configuration
export const appointmentStatusConfig: Record<
  AppointmentStatus,
  { label: string; color: string; bgColor: string }
> = {
  pending: {
    label: 'Pending',
    color: 'text-yellow-800',
    bgColor: 'bg-yellow-100',
  },
  draft: {
    label: 'Draft',
    color: 'text-slate-600',
    bgColor: 'bg-slate-100',
  },
  scheduled: {
    label: 'Scheduled',
    color: 'text-purple-800',
    bgColor: 'bg-purple-100',
  },
  confirmed: {
    label: 'Confirmed',
    color: 'text-blue-800',
    bgColor: 'bg-blue-100',
  },
  en_route: {
    label: 'En Route',
    color: 'text-cyan-800',
    bgColor: 'bg-cyan-100',
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-orange-800',
    bgColor: 'bg-orange-100',
  },
  completed: {
    label: 'Completed',
    color: 'text-green-800',
    bgColor: 'bg-green-100',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-800',
    bgColor: 'bg-red-100',
  },
  no_show: {
    label: 'No Show',
    color: 'text-gray-800',
    bgColor: 'bg-gray-100',
  },
};


// =============================================================================
// Schedule Generation Types (Route Optimization)
// =============================================================================

export type GenerationStatus = 'idle' | 'generating' | 'completed' | 'failed';

export interface ScheduleJobAssignment {
  job_id: string;
  customer_name: string;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  service_type: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  travel_time_minutes: number;
  sequence_index: number;
}

export interface ScheduleStaffAssignment {
  staff_id: string;
  staff_name: string;
  start_lat: number | null;
  start_lng: number | null;
  jobs: ScheduleJobAssignment[];
  total_jobs: number;
  total_travel_minutes: number;
  first_job_start: string | null;
  last_job_end: string | null;
}

export interface UnassignedJobResponse {
  job_id: string;
  customer_name: string;
  service_type: string;
  job_type?: string;
  address?: string;
  reason: string;
}

export interface ScheduleGenerateRequest {
  schedule_date: string;
  timeout_seconds?: number;
  job_ids?: string[];
  preview_only?: boolean;
  constraints?: Array<{
    type: string;
    description: string;
    staff_name?: string;
    time_start?: string;
    time_end?: string;
    job_type?: string;
    city?: string;
  }>;
}

export interface ScheduleGenerateResponse {
  schedule_date: string;
  is_feasible: boolean;
  hard_score: number;
  soft_score: number;
  assignments: ScheduleStaffAssignment[];
  unassigned_jobs: UnassignedJobResponse[];
  total_jobs: number;
  total_assigned: number;
  total_travel_minutes: number;
  optimization_time_seconds: number;
}

export interface ScheduleCapacityResponse {
  schedule_date: string;
  total_staff: number;
  available_staff: number;
  total_capacity_minutes: number;
  scheduled_minutes: number;
  remaining_capacity_minutes: number;
  can_accept_more: boolean;
}

export interface ScheduleGenerationStatusResponse {
  date: string;
  status: GenerationStatus;
  last_generated_at: string | null;
  total_assignments: number;
  total_unassigned: number;
}


// =============================================================================
// Apply Schedule Types
// =============================================================================

export interface ApplyScheduleRequest {
  schedule_date: string;
  assignments: ScheduleStaffAssignment[];
}

export interface ApplyScheduleResponse {
  success: boolean;
  schedule_date: string;
  appointments_created: number;
  message: string;
  created_appointment_ids: string[];
}

// =============================================================================
// Schedule Explanation Types (for API)
// =============================================================================

// Re-export from explanation.ts for backward compatibility
export type {
  StaffAssignmentSummary,
  ScheduleExplanationRequest,
  ScheduleExplanationResponse,
  UnassignedJobExplanationRequest,
  UnassignedJobExplanationResponse,
  ConstraintType,
  ParsedConstraint,
  ParseConstraintsRequest as ParseConstraintsRequestAlt,
  ParseConstraintsResponse as ParseConstraintsResponseAlt,
} from './explanation';

// Keep these for backward compatibility with existing code
export interface ScheduleExplanationRequestLegacy {
  schedule_date: string;
  staff_assignments: Array<{
    staff_name: string;
    jobs: Array<{
      customer_name: string;
      service_type: string;
      city: string | null;
      start_time: string;
      end_time: string;
      travel_time_minutes: number;
    }>;
    total_travel_minutes: number;
  }>;
  unassigned_jobs: Array<{
    customer_name: string;
    service_type: string;
    reason: string;
  }>;
  total_travel_minutes: number;
}

export interface ScheduleExplanationResponseLegacy {
  explanation: string;
  key_decisions: string[];
  optimization_notes: string[];
}

export interface UnassignedJobExplanationRequestLegacy {
  job_id: string;
  customer_name: string;
  job_type: string;
  city: string | null;
  reason: string;
  schedule_date: string;
  available_staff: string[];
}

export interface UnassignedJobExplanationResponseLegacy {
  explanation: string;
  suggestions: string[];
  alternative_dates: string[];
}

export interface ParseConstraintsRequest {
  constraint_text: string;
  schedule_date: string;
}

export interface ParseConstraintsResponse {
  constraints: ParsedConstraintItem[];
  raw_text: string;
  unparseable_text?: string;
}

export interface ParsedConstraintItem {
  type: string;
  description: string;
  staff_name?: string;
  time_start?: string;
  time_end?: string;
  job_type?: string;
  city?: string;
  validation_errors: string[];
  is_valid?: boolean;
  validation_error?: string;
}

export interface JobReadyToSchedule {
  job_id: string;
  customer_id: string;
  customer_name: string;
  job_type: string;
  city: string;
  priority: string;
  estimated_duration_minutes: number;
  requires_equipment: string[];
  status: string;
  // Extended fields for pick-jobs page (Requirements: 4.1, 4.8, 4.9, 4.10)
  address?: string;
  customer_tags?: import('@/features/jobs/types').CustomerTag[];
  property_type?: 'residential' | 'commercial' | null;
  property_is_hoa?: boolean;
  property_is_subscription?: boolean;
  requested_week?: string;
  notes?: string;
  priority_level?: number;
}

export interface JobsReadyToScheduleResponse {
  jobs: JobReadyToSchedule[];
  total_count: number;
  by_city: Record<string, number>;
  by_job_type: Record<string, number>;
}

export interface CustomerSearchResult {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
}

// =============================================================================
// Schedule Clear Types
// =============================================================================

export interface ScheduleClearRequest {
  schedule_date: string;
  notes?: string;
}

export interface ScheduleClearResponse {
  audit_id: string;
  schedule_date: string;
  appointments_deleted: number;
  jobs_reset: number;
  cleared_at: string;
}

export interface ScheduleClearAuditResponse {
  id: string;
  schedule_date: string;
  appointment_count: number;
  cleared_at: string;
  cleared_by: string | null;
  notes: string | null;
}

export interface ScheduleClearAuditDetailResponse extends ScheduleClearAuditResponse {
  appointments_data: Record<string, unknown>[];
  jobs_reset: string[];
}

export interface ScheduleRestoreResponse {
  audit_id: string;
  schedule_date: string;
  appointments_restored: number;
  jobs_updated: number;
  restored_at: string;
}

// =============================================================================
// Staff Workflow Types (Req 30-36)
// =============================================================================

// =============================================================================
// Reschedule Request Types (Req 25)
// =============================================================================

export interface RescheduleRequestDetail {
  id: string;
  job_id: string;
  appointment_id: string;
  customer_id: string;
  customer_name: string;
  original_appointment_date: string | null;
  original_appointment_staff: string | null;
  requested_alternatives: Record<string, unknown> | null;
  raw_alternatives_text: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

// =============================================================================
// Needs-Review Queue (bughunt H-7)
// =============================================================================

/**
 * Row returned by ``GET /appointments/needs-review``. Bundles the minimum
 * appointment + customer fields required to render the no-reply review
 * queue on ``/schedule`` without a second customer round-trip.
 *
 * Validates: bughunt 2026-04-16 finding H-7.
 */
export interface NeedsReviewAppointment {
  id: string;
  job_id: string;
  staff_id: string;
  scheduled_date: string;
  time_window_start: string;
  time_window_end: string;
  status: AppointmentStatus;
  needs_review_reason: string | null;
  confirmation_sent_at: string | null;
  customer_id: string | null;
  customer_name: string | null;
  customer_phone: string | null;
}

export type PaymentMethod = 'credit_card' | 'cash' | 'check' | 'venmo' | 'zelle' | 'send_invoice' | 'stripe_terminal';

export interface CollectPaymentRequest {
  payment_method: PaymentMethod;
  amount: number;
  reference_number?: string;
}

export interface CollectPaymentResponse {
  id: string;
  appointment_id: string;
  payment_method: PaymentMethod;
  amount: number;
  reference_number: string | null;
  collected_at: string;
}

export interface CreateInvoiceFromAppointmentResponse {
  id: string;
  invoice_number: string;
  total_amount: number;
  status: string;
  payment_link: string | null;
}

export interface CreateEstimateFromAppointmentRequest {
  template_id?: string;
  line_items: Array<{
    item: string;
    description: string;
    unit_price: number;
    quantity: number;
  }>;
  notes?: string;
  valid_until?: string;
}

export interface CreateEstimateFromAppointmentResponse {
  id: string;
  status: string;
  total: number;
}

export interface RequestReviewResponse {
  success: boolean;
  message: string;
  already_requested: boolean;
}

// =============================================================================
// Staff Tracking, Breaks & Time Analytics Types (Req 37, 41, 42)
// =============================================================================

export interface StaffLocation {
  staff_id: string;
  staff_name: string;
  latitude: number;
  longitude: number;
  current_appointment: string | null;
  time_elapsed_minutes: number;
  updated_at: string;
}

export type BreakType = 'lunch' | 'gas' | 'personal' | 'other';

export interface StaffBreak {
  id: string;
  staff_id: string;
  appointment_id: string | null;
  start_time: string;
  end_time: string | null;
  break_type: BreakType;
}

export interface CreateBreakRequest {
  break_type: BreakType;
}

export interface StaffTimeAnalytics {
  staff_id: string;
  staff_name: string;
  avg_travel_time: number;
  avg_job_duration: number;
  avg_total_time: number;
  flagged: boolean;
}

// =============================================================================
// Appointment Communication Timeline (Gap 11)
// =============================================================================

export type TimelineEventKind =
  | 'outbound_sms'
  | 'inbound_reply'
  | 'reschedule_opened'
  | 'reschedule_resolved'
  | 'opt_out'
  | 'opt_in';

export interface TimelineEvent {
  id: string;
  kind: TimelineEventKind;
  occurred_at: string;
  summary: string;
  details: Record<string, unknown>;
  source_id: string | null;
}

export interface OptOutState {
  consent_given: boolean;
  recorded_at: string | null;
  method: string | null;
}

export interface PendingRescheduleRequest {
  id: string;
  job_id: string;
  appointment_id: string;
  customer_id: string;
  original_reply_id: string | null;
  requested_alternatives: Record<string, unknown> | null;
  raw_alternatives_text: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export interface AppointmentTimelineResponse {
  appointment_id: string;
  events: TimelineEvent[];
  pending_reschedule_request: PendingRescheduleRequest | null;
  needs_review_reason: string | null;
  opt_out: OptOutState | null;
  last_event_at: string | null;
}
