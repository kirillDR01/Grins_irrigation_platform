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
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
  customer_name: 'Jane Doe',
  customer_phone: '+19527373312',
  property_address: '123 Elm St',
};

const mockDocument = {
  id: 'doc-001',
  customer_id: 'cust-001',
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
    mutateAsync: vi.fn(),
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
  useOverrideSalesStatus: () => ({ mutateAsync: vi.fn(), isPending: false }),
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
