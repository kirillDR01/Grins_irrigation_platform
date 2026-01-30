/**
 * Tests for MorningBriefing component.
 * Updated for redesigned amber alert styling.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MorningBriefing } from './MorningBriefing';
import { BrowserRouter } from 'react-router-dom';
import * as dashboardHooks from '@/features/dashboard/hooks';

// Mock the dashboard hooks
vi.mock('@/features/dashboard/hooks', () => ({
  useJobsByStatus: vi.fn(),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('MorningBriefing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock data with overnight requests
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
  });

  it('renders morning briefing when there are overnight requests', () => {
    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('morning-briefing')).toBeInTheDocument();
  });

  it('displays personalized greeting with request count', () => {
    render(<MorningBriefing />, { wrapper });
    const greeting = screen.getByTestId('greeting');
    expect(greeting).toBeInTheDocument();
    expect(greeting.textContent).toContain('Viktor');
    expect(greeting.textContent).toContain('5 overnight requests');
  });

  it('shows review requests button when overnight requests exist', () => {
    render(<MorningBriefing />, { wrapper });
    expect(screen.getByTestId('review-requests-btn')).toBeInTheDocument();
  });

  it('does not render when there are zero overnight requests', () => {
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
    expect(screen.queryByTestId('morning-briefing')).not.toBeInTheDocument();
  });

  it('does not render when data is undefined', () => {
    vi.mocked(dashboardHooks.useJobsByStatus).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    } as ReturnType<typeof dashboardHooks.useJobsByStatus>);

    render(<MorningBriefing />, { wrapper });
    expect(screen.queryByTestId('morning-briefing')).not.toBeInTheDocument();
  });

  it('handles singular request correctly', () => {
    vi.mocked(dashboardHooks.useJobsByStatus).mockReturnValue({
      data: {
        requested: 1,
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
    const greeting = screen.getByTestId('greeting');
    expect(greeting.textContent).toContain('1 overnight request');
    expect(greeting.textContent).not.toContain('requests');
  });

  it('has amber alert styling', () => {
    render(<MorningBriefing />, { wrapper });
    const briefing = screen.getByTestId('morning-briefing');
    expect(briefing).toHaveClass('border-l-4', 'border-amber-400');
  });

  it('review button links to jobs with requested status filter', () => {
    render(<MorningBriefing />, { wrapper });
    const reviewBtn = screen.getByTestId('review-requests-btn');
    expect(reviewBtn).toHaveAttribute('href', '/jobs?status=requested');
  });
});
