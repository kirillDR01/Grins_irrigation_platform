/**
 * Schedule Generation API client.
 * Handles route optimization and schedule generation calls.
 */

import { apiClient } from '@/core/api/client';
import type {
  ScheduleGenerateRequest,
  ScheduleGenerateResponse,
  ScheduleCapacityResponse,
  ScheduleGenerationStatusResponse,
  ScheduleExplanationRequest,
  ScheduleExplanationResponse,
  UnassignedJobExplanationRequest,
  UnassignedJobExplanationResponse,
  ParseConstraintsRequest,
  ParseConstraintsResponse,
  JobsReadyToScheduleResponse,
  CustomerSearchResult,
} from '../types';
import type { PaginatedResponse } from '@/core/api';

const BASE_URL = '/schedule';

export const scheduleGenerationApi = {
  /**
   * Generate optimized schedule for a date.
   */
  async generate(
    request: ScheduleGenerateRequest
  ): Promise<ScheduleGenerateResponse> {
    const response = await apiClient.post<ScheduleGenerateResponse>(
      `${BASE_URL}/generate`,
      request
    );
    return response.data;
  },

  /**
   * Preview schedule without persisting.
   */
  async preview(
    request: ScheduleGenerateRequest
  ): Promise<ScheduleGenerateResponse> {
    const response = await apiClient.post<ScheduleGenerateResponse>(
      `${BASE_URL}/preview`,
      { ...request, preview_only: true }
    );
    return response.data;
  },

  /**
   * Get capacity information for a date.
   */
  async getCapacity(date: string): Promise<ScheduleCapacityResponse> {
    const response = await apiClient.get<ScheduleCapacityResponse>(
      `${BASE_URL}/capacity/${date}`
    );
    return response.data;
  },

  /**
   * Get generation status for a date.
   */
  async getStatus(date: string): Promise<ScheduleGenerationStatusResponse> {
    const response = await apiClient.get<ScheduleGenerationStatusResponse>(
      `${BASE_URL}/generation-status/${date}`
    );
    return response.data;
  },

  /**
   * Get AI explanation for a generated schedule.
   */
  async explainSchedule(
    request: ScheduleExplanationRequest
  ): Promise<ScheduleExplanationResponse> {
    const response = await apiClient.post<ScheduleExplanationResponse>(
      `${BASE_URL}/explain`,
      request
    );
    return response.data;
  },

  /**
   * Get AI explanation for why a job was not assigned.
   */
  async explainUnassignedJob(
    request: UnassignedJobExplanationRequest
  ): Promise<UnassignedJobExplanationResponse> {
    const response = await apiClient.post<UnassignedJobExplanationResponse>(
      `${BASE_URL}/explain-unassigned`,
      request
    );
    return response.data;
  },

  /**
   * Parse natural language constraints into structured format.
   */
  async parseConstraints(
    request: ParseConstraintsRequest
  ): Promise<ParseConstraintsResponse> {
    const response = await apiClient.post<ParseConstraintsResponse>(
      `${BASE_URL}/parse-constraints`,
      request
    );
    return response.data;
  },

  /**
   * Get jobs that are ready to be scheduled for a date range.
   */
  async getJobsReadyToSchedule(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<JobsReadyToScheduleResponse> {
    const response = await apiClient.get<JobsReadyToScheduleResponse>(
      '/schedule/jobs-ready',
      { 
        params: {
          date_from: params?.start_date,
          date_to: params?.end_date,
        }
      }
    );
    return response.data;
  },

  /**
   * Search customers by name, phone, or email.
   * Returns simplified customer data for dropdowns.
   */
  async searchCustomers(query: string): Promise<CustomerSearchResult[]> {
    const response = await apiClient.get<PaginatedResponse<CustomerSearchResult>>(
      '/customers',
      { params: { search: query, page_size: 20 } }
    );
    return response.data.items;
  },
};
