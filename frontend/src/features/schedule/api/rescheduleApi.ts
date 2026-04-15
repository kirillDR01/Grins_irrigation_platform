/**
 * Reschedule requests API client.
 * Validates: CRM Changes Update 2 Req 25.1, 25.2, 25.3, 25.4
 */

import { apiClient } from '@/core/api/client';
import type { RescheduleRequestDetail } from '../types';

const BASE_URL = '/schedule/reschedule-requests';

export const rescheduleApi = {
  async list(status?: string): Promise<RescheduleRequestDetail[]> {
    const response = await apiClient.get<RescheduleRequestDetail[]>(BASE_URL, {
      params: status ? { status } : undefined,
    });
    return response.data;
  },

  async resolve(id: string, notes?: string): Promise<void> {
    await apiClient.put(`${BASE_URL}/${id}/resolve`, notes ? { notes } : {});
  },
};
