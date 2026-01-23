/**
 * Tests for DashboardPage component.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from './DashboardPage';

// Mock the hooks
vi.mock('../hooks', () => ({
  useDashboardMetrics: vi.fn(),
  useTodaySchedule: vi.fn(),
  useJobsByStatus: vi.fn(),
}));

// Mock the jobs and schedule hooks used by RecentActivity
vi.mock('@/features/jobs/hooks', () => ({
  useJobs: vi.fn(() => ({
    data: { items: [], total: 0 },
    isLoading: false,
  })),
}));

vi.mock('@/features/schedule/hooks', () => ({
  useAppointments: vi.fn(() => ({
    data: { items: [], total: 0 },
    isLoading: false,
  })),
}));

import { useDashboardMetrics, useTodaySchedule, useJobsByStatus } from '../hooks';

const mockUseDashboardMetrics = useDashboardMetrics as ReturnType<typeof vi.fn>;
const mockUseTodaySchedule = useTodaySchedule as ReturnType<typeof vi.fn>;
const mockUseJobsByStatus = useJobsByStatus as ReturnType<typeof vi.fn>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state when data is loading', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: undefined,
      isLoading: true,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: undefined,
      isLoading: true,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('renders dashboard with metrics when data is loaded', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: {
        total_appointments: 12,
        completed_appointments: 4,
        in_progress_appointments: 2,
        upcoming_appointments: 6,
      },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: {
        requested: 5,
        approved: 3,
        scheduled: 8,
        in_progress: 2,
        completed: 45,
      },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
    expect(screen.getByTestId('metrics-grid')).toBeInTheDocument();
    expect(screen.getByTestId('customers-metric')).toBeInTheDocument();
    expect(screen.getByTestId('appointments-metric')).toBeInTheDocument();
    expect(screen.getByTestId('jobs-metric')).toBeInTheDocument();
    expect(screen.getByTestId('staff-metric')).toBeInTheDocument();
  });

  it('displays correct customer metrics', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: {
        total_appointments: 12,
        completed_appointments: 4,
      },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: { requested: 5, approved: 3, in_progress: 2 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByText('150')).toBeInTheDocument();
    expect(screen.getByText('120 active')).toBeInTheDocument();
  });

  it('displays today schedule card', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: {
        total_appointments: 12,
        completed_appointments: 4,
        in_progress_appointments: 2,
        upcoming_appointments: 6,
      },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: { requested: 5, approved: 3, in_progress: 2 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    const todayScheduleCard = screen.getByTestId('today-schedule-card');
    expect(todayScheduleCard).toBeInTheDocument();
    expect(screen.getByText("Today's Schedule")).toBeInTheDocument();
    expect(screen.getByText('Upcoming')).toBeInTheDocument();
    // Use getAllByText since "In Progress" appears in multiple places
    expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
    // Check within the today schedule card specifically
    expect(todayScheduleCard).toHaveTextContent('Upcoming');
    expect(todayScheduleCard).toHaveTextContent('In Progress');
    expect(todayScheduleCard).toHaveTextContent('Completed');
  });

  it('displays jobs by status card', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: {
        total_appointments: 12,
        completed_appointments: 4,
      },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: {
        requested: 5,
        approved: 3,
        scheduled: 8,
        in_progress: 2,
        completed: 45,
      },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('jobs-status-card')).toBeInTheDocument();
    expect(screen.getByText('Jobs by Status')).toBeInTheDocument();
    expect(screen.getByText('Requested')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toBeInTheDocument();
    expect(screen.getByText('Scheduled')).toBeInTheDocument();
  });

  it('displays quick actions card', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: { total_appointments: 12, completed_appointments: 4 },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: { requested: 5, approved: 3, in_progress: 2 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('quick-actions-card')).toBeInTheDocument();
    expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    expect(screen.getByTestId('add-customer-action')).toBeInTheDocument();
    expect(screen.getByTestId('add-job-action')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-action')).toBeInTheDocument();
  });

  it('displays recent activity card', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: { total_appointments: 12, completed_appointments: 4 },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: { requested: 5, approved: 3, in_progress: 2 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('recent-activity-card')).toBeInTheDocument();
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
  });

  it('has navigation buttons in header', () => {
    mockUseDashboardMetrics.mockReturnValue({
      data: {
        total_customers: 150,
        active_customers: 120,
        available_staff: 5,
        total_staff: 8,
      },
      isLoading: false,
    });
    mockUseTodaySchedule.mockReturnValue({
      data: { total_appointments: 12, completed_appointments: 4 },
      isLoading: false,
    });
    mockUseJobsByStatus.mockReturnValue({
      data: { requested: 5, approved: 3, in_progress: 2 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('view-schedule-btn')).toBeInTheDocument();
    expect(screen.getByTestId('new-job-btn')).toBeInTheDocument();
  });
});
