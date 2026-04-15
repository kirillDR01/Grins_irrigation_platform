/**
 * Tests for DashboardPage component.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from './DashboardPage';

// Mock scrollIntoView for AIQueryChat component
Element.prototype.scrollIntoView = vi.fn();

// Mock the auth hook
vi.mock('@/features/auth', () => ({
  useAuth: () => ({ user: { name: 'Admin User' } }),
}));

// Mock the hooks
vi.mock('../hooks', () => ({
  useDashboardMetrics: vi.fn(),
  useDashboardSummary: vi.fn(),
  useTodaySchedule: vi.fn(),
  useJobsByStatus: vi.fn(),
  useLeadMetricsBySource: vi.fn(),
  useUnaddressedCount: vi.fn(),
  usePendingInvoiceMetrics: vi.fn(),
  useJobStatusMetrics: vi.fn(),
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

import { useDashboardMetrics, useTodaySchedule, useJobsByStatus, useDashboardSummary, useLeadMetricsBySource, useUnaddressedCount, usePendingInvoiceMetrics, useJobStatusMetrics } from '../hooks';

const mockUseDashboardMetrics = useDashboardMetrics as ReturnType<typeof vi.fn>;
const mockUseTodaySchedule = useTodaySchedule as ReturnType<typeof vi.fn>;
const mockUseJobsByStatus = useJobsByStatus as ReturnType<typeof vi.fn>;
const mockUseDashboardSummary = useDashboardSummary as ReturnType<typeof vi.fn>;
const mockUseLeadMetricsBySource = useLeadMetricsBySource as ReturnType<typeof vi.fn>;
const mockUseUnaddressedCount = useUnaddressedCount as ReturnType<typeof vi.fn>;
const mockUsePendingInvoiceMetrics = usePendingInvoiceMetrics as ReturnType<typeof vi.fn>;
const mockUseJobStatusMetrics = useJobStatusMetrics as ReturnType<typeof vi.fn>;

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
    // Default mock for subscription widgets (loaded, no data issues)
    mockUseDashboardSummary.mockReturnValue({
      data: {
        active_agreement_count: 10,
        mrr: 2500,
        renewal_pipeline_count: 3,
        failed_payment_count: 1,
        failed_payment_amount: 150,
        new_leads_count: 5,
        follow_up_queue_count: 2,
        leads_awaiting_contact_oldest_age_hours: 4.5,
      },
      isLoading: false,
      error: null,
    });
    // Default mock for lead metrics by source
    mockUseLeadMetricsBySource.mockReturnValue({
      data: {
        items: [
          { lead_source: 'website', count: 10 },
          { lead_source: 'phone_call', count: 5 },
        ],
        total: 15,
        date_from: '2026-02-08',
        date_to: '2026-03-10',
      },
      isLoading: false,
      error: null,
    });
    // Default mock for unaddressed count
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 3 },
      isLoading: false,
    });
    // Default mock for pending invoice metrics
    mockUsePendingInvoiceMetrics.mockReturnValue({
      data: { count: 4, total_amount: '1200.00' },
      isLoading: false,
    });
    // Default mock for job status metrics (6 categories)
    mockUseJobStatusMetrics.mockReturnValue({
      data: {
        new_requests: 5,
        estimates: 3,
        pending_approval: 2,
        to_be_scheduled: 4,
        in_progress: 7,
        complete: 12,
      },
      isLoading: false,
    });
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
    expect(screen.getByTestId('messages-widget')).toBeInTheDocument();
    expect(screen.getByTestId('appointments-metric')).toBeInTheDocument();
    expect(screen.getByTestId('invoice-metrics-widget')).toBeInTheDocument();
    expect(screen.getByTestId('staff-metric')).toBeInTheDocument();
  });

  it('displays correct messages widget count', () => {
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
    mockUseUnaddressedCount.mockReturnValue({
      data: { count: 7 },
      isLoading: false,
    });

    render(<DashboardPage />, { wrapper: createWrapper() });

    const widget = screen.getByTestId('messages-widget');
    expect(widget).toBeInTheDocument();
    expect(widget).toHaveTextContent('7');
    expect(widget).toHaveTextContent('7 unaddressed');
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
    // Don't check for "Today's Schedule" text as it appears in MorningBriefing too
    expect(screen.getByText('Upcoming')).toBeInTheDocument();
    // Use getAllByText since "In Progress" appears in multiple places
    expect(screen.getAllByText('In Progress').length).toBeGreaterThan(0);
    // Check within the today schedule card specifically
    expect(todayScheduleCard).toHaveTextContent('Upcoming');
    expect(todayScheduleCard).toHaveTextContent('In Progress');
    expect(todayScheduleCard).toHaveTextContent('Completed');
  });

  it('displays job status grid with 5 categories', () => {
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

    expect(screen.getByTestId('job-status-grid')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-new-requests')).toBeInTheDocument();
    expect(screen.queryByTestId('job-status-estimates')).not.toBeInTheDocument();
    expect(screen.getByTestId('job-status-pending-approval')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-to-be-scheduled')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-in-progress')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-complete')).toBeInTheDocument();
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
    // Don't check for "Quick Actions" text as it appears in MorningBriefing too
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
    expect(screen.getByText('Recent Jobs')).toBeInTheDocument();
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
