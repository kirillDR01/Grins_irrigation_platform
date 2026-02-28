import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { LeadDetail } from './LeadDetail';
import { leadApi } from '../api/leadApi';
import { staffApi } from '@/features/staff/api/staffApi';
import type { Lead } from '../types';

// Mock the lead API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    getById: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    convert: vi.fn(),
    list: vi.fn(),
  },
}));

// Mock the staff API
vi.mock('@/features/staff/api/staffApi', () => ({
  staffApi: {
    list: vi.fn(),
    getById: vi.fn(),
    getAvailable: vi.fn(),
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

// --- Mock Data ---

const baseLead: Lead = {
  id: 'lead-001',
  name: 'John Doe',
  phone: '6125551234',
  email: 'john@example.com',
  zip_code: '55424',
  situation: 'new_system',
  notes: 'Large backyard needs full irrigation',
  source_site: 'residential',
  status: 'new',
  assigned_to: null,
  customer_id: null,
  contacted_at: null,
  converted_at: null,
  created_at: '2025-01-20T10:00:00Z',
  updated_at: '2025-01-20T10:00:00Z',
};

const contactedLead: Lead = {
  ...baseLead,
  id: 'lead-002',
  status: 'contacted',
  contacted_at: '2025-01-21T09:00:00Z',
};

const convertedLead: Lead = {
  ...baseLead,
  id: 'lead-003',
  status: 'converted',
  customer_id: 'cust-001',
  converted_at: '2025-01-22T14:00:00Z',
};

const qualifiedLead: Lead = {
  ...baseLead,
  id: 'lead-004',
  status: 'qualified',
};

const mockStaffList = {
  items: [
    { id: 'staff-001', name: 'Viktor Grin', phone: '6125550001', role: 'owner', is_active: true },
    { id: 'staff-002', name: 'Vas Tech', phone: '6125550002', role: 'technician', is_active: true },
  ],
  total: 2,
  page: 1,
  page_size: 100,
  total_pages: 1,
};

// --- Helpers ---

function createWrapper(leadId: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/leads/${leadId}`]}>
          <Routes>
            <Route path="/leads/:id" element={children} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

// --- Tests ---

describe('LeadDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(staffApi.list).mockResolvedValue(mockStaffList);
  });

  // ---- Rendering all fields ----

  it('renders all lead fields correctly', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // Name (appears in PageHeader and CardTitle)
    expect(screen.getAllByText('John Doe').length).toBeGreaterThanOrEqual(1);
    // Phone
    expect(screen.getByText('6125551234')).toBeInTheDocument();
    // Email
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    // Zip code
    expect(screen.getByText('55424')).toBeInTheDocument();
    // Notes
    expect(screen.getByText('Large backyard needs full irrigation')).toBeInTheDocument();
    // Source site
    expect(screen.getByText('residential')).toBeInTheDocument();
    // Timestamps (submitted)
    expect(screen.getByText('Submitted')).toBeInTheDocument();
  });

  it('renders "Not provided" when email is null', async () => {
    const leadNoEmail: Lead = { ...baseLead, email: null };
    vi.mocked(leadApi.getById).mockResolvedValue(leadNoEmail);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.getByText('Not provided')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    vi.mocked(leadApi.getById).mockImplementation(() => new Promise(() => {}));

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    expect(screen.getByText('Loading lead...')).toBeInTheDocument();
  });

  it('renders error state on API failure', async () => {
    vi.mocked(leadApi.getById).mockRejectedValue(new Error('Network Error'));

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
    });
  });

  // ---- Status change dropdown ----

  it('renders status change dropdown with valid transitions for "new" status', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // Status dropdown should be present
    expect(screen.getByTestId('lead-status-dropdown')).toBeInTheDocument();
  });

  it('does not render status dropdown for converted lead (terminal state)', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(convertedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-003') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // No status dropdown for terminal state
    expect(screen.queryByTestId('lead-status-dropdown')).not.toBeInTheDocument();
  });

  // ---- Action buttons visibility based on status ----

  it('shows correct action buttons for "new" status', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // "Mark as Contacted" should be visible (appears in header and quick actions)
    expect(screen.getByTestId('mark-contacted-btn')).toBeInTheDocument();
    // "Mark as Lost" should be visible
    expect(screen.getByTestId('mark-lost-btn')).toBeInTheDocument();
    // "Mark as Spam" should be visible
    expect(screen.getByTestId('mark-spam-btn')).toBeInTheDocument();
    // "Convert to Customer" should NOT be visible (only for qualified)
    expect(screen.queryByTestId('convert-lead-btn')).not.toBeInTheDocument();
    // Delete should always be visible
    expect(screen.getByTestId('delete-lead-btn')).toBeInTheDocument();
  });

  it('shows correct action buttons for "contacted" status', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(contactedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-002') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // "Mark as Contacted" should NOT be visible (already contacted)
    expect(screen.queryByTestId('mark-contacted-btn')).not.toBeInTheDocument();
    // "Mark as Lost" should be visible
    expect(screen.getByTestId('mark-lost-btn')).toBeInTheDocument();
    // "Mark as Spam" should be visible
    expect(screen.getByTestId('mark-spam-btn')).toBeInTheDocument();
    // "Convert to Customer" should NOT be visible (only for qualified)
    expect(screen.queryByTestId('convert-lead-btn')).not.toBeInTheDocument();
  });

  it('shows Convert button for "qualified" status', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(qualifiedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-004') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // "Convert to Customer" should be visible for qualified leads
    expect(screen.getByTestId('convert-lead-btn')).toBeInTheDocument();
    // "Mark as Contacted" should NOT be visible (not new)
    expect(screen.queryByTestId('mark-contacted-btn')).not.toBeInTheDocument();
    // "Mark as Lost" should be visible
    expect(screen.getByTestId('mark-lost-btn')).toBeInTheDocument();
  });

  it('hides quick actions card for "converted" status (terminal)', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(convertedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-003') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // No quick action buttons for terminal state
    expect(screen.queryByTestId('mark-contacted-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('convert-lead-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('mark-lost-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('mark-spam-btn')).not.toBeInTheDocument();
  });

  // ---- Converted lead shows customer/job links ----

  it('shows customer and job links for converted lead', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(convertedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-003') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // Customer link should be visible
    expect(screen.getByTestId('customer-link')).toBeInTheDocument();
    expect(screen.getByText('View Customer')).toBeInTheDocument();

    // Job link should be visible
    expect(screen.getByTestId('job-link')).toBeInTheDocument();
    expect(screen.getByText('View Jobs')).toBeInTheDocument();
  });

  it('does not show conversion links for non-converted lead', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('customer-link')).not.toBeInTheDocument();
    expect(screen.queryByTestId('job-link')).not.toBeInTheDocument();
  });

  // ---- Staff assignment selector ----

  it('renders staff assignment selector', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.getByTestId('lead-staff-select')).toBeInTheDocument();
  });

  // ---- Contacted timestamp display ----

  it('shows contacted_at timestamp when lead has been contacted', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(contactedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-002') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // Contacted timestamp label (use getAllByText since "Contacted" also appears in status badge)
    expect(screen.getAllByText('Contacted').length).toBeGreaterThanOrEqual(2);
  });

  it('shows converted_at timestamp for converted lead', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(convertedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-003') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // Converted timestamp label (use getAllByText since "Converted" also appears in status badge)
    expect(screen.getAllByText('Converted').length).toBeGreaterThanOrEqual(2);
  });
});
