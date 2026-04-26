/**
 * Dashboard AlertCard for unacknowledged PENDING_RESCHEDULE_REQUEST alerts (gap-14).
 *
 * Count is sourced from the unified /api/v1/alerts/counts endpoint so a
 * single network call feeds every per-type card on the dashboard.
 * Clicking deep-links to the schedule page where the
 * RescheduleRequestsQueue handles the work.
 */
import { CalendarClock } from 'lucide-react';

import { useAlertCounts } from '../hooks/useAlertCounts';
import { AlertCard } from './AlertCard';

export function PendingRescheduleAlertCard() {
  const { data } = useAlertCounts();
  const count = data?.counts?.pending_reschedule_request ?? 0;
  if (count <= 0) {
    return null;
  }
  return (
    <AlertCard
      title="Pending reschedule requests"
      description="Customers asked to move their appointment — admin action required."
      count={count}
      icon={CalendarClock}
      targetPath="/schedule"
      queryParams={{ tab: 'reschedule-queue' }}
      variant="amber"
      testId="pending-reschedule-alert-card"
    />
  );
}
