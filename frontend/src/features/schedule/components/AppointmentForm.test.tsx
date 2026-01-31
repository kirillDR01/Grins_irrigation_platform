import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AppointmentForm } from './AppointmentForm';
import type { Appointment } from '../types';

// Mock the API
vi.mock('../api/appointmentApi', () => ({
  appointmentApi: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

const mockAppointment: Appointment = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  job_id: '123e4567-e89b-12d3-a456-426614174001',
  staff_id: '123e4567-e89b-12d3-a456-426614174010',
  scheduled_date: '2025-01-25',
  time_window_start: '09:00:00',
  time_window_end: '11:00:00',
  status: 'pending',
  arrived_at: null,
  completed_at: null,
  notes: 'Test notes',
  route_order: 1,
  estimated_arrival: null,
  job_type: null,
  customer_name: null,
  staff_name: null,
  created_at: '2025-01-20T10:00:00Z',
  updated_at: '2025-01-20T10:00:00Z',
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
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

describe('AppointmentForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders form with empty fields for new appointment', () => {
    render(<AppointmentForm />, { wrapper: createWrapper() });

    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();
    expect(screen.getByTestId('job-select')).toBeInTheDocument();
    expect(screen.getByTestId('staff-select')).toBeInTheDocument();
    expect(screen.getByTestId('date-input')).toBeInTheDocument();
    expect(screen.getByTestId('start-time-input')).toBeInTheDocument();
    expect(screen.getByTestId('end-time-input')).toBeInTheDocument();
    expect(screen.getByTestId('notes-input')).toBeInTheDocument();
    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Create Appointment');
  });

  it('renders form with populated fields for editing', () => {
    render(<AppointmentForm appointment={mockAppointment} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();
    expect(screen.getByTestId('date-input')).toHaveValue('2025-01-25');
    expect(screen.getByTestId('start-time-input')).toHaveValue('09:00');
    expect(screen.getByTestId('end-time-input')).toHaveValue('11:00');
    expect(screen.getByTestId('notes-input')).toHaveValue('Test notes');
    expect(screen.getByTestId('submit-btn')).toHaveTextContent('Update Appointment');
  });

  it('pre-fills date when initialDate is provided', () => {
    // Use a date that won't have timezone issues by creating it with explicit local time
    const initialDate = new Date(2025, 1, 15); // Feb 15, 2025 in local time
    render(<AppointmentForm initialDate={initialDate} />, {
      wrapper: createWrapper(),
    });

    // Format the expected date the same way the component does
    const expectedDate = initialDate.toISOString().split('T')[0];
    expect(screen.getByTestId('date-input')).toHaveValue(expectedDate);
  });

  it('shows validation error for missing job', async () => {
    const user = userEvent.setup();
    render(<AppointmentForm />, { wrapper: createWrapper() });

    // Fill required fields except job
    await user.type(screen.getByTestId('date-input'), '2025-01-25');

    // Submit
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Please select a valid job')).toBeInTheDocument();
    });
  });

  it('shows validation error for missing staff', async () => {
    const user = userEvent.setup();
    render(<AppointmentForm />, { wrapper: createWrapper() });

    // Fill required fields except staff
    await user.type(screen.getByTestId('date-input'), '2025-01-25');

    // Submit
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Please select a valid staff member')).toBeInTheDocument();
    });
  });

  it('shows validation error for missing date', async () => {
    const user = userEvent.setup();
    render(<AppointmentForm />, { wrapper: createWrapper() });

    // Clear the date input
    const dateInput = screen.getByTestId('date-input');
    await user.clear(dateInput);

    // Submit
    await user.click(screen.getByTestId('submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Date is required')).toBeInTheDocument();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();

    render(<AppointmentForm onCancel={onCancel} />, { wrapper: createWrapper() });

    await user.click(screen.getByText('Cancel'));

    expect(onCancel).toHaveBeenCalled();
  });

  it('renders time inputs with default values', () => {
    render(<AppointmentForm />, { wrapper: createWrapper() });

    expect(screen.getByTestId('start-time-input')).toHaveValue('08:00');
    expect(screen.getByTestId('end-time-input')).toHaveValue('10:00');
  });

  it('allows entering notes', async () => {
    const user = userEvent.setup();
    render(<AppointmentForm />, { wrapper: createWrapper() });

    const notesInput = screen.getByTestId('notes-input');
    await user.type(notesInput, 'Test appointment notes');

    expect(notesInput).toHaveValue('Test appointment notes');
  });

  it('disables job selection when editing', () => {
    render(<AppointmentForm appointment={mockAppointment} />, {
      wrapper: createWrapper(),
    });

    // The job select trigger should be disabled
    const jobSelect = screen.getByTestId('job-select');
    expect(jobSelect).toHaveAttribute('data-disabled');
  });
});
