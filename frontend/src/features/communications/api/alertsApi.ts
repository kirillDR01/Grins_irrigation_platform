/**
 * Admin alerts API client (Gap 06).
 *
 * Handles the informal-opt-out queue feature set:
 *   - `list({ type })` — mirrors GET /api/v1/alerts with a type filter.
 *   - `confirmOptOut(alertId)` — admin-confirms an informal opt-out,
 *     which writes an SmsConsentRecord and acknowledges the alert.
 *   - `dismiss(alertId)` — acknowledges the alert without writing consent.
 */
import { apiClient } from '@/core/api';

export interface AdminAlert {
  id: string;
  type: string;
  severity: 'info' | 'warning' | 'error' | string;
  entity_type: string;
  entity_id: string;
  message: string;
  created_at: string;
  acknowledged_at: string | null;
}

export interface AdminAlertListResponse {
  items: AdminAlert[];
  total: number;
}

const BASE_PATH = '/alerts';

export const alertsApi = {
  list: async (params?: {
    type?: string;
    acknowledged?: boolean;
    limit?: number;
  }): Promise<AdminAlertListResponse> => {
    const response = await apiClient.get<AdminAlertListResponse>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  confirmOptOut: async (alertId: string): Promise<AdminAlert> => {
    const response = await apiClient.post<AdminAlert>(
      `${BASE_PATH}/${alertId}/confirm-opt-out`,
    );
    return response.data;
  },

  dismiss: async (alertId: string): Promise<AdminAlert> => {
    const response = await apiClient.post<AdminAlert>(
      `${BASE_PATH}/${alertId}/dismiss`,
    );
    return response.data;
  },
};
