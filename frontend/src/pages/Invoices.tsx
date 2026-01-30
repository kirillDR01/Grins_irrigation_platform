import { InvoiceList, CreateInvoiceDialog } from '@/features/invoices';
import { PageHeader } from '@/shared/components';
import { useQueryClient } from '@tanstack/react-query';

export function InvoicesPage() {
  const queryClient = useQueryClient();

  const handleInvoiceCreated = () => {
    // Invalidate invoice queries to refresh the list
    queryClient.invalidateQueries({ queryKey: ['invoices'] });
  };

  return (
    <div data-testid="invoices-page">
      <PageHeader
        title="Invoices"
        action={<CreateInvoiceDialog onSuccess={handleInvoiceCreated} />}
      />
      <InvoiceList />
    </div>
  );
}
