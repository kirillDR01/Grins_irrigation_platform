/**
 * TypeScript types for the resource mobile feature.
 */

// ── Schedule types ─────────────────────────────────────────────────────

export type JobStatus =
  | 'scheduled'
  | 'en_route'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export interface ResourceJobCard {
  id: string;
  route_order: number;
  job_type: string;
  address: string;
  customer_name: string;
  customer_notes: string | null;
  estimated_duration: number;
  eta: string | null;
  time_window_start: string | null;
  time_window_end: string | null;
  status: JobStatus;
  has_prejob_flag: boolean;
  is_vip: boolean;
}

export interface ResourceDaySchedule {
  date: string;
  resource_id: string;
  resource_name: string;
  jobs: ResourceJobCard[];
  total_drive_minutes: number;
  total_job_minutes: number;
  utilization_pct: number;
}

// ── Alert types ────────────────────────────────────────────────────────

export type ResourceAlertType =
  | 'job_added'
  | 'job_removed'
  | 'route_resequenced'
  | 'special_equipment'
  | 'customer_access';

export interface ResourceAlert {
  id: string;
  alert_type: ResourceAlertType;
  title: string;
  description: string;
  job_id: string | null;
  created_at: string;
  is_read: boolean;
}

// ── Suggestion types ───────────────────────────────────────────────────

export type ResourceSuggestionType =
  | 'prejob_prep'
  | 'upsell_opportunity'
  | 'departure_timing'
  | 'parts_low'
  | 'pending_approval';

export interface ResourceSuggestion {
  id: string;
  suggestion_type: ResourceSuggestionType;
  title: string;
  description: string;
  job_id: string | null;
  action_label: string | null;
  action_url: string | null;
  created_at: string;
  is_dismissed: boolean;
}

// ── Request params ─────────────────────────────────────────────────────

export interface ResourceScheduleParams {
  date?: string;
}

export interface ResourceAlertsParams {
  is_read?: boolean;
}

export interface ResourceSuggestionsParams {
  is_dismissed?: boolean;
}
