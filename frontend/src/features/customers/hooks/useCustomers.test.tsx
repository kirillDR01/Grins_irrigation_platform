import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useCustomers, useCustomer, useCustomerSearch, customerKeys } from './useCustomers';
import { customerApi } from '../api/customerApi';

// Mock the customerApi
vi.mock('../api/customerApi', () => ({
  customerApi: {
    list: vi.fn(),
    get: vi.fn(),
    search: vi.fn(),
  },
}));

const mockCustomer = {
  id: '1',
  first_name: 'John',
  last_name: 'Doe',
  phone: '6125551234',
  email: 'john@example.com',
  is_priority: false,
  is_red_flag: false,
  is_slow_payer: false,
  is_new_customer: true,
  sms_opt_in: true,
  email_opt_in: true,
  lead_source: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockCustomer],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

// Create a wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('customerKeys', () => {
  it('should generate correct all key', () => {
    expect(customerKeys.all).toEqual(['customers']);
  });

  it('should generate correct lists key', () => {
    expect(customerKeys.lists()).toEqual(['customers', 'list']);
  });

  it('should generate correct list key with params', () => {
    const params = { page: 1, page_size: 20 };
    expect(customerKeys.list(params)).toEqual(['customers', 'list', params]);
  });

  it('should generate correct list key without params', () => {
    expect(customerKeys.list()).toEqual(['customers', 'list', undefined]);
  });

  it('should generate correct details key', () => {
    expect(customerKeys.details()).toEqual(['customers', 'detail']);
  });

  it('should generate correct detail key', () => {
    expect(customerKeys.detail('123')).toEqual(['customers', 'detail', '123']);
  });

  it('should generate correct search key', () => {
    expect(customerKeys.search('john')).toEqual(['customers', 'search', 'john']);
  });
});

describe('useCustomers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch customers successfully', async () => {
    vi.mocked(customerApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useCustomers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(customerApi.list).toHaveBeenCalledWith(undefined);
  });

  it('should fetch customers with params', async () => {
    const params = { page: 2, page_size: 10 };
    vi.mocked(customerApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useCustomers(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.list).toHaveBeenCalledWith(params);
  });

  it('should handle error', async () => {
    const error = new Error('Failed to fetch');
    vi.mocked(customerApi.list).mockRejectedValue(error);

    const { result } = renderHook(() => useCustomers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });

  it('should be in loading state initially', () => {
    vi.mocked(customerApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useCustomers(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe('useCustomer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch single customer successfully', async () => {
    vi.mocked(customerApi.get).mockResolvedValue(mockCustomer);

    const { result } = renderHook(() => useCustomer('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCustomer);
    expect(customerApi.get).toHaveBeenCalledWith('1');
  });

  it('should not fetch when id is empty', () => {
    const { result } = renderHook(() => useCustomer(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(customerApi.get).not.toHaveBeenCalled();
  });

  it('should handle error', async () => {
    const error = new Error('Customer not found');
    vi.mocked(customerApi.get).mockRejectedValue(error);

    const { result } = renderHook(() => useCustomer('999'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useCustomerSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should search customers when query is at least 2 characters', async () => {
    vi.mocked(customerApi.search).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useCustomerSearch('jo'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(customerApi.search).toHaveBeenCalledWith('jo');
  });

  it('should not search when query is less than 2 characters', () => {
    const { result } = renderHook(() => useCustomerSearch('j'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(customerApi.search).not.toHaveBeenCalled();
  });

  it('should not search when query is empty', () => {
    const { result } = renderHook(() => useCustomerSearch(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(customerApi.search).not.toHaveBeenCalled();
  });

  it('should handle search error', async () => {
    const error = new Error('Search failed');
    vi.mocked(customerApi.search).mockRejectedValue(error);

    const { result } = renderHook(() => useCustomerSearch('john'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});
