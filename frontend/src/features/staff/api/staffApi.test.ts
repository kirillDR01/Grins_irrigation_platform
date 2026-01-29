/**
 * Tests for Staff API client.
 * Requirements: All staff API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { staffApi } from './staffApi';
import { apiClient } from '@/core/api/client';

// Mock the API client
vi.mock('@/core/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockStaff = {
  id: 'staff-123',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  role: 'tech',
  is_active: true,
  is_available: true,
  created_at: '2025-01-29T00:00:00Z',
};

describe('staffApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('fetches staff without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockStaff], total: 1, page: 1, page_size: 20 },
      });

      const result = await staffApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/staff', { params: undefined });
      expect(result.items).toHaveLength(1);
    });

    it('fetches staff with params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockStaff], total: 1, page: 1, page_size: 20 },
      });

      const params = { role: 'tech', is_active: true };
      await staffApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/staff', { params });
    });
  });

  describe('getById', () => {
    it('fetches single staff by ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockStaff });

      const result = await staffApi.getById('staff-123');

      expect(apiClient.get).toHaveBeenCalledWith('/staff/staff-123');
      expect(result.id).toBe('staff-123');
    });
  });

  describe('create', () => {
    it('creates new staff member', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockStaff });

      const data = {
        name: 'John Doe',
        phone: '6125551234',
        email: 'john@example.com',
        role: 'tech',
      };
      const result = await staffApi.create(data);

      expect(apiClient.post).toHaveBeenCalledWith('/staff', data);
      expect(result.id).toBe('staff-123');
    });
  });

  describe('update', () => {
    it('updates existing staff member', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: mockStaff });

      const data = { name: 'John Updated' };
      const result = await staffApi.update('staff-123', data);

      expect(apiClient.put).toHaveBeenCalledWith('/staff/staff-123', data);
      expect(result.id).toBe('staff-123');
    });
  });

  describe('delete', () => {
    it('deletes staff member', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({});

      await staffApi.delete('staff-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/staff/staff-123');
    });
  });

  describe('updateAvailability', () => {
    it('updates staff availability', async () => {
      const updatedStaff = { ...mockStaff, is_available: false };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: updatedStaff });

      const data = { is_available: false };
      const result = await staffApi.updateAvailability('staff-123', data);

      expect(apiClient.patch).toHaveBeenCalledWith('/staff/staff-123/availability', data);
      expect(result.is_available).toBe(false);
    });
  });

  describe('getAvailable', () => {
    it('fetches available staff members', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockStaff], total: 1, page: 1, page_size: 20 },
      });

      const result = await staffApi.getAvailable();

      expect(apiClient.get).toHaveBeenCalledWith('/staff', {
        params: { is_available: true, is_active: true },
      });
      expect(result.items[0].is_available).toBe(true);
    });
  });
});
