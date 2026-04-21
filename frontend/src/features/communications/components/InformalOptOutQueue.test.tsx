/**
 * Tests for InformalOptOutQueue (Gap 06).
 *
 * Covers:
 *   - renders alert rows from API data with a count badge
 *   - Confirm opens a confirm dialog that previews the flagged message
 *     before firing the mutation (destructive-action safety pattern)
 *   - Dismiss fires the dismiss mutation directly and refetches the queue
 *   - empty state renders when no rows
 *   - error state renders when the list query fails
 *
 * Mocks `alertsApi` so no real network I/O happens.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { InformalOptOutQueue } from './InformalOptOutQueue';
import type { AdminAlert } from '../api/alertsApi';

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
  Toaster: () => null,
}));

vi.mock('../api/alertsApi', () => ({
  alertsApi: {
    list: vi.fn(),
    confirmOptOut: vi.fn(),
    dismiss: vi.fn(),
  },
}));

import { alertsApi } from '../api/alertsApi';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

function makeAlert(overrides: Partial<AdminAlert> = {}): AdminAlert {
  return {
    id: 'alert-1',
    type: 'informal_opt_out',
    severity: 'warning',
    entity_type: 'customer',
    entity_id: 'cust-1',
    message: 'please stop texting me',
    created_at: '2026-04-20T09:00:00Z',
    acknowledged_at: null,
    ...overrides,
  };
}

describe('InformalOptOutQueue (Gap 06)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders alert rows and a count badge from API data', async () => {
    (alertsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        makeAlert(),
        makeAlert({
          id: 'alert-2',
          message: 'remove me from this list',
          entity_type: 'phone',
        }),
      ],
      total: 2,
    });

    render(<InformalOptOutQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('informal-opt-out-row-alert-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('informal-opt-out-row-alert-2')).toBeInTheDocument();
    expect(screen.getByTestId('informal-opt-out-queue-count')).toHaveTextContent(
      '2 open',
    );
    expect(screen.getByText('please stop texting me')).toBeInTheDocument();
    expect(screen.getByText('remove me from this list')).toBeInTheDocument();
    expect(alertsApi.list).toHaveBeenCalledWith({ type: 'informal_opt_out' });
  });

  it('Confirm previews the flagged message in a dialog before firing the mutation', async () => {
    (alertsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [makeAlert()],
      total: 1,
    });
    (alertsApi.confirmOptOut as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeAlert({ acknowledged_at: '2026-04-21T10:00:00Z' }),
    );

    const user = userEvent.setup();
    render(<InformalOptOutQueue />, { wrapper: createWrapper() });

    const confirmTrigger = await screen.findByTestId('confirm-opt-out-trigger-alert-1');
    await user.click(confirmTrigger);

    // Dialog opens with the flagged message visible; no mutation yet.
    const dialog = await screen.findByTestId('confirm-opt-out-dialog');
    expect(dialog).toHaveTextContent('please stop texting me');
    expect(alertsApi.confirmOptOut).not.toHaveBeenCalled();

    // Admin confirms — mutation fires now.
    await user.click(screen.getByTestId('confirm-opt-out-btn'));

    await waitFor(() => {
      expect(alertsApi.confirmOptOut).toHaveBeenCalledWith('alert-1');
    });
  });

  it('Dismiss fires the mutation directly and refetches the queue', async () => {
    (alertsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [makeAlert()],
      total: 1,
    });
    (alertsApi.dismiss as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeAlert({ acknowledged_at: '2026-04-21T10:00:00Z' }),
    );

    const user = userEvent.setup();
    render(<InformalOptOutQueue />, { wrapper: createWrapper() });

    const dismissBtn = await screen.findByTestId('dismiss-opt-out-btn-alert-1');
    await user.click(dismissBtn);

    await waitFor(() => {
      expect(alertsApi.dismiss).toHaveBeenCalledWith('alert-1');
    });

    // The queue list query should be re-fetched after the mutation.
    await waitFor(() => {
      expect(alertsApi.list).toHaveBeenCalledTimes(2);
    });
  });

  it('renders the empty state when no alerts come back', async () => {
    (alertsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [],
      total: 0,
    });

    render(<InformalOptOutQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('informal-opt-out-queue-empty')).toBeInTheDocument();
    });
    expect(screen.getByTestId('informal-opt-out-queue-count')).toHaveTextContent(
      '0 open',
    );
  });

  it('renders an error state when the list query fails', async () => {
    (alertsApi.list as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('boom'),
    );

    render(<InformalOptOutQueue />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(
        screen.getByTestId('informal-opt-out-queue-error'),
      ).toBeInTheDocument();
    });
  });
});
