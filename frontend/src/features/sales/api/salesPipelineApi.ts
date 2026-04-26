import { apiClient } from '@/core/api';
import type {
  SalesEntry,
  SalesPipelineListResponse,
  SalesEntryStatusUpdate,
  SalesCalendarEvent,
  SalesCalendarEventCreate,
  SalesCalendarEventUpdate,
} from '../types/pipeline';

export interface SalesDocument {
  id: string;
  customer_id: string;
  // bughunt H-7 + Bug #9: scopes a contract/estimate doc to the
  // pipeline entry it was uploaded under. Legacy rows pre-H-7 have
  // ``null``.
  sales_entry_id: string | null;
  file_key: string;
  file_name: string;
  document_type: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  uploaded_by: string | null;
}

export const salesPipelineApi = {
  list: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<SalesPipelineListResponse> => {
    const response = await apiClient.get<SalesPipelineListResponse>(
      '/sales/pipeline',
      { params },
    );
    return response.data;
  },

  get: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.get<SalesEntry>(`/sales/pipeline/${id}`);
    return response.data;
  },

  advance: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.post<SalesEntry>(
      `/sales/pipeline/${id}/advance`,
    );
    return response.data;
  },

  overrideStatus: async (
    id: string,
    body: SalesEntryStatusUpdate,
  ): Promise<SalesEntry> => {
    const response = await apiClient.put<SalesEntry>(
      `/sales/pipeline/${id}/status`,
      body,
    );
    return response.data;
  },

  convert: async (id: string): Promise<{ job_id: string }> => {
    const response = await apiClient.post<{ job_id: string }>(
      `/sales/pipeline/${id}/convert`,
    );
    return response.data;
  },

  forceConvert: async (
    id: string,
  ): Promise<{ job_id: string; forced: boolean }> => {
    const response = await apiClient.post<{
      job_id: string;
      forced: boolean;
    }>(`/sales/pipeline/${id}/force-convert`);
    return response.data;
  },

  // NEW-D: pause/unpause auto-nudges, send appointment-confirmation SMS,
  // dismiss a row from the pipeline list. Persistence backed by the
  // ``nudges_paused_until`` and ``dismissed_at`` columns added in the
  // 20260430_120000 migration.
  pauseNudges: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.post<SalesEntry>(
      `/sales/pipeline/${id}/pause-nudges`,
    );
    return response.data;
  },

  unpauseNudges: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.post<SalesEntry>(
      `/sales/pipeline/${id}/unpause-nudges`,
    );
    return response.data;
  },

  sendTextConfirmation: async (
    id: string,
  ): Promise<{ message_id: string; status: string }> => {
    const response = await apiClient.post<{
      message_id: string;
      status: string;
    }>(`/sales/pipeline/${id}/send-text-confirmation`);
    return response.data;
  },

  dismiss: async (id: string): Promise<SalesEntry> => {
    const response = await apiClient.post<SalesEntry>(
      `/sales/pipeline/${id}/dismiss`,
    );
    return response.data;
  },

  markLost: async (
    id: string,
    closedReason?: string,
  ): Promise<SalesEntry> => {
    const response = await apiClient.delete<SalesEntry>(
      `/sales/pipeline/${id}`,
      { params: closedReason ? { closed_reason: closedReason } : undefined },
    );
    return response.data;
  },

  // Signing — Req 18.1, 18.2, 18.3
  triggerEmailSigning: async (
    id: string,
  ): Promise<{ document_id: string; status: string }> => {
    const response = await apiClient.post<{
      document_id: string;
      status: string;
    }>(`/sales/pipeline/${id}/sign/email`);
    return response.data;
  },

  getEmbeddedSigningUrl: async (
    id: string,
  ): Promise<{ signing_url: string }> => {
    const response = await apiClient.post<{ signing_url: string }>(
      `/sales/pipeline/${id}/sign/embedded`,
    );
    return response.data;
  },

  // Documents — Req 17.1, 17.2
  listDocuments: async (customerId: string): Promise<SalesDocument[]> => {
    const response = await apiClient.get<SalesDocument[]>(
      `/customers/${customerId}/documents`,
    );
    return response.data;
  },

  uploadDocument: async (
    customerId: string,
    file: File,
    documentType: string,
  ): Promise<SalesDocument> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<SalesDocument>(
      `/customers/${customerId}/documents?document_type=${encodeURIComponent(documentType)}`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } },
    );
    return response.data;
  },

  downloadDocument: async (
    customerId: string,
    documentId: string,
  ): Promise<{ download_url: string; file_name: string }> => {
    const response = await apiClient.get<{
      download_url: string;
      file_name: string;
    }>(`/customers/${customerId}/documents/${documentId}/download`);
    return response.data;
  },

  deleteDocument: async (
    customerId: string,
    documentId: string,
  ): Promise<void> => {
    await apiClient.delete(
      `/customers/${customerId}/documents/${documentId}`,
    );
  },

  // Calendar events — Req 15.1, 15.2, 15.3
  listCalendarEvents: async (params?: {
    start_date?: string;
    end_date?: string;
    sales_entry_id?: string;
  }): Promise<SalesCalendarEvent[]> => {
    const response = await apiClient.get<SalesCalendarEvent[]>(
      '/sales/calendar/events',
      { params },
    );
    return response.data;
  },

  createCalendarEvent: async (
    body: SalesCalendarEventCreate,
  ): Promise<SalesCalendarEvent> => {
    const response = await apiClient.post<SalesCalendarEvent>(
      '/sales/calendar/events',
      body,
    );
    return response.data;
  },

  updateCalendarEvent: async (
    eventId: string,
    body: SalesCalendarEventUpdate,
  ): Promise<SalesCalendarEvent> => {
    const response = await apiClient.put<SalesCalendarEvent>(
      `/sales/calendar/events/${eventId}`,
      body,
    );
    return response.data;
  },

  deleteCalendarEvent: async (eventId: string): Promise<void> => {
    await apiClient.delete(`/sales/calendar/events/${eventId}`);
  },
};
