/**
 * Appointment API client.
 * Handles all appointment-related API calls.
 */

import { apiClient } from '@/core/api/client';
import type {
  Appointment,
  AppointmentCreate,
  AppointmentUpdate,
  AppointmentListParams,
  AppointmentPaginatedResponse,
  DailyScheduleResponse,
  StaffDailyScheduleResponse,
  WeeklyScheduleResponse,
  CollectPaymentRequest,
  CollectPaymentResponse,
  CreateEstimateFromAppointmentRequest,
  CreateEstimateFromAppointmentResponse,
  CreateInvoiceFromAppointmentResponse,
  RequestReviewResponse,
  StaffLocation,
  StaffBreak,
  CreateBreakRequest,
  StaffTimeAnalytics,
} from '../types';

const BASE_URL = '/appointments';

export type BulkSendConfirmationRowStatus =
  | 'sent'
  | 'deferred'
  | 'skipped'
  | 'failed';

export interface BulkSendConfirmationItemResult {
  appointment_id: string;
  status: BulkSendConfirmationRowStatus;
  reason: string | null;
}

export interface BulkSendConfirmationsResult {
  sent_count: number;
  deferred_count: number;
  skipped_count: number;
  failed_count: number;
  total_draft: number;
  results: BulkSendConfirmationItemResult[];
}

export const appointmentApi = {
  /**
   * List appointments with optional filters and pagination.
   */
  async list(
    params?: AppointmentListParams
  ): Promise<AppointmentPaginatedResponse> {
    const response = await apiClient.get<AppointmentPaginatedResponse>(
      BASE_URL,
      { params }
    );
    return response.data;
  },

  /**
   * Get a single appointment by ID.
   */
  async getById(id: string): Promise<Appointment> {
    const response = await apiClient.get<Appointment>(`${BASE_URL}/${id}`);
    return response.data;
  },

  /**
   * Create a new appointment.
   */
  async create(data: AppointmentCreate): Promise<Appointment> {
    const response = await apiClient.post<Appointment>(BASE_URL, data);
    return response.data;
  },

  /**
   * Update an existing appointment.
   */
  async update(id: string, data: AppointmentUpdate): Promise<Appointment> {
    const response = await apiClient.put<Appointment>(`${BASE_URL}/${id}`, data);
    return response.data;
  },

  /**
   * Cancel an appointment (soft delete). Pass ``notifyCustomer=false`` to
   * opt out of the cancellation SMS.
   */
  async cancel(id: string, notifyCustomer: boolean = true): Promise<void> {
    await apiClient.delete(
      `${BASE_URL}/${id}?notify_customer=${notifyCustomer}`,
    );
  },

  /**
   * Get daily schedule for a specific date.
   */
  async getDailySchedule(date: string): Promise<DailyScheduleResponse> {
    const response = await apiClient.get<DailyScheduleResponse>(
      `${BASE_URL}/daily/${date}`
    );
    return response.data;
  },

  /**
   * Get daily schedule for a specific staff member.
   */
  async getStaffDailySchedule(
    staffId: string,
    date: string
  ): Promise<StaffDailyScheduleResponse> {
    const response = await apiClient.get<StaffDailyScheduleResponse>(
      `${BASE_URL}/staff/${staffId}/daily/${date}`
    );
    return response.data;
  },

  /**
   * Get weekly schedule overview.
   */
  async getWeeklySchedule(
    startDate?: string,
    endDate?: string
  ): Promise<WeeklyScheduleResponse> {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await apiClient.get<WeeklyScheduleResponse>(
      `${BASE_URL}/weekly`,
      { params }
    );
    return response.data;
  },

  /**
   * Confirm an appointment.
   */
  async confirm(id: string): Promise<Appointment> {
    return this.update(id, { status: 'confirmed' });
  },

  /**
   * Mark appointment as in progress (arrived).
   */
  async markArrived(id: string): Promise<Appointment> {
    return this.update(id, { status: 'in_progress' });
  },

  /**
   * Mark appointment as completed.
   */
  async markCompleted(id: string): Promise<Appointment> {
    return this.update(id, { status: 'completed' });
  },

  /**
   * Mark appointment as no show.
   */
  async markNoShow(id: string): Promise<Appointment> {
    return this.update(id, { status: 'no_show' });
  },

  /**
   * Get schedule lead time (Req 25).
   */
  async getLeadTime(): Promise<{ days: number; label: string }> {
    const response = await apiClient.get<{ days: number; label: string }>(
      '/schedule/lead-time'
    );
    return response.data;
  },

  /**
   * PATCH an appointment (for drag-drop rescheduling) (Req 24).
   */
  async patch(id: string, data: AppointmentUpdate): Promise<Appointment> {
    const response = await apiClient.patch<Appointment>(`${BASE_URL}/${id}`, data);
    return response.data;
  },

  /**
   * Transition appointment to en_route status (Req 35).
   */
  async markEnRoute(id: string): Promise<Appointment> {
    return this.update(id, { status: 'en_route' as Appointment['status'] });
  },

  /**
   * Collect payment on-site (Req 30).
   */
  async collectPayment(id: string, data: CollectPaymentRequest): Promise<CollectPaymentResponse> {
    const response = await apiClient.post<CollectPaymentResponse>(
      `${BASE_URL}/${id}/collect-payment`,
      data
    );
    return response.data;
  },

  /**
   * Create invoice from appointment (Req 31).
   */
  async createInvoice(id: string): Promise<CreateInvoiceFromAppointmentResponse> {
    const response = await apiClient.post<CreateInvoiceFromAppointmentResponse>(
      `${BASE_URL}/${id}/create-invoice`
    );
    return response.data;
  },

  /**
   * Create estimate from appointment (Req 32).
   */
  async createEstimate(
    id: string,
    data: CreateEstimateFromAppointmentRequest
  ): Promise<CreateEstimateFromAppointmentResponse> {
    const response = await apiClient.post<CreateEstimateFromAppointmentResponse>(
      `${BASE_URL}/${id}/create-estimate`,
      data
    );
    return response.data;
  },

  /**
   * Upload photos for an appointment (Req 33).
   */
  async uploadPhotos(id: string, files: File[]): Promise<{ uploaded: number }> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    const response = await apiClient.post<{ uploaded: number }>(
      `${BASE_URL}/${id}/photos`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  /**
   * Request Google review from customer (Req 34).
   */
  async requestReview(id: string): Promise<RequestReviewResponse> {
    const response = await apiClient.post<RequestReviewResponse>(
      `${BASE_URL}/${id}/request-review`
    );
    return response.data;
  },

  /**
   * Send confirmation SMS for a draft appointment (Req 8.4, 8.12).
   */
  async sendConfirmation(id: string): Promise<{ appointment_id: string; status: string; sms_sent: boolean }> {
    const response = await apiClient.post<{ appointment_id: string; status: string; sms_sent: boolean }>(
      `${BASE_URL}/${id}/send-confirmation`
    );
    return response.data;
  },

  /**
   * Bulk send confirmation SMS for draft appointments (Req 8.6, 8.13).
   *
   * Per-appointment results distinguish sent / deferred (rate-limited)
   * / skipped (no phone, missing customer) / failed (bughunt M-8, M-9).
   */
  async bulkSendConfirmations(data: {
    appointment_ids?: string[];
    date_from?: string;
    date_to?: string;
  }): Promise<BulkSendConfirmationsResult> {
    const response = await apiClient.post<BulkSendConfirmationsResult>(
      `${BASE_URL}/send-confirmations`,
      data
    );
    return response.data;
  },

  /**
   * Get all staff locations (Req 41).
   */
  async getStaffLocations(): Promise<StaffLocation[]> {
    const response = await apiClient.get<StaffLocation[]>('/staff/locations');
    return response.data;
  },

  /**
   * Update a staff member's location (Req 41).
   */
  async updateStaffLocation(
    staffId: string,
    data: { latitude: number; longitude: number }
  ): Promise<void> {
    await apiClient.post(`/staff/${staffId}/location`, data);
  },

  /**
   * Start a break for a staff member (Req 42).
   */
  async startBreak(staffId: string, data: CreateBreakRequest): Promise<StaffBreak> {
    const response = await apiClient.post<StaffBreak>(
      `/staff/${staffId}/breaks`,
      data
    );
    return response.data;
  },

  /**
   * End a break for a staff member (Req 42).
   */
  async endBreak(staffId: string, breakId: string): Promise<StaffBreak> {
    const response = await apiClient.patch<StaffBreak>(
      `/staff/${staffId}/breaks/${breakId}`
    );
    return response.data;
  },

  /**
   * Get staff time analytics (Req 37).
   */
  async getStaffTimeAnalytics(): Promise<StaffTimeAnalytics[]> {
    const response = await apiClient.get<StaffTimeAnalytics[]>(
      '/analytics/staff-time'
    );
    return response.data;
  },
};
