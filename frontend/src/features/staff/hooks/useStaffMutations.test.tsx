/**
 * Tests for Staff mutation hooks.
 */

import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useCreateStaff,
  useUpdateStaff,
  useDeleteStaff,
  useUpdateStaffAvailability,
} from './useStaffMutations';
import { staffApi } from '../api/staffApi';
import type { ReactNode } from 'react';

// Mock the staff API
vi.mock('../api/staffApi', () => ({
  staffApi: {
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    updateAvailability: vi.fn(),
  },
}));

const mockStaff = {
  id: 'staff-123',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  role: 'tech' as const,
  skill_level: 'senior' as const,
  certifications: null,
  availability_notes: null,
  hourly_rate: null,
  is_active: true,
  is_available: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

describe('useCreateStaff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates staff member', async () => {
    vi.mocked(staffApi.create).mockResolvedValue(mockStaff);

    const { result } = renderHook(() => useCreateStaff(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      name: 'John Doe',
      phone: '6125551234',
      email: 'john@example.com',
      role: 'tech',
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.create).toHaveBeenCalled();
    expect(result.current.data?.id).toBe('staff-123');
  });
});

describe('useUpdateStaff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates staff member', async () => {
    vi.mocked(staffApi.update).mockResolvedValue(mockStaff);

    const { result } = renderHook(() => useUpdateStaff(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      id: 'staff-123',
      data: { name: 'John Updated' },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.update).toHaveBeenCalledWith('staff-123', { name: 'John Updated' });
  });
});

describe('useDeleteStaff', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('deletes staff member', async () => {
    vi.mocked(staffApi.delete).mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteStaff(), {
      wrapper: createWrapper(),
    });

    result.current.mutate('staff-123');

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.delete).toHaveBeenCalledWith('staff-123');
  });
});

describe('useUpdateStaffAvailability', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates staff availability', async () => {
    const updatedStaff = { ...mockStaff, is_available: false };
    vi.mocked(staffApi.updateAvailability).mockResolvedValue(updatedStaff);

    const { result } = renderHook(() => useUpdateStaffAvailability(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      id: 'staff-123',
      data: { is_available: false },
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(staffApi.updateAvailability).toHaveBeenCalledWith('staff-123', {
      is_available: false,
    });
    expect(result.current.data?.is_available).toBe(false);
  });
});
