import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CampaignsList } from './CampaignsList';
import type { Campaign, WorkerHealth, CampaignStats } from '../types/campaign';

// --- Mocks ---

const mockCampaigns: Campaign[] = [
  {
    id: 'c1',
    name: 'Spring Promo',
    campaign_type: 'sms',
    status: 'sending',
    body: 'Hello!',
    target_audience: {},
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-01T10:00:00Z',
    scheduled_at: null,
    sent_at: null,
    created_by_staff_id: 's1',
  },
  {
    id: 'c2',
    name: 'Follow Up',
    campaign_type: 'sms',
    status: 'sent',
    body: 'Thanks!',
    target_audience: {},
    created_at: '2026-03-28T08:00:00Z',
    updated_at: '2026-03-28T08:00:00Z',
    scheduled_at: null,
    sent_at: '2026-03-28T09:00:00Z',
    created_by_staff_id: 's1',
  },
];

const mockWorkerHealthy: WorkerHealth = {
  status: 'healthy',
  last_tick_at: new Date().toISOString(),
  last_tick_duration_ms: 120,
  last_tick_recipients_processed: 2,
  pending_count: 5,
  sending_count: 1,
  orphans_recovered_last_hour: 0,
  rate_limit: { hourly_used: 43, hourly_allowed: 150, daily_used: 200, daily_allowed: 1000 },
};

const mockWorkerStale: WorkerHealth = {
  ...mockWorkerHealthy,
  status: 'stale',
};

const mockStats: CampaignStats = { total: 50, sent: 30, failed: 5, pending: 10, sending: 3, cancelled: 2 };

let mockUseCampaignsReturn: unknown;
let mockUseWorkerHealthReturn: unknown;
let mockUseCampaignStatsReturn: unknown;

vi.mock('../hooks', () => ({
  useCampaigns: () => mockUseCampaignsReturn,
  useWorkerHealth: () => mockUseWorkerHealthReturn,
  useCampaignStats: () => mockUseCampaignStatsReturn,
}));

function createWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('CampaignsList', () => {
  beforeEach(() => {
    mockUseCampaignsReturn = {
      data: { items: mockCampaigns, total: 2, page: 1, page_size: 20, total_pages: 1 },
      isLoading: false,
      error: null,
    };
    mockUseWorkerHealthReturn = { data: mockWorkerHealthy };
    mockUseCampaignStatsReturn = { data: mockStats };
  });

  it('renders campaign rows', () => {
    render(<CampaignsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('campaigns-table')).toBeInTheDocument();
    expect(screen.getAllByTestId('campaign-row')).toHaveLength(2);
  });

  it('shows loading state', () => {
    mockUseCampaignsReturn = { data: undefined, isLoading: true, error: null };
    render(<CampaignsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    mockUseCampaignsReturn = {
      data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
      isLoading: false,
      error: null,
    };
    render(<CampaignsList />, { wrapper: createWrapper() });
    expect(screen.getByText(/no campaigns/i)).toBeInTheDocument();
  });

  describe('worker health indicator', () => {
    it('shows green dot when worker is healthy', () => {
      render(<CampaignsList />, { wrapper: createWrapper() });
      const dot = screen.getByTestId('worker-health-dot');
      expect(dot.className).toContain('bg-emerald-500');
    });

    it('shows red dot when worker is stale', () => {
      mockUseWorkerHealthReturn = { data: mockWorkerStale };
      render(<CampaignsList />, { wrapper: createWrapper() });
      const dot = screen.getByTestId('worker-health-dot');
      expect(dot.className).toContain('bg-red-500');
    });

    it('shows rate limit status', () => {
      render(<CampaignsList />, { wrapper: createWrapper() });
      expect(screen.getByTestId('rate-limit-status')).toHaveTextContent('43/150');
    });

    it('shows unknown state when no health data', () => {
      mockUseWorkerHealthReturn = { data: undefined };
      render(<CampaignsList />, { wrapper: createWrapper() });
      expect(screen.getByText(/Worker: unknown/)).toBeInTheDocument();
    });
  });

  it('displays status badges with correct labels (Requirement 27)', () => {
    render(<CampaignsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('status-sending')).toHaveTextContent('Sending');
    expect(screen.getByTestId('status-sent')).toHaveTextContent('Sent');
  });
});
