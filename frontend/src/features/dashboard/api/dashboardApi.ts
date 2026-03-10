/**
 * Dashboard API client.
 * Handles all dashboard-related API calls.
 */

import { apiClient } from '@/core/api/client';
import type {
  DashboardMetrics,
  DashboardSummaryExtension,
  RequestVolumeMetrics,
  ScheduleOverview,
  PaymentStatusOverview,
  JobsByStatusResponse,
  TodayScheduleResponse,
  LeadMetricsBySourceResponse,
} from '../types';

const BASE_PATH = '/dashboard';

export const dashboardApi = {
  /**
   * Get overall dashboard metrics.
   */
  getMetrics: async (): Promise<DashboardMetrics> => {
    const response = await apiClient.get<DashboardMetrics>(
      `${BASE_PATH}/metrics`
    );
    return response.data;
  },

  /**
   * Get extended dashboard summary with agreement and lead metrics.
   */
  getSummary: async (): Promise<DashboardSummaryExtension> => {
    const response = await apiClient.get<DashboardSummaryExtension>(
      `${BASE_PATH}/summary`
    );
    return response.data;
  },

  /**
   * Get request volume metrics for a date range.
   */
  getRequestVolume: async (params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<RequestVolumeMetrics> => {
    const response = await apiClient.get<RequestVolumeMetrics>(
      `${BASE_PATH}/requests`,
      { params }
    );
    return response.data;
  },

  /**
   * Get schedule overview for a specific date.
   */
  getScheduleOverview: async (date?: string): Promise<ScheduleOverview> => {
    const response = await apiClient.get<ScheduleOverview>(
      `${BASE_PATH}/schedule`,
      { params: date ? { date } : undefined }
    );
    return response.data;
  },

  /**
   * Get payment status overview.
   */
  getPaymentStatus: async (): Promise<PaymentStatusOverview> => {
    const response = await apiClient.get<PaymentStatusOverview>(
      `${BASE_PATH}/payments`
    );
    return response.data;
  },

  /**
   * Get jobs count by status.
   */
  getJobsByStatus: async (): Promise<JobsByStatusResponse> => {
    const response = await apiClient.get<JobsByStatusResponse>(
      `${BASE_PATH}/jobs-by-status`
    );
    return response.data;
  },

  /**
   * Get today's schedule summary.
   */
  getTodaySchedule: async (): Promise<TodayScheduleResponse> => {
    const response = await apiClient.get<TodayScheduleResponse>(
      `${BASE_PATH}/today-schedule`
    );
    return response.data;
  },

  /**
   * Get lead metrics grouped by source (trailing 30 days by default).
   */
  getLeadMetricsBySource: async (): Promise<LeadMetricsBySourceResponse> => {
    const response = await apiClient.get<LeadMetricsBySourceResponse>(
      '/leads/metrics/by-source'
    );
    return response.data;
  },
};
