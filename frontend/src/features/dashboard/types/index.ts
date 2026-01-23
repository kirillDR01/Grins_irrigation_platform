/**
 * Dashboard types matching backend schemas.
 */

export interface DashboardMetrics {
  total_customers: number;
  active_customers: number;
  jobs_by_status: Record<string, number>;
  today_appointments: number;
  available_staff: number;
  total_staff: number;
}

export interface RequestVolumeMetrics {
  period_start: string;
  period_end: string;
  total_requests: number;
  requests_by_day: Record<string, number>;
  requests_by_category: Record<string, number>;
  requests_by_source: Record<string, number>;
  average_daily_requests: number;
}

export interface ScheduleOverview {
  schedule_date: string;
  total_appointments: number;
  appointments_by_status: Record<string, number>;
  appointments_by_staff: Record<string, number>;
  total_scheduled_minutes: number;
  staff_utilization: Record<string, number>;
}

export interface PaymentStatusOverview {
  total_invoices: number;
  pending_invoices: number;
  paid_invoices: number;
  overdue_invoices: number;
  total_pending_amount: number;
  total_overdue_amount: number;
  average_days_to_payment: number;
}

export interface RecentActivityItem {
  id: string;
  activity_type: string;
  description: string;
  job_id: string | null;
  customer_name: string;
  timestamp: string;
}

export interface RecentActivityResponse {
  items: RecentActivityItem[];
  total: number;
}

export interface JobsByStatusResponse {
  requested: number;
  approved: number;
  scheduled: number;
  in_progress: number;
  completed: number;
  closed: number;
  cancelled: number;
}

export interface TodayScheduleResponse {
  schedule_date: string;
  total_appointments: number;
  completed_appointments: number;
  in_progress_appointments: number;
  upcoming_appointments: number;
  cancelled_appointments: number;
}
