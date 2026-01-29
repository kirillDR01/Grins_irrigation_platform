/**
 * Tests for RecentlyClearedSection component.
 *
 * Validates: Requirements 6.1-6.5
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import { RecentlyClearedSection } from './RecentlyClearedSection';
import { scheduleGenerationApi } from '../api/scheduleGenerationApi';

// Mock the API
vi.mock('../api/scheduleGenerationApi', () => ({
  scheduleGenerationApi: {
    getRecentClears: vi.fn(),
  },
}));

const mockRecentClears = [
  {
    id: 'audit-1',
    schedule_date: '2025-01-28',
    appointment_count: 5,
    cleared_at: new Date().toISOString(),
    cleared_by: 'staff-1',
    notes: null,
  },
  {
    id: 'audit-2',
    schedule_date: '2025-01-27',
    appointment_count: 3,
    cleared_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    cleared_by: 'staff-1',
    notes: 'Test clear',
  },
];

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('RecentlyClearedSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    expect(screen.getByTestId('recently-cleared-section')).toBeInTheDocument();
    expect(screen.getByText('Recently Cleared')).toBeInTheDocument();
  });

  it('renders clears from last 24 hours', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue(
      mockRecentClears
    );

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    const items = screen.getAllByTestId('recently-cleared-item');
    expect(items).toHaveLength(2);
  });

  it('displays date, count, and timestamp for each clear', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue(
      mockRecentClears
    );

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    // Check dates are displayed (don't check exact format due to timezone)
    const dates = screen.getAllByTestId('recently-cleared-date');
    expect(dates).toHaveLength(2);
    expect(dates[0]).toBeInTheDocument();

    const counts = screen.getAllByTestId('recently-cleared-count');
    expect(counts[0]).toHaveTextContent('5 appointments cleared');
    expect(counts[1]).toHaveTextContent('3 appointments cleared');

    // Timestamps should be present
    const times = screen.getAllByTestId('recently-cleared-time');
    expect(times).toHaveLength(2);
  });

  it('shows View Details action for each clear', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue(
      mockRecentClears
    );

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByTestId('view-clear-details-btn');
    expect(detailButtons).toHaveLength(2);
  });

  it('calls onViewDetails when View Details is clicked', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue(
      mockRecentClears
    );
    const onViewDetails = vi.fn();

    render(<RecentlyClearedSection onViewDetails={onViewDetails} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    const detailButtons = screen.getAllByTestId('view-clear-details-btn');
    await userEvent.click(detailButtons[0]);

    expect(onViewDetails).toHaveBeenCalledWith('audit-1');
  });

  it('shows empty state when no recent clears', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue([]);

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-empty')).toBeInTheDocument();
    });

    expect(
      screen.getByText('No schedules cleared in the last 24 hours')
    ).toBeInTheDocument();
  });

  it('handles singular appointment count correctly', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue([
      {
        id: 'audit-1',
        schedule_date: '2025-01-28',
        appointment_count: 1,
        cleared_at: new Date().toISOString(),
        cleared_by: 'staff-1',
        notes: null,
      },
    ]);

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    expect(screen.getByTestId('recently-cleared-count')).toHaveTextContent(
      '1 appointment cleared'
    );
  });

  it('has correct data-testid attributes', async () => {
    vi.mocked(scheduleGenerationApi.getRecentClears).mockResolvedValue(
      mockRecentClears
    );

    render(<RecentlyClearedSection />, { wrapper: createWrapper() });

    // Wait for data to load
    await waitFor(() => {
      expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    });

    expect(screen.getByTestId('recently-cleared-section')).toBeInTheDocument();
    expect(screen.getByTestId('recently-cleared-list')).toBeInTheDocument();
    expect(screen.getAllByTestId('recently-cleared-item')).toHaveLength(2);
    expect(screen.getAllByTestId('recently-cleared-date')).toHaveLength(2);
    expect(screen.getAllByTestId('recently-cleared-count')).toHaveLength(2);
    expect(screen.getAllByTestId('recently-cleared-time')).toHaveLength(2);
    expect(screen.getAllByTestId('view-clear-details-btn')).toHaveLength(2);
  });
});
