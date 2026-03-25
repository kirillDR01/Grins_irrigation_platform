/**
 * Lead time indicator badge (Req 25).
 * Shows how far booked out the schedule is.
 */

import { useQuery } from '@tanstack/react-query';
import { Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { appointmentApi } from '../api/appointmentApi';

export function LeadTimeIndicator() {
  const { data, isLoading } = useQuery({
    queryKey: ['schedule', 'lead-time'],
    queryFn: () => appointmentApi.getLeadTime(),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading || !data) return null;

  const label =
    data.days >= 14
      ? `Booked out ${Math.round(data.days / 7)} weeks`
      : `Booked out ${data.days} days`;

  return (
    <Badge
      variant="outline"
      className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-amber-700 bg-amber-50 border-amber-200"
      data-testid="lead-time-indicator"
    >
      <Clock className="h-3.5 w-3.5" />
      {label}
    </Badge>
  );
}
