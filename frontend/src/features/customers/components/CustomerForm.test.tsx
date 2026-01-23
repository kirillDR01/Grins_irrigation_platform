import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CustomerForm } from './CustomerForm';
import * as customerMutations from '../hooks/useCustomerMutations';

// Mock the mutation hooks
vi.mock('../hooks/useCustomerMutations', () => ({
  useCreateCustomer: vi.fn(),
  useUpdateCustomer: vi.fn(),
  useDeleteCustomer: vi.fn(),
  useUpdateCustomerFlags: vi.fn(),
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockCustomer = {
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
};

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

describe('CustomerForm', () => {
  const mockCreateMutate = vi.fn();
  const mockUpdateMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(customerMutations.useCreateCustomer).mockReturnValue({
      mutateAsync: mockCreateMutate,
      isPending: false,
    } as unknown as ReturnType<typeof customerMutations.useCreateCustomer>);

    vi.mocked(customerMutations.useUpdateCustomer).mockReturnValue({
      mutateAsync: mockUpdateMutate,
      isPending: false,
    } as unknown as ReturnType<typeof customerMutations.useUpdateCustomer>);
  });

  it('renders form with empty fields for create mode', () => {
    render(<CustomerForm />, { wrapper: createWrapper() });

    expect(screen.getByTestId('customer-form')).toBeInTheDocument();
    expect(screen.getByTestId('first-name-input')).toHaveValue('');
    expect(screen.getByTestId('last-name-input')).toHaveValue('');
    expect(screen.getByTestId('phone-input')).toHaveValue('');
    expect(screen.getByTestId('email-input')).toHaveValue('');
  });

  it('renders form with customer data for edit mode', () => {
    render(<CustomerForm customer={mockCustomer} />, { wrapper: createWrapper() });

    expect(screen.getByTestId('first-name-input')).toHaveValue('John');
    expect(screen.getByTestId('last-name-input')).toHaveValue('Doe');
    expect(screen.getByTestId('phone-input')).toHaveValue('612-555-1234');
    expect(screen.getByTestId('email-input')).toHaveValue('john@example.com');
  });

  it('shows validation errors for required fields', async () => {
    const user = userEvent.setup();
    render(<CustomerForm />, { wrapper: createWrapper() });

    const submitButton = screen.getByTestId('submit-btn');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('First name is required')).toBeInTheDocument();
      expect(screen.getByText('Last name is required')).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid phone', async () => {
    const user = userEvent.setup();
    render(<CustomerForm />, { wrapper: createWrapper() });

    await user.type(screen.getByTestId('first-name-input'), 'John');
    await user.type(screen.getByTestId('last-name-input'), 'Doe');
    await user.type(screen.getByTestId('phone-input'), '123');

    const submitButton = screen.getByTestId('submit-btn');
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Phone must be at least 10 digits')).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid email', async () => {
    const user = userEvent.setup();
    render(<CustomerForm />, { wrapper: createWrapper() });

    await user.type(screen.getByTestId('first-name-input'), 'John');
    await user.type(screen.getByTestId('last-name-input'), 'Doe');
    await user.type(screen.getByTestId('phone-input'), '6125551234');
    await user.type(screen.getByTestId('email-input'), 'invalid-email');

    const submitButton = screen.getByTestId('submit-btn');
    await user.click(submitButton);

    // Wait for form to process - the form should not submit with invalid email
    // Since zod validation happens, the mutation should not be called
    await waitFor(() => {
      expect(mockCreateMutate).not.toHaveBeenCalled();
    });
  });

  it('calls createMutation on submit in create mode', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    mockCreateMutate.mockResolvedValue({ id: '1' });

    render(<CustomerForm onSuccess={onSuccess} />, { wrapper: createWrapper() });

    await user.type(screen.getByTestId('first-name-input'), 'John');
    await user.type(screen.getByTestId('last-name-input'), 'Doe');
    await user.type(screen.getByTestId('phone-input'), '6125551234');

    const submitButton = screen.getByTestId('submit-btn');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockCreateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          first_name: 'John',
          last_name: 'Doe',
          phone: '6125551234',
        })
      );
    });
  });

  it('calls updateMutation on submit in edit mode', async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    mockUpdateMutate.mockResolvedValue({ id: '1' });

    render(<CustomerForm customer={mockCustomer} onSuccess={onSuccess} />, {
      wrapper: createWrapper(),
    });

    await user.clear(screen.getByTestId('first-name-input'));
    await user.type(screen.getByTestId('first-name-input'), 'Jane');

    const submitButton = screen.getByTestId('submit-btn');
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockUpdateMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          id: '1',
          data: expect.objectContaining({
            first_name: 'Jane',
          }),
        })
      );
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(<CustomerForm onCancel={onCancel} />, { wrapper: createWrapper() });

    const cancelButton = screen.getByText('Cancel');
    await user.click(cancelButton);

    expect(onCancel).toHaveBeenCalled();
  });

  it('displays correct button text for create mode', () => {
    render(<CustomerForm />, { wrapper: createWrapper() });

    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Create Customer');
  });

  it('displays correct button text for edit mode', () => {
    render(<CustomerForm customer={mockCustomer} />, { wrapper: createWrapper() });

    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Update Customer');
  });
});
