/**
 * Tests for Job API client.
 * Requirements: All job API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { jobApi } from './jobApi';
import { apiClient } from '@/core/api';

// Mock the API client
vi.mock('@/core/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockJob = {
  id: 'job-123',
  customer_id: 'cust-123',
  property_id: 'prop-123',
  job_type: 'spring_startup',
  status: 'requested',
  description: 'Spring startup service',
  quoted_amount: '150.00',
  created_at: '2025-01-29T00:00:00Z',
};

describe('jobApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('fetches jobs without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      const result = await jobApi.list();

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', { params: undefined });
      expect(result.items).toHaveLength(1);
    });

    it('fetches jobs with params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      const params = { status: 'approved', page: 1 };
      await jobApi.list(params);

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', { params });
    });
  });

  describe('get', () => {
    it('fetches single job by ID', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockJob });

      const result = await jobApi.get('job-123');

      expect(apiClient.get).toHaveBeenCalledWith('/jobs/job-123');
      expect(result.id).toBe('job-123');
    });
  });

  describe('create', () => {
    it('creates new job', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockJob });

      const data = {
        customer_id: 'cust-123',
        property_id: 'prop-123',
        job_type: 'spring_startup',
        description: 'Spring startup service',
      };
      const result = await jobApi.create(data);

      expect(apiClient.post).toHaveBeenCalledWith('/jobs', data);
      expect(result.id).toBe('job-123');
    });
  });

  describe('update', () => {
    it('updates existing job', async () => {
      vi.mocked(apiClient.put).mockResolvedValue({ data: mockJob });

      const data = { description: 'Updated description' };
      const result = await jobApi.update('job-123', data);

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123', data);
      expect(result.id).toBe('job-123');
    });
  });

  describe('updateStatus', () => {
    it('updates job status', async () => {
      const approvedJob = { ...mockJob, status: 'approved' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: approvedJob });

      const result = await jobApi.updateStatus('job-123', { status: 'approved' });

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123/status', { status: 'approved' });
      expect(result.status).toBe('approved');
    });
  });

  describe('delete', () => {
    it('deletes job', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({});

      await jobApi.delete('job-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/jobs/job-123');
    });
  });

  describe('getReadyToSchedule', () => {
    it('fetches jobs ready to schedule', async () => {
      const approvedJob = { ...mockJob, status: 'approved' };
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [approvedJob], total: 1, page: 1, page_size: 20 },
      });

      const result = await jobApi.getReadyToSchedule();

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', {
        params: { category: 'ready_to_schedule', status: 'approved' },
      });
      expect(result.items[0].status).toBe('approved');
    });
  });

  describe('getRequiresEstimate', () => {
    it('fetches jobs requiring estimate', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      await jobApi.getRequiresEstimate();

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', {
        params: { category: 'requires_estimate' },
      });
    });
  });

  describe('getByStatus', () => {
    it('fetches jobs by status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      await jobApi.getByStatus('completed', { page: 1 });

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', {
        params: { page: 1, status: 'completed' },
      });
    });
  });

  describe('getByCustomer', () => {
    it('fetches jobs by customer', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      await jobApi.getByCustomer('cust-123', { page: 1 });

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', {
        params: { page: 1, customer_id: 'cust-123' },
      });
    });
  });

  describe('search', () => {
    it('searches jobs', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [mockJob], total: 1, page: 1, page_size: 20 },
      });

      await jobApi.search('spring');

      expect(apiClient.get).toHaveBeenCalledWith('/jobs', {
        params: { search: 'spring' },
      });
    });
  });

  describe('approve', () => {
    it('approves job', async () => {
      const approvedJob = { ...mockJob, status: 'approved' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: approvedJob });

      const result = await jobApi.approve('job-123');

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123/status', { status: 'approved' });
      expect(result.status).toBe('approved');
    });
  });

  describe('cancel', () => {
    it('cancels job', async () => {
      const cancelledJob = { ...mockJob, status: 'cancelled' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: cancelledJob });

      const result = await jobApi.cancel('job-123', 'Customer requested cancellation');

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123/status', {
        status: 'cancelled',
        notes: 'Customer requested cancellation',
      });
      expect(result.status).toBe('cancelled');
    });
  });

  describe('complete', () => {
    it('completes job', async () => {
      const completedJob = { ...mockJob, status: 'completed' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: completedJob });

      const result = await jobApi.complete('job-123', 'Work completed successfully');

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123/status', {
        status: 'completed',
        notes: 'Work completed successfully',
      });
      expect(result.status).toBe('completed');
    });
  });

  describe('close', () => {
    it('closes job', async () => {
      const closedJob = { ...mockJob, status: 'closed' };
      vi.mocked(apiClient.put).mockResolvedValue({ data: closedJob });

      const result = await jobApi.close('job-123', 'Payment received');

      expect(apiClient.put).toHaveBeenCalledWith('/jobs/job-123/status', {
        status: 'closed',
        notes: 'Payment received',
      });
      expect(result.status).toBe('closed');
    });
  });
});
