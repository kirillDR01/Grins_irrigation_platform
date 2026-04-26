/**
 * Dashboard AlertCard for CONFIRMATION_NO_REPLY alerts (gap-14).
 *
 * Counts appointments where the customer hasn't replied to the Y/R/C
 * confirmation prompt. Routes to the schedule page where the
 * NoReplyReviewQueue lives.
 */
import { Clock } from 'lucide-react';

import { useAlertCounts } from '../hooks/useAlertCounts';
import { AlertCard } from './AlertCard';

export function NoReplyConfirmationAlertCard() {
  const { data } = useAlertCounts();
  const count = data?.counts?.confirmation_no_reply ?? 0;
  if (count <= 0) {
    return null;
  }
  return (
    <AlertCard
      title="No-reply confirmations"
      description="Confirmation SMS sent but no Y/R/C reply yet."
      count={count}
      icon={Clock}
      targetPath="/schedule"
      queryParams={{ tab: 'no-reply' }}
      variant="amber"
      testId="no-reply-confirmation-alert-card"
    />
  );
}
