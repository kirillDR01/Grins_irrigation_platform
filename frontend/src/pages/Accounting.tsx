import { AccountingDashboard } from '@/features/accounting';
import { PageHeader } from '@/shared/components';

export function AccountingPage() {
  return (
    <div data-testid="accounting-page">
      <PageHeader title="Accounting" />
      <AccountingDashboard />
    </div>
  );
}
