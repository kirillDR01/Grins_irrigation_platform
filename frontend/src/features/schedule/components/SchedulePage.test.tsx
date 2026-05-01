import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { SchedulePage } from './SchedulePage';

vi.mock('@/shared/hooks', async () => {
  const actual =
    await vi.importActual<typeof import('@/shared/hooks')>('@/shared/hooks');
  return { ...actual, useMediaQuery: vi.fn() };
});

import { useMediaQuery } from '@/shared/hooks';
const mockUseMediaQuery = vi.mocked(useMediaQuery);

// Mock the child components to avoid complex setup
vi.mock('./ResourceTimelineView', () => ({
  ResourceTimelineView: ({
    onDateClick,
    onEventClick,
  }: {
    onDateClick?: (staffId: string | null, date: Date) => void;
    onEventClick?: (id: string) => void;
  }) => (
    <div data-testid="calendar-view">
      <button onClick={() => onDateClick?.(null, new Date())}>Click Date</button>
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

vi.mock('./AppointmentModal', () => ({
  AppointmentModal: ({ appointmentId, open, onClose }: { appointmentId: string; open: boolean; onClose?: () => void }) => {
    if (!open) return null;
    return (
      <div data-testid="appointment-detail">
        <span>Appointment: {appointmentId}</span>
        <button onClick={onClose}>Close</button>
      </div>
    );
  },
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
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(false); // default: desktop
  });

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

    expect(screen.getByTestId('view-calendar')).toBeInTheDocument();
    expect(screen.getByTestId('view-list')).toBeInTheDocument();
  });

  it('switches to list view when tab is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('view-list'));

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
    await user.click(screen.getByTestId('view-list'));

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

describe('SchedulePage — mobile action bar', () => {
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(true); // mobile
  });

  it('renders the primary "+ New Appointment" button at all viewports', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('add-appointment-btn')).toBeInTheDocument();
  });

  it('renders the overflow menu trigger on mobile', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('schedule-action-overflow-btn')).toBeInTheDocument();
  });

  it('does NOT render Add Jobs / Pick Jobs / inline view-toggle on mobile', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });
    expect(screen.queryByTestId('add-jobs-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('pick-jobs-btn')).not.toBeInTheDocument();
    expect(screen.queryByTestId('schedule-view-toggle')).not.toBeInTheDocument();
  });

  it('opens the overflow menu and shows view-toggle items', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('schedule-action-overflow-btn'));

    expect(
      await screen.findByTestId('overflow-menu-item-view-calendar'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('overflow-menu-item-view-list')).toBeInTheDocument();
  });

  it('switches viewMode when an overflow menu view item is clicked', async () => {
    const user = userEvent.setup();
    render(<SchedulePage />, { wrapper: createWrapper() });

    await user.click(screen.getByTestId('schedule-action-overflow-btn'));
    await user.click(await screen.findByTestId('overflow-menu-item-view-list'));

    expect(await screen.findByTestId('appointment-list')).toBeInTheDocument();
  });
});

describe('SchedulePage — desktop action bar (regression)', () => {
  beforeEach(() => {
    mockUseMediaQuery.mockReturnValue(false); // desktop
  });

  it('renders all action buttons inline at lg+ (no overflow menu)', () => {
    render(<SchedulePage />, { wrapper: createWrapper() });
    expect(screen.getByTestId('add-appointment-btn')).toBeInTheDocument();
    expect(screen.getByTestId('add-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('pick-jobs-btn')).toBeInTheDocument();
    expect(screen.getByTestId('schedule-view-toggle')).toBeInTheDocument();
    expect(
      screen.queryByTestId('schedule-action-overflow-btn'),
    ).not.toBeInTheDocument();
  });
});
