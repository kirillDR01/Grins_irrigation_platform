/**
 * Dashboard AlertCard for UNRECOGNIZED_CONFIRMATION_REPLY alerts (gap-14).
 *
 * Surfaces appointments where the customer replied with a free-text body
 * the parser couldn't classify (Y/R/C synonyms only). Clicking routes to
 * the schedule page; the upcoming inbox card and the per-customer
 * conversation view (gap-13) handle the triage.
 */
import { HelpCircle } from 'lucide-react';

import { useAlertCounts } from '../hooks/useAlertCounts';
import { AlertCard } from './AlertCard';

export function UnrecognizedReplyAlertCard() {
  const { data } = useAlertCounts();
  const count = data?.counts?.unrecognized_confirmation_reply ?? 0;
  if (count <= 0) {
    return null;
  }
  return (
    <AlertCard
      title="Unrecognized customer replies"
      description="Replies the parser couldn't classify — manual triage required."
      count={count}
      icon={HelpCircle}
      targetPath="/schedule"
      queryParams={{ section: 'inbox-queue' }}
      variant="amber"
      testId="unrecognized-reply-alert-card"
    />
  );
}
