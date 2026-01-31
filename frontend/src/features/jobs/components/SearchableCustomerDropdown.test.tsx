import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SearchableCustomerDropdown } from './SearchableCustomerDropdown';
import { customerApi } from '@/features/customers/api/customerApi';
import type { Customer } from '@/features/customers/types';

// Mock the customer API
vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    search: vi.fn(),
    get: vi.fn(),
  },
}));

const mockCustomers: Customer[] = [
  {
    id: '1',
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
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    first_name: 'Jane',
    last_name: 'Smith',
    phone: '612-555-5678',
    email: 'jane@example.com',
    is_priority: true,
    is_red_flag: false,
    is_slow_payer: false,
    is_new_customer: false,
    sms_opt_in: true,
    email_opt_in: true,
    lead_source: 'referral',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
  {
    id: '3',
    first_name: 'Bob',
    last_name: 'Johnson',
    phone: '612-555-9999',
    email: 'bob@example.com',
    is_priority: false,
    is_red_flag: false,
    is_slow_payer: false,
    is_new_customer: true,
    sms_opt_in: false,
    email_opt_in: false,
    lead_source: 'google',
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z',
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
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('SearchableCustomerDropdown', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dropdown button', () => {
    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByTestId('customer-dropdown')).toBeInTheDocument();
    expect(screen.getByText('Select customer...')).toBeInTheDocument();
  });

  it('shows search input when dropdown is opened', async () => {
    const user = userEvent.setup();
    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));

    expect(screen.getByTestId('customer-search-input')).toBeInTheDocument();
  });

  it('searches customers when typing in search input', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: mockCustomers.filter((c) => c.first_name.includes('John')),
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');
    await user.type(searchInput, 'John');

    await waitFor(() => {
      expect(customerApi.search).toHaveBeenCalledWith('John');
    });
  });

  it('displays search results', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: mockCustomers,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');
    await user.type(searchInput, 'test');

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-1')).toBeInTheDocument();
      expect(screen.getByTestId('customer-option-2')).toBeInTheDocument();
      expect(screen.getByTestId('customer-option-3')).toBeInTheDocument();
    });
  });

  it('shows "No customers found" when search returns empty', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');
    await user.type(searchInput, 'nonexistent');

    await waitFor(() => {
      expect(screen.getByText('No customers found')).toBeInTheDocument();
    });
  });

  /**
   * Property 4: Customer Dropdown Accuracy
   * 
   * This property-based test verifies that when a customer is selected from the dropdown,
   * the customer ID passed to onChange matches the displayed customer name.
   * 
   * Test Strategy:
   * 1. For each customer in the mock data set
   * 2. Search for and select that customer
   * 3. Verify the onChange callback receives the correct customer ID
   * 4. Verify the dropdown displays the correct customer name
   * 
   * This validates Requirement 8.4: Selected customer ID matches displayed name
   */
  it('Property 4: selected customer ID matches displayed name', async () => {
    // Test property for each customer in our dataset
    for (const customer of mockCustomers) {
      vi.clearAllMocks();

      // Mock search to return this specific customer
      vi.mocked(customerApi.search).mockResolvedValue({
        items: [customer],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      });

      // Mock get to return the customer when fetching by ID
      vi.mocked(customerApi.get).mockResolvedValue(customer);

      const { unmount } = render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
        wrapper: createWrapper(),
      });

      const user = userEvent.setup();

      // Open dropdown and search
      await user.click(screen.getByTestId('customer-dropdown'));
      const searchInput = screen.getByTestId('customer-search-input');
      await user.type(searchInput, customer.first_name);

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByTestId(`customer-option-${customer.id}`)).toBeInTheDocument();
      });

      // Select the customer
      await user.click(screen.getByTestId(`customer-option-${customer.id}`));

      // Verify onChange was called with correct ID
      await waitFor(() => {
        expect(mockOnChange).toHaveBeenCalledWith(customer.id);
      });

      // Verify the dropdown now displays the correct customer name
      const expectedDisplayText = `${customer.first_name} ${customer.last_name} - ${customer.phone}`;
      await waitFor(() => {
        expect(screen.getByText(expectedDisplayText)).toBeInTheDocument();
      });

      // Clean up before next iteration
      unmount();
    }
  });

  it('calls onChange with correct customer ID when customer is selected', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: mockCustomers,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');
    await user.type(searchInput, 'test');

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-1')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('customer-option-1'));

    expect(mockOnChange).toHaveBeenCalledWith('1');
  });

  it('displays selected customer name after selection', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: mockCustomers,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');
    await user.type(searchInput, 'test');

    await waitFor(() => {
      expect(screen.getByTestId('customer-option-1')).toBeInTheDocument();
    });

    await user.click(screen.getByTestId('customer-option-1'));

    await waitFor(() => {
      expect(screen.getByText('John Doe - 612-555-1234')).toBeInTheDocument();
    });
  });

  it('loads and displays pre-selected customer', async () => {
    vi.mocked(customerApi.get).mockResolvedValue(mockCustomers[0]);

    render(<SearchableCustomerDropdown value="1" onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(customerApi.get).toHaveBeenCalledWith('1');
      expect(screen.getByText('John Doe - 612-555-1234')).toBeInTheDocument();
    });
  });

  it('disables dropdown when disabled prop is true', () => {
    render(<SearchableCustomerDropdown onChange={mockOnChange} disabled />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByTestId('customer-dropdown')).toBeDisabled();
  });

  it('debounces search requests', async () => {
    const user = userEvent.setup();
    vi.mocked(customerApi.search).mockResolvedValue({
      items: mockCustomers,
      total: 3,
      page: 1,
      page_size: 20,
      total_pages: 1,
    });

    render(<SearchableCustomerDropdown onChange={mockOnChange} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByTestId('customer-dropdown'));
    const searchInput = screen.getByTestId('customer-search-input');

    // Type multiple characters quickly
    await user.type(searchInput, 'John');

    // Wait for debounce (300ms)
    await waitFor(
      () => {
        // Should only call search once after debounce
        expect(customerApi.search).toHaveBeenCalledTimes(1);
      },
      { timeout: 500 }
    );
  });
});
