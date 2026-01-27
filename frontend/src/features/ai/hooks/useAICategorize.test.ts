/**
 * Tests for useAICategorize hook
 * 
 * Updated to match new backend API that returns a single categorization result
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useAICategorize } from './useAICategorize';
import { aiApi } from '../api/aiApi';
import type { JobCategorizationResponse, JobCategorizationRequest } from '../types';

vi.mock('../api/aiApi');

describe('useAICategorize', () => {
  const mockResponse: JobCategorizationResponse = {
    audit_id: 'audit-123',
    category: 'ready_to_schedule',
    confidence_score: 90,
    reasoning: 'Standard service with known pricing',
    suggested_services: ['head_replacement'],
    needs_review: false,
  };

  const mockRequest: JobCategorizationRequest = {
    description: 'Broken sprinkler head in front yard',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useAICategorize());

    expect(result.current.categorization).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.auditLogId).toBeNull();
  });

  it('categorizes job successfully', async () => {
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAICategorize());

    await act(async () => {
      await result.current.categorizeJobs(mockRequest);
    });

    expect(result.current.categorization).toEqual(mockResponse);
    expect(result.current.auditLogId).toBe('audit-123');
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });

  it('handles categorization errors', async () => {
    const error = new Error('API error');
    vi.mocked(aiApi.categorizeJobs).mockRejectedValue(error);

    const { result } = renderHook(() => useAICategorize());

    await act(async () => {
      await result.current.categorizeJobs(mockRequest);
    });

    expect(result.current.error).toBe('API error');
    expect(result.current.categorization).toBeNull();
  });

  it('clears categorization', async () => {
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAICategorize());

    // First categorize
    await act(async () => {
      await result.current.categorizeJobs(mockRequest);
    });

    expect(result.current.categorization).toEqual(mockResponse);

    // Then clear
    act(() => {
      result.current.clearCategorizations();
    });

    expect(result.current.categorization).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.auditLogId).toBeNull();
  });

  it('sets loading state during categorization', async () => {
    let resolvePromise: (value: JobCategorizationResponse) => void;
    const promise = new Promise<JobCategorizationResponse>((resolve) => {
      resolvePromise = resolve;
    });

    vi.mocked(aiApi.categorizeJobs).mockReturnValue(promise);

    const { result } = renderHook(() => useAICategorize());

    // Start categorization without awaiting
    act(() => {
      result.current.categorizeJobs(mockRequest);
    });

    // Wait for loading state to be set
    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    // Resolve the promise
    await act(async () => {
      resolvePromise!(mockResponse);
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('handles bulk approval', async () => {
    const { result } = renderHook(() => useAICategorize());

    // First set up some categorization
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);
    await act(async () => {
      await result.current.categorizeJobs(mockRequest);
    });

    expect(result.current.categorization).toEqual(mockResponse);

    // Then approve bulk
    await act(async () => {
      await result.current.approveBulk(['job-1', 'job-2']);
    });

    // After approval, categorization should be cleared
    expect(result.current.categorization).toBeNull();
  });
});
