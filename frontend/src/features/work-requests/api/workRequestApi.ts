import { apiClient } from '@/core/api';
import type {
  WorkRequest,
  WorkRequestListParams,
  PaginatedWorkRequestResponse,
  SyncStatus,
} from '../types';

const BASE_PATH = '/sheet-submissions';

export interface TriggerSyncResponse {
  new_rows_imported: number;
}

export const workRequestApi = {
  list: async (params?: WorkRequestListParams): Promise<PaginatedWorkRequestResponse> => {
    const response = await apiClient.get<PaginatedWorkRequestResponse>(BASE_PATH, {
      params,
    });
    return response.data;
  },

  getById: async (id: string): Promise<WorkRequest> => {
    const response = await apiClient.get<WorkRequest>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  getSyncStatus: async (): Promise<SyncStatus> => {
    const response = await apiClient.get<SyncStatus>(`${BASE_PATH}/sync-status`);
    return response.data;
  },

  createLead: async (id: string): Promise<WorkRequest> => {
    const response = await apiClient.post<WorkRequest>(`${BASE_PATH}/${id}/create-lead`);
    return response.data;
  },

  triggerSync: async (): Promise<TriggerSyncResponse> => {
    const response = await apiClient.post<TriggerSyncResponse>(`${BASE_PATH}/trigger-sync`);
    return response.data;
  },
};
