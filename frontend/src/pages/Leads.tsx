import { useParams } from 'react-router-dom';
import { PageHeader } from '@/shared/components';
import { LeadsList } from '@/features/leads/components/LeadsList';
import { LeadDetail } from '@/features/leads/components/LeadDetail';

export function LeadsPage() {
  const { id } = useParams<{ id: string }>();

  // If we have an ID in the URL, show the detail view
  if (id) {
    return <LeadDetail />;
  }

  // Otherwise show the list view
  return (
    <div data-testid="leads-page">
      <PageHeader
        title="Leads"
        description="Manage incoming leads from the website"
      />
      <LeadsList />
    </div>
  );
}
