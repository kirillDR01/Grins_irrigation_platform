import { MarketingDashboard } from '@/features/marketing';
import { PageHeader } from '@/shared/components';

export function MarketingPage() {
  return (
    <div data-testid="marketing-page">
      <PageHeader title="Marketing" />
      <MarketingDashboard />
    </div>
  );
}
