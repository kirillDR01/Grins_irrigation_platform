import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useUpdateCustomerFlags,
} from './useCustomerMutations';
import { customerApi } from '../api/customerApi';

// Mock the customerApi
vi.mock('../api/customerApi', () => ({
  customerApi: {
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateFlags: vi.fn(),
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

// Create a wrapper with QueryClientProvider
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useCreateCustomer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create customer successfully', async () => {
    vi.mocked(customerApi.create).mockResolvedValue(mockCustomer);

    const { result } = renderHook(() => useCreateCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        first_name: 'John',
        last_name: 'Doe',
        phone: '6125551234',
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.create).toHaveBeenCalledWith({
      first_name: 'John',
      last_name: 'Doe',
      phone: '6125551234',
    });
  });

  it('should handle create error', async () => {
    const error = new Error('Failed to create');
    vi.mocked(customerApi.create).mockRejectedValue(error);

    const { result } = renderHook(() => useCreateCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        first_name: 'John',
        last_name: 'Doe',
        phone: '6125551234',
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });

  it('should complete mutation with delayed response', async () => {
    vi.mocked(customerApi.create).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockCustomer), 50))
    );

    const { result } = renderHook(() => useCreateCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        first_name: 'John',
        last_name: 'Doe',
        phone: '6125551234',
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useUpdateCustomer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should update customer successfully', async () => {
    const updatedCustomer = { ...mockCustomer, first_name: 'Jane' };
    vi.mocked(customerApi.update).mockResolvedValue(updatedCustomer);

    const { result } = renderHook(() => useUpdateCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: '1',
        data: { first_name: 'Jane' },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.update).toHaveBeenCalledWith('1', { first_name: 'Jane' });
  });

  it('should handle update error', async () => {
    const error = new Error('Failed to update');
    vi.mocked(customerApi.update).mockRejectedValue(error);

    const { result } = renderHook(() => useUpdateCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: '1',
        data: { first_name: 'Jane' },
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useDeleteCustomer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should delete customer successfully', async () => {
    vi.mocked(customerApi.delete).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.delete).toHaveBeenCalledWith('1');
  });

  it('should handle delete error', async () => {
    const error = new Error('Failed to delete');
    vi.mocked(customerApi.delete).mockRejectedValue(error);

    const { result } = renderHook(() => useDeleteCustomer(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useUpdateCustomerFlags', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should update customer flags successfully', async () => {
    const updatedCustomer = { ...mockCustomer, is_priority: true };
    vi.mocked(customerApi.updateFlags).mockResolvedValue(updatedCustomer);

    const { result } = renderHook(() => useUpdateCustomerFlags(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: '1',
        flags: { is_priority: true },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.updateFlags).toHaveBeenCalledWith('1', { is_priority: true });
  });

  it('should update multiple flags', async () => {
    const updatedCustomer = { ...mockCustomer, is_priority: true, is_red_flag: true };
    vi.mocked(customerApi.updateFlags).mockResolvedValue(updatedCustomer);

    const { result } = renderHook(() => useUpdateCustomerFlags(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: '1',
        flags: { is_priority: true, is_red_flag: true },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(customerApi.updateFlags).toHaveBeenCalledWith('1', {
      is_priority: true,
      is_red_flag: true,
    });
  });

  it('should handle flags update error', async () => {
    const error = new Error('Failed to update flags');
    vi.mocked(customerApi.updateFlags).mockRejectedValue(error);

    const { result } = renderHook(() => useUpdateCustomerFlags(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: '1',
        flags: { is_priority: true },
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});
