/**
 * Tests for useAICategorize hook
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useAICategorize } from './useAICategorize';
import { aiApi } from '../api/aiApi';
import type { JobCategorizationResponse } from '../types';

vi.mock('../api/aiApi');

describe('useAICategorize', () => {
  const mockResponse: JobCategorizationResponse = {
    categorizations: [
      {
        job_id: '1',
        suggested_category: 'seasonal',
        suggested_job_type: 'spring_startup',
        suggested_price: '$150',
        confidence_score: 0.92,
        ai_notes: 'Standard spring startup',
        requires_review: false,
      },
      {
        job_id: '2',
        suggested_category: 'repair',
        suggested_job_type: 'broken_head',
        suggested_price: '$50',
        confidence_score: 0.65,
        ai_notes: 'Low confidence - needs review',
        requires_review: true,
      },
    ],
    summary: {
      total_jobs: 2,
      ready_to_schedule: 1,
      requires_review: 1,
      avg_confidence: 0.785,
    },
    audit_log_id: 'audit-123',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useAICategorize());

    expect(result.current.categorizations).toEqual([]);
    expect(result.current.summary).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.auditLogId).toBeNull();
  });

  it('categorizes jobs successfully', async () => {
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAICategorize());

    result.current.categorizeJobs({ include_uncategorized_only: true });

    await waitFor(() => {
      expect(result.current.categorizations).toEqual(mockResponse.categorizations);
    });

    expect(result.current.summary).toEqual(mockResponse.summary);
    expect(result.current.auditLogId).toBe('audit-123');
    expect(result.current.error).toBeNull();
  });

  it('handles categorization errors', async () => {
    const error = new Error('API error');
    vi.mocked(aiApi.categorizeJobs).mockRejectedValue(error);

    const { result } = renderHook(() => useAICategorize());

    result.current.categorizeJobs({ include_uncategorized_only: true });

    await waitFor(() => {
      expect(result.current.error).toBe('API error');
    });

    expect(result.current.categorizations).toEqual([]);
    expect(result.current.summary).toBeNull();
  });

  it('approves jobs in bulk', async () => {
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAICategorize());

    // First categorize
    result.current.categorizeJobs({ include_uncategorized_only: true });

    await waitFor(() => {
      expect(result.current.categorizations).toHaveLength(2);
    });

    // Then approve one job
    result.current.approveBulk(['1']);

    await waitFor(() => {
      expect(result.current.categorizations).toHaveLength(1);
    });

    expect(result.current.categorizations[0].job_id).toBe('2');
    expect(result.current.summary?.total_jobs).toBe(1);
    expect(result.current.summary?.ready_to_schedule).toBe(0);
  });

  it('clears categorizations', async () => {
    vi.mocked(aiApi.categorizeJobs).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useAICategorize());

    // First categorize
    result.current.categorizeJobs({ include_uncategorized_only: true });

    await waitFor(() => {
      expect(result.current.categorizations).toHaveLength(2);
    });

    // Then clear
    result.current.clearCategorizations();

    // Wait for state update
    await waitFor(() => {
      expect(result.current.categorizations).toEqual([]);
    });

    expect(result.current.summary).toBeNull();
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

    result.current.categorizeJobs({ include_uncategorized_only: true });

    // Wait for loading state to be set
    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    // Resolve the promise
    resolvePromise!(mockResponse);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });
});
