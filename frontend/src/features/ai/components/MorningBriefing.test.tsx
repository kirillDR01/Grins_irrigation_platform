/**
 * Tests for MorningBriefing component.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MorningBriefing } from './MorningBriefing';
import { BrowserRouter } from 'react-router-dom';
import * as dashboardHooks from '@/features/dashboard/hooks';

// Mock the dashboard hooks
vi.mock('@/features/dashboard/hooks', () => ({
  useDashboardMetrics: vi.fn(),
  useJobsByStatus: vi.fn(),
  useTodaySchedule: vi.fn(),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('MorningBriefing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock data
    vi.mocked(dashboardHooks.useDashboardMetrics).mockReturnValue({
      data: {
        total_customers: 100,
        active_customers: 80,
        jobs_by_status: {},
        today_appointments: 10,
        available_staff: 3,
        total_staff: 4,
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useDashboardMetrics>);

    vi.mocked(dashboardHooks.useJobsByStatus).mockReturnValue({
      data: {
        requested: 5,
        approved: 3,
        scheduled: 8,
        in_progress: 2,
        completed: 50,
        closed: 40,
        cancelled: 1,
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useJobsByStatus>);

    vi.mocked(dashboardHooks.useTodaySchedule).mockReturnValue({
      data: {
        schedule_date: '2025-01-27',
        total_appointments: 10,
        completed_appointments: 3,
        in_progress_appointments: 2,
        upcoming_appointments: 5,
        cancelled_appointments: 0,
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useTodaySchedule>);
  });

  it('renders morning briefing card', () => {
    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('morning-briefing')).toBeInTheDocument();
  });

  it('displays personalized greeting', () => {
    render(<MorningBriefing />, { wrapper });
    const greeting = screen.getByTestId('greeting');
    expect(greeting).toBeInTheDocument();
    expect(greeting.textContent).toContain('Viktor');
  });

  it('displays overnight requests count', () => {
    render(<MorningBriefing />, { wrapper });
    const overnightSection = screen.getByTestId('overnight-requests');
    expect(overnightSection).toBeInTheDocument();
    expect(overnightSection.textContent).toContain('5');
  });

  it('displays today schedule summary', () => {
    render(<MorningBriefing />, { wrapper });
    const scheduleSection = screen.getByTestId('today-schedule');
    expect(scheduleSection).toBeInTheDocument();
    expect(scheduleSection.textContent).toContain('10');
    expect(scheduleSection.textContent).toContain('3 completed');
    expect(scheduleSection.textContent).toContain('2 in progress');
    expect(scheduleSection.textContent).toContain('5 upcoming');
  });

  it('displays pending communications count', () => {
    render(<MorningBriefing />, { wrapper });
    const commsSection = screen.getByTestId('pending-communications');
    expect(commsSection).toBeInTheDocument();
  });

  it('displays quick actions', () => {
    render(<MorningBriefing />, { wrapper });
    const quickActions = screen.getByTestId('quick-actions');
    expect(quickActions).toBeInTheDocument();
  });

  it('shows review requests button when overnight requests exist', () => {
    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('review-requests-btn')).toBeInTheDocument();
  });

  it('shows view schedule button', () => {
    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('morning-briefing-view-schedule-btn')).toBeInTheDocument();
  });

  it('handles zero overnight requests', () => {
    vi.mocked(dashboardHooks.useJobsByStatus).mockReturnValue({
      data: {
        requested: 0,
        approved: 3,
        scheduled: 8,
        in_progress: 2,
        completed: 50,
        closed: 40,
        cancelled: 1,
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useJobsByStatus>);

    render(<MorningBriefing />, { wrapper });
    const overnightSection = screen.getByTestId('overnight-requests');
    expect(overnightSection.textContent).toContain('0');
    expect(screen.queryByTestId('review-requests-btn')).not.toBeInTheDocument();
  });

  it('handles missing data gracefully', () => {
    vi.mocked(dashboardHooks.useJobsByStatus).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useJobsByStatus>);

    vi.mocked(dashboardHooks.useTodaySchedule).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useTodaySchedule>);

    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('morning-briefing')).toBeInTheDocument();
    expect(screen.getByTestId('overnight-requests').textContent).toContain('0');
  });
});
