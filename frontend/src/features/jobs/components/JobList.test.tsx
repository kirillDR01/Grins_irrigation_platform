import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { JobList } from './JobList';
import { jobApi } from '../api/jobApi';
import type { Job } from '../types';

// Mock the API
vi.mock('../api/jobApi', () => ({
  jobApi: {
    list: vi.fn(),
  },
}));

const mockJobs: Job[] = [
  {
    id: '123e4567-e89b-12d3-a456-426614174000',
    customer_id: '123e4567-e89b-12d3-a456-426614174001',
    property_id: null,
    service_offering_id: null,
    job_type: 'spring_startup',
    category: 'ready_to_schedule',
    status: 'requested',
    description: 'Spring startup for irrigation system',
    estimated_duration_minutes: 60,
    priority_level: 0,
    weather_sensitive: false,
    staffing_required: 1,
    equipment_required: null,
    materials_required: null,
    quoted_amount: 150,
    final_amount: null,
    source: 'website',
    source_details: null,
    payment_collected_on_site: false,
    requested_at: '2025-01-20T10:00:00Z',
    approved_at: null,
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    closed_at: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-20T10:00:00Z',
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174002',
    customer_id: '123e4567-e89b-12d3-a456-426614174003',
    property_id: null,
    service_offering_id: null,
    job_type: 'repair',
    category: 'requires_estimate',
    status: 'in_progress',
    description: 'Fix broken sprinkler head',
    estimated_duration_minutes: 30,
    priority_level: 2,
    weather_sensitive: true,
    staffing_required: 1,
    equipment_required: ['wrench'],
    materials_required: ['sprinkler head'],
    quoted_amount: 75,
    final_amount: null,
    source: 'phone',
    source_details: null,
    payment_collected_on_site: false,
    requested_at: '2025-01-19T14:00:00Z',
    approved_at: '2025-01-19T15:00:00Z',
    scheduled_at: '2025-01-20T09:00:00Z',
    started_at: '2025-01-20T09:30:00Z',
    completed_at: null,
    closed_at: null,
    created_at: '2025-01-19T14:00:00Z',
    updated_at: '2025-01-20T09:30:00Z',
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

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

describe('JobList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(jobApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<JobList />, { wrapper: createWrapper() });

    expect(screen.getByText('Loading jobs...')).toBeInTheDocument();
  });

  it('renders job list when data loads', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('job-list')).toBeInTheDocument();
    });

    expect(screen.getByTestId('job-table')).toBeInTheDocument();
    expect(screen.getAllByTestId('job-row')).toHaveLength(2);
  });

  it('displays job types correctly', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Spring Startup')).toBeInTheDocument();
    });

    expect(screen.getByText('Repair')).toBeInTheDocument();
  });

  it('displays job statuses correctly', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('status-requested')).toBeInTheDocument();
    });

    expect(screen.getByTestId('status-in_progress')).toBeInTheDocument();
  });

  it('displays priority levels correctly', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Normal')).toBeInTheDocument();
    });

    expect(screen.getByText('Urgent')).toBeInTheDocument();
  });

  it('renders empty state when no jobs', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('No jobs found.')).toBeInTheDocument();
    });
  });

  it('renders error state on API failure', async () => {
    vi.mocked(jobApi.list).mockRejectedValue(new Error('API Error'));

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('renders status filter dropdown', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('status-filter')).toBeInTheDocument();
    });

    // Verify the filter is present
    expect(screen.getByText('All Statuses')).toBeInTheDocument();
  });

  it('renders category filter dropdown', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('category-filter')).toBeInTheDocument();
    });

    // Verify the filter is present
    expect(screen.getByText('All Categories')).toBeInTheDocument();
  });

  it('calls onEdit when edit action is clicked', async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList onEdit={onEdit} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('job-table')).toBeInTheDocument();
    });

    // Open actions menu for first job
    const actionsButton = screen.getByTestId(
      `job-actions-${mockJobs[0].id}`
    );
    await user.click(actionsButton);

    // Click edit
    await user.click(screen.getByText('Edit'));

    expect(onEdit).toHaveBeenCalledWith(mockJobs[0]);
  });

  it('calls onDelete when delete action is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList onDelete={onDelete} />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('job-table')).toBeInTheDocument();
    });

    // Open actions menu for first job
    const actionsButton = screen.getByTestId(
      `job-actions-${mockJobs[0].id}`
    );
    await user.click(actionsButton);

    // Click delete
    await user.click(screen.getByText('Delete'));

    expect(onDelete).toHaveBeenCalledWith(mockJobs[0]);
  });
});
