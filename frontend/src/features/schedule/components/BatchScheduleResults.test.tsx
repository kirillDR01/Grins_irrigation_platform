/**
 * Tests for BatchScheduleResults component.
 * Validates: Requirements 30.6, 30.7, 30.8
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import {
  BatchScheduleResults,
  type BatchWeek,
  type RankedJob,
} from './BatchScheduleResults';

const sampleWeeks: BatchWeek[] = [
  {
    weekStart: '2025-03-03',
    weekLabel: 'Week of Mar 3',
    utilizationPct: 82,
    jobs: [
      {
        id: 'bj1',
        jobType: 'Spring Opening',
        customerName: 'Smith',
        zone: 'North',
        resourceName: 'Mike D.',
        date: '2025-03-04',
        revenue: 350,
      },
      {
        id: 'bj2',
        jobType: 'Maintenance',
        customerName: 'Jones',
        zone: 'South',
        resourceName: 'Sarah K.',
        date: '2025-03-05',
      },
    ],
  },
  {
    weekStart: '2025-03-10',
    weekLabel: 'Week of Mar 10',
    utilizationPct: 55,
    jobs: [],
  },
];

const sampleRankedJobs: RankedJob[] = [
  {
    id: 'rj1',
    jobType: 'New Build',
    customerName: 'Williams',
    projectedRevenue: 1200,
    revenueImpact: '+$1,200',
  },
];

describe('BatchScheduleResults', () => {
  it('renders with data-testid', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByTestId('batch-schedule-results')).toBeInTheDocument();
  });

  it('displays total jobs and week count', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByText('2 jobs scheduled across 2 weeks')).toBeInTheDocument();
  });

  it('renders week labels', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByText('Week of Mar 3')).toBeInTheDocument();
    expect(screen.getByText('Week of Mar 10')).toBeInTheDocument();
  });

  it('renders job list within weeks', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByText('Smith')).toBeInTheDocument();
    expect(screen.getByText('Jones')).toBeInTheDocument();
  });

  it('displays revenue when available', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByText('$350')).toBeInTheDocument();
  });

  it('renders notification button when notifications are ready', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={5}
      />
    );
    expect(screen.getByText('Send 5 Notifications')).toBeInTheDocument();
  });

  it('hides notification button when none ready', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.queryByText(/Send.*Notifications/)).not.toBeInTheDocument();
  });

  it('renders ranked jobs with assign buttons', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
        rankedJobs={sampleRankedJobs}
      />
    );
    expect(screen.getByText('Williams')).toBeInTheDocument();
    expect(screen.getByText('+$1,200')).toBeInTheDocument();
    expect(screen.getByText('Assign')).toBeInTheDocument();
  });

  it('calls onAssignJob when assign button is clicked', async () => {
    const onAssignJob = vi.fn();
    const user = userEvent.setup();
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
        rankedJobs={sampleRankedJobs}
        onAssignJob={onAssignJob}
      />
    );
    await user.click(screen.getByText('Assign'));
    expect(onAssignJob).toHaveBeenCalledWith('rj1');
  });

  it('shows utilization color coding per week', () => {
    render(
      <BatchScheduleResults
        weeks={sampleWeeks}
        totalJobsScheduled={2}
        notificationsReady={0}
      />
    );
    expect(screen.getByText('82% utilized')).toBeInTheDocument();
    expect(screen.getByText('55% utilized')).toBeInTheDocument();
  });
});
