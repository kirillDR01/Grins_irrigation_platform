import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  JobStatusBadge,
  getNextStatuses,
  canTransitionTo,
  JOB_STATUS_WORKFLOW,
} from './JobStatusBadge';
import type { JobStatus } from '../types';

describe('JobStatusBadge', () => {
  const allStatuses: JobStatus[] = [
    'to_be_scheduled',
    'scheduled',
    'in_progress',
    'completed',
    'cancelled',
  ];

  describe('rendering', () => {
    it.each(allStatuses)('renders %s status correctly', (status) => {
      render(<JobStatusBadge status={status} />);

      expect(screen.getByTestId(`status-${status}`)).toBeInTheDocument();
    });

    it('renders with correct label for to_be_scheduled status', () => {
      render(<JobStatusBadge status="to_be_scheduled" />);

      expect(screen.getByText('To Be Scheduled')).toBeInTheDocument();
    });

    it('renders with correct label for in_progress status', () => {
      render(<JobStatusBadge status="in_progress" />);

      expect(screen.getByText('In Progress')).toBeInTheDocument();
    });

    it('renders with correct label for completed status', () => {
      render(<JobStatusBadge status="completed" />);

      expect(screen.getByText('Complete')).toBeInTheDocument();
    });

    it('renders with correct label for cancelled status', () => {
      render(<JobStatusBadge status="cancelled" />);

      expect(screen.getByText('Cancelled')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<JobStatusBadge status="to_be_scheduled" className="custom-class" />);

      const badge = screen.getByTestId('status-to_be_scheduled');
      expect(badge).toHaveClass('custom-class');
    });
  });

  describe('tooltip', () => {
    it('does not show tooltip by default', () => {
      render(<JobStatusBadge status="to_be_scheduled" />);

      expect(
        screen.queryByText(/Job is waiting to be scheduled/)
      ).not.toBeInTheDocument();
    });

    it('shows correct tooltip for in_progress status', async () => {
      const user = userEvent.setup();
      render(<JobStatusBadge status="in_progress" showTooltip />);

      const badge = screen.getByTestId('status-in_progress');
      await user.hover(badge.parentElement!);

      expect(
        screen.getByText('Work is currently being performed')
      ).toBeInTheDocument();
    });
  });
});

describe('getNextStatuses', () => {
  it('returns correct next statuses for to_be_scheduled', () => {
    const nextStatuses = getNextStatuses('to_be_scheduled');
    expect(nextStatuses).toEqual(['scheduled', 'in_progress', 'cancelled']);
  });

  it('returns correct next statuses for scheduled', () => {
    const nextStatuses = getNextStatuses('scheduled');
    expect(nextStatuses).toEqual(['in_progress', 'to_be_scheduled', 'cancelled']);
  });

  it('returns correct next statuses for in_progress', () => {
    const nextStatuses = getNextStatuses('in_progress');
    expect(nextStatuses).toEqual(['completed', 'cancelled']);
  });

  it('returns empty array for completed', () => {
    const nextStatuses = getNextStatuses('completed');
    expect(nextStatuses).toEqual([]);
  });

  it('returns empty array for cancelled', () => {
    const nextStatuses = getNextStatuses('cancelled');
    expect(nextStatuses).toEqual([]);
  });
});

describe('canTransitionTo', () => {
  it('allows transition from to_be_scheduled to in_progress', () => {
    expect(canTransitionTo('to_be_scheduled', 'in_progress')).toBe(true);
  });

  it('allows transition from to_be_scheduled to scheduled', () => {
    expect(canTransitionTo('to_be_scheduled', 'scheduled')).toBe(true);
  });

  it('allows transition from to_be_scheduled to cancelled', () => {
    expect(canTransitionTo('to_be_scheduled', 'cancelled')).toBe(true);
  });

  it('does not allow transition from to_be_scheduled to completed', () => {
    expect(canTransitionTo('to_be_scheduled', 'completed')).toBe(false);
  });

  it('allows transition from scheduled to in_progress', () => {
    expect(canTransitionTo('scheduled', 'in_progress')).toBe(true);
  });

  it('allows transition from scheduled to to_be_scheduled', () => {
    expect(canTransitionTo('scheduled', 'to_be_scheduled')).toBe(true);
  });

  it('allows transition from scheduled to cancelled', () => {
    expect(canTransitionTo('scheduled', 'cancelled')).toBe(true);
  });

  it('allows transition from in_progress to completed', () => {
    expect(canTransitionTo('in_progress', 'completed')).toBe(true);
  });

  it('allows transition from in_progress to cancelled', () => {
    expect(canTransitionTo('in_progress', 'cancelled')).toBe(true);
  });

  it('does not allow transition from in_progress to to_be_scheduled', () => {
    expect(canTransitionTo('in_progress', 'to_be_scheduled')).toBe(false);
  });

  it('does not allow any transition from completed', () => {
    expect(canTransitionTo('completed', 'to_be_scheduled')).toBe(false);
    expect(canTransitionTo('completed', 'in_progress')).toBe(false);
    expect(canTransitionTo('completed', 'cancelled')).toBe(false);
  });

  it('does not allow any transition from cancelled', () => {
    expect(canTransitionTo('cancelled', 'to_be_scheduled')).toBe(false);
    expect(canTransitionTo('cancelled', 'in_progress')).toBe(false);
    expect(canTransitionTo('cancelled', 'completed')).toBe(false);
  });
});

describe('JOB_STATUS_WORKFLOW', () => {
  it('defines workflow for all statuses', () => {
    const allStatuses: JobStatus[] = [
      'to_be_scheduled',
      'scheduled',
      'in_progress',
      'completed',
      'cancelled',
    ];

    allStatuses.forEach((status) => {
      expect(JOB_STATUS_WORKFLOW).toHaveProperty(status);
      expect(Array.isArray(JOB_STATUS_WORKFLOW[status])).toBe(true);
    });
  });

  it('has correct workflow structure', () => {
    expect(JOB_STATUS_WORKFLOW).toEqual({
      to_be_scheduled: ['scheduled', 'in_progress', 'cancelled'],
      scheduled: ['in_progress', 'to_be_scheduled', 'cancelled'],
      in_progress: ['completed', 'cancelled'],
      completed: [],
      cancelled: [],
    });
  });
});
