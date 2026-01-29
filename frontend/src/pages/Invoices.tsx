import { InvoiceList } from '@/features/invoices';
import { PageHeader } from '@/shared/components';

export function InvoicesPage() {
  return (
    <div data-testid="invoices-page">
      <PageHeader title="Invoices" />
      <InvoiceList />
    </div>
  );
}
