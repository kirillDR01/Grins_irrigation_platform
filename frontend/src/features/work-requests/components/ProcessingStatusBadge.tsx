import { memo } from 'react';
import { cn } from '@/shared/utils/cn';
import type { ProcessingStatus } from '../types';
import { PROCESSING_STATUS_LABELS } from '../types';

interface ProcessingStatusBadgeProps {
  status: ProcessingStatus;
  className?: string;
}

const statusColors: Record<ProcessingStatus, string> = {
  imported: 'bg-blue-100 text-blue-800',
  lead_created: 'bg-green-100 text-green-800',
  skipped: 'bg-gray-100 text-gray-800',
  error: 'bg-red-100 text-red-800',
};

export const ProcessingStatusBadge = memo(function ProcessingStatusBadge({
  status,
  className,
}: ProcessingStatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        statusColors[status],
        className
      )}
      data-testid={`status-${status}`}
    >
      {PROCESSING_STATUS_LABELS[status]}
    </span>
  );
});
