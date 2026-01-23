import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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
});
