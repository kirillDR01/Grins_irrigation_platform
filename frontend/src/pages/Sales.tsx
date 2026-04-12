import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { SalesPipeline, SalesDetail, SalesCalendar } from '@/features/sales';
import { PageHeader } from '@/shared/components';
import { Button } from '@/components/ui/button';
import { List, CalendarDays } from 'lucide-react';
import { cn } from '@/lib/utils';

type SalesTab = 'pipeline' | 'calendar';

export function SalesPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<SalesTab>('pipeline');

  if (id) {
    return (
      <div data-testid="sales-page">
        <PageHeader title="Sales Entry" />
        <SalesDetail entryId={id} />
      </div>
    );
  }

  return (
    <div data-testid="sales-page">
      <PageHeader title="Sales Pipeline" />
      <div className="flex items-center gap-1 mb-4 border-b border-slate-200">
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'rounded-none border-b-2 px-4',
            activeTab === 'pipeline'
              ? 'border-teal-500 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-700',
          )}
          onClick={() => setActiveTab('pipeline')}
          data-testid="sales-tab-pipeline"
        >
          <List className="h-4 w-4 mr-1.5" />
          Pipeline
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'rounded-none border-b-2 px-4',
            activeTab === 'calendar'
              ? 'border-teal-500 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-700',
          )}
          onClick={() => setActiveTab('calendar')}
          data-testid="sales-tab-calendar"
        >
          <CalendarDays className="h-4 w-4 mr-1.5" />
          Estimate Calendar
        </Button>
      </div>
      {activeTab === 'pipeline' ? <SalesPipeline /> : <SalesCalendar />}
    </div>
  );
}
