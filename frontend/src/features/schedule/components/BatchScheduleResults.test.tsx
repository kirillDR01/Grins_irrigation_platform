import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  BatchScheduleResults,
  type BatchWeekSummary,
  type RankedJob,
} from './BatchScheduleResults';

const weeks: BatchWeekSummary[] = [
  {
    weekLabel: 'Week of Feb 16',
    startDate: '2026-02-16',
    jobCount: 18,
    utilization: 85,
    zones: ['North', 'East'],
    resources: ['Mike D.', 'Sarah K.'],
  },
  {
    weekLabel: 'Week of Feb 23',
    startDate: '2026-02-23',
    jobCount: 5,
    utilization: 40,
    zones: ['South'],
    resources: ['Carlos R.'],
  },
];

const rankedJobs: RankedJob[] = [
  {
    jobId: 'j1',
    customerName: 'Smith',
    address: '123 Main St',
    jobType: 'Spring Opening',
    projectedRevenue: 240,
    revenueImpact: '+$240/hr',
    bestFitResource: 'Mike D.',
    bestFitDate: 'Mon Feb 16',
  },
  {
    jobId: 'j2',
    customerName: 'Jones',
    address: '456 Oak Ave',
    jobType: 'Maintenance',
    projectedRevenue: 120,
    revenueImpact: '+$120/hr',
    bestFitResource: 'Sarah K.',
    bestFitDate: 'Tue Feb 17',
  },
];

describe('BatchScheduleResults', () => {
  it('renders with data-testid="batch-schedule-results"', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={rankedJobs} />);
    expect(screen.getByTestId('batch-schedule-results')).toBeInTheDocument();
  });

  it('renders week summaries', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={rankedJobs} />);
    expect(screen.getByText('Week of Feb 16')).toBeInTheDocument();
    expect(screen.getByText('Week of Feb 23')).toBeInTheDocument();
  });

  it('shows utilization with correct color for >90%', () => {
    const highWeeks: BatchWeekSummary[] = [
      { ...weeks[0], utilization: 95 },
    ];
    render(<BatchScheduleResults weeks={highWeeks} rankedJobs={[]} />);
    const utilEl = screen.getByText('95%');
    expect(utilEl.className).toContain('text-red-600');
  });

  it('shows utilization with correct color for 60–90%', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={[]} />);
    const utilEl = screen.getByText('85%');
    expect(utilEl.className).toContain('text-green-600');
  });

  it('shows utilization with correct color for <60%', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={[]} />);
    const utilEl = screen.getByText('40%');
    expect(utilEl.className).toContain('text-yellow-600');
  });

  it('renders ranked jobs with revenue impact', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={rankedJobs} />);
    expect(screen.getByText('+$240/hr')).toBeInTheDocument();
    expect(screen.getByText('+$120/hr')).toBeInTheDocument();
  });

  it('calls onAssignJob when Assign button clicked', () => {
    const onAssign = vi.fn();
    render(
      <BatchScheduleResults weeks={weeks} rankedJobs={rankedJobs} onAssignJob={onAssign} />
    );
    const assignButtons = screen.getAllByText('Assign');
    fireEvent.click(assignButtons[0]);
    expect(onAssign).toHaveBeenCalledWith('j1');
  });

  it('does not render ranked jobs section when empty', () => {
    render(<BatchScheduleResults weeks={weeks} rankedJobs={[]} />);
    expect(screen.queryByText('Best-Fit Jobs by Revenue Impact')).toBeNull();
  });
});
