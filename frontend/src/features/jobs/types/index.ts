import type { BaseEntity, PaginationParams } from '@/core/api';

// Job status enum matching backend
export type JobStatus =
  | 'requested'
  | 'approved'
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'closed';

// Job category enum matching backend
export type JobCategory = 'ready_to_schedule' | 'requires_estimate';

// Job source enum matching backend
export type JobSource = 'website' | 'google' | 'referral' | 'phone' | 'partner';

// Job entity
export interface Job extends BaseEntity {
  customer_id: string;
  property_id: string | null;
  service_offering_id: string | null;
  job_type: string;
  category: JobCategory;
  status: JobStatus;
  description: string | null;
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
  requested_at: string | null;
  approved_at: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  closed_at: string | null;
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
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// Status display configuration
export const JOB_STATUS_CONFIG: Record<
  JobStatus,
  { label: string; color: string; bgColor: string }
> = {
  requested: {
    label: 'Requested',
    color: 'text-yellow-800',
    bgColor: 'bg-yellow-100',
  },
  approved: {
    label: 'Approved',
    color: 'text-blue-800',
    bgColor: 'bg-blue-100',
  },
  scheduled: {
    label: 'Scheduled',
    color: 'text-purple-800',
    bgColor: 'bg-purple-100',
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
  closed: {
    label: 'Closed',
    color: 'text-gray-800',
    bgColor: 'bg-gray-100',
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
