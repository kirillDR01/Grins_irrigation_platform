// Admin notifications — TS types mirror Pydantic schemas in
// src/grins_platform/schemas/admin_notification.py
//
// Cluster H §5

export type AdminNotificationEventType =
  | 'estimate_approved'
  | 'estimate_rejected'
  | 'appointment_cancelled'
  | 'late_reschedule';

export interface AdminNotification {
  id: string;
  event_type: AdminNotificationEventType | string;
  subject_resource_type: string;
  subject_resource_id: string;
  summary: string;
  actor_user_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface AdminNotificationListResponse {
  items: AdminNotification[];
  total: number;
}

export interface AdminNotificationUnreadCountResponse {
  unread: number;
}
