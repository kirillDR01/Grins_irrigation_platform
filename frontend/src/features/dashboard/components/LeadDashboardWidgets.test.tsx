import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { LeadDashboardWidgets } from './LeadDashboardWidgets';
import * as hooks from '../hooks/useDashboard';

vi.mock('../hooks/useDashboard', () => ({
  useDashboardSummary: vi.fn(),
  useLeadMetricsBySource: vi.fn(),
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
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const mockSummary = {
  active_agreement_count: 10,
  mrr: 5000,
  renewal_pipeline_count: 1,
  failed_payment_count: 0,
  failed_payment_amount: 0,
  new_leads_count: 7,
  follow_up_queue_count: 3,
  leads_awaiting_contact_oldest_age_hours: 18,
};

const mockSourceMetrics = {
  items: [
    { lead_source: 'website', count: 5 },
    { lead_source: 'phone_call', count: 3 },
  ],
  total: 8,
  date_from: '2026-02-08',
  date_to: '2026-03-10',
};

describe('LeadDashboardWidgets', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders loading state when both hooks loading', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: undefined, isLoading: true, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: undefined, isLoading: true, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });
    expect(document.querySelector('[class*="animate"]')).toBeTruthy();
  });

  it('renders error state when both hooks error', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: undefined, isLoading: false, error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: undefined, isLoading: false, error: new Error('fail'),
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });
    expect(screen.getByTestId('lead-widgets-error')).toBeInTheDocument();
  });

  it('renders leads awaiting contact widget with count and urgency', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: mockSummary, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: mockSourceMetrics, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });

    const widget = screen.getByTestId('widget-leads-awaiting-contact');
    expect(widget).toBeInTheDocument();
    expect(widget).toHaveTextContent('7');
    expect(widget).toHaveTextContent('Oldest: 18h ago');
  });

  it('renders follow-up queue widget with count', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: mockSummary, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: mockSourceMetrics, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });

    const widget = screen.getByTestId('widget-follow-up-queue');
    expect(widget).toBeInTheDocument();
    expect(widget).toHaveTextContent('3');
  });

  it('renders leads by source chart widget', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: mockSummary, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: mockSourceMetrics, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });
    expect(screen.getByTestId('widget-leads-by-source')).toBeInTheDocument();
    expect(screen.getByText('Leads by Source')).toBeInTheDocument();
  });

  it('renders "No lead data" when source metrics empty', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: mockSummary, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: { items: [], total: 0, date_from: '', date_to: '' },
      isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });
    expect(screen.getByText('No lead data')).toBeInTheDocument();
  });

  it('renders "None" for oldest age when null', () => {
    vi.mocked(hooks.useDashboardSummary).mockReturnValue({
      data: { ...mockSummary, leads_awaiting_contact_oldest_age_hours: null },
      isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useDashboardSummary>);
    vi.mocked(hooks.useLeadMetricsBySource).mockReturnValue({
      data: mockSourceMetrics, isLoading: false, error: null,
    } as unknown as ReturnType<typeof hooks.useLeadMetricsBySource>);

    render(<LeadDashboardWidgets />, { wrapper });
    expect(screen.getByText('Oldest: None')).toBeInTheDocument();
  });
});
