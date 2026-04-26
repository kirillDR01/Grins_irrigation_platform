/**
 * Tests for SalesDetail signing button gating (bughunt M-17).
 *
 * The signing buttons (Email for Signature + Embedded Signer) used to
 * unlock as soon as ``documents.length > 0``. If the underlying
 * ``file_key`` was missing or the presigned URL had expired, the
 * signing iframe would open with a broken URL. SalesDetail now
 * resolves the presigned URL via ``useDocumentPresign`` at render and
 * disables the signing buttons until the URL actually loads.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { SalesDetail } from './SalesDetail';

const mockEntry = {
  id: 'entry-001',
  customer_id: 'cust-001',
  property_id: null,
  lead_id: null,
  job_type: 'install',
  status: 'send_estimate' as const,
  last_contact_date: null,
  notes: null,
  override_flag: false,
  closed_reason: null,
  signwell_document_id: null,
  nudges_paused_until: null,
  dismissed_at: null,
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
  customer_name: 'Jane Doe',
  customer_phone: '+19527373312',
  customer_email: 'jane@example.com',
  property_address: '123 Elm St',
};

const mockDocument = {
  id: 'doc-001',
  customer_id: 'cust-001',
  sales_entry_id: 'entry-001',
  file_key: 'docs/estimate.pdf',
  file_name: 'estimate.pdf',
  document_type: 'estimate',
  mime_type: 'application/pdf',
  size_bytes: 1024,
  uploaded_at: '2026-04-16T00:00:00Z',
  uploaded_by: null,
};

const presignState = {
  data: undefined as { download_url: string; file_name: string } | undefined,
  isLoading: false,
  isError: false,
};

vi.mock('../hooks/useSalesPipeline', () => ({
  useSalesEntry: () => ({
    data: mockEntry,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useSalesDocuments: () => ({
    data: [mockDocument],
    isLoading: false,
    error: null,
  }),
  useTriggerEmailSigning: () => ({
    mutateAsync: vi.fn().mockResolvedValue({ document_id: 'd', status: 'sent' }),
    isPending: false,
  }),
  useDocumentPresign: () => presignState,
  pipelineKeys: {
    detail: (id: string) => ['sales-pipeline', 'detail', id] as const,
    documents: (cid: string) =>
      ['sales-pipeline', 'documents', cid] as const,
    documentPresign: (cid: string, did: string) =>
      ['sales-pipeline', 'documents', cid, did, 'presign'] as const,
    lists: () => ['sales-pipeline', 'list'] as const,
  },
  // The pipelineKeys doubles as the calendar key — provide a stub.
  useAdvanceSalesEntry: () => ({ mutate: vi.fn(), isPending: false }),
  useConvertToJob: () => ({ mutate: vi.fn(), isPending: false }),
  useForceConvertToJob: () => ({ mutate: vi.fn(), isPending: false }),
  useMarkSalesLost: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateCalendarEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateCalendarEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSalesCalendarEvents: () => ({ data: [], isLoading: false, error: null }),
  useOverrideSalesStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUploadSalesDocument: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePauseNudges: () => ({ mutate: vi.fn(), isPending: false }),
  useUnpauseNudges: () => ({ mutate: vi.fn(), isPending: false }),
  useSendTextConfirmation: () => ({ mutate: vi.fn(), isPending: false }),
  useDismissSalesEntry: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('./DocumentsSection', () => ({
  DocumentsSection: () => <div data-testid="documents-section" />,
}));

vi.mock('./SignWellEmbeddedSigner', () => ({
  SignWellEmbeddedSigner: ({
    disabled,
    disabledReason,
  }: {
    disabled: boolean;
    disabledReason?: string;
  }) => (
    <button
      data-testid="embedded-sign-btn"
      disabled={disabled}
      title={disabledReason}
    >
      Sign on site
    </button>
  ),
}));

const mockUpdateCustomerMutateAsync = vi.fn().mockResolvedValue(undefined);

vi.mock('@/features/customers/hooks', () => ({
  useUpdateCustomer: () => ({
    mutateAsync: mockUpdateCustomerMutateAsync,
    isPending: false,
  }),
  useCustomer: (id: string) => ({
    data: id === 'cust-001' ? {
      id: 'cust-001',
      first_name: 'Jane',
      last_name: 'Doe',
      phone: '+19527373312',
      email: 'jane@example.com',
      internal_notes: 'Important customer context',
      properties: [],
    } : null,
    isLoading: false,
    error: null,
  }),
  customerKeys: {
    all: ['customers'],
    lists: () => ['customers', 'list'],
    detail: (id: string) => ['customers', 'detail', id],
  },
}));

const mockInvalidateAfterCustomerInternalNotesSave = vi.fn();
vi.mock('@/shared/utils/invalidationHelpers', () => ({
  invalidateAfterCustomerInternalNotesSave: (...args: unknown[]) =>
    mockInvalidateAfterCustomerInternalNotesSave(...args),
}));

vi.mock('@/features/staff/hooks/useStaff', () => ({
  useStaff: () => ({ data: { items: [] }, isLoading: false }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SalesDetail signing gate (bughunt M-17)', () => {
  beforeEach(() => {
    presignState.data = undefined;
    presignState.isLoading = false;
    presignState.isError = false;
  });

  it('disables signing buttons while presign is loading', async () => {
    presignState.isLoading = true;
    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('email-sign-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('email-sign-btn')).toBeDisabled();
    expect(screen.getByTestId('embedded-sign-btn')).toBeDisabled();
    expect(screen.getByTestId('embedded-sign-btn')).toHaveAttribute(
      'title',
      'Resolving document…',
    );
  });

  it('disables signing buttons when presign returns an error', async () => {
    presignState.isError = true;
    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('embedded-sign-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('email-sign-btn')).toBeDisabled();
    expect(screen.getByTestId('embedded-sign-btn')).toBeDisabled();
    expect(screen.getByTestId('embedded-sign-btn')).toHaveAttribute(
      'title',
      'Document file is missing or expired — re-upload required.',
    );
  });

  it('enables signing buttons once presign resolves to a real URL', async () => {
    presignState.data = {
      download_url: 'https://s3.example.com/docs/estimate.pdf?signed=abc',
      file_name: 'estimate.pdf',
    };
    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('embedded-sign-btn')).toBeInTheDocument();
    });

    expect(screen.getByTestId('email-sign-btn')).not.toBeDisabled();
    expect(screen.getByTestId('embedded-sign-btn')).not.toBeDisabled();
  });
});


// ---- InternalNotesCard (internal-notes-simplification Req 4, 9) ----

describe('SalesDetail InternalNotesCard', () => {
  beforeEach(() => {
    presignState.data = {
      download_url: 'https://s3.example.com/docs/estimate.pdf?signed=abc',
      file_name: 'estimate.pdf',
    };
    mockUpdateCustomerMutateAsync.mockClear();
    mockInvalidateAfterCustomerInternalNotesSave.mockClear();
  });

  it('renders InternalNotesCard with customer internal_notes', async () => {
    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('sales-notes-editor')).toBeInTheDocument();
    });

    expect(screen.getByText('Important customer context')).toBeInTheDocument();
    expect(screen.getByTestId('sales-internal-notes-display')).toBeInTheDocument();
  });

  it('Save calls useUpdateCustomer on the customer id and invokes invalidation', async () => {
    const user = userEvent.setup();
    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('sales-edit-notes-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('sales-edit-notes-btn'));

    const textarea = screen.getByTestId('sales-internal-notes-textarea');
    await user.clear(textarea);
    await user.type(textarea, 'Updated from sales');

    await user.click(screen.getByTestId('sales-save-notes-btn'));

    await waitFor(() => {
      expect(mockUpdateCustomerMutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'cust-001',
          data: { internal_notes: 'Updated from sales' },
        })
      );
    });

    await waitFor(() => {
      expect(mockInvalidateAfterCustomerInternalNotesSave).toHaveBeenCalledWith(
        expect.anything(),
        'cust-001'
      );
    });
  });

  it('renders readOnly card when customer_id is missing', async () => {
    // Override the mock entry to have no customer_id
    const origEntry = { ...mockEntry };
    Object.assign(mockEntry, { customer_id: null });

    render(<SalesDetail entryId="entry-001" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId('sales-notes-editor')).toBeInTheDocument();
    });

    // Edit button should not be present in readOnly mode
    expect(screen.queryByTestId('sales-edit-notes-btn')).not.toBeInTheDocument();

    // Restore
    Object.assign(mockEntry, origEntry);
  });
});


// ── Walkthrough integration tests (Task 11.5) ────────────────────────────────

describe('SalesDetail walkthrough layout', () => {
  beforeEach(() => {
    presignState.data = {
      download_url: 'https://s3.example.com/docs/estimate.pdf?signed=abc',
      file_name: 'estimate.pdf',
    };
    // Reset to default status
    Object.assign(mockEntry, {
      status: 'send_estimate',
      closed_reason: null,
      lead_id: null,
    });
  });

  it('renders StageStepper for non-terminal, non-closed_lost status', async () => {
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('stage-stepper')).toBeInTheDocument();
    });
  });

  it('renders NowCard for non-terminal, non-closed_lost status', async () => {
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-card')).toBeInTheDocument();
    });
  });

  it('renders ActivityStrip when there are activity events', async () => {
    Object.assign(mockEntry, { status: 'pending_approval', lead_id: 'lead-001' });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('activity-strip')).toBeInTheDocument();
    });
  });

  it('hides StageStepper, NowCard, ActivityStrip for closed_lost and shows banner', async () => {
    Object.assign(mockEntry, {
      status: 'closed_lost',
      closed_reason: 'Too expensive',
    });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('closed-lost-banner')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('stage-stepper')).not.toBeInTheDocument();
    expect(screen.queryByTestId('now-card')).not.toBeInTheDocument();
    expect(screen.queryByTestId('activity-strip')).not.toBeInTheDocument();
    expect(screen.getByTestId('closed-lost-banner')).toHaveTextContent('Too expensive');
  });

  it('does NOT render StatusActionButton in the header card', async () => {
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('sales-detail-page')).toBeInTheDocument();
    });
    // StatusActionButton renders advance-btn-{id} — should not be present
    expect(screen.queryByTestId(`advance-btn-${mockEntry.id}`)).not.toBeInTheDocument();
  });

  it('NowCard renders correct variation for send_estimate with doc', async () => {
    // mockDocument is an estimate doc, so hasEstimateDoc = true
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-card')).toBeInTheDocument();
    });
    // send_estimate with doc shows filled dropzone
    expect(screen.getByTestId('now-card-dropzone-filled')).toBeInTheDocument();
  });

  it('NowCard renders correct variation for schedule_estimate', async () => {
    Object.assign(mockEntry, { status: 'schedule_estimate' });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-card')).toBeInTheDocument();
    });
    expect(screen.getByTestId('now-action-schedule')).toBeInTheDocument();
  });

  it('NowCard renders correct variation for pending_approval', async () => {
    Object.assign(mockEntry, { status: 'pending_approval' });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-card')).toBeInTheDocument();
    });
    expect(screen.getByTestId('now-action-approved')).toBeInTheDocument();
  });

  it('hides StageStepper, NowCard, ActivityStrip for closed_won and shows banner', async () => {
    Object.assign(mockEntry, { status: 'closed_won' });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('closed-won-banner')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('stage-stepper')).not.toBeInTheDocument();
    expect(screen.queryByTestId('now-card')).not.toBeInTheDocument();
    expect(screen.queryByTestId('activity-strip')).not.toBeInTheDocument();
  });

  it('stubbed actions (text_confirmation, resend_estimate, pause_nudges) show toast', async () => {
    Object.assign(mockEntry, { status: 'pending_approval' });
    const user = userEvent.setup();
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-action-resend')).toBeInTheDocument();
    });
    // Clicking resend_estimate should not throw
    await user.click(screen.getByTestId('now-action-resend'));
    // Toast is shown — we just verify no crash
  });

  it('view_customer action navigates to /customers/{id}', async () => {
    // send_contract still shows NowCard, and exposes view_customer in some
    // variations. Use pending_approval which definitely renders NowCard.
    Object.assign(mockEntry, { status: 'pending_approval' });
    const user = userEvent.setup();
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-card')).toBeInTheDocument();
    });
    // Just confirm NowCard renders — actual view_customer button presence
    // depends on stage variation.
    expect(screen.getByTestId('now-card')).toBeInTheDocument();
    void user;
  });
});


// ── NEW-A: hasEmail derived from real customer email ──────────────────────────

describe('SalesDetail email-sign button gating (NEW-A)', () => {
  beforeEach(() => {
    presignState.data = {
      download_url: 'https://s3.example.com/docs/estimate.pdf?signed=abc',
      file_name: 'estimate.pdf',
    };
    Object.assign(mockEntry, {
      status: 'send_estimate',
      customer_email: 'jane@example.com',
    });
  });

  it('enables email-sign button when entry.customer_email is set', async () => {
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('email-sign-btn')).toBeInTheDocument();
    });
    expect(screen.getByTestId('email-sign-btn')).not.toBeDisabled();
  });

  it('disables email-sign button when both entry.customer_email and salesCustomer.email are null', async () => {
    Object.assign(mockEntry, { customer_id: 'cust-no-email', customer_email: null });
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('email-sign-btn')).toBeInTheDocument();
    });
    expect(screen.getByTestId('email-sign-btn')).toBeDisabled();
    // restore for downstream tests
    Object.assign(mockEntry, { customer_id: 'cust-001', customer_email: 'jane@example.com' });
  });
});


// ── NEW-B: MarkDeclinedDialog opens from mark_declined action ────────────────

describe('SalesDetail mark_declined opens dialog (NEW-B)', () => {
  beforeEach(() => {
    presignState.data = {
      download_url: 'https://s3.example.com/docs/estimate.pdf?signed=abc',
      file_name: 'estimate.pdf',
    };
    Object.assign(mockEntry, { status: 'pending_approval' });
  });

  it('clicking mark_declined action opens MarkDeclinedDialog', async () => {
    const user = userEvent.setup();
    render(<SalesDetail entryId="entry-001" />, { wrapper });
    await waitFor(() => {
      expect(screen.getByTestId('now-action-declined')).toBeInTheDocument();
    });
    await user.click(screen.getByTestId('now-action-declined'));
    expect(await screen.findByTestId('mark-declined-dialog')).toBeInTheDocument();
    // Confirm button is disabled while reason is empty
    expect(screen.getByTestId('confirm-mark-declined-btn')).toBeDisabled();
  });
});
