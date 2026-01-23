/**
 * Dashboard feature exports.
 */

// Components
export { DashboardPage, MetricsCard, RecentActivity } from './components';
export type { MetricsCardProps } from './components';

// Hooks
export {
  useDashboardMetrics,
  useRequestVolume,
  useScheduleOverview,
  usePaymentStatus,
  useJobsByStatus,
  useTodaySchedule,
  dashboardKeys,
} from './hooks';

// Types
export type {
  DashboardMetrics,
  RequestVolumeMetrics,
  ScheduleOverview,
  PaymentStatusOverview,
  RecentActivityItem,
  RecentActivityResponse,
  JobsByStatusResponse,
  TodayScheduleResponse,
} from './types';

// API
export { dashboardApi } from './api/dashboardApi';
