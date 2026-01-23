/**
 * Dashboard query hooks using TanStack Query.
 */

import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../api/dashboardApi';

/**
 * Query key factory for dashboard queries.
 */
export const dashboardKeys = {
  all: ['dashboard'] as const,
  metrics: () => [...dashboardKeys.all, 'metrics'] as const,
  requestVolume: (params?: { start_date?: string; end_date?: string }) =>
    [...dashboardKeys.all, 'requestVolume', params] as const,
  scheduleOverview: (date?: string) =>
    [...dashboardKeys.all, 'scheduleOverview', date] as const,
  paymentStatus: () => [...dashboardKeys.all, 'paymentStatus'] as const,
  jobsByStatus: () => [...dashboardKeys.all, 'jobsByStatus'] as const,
  todaySchedule: () => [...dashboardKeys.all, 'todaySchedule'] as const,
};

/**
 * Hook to fetch overall dashboard metrics.
 */
export function useDashboardMetrics() {
  return useQuery({
    queryKey: dashboardKeys.metrics(),
    queryFn: dashboardApi.getMetrics,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook to fetch request volume metrics.
 */
export function useRequestVolume(params?: {
  start_date?: string;
  end_date?: string;
}) {
  return useQuery({
    queryKey: dashboardKeys.requestVolume(params),
    queryFn: () => dashboardApi.getRequestVolume(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch schedule overview for a specific date.
 */
export function useScheduleOverview(date?: string) {
  return useQuery({
    queryKey: dashboardKeys.scheduleOverview(date),
    queryFn: () => dashboardApi.getScheduleOverview(date),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook to fetch payment status overview.
 */
export function usePaymentStatus() {
  return useQuery({
    queryKey: dashboardKeys.paymentStatus(),
    queryFn: dashboardApi.getPaymentStatus,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch jobs count by status.
 */
export function useJobsByStatus() {
  return useQuery({
    queryKey: dashboardKeys.jobsByStatus(),
    queryFn: dashboardApi.getJobsByStatus,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

/**
 * Hook to fetch today's schedule summary.
 */
export function useTodaySchedule() {
  return useQuery({
    queryKey: dashboardKeys.todaySchedule(),
    queryFn: dashboardApi.getTodaySchedule,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}
