/**
 * Regression tests for StatusActionButton.
 *
 * Cluster C removes the SignWell-gated convert flow. On SEND_CONTRACT the
 * action button now opens CreateJobModal (which owns the create + closed_won
 * two-call shape) instead of mutating directly. These tests pin that
 * routing in so a future refactor can't reintroduce a direct mutation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { StatusActionButton } from './StatusActionButton';
import type { SalesEntry } from '../types/pipeline';

const advanceMutate = vi.fn();

vi.mock('../hooks/useSalesPipeline', () => ({
  useAdvanceSalesEntry: () => ({
    mutate: advanceMutate,
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

vi.mock('@/features/jobs/components/CreateJobModal', () => ({
  CreateJobModal: ({ open }: { open: boolean }) =>
    open ? <div data-testid="create-job-modal" /> : null,
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
    nudges_paused_until: null,
    dismissed_at: null,
    created_at: '2026-04-16T00:00:00Z',
    updated_at: '2026-04-16T00:00:00Z',
    customer_name: 'Jane Doe',
    customer_phone: '+19527373312',
    customer_email: null,
    property_address: '123 Elm St',
    ...overrides,
  };
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('StatusActionButton — SEND_CONTRACT routing (Cluster C)', () => {
  beforeEach(() => {
    advanceMutate.mockReset();
  });

  it('clicking the action on send_contract opens CreateJobModal and does NOT call /advance', async () => {
    const user = userEvent.setup();
    render(<StatusActionButton entry={makeEntry({ status: 'send_contract' })} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId('advance-btn-entry-001')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('advance-btn-entry-001'));

    expect(await screen.findByTestId('create-job-modal')).toBeInTheDocument();
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
    expect(advanceMutate.mock.calls[0][0]).toBe('entry-001');
  });
});
