import { apiClient } from '@/core/api/client';
import type { ResourceAlert, ResourceSchedule, ResourceSuggestion } from '../types';

export const resourceApi = {
  getSchedule: async (staffId: string, date: string): Promise<ResourceSchedule> => {
    const response = await apiClient.get<ResourceSchedule>(
      `/staff/${staffId}/schedule/${date}`
    );
    return response.data;
  },

  getAlerts: async (staffId: string): Promise<ResourceAlert[]> => {
    const response = await apiClient.get<ResourceAlert[]>(
      `/staff/${staffId}/alerts`
    );
    return response.data;
  },

  getSuggestions: async (staffId: string): Promise<ResourceSuggestion[]> => {
    const response = await apiClient.get<ResourceSuggestion[]>(
      `/staff/${staffId}/suggestions`
    );
    return response.data;
  },

  dismissAlert: async (staffId: string, alertId: string): Promise<void> => {
    await apiClient.post(`/staff/${staffId}/alerts/${alertId}/dismiss`);
  },

  acceptSuggestion: async (staffId: string, suggestionId: string): Promise<void> => {
    await apiClient.post(`/staff/${staffId}/suggestions/${suggestionId}/accept`);
  },
};
