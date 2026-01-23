/**
 * Tests for RecentActivity component.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecentActivity } from './RecentActivity';

// Mock the hooks
vi.mock('@/features/jobs/hooks', () => ({
  useJobs: vi.fn(),
}));

vi.mock('@/features/schedule/hooks', () => ({
  useAppointments: vi.fn(),
}));

import { useJobs } from '@/features/jobs/hooks';
import { useAppointments } from '@/features/schedule/hooks';

const mockUseJobs = useJobs as ReturnType<typeof vi.fn>;
const mockUseAppointments = useAppointments as ReturnType<typeof vi.fn>;

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

describe('RecentActivity', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state when data is loading', () => {
    mockUseJobs.mockReturnValue({
      data: undefined,
      isLoading: true,
    });
    mockUseAppointments.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    expect(screen.getByTestId('recent-activity-card')).toBeInTheDocument();
    // Loading skeleton should be visible
    const card = screen.getByTestId('recent-activity-card');
    expect(card.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('renders empty state when no activity', () => {
    mockUseJobs.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    expect(screen.getByText('No recent activity')).toBeInTheDocument();
  });

  it('renders job activity items', () => {
    mockUseJobs.mockReturnValue({
      data: {
        items: [
          {
            id: 'job-1',
            job_type: 'Spring Startup',
            description: 'Test job description',
            status: 'requested',
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    expect(screen.getByTestId('activity-list')).toBeInTheDocument();
    expect(screen.getByText('Job: Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Test job description')).toBeInTheDocument();
  });

  it('renders appointment activity items', () => {
    mockUseJobs.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: {
        items: [
          {
            id: 'apt-1',
            scheduled_date: '2025-01-22',
            status: 'confirmed',
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    expect(screen.getByTestId('activity-list')).toBeInTheDocument();
    expect(screen.getByText('Appointment')).toBeInTheDocument();
    expect(screen.getByText('Scheduled for 2025-01-22')).toBeInTheDocument();
  });

  it('displays status badges with correct colors', () => {
    mockUseJobs.mockReturnValue({
      data: {
        items: [
          {
            id: 'job-1',
            job_type: 'Repair',
            description: 'Test',
            status: 'completed',
            created_at: new Date().toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    const badge = screen.getByText('completed');
    expect(badge).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('combines and sorts items by timestamp', () => {
    const now = new Date();
    const earlier = new Date(now.getTime() - 60000); // 1 minute ago

    mockUseJobs.mockReturnValue({
      data: {
        items: [
          {
            id: 'job-1',
            job_type: 'Older Job',
            description: 'Test',
            status: 'requested',
            created_at: earlier.toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: {
        items: [
          {
            id: 'apt-1',
            scheduled_date: '2025-01-22',
            status: 'pending',
            created_at: now.toISOString(),
          },
        ],
        total: 1,
      },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    const items = screen.getAllByTestId(/activity-item/);
    // Newer item (appointment) should be first
    expect(items[0]).toHaveAttribute('data-testid', 'activity-item-appointment-apt-1');
    expect(items[1]).toHaveAttribute('data-testid', 'activity-item-job-job-1');
  });

  it('has View All link', () => {
    mockUseJobs.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });
    mockUseAppointments.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    });

    render(<RecentActivity />, { wrapper: createWrapper() });

    const viewAllLink = screen.getByRole('link', { name: /view all/i });
    expect(viewAllLink).toHaveAttribute('href', '/jobs');
  });
});
