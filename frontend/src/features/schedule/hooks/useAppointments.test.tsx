import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useAppointments,
  useAppointment,
  useDailySchedule,
  useStaffDailySchedule,
  useWeeklySchedule,
  useJobAppointments,
  useStaffAppointments,
  appointmentKeys,
} from './useAppointments';
import { appointmentApi } from '../api/appointmentApi';

// Mock the appointmentApi
vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getDailySchedule: vi.fn(),
    getStaffDailySchedule: vi.fn(),
    getWeeklySchedule: vi.fn(),
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
  job_type: null,
  customer_name: null,
  staff_name: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockAppointment],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockDailySchedule = {
  date: '2024-01-15',
  appointments: [mockAppointment],
  total_count: 1,
};

const mockStaffDailySchedule = {
  staff_id: 'staff-1',
  staff_name: 'John Doe',
  date: '2024-01-15',
  appointments: [mockAppointment],
  total_scheduled_minutes: 120,
};

const mockWeeklySchedule = {
  start_date: '2024-01-15',
  end_date: '2024-01-21',
  days: [mockDailySchedule],
  total_appointments: 1,
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

describe('appointmentKeys', () => {
  it('should generate correct query keys', () => {
    expect(appointmentKeys.all).toEqual(['appointments']);
    expect(appointmentKeys.lists()).toEqual(['appointments', 'list']);
    expect(appointmentKeys.list({ page: 1 })).toEqual(['appointments', 'list', { page: 1 }]);
    expect(appointmentKeys.details()).toEqual(['appointments', 'detail']);
    expect(appointmentKeys.detail('apt-1')).toEqual(['appointments', 'detail', 'apt-1']);
    expect(appointmentKeys.daily('2024-01-15')).toEqual(['appointments', 'daily', '2024-01-15']);
    expect(appointmentKeys.staffDaily('staff-1', '2024-01-15')).toEqual([
      'appointments',
      'staffDaily',
      'staff-1',
      '2024-01-15',
    ]);
    expect(appointmentKeys.weekly('2024-01-15', '2024-01-21')).toEqual([
      'appointments',
      'weekly',
      '2024-01-15',
      '2024-01-21',
    ]);
  });
});

describe('useAppointments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch appointments successfully', async () => {
    vi.mocked(appointmentApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useAppointments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(appointmentApi.list).toHaveBeenCalledWith(undefined);
  });

  it('should fetch appointments with params', async () => {
    vi.mocked(appointmentApi.list).mockResolvedValue(mockPaginatedResponse);

    const params = { page: 2, page_size: 10, status: 'pending' as const };
    const { result } = renderHook(() => useAppointments(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.list).toHaveBeenCalledWith(params);
  });

  it('should handle fetch error', async () => {
    const error = new Error('Failed to fetch');
    vi.mocked(appointmentApi.list).mockRejectedValue(error);

    const { result } = renderHook(() => useAppointments(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useAppointment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch single appointment successfully', async () => {
    vi.mocked(appointmentApi.getById).mockResolvedValue(mockAppointment);

    const { result } = renderHook(() => useAppointment('apt-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockAppointment);
    expect(appointmentApi.getById).toHaveBeenCalledWith('apt-1');
  });

  it('should not fetch when id is undefined', () => {
    const { result } = renderHook(() => useAppointment(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.getById).not.toHaveBeenCalled();
  });
});

describe('useDailySchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch daily schedule successfully', async () => {
    vi.mocked(appointmentApi.getDailySchedule).mockResolvedValue(mockDailySchedule);

    const { result } = renderHook(() => useDailySchedule('2024-01-15'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockDailySchedule);
    expect(appointmentApi.getDailySchedule).toHaveBeenCalledWith('2024-01-15');
  });

  it('should not fetch when date is undefined', () => {
    const { result } = renderHook(() => useDailySchedule(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.getDailySchedule).not.toHaveBeenCalled();
  });
});

describe('useStaffDailySchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch staff daily schedule successfully', async () => {
    vi.mocked(appointmentApi.getStaffDailySchedule).mockResolvedValue(mockStaffDailySchedule);

    const { result } = renderHook(() => useStaffDailySchedule('staff-1', '2024-01-15'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockStaffDailySchedule);
    expect(appointmentApi.getStaffDailySchedule).toHaveBeenCalledWith('staff-1', '2024-01-15');
  });

  it('should not fetch when staffId is undefined', () => {
    const { result } = renderHook(() => useStaffDailySchedule(undefined, '2024-01-15'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.getStaffDailySchedule).not.toHaveBeenCalled();
  });

  it('should not fetch when date is undefined', () => {
    const { result } = renderHook(() => useStaffDailySchedule('staff-1', undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.getStaffDailySchedule).not.toHaveBeenCalled();
  });
});

describe('useWeeklySchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch weekly schedule successfully', async () => {
    vi.mocked(appointmentApi.getWeeklySchedule).mockResolvedValue(mockWeeklySchedule);

    const { result } = renderHook(() => useWeeklySchedule('2024-01-15', '2024-01-21'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockWeeklySchedule);
    expect(appointmentApi.getWeeklySchedule).toHaveBeenCalledWith('2024-01-15', '2024-01-21');
  });

  it('should fetch weekly schedule without dates', async () => {
    vi.mocked(appointmentApi.getWeeklySchedule).mockResolvedValue(mockWeeklySchedule);

    const { result } = renderHook(() => useWeeklySchedule(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.getWeeklySchedule).toHaveBeenCalledWith(undefined, undefined);
  });
});

describe('useJobAppointments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch job appointments successfully', async () => {
    vi.mocked(appointmentApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobAppointments('job-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.list).toHaveBeenCalledWith({ job_id: 'job-1' });
  });

  it('should not fetch when jobId is undefined', () => {
    const { result } = renderHook(() => useJobAppointments(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.list).not.toHaveBeenCalled();
  });
});

describe('useStaffAppointments', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch staff appointments successfully', async () => {
    vi.mocked(appointmentApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useStaffAppointments('staff-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(appointmentApi.list).toHaveBeenCalledWith({ staff_id: 'staff-1' });
  });

  it('should not fetch when staffId is undefined', () => {
    const { result } = renderHook(() => useStaffAppointments(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(appointmentApi.list).not.toHaveBeenCalled();
  });
});
