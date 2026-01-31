/**
 * Tests for Invoice query hooks.
 */

import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useInvoices,
  useInvoice,
  useOverdueInvoices,
  useLienDeadlines,
  useInvoicesByJob,
  invoiceKeys,
} from './useInvoices';
import { invoiceApi } from '../api/invoiceApi';
import type { ReactNode } from 'react';

// Mock the invoice API
vi.mock('../api/invoiceApi', () => ({
  invoiceApi: {
    list: vi.fn(),
    get: vi.fn(),
    getOverdue: vi.fn(),
    getLienDeadlines: vi.fn(),
  },
}));

const mockInvoice = {
  id: 'inv-123',
  invoice_number: 'INV-2025-0001',
  job_id: 'job-123',
  customer_id: 'cust-123',
  amount: 150.00,
  late_fee_amount: 0,
  total_amount: 150.00,
  invoice_date: '2025-01-20',
  due_date: '2025-02-20',
  status: 'draft' as const,
  payment_method: null,
  payment_reference: null,
  paid_at: null,
  paid_amount: null,
  reminder_count: 0,
  last_reminder_sent: null,
  lien_eligible: false,
  lien_warning_sent: null,
  lien_filed_date: null,
  line_items: null,
  notes: null,
  created_at: '2025-01-20T00:00:00Z',
  updated_at: '2025-01-20T00:00:00Z',
};

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
};

describe('invoiceKeys', () => {
  it('generates correct all key', () => {
    expect(invoiceKeys.all).toEqual(['invoices']);
  });

  it('generates correct lists key', () => {
    expect(invoiceKeys.lists()).toEqual(['invoices', 'list']);
  });

  it('generates correct list key with params', () => {
    expect(invoiceKeys.list({ status: 'draft' })).toEqual(['invoices', 'list', { status: 'draft' }]);
  });

  it('generates correct details key', () => {
    expect(invoiceKeys.details()).toEqual(['invoices', 'detail']);
  });

  it('generates correct detail key', () => {
    expect(invoiceKeys.detail('123')).toEqual(['invoices', 'detail', '123']);
  });

  it('generates correct byJob key', () => {
    expect(invoiceKeys.byJob('job-123')).toEqual(['invoices', 'by-job', 'job-123']);
  });

  it('generates correct overdue key', () => {
    expect(invoiceKeys.overdue()).toEqual(['invoices', 'overdue', undefined]);
  });

  it('generates correct lienDeadlines key', () => {
    expect(invoiceKeys.lienDeadlines()).toEqual(['invoices', 'lien-deadlines']);
  });
});

describe('useInvoices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches invoices list', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [mockInvoice],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const { result } = renderHook(() => useInvoices(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.list).toHaveBeenCalledWith(undefined);
    expect(result.current.data?.items).toHaveLength(1);
  });

  it('fetches invoices with params', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [mockInvoice],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const params = { status: 'draft' };
    const { result } = renderHook(() => useInvoices(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.list).toHaveBeenCalledWith(params);
  });
});

describe('useInvoice', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches single invoice', async () => {
    vi.mocked(invoiceApi.get).mockResolvedValue(mockInvoice);

    const { result } = renderHook(() => useInvoice('inv-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.get).toHaveBeenCalledWith('inv-123');
    expect(result.current.data?.id).toBe('inv-123');
  });

  it('does not fetch when id is empty', () => {
    const { result } = renderHook(() => useInvoice(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(invoiceApi.get).not.toHaveBeenCalled();
  });
});

describe('useOverdueInvoices', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches overdue invoices', async () => {
    const overdueInvoice = { ...mockInvoice, status: 'overdue' };
    vi.mocked(invoiceApi.getOverdue).mockResolvedValue({
      items: [overdueInvoice],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const { result } = renderHook(() => useOverdueInvoices(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.getOverdue).toHaveBeenCalled();
    expect(result.current.data?.items[0].status).toBe('overdue');
  });
});

describe('useLienDeadlines', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches lien deadlines', async () => {
    vi.mocked(invoiceApi.getLienDeadlines).mockResolvedValue({
      approaching_45_day: [mockInvoice],
      approaching_120_day: [],
    });

    const { result } = renderHook(() => useLienDeadlines(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.getLienDeadlines).toHaveBeenCalled();
    expect(result.current.data?.approaching_45_day).toHaveLength(1);
  });
});

describe('useInvoicesByJob', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches invoices by job ID', async () => {
    vi.mocked(invoiceApi.list).mockResolvedValue({
      items: [mockInvoice],
      total: 1,
      page: 1,
      page_size: 20,
    });

    const { result } = renderHook(() => useInvoicesByJob('job-123'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(invoiceApi.list).toHaveBeenCalledWith({ job_id: 'job-123' });
    expect(result.current.data).toHaveLength(1);
  });

  it('does not fetch when jobId is empty', () => {
    const { result } = renderHook(() => useInvoicesByJob(''), {
      wrapper: createWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(invoiceApi.list).not.toHaveBeenCalled();
  });
});
