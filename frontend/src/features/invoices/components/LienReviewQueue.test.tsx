import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../hooks/useLienReview', () => ({
  useLienCandidates: vi.fn(),
  useSendLienNotice: vi.fn(),
}));

import { useLienCandidates, useSendLienNotice } from '../hooks/useLienReview';
import { LienReviewQueue } from './LienReviewQueue';
import type { LienCandidate } from '../types';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

function makeCandidate(overrides: Partial<LienCandidate> = {}): LienCandidate {
  return {
    customer_id: 'cust-1',
    customer_name: 'Alice Smith',
    customer_phone: '+19527373312',
    oldest_invoice_age_days: 90,
    total_past_due_amount: '800.00',
    invoice_ids: ['inv-1'],
    invoice_numbers: ['INV-2026-000001'],
    ...overrides,
  };
}

describe('LienReviewQueue (CR-5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders candidate cards from API data', () => {
    vi.mocked(useLienCandidates).mockReturnValue({
      data: [makeCandidate()],
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useSendLienNotice).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<LienReviewQueue />, { wrapper: createWrapper() });

    expect(screen.getByTestId('lien-queue')).toBeInTheDocument();
    expect(screen.getByTestId('lien-candidate-row-cust-1')).toBeInTheDocument();
    expect(screen.getByText('Alice Smith')).toBeInTheDocument();
    expect(screen.getByText('+19527373312')).toBeInTheDocument();
  });

  it('calls sendLienNotice on confirm click', async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue({ success: true });

    vi.mocked(useLienCandidates).mockReturnValue({
      data: [makeCandidate()],
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useSendLienNotice).mockReturnValue({
      mutateAsync,
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<LienReviewQueue />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('send-lien-btn-cust-1'));
    expect(screen.getByTestId('lien-confirm-dialog')).toBeInTheDocument();
    await user.click(screen.getByTestId('confirm-send-lien-btn'));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith('cust-1');
    });
  });

  it('hides row after dismiss', async () => {
    const user = userEvent.setup();
    vi.mocked(useLienCandidates).mockReturnValue({
      data: [
        makeCandidate(),
        makeCandidate({ customer_id: 'cust-2', customer_name: 'Bob Jones' }),
      ],
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useSendLienNotice).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<LienReviewQueue />, { wrapper: createWrapper() });
    expect(screen.getByTestId('lien-candidate-row-cust-1')).toBeInTheDocument();

    await user.click(screen.getByTestId('dismiss-lien-btn-cust-1'));

    expect(screen.queryByTestId('lien-candidate-row-cust-1')).not.toBeInTheDocument();
    expect(screen.getByTestId('lien-candidate-row-cust-2')).toBeInTheDocument();
  });

  it('renders empty state when no candidates', () => {
    vi.mocked(useLienCandidates).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useSendLienNotice).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<LienReviewQueue />, { wrapper: createWrapper() });
    expect(
      screen.getByText(/No customers in the lien review queue/),
    ).toBeInTheDocument();
  });

  it('disables Send button for candidates without a phone', () => {
    vi.mocked(useLienCandidates).mockReturnValue({
      data: [
        makeCandidate({
          customer_id: 'cust-nophone',
          customer_name: 'No Phone',
          customer_phone: null,
        }),
      ],
      isLoading: false,
      error: null,
      // @ts-expect-error — partial mock
    });
    vi.mocked(useSendLienNotice).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      // @ts-expect-error — partial mock
    });

    render(<LienReviewQueue />, { wrapper: createWrapper() });
    expect(screen.getByTestId('send-lien-btn-cust-nophone')).toBeDisabled();
  });
});
