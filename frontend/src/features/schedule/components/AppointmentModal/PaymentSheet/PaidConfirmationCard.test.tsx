/**
 * Tests for PaidConfirmationCard — confirmation surface after a
 * collected payment. Umbrella plan §Phase 4.4.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PaidConfirmationCard } from './PaidConfirmationCard';

describe('PaidConfirmationCard', () => {
  it('renders amount and method label', () => {
    render(
      <PaidConfirmationCard amountPaid={150} paymentMethod="cash" />,
    );
    expect(screen.getByTestId('payment-paid-card')).toBeInTheDocument();
    expect(screen.getByText(/Payment Received/i)).toBeInTheDocument();
    expect(screen.getByText(/\$150\.00 · Cash/)).toBeInTheDocument();
  });

  it('formats credit_card method as "Credit card · Stripe"', () => {
    render(
      <PaidConfirmationCard amountPaid="200" paymentMethod="credit_card" />,
    );
    expect(screen.getByText(/Credit card · Stripe/)).toBeInTheDocument();
  });

  it('renders payment reference when provided', () => {
    render(
      <PaidConfirmationCard
        amountPaid={100}
        paymentMethod="check"
        paymentReference="1234"
      />,
    );
    expect(screen.getByText(/#1234/)).toBeInTheDocument();
  });

  it('hides Text receipt CTA when no handler given', () => {
    render(
      <PaidConfirmationCard amountPaid={50} paymentMethod="zelle" />,
    );
    expect(screen.queryByTestId('text-receipt-cta')).toBeNull();
  });

  it('fires onTextReceipt when Text receipt clicked', () => {
    const handler = vi.fn();
    render(
      <PaidConfirmationCard
        amountPaid={50}
        paymentMethod="venmo"
        onTextReceipt={handler}
      />,
    );
    fireEvent.click(screen.getByTestId('text-receipt-cta'));
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('disables Text receipt button when pending', () => {
    render(
      <PaidConfirmationCard
        amountPaid={50}
        paymentMethod="cash"
        onTextReceipt={() => {}}
        textReceiptPending
      />,
    );
    const cta = screen.getByTestId('text-receipt-cta') as HTMLButtonElement;
    expect(cta).toBeDisabled();
    expect(cta.textContent).toMatch(/Sending/);
  });
});
