import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useJobs,
  useJob,
  useJobsByStatus,
  useJobsByCustomer,
  useJobsReadyToSchedule,
  useJobsRequiresEstimate,
  useJobSearch,
  jobKeys,
} from './useJobs';
import { jobApi } from '../api/jobApi';

// Mock the jobApi
vi.mock('../api/jobApi', () => ({
  jobApi: {
    list: vi.fn(),
    get: vi.fn(),
    getByStatus: vi.fn(),
    getByCustomer: vi.fn(),
    getReadyToSchedule: vi.fn(),
    getRequiresEstimate: vi.fn(),
    search: vi.fn(),
  },
}));

const mockJob = {
  id: '1',
  customer_id: 'cust-1',
  property_id: 'prop-1',
  service_offering_id: null,
  job_type: 'spring_startup',
  category: 'ready_to_schedule' as const,
  status: 'requested' as const,
  description: 'Spring startup service',
  estimated_duration_minutes: 60,
  priority_level: 0,
  weather_sensitive: false,
  staffing_required: 1,
  equipment_required: null,
  materials_required: null,
  quoted_amount: null,
  final_amount: null,
  source: null,
  source_details: null,
  payment_collected_on_site: false,
  requested_at: '2024-01-01T00:00:00Z',
  approved_at: null,
  scheduled_at: null,
  started_at: null,
  completed_at: null,
  closed_at: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockJob],
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

describe('jobKeys', () => {
  it('should generate correct all key', () => {
    expect(jobKeys.all).toEqual(['jobs']);
  });

  it('should generate correct lists key', () => {
    expect(jobKeys.lists()).toEqual(['jobs', 'list']);
  });

  it('should generate correct list key with params', () => {
    const params = { page: 1, status: 'requested' as const };
    expect(jobKeys.list(params)).toEqual(['jobs', 'list', params]);
  });

  it('should generate correct details key', () => {
    expect(jobKeys.details()).toEqual(['jobs', 'detail']);
  });

  it('should generate correct detail key', () => {
    expect(jobKeys.detail('123')).toEqual(['jobs', 'detail', '123']);
  });

  it('should generate correct byStatus key', () => {
    expect(jobKeys.byStatus('requested')).toEqual(['jobs', 'status', 'requested']);
  });

  it('should generate correct byCustomer key', () => {
    expect(jobKeys.byCustomer('cust-1')).toEqual(['jobs', 'customer', 'cust-1']);
  });

  it('should generate correct readyToSchedule key', () => {
    expect(jobKeys.readyToSchedule()).toEqual(['jobs', 'ready-to-schedule']);
  });

  it('should generate correct requiresEstimate key', () => {
    expect(jobKeys.requiresEstimate()).toEqual(['jobs', 'requires-estimate']);
  });

  it('should generate correct search key', () => {
    expect(jobKeys.search('spring')).toEqual(['jobs', 'search', 'spring']);
  });
});

describe('useJobs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch jobs successfully', async () => {
    vi.mocked(jobApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(jobApi.list).toHaveBeenCalledWith(undefined);
  });

  it('should fetch jobs with params', async () => {
    const params = { page: 2, status: 'approved' as const };
    vi.mocked(jobApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobs(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.list).toHaveBeenCalledWith(params);
  });

  it('should handle error', async () => {
    const error = new Error('Failed to fetch');
    vi.mocked(jobApi.list).mockRejectedValue(error);

    const { result } = renderHook(() => useJobs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useJob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch single job successfully', async () => {
    vi.mocked(jobApi.get).mockResolvedValue(mockJob);

    const { result } = renderHook(() => useJob('1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockJob);
    expect(jobApi.get).toHaveBeenCalledWith('1');
  });

  it('should not fetch when id is empty', () => {
    const { result } = renderHook(() => useJob(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(jobApi.get).not.toHaveBeenCalled();
  });
});

describe('useJobsByStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch jobs by status', async () => {
    vi.mocked(jobApi.getByStatus).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobsByStatus('requested'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.getByStatus).toHaveBeenCalledWith('requested', undefined);
  });

  it('should fetch jobs by status with additional params', async () => {
    const params = { page: 2 };
    vi.mocked(jobApi.getByStatus).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobsByStatus('approved', params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.getByStatus).toHaveBeenCalledWith('approved', params);
  });
});

describe('useJobsByCustomer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch jobs by customer', async () => {
    vi.mocked(jobApi.getByCustomer).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobsByCustomer('cust-1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.getByCustomer).toHaveBeenCalledWith('cust-1', undefined);
  });

  it('should not fetch when customerId is empty', () => {
    const { result } = renderHook(() => useJobsByCustomer(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(jobApi.getByCustomer).not.toHaveBeenCalled();
  });
});

describe('useJobsReadyToSchedule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch jobs ready to schedule', async () => {
    vi.mocked(jobApi.getReadyToSchedule).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobsReadyToSchedule(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.getReadyToSchedule).toHaveBeenCalled();
  });
});

describe('useJobsRequiresEstimate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch jobs requiring estimate', async () => {
    vi.mocked(jobApi.getRequiresEstimate).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobsRequiresEstimate(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.getRequiresEstimate).toHaveBeenCalled();
  });
});

describe('useJobSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should search jobs when query is at least 2 characters', async () => {
    vi.mocked(jobApi.search).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useJobSearch('sp'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(jobApi.search).toHaveBeenCalledWith('sp');
  });

  it('should not search when query is less than 2 characters', () => {
    const { result } = renderHook(() => useJobSearch('s'), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(jobApi.search).not.toHaveBeenCalled();
  });
});
