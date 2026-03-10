import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { WorkRequestsList } from './WorkRequestsList';
import { workRequestApi } from '../api/workRequestApi';
import type { WorkRequest, PaginatedWorkRequestResponse, SyncStatus } from '../types';

vi.mock('../api/workRequestApi', () => ({
  workRequestApi: {
    list: vi.fn(),
    getSyncStatus: vi.fn(),
    triggerSync: vi.fn(),
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const baseRequest: WorkRequest = {
  id: 'wr-001',
  sheet_row_number: 2,
  timestamp: '2026-01-15T10:00:00Z',
  spring_startup: 'Yes',
  fall_blowout: null,
  summer_tuneup: null,
  repair_existing: null,
  new_system_install: null,
  addition_to_system: null,
  additional_services_info: null,
  date_work_needed_by: 'ASAP',
  name: 'Alice Johnson',
  phone: '6125551234',
  email: 'alice@example.com',
  city: 'Minneapolis',
  address: '123 Main St',
  additional_info: null,
  client_type: 'new',
  property_type: 'Residential',
  referral_source: 'Google',
  landscape_hardscape: null,
  processing_status: 'imported',
  processing_error: null,
  lead_id: null,
  imported_at: '2026-01-15T12:00:00Z',
  created_at: '2026-01-15T12:00:00Z',
  updated_at: '2026-01-15T12:00:00Z',
  promoted_to_lead_id: null,
  promoted_at: null,
};

const mockRequests: WorkRequest[] = [
  baseRequest,
  {
    ...baseRequest,
    id: 'wr-002',
    sheet_row_number: 3,
    name: 'Bob Smith',
    phone: '6125555678',
    email: null,
    client_type: 'existing',
    processing_status: 'lead_created',
    lead_id: 'lead-001',
    imported_at: '2026-01-16T08:00:00Z',
    created_at: '2026-01-16T08:00:00Z',
    updated_at: '2026-01-16T08:00:00Z',
    promoted_to_lead_id: 'lead-001',
    promoted_at: '2026-01-16T08:05:00Z',
  },
];

const mockPaginated: PaginatedWorkRequestResponse = {
  items: mockRequests,
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
};

const mockSyncStatus: SyncStatus = {
  last_sync: '2026-01-15T12:00:00Z',
  is_running: true,
  last_error: null,
};

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

describe('WorkRequestsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(workRequestApi.getSyncStatus).mockResolvedValue(mockSyncStatus);
  });

  it('renders loading state initially', () => {
    vi.mocked(workRequestApi.list).mockImplementation(() => new Promise(() => {}));

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    expect(screen.getAllByTestId('loading-spinner').length).toBeGreaterThan(0);
  });

  it('renders table with data when loaded', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('work-requests-page')).toBeInTheDocument();
    });

    expect(screen.getByTestId('work-requests-table')).toBeInTheDocument();
    expect(screen.getAllByTestId('work-request-row')).toHaveLength(2);
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
    expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    expect(screen.getByText('6125551234')).toBeInTheDocument();
    expect(screen.getByText('6125555678')).toBeInTheDocument();
  });

  it('renders submission count', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('submission-count')).toHaveTextContent('2 submissions total');
    });
  });

  it('renders empty state when no data', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });

    expect(screen.getByText('No work requests found.')).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    vi.mocked(workRequestApi.list).mockRejectedValue(new Error('Network Error'));

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('error-message').length).toBeGreaterThan(0);
    });
  });

  it('navigates to detail on row click', async () => {
    const user = userEvent.setup();
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('work-request-row')).toHaveLength(2);
    });

    await user.click(screen.getAllByTestId('work-request-row')[0]);
    expect(mockNavigate).toHaveBeenCalledWith('/work-requests/wr-001');
  });

  it('renders filter controls', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('search-input')).toBeInTheDocument();
    });

    expect(screen.getByTestId('filter-processing-status')).toBeInTheDocument();
    expect(screen.getByTestId('filter-client-type')).toBeInTheDocument();
  });

  it('renders sync status bar', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('sync-status-bar')).toBeInTheDocument();
    });
  });

  it('renders trigger sync button', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('trigger-sync-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('trigger-sync-btn')).toHaveTextContent('Sync Now');
  });

  it('calls trigger sync on button click', async () => {
    const user = userEvent.setup();
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);
    vi.mocked(workRequestApi.triggerSync).mockResolvedValue({ new_rows_imported: 3 });

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('trigger-sync-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('trigger-sync-btn'));

    await waitFor(() => {
      expect(workRequestApi.triggerSync).toHaveBeenCalled();
    });
  });

  it('renders pagination controls when data exists', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('pagination-controls')).toBeInTheDocument();
    });

    expect(screen.getByText('Page 1 of 1')).toBeInTheDocument();
  });

  it('does not render pagination when no data', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('No work requests found.')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('pagination-controls')).not.toBeInTheDocument();
  });

  it('renders processing status badges', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('status-imported')).toBeInTheDocument();
    });

    expect(screen.getByTestId('status-lead_created')).toBeInTheDocument();
  });

  it('shows singular submission text for count of 1', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue({
      items: [mockRequests[0]],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('submission-count')).toHaveTextContent('1 submission total');
    });
  });

  // ---- Promoted-to-Lead badge tests ----

  it('renders promoted-to-lead badge for work requests with promoted_to_lead_id', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('work-request-row')).toHaveLength(2);
    });

    // wr-002 has promoted_to_lead_id
    expect(screen.getByTestId('promoted-badge-wr-002')).toBeInTheDocument();
    expect(screen.getByTestId('promoted-badge-wr-002')).toHaveTextContent('Lead');

    // wr-001 does NOT have promoted_to_lead_id
    expect(screen.queryByTestId('promoted-badge-wr-001')).not.toBeInTheDocument();
  });

  it('promoted badge links to lead detail', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('promoted-badge-wr-002')).toBeInTheDocument();
    });

    const badge = screen.getByTestId('promoted-badge-wr-002');
    expect(badge.closest('a')).toHaveAttribute('href', '/leads/lead-001');
  });

  it('promoted badge shows promoted_at in title', async () => {
    vi.mocked(workRequestApi.list).mockResolvedValue(mockPaginated);

    render(<WorkRequestsList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('promoted-badge-wr-002')).toBeInTheDocument();
    });

    const badge = screen.getByTestId('promoted-badge-wr-002');
    // Title should contain "Promoted" text
    expect(badge.closest('a')?.getAttribute('title')).toContain('Promoted');
  });
});
