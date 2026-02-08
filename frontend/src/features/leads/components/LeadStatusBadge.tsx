import { memo } from 'react';
import { cn } from '@/shared/utils/cn';
import type { LeadStatus } from '../types';
import { LEAD_STATUS_LABELS } from '../types';

interface LeadStatusBadgeProps {
  status: LeadStatus;
  className?: string;
  'data-testid'?: string;
}

const leadStatusColors: Record<LeadStatus, string> = {
  new: 'bg-blue-100 text-blue-800',
  contacted: 'bg-yellow-100 text-yellow-800',
  qualified: 'bg-purple-100 text-purple-800',
  converted: 'bg-green-100 text-green-800',
  lost: 'bg-gray-100 text-gray-800',
  spam: 'bg-red-100 text-red-800',
};

export const LeadStatusBadge = memo(function LeadStatusBadge({
  status,
  className,
  'data-testid': dataTestId,
}: LeadStatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        leadStatusColors[status],
        className
      )}
      data-testid={dataTestId || 'lead-status-badge'}
    >
      {LEAD_STATUS_LABELS[status]}
    </span>
  );
});
