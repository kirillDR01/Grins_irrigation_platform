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
    created_at: '2025-01-19T14:00:00Z',
    updated_at: '2025-01-21T09:00:00Z',
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

function createMemoryWrapper(initialEntries: string[] = ['/leads']) {
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
    vi.mocked(leadApi.list).mockImplementation(
      () => new Promise(() => {}) // Never resolves — stays in loading
    );

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

    // Table renders
    expect(screen.getByTestId('leads-table')).toBeInTheDocument();

    // Both rows render
    expect(screen.getAllByTestId('lead-row')).toHaveLength(2);

    // Lead names visible
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();

    // Phone numbers visible
    expect(screen.getByText('6125551234')).toBeInTheDocument();
    expect(screen.getByText('6125555678')).toBeInTheDocument();

    // Source badges visible
    expect(screen.getByTestId('lead-source-website')).toBeInTheDocument();
    expect(screen.getByTestId('lead-source-phone_call')).toBeInTheDocument();

    // Consent indicators visible
    expect(screen.getByTestId('sms-consent-lead-001')).toBeInTheDocument();
    expect(screen.getByTestId('terms-accepted-lead-001')).toBeInTheDocument();

    // Total count shown
    expect(screen.getByText('2 leads total')).toBeInTheDocument();
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

    expect(
      screen.getByText('Try adjusting your filters or check back later.')
    ).toBeInTheDocument();
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

    // Click first row
    await user.click(screen.getAllByTestId('lead-row')[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/leads/lead-001');
  });

  it('renders filter controls with source filter and intake tabs', async () => {
    vi.mocked(leadApi.list).mockResolvedValue({
      items: mockLeads,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<LeadsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('lead-filters')).toBeInTheDocument();
    });

    // Search input present
    expect(screen.getByTestId('lead-search-input')).toBeInTheDocument();

    // Status filter present
    expect(screen.getByTestId('lead-status-filter')).toBeInTheDocument();

    // Situation filter present
    expect(screen.getByTestId('lead-situation-filter')).toBeInTheDocument();

    // Source filter present
    expect(screen.getByTestId('lead-source-filter')).toBeInTheDocument();

    // Intake tag tabs present
    expect(screen.getByTestId('intake-tag-tabs')).toBeInTheDocument();
    expect(screen.getByTestId('intake-tab-all')).toBeInTheDocument();
    expect(screen.getByTestId('intake-tab-schedule')).toBeInTheDocument();
    expect(screen.getByTestId('intake-tab-follow_up')).toBeInTheDocument();
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

  it('does not render pagination when no data', async () => {
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

    expect(screen.queryByTestId('leads-pagination')).not.toBeInTheDocument();
  });

  /**
   * URL parameter parsing and filter application tests.
   * Validates: Requirements 3.7
   */
  describe('URL parameter parsing and filter application', () => {
    it('parses ?status=new from URL and auto-applies the status filter', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: [mockLeads[0]], // 'new' status lead
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

      // Verify the API was called with the status filter from URL
      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'new' })
      );
    });

    it('parses ?status=contacted from URL and auto-applies the status filter', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: [mockLeads[1]], // 'contacted' status lead
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

    it('applies highlight-fade animation class when ?highlight={id} is present', async () => {
      const highlightLeadId = mockLeads[0].id;
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper([`/leads?highlight=${highlightLeadId}`]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      // Find the highlighted row by data-lead-id attribute
      const rows = screen.getAllByTestId('lead-row');
      const highlightedRow = rows.find(
        (row) => row.getAttribute('data-lead-id') === highlightLeadId
      );
      expect(highlightedRow).toBeDefined();
      expect(highlightedRow!.className).toContain('animate-highlight-fade');
    });

    it('does not apply highlight class to non-matching rows', async () => {
      const highlightLeadId = mockLeads[0].id;
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper([`/leads?highlight=${highlightLeadId}`]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      const rows = screen.getAllByTestId('lead-row');
      const nonHighlightedRow = rows.find(
        (row) => row.getAttribute('data-lead-id') !== highlightLeadId
      );
      expect(nonHighlightedRow).toBeDefined();
      expect(nonHighlightedRow!.className).not.toContain('animate-highlight-fade');
    });

    it('works correctly without any URL parameters (default state)', async () => {
      vi.mocked(leadApi.list).mockResolvedValue({
        items: mockLeads,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper(['/leads']),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      // API called without status filter
      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: undefined })
      );

      // No rows should have highlight animation
      const rows = screen.getAllByTestId('lead-row');
      rows.forEach((row) => {
        expect(row.className).not.toContain('animate-highlight-fade');
      });
    });

    it('ignores invalid/unknown status parameters gracefully', async () => {
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

      // Invalid status should be ignored — API called with status undefined
      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: undefined })
      );
    });

    it('handles both status and highlight params together', async () => {
      const highlightLeadId = mockLeads[0].id;
      vi.mocked(leadApi.list).mockResolvedValue({
        items: [mockLeads[0]],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      render(<LeadsList />, {
        wrapper: createMemoryWrapper([
          `/leads?status=new&highlight=${highlightLeadId}`,
        ]),
      });

      await waitFor(() => {
        expect(screen.getByTestId('leads-table')).toBeInTheDocument();
      });

      // Status filter applied
      expect(leadApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'new' })
      );

      // Highlight applied
      const rows = screen.getAllByTestId('lead-row');
      const highlightedRow = rows.find(
        (row) => row.getAttribute('data-lead-id') === highlightLeadId
      );
      expect(highlightedRow).toBeDefined();
      expect(highlightedRow!.className).toContain('animate-highlight-fade');
    });
  });
});
