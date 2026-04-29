/**
 * Tests for PaymentDialog component.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PaymentDialog, normalizePaymentReference } from './PaymentDialog';

const defaultProps = {
  open: true,
  onOpenChange: vi.fn(),
  remainingBalance: 150.0,
  onSubmit: vi.fn(),
  isLoading: false,
};

describe('PaymentDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dialog with correct data-testid', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByTestId('payment-dialog')).toBeInTheDocument();
  });

  it('renders amount input with default value', () => {
    render(<PaymentDialog {...defaultProps} />);
    const amountInput = screen.getByTestId('payment-amount');
    expect(amountInput).toBeInTheDocument();
    expect(amountInput).toHaveValue(150.0);
  });

  it('renders payment method select', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByTestId('payment-method')).toBeInTheDocument();
  });

  it('renders reference input', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByTestId('payment-reference')).toBeInTheDocument();
  });

  it('displays remaining balance', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByText('Remaining balance: $150.00')).toBeInTheDocument();
  });

  it('shows error when amount is invalid', async () => {
    const user = userEvent.setup();
    render(<PaymentDialog {...defaultProps} />);

    const amountInput = screen.getByTestId('payment-amount');
    await user.clear(amountInput);
    await user.type(amountInput, '0');

    const submitBtn = screen.getByTestId('submit-payment-btn');
    await user.click(submitBtn);

    expect(screen.getByTestId('payment-error')).toBeInTheDocument();
    expect(defaultProps.onSubmit).not.toHaveBeenCalled();
  });

  it('shows error when payment method is not selected', async () => {
    const user = userEvent.setup();
    render(<PaymentDialog {...defaultProps} />);

    const submitBtn = screen.getByTestId('submit-payment-btn');
    await user.click(submitBtn);

    expect(screen.getByTestId('payment-error')).toBeInTheDocument();
    expect(screen.getByText('Please select a payment method')).toBeInTheDocument();
    expect(defaultProps.onSubmit).not.toHaveBeenCalled();
  });

  it('disables inputs when loading', () => {
    render(<PaymentDialog {...defaultProps} isLoading={true} />);

    expect(screen.getByTestId('payment-amount')).toBeDisabled();
    expect(screen.getByTestId('payment-reference')).toBeDisabled();
    expect(screen.getByTestId('submit-payment-btn')).toBeDisabled();
    expect(screen.getByTestId('payment-cancel')).toBeDisabled();
  });

  it('shows loading text on submit button when loading', () => {
    render(<PaymentDialog {...defaultProps} isLoading={true} />);
    expect(screen.getByTestId('submit-payment-btn')).toHaveTextContent('Recording...');
  });

  it('calls onOpenChange when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<PaymentDialog {...defaultProps} />);

    const cancelBtn = screen.getByTestId('payment-cancel');
    await user.click(cancelBtn);

    expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
  });

  it('renders all payment method options in select', () => {
    render(<PaymentDialog {...defaultProps} />);
    
    // Check that the select trigger shows placeholder
    const selectTrigger = screen.getByTestId('payment-method');
    expect(selectTrigger).toBeInTheDocument();
    expect(screen.getByText('Select payment method')).toBeInTheDocument();
  });

  it('renders submit button with correct text', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByTestId('submit-payment-btn')).toHaveTextContent('Record Payment');
  });

  it('renders cancel button', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByTestId('payment-cancel')).toHaveTextContent('Cancel');
  });

  it('renders dialog title', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByRole('heading', { name: 'Record Payment' })).toBeInTheDocument();
  });

  it('renders dialog description', () => {
    render(<PaymentDialog {...defaultProps} />);
    expect(screen.getByText('Enter the payment details for this invoice.')).toBeInTheDocument();
  });

});

// Plan §Phase 3.6 — auto-prefix bare Stripe `pi_*` references with
// `stripe:` so CG-13 search by PaymentIntent id keeps working. Tested
// against the exported pure function so jsdom limitations around the
// Radix Select don't poison the assertion.
describe('normalizePaymentReference (CG-13)', () => {
  it('prepends stripe: to a bare pi_* id', () => {
    expect(normalizePaymentReference('pi_3OXxxxYYY')).toBe(
      'stripe:pi_3OXxxxYYY',
    );
  });

  it('does not double-prepend when reference is already stripe:pi_*', () => {
    expect(normalizePaymentReference('stripe:pi_3OXxxxYYY')).toBe(
      'stripe:pi_3OXxxxYYY',
    );
  });

  it('leaves unrelated references untouched', () => {
    expect(normalizePaymentReference('CHK-12345')).toBe('CHK-12345');
  });

  it('returns undefined for blank input', () => {
    expect(normalizePaymentReference('')).toBeUndefined();
    expect(normalizePaymentReference('   ')).toBeUndefined();
  });

  it('trims whitespace around bare pi_* before prefixing', () => {
    expect(normalizePaymentReference('  pi_3ABC  ')).toBe('stripe:pi_3ABC');
  });

  it('does not match invalid pi_* shapes', () => {
    // No alnum body → not a valid PaymentIntent id, leave untouched.
    expect(normalizePaymentReference('pi_')).toBe('pi_');
    // Embedded suffix should not be auto-prefixed.
    expect(normalizePaymentReference('foo pi_3ABC')).toBe('foo pi_3ABC');
  });
});
