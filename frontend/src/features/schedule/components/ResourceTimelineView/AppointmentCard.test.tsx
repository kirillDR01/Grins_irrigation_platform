/**
 * AppointmentCard tests — exercise the icon-rendering matrix and the
 * drag/click event handlers.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AppointmentCard } from './AppointmentCard';
import type { Appointment } from '../../types';

vi.mock('../SendConfirmationButton', () => ({
  SendConfirmationButton: () => (
    <div data-testid="send-confirmation-button" />
  ),
}));

const baseAppointment: Appointment = {
  id: 'appt-1',
  job_id: 'job-1',
  staff_id: 'staff-1',
  scheduled_date: '2026-04-30',
  time_window_start: '08:00:00',
  time_window_end: '09:30:00',
  status: 'confirmed',
  arrived_at: null,
  en_route_at: null,
  completed_at: null,
  notes: null,
  route_order: null,
  estimated_arrival: null,
  created_at: '2026-04-29T00:00:00Z',
  updated_at: '2026-04-29T00:00:00Z',
  job_type: 'Spring opening',
  customer_name: 'Henderson',
  staff_name: 'Mike Davis',
  service_agreement_id: null,
  priority_level: null,
  reply_state: null,
};

const baseProps = {
  variant: 'stacked' as const,
  onAppointmentClick: vi.fn(),
};

describe('AppointmentCard — icon matrix', () => {
  it('renders no icons when no flags are set', () => {
    render(<AppointmentCard appointment={baseAppointment} {...baseProps} />);
    expect(screen.queryByTestId('card-icon-priority')).not.toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-no-reply')).not.toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-reschedule')).not.toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-prepaid')).not.toBeInTheDocument();
  });

  it('renders only star when priority_level > 0', () => {
    render(
      <AppointmentCard
        appointment={{ ...baseAppointment, priority_level: 3 }}
        {...baseProps}
      />
    );
    expect(screen.getByTestId('card-icon-priority')).toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-no-reply')).not.toBeInTheDocument();
  });

  it('omits the star when priority_level === 0', () => {
    render(
      <AppointmentCard
        appointment={{ ...baseAppointment, priority_level: 0 }}
        {...baseProps}
      />
    );
    expect(screen.queryByTestId('card-icon-priority')).not.toBeInTheDocument();
  });

  it('renders the no-reply bell when has_no_reply_flag', () => {
    render(
      <AppointmentCard
        appointment={{
          ...baseAppointment,
          reply_state: {
            has_no_reply_flag: true,
            has_pending_reschedule: false,
            customer_opted_out: false,
            has_unrecognized_reply: false,
            last_reminder_sent_at: null,
          },
        }}
        {...baseProps}
      />
    );
    expect(screen.getByTestId('card-icon-no-reply')).toBeInTheDocument();
  });

  it('renders the gem when service_agreement_id is set', () => {
    render(
      <AppointmentCard
        appointment={{ ...baseAppointment, service_agreement_id: 'sa-1' }}
        {...baseProps}
      />
    );
    expect(screen.getByTestId('card-icon-prepaid')).toBeInTheDocument();
  });

  it('caps to 3 icons by severity (drops prepaid first)', () => {
    render(
      <AppointmentCard
        appointment={{
          ...baseAppointment,
          priority_level: 2,
          service_agreement_id: 'sa-1',
          reply_state: {
            has_no_reply_flag: true,
            has_pending_reschedule: true,
            customer_opted_out: false,
            has_unrecognized_reply: false,
            last_reminder_sent_at: null,
          },
        }}
        {...baseProps}
      />
    );
    expect(screen.getByTestId('card-icon-priority')).toBeInTheDocument();
    expect(screen.getByTestId('card-icon-no-reply')).toBeInTheDocument();
    expect(screen.getByTestId('card-icon-reschedule')).toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-prepaid')).not.toBeInTheDocument();
  });
});

describe('AppointmentCard — interactions', () => {
  it('renders SendConfirmationButton in place of icons for draft status', () => {
    render(
      <AppointmentCard
        appointment={{
          ...baseAppointment,
          status: 'draft',
          priority_level: 5,
        }}
        {...baseProps}
      />
    );
    expect(screen.getByTestId('send-confirmation-button')).toBeInTheDocument();
    expect(screen.queryByTestId('card-icon-priority')).not.toBeInTheDocument();
  });

  it('fires onAppointmentClick with the appointment id on click', () => {
    const onClick = vi.fn();
    render(
      <AppointmentCard
        appointment={baseAppointment}
        variant="stacked"
        onAppointmentClick={onClick}
      />
    );
    fireEvent.click(screen.getByTestId('appt-card-appt-1'));
    expect(onClick).toHaveBeenCalledWith('appt-1');
  });

  it('serializes a DragPayload onto dataTransfer on dragStart', () => {
    render(<AppointmentCard appointment={baseAppointment} {...baseProps} />);
    const card = screen.getByTestId('appt-card-appt-1');
    const setData = vi.fn();
    fireEvent.dragStart(card, {
      dataTransfer: { setData, effectAllowed: '' },
    });
    expect(setData).toHaveBeenCalledTimes(1);
    const [mime, raw] = setData.mock.calls[0]!;
    expect(mime).toBe('application/json');
    const payload = JSON.parse(raw as string);
    expect(payload).toMatchObject({
      appointmentId: 'appt-1',
      originStaffId: 'staff-1',
      originDate: '2026-04-30',
      originStartTime: '08:00:00',
      originEndTime: '09:30:00',
    });
  });

  it('paints the clear-day red ring when isOnSelectedDate', () => {
    render(
      <AppointmentCard
        appointment={baseAppointment}
        isOnSelectedDate
        {...baseProps}
      />
    );
    const card = screen.getByTestId('appt-card-appt-1');
    expect(card.className).toContain('animate-pulse');
  });
});
