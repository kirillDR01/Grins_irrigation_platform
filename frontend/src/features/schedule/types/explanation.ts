/**
 * Schedule explanation and AI feature types.
 * Maps to backend schedule_explanation schemas.
 */

// =============================================================================
// Schedule Explanation Types
// =============================================================================

export interface StaffAssignmentSummary {
  staff_name: string;
  total_jobs: number;
  total_travel_minutes: number;
  first_job_start: string | null;
  last_job_end: string | null;
}

export interface ScheduleExplanationRequest {
  schedule_date: string;
  assignments: StaffAssignmentSummary[];
  unassigned_count: number;
  total_travel_minutes: number;
}

export interface ScheduleExplanationResponse {
  explanation: string;
  highlights: string[];
}

// =============================================================================
// Unassigned Job Explanation Types
// =============================================================================

export interface UnassignedJobExplanationRequest {
  job_id: string;
  customer_name: string;
  service_type: string;
  city: string | null;
  duration_minutes: number;
  schedule_date: string;
  available_staff: string[];
  reason: string;
}

export interface UnassignedJobExplanationResponse {
  explanation: string;
  suggestions: string[];
  alternative_dates: string[];
}

// =============================================================================
// Constraint Parsing Types
// =============================================================================

export type ConstraintType =
  | 'staff_time'
  | 'job_grouping'
  | 'staff_restriction'
  | 'geographic';

export interface ParsedConstraint {
  type: ConstraintType;
  description: string;
  staff_name?: string;
  time_start?: string;
  time_end?: string;
  job_type?: string;
  city?: string;
  validation_errors?: string[];
}

export interface ParseConstraintsRequest {
  constraint_text: string;
}

export interface ParseConstraintsResponse {
  constraints: ParsedConstraint[];
  unparseable_text: string | null;
}

// =============================================================================
// Jobs Ready to Schedule Types
// =============================================================================

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
}

export interface JobsReadyToScheduleResponse {
  jobs: JobReadyToSchedule[];
  total_count: number;
  by_city: Record<string, number>;
  by_job_type: Record<string, number>;
}

// =============================================================================
// Customer Search Types
// =============================================================================

export interface CustomerSearchResult {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
}
