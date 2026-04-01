/**
 * API client for resource-mobile endpoints.
 */

import { apiClient } from '@/core/api/client';
import type {
  ResourceDaySchedule,
  ResourceAlert,
  ResourceSuggestion,
  ResourceScheduleParams,
  ResourceAlertsParams,
  ResourceSuggestionsParams,
} from '../types';

const BASE_URL = '/resource';

export const resourceApi = {
  /** GET /api/v1/resource/schedule — today's schedule for the authenticated resource. */
  async getSchedule(
    params?: ResourceScheduleParams
  ): Promise<ResourceDaySchedule> {
    const response = await apiClient.get<ResourceDaySchedule>(
      `${BASE_URL}/schedule`,
      { params }
    );
    return response.data;
  },

  /** GET /api/v1/resource/alerts — resource-facing alerts. */
  async getAlerts(params?: ResourceAlertsParams): Promise<ResourceAlert[]> {
    const response = await apiClient.get<ResourceAlert[]>(
      `${BASE_URL}/alerts`,
      { params }
    );
    return response.data;
  },

  /** POST /api/v1/resource/alerts/{id}/read — mark alert as read. */
  async markAlertRead(id: string): Promise<ResourceAlert> {
    const response = await apiClient.post<ResourceAlert>(
      `${BASE_URL}/alerts/${id}/read`
    );
    return response.data;
  },

  /** GET /api/v1/resource/suggestions — resource-facing suggestions. */
  async getSuggestions(
    params?: ResourceSuggestionsParams
  ): Promise<ResourceSuggestion[]> {
    const response = await apiClient.get<ResourceSuggestion[]>(
      `${BASE_URL}/suggestions`,
      { params }
    );
    return response.data;
  },

  /** POST /api/v1/resource/suggestions/{id}/dismiss — dismiss a suggestion. */
  async dismissSuggestion(id: string): Promise<ResourceSuggestion> {
    const response = await apiClient.post<ResourceSuggestion>(
      `${BASE_URL}/suggestions/${id}/dismiss`
    );
    return response.data;
  },
};
