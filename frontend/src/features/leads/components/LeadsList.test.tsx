import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { LeadsList } from './LeadsList';
import { leadApi } from '../api/leadApi';
import type { Lead } from '../types';

// Mock the API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    list: vi.fn(),
    followUpQueue: vi.fn(),
    delete: vi.fn(),
    moveToJobs: vi.fn(),
    moveToSales: vi.fn(),
    markContacted: vi.fn(),
  },
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock NewTextCampaignModal to avoid AuthProvider dependency
vi.mock('@/features/communications', () => ({
  NewTextCampaignModal: ({ open, preSelectedLeadIds }: { open: boolean; preSelectedLeadIds?: string[] }) =>
    open ? <div data-testid="campaign-modal">Campaign Modal ({preSelectedLeadIds?.length ?? 0} leads)</div> : null,
}));

const mockLeads: Lead[] = [
  {
    id: 'lead-001',
    name: 'John Doe',
    phone: '6125551234',
    email: 'john@example.com',
    address: '123 Main St',
    city: 'Minneapolis',
    state: 'MN',
    zip_code: '55424',
    situation: 'new_system',
    notes: 'Large backyard',
    source_site: 'residential',
    status: 'new',
    assigned_to: null,
    customer_id: null,
    contacted_at: null,
    converted_at: null,
    lead_source: 'website',
    source_detail: null,
    intake_tag: 'schedule',
    action_tags: ['NEEDS_CONTACT'],
    sms_consent: true,
    terms_accepted: true,
    email_marketing_consent: true,
    job_requested: 'Spring Startup',
    last_contacted_at: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-20T10:00:00Z',
  },
  {
    id: 'lead-002',
    name: 'Jane Smith',
    phone: '6125555678',
    email: null,
    address: null,
    city: 'Edina',
    state: 'MN',
    zip_code: '55305',
    situation: 'repair',
    notes: null,
    source_site: 'residential',
    status: 'contacted',
    assigned_to: 'staff-001',
    customer_id: null,
    contacted_at: '2025-01-21T09:00:00Z',
    converted_at: null,
    lead_source: 'phone_call',
    source_detail: 'Inbound call',
    intake_tag: null,
    action_tags: [],
    sms_consent: false,
    terms_accepted: false,
    email_marketing_consent: false,
    job_requested: null,
    last_contacted_at: '2025-01-21T09:00:00Z',
    created_at: '2025-01-19T14:00:00Z',
    updated_at: '2025-01-21T09:00:00Z',
  },
];

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

function createMemoryWrapper(initialEntries: string[] = ['/leads']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('LeadsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(leadApi.followUpQueue).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });
  });

  it('renders loading state initially', () => {
    vi.mocked(leadApi.list).mockImplementation(() => new Promise(() => {}));
    render(<LeadsList />, { wrapper: createWrapper() });
    expect(screen.getByText('Loading leads...')).toBeInTheDocument();
  });

  it('renders table with lead data when loaded', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-page')).toBeInTheDocument();
    });

    expect(screen.getByTestId('leads-table')).toBeInTheDocument();
    expect(screen.getAllByTestId('lead-row')).toHaveLength(2);
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('6125551234')).toBeInTheDocument();
    expect(screen.getByText('6125555678')).toBeInTheDocument();

    // Source column renders as plain text (no colored badge)
    expect(screen.getByTestId('lead-source-website')).toBeInTheDocument();
    expect(screen.getByTestId('lead-source-phone_call')).toBeInTheDocument();

    // Job Requested column
    expect(screen.getByText('Spring Startup')).toBeInTheDocument();

    // Total count shown
    expect(screen.getByText('2 leads total')).toBeInTheDocument();
  });

  it('does not render Intake column', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-table')).toBeInTheDocument();
    });

    // Intake column header should not exist
    expect(screen.queryByText('Intake')).not.toBeInTheDocument();
  });

  it('renders action buttons per row', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-table')).toBeInTheDocument();
    });

    // Move to Jobs and Move to Sales buttons on each row
    expect(screen.getByTestId('move-to-jobs-lead-001')).toBeInTheDocument();
    expect(screen.getByTestId('move-to-sales-lead-001')).toBeInTheDocument();
    expect(screen.getByTestId('delete-lead-lead-001')).toBeInTheDocument();

    // Mark contacted only on 'new' status leads
    expect(screen.getByTestId('mark-contacted-lead-001')).toBeInTheDocument();
    expect(screen.queryByTestId('mark-contacted-lead-002')).not.toBeInTheDocument();
  });

  it('renders empty state when no leads', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('No leads found.')).toBeInTheDocument();
    });
  });

  it('renders error state on API failure', async () => {
    vi.mocked(leadApi.list).mockRejectedValue(new Error('Network Error'));

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  it('navigates to lead detail on row click', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('lead-row')).toHaveLength(2);
    });

    await user.click(screen.getAllByTestId('lead-row')[0]);
    expect(mockNavigate).toHaveBeenCalledWith('/leads/lead-001');
  });

  it('shows delete confirmation dialog when delete button clicked', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-table')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('delete-lead-lead-001'));

    await waitFor(() => {
      expect(screen.getByTestId('delete-lead-dialog')).toBeInTheDocument();
    });

    expect(screen.getByText(/permanently delete/i)).toBeInTheDocument();
    expect(screen.getByTestId('confirm-delete-btn')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-delete-btn')).toBeInTheDocument();
  });

  it('calls delete API on confirm and closes dialog', async () => {
    const user = userEvent.setup();
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });
    vi.mocked(leadApi.delete).mockResolvedValue(undefined);

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-table')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('delete-lead-lead-001'));

    await waitFor(() => {
      expect(screen.getByTestId('delete-lead-dialog')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(leadApi.delete).toHaveBeenCalledWith('lead-001');
    });
  });

  it('renders pagination controls when data exists', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('leads-pagination')).toBeInTheDocument();
    });

    expect(screen.getByText('Page 1 of 1')).toBeInTheDocument();
    expect(screen.getByTestId('leads-prev-page')).toBeDisabled();
    expect(screen.getByTestId('leads-next-page')).toBeDisabled();
  });

  describe('URL parameter parsing', () => {
    it('parses ?status=new from URL', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: [mockLeads[0]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper(['/leads?status=new']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'new' })
      );
    });

    it('parses ?status=contacted from URL', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: [mockLeads[1]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper(['/leads?status=contacted']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'contacted' })
      );
    });

    it('applies highlight animation when ?highlight={id} is present', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper([`/leads?highlight=${mockLeads[0].id}`]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      const rows = screen.getAllByTestId('lead-row');
      const highlightedRow = rows.find(
        (row) => row.getAttribute('data-lead-id') === mockLeads[0].id
      );
      expect(highlightedRow!.className).toContain('animate-highlight-pulse');
    });

    it('ignores invalid status parameters', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper(['/leads?status=bogus_status']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: undefined })
      );
    });
  });

  describe('bulk select and Text Selected', () => {
    beforeEach(() => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });
    });

    it('renders checkbox column', async () => {
      render(<LeadsList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      expect(screen.getByTestId('select-all-checkbox')).toBeInTheDocument();
      expect(screen.getByTestId(`select-lead-${mockLeads[0].id}`)).toBeInTheDocument();
    });

    it('shows bulk-action bar when a row is checked', async () => {
      const user = userEvent.setup();
      render(<LeadsList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId(`select-lead-${mockLeads[0].id}`));

      await waitFor(() => {
        expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
      });

      expect(screen.getByTestId('selected-count')).toHaveTextContent('1 selected');
    });

    it('selects all rows via select-all checkbox', async () => {
      const user = userEvent.setup();
      render(<LeadsList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('select-all-checkbox'));

      await waitFor(() => {
        expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
      });

      expect(screen.getByTestId('selected-count')).toHaveTextContent('2 selected');
    });
  });
});
