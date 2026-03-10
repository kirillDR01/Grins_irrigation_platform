import { useParams } from 'react-router-dom';
import { PageHeader } from '@/shared/components';
import {
  AgreementDetail,
  AgreementsList,
  BusinessMetricsCards,
  MrrChart,
  TierDistributionChart,
  RenewalPipelineQueue,
  FailedPaymentsQueue,
  UnscheduledVisitsQueue,
  OnboardingIncompleteQueue,
} from '@/features/agreements';

export function AgreementsPage() {
  const { id } = useParams<{ id: string }>();

  if (id) {
    return (
      <div data-testid="agreement-detail-page">
        <AgreementDetail agreementId={id} />
      </div>
    );
  }

  return (
    <div data-testid="agreements-page" className="space-y-6">
      <PageHeader
        title="Service Agreements"
        description="Manage subscription packages, renewals, and payments"
      />
      <BusinessMetricsCards />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MrrChart />
        <TierDistributionChart />
      </div>
      <AgreementsList />
      <div className="space-y-4">
        <RenewalPipelineQueue />
        <FailedPaymentsQueue />
        <UnscheduledVisitsQueue />
        <OnboardingIncompleteQueue />
      </div>
    </div>
  );
}
