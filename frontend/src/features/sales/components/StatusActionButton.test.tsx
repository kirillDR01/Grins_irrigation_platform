/**
 * Regression tests for StatusActionButton (bughunt M-10).
 *
 * The bughunt flagged that on SEND_CONTRACT the action button used to
 * fire ``/advance`` first and only fall back to ``/convert`` on a
 * signature error — two round-trips on the happy path. The current
 * implementation calls ``convertToJob.mutate()`` directly when
 * ``isSendContract`` and only triggers the force-convert dialog when
 * the backend reports a missing signature. These tests lock that
 * behavior in so a future refactor can't reintroduce the regression.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatusActionButton } from './StatusActionButton';
import type { SalesEntry } from '../types/pipeline';

const advanceMutate = vi.fn();
const convertMutate = vi.fn();

vi.mock('../hooks/useSalesPipeline', () => ({
  useAdvanceSalesEntry: () => ({
    mutate: advanceMutate,
    isPending: false,
  }),
  useConvertToJob: () => ({
    mutate: convertMutate,
    isPending: false,
  }),
  useForceConvertToJob: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useMarkSalesLost: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
  useCreateCalendarEvent: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  pipelineKeys: {
    lists: () => ['pipeline', 'list'] as const,
  },
}));

function makeEntry(overrides: Partial<SalesEntry> = {}): SalesEntry {
  return {
    id: 'entry-001',
    customer_id: 'cust-001',
    property_id: null,
    lead_id: null,
    job_type: 'install',
    status: 'send_contract',
    last_contact_date: null,
    notes: null,
    override_flag: false,
    closed_reason: null,
    signwell_document_id: null,
    created_at: '2026-04-16T00:00:00Z',
    updated_at: '2026-04-16T00:00:00Z',
    customer_name: 'Jane Doe',
    customer_phone: '+19527373312',
    property_address: '123 Elm St',
    ...overrides,
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('StatusActionButton — SEND_CONTRACT routing (bughunt M-10)', () => {
  beforeEach(() => {
    advanceMutate.mockReset();
    convertMutate.mockReset();
  });

  it('clicking the action on send_contract calls /convert directly, not /advance', async () => {
    const user = userEvent.setup();
    render(<StatusActionButton entry={makeEntry({ status: 'send_contract' })} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId('advance-btn-entry-001')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('advance-btn-entry-001'));

    expect(convertMutate).toHaveBeenCalledTimes(1);
    expect(convertMutate.mock.calls[0][0]).toBe('entry-001');
    expect(advanceMutate).not.toHaveBeenCalled();
  });

  it('clicking the action on a non-send_contract status still calls /advance', async () => {
    const user = userEvent.setup();
    render(<StatusActionButton entry={makeEntry({ status: 'pending_approval' })} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId('advance-btn-entry-001')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('advance-btn-entry-001'));

    expect(advanceMutate).toHaveBeenCalledTimes(1);
    expect(convertMutate).not.toHaveBeenCalled();
  });
});
