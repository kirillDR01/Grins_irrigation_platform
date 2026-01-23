import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useCreateJob,
  useUpdateJob,
  useUpdateJobStatus,
  useDeleteJob,
  useApproveJob,
  useCancelJob,
  useCompleteJob,
  useCloseJob,
} from './useJobMutations';
import { jobApi } from '../api/jobApi';

vi.mock('../api/jobApi', () => ({
  jobApi: {
    create: vi.fn(),
    update: vi.fn(),
    updateStatus: vi.fn(),
    delete: vi.fn(),
    approve: vi.fn(),
    cancel: vi.fn(),
    complete: vi.fn(),
    close: vi.fn(),
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
  requested_at: '2024-01-01T00:00:00Z',
  approved_at: null,
  scheduled_at: null,
  started_at: null,
  completed_at: null,
  closed_at: null,
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
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useCreateJob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create job successfully', async () => {
    vi.mocked(jobApi.create).mockResolvedValue(mockJob);
    const { result } = renderHook(() => useCreateJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ customer_id: 'cust-1', job_type: 'spring_startup' });
    expect(jobApi.create).toHaveBeenCalled();
  });

  it('should handle create error', async () => {
    vi.mocked(jobApi.create).mockRejectedValue(new Error('Failed to create'));
    const { result } = renderHook(() => useCreateJob(), { wrapper: createWrapper() });
    await expect(result.current.mutateAsync({ customer_id: 'cust-1', job_type: 'spring_startup' })).rejects.toThrow('Failed to create');
  });
});

describe('useUpdateJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should update job successfully', async () => {
    vi.mocked(jobApi.update).mockResolvedValue({ ...mockJob, description: 'Updated' });
    const { result } = renderHook(() => useUpdateJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1', data: { description: 'Updated' } });
    expect(jobApi.update).toHaveBeenCalledWith('1', { description: 'Updated' });
  });
});

describe('useUpdateJobStatus', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should update job status successfully', async () => {
    vi.mocked(jobApi.updateStatus).mockResolvedValue({ ...mockJob, status: 'approved' as const });
    const { result } = renderHook(() => useUpdateJobStatus(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1', data: { status: 'approved' } });
    expect(jobApi.updateStatus).toHaveBeenCalledWith('1', { status: 'approved' });
  });
});

describe('useDeleteJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should delete job successfully', async () => {
    vi.mocked(jobApi.delete).mockResolvedValue(undefined);
    const { result } = renderHook(() => useDeleteJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync('1');
    expect(jobApi.delete).toHaveBeenCalledWith('1');
  });
});

describe('useApproveJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should approve job successfully', async () => {
    vi.mocked(jobApi.approve).mockResolvedValue({ ...mockJob, status: 'approved' as const });
    const { result } = renderHook(() => useApproveJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync('1');
    expect(jobApi.approve).toHaveBeenCalledWith('1');
  });
});


describe('useCancelJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should cancel job successfully', async () => {
    vi.mocked(jobApi.cancel).mockResolvedValue({ ...mockJob, status: 'cancelled' as const });
    const { result } = renderHook(() => useCancelJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1' });
    expect(jobApi.cancel).toHaveBeenCalledWith('1', undefined);
  });

  it('should cancel job with notes', async () => {
    vi.mocked(jobApi.cancel).mockResolvedValue({ ...mockJob, status: 'cancelled' as const });
    const { result } = renderHook(() => useCancelJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1', notes: 'Customer requested' });
    expect(jobApi.cancel).toHaveBeenCalledWith('1', 'Customer requested');
  });
});

describe('useCompleteJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should complete job successfully', async () => {
    vi.mocked(jobApi.complete).mockResolvedValue({ ...mockJob, status: 'completed' as const });
    const { result } = renderHook(() => useCompleteJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1' });
    expect(jobApi.complete).toHaveBeenCalledWith('1', undefined);
  });

  it('should complete job with notes', async () => {
    vi.mocked(jobApi.complete).mockResolvedValue({ ...mockJob, status: 'completed' as const });
    const { result } = renderHook(() => useCompleteJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1', notes: 'Work done' });
    expect(jobApi.complete).toHaveBeenCalledWith('1', 'Work done');
  });
});

describe('useCloseJob', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should close job successfully', async () => {
    vi.mocked(jobApi.close).mockResolvedValue({ ...mockJob, status: 'closed' as const });
    const { result } = renderHook(() => useCloseJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1' });
    expect(jobApi.close).toHaveBeenCalledWith('1', undefined);
  });

  it('should close job with notes', async () => {
    vi.mocked(jobApi.close).mockResolvedValue({ ...mockJob, status: 'closed' as const });
    const { result } = renderHook(() => useCloseJob(), { wrapper: createWrapper() });
    await result.current.mutateAsync({ id: '1', notes: 'Invoice paid' });
    expect(jobApi.close).toHaveBeenCalledWith('1', 'Invoice paid');
  });
});
