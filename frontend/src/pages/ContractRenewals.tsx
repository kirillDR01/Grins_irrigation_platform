import { useParams } from 'react-router-dom';
import { RenewalReviewList, RenewalProposalDetail } from '@/features/contract-renewals';
import { PageHeader } from '@/shared/components';

export function ContractRenewalsPage() {
  const { id } = useParams<{ id: string }>();

  if (id) {
    return (
      <div data-testid="contract-renewals-page">
        <PageHeader title="Renewal Proposal" />
        <RenewalProposalDetail proposalId={id} />
      </div>
    );
  }

  return (
    <div data-testid="contract-renewals-page">
      <PageHeader title="Contract Renewal Reviews" />
      <RenewalReviewList />
    </div>
  );
}
