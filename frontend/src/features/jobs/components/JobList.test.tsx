import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
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
    service_agreement_id: null,
    job_type: 'spring_startup',
    category: 'ready_to_schedule',
    status: 'requested',
    description: 'Spring startup for irrigation system',
    summary: 'Spring startup - residential',
    notes: 'Customer prefers morning appointments',
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
    target_start_date: null,
    target_end_date: null,
    requested_at: '2025-01-20T10:00:00Z',
    approved_at: null,
    scheduled_at: null,
    started_at: null,
    completed_at: null,
    closed_at: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-20T10:00:00Z',
    customer_name: 'John Doe',
    customer_tags: ['priority', 'new_customer'],
  },
  {
    id: '123e4567-e89b-12d3-a456-426614174002',
    customer_id: '123e4567-e89b-12d3-a456-426614174003',
    property_id: null,
    service_offering_id: null,
    service_agreement_id: null,
    job_type: 'repair',
    category: 'requires_estimate',
    status: 'in_progress',
    description: 'Fix broken sprinkler head',
    summary: null,
    notes: null,
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
    target_start_date: null,
    target_end_date: '2025-02-01',
    requested_at: '2025-01-19T14:00:00Z',
    approved_at: '2025-01-19T15:00:00Z',
    scheduled_at: '2025-01-20T09:00:00Z',
    started_at: '2025-01-20T09:30:00Z',
    completed_at: null,
    closed_at: null,
    created_at: '2025-01-19T14:00:00Z',
    updated_at: '2025-01-20T09:30:00Z',
    customer_name: 'Jane Smith',
    customer_tags: ['red_flag', 'slow_payer'],
  },
];

const mockSubscriptionJob: Job = {
  id: '123e4567-e89b-12d3-a456-426614174010',
  customer_id: '123e4567-e89b-12d3-a456-426614174001',
  property_id: null,
  service_offering_id: null,
  service_agreement_id: 'agr-001',
  job_type: 'spring_startup',
  category: 'ready_to_schedule',
  status: 'approved',
  description: 'Subscription spring startup',
  summary: 'Subscription spring startup',
  notes: null,
  estimated_duration_minutes: 60,
  priority_level: 0,
  weather_sensitive: false,
  staffing_required: 1,
  equipment_required: null,
  materials_required: null,
  quoted_amount: null,
  final_amount: null,
  source: 'website',
  source_details: null,
  payment_collected_on_site: false,
  target_start_date: '2025-04-01',
  target_end_date: '2025-04-30',
  requested_at: '2025-01-20T10:00:00Z',
  approved_at: '2025-01-20T10:00:00Z',
  scheduled_at: null,
  started_at: null,
  completed_at: null,
  closed_at: null,
  created_at: '2025-01-20T10:00:00Z',
  updated_at: '2025-01-20T10:00:00Z',
  customer_name: 'John Doe',
  customer_tags: ['priority'],
};

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

function createMemoryWrapper(initialEntries: string[] = ['/jobs']) {
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
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
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

  it('displays simplified status labels (Req 21)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('To Be Scheduled')).toBeInTheDocument();
    });

    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('displays customer names linked to customer detail (Req 22)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    expect(screen.getByText('Jane Smith')).toBeInTheDocument();

    // Customer name should be a link
    const customerLink = screen.getByTestId(`job-customer-${mockJobs[0].id}`);
    expect(customerLink.tagName).toBe('A');
    expect(customerLink).toHaveAttribute('href', `/customers/${mockJobs[0].customer_id}`);
  });

  it('displays customer tags as color-coded badges (Req 22)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId(`job-tags-${mockJobs[0].id}`)).toBeInTheDocument();
    });

    expect(screen.getByTestId('tag-priority')).toBeInTheDocument();
    expect(screen.getByText('New Customer')).toBeInTheDocument();
    expect(screen.getByTestId('tag-red_flag')).toBeInTheDocument();
    expect(screen.getByText('Slow Payer')).toBeInTheDocument();
  });

  it('displays Days Waiting column (Req 22)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId(`days-waiting-${mockJobs[0].id}`)).toBeInTheDocument();
    });

    // Days waiting should be a number
    const daysEl = screen.getByTestId(`days-waiting-${mockJobs[0].id}`);
    expect(Number(daysEl.textContent)).toBeGreaterThanOrEqual(0);
  });

  it('displays Due By column with "No deadline" for null dates (Req 23)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: [mockJobs[0]], // No target_end_date
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId(`due-by-${mockJobs[0].id}`)).toBeInTheDocument();
    });

    expect(screen.getByText('No deadline')).toBeInTheDocument();
  });

  it('displays summary column (Req 20)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId(`job-summary-${mockJobs[0].id}`)).toBeInTheDocument();
    });

    expect(screen.getByText('Spring startup - residential')).toBeInTheDocument();
  });

  it('does not display Category column (Req 22)', async () => {
    vi.mocked(jobApi.list).mockResolvedValue({
      items: mockJobs,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<JobList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('job-table')).toBeInTheDocument();
    });

    // Category column header should not exist
    expect(screen.queryByText('Category')).not.toBeInTheDocument();
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

  it('renders simplified status filter dropdown (Req 21)', async () => {
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

    expect(screen.getByText('All Statuses')).toBeInTheDocument();
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

    const actionsButton = screen.getByTestId(`job-actions-${mockJobs[0].id}`);
    await user.click(actionsButton);
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

    const actionsButton = screen.getByTestId(`job-actions-${mockJobs[0].id}`);
    await user.click(actionsButton);
    await user.click(screen.getByText('Delete'));

    expect(onDelete).toHaveBeenCalledWith(mockJobs[0]);
  });

  describe('Subscription extensions', () => {
    it('displays subscription source badge for jobs with service_agreement_id', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: [mockSubscriptionJob],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId(`subscription-badge-${mockSubscriptionJob.id}`)).toBeInTheDocument();
      });

      expect(screen.getByText('Sub')).toBeInTheDocument();
    });

    it('does not display subscription badge for standalone jobs', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(screen.queryByTestId(`subscription-badge-${mockJobs[0].id}`)).not.toBeInTheDocument();
      expect(screen.queryByTestId(`subscription-badge-${mockJobs[1].id}`)).not.toBeInTheDocument();
    });

    it('renders source type filter dropdown', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('source-type-filter')).toBeInTheDocument();
      });
    });

    it('renders target date filter button', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('target-date-filter')).toBeInTheDocument();
      });

      expect(screen.getByText('Target dates')).toBeInTheDocument();
    });
  });

  /**
   * URL parameter parsing and filter application tests.
   * Validates: Requirements 3.7
   */
  describe('URL parameter parsing and filter application', () => {
    it('parses ?status=in_progress from URL and auto-applies the status filter', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: [mockJobs[1]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper(['/jobs?status=in_progress']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(jobApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'in_progress' })
      );
    });

    it('parses ?status=requested from URL and auto-applies the status filter', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: [mockJobs[0]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper(['/jobs?status=requested']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(jobApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'requested' })
      );
    });

    it('applies highlight-fade animation class when ?highlight={id} is present', async () => {
      const highlightJobId = mockJobs[0].id;
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper([`/jobs?highlight=${highlightJobId}`]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      const rows = screen.getAllByTestId('job-row');
      const highlightedRow = rows.find(
        (row) => row.getAttribute('data-job-id') === highlightJobId
      );
      expect(highlightedRow).toBeDefined();
      expect(highlightedRow!.className).toContain('animate-highlight-fade');
    });

    it('does not apply highlight class to non-matching rows', async () => {
      const highlightJobId = mockJobs[0].id;
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper([`/jobs?highlight=${highlightJobId}`]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      const rows = screen.getAllByTestId('job-row');
      const nonHighlightedRow = rows.find(
        (row) => row.getAttribute('data-job-id') !== highlightJobId
      );
      expect(nonHighlightedRow).toBeDefined();
      expect(nonHighlightedRow!.className).not.toContain('animate-highlight-fade');
    });

    it('works correctly without any URL parameters (default state)', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper(['/jobs']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(jobApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: undefined })
      );

      const rows = screen.getAllByTestId('job-row');
      rows.forEach((row) => {
        expect(row.className).not.toContain('animate-highlight-fade');
      });
    });

    it('ignores invalid/unknown status parameters gracefully', async () => {
      vi.mocked(jobApi.list).mockResolvedValue({
        items: mockJobs,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper(['/jobs?status=invalid_status']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(jobApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: undefined })
      );
    });

    it('handles both status and highlight params together', async () => {
      const highlightJobId = mockJobs[1].id;
      vi.mocked(jobApi.list).mockResolvedValue({
        items: [mockJobs[1]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<JobList />, {
        wrapper: createMemoryWrapper([
          `/jobs?status=in_progress&highlight=${highlightJobId}`,
        ]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('job-table')).toBeInTheDocument();
      });

      expect(jobApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'in_progress' })
      );

      const rows = screen.getAllByTestId('job-row');
      const highlightedRow = rows.find(
        (row) => row.getAttribute('data-job-id') === highlightJobId
      );
      expect(highlightedRow).toBeDefined();
      expect(highlightedRow!.className).toContain('animate-highlight-fade');
    });
  });
});
