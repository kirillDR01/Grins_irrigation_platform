/**
 * Tests for ConsentHistoryPanel (Gap 06).
 *
 * Covers:
 *   - loading state
 *   - error state
 *   - empty state when the customer has no consent records
 *   - renders rows newest-first with method + actor + language-shown
 *   - applies opted-in vs opted-out styling via the Badge label
 *
 * Mocks `customerApi.getConsentHistory` so no network I/O occurs.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { ConsentHistoryPanel } from './ConsentHistoryPanel';
import type { ConsentHistoryEntry } from '../types';

vi.mock('../api/customerApi', () => ({
  customerApi: {
    getConsentHistory: vi.fn(),
  },
}));

import { customerApi } from '../api/customerApi';

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

function makeEntry(overrides: Partial<ConsentHistoryEntry> = {}): ConsentHistoryEntry {
  return {
    id: 'entry-1',
    consent_given: true,
    consent_type: 'transactional',
    consent_method: 'quote_acceptance',
    consent_timestamp: '2026-04-10T15:00:00Z',
    opt_out_method: null,
    opt_out_timestamp: null,
    created_by_staff_id: null,
    consent_language_shown: '',
    ...overrides,
  };
}

describe('ConsentHistoryPanel (Gap 06)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the panel container and card title', async () => {
    (
      customerApi.getConsentHistory as ReturnType<typeof vi.fn>
    ).mockResolvedValue({ items: [], total: 0 });

    render(<ConsentHistoryPanel customerId="cust-1" />, { wrapper: createWrapper() });

    expect(screen.getByTestId('consent-history-panel')).toBeInTheDocument();
    expect(screen.getByText('SMS Consent History')).toBeInTheDocument();
  });

  it('shows a loading message while fetching', () => {
    (customerApi.getConsentHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      new Promise(() => {}), // never-resolving
    );

    render(<ConsentHistoryPanel customerId="cust-1" />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading consent history/i)).toBeInTheDocument();
  });

  it('shows an error message when the query fails', async () => {
    (customerApi.getConsentHistory as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('boom'),
    );

    render(<ConsentHistoryPanel customerId="cust-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/failed to load consent history/i)).toBeInTheDocument();
    });
  });

  it('renders the empty state when there are no consent events', async () => {
    (
      customerApi.getConsentHistory as ReturnType<typeof vi.fn>
    ).mockResolvedValue({ items: [], total: 0 });

    render(<ConsentHistoryPanel customerId="cust-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('consent-history-empty')).toBeInTheDocument();
    });
    expect(
      screen.getByText(/no consent events recorded/i),
    ).toBeInTheDocument();
  });

  it('renders consent-history rows with method, actor, and language copy', async () => {
    (
      customerApi.getConsentHistory as ReturnType<typeof vi.fn>
    ).mockResolvedValue({
      items: [
        makeEntry({
          id: 'entry-new',
          consent_given: false,
          consent_method: 'admin_confirmed_informal',
          consent_timestamp: '2026-04-16T09:30:00Z',
          created_by_staff_id: 'a1b2c3d4-0000-0000-0000-000000000000',
          consent_language_shown: 'Customer said stop texting me.',
        }),
        makeEntry({
          id: 'entry-old',
          consent_given: true,
          consent_method: 'quote_acceptance',
          consent_timestamp: '2026-04-10T15:00:00Z',
          consent_language_shown: 'By accepting, you agree to SMS notifications.',
        }),
      ],
      total: 2,
    });

    render(<ConsentHistoryPanel customerId="cust-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('consent-history-list')).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId('consent-history-row');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Opted out');
    expect(rows[0]).toHaveTextContent('admin_confirmed_informal');
    expect(rows[0]).toHaveTextContent('(actor a1b2c3d4…)');
    expect(rows[0]).toHaveTextContent('Customer said stop texting me.');
    expect(rows[1]).toHaveTextContent('Opted in');
    expect(rows[1]).toHaveTextContent('quote_acceptance');
  });

  it('passes customerId to the API call', async () => {
    (
      customerApi.getConsentHistory as ReturnType<typeof vi.fn>
    ).mockResolvedValue({ items: [], total: 0 });

    render(<ConsentHistoryPanel customerId="cust-42" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(customerApi.getConsentHistory).toHaveBeenCalledWith('cust-42', {
        limit: 50,
      });
    });
  });
});
