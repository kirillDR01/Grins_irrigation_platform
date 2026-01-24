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
} from '../types';

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
};
