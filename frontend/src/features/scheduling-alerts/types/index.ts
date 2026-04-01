/**
 * TypeScript types for the scheduling alerts feature.
 */

export type AlertType =
  | 'double_booking'
  | 'skill_mismatch'
  | 'sla_risk'
  | 'resource_behind'
  | 'severe_weather'
  | 'route_swap'
  | 'underutilized'
  | 'customer_preference'
  | 'overtime_avoidable'
  | 'high_revenue';

export type Severity = 'critical' | 'suggestion';

export type AlertStatus = 'active' | 'resolved' | 'dismissed' | 'expired';

export type ChangeRequestStatus = 'pending' | 'approved' | 'denied' | 'expired';

export type ChangeRequestType =
  | 'delay_report'
  | 'followup_job'
  | 'access_issue'
  | 'nearby_pickup'
  | 'resequence'
  | 'crew_assist'
  | 'parts_log'
  | 'upgrade_quote';

export interface ResolutionOption {
  action: string;
  label: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface SchedulingAlert {
  id: string;
  alert_type: AlertType;
  severity: Severity;
  title: string;
  description: string;
  affected_job_ids: string[];
  affected_staff_ids: string[];
  criteria_triggered: number[];
  resolution_options: ResolutionOption[];
  status: AlertStatus;
  resolved_by: string | null;
  resolved_action: string | null;
  resolved_at: string | null;
  schedule_date: string;
  created_at: string;
  updated_at: string;
}

export interface ChangeRequest {
  id: string;
  resource_id: string;
  resource_name?: string;
  request_type: ChangeRequestType;
  details: Record<string, unknown>;
  affected_job_id: string | null;
  recommended_action: string;
  status: ChangeRequestStatus;
  admin_id: string | null;
  admin_notes: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResolveAlertRequest {
  action: string;
  parameters?: Record<string, unknown>;
}

export interface DismissAlertRequest {
  reason?: string;
}

export interface ApproveChangeRequestPayload {
  admin_notes?: string;
}

export interface DenyChangeRequestPayload {
  reason: string;
}

export interface AlertListParams {
  type?: 'alert' | 'suggestion';
  severity?: Severity;
  schedule_date?: string;
  status?: AlertStatus;
}
