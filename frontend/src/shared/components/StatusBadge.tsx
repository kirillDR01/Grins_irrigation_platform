import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/shared/utils/cn';

// Job status colors - Updated per design system
const jobStatusColors: Record<string, string> = {
  requested: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
  approved: 'bg-blue-100 text-blue-700 hover:bg-blue-100',
  scheduled: 'bg-violet-100 text-violet-700 hover:bg-violet-100',
  in_progress: 'bg-orange-100 text-orange-700 hover:bg-orange-100',
  completed: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
  closed: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
  cancelled: 'bg-red-100 text-red-700 hover:bg-red-100',
};

// Appointment status colors
const appointmentStatusColors: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-700 hover:bg-amber-100',
  confirmed: 'bg-blue-100 text-blue-700 hover:bg-blue-100',
  in_progress: 'bg-orange-100 text-orange-700 hover:bg-orange-100',
  completed: 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100',
  cancelled: 'bg-red-100 text-red-700 hover:bg-red-100',
  no_show: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
};

// Customer flag/tag colors - Updated per design system
const customerFlagColors: Record<string, string> = {
  priority: 'bg-rose-50 text-rose-600 border border-rose-100 hover:bg-rose-50',
  red_flag: 'bg-red-100 text-red-700 hover:bg-red-100',
  slow_payer: 'bg-orange-100 text-orange-700 hover:bg-orange-100',
  new_customer: 'bg-blue-50 text-blue-600 border border-blue-100 hover:bg-blue-50',
  new: 'bg-teal-50 text-teal-600 hover:bg-teal-50',
};

// Category badge colors
const categoryColors: Record<string, string> = {
  ready: 'bg-emerald-50 text-emerald-600 border border-emerald-100 hover:bg-emerald-50',
  needs_estimate: 'bg-amber-50 text-amber-600 border border-amber-100 hover:bg-amber-50',
};

type StatusType = 'job' | 'appointment' | 'customer' | 'category';

interface StatusBadgeProps {
  status: string;
  type?: StatusType;
  className?: string;
}

export const StatusBadge = memo(function StatusBadge({ status, type = 'job', className }: StatusBadgeProps) {
  const colorMap =
    type === 'job'
      ? jobStatusColors
      : type === 'appointment'
        ? appointmentStatusColors
        : type === 'category'
          ? categoryColors
          : customerFlagColors;

  const colorClass = colorMap[status] || 'bg-gray-100 text-gray-800';
  const displayStatus = status.replace(/_/g, ' ');

  return (
    <Badge
      variant="secondary"
      className={cn('px-3 py-1 rounded-full text-xs font-medium', colorClass, 'capitalize', className)}
      data-testid={`status-${status}`}
    >
      {displayStatus}
    </Badge>
  );
});
