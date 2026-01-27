/**
 * AI Assistant API client
 * 
 * Provides methods for interacting with AI Assistant endpoints
 * including chat, schedule generation, job categorization,
 * communication drafting, and estimate generation.
 */

import { apiClient } from '@/core/api/client';
import type {
  AIChatRequest,
  AIChatResponse,
  ScheduleGenerateRequest,
  ScheduleGenerateResponse,
  JobCategorizationRequest,
  JobCategorizationResponse,
  CommunicationDraftRequest,
  CommunicationDraftResponse,
  EstimateGenerateRequest,
  EstimateGenerateResponse,
  AIUsageResponse,
  AIAuditLogResponse,
  AIDecisionRequest,
  SMSSendRequest,
  SMSSendResponse,
  CommunicationsQueueResponse,
  BulkSendRequest,
  BulkSendResponse,
} from '../types';

/**
 * AI Chat
 */
export const chat = async (request: AIChatRequest): Promise<AIChatResponse> => {
  const response = await apiClient.post<AIChatResponse>('/ai/chat', request);
  return response.data;
};

/**
 * AI Chat with streaming support
 * Returns an EventSource for Server-Sent Events
 */
export const chatStream = (request: AIChatRequest): EventSource => {
  const url = new URL('/api/v1/ai/chat', apiClient.defaults.baseURL);
  url.searchParams.append('message', request.message);
  if (request.session_id) {
    url.searchParams.append('session_id', request.session_id);
  }
  
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  // Note: EventSource doesn't support custom headers in standard browsers
  // For production, consider using fetch with ReadableStream or a library like eventsource
  return new EventSource(url.toString());
};

/**
 * Schedule Generation
 */
export const generateSchedule = async (
  request: ScheduleGenerateRequest
): Promise<ScheduleGenerateResponse> => {
  const response = await apiClient.post<ScheduleGenerateResponse>(
    '/ai/schedule/generate',
    request
  );
  return response.data;
};

/**
 * Job Categorization
 */
export const categorizeJobs = async (
  request: JobCategorizationRequest
): Promise<JobCategorizationResponse> => {
  const response = await apiClient.post<JobCategorizationResponse>(
    '/ai/jobs/categorize',
    request
  );
  return response.data;
};

/**
 * Communication Drafting
 */
export const draftCommunication = async (
  request: CommunicationDraftRequest
): Promise<CommunicationDraftResponse> => {
  const response = await apiClient.post<CommunicationDraftResponse>(
    '/ai/communication/draft',
    request
  );
  return response.data;
};

/**
 * Estimate Generation
 */
export const generateEstimate = async (
  request: EstimateGenerateRequest
): Promise<EstimateGenerateResponse> => {
  const response = await apiClient.post<EstimateGenerateResponse>(
    '/ai/estimate/generate',
    request
  );
  return response.data;
};

/**
 * AI Usage Statistics
 */
export const getUsage = async (): Promise<AIUsageResponse> => {
  const response = await apiClient.get<AIUsageResponse>('/ai/usage');
  return response.data;
};

/**
 * AI Audit Logs
 */
export const getAuditLogs = async (params?: {
  action_type?: string;
  entity_type?: string;
  user_decision?: string;
  page?: number;
  page_size?: number;
}): Promise<AIAuditLogResponse> => {
  const response = await apiClient.get<AIAuditLogResponse>('/ai/audit', { params });
  return response.data;
};

/**
 * Record User Decision on AI Recommendation
 */
export const recordDecision = async (
  auditLogId: string,
  request: AIDecisionRequest
): Promise<void> => {
  await apiClient.post(`/ai/audit/${auditLogId}/decision`, request);
};

/**
 * SMS Operations
 */
export const sendSMS = async (request: SMSSendRequest): Promise<SMSSendResponse> => {
  const response = await apiClient.post<SMSSendResponse>('/sms/send', request);
  return response.data;
};

export const getCommunicationsQueue = async (params?: {
  status?: string;
  message_type?: string;
  limit?: number;
  offset?: number;
}): Promise<CommunicationsQueueResponse> => {
  const response = await apiClient.get<CommunicationsQueueResponse>(
    '/communications/queue',
    { params }
  );
  return response.data;
};

export const sendBulkSMS = async (
  request: BulkSendRequest
): Promise<BulkSendResponse> => {
  const response = await apiClient.post<BulkSendResponse>(
    '/communications/send-bulk',
    request
  );
  return response.data;
};

export const deleteCommunication = async (id: string): Promise<void> => {
  await apiClient.delete(`/communications/${id}`);
};

/**
 * Export all AI API methods
 */
export const aiApi = {
  chat,
  chatStream,
  generateSchedule,
  categorizeJobs,
  draftCommunication,
  generateEstimate,
  getUsage,
  getAuditLogs,
  recordDecision,
  sendSMS,
  getCommunicationsQueue,
  sendBulkSMS,
  deleteCommunication,
};
