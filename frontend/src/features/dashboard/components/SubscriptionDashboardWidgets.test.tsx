import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { SubscriptionDashboardWidgets } from './SubscriptionDashboardWidgets';
import * as hooks from '../hooks/useDashboard';

vi.mock('../hooks/useDashboard', () => ({
  useDashboardSummary: vi.fn(),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SubscriptionDashboardWidgets', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);

    render(<SubscriptionDashboardWidgets />, { wrapper });
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);

    render(<SubscriptionDashboardWidgets />, { wrapper });
    expect(screen.getByTestId('subscription-widgets-error')).toBeInTheDocument();
  });

  it('renders nothing when data is null', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);

    const { container } = render(<SubscriptionDashboardWidgets />, { wrapper });
    expect(container.innerHTML).toBe('');
  });

  it('renders all four widgets with correct values', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: {
        active_agreement_count: 25,
        mrr: 8500,
        renewal_pipeline_count: 3,
        failed_payment_count: 2,
        failed_payment_amount: 750,
        new_leads_count: 0,
        follow_up_queue_count: 0,
        leads_awaiting_contact_oldest_age_hours: null,
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);

    render(<SubscriptionDashboardWidgets />, { wrapper });

    expect(screen.getByTestId('subscription-dashboard-widgets')).toBeInTheDocument();
    expect(screen.getByTestId('widget-active-agreements')).toHaveTextContent('25');
    expect(screen.getByTestId('widget-mrr')).toHaveTextContent('$8,500');
    expect(screen.getByTestId('widget-renewal-pipeline')).toHaveTextContent('3');
    expect(screen.getByTestId('widget-failed-payments')).toHaveTextContent('2');
    expect(screen.getByText('$750 at risk')).toBeInTheDocument();
  });
});
