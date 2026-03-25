import { CommunicationsDashboard } from '@/features/communications';
import { PageHeader } from '@/shared/components';

export function CommunicationsPage() {
  return (
    <div data-testid="communications-page">
      <PageHeader title="Communications" />
      <CommunicationsDashboard />
    </div>
  );
}
