import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourceScheduleView } from './ResourceScheduleView';
import type { ResourceSchedule } from '../types';

const schedule: ResourceSchedule = {
  date: '2026-02-16',
  staff_id: 'r1',
  staff_name: 'Mike D.',
  total_drive_minutes: 45,
  jobs: [
    {
      id: 'j1',
      job_type: 'Spring Opening',
      address: '123 Main St',
      customer_name: 'Smith',
      estimated_duration_minutes: 90,
      eta: '8:00 AM',
      status: 'scheduled',
      notes: null,
      gate_code: '1234',
      requires_special_prep: false,
      route_order: 1,
    },
    {
      id: 'j2',
      job_type: 'Maintenance',
      address: '456 Oak Ave',
      customer_name: 'Jones',
      estimated_duration_minutes: 60,
      eta: '10:00 AM',
      status: 'in_progress',
      notes: 'Check zone 5',
      gate_code: null,
      requires_special_prep: true,
      route_order: 2,
    },
  ],
};

describe('ResourceScheduleView', () => {
  it('renders with data-testid="resource-schedule-view"', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByTestId('resource-schedule-view')).toBeInTheDocument();
  });

  it('shows date and total drive time', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('Today\'s Route — 2026-02-16')).toBeInTheDocument();
    expect(screen.getByText('45 min drive')).toBeInTheDocument();
  });

  it('renders route cards keyed by route_order with the data-job-id payload', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    const card1 = screen.getByTestId('route-card-1');
    const card2 = screen.getByTestId('route-card-2');
    expect(card1).toBeInTheDocument();
    expect(card2).toBeInTheDocument();
    expect(card1.getAttribute('data-job-id')).toBe('j1');
    expect(card2.getAttribute('data-job-id')).toBe('j2');
  });

  it('shows job type, customer name, address, and ETA', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('Spring Opening')).toBeInTheDocument();
    expect(screen.getByText('Smith')).toBeInTheDocument();
    expect(screen.getByText('123 Main St')).toBeInTheDocument();
    expect(screen.getByText('ETA 8:00 AM')).toBeInTheDocument();
  });

  it('shows gate code when present', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('Gate: 1234')).toBeInTheDocument();
  });

  it('shows special prep warning when requires_special_prep', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('⚠ Special prep required')).toBeInTheDocument();
  });

  it('shows notes when present', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('Check zone 5')).toBeInTheDocument();
  });

  it('shows route order numbers', () => {
    render(<ResourceScheduleView schedule={schedule} />);
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows empty state when no jobs', () => {
    render(<ResourceScheduleView schedule={{ ...schedule, jobs: [] }} />);
    expect(screen.getByText('No jobs scheduled.')).toBeInTheDocument();
  });
});
