import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { UnscheduledVisitsQueue } from './UnscheduledVisitsQueue';

// Mock the jobs feature hook
vi.mock('@/features/jobs', () => ({
  useJobsReadyToSchedule: vi.fn(),
}));

import { useJobsReadyToSchedule } from '@/features/jobs';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

const mockJobs = [
  {
    id: 'j1',
    job_type: 'spring_startup',
    status: 'approved',
    target_start_date: '2026-03-15',
    target_end_date: '2026-04-30',
    estimated_duration_minutes: 90,
    priority_level: 0,
  },
  {
    id: 'j2',
    job_type: 'spring_startup',
    status: 'approved',
    target_start_date: '2026-03-15',
    target_end_date: '2026-04-30',
    estimated_duration_minutes: 60,
    priority_level: 1,
  },
  {
    id: 'j3',
    job_type: 'fall_winterization',
    status: 'approved',
    target_start_date: null,
    target_end_date: null,
    estimated_duration_minutes: null,
    priority_level: 0,
  },
];

describe('UnscheduledVisitsQueue', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders empty state', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: [] },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    expect(screen.getByText(/all visits are scheduled/i)).toBeInTheDocument();
  });

  it('renders grouped jobs by type with formatted names', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: mockJobs },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    expect(screen.getByTestId('unscheduled-visits-queue')).toBeInTheDocument();
    // formatJobType converts snake_case to Title Case
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Fall Winterization')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-link-spring_startup')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-link-fall_winterization')).toBeInTheDocument();
  });

  it('expands group to show individual jobs', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: mockJobs },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });

    // Individual jobs should not be visible yet
    expect(screen.queryByTestId('unscheduled-job-j1')).not.toBeInTheDocument();

    // Click the Spring Startup group to expand
    fireEvent.click(screen.getByTestId('unscheduled-toggle-spring_startup'));

    // Now individual jobs should appear
    expect(screen.getByTestId('unscheduled-job-j1')).toBeInTheDocument();
    expect(screen.getByTestId('unscheduled-job-j2')).toBeInTheDocument();
    // Fall winterization jobs should not be expanded
    expect(screen.queryByTestId('unscheduled-job-j3')).not.toBeInTheDocument();
  });

  it('individual jobs link to job detail page', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: mockJobs },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    fireEvent.click(screen.getByTestId('unscheduled-toggle-spring_startup'));

    const jobLink = screen.getByTestId('unscheduled-job-j1');
    expect(jobLink).toHaveAttribute('href', '/jobs/j1');
  });

  it('shows priority badge for high-priority jobs', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: mockJobs },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    fireEvent.click(screen.getByTestId('unscheduled-toggle-spring_startup'));

    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('fail'),
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    expect(screen.getByText(/failed to load unscheduled visits/i)).toBeInTheDocument();
  });

  it('shows count badge', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: { items: [mockJobs[0]] },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    const badges = screen.getAllByText('1');
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });
});
