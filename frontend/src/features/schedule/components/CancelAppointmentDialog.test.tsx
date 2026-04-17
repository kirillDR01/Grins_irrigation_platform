/**
 * Tests for CancelAppointmentDialog — the three-button admin cancel UX.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CancelAppointmentDialog } from './CancelAppointmentDialog';

const baseProps = {
  open: true,
  onOpenChange: vi.fn(),
  customerName: 'Jane Smith',
  customerPhone: '(952) 737-3312',
  scheduledDate: '2026-04-21',
  timeWindowStart: '10:00:00',
  timeWindowEnd: '12:00:00',
  willNotifyByDefault: true,
  onConfirm: vi.fn(),
  isLoading: false,
};

describe('CancelAppointmentDialog', () => {
  it('renders customer name, phone, and time window', () => {
    render(<CancelAppointmentDialog {...baseProps} />);

    expect(screen.getByTestId('cancel-dialog-customer')).toHaveTextContent(
      'Jane Smith',
    );
    expect(screen.getByTestId('cancel-dialog-phone')).toHaveTextContent(
      '(952) 737-3312',
    );
    expect(screen.getByText(/10:00/)).toBeInTheDocument();
    expect(screen.getByText(/12:00/)).toBeInTheDocument();
  });

  it('keeps the appointment when "Keep" is clicked', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    const onConfirm = vi.fn();
    render(
      <CancelAppointmentDialog
        {...baseProps}
        onOpenChange={onOpenChange}
        onConfirm={onConfirm}
      />,
    );

    await user.click(screen.getByTestId('cancel-dialog-keep'));

    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('fires onConfirm(false) when "Cancel (no text)" is clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <CancelAppointmentDialog {...baseProps} onConfirm={onConfirm} />,
    );

    await user.click(screen.getByTestId('cancel-dialog-cancel-no-text'));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith(false);
  });

  it('fires onConfirm(true) when "Cancel & text customer" is clicked', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <CancelAppointmentDialog {...baseProps} onConfirm={onConfirm} />,
    );

    await user.click(screen.getByTestId('cancel-dialog-cancel-with-text'));

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledWith(true);
  });

  it('disables "Cancel & text customer" when the pre-cancel state sends no SMS', () => {
    render(
      <CancelAppointmentDialog
        {...baseProps}
        willNotifyByDefault={false}
      />,
    );

    const textBtn = screen.getByTestId('cancel-dialog-cancel-with-text');
    expect(textBtn).toBeDisabled();
    expect(
      screen.getByTestId('cancel-dialog-no-sms-notice'),
    ).toBeInTheDocument();
  });

  // bughunt M-2: layout stays consistent for DRAFT — both action buttons
  // must remain visible, and the disabled "send-text" variant must
  // explain itself via tooltip rather than disappearing.
  it('keeps both Cancel buttons visible and adds tooltip when DRAFT', () => {
    render(
      <CancelAppointmentDialog
        {...baseProps}
        willNotifyByDefault={false}
      />,
    );

    const noTextBtn = screen.getByTestId('cancel-dialog-cancel-no-text');
    const withTextBtn = screen.getByTestId('cancel-dialog-cancel-with-text');
    expect(noTextBtn).toBeInTheDocument();
    expect(withTextBtn).toBeInTheDocument();
    expect(withTextBtn).toBeDisabled();
    expect(withTextBtn).toHaveAttribute(
      'title',
      'Draft was never sent, no text needed.',
    );
  });

  it('disables "Cancel & text customer" when the customer has no phone', () => {
    render(
      <CancelAppointmentDialog {...baseProps} customerPhone={null} />,
    );

    expect(
      screen.getByTestId('cancel-dialog-cancel-with-text'),
    ).toBeDisabled();
  });

  it('disables all confirm actions while isLoading', () => {
    render(<CancelAppointmentDialog {...baseProps} isLoading={true} />);

    expect(screen.getByTestId('cancel-dialog-keep')).toBeDisabled();
    expect(screen.getByTestId('cancel-dialog-cancel-no-text')).toBeDisabled();
    expect(screen.getByTestId('cancel-dialog-cancel-with-text')).toBeDisabled();
  });
});
