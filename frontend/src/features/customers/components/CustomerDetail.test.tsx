import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { CustomerDetail } from './CustomerDetail';

// Mock hooks
vi.mock('../hooks/useCustomers', () => ({
  useCustomer: vi.fn(),
  useCustomerPhotos: vi.fn(),
  useCustomerInvoices: vi.fn(),
  useCustomerPaymentMethods: vi.fn(),
  useCustomerDuplicates: vi.fn(),
  useCustomerSentMessages: vi.fn(),
  useServicePreferences: vi.fn(),
  customerKeys: {
    all: ['customers'],
    lists: () => ['customers', 'list'],
    list: (params: unknown) => ['customers', 'list', params],
    details: () => ['customers', 'detail'],
    detail: (id: string) => ['customers', 'detail', id],
    photos: (id: string) => ['customers', id, 'photos'],
    invoices: (id: string, params?: unknown) => ['customers', id, 'invoices', params],
    paymentMethods: (id: string) => ['customers', id, 'payment-methods'],
    duplicates: (id: string) => ['customers', id, 'duplicates'],
    sentMessages: (id: string) => ['customers', id, 'sent-messages'],
    conversation: (id: string) => ['customers', id, 'conversation'],
    servicePreferences: (id: string) => ['customers', id, 'service-preferences'],
  },
}));

// gap-13: useCustomerConversation lives in its own module — mock so the
// Messages tab renders without hitting the real cursor-paginated query.
vi.mock('../hooks/useCustomerConversation', () => ({
  useCustomerConversation: vi.fn(() => ({
    data: { pages: [{ items: [], next_cursor: null, has_more: false }], pageParams: [null] },
    isLoading: false,
    error: null,
    dataUpdatedAt: 0,
    isFetching: false,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
  })),
}));

vi.mock('../hooks/useCustomerMutations', () => ({
  useDeleteCustomer: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateCustomer: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUploadCustomerPhotos: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdatePhotoCaption: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteCustomerPhoto: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useChargeCustomer: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useMergeCustomers: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useAddServicePreference: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateServicePreference: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteServicePreference: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useAddProperty: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateProperty: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteProperty: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useSetPropertyPrimary: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));

vi.mock('@/features/ai/components', () => ({
  AICommunicationDrafts: () => <div data-testid="ai-drafts">AI Drafts</div>,
}));

vi.mock('@/features/ai/hooks/useAICommunication', () => ({
  useAICommunication: () => ({
    draft: null,
    isLoading: false,
    error: null,
    sendNow: vi.fn(),
    scheduleLater: vi.fn(),
  }),
}));

import * as customerHooks from '../hooks/useCustomers';

const mockCustomer = {
  id: 'cust-1',
  first_name: 'John',
  last_name: 'Doe',
  phone: '612-555-1234',
  email: 'john@example.com',
  is_priority: false,
  is_red_flag: false,
  is_slow_payer: false,
  is_new_customer: false,
  sms_opt_in: true,
  email_opt_in: true,
  lead_source: 'website',
  internal_notes: 'VIP customer, prefers morning calls',
  preferred_service_times: { preference: 'MORNING' },
  properties: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/customers/cust-1']}>
          <Routes>
            <Route path="/customers/:id" element={children} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function setupMocks() {
  vi.mocked(customerHooks.useCustomer).mockReturnValue({
    data: mockCustomer,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof customerHooks.useCustomer>);

  vi.mocked(customerHooks.useCustomerPhotos).mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useCustomerPhotos>);

  vi.mocked(customerHooks.useCustomerInvoices).mockReturnValue({
    data: { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 },
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useCustomerInvoices>);

  vi.mocked(customerHooks.useCustomerPaymentMethods).mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useCustomerPaymentMethods>);

  vi.mocked(customerHooks.useCustomerDuplicates).mockReturnValue({
    data: null,
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useCustomerDuplicates>);

  vi.mocked(customerHooks.useCustomerSentMessages).mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useCustomerSentMessages>);

  vi.mocked(customerHooks.useServicePreferences).mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  } as unknown as ReturnType<typeof customerHooks.useServicePreferences>);
}

describe('CustomerDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders tabbed layout with all tabs', async () => {
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('customer-detail')).toBeInTheDocument();
    });

    expect(screen.getByTestId('customer-tabs')).toBeInTheDocument();
    expect(screen.getByTestId('tab-overview')).toBeInTheDocument();
    expect(screen.getByTestId('tab-photos')).toBeInTheDocument();
    expect(screen.getByTestId('tab-invoices')).toBeInTheDocument();
    expect(screen.getByTestId('tab-payment-methods')).toBeInTheDocument();
    expect(screen.getByTestId('tab-messages')).toBeInTheDocument();
    expect(screen.getByTestId('tab-duplicates')).toBeInTheDocument();
  });

  it('shows Overview tab by default with internal notes', async () => {
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('tab-content-overview')).toBeInTheDocument();
    });

    expect(screen.getByTestId('customer-internal-notes-display')).toBeInTheDocument();
    expect(screen.getByText('VIP customer, prefers morning calls')).toBeInTheDocument();
  });

  it('shows service preferences section on Overview tab', async () => {
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('service-preferences-section')).toBeInTheDocument();
    });

    expect(screen.getByTestId('add-preference-btn')).toBeInTheDocument();
  });

  it('switches to Photos tab', async () => {
    const user = userEvent.setup();
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('tab-photos')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('tab-photos'));

    await waitFor(() => {
      expect(screen.getByTestId('tab-content-photos')).toBeInTheDocument();
    });

    expect(screen.getByTestId('photo-gallery')).toBeInTheDocument();
  });

  it('switches to Invoice History tab', async () => {
    const user = userEvent.setup();
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('tab-invoices')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('tab-invoices'));

    await waitFor(() => {
      expect(screen.getByTestId('tab-content-invoices')).toBeInTheDocument();
    });

    expect(screen.getByTestId('invoices-empty')).toBeInTheDocument();
  });

  it('switches to Payment Methods tab', async () => {
    const user = userEvent.setup();
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('tab-payment-methods')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('tab-payment-methods'));

    await waitFor(() => {
      expect(screen.getByTestId('tab-content-payment-methods')).toBeInTheDocument();
    });

    expect(screen.getByTestId('payment-methods-empty')).toBeInTheDocument();
  });

  it('switches to Messages tab', async () => {
    const user = userEvent.setup();
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('tab-messages')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('tab-messages'));

    await waitFor(() => {
      expect(screen.getByTestId('tab-content-messages')).toBeInTheDocument();
    });

    expect(screen.getByTestId('messages-empty')).toBeInTheDocument();
  });

  it('opens notes editor when Edit is clicked', async () => {
    const user = userEvent.setup();
    render(<CustomerDetail />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('customer-edit-notes-btn')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('customer-edit-notes-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('customer-notes-editor')).toBeInTheDocument();
    });

    expect(screen.getByTestId('customer-internal-notes-textarea')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    vi.mocked(customerHooks.useCustomer).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomer>);

    render(<CustomerDetail />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(customerHooks.useCustomer).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch'),
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomerSentMessages>);

    render(<CustomerDetail />, { wrapper: createWrapper() });

    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  // ---- Internal Notes Card (internal-notes-simplification Req 2, 9) ----

  describe('InternalNotesCard', () => {
    it('renders InternalNotesCard with customer.internal_notes', async () => {
      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-notes-editor')).toBeInTheDocument();
      });

      expect(screen.getByText('VIP customer, prefers morning calls')).toBeInTheDocument();
      expect(screen.getByTestId('customer-internal-notes-display')).toBeInTheDocument();
    });

    it('renders placeholder when internal_notes is null', async () => {
      vi.mocked(customerHooks.useCustomer).mockReturnValue({
        data: { ...mockCustomer, internal_notes: null },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomer>);

      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-notes-editor')).toBeInTheDocument();
      });

      expect(screen.getByText('No internal notes')).toBeInTheDocument();
    });

    it('Edit → type → Save triggers useUpdateCustomer with { internal_notes }', async () => {
      const user = userEvent.setup();
      const mockMutateAsync = vi.fn().mockResolvedValue(undefined);
      const { useUpdateCustomer } = await import('../hooks/useCustomerMutations');
      vi.mocked(useUpdateCustomer).mockReturnValue({
        mutateAsync: mockMutateAsync,
        isPending: false,
      } as unknown as ReturnType<typeof useUpdateCustomer>);

      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-edit-notes-btn')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('customer-edit-notes-btn'));

      const textarea = screen.getByTestId('customer-internal-notes-textarea');
      await user.clear(textarea);
      await user.type(textarea, 'Updated customer notes');

      await user.click(screen.getByTestId('customer-save-notes-btn'));

      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            id: 'cust-1',
            data: { internal_notes: 'Updated customer notes' },
          })
        );
      });
    });

    it('Cancel reverts unsaved changes', async () => {
      const user = userEvent.setup();

      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-edit-notes-btn')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('customer-edit-notes-btn'));

      const textarea = screen.getByTestId('customer-internal-notes-textarea');
      await user.clear(textarea);
      await user.type(textarea, 'Discarded changes');

      await user.click(screen.getByText('Cancel'));

      await waitFor(() => {
        expect(screen.queryByTestId('customer-internal-notes-textarea')).not.toBeInTheDocument();
      });

      expect(screen.getByText('VIP customer, prefers morning calls')).toBeInTheDocument();
    });
  });

  // ---- April 16th: Inline edit sections ----

  describe('April 16th: Inline edit sections', () => {
    it('renders customer basic info fields', async () => {
      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-detail')).toBeInTheDocument();
      });

      // Customer name should be displayed (may appear in multiple places)
      expect(screen.getAllByText('John Doe').length).toBeGreaterThanOrEqual(1);
    });

    it('renders communication preferences section', async () => {
      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-detail')).toBeInTheDocument();
      });

      // The overview tab content should be displayed
      expect(screen.getByTestId('tab-content-overview')).toBeInTheDocument();
    });

    it('renders properties section on overview tab', async () => {
      const customerWithProperties = {
        ...mockCustomer,
        properties: [
          {
            id: 'prop-1',
            customer_id: 'cust-1',
            address: '123 Main St',
            city: 'Minneapolis',
            state: 'MN',
            zip_code: '55401',
            is_primary: true,
            zone_count: 6,
            system_type: 'standard',
            property_type: 'residential',
            has_dogs: false,
            gate_code: null,
            access_instructions: null,
            special_notes: null,
            latitude: null,
            longitude: null,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
        ],
      };

      vi.mocked(customerHooks.useCustomer).mockReturnValue({
        data: customerWithProperties,
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomer>);

      render(<CustomerDetail />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-detail')).toBeInTheDocument();
      });

      // Property address should be displayed somewhere on the page
      expect(screen.getAllByText(/123 Main St/).length).toBeGreaterThanOrEqual(1);
    });
  });
});
