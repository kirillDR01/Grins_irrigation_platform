import { memo } from 'react';
import { cn } from '@/shared/utils/cn';
import type { LeadSituation } from '../types';
import { LEAD_SITUATION_LABELS } from '../types';

interface LeadSituationBadgeProps {
  situation: LeadSituation;
  className?: string;
  'data-testid'?: string;
}

const leadSituationColors: Record<LeadSituation, string> = {
  new_system: 'bg-blue-50 text-blue-700',
  upgrade: 'bg-teal-50 text-teal-700',
  repair: 'bg-orange-50 text-orange-700',
  exploring: 'bg-slate-100 text-slate-700',
};

export const LeadSituationBadge = memo(function LeadSituationBadge({
  situation,
  className,
  'data-testid': dataTestId,
}: LeadSituationBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
        leadSituationColors[situation],
        className
      )}
      data-testid={dataTestId || 'lead-situation-badge'}
    >
      {LEAD_SITUATION_LABELS[situation]}
    </span>
  );
});
