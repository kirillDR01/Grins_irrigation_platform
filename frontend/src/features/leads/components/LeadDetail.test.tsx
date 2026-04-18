import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { LeadDetail } from './LeadDetail';
import { leadApi } from '../api/leadApi';
import { staffApi } from '@/features/staff/api/staffApi';
import type { Lead, LeadMoveResponse, DuplicateConflictError } from '../types';

// Mock the lead API
vi.mock('../api/leadApi', () => ({
  leadApi: {
    getById: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    convert: vi.fn(),
    list: vi.fn(),
    listAttachments: vi.fn(),
    listEstimateTemplates: vi.fn(),
    listContractTemplates: vi.fn(),
    moveToJobs: vi.fn(),
    moveToSales: vi.fn(),
    markContacted: vi.fn(),
  },
}));

// Mock sonner toast so assertions stay noise-free
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
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
  address: '123 Main St',
  city: 'Minneapolis',
  state: 'MN',
  zip_code: '55424',
  situation: 'new_system',
  notes: 'Large backyard needs full irrigation',
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
    vi.mocked(leadApi.listAttachments).mockResolvedValue([]);
    vi.mocked(leadApi.listEstimateTemplates).mockResolvedValue([]);
    vi.mocked(leadApi.listContractTemplates).mockResolvedValue([]);
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
    // Address
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText(/Minneapolis, MN 55424/)).toBeInTheDocument();
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

    // H-1: Mark Contacted, Move to Jobs, Move to Sales, Delete all visible in header
    expect(screen.getByTestId('lead-detail-mark-contacted-btn')).toBeInTheDocument();
    expect(screen.getByTestId('lead-detail-move-to-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('lead-detail-move-to-sales-btn')).toBeInTheDocument();
    // "Mark as Lost" should be visible
    expect(screen.getByTestId('mark-lost-btn')).toBeInTheDocument();
    // "Mark as Spam" should be visible
    expect(screen.getByTestId('mark-spam-btn')).toBeInTheDocument();
    // "Convert to Customer" should NOT be visible (only for qualified)
    expect(screen.queryByTestId('convert-lead-btn')).not.toBeInTheDocument();
    // Delete should always be visible
    expect(screen.getByTestId('lead-detail-delete-btn')).toBeInTheDocument();
  });

  it('shows correct action buttons for "contacted" status', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(contactedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-002') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // H-1 / L-3: Mark Contacted remains visible on contacted so admin can re-stamp
    expect(screen.getByTestId('lead-detail-mark-contacted-btn')).toBeInTheDocument();
    // Routing actions still visible on contacted
    expect(screen.getByTestId('lead-detail-move-to-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('lead-detail-move-to-sales-btn')).toBeInTheDocument();
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
    // H-1 / L-3: Mark Contacted stays visible on qualified too
    expect(screen.getByTestId('lead-detail-mark-contacted-btn')).toBeInTheDocument();
    // "Mark as Lost" should be visible
    expect(screen.getByTestId('mark-lost-btn')).toBeInTheDocument();
  });

  it('hides quick actions card for "converted" status (terminal)', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(convertedLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-003') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    // No header routing action or quick-actions buttons for terminal state
    expect(screen.queryByTestId('lead-detail-mark-contacted-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lead-detail-move-to-jobs-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('lead-detail-move-to-sales-btn')).not.toBeInTheDocument();
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

    // Contacted timestamp label and status badge (badge now says "Contacted (Awaiting Response)")
    expect(screen.getByText('Contacted (Awaiting Response)')).toBeInTheDocument();
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

  // ---- Source detail display ----

  it('renders source_detail when present', async () => {
    const leadWithSourceDetail: Lead = {
      ...baseLead,
      source_detail: 'Google Ads Spring Campaign',
    };
    vi.mocked(leadApi.getById).mockResolvedValue(leadWithSourceDetail);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.getByText('Source Detail')).toBeInTheDocument();
    expect(screen.getByText('Google Ads Spring Campaign')).toBeInTheDocument();
  });

  it('does not render source_detail section when null', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead); // source_detail is null

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.queryByText('Source Detail')).not.toBeInTheDocument();
  });

  // ---- Lead source badge on detail ----

  it('renders lead source badge on detail view', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.getByTestId('lead-source-website')).toBeInTheDocument();
  });

  // ---- Intake tag badge on detail ----

  it('renders intake tag badge on detail view', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead); // intake_tag='schedule'

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    expect(screen.getByTestId('intake-tag-schedule')).toBeInTheDocument();
  });

  // ---- Consent indicators on detail ----

  it('renders consent indicators as "Given"/"Opted in" when true', async () => {
    vi.mocked(leadApi.getById).mockResolvedValue(baseLead); // sms_consent=true, email_marketing_consent=true

    render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    const smsConsent = screen.getByTestId('sms-consent-lead-001');
    expect(smsConsent).toHaveTextContent('Given');

    const emailMarketing = screen.getByTestId('email-marketing-consent-lead-001');
    expect(emailMarketing).toHaveTextContent('Opted in');

    const termsAccepted = screen.getByTestId('terms-accepted-lead-001');
    expect(termsAccepted).toHaveTextContent('Accepted');
  });

  it('renders consent indicators as "Not given"/"Not accepted" when false', async () => {
    const leadNoConsent: Lead = {
      ...baseLead,
      id: 'lead-no-consent',
      sms_consent: false,
      terms_accepted: false,
      email_marketing_consent: false,
    };
    vi.mocked(leadApi.getById).mockResolvedValue(leadNoConsent);

    render(<LeadDetail />, { wrapper: createWrapper('lead-no-consent') });

    await waitFor(() => {
      expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
    });

    const smsConsent = screen.getByTestId('sms-consent-lead-no-consent');
    expect(smsConsent).toHaveTextContent('Not given');

    const emailMarketing = screen.getByTestId('email-marketing-consent-lead-no-consent');
    expect(emailMarketing).toHaveTextContent('Not opted in');

    const termsAccepted = screen.getByTestId('terms-accepted-lead-no-consent');
    expect(termsAccepted).toHaveTextContent('Not accepted');
  });

  // ---- Lead Deletion Flow (Req 5) ----

  describe('Lead Deletion', () => {
    it('opens confirmation dialog when delete button is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Click the delete button
      await user.click(screen.getByTestId('lead-detail-delete-btn'));

      // Confirmation dialog should appear
      await waitFor(() => {
        expect(screen.getByTestId('delete-confirmation-dialog')).toBeInTheDocument();
      });
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
      expect(screen.getAllByText('John Doe').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId('confirm-delete-btn')).toBeInTheDocument();
      expect(screen.getByTestId('cancel-delete-btn')).toBeInTheDocument();
    });

    it('closes confirmation dialog when cancel is clicked', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Open dialog
      await user.click(screen.getByTestId('lead-detail-delete-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('delete-confirmation-dialog')).toBeInTheDocument();
      });

      // Click cancel
      await user.click(screen.getByTestId('cancel-delete-btn'));

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByTestId('delete-confirmation-dialog')).not.toBeInTheDocument();
      });

      // Should NOT have called the delete API
      expect(leadApi.delete).not.toHaveBeenCalled();
    });

    it('deletes lead and navigates to /leads on success', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.delete).mockResolvedValue(undefined);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Open dialog and confirm
      await user.click(screen.getByTestId('lead-detail-delete-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('delete-confirmation-dialog')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('confirm-delete-btn'));

      // Should call delete API
      await waitFor(() => {
        expect(leadApi.delete).toHaveBeenCalledWith('lead-001');
      });

      // Should navigate to leads list
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/leads');
      });
    });

    it('shows error toast when deletion fails', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.delete).mockRejectedValue(new Error('Network Error'));

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Open dialog and confirm
      await user.click(screen.getByTestId('lead-detail-delete-btn'));
      await waitFor(() => {
        expect(screen.getByTestId('delete-confirmation-dialog')).toBeInTheDocument();
      });
      await user.click(screen.getByTestId('confirm-delete-btn'));

      // Should call delete API
      await waitFor(() => {
        expect(leadApi.delete).toHaveBeenCalledWith('lead-001');
      });

      // Should NOT navigate (deletion failed)
      expect(mockNavigate).not.toHaveBeenCalledWith('/leads');
    });
  });

  // ---- April 16th: Only 4 action buttons render ----

  describe('April 16th: Action button cleanup', () => {
    it('renders only 4 action buttons for a new lead (Mark Contacted, Move to Jobs, Move to Sales, Delete)', async () => {
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // These 4 should be present
      expect(screen.getByTestId('lead-detail-mark-contacted-btn')).toBeInTheDocument();
      expect(screen.getByTestId('lead-detail-move-to-jobs-btn')).toBeInTheDocument();
      expect(screen.getByTestId('lead-detail-move-to-sales-btn')).toBeInTheDocument();
      expect(screen.getByTestId('lead-detail-delete-btn')).toBeInTheDocument();
    });

    it('status dropdown has 2 options for non-terminal leads', async () => {
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Status dropdown should be present
      expect(screen.getByTestId('lead-status-dropdown')).toBeInTheDocument();
    });

    it('legacy statuses show "Archived" badge', async () => {
      // Test with qualified (legacy) status
      vi.mocked(leadApi.getById).mockResolvedValue(qualifiedLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-004') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      // Should show "Archived" text for legacy status
      expect(screen.getByText('Archived')).toBeInTheDocument();
    });
  });

  // ---- H-1: Routing action buttons ----

  describe('Routing actions (H-1)', () => {
    const successMoveResponse: LeadMoveResponse = {
      success: true,
      lead_id: 'lead-001',
      customer_id: 'cust-1',
      job_id: 'job-1',
      sales_entry_id: null,
      message: 'Moved to Jobs',
      requires_estimate_warning: false,
      merged_into_customer: null,
    };

    const requiresEstimateMoveResponse: LeadMoveResponse = {
      ...successMoveResponse,
      requires_estimate_warning: true,
    };

    function buildDuplicate409(): AxiosError {
      const detail: DuplicateConflictError = {
        error: 'duplicate_found',
        lead_id: 'lead-001',
        phone: '6125551234',
        email: 'john@example.com',
        duplicates: [
          {
            id: 'existing-cust-1',
            first_name: 'Existing',
            last_name: 'Customer',
            phone: '6125551234',
            email: 'john@example.com',
          },
        ],
      };
      return new AxiosError(
        'Request failed with status code 409',
        'ERR_BAD_REQUEST',
        undefined,
        undefined,
        {
          status: 409,
          data: { detail },
          headers: {},
          statusText: 'Conflict',
          config: {} as InternalAxiosRequestConfig,
        } as AxiosResponse,
      );
    }

    it('renders all four routing action buttons for a routable lead', async () => {
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      expect(
        screen.getByTestId('lead-detail-mark-contacted-btn'),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId('lead-detail-move-to-jobs-btn'),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId('lead-detail-move-to-sales-btn'),
      ).toBeInTheDocument();
      expect(screen.getByTestId('lead-detail-delete-btn')).toBeInTheDocument();
    });

    it('fires useMoveToJobs on click and navigates to /jobs', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.moveToJobs).mockResolvedValue(successMoveResponse);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('lead-detail-move-to-jobs-btn'));

      await waitFor(() => {
        expect(leadApi.moveToJobs).toHaveBeenCalledWith('lead-001', false);
      });
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/jobs');
      });
    });

    it('fires useMoveToSales on click and navigates to /sales', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.moveToSales).mockResolvedValue(successMoveResponse);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('lead-detail-move-to-sales-btn'));

      await waitFor(() => {
        expect(leadApi.moveToSales).toHaveBeenCalledWith('lead-001');
      });
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/sales');
      });
    });

    it('opens requires-estimate modal when move returns requires_estimate_warning', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.moveToJobs).mockResolvedValue(
        requiresEstimateMoveResponse,
      );

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('lead-detail-move-to-jobs-btn'));

      await waitFor(() => {
        expect(
          screen.getByTestId('lead-detail-requires-estimate-modal'),
        ).toBeInTheDocument();
      });
    });

    it('opens conflict modal when move returns 409', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.moveToJobs).mockRejectedValue(buildDuplicate409());

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('lead-detail-move-to-jobs-btn'));

      await waitFor(() => {
        expect(
          screen.getByTestId('lead-conversion-conflict-modal'),
        ).toBeInTheDocument();
      });
    });

    it('retries with force=true on Convert anyway', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.moveToJobs)
        .mockRejectedValueOnce(buildDuplicate409())
        .mockResolvedValueOnce(successMoveResponse);

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('lead-detail-move-to-jobs-btn'));

      await waitFor(() => {
        expect(
          screen.getByTestId('lead-conversion-conflict-modal'),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('convert-anyway-btn'));

      await waitFor(() => {
        expect(leadApi.moveToJobs).toHaveBeenCalledTimes(2);
      });
      expect(leadApi.moveToJobs).toHaveBeenNthCalledWith(2, 'lead-001', true);
    });

    it('fires useMarkContacted on header Mark Contacted click', async () => {
      const user = userEvent.setup();
      vi.mocked(leadApi.getById).mockResolvedValue(baseLead);
      vi.mocked(leadApi.markContacted).mockResolvedValue({
        ...baseLead,
        status: 'contacted',
      });

      render(<LeadDetail />, { wrapper: createWrapper('lead-001') });

      await waitFor(() => {
        expect(screen.getByTestId('lead-detail')).toBeInTheDocument();
      });

      await user.click(
        screen.getByTestId('lead-detail-mark-contacted-btn'),
      );

      await waitFor(() => {
        expect(leadApi.markContacted).toHaveBeenCalledWith('lead-001');
      });
    });
  });
});
