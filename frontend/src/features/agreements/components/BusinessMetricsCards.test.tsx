import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BusinessMetricsCards } from './BusinessMetricsCards';
import * as hooks from '../hooks/useAgreements';

vi.mock('../hooks/useAgreements', () => ({
  useAgreementMetrics: vi.fn(),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('BusinessMetricsCards', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state', () => {
    vi.mocked(hooks.useAgreementMetrics).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof hooks.useAgreementMetrics>);

    render(<BusinessMetricsCards />, { wrapper });
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useAgreementMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useAgreementMetrics>);

    render(<BusinessMetricsCards />, { wrapper });
    expect(screen.getByTestId('metrics-error')).toBeInTheDocument();
  });

  it('renders all KPI cards with correct values', () => {
    vi.mocked(hooks.useAgreementMetrics).mockReturnValue({
      data: {
        active_count: 42,
        mrr: 12500,
        arpa: 297.62,
        renewal_rate: 85.3,
        churn_rate: 4.2,
        past_due_amount: 1200,
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useAgreementMetrics>);

    render(<BusinessMetricsCards />, { wrapper });

    expect(screen.getByTestId('business-metrics-cards')).toBeInTheDocument();
    expect(screen.getByTestId('metric-active-agreements')).toHaveTextContent('42');
    expect(screen.getByTestId('metric-mrr')).toHaveTextContent('$12,500');
    expect(screen.getByTestId('metric-renewal-rate')).toHaveTextContent('85.3%');
    expect(screen.getByTestId('metric-churn-rate')).toHaveTextContent('4.2%');
    expect(screen.getByTestId('metric-past-due-amount')).toHaveTextContent('$1,200');
  });

  it('renders nothing when data is null', () => {
    vi.mocked(hooks.useAgreementMetrics).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useAgreementMetrics>);

    const { container } = render(<BusinessMetricsCards />, { wrapper });
    expect(container.innerHTML).toBe('');
  });
});
