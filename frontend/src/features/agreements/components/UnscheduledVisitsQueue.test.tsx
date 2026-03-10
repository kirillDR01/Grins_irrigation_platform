import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
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

  it('renders grouped jobs by type', () => {
    vi.mocked(useJobsReadyToSchedule).mockReturnValue({
      data: {
        items: [
          { id: 'j1', job_type: 'Spring Startup', status: 'approved' },
          { id: 'j2', job_type: 'Spring Startup', status: 'approved' },
          { id: 'j3', job_type: 'Fall Winterization', status: 'approved' },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    expect(screen.getByTestId('unscheduled-visits-queue')).toBeInTheDocument();
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    expect(screen.getByText('Fall Winterization')).toBeInTheDocument();
    // Schedule links
    expect(screen.getByTestId('schedule-link-Spring Startup')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-link-Fall Winterization')).toBeInTheDocument();
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
      data: {
        items: [
          { id: 'j1', job_type: 'Spring Startup', status: 'approved' },
        ],
      },
      isLoading: false,
      error: null,
    } as unknown as ReturnType<typeof useJobsReadyToSchedule>);

    render(<UnscheduledVisitsQueue />, { wrapper });
    // The header count badge and the group count both show 1
    const badges = screen.getAllByText('1');
    expect(badges.length).toBeGreaterThanOrEqual(1);
  });
});
