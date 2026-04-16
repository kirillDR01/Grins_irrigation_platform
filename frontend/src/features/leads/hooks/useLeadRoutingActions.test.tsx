/**
 * Tests for useLeadRoutingActions (H-1 — bughunt 2026-04-16).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import type { ReactNode } from 'react';

import { useLeadRoutingActions } from './useLeadRoutingActions';
import { leadApi } from '../api/leadApi';
import type { Lead, LeadMoveResponse, DuplicateConflictError } from '../types';

// The hook delegates to leadApi via useLeadMutations — mock the whole API layer.
vi.mock('../api/leadApi', () => ({
  leadApi: {
    moveToJobs: vi.fn(),
    moveToSales: vi.fn(),
    markContacted: vi.fn(),
    delete: vi.fn(),
  },
}));

// sonner's toast surface — mock to stay out of the DOM and spy on calls.
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

/** Minimal Lead fixture. */
const baseLead: Lead = {
  id: 'lead-1',
  name: 'Test Lead',
  phone: '6125550000',
  email: 'test@example.com',
  address: null,
  city: null,
  state: null,
  zip_code: null,
  situation: 'repair',
  notes: null,
  source_site: 'residential',
  status: 'new',
  assigned_to: null,
  customer_id: null,
  contacted_at: null,
  converted_at: null,
  lead_source: 'website',
  source_detail: null,
  intake_tag: null,
  action_tags: [],
  sms_consent: true,
  terms_accepted: true,
  email_marketing_consent: false,
  job_requested: null,
  last_contacted_at: null,
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
};

/** Successful move response (no requires_estimate_warning). */
const successMoveResponse: LeadMoveResponse = {
  success: true,
  lead_id: 'lead-1',
  customer_id: 'cust-1',
  job_id: 'job-1',
  sales_entry_id: null,
  message: 'Moved to Jobs',
  requires_estimate_warning: false,
  merged_into_customer: null,
};

/** Move response flagged as requiring an estimate override. */
const requiresEstimateMoveResponse: LeadMoveResponse = {
  ...successMoveResponse,
  message: 'Requires estimate',
  requires_estimate_warning: true,
};

/** 409 conflict-response factory matching the CR-6 DuplicateConflictError shape. */
function duplicate409Error(): AxiosError {
  const detail: DuplicateConflictError = {
    error: 'duplicate_found',
    lead_id: 'lead-1',
    phone: baseLead.phone,
    email: baseLead.email,
    duplicates: [
      {
        id: 'existing-customer-1',
        first_name: 'Existing',
        last_name: 'Customer',
        phone: baseLead.phone,
        email: baseLead.email,
      },
    ],
  };
  return new AxiosError(
    'Request failed with status code 409',
    'ERR_BAD_REQUEST',
    undefined,
    undefined,
    {
      status: 409,
      data: { detail },
      headers: {},
      statusText: 'Conflict',
      config: {} as InternalAxiosRequestConfig,
    } as AxiosResponse,
  );
}

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useLeadRoutingActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('exposes mutations and action callbacks', () => {
    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.markContacted).toBe('function');
    expect(typeof result.current.moveToJobs).toBe('function');
    expect(typeof result.current.moveToSales).toBe('function');
    expect(typeof result.current.deleteLead).toBe('function');
    expect(result.current.requiresEstimateState).toBeNull();
    expect(result.current.conflictState).toBeNull();
    expect(result.current.moveToJobsMutation).toBeDefined();
    expect(result.current.moveToSalesMutation).toBeDefined();
    expect(result.current.markContactedMutation).toBeDefined();
    expect(result.current.deleteLeadMutation).toBeDefined();
  });

  it('onMoveToJobs with no duplicate → mutation fires, navigate("/jobs")', async () => {
    const navigate = vi.fn();
    vi.mocked(leadApi.moveToJobs).mockResolvedValue(successMoveResponse);

    const { result } = renderHook(
      () => useLeadRoutingActions({ navigate, navigateOnSuccess: true }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    expect(leadApi.moveToJobs).toHaveBeenCalledWith('lead-1', false);
    expect(navigate).toHaveBeenCalledWith('/jobs');
    expect(result.current.conflictState).toBeNull();
    expect(result.current.requiresEstimateState).toBeNull();
  });

  it('onMoveToJobs does NOT navigate when navigateOnSuccess is false', async () => {
    const navigate = vi.fn();
    vi.mocked(leadApi.moveToJobs).mockResolvedValue(successMoveResponse);

    const { result } = renderHook(
      () => useLeadRoutingActions({ navigate, navigateOnSuccess: false }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    expect(leadApi.moveToJobs).toHaveBeenCalledWith('lead-1', false);
    expect(navigate).not.toHaveBeenCalled();
  });

  it('onMoveToJobs with 409 → opens conflict state; onConvertAnyway retries with force=true', async () => {
    const navigate = vi.fn();
    vi.mocked(leadApi.moveToJobs)
      .mockRejectedValueOnce(duplicate409Error())
      .mockResolvedValueOnce(successMoveResponse);

    const { result } = renderHook(
      () => useLeadRoutingActions({ navigate, navigateOnSuccess: true }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    // Conflict state should now hold the 409 detail.
    await waitFor(() => {
      expect(result.current.conflictState).not.toBeNull();
    });
    expect(result.current.conflictState?.target).toBe('jobs');
    expect(result.current.conflictState?.duplicates).toHaveLength(1);
    expect(result.current.conflictState?.duplicates[0].id).toBe(
      'existing-customer-1',
    );

    // onConvertAnyway retries with force=true.
    await act(async () => {
      await result.current.onConvertAnyway();
    });

    expect(leadApi.moveToJobs).toHaveBeenCalledTimes(2);
    expect(leadApi.moveToJobs).toHaveBeenNthCalledWith(2, 'lead-1', true);
    expect(navigate).toHaveBeenCalledWith('/jobs');
    expect(result.current.conflictState).toBeNull();
  });

  it('onMoveToJobs with requires_estimate_warning → opens requires-estimate state', async () => {
    vi.mocked(leadApi.moveToJobs).mockResolvedValue(
      requiresEstimateMoveResponse,
    );

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    await waitFor(() => {
      expect(result.current.requiresEstimateState).not.toBeNull();
    });
    expect(result.current.requiresEstimateState?.lead.id).toBe('lead-1');
    expect(result.current.requiresEstimateState?.target).toBe('jobs');
  });

  it('resolveRequiresEstimate("jobs-force") retries moveToJobs with force=true', async () => {
    vi.mocked(leadApi.moveToJobs)
      .mockResolvedValueOnce(requiresEstimateMoveResponse)
      .mockResolvedValueOnce(successMoveResponse);

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    await waitFor(() => {
      expect(result.current.requiresEstimateState).not.toBeNull();
    });

    await act(async () => {
      await result.current.resolveRequiresEstimate('jobs-force');
    });

    expect(leadApi.moveToJobs).toHaveBeenCalledTimes(2);
    expect(leadApi.moveToJobs).toHaveBeenNthCalledWith(2, 'lead-1', true);
    expect(result.current.requiresEstimateState).toBeNull();
  });

  it('resolveRequiresEstimate("sales") calls moveToSales instead', async () => {
    vi.mocked(leadApi.moveToJobs).mockResolvedValue(
      requiresEstimateMoveResponse,
    );
    vi.mocked(leadApi.moveToSales).mockResolvedValue(successMoveResponse);

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    await waitFor(() => {
      expect(result.current.requiresEstimateState).not.toBeNull();
    });

    await act(async () => {
      await result.current.resolveRequiresEstimate('sales');
    });

    expect(leadApi.moveToSales).toHaveBeenCalledWith('lead-1');
    expect(result.current.requiresEstimateState).toBeNull();
  });

  it('resolveRequiresEstimate("cancel") just closes the dialog', async () => {
    vi.mocked(leadApi.moveToJobs).mockResolvedValue(
      requiresEstimateMoveResponse,
    );

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    await waitFor(() => {
      expect(result.current.requiresEstimateState).not.toBeNull();
    });

    await act(async () => {
      await result.current.resolveRequiresEstimate('cancel');
    });

    expect(leadApi.moveToJobs).toHaveBeenCalledTimes(1);
    expect(leadApi.moveToSales).not.toHaveBeenCalled();
    expect(result.current.requiresEstimateState).toBeNull();
  });

  it('markContacted invokes useMarkContacted with the lead id', async () => {
    vi.mocked(leadApi.markContacted).mockResolvedValue(baseLead);

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.markContacted(baseLead);
    });

    expect(leadApi.markContacted).toHaveBeenCalledWith('lead-1');
  });

  it('onUseExisting navigates to the customer detail page', async () => {
    const navigate = vi.fn();
    vi.mocked(leadApi.moveToJobs).mockRejectedValue(duplicate409Error());

    const { result } = renderHook(
      () => useLeadRoutingActions({ navigate }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.moveToJobs(baseLead);
    });

    await waitFor(() => {
      expect(result.current.conflictState).not.toBeNull();
    });

    const dup = result.current.conflictState!.duplicates[0];
    act(() => {
      result.current.onUseExisting(dup);
    });

    expect(navigate).toHaveBeenCalledWith(`/customers/${dup.id}`);
    expect(result.current.conflictState).toBeNull();
  });

  it('deleteLead calls leadApi.delete and resolves to true on success', async () => {
    vi.mocked(leadApi.delete).mockResolvedValue(undefined);

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.deleteLead(baseLead);
    });

    expect(leadApi.delete).toHaveBeenCalledWith('lead-1');
    expect(ok).toBe(true);
  });

  it('deleteLead resolves to false when the API rejects', async () => {
    vi.mocked(leadApi.delete).mockRejectedValue(new Error('boom'));

    const { result } = renderHook(() => useLeadRoutingActions(), {
      wrapper: createWrapper(),
    });

    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.deleteLead(baseLead);
    });

    expect(ok).toBe(false);
  });
});
