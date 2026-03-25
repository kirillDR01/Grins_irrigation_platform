/**
 * Tests for JobStatusGrid component.
 * Validates: Requirements 6.1
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { JobStatusGrid } from './JobStatusGrid';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../hooks', () => ({
  useJobStatusMetrics: vi.fn(),
}));

import { useJobStatusMetrics } from '../hooks';
const mockUseJobStatusMetrics = useJobStatusMetrics as ReturnType<typeof vi.fn>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

const mockData = {
  new_requests: 5,
  estimates: 3,
  pending_approval: 2,
  to_be_scheduled: 4,
  in_progress: 7,
  complete: 12,
};

describe('JobStatusGrid', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all 6 status category cards', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    const grid = screen.getByTestId('job-status-grid');
    expect(grid).toBeInTheDocument();

    expect(screen.getByTestId('job-status-new-requests')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-estimates')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-pending-approval')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-to-be-scheduled')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-in-progress')).toBeInTheDocument();
    expect(screen.getByTestId('job-status-complete')).toBeInTheDocument();
  });

  it('displays correct counts for each category', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    expect(screen.getByTestId('job-status-new-requests')).toHaveTextContent('5');
    expect(screen.getByTestId('job-status-estimates')).toHaveTextContent('3');
    expect(screen.getByTestId('job-status-pending-approval')).toHaveTextContent('2');
    expect(screen.getByTestId('job-status-to-be-scheduled')).toHaveTextContent('4');
    expect(screen.getByTestId('job-status-in-progress')).toHaveTextContent('7');
    expect(screen.getByTestId('job-status-complete')).toHaveTextContent('12');
  });

  it('displays correct labels for each category', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    expect(screen.getByTestId('job-status-new-requests')).toHaveTextContent('New Requests');
    expect(screen.getByTestId('job-status-estimates')).toHaveTextContent('Estimates');
    expect(screen.getByTestId('job-status-pending-approval')).toHaveTextContent('Pending Approval');
    expect(screen.getByTestId('job-status-to-be-scheduled')).toHaveTextContent('To Be Scheduled');
    expect(screen.getByTestId('job-status-in-progress')).toHaveTextContent('In Progress');
    expect(screen.getByTestId('job-status-complete')).toHaveTextContent('Complete');
  });

  it('shows dash while loading', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    const cards = screen.getAllByText('—');
    expect(cards).toHaveLength(6);
  });

  it('shows zero counts when data has all zeros', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: {
        new_requests: 0,
        estimates: 0,
        pending_approval: 0,
        to_be_scheduled: 0,
        in_progress: 0,
        complete: 0,
      },
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    const zeros = screen.getAllByText('0');
    expect(zeros).toHaveLength(6);
  });

  it('navigates to /jobs?status=requested on New Requests click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-new-requests'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=requested');
  });

  it('navigates to /jobs?status=requires_estimate on Estimates click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-estimates'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=requires_estimate');
  });

  it('navigates to /jobs?status=pending_approval on Pending Approval click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-pending-approval'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=pending_approval');
  });

  it('navigates to /jobs?status=approved on To Be Scheduled click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-to-be-scheduled'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=approved');
  });

  it('navigates to /jobs?status=in_progress on In Progress click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-in-progress'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=in_progress');
  });

  it('navigates to /jobs?status=completed on Complete click', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.click(screen.getByTestId('job-status-complete'));
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=completed');
  });

  it('navigates on Enter key press', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('job-status-new-requests'), { key: 'Enter' });
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=requested');
  });

  it('navigates on Space key press', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: mockData,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    fireEvent.keyDown(screen.getByTestId('job-status-complete'), { key: ' ' });
    expect(mockNavigate).toHaveBeenCalledWith('/jobs?status=completed');
  });

  it('defaults to 0 when data is undefined', () => {
    mockUseJobStatusMetrics.mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    render(<JobStatusGrid />, { wrapper: createWrapper() });

    const zeros = screen.getAllByText('0');
    expect(zeros).toHaveLength(6);
  });
});
