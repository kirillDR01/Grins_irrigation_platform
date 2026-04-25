/**
 * Tests for useAppointmentNotes and useSaveAppointmentNotes hooks.
 * Validates: Requirements 8.1–8.4, 13.5
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useAppointmentNotes,
  useSaveAppointmentNotes,
  appointmentNoteKeys,
} from './useAppointmentNotes';

// ── Mock apiClient ───────────────────────────────────────────────────────────

const mockGet = vi.fn();
const mockPatch = vi.fn();

vi.mock('@/core/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    patch: (...args: unknown[]) => mockPatch(...args),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return {
    queryClient,
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  };
}

// ── Query key structure ──────────────────────────────────────────────────────

describe('appointmentNoteKeys', () => {
  it('has correct all key', () => {
    expect(appointmentNoteKeys.all).toEqual(['appointment-notes']);
  });

  it('has correct detail key', () => {
    expect(appointmentNoteKeys.detail('appt-001')).toEqual([
      'appointment-notes',
      'appt-001',
    ]);
  });
});

// ── useAppointmentNotes ──────────────────────────────────────────────────────

describe('useAppointmentNotes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches notes on mount and returns data', async () => {
    const notesData = {
      appointment_id: 'appt-001',
      body: 'Test notes body',
      updated_at: '2025-06-15T14:30:00Z',
      updated_by: { id: 'staff-1', name: 'Viktor', role: 'admin' },
    };
    mockGet.mockResolvedValueOnce({ data: notesData });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAppointmentNotes('appt-001'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(notesData);
    expect(mockGet).toHaveBeenCalledWith('/appointments/appt-001/notes');
  });

  it('returns default empty body when fetch fails (404)', async () => {
    mockGet.mockRejectedValueOnce(new Error('Not found'));

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useAppointmentNotes('appt-001'), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.body).toBe('');
    expect(result.current.data?.appointment_id).toBe('appt-001');
    expect(result.current.data?.updated_by).toBeNull();
  });

  it('does not fetch when appointmentId is empty', () => {
    const { wrapper } = createWrapper();
    renderHook(() => useAppointmentNotes(''), { wrapper });

    expect(mockGet).not.toHaveBeenCalled();
  });
});

// ── useSaveAppointmentNotes ──────────────────────────────────────────────────

describe('useSaveAppointmentNotes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls PATCH with correct endpoint and body', async () => {
    const savedData = {
      appointment_id: 'appt-001',
      body: 'Updated notes',
      updated_at: '2025-06-15T15:00:00Z',
      updated_by: { id: 'staff-1', name: 'Admin', role: 'admin' },
    };
    mockPatch.mockResolvedValueOnce({ data: savedData });

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useSaveAppointmentNotes(), { wrapper });

    await result.current.mutateAsync({
      appointmentId: 'appt-001',
      body: 'Updated notes',
    });

    expect(mockPatch).toHaveBeenCalledWith('/appointments/appt-001/notes', {
      body: 'Updated notes',
    });
  });

  it('invalidates notes query cache on success', async () => {
    const savedData = {
      appointment_id: 'appt-001',
      body: 'New body',
      updated_at: '2025-06-15T15:00:00Z',
      updated_by: null,
    };
    mockPatch.mockResolvedValueOnce({ data: savedData });

    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useSaveAppointmentNotes(), { wrapper });

    await result.current.mutateAsync({
      appointmentId: 'appt-001',
      body: 'New body',
    });

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: appointmentNoteKeys.detail('appt-001'),
      });
    });
  });

  it('performs optimistic update on mutate', async () => {
    // Pre-seed the cache with existing notes
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(appointmentNoteKeys.detail('appt-001'), {
      appointment_id: 'appt-001',
      body: 'Old body',
      updated_at: '2025-06-15T14:00:00Z',
      updated_by: null,
    });

    // Make the PATCH hang so we can check optimistic state
    let resolvePatch: (value: unknown) => void;
    mockPatch.mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePatch = resolve;
      }),
    );

    const { result } = renderHook(() => useSaveAppointmentNotes(), { wrapper });

    // Start mutation (don't await)
    const mutationPromise = result.current.mutateAsync({
      appointmentId: 'appt-001',
      body: 'Optimistic body',
    });

    // Check optimistic update was applied
    await waitFor(() => {
      const cached = queryClient.getQueryData(
        appointmentNoteKeys.detail('appt-001'),
      ) as { body: string } | undefined;
      expect(cached?.body).toBe('Optimistic body');
    });

    // Resolve the PATCH
    resolvePatch!({
      data: {
        appointment_id: 'appt-001',
        body: 'Optimistic body',
        updated_at: '2025-06-15T15:00:00Z',
        updated_by: null,
      },
    });

    await mutationPromise;
  });

  it('reverts optimistic update on failure', async () => {
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(appointmentNoteKeys.detail('appt-001'), {
      appointment_id: 'appt-001',
      body: 'Original body',
      updated_at: '2025-06-15T14:00:00Z',
      updated_by: null,
    });

    mockPatch.mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(() => useSaveAppointmentNotes(), { wrapper });

    try {
      await result.current.mutateAsync({
        appointmentId: 'appt-001',
        body: 'Failed update',
      });
    } catch {
      // Expected to throw
    }

    // Cache should be reverted to original
    await waitFor(() => {
      const cached = queryClient.getQueryData(
        appointmentNoteKeys.detail('appt-001'),
      ) as { body: string } | undefined;
      expect(cached?.body).toBe('Original body');
    });
  });
});
