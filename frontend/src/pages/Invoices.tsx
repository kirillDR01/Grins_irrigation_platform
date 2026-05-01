import { useParams, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import { InvoiceList, CreateInvoiceDialog } from '@/features/invoices';
import { InvoiceDetail } from '@/features/invoices/components';
import { LienReviewQueue } from '@/features/invoices/components/LienReviewQueue';
import { PriceListEditor } from '@/features/pricelist';
import { PageHeader } from '@/shared/components';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';

const TAB_ALL = 'all';
const TAB_LIEN = 'lien-review';
const TAB_PRICELIST = 'pricelist';
const VALID_TABS = new Set([TAB_ALL, TAB_LIEN, TAB_PRICELIST]);

export function InvoicesPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { id } = useParams<{ id: string }>();

  if (id) {
    return <InvoiceDetail />;
  }

  const tabParam = searchParams.get('tab') ?? '';
  const activeTab = VALID_TABS.has(tabParam) ? tabParam : TAB_ALL;

  const handleInvoiceCreated = () => {
    // Invalidate invoice queries to refresh the list
    queryClient.invalidateQueries({ queryKey: ['invoices'] });
  };

  const handleTabChange = (value: string) => {
    if (value === TAB_ALL) {
      // drop ?tab= when the user is on the default tab
      const next = new URLSearchParams(searchParams);
      next.delete('tab');
      setSearchParams(next);
    } else {
      setSearchParams({ tab: value });
    }
  };

  return (
    <div data-testid="invoices-page">
      <PageHeader
        title="Invoices"
        action={<CreateInvoiceDialog onSuccess={handleInvoiceCreated} />}
      />

      <Tabs value={activeTab} onValueChange={handleTabChange} className="mt-4">
        <TabsList data-testid="invoices-tabs">
          <TabsTrigger value={TAB_ALL} data-testid="tab-all-invoices">
            All Invoices
          </TabsTrigger>
          <TabsTrigger value={TAB_LIEN} data-testid="tab-lien-review">
            Lien Review
          </TabsTrigger>
          <TabsTrigger value={TAB_PRICELIST} data-testid="tab-pricelist">
            Pricelist
          </TabsTrigger>
        </TabsList>
        <TabsContent value={TAB_ALL}>
          <InvoiceList />
        </TabsContent>
        <TabsContent value={TAB_LIEN}>
          <LienReviewQueue />
        </TabsContent>
        <TabsContent value={TAB_PRICELIST}>
          <PriceListEditor />
        </TabsContent>
      </Tabs>
    </div>
  );
}
