/**
 * Tests for AI API client.
 * Requirements: All AI API requirements
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { aiApi } from './aiApi';
import { apiClient } from '@/core/api/client';
import type {
  AIChatResponse,
  ScheduleGenerateResponse,
  JobCategorizationResponse,
  CommunicationDraftResponse,
  EstimateGenerateResponse,
  AIUsageResponse,
  AIAuditLogResponse,
  SMSSendResponse,
  CommunicationsQueueResponse,
  BulkSendResponse,
} from '../types';

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
      const mockResponse: AIChatResponse = {
        message: 'Hello!',
        session_id: 'session-123',
        tokens_used: 10,
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await aiApi.chat({ message: 'Hi' });

      expect(apiClient.post).toHaveBeenCalledWith('/ai/chat', { message: 'Hi' });
      expect(result.message).toBe('Hello!');
    });
  });

  describe('generateSchedule', () => {
    it('generates schedule', async () => {
      const mockResponse: ScheduleGenerateResponse = {
        audit_id: 'audit-123',
        schedule: {},
        confidence_score: 0.95,
        warnings: [],
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = { target_date: '2025-01-29', job_ids: ['job-123'] };
      const result = await aiApi.generateSchedule(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/schedule/generate', request);
      expect(result.audit_id).toBe('audit-123');
    });
  });

  describe('categorizeJobs', () => {
    it('categorizes jobs', async () => {
      const mockResponse: JobCategorizationResponse = {
        audit_id: 'audit-123',
        category: 'ready_to_schedule',
        confidence_score: 0.9,
        reasoning: 'Job is ready',
        suggested_services: ['spring_startup'],
        needs_review: false,
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = { description: 'Spring startup needed' };
      const result = await aiApi.categorizeJobs(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/jobs/categorize', request);
      expect(result.category).toBe('ready_to_schedule');
    });
  });

  describe('draftCommunication', () => {
    it('drafts communication', async () => {
      const mockResponse: CommunicationDraftResponse = {
        draft: {
          draft_id: 'draft-123',
          customer_id: 'cust-123',
          customer_name: 'John Doe',
          customer_phone: '6125551234',
          message_type: 'appointment_confirmation',
          message_content: 'Hello, your appointment is confirmed.',
        },
        audit_log_id: 'audit-123',
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = { message_type: 'appointment_confirmation' as const, customer_id: 'cust-123' };
      const result = await aiApi.draftCommunication(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/communication/draft', request);
      expect(result.draft).toBeDefined();
    });
  });

  describe('generateEstimate', () => {
    it('generates estimate', async () => {
      const mockResponse: EstimateGenerateResponse = {
        job_id: 'job-123',
        zone_count: 6,
        similar_jobs: [],
        breakdown: {
          materials: '100.00',
          labor: '200.00',
          equipment: '50.00',
          margin: '150.00',
          total: '500.00',
        },
        recommended_price: '500.00',
        ai_recommendation: 'Based on similar jobs',
        requires_site_visit: false,
        confidence_score: 0.85,
        audit_log_id: 'audit-123',
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = { job_id: 'job-123', zone_count: 6 };
      const result = await aiApi.generateEstimate(request);

      expect(apiClient.post).toHaveBeenCalledWith('/ai/estimate/generate', request);
      expect(result.recommended_price).toBe('500.00');
    });
  });

  describe('getUsage', () => {
    it('fetches AI usage stats', async () => {
      const mockResponse: AIUsageResponse = {
        user_id: 'user-123',
        usage_date: '2025-01-29',
        request_count: 100,
        total_input_tokens: 5000,
        total_output_tokens: 3000,
        estimated_cost_usd: 0.5,
        daily_limit: 1000,
        remaining_requests: 900,
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      const result = await aiApi.getUsage();

      expect(apiClient.get).toHaveBeenCalledWith('/ai/usage');
      expect(result.request_count).toBe(100);
    });
  });

  describe('getAuditLogs', () => {
    it('fetches audit logs without params', async () => {
      const mockResponse: AIAuditLogResponse = {
        entries: [],
        total: 0,
        page: 1,
        page_size: 20,
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await aiApi.getAuditLogs();

      expect(apiClient.get).toHaveBeenCalledWith('/ai/audit', { params: undefined });
    });

    it('fetches audit logs with params', async () => {
      const mockResponse: AIAuditLogResponse = {
        entries: [],
        total: 0,
        page: 1,
        page_size: 20,
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

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
      const mockResponse: SMSSendResponse = {
        success: true,
        message_id: 'msg-123',
        status: 'sent',
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = {
        customer_id: 'cust-123',
        phone: '6125551234',
        message: 'Hello',
        message_type: 'custom' as const,
      };
      const result = await aiApi.sendSMS(request);

      expect(apiClient.post).toHaveBeenCalledWith('/sms/send', request);
      expect(result.status).toBe('sent');
    });
  });

  describe('getCommunicationsQueue', () => {
    it('fetches communications queue', async () => {
      const mockResponse: CommunicationsQueueResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockResponse });

      await aiApi.getCommunicationsQueue({ status: 'pending' });

      expect(apiClient.get).toHaveBeenCalledWith('/communications/queue', {
        params: { status: 'pending' },
      });
    });
  });

  describe('sendBulkSMS', () => {
    it('sends bulk SMS', async () => {
      const mockResponse: BulkSendResponse = {
        total: 5,
        success_count: 5,
        failure_count: 0,
        results: [],
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const request = {
        recipients: [{ customer_id: 'cust-1', phone: '6125551234' }],
        message: 'Hello',
        message_type: 'custom' as const,
      };
      const result = await aiApi.sendBulkSMS(request);

      expect(apiClient.post).toHaveBeenCalledWith('/communications/send-bulk', request);
      expect(result.success_count).toBe(5);
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
