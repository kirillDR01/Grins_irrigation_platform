/**
 * Tests for Staff query hooks.
 */

import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useStaff, useStaffMember, useAvailableStaff, staffKeys } from './useStaff';
import { staffApi } from '../api/staffApi';
import type { ReactNode } from 'react';

// Mock the staff API
vi.mock('../api/staffApi', () => ({
  staffApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getAvailable: vi.fn(),
  },
}));

const mockStaff = {
  id: 'staff-123',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  role: 'tech' as const,
  skill_level: null,
  certifications: null,
  is_active: true,
  is_available: true,
  availability_notes: null,
  hourly_rate: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

describe('staffKeys', () => {
  it('generates correct all key', () => {
    expect(staffKeys.all).toEqual(['staff']);
  });

  it('generates correct lists key', () => {
    expect(staffKeys.lists()).toEqual(['staff', 'list']);
  });

  it('generates correct list key with params', () => {
    expect(staffKeys.list({ role: 'tech' })).toEqual(['staff', 'list', { role: 'tech' }]);
  });

  it('generates correct details key', () => {
    expect(staffKeys.details()).toEqual(['staff', 'detail']);
  });

  it('generates correct detail key', () => {
    expect(staffKeys.detail('123')).toEqual(['staff', 'detail', '123']);
  });

  it('generates correct available key', () => {
    expect(staffKeys.available()).toEqual(['staff', 'available']);
  });
});

describe('useStaff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches staff list', async () => {
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [mockStaff],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const { result } = renderHook(() => useStaff(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.list).toHaveBeenCalledWith(undefined);
    expect(result.current.data?.items).toHaveLength(1);
  });

  it('fetches staff list with params', async () => {
    vi.mocked(staffApi.list).mockResolvedValue({
      items: [mockStaff],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const params = { role: 'tech', is_active: true };
    const { result } = renderHook(() => useStaff(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.list).toHaveBeenCalledWith(params);
  });
});

describe('useStaffMember', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches single staff member', async () => {
    vi.mocked(staffApi.getById).mockResolvedValue(mockStaff);

    const { result } = renderHook(() => useStaffMember('staff-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.getById).toHaveBeenCalledWith('staff-123');
    expect(result.current.data?.id).toBe('staff-123');
  });

  it('does not fetch when id is undefined', () => {
    const { result } = renderHook(() => useStaffMember(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(staffApi.getById).not.toHaveBeenCalled();
  });
});

describe('useAvailableStaff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches available staff', async () => {
    vi.mocked(staffApi.getAvailable).mockResolvedValue({
      items: [mockStaff],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const { result } = renderHook(() => useAvailableStaff(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.getAvailable).toHaveBeenCalled();
    expect(result.current.data?.items[0].is_available).toBe(true);
  });
});
