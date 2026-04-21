/**
 * Tests for OptOutBadge (Gap 06).
 *
 * Covers:
 *   - renders nothing while consent-status is loading / absent
 *   - renders nothing for a fully opted-in customer
 *   - red `hard-stop` variant for STOP-keyword opt-out
 *   - amber `admin-confirmed` variant for informal opt-out confirmed by admin
 *   - outline `pending` variant when only an alert (no consent row) exists
 *   - tooltip copy reflects method + date
 *
 * Mocks `customerApi.getConsentStatus` so no network I/O occurs.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { OptOutBadge } from './OptOutBadge';

vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    getConsentStatus: vi.fn(),
  },
}));

import { customerApi } from '@/features/customers/api/customerApi';

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

describe('OptOutBadge (Gap 06)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when customerId is missing', () => {
    const { container } = render(<OptOutBadge customerId={undefined} />, {
      wrapper: createWrapper(),
    });
    expect(container).toBeEmptyDOMElement();
    expect(customerApi.getConsentStatus).not.toHaveBeenCalled();
  });

  it('renders nothing for a fully opted-in customer', async () => {
    (customerApi.getConsentStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      customer_id: 'cust-1',
      phone: '+19527373312',
      is_opted_out: false,
      opt_out_method: null,
      opt_out_timestamp: null,
      pending_informal_opt_out_alert_id: null,
    });

    const { container } = render(<OptOutBadge customerId="cust-1" />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(customerApi.getConsentStatus).toHaveBeenCalledWith('cust-1');
    });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a red "hard-stop" badge for STOP-keyword opt-outs', async () => {
    (customerApi.getConsentStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      customer_id: 'cust-1',
      phone: '+19527373312',
      is_opted_out: true,
      opt_out_method: 'text_stop',
      opt_out_timestamp: '2026-04-15T12:00:00Z',
      pending_informal_opt_out_alert_id: null,
    });

    render(<OptOutBadge customerId="cust-1" />, { wrapper: createWrapper() });

    const badge = await screen.findByTestId('opt-out-badge');
    expect(badge).toHaveAttribute('data-variant', 'hard-stop');
    expect(badge).toHaveTextContent('Opted out');
    expect(badge.getAttribute('title')).toContain('STOP keyword');
  });

  it('renders an amber "admin-confirmed" badge for admin-confirmed informal opt-outs', async () => {
    (customerApi.getConsentStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      customer_id: 'cust-1',
      phone: '+19527373312',
      is_opted_out: true,
      opt_out_method: 'admin_confirmed_informal',
      opt_out_timestamp: '2026-04-16T09:30:00Z',
      pending_informal_opt_out_alert_id: null,
    });

    render(<OptOutBadge customerId="cust-1" />, { wrapper: createWrapper() });

    const badge = await screen.findByTestId('opt-out-badge');
    expect(badge).toHaveAttribute('data-variant', 'admin-confirmed');
    expect(badge).toHaveTextContent('Opted out');
    expect(badge.getAttribute('title')).toContain('Admin-confirmed informal opt-out');
  });

  it('renders an outlined "pending" badge when an informal alert is awaiting review', async () => {
    (customerApi.getConsentStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      customer_id: 'cust-1',
      phone: '+19527373312',
      is_opted_out: false,
      opt_out_method: null,
      opt_out_timestamp: null,
      pending_informal_opt_out_alert_id: 'alert-123',
    });

    render(<OptOutBadge customerId="cust-1" />, { wrapper: createWrapper() });

    const badge = await screen.findByTestId('opt-out-badge');
    expect(badge).toHaveAttribute('data-variant', 'pending');
    expect(badge).toHaveTextContent('Opt-out pending');
    expect(badge.getAttribute('title')).toContain('Awaiting admin review');
  });

  it('applies the compact size when the compact prop is set', async () => {
    (customerApi.getConsentStatus as ReturnType<typeof vi.fn>).mockResolvedValue({
      customer_id: 'cust-1',
      phone: '+19527373312',
      is_opted_out: true,
      opt_out_method: 'text_stop',
      opt_out_timestamp: '2026-04-15T12:00:00Z',
      pending_informal_opt_out_alert_id: null,
    });

    render(<OptOutBadge customerId="cust-1" compact />, { wrapper: createWrapper() });

    const badge = await screen.findByTestId('opt-out-badge');
    expect(badge.className).toContain('text-[10px]');
  });
});
