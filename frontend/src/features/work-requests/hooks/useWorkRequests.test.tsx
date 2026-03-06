import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import {
  useWorkRequests,
  useWorkRequest,
  useSyncStatus,
  useCreateLeadFromSubmission,
  useTriggerSync,
  workRequestKeys,
} from './useWorkRequests';
import { workRequestApi } from '../api/workRequestApi';

vi.mock('../api/workRequestApi', () => ({
  workRequestApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getSyncStatus: vi.fn(),
    createLead: vi.fn(),
    triggerSync: vi.fn(),
  },
}));

const mockWorkRequest = {
  id: 'wr-001',
  sheet_row_number: 2,
  timestamp: '2026-01-15T10:00:00Z',
  spring_startup: 'Yes',
  fall_blowout: null,
  summer_tuneup: null,
  repair_existing: null,
  new_system_install: null,
  addition_to_system: null,
  additional_services_info: null,
  date_work_needed_by: 'ASAP',
  name: 'Alice Johnson',
  phone: '6125551234',
  email: 'alice@example.com',
  city: 'Minneapolis',
  address: '123 Main St',
  additional_info: null,
  client_type: 'new',
  property_type: 'Residential',
  referral_source: 'Google',
  landscape_hardscape: null,
  processing_status: 'imported' as const,
  processing_error: null,
  lead_id: null,
  imported_at: '2026-01-15T12:00:00Z',
  created_at: '2026-01-15T12:00:00Z',
  updated_at: '2026-01-15T12:00:00Z',
};

const mockPaginatedResponse = {
  items: [mockWorkRequest],
  total: 1,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockSyncStatus = {
  last_sync: '2026-01-15T12:00:00Z',
  is_running: true,
  last_error: null,
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

describe('workRequestKeys', () => {
  it('should generate correct all key', () => {
    expect(workRequestKeys.all).toEqual(['work-requests']);
  });

  it('should generate correct lists key', () => {
    expect(workRequestKeys.lists()).toEqual(['work-requests', 'list']);
  });

  it('should generate correct list key with params', () => {
    const params = { page: 1, page_size: 20 };
    expect(workRequestKeys.list(params)).toEqual(['work-requests', 'list', params]);
  });

  it('should generate correct list key without params', () => {
    expect(workRequestKeys.list()).toEqual(['work-requests', 'list', undefined]);
  });

  it('should generate correct details key', () => {
    expect(workRequestKeys.details()).toEqual(['work-requests', 'detail']);
  });

  it('should generate correct detail key', () => {
    expect(workRequestKeys.detail('wr-001')).toEqual(['work-requests', 'detail', 'wr-001']);
  });

  it('should generate correct syncStatus key', () => {
    expect(workRequestKeys.syncStatus()).toEqual(['work-requests', 'sync-status']);
  });
});

describe('useWorkRequests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch work requests successfully', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useWorkRequests(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPaginatedResponse);
    expect(workRequestApi.list).toHaveBeenCalledWith(undefined);
  });

  it('should fetch with params', async () => {
    const params = { page: 2, processing_status: 'imported' as const };
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginatedResponse);

    const { result } = renderHook(() => useWorkRequests(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(workRequestApi.list).toHaveBeenCalledWith(params);
  });

  it('should handle error', async () => {
    const error = new Error('Failed to fetch');
    vi.mocked(workRequestApi.list).mockRejectedValue(error);

    const { result } = renderHook(() => useWorkRequests(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useWorkRequest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch single work request', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(mockWorkRequest);

    const { result } = renderHook(() => useWorkRequest('wr-001'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockWorkRequest);
    expect(workRequestApi.getById).toHaveBeenCalledWith('wr-001');
  });

  it('should not fetch when id is empty', () => {
    const { result } = renderHook(() => useWorkRequest(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(workRequestApi.getById).not.toHaveBeenCalled();
  });

  it('should handle error', async () => {
    const error = new Error('Not found');
    vi.mocked(workRequestApi.getById).mockRejectedValue(error);

    const { result } = renderHook(() => useWorkRequest('bad-id'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBe(error);
  });
});

describe('useSyncStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch sync status', async () => {
    vi.mocked(workRequestApi.getSyncStatus).mockResolvedValue(mockSyncStatus);

    const { result } = renderHook(() => useSyncStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockSyncStatus);
  });

  it('should handle error', async () => {
    const error = new Error('Server error');
    vi.mocked(workRequestApi.getSyncStatus).mockRejectedValue(error);

    const { result } = renderHook(() => useSyncStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useCreateLeadFromSubmission', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should create lead successfully', async () => {
    const updated = { ...mockWorkRequest, processing_status: 'lead_created' as const, lead_id: 'lead-1' };
    vi.mocked(workRequestApi.createLead).mockResolvedValue(updated);

    const { result } = renderHook(() => useCreateLeadFromSubmission(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('wr-001');
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(workRequestApi.createLead).toHaveBeenCalledWith('wr-001');
  });

  it('should handle mutation error', async () => {
    vi.mocked(workRequestApi.createLead).mockRejectedValue(new Error('Conflict'));

    const { result } = renderHook(() => useCreateLeadFromSubmission(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate('wr-001');
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useTriggerSync', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should trigger sync successfully', async () => {
    vi.mocked(workRequestApi.triggerSync).mockResolvedValue({ new_rows_imported: 3 });

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(workRequestApi.triggerSync).toHaveBeenCalled();
  });

  it('should handle sync error', async () => {
    vi.mocked(workRequestApi.triggerSync).mockRejectedValue(new Error('Sync failed'));

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});
