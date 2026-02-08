import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useLeads, useLead, leadKeys } from './useLeads';
import { leadApi } from '../api/leadApi';

// Mock the leadApi
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

const mockPaginatedResponse = {
  items: [mockLead],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('leadKeys', () => {
  it('should generate correct all key', () => {
    expect(leadKeys.all).toEqual(['leads']);
  });

  it('should generate correct lists key', () => {
    expect(leadKeys.lists()).toEqual(['leads', 'list']);
  });

  it('should generate correct list key with params', () => {
    const params = { status: 'new' as const, page: 1 };
    expect(leadKeys.list(params)).toEqual(['leads', 'list', params]);
  });

  it('should generate correct list key without params', () => {
    expect(leadKeys.list()).toEqual(['leads', 'list', undefined]);
  });

  it('should generate correct details key', () => {
    expect(leadKeys.details()).toEqual(['leads', 'detail']);
  });

  it('should generate correct detail key', () => {
    expect(leadKeys.detail('lead-1')).toEqual(['leads', 'detail', 'lead-1']);
  });
});

describe('useLeads', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch leads list successfully', async () => {
    vi.mocked(leadApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useLeads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(leadApi.list).toHaveBeenCalledWith(undefined);
  });

  it('should pass params to API', async () => {
    vi.mocked(leadApi.list).mockResolvedValue(mockPaginatedResponse);
    const params = { status: 'new' as const, page: 2, page_size: 10 };

    const { result } = renderHook(() => useLeads(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(leadApi.list).toHaveBeenCalledWith(params);
  });

  it('should handle fetch error', async () => {
    const error = new Error('Network error');
    vi.mocked(leadApi.list).mockRejectedValue(error);

    const { result } = renderHook(() => useLeads(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeDefined();
  });
});

describe('useLead', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch single lead by ID', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(mockLead);

    const { result } = renderHook(() => useLead('lead-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockLead);
    expect(leadApi.getById).toHaveBeenCalledWith('lead-1');
  });

  it('should not fetch when id is empty', () => {
    const { result } = renderHook(() => useLead(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(leadApi.getById).not.toHaveBeenCalled();
  });
});
