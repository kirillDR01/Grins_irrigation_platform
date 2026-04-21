import { InformalOptOutQueue } from '@/features/communications';
import { PageHeader } from '@/shared/components';

export function InformalOptOutQueuePage() {
  return (
    <div data-testid="informal-opt-out-page" className="p-6">
      <PageHeader
        title="Informal opt-out review"
        description="Resolve customers who informally asked to stop receiving SMS."
      />
      <InformalOptOutQueue />
    </div>
  );
}
