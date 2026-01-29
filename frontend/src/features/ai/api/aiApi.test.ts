/**
 * Tests for AI API client.
 * Requirements: All AI API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { aiApi } from './aiApi';
import { apiClient } from '@/core/api/client';

// Mock the API client
vi.mock('@/core/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api/v1' },
  },
}));

describe('aiApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('chat', () => {
    it('sends chat message', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { response: 'Hello!', session_id: 'session-123' },
      });

      const result = await aiApi.chat({ message: 'Hi' });

      expect(apiClient.post).toHaveBeenCalledWith('/ai/chat', { message: 'Hi' });
      expect(result.response).toBe('Hello!');
    });
  });

  describe('generateSchedule', () => {
    it('generates schedule', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { schedule_date: '2025-01-29', routes: [] },
      });

      const request = { schedule_date: '2025-01-29', job_ids: ['job-123'] };
      const result = await aiApi.generateSchedule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/schedule/generate', request);
      expect(result.schedule_date).toBe('2025-01-29');
    });
  });

  describe('categorizeJobs', () => {
    it('categorizes jobs', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { categorizations: [{ job_id: 'job-123', category: 'ready_to_schedule' }] },
      });

      const request = { job_ids: ['job-123'] };
      const result = await aiApi.categorizeJobs(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/jobs/categorize', request);
      expect(result.categorizations).toHaveLength(1);
    });
  });

  describe('draftCommunication', () => {
    it('drafts communication', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { draft: 'Hello, your appointment is confirmed.' },
      });

      const request = { type: 'confirmation', customer_id: 'cust-123' };
      const result = await aiApi.draftCommunication(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/communication/draft', request);
      expect(result.draft).toBeDefined();
    });
  });

  describe('generateEstimate', () => {
    it('generates estimate', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { estimate: { amount: '500.00', breakdown: [] } },
      });

      const request = { job_type: 'installation', zone_count: 6 };
      const result = await aiApi.generateEstimate(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/estimate/generate', request);
      expect(result.estimate).toBeDefined();
    });
  });

  describe('getUsage', () => {
    it('fetches AI usage stats', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { total_requests: 100, tokens_used: 5000 },
      });

      const result = await aiApi.getUsage();

      expect(apiClient.get).toHaveBeenCalledWith('/ai/usage');
      expect(result.total_requests).toBe(100);
    });
  });

  describe('getAuditLogs', () => {
    it('fetches audit logs without params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0 },
      });

      await aiApi.getAuditLogs();

      expect(apiClient.get).toHaveBeenCalledWith('/ai/audit', { params: undefined });
    });

    it('fetches audit logs with params', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0 },
      });

      const params = { action_type: 'schedule', page: 1 };
      await aiApi.getAuditLogs(params);

      expect(apiClient.get).toHaveBeenCalledWith('/ai/audit', { params });
    });
  });

  describe('recordDecision', () => {
    it('records user decision', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({});

      await aiApi.recordDecision('audit-123', { decision: 'approved' });

      expect(apiClient.post).toHaveBeenCalledWith('/ai/audit/audit-123/decision', {
        decision: 'approved',
      });
    });
  });

  describe('sendSMS', () => {
    it('sends SMS', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { message_id: 'msg-123', status: 'sent' },
      });

      const request = { to: '6125551234', message: 'Hello' };
      const result = await aiApi.sendSMS(request);

      expect(apiClient.post).toHaveBeenCalledWith('/sms/send', request);
      expect(result.status).toBe('sent');
    });
  });

  describe('getCommunicationsQueue', () => {
    it('fetches communications queue', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({
        data: { items: [], total: 0 },
      });

      await aiApi.getCommunicationsQueue({ status: 'pending' });

      expect(apiClient.get).toHaveBeenCalledWith('/communications/queue', {
        params: { status: 'pending' },
      });
    });
  });

  describe('sendBulkSMS', () => {
    it('sends bulk SMS', async () => {
      vi.mocked(apiClient.post).mockResolvedValue({
        data: { sent_count: 5, failed_count: 0 },
      });

      const request = { message_ids: ['msg-1', 'msg-2'] };
      const result = await aiApi.sendBulkSMS(request);

      expect(apiClient.post).toHaveBeenCalledWith('/communications/send-bulk', request);
      expect(result.sent_count).toBe(5);
    });
  });

  describe('deleteCommunication', () => {
    it('deletes communication', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({});

      await aiApi.deleteCommunication('comm-123');

      expect(apiClient.delete).toHaveBeenCalledWith('/communications/comm-123');
    });
  });
});
