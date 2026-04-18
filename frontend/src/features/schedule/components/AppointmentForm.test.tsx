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

// Mock customer API for InternalNotesCard
vi.mock('@/features/customers/api/customerApi', () => ({
  customerApi: {
    get: vi.fn().mockResolvedValue({
      id: 'cust-001',
      first_name: 'Test',
      last_name: 'Customer',
      phone: '6125551234',
      internal_notes: 'Customer notes from appointment',
      properties: [{ is_primary: true, address: '123 Main St', city: 'Minneapolis', state: 'MN', zip_code: '55401' }],
    }),
  },
}));

// Mock job API for InternalNotesCard
vi.mock('@/features/jobs/api/jobApi', () => ({
  jobApi: {
    get: vi.fn().mockResolvedValue({
      id: '123e4567-e89b-12d3-a456-426614174001',
      customer_id: 'cust-001',
      job_type: 'install',
    }),
  },
}));

const mockUpdateCustomerMutateAsync = vi.fn().mockResolvedValue(undefined);
vi.mock('@/features/customers/hooks', () => ({
  useUpdateCustomer: () => ({
    mutateAsync: mockUpdateCustomerMutateAsync,
    isPending: false,
  }),
  customerKeys: {
    all: ['customers'],
    lists: () => ['customers', 'list'],
    detail: (id: string) => ['customers', 'detail', id],
  },
}));

const mockInvalidateAfterCustomerInternalNotesSave = vi.fn();
vi.mock('@/shared/utils/invalidationHelpers', () => ({
  invalidateAfterCustomerInternalNotesSave: (...args: unknown[]) =>
    mockInvalidateAfterCustomerInternalNotesSave(...args),
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
  en_route_at: null,
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
    expect(screen.getByTestId('job-combobox-trigger')).toBeInTheDocument();
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

    // The job combobox trigger should be disabled
    const jobSelect = screen.getByTestId('job-combobox-trigger');
    expect(jobSelect).toBeDisabled();
  });

  // ---- InternalNotesCard (internal-notes-simplification Req 4, 9) ----

  describe('InternalNotesCard', () => {
    beforeEach(() => {
      mockUpdateCustomerMutateAsync.mockClear();
      mockInvalidateAfterCustomerInternalNotesSave.mockClear();
    });

    it('renders InternalNotesCard for job appointments in edit mode', async () => {
      render(<AppointmentForm appointment={mockAppointment} />, {
        wrapper: createWrapper(),
      });

      // Wait for customer data to load (fetched via job_id → customer_id)
      await waitFor(() => {
        expect(screen.getByTestId('appointment-notes-editor')).toBeInTheDocument();
      });

      expect(screen.getByText('Customer notes from appointment')).toBeInTheDocument();
    });

    it('does not render InternalNotesCard for new appointments', () => {
      render(<AppointmentForm />, { wrapper: createWrapper() });

      // InternalNotesCard should not be present for new appointments
      expect(screen.queryByTestId('appointment-notes-editor')).not.toBeInTheDocument();
    });

    it('Save PATCHes the customer and triggers invalidation', async () => {
      const user = userEvent.setup();

      render(<AppointmentForm appointment={mockAppointment} />, {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(screen.getByTestId('appointment-edit-notes-btn')).toBeInTheDocument();
      });

      await user.click(screen.getByTestId('appointment-edit-notes-btn'));

      const textarea = screen.getByTestId('appointment-internal-notes-textarea');
      await user.clear(textarea);
      await user.type(textarea, 'Updated from appointment');

      await user.click(screen.getByTestId('appointment-save-notes-btn'));

      await waitFor(() => {
        expect(mockUpdateCustomerMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            id: 'cust-001',
            data: { internal_notes: 'Updated from appointment' },
          })
        );
      });

      await waitFor(() => {
        expect(mockInvalidateAfterCustomerInternalNotesSave).toHaveBeenCalledWith(
          expect.anything(),
          'cust-001'
        );
      });
    });
  });
});
