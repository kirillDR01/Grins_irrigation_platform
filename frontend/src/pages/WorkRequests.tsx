import { useParams } from 'react-router-dom';
import { PageHeader } from '@/shared/components';
import { WorkRequestsList } from '@/features/work-requests/components/WorkRequestsList';
import { WorkRequestDetail } from '@/features/work-requests/components/WorkRequestDetail';

export function WorkRequestsPage() {
  const { id } = useParams<{ id: string }>();

  if (id) {
    return <WorkRequestDetail />;
  }

  return (
    <div data-testid="work-requests-page">
      <PageHeader
        title="Work Requests"
        description="Google Sheets form submissions"
      />
      <WorkRequestsList />
    </div>
  );
}
