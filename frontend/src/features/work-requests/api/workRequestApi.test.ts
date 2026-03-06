import { describe, it, expect, vi, beforeEach } from 'vitest';
import { workRequestApi } from './workRequestApi';
import { apiClient } from '@/core/api';

vi.mock('@/core/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockWorkRequest = {
  id: 'wr-001',
  sheet_row_number: 2,
  timestamp: '2026-01-15T10:00:00Z',
  spring_startup: 'Yes',
  fall_blowout: null,
  summer_tuneup: null,
  repair_existing: null,
  new_system_install: null,
  addition_to_system: null,
  additional_services_info: null,
  date_work_needed_by: 'ASAP',
  name: 'Alice Johnson',
  phone: '6125551234',
  email: 'alice@example.com',
  city: 'Minneapolis',
  address: '123 Main St',
  additional_info: null,
  client_type: 'new',
  property_type: 'Residential',
  referral_source: 'Google',
  landscape_hardscape: null,
  processing_status: 'imported',
  processing_error: null,
  lead_id: null,
  imported_at: '2026-01-15T12:00:00Z',
  created_at: '2026-01-15T12:00:00Z',
  updated_at: '2026-01-15T12:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockWorkRequest],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockSyncStatus = {
  last_sync: '2026-01-15T12:00:00Z',
  is_running: true,
  last_error: null,
};

describe('workRequestApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('should fetch work requests list', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedResponse });

      const result = await workRequestApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/sheet-submissions', { params: undefined });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should fetch with params', async () => {
      const params = { page: 2, page_size: 10, processing_status: 'imported' as const };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockPaginatedResponse });

      const result = await workRequestApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/sheet-submissions', { params });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Network error'));

      await expect(workRequestApi.list()).rejects.toThrow('Network error');
    });
  });

  describe('getById', () => {
    it('should fetch single work request', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockWorkRequest });

      const result = await workRequestApi.getById('wr-001');

      expect(apiClient.get).toHaveBeenCalledWith('/sheet-submissions/wr-001');
      expect(result).toEqual(mockWorkRequest);
    });

    it('should handle not found error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Not found'));

      await expect(workRequestApi.getById('bad-id')).rejects.toThrow('Not found');
    });
  });

  describe('getSyncStatus', () => {
    it('should fetch sync status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSyncStatus });

      const result = await workRequestApi.getSyncStatus();

      expect(apiClient.get).toHaveBeenCalledWith('/sheet-submissions/sync-status');
      expect(result).toEqual(mockSyncStatus);
    });

    it('should handle error', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('Server error'));

      await expect(workRequestApi.getSyncStatus()).rejects.toThrow('Server error');
    });
  });

  describe('createLead', () => {
    it('should create lead from submission', async () => {
      const updated = { ...mockWorkRequest, processing_status: 'lead_created', lead_id: 'lead-1' };
      vi.mocked(apiClient.post).mockResolvedValue({ data: updated });

      const result = await workRequestApi.createLead('wr-001');

      expect(apiClient.post).toHaveBeenCalledWith('/sheet-submissions/wr-001/create-lead');
      expect(result).toEqual(updated);
    });

    it('should handle conflict error', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Conflict'));

      await expect(workRequestApi.createLead('wr-001')).rejects.toThrow('Conflict');
    });
  });

  describe('triggerSync', () => {
    it('should trigger sync', async () => {
      const response = { new_rows_imported: 5 };
      vi.mocked(apiClient.post).mockResolvedValue({ data: response });

      const result = await workRequestApi.triggerSync();

      expect(apiClient.post).toHaveBeenCalledWith('/sheet-submissions/trigger-sync');
      expect(result).toEqual(response);
    });

    it('should handle error', async () => {
      vi.mocked(apiClient.post).mockRejectedValue(new Error('Sync failed'));

      await expect(workRequestApi.triggerSync()).rejects.toThrow('Sync failed');
    });
  });
});
