import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { adminNotificationsApi } from '../api/adminNotificationsApi';

export const adminNotificationKeys = {
  all: ['admin-notifications'] as const,
  lists: () => [...adminNotificationKeys.all, 'list'] as const,
  list: (params?: { limit?: number }) =>
    [...adminNotificationKeys.lists(), params ?? {}] as const,
  unreadCount: () => [...adminNotificationKeys.all, 'unread-count'] as const,
};

// Polled at 30s — spec is explicit. Don't poll when the tab is hidden so
// we don't keep firing requests while the user is in another app/tab.
export function useUnreadCount(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: adminNotificationKeys.unreadCount(),
    queryFn: () => adminNotificationsApi.unreadCount(),
    enabled: options?.enabled ?? true,
    staleTime: 15_000,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });
}

// List is lazy — only fetched when the dropdown opens.
export function useRecentAdminNotifications(options?: {
  enabled?: boolean;
  limit?: number;
}) {
  const limit = options?.limit ?? 20;
  return useQuery({
    queryKey: adminNotificationKeys.list({ limit }),
    queryFn: () => adminNotificationsApi.list({ limit }),
    enabled: options?.enabled ?? false,
    staleTime: 10_000,
  });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => adminNotificationsApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminNotificationKeys.all });
    },
  });
}
