/**
 * Tests for AlertsPanel component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AlertsPanel } from './AlertsPanel';
import type { SchedulingAlert } from '../types';

const mockAlerts: SchedulingAlert[] = [
  {
    id: 'a1',
    alert_type: 'double_booking',
    severity: 'critical',
    title: 'Double-booking on Tuesday',
    description: 'Mike D. has overlapping jobs at 10 AM',
    affected_job_ids: ['j1', 'j2'],
    affected_staff_ids: ['s1'],
    criteria_triggered: [8],
    resolution_options: [
      { action: 'reassign', label: 'Reassign', description: 'Reassign one job', parameters: {} },
    ],
    status: 'active',
    resolved_by: null,
    resolved_action: null,
    resolved_at: null,
    schedule_date: '2025-03-04',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 's1',
    alert_type: 'route_swap',
    severity: 'suggestion',
    title: 'Swap saves 28 min',
    description: 'Swap jobs between Sarah K. and Carlos R.',
    affected_job_ids: ['j3', 'j4'],
    affected_staff_ids: ['s2', 's3'],
    criteria_triggered: [1, 2],
    resolution_options: [
      { action: 'accept', label: 'Accept', description: 'Apply swap', parameters: {} },
    ],
    status: 'active',
    resolved_by: null,
    resolved_action: null,
    resolved_at: null,
    schedule_date: '2025-03-04',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

// Mock the hooks
vi.mock('../hooks/useAlerts', () => ({
  useAlerts: vi.fn(() => ({
    data: mockAlerts,
    isLoading: false,
    error: null,
  })),
  useResolveAlert: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
  useDismissAlert: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
  })),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('AlertsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByTestId('alerts-panel')).toBeInTheDocument();
  });

  it('displays alert count badge', () => {
    render(<AlertsPanel />, { wrapper: createWrapper() });
    const badge = screen.getByTestId('alerts-count-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('2 alerts');
  });

  it('renders alert cards for critical alerts', () => {
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByTestId('alert-card-a1')).toBeInTheDocument();
  });

  it('renders suggestion cards for suggestions', () => {
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByTestId('suggestion-card-s1')).toBeInTheDocument();
  });

  it('renders header text', () => {
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByText('Alerts & Suggestions')).toBeInTheDocument();
  });

  it('shows loading state', async () => {
    const { useAlerts } = await import('../hooks/useAlerts');
    (useAlerts as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading alerts…')).toBeInTheDocument();
  });

  it('shows empty state when no alerts', async () => {
    const { useAlerts } = await import('../hooks/useAlerts');
    (useAlerts as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    render(<AlertsPanel />, { wrapper: createWrapper() });
    expect(screen.getByText('No active alerts or suggestions.')).toBeInTheDocument();
  });
});
