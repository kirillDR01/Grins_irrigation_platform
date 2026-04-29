import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ScheduleOverviewEnhanced,
  type OverviewResource,
  type OverviewDay,
} from './ScheduleOverviewEnhanced';
import type { CapacityDay } from './CapacityHeatMap';

const days: OverviewDay[] = [
  { date: '2026-02-16', label: 'Mon 2/16', jobCount: 3 },
  { date: '2026-02-17', label: 'Tue 2/17', jobCount: 2 },
];

const capacityDays: CapacityDay[] = [
  { date: '2026-02-16', label: 'Mon 2/16', utilization: 80 },
  { date: '2026-02-17', label: 'Tue 2/17', utilization: 50 },
];

const resources: OverviewResource[] = [
  {
    id: 'r1',
    name: 'Mike D.',
    title: 'Senior Tech',
    utilization: 87,
    jobsByDate: {
      '2026-02-16': [
        {
          id: 'j1',
          jobTypeName: 'Spring Opening',
          timeStart: '8:00 AM',
          timeEnd: '9:30 AM',
          customerLastName: 'Smith',
          address: '123 Main St',
          isVip: true,
        },
      ],
      '2026-02-17': [],
    },
  },
  {
    id: 'r2',
    name: 'Sarah K.',
    title: 'Mid Tech',
    utilization: 45,
    jobsByDate: { '2026-02-16': [], '2026-02-17': [] },
  },
];

describe('ScheduleOverviewEnhanced', () => {
  it('renders with data-testid="schedule-overview-enhanced"', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByTestId('schedule-overview-enhanced')).toBeInTheDocument();
  });

  it('renders week title', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByText('Week of Feb 16')).toBeInTheDocument();
  });

  it('renders resource rows with correct data-testid', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByTestId('resource-row-r1')).toBeInTheDocument();
    expect(screen.getByTestId('resource-row-r2')).toBeInTheDocument();
  });

  it('renders job cards with correct data-testid', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByTestId('job-card-j1')).toBeInTheDocument();
  });

  it('shows VIP star icon for VIP jobs', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    const jobCard = screen.getByTestId('job-card-j1');
    expect(jobCard).toHaveTextContent('⭐');
  });

  it('renders capacity heat map', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByTestId('capacity-heat-map')).toBeInTheDocument();
  });

  it('calls onAddResource when + New Job button clicked', () => {
    const onAdd = vi.fn();
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
        onAddResource={onAdd}
      />
    );
    fireEvent.click(screen.getByText('+ New Job'));
    expect(onAdd).toHaveBeenCalledOnce();
  });

  it('calls onRemoveResource when remove button clicked', () => {
    const onRemove = vi.fn();
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
        onRemoveResource={onRemove}
      />
    );
    const removeButtons = screen.getAllByTitle('Remove resource');
    fireEvent.click(removeButtons[0]);
    expect(onRemove).toHaveBeenCalledWith('r1');
  });

  it('calls onViewModeChange when view mode button clicked', () => {
    const onChange = vi.fn();
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
        onViewModeChange={onChange}
      />
    );
    fireEvent.click(screen.getByText('day'));
    expect(onChange).toHaveBeenCalledWith('day');
  });

  it('renders day column headers with job counts', () => {
    render(
      <ScheduleOverviewEnhanced
        weekTitle="Week of Feb 16"
        resources={resources}
        days={days}
        capacityDays={capacityDays}
      />
    );
    expect(screen.getByText('3 jobs')).toBeInTheDocument();
    expect(screen.getByText('2 jobs')).toBeInTheDocument();
  });
});
