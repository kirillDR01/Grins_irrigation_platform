import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useCreateAppointment,
  useUpdateAppointment,
  useCancelAppointment,
  useConfirmAppointment,
  useMarkAppointmentArrived,
  useMarkAppointmentCompleted,
  useMarkAppointmentNoShow,
} from './useAppointmentMutations';
import { appointmentApi } from '../api/appointmentApi';

// Mock the appointmentApi
vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    create: vi.fn(),
    update: vi.fn(),
    cancel: vi.fn(),
    confirm: vi.fn(),
    markArrived: vi.fn(),
    markCompleted: vi.fn(),
    markNoShow: vi.fn(),
  },
}));

const mockAppointment = {
  id: 'apt-1',
  job_id: 'job-1',
  staff_id: 'staff-1',
  scheduled_date: '2024-01-15',
  time_window_start: '09:00:00',
  time_window_end: '11:00:00',
  status: 'pending' as const,
  arrived_at: null,
  completed_at: null,
  notes: null,
  route_order: 1,
  estimated_arrival: '09:30:00',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Create a wrapper with QueryClientProvider
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

describe('useCreateAppointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create appointment successfully', async () => {
    vi.mocked(appointmentApi.create).mockResolvedValue(mockAppointment);

    const { result } = renderHook(() => useCreateAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        job_id: 'job-1',
        staff_id: 'staff-1',
        scheduled_date: '2024-01-15',
        time_window_start: '09:00:00',
        time_window_end: '11:00:00',
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.create).toHaveBeenCalledWith({
      job_id: 'job-1',
      staff_id: 'staff-1',
      scheduled_date: '2024-01-15',
      time_window_start: '09:00:00',
      time_window_end: '11:00:00',
    });
  });

  it('should handle create error', async () => {
    const error = new Error('Failed to create');
    vi.mocked(appointmentApi.create).mockRejectedValue(error);

    const { result } = renderHook(() => useCreateAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        job_id: 'job-1',
        staff_id: 'staff-1',
        scheduled_date: '2024-01-15',
        time_window_start: '09:00:00',
        time_window_end: '11:00:00',
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });

  it('should be in pending state during mutation', async () => {
    vi.mocked(appointmentApi.create).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockAppointment), 50))
    );

    const { result } = renderHook(() => useCreateAppointment(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        job_id: 'job-1',
        staff_id: 'staff-1',
        scheduled_date: '2024-01-15',
        time_window_start: '09:00:00',
        time_window_end: '11:00:00',
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });
});

describe('useUpdateAppointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should update appointment successfully', async () => {
    const updatedAppointment = { ...mockAppointment, notes: 'Updated notes' };
    vi.mocked(appointmentApi.update).mockResolvedValue(updatedAppointment);

    const { result } = renderHook(() => useUpdateAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: 'apt-1',
        data: { notes: 'Updated notes' },
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.update).toHaveBeenCalledWith('apt-1', { notes: 'Updated notes' });
  });

  it('should handle update error', async () => {
    const error = new Error('Failed to update');
    vi.mocked(appointmentApi.update).mockRejectedValue(error);

    const { result } = renderHook(() => useUpdateAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        id: 'apt-1',
        data: { notes: 'Updated notes' },
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useCancelAppointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should cancel appointment successfully', async () => {
    vi.mocked(appointmentApi.cancel).mockResolvedValue(undefined);

    const { result } = renderHook(() => useCancelAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.cancel).toHaveBeenCalledWith('apt-1');
  });

  it('should handle cancel error', async () => {
    const error = new Error('Failed to cancel');
    vi.mocked(appointmentApi.cancel).mockRejectedValue(error);

    const { result } = renderHook(() => useCancelAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useConfirmAppointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should confirm appointment successfully', async () => {
    const confirmedAppointment = { ...mockAppointment, status: 'confirmed' as const };
    vi.mocked(appointmentApi.confirm).mockResolvedValue(confirmedAppointment);

    const { result } = renderHook(() => useConfirmAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.confirm).toHaveBeenCalledWith('apt-1');
  });

  it('should handle confirm error', async () => {
    const error = new Error('Failed to confirm');
    vi.mocked(appointmentApi.confirm).mockRejectedValue(error);

    const { result } = renderHook(() => useConfirmAppointment(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useMarkAppointmentArrived', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should mark appointment as arrived successfully', async () => {
    const arrivedAppointment = {
      ...mockAppointment,
      status: 'in_progress' as const,
      arrived_at: '2024-01-15T09:30:00Z',
    };
    vi.mocked(appointmentApi.markArrived).mockResolvedValue(arrivedAppointment);

    const { result } = renderHook(() => useMarkAppointmentArrived(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.markArrived).toHaveBeenCalledWith('apt-1');
  });

  it('should handle mark arrived error', async () => {
    const error = new Error('Failed to mark arrived');
    vi.mocked(appointmentApi.markArrived).mockRejectedValue(error);

    const { result } = renderHook(() => useMarkAppointmentArrived(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useMarkAppointmentCompleted', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should mark appointment as completed successfully', async () => {
    const completedAppointment = {
      ...mockAppointment,
      status: 'completed' as const,
      completed_at: '2024-01-15T10:30:00Z',
    };
    vi.mocked(appointmentApi.markCompleted).mockResolvedValue(completedAppointment);

    const { result } = renderHook(() => useMarkAppointmentCompleted(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.markCompleted).toHaveBeenCalledWith('apt-1');
  });

  it('should handle mark completed error', async () => {
    const error = new Error('Failed to mark completed');
    vi.mocked(appointmentApi.markCompleted).mockRejectedValue(error);

    const { result } = renderHook(() => useMarkAppointmentCompleted(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useMarkAppointmentNoShow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should mark appointment as no show successfully', async () => {
    const noShowAppointment = { ...mockAppointment, status: 'no_show' as const };
    vi.mocked(appointmentApi.markNoShow).mockResolvedValue(noShowAppointment);

    const { result } = renderHook(() => useMarkAppointmentNoShow(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.markNoShow).toHaveBeenCalledWith('apt-1');
  });

  it('should handle mark no show error', async () => {
    const error = new Error('Failed to mark no show');
    vi.mocked(appointmentApi.markNoShow).mockRejectedValue(error);

    const { result } = renderHook(() => useMarkAppointmentNoShow(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('apt-1');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});
