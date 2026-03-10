/**
 * Dashboard feature exports.
 */

// Components
export { DashboardPage, MetricsCard, RecentActivity, LeadDashboardWidgets } from './components';
export type { MetricsCardProps } from './components';

// Hooks
export {
  useDashboardMetrics,
  useDashboardSummary,
  useRequestVolume,
  useScheduleOverview,
  usePaymentStatus,
  useJobsByStatus,
  useTodaySchedule,
  useLeadMetricsBySource,
  dashboardKeys,
} from './hooks';

// Types
export type {
  DashboardMetrics,
  DashboardSummaryExtension,
  RequestVolumeMetrics,
  ScheduleOverview,
  PaymentStatusOverview,
  RecentActivityItem,
  RecentActivityResponse,
  JobsByStatusResponse,
  TodayScheduleResponse,
  LeadSourceCount,
  LeadMetricsBySourceResponse,
} from './types';

// API
export { dashboardApi } from './api/dashboardApi';
