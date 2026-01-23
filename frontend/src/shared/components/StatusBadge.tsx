import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

// Job status colors
const jobStatusColors: Record<string, string> = {
  requested: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
  approved: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
  scheduled: 'bg-purple-100 text-purple-800 hover:bg-purple-100',
  in_progress: 'bg-orange-100 text-orange-800 hover:bg-orange-100',
  completed: 'bg-green-100 text-green-800 hover:bg-green-100',
  closed: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
  cancelled: 'bg-red-100 text-red-800 hover:bg-red-100',
};

// Appointment status colors
const appointmentStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
  confirmed: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
  in_progress: 'bg-orange-100 text-orange-800 hover:bg-orange-100',
  completed: 'bg-green-100 text-green-800 hover:bg-green-100',
  cancelled: 'bg-red-100 text-red-800 hover:bg-red-100',
  no_show: 'bg-gray-100 text-gray-800 hover:bg-gray-100',
};

// Customer flag colors
const customerFlagColors: Record<string, string> = {
  priority: 'bg-green-100 text-green-800 hover:bg-green-100',
  red_flag: 'bg-red-100 text-red-800 hover:bg-red-100',
  slow_payer: 'bg-orange-100 text-orange-800 hover:bg-orange-100',
  new_customer: 'bg-blue-100 text-blue-800 hover:bg-blue-100',
};

type StatusType = 'job' | 'appointment' | 'customer';

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
        : customerFlagColors;

  const colorClass = colorMap[status] || 'bg-gray-100 text-gray-800';
  const displayStatus = status.replace(/_/g, ' ');

  return (
    <Badge
      variant="secondary"
      className={cn(colorClass, 'capitalize', className)}
      data-testid={`status-${status}`}
    >
      {displayStatus}
    </Badge>
  );
});
