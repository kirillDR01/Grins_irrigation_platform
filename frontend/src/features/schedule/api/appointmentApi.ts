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
} from '../types';

const BASE_URL = '/appointments';

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
   * Cancel an appointment (soft delete).
   */
  async cancel(id: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/${id}`);
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
};
