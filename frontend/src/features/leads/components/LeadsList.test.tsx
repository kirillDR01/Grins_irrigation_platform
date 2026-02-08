import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { LeadsList } from './LeadsList';
import { leadApi } from '../api/leadApi';
import type { Lead } from '../types';

// Mock the API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    list: vi.fn(),
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
    zip_code: '55424',
    situation: 'new_system',
    notes: 'Large backyard',
    source_site: 'residential',
    status: 'new',
    assigned_to: null,
    customer_id: null,
    contacted_at: null,
    converted_at: null,
    created_at: '2025-01-20T10:00:00Z',
    updated_at: '2025-01-20T10:00:00Z',
  },
  {
    id: 'lead-002',
    name: 'Jane Smith',
    phone: '6125555678',
    email: null,
    zip_code: '55305',
    situation: 'repair',
    notes: null,
    source_site: 'residential',
    status: 'contacted',
    assigned_to: 'staff-001',
    customer_id: null,
    contacted_at: '2025-01-21T09:00:00Z',
    converted_at: null,
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

describe('LeadsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

    // Zip codes visible
    expect(screen.getByText('55424')).toBeInTheDocument();
    expect(screen.getByText('55305')).toBeInTheDocument();

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

  it('renders filter controls', async () => {
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
});
