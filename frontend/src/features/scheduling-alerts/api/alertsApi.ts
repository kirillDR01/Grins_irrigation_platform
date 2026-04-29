import { apiClient } from '@/core/api/client';
import type {
  AlertsListParams,
  ChangeRequest,
  SchedulingAlert,
} from '../types';

export const alertsApi = {
  list: async (params?: AlertsListParams): Promise<SchedulingAlert[]> => {
    const response = await apiClient.get<SchedulingAlert[]>(
      '/scheduling-alerts/',
      { params }
    );
    return response.data;
  },

  resolve: async (
    id: string,
    payload: { action: string; parameters?: Record<string, unknown> }
  ): Promise<void> => {
    await apiClient.post(`/scheduling-alerts/${id}/resolve`, payload);
  },

  dismiss: async (id: string, reason?: string): Promise<void> => {
    await apiClient.post(`/scheduling-alerts/${id}/dismiss`, { reason });
  },

  listChangeRequests: async (): Promise<ChangeRequest[]> => {
    const response = await apiClient.get<ChangeRequest[]>(
      '/scheduling-alerts/change-requests'
    );
    return response.data;
  },

  approveChangeRequest: async (
    id: string,
    admin_notes?: string
  ): Promise<void> => {
    await apiClient.post(
      `/scheduling-alerts/change-requests/${id}/approve`,
      { admin_notes }
    );
  },

  denyChangeRequest: async (id: string, reason: string): Promise<void> => {
    await apiClient.post(
      `/scheduling-alerts/change-requests/${id}/deny`,
      { reason }
    );
  },
};
