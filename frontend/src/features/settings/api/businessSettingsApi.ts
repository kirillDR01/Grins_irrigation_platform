/**
 * businessSettingsApi — typed wrappers around /api/v1/settings/business.
 *
 * H-12 (bughunt 2026-04-16): firm-wide threshold knobs live in
 * ``business_settings``. Admins read/write the four keys via this pair.
 */

import { apiClient } from '@/core/api';

export interface BusinessThresholds {
  lien_days_past_due: number | null;
  lien_min_amount: string | number | null; // Decimal serialized as string
  upcoming_due_days: number | null;
  confirmation_no_reply_days: number | null;
}

export type BusinessThresholdsUpdate = Partial<BusinessThresholds>;

export const businessSettingsApi = {
  /** GET /api/v1/settings/business */
  getBusinessThresholds: async (): Promise<BusinessThresholds> => {
    const response = await apiClient.get<BusinessThresholds>('/settings/business');
    return response.data;
  },

  /** PATCH /api/v1/settings/business */
  updateBusinessThresholds: async (
    data: BusinessThresholdsUpdate,
  ): Promise<BusinessThresholds> => {
    const response = await apiClient.patch<BusinessThresholds>(
      '/settings/business',
      data,
    );
    return response.data;
  },
};
