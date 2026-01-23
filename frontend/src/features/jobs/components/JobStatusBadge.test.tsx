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
    'requested',
    'approved',
    'scheduled',
    'in_progress',
    'completed',
    'cancelled',
    'closed',
  ];

  describe('rendering', () => {
    it.each(allStatuses)('renders %s status correctly', (status) => {
      render(<JobStatusBadge status={status} />);

      expect(screen.getByTestId(`status-${status}`)).toBeInTheDocument();
    });

    it('renders with correct label for requested status', () => {
      render(<JobStatusBadge status="requested" />);

      expect(screen.getByText('Requested')).toBeInTheDocument();
    });

    it('renders with correct label for approved status', () => {
      render(<JobStatusBadge status="approved" />);

      expect(screen.getByText('Approved')).toBeInTheDocument();
    });

    it('renders with correct label for scheduled status', () => {
      render(<JobStatusBadge status="scheduled" />);

      expect(screen.getByText('Scheduled')).toBeInTheDocument();
    });

    it('renders with correct label for in_progress status', () => {
      render(<JobStatusBadge status="in_progress" />);

      expect(screen.getByText('In Progress')).toBeInTheDocument();
    });

    it('renders with correct label for completed status', () => {
      render(<JobStatusBadge status="completed" />);

      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('renders with correct label for cancelled status', () => {
      render(<JobStatusBadge status="cancelled" />);

      expect(screen.getByText('Cancelled')).toBeInTheDocument();
    });

    it('renders with correct label for closed status', () => {
      render(<JobStatusBadge status="closed" />);

      expect(screen.getByText('Closed')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<JobStatusBadge status="requested" className="custom-class" />);

      const badge = screen.getByTestId('status-requested');
      expect(badge).toHaveClass('custom-class');
    });
  });

  describe('tooltip', () => {
    it('does not show tooltip by default', () => {
      render(<JobStatusBadge status="requested" />);

      expect(
        screen.queryByText(/Job has been requested/)
      ).not.toBeInTheDocument();
    });

    it('shows tooltip on hover when showTooltip is true', async () => {
      const user = userEvent.setup();
      render(<JobStatusBadge status="requested" showTooltip />);

      const badge = screen.getByTestId('status-requested');
      await user.hover(badge.parentElement!);

      // The tooltip should be in the DOM (hidden by CSS until hover)
      expect(
        screen.getByText('Job has been requested and is awaiting approval')
      ).toBeInTheDocument();
    });

    it('shows correct tooltip for approved status', async () => {
      const user = userEvent.setup();
      render(<JobStatusBadge status="approved" showTooltip />);

      const badge = screen.getByTestId('status-approved');
      await user.hover(badge.parentElement!);

      expect(
        screen.getByText(
          'Job has been approved and is ready to be scheduled'
        )
      ).toBeInTheDocument();
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
  it('returns correct next statuses for requested', () => {
    const nextStatuses = getNextStatuses('requested');
    expect(nextStatuses).toEqual(['approved', 'cancelled']);
  });

  it('returns correct next statuses for approved', () => {
    const nextStatuses = getNextStatuses('approved');
    expect(nextStatuses).toEqual(['scheduled', 'cancelled']);
  });

  it('returns correct next statuses for scheduled', () => {
    const nextStatuses = getNextStatuses('scheduled');
    expect(nextStatuses).toEqual(['in_progress', 'cancelled']);
  });

  it('returns correct next statuses for in_progress', () => {
    const nextStatuses = getNextStatuses('in_progress');
    expect(nextStatuses).toEqual(['completed', 'cancelled']);
  });

  it('returns correct next statuses for completed', () => {
    const nextStatuses = getNextStatuses('completed');
    expect(nextStatuses).toEqual(['closed']);
  });

  it('returns empty array for cancelled', () => {
    const nextStatuses = getNextStatuses('cancelled');
    expect(nextStatuses).toEqual([]);
  });

  it('returns empty array for closed', () => {
    const nextStatuses = getNextStatuses('closed');
    expect(nextStatuses).toEqual([]);
  });
});

describe('canTransitionTo', () => {
  it('allows transition from requested to approved', () => {
    expect(canTransitionTo('requested', 'approved')).toBe(true);
  });

  it('allows transition from requested to cancelled', () => {
    expect(canTransitionTo('requested', 'cancelled')).toBe(true);
  });

  it('does not allow transition from requested to completed', () => {
    expect(canTransitionTo('requested', 'completed')).toBe(false);
  });

  it('allows transition from approved to scheduled', () => {
    expect(canTransitionTo('approved', 'scheduled')).toBe(true);
  });

  it('does not allow transition from approved to in_progress', () => {
    expect(canTransitionTo('approved', 'in_progress')).toBe(false);
  });

  it('allows transition from in_progress to completed', () => {
    expect(canTransitionTo('in_progress', 'completed')).toBe(true);
  });

  it('allows transition from completed to closed', () => {
    expect(canTransitionTo('completed', 'closed')).toBe(true);
  });

  it('does not allow any transition from closed', () => {
    expect(canTransitionTo('closed', 'requested')).toBe(false);
    expect(canTransitionTo('closed', 'approved')).toBe(false);
    expect(canTransitionTo('closed', 'cancelled')).toBe(false);
  });

  it('does not allow any transition from cancelled', () => {
    expect(canTransitionTo('cancelled', 'requested')).toBe(false);
    expect(canTransitionTo('cancelled', 'approved')).toBe(false);
    expect(canTransitionTo('cancelled', 'closed')).toBe(false);
  });
});

describe('JOB_STATUS_WORKFLOW', () => {
  it('defines workflow for all statuses', () => {
    const allStatuses: JobStatus[] = [
      'requested',
      'approved',
      'scheduled',
      'in_progress',
      'completed',
      'cancelled',
      'closed',
    ];

    allStatuses.forEach((status) => {
      expect(JOB_STATUS_WORKFLOW).toHaveProperty(status);
      expect(Array.isArray(JOB_STATUS_WORKFLOW[status])).toBe(true);
    });
  });

  it('has correct workflow structure', () => {
    expect(JOB_STATUS_WORKFLOW).toEqual({
      requested: ['approved', 'cancelled'],
      approved: ['scheduled', 'cancelled'],
      scheduled: ['in_progress', 'cancelled'],
      in_progress: ['completed', 'cancelled'],
      completed: ['closed'],
      cancelled: [],
      closed: [],
    });
  });
});
