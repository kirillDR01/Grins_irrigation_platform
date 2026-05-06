import { apiClient } from '@/core/api';

/**
 * Sales-side reschedule request endpoints (mirror of
 * frontend/src/features/schedule/api/rescheduleRequestsApi.ts but
 * scoped to estimate-visit rows where ``sales_calendar_event_id`` is set).
 */

export interface SalesRescheduleRequestDetail {
  id: string;
  job_id: string | null;
  appointment_id: string | null;
  sales_calendar_event_id: string | null;
  customer_id: string;
  customer_name: string;
  original_appointment_date: string | null;
  original_appointment_staff: string | null;
  requested_alternatives: { entries?: Array<{ text: string; at: string }> } | null;
  raw_alternatives_text: string | null;
  status: 'open' | 'resolved';
  created_at: string;
  resolved_at: string | null;
}

export const salesRescheduleApi = {
  list: async (
    statusFilter: 'open' | 'resolved' = 'open',
  ): Promise<SalesRescheduleRequestDetail[]> => {
    const response = await apiClient.get<SalesRescheduleRequestDetail[]>(
      '/sales/calendar/events/reschedule-requests',
      { params: { status: statusFilter } },
    );
    return response.data;
  },

  resolve: async (
    requestId: string,
  ): Promise<SalesRescheduleRequestDetail> => {
    const response = await apiClient.put<SalesRescheduleRequestDetail>(
      `/sales/calendar/events/reschedule-requests/${requestId}/resolve`,
    );
    return response.data;
  },

  rescheduleFromRequest: async (
    requestId: string,
    body: {
      scheduled_date: string;
      start_time?: string | null;
      end_time?: string | null;
    },
  ): Promise<{
    event_id: string;
    request_id: string;
    scheduled_date: string;
    confirmation_status: string;
  }> => {
    const response = await apiClient.post<{
      event_id: string;
      request_id: string;
      scheduled_date: string;
      confirmation_status: string;
    }>(
      `/sales/calendar/events/reschedule-requests/${requestId}/reschedule`,
      body,
    );
    return response.data;
  },
};
