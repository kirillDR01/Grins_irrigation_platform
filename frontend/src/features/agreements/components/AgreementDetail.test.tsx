import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AgreementDetail } from './AgreementDetail';
import * as agreementHooks from '../hooks/useAgreements';
import * as mutationHooks from '../hooks/useAgreementMutations';
import type {
  AgreementDetail as AgreementDetailType,
  AgreementJobSummary,
  AgreementStatusLog,
  DisclosureRecord,
} from '../types';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock('../hooks/useAgreements', () => ({
  useAgreement: vi.fn(),
  useAgreementCompliance: vi.fn(),
  agreementKeys: {
    all: ['agreements'],
    lists: () => ['agreements', 'list'],
    list: (p: unknown) => ['agreements', 'list', p],
    details: () => ['agreements', 'detail'],
    detail: (id: string) => ['agreements', 'detail', id],
    metrics: () => ['agreements', 'metrics'],
    renewalPipeline: () => ['agreements', 'renewal-pipeline'],
    failedPayments: () => ['agreements', 'failed-payments'],
    compliance: (id: string) => ['agreements', 'compliance', id],
  },
}));

vi.mock('../hooks/useAgreementMutations', () => ({
  useUpdateAgreementStatus: vi.fn(),
  useApproveRenewal: vi.fn(),
  useRejectRenewal: vi.fn(),
  useUpdateNotes: vi.fn(),
}));

vi.mock('@/core/config', () => ({
  config: { stripeCustomerPortalUrl: 'https://billing.stripe.com/test-portal' },
}));

// Sonner toast mock
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// ---------------------------------------------------------------------------
// Factories
// ---------------------------------------------------------------------------

const makeJob = (overrides: Partial<AgreementJobSummary> = {}): AgreementJobSummary => ({
  id: 'j1',
  job_type: 'Spring Startup',
  status: 'to_be_scheduled',
  target_start_date: '2026-04-01',
  target_end_date: '2026-04-30',
  ...overrides,
});

const makeLog = (overrides: Partial<AgreementStatusLog> = {}): AgreementStatusLog => ({
  id: 'l1',
  old_status: null,
  new_status: 'pending',
  changed_by: null,
  changed_by_name: null,
  reason: null,
  metadata: null,
  created_at: '2026-03-01T00:00:00Z',
  ...overrides,
});

const makeDisclosure = (overrides: Partial<DisclosureRecord> = {}): DisclosureRecord => ({
  id: 'd1',
  agreement_id: 'a1',
  customer_id: 'c1',
  disclosure_type: 'PRE_SALE',
  sent_at: '2026-03-01T00:00:00Z',
  sent_via: 'email',
  recipient_email: 'test@example.com',
  recipient_phone: null,
  delivery_confirmed: true,
  created_at: '2026-03-01T00:00:00Z',
  ...overrides,
});

const makeAgreement = (overrides: Partial<AgreementDetailType> = {}): AgreementDetailType => ({
  id: 'a1',
  agreement_number: 'AGR-2026-001',
  customer_id: 'c1',
  customer_name: 'John Doe',
  tier_id: 't1',
  tier_name: 'Professional',
  package_type: 'residential',
  property_id: 'p1',
  status: 'active',
  annual_price: 599,
  start_date: '2026-03-01',
  end_date: '2027-03-01',
  renewal_date: '2027-03-01',
  auto_renew: true,
  payment_status: 'current',
  created_at: '2026-03-01T00:00:00Z',
  stripe_subscription_id: 'sub_123',
  stripe_customer_id: 'cus_123',
  cancelled_at: null,
  cancellation_reason: null,
  cancellation_refund_amount: null,
  pause_reason: null,
  last_payment_date: '2026-03-01',
  last_payment_amount: 599,
  renewal_approved_by: null,
  renewal_approved_at: null,
  consent_recorded_at: '2026-03-01T00:00:00Z',
  consent_method: 'checkout',
  last_annual_notice_sent: null,
  last_renewal_notice_sent: null,
  notes: null,
  jobs: [
    makeJob(),
    makeJob({ id: 'j2', job_type: 'Fall Winterization', status: 'completed', target_start_date: '2026-10-01', target_end_date: '2026-10-31' }),
  ],
  status_logs: [
    makeLog(),
    makeLog({ id: 'l2', old_status: 'pending', new_status: 'active', created_at: '2026-03-02T00:00:00Z' }),
  ],
  ...overrides,
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mutateAsync = vi.fn().mockResolvedValue({});

function setupMutationMocks() {
  vi.mocked(mutationHooks.useUpdateAgreementStatus).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof mutationHooks.useUpdateAgreementStatus>);
  vi.mocked(mutationHooks.useApproveRenewal).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof mutationHooks.useApproveRenewal>);
  vi.mocked(mutationHooks.useRejectRenewal).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof mutationHooks.useRejectRenewal>);
  vi.mocked(mutationHooks.useUpdateNotes).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as unknown as ReturnType<typeof mutationHooks.useUpdateNotes>);
}

function setupHooks(agreement: AgreementDetailType | undefined, compliance: DisclosureRecord[] | undefined, opts?: { isLoading?: boolean; error?: Error | null }) {
  vi.mocked(agreementHooks.useAgreement).mockReturnValue({
    data: agreement,
    isLoading: opts?.isLoading ?? false,
    error: opts?.error ?? null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof agreementHooks.useAgreement>);
  vi.mocked(agreementHooks.useAgreementCompliance).mockReturnValue({
    data: compliance,
  } as unknown as ReturnType<typeof agreementHooks.useAgreementCompliance>);
  setupMutationMocks();
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AgreementDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mutateAsync.mockResolvedValue({});
  });

  // ---- Loading / Error / Empty states ----

  it('renders loading state', () => {
    setupHooks(undefined, undefined, { isLoading: true });
    render(<AgreementDetail agreementId="a1" />, { wrapper });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    setupHooks(undefined, undefined, { error: new Error('Network error') });
    render(<AgreementDetail agreementId="a1" />, { wrapper });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });

  it('renders not-found when agreement is undefined after loading', () => {
    setupHooks(undefined, undefined);
    render(<AgreementDetail agreementId="a1" />, { wrapper });
    expect(screen.getByTestId('error-message')).toBeInTheDocument();
  });

  // ---- Info display ----

  it('renders agreement info section', async () => {
    const agreement = makeAgreement();
    setupHooks(agreement, []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-detail')).toBeInTheDocument();
    });
    expect(screen.getByTestId('agreement-title')).toHaveTextContent('AGR-2026-001');
    expect(screen.getByTestId('agreement-info')).toBeInTheDocument();
    expect(screen.getByTestId('agreement-status-badge')).toBeInTheDocument();
    expect(screen.getByText('Professional')).toBeInTheDocument();
    expect(screen.getByText('$599.00')).toBeInTheDocument();
    expect(screen.getByText('Yes')).toBeInTheDocument(); // auto_renew
  });

  it('renders customer link', async () => {
    setupHooks(makeAgreement(), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-customer-link')).toBeInTheDocument();
    });
    expect(screen.getByTestId('agreement-customer-link')).toHaveAttribute('href', '/customers/c1');
  });

  // ---- Jobs timeline ----

  it('renders jobs timeline with progress', async () => {
    setupHooks(makeAgreement(), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-jobs-timeline')).toBeInTheDocument();
    });
    expect(screen.getByTestId('jobs-progress')).toHaveTextContent('1 of 2 completed');
    expect(screen.getByTestId('job-row-j1')).toBeInTheDocument();
    expect(screen.getByTestId('job-row-j2')).toBeInTheDocument();
  });

  it('renders empty jobs message when no jobs', async () => {
    setupHooks(makeAgreement({ jobs: [] }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-jobs-timeline')).toBeInTheDocument();
    });
    expect(screen.getByText(/no visits scheduled/i)).toBeInTheDocument();
  });

  // ---- Status log ----

  it('renders status log entries', async () => {
    setupHooks(makeAgreement(), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-status-log')).toBeInTheDocument();
    });
    expect(screen.getByTestId('status-log-l1')).toBeInTheDocument();
    expect(screen.getByTestId('status-log-l2')).toBeInTheDocument();
  });

  // ---- Compliance log ----

  it('renders compliance log with disclosure records', async () => {
    const disclosures = [
      makeDisclosure(),
      makeDisclosure({ id: 'd2', disclosure_type: 'CONFIRMATION', sent_at: '2026-03-02T00:00:00Z' }),
    ];
    setupHooks(makeAgreement(), disclosures);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-compliance-log')).toBeInTheDocument();
    });
    expect(screen.getByTestId('compliance-status-summary')).toBeInTheDocument();
    expect(screen.getByTestId('disclosure-d1')).toBeInTheDocument();
    expect(screen.getByTestId('disclosure-d2')).toBeInTheDocument();
  });

  it('shows overdue warning for active agreement missing annual notice', async () => {
    setupHooks(makeAgreement({ status: 'active', last_annual_notice_sent: null }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('compliance-overdue-warning')).toBeInTheDocument();
    });
  });

  it('shows compliance indicators for present and missing types', async () => {
    const disclosures = [makeDisclosure({ disclosure_type: 'PRE_SALE' })];
    setupHooks(makeAgreement(), disclosures);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('compliance-PRE_SALE')).toHaveTextContent('✓');
    });
    // CONFIRMATION is missing and required
    expect(screen.getByTestId('compliance-CONFIRMATION')).toHaveTextContent('✗');
  });

  // ---- Admin notes ----

  it('renders admin notes section', async () => {
    setupHooks(makeAgreement({ notes: 'Test note' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-admin-notes')).toBeInTheDocument();
    });
    expect(screen.getByTestId('admin-notes-input')).toHaveValue('Test note');
  });

  it('shows save button only when notes are dirty', async () => {
    const user = userEvent.setup();
    setupHooks(makeAgreement(), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('admin-notes-input')).toBeInTheDocument();
    });
    // Save button should not be visible initially
    expect(screen.queryByTestId('save-notes-btn')).not.toBeInTheDocument();

    await user.type(screen.getByTestId('admin-notes-input'), 'New note');
    expect(screen.getByTestId('save-notes-btn')).toBeInTheDocument();
  });

  // ---- Action buttons per status ----

  it('shows Pause and Cancel buttons for ACTIVE agreement', async () => {
    setupHooks(makeAgreement({ status: 'active' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-actions')).toBeInTheDocument();
    });
    expect(screen.getByTestId('pause-agreement-btn')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-agreement-btn')).toBeInTheDocument();
  });

  it('shows Resume and Cancel buttons for PAUSED agreement', async () => {
    setupHooks(makeAgreement({ status: 'paused' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-actions')).toBeInTheDocument();
    });
    expect(screen.getByTestId('resume-agreement-btn')).toBeInTheDocument();
    expect(screen.getByTestId('cancel-agreement-btn')).toBeInTheDocument();
  });

  it('shows Approve and Reject buttons for PENDING_RENEWAL agreement', async () => {
    setupHooks(makeAgreement({ status: 'pending_renewal' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-actions')).toBeInTheDocument();
    });
    expect(screen.getByTestId('approve-renewal-btn')).toBeInTheDocument();
    expect(screen.getByTestId('reject-renewal-btn')).toBeInTheDocument();
  });

  it('shows no action buttons for PENDING status', async () => {
    setupHooks(makeAgreement({ status: 'pending' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-detail')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('agreement-actions')).not.toBeInTheDocument();
  });

  it('shows no action buttons for CANCELLED status', async () => {
    setupHooks(makeAgreement({ status: 'cancelled' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-detail')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('agreement-actions')).not.toBeInTheDocument();
  });

  it('shows no action buttons for EXPIRED status', async () => {
    setupHooks(makeAgreement({ status: 'expired' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-detail')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('agreement-actions')).not.toBeInTheDocument();
  });

  // ---- Cancel dialog requires reason ----

  it('cancel dialog requires reason before confirming', async () => {
    const user = userEvent.setup();
    setupHooks(makeAgreement({ status: 'active' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('cancel-agreement-btn')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('cancel-agreement-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('cancel-dialog')).toBeInTheDocument();
    });
    // Confirm button should be disabled without reason
    expect(screen.getByTestId('cancel-dialog-confirm')).toBeDisabled();

    await user.type(screen.getByTestId('cancel-reason-input'), 'Customer requested');
    expect(screen.getByTestId('cancel-dialog-confirm')).toBeEnabled();
  });

  it('submitting cancel dialog calls updateStatus with reason', async () => {
    const user = userEvent.setup();
    setupHooks(makeAgreement({ status: 'active' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await user.click(screen.getByTestId('cancel-agreement-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('cancel-dialog')).toBeInTheDocument();
    });
    await user.type(screen.getByTestId('cancel-reason-input'), 'Customer requested');
    await user.click(screen.getByTestId('cancel-dialog-confirm'));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        id: 'a1',
        data: { status: 'cancelled', reason: 'Customer requested' },
      });
    });
  });

  // ---- External links ----

  it('renders Stripe dashboard link when subscription id present', async () => {
    setupHooks(makeAgreement({ stripe_subscription_id: 'sub_abc' }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('stripe-dashboard-link')).toBeInTheDocument();
    });
    expect(screen.getByTestId('stripe-dashboard-link')).toHaveAttribute(
      'href',
      'https://dashboard.stripe.com/subscriptions/sub_abc',
    );
  });

  it('does not render Stripe link when subscription id is null', async () => {
    setupHooks(makeAgreement({ stripe_subscription_id: null }), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('agreement-detail')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('stripe-dashboard-link')).not.toBeInTheDocument();
  });

  it('renders customer portal link', async () => {
    setupHooks(makeAgreement(), []);
    render(<AgreementDetail agreementId="a1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('customer-portal-link')).toBeInTheDocument();
    });
    expect(screen.getByTestId('customer-portal-link')).toHaveAttribute(
      'href',
      'https://billing.stripe.com/test-portal',
    );
  });
});
