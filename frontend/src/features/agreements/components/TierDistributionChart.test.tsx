import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TierDistributionChart } from './TierDistributionChart';
import * as hooks from '../hooks/useAgreements';

vi.mock('../hooks/useAgreements', () => ({
  useTierDistribution: vi.fn(),
}));

vi.mock('recharts', async () => {
  const actual = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('TierDistributionChart', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state', () => {
    vi.mocked(hooks.useTierDistribution).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof hooks.useTierDistribution>);

    render(<TierDistributionChart />, { wrapper });
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useTierDistribution).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useTierDistribution>);

    render(<TierDistributionChart />, { wrapper });
    expect(screen.getByTestId('tier-distribution-chart-error')).toBeInTheDocument();
  });

  it('renders chart with data', () => {
    vi.mocked(hooks.useTierDistribution).mockReturnValue({
      data: {
        items: [
          { tier_id: 't1', tier_name: 'Essential', package_type: 'residential', active_count: 10 },
          { tier_id: 't2', tier_name: 'Professional', package_type: 'residential', active_count: 20 },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useTierDistribution>);

    render(<TierDistributionChart />, { wrapper });
    expect(screen.getByTestId('tier-distribution-chart')).toBeInTheDocument();
    expect(screen.getByText('Agreements by Tier')).toBeInTheDocument();
  });

  it('renders nothing when no items', () => {
    vi.mocked(hooks.useTierDistribution).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useTierDistribution>);

    const { container } = render(<TierDistributionChart />, { wrapper });
    expect(container.innerHTML).toBe('');
  });
});
