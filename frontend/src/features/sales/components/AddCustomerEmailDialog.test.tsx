import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AddCustomerEmailDialog } from './AddCustomerEmailDialog';

const mockUpdateCustomerMutateAsync = vi.fn();

vi.mock('@/features/customers', () => ({
  useUpdateCustomer: () => ({
    mutateAsync: mockUpdateCustomerMutateAsync,
    isPending: false,
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe('AddCustomerEmailDialog', () => {
  beforeEach(() => {
    mockUpdateCustomerMutateAsync.mockReset();
    mockUpdateCustomerMutateAsync.mockResolvedValue(undefined);
  });

  it('renders dialog with email input when open', () => {
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={vi.fn()}
        customerId="cust-001"
      />,
    );
    expect(screen.getByTestId('add-customer-email-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('customer-email-input')).toBeInTheDocument();
  });

  it('confirm button disabled when email is empty', () => {
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={vi.fn()}
        customerId="cust-001"
      />,
    );
    expect(screen.getByTestId('confirm-add-email-btn')).toBeDisabled();
  });

  it('confirm button disabled with malformed email', async () => {
    const user = userEvent.setup();
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={vi.fn()}
        customerId="cust-001"
      />,
    );
    await user.type(screen.getByTestId('customer-email-input'), 'not-an-email');
    expect(screen.getByTestId('confirm-add-email-btn')).toBeDisabled();
  });

  it('confirm button enabled with valid email', async () => {
    const user = userEvent.setup();
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={vi.fn()}
        customerId="cust-001"
      />,
    );
    await user.type(
      screen.getByTestId('customer-email-input'),
      'jane@example.com',
    );
    expect(screen.getByTestId('confirm-add-email-btn')).not.toBeDisabled();
  });

  it('submit calls useUpdateCustomer with email and fires onSaved', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onSaved = vi.fn();
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={onOpenChange}
        customerId="cust-001"
        onSaved={onSaved}
      />,
    );
    await user.type(
      screen.getByTestId('customer-email-input'),
      'jane@example.com',
    );
    await user.click(screen.getByTestId('confirm-add-email-btn'));

    await waitFor(() => {
      expect(mockUpdateCustomerMutateAsync).toHaveBeenCalledWith({
        id: 'cust-001',
        data: { email: 'jane@example.com' },
      });
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onSaved).toHaveBeenCalled();
  });

  it('cancel button fires onOpenChange(false)', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <AddCustomerEmailDialog
        open
        onOpenChange={onOpenChange}
        customerId="cust-001"
      />,
    );
    await user.click(screen.getByTestId('cancel-add-email-btn'));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
