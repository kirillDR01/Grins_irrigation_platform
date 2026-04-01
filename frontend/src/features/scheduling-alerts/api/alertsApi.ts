/**
 * API client for scheduling alerts endpoints.
 */

import { apiClient } from '@/core/api/client';
import type {
  SchedulingAlert,
  ChangeRequest,
  ResolveAlertRequest,
  DismissAlertRequest,
  ApproveChangeRequestPayload,
  DenyChangeRequestPayload,
  AlertListParams,
} from '../types';

const BASE_URL = '/alerts';

export const alertsApi = {
  /**
   * List active alerts/suggestions with optional filters.
   */
  async list(params?: AlertListParams): Promise<SchedulingAlert[]> {
    const response = await apiClient.get<SchedulingAlert[]>(BASE_URL, {
      params,
    });
    return response.data;
  },

  /**
   * Resolve an alert with a chosen action.
   */
  async resolve(id: string, data: ResolveAlertRequest): Promise<SchedulingAlert> {
    const response = await apiClient.post<SchedulingAlert>(
      `${BASE_URL}/${id}/resolve`,
      data
    );
    return response.data;
  },

  /**
   * Dismiss a suggestion.
   */
  async dismiss(id: string, data?: DismissAlertRequest): Promise<SchedulingAlert> {
    const response = await apiClient.post<SchedulingAlert>(
      `${BASE_URL}/${id}/dismiss`,
      data ?? {}
    );
    return response.data;
  },

  /**
   * List pending change requests for admin review.
   */
  async listChangeRequests(): Promise<ChangeRequest[]> {
    const response = await apiClient.get<ChangeRequest[]>(
      `${BASE_URL}/change-requests`
    );
    return response.data;
  },

  /**
   * Approve a change request.
   */
  async approveChangeRequest(
    id: string,
    data?: ApproveChangeRequestPayload
  ): Promise<ChangeRequest> {
    const response = await apiClient.post<ChangeRequest>(
      `${BASE_URL}/change-requests/${id}/approve`,
      data ?? {}
    );
    return response.data;
  },

  /**
   * Deny a change request.
   */
  async denyChangeRequest(
    id: string,
    data: DenyChangeRequestPayload
  ): Promise<ChangeRequest> {
    const response = await apiClient.post<ChangeRequest>(
      `${BASE_URL}/change-requests/${id}/deny`,
      data
    );
    return response.data;
  },
};
