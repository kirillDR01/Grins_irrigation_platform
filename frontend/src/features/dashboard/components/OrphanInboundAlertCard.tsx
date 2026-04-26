/**
 * Dashboard AlertCard for ORPHAN_INBOUND alerts (gap-14).
 *
 * Inbound SMS that the webhook couldn't correlate to a customer or open
 * thread. Routes to the schedule page; the inbox queue (gap-16) is the
 * eventual triage surface.
 */
import { Inbox } from 'lucide-react';

import { useAlertCounts } from '../hooks/useAlertCounts';
import { AlertCard } from './AlertCard';

export function OrphanInboundAlertCard() {
  const { data } = useAlertCounts();
  const count = data?.counts?.orphan_inbound ?? 0;
  if (count <= 0) {
    return null;
  }
  return (
    <AlertCard
      title="Orphan inbound messages"
      description="Inbound SMS from unknown numbers — may need a new lead/customer."
      count={count}
      icon={Inbox}
      targetPath="/schedule"
      queryParams={{ section: 'inbox-queue' }}
      variant="amber"
      testId="orphan-inbound-alert-card"
    />
  );
}
