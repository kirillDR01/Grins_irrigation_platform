import type { BaseEntity, PaginationParams } from '@/core/api';
import { parseLocalDate } from '@/shared/utils/dateUtils';

// Job status enum matching backend
export type JobStatus =
  | 'to_be_scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

// Job category enum matching backend
export type JobCategory = 'ready_to_schedule' | 'requires_estimate';

// Job source enum matching backend
export type JobSource = 'website' | 'google' | 'referral' | 'phone' | 'partner';

// Display labels for job statuses
export type JobStatusLabel = 'To Be Scheduled' | 'In Progress' | 'Complete' | 'Cancelled';

// Customer tag types (Req 22)
export type CustomerTag = 'priority' | 'red_flag' | 'slow_payer' | 'new_customer';

// Job entity
export interface Job extends BaseEntity {
  customer_id: string;
  property_id: string | null;
  service_offering_id: string | null;
  service_agreement_id: string | null;
  job_type: string;
  category: JobCategory;
  status: JobStatus;
  description: string | null;
  summary: string | null;
  notes: string | null;
  estimated_duration_minutes: number | null;
  priority_level: number;
  weather_sensitive: boolean;
  staffing_required: number;
  equipment_required: string[] | null;
  materials_required: string[] | null;
  quoted_amount: number | null;
  final_amount: number | null;
  source: JobSource | null;
  source_details: Record<string, unknown> | null;
  payment_collected_on_site: boolean;
  target_start_date: string | null;
  target_end_date: string | null;
  requested_at: string | null;
  approved_at: string | null;  // Historical, no longer written
  scheduled_at: string | null;  // Historical, no longer written
  started_at: string | null;
  completed_at: string | null;
  closed_at: string | null;  // Historical, no longer written
  // Nested customer summary (Req 22)
  customer_name: string | null;
  customer_tags: CustomerTag[] | null;
}

// Per-job financials (Req 57)
export interface JobFinancials {
  job_id: string;
  quoted_amount: number | null;
  final_amount: number | null;
  total_paid: number;
  material_costs: number;
  labor_costs: number;
  total_costs: number;
  profit: number;
  profit_margin: number | null;
}

// Create job request
export interface JobCreate {
  customer_id: string;
  property_id?: string | null;
  service_offering_id?: string | null;
  job_type: string;
  description?: string | null;
  estimated_duration_minutes?: number | null;
  priority_level?: number;
  weather_sensitive?: boolean;
  staffing_required?: number;
  equipment_required?: string[] | null;
  materials_required?: string[] | null;
  quoted_amount?: number | null;
  source?: JobSource | null;
  source_details?: Record<string, unknown> | null;
}

// Update job request
export interface JobUpdate {
  property_id?: string | null;
  service_offering_id?: string | null;
  job_type?: string;
  category?: JobCategory;
  description?: string | null;
  summary?: string | null;
  notes?: string | null;
  estimated_duration_minutes?: number | null;
  priority_level?: number;
  weather_sensitive?: boolean;
  staffing_required?: number;
  equipment_required?: string[] | null;
  materials_required?: string[] | null;
  quoted_amount?: number | null;
  final_amount?: number | null;
  source?: JobSource | null;
  source_details?: Record<string, unknown> | null;
  payment_collected_on_site?: boolean;
}

// Job status update request
export interface JobStatusUpdate {
  status: JobStatus;
  notes?: string | null;
}

// Job list params
export interface JobListParams extends PaginationParams {
  status?: JobStatus;
  category?: JobCategory;
  customer_id?: string;
  property_id?: string;
  service_offering_id?: string;
  priority_level?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  has_service_agreement?: boolean;
  target_date_from?: string;
  target_date_to?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Status display configuration
export const JOB_STATUS_CONFIG: Record<
  JobStatus,
  { label: string; color: string; bgColor: string }
> = {
  to_be_scheduled: {
    label: 'To Be Scheduled',
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
  },
  in_progress: {
    label: 'In Progress',
    color: 'text-orange-700',
    bgColor: 'bg-orange-100',
  },
  completed: {
    label: 'Complete',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
  },
};

// Category display configuration
export const JOB_CATEGORY_CONFIG: Record<
  JobCategory,
  { label: string; color: string; bgColor: string }
> = {
  ready_to_schedule: {
    label: 'Ready to Schedule',
    color: 'text-green-800',
    bgColor: 'bg-green-100',
  },
  requires_estimate: {
    label: 'Requires Estimate',
    color: 'text-amber-800',
    bgColor: 'bg-amber-100',
  },
};

// Priority display configuration
export const JOB_PRIORITY_CONFIG: Record<
  number,
  { label: string; color: string; bgColor: string }
> = {
  0: {
    label: 'Normal',
    color: 'text-gray-800',
    bgColor: 'bg-gray-100',
  },
  1: {
    label: 'High',
    color: 'text-orange-800',
    bgColor: 'bg-orange-100',
  },
  2: {
    label: 'Urgent',
    color: 'text-red-800',
    bgColor: 'bg-red-100',
  },
};

// Source display configuration
export const JOB_SOURCE_CONFIG: Record<JobSource, { label: string }> = {
  website: { label: 'Website' },
  google: { label: 'Google' },
  referral: { label: 'Referral' },
  phone: { label: 'Phone' },
  partner: { label: 'Partner' },
};

// Helper to get status config
export function getJobStatusConfig(status: JobStatus) {
  return JOB_STATUS_CONFIG[status];
}

// Helper to get category config
export function getJobCategoryConfig(category: JobCategory) {
  return JOB_CATEGORY_CONFIG[category];
}

// Helper to get priority config
export function getJobPriorityConfig(priority: number) {
  return JOB_PRIORITY_CONFIG[priority] || JOB_PRIORITY_CONFIG[0];
}

// Helper to format job type for display
export function formatJobType(jobType: string): string {
  return jobType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Helper to format duration
export function formatDuration(minutes: number | null): string {
  if (minutes === null) return 'Not estimated';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (remainingMinutes === 0) return `${hours} hr`;
  return `${hours} hr ${remainingMinutes} min`;
}

// Helper to format amount
export function formatAmount(amount: number | null): string {
  if (amount === null) return 'Not quoted';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

// Status label mapping (backend status → display label)
export const STATUS_LABEL_MAP: Record<JobStatus, JobStatusLabel> = {
  to_be_scheduled: 'To Be Scheduled',
  in_progress: 'In Progress',
  completed: 'Complete',
  cancelled: 'Cancelled',
};

// Reverse mapping: display label → backend status
export const LABEL_STATUS_MAP: Record<JobStatusLabel, JobStatus> = {
  'To Be Scheduled': 'to_be_scheduled',
  'In Progress': 'in_progress',
  'Complete': 'completed',
  'Cancelled': 'cancelled',
};

// Helper to get status label
export function getSimplifiedStatus(status: JobStatus): JobStatusLabel {
  return STATUS_LABEL_MAP[status];
}

// Helper to get status config (replaces getSimplifiedStatusConfig)
export function getSimplifiedStatusConfig(status: JobStatus) {
  return JOB_STATUS_CONFIG[status];
}

// Customer tag display config (Req 22)
export const CUSTOMER_TAG_CONFIG: Record<
  CustomerTag,
  { label: string; color: string; bgColor: string }
> = {
  priority: {
    label: 'Priority',
    color: 'text-blue-700',
    bgColor: 'bg-blue-100',
  },
  red_flag: {
    label: 'Red Flag',
    color: 'text-red-700',
    bgColor: 'bg-red-100',
  },
  slow_payer: {
    label: 'Slow Payer',
    color: 'text-amber-700',
    bgColor: 'bg-amber-100',
  },
  new_customer: {
    label: 'New Customer',
    color: 'text-emerald-700',
    bgColor: 'bg-emerald-100',
  },
};

// Helper: calculate days waiting (Req 22)
export function calculateDaysWaiting(createdAt: string): number {
  const created = new Date(createdAt);
  const now = new Date();
  const diffMs = now.getTime() - created.getTime();
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

// Helper: get due by color class (Req 23)
export function getDueByColorClass(targetEndDate: string | null): string {
  if (!targetEndDate) return '';
  const target = parseLocalDate(targetEndDate);
  const now = new Date();
  // Reset time to compare dates only
  now.setHours(0, 0, 0, 0);
  target.setHours(0, 0, 0, 0);
  const diffMs = target.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return 'text-red-600 font-medium';
  if (diffDays <= 7) return 'text-amber-600 font-medium';
  return 'text-slate-600';
}
