import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { SchedulePage } from './SchedulePage';

// Mock the child components to avoid complex setup
vi.mock('./CalendarView', () => ({
  CalendarView: ({ onDateClick, onEventClick }: { onDateClick?: (date: Date) => void; onEventClick?: (id: string) => void }) => (
    <div data-testid="calendar-view">
      <button onClick={() => onDateClick?.(new Date())}>Click Date</button>
      <button onClick={() => onEventClick?.('test-id')}>Click Event</button>
    </div>
  ),
}));

vi.mock('./AppointmentList', () => ({
  AppointmentList: ({ onAppointmentClick }: { onAppointmentClick?: (id: string) => void }) => (
    <div data-testid="appointment-list">
      <button onClick={() => onAppointmentClick?.('test-id')}>Click Appointment</button>
    </div>
  ),
}));

vi.mock('./AppointmentForm', () => ({
  AppointmentForm: ({ onSuccess, onCancel }: { onSuccess?: () => void; onCancel?: () => void }) => (
    <div data-testid="appointment-form">
      <button onClick={onSuccess}>Submit</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

vi.mock('./AppointmentDetail', () => ({
  AppointmentDetail: ({ appointmentId, onClose }: { appointmentId: string; onClose?: () => void }) => (
    <div data-testid="appointment-detail">
      <span>Appointment: {appointmentId}</span>
      <button onClick={onClose}>Close</button>
    </div>
  ),
}));

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

describe('SchedulePage', () => {
  it('renders schedule page with header', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('schedule-page')).toBeInTheDocument();
    expect(screen.getByText('Schedule')).toBeInTheDocument();
    expect(screen.getByText('Manage appointments and view daily/weekly schedules')).toBeInTheDocument();
  });

  it('renders calendar view by default', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('calendar-view')).toBeInTheDocument();
  });

  it('renders view toggle tabs', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('calendar-view-tab')).toBeInTheDocument();
    expect(screen.getByTestId('list-view-tab')).toBeInTheDocument();
  });

  it('switches to list view when tab is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('list-view-tab'));

    expect(screen.getByTestId('appointment-list')).toBeInTheDocument();
  });

  it('renders new appointment button', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });

    expect(screen.getByTestId('add-appointment-btn')).toBeInTheDocument();
    expect(screen.getByText('New Appointment')).toBeInTheDocument();
  });

  it('opens create dialog when new appointment button is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('add-appointment-btn'));

    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();
  });

  it('opens create dialog when date is clicked in calendar', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByText('Click Date'));

    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();
  });

  it('opens detail dialog when event is clicked in calendar', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByText('Click Event'));

    expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
    expect(screen.getByText('Appointment: test-id')).toBeInTheDocument();
  });

  it('opens detail dialog when appointment is clicked in list view', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    // Switch to list view
    await user.click(screen.getByTestId('list-view-tab'));

    // Click appointment
    await user.click(screen.getByText('Click Appointment'));

    expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();
  });

  it('closes create dialog on success', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    // Open dialog
    await user.click(screen.getByTestId('add-appointment-btn'));
    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();

    // Submit form
    await user.click(screen.getByText('Submit'));

    // Dialog should close (form should not be visible)
    expect(screen.queryByTestId('appointment-form')).not.toBeInTheDocument();
  });

  it('closes create dialog on cancel', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    // Open dialog
    await user.click(screen.getByTestId('add-appointment-btn'));
    expect(screen.getByTestId('appointment-form')).toBeInTheDocument();

    // Cancel
    await user.click(screen.getByText('Cancel'));

    // Dialog should close
    expect(screen.queryByTestId('appointment-form')).not.toBeInTheDocument();
  });

  it('closes detail dialog when close is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    // Open detail dialog
    await user.click(screen.getByText('Click Event'));
    expect(screen.getByTestId('appointment-detail')).toBeInTheDocument();

    // Close - use getAllByText and click the first visible button
    const closeButtons = screen.getAllByText('Close');
    // Find the button element (not the sr-only span)
    const closeButton = closeButtons.find(el => el.tagName === 'BUTTON');
    await user.click(closeButton!);

    // Dialog should close
    expect(screen.queryByTestId('appointment-detail')).not.toBeInTheDocument();
  });
});
