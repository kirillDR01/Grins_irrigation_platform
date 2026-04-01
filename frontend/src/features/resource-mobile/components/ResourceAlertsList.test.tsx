/**
 * Tests for ResourceAlertsList component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResourceAlertsList } from './ResourceAlertsList';
import type { ResourceAlert } from '../types';

const mockAlerts: ResourceAlert[] = [
  {
    id: 'ra1',
    alert_type: 'job_added',
    title: 'New job added to route',
    description: 'Maintenance at 789 Elm St added at 2:00 PM',
    job_id: 'j20',
    created_at: new Date().toISOString(),
    is_read: false,
  },
  {
    id: 'ra2',
    alert_type: 'special_equipment',
    title: 'Special equipment needed',
    description: 'Backflow tester required for next job',
    job_id: 'j21',
    created_at: new Date().toISOString(),
    is_read: false,
  },
  {
    id: 'ra3',
    alert_type: 'customer_access',
    title: 'Gate code required',
    description: 'Gate code: 1234. Enter through north entrance.',
    job_id: 'j22',
    created_at: new Date().toISOString(),
    is_read: true,
  },
];

const mockMarkReadMutate = vi.fn();

vi.mock('../hooks/useResourceSchedule', () => ({
  useResourceAlerts: vi.fn(() => ({
    data: mockAlerts,
    isLoading: false,
    error: null,
  })),
  useMarkAlertRead: vi.fn(() => ({
    mutate: mockMarkReadMutate,
  })),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Plus: () => <span>+</span>,
  Minus: () => <span>-</span>,
  ArrowUpDown: () => <span>↕</span>,
  Wrench: () => <span>🔧</span>,
  Key: () => <span>🔑</span>,
  CheckCircle2: () => <span>✓</span>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ResourceAlertsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-alerts-list')).toBeInTheDocument();
  });

  it('renders alert items with data-testid', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-alert-ra1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-alert-ra2')).toBeInTheDocument();
    expect(screen.getByTestId('resource-alert-ra3')).toBeInTheDocument();
  });

  it('displays alert titles', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByText('New job added to route')).toBeInTheDocument();
    expect(screen.getByText('Special equipment needed')).toBeInTheDocument();
    expect(screen.getByText('Gate code required')).toBeInTheDocument();
  });

  it('displays alert descriptions', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByText(/Maintenance at 789 Elm St/)).toBeInTheDocument();
  });

  it('displays unread count badge', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByText('2 new')).toBeInTheDocument();
  });

  it('shows mark-as-read button for unread alerts', () => {
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    // Unread alerts (ra1, ra2) should have mark-as-read buttons
    const markReadButtons = screen.getAllByLabelText('Mark as read');
    expect(markReadButtons).toHaveLength(2);
  });

  it('calls markRead mutation when mark-as-read is clicked', async () => {
    const user = userEvent.setup();
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    const markReadButtons = screen.getAllByLabelText('Mark as read');
    await user.click(markReadButtons[0]);
    expect(mockMarkReadMutate).toHaveBeenCalledWith('ra1');
  });

  it('shows loading state', async () => {
    const { useResourceAlerts } = await import('../hooks/useResourceSchedule');
    (useResourceAlerts as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading alerts…')).toBeInTheDocument();
  });

  it('shows empty state when no alerts', async () => {
    const { useResourceAlerts } = await import('../hooks/useResourceSchedule');
    (useResourceAlerts as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    render(<ResourceAlertsList />, { wrapper: createWrapper() });
    expect(screen.getByText('No alerts right now')).toBeInTheDocument();
  });
});
