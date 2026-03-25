import { apiClient } from '@/core/api';
import type { BusinessSettings } from '../types';

export const settingsApi = {
  getSettings: async (): Promise<BusinessSettings> => {
    const response = await apiClient.get<BusinessSettings>('/settings');
    return response.data;
  },

  updateSettings: async (data: Partial<BusinessSettings>): Promise<BusinessSettings> => {
    const response = await apiClient.patch<BusinessSettings>('/settings', data);
    return response.data;
  },

  uploadLogo: async (file: File): Promise<{ url: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<{ url: string }>('/settings/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};
