/**
 * Tests for SendConfirmationButton (H-8).
 *
 * Verifies the button is enabled only for DRAFT appointments. For every
 * other ``AppointmentStatus`` the button renders disabled with a
 * "Confirmation already sent" tooltip, so users don't click into a 422
 * backend error.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SendConfirmationButton } from './SendConfirmationButton';
import type { Appointment, AppointmentStatus } from '../types';

vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    sendConfirmation: vi.fn(),
  },
}));

function makeAppointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: '11111111-2222-3333-4444-555555555555',
    job_id: '66666666-7777-8888-9999-aaaaaaaaaaaa',
    staff_id: 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff',
    scheduled_date: '2026-04-20',
    time_window_start: '09:00:00',
    time_window_end: '11:00:00',
    status: 'draft',
    arrived_at: null,
    en_route_at: null,
    completed_at: null,
    notes: null,
    route_order: 1,
    estimated_arrival: null,
    created_at: '2026-04-16T10:00:00Z',
    updated_at: '2026-04-16T10:00:00Z',
    job_type: 'Spring Turn-On',
    customer_name: 'Jane Smith',
    staff_name: 'Bob',
    service_agreement_id: null,
    ...overrides,
  };
}

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe('SendConfirmationButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders enabled for DRAFT with customer-specific tooltip', () => {
    const appointment = makeAppointment({ status: 'draft', customer_name: 'Jane Smith' });
    renderWithQuery(<SendConfirmationButton appointment={appointment} />);

    const btn = screen.getByTestId(`send-confirmation-btn-${appointment.id}`);
    expect(btn).toBeEnabled();
    expect(btn).toHaveAttribute('title', 'Send confirmation SMS to Jane Smith');
    expect(btn).toHaveAttribute('aria-label', 'Send confirmation SMS to Jane Smith');
  });

  it('renders enabled compact variant for DRAFT with customer-specific tooltip', () => {
    const appointment = makeAppointment({ status: 'draft', customer_name: 'Jane Smith' });
    renderWithQuery(<SendConfirmationButton appointment={appointment} compact />);

    const btn = screen.getByTestId(`send-confirmation-icon-${appointment.id}`);
    expect(btn).toBeEnabled();
    expect(btn).toHaveAttribute('title', 'Send confirmation SMS to Jane Smith');
    expect(btn).toHaveAttribute('aria-label', 'Send confirmation SMS to Jane Smith');
  });

  it('renders disabled with "Confirmation already sent" tooltip for SCHEDULED', () => {
    const appointment = makeAppointment({ status: 'scheduled' });
    renderWithQuery(<SendConfirmationButton appointment={appointment} />);

    const btn = screen.getByTestId(`send-confirmation-btn-${appointment.id}`);
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'Confirmation already sent');
    expect(btn).toHaveAttribute('aria-label', 'Confirmation already sent');
  });

  it.each<AppointmentStatus>([
    'pending',
    'scheduled',
    'confirmed',
    'en_route',
    'in_progress',
    'completed',
    'cancelled',
    'no_show',
  ])('renders disabled for non-draft status %s (full variant)', (status) => {
    const appointment = makeAppointment({ status });
    renderWithQuery(<SendConfirmationButton appointment={appointment} />);

    const btn = screen.getByTestId(`send-confirmation-btn-${appointment.id}`);
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'Confirmation already sent');
  });

  it.each<AppointmentStatus>([
    'pending',
    'scheduled',
    'confirmed',
    'en_route',
    'in_progress',
    'completed',
    'cancelled',
    'no_show',
  ])('renders disabled for non-draft status %s (compact variant)', (status) => {
    const appointment = makeAppointment({ status });
    renderWithQuery(<SendConfirmationButton appointment={appointment} compact />);

    const btn = screen.getByTestId(`send-confirmation-icon-${appointment.id}`);
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('title', 'Confirmation already sent');
  });

  it('falls back to "customer" when customer_name is null', () => {
    const appointment = makeAppointment({ status: 'draft', customer_name: null });
    renderWithQuery(<SendConfirmationButton appointment={appointment} />);

    const btn = screen.getByTestId(`send-confirmation-btn-${appointment.id}`);
    expect(btn).toHaveAttribute('title', 'Send confirmation SMS to customer');
  });
});
