/**
 * Tests for Schedule Generation API client.
 * Requirements: All schedule generation API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { scheduleGenerationApi } from './scheduleGenerationApi';
import { apiClient } from '@/core/api/client';

// Mock the API client
vi.mock('@/core/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockScheduleResponse = {
  schedule_date: '2025-01-29',
  routes: [
    {
      staff_id: 'staff-123',
      staff_name: 'John Doe',
      appointments: [
        {
          job_id: 'job-123',
          time_window_start: '09:00',
          time_window_end: '11:00',
        },
      ],
    },
  ],
  unassigned_jobs: [],
};

describe('scheduleGenerationApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('generate', () => {
    it('generates schedule', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockScheduleResponse });

      const request = { schedule_date: '2025-01-29', job_ids: ['job-123'] };
      const result = await scheduleGenerationApi.generate(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/generate', request);
      expect(result.schedule_date).toBe('2025-01-29');
    });
  });

  describe('preview', () => {
    it('previews schedule without persisting', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockScheduleResponse });

      const request = { schedule_date: '2025-01-29', job_ids: ['job-123'] };
      const result = await scheduleGenerationApi.preview(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/preview', {
        ...request,
        preview_only: true,
      });
      expect(result.schedule_date).toBe('2025-01-29');
    });
  });

  describe('getCapacity', () => {
    it('fetches capacity for date', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { date: '2025-01-29', total_slots: 10, available_slots: 5 },
      });

      const result = await scheduleGenerationApi.getCapacity('2025-01-29');

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/capacity/2025-01-29');
      expect(result.date).toBe('2025-01-29');
    });
  });

  describe('getStatus', () => {
    it('fetches generation status', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { date: '2025-01-29', status: 'completed' },
      });

      const result = await scheduleGenerationApi.getStatus('2025-01-29');

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/generation-status/2025-01-29');
      expect(result.status).toBe('completed');
    });
  });

  describe('explainSchedule', () => {
    it('gets AI explanation for schedule', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { explanation: 'Schedule optimized for travel time' },
      });

      const request = { schedule_date: '2025-01-29' };
      const result = await scheduleGenerationApi.explainSchedule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/explain', request);
      expect(result.explanation).toBeDefined();
    });
  });

  describe('explainUnassignedJob', () => {
    it('gets explanation for unassigned job', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { explanation: 'No available staff with required skills' },
      });

      const request = { job_id: 'job-123', schedule_date: '2025-01-29' };
      const result = await scheduleGenerationApi.explainUnassignedJob(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/explain-unassigned', request);
      expect(result.explanation).toBeDefined();
    });
  });

  describe('parseConstraints', () => {
    it('parses natural language constraints', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { constraints: [{ type: 'time_preference', value: 'morning' }] },
      });

      const request = { text: 'Schedule in the morning' };
      const result = await scheduleGenerationApi.parseConstraints(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/parse-constraints', request);
      expect(result.constraints).toBeDefined();
    });
  });

  describe('getJobsReadyToSchedule', () => {
    it('fetches jobs ready to schedule without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { jobs: [{ id: 'job-123' }] },
      });

      await scheduleGenerationApi.getJobsReadyToSchedule();

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/jobs-ready', {
        params: { date_from: undefined, date_to: undefined },
      });
    });

    it('fetches jobs ready to schedule with date range', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { jobs: [{ id: 'job-123' }] },
      });

      await scheduleGenerationApi.getJobsReadyToSchedule({
        start_date: '2025-01-29',
        end_date: '2025-02-05',
      });

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/jobs-ready', {
        params: { date_from: '2025-01-29', date_to: '2025-02-05' },
      });
    });
  });

  describe('searchCustomers', () => {
    it('searches customers', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [{ id: 'cust-123', name: 'John Doe' }], total: 1 },
      });

      const result = await scheduleGenerationApi.searchCustomers('John');

      expect(apiClient.get).toHaveBeenCalledWith('/customers', {
        params: { search: 'John', page_size: 20 },
      });
      expect(result).toHaveLength(1);
    });
  });

  describe('applySchedule', () => {
    it('applies generated schedule', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { appointments_created: 5, success: true },
      });

      const request = { schedule_date: '2025-01-29', routes: [] };
      const result = await scheduleGenerationApi.applySchedule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/apply', request);
      expect(result.success).toBe(true);
    });
  });

  describe('clearSchedule', () => {
    it('clears schedule for date', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { audit_id: 'audit-123', appointments_deleted: 5 },
      });

      const request = { schedule_date: '2025-01-29' };
      const result = await scheduleGenerationApi.clearSchedule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/schedule/clear', request);
      expect(result.audit_id).toBe('audit-123');
    });
  });

  describe('getRecentClears', () => {
    it('fetches recent clears with default hours', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [{ id: 'audit-123', schedule_date: '2025-01-29' }],
      });

      const result = await scheduleGenerationApi.getRecentClears();

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/clear/recent', {
        params: { hours: 24 },
      });
      expect(result).toHaveLength(1);
    });

    it('fetches recent clears with custom hours', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: [{ id: 'audit-123', schedule_date: '2025-01-29' }],
      });

      await scheduleGenerationApi.getRecentClears(48);

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/clear/recent', {
        params: { hours: 48 },
      });
    });
  });

  describe('getClearDetails', () => {
    it('fetches clear audit details', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: {
          id: 'audit-123',
          schedule_date: '2025-01-29',
          appointments_data: [],
          jobs_reset: [],
        },
      });

      const result = await scheduleGenerationApi.getClearDetails('audit-123');

      expect(apiClient.get).toHaveBeenCalledWith('/schedule/clear/audit-123');
      expect(result.id).toBe('audit-123');
    });
  });
});
