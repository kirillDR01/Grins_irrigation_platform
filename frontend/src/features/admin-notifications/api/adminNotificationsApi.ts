import { apiClient } from '@/core/api';
import type {
  AdminNotification,
  AdminNotificationListResponse,
  AdminNotificationUnreadCountResponse,
} from '../types';

const BASE_PATH = '/admin/notifications';

export const adminNotificationsApi = {
  list: async (
    params?: { limit?: number },
  ): Promise<AdminNotificationListResponse> => {
    const response = await apiClient.get<AdminNotificationListResponse>(
      BASE_PATH,
      { params },
    );
    return response.data;
  },

  unreadCount: async (): Promise<AdminNotificationUnreadCountResponse> => {
    const response = await apiClient.get<AdminNotificationUnreadCountResponse>(
      `${BASE_PATH}/unread-count`,
    );
    return response.data;
  },

  markRead: async (id: string): Promise<AdminNotification> => {
    const response = await apiClient.post<AdminNotification>(
      `${BASE_PATH}/${id}/read`,
    );
    return response.data;
  },
};
