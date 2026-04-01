/**
 * Tests for ScheduleOverviewEnhanced component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import {
  ScheduleOverviewEnhanced,
  type ScheduleOverviewEnhancedProps,
} from './ScheduleOverviewEnhanced';

const defaultProps: ScheduleOverviewEnhancedProps = {
  weekTitle: 'Schedule Overview — Week of Feb 16',
  resources: [
    { id: 'r1', name: 'Mike D.', role: 'Senior Tech', utilizationPct: 87 },
    { id: 'r2', name: 'Sarah K.', role: 'Tech', utilizationPct: 62 },
  ],
  days: [
    { date: '2025-02-16', label: 'Mon 2/16', jobCount: 10 },
    { date: '2025-02-17', label: 'Tue 2/17', jobCount: 8 },
  ],
  cells: [
    {
      resourceId: 'r1',
      day: '2025-02-16',
      jobs: [
        {
          id: 'j1',
          jobType: 'spring_opening',
          jobTypeName: 'Spring Opening',
          timeWindow: '8:00 – 9:30 AM',
          customerName: 'Smith',
          address: '123 Main St',
          isVip: true,
          hasConflict: false,
          status: 'confirmed',
        },
      ],
    },
    {
      resourceId: 'r1',
      day: '2025-02-17',
      jobs: [
        {
          id: 'j2',
          jobType: 'maintenance',
          jobTypeName: 'Maintenance',
          timeWindow: '10:00 – 11:00 AM',
          customerName: 'Jones',
          address: '456 Oak Ave',
          isVip: false,
          hasConflict: true,
          status: 'flagged',
        },
      ],
    },
  ],
  capacityData: [
    { day: '2025-02-16', utilization: 85 },
    { day: '2025-02-17', utilization: 70 },
  ],
};

describe('ScheduleOverviewEnhanced', () => {
  it('renders with data-testid', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByTestId('schedule-overview-enhanced')).toBeInTheDocument();
  });

  it('renders the week title', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByText('Schedule Overview — Week of Feb 16')).toBeInTheDocument();
  });

  it('renders resource rows with data-testid', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByTestId('resource-row-r1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-row-r2')).toBeInTheDocument();
  });

  it('renders resource names and utilization', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByText('Mike D.')).toBeInTheDocument();
    expect(screen.getByText(/87% utilized/)).toBeInTheDocument();
  });

  it('renders day column headers with job counts', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByText('Mon 2/16')).toBeInTheDocument();
    expect(screen.getByText('10 jobs')).toBeInTheDocument();
  });

  it('renders job cards with data-testid', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByTestId('job-card-j1')).toBeInTheDocument();
    expect(screen.getByTestId('job-card-j2')).toBeInTheDocument();
  });

  it('renders VIP indicator on VIP jobs', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    const jobCard = screen.getByTestId('job-card-j1');
    expect(jobCard).toHaveTextContent('⭐');
  });

  it('renders conflict indicator on conflicting jobs', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    const jobCard = screen.getByTestId('job-card-j2');
    expect(jobCard).toHaveTextContent('⚠️');
  });

  it('renders Day/Week/Month toggle buttons', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByText('day')).toBeInTheDocument();
    expect(screen.getByText('week')).toBeInTheDocument();
    expect(screen.getByText('month')).toBeInTheDocument();
  });

  it('calls onViewModeChange when toggle is clicked', async () => {
    const onViewModeChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ScheduleOverviewEnhanced {...defaultProps} onViewModeChange={onViewModeChange} />
    );
    await user.click(screen.getByText('day'));
    expect(onViewModeChange).toHaveBeenCalledWith('day');
  });

  it('renders + New Job button', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByText('+ New Job')).toBeInTheDocument();
  });

  it('renders the CapacityHeatMap at the bottom', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
  });

  it('renders job type color legend', () => {
    render(<ScheduleOverviewEnhanced {...defaultProps} />);
    // "Spring Opening" and "Maintenance" appear in both legend and job cards
    expect(screen.getAllByText('Spring Opening').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Fall Closing')).toBeInTheDocument();
    expect(screen.getByText('New Build')).toBeInTheDocument();
    expect(screen.getByText('Backflow Test')).toBeInTheDocument();
  });
});
