import { memo } from 'react';
import { cn } from '@/lib/utils';
import type { JobStatus } from '../types';
import { getJobStatusConfig } from '../types';

interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
  showTooltip?: boolean;
}

const STATUS_DESCRIPTIONS: Record<JobStatus, string> = {
  requested: 'Job has been requested and is awaiting approval',
  approved: 'Job has been approved and is ready to be scheduled',
  scheduled: 'Job has been scheduled for a specific date and time',
  in_progress: 'Work is currently being performed',
  completed: 'Work has been completed, awaiting final review',
  cancelled: 'Job has been cancelled',
  closed: 'Job is fully complete and closed',
};

export const JobStatusBadge = memo(function JobStatusBadge({
  status,
  className,
  showTooltip = false,
}: JobStatusBadgeProps) {
  const config = getJobStatusConfig(status);

  const badge = (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        config.bgColor,
        config.color,
        className
      )}
      data-testid={`status-${status}`}
    >
      {config.label}
    </span>
  );

  if (showTooltip) {
    return (
      <div className="group relative inline-block">
        {badge}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
          <div className="bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap">
            {STATUS_DESCRIPTIONS[status]}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      </div>
    );
  }

  return badge;
});

// Export status workflow helpers
export const JOB_STATUS_WORKFLOW: Record<JobStatus, JobStatus[]> = {
  requested: ['approved', 'cancelled'],
  approved: ['scheduled', 'cancelled'],
  scheduled: ['in_progress', 'cancelled'],
  in_progress: ['completed', 'cancelled'],
  completed: ['closed'],
  cancelled: [],
  closed: [],
};

export function getNextStatuses(currentStatus: JobStatus): JobStatus[] {
  return JOB_STATUS_WORKFLOW[currentStatus] || [];
}

export function canTransitionTo(
  currentStatus: JobStatus,
  targetStatus: JobStatus
): boolean {
  return JOB_STATUS_WORKFLOW[currentStatus]?.includes(targetStatus) || false;
}
