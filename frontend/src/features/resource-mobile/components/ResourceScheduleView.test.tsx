/**
 * Tests for ResourceScheduleView component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ResourceScheduleView } from './ResourceScheduleView';
import type { ResourceDaySchedule } from '../types';

const mockSchedule: ResourceDaySchedule = {
  date: '2025-03-04',
  resource_id: 'r1',
  resource_name: 'Mike D.',
  total_drive_minutes: 45,
  total_job_minutes: 360,
  utilization_pct: 84,
  jobs: [
    {
      id: 'j1',
      route_order: 1,
      job_type: 'Spring Opening',
      address: '123 Main St',
      customer_name: 'Smith',
      customer_notes: 'Dog in yard',
      estimated_duration: 60,
      eta: '8:15 AM',
      time_window_start: '8:00',
      time_window_end: '10:00',
      status: 'scheduled',
      has_prejob_flag: true,
      is_vip: true,
    },
    {
      id: 'j2',
      route_order: 2,
      job_type: 'Maintenance',
      address: '456 Oak Ave',
      customer_name: 'Jones',
      customer_notes: null,
      estimated_duration: 45,
      eta: '10:30 AM',
      time_window_start: null,
      time_window_end: null,
      status: 'scheduled',
      has_prejob_flag: false,
      is_vip: false,
    },
  ],
};

vi.mock('../hooks/useResourceSchedule', () => ({
  useResourceSchedule: vi.fn(() => ({
    data: mockSchedule,
    isLoading: false,
    error: null,
  })),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  MapPin: () => <span>📍</span>,
  Clock: () => <span>🕐</span>,
  Car: () => <span>🚗</span>,
  Star: () => <span>⭐</span>,
  AlertTriangle: () => <span>⚠️</span>,
  ClipboardList: () => <span>📋</span>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('ResourceScheduleView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with data-testid', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByTestId('resource-schedule-view')).toBeInTheDocument();
  });

  it('renders job cards with data-testid', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByTestId('job-card-j1')).toBeInTheDocument();
    expect(screen.getByTestId('job-card-j2')).toBeInTheDocument();
  });

  it('displays route order numbers', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    const card1 = screen.getByTestId('job-card-j1');
    expect(card1).toHaveTextContent('1');
    const card2 = screen.getByTestId('job-card-j2');
    expect(card2).toHaveTextContent('2');
  });

  it('displays job type names', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('Spring Opening')).toBeInTheDocument();
    expect(screen.getByText('Maintenance')).toBeInTheDocument();
  });

  it('displays addresses', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('456 Oak Ave')).toBeInTheDocument();
  });

  it('displays ETAs', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText(/ETA 8:15 AM/)).toBeInTheDocument();
  });

  it('displays estimated durations', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('60 min')).toBeInTheDocument();
    expect(screen.getByText('45 min')).toBeInTheDocument();
  });

  it('displays total drive time', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('45 min drive')).toBeInTheDocument();
  });

  it('displays utilization percentage', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('84% utilized')).toBeInTheDocument();
  });

  it('displays job count', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('2 jobs')).toBeInTheDocument();
  });

  it('shows pre-job flag indicator', () => {
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText(/Special prep required/)).toBeInTheDocument();
  });

  it('shows loading state', async () => {
    const { useResourceSchedule } = await import('../hooks/useResourceSchedule');
    (useResourceSchedule as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading schedule…')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    const { useResourceSchedule } = await import('../hooks/useResourceSchedule');
    (useResourceSchedule as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    });
    render(<ResourceScheduleView />, { wrapper: createWrapper() });
    expect(screen.getByText('Failed to load schedule')).toBeInTheDocument();
  });
});
