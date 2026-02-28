import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useUpdateLead, useConvertLead, useDeleteLead } from './useLeadMutations';
import { leadApi } from '../api/leadApi';

vi.mock('../api/leadApi', () => ({
  leadApi: {
    list: vi.fn(),
    getById: vi.fn(),
    update: vi.fn(),
    convert: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockLead = {
  id: 'lead-1',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  zip_code: '55344',
  situation: 'new_system' as const,
  notes: 'Interested in new irrigation',
  source_site: 'residential',
  status: 'new' as const,
  assigned_to: null,
  customer_id: null,
  contacted_at: null,
  converted_at: null,
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
};

const mockConversionResponse = {
  success: true,
  lead_id: 'lead-1',
  customer_id: 'cust-1',
  job_id: 'job-1',
  message: 'Lead converted successfully',
};

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

describe('useUpdateLead', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should update lead successfully', async () => {
    const updatedLead = { ...mockLead, status: 'contacted' as const };
    vi.mocked(leadApi.update).mockResolvedValue(updatedLead);

    const { result } = renderHook(() => useUpdateLead(), { wrapper: createWrapper() });

    await result.current.mutateAsync({ id: 'lead-1', data: { status: 'contacted' } });

    expect(leadApi.update).toHaveBeenCalledWith('lead-1', { status: 'contacted' });
  });

  it('should handle update error', async () => {
    vi.mocked(leadApi.update).mockRejectedValue(new Error('Invalid transition'));

    const { result } = renderHook(() => useUpdateLead(), { wrapper: createWrapper() });

    await expect(
      result.current.mutateAsync({ id: 'lead-1', data: { status: 'converted' } })
    ).rejects.toThrow('Invalid transition');
  });
});

describe('useConvertLead', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should convert lead successfully', async () => {
    vi.mocked(leadApi.convert).mockResolvedValue(mockConversionResponse);

    const { result } = renderHook(() => useConvertLead(), { wrapper: createWrapper() });

    const response = await result.current.mutateAsync({
      id: 'lead-1',
      data: { first_name: 'John', last_name: 'Doe', create_job: true },
    });

    expect(leadApi.convert).toHaveBeenCalledWith('lead-1', {
      first_name: 'John',
      last_name: 'Doe',
      create_job: true,
    });
    expect(response).toEqual(mockConversionResponse);
  });

  it('should handle conversion error', async () => {
    vi.mocked(leadApi.convert).mockRejectedValue(new Error('Already converted'));

    const { result } = renderHook(() => useConvertLead(), { wrapper: createWrapper() });

    await expect(
      result.current.mutateAsync({ id: 'lead-1', data: { create_job: false } })
    ).rejects.toThrow('Already converted');
  });
});

describe('useDeleteLead', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should delete lead successfully', async () => {
    vi.mocked(leadApi.delete).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteLead(), { wrapper: createWrapper() });

    await result.current.mutateAsync('lead-1');

    expect(leadApi.delete).toHaveBeenCalledWith('lead-1');
  });

  it('should handle delete error', async () => {
    vi.mocked(leadApi.delete).mockRejectedValue(new Error('Not found'));

    const { result } = renderHook(() => useDeleteLead(), { wrapper: createWrapper() });

    await expect(result.current.mutateAsync('lead-1')).rejects.toThrow('Not found');
  });
});
