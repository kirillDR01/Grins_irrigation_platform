import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MobileJobCard } from './MobileJobCard';
import type { Appointment, AppointmentStatus } from '@/features/schedule/types';

function makeAppointment(overrides: Partial<Appointment> = {}): Appointment {
  return {
    id: 'appt-1',
    job_id: 'job-1',
    staff_id: 'staff-1',
    scheduled_date: '2026-05-01',
    time_window_start: '10:30:00',
    time_window_end: '12:00:00',
    status: 'scheduled' as AppointmentStatus,
    arrived_at: null,
    en_route_at: null,
    completed_at: null,
    notes: null,
    route_order: null,
    estimated_arrival: null,
    created_at: '2026-04-30T00:00:00Z',
    updated_at: '2026-04-30T00:00:00Z',
    job_type: 'Spring Startup',
    customer_name: 'Jane Doe',
    staff_name: 'Vas Grin',
    service_agreement_id: null,
    priority_level: null,
    property_summary: {
      address: '12345 Eden Way',
      city: 'Eden Prairie',
      state: 'MN',
      zip_code: '55344',
      zone_count: 8,
      system_type: 'city_water',
    },
    ...overrides,
  };
}

describe('MobileJobCard', () => {
  let onOpen: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onOpen = vi.fn();
    vi.spyOn(window, 'open').mockImplementation(() => null);
  });

  it('renders the upcoming state with Navigate + Job details actions', () => {
    render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'scheduled' })}
        onOpen={onOpen}
      />
    );
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('Navigate')).toBeInTheDocument();
    expect(screen.getByText('Job details')).toBeInTheDocument();
    expect(screen.queryByText('NOW · IN PROGRESS')).not.toBeInTheDocument();
  });

  it('renders the current state with NOW · IN PROGRESS pill', () => {
    render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'in_progress' })}
        onOpen={onOpen}
      />
    );
    expect(screen.getByText('NOW · IN PROGRESS')).toBeInTheDocument();
    expect(screen.queryByText('Navigate')).not.toBeInTheDocument();
  });

  it('renders the complete state with COMPLETE banner and no Navigate', () => {
    render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'completed' })}
        onOpen={onOpen}
      />
    );
    // The COMPLETE pill renders twice: once next to the time, once as the banner.
    expect(screen.getAllByText('COMPLETE').length).toBeGreaterThan(0);
    expect(screen.queryByText('Navigate')).not.toBeInTheDocument();
  });

  it('returns null for hidden statuses (cancelled / no_show)', () => {
    const { container } = render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'cancelled' })}
        onOpen={onOpen}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('fires onOpen when the card body is clicked', async () => {
    const user = userEvent.setup();
    render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'scheduled' })}
        onOpen={onOpen}
      />
    );
    const card = screen.getByTestId('mobile-job-card-upcoming');
    await user.click(card);
    expect(onOpen).toHaveBeenCalledWith('appt-1');
  });

  it('does NOT fire onOpen when Navigate is clicked (stopPropagation)', async () => {
    const user = userEvent.setup();
    render(
      <MobileJobCard
        appointment={makeAppointment({ status: 'scheduled' })}
        onOpen={onOpen}
      />
    );
    await user.click(screen.getByText('Navigate'));
    expect(onOpen).not.toHaveBeenCalled();
    expect(window.open).toHaveBeenCalledWith(
      expect.stringContaining('maps'),
      '_blank',
      'noopener,noreferrer'
    );
  });

  it('omits the address block when property_summary is null', () => {
    render(
      <MobileJobCard
        appointment={makeAppointment({
          status: 'scheduled',
          property_summary: null,
        })}
        onOpen={onOpen}
      />
    );
    expect(screen.queryByText(/Eden Prairie/)).not.toBeInTheDocument();
    expect(screen.queryByText(/zones/)).not.toBeInTheDocument();
  });
});
