export type AlertType =
  | 'double_booking'
  | 'skill_mismatch'
  | 'sla_risk'
  | 'resource_behind'
  | 'severe_weather'
  | 'route_swap'
  | 'underutilized_resource'
  | 'customer_preference'
  | 'overtime_avoidable'
  | 'high_revenue_job';

export type Severity = 'critical' | 'warning' | 'suggestion';

export type AlertStatus = 'active' | 'resolved' | 'dismissed';

export interface ResolutionOption {
  action: string;
  label: string;
  description: string;
  parameters?: Record<string, unknown>;
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
  schedule_date: string;
  created_at: string;
}

export type ChangeRequestType =
  | 'delay_report'
  | 'followup_job'
  | 'access_issue'
  | 'nearby_pickup'
  | 'resequence'
  | 'crew_assist'
  | 'parts_log'
  | 'upgrade_quote';

export type ChangeRequestStatus = 'pending' | 'approved' | 'denied';

export interface ChangeRequest {
  id: string;
  resource_id: string;
  resource_name: string;
  request_type: ChangeRequestType;
  details: string;
  affected_job_id: string | null;
  recommended_action: string;
  status: ChangeRequestStatus;
  admin_notes: string | null;
  created_at: string;
}

export interface AlertsListParams {
  type?: 'alert' | 'suggestion';
  severity?: Severity;
  schedule_date?: string;
  status?: AlertStatus;
}
