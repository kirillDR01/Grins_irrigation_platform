import { memo } from 'react';
import { cn } from '@/shared/utils/cn';
import type { LeadSource } from '../types';
import { LEAD_SOURCE_LABELS, LEAD_SOURCE_COLORS } from '../types';

interface LeadSourceBadgeProps {
  source: LeadSource;
  className?: string;
}

export const LeadSourceBadge = memo(function LeadSourceBadge({
  source,
  className,
}: LeadSourceBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        LEAD_SOURCE_COLORS[source] ?? 'bg-gray-100 text-gray-800',
        className
      )}
      data-testid={`lead-source-${source}`}
    >
      {LEAD_SOURCE_LABELS[source] ?? source}
    </span>
  );
});
