import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MrrChart } from './MrrChart';
import * as hooks from '../hooks/useAgreements';

vi.mock('../hooks/useAgreements', () => ({
  useMrrHistory: vi.fn(),
}));

// Recharts uses ResizeObserver internally; already mocked in setup.ts
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

describe('MrrChart', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state', () => {
    vi.mocked(hooks.useMrrHistory).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as unknown as ReturnType<typeof hooks.useMrrHistory>);

    render(<MrrChart />, { wrapper });
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders error state', () => {
    vi.mocked(hooks.useMrrHistory).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useMrrHistory>);

    render(<MrrChart />, { wrapper });
    expect(screen.getByTestId('mrr-chart-error')).toBeInTheDocument();
  });

  it('renders chart with data', () => {
    vi.mocked(hooks.useMrrHistory).mockReturnValue({
      data: {
        data_points: [
          { month: '2026-01', mrr: 10000 },
          { month: '2026-02', mrr: 11000 },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useMrrHistory>);

    render(<MrrChart />, { wrapper });
    expect(screen.getByTestId('mrr-chart')).toBeInTheDocument();
    expect(screen.getByText('MRR Over Time')).toBeInTheDocument();
  });

  it('renders nothing when no data points', () => {
    vi.mocked(hooks.useMrrHistory).mockReturnValue({
      data: { data_points: [] },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof hooks.useMrrHistory>);

    const { container } = render(<MrrChart />, { wrapper });
    expect(container.innerHTML).toBe('');
  });
});
