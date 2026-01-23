/**
 * Staff API client functions.
 */

import { apiClient } from '@/core/api/client';
import type {
  Staff,
  StaffCreate,
  StaffUpdate,
  StaffAvailabilityUpdate,
  StaffListParams,
  PaginatedStaffResponse,
} from '../types';

const BASE_URL = '/staff';

export const staffApi = {
  /**
   * List staff members with optional filters.
   */
  async list(params?: StaffListParams): Promise<PaginatedStaffResponse> {
    const response = await apiClient.get<PaginatedStaffResponse>(BASE_URL, {
      params,
    });
    return response.data;
  },

  /**
   * Get a single staff member by ID.
   */
  async getById(id: string): Promise<Staff> {
    const response = await apiClient.get<Staff>(`${BASE_URL}/${id}`);
    return response.data;
  },

  /**
   * Create a new staff member.
   */
  async create(data: StaffCreate): Promise<Staff> {
    const response = await apiClient.post<Staff>(BASE_URL, data);
    return response.data;
  },

  /**
   * Update an existing staff member.
   */
  async update(id: string, data: StaffUpdate): Promise<Staff> {
    const response = await apiClient.put<Staff>(`${BASE_URL}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a staff member (soft delete).
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${BASE_URL}/${id}`);
  },

  /**
   * Update staff availability.
   */
  async updateAvailability(
    id: string,
    data: StaffAvailabilityUpdate
  ): Promise<Staff> {
    const response = await apiClient.patch<Staff>(
      `${BASE_URL}/${id}/availability`,
      data
    );
    return response.data;
  },

  /**
   * Get available staff members.
   */
  async getAvailable(): Promise<PaginatedStaffResponse> {
    const response = await apiClient.get<PaginatedStaffResponse>(BASE_URL, {
      params: { is_available: true, is_active: true },
    });
    return response.data;
  },
};
