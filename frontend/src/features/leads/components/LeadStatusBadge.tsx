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
  qualified: 'bg-gray-100 text-gray-600',
  converted: 'bg-gray-100 text-gray-600',
  lost: 'bg-gray-100 text-gray-600',
  spam: 'bg-gray-100 text-gray-600',
};

/** Legacy statuses that should render as "Archived" */
const LEGACY_STATUSES: Set<LeadStatus> = new Set(['qualified', 'converted', 'lost', 'spam']);

export const LeadStatusBadge = memo(function LeadStatusBadge({
  status,
  className,
  'data-testid': dataTestId,
}: LeadStatusBadgeProps) {
  const isLegacy = LEGACY_STATUSES.has(status);
  const label = isLegacy ? 'Archived' : LEAD_STATUS_LABELS[status];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        leadStatusColors[status],
        className
      )}
      data-testid={dataTestId || 'lead-status-badge'}
    >
      {label}
    </span>
  );
});
