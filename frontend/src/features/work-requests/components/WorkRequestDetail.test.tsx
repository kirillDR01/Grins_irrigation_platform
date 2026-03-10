import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { WorkRequestDetail } from './WorkRequestDetail';
import { workRequestApi } from '../api/workRequestApi';
import type { WorkRequest } from '../types';

vi.mock('../api/workRequestApi', () => ({
  workRequestApi: {
    getById: vi.fn(),
    createLead: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const baseRequest: WorkRequest = {
  id: 'wr-001',
  sheet_row_number: 2,
  timestamp: '2026-01-15T10:00:00Z',
  spring_startup: 'Yes',
  fall_blowout: 'No',
  summer_tuneup: null,
  repair_existing: 'Yes',
  new_system_install: null,
  addition_to_system: 'Maybe',
  additional_services_info: 'Extra info here',
  date_work_needed_by: 'ASAP',
  name: 'Alice Johnson',
  phone: '6125551234',
  email: 'alice@example.com',
  city: 'Minneapolis',
  address: '123 Main St',
  additional_info: 'Some notes',
  client_type: 'new',
  property_type: 'Residential',
  referral_source: 'Google',
  landscape_hardscape: 'Landscape work',
  processing_status: 'imported',
  processing_error: null,
  lead_id: null,
  imported_at: '2026-01-15T12:00:00Z',
  created_at: '2026-01-15T12:00:00Z',
  updated_at: '2026-01-15T12:00:00Z',
  promoted_to_lead_id: null,
  promoted_at: null,
};

function renderWithRoute(id: string = 'wr-001') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/work-requests/${id}`]}>
        <Routes>
          <Route path="/work-requests/:id" element={<WorkRequestDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('WorkRequestDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(workRequestApi.getById).mockImplementation(() => new Promise(() => {}));
    renderWithRoute();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    vi.mocked(workRequestApi.getById).mockRejectedValue(new Error('Not found'));
    renderWithRoute();
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });
  });

  it('renders all 19 sheet fields when loaded', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('work-request-detail')).toBeInTheDocument();
    });

    // Contact fields (name appears in header + field, so use getAllByText)
    expect(screen.getAllByText('Alice Johnson').length).toBeGreaterThan(0);
    expect(screen.getByText('6125551234')).toBeInTheDocument();
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByText('Minneapolis')).toBeInTheDocument();
    expect(screen.getByText('123 Main St')).toBeInTheDocument();

    // Service fields (Yes appears for both spring_startup and repair_existing)
    expect(screen.getAllByText('Yes').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('No')).toBeInTheDocument(); // fall_blowout
    expect(screen.getByText('Maybe')).toBeInTheDocument(); // addition_to_system
    expect(screen.getByText('Extra info here')).toBeInTheDocument();

    // Additional details
    expect(screen.getByText('new')).toBeInTheDocument(); // client_type
    expect(screen.getByText('Residential')).toBeInTheDocument();
    expect(screen.getByText('ASAP')).toBeInTheDocument();
    expect(screen.getByText('Google')).toBeInTheDocument();
    expect(screen.getByText('Landscape work')).toBeInTheDocument();
    expect(screen.getByText('Some notes')).toBeInTheDocument();
  });

  it('renders processing status badge', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('status-imported')).toBeInTheDocument();
    });
  });

  it('shows create lead button when no lead linked', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('create-lead-btn')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('lead-link')).not.toBeInTheDocument();
  });

  it('shows lead link when lead exists', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue({
      ...baseRequest,
      processing_status: 'lead_created',
      lead_id: 'lead-123',
    });
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getAllByTestId('lead-link').length).toBeGreaterThan(0);
    });

    expect(screen.queryByTestId('create-lead-btn')).not.toBeInTheDocument();
  });

  it('calls createLead on button click', async () => {
    const user = userEvent.setup();
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    vi.mocked(workRequestApi.createLead).mockResolvedValue({
      ...baseRequest,
      processing_status: 'lead_created',
      lead_id: 'lead-new',
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('create-lead-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('create-lead-btn'));

    await waitFor(() => {
      expect(workRequestApi.createLead).toHaveBeenCalledWith('wr-001');
    });
  });

  it('shows toast on create lead success', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    vi.mocked(workRequestApi.createLead).mockResolvedValue({
      ...baseRequest,
      processing_status: 'lead_created',
      lead_id: 'lead-new',
    });

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('create-lead-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('create-lead-btn'));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Lead Created', expect.any(Object));
    });
  });

  it('shows error toast on create lead failure', async () => {
    const { toast } = await import('sonner');
    const user = userEvent.setup();
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    vi.mocked(workRequestApi.createLead).mockRejectedValue(new Error('Conflict'));

    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('create-lead-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('create-lead-btn'));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Lead Creation Failed', expect.any(Object));
    });
  });

  it('displays processing error when present', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue({
      ...baseRequest,
      processing_status: 'error',
      processing_error: 'Phone parse failed',
    });
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Phone parse failed')).toBeInTheDocument();
    });
  });

  it('displays dashes for null fields', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue({
      ...baseRequest,
      email: null,
      city: null,
      summer_tuneup: null,
    });
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('work-request-detail')).toBeInTheDocument();
    });

    // Null fields render as '—'
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });

  it('displays row number in metadata', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('#2')).toBeInTheDocument();
    });
  });

  // ---- Promoted-to-Lead section ----

  it('shows promoted-to-lead link when promoted_to_lead_id is set', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue({
      ...baseRequest,
      promoted_to_lead_id: 'lead-abc',
      promoted_at: '2026-01-15T13:00:00Z',
    });
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('promoted-lead-link')).toBeInTheDocument();
    });

    const link = screen.getByTestId('promoted-lead-link');
    expect(link).toHaveAttribute('href', '/leads/lead-abc');
    expect(screen.getByText('View Promoted Lead')).toBeInTheDocument();
  });

  it('shows promoted_at timestamp when present', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue({
      ...baseRequest,
      promoted_to_lead_id: 'lead-abc',
      promoted_at: '2026-01-15T13:00:00Z',
    });
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByText('Promoted to Lead')).toBeInTheDocument();
    });
  });

  it('does not show promoted section when promoted_to_lead_id is null', async () => {
    vi.mocked(workRequestApi.getById).mockResolvedValue(baseRequest);
    renderWithRoute();

    await waitFor(() => {
      expect(screen.getByTestId('work-request-detail')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('promoted-lead-link')).not.toBeInTheDocument();
    expect(screen.queryByText('Promoted to Lead')).not.toBeInTheDocument();
  });
});
