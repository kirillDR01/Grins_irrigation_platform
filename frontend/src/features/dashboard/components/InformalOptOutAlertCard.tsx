/**
 * Dashboard AlertCard for unacknowledged informal-opt-out alerts (Gap 06).
 *
 * Renders the amber variant with a count driven by the same query the
 * queue page consumes. Clicking navigates to /alerts/informal-opt-out.
 */
import { AlertOctagon } from 'lucide-react';

import { AlertCard } from './AlertCard';
import { useInformalOptOutCount } from '../hooks/useInformalOptOutCount';

export function InformalOptOutAlertCard() {
  const { data: count } = useInformalOptOutCount();
  if (!count || count <= 0) {
    return null;
  }
  return (
    <AlertCard
      title="Informal opt-outs"
      description="Customers asked to stop receiving SMS — admin review required."
      count={count}
      icon={AlertOctagon}
      targetPath="/alerts/informal-opt-out"
      variant="amber"
      testId="informal-opt-out-alert-card"
    />
  );
}
