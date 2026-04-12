import { SalesPipeline } from '@/features/sales';
import { PageHeader } from '@/shared/components';

export function SalesPage() {
  return (
    <div data-testid="sales-page">
      <PageHeader title="Sales Pipeline" />
      <SalesPipeline />
    </div>
  );
}
