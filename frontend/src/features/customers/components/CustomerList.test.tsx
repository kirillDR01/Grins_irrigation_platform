import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { CustomerList } from './CustomerList';
import * as customerHooks from '../hooks/useCustomers';

// Mock the hooks
vi.mock('../hooks/useCustomers', () => ({
  useCustomers: vi.fn(),
  customerKeys: {
    all: ['customers'],
    lists: () => ['customers', 'list'],
    list: (params: unknown) => ['customers', 'list', params],
    details: () => ['customers', 'detail'],
    detail: (id: string) => ['customers', 'detail', id],
  },
}));

// Mock NewTextCampaignModal to avoid AuthProvider dependency
vi.mock('@/features/communications', () => ({
  NewTextCampaignModal: ({ open, preSelectedCustomerIds }: { open: boolean; preSelectedCustomerIds?: string[] }) =>
    open ? <div data-testid="campaign-modal">Campaign Modal ({preSelectedCustomerIds?.length ?? 0} customers)</div> : null,
}));

// Capture the onSearch callback from CustomerSearch so we can invoke it directly
let capturedOnSearch: ((query: string) => void) | null = null;

vi.mock('./CustomerSearch', () => ({
  CustomerSearch: ({ onSearch, placeholder }: { onSearch: (q: string) => void; placeholder?: string }) => {
    capturedOnSearch = onSearch;
    return (
      <div data-testid="customer-search">
        <input
          data-testid="customer-search-input"
          placeholder={placeholder || 'Search customers...'}
          onChange={() => {
            // Simulate debounce: the real component debounces internally
            // and calls onSearch with the debounced value.
            // In tests, we call onSearch directly via capturedOnSearch.
          }}
        />
      </div>
    );
  },
}));

const mockCustomers = [
  {
    id: '1',
    first_name: 'John',
    last_name: 'Doe',
    phone: '612-555-1234',
    email: 'john@example.com',
    is_priority: true,
    is_red_flag: false,
    is_slow_payer: false,
    is_new_customer: false,
    sms_opt_in: true,
    email_opt_in: true,
    lead_source: 'website',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    first_name: 'Jane',
    last_name: 'Smith',
    phone: '612-555-5678',
    email: null,
    is_priority: false,
    is_red_flag: true,
    is_slow_payer: false,
    is_new_customer: true,
    sms_opt_in: false,
    email_opt_in: false,
    lead_source: 'referral',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
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

describe('CustomerList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state', () => {
    vi.mocked(customerHooks.useCustomers).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomers>);

    render(<CustomerList />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    vi.mocked(customerHooks.useCustomers).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to fetch customers'),
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomers>);

    render(<CustomerList />, { wrapper: createWrapper() });

    expect(screen.getByText(/error/i)).toBeInTheDocument();
  });

  it('renders customer list with data', async () => {
    vi.mocked(customerHooks.useCustomers).mockReturnValue({
      data: {
        items: mockCustomers,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomers>);

    render(<CustomerList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('customer-list')).toBeInTheDocument();
    });

    // Check that customer names are displayed
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('renders empty state when no customers', async () => {
    vi.mocked(customerHooks.useCustomers).mockReturnValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomers>);

    render(<CustomerList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('customer-list')).toBeInTheDocument();
    });

    expect(screen.getByText(/no customers/i)).toBeInTheDocument();
  });

  it('displays customer flags correctly', async () => {
    vi.mocked(customerHooks.useCustomers).mockReturnValue({
      data: {
        items: mockCustomers,
        total: 2,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof customerHooks.useCustomers>);

    render(<CustomerList />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('customer-list')).toBeInTheDocument();
    });

    // Check for priority badge on John Doe (using data-testid)
    expect(screen.getByTestId('status-priority')).toBeInTheDocument();
    // Check for red flag badge on Jane Smith
    expect(screen.getByTestId('status-red_flag')).toBeInTheDocument();
  });

  describe('debounce integration', () => {
    beforeEach(() => {
      capturedOnSearch = null;
    });

    it('renders the CustomerSearch component instead of inline input', () => {
      vi.mocked(customerHooks.useCustomers).mockReturnValue({
        data: {
          items: mockCustomers,
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomers>);

      render(<CustomerList />, { wrapper: createWrapper() });

      // CustomerSearch component renders with data-testid="customer-search"
      expect(screen.getByTestId('customer-search')).toBeInTheDocument();
      // The debounced search input should be present
      expect(screen.getByTestId('customer-search-input')).toBeInTheDocument();
    });

    it('passes debounced search value to useCustomers', async () => {
      vi.mocked(customerHooks.useCustomers).mockReturnValue({
        data: {
          items: mockCustomers,
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomers>);

      render(<CustomerList />, { wrapper: createWrapper() });

      // Before search, useCustomers should be called with no search param
      const callsBefore = vi.mocked(customerHooks.useCustomers).mock.calls;
      const lastCallBefore = callsBefore[callsBefore.length - 1][0];
      expect(lastCallBefore?.search).toBeUndefined();

      // Simulate the debounced search callback firing (as CustomerSearch would after 300ms)
      act(() => {
        capturedOnSearch!('John');
      });

      // After debounced callback, useCustomers should be called with the search query
      await waitFor(() => {
        const calls = vi.mocked(customerHooks.useCustomers).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall?.search).toBe('John');
      });
    });

    it('resets pagination to page 1 when search query changes', async () => {
      vi.mocked(customerHooks.useCustomers).mockReturnValue({
        data: {
          items: mockCustomers,
          total: 40,
          page: 1,
          page_size: 20,
          total_pages: 2,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomers>);

      render(<CustomerList />, { wrapper: createWrapper() });

      // Navigate to page 2
      const nextBtn = screen.getByTestId('next-page-btn');
      fireEvent.click(nextBtn);

      // Verify page changed to 2
      await waitFor(() => {
        const calls = vi.mocked(customerHooks.useCustomers).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall?.page).toBe(2);
      });

      // Simulate debounced search callback
      act(() => {
        capturedOnSearch!('test');
      });

      // After search change, page should be reset to 1
      await waitFor(() => {
        const calls = vi.mocked(customerHooks.useCustomers).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall?.page).toBe(1);
        expect(lastCall?.search).toBe('test');
      });
    });

    it('only updates search param with final debounced value', async () => {
      vi.mocked(customerHooks.useCustomers).mockReturnValue({
        data: {
          items: mockCustomers,
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomers>);

      render(<CustomerList />, { wrapper: createWrapper() });

      // Simulate the final debounced value (CustomerSearch only calls onSearch after debounce)
      act(() => {
        capturedOnSearch!('John');
      });

      // The search param should reflect the debounced value
      await waitFor(() => {
        const calls = vi.mocked(customerHooks.useCustomers).mock.calls;
        const lastCall = calls[calls.length - 1][0];
        expect(lastCall?.search).toBe('John');
      });

      // Verify no intermediate values were passed — only 'John' should appear as a search value
      const allCalls = vi.mocked(customerHooks.useCustomers).mock.calls;
      const searchValues = allCalls.map(call => call[0]?.search).filter(Boolean);
      const uniqueSearchValues = [...new Set(searchValues)];
      expect(uniqueSearchValues).toEqual(['John']);
    });
  });

  describe('bulk select and Text Selected', () => {
    beforeEach(() => {
      vi.mocked(customerHooks.useCustomers).mockReturnValue({
        data: {
          items: mockCustomers,
          total: 2,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      } as unknown as ReturnType<typeof customerHooks.useCustomers>);
    });

    it('renders checkbox column in the table', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      expect(screen.getByTestId('select-all-customers')).toBeInTheDocument();
      expect(screen.getByTestId(`select-customer-${mockCustomers[0].id}`)).toBeInTheDocument();
      expect(screen.getByTestId(`select-customer-${mockCustomers[1].id}`)).toBeInTheDocument();
    });

    it('does not show bulk-action bar when no rows selected', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument();
    });

    it('shows bulk-action bar with selected count when a row is checked', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      // Click the first customer checkbox
      fireEvent.click(screen.getByTestId(`select-customer-${mockCustomers[0].id}`));

      await waitFor(() => {
        expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
      });

      expect(screen.getByTestId('selected-count')).toHaveTextContent('1 selected');
      expect(screen.getByTestId('text-selected-customers-btn')).toBeInTheDocument();
    });

    it('opens campaign modal with pre-selected customer IDs when Text Selected is clicked', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      // Select first customer
      fireEvent.click(screen.getByTestId(`select-customer-${mockCustomers[0].id}`));

      await waitFor(() => {
        expect(screen.getByTestId('text-selected-customers-btn')).toBeInTheDocument();
      });

      // Click "Text Selected"
      fireEvent.click(screen.getByTestId('text-selected-customers-btn'));

      await waitFor(() => {
        expect(screen.getByTestId('campaign-modal')).toBeInTheDocument();
      });

      // Mock renders the count of pre-selected IDs
      expect(screen.getByTestId('campaign-modal')).toHaveTextContent('1 customers');
    });

    it('clears selection when clear button is clicked', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      // Select a customer
      fireEvent.click(screen.getByTestId(`select-customer-${mockCustomers[0].id}`));

      await waitFor(() => {
        expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
      });

      // Click clear
      fireEvent.click(screen.getByTestId('clear-selection-btn'));

      await waitFor(() => {
        expect(screen.queryByTestId('bulk-action-bar')).not.toBeInTheDocument();
      });
    });

    it('selects all rows via select-all checkbox', async () => {
      render(<CustomerList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('customer-list')).toBeInTheDocument();
      });

      // Click select all
      fireEvent.click(screen.getByTestId('select-all-customers'));

      await waitFor(() => {
        expect(screen.getByTestId('bulk-action-bar')).toBeInTheDocument();
      });

      expect(screen.getByTestId('selected-count')).toHaveTextContent('2 selected');
    });
  });
});
