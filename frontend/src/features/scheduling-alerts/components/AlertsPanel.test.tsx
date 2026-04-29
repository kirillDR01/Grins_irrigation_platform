import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { SchedulingAlert } from '../types';

// Mock hooks before importing component
vi.mock('../hooks/useAlerts', () => ({
  useAlerts: vi.fn(),
  useResolveAlert: () => ({ mutate: vi.fn(), isPending: false }),
  useDismissAlert: () => ({ mutate: vi.fn(), isPending: false }),
}));

import { AlertsPanel } from './AlertsPanel';
import { useAlerts } from '../hooks/useAlerts';

const mockAlert: SchedulingAlert = {
  id: 'a1',
  alert_type: 'skill_mismatch',
  severity: 'critical',
  title: 'Skill mismatch on job',
  description: 'Carlos is not backflow-certified.',
  affected_job_ids: ['j1'],
  affected_staff_ids: ['s1'],
  criteria_triggered: [6],
  resolution_options: [{ action: 'reassign', label: 'Reassign', description: 'Reassign job' }],
  status: 'active',
  schedule_date: '2026-02-16',
  created_at: new Date().toISOString(),
};

const mockSuggestion: SchedulingAlert = {
  ...mockAlert,
  id: 's1',
  alert_type: 'route_swap',
  severity: 'suggestion',
  title: 'Route swap saves 28 min',
  description: 'Swap 2 jobs between Sarah and Carlos.',
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('AlertsPanel', () => {
  beforeEach(() => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAlerts>);
  });

  it('renders with data-testid="alerts-panel"', () => {
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByTestId('alerts-panel')).toBeInTheDocument();
  });

  it('shows empty state when no alerts', () => {
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByText('No active alerts or suggestions.')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [],
      isLoading: true,
      error: null,
    } as ReturnType<typeof useAlerts>);
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByText('Loading alerts…')).toBeInTheDocument();
  });

  it('shows error state', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [],
      isLoading: false,
      error: new Error('fail'),
    } as ReturnType<typeof useAlerts>);
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByText('Failed to load alerts.')).toBeInTheDocument();
  });

  it('renders count badge when alerts present', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [mockAlert, mockSuggestion],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAlerts>);
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByTestId('alerts-count-badge')).toHaveTextContent('2 alerts');
  });

  it('renders AlertCard for non-suggestion alerts', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [mockAlert],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAlerts>);
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByTestId('alert-card-a1')).toBeInTheDocument();
  });

  it('renders SuggestionCard for suggestion alerts', () => {
    vi.mocked(useAlerts).mockReturnValue({
      data: [mockSuggestion],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useAlerts>);
    render(<AlertsPanel />, { wrapper });
    expect(screen.getByTestId('suggestion-card-s1')).toBeInTheDocument();
  });
});
